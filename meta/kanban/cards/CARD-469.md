# CARD-469: The Hints counter counts what its label says

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.25c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/469-cells-revealed (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding L2 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, tests/test_player_shared_ui_site.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py
**Review score:** — (no review cycle; owner request, 2026-11-17)
**Started:** 2026-11-17T02:50Z
**Closed:** 2026-11-17T05:00Z
**Actual:** —
**Merge commit:** be28ac2f (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

After two Hint presses the counter still shows 0; it counts revealed cells while the label says "Hints".

## What to implement

Rename it "Cells revealed", or count every press — owner to choose at pick-up (default: rename).

## Acceptance criteria

- **AC-1**: label and figure agree.

## Worktree notes
- **[Built]** Owner 2026-11-17 "do l2". Label "Revealed: N" — "Cells revealed:" was tried first and wrapped onto two lines at 412 px. On the ADMIN page the wider word costs the 30x30 stage 5 px at 600x844 (two pins re-stated). Renders: ~/Documents/nonogram-reviews/CARD-469/.
- **[Gate, 2026-11-17]** One player-set run over 469+455+458+468 stacked: 1442 passed, 9 skipped (DATABASE_URL unset).
