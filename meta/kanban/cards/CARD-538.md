# CARD-538: The CARD-150 admin-local script-test minors, verified first and fixed only where still live

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/538-script-test-minors
**Worktree:** ../PythonProject4-card-538
**Source:** roadmap wave 17, cut 2026-11-24 on the owner's "pick the next no-decision wave from the backlog". IDEA-018.
**Idea:** IDEA-018
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_admin_local_cost.py, tests/helpers/admin_script_stubs.py, tests/test_start_admin_local.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T08:21Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-150's review left four minors (F-003/F-004/F-005/F-007): a "14 of 18" figure that is an artifact of `--check-only` not existing on the old script; the README tests' `returncode != 0` precondition is met by any failure; the two Docker branches match on database name only, dropping host, port and credentials, with no runtime coverage; and nothing asserts G-3's launch target although the stub logs it. Re-checked on main at the cut: the script tests were restructured since (CARD-236, CARD-492: `tests/helpers/admin_script_stubs.py`), and `tests/test_admin_local_cost.py` now asserts `[c["dbname"] for c in connections(run)] == [url]` beside several `run.returncode != 0` asserts. So some items may be moot.

## What to implement

1. Verify first. For each of the four, find where the claim now lives (grep the three files named in Touches) and record live or moot. For F-004 and F-005, run a mutant: make the script fail for an unrelated reason, or connect to the right database name on the wrong host, and see whether a test notices.
2. Fix only the live ones, by tightening an existing assert (for example matching the failure's message, or comparing the full connection target, not the database name).
3. F-003 is a figure in prose. If it still appears, correct it to what a run measures today, or delete it.

## Acceptance criteria

- AC-1: each item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a test), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and its fix has one control that fails when the fix is reverted.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes
- [Method] The findings are read from CARD-150's review YAML (main checkout, `meta/review/20261001T155452Z-CARD-150-cycle1.yml`), not from this card's paraphrase. Every mutant is a one-substitution copy of the pristine `scripts/start_admin_local.sh` (sha1 `71b3ddf7…`; anchor count asserted == 1), copied over the script for one run and restored by copy, with the sha1 re-checked after each run. The script and `src/` are unchanged in this diff. The mutant runs drive `tests/test_start_admin_local.py` plus `tests/test_admin_local_cost.py` (59 tests). Those are the two files that run `start_admin_local.sh`, found through `run_script`'s import in the cost file. `tests/test_setup_admin_local.py` reads the script's text but never runs it.
- [F-003, moot] The "14 of 18" figure appears in the repo only in CARD-150's own `[Correction to the orchestrator's own reporting]` note, which already states its caveat (13 of the 14 failed on `Unknown option: --check-only`). That is the review's second suggested resolution. It is a dated record of an 18-test suite, so I left it as written. Today's figure, measured by running the pre-CARD-150 script (`git show 3750fd8:scripts/start_admin_local.sh`) against today's `tests/test_start_admin_local.py`: **31 failed, 6 passed**, and `Unknown option: --check-only` appears 63 times in the output. It is still mostly an artefact of the missing flag. No prose was changed.
- [F-004, live → fixed] Mutant: delete the `--check-only)` case arm, so the script fails for an unrelated reason. Against the unmodified tests the result was 36 failed and 23 passed. `test_it_says_a_missing_database_stops_the_script` and `test_it_says_a_failed_migration_stops_the_script` were among the passes, because the unrelated failure met their `returncode != 0` precondition. Fix: each test now also asserts the refusal for its own reason on the script's stdout: `"Database 'nonogram_poc' is not reachable"` and `"Migrations failed"`. Control: the fixed tests under the same mutant give 2 failed, with `assert "Database 'nonogram_poc' is not reachable" in 'Unknown option: --check-only\nUse --help for usage information\n'` and `assert 'Migrations failed' in 'Unknown option: --check-only…'`.
- [F-005, Homebrew branch moot; Docker branches live, not fixed: needs a decision] The local-branch mutant (`elif psql -U postgres -d "$DB_NAME"`: right database name, but the URL's host, port and password dropped) is killed: 8 failed. They include `TestStartAdminLocal_StillChecksTheTargetDatabase::test_the_check_carries_the_urls_host_port_and_credentials` and the URL-shape corpus (CARD-151's full `connections()` comparison). The Docker-branch mutant (`docker exec nonogram-postgres psql -U nobody`) survives: 59 passed. `DOCKER_STUB` always exits 1, so neither Docker branch ever runs in a test. A probe with a docker stub that succeeds (`/private/tmp/claude-501/card538/probe_f005_docker.py`, run outside the repo) used `DATABASE_URL=postgresql://someone:secret@db.example:6543/nonogram_dev` with `nonogram_dev` missing on that server. It printed `✓ PostgreSQL is running, database 'nonogram_dev' reachable (Docker)` and exited 0, and no psql read the URL. The review allowed documenting the limitation as a resolution, and `scripts/README.md` Prerequisites now documents it ("the two Docker ways … check only that a database of that **name** exists there"). Tightening a test cannot make those branches check the host, because that needs a script change. Per the brief, I did not change the script and am reporting it.
- [F-007, live → fixed] Mutant: launch with `--app src.nonogram.admin.app` (CARD-139's defect). Against the unmodified tests: 59 passed, because no test ran to the launch line. Fix: `test_the_harness_reaches_the_end_of_the_script` now also runs without `--check-only` and asserts that the last `python` call is `python -m flask --app nonogram.admin.app run --port 5000`. Control: the fixed test under the mutant fails with `+ python -m flask --app src.nonogram.admin.app run --port 5000`.
- [Gate] Unarmed, `-rfs`: `tests/test_start_admin_local.py tests/test_admin_local_cost.py tests/test_setup_admin_local.py tests/test_run_admin_tests.py`: **108 passed**, 0 skipped. The two neighbour files are the sibling scripts' suites, which share `tests/helpers/admin_script_stubs.py`.
- [Test budget] Collected count: 10713 before, 10713 after, so the net change is **0**. Only existing tests were changed: three test functions in `tests/test_start_admin_local.py`.
