# CARD-427: The hint and probe messages are hard to notice: a page-wide strip that vanishes on the next tap

**Status:** ready
**Priority:** P2
**Category:** ux-polish
**Estimate:** 2c (1d)
<!-- Three measured mechanisms, one of which is a behaviour decision (glance vs panel) that the owner must settle before the styling is worth doing. The CSS is small; the placement path and the dismissal rule are not. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, item 3 and 4 (one card: the same strip, in both findings). Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_probe.py
<!-- Derived 2026-11-11 by reading `solver.js`'s `placeExplain`, `replaceExplain` and `wireExplainDismiss`, and `admin.css`'s `.player-explain`. `tests/test_player_public_mode.py` and `tests/test_player_shared_ui_site.py` also name `player-explain` — name them in the brief, they may need re-pinning. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The owner, playing on both desktop and mobile: *"Hint and contradiction/probing messages in both desktop and mobile versions are difficult to notice. I think we can bring them over the puzzle and add a noticeable background"*, and *"Desktop - Hint message is much longer than the puzzle"*.

Three mechanisms, all measured on production at 1440x900:

1. **It is page-wide.** `#puzzle-player-explain` measures **1360 px** against a board of **698 px** — nearly double. That is finding 4 exactly; a strip twice the width of the thing it is about does not read as attached to it.
2. **It is a glance, by an earlier decision.** `wireExplainDismiss` (CARD-409) clears the text on the **next pointer-down anywhere**, exempting only the hint and check buttons. On a phone the tap the reader makes *to act on the hint* is the tap that erases it. The sentence survives for a screen reader in `#puzzle-player-announce` (1 x 1 px, correct by design) — so the reader who can see it has the weakest version of it.
3. **The "over the board" placement often does not happen.** `placeExplain` positions the strip against `td.player-cell.is-hinted, .is-offered`, or against a single hinted ROW; a hinted **column** yields one lined cell per row (measured: 13 cells, 13 distinct rows), so `targets.length === 0` and the function **returns without placing anything**. Measured: `is-top` false and y = 568 on all three hint rungs, with the strip left where its default CSS puts it.

So "difficult to notice" is not a styling opinion: for a column hint the strip is unplaced, full-page-width, and gone on the next touch.

## Decision owed before implementation (owner)

The owner has already given the direction — over the puzzle, with a noticeable background. What is not settled is the one that conflicts with mechanism 2:

**D1: does the message stay a glance?** "Noticeable" and "wiped by your next tap" pull against each other. Options: (a) it persists until the next hint, a tap **on it**, or the next probe decision; (b) it stays a glance but gets a timeout long enough to read; (c) it stays exactly as now and only the width and background change. **There is no default** — CARD-409 chose the glance deliberately ("it is a glance, not a panel"), so reversing it is the owner's call, not an author's.

**D2:** does the strip overlay the board (covering cells while shown) or sit immediately above it (pushing nothing)? Overlaying is what "over the puzzle" says; the board must not move when it appears either way — `TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth` is the existing control for that class of claim.

## What to implement

1. **Width:** the strip is at most the board's width and is placed against it, at every viewport. Nothing page-wide.
2. **A noticeable background:** from the theme tokens, not a literal; contrast checked against both themes (the page has a dark mode).
3. **Placement that always happens:** `placeExplain`'s early return on a column hint is the bug behind finding 3. A hinted column has a column clue and a known axis; place against those rather than giving up.
4. **Whatever D1 decides, applied to the probe messages too** — the owner named hint *and* contradiction/probing together, and both write through the same strip.

## Acceptance criteria

- **AC-1** (never wider than the board): at 390x844, 844x390, 1280x720 and 1440x900, with a hint shown, the strip's width is <= the board's. (test: changed cell in `tests/test_puzzle_solver_hint.py`; plant: restore the page-wide rule and it reds.)
- **AC-2** (a column hint is placed too): after the first hint on a puzzle whose first hint is a COLUMN, the strip is positioned against the board (not at its default slot) and `placeExplain` did not early-return. (test: a changed/new cell naming the column case; evidence: the 13-cells/13-rows measurement above.)
- **AC-3** (D1's rule, whichever it is): the strip's lifetime follows the owner's answer, asserted once. (test: `tests/test_puzzle_solver_hint.py`; a probe cell in `tests/test_puzzle_solver_probe.py` for the probe wording.)
- **AC-4** (the board does not move when it appears): at 390x844 and 1440x900 the board's box is identical with and without the strip. (test: the existing board-does-not-move control, extended to this trigger.)

**Net test count:** prefer 0 added; changing the hint module's existing presentation cells is the intended route. State the net.

## Worktree notes

—
