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


# --- Engine selection (Docxodus v7.0.0 --engine flag) ---

def test_build_command_engine_omitted_by_default():
    """No engine= kwarg means no --engine flag: the argv stays as it was pre-v7."""
    engine = DocxodusEngine()
    cmd = engine._build_command("Author", "/tmp/o.docx", "/tmp/m.docx", "/tmp/out.docx")
    assert not any(arg.startswith("--engine") for arg in cmd)


def test_build_command_engine_docxdiff():
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/o.docx", "/tmp/m.docx", "/tmp/out.docx", engine="docxdiff",
    )
    assert "--engine=docxdiff" in cmd


def test_build_command_engine_explicit_wmlcomparer():
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/o.docx", "/tmp/m.docx", "/tmp/out.docx", engine="wmlcomparer",
    )
    assert "--engine=wmlcomparer" in cmd


def test_build_command_engine_is_normalized():
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/o.docx", "/tmp/m.docx", "/tmp/out.docx", engine="  DocxDiff  ",
    )
    assert "--engine=docxdiff" in cmd


def test_build_command_unknown_engine():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="engine must be one of"):
        engine._build_command("Author", "orig", "mod", "out", engine="bogus")


def test_build_command_non_string_engine():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="engine must be a string"):
        engine._build_command("Author", "orig", "mod", "out", engine=1)


@pytest.mark.parametrize("kwarg, value", [
    ("detail_threshold", 0.5),
    ("detail_threshold", 0.0),
    ("simplify_move_markup", True),
    ("simplify_move_markup", False),
    ("detect_format_changes", True),
    ("detect_format_changes", False),
])
def test_docxdiff_rejects_wmlcomparer_only_kwargs(kwarg, value):
    """docxdiff silently ignores these in C#; reject on key presence, whatever the value."""
    engine = DocxodusEngine()
    expected = f"{kwarg} is not supported by the 'docxdiff' engine"
    with pytest.raises(ValueError, match=expected):
        engine._build_command("Author", "orig", "mod", "out", engine="docxdiff", **{kwarg: value})


def test_wmlcomparer_still_allows_its_own_kwargs():
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "orig", "mod", "out",
        engine="wmlcomparer", detail_threshold=0.5, simplify_move_markup=True,
    )
    assert "--engine=wmlcomparer" in cmd
    assert "--detail-threshold=0.5" in cmd
    assert "--simplify-move-markup" in cmd


def test_docxdiff_allows_the_kwargs_it_honours():
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "orig", "mod", "out",
        engine="docxdiff", detect_moves=True, case_insensitive=True,
        conflate_spaces=False, move_similarity_threshold=0.7, move_minimum_word_count=2,
    )
    assert "--engine=docxdiff" in cmd
    assert "--detect-moves" in cmd
    assert "--case-insensitive" in cmd
    assert "--no-conflate-spaces" in cmd
    assert "--move-similarity-threshold=0.7" in cmd
    assert "--move-minimum-word-count=2" in cmd


def test_docxdiff_engine_check_precedes_range_check():
    """engine='docxdiff' + an out-of-range detail_threshold reports the engine problem."""
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="not supported by the 'docxdiff' engine"):
        engine._build_command("Author", "orig", "mod", "out", engine="docxdiff", detail_threshold=1.5)


# --- Engine selection, end to end ---

def test_docxodus_default_engine_is_wmlcomparer(original_docx, modified_docx):
    """The default path is the regression anchor: 9 revisions, exactly as before v7."""
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
    )
    assert stderr is None
    assert "Redline complete: 9 revision(s) found" in stdout
    assert redline_output[:2] == b"PK"


def test_docxodus_docxdiff_engine(original_docx, modified_docx):
    """docxdiff is a different algorithm and finds a different number of revisions."""
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx, engine="docxdiff",
    )
    assert stderr is None
    assert "Redline complete: 11 revision(s) found" in stdout
    assert redline_output[:2] == b"PK"


def test_docxodus_explicit_wmlcomparer_matches_default(original_docx, modified_docx):
    engine = DocxodusEngine()
    _, default_stdout, _ = engine.run_redline("TestAuthor", original_docx, modified_docx)
    _, explicit_stdout, _ = engine.run_redline(
        "TestAuthor", original_docx, modified_docx, engine="wmlcomparer",
    )
    assert "9 revision(s) found" in default_stdout
    assert "9 revision(s) found" in explicit_stdout


def test_docxdiff_output_is_a_valid_docx_with_tracked_changes(original_docx, modified_docx):
    import io
    import zipfile

    engine = DocxodusEngine()
    redline_output, _, _ = engine.run_redline(
        "TestAuthor", original_docx, modified_docx, engine="docxdiff",
    )
    with zipfile.ZipFile(io.BytesIO(redline_output)) as archive:
        assert archive.testzip() is None
        document_xml = archive.read("word/document.xml").decode("utf-8")

    assert "<w:ins " in document_xml
    assert "<w:del " in document_xml
