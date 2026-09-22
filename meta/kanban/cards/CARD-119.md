# CARD-119: The distribution plan as pure domain — longest-side buckets, Book 1 prefill, POL-007 re-derive

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/119-book-plan-domain
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-14 (domain half; storage and Print setup are CARD-120)
**Idea:** —
**Wave:** 20
**Depends on:** —
**Touches:** src/nonogram/admin/book_plan.py, tests/test_book_plan.py, tests/property/test_book_plan.py, tests/property/test_longest_side_buckets.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-09-22T15:26:35Z
**Closed:** 2026-09-22T16:16:56Z
**Actual:** 0.1d
**Merge commit:** da6cf84
**Blocked by:** —

## What to implement

This card covers the arithmetic of FR-034/FR-035 as pure functions, with no DB, Flask or
templates. It lives in `admin/book_plan.py` (COMP-009, AGG-002's plan value). Everything
later in Increments 14 and 16 reads these functions: the Print setup form, the tabs,
the gate and the books-list stats.

1. **`LongestSideBucket`**: `≤15`, `16–20`, `21–25`, `26–30` (TERM-027).
   `bucket_of(width, height)` uses `max(width, height)` alone. This is the **one**
   bucketing function EC-024 requires; the plan, the tabs (CARD-122), the gate
   (CARD-124) and the list hint (CARD-132) all import it and never re-derive it.
2. **`DistributionPlan`** (TERM-026/029), a value object:
   - `count` ≥ 1, and an easy/medium/hard split in whole percent that **must sum to
     exactly 100** (INV-005, AC-197; construction refuses otherwise);
   - a 4 × 3 per-bucket matrix of non-negative ints;
   - which cells were hand-edited.
3. **`prefill(count, split)`** rescales the Book 1 size × difficulty matrix
   (`docs/research/book-format-research.md` §8: ≤15 10/5/–, 16–20 15/20/5,
   21–25 5/15/10, 26–30 –/5/10) **column by column**:
   - The general plan's tier counts come from `count × split`. When that is not whole
     (e.g. 137 × 40%), round by **largest remainder** so the three tier counts sum to
     `count` (trace FR-034 note; EC-023).
   - Each tier column is then apportioned over the four buckets by largest remainder in
     proportion to the Book 1 column, so the column total equals the tier count exactly.
   - Zero-share cells (≤15 × hard, 26–30 × easy) stay 0.
   - **Tie-breaking** among equal remainders is unstated. AC-198's worked table
     (medium 60 → 7/27/20/6) implies ties go to the earlier bucket. Implement that, pin
     it with AC-198, and note it in Worktree notes.
4. **POL-007 / CMD-020 → EVT-021: `with_split(plan, new_split)`.** A plan with no
   hand-edited cells is re-derived. Hand-edited cells keep their values, and the result
   reports `disagrees_with_split=True` so Print setup can warn (AC-203 is rendered in
   CARD-120).
5. **`DEFAULT_PLAN`**: 150 at 40/40/20 (60/60/30) with the prefilled matrix (ADR-0034).
   A constant of book creation. Storing it on creation is CARD-120.
6. **`selection_cells(puzzles) -> {(bucket, tier): count}`** and
   **`planned_cells(plan)`**, shared helpers for planned-vs-actual (CARD-122 headers,
   CARD-124 gate, CARD-132 list). Tier comes from the stored tier through the one
   classifier's accessor (`difficulty.tier_of_record`), never re-graded (ADR-0033/R1).

## Acceptance criteria

- **AC-197** (INV-005) — given a draft book with a stored plan of 150 at 40/40/20, when Print setup is submitted with split 40/40/30 (110%), then the submission is rejected and the stored plan stays 150 at 40/40/20.
  *test:* `TestBookPlan_RejectsSplitNotSummingTo100` — _domain half here (construction refuses); the "stored plan stays" half is re-asserted through the route in CARD-120._
- **AC-198** — given a general plan of 150 puzzles at 40/40/20 with no hand-edited cells, when the per-bucket plan is prefilled, then the matrix is <=15: 20/7/0, 16-20: 30/27/6, 21-25: 10/20/12, 26-30: 0/6/12 (easy/medium/hard).
  *test:* `TestBookPlan_PrefillMatchesBook1MatrixAt150x40_40_20`
- **AC-199** — given a general plan of 120 puzzles at 30/45/25 (36/54/30), when the per-bucket plan is prefilled, then the 12 cells sum to 120 with column totals 36, 54 and 30.
  *test:* `TestBookPlan_PrefillColumnTotalsMatchGeneralPlan`
- **AC-200** — given a general plan of 120 puzzles at 30/45/25, when the per-bucket plan is prefilled, then the <=15 x hard cell and the 26-30 x easy cell are both 0.
  *test:* `TestBookPlan_ZeroShareCellsStayZero`
- **AC-201** (POL-007) — given a stored plan of 150 at 40/40/20 whose per-bucket cells were never hand-edited, when the general split is changed to 30/45/25, then the per-bucket plan is re-derived from the Book 1 matrix at 30/45/25.
  *test:* `TestBookPlan_UneditedMatrixRederivedOnSplitChange`
- **AC-202** (POL-007) — given a stored plan of 150 at 40/40/20 whose 21-25 x hard cell was hand-edited from 12 to 15, when the general split is changed to 30/45/25, then the 21-25 x hard cell still holds 15.
  *test:* `TestBookPlan_HandEditedCellSurvivesSplitChange`
- **AC-208** — given a 15-wide x 30-tall puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the 26-30 tab only.
  *test:* `TestBookSelect_PuzzleListedUnderLongestSideTab` — _bucket-function half here (`bucket_of(15, 30)` is 26–30); the rendered tab is CARD-122._
- **AC-209** — given a 15-wide x 16-tall puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the 16-20 tab, not the <=15 tab.
  *test:* `TestBookSelect_LongestSideSixteenGoesToSecondTab` — _bucket-function half; rendered in CARD-122._
- **AC-210** — given a 15x15 puzzle available for a book, when puzzle selection is rendered, then the puzzle is listed on the <=15 tab.
  *test:* `TestBookSelect_LongestSideFifteenGoesToFirstTab` — _bucket-function half; rendered in CARD-122._

## Engineering constraints

- **EC-023** (consistency, INV-005) — For any count of at least 1 and any split summing to 100%, the prefilled per-bucket plan has 12 non-negative integer cells whose sum equals the count, whose per-tier column totals equal the general plan's tier counts, and whose zero-share cells (<=15 x hard, 26-30 x easy) are 0 — for every count and split, not only the measured examples.
  *test:* `PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan`
- **EC-024** (consistency) — For every extent of 10..30 x 10..30, the longest-side bucketing assigns the puzzle to exactly one of the four buckets, chosen by max(width, height) alone — the four tabs partition the supported size range with no gap and no overlap, and one bucketing function serves the plan (FR-034), the tabs and the readiness check (FR-037).
  *test:* `PropertyTest_LongestSideBuckets_PartitionEveryExtent`

## Guardrails

- G-1: Out of scope: an audience-derived default split (ADR-0034's rejected alternative; AC-206/AC-207 retired). `DEFAULT_PLAN` is a constant, not a function of `target_audience`.
- G-2: Pure domain module. No import of `nonogram.db`, Flask or templates from `book_plan.py`, and no DB schema change in this card (storage is CARD-120).
- G-3: Book assembly never re-grades a puzzle. Tier is read, not computed (ADR-0033/R1).
- G-4: Do not edit `tests/test_export_a4_golden.py` or `tests/fixtures/a4_golden/**`. They are owned by CARD-113 this wave.

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
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is … (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-034, FR-035, FR-036 (bucketing only)
- **NFR:** —
- **ADR:** ADR-0034, ADR-0033
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

Implemented `src/nonogram/admin/book_plan.py` (pure domain; imports only `nonogram.difficulty`, `nonogram.errors`, `nonogram.limits`).
- **API:** `LongestSideBucket` (+ `label`/`low`/`high`, outer ends from `limits.MIN_SIZE`/`MAX_SIZE`), `BUCKETS`, `TIERS`, `bucket_of(width, height)`, `Split(easy, medium, hard)`, `BOOK1_MATRIX`, `DistributionPlan(count, split, cells, edited)` with `cell()`, `tier_counts`, `disagrees_with_split`; `tier_counts(count, split)`, `prefill(count, split)`, `with_split(plan, new_split)`, `with_edited_cell(plan, bucket, tier, value)`, `DEFAULT_PLAN`, `planned_cells(plan)`, `selection_cells(puzzles)`, `InvalidPlan(ValueError)`.
- **Rounding:** all largest-remainder arithmetic is exact integers (remainders compared as `total*w % W` numerators). **Ties go to the earlier share:** the earlier bucket (<=15 first) inside a tier column (AC-198's 7/27/20/6 pins it), and the earlier tier (easy, medium, hard) for the general plan's tier counts (e.g. 150 at 30/45/25 = 45/67.5/37.5 -> 45/68/37). Zero-share cells stay 0 structurally: a zero-weight share has zero remainder and there are always more positive remainders than leftover units.
- **POL-007 / `with_split`:** unedited cells take their `prefill(count, new_split)` value; edited cells keep value and edited mark. `disagrees_with_split` is a derived property (column totals != new tier counts, which also covers the sum), not a stored flag, so it cannot be out of date. Note: in AC-202 itself the kept 15 happens to equal the 30/45/25 prefill of 21-25 x hard (37 over 0/5/10/10 -> 0/7/15/15), so that plan does not disagree. The warning is True whenever an edit really breaks a column (tested with an edit to 20).
- **Hand edits** may set any non-negative int, including on zero-share cells; INV-005 only requires split=100 and non-negative cells, so an edited matrix that is off the general plan is valid and reported, not refused.
- **`bucket_of`** raises `SizeOutOfRange` (existing `NonogramError`) for a side outside MIN_SIZE..MAX_SIZE. **`selection_cells`** reads `width`/`height`/`difficulty_tier` from the admin puzzle dicts; tier via `difficulty.tier_of_record` (never re-graded). It skips a record whose tier is None/unrecognised or whose extent is out of range (e.g. rows stored under the old 50 limit), because such a record has no tab and no plan cell. Both helpers return all 12 `(bucket, tier)` keys.
- `InvalidPlan` is a `ValueError` local to `book_plan.py` (no `errors.py` edit), so there are no SCOPE+ edits.
- **Tests:** `tests/test_book_plan.py` (AC-197..AC-202, AC-208..AC-210 bucket halves, G-1/G-2/G-3 checks), `tests/property/test_book_plan.py` (EC-023 over at least 15k cases against an independent Fraction-based sequential apportionment oracle, plus a POL-007 hand-edit survival property), `tests/property/test_longest_side_buckets.py` (EC-024, all 441 extents exhaustively). The PropertyTest ids are module-level `test_PropertyTest_...` functions so pytest collects them. A mutation that flips the tie-break to the later index fails AC-198 and EC-023.
- Full suite: 3730 passed, 26 skipped, 1 failed. The failure is `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`, which is about template content and does not touch this card's files.
- [Scope] src/nonogram/admin/book_plan.py, tests/property/test_book_plan.py, tests/property/test_longest_side_buckets.py, tests/test_book_plan.py
- [Build gate] impact underivable (python-pro, no pytest-testmon) — full suite
- [System contract] fresh lens matches card section (44 rules) — no refresh needed
- [Build gate] PASSED (full, 125s) — 3730 passed, 26 skipped, 1 failed: tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied — pre-existing, fails identically on main HEAD 89ed292, outside this card (no file in fix_scope); treated as baseline, not a card regression
- [Scope gate] cycle 1: in_scope — 4/4 files inside Touches; no G-4 guarded path touched
- [Review 1/3] Score: 9.0 — crit: 0, imp: 0
- [Review sync] 1 report(s) → meta/review/ (20260922T160048Z-CARD-119-cycle1.yml)
- [Review 1/3] Score: 9.0 ✓ threshold reached + no critical/important (4 Minor: F-001 G-3 test patches module not book_plan namespace; F-002 tier-level tie rule unstated (45/68/37); F-003 AC-197 untouched-plan assertion vacuous; F-004 with_edited_cell/non-iterable cells raise ValueError/TypeError not InvalidPlan; out-of-scope F-005 selection_cells silently skips unplaceable members → CARD-124/CARD-132)
- [Review 1/3] Step 8h coverage: 44/44 card rule ids have verdict lines (6 ✓, 38 ⚠ no_eligible_fact)
- [Inline fallback] none — all agents spawned as subagents
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, CON-011)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-197 ✓ TestBookPlan_RejectsSplitNotSummingTo100 PASSED (domain half; route half CARD-120) · AC-198 ✓ TestBookPlan_PrefillMatchesBook1MatrixAt150x40_40_20::test_matrix PASSED · AC-199 ✓ TestBookPlan_PrefillColumnTotalsMatchGeneralPlan PASSED · AC-200 ✓ TestBookPlan_ZeroShareCellsStayZero PASSED · AC-201 ✓ TestBookPlan_UneditedMatrixRederivedOnSplitChange PASSED · AC-202 ✓ TestBookPlan_HandEditedCellSurvivesSplitChange PASSED · AC-208/209/210 ✓ TestBookSelect_* PASSED (bucket-function half; rendered tabs CARD-122) · EC-023 ✓ test_PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan PASSED (≥15000 cases, ≥100 ties, Fraction oracle) · EC-024 ✓ test_PropertyTest_LongestSideBuckets_PartitionEveryExtent PASSED (exhaustive 441 extents) · G-1 ✓ DEFAULT_PLAN module constant, no audience param · G-2 ✓ AST import scan + test_every_import_in_the_package_points_inward PASSED, no schema files · G-3 ✓ tier only via tier_of_record, test_selection_never_regrades PASSED · G-4 ✓ diff lists 4 files, none under a4_golden; 0 lines removed from tests
- [Docs] skipped — changed dirs src/nonogram/admin/ (no README), tests/ (README is a Wave-1 admin suite guide, structure unchanged), tests/property/ (no README); no directory purpose changed
- [Commit] /commit auto: nothing further to commit (worktree clean outside meta/); card commit is 3cd891d feat(book-plan) — 4 files, +834. Status stays review until done merges.

- [Done] rebased onto main e1b5a12 (clean), full suite on the rebased tree: 1 failure only, test_size_configuration_applied — confirmed pre-existing by running it on 89ed292. Merged da6cf84 (--no-ff). Deferral scan: 0 hits. Trace: evidence tests already listed; FR-034 stays partial (CARD-120 open).
