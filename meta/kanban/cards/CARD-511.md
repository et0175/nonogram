# CARD-511: At 600x900 the board no longer moves when a puzzle is solved

**Status:** in_progress
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/511-solve-shift-600
**Worktree:** ../PythonProject4-card-511
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-223, recorded by CARD-507's implementer and review.
**Idea:** IDEA-223
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js (if the banner's reveal needs it), tests/test_puzzle_solver_maybe.py
**UI surface:** puzzle player (compact layout, solved banner)
**Review score:** —
**Started:** 2026-11-21T05:47Z
**Blocked by:** —

## Why this card exists

CARD-507 measured, at 600x900 in the compact layout, that the board moves dx +12.656, dy +27.203 px when a puzzle is solved, for all eight names it tried, including a 10-character one; identical before and after CARD-507, so pre-existing. At 1100x700 and 390x844 the board holds still (CARD-507's AC-1 and test_wraps). 600x900 is a portrait tablet. The player is the shared admin player and the public site's copy (one source of truth: change the admin static files only).

## What to implement

1. Reproduce in Chromium: the board's bounding box before and after solving at 600x900, and find which box change moves it (the banner appearing, a toolbar row wrapping, a column changing width). Record the cause measured, not guessed.
2. Fix it at that cause so the board does not move on solve at 600x900, without moving it at the widths that already hold (1100x700, 390x844), and without changing the layout before solve.
3. Hold it by extending an existing test (CARD-507's test_wraps or its neighbour in tests/test_puzzle_solver_maybe.py) with the 600x900 viewport, rather than adding a test.

## Acceptance criteria

* **AC-1**: at 600x900 the board's box is the same (within 0.5 px) before and after solve, for a short and a long name; control: the base CSS reds it with the measured shift.
* **AC-2**: at 1100x700 and 390x844 the existing no-move assertions still hold; the pre-solve layout at all three sizes is unchanged (board box within 0.5 px of base).
* **AC-3**: net test count 0 (a parameter, not a test, if the viewport is a param; report it, and if a node id is renamed record it in tests/test_browser_fixture_scope.py's `RENAMED_SINCE_BEFORE` as a move).

## Guardrails

* **G-1**: the browser-family census (tests/test_browser_fixture_scope.py) is a frozen registry outside impact scope: a new or renamed browser node id reds it at the gate. Re-derive, never paste the printed figure.
* **G-2**: admin static files only; nothing under player/ (the public site copies them at build).
* **G-3**: the owner validates renders after merge: leave before/after screenshots at the three sizes in ~/Documents/nonogram-reviews/CARD-511/.

## Worktree notes
