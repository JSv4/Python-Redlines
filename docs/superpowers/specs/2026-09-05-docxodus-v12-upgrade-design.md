# Docxodus v12.1.0 upgrade: DocxDiff becomes the only algorithm

**Date:** 2026-09-05
**Status:** Approved, in implementation
**Target release:** python-redlines 1.0.0

## Problem

The `docxodus` submodule is pinned to v7.0.0. Upstream is at v12.1.0, and
**v11.0.0 deleted the `WmlComparer` engine outright** in favour of `DocxDiff`,
which has been the upstream default since v8.0.0 and is now mature.

That removal reaches directly into this repository's public API. Since 0.3.0 we
have exposed the upstream selector as a keyword argument:

```python
engine.run_redline("Reviewer", original, modified, engine="docxdiff")
```

`--engine=` no longer exists on the `redline` CLI. Two more flags —
`--detail-threshold=` and `--simplify-move-markup` — survive only as
warn-and-ignore stubs that upstream describes as kept "one release longer".

## Goals

1. Track upstream to v12.1.0.
2. Remove the dead comparison-settings surface **loudly**, never silently.
3. Fix issue #30 and the data-loss bug found beside it.
4. Ship as 1.0.0 with release notes that lead with the WmlComparer removal.

## Non-goals

- Retiring `XmlPowerToolsEngine` or the `python-redlines-ooxmlpowertools`
  package. It wraps the *original* Open-XML-PowerTools WmlComparer, is a
  separately published wheel that users have pinned, and retiring it is its own
  decision with its own migration story. It gets a `DeprecationWarning` and
  keeps shipping.
- Any change to the `wmlcomparer`-era *output* of already-published versions.
  0.3.0 remains on PyPI for anyone who needs that algorithm.

## Design

### 1. Submodule

`docxodus` v7.0.0 → v12.1.0. Verified unchanged and therefore requiring no
build changes: `TargetFramework` is still `net10.0` and `AssemblyName` is still
`redline`, which `build_differ.py` and `BINARY_BASE_NAME` hardcode respectively.

### 2. `DocxodusEngine` — removed settings become hard errors

`engine`, `detail_threshold` and `simplify_move_markup` raise `ValueError`
naming the argument, the version that removed it, and what to do instead.

**This rejection is the load-bearing part of the change.** Deleting the code
path without it would not produce a breaking change; it would produce a
*wrong-answer* change. `_build_command` only reads keys it knows about, so
`run_redline(..., engine="wmlcomparer")` would become a silently-ignored kwarg
and hand the caller DocxDiff output while they believe they selected
WmlComparer. Rejection also covers `engine="docxdiff"`: it names a selector
that no longer exists, and leaving a vestigial argument that happens to match
the surviving engine invites code that breaks confusingly later.

A second reason the rejection cannot be skipped: v12's CLI writes a *warning to
stderr* for `--detail-threshold=` and `--simplify-move-markup`. `run_redline`
surfaces any non-empty stderr to the caller, so passing them through would
break every `assert stderr is None` in the suite.

**Unknown keyword arguments are also rejected.** Today `detial_threshold=0.5`
is silently discarded. Hard-erroring on removed arguments while still
swallowing typos would be half a fix, and the two failures are indistinguishable
to a user.

Retained and unchanged: `case_insensitive`, `detect_moves`,
`move_similarity_threshold`, `move_minimum_word_count`, `detect_format_changes`,
`conflate_spaces`, `date_time`.

Note for the release notes: upstream v11 remapped `--no-detect-format-changes`
onto `DocxDiffSettings.TrackBlockFormatChanges`, so its meaning shifted from
run-level to block-level format tracking.

### 3. `BaseEngine` — two temp-file bugs

**Issue #30 — leaked `NamedTemporaryFile`.**
`tempfile.NamedTemporaryFile(delete=False).name` constructs the object, takes
its name and drops the only reference. The finalizer then reports
`ResourceWarning: Implicitly cleaning up ...` on CPython 3.13+, once per call,
and the descriptor stays open until collection. Under `-W error` it surfaces as
an unraisable exception attributed to whatever test was running when the
collector fired. Replaced with `tempfile.mkstemp()` + `os.close(fd)`, which is
the right tool when only a path is wanted.

**Data loss on path inputs (found while fixing #30).**
`run_redline` appends `original_path` and `modified_path` to `temp_files`
unconditionally, and the `finally` block `os.remove`s every entry. When the
caller passes a *path* — a documented, type-hinted input mode that
`docs/quickstart.md` demonstrates — those entries are the caller's own files,
and the call deletes both source documents. Only byte inputs are safe, which is
why the GitHub Action (bytes-only) has never hit it.

Fix: register a file for cleanup only when this library created it.

### 4. `XmlPowerToolsEngine`

`DeprecationWarning` on instantiation, naming DocxodusEngine as the
replacement. The class and its wheel keep working.

### 5. GitHub Action

The `comparison` input maps onto the deleted kwarg. It becomes a `ConfigError`
with the same reasoning as the Python surface. `action.yml`, the
`DOCXODUS_ONLY_INPUTS` validation in `action/redline_changed.py`, and
`tests/test_action_script.py` all move together.

### 6. Revision counts are measured, not predicted

v11 and v12 changed region arrangement, surplus table cells, section defaults
and note pruning, so the fixture count was unlikely to be either of the numbers
previously pinned (9 for wmlcomparer, 11 for docxdiff). Measured against a
freshly built v12.1.0 binary on `tests/fixtures/`, it is **10** — neither. Every
assertion and doc table is pinned to that measurement.

The extraction cache must be cleared first: `_extraction_root()` keys on the
installed *binary package* version, which does not change when `__about__.py`
is edited, so a stale `~/.cache/python-redlines` would silently keep serving
the v7 binary.

## Testing

- One rejection test per removed argument, plus unknown-kwarg rejection.
- `ResourceWarning`-as-error regression test for #30.
- A test that path inputs still exist after `run_redline` returns.
- Re-pinned integration counts, measured.
- `DeprecationWarning` on `XmlPowerToolsEngine()`.
- Action config tests for the rejected `comparison` input.

## Release

Version 0.3.0 → **1.0.0** in `packages/core/src/python_redlines/__about__.py`
(the single source of truth all three packages read).

Release notes lead with the removal. Wording is deliberate: *"the Docxodus
engine no longer carries WmlComparer"* — **not** *"Python-Redlines is
WmlComparer-free"*, which would be false while the `ooxmlpowertools` wheel
still ships the original.

The notes must also state that upstream v11 dropped `PreserveInputRevisions`
from `DocxCompare.Compare`'s front door, so output shifts on revision-bearing
inputs. This project's fixtures carry no input revisions and will not catch it;
users comparing already-redlined documents will.
