# CARD-513: Two book-route minors: a no-puzzle book's download, and the plan tripwire logged twice

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/513-book-route-minors
**Worktree:** ../PythonProject4-card-513
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-052 (wave-30 goal check) and IDEA-043 (CARD-153 F-009/F-011), bundled: each alone is below `sizing.min_estimate`.
**Idea:** IDEA-052, IDEA-043
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/books.html or book_detail.html, src/nonogram/admin/app.py, tests of the books list and Finalise
**UI surface:** books list, book detail (interior download button)
**Review score:** 8.0 (cycle 1/3)
**Started:** 2026-11-21T05:47Z
**Blocked by:** —

## Why this card exists

1. **IDEA-052.** On a book with no puzzles, /books offers the interior download (it returns a 200 PDF), while /book/<id> disables the same button. The two pages disagree and no AC covers either. Decide by what the download produces: if a no-puzzle interior is a valid PDF a user might want, /book should offer it; if not, /books should not. Prefer the more conservative (disable on both) unless the code shows the empty PDF is deliberate; say which and why.
2. **IDEA-043.** A plan tripwire on GET Finalise is logged twice (the helper logs, then Flask logs the same error). Also, the G-1 "never laid out again" spy only sees layouts through `BookPDFGenerator`, which is the only layout path today per ADR-0036/R2; record that scope in the test's docstring instead of widening the spy, unless a second path exists.

## What to implement

Re-verify each against main first; drop anything already closed, with one line in the notes.

## Acceptance criteria

* **AC-1**: on a no-puzzle book the two pages agree about the interior download, and an existing books-list or book-detail test asserts it (control: main's template reds it).
* **AC-2**: the tripwire is logged once (control: main's double log reds a caplog count).
* **AC-3**: the spy's scope is stated truthfully in its docstring (or widened if a second layout path exists, found by `ast`).
* **AC-4**: net test count at most +1; report it.

## Guardrails

* **G-1**: run the database-backed selection armed (at the worktree's own `*_test` database) and unarmed, and report both with `-rfs`.
* **G-2**: never connect to the production database.

## Worktree notes

- [IDEA-052, decided: disable on both] Premise re-verified by a recorded run (no-puzzle book, in-memory panel): `POST /book/<id>/download-pdf part=interior` answers 200 `application/pdf` of 3 pages (title page + the two guide pages, no puzzle), while `POST /book/<id>/generate-pdf` refuses the same book ("Cannot generate PDF for book with no puzzles", 302). No ADR, AC or card note found saying a puzzle-less interior is deliberate (text search of meta/architecture, meta/kanban/cards, docs; ADR-0035's only rule is "at least one puzzle before leaving draft"). So `books_list.html` now guards the row's interior form with the book page's own test, `book.puzzle_ids|length > 0`, and renders a disabled, form-less button otherwise. The `download-pdf` route itself is unchanged: it still serves the 3-page file to a direct POST (out of this card's scope; no page offers it now).
- [AC-1] `TestBookPages_OfferBothExportFiles::test_a_book_with_no_puzzles_still_offers_its_cover` (tests/test_book_detail_page.py) now reads both `PAGES` (detail, list) in one loop, not a parametrize (0 net tests). Control: main's `books_list.html` reds it, `AssertionError: list` / `Left contains one more item: ({'action': '/book/book_000001/download-pdf', 'hidden': {'part': 'interior'}, 'parts': [{'part': 'interior', 'disabled': False}]}, ...)`.
- [IDEA-043 first half, already closed] The double log was closed by CARD-171: GET Finalise answers the helper's stamped plan failure itself (`_page_plan_failure_page`), so Flask never logs it. Re-verified: `TestFinaliseGet_NamesThePagePlanFailure::test_logs_it_once` and `TestFinaliseCounts_PlanTripwireIsNotAnEstimate::test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback` pass; control (GET's `except` made a bare `raise`) reds all 4 cells with `assert 2 == 1`, the two records being the helper's "The page plan of book ... could not be built" and Flask's "Exception on /book/.../finalize [GET]". No code change.
- [AC-3, widened] An `ast` census of calls to `BookPDFGenerator`, `interior_generator`, `interior_stream`, `export_interior` and `puzzle_pages` under src/nonogram, plus a walk of `finalize_book`'s calls inside app.py, found a second layout lookup Finalise reaches: the `download_pdf` action goes `generate_book_pdf_download` -> `_export_part` -> `interior_generator`, which builds the generator `book_interior_vector` imports, not the one `nonogram.admin.app` looks up. Recorded red before widening: the spy saw `built == []` for that download. `_LayoutSpy` now patches both lookups (and passes the generator's writer kwargs through); its docstring states the scope, including that `book_proof`'s own lookup is not patched because Finalise does not call it.
- [AC-3 test, +1] `TestFinaliseGutter_NeverLaidOutAgainAtAnotherGutter::test_the_finalise_download_is_laid_out_once_on_its_stored_gutter` (tests/test_book_finalise_gutter.py). Control: deleting the `book_interior_vector` setattr reds it, `assert [] == ['0.70']`; the class's other 7 stay green.
- [AC-4] Net collected `tests/`: 10689 before, 10690 after (+1).
- [Gate] tests/test_book_detail_page.py tests/test_book_finalise_gutter.py tests/test_book_export_interior_cover.py tests/test_books_list_plan_stats.py tests/test_books_list_mobile.py tests/test_admin_error_text.py tests/test_book_finalise_guide_preview.py tests/test_kanban_review_record.py, `-o addopts= -rfs`: unarmed 497 passed, 0 failed, 0 skipped; armed (DATABASE_URL at this worktree's `nonogram_pythonproject4_card_513_f3c6003747aa_test` on localhost) 497 passed, 0 failed, 0 skipped. None of these files holds a database-backed test (their fixtures unset DATABASE_URL), so the armed run shows only that arming changes nothing here, not that the database was reached.

[Review 1/3] Score: 8.0, one gating finding, not certified. F-001 (gating) the Finalise page still offers the interior download for a no-puzzle book (`book_finalize.html`'s interior form has no guard; GET 200 with the button enabled, POST `download_pdf part=interior` 200 PDF), so "no page offers it now" is false and the "disable on both" decision reaches 2 of 3 places; F-002 (low) nothing pins the guard's edge: `> 1` in the list left the offering tests green (they build 3-puzzle books); F-003 (low) the list's disabled button gives its reason only in `aria-label`, against CARD-158's visible-muted-text rule and unlike `/book`'s "Add puzzles first."; F-004 (info) a direct POST still returns the 3-page PDF, out of scope. Confirmed by run: the same guard as book detail, the double log already closed by CARD-171, the second layout path and the widened spy, net +1.
