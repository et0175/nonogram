# CARD-453: A solved puzzle offers the way on — Next puzzle and Back to the book

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1.5c (0.5d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H2 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
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

On solving, the brush button becomes a small "Solved!" chip, the editing buttons stay on screen with nothing to do, and the only way forward is the back link. In a 160-puzzle book the next step is almost always the next puzzle. The Show grid toggle is the only light-blue element in the palette.

## What to implement

A solved card under the board: hints used, a primary **Next puzzle →** (the next key in the book; absent on the book's last puzzle and outside a book) and **Back to the book**. The editing buttons hide once solved. Show grid takes the theme's accent instead of the light blue.

## Acceptance criteria

- **AC-1**: solving a book puzzle shows the card; Next puzzle opens the next key with ?book= kept; the last puzzle has no Next.
- **AC-2**: outside a book the card offers only the library.
- **AC-3**: no blue outside the theme tokens in the solved state.

## Worktree notes
