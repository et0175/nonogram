# CARD-457: Desktop opens the board at Fit, with a cell cap

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.2d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/457-desktop-cells (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M1 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_player_base_css.py
**Review score:** — (no review cycle; owner request, 2026-11-17)
**Started:** 2026-11-17T07:05Z
**Closed:** 2026-11-17T08:00Z
**Actual:** —
**Merge commit:** 78041a35 (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

At 1280×800 the board opens at 100 % and fills under half the width; the 30×29 uses ~16 px cells, a 10×10 is ~300 px wide.

## What to implement

On desktop the initial zoom fits the board to the window height, capped at ~36 px per cell.

## Acceptance criteria

- **AC-1**: at 1280×800 the 30×29 and the 10×10 open fitted and capped.

## Worktree notes
- **[Built]** Owner 2026-11-17 "go on". Public desktop page only (same scope as CARD-458): `--player-cell-max` 36 px. Live book 10x10 at 1280x800: ~300 -> ~390 px. Big boards unchanged (height-bound). Renders: ~/Documents/nonogram-reviews/CARD-457/.
- **[Gate, 2026-11-17]** Player set over 457+461: 1442 passed, 9 skipped (DATABASE_URL unset).
