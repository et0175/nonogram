# CARD-128: Level dividers and the difficulty order in print — "Easy", "Medium", "Hard" pages, numbers 1..n unbroken

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/128-book-level-dividers
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-15 (FR-041 print half)
**Idea:** —
**Wave:** 26
**Depends on:** CARD-126, CARD-127, CARD-134
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_answer_key.py, tests/test_book_pdf_levels.py, tests/property/test_book_order.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

1. **Print order.** The generator prints puzzles in CARD-126's `book_level_order`:
   easy, then medium, then hard, keeping the stored within-level order. A legacy mixed
   arrangement therefore prints grouped by level (AC-260), without the stored list being
   rewritten at PDF time.
2. **Divider pages** (TERM-031): one page before the first puzzle of each level that
   holds at least one puzzle. It carries **only** the level's name ("Easy", "Medium",
   "Hard"), is trim-sized, and has no band, no number and no other text. An empty level
   gets no divider.
3. **Numbering.** Puzzle numbers run 1..n in print order across levels. Dividers do not
   consume numbers. Two-up pages (CARD-127) pair only within a level: tiers are already
   equal in a pair, and the divider sits between levels.
4. **Answer key** (decided 2026-09-22 (d), FR-042 / FR-041 amended): small **level
   headings**, not divider pages. Each level starts a new answer page with its heading
   at the top. The walk and the headings are CARD-134's (AC-290..AC-292) and the heading
   line and 5 mm cap are CARD-133's. This card feeds them the grouped print order, so
   the answer levels follow the puzzle section's, and asserts the three-level default
   plan end to end: 31 answer pages after one SOLUTIONS page (AC-293; 30 before
   level-first pages).
5. **Parity with dividers** (FR-043, decided 2026-09-22 (d)): the interior starts at the
   guide page (CARD-135), so with the "Easy" divider the first puzzle page is interior
   page 3, right-hand, gutter on the left (AC-287). Every divider page takes its parity
   from its interior position like any other page (CARD-116).
6. The guide page's per-tier counts and the page-count report (CARD-127) stay correct
   with dividers counted. The report counts interior pages only (the cover file is
   never counted, FR-043).

## Acceptance criteria

- **AC-253** (INV-009) — given a Book 1 profile book arranged easy E1, easy E2, medium M1, medium M2, hard H1, all 20x20 (no pairs), when the book PDF is generated, then the puzzle section's pages run divider "Easy", E1, E2, divider "Medium", M1, M2, divider "Hard", H1.
  *test:* `TestBookPdf_DifficultyOrderWithDividerPerLevel`
- **AC-254** — given the book of AC-253, when its divider pages are read, then each divider page's only content is its level's name.
  *test:* `TestBookPdf_DividerPageCarriesLevelNameOnly`
- **AC-255** — given a book of 2 easy puzzles and 1 medium puzzle, all 20x20, when the book PDF is generated, then the medium puzzle's band reads "Puzzle 3 · Medium" — divider pages do not consume puzzle numbers.
  *test:* `TestBookPdf_DividerPagesDoNotConsumePuzzleNumbers`
- **AC-256** — given a book of 3 easy and 2 medium puzzles and no hard puzzle, when the book PDF is generated, then the PDF holds no "Hard" divider page.
  *test:* `TestBookPdf_EmptyLevelHasNoDivider`
- **AC-260** (INV-009) — given a book whose stored arrangement, saved before this rule, is medium M1, easy E1, hard H1, easy E2, when the book PDF is generated, then the puzzles print in the order E1, E2, M1, H1.
  *test:* `TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel`
- **AC-287** (FR-043, INV-013, added 2026-09-22 (d)) — given a Book 1 profile book whose interior runs guide page, "Easy" divider, then its first puzzle page, when the book is exported, then the first puzzle page is interior page 3, a right-hand page, whose usable area starts 12.7 mm from its left trim edge (gutter on the left) — with the cover as page 1 it would have been a left-hand page 4.
  *test:* `TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1`
- **AC-293** (FR-042, INV-011, added 2026-09-22 (d)) — given a Book 1 profile book on the default plan — 150 puzzles at 40/40/20 with the AC-198 prefill, i.e. easy 50 answers at most 20 on the longest side then 10 longer, medium 34 then 26, hard 6 then 24, in that order inside each level — when the book PDF is generated, then the answer key is 31 answer pages — easy 11, medium 13, hard 7 — after 1 SOLUTIONS divider page (32 pages; 30 before level-first pages).
  *test:* `TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages`

## Engineering constraints

- **EC-029** (consistency, INV-009) — For any book and any sequence of adds, removes and moves, the book order stays grouped by tier (easy, then medium, then hard); the relative order of two puzzles of one level changes only through an explicit move within that level; and the book PDF holds exactly one divider per non-empty level, immediately before that level's first puzzle, with puzzle numbers 1..n unbroken — for every sequence, not only the measured examples.
  *test:* `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence` — _extend CARD-126's property with the PDF half: dividers, their positions, and 1..n numbering._
- EC(ADR-0037/R1): the band stays "Puzzle N · Tier" with N the print position after grouping, and divider pages carry no band.
  *test:* `PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle` (CARD-117 — add grouped and divided books)

## Guardrails

- G-1: Dividers and print order are decided at PDF time, and nothing is stored (Increment 15 Rollback). Do not edit `src/nonogram/db/**`, `migrations/**` or `src/nonogram/admin/book_manager.py`.
- G-2: Out of scope: solution hints (deferred). Answer-key packing and headings are CARD-134's and are consumed as delivered.
- G-3: The admin panel fits no cells itself (ADR-0036/R2). Divider pages are text on a blank trim page.
- G-4: Do not edit `src/nonogram/admin/app.py`, `src/nonogram/admin/templates/books_list.html` or `src/nonogram/admin/book_manager.py`. They are owned by CARD-131 / CARD-132 this wave.

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
- ADR-0031/R1 — Tier has exactly three members — easy, medium, hard — and every one has a score band. classify takes the score alone; no module derives a tier from branch_nodes. (check: TestTiers_ThreeBandsAndNoFourthTier)
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (check: TestTiers_BranchingIsAStrategyNotATier)
- ADR-0031/R3 — A stored difficulty_tier of "guess" reads back as Tier.HARD and is never rewritten by this decision; no migration runs and no production database is touched. (check: TestTiers_LegacyGuessRowReadsAsHard)
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
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is … (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-041 (answer-key headings delivered by CARD-134 on FR-042's pages), FR-042 (AC-293), FR-043 (AC-287)
- **NFR:** —
- **ADR:** ADR-0037, ADR-0031
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

- [Handover from CARD-117, 2026-09-23] Puzzle numbering is positional: reordering renumbers the bands and the answer key together, and a per-level divider changes page positions only — N stays index+1 over the puzzles, not over pages.
