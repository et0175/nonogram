# CARD-454: Probe on a phone: one labelled strip — "Probing", Keep, Wrong guess

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/454-probe-on-phones (stacked on ux-review-cards: main is checked out in another session's worktree)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H3 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_probe.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T20:40Z
**Closed:** 2026-11-16T21:30Z
**Actual:** —
**Merge commit:** — (branch tip def92ad0; merges into main with ux-review-cards)
**Blocked by:** —

## Why

In portrait the Probe status is squeezed into a 30 px gap and shows as "Le t.."; in landscape the ✗ button wraps to a fourth row and pushes zoom and the Hints counter off the screen. The board shows bare ✓/✗ icons, Line view shows labelled buttons.

## What to implement

While probing, a full-width strip above the board: "Probing · new marks are dashed" with labelled **✓ Keep** and **✗ Wrong guess**, replacing the Probe button rather than adding to the toolbar. Same wording as Line view.

## Acceptance criteria

- **AC-1**: at 412×839 and 839×412 (and the 320/658 S9+ sizes) the status text is not truncated and no toolbar control leaves the viewport while probing.
- **AC-2**: Keep and Wrong guess carry text labels on the board as in Line view.

## Worktree notes
- **[Built, narrower than the card]** CARD-411's owner ruling (2026-11-10, "A") keeps Probe and its pair on ONE control row so opening a probe moves nothing, so a full-width strip above the board was not built. What shipped: the cut-off note is not drawn on an upright phone (<= 600 px). Measured at 412x839 and 320x658: note not drawn, no toolbar control past the viewport. Renders: ~/Documents/nonogram-reviews/CARD-454/.
- **[Tried and dropped]** Putting Wrong guess in the empty third cell of the landscape brush row: that row is the brush slot spanning all three columns, so the rule made a NEW row at the top of the strip. Reverted. In landscape the open probe still adds one strip row (the strip scrolls by CARD-402's design); CARD-459 (garland) gives the strip back ~60 px.
- **[Gate, 2026-11-16]** Player set (impact rule of 2026-11-09): 1440 passed, 1 failed, 9 skipped (DATABASE_URL unset). The red was `test_the_scroll_stays_inside_a_half_cell[390x844]`, which expected the note drawn; updated, file re-run 39 passed.
