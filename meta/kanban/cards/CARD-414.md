# CARD-414: The shared crosshair stops during a pinch and counts a pen as part of one — ported from play.js, with one test

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.5d)
<!-- Small in code; the cost is the CARD-268 budget claim ('the bar is paid for above the toolbar, so the board sits where it sat'), which the larger buttons break and which must be re-paid, not relaxed. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-08 on the CARD-399 audit: play.js suppresses its crosshair during a two-finger pinch and treats a pen as part of a pinch; solver.js (`wireCrosshair`) has no such suppression, so the shared UI would change what a phone user sees. Port it into solver.js once; the seven play.js tests that covered it retire with play.js (CARD-399), replaced by ONE test.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_crosshair.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. The accessible names 'Keep' and 'Contradiction' are used by tests that find buttons by role and name and by the `data-player-probe-action` attributes (the attributes are the stable handle and do not change). Serialize after CARD-410 (same bar) if both are in flight. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

One source of truth: the behaviour lives in the admin files and the public site copies them. The audit of the public player's tests (meta/profiling/card-399-claim-audit.md on branch card/399-retire-play-js) found that `player/play.js` (retiring in CARD-399) keeps its crosshair off while two fingers are down (a pinch), takes down a crosshair an earlier tap left, resumes after the pinch, ignores a third finger, and counts a pen as one of the pointers of a pinch, with a lost pen `pointerup` not sticking the pinch. `solver.js`'s `wireCrosshair` has none of that: one handler for every pointer type. On a phone that means a crosshair can flash or stick during a pinch-zoom.

## What to implement

1. Read `wireCrosshair` and the zoom pinch handling in `solver.js` and the seven play.js tests the audit lists (test_a_pinch_neither_starts_a_crosshair_nor_leaves_one, test_a_pinch_takes_off_a_crosshair_an_earlier_tap_left, test_crossing_resumes_after_a_pinch, test_a_third_finger_neither_paints_nor_follows, test_a_pen_counts_toward_a_pinch, test_a_finger_counts_toward_a_pinch_that_a_pen_began, test_a_lost_pen_pointerup_does_not_stick_a_pinch in tests/test_public_player_crosshair.py): re-derive the rules from play.js's code, not from memory.
2. Port the same rules into the shared crosshair (the admin page and, by the byte-identical copy, the public page), with no behaviour change for a single pointer.
3. ONE test in `tests/test_puzzle_solver_crosshair.py` (owner test budget: fewer tests): a single scenario-driven cell that runs the pinch sequence (two fingers down, move, release; a pen as the second pointer; a lost pointerup) and asserts the crosshair state at each step; one control that can fail (drop the pinch check and it reds).

## Acceptance criteria

- **AC-1** (pinch): *Given* an admin solver page on a touch emulation, *when* two pointers are down, *then* no crosshair starts and an existing one is taken down; it resumes on the next single-pointer cross. (test: the one cell, plant: remove the pinch guard.)
- **AC-2** (pen): *Given* a pen as the second pointer, *then* it counts toward the pinch; a lost pen pointerup does not leave the pinch stuck. (the same cell.)
- **AC-3** (single pointer unchanged): the existing crosshair tests pass unchanged. (existing tests.)
- **AC-4** (net tests): the closing note states the net collected-node-id change (target +1).

## Guardrails

* **G-1** Edit the admin files only; nothing in player/ (CARD-399 retires play.js). The change reaches the public page through the byte-identical copy and the shared-UI deploy.
* **G-2** No other behaviour change; the owner test budget applies.

## System contract

* ADR-0041/R3 — byte-identical build-time copies (check: the existing byte-identity cell).

## Worktree notes

- Ported from player/play.js wireCrosshair (the `down` Map / `pinching` flag, the pointerdown branch with the per-type isPrimary reset, `follow`'s `if (pinching) return`, the pointerup/pointercancel `lift`) into solver.js `wireCrosshair`, unchanged in rule; a single pointer takes the old path (`follow`) exactly as before. The existing `forget()` stays (the admin redraws; play.js's isPainted shortcut was not ported, no behaviour change asked).
- ONE cell: `TestSolverCrosshair_TouchKeepsTheLastCell::test_a_pinch_has_no_crosshair_and_a_pen_counts_toward_one`. Scratch mutants, each reds it with its own message: guard `if (down.size >= 2)` -> `if (false)` ("the second finger did not take the crosshair off"); wipe of all pointer types instead of the pointer's own ("a pen did not count toward the pinch"); no stale-entry wipe ("a stale pen entry stuck the pinch"); `follow` without the `pinching` return ("the crosshair followed a pinch's spread"). Source restored after each.
- CARD-268 budget: this card adds or resizes no button; the claim 'the bar is paid for above the toolbar' is not touched, nothing to re-pay (the Estimate comment names the larger buttons of a sibling card).
- Net collected node ids: +1 (test_puzzle_solver_crosshair.py 17 -> 18); the 7 play.js tests retire with play.js in CARD-399.

