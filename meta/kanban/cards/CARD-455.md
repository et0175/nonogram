# CARD-455: Hint speaks by clue and stays off the board

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/455-hint-placement (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H4 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_hint.py
**Review score:** — (no review cycle; owner request, 2026-11-17)
**Started:** 2026-11-17T02:50Z
**Closed:** 2026-11-17T05:00Z
**Actual:** —
**Merge commit:** be28ac2f (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

The hint box opens over the middle of the board, hiding the rows and clues it talks about. It says "the highlighted column (1)" though no line numbers are shown, and "the 17-run" is jargon that breaks as "17-" / "run".

## What to implement

Dock the hint above the board (phones: in the free space under it when that is visible). Name lines by position and clue: "Look at the first column (clue 17)." and "The block of 17 is longer than half the column, so its middle cells must be black." Ordinals for 1–3 and "column 12" beyond.

## Acceptance criteria

- **AC-1**: the hint never overlaps a board cell or clue at the three viewports.
- **AC-2**: no hint sentence names a line by a bare index in parentheses; "run" is replaced by "block".

## Worktree notes
- **[Built]** Owner 2026-11-17 "do h4", superseding the CENTRE of CARD-427's ruling. `placeExplain`: with a line lit, the box goes to the top or bottom edge away from it (column -> bottom); no line -> centred. Sentences: "Hint: look at the highlighted column 1 (clue 17)." and "... — wherever the block of 17 can sit, it always covers the same cells, so they are black." The CARD-427 test now holds "covers none of the lit line" on its board.
- **[Residual]** In landscape the box at the bottom still covers the bottom rows of a lit column (the box is wider than the free space beside the board). Renders: ~/Documents/nonogram-reviews/CARD-455/.
- **[Gate, 2026-11-17]** One player-set run over 469+455+458+468 stacked: 1442 passed, 9 skipped (DATABASE_URL unset).
