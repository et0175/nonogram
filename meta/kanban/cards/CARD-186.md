# CARD-186: The puzzle player gets a "?" mark and a "?" brush for assumptions

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/186-player-maybe-mark
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (owner's solver test doc 2026-10-05, item 2: a fourth mark drawn as "?", never an error, puzzle not solved while any "?" remains, the "?" tool paints and clicks like the other tools)
**Idea:** —
**Wave:** 34
**Depends on:** CARD-183
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_maybe.py, tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_page.py
**Review score:** 9.0 (2 cycles)
**Started:** 2026-10-05T17:33:38Z
**Closed:** 2026-10-06T02:17:20Z
**Actual:** 1.1d
**Merge commit:** ddfc116
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**
- `static/solver_state.js` has three cell states: `UNKNOWN = "unknown"`,
  `FILLED = "filled"`, `EMPTY = "empty"`, and `CELL_STATES` (line 29) lists
  them. `isBoard`, `withCell`, `dragStroke` and `applyStroke` accept exactly
  `CELL_STATES`.
- A click ignores the tool. `clickStroke(board, row, col)` (line 166) uses
  `cycled(state)`: undecided -> filled -> marked empty -> undecided (`CYCLE`,
  line 151).
- The tool governs drags only. `dragStroke(start, path, tool)` sets every
  covered cell to `tool`.
- `errorCount` (line 297) counts FILLED on a solution-empty cell and EMPTY on
  a solution-filled cell. Nothing else counts.
- `isSolved` (line 312) is true when every cell's "is FILLED" equals the
  solution. A cell that is neither FILLED nor EMPTY on a solution-empty cell
  does not stop a solve.
- `solver.js` `wireMarking` (line 315): the tool is taken at pointerdown
  (`gesture.tool`); on pointerup a click records
  `clickStroke(history.board, ...done.start)` (line 371) with no tool. Reset
  says `aria-disabled` while every cell is UNKNOWN (line 334).
- `templates/puzzle_solve.html` (lines 50–54) has three tool buttons, Black,
  White, Undecided, each `data-player-tool="<state>"` with a
  `.player-swatch[data-state]`. The usage paragraph (line 80) says "Click a
  cell to cycle black, white, undecided."
- `admin.css` draws FILLED as ink (line 422) and EMPTY as a dot (line 423).
  The tool swatches are at lines 442–444.
- CARD-183 (Hint) adds `lineForced`, `hintCell`, `hintStroke`, `hintCount`
  to `solver_state.js`. Its `hintCell` only considers cells that are UNKNOWN
  on the player's board, and returns `null` when no cell is UNKNOWN.

**Target behaviour.**

1. **A fourth cell state.** Add `MAYBE = "maybe"` to `solver_state.js` and
   append it: `CELL_STATES = [UNKNOWN, FILLED, EMPTY, MAYBE]`. It is neither
   dark nor white. `isBoard`, `withCell`, `applyStroke`, `dragStroke`,
   `record`, `undo`, `redo` and `replay` then accept it with no further change.
   Update the module's header comment to name the fourth state.
2. **One click function.** Add a pure, exported
   `clickedState(state, tool)`. It is the only place that decides what a click
   does, so CARD-189 can change the other brushes' order inside it.
   - Tool MAYBE: a cell that is not MAYBE becomes MAYBE; a MAYBE cell becomes
     UNKNOWN (owner rule: "?" -> blank).
   - Any other tool: today's cycle, unchanged. A MAYBE cell is read as blank,
     so it becomes FILLED (`CYCLE` gains `[MAYBE]: FILLED`).
   - `clickStroke(board, row, col, tool)` returns
     `makeStroke([[row, col]], clickedState(cellAt(board, row, col), tool))`.
     When `tool` is omitted, it behaves exactly as today (EC-035's corpus and
     CARD-161's module tests call it with three arguments).
   - `solver.js` passes the tool taken at pointerdown: `clickStroke(history.board, ...done.start, done.tool)`.
3. **Drags.** The MAYBE tool paints "?" along the drag line, like any tool.
   No code change beyond step 1: `dragStroke` takes any cell state. A drag
   with another tool over "?" cells overwrites them.
4. **Error count.** "?" never counts. `errorCount` already counts only FILLED
   and EMPTY. Keep it so, and say so in its comment.
5. **Solved.** `isSolved` returns false while any cell is MAYBE. Otherwise
   it is unchanged. So a board whose blacks match the solution but holds one
   "?" on a solution-empty cell is not solved, is not locked, and shows no
   banner. Removing the last "?" (click with the "?" tool, a drag, undo) solves it.
6. **Undo, redo, reset.** A "?" click or drag is one stroke and one undo
   step, like any other. Reset clears "?" marks (every cell to UNKNOWN). A
   board holding only "?" marks is not blank, so Reset is available
   (`refresh`'s every-UNKNOWN test already gives this).
7. **The hint (CARD-183) reads "?" as undecided and may overwrite it.**
   - In `hintCell`, a candidate cell is one whose state is UNKNOWN or MAYBE,
     not only UNKNOWN. That applies to the deducible pick, the fallback pick
     and the `null` case ("no cell is UNKNOWN or MAYBE").
   - The knowns stay as CARD-183 built them: only correct FILLED and EMPTY
     marks are known, so a "?" is never a known.
   - `lineForced` treats any state other than FILLED and EMPTY as unknown.
   - So `hintCell(board, ...)` gives the same cell, state and `deduced` as
     `hintCell` on the same board with every MAYBE replaced by UNKNOWN.
   - The hint stroke sets the cell to its solution state. Undo brings the "?"
     back. The Hint button's `aria-disabled` follows the widened `null` case.
8. **The page.**
   - Add a fourth tool button after Undecided:
     `data-player-tool="maybe"`, visible label **Maybe**, with a
     `.player-swatch[data-state="maybe"]` showing "?" (`aria-hidden="true"`,
     like the other swatches). Its accessible name is "Maybe". It is a toggle
     with `aria-pressed`, exactly one tool pressed, as today.
   - Draw a MAYBE cell as a "?" glyph: `.player-cell[data-state="maybe"]::after`
     with `content: "?"`, sized from `--player-cell` (about 0.6 × the cell,
     like the clue numbers), weight 600, centred, in a colour token with at
     least 4.5:1 contrast on `--grid-paper`. Tokens only, no literal colour
     (`test_the_stylesheet_uses_tokens_not_literals`). It must stay legible at
     the CARD-182 phone minimum of 24 px cells.
   - Extend the usage paragraph (`#puzzle-player-hint`, id and class kept)
     with one sentence: "With Maybe, a click marks ? and a second click clears it."
   - Update the comments that state the rule: `solver.js` header ("MARKING",
     "tools") and the template's header comment.

**Owner-visible defaults this card picks (say them at review, see Design context):**
- (a) The tool is labelled "Maybe", with a "?" swatch, placed after Undecided.
- (b) A click on a "?" cell with Black, White or Undecided selected makes it
  black (blank's next step in today's cycle). CARD-189 will set this by its
  first-click rule anyway; this card only needs a defined answer.
- (c) The "?" glyph's size, weight and colour token.
- (d) The extra sentence in the usage paragraph.

## Acceptance criteria

- **AC-1:** Given `solver_state.js`, when `CELL_STATES`, `MAYBE`, `isBoard` and `withCell` are read, then `CELL_STATES` is `["unknown", "filled", "empty", "maybe"]`, a frozen board holding "maybe" cells is a board, and `withCell(board, r, c, MAYBE)` sets exactly that cell.
  *test: TestSolverMaybeModule_IsAFourthState (in tests/test_puzzle_solver_maybe.py)*
- **AC-2:** Given every pair of (cell state, tool) over the four states, plus the tool omitted, when `clickedState` and `clickStroke` run, then the result matches the table written in the test: tool MAYBE gives MAYBE for every non-MAYBE cell and UNKNOWN for a MAYBE cell; any other tool, or none, gives UNKNOWN -> FILLED -> EMPTY -> UNKNOWN and MAYBE -> FILLED.
  *test: TestSolverMaybeModule_ClickedStateTable (in tests/test_puzzle_solver_maybe.py)*
- **AC-3:** Given the 15×15 player page with Maybe selected, when one undecided cell is clicked twice by a real mouse, then it reads "maybe" after the first click and "unknown" after the second, and no other cell changes. A black cell clicked once with Maybe reads "maybe". A "?" cell clicked once with Black selected reads "filled".
  *test: TestSolverMaybe_ClickWithTheMaybeTool (in tests/test_puzzle_solver_maybe.py)*
- **AC-4:** Given a board with marks in row 2, when a drag with Maybe runs along row 2 from column 3 to column 7, then exactly those five cells read "maybe" whatever they held; a following White drag over columns 5–6 makes those two "empty".
  *test: TestSolverMaybe_DragPaintsMaybe (in tests/test_puzzle_solver_maybe.py)*
- **AC-5:** Given a seeded corpus of at least 200 boards per shape over (10, 10), (15, 10) and (10, 25), each cell drawn from all four states with at least 20% "?", when `errorCount` runs, then it equals a Python oracle that counts only FILLED on solution-empty and EMPTY on solution-filled. The minimum counts are asserted in the test.
  *test: PropertyTest_SolverMaybe_ErrorCountNeverCountsMaybe (in tests/test_puzzle_solver_maybe.py)*
- **AC-6:** Given EC-036's oracle extended by "and no cell is MAYBE", over the AC-5 corpus plus at least 50 boards that are solved except for one "?" on a solution-empty cell, when `isSolved` runs, then it equals the oracle on every board and is false on all 50. The minimum counts are asserted in the test.
  *test: PropertyTest_SolverMaybe_NotSolvedWhileAnyMaybe (in tests/test_puzzle_solver_maybe.py)*
- **AC-7:** Given a page board, set by `setBoard`, with every solution-filled cell FILLED and one "?" on a solution-empty cell, when it is read, then no banner shows, the board is not locked and the error count reads 0; when that "?" is clicked with Maybe selected, the solved banner shows and the board locks.
  *test: TestSolverMaybe_BlocksTheSolvedState (in tests/test_puzzle_solver_maybe.py)*
- **AC-8:** Given a seeded sequence of at least 500 strokes mixing clicks with each of the four tools, drags with each of the four tools, resets, undos and redos, with at least 100 strokes that set MAYBE, when the history is replayed after every step, then replaying `done` from the blank board reproduces the current board. The minimum counts are asserted in the test.
  *test: PropertyTest_SolverMaybe_ReplayReproducesTheBoard (in tests/test_puzzle_solver_maybe.py)*
- **AC-9:** Given one "?" click and one "?" drag on the page, when Undo is pressed twice and Redo twice (buttons, then Ctrl/Cmd+Z), then each undo removes one stroke's "?" marks and each redo puts them back.
  *test: TestSolverMaybe_UndoRedo (in tests/test_puzzle_solver_maybe.py)*
- **AC-10:** Given a page board with only "?" marks, when the controls are read, then Reset is not `aria-disabled`; when Reset and "Clear board" are pressed, then every cell is "unknown".
  *test: TestSolverMaybe_ResetClearsMaybe (in tests/test_puzzle_solver_maybe.py)*
- **AC-11:** Given a seeded corpus of at least 200 boards per shape over (10, 10), (15, 10) and (30, 30) mixing correct, wrong, undecided and "?" cells, when `hintCell` runs on each board and on the same board with every "?" replaced by UNKNOWN, then both calls return the same cell, state and `deduced`. The corpus has at least 30 boards where the returned cell was "?", and at least 10 where every non-correct cell is "?". The minimum counts are asserted in the test.
  *test: PropertyTest_SolverMaybe_HintReadsMaybeAsUndecided (in tests/test_puzzle_solver_maybe.py)*
- **AC-12:** Given a page board where every cell is correct except some "?" cells, when Hint is pressed, then Hint was not `aria-disabled`, exactly one "?" cell takes its solution state, "Hints: 1" shows, and Undo brings that "?" back with "Hints: 0".
  *test: TestSolverMaybe_HintMayOverwriteMaybe (in tests/test_puzzle_solver_maybe.py)*
- **AC-13:** Given the 30×30 deep-row-clue page at 390×844 (cells at the CARD-182 24 px floor) and the 15×15 page at 1440×900, when a "?" cell is measured, then its `::after` content is "?", its computed font size is at least 12 px and at least 0.5 × the cell side, its glyph box lies inside the cell, and its colour has at least 4.5:1 contrast on the cell's background.
  *test: TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell (in tests/test_puzzle_solver_maybe.py)*
- **AC-14:** Given the player page, when the tools are inspected and operated from the keyboard, then a button with accessible name "Maybe" exists, Tab reaches it between Undecided and Undo, Enter and Space each select it (`aria-pressed="true"`, the others false), and its swatch is `aria-hidden`.
  *test: TestSolverMaybe_ToolKeyboardAndLabel (in tests/test_puzzle_solver_maybe.py)*
- **AC-15:** Given the loaded page, when 10 "?" clicks and drags are made, then the browser issues no network request and stores nothing (localStorage and sessionStorage stay empty).
  *test: TestSolverMaybe_NoRequestPerMark (in tests/test_puzzle_solver_maybe.py)*
- **AC-16:** Owner render: a 15×15 board with black, white and "?" marks and the Maybe tool pressed, at desktop width and at 390 px; plus the "blacks match but one ? left" board (not solved) next to the same board solved. Saved in ~/Documents/nonogram-reviews/CARD-186/.
  *test: review-lens (owner visual check of the renders)*

## Guardrails

- G-1: Every existing player test stays green. Only two edits to them are allowed, both forced by the new state: `CONTROLS` in `tests/test_puzzle_solver_marking.py` (line 514) gains "Maybe" after "Undecided", and the `"states"` pin in `tests/test_puzzle_solver_page.py` (line 956) gains "maybe". Nothing else in `test_puzzle_solver_page.py`, `test_puzzle_solver_marking.py`, `test_puzzle_solver_progress.py`, CARD-182's `test_puzzle_solver_phone.py` or CARD-183's `test_puzzle_solver_hint.py` is edited. That keeps EC-035 (`PropertyTest_SolverHistory_ReplayReproducesTheBoard`), EC-036, EC-037, AC-303/AC-304 (click cycle with Black/White/Undecided), AC-310, AC-311 and AC-319 pinned as they are.
- G-2: FR-044 is unchanged for the three existing tools: clicks with Black, White or Undecided on undecided, filled and empty cells cycle as today, drags paint as today, the error-count definition and the lock are unchanged. Only the "?" state and tool are new.
- G-3: ADR-0038/R4: `MAYBE`, `clickedState` and the `isSolved` change live in `solver_state.js`, which keeps no DOM, globals, `import ` or colour literal (`test_the_state_module_touches_no_dom`, `test_the_scripts_carry_no_colour_literals`).
- G-4: ADR-0038/R2 and R3: no request per mark, and the payload shape is unchanged (`test_the_payload_has_exactly_the_documented_shape`).
- G-5: CON-021 / CON-017: no "?" mark is persisted or sent anywhere by this card.
- G-6: CARD-183's hint is unchanged on boards with no "?" (its tests pass unedited). CARD-182's cell sizing is unchanged: no edit to `--player-cell`, `--player-cell-min` or `--player-cell-max`.
- G-7: COMP-005 (`src/nonogram/solver/`) is not modified.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-186` (52 rules). A projection — fix the source artifact, never this list._

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
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
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

- **FR-044** (puzzle player, AC-296..AC-323, EC-035..EC-037). Its statement names three tools and "a single click ... always cycles ... whatever tool is selected". AC-304 says the same, AC-310 lists three tools, and EC-036's solved definition has no "?" clause. This card adds card-local ACs only. An architect delta is needed (see Worktree notes).
- **ADR-0038** R1 (plain JS/CSS, tokens), R2 (no request per mark), R3 (payload clues), R4 (pure state module), R6 (solution only in the admin player).
- **CON-021**, CON-017, CON-015/CON-016.
- Components: COMP-008 area (admin panel, `src/nonogram/admin/`). TERM-037 (puzzle player), TERM-038 (error count), TERM-039 (stroke).
- Trace: owner's solver test doc 2026-10-05 item 2 → CARD-186 → FR-044 (extension, no AC id yet).

## Design context

- **Screen:** the admin puzzle player, `/puzzle/<id>/solve`: the tool group (a fourth button), the board ("?" cells) and the usage paragraph.
- **Owner-visible defaults:** (a)–(d) in "What to implement": the "Maybe" label and place, a "?" cell going to black on a non-Maybe click, the glyph's look, and the usage sentence. The owner confirms or overrides them from the renders before merge.
- **Renders:** ~/Documents/nonogram-reviews/CARD-186/ (owner visual check). PNGs at desktop width and at 390 px (24 px cells, CARD-182): the toolbar with Maybe pressed, a board mixing black, white and "?", and the "one ? left" board beside its solved form. Check the four-button tool group wraps cleanly at 390 px next to CARD-183's Hint button.

## Worktree notes

- [Origin] Roadmap wave 1: owner's solver test doc ("Solver - test", 2026-10-05), item 2, owner decision: a fourth mark drawn as "?", neither dark nor white, never an error, not solved while any "?" remains, the "?" tool paints (drag) and clicks like the other tools. No IDEA id.
- [Spec] Card-local ACs. Raise an architect delta for FR-044 at the next pass: the statement (requirements.yml ~line 3692–3696: "A single click ... always cycles ... whatever tool is selected", "The selected tool (filled, empty or undecided) governs drags"; ~line 3704: the solved definition), AC-304, AC-310's tool list, and EC-036 ("... and no cell is marked ?"). Add ACs mirroring AC-2..AC-15. Do not edit meta/ from the card.
- [Order] Depends on CARD-183. Build on main after CARD-183 (and CARD-182) merge. Read CARD-183's merged `hintCell` before step 7: its card says candidates are "UNKNOWN on the player's board" and the fallback is "the first UNKNOWN cell". Widen exactly those predicates to UNKNOWN-or-MAYBE (a small helper, e.g. `isUndecided(state)`), and the `null` / disabled case with them.
- [Facts] The state's string must not start with "u", "f" or "e". EC-035's test (`_RUN_HISTORY`, test_puzzle_solver_marking.py ~line 1026) and others compress a board as `s[0]` per cell, and `_PURE` (test_puzzle_solver_progress.py ~line 737) maps letters u/f/e. "maybe" gives "m". The new tests use the same letter scheme with "m".
- [Facts] Two existing tests must change, and only these (G-1): `CONTROLS` (test_puzzle_solver_marking.py line 514) is the exact Tab order asserted by `test_each_control_has_a_name_and_is_reachable_by_tab`, so "Maybe" goes after "Undecided". CARD-183 will also edit `CONTROLS` (adds "Hint"); rebase on its list. `test_puzzle_solver_page.py` line 956 pins `"states": ["unknown", "filled", "empty"]`; append "maybe".
- [Facts] `clickStroke` keeps working with three arguments: EC-035's `_RUN_HISTORY` and `TestSolverHistoryModule.test_cycle_and_strokes` call `S.clickStroke(board, r, c)`. Omitted tool = today's cycle.
- [Facts] `isSolved`'s only change is an early false on any MAYBE. The existing `TestSolverProgressModule.CASES` and EC-036/EC-037 corpora contain no "?" and stay valid.
- [Facts] Browser harness: `browser_page`, `live`, `_open` (test_puzzle_solver_page.py ~561–598); `_cell`, `_states`, `_button`, `_tool`, `_drag`, GRID 15×15 (test_puzzle_solver_marking.py). The pure-module pattern is `page.evaluate("async () => { const S = await import('/static/solver_state.js'); ... }")`. For AC-13 reuse CARD-182's phone setup (390×844, deep-row-clue 30×30). Mark browser tests `@pytest.mark.browser`.
- [Facts] No new static file, so the wheel check in `TestPlayerAssets` and `pyproject.toml` package-data stay as they are.
- [Future] CARD-189 (item 5) changes the other brushes' first click. It edits only `clickedState`. Its rule for the "?" brush ("?" -> blank) is the one this card implements. The tool group's `aria-label` "Marking tool for drags" becomes inaccurate once every brush governs clicks; CARD-189 should rename it. This card leaves it, since only Maybe's click follows the tool here.
- [Future] The item-1 persistence card (localStorage) must save and restore "maybe" cells; `isBoard` accepts them once this card lands. The item-3 "% solved" and item-4 clue-circle cards must treat "?" as not correct and not white.
- [Conflict] CARD-182 and CARD-183 edit `admin.css` (player block ~lines 433–480), `solver.js` and `puzzle_solve.html`. Keep this card's CSS to the "?" glyph rule, the "maybe" swatch rule and nothing in the sizing variables.
- [AC cross-check] Re-read all ACs against "What to implement". AC-2's table, AC-3 and point 2 agree on MAYBE -> FILLED for non-Maybe tools and "?" -> blank for Maybe; AC-6/AC-7 match point 5; AC-11/AC-12 match point 7 (candidates widened, knowns unchanged). The first draft of AC-14 did not say where Maybe sits in Tab order, so it now names "between Undecided and Undo", matching point 8 and the `CONTROLS` edit.
- [Note 2026-10-05] CARD-189 (wave 35, owner decision "follow the doc's sequences") later replaces this card's click rule for "?" cells with a colour brush (White → white, Undecided → blank) and removes the no-tool fallback. Implement this card's rule as drafted; keep `clickedState(state, tool)` the single hook CARD-189 extends.
- [Env] forge 2026.8.17
- [Implementation 2026-10-05] What changed:
  - `static/solver_state.js`: `MAYBE = "maybe"`, `CELL_STATES = [UNKNOWN, FILLED, EMPTY, MAYBE]` (header comment names the fourth state). New pure, exported `clickedState(state, tool)` — the single click hook CARD-189 extends: tool MAYBE gives MAYBE for a non-"?" cell and UNKNOWN for a "?"; any other tool, or none, cycles (`CYCLE` gains `[MAYBE]: FILLED`). `clickStroke(board, row, col, tool)` uses it; three-argument calls cycle as before. `errorCount` unchanged (its comment now says UNKNOWN and MAYBE never count). `isSolved` gets one early `false` while any cell is MAYBE. `hintCell`: candidates are `isUndecided(state)` (UNKNOWN or MAYBE) for the deducible pick, the fallback and the null case; knowns unchanged (a "?" never equals the solution's state, so it is never a known). Circles code untouched.
  - `static/solver.js`: a click records `clickStroke(history.board, ...done.start, done.tool)` (tool taken at pointerdown); header MARKING/pointer/tools comments updated. Hint `aria-disabled` uses `nextHint() === null`, so it follows the widened null case (AC-12 checks Hint is enabled on a board whose only non-correct cells are "?").
  - `templates/puzzle_solve.html`: fourth tool button after Undecided (`data-player-tool="maybe"`, label "Maybe", `.player-swatch[data-state="maybe"]` aria-hidden); usage paragraph gains "With Maybe, a click marks ? and a second click clears it."; header comment states the rule.
  - `static/admin.css`: `.player-cell[data-state="maybe"]::after` ("?", 0.6 × `--player-cell`, weight 600, `--color-accent`); `.player-swatch[data-state="maybe"]::after` ("?" in `--color-accent`, `--text-xs`, weight 600); and `.player-toolbar .player-tool { padding-left/right: var(--space-2) }` — see SCOPE note below.
  - Tests: new `tests/test_puzzle_solver_maybe.py` (AC-1..AC-15 named tests plus `PropertyTest_SolverMaybe_CirclesReadMaybeAsUndecided`). The two G-1 edits only: `CONTROLS` gains "Maybe" after "Undecided" (test_puzzle_solver_marking.py), `"states"` pin gains "maybe" (test_puzzle_solver_page.py).
- [Layout] Adding the fourth tool button made `test_the_banner_takes_the_tools_place_and_the_board_does_not_move` (test_puzzle_solver_progress.py, G-1) fail at the default 1280 × 720 viewport: the toolbar went to two rows (the Hints counter wrapped), so hiding the tools when solved moved the board up 48 px. Fix inside this card's CSS, no test edited: tool buttons take `--space-2` side padding instead of Bootstrap's 0.75rem (all four tools, owner-visible, slightly narrower buttons; height unchanged). Mutant M21 (drop that rule) re-fails the guarded test. Only the 1280 × 720 case is tested. Measured at 1280 before the fix: toolbar 980 px wide, the four tools 445 px, 3 px too many for the Hints counter to stay on the first row; the padding saves 32 px. At somewhat narrower desktop widths the toolbar may wrap where main's did not (an estimate, not tested).
- [Measured] AC-13: the "?" glyph is 14.4 px on the 24 px phone cell (30×30 at 390×844) and 16.8 px on the 28 px cell (15×15 at 1440×900); its rendered pixels (screenshot diff, undecided → "?") lie inside the cell on both axes at both sizes; `--color-accent` (rgb 31,95,91) on the cell background `--grid-paper` (rgb 255,253,248) measures 7.26:1.
- [Mutants] each applied alone, named tests run, then restored (scratch runner, not committed):
  - M1 isSolved: drop the MAYBE early false → `PropertyTest_SolverMaybe_NotSolvedWhileAnyMaybe`, `TestSolverMaybe_BlocksTheSolvedState`
  - M2 clickedState: "?" with Maybe returns MAYBE (not UNKNOWN) → `TestSolverMaybeModule_ClickedStateTable`, `TestSolverMaybe_ClickWithTheMaybeTool::test_two_clicks_mark_then_clear`
  - M3 hintCell candidate predicate back to `!== UNKNOWN` → `PropertyTest_SolverMaybe_HintReadsMaybeAsUndecided`, `TestSolverMaybe_HintMayOverwriteMaybe`
  - M4 drop `[MAYBE]: FILLED` from CYCLE → `ClickedStateTable`, `test_a_maybe_cell_clicked_with_another_tool_reads_filled[Black/White/Undecided]`, `PropertyTest_SolverMaybe_ReplayReproducesTheBoard`
  - M5 solver.js drops `done.tool` → all `TestSolverMaybe_ClickWithTheMaybeTool`, `TestSolverMaybe_ToolKeyboardAndLabel::test_enter_and_space_select_it[Enter/Space]`
  - M6 circles walkIn: a "?" closes a run → `PropertyTest_SolverMaybe_CirclesReadMaybeAsUndecided`
  - M7 circles rule B (edge): a "?" closes a run → same
  - M8 circles `[0]` clue: a "?" reads white → same
  - M9 errorCount counts "?" on solution-filled → `PropertyTest_SolverMaybe_ErrorCountNeverCountsMaybe`
  - M10 errorCount counts "?" on solution-empty (edge) → same
  - M11 CELL_STATES without MAYBE → `TestSolverMaybeModule_IsAFourthState`
  - M12 clickedState: drop the bad-state guard under the Maybe tool → `ClickedStateTable`
  - M13 Reset disabled on a "?"-only board → `TestSolverMaybe_ResetClearsMaybe`
  - M14 glyph colour `--color-border` → `TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell[30x30@390, 15x15@1440]`
  - M15 glyph 0.45 × cell → same
  - M16 glyph translateY(80%) (y axis) → same; M17 glyph translateX(60%) (x axis) → same
  - M18 swatch not aria-hidden → `TestSolverMaybe_ToolKeyboardAndLabel::test_name_and_swatch`
  - M19 Maybe button moved after Undo → `test_tab_reaches_it_between_undecided_and_undo`
  - M20 a commit writes localStorage → `TestSolverMaybe_NoRequestPerMark`
  - M21 compact tool padding removed → `test_puzzle_solver_progress.py::...::test_the_banner_takes_the_tools_place_and_the_board_does_not_move`
  All 21 killed.
- [Owner default] (a) Tool labelled "Maybe" with a "?" swatch, placed after Undecided — implemented as drafted.
- [Owner default] (b) A click on a "?" cell with Black, White or Undecided makes it black — implemented as drafted.
- [Owner default] (c) "?" glyph: 0.6 × the cell side, weight 600, `--color-accent` — implemented as drafted.
- [Owner default] (d) Usage sentence "With Maybe, a click marks ? and a second click clears it." — implemented as drafted.
- DESIGN-REGISTER: player tool button — Maybe (unpressed / pressed, same states as Black/White/Undecided) — --color-accent, --color-accent-tint (pressed, existing rule), --space-2 side padding (all four tools)
- DESIGN-REGISTER: player swatch — "?" (data-state="maybe") — --grid-paper, --color-border-strong, --color-accent, --text-xs
- DESIGN-REGISTER: player cell — "?" glyph (data-state="maybe") — --grid-paper, --color-accent, --player-cell (font-size 0.6 ×), weight 600
- [Renders] ~/Documents/nonogram-reviews/CARD-186/: `mixed-board-maybe-pressed-1440.png`, `mixed-board-maybe-pressed-390.png` (15×15, black/white/"?" marks, Maybe pressed; 24 px cells at 390), `one-maybe-left-not-solved-1440.png`, `one-maybe-left-solved-1440.png`, `toolbar-before-main-390.png` / `toolbar-after-390.png`, `toolbar-before-main-1440.png` / `toolbar-after-1440.png` (before = main's static files and template, served through Playwright routes). At 390 the four tools wrap to two rows (Maybe alone on the second), above Undo/Redo/Reset and Hint.
- SCOPE+ none (every change is inside Touches). Within admin.css, beyond the "?" glyph and swatch rules, one extra rule (tool padding) was needed to keep G-1's banner test green — see [Layout].
- [For the architect delta] FR-044's statement, AC-304, AC-310's tool list and EC-036 still need the "?" amendment listed in [Spec]; nothing under meta/ was edited by this card beyond these notes.
- [Scope] src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_maybe.py, tests/test_puzzle_solver_page.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Build gate] PASSED (full, 686s) — 6489 passed, 9 skipped
- [Scope gate] cycle 1: IN_SCOPE — 7 files, all inside Touches; no guardrail hits (nothing under src/nonogram/solver/, no other player test file, no sizing variable)
- [Review 1/3] Score: 8.0 — crit: 0, imp: 1 (F-001, pending adversarial verification)
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: 52/52 card rules have a verdict line (11 ✓, 41 ⚠, 0 ✗)
- [Adversarial] F-001 CONFIRMED — independent sweep: main dy 0 / branch dy −44 px at 1180–1240 px (h 900); both −44 at 1100–1160 (pre-existing on main), both 0 at ≥1260
- [Review 1/3] confirmed after adversarial: crit 0, imp 1 → fix cycle 1
- [Fix cycle 1, F-001 2026-10-05] Supersedes the mechanism in [Layout] (that note stays as history). Measured the board jumping on the solving click across widths (new `TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth`, 960..1480 step 20 at height 900 plus 390 × 844, board box x and y before/after, the last cell scrolled into view before measuring so the click itself scrolls nothing). Before this fix, on the branch: moved at 960–1020 (−2.8 px), 1040–1080 (−46.8), 1100–1240 (−44) and 390 (+0.4). Main's admin.css + template (branch solver.js) measured with the same test: moved at 960–1000 (−2.8), 1040–1160 (−44) and 390 (−0.8). After: 0 at all 28 widths.
  - What changed: the cause was `.player-toolbar.is-solved .player-tools { display: none }` — removing the tools from layout changed the toolbar's row structure wherever the tools shared a wrapped row. Now (template) the tools and a new `.player-solved-box` wrapping `#puzzle-player-solved` sit in `.player-slot`, one CSS grid cell shared by both (`grid-area: 1 / 1`); while solved the tools are `visibility: hidden` (keep their box, not focusable, not in the accessibility tree). `.player-solved-box` has `contain: inline-size` (the banner adds nothing to the slot's width) and `align-self: center` (centred down the tools' box, within 1 px — matters at 390 where the tools are two rows); the banner gets `overflow-wrap: anywhere` (breaks a name with no spaces); `.player-solved .icon` gets `flex: none` (a wrapping banner squeezed the check icon to a sliver — seen in the long-name render). A banner taller than the tools' box (a long name) makes the row taller and moves the board — declared, not hidden: `TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth` claims only width/overlap/icon for 120-character names (words and one unbroken token) at 1440, 1200, 390.
  - Owner-visible: in the solved state Undo/Redo/Reset/Hint now stay where they were (before, they slid left into the tools' place next to the banner); a long name wraps inside the tools' width instead of spanning the row. The unsolved toolbar is unchanged.
  - The padding rule `.player-toolbar .player-tool { padding-left/right: var(--space-2) }` is KEPT, with a new job: it keeps the four tools, history and both counters on one toolbar row at 1280 × 720 (new `TestSolverMaybe_FourToolsKeepOneToolbarRowAt1280`). Removing it no longer moves the board, but at 1280 × 720 the toolbar then wraps and the board's last row crosses the viewport bottom by a few px, so the G-1 banner test's click on the bottom-right filled cell scrolls the page 4 px (measured: scrollY 0 → 4, board y unchanged in document coordinates) and that test, which compares viewport boxes, fails. So M21's old explanation ("the banner moves the board at 1280") no longer applies; M21 now kills via the one-row test and the scroll artefact in the G-1 test. At 1180–1259 the toolbar still wraps (Hints on a second row), solved or not, and the board no longer moves there.
  - `TestSolverMaybe_HiddenToolsAreOutOfReachWhenSolved`: solved, no tool is a button by role, focus() does not take, Tab reaches Reset without passing a tool.
  - Declarations corrected: admin.css Progress block comment (no longer "never moves"; points at the .player-slot comment with the tested widths); new .player-slot comment; the padding rule's comment (new job); template header Progress paragraph; solver.js PROGRESS "solved" bullet. G-1 respected: no existing test file edited.
- [Mutants F-001] applied alone to admin.css, the new tests + the G-1 banner test run, restored (scratch runner, not committed):
  - MA tools `display: none` again → sweep, LongName ×6, G-1 banner test
  - MB drop `contain: inline-size` → LongName at 1440/1200 (both names)
  - MC drop the visibility rule → sweep, OutOfReach, G-1 banner test
  - MD drop `grid-area: 1 / 1` → sweep, G-1 banner test
  - ME drop `overflow-wrap: anywhere` → LongName one-token ×3
  - MF drop `.player-slot { display: grid }` → sweep, G-1 banner test
  - MG (= M21) drop the tool padding → OneToolbarRowAt1280, G-1 banner test
  - MH `align-self: start` → sweep (centring at 390)
  - MI `opacity: 0` instead of `visibility: hidden` → sweep, OutOfReach, G-1 banner test
  - MJ drop `flex: none` on the icon → LongName ×6
  All 10 killed. (A `max-width: 100%` on the banner was tried and dropped: redundant with overflow-wrap, no test could tell it apart.)
- DESIGN-REGISTER: player SolvedBanner (CARD-162) — supersedes its placement: shown in the tools' box (.player-slot, tools visibility: hidden), centred down it; width up to the tools' width, a longer name wraps (overflow-wrap: anywhere); check icon flex: none — tokens unchanged (--color-success, --color-success-tint, --radius-control, --space-2, --space-3, --control-h)
- DESIGN-REGISTER: player tool button padding (--space-2 side padding, all four tools) — line above stands; its reason is now the one-row toolbar at 1280 × 720, not the banner.
- [Renders F-001] ~/Documents/nonogram-reviews/CARD-186/: new `solved-toolbar-1200.png` / `unsolved-toolbar-1200.png`, `solved-toolbar-390.png` / `unsolved-toolbar-390.png` (same rows before and after solving), `solved-toolbar-long-name-1440.png`, `solved-toolbar-long-name-390.png` (120-character name wrapping inside the tools' width; at 390 it is taller than the tools' box, so that row grows); all earlier renders regenerated (`one-maybe-left-solved-1440.png` shows history staying in place).
- [Fix 1] FIXED F-001 — pre-gate: named tests 9 passed (BoardDoesNotMoveOnSolveAtAnyWidth, LongNameBannerWrapsInsideTheToolsWidth, FourToolsKeepOneToolbarRowAt1280, HiddenToolsAreOutOfReachWhenSolved)
- [Fix 1] declarations: 4 updated (comments admin.css/template/solver.js, card notes + DESIGN-REGISTER), 0 confirmed, 0 none
- [Build gate] PASSED (full, 712s) — 6498 passed, 9 skipped
- [Scope gate] cycle 2: IN_SCOPE — same 7 files (fix delta uncommitted: admin.css, solver.js, puzzle_solve.html, test_puzzle_solver_maybe.py); no guardrail hits
- [Review 2/3] Score: 9.0 — crit: 0, imp: 0 (confirmation mode; F-001 ✓ resolved; minors F-002/F-003/F-004 open)
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: 52/52 card rules named (11 ✓, 41 ⚠ incl. carried, 0 ✗)
- [Review 2/3] Score: 9.0 ✓ threshold reached + no critical/important
- [Review 2/3] mutation check: 10/10 killed (K1–K10), tree restored
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0038/R2, ADR-0038/R4, ADR-0038/R3)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-1..AC-15 demonstrated — tests/test_puzzle_solver_maybe.py 34 passed in 67.55s (each AC's named test PASSED; property ACs assert their minimum counts); AC-16 demonstrated — renders mixed-board-maybe-pressed-1440/390, one-maybe-left-not-solved-1440, one-maybe-left-solved-1440 present (owner look pending pre-merge); G-1 demonstrated — page/marking/progress/phone/hint 215 passed, diff = the two allowed lines only; G-2 demonstrated (FR-044 tests unedited, green; AC-2 table); G-3 demonstrated — test_the_state_module_touches_no_dom, test_the_scripts_carry_no_colour_literals PASSED; G-4 demonstrated — payload shape [memory,sqlite] + TestSolverMarking_NoRequestPerMark PASSED (6 passed); G-5 demonstrated (AC-15 storage empty, no send path); G-6 demonstrated (hint file unedited/green, no --player-cell* definition change); G-7 demonstrated (no diff under src/nonogram/solver/)
- [Docs] forge:readme: changed dirs src/nonogram/admin/static, src/nonogram/admin/templates, tests — no README in the admin dirs; tests/README.md does not catalogue the player test files (none of CARD-161..188's) — skipped, current
- [Commit] success commit 3cb98bd (on top of implementation 2ffec96) — explicit pathspecs; diff vs main: 7 files, +1189/−40
- [Owner check] pre-merge, from ~/Documents/nonogram-reviews/CARD-186/: defaults (a)–(d) as drafted, plus three owner-visible layout changes not in (a)–(d) (review F-003/F-004, Minor): (e) all four tool buttons have --space-2 side padding (narrower than main's three); (f) when solved, Undo/Redo/Reset/Hint stay in place and the banner sits in the tools' box, a long name wraps inside it — names of ~40+ characters move the board 13 px (100 chars: 38 px) at desktop widths, where main moved it only from 50–60 chars at 1280/1440; (g) at 1180–1259 px 'Hints: 0' sits alone on a second toolbar row, solved or not
- [Merge gate] branched from adec591 (= main at merge); pipeline full suite after the fix 6498 passed, 9 skipped (same tree, not re-run). Owner: "merge now, check later" (renders incl. toolbar changes e–g in ~/Documents/nonogram-reviews/CARD-186/). Merged ddfc116.
