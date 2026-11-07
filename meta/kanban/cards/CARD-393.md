# CARD-393: How to Solve says where the code is — one line under the guide's intro, with the Play online page's real number

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner decision 2026-11-07, version B, "How to Solve mentions it up front": "The front pages are what Amazon's preview shows, so the guide gets one line under its intro: 'Every puzzle in this book can also be played online. Scan the code on page 167.' It's a selling point in the preview, without putting the link there."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-390, CARD-229
<!-- CARD-229 (the guide as a facing spread on pages 2 and 3, ready, unstarted) re-lays the guide's intro and frame; this line belongs under the intro it produces. If the owner wants this line sooner, drop the CARD-229 edge and accept that CARD-229 then re-seats one line. -->
**Touches:** src/nonogram/admin/book_guide_vector.py, src/nonogram/admin/book_interior_vector.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, docs/guides/how-to-solve-nonograms.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The Play online page sits at the back, deliberately outside Amazon's preview (the owner's reasoning in version B). The front pages are what the preview shows, so the guide is the one place the book can say, without printing a link, that the puzzles can be played online and where to scan. The page number is the Play page's real folio, known from the page plan (CARD-390), so this card computes nothing and prints nothing a changed page count could falsify.

## What to implement

1. The guide writer (`book_guide_vector.py`, called through `InteriorPageWriters.guide` from `book_pdf_generator.py`) takes the Play page's interior page number (`None` when the book prints no Play page) and sets one line under the guide's intro: `Every puzzle in this book can also be played online. Scan the code on page {X}.` At or above the interior type floor, in the guide's own face and column, position from the guide's layout (not a new coordinate in the writer).
2. No Play page (no stored domain): the line is absent, and the guide is exactly today's. The line never appears for a page that was not printed (ADR-0041/R8).
3. The guide stays two pages. If the line makes the intro overflow its page on any admitted trim, the intro's spacing yields, never the line, and the author states the margin that remains.
4. `docs/guides/how-to-solve-nonograms.md` is touched only if it is the text the writer reads; the author states whether it is, and if so the sentence appears there with the page number as a described variable.

## Acceptance criteria

- **AC-1** (happy): *Given* a book with a Play page at interior page 167, *then* the guide's text layer holds the sentence with `167` exactly, below the intro and above the first technique heading. (test: `TestGuidePage_NamesThePlayPage`)
- **AC-2** (guard, true number): *Given* books of several sizes, *then* the number in the guide equals the interior page number of the PLAY page in the exported PDF, read from the PDF. (test: `TestGuidePage_PlayPageNumberIsTheRealOne`)
- **AC-3** (negative, no domain): *Given* a book with no stored domain, *then* the guide has no such line and its text equals the guide on main before this card. (test: `TestGuidePage_NoPlayPageNoLine`)
- **AC-4** (edge, fit): *Given* every trim in CON-018's profile set, *then* the guide is still two pages and the line overlaps no other guide mark. (test: `TestGuidePage_TheLineFitsEveryTrim`)
- **AC-5** (guard, type floor): *Given* the line, *then* it is at or above the interior type floor. (test: `tests/test_book_guide_page_type.py` floor cell, extended to the new line)
- **AC-6** (guard, preview): *Given* the interior, *then* the first QR-bearing page is not within the first pages Amazon previews: the guide carries no code, only the sentence (this is a restatement of ADR-0041/R8 against this page). (test: `TestGuidePage_CarriesNoQr`)

## Guardrails

- G-1: No link, URL or QR on the guide (the owner's reason for the line).
- G-2: The page number is read from the plan; never typed, never derived from the puzzle count here.
- G-3: Guide page count unchanged (KDP band and gutter depend on it).

## System contract

- ADR-0041/R8 — pointer only with the page, one QR in the book (check: review-lens until CARD-391 flips it)
- ADR-0042/R1 — the guide is PDF operators (check: the rule's own ref)

## Architecture context

- **FR:** FR-041 (the guide).
- **Sequencing:** after CARD-229/CARD-230 (the guide spread and its worked example) so the line is laid once.

## Worktree notes

(none yet)
