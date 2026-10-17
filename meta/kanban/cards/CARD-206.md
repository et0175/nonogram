# CARD-206: The interior opens with a blank title / copyright page, ahead of the guide

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/206-interior-title-page
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("# Book structure — The generator should construct the PDF in this order: Front matter ├─ Title / copyright page ├─ How to Solve Nonograms ├─ Table of Contents [generated]"); owner decision 2026-10-13 via AskUserQuestion — the page is **reserved blank** (a template page), not populated: "Leave it blank (template page) — reserve the page in the page plan so counts and parity are right, print nothing on it; you add the copyright text in the PDF afterwards."
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_page_numbers.py, tests/test_book_export_interior_cover.py, tests/property/test_book_export_interior.py, tests/test_book_toc.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The interior's first page is the guide: `interior_stream`'s `produce()` yields
  `create_guide_page` for `1 .. GUIDE_PAGE_COUNT` (`GUIDE_PAGE_COUNT = 2`,
  `book_pdf_generator.py:459`), then the TOC pages at
  `GUIDE_PAGE_COUNT + 1 + index`, then the puzzle section, then the SOLUTIONS
  divider and the answer pages.
- Every downstream page number is derived from that start:
  `section_plan`'s `first_page`, `interior_page_count`'s terms
  (`:2111`), and `book_kdp.unpaired_interior_page_count` (`book_kdp.py:484`).
- `INV-013` **no longer** says the interior starts at the guide page: it and
  FR-043 were amended on 2026-10-17 (commit `91609aa`) to say page 1 is the
  book's blank title / copyright page with the guide following on pages 2 and 3.
  The shipped code and
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` still
  encode the old statement, so they are what this card brings up to the
  registry. The cover stays a separate file (FR-043) and is unaffected.

**What changes.** One blank page is inserted as interior page 1, so the front
matter reads: title/copyright (blank) → How to Solve (2 pages) → TOC → EASY
divider → ….

1. Add a front-matter page count constant next to `GUIDE_PAGE_COUNT`
   (e.g. `TITLE_PAGE_COUNT = 1`) and yield that page first in `produce()`: a
   white page on `self.page_spec(1)`, nothing drawn — **no folio either** (a
   title page carries no page number in any printed book, and this one carries
   no ink at all).
2. Shift every subsequent position by that constant — the guide pages, the TOC
   pages, `section_plan`'s `first_page`, `interior_page_count` and
   `book_kdp.unpaired_interior_page_count`. Derive it from the constant in
   every one of those places; a literal `3` anywhere is the bug this card is
   most likely to ship.
3. Parity: inserting one page flips the parity of **every** page after it, which
   is what moves each puzzle page's gutter side (`book_page_spec`'s
   `PageParity`). That is the intended consequence, not a side effect — the
   guide now opens on a left-hand page 2. Check it against a rendered proof
   before claiming the card done (owner validates print changes visually).
4. The page is reserved by the page plan, so the exported PDF gains exactly one
   page and the KDP gutter table is consulted with that count.

**The architecture delta this card flagged has LANDED (2026-10-17, commit
`91609aa`) — nothing is owed at the architect station.** INV-013 and FR-043 were
amended as **one statement covering both claimants**, this card and CARD-229:
interior page 1 is the book's title / copyright page, a right-hand page carrying
no folio and no ink at all, and the guide follows as a facing spread on pages 2
(verso) and 3 (recto). The parity mechanism and the page count finalise checks
against KDP are unchanged. The card must therefore: implement that behaviour,
and update
`PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` — which
still encodes the retired statement — to the amended one. Build against AC-283
(page 1 blank, no ink of any kind), AC-286, AC-287 (re-measured: the first
puzzle page is now interior page 6, a left-hand page), AC-289 and EC-034.
Kanban cards only read `meta/architecture/**` — the same posture CARD-198/202
took for FR-042/INV-011.

## Acceptance criteria

- **AC-1** (happy): *Given* any book with at least one drawable puzzle, *when*
  its interior is exported, *then* page 1 is blank — no folio, no title, no
  rule, no ink of any kind — and page 2 is the guide's first page. (test:
  `TestBookExport_InteriorOpensWithABlankTitlePage`)
- **AC-2** (happy, counts): *Given* the same book, *when* the interior is
  exported, *then* its page count is exactly one more than before this card,
  and `interior_page_count` and `book_kdp.unpaired_interior_page_count` both
  report that same number. (test: `TestBookExport_TitlePageCountedEverywhere`)
- **AC-3** (happy, positions): *Given* the same book, *when* the TOC is drawn,
  *then* every TOC row's page number still points at the page it names (the
  guide, each level's divider, the SOLUTIONS divider) after the shift. (test:
  `TestBookToc_PageNumbersSurviveTheTitlePage`)
- **AC-4** (edge, parity): *Given* a book whose first puzzle page was a
  right-hand page before this card, *when* it is exported, *then* that page is
  now a left-hand page and its margins are the left-hand spec — i.e. parity is
  still the 1-based interior position, counted from the title page. (test:
  `PropertyTest_BookExport_ParityCountsFromTheTitlePage`)
- **AC-5** (edge, no cover in interior): *Given* a book with an uploaded cover,
  *when* it is exported, *then* the cover is still a separate file and the
  interior's page 1 is the blank title page, not the cover. (test:
  `TestBookExport_InteriorHoldsNoCoverPage`, extended)
- **AC-6** (edge, empty book): *Given* a book with no drawable puzzle, *when*
  the interior is exported, *then* the existing refusal/empty behaviour is
  unchanged — this card does not make a blank page the only page of an
  otherwise-empty book. (test: `TestBookExport_EmptyBookUnchanged`)

## Guardrails

- G-1: The cover is produced as a separate file and never enters the interior
  (FR-043, INV-013's surviving half; test:
  `TestBookExport_EveryRouteSeparatesInteriorAndCover`).
- G-2: Puzzle-page and answer-page geometry is untouched — only positions
  shift. Do not edit `src/nonogram/export/layout.py` (owned by CARD-204).
- G-3: The guide's own content and page count are unchanged (CARD-201's 2-page
  tutorial; test: `TestBookGuidePage_*`).
- G-4: Out of scope — no imprint/ISBN field, no author line, no owner-editable
  copyright text (explicit owner decision 2026-10-13; the page stays blank).
- G-5: CLI and web-UI exports stay byte-identical (CON-019) — this is a book
  interior change only.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-206 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-013 / FR-043 — the amendment this card flagged LANDED** on 2026-10-17 (commit
  `91609aa`), jointly with CARD-229 and as one statement covering both claimants: interior
  page 1 is now the book's blank title / copyright page (no folio, no ink) and the guide
  follows as a facing spread on pages 2 (verso) and 3 (recto). **Nothing is owed at the
  architect station for this card** — the registry now states what this card builds. Build
  against AC-283 (page 1 is the title page, no ink of any kind), AC-286, AC-287 (re-measured:
  the first puzzle page moves to interior page 6, a left-hand page), AC-289 and EC-034.
  AC-283's test name is this card's own `TestBookExport_InteriorOpensWithABlankTitlePage`, a
  planned name — it does not exist yet, so write it rather than assume it.

- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 perc… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_51 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-043 (interior/cover split, folios, TOC) — amended by this card, see
  the delta note.
- **ADR:** ADR-0036 (book page geometry), ADR-0035/R1 (status gating untouched).
- **CON:** CON-018 (Book 1 trim profile), CON-019, CON-020.
- **Components:** COMP-009 (`book_pdf_generator.py`, `book_kdp.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—

## Amendment 2026-10-14 — the owner's "Puzzle page layout" artifact

The artifact (https://claude.ai/artifact/Wp4iGB27cyBAV62da5ACMP) puts the guide on interior
pages **2 and 3** so the two pages face each other. That is only possible if something occupies
page 1 — which is this card. So:

- This card is no longer only a nicety; **CARD-229 depends on it structurally.** "Facing" is a
  claim about parity, and two pages face only when the first of them is a verso.
- The **INV-013 amendment this card flagged LANDED on 2026-10-17** (commit `91609aa`), and
  landed the way this bullet asked for it: **as one statement covering both claimants**, this
  card and CARD-229 — interior page 1 is the blank title page, the guide is the facing spread on
  pages 2 (verso) and 3 (recto). Nothing is owed at the architect station any more.
- The page this card adds shifts every interior page number by one, which moves the TOC's rows,
  the KDP band and therefore the printed gutter. CARD-205 left a three-caller page-count
  cross-check in place (`TestBookToc_KdpAgreesWithTheExportedCount`,
  `tests/test_book_toc.py:595`) — that is the test which must stay green.
- ~~Still blocked in substance until the architect pass makes the INV-013 / FR-043
  amendment.~~ **Unblocked 2026-10-17:** that amendment landed in commit `91609aa`. The card is
  ready to start on the registry as it now stands.
