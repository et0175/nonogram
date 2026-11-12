# CARD-438: The portrait toolbar takes three rows to hold what fits in two, and the board pays 44 px for it

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: the rows are a grid in admin.css's compact block and no control changes; the cost is the frozen census and the geometry cells, which re-record whenever the toolbar's height moves. CARD-423 is the precedent: the same kind of change re-recorded 27 rows. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner's play-test doc "Гра - тест", 2026-11-12, item 7: *"Is it possible to have all the buttons in 2 lines on portrait mode"*, with a screenshot. **The screenshot was not readable** from the document export — the measurement below was taken instead, and the owner should confirm it shows what they saw.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-430
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_phone.py, tests/test_player_base_css.py
<!-- Derived 2026-11-12. The compact toolbar grid is in admin.css's `@media (max-width: 600px), (max-height: 500px)` block. tests/test_puzzle_solver_phone.py owns the portrait geometry (_CONTROL_BOXES, TestSolverPhone_CompactToolbar). tests/test_player_base_css.py's FROZEN census samples the toolbar's elements at 390 and MUST be re-recorded and re-certified against the pinned bootstrap@5.3.0 — it is outside the impact selection and reds at the gate if it is forgotten. tests/test_puzzle_solver_clues.py's ROOMS and TestSolverPhone_MirroredGutterSticks hold the scrollport figures that move when the toolbar's height changes (CARD-423 moved both). Re-derive with scripts/impact_set.py --gate. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The answer to the owner's question is yes, and here is the measurement

Production, 390×844, iPhone-class emulation, 2026-11-12. Every control in `.player-toolbar`, with its box:

| row (y) | controls | x range used | free to the right |
| --- | --- | --- | --- |
| 63 | Brush 44 · Region 49 · Undo 44 · Redo 44 · Reset 44 · Hint 44 | 16 → 325 | 49 px |
| 115 | Zoom out 44 · Zoom in 44 · 100% 39 … Hints: 0 (right-aligned at 311) | 16 → 374 | **160 px between the zoom group and the readout** |
| 159 | Probe 44, alone | 16 → 60 | **314 px** |

The toolbar is **125 px tall**; the stage below it gets **385 px of 844**, 46% of the screen for the thing the reader came for.

Probe is one 44 px button on a row of its own, and row 2 has 160 px of dead space in the middle. Moving Probe into that gap costs about 52 px of it and leaves roughly 108 px before the readout. **Two rows needs nothing dropped, nothing shrunk and no control merged.** The toolbar becomes about 81 px and the board gains 44 — 385 → 429, +11%.

## Read this before measuring again

The figures above are from **production as it stood at the moment they were taken**, and production has moved twice since. They do **not** include CARD-430 (the compact zoom as one joined pill), which changes the zoom group's width — one of the two numbers the free space is computed from — and they do **not** include **CARD-439's `Line` button**, a TWELFTH control added to this very toolbar on 2026-11-12, which the table above does not list at all. Both are live now. A twelfth control plausibly changes the row layout this card is built on, so the three-row reading, the 160 px of dead space and the 314 px on the Probe row are all suspect. The pill changes the zoom group's width, which is one of the two numbers the free space is computed from. **Re-measure on main before implementing**, and record both sets in the notes. Taking the table above as current is the mistake this paragraph exists to prevent.

## What to implement

The compact portrait toolbar lays its controls out in two rows, with the 44 px floor CARD-423 and CARD-424 established kept on every control, the DOM order kept as it is (CARD-429 put the zoom readout after `+` so focus follows the eye — do not reorder to make the rows come out), and the live region, the Hints readout and the solved state behaving as they do now.

How the rows are divided is the implementer's, informed by the re-measurement: the obvious arrangement is the six marking controls on row 1 and zoom + Probe + Hints on row 2, which is what the free space above allows, but say what was measured and why.

## Acceptance criteria

- **AC-1** (two rows): at 390×844 every visible control of `.player-toolbar` has one of exactly two distinct `y` values. (test: a changed cell in `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar`; plant: restore the third row and the cell reds.)
- **AC-2** (nothing was dropped to get there): the same twelve controls are present and hit-testable as today — brush trigger, Region, Undo, Redo, Reset, Hint, zoom out, zoom in, the readout, Probe, the Hints readout and the announce region. (test: the same cell, asserting the set by id/label, not the count.)
- **AC-3** (the 44 px floor holds): every control still measures at least 44 px in both axes, the readout excepted exactly as it is today. (test: `_CONTROL_BOXES` in the same module, unchanged in intent and re-pinned in figures.)
- **AC-4** (the board gets the room): the stage's height at 390×844 grows by the row that was removed — the figure measured on main, not the 44 px predicted here. (test: the scrollport cells in `tests/test_puzzle_solver_phone.py` and `tests/test_puzzle_solver_clues.py::TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::ROOMS`, re-pinned; the class name says what to do.)
- **AC-5** (the census is re-recorded, not patched): `tests/test_player_base_css.py`'s `FROZEN[390]` is re-measured whole against the pinned `bootstrap@5.3.0` (sha256 verified before the run), `PROVENANCE` says what moved and why, and `FROZEN[1280]` is asserted unchanged rather than assumed. (evidence: the certification run's output, in the notes.)
- **AC-6** (landscape is untouched): the `max-height: 500px` landscape strip, CARD-428's two-column zoom and CARD-430's joined block are unchanged. (test: the landscape cells in `tests/test_puzzle_solver_zoom.py`, unchanged.)

**Net test count: 0 added** — every cell above exists; this card re-pins figures and tightens one assertion.

## Worktree notes
- **[Note, 2026-11-12, orchestrator]** The control inventory in AC-2 says "the same twelve controls" by counting the table above; that table was measured before `Line` existed, so the real inventory at implementation time is **thirteen** — re-derive it from `tests/test_puzzle_solver_phone.py`'s `_LABELLED + _UNLABELLED`, which is now the maintained list and was itself corrected at CARD-437's close after CARD-439 landed the control without it. Do not count the table in this card.
