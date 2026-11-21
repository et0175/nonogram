# CARD-512: Two test-instrument holes from wave 7: the session lock's escape hatch and test_wraps' paint check

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/512-lock-escape-paint-check
**Worktree:** ../PythonProject4-card-512
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-220 (CARD-508 review F-001) and IDEA-222 (CARD-507 review F-006), bundled: each alone is below `sizing.min_estimate`.
**Idea:** IDEA-220, IDEA-222
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_db_isolation.py or tests/test_card_156_db_fixture.py (the lock's existing tests), tests/test_puzzle_solver_maybe.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-21T11:04Z
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
- [Built] 2026-11-21. Armed runs used only this worktree's resolved database `nonogram_pythonproject4_card_512_7c5450c32b4a_test` on localhost (from `tests.db_name.resolve_test_database_url`). Scratch scripts and logs: /private/tmp/claude-501/card512/.
- IDEA-220 (OPEN on base, FIXED). Premise measured on base with a temporary probe (holder: `db_session`, commit a `Batch`, sleep 15 s, read back; never committed) and, 6 s later, `test_db_e2e_smoke.py::test_db_session_fixture_works` with `NONOGRAM_TEST_DB_SESSION_LOCK` hand-set to the database name: the holder failed `AssertionError: saw []`, the second run `1 passed`. Same pair without the variable: holder passed, second run refused ("another pytest run is using it"). Fix, in tests/conftest.py: the holder now exports `<database>:<its os pid>:<its backend pid>` (`_session_lock_value`), and `_session_lock` skips the lock only when `_held_by_parent` passes: the value names this database, its os pid is `os.getppid()`, and its backend pid holds the 508031 advisory lock in `pg_locks` on this database (granted). Anything else takes the lock as before, so a forged or stale value meets the existing refusal. After the fix the same pair, hand-set bare name: holder `1 passed`, second run refused; hand-set `<db>:<the shell's pid, the run's real parent>:999999`: holder `1 passed`, second run refused. Not covered: a grandchild of the holder (refused; no test in `tests/` starts one), and a real child its parent does not wait for (still a convention, as before).
- AC-1 test: `test_db_isolation.py::TestDbIsolation_TwoTreesDoNotCorruptEachOther::test_two_trees_pass_concurrently_and_the_same_pair_reds_when_they_share` extended, not added. `_run_two_trees` takes `intruders`; the shared arm runs two more probes in tree B's root once tree A holds the database: "copied" sets tree A's exported value as its own (live holder, wrong parent), "dead" carries this process (its real parent) with a closed connection's backend pid (`_closed_backend_pid`). Both must show "another pytest run is using it". The probe writes its exported value to `<signal>.lock`. The real child is test_card_349's `TestColdDatabase_TheTwoDatabaseGatesStayAttributable` (5 passed armed).
- Controls (mutant applied, node run, file restored from a saved copy, `cmp` identical and `git diff --stat` unchanged after). L1: main's conftest -> red at `assert "another pytest run is using it" in shared_output[2]` ("copied: ... 1 passed"): main lets the copied value in. L2: the `os.getppid()` check removed -> red at the same assert. L3: `pg_locks` result replaced by `True` -> red at `... in shared_output[3]` ("dead: ... 1 passed"). L4: `_held_by_parent` always `False` -> test_card_349's re-raise control red at `assert clean_code == 0` (the real child refused).
- IDEA-222 (OPEN on base, FIXED). Premise measured: with `.player-solved > span`'s `overflow: hidden` replaced by `pointer-events: none` in admin.css, `TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth` gave 6 passed. Fix: `test_wraps` scrolls the banner into view, and `_name_paints` screenshots two rects from `_BANNER_TEXT` (the name's first line, and its first line laid out below the box, cut to below the box and shrunk to whole pixels) with the name visible and with it `visibility: hidden`. It asserts the first line changes (the instrument sees the name) and the below-the-box line does not. The `elementsFromPoint` check is gone. Plants: `pointer-events: none` in place of `overflow: hidden` -> 6 failed at `assert painted["below"] is False` (`{'first': True, 'below': True}`); `overflow: hidden` removed -> 6 failed at the same assert. Instrument control: the hide made a no-op -> red at `assert painted["first"] is True` (`{'first': False, 'below': False}`). admin.css restored after each plant (not in the diff). Main's CSS: 6 passed, three repeats 6/6 each. Node ids unchanged, so `RENAMED_SINCE_BEFORE` is untouched.
- AC-3: collected 10690 before and 10690 after (net 0).
- Gate (no full suite; tests/conftest.py is gate-wide, the orchestrator's merge gate runs it): tests/test_db_isolation.py, test_card_156_db_fixture.py, test_db_connect_timeout.py, test_db_e2e_smoke.py, test_shared_fixture_controls.py, test_puzzle_solver_maybe.py, test_browser_fixture_scope.py, test_kanban_review_record.py, test_card_349_cold_database.py (the other lock test: the real child). Unarmed `-rfs`: 290 passed, 14 skipped (all "Database not reachable: DATABASE_URL is not set"), 0 failed. Armed `-rEfs`: 304 passed, 0 skipped, 0 failed, 0 errors. Afterwards no advisory lock on 508031 is held on this worktree's database.

[Review 1/3] Score: 9.5, nothing gating, certified. Controls re-run: L1 (main's conftest) reds at `shared_output[2]`, L3 (`pg_locks` forced True) at `shared_output[3]`; both paint plants red 6/6 at `painted["below"] is False`; the "below" rect starts at the clamp box's bottom at every viewport (about 14 px tall, 47-154 px wide); 294 runs on the real CSS gave no false "below". False refusals: every subprocess/os call under tests/ walked by `ast` (90 sites); every child pytest that reaches fixtures is started directly (`sys.executable -m pytest`), the `make` wrapper runs a stub, the `sh -c` launches are `--collect-only`; armed, the seven lock-adjacent files 121 passed. A probe showed direct, `env` and single-command `sh -c` children pass, a forking shell or a grandchild is refused: a constraint on future tests, nothing breaks today. F-001 (low): 1 of 49 runs of `TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth` on main's CSS gave 1 failed / 5 passed, output not captured, assertion unknown; if it recurs at a gate, capture the assertion first. F-002 (low): `_held_by_parent`'s `database =` clause has no committed control (checked by hand: a lock on another database is rejected). F-003 (info): the constraint above. F-004 (info): a refused run stops before `_rebuild_public_schema`; CARD-508's F-004 (non-db_required app builders read DATABASE_URL themselves) still stands.
