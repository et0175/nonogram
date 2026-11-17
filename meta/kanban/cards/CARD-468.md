# CARD-468: Probe marks read on small cells

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/468-probe-marks-visible (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding L1 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_probe.py, tests/test_admin_design_tokens.py
**Review score:** — (no review cycle; owner request, 2026-11-17)
**Started:** 2026-11-17T02:50Z
**Closed:** 2026-11-17T05:00Z
**Actual:** —
**Merge commit:** be28ac2f (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

At ~16 px cells the dashed amber edge is barely visible, so probe marks look like normal blacks; it reads well only in Line view.

## What to implement

Below a cell-size threshold, probe cells also get a light amber fill.

## Acceptance criteria

- **AC-1**: a probe cell under the threshold has a fill distinct from a kept cell.

## Worktree notes
- **[Blocked, 2026-11-17]** Tried: a warm lighter ink on probed blacks (`color-mix(--grid-ink 72%, --player-probe)`). Refused by `TestSolverProbe_TheMarkerIsMeasurablyApartFromItsGround` (three ink cases), whose docstring records the owner's 2026-10-30 fix: the marker moved to the outline CHANNEL rather than a ground tint, so a later ground tint cannot collide with it. A fill is exactly that ground tint. Reverted; asks the owner whether to reopen that ruling (or to thicken the outline on small cells instead).
- **[Unblocked, built]** Owner 2026-11-17 "do l1", reopening the 2026-10-30 outline-only choice. A probed black on the board: `color-mix(in srgb, var(--grid-ink) 70%, var(--player-probe))`; the Line view keeps the plain ink. Render: ~/Documents/nonogram-reviews/CARD-468/probe-vs-kept-port.png.
- **[Gate, 2026-11-17]** One player-set run over 469+455+458+468 stacked: 1442 passed, 9 skipped (DATABASE_URL unset).
