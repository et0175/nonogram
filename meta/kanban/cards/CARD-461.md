# CARD-461: One brush control everywhere — the inline row of four

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/461-brush-caret (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M5 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_player_base_css.py
**Review score:** — (no review cycle; owner request, 2026-11-17)
**Started:** 2026-11-17T07:05Z
**Closed:** 2026-11-17T08:00Z
**Actual:** —
**Merge commit:** 78041a35 (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

On phones the brush button is a plain black square with no sign it opens a menu; How to solve and Line view show the four brushes as an inline row.

## What to implement

Use the inline row of four brushes on the board where it fits in portrait; where it does not, the brush button gets a ▾ caret.

## Acceptance criteria

- **AC-1**: portrait and desktop show the inline row (or the caret where the row does not fit).

## Worktree notes
- **[Built, the card's fallback]** Owner 2026-11-17 "go on". A ▾ caret on the brush trigger at every size (corner of the 44 px button when compact). The inline row of four was not built: it does not fit the upright phone's two rows (CARD-438). Renders: ~/Documents/nonogram-reviews/CARD-461/.
- **[Gate, 2026-11-17]** Player set over 457+461: 1442 passed, 9 skipped (DATABASE_URL unset).
