# CARD-480: A failed admin action tells the user what to do, and the exception text goes to the log

**Status:** ready
**Priority:** P2
**Category:** compliance
**Estimate:** 3c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-130, WSJF 2.0); premise re-read against main on 2026-11-18. Origin: CARD-177 drafting note.
**Idea:** IDEA-130
**Wave:** —
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, tests/test_admin_error_text.py
**UI surface:** user-facing
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-177 stopped the PDF download from showing raw exception text. The rest of `src/nonogram/admin/app.py` still does it: about 38 sites flash or return `str(e)` — `delete_book` (a pure database call, so the text is a driver error), the proof pages, cover upload, batch upload and generate, and the API routes that answer a 500 with `Error: <exception>` as plain text. Driver and path text reaches the browser, and the user is told nothing they can act on.

## What to implement

Sort the sites into two kinds, by `ast` and not by eye: (a) a domain refusal the user caused and can fix (`NonogramError` subclasses, form errors) — its message is written for the user and stays; (b) anything else — the user sees a fixed sentence naming the action that failed, the exception is logged with its traceback. Follow the pattern CARD-177 set for the PDF download — a named fixed-text constant (`PDF_EXPORT_FAILED`, `FINALISE_ACTION_FAILED`) plus `app.logger.exception` — rather than a second mechanism. The 500 template and the plain-text API bodies follow the same rule.

## Acceptance criteria

* **AC-1**: for every handler in `app.py` that catches a non-domain exception, a planted exception whose message is a marker string never reaches the response body or a flash — the population of handlers is derived by `ast`, and the cell asserts a minimum count so it cannot silently shrink.
* **AC-2**: a domain refusal still reaches the user with its own message (one control per kind of surface: flash, JSON, plain text).
* **AC-3**: the planted exception is in the log with its traceback.
* **AC-4**: HTTP status codes are unchanged for every route touched.
* **AC-5**: tests extend `tests/test_admin_error_text.py`; net test count reported.

## Guardrails

* **G-1**: no route, redirect target or status code changes — text only.
* **G-2**: `_PlanFormError` and the other form-error paths are user-facing by design and are kind (a).
* **G-3**: `app.py` is a hotspot: the card does not run beside CARD-477.
* **G-4**: at 3c this is the wave's largest card; if the `ast` sort finds the two kinds cannot be told apart for a group of sites, stop and report the group rather than guess.

## Worktree notes

—
