# CARD-548: CARD-277's 225-cell zoom drag: reproduce it, or measure that it does not reproduce

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/548-reproduce-zoom-drag
**Worktree:** ../PythonProject4-card-548
**Source:** roadmap wave 23, cut 2026-11-26 on the owner's "card CARD-277's reproduction and carry on". This splits out step 1 of CARD-277 ("Reproduce it first ... This is the whole card"), plus the path capture of step 2.
**Idea:** —
**Wave:** 102
**Created wave:** 102
**Deferred waves:** 0
**Depends on:** —
**Touches:** nothing in `src/`; a scratch harness and instrumentation outside the tree (the scratchpad or `/tmp`-style location), and this card's notes. `tests/test_puzzle_solver_zoom.py` only if a run needs a temporary probe, and that probe is reverted before commit.
**UI surface:** —
**Review score:** —
**Started:** 2026-11-26T14:02Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-277 records one observation from CARD-270's fix round (2026-10-22). A mouse drag at 200% zoom marked **225 cells instead of 5**: every cell of the 15×15 board. Two tests in `tests/test_puzzle_solver_zoom.py` failed together:
- `test_a_mouse_drag_at_200_percent_still_marks_along_the_dragged_line`
- `test_marks_zoom_and_circles_survive_crossing_both_ways`

It did not reproduce in four later runs. CARD-277 names three suspects, each needing a different fix:
1. a redraw mid-drag: a real bug in `solver.js`;
2. under-stepped synthetic mouse moves: a test artifact;
3. scroll skew under `elementFromPoint`: could be either.

CARD-277 forbids writing a fix against a suspect. This card does only the reproduction, so the fix card starts from a measured fact.

## What to implement

1. **Declare the budget before running.** Default:
   - 50 runs of the two tests alone, by node id;
   - 10 runs of the zoom file with `tests/test_puzzle_solver_page.py` and the other browser files of the solver family. CARD-277 says the one failure was in a multi-file run. Re-derive the twelve-file set from CARD-270's notes if it can be identified; otherwise state the set used.

   Run under `caffeinate -i`. A run that overlaps a sleep in `pmset -g log` is excluded and counted separately, because Playwright's timers count time asleep.
2. **Instrument so a hit is diagnosable.** Before the loop, add instrumentation that would capture, for each `pointermove` of the drag:
   - `gesture.path` (or the stroke's cell list);
   - the board's scroll offset and bounding rect;
   - whether a `redraw()` fired.

   For example, a page-side `addInitScript` hook or a temporary console log read by the test. The instrumentation must not change behaviour.
3. **If it reproduces:** record the captured path and say which of CARD-277's three suspects it selects, and why: a contiguous sweep, a jump, or a superset. **Do not fix anything.** The fix is CARD-277's.
4. **If it does not reproduce:** record the run count, the selections, the zoom level, the load average, and the instrumentation that would have caught it.
5. Leave nothing behind. `src/` is unchanged and any temporary test probe is reverted. The commit carries only this card's notes, and the net test count is 0.
6. Do not run load processes to provoke it. If you judge load necessary, cap it at 8 processes, start and kill them in the same command with a trap, and say so.

## Acceptance criteria

- AC-1: the budget is declared in the notes before the first run, and the result is reported against it: N runs per selection, hits, excluded sleeps, and load. A "0 of N" result is a valid outcome.
- AC-2: the instrumentation's ability to see a hit is shown, not asserted. Demonstrate on one deliberately broken run that the capture records a path; for example, a forced `redraw()` mid-drag injected only in the scratch harness, or an under-stepped drag. Then remove it.
- AC-3: `git diff --name-only main...HEAD` lists only `meta/kanban/cards/CARD-548.md`.
- AC-4: if it reproduces, the captured path and the suspect it selects are recorded. If it does not, the notes give CARD-277 a recommendation: keep it, adding the permanent count detector of its AC-4, or close it as unreproduced.

## Worktree notes
