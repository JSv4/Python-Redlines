import warnings

import pytest

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
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
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


def test_xmlpowertools_engine_is_deprecated():
    """It wraps the original, unmaintained Open-XML-PowerTools WmlComparer.

    The package keeps shipping and the class keeps working; instantiating it
    has to say that it is on the way out and name what to use instead.
    """
    with pytest.warns(DeprecationWarning) as record:
        XmlPowerToolsEngine()

    message = str(record[0].message)
    assert "DocxodusEngine" in message


def test_xmlpowertools_deprecation_points_at_the_caller():
    """stacklevel must blame the user's construction site, not engines.py."""
    with pytest.warns(DeprecationWarning) as record:
        XmlPowerToolsEngine()

    assert record[0].filename == __file__
