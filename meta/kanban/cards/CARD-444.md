# CARD-444: How to solve looks and explains like the player — its buttons, brushes, tap cycle and probe

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: an audit of the lesson against the live player, then the clear-cut fixes in the lesson's own three files; the larger look changes are listed as proposals, not done. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/444-lesson-matches-the-player
**Worktree:** ../PythonProject4-card-444
**Source:** owner 2026-11-14 (project thread): *"Please check that "how to solve" has the same look and feel and explain the same functionality as the puzzle player (buttons, black\white\maybe brushes, contradiction\probing, hints)"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-419, CARD-412, CARD-440
**Touches:** player/how-to-solve.html, player/how-to-solve.js, player/player.css, tests/test_how_to_solve_page.py
**Review score:** — (no review cycle; owner request, 2026-11-14)
**Started:** 2026-11-14T09:10Z
**Closed:** 2026-11-14T10:00Z
**Actual:** —
**Merge commit:** 8325cb54
**Blocked by:** —

## Why — the audit (live site, 390x844 and 1280x900)

| Area | The player | The lesson before this card | Mismatch |
| --- | --- | --- | --- |
| Buttons | Brush, Region, Undo/Redo/Reset, Line, Hint, zoom, Probe; a "How to play" list under every board | Only Probe (and Line, in step 5) | Hint, Brush, Region, zoom never explained |
| Brushes | Black, White, Maybe, Clear in a menu; chosen item green-tinted | Black, White, Maybe; chosen item inverted (dark) | No Clear; different chosen look |
| Tap | Tap again cycles black → white → clear (Maybe ↔ clear) | Tap again clears | Different rule |
| Probe buttons | Probe (dashed-square icon); ✓ Keep, ✗ Wrong guess, outline buttons, Wrong guess red-edged once a line breaks | Probe (text), Keep, a solid red "Contradiction" | Wrong name, look and icon |
| After a wrong guess | Probe undone, then "Your first guess was wrong… Mark it?" offer | The square turned white by itself | The offer is missing |
| Hints | Three presses: where, why, fill; "no single row or column decides" | Not mentioned | Missing |
| Clue circles, crosshair, solved celebration | On | Not drawn in the demos | Look (proposal) |
| Cells | A ruled grid, heavy every fifth line | Separate rounded tiles | Look (proposal) |

## What to implement

1. A new step 5, **The buttons**: the player's own "How to play" list, word for word (less the panel-only Check), each line beside the control as the player draws it (the swatch, the two squares, the bulb and probe icons copied from `_icons.html`).
2. **Try one**: the player's tap cycle (`tappedState`, the player's `clickedState` reimplemented), a fourth brush Clear, and the chosen brush drawn as the player's chosen menu item.
3. **Try a probe**: ✓ Keep and ✗ Wrong guess (renamed from Contradiction), outline buttons, Wrong guess red-edged while the probe has broken a line; Probe carries the player's icon; Wrong guess undoes the probe and shows the player's offer ("Your first guess was wrong, so row 3, column 2 must be white. Mark it?") with Mark it / No thanks; the step's text says so.

Proposed, not done: clue circles and the crosshair in the demo boards; the demo's cells drawn as the player's ruled grid; Undo/Redo/Reset and Line added to the player's own How to play list (the lesson follows it); and once **CARD-435** merges (a probe's red clues wait for Hint), the lesson's probe demo must follow — today it shows the red at once, as the live player still does.

## Acceptance criteria

- **AC-1** (the buttons): step 5's list equals the player's How to play list without Check, in order, and the bulb and probe icons are the player's paths. (test: `test_the_lessons_buttons_are_the_players`)
- **AC-2** (tap and brushes): a square tapped three times reads black, white, clear; the lesson's rule equals the player's `clickedState` on every state, brush and repeat; Clear clears. (test: `test_try_one_marks_black_white_and_maybe_and_show_me_solves_it`)
- **AC-3** (probe): Wrong guess is flagged while the probe is broken, undoes the probe, shows the offer naming the square and outlines it; Mark it marks it white. (test: `test_the_probe_demo_runs_like_the_players_probe`)

## Worktree notes
- **[Measured, 2026-11-14]** Local assembled site: the four brushes fit the card at 360, 390 and 1280 (`scrollWidth` equal to the viewport); before the fix the bar overflowed a 390 px card. Screenshots before/after: `~/Documents/nonogram-reviews/CARD-444/`.
- **[Env]** The lesson's tests are a non-browser equality (`test_the_lessons_buttons_are_the_players`, new) and two browser tests whose names are unchanged, so the browser family's census does not move. `&#10003;`/`&#10007;` entities read as hex colours to the lesson's literal sweep, so the page writes ✓ and ✗ directly.
- **[Gate, 2026-11-14]** The 10 lesson/player/site files: 367 passed, 0 failed, 0 skipped.
