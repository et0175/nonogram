# CARD-196: The puzzle player's clue numbers get their own size, independent of the cell, with a 12 px minimum

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1.25d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/196-player-numbers-own-size
**Worktree:** —
**Source:** owner mobile solver feedback, 2026-10-06 (owner decision, option b: clue numbers get a fixed 12 px minimum and are no longer 60% of the cell)
**Idea:** —
**Wave:** 36
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_clues.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**
- `admin.css` `.player-board` (lines 398-407) sets `--player-cell` to `clamp(--player-cell-min, min(100cqi / (cols + row-depth + 1), (100svh − chrome) / (rows + col-depth + 1)), --player-cell-max)`. Every clue number is sized from the cell: `font-size: calc(var(--player-cell) * 0.6)` (line 407).
- A row number is one cell wide: `.player-clue.is-row .player-clue-num { min-width: var(--player-cell) }` (line 418). `.player-clue.is-row` pads left by 0.2 cell (line 417). So a row clue band is `row-depth` cells wide.
- A column number is one cell tall: `.player-clue.is-col .player-clue-num { height: var(--player-cell); line-height: var(--player-cell) }` (line 416). Column boxes are one cell wide, because each column is a cell column.
- The "?" glyph is `calc(var(--player-cell) * 0.6)` (line 427). It is not a clue number and does not change.
- The CARD-182 phone floor (`@media (max-width: 820px) { .player-stage { --player-cell-min: 24px } }`, line 437) stays in force until CARD-193 lands.
- `solver.js:drawBoard` (lines 211-254) sets `--player-cols`, `--player-rows`, `--player-row-depth` and `--player-col-depth` (lines 217-220). `clueBox` (lines 195-207) builds each number as a `span.player-clue-num`.
- The font is IBM Plex Mono, a monospace face (`tokens.css:58`). Its digit advance is 0.6 em, so one digit is 7.2 px at 12 px and two digits are 14.4 px.

**Target behaviour.**
1. **Numerals (the fixed minimum).** `.player-board` sets `font-size: max(12px, calc(var(--player-cell) * 0.6))`. A numeral is never below 12 px on any width. On a 15×15 at 1440 the numerals stay at 0.6 × 28 = 16.8 px. On a 30×30 at 1440 they go from 10.08 px to 12 px (the floor binds). The "?" glyph keeps its own rule (0.6 × cell).
2. **Row clues: a horizontal slot per number, sized from the numeral.** Each row number's box is as wide as its digits (`digits × 0.6 em`), not one cell. The rule has two parts:
   - Between numbers there is a 0.5 ch gap, and there is 0.5 ch of left padding on the row box. (1 ch = 0.6 em at 12 px = 7.2 px.)
   - `solver.js:drawBoard` sets `--player-row-ch` to the widest row clue in ch: the maximum over rows of `Σ(digits_i + 0.5) + 0.5`.
   - The row band width is `R = calc(var(--player-row-ch) * 0.6 * 12px)`. It is fixed by the 12 px numeral, not by the cell, so it does not feed back into the cell size.
   - Remove `min-width: var(--player-cell)` from `.player-clue.is-row .player-clue-num` (line 418). Replace the cell-based padding (line 417) with the 0.5 ch padding.
3. **Column clues: the width rule.** A column is one cell wide, so its widest number must fit in one cell. `solver.js:drawBoard` sets `--player-col-digits` to the most digits in any column number (1 or 2). The cell's floor from numbers is `--player-col-floor = calc(var(--player-col-digits) * 0.6 * 12px)`: 7.2 px if every column number is one digit, 14.4 px if any is two digits.
   - Column numbers keep their slot height of one cell, and the vertical term of the cell formula is unchanged. The column band's height therefore does not change.
4. **Cell formula.** `--player-cell` becomes `clamp(max(--player-cell-min, --player-col-floor), min((100cqi − R) / cols, (100svh − chrome) / (rows + col-depth + 1)), --player-cell-max)`. The row-depth cell term is gone, because the row band is now `R`.
5. **The rule when numbers do not fit (chosen by this card, pinned by a test).** If the floor from numbers (`--player-col-floor`) is larger than the fit, the cell is the floor, not the fit. The board is then wider than `.player-stage`, and `.player-stage` scrolls sideways. The page never scrolls. This is the only case of sideways scrolling this card creates. It conflicts with the owner's 2026-10-06 phone decision of no sideways scroll; see the owner decision in Worktree notes.
6. **Desktop sizes are kept.** The vertical term binds on the 30×30 at 1440×900 (16.797 px). The horizontal term with `R` must not bind there. The implementer confirms this. If the horizontal term does bind, stop and report, because that changes a G-1 pin.

Rejected, for the record:
- Make the numerals a fixed 12 px everywhere. This would also shrink the 15×15 desktop numerals from 16.8 px to 12 px. The owner's "NOT 60% any more" could mean that, so it is listed as an ambiguity below.
- Let a two-digit column number overflow its one-cell column. Neighbouring two-digit numbers would overlap.
- Stack the two digits of a column number on top of each other. This would change how every column clue reads, so it is an option for the owner and not part of this card.
- Use `ch` units directly in `calc()` for the row band. The numeral size comes from `calc(var(--player-cell) * 0.6)` on desktop, so the band would depend on the cell. The 12 px constant keeps `R` independent of the cell.

## Acceptance criteria

- **AC-1** (happy): *Given* a 15×15 and a 30×30 player page at 1440×900, *when* the computed font-size of their numerals is read, *then* the 15×15's numerals are 16.8 px (0.6 × its 28 px cell) and the 30×30's are 12 px (the floor binds), and no numeral is below 12 px.
  *test: TestPlayerNumerals_TwelvePixelFloor (in tests/test_puzzle_solver_clues.py)*
- **AC-2** (boundary): *Given* a 15×15 page at 390×844 (its cell at the CARD-182 24 px floor) and a 30×30 page at 1100×700 (the 14 px floor), *when* the numerals are read, *then* the 15×15's are 14.4 px and every numeral on the 30×30 is at least 12 px.
  *test: TestPlayerNumerals_TwelvePixelFloor (in tests/test_puzzle_solver_clues.py)*
- **AC-3** (happy): *Given* a 25×15 page at 1440×900 and at 390×844, *when* a row clue's numbers are read, *then* each number's box is as wide as its digits (not one cell wide), and each column number's box is still one cell tall.
  *test: TestSolverClues_EveryNumberKeepsAOneCellSlot (in tests/test_puzzle_solver_clues.py) — rewritten: the one-cell width rule becomes the numeral-width rule; the height rule stays*
- **AC-4** (boundary): *Given* a 30-column board whose column numbers all have one digit, at 390×844 with the phone floor removed by an injected `--player-cell-min: 0px`, *when* the cell side is read, *then* it equals the fit value (it is not raised to 14.4 px).
  *test: TestPlayerNumerals_ColumnFloorIsTheWidestColumnNumeral (in tests/test_puzzle_solver_clues.py)*
- **AC-5** (boundary): *Given* a board with a two-digit column number, *when* its cell side is read at 1100×700 (the 14 px desktop floor), *then* it is 14.4 px, and with the phone floor removed at 390×844 it is never below 14.4 px.
  *test: TestPlayerNumerals_ColumnFloorIsTheWidestColumnNumeral (in tests/test_puzzle_solver_clues.py)*
- **AC-6** (negative): *Given* a 30-column board with two-digit column numbers at 390×844 with the phone floor removed, *when* the page is measured, *then* the cell is 14.4 px, the board is wider than `.player-stage`, `.player-stage` scrolls sideways, and the page's scrollWidth is at most the viewport width.
  *test: TestPlayerNumerals_ColumnNumbersDecideTheStageScroll (in tests/test_puzzle_solver_clues.py)*
- **AC-7** (negative): *Given* the 15×15 and 30×30 "?" boards at 1440×900, *when* the "?" glyph's font-size is read, *then* it is still 0.6 × the cell, not the numeral floor.
  *test: TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell (in tests/test_puzzle_solver_maybe.py) — unchanged*
- **AC-8** (boundary): *Given* the 30×30 two-digit board at 1100×700, *when* its cell side is read, *then* it is 14.4 px (the floor from its two-digit column numbers), and its rings still clear their digits.
  *test: test_two_digit_rings_clear_their_digits_on_a_30x30 (in tests/test_puzzle_solver_clues.py) — edited: the 1100 expected cell changes from 14 to 14.4; all other assertions unchanged*

## Guardrails

- G-1: Desktop cell sizes are unchanged at 1440×900. `TestSolverPhone_DesktopSizingUnchanged` (3 params: 28, 28, 16.797 px, in tests/test_puzzle_solver_phone.py) and `TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen` (2 params, tests/test_puzzle_solver_page.py) pass unedited. The one desktop size that moves is the 14 px floor at 1100×700 for boards with a two-digit column number (AC-8). Owner-visible, and it needs a G-1 narrowing call.
- G-2: Circling moves nothing. `TestSolverClues_CirclingMovesNothing::test_geometry_and_text_are_unchanged` (2 params) passes unedited. Ring geometry tests in `TestSolverClues_TheCircleIsVisible` (other than the AC-8 edit) pass unedited.
- G-3: Marking, touch and the touch split are unchanged. `tests/test_puzzle_solver_marking.py` and `tests/test_puzzle_solver_hint.py` pass unedited. Cells keep `touch-action: none`; clue boxes keep `auto` (`TestSolverPhone_SwipingTheCluesPansTheBoard`, unedited).
- G-4: The "?" glyph is still 0.6 × the cell and at least 12 px (AC-343, `TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell`, unedited).
- G-5: No new colour literal, framework or dependency (ADR-0038/R1). `TestPlayerAssets` and `tests/test_admin_design_tokens.py` pass.
- G-6: `static/solver_state.js` and `templates/puzzle_solve.html` are not edited (ADR-0038/R4). `solver.js` changes only the custom properties set in `drawBoard` and the `clueBox` class names, if any. No state logic moves.
- G-7: CARD-182's 24 px phone floor and 28 px cap stay in force in this card. CARD-193 removes the phone floor. CARD-196 does not edit CARD-193's tests.
- G-8: Other edits to tests are limited to those named in Acceptance criteria. Any other failing test is a regression.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-196` (53 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-044 (the puzzle player). AC-343 (the "?" glyph floor), AC-345..AC-350 (clue circling, EC-044), AC-354 (no page scroll at 390 px) all still hold.
- **ADR:** ADR-0038 (R1 plain static JS and CSS, R2 no request per mark, R4 pure state module).
- **CON:** CON-021 (the player is admin-only), CON-011 (sides 10 to 30, so up to 30 cells and 30 clue numbers per line).
- **Components:** COMP-009 (Admin Panel); capability CAP-007 (Puzzle play).
- **Trace:** meta/architecture/trace.yml, `req: FR-044`. The new test class names are added to its tests list at merge.

## Design context

- **Screen:** puzzle player, `/puzzle/<id>/solve` (SolverBoard, with ClueBox), at phone width (390×844) and at desktop width (1440×900).
- **Owner-visible defaults this card picks:**
  - Numerals never go below 12 px. Desktop 30×30 numerals grow from 10.08 px to 12 px. Desktop 15×15 numerals stay at 16.8 px. At the 1100×700 floor, numerals grow from 8.4 px to 12 px.
  - Row clue bands are as wide as their digits, not one cell per number. Desktop board cells do not change, but the row band is narrower, so the board sits further left.
  - On a 30-column board with a two-digit column number, the cell is at least 14.4 px, so such a board is wider than the stage and scrolls sideways inside it. This is the rule in item 5 above, and it needs the owner's decision (see Worktree notes).
- **Renders:** ~/Documents/nonogram-reviews/CARD-196/ (owner visual check). Real pictures through the image pipeline, mid-solve, in before and after pairs:
  - 390×844: a 15×15 and a 30×30 (the 30×30 with its deepest row clue and a two-digit column number).
  - 1440×900: the 30×30, before and after, to show that the cell is unchanged and the numerals are 12 px.

## Worktree notes

- [Origin] Owner mobile solver feedback, 2026-10-06, owner decision option b: clue numbers are NOT 60% of the cell any more. They have a fixed minimum of 12 px on every width; cells fit the board to the available width. No IDEA id was given.
- [Owner decision, to confirm] Two readings of "NOT 60% any more". This card takes the reading that keeps 0.6 × cell where it is above 12 px (the brief's option). The alternative is a fixed 12 px everywhere, which also shrinks desktop 15×15 numerals from 16.8 px to 12 px. Confirm before implementing.
- [Owner decision, needed] Phone and column numbers. A two-digit column number needs 14.4 px of width at 12 px. At 390 px the stage is 358 px wide, so a 30-column board with any two-digit column number cannot fit: 30 × 14.4 = 432 px. The rule in this card lets such a board scroll sideways inside `.player-stage`. Options:
  - (a) Scroll inside the stage for those boards (the card's default). This breaks the owner's 2026-10-06 phone decision of no sideways scroll for those boards.
  - (b) Stack the two digits of a column number on top of each other. Each column then needs 7.2 px. This changes how the clue reads.
  - (c) Allow numerals below 12 px on phones. This reverses the owner's fixed minimum.
- [Conflict with CARD-193] CARD-193 AC-1, AC-2 and AC-11 assume 30×30 boards fit 358 px with no sideways scroll, with cells of about 8 px. Under this card that holds only when no column number has two digits. CARD-193 must be re-checked after this card merges, and re-cut if option (a) is chosen. CARD-193 already depends on CARD-196.
- [Verified] Row clue slot: `admin.css:418` (`min-width: var(--player-cell)`) and `admin.css:417` (padding 0.2 cell). Column slot height: `admin.css:416`. The "?" glyph: `admin.css:427`. CARD-182 floor: `admin.css:437`. Font: `tokens.css:58` (IBM Plex Mono, monospace, 0.6 em advance).
- [G-1 tests that pin clue geometry, read before editing]:
  - `tests/test_puzzle_solver_clues.py`:
    - `TestSolverClues_EveryNumberKeepsAOneCellSlot::test_slots` (2 params): pins the one-cell width. REWRITE (AC-3).
    - `TestSolverClues_CirclingMovesNothing::test_geometry_and_text_are_unchanged` (2 params): keep.
    - `TestSolverClues_TheCircleIsVisible::test_the_outline` (2 params): keep. Check that the ring geometry still holds with the new numeral sizes.
    - `test_two_digit_rings_clear_their_digits_on_a_30x30` (3 params, cells 14 / 17.67 / 24): EDIT only the 1100 expected cell, 14 to 14.4 (AC-8).
  - `tests/test_puzzle_solver_phone.py`: `TestSolverPhone_DesktopSizingUnchanged` (3 params, 28 / 28 / 16.797): keep. `TestSolverPhone_CellsAreATapTarget` and `TestSolverPhone_FloorAppliesOnlyBelowTheShellBreakpoint` pin CARD-182's 24 px floor. They are kept here and rewritten by CARD-193.
  - `tests/test_puzzle_solver_page.py`: `TestSolverPageFits` (laptop and phone): keep. `TestSolverPage_EmphasisesEveryFifthLine`: keep.
  - `tests/test_puzzle_solver_maybe.py`: `TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell` (AC-343; `round(side) == 24` at 390): keep.
  - `tests/test_puzzle_solver_percent.py` (`TestSolverPercent_SitsNextToTheCounters`, AC-354): keep. It reads the toolbar and counters, not the board.
  - `tests/test_puzzle_solver_progress.py` (`test_the_success_frame_is_not_clipped_by_the_stage`): keep. It reads the board's outline inside the stage.
- [DESIGN-REGISTER] Not in Touches (meta is not in the card commit). Update `meta/design/components.md`:
  - line 229 (`Sizing:`): the cell side is now `clamp(max(cell floor, column-number floor), fit minus row band, 28px)`; numerals are `max(12px, 0.6 × cell)`.
  - line 249 (ClueBox, CARD-188): "each number keeps main's one-cell slot" becomes "each row number's slot is its numeral's width, and each column number keeps a one-cell height".
- [Estimate] 1.25d. The CSS and the two custom properties are small. The time goes to rewriting AC-3 and AC-8, adding the new classes, and rendering the before/after pairs. The range is 1 to 1.5 d.
- [AC cross-check] The body and ACs agree: numerals (item 1, AC-1, AC-2); row slot (item 2, AC-3); column floor and scroll rule (items 3 and 5, AC-4, AC-5, AC-6); cell formula (item 4, AC-4 to AC-6); desktop (item 6, AC-1 and G-1). No AC orders placement or precedence differently from the body.
- [Scope] `admin.css`, `solver.js`, `tests/test_puzzle_solver_clues.py`. No new file. No new dependency.
- [Owner decision] 2026-10-06 — boards whose two-digit column numbers cannot fit the phone stage scroll sideways INSIDE the board area (page never scrolls); clue numbers are max(12 px, 60% of the cell): desktop 15×15 numbers keep 16.8 px; the 12 px floor only bites where the cell is smaller.

