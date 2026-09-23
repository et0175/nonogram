# CARD-140: The arrange screen shows the book's real page breaks, not one every three puzzles

**Status:** ready
**Priority:** P1
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/140-arrange-real-page-breaks
**Worktree:** —
**Source:** owner, 2026-09-23 ("arrangement of puzzles by pages — it shows 3 puzzles per page, even for big ones")
**Idea:** —
**Wave:** 26
**Depends on:** CARD-128
**Touches:** src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/app.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_arrange_page_breaks.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`book_arrange_puzzles.html:114` draws a page divider every third puzzle:

    {% if puzzle.order % 3 == 0 and puzzle.order < puzzles[-1].order %}
    <div class="page-break-divider"><span>page {{ (puzzle.order // 3) + 1 }}</span></div>

Three per page was never true of any book this project prints. It is scaffolding from the
original arrange step, written before the book had a page model at all. The PDF puts **one
puzzle per page**, except a two-up pair: same tier, adjacent in print order, both fitting at
one shared cell of at least 7.0 mm (INV-010, CARD-127). So the real maximum is two, and for
big puzzles on a small trim it is one. The owner reported the screen showing three pages'
worth of big puzzles on one page.

The generator already decides this. `PuzzlePagePlan` (book_pdf_generator.py:351) carries a
page's 1-based interior position and the puzzle numbers on it, and the pairing walk builds
the list. **Do not re-implement pairing in the admin panel or the template** — ADR-0036/R2
says the panel fits no cell and places no tile, and a second implementation of INV-010 is
exactly the defect this card exists to remove.

1. **Expose a pure planning seam.** The existing walk needs full `ExportPayload`s because it
   renders; the arrange screen has no grids and should not load them. Extract (or add beside
   it) a function that decides the page plan from what the screen already has — each
   puzzle's tier and (width, height) extent, plus the book's PageSpec — and have the
   rendering path call that same function, so the two can never disagree. Both the stored
   extent and the tier are already on the puzzle record.
2. **Render breaks from the plan.** The divider appears where the plan starts a new page,
   and its label is the plan's page number, not an arithmetic guess. Two puzzles sharing a
   page are shown as sharing it.
3. **Show the level dividers too** (CARD-128, which this card depends on): a level's first
   puzzle opens a new page behind a divider page, so the arrange screen must show that break
   as well, labelled with the level. This is why the card waits for CARD-128 rather than
   racing it.
4. **Page numbers are interior numbers.** The interior starts at the guide page (INV-013), so
   the first puzzle page is not page 1. Show the number the printed book will carry.

Out of scope: changing pairing, the divider design, or anything about the arrangement
semantics (level-confined moves are CARD-126's and stay untouched). This card changes what
the screen *reports*, never what the book *does*.

## Acceptance criteria

- New: a book of 30x30 puzzles shows one puzzle per page, never three.
  test: TestArrangeBreaks_BigPuzzlesAreOnePerPage
- New: two adjacent same-tier puzzles that pair are shown sharing one page, with one page
  number.
  test: TestArrangeBreaks_PairedNeighboursShareAPage
- New: the page numbers shown are the interior numbers the PDF prints, for the same book.
  test: TestArrangeBreaks_NumbersMatchTheGeneratedInterior
- New: the screen's page plan and the PDF's page plan are the same object for any book — an
  independent corpus, not one call compared with itself.
  test: PropertyTest_ArrangeBreaks_AgreeWithTheGeneratedBook
- New: a level's first puzzle starts a new page and the break names the level.
  test: TestArrangeBreaks_LevelStartsANewPage

## Guardrails

- G-1: The panel decides no geometry (ADR-0036/R2). Pairing stays in COMP-007 / the
  generator; the screen asks and renders. No cell fitting, no 7.0 mm literal, no tier
  comparison for pairing in app.py or the template.
- G-2: INV-010 is unchanged — this card must not alter which puzzles pair, only what is
  displayed. The CARD-127 pairing tests stay green and untouched.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019).
- G-4: No schema change and no stored page plan — pages are decided at PDF time
  (Increment 15 Rollback).

## Architecture context

- **FR:** FR-036 (arrangement), FR-041
- **INV:** INV-010 (pairing), INV-013 (interior parity)
- **ADR:** ADR-0036 (geometry ownership), ADR-0033
- **Components:** COMP-009, COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23, after the first working deploy: "it shows 3 puzzles per page,
  even for big ones". The same message asked whether a level should start a new page —
  that half is CARD-128 (divider pages per level), already scheduled in this wave, so this
  card only has to display it.
- [Why it survived this long] Every book card so far changed the PDF, and the arrange
  screen's indicator was never wired to it. No test compared the two, which is why AC-4 is
  a property test over an independent corpus rather than another example.
