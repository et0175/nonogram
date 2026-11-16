# CARD-463: How to solve: found from the top of the book page, linked from How to play, dressed in the book's theme

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
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M7 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/book.html, player/how-to-solve.html, player/how-to-solve.js, player/pages.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The book page's "How to solve one" link sits under all 68 Easy tiles (~4,000 px down on a phone); How to play does not link to it; How to solve wears the default teal look even when opened from the book.

## What to implement

A "New to nonograms? Learn in 2 minutes" link under the "Which puzzle are you on?" box; the same link at the end of How to play; How to solve opened from a book carries ?book= and wears that book's theme.

## Acceptance criteria

- **AC-1**: the link is above the first section on the book page.
- **AC-2**: How to play links to How to solve.
- **AC-3**: opened from the Christmas book, How to solve loads the theme.

## Worktree notes
