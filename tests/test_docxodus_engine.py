import pytest

from python_redlines.engines import DocxodusEngine


def load_docx_bytes(file_path):
    with open(file_path, 'rb') as file:
        return file.read()


@pytest.fixture
def original_docx():
    return load_docx_bytes('tests/fixtures/original.docx')


@pytest.fixture
def modified_docx():
    return load_docx_bytes('tests/fixtures/modified.docx')


def test_run_docxodus_with_real_files(original_docx, modified_docx):
    wrapper = DocxodusEngine()

    author_tag = "TestAuthor"

    redline_output, stdout, stderr = wrapper.run_redline(author_tag, original_docx, modified_docx)

    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0
    assert stderr is None
    assert "revision(s) found" in stdout
