# CARD-472: Region keeps one green in landscape

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 0.25c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding L5 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/player.css
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The active Region button is a lighter green in landscape than in portrait, which can read as disabled.

## What to implement

Same active colour in both orientations.

## Acceptance criteria

- **AC-1**: active Region computed background is identical at 412×839 and 839×412.

## Worktree notes
