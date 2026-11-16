# CARD-452: The player title names the book puzzle — "Puzzle 160", size and level beside it

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H1 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/pages.js, player/player.css
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Opened from a book (/play/<key>?book=<slug>), the player title reads "Puzzle 30×29 · HARD" and never the number the reader typed on the book page or saw printed above the grid, so they cannot confirm they opened the right puzzle.

## What to implement

When the book file holds this key, title the page "Puzzle N" (N = the key's 1-based position in the book) with "30×29 · Hard" as the small line beside it, in the heading and in document.title. Library puzzles keep the size-only title.

## Acceptance criteria

- **AC-1**: opened from a book, the heading and document.title carry the book number; the size and level stay visible.
- **AC-2**: opened from the library or with an unrelated ?book=, the title is unchanged.

## Worktree notes
