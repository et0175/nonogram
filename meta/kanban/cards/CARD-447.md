# CARD-447: Anna's QA — Clear never paints, and a quick second tap is not a zoom

**Status:** in_progress
**Priority:** P1
**Category:** bug
**Estimate:** 1c (0.25d)
<!-- Basis: one rule in clickedState and one touchend guard; the cost is the literal click tables and the replay property test that pin the old Clear cycle. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/447-qa-clear-and-double-tap
**Worktree:** ../PythonProject4-card-447
**Source:** owner 2026-11-16 (project thread), handing over Anna's QA checklist of the live player on an iPhone: *"Подивись, що можливо відтворити і пофіксь"* ("see what can be reproduced and fix it"). Items 4, 5 and 13 of the checklist.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_maybe.py, tests/test_puzzle_solver_probe.py (its oracle tracks cells: Clear on blank records nothing)
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T13:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

1. **Clear painted black** (checklist items 4, 5). CARD-189 gave the brush then called "Undecided" the colour brushes' cycle, so on a blank cell it painted dark, then white, then blank; CARD-247 renamed it "Clear" and kept the rule. Reproduced on the live site: Clear, three taps on a blank cell → black, white, blank. A Clear swipe that ends as a tap paints black the same way.
2. **A quick second tap zoomed the page and broke the cycle** (items 4 and 13). iOS Safari reads a fast second tap as double-tap-to-zoom: it zooms, swallows the tap, and its cancelled touch ends the repeat, so the next tap is a first tap — Black on a white cell paints black. That is exactly "the last cell won't clear, after the dot it paints black again" and "the page zooms while I place dots". Not reproducible in Chromium (no such zoom there); no iOS simulator or WebKit on this machine.

## What to implement

1. `clickedState`: Clear (`UNKNOWN`) always gives `UNKNOWN`, on any cell, first or repeat. A Clear tap on a blank cell changes nothing and `record` records nothing (no undo step).
2. `solver.js`: a `touchend` on the board or a line strip that follows the previous one within 350 ms is cancelled (`preventDefault`), which is what stops Safari's double-tap zoom; marking runs on pointer events, already fired, and nothing on those surfaces uses the synthesized click. `admin.css`: the toolbar and the line view get `touch-action: manipulation` (pinch and scroll kept).

## Acceptance criteria

- **AC-1** (Clear never paints): the literal click tables give blank for Clear from every state, first click and repeat. (tests: `TestSolverClickFollowsTheBrush::test_every_brush_state_and_repeat_gives_the_table`, `::test_repeat_clicks_follow_each_brush_sequence`, `TestSolverMaybeModule_ClickedStateTable::test_table`, and `test_PropertyTest_SolverHistory_ReplayReproducesTheBoard` with Clear-on-blank as a non-step)
- **AC-2** (no double-tap zoom): three quick taps cycle white, blank, dark and the second and third touchends are cancelled; a tap after a pause is not. (test: `TestSolverClickFollowsTheBrush::test_touch_taps_follow_the_brush`, which reds on `main`: no touchend is cancelled there)

## Worktree notes
- **[QA triage, 2026-11-16]** Not this card. Item 6 (Region by two taps): the How to play text promises a DRAG, and a drag works; tap-tap is a new interaction, put to the owner. Item 2/5 (landscape): the two-wide tool strip (owner ruling "B", 2026-11-10) cannot fit a landscape phone — at 844x390 Probe and the Hints counter are below the edge, at 844x340 the zoom too (they scroll inside the strip); a three-wide prototype fits everything at 844x390 — put to the owner, and CARD-438 (the portrait toolbar) is in flight. 30x30 digits in landscape (6-7 px) are geometry: 30 rows in about 300 px; zoom and Line are the answer. Item 13's unringed "1 1 1 1": correct — a brute force over Anna's marks finds 11 arrangements and no number fixed in all of them. The crosshair's grey on black cells: noted, unchanged.
- **[Checked, 2026-11-16, live site, Chromium touch]** Saving: marks, the Hints count and Undo come back after a reload. Rotation 390x844 <-> 844x390 four times: no mark lost. Reduced motion: solved by Hint, banner and board shown, no animation running.
- **[Gate, 2026-11-16]** The 15 player/editor/lesson files: 644 passed, 2 red — the probe oracle (`TestSolverProbe_StateIsPureAndStatesAreFour`, named cases and seeded corpus) counted every mark as a stroke; it now tracks cell states with its own first-click table and skips a mark that changes nothing. Re-run of probe, marking and maybe: 150 passed.
