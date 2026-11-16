# CARD-469: The Hints counter counts what its label says

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding L2 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
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

After two Hint presses the counter still shows 0; it counts revealed cells while the label says "Hints".

## What to implement

Rename it "Cells revealed", or count every press — owner to choose at pick-up (default: rename).

## Acceptance criteria

- **AC-1**: label and figure agree.

## Worktree notes
