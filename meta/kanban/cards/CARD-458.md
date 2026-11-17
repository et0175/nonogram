# CARD-458: Desktop toolbar on one row, Hint carries its own count

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.2d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/458-desktop-toolbar-row (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M2 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_player_base_css.py
**Review score:** — (no review cycle; owner request, 2026-11-17)
**Started:** 2026-11-17T02:50Z
**Closed:** 2026-11-17T05:00Z
**Actual:** —
**Merge commit:** be28ac2f (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

Probe drops alone onto a second row; the Hints counter sits at the far right, away from Hint.

## What to implement

One row in groups: Brush, Region | Undo, Redo, Reset | Hint, Probe, Line | zoom. The count shows on the Hint button ("Hint · 2").

## Acceptance criteria

- **AC-1**: at 1280×800 every toolbar control is on one row.
- **AC-2**: the count is inside the Hint button.

## Worktree notes
- **[Built]** Owner 2026-11-17 "do m2", superseding CARD-411 option "A" on the PUBLIC desktop page only (`.player-toolbar:not(:has([data-player-action="check"]))`, min-width 601 and min-height 501). Order: brush, Region | Undo Redo Reset Hint | Probe | Revealed | zoom. The open probe's leaving note is not drawn there (it would wrap the row and move the board). The admin page keeps CARD-411's layout: one row there wrapped and shrank the board (15.4 px cells at 1440), measured by 16 admin geometry tests.
- **[Test]** test_player_base_css FROZEN[1280] re-measured against the real Bootstrap 5.3.0 (sha256 verified) and pasted. Renders: ~/Documents/nonogram-reviews/CARD-458/.
- **[Gate, 2026-11-17]** One player-set run over 469+455+458+468 stacked: 1442 passed, 9 skipped (DATABASE_URL unset).
