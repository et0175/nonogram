# CARD-381: Raise the hang guard's default to 300 s, and move every claim that quotes 120 s with it

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1c (0.5d) <!-- Stated in review cycles at DRAFT time (see CARD-380). -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/381-hang-guard-300
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-381
**Source:** CARD-322 premise pass D6, owner ruling 2026-11-06 ("accept your recommendation for D6"). Cut bar: it blocks scheduled work (the flip card's geometry node, and every armed gate that runs `test_kill_matrix::test_ac7`).
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/hang_guard.py, tests/test_suite_profile.py, tests/test_nfr001_generation_time.py, tests/test_book_pdf_memory.py, tests/test_db_isolation.py, tests/test_db_connect_timeout.py <!-- a starting list from a text search of "120 s" near "hang"; the author re-derives it by reading each hit (a text search is not a census) -->
**Review score:** —
**Started:** 2026-11-06T08:46Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/hang_guard.py` kills the WHOLE pytest process at `NONOGRAM_TEST_HANG_SECONDS` (default 120). `tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces` already sits at that ceiling when armed and has killed two gate runs (CARD-326's gate was green only on a third run at 300). The premise pass for CARD-322 projects the geometry node `PortraitWithFixedTopEdge_pdf_pages` at about 125 s once the interior is vector (CARD-336 carried the figure), and G-4 forbids shrinking that corpus. Every gate brief has been carrying `NONOGRAM_TEST_HANG_SECONDS=300` as a standing override since.

**Owner ruling (2026-11-06): raise the DEFAULT to 300 s.** Not a per-test ceiling marker, not a speed-up of the tests. Cost accepted: a true hang is caught in 5 minutes instead of 2.

## What to implement

1. Change the default in `tests/hang_guard.py` to 300 and rewrite its comment: the slowest honest tests are now at or above the old bound, so say what the new bound is measured against (re-measure the slowest tests with `--durations`, state the figures as yours).
2. Every other claim that quotes the old number moves with it, found by READING each hit (the text search is only a start): `tests/test_suite_profile.py` (two comments quoting 120 s, one reasoning about 60 s against the timer), `tests/test_nfr001_generation_time.py` (its 122.04 s "past the ceiling" argument; it may now be under it, so re-derive what that test claims), `tests/test_book_pdf_memory.py:1412`, `tests/test_db_isolation.py:589` (a rendezvous of 45 s "comfortably under 120"; still true, but the sentence is stale).
3. Remove the need for the standing override: after this card no gate brief says `NONOGRAM_TEST_HANG_SECONDS=300`. Record that in the card, not in a doc that drifts.

## Acceptance criteria

- **AC-1** *Given* `tests/hang_guard.py`, *then* `HANG_SECONDS` defaults to 300 with the env override intact and the guard's own subprocess tests (`tests/test_db_connect_timeout.py`) pass unedited. (test: the existing hang-guard tests, named by the implementation)
- **AC-2** *Given* any test or comment that quotes the old 120 s bound, *then* it either states 300 or is shown by the author to be about something else. (test: a census test that no quoted number disagrees with `HANG_SECONDS`, with a control that can fail; or check: review-lens if no mechanical form exists, stated honestly)
- **AC-3** *Given* the armed full suite on this card's tip with NO override, *then* it passes with zero killed runs and `test_kill_matrix::test_ac7` included. (test: the armed full-suite gate)

## Guardrails

- **G-1** The guard still kills on a real hang; the mechanism (`faulthandler.dump_traceback_later(..., exit=True)`) is not changed.
- **G-2** No test deleted, renamed, skipped or merged, parametrize ids included.
- **G-3** The corpus of any slow test is not shrunk to fit (CARD-322 G-4).
- **G-4** Run the standing census modules after the edit (see the board's census rule); `test_suite_profile` is touched, so run it fully.

## Worktree notes

(none yet)

[Author round, commit `f226eed2`] Verified by the orchestrator by git facts only: tip `f226eed2`, one commit over the cut `979771c7`, worktree clean; six files, all in Touches (`tests/hang_guard.py` 35 lines changed, `tests/test_book_pdf_memory.py` 2, `tests/test_db_connect_timeout.py` 2, `tests/test_db_isolation.py` 2, `tests/test_nfr001_generation_time.py` 35, `tests/test_suite_profile.py` 59; 94 insertions, 41 deletions); `src/`, `meta/` and `tests/helpers` diffs 0; no added bare early `return`, skip or xfail; `HANG_SECONDS` default now `"300"` with the env override and the `faulthandler` mechanism unchanged. Not re-run by me. Author-reported (labels the author's): node ids 10762 before and after, identical sets, nothing added or removed; the 14 census modules (13 plus `test_db_connect_timeout`) 1107 passed, 3 skipped (all unarmed-DB), 0 failed; plant: default put back to 120, `TestSuiteCeiling_TheCliffEdgeListIsDerived` gave 2 failed, 3 passed (the cliff-edge list gained 5 rows because the 60 s line moved to 24 s), file restored byte-identical (`cmp`); measured by the author at load about 7 with the new default and no override, one module at a time: `tests/test_kill_matrix.py` passes (76 tests, 119 s) with `test_ac7_the_four_arm_grid_of_card_257_reproduces` at 80.28 s, and the dearest test across four other heavy modules is 17.94 s; CARRIED: test_ac7 reaching about 120 s under an armed gate, CARD-336's projected 125 s geometry node, the 122.04 s uncensored sweep, the 1433.47 s suite figure. Disposition table of ~20 hits is in the author's report (states-the-default hits changed; subprocess timeouts, gunicorn's 120 s, an Alembic `timeout=120` and "a suite run time" hits deliberately untouched). **Judgement call to review: `CEILING_FRACTION` 0.5 -> 0.2** (same 60 s cliff-edge line against the 300 s ceiling; keeping 0.5 would put the line at 150 s, above every row of the artefact (dearest 81.03 s), emptying the frozen list and leaving `test_both_cliff_edge_rows_are_tests_the_suite_still_collects` with nothing to collect); rewrites CARD-292's "within 50 %" wording; the alternative is to empty the list. `test_nfr001_generation_time.py`: its 122.04 s premise now has 178 s of margin; the author kept "stays out of the suite" on other grounds and did not re-run the sweep. `test_db_connect_timeout.py` has a docstring-only edit (AC-1 says "unedited"; no test code changed, 5 pass). **AC-2 is REVIEW-LENS** (no honest mechanical form for prose such as "comfortably under the hang guard's 300 s": a regex over free text would match gunicorn's 120 s, subprocess timeouts and dated notes; the one mechanical part is the AST read of the default asserting 300, with the plant above). AC-3 (armed full suite with NO override) is open for the merge gate. Owed by the orchestrator (meta/): `meta/kanban/config.yml` line ~328 "(120 s)" in the per-test-ceiling cell comment (line 341's 120 s is a shell tool timeout, unrelated); `dispatcher.state` ~2922 quotes "hang_guard's 120s" in an old historical comment (left as history). Not reviewed.