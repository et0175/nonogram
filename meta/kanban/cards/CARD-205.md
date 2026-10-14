# CARD-205: The table of contents lists sections, not puzzles — How to Solve, each level with its puzzle range, Solutions

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/205-structural-toc
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 1: "PDF book - Table of contents - let's don't not have individual puzzles in ToC - only How-to-Solve, Easy-medium-hard divisors and Solutions"; restated later in the same doc under "Add table of contents" with the same sample)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_toc.py, tests/test_book_finalise_gutter.py, tests/property/test_book_export_interior.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- `BookPDFGenerator.interior_stream` builds **one TOC row per drawable puzzle**
  (`book_pdf_generator.py:4531` — `toc_entries`), labelled through
  `answer_caption(number, answer_title(...))` ("37. Ice skate") against that
  puzzle's own `PuzzlePagePlan.page_number`. A 150-puzzle book therefore prints
  150 rows: at `TOC_ENTRY_PT = 10.0` + `TOC_ENTRY_GAP_PT = 4.0`
  (`book_pdf_generator.py:479`) that is several TOC pages, split by
  `measured_toc_page_count` / `_toc_entries_per_page` (`:2079`, `:2036`).
- `create_toc_page` (`:3067`) draws a page's slice: label left (clipped with an
  ellipsis when too wide), page number right-aligned, **no leader dots**, title
  `TOC_TITLE = "Table of Contents"` repeated on every TOC page, folio at the
  bottom.
- `book_kdp.unpaired_interior_page_count` (`book_kdp.py:484`) calls
  `measured_toc_page_count(len(ordered), ...)` — the TOC page count that feeds
  KDP's gutter table is **derived from the puzzle count**. Changing the entry
  rule without changing this line makes the gutter margin and the real book
  disagree.

**What changes.** The TOC becomes a fixed, structural list — one row per
section, never per puzzle:

```
CONTENTS

How to Solve Nonograms ................ 3

Easy
Puzzles 1–60 .......................... 5

Medium
Puzzles 61–120 ....................... 37

Hard
Puzzles 121–150 ...................... 69

Solutions ............................ 86
```

1. Build the entries from the page plan the walk already has, not from a second
   source of truth: the guide's own first page (`1` today, `GUIDE_PAGE_COUNT`
   pages), each non-empty level's **divider** page number and the
   first/last puzzle *numbers* in that level (both already in
   `SectionPlan.pages` — `DividerPagePlan.level` and the `PuzzlePagePlan.numbers`
   that follow it), and the first answer page (the SOLUTIONS divider, the same
   `first_answer_page` arithmetic `interior_stream` already does).
2. A level heading (`Easy` / `Medium` / `Hard`, from `Tier.label`, the same
   source `DividerPagePlan.text` uses) is a row of its own with **no page
   number**; the `Puzzles N–M` row underneath carries the number. A level with
   no printable puzzle gets neither row — the same "only when there are
   puzzles" guard the divider and the answer section already apply.
3. Leader dots fill the gap between label and number, drawn to the measured gap
   (the repeated-`.` run is sized from `entry_font.getlength(".")`, clipped to
   the available width, never overlapping either side). An entry whose label
   leaves no room for a single dot simply gets none.
4. The structural list is ~6 rows, so `measured_toc_page_count` is now called
   with the **entry count of the structural list** — in both callers: the
   generator and `book_kdp.unpaired_interior_page_count`. Keep the measured
   split (do not hardcode "the TOC is one page"): the same arithmetic still
   decides, it is simply fed a different count.
5. `answer_caption`/`answer_title` stop being read by the TOC path. They stay
   exactly as they are for the answer pages (AC-5 of CARD-200 was "no second
   independent title lookup"; this card removes the TOC's lookup entirely, which
   satisfies it trivially).

## Acceptance criteria

- **AC-1** (happy, structure): *Given* a book with easy, medium and hard
  puzzles, *when* its interior is exported, *then* the TOC pages hold exactly
  one `How to Solve Nonograms` row, one heading + one `Puzzles N–M` row per
  non-empty level, and one `Solutions` row — and **no row naming an individual
  puzzle**. (test: `TestBookToc_ListsSectionsNotPuzzles`)
- **AC-2** (happy, numbers): *Given* any such book, *when* the TOC is drawn,
  *then* every row's page number equals the interior position of the page it
  names — the guide's first page, that level's divider page, and the SOLUTIONS
  divider page — measured against the same `interior_stream` walk that drew
  them. (test: `TestBookToc_PageNumbersMatchTheWalk`)
- **AC-3** (happy, ranges): *Given* a book whose levels hold 60/60/30 puzzles,
  *when* the TOC is drawn, *then* the three range rows read `Puzzles 1–60`,
  `Puzzles 61–120`, `Puzzles 121–150`. (test:
  `TestBookToc_RangeRowsFollowTheLevelRuns`)
- **AC-4** (edge, one level): *Given* a book whose members are all easy, *when*
  the TOC is drawn, *then* it carries one level heading and one range row, and
  no empty heading for medium or hard. (test:
  `TestBookToc_SkipsEmptyLevels`)
- **AC-5** (edge, page count): *Given* a 150-puzzle book, *when* the interior is
  exported, *then* the TOC occupies one page, and
  `book_kdp.unpaired_interior_page_count` reports the same TOC page count the
  export actually wrote. (test: `TestBookToc_KdpAgreesWithTheExportedCount`)
- **AC-6** (edge, leaders): *Given* an entry whose label and number leave at
  least one dot of room, *when* the row is drawn, *then* the dots lie strictly
  between the label's right edge and the number's left edge, touching neither.
  (test: `TestBookToc_LeaderDotsStayInsideTheGap`)
- **AC-7** (edge, empty book): *Given* a book with no drawable puzzle, *when*
  the interior is exported, *then* no TOC page is produced (unchanged from
  CARD-200). (test: `TestBookToc_EmptyBookHasNoTocPage`)

## Guardrails

- G-1: Every TOC page keeps its folio, including the one-page case — the
  folio-sized reservation in `_toc_entries_per_page` is load-bearing, not a
  margin (test: `TestBookPageNumbers_EveryInteriorPageCarriesAFolio`).
- G-2: No new text-layout primitive — rows are set with `_guide_face`/`type_px`
  and `page_frame` like every other page (ADR-0036/R2).
- G-3: `answer_caption` / `answer_title` behaviour unchanged — the answer pages'
  captions are not touched by this card (test: `TestBookSolvedPage_Caption*`).
- G-4: Do not edit `src/nonogram/export/layout.py` — owned by CARD-204 (and no
  page geometry changes here: the TOC is text on an existing frame).
- G-5: Out of scope — no change to the TOC's title, type sizes, or its position
  after the guide page.

## System contract

(Projection of the lens over this card's `Touches:`; the lens's own glob scope
is far wider — `src/nonogram/**` — so only the rules that bear on this
mechanism are listed, mandatory first.)

- CON-020 — no reader-facing interior text below 10 pt except puzzle-page clue
  digits (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- INV-013 — the interior holds no cover page and starts at the guide page as
  right-hand page 1; parity is the 1-based interior position (check:
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
- INV-009 — a book's order is grouped by tier, which is what makes a level's
  puzzle numbers a contiguous range at all (check:
  `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence`)
- ADR-0036/R2 — page geometry comes from COMP-007's layout functions; the admin
  panel does not place things itself (check: review-lens)
- ADR-0033/R1 — book assembly never changes a puzzle's grid, clues, tier or
  strategies (check: review-lens)

## Architecture context

- **FR:** FR-043 (page numbers + table of contents, the statement CARD-200
  implemented). This card amends the TOC half of it: FR-043's acceptance
  criteria describe a per-puzzle listing. The amendment belongs at the
  architect station — this card does not edit `meta/architecture/**` (kanban
  cards only read it) and flags the delta here, the same shape CARD-198/202
  used for FR-042/INV-011.
- **ADR:** ADR-0036/R2 (layout owns geometry), ADR-0037/R1 (a puzzle page's
  band carries number + tier only — unaffected, the TOC is a different page).
- **CON:** CON-020 (10 pt floor), CON-018 (Book 1 profile, the frame measured).
- **Components:** COMP-009 (`book_pdf_generator.py`, `book_kdp.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—
