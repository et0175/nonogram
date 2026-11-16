# CARD-466: Zoomed in, only the board scrolls

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M10 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
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

Zoomed in, the board scrolls in its own frame while the page is also taller than the screen (861 vs 839 px portrait, 422 vs 360 px landscape), so an edge drag can move the page and the toolbar slides away.

## What to implement

While zoomed in, the board frame is sized so the page itself does not scroll; How to play sits below the fold.

## Acceptance criteria

- **AC-1**: zoomed in at 412×839 and 839×412, document scroll height equals the viewport height.

## Worktree notes
