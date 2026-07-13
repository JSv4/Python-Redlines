# Python-Redlines: Open-Source DOCX Comparison for Python

**Python-Redlines** is an open-source DOCX comparison tool that generates native Word
tracked changes (redlines) in Python — without any MS Word dependency. Compare two
`.docx` files and get back a third document showing every insertion, deletion, and
(optionally) moved block of text as real Word tracked changes, openable in Microsoft
Word, LibreOffice, or Google Docs.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Python-Redlines",
  "alternateName": "python-redlines",
  "description": "Open-source DOCX comparison tool to generate native Word tracked changes (redlines) in Python without MS Word dependencies. Cross-platform Word document comparison with move and format-change detection.",
  "url": "https://jsv4.github.io/Python-Redlines/",
  "downloadUrl": "https://pypi.org/project/python-redlines/",
  "codeRepository": "https://github.com/JSv4/Python-Redlines",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Linux, macOS, Windows",
  "programmingLanguage": "Python",
  "license": "https://opensource.org/licenses/MIT",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "author": {
    "@type": "Person",
    "name": "John Scrudato IV"
  }
}
</script>

**🔗 [Try the live demo](https://redlines.opensource.legal)** — upload two `.docx`
files in your browser and download a real tracked-changes redline, no install
required.

## Why Python-Redlines

- **Open source, MIT licensed** — inspect, fork, or contribute to the comparison
  engines. No per-comparison fees, no API keys, no vendor lock-in.
- **Runs in-process** — document bytes never leave your infrastructure, unlike
  cloud comparison APIs. Works fully offline and in air-gapped environments.
- **No Microsoft Word required** — no COM automation, no Office Interop, no Terms
  of Service risk from server-side Word automation.
- **Native tracked-changes output** — the redline `.docx` opens in Word with real
  insertions, deletions, and moves, attributable to an author tag.
- **Cross-platform, high-performance diffing engine** — the default
  [Docxodus](https://github.com/JSv4/Docxodus) engine is a modernized .NET 10
  fork of Open-XML-PowerTools' `WmlComparer`, shipped as a prebuilt, self-contained
  binary embedded in the wheel for Linux, macOS, and Windows (x64/arm64) — nothing to
  compile.

## Install

```bash
pip install python-redlines[docxodus]
```

## Minimal example

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

## Where to go next

- [How to compare two Word documents programmatically in Python](tutorials/how-to-compare-word-documents-python.md) —
  a hands-on, step-by-step tutorial
- [Quickstart guide](quickstart.md)
- [Python-Redlines vs. commercial alternatives](alternatives.md) — Draftable API,
  Cloudmersive, and why not to automate MS Word server-side
- [Developer guide](developer-guide.md) — repository layout, building the C# engines,
  releasing
- [GitHub repository](https://github.com/JSv4/Python-Redlines)
- [PyPI package](https://pypi.org/project/python-redlines/)
