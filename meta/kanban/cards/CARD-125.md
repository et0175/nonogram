# CARD-125: The pair-aware layout call — two puzzles, one shared cell in [7.0, 7.5] mm, or no pairing

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/125-pair-aware-layout
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-15 (COMP-007 half of FR-040)
**Idea:** —
**Wave:** 22
**Depends on:** CARD-114
**Touches:** src/nonogram/export/layout.py, src/nonogram/export/__init__.py, tests/test_layout_two_up.py, tests/property/test_book_two_up.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

This card is the first implementation of ADR-0036's 2026-09-22 clarification ("Two-up
pages"). FR-040's `_meta` left the API shape open, and this card settles it.

1. **`compute_pair_layout(first, second, page_spec) -> PairLayout | None`** in
   `export/layout.py`. `first` and `second` are each `(row_clues, column_clues)`.
   - The shared cell is the **largest** cell, capped at the spec's flat cap (7.5 mm),
     at which (a) the combined drawing height of both puzzles (grid rows plus
     column-clue rows of each) × cell, plus **one band per puzzle**, fits the usable
     height (trim − top − bottom), and (b) **each** puzzle's drawing width (grid columns
     plus row-clue columns) × cell fits the usable width. Clue depths are the real
     depths (TERM-021).
   - It returns `None` (no pairing) when that cell is below the **7.0 mm two-up
     minimum** (a named constant).
   - Otherwise it returns both slot `Layout`s at that one cell, with their page
     positions: the **earlier puzzle in the upper slot**, the upper slot's drawing top
     edge at top margin + band (the same fixed row as a single page, EC-022), and the
     lower slot below its own band. The slots must not overlap.
   - It is only valid for a portrait-only, flat-cap spec. Any other spec raises
     `ValueError`: the default A4 spec never pairs.
2. The single-puzzle `compute_layout` is **unchanged**. A single puzzle keeps using it
   (ADR-0036 clarification).
3. It reuses the existing private helpers (`_gutter_depth`, `_axis_lines`,
   `_rule_widths`, clue placement) so strokes and every-5th rules match the single-page
   book path. Do not add a second implementation of cell fitting.
4. Pin the arithmetic of AC-242..AC-247 at layout level here: 7.5, 7.39, 7.16 mm,
   `None` at 6.95 and 6.57 mm, and `None` on the width failure. CARD-127 re-asserts
   them on the PDF.

If writing this reveals that ADR-0036's clarification cannot be met as worded (for
example, the fixed top edge conflicts with the combined-height rule), stop and escalate
to the architect station. Do not reshape the rule here.

## Acceptance criteria

_Layout-level halves of FR-040's criteria (the PDF-level tests are CARD-127):_

- **AC-242** (INV-010) — given a Book 1 profile book whose order starts with two easy 10x10 puzzles, each with 4-deep row- and column-clue gutters (combined drawing height 28 cells), when the book PDF is generated, then both puzzles print on one page at a 7.5 mm shared cell (the page fit of 8.44 mm capped at the standard cell).
  *test:* `TestPairLayout_TwoTenByTensShareAtStandardCell`
- **AC-243** (INV-010) — given a Book 1 profile book whose order starts with two easy 12x12 puzzles, each with 4-deep row- and column-clue gutters (combined drawing height 32 cells), when the book PDF is generated, then both puzzles print on one page at a 7.39 mm shared cell (+/- 0.05 mm; 236.35 mm over 32 cells).
  *test:* `TestPairLayout_TwelvePairAtSevenThirtyNine`
- **AC-244** (INV-010) — given a Book 1 profile book whose order has an easy 15x15 puzzle with a 5-deep column-clue gutter followed by an easy 10x10 puzzle with a 3-deep column-clue gutter (combined drawing height 33 cells), when the book PDF is generated, then both puzzles print on one page at a 7.16 mm shared cell (+/- 0.05 mm) — at or above the 7.0 mm two-up minimum.
  *test:* `TestPairLayout_JustAboveTwoUpMinimum`
- **AC-245** (INV-010) — given the same book but the 15x15 puzzle's column-clue gutter is 6 deep (combined drawing height 34 cells, 6.95 mm shared cell), when the book PDF is generated, then the two puzzles print on two separate pages.
  *test:* `TestPairLayout_JustBelowTwoUpMinimumIsNone`
- **AC-246** (INV-010) — given a Book 1 profile book whose order has an easy 15x15 puzzle with a 5-deep column-clue gutter followed by an easy 12x12 puzzle with a 4-deep one (combined 36 cells, 6.57 mm), when the book PDF is generated, then the two puzzles print on two separate pages.
  *test:* `TestPairLayout_FifteenPlusTwelveIsNone`
- **AC-247** (INV-010) — given a Book 1 profile book whose order has an easy 22-wide x 10-tall puzzle with a 6-deep row-clue gutter (28 cells across, at most 6.92 mm on the 193.7 mm usable width) followed by an easy 10x10 puzzle with 3-deep gutters, when the book PDF is generated, then the two puzzles print on two separate pages — the pair fits the height but the wide puzzle's drawing does not fit the width at 7.0 mm.
  *test:* `TestPairLayout_WidthFailureAtTwoUpMinimumIsNone`

## Engineering constraints

- **EC-028** (consistency, NFR-008) — For any two puzzles of 10..30 cells per side, any clue depths and any stored trim and margins, a two-up page's shared cell lies in [7.0, 7.5] mm, both puzzles print at that one cell, and both drawings with their two 12 mm bands lie inside the usable area without overlapping — and a pair whose largest fitting cell is below 7.0 mm is never put on one page.
  *test:* `PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea`
- EC(ADR-0036/R1): adding the pair-aware call leaves `compute_layout`'s default path byte-identical.
  *test:* `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` (CARD-113) stays green
- EC(ADR-0037/R2): both slots use the book strokes (thin ≥ 0.25 mm, heavy = 2 × thin, black) at the shared cell.
  *test:* `PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin` (CARD-114 — add two-up cases)

## Guardrails

- G-1: CLI and web A4 output stay byte-identical (CON-019, ADR-0036/R1). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry.
- G-2: `compute_layout`'s signature and single-puzzle behaviour are unchanged. The pair call is additive (Increment 15 Rollback: "nothing is stored, so reverting restores one puzzle per page").
- G-3: Do not edit `src/nonogram/admin/**`, `src/nonogram/db/**` or `migrations/**`. The walk that decides which neighbours to offer is CARD-127 (ADR-0036/R2), and nothing is stored.
- G-4: Do not edit `tests/fixtures/a4_golden/**`. It is CARD-113's tripwire.

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
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)

## Architecture context

- **FR:** FR-040
- **NFR:** NFR-008
- **CON:** CON-019
- **ADR:** ADR-0036, ADR-0037
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
