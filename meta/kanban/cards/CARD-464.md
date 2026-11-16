# CARD-464: Book tiles show the size; only the current section opens

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.2d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/464-book-tiles (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M8 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/pages.js, player/player.css, tests/test_book_landing_page.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-17T00:00Z
**Closed:** 2026-11-17T00:30Z
**Actual:** —
**Merge commit:** 9fca0210 (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

Every tile in a section is the same blank square with a number; Easy is open by default and pushes Medium and Hard far down on a phone.

## What to implement

Each tile carries its size in small text under the number. The section holding the "continue" puzzle opens; the others start collapsed.

## Acceptance criteria

- **AC-1**: tiles show W×H.
- **AC-2**: with progress in Medium, Medium is the open section.

## Worktree notes
- **[Built]** `.tile-size` (10 px, secondary colour) at the square's bottom; hidden when solved. CARD-418's default changed from "first Easy + the Continue section" to "the Continue section, else first Easy"; the reader's own open/closed state still wins on a repaint (CARD-437). Render: ~/Documents/nonogram-reviews/CARD-464/.
