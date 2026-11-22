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

### [Implementation] 2026-11-22

**Premises, re-measured before the fix.** F-001: with today's `Runner._expect`, a byte-identical `os.replace` onto the target during the `SHIPPED` reading makes the next mutant's before-check raise `ConcurrentWrite: AFTER: [...km_simple_target.py] no longer hold what this instrument last wrote there, before its child pytest started`, and the "foreign" copy it keeps is the instrument's own mutant (control C1 below is that run). F-002: a foreign delete gave a message with no directory in it (the new delete row of the AC-4 test, red against the unchanged instrument, `assert (None)` on the tree regex). F-202: `ast` over `tests/` finds no test that references `database_guard._trimmed` or `trimmed_url` (the two hits are `conftest.py`'s calls to `_trimmed`, in no test).

**What changed.**
- `tests/kill_matrix.py`, `Runner._expect`: before it records a key, it retires every older key whose recorded spelling now `os.stat`s to the same `(st_dev, st_ino)` (AC-1). A different-bytes rewrite is still caught by the after-child check of the reading it happened in, before any `_expect` runs.
- `tests/kill_matrix.py`, `Runner._refuse_on_foreign_write`: an in-place run's message now always ends `This run's temp tree, <dir>, is kept.`, including a foreign delete, where nothing is copied (AC-2). `_discard_workdir`'s "the exception names it" is now true for that case, so its docstring is unchanged.
- `tests/test_kill_matrix.py`, `test_ac4_a_leaked_patch_is_caught_by_the_shipped_re_run_between_mutants` (extended, not duplicated): `WrittenUnder` plants in place, onto a new inode (`replace`, the test asserts the inode really changed), or as a delete. The writer loop gains two rows on the `AFTER` reading: pristine bytes onto a new inode (still `ConcurrentWrite`, AC-1 second half), and a delete (message names the kept tree, no copy, AC-2). Every row now asserts that the named tree exists and holds the copy, then removes that tree. One more run: the same bytes onto a new inode during `SHIPPED`, which must publish `FAIL` at the MARK cell for `AFTER` (AC-1).
- `tests/test_card_109_database_guard.py`, `test_no_database_at_all_is_the_ordinary_case` (the CARD-515 trim test of the guard, the only guard test that exercises the trim, found by `ast`): asserts `database_guard._trimmed(v) == nonogram.db.session.trimmed_url(v)` over 12 values (None, empty, space, tab, CRLF, space+LF, NBSP, NEL, mixed whitespace-only, a bare URL, a padded URL, a padded URL with an inner space). The `nonogram` import sits inside the test body. Importing `nonogram.db` there emits SQLAlchemy's `MovedIn20Warning` from `nonogram/db/models.py` (a warning, not a failure).

**G-1.** `ast` over `tests/database_guard.py`: its imports are `__future__`, `os`, `pytest`. Nothing from `nonogram`. The file is unchanged.

**Controls.** Each planted by `/private/tmp/claude-501/card518/control.py`: a `cp -p` backup, one replacement asserted to occur once, then the test, then a `cp -p` restore with sha256 matched (all four matched). `git diff --stat` afterwards lists only the three intended files. `src/nonogram/db/session.py` is not in it.
- C1 (AC-1), the retirement in `_expect` neutered (`del` -> `pass`): RED, `tests.kill_matrix.ConcurrentWrite: AFTER: [...] no longer hold what this instrument last wrote there, before its child pytest started. A copy of what it left is kept at [.../foreign.0.km_simple_target.py]`.
- C2 (AC-2), the tree named only when a copy was kept (`if self._keeps_foreign and kept:`, the old shape): RED on the delete row, `AssertionError: ('delete', "AFTER: [...]")` / `assert (None)`.
- C3 (AC-3), the guard's `_trimmed` reduced to `rstrip()`: RED, `AssertionError: '  postgresql://u:p@localhost/nonogram_test\n'`.
- C4 (AC-3), `session.trimmed_url` reduced to `strip(" ")`: RED, `AssertionError: '\t'` / `assert None == '\t'`.
- No separate control for "a different-bytes rewrite onto a new inode still raises". The `replace` row asserts it raises, and that assertion is the evidence.

**Gate (unarmed, `-o addopts= -rfs`).** tests/test_kill_matrix.py, tests/test_card_109_database_guard.py, and their neighbours tests/test_db_isolation.py and tests/test_card_349_cold_database.py (both read the guard's file): 176 passed, 6 skipped, 0 failed, in 116 s. All 6 skips are `Database not reachable: DATABASE_URL is not set`. No `kill-matrix-*` temp tree is left by these runs. Not run armed (the card asks for no armed run).

**AC-4, net test count:** 10692 collected before and 10692 after. Net 0.
