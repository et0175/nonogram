# CARD-460: Phone toolbar icons get captions; Reset moves away from Redo

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M4 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/pages.js, player/player.css, src/nonogram/admin/static/solver.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

In portrait, Undo, Redo, Reset, Line, Hint and Probe are icons only; the Probe dashed square and the Line strip are hard to guess, and Reset sits next to Redo.

## What to implement

Small captions under each icon in the two-row portrait toolbar; Reset moves to the end of its row.

## Acceptance criteria

- **AC-1**: each portrait toolbar button shows a visible caption.
- **AC-2**: Reset is not adjacent to Redo.

## Worktree notes
