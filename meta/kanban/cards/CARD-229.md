# CARD-229: "How to Solve" becomes a facing spread on pages 2 and 3, in the puzzle pages' own frame

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/229-guide-facing-spread
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "How to Solve, as a facing spread"
**Idea:** —
**Wave:** —
**Depends on:** CARD-206 (the title page that makes page 1, so the guide can start on page 2 and face page 3), CARD-222 (the frame it borrows), CARD-228 (the dots its key strip teaches)
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_finalise_guide_preview.py, tests/test_book_page_numbers.py, tests/property/test_book_export_interior.py, tests/fixtures/book_baseline_card229.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The owner's requirement:** *"The two guide pages should face each other, on pages 2 and 3,
so a reader sees the whole lesson at once. They use the same header rule, margins and grey
clue boxes as the puzzle pages, so the examples look like the puzzles they teach. Each
technique sits in two columns: a numbered heading and a short explanation on the left, its
example on the right."*

**Current behaviour (verified by reading the code).**

- `GUIDE_PAGE_COUNT = 2` and `GUIDE_TITLE = "How to Solve Nonograms"`
  (`book_pdf_generator.py:491,497`); `create_guide_page` draws them (`:3196`).
- The guide is set in its own type scale — `GUIDE_TITLE_PT = 22.0`, `GUIDE_BODY_PT = 11.0`,
  `GUIDE_LEADING_PT = 17.0`, `GUIDE_TITLE_GAP_PT = 36.0` — not in the puzzle pages' frame.
- Its content constants are already named and tested: `GUIDE_INTRO`,
  `GUIDE_CELL_STATES_HEADING` + `GUIDE_CELL_STATES` (the three marks, **as a vertical list**),
  `GUIDE_EXAMPLE_HEADING`, `GUIDE_CLOSING_HEADING`, `GUIDE_CLOSING`, `GUIDE_BASIC_RULE_TEXT`.
- **INV-013 says the interior starts at the guide page as right-hand page 1.** Pages 2 and 3
  can only face each other if something else is page 1 — which is exactly CARD-206's blank
  title page. That is why this card depends on it, and why **INV-013's amendment is owed at
  the architect station** (CARD-206 already flags it; this card is the second claimant).

**What changes.**

1. The guide occupies interior pages **2 and 3**, so they face. Page 2 is a verso and page 3 a
   recto: assert the parity, not just the numbers.
2. The two pages adopt CARD-222's frame — the same margins, the same header rule at the same
   baseline, the same footer — so the lesson looks like the puzzles it teaches.
3. Examples use the **grey clue boxes** of the puzzle pages (CARD-208's shading), one cell size
   for every example, and a heavier outline around the playable squares.
4. Each technique becomes **two columns**: a numbered heading and its short explanation on the
   left, its example on the right.
5. **The three marks become a key strip at the top**, replacing today's vertical
   `GUIDE_CELL_STATES` list, and the key strip also carries the **difficulty legend** built
   from CARD-228's dots — the one place a reader learns them.
6. The copy is *the owner's current text, lightly tightened*. Keep the existing constants as
   the source; if a string changes, change the constant, and do not move prose into the
   drawing code.

**Deliberately not in this card:** the worked example's four steps and the rows/columns
callout at the foot of page 2 — CARD-230, so that this card's diff is the spread and the frame.

## Acceptance criteria

- **AC-1** (happy, the spread): *Given* any non-empty book, *when* the interior is exported,
  *then* the guide is interior pages 2 and 3, page 2 is a verso and page 3 a recto, and they
  face. (test: `TestGuideSpread_SitsOnPagesTwoAndThree`)
- **AC-2** (happy, the borrowed frame): *Given* a guide page and a puzzle page of the same
  book, *then* their margins, header-rule y and footer-rule y are identical, measured off the
  ink. (test: `TestGuideSpread_SharesThePuzzlePagesFrame`)
- **AC-3** (happy, two columns): *Given* each technique, *then* its heading and explanation lie
  wholly in the left column and its example wholly in the right, with no ink crossing the
  column boundary. (test: `TestGuideSpread_EachTechniqueIsTwoColumns`)
- **AC-4** (happy, the key strip): *Given* page 2, *then* the three marks are drawn as one
  horizontal strip at the top — not as a vertical list — and the difficulty legend beside them
  uses CARD-228's dots. (test: `TestGuideSpread_MarksAndLegendAreAKeyStrip`)
- **AC-5** (happy, one example cell size): *Given* every example on both pages, *then* all are
  drawn at one cell size, and the playable squares carry a heavier outline than the cell lines.
  (test: `TestGuideSpread_ExamplesShareOneCellSize`)
- **AC-6** (guard, the copy is the stored copy): *Given* the drawn pages, *then* every sentence
  comes from an existing `GUIDE_*` constant — asserted by comparing drawn text against the
  constants, so prose cannot drift into the drawing code.
  (test: `TestGuideSpread_TextComesFromTheConstants`)
- **AC-7** (edge, the page count and parity): *Given* a book with and without puzzles, *then*
  the interior's page count and every page's parity still agree with
  `interior_page_count`, `unpaired_interior_page_count` and the TOC's own page numbers — the
  guide moving by one page moves every number after it.
  (test: `TestBookToc_PageNumbersMatchTheWalk`, `tests/test_book_toc.py:357`)

## Guardrails

- G-1: CON-020's 10 pt floor holds for every face on both pages, including the key strip's
  labels and the two-column body (test: `TestInteriorType_EveryFaceHoldsTheFloor`; and the four
  `TestGuidePage_*` classes in `tests/test_book_guide_page_type.py`).
- G-2: The Finalise screen's guide preview keeps agreeing with the printed pages — it reads the
  generator's own text (test: `tests/test_book_finalise_guide_preview.py`'s
  `TestFinaliseGuidePreview_ReadsTheGeneratorsText`).
- G-3: The TOC's own `How to Solve Nonograms` row still points at the guide's first page, which
  is now 2, not 1 (test: `TestBookToc_PageNumbersMatchTheWalk`).
- G-4: Out of scope — the worked example's steps and the callout (CARD-230), the title page
  itself (CARD-206).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- **INV-013** — the interior holds no cover page and **starts at the guide page as right-hand
  page 1**. This card and CARD-206 both contradict that clause; the amendment is owed at the
  architect station and should be made once, for both (check:
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
- FR-041 — the guide page's content, including CARD-201's deferred clause (check: the guide
  tests)
- CON-020 (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0036/R2 (check: review-lens)

## Architecture context

- **FR:** FR-041 (the guide), FR-043 (folios, the TOC's rows).
- **INV:** **INV-013 (amendment owed, jointly with CARD-206)**.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [The dependency on CARD-206 is structural, not stylistic] "Facing" is a claim about parity.
  Two pages face only when the first is a verso, so the guide cannot face until something
  occupies page 1. Starting this card before CARD-206 would mean implementing the spread
  against a parity that is about to change.
