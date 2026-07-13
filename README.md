# Python-Redlines: Open-Source DOCX Comparison for Python

Open-source DOCX comparison tool to generate native Word tracked changes (redlines) in
Python — compare two Word files and get back a third document showing every insertion,
deletion, and (optionally) move as native Word tracked changes, **without any MS Word
dependency**.

Comparing `.docx` documents has long been dominated by commercial software, with cost
barriers and little integration flexibility. Python-Redlines brings open-source `.docx`
redlining to the Python ecosystem so legal hackers, hobbyists, and product teams can build
on it freely: two documents in, one redline out.

**🔗 Try it now: [redlines.opensource.legal](https://redlines.opensource.legal)** — a
live browser demo of the comparison engine, no install required. See also the
[full documentation site](https://jsv4.github.io/Python-Redlines/) and
[Python-Redlines vs. commercial alternatives](docs/alternatives.md) (Draftable API,
Cloudmersive, server-side MS Word automation).

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

That's the whole thing. The rest of this README covers the other engines, comparison
settings, and how the packages are built and distributed.

### 🆕 New in 0.3.0: `docxdiff`, an optional next-generation engine

Docxodus now ships a **second comparison algorithm** alongside the classic one. `docxdiff` is a
structure-aware engine that models the document as a tree rather than a stream of runs, so it
produces finer-grained redlines and tracks structural edits — table cell and row properties, section
properties, header and footer content — that the classic algorithm reports coarsely or not at all.

**It is off by default, so nothing about your existing calls changes engines.** Opting in is one
keyword argument:

```python
engine.run_redline("Reviewer", original, modified, engine="docxdiff")
```

**Please try it and tell us what you find.** It is new, and the two algorithms legitimately disagree
about how to describe the same edit — on this project's own test fixtures `docxdiff` reports 11
revisions where the classic engine reports 9. Neither is wrong; they segment the same changes
differently. Before adopting it for production redlines, compare its output against your own
documents. See [Choosing an engine](#choosing-an-engine) for the trade-offs and the settings it does
not support.

> **Note:** the default algorithm is unchanged, but the Docxodus binary behind it moved from v5.4.2
> to v7.0.0 in this release and carries upstream `WmlComparer` fixes of its own (header references,
> table anchoring). Redline output on the default path can therefore differ from 0.2.1 independently
> of this new flag. Diff a representative document if byte-level stability matters to you.

## Comparison Engines

Python-Redlines gives you **three ways to compare**, across two engine classes. `DocxodusEngine`
carries two interchangeable algorithms in one binary; `XmlPowerToolsEngine` is a separate, legacy
package.

| # | Choice | How to select it | Algorithm | Status |
|---|---|---|---|---|
| 1 | **Docxodus · `wmlcomparer`** | `DocxodusEngine()` | Modernized `WmlComparer` | ✅ **Default.** Stable, recommended |
| 2 | **Docxodus · `docxdiff`** | `DocxodusEngine()` + `engine="docxdiff"` | Structure-aware IR diff | 🆕 New in 0.3.0. Opt-in, seeking feedback |
| 3 | **Open-XML-PowerTools** | `XmlPowerToolsEngine()` | Original `WmlComparer` | 🗄️ Legacy. Upstream archived |

Choices 1 and 3 are cousins: both descend from Microsoft's `WmlComparer`, which is why choice 1 is
named `wmlcomparer`. Choice 1 is Docxodus's actively-maintained fork of it; choice 3 is the original,
unmaintained code. Choice 2 shares nothing with either but the output format — it is a new engine.

**If you are unsure, use choice 1.** It is the default and requires no arguments.

### 1. `DocxodusEngine` with `wmlcomparer` — the default

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

### 2. `DocxodusEngine` with `docxdiff` — new, opt-in

The same class and the same binary, selected per call. `docxdiff` models the document as an
intermediate representation, which lets it attribute a change to the exact paragraph, cell, row, or
section it touched.

```python
from python_redlines import DocxodusEngine

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline(
    "AuthorName", original_bytes, modified_bytes, engine="docxdiff",
)
```

Three settings do not exist for this algorithm and raise `ValueError` rather than being silently
ignored — see [Choosing an engine](#choosing-an-engine).

### 3. `XmlPowerToolsEngine` — legacy

Wraps the original [Open-XML-PowerTools](https://github.com/OpenXmlDev/Open-Xml-PowerTools) `WmlComparer`. This
engine remains available for backward compatibility and for users who prefer the original comparison behavior.

```python
from python_redlines import XmlPowerToolsEngine

engine = XmlPowerToolsEngine()
redline_bytes, stdout, stderr = engine.run_redline("AuthorName", original_bytes, modified_bytes)
```

> **Note:** Open-XML-PowerTools was archived by Microsoft and is no longer maintained. It uses an older
> version of the Open XML SDK. While it works for many purposes, Docxodus is the recommended engine going forward.

All three share the same call signature — `run_redline(author, original, modified)` returning
`(bytes, stdout, stderr)`. They differ in the class you instantiate, which keyword arguments they
accept, and their stdout format (see [Stdout Differences](#stdout-differences) below).

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
pip install python-redlines[all]                # both engine packages
```

Prebuilt wheels are available for Linux, macOS, and Windows (x64 and arm64); `pip`
selects the wheel matching your platform automatically. Instantiating an engine whose
companion package is not installed raises `EngineNotInstalledError` telling you which
extra to install.

### Use the Library

See the [Quick Start](#quick-start) above for a minimal example, or the
[quickstart guide](docs/quickstart.md) for a step-by-step walkthrough.

## Comparison Settings (DocxodusEngine only)

`DocxodusEngine` supports fine-grained control over the comparison via keyword arguments to
`run_redline()`. Which arguments are available depends on the algorithm you select — the second
table below is the authoritative matrix. `XmlPowerToolsEngine` accepts none of them.

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

### What each setting does

| Setting | Type | Default | Description |
|---|---|---|---|
| `engine` | str | `"wmlcomparer"` | Comparison algorithm: `"wmlcomparer"` or `"docxdiff"` |
| `detail_threshold` | float | `0.0` | Comparison granularity (0.0–1.0, lower = more detailed) |
| `case_insensitive` | bool | `False` | Ignore case differences |
| `detect_moves` | bool | `False` | Enable move detection |
| `simplify_move_markup` | bool | `False` | Convert moves to del/ins for Word compatibility |
| `move_similarity_threshold` | float | `0.8` | Jaccard threshold for move matching (0.0–1.0) |
| `move_minimum_word_count` | int | `3` | Minimum words for move detection |
| `detect_format_changes` | bool | `True` | Detect formatting-only changes |
| `conflate_spaces` | bool | `True` | Treat breaking/non-breaking spaces the same |
| `date_time` | str | now | Custom ISO 8601 timestamp for revisions |

### Which engine accepts which setting

| Setting | Docxodus · `wmlcomparer` | Docxodus · `docxdiff` | `XmlPowerToolsEngine` |
|---|:---:|:---:|:---:|
| `engine` | ✅ | ✅ | — ignored |
| `detail_threshold` | ✅ | ❌ `ValueError` | — ignored |
| `case_insensitive` | ✅ | ✅ | — ignored |
| `detect_moves` | ✅ | ✅ | — ignored |
| `simplify_move_markup` | ✅ | ❌ `ValueError` | — ignored |
| `move_similarity_threshold` | ✅ | ✅ | — ignored |
| `move_minimum_word_count` | ✅ | ✅ | — ignored |
| `detect_format_changes` | ✅ | ❌ `ValueError` | — ignored |
| `conflate_spaces` | ✅ | ✅ | — ignored |
| `date_time` | ✅ | ✅ | — ignored |

**❌ `ValueError`** — `docxdiff` has no equivalent of these three settings. The underlying CLI accepts
and silently discards them, so Python rejects them up front rather than let you believe a setting took
effect when it did not. The check is on the *keyword being present*, whatever its value: pass
`detect_format_changes=True` (its default) with `engine="docxdiff"` and you still get a `ValueError`.
Drop the keyword, or use `engine="wmlcomparer"`.

**— ignored** — `XmlPowerToolsEngine` silently discards every keyword argument, including `engine`.
This is long-standing behavior, not new. Passing `engine="docxdiff"` to it does nothing.

> **Warning:** (`wmlcomparer` only) Move detection can cause Word to display "unreadable content" warnings due to a known
> ID collision bug. When using `detect_moves=True`, always set `simplify_move_markup=True` as well.
> This converts move markup to regular del/ins (loses green move styling but ensures Word compatibility).

### Choosing an engine

`DocxodusEngine` wraps two comparison algorithms in one binary, selected per call:

```python
engine.run_redline("Reviewer", original, modified)                     # wmlcomparer (default)
engine.run_redline("Reviewer", original, modified, engine="docxdiff")  # opt in
```

| | Reach for `wmlcomparer` | Reach for `docxdiff` |
|---|---|---|
| **When** | You want the long-established algorithm | You want finer-grained, structure-aware redlines |
| **Maturity** | Years of production use | New in 0.3.0 — evaluate on your documents first |
| **Granularity knob** | `detail_threshold` tunes it | Not applicable; granularity is structural |
| **Moves** | Can be lowered to del/ins via `simplify_move_markup` | Rendered natively; cannot be lowered |
| **Structural edits** | Reported coarsely | Attributed to the paragraph, cell, row, or section |

**The two disagree about revision counts, and that is expected.** On this project's own fixtures,
`wmlcomparer` reports 9 revisions and `docxdiff` reports 11 for the same pair of documents. They
segment the same edits differently — a single reworded sentence may be one revision to one engine and
two to the other. Do not treat a changed count as a defect; do compare the rendered redline against
your own documents before switching.

**Move markup differs.** `docxdiff` renders moves natively and rejects `simplify_move_markup`, so the
Word-compatibility mitigation in the warning above is unavailable there. Whether Word's ID-collision
warning affects `docxdiff`'s native move markup is untested. If you need moves lowered to plain
del/ins for maximum Word compatibility, use `engine="wmlcomparer"` with `simplify_move_markup=True`.

**Feedback wanted.** `docxdiff` stays off by default precisely so that adopting 0.3.0 cannot change
your output. If you try it, please
[open an issue](https://github.com/JSv4/Python-Redlines/issues) with what you found — especially
documents where its redline reads worse than `wmlcomparer`'s.

## Architecture Overview

Both engine classes follow the same pattern: a Python wrapper class invokes a self-contained C# binary
via subprocess. `DocxodusEngine`'s two algorithms are one binary selected by a CLI flag, not two binaries.

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

## Python-Redlines vs. Commercial Alternatives

Looking for a `.docx` comparison tool and weighing it against a paid API? Short
version: Python-Redlines is a free, MIT-licensed, self-hosted library — your documents
never leave your process, there's no per-comparison fee, and it works fully offline.
The full write-up, including feature-by-feature tables, lives in
[docs/alternatives.md](docs/alternatives.md):

### Python-Redlines vs Draftable API

[Draftable](https://draftable.com/)'s document comparison API is metered per
comparison and requires sending your documents to a third-party cloud service.
Python-Redlines runs in-process with no per-call cost, no network dependency, and full
source availability (MIT license). See
[the detailed comparison](docs/alternatives.md#python-redlines-vs-draftable-api).

### Why choose Python-Redlines over Cloudmersive

[Cloudmersive](https://cloudmersive.com/)'s document comparison endpoint is one part
of a broader, metered, closed-source API. Python-Redlines has no API keys, no quotas,
and keeps document bytes local to your own infrastructure. See
[the detailed comparison](docs/alternatives.md#why-choose-python-redlines-over-cloudmersive).

### The problem with server-side MS Word automation

Driving a headless copy of MS Word via COM/Interop to generate tracked changes
violates Microsoft's Terms of Service for unattended server-side use and is
operationally fragile under concurrent load. Python-Redlines produces the same native
Word tracked-changes `.docx` output via a lightweight, self-contained comparison
engine — no Word installation, no TOS risk. See
[the full breakdown](docs/alternatives.md#the-problem-with-server-side-ms-word-automation).

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
