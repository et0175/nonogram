# CARD-122: Puzzle selection by longest-side tab — planned-vs-selected headers, whole-book summary, tier-then-shorter-side sort

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/122-select-by-longest-side-tab
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-14 (FR-036)
**Idea:** —
**Wave:** 22
**Depends on:** CARD-119, CARD-120
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, tests/test_book_select_tabs.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

1. **Four tabs** on `/book/<id>/select-puzzles`: ≤15 · 16–20 · 21–25 · 26–30. The trace
   note suggests a server-rendered `?bucket=` parameter on the existing route; FR-036's
   open question (separate routes or client-side tabs) is not a blocker, so record the
   choice. Each puzzle is listed on exactly one tab, using CARD-119's `bucket_of`.
   Never re-derive the bucket.
2. **Selections survive tab switches** (AC-211). Server-side, a selection is submitted
   per tab and kept (in the session or as book membership, according to what the current
   step does today; record which). Switching tabs never drops it.
3. **Headers.** Each tab shows, per tier and in total, `selected / planned` for its
   bucket, from CARD-119's `selection_cells` and `planned_cells` against the stored
   plan. Over-plan cells are marked as over. The same summary for the whole book sits
   above the tabs. If a book has no plan, show the selected counts alone and link to
   Print setup (ADR-0035's remedy).
4. **Sort inside a tab:** tier (easy, medium, hard), then shorter side ascending.
5. **Filters:** theme, name, quality and difficulty still apply inside a tab. The
   **size-range filter (`size_from`/`size_to`) is removed**, replaced by the tab.
6. Tiles keep their current content in this card. The per-tile cell and below-floor
   flag are CARD-123.

## Acceptance criteria

- **AC-208** — given a 15-wide x 30-tall puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the 26-30 tab only.
  *test:* `TestBookSelect_PuzzleListedUnderLongestSideTab`
- **AC-209** — given a 15-wide x 16-tall puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the 16-20 tab, not the <=15 tab.
  *test:* `TestBookSelect_LongestSideSixteenGoesToSecondTab`
- **AC-210** — given a 15x15 puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the <=15 tab.
  *test:* `TestBookSelect_LongestSideFifteenGoesToFirstTab`
- **AC-211** — given 3 puzzles selected on the <=15 tab, when the owner switches to the 21-25 tab and back, then the same 3 puzzles are still selected.
  *test:* `TestBookSelect_SelectionKeptAcrossTabSwitch`
- **AC-212** — given a plan of 21-25 easy 10 / medium 20 / hard 12 and 8 easy, 20 medium, 14 hard puzzles selected in that bucket, when the 21-25 tab is rendered, then its header reads 21-25: easy 8 / 10 · medium 20 / 20 · hard 14 / 12.
  *test:* `TestBookSelect_TabHeaderShowsPlannedVsActual`
- **AC-213** — given the same 21-25 bucket with 14 hard selected against a plan of 12, when the 21-25 tab is rendered, then the hard cell is marked over plan.
  *test:* `TestBookSelect_OverPlanCellMarked`
- **AC-214** — given a plan with 60 easy puzzles and 12 easy selected on the <=15 tab plus 30 on the 16-20 tab, when puzzle selection is rendered, then the whole-book summary above the tabs reads easy 42 / 60.
  *test:* `TestBookSelect_BookSummarySumsAllTabs`
- **AC-215** — given a 21-25 bucket holding a hard 25x21, an easy 25x18, an easy 22x16 and a medium 25x25 puzzle, when the 21-25 tab is rendered, then the order is easy 22x16, easy 25x18, medium 25x25, hard 25x21.
  *test:* `TestBookSelect_TabSortsByTierThenShorterSide`
- **AC-216** — given any book on the puzzle-selection step, when the page is rendered, then it carries no size_from or size_to field.
  *test:* `TestBookSelect_SizeRangeFilterReplacedByTab`
- **AC-217** — given a 21-25 bucket holding 3 easy, 2 medium and 4 hard puzzles, when the 21-25 tab is filtered by difficulty hard, then exactly the 4 hard puzzles are listed.
  *test:* `TestBookSelect_ExistingFiltersApplyInsideTab`

## Engineering constraints

- **EC-024** (consistency) — For every extent of 10..30 x 10..30, the longest-side bucketing assigns the puzzle to exactly one of the four buckets, chosen by max(width, height) alone — the four tabs partition the supported size range with no gap and no overlap, and one bucketing function serves the plan (FR-034), the tabs and the readiness check (FR-037).
  *test:* `PropertyTest_LongestSideBuckets_PartitionEveryExtent` (CARD-119 — add a route-level case: every available puzzle appears on exactly one rendered tab)

## Guardrails

- G-1: One bucketing function. The route and the template import `book_plan.bucket_of`, and no second `max(w, h)` threshold table appears (EC-024).
- G-2: Out of scope: BK-UI-8 (the owner's unfinished "When adding puzzles to book, please add a possibility to …"). It goes back to the owner and is not guessed here.
- G-3: Assigned-puzzle exclusion (a puzzle held by another book is not offered) stays as it is (ADR-0033, one book per puzzle).
- G-4: Do not edit `src/nonogram/admin/book_manager.py` or `src/nonogram/admin/book_page_spec.py`. They are owned by CARD-124 / CARD-115 this wave.
- G-5: Do not edit `src/nonogram/export/**`. It is owned by CARD-125 this wave.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as … (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it … (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from … (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX … (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, … (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is … (check: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled … (check: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, … (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of … (check: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims … (check: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each … (check: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from … (check: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and … (check: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside … (check: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero … (check: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with … (check: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left … (check: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (check: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the … (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form … (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This … (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an … (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens … (check: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the … (check: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (check: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (check: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level … (check: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes … (check: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)

## Architecture context

- **FR:** FR-036
- **NFR:** —
- **ADR:** ADR-0033, ADR-0035 (plan-less remedy)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md (direction + anti-patterns), tokens.css (all visual values), components.md (inventory + states)
- **UI components:** PuzzleTile (reuse), FilterBar (reuse — size-range fields removed), TierChip (reuse), StatBlock (reuse for the planned-vs-selected summary; "emphasised" state for over-plan), Stepper (reuse); longest-side tabs — **register a "Tabs" entry in components.md** (states: default · current · with-over-plan marker)
- **Screens:** /book/<id>/select-puzzles (four tabs)
- **Standards:** forge:engineering-standards §11 (tokens-only styling, all listed states, a11y minimum — tabs keyboard-reachable, current tab announced)

## Worktree notes

—
