# CARD-227: The printed grid's rules get three weights — cell, every fifth, outer border

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/227-grid-rule-weights
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "The rules behind it": Grid lines ("0.3 pt cells in grey, 0.8 pt every fifth line, 1.3 pt outer border")
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the frame these rules are measured inside)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/fixtures/book_baseline_card227.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The printed grid gets the same three-weight hierarchy the player's board has, stated in points
so it is resolution-independent:

- **0.3 pt** for ordinary cell lines, in grey (not black).
- **0.8 pt** for every fifth line, both axes.
- **1.3 pt** for the outer border.

**What to check before writing anything.** FR-033 already says "bolder 5th lines, dark lines
(threshold unstated — open question)" — the threshold was left open in the architecture and
this card is the answer to it. So this is not a new rule but the **closing of a stated open
question**, which means the figures belong in FR-033's acceptance criteria and an amendment is
owed at the architect station. Read FR-033 before implementing and say in the notes whether
the shipped behaviour already has one of these weights.

**One figure the artifact gives that belongs to another card:** "Clue areas shaded 5% grey,
with each number in its own box (CARD-208)" — the shading and the boxes are CARD-208's, which
has been amended to carry them. This card owns the three line weights only.

## Acceptance criteria

- **AC-1** (happy, three weights): *Given* a drawn grid, *when* its rules are measured off the
  ink, *then* ordinary cell lines are 0.3 pt, every fifth line is 0.8 pt and the outer border
  is 1.3 pt, at the page's own resolution. (test: `TestBookGridRules_HasThreeWeights`)
- **AC-2** (happy, grey cells): *Given* a drawn grid, *then* the cell lines are grey and the
  fifth lines and border are darker — asserted as an ink-value ordering, not as one literal
  colour. (test: `TestBookGridRules_CellLinesAreLighterThanTheFifths`)
- **AC-3** (happy, both axes): *Given* a non-square grid, *then* the every-fifth rule applies
  on rows and columns independently and counts from the border on each.
  (test: `TestBookGridRules_FifthLinesOnBothAxes`)
- **AC-4** (edge, a grid whose side is not a multiple of five): *Given* a 22x13 grid, *then*
  the last band is short and the border is still 1.3 pt — no half-weight line at the edge.
  (test: `TestBookGridRules_RaggedLastBand`)
- **AC-5** (edge, the smallest cell): *Given* the smallest cell the book admits (NFR-008's
  4.8 mm floor), *then* the three weights are still distinguishable — each is at least one
  pixel and no two round to the same width. (test: `TestBookGridRules_WeightsSurviveTheFloor`)
- **AC-6** (guard, resolution independence): *Given* two resolutions, *then* each weight
  scales with the page's dpi and the ordering holds at both.
  (test: `TestBookGridRules_PointsNotPixels`)

## Guardrails

- G-1: The answer pages' grids follow the same weights — the artifact wants the solutions to
  look like the puzzles (test: the answer-page frame tests).
- G-2: No new text-layout or drawing primitive: the weights go through the existing stroke
  path (ADR-0036/R2).
- G-3: The cells' *geometry* does not change — this card changes stroke widths, not positions
  (test: a geometry test asserting cell boxes are unchanged against the previous baseline).
- G-4: Out of scope — the clue boxes and the 5% shading (CARD-208), the cell size (CARD-225).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- **FR-033** — titles only in the answer key, bolder 5th lines, **dark lines (threshold
  unstated — open question)**. This card closes that open question with the owner's three
  figures; the amendment and its ACs are owed at the architect station (check: review-lens)
- CON-020 — the clue digits' floor exemption (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0036/R2 (check: review-lens)

## Architecture context

- **FR:** FR-033 (the open threshold this card closes).
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Smallest card of the set, and the one most likely to be mis-measured] A 0.3 pt line at
  300 dpi is 1.25 px. Rounding decides whether two weights are distinguishable at all, which
  is why AC-5 and AC-6 exist: the figures are only meaningful if they survive the smallest
  cell and both resolutions.
