# CARD-161: Mark cells in the solver: tools, click cycle, drag, undo and redo

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/161-solver-marking-undo-redo
**Worktree:** —
**Source:** owner design doc "Nonograms - Print layout" (Google Doc 1pJKF2qX6mC9qw4Cf9Nv3hblTDmtoHwP5Tb8wzK1_WqM), section "Online solver"
**Idea:** —
**Wave:** 31
**Depends on:** CARD-160
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_marking.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-10-03T11:41:24Z
**Closed:** 2026-10-03T13:30:16Z
**Actual:** 0.2d
**Merge commit:** 8b485cc
**Blocked by:** —

## What to implement

The marking controls the owner's document lists, kept "as simple as
possible, similar to puzzle-nonograms.com". The document says no more
options than these for now.

1. **Tool picker:** three tools: **black** (filled), **white** (marked
   empty, drawn as a dot or a small cross), and **undecided** (clears a
   cell). Exactly one tool is active. Pick it by button and by keyboard.
2. **Click cycle in the grid:** clicking a cell cycles it: 1st click
   black, 2nd click white, 3rd click clear. This is independent of the
   active tool, as the document describes.
   **Owner answer (2026-10-03, FR-044 AC-303/304):** a click always cycles,
   whatever tool is selected. The selected tool governs drags.
3. **Drag to mark a region:** press on a cell and drag, and every cell
   passed over takes the active tool's state. Constrain a drag to the row
   or column it started in, as the reference site does; that's the usual
   nonogram behaviour and avoids smearing diagonals. One drag is one
   history step.
4. **Undo and redo:** buttons plus Ctrl/Cmd+Z and Shift+Ctrl/Cmd+Z. Undo
   reverts a whole stroke (one click, or one drag). A new mark after an
   undo drops the redo stack.
5. **Touch:** tap and drag must work on a tablet-sized touch screen. This
   is the cheapest moment to get it right, since phones are where printed
   QR codes will land later.

State changes go through CARD-160's pure state module (apply stroke,
undo, redo), so the logic is testable without a browser. Rendering only
reflects state.

## Acceptance criteria

_Verbatim from FR-044 in meta/architecture/requirements.yml (architect delta 2026-10-03)._

- **AC-303** (happy): *Given* an undecided cell on the player page with the filled tool selected, *when* the cell is clicked three times, *then* its state goes filled, then marked empty, then undecided, drawn black, then as a dot or small cross, then blank.
  *test: TestSolverMarking_ClickCycles*
- **AC-304** (boundary): *Given* an undecided cell with the empty tool selected, *when* the cell is clicked once, *then* the cell becomes filled, not marked empty — a click cycles whatever tool is selected.
  *test: TestSolverMarking_ClickIgnoresTheSelectedTool*
- **AC-305** (happy): *Given* a blank board with the filled tool selected, *when* the pointer is pressed on row 2 column 3 and dragged along row 2 to column 7, *then* exactly the five cells row 2 columns 3-7 are filled and every other cell is undecided.
  *test: TestSolverMarking_DragMarksOneLine*
- **AC-306** (boundary): *Given* a blank board with the filled tool selected, *when* a drag starts on row 2 column 3 and wanders through row 3 column 5 to row 4 column 7, *then* only cells of row 2 are marked, and no cell of rows 3 or 4 changes.
  *test: TestSolverMarking_DragMarksOneLine*
- **AC-307** (happy): *Given* a blank board on which one five-cell drag and then two single clicks on other cells are made, *when* undo is pressed three times and then redo three times, *then* after the undos the board is entirely undecided, and after the redos it shows all seven marks again.
  *test: TestSolverMarking_UndoRedoByStroke*
- **AC-308** (negative): *Given* the board of AC-307 after one undo, *when* a new single click marks another cell, *then* redo is disabled and pressing it changes no cell — the undone stroke cannot be restored.
  *test: TestSolverMarking_UndoRedoByStroke*
- **AC-309** (happy): *Given* a board with two strokes and keyboard focus on the page, *when* Ctrl+Z (Cmd+Z on macOS) is pressed, then Shift+Ctrl+Z (Shift+Cmd+Z), *then* the first key undoes the last stroke and the second redoes it.
  *test: TestSolverMarking_KeyboardAndLabels*
- **AC-310** (boundary): *Given* the player page of a stored puzzle, *when* the filled, empty and undecided tools and the undo, redo and reset controls are inspected and operated from the keyboard alone, *then* each control has a non-empty accessible name, is reachable by Tab, and acts on Enter or Space.
  *test: TestSolverMarking_KeyboardAndLabels*
- **AC-311** (negative): *Given* the player page has finished loading, *when* 20 strokes of clicks and drags are made, *then* the browser issues no network request.
  *test: TestSolverMarking_NoRequestPerMark*

## Engineering constraints

_Verbatim from FR-044._

- **EC-035** (consistency): For any sequence of strokes, undos and redos, replaying the remaining undo history from a blank board reproduces the current board exactly, cell for cell — verified over a seeded random sequence of at least 500 strokes mixing clicks, drags with each tool, undos and redos, with the minimum count asserted in the test.
  *test: PropertyTest_SolverHistory_ReplayReproducesTheBoard*

## Guardrails

- G-1: No new runtime dependency (ADR-0006/R1); plain JS as decided in
  ADR-0038.
- G-2: The board does not reveal correctness while marking. Errors and
  the solved state are CARD-162's, so this card must not leak whether a
  mark is right.
- G-3: No server round-trip per mark; marking is entirely client-side.

## System contract

_Assembled 2026-10-03 by `system_rules.py --card CARD-161` (52 rules); refreshed 2026-10-03 at start (53 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn;… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp <… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R5 — pyproject.toml package-data for nonogram.admin includes static/*.js alongside templates/*.html and static/*.css, so the player's script ships in every built wheel. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode)… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031,… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-044 (AC-303..AC-311, EC-035); US-028; CAP-007
- **ADR:** ADR-0038 (plain JS in the admin panel, pytest-playwright dev extra), ADR-0006/R1
- **CON:** CON-021 (supersedes CON-002), CON-015, CON-016
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ (tokens only; register the tool picker in components.md)
- **Screens:** /puzzle/<id>/solve
- **Reference:** puzzle-nonograms.com; the doc's screenshots were not readable through the Drive text export

## Worktree notes

- [Origin] Cut 2026-10-03 from the owner's design doc at the owner's request.
- [Estimate] 1d is the card-size ceiling. If the click-cycle/tool question
  and touch support push it over, split touch support into its own card
  instead of growing this one.
- [Architect delta] 2026-10-03 — unblocked: CON-002 superseded by CON-021; FR-044 (US-028, CAP-007) and ADR-0038 (resolving DEC-040/041) now exist; acceptance criteria re-cut verbatim from FR-044 and the system contract assembled. Owner answers folded in: a click always cycles, tools govern drags; the error count is the live number of wrong marks.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +ADR-0038/R5 / −none
- [Spawn] implementation agent: general-purpose (Skill: python-pro read as "a Python card" per config.yml caveat), no model parameter (no models: block); started 2026-10-03T11:44Z
- [Implementation 2026-10-03] Built: tool picker (Black / White / Undecided toggle buttons, aria-pressed, exactly one pressed, FILLED at load), click cycle unknown→filled→empty→unknown whatever the tool, row/column-constrained drag with the selected tool (previewed while dragging, recorded on release), stroke-level undo/redo (buttons + Ctrl/Cmd+Z, Shift+Ctrl/Cmd+Z), reset, touch tap and drag via pointer events. No request per mark; nothing reads payload.solution.
- STRUCTURE: strokes and history are pure, frozen values in solver_state.js (ADR-0038/R4). Stroke = `{cells: [[r,c]...], state}`: it carries the state it sets, not the gesture, so replaying it gives the same board (a click's stroke already holds the cycled state). History = `{board, done: [{stroke, before}], undone: [stroke]}`. Undo restores the saved `before` board and does not replay, so EC-035's replay check tests something real. New exports: `cycled`, `clickStroke`, `dragLine`, `dragStroke`, `resetStroke`, `applyStroke`, `replay`, `createHistory`, `record`, `undo`, `redo`.
- STRUCTURE: drag rule (`dragLine`): the axis is set by the first path cell other than the start: the row when its column distance >= its row distance (a tie goes to the row), the column otherwise. A path cell off that line adds nothing (AC-306, owner answer: ignored, not projected). Each on-line path cell adds every cell between it and the previous on-line position, so a fast pointer that skips cells still covers what it passed.
- STRUCTURE: a stroke that changes no cell (e.g. Black over black cells, reset of a blank board) is not a history step: `record` returns the same history, so the redo stack is kept. Pressing a disabled (aria-disabled) control therefore changes nothing by construction: undo/redo with an empty stack and a blank-board reset return the history unchanged. A redundant guard in solver.js was removed after mutation [11] showed it had no effect.
- STRUCTURE: reset = `resetStroke` (every cell → undecided) recorded as ONE undoable stroke, with NO confirmation. CARD-162 owns the in-page confirmation (AC-320/321) and should put it in front of this action (`[data-player-action="reset"]`). Whether reset is undoable after a solve is CARD-162's call (AC-318 locks the board).
- STRUCTURE: undo/redo/reset use `aria-disabled="true"`, not `disabled`, so they stay Tab-reachable (AC-310 asks every control to be reachable by Tab, including at load when there is nothing to undo). Playwright's role query reports them as disabled (`get_by_role(..., disabled=True)`).
- STRUCTURE: renderer seam: `window.puzzlePlayer.setBoard` now also starts a NEW history at the given board (nothing to undo or redo), so a test or CARD-162 can set up a board and then mark on top of it. `getBoard()` returns the shown board, which during a drag is the preview. The controls and the usage hint are server-rendered `hidden` and shown by solver.js once the board is drawn, so a page without its script shows no dead buttons.
- STRUCTURE: pointer input is delegated on table.player-board with setPointerCapture plus `document.elementFromPoint`, so touch (implicitly captured) and a release outside the board both work. pointercancel drops the stroke. A mouse button other than the main one is ignored. CSS: `.player-cell {touch-action: none; cursor: pointer}`, `.player-board {user-select: none}`. Cells themselves are not keyboard-operable: no AC asks for it; a roving-tabindex grid would be its own card.
- STRUCTURE: `--player-chrome-h` now includes one toolbar row (`--control-h + --space-4`) so CARD-160's "30×30 fits 1440×900" test holds; the hint sits below the board for the same reason.
- INVARIANTS (history value), each with a test: I1 replay(first board, done strokes) == board after every op (EC-035 property, 1300 ops / >= 500 strokes). I2 board, done (length and stacks) match an independent Python snapshot model at every op (same property test). I3 a recorded stroke drops the redo stack (property + AC-308 + test_history_branches). I4 a no-op stroke is not a step and keeps redo (property model + test_a_drag_that_changes_nothing_is_not_a_step + test_history_branches). I5 undo/redo on an empty stack return the same history (test_history_branches, test_nothing_to_undo_or_redo_at_load). I6 inputs are not mutated and outputs are frozen (test_history_branches, test_cycle_and_strokes). I7 a drag covers only its start line (drag_line table checked against the Python oracle `_line_cells`, plus browser drags).
- SCOPE+ src/nonogram/admin/static/solver_state.js — the card routes state changes through CARD-160's pure module, and ADR-0038/R4 requires strokes/history to live there. Strictly additive: one appended section; CARD-160's code and comments are untouched.
- DESIGN-REGISTER ToolPicker (new; for components.md, not edited here): used by the puzzle player. Parts: `div.player-tools[role=group][aria-label="Marking tool for drags"]` holding three `button.btn.btn-outline-secondary.player-tool[data-player-tool][aria-pressed]`, each a `span.player-swatch[data-state]` (mini cell: paper / ink / paper with dot) plus a visible label Black / White / Undecided (accessible name = visible label). States: default (quiet button) · hover (Bootstrap quiet hover) · selected (aria-pressed=true: --color-accent-tint ground, --color-accent border and text, 1px inset accent ring) · focus-visible (existing 2px --color-focus ring) · disabled: none (a tool is always pickable). Aria: toggle-button group, exactly one pressed; every button is a Tab stop and acts on Enter/Space. Tokens: --color-accent, --color-accent-tint, --color-border-strong, --grid-paper, --grid-ink, --color-text-secondary, --border-width, --control-h, --space-2/4.
- DESIGN-REGISTER HistoryControls (new): `div.player-history[role=group][aria-label="History"]` with Undo (undo icon), Redo (the undo icon mirrored via `.player-mirror`, since _icons.html is outside scope and has no redo icon) and Reset (refresh icon), all quiet buttons with text labels; Undo/Redo carry aria-keyshortcuts. States: default · hover · focus-visible · disabled = aria-disabled="true" (55% opacity, not-allowed cursor, still focusable; pressing it changes nothing). Layout: tools and history sit in one row above the board (`.player-toolbar`, flex-wrap; on a 390 phone it wraps to two rows). A usage hint (`.player-hint`, --text-sm secondary) sits below the board. Candidate icon: a real `redo` icon in _icons.html.
- DESIGN-REGISTER SolverBoard (new states): interactive cells (cursor: pointer, touch-action none, no text selection); drag in progress shows a live preview (cells take the tool's state as the pointer passes, recorded on release). No new colours or tokens; no hover tint (it would hide the state while the pointer rests on a cell). No error/solved state (G-2, CARD-162).
- MUTATION: cycle order swapped (filled→unknown) → caught by TestSolverMarking_ClickCycles::test_three_clicks_go_filled_empty_undecided_and_are_drawn_so
- MUTATION: click uses the selected tool → caught by TestSolverMarking_ClickCycles::test_three_clicks… (and ClickIgnoresTheSelectedTool)
- MUTATION: axis constraint dropped (off-line cells marked) → caught by TestSolverMarking_DragMarksOneLine::test_a_drag_that_jumps_off_its_row_marks_only_the_start
- MUTATION: tie picks the column (>= → >) → caught by TestSolverHistoryModule::test_drag_line[tie-is-row]
- MUTATION: no interpolation (only the reached cell) → caught by TestSolverMarking_DragMarksOneLine::test_coming_back_to_the_row_marks_the_span_passed
- MUTATION: record keeps the redo stack → caught by TestSolverMarking_UndoRedoByStroke::test_a_new_stroke_after_undo_drops_redo
- MUTATION: no-op guard dropped in record → caught by TestSolverMarking_UndoRedoByStroke::test_a_drag_that_changes_nothing_is_not_a_step
- MUTATION: drag recorded per cell instead of per stroke → caught by TestSolverMarking_DragMarksOneLine::test_a_drag_released_outside_the_board_still_counts (and UndoRedoByStroke)
- MUTATION: undo takes the oldest entry → caught by test_a_drag_released_outside_the_board_still_counts (and AC-307's test)
- MUTATION: redo leaves the stroke on the redo stack → caught by TestSolverMarking_UndoRedoByStroke::test_three_undos_then_three_redos
- MUTATION: redo button never aria-disabled → caught by test_three_undos_then_three_redos
- MUTATION: disabled buttons still act (guard removed) → SURVIVED: the guard was redundant, because the module already returns the history unchanged in every disabled case. Resolved by deleting the guard; test_nothing_to_undo_or_redo_at_load and AC-308's test check the behaviour.
- MUTATION: Shift ignored by the shortcut (always undo) → caught by test_a_new_stroke_after_undo_drops_redo (and AC-309's test)
- MUTATION: Meta ignored by the shortcut → caught by TestSolverMarking_KeyboardAndLabels::test_ctrl_z_undoes_and_shift_ctrl_z_redoes[Meta]
- MUTATION: reset bypasses the history → caught by test_reset_clears_the_board_as_one_undoable_step
- MUTATION: other mouse buttons mark → caught by test_other_mouse_buttons_mark_nothing
- MUTATION: no setPointerCapture → caught by test_a_drag_released_outside_the_board_still_counts
- MUTATION: setBoard keeps the old history → caught by test_set_board_starts_a_new_history
- MUTATION: applyStroke accepts any state → caught by TestSolverHistoryModule::test_cycle_and_strokes
- MUTATION: touch-action: none dropped → caught by test_a_touch_drag_marks_one_line
- MUTATION: drag preview never shown → first SURVIVED; added test_a_drag_is_previewed_and_recorded_on_release, which now catches it
- MUTATION: White tool mapped to filled → caught by the ClickIgnoresTheSelectedTool / DragMarksOneLine tool tests
- MUTATION: reset never aria-disabled → caught by test_nothing_to_undo_or_redo_at_load
- TESTS: tests/test_puzzle_solver_marking.py: 48 tests, all green (real Chromium): ClickCycles 4 (incl. touch tap via page.touchscreen), ClickIgnoresTheSelectedTool 5, DragMarksOneLine 10 (incl. CDP touch drag), UndoRedoByStroke 6, KeyboardAndLabels 6, NoRequestPerMark 2 (20 real strokes + undo/redo/reset → zero requests; console-clean with strokes), RevealsNoCorrectness 2 (G-2), TestSolverHistoryModule 11 (pure branches + dragLine table), test_PropertyTest_SolverHistory_ReplayReproducesTheBoard 1 (seed 35, 1300 ops, >= 500 strokes asserted in-test, >= 80 drags per tool, >= 100 undos and >= 100 redos, >= 50 effective redos, >= 20 redo-stack drops). Neighbours green: tests/test_puzzle_solver_page.py, tests/test_cli.py, tests/test_admin_design_tokens.py, test_export_pdf::test_the_dependency_baseline_is_still_closed (TestDependencyBaseline_IsExactlyPillowAndNumpy). Fixtures are imported from tests.test_puzzle_solver_page, which was not edited.
- CONSOLE: clean. test_strokes_leave_the_console_clean (20 strokes + undo/redo/reset: no console error/warning, page error, failed request or 4xx/5xx) passes, and the render run reported "console clean" at 1440 and 390.
- RENDERS: ~/Documents/nonogram-reviews/CARD-161/ (script card161_render.py; Duck 15×15 through the real image pipeline, real mouse strokes and Tab): tool-picker-1440.png, tool-picker-390.png, player-fresh-1440.png, player-fresh-390.png, player-mid-solve-1440.png, player-mid-solve-390.png (filled runs + white dots, White tool selected), focus-visible-undo-1440.png, focus-visible-undo-390.png (keyboard focus ring on Undo).
- [Scope] src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_marking.py
- [Build gate] impact underivable (test_scope: full) — full suite
- [Scope gate] cycle 1: IN_SCOPE — guardrail_hits 0 (G-1..G-3 behavioural, no structural globs); excess 1/5 = 20% (solver_state.js, existing file outside Touches, recorded SCOPE+ — card text and ADR-0038/R4 route strokes/history through the pure module; diff is append-only); comp_spread 0 (COMP-009 only); poached: CARD-162 Touches overlap 3 files (solver.js, puzzle_solve.html, admin.css) — designed sharing, CARD-162 Depends on CARD-161; no error-count/solved/solution-reading code in the diff (grep), so no sibling scope absorbed
- [Build gate] PASSED (full, 477s) — 5967 passed, 9 skipped, 3 failed: the 2 main-branch baseline failures (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders) + 1 flake not attributable to this card: tests/test_book_ready_gate.py::TestBookPlanEdit_OnANonDraftBookReturnsItToDraft::test_save_plan_returns_the_book_to_draft[db-ready_for_pdf] (book plan page "Fixed" text missing; the module re-run alone 3x → 87 passed each time; the card touches no book code)
- [Adversarial] F-001 CONFIRMED — solver_state.js:14-17 and :72 (CARD-160 header, unchanged) say CARD-161 routes clicks through withCell/setBoard and keeps an array of boards; solver.js:300 routes clicks clickStroke → record → applyStroke, withCell has no caller in solver.js, setBoard (solver.js:220-232) now resets the history
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (F-001, adversarially confirmed). Minor F-002..F-005, out-of-scope F-006 (tap target, CARD-160 sizing), F-007 (ADR-0006/R1 check ref names no existing test — model defect). Step 8h coverage: 53/53 card rules addressed (13 ✓, 40 ⚠, 0 ✗); 8f-mutation deferred(cost); 8g static only (visual off)
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Review sync] 1 report(s) → meta/review/ (20261003T121943Z-CARD-161-cycle1.yml)
- SCOPE+ amended (fix 1): CARD-160's header comment in solver_state.js (lines 13–21 and the isBoard note "a history of boards") corrected to match the shipped stroke/history design (F-001); no CARD-160 code changed.
- STRUCTURE correction (fix 1, F-003): a drag uses the tool selected at its pointerdown (kept on the gesture), for its preview and for the stroke recorded on release; a tool picked mid-drag governs the next drag. Supersedes "drag with the selected tool" in the Implementation line above.
- STRUCTURE correction (fix 1, F-002): the Ctrl/Cmd+Z and Shift+Ctrl/Cmd+Z shortcuts match event.key "z"/"Z", or event.code "KeyZ" when event.key is not a Latin letter (e.g. Russian "я"); a Latin letter on the KeyZ position (German "y") is that letter, not Z.
- STRUCTURE confirmed (fix 1, F-004): controls and hint stay hidden when solver.js refuses the payload as well as when the script never ran — now tested (TestSolverMarking_ControlsStayHiddenWithoutABoard); template comment extended to say so.
- STYLE (fix 1, F-005): .player-swatch size 1rem → var(--space-4) (same value).
- MUTATION (fix 1): isZ drops the event.code fallback → caught by TestSolverMarking_KeyboardAndLabels::test_ctrl_z_works_when_the_layout_puts_a_non_latin_letter_on_z
- MUTATION (fix 1): isZ drops the "not a Latin letter" guard (code KeyZ always matches) → caught by TestSolverMarking_KeyboardAndLabels::test_a_latin_letter_on_the_z_position_is_that_letter_not_z
- MUTATION (fix 1): pointerup records with the current tool instead of the gesture's → caught by TestSolverMarking_KeyboardAndLabels::test_a_tool_picked_mid_drag_applies_to_the_next_drag
- MUTATION (fix 1): pointermove previews with the current tool instead of the gesture's → caught by TestSolverMarking_KeyboardAndLabels::test_a_tool_picked_mid_drag_applies_to_the_next_drag
- MUTATION (fix 1): controls and hint shown before the payload is read → caught by TestSolverMarking_ControlsStayHiddenWithoutABoard::test_a_refused_payload_shows_no_controls
- MUTATION (fix 1): template controls rendered without `hidden` → caught by TestSolverMarking_ControlsStayHiddenWithoutABoard::test_a_page_whose_script_never_ran_shows_no_controls
- TESTS (fix 1): +5 tests (KeyboardAndLabels +3, ControlsStayHiddenWithoutABoard 2) → 53 in tests/test_puzzle_solver_marking.py.
- [Fix 1] FIXED F-001 (comment-only: solver_state.js header re-derived to the shipped stroke/history design), F-002 (isZ: event.code KeyZ fallback when event.key is not a Latin letter), F-003 (tool captured on the gesture at pointerdown), F-004 (controls-hidden paths tested), F-005 (1rem → var(--space-4)); SKIPPED F-006, F-007 (out of scope). 6/6 fix mutants killed. Pre-gate: 5/5 named tests passed
- [Fix 1] declarations: 4 updated (solver_state.js header, isZ doc, gesture/pointerdown docs, puzzle_solve.html comment), 3 confirmed (aria-keyshortcuts, drag hint/aria-label, template hidden contract), 1 none (F-005)
- [Build gate] PASSED (full, 478s) — after fix 1: 5973 passed, 9 skipped, 2 failed = exactly the main-branch baseline pair (test_size_configuration_applied, test_batch_creation_form_renders); the cycle-0 book flake did not recur
- [Scope gate] cycle 2: IN_SCOPE — same 5 product files, no new paths; G-1..G-3 behavioural
- [Review 2/3] CONFIRMATION MODE eligible — prior review parsed; delta = uncommitted fix-1 edits for F-001..F-005 only (admin.css, solver.js, solver_state.js, puzzle_solve.html, tests/test_puzzle_solver_marking.py); IN_SCOPE; cycle 1 raised no gating findings beyond F-001
- [Review 2/3] Score: 9.0 — crit: 0, imp: 0. Confirmation mode; F-001..F-005 ✓ resolved (mutants M7, M8 re-run and killed). New Minor F-008 (usage hint never asserted visible — surviving mutant M10; reviewer filed it Minor deliberately: static help text outside every AC/EC, consistent with F-004's rating; orchestrator accepts the rating), F-009 (solver.js MARKING header still says drags use "the selected tool"; isZ comment wording). Step 8h 53/53 addressed (9 ✓, 44 ⚠ incl. ADR-0006/R1 check_ref_missing, 0 ✗; carried lines delta-clean); reviewer notes cycle 1's count line overstated ✓ (13 vs 9 in its own list). 8f-mutation RAN: 10 mutants, 9 killed, 1 survived (M10 → F-008)
- [Review 2/3] Score: 9.0 ✓ threshold reached + no critical/important
- [Review sync] 2 report(s) → meta/review/ (…-cycle1.yml with fix-1 status write-backs, 20261003T124849Z-CARD-161-cycle2.yml)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0038/R2 — TestSolverMarking_NoRequestPerMark 2 passed, context-wide request listener, 0 network-API hits; ADR-0038/R3 — ShowsTheClues 7 passed, embedding line unchanged; ADR-0038/R4 — 0 DOM hits, delta comments-only, TestSolverHistoryModule 11 passed). Skeptic nits (non-gating): R2 — the first of the 10 drags starts and ends on one cell (a click stroke), 20 strokes still made; R4 — solver.js refresh() computes the reset button's aria-disabled with a local blank-board predicate (display only)
- [AC/EC check] Failed: AC-310 ⚠ partial — every control has a non-empty accessible name and Tab reaches all six, but Enter AND Space are not each demonstrated per control: Undecided tested with Enter only, Black with Space only; Undo-Space / Redo-Enter pressed only as a pair whose expected end state equals the start (a both-dead mutant passes). 12 other items ✓ demonstrated (AC-303..309, AC-311, EC-035, G-1..G-3)
- MUTATION (AC fix): tool and history click handlers ignore keyboard-triggered clicks (`event.detail === 0` → return) → caught by TestSolverMarking_KeyboardAndLabels::test_each_tool_acts_on_a_single_key_press[{Black,White,Undecided}-{Enter,Space}] and ::test_each_history_control_acts_on_a_single_key_press[{Undo,Redo,Reset}-{Enter,Space}] (12/12 fail)
- MUTATION (AC fix): Space dead on the controls (keyup " " preventDefault on #puzzle-player-controls) → caught by the 6 `-Space` cases of the two tests above (Enter cases still pass)
- MUTATION (AC fix): Enter dead on the controls (keydown "Enter" preventDefault on #puzzle-player-controls) → caught by the 6 `-Enter` cases of the two tests above (Space cases still pass)
- AC fix (AC-310): test-only — each of the six controls is reached by Tab and operated by ONE Enter and, separately from a fresh page, ONE Space, with the effect asserted after that single press (tool: aria-pressed moves and the next drag uses it; Undo: board minus last stroke; Redo: stroke restored; Reset: blank, then undoable). +2 parametrized tests (12 cases) → 65 in tests/test_puzzle_solver_marking.py, all passing.
- [AC fix] FIXED AC-310 — test-only: test_each_tool_acts_on_a_single_key_press, test_each_history_control_acts_on_a_single_key_press (6 controls × Enter/Space, each reached by Tab, effect asserted per single press); 3 mutants (keyboard clicks ignored / Space blocked / Enter blocked) each killed exactly the expected cases. Pre-gate: named tests passed. DECLARATIONS AC-310 — none (test-only)
- [Build gate] PASSED (full, 496s) — after the AC fix: 5985 passed, 9 skipped, 2 failed = exactly the main-branch baseline pair
- [Scope gate] cycle 2 (repeat after AC fix): IN_SCOPE — same 5 product files; AC-fix delta is tests/test_puzzle_solver_marking.py only
- [Review 2/3 repeat] CONFIRMATION MODE — AC-fix loop repeats cycle 2 (counter not incremented); delta since the cycle-2 reviewed state = tests/test_puzzle_solver_marking.py only
- [Review 2/3 repeat] Score: 9.0 — crit: 0, imp: 0. Confirmation mode (delta = test file only); AC-310 ✓ resolved (4 keyboard mutants K1–K4, 4 killed). Minor still open: F-008 (hint visibility untested, M10), F-009 (stale "selected tool" wording in solver.js header); new Minor F-010 (older test_each_control_acts_on_enter_or_space sets focus by script and chains presses — superseded by the new parametrized tests). Step 8h 53/53 (9 ✓ — R2/R4/R6/R8 re-verified fresh, rest carried delta-clean; 44 ⚠; 0 ✗)
- [Review 2/3 repeat] Score: 9.0 ✓ threshold reached + no critical/important
- [Review sync] 3 report(s) → meta/review/ (cycle1, cycle2 20261003T124849Z, cycle2-repeat 20261003T131835Z)
- [8h spot-check] 3/3 sampled holds reproduced after the AC fix (ADR-0038/R2 — NoRequestPerMark 2 passed, context-level listener, 0 network-API hits; ADR-0038/R4 — TestSolverHistoryModule 11 passed, touches_no_dom passed, solver_state.js comment-only since 753e023; ADR-0038/R6 — RevealsNoCorrectness 2 passed, no new route/.py, new tests read no solution)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-303 ✓ demonstrated — evidence: TestSolverMarking_ClickCycles::test_three_clicks_go_filled_empty_undecided_and_are_drawn_so PASSED (real clicks ×3; states filled/empty/unknown + drawn look)
  AC-304 ✓ demonstrated — evidence: TestSolverMarking_ClickIgnoresTheSelectedTool::test_a_click_on_an_undecided_cell_fills_it_whatever_the_tool[White|Undecided|Black] PASSED (exactly {(5,5): filled})
  AC-305 ✓ demonstrated — evidence: TestSolverMarking_DragMarksOneLine::test_row_2_columns_3_to_7 PASSED (real mouse drag; marked set == exactly the five cells)
  AC-306 ✓ demonstrated — evidence: TestSolverMarking_DragMarksOneLine::test_a_drag_that_wanders_off_marks_only_its_row + test_a_drag_that_jumps_off_its_row_marks_only_the_start PASSED
  AC-307 ✓ demonstrated — evidence: TestSolverMarking_UndoRedoByStroke::test_three_undos_then_three_redos PASSED (3 undos → {}, 3 redos → all seven marks)
  AC-308 ✓ demonstrated — evidence: TestSolverMarking_UndoRedoByStroke::test_a_new_stroke_after_undo_drops_redo PASSED (Redo disabled; forced click + Shift+Ctrl+Z change no cell)
  AC-309 ✓ demonstrated — evidence: TestSolverMarking_KeyboardAndLabels::test_ctrl_z_undoes_and_shift_ctrl_z_redoes[Control|Meta] PASSED
  AC-310 ✓ demonstrated — evidence: test_each_control_has_a_name_and_is_reachable_by_tab + test_each_tool_acts_on_a_single_key_press[3×Enter|Space] + test_each_history_control_acts_on_a_single_key_press[Undo|Redo|Reset × Enter|Space] PASSED (12 single-press cases)
  AC-311 ✓ demonstrated — evidence: TestSolverMarking_NoRequestPerMark::test_twenty_strokes_issue_no_request PASSED (context-level listener; 10 clicks + 10 drags + undo/redo/reset; requests == [])
  EC-035 ✓ demonstrated — evidence: test_PropertyTest_SolverHistory_ReplayReproducesTheBoard PASSED (random.Random(35), 1300 ops; in-test minima: strokes ≥ 500, ≥ 80 drags per tool, ≥ 100 undos/redos; replay-from-blank == board and == independent Python model after every op)
  G-1 ✓ demonstrated — evidence: no pyproject/package file in the diff; only JS import is ./solver_state.js; test_the_dependency_baseline_is_still_closed 1 passed
  G-2 ✓ demonstrated — evidence: TestSolverMarking_RevealsNoCorrectness (2) PASSED; no `solution` token in marking code outside comments (only the load-time payload check, solver.js:109)
  G-3 ✓ demonstrated — evidence: TestSolverMarking_NoRequestPerMark (2) PASSED; no fetch/XHR/sendBeacon/WebSocket/EventSource/location/form submit in solver.js/solver_state.js
  (52 passed, 0 skipped, real Chromium; tests/test_puzzle_solver_page.py unchanged vs main)
- [Docs] skipped — the changed directories (src/nonogram/admin/static, src/nonogram/admin/templates) carry no per-directory README (convention is an open owner decision, as at CARD-160); tests/README.md catalogues no per-feature test file. DESIGN-REGISTER lines (ToolPicker, HistoryControls, SolverBoard new states) NOT applied — meta/design/components.md is outside Touches; left for the dispatcher at merge
- [Commit] 1b01b5e (review fixes) on top of 753e023 (implementation) — success commit; explicit pathspecs (5 product files), nothing under meta/ committed [Inline fallback] commit message written inline from the diff + card (forge:commit's git add -A / no-Co-Authored-By rules overridden by project rules). Card diff vs main: 5 files, +1452 −13. Card stays review until done
- [Merged] 2026-10-03 — 8b485cc into main (--no-ff). Merge gate: rebase was a no-op (main still at 40c0dc8 = branch base); the merged tree is the one that passed the post-fix full suite (5985 passed, only the 2 baseline failures); not re-run. Deferral scan: 0 hits. Trace: FR-044 already lists the card's tests. DESIGN-REGISTER applied at close-out: ToolPicker and HistoryControls registered, SolverBoard interactive states added in meta/design/components.md. F-006/F-008/F-009/F-010, keyboard cell marking and the gate-0 book-gate flake captured to backlog.
