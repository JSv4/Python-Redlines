# Python-Redlines: Docx Redlines (Tracked Changes) for the Python Ecosystem

## Project Goal - Democratizing DOCX Comparisons

The main goal of this project is to address the significant gap in the open-source ecosystem around `.docx` document
comparison tools. Currently, the process of comparing and generating redline documents (documents that highlight
changes between versions) is complex and largely dominated by commercial software. These
tools, while effective, often come with cost barriers and limitations in terms of accessibility and integration
flexibility.

`Python-redlines` aims to democratize the ability to run tracked change redlines for .docx, providing the
open-source community with a tool to create `.docx` redlines without the need for commercial software. This will let
more legal hackers and hobbyist innovators experiment and create tooling for enterprise and legal.

## Comparison Engines

Python-Redlines ships with **two comparison engines** — choose the one that best fits your needs:

### `DocxodusEngine` — Recommended

**[Docxodus](https://github.com/JSv4/Docxodus)** is a modernized .NET 8.0 fork of Open-XML-PowerTools with
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

```commandline
pip install git+https://github.com/JSv4/Python-Redlines
```

You can add this as a dependency like so:

```requirements
python_redlines @ git+https://github.com/JSv4/Python-Redlines@v0.0.4
```

### Use the Library

If you just want to use the tool, jump into our [quickstart guide](docs/quickstart.md).

### Quick Example

```python
from python_redlines import DocxodusEngine

# Load your documents as bytes
with open("original.docx", "rb") as f:
    original = f.read()
with open("modified.docx", "rb") as f:
    modified = f.read()

# Generate a redline document
engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline("Reviewer", original, modified)

# Save the result
with open("redline.docx", "wb") as f:
    f.write(redline_bytes)

print(stdout)  # e.g. "Redline complete: 9 revision(s) found"
```

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

## Architecture Overview

Both engines follow the same pattern: a Python wrapper class invokes a self-contained C# binary via subprocess.
The binary takes four arguments: `<author_tag> <original.docx> <modified.docx> <output.docx>`.

```
python-redlines/
│
├── csproj/                          # XmlPowerTools C# source
│   ├── Program.cs
│   └── redlines.csproj
│
├── docxodus/                        # Docxodus git submodule
│   └── tools/redline/
│       ├── Program.cs
│       └── redline.csproj
│
├── src/
│   └── python_redlines/
│       ├── engines.py               # BaseEngine, XmlPowerToolsEngine, DocxodusEngine
│       ├── dist/                    # XmlPowerTools compressed binaries
│       ├── dist_docxodus/           # Docxodus compressed binaries
│       ├── bin/                     # XmlPowerTools extracted binaries (runtime)
│       ├── bin_docxodus/            # Docxodus extracted binaries (runtime)
│       ├── __about__.py
│       └── __init__.py
│
├── tests/
│   ├── fixtures/
│   ├── test_openxml_differ.py       # XmlPowerTools integration test
│   ├── test_docxodus_engine.py      # Docxodus integration test
│   └── test_engine_contract.py      # Shared contract tests for both engines
│
├── build_differ.py                  # Builds both engines for all platforms
├── pyproject.toml
└── README.md
```

Pre-compiled binaries for 6 platform targets (linux/win/osx x x64/arm64) are bundled in the wheel for each engine.
On first use, the appropriate binary is extracted and cached.

### Stdout Differences

The two engines produce slightly different stdout messages:

| Engine | Example stdout |
|---|---|
| `XmlPowerToolsEngine` | `Revisions found: 9` |
| `DocxodusEngine` | `Redline complete: 9 revision(s) found` |

## Development

### Prerequisites

- Python 3.8+
- .NET 8.0 SDK (for building C# binaries)

### Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/JSv4/Python-Redlines
cd Python-Redlines

# If you already cloned without submodules
git submodule update --init --recursive
```

### Commands

```bash
# Run tests
hatch run test

# Run a single test
hatch run test tests/test_openxml_differ.py::test_run_redlines_with_real_files

# Build C# binaries for all platforms
hatch run build

# Build Python package
hatch build
```

### Detailed Dev Setup

If you want to contribute to the library or want to dive into some of the C# packaging architecture, go to our
[developer guide](docs/developer-guide.md).

## Additional Information

- **Contributing**: Contributions to the project should follow the established coding and documentation standards.
- **Issues and Support**: For issues, feature requests, or support, please use the project's issue tracker on GitHub.

## License

MIT
