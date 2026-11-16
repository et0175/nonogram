# CARD-453: A solved puzzle offers the way on — Next puzzle and Back to the book

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1.5c (0.5d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/453-next-puzzle
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H2 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/assemble.py (the site loader), tests/test_player_shared_ui_site.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T20:05Z
**Closed:** 2026-11-16T20:40Z
**Actual:** —
**Merge commit:** ae03d784
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
- **[Built]** In the site loader (`wayOn` in `player/assemble.py`), beside the way back. Rendered solved at 1280x800, 412x839, 839x412: ~/Documents/nonogram-reviews/CARD-453/after-*.png.
- **[Not done, by choice]** The editing buttons are NOT hidden once solved: they belong to the shared solver.js, and Reset is how a reader replays a solved puzzle. The light-blue Show grid in the QA shot was the default theme; in the Christmas theme it is the theme's own colour, so nothing was changed.
- **[Residual]** On an 839x360 phone in landscape the row sits partly below the fold (the page is already taller than the screen there); CARD-459 (garland) and CARD-465 (page scroll) remove that.
