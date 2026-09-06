import io
import re
import zipfile

import pytest

from python_redlines.engines import DocxodusEngine

# Measured against the Docxodus v12.1.0 binary on tests/fixtures/. Docxodus
# v11.0.0 removed WmlComparer, so DocxDiff is the only algorithm; the count is
# neither the 9 the old default reported nor the 11 the old opt-in reported.
EXPECTED_REVISIONS = 10


def load_docx_bytes(file_path):
    with open(file_path, 'rb') as file:
        return file.read()


@pytest.fixture
def original_docx():
    return load_docx_bytes('tests/fixtures/original.docx')


@pytest.fixture
def modified_docx():
    return load_docx_bytes('tests/fixtures/modified.docx')


def revision_count(stdout):
    """The integer revision count from a Docxodus 'Redline complete: N revision(s) found' line."""
    match = re.search(r"Redline complete: (\d+) revision\(s\) found", stdout)
    assert match, f"no revision count in stdout: {stdout!r}"
    return int(match.group(1))


def test_run_docxodus_with_real_files(original_docx, modified_docx):
    wrapper = DocxodusEngine()

    author_tag = "TestAuthor"

    redline_output, stdout, stderr = wrapper.run_redline(author_tag, original_docx, modified_docx)

    assert redline_output is not None
    assert isinstance(redline_output, bytes)
    assert len(redline_output) > 0
    assert stderr is None
    assert "revision(s) found" in stdout


def test_docxodus_revision_count_is_pinned(original_docx, modified_docx):
    """The regression anchor for the DocxDiff-only engine."""
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
    )
    assert stderr is None
    assert revision_count(stdout) == EXPECTED_REVISIONS
    assert redline_output[:2] == b"PK"


def test_docxodus_output_is_a_valid_docx_with_tracked_changes(original_docx, modified_docx):
    engine = DocxodusEngine()
    redline_output, _, _ = engine.run_redline("TestAuthor", original_docx, modified_docx)

    with zipfile.ZipFile(io.BytesIO(redline_output)) as archive:
        assert archive.testzip() is None
        document_xml = archive.read("word/document.xml").decode("utf-8")

    assert "<w:ins " in document_xml
    assert "<w:del " in document_xml


# --- Integration tests for comparison settings ---

def test_docxodus_with_detect_moves(original_docx, modified_docx):
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
        detect_moves=True,
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
    """Every surviving setting at once, and the CLI stays quiet on stderr."""
    engine = DocxodusEngine()
    redline_output, stdout, stderr = engine.run_redline(
        "TestAuthor", original_docx, modified_docx,
        case_insensitive=True,
        detect_moves=True,
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


# --- Settings removed with WmlComparer (Docxodus v11.0.0) ---
#
# These must raise rather than be dropped. Two of them are still *accepted* by
# the v12 CLI, which warns on stderr and ignores them; `engine` is rejected as
# an unknown flag. Silently discarding any of them would hand the caller
# DocxDiff output while they believe they configured something else.

@pytest.mark.parametrize("value", ["wmlcomparer", "docxdiff", "WmlComparer", "  docxdiff  "])
def test_engine_kwarg_is_rejected(value):
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match=r"engine .*no longer"):
        engine._build_command("Author", "orig", "mod", "out", engine=value)


def test_detail_threshold_is_rejected():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match=r"detail_threshold .*no longer"):
        engine._build_command("Author", "orig", "mod", "out", detail_threshold=0.5)


def test_simplify_move_markup_is_rejected():
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match=r"simplify_move_markup .*no longer"):
        engine._build_command("Author", "orig", "mod", "out", simplify_move_markup=True)


@pytest.mark.parametrize("kwarg", ["engine", "detail_threshold", "simplify_move_markup"])
def test_removed_kwarg_error_names_the_replacement(kwarg):
    """The message has to tell the reader what to do, not just that they are wrong."""
    values = {"engine": "docxdiff", "detail_threshold": 0.5, "simplify_move_markup": True}
    engine = DocxodusEngine()
    with pytest.raises(ValueError) as excinfo:
        engine._build_command("Author", "orig", "mod", "out", **{kwarg: values[kwarg]})

    message = str(excinfo.value)
    assert "v11.0.0" in message
    assert "DocxDiff" in message


def test_removed_kwarg_is_rejected_even_when_false():
    """The check is on the keyword being present, whatever its value."""
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="no longer"):
        engine._build_command("Author", "orig", "mod", "out", simplify_move_markup=False)


def test_removed_kwarg_rejection_reaches_run_redline(original_docx, modified_docx):
    """The guard is on the public call, not only on the private builder."""
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="no longer"):
        engine.run_redline("TestAuthor", original_docx, modified_docx, engine="docxdiff")


# --- Unknown settings ---

def test_unknown_kwarg_is_rejected():
    """A typo used to be discarded in silence, which reads as 'the setting did nothing'."""
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="detial_threshold"):
        engine._build_command("Author", "orig", "mod", "out", detial_threshold=0.5)


def test_unknown_kwarg_error_lists_the_supported_settings():
    engine = DocxodusEngine()
    with pytest.raises(ValueError) as excinfo:
        engine._build_command("Author", "orig", "mod", "out", nonsense=True)

    message = str(excinfo.value)
    assert "case_insensitive" in message
    assert "detect_moves" in message


def test_removed_kwarg_beats_unknown_kwarg_reporting():
    """A removed setting gets its specific message, not the generic 'unknown' one."""
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="no longer"):
        engine._build_command("Author", "orig", "mod", "out", engine="docxdiff", nonsense=True)


# --- Validation of surviving settings ---

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


# --- Unit tests for _build_command flag construction ---

def test_build_command_default():
    engine = DocxodusEngine()
    cmd = engine._build_command("Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx")
    assert cmd[1] == "/tmp/orig.docx"
    assert cmd[2] == "/tmp/mod.docx"
    assert cmd[3] == "/tmp/out.docx"
    assert "--author=Author" in cmd
    assert len(cmd) == 5  # binary + 3 positional + --author


def test_build_command_never_emits_an_engine_flag():
    """--engine= was removed from the CLI in v11.0.0; emitting it exits 1."""
    engine = DocxodusEngine()
    cmd = engine._build_command("Author", "/tmp/o.docx", "/tmp/m.docx", "/tmp/out.docx")
    assert not any(str(arg).startswith("--engine") for arg in cmd)


def test_build_command_with_all_flags():
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx",
        case_insensitive=True,
        detect_moves=True,
        move_similarity_threshold=0.7,
        move_minimum_word_count=2,
        detect_format_changes=False,
        conflate_spaces=False,
        date_time="2025-01-01T00:00:00Z",
    )
    assert "--author=Author" in cmd
    assert "--case-insensitive" in cmd
    assert "--detect-moves" in cmd
    assert "--no-detect-format-changes" in cmd
    assert "--no-conflate-spaces" in cmd
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
