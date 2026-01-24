"""
Build script for compiling comparison engine binaries.

This script builds self-contained .NET executables for multiple platforms
for both the Open-Xml-PowerTools and Docxodus comparison engines.
"""

import subprocess
import os
import sys
import tarfile
import zipfile
import argparse


# Engine configurations
ENGINES = {
    'openxml-powertools': {
        'csproj_path': './csproj',
        'binary_name': 'redlines',
        'dist_subdir': 'openxml-powertools',
    },
    'docxodus': {
        'csproj_path': './csproj-docxodus',
        'binary_name': 'redline',
        'dist_subdir': 'docxodus',
    },
}

# Platform configurations
PLATFORMS = [
    {'rid': 'linux-x64', 'archive_ext': '.tar.gz'},
    {'rid': 'linux-arm64', 'archive_ext': '.tar.gz'},
    {'rid': 'win-x64', 'archive_ext': '.zip'},
    {'rid': 'win-arm64', 'archive_ext': '.zip'},
    {'rid': 'osx-x64', 'archive_ext': '.tar.gz'},
    {'rid': 'osx-arm64', 'archive_ext': '.tar.gz'},
]


def get_version():
    """
    Extracts the version from the specified __about__.py file.
    """
    about = {}
    with open('./src/python_redlines/__about__.py') as f:
        exec(f.read(), about)
    return about['__version__']


def run_command(command, check=True):
    """
    Runs a shell command and prints its output.
    Returns True if successful, False otherwise.
    """
    print(f"Running: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    output_lines = []
    for line in process.stdout:
        decoded = line.decode().strip()
        print(decoded)
        output_lines.append(decoded)

    process.wait()
    if check and process.returncode != 0:
        print(f"Command failed with return code {process.returncode}")
        return False
    return True


def compress_files(source_dir, target_file):
    """
    Compresses files in the specified directory into a tar.gz or zip file.
    """
    print(f"Compressing {source_dir} to {target_file}")
    if target_file.endswith('.tar.gz'):
        with tarfile.open(target_file, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
    elif target_file.endswith('.zip'):
        with zipfile.ZipFile(target_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                    zipf.write(file_path, arcname)


def cleanup_old_builds(dist_dir, current_version):
    """
    Deletes any build files ending in .zip or .tar.gz in the dist_dir with a different version tag.
    """
    if not os.path.exists(dist_dir):
        return

    for file in os.listdir(dist_dir):
        if file.endswith(('.zip', '.tar.gz')) and current_version not in file:
            file_path = os.path.join(dist_dir, file)
            os.remove(file_path)
            print(f"Deleted old build file: {file}")


def build_engine(engine_name, engine_config, version, platforms=None):
    """
    Build binaries for a specific engine.

    Args:
        engine_name: Name of the engine
        engine_config: Configuration dict for the engine
        version: Version string
        platforms: Optional list of platforms to build (default: all)
    """
    csproj_path = engine_config['csproj_path']
    binary_name = engine_config['binary_name']
    dist_subdir = engine_config['dist_subdir']

    dist_dir = f"./src/python_redlines/dist/{dist_subdir}/"

    # Ensure dist directory exists
    os.makedirs(dist_dir, exist_ok=True)

    platforms_to_build = platforms or PLATFORMS

    print(f"\n{'='*60}")
    print(f"Building {engine_name} engine")
    print(f"{'='*60}\n")

    for platform_config in platforms_to_build:
        rid = platform_config['rid']
        archive_ext = platform_config['archive_ext']

        print(f"\nBuilding for {rid}...")

        # Build the binary
        cmd = f'dotnet publish {csproj_path} -c Release -r {rid} --self-contained'
        if not run_command(cmd, check=False):
            print(f"Warning: Build failed for {rid}")
            continue

        # Determine build output directory
        build_dir = f'{csproj_path}/bin/Release/net8.0/{rid}'

        # Check if build directory exists
        if not os.path.exists(build_dir):
            print(f"Warning: Build directory not found: {build_dir}")
            continue

        # Compress to archive
        archive_name = f"{rid}-{version}{archive_ext}"
        archive_path = os.path.join(dist_dir, archive_name)
        compress_files(build_dir, archive_path)
        print(f"Created: {archive_path}")

    # Cleanup old builds
    cleanup_old_builds(dist_dir, version)

    print(f"\n{engine_name} build complete.")


def main():
    parser = argparse.ArgumentParser(
        description='Build comparison engine binaries for multiple platforms.'
    )
    parser.add_argument(
        '--engine',
        choices=['all'] + list(ENGINES.keys()),
        default='all',
        help='Which engine to build (default: all)'
    )
    parser.add_argument(
        '--platform',
        choices=['all'] + [p['rid'] for p in PLATFORMS],
        default='all',
        help='Which platform to build for (default: all)'
    )

    args = parser.parse_args()

    version = get_version()
    print(f"Version: {version}")

    # Determine which platforms to build
    if args.platform == 'all':
        platforms = PLATFORMS
    else:
        platforms = [p for p in PLATFORMS if p['rid'] == args.platform]

    # Determine which engines to build
    if args.engine == 'all':
        engines_to_build = ENGINES.items()
    else:
        engines_to_build = [(args.engine, ENGINES[args.engine])]

    # Build each engine
    for engine_name, engine_config in engines_to_build:
        build_engine(engine_name, engine_config, version, platforms)

    print("\n" + "="*60)
    print("All builds complete.")
    print("="*60)


if __name__ == "__main__":
    main()
