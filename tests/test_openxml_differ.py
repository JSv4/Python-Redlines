"""
Tests for the OpenXML differ functionality.

This file maintains backward compatibility with the original test suite
while also testing the new pluggable engine system.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from python_redlines.engines import XmlPowerToolsEngine


def load_docx_bytes(file_path):
    """Load a docx file as bytes."""
    with open(file_path, 'rb') as file:
        return file.read()


@pytest.fixture
def original_docx():
    """Load the original test document."""
    return load_docx_bytes('tests/fixtures/original.docx')


@pytest.fixture
def modified_docx():
    """Load the modified test document."""
    return load_docx_bytes('tests/fixtures/modified.docx')


def test_run_redlines_with_real_files(original_docx, modified_docx):
    """Test the redline functionality with real document files.

    This is the original test from the codebase, maintained for
    backward compatibility.
    """
    try:
        wrapper = XmlPowerToolsEngine()
    except FileNotFoundError:
        pytest.skip("XmlPowerTools binaries not available")

    author_tag = "TestAuthor"

    # Running the wrapper function with actual file bytes
    redline_output, stdout, stderr = wrapper.run_redline(
        author_tag, original_docx, modified_docx
    )

    # Asserting that some output is generated
    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0
    assert stderr is None
    assert "Revisions found: 9" in stdout


def test_compare_method_equivalent_to_run_redline(original_docx, modified_docx):
    """Test that the new compare() method works like run_redline()."""
    try:
        wrapper = XmlPowerToolsEngine()
    except FileNotFoundError:
        pytest.skip("XmlPowerTools binaries not available")

    author_tag = "TestAuthor"

    # Using the new compare method
    redline_output, stdout, stderr = wrapper.compare(
        author_tag, original_docx, modified_docx
    )

    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0
    assert stderr is None
    assert "Revisions found: 9" in stdout


def test_get_engine_returns_xmlpowertools_by_default():
    """Test that get_engine() returns XmlPowerToolsEngine by default."""
    from python_redlines import get_engine

    try:
        engine = get_engine()
    except (FileNotFoundError, RuntimeError):
        pytest.skip("Engines not available")

    assert engine.name == "openxml-powertools"


def test_list_engines_includes_both_engines():
    """Test that list_engines() returns both registered engines."""
    from python_redlines import list_engines

    engines = list_engines()
    assert "openxml-powertools" in engines
    assert "docxodus" in engines


def test_get_engine_by_name():
    """Test getting a specific engine by name."""
    from python_redlines import get_engine

    # Test getting openxml-powertools
    try:
        engine = get_engine("openxml-powertools")
        assert engine.name == "openxml-powertools"
    except FileNotFoundError:
        pytest.skip("XmlPowerTools binaries not available")


def test_engine_properties():
    """Test that engine has expected properties."""
    try:
        engine = XmlPowerToolsEngine()
    except FileNotFoundError:
        pytest.skip("XmlPowerTools binaries not available")

    # Test name property
    assert engine.name == "openxml-powertools"

    # Test description property
    assert len(engine.description) > 0
    assert "Open-Xml-PowerTools" in engine.description


def test_comparison_error_handling():
    """Test that comparison errors are properly raised."""
    from python_redlines.base import ComparisonError

    # Create an error with all attributes
    error = ComparisonError(
        "Test error",
        stdout="some output",
        stderr="some error"
    )

    assert error.message == "Test error"
    assert error.stdout == "some output"
    assert error.stderr == "some error"

    # Test string representation
    error_str = str(error)
    assert "Test error" in error_str
    assert "stdout: some output" in error_str
    assert "stderr: some error" in error_str


def test_output_file_is_valid_docx(original_docx, modified_docx):
    """Test that the output is a valid DOCX file."""
    try:
        wrapper = XmlPowerToolsEngine()
    except FileNotFoundError:
        pytest.skip("XmlPowerTools binaries not available")

    redline_output, _, _ = wrapper.compare(
        "TestAuthor", original_docx, modified_docx
    )

    # DOCX files are ZIP archives, should start with PK signature
    assert redline_output[:2] == b'PK', "Output should be a valid ZIP/DOCX file"
    assert len(redline_output) > 100, "Output should have substantial content"


def test_comparison_with_path_objects(original_docx, modified_docx):
    """Test comparison using Path objects instead of bytes."""
    try:
        wrapper = XmlPowerToolsEngine()
    except FileNotFoundError:
        pytest.skip("XmlPowerTools binaries not available")

    original_path = Path('tests/fixtures/original.docx')
    modified_path = Path('tests/fixtures/modified.docx')

    redline_output, stdout, stderr = wrapper.compare(
        "TestAuthor", original_path, modified_path
    )

    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0
    assert "Revisions found: 9" in stdout
