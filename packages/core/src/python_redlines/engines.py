import importlib.metadata
import importlib.resources
import logging
import os
import platform
import subprocess
import tarfile
import tempfile
import warnings
import zipfile
from pathlib import Path
from typing import Optional, Tuple, Union

import platformdirs

from .__about__ import __version__

logger = logging.getLogger(__name__)


class EngineNotInstalledError(ImportError):
    """Raised when an engine is used but its binary package is not installed."""


def _detect_rid() -> str:
    """Return the .NET-style runtime identifier for the current platform."""
    os_name = platform.system().lower()
    machine = platform.machine().lower()

    if machine in ('x86_64', 'amd64'):
        arch = 'x64'
    elif machine in ('arm64', 'aarch64'):
        arch = 'arm64'
    else:
        raise EnvironmentError(f"Unsupported architecture: {machine}")

    if os_name == 'linux':
        return f'linux-{arch}'
    if os_name == 'windows':
        return f'win-{arch}'
    if os_name == 'darwin':
        return f'osx-{arch}'
    raise EnvironmentError(f"Unsupported OS: {os_name}")


class BaseEngine(object):
    """
    Base class for redline comparison engines. Each engine ships its compiled
    binary in a separate, optional companion package; subclasses declare:
      - BINARY_PACKAGE: importable package name that ships the binary archives
      - BINARY_BASE_NAME: the executable name (without .exe extension)
      - EXTRA_NAME: the python-redlines extra that installs the companion package
    """
    BINARY_PACKAGE: str = NotImplemented
    BINARY_BASE_NAME: str = NotImplemented
    EXTRA_NAME: str = NotImplemented

    def __init__(self, target_path: Optional[str] = None):
        self.target_path = target_path
        self.extracted_binaries_path = self._resolve_binary()

    def _resolve_binary(self) -> str:
        """
        Locate the platform binary inside the companion package, extracting it
        once into a writable cache directory. Returns the path to the executable.
        """
        rid = _detect_rid()
        is_windows = rid.startswith('win-')
        archive_name = f'{rid}.zip' if is_windows else f'{rid}.tar.gz'
        binary_name = f'{self.BINARY_BASE_NAME}.exe' if is_windows else self.BINARY_BASE_NAME

        try:
            package_root = importlib.resources.files(self.BINARY_PACKAGE)
        except ModuleNotFoundError as exc:
            raise EngineNotInstalledError(
                f"{type(self).__name__} requires the '{self.BINARY_PACKAGE}' package. "
                f"Install it with:  pip install python-redlines[{self.EXTRA_NAME}]"
            ) from exc

        archive = package_root / '_binaries' / archive_name
        if not archive.is_file():
            raise EngineNotInstalledError(
                f"{type(self).__name__}: '{self.BINARY_PACKAGE}' is installed but contains "
                f"no binary for platform '{rid}'. The wheel may target a different platform."
            )

        extract_root = self._extraction_root() / rid
        binary_path = extract_root / binary_name

        if not binary_path.exists():
            self._extract_archive(archive, extract_root)

        if not is_windows:
            os.chmod(binary_path, 0o755)

        return str(binary_path)

    def _extraction_root(self) -> Path:
        """Directory the binary is extracted into (writable, outside site-packages)."""
        if self.target_path:
            return Path(self.target_path)

        try:
            pkg_version = importlib.metadata.version(self.BINARY_PACKAGE.replace('_', '-'))
        except importlib.metadata.PackageNotFoundError:
            pkg_version = __version__

        return Path(platformdirs.user_cache_dir('python-redlines')) / self.EXTRA_NAME / pkg_version

    @staticmethod
    def _extract_archive(archive, target_path: Path):
        """Extract a .zip or .tar.gz archive (a Traversable) into target_path."""
        target_path.mkdir(parents=True, exist_ok=True)
        name = archive.name

        with importlib.resources.as_file(archive) as archive_path:
            if name.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(target_path)
            elif name.endswith('.tar.gz'):
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    try:
                        tar_ref.extractall(target_path, filter='data')
                    except TypeError:
                        tar_ref.extractall(target_path)
            else:
                raise ValueError(f"Unsupported archive format: {name}")

    def _build_command(self, author_tag: str, original_path, modified_path, target_path, **kwargs):
        """
        Build the command list for subprocess execution.
        Subclasses can override to customize argument format.
        """
        return [self.extracted_binaries_path, author_tag, original_path, modified_path, target_path]

    def run_redline(self, author_tag: str, original: Union[str, bytes, Path], modified: Union[str, bytes, Path],
                    **kwargs) -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Runs the redline binary. The 'original' and 'modified' arguments can be either bytes or file paths
        (as ``str`` or ``pathlib.Path``). Returns the redline output as bytes.

        A path the caller supplies is never deleted; only scratch files this
        method creates are cleaned up.

        Additional keyword arguments are passed to _build_command() for engine-specific
        options. DocxodusEngine supports: case_insensitive, detect_moves,
        move_similarity_threshold, move_minimum_word_count, detect_format_changes,
        conflate_spaces, date_time. It raises ValueError for unrecognised settings and
        for the WmlComparer-era settings removed in Docxodus v11.0.0 (engine,
        detail_threshold, simplify_move_markup). XmlPowerToolsEngine ignores kwargs.
        """
        scratch_files = []
        try:
            # mkstemp, not NamedTemporaryFile: we want a path, and NamedTemporaryFile
            # hands back an open file object that nothing here would close (issue #30).
            handle, target_path = tempfile.mkstemp(suffix='.docx')
            os.close(handle)
            scratch_files.append(target_path)

            original_path = self._as_path(original, scratch_files)
            modified_path = self._as_path(modified, scratch_files)

            command = self._build_command(author_tag, original_path, modified_path, target_path, **kwargs)

            # Capture stdout and stderr
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            stdout_output = result.stdout if isinstance(result.stdout, str) and len(result.stdout) > 0 else None
            stderr_output = result.stderr if isinstance(result.stderr, str) and len(result.stderr) > 0 else None

            redline_output = Path(target_path).read_bytes()

            return redline_output, stdout_output, stderr_output

        finally:
            self._cleanup_temp_files(scratch_files)

    def _as_path(self, document, scratch_files):
        """Return a filesystem path for *document*, writing bytes out if needed.

        Only a path this method creates is appended to *scratch_files*. A path
        the caller passed in is the caller's own document, and registering it
        for cleanup would delete the file they asked us to compare.
        """
        if isinstance(document, bytes):
            path = self._write_to_temp_file(document)
            scratch_files.append(path)
            return path
        return os.fspath(document)

    def _cleanup_temp_files(self, temp_files):
        for file_path in temp_files:
            try:
                os.remove(file_path)
            except OSError as e:
                logger.warning("Error deleting temp file %s: %s", file_path, e)

    def _write_to_temp_file(self, data):
        """
        Writes bytes data to a temporary file and returns the file path.
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(data)
        temp_file.close()
        return temp_file.name


class XmlPowerToolsEngine(BaseEngine):
    BINARY_PACKAGE = 'python_redlines_ooxmlpowertools'
    BINARY_BASE_NAME = 'redlines'
    EXTRA_NAME = 'ooxmlpowertools'

    def __init__(self, target_path: Optional[str] = None):
        warnings.warn(
            "XmlPowerToolsEngine wraps the original, unmaintained Open-XML-PowerTools "
            "WmlComparer and is deprecated; it will be removed in a future major "
            "release. Use DocxodusEngine, which is actively maintained and runs the "
            "DocxDiff algorithm.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(target_path)


class DocxodusEngine(BaseEngine):
    BINARY_PACKAGE = 'python_redlines_docxodus'
    BINARY_BASE_NAME = 'redline'
    EXTRA_NAME = 'docxodus'

    # Settings that died with WmlComparer in Docxodus v11.0.0. They are rejected
    # rather than dropped, because dropping them would not be a breaking change
    # but a wrong-answer one: the v12 CLI rejects --engine as an unknown flag,
    # and merely warns-and-ignores the other two, so a caller who passed
    # engine='wmlcomparer' would silently receive DocxDiff output believing they
    # had selected something else.
    _REMOVED_KWARGS = {
        'engine': (
            "the comparison-engine selector was removed in Docxodus v11.0.0, which "
            "deleted WmlComparer. DocxDiff is now the only algorithm — drop the argument"
        ),
        'detail_threshold': (
            "it tuned WmlComparer's LCS granularity and went with it in Docxodus "
            "v11.0.0. DocxDiff's granularity is structural, with no equivalent knob — "
            "drop the argument"
        ),
        'simplify_move_markup': (
            "it worked around WmlComparer's move markup and went with it in Docxodus "
            "v11.0.0. DocxDiff renders moves natively — drop the argument"
        ),
    }

    # Boolean flags (default False — presence enables)
    _BOOL_FLAGS = [
        ('case_insensitive', '--case-insensitive'),
        ('detect_moves', '--detect-moves'),
    ]

    # Negatable flags (default True — --no- prefix disables)
    _NEG_FLAGS = [
        ('detect_format_changes', '--no-detect-format-changes'),
        ('conflate_spaces', '--no-conflate-spaces'),
    ]

    # Value flags
    _VALUE_FLAGS = [
        ('move_similarity_threshold', '--move-similarity-threshold'),
        ('move_minimum_word_count', '--move-minimum-word-count'),
        ('date_time', '--date-time'),
    ]

    @classmethod
    def _supported_kwargs(cls):
        """Every comparison setting this engine still understands."""
        return {name for name, _ in (*cls._BOOL_FLAGS, *cls._NEG_FLAGS, *cls._VALUE_FLAGS)}

    @classmethod
    def _validate_kwargs(cls, kwargs):
        # Removed settings first, so they get their specific explanation rather
        # than being lumped in with typos below.
        for name, reason in cls._REMOVED_KWARGS.items():
            if name in kwargs:
                raise ValueError(f"{name} is no longer supported: {reason}.")

        supported = cls._supported_kwargs()
        unknown = sorted(set(kwargs) - supported)
        if unknown:
            raise ValueError(
                f"Unknown comparison setting(s): {', '.join(unknown)}. "
                f"Supported settings: {', '.join(sorted(supported))}."
            )

        if 'move_similarity_threshold' in kwargs:
            val = kwargs['move_similarity_threshold']
            if not isinstance(val, (int, float)) or val < 0.0 or val > 1.0:
                raise ValueError(f"move_similarity_threshold must be a float between 0.0 and 1.0, got {val!r}")

        if 'move_minimum_word_count' in kwargs:
            val = kwargs['move_minimum_word_count']
            if not isinstance(val, int) or val < 1:
                raise ValueError(f"move_minimum_word_count must be a positive integer, got {val!r}")

    def _build_command(self, author_tag, original_path, modified_path, target_path, **kwargs):
        self._validate_kwargs(kwargs)

        cmd = [self.extracted_binaries_path, original_path, modified_path, target_path,
               f'--author={author_tag}']

        for kwarg, flag in self._BOOL_FLAGS:
            if kwargs.get(kwarg):
                cmd.append(flag)

        for kwarg, neg_flag in self._NEG_FLAGS:
            if kwarg in kwargs and not kwargs[kwarg]:
                cmd.append(neg_flag)

        for kwarg, flag in self._VALUE_FLAGS:
            if kwarg in kwargs:
                cmd.append(f'{flag}={kwargs[kwarg]}')

        return cmd
