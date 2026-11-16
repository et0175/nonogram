# CARD-452: The player title names the book puzzle — "Puzzle 160", size and level beside it

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/452-book-number-title
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H1 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/assemble.py (the site loader), tests/test_player_shared_ui_site.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T19:35Z
**Closed:** 2026-11-16T20:05Z
**Actual:** —
**Merge commit:** e40b68f6
**Blocked by:** —

## Why

Opened from a book (/play/<key>?book=<slug>), the player title reads "Puzzle 30×29 · HARD" and never the number the reader typed on the book page or saw printed above the grid, so they cannot confirm they opened the right puzzle.

## What to implement

When the book file holds this key, title the page "Puzzle N" (N = the key's 1-based position in the book) with "30×29 · Hard" as the small line beside it, in the heading and in document.title. Library puzzles keep the size-only title.

## Acceptance criteria

- **AC-1**: opened from a book, the heading and document.title carry the book number; the size and level stay visible.
- **AC-2**: opened from the library or with an unrelated ?book=, the title is unchanged.

## Worktree notes
- **[Built]** The title lives in the site loader in `player/assemble.py`, not in pages.js. Rendered at 1280x800, 412x839, 839x412 and 658x320: ~/Documents/nonogram-reviews/CARD-452/.
- **[Residual]** The extra size span makes the way-back link ellipsise earlier on a phone ("← Christmas Non…" at 412 px). CARD-459 (M3) shortens that link.
