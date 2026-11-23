# CARD-528: The impact selector resolves CLAUDE.md and other root files to their readers instead of the full suite

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/528-impact-root-files
**Worktree:** ../PythonProject4-card-528
**Source:** roadmap wave 14, cut 2026-11-23 on the owner's "pick a no-decision wave from the backlog". IDEA-193 (CARD-261 build-gate finding).
**Idea:** IDEA-193
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/impact_set.py, tests/test_impact_set.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-23T08:10Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`scripts/impact_set.py` picks which tests a merge gate runs. A path outside `KNOWN_ROOTS` (`src/`, `tests/`, `meta/`, `docs/`, `scripts/`, `migrations/`) returns FULL. Re-run on 2026-11-23: `impact_set.py CLAUDE.md` prints FULL, rule outside-known-roots. Failing closed is correct in direction, since an unmodelled path must never narrow the selection. But CLAUDE.md is read by known tests (`tests/test_cli.py`'s `TestComponentMap_*` hold it), so a CLAUDE.md-only change runs about 10,000 tests where a handful would do. The backlog triage found the same for README.md, Procfile, runtime.txt and render.yaml.

## What to implement

1. Re-verify the premise for each root-level tracked file: list them with `git ls-files` and record what the selector prints for each today.
2. For a root file whose readers can be derived the way the selector already derives readers elsewhere (tests that open the file by path, resolved by `ast`), resolve to those readers. A root file with no derivable readers stays FULL, and so does anything in `UNANALYSABLE` (Makefile, pyproject.toml and the like). Apply the selector's existing rule, not a hand-written list of root files.
3. Update the selector's docstring/comments where they state that a root-level `.md` stays FULL.

## Acceptance criteria

* **AC-1**: `impact_set.py CLAUDE.md` prints a selection that includes every test that reads CLAUDE.md, derived and not hand-listed, and does not print FULL. Control: reverting the change makes a named test red.
* **AC-2**: a root file no test reads, and every `UNANALYSABLE` file, still prints FULL. A test covers one of each, with a new untracked root file standing in for "unknown".
* **AC-3**: no path under `KNOWN_ROOTS` changes its selection. Compare the selector's output before and after over a fixed sample of at least 20 changed paths drawn from recent merges, and state the sample in the notes.
* **AC-4**: report the net test count; extend `tests/test_impact_set.py`'s existing tests where they fit.

## Guardrails

* **G-1**: the selector must never narrow on a path it cannot model. Where unsure, FULL.
* **G-2**: the gate scripts (`make test-gate`, the marker deferral) are otherwise unchanged.

## Worktree notes
