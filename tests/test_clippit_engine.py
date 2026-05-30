import pytest

from python_redlines.engines import ClippitEngine


def load_docx_bytes(file_path):
    with open(file_path, 'rb') as file:
        return file.read()


@pytest.fixture
def original_docx():
    return load_docx_bytes('tests/fixtures/original.docx')


@pytest.fixture
def modified_docx():
    return load_docx_bytes('tests/fixtures/modified.docx')


def test_run_clippit_with_real_files(original_docx, modified_docx):
    wrapper = ClippitEngine()

    author_tag = "TestAuthor"

    redline_output, stdout, stderr = wrapper.run_redline(author_tag, original_docx, modified_docx)

    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0
    assert stderr is None
    # Clippit wraps the same WmlComparer API as Open-XML-PowerTools and emits the
    # same stdout format.
    assert "Revisions found:" in stdout


def test_clippit_uses_positional_command():
    """ClippitEngine inherits the legacy 4-positional-arg CLI format."""
    engine = ClippitEngine()
    cmd = engine._build_command("Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx")
    assert cmd[1:] == ["Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx"]
