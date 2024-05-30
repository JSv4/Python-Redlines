import subprocess
import os
import tarfile
import zipfile


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


def cleanup_old_builds(dist_dir, current_version):
    """
    Deletes any build files ending in .zip or .tar.gz in the dist_dir with a different version tag.
    """
    for file in os.listdir(dist_dir):
        if not file.endswith((f'{current_version}.zip', f'{current_version}.tar.gz', '.gitignore')):
            file_path = os.path.join(dist_dir, file)
            os.remove(file_path)
            print(f"Deleted old build file: {file}")


def main():
    version = get_version()
    print(f"Version: {version}")

    dist_dir = "./src/python_redlines/dist/"

    # Build for Linux x64
    print("Building for Linux x64...")
    run_command('dotnet publish ./csproj -c Release -r linux-x64 --self-contained')

    # Build for Linux ARM64
    print("Building for Linux ARM64...")
    run_command('dotnet publish ./csproj -c Release -r linux-arm64 --self-contained')

    # Build for Windows x64
    print("Building for Windows x64...")
    run_command('dotnet publish ./csproj -c Release -r win-x64 --self-contained')

    # Build for Windows ARM64
    print("Building for Windows ARM64...")
    run_command('dotnet publish ./csproj -c Release -r win-arm64 --self-contained')

    # Build for macOS x64
    print("Building for macOS x64...")
    run_command('dotnet publish ./csproj -c Release -r osx-x64 --self-contained')

    # Build for macOS ARM64
    print("Building for macOS ARM64...")
    run_command('dotnet publish ./csproj -c Release -r osx-arm64 --self-contained')

    # Compress the Linux x64 build
    linux_x64_build_dir = './csproj/bin/Release/net8.0/linux-x64'
    compress_files(linux_x64_build_dir, f"{dist_dir}/linux-x64-{version}.tar.gz")

    # Compress the Linux ARM64 build
    linux_arm64_build_dir = './csproj/bin/Release/net8.0/linux-arm64'
    compress_files(linux_arm64_build_dir, f"{dist_dir}/linux-arm64-{version}.tar.gz")

    # Compress the Windows x64 build
    windows_build_dir = './csproj/bin/Release/net8.0/win-x64'
    compress_files(windows_build_dir, f"{dist_dir}/win-x64-{version}.zip")

    # Compress the macOS x64 build
    macos_x64_build_dir = './csproj/bin/Release/net8.0/osx-x64'
    compress_files(macos_x64_build_dir, f"{dist_dir}/osx-x64-{version}.tar.gz")

    # Compress the macOS ARM64 build
    macos_arm64_build_dir = './csproj/bin/Release/net8.0/osx-arm64'
    compress_files(macos_arm64_build_dir, f"{dist_dir}/osx-arm64-{version}.tar.gz")

    cleanup_old_builds(dist_dir, version)

    print("Build and compression complete.")


if __name__ == "__main__":
    main()
