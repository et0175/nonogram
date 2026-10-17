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
- **INV-013 used to say the interior starts at the guide page as right-hand page 1.** Pages 2
  and 3 can only face each other if something else is page 1 — which is exactly CARD-206's
  blank title page, and why this card depends on it. **That amendment LANDED on 2026-10-17**
  (commit `91609aa`), as one statement covering both claimants: INV-013 and FR-043 now say
  page 1 is the blank title / copyright page with the guide following as a facing spread on
  pages 2 (verso) and 3 (recto), and **AC-368** is the registry's criterion for the spread.
  Nothing is owed at the architect station; the shipped code and
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` are what still encode
  the retired statement.

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

_Assembled 2026-10-17 by `system_rules.py --card CARD-229 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-013 / FR-043 — the amendment this card flagged LANDED** on 2026-10-17 (commit
  `91609aa`), as **one statement covering both claimants** (this card and CARD-206), which is
  what the two cards asked for: interior page 1 is the blank title / copyright page and the
  guide is the facing spread on pages **2 (verso) and 3 (recto)**. **Nothing is owed at the
  architect station.** The registry's criterion for the spread is **AC-368**, which names this
  card's own planned test `TestGuideSpread_SitsOnPagesTwoAndThree` (it does not exist yet);
  AC-283/AC-286/AC-289 and EC-034 were reworded for the title page, and AC-287 was re-measured
  — the first puzzle page moves to interior page 6. The parity mechanism and the KDP
  page-count check are unchanged.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-041 (the guide), FR-043 (folios, the TOC's rows).
- **INV:** **INV-013 (amended 2026-10-17, commit `91609aa`, jointly with CARD-206 as one
  statement — guide on interior pages 2 and 3; nothing owed)**.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [The dependency on CARD-206 is structural, not stylistic] "Facing" is a claim about parity.
  Two pages face only when the first is a verso, so the guide cannot face until something
  occupies page 1. Starting this card before CARD-206 would mean implementing the spread
  against a parity that is about to change.

## Inherited from CARD-221, 2026-10-14 — a disagreement this card is expected to close

CARD-221 dropped the difficulty box's three sentences from printed guide page 2 (the owner's
decision), but **the Finalise screen's preview still shows them**
(`src/nonogram/admin/templates/book_finalize.html`), so that screen and the page it previews now
disagree. `DifficultyLabel.text` is deliberately kept alive for this reason and for this card's
key strip.

CARD-221 left it rather than fixing it, correctly — its G-6 put the admin screen out of scope,
and this card rebuilds the block on **both** surfaces anyway. Recorded here so it cannot be lost
between the two: reconciling them is a one-line template change plus
`tests/test_book_finalise_guide_preview.py:622`. This card's G-2 already requires the preview to
keep agreeing with the printed pages, so the disagreement must be gone by the time it merges.
