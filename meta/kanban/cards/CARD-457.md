# CARD-457: Desktop opens the board at Fit, with a cell cap

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M1 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

At 1280×800 the board opens at 100 % and fills under half the width; the 30×29 uses ~16 px cells, a 10×10 is ~300 px wide.

## What to implement

On desktop the initial zoom fits the board to the window height, capped at ~36 px per cell.

## Acceptance criteria

- **AC-1**: at 1280×800 the 30×29 and the 10×10 open fitted and capped.

## Worktree notes
