# CARD-407: A big puzzle opens at Fit — the player sees what they are solving before they zoom in

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- One decision (what counts as big and what the opening zoom is) on top of CARD-406's model; small, but it changes the first thing every owner and player sees, so it carries the owner's go in the Source. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/407-open-at-fit
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-407
**Source:** owner player findings 2026-11-07, item 2: "Big puzzles would open at Fit, so the player sees what they're solving." 'Big' is not defined by the owner (owner Q11).
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-406
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_zoom.py, tests/test_puzzle_solver_resume.py, tests/test_puzzle_solver_page.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. -->
**Review score:** —
**Started:** 2026-11-09T17:30Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-195 rule 6: zoom is never saved and starts at 100% on every load. CARD-406 adds the Fit floor. This card changes the INITIAL zoom for big puzzles: instead of 100% they open at Fit. 'Big' candidates: the board does not fit the stage at 100% (the objective rule, recommended: it reuses `fitZoom < 100`); or a side past `BIG_SIDE = 15` (the existing constant for the clue doubling); or a cell-count threshold. Owner Q11 chooses; Q12: whether the same applies on desktop (a 30 x 30 at 1280 x 720 scrolls 91 px at 100%; Fit would shrink it to nearly the 14 px floor-less size) or only compact screens.

**[OWNER RULING 2026-11-07, on the drafter's question]** A 'big' puzzle is one whose whole board does not fit on screen at 100% zoom (objective: reuses the Fit computation); applies on compact screens (phones) only at first; desktop keeps opening at 100%.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **The opening zoom** is `fitZoom` when the chosen 'big' rule holds, otherwise 100% (unchanged). A reload re-applies the rule (nothing is saved).
2. **A resume does not override the player:** zoom was never part of the save, so a resumed board opens at the rule's zoom, not at the last one (state this in the page text where zoom is described).
3. **The first draw is not wasted:** the board is drawn once at the opening zoom (no 100% flash then a redraw), measured by counting `drawBoard` calls the way `TestSolverClues_TheLadderStopsAtTheFirstRungThatFits` does.

## Acceptance criteria

* **AC-1** (opens at Fit): a puzzle the rule calls big opens with the readout 'Fit' and the whole board visible; one the rule calls small opens at 100%. (test: new browser cells with the boundary neighbour on each side; plant: invert the rule)
* **AC-2** (not saved): a reload after zooming to 200% reopens at the rule's zoom. (test: re-pointed `TestSolverZoom_IsNotSavedAndSendsNothing`)
* **AC-3** (one draw): the number of `drawBoard` calls to first paint is unchanged from the merge-base. (test: the ladder-count cell, unchanged expectations)
* **AC-4** (existing opens): every existing cell that assumes 'opens at 100%' on a board the rule now calls big is changed ONLY with the owner finding named as the reason; the rest pass unchanged. (test: node-id difference with the list)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).

* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)


## Architecture context

FR-044 (the admin puzzle player, TERM-037) and FR-045 (public player, COMP-011) — the public player gets this behaviour by the shared-UI mode, not by its own code. The author reads the AC ids in `requirements.yml` FR-044 and amends exactly the ones whose claim changes (do not guess ids; AC-345..AC-347 are the circling ACs).

## How this reaches the public player

One source of truth (owner direction 2026-11-07; ADR-0041/R3): the change is made ONLY in the admin files (`src/nonogram/admin/static/solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and the admin templates). Nothing in `player/play.js`, `player/player.css` or `player/play.html` is edited or tested by this card: CARD-399 retires them, and production serves `play.js` until the owner deploys the shared-UI mode, so this card reaches production only through the shared-UI rebuild and that deploy (the owner's timing; CARD-394 and CARD-399 are NOT dependencies of this card). What the card owes the public side:

* the shared-UI tree assembled from the changed files passes `tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity` with no edit to the table it holds (the copies stay byte-identical; no override layer, no public-only rule);
* the behaviour is verified ONCE, on the admin page (owner test-budget ruling, 2026-11-07): no duplicate public-mode cell is added; a public-mode cell exists only where the behaviour differs in public mode (for example Check and the error counter do not exist there); CARD-385's existing public-mode sweep and the byte-identity test cover the copy;
* the served-tree scan (`TestSharedUi_TheServedTreeCarriesNoAnswer`) still passes: a feature that needs the answer is not allowed to read it in public mode (ADR-0041/R2).

## Viewports the card must verify

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390 x 844** (phone portrait), **844 x 390** (phone landscape), **1280 x 720** and **1440 x 900** (desktop), each on a 15 x 15 board and on the owner's 30 x 29 class of board (use a 30 x 30 stored grid; the exact puzzle 1750b436-... is in the production database, which is off limits to this work). For each: no horizontal page scroll, no control clipped, the board does not move when the thing the card changes appears or disappears, and the card's own claim.

## Worktree notes

[Env] forge from /Users/omelnikova/MyProjects/forge_1; orchestrated from the player-phone thread. Cut from card/406 (merged 63703247 before this card's review).
[Impl 2026-11-09] 3e4be450. Q11/Q12 answered by the owner's ruling of 2026-11-07 on the card: "big" = the board does not fit at 100% (fitZoom < 100); compact screens only (CARD-401's media condition), desktop keeps 100%. solver.js: at the first measureFit after the first draw, openAt(floor) when compact; no redraw (AC-3: the draw count to first paint is unchanged — the zoom is a CSS multiplier applied after the draw).
[Tests] AC-4: rather than re-pin the ~32 cells that measure the 100% board on a phone, the shared helpers (_open in test_puzzle_solver_page.py, _open_editor) return a Fit opening to 100% and the stage's home, the owner finding named in the docstring; keep_opening_zoom=True opts out. New cell TestSolverZoom_Fit::test_a_big_board_opens_at_fit_on_a_compact_screen_only (plant: inverting the compact condition reds it — run). AC-2 (not saved): zoom was never saved; a reload re-applies the rule (the stage sweep's reloads exercise it). Net node ids +1.
[AC-4 list] The cells the helper returns from Fit to 100% — the 32 that went red before it (measured on this branch, 2026-11-09): zoom.py::TestSolverZoom_PinchOnTheBoardZooms::test_spreading_100_to_200px_on_a_cell_reads_200_percent_and_marks_nothing[chromium]; zoom.py::TestSolverZoom_PinchOnAClueBoxIsNotTheBoardsZoom::test_a_pinch_starting_on_a_column_clue_box_is_left_to_the_browser[chromium]; zoom.py::TestSolverZoom_StageEndsAboveTheFold::test_sweep[chromium]; zoom.py::TestSolverZoom_StageEndsAboveTheFold::test_a_resize_keeps_the_board_and_its_scroll[chromium]; zoom.py::TestSolverZoom_Fit::test_fit_shows_the_whole_board_and_says_so[chromium-390-844]; zoom.py::TestSolverZoom_Fit::test_fit_shows_the_whole_board_and_says_so[chromium-844-390]; clues.py::TestSolverClues_TheCircleIsVisible::test_two_digit_rings_clear_their_digits_on_a_30x30[phone]; clues.py::TestPlayerNumerals_ColumnFloorIsTheWidestColumnNumeral::test_one_digit_column_numbers_keep_the_fit; clues.py::TestPlayerNumerals_ColumnFloorIsTheWidestColumnNumeral::test_a_two_digit_column_number_sets_the_floor_at_390_without_the_phone_floor; clues.py::TestPlayerNumerals_ColumnNumbersDecideTheStageScroll::test_the_stage_scrolls_and_the_page_does_not; clues.py::TestSolverClues_SmallBoardsUnaffectedByStickiness::test_a_resize_after_a_zoom_re_measures_the_room; clues.py::TestSolverClues_SmallBoardsUnaffectedByStickiness::test_a_grown_window_re_measures_the_room_too; clues.py::TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[390x844]; clues.py::TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::test_each_axis_keeps_its_clues_exactly_when_it_has_the_room[600x844]; fifth_rule.py::TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::test_a_light_band_reads_across_the_fifth_rule[phone-x]; fifth_rule.py::TestSolverFifthRule_FilledCellsDivideAcrossMajorRules::test_a_light_band_reads_across_the_fifth_rule[phone-y]; fifth_rule.py::TestSolverFifthRule_GeometryAndOtherMarksUnchanged::test_the_hairline_takes_no_part_in_layout[phone]; maybe.py::TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell::test_glyph[30x30@390]; page.py::TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways; phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_cell_matches_the_formula_and_clears_the_old_floor[15x15]; phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_cell_matches_the_formula_and_clears_the_old_floor[25x15]; phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_cell_matches_the_formula_and_clears_the_old_floor[30x30]; phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_stage_scrolls_exactly_when_the_column_floor_exceeds_the_fit[15x15]; phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_stage_scrolls_exactly_when_the_column_floor_exceeds_the_fit[25x15]; phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_stage_scrolls_exactly_when_the_column_floor_exceeds_the_fit[30x30]; phone.py::TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit::test_a_30x30_at_390_keeps_one_mirrored_gutter_per_axis; phone.py::TestSolverPhone_MirroredGutterSticks::test_both_bands_are_in_view_at_every_corner; phone.py::TestSolverPhone_MirroredGutterSticks::test_a_390px_phone_keeps_its_cells_rather_than_its_row_clues; zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_zoom_in_once_reads_125_percent_and_scales_every_cell; zoom.py::TestSolverZoom_TheBoardScrollsInsideItsStage::test_300_percent_scrolls_the_stage_both_ways_never_the_page; zoom.py::TestSolverZoom_ZoomKeepsTheViewCentre::test_zoom_out_keeps_the_same_cell_near_the_stages_centre; puzzle_editor_ui.py::TestPuzzleEditor_TheBoardKeepsItsCluesByTheSameRule::test_a_resize_after_a_zoom_re_measures_the_editors_room.
[Review 1/3] Score: 8.5 — opening rule sound (mutants re-decide-every-time and drop-compact both caught); the helper strategy honest. Important: the page text (puzzle_solve.html, solver.js ZOOM) still said "100% on every load" — fixed 7be3f1b9, stating the rule and that a reload/resume applies it again. Lows fixed: one zoom-back helper, the docstring citation, the 200 ms sleep, compact-condition cross-references; this note lists AC-4's cells. Report meta/review/20261109T183000Z-CARD-407-cycle1.yml.

