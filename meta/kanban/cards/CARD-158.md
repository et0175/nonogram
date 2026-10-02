# CARD-158: The book list and book page show what the book actually holds

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-135 follow-up, CARD-130 handover, CARD-136 handover (backlog); templates re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 30
**Depends on:** —
**Touches:** src/nonogram/admin/templates/books_list.html, src/nonogram/admin/templates/book_detail.html, src/nonogram/admin/app.py, src/nonogram/admin/static/admin.css, tests/test_book_detail_page.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Four display gaps on `/books` and `/book/<id>`:

1. **Cover download is missing.** Since CARD-135 the export is two files, interior
   and cover, but `books_list.html:115` and `book_detail.html:73` only offer the
   interior. The route already serves the cover: `POST /book/<id>/download-pdf`
   with `part=cover` (`app.py:4407`). Only the buttons are missing.
2. **Puzzles appear as raw UUIDs.** `book_detail.html:117-120` renders
   `<code>{{ puzzle_id }}</code>` for each member, although every puzzle has a
   title (`custom_title`, falling back to `puzzle_name`, as Finalise does).
3. **The "Size" row is stale.** `book_detail.html:42` reads `book.metadata.size`,
   which Print setup no longer writes (CARD-136). It should show the stored trim
   from the book's print spec, or "not set" with a link to Print setup.
4. **The books table overflows at 390 px** (CARD-130 handover; not re-measured).

## What to do

1. Add a cover download next to the interior one on both pages. It follows the
   same lost-upload rule the route already applies (`_cover_upload_lost`).
2. Show each member puzzle's title (and tier, if it's cheap) instead of its id.
   Keep the id available, for example in a `title` attribute or a muted column,
   because the "Add puzzles by ID" form still uses ids. Read titles in one pass;
   if CARD-157 has landed, use `get_puzzles`.
3. Replace the Size row with the stored trim.
4. Make the books table fit a 390 px viewport (horizontal scroll inside the
   table wrapper is fine). Render it at 390 px and put the screenshot in
   `~/Documents/nonogram-reviews/CARD-158/` for the owner.

## Acceptance criteria

- **AC-1:** Both pages offer an interior download and a cover download, and the
  cover button submits `part=cover`.
  *test: TestBookPages_OfferBothExportFiles*
- **AC-2:** The book page lists member puzzles by title, not by id.
  *test: TestBookDetail_ListsPuzzlesByTitle*
- **AC-3:** The book page's size row shows the trim stored by Print setup, and
  "not set" for a book with no print spec.
  *test: TestBookDetail_ShowsTheStoredTrim*

## Guardrails

- G-1: No route, export or PDF behaviour changes; this card only changes templates
  and their view data.
- G-2: Use existing tokens and components only (no inline colours or sizes).
- G-3: The owner checks the rendered pages (see owner-validates-visually).

## Architecture context

- **FR:** FR-043 (two-file export), FR-030 (print setup)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Four small display leftovers from CARD-130, CARD-135 and CARD-136,
  grouped by the two screens they share. Cut on 2026-10-02.
