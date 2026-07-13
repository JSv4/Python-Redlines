# How to compare two Word documents programmatically in Python

This tutorial walks through comparing two `.docx` files in Python and producing a
native Word tracked-changes redline — the same kind of output you'd get from Word's
built-in "Compare Documents" feature, but scriptable, automatable, and free.

We'll use [Python-Redlines](https://github.com/JSv4/Python-Redlines), an open-source
DOCX comparison library. You can try the underlying engine in your browser first at
**[redlines.opensource.legal](https://redlines.opensource.legal)** before writing any
code.

## What you'll build

A small Python script that takes an `original.docx` and a `modified.docx`, compares
them, and writes out `redline.docx` — a Word document where every insertion, deletion,
and (optionally) moved block of text is marked up as a real Word tracked change,
openable and reviewable in Microsoft Word, LibreOffice, or Google Docs.

## Prerequisites

- Python 3.9+
- Two `.docx` files to compare (any two versions of the same Word document)

No Microsoft Word installation, no COM automation, and no .NET SDK are required — the
comparison engine is a prebuilt, self-contained binary embedded in the wheel.

## Step 1: Install the library

```bash
pip install python-redlines[docxodus]
```

This installs the pure-Python wrapper (`python-redlines`) plus the default comparison
engine, [Docxodus](https://github.com/JSv4/Docxodus) — a modernized, high-performance
.NET 10 document diffing engine with move detection and cross-platform prebuilt
binaries for Linux, macOS, and Windows.

## Step 2: Load the two documents

```python
with open("original.docx", "rb") as f:
    original_bytes = f.read()

with open("modified.docx", "rb") as f:
    modified_bytes = f.read()
```

You can also pass file paths directly to `run_redline` instead of reading bytes
yourself — both are supported.

## Step 3: Run the comparison

```python
from python_redlines import DocxodusEngine

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline(
    "Reviewer",          # author tag attributed to each tracked change
    original_bytes,
    modified_bytes,
)
```

`run_redline` returns a 3-tuple: the redline `.docx` as bytes, and the engine's raw
stdout/stderr (useful for logging or a revision count — see
[stdout differences](https://github.com/JSv4/Python-Redlines#stdout-differences)).

## Step 4: Save the redline

```python
with open("redline.docx", "wb") as f:
    f.write(redline_bytes)
```

Open `redline.docx` in Word and you'll see standard tracked changes — insertions
underlined, deletions struck through, attributed to the `"Reviewer"` author tag you
passed in — exactly as if a human had compared the documents with Word's own Compare
feature.

## Full script

```python
from python_redlines import DocxodusEngine

with open("original.docx", "rb") as f:
    original_bytes = f.read()
with open("modified.docx", "rb") as f:
    modified_bytes = f.read()

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline("Reviewer", original_bytes, modified_bytes)

with open("redline.docx", "wb") as f:
    f.write(redline_bytes)

print(stdout)  # e.g. "Redline complete: 9 revision(s) found"
```

## Tuning the comparison

`DocxodusEngine` accepts keyword arguments for move detection, comparison
granularity, and more:

```python
redline_bytes, stdout, stderr = engine.run_redline(
    "Reviewer", original_bytes, modified_bytes,
    detect_moves=True,
    simplify_move_markup=True,  # required alongside detect_moves for Word compatibility
    detail_threshold=0.3,       # lower = more detailed diff
    case_insensitive=True,
)
```

See the [comparison settings reference](https://github.com/JSv4/Python-Redlines#comparison-settings-docxodusengine-only)
for every option and which engine supports it.

## Why not automate MS Word instead?

A common older approach is scripting Word itself (COM automation on Windows, or
Office Interop) to run its built-in comparison. This works on a single desktop but is
a poor fit for a server or pipeline: it violates Microsoft's Terms of Service for
unattended server-side use, requires a full licensed Office install per worker, and is
prone to crashes and zombie processes under concurrent load. Python-Redlines produces
the same native Word tracked-changes output without launching Word at all. See the
full [Python-Redlines vs. commercial alternatives](../alternatives.md) comparison for
more on this and other trade-offs (Draftable API, Cloudmersive, cloud data privacy).

## Next steps

- [Quickstart guide](../quickstart.md) — the same walkthrough with more detail on
  engine choice
- [Comparison engines](https://github.com/JSv4/Python-Redlines#comparison-engines) — `wmlcomparer` vs
  `docxdiff` vs the legacy Open-XML-PowerTools engine
- [Live demo](https://redlines.opensource.legal) — try a comparison in your browser
  first
