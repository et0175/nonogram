# CARD-542: The test-database rebuild's ownership and grants note, verified against today's code

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/542-schema-grants
**Worktree:** ../PythonProject4-card-542
**Source:** roadmap wave 18, cut 2026-11-24 on the owner's pick of "a small Wave 18" from the backlog's remaining no-decision items. IDEA-033.
**Idea:** IDEA-033
**Wave:** 97
**Created wave:** 97
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/README.md, src/nonogram/db/session.py (only if a finding cannot be closed in the README)
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T11:23Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-156's review (F-007) noted that `DROP SCHEMA public CASCADE` needs the test role to own `public`, and that the recreated schema loses its default grants; it was documented in `tests/README.md`, not handled in code. Re-checked on main at the cut: the rebuild now lives in `src/nonogram/db/session.py` (its docstring describes the drop and `alembic upgrade head`), and `tests/README.md` says the armed run needs a "`public` schema your role owns". Whether the grants half is still true, still documented, or matters to any test is not known.

## What to implement

1. Verify first, on your worktree's OWN `*_test` database on localhost only (never `nonogram_poc`, never production; the suite resolves the name per worktree). Record: who owns `public` before and after one armed rebuild, and the schema's grants (`\dn+ public`) before and after.
2. If the README already says what the run shows, record moot. If it is missing or wrong, correct `tests/README.md`.
3. Do not change `tests/conftest.py`, `tests/database_guard.py` or any guard: they are protected, and widening a guard is out of scope. Change `session.py` only if a lost grant breaks something a test or the owner's local run needs; otherwise stop and report.

## Acceptance criteria

- AC-1: each in-scope item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a computed figure), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and a fix to a test or to code has one control that fails when the fix is reverted. A comment-only fix records the computed figure instead.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes
