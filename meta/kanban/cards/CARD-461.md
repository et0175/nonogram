# CARD-461: One brush control everywhere — the inline row of four

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M5 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
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

On phones the brush button is a plain black square with no sign it opens a menu; How to solve and Line view show the four brushes as an inline row.

## What to implement

Use the inline row of four brushes on the board where it fits in portrait; where it does not, the brush button gets a ▾ caret.

## Acceptance criteria

- **AC-1**: portrait and desktop show the inline row (or the caret where the row does not fit).

## Worktree notes
