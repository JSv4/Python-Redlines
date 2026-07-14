# Python-Redlines Quickstart

`python-redlines` wraps a C# comparison engine to produce tracked-change redline `.docx`
files. This guide uses `DocxodusEngine` — the default and recommended engine.
`XmlPowerToolsEngine` (legacy) shares the same call signature; the only behavioural
difference is that it silently ignores the keyword arguments shown in Step 4.

### Step 0: Install

Install the core package plus the engine you want as an extra. No .NET SDK is needed —
the engine binary is prebuilt and embedded in the wheel.

```commandline
pip install python-redlines[docxodus]
```

Use `python-redlines[ooxmlpowertools]` for the legacy engine, or `python-redlines[all]`
for both.

### Step 1: Import and Initialize the Wrapper

In your Python script or interactive session, import and initialize the wrapper:

```python
from python_redlines import DocxodusEngine

wrapper = DocxodusEngine()
```

### Step 2: Run Redlines

Use the `run_redline` method to compare documents. You can pass the paths of the `.docx` files (as `str` or `pathlib.Path`) or their byte content:

```python
# Example with file paths
output = wrapper.run_redline('AuthorTag', '/path/to/original.docx', '/path/to/modified.docx')

# Example with byte content
with open('/path/to/original.docx', 'rb') as f:
    original_bytes = f.read()
with open('/path/to/modified.docx', 'rb') as f:
    modified_bytes = f.read()

# Returns (redline_bytes, stdout, stderr)
output = wrapper.run_redline('AuthorTag', original_bytes, modified_bytes)
```

In both cases, `output[0]` will contain the byte content of the resulting redline — a .docx with changes as Word tracked changes.

### Step 3: Handle the Output

Process or save the output as needed. For example, to save the redline output to a file:

```python
with open('/path/to/redline_output.docx', 'wb') as f:
    f.write(output[0])
```

### Step 4: Tune the Comparison (optional, DocxodusEngine only)

`DocxodusEngine` accepts keyword arguments to control move detection, granularity, and
more. See the [main README](https://github.com/JSv4/Python-Redlines#comparison-settings-docxodusengine-only) for
the full table.

```python
output = wrapper.run_redline(
    'AuthorTag', original_bytes, modified_bytes,
    detect_moves=True,
    simplify_move_markup=True,  # required with detect_moves for Word compatibility
    detail_threshold=0.3,
)
```

`XmlPowerToolsEngine` silently ignores these kwargs — switch engines if you need them.

### See also

- [How to compare two Word documents programmatically in Python](tutorials/how-to-compare-word-documents-python.md) —
  a step-by-step tutorial covering this same flow in more depth
- [Live demo](https://redlines.opensource.legal) — try a comparison in your browser
- [Python-Redlines vs. commercial alternatives](alternatives.md)
