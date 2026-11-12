# CARD-440: Line mode polish — the button before Hint, "?" apart from the selected line, and a tutorial step

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.25d)
<!-- Basis: three small owner requests on CARD-439's line view: one DOM insertion point, one colour, one tutorial step; the cost is measuring the toolbar row at phone widths. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/440-line-mode-polish
**Worktree:** ../PythonProject4-card-440
**Source:** owner 2026-11-12 (project thread, after trying CARD-439 live): *"Looks good. I'd place the button before hints, and grin preview on the picture for question mark looks the same as the selected line. And add please description abount this mode to the "How to solve" tutorial"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-439
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, player/how-to-solve.html, player/how-to-solve.js, player/player.css (comment), tests/test_how_to_solve_page.py
**Review score:** — (no review cycle; owner request, merged on the owner's go-ahead, 2026-11-12)
**Started:** 2026-11-12T14:05Z
**Closed:** 2026-11-12T14:40Z
**Actual:** —
**Merge commit:** dd75ac68
**Blocked by:** —

## Why

CARD-439 put the Line button on the probe line, after Probe; the owner wants it in the toolbar before Hint. On the line view's mini board a "?" cell was filled with the accent green at 45 %, and the focused line is the same green at 22 % with a green edge, so "?" cells read as part of the selection. And the site-wide How to solve page did not mention the mode.

## What to implement

1. **Placement.** `buildLineView` inserts the Line button just before `.player-history [data-player-action="hint"]`; the probe line stays the fallback for a page with no Hint button. Still built only for a board of `LINE_MIN_SIDE` or more, still hidden unless offered.
2. **Fit.** With a sixth button the portrait history row is 377 px against 374 at 390 px and wrapped whole (the board 52 px lower). While Line is offered, at `max-width: 600px`, the toolbar's column gap and the history group's gap are 4 px: one row from 364 px up. Landscape's two-column strip is unchanged (Line takes the cell beside Reset; Hint moves to a third row).
3. **Colour.** `.player-line-mini-maybe` is `color-mix(in srgb, var(--color-warning) 55%, var(--grid-paper))` (amber), a hue the focus band never uses. The strip's own "?" stays the board's accent glyph.
4. **Tutorial.** `/how-to-solve` gains step 5, "Big puzzles on a phone"; the levels become step 6 and stay last.

## Acceptance criteria

- **AC-1** (before Hint): at 390 x 844 and 375 x 812 on a 30 x 30, the history group reads Undo, Redo, Reset, Line, Hint on one row with the brush trigger, the toolbar 125 px tall as on `main`, no horizontal overflow. (measured, Worktree notes; the existing `TestSolverLine_*` classes find the button by `[data-player-line-open]` and still pass)
- **AC-2** (apart from the selection): a "?" cell on the mini board computes an amber fill, not the focus band's green. (measured, Worktree notes)
- **AC-3** (tutorial): `/how-to-solve#5` shows "Big puzzles on a phone", its Next reads "Next: Levels and the promise", and `#6` is the last step. (test: `test_the_wizard_moves_by_next_by_segment_and_by_fragment`)

## Worktree notes
- **[Measured, 2026-11-12]** Local assembled site, headless Chromium, touch, `/play/52603b6dee` (30 x 30). History x positions at 390 and 375: Undo 121, Redo 169, Reset 217, Line 265, Hint 313 (all y 51, 44 x 44); toolbar 125 px tall, `scrollWidth` equal to the viewport. At 360 the group still wraps to its own row (toolbar 177 px, no overflow) — on `main` it fitted there with one button fewer. At 844 x 390 the strip reads Undo/Redo, Reset/Line, Hint; the zoom control moves down 52 px and stays on screen.
- **[Measured, 2026-11-12]** With four "?" cells on row 1 and two on row 2: `.player-line-mini-maybe` computes `color(srgb 0.737 0.647 0.438)` (amber), `.player-line-mini-focus` `color(srgb 0.122 0.373 0.357 / 0.22)`; the "?" cells under the band read darker olive, still distinct from the band.
