# CARD-451: Clues stay pinned on a landscape phone, and Hint's dead end points to Probe

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: one constant moved inside a gap its own comment measured, two sentences, and the tests that quote them. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/451-clues-and-probe-pointer
**Worktree:** ../PythonProject4-card-451
**Source:** owner 2026-11-16 (project thread), on the two design notes of the Android QA run: *"погоджуюсь з 1 та 2"* ("I agree with 1 and 2") — (1) the column clues scrolled away on a landscape phone at 150 % zoom because of the 40 % rule, (2) Hint's dead end gives no next step. Read with the coordinator as: move the bar so they stay, and add the pointer.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-271, CARD-404, CARD-435
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html (comment), tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_zoom.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T18:50Z
**Closed:** 2026-11-16T19:40Z
**Actual:** —
**Merge commit:** 72c7886c
**Blocked by:** —

## What to implement

1. `STICK_MAX_SHARE` 0.4 → **0.48** (CARD-271's owner-movable bar). Measured on the live site with the 30 x 30 `52603b6dee`: at 839 x 412 (Pixel 7 on its side) the column band is 43 % of the stage at 150 % and 46 % from 175 % up (CARD-404's numeral cap), so 0.48 keeps it at every zoom. It stays under the 0.496 that CARD-271 measured a stuck band taking the cells a drag aimed at (`TestSolverZoom_OneFingerDragIsUnchangedByZoom`, which reds at 0.5). On a Galaxy S9+ (658 x 320 on its side) the column band keeps to 125 % (46 %; 55 % at 150 %), and upright (320 x 658) the row band keeps to 125 % (45 %; 49 % at 150 %).
2. Hint's two dead ends gain "Try a Probe: guess one square and see if it breaks a line." — the public player's (`PUBLIC_EXHAUSTED`, where it has no solution to reveal from) and the ladder's (`LADDER_EXHAUSTED`).

## Acceptance criteria

- **AC-1**: every sticky-band test derives keep / not-keep from the measured cover and `STICK_MAX_SHARE` read out of solver.js, so they hold the new bar; the 0.496 case still does not keep. (tests: `tests/test_puzzle_solver_clues.py`, `tests/test_puzzle_solver_zoom.py`, `tests/test_puzzle_solver_phone.py`)
- **AC-2**: the dead-end sentences read the Probe pointer. (tests: `tests/test_puzzle_solver_hint.py`'s two exhausted-ladder assertions; `tests/test_player_public_mode.py` reads `PUBLIC_EXHAUSTED` from solver.js)

## Worktree notes
- **[Tried and dropped]** A test pinning the QA case on the suite's own 30 x 30 (`GRID_30x30`): its column clues are deeper than the live puzzle's (64 % of the stage at 150 %, not 43 %), so it cannot stand for the case; the derived tests hold the rule, and the live case is measured on the preview.
- **[Gate, 2026-11-16]** The 10 hint/clue/zoom/phone/probe/public/lesson files: 418 passed, 2 red — both pinned the 0.4 bar on purpose (`test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[1280x600]`: the column band, 0.41 of the port, keeps again; `GIVES_UP_AT` cols 150 → 175). Updated with the old figures in their comments; re-run of clues + zoom: 125 passed.
