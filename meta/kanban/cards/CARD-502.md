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
