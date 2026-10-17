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
**still owed at the architect station**. The registry delta of 2026-10-17 (commit `91609aa`)
did **not** touch FR-033 — it carried CON-018, NFR-008, FR-030, FR-031, FR-032, FR-043 and
INV-013 only, and this card's amendment was explicitly out of its scope. Do not read that
delta as having settled the rule weights. Read FR-033 before implementing and say in the notes
whether the shipped behaviour already has one of these weights.

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
  floor, **4.75 mm** since the 2026-10-17 amendment), *then* the three weights are still
  distinguishable — each is at least one
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

_Assembled 2026-10-17 by `system_rules.py --card CARD-227 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **FR-033 — STILL OWED, and explicitly out of scope of the 2026-10-17 delta.** That pass
  carried CON-018, NFR-008, FR-030, FR-031, FR-032, FR-043 and INV-013 — **not** FR-033. Its
  "dark lines (threshold unstated — open question)" is therefore still open, this card is still
  the answer to it, and its three figures (0.3 pt cell lines in grey, 0.8 pt every fifth line,
  1.3 pt outer border) **still need FR-033 acceptance criteria written at the architect
  station**. Do not read the 2026-10-17 amendments as having settled this one: nothing about
  rule weights was decided that day. Read FR-033 before implementing and say in the notes
  whether the shipped behaviour already has one of these weights.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

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
