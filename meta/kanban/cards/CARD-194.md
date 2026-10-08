# CARD-194: The puzzle player's brushes become one dropdown with a Region option; a drag scrolls the page unless Region is picked

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/194-player-brush-dropdown-region
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-194
**Source:** owner mobile solver feedback, 2026-10-06 (owner decision: brushes become one dropdown with Region; a drag scrolls the page unless Region is picked)
**Idea:** —
**Wave:** 36
**Depends on:** CARD-189 (merged: click sequences, `clickedState`), CARD-186 (merged: the Maybe brush)
**Touches:** src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_brush_menu.py (new), tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_maybe.py, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_resume.py, tests/test_puzzle_solver_percent.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-10-08T00:00:00Z
**Closed:** 2026-10-08T05:52:27Z
**Actual:** 0.2d
**Merge commit:** e0214c9
**Blocked by:** —

## What to implement

Owner decision (2026-10-06): the four brush buttons become one dropdown. A drag on a phone must scroll the page unless Region is picked.

**Current behaviour (verified by reading the code).**
- `templates/puzzle_solve.html`: `#puzzle-player-controls` holds `.player-tools` (`role="group"`, `aria-label="Marking tool"`) with four toggle buttons `[data-player-tool]`: `filled` (Black), `empty` (White), `unknown` (Undecided), `maybe` (Maybe). Exactly one has `aria-pressed="true"`.
- `static/solver.js` `wireMarking` (line 462): `let tool = FILLED` (line 470). The tool buttons' click handler (line 541) sets `tool` and clears `lastClick`.
- `solver.js` `pointerdown` (line 493) reads `tool` at press. It calls `setPointerCapture` and `preventDefault` for every pointer type (mouse, pen, touch). `pointermove` (line 505) previews `dragStroke`. `pointerup` (line 517) records a drag, or a click through `clickStroke`.
- `static/admin.css` line 432: `.player-cell { touch-action: none }`. So a touch drag on a cell never scrolls the page today. Clue boxes keep `auto` (CARD-182).
- `static/solver_state.js`: `dragStroke(start, path, tool)` and `clickStroke(board, row, col, tool, repeat)` accept only the four cell states. CARD-189 AC-2 refuses any other tool.

**Target behaviour.**
1. **One trigger.** `.player-tools` keeps one `<button>` as its direct child. It has `aria-haspopup="menu"`, `aria-expanded` and `aria-controls` (the menu's id). Its accessible name is `Brush: <chosen brush>` (for example `Brush: Black`). Its visible text is the chosen brush (for example `Black`). With Region on, the visible text is `Region · <brush>`. Owner-visible default.
2. **The menu.** A `<div role="menu" hidden>` sits inside `.player-tools`, after the trigger. It holds five `<button role="menuitemradio">` items in this order: Black, White, Maybe, Undecided, Region. Each item carries `data-player-tool` (`filled`, `empty`, `maybe`, `unknown`, `region`). The item for the current choice has `aria-checked="true"`; exactly one item is checked. The menu opens over the board and does not move it. The menu's items are not `<button>` children of `.player-tools`, so layout selectors that use `.player-tools > button` still see only the trigger.
3. **Picking a brush** sets the brush and turns Region off. The menu closes, focus returns to the trigger, and `lastClick` is cleared (as a tool press is today).
4. **Picking Region** turns Region on and keeps the brush it was on. The menu closes and focus returns to the trigger.
5. **Region on, drag.** A drag (any pointer type) marks cells with the brush's state. It uses `dragStroke` with the brush, so `solver_state.js` never sees "region". The stroke is previewed on move and recorded on release, as today.
6. **Region on, tap.** A single tap is a click with the brush (CARD-189 table). Region stays on.
7. **Region turns itself off** after a region drag is recorded (pointerup with `dragging` true). The brush is back on the trigger.
8. **Region off, touch or pen drag.** No cell is marked. The browser pans the page, or the stage on a wide phone board. A touch tap is still a click (CARD-189). The gesture is dropped on `pointercancel`, as now.
9. **Region off, mouse drag.** Drags mark as today (desktop default, see Decisions).
10. **Touch-action follows Region.** `.player-board` gets class `is-region` while Region is on. In `admin.css`, `.player-cell` takes `touch-action: auto`. `.player-board.is-region .player-cell` takes `touch-action: none`. In `solver.js` `pointerdown`, a touch or pen press with Region off does not call `setPointerCapture` and does not start a drag. Its tap path (pointerup on the same cell, nothing in between) still records the click.
11. **Keyboard.** On the trigger, Enter, Space or ArrowDown opens the menu with focus on the checked item. Inside the menu: ArrowDown and ArrowUp move (wrapping), Home and End go to the first and last item, Enter or Space picks the focused item (it closes the menu and returns focus to the trigger), Escape closes without a change. Tab closes the menu and moves focus to the next control.
12. **Solved board.** The trigger and the menu sit in `.player-tools`, which the solved state already hides (`visibility: hidden`, admin.css). The menu closes on solve. Clicks, drags and menu picks do nothing while the board is solved (the existing lock).
13. **Not saved.** Brush and Region are UI state, like `lastClick`. They are not in the history and not in the saved state (CARD-185). After a reload the trigger reads `Brush: Black` and Region is off. Today the tool is not saved either.
14. **Copy.** `#puzzle-player-hint` gets a Region sentence and names the menu. The drag sentence keeps its meaning: with Region on, a drag marks; with Region off, a mouse drag marks and a touch drag scrolls. The Maybe sentence stays.

**Decisions made in this card (owner-visible; the owner confirms from the renders).**
- [Owner decision needed, default applied] Desktop: mouse drags keep marking without Region. The dropdown and Region apply at every width. The owner's scroll rule is written for touch and phone.
- [Owner decision needed, default applied] Pen counts as touch: a pen drag needs Region.
- Tap with Region on: a click with the brush; Region stays on.
- Region turns off after any recorded region drag, even one that changes no cell. The rule is "a drag ended", not "a cell changed".
- Menu order: Black, White, Maybe, Undecided, Region (the owner's order). The old button order was Black, White, Undecided, Maybe.
- Trigger text with Region on: `Region · Black`.

## Acceptance criteria

- **AC-1:** Given the player page of a stored puzzle, when the tool group is read, then it holds one button named `Brush: Black` with `aria-haspopup="menu"` and `aria-expanded="false"`, and no button named White, Undecided or Maybe exists.
  *test: TestSolverBrushMenu_OneButtonWithAMenu::test_one_button_with_a_menu (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-2:** Given the trigger is clicked, when the menu is read, then five `menuitemradio` items read Black, White, Maybe, Undecided, Region in that order, Black is `aria-checked="true"` and the trigger has `aria-expanded="true"`.
  *test: TestSolverBrushMenu_OneButtonWithAMenu::test_menu_lists_five_items_in_order (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-3:** Given the menu is open from the keyboard, when ArrowDown and Enter are pressed to pick White, then the menu closes, focus is on the trigger, the trigger reads `Brush: White`, and the next mouse drag marks white.
  *test: TestSolverBrushMenu_Keyboard::test_arrow_and_enter_pick_a_brush (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-4:** Given the menu is open, when Escape is pressed, then the menu closes, nothing on the board changes and focus is on the trigger; and when Tab is pressed instead, the menu closes and focus moves to Undo.
  *test: TestSolverBrushMenu_Keyboard::test_escape_closes_and_tab_leaves (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-5:** Given Maybe is picked, when a blank cell is clicked twice, then it reads "?" and then blank (the CARD-189 Maybe sequence).
  *test: TestSolverClickFollowsTheBrush::test_repeat_clicks_follow_each_brush_sequence (in tests/test_puzzle_solver_marking.py; only its tool helper changes)*
- **AC-6:** Given Region is off, when a touch drag runs along row 2 from column 3 to column 7 (CDP touch events), then no cell changes and the page scrolls.
  *test: TestSolverBrushMenu_Touch::test_touch_drag_without_region_scrolls_and_marks_nothing (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-7:** Given Region is on with White picked, when the same touch drag runs, then the five cells are white and Region is off afterwards (the trigger reads `Brush: White`).
  *test: TestSolverBrushMenu_Touch::test_touch_drag_with_region_marks_and_region_turns_off (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-8:** Given Region is on with Maybe picked, when a mouse drag runs along row 4 from column 2 to column 6, then the five cells read "?", and afterwards the Region item is `aria-checked="false"` and Maybe is checked.
  *test: TestSolverBrushMenu_Region::test_mouse_region_drag_marks_then_region_turns_off (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-9:** Given Region is on with Black picked, when a blank cell is tapped once, then it reads black and Region is still on.
  *test: TestSolverBrushMenu_Region::test_a_tap_with_region_clicks_and_region_stays_on (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-10:** Given Region is off and the brush is Black, when a mouse drag runs along a row, then the five cells are black (the desktop default).
  *test: TestSolverMarking_DragMarksOneLine::test_each_tool_sets_its_state_along_the_line (existing, in tests/test_puzzle_solver_marking.py; unchanged)*
- **AC-11:** Given the board is solved, when Tab is pressed from the top of the page, then no brush control is reached and the trigger and menu items are not focusable.
  *test: TestSolverMaybe_HiddenToolsAreOutOfReachWhenSolved::test_out_of_reach (in tests/test_puzzle_solver_maybe.py; changed, see G-4)*
- **AC-12:** Given the page is reloaded after a brush and Region were chosen, when it loads, then the trigger reads `Brush: Black` and Region is off.
  *test: TestSolverBrushMenu_Region::test_reload_starts_with_black_and_region_off (in tests/test_puzzle_solver_brush_menu.py, new)*
- **AC-13:** Given Region is off, when the board is viewed at 390 px, then `.player-cell` computes `touch-action: auto` and clue boxes keep `auto`; with Region on, cells compute `none`.
  *test: TestSolverPhone_SwipingTheCluesPansTheBoard::test_cells_take_no_touch_action_and_clue_boxes_keep_the_default (in tests/test_puzzle_solver_phone.py; changed, see G-4)*
- **AC-14:** Given a player page with ten brush picks and drags, when the page runs, then the browser issues no network request for them.
  *test: TestSolverMaybe_NoRequestPerMark::test_no_request (in tests/test_puzzle_solver_maybe.py; unchanged, uses the tool helper)*
- **AC-15:** Given the owner's renders, when the owner looks at the dropdown open, Region on, a marked region, at 390 px and at 1440 px, then the layout is accepted before merge.
  *test: review-lens (owner renders in ~/Documents/nonogram-reviews/CARD-194/)*

## Guardrails

- G-1: Mouse drags do not change: `dragStroke`, `dragLine`, `TestSolverMarking_DragMarksOneLine` and FR-044 AC-305/AC-306 (mouse) stay as they are. Playwright's `mouse` drags are pointerType mouse, so they keep working.
- G-2: `solver_state.js` is unchanged and its tests stay green: CARD-189 AC-1 (32-case click table), AC-2 (a tool that is not a cell state throws `RangeError`), TestSolverPage_AllCellsStartUndecided and the `"states"` pin. Region is never a cell state.
- G-3: The history model and the saved state carry no brush and no Region (TestSolverMarking_UndoRedoByStroke, TestSolverHistoryModule, CARD-185's TestSolverResume_*).
- G-4: Protected tests that change. Each change is forced by the one-button menu or by touch drags needing Region. No other protected test is edited.
  - `tests/test_puzzle_solver_marking.py`
    - helper `_tool(page, name)` and `_button` (lines 180-185): `_tool` opens the menu and picks the item. Every caller (about 35 `_tool(` calls across marking, maybe, percent, progress, resume) is unchanged.
    - `CONTROLS` (line 814) and `test_each_control_has_a_name_and_is_reachable_by_tab` (line 843): the four brush names become one trigger name. Tab order is checked again.
    - `test_three_clicks_go_filled_empty_undecided_and_are_drawn_so` (line 220): reads `aria-pressed` on a "Black" button. Now it reads the trigger's name.
    - `TestSolverMarking_ClickIgnoresTheSelectedTool::test_exactly_one_tool_is_pressed` (line 277): reads four `aria-pressed` buttons. Now it reads the menu's `aria-checked`.
    - `test_the_page_copy_describes_the_new_click` (line 551): asserts 4 `[data-player-tool]` items in the group. Now it asserts 5 menu items and the new hint copy.
    - `test_each_control_acts_on_enter_or_space` (line 864): presses the four brush buttons by name. Now it operates the menu.
    - `TestSolverMarking_KeyboardAndLabels::test_each_tool_acts_on_a_single_key_press` (line 915, six cases): same reason.
    - `test_the_tool_picked_by_keyboard_governs_the_next_drag` (line 965) and `test_a_tool_picked_mid_drag_applies_to_the_next_drag` (line 1018): focus the White button by name. Now they use the menu.
    - `test_a_touch_drag_marks_one_line` (line 670): touch drag with no Region would pan. Pick Region first.
  - `tests/test_puzzle_solver_maybe.py`
    - `_pressed` helper (line 102) and `test_enter_and_space_select_it` (line 880): read four brush buttons' `aria-pressed`.
    - `TestSolverMaybe_ToolKeyboardAndLabel` (line 850, Maybe button name, `data-player-tool`, swatch) and `test_tab_reaches_it_between_undecided_and_undo` (line 866): the Maybe button is now a menu item.
    - `TestSolverMaybe_HiddenToolsAreOutOfReachWhenSolved::test_out_of_reach` (line 1064): counts four brush buttons by name and focuses `[data-player-tool]`. Now it checks the trigger and the menu items.
    - `TestSolverMaybe_FourToolsKeepOneToolbarRowAt1280::test_one_row` (line 1052): the assertion should still hold with one trigger. Only the class name and docstring ("four tools") change, and only if the assertion still holds.
  - `tests/test_puzzle_solver_phone.py`
    - `_scrolled_phone_page` (line 213): `tool="White"` clicks the White button by name. Now it picks White, then Region for the touch-drag test.
    - `test_a_touch_drag_marks_exactly_the_five_cells_under_the_finger` (line 236): must pick Region (its expected state stays `E`).
    - `test_cells_take_no_touch_action_and_clue_boxes_keep_the_default` (line 310): asserts cells are `none`. Now: `auto` with Region off, `none` with Region on.
    - module docstring (line 7): says cells keep `touch-action: none`. Text only.
  - `tests/test_puzzle_solver_resume.py`
    - line 463: asserts the Black button's `aria-pressed` on load. Now it reads the trigger's name.
  - `tests/test_puzzle_solver_percent.py`
    - conditional: its `_LAYOUT` checks read `.player-tools > button`. Only the trigger matches. If the 1280 px layout asserts fail, adjust them and say why in Worktree notes.
  - Not changed: `tests/test_puzzle_solver_clues.py` and `tests/test_puzzle_solver_hint.py` (mouse drags, the Hint and Reset buttons), `tests/test_puzzle_solver_progress.py` (uses `_tool` only, and `.player-tools` still exists), `tests/test_puzzle_solver_page.py`, and every touch tap test (`test_a_touch_tap_cycles_too`, `test_touch_taps_follow_the_brush`, `test_a_cancelled_gesture_makes_the_next_tap_a_first_click`).
- G-5: The solved lock still ignores clicks, drags and menu picks (TestSolverProgress locked-board tests).
- G-6: No mark or pick sends a request (FR-044 AC-311, TestSolverMarking_NoRequestPerMark); the marking code still reads no solution (TestSolverMarking_RevealsNoCorrectness).
- G-7: CARD-182's desktop rules, the 24 px phone floor and the clue boxes' `touch-action: auto` stay. CARD-183's Hint, CARD-186's Maybe state and sequence, CARD-187's percent and CARD-188's circles are unchanged.
- G-8: `solver.js` header comments that describe the tool group or the pointer rules are updated in the same change (a stale header is a defect).

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-194` (53 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniq… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when th… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws n… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on dens… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzz… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pur… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with th… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attributi… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the gr… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle neve… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membersh… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percent… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm toolcha… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R5 — pyproject.toml package-data for nonogram.admin includes static/*.js alongside templates/*.html and static/*.css, so the player's script ships in every built wheel. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a paramet… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No ot… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) nev… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement,… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is a… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns i… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the bo… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-044 (puzzle player). Drags (AC-305, AC-306) stand for the mouse. Touch drags need Region. AC-310 (Tab order) is amended by this card: four brush buttons become one trigger and a menu. Card-local ACs above stand until the architect writes the delta.
- **Architect delta needed:** amend FR-044's drag statement (touch needs Region, mouse unchanged), amend AC-310 (one brush control, menu keys), add a Region AC. Card-local until then.
- **ADR:** ADR-0038 (R1 plain JS and CSS, no build step; R2 no request per mark; R4 pure state module: Region and the brush are UI state in `solver.js`, not in `solver_state.js`).
- **CON:** CON-021 (interactive play is the admin panel's player only).
- **Components:** COMP-009 (admin panel), CAP-007 (puzzle play), as CARD-189 names them.
- **Trace:** meta/architecture/trace.yml (FR-044 row).

## Design context

- **Screen:** the admin puzzle player, `/puzzle/<id>/solve`. The tool group becomes one button with a menu. The hint line under the board changes copy.
- **Owner-visible defaults:** (a) one trigger labelled with the brush, Region shown as `Region · <brush>`; (b) menu order Black, White, Maybe, Undecided, Region; (c) the menu opens over the board and does not move it; (d) desktop mouse drags still mark without Region; (e) Region turns off after a region drag; (f) the hint sentence.
- **Phone note:** on a board wider than the stage, a touch drag on a cell pans the stage first, then the page, because the stage is the nearest scroll box. The owner should see this in the 390 px render.
- **Renders:** ~/Documents/nonogram-reviews/CARD-194/ (owner visual check before merge): the dropdown open; Region on; a marked region; 390 px and 1440 px.

## Worktree notes

- [Origin] Owner mobile solver feedback, 2026-10-06. No IDEA.
- [Owner decision] One brush dropdown (Black / White / Maybe / Undecided / Region). With Region on, a drag marks cells in the brush's state. Without Region, a touch drag scrolls the page. Region turns off after each marked region. Recorded as [Owner decision] 2026-10-06.
- [Owner decision needed, default applied] Desktop mouse drags keep marking without Region (the owner's scroll rule is for touch). Pen counts as touch. The owner confirms both from the renders.
- [Facts] `admin.css:432` `.player-cell { touch-action: none }` is why a touch drag never scrolls today. `solver.js:493` `pointerdown` captures and `preventDefault`s every pointer type. `solver.js:470` `let tool = FILLED`. `solver.js:541` is the tool click handler. `solver_state.js:192` `clickStroke` takes the tool and refuses non-states.
- [Facts] Playwright's `page.mouse` drags are pointerType mouse, so every mouse drag test keeps working with no change. Touch tests use CDP `Input.dispatchTouchEvent` or `touchscreen.tap`, and need Region (or are taps, which still work).
- [Decision] Region is UI state (like `lastClick`): not in `solver_state.js`, not in the history, not saved. The brush is not saved either (matches today).
- [Decision] The trigger is the only direct `<button>` child of `.player-tools`. Menu items are `button role="menuitemradio"` inside a `div role="menu"`, so `.player-tools > button` layout selectors still measure the trigger.
- [Decision] Region turns off after any recorded region drag, even one that changes no cell.
- [Decision] A tap with Region on is a click with the brush (CARD-189 sequence) and Region stays on.
- [Protected tests] See Guardrails G-4 for the exact list. The `_tool` helper edit is the single change that keeps about 35 callers unchanged.
- [Conditional] `tests/test_puzzle_solver_percent.py` changes only if the 1280 px layout asserts fail with one trigger. Its `_LAYOUT` checks `.player-tools > button`. Record the reason in these notes if it changes.
- [Architect delta] FR-044 / AC-310 amendment and the Region AC go in meta/architecture. Card commits exclude meta/, so record a `DESIGN-REGISTER` line here instead of editing it: the brush dropdown replaces the four-button tool group (CARD-194) and the touch-action rule follows Region.
- [Sibling] CARD-193 and CARD-195 of wave 36 touch the same player; rebase before merge.
- [Owner decision] 2026-10-06 — dropdown with Black / White / Maybe / Undecided / Region as the owner specified; desktop mouse drags keep marking without Region (defaults in the card stand, pen counts as touch).
- [Implementation] Trigger + menu built per the card: `#puzzle-player-tool-trigger` (aria-label `Brush: <brush>`, visible text `<brush>` or `Region · <brush>`) opens `#puzzle-player-tool-menu` (`role="menu"`, five `role="menuitemradio"` items in the owner's order). `solver.js` `wireMarking` gained `syncTrigger`/`openMenu`/`closeMenu`/`pick`; `pointerdown` now computes `paints = pointerType === "mouse" || region` and only captures/prevents-default when `paints`; `pointerup`'s drag branch turns Region off and calls `syncTrigger()` before committing. `admin.css` flips `.player-cell`'s `touch-action` from a permanent `none` to `auto`, with `.player-board.is-region .player-cell { touch-action: none }` layered on top.
- [Bug found and fixed, review cycle 1] `pointermove` only tracked `gesture.dragging` when `gesture.paints` was true, so a non-painting touch/pen drag (Region off) that reached `pointerup` without a `pointercancel` was read as a click on its *start* cell instead of marking nothing. Probed with CDP `Input.dispatchMouseEvent(pointerType: "pen")`: confirmed Chromium does not reliably cancel a pen gesture the way it cancels touch (a real, reproducible gap, not a simulation artifact of the probe itself — touch reliably got `pointercancel` in the same harness). Fix: `dragging` is now tracked unconditionally (only the preview *paint* stays gated on `paints`); `pointerup` takes no action when `dragging` is true but `paints` is false. Covered by new `TestSolverBrushMenu_Pen` (2 cases); mutation-tested (reverting the fix made the new test fail, confirmed, reverted). Adversarial verification for this Important finding was the mutation-revert itself (an independent, reproducible behavioral check) rather than a second reasoning pass — recorded here since the finder and fixer were the same agent in the same cycle.
- [CSS fix, review cycle 1] Collapsing four buttons into one trigger made `.player-tools`' own width (and so the shared-grid-cell `.player-solved-box`'s wrap width — `contain: inline-size`) too narrow for a short picture name ("Solved: Lighthouse") to fit on one line, so the solved banner wrapped onto a second line and moved the board — breaking `TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth` (CARD-186's own invariant) at every swept width. Fixed with `.player-tool-trigger { min-width: 13rem }`, measured (193.5px natural width of "Solved: Lighthouse" + icon, +headroom) and documented in the adjoining admin.css comment; `TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth` (the 120-char case) still wraps as before, confirming the fix didn't remove the wrap mechanism, just raised its threshold.
- [Conditional resolved] `tests/test_puzzle_solver_percent.py`'s 1280 px layout assertion (`test_below_the_pair_at_the_right_at_1280`) DID fail with one trigger: the narrower trigger leaves enough room that Progress now shares the buttons' row at 1280 px, the same as at 1440 px, instead of wrapping below the errors/hints pair. Renamed to `test_shares_the_buttons_row_at_1280` and rewritten to assert the new (now-true) same-row layout; the admin.css `.player-counters` comment was updated to match. The narrower-wraps-below case still holds at some width between 1280 and 390 (not re-derived; not required by any AC).
- [SCOPE+] Two files outside this card's Touches list needed a one-line fix each, forced by the same four-button-to-menu collapse: `tests/test_puzzle_solver_hint.py` (`TestSolverHint_DisabledWithNothingToReveal::test_enabled_again_once_a_cell_is_undecided`) and `tests/test_puzzle_solver_mirror.py` (two call sites) each had a direct `_button(page, "Black").click()`, which no longer resolves a `role="button"` named "Black" (Black is now a `role="menuitemradio"` menu item). Both changed to `_tool(page, "Black")` (opens the menu, picks the item) with no other change to either file. G-4's own enumeration of "Not changed" files (`test_puzzle_solver_clues.py`, `test_puzzle_solver_hint.py`) didn't anticipate `hint.py`'s one direct button-click call site outside the `_tool`/`_button`-helper pattern; `mirror.py` isn't named in G-4 at all (CARD-193's own file, not audited by this card's guardrail).
- [AC/EC/G check] All 15 card-local AC tests (AC-1..AC-4, AC-6..AC-9, AC-12 in the new file; AC-5, AC-10, AC-11, AC-13, AC-14 in their existing homes per the card's own `test:` pointers) re-run individually by name: 15 passed, 0 failed. All G-1/G-2/G-4/G-6 guardrail-protected test classes re-run individually by name (`TestSolverMarking_DragMarksOneLine`, `TestSolverHistoryModule`, `TestSolverMarking_UndoRedoByStroke`, `TestSolverMarking_RevealsNoCorrectness`, `TestSolverMarking_NoRequestPerMark`, `TestSolverMaybe_NoRequestPerMark`, `TestSolverResume_ReloadRestoresBoardCountsAndHistory`): 34 passed, 0 failed. Full touched-file group (11 files, including the new one): 339 passed, 0 failed. Full suite, run twice — once before the pen fix (6699 passed, 0 failed; the pen-input defect had no test yet, so this run couldn't have caught it) and once after, on the final tree (6701 passed, 0 failed, +2 for the two new Pen tests) — both clean (dot count taken directly per the harness-quirk note; no F/E markers either run).
- [Review] Score 9.0, cycle 1/3 (0 critical, 1 important — found and fixed within this same cycle, see above — 3 minor, 2 out-of-scope). Report: `meta/review/20261008T040241Z-CARD-194-cycle1.yml` (worktree only, per the card-sync protocol — not committed).
- [Docs step] `tests/README.md` is scoped to "Wave 1" features (batch history, puzzle preview, bulk operations) and has never documented any `test_puzzle_solver_*.py` file — checked CARD-161 through CARD-193, none touched it either. No-op, consistent with established precedent, not a silent skip.
- [Renders] `~/Documents/nonogram-reviews/CARD-194/`: `dropdown-open-{1440x900,390x844}.png`, `region-on-{1440x900,390x844}.png`, `marked-region-{1440x900,390x844}.png` (6 PNGs). Produced through the real admin app (temp SQLite) + Playwright against the 15×15 fixture grid used throughout this card's tests, named "Lighthouse". The marked-region renders capture a drag mid-gesture (mouse down + move, before release) so the preview is visible while Region is still on, since Region turns itself off the instant the drag is recorded. Not yet owner-reviewed (AC-15 is review-lens only).
- [Commit] Success commit `7c82b35` on `card/194-player-brush-dropdown-region` (11 files, +884/-167; explicit pathspecs, nothing under `meta/`). Not merged — that is the dispatcher's call, per the pipeline brief.
- [Open question for the owner] None blocking. The two "[Owner decision needed, default applied]" lines above (desktop mouse unaffected; pen counts as touch) are implemented as written and are exactly what the renders + this implementation ask the owner to confirm — no further default needed a guess.
- [Owner render check] 2026-10-08 — owner reviewed the 6 renders at ~/Documents/nonogram-reviews/CARD-194/ (dropdown order Black/White/Maybe/Undecided/Region; trigger reads "Region · Black" with Region on; a marked region shows a correct run of cells) and approved merging as-is.
- [Success] Commit `7c82b35` stands as this card's success commit; no fix cycle needed beyond the same-cycle bug fixes already folded in. Only `meta/` artefacts (this card's own notes, the review YAML) remained uncommitted in the worktree, synced into the main repo instead.
