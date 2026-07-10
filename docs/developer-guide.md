# Developer Guide

## Prerequisites

- Python 3.9 or higher
- .NET 10.0 SDK (to compile the C# engine binaries). The Docxodus engine targets
  `net10.0`; the Open-XML-PowerTools engine still targets `net8.0` and the .NET 10 SDK
  builds both.
- `git` (the Docxodus engine is a submodule)

## Repository layout

This repository is a monorepo that publishes three PyPI packages, each with its own
`pyproject.toml` under `packages/`:

| Directory | PyPI name | Contents |
|---|---|---|
| `packages/core` | `python-redlines` | Pure-Python wrapper |
| `packages/ooxmlpowertools` | `python-redlines-ooxmlpowertools` | Open-XML-PowerTools engine binary |
| `packages/docxodus` | `python-redlines-docxodus` | Docxodus engine binary |

The repo root is not itself installable; its `pyproject.toml` only holds shared
pytest/coverage configuration.

## Setting up

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/JSv4/Python-Redlines
cd Python-Redlines

# Or, if already cloned:
git submodule update --init --recursive

# Build the engine binaries for your platform
python build_differ.py linux-x64        # or win-x64 / osx-arm64 / ...

# Install all three packages editable, plus pytest
pip install -e packages/core -e packages/ooxmlpowertools -e packages/docxodus pytest
```

## Building the C# binaries

`build_differ.py` compiles an engine for one or more .NET runtime identifiers (RIDs)
and writes a single flat archive into each binary package's `_binaries/` directory.

```bash
python build_differ.py linux-x64                 # one platform
python build_differ.py linux-x64 win-x64          # several
python build_differ.py --all                      # all six RIDs
```

Valid RIDs: `linux-x64`, `linux-arm64`, `win-x64`, `win-arm64`, `osx-x64`, `osx-arm64`.

Under the hood this runs `dotnet publish -c Release -r <rid> --self-contained` for
`csproj/` (Open-XML-PowerTools) and `docxodus/tools/redline/` (Docxodus), then
compresses each `publish/` output into `<rid>.tar.gz` (or `.zip` on Windows).

## Building wheels

A binary-package wheel must contain **exactly one** platform archive, so build one RID
at a time:

```bash
python build_differ.py linux-x64
python -m build --wheel packages/ooxmlpowertools
python -m build --wheel packages/docxodus
```

The core package is pure Python and platform-independent:

```bash
python -m build packages/core
```

Each binary package's `hatch_build.py` build hook detects the RID of the archive in
`_binaries/` and stamps the wheel with the matching platform tag (e.g.
`manylinux2014_x86_64`, `macosx_11_0_arm64`, `win_amd64`).

## Running tests

Run from the repository root (test fixtures use relative paths):

```bash
python -m pytest tests/
```

Tests require all three packages installed and the engine binaries built for the
current platform.

## Releasing

`.github/workflows/python-publish.yml` runs on a published GitHub release: it builds
per-platform engine wheels across three OS runners, builds the core sdist + wheel, and
publishes all three packages to PyPI. Bump the version in
`packages/core/src/python_redlines/__about__.py` only — the binary packages read it
from there, so all three always release in lockstep.
