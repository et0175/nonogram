# CARD-449: Region by hold, then tap — a held press sets the start, the next tap in its line paints the segment

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: one timer on the board's existing gesture, an anchor that every other input drops, one How to play clause; the cost is keeping ordinary taps, repeat taps and drags exactly as they were. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/449-region-hold-then-tap
**Worktree:** ../PythonProject4-card-449
**Source:** Anna's QA checklist item 6 (*"Region works only by dragging, not by tapping two cells"*), handed over by the owner 2026-11-16, who then asked *"додавай функцію регіона з двома торканнями"* ("add the two-tap region function"). Built as the safer of the two variants offered the same day (a held press sets the start), so ordinary taps keep their meaning while Region is armed at load (CARD-433).
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-211, CARD-433
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, player/how-to-solve.html, tests/test_puzzle_solver_marking.py, tests/test_browser_fixture_scope.py (ADDED_SINCE_BEFORE)
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T14:30Z
**Closed:** 2026-11-16T15:10Z
**Actual:** —
**Merge commit:** e70a1339
**Blocked by:** —

## What to implement

1. With Region on, a press held 450 ms (`REGION_HOLD_MS`, the line view's long-press figure) without leaving its cell marks nothing and makes the cell the anchor: `.is-anchor`, a thick inset accent ring, and an announcement.
2. The next tap in the anchor's row or column paints the segment between them with the brush: one `dragStroke`, so one recorded stroke, one undo step, saved like a drag.
3. A tap anywhere else (or on the anchor) only drops the anchor; so do Escape, a brush change, Region turning off, a drag, and any recorded change (`commit`). A redraw re-applies the ring.
4. Ordinary taps, repeat taps and drags are unchanged; Region off, a held press is a slow tap, as before. On the board a long press did nothing special before (a slow tap); the line view's own long press (its strips, CARD-439) is a different surface, untouched. The board's context menu and the iOS callout are suppressed while Region is on.
5. How to play's Region bullet gains ", or press and hold one cell and tap the other end"; How to solve's step 5 follows (CARD-444's sync test).

## Acceptance criteria

- **AC-1** (hold, then tap): the hold marks nothing and rings the cell; the tap in its row paints the six cells between; one Undo takes all six back. (test: `TestSolverMarking_RegionHoldThenTap::test_hold_then_tap_paints_the_segment`)
- **AC-2** (dropping it): a tap in another row and column, Escape, and a brush change each leave no anchor and no mark. (same test)
- **AC-3** (taps unchanged): two ordinary taps in one row mark exactly those two cells. (same test)
- **AC-4** (the text): the How to play bullets and the lesson's step 5 read the new Region sentence. (tests: `test_the_page_copy_describes_the_new_click`, `test_the_lessons_buttons_are_the_players`)

## Worktree notes
- **[Env]** Built on `main` with CARD-447 and CARD-448 merged; CARD-438 (the portrait toolbar) was in flight in another session and is not touched.
- **[Gate, 2026-11-16]** The 16 player/lesson/site files (incl. the browser-family census): 630 passed, 0 failed, 0 skipped.
