# CARD-518: Two one-line follow-ups from wave 10's reviews: the kill matrix's stale inode key, and the guard's trim held equal to the app's

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/518-review-followups
**Worktree:** ../PythonProject4-card-518
**Source:** roadmap wave 11, cut 2026-11-22 on the owner's "start the no-decision wave 11". CARD-315 review 2 F-001 and F-002; CARD-515 review 2 F-202.
**Idea:** —
**Wave:** 90
**Created wave:** 90
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py, tests/database_guard.py, tests/test_card_109_database_guard.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-22T10:32Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **CARD-315 review 2, F-001 (medium).** `Runner._expect` (tests/kill_matrix.py) keys the foreign-write check on `(st_dev, st_ino)` and never retires an old key. A byte-identical rewrite that gives a registered file a new inode during a reading (an editor's safe-save via `os.replace`, git's unlink-and-recreate) is then reported as `ConcurrentWrite` at the next mutant's before-check, and the "foreign" copy it keeps is the instrument's own mutant. It fails closed, but the message's premise is false. The reviewer's fix: drop any existing entry for the same file before inserting a new one.
2. **CARD-315 review 2, F-002 (low).** When a foreign writer deletes a registered file, the run keeps its temp tree but the message names no directory, so `_discard_workdir`'s docstring ("the exception names it") is false for that case.
3. **CARD-515 review 2, F-202 (low).** `tests/database_guard.py`'s `_trimmed` is a deliberate second copy of `nonogram.db.session.trimmed_url` (the guard must not import `nonogram` at configure time). Nothing holds the two equal. CLAUDE.md's precedent for a copied rule (`mask_runs`) is cross-checked against the original from the test tree.

## Acceptance criteria

* **AC-1**: a same-bytes rewrite of a registered file onto a new inode during a reading no longer raises `ConcurrentWrite` (control: today's `_expect` reds it), and a different-bytes rewrite onto a new inode still does. Shown inside the existing AC-4 test, not a new test.
* **AC-2**: a foreign delete's `ConcurrentWrite` message names the kept directory, or the docstring is corrected to say it does not; with a control if behaviour changes.
* **AC-3**: an existing guard test asserts `database_guard._trimmed(v) == session.trimmed_url(v)` over a corpus of padded, blank, whitespace-only and None values (importing `nonogram` there is legal; it is a test, not the guard). Control: a mutant of either reds it.
* **AC-4**: net test count 0; report it.

## Guardrails

* **G-1**: the guard module itself still imports nothing from `nonogram`.
* **G-2**: never leave a mutant on disk; restore and verify by sha256.

## Worktree notes
