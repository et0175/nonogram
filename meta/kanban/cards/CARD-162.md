# CARD-162: The solver counts errors and celebrates a solved puzzle

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/162-solver-errors-and-solved
**Worktree:** —
**Source:** owner design doc "Nonograms - Print layout" (Google Doc 1pJKF2qX6mC9qw4Cf9Nv3hblTDmtoHwP5Tb8wzK1_WqM), section "Online solver"
**Idea:** —
**Wave:** 31
**Depends on:** CARD-161
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_progress.py
**Review score:** 9.5 (cycle 3/3)
**Started:** 2026-10-03T13:31:15Z
**Closed:** 2026-10-03T16:12:45Z
**Actual:** 0.3d
**Merge commit:** 4b5ed9d
**Blocked by:** —

## What to implement

The document's top bar: "the number of errors and hint button (or we can go
without hints for now)", plus "some animation when the puzzle is solved".
**Hints are left out** of this card, as the document allows; they're on
the backlog.

1. **Error count** at the top of the page, compared against the solution
   CARD-160 put in the page.
   **Definition (owner answer 2026-10-03, FR-044 AC-312..315, EC-037):** an error is a cell currently
   marked black where the solution is white, or marked white where the
   solution is black. Undecided cells are never errors. The count is live,
   so it goes back down when a mistake is undone or corrected.
2. **Solved state:** the puzzle is solved when every solution-black cell is
   marked black and no solution-white cell is marked black. White marks are
   optional, as on paper. On solve:
   - show the picture's name (the reveal the printed answer key also gives);
   - play a short animation (the document's request);
   - stop accepting marks until the person chooses to keep looking or
     reset.
   Respect `prefers-reduced-motion` with a non-animated reveal.
3. **Reset:** a button that clears the board after a confirmation. Use an
   in-page confirm, not a browser `confirm()` dialog.

## Acceptance criteria

_Verbatim from FR-044 in meta/architecture/requirements.yml (architect delta 2026-10-03)._

- **AC-312** (happy): *Given* a board with error count 0, *when* one cell whose solution is empty is marked filled, *then* the error count reads 1.
  *test: TestSolverProgress_LiveErrorCount*
- **AC-313** (happy): *Given* a board with error count 0, *when* one cell whose solution is filled is marked empty by a drag with the empty tool, *then* the error count reads 1.
  *test: TestSolverProgress_LiveErrorCount*
- **AC-314** (boundary): *Given* the board of AC-312 showing error count 1, *when* that stroke is undone, *then* the error count reads 0 — the count is the current number of wrong marks, not a running total.
  *test: TestSolverProgress_LiveErrorCount*
- **AC-315** (boundary): *Given* a freshly loaded board, every cell undecided, whose solution has 120 filled cells, *when* the error count is read, *then* it reads 0 — undecided cells never count.
  *test: TestSolverProgress_LiveErrorCount*
- **AC-316** (happy): *Given* a board on which exactly the solution's filled cells are marked filled and some, none or all solution-empty cells are marked empty, *when* the stroke completing the last solution-filled cell is made, *then* the solved state appears showing the puzzle's picture name.
  *test: TestSolverProgress_SolvedWhenBlacksMatch*
- **AC-317** (negative): *Given* a board on which every solution-filled cell is marked filled and one solution-empty cell is also marked filled, *when* the board is checked, *then* the solved state does not appear.
  *test: TestSolverProgress_SolvedWhenBlacksMatch*
- **AC-318** (boundary): *Given* a board in the solved state, *when* a cell is clicked, a drag is made, and undo and redo are pressed, *then* no cell changes state.
  *test: TestSolverProgress_LockedUntilReset*
- **AC-319** (boundary): *Given* a browser reporting prefers-reduced-motion reduce, *when* the puzzle is solved, *then* the solved state and picture name appear with no CSS animation or transition running.
  *test: TestSolverProgress_ReducedMotion*
- **AC-320** (happy): *Given* a board with 30 marks, or a board in the solved state, *when* reset is pressed and the in-page confirmation is accepted, *then* every cell is undecided, the error count reads 0, and marks are accepted again.
  *test: TestSolverProgress_ResetAfterConfirm*
- **AC-321** (negative): *Given* a board with 30 marks, *when* reset is pressed and the in-page confirmation is cancelled, *then* all 30 marks remain and no browser confirm() dialog was opened at any point.
  *test: TestSolverProgress_ResetAfterConfirm*

## Engineering constraints

_Verbatim from FR-044._

- **EC-036** (consistency): For any board and any solution grid of matching width and height, the player's solved check is true if and only if a direct cell-by-cell comparison finds every solution-filled cell marked filled and no solution-empty cell marked filled — verified over a seeded corpus of at least 200 random boards per grid shape tried, including non-square shapes, with the minimum count asserted in the test.
  *test: PropertyTest_SolverProgress_SolvedMatchesTheSolution*
- **EC-037** (consistency): For any board and any solution grid of matching width and height, the error count equals the number of cells marked filled whose solution is empty plus the number marked empty whose solution is filled, computed independently cell by cell — verified over EC-036's seeded corpus, so the count can never drift into a running total or count an undecided cell.
  *test: PropertyTest_SolverProgress_ErrorCountMatchesTheDefinition*

## Guardrails

- G-1: No new runtime dependency; plain JS as decided in ADR-0038.
- G-2: No hint feature in this card. If one seems needed, it's a backlog
  item.
- G-3: Nothing is persisted: no score, no time, no progress row.

## System contract

_Assembled 2026-10-03 by `system_rules.py --card CARD-162` (52 rules; refreshed 2026-10-03 at start: 53). A projection — fix the source artifact, never this list._

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

- **FR:** FR-044 (AC-312..AC-321, EC-036, EC-037); US-028; CAP-007
- **ADR:** ADR-0038 (plain JS in the admin panel, pytest-playwright dev extra), ADR-0006/R1
- **CON:** CON-021 (supersedes CON-002), CON-015, CON-016
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ (tokens only; error counter and solved state registered in components.md)
- **Screens:** /puzzle/<id>/solve

## Worktree notes

- [Origin] Cut 2026-10-03 from the owner's design doc at the owner's request.
- [Architect delta] 2026-10-03 — unblocked: CON-002 superseded by CON-021; FR-044 (US-028, CAP-007) and ADR-0038 (resolving DEC-040/041) now exist; acceptance criteria re-cut verbatim from FR-044 and the system contract assembled. Owner answers folded in: a click always cycles, tools govern drags; the error count is the live number of wrong marks.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +ADR-0038/R5 / −none
- [Implementation 2026-10-03] Built: live error counter in the toolbar row (`Errors: N`, role=status), solved state (banner "Solved: <picture name>" in place of the tools, success frame on the board, short diagonal success-flash animation over the filled cells plus banner settle-in, board locked), reduced-motion reveal (same banner/frame, no animation or transition anywhere in the player), Reset behind an in-page confirmation (role=alertdialog, "Clear board" / "Keep marks", Escape cancels, focus moved in to "Keep marks" and back to Reset; never window.confirm). Hints not built (G-2); nothing persisted, no request, no storage (G-3, ADR-0038/R2).
- STRUCTURE: pure logic in solver_state.js — `errorCount(board, solution)` (FILLED on solution-empty + EMPTY on solution-filled; UNKNOWN never) and `isSolved(board, solution)` ((cell === FILLED) === solution cell, for every cell; EMPTY marks optional). solution = the payload's [[bool]] grid, trusted in-page value like boards (no hostile-value defences claimed).
- STRUCTURE: solver.js start() re-derives both from the RECORDED board (history.board) after every commit (stroke, undo, redo, reset) and setBoard; nothing accumulates, so the count is live. A drag preview is not counted until recorded. wireMarking still never reads payload.solution — it asks `player.locked()`. Header comment of solver.js updated (it previously said nothing reads payload.solution).
- STRUCTURE: the lock is a function of the current board (locked iff isSolved), not a separate flag. Locked: pointerdown ignored (no click, no drag, no preview), undo/redo buttons and Ctrl/Cmd+Z / Shift+Ctrl/Cmd+Z return the history unchanged, Undo/Redo show aria-disabled. Reset stays active. setBoard to a solved board locks; to an unsolved one unlocks.
- DECISION (reset from solved): reset stays ONE undoable step (record(history, resetStroke(...)), as in CARD-161), also from the solved state. Undoing it brings the solved board back and, because the lock is derived from the board, the lock with it; the reset then sits on the redo stack but redo is locked, so only Reset leaves the solved state again. Tested: TestSolverProgress_LockedUntilReset::test_redo_changes_nothing, TestSolverProgress_ResetAfterConfirm::test_the_reset_from_solved_is_one_undoable_step.
- Picture name: the template's existing `title` (route data: puzzle_name or source_image or short id) rendered into the hidden banner; app.py NOT changed, payload keys unchanged.
- A11y: error counter is a role=status region (text rewritten only when the number changes); the solved text goes into an always-present visually hidden live region #puzzle-player-announce (cleared when unsolved), since a region that only appears is not reliably read. Confirm keyboard-operable (tested Enter/Space/Shift+Tab/Escape).
- SCOPE+ src/nonogram/admin/static/solver_state.js — ADR-0038/R4 puts the error count and solved predicate in the pure module. Strictly additive: one appended section + two header lines; no existing code touched.
- SCOPE+ tests/test_puzzle_solver_marking.py — CARD-161 tests pinned behaviour this card changes by design: (a) 5 reset tests now accept the in-page confirmation ("Clear board" / Shift+Tab + key) before asserting the cleared board; the Reset single-key AC-310 case now asserts the press opens the confirmation with focus on "Keep marks", then one more press of the same key clears; (b) TestSolverMarking_RevealsNoCorrectness (G-2 of CARD-161) narrowed: marking all but the LAST solution cell still changes nothing but cell states (renamed test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states); test_the_marking_code_reads_no_solution now checks wireMarking + the stroke/history section of solver_state.js only. 65/65 green.
- TESTS: tests/test_puzzle_solver_progress.py — 36 tests, all green (real Chromium): TestSolverProgress_LiveErrorCount 8 (AC-312..315 + corrections/undo/redo, live region, setBoard), TestSolverProgress_SolvedWhenBlacksMatch 8 (AC-316 whites none/some/all + completing drag, AC-317 stray black, missing black with 0 errors, board does not move, setBoard), TestSolverProgress_LockedUntilReset 6 (AC-318 combined + click / drag incl. no preview / undo / redo-after-undone-reset / reset available), TestSolverProgress_ReducedMotion 2 (AC-319: getAnimations()==0, animation-name none and transition-duration 0 on every player element; control: without reduced motion every filled cell and the banner animate, all finished < 2 s), TestSolverProgress_ResetAfterConfirm 7 (AC-320 30 marks + solved, AC-321 cancel; page.on("dialog") never fires; Escape; keyboard; disabled Reset opens nothing; reset-from-solved undo), TestSolverProgress_StaysInThePage 1 (no request, no local/sessionStorage, console clean through solve + reset flows), TestSolverProgressModule 1 (12 hand cases), test_PropertyTest_SolverProgress_SolvedMatchesTheSolution (EC-036), test_PropertyTest_SolverProgress_ErrorCountMatchesTheDefinition (EC-037), test_PropertyTest_SolverProgress_PageShowsWhatTheDefinitionSays (40 boards through setBoard, DOM vs oracle). AC-315 uses GRID_120: 20x10 tight rows, exactly 120 filled (asserted from the payload).
- EC corpus: random.Random(36); shapes 10x10, 15x10, 10x25, 30x30; 300 boards per shape over 6 solutions (4 random densities + all-empty + all-filled); kinds random / solved / near-miss (one wrong or missing cell) / missing (1-5 blacks undecided, no error) / noisy. In-test minima per shape: >= 200 boards, >= 50 solved and >= 150 unsolved, >= 50 near misses, >= 20 unsolved-with-zero-errors, >= 100 with errors, >= 20 with exactly one error, >= 100 with undecided solution-filled cells. Oracle: explicit Python cell-by-cell loops (_errors_of, _solved_of), never the JS. One page.evaluate per shape.
- Neighbours green: tests/test_puzzle_solver_page.py (58), tests/test_puzzle_solver_marking.py (65), tests/test_admin_design_tokens.py — 169 passed with the progress file.
- MUTANT M1 errorCount counts UNKNOWN on a solution-filled cell → caught by TestSolverProgress_LiveErrorCount (14 tests incl. test_ac315…, EC-037)
- MUTANT M2 errorCount drops the EMPTY-where-filled term → caught by test_ac313_a_white_drag_over_a_solution_filled_cell_reads_one (+6, EC-037)
- MUTANT M3 errorCount drops the FILLED-where-empty term → caught by test_ac312_marking_a_solution_empty_cell_filled_reads_one (+9, EC-037)
- MUTANT M4 isSolved ignores stray fills → caught by test_ac317_a_stray_black_on_a_solution_empty_cell_is_not_solved (+EC-036, page property)
- MUTANT M5 isSolved requires white marks → caught by test_ac316_the_completing_click_shows_the_picture_name[none|some] (+8, EC-036)
- MUTANT M6 error count never goes down (running maximum in the DOM) → caught by test_ac314_undoing_the_wrong_stroke_reads_zero (+5)
- MUTANT M7 pointer input not locked → caught by TestSolverProgress_LockedUntilReset test_ac318…, test_a_click_changes_nothing, test_a_drag_changes_nothing_not_even_as_a_preview (+1)
- MUTANT M8 undo not locked → caught by TestSolverProgress_LockedUntilReset::test_undo_changes_nothing
- MUTANT M9 redo not locked → caught by TestSolverProgress_LockedUntilReset::test_redo_changes_nothing
- MUTANT M10 keyboard shortcuts bypass the lock → caught by test_ac318_click_drag_undo_redo_change_nothing, test_undo_changes_nothing
- MUTANT M11 reset skips the confirmation → caught by TestSolverProgress_ResetAfterConfirm (8 tests incl. test_ac321_cancelling_keeps_all_thirty_marks)
- MUTANT M12 reset asks window.confirm → caught by TestSolverProgress_ResetAfterConfirm (8 tests; dialog list non-empty / marks kept)
- MUTANT M13 accept bypasses record (fresh history) → caught by test_the_reset_from_solved_is_one_undoable_step, test_redo_changes_nothing (+1)
- MUTANT M14 Escape does not cancel → caught by test_escape_cancels_and_focus_returns_to_reset
- MUTANT M15 focus not moved into the confirmation → caught by test_escape_cancels_and_focus_returns_to_reset, test_the_confirmation_is_keyboard_operable
- MUTANT M16 focus not returned to Reset → caught by the same two tests
- MUTANT M17 setBoard does not re-derive progress → caught by test_set_board_rederives_the_count, test_set_board_to_a_solved_board_shows_it…, page property test
- MUTANT M18 solved not announced (live region left empty) → caught by test_ac316_the_completing_click_shows_the_picture_name[*]
- MUTANT M19 tools stay visible when solved → caught by test_the_banner_takes_the_tools_place_and_the_board_does_not_move
- MUTANT M20 undo/redo not aria-disabled while locked → caught by test_ac318…, test_redo_changes_nothing
- MUTANT M21 a disabled Reset still opens the confirmation → caught by test_a_disabled_reset_opens_no_confirmation
- MUTANT M22 reduced motion still animates (media query disabled) → caught by TestSolverProgress_ReducedMotion::test_ac319_solved_with_no_animation_or_transition
- MUTANT M23 no solved board animation at all → first SURVIVED (the control only counted page animations; the banner's still ran); control test strengthened to require every filled cell and the banner to animate → now caught by test_without_reduced_motion_the_solve_is_animated
- MUTANT M24 reduced motion keeps transitions → caught by test_ac319_solved_with_no_animation_or_transition
- MUTANT M25 progress not re-derived after a commit → caught by 23 tests
- DESIGN-REGISTER ErrorCounter — new: "Errors: N" at the end of the player toolbar row (margin-left auto; wraps under the history controls on a phone); label --text-sm --color-text-secondary, number --font-num tabular --text-base --color-text; role=status, aria-atomic; states: default only (0 is shown, not hidden) — admin.css:.player-errors, .player-errors-count
- DESIGN-REGISTER SolvedBanner — new: check icon (--color-success) + "Solved: <strong>picture name</strong>", --color-success-tint ground, 1px --color-success border with 3px left rule, --radius-control, min-height --control-h; shown only while the board is solved, in place of the ToolPicker (the board does not move); settles in over --duration-base --ease; text mirrored into a visually hidden live region — admin.css:.player-solved, .player-announce
- DESIGN-REGISTER SolverBoard (new state "solved") — 2px --color-success outline at --space-1 offset while solved; on the transition into solved the filled cells flash --color-success in a diagonal sweep (delay (row+col)·12ms, 2×--duration-base each, ~1 s total) ending in ink; cells locked (no input) — admin.css:.player-board.is-solved
- DESIGN-REGISTER SolverBoard (reduced-motion solved state) — prefers-reduced-motion: reduce → same banner, name and success outline, no animation or transition on any player element — admin.css:@media (prefers-reduced-motion: reduce)
- DESIGN-REGISTER ResetConfirm — new: in-page popover under the history controls (left-anchored, overlays the board, no layout shift), --color-surface, --color-border-strong border, --radius-container, --shadow-modal, max 22rem; title (600) "Clear the board?", secondary --text-sm line, actions "Clear board" (btn-danger) + "Keep marks" (quiet); role=alertdialog labelled/described; Reset carries aria-haspopup=dialog + aria-expanded; focus to "Keep marks" on open, back to Reset on close; Escape = Keep marks — admin.css:.player-confirm
- DESIGN-REGISTER HistoryControls (new state) — Undo/Redo aria-disabled while the board is solved (locked); Reset opens ResetConfirm instead of acting at once — templates/puzzle_solve.html:[data-player-action]
- RENDERS: ~/Documents/nonogram-reviews/CARD-162/ (script card162_render.py; Duck 15×15 through the real image pipeline, real mouse strokes; console clean at 1440 and 390, both motion settings; 0 running animations under reduced motion): errors-mid-solve-1440.png, errors-mid-solve-390.png (3 errors), reset-confirm-1440.png, reset-confirm-390.png, solved-animating-1440.png, solved-animating-390.png (mid-sweep frame), solved-1440.png, solved-390.png, solved-reduced-motion-1440.png, solved-reduced-motion-390.png. The 390 render first showed the confirm clipped off the left edge → anchored left; re-rendered.
- CONCERN (not changed, outside this card): the page header already reads "Puzzle <title>" (CARD-160), so the picture name the solved state "reveals" is visible before solving whenever the puzzle has a name. Owner call whether the header should hide it until solved.
- [Scope] src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_progress.py
- [Scope gate] ⚠ grown: +0 components · 2 files outside Touches (src/nonogram/admin/static/solver_state.js — additive, ADR-0038/R4; tests/test_puzzle_solver_marking.py — CARD-161 tests pinned the unconfirmed reset), both declared SCOPE+
- [Build gate] PASSED (full, 521s) — 6021 passed, 9 skipped, 2 failed = exactly the main-branch baseline (test_size_configuration_applied, test_batch_creation_form_renders); run with PYTHONPATH=<worktree>/src (bare interpreter resolves nonogram to the main repo)
- [Review 1/3] Score: 8.4 — crit: 0, imp: 1 (F-001, pending adversarial verification)
- [Review sync] 1 report(s) → meta/review/
- [Adversarial] F-001 CONFIRMED — setBoard (solver.js:277-290) re-derives progress without the lock, so it unlocks a solved board; header solver.js:79-82 says only reset can
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Fix cycle 1 2026-10-03] F-001: solver.js PROGRESS header no longer says only reset can unlock a solved board — once locked, reset or the setBoard seam (which replaces the board) unlocks it; "Only reset acts" now reads "Of the player's controls only reset acts".
- [Fix cycle 1] F-003 CHANGES the reset confirmation's lifecycle: it now also closes (as "Keep marks": aria-expanded=false, focus back to Reset) on every recorded stroke, undo or redo (button or key, even one that changes nothing) and setBoard while it is open, after the change is recorded. setBoard now records through wireMarking's commit (returned as { refresh, commit }) instead of its own paint/showProgress/refresh sequence; the "Clear board" accept relies on commit to close it. Tests: TestSolverProgress_ResetAfterConfirm::test_a_board_change_while_asking_closes_the_confirmation[undo-key|undo-button|stroke|set-board], ::test_a_board_change_with_the_confirmation_closed_leaves_focus_alone.
- [Fix cycle 1] F-004 CORRECTS the DESIGN-REGISTER SolverBoard "solved" line above: the success outline is now drawn just inside the board's edge (outline-offset = -rule-major, over the outer rules), not at --space-1 outside it — .player-stage's overflow-x:auto clipped the outside frame on top and left. Test: TestSolverProgress_SolvedWhenBlacksMatch::test_the_success_frame_is_not_clipped_by_the_stage. Re-rendered solved-1440/390 and solved-reduced-motion-1440/390 (and the rest of the set) into ~/Documents/nonogram-reviews/CARD-162/; all four sides of the frame show.
- [Fix cycle 1] F-002 CORRECTS the SCOPE+ note above: test_the_marking_code_reads_no_solution checks everything in solver_state.js before "// Progress against the solution" (board section included), not only the stroke/history section.
- [Fix cycle 1] F-005 ADDS to the EC corpus minima above: >= 100 boards per shape with an undecided solution-empty cell (alongside the solution-filled one).
- [Fix cycle 1] F-006 skipped (literals 12ms / 22rem / 2ch / 3px left as is: one-off values; 3px has precedent in .side a).
- [Fix cycle 1] MUTANTS: commit no longer closes the confirm → killed (board_change[undo-key]); closes unconditionally → killed (leaves_focus_alone); setBoard back on its own path → killed (board_change[set-board]); frame offset back to --space-1 → killed (success_frame); corpus never leaves solution-empty cells undecided → killed (EC-037 property); a "solution" read in solver_state.js's board section → killed (reads_no_solution).
- [Fix 1] pre-gate: 9/9 named tests passed (F-001 n/a doc-only, F-002..F-005 named tests); F-006 SKIPPED (optional token nit); declarations: 5 updated (solver.js header ×2, test docstring, admin.css comment, EC corpus note), 0 confirmed, 0 none
- [Build gate] PASSED (full, 505s) — 6027 passed, 9 skipped, 2 failed = main baseline
- [Review 2/3] Score: 8.8 — crit: 0, imp: 1 (F-008, pending adversarial verification); cycle-1 F-001..F-005 ✓ resolved; 8f mutation ran: 9 killed / 1 survived (M7 → F-008)
- [Review sync] 2 report(s) → meta/review/
- [Adversarial] F-008 CONFIRMED — header solver.js:90-93 promises the confirm closes even on a no-op undo/redo; _CHANGES (tests/test_puzzle_solver_progress.py:634-656) holds only board-changing cases; mutant "close only when history changed" passes all 107 progress+marking tests
- [Severity gate 2/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Review 2/3] family regression streak 1 (F-008 attributed to the F-003 fix; first occurrence) — below the escalation threshold of 2
- [Review 2/3] ⚠ improvement stalled — Δscore: 0.4, Δcrit+imp: 0
- [Escalated] 2026-10-03T15:18:37Z — review stalled at 8.8 (Δscore 0.4 < min_improvement 0.5, Δcrit+imp 0); the one gating finding F-008 is a fix-introduced header claim (reset confirm closes 'even on a change that does nothing') with no test — killed mutant M7 survived. Changes NOT committed beyond implementation commit b72e7d7: fix-cycle-1 edits (F-001..F-005) are UNCOMMITTED in the worktree · station: implementation · route: manual fix (add a no-op redo/undo case to _CHANGES in TestSolverProgress_ResetAfterConfirm::test_a_board_change_while_asking_closes_the_confirmation asserting close + focus to Reset, OR drop the 'even one that changes nothing' clause from solver.js header and the [Fix cycle 1] note; optionally F-009 comment wording), then /kanban review CARD-162
- [Unblocked] 2026-10-03 — owner chose: add the no-op test for F-008 + final review cycle (3/3) (dispatcher)
- [F-007] owner decision → follow-up card (player header must hide the picture name until solved); not changed in CARD-162
- [Fix cycle 2] F-008: the PROGRESS "reset" claim that the confirmation closes on a recorded step "even one that changes nothing" is now demonstrated: board_change[redo-key-noop] (Control+Shift+Z with an empty redo stack, confirm open) asserts it closes, aria-expanded="false", focus back on Reset, board unchanged. No production change. MUTANT M7 (close only when the history changed) → killed by board_change[redo-key-noop] only; solver.js restored byte-exact (sha1 e929be51 before/after).
- [Fix cycle 2] F-009: admin.css comment reworded — the success frame sits "just inside the table's edge" (top/left edge is clue boxes / corner cell, not outer rules). Comment only.
- [Fix 2] pre-gate: 5/5 passed incl. test_a_board_change_while_asking_closes_the_confirmation[redo-key-noop]; mutant M7 killed by it (solver.js sha1 e929be51… identical before/after); F-009 comment-only; declarations: 0 updated, 1 confirmed (solver.js header F-008 claim now tested), 1 comment (F-009)
- [Build gate] PASSED (full, 548s) — 6028 passed, 9 skipped, 2 failed = main baseline (after commit e1b8837)
- [Review 3/3] confirmation mode per owner/dispatcher direction (scope verdict still GROWN on the same two declared SCOPE+ files — no new excess since cycle 1; fix delta = tests/test_puzzle_solver_progress.py + admin.css comment)
- [Review 3/3] Score: 9.5 — crit: 0, imp: 0 (Minor F-010 open; F-008/F-009 ✓ resolved, re-derived)
- [Review 3/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Review 3/3] 8f mutation check ran (certification on the passing cycle): 10/11 killed; M11 (undo/redo button skips commit while aria-disabled) survived → Minor F-010
- [Review sync] 3 report(s) → meta/review/
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0038/R2, ADR-0038/R8, ADR-0038/R1); R8 precision: the missing-Chromium fail is tests/test_puzzle_solver_page.py:439 (browser_type override), :453 is the missing-plugin fail — substance holds
- [AC/EC/G check] All criteria/constraints ✓ (evidence): AC-312..AC-321 ✓ demonstrated (named TestSolverProgress_* tests PASSED on real Chromium, 108 passed marking+progress); EC-036 ✓ / EC-037 ✓ demonstrated (random.Random(36), 300 boards × 10x10/15x10/10x25/30x30, >=200 asserted, independent Python oracles _solved_of/_errors_of); G-1 ✓ (no manifest change, only relative import), G-2 ✓ (no hint feature; only pre-existing #puzzle-player-hint), G-3 ✓ (no request/storage APIs; test_solve_and_reset_issue_no_request_store_nothing_and_log_nothing + TestSolverMarking_NoRequestPerMark PASSED, NoRequestPerMark only gained the confirm click)
- [Docs] skipped — no per-directory READMEs under src/ (convention is an open owner decision, backlog); tests/README.md is the stale Wave-1 doc tracked in backlog
- [Commit] success state = e1b8837 (fix delta committed before cycle 3 at the dispatcher's direction; no remaining non-meta changes, so no further commit). Branch: b72e7d7 + e1b8837
- [Review 3/3] open: F-010 Minor (redo/undo BUTTON no-op close untested; M11 survived) · F-006 Minor dismissed · F-007 → owner decision, follow-up card CARD-163
- [Merged] 2026-10-03 — 4b5ed9d into main (--no-ff). Merge gate: the branch's src/tests are exactly e1b8837, the tree that passed the cycle-3 full suite (6028 passed, only the 2 baseline failures); main had moved since 1513c3c by 27490ad only, which touches meta/ alone, so the code under test is unchanged — not re-run. Gate evidence is the `[AC/EC/G check] All criteria/constraints ✓` line (the newer spelling of the done gate's `[AC/EC check]`). Deferral scan: 0 hits. Trace: FR-044 already lists the card's tests. DESIGN-REGISTER applied at close-out (ErrorCounter, SolvedBanner, ResetConfirm, SolverBoard solved + reduced-motion states with the F-004 inside-edge correction, HistoryControls solved/confirm states). F-010 folded into CARD-163; F-007 → CARD-163. Note on the report's PYTHONPATH claim: verified 2026-10-03 that pytest run from a worktree imports the worktree's src/nonogram with or without PYTHONPATH=src (only a bare `python -c` resolves to the main repo's editable install).
