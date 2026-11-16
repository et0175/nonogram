# CARD-471: Line view: a smaller overview in portrait

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/471-smaller-line-map (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding L4 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_line.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-17T02:00Z
**Closed:** 2026-11-17T02:40Z
**Actual:** —
**Merge commit:** fe87762c (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

In portrait the overview takes ~40 % of the height, so the strips and brushes sit low.

## What to implement

Shrink the overview by about a third in portrait.

## Acceptance criteria

- **AC-1**: at 412×839 the overview is ≤ 28 % of the viewport height.

## Worktree notes
- **[Built]** `@media (orientation: portrait)` override after the base `.player-line-mini` rule: 24svh. AC was <= 28 % of the viewport height; shipped <= 25 %. Render: ~/Documents/nonogram-reviews/CARD-471/line-port.png.
