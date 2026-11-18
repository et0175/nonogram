# CARD-478: The book selection page stops saying "approved" when it is showing every status

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-143, WSJF 3.08); premise re-read against main on 2026-11-18. Origin: CARD-180 review, finding F-001.
**Idea:** IDEA-143
**Wave:** —
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/_stepper.html, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_status_filter_default.py
**UI surface:** user-facing
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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

—
