# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-Redlines is a Python wrapper around compiled C# binaries that generate `.docx` redline/tracked-changes documents by comparing two Word files. The Python layer handles platform detection, binary extraction, temp file management, and subprocess execution.

Two comparison engines are available:
- **XmlPowerToolsEngine** — wraps Open-XML-PowerTools WmlComparer (original engine)
- **DocxodusEngine** — wraps Docxodus, a modernized .NET 8.0 fork with better move detection

## Commands

```bash
# Run tests
hatch run test

# Run a single test
hatch run test tests/test_openxml_differ.py::test_run_redlines_with_real_files

# Run tests with coverage
hatch run cov

# Type checking
hatch run types:check

# Build C# binaries for all platforms (requires .NET 8.0 SDK)
hatch run build

# Build Python package (triggers C# build via custom hook)
hatch build

# Initialize Docxodus submodule (required before building)
git submodule update --init --recursive
```

## Architecture

The system uses a two-layer wrapper pattern with a shared base class:

1. **Python layer** (`src/python_redlines/engines.py`):
   - `BaseEngine` — shared logic for binary extraction, subprocess invocation, and temp file management
   - `XmlPowerToolsEngine(BaseEngine)` — sets constants for the Open-XML-PowerTools binary (`dist/`, `bin/`, `redlines`)
   - `DocxodusEngine(BaseEngine)` — sets constants for the Docxodus binary (`dist_docxodus/`, `bin_docxodus/`, `redline`)

   Both engines expose `run_redline(author_tag, original, modified, **kwargs)`. `DocxodusEngine` overrides `_build_command()` to translate kwargs (e.g. `detect_moves`, `detail_threshold`) into CLI flags for the Docxodus binary. `XmlPowerToolsEngine` uses the legacy 4-positional-arg format and ignores kwargs.

2. **C# binaries**:
   - `csproj/Program.cs` — Open-XML-PowerTools CLI tool
   - `docxodus/tools/redline/Program.cs` — Docxodus CLI tool (git submodule)

Pre-compiled binaries for 6 platform targets (linux/win/osx x x64/arm64) are stored as archives in `src/python_redlines/dist/` and `src/python_redlines/dist_docxodus/`, included in the wheel. The build script `build_differ.py` compiles both engines using `dotnet publish`.

## Key Files

- `src/python_redlines/engines.py` — BaseEngine, XmlPowerToolsEngine, and DocxodusEngine classes
- `src/python_redlines/__init__.py` — Exports all engine classes
- `src/python_redlines/__about__.py` — Single source of truth for package version
- `csproj/Program.cs` — Open-XML-PowerTools C# comparison utility
- `docxodus/` — Docxodus git submodule (tools/redline/ contains the CLI)
- `build_differ.py` — Cross-platform C# build orchestration for both engines
- `hatch_run_build_hook.py` — Hatch build hook that triggers C# compilation
- `tests/fixtures/` — Test `.docx` files (original, modified, expected_redline)

## Testing Notes

Tests must be run from the project root (fixtures use relative paths like `tests/fixtures/original.docx`). The XmlPowerToolsEngine integration test validates that comparing the fixture documents produces exactly 9 revisions. Docxodus uses a different stdout format (`"revision(s) found"` vs `"Revisions found: 9"`).

## Stdout Format Differences

- **XmlPowerToolsEngine**: `"Revisions found: 9"`
- **DocxodusEngine**: `"Redline complete: 9 revision(s) found"`
