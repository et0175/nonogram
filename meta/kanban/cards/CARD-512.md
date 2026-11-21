# CARD-512: Two test-instrument holes from wave 7: the session lock's escape hatch and test_wraps' paint check

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/512-lock-escape-paint-check
**Worktree:** —
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-220 (CARD-508 review F-001) and IDEA-222 (CARD-507 review F-006), bundled: each alone is below `sizing.min_estimate`.
**Idea:** IDEA-220, IDEA-222
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_db_isolation.py or tests/test_card_156_db_fixture.py (the lock's existing tests), tests/test_puzzle_solver_maybe.py
**UI surface:** —
**Review score:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-220.** CARD-508's `_session_lock` (tests/conftest.py) lets a child pytest through when `NONOGRAM_TEST_DB_SESSION_LOCK` is set, and trusts the variable alone. Exported by hand or left in a shell, it lets a concurrent run in, and the measured result was the very wipe CARD-508 fixed (`UndefinedTable: relation "batches" does not exist`). Reviewer's suggestion: carry the holder's pid (or the lock's own identity) in the value, and have the child confirm in `pg_locks` that the advisory lock is really held by a live session before skipping it.
2. **IDEA-222.** test_wraps (tests/test_puzzle_solver_maybe.py, CARD-507) checks that the solved name's third line does not cover the controls with `elementsFromPoint`. It passes 6/6 when `overflow: hidden` is replaced by `pointer-events: none`, while lines 3+ still paint over the controls: it follows hit-testing, not paint. A clip-rect check (the span's painted box, or the rendered text's range rects, against the controls' boxes), or a pixel comparison, closes it.

## What to implement

Re-verify each against main first.

1. The escape works only for a real child of the holding run: a stale or hand-set value no longer disables the lock.
2. test_wraps' overflow assertion judges what is painted, not what is hit-tested.

## Acceptance criteria

* **AC-1**: with the variable set by hand (no holder, or a dead holder) while another run holds the lock, the second run is refused with the existing "another pytest run is using it" message; a real child of the holder still runs. Control: main's conftest lets the hand-set run in.
* **AC-2**: test_wraps reds under the `pointer-events: none` plant (and still reds under removing `overflow: hidden`), and is green on main's CSS.
* **AC-3**: net test count at most +1; report it.

## Guardrails

* **G-1**: tests/conftest.py is a gate-wide file: the merge gate will run the full suite. Report skips with `-rfs` (30 unarmed expected: 29 DATABASE_URL + 1 setrlimit).
* **G-2**: never connect to the production database; lock tests use the worktree's own `*_test` database on localhost.
* **G-3**: if a test_wraps node id changes, record it in tests/test_browser_fixture_scope.py's `RENAMED_SINCE_BEFORE`.

## Worktree notes
