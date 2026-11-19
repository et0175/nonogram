# CARD-488: Four small test-side gaps closed in one pass: the DB probe, the migration log, the size form and two stale comments

**Status:** in_progress
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
**Review score:** —
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

—
