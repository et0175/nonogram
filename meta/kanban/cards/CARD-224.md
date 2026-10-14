# CARD-224: The grid goes back to centred, sitting at 42% of the puzzle area's spare height

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/224-grid-centred-again
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 2 ("Grids are pushed to one edge and pinned to the top. On most pages the lower third of the page is empty (pp. 28, 75, 125), so the page looks unbalanced") and "Puzzle area" + the artifact's own note on reversing CARD-204
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the area), CARD-223 (the QR must be out of the gutter strip before the strip stops existing)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/book_baseline_card224.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Read this first: this card deliberately reverses the central decision of CARD-204, which
merged on 2026-10-14 after 12.2 days and 8 fix cycles.** The owner knows, and says so in the
artifact: *"This reverses the flush-right and flush-left placement from CARD-204 back to
centring. That alignment was what freed the gutter-side strip for the QR. Once the QR has its
own footer, centring is the calmer choice."* Treat CARD-204 as a decision the product has
outgrown, not as work to be undone carelessly: it also delivered the QR slot, the two-up
folio reserve and `export.layout.caption_slot`, **and all three of those stay**.

**Current behaviour (verified by reading the code).**

- A puzzle page's drawing sits **flush to the page's outer edge, mirrored by parity** (right
  on right-hand pages, left on left-hand ones) — CARD-204's implementation of FR-032 as
  amended, replacing FR-032's original "centred" statement.
- The drawing is **pinned to the top** of its area under the band (FR-032's "fixed top edge"),
  which is what leaves the lower third of a page empty on pp. 28, 75 and 125.

**What changes.**

1. The grid is **centred horizontally** in the puzzle area again. Parity stops moving it.
2. Vertically it sits at **42% of the spare height** — the artifact's figure, with the
   artifact's reason: *"which looks centred once the header sits above it."* So 42% is an
   optical decision, not an arithmetic one. Declare it once, named, with that sentence as its
   docstring, and do not silently "improve" it to 50%.
3. The spare height is measured against CARD-222's puzzle area (header rule to footer rule),
   so the grid can never land on either rule.
4. Keep what CARD-204 built that this does not contradict: `caption_slot` (it bounded a real
   defect — a 65-character picture name putting ink 9.6 mm outside the page), the two-up folio
   reservation, and the QR (now in the footer, CARD-223).

**One trap, named because this family has already produced five regressions.** CARD-204's own
retro lesson is in `backlog.md`: `_draw_solved_slot`'s return value has **two** consumers,
`solved_puzzle_page` and `_packed_answer_page`, which must change together, and nothing in the
code enforces it. The same asymmetry produced a gating defect in CARD-203 cycle 1, CARD-203
cycle 2, CARD-204 Fix 7 and CARD-204 cycle 5. If this card changes anything a slot returns,
change both consumers in the same commit and say so.

## Acceptance criteria

- **AC-1** (happy, centred): *Given* a left-hand page and a right-hand page holding the same
  puzzle, *when* both are drawn, *then* the drawing's left and right margins within the puzzle
  area are equal to within a pixel, and the two pages place it identically — parity no longer
  moves it. (test: `TestBookPuzzleFrame_GridIsCentredOnBothParities`)
- **AC-2** (happy, the 42%): *Given* a puzzle area with spare height `s`, *when* the grid is
  placed, *then* the gap above it is `0.42 * s` and the gap below `0.58 * s`, measured off the
  drawn ink. (test: `TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare`)
- **AC-3** (guard, never on a rule): *Given* every grid size the book admits and every trim,
  *when* a page is drawn, *then* no grid or clue ink touches the header rule or the footer
  rule. (test: `TestBookPuzzleFrame_GridClearsBothRules`)
- **AC-4** (edge, the tallest grid): *Given* the tallest grid that fits at all, *then* the
  42% rule degrades to "as low as it fits" rather than pushing ink past the footer rule, and
  the page says which rule bound it. (test: `TestBookPuzzleFrame_TallestGridYieldsToTheFooter`)
- **AC-5** (guard, CARD-204's survivors): *Given* a 65-character picture name, *when* the
  answer page is drawn, *then* `caption_slot` still bounds it inside the usable area — the
  defect CARD-204 Fix 7 and Fix 8 closed does not come back with centring.
  (test: the existing caption-slot classes in `tests/test_book_solved_page.py`)
- **AC-6** (happy, the lower third): *Given* the corpus pages the owner named (28, 75, 125),
  *when* they are drawn, *then* the empty band below the grid is no larger than the band above
  it — the measured form of "the page looks unbalanced".
  (test: `TestBookPuzzleFrame_NoEmptyLowerThird`)

## Guardrails

- G-1: FR-040's pairing behaviour is unchanged — this card moves a grid inside its slot, it
  does not change which puzzles share a page (test: the existing pairing tests).
- G-2: The two-up folio reservation CARD-204 added still holds: every two-up page keeps its
  folio (test: `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-3: `caption_slot` is not removed or widened.
- G-4: Out of scope — the cell size (CARD-225), the slot split (CARD-226), the header's
  content (CARD-207).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- **FR-032** — portrait only, fixed top edge, wide-grid flag. **Two amendments owed at the
  architect station, and they pull in opposite directions:** its original "centred" statement
  becomes *correct again* (so the delta CARD-204 logged against it is cancelled, not applied),
  while its **"fixed top edge" clause is what this card actually breaks** — the grid now
  floats at 42% of the spare height. Say exactly this in the notes so the architect pass does
  not mechanically apply CARD-204's pending amendment.
- CON-020 (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0036/R2 — placement comes from COMP-007's layout functions (check: review-lens)
- ADR-0037/R1 — a puzzle page's band carries number + tier only (check: review-lens)
- INV-013 (check: `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)

## Architecture context

- **FR:** FR-032 (both clauses above), FR-040 (pairing, unchanged).
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2, ADR-0037/R1.
- **Components:** COMP-009, COMP-007.
- **Trace:** not updated by this card.

## Worktree notes

- [On reversing 12 days of work] CARD-204 cost 12.2d against a 2.5d estimate and found three
  real print defects on the way (a caption 9.6 mm outside the page, a caption overprinting a
  folio, two-up pages losing their folios). Those findings are *why* this reversal is cheap:
  the tests they left behind are the ones that will catch this card if it gets the geometry
  wrong. Reverting the placement is not reverting the card.
