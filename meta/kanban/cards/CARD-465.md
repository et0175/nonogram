# CARD-465: Zoomed in on a landscape phone, the clue band leaves room for the board

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M9 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, player/player.css
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

At 125 % in phone landscape the board area is ~270 px; the sticky column clues take ~110 px of it and the garland 60 px above, so ~8 of 29 rows show.

## What to implement

In landscape, the sticky clue band uses a smaller numeral size when zoomed in (with M3 removing the garland).

## Acceptance criteria

- **AC-1**: at 839×412 and 125 %, at least 12 rows of the 30×29 are visible.

## Worktree notes
