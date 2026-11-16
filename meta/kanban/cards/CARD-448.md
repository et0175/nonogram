# CARD-448: The landscape tool strip three wide, so every control is on a landscape phone's screen

**Status:** done
**Priority:** P1
**Category:** bug
**Estimate:** 1c (0.25d)
<!-- Basis: four values in the landscape block (strip and title width, the zoom pill's row) and the two tests that pinned the two-wide geometry. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/448-landscape-three-wide
**Worktree:** ../PythonProject4-card-448
**Source:** Anna's QA checklist (handed over by the owner 2026-11-16), items 2 and 5: *"in landscape the Hints button is missing"*, *"the menu is cut off in landscape"*. The owner chose "three wide" the same day, narrowing the 2026-11-10 ruling "B, two buttons wide" (CARD-402).
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-402, CARD-428, CARD-430
**Touches:** src/nonogram/admin/static/admin.css, tests/test_player_public_mode.py, tests/test_puzzle_solver_zoom.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T13:40Z
**Closed:** 2026-11-16T14:20Z
**Actual:** —
**Merge commit:** 6fb3a4ab
**Blocked by:** —

## Why

Two wide, the landscape strip was about 390 px tall; a landscape phone gives it 300 or less. Measured on the live site: at 844x390 Probe and the Hints counter sat below the edge, at 844x340 (Safari's landscape window with its bars) the zoom too — reachable only by scrolling the strip, which nobody discovers.

## What to implement

The landscape block (`@media (max-height: 500px) and (orientation: landscape)`): the strip `repeat(3, 44px)`, the title above it as wide, and the zoom pill as one row — minus, plus, the readout (Fit) — instead of the pair over a spanning readout; its radius the pill's 22 px. Portrait (CARD-438 in flight) untouched.

## Acceptance criteria

- **AC-1** (every control on screen): at 844x390, 852x393, 874x402 and 844x340 the strip is at most three buttons wide, left of the board, and its lowest control is inside the strip's view with the page unscrolled; the brush menu is tappable. (test: `TestPublicMode_LandscapeToolStrip::test_the_tools_stand_in_a_strip_left_of_the_board`, which reds on `main`'s stylesheet: lowest control 354 against a view of 324)
- **AC-2** (the zoom pill): minus, plus and the readout share one row in that order, adjacent, each at least 44 px. (test: `TestSolverZoom_TapTargetsAreAtLeast24px::test_zoom_buttons_and_300_percent_cells_are_at_least_24px`)

## Worktree notes
- **[Measured, 2026-11-16]** Local assembled site, Chromium touch: at 844x390 and 932x380 Hint, Probe, zoom, brush and the Hints counter all on screen for a 14x14 and a 30x30; at 844x340 every control on screen and only the counter's text ("Hints: 0") below the edge; the brush menu's four items fully visible at both heights. The board's box is unchanged (334 x 318 at 844x390 for the 14x14). Before/after: `~/Documents/nonogram-reviews/CARD-448/`.
- **[Gate, 2026-11-16]** The 14 test files that measure 844-wide viewports: 620 passed, 2 red, both pinning the two-wide geometry on purpose (the strip's width cap and the readout's row below the pair), updated with the old claim kept in their comments.
