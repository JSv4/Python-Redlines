"""Engine failures must expose diagnostics without breaking subprocess callers."""
import subprocess
import sys
import tempfile

import pytest

from python_redlines import BaseEngine


@pytest.mark.parametrize("stdout,stderr", [
    ("Usage: redline ...\n", "Error: Unknown flag: --engine=wmlcomparer\n"),
    ("The engine explains the failure on stdout\n", ""),
    ("", "The engine explains the failure on stderr\n"),
    ("", ""),
])
@pytest.mark.parametrize("use_paths", [False, True])
def test_failed_engine_exposes_diagnostics_and_cleans_scratch(
    tmp_path, monkeypatch, stdout, stderr, use_paths,
):
    from python_redlines import EngineExecutionError

    class FailingEngine(BaseEngine):
        def _resolve_binary(self):
            return sys.executable

        def _build_command(self, *args, **kwargs):
            script = (
                f"import sys; sys.stdout.write({stdout!r}); "
                f"sys.stderr.write({stderr!r}); sys.exit(2)"
            )
            return [self.extracted_binaries_path, "-c", script]

    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    original = tmp_path / "original.docx"
    modified = tmp_path / "modified.docx"
    original.write_bytes(b"original")
    modified.write_bytes(b"modified")
    inputs = (original, modified) if use_paths else (b"original", b"modified")

    with pytest.raises(subprocess.CalledProcessError) as caught:
        FailingEngine().run_redline("Author", *inputs)

    error = caught.value
    assert isinstance(error, EngineExecutionError)
    assert error.returncode == 2
    assert error.cmd[:2] == [sys.executable, "-c"]
    assert error.stdout == error.output == stdout
    assert error.stderr == stderr
    assert isinstance(error.__cause__, subprocess.CalledProcessError)
    assert "exit status 2" in str(error)
    for label, diagnostic in (("stdout", stdout), ("stderr", stderr)):
        if diagnostic:
            assert f"{label}:\n{diagnostic.rstrip()}" in str(error)
    assert not list(scratch.iterdir())
    assert original.read_bytes() == b"original"
    assert modified.read_bytes() == b"modified"
