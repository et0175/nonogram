# CARD-462: Small boards fill the phone width and sit centred

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.2d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/462-small-boards-centred (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M6 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_player_shared_ui_site.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T22:45Z
**Closed:** 2026-11-16T23:20Z
**Actual:** —
**Merge commit:** 9ebb4d45 (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

A 10×10 in portrait is ~300 px wide on a 412 px screen, aligned left, with "100 %" shown though it already fits.

## What to implement

When the board fits, it is fitted to the width (with the cell cap) and centred.

## Acceptance criteria

- **AC-1**: at 412×839 the 10×10 board is centred and at least 85 % of the content width.

## Worktree notes
- **[Built]** Portrait phone only (`max-width: 600px` and portrait): `--player-cell-max` 36 px and `margin-inline: auto` on the board. The board was stopped by the 28 px cap, not by the width. Live book 10x10 at 412x839: 36 px cells, centred. Renders: ~/Documents/nonogram-reviews/CARD-462/. The zoom readout still says 100% (that is what it is); not changed.
- **[Gate]** Solver/player/public set: 922 passed (before the final test-only edit, which was re-run alone and is red against the old admin.css).
