# CARD-522: The deployed panel refuses to start without a database

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/522-refuse-memory-mode-deployed
**Worktree:** —
**Source:** roadmap wave 12, cut 2026-11-22 on the owner's "let's take your suggestions for first 4 ideas". IDEA-226 (CARD-515 review 1 F-003).
**Idea:** IDEA-226
**Wave:** 91
**Created wave:** 91
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py
**UI surface:** — (start-up only)
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-22T13:38Z
**Closed:** 2026-11-22T14:36Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** 7110c1bcaf14a39f3aa74f9c751db3201f2cab35
**Blocked by:** —

## Why this card exists

After CARD-515 a blank or whitespace-only DATABASE_URL counts as unset, and the admin panel then starts quietly in in-memory mode: it logs "DATABASE_URL not set", and everything saved is lost on restart. Locally that is the intended fallback. On the deployed panel it would silently lose work. Owner's ruling 2026-11-22: refuse to start on the deployed server (where REMOTE_HOST is set); keep the in-memory fallback locally.

## What to implement

Re-verify on main first: how `create_app` chooses in-memory mode, how the deployed server is recognised (REMOTE_HOST, `_configured_hostname`; read how both are set and used), and what happens today with REMOTE_HOST set and DATABASE_URL unset or blank. Then make `create_app` refuse to start in that case, with one clear message naming what is missing (never echoing any URL or secret). Locally (REMOTE_HOST unset) nothing changes.

## Acceptance criteria

* **AC-1**: REMOTE_HOST set and DATABASE_URL unset, empty or whitespace-only: the app refuses to start, with a message that names DATABASE_URL and says the deployed panel needs a database (control: today's code starts in memory).
* **AC-2**: REMOTE_HOST unset and DATABASE_URL unset: the in-memory fallback still starts, unchanged.
* **AC-3**: REMOTE_HOST set and a valid DATABASE_URL: starts as before (no connection is needed to show this; stop at the mode decision).
* **AC-4**: net test count at most +1, preferring extensions of existing create_app tests. Report it.

## Guardrails

* **G-1**: never connect to the production database, and do not deploy; Render runs its own dashboard-configured service and this change reaches it only on the owner's next deploy.
* **G-2**: the refusal message carries no URL, host or credential.

## Worktree notes

### 2026-11-22: implementation (agent)

**Premise, re-verified on the branch base before any change** (recorded run, not a reading): with `ADMIN_ALLOWED_HOST` set (the code's `REMOTE_HOST_VAR`; there is no variable literally named REMOTE_HOST), a valid password and SECRET_KEY, `create_app()` started for DATABASE_URL unset, `""` and `"   "`, each logging "Running in in-memory mode (DATABASE_URL not set)" with `puzzle_review_service._session_factory is None`.

**Where a refusal surfaces.** `start.sh` runs gunicorn on `nonogram.admin.app:create_app()`, and the existing boot refusals are `AdminConfigurationError` raised from `create_app`. So this one is too. Measured locally (127.0.0.1, no database, nothing deployed): gunicorn exits 3, "Worker failed to boot", with the message in the log.

**What changed**
- `create_app` (src/nonogram/admin/app.py): the trimmed DATABASE_URL check (CARD-515's rule, still written out, still no SQLAlchemy import in an in-memory install) is read once as `database_url_set`, before the remote-mode checks, and reused for the mode decision. Inside the `if remote_host:` block, after the SECRET_KEY check, a missing/blank DATABASE_URL raises `AdminConfigurationError` naming DATABASE_URL and `ADMIN_ALLOWED_HOST` and saying the deployed panel needs a database. The message holds no host, URL or credential (G-2). Local mode is untouched.
- New keyword-only parameter `allow_in_memory_when_deployed=False`, for tests only. The suite builds an in-memory deployed panel at 9 call sites (counted by `ast`) to test the door, not storage; they pass it. `start.sh` calls `create_app()` bare, so production cannot reach the bypass through the environment.
- Tests, by name: new `TestAdminAuth_RefusesToBootMisconfigured::test_no_database_is_fatal` (AC-1: loops unset/empty/whitespace in one test, so +1 collected). Extended `test_a_correct_configuration_boots` (AC-3: black-holed TEST-NET-3 DATABASE_URL, asserts the DB-backed store was built, no connection opened). Extended `test_local_mode_boots_with_neither` (AC-2: asserts the in-memory store). These fixtures/tests now pass `allow_in_memory_when_deployed=True`: test_admin_auth `deployed_app` and `TestAdminAuth_RefusesToBootWithAGuessablePassword::test_the_boundary_itself_boots`; test_admin_binding `TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit.deployed_client`; test_admin_regrade_hidden_when_deployed `deployed_client`; test_admin_serving `test_every_shape_an_operator_might_paste_works`, `test_a_host_mismatch_is_logged_with_both_values`, `test_the_response_itself_still_gives_nothing_away`, `test_the_boot_log_says_which_door_is_open` (both calls).
- ADMIN_SETUP.md: the "refuses to start" paragraph now lists DATABASE_URL.

**Controls** (src/nonogram/admin/app.py mutated, then restored from a copy; `diff -q` confirmed identical):
- A: refusal condition replaced by `if False` -> `test_no_database_is_fatal` red: `Failed: DID NOT RAISE AdminConfigurationError`.
- B: `{remote_host!r}` added to the message -> red: `assert 'nonogram-admin.onrender.com' not in 'ADMIN_ALLOW...run locally.'`.
- F: "needs a database" reworded -> red: `assert 'needs a database' in '...'`.
- G: both DATABASE_URL mentions removed from the message -> red: `assert 'DATABASE_URL' in '...'`.
- H: `database_url_set` made `os.getenv('DATABASE_URL') is not None` (blank counts as set) -> red: `DID NOT RAISE` (unset still refuses, so a blank value is what escaped).
- C: refusal made unconditional on the URL -> `test_a_correct_configuration_boots` red with the AdminConfigurationError.
- D: mode decision `if database_url_set` -> `if False` -> `test_a_correct_configuration_boots` red: `a deployed panel with DATABASE_URL set must be DB-backed / assert None is not None`.
- E: the same refusal placed in local mode -> `test_local_mode_boots_with_neither` red: `AdminConfigurationError: DATABASE_URL needed`.
- The `"deployed admin panel"` text assert has no separate control. A and C cover the remaining asserts as a group.

**Gate** (no full suite):
- Unarmed: tests/test_admin_auth.py, test_admin_serving.py, test_admin_binding.py, test_admin_regrade_hidden_when_deployed.py, test_admin_import_consistency.py, test_batch_requested_tier.py, test_puzzle_edit_routes.py, test_puzzle_editor_ui.py, plus neighbours test_db_url_driver.py, test_admin_filter_side_range_and_name.py, test_kill_matrix.py: 584 passed, 0 failed, 13 skipped (all "Database not reachable: DATABASE_URL is not set").
- Armed against this worktree's own `nonogram_pythonproject4_card_522_14f2af8fd8ab_test` on localhost: the five edited test files gave 205 passed, 0 skipped, 0 failed.
- Net collected: 10693 -> 10694 (+1, AC-4).

**Not covered (outside this card).** With DATABASE_URL set but `from nonogram.db import session_scope` failing (for example, SQLAlchemy missing), `create_app` still catches the exception and falls back to in-memory mode silently, including on the deployed panel. The card scoped the refusal to unset/blank. This path is unchanged, and no test covers it.

[Review 1/3] Score: 8.5, one gating finding, not certified. AC-1 to AC-4 met; G-1 and G-2 hold; no existing test weakened; controls H and I red again (four edited files 186 passed, 9 skipped "DATABASE_URL is not set"). F-001 (Important): with DATABASE_URL set but `from nonogram.db import session_scope` failing, `create_app`'s `except Exception: session_scope = None` still boots the deployed panel in memory (probe with `sys.modules['nonogram.db'] = None`: `booted; session_factory: None`), logging "DATABASE_URL not set"; the new ADMIN_SETUP.md sentence "the deployed panel never falls back to the in-memory store" is therefore false. Unlikely on today's build (SQLAlchemy is a requirement), but it is the harm the card exists to stop. F-002 (low): `allow_in_memory_when_deployed` is acceptable; start.sh, the Procfile/railway.json `flask run` path and `main()` all call `create_app()` bare; its docstring names only start.sh. F-003 (low): the "deployed admin panel" message assert has no control; the net-count figure names no command (re-derived +1 over the four edited files). F-004 (info): message claims true; local mode unchanged.

### 2026-11-22: fix round 1 (agent), review 1 F-001..F-003

- **F-001 fixed.** In `create_app`, the `except Exception` after `from nonogram.db import session_scope` now raises `AdminConfigurationError ... from None` when the deployed switch is set and `allow_in_memory_when_deployed` is off. The message says DATABASE_URL is set but the database code could not be loaded, and contains no exception text, URL, host or credential. Locally the in-memory fallback stays. The mode log line now reads "Running in in-memory mode (DATABASE_URL is set but the database code could not be loaded)" on that path. The not-set case still reads "(DATABASE_URL not set)". So the "Not covered" paragraph of the implementation note above is closed. ADMIN_SETUP.md's sentence now lists the load-failure case. Its "never falls back" claim holds for every recorded start path; the only bypass is the test-only keyword.
- **Test.** I extended `TestAdminAuth_RefusesToBootMisconfigured::test_no_database_is_fatal`; no new test function.
  - A fourth case sets DATABASE_URL to the black-holed URL with `sys.modules["nonogram.db"] = None`, the reviewer's probe. It asserts the refusal, "could not be loaded" in the message, "not set" absent, no "203.0.113.1"/"nonogram.db"/"://" in it, and `__suppress_context__`.
  - It then unsets the switch and asserts the local boot is in memory, with a truthful log line.
- **F-002 fixed.** The `create_app` docstring now names every recorded start path: start.sh's gunicorn, the Procfile and railway.json `flask run` (Flask calls the factory bare), and `main()`. All of them call `create_app()` with no arguments.
- **F-003 fixed:** control J below.
- **Controls** (app.py mutated, restored from a copy, `diff -q` identical), all on `test_no_database_is_fatal`:
  - I1, today's except branch restored (no raise, old reason): `Failed: DID NOT RAISE AdminConfigurationError`.
  - I2, `from None` dropped: `AssertionError: raise ... from None`.
  - I3, the local log line hard-coded back to "(DATABASE_URL not set)": `assert 'database code could not be loaded' in 'INFO ... Running in in-memory mode (DATABASE_URL not set)'`.
  - J, "deployed admin panel" reworded to "remote panel" in the not-set message: `assert 'deployed admin panel' in 'ADMIN_ALLOWED_HOST is set, which makes this the remote panel, ...'`.
- **Gate.**
  - Unarmed, same eleven files as the implementation note: 584 passed, 0 failed, 13 skipped (all "Database not reachable: DATABASE_URL is not set").
  - Armed against `nonogram_pythonproject4_card_522_14f2af8fd8ab_test` on localhost, the four changed test files (test_admin_auth, test_admin_serving, test_admin_binding, test_admin_regrade_hidden_when_deployed): 195 passed, 0 skipped, 0 failed.
- **Net count**, re-derived with `--collect-only -q -o addopts= tests/ | tail -1`: merge-base b607321a (extracted by `git archive` to a scratch directory) 10693, this branch 10694, so +1.

[Review 2/3] Score: 9.5, nothing gating, certified. With ADMIN_ALLOWED_HOST set, both routes into memory (DATABASE_URL unset/blank; set but `nonogram.db` fails to import) now refuse unless the test-only keyword is passed, and every recorded start path calls `create_app()` bare; no code outside tests/ passes the keyword. Messages carry only the variable name; the import-failure refusal is raised `from None`. Local log lines are truthful in both cases. `sys.modules` is patched with `monkeypatch.setitem` and restored (test_admin_auth.py 81 passed; followed by neighbours 68 passed). Controls I1, I2, I3, J red again, plus the reviewer's K (exception text in the message) and L (refusing locally). Unarmed 186 passed, 9 skipped "DATABASE_URL is not set"; armed 195 passed; net +1. F-001 (low): the import-failure refusal names no cause, and the same `except` also catches an import-time bug inside `nonogram/db`; the exception's class name would help without leaking anything.

**Merge gate (orchestrator).** `make test-gate BASE=main` on `82ba2d1f` (main had not moved) answered FULL less 2 deferred marked tests: 10650 passed / 30 skipped (unarmed) / 13 deselected / 1 xfailed / 0 failed in 27 min 52 s, then the marked run 11 passed. 2 marked tests are owed at the wave close.
