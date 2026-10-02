# CARD-156: The db_session fixture stops dropping tables other tests are using

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** surfaced 2026-09-30 while running the db_required set against a real nonogram_test (backlog); fixture re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** tests/conftest.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`tests/conftest.py`'s function-scoped `db_session` fixture (:178) runs
`DROP TABLE IF EXISTS puzzles CASCADE` and `DROP TABLE IF EXISTS batches CASCADE`
(around :215), then `Base.metadata.create_all`, **before every test** that
uses it. Tests that reach the same database through other fixtures land in the
window where those tables are gone. With a real `nonogram_test` present, running
the `db_required` set shows 3 such failures.

Nobody noticed because without a test database every one of these tests skips
green. So the DB-mode suite has only ever been checked by skipping it.

Dropping with `CASCADE` also removes anything else that depends on those tables
(for example, book tables created by migrations). After the fixture runs, the
schema can drift from what `alembic upgrade head` would build.

## What to do

1. Set up the schema **once per session** (alembic to head, or `create_all` if
   that's the established choice), and isolate per test by truncating or by
   rolling back a transaction. Pick the one that fits how the DB tests already
   use `SessionLocal`.
2. Find the 3 failing tests, name them in the worktree notes, and confirm they
   pass under the new fixture against `nonogram_test`.
3. The fixture must only ever touch the database named by `TEST_DATABASE_URL`
   (default `…/nonogram_test`). Add a guard that refuses to run destructive setup
   against any database whose name doesn't end in `_test`.

## Acceptance criteria

- **AC-1:** With `nonogram_test` reachable, the full `db_required` set passes,
  including the 3 tests that fail today.
  *test: the existing db_required set, run against nonogram_test; the run's
  summary line goes in the worktree notes*
- **AC-2:** The fixture refuses, without touching anything, when the test URL
  names a database that doesn't end in `_test`.
  *test: TestDbFixture_RefusesANonTestDatabase*
- **AC-3:** No `DROP TABLE` runs per test.
  *test: TestDbFixture_SchemaIsBuiltOncePerSession*

## Guardrails

- G-1: **Never touch `nonogram_dev`** or any database other than `nonogram_test`.
  `nonogram_test` may be reset; nothing else may.
- G-2: Without a reachable test database, the DB tests still skip quickly
  (CARD-097's cached reachability check stays).
- G-3: No change under `src/`.

## Architecture context

- **FR:** — (test infrastructure)
- **Components:** COMP-009 (test harness)

## Worktree notes

- [Origin] Found 2026-09-30 when the db_required set ran against a real database
  for the first time. Cut on 2026-10-02.
- [Why it matters] Until this is fixed, "DB mode passes" means "DB mode skipped".
  Several follow-up cards (CARD-154, CARD-157) need DB-mode tests they can trust.
