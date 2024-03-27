import subprocess
import tempfile
import os
import platform
import zipfile
import tarfile
from pathlib import Path
from typing import Union, Tuple, Optional

from .__about__ import __version__


class XmlPowerToolsEngine(object):
    def __init__(self):
        self.extracted_binaries_path = self._unzip_binary()

    def _unzip_binary(self):
        """
        Unzips the appropriate C# binary for the current platform.
        """
        base_path = os.path.dirname(__file__)
        binaries_path = os.path.join(base_path, 'dist')
        target_path = os.path.join(base_path, 'bin')

        if not os.path.exists(target_path):
            os.makedirs(target_path)

        os_name = platform.system().lower()
        arch = 'x64'  # Assuming x64 architecture

        if os_name == 'linux':
            zip_name = f"linux-{arch}-{__version__}.tar.gz"
            binary_name = 'linux-x64/redlines'
            zip_path = os.path.join(binaries_path, zip_name)
            if not os.path.exists(zip_path):
                with tarfile.open(zip_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(target_path)

        elif os_name == 'windows':
            zip_name = f"win-{arch}-{__version__}.zip"
            binary_name = 'win-x64/redlines.exe'
            zip_path = os.path.join(binaries_path, zip_name)
            if not os.path.exists(zip_path):
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(target_path)

        elif os_name == 'darwin':
            zip_name = f"osx-{arch}-{__version__}.tar.gz"
            binary_name = 'osx-x64/redlines'
            zip_path = os.path.join(binaries_path, zip_name)
            if not os.path.exists(zip_path):
                with tarfile.open(zip_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(target_path)

        else:
            raise EnvironmentError("Unsupported OS")

        return os.path.join(target_path, binary_name)

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
