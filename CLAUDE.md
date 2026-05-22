# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-Redlines generates `.docx` redline/tracked-changes documents by comparing two Word files. A pure-Python wrapper drives compiled C# (.NET 8) engine binaries; the Python layer handles platform detection, binary extraction, temp file management, and subprocess execution.

Two comparison engines are available:
- **XmlPowerToolsEngine** — wraps Open-XML-PowerTools WmlComparer (original engine)
- **DocxodusEngine** — wraps Docxodus, a modernized .NET 8.0 fork with better move detection

## Monorepo structure — three published packages

This repo publishes **three** PyPI packages, each with its own `pyproject.toml` under `packages/`:

| Directory | PyPI name | Contents | Wheel |
|---|---|---|---|
| `packages/core` | `python-redlines` | Pure-Python wrapper (`engines.py`) | `py3-none-any` |
| `packages/ooxmlpowertools` | `python-redlines-ooxmlpowertools` | Open-XML-PowerTools binary | per-platform |
| `packages/docxodus` | `python-redlines-docxodus` | Docxodus binary | per-platform |

Engine binaries are **optional dependencies**. Users install an engine via an extra:
`pip install python-redlines[docxodus]`, `[ooxmlpowertools]`, or `[all]`. The core
package has no binaries; each binary package ships one platform's compiled binary as a
prebuilt wheel, so end users never compile anything.

The repo root is **not** an installable project — its `pyproject.toml` holds only
shared pytest/coverage config.

## Commands

```bash
# Initialize the Docxodus submodule (required before building its engine)
git submodule update --init --recursive

# Build engine binaries for one or more platforms (requires .NET 8.0 SDK).
# RIDs: linux-x64 linux-arm64 win-x64 win-arm64 osx-x64 osx-arm64
python build_differ.py linux-x64
python build_differ.py --all

# Install all three packages editable for development
pip install -e packages/core -e packages/ooxmlpowertools -e packages/docxodus pytest

# Run tests (from repo root)
python -m pytest tests/
python -m pytest tests/test_openxml_differ.py::test_run_redlines_with_real_files

# Build a package wheel
python -m build packages/core
python -m build --wheel packages/docxodus      # needs an archive in _binaries/ first
```

## Architecture

1. **Core Python layer** (`packages/core/src/python_redlines/engines.py`):
   - `BaseEngine` — locates the engine binary in its companion package via
     `importlib.resources`, extracts the platform archive once into a writable
     user cache dir (`platformdirs.user_cache_dir`), and runs it via subprocess.
   - `XmlPowerToolsEngine` / `DocxodusEngine` — subclasses declaring `BINARY_PACKAGE`,
     `BINARY_BASE_NAME`, and `EXTRA_NAME`.
   - `EngineNotInstalledError` — raised on instantiation if the companion binary
     package is missing, with the `pip install` command to fix it.

   Both engines expose `run_redline(author_tag, original, modified, **kwargs)`.
   `DocxodusEngine` overrides `_build_command()` to translate kwargs (e.g. `detect_moves`,
   `detail_threshold`) into CLI flags. `XmlPowerToolsEngine` uses the legacy
   4-positional-arg format and ignores kwargs.

2. **Binary packages** ship one platform archive under
   `src/<pkg>/_binaries/<rid>.tar.gz` (or `.zip` for Windows). The archive is
   gitignored; CI builds it. The hatchling build hook `hatch_build.py` reads which
   RID archive is present and stamps the wheel's platform tag accordingly.

3. **C# sources**:
   - `csproj/Program.cs` — Open-XML-PowerTools CLI tool
   - `docxodus/tools/redline/Program.cs` — Docxodus CLI tool (git submodule)

   `build_differ.py` compiles an engine for a given RID with `dotnet publish` and
   writes a single flat archive into the corresponding binary package's `_binaries/`.

## Build & release flow

- A binary-package wheel must contain **exactly one** platform archive. Each
  `build_differ.py <rid>` invocation clears old archives, so build one RID, build
  the wheel, repeat.
- `.github/workflows/ci.yml` — tests on each OS (native RID) + builds all wheels.
- `.github/workflows/python-publish.yml` — on release, builds per-platform engine
  wheels across 3 OS runners, the core sdist+wheel, and publishes all three packages.

## Version management

`packages/core/src/python_redlines/__about__.py` is the single source of truth.
The two binary packages read it via `[tool.hatch.version] path = "../core/..."`,
so all three always share one version. Bump only that file.

## Testing Notes

Tests live in repo-root `tests/` and must be run from the repo root (fixtures use
relative paths like `tests/fixtures/original.docx`). They require all three packages
installed and the binaries built for the current platform. The XmlPowerToolsEngine
integration test validates exactly 9 revisions on the fixture documents.

## Stdout Format Differences

- **XmlPowerToolsEngine**: `"Revisions found: 9"`
- **DocxodusEngine**: `"Redline complete: 9 revision(s) found"`
