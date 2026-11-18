# CARD-478: The book selection page stops saying "approved" when it is showing every status

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/478-select-page-status-wording
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-143, WSJF 3.08); premise re-read against main on 2026-11-18. Origin: CARD-180 review, finding F-001.
**Idea:** IDEA-143
**Wave:** 80
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/_stepper.html, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_status_filter_default.py, tests/test_book_workflow_steps.py
**UI surface:** user-facing
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-18T15:24Z
**Closed:** 2026-11-18T19:01Z
**Actual:** 1c — ratio 1/1 = 1.000
**Merge commit:** 2af51e57f89bc75b10a25b77ab6ad1724b76f562
**Blocked by:** —

## Why this card exists

Under `?status=all` the selection page lists puzzles of every status, but its intro still reads "pick the approved grids" and the stepper subtitle "Pick approved grids". The page says one thing and shows another.

## What to implement

Make both strings follow the status the page is actually filtered to: the current wording when the filter is approved, a status-neutral wording otherwise. The stepper's step list is shared by every book page; the subtitle may simply become neutral everywhere ("Pick the grids") if that is the smaller change.

## Acceptance criteria

* **AC-1**: under `?status=all` neither the intro nor the stepper subtitle contains "approved".
* **AC-2**: under the default filter the intro still says the grids are the approved ones.
* **AC-3**: asserted in the existing `tests/test_status_filter_default.py`; net test count +1 at most.

## Guardrails

* **G-1**: the dashboard's "Select and arrange approved grids in a book" line is not this card's.
* **G-2**: the filter's behaviour is unchanged — wording only.

## Worktree notes

[Choice] The stepper's standing hint is unchanged; `book_steps` takes an optional `hints` map that only the selection page passes. Wider than AC-1 on purpose: "approved" is said only under the approved filter, so draft, rejected and unknown statuses read neutral too (reviewer: right, since none of them shows only approved tiles).
[Touches grew] `tests/test_book_workflow_steps.py`: its key check read `book_steps(N)` exactly and went red when the selection page passed a second argument; it now reads the first argument.
[Review 1/3] Score: 9.0, nothing gating, certified. Minor F-001 (only the current step's hint was read, so an override applied to all five steps passed) fixed after the cycle in `7d439d91`: no review cycle has seen that commit; the mutant it targets now reds, which is what the merge gate will re-run, nothing more.
[Not carded, reviewer F-002] Under a filter other than `all` and `approved`, an empty tab still says "No approved puzzles…" — CARD-180's branch tests `status == 'all'`, this card's wording tests `status == 'approved'`. Pre-existing; matters only if the owner wants the empty-tab copy to follow too.
[Merge gate] `make test-gate` on the tip rebased onto CARD-477's merge: run 1, 8999 passed, 30 skipped (29 database-not-set, 1 setrlimit), 13 deselected, 1 xfailed, of 9041 selected; run 2 (wave_close_only), 11 passed; exit 0.
[Estimate] 1c estimated, 1 cycle used.
