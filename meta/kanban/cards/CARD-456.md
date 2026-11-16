# CARD-456: Two-digit clues stay apart on 25–30 wide boards

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1c (0.3d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/456-two-digit-clues (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding H5 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** 80
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_clues.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T21:30Z
**Closed:** 2026-11-16T22:10Z
**Actual:** —
**Merge commit:** cd0f9180 (on ux-review-cards; into main with it)
**Blocked by:** —

## Why

On 30-wide boards "17 2", "12 13", "16 14" and "1 10 1" touch their neighbours at phone and desktop sizes; "1213" can read as one number.

## What to implement

Two-digit numerals get a condensed rendering (tighter letter spacing or a smaller size) so each fits its own column, and column-clue cells get a faint vertical rule.

## Acceptance criteria

- **AC-1**: on the 30×29 book puzzle at Fit, no two-digit numeral's box overlaps a neighbouring column's box (measured from the DOM).

## Worktree notes
- **[Built, narrower than the card]** CARD-196's 12 px numeral floor is an owner decision (2026-10-06), and at that floor two digits ARE the 14.4 px column floor, so a smaller size was refused by `test_30x30_numerals_never_fall_below_12_px`. What shipped: `data-wide` on two-digit column numbers and `letter-spacing: -0.12em`. Gaps on the live 30x29: 0.9 -> 3.8 px (1280x800), -0.5 -> 1.5 px (412x839 Fit), -0.5 -> 0.8 px (839x412 Fit, 5.6 px numerals). No faint rule added: the column clue cells already draw one.
- **[Tried and dropped]** `padding-left`/`margin-right` compensation and `text-indent`: each moved the circled-number ring off centre (`test_two_digit_rings_clear_their_digits_on_a_30x30`). Letter-spacing alone keeps the ring centred.
- **[Open]** A real separation at phone Fit would mean raising CARD-196's column floor above two digits' width, which makes every two-digit board a little smaller on screen: an owner call, not taken here.
