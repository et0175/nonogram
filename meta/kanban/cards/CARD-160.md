# CARD-160: The admin panel opens any puzzle in a solver page with its clues

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** owner design doc "Nonograms - Print layout" (Google Doc 1pJKF2qX6mC9qw4Cf9Nv3hblTDmtoHwP5Tb8wzK1_WqM), sections "Online solver", "Infrastructure", "V1"; raw-requirements.md Delta 2026-09-24 (a) and 2026-10-03 (a)
**Idea:** —
**Wave:** 31
**Depends on:** —
**Touches:** pyproject.toml, src/nonogram/admin/app.py, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/_puzzle_table.html, tests/test_puzzle_solver_page.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The first slice of the online solver the owner's document asks for. V1 is
"only the solver for Book 1", built for now **inside the admin panel**:
clicking a puzzle opens it to be solved. Public hosting, QR codes and the
picture-to-puzzle generator are later phases.

This card builds the page and the data it needs. Marking cells is
CARD-161, and errors and the solved state are CARD-162.

1. **Route.** `GET /puzzle/<puzzle_id>/solve` renders `puzzle_solve.html`
   for a stored puzzle. Unknown id → the panel's 404. The puzzle is read
   through `puzzle_review.get_puzzle`; nothing is written.
2. **Data for the page.** Row and column clues come from the stored grid
   through the one encoder (`compute_clues`, the same call the storage
   boundary makes). Never re-derive clues another way. The page also needs
   the solution, for CARD-162's error count. For an admin-only POC it can
   ship inside the page. Name that choice in the ADR, because a public
   solver must not hand the answer to the browser.
3. **Board.** An empty grid of the puzzle's real width × height, with:
   - every fifth line heavier (the counting aid the printed pages use);
   - **row clues in boxes** to the left and **column clues in boxes**
     above, as the document's "clue numbers in box" sample shows;
   - a header reading "Puzzle <title>" and the tier ("MEDIUM"), mirroring
     the printed page header the document sketches.
   Size it to fit a laptop screen for the largest supported grids
   (`limits.MAX_SIZE` per side). Use tokens from `meta/design/` for every
   colour and spacing value.
4. **Entry point.** The puzzle detail modal (`_puzzle_table.html`) gets a
   "Solve" action linking to the page.
5. **State model only.** `solver.js` holds the board state, one of
   `unknown | filled | empty` per cell, and renders it. It has no input
   handling yet, beyond what's needed to prove the board renders from
   state. Keep the state logic separate from rendering, as a small pure
   module, so CARD-161/162 can test it.

## Acceptance criteria

_Verbatim from FR-044 in meta/architecture/requirements.yml (architect delta 2026-10-03)._

- **AC-296** (happy): *Given* a stored puzzle 25 cells wide and 15 cells high, *when* the admin opens /puzzle/<its id>/solve, *then* the board shows exactly 15 rows of 25 cells.
  *test: TestSolverPage_ShowsTheClues*
- **AC-297** (boundary): *Given* the stored 25x15 puzzle of AC-296, whose row 3 has no filled cell, *when* the admin opens its player page, *then* each of the 40 clue boxes shows its line's compute_clues(grid) entry, row 3's (0,) appearing as the single number "0".
  *test: TestSolverPage_ShowsTheClues*
- **AC-298** (boundary): *Given* the stored 25x15 puzzle of AC-296, *when* the admin opens its player page, *then* every fifth grid line on both axes (after columns 5, 10, 15, 20; after rows 5, 10) is drawn heavier than the other interior lines.
  *test: TestSolverPage_EmphasisesEveryFifthLine*
- **AC-299** (negative): *Given* no stored puzzle has the id "no-such-puzzle", *when* the admin opens /puzzle/no-such-puzzle/solve, *then* the response is the panel's 404 page with status 404.
  *test: TestSolverPage_UnknownPuzzleIs404*
- **AC-300** (happy): *Given* a stored puzzle shown in the puzzle detail modal, *when* the modal is rendered, *then* it holds a "Solve" action linking to /puzzle/<that puzzle's id>/solve.
  *test: TestPuzzleDetail_OffersSolve*
- **AC-301** (happy): *Given* the player page of a stored 20x20 puzzle has just loaded, *when* the board state and the rendered board are read, *then* all 400 cells are undecided in the page's state and none is drawn filled or marked empty.
  *test: TestSolverPage_AllCellsStartUndecided*
- **AC-302** (negative): *Given* the puzzles, books, batches and generation-history tables hold a known number of rows each, *when* the admin opens a puzzle's player page, makes 10 strokes and solves it, *then* every table's row count and every puzzle row's stored fields are unchanged.
  *test: TestSolverPage_WritesNothing*

## Guardrails

- G-1: No new **runtime** dependency (ADR-0006/R1: stdlib + Pillow + NumPy).
  The client is plain JavaScript served as a static file, with no build
  step and no framework, as ADR-0038/R1 records.
- G-2: Nothing under `src/nonogram/solver/` changes. That is the uniqueness
  solver (COMP-005), a different thing from this player page.
- G-3: Read-only. No puzzle, book or batch row is written, and no progress
  is persisted (not requested).
- G-4: The player is an admin page behind the panel's existing door
  (CON-015 / CON-016). This card adds no public route, auth or hosting.

## Decisions (resolved 2026-10-03 by ADR-0038)

- **CON-002** is superseded by **CON-021**: interactive play exists only as the admin panel's puzzle player.
- **Client:** plain JavaScript and CSS served as static files by Flask. No framework, no build step, no vendored library (ADR-0038/R1, R4).
- **Packaging (ADR-0038/R5):** add `static/*.js` to `nonogram.admin`'s package-data in `pyproject.toml`. Today it lists only `templates/*.html` and `static/*.css`, so the player's JS would be missing from built wheels.
- **Browser tests (ADR-0038/R7, R8):** declare `pytest-playwright` in a dev-only extra in `pyproject.toml`, never in `project.dependencies` or the `admin` extra. When Chromium isn't installed, browser tests fail or skip with a named reason, never silently green. Note the CI step (`playwright install chromium`).
- **Solution in the page (ADR-0038/R6, CON-021):** allowed for the admin player only. A public player reopens ADR-0038.

## System contract

_Assembled 2026-10-03 by `system_rules.py --card CARD-160` (52 rules). A projection — fix the source artifact, never this list._

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

- **FR:** FR-044 (AC-296..AC-302); US-028; CAP-007
- **CON:** CON-002 (conflicts), CON-015 (loopback), ADR-0006/R1 (dependency baseline)
- **ADR:** ADR-0038 (plain JS in the admin panel, pytest-playwright dev extra), ADR-0006/R1
- **CON:** CON-021 (supersedes CON-002), CON-015, CON-016
- **Components:** COMP-009 (admin panel)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/: brief.md, tokens.css, components.md
- **UI components:** SolverBoard (new; register in components.md), clue boxes (new)
- **Screens:** /puzzle/<id>/solve
- **Reference:** puzzle-nonograms.com (owner's reference). The document's
  reference screenshots were not readable through the Drive text export,
  so check them before building.

## Worktree notes

- [Origin] Cut 2026-10-03 at the owner's request ("make cards for the
  solver") from the owner's design doc. Marked architectural: it is the
  first card of a new product surface, and its client structure is what
  CARD-161/162 copy.
- [Architect delta] 2026-10-03 — unblocked: CON-002 superseded by CON-021; FR-044 (US-028, CAP-007) and ADR-0038 (resolving DEC-040/041) now exist; acceptance criteria re-cut verbatim from FR-044 and the system contract assembled. Owner answers folded in: a click always cycles, tools govern drags; the error count is the live number of wrong marks.
