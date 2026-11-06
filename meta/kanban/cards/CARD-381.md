# CARD-381: Raise the hang guard's default to 300 s, and move every claim that quotes 120 s with it

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1c (0.5d) <!-- Stated in review cycles at DRAFT time (see CARD-380). -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-322 premise pass D6, owner ruling 2026-11-06 ("accept your recommendation for D6"). Cut bar: it blocks scheduled work (the flip card's geometry node, and every armed gate that runs `test_kill_matrix::test_ac7`).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/hang_guard.py, tests/test_suite_profile.py, tests/test_nfr001_generation_time.py, tests/test_book_pdf_memory.py, tests/test_db_isolation.py, tests/test_db_connect_timeout.py <!-- a starting list from a text search of "120 s" near "hang"; the author re-derives it by reading each hit (a text search is not a census) -->
**Review score:** —
**Started:** —
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
