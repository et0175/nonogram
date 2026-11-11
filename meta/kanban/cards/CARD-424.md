# CARD-424: The brush menu's four options are 142 x 36 px — the one tap target the compact floor does not reach

**Status:** ready
**Priority:** P3
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- The CSS is one declaration, as CARD-423's was. The cost is the decision below and the popover's growth: four options at 44 px instead of 36 add 32 px to a menu that opens over the board. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-423 review cycles 1, 2 and 3 — raised as an out-of-scope observation in all three and never carded, which is why it is carded here. Measured on the admin solve page at 390x844, 600x844 and 844x390.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-423
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py
<!-- Derived 2026-11-11 from where the measured behaviour lives: `.player-tool-item`'s own rule in admin.css, and the brush-menu module that already drives the menu open at 390 px. `tests/test_player_base_css.py`'s FROZEN[390] records the four options' `min-height` and WILL move if this lands — name it in the brief and re-record it the way CARD-423 did (the real Bootstrap is the pinned URL in `src/nonogram/admin/templates/base.html`, sha256 7f1d37f0…, and the two-step certification is in CARD-423's Worktree notes). Nothing under `player/`: admin.css is in COPIED_FROM_ADMIN. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-423 raised the compact toolbar's tap-target floor to 44 x 44 px on the eleven controls its AC-1 enumerated. The brush menu's four options are not among them and were not reached: `.player-tool-item` is a `<button>` inside `.player-toolbar` but carries no `.btn`, so neither CARD-423's `.player-toolbar .btn { min-height: 44px; }` nor CARD-402's landscape `.btn` rule touches it. Its own rule keeps `min-height: var(--control-h)` = 36 px.

**142 x 36 px, and the width is derivable rather than measured:** `.player-tool-menu`'s `min-width: 10rem` minus 2x8 px padding minus 2x1 px border = 142, which is why the figure is the same at 390x844, 600x844 and 844x390. `tests/test_player_base_css.py`'s `FROZEN[390]` records all four rows at `36px` on both sides of CARD-423's diff, so this is a second, independent record of the same fact.

**This is not a regression.** They were 36 px before CARD-423 too. What changed is that they are now the *only* sub-44 px tap target in the compact toolbar, in a menu whose whole purpose is choosing between four similar-looking swatches — the place where a mis-tap is least noticeable and most annoying, because picking White instead of Maybe silently marks the wrong thing.

Raised as an out-of-scope observation by **all three** of CARD-423's review cycles and carded only now; the delay is itself the argument for a card, since an observation nobody owns is re-measured every cycle and fixed in none.

## Decision owed before implementation (owner)

**D1:** the four options are 44 px tall, and the popover grows 32 px over the board; or they stay 36 px and the player keeps one sub-floor target; or they take an intermediate value that the 24 px floor of CARD-195 AC-11 already clears. **There is no default.** CARD-423's own D1 ruled on nine named controls and the owner has not been asked about these four, so an author who picks one is deciding for them. The popover opens over the board on a phone, which is exactly the trade CARD-423's D1 weighed for the toolbar — and there the owner chose the target over the space.

## What to implement

1. **One declaration** in `admin.css`'s compact block, beside CARD-423's, keyed on `.player-tool-item` — only if D1 says 44. `--control-h` does not change: it is the whole admin panel's control height.
2. **Re-record `FROZEN[390]`** in `tests/test_player_base_css.py`, the way CARD-423 did it: patch the moved rows from the measured actuals, then certify by running with `NONOGRAM_REAL_BOOTSTRAP` pointed at the pinned Bootstrap so the module's own sha-matched assert proves the table equals the real file's measurement. Append the card to `PROVENANCE`'s list. Do not skip the certification step — the ordering trap (the assert fires before the printing branch) is documented in CARD-423's notes.
3. **Nothing under `player/`:** `admin.css` is in `COPIED_FROM_ADMIN`, so the public player inherits this by the build-time byte-identical copy.

## Acceptance criteria

- **AC-1** (the floor reaches the menu): at 390x844, 600x844 and 844x390, with the brush menu open, each of the four `.player-tool-item` options has a border box at least 44 px tall. (test: change the existing `tests/test_puzzle_solver_brush_menu.py` cell that already drives the menu open at 390 px — `TestSolverBrushMenu_RegionIsItsOwnToggle::test_it_keeps_a_tap_target_and_the_toolbars_button_pattern_on_a_phone` is the sibling that asserts the toolbar's pattern; plant: drop the new declaration and the cell reds.)
- **AC-2** (the board is not covered differently than the owner ruled): with the menu open at 390x844 the popover still fits the viewport and no control is clipped; the measured growth is recorded in Worktree notes as the figure it became. (test: the existing brush-menu geometry cells.)
- **AC-3** (nothing else moves): the eleven controls CARD-423 floored are unchanged at every viewport, and `FROZEN[1280]` is untouched. (test: `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar` and `tests/test_player_base_css.py` unchanged apart from the re-recorded rows.)

**Net test count: 0 added** — one existing brush-menu cell gains the assertion, per the owner's test budget (2026-11-07).

## Worktree notes

—
