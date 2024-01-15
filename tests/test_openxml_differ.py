import os
import pytest
from unittest.mock import patch, MagicMock

from python_redlines.engines import XmlPowerToolsEngine


def load_docx_bytes(file_path):
    with open(file_path, 'rb') as file:
        return file.read()


@pytest.fixture
def original_docx():
    return load_docx_bytes('tests/fixtures/original.docx')


@pytest.fixture
def modified_docx():
    return load_docx_bytes('tests/fixtures/modified.docx')


def test_run_redlines_with_real_files(original_docx, modified_docx):
    # Create an instance of the wrapper
    wrapper = XmlPowerToolsEngine()

    author_tag = "TestAuthor"

    # Running the wrapper function with actual file bytes
    redline_output, stdout, stderr = wrapper.run_redline(author_tag, original_docx, modified_docx)

    # Asserting that some output is generated (specific assertions depend on expected output)
    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0
    assert stderr is None
    assert "Revisions found: 9" in stdout
