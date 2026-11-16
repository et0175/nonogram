# CARD-455: Hint speaks by clue and stays off the board

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H4 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
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

The hint box opens over the middle of the board, hiding the rows and clues it talks about. It says "the highlighted column (1)" though no line numbers are shown, and "the 17-run" is jargon that breaks as "17-" / "run".

## What to implement

Dock the hint above the board (phones: in the free space under it when that is visible). Name lines by position and clue: "Look at the first column (clue 17)." and "The block of 17 is longer than half the column, so its middle cells must be black." Ordinals for 1–3 and "column 12" beyond.

## Acceptance criteria

- **AC-1**: the hint never overlaps a board cell or clue at the three viewports.
- **AC-2**: no hint sentence names a line by a bare index in parentheses; "run" is replaced by "block".

## Worktree notes
