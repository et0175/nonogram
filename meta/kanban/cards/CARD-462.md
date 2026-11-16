# CARD-462: Small boards fill the phone width and sit centred

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M6 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
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

A 10×10 in portrait is ~300 px wide on a 412 px screen, aligned left, with "100 %" shown though it already fits.

## What to implement

When the board fits, it is fitted to the width (with the cell cap) and centred.

## Acceptance criteria

- **AC-1**: at 412×839 the 10×10 board is centred and at least 85 % of the content width.

## Worktree notes
