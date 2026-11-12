# CARD-431: The puzzle's title is 20 px in the compact portrait layout, not 30

**Status:** in_progress
**Priority:** P3
**Category:** feature
**Estimate:** 1c (0.25d)
<!-- Basis: one CSS value; the cost is re-pointing whatever measures the heading or the board's place under it. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/431-title-size
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-431
**Source:** owner 2026-11-12 (project thread): "in landscape mode the title looks much smaller. Maybe it makes sense to make it smaller in the Portrait mode?"; proposed 20 px (portrait was 30, landscape 16); "yes please".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css
**Review score:** —
**Started:** 2026-11-12T11:45Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

In the compact layout (`max-width: 600px` or `max-height: 500px`) `.player-head h1` is `--text-lg` (1.25rem, 20 px) instead of `--text-xl` (1.9rem). The landscape strip keeps its own `--text-base`, which still wins there.

## Acceptance criteria

- **AC-1** *Given* a compact portrait viewport, *then* the puzzle's heading computes to 20 px and the landscape strip's to 16 px. (test: the player set's existing phone and geometry cells, re-pointed where they measured the old heading)

## Worktree notes
- **[Gate, 2026-11-12]** Player set: 1396 passed, 5 red, all the intended consequence: the 20 px heading gives the board 13 px more height, and four cells pin the stage's measured overflow and port (`TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted` 390x844 and 600x844; `TestSolverPhone_MirroredGutterSticks` both cells) — re-pointed to the new measurements with the old ones kept in their history comments; the base-css FROZEN table re-recorded (green against the real Bootstrap and the project stylesheet). After: clues, phone and base-css 110 passed.
