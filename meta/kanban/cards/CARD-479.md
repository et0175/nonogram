# CARD-479: The clue bands are re-measured whenever the stage's own box changes

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-209, WSJF 4.62); premise re-read against main on 2026-11-18. Origin: CARD-271 review cycle 2, residual of finding F-001.
**Idea:** IDEA-209
**Wave:** —
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py
**UI surface:** user-facing
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`keepCluesInView()` must run whenever `.player-stage` changes size, or a clue band can be left cut off. Today it runs from a `ResizeObserver` on the toolbar, `.player-head` and `document.body`, keyed on the stage's top and the toolbar's width — the things known to move the stage. Anything else that changes the stage's box is covered only as long as nobody adds one; CARD-271 hunted for such a case, found none, and named observing the stage itself as the fix that holds by construction.

## What to implement

Observe `.player-stage` directly and re-measure on a change of its box. The existing observer's key is narrow for a reason: CARD-402 F-001 measured an endless loop on a landscape phone (932 x 430, a 30 x 29 at Fit flipped every frame) because re-fitting changes the stage. The new observation needs the same kind of guard — act only when the stage's rounded box differs from the last one acted on — and must not re-fire from its own re-fit.

## Acceptance criteria

* **AC-1**: a change to the stage's box that fires no `resize` and moves neither the toolbar nor the header (a test-only style change on the stage) re-measures the bands: no clue band is cut off afterwards. With the new observation removed, this cell reds.
* **AC-2**: CARD-402's measured loop case (932 x 430, a 30 x 29 at Fit) does not loop — reuse the suite's existing cell for it if there is one (not located when this card was cut), otherwise it is one of this card's two new cells, and the number of re-fits after a single change settles — counted, not timed.
* **AC-3**: tests extend `tests/test_puzzle_solver_clues.py`; net test count +2 at most.
* **AC-4**: owner looks at the play page on a phone after publish (the admin solver files are the player's source).

## Guardrails

* **G-1**: zoom, Fit and pinch behaviour unchanged (`tests/test_puzzle_solver_zoom.py` passes unmodified).
* **G-2**: the public player is a build-time copy of these files: no edit under `player/` beyond what the build produces.
* **G-3**: gate on the player test set only (owner rule 2026-11-09), full suite at wave close.

## Worktree notes

—
