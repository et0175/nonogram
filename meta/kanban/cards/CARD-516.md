# CARD-516: The kill matrix's own anchors and controls hold what they claim

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/516-kill-matrix-anchors
**Worktree:** ../PythonProject4-card-516
**Source:** roadmap wave 9, cut 2026-11-21 on the owner's "yes, start wave 9". IDEA-185, IDEA-187, IDEA-188 (one job: the AC-7 anchors) and IDEA-182, IDEA-184 (weak controls in the same instrument). Full texts: meta/kanban/backlog.md, the five CARD-260 items.
**Idea:** IDEA-182, IDEA-184, IDEA-185, IDEA-187, IDEA-188
**Wave:** 88
**Created wave:** 88
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py, tests/README.md
**UI surface:** —
**Review score:** —
**Started:** 2026-11-21T20:01Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The kill matrix (CARD-260) checks whether tests red when the code they guard is broken. Its own checks are weaker than they read:

1. **Anchors (IDEA-185, 187, 188).** The AC-7 anchor in `tests/test_kill_matrix.py` holds another file (`tests/test_db_engine_lifecycle.py`) by absolute line numbers, checks its four arms only by membership (`set(arms) <= linenos`: any four asserts pass), and pins `src/nonogram/db/session.py` by a substring count. So any edit to the lifecycle file reds the kill-matrix tests (CARD-259 had to edit them), while a swap of arms or a reordered declaration may not red at all. Hold the arms by what they are (their own labels or messages, found by `ast`) and make the session.py pin structural.
2. **Weak controls (IDEA-182).** Five items (a)-(e); (a) is one assert on `GIT_COMMAND.pattern`; (d) and (e) are the AC-4 honest-path and AC-3 `Pass` routing gaps. Close what is still open with the smallest change; drop any that is already closed with one line.
3. **Spawn aliases and one exception class (IDEA-184).** `import subprocess as sp`, `run = subprocess.run` and `functools.partial(subprocess.run, ...)` are invisible to the import census; `_verification_failures` controls the absent-binary `OSError` but not a `shasum` that exits non-zero (`CalledProcessError`). The trailing mkdtemp/mutation-window clause is CARD-315's (still ready); leave it.

These items are from October; re-verify each against main before changing anything.

## Acceptance criteria

* **AC-1**: the AC-7 anchor finds its four arms without stored line numbers: inserting blank lines above them in a copy of `tests/test_db_engine_lifecycle.py` leaves it green, and swapping two arms reds it (both shown in the notes, on a scratch copy; the real file is not edited).
* **AC-2**: the session.py pin reds on a reordered declaration of the three globals and not on an appended name (control shown).
* **AC-3**: each IDEA-182 item (a)-(e) is closed with a named control, or dropped with one line saying why.
* **AC-4**: the three alias routes are either refused by the census with a control each, or named as a stated bound in the docstring; the `CalledProcessError` arm has its own control.
* **AC-5**: net test count at most +2; change existing tests in preference to adding. Report it.

## Guardrails

* **G-1**: `tests/test_db_engine_lifecycle.py` and `src/nonogram/db/session.py` are not edited.
* **G-2**: the kill matrix's measured results on its current selections are unchanged.
* **G-3**: CARD-315's window item is out of scope.

## Worktree notes
