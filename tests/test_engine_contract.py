import pytest

from python_redlines.engines import XmlPowerToolsEngine, DocxodusEngine


def load_docx_bytes(file_path):
    with open(file_path, 'rb') as file:
        return file.read()


@pytest.fixture
def original_docx():
    return load_docx_bytes('tests/fixtures/original.docx')


@pytest.fixture
def modified_docx():
    return load_docx_bytes('tests/fixtures/modified.docx')


@pytest.mark.parametrize("engine_class", [XmlPowerToolsEngine, DocxodusEngine])
def test_engine_returns_bytes(engine_class, original_docx, modified_docx):
    engine = engine_class()
    redline_output, stdout, stderr = engine.run_redline("TestAuthor", original_docx, modified_docx)

    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0


@pytest.mark.parametrize("engine_class", [XmlPowerToolsEngine, DocxodusEngine])
def test_engine_no_stderr(engine_class, original_docx, modified_docx):
    engine = engine_class()
    _, _, stderr = engine.run_redline("TestAuthor", original_docx, modified_docx)

    assert stderr is None


@pytest.mark.parametrize("engine_class", [XmlPowerToolsEngine, DocxodusEngine])
def test_engine_has_stdout(engine_class, original_docx, modified_docx):
    engine = engine_class()
    _, stdout, _ = engine.run_redline("TestAuthor", original_docx, modified_docx)

    assert stdout is not None
    assert len(stdout) > 0
