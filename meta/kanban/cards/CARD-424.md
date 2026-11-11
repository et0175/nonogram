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
**Depends on:** CARD-423, CARD-426
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_brush_menu.py
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

## Owner ruling, 2026-11-11

**D1: 44 px, like the rest.** The owner's words when asked: *"44 px, like the rest"* — one rule for every control the toolbar draws, the menu included, and the popover grows from about 174 px to about 206 px over the top-left of the grid. That is the same trade they took in CARD-423's D1, where the toolbar's own floor cost the board 24 px of height and they chose the target over the space; this card is that decision applied to the four controls CARD-423's enumeration did not name.

So: no author decides a height here, and the alternatives the card used to offer — stay at 36, or an intermediate value — are **declined**. An intermediate value is declined for a stated reason, not just unchosen: it would leave the menu the only control in the player at its own height, clearing neither the guideline nor the inconsistency.

**What is still an author's to measure, not to decide:** whether the taller popover still fits its viewport at 390x844 and at 844x390 (where CARD-402's block makes the menu `fixed` and `openMenu` already lifts it to end inside the window). If 44 px makes it run off the screen on a short landscape phone, that is a `[BLOCKER]` with the measurement, not a licence to pick 40.

## Ordering, decided with the ruling

`Depends on:` now names **CARD-426** as well as CARD-423. CARD-426 (the menu that will not close) was in flight when this ruling was given and edits the same `admin.css` compact block and the same `tests/test_puzzle_solver_brush_menu.py`. The owner chose to queue rather than run both: two agents rewriting one test module about one component is a guaranteed rebase and a real chance of one clobbering the other's work. The dependency is how that choice is enforced — `start` gates on it — rather than left to whoever reads the board next.

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

- **[Two minors inherited from CARD-426's cycle 2, 2026-11-11]** Both are in `solver.js` and both concern the menu this card is already changing, so they land here rather than as cards of their own (cut bar: each is smaller than a card and neither needs a decision). `Touches:` has gained `solver.js` for them.
  1. **A chrome dismissal drops focus to `<body>`.** Measured at 1440x900: opening the menu focuses the checked `.player-tool-item`; a pointer-down on the chrome then calls `closeMenu()`, which hides the menu around the focused element, and `document.activeElement` becomes `BODY`. `pick()` and Escape both call `trigger.focus()`; the chrome path does not. **Any fix must be scoped to the in-box case** — a blanket `trigger.focus()` in `closeMenu()` would yank focus back on an ordinary board tap, which is the opposite of what CARD-426's decision (b) ships.
  2. **The exemption selector is globally scoped.** `closest("#puzzle-player-tool-trigger, .player-tool-item")` matches that class anywhere in the document. Harmless today — six elements, all inside the menu, across both templates — but a future control reusing the class outside the box would silently stop dismissing the menu. `#puzzle-player-tool-menu .player-tool-item` is the scoped form.
