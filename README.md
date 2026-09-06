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

### ⚠️ Breaking in 1.0.0: `WmlComparer` is gone; DocxDiff is the only algorithm

Docxodus v11.0.0 **removed `WmlComparer`**, the algorithm this library ran by default for its
entire life. `DocxDiff` — introduced as an opt-in in 0.3.0, upstream's default since v8.0.0, and
now mature — replaces it. There is no flag to bring the old engine back: it no longer exists in
the binary.

If you never passed comparison settings, **your code needs no change**. Output will differ, because
the algorithm differs; see [Upgrading to 1.0.0](#upgrading-to-100).

Three keyword arguments were removed and now raise `ValueError`:

```python
engine.run_redline("Reviewer", original, modified, engine="docxdiff")          # ValueError
engine.run_redline("Reviewer", original, modified, detail_threshold=0.3)       # ValueError
engine.run_redline("Reviewer", original, modified, simplify_move_markup=True)  # ValueError
```

They raise rather than being ignored on purpose. Two of them are still *accepted* by the
underlying CLI, which warns and does nothing; `--engine` is rejected outright. Silently dropping
`engine="wmlcomparer"` would have handed you DocxDiff output while you believed you had selected
something else — a wrong answer, not a breaking change. Unknown keyword arguments are rejected on
the same reasoning: a typo used to vanish in silence.

## GitHub Action

This repository doubles as a GitHub Action, so a repo that versions `.docx` files can get a
redline of every Word document a pull request changes — as a reviewable workflow artifact —
without anyone opening Word ([#12](https://github.com/JSv4/Python-Redlines/issues/12)).

```yaml
name: DOCX redlines
on: pull_request

permissions:
  contents: read

jobs:
  redline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # both sides of the comparison must be fetchable
      - uses: JSv4/Python-Redlines@main
```

That's the whole workflow. For every `.docx` file the pull request modifies (or renames), the
action extracts the base and head versions from git, runs the redline engine, and:

- writes `<output-dir>/<path>/<name>.redline.docx` with native Word tracked changes,
- uploads the output directory as a workflow artifact,
- posts a job-summary table (file, revision count, output paths),
- when HTML previews are on, also writes a browser-viewable `.redline.html` per file, rendered
  with the [Docxodus](https://github.com/JSv4/Docxodus) `Docx2Html` tool's `--track-changes`
  mode so insertions/deletions/moves show as `ins`/`del` markup.

You can also compare an explicit pair of files instead of auto-detecting:

```yaml
      - uses: JSv4/Python-Redlines@main
        with:
          original: docs/contract-v1.docx
          modified: docs/contract-v2.docx
          author: Legal Review
```

### Action inputs

| Input | Default | Purpose |
|---|---|---|
| `original` / `modified` | — | Explicit-pair mode: compare these two files instead of auto-detecting. |
| `files` | `**/*.docx` | Newline-separated git glob pattern(s) selecting which changed files to redline. |
| `base-ref` / `head-ref` | event-derived | Commits to compare. Defaults: PR base (merge-base) → head on `pull_request`, `before` → `after` on `push`, else `HEAD~1` → `HEAD`. |
| `author` | `python-redlines` | Author recorded on the tracked changes. |
| `engine` | `docxodus` | `docxodus` or `xmlpowertools`. |
| `comparison` | — | **Removed in 1.0.0.** Setting it fails the run; there is no longer an algorithm to select. |
| `detect-moves` | `false` | Move detection (docxodus engine only). |
| `output-dir` | `redlines` | Where outputs are written (mirrors the source tree). |
| `html-preview` | `auto` | `auto` (render when the Docx2Html tool supports `--track-changes`, else warn and skip), `true` (require), `false` (skip — no .NET needed). |
| `summary` | `true` | Write the job-summary table. |
| `upload-artifact` / `artifact-name` | `true` / `docx-redlines` | Artifact upload controls. |
| `package-version` | latest | pip pin for python-redlines, e.g. `==1.0.0`. |
| `docx2html-version` | latest | NuGet pin for the Docx2Html preview tool. |

Outputs: `count` (redlines generated), `any-changes`, `redlines` (a JSON array of
`{path, previous_path, status, revisions, redline, html, error}` records), and `artifact-url`.

Notes:

- Added and deleted `.docx` files are listed in the summary but not redlined — a redline
  needs both a base and a head version. Pure renames report zero revisions without
  invoking the engine.
- HTML previews need the `Docx2Html` dotnet tool with `--track-changes` support (Docxodus
  ≥ 7.1.0). That is now on NuGet, so the default `auto` mode renders previews rather than
  skipping them. `auto` still degrades to a warning-and-skip when the tool is missing or
  when `docx2html-version` pins it below 7.1.0; use `html-preview: true` to require a
  preview and fail the run if one cannot be produced.
- The action installs python-redlines from PyPI with prebuilt engine binaries — it does
  not build anything from the repository, so runs are fast on `ubuntu-latest` runners.

## Comparison Engines

Python-Redlines ships **two engine classes**, each wrapping one algorithm.

| # | Choice | How to select it | Algorithm | Status |
|---|---|---|---|---|
| 1 | **Docxodus** | `DocxodusEngine()` | `DocxDiff` — structure-aware IR diff | ✅ **Default.** Actively maintained |
| 2 | **Open-XML-PowerTools** | `XmlPowerToolsEngine()` | Original `WmlComparer` | ⚠️ Deprecated. Upstream archived |

**If you are unsure, use choice 1.** It is the default and requires no arguments.

Until 1.0.0 there was a third choice — Docxodus running a modernized `WmlComparer`, selected with
`engine="wmlcomparer"`. Docxodus v11.0.0 deleted it, so that choice is gone and the keyword
argument raises `ValueError`.

### 1. `DocxodusEngine` — the default

**[Docxodus](https://github.com/JSv4/Docxodus)** is an actively-maintained .NET 10.0 document
toolchain. Its `DocxDiff` algorithm models the document as an intermediate representation rather
than a stream of runs, which lets it attribute a change to the exact paragraph, cell, row, or
section it touched:

- **Structure-aware** — tracks table cell and row properties, section properties, and header and
  footer content that a run-stream diff reports coarsely or not at all
- **Native move detection** — identifies content that moved rather than deleting and re-inserting it
- **Format change detection** — detects changes to bold, italic, font size, and other run properties
- **Actively maintained** — regular bug fixes and new features

```python
from python_redlines import DocxodusEngine

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline("AuthorName", original_bytes, modified_bytes)
```

### 2. `XmlPowerToolsEngine` — deprecated

Wraps the original [Open-XML-PowerTools](https://github.com/OpenXmlDev/Open-Xml-PowerTools)
`WmlComparer`. Instantiating it emits a `DeprecationWarning`.

```python
from python_redlines import XmlPowerToolsEngine

engine = XmlPowerToolsEngine()  # DeprecationWarning
redline_bytes, stdout, stderr = engine.run_redline("AuthorName", original_bytes, modified_bytes)
```

> **Note:** Open-XML-PowerTools was archived by Microsoft and is no longer maintained. This class
> and its `python-redlines-ooxmlpowertools` wheel still ship, and still work, so that anyone who
> needs the original algorithm's output has somewhere to stand. It will be removed in a future
> major release — move to `DocxodusEngine` when you can.

Both share the same call signature — `run_redline(author, original, modified)` returning
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
pip install python-redlines[docxodus]           # Docxodus engine (recommended)
pip install python-redlines[ooxmlpowertools]    # Open-XML-PowerTools engine (deprecated)
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
`run_redline()`. `XmlPowerToolsEngine` accepts none of them.

```python
from python_redlines import DocxodusEngine

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline(
    "Reviewer", original, modified,
    detect_moves=True,
    case_insensitive=True,
)
```

### What each setting does

| Setting | Type | Default | Description |
|---|---|---|---|
| `case_insensitive` | bool | `False` | Ignore case differences |
| `detect_moves` | bool | `False` | Enable move detection |
| `move_similarity_threshold` | float | `0.8` | Jaccard threshold for move matching (0.0–1.0) |
| `move_minimum_word_count` | int | `3` | Minimum words for move detection |
| `detect_format_changes` | bool | `True` | Detect block-level formatting changes |
| `conflate_spaces` | bool | `True` | Treat breaking/non-breaking spaces the same |
| `date_time` | str | now | Custom ISO 8601 timestamp for revisions |

Anything else raises `ValueError`, including a misspelled setting name. Passing a setting to
`XmlPowerToolsEngine` is still silently ignored — it has never accepted any.

### Settings removed in 1.0.0

| Setting | Why it is gone |
|---|---|
| `engine` | Selected between `wmlcomparer` and `docxdiff`. Docxodus v11.0.0 deleted `WmlComparer`, so there is nothing to select. |
| `detail_threshold` | Tuned `WmlComparer`'s LCS granularity. `DocxDiff`'s granularity is structural and has no equivalent knob. |
| `simplify_move_markup` | Worked around `WmlComparer`'s move markup. `DocxDiff` renders moves natively. |

All three raise `ValueError` naming the removal and what to do instead. The check is on the
*keyword being present*, whatever its value: `simplify_move_markup=False` raises too.

The 0.3.0-era warning that `detect_moves=True` needed `simplify_move_markup=True` to avoid Word's
"unreadable content" dialog applied to `WmlComparer`'s move markup. It does not apply here —
`DocxDiff` emits move markup natively and has no such mitigation, because it needs none.

## Upgrading to 1.0.0

**If you called `run_redline` with no keyword arguments, nothing in your code changes.** Your
output will change, because the algorithm changed.

1. **Remove `engine=`, `detail_threshold=` and `simplify_move_markup=`.** They raise `ValueError`.
   If you were passing `engine="docxdiff"`, delete the argument — you now get it by default.
2. **Re-baseline anything that asserts on revision counts.** On this project's own fixtures the
   count moved from 9 (`wmlcomparer`) and 11 (`docxdiff` in 0.3.0) to **10**. Upstream v11 and v12
   changed region arrangement, surplus table cells and section defaults, so the 0.3.0 `docxdiff`
   count is not the 1.0.0 count either.
3. **Check documents that already carry tracked changes.** Docxodus v11 dropped
   `PreserveInputRevisions` from `DocxCompare.Compare`'s front door to match Word's own Compare
   behaviour. Revision-bearing inputs therefore produce different output than in 0.3.0. This
   project's fixtures carry no input revisions and will not warn you; diff a representative
   document if this is your workload.
4. **Move off `XmlPowerToolsEngine`** when you can — it now warns, and will be removed in a future
   major release.
5. **In the GitHub Action, remove the `comparison:` input.** It fails the run.

Pin `python-redlines==0.3.0` if you need the old `wmlcomparer` output while you migrate.

## Architecture Overview

Both engine classes follow the same pattern: a Python wrapper class invokes a self-contained C# binary
via subprocess.

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
| `DocxodusEngine` | `Redline complete: 10 revision(s) found` |

The counts differ because the algorithms differ, not because either is wrong.

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
