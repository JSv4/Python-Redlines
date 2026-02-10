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


# --- Integration tests for comparison settings ---

def test_docxodus_with_detect_moves(original_docx, modified_docx):
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
        detect_moves=True, simplify_move_markup=True,
    )
    assert redline_output is not None
    assert len(redline_output) > 0
    assert stderr is None
    assert "revision(s) found" in stdout


def test_docxodus_with_detail_threshold(original_docx, modified_docx):
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
        detail_threshold=0.5,
    )
    assert redline_output is not None
    assert len(redline_output) > 0
    assert stderr is None
    assert "revision(s) found" in stdout


def test_docxodus_with_case_insensitive(original_docx, modified_docx):
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
        case_insensitive=True,
    )
    assert redline_output is not None
    assert len(redline_output) > 0
    assert stderr is None
    assert "revision(s) found" in stdout


def test_docxodus_with_no_format_changes(original_docx, modified_docx):
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
        detect_format_changes=False,
    )
    assert redline_output is not None
    assert len(redline_output) > 0
    assert stderr is None
    assert "revision(s) found" in stdout


def test_docxodus_with_all_options(original_docx, modified_docx):
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
        detail_threshold=0.3,
        case_insensitive=True,
        detect_moves=True,
        simplify_move_markup=True,
        move_similarity_threshold=0.7,
        move_minimum_word_count=2,
        detect_format_changes=False,
        conflate_spaces=False,
        date_time="2025-01-01T00:00:00Z",
    )
    assert redline_output is not None
    assert len(redline_output) > 0
    assert stderr is None
    assert "revision(s) found" in stdout


# --- Validation tests ---

def test_docxodus_invalid_detail_threshold():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="detail_threshold must be a float between 0.0 and 1.0"):
        engine._build_command("Author", "orig", "mod", "out", detail_threshold=1.5)


def test_docxodus_invalid_move_similarity_threshold():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="move_similarity_threshold must be a float between 0.0 and 1.0"):
        engine._build_command("Author", "orig", "mod", "out", move_similarity_threshold=-0.1)


def test_docxodus_invalid_move_minimum_word_count():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="move_minimum_word_count must be a positive integer"):
        engine._build_command("Author", "orig", "mod", "out", move_minimum_word_count=0)


def test_docxodus_invalid_move_minimum_word_count_type():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="move_minimum_word_count must be a positive integer"):
        engine._build_command("Author", "orig", "mod", "out", move_minimum_word_count=2.5)


# --- Unit test for _build_command flag construction ---

def test_build_command_default():
    engine = DocxodusEngine()
    cmd = engine._build_command("Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx")
    assert cmd[1] == "/tmp/orig.docx"
    assert cmd[2] == "/tmp/mod.docx"
    assert cmd[3] == "/tmp/out.docx"
    assert "--author=Author" in cmd
    assert len(cmd) == 5  # binary + 3 positional + --author


def test_build_command_with_all_flags():
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx",
        detail_threshold=0.5,
        case_insensitive=True,
        detect_moves=True,
        simplify_move_markup=True,
        move_similarity_threshold=0.7,
        move_minimum_word_count=2,
        detect_format_changes=False,
        conflate_spaces=False,
        date_time="2025-01-01T00:00:00Z",
    )
    assert "--author=Author" in cmd
    assert "--case-insensitive" in cmd
    assert "--detect-moves" in cmd
    assert "--simplify-move-markup" in cmd
    assert "--no-detect-format-changes" in cmd
    assert "--no-conflate-spaces" in cmd
    assert "--detail-threshold=0.5" in cmd
    assert "--move-similarity-threshold=0.7" in cmd
    assert "--move-minimum-word-count=2" in cmd
    assert "--date-time=2025-01-01T00:00:00Z" in cmd


def test_build_command_false_bools_not_added():
    """Boolean flags that are False should not be added to the command."""
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx",
        detect_moves=False,
        case_insensitive=False,
    )
    assert "--detect-moves" not in cmd
    assert "--case-insensitive" not in cmd


def test_build_command_negatable_true_not_added():
    """Negatable flags that are True (default) should not add --no- flags."""
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx",
        detect_format_changes=True,
        conflate_spaces=True,
    )
    assert "--no-detect-format-changes" not in cmd
    assert "--no-conflate-spaces" not in cmd
