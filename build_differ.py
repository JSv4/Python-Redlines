"""Build the C# redline engine binaries and package them for the wheels.

Each engine's binary ships in its own companion package; this script compiles
an engine for a given platform (.NET runtime identifier) and writes a single
flat archive into that package's ``_binaries/`` directory. A binary-package
wheel must contain exactly one such archive, so each invocation clears any
existing archives first.

Usage:
    python build_differ.py <rid> [<rid> ...]
    python build_differ.py --all

Valid RIDs: linux-x64, linux-arm64, win-x64, win-arm64, osx-x64, osx-arm64
"""
import os
import subprocess
import sys
import tarfile
import zipfile

RIDS = ["linux-x64", "linux-arm64", "win-x64", "win-arm64", "osx-x64", "osx-arm64"]

ENGINES = [
    {
        "name": "ooxmlpowertools",
        "csproj": os.path.join("csproj"),
        "csproj_file": os.path.join("csproj", "redlines.csproj"),
        "tfm": "net8.0",
        "binaries_dir": os.path.join(
            "packages", "ooxmlpowertools", "src",
            "python_redlines_ooxmlpowertools", "_binaries",
        ),
    },
    {
        "name": "docxodus",
        "csproj": os.path.join("docxodus", "tools", "redline"),
        "csproj_file": os.path.join("docxodus", "tools", "redline", "redline.csproj"),
        "tfm": "net10.0",
        "binaries_dir": os.path.join(
            "packages", "docxodus", "src",
            "python_redlines_docxodus", "_binaries",
        ),
    },
]


def run_command(command):
    """Run a shell command, streaming output. Raises on a non-zero exit code."""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in process.stdout:
        print(line.decode().rstrip())
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {process.returncode}: {command}")


def archive_name(rid):
    return f"{rid}.zip" if rid.startswith("win-") else f"{rid}.tar.gz"


def compress_dir(source_dir, target_file):
    """Compress the contents of source_dir (flat, no parent prefix) into target_file."""
    files = []
    for root, _, names in os.walk(source_dir):
        for name in names:
            full = os.path.join(root, name)
            files.append((full, os.path.relpath(full, source_dir)))

    if target_file.endswith(".tar.gz"):
        with tarfile.open(target_file, "w:gz") as tar:
            for full, arcname in files:
                tar.add(full, arcname=arcname)
    elif target_file.endswith(".zip"):
        with zipfile.ZipFile(target_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for full, arcname in files:
                zf.write(full, arcname=arcname)
    else:
        raise ValueError(f"Unsupported archive format: {target_file}")


def clean_binaries_dir(binaries_dir):
    """Remove existing archives so each wheel ships exactly one platform's binary."""
    for name in os.listdir(binaries_dir):
        if name.endswith((".tar.gz", ".zip")):
            os.remove(os.path.join(binaries_dir, name))


def build_engine_for_rid(engine, rid):
    csproj = engine["csproj"]
    print(f"[{engine['name']}] Building {rid} ...")
    run_command(f"dotnet publish {csproj} -c Release -r {rid} --self-contained")

    publish_dir = os.path.join(csproj, "bin", "Release", engine["tfm"], rid, "publish")
    if not os.path.isdir(publish_dir):
        raise RuntimeError(f"Expected publish output not found: {publish_dir}")

    target = os.path.join(engine["binaries_dir"], archive_name(rid))
    print(f"[{engine['name']}] Compressing -> {target}")
    compress_dir(publish_dir, target)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    rids = RIDS if argv[0] == "--all" else argv
    unknown = [r for r in rids if r not in RIDS]
    if unknown:
        print(f"ERROR: unknown RID(s): {', '.join(unknown)}")
        print(f"Valid RIDs: {', '.join(RIDS)}")
        return 1

    for engine in ENGINES:
        if not os.path.exists(engine["csproj_file"]):
            print(f"WARNING: {engine['name']} project not found at "
                  f"{engine['csproj_file']} — skipping.")
            if engine["name"] == "docxodus":
                print("Run 'git submodule update --init --recursive' to initialize "
                      "the Docxodus submodule.")
            continue

        os.makedirs(engine["binaries_dir"], exist_ok=True)
        clean_binaries_dir(engine["binaries_dir"])
        for rid in rids:
            build_engine_for_rid(engine, rid)

    print("Build complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
