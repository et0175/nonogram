# CARD-429: The zoom readout moves after the + button, so focus order follows the eye in landscape

**Status:** ready
**Priority:** P3
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- The markup change is one element moved. The cost is everything that records the group's ORDER: the frozen CSS census rows, any geometry cell that reads the children positionally, and the two layouts' comments. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-11, following CARD-428's merge: asked how to resolve the landscape Tab-order zigzag, the owner chose "Fix the Tab order only", then — told that focus order follows DOM order and desktop draws the same group in DOM order — chose **"Accept − + 100% everywhere"**.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-426
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_zoom.py, tests/test_player_base_css.py
<!-- Derived 2026-11-11. The markup is `puzzle_solve.html`'s `.player-zoom` group; `admin.css` only if a comment or a grid-area needs to follow (CARD-402's landscape block places the three children by explicit `grid-area`, so the visual result there must NOT move). `tests/test_player_base_css.py` is named because its FROZEN census enumerates elements in document order — moving one changes which row is which, and that is a re-record with the 26-second real-Bootstrap certification, not a one-field edit. Conflict edge: CARD-424 and CARD-427 are queued behind CARD-426 on the same stylesheet and script; this card touches the template, which none of them does. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-428 paired the landscape zoom steppers by giving the group its own two-column grid: `−` and `+` on row 1, the readout spanning row 2. Review cycle 1 found the consequence — **Tab now zigzags**. The DOM is `out, readout, in`; the landscape grid draws `out | in` then the readout below; focus follows DOM, so it goes top-left → bottom → top-right.

Measured before the ruling: desktop and portrait draw the same group as `display: flex`, i.e. **in DOM order**, so `− 100% +` is what you see and the focus order there is already correct. That is why this cannot be fixed in CSS — focus order follows DOM order, and CSS cannot change it (a positive `tabindex` is an anti-pattern and fragile).

So the choice the owner was given was real and the cost is real: moving the readout after `+` fixes landscape and **changes what desktop and portrait look like**, from `− 100% +` to `− + 100%`. They took it. The declined alternatives are recorded so nobody re-opens them: leaving the zigzag, and un-pairing the steppers in landscape (which would undo CARD-428 and re-create the owner's original finding).

## Owner ruling, 2026-11-11

**"Accept − + 100% everywhere."** One markup change; the steppers stay paired at every size; the readout follows them. No decision is outstanding.

## What to implement

1. **Move the readout** (`.player-zoom-readout[data-player-zoom-readout]`) after the `data-player-zoom-action="in"` button in `puzzle_solve.html`'s `.player-zoom` group. Nothing else in the template moves.
2. **Landscape must look exactly as it does today.** CARD-402's block places all three children by explicit `grid-area`, so the drawn result should not move — but the DOM order it reads has changed, so verify rather than assume, and adjust only if the measurement says to.
3. **Comments follow the code.** `.player-zoom`'s own comment and CARD-428's comment in the landscape block both describe the order; this card is the fifth on this board to have prose go stale one step behind the code, so read every comment the diff touches.
4. **The frozen census is a re-record, not a field edit.** `tests/test_player_base_css.py`'s `FROZEN` enumerates sampled elements in document order (`04 div puzzle-player-tool-menu`, and the zoom rows beside it); moving an element changes which row is which. Re-record both widths and **certify** against the pinned Bootstrap (`src/nonogram/admin/templates/base.html` pins `bootstrap@5.3.0`; sha256 `7f1d37f0…` must match `PROVENANCE`), so the sha-matched branch asserts the table equals the real file's live measurement — 26 seconds, this board's standing practice. The ordering trap is in CARD-423's notes: the assert fires before the printing branch, so patch from measured actuals first, then certify.

## Acceptance criteria

- **AC-1** (focus follows the eye in landscape): at 844x390 and 874x402, tabbing through the zoom group visits `−`, then `+`, then the readout, matching the drawn order left-to-right then below. (test: changed cell in `tests/test_puzzle_solver_zoom.py`; plant: move the readout back and the cell reds.)
- **AC-2** (desktop and portrait draw the ruled order): at 390x844, 1280x720 and 1440x900 the group reads `−`, `+`, readout left to right, and focus order matches it. (test: the same cell's other viewports.)
- **AC-3** (landscape geometry unchanged): the three children's boxes at 844x390 and 874x402 are identical to CARD-428's recorded figures — `out [260, 344, 44, 44]`, `in [312, 344, 44, 44]`, readout `[260, 396, 96, 44]`. (test: CARD-428's own cell, unchanged.)
- **AC-4** (the floor holds): every zoom control is still at least 44x44 px at both landscape viewports and in compact portrait. (test: `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar`, unchanged.)

**Net test count: 0 added** — the zoom module already has order and geometry cells; change one.

## Worktree notes

—
