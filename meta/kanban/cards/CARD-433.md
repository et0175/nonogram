# CARD-433: Region stays armed while the whole board is in view, and goes back to one-shot once it is zoomed in

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: no new control and no new markup — the change is WHEN the existing region flag is set and cleared, in solver.js's state machine. The cost is the predicate (what "the whole board is in view" means in code) and the brush-pick coupling, which reverses a standing decision and so has existing cells asserting the opposite. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/433-region-sticky-while-it-fits
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-433
**Source:** owner's play-test doc "Гра - тест", 2026-11-12, items 1 and 2: *"when we select a new brash (black\white…) select also 'Region'"* and *"In 100% or Fit mode select 'region' by default (the same as for the desktop)"*. Ruled the same day, asked as one question because both are about when Region is armed: **"Sticky only at 100%/Fit"** — armed and sticky while the whole board is in view; today's one-shot behaviour once it is zoomed in, where a drag is also how you pan.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_maybe.py
<!-- Derived 2026-11-12. The region flag, its arming and its post-drag disarm are all in solver.js (see its header, "region"); solver_state.js's nextRegion carries the independence note and may need its comment corrected but holds no zoom state. tests/test_puzzle_solver_brush_menu.py holds three of the five references to #puzzle-player-region and is where the brush/Region coupling is asserted; tests/test_puzzle_solver_maybe.py::TestSolverMaybe_DragPaintsMaybe drives a region drag. Re-derive with scripts/impact_set.py --gate rather than trusting this list: tests/test_puzzle_solver_marking.py and tests/test_puzzle_solver_zoom.py both drive drags and are likely in scope. -->
**Review score:** —
**Started:** 2026-11-13T08:10:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Region is a one-shot mode: pressing it arms a single drag, and it disarms itself the moment that drag is recorded. It is never saved, so every load starts with it off. On a phone that means a reader who wants to paint three runs presses Region three times.

It is also, by an explicit decision of **2026-10-14 (CARD-211)**, independent of the brush in both directions: *"arming Region never changes the brush and picking a brush never disarms Region"*. The owner has now play-tested the result and asked for the coupling back, in the direction that was never tried: picking a brush should **arm** Region.

**This card reverses a standing decision.** That is the owner's call, made with the product in hand, and it is recorded here so the next reader does not mistake it for drift: `solver.js`'s header and `solver_state.js`'s `nextRegion` note both state the independence rule as deliberate, and both must be rewritten by this card rather than left to contradict the code.

## The open point the implementation must settle, not assume

The owner's words are *"In 100% or Fit mode"*. Those name the zoom readout's label, but the label is not the property that matters. On a 390 px phone a 30×30 board at **100% does not fit** — it is the case CARD-432 is about, with 319 px of stage scroll. If Region were sticky there, a drag would paint instead of panning and the reader could not reach the rest of their own board.

So there are two candidate predicates:

- **A — the label**: zoom level is exactly 100%, or the reader pressed Fit.
- **B — the geometry**: the stage has no scrollable overflow in either axis, so no drag is needed to pan.

**B is the recommendation**, because it is what the ruling *means* ("while the whole board is in view") and because A has a measured failure case. The card must **measure where A and B diverge** at 390×844 for a small, a medium and a 30×30 board, write the figures into the notes, and implement B — and if the measurement shows them to agree everywhere that matters, say so and implement the simpler one. Do not implement A silently because the doc named a percentage.

## What to implement

1. While the board fits (predicate above), Region is **armed by default** at load, and **stays armed** after a drag is recorded.
2. While the board fits, **picking a brush arms Region** if it is off, and never disarms it.
3. Once the board does not fit, Region behaves exactly as it does today: off at load, armed only by its own button, disarmed after one drag.
4. Pressing Region itself always wins — a reader who turns it off gets it off, and a brush pick does not turn it back on until the next load. (This is the one rule not in the owner's words; it is here because without it the control cannot be switched off while the board fits. Flag it in the review if it reads wrong.)
5. The announce text ("Region on" / "Region off") keeps its current contract, and an unchanged value is still never rewritten.
6. Correct the two places that state the old rule as deliberate: `solver.js`'s header and `solver_state.js`'s `nextRegion` note.

## Acceptance criteria

- **AC-1** (sticky while it fits): at a viewport and board where the stage has no overflow, two consecutive drags both paint, with no press of Region between them. (test: a changed cell in `tests/test_puzzle_solver_maybe.py::TestSolverMaybe_DragPaintsMaybe`; plant: restore the post-drag disarm and the second drag paints nothing.)
- **AC-2** (a brush pick arms it): with the board fitting and Region off, choosing a brush from the menu leaves `aria-pressed="true"` on `#puzzle-player-region`. (test: the changed cell in `tests/test_puzzle_solver_brush_menu.py` that today asserts a brush pick leaves Region alone — it is asserting the decision this card reverses, so it flips, and its docstring must say which ruling flipped it.)
- **AC-3** (zoomed in, nothing changed): with the board overflowing its stage, load leaves Region off, one drag disarms it, and a brush pick does not arm it — the behaviour pinned today. (test: the existing cells, unchanged. This is the AC that keeps CARD-432's gesture available.)
- **AC-4** (off means off): with the board fitting, pressing Region off and then picking a brush leaves it off. (test: the cell from AC-2.)
- **AC-5** (the files stop contradicting themselves): no comment in `solver.js` or `solver_state.js` states that picking a brush never changes Region. (evidence: the replaced sentences, quoted in the notes.)

**Net test count: 0 added** — three existing cells change. If the fit predicate needs a cell of its own, that is **one** added, and the number is reported at the gate.

## Worktree notes
- **[Env]** forge 2026.10.29; no `meta/.skills.yml`, so no `min_version` comparison exists. Start gate `decision: gate` (command from `review.test_command`); fork point interactive/target tip. Pin, drift and state-table gates not applicable; no dependencies.
- **[Concurrency]** CARD-434 is `ready` and being picked up by another session. Checked rather than assumed before dispatching beside it: 434 touches `src/nonogram/admin/static/solver_state.js` + `tests/test_puzzle_solver_clues.py`, this card touches `solver.js` + `tests/test_puzzle_solver_brush_menu.py` + `tests/test_puzzle_solver_maybe.py`. No shared path, so no serialization needed — but `solver.js` imports from `solver_state.js`, so if 434 changes an exported signature the two meet at the rebase, not in the editor.
- **[Written before CARD-439 existed, read this before implementing]** This card was cut on 2026-11-12 and **CARD-439's line mode landed and shipped afterwards**. That matters here specifically, not generally: the line view is a second surface on which a drag paints, its strips "always mark (there is nothing to scroll)" by its own card's rule 3, and its brushes set the board's own brush. So a ruling about *when a drag paints* now has two places to be true, and the line view's rule is already unconditional. Derive what Region means inside the line view before changing anything, and say in the notes whether this card's predicate applies there, is irrelevant there, or needs a ruling.
