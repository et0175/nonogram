# CARD-458: Desktop toolbar on one row, Hint carries its own count

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M2 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
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

Probe drops alone onto a second row; the Hints counter sits at the far right, away from Hint.

## What to implement

One row in groups: Brush, Region | Undo, Redo, Reset | Hint, Probe, Line | zoom. The count shows on the Hint button ("Hint · 2").

## Acceptance criteria

- **AC-1**: at 1280×800 every toolbar control is on one row.
- **AC-2**: the count is inside the Hint button.

## Worktree notes
