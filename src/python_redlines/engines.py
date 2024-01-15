import subprocess
import tempfile
import os
import platform
import zipfile
from pathlib import Path
from typing import Union

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
            zip_name = f"linux-{arch}-{__version__}.zip"
        elif os_name == 'windows':
            zip_name = f"win-{arch}-{__version__}.zip"
        else:
            raise EnvironmentError("Unsupported OS")

        binary_name = 'redlines' if os_name == 'linux' else 'redlines.exe'
        zip_path = os.path.join(binaries_path, zip_name)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_path)

        return os.path.join(target_path, binary_name)

    def run_redline(self, author_tag: str, original: Union[bytes, Path], modified: Union[bytes, Path]) -> bytes:
        """
        Runs the redlines binary. The 'original' and 'modified' arguments can be either bytes or file paths.
        Returns the redline output as bytes.
        """
        with tempfile.NamedTemporaryFile(delete=False) as redline_output_file:
            original_path = self._write_to_temp_file(original) if isinstance(original, bytes) else original
            modified_path = self._write_to_temp_file(modified) if isinstance(modified, bytes) else modified

            command = [self.extracted_binaries_path, author_tag, original_path, modified_path, redline_output_file.name]
            subprocess.run(command, check=True)

            redline_output_file.seek(0)
            redline_output = redline_output_file.read()

        return redline_output

    def _write_to_temp_file(self, data):
        """
        Writes bytes data to a temporary file and returns the file path.
        """
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data)
            return temp_file.name

    def _ensure_temp_file(self, data):
        """
        Ensures the data is in a file. If data is bytes, it writes it to a temp file and returns the file path.
        Otherwise, it returns the data as is, assuming it's a file path.
        """
        if isinstance(data, bytes):
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(data)
            temp_file.close()
            return temp_file.name
        else:
            return data
