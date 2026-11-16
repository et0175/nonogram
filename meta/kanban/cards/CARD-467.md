# CARD-467: Region's automatic switch-off says so

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/467-region-zoom-toast (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M11 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_page.py, tests/test_browser_fixture_scope.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-17T00:30Z
**Closed:** 2026-11-17T01:40Z
**Actual:** —
**Merge commit:** c747543a (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

Region turns off when zooming in so that drags scroll; the only sign is the button losing its green.

## What to implement

The first time it happens in a session, a short toast: "Zoomed in: drag now scrolls. Turn on Region to paint by dragging."

## Acceptance criteria

- **AC-1**: zooming in from a fitted board with Region on shows the toast once per session.

## Worktree notes
- **[Built]** Wording: "Zoomed in: dragging now moves the board. Turn on Region to paint by dragging." Gated on `readerZoomed` (set by the zoom buttons, the Fit readout and a pinch): the first build said it on the page's own opening at 390 x 844, measured by `test_the_line_moves_neither_the_toolbar_nor_the_board`.
- **[Test helper]** `_to_hundred` zooms with the readout like a reader, so it now presses Escape when the box shows. Gate after that: 1442 passed, 9 skipped.
