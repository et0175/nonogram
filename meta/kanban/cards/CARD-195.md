# CARD-195: The puzzle player can zoom the board in and out

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 1.0d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/195-player-zoom
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-195
**Source:** owner mobile solver feedback, 2026-10-06 (zoom request, after the phone fit-to-width of CARD-193)
**Idea:** —
**Wave:** 36
**Depends on:** CARD-193, CARD-194
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_zoom.py (new)
**Review score:** 9.3 (cycle 2/3)
**Started:** 2026-10-08T06:10:00Z
**Closed:** 2026-10-08T08:12:48Z
**Actual:** 0.1d
**Merge commit:** 1b4bc97
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**
- The cell side is pure CSS. `src/nonogram/admin/static/admin.css`, `.player-board { --player-cell: clamp(var(--player-cell-min), min(100cqi / (...), (100svh − chrome) / (...)), var(--player-cell-max)) }` (lines 398–402). There is no zoom today.
- `.player-stage` (admin.css 383–396) is `container-type: inline-size; overflow-x: auto`. It scrolls sideways only. The board's height is always fitted to the viewport height through `--player-chrome-h`, so a tall board never scrolls vertically inside the stage.
- `solver.js:drawBoard` (line 211) sets only `--player-cols`, `--player-rows`, `--player-row-depth`, `--player-col-depth` on the table.
- Cells have `touch-action: none` (admin.css line 432). Clue boxes keep the default (CARD-182 AC-7 depends on this).
- `solver.js:wireMarking` (line 462) owns pointer input. Its `pointerdown` handler returns early while a gesture is in progress (line 494), so a second finger is ignored today.
- `solver.js:cellUnder` (line 443) uses `document.elementFromPoint` in viewport coordinates. Any zoom done by layout (not by `transform`) keeps hit-testing correct.
- Phone sizing will change first: CARD-193 (fit-to-width) replaces the 24 px phone floor of CARD-182 with a shrink-to-fit. This card builds on CARD-193's fitted size.

**Target behaviour.**
A zoom level multiplies the fitted cell size. Zoom is a view setting only. It changes no board state.

1. **Range and steps.** 100% to 300% of the fitted size, inclusive. The buttons step by 25 points (100, 125, 150 … 300). Each button moves to the next multiple of 25 in its direction from the current value. A pinch is continuous and clamped to the same range. The readout shows a whole percent (e.g. "150%").
2. **Where it lives in CSS.** `.player-board` cell side becomes `calc(clamp(...) * var(--player-zoom))`. `solver.js:drawBoard` sets `--player-zoom` on the table from the current zoom level, default 1. Font size follows the cell (it is already `calc(var(--player-cell) * 0.6)`), so numerals and rules scale together. Cell width and clue boxes do not change anywhere else.
3. **Controls.** A zoom group in `#puzzle-player-controls`, placed after `.player-history` in `puzzle_solve.html` and before the counters. It holds a "Zoom out" button (−), a readout ("100%") and a "Zoom in" button (+). Buttons are `.btn` with the existing `aria-disabled` pattern (`aria-disabled="true"` at 100% for − and at 300% for +). They stay focusable. The readout is not a live region. The group starts hidden and `solver.js` shows it with the rest of the controls.
4. **Scrolling.** The stage becomes a scroller in both directions. `.player-stage` gets `max-height: calc(100svh − var(--player-chrome-h))` and `overflow: auto`. At 100% on a board that fits, nothing changes. When zoomed, the board scrolls inside `.player-stage`. The page itself never scrolls sideways, at any zoom.
5. **Keep the view.** A button zoom keeps the centre of the stage's visible box on the same board point. A pinch keeps the midpoint of the two fingers on the same board point. Formula, per axis: `scroll' = (scroll + a) × (new ÷ old) − a`, where `a` is the anchor's offset inside the stage's visible box.
6. **Zoom state is not saved.** It is not in the history, not in `serializeState`, and not in localStorage. A reload starts at 100%.

**Pinch rule (exact).** This card decides it. Owner confirmation requested, see Worktree notes.
- (a) Two touch or pen pointers down, with the first one started on a board cell, is a pinch. It zooms the board. It never marks and never scrolls the page.
- (b) A pinch cancels the single-pointer gesture in progress. The preview is removed (`player.show` of the recorded board), `gesture` and `lastClick` are cleared, and nothing is committed. The first pointer's later `pointerup` is ignored. A pinch that ends with one finger still down marks nothing.
- (c) Pinch zoom = starting zoom × (current distance between the two pointers ÷ starting distance), clamped to 100–300%.
- (d) A pinch that starts on a clue box, or outside the board, is not the board's zoom. It keeps the browser's own page pinch (clue boxes keep touch-action auto, as CARD-182 AC-7 requires).
- (e) One-pointer drag is not changed by zoom. With Region on, a drag marks cells (CARD-194). With Region off, a drag scrolls the page (CARD-194). Zoom adds no page scroll and removes none.
- (f) Mouse: no pinch. Trackpad pinch (ctrl+wheel) is the browser's and is not handled here.
- (g) Cells keep `touch-action: none` (CARD-182 G-3). The browser never takes a pinch that starts on a cell.

Rejected, for the record:
- **CSS `transform: scale()` on the table.** The layout box would not grow, so the stage would not scroll to the zoomed board. Layout sizing (`--player-zoom` into `--player-cell`) keeps scroll and hit-testing correct.
- **Native `touch-action: pinch-zoom` on cells.** A pinch would then cancel strokes mid-drag (the reason CARD-182 rejected it).
- **Storing the zoom level.** It is a view setting. Saving it would add a state to CON-021's one allowed store for no owner request.

No change to the cell's width at 100%: the fitted size from CARD-193 is what 100% means.

## Acceptance criteria

- **AC-1** (happy): *Given* a 15×15 page at 390×844 at 100%, *when* the zoom-in button is pressed once, *then* the readout reads "125%" and every `td.player-cell` is 1.25 × its 100% width (±0.5 px).
  *test: TestSolverZoom_ButtonsStepAndClamp (in tests/test_puzzle_solver_zoom.py)*
- **AC-2** (boundary): *Given* the page at 100%, *when* zoom-out is pressed, *then* nothing changes and zoom-out has `aria-disabled="true"`; *given* the page at 300%, *when* zoom-in is pressed, *then* nothing changes and zoom-in has `aria-disabled="true"`.
  *test: TestSolverZoom_ButtonsStepAndClamp (in tests/test_puzzle_solver_zoom.py)*
- **AC-3** (negative, no solve-state change): *Given* a 15×15 page with five cells marked, an undo available and the errors and progress counters showing, *when* the zoom goes 100% → 300% → 100%, *then* every `data-state`, the errors count, the progress percent, the hints counter, the undo/redo `aria-disabled` values and the localStorage entry are unchanged.
  *test: TestSolverZoom_ChangingZoomChangesNoSolveState (in tests/test_puzzle_solver_zoom.py)*
- **AC-4** (happy, scrolling): *Given* the 30×30 deep-row-clue page at 390×844, *when* the zoom is 300%, *then* the stage scrolls sideways and vertically (scrollWidth > clientWidth and scrollHeight > clientHeight), the page's scrollWidth is ≤ 390, and the stage's clientHeight is ≤ 844.
  *test: TestSolverZoom_TheBoardScrollsInsideItsStage (in tests/test_puzzle_solver_zoom.py)*
- **AC-5** (happy, anchor): *Given* the 30×30 page at 300% with the stage scrolled to its centre, *when* zoom-out is pressed, *then* the board cell that was at the centre of the stage's visible box is still within one cell of that centre.
  *test: TestSolverZoom_ZoomKeepsTheViewCentre (in tests/test_puzzle_solver_zoom.py)*
- **AC-6** (happy, pinch): *Given* the 15×15 page at 390×844 with the Black brush, *when* a two-finger pinch on a cell spreads the fingers from 100 px to 200 px apart, *then* the readout reads "200%" (±1), no cell changes state, and the page's scrollX and scrollY stay 0.
  *test: TestSolverZoom_PinchOnTheBoardZooms (in tests/test_puzzle_solver_zoom.py)*
- **AC-7** (boundary, pinch cancels a stroke): *Given* a one-finger drag with Region on that has passed over three cells, *when* a second finger lands on a cell, *then* the three cells return to their recorded state at once, and lifting both fingers marks nothing and records nothing.
  *test: TestSolverZoom_PinchCancelsTheStrokeInProgress (in tests/test_puzzle_solver_zoom.py)*
- **AC-8** (boundary, pinch on clue boxes): *Given* a two-finger pinch that starts on a column-clue box, *when* the fingers spread, *then* the board's readout is unchanged and the start element's computed `touch-action` is not `none`.
  *test: TestSolverZoom_PinchOnAClueBoxIsNotTheBoardsZoom (in tests/test_puzzle_solver_zoom.py)*
- **AC-9** (negative, drag unchanged): *Given* Region on (CARD-194) at 200%, *when* a one-finger drag runs along one row across five visible cells, *then* exactly those five cells change state.
  *test: TestSolverZoom_OneFingerDragIsUnchangedByZoom (in tests/test_puzzle_solver_zoom.py)*
- **AC-10** (boundary, sizing): *Given* a 15×15 page at 1440×900, *when* the zoom is 100% and then 200%, *then* the cell widths are 28 px and then 56 px (±0.5 px); 28 px is the CARD-182 desktop value.
  *test: TestSolverZoom_HundredPercentIsTheFittedSize (in tests/test_puzzle_solver_zoom.py)*
- **AC-11** (happy, tap targets): *Given* the page at 390×844, *when* the zoom controls are measured, *then* each button is at least 24 × 24 px, and at 300% every `td.player-cell` is at least 24 px square.
  *test: TestSolverZoom_TapTargetsAreAtLeast24px (in tests/test_puzzle_solver_zoom.py)*
- **AC-12** (negative, no save, no request): *Given* a zoom change, *when* it is made and the page is reloaded, *then* no network request is made, the localStorage entry is unchanged, and the zoom reads 100% after the reload.
  *test: TestSolverZoom_IsNotSavedAndSendsNothing (in tests/test_puzzle_solver_zoom.py)*

## Guardrails

- G-1: Board state, history and save are unchanged. `tests/test_puzzle_solver_marking.py`, `tests/test_puzzle_solver_progress.py` and `tests/test_puzzle_solver_resume.py` pass unedited. `solver_state.js` board functions (`record`, `undo`, `redo`, `serializeState`, `deserializeState`) are not edited; only the zoom arithmetic is added to it.
- G-2: 100% is the fitted size. `TestSolverPhone_DesktopSizingUnchanged` (tests/test_puzzle_solver_phone.py, the pinned 28 / 28 / 16.797 px at 1440×900) and `TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen` (tests/test_puzzle_solver_page.py) pass unedited. The zoom group must not push the board's fit at 1440×900. If the toolbar wraps and changes this, stop and report.
- G-3: The page never scrolls sideways at 390 px. `TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways` passes unedited, at 100% and at 300% (AC-4 covers 300%).
- G-4: Touch rules from CARD-182 hold. `TestSolverPhone_SwipingTheCluesPansTheBoard` and `TestSolverPhone_TouchDragMarksOnAScrolledBoard` (tests/test_puzzle_solver_phone.py) pass unedited. Cells keep `touch-action: none`; clue boxes keep the default.
- G-5: No request per mark and no new dependency. `TestSolverMarking_NoRequestPerMark` (tests/test_puzzle_solver_marking.py), `TestPlayerAssets` and `tests/test_admin_design_tokens.py` pass unedited. The new rules use lengths and existing tokens, no colour literal and no framework (ADR-0038/R1, R2).
- G-6: Existing controls keep their DOM order. The zoom group is appended after `.player-history` and before the counters. The Tab order and the counter order tests (`tests/test_puzzle_solver_hint.py::test_dom_order_and_boxes`, `tests/test_puzzle_solver_percent.py::test_order_text_and_style`) pass unedited.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-195` (53 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-044 (the puzzle player; AC-296..AC-365 must keep holding). This card adds view behaviour only.
- **ADR:** ADR-0038 (R1 plain static JS/CSS; R2 no request per mark; R4 state logic in a pure module with no DOM, which the zoom arithmetic joins; R7/R8 browser tests with a loud skip).
- **CON:** CON-021 (player is admin-only; the one allowed browser save is unchanged and zoom is not written to it). CON-011 (sides 10..30, so up to 30 wide). CON-020 does not apply: it governs interior print type only.
- **Components:** COMP-009 (Admin Panel); capability CAP-007 Puzzle play.
- **Trace:** meta/architecture/trace.yml, `req: FR-044` (add `TestSolverZoom_*` class names to its tests list at merge).

## Design context

- **Screen:** puzzle player, `/puzzle/<id>/solve` (SolverBoard), at phone width (390 px) and desktop (1440×900).
- **Owner-visible defaults this card picks:**
  - Zoom range 100% to 300%, steps of 25 points on the buttons. Pinch is continuous.
  - The zoom group sits in the toolbar after the history group, with a plain "100%" readout between − and +.
  - When zoomed in, the board scrolls inside its stage in both directions. Before this card, a board never scrolled vertically inside the stage.
  - At 300% on phone, the board is much larger than the screen. Panning is by the stage's scroll bars or by a drag on the clue bands (CARD-182 AC-7). One-finger drags on cells follow CARD-194.
  - Zoom resets to 100% on every page load.
- **Renders:** ~/Documents/nonogram-reviews/CARD-195/ (owner visual check before merge). Real pictures through the image pipeline, as in CARD-160 (duck 15×15, butterfly 25×15, cat 30×30):
  - phone 390×844: 15×15 and 30×30 with deep row clues, each at 100%, 200% and 300%
  - desktop 1440×900: the same two boards at 100%, 200% and 300%
  - the 30×30 at 300% on phone with the stage scrolled to its centre
  - a mid-pinch frame on phone (two fingers, zoom about 200%)

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-XXX not yet assigned (owner mobile solver feedback, 2026-10-06, zoom request). Create the IDEA entry at roadmap time.
- [Dependencies] Merge order: CARD-193 (fit-to-width, phone) → CARD-194 (brush dropdown and Region drag) → CARD-195. Do not start this card until both are merged. This draft was written before CARD-193 and CARD-194 existed on disk (checked 2026-10-06, `meta/kanban/cards/`). It assumes the owner-decided shapes: fitted cell size from CARD-193 with no 24 px phone floor, and a Region option whose drag marks cells while the other brushes' drags scroll the page. Re-check both assumptions when those cards are drafted and fix this card if they differ.
- [Supersession] CARD-182's 24 px phone floor (`@media (max-width: 820px) { .player-stage { --player-cell-min: 24px; } }`, admin.css line 437) is superseded by CARD-193 (owner decision 2026-10-06). This card does not restore it. The 14 px desktop floor and CARD-182's desktop rules are unchanged.
- [Owner decision] "The 24 px tap-target rule of the desktop/tablet mode": no such rule exists in the code. CARD-182 states the 24 px rule for phone width (≤ 820 px) only. This card applies 24 px to the zoom buttons (AC-11) and to cells at 300% (AC-11). Confirm with the owner.
- [Facts] Current line numbers: admin.css `.player-stage` 383–396, `.player-board` clamp 398–402, `.player-cell` touch-action 432, the CARD-182 media rule 437. solver.js `drawBoard` 211, `cellUnder` 443, `wireMarking` 462, `pointerdown` early return 494.
- [Facts] `--player-chrome-h` (admin.css 392) is not changed by this card. The zoom group is inside the toolbar, which is already in that height. If the toolbar wraps at 1440 px, see G-2.
- [Pinch implementation] Track active touch and pen pointers in `wireMarking` (a Map of pointerId → position). When a second one lands on a cell (whether or not a single-pointer gesture is in progress), run the pinch rule from What to implement. The pinch's own `pointerup` events commit nothing. Zoom value lives in solver.js (view state). The arithmetic (clamp, step, next level, anchor scroll) lives in `solver_state.js` as pure functions with no DOM access (ADR-0038/R4), so the browser test can cover them with plain values too.
- [Tests] New file `tests/test_puzzle_solver_zoom.py`. Browser tests use `@pytest.mark.browser` and the CARD-160 fixtures (a missing Chromium fails loudly, ADR-0038/R8). Pinch uses CDP `Input.dispatchTouchEvent` with two touch points (precedent: `TestSolverPhone_TouchDragMarksOnAScrolledBoard` in tests/test_puzzle_solver_phone.py). Region tests (AC-7, AC-9) depend on CARD-194's control; use the control it defines.
- [AC cross-check] All twelve ACs were re-read against What to implement. They agree on: 25-point steps and the 100–300% range (AC-1, AC-2 vs item 1); the anchor rule (AC-5 vs item 5); pinch cancels, does not commit and does not scroll (AC-6, AC-7 vs pinch rule b, a); the clue-box exception (AC-8 vs pinch rule d); zoom not saved (AC-12 vs item 6). Nothing was changed after the check.
- [Owner decisions taken as default, confirm]
  - Range 100–300%, steps 25 points.
  - Zoom group after the history group in the toolbar.
  - Stage scrolls vertically too when zoomed (item 4).
  - Pinch that starts on a clue box or outside the board stays the browser's page pinch (rule d).
  - Zoom is not saved; reload resets to 100%.
- [Open, owner decision] Clue numeral legibility. There is no standing floor for player text. CON-020 covers only the interior print type and was amended 2026-10-06 for book pages. At 100% on a 390 px phone, a 30-wide board after CARD-193 may give cells of about 11 px and numerals of about 6–7 px (cell × 0.6). This card adds no floor. Zoom is the remedy the card provides. The owner should decide whether player numerals need a minimum size, and whether it should be a CON.
- [Open, owner decision] Scroll mechanism for a one-finger drag with Region off. Cells keep `touch-action: none`, so a drag on a cell cannot scroll the page natively. CARD-194 must say how it scrolls. If CARD-194 switches cells to `pan-x pan-y` for that case, the pinch on cells must be re-verified on a real touch device before merge, because a native pan can take the second finger's pointer events.
- [DESIGN-REGISTER] SolverBoard → Sizing (meta/design/components.md, line 224 onward): add "zoom 100–300% multiplies the fitted cell side (--player-zoom); the stage scrolls both ways when zoomed; pinch on a cell zooms the board, a pinch elsewhere is the browser's." Add a line for the zoom group under the toolbar. Counted as a DESIGN-REGISTER line, not a file change under meta/.
- [Env] forge 2026.8.17
- [Owner decision] 2026-10-06 — zoom buttons are at least 24 px.
- [Implementation complete, 2026-10-08] All 12 ACs implemented and verified by `tests/test_puzzle_solver_zoom.py` (18 tests: one `TestSolverZoom_*` class per AC, plus `TestZoomArithmetic_PureFunctions` for the new `solver_state.js` exports — `clampZoom`, `stepZoom`, `pinchZoom`, `anchoredScroll`), all green against real Chromium. All 6 guardrails pass unedited.
- [AC/EC check] Final consolidated run (not just incidental dev runs): `tests/test_puzzle_solver_zoom.py` (18) + `TestSolverMarking_NoRequestPerMark` + `test_puzzle_solver_progress.py` (all) + `test_puzzle_solver_resume.py` (all) + `TestSolverPhone_DesktopSizingUnchanged` + `TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen` + `TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways` + `TestSolverPhone_SwipingTheCluesPansTheBoard` + `TestSolverPhone_TouchDragMarksOnAFittedBoard` (renamed by CARD-193 from `...OnAScrolledBoard`, named in this card's own G-4 under the old name — same test, unedited) + `TestPlayerAssets` + `test_admin_design_tokens.py` (all) + `test_dom_order_and_boxes` + `TestSolverPercent_SitsNextToTheCounters` — **109 passed, 0 failed**. Full suite (lock protocol, acquired/released cleanly): **6691 passed, 9 skipped, 0 failed, 865.80s**.
- [Regression found and fixed] The zoom group's first layout pushed `.player-toolbar` to wrap at 1280 px, failing `test_puzzle_solver_percent.py::TestSolverPercent_SitsNextToTheCounters::test_shares_the_buttons_row_at_1280` (not a named guardrail test, caught only by running the whole file rather than the named subset). Fixed in `admin.css` by narrowing `.player-zoom .btn` to a literal 5px side padding (no `--space-*` token lands between the 4px/8px pair and the width this needed) and the group's own gap to `--space-1`; re-verified green, buttons still clear the 24 px AC-11 floor (measured 25.3 px).
- [Mutation testing] 8 mutants applied and killed, each reverted and confirmed via `git diff`: `clampZoom` min/max swap, `stepZoom` off-by-one (both directions covered a priori, one applied), `pinchZoom` ratio inversion, `anchoredScroll` sign flip, the pinch rule (a)/(d) boundary condition flip, admin.css's `--player-zoom` CSS multiply removed, admin.css's stage vertical-overflow removed, and `applyZoom`'s scroll-adjustment calls stubbed to no-ops.
- [Review] forge:review cycle 1/3 — score 9.0, 0 Critical, 0 Important, 3 Low/Info (non-gating): (1) the literal 5px CSS padding above — acceptable, G-5 restricts colour literals only, and admin.css already carries many literal px lengths; (2) the pinch's own anchor-keeping (target behaviour #5's pinch half) has no dedicated AC-level browser assertion the way AC-5 checks the button case — covered only at the pure-function level plus AC-6's weaker "scrollX/scrollY stay 0" check; (3) the pinch-vs-native-gesture rule (a)/(d) boundary is verified only via CDP-synthetic touch events, not a real touch device — this is the same open item the card's own Worktree notes already flag below, carried forward unresolved. YAML report: `meta/review/20261008T071332Z-CARD-195-cycle1.yml` (worktree only, per protocol — not committed).
- [Renders] 14 PNGs in `~/Documents/nonogram-reviews/CARD-195/`, produced through the real running admin app (`create_app()`) + real Playwright/Chromium. Real pictures actually used (see the card's own "or whatever is actually available — name what you use"): `pictures/duck.png` (15×15) and `pictures/wolf_face.png` (30×30) — **not** cat, which this environment's `pictures/cat.jpg` measured at only a 2-run-deep row clue (a cat silhouette is mostly one blob); `wolf_face.png` measured 5 runs in its deepest row, a materially better demonstration of the clue-legibility problem zoom exists to solve. Coverage: phone 390×844 and desktop 1440×900 × {100%, 200%, 300%} for both boards; the 30×30 at 300% on phone scrolled to the stage's centre; a mid-pinch frame on phone (two real CDP touch points, duck15, readout 200%).
- [Success commit] `49aec83` on `card/195-player-zoom` (exactly the Touches list: `admin.css`, `solver.js`, `solver_state.js`, `puzzle_solve.html`, `tests/test_puzzle_solver_zoom.py` — nothing under `meta/`). Not merged — per the dispatcher pipeline, the actual `git merge` and owner confirmation happen at the dispatcher level, not in this pass.
- [Open, owner decision — unresolved, carried from above] Clue numeral legibility floor remains open (see above). The pinch-vs-native-gesture real-device re-verification item is now **partially resolved** — see the next entry; a real-device check is still recommended but the specific risk the card's Worktree notes anticipated turned out to be catchable (and was caught) in automation.
- [Bug found and fixed, 2026-10-08, cycle 2] The owner's visual inspection of `midpinch-duck15-phone-200.png` caught upside-down column-clue numerals. Investigation (CDP `Page.getLayoutMetrics`, the actual ground truth, not a JS-spoofable reading) confirmed a real, reproducible bug: a two-finger pinch on a board cell with Region off (AC-6's own scenario, and the default brush) committed a genuine **native browser page pinch-zoom** alongside this card's own `--player-zoom` — `window.visualViewport.scale` settled at `~1.538` with a nonzero pan offset after the exact gesture AC-6 exercises. The native zoom commits *asynchronously* (not visible immediately after `touchend`, only after a short settle), which is exactly why cycle 1's AC-6 test — checking only `window.scrollX`/`scrollY`, which genuinely do stay 0 — never caught it.
  - Root cause: `.player-cell`'s `touch-action` was `auto` whenever Region is off. `touch-action` is evaluated by the compositor thread *before* any JS runs, so `solver.js`'s own `preventDefault()` calls (the second finger's `pointerdown`, every `pointermove` during the pinch) could never retroactively cancel a native pinch-zoom gesture the compositor had already committed to recognizing — no amount of additional JS-side prevention can fix this; only `touch-action` itself can.
  - Fix (`admin.css`): `.player-cell { touch-action: auto }` → `touch-action: pan-x pan-y` for the Region-off case only (the Region-on case, `touch-action: none`, is untouched). `pan-x pan-y` keeps single-finger panning identical to `auto` (confirmed: every actual pan/drag behavioral test in `test_puzzle_solver_phone.py` and `test_puzzle_solver_brush_menu.py` stayed green, unedited) while dropping the browser's own pinch-zoom/double-tap-zoom eligibility.
  - Test impact: exactly one guardrail assertion needed its literal expected value corrected, `tests/test_puzzle_solver_phone.py::TestSolverPhone_SwipingTheCluesPansTheBoard::test_cells_take_no_touch_action_and_clue_boxes_keep_the_default` (`"auto"` → `"pan-x pan-y"`, with a comment citing this investigation) — a coordinator-approved SCOPE+ (outside this card's own Touches list, justified since the fix necessarily changes that literal CSS value and the *behavior* the guardrail exists to protect, panning, is unchanged and still green). `tests/test_puzzle_solver_zoom.py`'s AC-6 test was strengthened with a settle wait + a `window.visualViewport.scale === 1` assertion, closing the exact gap that let this ship; mutation-verified by reverting the CSS fix and confirming the assertion fails with the precise value from the original bug (`1.5384615659713745`), then passes again on revert.
  - Second, separate finding during this investigation: one specific `(grid, anchor cell, zoom)` combination reached via real touch input (`duck15` + cell (7,7) + 200%) deterministically (7/7) corrupts one column-clue box's rendered text glyphs in this exact headless-Chromium + software-SwiftShader environment — confirmed unrelated to the bug above (`visualViewport.scale` stays 1 throughout with the fix in place) and not a code defect anywhere in this diff (DOM text content, `--player-zoom`, scroll position all verified correct; only the painted pixels are wrong, and only for this one path — reaching the equivalent scroll position via button-zoom + a JS-set `scrollLeft`, with no touch at all, renders cleanly). Not fixed in code (nothing in this diff is wrong); worked around for the owner render by using cell (3,3) instead of (7,7) for the mid-pinch frame screenshot, confirmed clean. Documented inline in the render script and here for anyone who hits a similar artifact in this environment later.
  - Review cycle 2/3: 9.3, 0 Critical, 0 Important remaining (YAML: `meta/review/20261008T075450Z-CARD-195-cycle2.yml`). Full suite re-run clean after the fix: 6691 passed, 9 skipped, 0 failed.
  - Renders re-generated with the fix and the corrected anchor cell; all 14 re-verified clean.
- [Success commit] `49aec83` (feature) then `9a1feee` (this fix) on `card/195-player-zoom`. `9a1feee` touches exactly: `admin.css`, `tests/test_puzzle_solver_phone.py` (the approved SCOPE+), `tests/test_puzzle_solver_zoom.py` — nothing under `meta/`. Not merged — per the dispatcher pipeline, the actual `git merge` and owner confirmation happen at the dispatcher level, not in this pass.
- [Owner render check] 2026-10-08 — owner's own inspection of the renders caught the upside-down mid-pinch numerals (see the bug note above), prompting the cycle-2 investigation and fix. After the fix, owner reviewed the corrected render set (zoom readout, toolbar placement, legible 300% numerals, a clean mid-pinch frame) and approved merging.
- [Success] Commit `9a1feee` stands as this card's final success commit (on top of `49aec83`). Only `meta/` artefacts (this card's own notes, both review-cycle YAMLs) remained uncommitted in the worktree, synced into the main repo instead.
