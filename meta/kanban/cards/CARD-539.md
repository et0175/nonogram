# CARD-539: An uploaded cover is held as one RGB page, so a transparent upload stays within the one-page memory bound

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/539-rgb-cover
**Worktree:** ../PythonProject4-card-539
**Source:** found 2026-11-24 by CARD-537 (IDEA-025, minor 2), which stopped on its own rule because the fix changes `src/`. Added to wave 17.
**Idea:** IDEA-025
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** CARD-537
**Touches:** src/nonogram/admin/book_pdf_generator.py (`BookPDFGenerator.create_cover_page`), tests/test_book_pdf_memory.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T08:40Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`BookPDFGenerator.create_cover_page` returns an uploaded cover as `cover_image.resize(...)`, which keeps the upload's mode. An RGBA upload (a PNG with transparency) is therefore held at 4 bytes a pixel. CARD-537 measured `export_book` through `tests/test_book_pdf_memory.py`'s own probe: peak 25,245,000 B with no upload and with an RGB upload, 33,660,000 B with an RGBA upload. All three held one page at a time. The RGBA peak is over the bound `test_the_whole_book_holds_one_page_bitmap_at_a_time` holds the book to. `_write_page` already converts every page to RGB as it writes, so the printed cover keeps no alpha today. No memory test feeds the cover any upload at all.

## What to implement

1. Before changing anything, export the cover page from an RGBA upload on main (with transparent and half-transparent regions) and record its digest. That is today's printed appearance.
2. Make `create_cover_page` hand back an RGB page for an upload in any mode, holding one page at 3 bytes a pixel.
3. The printed cover must not change: compare against step 1's digest. If converting before or after the resize changes the pixels (Pillow resamples RGBA with premultiplied alpha), keep today's pixels, for example by resizing first and converting after, inside `create_cover_page`. If today's pixels cannot be kept within the bound, stop and report: what a transparent region prints as is the owner's call.
4. Add the RGBA upload as a case of the existing whole-book memory test (a parameter, not a new test function). It must fail on main's `create_cover_page` and pass after the fix.
5. Update the docstring's "returned untouched" sentence to say what the code now does.

## Acceptance criteria

- AC-1: with an RGBA upload, `export_book`'s measured peak equals the no-upload peak, by the module's own probe.
- AC-2: the printed cover from an RGBA upload is byte-identical to main's (digest recorded before and after), or the card stopped and reported under step 3.
- AC-3: the new parameter fails on main's `create_cover_page` with its assertion text recorded, and passes on the branch.
- AC-4: owner's test budget: net tests at most +1 (one parameter), reported.

## Worktree notes
