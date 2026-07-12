"""Driver script for the python-redlines GitHub Action.

Generates Word tracked-changes ("redline") documents for .docx files, either
for an explicit original/modified pair or for every .docx changed between two
git commits (the PR base and head by default). Optionally converts each
redline to an HTML preview via the Docx2Html dotnet tool.

The script is intentionally stdlib-only (plus python-redlines itself) and
runs from the repository root ($GITHUB_WORKSPACE). Inputs arrive as INPUT_*
environment variables mapped in action.yml; results are written to
$GITHUB_OUTPUT and $GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ZERO_SHA = re.compile(r'^0+$')
REVISION_COUNT = re.compile(r'(?:Revisions found:|Redline complete:)\s*(\d+)')

ENGINES = ('docxodus', 'xmlpowertools')
HTML_PREVIEW_MODES = ('auto', 'true', 'false')

# kwargs only DocxodusEngine understands; XmlPowerToolsEngine would silently
# ignore them, so requesting one with engine=xmlpowertools is a config error.
DOCXODUS_ONLY_INPUTS = ('comparison', 'detect-moves')


class ConfigError(Exception):
    """A bad input combination; reported as ::error:: and exit 1."""


@dataclass
class Change:
    """One changed .docx file between the two compared commits."""
    path: str                          # path in the head commit (or base for deletions)
    status: str                        # 'modified' | 'renamed' | 'added' | 'deleted' | 'explicit'
    previous_path: Optional[str] = None  # old path for renames
    revisions: Optional[int] = None
    redline: Optional[str] = None
    html: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'previous_path': self.previous_path,
            'status': self.status,
            'revisions': self.revisions,
            'redline': self.redline,
            'html': self.html,
            'error': self.error,
        }


@dataclass
class Inputs:
    original: str = ''
    modified: str = ''
    files: str = '**/*.docx'
    base_ref: str = ''
    head_ref: str = ''
    author: str = 'python-redlines'
    engine: str = 'docxodus'
    comparison: str = ''
    detect_moves: bool = False
    output_dir: str = 'redlines'
    html_preview: str = 'auto'
    write_summary: bool = True
    raw: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Dict[str, str]) -> 'Inputs':
        def get(name: str, default: str = '') -> str:
            return env.get('INPUT_' + name.upper().replace('-', '_'), default).strip()

        def get_bool(name: str, default: bool) -> bool:
            value = get(name, 'true' if default else 'false').lower()
            if value not in ('true', 'false'):
                raise ConfigError(f"Input '{name}' must be 'true' or 'false', got '{value}'")
            return value == 'true'

        inputs = cls(
            original=get('original'),
            modified=get('modified'),
            files=get('files') or '**/*.docx',
            base_ref=get('base-ref'),
            head_ref=get('head-ref'),
            author=get('author') or 'python-redlines',
            engine=(get('engine') or 'docxodus').lower(),
            comparison=get('comparison').lower(),
            detect_moves=get_bool('detect-moves', False),
            output_dir=get('output-dir') or 'redlines',
            html_preview=(get('html-preview') or 'auto').lower(),
            write_summary=get_bool('summary', True),
        )
        inputs.raw = {k: v for k, v in env.items() if k.startswith('INPUT_')}
        inputs.validate()
        return inputs

    def validate(self) -> None:
        if self.engine not in ENGINES:
            raise ConfigError(f"Input 'engine' must be one of {ENGINES}, got '{self.engine}'")
        if self.html_preview not in HTML_PREVIEW_MODES:
            raise ConfigError(
                f"Input 'html-preview' must be one of {HTML_PREVIEW_MODES}, got '{self.html_preview}'")
        if bool(self.original) != bool(self.modified):
            raise ConfigError(
                "Inputs 'original' and 'modified' must be provided together "
                "(explicit-pair mode) or both left empty (auto-detect mode).")
        if self.engine != 'docxodus':
            if self.comparison:
                raise ConfigError(
                    "Input 'comparison' is only supported by the docxodus engine.")
            if self.detect_moves:
                raise ConfigError(
                    "Input 'detect-moves' is only supported by the docxodus engine.")

    def engine_kwargs(self) -> Dict:
        kwargs: Dict = {}
        if self.comparison:
            kwargs['engine'] = self.comparison
        if self.detect_moves:
            kwargs['detect_moves'] = True
        return kwargs


# --------------------------------------------------------------------------
# git helpers
# --------------------------------------------------------------------------

def run_git(args: List[str], cwd: Optional[str] = None, binary: bool = False):
    result = subprocess.run(
        ['git'] + args, cwd=cwd, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout if binary else result.stdout.decode('utf-8', 'replace')


def try_git(args: List[str], cwd: Optional[str] = None) -> Optional[str]:
    try:
        return run_git(args, cwd=cwd).strip()
    except subprocess.CalledProcessError:
        return None


def resolve_commit(ref: str, cwd: Optional[str] = None) -> str:
    """Resolve ref to a commit sha, fetching it from origin when absent locally."""
    sha = try_git(['rev-parse', '--verify', '--quiet', ref + '^{commit}'], cwd=cwd)
    if sha:
        return sha
    # PR base/head shas are often absent from a shallow checkout; GitHub allows
    # fetching them directly because they are reachable from branch refs.
    try_git(['fetch', '--no-tags', '--depth=1', 'origin', ref], cwd=cwd)
    sha = try_git(['rev-parse', '--verify', '--quiet', ref + '^{commit}'], cwd=cwd)
    if sha:
        return sha
    raise ConfigError(
        f"Could not resolve '{ref}' to a commit. Check out the repository with "
        "'fetch-depth: 0' (actions/checkout) so both sides of the comparison are available.")


def resolve_refs(inputs: Inputs, env: Dict[str, str], event: Dict,
                 cwd: Optional[str] = None) -> Tuple[str, str]:
    """Decide which two commits to compare.

    Priority: explicit base-ref/head-ref inputs, then the triggering event
    (PR base/head, push before/after), then HEAD~1..HEAD.
    For PR events the merge-base of base and head is used when computable, so
    the redline matches the PR's "files changed" view even if the base branch
    has moved on.
    """
    event_name = env.get('GITHUB_EVENT_NAME', '')

    if inputs.base_ref or inputs.head_ref:
        if not (inputs.base_ref and inputs.head_ref):
            raise ConfigError("Inputs 'base-ref' and 'head-ref' must be provided together.")
        return (resolve_commit(inputs.base_ref, cwd=cwd),
                resolve_commit(inputs.head_ref, cwd=cwd))

    if event_name in ('pull_request', 'pull_request_target') and 'pull_request' in event:
        base = resolve_commit(event['pull_request']['base']['sha'], cwd=cwd)
        head = resolve_commit(event['pull_request']['head']['sha'], cwd=cwd)
        merge_base = try_git(['merge-base', base, head], cwd=cwd)
        if merge_base:
            base = merge_base
        else:
            print(f"::warning::Could not compute the merge-base of {base[:12]} and "
                  f"{head[:12]} (shallow clone?); comparing against the base branch tip "
                  "instead. Use 'fetch-depth: 0' on actions/checkout for exact PR semantics.")
        return base, head

    if event_name == 'push':
        after = event.get('after') or env.get('GITHUB_SHA', 'HEAD')
        before = event.get('before', '')
        if before and not ZERO_SHA.match(before):
            return resolve_commit(before, cwd=cwd), resolve_commit(after, cwd=cwd)
        head = resolve_commit(after, cwd=cwd)
        parent = try_git(['rev-parse', '--verify', '--quiet', head + '~1'], cwd=cwd)
        if parent:
            return parent, head
        raise ConfigError(
            "This push has no previous commit to compare against "
            "(new branch or initial commit). Set 'base-ref' explicitly.")

    head = resolve_commit(env.get('GITHUB_SHA') or 'HEAD', cwd=cwd)
    parent = try_git(['rev-parse', '--verify', '--quiet', head + '~1'], cwd=cwd)
    if not parent:
        raise ConfigError(
            "HEAD has no parent commit to compare against. Set 'base-ref' explicitly.")
    return parent, head


def parse_name_status(raw: bytes) -> List[Change]:
    """Parse `git diff --name-status -z` output into Change records."""
    fields = [f.decode('utf-8', 'replace') for f in raw.split(b'\0') if f]
    changes: List[Change] = []
    i = 0
    while i < len(fields):
        status = fields[i]
        if status.startswith(('R', 'C')):  # rename/copy: score, old path, new path
            old, new = fields[i + 1], fields[i + 2]
            changes.append(Change(path=new, previous_path=old, status='renamed'))
            i += 3
            continue
        path = fields[i + 1]
        kind = {'M': 'modified', 'A': 'added', 'D': 'deleted', 'T': 'modified'}.get(status[0])
        if kind:
            changes.append(Change(path=path, status=kind))
        i += 2
    return changes


def detect_changes(base: str, head: str, patterns: List[str],
                   cwd: Optional[str] = None) -> List[Change]:
    pathspecs = [f':(glob,icase){p}' for p in patterns]
    raw = run_git(['diff', '--name-status', '-z', '--find-renames',
                   base, head, '--'] + pathspecs, cwd=cwd, binary=True)
    changes = parse_name_status(raw)
    return [c for c in changes if c.path.lower().endswith('.docx')]


def read_blob(commit: str, path: str, cwd: Optional[str] = None) -> bytes:
    return run_git(['cat-file', 'blob', f'{commit}:{path}'], cwd=cwd, binary=True)


# --------------------------------------------------------------------------
# redline + preview generation
# --------------------------------------------------------------------------

def _as_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value or ''


def make_engine(inputs: Inputs):
    from python_redlines.engines import DocxodusEngine, XmlPowerToolsEngine
    return DocxodusEngine() if inputs.engine == 'docxodus' else XmlPowerToolsEngine()


def revision_count_from_stdout(stdout: Optional[str]) -> Optional[int]:
    if not stdout:
        return None
    match = REVISION_COUNT.search(stdout)
    return int(match.group(1)) if match else None


def redline_output_paths(output_dir: str, source_path: str) -> Tuple[Path, Path]:
    """Mirror the source's relative directory tree under output_dir."""
    rel = Path(source_path)
    # An absolute path joined onto output_dir would replace it entirely, and a
    # '..' component would escape it. Note is_absolute() alone is not enough on
    # Windows, where a rooted-but-driveless path ('/x/y') still hijacks a join.
    if rel.is_absolute() or rel.drive or rel.root or '..' in rel.parts:
        try:
            rel = rel.relative_to(Path.cwd())
        except ValueError:
            rel = Path(rel.name)
    stem = rel.name[:-len('.docx')] if rel.name.lower().endswith('.docx') else rel.name
    base = Path(output_dir) / rel.parent / stem
    return Path(str(base) + '.redline.docx'), Path(str(base) + '.redline.html')


def find_docx2html() -> Optional[str]:
    exe = shutil.which('docx2html')
    if not exe:
        return None
    try:
        result = subprocess.run([exe, '--help'], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=120)
        help_text = result.stdout.decode('utf-8', 'replace')
    except (OSError, subprocess.TimeoutExpired):
        return None
    return exe if '--track-changes' in help_text else None


def resolve_previewer(inputs: Inputs) -> Optional[str]:
    if inputs.html_preview == 'false':
        return None
    exe = find_docx2html()
    if exe:
        return exe
    message = (
        "HTML previews need the Docx2Html dotnet tool with --track-changes support "
        "(Docxodus >= 7.1.0) on PATH. Install it with "
        "'dotnet tool install --global Docx2Html', or set html-preview: 'false'.")
    if inputs.html_preview == 'true':
        raise ConfigError(message)
    print(f"::warning::Skipping HTML previews. {message}")
    return None


def generate_preview(previewer: str, redline_path: Path, html_path: Path) -> bool:
    result = subprocess.run(
        [previewer, str(redline_path), str(html_path), '--track-changes'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        output = result.stdout.decode('utf-8', 'replace').strip()
        print(f"::warning::docx2html failed for {redline_path}: {output}")
        return False
    return True


def run_redline_pair(engine, inputs: Inputs, change: Change,
                     original: bytes, modified: bytes,
                     previewer: Optional[str]) -> None:
    if original == modified:
        # e.g. a pure rename — nothing to redline.
        change.revisions = 0
        return

    redline_path, html_path = redline_output_paths(inputs.output_dir, change.path)
    redline_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        redline_bytes, stdout, stderr = engine.run_redline(
            inputs.author, original, modified, **inputs.engine_kwargs())
    except subprocess.CalledProcessError as exc:
        detail = _as_text(exc.stderr) or _as_text(exc.stdout)
        change.error = detail.strip() or f'engine exited with code {exc.returncode}'
        print(f'::error::Redline generation failed for {change.path}: {change.error}')
        return

    if stderr:
        print(f"::warning::redline engine stderr for {change.path}: {stderr.strip()}")

    redline_path.write_bytes(redline_bytes)
    change.redline = redline_path.as_posix()
    change.revisions = revision_count_from_stdout(stdout)

    if previewer and generate_preview(previewer, redline_path, html_path):
        change.html = html_path.as_posix()


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

STATUS_LABELS = {
    'modified': 'Modified',
    'renamed': 'Renamed',
    'added': 'Added (no base version to compare)',
    'deleted': 'Deleted (no head version to compare)',
    'explicit': 'Explicit pair',
}


def build_summary(changes: List[Change], base: Optional[str], head: Optional[str]) -> str:
    lines = ['## 📕 DOCX redlines', '']
    if base and head:
        lines.append(f'Compared `{base[:12]}` → `{head[:12]}`.')
        lines.append('')
    if not changes:
        lines.append('No changed `.docx` files matched the configured patterns.')
        return '\n'.join(lines) + '\n'

    lines.append('| File | Change | Revisions | Redline | HTML preview |')
    lines.append('|---|---|---|---|---|')
    for c in changes:
        name = f'`{c.path}`'
        if c.previous_path:
            name = f'`{c.previous_path}` → `{c.path}`'
        revisions = str(c.revisions) if c.revisions is not None else '—'
        redline = f'`{c.redline}`' if c.redline else '—'
        if c.error:
            redline = '⚠️ failed'
        html = f'`{c.html}`' if c.html else '—'
        lines.append(f'| {name} | {STATUS_LABELS[c.status]} | {revisions} | {redline} | {html} |')

    if any(c.redline for c in changes):
        lines.append('')
        lines.append('Redline documents carry native Word tracked changes: open one in '
                     'Word/LibreOffice to review, accept, or reject each edit.')
    return '\n'.join(lines) + '\n'


def append_to_file(env_var: str, content: str, env: Dict[str, str]) -> None:
    path = env.get(env_var)
    if not path:
        return
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(content)


def write_outputs(changes: List[Change], env: Dict[str, str]) -> None:
    generated = [c for c in changes if c.redline]
    payload = json.dumps([c.to_dict() for c in changes], separators=(',', ':'))
    content = (
        f'count={len(generated)}\n'
        f'any-changes={"true" if changes else "false"}\n'
        f'redlines={payload}\n'
    )
    append_to_file('GITHUB_OUTPUT', content, env)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def load_event(env: Dict[str, str]) -> Dict:
    path = env.get('GITHUB_EVENT_PATH')
    if path and os.path.isfile(path):
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    return {}


def main(env: Dict[str, str]) -> int:
    inputs = Inputs.from_env(env)
    previewer = resolve_previewer(inputs)
    base = head = None

    if inputs.original:  # explicit-pair mode
        for label, candidate in (('original', inputs.original), ('modified', inputs.modified)):
            if not os.path.isfile(candidate):
                raise ConfigError(f"Input '{label}' file not found: {candidate}")
        changes = [Change(path=inputs.modified, previous_path=inputs.original, status='explicit')]
        engine = make_engine(inputs)
        run_redline_pair(engine, inputs, changes[0],
                         Path(inputs.original).read_bytes(),
                         Path(inputs.modified).read_bytes(),
                         previewer)
    else:  # auto-detect mode
        event = load_event(env)
        base, head = resolve_refs(inputs, env, event)
        patterns = [line.strip() for line in inputs.files.splitlines() if line.strip()]
        changes = detect_changes(base, head, patterns)
        comparable = [c for c in changes if c.status in ('modified', 'renamed')]
        print(f'Found {len(changes)} changed .docx file(s) between '
              f'{base[:12]} and {head[:12]}; {len(comparable)} comparable.')
        if comparable:
            engine = make_engine(inputs)
            for change in comparable:
                original = read_blob(base, change.previous_path or change.path)
                modified = read_blob(head, change.path)
                run_redline_pair(engine, inputs, change, original, modified, previewer)
                print(f'  {change.path}: {change.revisions} revision(s) '
                      f'-> {change.redline}')

    write_outputs(changes, env)
    if inputs.write_summary:
        append_to_file('GITHUB_STEP_SUMMARY', build_summary(changes, base, head), env)

    failed = [c for c in changes if c.error]
    if failed:
        print(f'::error::Redline generation failed for {len(failed)} file(s).')
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(dict(os.environ)))
    except ConfigError as error:
        print(f'::error::{error}')
        sys.exit(1)
