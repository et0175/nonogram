# CARD-502: The admin's remaining error paths: the status route's raw text, log-before-flash untested, the double flash, a refused New book's alert

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/502-admin-error-paths
**Worktree:** ../PythonProject4-card-502
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-138, IDEA-023, IDEA-050 (each WSJF 2.31) plus CARD-496's out-of-scope F-003 (recorded at the wave-5 close); one card because all are error paths of src/nonogram/admin/app.py.
**Idea:** IDEA-138, IDEA-023, IDEA-050
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_*.html, tests/test_admin_error_text.py, tests/test_book_*.py
**UI surface:** admin book status change, PDF download, New book (flash messages, alerts)
**Review score:** —
**Started:** 2026-11-20T15:14Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **CARD-496 F-003 (recorded 2026-11-20).** `update_book_status` catches `ValueError` and flashes `f"Error: {str(e)}"` with no log line: the same raw-text shape CARD-480 and CARD-496 removed from the other handlers. Re-read on main 2026-11-20: still there.
2. **IDEA-138 (CARD-177 F-001/F-002, OOS-3).** No test asserts that a handler logs BEFORE it flashes; the AC-2 redirect is tested only without a Referer; `/generate-pdf` can show both a success and a failure flash when sending the file fails.
3. **IDEA-023 (CARD-140 F-006).** `puzzle_section`'s `ValueError("ids must be parallel to payloads")` is a caller precondition, but it lands in the arrange route's WARNING clause with no traceback. Unreachable today.
4. **IDEA-050 (CARD-159 F-002/F-003).** No route-level test for a below-minimum, zero or negative trim (the server refuses them since the browser `min` went); a refused New book shows the edit-mode alert ("General info not saved… Nothing stored was changed"), which is wrong when nothing was ever stored.

## What to implement

Re-verify each against main first, in a recorded run; drop any already closed with one line in the notes.

1. `update_book_status`: classify its refusals as CARD-496 did for Finalise (an owner refusal keeps a sentence the owner acts on, unlogged; anything else shows fixed text and is logged). Reuse CARD-496's mechanism by name; do not invent a second one.
2. One test pins log-before-flash ordering for a handler error (extend tests/test_admin_error_text.py), and the redirect case also runs WITH a same-site Referer.
3. `/generate-pdf` never shows a success flash for a download that failed.
4. The precondition `ValueError` either is logged with its traceback or is no longer caught by the WARNING clause (a programming error should not read as an owner refusal).
5. A refused New book shows an alert that does not claim something stored was kept; route tests for below-minimum, zero and negative trims (parametrise an existing test).

## Acceptance criteria

* **AC-1**: `update_book_status` with a non-owner failure shows fixed text and writes a log record; an owner refusal keeps its sentence; control: the old handler reds it.
* **AC-2**: a test reds if the handler flashes before it logs (control: swap the two calls).
* **AC-3**: a failed PDF send leaves no success flash (control: the old order reds).
* **AC-4**: the puzzle_section precondition reaches a log record carrying a traceback, or propagates; control reds.
* **AC-5**: the refused New book alert's text is pinned; the three trim refusals are pinned at the route.
* **AC-6**: net test count at most +2; report it.

## Guardrails

* **G-1**: owner-facing wording changes only where a refusal becomes an error, or for the New book alert; every other message's text is unchanged.
* **G-2**: DB-mode tests run armed at the worktree's own `_test` database; report skips with `-rfs`.

## Worktree notes
[Premises] All five re-verified open on the branch before any change, by a recorded probe run (memory mode; /private/tmp/claude-501/card502/probe_premises.py): `update_book_status` flashed `Error: Invalid status: bogus` and a planted ValueError's raw text (`password=hunter2 …`), 0 log records; `/generate-pdf` with `send_file` failing flashed `PDF generated successfully!` AND `PDF_EXPORT_FAILED`; the arrange screen given one id too few logged `No page plan …: ids must be parallel to payloads` at WARNING with no traceback; a refused New book showed the edit-mode alert ("Nothing stored was changed"); zero and negative trims are refused by the server, and no test posts either (below-minimum in inches was already pinned by CARD-174's `test_a_side_under_the_minimum_says_inches_and_quotes_the_entry`). Log-before-flash: with Finalise's two calls swapped, main's tests/test_admin_error_text.py stayed green on the ordering (its one red was the census of this card's new handler); the branch's version reds. None dropped.
[Item 1] `update_book_status` now catches `StatusRefusal` (CARD-496's class, by name) and flashes `Error: <sentence>`, unlogged; anything else (`except Exception`) is logged with `app.logger.exception` and then shows the new `STATUS_CHANGE_FAILED` ("The book's status could not be changed. The details are in the panel's log."). Previously a non-ValueError was unhandled (500). Wording changes only for faults (G-1).
[Item 3] `generate_book_pdf` builds the response (`_send_export_part`) before `set_pdf_url` and the success flash; a failed send therefore also records no pdf_url.
[Item 4] `BookPDFGenerator.puzzle_section` and `puzzle_pages` raise `AssertionError` (not `ValueError`) for the ids-parallel precondition, so the arrange route's `(RuntimeError, ValueError)` warning clause no longer takes it; it reaches the `except Exception` clause, logged at ERROR with its traceback. The declared-failure warning (`test_the_declared_failure_is_logged_as_a_warning`) is unchanged.
[Item 5] book_create.html: in create mode the alert reads "Book not created: correct the field marked below. Your other entries are kept as you typed them."; edit mode keeps its text.
[Tests] Extended, none added. tests/test_admin_error_text.py: `SEAMS` gains `status_route` (appended; the corpus asserts it is reached with a ValueError, case 58), `_PLANTED_BY_CARD_177` gains `update_book_status`, `_BROAD_HANDLER_FLOOR` 22 -> 23, and the corpus records every `flash` with how often the error had been logged by then (must be `[1]`); `TestBookPdfDownload_ErrorIsGenericAndLogged::test_the_flash_is_the_constant_and_the_error_is_logged` also fails `send_file` under a same-site Referer and asserts the flashes are exactly `[("error", PDF_EXPORT_FAILED)]` and the Location is the Referer (finalise, download-pdf) or the book page (generate-pdf). test_book_ready_gate `test_the_status_route_flashes_it`: one flash, no ERROR record. test_book_arrange_page_breaks `test_a_bug_in_the_seam_itself_is_logged_with_its_traceback`: second case, the real precondition reached with one id short. test_book_workflow_steps `test_the_create_screen_marks_like_the_edit_screen`: both alert texts pinned; `test_a_side_under_the_minimum_says_inches_and_quotes_the_entry` parametrised over 3, 0, -2 (inches).
[Controls] Each mutation applied, named tests run, file restored (`git diff --stat` unchanged after). C1 old `except ValueError` handler: corpus RED (unhandled `RuntimeError: could not connect …` at the status seam) and `test_no_broad_handler…` RED (`assert 22 >= 23`); `test_the_status_route_flashes_it` stays green (the old handler showed refusals too). C1c old ValueError clause kept, faults handled: corpus RED `AssertionError: (58, 'status_route', 'ValueError')` (the password reached the flash). C1b `StatusRefusal` clause removed: `test_the_status_route_flashes_it` RED (only `STATUS_CHANGE_FAILED` flashed). C2 flash before log in `update_book_status`: corpus RED `((6, 'status_route', 'RuntimeError'), [(…, 0)])` / `assert [0] == [1]`; the same swap in `finalize_book` reds it at case 0 (`clear_cover`). C3 success flash before the send: `[generate-pdf]` RED (`[('success', 'PDF generated successfully!'), ('error', …)]`). C3b `_same_site_back` ignoring the Referer: `[finalise]` and `[download-pdf]` RED (`'/book/book_000002' == 'http://localhost/book/book_000002/finalize'`). C4 both raises back to ValueError: the seam test RED on its `puzzle_section` case (`assert []`, WARNING only); its `section_plan` case stays green. C5 alert `{% if true %}`: `test_the_create_screen_marks_like_the_edit_screen` RED (create shows "General info not saved … Nothing stored was changed"). C5b minimum check disabled in print_specs: all three `[3]`, `[0]`, `[-2]` RED (`assert 302 == 200`).
[Gate] Ring 1 (14 files): test_admin_error_text, test_book_arrange_page_breaks, test_book_ready_gate, test_book_workflow_steps, test_book_create, property/test_book_workflow, test_puzzle_review_bulk_read, test_player_bundle, test_book_pdf_levels, test_book_pdf_two_up, property/test_book_pairing, test_book_finalise_gutter, test_book_trim_persistence, test_book_proof_pages: unarmed 873 passed, 0 skipped; armed (plus test_db_e2e_smoke, which unarmed is 6 skipped "DATABASE_URL is not set") at nonogram_pythonproject4_card_502_ac9daeef7dd6_test: 879 passed, 0 skipped. Ring 2 (6 files naming a changed surface): property/test_book_export_interior, test_book_detail_page, test_book_export_interior_cover, test_book_landing_address, test_book_metadata_column, test_puzzle_edit_routes: unarmed 303 passed, 4 skipped (all "Database not reachable: DATABASE_URL is not set"); armed 307 passed, 0 skipped.
[AC-6] Net collected count: 10711 before, 10713 after (+2, the two new trim parameters).
