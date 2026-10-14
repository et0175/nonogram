# CARD-226: A two-up page becomes two equal slots split by a light rule, with aligned bottoms

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/226-two-up-equal-slots
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 3 ("Two-up pages don't line up. Two stacked puzzles get different cell sizes and different left edges (pp. 9, 12), and nothing separates them") and "Small puzzles, two to a page"
**Idea:** —
**Wave:** —
**Depends on:** CARD-224 (centring), CARD-225 (the shared cell size), CARD-223 (each slot's own QR corner)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_two_up.py, tests/test_book_page_numbers.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/book_baseline_card226.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The owner's issue 3 names three separate defects on one page: different cell sizes, different
left edges, and nothing separating the two puzzles. CARD-225 fixes the first (both puzzles
take the smaller of their two book sizes). This card fixes the other two and makes the slot a
real region.

**What changes.**

1. The puzzle area splits into **two equal slots**, separated by a **light rule** across the
   text width. Equal means measured: the two slots' heights differ by at most a pixel.
2. Each slot "follows the same rule as a full page" (the owner's words): the grid centred
   horizontally, the 42% placement within the slot, and **its QR at the slot's outer bottom
   corner** (CARD-223's rule applied per slot, not per page).
3. **The two grids' bottoms align** with each other — the artifact's "its bottom aligned with
   the grid's bottom". With a shared cell size (CARD-225) and equal slots this follows, so the
   test is the proof that all three cards agree, and it is the one that fails first if any of
   them drifts.
4. Keep CARD-204's folio reservation on the lower slot. It was added for a real regression —
   two-up pages were losing their folios — and the owner accepted its measured cost (about 5%
   of pairs refuse to share a page). That cost does **not** change here.

## Acceptance criteria

- **AC-1** (happy, equal slots): *Given* a two-up page, *then* the two slots' heights differ
  by at most one pixel and a light rule lies between them, spanning the text width.
  (test: `TestBookTwoUp_SlotsAreEqualAndSeparated`)
- **AC-2** (happy, same left edge): *Given* two puzzles of the same grid size on one page,
  *then* their grids' left edges are identical. (test: `TestBookTwoUp_GridsShareTheirLeftEdge`)
- **AC-3** (happy, aligned bottoms): *Given* any admitted pair, *then* each grid's bottom sits
  at the same offset from its own slot's bottom. (test: `TestBookTwoUp_BottomsAlign`)
- **AC-4** (happy, a QR per slot, outer): *Given* each slot, *then* its QR sits at the slot's
  **outer** bottom corner, and no QR ink lies in the gutter half of the page at either parity.
  (test: `TestBookTwoUp_EachSlotsQrIsOuter`)
- **AC-5** (guard, the folio survives): *Given* every two-up page, *then* it carries its
  folio, and the lower slot's reservation is unchanged.
  (test: `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`)
- **AC-6** (edge, different grid sizes): *Given* a 15x15 and a 10x20 sharing a page, *then*
  both draw at the smaller book size and both slots still hold their own grid, rule and QR.
  (test: `TestBookTwoUp_MixedGridSizes`)
- **AC-7** (edge, the pairing rate): *Given* the corpus, *when* the interior is exported,
  *then* the number of pages is recorded against the figure before this card, and any change
  is attributed — equal slots may admit or refuse a pair the old asymmetric layout did not.
  (test: `TestBookTwoUp_PageCountIsAttributed`)

## Guardrails

- G-1: FR-040 decides *which* puzzles pair; this card decides how a page holds them. No change
  to the pairing predicate (test: the existing pairing tests).
- G-2: The caption/folio collision CARD-204 Fix 8 closed stays closed, on both slots (test:
  the existing caption-slot and folio tests).
- G-3: **`_draw_solved_slot`'s return value has two consumers** — `solved_puzzle_page` and
  `_packed_answer_page` — and nothing enforces changing them together. This family has
  produced five gating regressions across CARD-203 and CARD-204. If this card touches that
  return value, both consumers change in the same commit, and the notes say so.
- G-4: Out of scope — the solution pages' tiles (CARD-232), the cell size rule itself (CARD-225).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- FR-040 — two-up pairing, including the "and only when" clause already owed an amendment
  (check: the pairing tests)
- FR-043 — every interior page carries its folio (check:
  `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`)
- CON-020 (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0036/R2 (check: review-lens)
- INV-013 — parity, which "outer" is defined against (check:
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)

## Architecture context

- **FR:** FR-040, FR-043.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Why AC-3 is the keystone] Aligned bottoms is the only assertion in the set that fails if
  *any* of CARD-224, CARD-225 or this card drifts. It is cheap to write and it is the one to
  keep green.
