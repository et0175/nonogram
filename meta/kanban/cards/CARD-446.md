# CARD-446: How to solve draws like the player — ruled grid, clue rings, crosshair, the quiet probe — and How to play names Undo, Redo, Reset and Line

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: CARD-444's three proposals plus following CARD-435 in the lesson's probe demo; the lesson now imports the player's pure module instead of copying its rules. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/446-lesson-draws-like-the-player
**Worktree:** ../PythonProject4-card-445 (created under that name before CARD-445 was found taken; the card number is 446)
**Source:** owner 2026-11-16 (project thread): *"please fix your 3 findings also"* — CARD-444's three proposals: the clue rings and crosshair on the lesson's boards, its cells as the player's ruled grid, and Undo/Redo/Reset and Line in the player's own How to play list.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-444, CARD-435
**Touches:** player/how-to-solve.html, player/how-to-solve.js, player/player.css, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, tests/test_how_to_solve_page.py, tests/test_player_shared_ui_site.py, tests/test_player_base_css.py (FROZEN: one row), tests/test_puzzle_solver_marking.py (the How to play bullets)
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T06:40Z
**Closed:** 2026-11-16T07:40Z
**Actual:** —
**Merge commit:** 6d62bda5
**Blocked by:** —

## What to implement

1. **The player's rules, imported.** `how-to-solve.js` imports `circledNumbers` and `clickedState` from `/solver_state.js` (the play page's byte-identical copy, served at the site root), so a tap and a ring are the player's own code, not a copy. CARD-444's reimplemented tap rule is retired (`tappedState` is now that import).
2. **Rings.** Each clue box draws one span per number; a number the marks settle is circled with a thin grid-ink ring (a pill for two digits) exactly where the player would circle it. The row-clue column grows to fit its rings.
3. **Crosshair.** Pointing at a square tints its row, its column and their two clue boxes (the player's two tints).
4. **Ruled grid.** The demo boards drop the rounded tiles: thin `--player-thin` rules, a heavy grid-ink rule round the frame and after every fifth line; black cells carry the player's inset hairline; the squeeze strips likewise, heavy after the fifth.
5. **The quiet probe (CARD-435).** The probe demo gains Hint (the bulb). A broken line is not shown until Hint is pressed during the probe; then the clue turns the player's broken red, Wrong guess is flagged, and the player's sentence reads "Hint: this guess breaks column 1."; the next press withdraws both. Only the clue is red now, as on the player (the cells are no longer tinted). Step 4's text says so.
6. **How to play** (the player's own list): Undo and Redo, Reset, and Line (`data-player-howto-line`, `hidden` until solver.js's `syncLine` shows it with the Line button). The lesson's step 5 follows through the CARD-444 sync test.

## Acceptance criteria

- **AC-1** (rings, crosshair): on the solved try-one board every number is circled; a hovered square crosses 9 squares and 2 clue boxes. (test: `test_try_one_marks_black_white_and_maybe_and_show_me_solves_it`)
- **AC-2** (the player's colours): the lesson's thin rule, crosshair tints and broken red are admin.css's expressions. (test: `test_the_lesson_uses_tokens_and_the_players_probe_colours`)
- **AC-3** (quiet probe): no red, no flag until Hint; after it both, with the sentence; Keep withdraws them. (test: `test_the_probe_demo_runs_like_the_players_probe`)
- **AC-4** (How to play): step 5 equals the player's list (now with Undo/Redo, Reset, Line) and draws the undo, refresh and Line icons from their sources (test: `test_the_lessons_buttons_are_the_players`); the public page's text names only controls it shows, Line's bullet hidden with its button (test: `howto_problems` in `tests/test_player_shared_ui_site.py`, which now reads shown bullets only and knows Undo, Reset and Line).

## Worktree notes
- **[Guards changed, 2026-11-16]** `test_player_shared_ui_site.py`'s `HOWTO_CONTROLS` gains Undo, Reset and Line, and `howto_problems` reads `li:not([hidden])` (Line's bullet is hidden wherever its button is); `test_how_to_solve_page.py`'s colour pin gains `--hts-thin`, `--hts-cross`, `--hts-cross-ink`, `--hts-broken`, its icon pin gains undo, refresh and solver.js's `LINE_ICONS.line`, and its probe walk asserts the quiet rule instead of the immediate red. `test_player_base_css.py`'s FROZEN table gains ONE row per width, "30 li " (the Line bullet, [hidden] on the census's 10 x 8, and SAMPLE collects [hidden]); its value was measured against the real Bootstrap (sha256 verified), which named that row as the only difference and our stylesheet as equal to it; no other row moved. `test_puzzle_solver_marking.py`'s `test_the_page_copy_describes_the_new_click` pins the How to play bullets word for word and gains the three.
- **[Measured, 2026-11-16]** 360/390/1280: `scrollWidth` equal to the viewport; the probe board inside its card at 360 and 390 (it overflowed left with three ringed row numbers until the clue column was let grow). Before/after: `~/Documents/nonogram-reviews/CARD-446/`.
- **[Gate, 2026-11-16]** First run of the 14 player/lesson/site files: 571 passed, 8 red, every one green on `main`. Six were this card's: the FROZEN row (above), the bullets pin (above), and three served-tree scans (`test_assembled_site_is_self_contained`, `test_no_homegrown_tracking`, `test_ac392s_own_scan_of_the_tree_is_empty_and_finds_a_plant`), which read the text between the Undo icon's closing quote and the Redo icon's `class="` — `/></svg><svg class=` — as an address resolving to nothing; the Undo icon's path now closes with `></path>`, so no quoted run starts with `/`. The other two (`TestPublicMode_LandscapeToolStrip`, `TestSolverPage_EmphasisesEveryFifthLine`) passed when re-run alone and on the full re-run: 579 passed, 0 failed, 0 skipped.
