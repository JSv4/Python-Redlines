import io
import re
import zipfile
import xml.etree.ElementTree as ET

import pytest

from python_redlines.engines import DocxodusEngine

# Measured against the Docxodus v17.0.0 binary on tests/fixtures/. Docxodus
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


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def make_document(template_docx, *paragraphs):
    """A copy of *template_docx* whose body is exactly these plain paragraphs."""
    document = ET.Element(f"{{{W_NS}}}document")
    body = ET.SubElement(document, f"{{{W_NS}}}body")
    for text in paragraphs:
        run = ET.SubElement(ET.SubElement(body, f"{{{W_NS}}}p"), f"{{{W_NS}}}r")
        ET.SubElement(run, f"{{{W_NS}}}t").text = text

    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(template_docx)) as template:
        with zipfile.ZipFile(output, "w") as archive:
            for member in template.infolist():
                data = (ET.tostring(document, encoding="utf-8", xml_declaration=True)
                        if member.filename == "word/document.xml"
                        else template.read(member.filename))
                archive.writestr(member, data)
    return output.getvalue()


def document_root(docx):
    """The parsed word/document.xml of a .docx given as bytes."""
    with zipfile.ZipFile(io.BytesIO(docx)) as archive:
        return ET.fromstring(archive.read("word/document.xml"))


def joined_text(root, path):
    return "".join(node.text or "" for node in root.findall(path, NS))


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


def test_docxodus_marks_a_single_changed_cjk_character(original_docx):
    """Guard the CJK granularity fix needed by users upgrading from 0.3.0 (#34)."""
    before = make_document(original_docx, "本合同的交付日期为三月十五日，双方应按约履行。")
    after = make_document(original_docx, "本合同的交付日期为一月十五日，双方应按约履行。")
    redline, _, stderr = DocxodusEngine().run_redline("Reviewer", before, after)
    assert stderr is None
    document = document_root(redline)
    assert joined_text(document, ".//w:delText") == "三"
    assert joined_text(document, ".//w:ins//w:t") == "一"


# --- Minimum anchor word count (new in Docxodus v17.0.0) ---

LEASE_CLAUSES = [
    "The tenant shall keep the premises in good repair at its own expense.",
    "Payment of rent falls due on the first business day of every month.",
    "Either party may terminate this lease by giving ninety days of written notice.",
    "The landlord shall insure the building against fire and flood damage.",
    "Disputes are resolved by arbitration seated in the city of Geneva.",
]


def labelled_entries(clauses):
    """P1 / clause / P2 / clause / ... with each label on a line of its own."""
    return [text for number, clause in enumerate(clauses, 1) for text in (f"P{number}", clause)]


@pytest.fixture
def renumbered_entries(original_docx):
    """Dropping the first entry renumbers every later label but leaves its text alone."""
    return (
        make_document(original_docx, *labelled_entries(LEASE_CLAUSES)),
        make_document(original_docx, *labelled_entries(LEASE_CLAUSES[1:])),
    )


def moved_paragraph_count(redline):
    """Paragraphs the redline shows as moved, counted at their destination."""
    return len([p for p in document_root(redline).findall(".//w:p", NS)
                if p.find(".//w:moveTo", NS) is not None])


@pytest.mark.parametrize("settings", [{}, {"minimum_anchor_word_count": 0}], ids=["omitted", "zero"])
def test_renumbered_entries_read_as_moves_by_default(renumbered_entries, settings):
    """The behaviour the setting exists to change; 0 must be accepted and mean the default."""
    redline, _, stderr = DocxodusEngine().run_redline("Reviewer", *renumbered_entries, **settings)
    assert stderr is None
    assert moved_paragraph_count(redline) > 0


def test_minimum_anchor_word_count_matches_renumbered_entries_by_their_text(renumbered_entries):
    redline, _, stderr = DocxodusEngine().run_redline(
        "Reviewer", *renumbered_entries, minimum_anchor_word_count=2,
    )
    assert stderr is None
    assert moved_paragraph_count(redline) == 0

    document = document_root(redline)
    deleted = joined_text(document, ".//w:delText")
    assert LEASE_CLAUSES[0] in deleted
    for clause in LEASE_CLAUSES[1:]:
        assert clause not in deleted
    # Only label digits are inserted; no surviving clause is re-typed.
    assert joined_text(document, ".//w:ins//w:t").strip("P0123456789") == ""


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
        minimum_anchor_word_count=2,
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


@pytest.mark.parametrize("value", [-1, 2.5, "2", None, True, False])
def test_docxodus_invalid_minimum_anchor_word_count(value):
    """bool is an int subclass, and str(True) is not a number the CLI can parse."""
    engine = DocxodusEngine()
    with pytest.raises(ValueError, match="minimum_anchor_word_count must be a non-negative integer"):
        engine._build_command("Author", "orig", "mod", "out", minimum_anchor_word_count=value)


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
        minimum_anchor_word_count=2,
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
    assert "--minimum-anchor-word-count=2" in cmd
    assert "--date-time=2025-01-01T00:00:00Z" in cmd


def test_build_command_passes_a_zero_minimum_anchor_word_count():
    """0 is a legal value here, unlike move_minimum_word_count, and must not be lost as falsy."""
    engine = DocxodusEngine()
    cmd = engine._build_command(
        "Author", "/tmp/orig.docx", "/tmp/mod.docx", "/tmp/out.docx",
        minimum_anchor_word_count=0,
    )
    assert "--minimum-anchor-word-count=0" in cmd


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
