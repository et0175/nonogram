# CARD-231: A section opener names its section in large type, with dots, range and a line of what to expect

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/231-section-openers
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "Section openers": "Today each section starts with one small word in the middle of an empty page (pp. 8, 73, 124, 167). A proper opener names the section in large type, shows its difficulty dots and puzzle range, and adds one line on what to expect. Openers always start on a right-hand page."
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the frame), CARD-228 (the dots)
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_divider_page.py, tests/test_book_page_numbers.py, tests/test_book_toc.py, tests/property/test_book_export_interior.py, tests/fixtures/book_baseline_card231.json, meta/profiling/rank_durations.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
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

_Assembled 2026-10-17 by `system_rules.py --card CARD-231 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **FR-043 — the section-opener behaviour this card needs is STILL OWED, and was explicitly out
  of scope of the 2026-10-17 delta.** FR-043 *was* amended that day (commit `91609aa`) — but
  only for the **front matter**: interior page 1 becomes the blank title / copyright page and
  the guide moves to a facing spread on pages 2–3. **That amendment does not touch this card's
  rule.** "Openers always start on a right-hand page", and the inserted blank page that follows
  from it — which moves the interior's page count, the KDP band and therefore the printed
  gutter — still has **no acceptance criterion in the registry** and did not acquire one. Do
  not read the FR-043 amendment as satisfying it; AC-3 and AC-4 are still this card's own
  claims, gated against nothing in the registry until the architect station writes them.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-043. The inserted-blank rule is new behaviour with a page-count consequence and
  needs its own acceptance criteria in the registry — **still owed at the architect station**.
  FR-043 *was* amended on 2026-10-17 (commit `91609aa`), but only for the front matter (page 1
  becomes the blank title page, the guide moves to a facing spread on pages 2–3). **That
  amendment does not cover this card:** "openers always start on a right-hand page" and the
  blank page it inserts — which moves the interior's page count, the KDP band and therefore the
  printed gutter — acquired no acceptance criterion, and this card's own section-opener
  behaviour was explicitly out of that delta's scope.
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

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** a section opener names its section in large type, with dots — to be
implemented on today's raster divider page, whose own docstring is *"one word on
the book's trim, one page"*.

**Should be:** **born vector.** The owner left the dividers raster on 2026-10-25 —
*"I'd left dividers out for now - I think I can come out with a 'nicer' design for
them"* — precisely so this card's redesign is drawn as operators from the start
rather than converting the old page and then redesigning it.

**Delta:**
- This card is the **only** print-layout card whose page is still raster when it
  starts, and it is raster deliberately. It does not convert the existing divider;
  it replaces it with a vector design.
- **Landing this card EXPIRES ADR-0042/R2's divider exception.** R2 declares two
  raster exceptions, the cover and the dividers, and states that *"a declaration
  whose reason has expired"* is a defect: *"once CARD-231 lands, the divider's
  exception goes with it."* So this card must also **remove the divider from the
  declared raster set** and leave the cover as the only exception.
- CARD-298's `test_every_raster_page_is_declared_with_its_reason` reads the
  declaration rather than hard-coding the pair, and its AC-3 specifically tests
  that an expired declaration reds — so the guard is already built to catch this
  card forgetting the removal.
- `divider` is one of the lettering kinds CON-020's non-vacuity floor requires
  (`tests/test_book_interior_type_floor.py:355`). When the divider goes vector,
  that kind's reading must move to the stream with it — CARD-299 left it on the
  raster path precisely because this card had not run.

## [Cross-reference added 2026-10-29 — CARD-311 is the sibling feature]

The owner asked whether the panel could **upload** a divider page; it cannot, and
**CARD-311** was cut for it the same day. The two cards touch the same page from
opposite directions and neither depends on the other:

- **this card** makes the *generated* opener richer — large type, dots, range, a
  line of what to expect;
- **CARD-311** lets the owner supply an image that replaces it, with the drawn page
  as the fallback when a slot is empty.

So they are complementary: whatever this card designs becomes CARD-311's fallback.
But **whichever lands second inherits a question neither card can answer alone** —
whether an uploaded image should be able to replace a designed page at all, and
what that means for CON-020's 10 pt type floor, which an image bypasses because the
floor is verified by watching text draws. Worth the owner's view before the second
one starts, rather than discovered by the second round.

One ordering fact, measured: **ADR-0042/R2 keeps `PageKind.DIVIDER` declared raster
specifically for this card** — its reason is that the new design should be *"born
vector rather than the old one converted"*, and the declaration's `expires_with`
names CARD-231. CARD-311 would make that page raster for a different and permanent
reason, so if CARD-311 lands first, this card's vector ambition needs restating
rather than assuming.
