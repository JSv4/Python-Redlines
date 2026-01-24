# SPDX-FileCopyrightText: 2024-present John Scrudato IV
#
# SPDX-License-Identifier: MIT

"""
Python Redlines - Document comparison library for generating redlined Word documents.

This library provides a pluggable comparison engine system for generating
Word documents with tracked changes (redlines) from original and modified documents.

Quick Start:
    from python_redlines import get_engine

    # Get the default engine
    engine = get_engine()

    # Compare two documents
    redline_bytes, stdout, stderr = engine.compare(
        author="John Doe",
        original=original_doc_bytes,
        modified=modified_doc_bytes
    )

    # Save the result
    with open("redlined.docx", "wb") as f:
        f.write(redline_bytes)

Available Engines:
    - 'openxml-powertools': Uses Open-Xml-PowerTools WmlComparer (default)
    - 'docxodus': Uses Docxodus, a modern .NET 8.0 fork with improved features

Selecting an Engine:
    # Use the default engine (openxml-powertools)
    engine = get_engine()

    # Use a specific engine
    engine = get_engine('docxodus')

    # List available engines
    from python_redlines import list_available_engines
    engines = list_available_engines()
"""

from .__about__ import __version__

# Import base classes
from .base import ComparisonEngine, ComparisonError

# Import engine implementations
from .engines import XmlPowerToolsEngine, DocxodusEngine

# Import registry functions
from .registry import (
    get_engine,
    list_engines,
    list_available_engines,
    EngineRegistry,
)

__all__ = [
    # Version
    "__version__",
    # Base classes
    "ComparisonEngine",
    "ComparisonError",
    # Engine implementations
    "XmlPowerToolsEngine",
    "DocxodusEngine",
    # Registry
    "get_engine",
    "list_engines",
    "list_available_engines",
    "EngineRegistry",
]
