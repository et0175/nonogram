# CARD-466: Zoomed in, only the board scrolls

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/466-page-stays-put (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M10 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_player_base_css.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-17T02:45Z
**Closed:** 2026-11-17T03:30Z
**Actual:** —
**Merge commit:** 91855131 (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

Zoomed in, the board scrolls in its own frame while the page is also taller than the screen (861 vs 839 px portrait, 422 vs 360 px landscape), so an edge drag can move the page and the toolbar slides away.

## What to implement

While zoomed in, the board frame is sized so the page itself does not scroll; How to play sits below the fold.

## Acceptance criteria

- **AC-1**: zoomed in at 412×839 and 839×412, document scroll height equals the viewport height.

## Worktree notes
- **[Built, narrower than AC-1]** The cause was mostly `.main`'s 56 px bottom padding (above 820 px wide, which includes a phone held sideways). Now 16 px on the solve page, 4 px sideways. Measured on the live 30x29: sideways 58 -> 10 px open (10 zoomed), desktop 52 -> 12 open / 22 zoomed, portrait zoomed 22 px unchanged.
- **[Open]** The last 10-22 px are the "How to play" line below a stage whose height reserves only 16 px under it (admin.css's own CARD-403 comment measures this slack). Closing it means the stage reserving that line too: every stage height the suite pins moves by ~22 px. Not done here.
