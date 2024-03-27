import subprocess
import os
import tarfile
import zipfile
import sys


def get_version():
    """
    Extracts the version from the specified __about__.py file.
    """
    about = {}
    with open('./src/python_redlines/__about__.py') as f:
        exec(f.read(), about)
    return about['__version__']


def run_command(command):
    """
    Runs a shell command and prints its output.
    """
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in process.stdout:
        print(line.decode().strip())


def compress_files(source_dir, target_file):
    """
    Compresses files in the specified directory into a tar.gz or zip file.
    """
    if target_file.endswith('.tar.gz'):
        with tarfile.open(target_file, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
    elif target_file.endswith('.zip'):
        with zipfile.ZipFile(target_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    zipf.write(os.path.join(root, file),
                               os.path.relpath(os.path.join(root, file),
                                               os.path.join(source_dir, '..')))


def main():
    version = get_version()
    print(f"Version: {version}")

    # Build for Linux
    print("Building for Linux...")
    run_command('dotnet publish ./csproj -c Release -r linux-x64 --self-contained')

    # Build for Windows
    print("Building for Windows...")
    run_command('dotnet publish ./csproj -c Release -r win-x64 --self-contained')

    # Build for macOS
    print("Building for macOS...")
    run_command('dotnet publish ./csproj -c Release -r osx-x64 --self-contained')

    # Compress the Linux build
    linux_build_dir = './csproj/bin/Release/net8.0/linux-x64'
    compress_files(linux_build_dir, f"./dist/linux-x64-{version}.tar.gz")

    # Compress the Windows build
    windows_build_dir = './csproj/bin/Release/net8.0/win-x64'
    compress_files(windows_build_dir, f"./dist/win-x64-{version}.zip")

    # Compress the macOS build
    macos_build_dir = './csproj/bin/Release/net8.0/osx-x64'
    compress_files(macos_build_dir, f"./dist/osx-x64-{version}.tar.gz")

    print("Build and compression complete.")


if __name__ == "__main__":
    main()
