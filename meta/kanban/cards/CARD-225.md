# CARD-225: One cell size per grid size across the whole book, capped at 7.5 mm

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/225-one-cell-size-per-grid-size
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 4 ("Cell size jumps around. A 20x20 grid prints larger or smaller depending on its clue widths, so grids of the same size don't match across pages") and "The rules behind it": Cell size
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the usable area the sizes are fitted against changes with the margins)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_plan.py, tests/test_book_cell_size.py, tests/property/test_book_pdf_geometry.py, tests/test_book_interior_type_floor.py, tests/fixtures/book_baseline_card225.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code and `export/layout.py`'s own docstrings).**

- A book cell is fitted **per puzzle, on that puzzle's real clue depth**: `cell = min(7.5,
  usable_w / (width + row-clue depth), ...)` (`export/layout.py:1966`), inside NFR-008's
  4.8..7.5 mm band. So two 20x20 puzzles print at different sizes when their clue columns
  differ in width — exactly the owner's issue 4.
- A shared (two-up) page already reduces to a shared cell (`export/layout.py:1909`), but the
  shared figure is derived from the pair, not from the book.

**What changes.**

1. **One cell size per grid size, book-wide.** All 20x20 puzzles in a book print at the same
   cell; all 25x15 at theirs. The size for a grid size is the **smallest** size that every
   puzzle of that grid size in this book can take — i.e. fitted against the deepest clue
   stack among them, so no puzzle of that size overflows.
2. The flat **7.5 mm cap stands** (NFR-008's standard cell, and the owner restates it).
3. **Two puzzles sharing a page use the smaller of their two sizes** — the owner's rule,
   which is what makes their grids line up (and what CARD-226 then aligns the slots around).
4. NFR-008 says the cell is fitted "per puzzle on its real clue depth". This card replaces
   that with a per-grid-size, per-book rule, so an **NFR-008 amendment is owed at the
   architect station**; this card flags it and does not edit `meta/architecture/**`.
5. Record the cost honestly: a book-wide size is by construction **≤** the per-puzzle size, so
   some puzzles print smaller than they do today. Measure the corpus's distribution before and
   after and state the worst case, including whether anything lands on NFR-008's 4.8 mm floor
   (and therefore on FR-031's below-floor flag).

## Acceptance criteria

- **AC-1** (happy, one size per grid size): *Given* a book holding several 20x20 puzzles with
  different clue depths, *when* the interior is exported, *then* every one of them is drawn at
  the same cell size, measured off the ink. (test: `TestBookCellSize_SameGridSizeSameCell`)
- **AC-2** (happy, the deepest clue stack decides): *Given* that set, *then* the shared size
  equals the size the *deepest-clued* member would have taken alone — so nothing overflows
  and nothing is smaller than it needs to be. (test: `TestBookCellSize_FitsTheDeepestMember`)
- **AC-3** (happy, the cap): *Given* a book of small grids with shallow clues, *then* the cell
  is 7.5 mm and not larger. (test: `TestBookCellSize_HoldsTheSevenAndAHalfMillimetreCap`)
- **AC-4** (happy, a shared page): *Given* two puzzles of different grid sizes on one page,
  *then* both are drawn at the smaller of their two book sizes.
  (test: `TestBookCellSize_SharedPageTakesTheSmaller`)
- **AC-5** (edge, one puzzle of its size): *Given* a grid size with exactly one puzzle in the
  book, *then* the rule degenerates to today's per-puzzle fit for it.
  (test: `TestBookCellSize_SoleMemberOfItsSize`)
- **AC-6** (edge, the floor): *Given* a book whose deepest-clued 30x30 forces a cell below
  NFR-008's 4.8 mm floor, *then* the below-floor flag FR-031 already defines is raised for
  **every** puzzle of that grid size, not only the one that forced it — the flag must describe
  what is printed. (test: `TestBookCellSize_BelowFloorFlagFollowsTheSharedSize`)
- **AC-7** (guard, determinism): *Given* the same book, *when* the sizes are computed twice,
  *then* they are identical, and they do not depend on the order the puzzles were added.
  (test: `TestBookCellSize_IsOrderIndependent`)

## Guardrails

- G-1: NFR-008's 4.8..7.5 mm band is not widened — this card changes how the figure is
  *chosen*, not what is allowed (test: the existing NFR-008 tests).
- G-2: FR-031's below-floor flag and per-puzzle override keep working (test: the existing
  FR-031 tests).
- G-3: A puzzle's grid, clues, tier and strategies are never changed — ADR-0033/R1. This card
  changes a drawing size only (check: review-lens).
- G-4: Out of scope — where the grid sits (CARD-224), the slot split (CARD-226), clue boxes
  (CARD-208).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- **NFR-008** — book cell in [4.8, 7.5] mm per puzzle on its real clue depth; AC-236..AC-239.
  **Amendment owed:** the "per puzzle on its real clue depth" clause becomes "per grid size
  per book, fitted to the deepest-clued member" (check: review-lens)
- FR-031 — below-floor flag and per-puzzle override (check: the FR-031 tests)
- CON-020 — the clue digits are the one exemption from the 10 pt floor, and they shrink with
  the cell (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0033/R1 — book assembly never changes a puzzle's grid, clues, tier or strategies
  (check: review-lens)
- ADR-0036/R2 — geometry from COMP-007 (check: review-lens)

## Architecture context

- **FR:** FR-031 (the floor flag), FR-040 (pairing — a shared page's size rule).
- **NFR:** **NFR-008 (amendment owed)**.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0033/R1, ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Why this is P1 and architectural] It is the only card of the set that changes what the
  reader *solves* rather than where it sits: a smaller cell is a harder puzzle to mark by
  hand. NFR-008's band exists for that reason, and this card moves a figure inside it for
  every puzzle in the book at once.

## Measured at the decompose station, 2026-10-14 — the margins cost 4.9% of every cell

Run against the repo's own `_placed_cell_mm` with the shipped Book 1 spec and the artifact's
four margins, so this is a measurement and not an estimate. Usable width goes 193.68 -> 184.15 mm
(-4.9%); usable height 248.35 -> 237.19 mm. The fit is width-bound for every grid the book
admits, so **every cell that is not already at the 7.5 mm cap loses exactly 4.9%**:

| grid | clue depth | today | at the new margins |
|------|-----------|-------|--------------------|
| 15x15 | any | 7.50 (capped) | 7.50 (capped) |
| 20x20 | shallow | 7.50 (capped) | 7.50 (capped) |
| 20x20 | deep | 7.45 | 7.08 |
| 25x25 | deep | 5.87 | 5.58 |
| 30x30 | shallow | 5.53 | 5.26 |
| **30x30** | **deep** | **4.84** | **4.60 — below NFR-008's 4.8 mm floor** |
| **30x12** | **deep** | **4.84** | **4.60 — below the floor** |

Small grids are unaffected because they are already at the cap. The cost falls entirely on the
large, deeply-clued puzzles — which are the hard ones, printed for the readers most likely to
mark cells by hand. A deeply-clued 30x30 sits 0.04 mm above the floor today and crosses it at
the new margins, which raises FR-031's below-floor flag.

**This compounds with CARD-225.** Under a book-wide size per grid size, the deepest-clued
member decides for every puzzle of that size, so one deep 30x30 drags every 30x30 in the book
to 4.60 mm and raises the flag for all of them. The two cards are individually reasonable and
jointly push a whole grid size under the floor. **Surfaced to the owner as a decision before
either card starts.**

## Owner decision 2026-10-14 — the gutter stays at 0.5 in

Presented with the measurement above, the owner chose **outer 0.5 in, top 0.55 in, bottom
0.47 in as drawn, but the gutter unchanged at KDP's required 0.5 in** rather than the
artifact's 0.75 in. Re-measured against `_placed_cell_mm` with the shipped spec:

| | usable width | deep 30x30 cell | deep 25x25 | deep 20x20 |
|---|---|---|---|---|
| today | 193.68 mm | 4.84 mm | 5.87 | 7.45 |
| **shipped by this card** | **190.50 mm** | **4.76 mm** | **5.77** | **7.33** |
| artifact as drawn (0.75 in gutter) | 184.15 mm | 4.60 mm | 5.58 | 7.08 |

The cost falls from 4.9% to **1.6%**, uniformly, on every cell not already at the 7.5 mm cap.
Usable height goes 248.35 -> 241.49 mm.

**Stated honestly, because it is still true:** a deeply-clued 30x30 or 30x12 still lands at
4.76 mm, under NFR-008's 4.8 mm floor, so FR-031's below-floor flag still fires for that case —
0.04 mm under instead of 0.20 mm under. The owner accepted that with the reasoning that the
gutter is where the page curves anyway, so width spent there is the least useful width on the
page. CARD-225 must therefore still handle a grid size whose shared size is under the floor
(its AC-6), and that AC is not hypothetical: it has a real case in the corpus.

**So CON-018's gutter clause is NOT amended** — only its outer, top and bottom values. That
also keeps CON-018's own KDP reasoning intact (0.375 in up to 150 pages, 0.5 in for 151-300,
and Book 1 straddles 150), which the 0.75 in gutter would have left stranded.
