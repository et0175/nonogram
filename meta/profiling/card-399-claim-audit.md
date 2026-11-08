# CARD-399 claim audit (step 1: classify, delete nothing)

Author: CARD-399 audit-step author, 2026-11-08, worktree `PythonProject4-card-399`, branch `card/399-retire-play-js`, cut from main `79c5052d`. Method: `ast` over the test files, node ids and seconds read from the quiet CARD-395 gate rerun (`~/Documents/nonogram-reviews/suite-profile-2026-11-07/gate-card395-rerun-durations.txt`, 11699 call phases), survivors resolved by `ast` and by that same id list. **No pytest was run** (the full-suite lock `meta/kanban/.full-suite.lock` was present and a gate pytest, pid 64397, was live when I started), so **no plant was run**: every survivor below is verified to EXIST once and be COLLECTED, and its claim was read at its class/test docstring and name, but its plant-run (card AC-2) is a task of the deletion step. Every figure is labelled mine (derived in this run by a command) or carried.

## 0. Verdict in numbers (mine)

| class | node ids | gate seconds (summed, quiet rerun) |
|---|---|---|
| RETIRE-TWIN | 134 | 69.8 |
| RETIRE-MOOT | 542 | 673.5 |
| KEEP-LIVE | 279 | 298.0 |
| CONVERT | 20 | 21.8 |
| LOST | 27 | 19.7 |
| **total in scope** | **1002** | **1082.8** |

Retired by the deletion step = RETIRE-TWIN + RETIRE-MOOT = **676 ids, 743.3 s summed** (12.4 min; x0.74 solo scaling, carried factor = 9.2 min). The card's planning figure was 917.1 s for the seven feature files on a contended run; on the quiet rerun those seven files sum to 758.8 s (probe 425.8, hint 149.2, zoom 115.4, circles 41.8, crosshair 21.4, maybe 2.7, agreement 2.5) and **738.9 s** of that is retired (the rest, 19.7 s, is LOST rows kept until the owner rules).

### 0.1 Per file

| file | RETIRE-TWIN | RETIRE-MOOT | KEEP-LIVE | CONVERT | LOST | ids | s |
|---|---|---|---|---|---|---|---|
| tests/test_public_player.py | 12 / 4.0 s | 2 / 0.2 s | 15 / 1.2 s | 5 / 0.7 s | 0 / 0.0 s | 34 | 6.1 |
| tests/test_public_player_pages.py | 0 / 0.0 s | 0 / 0.0 s | 31 / 7.7 s | 2 / 0.7 s | 0 / 0.0 s | 33 | 8.4 |
| tests/test_public_player_agreement.py | 0 / 0.0 s | 193 / 2.5 s | 0 / 0.0 s | 0 / 0.0 s | 0 / 0.0 s | 193 | 2.5 |
| tests/test_public_player_circles.py | 20 / 9.5 s | 65 / 31.8 s | 0 / 0.0 s | 0 / 0.0 s | 1 / 0.4 s | 86 | 41.8 |
| tests/test_public_player_crosshair.py | 22 / 9.7 s | 31 / 0.8 s | 0 / 0.0 s | 0 / 0.0 s | 17 / 10.9 s | 70 | 21.4 |
| tests/test_public_player_hint.py | 38 / 17.0 s | 132 / 126.0 s | 0 / 0.0 s | 0 / 0.0 s | 5 / 6.2 s | 175 | 149.2 |
| tests/test_public_player_maybe.py | 8 / 2.1 s | 13 / 0.6 s | 0 / 0.0 s | 0 / 0.0 s | 0 / 0.0 s | 21 | 2.7 |
| tests/test_public_player_probe.py | 24 / 22.4 s | 73 / 401.1 s | 0 / 0.0 s | 0 / 0.0 s | 4 / 2.2 s | 101 | 425.8 |
| tests/test_public_player_zoom.py | 10 / 5.0 s | 29 / 110.3 s | 0 / 0.0 s | 0 / 0.0 s | 0 / 0.0 s | 39 | 115.4 |
| tests/test_player_public_mode.py | 0 / 0.0 s | 1 / 0.0 s | 69 / 259.9 s | 8 / 19.7 s | 0 / 0.0 s | 78 | 279.6 |
| tests/test_player_shared_ui_site.py | 0 / 0.0 s | 3 / 0.2 s | 45 / 23.2 s | 5 / 0.7 s | 0 / 0.0 s | 53 | 24.1 |
| tests/test_player_bundle.py | 0 / 0.0 s | 0 / 0.0 s | 119 / 6.0 s | 0 / 0.0 s | 0 / 0.0 s | 119 | 6.0 |

## 1. What the audit found that the card did not say (read these first)

1. **The 27 mutant arms of `test_player_public_mode.py` do NOT retarget play.js text** (the card's keep list says they do). Measured on the `MUTANTS` table: 27 arms, 18 edit `solver.js`, 9 edit `solver_state.js`, 0 edit `play.js`. What does read play.js there is (a) the helper `play_exhausted_sentence()` (lines 101-104, reads `HINT_EXHAUSTED` out of `player/play.js`; called from `step_hint` at lines ~490/494, and at ~698 and ~745), which the whole sweep family runs through (the sweep, the census plant, the sweep of the real files, 11 `sweep` mutant arms, 5 `stall` arms, and `test_player_shared_ui_site.py`'s two sweep cells: about 26 cells, my count from the `CHECKS` table), and (b) the `_PLAY` comparator (`extra_files=[("play.js", ...)]`, lines 1321-1324, 1577) of the `hint` and `solved` checks, used by 3 arms and 3 tests. So: **all 27 arms stay**; 24 are untouched, 3 are CONVERT (drop the comparator arm); the one helper is the single edit that unblocks the family. Deleting play.js without re-pointing the helper reds roughly 26 live cells.
2. **`player/player.css` cannot retire: it is the listing pages' stylesheet.** `library.html` and `book.html` link `/player.css` (library.html:43, book.html:58), `pages.js` and 39 of player.css's 113 rules (`.tile*`, `.pages-*`, `.page-head`, `.player-head`/`-hint`/`-fallback`/`-announce`/`-tier`, `.btn`) are theirs; `assemble.py` says so itself (`SHARED_UI_PLAYER_FILES` comment: "`player.css` still is [published], because the two listing pages ... are styled by it"). The listing section starts at player.css line 310. The deletion step therefore SPLITS player.css (the play-page half goes, a listing stylesheet stays, probably renamed), or moves the listing pages onto CARD-394's stylesheet. Card text says "`player/pages.js`, `book.html`, `library.html`, `vercel.json` stay unless the audit shows otherwise": the audit shows they need an edit (the stylesheet link), and `test_public_player_pages.py::test_the_listing_pages_carry_no_colour_literal_and_only_defined_tokens` and `...::test_the_two_pages_add_nothing_to_the_package_and_no_toolchain` already name player.css and must follow.
3. **`tests/test_player_bundle.py` (119 ids, 6.0 s) has nothing to do with the retirement**: its header says "nothing here reads `player/`"; 0 hits for play.js / player.css / play.html. Classified KEEP-LIVE, out of the blast radius; the card's Touches row for it is over-inclusive. Likewise `test_public_player_pages.py` (33 ids) is the listing-door suite: 31 KEEP-LIVE, 2 CONVERT.
4. **`test_public_player.py` is mostly NOT play.js either**: of 34 ids, 15 are assembler/bundle/key-recipe/R2/R1 claims (KEEP-LIVE), 12 are RETIRE-TWIN, 5 CONVERT, 2 MOOT. It must also SURVIVE as a helper module: `test_player_shared_ui_site.py` imports `REPO_ROOT, _bundle_payload, _leaky_title, assembler` from it and `BOOK_ORDER, PAGE_GRIDS, PAGES_SETTLE_MS, _open_pages, _serve, _tiles, driver, scan_site, write_pages_bundle` from `test_public_player_pages.py`; the four feature files import fixtures from `test_public_player` and from each other (probe -> circles, crosshair, hint, zoom; hint -> circles, crosshair, zoom; circles -> crosshair, zoom; maybe -> agreement). **The cross-imports mean the feature files can only be deleted together, after the LOST rows are decided** (LOST rows live in circles, crosshair, hint, probe; zoom, maybe and agreement have none).
5. **A behaviour difference, not just a test difference: the pinch/pen crosshair rules exist in play.js and not in the admin's `solver.js`.** `wireCrosshair` (solver.js ~1639-1690) follows every `pointerdown`/`pointermove` of every pointer and only exempts touch from the leave rule; `grep -i pinch` in that block is 0 and `tests/test_puzzle_solver_crosshair.py` has no pinch/pen cell. play.js suppresses the crosshair during a two-pointer pinch and has 7 tests holding it (see the LOST list). Moving to the shared UI changes what a phone user sees. This is the owner's call (port to solver.js in a findings card, or accept).
6. **Several play.js layout pins conflict with the owner's new decisions and are MOOT, not survivors** (cards 401-405, 409, 411): the stage-above-the-fold cap, the landscape one-row toolbar, the sentence-below-the-board premise, the probe-bar 1-px width sweeps (192.2 s), the gutter-unpinning rule sweep (57.5 s), the hint control under the board. The admin page has a different layout, which those cards re-decide with their own tests. **Until CARD-403 merges, "the board's scroll box ends above the fold" is held by no test on the shared page** (the play.js pin dies with the file, the admin pin does not exist yet): do not delete before 403 if the owner wants that held meanwhile.
7. **Twins whose survivor file is itself about to be rewritten by the findings cards** (so the claim is safe, the cell name may move): zoom (cards 401-408), phone (401,402,403,405,406), clues (400,403,404,405,406), hint (401,408,409), probe (410,411,412), brush_menu (401,413), page (401,407,409,411,413), maybe (402), resume (407,411,412), `test_player_shared_ui_site.py` (394, 409, 413). Table in section 6.
8. **The five check refs that retire move**: `requirements.yml` AC-383..AC-386 (lines 5559-5577), EC-050 (5675), `trace.yml` 2398-2403, ADR-0041/R4's `check.ref`, `docs/deploy/player.md:415`, `11-the-public-player.md:200`. None of the seven feature files is cited by requirements.yml, trace.yml or an ADR check ref (measured: `grep` of the model for `test_public_player_{probe,hint,zoom,circles,crosshair,maybe,agreement}` = 0), so retiring them moves no model row.

## 2. LOST list (live claim, no twin: the OWNER decides; none of these is deleted)

27 ids, 19.7 s. `decide` = a behaviour that the shared UI would LOSE or leave unprotected and that the owner may want kept (port to the admin page = a few cells in the admin test files, which cost the same seconds they cost today); `accept-recommended` = the claim holds by construction in solver.js (one handler for every pointer type etc.), only the test is missing; the cheapest honest resolution is to accept the loss.

| # | ids | s | node id (file::class::test) | claim | evidence that no twin exists | resolution |
|---|---|---|---|---|---|---|
| L1 | 1 | 0.4 | `test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_crossed_and_circled_clue_box_shows_its_tint_and_its_ring` | a crossed and circled clue box shows its tint and its ring | crossed+circled clue box shows both; no admin cell (CARD-400 touches the circle rule) | decide |
| L2 | 1 | 0.2 | `test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision::test_a_mouse_drag_is_crossed_at_every_cell_it_visits_and_still_marks` | a mouse drag is crossed at every cell it visits and still marks | no admin cell; one handler for every pointer type (solver.js wireCrosshair follow on pointerdown+pointermove) | accept-recommended |
| L3 | 1 | 0.3 | `test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision::test_a_pen_drag_follows_the_pen_across_the_board` | a pen drag follows the pen across the board (Pen with Region off reaches the whole drag branch (see _pen_drag).) | no pen cell in test_puzzle_solver_crosshair.py; same handler | accept-recommended |
| L4 | 1 | 0.6 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_crosshair_painted_before_a_zoom_survives_it_whole` | a crosshair painted before a zoom survives it whole (Zoom is a view: pressing it re-paints nothing and rewrites nothing.) | zoom is a view; admin zoom never touches is-crossed (no cell) | accept-recommended |
| L5 | 1 | 0.5 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_finger_counts_toward_a_pinch_that_a_pen_began` | a finger counts toward a pinch that a pen began (The mirror of the pen test: a pen is down, then a finger lands. The) | solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared UI regresses this unless ported (findings card) or accepted | decide |
| L6 | 1 | 0.2 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_lost_pen_pointerup_does_not_stick_a_pinch` | a lost pen pointerup does not stick a pinch (A pen pointerup that never reaches the stage leaves a stale entry; the) | solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared UI regresses this unless ported (findings card) or accepted | decide |
| L7 | 1 | 0.5 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_pen_counts_toward_a_pinch` | a pen counts toward a pinch (play.js counts touch AND pen as the pinch's pointers, so the crosshair) | solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared UI regresses this unless ported (findings card) or accepted | decide |
| L8 | 1 | 1.1 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_pinch_neither_starts_a_crosshair_nor_leaves_one` | a pinch neither starts a crosshair nor leaves one | solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared UI regresses this unless ported (findings card) or accepted | decide |
| L9 | 1 | 1.5 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_pinch_takes_off_a_crosshair_an_earlier_tap_left` | a pinch takes off a crosshair an earlier tap left | solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared UI regresses this unless ported (findings card) or accepted | decide |
| L10 | 1 | 0.9 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_third_finger_neither_paints_nor_follows` | a third finger neither paints nor follows (Two fingers are a pinch; three are still no crosshair, whether the) | solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared UI regresses this unless ported (findings card) or accepted | decide |
| L11 | 1 | 1.5 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_crossing_resumes_after_a_pinch` | crossing resumes after a pinch (The suppression is for the pinch and nothing longer.) | solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared UI regresses this unless ported (findings card) or accepted | decide |
| L12 | 1 | 0.4 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_after_the_zoom_moved_the_scroll_itself` | it lands on the cell after the zoom moved the scroll itself (Zoom anchors the scroll (anchoredScroll), so after a zoom the stage) | same | decide |
| L13 | 4 | 1.8 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_at_the_zoom_maximum_at_any_stage_scroll` | it lands on the cell at the zoom maximum at any stage scroll (At 390 px and 300% the row gutter is wider than the stage and lets) | crosshair position under zoom+scroll; admin sticky gutters differ and CARD-404/405 change them; no admin cell crosses a zoomed board | decide |
| L14 | 1 | 0.4 | `test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_when_the_page_itself_has_scrolled` | it lands on the cell when the page itself has scrolled (A phone on its side: the toolbar wraps and the page can scroll as) | same | decide |
| L15 | 1 | 1.0 | `test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_full_or_none_holds_at_every_step_of_a_mixed_session` | full or none holds at every step of a mixed session | the half-painted-crosshair invariant over a mixed mouse+touch session has no admin walk; admin has the point cases (NoStaleMarkerAfterRedraw, TouchKeepsTheLastCell) | accept-recommended |
| L16 | 1 | 2.6 | `test_public_player_hint.py::TestPublicHint_StayLegibleAndInPlaceWhenZoomedAndScrolled::test_the_lit_line_and_the_outlined_cell_survive_zoom_and_scroll` | the lit line and the outlined cell survive zoom and scroll | hint highlight stays legible and in place at zoom+scroll; CARD-408 ('Hint brings what it points at into view') owns the replacement | decide |
| L17 | 1 | 1.0 | `test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_hinted_crossed_and_circled_box_shows_all_three` | a hinted crossed and circled box shows all three | hint tint vs crossed/circled/maybe distinguishability; admin has the probe (TheMarkerIsMeasurablyApartFromItsGround) and crosshair-vs-four-states analogues only; CARD-409 re-decides the hint highlight | decide |
| L18 | 1 | 0.8 | `test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_hinted_line_keeps_a_filled_a_white_and_a_blank_cell_apart` | a hinted line keeps a filled a white and a blank cell apart (The tint is a background, so the marks on a lit line are still told apart: the) | hint tint vs crossed/circled/maybe distinguishability; admin has the probe (TheMarkerIsMeasurablyApartFromItsGround) and crosshair-vs-four-states analogues only; CARD-409 re-decides the hint highlight | decide |
| L19 | 1 | 0.9 | `test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_maybe_cell_on_a_lit_line_keeps_its_glyph_and_the_tint_is_not_the_maybe_ground` | a maybe cell on a lit line keeps its glyph and the tint is not the maybe ground (G-9: the hint highlight stays distinct from CARD-323's Mayb | hint tint vs crossed/circled/maybe distinguishability; admin has the probe (TheMarkerIsMeasurablyApartFromItsGround) and crosshair-vs-four-states analogues only; CARD-409 re-decides the hint highlight | decide |
| L20 | 1 | 0.8 | `test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_the_four_states_of_a_clue_box_are_pairwise_distinguishable` | the four states of a clue box are pairwise distinguishable | hint tint vs crossed/circled/maybe distinguishability; admin has the probe (TheMarkerIsMeasurablyApartFromItsGround) and crosshair-vs-four-states analogues only; CARD-409 re-decides the hint highlight | decide |
| L21 | 1 | 1.2 | `test_public_player_probe.py::TestPublicProbe_APinchNeitherOpensNorChangesAProbe::test_a_two_finger_pinch_leaves_the_probe_alone` | a two finger pinch leaves the probe alone | pinch while a probe is open; admin zoom tests never open a probe | accept-recommended |
| L22 | 1 | 0.3 | `test_public_player_probe.py::TestPublicProbe_ARegionDragIsOneProbeStroke::test_the_save_is_the_checkpoint_save_abandon_restores_and_no_marker_is_left` | the save is the checkpoint save abandon restores and no marker is left | a Region drag inside a probe is ONE probe stroke; admin Region and probe tests never combine | accept-recommended |
| L23 | 1 | 0.3 | `test_public_player_probe.py::TestPublicProbe_OnlyOneProbeAtATime::test_the_controls_are_ignored_while_a_stroke_is_being_drawn` | the controls are ignored while a stroke is being drawn | probe controls mid-stroke; no admin cell | accept-recommended |
| L24 | 1 | 0.5 | `test_public_player_probe.py::TestPublicProbe_TheMarksCoexistByPixels::test_a_circled_clue_number_keeps_its_ring_while_the_board_is_probed` | a circled clue number keeps its ring while the board is probed | ring on the clue number while probing; disjoint elements by construction | accept-recommended |

Dependency of the `decide-with-CARD-408/409` rows: those two cards re-decide the hint highlight (409) and bring-into-view (408); if the owner prefers, those rows can simply be handed to the cards as 'the replacement test is owed here' and counted as moot once the card merges.

## 3. Survivors by claim family (retired claim -> named survivor)

Every survivor below was verified by `ast` to exist exactly once in its class and to be in the 11699-id collected list (97 distinct survivors, 0 bad; `gen.py` output in my scratchpad). A survivor that is itself a CONVERT row is marked `[C]` (it survives, but its play.js arm must be dropped first and its plant re-run). Weak twins (the survivor proves a neighbour or part of the claim) are marked **WEAK** in the per-test table.

| survivor (file::class::test) | retiring ids it backs (TWIN rows only count in 'twin') | twin | of which in WEAK rows | survivor file touched by findings cards |
|---|---|---|---|---|
| `test_puzzle_solver_hint.py::TestSolverHintLadder_ThePureModule::test_the_ladder` | 14 | 14 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_hint.py::TestSolverHintLadder_FirstPressPointsAtALine::test_the_first_press_highlights_the_line_and_says_so` | 11 | 11 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_hint.py::TestSolverHintLadder_SecondPressExplains::test_each_reason_is_announced_on_a_board_where_it_holds` | 11 | 11 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_BoardIsLineByLine` | 10 | 10 | 1 | CARD-400, CARD-403, CARD-404, CARD-405, CARD-406 |
| `test_puzzle_solver_clues.py::TestSolverClues_RuleExamples::test_each_row_circles_what_the_table_says` | 9 | 9 | 0 | CARD-400, CARD-403, CARD-404, CARD-405, CARD-406 |
| `test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_AFullyMarkedLineCirclesEverything` | 9 | 9 | 0 | CARD-400, CARD-403, CARD-404, CARD-405, CARD-406 |
| `test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot` | 9 | 9 | 0 | CARD-400, CARD-403, CARD-404, CARD-405, CARD-406 |
| `test_puzzle_solver_hint.py::test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell` | 8 | 8 | 2 | CARD-401, CARD-408, CARD-409 |
| `test_player_public_mode.py::TestPublicMode_SolvedComesFromTheClues::test_it_agrees_with_the_oracle_and_with_play_js` [C] | 6 | 6 | 5 | - |
| `test_puzzle_solver_hint.py::TestSolverHintLadder_ThirdPressRevealsTheSameSituation::test_the_third_press_reveals_the_cell_of_that_line` | 6 | 6 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_hint.py::TestSolverHint_RevealsOneCell::test_one_click_reveals_the_oracles_cell` | 6 | 6 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_clues.py::TestSolverClues_CirclesFollowEveryCommit::test_drag_click_undo_redo_reset` | 5 | 5 | 2 | CARD-400, CARD-403, CARD-404, CARD-405, CARD-406 |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_RowColumnAndCluesLight::test_the_hovered_rows_column_and_clues_carry_the_marker` | 5 | 5 | 5 | - |
| `test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised` | 4 | 4 | 3 | - |
| `test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean` | 4 | 4 | 0 | CARD-394, CARD-409, CARD-413 |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_ClearsWhenThePointerLeaves::test_leaving_the_stage_clears_it_and_a_clue_box_does_not` | 4 | 4 | 2 | - |
| `test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_a_hint_revealed_inside_a_probe_belongs_to_it` | 4 | 4 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_TheMarkerIsMeasurablyApartFromItsGround::test_the_ring_is_apart_from_the_ground_it_is_drawn_on` | 4 | 4 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_resume.py::test_PropertyTest_SolverResume_RejectsAnyUntrustedSave` | 4 | 4 | 4 | CARD-407, CARD-411, CARD-412 |
| `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_every_puzzle_file_carries_exactly_the_served_key_set` | 3 | 3 | 0 | CARD-394, CARD-409, CARD-413 |
| `test_puzzle_solver_clues.py::TestSolverClues_DragPreviewDoesNotCircle::test_no_circle_until_release` | 3 | 3 | 0 | CARD-400, CARD-403, CARD-404, CARD-405, CARD-406 |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_IsPureView::test_a_long_hover_sequence_changes_no_state_no_history_and_no_save` | 31 | 3 | 0 | - |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_IsPureView::test_hovering_issues_no_request` | 3 | 3 | 0 | - |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_TouchKeepsTheLastCell::test_a_touch_drag_crosses_the_finger_and_the_crosshair_stays` | 3 | 3 | 0 | - |
| `test_puzzle_solver_hint.py::TestSolverHintLadder_AnyChangeResetsTheLadder::test_the_next_press_is_rung_one_again` | 3 | 3 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_hint.py::TestSolverHint_DisabledWithNothingToReveal::test_disabled_during_a_drag` | 3 | 3 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_maybe.py::TestSolverMaybeModule_ClickedStateTable::test_table` | 3 | 3 | 0 | CARD-402 |
| `test_puzzle_solver_maybe.py::TestSolverMaybe_ClickWithTheMaybeTool::test_two_clicks_mark_then_clear` | 3 | 3 | 0 | CARD-402 |
| `test_puzzle_solver_maybe.py::TestSolverMaybe_DragPaintsMaybe::test_drag` | 3 | 3 | 0 | CARD-402 |
| `test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_the_probes_marks_carry_the_marker_and_earlier_marks_do_not` | 3 | 3 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_resume.py::TestSolverResume_ReloadRestoresBoardCountsAndHistory::test_reload_restores` | 3 | 3 | 0 | CARD-407, CARD-411, CARD-412 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_PinchCancelsTheStrokeInProgress::test_a_second_finger_reverts_the_drag_and_commits_nothing` | 3 | 3 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_PinchOnTheBoardZooms::test_spreading_100_to_200px_on_a_cell_reads_200_percent_and_marks_nothing` | 3 | 3 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestZoomArithmetic_PureFunctions::test_clamp_and_step_cover_the_range_its_edges_and_a_non_multiple` | 3 | 3 | 3 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_it_agrees_with_the_brute_force_oracle_and_with_play_js` [C] | 2 | 2 | 0 | - |
| `test_player_public_mode.py::TestPublicMode_TheStallBoard::test_the_oracle_s_stalled_boards_drive_it` [C] | 2 | 2 | 0 | - |
| `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte` | 195 | 2 | 0 | CARD-394, CARD-409, CARD-413 |
| `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_an_address_that_is_no_puzzle_says_so_and_draws_no_board` | 2 | 2 | 0 | CARD-394, CARD-409, CARD-413 |
| `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_hint_stays_on_and_says_why_where_no_line_decides` | 3 | 2 | 0 | CARD-394, CARD-409, CARD-413 |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_FollowsThePointer::test_a_move_clears_the_old_lines_and_marks_the_new` | 2 | 2 | 1 | - |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_NoStaleMarkerAfterRedraw::test_a_redraw_clears_the_marker_and_the_same_cell_crosses_again` | 2 | 2 | 1 | - |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_RowColumnAndCluesLight::test_the_four_cell_states_stay_apart_under_the_tint` | 2 | 2 | 0 | - |
| `test_puzzle_solver_hint.py::test_PropertyTest_SolverHint_LineForcedMatchesBruteForce` | 2 | 2 | 2 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_probe.py::TestSolverProbe_AbandonRestoresTheCheckpointBoard::test_abandon_restores_the_board_and_closes_the_probe` | 2 | 2 | 2 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_CommitKeepsCellsAndDropsTheTint::test_keep_keeps_every_cell_and_drops_every_marker` | 2 | 2 | 2 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_resume.py::TestSolverResume_AReloadAbandonsTheOpenProbe::test_the_save_is_the_save_as_of_the_checkpoint` | 2 | 2 | 1 | CARD-407, CARD-411, CARD-412 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_the_full_25_point_staircase_up_and_down` | 2 | 2 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_zoom_in_at_300_percent_is_a_no_op_and_stays_disabled` | 2 | 2 | 2 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_zoom_in_once_reads_125_percent_and_scales_every_cell` | 2 | 2 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_zoom_out_at_100_percent_is_a_no_op_and_stays_disabled` | 2 | 2 | 2 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_player_public_mode.py::TestPublicMode_EverySolutionReadIsListedAndGated::test_the_reads_are_exactly_the_listed_sites` | 1 | 1 | 1 | - |
| `test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[a-network-call-is-added]` | 1 | 1 | 0 | - |
| `test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[probe-auto-commit-decided-by-filled-count]` | 1 | 1 | 0 | - |
| `test_player_public_mode.py::TestPublicMode_TheCensus::test_the_real_template_is_fully_swept_and_a_plant_is_not` | 1 | 1 | 0 | - |
| `test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_a_wrong_mark_misleads_it_exactly_as_it_misleads_play_js` [C] | 1 | 1 | 0 | - |
| `test_player_public_mode.py::TestPublicMode_ThePayload::test_a_public_payload_is_still_checked_for_its_shape` | 1 | 1 | 0 | - |
| `test_player_public_mode.py::TestPublicMode_TheSave::test_the_save_carries_a_constant_stamp_and_resumes` | 1 | 1 | 0 | - |
| `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_table_covers_exactly_the_four_files` | 1 | 1 | 0 | CARD-394, CARD-409, CARD-413 |
| `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_a_real_puzzle_plays_to_the_solved_banner` | 1 | 1 | 0 | CARD-394, CARD-409, CARD-413 |
| `test_puzzle_solver_brush_menu.py::TestRegionRules_PureFunctions::test_gesture_paints_is_mouse_always_and_the_rest_only_when_armed` | 1 | 1 | 0 | CARD-401, CARD-413 |
| `test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_HoldsFourBrushesOnly::test_menu_lists_the_four_brushes_in_order` | 1 | 1 | 0 | CARD-401, CARD-413 |
| `test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_Pen::test_pen_drag_with_region_marks_like_touch` | 1 | 1 | 0 | CARD-401, CARD-413 |
| `test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_Pen::test_pen_drag_without_region_marks_nothing_not_even_the_start_cell` | 1 | 1 | 0 | CARD-401, CARD-413 |
| `test_puzzle_solver_brush_menu.py::TestSolverRegion_UnarmedTouchDragStillScrolls::test_touch_drag_without_region_scrolls_and_marks_nothing` | 1 | 1 | 0 | CARD-401, CARD-413 |
| `test_puzzle_solver_crosshair.py::TestSolverCrosshair_TouchKeepsTheLastCell::test_a_single_tap_leaves_the_crosshair_on_the_tapped_cell` | 1 | 1 | 0 | - |
| `test_puzzle_solver_hint.py::TestSolverHint_IsOneUndoableStroke::test_undo_and_redo_buttons` | 1 | 1 | 0 | CARD-401, CARD-408, CARD-409 |
| `test_puzzle_solver_marking.py::TestSolverClickFollowsTheBrush::test_every_brush_state_and_repeat_gives_the_table` | 1 | 1 | 0 | - |
| `test_puzzle_solver_marking.py::TestSolverMarking_ClickCycles::test_three_clicks_go_filled_empty_undecided_and_are_drawn_so` | 1 | 1 | 0 | - |
| `test_puzzle_solver_marking.py::TestSolverMarking_ClickIgnoresTheSelectedTool::test_exactly_one_tool_is_pressed` | 1 | 1 | 1 | - |
| `test_puzzle_solver_marking.py::TestSolverMarking_KeyboardAndLabels::test_ctrl_z_undoes_and_shift_ctrl_z_redoes` | 1 | 1 | 1 | - |
| `test_puzzle_solver_page.py::TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways` | 1 | 1 | 1 | CARD-401, CARD-407, CARD-409, CARD-411, CARD-413 |
| `test_puzzle_solver_page.py::TestSolverPage_AllCellsStartUndecided::test_the_board_is_painted_from_state` | 1 | 1 | 1 | CARD-401, CARD-407, CARD-409, CARD-411, CARD-413 |
| `test_puzzle_solver_phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_cell_matches_the_formula_and_clears_the_old_floor` | 1 | 1 | 1 | CARD-401, CARD-402, CARD-403, CARD-405, CARD-406 |
| `test_puzzle_solver_probe.py::TestSolverProbe_CommitKeepsCellsAndDropsTheTint::test_a_reset_clears_the_open_probe` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_CountersSeeProbeMarksAsMarks::test_the_same_marks_read_the_same_inside_a_probe` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_the_four_states_stay_apart_under_the_tint` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_the_hint_lines_tint_does_not_repaint_a_probe_cell` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_OnlyOneProbeAtATime::test_a_second_press_opens_nothing` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_SolvingCommitsTheProbe::test_the_solving_mark_commits_the_probe` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_StateIsPureAndStatesAreFour::test_the_cell_states_are_four_and_an_unknown_event_is_refused` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_probe.py::TestSolverProbe_UndoClampsTheCheckpoint::test_undo_pops_probe_strokes_first_then_clamps` | 1 | 1 | 0 | CARD-410, CARD-411, CARD-412 |
| `test_puzzle_solver_progress.py::TestSolverProgress_SolvedWhenBlacksMatch::test_ac316_the_completing_click_shows_the_picture_name` | 1 | 1 | 1 | - |
| `test_puzzle_solver_resume.py::TestSolverResume_AReloadAbandonsTheOpenProbe::test_an_open_probe_saves_no_redo_stack` | 1 | 1 | 0 | CARD-407, CARD-411, CARD-412 |
| `test_puzzle_solver_resume.py::TestSolverResume_SavesEveryChangeWithoutARequest::test_saves_every_change` | 1 | 1 | 0 | CARD-407, CARD-411, CARD-412 |
| `test_puzzle_solver_resume.py::TestSolverResume_UntrustedSaveStartsFresh::test_untrusted_starts_fresh` | 1 | 1 | 0 | CARD-407, CARD-411, CARD-412 |
| `test_puzzle_solver_resume.py::test_PropertyTest_SolverResume_SaveAndRestoreRoundTrip` | 1 | 1 | 0 | CARD-407, CARD-411, CARD-412 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_ChangingZoomChangesNoSolveState::test_a_100_to_300_to_100_round_trip_changes_nothing_recorded` | 1 | 1 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_IsNotSavedAndSendsNothing::test_zoom_sends_no_request_leaves_the_save_untouched_and_resets_on_reload` | 1 | 1 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestSolverZoom_ZoomKeepsTheViewCentre::test_zoom_out_keeps_the_same_cell_near_the_stages_centre` | 1 | 1 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestZoomArithmetic_PureFunctions::test_anchored_scroll_matches_the_cards_own_formula_by_hand` | 1 | 1 | 0 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |
| `test_puzzle_solver_zoom.py::TestZoomArithmetic_PureFunctions::test_pinch_zoom_scales_clamps_and_refuses_a_non_positive_distance` | 1 | 1 | 1 | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |

## 4. Per-test table (every node id belongs to exactly one row; Appendix A lists the ids)

Class codes: TWIN = RETIRE-TWIN, MOOT = RETIRE-MOOT, KEEP = KEEP-LIVE, CONV = CONVERT, LOST. `ids` is the number of node ids (parametrised cells) in the row; `s` their summed gate seconds.


### tests/test_player_bundle.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPlayUrl_TheShapeTheDeployPageRecords | 5: a trailing slash on the base does not double; it builds the owner s own example; ... (+3) | 12 | 0.0 | KEEP | bundle export (src/nonogram/admin/player_bundle.py): its docstring says 'nothing here reads player/'; grep play.js/player.css/play.html = 0 hits; the card's scope row is over-inclusive |
| TestPuzzleKeyOfRecord_OneRecipeForARow | 4: a record keys to the adr s own recipe; a record with no grid is refused rather than keyed; ... (+2) | 8 | 0.0 | KEEP | bundle export (src/nonogram/admin/player_bundle.py): its docstring says 'nothing here reads player/'; grep play.js/player.css/play.html = 0 hits; the card's scope row is over-inclusive |
| - | 37: a book stored mixed is bundled in print order (The oracle's own contro; a legitimate value stays green (The whitelist's edge: what it must NOT; ... (+35) | 99 | 6.0 | KEEP | bundle export (src/nonogram/admin/player_bundle.py): its docstring says 'nothing here reads player/'; grep play.js/player.css/play.html = 0 hits; the card's scope row is over-inclusive |

### tests/test_player_public_mode.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPublicMode_EverySolutionReadIsListedAndGated | 3: a tenth read is found; the gated calls are exactly the ones the gates name (A read that is ga; ... (+1) | 3 | 0.0 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_EveryWayOfLosingItIsCaught | 3: a network plant reds the scan beside a clean control; the check is green on the real files and red on the mutant; ... (+1) | 27 | 209.7 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_EveryWayOfLosingItIsCaught | 1: the check is green on the real files and red on the mutant | 1 | 0.6 | CONV | same: check _solved_check serves play.js as extra_files |
| TestPublicMode_EveryWayOfLosingItIsCaught | 1: the check is green on the real files and red on the mutant | 2 | 8.8 | CONV | mutant edits solver_state.js (NOT play.js); its check _hint_check serves play.js as extra_files: stays once that arm is dropped - the plant must be re-run red |
| TestPublicMode_NoNetworkInAnyMode | 2: a plant of each kind reds the scan; the admin player files contain no network call | 8 | 0.0 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_NothingServedCarriesTheSolution | 3: a payload that ships the solution is what the scan exists to find; a plant that serves the solution reds the scan; ... (+1) | 6 | 0.5 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_SolvedComesFromTheClues | 1: it agrees with the oracle and with play js (AC-6 / G-6. Declared: it d | 1 | 0.3 | CONV | drop the play.js arm; oracle (solved_truth/clue_truth) arm stays |
| TestPublicMode_SolvedComesFromTheClues | 2: the corpus is big unique and two sided; the one difference from the admin is a maybe on a solved board | 2 | 0.3 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_TheAdminDefaultIsUnchanged | 1: errors progress check the fallback and the fingerprint are all there | 1 | 0.9 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_TheCensus | 4: an unclicked step is found by the sweep not only by the census (A regi; every control family is read by the census; ... (+2) | 8 | 10.2 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks | 1: a wrong mark misleads it exactly as it misleads play js (AC-6's declar | 1 | 2.1 | CONV | differential vs play.js: re-express against the module's own derivation on the wrong-mark board (R2 declared residual: a wrong mark misleads the hint); plant needed |
| TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks | 1: it agrees with the brute force oracle and with play js (AC-6 and G-6:  | 1 | 2.0 | CONV | drop the play.js comparison arm (extra_files=_PLAY); the brute-force oracle arm stays; saves ~2 s |
| TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks | 2: the corpus is big and has every kind of board; there is never a hint where no line decides | 2 | 2.7 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_ThePayload | 5: a public payload is still checked for its shape; a public payload with a solution is refused (AC-2 - and the matched co; ... (+3) | 5 | 4.4 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_TheSave | 1: the save carries a constant stamp and resumes | 1 | 0.4 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_TheStallBoard | 1: hint offers and reveals nothing where no line decides (Id kept (G-5);  | 1 | 0.2 | CONV | helper play_exhausted_sentence() reads HINT_EXHAUSTED out of play.js (line 102); re-point at solver.js PUBLIC_EXHAUSTED |
| TestPublicMode_TheStallBoard | 1: the oracle s stalled boards drive it (Boards the brute-force oracle sa | 1 | 5.7 | CONV | same helper |
| TestPublicMode_TheStallBoard | 1: the sentence is play js s own (G-6: the same words as the public playe | 1 | 0.0 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_hint_stays_on_and_says_why_where_no_line_decides`<br>claim is 'the same words as play.js'; no subject; the sentence itself stays pinned by the stall tests once their helper reads solver.js (see next two rows) |
| TestPublicMode_TheSweep | 3: every control is driven and nothing goes wrong (AC-1.); the census and the sweep agree on the real template; ... (+1) | 3 | 10.4 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| TestPublicMode_TheSweepOfTheRealFiles | 2: the sweep drives what it says it drives; the sweep is clean (AC-1 + AC-4: every control, every gesture, the sol | 2 | 20.4 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |
| - | 1: the sweep puzzles are what the sweep needs | 1 | 0.0 | KEEP | CARD-385: solver.js public mode, sealed getter (R2), no network (R4), sweep; asserts on admin files |

### tests/test_player_shared_ui_site.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestSharedUi_ByteIdentity | 4: a plant that edits a copy reds; the assembly time check refuses a copy that is not identical; ... (+2) | 8 | 0.5 | KEEP | CARD-386: the shared-UI page, R2 served-tree scan, R3 byte-identity, shell refusals |
| TestSharedUi_TheCard385SweepOnThisTree | 2: every control every gesture the solve and the reload are clean (AC-1 /; the sweep is not vacuous a gutted control reds it (The control: remove | 2 | 15.4 | KEEP | CARD-386: the shared-UI page, R2 served-tree scan, R3 byte-identity, shell refusals |
| TestSharedUi_TheDefaultIsUnchanged | 1: the cli flags are all or nothing | 1 | 0.0 | MOOT | --shared-ui-fragment/--bootstrap retire or change with CARD-394; claim dissolves |
| TestSharedUi_TheDefaultIsUnchanged | 1: the driver end to end equals the in process assembly | 1 | 0.3 | CONV | re-point at the default invocation |
| TestSharedUi_TheDefaultIsUnchanged | 1: the driver refuses one of the two flags and print only renders nothing | 1 | 0.2 | CONV | the 'one of two flags' half retires; keep the print-only-renders-nothing half |
| TestSharedUi_TheDefaultIsUnchanged | 1: the driver still writes no file and names no published path (The exist | 1 | 0.0 | KEEP | guard on the driver (writes nothing itself) |
| TestSharedUi_TheDefaultIsUnchanged | 1: the drivers default command line is unchanged | 1 | 0.0 | CONV | re-pin the new default command line |
| TestSharedUi_TheDefaultIsUnchanged | 1: the preview differs from the default in the named paths only | 1 | 0.1 | MOOT | compares preview to default; PREVIEW_DROPPED={'play.js'}; no second mode left |
| TestSharedUi_TheDefaultIsUnchanged | 1: two default runs are byte identical | 1 | 0.1 | CONV | determinism of the (new) default tree; keep as the one 'two runs identical' cell (pages.py has test_two_assemble_runs_are_byte_identical: consider T then) |
| TestSharedUi_TheDefaultIsUnchanged | 1: without the flag the tree is the default tree | 1 | 0.1 | MOOT | opt-in contract: asserts play.html/play.js ARE the default; no meaning once shared-UI is the default |
| TestSharedUi_TheDoorsKeepTheirShapes | 3: the library lists every puzzle and a tile opens the admin player; the preview server serves the three url shapes; ... (+1) | 3 | 0.6 | KEEP | CARD-386: the shared-UI page, R2 served-tree scan, R3 byte-identity, shell refusals |
| TestSharedUi_TheDoorsKeepTheirShapes | 1: the two listing pages and their assets are the default trees bytes | 1 | 0.1 | CONV | compares the preview tree to the default tree for pages.js/player.css/vercel.json; re-point at the player/ source bytes |
| TestSharedUi_ThePageRuns | 10: a bad address shows no placeholder header chip or false fallback (F-2:; a real puzzle plays to the solved banner (AC-1.); ... (+8) | 12 | 5.2 | KEEP | CARD-386: the shared-UI page, R2 served-tree scan, R3 byte-identity, shell refusals |
| TestSharedUi_TheServedTreeCarriesNoAnswer | 8: a bundle whose puzzle carries a solution key is served without it; a plant that adds a solution key to a served file reds the key check; ... (+6) | 9 | 1.3 | KEEP | CARD-386: the shared-UI page, R2 served-tree scan, R3 byte-identity, shell refusals |
| TestSharedUi_TheShellRefusesAFragmentItCannotTrust | 4: a fragment missing a hook is refused; a missing bootstrap file is an error before the tree is touched; ... (+2) | 9 | 0.2 | KEEP | CARD-386: the shared-UI page, R2 served-tree scan, R3 byte-identity, shell refusals |
| - | 1: the two boards are what the sweep needs (The same properties as CARD-3 | 1 | 0.0 | KEEP | CARD-386: the shared-UI page, R2 served-tree scan, R3 byte-identity, shell refusals |

### tests/test_public_player.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| - | 14: a puzzle file the schema cannot accept is refused and named (Every val; a tier outside the vocabulary carries no cell to the site (EC-048, at ; ... (+12) | 14 | 0.7 | KEEP | assembler/bundle half: R1/R2/EC-048/ADR-0039; names no play file in its body |
| - | 1: a save or a puzzle file the page cannot trust is refused (The page che | 1 | 0.3 | TWIN | `test_player_public_mode.py::TestPublicMode_ThePayload::test_a_public_payload_is_still_checked_for_its_shape`<br>`test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_an_address_that_is_no_puzzle_says_so_and_draws_no_board`<br>`test_puzzle_solver_resume.py::TestSolverResume_UntrustedSaveStartsFresh::test_untrusted_starts_fresh`<br>page refuses an untrusted save / puzzle file |
| - | 1: a touch or pen drag marks only while region is armed (Item 5 of the ca | 1 | 0.4 | TWIN | `test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_Pen::test_pen_drag_without_region_marks_nothing_not_even_the_start_cell`<br>`test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_Pen::test_pen_drag_with_region_marks_like_touch`<br>`test_puzzle_solver_brush_menu.py::TestSolverRegion_UnarmedTouchDragStillScrolls::test_touch_drag_without_region_scrolls_and_marks_nothing` |
| - | 1: an unknown or malformed key draws no board (A link to nothing says so, | 1 | 0.3 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_an_address_that_is_no_puzzle_says_so_and_draws_no_board`<br>2 parametrised cells there |
| - | 1: every player control is in the ec 050 walk (EC-050's walk is held to t | 1 | 0.0 | TWIN | `test_player_public_mode.py::TestPublicMode_TheCensus::test_the_real_template_is_fully_swept_and_a_plant_is_not`<br>census of the page's controls against the walk; the shared template census replaces play.html's |
| - | 1: no write request for any interaction (EC-050 / ADR-0041/R4 — for every | 1 | 0.7 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean`<br>`test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[a-network-call-is-added]`<br>ADR-0041/R4 check ref: Watch records every non-GET; plant a-network-call-is-added. THE REF MOVES to the sweep (honest-ref rule) |
| - | 1: phone viewport is playable (AC-386 — 390 px wide, ``MAX_SIZE`` per sid | 1 | 0.2 | TWIN | `test_puzzle_solver_page.py::TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways`<br>`test_puzzle_solver_phone.py::TestSolverPhone_BoardFitsThePhoneWidth::test_the_cell_matches_the_formula_and_clears_the_old_floor`<br>WEAK: AC-386 390px/MAX_SIZE playable; admin phone tests measure fit, not 'playable at MAX_SIZE'; phone layout is re-decided by CARD-401/402/405/406/407 |
| - | 1: play page renders and marks (AC-383 — the board renders, and marking m | 1 | 0.4 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_a_real_puzzle_plays_to_the_solved_banner`<br>`test_puzzle_solver_marking.py::TestSolverMarking_ClickCycles::test_three_clicks_go_filled_empty_undecided_and_are_drawn_so`<br>AC-383 board renders and marking: the shared page renders (ThePageRuns) and the admin marks it (ClickCycles) |
| - | 1: resume is local and the page writes nowhere (AC-385 — marks come back  | 1 | 0.3 | TWIN | `test_puzzle_solver_resume.py::TestSolverResume_ReloadRestoresBoardCountsAndHistory::test_reload_restores`<br>`test_puzzle_solver_resume.py::TestSolverResume_SavesEveryChangeWithoutARequest::test_saves_every_change`<br>`test_player_public_mode.py::TestPublicMode_TheSave::test_the_save_carries_a_constant_stamp_and_resumes`<br>AC-385 resume from this browser only |
| - | 1: served tree is clean of answers (EC-048 / AC-381's served half (ADR-00 | 1 | 0.6 | KEEP | ADR-0041/R2 check ref (served half) - live, its own control; scans whatever the default tree becomes |
| - | 1: solved fires on clue satisfaction only (AC-384 — solved is every clue  | 1 | 0.5 | TWIN | `test_player_public_mode.py::TestPublicMode_SolvedComesFromTheClues::test_it_agrees_with_the_oracle_and_with_play_js`<br>AC-384: solved = clue satisfaction only; survivor is itself a CONVERT row (its play.js arm is dropped first); the sweep mutants banner-decided-by-filled-count / probe-auto-commit-decided-by-filled-count plant it on the shared file |
| - | 1: the brush region and touch bindings are the modules (What a brush writ | 1 | 0.3 | TWIN | `test_puzzle_solver_marking.py::TestSolverClickFollowsTheBrush::test_every_brush_state_and_repeat_gives_the_table`<br>`test_puzzle_solver_brush_menu.py::TestRegionRules_PureFunctions::test_gesture_paints_is_mouse_always_and_the_rest_only_when_armed`<br>brush table and region/touch rules are solver_state.js's |
| - | 1: the empty mark is a dot and solving is revealed (The owner's two calls | 1 | 0.4 | TWIN | `test_puzzle_solver_page.py::TestSolverPage_AllCellsStartUndecided::test_the_board_is_painted_from_state`<br>`test_puzzle_solver_progress.py::TestSolverProgress_SolvedWhenBlacksMatch::test_ac316_the_completing_click_shows_the_picture_name`<br>WEAK: dot is the admin white mark too; 'solving is revealed' differs by decision (public banner reads 'Solved: Puzzle <key>', owner item (b) open) |
| - | 1: the page carries no answer and no third party asset (EC-048 in the bro | 1 | 0.3 | CONV | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_ac392s_own_scan_of_the_tree_is_empty_and_finds_a_plant`<br>`test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised`<br>ADR-0041/R2 live-page half; two partial twins (disk scan + sealed getter) but nothing inspects the RUNNING shared page's URLs for a solution/third-party request: re-point this test's selectors at the shared page (zero new cells) |
| - | 1: the player assets carry no colour literal and only defined tokens (Col | 1 | 0.0 | MOOT | `test_public_player_pages.py::test_the_listing_pages_carry_no_colour_literal_and_only_defined_tokens`<br>scans play.js/player.css(play part)/play.html; the listing half of player.css stays and its test is the pages one (which already names player.css) |
| - | 1: the player tree is static and adds nothing to the package (ADR-0041/R3 | 1 | 0.2 | CONV | ADR-0041/R3; the file list is DERIVED from PLAYER_FILES, but `assert len(files) >= 8` reds when 3 files leave: change the floor |
| - | 1: the registrys check refs for this card all resolve (Every ``tests/test | 1 | 0.0 | CONV | docstring node-id table guard: the table loses the retired rows and the moved R4 ref |
| - | 1: the runtime dependency baseline is untouched (G-3 / ADR-0006/R1 — noth | 1 | 0.0 | CONV | ADR-0006/R1 + R3: reads play.js/play.html to assert imports == ['/solver_state.js'] and scripts == ['/play.js']; re-point at the shared shell (solver.js module import) - the baseline claim is live |
| - | 1: the stage fits the board on a wide screen (The bordered stage is the b | 1 | 0.2 | MOOT | pixel claim about play.html's bordered stage; the admin stage is not that box (CARD-403 re-decides the stage) |
| - | 1: the state module and tokens are byte identical copies (ADR-0041/R3 — r | 1 | 0.0 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>`test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_table_covers_exactly_the_four_files`<br>R3 byte-identity of solver_state.js + tokens.css is a subset of the four-file table; valid once the default tree IS the shared-UI tree |
| - | 1: the static half of the site does not vary with the puzzles (No asset b | 1 | 0.2 | CONV | plants a byte into play.js (planted['play.js']); re-point the plant at a surviving static file (solver.js); one-line |

### tests/test_public_player_agreement.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPlayerLooksAgree_ADivergenceMustBeDeclared | 13: a declared divergence that stops diverging is reported (The other dire; a fourth divergence in the compared surface is reported (The positive ; ... (+11) | 18 | 0.1 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_AReasonMustNameTheLayoutThatForcesIt | 2: a reason that is only a preference fails it; every declared reason names a forcing layout fact | 3 | 0.0 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_BothPlayersSetTheSameWave | 3: both players set the wave to the same expression (AC-6's second mutant; each player sets the wave exactly once (The shape constraint. A second; ... (+1) | 3 | 0.0 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheCirclesAreTheSameLook | 7: a declaration is a real divergence with a reason over a fact the extra; a declared divergence that stops diverging is reported (The stale-exem; ... (+5) | 32 | 0.9 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions | 9: a declared divergence that stops diverging is reported (The stale-exem; a one sided change to a decision is reported (Each edge mutant moves o; ... (+7) | 20 | 0.6 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame | 6: reformatting a dot rule moves no declaration (The claim the arm above ; the admin sheet declares the seven properties; ... (+4) | 6 | 0.0 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords | 8: a declaration is a real divergence with a reason over a fact the extra; a declared divergence that stops diverging is reported (The stale-exem; ... (+6) | 28 | 0.3 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark | 13: a glyph deleted from this page is a failure and not an absence (The th; a one sided change to the maybe mark is reported (AC-2: a divergence i; ... (+11) | 17 | 0.1 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed | 9: a change to a sibling mark moves the census (The control (ADR-0039/R1); a fifth cell state is enumerated rather than left outside the census (; ... (+7) | 10 | 0.1 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheProbeIsTheSameLook | 9: a declaration is a real divergence with a reason over a fact the extra; a declared divergence that stops diverging is reported (The stale-exem; ... (+7) | 36 | 0.4 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep | 8: neither keyframes body is empty in either sheet (Anti-vacuity: two emp; the banner keyframes agree; ... (+6) | 8 | 0.0 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |
| TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot | 11: a one sided change to the swatch dot is reported (AC-2: a divergence i; a swatch dot deleted from this page is a failure and not an absence (T; ... (+9) | 12 | 0.1 | MOOT | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>CARD-328/339/348/325/326/327/380 duplicate-look guard: its subject is TWO implementations looking alike; one implementation, the claim dissolves (the live residue 'the copies are the admin bytes' is the survivor) |

### tests/test_public_player_circles.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPublicCircles_ACrossedClueStillShowsItsCircle | 1: a crossed and circled clue box shows its tint and its ring | 1 | 0.4 | LOST | LOST/decide: crossed+circled clue box shows both; no admin cell (CARD-400 touches the circle rule) |
| TestPublicCircles_ACrossedClueStillShowsItsCircle | 1: a tint that can hide the ring is caught | 6 | 4.4 | MOOT | plants into player.css |
| TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed | 1: a ring not drawn where it says is caught | 4 | 5.0 | MOOT | plants |
| TestPublicCircles_CirclesAreNotTheSolvedCheck | 1: a solved check made from the circle set declares victory on the wrong  | 2 | 0.8 | MOOT | plant into play.js |
| TestPublicCircles_CirclesAreNotTheSolvedCheck | 1: every number circled and the board is not solved | 5 | 1.4 | TWIN | `test_player_public_mode.py::TestPublicMode_SolvedComesFromTheClues::test_it_agrees_with_the_oracle_and_with_play_js`<br>WEAK: public solved is decided from the clues (isClueSolved) and the corpus has flipped/extra_fill boards; the all-circled-but-wrong board is not constructed there |
| TestPublicCircles_CirclesAreNotTheSolvedCheck | 2: no existing fixture has the extra cell board (Why this card builds a f; the constructed board is what the card says (The extra-cell list is th | 5 | 1.3 | MOOT | fixture sanity |
| TestPublicCircles_NoAnswerAndNoRequest | 1: every interaction issues nothing beyond the load | 1 | 1.1 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean`<br>Watch records non-GET and every URL |
| TestPublicCircles_NoAnswerAndNoRequest | 1: the circle code adds no external reference | 1 | 0.0 | MOOT | source scan; the served-tree scan (R2/R3) is the live version |
| TestPublicCircles_NoAnswerAndNoRequest | 1: the page holds no solution field and the circles add no attribute | 1 | 0.3 | TWIN | `test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised` |
| TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled | 1: a ring past a declared bound is caught (The matched control (shipped C | 2 | 1.8 | MOOT | plants |
| TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled | 1: the rings are in place and clear of each other at the maximum (``fract | 3 | 2.4 | MOOT | `test_puzzle_solver_clues.py::TestSolverClues_TheCircleIsVisible::test_two_digit_rings_clear_their_digits_on_a_30x30`<br>ring geometry at 300 % on play.css gutters; CARD-404/405 re-decide the clue strips at every zoom |
| TestPublicCircles_TheInPlaceBandHasADeclaredResidue | 1: the in place residue is declared and a shift just past it is caught | 2 | 2.6 | MOOT | measurement residue of play.css gutters |
| TestPublicCircles_TheMarksCircleTheNumbers | 5: a blank board circles nothing; a fully marked solution circles every number; ... (+3) | 9 | 2.1 | TWIN | `test_puzzle_solver_clues.py::TestSolverClues_RuleExamples::test_each_row_circles_what_the_table_says`<br>`test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot`<br>`test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_AFullyMarkedLineCirclesEverything`<br>`test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_BoardIsLineByLine`<br>AC-1; the rule is circledClues in solver_state.js, tested at module level. CARD-400 changes the rule and its tests (dependency) |
| TestPublicCircles_TheMarksCircleTheNumbers | 1: the fixtures are uniquely solvable (CON-005 / INV-002, for the two fix | 1 | 0.0 | MOOT | fixture sanity for the retiring file |
| TestPublicCircles_ThePredicateIsTheModules | 7: a second rule or a read the painter may not make is refused (The match; a solved check that reaches for the circles is refused; ... (+5) | 31 | 0.8 | MOOT | source scan of play.js's circle painter |
| TestPublicCircles_ThePredicateIsTheModules | 1: the page set equals the modules across a seeded corpus (EC (ADR-0041/R | 1 | 3.5 | TWIN | `test_puzzle_solver_clues.py::test_PropertyTest_SolverClues_BoardIsLineByLine`<br>`test_puzzle_solver_clues.py::TestSolverClues_CirclesFollowEveryCommit::test_drag_click_undo_redo_reset`<br>WEAK: admin property tests are module-level; the page-equals-module corpus has no page-level twin |
| TestPublicCircles_TheyFollowUndoRedoAndReset | 3: a drag in progress leaves the circles on the record; every step of a stroke undo redo reset walk equals the module; ... (+1) | 3 | 1.1 | TWIN | `test_puzzle_solver_clues.py::TestSolverClues_CirclesFollowEveryCommit::test_drag_click_undo_redo_reset`<br>`test_puzzle_solver_clues.py::TestSolverClues_DragPreviewDoesNotCircle::test_no_circle_until_release`<br>AC-2 |
| TestPublicCircles_TheyFollowUndoRedoAndReset | 1: a planted defect is caught and the unplanted page is clean (The matche | 8 | 12.8 | MOOT | plants into play.js |

### tests/test_public_player_crosshair.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPublicCrosshair_ADragKeepsTheDecision | 1: a drag that ends off the stage with a mouse clears the cross (Only lea | 1 | 0.3 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_ClearsWhenThePointerLeaves::test_leaving_the_stage_clears_it_and_a_clue_box_does_not`<br>WEAK: leave while NOT dragging; pointer capture during a drag not exercised |
| TestPublicCrosshair_ADragKeepsTheDecision | 1: a mouse drag is crossed at every cell it visits and still marks | 1 | 0.2 | LOST | LOST/accept-recommended: no admin cell; one handler for every pointer type (solver.js wireCrosshair follow on pointerdown+pointermove) |
| TestPublicCrosshair_ADragKeepsTheDecision | 1: a pen drag follows the pen across the board (Pen with Region off reach | 1 | 0.3 | LOST | LOST/accept-recommended: no pen cell in test_puzzle_solver_crosshair.py; same handler |
| TestPublicCrosshair_ADragKeepsTheDecision | 1: a press alone crosses the cell before any move (The edge the card's `p | 1 | 0.5 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_TouchKeepsTheLastCell::test_a_single_tap_leaves_the_crosshair_on_the_tapped_cell`<br>touch tap only; the mouse press arm is the same handler |
| TestPublicCrosshair_ADragKeepsTheDecision | 1: a touch drag leaves the cross on the last cell it reached | 1 | 0.6 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_TouchKeepsTheLastCell::test_a_touch_drag_crosses_the_finger_and_the_crosshair_stays` |
| TestPublicCrosshair_HoverHighlightsTheCross | 1: a clue box and the corner keep the crosshair where it was (CARD-267's  | 1 | 0.2 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_ClearsWhenThePointerLeaves::test_leaving_the_stage_clears_it_and_a_clue_box_does_not`<br>WEAK: clue box covered, the gutter corner is not named there |
| TestPublicCrosshair_HoverHighlightsTheCross | 1: hovering a cell marks its row its column and both clues (The oblong bo | 5 | 1.1 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_RowColumnAndCluesLight::test_the_hovered_rows_column_and_clues_carry_the_marker`<br>5 cells (sizes) vs 1: WEAK on the oblong-board row/column swap |
| TestPublicCrosshair_HoverHighlightsTheCross | 1: leaving the stage clears every marker | 1 | 0.2 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_ClearsWhenThePointerLeaves::test_leaving_the_stage_clears_it_and_a_clue_box_does_not` |
| TestPublicCrosshair_HoverHighlightsTheCross | 1: the crosshair follows the pointer and only one cross exists | 1 | 0.2 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_FollowsThePointer::test_a_move_clears_the_old_lines_and_marks_the_new` |
| TestPublicCrosshair_HoverRecordsNoStroke | 3: hovering makes no request (ADR-0038/R2 for the crosshair: nothing leav; pointer movement across the whole board changes nothing but the marker; ... (+1) | 3 | 2.8 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_IsPureView::test_a_long_hover_sequence_changes_no_state_no_history_and_no_save`<br>`test_puzzle_solver_crosshair.py::TestSolverCrosshair_IsPureView::test_hovering_issues_no_request`<br>AC-3 |
| TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled | 1: a crosshair painted before a zoom survives it whole (Zoom is a view: p | 1 | 0.6 | LOST | LOST/accept-recommended: zoom is a view; admin zoom never touches is-crossed (no cell) |
| TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled | 7: a finger counts toward a pinch that a pen began (The mirror of the pen; a lost pen pointerup does not stick a pinch (A pen pointerup that neve; ... (+5) | 7 | 6.2 | LOST | LOST/decide - BEHAVIOUR DIFFERENCE: solver.js wireCrosshair follows pointerdown/pointermove of every pointer incl. the pinch's fingers (no pinch suppression: grep 'pinch' in the crosshair block = 0); play.js suppresses it. Shared  |
| TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled | 1: a pinch marks nothing and records no stroke (G-5 from the crosshair's  | 1 | 1.1 | TWIN | `test_puzzle_solver_zoom.py::TestSolverZoom_PinchOnTheBoardZooms::test_spreading_100_to_200px_on_a_cell_reads_200_percent_and_marks_nothing`<br>`test_puzzle_solver_zoom.py::TestSolverZoom_PinchCancelsTheStrokeInProgress::test_a_second_finger_reverts_the_drag_and_commits_nothing` |
| TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled | 2: it lands on the cell after the zoom moved the scroll itself (Zoom anch; it lands on the cell when the page itself has scrolled (A phone on its | 2 | 0.8 | LOST | LOST/decide: same |
| TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled | 1: it lands on the cell at the zoom maximum at any stage scroll (At 390 p | 4 | 1.8 | LOST | LOST/decide: crosshair position under zoom+scroll; admin sticky gutters differ and CARD-404/405 change them; no admin cell crosses a zoomed board |
| TestPublicCrosshair_ItReadsNoBoard | 5: a planted reference is reported (The control CAN fail: each plant goes; a reference in a shared helper is reported too (``cellUnder`` and ``is; ... (+3) | 28 | 0.8 | MOOT | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_IsPureView::test_a_long_hover_sequence_changes_no_state_no_history_and_no_save`<br>AC-2 is a default-deny SOURCE scan of play.js; the behavioural claim (hover changes nothing) is the survivor |
| TestPublicCrosshair_TheLookIsTokensOnly | 2: every crosshair value is a token; the crosshair only ever sets a background (A tint cannot be read as a  | 2 | 0.0 | MOOT | player.css values; the admin's tint is tokens.css/admin.css (test_admin_design_tokens, test_puzzle_solver_page::test_the_scripts_carry_no_colour_literals) |
| TestPublicCrosshair_TheTintStaysApart | 2: a crossed cell is not the colour of a maybe cell; a crossed filled cell keeps its dark ground | 2 | 0.4 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_RowColumnAndCluesLight::test_the_four_cell_states_stay_apart_under_the_tint` |
| TestPublicCrosshair_TouchIsNeverHalfPainted | 1: a mouse leave still clears what a touch leave does not (The exemption  | 1 | 0.2 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_ClearsWhenThePointerLeaves::test_leaving_the_stage_clears_it_and_a_clue_box_does_not` |
| TestPublicCrosshair_TouchIsNeverHalfPainted | 1: a remembered position with nothing painted repaints (Decision 4, by CO | 1 | 0.2 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_NoStaleMarkerAfterRedraw::test_a_redraw_clears_the_marker_and_the_same_cell_crosses_again`<br>decision 4 by the same construction |
| TestPublicCrosshair_TouchIsNeverHalfPainted | 1: a second tap moves the cross and leaves only one | 1 | 0.9 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_FollowsThePointer::test_a_move_clears_the_old_lines_and_marks_the_new`<br>WEAK: mouse move, not a second tap |
| TestPublicCrosshair_TouchIsNeverHalfPainted | 1: a touch crosshair stays after the finger lifts (Decisions 2 and 3. The | 2 | 1.1 | TWIN | `test_puzzle_solver_crosshair.py::TestSolverCrosshair_TouchKeepsTheLastCell::test_a_touch_drag_crosses_the_finger_and_the_crosshair_stays` |
| TestPublicCrosshair_TouchIsNeverHalfPainted | 1: full or none holds at every step of a mixed session | 1 | 1.0 | LOST | LOST/accept-recommended: the half-painted-crosshair invariant over a mixed mouse+touch session has no admin walk; admin has the point cases (NoStaleMarkerAfterRedraw, TouchKeepsTheLastCell) |
| TestPublicCrosshair_TouchIsNeverHalfPainted | 1: the rules do not depend on hover (A no-hover device never matches :hov | 1 | 0.0 | MOOT | CSS claim on player.css; the admin crosshair is the .is-crossed class set by script (solver.js CROSSHAIR comment), not :hover |

### tests/test_public_player_hint.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPublicHint_AContradictingLineIsSkipped | 2: a board where the only deciding line is contradicted is the exhausted ; a line the marks contradict supplies no hint and the others still do | 2 | 0.5 | TWIN | `test_puzzle_solver_hint.py::test_PropertyTest_SolverHint_LineForcedMatchesBruteForce`<br>`test_puzzle_solver_hint.py::test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell`<br>module-level: its corpus includes _contradicting_corpus (null verdicts); WEAK at page level |
| TestPublicHint_AHintIsOneUndoStep | 1: a hint moves the circles like any mark and leaves no crosshair behind  | 1 | 0.3 | TWIN | `test_puzzle_solver_clues.py::TestSolverClues_CirclesFollowEveryCommit::test_drag_click_undo_redo_reset`<br>`test_puzzle_solver_crosshair.py::TestSolverCrosshair_NoStaleMarkerAfterRedraw::test_a_redraw_clears_the_marker_and_the_same_cell_crosses_again`<br>WEAK: no admin cell combines hint and circles/crosshair |
| TestPublicHint_AHintIsOneUndoStep | 1: a save whose hint flag is not true is refused | 4 | 1.2 | TWIN | `test_puzzle_solver_resume.py::test_PropertyTest_SolverResume_RejectsAnyUntrustedSave`<br>WEAK: untrusted-save fuzz; whether it varies the hint flag is not verified by me |
| TestPublicHint_AHintIsOneUndoStep | 1: the hint survives a reload as a hint (The page's own save used to keep | 1 | 0.3 | TWIN | `test_puzzle_solver_resume.py::TestSolverResume_ReloadRestoresBoardCountsAndHistory::test_reload_restores`<br>that test's docstring: 'five strokes, a hint, a ? mark and an undo survive' |
| TestPublicHint_AHintIsOneUndoStep | 1: undo returns the cell to undecided and the count falls and redo restor | 1 | 0.3 | TWIN | `test_puzzle_solver_hint.py::TestSolverHint_IsOneUndoableStroke::test_undo_and_redo_buttons` |
| TestPublicHint_EachPlantFiresTheScenarioItIsAbout | 2: a plant is served fires exactly its scenarios and its control is green; there are plants for every edge the card names | 35 | 75.5 | MOOT | 34 play.js plants (75.5 s) + their edge list |
| TestPublicHint_ExhaustedRevealsNothing | 2: a board no line decides says so at every rung and reveals no cell; the page never holds back a cell to reveal later | 2 | 0.6 | TWIN | `test_player_public_mode.py::TestPublicMode_TheStallBoard::test_the_oracle_s_stalled_boards_drive_it`<br>`test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_hint_stays_on_and_says_why_where_no_line_decides`<br>public-mode claim; survivors need their play.js sentence helper converted first (CONVERT rows) |
| TestPublicHint_RungThreeDerivesTheCell | 2: rung three marks the cell lineforced gives it as one hint stroke; the derived cell is what an independent enumeration finds (The expecta | 6 | 1.7 | TWIN | `test_puzzle_solver_hint.py::TestSolverHint_RevealsOneCell::test_one_click_reveals_the_oracles_cell`<br>`test_puzzle_solver_hint.py::test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell`<br>`test_puzzle_solver_hint.py::TestSolverHintLadder_ThirdPressRevealsTheSameSituation::test_the_third_press_reveals_the_cell_of_that_line`<br>rung 3 = the module's hintCell; admin oracle tests; CARD-409 changes wording, CARD-408 scroll |
| TestPublicHint_RungsOneAndTwoPointAndExplain | 5: only one line is lit after a change and a second press; rung one lights the line the deduction comes from and says so; ... (+3) | 11 | 3.1 | TWIN | `test_puzzle_solver_hint.py::TestSolverHintLadder_FirstPressPointsAtALine::test_the_first_press_highlights_the_line_and_says_so`<br>`test_puzzle_solver_hint.py::TestSolverHintLadder_SecondPressExplains::test_each_reason_is_announced_on_a_board_where_it_holds`<br>`test_puzzle_solver_hint.py::TestSolverHintLadder_ThePureModule::test_the_ladder`<br>CARD-409 rewords the sentence ('the highlighted row (13)'): the survivors change, not the claim |
| TestPublicHint_StayLegibleAndInPlaceWhenZoomedAndScrolled | 1: the lit line and the outlined cell survive zoom and scroll | 1 | 2.6 | LOST | LOST/decide-with-CARD-408: hint highlight stays legible and in place at zoom+scroll; CARD-408 ('Hint brings what it points at into view') owns the replacement |
| TestPublicHint_TheAssetGainsNothing | 1: a page that stashes the solution is caught (The control for the walk:  | 1 | 0.6 | MOOT | plant into play.js |
| TestPublicHint_TheAssetGainsNothing | 1: across a seeded corpus no hint leaves a grid behind (EC (ADR-0041/R2): | 1 | 2.1 | TWIN | `test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised`<br>`test_player_public_mode.py::TestPublicMode_EverySolutionReadIsListedAndGated::test_the_reads_are_exactly_the_listed_sites`<br>WEAK |
| TestPublicHint_TheAssetGainsNothing | 1: every served puzzle file carries exactly the five fields | 1 | 0.1 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_every_puzzle_file_carries_exactly_the_served_key_set` |
| TestPublicHint_TheAssetGainsNothing | 1: the hint adds no request and the only one is the get of its own puzzle | 1 | 1.0 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean` |
| TestPublicHint_TheAssetGainsNothing | 1: the page holds one global and no solution grid before and after hints | 1 | 0.4 | TWIN | `test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised`<br>WEAK: the shared page holds no grid by construction (sealed getter, nine listed reads) |
| TestPublicHint_TheAssetGainsNothing | 1: the scanner also refuses the stash in source | 1 | 0.0 | MOOT | play.js source scan |
| TestPublicHint_TheControlIsOutsideTheToolbar | 5: a rung two sentence is whole and in the viewport at every width; a toolbar button added or the control moved into it is refused; ... (+3) | 8 | 2.2 | MOOT | play.html layout (44 px control under the board); re-decided by CARD-409 (hint text by the board) and CARD-401 |
| TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards | 2: a clean board never gets a hint that disagrees with the solution; the page agrees with the module and the enumeration | 2 | 3.1 | TWIN | `test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_it_agrees_with_the_brute_force_oracle_and_with_play_js`<br>survivor is a CONVERT row (drop its play.js arm); oracle arm carries the claim |
| TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards | 1: the corpus is big and has every kind of board | 1 | 0.0 | MOOT | corpus floor of the retiring test; the PM corpus has its own floor |
| TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards | 1: where a mark is wrong the two differ and only there | 1 | 1.3 | TWIN | `test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_a_wrong_mark_misleads_it_exactly_as_it_misleads_play_js`<br>survivor is a CONVERT row |
| TestPublicHint_TheHeaderClaimIsTrue | 6: a page with a check button makes the claim false; each part of the claim is individually load bearing; ... (+4) | 11 | 0.6 | MOOT | play.js header comment claim |
| TestPublicHint_TheLadderIsTheModules | 3: a hint that is pressed mid gesture does nothing; rung three is the reveal and the others record nothing; ... (+1) | 3 | 1.0 | TWIN | `test_puzzle_solver_hint.py::TestSolverHintLadder_AnyChangeResetsTheLadder::test_the_next_press_is_rung_one_again`<br>`test_puzzle_solver_hint.py::TestSolverHintLadder_ThePureModule::test_the_ladder`<br>`test_puzzle_solver_hint.py::TestSolverHint_DisabledWithNothingToReveal::test_disabled_during_a_drag` |
| TestPublicHint_TheListenerCensus | 3: a hint button without its listener or a listener without its button re; a sixth listener reds it; ... (+1) | 3 | 0.0 | MOOT | play.js listener census |
| TestPublicHint_TheScenariosAreGreenOnTheRealPage | 3: each scenario is green on its own node (The umbrella above names no sc; every scenario passes and none is skipped; ... (+1) | 15 | 6.0 | MOOT | scenario harness over play.js (claims enumerated in the rows above) |
| TestPublicHint_TheSentenceBelowTheBoardKeepsTheZoomModulesPremise | 4: a sentence far longer than any the page says goes past the bound; the usage paragraph comes back with the next change; ... (+2) | 4 | 27.7 | MOOT | play.html stage/sentence geometry (27.7 s); re-decided by CARD-409/403 |
| TestPublicHint_ThreeMarksCoexist | 4: a highlight that can hide the ring is caught; a tint that is not distinct is caught; ... (+2) | 11 | 10.7 | MOOT | distance floors / plants / tokens of player.css's hint tint |
| TestPublicHint_ThreeMarksCoexist | 4: a hinted crossed and circled box shows all three; a hinted line keeps a filled a white and a blank cell apart (The tint ; ... (+2) | 4 | 3.6 | LOST | LOST/decide-with-CARD-409: hint tint vs crossed/circled/maybe distinguishability; admin has the probe (TheMarkerIsMeasurablyApartFromItsGround) and crosshair-vs-four-states analogues only; CARD-409 re-decides the hint highlight |
| - | 5: a bypass is refused beside its clean control; the declaration census is the whole file and is not vacuous (The contr; ... (+3) | 37 | 2.7 | MOOT | lexical scanner over play.js's hint code and its bypass plants |
| - | 1: every neq this card added has a plant that fails it (Every `!==` / `!= | 1 | 0.0 | MOOT | play.js line census |
| - | 3: the contradiction fixture contradicts a line and another still decides; the exhausted fixture is what the card needs; ... (+1) | 3 | 0.0 | MOOT | fixture sanity for the retiring file |
| - | 1: the neq census notices a comparison with no plant (The control for the | 1 | 0.0 | MOOT | control of the retiring census |

### tests/test_public_player_maybe.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPublicMaybe_AReloadRestoresMaybeMarks | 1: maybe marks come back after a reload | 1 | 0.4 | TWIN | `test_puzzle_solver_resume.py::TestSolverResume_ReloadRestoresBoardCountsAndHistory::test_reload_restores`<br>that test's docstring names a '?' mark |
| TestPublicMaybe_AReloadRestoresMaybeMarks | 1: the fetched puzzle file still carries only what the page reads (ADR-00 | 1 | 0.2 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_every_puzzle_file_carries_exactly_the_served_key_set` |
| TestPublicMaybe_AReloadRestoresMaybeMarks | 1: the save gains no field for the fourth brush (ADR-0041/R2 — the fourth | 1 | 0.4 | TWIN | `test_puzzle_solver_resume.py::test_PropertyTest_SolverResume_SaveAndRestoreRoundTrip`<br>save round-trips over a corpus that includes maybe |
| TestPublicMaybe_FourToolsInTheAdminsOrder | 1: each tool is a radio built like its siblings (The fourth button is its | 1 | 0.0 | MOOT | play.html's radio markup; the admin tool is a menu item |
| TestPublicMaybe_FourToolsInTheAdminsOrder | 1: the order check reports a reordered page (The control: the same readin | 1 | 0.0 | MOOT | control of the retired order check |
| TestPublicMaybe_FourToolsInTheAdminsOrder | 1: the public page offers the admin menus four tools in its order | 1 | 0.0 | TWIN | `test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_HoldsFourBrushesOnly::test_menu_lists_the_four_brushes_in_order` |
| TestPublicMaybe_FourToolsInTheAdminsOrder | 1: the tools constant is the markups order (``play.js``'s ``TOOLS`` and t | 1 | 0.0 | MOOT | play.js TOOLS constant |
| TestPublicMaybe_OneToolIsCheckedAtATime | 1: a seeded walk over the tools never checks two (The corpus. Its floor i | 1 | 0.6 | MOOT | radio-group invariant of play.html; the admin brush is a menu with one trigger |
| TestPublicMaybe_OneToolIsCheckedAtATime | 1: choosing each tool leaves exactly that one checked | 1 | 0.3 | TWIN | `test_puzzle_solver_marking.py::TestSolverMarking_ClickIgnoresTheSelectedTool::test_exactly_one_tool_is_pressed`<br>WEAK: admin asserts one pressed tool, not for each of four |
| TestPublicMaybe_TheBrushMarksACell | 3: a drag with the maybe brush marks its whole line (A drag is a separate; choosing maybe and clicking marks the cell and records one stroke; ... (+1) | 3 | 0.8 | TWIN | `test_puzzle_solver_maybe.py::TestSolverMaybe_ClickWithTheMaybeTool::test_two_clicks_mark_then_clear`<br>`test_puzzle_solver_maybe.py::TestSolverMaybe_DragPaintsMaybe::test_drag`<br>`test_puzzle_solver_maybe.py::TestSolverMaybeModule_ClickedStateTable::test_table`<br>AC-1 |
| TestPublicMaybe_TheLookIsDeclaredOnce | 3: the maybe cell look is one rule declaring one background (The paper is; the reading reports each planted defect (The control (ADR-0039/R1): ev; ... (+1) | 9 | 0.0 | MOOT | `test_puzzle_solver_maybe.py::TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell::test_glyph`<br>counts rules in player.css; the maybe look is admin.css's |

### tests/test_public_player_pages.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| - | 31: a book the schema cannot accept is refused and named (``served_book``'; a book with no resolvable puzzle is still served empty (A published sl; ... (+29) | 31 | 7.7 | KEEP | listing doors, bundle/index/book/capacity, routes (vercel.json), R6, AC-390..392: untouched by the play-page swap |
| - | 1: book landing lists and links (AC-387 — the QR landing titles the book  | 1 | 0.2 | CONV | a tile opens /play/<key> through publicPlayer (play.js); the shared page has window.puzzlePlayer |
| - | 1: pages work with analytics blocked (AC-391 — the counted pages play and | 1 | 0.5 | CONV | plays /play/<key> through publicPlayer; the shared-UI shell must carry the GoatCounter tag (CARD-386 F-7: never run with --analytics) - R6 live, re-point and prove |

### tests/test_public_player_probe.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPublicProbe_APinchNeitherOpensNorChangesAProbe | 1: a two finger pinch leaves the probe alone | 1 | 1.2 | LOST | LOST/accept-recommended: pinch while a probe is open; admin zoom tests never open a probe |
| TestPublicProbe_ARedoStackIsNotSavedWhileOpen | 1: a save that does hold the redo stack is caught | 1 | 0.7 | MOOT | plant |
| TestPublicProbe_ARedoStackIsNotSavedWhileOpen | 1: undoing past the checkpoint inside a probe changes what a reload resum | 1 | 0.6 | TWIN | `test_puzzle_solver_resume.py::TestSolverResume_AReloadAbandonsTheOpenProbe::test_an_open_probe_saves_no_redo_stack` |
| TestPublicProbe_ARegionDragIsOneProbeStroke | 1: a save that holds the drag is caught beside its clean control | 1 | 0.4 | MOOT | plant |
| TestPublicProbe_ARegionDragIsOneProbeStroke | 1: the save is the checkpoint save abandon restores and no marker is left | 1 | 0.3 | LOST | LOST/accept-recommended: a Region drag inside a probe is ONE probe stroke; admin Region and probe tests never combine |
| TestPublicProbe_AReloadAbandonsTheOpenProbe | 1: the page says so in one line where the controls are | 1 | 0.2 | MOOT | copy of play.html's probe line; the probe UI text is re-decided by CARD-411/412 |
| TestPublicProbe_AReloadAbandonsTheOpenProbe | 1: the save is the save as of the checkpoint | 1 | 0.4 | TWIN | `test_puzzle_solver_resume.py::TestSolverResume_AReloadAbandonsTheOpenProbe::test_the_save_is_the_save_as_of_the_checkpoint` |
| TestPublicProbe_AReloadAbandonsTheOpenProbe | 1: the save never holds a probe stroke over a seeded corpus | 1 | 2.3 | TWIN | `test_puzzle_solver_resume.py::TestSolverResume_AReloadAbandonsTheOpenProbe::test_the_save_is_the_save_as_of_the_checkpoint`<br>WEAK: corpus half has no twin |
| TestPublicProbe_AbandonRestoresTheCheckpointBoard | 2: over a seeded corpus the board is the checkpoint board cell for cell; the scenario is green | 2 | 2.5 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_AbandonRestoresTheCheckpointBoard::test_abandon_restores_the_board_and_closes_the_probe`<br>WEAK: the seeded corpus (board == checkpoint cell for cell) has no admin twin; admin has the by-hand case |
| TestPublicProbe_CirclesSeeProbeMarksAsMarks | 1: the circle set is circledclues of the recorded board probe strokes inc | 1 | 1.5 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_CountersSeeProbeMarksAsMarks::test_the_same_marks_read_the_same_inside_a_probe` |
| TestPublicProbe_CommitKeepsCellsAndDropsTheLook | 2: over a seeded corpus no cell changes and no marker remains; the scenario is green | 2 | 2.7 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_CommitKeepsCellsAndDropsTheTint::test_keep_keeps_every_cell_and_drops_every_marker`<br>WEAK for the corpus half |
| TestPublicProbe_EachPlantFiresTheScenarioItIsAbout | 1: a plant is served fires exactly its scenarios and its control is green | 25 | 137.2 | MOOT | 25 edge mutants of play.js (137.2 s) |
| TestPublicProbe_MarksCarryTheLook | 3: a rung three hint inside a probe is a member of it; every mark made in a probe carries the marker and the cells before it ; ... (+1) | 3 | 1.3 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_the_probes_marks_carry_the_marker_and_earlier_marks_do_not`<br>`test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_a_hint_revealed_inside_a_probe_belongs_to_it`<br>`test_puzzle_solver_probe.py::TestSolverProbe_TheMarkerIsMeasurablyApartFromItsGround::test_the_ring_is_apart_from_the_ground_it_is_drawn_on`<br>CARD-410/411/412 change the probe UI (dependency) |
| TestPublicProbe_NoAnswerAndNoRequest | 1: every served puzzle file still carries exactly the five fields | 1 | 0.1 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_every_puzzle_file_carries_exactly_the_served_key_set` |
| TestPublicProbe_NoAnswerAndNoRequest | 1: no page variable or stored value is a solution grid after a probe | 1 | 0.5 | TWIN | `test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised`<br>WEAK |
| TestPublicProbe_NoAnswerAndNoRequest | 1: the only request is the get of its own puzzle file through every inter | 1 | 1.0 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean` |
| TestPublicProbe_NoAnswerAndNoRequest | 1: the probe adds no field to the page object and no word solution to the | 1 | 0.0 | MOOT | play.js source scan |
| TestPublicProbe_OnlyOneProbeAtATime | 1: the controls are ignored while a stroke is being drawn | 1 | 0.3 | LOST | LOST/accept-recommended: probe controls mid-stroke; no admin cell |
| TestPublicProbe_OnlyOneProbeAtATime | 1: the probe control is disabled while one is open and a press is a no op | 1 | 0.3 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_OnlyOneProbeAtATime::test_a_second_press_opens_nothing` |
| TestPublicProbe_SolvingCommitsTheProbe | 1: marks that reach the clue solved state commit the probe and the banner | 1 | 0.5 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_SolvingCommitsTheProbe::test_the_solving_mark_commits_the_probe`<br>`test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[probe-auto-commit-decided-by-filled-count]`<br>public arm (clue-solved) is the PM mutant arm |
| TestPublicProbe_SolvingCommitsTheProbe | 1: reset closes an open probe | 1 | 0.4 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_CommitKeepsCellsAndDropsTheTint::test_a_reset_clears_the_open_probe` |
| TestPublicProbe_SolvingCommitsTheProbe | 1: the constructed board is one mark from solved and the fixture is what  | 1 | 0.0 | MOOT | fixture sanity |
| TestPublicProbe_StateIsThePureModulesAndStatesAreFour | 1: a page that decides a transition is refused beside its clean control | 8 | 0.2 | MOOT | plants into play.js |
| TestPublicProbe_StateIsThePureModulesAndStatesAreFour | 1: play js asks the module for every transition and defines none of its o | 1 | 0.0 | MOOT | play.js source scan |
| TestPublicProbe_StateIsThePureModulesAndStatesAreFour | 1: the cell has exactly the four states and a probe session writes no oth | 1 | 2.2 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_StateIsPureAndStatesAreFour::test_the_cell_states_are_four_and_an_unknown_event_is_refused` |
| TestPublicProbe_StateIsThePureModulesAndStatesAreFour | 1: the served module and tokens are the admins byte for byte | 1 | 0.1 | TWIN | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte`<br>R3 |
| TestPublicProbe_TheBarsKeepThePremiseOnAOnePixelSweep | 5: at rest a sample of other heights holds; at rest every width from 320 to 999 at two heights holds and includes ; ... (+3) | 5 | 192.2 | MOOT | 1-px width sweeps of play.html's bars (192.2 s); the narrow-phone layout under the sentence-below-the-board is play.html's and is re-decided by CARD-401/402/403/409/411 |
| TestPublicProbe_TheBarsKeepTheZoomModulesPremise | 6: a line more under the paragraph at rest goes past the bound (The contr; a sentence far longer than any the page says goes past the open bound; ... (+4) | 6 | 52.5 | MOOT | play.html stage premise (52.5 s) |
| TestPublicProbe_TheControlsAreOutsideTheToolbar | 5: a control under the touch floor is refused; a probe control moved into the toolbar is refused; ... (+3) | 7 | 2.8 | MOOT | play.html layout; CARD-411 re-decides the probe buttons ('clear and full size') and keeps 'the bar costs the board no ground' (admin TestSolverProbe_TheBarCostsTheBoardNoGround is that claim's home) |
| TestPublicProbe_TheMarksCoexistByPixels | 1: a circled clue number keeps its ring while the board is probed | 1 | 0.5 | LOST | LOST/accept-recommended: ring on the clue number while probing; disjoint elements by construction |
| TestPublicProbe_TheMarksCoexistByPixels | 1: a hinted probed cell shows the accent and the dash | 1 | 0.8 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_a_hint_revealed_inside_a_probe_belongs_to_it`<br>`test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_the_hint_lines_tint_does_not_repaint_a_probe_cell` |
| TestPublicProbe_TheMarksCoexistByPixels | 1: a probed cell keeps its dashed ring on every ground it can have | 1 | 1.6 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_TheMarkerIsMeasurablyApartFromItsGround::test_the_ring_is_apart_from_the_ground_it_is_drawn_on` |
| TestPublicProbe_TheMarksCoexistByPixels | 1: a ring painted in the grounds own colour is caught | 1 | 3.0 | MOOT | plant |
| TestPublicProbe_TheMarksCoexistByPixels | 1: the probe changes no ground so every tint still shows (The same real e | 1 | 2.9 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_MarksCarryTheTint::test_the_four_states_stay_apart_under_the_tint` |
| TestPublicProbe_TheScenariosAreGreenOnTheRealPage | 3: each scenario is green on its own node (The umbrella above names no sc; every scenario passes and none is skipped; ... (+1) | 14 | 11.7 | MOOT | scenario harness over play.js (14 ids); each scenario's claim is classified in the rows below |
| TestPublicProbe_UndoClampsTheCheckpoint | 1: the keyboard undo and redo move the probe like the buttons | 1 | 0.2 | TWIN | `test_puzzle_solver_marking.py::TestSolverMarking_KeyboardAndLabels::test_ctrl_z_undoes_and_shift_ctrl_z_redoes`<br>WEAK: keyboard undo exists generally; not inside a probe |
| TestPublicProbe_UndoClampsTheCheckpoint | 1: the scenario is green | 1 | 0.5 | TWIN | `test_puzzle_solver_probe.py::TestSolverProbe_UndoClampsTheCheckpoint::test_undo_pops_probe_strokes_first_then_clamps` |
| - | 1: the public probe look comes from tokens (AC-9 (colours): every value i | 1 | 0.0 | MOOT | player.css |

### tests/test_public_player_zoom.py

| class | tests (functions) | ids | s | class | survivor / reason |
|---|---|---|---|---|---|
| TestPublicZoom_APinchZoomsAndPaintsNothing | 2: with region armed the second finger reverts the drag and commits nothi; with region off the pinch zooms and the first fingers cell is unmarked | 2 | 1.5 | TWIN | `test_puzzle_solver_zoom.py::TestSolverZoom_PinchOnTheBoardZooms::test_spreading_100_to_200px_on_a_cell_reads_200_percent_and_marks_nothing`<br>`test_puzzle_solver_zoom.py::TestSolverZoom_PinchCancelsTheStrokeInProgress::test_a_second_finger_reverts_the_drag_and_commits_nothing`<br>AC-5 both arms |
| TestPublicZoom_AZoomedGutterNeverCoversTheBoard | 5: a gutter is pinned exactly while a cell still fits beside it; a pinned gutter always leaves a whole cell in view (F-3's 175% rung, a; ... (+3) | 5 | 2.1 | MOOT | `test_puzzle_solver_zoom.py::TestSolverZoom_CluesStayInViewWhileZoomed::test_each_axis_keeps_its_clues_up_to_the_zoom_its_band_outgrows`<br>`test_puzzle_solver_clues.py::TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::test_each_axis_keeps_its_clues_exactly_when_it_has_the_room`<br>pins play.js's own gutter-unpinning rule (stage geometry); the admin has its own stuck-band rule and tests; CARD-404/405 re-decide pinning at every zoom (owner decision supersedes the play.js pin) |
| TestPublicZoom_NoRequestPerZoom | 1: every zoom interaction issues nothing beyond the initial get (AC-6 — t | 1 | 0.8 | TWIN | `test_puzzle_solver_zoom.py::TestSolverZoom_IsNotSavedAndSendsNothing::test_zoom_sends_no_request_leaves_the_save_untouched_and_resets_on_reload`<br>AC-6 |
| TestPublicZoom_TheAnchoredScrollIsTheModules | 1: the stage lands where anchored scroll says on both axes (AC-4 — assert | 1 | 0.3 | TWIN | `test_puzzle_solver_zoom.py::TestSolverZoom_ZoomKeepsTheViewCentre::test_zoom_out_keeps_the_same_cell_near_the_stages_centre`<br>`test_puzzle_solver_zoom.py::TestZoomArithmetic_PureFunctions::test_anchored_scroll_matches_the_cards_own_formula_by_hand`<br>AC-4 |
| TestPublicZoom_TheArithmeticIsTheModules | 6: neither page invents a zoom key binding (The card's item 5, held to BO; play js consumes the admins own zoom surface and declares none of it (; ... (+4) | 6 | 0.0 | MOOT | source/CSS scan of play.js/player.css or a play.js-vs-admin divergence: no second implementation to compare |
| TestPublicZoom_TheArithmeticIsTheModules | 1: the module still exports all seven names and only over numbers (The ca | 1 | 0.0 | TWIN | `test_puzzle_solver_zoom.py::TestZoomArithmetic_PureFunctions::test_clamp_and_step_cover_the_range_its_edges_and_a_non_multiple`<br>`test_puzzle_solver_zoom.py::TestZoomArithmetic_PureFunctions::test_pinch_zoom_scales_clamps_and_refuses_a_non_positive_distance`<br>claim is about solver_state.js's exports; WEAK: the 'exactly seven names' check has no admin twin (the surface is exercised, not enumerated) |
| TestPublicZoom_TheBoundsComeFromTheModule | 2: both ends disable their button and a press there changes nothing (AC-2; no sequence of presses leaves the modules range (AC-2's completeness h | 2 | 1.2 | TWIN | `test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_zoom_out_at_100_percent_is_a_no_op_and_stays_disabled`<br>`test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_zoom_in_at_300_percent_is_a_no_op_and_stays_disabled`<br>`test_puzzle_solver_zoom.py::TestZoomArithmetic_PureFunctions::test_clamp_and_step_cover_the_range_its_edges_and_a_non_multiple`<br>AC-2; WEAK for the seeded press-walk (admin proves the clamp pure + each end by hand) |
| TestPublicZoom_TheControlsChangeTheZoom | 2: zoom in reads the modules next step and grows every cell (AC-1 — ``ZOO; zoom out from a stepped in board returns to the modules floor (AC-1's  | 2 | 0.6 | TWIN | `test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_zoom_in_once_reads_125_percent_and_scales_every_cell`<br>`test_puzzle_solver_zoom.py::TestSolverZoom_ButtonsStepAndClamp::test_the_full_25_point_staircase_up_and_down`<br>AC-1 zoom buttons step |
| TestPublicZoom_TheGutterRuleHoldsOverItsOperands | 6: a scrolled page and an unbounded stage hold the visible height operand; a stage missing a measured element is left alone and never thrown at (; ... (+4) | 6 | 57.5 | MOOT | `test_puzzle_solver_clues.py::TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::test_each_axis_keeps_its_clues_exactly_when_it_has_the_room`<br>57.5 s viewport x rung sweep of play.js's pin rule; same supersession by CARD-404/405 |
| TestPublicZoom_TheLandscapeToolbarIsOneRow | 8: a portrait phone keeps its readout; every landscape width from the headline phone up stays one row (The re; ... (+6) | 8 | 12.1 | MOOT | play.html toolbar at 844x390; the toolbar is the admin's, re-decided by CARD-401/402 |
| TestPublicZoom_TheStageEndsAboveTheFold | 4: it follows a toolbar that changes height with no resize (The ResizeObs; it holds with the page scrolled when the rule is re asked (The cap is ; ... (+2) | 4 | 38.6 | MOOT | play.html stage cap follows the toolbar; the claim is re-decided by CARD-403 ('ends above the fold at any toolbar height'), which owns the replacement test. UNPROTECTED on the shared page until 403 merges |
| TestPublicZoom_ZoomRecordsNoStroke | 1: every zoom interaction leaves the board history and save identical (AC | 1 | 0.7 | TWIN | `test_puzzle_solver_zoom.py::TestSolverZoom_ChangingZoomChangesNoSolveState::test_a_100_to_300_to_100_round_trip_changes_nothing_recorded`<br>AC-3 |
## 5. The keep list, with the plant that reds each claim (verified by `ast` to exist once and be collected; plants NOT run)

| keep-list claim | test (exists once, collected) |
|---|---|
| R2 served-tree scan finds a plant in every encoding | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_the_scan_finds_a_planted_solution_in_every_encoding` (ok) |
| R2 solution key added to a served file | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_a_plant_that_adds_a_solution_key_to_a_served_file_reds_the_key_check` (ok) |
| R2 served tree clean (own control) | `test_public_player.py::test_served_tree_is_clean_of_answers` (ok) |
| R2 title exemption scoped | `test_public_player_pages.py::test_the_book_title_exemption_is_scoped_and_its_cost_is_measured` (ok) |
| R2 plant serving the solution reds the scan | `test_player_public_mode.py::TestPublicMode_NothingServedCarriesTheSolution::test_a_plant_that_serves_the_solution_reds_the_scan` (ok) |
| R2 sealed getter | `test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised` (ok) |
| R2 sealed getter plant (mutant) | `test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[the-solution-is-not-sealed]` (ok) |
| R2 every solution read listed and gated | `test_player_public_mode.py::TestPublicMode_EverySolutionReadIsListedAndGated::test_the_reads_are_exactly_the_listed_sites` (ok) |
| R3 plant edits a copy | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_a_plant_that_edits_a_copy_reds` (ok) |
| R3 assembly-time check refuses a non-identical copy | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_assembly_time_check_refuses_a_copy_that_is_not_identical` (ok) |
| R3 copies equal sources | `test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte` (ok) |
| R4 fetch added (mutant) | `test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[a-network-call-is-added]` (ok) |
| R4 plant of each kind reds the scan | `test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_a_plant_of_each_kind_reds_the_scan` (ok) |
| R4 sweep with Watch (non-GET) | `test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean` (ok) |
| R4 sweep is not vacuous | `test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_the_sweep_is_not_vacuous_a_gutted_control_reds_it` (ok) |
| routes: two doors routed by vercel.json | `test_public_player_pages.py::test_the_two_doors_are_routed_by_the_shipped_config` (ok) |
| 404 control: unknown slug lands softly | `test_public_player_pages.py::test_unknown_slug_lands_softly` (ok) |
| 404 control: no-puzzle address draws no board | `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_an_address_that_is_no_puzzle_says_so_and_draws_no_board` (ok) |
| three URL shapes served | `test_player_shared_ui_site.py::TestSharedUi_TheDoorsKeepTheirShapes::test_the_preview_server_serves_the_three_url_shapes` (ok) |
| key set of puzzle JSON | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_every_puzzle_file_carries_exactly_the_served_key_set` (ok) |
| key set plant | `test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_a_bundle_whose_puzzle_carries_a_solution_key_is_served_without_it` (ok) |
| R6 no homegrown tracking | `test_public_player_pages.py::test_no_homegrown_tracking` (ok) |

Not in the audited files and therefore unchanged by this card: the landing address computed once (CARD-389) lives in `tests/test_book_landing_address.py` (exists on this tree); the bundle's R1/R5/R7 refs are `tests/test_player_bundle.py`'s (119 ids, KEEP-LIVE).

Card AC-3 asks each keep-list claim to red under its plant when the retirement is done. The plants listed above exist today; **their red results are recorded by the deletion step, not here** (no pytest in this step).

## 6. Dependencies on the findings cards and on CARD-394

Survivor files that cards 394 and 400-413 (all `ready`, Wave unstamped, read from the branch copies of the cards) list in `**Touches:**`:

| survivor file | cards that will edit it |
|---|---|
| tests/test_player_public_mode.py | - |
| tests/test_player_shared_ui_site.py | CARD-394, CARD-409, CARD-413 |
| tests/test_public_player_pages.py | - |
| tests/test_puzzle_solver_brush_menu.py | CARD-401, CARD-413 |
| tests/test_puzzle_solver_clues.py | CARD-400, CARD-403, CARD-404, CARD-405, CARD-406 |
| tests/test_puzzle_solver_crosshair.py | - |
| tests/test_puzzle_solver_hint.py | CARD-401, CARD-408, CARD-409 |
| tests/test_puzzle_solver_marking.py | - |
| tests/test_puzzle_solver_maybe.py | CARD-402 |
| tests/test_puzzle_solver_page.py | CARD-401, CARD-407, CARD-409, CARD-411, CARD-413 |
| tests/test_puzzle_solver_phone.py | CARD-401, CARD-402, CARD-403, CARD-405, CARD-406 |
| tests/test_puzzle_solver_probe.py | CARD-410, CARD-411, CARD-412 |
| tests/test_puzzle_solver_progress.py | - |
| tests/test_puzzle_solver_resume.py | CARD-407, CARD-411, CARD-412 |
| tests/test_puzzle_solver_zoom.py | CARD-401, CARD-402, CARD-403, CARD-404, CARD-405, CARD-406, CARD-407, CARD-408 |

Reading of it: a twin whose survivor file is rewritten by a findings card is not a risk to the CLAIM (the findings cards re-state it with the owner's new decision) but it is a risk to the NAME: the deletion step must re-verify each survivor by `ast` at its own tip, and a survivor that a findings card retires must be re-pointed. The sharpest cases:

* **CARD-403** (stage ends above the fold) is the only owner of that claim once play.js's pin goes; **CARD-404/405/406** (clue strips capped, left/top only, Fit) rewrite `test_puzzle_solver_clues.py` and `_zoom.py`, which are the survivors of the gutter/pinning rows (zoom `AZoomedGutterNeverCoversTheBoard`, `TheGutterRuleHoldsOverItsOperands`: 11 ids, 59.6 s, MOOT).
* **CARD-409/413** touch `player/assemble.py` and `tests/test_player_shared_ui_site.py` (conflict edges with this card's switch/delete step) and **CARD-394** touches `assemble.py`, `test_player_shared_ui_site.py`, `docs/deploy/player.md`: all three must merge BEFORE the switch/delete step (the card already says CARD-394; add 409 and 413).
* **CARD-400** changes the circle rule (`solver_state.js`, `test_puzzle_solver_clues.py`): the circles TWIN rows (20 ids) point at tests it will edit.
* **CARD-410/411/412** rewrite `test_puzzle_solver_probe.py` and `_resume.py`: probe TWIN rows (24 ids).
* **CARD-408** owns the replacement for hint 'in place at zoom + scroll' (LOST row L-hint-zoom); **CARD-409** owns hint highlight coexistence (4 LOST ids).
* **CARD-394** replaces `--bootstrap` with a committed stylesheet (`player/bootstrap-lite.css`): the CLI rows that depend on the two-flag contract (`test_the_cli_flags_are_all_or_nothing`, MOOT; `test_the_driver_refuses_one_of_the_two_flags_and_print_only_renders_nothing`, CONVERT) are classified on the pre-394 contract and must be re-read after 394 lands.

## 7. Blast radius of the deletion step (every consumer found; command: `grep -rnE 'play\.js|player\.css|play\.html|PLAY_JS|PLAYER_FILES'` over tests/ scripts/ player/ docs/ meta/ src/ vercel.json, plus a grep for the audited test file names)

**Files that go (or split):** `player/play.js` (1525 lines), `player/play.html` (199), `player/player.css` (950; **splits**, the listing half from line ~310 stays and is linked by `library.html` and `book.html`), tests: agreement 4043, circles 1553, crosshair 1386, hint 2862, maybe 872, probe 1814, zoom 2283 lines (14813 lines in 7 files, after the LOST rows are ruled, because the files import each other); 14 ids go from `test_public_player.py` (12 TWIN + 2 MOOT), 3 from `test_player_shared_ui_site.py`, 1 from `test_player_public_mode.py` (exact id list: Appendix A).

**Code that changes:**
* `player/assemble.py` (1959 lines, 19 hits): `PLAYER_FILES` loses `play.html`/`play.js`; `SHARED_UI_PLAYER_FILES` and its derivation comment; `COPIED_FROM_ADMIN` absorbs `SHARED_UI_COPIED_FROM_ADMIN` (solver.js, admin.css join solver_state.js, tokens.css); `SharedUi`, `shared_ui_play_page`, `assemble(shared_ui=...)` and `main(shared_ui_fragment=...)` become the only path; the module docstring (lines 25-39) names `play/index.html (from player/play.html)`; `--shared-ui-fragment` / `--bootstrap` flags and the 'all or nothing' rule retire or change with CARD-394; the output stylesheet set (Bootstrap vs CARD-394's file) is CARD-394's.
* `scripts/assemble_player_site.py`: `--shared-ui`, `--bootstrap`, `render_shared_ui_fragment` (needs **jinja2** at build time: the driver renders `puzzle_solve.html`; the assembler stays stdlib-only); `scripts/preview_player_site.py` and `scripts/README.md` (3 mentions).
* `player/library.html`, `player/book.html` (comments naming play.html; `<link href="/player.css">`), `player/pages.js` (comments naming play.js/play.html, `player.css` classes).
* `src/nonogram/admin/static/solver.js` (4) and `solver_state.js` (2): comments only ("twin of player/play.js's ...", "the words of player/play.js's HINT_EXHAUSTED"). G-4 forbids editing admin files in this card: the comments go stale and are an owner/card decision (leave, or a comment-only edit in a findings card).
* `vercel.json`: **no change** (the three rewrites already serve `/play/:key -> /play/index.html`, which the shared shell occupies).

**Tests outside the audited set that name the retiring files (found by grep):**
* `tests/test_impact_set.py:1169-1175`, `test_the_real_player_assets_select_every_public_player_test`: hard-codes the three asset names and `len(public) >= 9` test files: **CONVERT** (it reds on the deletion; re-point at a surviving asset and the surviving test files). Not in the card's Touches.
* `tests/test_check_ref_resolution.py`: frozen censuses that count the refs of these files: `CENSUS (575)`, `TRACE_TESTS (507)`, `DEFINED (411)`, `SAME_FILE_PROSE (19)`, `FALSELY_ALIVE (155)` and the `_AC392_REF` pin (`test_public_player_pages.py::test_no_homegrown_tracking`, KEEP-LIVE, stays). Retiring the five test ids named by requirements.yml/trace.yml and moving them to survivors changes `CENSUS`/`TRACE_TESTS`/`DEFINED`/`SAME_FILE_PROSE` (the docstring node-id table of `test_public_player.py` is a SAME_FILE_PROSE member). **Not re-derived here** (pytest forbidden); the deletion step must re-derive the hashes, never paste.
* Prose naming the files (comments only; no census): `test_nfr001_generation_time.py`, `test_approval_guess_gate.py`, `test_book_player_domain.py`.
* `RENDER_HEAVY_SNAPSHOT` (`meta/profiling/rank_durations.py`, `test_suite_profile.py`) names no audited file (grep = 0); `tests/wave_close_marker.py` names none (grep = 0): the family is outside CARD-395's marker, so every second below is a merge-gate second.

**Model rows that cite a retiring test (honest-ref rule: a ref to a deleted test must move to a survivor):** requirements.yml AC-383 (5559), AC-384 (5565), AC-385 (5571), AC-386 (5577), EC-050 (5675, plus a comment at 7145); trace.yml 2398-2403 (the same five); ADR-0041/R4 `check.ref` (line 366); `docs/deploy/player.md:415`; `docs/how-it-works/.../11-the-public-player.md:200`. Proposed moves: AC-383 -> `test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_a_real_puzzle_plays_to_the_solved_banner`; AC-384 -> `test_player_public_mode.py::TestPublicMode_SolvedComesFromTheClues::test_it_agrees_with_the_oracle_and_with_play_js` (after its CONVERT rename: the id contains `play_js`, so it must be RENAMED when its play.js arm is dropped, and the model rows follow the new name); AC-385 -> `test_puzzle_solver_resume.py::TestSolverResume_ReloadRestoresBoardCountsAndHistory::test_reload_restores` plus `TestPublicMode_TheSave`; AC-386 -> `test_puzzle_solver_page.py::TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways` (WEAK: AC-386 says MAX_SIZE per side; the survivor measures the page fit, not MAX_SIZE); EC-050 / ADR-0041/R4 -> `TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean` with the `a-network-call-is-added` mutant as its plant. ADR-0041/R3 (`check: review-lens`) still reads 'copy of solver_state.js' and needs the 'four files + shell' amendment the card promises; **ADR-0041 R2's check ref** (`test_bundle_is_clean_of_answers, test_served_tree_is_clean_of_answers, test_the_book_title_exemption_is_scoped_and_its_cost_is_measured`) names three KEEP-LIVE tests and does not move. Other docs that describe the retiring files: `docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md` (17 hits), its README (3, a file-size table), `diagrams/11-bundle-to-site.puml` (2), `docs/deploy/player.md` (6 hits; the 'What production is' observation tables describe a play.js deployment and are dated history), `meta/design/components.md` (the public tile, KEEP).

**Cards:** CARD-384 (parked) closes as moot with a one-line note (card text); CARD-328 is already `done` (its guard file is the 193 MOOT ids). Stale worktrees still exist for CARD-324/325/326/327/380 (all `done`) and 384 (parked): not touched by me (`git worktree list`), housekeeping for the orchestrator.

## 8. Gate time (mine, from the quiet CARD-395 rerun; 3516 s wall, 3506 s attributed)

| | ids | summed s |
|---|---|---|
| RETIRE-TWIN | 134 | 69.8 |
| RETIRE-MOOT | 542 | 673.5 |
| **retired** | **676** | **743.3** |
| LOST (kept until ruled; saved too if all are accepted) | 27 | 19.7 |
| CONVERT (stay; dropping the play.js arms saves a little, unmeasured) | 20 | 21.8 |
| KEEP-LIVE | 279 | 298.0 |

Estimated gate saving of the deletion step: **743 s = 12.4 min** summed from the quiet rerun (share of the 3506 s attributed: 21.2 %); 763 s = 12.7 min if every LOST row is accepted. With the carried 0.74 solo-scaling factor (not re-measured by me; whether it applies to a file that already came from a quiet run is an assumption): 550 s = 9.2 min (9.4 min if all LOST accepted). The card's 917.1 s / 19.9 % planning figure came from the contended CARD-388 run and over-states it; the quiet figures are the ones to quote. Biggest single items (MOOT): probe 1-px width sweeps 192.2 s (5 ids), probe plants 137.2 s (25), hint plants 75.5 s (35), gutter-rule sweep 57.5 s (6), probe premise 52.5 s (6), zoom above-the-fold 38.6 s (4), hint sentence-below premise 27.7 s (4): 581 s of the 743 s are these seven classes (85 ids) and are play.html layout or play.js plant harness. The 171 plant/scenario-harness ids alone are 273.5 s. Seconds are setup+call+teardown per id, as in CARD-395's per-file table.

## 9. The deletion step: estimate, split, order, deploy sequence

**Estimate (mine): 5c over about 2.5 days for everything after this audit** (the card's 8c (2.5d) included the audit; the audit at class granularity with ids exhaustive was about 1c). **It should be split in two plus an owner decision**, because half of it is safe before the production deploy and half is not:

0. **This step (audit): done in this commit, deletes nothing.** Owner rules the LOST list (decision, no work; if 'decide' rows are to be ported, each port is a few cells in `test_puzzle_solver_crosshair.py` / `_probe.py`, preferably carried by the findings card that already touches those files).
1. **CONVERT-NOW (about 2c, valid on today's tree, merge BEFORE the production deploy is even decided):** the changes that only REMOVE a dependence on play.js and are true with play.js still present: re-point `play_exhausted_sentence()` at solver.js `PUBLIC_EXHAUSTED` (unblocks ~26 sweep/stall cells), drop the `_PLAY` comparator arms of the `hint`/`solved` checks and rename the three tests whose names contain `play_js` (and the model rows that cite them), re-point `test_the_static_half...` plant, the `test_impact_set.py` hard-codes, and move the 5 model refs + 2 docs to their survivors. Run each survivor's plant red (card AC-2/AC-3). Net node-id change: 0 (renames only).
2. **SWITCH + DELETE (about 3c, only after: CARD-394, 409, 413 merged; the findings cards 401-405 merged if the owner wants the layout claims held meanwhile; the owner's go; the production deploy observed working):** make shared-UI the default and delete the flags, the old `play_page` path, `play.js`, `play.html`, the play half of `player.css` (split), the 7 feature files, the 14 + 3 + 1 retiring ids elsewhere, the CONVERT rows that depend on the flip (pages play-page tests, `test_player_shared_ui_site.py` default-contract cells), docs/ADR text, the frozen censuses (re-derived), AC-4 census cell reading `git ls-files player/`, and the net-removal check (AC-6/AC-7: removed ids == RETIRE rows both ways).

**Deploy sequence the deletion must respect:** production today serves play.js (`nonogram-studio`, deployed from the Vercel CLI out of `build/site`; no Git connection, per `docs/deploy/player.md`). (1) merge CARD-394 and build the shared-UI site; (2) owner tests the preview and rules the LOST list and the two open owner items from CARD-385/386 (old `nonogram-public:<key>` saves are not read -> visitors start fresh; the solved banner reads 'Solved: Puzzle <key>'); (3) owner deploys the shared-UI build and the deploy is OBSERVED (the deploy doc's observation table); the shell must also be proven with `--analytics` (CARD-386 F-7: never run) and `pages_work_with_analytics_blocked` re-pointed; (4) only then merge the SWITCH + DELETE card. Merging it earlier would leave production on a play.js nobody tests (G-1). Note the build now needs jinja2 on the machine that assembles (the admin extra), which the old default did not.

**Owner-budget note:** card AC-1/AC-2 ask for a NEW permanent test module (`test_public_player_retirement_audit.py`) reading this table with two plants. The owner's rule is fewer tests; a one-shot script run at the deletion step (set equality of ids, survivor-exists-once by `ast`) gives the same assurance without a permanent cell. This is the orchestrator's/owner's call; I did not create it.

## 10. What was NOT done

No test run (lock held, gate pid 64397 live at start), so no collect-only (ids come from the 11699-id quiet gate list and match the carried counts exactly: 34/193/86/70/175/21/33/101/39 for the nine `test_public_player*.py` modules, 78 for `test_player_public_mode.py`, 53 for `test_player_shared_ui_site.py`, 119 for `test_player_bundle.py`; AST resolves 1002/1002); no plant run; the CONVERT and LOST classes are by reading, not by execution; the gate durations are from main at CARD-395's merge, the audited files are identical on `79c5052d` for the player family (not re-diffed by me beyond the id match); nothing deleted or edited under `src/`, `tests/`, `player/`; main checkout untouched; `dispatcher.state` untouched; the production DB never contacted.

## Appendix A: every audited node id and its class (1002 lines; machine-readable: `id | class`)

```text
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_a_trailing_slash_on_the_base_does_not_double | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_builds_the_owner_s_own_example | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_a_key_that_is_not_r1_s[073280EDD0] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_a_key_that_is_not_r1_s[073280edd00] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_a_key_that_is_not_r1_s[073280edd] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_a_key_that_is_not_r1_s[073280edgz] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_a_key_that_is_not_r1_s[None] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_a_key_that_is_not_r1_s[] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_to_build_a_url_with_no_base[   ] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_to_build_a_url_with_no_base[None] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_it_refuses_to_build_a_url_with_no_base[] | KEEP-LIVE
tests/test_player_bundle.py::TestPlayUrl_TheShapeTheDeployPageRecords::test_the_segment_is_the_one_the_deploy_page_records | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_a_record_keys_to_the_adr_s_own_recipe | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_a_record_with_no_grid_is_refused_rather_than_keyed | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_it_refuses_a_stored_value_that_is_not_a_grid[None] | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_it_refuses_a_stored_value_that_is_not_a_grid[not a grid] | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_it_refuses_a_stored_value_that_is_not_a_grid[stored1] | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_it_refuses_a_stored_value_that_is_not_a_grid[stored2] | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_it_refuses_a_stored_value_that_is_not_a_grid[stored3] | KEEP-LIVE
tests/test_player_bundle.py::TestPuzzleKeyOfRecord_OneRecipeForARow::test_stored_integers_key_the_same_as_stored_booleans | KEEP-LIVE
tests/test_player_bundle.py::test_a_book_stored_mixed_is_bundled_in_print_order | KEEP-LIVE
tests/test_player_bundle.py::test_a_legitimate_value_stays_green[a name that looks like an encoding but is the stored one] | KEEP-LIVE
tests/test_player_bundle.py::test_a_legitimate_value_stays_green[a non-ascii name with surrounding whitespace] | KEEP-LIVE
tests/test_player_bundle.py::test_a_legitimate_value_stays_green[no stored name at all, so the neutral fallback] | KEEP-LIVE
tests/test_player_bundle.py::test_a_legitimate_value_stays_green[no stored tier at all] | KEEP-LIVE
tests/test_player_bundle.py::test_a_legitimate_value_stays_green[two books with the same puzzles and different titles] | KEEP-LIVE
tests/test_player_bundle.py::test_a_member_with_an_unreadable_grid_is_named_not_silently_dropped | KEEP-LIVE
tests/test_player_bundle.py::test_a_puzzle_that_leaves_every_finalized_book_leaves_the_bundle | KEEP-LIVE
tests/test_player_bundle.py::test_a_wrong_exemption_is_loud_in_the_scan[exemption0-no ADR recipe] | KEEP-LIVE
tests/test_player_bundle.py::test_a_wrong_exemption_is_loud_in_the_scan[exemption1-no named non-solution source] | KEEP-LIVE
tests/test_player_bundle.py::test_a_wrong_exemption_is_loud_in_the_scan[exemption2-no named non-solution source] | KEEP-LIVE
tests/test_player_bundle.py::test_an_undeclared_field_is_a_violation_and_not_a_pass | KEEP-LIVE
tests/test_player_bundle.py::test_bundle_is_clean_of_answers | KEEP-LIVE
tests/test_player_bundle.py::test_bundle_tree_and_clues_match_the_encoder | KEEP-LIVE
tests/test_player_bundle.py::test_each_sanctioned_source_absorbs_only_the_adrs_own_recipe[clues] | KEEP-LIVE
tests/test_player_bundle.py::test_each_sanctioned_source_absorbs_only_the_adrs_own_recipe[key] | KEEP-LIVE
tests/test_player_bundle.py::test_each_sanctioned_source_absorbs_only_the_adrs_own_recipe[puzzle_keys] | KEEP-LIVE
tests/test_player_bundle.py::test_each_sanctioned_source_absorbs_only_the_adrs_own_recipe[slug] | KEEP-LIVE
tests/test_player_bundle.py::test_every_declared_field_has_one_source_and_the_exemption_picks_which | KEEP-LIVE
tests/test_player_bundle.py::test_export_is_readonly_and_deterministic | KEEP-LIVE
tests/test_player_bundle.py::test_identical_grids_are_one_public_puzzle | KEEP-LIVE
tests/test_player_bundle.py::test_no_other_book_action_writes_the_bundle[/book/{book_id}/add-puzzles-data1] | KEEP-LIVE
tests/test_player_bundle.py::test_no_other_book_action_writes_the_bundle[/book/{book_id}/status-data0] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates0-None] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates1-None] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates2-'easy'] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates3-'easy'] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates4-'  a'] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates5-1] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates6-1] | KEEP-LIVE
tests/test_player_bundle.py::test_settled_is_a_function_of_its_candidates_and_of_nothing_else[candidates7-['a']] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[a diagonal traversal in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[a list as the key] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[a nested object as the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[a published puzzle's file removed] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[a puzzle file under a key nothing published] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[a width that is not the grid's extent] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[an index entry with its tier dropped] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[another file's declared names in a puzzle file] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[base64 of the packed bits in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[base85 of the packed bits in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[each row reversed in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[grid as a field] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[grid as dots and hashes] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[grid bits column-major] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[grid bits in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[per-row hex in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[picture name as the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[run-length of the cells in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[the bits in a book's puzzle_keys] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[the bits in the tier] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[the bits joined by dashes in the title] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[the untruncated digest as the key] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[the untruncated digest] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[the whole grid in index.json under clues] | KEEP-LIVE
tests/test_player_bundle.py::test_the_answer_scan_catches_each_leak_shape[undeclared field] | KEEP-LIVE
tests/test_player_bundle.py::test_the_belt_runs_on_the_bytes_the_exporter_writes | KEEP-LIVE
tests/test_player_bundle.py::test_the_book_page_offers_the_action_and_it_writes_the_bundle | KEEP-LIVE
tests/test_player_bundle.py::test_the_corpus_floor_is_a_bound_the_corpus_does_not_set | KEEP-LIVE
tests/test_player_bundle.py::test_the_corpus_records_have_the_shape_the_store_returns | KEEP-LIVE
tests/test_player_bundle.py::test_the_declared_schema_is_the_field_set_the_criteria_name | KEEP-LIVE
tests/test_player_bundle.py::test_the_default_output_directory_is_a_gitignored_build_directory | KEEP-LIVE
tests/test_player_bundle.py::test_the_exemptions_two_premises_are_measured_not_cited | KEEP-LIVE
tests/test_player_bundle.py::test_the_export_writes_no_float_and_refuses_one | KEEP-LIVE
tests/test_player_bundle.py::test_the_finalized_statuses_are_every_status_but_draft | KEEP-LIVE
tests/test_player_bundle.py::test_the_key_is_the_adrs_worked_example | KEEP-LIVE
tests/test_player_bundle.py::test_the_key_refuses_a_grid_row_major_order_has_no_meaning_for[grid0-no rows] | KEEP-LIVE
tests/test_player_bundle.py::test_the_key_refuses_a_grid_row_major_order_has_no_meaning_for[grid1-no columns] | KEEP-LIVE
tests/test_player_bundle.py::test_the_key_refuses_a_grid_row_major_order_has_no_meaning_for[grid2-ragged] | KEEP-LIVE
tests/test_player_bundle.py::test_the_key_separates_the_recipes_parts[a cell swapped-grid1-other1] | KEEP-LIVE
tests/test_player_bundle.py::test_the_key_separates_the_recipes_parts[a transposed grid-grid2-other2] | KEEP-LIVE
tests/test_player_bundle.py::test_the_key_separates_the_recipes_parts[the same cells under two extents-grid0-other0] | KEEP-LIVE
tests/test_player_bundle.py::test_the_route_the_owner_posts_is_read_only_too | KEEP-LIVE
tests/test_player_bundle.py::test_the_serialisation_levers_are_pinned[key order-sorted] | KEEP-LIVE
tests/test_player_bundle.py::test_the_serialisation_levers_are_pinned[line ending-lf only] | KEEP-LIVE
tests/test_player_bundle.py::test_the_serialisation_levers_are_pinned[non-ascii-escaped] | KEEP-LIVE
tests/test_player_bundle.py::test_the_serialisation_levers_are_pinned[trailing newline-present] | KEEP-LIVE
tests/test_player_bundle.py::test_the_slug_does_not_move_when_the_title_is_edited | KEEP-LIVE
tests/test_player_bundle.py::test_the_slug_is_content_addressed_and_not_the_books_row_id | KEEP-LIVE
tests/test_player_bundle.py::test_the_solution_derived_exemption_is_the_three_fields_the_adr_sanctions | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_log_catches_a_write | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[  BEGIN (implicit)-False] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[CREATE TABLE t (a int)-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[DELETE FROM books-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[DROP TABLE puzzles-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[GRANT ALL ON puzzles TO x-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[INSERT INTO puzzles VALUES (1)-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[MERGE INTO puzzles-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[PRAGMA foreign_keys=ON-False] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[REPLACE INTO puzzles VALUES (1)-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[SELECT 1-False] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[TRUNCATE TABLE puzzles-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[UPSERT INTO puzzles VALUES (1)-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[\xbfqu\xe9?-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[select * from puzzles-False] | KEEP-LIVE
tests/test_player_bundle.py::test_the_statement_verdict_is_default_deny[update books set title='x'-True] | KEEP-LIVE
tests/test_player_bundle.py::test_the_stores_internal_fingerprint_is_not_the_public_key | KEEP-LIVE
tests/test_player_bundle.py::test_the_title_never_falls_back_to_the_picture_name | KEEP-LIVE
tests/test_player_bundle.py::test_two_books_with_the_same_puzzles_are_one_public_book | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EverySolutionReadIsListedAndGated::test_a_tenth_read_is_found | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EverySolutionReadIsListedAndGated::test_the_gated_calls_are_exactly_the_ones_the_gates_name | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EverySolutionReadIsListedAndGated::test_the_reads_are_exactly_the_listed_sites | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_a_network_plant_reds_the_scan_beside_a_clean_control[solver.js] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_a_network_plant_reds_the_scan_beside_a_clean_control[solver_state.js] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[a-network-call-is-added] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[a-public-payload-with-a-solution-is-accepted] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[admin-hint-loses-its-fallback] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[admin-loses-its-counters-and-check] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[admin-resumes-a-public-stamp] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[admin-save-is-stamped-public] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[admin-solved-is-read-from-the-clues] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[banner-decided-by-filled-count] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[check-left-on-the-page] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[clue-solved-ignores-the-columns] | CONVERT
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[errors-counted-from-the-solution-in-public] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hint-counts-where-no-line-decides] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hint-disabled-again-where-no-line-decides] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hint-falls-back-to-revealing-a-cell-oracle] | CONVERT
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hint-falls-back-to-revealing-a-cell-stall] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hint-is-silent-where-no-line-decides] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hint-reveals-a-cell-where-no-line-decides] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hintLine-reads-the-solution-ungated] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[nextHint-reads-the-solution-ungated] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[probe-auto-commit-decided-by-filled-count] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[probe-auto-commit-reads-the-solution-ungated] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[progress-counted-from-the-solution-in-public] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[public-marks-ignore-the-empty-marks] | CONVERT
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[solved-reads-the-solution-ungated] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[the-save-is-fingerprinted-from-a-solution] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[the-save-reads-the-solution-in-public] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[the-solution-is-not-sealed] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_EveryWayOfLosingItIsCaught::test_there_is_a_mutant_for_every_way_the_card_names | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_a_plant_of_each_kind_reds_the_scan[fetch("/x")] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_a_plant_of_each_kind_reds_the_scan[import('/x.js')] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_a_plant_of_each_kind_reds_the_scan[navigator.sendBeacon('/x')] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_a_plant_of_each_kind_reds_the_scan[new EventSource('/x')] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_a_plant_of_each_kind_reds_the_scan[new WebSocket('ws://x')] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_a_plant_of_each_kind_reds_the_scan[new XMLHttpRequest()] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_the_admin_player_files_contain_no_network_call[solver.js] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NoNetworkInAnyMode::test_the_admin_player_files_contain_no_network_call[solver_state.js] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NothingServedCarriesTheSolution::test_a_payload_that_ships_the_solution_is_what_the_scan_exists_to_find | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NothingServedCarriesTheSolution::test_a_plant_that_serves_the_solution_reds_the_scan[flat] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NothingServedCarriesTheSolution::test_a_plant_that_serves_the_solution_reds_the_scan[json-spaced] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NothingServedCarriesTheSolution::test_a_plant_that_serves_the_solution_reds_the_scan[json] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NothingServedCarriesTheSolution::test_a_plant_that_serves_the_solution_reds_the_scan[zero-one] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_NothingServedCarriesTheSolution::test_the_assembled_tree_carries_no_solution_in_any_encoding | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_SolvedComesFromTheClues::test_it_agrees_with_the_oracle_and_with_play_js | CONVERT
tests/test_player_public_mode.py::TestPublicMode_SolvedComesFromTheClues::test_the_corpus_is_big_unique_and_two_sided | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_SolvedComesFromTheClues::test_the_one_difference_from_the_admin_is_a_maybe_on_a_solved_board | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheAdminDefaultIsUnchanged::test_errors_progress_check_the_fallback_and_the_fingerprint_are_all_there | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_an_unclicked_step_is_found_by_the_sweep_not_only_by_the_census[chromium] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_every_control_family_is_read_by_the_census[data-player-action] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_every_control_family_is_read_by_the_census[data-player-confirm] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_every_control_family_is_read_by_the_census[data-player-probe-action] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_every_control_family_is_read_by_the_census[data-player-tool] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_every_control_family_is_read_by_the_census[data-player-zoom-action] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_the_real_template_is_fully_swept_and_a_plant_is_not | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_the_template_has_the_controls_the_census_expects | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_a_wrong_mark_misleads_it_exactly_as_it_misleads_play_js | CONVERT
tests/test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_it_agrees_with_the_brute_force_oracle_and_with_play_js | CONVERT
tests/test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_the_corpus_is_big_and_has_every_kind_of_board | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks::test_there_is_never_a_hint_where_no_line_decides | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_ThePayload::test_a_public_payload_is_still_checked_for_its_shape | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_ThePayload::test_a_public_payload_with_a_solution_is_refused | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_ThePayload::test_even_a_null_or_empty_solution_key_is_refused | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_ThePayload::test_the_default_mode_still_needs_its_solution | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_ThePayload::test_the_solution_getter_throws_in_public_mode_and_is_not_serialised | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheSave::test_the_save_carries_a_constant_stamp_and_resumes | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheStallBoard::test_hint_offers_and_reveals_nothing_where_no_line_decides | CONVERT
tests/test_player_public_mode.py::TestPublicMode_TheStallBoard::test_the_oracle_s_stalled_boards_drive_it | CONVERT
tests/test_player_public_mode.py::TestPublicMode_TheStallBoard::test_the_sentence_is_play_js_s_own | RETIRE-MOOT
tests/test_player_public_mode.py::TestPublicMode_TheSweep::test_every_control_is_driven_and_nothing_goes_wrong[chromium] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheSweep::test_the_census_and_the_sweep_agree_on_the_real_template | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheSweep::test_the_stall_board_has_a_disabled_hint_and_reveals_nothing | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheSweepOfTheRealFiles::test_the_sweep_drives_what_it_says_it_drives[chromium] | KEEP-LIVE
tests/test_player_public_mode.py::TestPublicMode_TheSweepOfTheRealFiles::test_the_sweep_is_clean[chromium] | KEEP-LIVE
tests/test_player_public_mode.py::test_the_sweep_puzzles_are_what_the_sweep_needs | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_a_plant_that_edits_a_copy_reds[admin.css] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_a_plant_that_edits_a_copy_reds[solver.js] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_a_plant_that_edits_a_copy_reds[solver_state.js] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_a_plant_that_edits_a_copy_reds[tokens.css] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_assembly_time_check_refuses_a_copy_that_is_not_identical[admin.css] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_assembly_time_check_refuses_a_copy_that_is_not_identical[solver.js] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_table_covers_exactly_the_four_files | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity::test_the_trees_copies_are_the_sources_byte_for_byte | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_every_control_every_gesture_the_solve_and_the_reload_are_clean[chromium] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheCard385SweepOnThisTree::test_the_sweep_is_not_vacuous_a_gutted_control_reds_it[chromium] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_the_cli_flags_are_all_or_nothing | RETIRE-MOOT
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_the_driver_end_to_end_equals_the_in_process_assembly | CONVERT
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_the_driver_refuses_one_of_the_two_flags_and_print_only_renders_nothing | CONVERT
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_the_driver_still_writes_no_file_and_names_no_published_path | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_the_drivers_default_command_line_is_unchanged | CONVERT
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_the_preview_differs_from_the_default_in_the_named_paths_only | RETIRE-MOOT
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_two_default_runs_are_byte_identical | CONVERT
tests/test_player_shared_ui_site.py::TestSharedUi_TheDefaultIsUnchanged::test_without_the_flag_the_tree_is_the_default_tree | RETIRE-MOOT
tests/test_player_shared_ui_site.py::TestSharedUi_TheDoorsKeepTheirShapes::test_the_library_lists_every_puzzle_and_a_tile_opens_the_admin_player | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheDoorsKeepTheirShapes::test_the_preview_server_serves_the_three_url_shapes | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheDoorsKeepTheirShapes::test_the_qr_landing_lists_the_book_and_a_tile_opens_the_admin_player | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheDoorsKeepTheirShapes::test_the_two_listing_pages_and_their_assets_are_the_default_trees_bytes | CONVERT
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_a_bad_address_shows_no_placeholder_header_chip_or_false_fallback | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_a_real_puzzle_plays_to_the_solved_banner | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_an_address_that_is_no_puzzle_says_so_and_draws_no_board[/play/0000000000-This puzzle is not on the site] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_an_address_that_is_no_puzzle_says_so_and_draws_no_board[/play/not-a-key-This address names no puzzle] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_hint_stays_on_and_says_why_where_no_line_decides | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_old_public_saves_are_not_read_and_the_visitor_starts_fresh | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_the_header_the_tab_and_the_banner_name_come_from_the_puzzle_file | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_the_line_the_usage_text_names_is_where_it_says_at_both_widths[1280-900] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_the_line_the_usage_text_names_is_where_it_says_at_both_widths[390-844] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_the_old_wording_is_false_on_a_phone_and_the_check_sees_it | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_the_page_links_no_stylesheet_beyond_the_admins_and_has_no_style_element | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_ThePageRuns::test_the_usage_line_is_true_for_the_public_player | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_a_bundle_whose_puzzle_carries_a_solution_key_is_served_without_it | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_a_plant_that_adds_a_solution_key_to_a_served_file_reds_the_key_check | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_ac392s_own_scan_of_the_tree_is_empty_and_finds_a_plant | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_every_puzzle_file_carries_exactly_the_served_key_set | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_no_served_file_contains_a_solution_string | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_the_copied_javascript_has_no_network_call[solver.js] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_the_copied_javascript_has_no_network_call[solver_state.js] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_the_scan_finds_a_planted_solution_in_every_encoding | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheServedTreeCarriesNoAnswer::test_the_site_marker_is_there | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_fragment_missing_a_hook_is_refused[<lambda>-no banner name hook] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_fragment_missing_a_hook_is_refused[<lambda>-no payload element] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_fragment_missing_a_hook_is_refused[<lambda>-no stage] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_fragment_missing_a_hook_is_refused[<lambda>-no tier hook] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_fragment_missing_a_hook_is_refused[<lambda>-the usage clause is gone] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_fragment_missing_a_hook_is_refused[<lambda>-the usage clause twice] | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_missing_bootstrap_file_is_an_error_before_the_tree_is_touched | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_a_refused_fragment_leaves_the_previous_tree_alone | KEEP-LIVE
tests/test_player_shared_ui_site.py::TestSharedUi_TheShellRefusesAFragmentItCannotTrust::test_the_real_fragment_builds_a_page | KEEP-LIVE
tests/test_player_shared_ui_site.py::test_the_two_boards_are_what_the_sweep_needs | KEEP-LIVE
tests/test_public_player.py::test_a_puzzle_file_the_schema_cannot_accept_is_refused_and_named | KEEP-LIVE
tests/test_public_player.py::test_a_save_or_a_puzzle_file_the_page_cannot_trust_is_refused | RETIRE-TWIN
tests/test_public_player.py::test_a_tier_outside_the_vocabulary_carries_no_cell_to_the_site | KEEP-LIVE
tests/test_public_player.py::test_a_touch_or_pen_drag_marks_only_while_region_is_armed | RETIRE-TWIN
tests/test_public_player.py::test_an_out_dir_that_is_not_a_previous_site_is_refused | KEEP-LIVE
tests/test_public_player.py::test_an_unknown_or_malformed_key_draws_no_board | RETIRE-TWIN
tests/test_public_player.py::test_every_fixture_puzzle_is_uniquely_solvable | KEEP-LIVE
tests/test_public_player.py::test_every_player_control_is_in_the_ec_050_walk | RETIRE-TWIN
tests/test_public_player.py::test_no_write_request_for_any_interaction | RETIRE-TWIN
tests/test_public_player.py::test_phone_viewport_is_playable | RETIRE-TWIN
tests/test_public_player.py::test_play_page_renders_and_marks | RETIRE-TWIN
tests/test_public_player.py::test_resume_is_local_and_the_page_writes_nowhere | RETIRE-TWIN
tests/test_public_player.py::test_served_tree_is_clean_of_answers | KEEP-LIVE
tests/test_public_player.py::test_solved_fires_on_clue_satisfaction_only | RETIRE-TWIN
tests/test_public_player.py::test_the_brush_region_and_touch_bindings_are_the_modules | RETIRE-TWIN
tests/test_public_player.py::test_the_capacity_bound_is_derived_and_can_fail | KEEP-LIVE
tests/test_public_player.py::test_the_clue_satisfaction_rule_agrees_with_the_solution_on_a_corpus | KEEP-LIVE
tests/test_public_player.py::test_the_command_line_says_what_it_dropped_and_what_it_narrowed | KEEP-LIVE
tests/test_public_player.py::test_the_empty_mark_is_a_dot_and_solving_is_revealed | RETIRE-TWIN
tests/test_public_player.py::test_the_index_and_book_files_are_rebuilt_and_never_copied | KEEP-LIVE
tests/test_public_player.py::test_the_key_recipe_matches_the_exporters | KEEP-LIVE
tests/test_public_player.py::test_the_page_carries_no_answer_and_no_third_party_asset | CONVERT
tests/test_public_player.py::test_the_picture_name_is_dropped_and_the_books_title_is_not | KEEP-LIVE
tests/test_public_player.py::test_the_player_assets_carry_no_colour_literal_and_only_defined_tokens | RETIRE-MOOT
tests/test_public_player.py::test_the_player_tree_is_static_and_adds_nothing_to_the_package | CONVERT
tests/test_public_player.py::test_the_registrys_check_refs_for_this_card_all_resolve | CONVERT
tests/test_public_player.py::test_the_runtime_dependency_baseline_is_untouched | CONVERT
tests/test_public_player.py::test_the_served_extents_are_recomputable_from_the_served_clues | KEEP-LIVE
tests/test_public_player.py::test_the_served_puzzle_files_are_rebuilt_not_copied | KEEP-LIVE
tests/test_public_player.py::test_the_served_tier_set_is_the_runtimes_tier_vocabulary | KEEP-LIVE
tests/test_public_player.py::test_the_stage_fits_the_board_on_a_wide_screen | RETIRE-MOOT
tests/test_public_player.py::test_the_state_module_and_tokens_are_byte_identical_copies | RETIRE-TWIN
tests/test_public_player.py::test_the_static_half_of_the_site_does_not_vary_with_the_puzzles | CONVERT
tests/test_public_player.py::test_the_tier_is_narrowed_to_the_vocabulary_or_dropped | KEEP-LIVE
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_a_declared_divergence_that_stops_diverging_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_a_fourth_divergence_in_the_compared_surface_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_every_declared_divergence_agrees_on_the_residue_it_leaves | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_every_declared_divergence_carries_a_control_of_its_own | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_every_declared_divergence_carries_a_reason | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_every_declared_divergence_is_a_fact_the_guard_measures | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_every_declared_divergence_names_the_difference_it_normalises_away | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_no_declared_divergence_has_an_unreadable_residue | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_real_drift_inside_a_declared_divergence_is_reported[reduced-motion.coverage::the panel stops quieting its sweep] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_real_drift_inside_a_declared_divergence_is_reported[reduced-motion.coverage::the public page stops quieting its sweep] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_real_drift_inside_a_declared_divergence_is_reported[sweep.animation.delay::the panel's sweep is three times slower] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_real_drift_inside_a_declared_divergence_is_reported[sweep.animation.delay::the public sweep is three times slower] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_real_drift_inside_a_declared_divergence_is_reported[sweep.selector::the panel flashes the empty cells] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_real_drift_inside_a_declared_divergence_is_reported[sweep.selector::the public page flashes the empty cells] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_the_compared_surface_is_not_empty_and_names_both_looks | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_the_compared_surface_parses_fact_by_fact | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_the_disagreements_are_exactly_the_declared_ones | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_ADivergenceMustBeDeclared::test_the_guard_reads_both_trees_and_not_one_of_them_twice | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_AReasonMustNameTheLayoutThatForcesIt::test_a_reason_that_is_only_a_preference_fails_it[roomier] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_AReasonMustNameTheLayoutThatForcesIt::test_a_reason_that_is_only_a_preference_fails_it[taste] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_AReasonMustNameTheLayoutThatForcesIt::test_every_declared_reason_names_a_forcing_layout_fact | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_BothPlayersSetTheSameWave::test_both_players_set_the_wave_to_the_same_expression | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_BothPlayersSetTheSameWave::test_each_player_sets_the_wave_exactly_once | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_BothPlayersSetTheSameWave::test_the_wave_is_the_cells_row_plus_its_column | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_declaration_is_a_real_divergence_with_a_reason_over_a_fact_the_extractor_makes | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_declared_divergence_that_stops_diverging_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_declared_value_that_drifts_inside_its_fact_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-circle-in-accent] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-circled-colour] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-circled-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-everything-circled] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-marker-renamed] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-reads-the-preview] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ring-fixed-height] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ring-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ring-square] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ring-takes-the-pointer] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ring-transform] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ring-transition] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ring-z-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-circle-in-accent] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-circled-colour] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-circled-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-everything-circled] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-marker-renamed] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-reads-the-preview] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ring-fixed-height] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ring-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ring-square] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ring-takes-the-pointer] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ring-transform] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ring-transition] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ring-z-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_the_declared_ring_sizes_are_the_stated_ratio | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_the_disagreements_are_exactly_the_declared_pairs | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook::test_the_facts_that_agree_are_enumerated_and_not_empty | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_declared_divergence_that_stops_diverging_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[admin-a-gutter-hit-now-moves] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[admin-column-clue-by-the-wrong-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[admin-marker-renamed] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[admin-pen-exempt-not-touch] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[admin-pointerdown-no-longer-moves] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[admin-touch-no-longer-exempt] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[public-a-gutter-hit-now-moves] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[public-marker-renamed] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[public-pen-exempt-not-touch] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[public-pointermove-no-longer-moves] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[public-row-clue-by-the-wrong-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_one_sided_change_to_a_decision_is_reported[public-touch-no-longer-exempt] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_a_second_listener_for_one_event_is_refused_and_not_read_past | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_the_crosshair_sheet_rules_agree_and_the_tint_is_a_declared_difference | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_the_declared_values_are_the_stated_difference | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_the_disagreements_are_exactly_the_declared_ones | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_the_facts_are_not_vacuous | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_the_four_decisions_are_compared_facts_and_agree | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions::test_the_public_page_has_no_redraw_to_forget_after | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame::test_reformatting_a_dot_rule_moves_no_declaration | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame::test_the_admin_sheet_declares_the_seven_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame::test_the_comparison_is_over_declarations_and_not_over_rule_text | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame::test_the_public_sheet_declares_the_seven_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame::test_the_rule_is_declared_once_in_each_sheet | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame::test_the_two_declaration_sets_are_equal | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_declaration_is_a_real_divergence_with_a_reason_over_a_fact_the_extractor_makes | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_declared_divergence_that_stops_diverging_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_declared_value_that_drifts_inside_its_fact_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-clue-tint-in-accent] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-generic-sentence] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-hinted-keyframe] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-line-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-line-transform] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-line-transition] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-line-z-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-marker-renamed] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-point-sentence] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[admin-reveal-ignores-the-state] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-clue-tint-in-accent] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-generic-sentence] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-hint-animations-not-quieted] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-hinted-keyframe] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-line-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-line-transform] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-line-transition] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-line-z-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-marker-renamed] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-point-sentence] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_a_one_sided_change_to_a_held_fact_is_reported[public-reveal-ignores-the-state] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_the_disagreements_are_exactly_the_declared_pairs | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_the_exhausted_sentence_figures_in_the_reason_are_the_sentences | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_the_facts_that_agree_are_enumerated_and_each_is_a_real_value_on_both_sides | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheHintIsTheSameLookAndTheSameWords::test_the_sentences_the_extractor_reads_are_the_sentences | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_glyph_deleted_from_this_page_is_a_failure_and_not_an_absence[cell] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_glyph_deleted_from_this_page_is_a_failure_and_not_an_absence[swatch] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_one_sided_change_to_the_maybe_mark_is_reported[the admin cell glyph is drawn half the size] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_one_sided_change_to_the_maybe_mark_is_reported[the admin swatch glyph draws an exclamation mark] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_one_sided_change_to_the_maybe_mark_is_reported[the public cell glyph loses the accent token] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_one_sided_change_to_the_maybe_mark_is_reported[the public swatch glyph stops centring the mark] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_admin_sheet_declares_the_cell_glyphs_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_admin_sheet_declares_the_swatch_glyphs_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_cell_glyph_is_declared_once_in_each_sheet | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_mark_both_glyphs_draw_is_a_question_mark_in_the_accent_token | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_maybe_mark_is_a_fact_this_guard_compares | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_numeral_floor_the_cell_glyph_reads_agrees_in_both_sheets | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_public_sheet_declares_the_cell_glyphs_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_public_sheet_declares_the_swatch_glyphs_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_swatch_glyph_is_declared_once_in_each_sheet | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_two_cell_glyph_declaration_sets_are_equal | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_two_swatch_glyph_declaration_sets_are_equal | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_a_change_to_a_sibling_mark_moves_the_census[a sibling mark starts diverging (the admin's Clear swatch is tinted)] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_a_change_to_a_sibling_mark_moves_the_census[a sibling mark starts diverging (the public cell loses its ink)] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_a_fifth_cell_state_is_enumerated_rather_than_left_outside_the_census | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_census_fact_is_compared_routed_or_agreeing | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_compared_mark_names_a_fact_the_surface_really_carries | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_routed_finding_carries_a_reason_and_a_measured_figure | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_no_mark_is_both_compared_and_routed | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_the_census_is_derived_from_the_module_both_players_import | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_the_census_is_not_vacuous | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_declaration_is_a_real_divergence_with_a_reason_over_a_fact_the_extractor_makes | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_declared_divergence_that_stops_diverging_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_declared_value_that_drifts_inside_its_fact_is_reported | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-abandon-label] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-cell-background] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-cell-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-cell-transition] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-cell-z-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-checkpoint-save-dropped] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-filled-ink-colour] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-hinted-probe-colour] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-ink-mix] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-keep-label] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-marker-value] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-note-words] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-outline-solid] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[admin-probe-mix] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-abandon-label] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-cell-background] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-cell-opacity] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-cell-transition] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-cell-z-index] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-checkpoint-save-dropped] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-filled-ink-colour] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-hinted-probe-colour] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-ink-mix] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-keep-label] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-marker-value] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-note-words] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-outline-solid] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_one_sided_change_to_a_held_fact_is_reported[public-probe-mix] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_a_probe_rule_with_a_property_the_extractor_was_not_told_about_is_seen | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_the_disagreements_are_exactly_the_declared_pairs | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_the_facts_that_agree_are_enumerated_and_each_is_a_real_value_on_both_sides | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_the_figures_in_the_reasons_are_the_tokens | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheProbeIsTheSameLook::test_the_look_is_the_same_declaration_for_declaration | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_neither_keyframes_body_is_empty_in_either_sheet | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_the_banner_keyframes_agree | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_the_flash_keyframes_agree | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_the_per_cell_step_agrees | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_the_sweep_duration_formula_agrees | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_the_sweep_easing_agrees | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_the_sweep_plays_the_same_keyframes_in_both | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep::test_the_sweep_rule_is_found_once_in_each_sheet | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_a_one_sided_change_to_the_swatch_dot_is_reported[the admin swatch dot is drawn as a square] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_a_one_sided_change_to_the_swatch_dot_is_reported[the public swatch dot is drawn in the board's ink] | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_a_swatch_dot_deleted_from_this_page_is_a_failure_and_not_an_absence | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_admin_sheet_declares_the_swatch_dots_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_brush_button_previews_the_mark_the_board_draws | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_four_brush_buttons_are_mutually_distinguishable | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_mark_both_swatches_draw_is_a_round_dot_in_the_secondary_ink | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_public_sheet_declares_the_swatch_dots_properties | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_swatch_dot_is_declared_once_in_each_sheet | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_swatch_is_the_containing_block_both_marks_resolve_against | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_two_swatch_dot_declaration_sets_are_equal | RETIRE-MOOT
tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_white_mark_is_a_fact_this_guard_compares | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_crossed_and_circled_clue_box_shows_its_tint_and_its_ring | LOST
tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_tint_that_can_hide_the_ring_is_caught[lower-half-clipped] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_tint_that_can_hide_the_ring_is_caught[right-half-clipped] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_tint_that_can_hide_the_ring_is_caught[tint-clears-the-ring] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_tint_that_can_hide_the_ring_is_caught[tint-hides-the-number] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_tint_that_can_hide_the_ring_is_caught[tint-is-an-overlay-above-the-ring] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle::test_a_tint_that_can_hide_the_ring_is_caught[upper-half-clipped] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed::test_a_ring_not_drawn_where_it_says_is_caught[ring-faded-to-nothing] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed::test_a_ring_not_drawn_where_it_says_is_caught[ring-not-drawn] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed::test_a_ring_not_drawn_where_it_says_is_caught[ring-shifted-down] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed::test_a_ring_not_drawn_where_it_says_is_caught[ring-shifted-right] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_a_solved_check_made_from_the_circle_set_declares_victory_on_the_wrong_board[banner-from-circles-plant0] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_a_solved_check_made_from_the_circle_set_declares_victory_on_the_wrong_board[rule-from-circles-plant1] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_every_number_circled_and_the_board_is_not_solved[extra-cell-0-4] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_every_number_circled_and_the_board_is_not_solved[extra-cell-0-7] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_every_number_circled_and_the_board_is_not_solved[extra-cell-1-0] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_every_number_circled_and_the_board_is_not_solved[extra-cell-4-0] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_every_number_circled_and_the_board_is_not_solved[extra-cell-6-0] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_no_existing_fixture_has_the_extra_cell_board[cycle2-144] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_no_existing_fixture_has_the_extra_cell_board[max] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_no_existing_fixture_has_the_extra_cell_board[min] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_no_existing_fixture_has_the_extra_cell_board[oblong] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck::test_the_constructed_board_is_what_the_card_says | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_NoAnswerAndNoRequest::test_every_interaction_issues_nothing_beyond_the_load | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_NoAnswerAndNoRequest::test_the_circle_code_adds_no_external_reference | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_NoAnswerAndNoRequest::test_the_page_holds_no_solution_field_and_the_circles_add_no_attribute | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled::test_a_ring_past_a_declared_bound_is_caught[ring-in-px-  --player-circle: 1.05em;-  --player-circle: 15px;-scale] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled::test_a_ring_past_a_declared_bound_is_caught[ring-too-tall-  --player-circle: 1.05em;-  --player-circle: 1.09em;-gap] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled::test_the_rings_are_in_place_and_clear_of_each_other_at_the_maximum[desktop-unscrolled] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled::test_the_rings_are_in_place_and_clear_of_each_other_at_the_maximum[phone-a-quarter-into-the-gutters] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled::test_the_rings_are_in_place_and_clear_of_each_other_at_the_maximum[phone-three-quarters-into-the-gutters] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheInPlaceBandHasADeclaredResidue::test_the_in_place_residue_is_declared_and_a_shift_just_past_it_is_caught[a-1_5px-shift-just-past-it-is-caught] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheInPlaceBandHasADeclaredResidue::test_the_in_place_residue_is_declared_and_a_shift_just_past_it_is_caught[a-1px-shift-is-the-declared-residue] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_a_blank_board_circles_nothing | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_a_fully_marked_solution_circles_every_number[circles] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_a_fully_marked_solution_circles_every_number[cycle2-144] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_a_fully_marked_solution_circles_every_number[max] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_a_fully_marked_solution_circles_every_number[min] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_a_fully_marked_solution_circles_every_number[oblong] | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_a_number_repeated_in_a_clue_circles_one_at_a_time | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_the_blank_line_clue_is_circled_only_when_every_cell_is_white | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_the_fixtures_are_uniquely_solvable | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers::test_the_numbers_the_marks_account_for_are_circled_and_the_rest_are_not | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-computed-index-by-literal] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-computed-member-by-string] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-getAttribute-read] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-global-helper] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-length-property] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-listener] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-reference-to-the-history] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-second-circled-rule-in-another-function] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-second-toggler-in-a-template] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-second-toggler-in-single-quotes] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[a-string-naming-state] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[an-assignment] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[an-offset-index] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[an-operator-and-a-condition] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[collector-indexes-by-a-string] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[collector-reads-the-text] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[indexes-axis-after-line] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[indexes-k-then-line] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[indexes-line-twice] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused[the-comma-operator] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_solved_check_that_reaches_for_the_circles_is_refused[a-circle-global] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_solved_check_that_reaches_for_the_circles_is_refused[a-reference-to-the-painter] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_a_solved_check_that_reaches_for_the_circles_is_refused[the-module-call] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_circle_code_is_not_vacuously_clean | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_circle_code_registers_no_listener_and_the_file_adds_none | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_circle_code_says_nothing_but_the_modules_return_value | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_import_and_the_hook_are_held_too[a-second-painter-is-defined] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_import_and_the_hook_are_held_too[the-hook-is-gone] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_import_and_the_hook_are_held_too[the-hook-reads-the-preview] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_import_and_the_hook_are_held_too[the-import-is-gone] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_page_set_equals_the_modules_across_a_seeded_corpus | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules::test_the_solved_check_is_still_the_clue_rule_and_its_warning_stands | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_drag_in_progress_leaves_the_circles_on_the_record | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[first-line-skipped] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[last-line-skipped] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[left-after-reset] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[preview-not-record] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[repeat-by-value] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[survives-undo] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[toggle-without-force] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean[wrong-axis] | RETIRE-MOOT
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_every_step_of_a_stroke_undo_redo_reset_walk_equals_the_module | RETIRE-TWIN
tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset::test_the_edges_a_repeat_and_a_blank_clue_equal_the_module | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision::test_a_drag_that_ends_off_the_stage_with_a_mouse_clears_the_cross | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision::test_a_mouse_drag_is_crossed_at_every_cell_it_visits_and_still_marks | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision::test_a_pen_drag_follows_the_pen_across_the_board | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision::test_a_press_alone_crosses_the_cell_before_any_move | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision::test_a_touch_drag_leaves_the_cross_on_the_last_cell_it_reached | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_a_clue_box_and_the_corner_keep_the_crosshair_where_it_was | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_hovering_a_cell_marks_its_row_its_column_and_both_clues[bottom-left] | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_hovering_a_cell_marks_its_row_its_column_and_both_clues[bottom-right] | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_hovering_a_cell_marks_its_row_its_column_and_both_clues[inside] | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_hovering_a_cell_marks_its_row_its_column_and_both_clues[top-left] | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_hovering_a_cell_marks_its_row_its_column_and_both_clues[top-right] | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_leaving_the_stage_clears_every_marker | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross::test_the_crosshair_follows_the_pointer_and_only_one_cross_exists | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverRecordsNoStroke::test_hovering_makes_no_request | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverRecordsNoStroke::test_pointer_movement_across_the_whole_board_changes_nothing_but_the_marker | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverRecordsNoStroke::test_the_save_and_the_history_survive_a_reload_untouched_by_hovering | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_crosshair_painted_before_a_zoom_survives_it_whole | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_finger_counts_toward_a_pinch_that_a_pen_began | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_lost_pen_pointerup_does_not_stick_a_pinch | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_pen_counts_toward_a_pinch | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_pinch_marks_nothing_and_records_no_stroke | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_pinch_neither_starts_a_crosshair_nor_leaves_one | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_pinch_takes_off_a_crosshair_an_earlier_tap_left | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_a_third_finger_neither_paints_nor_follows | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_crossing_resumes_after_a_pinch | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_after_the_zoom_moved_the_scroll_itself | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_at_the_zoom_maximum_at_any_stage_scroll[desktop-0.0] | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_at_the_zoom_maximum_at_any_stage_scroll[phone-0.5] | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_at_the_zoom_maximum_at_any_stage_scroll[phone-0.75] | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_at_the_zoom_maximum_at_any_stage_scroll[phone-1.0] | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled::test_it_lands_on_the_cell_when_the_page_itself_has_scrolled | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[UNKNOWN] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[attributes] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[board] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[cells] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[children] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[classList-contains] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[className] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[clue-numeral] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[clue-text] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[computed-member] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[data-state-selector] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[dataset-state] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[fetch] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[getAttribute-concatenated] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[getAttributeNames] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[history] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[isClueSolved] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[localStorage] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[nextElementSibling] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[payload] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[publicPlayer] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[shown] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[strokeOf] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_planted_reference_is_reported[unlisted-data-attribute] | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_a_reference_in_a_shared_helper_is_reported_too | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_it_references_no_cell_state_history_clue_data_or_payload_field | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_no_network_request_and_no_external_reference_is_added | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard::test_the_crosshair_is_defined_and_wired_to_the_stage_alone | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_TheLookIsTokensOnly::test_every_crosshair_value_is_a_token | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_TheLookIsTokensOnly::test_the_crosshair_only_ever_sets_a_background | RETIRE-MOOT
tests/test_public_player_crosshair.py::TestPublicCrosshair_TheTintStaysApart::test_a_crossed_cell_is_not_the_colour_of_a_maybe_cell | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_TheTintStaysApart::test_a_crossed_filled_cell_keeps_its_dark_ground | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_a_mouse_leave_still_clears_what_a_touch_leave_does_not | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_a_remembered_position_with_nothing_painted_repaints | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_a_second_tap_moves_the_cross_and_leaves_only_one | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_a_touch_crosshair_stays_after_the_finger_lifts[touchCancel] | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_a_touch_crosshair_stays_after_the_finger_lifts[touchEnd] | RETIRE-TWIN
tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_full_or_none_holds_at_every_step_of_a_mixed_session | LOST
tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted::test_the_rules_do_not_depend_on_hover | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_AContradictingLineIsSkipped::test_a_board_where_the_only_deciding_line_is_contradicted_is_the_exhausted_state | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AContradictingLineIsSkipped::test_a_line_the_marks_contradict_supplies_no_hint_and_the_others_still_do | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AHintIsOneUndoStep::test_a_hint_moves_the_circles_like_any_mark_and_leaves_no_crosshair_behind | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AHintIsOneUndoStep::test_a_save_whose_hint_flag_is_not_true_is_refused[false] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AHintIsOneUndoStep::test_a_save_whose_hint_flag_is_not_true_is_refused[null] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AHintIsOneUndoStep::test_a_save_whose_hint_flag_is_not_true_is_refused[number] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AHintIsOneUndoStep::test_a_save_whose_hint_flag_is_not_true_is_refused[string] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AHintIsOneUndoStep::test_the_hint_survives_a_reload_as_a_hint | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_AHintIsOneUndoStep::test_undo_returns_the_cell_to_undecided_and_the_count_falls_and_redo_restores_both | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-black-cell-may-be-left-blank-backward] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-black-cell-may-be-left-blank-forward] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-column-wins-a-tie] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-contradicted-line-forces-a-cell] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-forced-cell-reads-as-undecided] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-full-board-can-be-hinted] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-hint-also-writes-a-second-storage-key] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-noop-undo-resets-the-ladder] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-null-line-decides-nothing-else-does-either] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-press-does-not-climb] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-press-mid-drag-is-honoured] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-run-may-touch-the-next-black-cell] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-save-forgets-the-hint-flag] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-save-with-any-flag-is-accepted] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[first-column-skipped] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[first-line-skipped] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[last-column-skipped] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[last-line-skipped] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[rung-one-names-the-wrong-axis] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[rung-three-ignores-the-derived-state] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[rung-three-records-a-plain-stroke] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-control-is-never-disabled] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-count-is-a-variable-not-the-history] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-counter-is-never-written] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-counter-reads-zero-after-reset] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-deduction-reads-the-displayed-board] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-exhausted-state-reveals-a-cell] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-hinted-cell-is-never-outlined] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-line-is-never-lit] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-old-line-is-never-unlit] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-old-outline-is-never-removed] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-reveal-never-happens] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-rung-does-not-reset-on-a-change] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[undo-does-not-remove-a-hint] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_EachPlantFiresTheScenarioItIsAbout::test_there_are_plants_for_every_edge_the_card_names | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ExhaustedRevealsNothing::test_a_board_no_line_decides_says_so_at_every_rung_and_reveals_no_cell | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_ExhaustedRevealsNothing::test_the_page_never_holds_back_a_cell_to_reveal_later | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungThreeDerivesTheCell::test_rung_three_marks_the_cell_lineforced_gives_it_as_one_hint_stroke[blank] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungThreeDerivesTheCell::test_rung_three_marks_the_cell_lineforced_gives_it_as_one_hint_stroke[four-rows-marked] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungThreeDerivesTheCell::test_rung_three_marks_the_cell_lineforced_gives_it_as_one_hint_stroke[maybe-cells] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungThreeDerivesTheCell::test_the_derived_cell_is_what_an_independent_enumeration_finds[blank] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungThreeDerivesTheCell::test_the_derived_cell_is_what_an_independent_enumeration_finds[four-rows-marked] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungThreeDerivesTheCell::test_the_derived_cell_is_what_an_independent_enumeration_finds[maybe-cells] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_only_one_line_is_lit_after_a_change_and_a_second_press | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_one_lights_the_line_the_deduction_comes_from_and_says_so[blank] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_one_lights_the_line_the_deduction_comes_from_and_says_so[four-rows-marked] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_one_lights_the_line_the_deduction_comes_from_and_says_so[maybe-cells] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_one_lights_the_line_the_deduction_comes_from_and_says_so[row-complete] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_two_adds_the_reason_hintreason_gives_and_changes_nothing_on_the_board[blank] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_two_adds_the_reason_hintreason_gives_and_changes_nothing_on_the_board[four-rows-marked] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_two_adds_the_reason_hintreason_gives_and_changes_nothing_on_the_board[maybe-cells] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_rung_two_adds_the_reason_hintreason_gives_and_changes_nothing_on_the_board[row-complete] | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_the_reason_sentences_are_exactly_the_modules_reasons | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain::test_the_three_boards_between_them_give_every_reason_the_module_has | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_StayLegibleAndInPlaceWhenZoomedAndScrolled::test_the_lit_line_and_the_outlined_cell_survive_zoom_and_scroll | LOST
tests/test_public_player_hint.py::TestPublicHint_TheAssetGainsNothing::test_a_page_that_stashes_the_solution_is_caught | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheAssetGainsNothing::test_across_a_seeded_corpus_no_hint_leaves_a_grid_behind | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheAssetGainsNothing::test_every_served_puzzle_file_carries_exactly_the_five_fields | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheAssetGainsNothing::test_the_hint_adds_no_request_and_the_only_one_is_the_get_of_its_own_puzzle | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheAssetGainsNothing::test_the_page_holds_one_global_and_no_solution_grid_before_and_after_hints | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheAssetGainsNothing::test_the_scanner_also_refuses_the_stash_in_source | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_a_rung_two_sentence_is_whole_and_in_the_viewport_at_every_width[320] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_a_rung_two_sentence_is_whole_and_in_the_viewport_at_every_width[desktop] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_a_rung_two_sentence_is_whole_and_in_the_viewport_at_every_width[landscape] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_a_rung_two_sentence_is_whole_and_in_the_viewport_at_every_width[phone] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_a_toolbar_button_added_or_the_control_moved_into_it_is_refused | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_the_control_is_reachable_and_legible_at_the_zoom_maximum_and_a_scrolled_offset | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_the_control_is_under_the_board_44px_and_the_toolbar_is_what_it_was | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheControlIsOutsideTheToolbar::test_the_markup_agrees_before_a_script_runs | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards::test_a_clean_board_never_gets_a_hint_that_disagrees_with_the_solution | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards::test_the_corpus_is_big_and_has_every_kind_of_board | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards::test_the_page_agrees_with_the_module_and_the_enumeration | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards::test_where_a_mark_is_wrong_the_two_differ_and_only_there | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_a_page_with_a_check_button_makes_the_claim_false | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_each_part_of_the_claim_is_individually_load_bearing[missing fallback is not stated] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_each_part_of_the_claim_is_individually_load_bearing[named as needing the answer] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_each_part_of_the_claim_is_individually_load_bearing[not named as deriving] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_each_part_of_the_claim_is_individually_load_bearing[not named as not needing the answer] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_each_retracted_phrase_is_individually_refused[hintcell-takes-solution] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_each_retracted_phrase_is_individually_refused[needs-the-answer] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_each_retracted_phrase_is_individually_refused[no-hints] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_the_behaviour_the_header_names_is_the_behaviour | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_the_header_states_what_holds_and_not_what_was_false | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheHeaderClaimIsTrue::test_the_old_header_is_refused | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheLadderIsTheModules::test_a_hint_that_is_pressed_mid_gesture_does_nothing | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheLadderIsTheModules::test_rung_three_is_the_reveal_and_the_others_record_nothing | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheLadderIsTheModules::test_the_rung_after_every_step_is_what_nextrung_returns_for_the_event_that_occurred | RETIRE-TWIN
tests/test_public_player_hint.py::TestPublicHint_TheListenerCensus::test_a_hint_button_without_its_listener_or_a_listener_without_its_button_reds_it | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheListenerCensus::test_a_sixth_listener_reds_it | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheListenerCensus::test_the_hint_is_one_click_listener_and_the_census_balances | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[contradiction] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[corpus] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[edges] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[exhausted] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[full] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[hinted] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[ladder] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[lit] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[mid-drag] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[noop-undo] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[reset] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[save] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[undo] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_every_scenario_passes_and_none_is_skipped | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheScenariosAreGreenOnTheRealPage::test_the_served_canary_mechanism_serves_an_unchanged_file | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheSentenceBelowTheBoardKeepsTheZoomModulesPremise::test_a_sentence_far_longer_than_any_the_page_says_goes_past_the_bound | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheSentenceBelowTheBoardKeepsTheZoomModulesPremise::test_the_usage_paragraph_comes_back_with_the_next_change | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheSentenceBelowTheBoardKeepsTheZoomModulesPremise::test_with_a_sentence_showing_the_space_below_stays_smaller_than_the_top | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_TheSentenceBelowTheBoardKeepsTheZoomModulesPremise::test_without_the_swap_the_premise_fails_on_a_measured_number_of_viewports | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_highlight_that_can_hide_the_ring_is_caught[number-hidden] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_highlight_that_can_hide_the_ring_is_caught[right-half-clipped] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_highlight_that_can_hide_the_ring_is_caught[ring-cleared] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_highlight_that_can_hide_the_ring_is_caught[tint-is-an-overlay-above-the-ring] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_hinted_crossed_and_circled_box_shows_all_three | LOST
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_hinted_line_keeps_a_filled_a_white_and_a_blank_cell_apart | LOST
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_maybe_cell_on_a_lit_line_keeps_its_glyph_and_the_tint_is_not_the_maybe_ground | LOST
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_tint_that_is_not_distinct_is_caught[the-blend-is-the-crosshairs-.player-clue.is-hint-line.is-crossed { background: var(--player-cross); }] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_tint_that_is_not_distinct_is_caught[the-blend-is-the-hint-.player-clue.is-hint-line.is-crossed { background: var(--player-hint-line); }] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_tint_that_is_not_distinct_is_caught[the-hint-tint-is-nearly-the-crosshairs-.player-stage { --player-hint-line: color-mix(in srgb, var(--player-cross) 97%, var(--color-accent-tint)); }] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_tint_that_is_not_distinct_is_caught[the-hint-tint-is-the-crosshairs-.player-stage { --player-hint-line: var(--player-cross); }] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_a_tint_that_is_not_distinct_is_caught[the-hint-tint-is-the-panels-own-and-6-levels-from-the-crosshair-.player-stage { --player-hint-line: var(--color-accent-tint); }] | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_every_value_of_the_hint_rules_is_a_token_or_a_token_only_expression | RETIRE-MOOT
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_the_four_states_of_a_clue_box_are_pairwise_distinguishable | LOST
tests/test_public_player_hint.py::TestPublicHint_ThreeMarksCoexist::test_the_measured_distances_are_the_ones_the_floor_was_set_from | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-closure-const-memo] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-comma-operator-in-the-painter] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-computed-member-from-strings] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-condition-in-the-painter] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-dynamic-import] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-fetch-by-name] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-global-by-identifier] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-module-level-const-stash] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-new-global] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-new-page-variable] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-number-in-an-index] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-property-read] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-regex-literal-holding-a-backtick] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-regex-literal-holding-a-quote] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-second-ask-of-the-deduction] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-second-rule-in-the-painter] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[a-template-index] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[an-alias-const] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[an-import-that-reads-the-solution] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[an-old-name-declared-again-in-a-closure] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[an-operator-the-vocabulary-lacks] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[an-unscanned-arrow-const-called-from-the-click-handler] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[an-unscanned-function-called-from-the-click-handler] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[loose-inequality] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[optional-chaining] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[the-comma-operator-in-an-index] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[the-comma-operator] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[the-function-constructor] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[the-marker-is-given-a-constant] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[the-painter-indexes-by-the-wrong-property] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[the-painter-reads-another-index] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[the-word-in-a-string] | RETIRE-MOOT
tests/test_public_player_hint.py::test_a_bypass_is_refused_beside_its_clean_control[this] | RETIRE-MOOT
tests/test_public_player_hint.py::test_every_neq_this_card_added_has_a_plant_that_fails_it | RETIRE-MOOT
tests/test_public_player_hint.py::test_the_contradiction_fixture_contradicts_a_line_and_another_still_decides | RETIRE-MOOT
tests/test_public_player_hint.py::test_the_declaration_census_is_the_whole_file_and_is_not_vacuous | RETIRE-MOOT
tests/test_public_player_hint.py::test_the_exhausted_fixture_is_what_the_card_needs | RETIRE-MOOT
tests/test_public_player_hint.py::test_the_mixed_fixture_is_uniquely_solvable_and_has_a_forced_first_cell | RETIRE-MOOT
tests/test_public_player_hint.py::test_the_neq_census_notices_a_comparison_with_no_plant | RETIRE-MOOT
tests/test_public_player_hint.py::test_the_regex_lexer_finds_the_one_literal_and_nothing_in_strings | RETIRE-MOOT
tests/test_public_player_hint.py::test_the_scanner_finds_the_hint_code_and_passes_the_real_file | RETIRE-MOOT
tests/test_public_player_hint.py::test_there_are_at_least_eight_bypasses_and_every_vocabulary_has_one | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_AReloadRestoresMaybeMarks::test_maybe_marks_come_back_after_a_reload | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_AReloadRestoresMaybeMarks::test_the_fetched_puzzle_file_still_carries_only_what_the_page_reads | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_AReloadRestoresMaybeMarks::test_the_save_gains_no_field_for_the_fourth_brush | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_FourToolsInTheAdminsOrder::test_each_tool_is_a_radio_built_like_its_siblings | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_FourToolsInTheAdminsOrder::test_the_order_check_reports_a_reordered_page | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_FourToolsInTheAdminsOrder::test_the_public_page_offers_the_admin_menus_four_tools_in_its_order | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_FourToolsInTheAdminsOrder::test_the_tools_constant_is_the_markups_order | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_OneToolIsCheckedAtATime::test_a_seeded_walk_over_the_tools_never_checks_two | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_OneToolIsCheckedAtATime::test_choosing_each_tool_leaves_exactly_that_one_checked | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_TheBrushMarksACell::test_a_drag_with_the_maybe_brush_marks_its_whole_line | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_TheBrushMarksACell::test_choosing_maybe_and_clicking_marks_the_cell_and_records_one_stroke | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_TheBrushMarksACell::test_the_brushs_click_sequence_is_the_modules | RETIRE-TWIN
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_maybe_cell_look_is_one_rule_declaring_one_background | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_reading_reports_each_planted_defect[a second cell rule] | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_reading_reports_each_planted_defect[an extra cell rule, as an ::after] | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_reading_reports_each_planted_defect[the cell glyph deleted] | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_reading_reports_each_planted_defect[the swatch given another value] | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_reading_reports_each_planted_defect[the swatch glyph deleted] | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_reading_reports_each_planted_defect[the swatch glyph draws another mark] | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_reading_reports_each_planted_defect[the swatch rule deleted] | RETIRE-MOOT
tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce::test_the_swatch_previews_the_cell_with_the_cells_own_value | RETIRE-MOOT
tests/test_public_player_pages.py::test_a_book_the_schema_cannot_accept_is_refused_and_named | KEEP-LIVE
tests/test_public_player_pages.py::test_a_book_with_no_resolvable_puzzle_is_still_served_empty | KEEP-LIVE
tests/test_public_player_pages.py::test_a_listing_carries_only_values_already_on_a_puzzle_file | KEEP-LIVE
tests/test_public_player_pages.py::test_a_listing_never_names_a_puzzle_the_site_does_not_serve | KEEP-LIVE
tests/test_public_player_pages.py::test_a_listing_the_page_cannot_trust_is_refused | KEEP-LIVE
tests/test_public_player_pages.py::test_a_tile_is_a_thumb_target_and_wears_its_tier | KEEP-LIVE
tests/test_public_player_pages.py::test_an_empty_book_renders_its_empty_note | KEEP-LIVE
tests/test_public_player_pages.py::test_assembled_site_is_self_contained | KEEP-LIVE
tests/test_public_player_pages.py::test_book_landing_lists_and_links | CONVERT
tests/test_public_player_pages.py::test_both_waits_in_open_pages_carry_the_explicit_timeout | KEEP-LIVE
tests/test_public_player_pages.py::test_filtering_is_announced_in_a_live_region | KEEP-LIVE
tests/test_public_player_pages.py::test_library_filters_the_index | KEEP-LIVE
tests/test_public_player_pages.py::test_no_homegrown_tracking | KEEP-LIVE
tests/test_public_player_pages.py::test_no_puzzle_title_reaches_either_listing | KEEP-LIVE
tests/test_public_player_pages.py::test_pages_work_with_analytics_blocked | CONVERT
tests/test_public_player_pages.py::test_the_assembly_helper_drives_the_assembler_and_writes_nothing_itself | KEEP-LIVE
tests/test_public_player_pages.py::test_the_book_landing_shows_the_books_title | KEEP-LIVE
tests/test_public_player_pages.py::test_the_book_title_exemption_is_scoped_and_its_cost_is_measured | KEEP-LIVE
tests/test_public_player_pages.py::test_the_counting_snippet_goes_in_once_and_refuses_anything_else | KEEP-LIVE
tests/test_public_player_pages.py::test_the_deploy_page_is_the_only_place_that_holds_an_endpoint | KEEP-LIVE
tests/test_public_player_pages.py::test_the_listing_capacity_is_partitioned_and_can_fail | KEEP-LIVE
tests/test_public_player_pages.py::test_the_listing_pages_carry_no_colour_literal_and_only_defined_tokens | KEEP-LIVE
tests/test_public_player_pages.py::test_the_listing_pages_only_get_and_write_nothing | KEEP-LIVE
tests/test_public_player_pages.py::test_the_pages_tier_vocabulary_is_the_runtimes | KEEP-LIVE
tests/test_public_player_pages.py::test_the_public_tile_is_registered_in_the_design_inventory | KEEP-LIVE
tests/test_public_player_pages.py::test_the_qr_url_shapes_here_are_the_shipped_routes | KEEP-LIVE
tests/test_public_player_pages.py::test_the_registrys_refs_for_this_file_resolve_or_are_card_285s | KEEP-LIVE
tests/test_public_player_pages.py::test_the_served_index_is_key_sorted | KEEP-LIVE
tests/test_public_player_pages.py::test_the_size_bands_partition_the_supported_extent | KEEP-LIVE
tests/test_public_player_pages.py::test_the_two_doors_are_routed_by_the_shipped_config | KEEP-LIVE
tests/test_public_player_pages.py::test_the_two_pages_add_nothing_to_the_package_and_no_toolchain | KEEP-LIVE
tests/test_public_player_pages.py::test_two_assemble_runs_are_byte_identical | KEEP-LIVE
tests/test_public_player_pages.py::test_unknown_slug_lands_softly | KEEP-LIVE
tests/test_public_player_probe.py::TestPublicProbe_APinchNeitherOpensNorChangesAProbe::test_a_two_finger_pinch_leaves_the_probe_alone | LOST
tests/test_public_player_probe.py::TestPublicProbe_ARedoStackIsNotSavedWhileOpen::test_a_save_that_does_hold_the_redo_stack_is_caught | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_ARedoStackIsNotSavedWhileOpen::test_undoing_past_the_checkpoint_inside_a_probe_changes_what_a_reload_resumes_at | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_ARegionDragIsOneProbeStroke::test_a_save_that_holds_the_drag_is_caught_beside_its_clean_control | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_ARegionDragIsOneProbeStroke::test_the_save_is_the_checkpoint_save_abandon_restores_and_no_marker_is_left | LOST
tests/test_public_player_probe.py::TestPublicProbe_AReloadAbandonsTheOpenProbe::test_the_page_says_so_in_one_line_where_the_controls_are | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_AReloadAbandonsTheOpenProbe::test_the_save_is_the_save_as_of_the_checkpoint | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_AReloadAbandonsTheOpenProbe::test_the_save_never_holds_a_probe_stroke_over_a_seeded_corpus | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_AbandonRestoresTheCheckpointBoard::test_over_a_seeded_corpus_the_board_is_the_checkpoint_board_cell_for_cell | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_AbandonRestoresTheCheckpointBoard::test_the_scenario_is_green | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_CirclesSeeProbeMarksAsMarks::test_the_circle_set_is_circledclues_of_the_recorded_board_probe_strokes_included | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_CommitKeepsCellsAndDropsTheLook::test_over_a_seeded_corpus_no_cell_changes_and_no_marker_remains | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_CommitKeepsCellsAndDropsTheLook::test_the_scenario_is_green | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-blank-reset-closes-the-probe] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-control-works-mid-drag] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-hint-is-not-a-member] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-pinch-opens-a-probe] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-second-press-opens-a-second-probe] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[a-solved-board-still-offers-probe] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[abandon-does-not-write-the-save] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[abandon-leaves-one-cell] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[commit-touches-a-cell] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[keep-does-not-write-the-save] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[reset-leaves-the-probe-open] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[rule-seven-fires-on-any-filled-cell] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[rule-seven-never-fires] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-actions-show-with-no-probe] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-circles-read-the-checkpoint-board] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-event-is-ignored] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-marker-is-a-fifth-state] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-marker-is-by-position-not-by-set] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-marker-is-never-removed] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-marker-is-on-every-stroke-not-the-probes] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-note-never-shows] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-note-stays-under-a-sentence] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-save-holds-probe-strokes] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[the-usage-paragraph-stays-beside-the-note] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_EachPlantFiresTheScenarioItIsAbout::test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green[undo-past-the-checkpoint-closes-the-probe] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_MarksCarryTheLook::test_a_rung_three_hint_inside_a_probe_is_a_member_of_it | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_MarksCarryTheLook::test_every_mark_made_in_a_probe_carries_the_marker_and_the_cells_before_it_do_not | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_MarksCarryTheLook::test_the_marker_is_a_dashed_outline_and_the_four_states_keep_their_own_look_under_it | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_NoAnswerAndNoRequest::test_every_served_puzzle_file_still_carries_exactly_the_five_fields | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_NoAnswerAndNoRequest::test_no_page_variable_or_stored_value_is_a_solution_grid_after_a_probe | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_NoAnswerAndNoRequest::test_the_only_request_is_the_get_of_its_own_puzzle_file_through_every_interaction | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_NoAnswerAndNoRequest::test_the_probe_adds_no_field_to_the_page_object_and_no_word_solution_to_the_script | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_OnlyOneProbeAtATime::test_the_controls_are_ignored_while_a_stroke_is_being_drawn | LOST
tests/test_public_player_probe.py::TestPublicProbe_OnlyOneProbeAtATime::test_the_probe_control_is_disabled_while_one_is_open_and_a_press_is_a_no_op | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_SolvingCommitsTheProbe::test_marks_that_reach_the_clue_solved_state_commit_the_probe_and_the_banner_is_todays | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_SolvingCommitsTheProbe::test_reset_closes_an_open_probe | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_SolvingCommitsTheProbe::test_the_constructed_board_is_one_mark_from_solved_and_the_fixture_is_what_the_card_needs | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[a-probe-flag-  let probe = null;-  let probe = null;\n  let probing = false;-] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[a-second-copy-of-the-open-rule-  const probeNote =-  const probeStart = (h) => h.done.length;\n  const probeNote =-probe declarations] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[an-event-named-in-the-page-  function paintProbe() {-  const opened = "open";\n  function paintProbe() {-names a probe event] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[an-import-is-dropped-  nextProbe, probeCells, abandonProbe, checkpointHistory,-  probeCells, abandonProbe, checkpointHistory,-nextProbe is not imported] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[the-checkpoint-save-is-not-called-checkpointHistory(history, probe)-history-checkpointHistory is never called] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[the-membership-function-is-not-called-probeCells(history, probe)-[]-probeCells is never called] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[the-page-closes-the-probe-itself-    probe = nextProbe(probe, history, "keep");-    probe = null;-`probe` is given] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control[the-page-opens-a-probe-itself-    probe = nextProbe(probe, history, "open");-    probe = history.done.map((entry) => entry.stroke);-`probe` is given] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_play_js_asks_the_module_for_every_transition_and_defines_none_of_its_own | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_the_cell_has_exactly_the_four_states_and_a_probe_session_writes_no_other | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_StateIsThePureModulesAndStatesAreFour::test_the_served_module_and_tokens_are_the_admins_byte_for_byte | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepThePremiseOnAOnePixelSweep::test_at_rest_a_sample_of_other_heights_holds | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepThePremiseOnAOnePixelSweep::test_at_rest_every_width_from_320_to_999_at_two_heights_holds_and_includes_the_phone_widths | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepThePremiseOnAOnePixelSweep::test_the_first_versions_layout_violates_the_premise_at_exactly_the_phone_widths | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepThePremiseOnAOnePixelSweep::test_the_letter_spacing_the_layout_survives_and_the_one_that_breaks_it | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepThePremiseOnAOnePixelSweep::test_with_a_probe_open_and_with_a_sentence_too_the_premise_holds_on_a_two_pixel_sweep | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepTheZoomModulesPremise::test_a_line_more_under_the_paragraph_at_rest_goes_past_the_bound | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepTheZoomModulesPremise::test_a_sentence_far_longer_than_any_the_page_says_goes_past_the_open_bound | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepTheZoomModulesPremise::test_at_rest_the_space_below_stays_smaller_than_the_top | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepTheZoomModulesPremise::test_both_occupants_of_the_slot_at_once_break_the_premise_while_open | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepTheZoomModulesPremise::test_with_a_probe_open_and_a_hint_sentence_showing_the_premise_holds | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheBarsKeepTheZoomModulesPremise::test_with_a_probe_open_the_note_takes_the_paragraphs_slot_and_the_premise_holds | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheControlsAreOutsideTheToolbar::test_a_control_under_the_touch_floor_is_refused | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheControlsAreOutsideTheToolbar::test_a_probe_control_moved_into_the_toolbar_is_refused | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheControlsAreOutsideTheToolbar::test_the_controls_are_reachable_and_legible_at_the_zoom_maximum_and_a_scrolled_offset[bottom] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheControlsAreOutsideTheToolbar::test_the_controls_are_reachable_and_legible_at_the_zoom_maximum_and_a_scrolled_offset[scrolled] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheControlsAreOutsideTheToolbar::test_the_controls_are_reachable_and_legible_at_the_zoom_maximum_and_a_scrolled_offset[top] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheControlsAreOutsideTheToolbar::test_the_controls_are_under_the_board_44px_and_the_toolbar_is_what_it_was | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheControlsAreOutsideTheToolbar::test_the_markup_agrees_before_a_script_runs | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheMarksCoexistByPixels::test_a_circled_clue_number_keeps_its_ring_while_the_board_is_probed | LOST
tests/test_public_player_probe.py::TestPublicProbe_TheMarksCoexistByPixels::test_a_hinted_probed_cell_shows_the_accent_and_the_dash | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_TheMarksCoexistByPixels::test_a_probed_cell_keeps_its_dashed_ring_on_every_ground_it_can_have | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_TheMarksCoexistByPixels::test_a_ring_painted_in_the_grounds_own_colour_is_caught | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheMarksCoexistByPixels::test_the_probe_changes_no_ground_so_every_tint_still_shows | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[abandon] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[circles] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[commit] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[depth] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[hint] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[marks] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[middrag] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[pinch] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[reset] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[save] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[solve] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_each_scenario_is_green_on_its_own_node[undo] | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_every_scenario_passes_and_none_is_skipped | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_TheScenariosAreGreenOnTheRealPage::test_the_served_canary_mechanism_serves_an_unchanged_file | RETIRE-MOOT
tests/test_public_player_probe.py::TestPublicProbe_UndoClampsTheCheckpoint::test_the_keyboard_undo_and_redo_move_the_probe_like_the_buttons | RETIRE-TWIN
tests/test_public_player_probe.py::TestPublicProbe_UndoClampsTheCheckpoint::test_the_scenario_is_green | RETIRE-TWIN
tests/test_public_player_probe.py::test_the_public_probe_look_comes_from_tokens | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_APinchZoomsAndPaintsNothing::test_with_region_armed_the_second_finger_reverts_the_drag_and_commits_nothing | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_APinchZoomsAndPaintsNothing::test_with_region_off_the_pinch_zooms_and_the_first_fingers_cell_is_unmarked | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_AZoomedGutterNeverCoversTheBoard::test_a_gutter_is_pinned_exactly_while_a_cell_still_fits_beside_it | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_AZoomedGutterNeverCoversTheBoard::test_a_pinned_gutter_always_leaves_a_whole_cell_in_view | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_AZoomedGutterNeverCoversTheBoard::test_one_cell_of_room_is_not_enough_at_the_rung_the_owner_will_meet | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_AZoomedGutterNeverCoversTheBoard::test_pinning_the_gutter_anyway_is_what_hides_the_board | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_AZoomedGutterNeverCoversTheBoard::test_rotating_a_zoomed_phone_re_asks_the_rule | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_NoRequestPerZoom::test_every_zoom_interaction_issues_nothing_beyond_the_initial_get | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_TheAnchoredScrollIsTheModules::test_the_stage_lands_where_anchored_scroll_says_on_both_axes | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules::test_neither_page_invents_a_zoom_key_binding | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules::test_play_js_consumes_the_admins_own_zoom_surface_and_declares_none_of_it | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules::test_play_js_spells_no_bound_step_or_clamp_of_its_own | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules::test_the_cells_touch_action_diverges_from_the_admins_and_is_a_routed_finding | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules::test_the_module_still_exports_all_seven_names_and_only_over_numbers | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules::test_the_only_values_the_zoom_ever_takes_come_from_the_module | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules::test_the_public_sheet_took_the_admins_zoom_rules_and_declares_the_multiplier | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheBoundsComeFromTheModule::test_both_ends_disable_their_button_and_a_press_there_changes_nothing | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_TheBoundsComeFromTheModule::test_no_sequence_of_presses_leaves_the_modules_range | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_TheControlsChangeTheZoom::test_zoom_in_reads_the_modules_next_step_and_grows_every_cell | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_TheControlsChangeTheZoom::test_zoom_out_from_a_stepped_in_board_returns_to_the_modules_floor | RETIRE-TWIN
tests/test_public_player_zoom.py::TestPublicZoom_TheGutterRuleHoldsOverItsOperands::test_a_scrolled_page_and_an_unbounded_stage_hold_the_visible_height_operands | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheGutterRuleHoldsOverItsOperands::test_a_stage_missing_a_measured_element_is_left_alone_and_never_thrown_at | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheGutterRuleHoldsOverItsOperands::test_scrolling_the_page_only_ever_adds_reach_because_the_space_below_is_smaller_than_the_top | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheGutterRuleHoldsOverItsOperands::test_the_boundary_itself_pins_on_both_axes | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheGutterRuleHoldsOverItsOperands::test_the_column_rule_equals_the_geometry_across_the_viewport_heights_at_every_rung | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheGutterRuleHoldsOverItsOperands::test_the_row_rule_equals_the_geometry_across_the_phone_widths_at_every_rung | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_a_portrait_phone_keeps_its_readout | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_every_landscape_width_from_the_headline_phone_up_stays_one_row | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_the_breakpoint_covers_the_width_the_groups_wrap_at_with_the_readout_shown | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_the_column_band_pins_again_at_the_headline_phone_at_100_percent | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_the_gap_is_the_second_spacing_step_in_landscape_and_the_third_otherwise | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_the_readout_is_hidden_visually_in_landscape_and_its_text_is_still_in_the_dom | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_the_stage_regained_the_rows_the_wrap_took | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheLandscapeToolbarIsOneRow::test_the_three_iphone_widths_get_one_44px_row_with_room_to_spare | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheStageEndsAboveTheFold::test_it_follows_a_toolbar_that_changes_height_with_no_resize | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheStageEndsAboveTheFold::test_it_holds_with_the_page_scrolled_when_the_rule_is_re_asked | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheStageEndsAboveTheFold::test_the_stage_bottom_is_inside_the_fold_at_every_viewport | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_TheStageEndsAboveTheFold::test_the_sweep_can_fail_the_old_allowance_is_what_it_would_have_left | RETIRE-MOOT
tests/test_public_player_zoom.py::TestPublicZoom_ZoomRecordsNoStroke::test_every_zoom_interaction_leaves_the_board_history_and_save_identical | RETIRE-TWIN
```