# CARD-414: The shared crosshair stops during a pinch and counts a pen as part of one — ported from play.js, with one test

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.5d)
<!-- Small in code; the cost is the CARD-268 budget claim ('the bar is paid for above the toolbar, so the board sits where it sat'), which the larger buttons break and which must be re-paid, not relaxed. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/414-shared-crosshair-pinch
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-414
**Source:** owner ruling 2026-11-08 on the CARD-399 audit: play.js suppresses its crosshair during a two-finger pinch and treats a pen as part of a pinch; solver.js (`wireCrosshair`) has no such suppression, so the shared UI would change what a phone user sees. Port it into solver.js once; the seven play.js tests that covered it retire with play.js (CARD-399), replaced by ONE test.
**Idea:** —
**Wave:** 79
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
- Frozen census re-derived by measurement: tests/test_public_player_agreement.py `DECLARED_CROSSHAIR_DIVERGENCES` declared 5 admin/public differences; after the port the admin matches the public on three of them (events.listened, events.that_clear_the_crosshair, pointer_type.is_read_in), so those three declarations were stale and are removed (measured: crosshair_disagreements now returns only the two redraw-forget facts); the `admin-pointerdown-no-longer-moves` mutant's plant text moved with the handler (the admin's pointerdown listener is now an arrow that calls `follow`). No node id added or removed there (193 collected before and after).
- Fix round 1 (review 6.5). B1: a new browser-family test id must be recorded in `tests/test_browser_fixture_scope.py` `ADDED_SINCE_BEFORE` (a frozen registry outside impact scope: the 'tests added: ... recorded nowhere' trap); the cell's `[chromium]` id is now there as CARD-414. S1: the SAME cell gained a pen-then-finger arm (a finger's primary must not wipe a pen entry), a pen move during a pinch that must not cross, and a mouse press with a finger down that must not count as a pinch pointer, plus a resume after each. Scratch mutants, each red with its own message: M5 finger primary also wipes pen entries ("a finger did not count toward a pinch a pen began"); M3 `isFinger` always true ("a mouse press counted as a pinch pointer"); M4 `follow` ignores `pinching` for a pen only ("a pen's move crossed during a pinch"); and the earlier four still red. A mouse HOVER (no press) cannot be an arm for M3: only a pointerdown enters the count, so the press is the deterministic form.
- G-2 reading, OWNER RULING 2026-11-08 ('fix the stuck pen case too'): the stuck-pen fix is an owner-ruled addition BEYOND play.js parity. Repro (probe A): a real CDP pen pressed on the board, moved OUTSIDE the stage and released there never delivers its pointerup to the stage (no pointer capture without Region), so its entry stays in `down`; a finger tap is then not crossed, nor a later mouse hover, until the next primary PEN press (a finger primary wipes only touch entries). Remedy chosen: the pointerup/pointercancel `lift` listens on the WINDOW instead of the stage (the window hears a release anywhere and everything the stage hears bubbles to it), so a lost up lifts its entry; a pen genuinely still down has produced no up, so a pen-then-finger pinch still counts (the S1 arm, play.js behaviour 6), and a single pointer is unchanged. Chosen over a timeout or an event.buttons check on the next move because it is the standard cure and needs no state. play.js had the same flaw; it retires with CARD-399 and is not fixed there. The cell gained the probe-A arm (pen press, move and release outside the stage, finger tap crossed, mouse hover crossed); the scratch mutant that drops the window listener (M6) reds it ("a pen released outside the stage stuck the pinch"). The pen helper now sends `buttons: 0` on release (a release with buttons 1 is not a pointerup), and the mouse pointer is parked off the stage before the tap (its pointerleave would clear a touch cross). Census re-derived by measurement: `crosshair_disagreements` still returns exactly the two redraw/forget facts (the window listener reads as the same listened events), nothing loosened.
- Process blip: a stray `git stash; git stash pop` was run in this worktree; the tree was clean so nothing was stashed, the pop failed on an older unrelated stash and left it; `git stash list` is unchanged (4 pre-existing entries, none mine).

