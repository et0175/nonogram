# CARD-463: How to solve: found from the top of the book page, linked from How to play, dressed in the book's theme

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/463-how-to-solve-reach (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M7 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/book.html, player/player.css, player/how-to-solve.js, player/decor.js, player/assemble.py, tests/test_book_landing_page.py, tests/test_how_to_solve_page.py, tests/test_player_shared_ui_site.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T23:20Z
**Closed:** 2026-11-17T00:00Z
**Actual:** —
**Merge commit:** b6c31be0 (on ux-review-cards; into main with it)
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
- **[Built]** The landing's `.book-foot` is gone; its one link is `.book-learn` under the number box. The theme on the lesson keys on the REFERRER (a /b/<slug> on this site, as "Back to your puzzles" already does), so the lesson opened from a puzzle page keeps the default look.
- **[Narrowed]** How to play's lesson link is on BOOK puzzles only: CARD-436's test holds a library puzzle page at zero anchors, and that stays.
- **[Changed claim]** CARD-419's "static: no request" check becomes "one request, the book file" (owner 2026-11-16 asked for these cards; the lesson stays generic: no theme or book name in its own files).
