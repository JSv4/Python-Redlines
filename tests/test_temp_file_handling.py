"""Temp-file handling in BaseEngine.run_redline.

Two bugs live in the same handful of lines, so they are tested together:

- Issue #30: the output scratch file was created as
  ``NamedTemporaryFile(delete=False).name``, which drops the only reference to
  the file object. Its finalizer then reports a ResourceWarning and the
  descriptor stays open until collection.
- Path inputs were registered for deletion alongside the engine's own scratch
  files, so passing a path — a documented input mode — deleted the caller's
  source documents.
"""
import gc
import shutil
import sys
import tempfile
import warnings

import pytest

from python_redlines.engines import DocxodusEngine


@pytest.fixture
def engine():
    return DocxodusEngine()


@pytest.fixture
def docs(tmp_path):
    """A private copy of the fixtures, so a destructive bug cannot damage them."""
    original = tmp_path / 'original.docx'
    modified = tmp_path / 'modified.docx'
    shutil.copy('tests/fixtures/original.docx', original)
    shutil.copy('tests/fixtures/modified.docx', modified)
    return original, modified


def test_run_redline_closes_every_temp_file_it_opens(engine, docs, monkeypatch):
    """Issue #30, in a form that is observable on every CPython version.

    The ResourceWarning the issue reports is only emitted on 3.13+, so this
    asserts the underlying defect instead: a temp file object that run_redline
    creates must be closed by the time the call returns. Holding a reference in
    the spy is what makes the leak visible — it is precisely the reference the
    buggy code drops, letting the finalizer close the file and hide the fault.
    """
    original, modified = docs
    created = []
    real_named_temp_file = tempfile.NamedTemporaryFile

    def spy(*args, **kwargs):
        handle = real_named_temp_file(*args, **kwargs)
        created.append(handle)
        return handle

    monkeypatch.setattr(tempfile, 'NamedTemporaryFile', spy)
    engine.run_redline('Author', original.read_bytes(), modified.read_bytes())

    unclosed = [handle for handle in created if not handle.closed]
    assert not unclosed, (
        f'run_redline abandoned {len(unclosed)} unclosed temp file object(s); '
        'this is what raises ResourceWarning on CPython 3.13+ (issue #30)'
    )


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason="tempfile's finalizer only emits ResourceWarning on CPython 3.13+",
)
def test_run_redline_emits_no_resource_warning(engine, docs):
    """The exact symptom issue #30 reports, on the versions that can show it."""
    original, modified = docs

    with warnings.catch_warnings():
        warnings.simplefilter('error', ResourceWarning)
        engine.run_redline('Author', original.read_bytes(), modified.read_bytes())
        gc.collect()


def test_run_redline_keeps_path_inputs_on_disk(engine, docs):
    """Passing paths must not delete the caller's documents."""
    original, modified = docs

    redline_bytes, _, _ = engine.run_redline('Author', str(original), str(modified))

    assert original.exists(), 'run_redline deleted the original document it was given'
    assert modified.exists(), 'run_redline deleted the modified document it was given'
    assert redline_bytes[:2] == b'PK'


def test_run_redline_accepts_pathlib_paths(engine, docs):
    """The docstring and type hint promise pathlib.Path works, not just str."""
    original, modified = docs

    redline_bytes, _, _ = engine.run_redline('Author', original, modified)

    assert original.exists()
    assert modified.exists()
    assert redline_bytes[:2] == b'PK'


def test_run_redline_cleans_up_its_own_scratch_files(engine, docs, tmp_path, monkeypatch):
    """The fix must not overshoot: engine-created temp files still get removed.

    tempfile is pointed at a private directory so the assertion sees only what
    this call created, not whatever else is using the system temp directory.
    """
    original, modified = docs
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(scratch))

    engine.run_redline('Author', original.read_bytes(), modified.read_bytes())

    leaked = sorted(path.name for path in scratch.iterdir())
    assert not leaked, f'run_redline left scratch files behind: {leaked}'
