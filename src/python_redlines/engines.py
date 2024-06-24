import subprocess
import tempfile
import os
import platform
import logging
import zipfile
import tarfile
from pathlib import Path
from typing import Union, Tuple, Optional

from .__about__ import __version__

logger = logging.getLogger(__name__)


class XmlPowerToolsEngine(object):
    def __init__(self, target_path: Optional[str] = None):
        self.target_path = target_path
        self.extracted_binaries_path = self.__unzip_binary()

    def __unzip_binary(self):
        """
        Unzips the appropriate C# binary for the current platform.
        """
        base_path = os.path.dirname(__file__)
        binaries_path = os.path.join(base_path, 'dist')
        target_path = self.target_path if self.target_path else os.path.join(base_path, 'bin')

        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # Get the binary name and zip name based on the OS and architecture
        binary_name, zip_name = self.__get_binaries_info()

        # Check if the binary already exists. If not, extract it.
        full_binary_path = os.path.join(target_path, binary_name)

        if not os.path.exists(full_binary_path):
            zip_path = os.path.join(binaries_path, zip_name)
            self.__extract_binary(zip_path, target_path)

        return os.path.join(target_path, binary_name)

    def __extract_binary(self, zip_path: str, target_path: str):
        """
        Extracts the binary from the zip file based on the extension. Supports .zip and .tar.gz files
        :parameter
            zip_path: str - The path to the zip file
            target_path: str - The path to extract the binary to
        """
        if zip_path.endswith('.zip'):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_path)

        elif zip_path.endswith('.tar.gz'):
            with tarfile.open(zip_path, 'r:gz') as tar_ref:
                tar_ref.extractall(target_path)

    def __get_binaries_info(self):
        """
        Returns the binary name and zip name based on the OS and architecture
        :return
            binary_name: str - The name of the binary file
            zip_name: str - The name of the zip file
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
            zip_name = f"linux-{arch}-{__version__}.tar.gz"
            binary_name = f'linux-{arch}/redlines'

        elif os_name == 'windows':
            zip_name = f"win-{arch}-{__version__}.zip"
            binary_name = f'win-{arch}/redlines.exe'

        elif os_name == 'darwin':
            zip_name = f"osx-{arch}-{__version__}.tar.gz"
            binary_name = f'osx-{arch}/redlines'

        else:
            raise EnvironmentError("Unsupported OS")

        return binary_name, zip_name

    def run_redline(self, author_tag: str, original: Union[bytes, Path], modified: Union[bytes, Path]) \
            -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Runs the redlines binary. The 'original' and 'modified' arguments can be either bytes or file paths.
        Returns the redline output as bytes.
        """
        temp_files = []
        try:

            target_path = tempfile.NamedTemporaryFile(delete=False).name
            original_path = self._write_to_temp_file(original) if isinstance(original, bytes) else original
            modified_path = self._write_to_temp_file(modified) if isinstance(modified, bytes) else modified
            temp_files.extend([target_path, original_path, modified_path])

            command = [self.extracted_binaries_path, author_tag, original_path, modified_path, target_path]

            # Capture stdout and stderr
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            stdout_output = result.stdout if isinstance(result.stdout, str) and len(result.stdout) > 0 else None
            stderr_output = result.stderr if isinstance(result.stderr, str) and len(result.stderr) > 0 else None

            redline_output = Path(target_path).read_bytes()

            return redline_output, stdout_output, stderr_output

        finally:
            self._cleanup_temp_files(temp_files)

    def _cleanup_temp_files(self, temp_files):
        for file_path in temp_files:
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Error deleting temp file {file_path}: {e}")

    def _write_to_temp_file(self, data):
        """
        Writes bytes data to a temporary file and returns the file path.
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(data)
        temp_file.close()
        return temp_file.name
