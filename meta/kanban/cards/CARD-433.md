# CARD-433: Region stays armed while the whole board is in view, and goes back to one-shot once it is zoomed in

**Status:** done
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
**Review score:** 9.0 (cycle 2)
**Started:** 2026-11-13T08:10:00Z
**Closed:** 2026-11-13T09:05:00Z
**Actual:** 2 review cycles + 1 fix round (wall clock excluded, owner ruling 2026-11-07)
**Merge commit:** 23ad1e3c
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
### What this card settled, and how
**The predicate: B (the geometry), implemented.** `boardFits()` in `solver.js` reads
`.player-stage`'s own scrollable overflow — `scrollWidth <= clientWidth && scrollHeight <= clientHeight`
— and nothing about the zoom readout.
**A vs B, measured** (Chromium, this suite's fixtures; stage overflow x × y in px, at the zoom
whose readout says `100%`). **Every row names its board**, because stage overflow is a property of
the particular grid and not of its size — the x overflow follows the deepest *row* clue and the y
overflow the deepest *column* clue. The instrument for every cell below is one expression,
`tests/test_puzzle_solver_brush_menu._overflow` (`.player-stage`'s `scrollWidth - clientWidth` /
`scrollHeight - clientHeight`), against a board opened with `_open(page, live, live.store(grid))` at
the viewport in the column header; so each row is re-derivable from its seed alone.
| board | 390×844 (phone) | 1024×768 | 1280×720 | at Fit, all three |
|---|---|---|---|---|
| 10×10 `_unique_grid(10, 10, seed=40701)` | 0 × 0 — **agree** | — | 0 × 0 — **agree** | n/a (no Fit exists) |
| 15×15 `_unique_grid(15, 15, seed=161)` (the suite's `GRID`) | **6 × 0 — diverge** | 0 × 0 — agree | 0 × 0 — agree | 0 × 0 — agree |
| 15×30 `_unique_grid(15, 30, seed=433)` (`SCROLLING_GRID`) | **6 × 170 — diverge** | **0 × 95 — diverge** | **0 × 133 — diverge** | 0 × 0 — agree |
| 20×20 `_unique_grid(20, 20, seed=301)` (`test_puzzle_solver_page.AC301_GRID`) | **113 × 0 — diverge** | — | 0 × 0 — agree | 0 × 0 — agree |
| 30×30 `_unique_grid(30, 30, seed=19330)` (`test_puzzle_solver_clues.GRID_30x30`) | **346 × 170 — diverge** | — | **0 × 133 — diverge** | 0 × 0 — agree |

**[RETRACTED, review cycle 1 F-003 — ADR-0039/R4]** The 20×20 row said **96 × 0** and named no
board, and so did the implementation commit's message (`565ff801`, "a 20 x 20 with 96 x 0"); the
commit message cannot be edited, so the retraction lives here. The reviewer recomputed it on the
suite's only 20×20 and on an independently seeded one, both giving **113 × 0**, and the fix round
re-derived all five rows a third time on 2026-11-13 with the instrument above: `seed=301` → `113 × 0`
and `seed=4332` → `113 × 0` at 390×844, `seed=301` → `0 × 0` at 1280×720. **Nothing reachable here
gives 96, and the figure's domain — *which* 20×20 — was missing, which is the other half of the
finding.** The conclusion is untouched: 113 > 0 diverges from the "100%" label exactly as 96 would.
The other four rows were re-derived unchanged in the same run (`6 × 0`, `6 × 170` / `0 × 95` /
`0 × 133`, `346 × 170` / `0 × 133`, `0 × 0`) — and the reason a board must be named is itself
measured: a *different* 30×30, `_unique_grid(30, 30, seed=40601)`, gives **346 × 185** at 390×844 and
**0 × 148** at 1280×720, so the size alone does not fix the figure. The three figures quoted in
`boardFits`'s own note in `solver.js` now carry these same seeds and point at the cells that run them.
So A and B **agree exactly where the board really is in view** — small boards, and *every* board at
Fit (because `fitTheFloor`'s overshoot loop steps the floor down until nothing scrolls) — and
**diverge on every board bigger than its stage at 100%**, which is the case the ruling was written
for. A would have armed Region on a phone with 346 px of board the reader could then no longer
reach by dragging. The card's own figure (319 px for a 30×30 at 390) measures 346 × 170 here.
Two measurements the card did not predict:
* the divergence is **not phone-only** — a 30×30 at 1280×720 reads "100%" with 133 px of vertical
  scroll, so A is wrong on the desktop too;
* B reads the **stage** only. On a phone a board that fits leaves the document with no overflow
  either (measured 0 for a 10×10 at 390×844), so nothing is stranded; at 1280×720 a fitting board
  still leaves 49 px of *document* scroll, reachable by a finger on a touch laptop and by the wheel
  everywhere. Not in the predicate: making it depend on page length would make Region flicker with
  a banner appearing.
**Region in the line view (CARD-439, which this card predates): irrelevant there, and unchanged.**
Derived by reading, not assumed: the strip's own pointer handlers (the ones guarded on
`lineGesture`, inside `buildLineView`'s wiring) never consult
`region` or `gesturePaints`, and the view's own rule 3 is that a strip always marks "because there
is nothing to scroll" — which is CARD-433's predicate already true unconditionally, for the same
reason. So this card's predicate neither applies nor needs an owner ruling there, and no line-view
code was touched. One measured asymmetry, recorded rather than fixed: the line view's brush buttons
set `tool` inline (the `lineParts.tools` click listener) rather than through `pick()`, so a brush
picked **in the line
view** does not arm Region. It is observable only in one path (board in view, Region off because the
reader zoomed in and back out, then a brush picked from the strip rather than the board) and
changing it is CARD-439's subject. No card: below the cut bar.
### Rules beyond the owner's words — flagged for the review
1. **Rule 4 (the card's own):** a press of Region OFF is latched (`regionOff`) and the brush picks
   that follow leave it off until the next load. Without it the control cannot be switched off while
   the board is in view. It is also what makes AC-2 and AC-4 consistent: the "off while the board
   fits" that a brush pick arms is reachable only without a press — load on an overflowing board,
   then bring it into view — which is the path AC-2's cell walks.
2. **A board that STOPS being wholly in view disarms Region** (`syncRegionToFit`). Not in the
   owner's words, and it is rule 3 taken literally ("once the board does not fit… armed only by its
   own button"): without it the commonest phone flow breaks the gesture CARD-432 had just fixed —
   a big board opens at Fit (CARD-407) with Region armed, the reader taps `+`, and the drag they
   make to pan paints a run instead. It fires on the TRANSITION, not the state, so a Region armed by
   its own button on a board that was already scrolling survives a resize and a zoom exactly as
   before. Its one cost is an order change in one existing cell: arming Region and *then* zooming in
   no longer keeps it armed (`test_a_region_touch_drag_at_200_percent_marks_exactly_five_cells`
   presses Region after the zoom now).
3. **The load's default is not announced.** `settleRegion` writes `aria-pressed` and the board's
   class but no live-region line: it is an initial state, not a change, and `#puzzle-player-announce`
   holds a restored solved board's banner at that moment (the ordering
   `test_a_drag_that_solves_the_board_announces_the_banner_instead` pins). AC-5's contract is kept —
   an unchanged value is still never rewritten.
### AC-5 is partially met — and the half that is not is a [BLOCKER]
`solver.js` is clean: the `region` block in its header, the gesture block's statement of the
one-shot disarm, `setRegion`'s "every caller goes through nextRegion" claim (which this card made
false and which is rewritten), `pick`'s own note and `syncTrigger`'s were all rewritten to state
the current rule and to name the ruling that changed it. The replaced sentences, quoted:
* header: *"Picking a brush leaves Region exactly as it was: a DELIBERATE divergence from CARD-194's
  target behaviour #3, decided by the owner on 2026-10-14 (CARD-211)… So the two controls are
  independent in both directions"*;
* `setRegion`: *"Every caller goes through solver_state.js nextRegion, so this function never
  decides the transition itself"*;
* `pick`: *"picking one restarts the click sequence but leaves Region alone… so there is no
  setRegion call here"*.
**[BLOCKER] decomposition defect (recorded, not stopped on): `solver_state.js`'s `nextRegion` note
still states the rule this card reverses, and this card could not edit it.** CARD-434 holds that
file concurrently (its `Touches:` is `src/nonogram/admin/static/solver_state.js`,
`tests/test_puzzle_solver_clues.py`), and the brief forbids touching it. The two sentences now
false, verbatim, from the "DELIBERATE DIVERGENCE" note above `nextRegion` (resolve it by that
name, not by a line number):
> *"so there is no "brush" event any more and picking a brush leaves Region exactly as the user left
> it. The two controls are now independent in BOTH directions. This is a decision, not drift:
> anything still saying a brush pick disarms Region is stale."*
The first clause and the second sentence are stale as of this card; the third sentence is still
true (a pick never *disarms* Region, which is why `"brush"` stays a refused event name and
`TestRegionRules_PureFunctions` is unchanged). `solver.js`'s header names this file and this note as
stale so a reader is not misled in the meantime, but **AC-5 as written is not met** and the edit is
owed: it is two sentences, in the file CARD-434 is already editing, and the cheapest resolution is
for CARD-434 (or the merge that follows it) to carry them. Flagged for the review rather than worked
around, because a comment that contradicts the code is a defect in its own right here.
### AC evidence
* **AC-1** (sticky while it fits): test `tests/test_puzzle_solver_marking.py::TestSolverMarking_DragMarksOneLine::test_a_touch_drag_marks_one_line`
  **red → green**. Red for the right reason: `_region_pressed == "true"` at load read `false`, with
  the cell's own `[0, 0]` overflow premise asserted and passing first. Two consecutive real CDP
  touch drags (rows 1 and 7), no Region press anywhere in the cell. Plant named in the docstring:
  restoring the unconditional post-drag `setRegion(nextRegion(region, "drag"))` leaves the second
  drag marking nothing.
* **AC-2** (a brush pick arms it): test `tests/test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_Region::test_picking_a_brush_leaves_region_armed`
  **red → green**. Red for the right reason: at Fit (overflow asserted `[0, 0]` in the cell) a brush
  pick left `aria-pressed="false"`. Name unchanged; docstring names the 2026-11-12 ruling that
  flipped it and the 2026-10-14 decision it used to assert.
* **AC-3** (zoomed in, nothing changed): the existing cells, assertions unchanged, on a board whose
  stage really overflows — `TestSolverRegion_ArmedDragMarksThenDisarms` (3),
  `TestSolverRegion_UnarmedTouchDragStillScrolls` (1), `TestSolverRegion_DoesNotChangeTheBrush` (5),
  `TestSolverRegion_AnnouncesItsState` (5), `TestSolverBrushMenu_Pen` (2),
  `TestSolverRegion_KeepsItsAccessibleNameAndPressedState` (1), two cells of
  `TestSolverBrushMenu_RegionIsItsOwnToggle` and three of `TestSolverBrushMenu_Region`, plus step 1
  of AC-2's own cell. All **green**.
* **AC-4** (off means off): the AC-2 cell, step 3 — **red → green** (red: the brush pick after the
  press re-armed it, there being no `regionOff` latch yet).
* **AC-5**: `solver.js` met; `solver_state.js` blocked — see above.
### Scope
`Touches:` predicted `src/nonogram/admin/static/solver.js`,
`tests/test_puzzle_solver_brush_menu.py`, `tests/test_puzzle_solver_maybe.py`. All three are in the
diff. Beyond them:
* `SCOPE+ tests/test_puzzle_solver_marking.py` — it holds the suite's only **touch** drag on a board
  that is wholly in view, which is the only place AC-1 can be asserted at all (see "what the card
  got wrong" below). The card's own derivation note predicted this file.
* `SCOPE+ tests/test_puzzle_solver_zoom.py` — two cells armed Region by hand on a 15 x 15 at
  1024 x 768, which has no stage overflow (measured 0 x 0), so the press now turns it OFF; one of
  them then zoomed to 200%, where rule 3's disarm applies. One press dropped, one press moved after
  its zoom. The card's derivation note predicted this file too.
* `SCOPE+ tests/test_player_public_mode.py` — the public player is a build-time COPY of this
  `solver.js` (`scripts/assemble_player_site.py`), and the control sweep's `step_region` asserted
  Region off at load and disarmed after a drag on a 10 x 8 board that is wholly in view. Rewritten
  to drive the control on its real premise (and it now asserts that premise).
### What the card got wrong
1. **"Net test count: 0 added — three existing cells change."** 0 added is right (node ids are
   byte-identical to main: `--collect-only` over the five changed test files diffs clean, 280 ids,
   nothing added, removed or renamed). "Three cells" is not: **25 cells changed across 6 files.**
   The reason is measurable and the card could not have guessed it without measuring — **the suite's
   default board has no stage overflow at the suite's default viewport** (15 x 15 at 1280 x 720:
   0 x 0), so under predicate B it is a board "wholly in view" and every cell that pinned Region's
   off-at-load or one-shot behaviour lost its premise. Nineteen of the 25 are a one-token change of
   the board the cell opens (`GRID` -> `SCROLLING_GRID`), with every assertion left verbatim; the
   card's own AC-3 asked for exactly that ("the existing cells, unchanged"), it just did not know
   the cells were on the wrong board for it.
2. **AC-1's named test cannot carry AC-1.** The card points it at a changed cell in
   `tests/test_puzzle_solver_maybe.py::TestSolverMaybe_DragPaintsMaybe`, whose three drags are
   MOUSE drags — and `gesturePaints`' first rule is that a mouse drag always marks, whatever Region
   says. So the plant the card names for it ("restore the post-drag disarm and the second drag
   paints nothing") cannot fire there: the second drag paints either way. AC-1 is asserted on the
   touch drag instead.
3. `tests/test_puzzle_solver_maybe.py` **is** in scope, but not for the reason `Touches:` gives: its
   "?" glyph cell diffs two screenshots to isolate one cell, and with Region now armed at load the
   toggle's 150 ms colour transition into its pressed look landed in that diff — 226 x 440 px of it,
   with the glyph's own rectangle outside the bounding box. A 300 ms settle before the pair, the same
   wait and the same reason as `test_player_base_css.py`'s `_settle`.
4. **The 319 px figure.** The card says a 30 x 30 at 390 px has "319 px of stage scroll"; measured
   here it is 346 x 170 (x and y). Not a correction of CARD-432 — a different measurement (that card
   measured one axis of a different board state) — but the figure to quote from now on is this one,
   and it is 170 px in the OTHER axis too, which A ignores just as completely.
5. **The divergence is not phone-only.** The card frames A-vs-B as a 390 px problem. A 30 x 30 at
   1280 x 720 also reads "100%" with 133 px of vertical stage scroll, so predicate A is wrong on the
   desktop as well. This is what made B, not "B on a compact screen", the honest choice: a media
   query would make the same board behave differently at 601 px and 600 px for no reason the reader
   can see, and would leave a touch laptop with the complaint the owner raised.
6. **Two more files the card could not have predicted**, both found by running rather than reading,
   and both the same shape — a page the ruling reaches whose board is wholly in view:
   `SCOPE+ tests/test_puzzle_editor_ui.py` (the manual editor loads this same `solver.js`, and its
   board has no stage overflow, so Region is armed there at load too — the cell's press-on/press-off
   pair becomes press-off/press-on, and **nothing was added to the `editing` contract for it**: the
   rule is about the view, not the page, and that contract's own count is still six reads) and
   `SCOPE+ tests/test_puzzle_solver_crosshair.py` (its touch-drag cell armed Region by hand on a
   board in view; measured, the press turned it off and the browser's pan recognition then cancelled
   the drag after three cells, so the crosshair stopped with it).
7. `SCOPE+ tests/test_player_base_css.py` — **the FROZEN census moves, and it would have moved under
   any predicate that does what the owner asked.** Its page is the sweep board (a 10 x 8, no stage
   overflow at either width), so the Region toggle's RESTING state on that page is now its pressed
   state: three fields of one row at each width — `09 button puzzle-player-region`'s `color`,
   `background-color` and `border-top-color`, the three declarations of
   `.player-region[aria-pressed="true"]`. Edited by their indexes in `PROPS` (field [23], [24],
   [25], derived with `PROPS.index`), the row's rectangle untouched, `recorded` NOT moved — nothing
   in `base.css` or `admin.css` changed and the committed bytes were not re-measured against the
   real Bootstrap, so this is a state change in our own page and not a measurement of theirs. The
   module's run named exactly those three differences at 390 and exactly those three at 1280 and no
   other before the edit, none after it, and `test_a_changed_stylesheet_reds_the_fidelity_check`
   still reds on both of its plants. Written up in `PROVENANCE`'s own record, in the form CARD-424
   and CARD-426 set.
### Figures
* **Net test count: 0 added, 0 removed, 0 renamed.** Derived, not asserted: `--collect-only` over
  the eight changed test files gives 418 node ids and `diff` against the same collection on `main`
  is empty. So `tests/test_browser_fixture_scope.py`'s node-id census has nothing to register and
  no `ADDED_SINCE_BEFORE` entry was added.
* **Test functions touched: 26**, in 8 files, counted from the diff rather than estimated —
  `tests/test_puzzle_solver_brush_menu.py` 20 (19 of them a one-token board move, `GRID` ->
  `SCROLLING_GRID`, with every assertion verbatim; the 20th is AC-2/AC-4's rewrite),
  `tests/test_puzzle_solver_marking.py` 1 (AC-1), `tests/test_puzzle_solver_zoom.py` 2 (a press
  dropped, a press moved after its zoom), `tests/test_puzzle_solver_crosshair.py` 1 (a press
  dropped), `tests/test_puzzle_solver_maybe.py` 1 helper serving 2 cells (the settle wait),
  `tests/test_player_public_mode.py` 1 (the sweep's `step_region`) and
  `tests/test_puzzle_editor_ui.py` 1. `tests/test_player_base_css.py` is not a cell change at all:
  three fields of two rows of a frozen table, plus its own record.
* **Impact set, re-derived from the final diff** (`scripts/impact_set.py --gate --against main`):
  SELECTION, **140 test files, 7654 of 10650 tests, 7648 at this gate**; 3 marked files lifted by the
  subject edge (`tests/property/test_book_pairing.py`, `tests/test_book_export_interior_cover.py`,
  `tests/test_browser_fixture_scope.py`), 6 marked tests owed at the wave close.
* **Self-verification** (the player family of that selection — the part of it this card can move;
  the owner's 2026-11-09 ruling on player gates): three runs, 223 then 1033 then 186 tests. Run 1
  ended 220/223 with three `Page.goto` 30 s timeouts, each green alone. Run 2 ended 1025/1029 with
  the four reds this card then fixed — the two `test_player_base_css.py` widths, the editor's Region
  cell and the crosshair's touch drag — plus nothing else. Run 3 re-ran every file changed after run
  2 began (`brush_menu`, `editor_ui`, `crosshair`) and the three fixed cells directly: **186 passed,
  0 failed**, and `test_player_base_css.py` whole is green. What run 2 did not see of the committed
  tree, named rather than waved at: the four cells run 3 re-ran, and two COMMENT-ONLY edits to
  `solver.js` (`setRegion`'s note, which this card had made false, and one measured figure) made
  while it was running — no executable line of the diff is unrun. One lesson for the next card: the
  goto timeouts were my own concurrent pytest processes, not the diff — do not run two of them.
- **[AC-5 completed by the orchestrator]** The round recorded a `[BLOCKER] decomposition defect` for the one half of AC-5 it was forbidden to touch: `solver_state.js`'s `nextRegion` note still stated the rule the owner reversed, and the brief had told it not to edit that file because CARD-434 was expected to hold it. **CARD-434 has not started and has no worktree**, so the edit was safe — and it belongs in this BRANCH, not on main: the new text describes behaviour that exists only once this card merges, so on main it would itself be a false comment. The orchestrator wrote it on main first, noticed exactly that, reverted, and applied it here (`08b48ac6`, rebased to `5d45f075`). The paragraph now records two owner rulings in sequence, quotes the sentence it replaces with the dates it was true between, and states that `nextRegion` itself is unchanged — the arming lives in `solver.js`'s `pick()`, where the fit predicate can be read.
- **[Scope, and a misreading by the orchestrator worth recording]** `git diff main` showed TEN changed test files against the eight the round declared, and the two extras were nearly reported as an undeclared scope breach. They are **CARD-443's**, which landed on main after this branch was cut; the branch's own commit touches **9 files exactly as declared** (`git show --stat` on the implementation commit, which is the right instrument — a diff against a moving main is not). Same class of error as the `meta/` confusion on CARD-437 earlier in the session: reading another session's commits as this branch's work.
- **[Net test count, verified independently]** 0 added, 0 removed. Collected the ten changed test files on the branch and on main: **471 both sides**. The round's own figure (418 over 8 files) was taken over a different file set and agrees in the only way that matters — branch equals main.
- **[Review 1/3 dispatch]** Reviewer out on the rebased branch (cycle 1, min_score 8, severity gate on, class heavy). Six things named for scepticism rather than reading: the predicate and whether `boardFits()` is re-evaluated at the right moments; **the rule the round added that the owner never gave** (a board that stops being wholly in view disarms Region) and whether it can fire at a moment that surprises the reader; the card's own off-latch and when it clears; whether the 19 cells moved onto a scrolling board still test what their names say, since moving a board can quietly change what a cell asserts; the FROZEN re-record's reasoning and its plant; and the round's claim that AC-1's named test could not carry AC-1 because its drags are mouse drags. It was also told that `git diff` against a moving main shows other sessions' commits as this branch's work — the trap the orchestrator fell into twice today — and to use `git show --stat` when it needs to know what this card changed.
- [Review 1/3] Score: 6.0 — gated. 1 Critical, 2 Important, 5 Minor. Risk judged on a diff of 9 files; `task_contract_verdict: pass`, `system_contract_verdict: FAIL` (1 ✗ violated, ADR-0039/R4). Report `meta/review/20261113T185500Z-CARD-433-cycle1.yml`. Everything the brief named was re-derived rather than read: **the 1280x720 figure the whole fix rests on is CONFIRMED** (a 30x30 reads "100%" on a desktop with 133 px of board the reader cannot see), so predicate A is wrong off-phone too and a compact media query would indeed split identical boards at 600/601 px; `boardFits()` reads the right element; the 19 `GRID` → `SCROLLING_GRID` moves were read one by one, assertions verbatim, with one cell (`TestSolverRegion_UnarmedTouchDragStillScrolls`) actually **strengthened** by the move; the FROZEN re-record's `PROPS` indexes were recomputed mechanically and the plant still reds; the line view was verified by reading to consult Region nowhere; and the net count was independently collected at **418 node ids on branch and main with an empty diff**.
- **[Severity gate] BLOCKED on F-001 (Critical), and it is a defect in a rule nobody asked for.** A resize while the board sits at Fit **disarms Region although the board never leaves view** — measured repro at 390x844 → 390x700 (overflow stays `[0,0]`, readout stays "Fit", `aria-pressed` flips to `false`, announce says "Region off"), and reproduced at 360x760 while a *growing* resize does not fire it. Mechanism traced and confirmed statically here: `fitTheFloor` applies a recomputed floor **before** its overshoot loop corrects it, `setFloor` calls `applyZoom` because the board was at Fit, and `applyZoom` calls `syncRegionToFit` **unconditionally** (solver.js:2461) — so the predicate is read on an intermediate layout that exists for one task, sees 7 px of transient overflow against a 269 px client height, and disarms. It defeats the card's rule 1 on the commonest phone paths (URL-bar collapse, rotation, a toolbar re-wrap) and falsifies `syncRegionToFit`'s own comment, "The TRANSITION, not the state". Nothing in the suite resizes a board at Fit with Region armed, which is why it shipped. **The rule it breaks is the one the implementation round ADDED and the owner never gave** — sound in intent, wrong in timing, and the fix brief forbids deleting the rule to make the finding disappear.
- **[F-002 is the orchestrator's error, not the implementation round's.]** `solver.js:285-288` states that `nextRegion`'s note "still states the 2026-10-14 rule and is stale; CARD-433 could not correct it". That was true when the round wrote it and became false when **I** wrote `5d45f075` on this branch correcting the note — and did not repoint the sentence that referred to it. So the diff's hotspot file carries a false cross-file claim in its canonical header, introduced by the station that is supposed to catch exactly that. Confirmed by reading the lines before dispatching the fix.
- **[F-003] A figure of this card's own is refuted.** The measurement table says a 20x20 at 390x844 overflows `96 x 0`; the reviewer recomputed it on the suite's only 20x20 **and** an independently seeded one, both giving **113 x 0**, and the figure names no particular board while stage overflow depends on the grid's deepest column clue. The conclusion is untouched (113 > 0 diverges exactly as 96 would) — the number is wrong, and under ADR-0039/R4 a figure without an instrument is the finding.
- **[Review sync] ⚠ the report was REFUSED by the parser, and was NOT repaired here.** `parse_review.py` returns `security-malformed`: the `security:` value is a YAML block scalar (`>-`), so the parser reads the literal `>-` instead of the reviewer's text, which is otherwise correct. **The orchestrator does not edit review reports** — it copies and reads them, and a report rewritten by the station it judges is not evidence — so it was bounced back to its author with the parser's exact output and the required scalar form. The card cannot close until `parse_review.py` accepts it.
- **[Fix 1/3] F-001 fixed — `syncRegionToFit` now answers only to a SETTLED reading, and the rule stays.** The rule the round added (a board that stops being wholly in view disarms Region) is NOT removed: removing it reintroduces the flow it exists for. What changed is *when* the predicate is read. `applyZoom`'s `syncRegionToFit()` is now guarded by `!player.measuringFit()` — the same `measuringFit` flag `player.zoomed()` already reads, published as a one-line getter on the `player` object `wireMarking` is handed, so the guard sits at the CALL (as `zoomed`'s does) rather than inside the function, which is what keeps `fitTheFloor`'s own trailing call — the settled one — working. A zoom ABOVE 100% is not a measurement at all (`zoomed()` skips `measureFit` there, CARD-271 cycle 2 F-103), so the direct call the reviewer flagged as load-bearing still fires there; at or below 100% the measurement has already run by the time `applyZoom` asks, so that call re-reads the same settled layout and finds nothing to do.
- **[Fix 1/3] The covering cell, watched red first.** `tests/test_puzzle_solver_zoom.py::TestSolverZoom_Fit::test_a_resize_at_fit_leaves_region_armed_while_the_board_stays_in_view` — `SCROLLING_GRID` at 390×844 opened with `keep_opening_zoom=True` (so it sits at Fit), then the viewport shrunk to 390×700. Run against the UNFIXED code it failed exactly as the review measured: overflow `[0, 0]` and readout `"Fit"` on both sides, `aria-pressed` `'false'` and the live region reading `"Region off."`. After the fix it passes, and that red IS the plant recorded in its docstring. **Net test count: +1 added, 0 removed** (the card predicted exactly this: "If the fit predicate needs a cell of its own, that is one added").
- **[Fix 1/3] The census red was expected and registered, not dodged.** The new node id reddened `tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured` ("recorded nowhere"). It is now an `ADDED_SINCE_BEFORE` entry attributed to CARD-433 with its reason; nothing was renamed to avoid the guard. `SCOPE+ tests/test_browser_fixture_scope.py — the family's node-id census refuses an unrecorded addition; registering the new cell is the required way through it.`
- **[Fix 1/3] F-002 fixed, and its siblings checked rather than assumed.** `solver.js`'s header now says what is true: `nextRegion`'s note in `solver_state.js` records BOTH rulings in sequence, quoting the sentence it replaces with the dates it was true between, and `nextRegion` itself is unchanged and still refuses a `"brush"` event because the arming lives in `pick()`. Every other cross-file claim in the same block was re-read against this branch's HEAD, since all of them were written under the assumption that `solver_state.js` would not be touched: (a) *"'brush' is still not one of nextRegion's events"* — **holds**, `REGION_EVENTS` is `["toggle", "drag"]` at solver_state.js:1267 and the rewritten note says so itself; (b) *"the button's name comes from an aria-label the template carries"*, with an aria-hidden swatch run — **holds**, `puzzle_solve.html`'s `#puzzle-player-region` carries `aria-label="Region"` and two `aria-hidden` swatches; (c) *".is-region is how admin.css drops .player-cell's touch-action to none"* — **holds**, `admin.css:774`. Two claims in the block were corrected because this card's own change made them imprecise, both inside the block the finding names: *"the flag's own transition table is nextRegion"* now names the two events that table covers and points at `setRegion` for the three view-driven writes, and *"the toggle is the only thing that sets that class"* (false since the flag also moves at load, on a brush pick and on a board leaving view) now says the class is written only by `refresh()`, from the flag.
- **[Fix 1/3] F-003 retracted and re-measured, with the board named.** The A-vs-B table above now names a board and a seed in every row and states its instrument (`_overflow` + `_open` at the column's viewport), and carries the retraction of `96 × 0` in full. All five rows were re-derived a third time on this host on 2026-11-13: `seed=301` and `seed=4332` both give **113 × 0** at 390×844 (and `0 × 0` at 1280×720), and the four unrefuted rows came back unchanged. The reason a bare size is not a figure is now measured rather than argued: a *different* 30×30, `_unique_grid(30, 30, seed=40601)`, gives **346 × 185** / **0 × 148** where the suite's `GRID_30x30` (`seed=19330`) gives **346 × 170** / **0 × 133**. `boardFits`'s own note in `solver.js` now carries those seeds and, for each figure, the cell a later reader can run.
- **[Fix 1/3] The six Minors were read and deliberately left.** F-004 (a zoom-driven disarm writes the shared live region), F-005 (the 300 ms sleep in `_glyph_box`), F-006 (AC-1's cell marks two lines under a one-line name), F-007 and F-008 (owner questions: does entering Fit re-arm, and does edit mode share the default) are untouched this round — they are not gating and the brief holds the diff to the three. Note for whoever takes F-004: this fix removes most of the occasions it fires on, exactly as the reviewer predicted.
- **[Fix 1] verified by the orchestrator with its own plant.** Removed the `!player.measuringFit()` guard at `applyZoom`'s call site (solver.js:2493) and ran the new cell: **FAILED**. Restored and re-ran: **passed**, with `git diff` on `solver.js` empty afterwards. So the Critical's fix is real and its cell discriminates — this was run here rather than read off the round's report, because "red before, green after" is the one claim a fix round cannot be taken on trust about.
- **[Fix 1] the rule was kept, not deleted.** The brief forbade making F-001 disappear by removing the rule the round had added beyond the owner's words, because removing it reintroduces what it was added for (a big board opens at Fit armed, the reader taps `+`, and the drag they make to pan paints). The fix changes only **when the predicate is read**: the same `measuringFit` flag `zoomed()` already consults now gates the call, so `fitTheFloor`'s settled trailing reading still syncs and a zoom **above** 100% — where `zoomed()` deliberately skips `measureFit` (CARD-271 cycle 2, F-103) — still fires.
- **[Fix 1] one flag acquired a second job, and the round said so rather than hiding it.** `measuringFit` now gates both whether `zoomed()` re-measures and whether `applyZoom` syncs Region. The round's argument for publishing it rather than duplicating it is that both want the same magnitude — the duration of one fit measurement — so there is no value conflict. **That is a judgement, and it is exactly the kind cycle 2 should examine**, because a shared flag with two consumers is how a later card acquires a bug that neither consumer's tests can see.
- **[Fix 1] the census red happened and was REGISTERED, not dodged.** The new node id reddened `test_browser_fixture_scope.py`'s CARD-217 family census ("collected in the browser family but recorded nowhere"); it is now an `ADDED_SINCE_BEFORE` entry attributed to CARD-433 with its reason, and nothing was renamed. **Net test count is +1 added, 0 removed** — the card budgeted exactly this ("If the fit predicate needs a cell of its own, that is one added, and the number is reported at the gate"), so the promise holds and the figure is stated rather than buried.
- **[Fix 1] F-003 was re-measured, not merely retracted,** and the re-measurement produced the better argument: a *different* 30x30 (`seed=40601`) gives `346 x 185` / `0 x 148` where the suite's `GRID_30x30` (`seed=19330`) gives `346 x 170` / `0 x 133`. So the reason a figure must name its board is now itself measured. Every row of the A-vs-B table now names a board and a seed and states its instrument, and the `96 x 0` retraction is written out in full on the card because a commit message cannot be edited.
- **[Deviation, recorded]** The fix round edited **main's** copy of this card rather than the worktree's, contrary to the two-copies rule, on the ground that the measurement table it had to correct exists only on main. It flagged a concurrent write mid-edit and re-read the file afterwards. Checked here: 308 lines, all six `[Fix 1/3]` notes present, no header field touched. The deviation is noted rather than undone — the alternative was a correction landing in the copy that gets discarded.
- [Review 2/3] Score: 9.0 — passed. **0 Critical, 0 Important**; the severity gate that blocked cycle 1 is clear. `task_contract_verdict: pass`, `system_contract_verdict: pass` — **ADR-0039/R4 moves from ✗ to ✓**, so the contract failure cycle 1 recorded is closed. Report `meta/review/20261113T190718Z-CARD-433-cycle2.yml`; both cycles' reports are synced to main and both `parse_review.py` as `accepted`.
- **[Review 2/3] the shared-flag question was answered structurally, which is better than answered empirically.** The brief asked whether `measuringFit`'s two consumers can ever want different values. They cannot, and the reason is not a measurement that might not generalise: the flag is set only inside `measureFit`, around a **wholly synchronous** `fitTheFloor`, and restored in a `finally`; `wireMarking` has exactly one call site, so there is only ever one `player` object; and single-threaded JS means a pinch, an orientation change, a debounced resize, two resizes in one frame and a board swap **cannot interleave** with the measurement. The mirror question also came back clean — the only skips are `fitTheFloor`'s two early returns, both of which happen *before* the first `setFloor`, so nothing was suppressed that needed recovering.
- **[Review 2/3] mutation check RUN (the deferral from cycle 1 lifted), 3 mutants, all killed.** Deleting `syncRegionToFit`'s disarm: killed. Deleting `fitTheFloor`'s **trailing** `syncRegionToFit()` — the call this fix's whole argument rests on: killed. Removing the census entry: killed. **A finding inside the finding, recorded because it is the useful one:** the first two mutants are killed by *one and the same cell*, `TestSolverZoom_OneFingerDragIsUnchangedByZoom::test_a_region_touch_drag_at_200_percent_marks_exactly_five_cells`. Rule 3's entire coverage is that single cell. Left as an observation rather than a finding, because adding a second would fight the owner's test budget — but a later card that touches rule 3 should know its safety net is one thread.
- **[Review 2/3] honest about what it could NOT check.** F-002's closure has no runnable mutant, because **no cell in this project reads `solver.js` or `solver_state.js` as source text** — comment truth in those two files is unguarded by construction. The reviewer verified it by reading, claim by claim, and said so instead of implying a test covered it. That is a standing property of the project, not a defect of this card, and worth knowing: every comment correction this card made (and there were several) rests on review discipline alone.
- **[F-009 fixed before merge, by the orchestrator]** Cycle 2's new Minor: `setRegion`'s note said "the **three** callers that pass a value straight in — pick, syncRegionToFit and settleRegion's write below" and, four lines later, "the one caller that does **not** come through here is settleRegion". Both cannot be true. Resolved by reading **every** `setRegion` call site rather than picking a side: there are four callers — `pick` and `syncRegionToFit` pass a value straight in, the toggle and the recorded drag pass `nextRegion`'s answer — and `settleRegion` calls it not at all, assigning `region` and `aria-pressed` itself so a board restored already-armed announces nothing. The paragraph now says that, and carries the contradiction it replaced so the next reader does not re-derive it. Fixed here rather than in a third round because it is one paragraph of prose whose falsity was already established — **and because AC-5 of this very card is that no comment still states the superseded rule**; shipping a card about comment truth with a self-contradicting comment in its hotspot file would be the joke writing itself.
- **[Carried figures corrected]** Two of this card's own notes were wrong and are fixed above: cycle 1 produced **5** Minors, not the 6 the orchestrator wrote (the YAML's `minor_triage.total` is 5), and the system-contract set is **57** rules on this host, not cycle 1's 52 — cycle 2 re-assembled it rather than carrying the number, and verdicted the five extra ids rather than dropping them.
- **[Note-sync correction]** The pre-merge sync check caught one worktree note line absent from main and it was carried in — which **re-introduced a stale figure**: the line was the uncorrected `[Review 1/3]` note saying *6 Minor*, the very figure cycle 2 refuted and the orchestrator had already fixed to **5** in main's copy. The duplicate has been removed and the corrected line kept. Recorded because the diff-based note sync is **line-identity based**: a line that main has *deliberately edited* reads as a line main is *missing*, so the sync wants to restore it. That is the second failure mode of this helper in the session (the first was matching only `###` headings and silently syncing nothing).
- **[Merge gate]** Impact-scoped, derived on the rebased branch (`head=b051d29e`): **143 files** in the full selection, **33 of them run** — the player subset, per the owner's ruling of 2026-11-09 that player cards gate on the player test set rather than on everything `solver.js` reaches. **2165 passed, 0 failed, 0 skipped** in 23:12, plus the three lifted `wave_close_only` files, **7 passed**. Stated so it cannot be read as broader than it is: **the full 143-file selection was NOT run at this gate, and the wave close owes it.**
- **[AC/EC check]** By node id, skips counted: `tests/test_puzzle_solver_brush_menu.py` (AC-2, AC-4), `TestSolverMarking_DragMarksOneLine` (AC-1's real home, since the card's named cell drives MOUSE drags and could not carry it), `TestSolverZoom_Fit` (the Critical's cell) and `TestSolverMaybe_DragPaintsMaybe` (the cell the card named). **68 passed, 0 skipped.**
- **[Merged]** `23ad1e3c`, `--no-ff`, four commits replayed. Both review reports and every note line were confirmed in main **before** the worktree was removed — by a check that **exits non-zero**, not one that prints a warning a following `&&` can walk past. That distinction is this session's own scar: the CARD-432 close printed `MISSING/DIFFERENT` and removed the worktree anyway.
