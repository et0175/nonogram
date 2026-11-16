# CARD-456: Two-digit clues stay apart on 25–30 wide boards

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H5 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/player.css, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

On 30-wide boards "17 2", "12 13", "16 14" and "1 10 1" touch their neighbours at phone and desktop sizes; "1213" can read as one number.

## What to implement

Two-digit numerals get a condensed rendering (tighter letter spacing or a smaller size) so each fits its own column, and column-clue cells get a faint vertical rule.

## Acceptance criteria

- **AC-1**: on the 30×29 book puzzle at Fit, no two-digit numeral's box overlaps a neighbouring column's box (measured from the DOM).

## Worktree notes
