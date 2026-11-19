# CARD-488: Four small test-side gaps closed in one pass: the DB probe, the migration log, the size form and two stale comments

**Status:** review
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/488-test-side-gaps
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-488
**Source:** roadmap rescore 2026-11-18, wave 3 (IDEA-034, IDEA-017, IDEA-083, IDEA-100, each WSJF 3.85, each 0.125 d: bundled because each alone is below `sizing.min_estimate`).
**Idea:** IDEA-034, IDEA-017, IDEA-083, IDEA-100
**Wave:** 82
**Created wave:** 82
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_db_url_driver.py, tests/e2e/test_admin_workflow.py, src/nonogram/admin/static/admin.css, tests/test_books_list_mobile.py
**UI surface:** books list (plan-hints summary focus ring)
**Review score:** 9.6 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-19T19:53Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Four items from old reviews, each still open when re-read on 2026-11-18, none worth a card alone:

1. **IDEA-034 (safety).** The `db_required` reachability hook in tests/conftest.py (`pytest_runtest_setup` -> `_unreachable_reason`) still connects and runs `SELECT 1` against whatever `DATABASE_URL` names **before** the `_test` guard applies. A developer whose shell holds a production URL sends it a probe on every DB test.
2. **IDEA-017.** `migrations/env.py` keeps the plaintext URL out of logs only by configuration (`logger_sqlalchemy = WARNING`, no `echo`); nothing asserts it. tests/test_db_url_driver.py already drives the online branch in a subprocess.
3. **IDEA-083.** tests/e2e/test_admin_workflow.py `test_size_configuration_applied` posts `default_size` straight to the route, so renaming the step-1 form's select leaves it green (mutant M8).
4. **IDEA-100.** The books-list plan-hints `summary` uses the browser's default focus ring, not the `--color-focus` ring; a test comment in tests/test_books_list_mobile.py still says about 176 px (now about 169).

## What to implement

Re-verify each against main first; drop any that is already closed, with one line in the notes.

1. The probe never reaches a database the `_test` guard would refuse: guard first, probe after.
2. One assertion that the subprocess's stderr does not contain the URL (or its password).
3. The size test reads the form (GET) and posts the field names it finds, or asserts them.
4. The summary gets the shared focus rule; the stale comments are corrected.

## Acceptance criteria

* **AC-1**: with `DATABASE_URL` pointing at a non-`_test` database, no connection is opened by the hook (control: the old order, observed by a fake/unreachable host or a connect spy, reds).
* **AC-2** (amended 2026-11-19 after review cycle 1, F-002: the original premise was wrong — psycopg2 masks the password and the probe never builds an engine): the online migration step's output (stdout and stderr, the probe's own `CONFIG:` line excluded) carries neither DATABASE_URL nor its password in either spelling (raw and percent-encoded). Control: env.py emitting the URL — `print`, or a logger record reaching alembic.ini's console handler — reds it. Out of reach by design: engine echo / DEBUG logging, which this probe never builds (`engine_from_config` is faked) and which was measured on a real connection not to carry the password.
* **AC-3**: renaming the step-1 `default_size` select reds the size test (plant it).
* **AC-4**: the plan-hints summary's focus ring is the `--color-focus` ring (checked the way the existing focus-ring tests check it).
* **AC-5**: net test count at most +2 (owner's budget); report it.

## Guardrails

* **G-1**: tests/conftest.py is a gate-wide file: the merge gate will run the full suite. Note the 30-skip unarmed baseline (memory) and report the skip count and reasons with `-rfs`.
* **G-2**: never connect to the production database, even to prove AC-1; use an unreachable or fake host.

## Worktree notes

All four items were re-verified live on the branch base; none was already closed.

* **Item 1 / AC-1 (IDEA-034): fixed (rewritten in fix round 1, F-001).** `pytest_runtest_setup` never probes a URL `_refusal_reason` refuses. A refused DATABASE_URL no longer skips by itself: the gate judges the resolved test database (TEST_DATABASE_URL, or the derived `*_test` name) with `_unusable_reason`, as main does when DATABASE_URL names it, because that is what `db_session` and the other db_required fixtures act on. Only when both are refused does it skip, unprobed, with a message naming DATABASE_URL (F-003). Round 0's claim that the 14 `db_session` tests "failed on its refusal anyway" was false and is withdrawn: the reviewer's control (DATABASE_URL = this worktree's `_test` URL plus `?dbname=<same name>`, TEST_DATABASE_URL = the `_test` URL, `-m db_required` over test_db_e2e_smoke, test_puzzle_edit_routes, test_card_156_db_fixture, test_db_engine_lifecycle) gave 14 skipped on round 0 (reproduced) and gives 14 passed now. Control, `test_db_session_fails_without_connecting` (8 refused URLs, TEST-NET-1 host, the `create_engine`/`psycopg2.connect` spies), two phases: both variables refused must skip with no probe and a message starting `Database refused, not probed: DATABASE_URL names`; only DATABASE_URL refused must call `_unusable_reason` with the allowed test URL and must neither skip nor probe. Reds, 8/8 each: main's conftest (`the db_required gate probed a refused URL: ['sqlalchemy.create_engine']`); round 0's conftest (the message assertion); plant `pytest.skip` in place of `_unusable_reason(resolved)` (`the gate skipped instead of judging …`); plant dropping the refused check before `_unreachable_reason` (`the gate skipped instead of judging …: Database not reachable: sqlalchemy.create_engine called by a refused fixture`). Unarmed, `-m db_required` over tests/: 29 skipped, all `Database not reachable: DATABASE_URL is not set`; armed at this worktree's own `_test` database: 29 passed. The conftest comment now states that the fixtures act on `test_db_url` (F-005).
* **Item 2 / AC-2 (IDEA-017): assertion added; AC-2's premise did not hold.** `test_the_online_branch_names_the_driver_and_keeps_the_password` now asserts that the subprocess output, minus the probe's own `CONFIG:` line, carries neither the raw URL nor the password (either spelling). Plants on a scratch edit, each reverted: `echo=True` in env.py's `engine_from_config` stays GREEN; every alembic.ini logger at DEBUG stays GREEN; env.py logging the URL at WARNING REDS (`the migration step's output carries 'postgresql://panel:s3cr3t-p%40ss@…'`). Why the first two stay green, measured: the probe fakes `engine_from_config`, so nothing connects. Then, on a real connection to the local `nonogram_test` with `echo="debug"`, `echo_pool="debug"` and all loggers at DEBUG, 63 lines of output contained the password 0 times. The pool lines print the psycopg2 DSN with `password=xxx`. So no configuration keeps the password out; the driver masks it. What the assertion does guard against is env.py (or alembic) emitting the URL.
* **Item 3 / AC-3 (IDEA-083): fixed.** `test_size_configuration_applied` GETs `/batch/create`, takes the name of the one `<select>` offering `large`, and posts that. Plant: renaming the template's `name="default_size"` to `puzzle_size` reds it (`assert b'extent=30x30' in …`). The base test under the same plant stays green, so mutant M8 was live. The first draft scoped this to the form by `UPLOAD_ROUTE`, and `test_every_upload_posts_a_field_the_route_reads` caught that, because only `_upload` may read the constant. So the draft now matches on the select instead.
* **Item 4 / AC-4 (IDEA-100): fixed.** `.plan-hints > summary:focus-visible` joins admin.css's shared `--color-focus` rule. New `test_the_summary_takes_the_shared_focus_ring` focuses it after a Shift press, the same keyboard-modality technique test_player_base_css's census uses (no existing test checks an admin `--color-focus` ring), and asserts `solid 2px <resolved --color-focus>`. Control: with the base admin.css it reds with `ring: ['auto', '1px', 'rgb(0, 95, 204)']` vs `rgb(31, 95, 91)`. Comment re-measured in Chromium at 390 px: row 168.8 px (was "about 176"), actions column 148.1 px (its "148 px" still holds). Second stale comment (F-004, fix round 1): `test_two_off_plan_cells_read_plural` named two hints it never asserted; it now asserts `hints_of(disclosure) == ['16-20 × hard: over 2', '26-30 × hard: short 7']`, the strings measured by a failing placeholder run first; no new test.
* **AC-5:** `--collect-only -q -o addopts=` over tests/: base 10704, branch 10705, so net +1.
* **Gate (unarmed, `-rfs`):** test_db_*.py, test_card_156_db_fixture, test_card_349_cold_database, test_shared_fixture_controls, test_guard_integrity, e2e/test_admin_workflow, test_books_list_mobile, test_admin_design_tokens, test_card_109_database_guard, test_admin_binding, test_full_suite_lock, test_impact_set, test_kill_matrix, test_collected_names, test_cli, test_kanban_review_record, test_suite_profile, test_browser_fixture_scope. The first run gave 1 failed (the draft above), 1563 passed, 25 skipped, all `DATABASE_URL is not set`. After the fix, e2e/test_admin_workflow alone gave 19 passed. The full suite was not run here.
* **Fix round 1 gate:** the round-0 files plus test_books_list_plan_stats (23 files, globs expanded), `-rfs`. Unarmed: 1599 passed, 25 skipped, all `Database not reachable: DATABASE_URL is not set`. Armed at this worktree's `_test` database: 1624 passed, 0 skipped. `--collect-only -q -o addopts=` over tests/: 10705 (net +1 vs base 10704). Full suite not run here.

[Review 1/3] Score: 8.0, two gating findings, not certified. F-001 a refused DATABASE_URL skipped every db_required test, including those that run on the suite's own `_test` database (measured 14 passed on main, 14 skipped on the branch), on a false premise; F-002 AC-2's control could not fail as written (the probe never builds an engine; psycopg2 masks the password); F-003 the skip message named TEST_DATABASE_URL; F-004 the second stale comment the title promised was not touched; F-005 a conftest comment repeated F-001's premise. AC-2 amended on main and branch by the orchestrator (`52e859fb`); F-001 (option a: judge the resolved test URL, never probe the refused one), F-003, F-004, F-005 fixed in `bd36accd`.

[Review 2/3] Score: 9.6, nothing gating, certified. F-001..F-005 closed and re-measured: the refused-but-reachable `?dbname=` control 14 passed (14 skipped in cycle 1); unarmed `-m db_required` 29 skipped "DATABASE_URL is not set"; armed at the worktree's own `_test` DB 29 passed; opt-out with a foreign unreachable host 29 skipped in 1.8 s, nothing probed; the AC-1 control reds 8/8 under all four plants. F-006 (info): with DATABASE_URL refused, the gate may create the resolved database, but `_ensure_test_database` re-checks the refusal before any DDL (name ends `_test`, no dbname override, `[a-z0-9_]+`), and main already reached that path via `db_session`. Net +1 (10705).
