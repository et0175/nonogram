# CARD-513: Two book-route minors: a no-puzzle book's download, and the plan tripwire logged twice

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/513-book-route-minors
**Worktree:** —
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-052 (wave-30 goal check) and IDEA-043 (CARD-153 F-009/F-011), bundled: each alone is below `sizing.min_estimate`.
**Idea:** IDEA-052, IDEA-043
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/books.html or book_detail.html, src/nonogram/admin/app.py, tests of the books list and Finalise
**UI surface:** books list, book detail (interior download button)
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-21T05:47Z
**Closed:** 2026-11-21T10:25Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** 2fdbf14d6a97de823658d21368beeef7619bc82f
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

- [IDEA-052, decided: disable on both] Premise re-verified by a recorded run (no-puzzle book, in-memory panel): `POST /book/<id>/download-pdf part=interior` answers 200 `application/pdf` of 3 pages (title page + the two guide pages, no puzzle), while `POST /book/<id>/generate-pdf` refuses the same book ("Cannot generate PDF for book with no puzzles", 302). No ADR, AC or card note found saying a puzzle-less interior is deliberate (text search of meta/architecture, meta/kanban/cards, docs; ADR-0035's only rule is "at least one puzzle before leaving draft"). So `books_list.html` now guards the row's interior form with the book page's own test, `book.puzzle_ids|length > 0`, and renders a disabled, form-less button otherwise. The `download-pdf` route itself is unchanged: it still serves the 3-page file to a direct POST (out of this card's scope). [Corrected in fix round 1: as first committed, Finalise still offered it; see below.]
- [AC-1] `TestBookPages_OfferBothExportFiles::test_a_book_with_no_puzzles_still_offers_its_cover` (tests/test_book_detail_page.py) now reads both `PAGES` (detail, list) in one loop, not a parametrize (0 net tests). Control: main's `books_list.html` reds it, `AssertionError: list` / `Left contains one more item: ({'action': '/book/book_000001/download-pdf', 'hidden': {'part': 'interior'}, 'parts': [{'part': 'interior', 'disabled': False}]}, ...)`.
- [IDEA-043 first half, already closed] The double log was closed by CARD-171: GET Finalise answers the helper's stamped plan failure itself (`_page_plan_failure_page`), so Flask never logs it. Re-verified: `TestFinaliseGet_NamesThePagePlanFailure::test_logs_it_once` and `TestFinaliseCounts_PlanTripwireIsNotAnEstimate::test_the_screen_shows_no_count_and_the_error_is_logged_with_its_traceback` pass; control (GET's `except` made a bare `raise`) reds all 4 cells with `assert 2 == 1`, the two records being the helper's "The page plan of book ... could not be built" and Flask's "Exception on /book/.../finalize [GET]". No code change.
- [AC-3, widened] An `ast` census of calls to `BookPDFGenerator`, `interior_generator`, `interior_stream`, `export_interior` and `puzzle_pages` under src/nonogram, plus a walk of `finalize_book`'s calls inside app.py, found a second layout lookup Finalise reaches: the `download_pdf` action goes `generate_book_pdf_download` -> `_export_part` -> `interior_generator`, which builds the generator `book_interior_vector` imports, not the one `nonogram.admin.app` looks up. Recorded red before widening: the spy saw `built == []` for that download. `_LayoutSpy` now patches both lookups (and passes the generator's writer kwargs through); its docstring states the scope, including that `book_proof`'s own lookup is not patched because Finalise does not call it.
- [AC-3 test, +1] `TestFinaliseGutter_NeverLaidOutAgainAtAnotherGutter::test_the_finalise_download_is_laid_out_once_on_its_stored_gutter` (tests/test_book_finalise_gutter.py). Control: deleting the `book_interior_vector` setattr reds it, `assert [] == ['0.70']`; the class's other 7 stay green.
- [AC-4] Net collected `tests/`: 10689 before, 10690 after (+1).
- [Gate] tests/test_book_detail_page.py tests/test_book_finalise_gutter.py tests/test_book_export_interior_cover.py tests/test_books_list_plan_stats.py tests/test_books_list_mobile.py tests/test_admin_error_text.py tests/test_book_finalise_guide_preview.py tests/test_kanban_review_record.py, `-o addopts= -rfs`: unarmed 497 passed, 0 failed, 0 skipped; armed (DATABASE_URL at this worktree's `nonogram_pythonproject4_card_513_f3c6003747aa_test` on localhost) 497 passed, 0 failed, 0 skipped. None of these files holds a database-backed test (their fixtures unset DATABASE_URL), so the armed run shows only that arming changes nothing here, not that the database was reached.

[Review 1/3] Score: 8.0, one gating finding, not certified. F-001 (gating) the Finalise page still offers the interior download for a no-puzzle book (`book_finalize.html`'s interior form has no guard; GET 200 with the button enabled, POST `download_pdf part=interior` 200 PDF), so "no page offers it now" is false and the "disable on both" decision reaches 2 of 3 places; F-002 (low) nothing pins the guard's edge: `> 1` in the list left the offering tests green (they build 3-puzzle books); F-003 (low) the list's disabled button gives its reason only in `aria-label`, against CARD-158's visible-muted-text rule and unlike `/book`'s "Add puzzles first."; F-004 (info) a direct POST still returns the 3-page PDF, out of scope. Confirmed by run: the same guard as book detail, the double log already closed by CARD-171, the second layout path and the widened spy, net +1.

### Fix round 1

- [F-001] `book_finalize.html`'s interior download form now sits behind the same `book.puzzle_ids|length > 0` guard; a no-puzzle book gets a disabled, form-less button with the book page's visible reason, "Add puzzles first.". Measured in the extended test below: on a no-puzzle book, the book page, the list and Finalise each render no interior form and exactly one disabled interior button, so none of the three pages offers the interior. The `download-pdf` route still serves the 3-page file to a direct POST (F-004, out of scope, unchanged). Control: main's `book_finalize.html` reds the test with `AssertionError: finalize` / `Left contains one more item: ({'action': None, 'hidden': {'action': 'download_pdf', 'part': 'interior'}, 'parts': [{'part': 'interior', 'disabled': False}]}, ...)`; main's `books_list.html` still reds it with `AssertionError: list`.
- [F-002] The same test, `TestBookPages_OfferBothExportFiles::test_a_book_with_no_puzzles_still_offers_its_cover`, now loops over detail, list and Finalise for a no-puzzle book AND a one-puzzle book, which must be offered an enabled interior form on each page. Planting `> 1` for `> 0` reds it on every guarded template: `book_detail.html` and `book_finalize.html` with `ValueError: not enough values to unpack (expected 1, got 0)` (the one-puzzle book's form is gone), and `books_list.html` with `AssertionError: list` (the one-puzzle row's button becomes a second disabled loose button). Each template was restored after its plant.
- [F-003] The list's disabled interior now has visible muted text beside it, "Add puzzles first." (same words as /book), and keeps its aria-label. The test asserts the text as element text (`>\s*Add puzzles first\.\s*<`) exactly once on each page for the no-puzzle book, and not at all on the detail and Finalise pages of the one-puzzle book. Control: deleting the list's span reds it, `AssertionError: list` / `assert 0 == 1`.
- [F-004] No change; still recorded as out of scope.
- [Count] Net collected `tests/`: 10690 (main 10689, +1, all from the round-0 spy test; this round adds none).
- [Gate] Unarmed, `-o addopts= -rfs`, written literally: tests/test_book_detail_page.py tests/test_book_finalise_gutter.py tests/test_book_export_interior_cover.py tests/test_books_list_plan_stats.py tests/test_books_list_mobile.py tests/test_admin_error_text.py tests/test_book_finalise_guide_preview.py tests/test_book_finalise_guide_preview_layout.py tests/test_book_cell_size.py tests/test_book_pdf_ink_mode.py tests/test_book_ready_gate.py tests/test_book_select_floor_tiles.py tests/test_book_uploaded_dividers.py tests/test_book_trim_persistence.py tests/test_book_workflow_steps.py tests/test_kanban_review_record.py (the earlier set plus every test file that GETs or POSTs `/finalize`): 1075 passed, 0 failed, 0 skipped.

[Review 2/3] Score: 9.5, nothing gating, certified. Cycle 1's F-001..F-003 closed and re-measured: `> 1` planted in each of the three guarded templates reds the extended no-puzzle test, deleting the list's reason reds it, main's `book_finalize.html` reds it, a duplicated reason reds it; only three templates post `part=interior`, each behind the guard; 455 passed, 0 skipped. F-001 (low): at 390 px "Add puzzles first." wraps to three lines and a no-puzzle book's row is 234 px tall (165 on main); no horizontal scroll, and the mobile test's 220 px row bound covers only its four-puzzle book. Left as recorded: the row belongs to a book that cannot be finalised yet. F-002 (info): cycle 1's F-004 carried (a direct POST still serves the 3-page file).

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 9016 passed / 30 skipped (the unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 13 deselected / 1 xfailed / 0 failed, then 11 passed marked (wave_close_only lifted by the diff).
