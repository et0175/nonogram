# CARD-496: The book routes' error paths: Finalise's other status refusals logged, the proof route's raw text, the referrer redirects, utcnow

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/496-book-route-error-paths
**Worktree:** —
**Source:** roadmap wave 5 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-101 WSJF 3.08, IDEA-015 WSJF 2.31; one card because both live in the same routes of src/nonogram/admin/app.py.
**Idea:** IDEA-101, IDEA-015
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, tests/test_book_*.py, tests/test_admin_*.py
**UI surface:** admin book Finalise and Print setup (flash messages, redirects)
**Review score:** —
**Started:** —
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
