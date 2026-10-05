# CARD-182: Puzzle player cells are a usable tap target on a 390 px phone

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/182-player-phone-tap-target
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (IDEA-057; CARD-161 review finding F-006, CARD-160 cell sizing)
**Idea:** IDEA-057
**Wave:** 34
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_phone.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**
The player's cell side is pure CSS, in `src/nonogram/admin/static/admin.css`:
`.player-board { --player-cell: clamp(var(--player-cell-min), min(100cqi / (cols + row-depth + 1), (100svh − chrome) / (rows + col-depth + 1)), var(--player-cell-max)) }`,
with `--player-cell-min: 14px` and `--player-cell-max: 28px` set on `.player-stage`.
`solver.js:drawBoard` only sets the four inputs (`--player-cols`, `--player-rows`,
`--player-row-depth`, `--player-col-depth`). At 390 px wide the shell's
`@media (max-width: 820px)` block gives `.main` a 16 px padding, so the stage is
358 px wide. Fitting the whole board into 358 px gives cells of about 18 px for a
15×15 (CARD-161 F-006, render player-mid-solve-390.png). The 25×15 and 30×30 boards
hit the 14 px floor and scroll inside `.player-stage` (CARD-160 notes). The page
itself never scrolls sideways.

**Target behaviour.**
On a phone-width screen every board cell is at least **24 px** square (the WCAG 2.2
"target size, minimum" yardstick, 2.5.8). Boards up to 30 wide keep working.

How, and why this way:
1. **Raise the floor below the shell breakpoint only.** Inside a
   `@media (max-width: 820px)` rule, set `.player-stage { --player-cell-min: 24px; }`.
   The clamp formula, the max (28 px) and everything above 820 px stay as they are.
   So desktop sizing does not change, and the 30×30 laptop fit (CARD-160 F12) holds.
2. **Horizontal scroll of the board, as today.** At 24 px, 15 cells are already
   360 px, wider than the 358 px stage, so no clue-gutter trim can make a 15-wide
   board fit. The board keeps scrolling inside `.player-stage` (`overflow-x: auto`,
   already there). The page body still never scrolls sideways.
3. **Panning stays on the clue areas.** Cells keep `touch-action: none`, because a
   touch drag must mark, not scroll (CARD-161). Clue boxes and the corner keep the
   default touch action, so a swipe that starts on the column-clue band pans the
   board. Do not change the cells' touch action.

Rejected, for the record:
- **Smaller clue gutter** — cannot help (point 2), and the clue numbers are already
  0.6 × the cell side.
- **Sticky row clues** — for a 30-wide board with deep clues the row-clue gutter is
  wider than the 358 px stage (15 numbers × 24 px), so a sticky gutter would hide every
  cell.
- **Pinch zoom on cells** (`touch-action: pinch-zoom`) — it would let a two-finger
  gesture cancel strokes mid-drag. A zoomed page still needs a one-finger pan, which
  the cells block anyway.

No JavaScript change. `solver.js:cellUnder` already finds the cell with
`document.elementFromPoint` in viewport coordinates, so a drag on a scrolled board
marks the cells under the finger. The tests must prove that, not assume it.

## Acceptance criteria

- **AC-1** (happy): *Given* a stored 15×15, 25×15 and 30×30 puzzle (the 30×30 with deep row clues), *when* each player page is opened at a 390×844 viewport, *then* every `td.player-cell` measures at least 24 px and at most 28 px wide and high.
  *test: TestSolverPhone_CellsAreATapTarget (in tests/test_puzzle_solver_phone.py)*
- **AC-2** (boundary): *Given* the same three pages at 390×844, *when* the page and the stage are measured, *then* the page's scrollWidth is ≤ the viewport width and `.player-stage` scrolls sideways (its scrollWidth > its clientWidth).
  *test: TestSolverPhone_CellsAreATapTarget (in tests/test_puzzle_solver_phone.py)*
- **AC-3** (boundary): *Given* the deep-row-clue 30×30 puzzle, *when* the page is opened at 820×900 and then at 821×900, *then* its cells are ≥ 24 px at 820 and under 24 px at 821 (the unchanged desktop clamp).
  *test: TestSolverPhone_FloorAppliesOnlyBelowTheShellBreakpoint (in tests/test_puzzle_solver_phone.py)*
- **AC-4** (negative): *Given* the three puzzles of AC-1, *when* each is opened at 1440×900, *then* its cell width equals the value measured on main before this change (pinned in the test, recorded in Worktree notes).
  *test: TestSolverPhone_DesktopSizingUnchanged (in tests/test_puzzle_solver_phone.py)*
- **AC-5** (happy): *Given* the 30×30 page at 390×844 in a touch context with `.player-stage` scrolled to its right end, *when* a touch drag runs along one row across 5 visible cells, *then* exactly those 5 cells (by `data-row`/`data-col`) take the selected tool's state, no other cell changes, and the stage's scrollLeft is unchanged.
  *test: TestSolverPhone_TouchDragMarksOnAScrolledBoard (in tests/test_puzzle_solver_phone.py)*
- **AC-6** (happy): *Given* the same scrolled page, *when* one visible cell is tapped, *then* that cell alone becomes filled.
  *test: TestSolverPhone_TouchDragMarksOnAScrolledBoard (in tests/test_puzzle_solver_phone.py)*
- **AC-7** (boundary): *Given* the 30×30 page at 390×844 in a touch context with the stage at scrollLeft 0, *when* a horizontal touch swipe starts on the column-clue band, *then* the stage's scrollLeft grows and no cell changes state. The computed `touch-action` is `none` on `td.player-cell` and not `none` on the clue boxes.
  *test: TestSolverPhone_SwipingTheCluesPansTheBoard (in tests/test_puzzle_solver_phone.py)*

## Guardrails

- G-1: Desktop sizing is unchanged. `TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen` (both params) passes unedited. Nothing changes at viewports wider than 820 px.
- G-2: The page never scrolls sideways at 390 px. `TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways` passes unedited.
- G-3: Marking is unchanged. `tests/test_puzzle_solver_marking.py` passes unedited, including `test_a_touch_tap_cycles_too`, `test_a_touch_drag_marks_one_line` and `test_a_drag_released_outside_the_board_still_counts`. Cells keep `touch-action: none`.
- G-4: CSS only. `static/solver.js`, `static/solver_state.js` and `templates/puzzle_solve.html` are not edited. CARD-183 (hint button) edits the player JS and template.
- G-5: Progress and solved state are unchanged. `tests/test_puzzle_solver_progress.py` passes unedited (solved outline, reduced motion).
- G-6: No new colour, framework or dependency (ADR-0038/R1). `TestPlayerAssets` and `tests/test_admin_design_tokens.py` pass. The new rule uses a length, no colour literal.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-182` (53 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-044 (the puzzle player; AC-296..AC-311 and AC-322/AC-323 must keep holding). CARD-161 item 5: touch tap and drag must work.
- **ADR:** ADR-0038 (R1 plain static JS/CSS; R2 no request per mark; R7/R8 pytest-playwright with a loud skip)
- **CON:** CON-021 (player is admin-only), CON-011 (sides 10..30, so up to 30 wide)
- **Components:** COMP-009 (Admin Panel); capability CAP-007 Puzzle play
- **Trace:** meta/architecture/trace.yml, `req: FR-044` (add the new test class names to its tests list at merge)

## Design context

- **Screen:** puzzle player, `/puzzle/<id>/solve` (SolverBoard), at phone width.
- **Owner-visible defaults this card picks:**
  - Cells are 24 px on screens up to 820 px wide.
  - So every board 15 or more wide is wider than a 390 px screen and scrolls sideways inside its stage. That includes the 15×15, which fits today at about 18 px.
  - The breakpoint is width-based (the shell's 820 px). A phone in landscape (e.g. 844 px wide) keeps the desktop sizing.
- **Renders:** ~/Documents/nonogram-reviews/CARD-182/ (owner visual check before merge). Real pictures through the image pipeline, as in CARD-160 (duck 15×15, butterfly 25×15, cat 30×30):
  - each at 390×844, fresh and mid-solve
  - the 30×30 at 390 also with the stage scrolled to its right end
  - the 30×30 at 1440×900, to show desktop is unchanged

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-057 — CARD-161 review F-006 (meta/review/20261003T121943Z-CARD-161-cycle1.yml, admin.css:352 at the time): "Phone-width cells are ~18px — below a comfortable tap target", dismissed as out of scope and routed to a follow-up.
- [Facts] admin.css on main at drafting time:
  - `.player-stage` custom properties at lines 383–396 (`--player-cell-min: 14px`, `--player-cell-max: 28px`)
  - the clamp at lines 398–402
  - the marking rules `.player-board { user-select: none }` and `.player-cell { cursor: pointer; touch-action: none; }` at lines 427–428
  - the shell's `@media (max-width: 820px)` block at line 361, which sets `.main { padding: var(--space-4) }` (16 px), so the stage is 358 px wide at 390
- [Placement] Put the new media rule directly after the line-428 marking block, in the board part of the player section. Not in the toolbar rules (lines 433+), where CARD-183's hint button styling is likely to land. That keeps the two cards' admin.css hunks apart.
- [Tests] New file `tests/test_puzzle_solver_phone.py`. Import `browser_page`, `live`, `_open` and the grid helpers from `tests.test_puzzle_solver_page`, as `tests/test_puzzle_solver_marking.py` does (fixtures used by name). Mark the browser tests `@pytest.mark.browser`. Touch contexts: `browser.new_context(has_touch=True, viewport={"width": 390, "height": 844})`. Drive touch drags with CDP `Input.dispatchTouchEvent` (precedent: `test_a_touch_drag_marks_one_line`). For AC-7, if a dispatched touch swipe does not scroll in headless Chromium, use CDP `Input.synthesizeScrollGesture` starting on a column-clue box, and record which one in these notes.
- [AC-4 baseline] Before editing admin.css, measure the 1440×900 cell width of the three seeded test grids on main, and record the three numbers here. The test pins them.
- [Existing tests] No existing test needs editing. `test_a_phone_width_page_never_scrolls_sideways` only asserts that the page does not scroll sideways and that the stage does. `test_the_largest_board_fits_a_laptop_screen` runs at 1440×900. The marking tests run at 1024×768, above the breakpoint.
- [Not in scope] Pre-existing and unchanged: on a phone, a board that fills the screen leaves only the clue areas and the 16 px side gutters as pan or page-scroll surfaces, because cells take every touch for marking. If the owner finds this clumsy in the renders, a pan/mark mode toggle or edge auto-scroll during a drag is its own card. Sticky clues and pinch zoom were rejected (see What to implement).
- [Owner decisions, defaults taken]
  - Floor 24 px, not 28 px.
  - Width-based trigger `(max-width: 820px)`. Adding `, (pointer: coarse)` would also cover phone landscape, but it would enlarge cells on tablets too.
- DESIGN-REGISTER: SolverBoard → Sizing: "cell side clamp(14px, fit, 28px); at viewports ≤ 820 px the floor is 24 px (tap target, CARD-182) and the board scrolls inside `.player-stage`; panning starts on the clue areas, cells keep touch-action none." Candidate token note: `--player-cell-min` is 24px below the breakpoint.
- [AC cross-check] All seven ACs were re-read against What to implement. They agree on the floor (24 px), the trigger (≤ 820 px), the scroll (inside the stage, never the page) and the touch split (cells none, clues default). AC-3 was worded "under 24 px at 821" rather than an exact value because the desktop value comes from the unchanged clamp. Nothing was changed after the check.
