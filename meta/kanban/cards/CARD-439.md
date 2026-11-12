# CARD-439: A big puzzle on a phone can be solved one row or column at a time, in big cells

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 3c (0.75d)
<!-- Basis: one dialog over the existing player, driven entirely by the player's own strokes and history; the cost is the touch handling (tap, drag, long press) and proving it on a phone viewport. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** claude/project-thread-3lft6x
**Worktree:** — (built in a cloud session; handed over as a git bundle)
**Source:** owner 2026-11-12 (project thread "Design line-solving mode for small cells"): *"one more mode on mobile - primarily to deal with the small cells. To have a solve line\column mode - and then open screen with a small picture on top and a line presenting the selected line or column (cues above)"*. A mockup was agreed the same day, with the line split in two rather than scrolled: *"yes, I agree to split the line, it looks much more convenient than scrolling. Go ahead with it please"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/templates/_icons.html, tests/test_puzzle_solver_line.py, tests/test_puzzle_solver_page.py (PAGE_ISOLATION row)
**Review score:** —
**Started:** 2026-11-12T12:30Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

A 30 x 30 board on a 390 px phone has cells about 11 px wide and clue numerals about 7 px tall at Fit. Zoom (to 300 %) makes the cells about 33 px, but then a third of a row is visible and its clue is off screen. The line view shows one whole line and its clue at once, in cells about 23 x 48 px.

## What to implement

1. **Entry.** A *Line* button on the probe line, shown only on a compact screen (the CARD-407 query: `max-width: 600px` or `max-height: 500px`), only for a board at least `LINE_MIN_SIDE` (20) cells on its longer side, and not while the board is solved. It opens the row of the last board cell touched (row 1 before any).
2. **The view** (`#puzzle-player-line`, a dialog over the page): a head (*Board* to go back, "Row 14 of 30", a Rows/Cols toggle); a mini board (canvas) with the focused line outlined, a tap on it focusing the line under the finger, and previous/next arrows; the line's clue, each number struck through when the marks settle it (the board's own `circledNumbers`); the line as one strip, or two when longer than 15 (`lineStrips`: the first strip a whole number of fives, 30 = 15 + 15, 25 = 15 + 10, 20 = 10 + 10), with the board's heavy fifth rule and 1/5/10/15 index labels; the four brushes and Undo/Redo.
3. **Marking.** A tap, a repeat tap and a drag along the strip follow the board's own rules (`clickStroke` with the same repeat rule, `dragStroke`) and are recorded through the player's one `commit`, so the save, the probe, the hint ladder, Hint and Check all see them. A strip drag always marks (there is nothing to scroll). The brushes set the board's own brush.
4. **Pivot.** A press held 450 ms without moving marks nothing and focuses the line crossing the line at that cell; the Rows/Cols toggle pivots the same way through the last cell touched in the view.
5. **Leaving.** *Board*, Escape, or the board becoming solved (so the celebration is seen) closes the view. Nothing about the view is saved.

## Acceptance criteria

- **AC-1** (offered where it helps): the Line button is visible for a 30 x 30 at 390 x 844 and 844 x 390, and hidden for a 30 x 30 at 1440 x 900 and for a 15 x 15 at 390 x 844. (test: `TestSolverLine_IsOfferedOnlyForABigBoardOnAPhone`)
- **AC-2** (opens where you were): after a tap on a board cell, Line opens that cell's row. (test: `TestSolverLine_OpensAtTheLastCellTouched`)
- **AC-3** (one board): a tap, a repeat tap and a drag in the strip change the same cells on the board, are saved, and Undo in the view takes them back. (test: `TestSolverLine_MarksAreTheBoardsMarks`)
- **AC-4** (split, not scrolled): a 30-cell line draws as 15 + 15, a 25-cell one as 15 + 10, with no horizontal overflow at 390 px and cells at least 22 px wide. (test: `TestSolverLine_TheLineIsSplitInTwo`, plus the pure `lineStrips` cells)
- **AC-5** (pivot): a long press on cell k of row r focuses column k with cell r marked, and marks nothing. (test: `TestSolverLine_ALongPressOpensTheCrossingLine`)
- **AC-6** (leaves for the celebration): the stroke that solves the board closes the view. (test: `TestSolverLine_SolvingClosesTheView`)
- **AC-7** (public site): the public player (public mode, no solution) offers the same view; a mark made in it is the board's and is saved. (test: `TestSolverLine_ThePublicPlayerOffersItToo`). The public control sweep's census reads named attribute families and its sweep board is 10 x 10, under `LINE_MIN_SIDE`, so it neither lists nor reaches these controls; that is left as it is.

## Worktree notes
- **[Env]** Built in a cloud session on a bundle of the owner's `main` at `c94e57f4`; Python 3.14.6, Playwright 1.63.0 against the container's Chromium. Some layout cells measured on this Linux Chromium differ from the owner's Mac (fonts); the gate compares this branch with the same files run on `main` here, not with the Mac's numbers.
- **[Design, 2026-11-12]** The view's markup is built by solver.js (`buildLineView`) and only for a board of `LINE_MIN_SIDE` or more, not written in `puzzle_solve.html`. Written in the template first, it changed the page every census reads: the FROZEN base-css sample (25 buttons became 37), the public sweep's control census and the "How to play" bullets. Built only where it can be offered, a small board's page — which is what those censuses sample — is byte-for-byte the page it was. The mini board is an SVG whose cells are classed by state, so its colours stay in admin.css (`test_no_served_script_decides_a_colour`).
- **[Env]** A synthetic CDP swipe sent as one instantaneous jump is read by Chromium as a fling, and the next tap is spent stopping it (measured: the same happens after a fast Region drag on the board). The tests drag in 12 small steps with a pause, as a finger does.
- **[Gate, 2026-11-12]** The 36 files that touch the player, run on `main` and on this branch in the same container: `main` 119 red, this branch 118 red, **no test red here that is green on `main`** (the one difference is a hint-redraw cell that is flaky on this host). The reds are this Linux host's (fonts move the FROZEN measurements; `test_strokes_leave_the_console_clean` needs the Bootstrap CDN, which the sandbox blocks — red on `main` too). New: `tests/test_puzzle_solver_line.py`, 15 tests, all green; registered in `PAGE_ISOLATION`, `ADDED_SINCE_BEFORE` and `ALONE_PROBES`. Run the gate on the Mac before merging.
