# CARD-479: The clue bands are re-measured whenever the stage's own box changes

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/479-observe-the-stage
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-209, WSJF 4.62); premise re-read against main on 2026-11-18. Origin: CARD-271 review cycle 2, residual of finding F-001.
**Idea:** IDEA-209
**Wave:** 80
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py
**UI surface:** user-facing
**Review score:** 9.0 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-18T18:29Z
**Closed:** 2026-11-18T19:57Z
**Actual:** 2c — ratio 2/2 = 1.000
**Merge commit:** c1beebc575171c789b82db62166692b633d6e13e
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

[AC-2] Reuses CARD-402's own cell, `tests/test_player_public_mode.py::TestPublicMode_LandscapeToolStrip` (932 x 430, 30 x 29 at Fit, twenty frames); it reds when the new observer loses its key.
[Review 1/3] Score: 6.5, fail. F-001 (critical): G-1 broken — `TestSolverZoom_Fit::test_fit_shows_the_whole_board_and_says_so` failed at 390x844 and 844x390; the observer keyed on the stage's height, which follows the board below its cap, so every zoom change re-fitted from a board drawn at the old zoom and Fit came out one percent short. Fixed: keyed on the stage's width and max-height. Reviewer's loop sweep (on the cycle-1 key): 128 cells, admin and public, eight viewports, 100% and Fit — 0 board-size changes after the first two frames, on main and branch.
[G-1, F-006] The extra measure at load changes the PUBLIC page's opening Fit by one percent in 2 of 48 cells (30x29 at 932x430: 69% -> 70%; 30x30 at 667x375: 57% -> 58%); reviewer-measured, and the new value is the true largest fit. Confirmed on the room key in cycle 2 (same two cells, same amounts, 3 of 3 runs); the admin page is identical to main in all 24 cells.
[Review 2/3] Score: 9.0, nothing gating, certified. Reviewer re-measured on the room key: the full player set 932 passed, 0 skipped; the loop sweep (128 cells) 0 board-size changes after the first two frames; zoom-step and pinch call counts identical to main, so cycle 1's extra layouts are gone. Open, low: a window drag re-measures through both observers (stated in the code comment); `offerRedrawn` in the new observer has no test.
[For whoever adds a height rule to .player-stage — reviewer F-008] The new observer is keyed on the stage's width and max-height, deliberately not its height (cycle 1's defect). A future rule that changes the stage's height without changing its max-height will not re-measure through it; the key would have to follow that rule.
[Merge gate] The player set plus the cheap guards (owner rule 2026-11-09; 32 files): 1 failed, 1438 passed, 9 skipped (database-not-set). The one failure was the browser-family census, `TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`: the new test was recorded nowhere. Fixed after certification by one `ADDED_SINCE_BEFORE` entry (`5d589e95`, no review cycle saw it); that module plus `test_collected_names.py` and `test_guard_integrity.py` then 213 passed. The rest of the set was not re-run after that commit. The reviewer's own player-set run in cycle 2: 932 passed.
[AC-4, owed] The owner looks at the play page on a phone after publish.
[Estimate] 2c estimated, 2 cycles used.
