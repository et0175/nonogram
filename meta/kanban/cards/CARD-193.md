# CARD-193: The puzzle player fits big boards to the phone width and mirrors row clues on the right above 15 cells

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/193-player-mobile-fit
**Worktree:** —
**Source:** owner mobile solver feedback, 2026-10-06 (owner decisions on phone fit and mirrored row clues)
**Idea:** —
**Wave:** 36
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_mirror.py, tests/test_puzzle_solver_page.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_maybe.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**
- `admin.css` `.player-stage` sets `--player-cell-min: 14px` and `--player-cell-max: 28px` (lines 383-386). `.player-board` sets `--player-cell` to `clamp(min, min(100cqi / (cols + row-depth + 1), (100svh − chrome) / (rows + col-depth + 1)), max)` (lines 398-402).
- CARD-182 raised the floor below the shell breakpoint with `@media (max-width: 820px) { .player-stage { --player-cell-min: 24px; } }` (line 437). At 390 px the stage is 358 px wide, so a 30×30 with a 15-number row clue scrolls inside `.player-stage` at 24 px cells.
- `solver.js:drawBoard` (lines 211-254) puts the row-clue box first in every body row (`line.append(box)` before the cell loop). The head row is `td.player-corner` followed by the column-clue boxes. `solver.js:clueBox` (lines 195-209) builds each box.

**Target behaviour.**
1. **Phones (≤ 820 px): the board fits the stage width.** Below 820 px the cell floor goes to 0 px (or another value that never binds), so the clamp returns the fit value. The board never scrolls sideways. `.player-stage` keeps `overflow-x: auto` as a safety net, but at 390 px it should never scroll. The 28 px cap stays. Above 820 px nothing changes (14 px floor, 28 px cap).
   - Estimate from the formula: at 390 px a 15-wide board whose deepest row clue has about 8 numbers gets cells of about 15 px. A 30-wide board with a 15-number row clue gets cells of about 8 px (358 / (30 + 15 + 1)). The implementer measures the real values and records them in Worktree notes.
   - This supersedes CARD-182's 24 px phone floor for the phone case. Owner decision, 2026-10-06 (recorded in Worktree notes).
2. **Boards wider than 15 mirror their row clues to the right.** Width means the number of columns (W in W×H). In `solver.js:drawBoard`, when `width > 15` the table gets the class `is-mirrored`. Each body row then puts its row-clue box after the cells, and the head row's corner moves to the end, after the last column clue. The row clues stay in top-to-bottom order.
   - CSS flips the sides that `.player-corner` and `.player-clue.is-row` use (lines 413 and 417): the heavy line sits on the left of the row clues, the text is left-aligned, and the padding is on the right. The rules keyed on `:last-child` (lines 415 and 420) are re-keyed so the heavy line between the last column and the row clues stays heavy, and no line gains or loses weight.
   - The mirror applies at every viewport width (see the first ambiguity below). It changes placement only, not sizes: the cell formula is symmetric in cols and row-depth, so every cell size at 1440 px is unchanged.
3. **Marking, clue numbers and circles keep working.** Cells keep `touch-action: none`, and the clue boxes keep `auto`. Clue circles (CARD-188), hints, progress and the solved state find their elements by class, so they do not depend on the side.

Rejected, for the record:
- Keep a 24 px floor and scroll (the owner decided against it).
- Mirror with CSS `direction` or flex order. A table cannot reorder its cells that way without reversing the columns too, so the placement is done in JS.
- Redraw the board on the breakpoint. The mirror depends on the board's width, not the viewport, so no redraw is needed.

Not in this card: the brush dropdown (owner decision, 2026-10-06). That is CARD-194, which also edits `solver.js` and the player template (see Worktree notes for the merge order).

## Acceptance criteria

- **AC-1** (happy): *Given* stored 15×15, 20×20, 25×25 and 30×30 puzzles (the 30×30 with a 15-number row clue), *when* each player page opens at 390×844, *then* every `td.player-cell` has the same side, the board's right edge is inside the stage's right edge, and the stage's scrollWidth is ≤ its clientWidth.
  *test: TestSolverPhone_BoardFitsThePhoneWidth (in tests/test_puzzle_solver_phone.py)*
- **AC-2** (boundary): *Given* the 30×30 with a 15-number row clue, *when* its page opens at 390×844, *then* its cells are narrower than 14 px (the old floor no longer applies) and the page's scrollWidth is ≤ the viewport width.
  *test: TestSolverPhone_BoardFitsThePhoneWidth (in tests/test_puzzle_solver_phone.py)*
- **AC-3** (boundary): *Given* the 30×30 with a 15-number row clue, *when* its page opens at 820×900 and then at 821×900, *then* at 820 the board fits its stage with no stage scroll, and at 821 every cell is at least 14 px (the desktop floor still applies).
  *test: TestSolverPhone_FitAppliesOnlyAtOrBelowTheShellBreakpoint (in tests/test_puzzle_solver_phone.py)*
- **AC-4** (negative): *Given* the 15×15, 25×15 and 30×30 puzzles of CARD-182, *when* each opens at 1440×900, *then* its cell width equals the pinned desktop value (28, 28, 16.797 px).
  *test: TestSolverPhone_DesktopSizingUnchanged (in tests/test_puzzle_solver_phone.py) — unchanged*
- **AC-5** (happy): *Given* a 25×15 board, *when* it is drawn at 390×844 and at 1440×900, *then* in every body row the row-clue box is the last child and the first child is a `td.player-cell`, the head row ends with `td.player-corner`, and the row clues read top to bottom in payload order.
  *test: TestSolverMirror_RowCluesOnTheRightAboveFifteen (in tests/test_puzzle_solver_mirror.py)*
- **AC-6** (boundary): *Given* a 15-wide board (15×25) and a 16-wide board (16×15) at 390×844, *when* each is drawn, *then* the 15-wide board keeps the row clue first in each row and the 16-wide board has it last.
  *test: TestSolverMirror_RowCluesOnTheRightAboveFifteen (in tests/test_puzzle_solver_mirror.py)*
- **AC-7** (boundary): *Given* the mirrored 25×15 at 1440×900, *when* its borders are read, *then* the heavy vertical lines are after every fifth column and on the line between the last column and the row clues, and every other vertical line is thin.
  *test: TestSolverMirror_HeavyLinesMatchTheLeftLayout (in tests/test_puzzle_solver_mirror.py)*
- **AC-8** (happy): *Given* the mirrored 25×15 at 390×844 with the Black tool, *when* one cell in the rightmost column is tapped, *then* that cell alone becomes filled.
  *test: TestSolverMirror_MarkingWorksOnAMirroredBoard (in tests/test_puzzle_solver_mirror.py)*
- **AC-9** (happy): *Given* the 30×30 with a 15-number row clue at 390×844, *when* a touch drag runs along one row across 5 cells with the page scrolled so that row is mid-screen, *then* exactly those 5 cells take the selected tool's state and no other cell changes.
  *test: TestSolverPhone_TouchDragMarksOnAFittedBoard (in tests/test_puzzle_solver_phone.py, renamed from TestSolverPhone_TouchDragMarksOnAScrolledBoard)*
- **AC-10** (negative): *Given* the 30×30 with a 15-number row clue at 390×844, *when* the cells' computed `touch-action` is read, *then* cells are `none` and every column clue, row clue and the corner is `auto`.
  *test: TestSolverPhone_SwipingTheCluesPansTheBoard (in tests/test_puzzle_solver_phone.py) — the touch-action test, unchanged*
- **AC-11** (happy): *Given* a 30×30 at 390×844, *when* the page is measured, *then* the page's scrollWidth is ≤ the viewport width and `.player-stage` does not scroll sideways.
  *test: TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways (in tests/test_puzzle_solver_page.py) — edited*

## Guardrails

- G-1: Desktop sizing is unchanged. `TestSolverPhone_DesktopSizingUnchanged` (3 params), `TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen` (2 params) and the 1440 params of `tests/test_puzzle_solver_clues.py` pass unedited. The cell side at 1440 does not change.
- G-2: Marking is unchanged. `tests/test_puzzle_solver_marking.py` passes unedited, including the touch tap and drag cases at 1024×768.
- G-3: Touch split is unchanged. Cells keep `touch-action: none`; clue boxes and the corner keep `auto`.
- G-4: Progress, solved state, resume and hints are unchanged. `tests/test_puzzle_solver_progress.py`, `tests/test_puzzle_solver_resume.py`, `tests/test_puzzle_solver_hint.py` and `tests/test_puzzle_solver_percent.py` pass unedited, including their 390 px layout checks.
- G-5: No new colour literal, framework or dependency (ADR-0038/R1). `TestPlayerAssets` and `tests/test_admin_design_tokens.py` pass.
- G-6: `static/solver_state.js` and `templates/puzzle_solve.html` are not edited (ADR-0038/R4: the state module stays pure). CARD-182's G-4 ("CSS only") is superseded for this card, because `solver.js` changes for the mirror.
- G-7: No request per mark (ADR-0038/R2, `TestSolverMarking_NoRequestPerMark` passes unedited).
- G-8: Other edits to tests are limited to the list in Worktree notes. Any other failing test is a regression, not a test to edit.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-193` (53 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-044 (the puzzle player). AC-354 ("no horizontal scroll at 390 px") still holds. AC-343 (CARD-186, "?" glyph at 390) has a phone case that pins the 24 px floor; see Worktree notes.
- **ADR:** ADR-0038 (R1 plain static JS and CSS; R2 no request per mark; R4 pure state module; R7 and R8 browser tests with a loud skip).
- **CON:** CON-021 (the player is admin-only), CON-011 (sides 10 to 30, so up to 30 wide).
- **Components:** COMP-009 (Admin Panel); capability CAP-007 (Puzzle play).
- **Trace:** meta/architecture/trace.yml, `req: FR-044` (add the new test class names to its tests list at merge).

## Design context

- **Screen:** puzzle player, `/puzzle/<id>/solve` (SolverBoard, with ClueBox), at phone width (390 px) and at the 820 px breakpoint.
- **Owner-visible defaults this card picks:**
  - On phones the board fills the 358 px stage. Cells are about 15 px on a 15-wide board and about 8 px on a 30-wide board with deep row clues (formula estimate; the render shows the real size).
  - Clue numerals and the "?" glyph are 0.6 × the cell side, so on the smallest boards they are about 5 px. They are hard to read on a phone. The owner must accept this (see the second ambiguity below).
  - Boards wider than 15 show row clues on the right, at every width.
- **Renders:** ~/Documents/nonogram-reviews/CARD-193/ (owner visual check before merge). Real pictures through the image pipeline, at 390×844, each board in two versions:
  - 15×15, 20×20, 25×25 and 30×30, each with mirrored clues (the new layout) and without (the same board rendered from main, showing the old left clues).
  - Each render fresh and mid-solve.
  - The 30×30 at 1440×900 with mirrored clues, to show that desktop sizing is unchanged.

## Worktree notes

- [Origin] Owner mobile solver feedback, 2026-10-06. No IDEA id was given.
- [Owner decision] Phone (≤ 820 px): boards scale to fit the width, cells shrink, no sideways scroll. This SUPERSEDES CARD-182's 24 px phone floor for the phone case. CARD-182's desktop rules (the 14 px floor and 28 px cap above 820 px) are unchanged. [Owner decision]
- [Owner decision] Boards wider than 15 mirror their row clues to the right. [Owner decision]
- DESIGN-REGISTER: `meta/design/components.md`, SolverBoard, the paragraph "Sizing on phones (CARD-182)". Replace it with: "Sizing on phones (CARD-193): at viewports ≤ 820 px the cell floor is removed; the board fits the stage width and never scrolls. Boards wider than 15 show their row clues on the right (`is-mirrored`), at every width. The 24 px floor of CARD-182 is superseded." Also update the ClueBox entry: row clues sit on the left, or on the right for boards wider than 15. Meta files are not in the card commit, so this is a register line, not a Touches entry.
- [CARD-182 tests that change] In `tests/test_puzzle_solver_phone.py`, 11 of CARD-182's 15 tests change. The reasons:
  - `TestSolverPhone_CellsAreATapTarget::test_every_cell_is_between_24_and_28_px` (3 params): pins the 24 px floor. Becomes: all cells share one side, which is at most 28 px, and the board fits.
  - `TestSolverPhone_CellsAreATapTarget::test_the_board_scrolls_in_its_stage_and_the_page_does_not` (3 params): asserts the stage scrolls. Becomes: the stage does not scroll and the page does not either (AC-1, AC-2).
  - `TestSolverPhone_FloorAppliesOnlyBelowTheShellBreakpoint::test_820_gets_the_floor_and_821_the_desktop_clamp`: asserts ≥ 24 px at 820. Renamed `TestSolverPhone_FitAppliesOnlyAtOrBelowTheShellBreakpoint` (AC-3).
  - `TestSolverPhone_TouchDragMarksOnAScrolledBoard` (2 tests) and `_scrolled_phone_page`: assert `scrollLeft > 0` as a precondition. The board no longer scrolls on a phone. The class is renamed `TestSolverPhone_TouchDragMarksOnAFittedBoard`, and the scroll precondition is removed (AC-9). The page is still scrolled vertically so row 12 is mid-screen.
  - `TestSolverPhone_SwipingTheCluesPansTheBoard::test_a_swipe_on_the_column_clue_band_scrolls_the_stage_and_marks_nothing` (2 params): asserts that the swipe pans the stage. Nothing pans on a phone now. Delete the test. The clue-band swipe is covered by the touch-action test (AC-10).
  - Unchanged, so they pass as they are: `TestSolverPhone_DesktopSizingUnchanged` (3 params) and `TestSolverPhone_SwipingTheCluesPansTheBoard::test_cells_take_no_touch_action_and_clue_boxes_keep_the_default`.
  - Counting: 3 + 3 + 1 + 2 + 2 = 11 changed or deleted (the swipe test's 2 params are deleted), 4 unchanged, of the file's 15 test cases. The new AC-1, AC-2, AC-3 and AC-5 to AC-8 tests go in the same file or in `tests/test_puzzle_solver_mirror.py`.
- [Merge order with CARD-194] CARD-194 (brush dropdown) edits `solver.js`, `admin.css` and `puzzle_solve.html`. Both cards touch the `.player-tools` and `solver.js` wiring areas. Whichever merges second rebases on the first. Mirror CSS and the phone rule sit in the board block (admin.css lines 383-437 and 546-588), not the toolbar rules (lines 442+), to keep the hunks apart.
- [Other tests that change, outside `test_puzzle_solver_phone.py`]
  - `tests/test_puzzle_solver_page.py::TestSolverPageFits::test_a_phone_width_page_never_scrolls_sideways` (line ~1237): asserts `stageScrolls is True` for the 30×30. Becomes `False` (AC-11). The page-level assertion stays.
  - `tests/test_puzzle_solver_clues.py::TestSolverClues_TheCircleIsVisible::test_two_digit_rings_clear_their_digits_on_a_30x30[phone]` (line ~667): asserts a 24 px cell at 390. Becomes the fit value. The ring clearance (0.05 cell, and the 0.5 px check) is about 0.4 px at 8 px cells, so this check may fail even with the right cell size. The implementer must confirm it, and if the threshold has to scale with the cell, record that as a test change. Also update the comment at line ~470 ("the ≤ 820 px 24 px cell floor").
  - `tests/test_puzzle_solver_maybe.py::TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell` (the `30x30@390` case, line ~835): asserts `round(side) == 24` and a glyph of at least 12 px. At 8 px cells the "?" is about 5 px, so the case cannot pass as written. Owner decision needed (see the second ambiguity). AC-343 says "cells at the 24 px phone floor" and must be amended with this card.
  - `tests/test_puzzle_solver_clues.py` phone params of `test_geometry_and_text_are_unchanged` and `test_slots`: they compare relative geometry, so they should pass unedited. Verify.
- [Mirror placement] `solver.js:drawBoard`: `is-mirrored` on the table when `width > 15`. Keep the cells array in row-major order (paint and the marking code depend on it). Keep `th scope="row"` and the aria-labels. DOM order changes for mirrored boards: a screen reader meets the row clue after the row's cells. Record this in the PR.
- [Mirror CSS] Rules to change in `admin.css`: the `.player-corner` border (line 413), `.player-clue.is-row` borders, padding and alignment (line 417), the `.player-clue.is-col:last-child` and `.player-cell:last-child` rules (lines 415 and 420), and the `.player-clue.is-row .player-clue-num` text alignment (line 418). Scope the overrides under `.player-board.is-mirrored`. `_RULES` in `test_puzzle_solver_page.py` checks only the bottom and right widths, so AC-7 needs its own check of the left and right widths.
- [Stage width facts] At 390 px the shell's 820 px block sets `.main` to 16 px padding, so the stage is 358 px wide (admin.css line 361). At 820 px the stage is about 788 px. At 821 px the side nav (220 px, `--side-w`) is back, so the stage is about 550 px and the 30×30 deep-clue board scrolls again at the 14 px floor. That is the same as main today, but the cell size jumps from about 17 px at 820 to 14 px at 821. This is an expected consequence, not a regression.
- [Pinned values to keep] At 1440×900, `DESKTOP_CELL` in `tests/test_puzzle_solver_phone.py` (28, 28, 16.797) must still hold. The 1100×700 ring window and the 1440 ring value (about 17.67 px) in `test_puzzle_solver_clues.py` must still hold.
- [Owner ambiguity 1, decide before implementing] "Boards wider than 15 show mirrored row clues on the right". This card reads it as: every width, columns > 15 (W). If the owner means phones only, the mirror must follow the 820 px breakpoint. That needs a `matchMedia` listener that re-draws the board from the current state, and it adds about 0.25d. Also, "wider" is read as columns, not cells.
- [Owner ambiguity 2, decide before implementing] At a phone width the 30×30 with deep clues gets about 8 px cells. That is below any tap target, and the clue numerals and the "?" glyph are about 5 px. The owner asked for cells to shrink and gave no floor. Options: (a) accept as built; (b) keep a legibility floor for the numerals only, by setting a minimum font size; (c) allow a sideways scroll below a floor, which contradicts the owner decision. This card builds (a). Owner decides whether a numeral floor is a separate card.
- [Renders] The render list needs a before-state from main for the "without mirrored clues" version. Render the 20×20, 25×25 and 30×30 from main before editing admin.css, and keep those files for the owner's comparison.
- [AC cross-check] AC-1 to AC-11 were re-read against What to implement. The body says: floor removed below 820, mirror when width > 15 at every width, corner at the end of the head row when mirrored, cells keep `touch-action: none`. The ACs agree with that. AC-3 uses "at least 14 px" at 821 because the desktop clamp applies there, not a fixed value. AC-2 says "narrower than 14 px" for the 30×30 at 390; that is true for the fit value of about 8 px. If the implementer picks a non-zero floor, AC-2 must be re-checked against it.
- [Estimate] 1d: CSS and JS change, mirror CSS flips, one new test file, about 6 edited test functions, the renders and the DESIGN-REGISTER line.
- [Trace] Add `tests/test_puzzle_solver_mirror.py` and the renamed classes to FR-044's tests list in meta/architecture/trace.yml at merge. Not in the card commit.
- [Owner decision] 2026-10-06 — mirrored row clues on the right apply on PHONES ONLY (desktop unchanged). Clue numbers and the "?" mark never render below 12 px: where a board cannot fit at 12 px, it scrolls sideways (this overrides the fit-to-width rule for numerals only).
