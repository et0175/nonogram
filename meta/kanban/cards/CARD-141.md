# CARD-141: Answer-page rows take the height they need, so the spare white falls at the page foot

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/141-answer-rows-pack-to-top
**Worktree:** —
**Source:** owner, 2026-09-23 ("I'd rather have this white band on the bottom"), ruling on CARD-133's open question
**Idea:** —
**Wave:** 26
**Depends on:** CARD-134
**Touches:** src/nonogram/export/layout.py, tests/test_answer_page_layout.py, tests/property/test_answer_page_layout.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`compute_answer_page_layout` divides the usable area into `capacity` equal tiles and draws
each answer at the top of its own tile, hanging from its caption. Every answer on a page
shares one cell size, so a 10x10 grid is physically shorter than a 20x20 at the same cell —
and a row of small answers leaves slack under it. On a mixed 4-up page that slack is a deep
white band across the middle of the page, and the page reads as two unrelated rows instead
of one block (`~/Documents/nonogram-reviews/CARD-134/03-mixed-1.png`).

The owner ruled on 2026-09-23: **the spare white belongs at the foot of the page**, not
between the rows. Vertical centring inside each tile was the alternative and was rejected —
it spreads the slack around every grid rather than gathering it.

1. **Each row takes the height its content needs**: the caption band plus the tallest grid
   in that row at the page's cell size, plus `ANSWER_TILE_GAP_MM` between rows. Rows are
   laid from the top of the usable area (under the heading, where there is one) and the
   leftover height accumulates at the bottom of the page.
2. **The cell size does not change.** Compute it exactly as today, from the equal-tile
   worst case, and only then lay the rows out at their content height. This is what keeps
   the computation non-circular and every pinned figure intact: 3.97 mm for a 20x20 six-up,
   3.87 mm under a heading, 3.19 mm for a 30x30 four-up, the 5.0 mm cap and the 10x10 at
   5.0 mm (AC-262, AC-265, AC-294, AC-295) all still hold. If any of those numbers moves,
   the implementation has gone wrong.
3. **Horizontal geometry is untouched.** Two columns, the same column width and gap, each
   answer still centred horizontally in its column as it is today.
4. **The page still reads as a regular grid.** One cell size for every answer on the page
   stays the rule (the docstring's "a 10x10 next to a 20x20 does not pull the page out of
   true"); what changes is only where a row's unused height goes. Update that docstring so
   it describes the vertical rule it now implements.

Out of scope: the caption's own position within a row, the heading, the packing walk that
decides which answers land on which page (CARD-134's, and unchanged by this), and any
change to `capacity` or the 6-up/4-up rule.

## Acceptance criteria

- New: on a mixed page whose top row is short, the gap between the two rows is
  `ANSWER_TILE_GAP_MM` and the remaining height is below the bottom row.
  test: TestAnswerLayout_SpareHeightFallsAtThePageFoot
- New: the cell size for every pinned case is unchanged from before this card.
  test: TestAnswerLayout_CellSizesAreUnchangedByRowPacking
- New: a page whose answers are all the same size looks exactly as it does today, apart
  from the foot.
  test: TestAnswerLayout_UniformPageIsUnchangedAboveTheFoot
- New: no row ever overlaps the next, and no answer leaves the usable area, for any mix.
  test: PropertyTest_AnswerLayout_RowsNeverOverlapNorOverflow

## Guardrails

- G-1: One cell size per page (ADR-0036/R2). This card changes vertical placement only —
  it must not make a grid's cell depend on its own extent.
- G-2: The pinned millimetre figures (AC-262, AC-265, AC-294, AC-295) are unchanged. Their
  tests stay green and are not edited to accommodate this card.
- G-3: CLI and web A4 output stay byte-identical (CON-019). `compute_answer_page_layout`
  has no CLI or web caller, so the golden tripwire must not move at all.
- G-4: Do not edit `src/nonogram/admin/**` — the panel decides no geometry.

## Architecture context

- **FR:** FR-042 (the answer key)
- **ADR:** ADR-0036/R2 (geometry lives in COMP-007)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner ruling, 2026-09-23, closing CARD-133's open question with the CARD-134
  renders as evidence. Note this is the OPPOSITE of the two-up ruling the same day, and
  deliberately so: on a two-up puzzle page the slack stays BETWEEN the two puzzles (the
  upper slot's top edge must align with a facing single page), while on an answer page the
  slack goes to the FOOT. The two pages are read differently — a puzzle page is worked one
  puzzle at a time, an answer page is scanned as a block.
- [Depends on CARD-134] Waits for it because CARD-134 is the card that renders and captions
  these pages; starting both against the same geometry would collide.
