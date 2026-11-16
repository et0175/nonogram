# CARD-459: The garland gives way in landscape, and the back link is short

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.2d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M3 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/decor.css, player/pages.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

In phone landscape the garland takes ~60 of 412 px above the board; the back link truncates to "← Christmas Nonog…".

## What to implement

In landscape (height < 500 px) the garland shrinks to a thin strip or hides in the player; the back link reads "← Book" (full title in its accessible name).

## Acceptance criteria

- **AC-1**: at 839×412 the garland is ≤ 16 px tall in the player.
- **AC-2**: the back link is not truncated.

## Worktree notes
