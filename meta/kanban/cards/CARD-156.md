# CARD-156: The db_session fixture stops dropping tables other tests are using

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/156-db-session-fixture-isolation
**Worktree:** —
**Source:** surfaced 2026-09-30 while running the db_required set against a real nonogram_test (backlog); fixture re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** tests/conftest.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-10-02T11:56:47Z
**Closed:** 2026-10-02T13:37:39Z
**Actual:** 0.2d
**Merge commit:** c095b22
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

## System contract

_Assembled 2026-10-02 by system_rules.py --card CARD-156 (card_scope: touches; all five are global rules — none is scoped to tests/conftest.py)._

- CON-005 — The uniqueness check must never produce a false positive (check: test PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds 127.0.0.1 only (check: test TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI refuses cross-site / foreign-authority requests (check: test PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive, every source mode and adapter (check: test PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — Aspect guard: refuse >2x ink-bbox ratio difference, exactly 2x accepted (check: test PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Worktree notes

- [Origin] Found 2026-09-30 when the db_required set ran against a real database
  for the first time. Cut on 2026-10-02.
- [Why it matters] Until this is fixed, "DB mode passes" means "DB mode skipped".
  Several follow-up cards (CARD-154, CARD-157) need DB-mode tests they can trust.
- [Env] forge 2026.8.17
- [DB] nonogram_test reachable on Postgres.app: `psql postgresql://omelnikova@localhost:5432/nonogram_test` → alembic_version 013 (the conftest default `postgres:postgres@…/nonogram_test` also authenticates on this machine). Read-only check before any write.
- [AC-1 before] `DATABASE_URL=TEST_DATABASE_URL=postgresql://omelnikova@localhost:5432/nonogram_test pytest -m db_required` on dc26103 (worktree, lock held): **3 failed, 3 passed**. Failing: `tests/test_db_e2e_smoke.py::test_app_instantiates_with_db_services` (UndefinedTable: relation "puzzles" does not exist), `::test_batch_persistence_to_db` (UndefinedTable: relation "batches" does not exist), `::test_create_batch_route_works` (200 page without "Create Batch"). Orchestrator's read of the cause, for the implementer to confirm: the DROPs run inside an uncommitted `engine.begin()` transaction while `Base.metadata.create_all(engine)` checks existence on a separate connection — it still sees the tables, creates nothing, and the outer commit then removes them.
- [System contract] section stale — refreshed from the model: +CON-005, CON-009, CON-010, CON-011, CON-012 / −(none; card had no section)
- [Root cause — confirmed] Direct probe on nonogram_test: inside the fixture's `engine.begin()` after the two DROPs, a second connection still reports `has_table("puzzles") == True`; `Base.metadata.create_all(engine)` (its own pooled connection) therefore creates nothing, and on commit the tables are gone. The next test's DROP IF EXISTS is a no-op and its create_all does build them — so the 6 db_required tests alternated fail/pass (1,3,5 failed). The schema each odd run left behind was create_all's, not alembic's (CASCADE drift).
- [Design] `tests/conftest.py`: session fixture `_test_database_tables` empties `public` (DROP SCHEMA public CASCADE; CREATE SCHEMA public) and runs `alembic upgrade head` once — emptied first because alembic_version can read 013 over missing/drifted tables, which is what the old fixture (still on other branches) leaves behind. Alembic runs as a subprocess because env.py calls `logging.config.fileConfig` (disables existing loggers → breaks later caplog tests) and re-imports models as `src.nonogram`. Per-test isolation: `db_session` TRUNCATEs every public table except alembic_version (RESTART IDENTITY CASCADE, `lock_timeout 10s` so a leaked session errors instead of hanging) at setup. Not rollback: the app opens and commits its own sessions via `session_scope`, which an outer transaction would not cover. No DROP per test.
- [Guard] `_refuse_unless_test_database(url)`: name parsed with `tests/database_guard._database_name` (never echoes the password), must end in `_test`, else `pytest.fail(pytrace=False)` — loud, not a green skip. Runs first in both fixtures; `db_session` reaches the session fixture via `request.getfixturevalue` so the guard and the cached CARD-097 reachability check (G-2) run before the session fixture is even requested.
- [Tests] `tests/test_card_156_db_fixture.py`: `TestDbFixture_RefusesANonTestDatabase` (5 non-test names incl. `test_nonogram`/`nonogram_test_backup`, host 192.0.2.1 TEST-NET-1, spies on sqlalchemy.create_engine / session.create_engine / psycopg2.connect assert zero attempts, password not in message; plus the allowed case) — runs with no DB. `TestDbFixture_SchemaIsBuiltOncePerSession` (db_required): SQL captured during db_session setup has TRUNCATE and no DROP/CREATE/ALTER; next test starts empty; alembic_version == heads read from ScriptDirectory.
- [AC-1] The 3 formerly failing tests now pass: `test_db_e2e_smoke.py::test_app_instantiates_with_db_services`, `::test_batch_persistence_to_db`, `::test_create_batch_route_works`. The third had a second, independent cause: the page heading is "New batch" since f773015 (Pressroom), assertion was stale.
- [AC-1 after] `DATABASE_URL=TEST_DATABASE_URL=postgresql://omelnikova@localhost:5432/nonogram_test pytest -m db_required -p no:cacheprovider` (lock held): `8 passed, 5558 deselected, 7 warnings in 2.76s` (6 smoke + 2 AC-3). Also green with the conftest default postgres:postgres URL.
- [G-2] DATABASE_URL unset: `8 skipped, 5558 deselected, 7 warnings in 1.11s`; unreachable `127.0.0.1:1/nonogram_test`: `8 skipped … in 1.21s`.
- SCOPE+ tests/test_db_e2e_smoke.py — one-line assertion update in `test_create_batch_route_works` (stale "Create Batch" copy → `<h1>New batch</h1>`); not additive, but AC-1 cannot pass otherwise.
- [Commit] 542b0ac on card/156-db-session-fixture-isolation.
- [Scope] tests/conftest.py, tests/test_card_156_db_fixture.py, tests/test_db_e2e_smoke.py
- [Build gate] impact underivable (test_scope: full; fix_scope includes conftest.py) — full suite
- [Build gate] PASSED (full, 311s; waited 226s for the full-suite lock): 5555 passed, 9 skipped, 2 failed — both are the known baseline failures on main dc26103 (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders); no other failure. Run with DATABASE_URL/TEST_DATABASE_URL unset; nonogram.__file__ verified to resolve into the worktree.
- [Scope gate] ⚠ grown: +0 components · 1 file outside Touches (tests/test_db_e2e_smoke.py — existing file, implementer's SCOPE+; 1/3 = 33% of actual files). New tests/test_card_156_db_fixture.py counted as a new file near scope. Guardrail hits (G-3 src/**): none. Poached siblings: none.
- [Review 1/3] Score: 7.5 — crit: 0, imp: 2 (F-001 AC-3 test blind to a function-scoped schema fixture; F-002 AC-2 spy swallowed by _unreachable_reason → SKIPPED not FAILED); minor F-003 (DROP SCHEMA without lock_timeout, engine leak on failure), F-004 (guard reads only URL path, ?dbname= bypass); out-of-scope F-005 (shared nonogram_test across concurrent runs). Adversarial verification of F-001/F-002 pending. Step 8h: 5 rules checked, 5 ⚠ unchecked no_eligible_fact (CON-005/009/010/011/012) — coverage complete. Mutation check deferred — cycle not passing.
- [Review sync] 1 report(s) → meta/review/ (20261002T122954Z-CARD-156-cycle1.yml)
- [Adversarial] F-001 CONFIRMED — with _test_database_tables function-scoped, pytest resolves it before per_test_sql starts recording and db_session's getfixturevalue returns the cached instance; both AC-3 tests stay green (static trace of fixture order).
- [Adversarial] F-002 CONFIRMED — mutant (guard moved below the reachability check) run on a scratch copy: 1 passed, 5 skipped; the spy's AssertionError is swallowed by _unreachable_reason's except Exception and db_session skips, so the forbidden connection goes unreported.
- [Review 1/3] after verification: crit 0, imp 2 confirmed; score 7.5 < 8 → fix loop
- [Fix 1] Review cycle 1 (7.5). F-001: AC-3 now also checks the session fixture *across* tests — test 1 records the yielded engine and `'batches'::regclass::oid`, test 2 asserts the same engine and the same OID (a per-test DROP SCHEMA + alembic yields a new engine and a new table OID); the pair must run together, test 2 fails alone. F-002: the AC-2 spies' AssertionError was swallowed by `_unreachable_reason` into a green skip; the test now converts a skip into a failure, asserts zero connection attempts in a `finally`, and empties `_DATABASE_VERDICTS` so a cached verdict cannot bypass the spied probe. F-004: `_refuse_unless_test_database` now parses with SQLAlchemy `make_url` (no connection) and also refuses `dbname`/`database` query overrides (case-insensitive) and unparseable URLs, never echoing the password — supersedes the [Guard] note's "parsed with `_database_name`". F-003: session DROP SCHEMA runs under `SET LOCAL lock_timeout = '10s'`; the engine is disposed in `try/finally` on every exit. F-005 (concurrent runs wipe each other's schema) left for a follow-up card.
- [Fix 1] declarations: 0 updated (no failure matrix on this card), 4 doc/card-note (F-001 class docstring; F-002 class docstring; F-003 _test_database_tables docstring; F-004 _refuse_unless_test_database docstring), 0 none. Review YAML cycle1: F-001..F-004 status: fixed (written by the orchestrator — the fix agent's write was refused by the permission check), synced to main.
- [Fix 1] pre-gate PASSED: tests/test_card_156_db_fixture.py (TestDbFixture_RefusesANonTestDatabase + TestDbFixture_SchemaIsBuiltOncePerSession as a pair) — with nonogram_test, lock held: 12 passed in 1.67s; with no DB env: 10 passed, 2 skipped in 0.13s.
- [Build gate] PASSED (full, 311s): 5559 passed, 9 skipped, 2 failed — only the 2 known baseline failures (test_size_configuration_applied, test_batch_creation_form_renders).
- [Scope] cycle 2 scope gate: unchanged (GROWN, already noted; fix touched only tests/conftest.py and tests/test_card_156_db_fixture.py; no guardrail hits). Review 2 runs FULL (cycle 1 discovered gating findings → not confirmation-eligible).
- [Review 2/3] Score: 9.0 — crit: 0, imp: 0. Cycle-1 F-001..F-004 ✓ resolved. New minor: F-006 (second AC-3 test fails red when run alone — introduced by the F-001 fix; non-gating), F-007 (DROP SCHEMA public needs schema ownership and resets owner/grants). F-005 carried out-of-scope (backlog). Step 8h: 5 rules checked, 5 ✓ holds — coverage complete.
- [Review 2/3] Score: 9.0 ✓ threshold reached + no critical/important
- [Mutation] review cycle 2, card's own tests + db_required under the lock: 6/6 testable mutants caught (M1 endswith→contains: 2 failed; M2 guard below reachability: 8 failed; M3 override check off: 3 failed; M4 TRUNCATE→DROP+create_all: 2 failed; M5 session fixture function-scoped: 1 failed; M7 guard removed: 8 failed); M6 (lock_timeout removed) not testable without a competing lock — equivalent under these tests. File restored from backup, cmp-verified.
- [Review sync] 2 report(s) → meta/review/ (cycle1, 20261002T132434Z-CARD-156-cycle2.yml)
- [8h spot-check] 3/3 sampled holds reproduced (CON-005: tests/property/test_solver_uniqueness.py 2 passed; CON-009: TestWebServer_BindsLoopbackOnlyByDefault 6 passed; CON-010: tests/test_web_server.py 154 passed, property arms 4 passed) — no diff path reaches solver or web server.
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — db_required against nonogram_test (lock held): `8 passed, 5562 deselected, 7 warnings in 3.55s`, incl. test_app_instantiates_with_db_services, test_batch_persistence_to_db, test_create_batch_route_works
  AC-2 ✓ demonstrated — TestDbFixture_RefusesANonTestDatabase: 10 PASSED (8 refused URLs incl. ?dbname=/?database= overrides, spies assert zero connection attempts in finally; unparseable URL refused without echo; nonogram_test allowed)
  AC-3 ✓ demonstrated — TestDbFixture_SchemaIsBuiltOncePerSession (as a class): 2 PASSED (per-test SQL TRUNCATE only, no DROP/CREATE/ALTER; same engine + same batches OID across tests; alembic_version == head)
  G-1 ✓ demonstrated — refusal tests above + read of conftest: guard first in both fixtures, all destructive work and alembic use test_db_url only. Caveat (pre-existing, unchanged): the CARD-097 db_required hook's read-only SELECT 1 probe goes to whatever DATABASE_URL names
  G-2 ✓ demonstrated — no DB env: 10 passed, 8 skipped in 0.12s; refused port: 8 skipped in 0.19s; blackhole 192.0.2.1: 8 skipped after one 10s deadline (cache holds); test_db_connect_timeout / test_card_109_database_guard / test_db_url_driver untouched and green (73 passed with the card file)
  G-3 ✓ demonstrated — changed files (committed + uncommitted, meta/ excluded): tests/conftest.py, tests/test_card_156_db_fixture.py, tests/test_db_e2e_smoke.py; none under src/
- [Docs] tests/README.md updated by the orchestrator (forge:readme step run inline, doc-only): db_session added to the fixtures list with its once-per-session schema / per-test TRUNCATE / _test-refusal semantics; troubleshooting entry for the refusal, incl. the public-schema ownership requirement (answers minor F-007 by documentation). tests/README.md is outside Touches — docs-step addition, not implementation scope.
- [Commit] success commit e0708c0 on card/156-db-session-fixture-isolation (explicit pathspecs: tests/conftest.py, tests/test_card_156_db_fixture.py, tests/README.md); implementation commit 542b0ac carries tests/test_db_e2e_smoke.py. Nothing under meta/ committed. Branch base dc26103 — not rebased (main is at cc4c420; the dispatcher rebases at done).
- [Left open] Minor F-006 (second AC-3 test fails red when run alone — pair dependency from the F-001 fix), F-007 (DROP SCHEMA public needs schema ownership; documented, not changed). Out-of-scope F-005 (shared nonogram_test across concurrent runs) → backlog via the dispatcher.
- [Merged] 2026-10-02 — c095b22 into main (--no-ff). Rebased onto cc4c420 cleanly (main had not touched conftest.py, tests/README.md or test_db_e2e_smoke.py since dc26103) → tip 47d011a. Merge gate: full suite on the rebased tree under the lock (342s); only the 2 baseline failures. Deferral scan: 0 hits. No trace write-back: no FR on the card. F-005/F-006/F-007 captured to backlog. Dependent CARD-157 is `ready` (no worktree) — it will branch from this merge.
