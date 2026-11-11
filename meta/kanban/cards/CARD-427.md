# CARD-427: The hint and probe messages are hard to notice: a page-wide strip that vanishes on the next tap

**Status:** ready
**Priority:** P2
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- LOWERED from 2c when the owner ruled D1/D2 (2026-11-11): a viewport-centred box needs no target tracking, so the card now DELETES `placeExplain`'s targeting path instead of fixing it, and the dismissal rule stays exactly as CARD-409 wrote it. What is left is a centred box, a background from the tokens, and the tests that move with them. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, items 3 and 4 (one card: the same strip, in both findings), with D1/D2 ruled by the owner the same day. Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
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

## Owner ruling, 2026-11-11

Asked whether the message should stop being a glance, the owner's answer: **"let it disappear. just appear the center of the screen on some background"**. So:

**D1 — it stays a glance.** `wireExplainDismiss` is unchanged: the next pointer-down anywhere still clears it, and the live region still keeps the sentence for a screen reader. CARD-409's decision stands; this card does not reopen it.

**D2 — it is centred in the viewport, over whatever is under it.** This supersedes the direction in the original finding ("bring them over the puzzle"): the ruling is the *screen's* centre, not the board's, which is a simpler rule and is independent of where the hint points.

**What the ruling removes.** `placeExplain` exists to track the hinted cells — it measures their span, decides `is-top`, and `replaceExplain` re-runs it on every redraw, resize and stage move. A viewport-centred box needs none of that, and the column-hint early return (mechanism 3 below) stops being a bug to fix and becomes a path to delete. Deleting it is part of this card, not a follow-up: leaving dead placement logic beside a centred box is how the next reader learns a rule that is no longer true.

**One consequence to state rather than discover.** Centred, the box can cover the cells the hint is about — including the highlighted column it names. That is acceptable under D1 precisely because it disappears on the next pointer-down: the reader reads, then taps, and the board is clear. The author does not add a dodge-the-target behaviour; if it turns out to matter in play, that is a new finding from the owner, not an author's guess.

## What to implement

1. **A contained box, centred in the viewport.** Not page-wide: today it measures 1360 px against a 698 px board. Fixed positioning, centred both ways, with a max width that keeps it readable on a phone and well short of the page on a desktop.
2. **A noticeable background,** from the theme tokens rather than a literal, with contrast checked in both themes (the page has a dark mode) — and the box must read as a message, not as part of the board.
3. **Delete the placement path the ruling makes dead:** `placeExplain`, its `is-top` class, `replaceExplain` and its callers. Keep `wireExplainDismiss` exactly as it is.
4. **The probe messages come with it** — the owner named hint and contradiction/probing together, and both write through this same strip, so both land centred without a second code path.

## Acceptance criteria

- **AC-1** (centred, contained): at 390x844, 844x390, 1280x720 and 1440x900, with a hint shown, the box's centre is within a pixel or two of the viewport's centre on both axes, and its width is at most the board's and well under the page's. (test: changed presentation cells in `tests/test_puzzle_solver_hint.py`; plant: restore the page-wide rule, or the old placement, and the cell reds.)
- **AC-2** (it still disappears, D1): a pointer-down anywhere but the hint and check controls clears it, and the live region keeps the sentence. (test: the existing `wireExplainDismiss` cells, which must pass **unchanged** — that is the evidence that this card did not reopen CARD-409.)
- **AC-3** (the dead path is gone, not orphaned): `placeExplain`, `is-top` and `replaceExplain` are absent from `solver.js` and from `admin.css`, and no test still names them. (test: the hint module's own cells after the change; evidence: a grep over `src/`, `tests/` and `player/` recorded in Worktree notes.)
- **AC-4** (the board does not move when it appears): at 390x844 and 1440x900 the board's box is identical with and without the box shown. (test: the existing board-does-not-move control, extended to this trigger.)
- **AC-5** (the probe messages too): a probe decision's message appears in the same centred box, with no second placement path. (test: a changed cell in `tests/test_puzzle_solver_probe.py`.)

**Net test count:** prefer 0 added — the hint module's existing presentation cells are the place for AC-1 and AC-2, and AC-3 removes claims rather than adding them. Deleting a test whose only subject was `placeExplain`'s targeting is expected, with the survivor named. State the net.

## Worktree notes

—
