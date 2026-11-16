# CARD-454: Probe on a phone: one labelled strip — "Probing", Keep, Wrong guess

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H3 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/pages.js, player/player.css, src/nonogram/admin/static/solver.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

In portrait the Probe status is squeezed into a 30 px gap and shows as "Le t.."; in landscape the ✗ button wraps to a fourth row and pushes zoom and the Hints counter off the screen. The board shows bare ✓/✗ icons, Line view shows labelled buttons.

## What to implement

While probing, a full-width strip above the board: "Probing · new marks are dashed" with labelled **✓ Keep** and **✗ Wrong guess**, replacing the Probe button rather than adding to the toolbar. Same wording as Line view.

## Acceptance criteria

- **AC-1**: at 412×839 and 839×412 (and the 320/658 S9+ sizes) the status text is not truncated and no toolbar control leaves the viewport while probing.
- **AC-2**: Keep and Wrong guess carry text labels on the board as in Line view.

## Worktree notes
