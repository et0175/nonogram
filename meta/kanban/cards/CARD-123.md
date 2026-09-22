# CARD-123: Every tile shows its cell on the book's trim, below-floor flagged with an override control; finalise counts below-floor puzzles

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/123-tile-cell-and-floor-count
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-14 (surface half of FR-031; closes Increment 14)
**Idea:** —
**Wave:** 24
**Depends on:** CARD-121, CARD-122
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/book_finalize.html, tests/test_book_select_floor_tiles.py, tests/property/test_book_membership_floor.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

1. **Tile cell.** Every tile on the selection tabs shows the puzzle's cell on the book's
   current trim and margins, already capped at 7.5 mm, computed with CARD-115's
   `book_cell_mm(book_page_spec(book), …)`. It is the same call CARD-121's refusal and
   CARD-116's PDF make. Format: one decimal place is too coarse near the floor (4.84 vs
   4.8), so use two decimals ("4.61 mm").
2. **Below-floor flag** on a tile under 4.8 mm, plus an **explicit override control**
   (e.g. a labelled "Include below floor" checkbox bound to the `override_<id>` field
   CARD-121 reads). A wide grid carries **no flag of its own** (FR-032 amended; AC-191/192
   retired). Only the floor flags.
3. **Finalise summary** (`book_finalize.html`) counts the book's puzzles below the floor,
   **recomputed on the book's current trim and margins** every time it renders. It is
   not read from stored overrides, so a trim change after curation shows up (AC-188).
4. Extend `PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride` with the
   agreement half of EC-021: for any puzzle and trim, the tile's value, the add
   refusal's value and the finalise count's per-puzzle verdict are one number.

## Increment 14 checkpoint (this card closes it)

A new book's Print setup shows 150 at 40/40/20 and the AC-198 matrix (≤15: 20/7/0,
16-20: 30/27/6, 21-25: 10/20/12, 26-30: 0/6/12). The plan survives leaving and
reopening (CARD-119/120). On the selection step, a 30×25 puzzle with a 12-deep row clue
shows 4.61 mm with a below-floor flag. It is refused on both the tab and the paste-IDs
route, and then accepted with an override that the finalise summary counts
(CARD-121/123). A 100-puzzle book with one cell at 14% against 10% is refused with that
cell named, a `draft → ready_for_kdp` jump is refused the same way, and at 13% it passes
(CARD-124). Put a rendered selection tab and the finalise summary in
`~/Documents/nonogram-reviews/CARD-123/` for the owner's eye.

## Acceptance criteria

- **AC-182** — given a Book 1 profile book and a 30-wide x 25-tall puzzle whose row-clue gutter is 12 entries deep and column-clue gutter 8 deep (42 cells across, 4.61 mm on the trim), when the puzzle-selection step lists it, then its tile shows a 4.61 mm cell with a below-floor flag.
  *test:* `TestBookSelect_TileShowsCellAndBelowFloorFlag`
- **AC-241** — given a Book 1 profile book and a 25-wide x 12-tall puzzle whose book cell is 6.0 mm (above the 4.8 mm floor), when the puzzle-selection step lists it, then its tile carries no flag — neither a wide-grid flag nor a below-floor flag.
  *test:* `TestBookSelect_WideGridAboveFloorCarriesNoFlag`
- **AC-187** — given a book holding 150 puzzles, 2 of them added below the floor with overrides, when the finalise step renders its summary, then the summary reports 2 puzzles below the 4.8 mm floor.
  *test:* `TestBookFinalize_SummaryCountsPuzzlesBelowFloor`
- **AC-188** — given a Book 1 profile book holding a 20x20 puzzle with 8-deep row- and column-clue gutters (6.92 mm on 8.5 x 11), no puzzle below the floor, when its trim is changed to 6 x 9 in and the finalise summary is rendered, then the summary reports 1 puzzle below the floor (4.65 mm on the new trim).
  *test:* `TestBookFinalize_SummaryRecountsBelowFloorAfterTrimChange`
- **AC-239** (NFR-008) — given a Book 1 profile book holding a 30-wide x 25-tall puzzle with a 12-deep row-clue gutter, when its book cell is computed, then cell < 4.8 mm (4.61 mm) and the puzzle is flagged below the floor (FR-031).
  *test:* `TestBookCell_TwelveDeepBandFallsBelowFloor` — _flag half here; the 4.61 mm cell is CARD-114._

## Engineering constraints

- **EC-021** (consistency, INV-006) — For any puzzle, any stored trim and margins and every add route (selection step, paste-IDs form, any future route ending in the book store), a puzzle whose book cell is below 4.8 mm becomes a member only together with a stored override for its id; and the tile's cell, the add refusal and the finalise count all come from the one computation FR-030's PDF uses, so no two of them can disagree about a puzzle.
  *test:* `PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride`

## Guardrails

- G-1: One computation. Tile, refusal and finalise count all call `book_cell_mm`, and the admin fits no cell itself (ADR-0036/R2, EC-021).
- G-2: No wide-grid flag. AC-191/AC-192 are retired, and only the floor flags a tile (FR-032 amended 2026-09-22 (b)).
- G-3: Out of scope: BK-UI-8 (unstated add-puzzles ask; back to the owner).
- G-4: Do not edit `src/nonogram/admin/book_manager.py` or `src/nonogram/admin/templates/book_arrange_puzzles.html`. They are owned by CARD-126 this wave. Do not edit `src/nonogram/admin/book_pdf_generator.py`, which is owned by CARD-117 this wave.

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

- **FR:** FR-031, FR-032 (AC-241)
- **NFR:** NFR-008
- **ADR:** ADR-0036
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md (direction + anti-patterns), tokens.css (all visual values), components.md (inventory + states)
- **UI components:** PuzzleTile (extend — add a "below floor" state with its cell value and an override checkbox; update components.md's PuzzleTile states), StatBlock (reuse on finalise for the below-floor count; "zero" renders 0, never hidden), Flash / Alert (reuse — refusal message naming mm vs floor)
- **Screens:** /book/<id>/select-puzzles, /book/<id>/finalize
- **Standards:** forge:engineering-standards §11 (tokens-only styling, all listed states, a11y minimum — the flag is text, not colour alone)

## Worktree notes

—
