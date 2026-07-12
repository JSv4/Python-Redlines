"""Tests for the GitHub Action driver script (action/redline_changed.py).

Most tests exercise the pure/git-only helpers and need no engine binaries;
the two integration tests at the bottom run the real DocxodusEngine against
the repo fixtures, matching the requirements of the other test modules.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'action'))

import redline_changed as ra  # noqa: E402

FIXTURES = REPO_ROOT / 'tests' / 'fixtures'


def git(repo, *args, check=True):
    return subprocess.run(['git', '-C', str(repo)] + list(args), check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'repo'
    path.mkdir()
    git(path, 'init', '-q')
    git(path, 'config', 'user.email', 'test@example.com')
    git(path, 'config', 'user.name', 'Test')
    return path


def commit_file(repo, rel, data: bytes, message='commit'):
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', message)
    return git(repo, 'rev-parse', 'HEAD')


# ---------------------------------------------------------------------------
# input parsing / validation
# ---------------------------------------------------------------------------

def test_inputs_defaults():
    inputs = ra.Inputs.from_env({})
    assert inputs.engine == 'docxodus'
    assert inputs.files == '**/*.docx'
    assert inputs.output_dir == 'redlines'
    assert inputs.html_preview == 'auto'
    assert inputs.write_summary is True
    assert inputs.engine_kwargs() == {}


def test_inputs_engine_kwargs():
    inputs = ra.Inputs.from_env({
        'INPUT_COMPARISON': 'docxdiff',
        'INPUT_DETECT_MOVES': 'true',
    })
    assert inputs.engine_kwargs() == {'engine': 'docxdiff', 'detect_moves': True}


@pytest.mark.parametrize('env', [
    {'INPUT_ENGINE': 'wordperfect'},
    {'INPUT_HTML_PREVIEW': 'maybe'},
    {'INPUT_ORIGINAL': 'a.docx'},                              # original without modified
    {'INPUT_ENGINE': 'xmlpowertools', 'INPUT_COMPARISON': 'docxdiff'},
    {'INPUT_ENGINE': 'xmlpowertools', 'INPUT_DETECT_MOVES': 'true'},
    {'INPUT_DETECT_MOVES': 'yes'},                             # not a bool
])
def test_inputs_rejects_bad_combinations(env):
    with pytest.raises(ra.ConfigError):
        ra.Inputs.from_env(env)


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('stdout,expected', [
    ('Revisions found: 9', 9),
    ('Redline complete: 11 revision(s) found', 11),
    ('nothing to see here', None),
    (None, None),
])
def test_revision_count_from_stdout(stdout, expected):
    assert ra.revision_count_from_stdout(stdout) == expected


def test_parse_name_status_handles_modifications_and_renames():
    raw = b'M\0docs/contract.docx\0R097\0old name.docx\0new name.docx\0A\0added.docx\0D\0gone.docx\0'
    changes = ra.parse_name_status(raw)
    assert [(c.status, c.path, c.previous_path) for c in changes] == [
        ('modified', 'docs/contract.docx', None),
        ('renamed', 'new name.docx', 'old name.docx'),
        ('added', 'added.docx', None),
        ('deleted', 'gone.docx', None),
    ]


def test_redline_output_paths_mirror_source_tree():
    docx, html = ra.redline_output_paths('redlines', 'docs/deals/Contract.DOCX')
    assert docx.as_posix() == 'redlines/docs/deals/Contract.redline.docx'
    assert html.as_posix() == 'redlines/docs/deals/Contract.redline.html'


def test_redline_output_paths_absolute_source_stays_under_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inside = tmp_path / 'docs' / 'a.docx'
    docx, _ = ra.redline_output_paths('out', str(inside))
    assert docx.as_posix() == 'out/docs/a.redline.docx'
    outside = '/somewhere/else/entirely/b.docx'
    docx, _ = ra.redline_output_paths('out', outside)
    assert docx.as_posix() == 'out/b.redline.docx'


def test_build_summary_lists_each_change():
    changes = [
        ra.Change(path='a.docx', status='modified', revisions=3,
                  redline='redlines/a.redline.docx'),
        ra.Change(path='b.docx', status='added'),
        ra.Change(path='c.docx', status='modified', error='boom'),
    ]
    summary = ra.build_summary(changes, 'a' * 40, 'b' * 40)
    assert '| `a.docx` | Modified | 3 | `redlines/a.redline.docx` | — |' in summary
    assert 'Added (no base version to compare)' in summary
    assert '⚠️ failed' in summary


def test_build_summary_no_changes():
    summary = ra.build_summary([], None, None)
    assert 'No changed `.docx` files' in summary


def test_write_outputs(tmp_path):
    out = tmp_path / 'out.txt'
    changes = [ra.Change(path='a.docx', status='modified', revisions=2,
                         redline='redlines/a.redline.docx')]
    ra.write_outputs(changes, {'GITHUB_OUTPUT': str(out)})
    text = out.read_text()
    assert 'count=1\n' in text
    assert 'any-changes=true\n' in text
    payload = [line for line in text.splitlines() if line.startswith('redlines=')][0]
    parsed = json.loads(payload[len('redlines='):])
    assert parsed[0]['path'] == 'a.docx'
    assert parsed[0]['revisions'] == 2


# ---------------------------------------------------------------------------
# git plumbing against a real temporary repository
# ---------------------------------------------------------------------------

def test_detect_changes_and_read_blob(repo):
    base = commit_file(repo, 'docs/contract.docx', b'original bytes')
    (repo / 'notes.txt').write_text('irrelevant')
    head = commit_file(repo, 'docs/contract.docx', b'modified bytes')

    changes = ra.detect_changes(base, head, ['**/*.docx'], cwd=str(repo))
    assert [(c.status, c.path) for c in changes] == [('modified', 'docs/contract.docx')]
    assert ra.read_blob(base, 'docs/contract.docx', cwd=str(repo)) == b'original bytes'
    assert ra.read_blob(head, 'docs/contract.docx', cwd=str(repo)) == b'modified bytes'


def test_detect_changes_pure_rename(repo):
    base = commit_file(repo, 'a.docx', b'same bytes either way')
    git(repo, 'mv', 'a.docx', 'b.docx')
    git(repo, 'commit', '-q', '-m', 'rename')
    head = git(repo, 'rev-parse', 'HEAD')

    changes = ra.detect_changes(base, head, ['**/*.docx'], cwd=str(repo))
    assert [(c.status, c.path, c.previous_path) for c in changes] == [
        ('renamed', 'b.docx', 'a.docx')]


def test_detect_changes_respects_patterns_and_extension(repo):
    base = commit_file(repo, 'docs/in-scope.docx', b'v1')
    (repo / 'other.docx').write_bytes(b'v1')
    (repo / 'docs' / 'readme.txt').write_text('v1')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', 'more files')
    (repo / 'docs' / 'in-scope.docx').write_bytes(b'v2')
    (repo / 'other.docx').write_bytes(b'v2')
    (repo / 'docs' / 'readme.txt').write_text('v2')
    git(repo, 'add', '-A')
    head = commit_file(repo, 'docs/in-scope.docx', b'v3')

    changes = ra.detect_changes(base, head, ['docs/*.docx'], cwd=str(repo))
    assert [c.path for c in changes] == ['docs/in-scope.docx']


def test_resolve_refs_push_event(repo):
    base = commit_file(repo, 'a.docx', b'v1')
    head = commit_file(repo, 'a.docx', b'v2')
    inputs = ra.Inputs.from_env({})
    resolved = ra.resolve_refs(
        inputs, {'GITHUB_EVENT_NAME': 'push'},
        {'before': base, 'after': head}, cwd=str(repo))
    assert resolved == (base, head)


def test_resolve_refs_push_event_new_branch_uses_parent(repo):
    base = commit_file(repo, 'a.docx', b'v1')
    head = commit_file(repo, 'a.docx', b'v2')
    inputs = ra.Inputs.from_env({})
    resolved = ra.resolve_refs(
        inputs, {'GITHUB_EVENT_NAME': 'push'},
        {'before': '0' * 40, 'after': head}, cwd=str(repo))
    assert resolved == (base, head)


def test_resolve_refs_pull_request_uses_merge_base(repo):
    fork_point = commit_file(repo, 'a.docx', b'v1')
    default_branch = git(repo, 'rev-parse', '--abbrev-ref', 'HEAD')
    git(repo, 'checkout', '-q', '-b', 'feature')
    pr_head = commit_file(repo, 'a.docx', b'feature edit')
    git(repo, 'checkout', '-q', default_branch)
    base_tip = commit_file(repo, 'unrelated.txt', b'base moved on')

    inputs = ra.Inputs.from_env({})
    event = {'pull_request': {'base': {'sha': base_tip}, 'head': {'sha': pr_head}}}
    resolved = ra.resolve_refs(
        inputs, {'GITHUB_EVENT_NAME': 'pull_request'}, event, cwd=str(repo))
    assert resolved == (fork_point, pr_head)


def test_resolve_refs_explicit_inputs_win(repo):
    base = commit_file(repo, 'a.docx', b'v1')
    head = commit_file(repo, 'a.docx', b'v2')
    inputs = ra.Inputs.from_env({'INPUT_BASE_REF': 'HEAD~1', 'INPUT_HEAD_REF': 'HEAD'})
    resolved = ra.resolve_refs(inputs, {'GITHUB_EVENT_NAME': 'push'}, {}, cwd=str(repo))
    assert resolved == (base, head)


def test_resolve_refs_unresolvable_ref_raises(repo):
    commit_file(repo, 'a.docx', b'v1')
    inputs = ra.Inputs.from_env({'INPUT_BASE_REF': 'no-such-ref', 'INPUT_HEAD_REF': 'HEAD'})
    with pytest.raises(ra.ConfigError):
        ra.resolve_refs(inputs, {}, {}, cwd=str(repo))


# ---------------------------------------------------------------------------
# integration: run main() with the real engine over the repo fixtures
# ---------------------------------------------------------------------------

def test_main_explicit_pair(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    out_file, summary_file = tmp_path / 'out.txt', tmp_path / 'summary.md'
    env = {
        'INPUT_ORIGINAL': str(FIXTURES / 'original.docx'),
        'INPUT_MODIFIED': str(FIXTURES / 'modified.docx'),
        'INPUT_OUTPUT_DIR': str(tmp_path / 'redlines'),
        'INPUT_HTML_PREVIEW': 'false',
        'GITHUB_OUTPUT': str(out_file),
        'GITHUB_STEP_SUMMARY': str(summary_file),
    }
    assert ra.main(env) == 0

    text = out_file.read_text()
    assert 'count=1\n' in text
    payload = [line for line in text.splitlines() if line.startswith('redlines=')][0]
    record = json.loads(payload[len('redlines='):])[0]
    assert record['revisions'] == 9
    redline = Path(record['redline'])
    assert redline.is_file() and redline.stat().st_size > 0
    # absolute source paths must not escape the requested output directory
    assert (tmp_path / 'redlines') in redline.resolve().parents
    assert 'DOCX redlines' in summary_file.read_text()


def test_main_auto_detect_over_git_history(repo, tmp_path, monkeypatch):
    base = commit_file(repo, 'contracts/agreement.docx',
                       (FIXTURES / 'original.docx').read_bytes())
    head = commit_file(repo, 'contracts/agreement.docx',
                       (FIXTURES / 'modified.docx').read_bytes())
    monkeypatch.chdir(repo)

    out_file, summary_file = tmp_path / 'out.txt', tmp_path / 'summary.md'
    env = {
        'INPUT_BASE_REF': base,
        'INPUT_HEAD_REF': head,
        'INPUT_OUTPUT_DIR': str(tmp_path / 'redlines'),
        'INPUT_HTML_PREVIEW': 'false',
        'GITHUB_OUTPUT': str(out_file),
        'GITHUB_STEP_SUMMARY': str(summary_file),
    }
    assert ra.main(env) == 0

    payload = [line for line in out_file.read_text().splitlines()
               if line.startswith('redlines=')][0]
    record = json.loads(payload[len('redlines='):])[0]
    assert record['path'] == 'contracts/agreement.docx'
    assert record['status'] == 'modified'
    assert record['revisions'] == 9
    assert Path(record['redline']).is_file()
    assert 'contracts/agreement.docx' in summary_file.read_text()
