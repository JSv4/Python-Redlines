# python-redlines

Generate tracked-change "redline" `.docx` documents by comparing two Word files.

`python-redlines` is the pure-Python core. The comparison engines themselves are
compiled .NET binaries shipped in separate, optional companion packages — install
the one(s) you need as extras:

```bash
pip install python-redlines[docxodus]          # Docxodus engine
pip install python-redlines[ooxmlpowertools]    # Open-XML-PowerTools engine
pip install python-redlines[all]                # both
```

Binaries are prebuilt for each platform and embedded in the companion package's
wheel — no .NET SDK and no local compilation are needed to install or use it.

## Usage

```python
from python_redlines import DocxodusEngine

engine = DocxodusEngine()
redline_bytes, stdout, stderr = engine.run_redline(
    "Author Name",
    original=open("original.docx", "rb").read(),
    modified=open("modified.docx", "rb").read(),
)
```

If an engine's companion package is not installed, instantiating the engine
raises `EngineNotInstalledError` with the `pip install` command to fix it.

See the [project repository](https://github.com/JSv4/Python-Redlines) for details.
