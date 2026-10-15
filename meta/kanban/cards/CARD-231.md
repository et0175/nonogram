# CARD-231: A section opener names its section in large type, with dots, range and a line of what to expect

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/231-section-openers
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "Section openers": "Today each section starts with one small word in the middle of an empty page (pp. 8, 73, 124, 167). A proper opener names the section in large type, shows its difficulty dots and puzzle range, and adds one line on what to expect. Openers always start on a right-hand page."
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the frame), CARD-228 (the dots)
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_divider_page.py, tests/test_book_page_numbers.py, tests/test_book_toc.py, tests/property/test_book_export_interior.py, tests/fixtures/book_baseline_card231.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** `create_divider_page(self, page_number,
text: str = "SOLUTIONS")` (`book_pdf_generator.py:3647`) draws **one word** on an otherwise
empty page. The level dividers use the tier's label the same way. That is the owner's "one
small word in the middle of an empty page" on pp. 8, 73, 124 and 167.

**What changes.**

1. An opener carries four things: the **section's name in large type**, its **difficulty dots**
   (CARD-228), its **puzzle range** (`Puzzles 1-60`, the same range the structural TOC prints —
   read it from the page plan, not from a second count), and **one line on what to expect**.
2. **Openers always start on a right-hand page.** That is a parity requirement with a real
   consequence: when an opener would fall on a verso, a blank page is inserted before it, which
   changes the interior's page count, the KDP band and therefore the printed gutter. This is
   the card's main risk and its main test.
3. The **Solutions opener uses the same frame without the dots** (the artifact's own caption) —
   there is no difficulty for an answer section.
4. The TOC's range rows and an opener's range must agree by construction: both come from
   `structural_toc_entries`' own level runs (CARD-205 built that), never from two counts.

## Acceptance criteria

- **AC-1** (happy, the four parts): *Given* a level opener, *then* it carries the section name
  in the large face, three dots filled to the tier's rank, the puzzle range, and one line of
  expectation text. (test: `TestSectionOpener_CarriesNameDotsRangeAndLine`)
- **AC-2** (happy, always recto): *Given* a book whose level boundaries fall at every parity,
  *when* the interior is exported, *then* **every** opener sits on a right-hand page.
  (test: `TestSectionOpener_AlwaysStartsOnARightHandPage`)
- **AC-3** (happy, the inserted blank): *Given* an opener that would fall on a verso, *then* a
  blank page is inserted before it, that blank carries no folio or a folio per FR-043's rule as
  the owner's convention requires (state which, and test it), and the interior's page count
  reflects it. (test: `TestSectionOpener_InsertsABlankToReachARecto`)
- **AC-4** (guard, the page count and the gutter follow): *Given* a book that needs inserted
  blanks, *then* `interior_page_count`, `unpaired_interior_page_count` and the exported page
  count all agree, and the KDP band is computed from the real total.
  (test: `TestSectionOpener_PageCountAndBandIncludeTheBlanks`)
- **AC-5** (happy, the range matches the TOC): *Given* each level, *then* the opener's range
  string and the TOC's range row for that level are equal, read from the same function.
  (test: `TestSectionOpener_RangeAgreesWithTheToc`)
- **AC-6** (happy, Solutions): *Given* the Solutions opener, *then* it uses the same frame and
  large face, carries **no dots**, and still carries a range or its own line as the artifact
  shows. (test: `TestSectionOpener_SolutionsHasNoDots`)
- **AC-7** (edge, one level): *Given* an all-easy book, *then* there is exactly one level opener
  plus the Solutions opener, and no empty opener for a level with no puzzles — the same
  "only when there are puzzles" guard the dividers and the TOC already apply.
  (test: `TestSectionOpener_SkipsEmptyLevels`)

## Guardrails

- G-1: Every opener page carries its folio per FR-043, unless the convention AC-3 pins says a
  deliberately blank page does not (test: `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-2: The TOC still points at each opener's own page number after any blank is inserted (test:
  `TestBookToc_PageNumbersMatchTheWalk`, `tests/test_book_toc.py:357`).
- G-3: INV-009 — a book's order is grouped by tier, which is what makes a level's range
  contiguous at all (test: `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence`).
- G-4: CON-020's floor holds for the expectation line and the range; the large face is a title,
  not an exemption (test: `TestInteriorType_EveryFaceHoldsTheFloor`).
- G-5: Out of scope — the dots glyph itself (CARD-228), the TOC's rows (CARD-205, merged).
- G-6: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- FR-043 — the interior's pages, folios and TOC (check:
  `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`)
- INV-013 — parity is the 1-based interior position, which "right-hand page" is defined
  against (check: `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
- INV-009 — grouped by tier (check: `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence`)
- CON-020 (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0036/R2 (check: review-lens)

## Architecture context

- **FR:** FR-043. The inserted-blank rule is new behaviour with a page-count consequence and
  needs its own acceptance criteria in the registry — **owed at the architect station**.
- **INV:** INV-013 (parity), INV-009 (tier grouping).
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [The expensive half of this card is parity, not typography] "Openers always start on a
  right-hand page" inserts blank pages, and every inserted page moves the KDP gutter band. The
  project has already had one card (CARD-205) whose whole risk was a page count feeding a
  printed margin, and one (CARD-221) cut because a page count was host-dependent. Treat AC-4 as
  the gating criterion.
