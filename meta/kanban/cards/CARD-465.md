# CARD-465: Zoomed in on a landscape phone, the clue band leaves room for the board

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/465-landscape-side-decor (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M9 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/decor.js, player/decor.css, tests/test_book_landing_page.py
**Review score:** — (no review cycle; owner request, 2026-11-17)
**Started:** 2026-11-17T05:20Z
**Closed:** 2026-11-17T06:00Z
**Actual:** —
**Merge commit:** 795ecc90 (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

At 125 % in phone landscape the board area is ~270 px; the sticky column clues take ~110 px of it and the garland 60 px above, so ~8 of 29 rows show.

## What to implement

In landscape, the sticky clue band uses a smaller numeral size when zoomed in (with M3 removing the garland).

## Acceptance criteria

- **AC-1**: at 839×412 and 125 %, at least 12 rows of the 30×29 are visible.

## Worktree notes
- **[Skipped, 2026-11-17]** M9: the owner kept CARD-196's 12 px numeral floor (2026-11-17: "do h4, m2, l1, l2", M9 not among them).
- **[Reopened and built, 2026-11-17]** Owner on M9: "I'd remove the garland but maybe add some decoration to the right". Not the card's smaller-numerals fix (the 12 px floor stays): on the PLAY page held sideways the garland is not drawn and a side bough (`sideTile`, baubles on short strings) hangs down the right edge in a 60 px strip `.main` keeps free. Landing keeps CARD-459's 32 px garland. The 30x29 board at 839x412 gains the garland's height. Renders: ~/Documents/nonogram-reviews/CARD-465/. Gate: player/site set 415 passed.
