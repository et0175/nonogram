# CARD-459: The garland gives way in landscape, and the back link is short

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.2d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/459-landscape-garland (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M3 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/decor.css, player/assemble.py (the site loader), tests/test_book_landing_page.py, tests/test_player_shared_ui_site.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T22:10Z
**Closed:** 2026-11-16T22:40Z
**Actual:** —
**Merge commit:** d3cb3ccc (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

In phone landscape the garland takes ~60 of 412 px above the board; the back link truncates to "← Christmas Nonog…".

## What to implement

In landscape (height < 500 px) the garland shrinks to a thin strip or hides in the player; the back link reads "← Book" (full title in its accessible name).

## Acceptance criteria

- **AC-1**: at 839×412 the garland is ≤ 16 px tall in the player.
- **AC-2**: the back link is not truncated.

## Worktree notes
- **[Built, AC-1 changed]** The garland is 32 px in landscape, not the card's <= 16 px: decor.js draws a fixed eight tiles and at 24 px they ended at 720 px, short of an 863 px phone. 32 px reaches 960 px. Applies to the book landing in landscape too (same rule). Renders: ~/Documents/nonogram-reviews/CARD-459/.
- **[Built]** "← Book" on a compact screen ((max-width: 600px), (max-height: 500px)), via matchMedia in `wayBack`; `aria-label` "Back to <title>". This retires CARD-436's declared residual (name clipped at 390 x 844); the test that pinned it was re-stated.
