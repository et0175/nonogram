# CARD-468: Probe marks read on small cells

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding L1 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/player.css, src/nonogram/admin/static/admin.css
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

At ~16 px cells the dashed amber edge is barely visible, so probe marks look like normal blacks; it reads well only in Line view.

## What to implement

Below a cell-size threshold, probe cells also get a light amber fill.

## Acceptance criteria

- **AC-1**: a probe cell under the threshold has a fill distinct from a kept cell.

## Worktree notes
