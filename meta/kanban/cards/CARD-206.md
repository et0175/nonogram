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
- `INV-013` states the interior "**starts at the guide page as a right-hand
  page 1**" and `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`
  asserts it. The cover stays a separate file (FR-043) and is unaffected.

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

**Architecture delta this card requires (flag, do not edit).** INV-013 and
FR-043 both say the interior *starts at the guide page*. After this card the
interior starts at the title page, and the property test named above encodes
the old statement. The card must: implement the behaviour the owner asked for,
update that property test to the new statement, and record in its Worktree
notes that `INV-013`/`FR-043` need an architect-station amendment ("starts at
the title page as right-hand page 1; the guide follows"). Kanban cards only read
`meta/architecture/**` — the same posture CARD-198/202 took for FR-042/INV-011.

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

- INV-013 — interior holds no cover page; parity is the 1-based interior
  position (check: `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`
  — **this card amends the statement; see the delta note above**)
- CON-020 — 10 pt floor for reader-facing interior text (vacuous on a blank
  page, but the card must not introduce sub-floor text; check:
  `TestInteriorType_EveryFaceHoldsTheFloor`)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- ADR-0036/R2 — layout functions own page geometry (check: review-lens)

## Architecture context

- **FR:** FR-043 (interior/cover split, folios, TOC) — amended by this card, see
  the delta note.
- **ADR:** ADR-0036 (book page geometry), ADR-0035/R1 (status gating untouched).
- **CON:** CON-018 (Book 1 trim profile), CON-019, CON-020.
- **Components:** COMP-009 (`book_pdf_generator.py`, `book_kdp.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—
