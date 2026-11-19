# CARD-486: The four CARD-183 hint minors, verified against today's ladder and fixed only where still live

**Status:** review
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/486-hint-minors
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-486
**Source:** roadmap rescore 2026-11-18, wave 3 (IDEA-149, WSJF 1.54, `verify_before_carding: true`); carried from wave 1, where it was held for verification.
**Idea:** IDEA-149
**Wave:** 82
**Created wave:** 82
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_hint.py
**UI surface:** admin solve page and public player (hint ladder)
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-19T17:49Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-183's review left four minors (F-011..F-014): two polite announcements per hint; Hint pressed by keyboard while the reset confirm is open moves focus to Reset; a 440 ms animation-test window; after Undo the announce region keeps the old hint's text. Since then the hint became a three-rung ladder (CARD-269), its text moved twice (CARD-409, CARD-455) and CARD-484 changed which cell it picks. None of the four was re-tested, so each may be moot.

## What to implement

1. **Verify first, in a real browser** (the player test fixtures), each of the four on today's ladder. Record per item: live or moot, with the command or test that showed it.
2. Fix only the live ones. A moot item gets one line in the notes and no code.
3. If all four are moot, the card closes with the notes alone.

## Acceptance criteria

* **AC-1**: each of F-011..F-014 has a recorded verdict (live / moot) backed by a browser observation, never by reading code alone.
* **AC-2**: every live item is fixed and has one control that reds when the fix is reverted.
* **AC-3**: owner's test budget: change existing tests rather than add; net test count at most +2; report it.

## Guardrails

* **G-1**: the ladder's rungs, wording and the cell CARD-484 picks are unchanged.
* **G-2**: the public player's pages and payloads change only if a live fix requires it, and then by the same edit as the admin (one source of truth, 2026-11-07).
* **G-3**: not published until the owner asks.

## Worktree notes

—
