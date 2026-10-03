# CARD-160: The admin panel opens any puzzle in a solver page with its clues

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/160-solver-page-with-clues
**Worktree:** —
**Source:** owner design doc "Nonograms - Print layout" (Google Doc 1pJKF2qX6mC9qw4Cf9Nv3hblTDmtoHwP5Tb8wzK1_WqM), sections "Online solver", "Infrastructure", "V1"; raw-requirements.md Delta 2026-09-24 (a) and 2026-10-03 (a)
**Idea:** —
**Wave:** 31
**Depends on:** —
**Touches:** pyproject.toml, src/nonogram/admin/app.py, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/_puzzle_table.html, tests/test_puzzle_solver_page.py
**Review score:** 8.5 (cycle 4/4, owner-granted final)
**Started:** 2026-10-03T07:58:24Z
**Closed:** 2026-10-03T11:39:56Z
**Actual:** 0.5d
**Merge commit:** 625ce14
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

_Assembled 2026-10-03 by `system_rules.py --card CARD-160` (53 rules; refreshed at start). A projection — fix the source artifact, never this list._

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

## Failure matrix

_Declared before implementation (2026-10-03). W, H = the stored grid's width and height; MIN_SIZE/MAX_SIZE from `nonogram.limits` (10/30). The reviewer verifies each row against the code and the named test._

| # | Operation / boundary | Failure mode | Declared behaviour | Numeric bound | Verified by |
|---|---|---|---|---|---|
| F1 | `GET /puzzle/<id>/solve` → `puzzle_review.get_puzzle` | id names no stored puzzle (well-formed UUID in DB mode, any string in memory mode) | `get_puzzle` returns `None` → `abort(404)` → the panel's `404.html`, status 404 | 1 read, 0 writes | `TestSolverPage_UnknownPuzzleIs404` (memory + sqlite) |
| F2 | same | id is not a UUID in DB mode (`"no-such-puzzle"`) — `get_puzzle` raises `ValueError` parsing it | caught (`ValueError` only) → same 404 as F1; any other exception is not caught | 0 DB queries, 0 writes | `TestSolverPage_UnknownPuzzleIs404` (sqlite) |
| F3 | same | DB/session error inside `get_puzzle` (e.g. `OperationalError`) | not caught by the route: Flask's 500 handler renders `500.html` (status 500); under `TESTING` the exception propagates. Never turned into a 404 | 1 attempt, no retry, 0 writes | `test_a_database_error_is_not_reported_as_a_missing_puzzle` |
| F4 | stored row → grid | `grid` is `None`, not a list, empty, has an empty row, or is ragged | read through `PuzzleReviewService._as_readable_grid` (the panel's read-side reader); `None` → `abort(500)` with the reason "no readable grid"; no board is drawn | 0 writes | `test_an_unreadable_stored_grid_is_a_500_not_a_board` |
| F5 | stored row → grid | cells stored as `0`/`1` (legacy writer) | coerced with `bool()` (the read-side rule); page renders normally, `solution` is booleans | — | `test_a_legacy_zero_one_grid_is_read_as_booleans` |
| F6 | stored row → clues | stored `clues_rows`/`clues_cols` disagree with the grid, or `width`/`height` columns disagree with it | stored clue and size columns are **never read**: clues = `compute_clues(grid)`, width = `len(grid[0])`, height = `len(grid)` | — | `test_stale_stored_clues_and_sizes_are_never_shown` |
| F7 | stored row → header | `difficulty_tier` missing/unrecognised | `tier_of_record` → `None` → no tier chip; title falls back `puzzle_name` → `source_image` → first 8 chars of id | — | `test_header_without_a_tier_shows_no_chip`, `test_header_falls_back_to_source_then_id` |
| F8 | page → `solver.js` / `solver_state.js` | script missing from the install (wheel without `static/*.js`, ADR-0038/R5) or fails to load | (a) build side: `pyproject.toml` package-data globs must cover every file in `admin/static/` and `admin/templates/` — test fails otherwise; (b) browser side: the server-rendered fallback text stays visible ("…the player script did not load"), no board | glob coverage = 100% of files | `test_every_admin_asset_ships_in_the_wheel`, `test_without_the_script_the_fallback_says_so` |
| F9 | page → embedded JSON payload | `<script id="puzzle-player-data">` absent, not JSON, or wrong shape (rows ≠ H, columns ≠ W, solution not H×W, W/H not positive integers) | renderer shows a `role="alert"` danger message, draws no board, leaves `window.puzzlePlayer` undefined, logs one `console.error` with the reason | 1 alert, 0 cells | `test_an_unreadable_payload_shows_an_alert_not_a_board` (invalid JSON + wrong shape) |
| F10 | state module API (`createBoard`, `cellAt`, `withCell`) | non-positive/non-integer size; row/col out of range; state not in `unknown/filled/empty` | throws `RangeError`; the input board is never mutated (boards are frozen) | — | `test_the_state_module_refuses_bad_input`, `PropertyTest_StateModule_WithCellChangesExactlyOneCell` |
| F11 | live player `setBoard` | board of other dimensions than the payload | throws `RangeError`, keeps the current board and DOM | — | `test_set_board_refuses_a_board_of_another_size` |
| F12 | largest supported grid (MAX_SIZE × MAX_SIZE = 30×30) | does not fit a laptop screen | cell side = clamp(14px, min(stage width / (W + row-clue depth + 1), (100svh − chrome) / (H + column-clue depth + 1)), 28px), chrome = topbar 52px + space-6 + space-12 + space-8 = 204px; at 1440×900 the whole board (clues included) lies inside the viewport | DOM = W·H cells + W + H clue boxes = 960 at 30×30; worst clue depth ⌈30/2⌉ = 15 → (30+15+1)·14px = 644px ≤ 900 − 204 = 696px | `test_the_largest_board_fits_a_laptop_screen` (deep row clues and deep column clues) |
| F13 | narrow viewport (390 px) | board wider than the screen at the 14px floor | the board scrolls inside its own `.player-stage` container; the page body never scrolls horizontally | body scrollWidth ≤ viewport width | `test_a_phone_width_page_never_scrolls_sideways` |
| F14 | browser tests | `pytest-playwright` not installed, or Chromium not installed (ADR-0038/R8) | the browser test **errors/fails** (`pytest.fail` in the fixture, reported as ERROR — not a skip) with a named reason and the fix (`pip install -e '.[dev]'` / `playwright install chromium`); never green. Deliberately fail rather than skip: pytest's default summary hides skip reasons, and a silent skip is this repo's known failure mode | 0 silent passes | `browser_type` / `browser_page` fixtures in tests/test_puzzle_solver_page.py; checked by hand with `PLAYWRIGHT_BROWSERS_PATH=<empty dir>` → `1 error`, message ends "Fix: playwright install chromium (ADR-0038/R8)" |
| F15 | player page, any interaction | a write to the store (G-3, AC-302) | route performs exactly one read; no form, no fetch, no XHR from the player; 0 requests after load | 0 rows changed in puzzles / books / batches / generation_history; 0 network requests after `load` | `TestSolverPage_WritesNothing` |
| F16 | access (G-4, CON-015/016) | request outside the door | unchanged: the panel's `before_request` door runs before this route like every other (404 / 401) | — | existing `tests/test_admin_binding.py`, `tests/test_admin_auth.py` (no new door) |
| F17 | live player `setBoard`; `solver_state.isBoard`, `copyBoard`, `withCell` (boards are trusted in-page values — only the page's own code builds and passes them; the card does not defend against hostile objects) | any value that is not a board. isBoard checks EXACTLY: a non-null object (typeof `object`) that is `Object.isFrozen`; whose own **data** properties `width` and `height` are integers ≥ 1 (`Number.isInteger`; 0, negatives, 2.5, NaN, Infinity, `"20"`, missing, a getter or an inherited value are not sides); whose own data property `cells` is a genuine `Array` (`Array.isArray` — no array-likes), itself frozen, of length exactly width·height (off by one either way, or sides that do not multiply to the length, are refused); and in which EVERY index 0..length−1, checked index by index, is an own data element holding `unknown`/`filled`/`empty` (no holes — `every()` skips them, F-009 — no getter elements, no `"Filled"`/`null`/`undefined`/`1`). Nothing else is checked: other own properties are not looked at (re-derived in review cycle 3, F-011; cycle 2, F-009/F-010; first added in cycle 1, F-003) | `isBoard` is false → `setBoard` throws `RangeError` before any paint; keeps the current board and DOM (never a `data-state="undefined"` cell); checked before the F11 dimension check. An accepted board is copied (`copyBoard`: width, height and each cell by index, own-data reads, into a fresh frozen board) and the copy is stored and painted — `getBoard()` is never the caller's object, equals it structurally, and does not carry its other own properties. `withCell` builds its new cells Array by index (not `cells.slice()`); `createBoard`/`copyBoard`/`withCell` output, for a board input, is always a board | 0 cells repainted on refusal; the stored board is the player's own frozen copy, so every value it holds is permanent (CARD-161 history, CARD-162 error count rely on it) | `test_set_board_refuses_a_value_that_is_not_a_board` (one row per clause, 33 refused values + an accepted extra-property board kept as a copy without it), `test_set_board_keeps_and_paints_its_own_copy` (getBoard() ≠ caller's object, equal cells/sides, frozen, isBoard, painted), `test_with_cell_builds_its_cells_by_index_not_by_slice` (cells with an own `constructor`/`Symbol.species` or a throwing own `slice` still yield a board), `test_PropertyTest_StateModule_IsBoardIsExactlyTheDeclaration` (240 seeded made boards accepted, ≥1000 board values; one corruption of each refused, ≥20 per kind) |

## Worktree notes

- [Origin] Cut 2026-10-03 at the owner's request ("make cards for the
  solver") from the owner's design doc. Marked architectural: it is the
  first card of a new product surface, and its client structure is what
  CARD-161/162 copy.
- [Architect delta] 2026-10-03 — unblocked: CON-002 superseded by CON-021; FR-044 (US-028, CAP-007) and ADR-0038 (resolving DEC-040/041) now exist; acceptance criteria re-cut verbatim from FR-044 and the system contract assembled. Owner answers folded in: a click always cycles, tools govern drags; the error count is the live number of wrong marks.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +ADR-0038/R5 / −(none) (53 rules)
- [Spawn] implementation agent: general-purpose (Skill: python-pro read as 'a Python card' per config.yml caveat), no model parameter (no models: block)
- [CARD-160 implementation 2026-10-03] Route `GET /puzzle/<id>/solve` (app.py, additive block before CARD-077's), template `puzzle_solve.html`, pure state module `static/solver_state.js`, renderer `static/solver.js`, "Puzzle player" section appended to `admin.css`, "Solve" action in the detail modal (`_puzzle_table.html`), pyproject: `static/*.js` in package-data (ADR-0038/R5), `pytest-playwright>=0.7` in the dev extra (R7), `browser` marker registered. Tests: `tests/test_puzzle_solver_page.py` — 58 tests (31 server, 27 browser), all green, 0 skipped. Neighbours green: test_cli (structural import guard), test_admin_design_tokens, test_export_pdf (dependency baseline), test_admin_rename_strategies_batches, test_book_floor, test_admin_binding, test_admin_auth, test_admin_tier_surfaces; tests/e2e/test_admin_workflow.py only the known pre-existing `test_size_configuration_applied` failure. Nothing under src/nonogram/solver/ touched (G-2).
- STRUCTURE: two ES modules, not one file — `solver_state.js` (pure: no DOM, no globals, frozen board values `{width, height, cells}` row-major, `createBoard`/`cellAt`/`withCell`, states `unknown|filled|empty`) and `solver.js` (the only DOM code; reads the payload, draws, paints, exposes the live player). Why: ADR-0038/R4 purity is then structural and checkable (`test_the_state_module_touches_no_dom` scans it), and CARD-161/162 import the same module the page runs, with `await import('/static/solver_state.js')` in page.evaluate — no copy, no build step. CARD-161 adds strokes/history as new pure functions over these board values (undo = an array of boards).
- STRUCTURE: the page embeds its data as one JSON payload in `<script type="application/json" id="puzzle-player-data">` via Jinja `|tojson` (HTML-safe escaping); shape `{id, width, height, rows, columns, solution}` documented once in solver.js's header and pinned by `test_the_payload_has_exactly_the_documented_shape`. Width/height/clues come from the stored grid only (stored clue/size columns never read); clues are `compute_clues(grid)` (ADR-0038/R3); solution ships for CARD-162 (admin-only, R6). The renderer validates the payload and shows a role=alert instead of a board when it is absent/invalid.
- STRUCTURE: the server renders only the header (`Puzzle <title>` + TierChip with the tier upper-cased, e.g. MEDIUM) and a fallback paragraph; the board is drawn client-side from the payload, so there is one rendering path for CARD-161 to attach input to. Title falls back puzzle_name → source_image → id[:8] (the modal's rule).
- STRUCTURE: the live player is `window.puzzlePlayer = {payload, getBoard(), setBoard(board)}` (frozen). `setBoard` is the single way the board changes and repaints; it refuses a board of other dimensions. CARD-161's click/drag/undo should call it rather than touch the DOM; CARD-162 reads `payload.solution` + `getBoard()`.
- STRUCTURE: CSS naming — component prefix `player-` (`.player-stage`, `.player-board`, `.player-clue.is-row|.is-col`, `.player-clue-num`, `.player-cell`, `.player-corner`, `.player-fallback`, `.player-error`), cell state as `data-state` (not classes), heavy rules as `.major-right` / `.major-below` set by the renderer (never on the last line; the frame is heavy via `:last-child`). Each cell/clue box draws only its right+bottom rule with `border-collapse: separate; border-spacing: 0`, so a rule's weight is one element's computed border — which is what the AC-298 test reads. Cell side is pure CSS: `clamp(14px, min(100cqi/(W+rowDepth+1), (100svh−chrome)/(H+colDepth+1)), 28px)` with W/H/depths set as custom properties by the renderer.
- DESIGN-REGISTER: **SolverBoard** — Used by: puzzle player (`puzzle_solve.html`, drawn by `static/solver.js`). Parts: column-clue boxes above, row-clue boxes left, W×H cells, heavy rule after every 5th line on both axes and on the frame (the printed page's counting aid), clue area carries the same rules. States: loading/no-script (fallback sentence "…the player script did not load") · error (danger alert, no board, when the payload is unreadable) · drawn — each cell `unknown` (bare --grid-paper) · `filled` (--grid-ink) · `empty` (small --color-text-secondary dot). Sizing: cell side clamp(14px, fit, 28px) from the board size and clue depth; fits 1440×900 at 30×30; below the floor it scrolls inside `.player-stage`, the page never scrolls sideways. Tokens: --grid-paper, --grid-ink, --color-surface, --color-text-secondary, --border-width, --font-num, --topbar-h, --space-*. Candidate new tokens (now local custom properties in admin.css): --player-cell-min 14px, --player-cell-max 28px, thin rule = color-mix(--grid-ink 28%, --grid-paper).
- DESIGN-REGISTER: **ClueBox** — one box per line (a row's to the left, a column's above), holding one numeral slot per clue number, cell-sized, --font-num tabular; an empty line shows the single number "0"; `aria-label` "Row N: …" / "Column N: …". States: default only (CARD-161/162 may add "line satisfied"). Tokens: --color-surface, --font-num, --grid-ink.
- DESIGN-REGISTER: Modal (puzzle detail) gains a "Solve" action (btn-outline-primary, first in the downloads row) linking to /puzzle/<id>/solve.
- MUTATION: drop the route's ValueError catch → caught by TestSolverPage_UnknownPuzzleIs404::test_no_such_puzzle_is_the_panels_404[sqlite]
- MUTATION: drop `abort(404)` on None → caught by TestSolverPage_UnknownPuzzleIs404 [memory]
- MUTATION: drop the unreadable-grid guard → caught by test_an_unreadable_stored_grid_is_a_500_not_a_board[none]
- MUTATION: read the stored grid raw (no `_as_readable_grid`) → caught by test_an_unreadable_stored_grid_is_a_500_not_a_board[string]
- MUTATION: clues from the stored `clues_rows` → caught by test_stale_stored_clues_and_sizes_are_never_shown
- MUTATION: width from the stored `width` column → caught by test_stale_stored_clues_and_sizes_are_never_shown
- MUTATION: tier not upper-cased → caught by test_header_reads_puzzle_title_and_the_tier
- MUTATION: tier chip always rendered → caught by test_header_without_a_tier_shows_no_chip
- MUTATION: title skips source_image → caught by test_header_falls_back_to_source_then_id
- MUTATION: heavy every 4th line → caught by TestSolverPage_EmphasisesEveryFifthLine::test_the_25x15_board
- MUTATION: heavy rule also after the last line → caught by TestSolverPage_EmphasisesEveryFifthLine::test_the_25x15_board
- MUTATION: no major rule on column-clue boxes → caught by TestSolverPage_EmphasisesEveryFifthLine::test_the_25x15_board
- MUTATION: CSS `.major-right` rule removed → caught by TestSolverPage_EmphasisesEveryFifthLine::test_the_25x15_board
- MUTATION: cells start filled (`fill(FILLED)`) → caught by TestSolverPage_AllCellsStartUndecided::test_all_400_cells_start_undecided
- MUTATION: paint is a no-op → caught by TestSolverPage_AllCellsStartUndecided::test_all_400_cells_start_undecided
- MUTATION: empty-mark CSS removed → caught by test_the_board_is_painted_from_state
- MUTATION: Solve link dropped from the modal → caught by TestPuzzleDetail_OffersSolve
- MUTATION: Solve link to /puzzles/<id>/solve → caught by TestPuzzleDetail_OffersSolve
- MUTATION: setBoard size guard dropped → caught by test_set_board_refuses_a_board_of_another_size
- MUTATION: payload validity reduced to `!payload` → caught by test_an_unreadable_payload_shows_an_alert_not_a_board[height-off]
- MUTATION: null payload accepted → [null]; isSide accepts anything → [width-zero]; rows not checked → [negative-clue]; columns not checked → [empty-clue]; solution not checked → [solution-not-bool]; empty clue accepted → [empty-clue]; negative clue accepted → [negative-clue]; fractional clue accepted → [fractional-clue]; non-boolean cell accepted → [solution-not-bool]; short solution row accepted → [solution-short-row] (all test_an_unreadable_payload_shows_an_alert_not_a_board)
- MUTATION: first payload-shape mutant (`false && !isSide(width)` only) SURVIVED — operator precedence left the other checks live, and the one corruption then tested was caught by them; answered by 8 more corruption cases and the 11 targeted mutants above, all caught
- MUTATION: missing-element check dropped → caught by [absent]; JSON error unlabelled → [not-json]; console.error dropped → [not-json]
- MUTATION: withCell state check / range check / createBoard validation dropped → caught by TestSolverStateModule::test_the_state_module_refuses_bad_input
- MUTATION: withCell indexes column-major → caught by test_PropertyTest_StateModule_WithCellChangesExactlyOneCell
- MUTATION: pyproject drops `static/*.js` → caught by test_every_admin_asset_ships_in_the_wheel; pytest-playwright moved into runtime deps → caught by test_pytest_playwright_is_a_dev_only_dependency
- MUTATION: cell floor 22px → caught by test_the_largest_board_fits_a_laptop_screen[row-clues]; stage without overflow-x → caught by test_a_phone_width_page_never_scrolls_sideways
- MUTATION: fallback text changed → caught by test_without_the_script_the_fallback_says_so; clue numbers reversed → caught by TestSolverPage_ShowsTheClues…each_of_40_boxes_shows_its_clue
- AC-302 (TestSolverPage_WritesNothing): SQLite store pre-filled with 2 puzzles (one in a real batch), 1 book, 1 batch; counts of puzzles/books/batches/generation_history and every `puzzles` row (SELECT *) snapshotted; page opened in Chromium, then — since CARD-160 has no input handling — 10 strokes are driven through the page's own seam: 10 × `puzzlePlayer.setBoard(withCell(board, r, c, filled|empty))`, then "solves it" by setting every cell to `payload.solution` the same way; asserts final state and DOM equal the solution, zero network requests after load, and the snapshot unchanged. CARD-161 will replace the setBoard strokes with real clicks/drags against the same assertions.
- AC-300 is browser-only (the modal is built client-side from /api/puzzle/<id>/details): the test opens /puzzles, clicks the puzzle, checks the Solve href and follows it to a drawn board.
- R8 / browser prerequisites: missing pytest-playwright or Chromium makes the browser tests ERROR via `pytest.fail` with the fix (`pip install -e '.[dev]' && playwright install chromium`), deliberately not a skip (default pytest summary hides skip reasons). Checked by hand: `PLAYWRIGHT_BROWSERS_PATH=<empty dir>` → 1 error with that message. CI note is in pyproject's dev-extra comment and the test module docstring.
- Console-clean check: `test_the_player_page_loads_with_a_clean_console` (no console error/warning, no page error, no failed request, no own-origin 4xx/5xx) passes; the render script re-checked all six player renders — console clean on each (desktop and 390 px).
- Fit check (owner renders, real pictures through the image pipeline): 30×30 cat at 1440×900 → board right/bottom 969/857 px, cell 21.9 px: fits the laptop screen. Worst case covered by test_the_largest_board_fits_a_laptop_screen (tight rows → 15-deep row clues, and transposed → 15-deep column clues). At 390 px the 25×15 and 30×30 boards sit at the 14 px floor and scroll inside their stage; the page does not scroll sideways.
- Renders: ~/Documents/nonogram-reviews/CARD-160/ — player-small-{1440,390}.png (duck 15×15), player-25x15-{1440,390}.png (butterfly 25×15), player-30x30-{1440,390}.png (cat 30×30), modal-solve-entry-1440.png; re-run with card160_render.py there (SQLite temp DB via tests/helpers/db.sqlite_session_scope, loopback server).
- Observation (pre-existing, not changed — out of scope): on narrow screens the shell's single-column grid stretches the side-nav row when the page is short, leaving a blank band under the nav strip (visible in player-small-390.png). Belongs to AppShell, every short page shows it.
- No SCOPE+ — every changed file is in Touches, plus the new `static/solver_state.js` next to solver.js.
- [Scope] pyproject.toml, src/nonogram/admin/app.py, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/_puzzle_table.html, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_page.py
- [Build gate] impact underivable (test_scope: full; fix_scope touches pyproject.toml) — full suite
- [Scope gate] cycle 1: IN_SCOPE — guardrail_hits 0 (G-2 src/nonogram/solver/** untouched); excess 0 (solver_state.js is a new file beside Touches' static/solver.js); comp_spread 0 (COMP-009 only); poached: CARD-161/162 Touches overlap 3 files (solver.js, puzzle_solve.html, admin.css), all inside CARD-160's own Touches and created by it — the dependents extend them by design; no input/marking/error-count/solved behaviour present in the diff (grep), so no sibling scope absorbed
- [Build gate] PASSED (full, 387s) — 5916 passed, 9 skipped (none in tests/test_puzzle_solver_page.py), 2 failed = exactly the main-branch baseline (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders)
- [Adversarial] F-001 CONFIRMED — mutant shipping the raw 0/1 grid as solution passes all 58 tests; solver.js isSolution rejects non-booleans, so legacy puzzles would show an alert with the suite green
- [Adversarial] F-002 CONFIRMED — withCell returning an unfrozen board/cells passes all 58 tests; frozenness is declared by F10 and the solver_state.js header
- [Review 1/3] Score: 8.0 — crit: 0, imp: 2 (F-001, F-002; both adversarially confirmed). Step 8h coverage: 53/53 card rules addressed (14 ✓, 39 ⚠, 0 ✗); 8f-mutation ran (8 mutants, 6 killed, 2 survived → F-001/F-002); 8g static only (visual off)
- [Severity gate 1/3] Score >= threshold but 0 critical / 2 important findings — fix mandatory
- [Review sync] 1 report(s) → meta/review/ (20261003T084948Z-CARD-160-cycle1.yml)
- [Fix 1] FIXED F-001, F-002, F-003, F-007 (each with a killed mutant: M8, M6, five F-003 guard mutants); SKIPPED F-004 (tokens.css outside fix scope), F-005 (owner viewport decision), F-006 (puzzle_review.py outside fix scope), F-008 (out of scope). Pre-gate: 5/5 named tests passed. Behaviour delta: setBoard(non-board) now RangeError (was TypeError for null) — new F17 row
- [Fix 1] declarations: 1 updated (F17 new row), 3 confirmed (F5, F10, F15; F11 also confirmed), 0 none
- [Build gate] PASSED (full, 406s) — after fix 1: 5917 passed, 9 skipped, 2 failed = exactly the baseline pair
- [Scope gate] cycle 2: IN_SCOPE — same 8 files, no new paths; G-2 untouched
- [Review 2/3] CONFIRMATION MODE eligible — prior review parsed; delta = uncommitted fix-1 edits for F-001/F-002/F-003/F-007 only (solver.js, solver_state.js, tests/test_puzzle_solver_page.py); IN_SCOPE; cycle 1 raised no gating findings beyond those fixed
- [Adversarial] F-009 CONFIRMED — node: isBoard(frozen {20x20, cells: frozen new Array(400)}) === true (every() skips holes); setBoard then paints data-state="undefined", which F17 declares impossible
- [Review 2/3] Score: 8.0 — crit: 0, imp: 1 (F-009, adversarially confirmed). Confirmation mode; F-001/F-002/F-003/F-007 ✓ resolved (M8, M6 re-run and killed). Step 8h 53/53 addressed (14 ✓, 39 ⚠, 0 ✗; none carried). 8f-mutation ran: 9 mutants, 8 killed, M15 survived → F-010 Minor. Next cycle must be FULL (new Important)
- [Severity gate 2/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Family check 2/3] F-009 is attributed to the F-003 fix (its isBoard / F17 row, the boundary named in [Fix 1] declarations) → regression streak 1 (first occurrence vs the previous fix's own declarations); escalation needs ≥2 — continuing
- [Stalled check 2/3] Δscore 0.0 < 0.5 but Δcrit+imp = +1 (2 → 1) — not stalled
- [Review sync] 1 report(s) → meta/review/ (20261003T091500Z-CARD-160-cycle2.yml)
- [Fix 2] FIXED F-009 (isBoard declared in full — own-data properties, Array.isArray, index-wise own-element walk; 33-row refusal table + seeded corpus of 240 boards/≥1000 accepted/≥200 corruptions), F-010 (direct side cases); 15 mutants all killed; old cycle-1 isBoard fails the table with the finding's own symptom. SKIPPED F-004/F-005/F-006/F-008 (as cycle 1). Pre-gate: 2/2 named tests passed. Stated: revoked Proxy → TypeError from isBoard (no handler widened), still before paint
- [Fix 2] declarations: 2 updated (F17 re-derived; isBoard/setBoard docs), 2 confirmed (F10, F11), 0 none
- [Build gate] PASSED (full, 408s) — after fix 2: 5918 passed, 9 skipped, 2 failed = exactly the baseline pair
- [Scope gate] cycle 3: IN_SCOPE — same 8 files; G-2 untouched
- [Review 3/3] FULL mode (cycle 2 raised new Important F-009 — not confirmation-eligible)
- [Adversarial] F-011 CONFIRMED — node: (1) a frozen cells Array with an own constructor/Symbol.species (or replaced prototype) passes isBoard, yet withCell's cells.slice() returns a non-board — contradicts F17 'nothing reads them' / 'withCell output is always a board'; (2) a Proxy accepted by isBoard (which never uses the get trap) revokes/throws on get mid-paint: 1 cell repainted, getBoard() returns a revoked proxy — contradicts F17 'before any paint', 'keeps the current board'. Reachability: none from real input (CARD-160 has no input handling; only tests/devtools call setBoard)
- [Review 3/3] Score: 7.5 — crit: 0, imp: 1 (F-011, adversarially confirmed). FULL mode; F-009/F-010 ✓ resolved. Step 8h 53/53 addressed (14 ✓, 39 ⚠, 0 ✗). 8f-mutation: deferred(cost) — gating finding present. AC-296..302 all hold per reviewer; G-1..G-4 ✓
- [Review 3/3] ⚠ family regression — what makes a value a board: 2 gating findings across cycles 2-3 (F-009, F-011), each attributed to the previous fix (F-003 fix introduced isBoard → F-009; F-009 fix's declared F17 semantics → F-011)
- [Family] The card's state module never decided whether a board is a trusted in-page value or an arbitrary caller-supplied object, so each fix re-derives 'what makes a value a board' one more clause at a time (holes, then prototypes/Proxies) and declares guarantees the code does not hold — F-001→F-003, F-009, F-011, cycles 1-3, files: src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_page.py
- [Review 3/3] Score: 7.5 ⚠ max cycles reached
- [Review sync] 3 report(s) → meta/review/ (…-cycle1.yml, 20261003T091500Z-CARD-160-cycle2.yml, 20261003T093454Z-CARD-160-cycle3.yml)
- [Escalated] 2026-10-03T09:38:31Z — review loop regenerating defects in one family ('what makes a value a board': F-009 cycle 2, F-011 cycle 3, each attributed to the previous fix) + max cycles reached (7.5 < 8, 1 confirmed Important); AC-296..302 hold, 0 system-contract violations; fix-1+fix-2 edits UNCOMMITTED in the worktree on top of c79e41d · station: likely implementation/design (owner choice — see routes) · route: design → manual fix (setBoard stores a fresh frozen board built from own-data reads; withCell builds cells by index, no cells.slice(); narrow F17 + solver_state.js header to trusted in-page values and drop the Proxy/prototype prose) then /kanban review CARD-160, or /kanban redo CARD-160 with the [Family] sentence as a Prior attempt constraint · term → /forge:architect if 'board value' needs a glossary/requirement definition, then decompose, then redo · slice → /forge:kanban decompose (move board validation to CARD-161, which owns input) · continue → one more cycle
- [Unblocked] 2026-10-03 — owner chose targeted fix (trusted in-page values) + one final review cycle; F-005 owner-accepted (dispatcher)
- [Owner decision] F-005 owner-accepted: a 30x30 board with deep clues may scroll vertically on 1366x768 for the admin POC; the fit target stays 1440x900 — not fixed
- [Fix 3] (owner-approved targeted fix) FIXED F-011 — setBoard stores/paints copyBoard(next) built from own-data reads; withCell builds cells by index (no cells.slice()); F17 + solver_state.js header/isBoard doc + solver.js seam comment narrowed to trusted in-page values, Proxy/revoked-Proxy/indistinguishable claims and their tests removed; no handler added. Mutants (i) board=next, (ii) slice revert, (iii-a) copy skips last cell, (iii-b) copy drops height — all killed. Verify-by-revert: pre-fix code fails test_set_board_keeps_and_paints_its_own_copy ('getBoard() returned the object passed to setBoard') and test_with_cell_builds_its_cells_by_index_not_by_slice ('species'). Pre-gate: 3/3 named tests passed
- [Fix 3] declarations: 1 updated (F17 narrowed; isBoard/copyBoard/withCell/setBoard docs), 2 confirmed (F10, F11), 0 none
- [Commit] 1b869aa — fix rounds 1+2+3 (F-001, F-002, F-003, F-007, F-009, F-010, F-011) on the card branch, explicit pathspecs (solver.js, solver_state.js, tests/test_puzzle_solver_page.py); fixed_in stamped in the cycle YAMLs
- [Build gate] PASSED (full, 428s) — after fix 3 / commit 1b869aa: 5920 passed, 9 skipped, 2 failed = exactly the baseline pair (test_size_configuration_applied, test_batch_creation_form_renders)
- [Scope gate] cycle 4 (owner-granted final): IN_SCOPE — same 8 files vs main; G-2 untouched
- [Review 4/4] FULL mode (cycle 3 raised new Important F-011); owner-granted final cycle — a confirmed gating finding escalates for good; deferred mutation certification must run
- [Review 4/4] Score: 8.5 — crit: 0, imp: 0. FULL mode; F-011 ✓ resolved (1b869aa); Step 8h 53/53 addressed (14 ✓, 39 ⚠, 0 ✗); 8f-mutation RAN (deferred certification from cycle 3): 10 mutants, 9 killed, M6 (isBoard reads value.cells instead of own data) survived → filed Minor F-012 by the reviewer (out of trusted scope; behaviour still refuses before paint); Minor F-013 (F12 chrome sum misstated 204px vs 176px — bound looser, not refuted); F-004/F-006 Minor carried; F-005 owner-accepted; F-008 out of scope
- [Review 4/4] Score: 8.5 ✓ threshold reached + no critical/important
- [Review sync] 4 report(s) → meta/review/ (+ 20261003T113240Z-CARD-160-cycle4.yml)
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0038/R1) — named tests re-run green on 1b869aa, scans repeated; note: the ADR-0038/R1 line cites test_the_scripts_are_served_as_javascript by bare name (it lives in a class; resolves via -k)
- [AC/EC check] All criteria/constraints ✓ (evidence): (no ## Engineering constraints section; tests/test_puzzle_solver_page.py 62 passed, 0 skipped, real Chromium vs live loopback Flask + tmp SQLite; baseline+door tests 114 passed)
  AC-296 ✓ demonstrated — TestSolverPage_ShowsTheClues payload (25,15) [memory, sqlite] + browser board_is_15_rows_of_25_cells (rowLengths == [25]*15)
  AC-297 ✓ demonstrated — browser each_of_40_boxes_shows_its_clue vs an independent encoder; rowClues[2] == ["0"]
  AC-298 ✓ demonstrated — TestSolverPage_EmphasisesEveryFifthLine::test_the_25x15_board computed widths: heavy cols [5,10,15,20], rows [5,10]; 12-size property test
  AC-299 ✓ demonstrated — TestSolverPage_UnknownPuzzleIs404::test_no_such_puzzle_is_the_panels_404 [memory, sqlite]: 404 + panel 404 page
  AC-300 ✓ demonstrated — TestPuzzleDetail_OffersSolve::test_the_modal_links_to_the_player: href /puzzle/<id>/solve, click loads the player
  AC-301 ✓ demonstrated — TestSolverPage_AllCellsStartUndecided::test_all_400_cells_start_undecided: state 400×unknown, none drawn filled/marked
  AC-302 ✓ demonstrated — TestSolverPage_WritesNothing::test_ten_strokes_and_a_solve_write_nothing: SELECT * snapshots of puzzles/books/batches/generation_history identical, 0 requests after load (strokes via puzzlePlayer.setBoard on the live page; real clicks arrive with CARD-161)
  G-1 ✓ demonstrated — test_the_dependency_baseline_is_still_closed PASS; project.dependencies unchanged; only hand-written JS, no vendored/CDN code
  G-2 ✓ demonstrated — git diff --name-only main...HEAD -- src/nonogram/solver/ and git status -- src/nonogram/solver/ both empty
  G-3 ✓ demonstrated — TestSolverPage_WritesNothing PASS; route calls only get_puzzle, compute_clues, render_template
  G-4 ✓ demonstrated — tests/test_admin_binding.py + tests/test_admin_auth.py PASS, both untouched; one @app.route added, no door/auth/bind change
- [Docs] skipped — the changed src/ directories (admin, admin/static, admin/templates) carry no per-directory README (convention is an open owner decision, backlog line 10); tests/README.md catalogues no per-feature test file, so nothing in it went stale. DESIGN-REGISTER lines (SolverBoard, ClueBox, modal Solve action) NOT applied: meta/design/components.md is outside the card's Touches and nothing under meta/ is committed from the worktree — left for the dispatcher at merge (F-008)
- [Commit] success commit = 1b869aa (fix rounds 1-3, committed before the final review on the coordinator's instruction); the passing cycle-4 review, spot-check and AC/EC/G gate ran on exactly 1b869aa and left no source diff, so /commit had nothing further to commit (git status: only meta/ files)
- [Renders] refreshed on 1b869aa → ~/Documents/nonogram-reviews/CARD-160/ (player-small/25x15/30x30 at 1440 and 390, modal-solve-entry-1440.png; card160_render.py)
- [Merged] 2026-10-03 — 625ce14 into main (--no-ff). Merge gate: rebase was a no-op (main still at e3a7db3 = branch base); the merged tree is 1b869aa, the one that passed the cycle-4 full suite (5920 passed, only the 2 baseline failures); not re-run. Deferral scan: 0 hits. Trace write-back: no change — FR-044 already lists all six evidence tests (planned by the architect delta); status stays partial while CARD-161/162 are open. F-008 applied at close-out: SolverBoard and ClueBox registered in meta/design/components.md, Modal gains the Solve action. F-013 noted: failure-matrix row F12's chrome sum is 176px, not the 204px declared (bound looser, not refuted). F-004/F-006/F-012 captured to backlog.
