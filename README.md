# Python-Redlines: Docx Redlines (Tracked Changes) for the Python Ecosystem

[![CI](https://github.com/JSv4/Python-Redlines/actions/workflows/ci.yml/badge.svg)](https://github.com/JSv4/Python-Redlines/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/python-redlines.svg)](https://pypi.org/project/python-redlines/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Project Goal - Democratizing DOCX Comparisons

The main goal of this project is to address the significant gap in the open-source ecosystem around `.docx` document
comparison tools. Currently, the process of comparing and generating redline documents (documents that highlight
changes between versions) is complex and largely dominated by commercial software. These
tools, while effective, often come with cost barriers and limitations in terms of accessibility and integration
flexibility.

`Python-redlines` aims to democratize the ability to run tracked change redlines for .docx, providing the
open-source community with a tool to create `.docx` redlines without the need for commercial software. This will let
more legal hackers and hobbyist innovators experiment and create tooling for enterprise and legal.

## Quick Start

### Installation

```bash
pip install python-redlines
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/JSv4/Python-Redlines
```

### Basic Usage

```python
from python_redlines import get_engine

# Get a comparison engine (default: openxml-powertools)
engine = get_engine()

# Load your documents
with open("original.docx", "rb") as f:
    original = f.read()
with open("modified.docx", "rb") as f:
    modified = f.read()

# Generate redlined document
redline_bytes, stdout, stderr = engine.compare(
    author="John Doe",
    original=original,
    modified=modified
)

# Save the result
with open("redlined.docx", "wb") as f:
    f.write(redline_bytes)
```

## Comparison Engines

Python-Redlines uses a **pluggable engine architecture** that allows you to choose between different comparison backends. This design provides flexibility and allows the library to evolve as better comparison tools become available.

### Available Engines

| Engine | Name | Status | Description |
|--------|------|--------|-------------|
| [Open-Xml-PowerTools](https://github.com/OpenXmlDev/Open-Xml-PowerTools) | `openxml-powertools` | Default | Original WmlComparer engine. Stable but no longer maintained. |
| [Docxodus](https://github.com/JSv4/Docxodus) | `docxodus` | Optional | Modern .NET 8.0 fork with improved features. **Will become default in future release.** |

### Selecting an Engine

```python
from python_redlines import get_engine, list_engines

# See available engines
print(list_engines())  # ['openxml-powertools', 'docxodus']

# Use the default engine (currently openxml-powertools)
engine = get_engine()

# Or explicitly select an engine
engine = get_engine('openxml-powertools')
engine = get_engine('docxodus')
```

### Engine Comparison

#### Open-Xml-PowerTools (Current Default)

The [Open-Xml-PowerTools](https://github.com/OpenXmlDev/Open-Xml-PowerTools) engine uses the `WmlComparer` class from Microsoft's archived repository. While stable and well-tested, it has limitations:

- ⚠️ Repository archived ~5 years ago
- ⚠️ Limited compatibility with newer Open XML SDK versions
- ⚠️ No active maintenance

#### Docxodus (Recommended, Future Default)

[Docxodus](https://github.com/JSv4/Docxodus) is a modernized fork of Open-Xml-PowerTools, upgraded to .NET 8.0 with active maintenance and improved features:

- ✅ **Move Detection** - Identifies when content is relocated rather than deleted and re-inserted
- ✅ **Format Change Detection** - Recognizes styling-only modifications (bold, italic, font changes)
- ✅ **Active Maintenance** - Regular updates and bug fixes
- ✅ **.NET 8.0** - Modern framework support
- ✅ **Configurable Thresholds** - Fine-tune comparison sensitivity

**We plan to make Docxodus the default engine in a future release** once it has been thoroughly tested in production environments.

## API Reference

### Core Functions

```python
from python_redlines import (
    get_engine,           # Get an engine instance by name
    list_engines,         # List all registered engine names
    list_available_engines,  # List engines with binaries installed
)
```

### Engine Interface

All engines implement the `ComparisonEngine` interface:

```python
class ComparisonEngine:
    @property
    def name(self) -> str:
        """Engine identifier (e.g., 'openxml-powertools', 'docxodus')"""

    @property
    def description(self) -> str:
        """Human-readable description"""

    def compare(
        self,
        author: str,
        original: Union[bytes, Path],
        modified: Union[bytes, Path]
    ) -> Tuple[bytes, Optional[str], Optional[str]]:
        """
        Compare two documents and return redlined version.

        Returns:
            - bytes: The redlined document
            - str | None: Standard output from comparison
            - str | None: Standard error (if any)
        """

    def is_available(self) -> bool:
        """Check if engine binaries are installed"""
```

### Backward Compatibility

The original `XmlPowerToolsEngine` API is still supported:

```python
from python_redlines import XmlPowerToolsEngine

engine = XmlPowerToolsEngine()
redline_bytes, stdout, stderr = engine.run_redline(
    author_tag="Author",
    original=original_bytes,
    modified=modified_bytes
)
```

## Architecture Overview

### Project Structure

```
python-redlines/
├── csproj/                      # Open-Xml-PowerTools CLI wrapper
│   └── Program.cs
├── csproj-docxodus/             # Docxodus CLI wrapper
│   └── Program.cs
├── src/python_redlines/
│   ├── base.py                  # Abstract ComparisonEngine interface
│   ├── engines.py               # Engine implementations
│   ├── registry.py              # Engine discovery and registration
│   ├── dist/
│   │   ├── openxml-powertools/  # Open-Xml-PowerTools binaries
│   │   └── docxodus/            # Docxodus binaries
│   └── bin/                     # Extracted binaries (runtime)
├── tests/
│   ├── test_base.py
│   ├── test_engines.py
│   ├── test_registry.py
│   └── fixtures/
└── build_differ.py              # Build script for all engines
```

### How It Works

1. **Python Wrapper** - The `engines.py` module provides Python classes that wrap .NET CLI tools
2. **Binary Management** - Platform-specific binaries are bundled and extracted at runtime
3. **Pluggable Design** - New engines can be added by implementing the `ComparisonEngine` interface

### Supported Platforms

| Platform | Architecture | Status |
|----------|-------------|--------|
| Linux | x64 | ✅ Supported |
| Linux | ARM64 | ✅ Supported |
| Windows | x64 | ✅ Supported |
| Windows | ARM64 | ✅ Supported |
| macOS | x64 | ✅ Supported |
| macOS | ARM64 (Apple Silicon) | ✅ Supported |

## Development

### Prerequisites

- Python 3.8+
- .NET 8.0 SDK (for building binaries)

### Setup

```bash
# Clone the repository
git clone https://github.com/JSv4/Python-Redlines.git
cd Python-Redlines

# Install in development mode
pip install -e ".[dev]"

# Build engine binaries
python build_differ.py

# Run tests
pytest tests/ -v
```

### Building Specific Engines

```bash
# Build all engines
python build_differ.py

# Build only Open-Xml-PowerTools
python build_differ.py --engine openxml-powertools

# Build only Docxodus
python build_differ.py --engine docxodus

# Build for a specific platform
python build_differ.py --platform linux-x64
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=python_redlines

# Run only unit tests (no binaries needed)
pytest tests/ -v -k "not integration"
```

## Roadmap

### Current State (v0.0.4+)

- ✅ Pluggable engine architecture
- ✅ Open-Xml-PowerTools engine (default)
- ✅ Docxodus engine (optional)
- ✅ Cross-platform support (Linux, Windows, macOS)
- ✅ Comprehensive test suite

### Planned

- 🔄 Make Docxodus the default engine
- 📋 Pure Python comparison engine (using [xmldiff](https://github.com/Shoobx/xmldiff))
- 📋 Additional comparison options and configuration
- 📋 Better error messages and diagnostics

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [Developer Guide](docs/developer-guide.md)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

For bugs or feature requests, please [open an issue](https://github.com/JSv4/Python-Redlines/issues).

## License

[MIT](License.md)

## Acknowledgments

- [Open-Xml-PowerTools](https://github.com/OpenXmlDev/Open-Xml-PowerTools) - Original WmlComparer implementation
- [Docxodus](https://github.com/JSv4/Docxodus) - Modernized fork with active maintenance
- [DocumentFormat.OpenXml](https://github.com/dotnet/Open-XML-SDK) - Microsoft's Open XML SDK
