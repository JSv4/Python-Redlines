"""
Comparison engine implementations for document redlining.

This module provides concrete implementations of the ComparisonEngine interface
for generating redlined Word documents with tracked changes.
"""

import subprocess
import tempfile
import os
import platform
import logging
import zipfile
import tarfile
from pathlib import Path
from typing import Union, Tuple, Optional

from .base import ComparisonEngine, ComparisonError
from .__about__ import __version__

logger = logging.getLogger(__name__)


class BinaryManager:
    """
    Utility class for managing platform-specific binary extraction and caching.

    This class handles the extraction and caching of compiled binaries for
    different platforms (Windows, Linux, macOS) and architectures (x64, ARM64).
    """

    def __init__(
        self,
        engine_name: str,
        dist_subdir: str,
        binary_base_name: str,
        version: str,
        target_path: Optional[str] = None
    ):
        """
        Initialize the binary manager.

        Args:
            engine_name: Identifier for the engine (used in error messages)
            dist_subdir: Subdirectory under dist/ where binaries are stored
            binary_base_name: Base name of the binary (without extension)
            version: Version string for the binaries
            target_path: Optional custom path to extract binaries to
        """
        self.engine_name = engine_name
        self.dist_subdir = dist_subdir
        self.binary_base_name = binary_base_name
        self.version = version
        self.target_path = target_path
        self._binary_path: Optional[str] = None

    def get_binary_path(self) -> str:
        """
        Get the path to the extracted binary, extracting it if necessary.

        Returns:
            str: Full path to the binary executable

        Raises:
            EnvironmentError: If the platform/architecture is not supported
            FileNotFoundError: If the binary archive is not found
        """
        if self._binary_path and os.path.exists(self._binary_path):
            return self._binary_path

        self._binary_path = self._extract_binary()
        return self._binary_path

    def _extract_binary(self) -> str:
        """Extract the appropriate binary for the current platform."""
        base_path = os.path.dirname(os.path.dirname(__file__))
        module_path = os.path.dirname(__file__)
        binaries_path = os.path.join(module_path, 'dist', self.dist_subdir)
        target_path = self.target_path or os.path.join(module_path, 'bin', self.dist_subdir)

        if not os.path.exists(target_path):
            os.makedirs(target_path)

        binary_name, archive_name = self._get_platform_info()
        full_binary_path = os.path.join(target_path, binary_name)

        if not os.path.exists(full_binary_path):
            archive_path = os.path.join(binaries_path, archive_name)
            if not os.path.exists(archive_path):
                raise FileNotFoundError(
                    f"Binary archive not found for {self.engine_name}: {archive_path}. "
                    f"Please ensure the package was installed correctly."
                )
            self._extract_archive(archive_path, target_path)

        return full_binary_path

    def _extract_archive(self, archive_path: str, target_path: str) -> None:
        """Extract a .zip or .tar.gz archive to the target path."""
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(target_path)
        elif archive_path.endswith('.tar.gz'):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(target_path)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")

    def _get_platform_info(self) -> Tuple[str, str]:
        """
        Get binary name and archive name based on OS and architecture.

        Returns:
            Tuple of (binary_name, archive_name)
        """
        os_name = platform.system().lower()
        arch = platform.machine().lower()

        if arch in ('x86_64', 'amd64'):
            arch = 'x64'
        elif arch in ('arm64', 'aarch64'):
            arch = 'arm64'
        else:
            raise EnvironmentError(f"Unsupported architecture: {arch}")

        if os_name == 'linux':
            archive_name = f"linux-{arch}-{self.version}.tar.gz"
            binary_name = f"linux-{arch}/{self.binary_base_name}"
        elif os_name == 'windows':
            archive_name = f"win-{arch}-{self.version}.zip"
            binary_name = f"win-{arch}/{self.binary_base_name}.exe"
        elif os_name == 'darwin':
            archive_name = f"osx-{arch}-{self.version}.tar.gz"
            binary_name = f"osx-{arch}/{self.binary_base_name}"
        else:
            raise EnvironmentError(f"Unsupported OS: {os_name}")

        return binary_name, archive_name

    def is_available(self) -> bool:
        """Check if the binary is available for extraction."""
        try:
            binary_name, archive_name = self._get_platform_info()
            module_path = os.path.dirname(__file__)
            binaries_path = os.path.join(module_path, 'dist', self.dist_subdir)
            archive_path = os.path.join(binaries_path, archive_name)
            return os.path.exists(archive_path)
        except EnvironmentError:
            return False


class XmlPowerToolsEngine(ComparisonEngine):
    """
    Comparison engine using Open-Xml-PowerTools (WmlComparer).

    This engine wraps the Open-Xml-PowerTools C# library which provides
    Word document comparison functionality through the WmlComparer class.

    Note: This uses the original Open-Xml-PowerTools package which is
    no longer actively maintained but is stable and well-tested.
    """

    def __init__(self, target_path: Optional[str] = None):
        """
        Initialize the XmlPowerToolsEngine.

        Args:
            target_path: Optional custom path for extracting binaries.
                        If not specified, uses the default bin/ directory.
        """
        self._binary_manager = BinaryManager(
            engine_name="XmlPowerTools",
            dist_subdir="openxml-powertools",
            binary_base_name="redlines",
            version=__version__,
            target_path=target_path
        )
        # Eagerly extract binary to maintain backward compatibility
        self._binary_path = self._binary_manager.get_binary_path()

    @property
    def name(self) -> str:
        return "openxml-powertools"

    @property
    def description(self) -> str:
        return (
            "Open-Xml-PowerTools engine using WmlComparer for Word document comparison. "
            "Stable and well-tested but no longer actively maintained."
        )

    def is_available(self) -> bool:
        return self._binary_manager.is_available()

    def compare(
        self,
        author: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Compare two Word documents and generate a redlined version.

        Args:
            author: Author name for tracked changes attribution
            original: Original document (bytes or Path)
            modified: Modified document (bytes or Path)

        Returns:
            Tuple of (redline_bytes, stdout, stderr)

        Raises:
            ComparisonError: If the comparison process fails
        """
        temp_files = []
        try:
            target_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            target_file.close()
            target_path = target_file.name

            original_path = self._write_to_temp_file(original) if isinstance(original, bytes) else str(original)
            modified_path = self._write_to_temp_file(modified) if isinstance(modified, bytes) else str(modified)

            temp_files.extend([target_path])
            if isinstance(original, bytes):
                temp_files.append(original_path)
            if isinstance(modified, bytes):
                temp_files.append(modified_path)

            command = [self._binary_path, author, original_path, modified_path, target_path]

            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout_output = result.stdout if result.stdout else None
            stderr_output = result.stderr if result.stderr else None

            if result.returncode != 0:
                raise ComparisonError(
                    f"Comparison failed with return code {result.returncode}",
                    stdout=stdout_output,
                    stderr=stderr_output
                )

            if not os.path.exists(target_path):
                raise ComparisonError(
                    "Comparison did not produce output file",
                    stdout=stdout_output,
                    stderr=stderr_output
                )

            redline_output = Path(target_path).read_bytes()
            return redline_output, stdout_output, stderr_output

        finally:
            self._cleanup_temp_files(temp_files)

    def run_redline(
        self,
        author_tag: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Backward-compatible alias for compare().

        Deprecated: Use compare() instead.
        """
        return self.compare(author_tag, original, modified)

    # Legacy property for backward compatibility
    @property
    def extracted_binaries_path(self) -> str:
        """Legacy property for backward compatibility."""
        return self._binary_path

    def _cleanup_temp_files(self, temp_files: list) -> None:
        """Clean up temporary files."""
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError as e:
                logger.warning(f"Error deleting temp file {file_path}: {e}")

    def _write_to_temp_file(self, data: bytes) -> str:
        """Write bytes to a temporary file and return the path."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        temp_file.write(data)
        temp_file.close()
        return temp_file.name


class DocxodusEngine(ComparisonEngine):
    """
    Comparison engine using Docxodus (modern fork of Open-Xml-PowerTools).

    Docxodus is a .NET 8.0 modernization of Open-Xml-PowerTools with
    improved move detection, format change detection, and active maintenance.

    Features over XmlPowerTools:
    - Better move detection (identifies relocated content)
    - Format change detection (recognizes styling-only modifications)
    - Active maintenance and .NET 8.0 support
    - Configurable similarity thresholds
    """

    def __init__(self, target_path: Optional[str] = None):
        """
        Initialize the DocxodusEngine.

        Args:
            target_path: Optional custom path for extracting binaries.
                        If not specified, uses the default bin/ directory.
        """
        self._binary_manager = BinaryManager(
            engine_name="Docxodus",
            dist_subdir="docxodus",
            binary_base_name="redline",
            version=__version__,
            target_path=target_path
        )
        self._binary_path: Optional[str] = None

    def _ensure_binary(self) -> str:
        """Ensure binary is extracted and return its path."""
        if self._binary_path is None:
            self._binary_path = self._binary_manager.get_binary_path()
        return self._binary_path

    @property
    def name(self) -> str:
        return "docxodus"

    @property
    def description(self) -> str:
        return (
            "Docxodus engine - a modern .NET 8.0 fork of Open-Xml-PowerTools with "
            "improved move detection, format change detection, and active maintenance."
        )

    def is_available(self) -> bool:
        return self._binary_manager.is_available()

    def compare(
        self,
        author: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Compare two Word documents and generate a redlined version.

        Args:
            author: Author name for tracked changes attribution
            original: Original document (bytes or Path)
            modified: Modified document (bytes or Path)

        Returns:
            Tuple of (redline_bytes, stdout, stderr)

        Raises:
            ComparisonError: If the comparison process fails
        """
        binary_path = self._ensure_binary()
        temp_files = []

        try:
            target_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            target_file.close()
            target_path = target_file.name

            original_path = self._write_to_temp_file(original) if isinstance(original, bytes) else str(original)
            modified_path = self._write_to_temp_file(modified) if isinstance(modified, bytes) else str(modified)

            temp_files.append(target_path)
            if isinstance(original, bytes):
                temp_files.append(original_path)
            if isinstance(modified, bytes):
                temp_files.append(modified_path)

            # Docxodus redline CLI: redline <original> <modified> <output> [--author=<name>]
            command = [binary_path, original_path, modified_path, target_path, f"--author={author}"]

            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout_output = result.stdout if result.stdout else None
            stderr_output = result.stderr if result.stderr else None

            if result.returncode != 0:
                raise ComparisonError(
                    f"Comparison failed with return code {result.returncode}",
                    stdout=stdout_output,
                    stderr=stderr_output
                )

            if not os.path.exists(target_path):
                raise ComparisonError(
                    "Comparison did not produce output file",
                    stdout=stdout_output,
                    stderr=stderr_output
                )

            redline_output = Path(target_path).read_bytes()
            return redline_output, stdout_output, stderr_output

        finally:
            self._cleanup_temp_files(temp_files)

    def run_redline(
        self,
        author_tag: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Alias for compare() to maintain consistent API with XmlPowerToolsEngine.
        """
        return self.compare(author_tag, original, modified)

    def _cleanup_temp_files(self, temp_files: list) -> None:
        """Clean up temporary files."""
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError as e:
                logger.warning(f"Error deleting temp file {file_path}: {e}")

    def _write_to_temp_file(self, data: bytes) -> str:
        """Write bytes to a temporary file and return the path."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        temp_file.write(data)
        temp_file.close()
        return temp_file.name
