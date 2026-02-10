import subprocess
import os
import tarfile
import zipfile


RIDS = [
    ("linux-x64", ".tar.gz"),
    ("linux-arm64", ".tar.gz"),
    ("win-x64", ".zip"),
    ("win-arm64", ".zip"),
    ("osx-x64", ".tar.gz"),
    ("osx-arm64", ".tar.gz"),
]


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


def build_engine(csproj_path, dist_dir, version):
    """
    Builds a C# engine for all platform targets, compresses the output, and cleans up old builds.

    :param csproj_path: Path to the .csproj directory (e.g. './csproj' or './docxodus/tools/redline')
    :param dist_dir: Path to the distribution directory for compressed binaries
    :param version: Version string for archive naming
    """
    # Build for each RID
    for rid, _ in RIDS:
        print(f"Building {csproj_path} for {rid}...")
        run_command(f'dotnet publish {csproj_path} -c Release -r {rid} --self-contained')

    # Determine the build output base directory
    # dotnet publish outputs to <csproj_path>/bin/Release/net8.0/<rid>
    build_base = os.path.join(csproj_path, 'bin', 'Release', 'net8.0')

    # Compress each build
    for rid, ext in RIDS:
        build_dir = os.path.join(build_base, rid)
        archive_path = os.path.join(dist_dir, f"{rid}-{version}{ext}")
        print(f"Compressing {rid} to {archive_path}...")
        compress_files(build_dir, archive_path)

    cleanup_old_builds(dist_dir, version)


def main():
    version = get_version()
    print(f"Version: {version}")

    # Build the XmlPowerTools engine (original)
    build_engine('./csproj', './src/python_redlines/dist/', version)

    # Build the Docxodus engine (if submodule is available)
    docxodus_csproj = './docxodus/tools/redline'
    if os.path.exists(os.path.join(docxodus_csproj, 'redline.csproj')):
        build_engine(docxodus_csproj, './src/python_redlines/dist_docxodus/', version)
    else:
        print("WARNING: Docxodus submodule not found at docxodus/tools/redline/redline.csproj — skipping Docxodus build.")
        print("Run 'git submodule update --init --recursive' to initialize the submodule.")

    print("Build and compression complete.")


if __name__ == "__main__":
    main()
