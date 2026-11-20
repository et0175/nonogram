# CARD-508: Test-database hygiene: concurrent runs, the schema-once test run alone, engine globals restored, the connect-timeout flake

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/508-test-db-hygiene
**Worktree:** ../PythonProject4-card-508
**Source:** roadmap wave 7 (cut 2026-11-20 on the owner's "go with option 2, start wave 7"). IDEA-031 (WSJF 3.33), IDEA-032, IDEA-140, IDEA-174 (1.92 each): the faults most likely to red a merge gate for no code reason. Two are marked unverified/partly in the backlog; expect some to be closed already.
**Idea:** IDEA-031, IDEA-032, IDEA-140, IDEA-174
**Wave:** 86
**Created wave:** 86
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_card_156_db_fixture.py, tests/test_db_connect_timeout.py, tests/test_db_*.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T21:24Z
**Blocked by:** —

## Why this card exists

1. **IDEA-031 (CARD-156 F-005).** Two test runs at once share one test database, and the per-session `DROP SCHEMA public` wipes the other run's schema mid-flight. Triage 2026-11-18: "partly"; the per-worktree `*_test` database resolution (CARD-378 family) separates runs in different worktrees; the remaining case, two runs in the SAME worktree (or two worktrees resolving the same name), was considered and skipped as CARD-378. Only the full-suite lock covers it.
2. **IDEA-032 (CARD-156 F-006).** The second `TestDbFixture_SchemaIsBuiltOncePerSession` test fails by design when run alone (`-k`, node id, `--lf`), because it compares against state the first records. Unverified.
3. **IDEA-140 (CARD-178 F-001/F-003).** Tests that reset `db.session`'s engine do not restore the module globals (`engine`, `SessionLocal`, `_engine_url`); CARD-252/254 added a guard. Not established whether the guard makes an autouse snapshot fixture unnecessary.
4. **IDEA-174.** tests/test_db_connect_timeout.py reported `1 error` once under host contention (2026-10-18), never reproduced since.

## What to implement

Re-verify each against main first, armed at this worktree's own `*_test` database where the item needs a database; drop any already closed with one line and its evidence.

1. IDEA-031: if two armed runs in one worktree can still wipe each other, make the session schema build safe against it (a session-level `pg_advisory_lock` around the build/drop, or refusing a second concurrent run with a clear message). Prove it with two concurrent armed runs of a small db_required selection. If the remaining case is not reachable, record why.
2. IDEA-032: make the second test self-contained (run it alone by node id: green), without weakening what the pair asserts together.
3. IDEA-140: decide by measurement whether the existing guard already restores or detects the globals (plant a test that resets the engine without restoring, see whether anything reds). Fix only if nothing catches it.
4. IDEA-174: try to reproduce under load (e.g. the DB file set in parallel with a CPU hog); if it does not reproduce in a stated number of runs, record that and drop it. If it does, widen the timing margin with its reason.

## Acceptance criteria

* **AC-1**: each item fixed with a control that reds, or dropped with its measured evidence.
* **AC-2**: unarmed, the full db_required set still skips with "DATABASE_URL is not set" (29); armed at this worktree's `_test` database, it passes with 0 skips. Report both with `-rfs`.
* **AC-3**: net test count at most +1; report it.

## Guardrails

* **G-1**: tests/conftest.py is a gate-wide file: the merge gate runs the full suite. Report skip counts and reasons with `-rfs`.
* **G-2**: never connect to the production database; armed runs use only this worktree's own `*_test` database on localhost. Never DROP anything that does not end in `_test`.

## Worktree notes
- [Built] 2026-11-21. Armed runs used only this worktree's resolved database `nonogram_pythonproject4_card_508_184f05c24fec_test` on localhost (read from `tests.db_name.resolve_test_database_url`). Nothing was dropped by hand. Scratch scripts and logs are in /private/tmp/claude-501/card508/.
- IDEA-031 (OPEN on base, FIXED). Reproduced in this worktree with two concurrent armed runs: A was a planted probe (`db_session`, commit one `Batch`, sleep 12 s, read back; temporary file, never committed), and B, started 5 s later, was `TestDbFixture_SchemaIsBuiltOncePerSession`. On base A failed `AssertionError: saw []` and B passed. Two looser tries did not show it (two 57-test runs of test_db_isolation.py + test_db_e2e_smoke.py 8 s apart, and the same with six short B runs during A: all green), because the wipe window is short. Fix: conftest `_session_lock`, used by `_test_database_tables`. It holds a session-level `pg_try_advisory_lock` for the whole session on one connection. A second process on the same database fails the fixture: "Refusing to set up the test database '<name>': another pytest run is using it (database backend pid [...])". It refuses instead of waiting. A child pytest that a lock holder starts on the same database inherits `NONOGRAM_TEST_DB_SESSION_LOCK` and proceeds; test_card_349's re-raise control runs one. That exception is safe only while the parent waits for the child, and this is a convention that nothing enforces. After the fix the same pair gave A `1 passed`, and B 2 errors carrying the refusal. B's terminal note named it too. The existing `TestDbIsolation_TwoTreesDoNotCorruptEachOther::test_two_trees_pass_concurrently_and_the_same_pair_reds_when_they_share` is the committed control. Its shared arm now asserts that tree B is refused, that tree A shows no `saw [`, and that A fails with "peer never reached". Before, it accepted a destroyed row. Cost: the shared arm now waits out the probe's 45 s rendezvous deadline in tree A.
- IDEA-032 (OPEN on base, FIXED). On base, running the second test alone by node id failed with `AssertionError: run this class as a whole ... assert 0 == 1`. Now `test_the_next_test_starts_empty_on_the_migrated_schema` checks `request.session.items` to see whether the first test ran earlier in the session. If it did, the record is required and compared as before. If not, the test runs only its own checks. Alone by node id: 1 passed. With `-k next_test`: 1 passed, 12 deselected. Run as a pair: 2 passed.
- IDEA-140 (CLOSED, dropped). A planted file (temporary) hand-set `engine`/`SessionLocal`/`_engine_url` to None without restoring. `test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam::test_no_test_file_outside_the_exemption_sets_those_globals` went red: "the per-file count ... has changed", with `('test_zz_card508_plant140.py', 'engine'), 1` among the found sites. A one-line `setattr(app_session, "engine", None)` plant also went red there. The two exempt files (test_db_connect_timeout.py and test_db_url_driver.py) set the globals only through `monkeypatch.setattr`, which restores them. No autouse snapshot fixture was added. The guard's own docstring on `reset_engine` lists the spellings it cannot see.
- IDEA-174 (REPRODUCED, margins widened). Load: 22 `yes` busy loops on an 11-core host, plus the host's other work; the load average reached about 350. Ten sequential runs of tests/test_db_connect_timeout.py (unarmed): runs 1, 2, 5, 6, 7 and 9 passed; 3, 4, 8 and 10 failed. The failures were `subprocess.TimeoutExpired ... timed out after 60 seconds` for the two hang-guard child-pytest tests (run 3 twice, run 4 once), and `took 17.4s / 29.0s / 23.2s — that is a hang` against `_ALLOWED_SECONDS = 15` (runs 4, 8, 10). That is failures, not the recorded "1 error"; that shape was not seen. Caveat: I moved the child timeout to 240 s (`_CHILD_SECONDS`) while the series was still running. Runs 5-10 took it; the "60 seconds" text in runs 3-4 shows the old value. `_ALLOWED_SECONDS` 15 -> 60 then followed: twice the worst observed time, and a connect with no deadline is unbounded, so it still fails. Three more runs under the same load with both changes (11-13): all 5 passed. Both reasons are on the constants.
- Controls (mutant applied, node run, file restored from a saved copy, `git diff --stat` unchanged after each). C1: `_session_lock` replaced by `nullcontext` -> the AC-6 test went red at `assert "another pytest run is using it" in shared_output[1]` (tree b `1 passed`). With that assert also removed, it went red at `assert "saw [" not in shared_output[0]`, with tree A output `AssertionError: a saw ['b']`. C2: the child-inheritance check made `if False:` -> `test_card_349_cold_database.py::TestColdDatabase_TheTwoDatabaseGatesStayAttributable::test_a_swallowed_stop_still_errors_every_test_that_asks_for_the_database` went red (`assert 1 == 0`, the child run `1 passed, 1 warning, 1 error`). C3 (IDEA-032): `if first_ran:` -> `if True:` -> alone red: "the previous test ran in this session but recorded nothing". C4: `_test_database_tables` made function-scoped -> pair red: "the session fixture built a new engine for this test". C5: the first test stops recording -> pair red: "the previous test ran in this session but recorded nothing". C6 (IDEA-174): the test's deadline set to 75 s -> `took 75.1s — that is a hang`.
- AC-2: unarmed, `-m db_required tests/ -rfs`: 29 skipped, all "Database not reachable: DATABASE_URL is not set" (10660 deselected). Armed at this worktree's `_test` database: 29 passed, 0 skipped, 0 failed.
- AC-3: collected count 10689 before and 10689 after (net 0).
- Gate (touched files and their neighbours: test_card_156_db_fixture.py, test_db_isolation.py, test_db_connect_timeout.py, test_card_349_cold_database.py, test_db_engine_lifecycle.py, test_db_e2e_smoke.py, test_db_url_driver.py, test_card_109_database_guard.py). Unarmed `-rfs`: 182 passed, 16 skipped (all "Database not reachable: DATABASE_URL is not set"), 0 failed. Armed `-rEfs`: 198 passed, 0 skipped, 0 failed, 0 errors. tests/test_kanban_review_record.py: 71 passed.
