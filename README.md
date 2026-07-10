# Python-Redlines: Docx Redlines (Tracked Changes) for the Python Ecosystem

Generate tracked-change "redline" `.docx` documents from Python — compare two Word files
and get back a third document showing every insertion, deletion, and (optionally) move as
native Word tracked changes.

Comparing `.docx` documents has long been dominated by commercial software, with cost
barriers and little integration flexibility. Python-Redlines brings open-source `.docx`
redlining to the Python ecosystem so legal hackers, hobbyists, and product teams can build
on it freely: two documents in, one redline out.

## Quick Start

The **default engine is [Docxodus](https://github.com/JSv4/Docxodus)** — a modernized,
actively-maintained .NET 10 comparison engine (detailed below). Install it and you're
running; the engine binary is prebuilt and embedded in the wheel, so there is **no .NET
SDK to install and nothing to compile**:

```commandline
pip install python-redlines[docxodus]
```

```python
from python_redlines import DocxodusEngine

with open("original.docx", "rb") as f:
    original = f.read()
with open("modified.docx", "rb") as f:
    modified = f.read()

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline("Reviewer", original, modified)

with open("redline.docx", "wb") as f:
    f.write(redline_bytes)
```

That's the whole thing. The rest of this README covers the second (legacy) engine,
comparison settings, and how the packages are built and distributed.

## Comparison Engines

Python-Redlines provides **two comparison engines**. `DocxodusEngine` is the default and
recommended choice; `XmlPowerToolsEngine` remains available as a legacy option.

### `DocxodusEngine` — Default (Recommended)

**[Docxodus](https://github.com/JSv4/Docxodus)** is a modernized .NET 10.0 fork of Open-XML-PowerTools with
significant improvements:

- **Move detection** — identifies content that was moved rather than deleted and re-inserted
- **Format change detection** — detects changes to bold, italic, font size, and other run properties
- **Better table handling** — LCS-based row matching for large tables
- **Actively maintained** — regular bug fixes and new features
- **Open XML SDK 3.x compatible** — uses the latest SDK version

```python
from python_redlines import DocxodusEngine

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline("AuthorName", original_bytes, modified_bytes)
```

### `XmlPowerToolsEngine` — Legacy

Wraps the original [Open-XML-PowerTools](https://github.com/OpenXmlDev/Open-Xml-PowerTools) `WmlComparer`. This
engine remains available for backward compatibility and for users who prefer the original comparison behavior.

```python
from python_redlines import XmlPowerToolsEngine

engine = XmlPowerToolsEngine()
redline_bytes, stdout, stderr = engine.run_redline("AuthorName", original_bytes, modified_bytes)
```

> **Note:** Open-XML-PowerTools was archived by Microsoft and is no longer maintained. It uses an older
> version of the Open XML SDK. While it works for many purposes, Docxodus is the recommended engine going forward.

Both engines share the same API — the only difference is the class you instantiate and the stdout format
(see [Stdout Differences](#stdout-differences) below).

## Getting Started

### Install the Library

The comparison engines are compiled .NET binaries, but they are **prebuilt and embedded
in the published wheels** — you do not need the .NET SDK (or any local compilation) to
install or use `python-redlines`.

Each engine ships in its own optional companion package. Install the engine(s) you need
as extras:

```commandline
pip install python-redlines[docxodus]          # Docxodus engine
pip install python-redlines[ooxmlpowertools]    # Open-XML-PowerTools engine
pip install python-redlines[all]                # both engines
```

Prebuilt wheels are available for Linux, macOS, and Windows (x64 and arm64); `pip`
selects the wheel matching your platform automatically. Instantiating an engine whose
companion package is not installed raises `EngineNotInstalledError` telling you which
extra to install.

### Use the Library

See the [Quick Start](#quick-start) above for a minimal example, or the
[quickstart guide](docs/quickstart.md) for a step-by-step walkthrough.

## Comparison Settings (DocxodusEngine only)

`DocxodusEngine` supports fine-grained control over the comparison via keyword arguments to `run_redline()`:

```python
from python_redlines import DocxodusEngine

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline(
    "Reviewer", original, modified,
    detect_moves=True,
    simplify_move_markup=True,
    detail_threshold=0.3,
    case_insensitive=True,
)
```

| Setting | Type | Default | Description |
|---|---|---|---|
| `engine` | str | `"wmlcomparer"` | Comparison algorithm: `"wmlcomparer"` or `"docxdiff"` |
| `detail_threshold` | float | 0.0 | Comparison granularity (0.0–1.0, lower = more detailed) |
| `case_insensitive` | bool | False | Ignore case differences |
| `detect_moves` | bool | False | Enable move detection |
| `simplify_move_markup` | bool | False | Convert moves to del/ins for Word compatibility |
| `move_similarity_threshold` | float | 0.8 | Jaccard threshold for move matching (0.0–1.0) |
| `move_minimum_word_count` | int | 3 | Minimum words for move detection |
| `detect_format_changes` | bool | True | Detect formatting-only changes |
| `conflate_spaces` | bool | True | Treat breaking/non-breaking spaces the same |
| `date_time` | str | now | Custom ISO 8601 timestamp for revisions |

> **Warning:** Move detection can cause Word to display "unreadable content" warnings due to a known
> ID collision bug. When using `detect_moves=True`, always set `simplify_move_markup=True` as well.
> This converts move markup to regular del/ins (loses green move styling but ensures Word compatibility).

> **Note:** These settings are only available on `DocxodusEngine`. `XmlPowerToolsEngine` ignores
> extra keyword arguments.

### Choosing an engine

`DocxodusEngine` wraps two comparison algorithms in one binary. `wmlcomparer` is the default
and is the lineage inherited from Open-XML-PowerTools. `docxdiff` is Docxodus's newer
structure-aware IR engine, which produces finer-grained markup — on the same pair of documents
it reports 11 revisions where `wmlcomparer` reports 9.

```python
engine.run_redline("Reviewer", original, modified, engine="docxdiff")
```

`docxdiff` does not implement `detail_threshold`, `simplify_move_markup`, or
`detect_format_changes`. Passing any of them alongside `engine="docxdiff"` raises `ValueError`
rather than silently ignoring them. It does honour `detect_moves`, `case_insensitive`,
`conflate_spaces`, `move_similarity_threshold`, `move_minimum_word_count`, and `date_time`.

## Architecture Overview

Both engines follow the same pattern: a Python wrapper class invokes a self-contained C# binary via subprocess.

The repository is a **monorepo of three separately-published packages**:

| Package | PyPI name | Contents |
|---|---|---|
| `packages/core` | `python-redlines` | Pure-Python wrapper; no binaries |
| `packages/ooxmlpowertools` | `python-redlines-ooxmlpowertools` | Open-XML-PowerTools engine binary |
| `packages/docxodus` | `python-redlines-docxodus` | Docxodus engine binary |

The core package's `[docxodus]` / `[ooxmlpowertools]` / `[all]` extras pull in the
binary packages. Each binary package is published as **per-platform wheels** (Linux,
macOS, Windows × x64/arm64), each embedding one prebuilt, self-contained .NET binary.

```
python-redlines/
│
├── csproj/                          # XmlPowerTools C# source
├── docxodus/                        # Docxodus git submodule (tools/redline/)
│
├── packages/
│   ├── core/                        # -> python-redlines
│   │   └── src/python_redlines/     #    engines.py, __init__.py, __about__.py
│   ├── ooxmlpowertools/             # -> python-redlines-ooxmlpowertools
│   │   ├── hatch_build.py           #    stamps the wheel platform tag
│   │   └── src/python_redlines_ooxmlpowertools/_binaries/
│   └── docxodus/                    # -> python-redlines-docxodus
│       ├── hatch_build.py
│       └── src/python_redlines_docxodus/_binaries/
│
├── tests/                           # integration + contract tests (run from root)
├── build_differ.py                  # compiles engines into each package's _binaries/
└── pyproject.toml                   # shared pytest/coverage config only
```

At runtime the wrapper finds its companion binary package via `importlib.resources`,
extracts the platform archive once into the user cache directory, and runs it.

### Stdout Differences

The engines produce slightly different stdout messages:

| Engine | Example stdout |
|---|---|
| `XmlPowerToolsEngine` | `Revisions found: 9` |
| `DocxodusEngine` (default / `engine="wmlcomparer"`) | `Redline complete: 9 revision(s) found` |
| `DocxodusEngine` (`engine="docxdiff"`) | `Redline complete: 11 revision(s) found` |

The revision counts differ between the two Docxodus engines because the algorithms differ,
not because either is wrong.

## Development

### Prerequisites

- Python 3.9+
- .NET 10.0 SDK (only for building the engine binaries locally). Install with
  `apt install dotnet-sdk-10.0`, or `curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0`.
  A .NET 8 SDK can no longer build the Docxodus engine, which targets `net10.0`.

### Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/JSv4/Python-Redlines
cd Python-Redlines

# If you already cloned without submodules
git submodule update --init --recursive

# Build the engine binaries for your platform (RIDs: linux-x64, win-x64, osx-arm64, ...)
python build_differ.py linux-x64

# Install all three packages editable
pip install -e packages/core -e packages/ooxmlpowertools -e packages/docxodus pytest
```

### Commands

```bash
# Run tests (from the repo root)
python -m pytest tests/

# Run a single test
python -m pytest tests/test_openxml_differ.py::test_run_redlines_with_real_files

# Build engine binaries for one or more platforms
python build_differ.py linux-x64 win-x64
python build_differ.py --all

# Build a package wheel
python -m build packages/core
```

### Detailed Dev Setup

If you want to contribute to the library or want to dive into some of the C# packaging architecture, go to our
[developer guide](docs/developer-guide.md).

## Additional Information

- **Contributing**: Contributions to the project should follow the established coding and documentation standards.
- **Issues and Support**: For issues, feature requests, or support, please use the project's issue tracker on GitHub.

## License

MIT
