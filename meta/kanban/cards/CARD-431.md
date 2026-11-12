# CARD-431: The puzzle's title is 20 px in the compact portrait layout, not 30

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 1c (0.25d)
<!-- Basis: one CSS value; the cost is re-pointing whatever measures the heading or the board's place under it. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-12 (project thread): "in landscape mode the title looks much smaller. Maybe it makes sense to make it smaller in the Portrait mode?"; proposed 20 px (portrait was 30, landscape 16); "yes please".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css
**Review score:** — (no review cycle; merged on the gates)
**Started:** 2026-11-12T11:45Z
**Closed:** 2026-11-12T12:09Z
**Actual:** one owner session (wall clock excluded, owner ruling)
**Merge commit:** 408839b8
**Blocked by:** —

## What to implement

In the compact layout (`max-width: 600px` or `max-height: 500px`) `.player-head h1` is `--text-lg` (1.25rem, 20 px) instead of `--text-xl` (1.9rem). The landscape strip keeps its own `--text-base`, which still wins there.

## Acceptance criteria

- **AC-1** *Given* a compact portrait viewport, *then* the puzzle's heading computes to 20 px and the landscape strip's to 16 px. (test: the player set's existing phone and geometry cells, re-pointed where they measured the old heading)

## Worktree notes
- **[Gate, 2026-11-12]** Player set: 1396 passed, 5 red, all the intended consequence: the 20 px heading gives the board 13 px more height, and four cells pin the stage's measured overflow and port (`TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted` 390x844 and 600x844; `TestSolverPhone_MirroredGutterSticks` both cells) — re-pointed to the new measurements with the old ones kept in their history comments; the base-css FROZEN table re-recorded (green against the real Bootstrap and the project stylesheet). After: clues, phone and base-css 110 passed.
