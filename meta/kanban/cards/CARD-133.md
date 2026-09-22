# CARD-133: Answer tiles in COMP-007 — grid-only answers on a 2 × 3 or 2 × 2 tiled page of the book PageSpec

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/133-answer-tiles-layout
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-15 (COMP-007 half of FR-042, added by the 2026-09-22 (c) delta)
**Idea:** —
**Wave:** 22
**Depends on:** CARD-114
**Touches:** src/nonogram/export/layout.py, src/nonogram/export/png.py, src/nonogram/export/__init__.py, tests/test_layout_answer_tiles.py, tests/property/test_book_answer_tiles.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

FR-042 (owner decision BK-8, 2026-09-22 (c)) replaces today's one full answer page per
puzzle with a packed answer key. ADR-0036/R2 keeps all book geometry in COMP-007, so
the tile geometry and the tile drawing live here. The page-filling walk and the
captions' text are CARD-134 (COMP-009). This card follows the CARD-125/CARD-127 split
of FR-040.

1. **`compute_answer_page_layout(extents, capacity, page_spec) -> AnswerPageLayout`**
   in `export/layout.py`. `extents` is a list of up to `capacity` `(width, height)`
   answer grids, in order. `capacity` is 6 (2 columns × 3 rows) or 4 (2 × 2). The page
   is the book `PageSpec`, **mirrored margins included** (CARD-114's parity: the usable
   area follows the page's parity), with **no title band** on an answer page.
   - Tile size: `(usable width − 2 mm) / 2` wide and
     `(usable height − (rows − 1) × 2 mm) / rows` tall. On the Book 1 profile that is
     95.85 × 85.45 mm (6-up) and 95.85 × 129.18 mm (4-up), from a 193.7 × 260.35 mm
     usable area.
   - Each tile reserves a **6 mm caption line**. The grid is drawn at the **largest
     square cell** that fits the rest of the tile:
     `min(tile width / columns, (tile height − 6 mm) / rows)`.
   - Tiles fill left to right, top to bottom, in the order given.
   - Name the 2 mm gap and the 6 mm caption line as constants. They are FR-042's stated
     geometry, not the owner's figures. The owner quoted 3.7 mm and 3.1 mm, and this
     geometry gives 3.97 mm and 3.19 mm, so "about 3 mm or more" holds with margin.
   - It is valid only for a book `PageSpec` (portrait-only, flat cap). Any other spec
     raises `ValueError`: the default A4 spec has no answer tiles.
   - **Answer cells are capped at 5 mm** (decided 2026-09-22 (d), FR-042 amended,
     BK-8): `cell = min(5 mm, tile width / columns, (tile height − 6 mm) / rows)`. A
     10×10 in a 6-up tile would otherwise get 7.94 mm and a 15×15 5.30 mm; both print at
     5.0 mm (AC-294). Name the cap as a constant beside the gap and caption line.
   - **Level heading line** (decided 2026-09-22 (d)): an optional `heading` argument.
     When given, the page reserves a **6 mm heading line plus the 2 mm gap** at the top
     of its usable area, and the tile rows share the height below it:
     `(usable height − 8 mm − (rows − 1) × 2 mm) / rows`. On the Book 1 profile a 6-up
     tile becomes 95.85 × 83.45 mm (20×20 → 3.87 mm, AC-295). A 4-up tile becomes
     95.85 × 126.18 mm, where a 30×30 is still width-limited at 3.19 mm. Without a
     heading the geometry is exactly the one above. Which page carries a heading is
     the caller's decision (CARD-128), not this card's.
2. **`render_answer_page(answers, capacity, page_spec, heading=None) -> Image`** in `export/png.py`.
   `answers` is a list of `(grid, caption)` pairs. It draws each answer as its **filled
   grid only**: filled cells, grid rules and every-5th heavy rules under the book
   stroke minimum (ADR-0037/R2). It draws **no clue numbers and no clue gutters**. It
   prints the caption text on the tile's caption line. The caption string comes from
   the caller. This card does not compose "Puzzle N — Title". When `heading` is given
   it prints that text (e.g. "Easy") small, on the reserved heading line.
3. Reuse the existing private helpers (`_axis_lines`, `_rule_widths`, the stroke
   policy). Do not write a second implementation of rules or stroke widths.
4. Pin AC-262, AC-265, AC-294 and AC-295 at layout level with a Book 1 `PageSpec` literal built in the
   test (no `nonogram.admin` import, as in CARD-114). CARD-134 re-asserts them on the
   PDF.

## Acceptance criteria

- **AC-262** (reworded 2026-09-22 (d)) — given a Book 1 profile book whose answer key holds a 20x20 answer on a 6-up page that is not the first answer page of its level, when the answer's grid is measured, then its cell is 3.97 mm (+/- 0.05 mm; 79.45 mm tile grid area over 20 rows).
  *test:* `TestBookAnswerKey_TwentyInSixUpTileCellSize`
- **AC-265** — given a Book 1 profile book whose answer key holds a 30x30 answer on a 4-up page, when the answer's grid is measured, then its cell is 3.19 mm (+/- 0.05 mm; 95.85 mm tile width over 30 columns).
  *test:* `TestBookAnswerKey_ThirtyInFourUpTileCellSize`
- **AC-267** — given a Book 1 profile book holding a 15x15 puzzle whose row and column clues are non-empty, when its answer tile is rendered, then the tile draws the 15 x 15 filled grid and no clue number.
  *test:* `TestBookAnswerKey_AnswerDrawsGridOnlyNoClues`
- **AC-294** (added 2026-09-22 (d)) — given a Book 1 profile book whose answer key holds a 10x10 answer on a 6-up page, when the answer's grid is measured, then its cell is 5.0 mm (+/- 0.05 mm) — the 5 mm answer cap, not the 7.94 mm the tile would allow.
  *test:* `TestBookAnswerKey_SmallAnswerCellCappedAtFiveMm`
- **AC-295** (added 2026-09-22 (d)) — given a Book 1 profile book whose answer key holds a 20x20 answer on the first 6-up answer page of its level (under the level heading), when the answer's grid is measured, then its cell is 3.87 mm (+/- 0.05 mm; 77.45 mm tile grid area over 20 rows).
  *test:* `TestBookAnswerKey_HeadingPageTwentyInSixUpTileCellSize`

## Engineering constraints

- **EC-031** (consistency; amended 2026-09-22 (d)) — For any answer of 10..30 cells per side on the Book 1 profile, on either page parity and whether or not its page carries a level heading, the answer's cell lies in [3.19, 5.0] mm, its grid and 6 mm caption line lie inside its tile, and every tile and the heading line lie inside the page's usable area without overlapping one another — for every extent and position, not only the measured examples.
  *test:* `PropertyTest_BookAnswerKey_CellAtLeast319AndTilesInsideUsableArea`

## Guardrails

- G-1: CLI and web A4 output stay byte-identical (CON-019, ADR-0036/R1). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, TestCliExports_ByteIdenticalAfterBookGeometry, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry.
- G-2: `compute_layout`, `render_image` and `render_pages` keep their signatures and behaviour. The CLI PDF's own answer page (the second page `render_pages` returns) is unchanged. The answer-tile calls are additive.
- G-3: Do not edit `src/nonogram/admin/**`, `src/nonogram/db/**` or `migrations/**`. The page-filling walk and the caption text are CARD-134 (ADR-0036/R2), and nothing is stored.
- G-4: Do not edit `tests/fixtures/a4_golden/**` or `tests/test_export_a4_golden.py`. They are CARD-113's tripwire.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as … (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it … (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from … (check: review-lens)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions from one. (check: review-lens)
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
- CON-019 — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's exports: for any generation request the PNG, SVG and PDF files … (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
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

- **FR:** FR-042 (AC-262, AC-265, AC-267, AC-294, AC-295, EC-031)
- **NFR:** —
- **CON:** CON-019
- **ADR:** ADR-0036, ADR-0037
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
