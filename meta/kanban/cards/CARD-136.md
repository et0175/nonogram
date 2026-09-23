# CARD-136: Print setup stores the chosen trim on the book

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/136-store-chosen-trim
**Worktree:** —
**Source:** CARD-115 / CARD-116 handover (gap found during wave 22-23, 2026-09-23)
**Idea:** —
**Wave:** 24
**Depends on:** CARD-116
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_trim_persistence.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Print setup validates the owner's trim and then throws it away: it writes only
`book.metadata.size` (a display string), never `books.trim_width_cm` /
`trim_height_cm`. The print columns are written exactly once, by `create_book`, so a
book whose trim the owner changed on Print setup still **prints on the Book 1 profile**
— the geometry, the cell size, the page pixels, all of it.

Two halves, and they must close together:

1. **Store it.** Add a `BookManager.set_print_spec(book_id, ...)` (both storage modes,
   as every other book_manager writer does) that writes the trim columns — and only
   those plus `updated_at` — and call it from `setup_print` after
   `PrintSpecValidator.create_spec` succeeds, in the same place the plan is saved
   (CARD-120). A refused plan must still not save the trim (AC-197's existing rule).
2. **Read it back consistently.** The Finalise screen reads `metadata.size` while the
   export reads the columns. After this card both must report the same trim, or a book
   will display one size and print another.

The export side is already done (CARD-116's `_export_part` passes the real Book), so a
book follows the stored columns the moment they are written.

CARD-115's `book_page_spec` already falls back to the Book 1 profile when the columns
are empty — keep that fallback for legacy books; this card is about new writes.

## Acceptance criteria

- AC-176 (now reachable): a 6 x 9 in book (trim 15.24 x 22.86 cm, Book 1 margins)
  holding a 15x15 puzzle with 7-deep clue gutters draws a 5.92 mm cell (+/- 0.05 mm),
  where the same puzzle on the 8.5 x 11 trim draws 7.5 mm.
  test: TestBookPdf_CellFollowsStoredTrim (exists; extend it to reach the trim through
  the Print setup route rather than a hand-built Book).
- AC-177 (now reachable): every page of that book's PDF is 1800 x 2700 px at 300 DPI.
  test: TestBookPdf_PageSizeEqualsStoredTrim (same note).
- New: setting the trim on Print setup and reopening the book shows the stored trim on
  both Print setup and Finalise, and the exported interior uses it.
  test: TestBookTrim_SetupPrintStoresAndExportFollows
- New: a submission whose plan is refused saves neither the plan nor the trim.
  test: TestBookTrim_RefusedPlanStoresNothing

## Guardrails

- G-1: `create_book`'s existing Book 1 profile defaults are unchanged — a book created
  and never edited keeps 21.59 x 27.94 cm with the CON-018 margins.
- G-2: `book_page_spec`'s profile fallback for legacy books (empty columns) is unchanged.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**`.
- G-4: `set_print_spec` writes no puzzle membership, order, titles or status
  (the INV-008 rule CARD-120's `save_plan` already respects).

## Architecture context

- **FR:** FR-030 (AC-176, AC-177), FR-031
- **CON:** CON-018
- **ADR:** ADR-0036
- **Components:** COMP-009, COMP-010
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Found by CARD-115 (handover) and confirmed by CARD-116, which deliberately
  left it (its G-4 forbade the book_manager write). Until this card lands, a
  UI-configured trim is display-only.

- [Handover from CARD-123, 2026-09-23] The Finalise Summary's "Trim size" row still reads book.metadata.size and renders nonsense like "8x10 x 27.94 cm" — it does not read the print columns the floor figure is measured against. Visible in ~/Documents/nonogram-reviews/CARD-123/finalize-after-trim-change.png. Closing that row is the display half of this card.
