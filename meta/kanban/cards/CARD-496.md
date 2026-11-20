# CARD-496: The book routes' error paths: Finalise's other status refusals logged, the proof route's raw text, the referrer redirects, utcnow

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/496-book-route-error-paths
**Worktree:** ../PythonProject4-card-496
**Source:** roadmap wave 5 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-101 WSJF 3.08, IDEA-015 WSJF 2.31; one card because both live in the same routes of src/nonogram/admin/app.py.
**Idea:** IDEA-101, IDEA-015
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, tests/test_book_*.py, tests/test_admin_*.py
**UI surface:** admin book Finalise and Print setup (flash messages, redirects)
**Review score:** —
**Started:** 2026-11-20T09:21Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-101 (CARD-171 note).** Finalise catches `ValueError` around `book_mgr.set_book_status` and flashes it (`flash(f"Error: {gate_refusal}")`) with no log line. Only the plan-gate refusal is tested; `set_book_status`'s other refusals (already published, no puzzles, an invalid status) reach the same flash, unlogged. Decide per refusal whether it is an owner refusal (a sentence the owner acts on, no log) or an error (fixed text, logged), as CARD-480 did for the other handlers.
2. **IDEA-015 (CARD-118 minors).** Re-verified 2026-11-20: two `redirect(request.referrer or url_for(...))` sites remain in app.py (the PDF download and a setup-print path), taking the target from the caller; book_manager.py has 22 `datetime.utcnow()` calls (deprecated since Python 3.12). The proof route's broad `except Exception` flashing raw text may already be closed by CARD-480 (a failed admin action shows fixed text); check it first.

## What to implement

Re-verify each against main first; drop any already closed with one line in the notes.

1. Each `set_book_status` refusal Finalise can meet is classified; owner refusals keep a sentence the owner can act on, errors show fixed text and are logged (CARD-480's pattern, by name).
2. The two referrer redirects go to a fixed, same-site target (or a validated same-origin referrer); an off-site Referer never becomes a redirect target.
3. `datetime.utcnow()` replaced by an aware UTC timestamp wherever the stored value's meaning is unchanged; if a column stores naive UTC, keep it naive (`datetime.now(timezone.utc).replace(tzinfo=None)`) and say so; no schema change.

## Acceptance criteria

* **AC-1**: each refusal class has a test that pins its flash text and whether a log record is written; control: the old handler reds it.
* **AC-2**: a request with an off-site `Referer` is redirected to the fixed target; control: the old `request.referrer or` reds it.
* **AC-3**: no `datetime.utcnow(` left in src/ (ast), and the stored timestamps compare equal in kind (naive/aware) to before, by a test that already reads them or one assertion added to it.
* **AC-4**: net test count at most +2; report it.

## Guardrails

* **G-1**: no schema change; DB-mode tests run armed at the worktree's own `_test` database, skip counts reported with `-rfs`.
* **G-2**: owner-facing wording only changes where a refusal becomes an error; the plan-gate refusal's text is unchanged.

## Worktree notes

[Implementation] Premises re-verified on the branch before any change (ast, probe runs): Finalise's `save_and_finish` caught every `ValueError` from `set_book_status` and from the read-only gate call, flashing `Error: <text>` with no log; the two `request.referrer or url_for(...)` sites are `generate_book_pdf_download` and `download_book_proof_pages`; `datetime.utcnow` appeared as 33 calls in src/ (book_manager 22, batch_generator 8, app 2, image_manager 1) plus 5 `default_factory=datetime.utcnow` references (book_manager 2, batch_generator 3).
[Already closed] The proof route's broad `except Exception` flashing raw text: closed by CARD-480 (`download_book_proof_pages` shows `PROOF_PAGES_FAILED` for anything but the ValueError refusal CARD-118 keeps; pinned by `test_a_planted_failure_shows_fixed_text_and_is_logged[proof]`). Not changed here.
[AC-1 classification] The `ValueError`s `set_book_status` can raise on the Finalise path, each reproduced by a probe run on the branch: owner refusals — "Cannot change status of published book" (a published book), "Must have puzzles before advancing status" (an empty book: reached, because an empty book is countable), the plan gate's (`NO_PLAN_REFUSAL`, off-plan cells); faults — `UNREADABLE_SELECTION_REFUSAL` (no puzzle store: a wiring error), "Invalid status" (unreachable from Finalise, which passes a constant), and any library `ValueError` inside the call. New `book_manager.StatusRefusal(ValueError)` is raised for the owner refusals only; `finalize_book` catches `StatusRefusal` at both sites (the gate call and `set_book_status`), so a fault falls through to the route's outer handler: logged with its traceback, `FINALISE_ACTION_FAILED` shown (CARD-177/CARD-480's rule). Wording changes only for the faults (the no-store sentence now shows fixed text); the plan-gate and the two other refusals' texts are unchanged. Other `set_book_status` callers still catch `ValueError` and are unaffected.
[AC-1 tests] Owner class: `TestFinalisePost_PlanGateRefusalIsNotAnError::test_the_refusal_is_flashed_and_nothing_is_logged` gains `[published]` and `[no-puzzles]` and now also asserts `FINALISE_ACTION_FAILED` is absent. Error class: `test_PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen` gains a sixth seam, `set_book_status`, placed so a `ValueError` (holding a fake credential) lands there, asserted by the test.
[AC-2] `_same_site_back(fallback)` (module level, app.py): the `Referer` when it is an http/https URL whose authority equals the request's `Host`, else the `url_for` fallback; used by `generate_book_pdf_download` and `download_book_proof_pages`. Tests: `TestBookPdfDownload_ErrorIsGenericAndLogged::test_the_flash_is_the_constant_and_the_error_is_logged` now sends an off-site Referer; `test_a_domain_refusal_still_says_what_it_is` sends an off-site Referer (lands on setup-print) and a same-site one (kept).
[AC-3] Each of book_manager, batch_generator and image_manager has its own `_utc_now()` = `datetime.now(timezone.utc).replace(tzinfo=None)` (one per module: no lateral import). Naive kept on purpose: every timestamp column is a naive `DateTime` (db/models.py, migrations), and in-memory values are compared with naive values (`list_batches`' `strptime` bounds) and serialised by `isoformat()` (an aware value would add `+00:00`). app.py's two download-name stamps use `datetime.now(timezone.utc).strftime(...)`, the same string. No schema change. ast finds 0 `utcnow` calls left in src/. Kind pinned by one assertion added to `TestSetPrintSpec_WritesOnlyTheTrim::test_nothing_but_the_trim_columns_moves` (`updated_at.tzinfo is None`, before and after a write).
[Controls] Each mutation applied, the named test run, the file restored (`git diff --stat` unchanged after). C1 `except StatusRefusal` -> `except ValueError` (both sites): the corpus test RED, `AssertionError: (4, 'set_book_status', 'ValueError')` / `assert 'fake…' not in '<!DOCTYPE h…'` (the credential reached the page). C2 the five `raise StatusRefusal(` -> `raise ValueError(`: all four refusal params RED (`assert 'x medium: 0% against 100%' in …` x2, `assert 'Error: Cannot change status of published book' in …`, `assert 'Error: Must have puzzles before advancing status' in …`). C3 both `_same_site_back(...)` -> `request.referrer or ...`: `[finalise]`, `[download-pdf]` and `test_a_domain_refusal_still_says_what_it_is` RED; `[generate-pdf]` stays green under the control because `generate_book_pdf` never used the referrer (fixed `book_detail` redirects). C4 `_utc_now` returning aware: `test_nothing_but_the_trim_columns_moves[memory]` RED; `[db]` (sqlite) stays green under the control, so the kind is pinned in memory mode only.
[Gate] 18 files: tests/test_admin_error_text.py, test_book_finalise_gutter.py, test_book_trim_persistence.py, and neighbours test_book_manager.py, test_book_ready_gate.py, property/test_book_ready_gate.py, test_book_published_confirm.py, test_book_proof_pages.py, test_book_plan_storage.py, test_batch_generator.py, test_batch_history.py, test_admin_rename_strategies_batches.py, test_admin_review_actions.py, test_card_108_delete_book_releases.py, test_cli.py, test_approval_guess_gate.py, test_puzzle_edit_routes.py, test_db_e2e_smoke.py. Unarmed: 1012 passed, 10 skipped (all "Database not reachable: DATABASE_URL is not set"). Armed at nonogram_pythonproject4_card_496_d4fd2b8d3e8c_test: 1022 passed, 0 skipped.
[AC-4] Net collected count: 10708 before, 10710 after (+2).
