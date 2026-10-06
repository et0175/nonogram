# CARD-189: In the puzzle player, a click follows the selected brush

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/189-click-follows-the-brush
**Worktree:** —
**Source:** owner's solver test doc 2026-10-05, item 5 (owner decision 2026-10-05: follow the doc's sequences — the first click on a cell sets the brush's state, repeat clicks continue the brush's sequence)
**Idea:** —
**Wave:** 35
**Depends on:** CARD-186 (the MAYBE "?" state, the Maybe brush and the `clickedState(state, tool)` hook exist)
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_progress.py, tests/test_puzzle_solver_maybe.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code, before CARD-186).**

- `static/solver_state.js` line 151: `CYCLE = {UNKNOWN: FILLED, FILLED: EMPTY, EMPTY: UNKNOWN}`.
  `cycled(state)` reads it.
- `clickStroke(board, row, col)` (line 166) takes no tool. Its comment says
  "whatever tool is selected — the tool governs drags only".
- `static/solver.js` `wireMarking`: the `pointerup` handler (line 371) records
  `clickStroke(history.board, ...done.start)` for a click and
  `dragStroke(done.start, done.path, done.tool)` for a drag. The tool is
  already captured at `pointerdown` (`gesture.tool`, line 351). The header
  comment (line 51) says "a click: the cell cycles whatever the tool".
- `templates/puzzle_solve.html`: the tool group is labelled
  `aria-label="Marking tool for drags"` (line 50). The hint line (line 80)
  reads "Click a cell to cycle black, white, undecided. Drag along a row or
  column to apply the selected tool."
- This is CARD-161's build of FR-044 ("click cycles, tool drags", owner
  2026-10-03), pinned by AC-303 and AC-304.

**After CARD-186 (drafted, merges first).** `MAYBE = "maybe"` is the fourth
cell state (`CELL_STATES = [UNKNOWN, FILLED, EMPTY, MAYBE]`), the brush is
labelled **Maybe** (`data-player-tool="maybe"`). CARD-186 adds a pure
`clickedState(state, tool)`: Maybe toggles "?" <-> blank, every other tool
keeps today's cycle (MAYBE -> FILLED). `clickStroke(board, row, col, tool)`
calls it; an omitted tool keeps today's cycle. `solver.js` passes `done.tool`.

**Target behaviour (owner decision 2026-10-05: follow the doc's sequences).**

Each brush has a sequence. A first click on a cell sets the brush's state.
Each repeat click on the same cell with the same brush moves one step on.

| Brush     | Sequence                                  |
|-----------|-------------------------------------------|
| Black     | dark -> white -> blank -> dark -> ...     |
| White     | white -> blank -> dark -> white -> ...    |
| Undecided | blank -> dark -> white -> blank -> ...    |
| Maybe     | "?" -> blank -> "?" -> ...                |

The three colour brushes share one order (dark -> white -> blank -> dark) and
differ only in where they start.

**What is a repeat click.** A click is a *repeat* when the player's previous
input was a recorded click on the same cell with the same brush, and nothing
else happened in between. Anything else makes the next click a *first* click:

- a click on a different cell;
- pressing any tool button (even the one already pressed);
- a drag (recorded, or one that changed nothing), or a cancelled gesture;
- undo, redo, reset (Clear board), a hint (CARD-183), `setBoard`;
- a page load (the memory is never saved, see below).

**A first click on a cell already in the brush's state.** Decision: it
advances to the sequence's next step (Black on a dark cell gives white;
Undecided on a blank cell gives dark; Maybe on a "?" cell gives blank). So a
click always changes the cell and is always one undo step. It then counts as
the last click, so the next click on that cell is a repeat.

**The full table** (`clickedState(state, tool, repeat)`). "blank" = UNKNOWN,
"dark" = FILLED, "white" = EMPTY, "?" = MAYBE.

First click (`repeat = false`):

| Brush \ cell before | blank | dark  | white | "?"   |
|---------------------|-------|-------|-------|-------|
| Black               | dark  | white | dark  | dark  |
| White               | white | white | blank | white |
| Undecided           | dark  | blank | blank | blank |
| Maybe               | "?"   | "?"   | "?"   | blank |

Repeat click (`repeat = true`):

| Brush \ cell before | blank | dark  | white | "?"     |
|---------------------|-------|-------|-------|---------|
| Black               | dark  | white | blank | dark *  |
| White               | dark  | white | blank | white * |
| Undecided           | dark  | white | blank | blank * |
| Maybe               | "?"   | "?" * | "?" * | blank   |

\* Unreachable in the page: a repeat click only follows a click by the same
brush, which left the cell inside that brush's sequence. The pure function
still defines these cells: a cell outside the brush's sequence takes the
brush's state, as on a first click.

The rule in one line: if the cell is outside the brush's sequence, it takes
the brush's state; otherwise, on a repeat click or when the cell already holds
the brush's state, it moves one step along the sequence; otherwise it takes
the brush's state.

**A click on a "?" cell.** First click: Black makes it dark, White makes it
white, Undecided makes it blank, Maybe makes it blank. This replaces
CARD-186's interim "a "?" cell clicks to black with any colour brush".

Every one of the 32 entries changes the cell. So every click is exactly one
stroke and one undo step; history never drops a click as a no-op.

Implementation:

1. **`solver_state.js` (pure).** Extend CARD-186's hook to
   `clickedState(state, tool, repeat)` implementing the tables. Make
   `clickStroke(board, row, col, tool, repeat)` take the tool as required:
   no tool, or a value that is not a cell state, throws `RangeError`, as
   `dragStroke` does. This drops CARD-186's "omitted tool = today's cycle"
   fallback; this card updates every three-argument caller. `repeat` is
   coerced with `=== true`. Remove `CYCLE`'s old meaning: if a cycle constant
   stays, its comment names it as the colour brushes' order, not "a click's
   next state". `cycled` goes or is rewritten the same way. The module stays
   pure: no DOM, never the substring "import " (ADR-0038/R4).
2. **`solver.js` holds the memory.** Decision: the "last click" memory lives
   in `wireMarking` as `lastClick = {row, col, tool} | null`. It is UI state.
   It is not on the board, not in the history value, never undone or redone,
   and never saved (CARD-185's localStorage restore starts with it empty).
   - On a click: `repeat = lastClick` matches the cell and `gesture.tool`.
     Record `clickStroke(board, row, col, gesture.tool, repeat)`, then set
     `lastClick` to that cell and tool.
   - Clear `lastClick` on everything in the "first click" list above. One
     way: `commit` clears it, and the click path sets it after its commit;
     tool buttons, a no-op drag and `pointercancel` clear it too.
   - A click on a locked (solved) board is still ignored and leaves no memory.
   - Update the MARKING header comment.
3. **`puzzle_solve.html`.** Relabel the tool group `aria-label="Marking tool"`
   (it no longer governs drags only). Rewrite the hint line's first sentence:
   "Click a cell to give it the selected tool's mark; click it again to go
   on (Black: black, white, blank; White: white, blank, black; Undecided:
   blank, black, white)." Keep "Drag along a row or column to apply the
   selected tool." and CARD-186's Maybe sentence ("With Maybe, a click marks ?
   and a second click clears it."). Keep the id and class.
4. **Drags are unchanged.** They paint the tool's state along one line.
5. **Keyboard.** There is no keyboard cell marking. Keys only pick a tool
   (Enter/Space on a focused tool button) and undo/redo (Ctrl/Cmd+Z,
   Shift+Ctrl/Cmd+Z). Picking a tool by key clears the memory exactly as a
   mouse press does (same button `click` handler). Do not add keyboard marking.

## Acceptance criteria

- **AC-1:** Given each brush (FILLED, EMPTY, UNKNOWN, MAYBE), each cell state (UNKNOWN, FILLED, EMPTY, MAYBE) and each `repeat` (false, true), when `clickStroke(board, r, c, brush, repeat)` is called on a board holding that state at (r, c), then the stroke is that one cell with the state in this card's two tables, for all 32 cases. The expected tables are hand-written literals in the test, not computed from the module, and the test fails if `CELL_STATES` holds a state the literals do not cover.
  *test: TestSolverClickFollowsTheBrush::test_every_brush_state_and_repeat_gives_the_table (in tests/test_puzzle_solver_marking.py, `await import('/static/solver_state.js')`)*
- **AC-2:** Given a missing tool or a tool name that is not a cell state, when `clickStroke` is called with it, then it throws `RangeError`.
  *test: TestSolverClickFollowsTheBrush::test_a_click_without_a_valid_tool_is_refused (in tests/test_puzzle_solver_marking.py)*
- **AC-3:** Given a blank cell on the player page and one brush selected, when the same cell is clicked four times in a row, then the states seen are Black: dark, white, blank, dark; White: white, blank, dark, white; Undecided: dark, white, blank, dark; Maybe: "?", blank, "?", blank. One fresh cell per brush, real mouse clicks.
  *test: TestSolverClickFollowsTheBrush::test_repeat_clicks_follow_each_brush_sequence (in tests/test_puzzle_solver_marking.py)*
- **AC-4:** Given a cell in each of dark, white and "?" (set by drags), when it is clicked once with each brush (a first click), then it takes the first-click table's state; in particular a "?" cell becomes dark (Black), white (White), blank (Undecided) and blank (Maybe).
  *test: TestSolverClickFollowsTheBrush::test_a_first_click_on_each_state_with_each_brush (in tests/test_puzzle_solver_marking.py)*
- **AC-5:** Given Black selected and a cell clicked twice (dark, then white), when the next click on it follows (a) a click on another cell, (b) pressing the Black button again, (c) a drag elsewhere, (d) undo then redo, then that click is a first click: the white cell becomes dark, not blank. Without any of these, the third click gives blank.
  *test: TestSolverClickFollowsTheBrush::test_anything_between_two_clicks_makes_the_next_a_first_click (in tests/test_puzzle_solver_marking.py)*
- **AC-6:** Given a blank cell with Black selected, when it is clicked once, then White is selected and it is clicked again, then the second click is a first click for White: the cell becomes white (dark is not White's state, so it takes White's state).
  *test: TestSolverClickFollowsTheBrush::test_a_brush_change_restarts_the_sequence (in tests/test_puzzle_solver_marking.py)*
- **AC-7:** Given White selected, when a blank cell is tapped three times on a touch screen, then it goes white, blank, dark (taps follow the brush and its sequence as clicks do).
  *test: TestSolverClickFollowsTheBrush::test_touch_taps_follow_the_brush (in tests/test_puzzle_solver_marking.py)*
- **AC-8:** Given a blank board and Black selected, when one cell is clicked three times (dark, white, blank) and undo is pressed three times and redo three times, then each undo steps back exactly one click (white, dark, blank) and the redos bring back dark, white, blank; the next click after the redos is a first click (blank becomes dark).
  *test: TestSolverClickFollowsTheBrush::test_each_click_is_one_undo_step (in tests/test_puzzle_solver_marking.py)*
- **AC-9:** Given each brush, when a drag is made along a row, then every cell passed takes the brush's state whatever it held before (drags unchanged).
  *test: TestSolverMarking_DragMarksOneLine::test_each_tool_sets_its_state_along_the_line (existing, in tests/test_puzzle_solver_marking.py — stays green unchanged)*
- **AC-10:** Given EC-035's seeded corpus, with each click op now carrying a random brush and a repeat flag computed by the corpus driver from its own last-click memory (cleared by every non-click op), and the Python `_Model.click` using its own hand-written 32-entry table, when the corpus runs, then replay equals the board and the board equals the model at every step. The corpus asserts at least 50 clicks per brush and at least 50 repeat clicks.
  *test: test_PropertyTest_SolverHistory_ReplayReproducesTheBoard (in tests/test_puzzle_solver_marking.py, updated)*
- **AC-11:** Given the player page, when the tool group and the hint line are read, then the group's accessible name is "Marking tool" (no "for drags") and the hint no longer says "Click a cell to cycle"; it names each colour brush's sequence and keeps the drag sentence and CARD-186's Maybe sentence.
  *test: TestSolverClickFollowsTheBrush::test_the_page_copy_describes_the_new_click (in tests/test_puzzle_solver_marking.py)*

## Guardrails

- G-1: Drags are unchanged. `dragStroke`, `dragLine` and TestSolverMarking_DragMarksOneLine stay as they are.
- G-2: The history model is unchanged: the last-click memory is not in the history value, undo/redo restore boards only (TestSolverMarking_UndoRedoByStroke, TestSolverHistoryModule::test_history_branches).
- G-3: Keyboard behaviour is unchanged: TestSolverMarking_KeyboardAndLabels stays green (edit only a line that reads the group's accessible name, if any).
- G-4: The solved lock still ignores clicks (TestSolverProgress locked-board tests).
- G-5: No mark sends a request (AC-311, TestSolverMarking_NoRequestPerMark); the marking code still reads no solution (TestSolverMarking_RevealsNoCorrectness).
- G-6: `solver_state.js` stays pure and never contains the substring "import ".
- G-7: CARD-183's hint stroke, CARD-186's Maybe drag, error count and solved rule, and CARD-185's saved state (board, counters, history only — no last-click memory) are unchanged.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-189` (53 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-044 (puzzle player). Its statement says "A single click on a cell always cycles it undecided -> filled -> marked empty -> undecided, whatever tool is selected". AC-303 (TestSolverMarking_ClickCycles) and AC-304 (TestSolverMarking_ClickIgnoresTheSelectedTool) pin that. Both are **superseded for clicks** by this card's AC-1..AC-8. Drags (AC-305/AC-306), undo/redo (AC-307..AC-309) and keyboard (AC-310) stand. · formalized 2026-10-06: FR-044 AC-355..AC-359 (supersede AC-303/AC-304 for clicks)
- **Architect delta needed:** amend FR-044's statement (each brush's click sequence, first vs repeat click, the memory is UI state outside history) and replace AC-303/AC-304. Card-local ACs until then. CARD-186's own card-local note on a "?" cell's click (design (b)) is replaced too.
- **ADR:** ADR-0038 (R2 no request per mark, R4 pure state module). CON-021.
- **Components:** COMP-009 (admin panel), CAP-007 Puzzle play.
- **Trace:** meta/architecture/trace.yml (FR-044 row).

## Design context

- Screen: the puzzle player, `/puzzle/<id>/solve`.
- No new pixels: cells draw as today. What the owner SEES change is the result of a click, plus two copy changes: the tool group's accessible name and the hint line under the board (owner-visible default: the hint wording above).
- Renders: ~/Documents/nonogram-reviews/CARD-189/ (owner visual check before merge). One screenshot strip per brush: a blank cell after clicks 1, 2, 3 and 4 (AC-3), plus a screenshot of the new hint line.

## Worktree notes

- [Origin] Owner's solver test doc 2026-10-05, item 5 ("click order follows the brush"). No IDEA. Supersedes the owner's 2026-10-03 "click cycles, tool drags" decision for clicks only.
- [Owner decision] 2026-10-05 doc sequences. The first draft's stateless table (brush × cell only) gave Black: dark, white, dark. The owner chose the doc's sequences: the player remembers the last click (cell + brush), a repeat click advances the brush's sequence. Resolved.
- [Decisions made in this card] (1) A first click on a cell already in the brush's state advances one step, so every click changes the cell and is one undo step (coordinator's recommendation). (2) The memory lives in `solver.js` `wireMarking` (`lastClick`), not in the pure module; the step is the pure `clickedState(state, tool, repeat)`. (3) Pressing any tool button clears the memory, even the pressed one. (4) `clickStroke` now requires a tool; CARD-186's omitted-tool fallback goes.
- [Facts] Before CARD-186: `solver_state.js` `CYCLE` line 151, `cycled` 153, `clickStroke` 166; `solver.js` header comment line 51, `gesture.tool` at pointerdown line 351, click recorded at line 371; `puzzle_solve.html` tool group label line 50, hint line 80. Line numbers shift after CARD-186/CARD-183; find by name.
- [Tests that pin the old click and must change] tests/test_puzzle_solver_marking.py: module-level `CYCLE` (line 42) and `_Model.click` (line 93) — give `click` a brush and a repeat flag and a literal 32-entry table; `TestSolverMarking_ClickCycles` (line 191: three Black clicks expect F, E, U — still F, E, U as repeat clicks; keep it, it now also proves repeat); `TestSolverMarking_ClickIgnoresTheSelectedTool` (line 243) — rewrite or delete (it pins AC-304, superseded: White/Undecided on a blank cell no longer give F for White; Undecided still gives F); keep `test_exactly_one_tool_is_pressed`; `TestSolverHistoryModule::test_cycle_and_strokes` (line 904: `S.cycled`, three-argument `S.clickStroke`); EC-035 `_RUN_HISTORY` / `_ec_ops` (lines ~1017–1060: click ops have no brush).
- [Conditional touch] tests/test_puzzle_solver_progress.py: most clicks there use the default Black brush on blank or white cells. Black first click keeps blank -> dark, dark -> white, white -> dark (as today). `_solve` clicks the last cell from white with Black: dark either way. `test_a_click_that_cycles_a_wrong_black_to_white_corrects_it` clicks one cell twice with Black: dark, white, as today. Run the file; edit only what the new rule really changes.
- [Conditional touch] tests/test_puzzle_solver_maybe.py (created by CARD-186): its tests of a click on a "?" cell with a colour brush expect black (CARD-186's interim rule). Under this card White gives white and Undecided gives blank. Update those expectations only.
- [Board encoding] Checked against CARD-186: the constant is `MAYBE = "maybe"`, first letter "m", so EC-035's `s[0]` encoding (and `_PURE` in test_puzzle_solver_progress.py) does not collide with u/f/e.
- [Coordination] CARD-186 adds the Maybe tool and state and edits the same three source files; build on its merged version and change only `clickedState`/`clickStroke` in the module. CARD-183 (hint) commits through `commit`, so it clears the memory with no change to its code. CARD-185 (restore on reopen) must not save `lastClick`.
- [AC cross-check] Re-read AC-1..AC-11 against the body. AC-3 matches the sequences table (Undecided on a blank cell: a first click on a cell in the brush's state advances, so dark, white, blank, dark). AC-5/AC-6/AC-8's "first click" cases match the first-click table (white + Black = dark; dark + White = white; blank + Black = dark). Body and ACs agree.
- [Architect 2026-10-06] FR-044 AC-355..AC-359 now formalize this card (AC-303/AC-304 superseded for clicks). When the card replaces TestSolverMarking_ClickCycles / ClickIgnoresTheSelectedTool, the dispatcher updates trace.yml at merge.
