# CARD-137: Recalibrate the medium/hard cutoff so medium is reachable

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/137-recalibrate-medium-cutoff
**Worktree:** —
**Source:** owner, 2026-09-23 (5 medium puzzles in 300 on production)
**Idea:** —
**Wave:** 24
**Depends on:** —
**Touches:** src/nonogram/difficulty.py, tests/test_difficulty_tiers.py, tests/property/test_difficulty_calibration.py, docs/GENERATION_ALGORITHM.md
**Review score:** 8.0 (cycle 1/3)
**Started:** 2026-09-23T06:21:22Z
**Closed:** 2026-09-23T08:20:09Z
**Actual:** 0.2d
**Merge commit:** a949244
**Blocked by:** —

## What to implement

Medium is effectively unreachable. The tier is defined as "needed line deduction but
**no** probe at all", and in random grids a single probe anywhere promotes the whole
puzzle to hard — the owner measures 5 medium in 300 production puzzles; the local DB
shows 10 easy / 2 medium / 9 hard, with the hard scores spread 67..99.

That spread is the opening. `score = band_low(rung) + share * band_width(rung)` already
measures **how much** of the grid needed the hardest rung, so a 67 (one probe in an
otherwise line-solvable grid) and a 99 (probing nearly everywhere) are different puzzles
wearing one label. ADR-0005's two cutoff constants are the recalibration the module's own
docstring says is owed.

Owner decision (2026-09-23): keep three tiers; move the medium/hard boundary so **medium
= needed a little non-trivial work, hard = needed a lot**. Not a new signal, not a
removed tier.

**Step 1 — measure, then STOP.** Build a seeded corpus with the existing generator
across the supported size range and densities (no new solver entry point; score what the
one verifying solve already measured). Report, for candidate medium/hard cutoffs (at
least 75 / 80 / 85 / 90), the resulting easy / medium / hard shares overall and per
longest-side bucket (<=15, 16-20, 21-25, 26-30 — the book's own buckets, FR-034). Hand
that table back to the dispatcher and **do not pick the constant yourself**: the owner
chooses, against the 40/40/20 default plan.

**Step 2 — apply the chosen cutoff.** One constant in `src/nonogram/difficulty.py`
(`classify` stays the single classifier — the AST guard in tests/test_difficulty_tiers.py
must stay green). Update the module docstring's band arithmetic, the tier tests, and
`docs/GENERATION_ALGORITHM.md`. Regrading stored puzzles is the panel's existing
`POST /regrade` action — do not write a migration, and do not run it against the owner's
database.

## Acceptance criteria

- New: with the chosen cutoff, a seeded corpus of at least 200 line-solvable puzzles
  classifies into all three tiers, and medium holds at least 20% of them.
  test: TestDifficulty_MediumIsReachableOnASeededCorpus
- New: the tier of a puzzle is monotone in its score — no score classifies harder than a
  higher score (ADR-0029/R1 cross-rung monotonicity is unchanged).
  test: PropertyTest_Difficulty_TierIsMonotoneInScore
- Unchanged: `Tier.GUESS` is still keyed on `branch_nodes > 0`, never on a threshold
  (EC-015), and easy/medium/hard still contain only line-solvable puzzles.
  test: existing tests/test_difficulty_tiers.py (must stay green unmodified except for
  the cutoff figure itself)

## Guardrails

- G-1: `classify` remains the ONLY place a score is compared against the cutoffs; the
  AST walk in tests/test_difficulty_tiers.py must keep passing.
- G-2: No solver re-entry, no clock, no size, no density in the grade (NFR-007, CON-014,
  ADR-0029/R3). Scoring still reads only what the verifying solve measured.
- G-3: Do not edit `src/nonogram/export/**`, `src/nonogram/admin/**`, or
  `tests/fixtures/a4_golden/**`. The book pipeline reads the tier and must not care.
- G-4: No database migration, and no write to the owner's database.

## Architecture context

- **FR:** FR-026
- **NFR:** NFR-007
- **CON:** CON-014
- **ADR:** ADR-0005 (the two cutoff constants), ADR-0029 (strategy ladder), ADR-0031
  (three tiers), ADR-0025 (GUESS)
- **Components:** COMP-006
- **Trace:** meta/architecture/trace.yml

## System contract

Standing rules applicable to this card's scope (assembled fresh from the model at
start, 2026-09-23 — the card carried no section before).

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package data instead, and doing so is not a dependency change. (TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py. (test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer. (review-lens)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is never a second bound; exhausting the counter raises GenerationAbandoned whichever kind of attempt came last. (TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled count is preserved and no cell outside the region changes. (TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, so a seed replays the same repair lineage everywhere. (review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of that range. (TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims that one does. (TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each rung is the fixed point of its technique, so the rung of a cell is a function of the clue set alone; a deeper solve of the same extent scores strictly higher, and the line-solvable corpus populates every score band. (TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from that same list — no second derivation, no second solver entry. The ladder's fixed points are phases of that one monotone forward solve — each continues from the board the previous left, the board is never reset and the search is never re-entered — so running a cheaper technique to exhaustion before a dearer one is not re-solving. (TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and branch_nodes, identical on every machine. (PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside the solver package; the solver never imports clues.py or any other capability module for the purpose (ADR-0007). (test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero per-rung histogram, an empty rung list). For uniquely-solvable clue sets, rung attribution is invariant under transposition and under line-visit order — a clue set and its transpose yield the same per-rung cell counts, the same rung list and the same score — and a change to the solver's iteration order may change how a fixed point is reached but never which cells belong to which rung. The invariance holds trivially for the non-unique ones too, since both orientations report nothing. (PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0031/R1 — Tier has exactly three members — easy, medium, hard — and every one has a score band. classify takes the score alone; no module derives a tier from branch_nodes. (TestTiers_ThreeBandsAndNoFourthTier)
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (TestTiers_BranchingIsAStrategyNotATier)
- ADR-0031/R3 — A stored difficulty_tier of "guess" reads back as Tier.HARD and is never rewritten by this decision; no migration runs and no production database is touched. (TestTiers_LegacyGuessRowReadsAsHard)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's socket-reach half is discharged by more than a threshold visible only in requirements.yml. (TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form request target whose authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets Host from the request's target url, not from the page's origin. (PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019 restates the behaviour over the narrowed range. (PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an explanatory error rather than converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) / max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule "never silently discard more than half the user's picture". Retaining exactly 50% (a ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-014 — Wall-clock solve time — the solver's elapsed_seconds or any other reading of a clock — never enters the difficulty score or the tier decision made on it (NFR-007). The score is a pure function of the solve's structural signals and the puzzle's clues; the cooperative deadline (ADR-0011) bounds the solve but is not a scoring input. (PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level (FR-041). (PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes the book order (FR-040). (PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 once it holds one longer than 20; no answer-key page holds answers of two levels (FR-042). (PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; ADR-0035 clarification). (PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is produced as a separate file (FR-043). (PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Failure matrix

COMP-006 is a pure-function module: no I/O, no clock, no randomness, no module
state, no concurrency, no retries and no solver re-entry (ADR-0007, ADR-0029/R2,
CON-014). **It has no failure-bearing boundaries in the usual sense** — there is
no call that can time out, no resource that can be exhausted and no partial
write to undo. What it does have is a handful of *total-function* edges, and
those are declared here because "total" is a claim a reviewer should be able to
check rather than take on trust.

| operation | boundary / failure mode | declared behaviour | numeric bound |
|---|---|---|---|
| `classify(score)` | score below the scale (`< 0.0`) | returns `Tier.EASY`; never raises | any float `< SCORE_MIN` |
| `classify(score)` | score above the scale (`> 100.0`) | returns `Tier.HARD`; never raises | any float `> SCORE_MAX` |
| `classify(score)` | score exactly on a cutoff | the cutoff belongs to the band **below** it — `33.0` is Easy, `90.0` is Medium | exactly `EASY_MAX_SCORE`, `MEDIUM_MAX_SCORE` |
| `classify(score)` | `NaN` | unreachable: `score_difficulty` cannot produce one (integer counts, positive denominator, clamped share). If one were passed, both `<=` tests are false and the answer is `Tier.HARD` | — |
| `score_difficulty(signals)` | no rung settled a cell (`rung_cells` all zero — a clue set that is not a puzzle, ADR-0029/R5) | returns `SCORE_MIN`; the number means "nothing to grade", and INV-002 has discarded such a candidate before this is called | exactly `0.0` |
| `score_difficulty(signals)` | `total_cells <= 0` | returns `SCORE_MIN` rather than dividing | exactly `0.0` |
| `score_difficulty(signals)` | share outside `0..1` (a solver that over- or under-counted) | clamped into the rung's band, then into `SCORE_MIN..SCORE_MAX`; no exception | result always in `[0.0, 100.0]` |
| `hardest_rung(rung_cells)` | a rung name this module does not know | ignored, not raised — a fourth rung is a decision to take, not a crash to discover at the scorer | — |
| `parse_tier(text)` | text naming no tier | raises `UnsupportedDifficulty` (AC-021) — the one place this module refuses an input, because a user typed it and must be told | — |
| `tier_of_record(value)` | any stored text, including `None`, a blank, a non-string, or `"guess"` | total; never raises. `"guess"` reads as `Tier.HARD` (ADR-0031/R3), anything else unrecognised as `None` | — |

No row is a retry, a timeout or a rollback, because there is nothing here to
retry, time out or roll back.

## Worktree notes

- [Origin] Owner, 2026-09-23: "it's really difficult to generate a puzzle with medium
  difficulty — from 300 puzzles on prod only 5 are medium. Maybe we remove medium, or
  redefine it as only one of not trivial strategies applied". Removing the tier was
  rejected: the plan matrix, stored plans, the readiness gate, level order, dividers and
  the answer-key headings all assume three levels and are merged, and a two-level book
  drops the beginner-to-expert promise.
- [Architect] ADR-0005/ADR-0029/ADR-0031 need the new reading written back once the
  cutoff is chosen — queued in inputs/raw-requirements.md, not done in the worktree.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

- [Step 1] 2026-09-23: measured, cutoff NOT changed. `scripts/measure_difficulty_cutoff.py`
  (committed, b7b961f) builds a seeded corpus through `orchestrator.generate` (random mode,
  the batch path) and scores it through `difficulty.score_difficulty` on the verifying
  solve's signals — no solver re-entry, no new entry point. Seed 20260923, 12 sizes
  (10..30), densities 45..75 narrowing as the grid grows, 10 draws per cell: 1010 requests,
  1005 puzzles, 4 branched (excluded), **1001 graded in 199.6 s**. Generation failures 5
  (4 `GenerationAbandoned`, 1 `SolverTimeout`), all at density 45 on large grids.
  - Two structural findings the owner's decision turns on. (a) **The easy share is a
    density question, not a cutoff one**: every `simple_overlap`-only puzzle scores exactly
    33.0, and 698 of 1001 do, so no cutoff moves easy off 69.7% overall. Density is the
    dial: 100% easy at d65+, 98.3% at d60, 79.2% at d55, 25.8% at d50, 20.0% at d45.
    (b) **The probe band is bimodal** — 99 of the 303 non-trivial puzzles score above 94
    (probing settled almost the whole grid), so a cutoff below ~90 converts only the thin
    left shoulder of it.
  - Medium's share of the 303 non-trivial puzzles by cutoff: 66 -> 24.1%, 75 -> 36.3%,
    80 -> 40.3%, 85 -> 48.5%, 90 -> 57.4%, 93 -> 65.7%, 95 -> 71.3%. The plan's 40/20
    medium:hard is 2:1, which lands at ~93.
  - [Owner decision] 2026-09-23: **`MEDIUM_MAX_SCORE = 90.0`**. Medium therefore means
    "the probe rung settled at most (90-66)/34 = 70.6% of the grid"; hard means line logic
    got essentially nowhere. Decisive numbers: medium goes from 24.1% to 57.4% of the 303
    non-trivial puzzles; in the 16-20 bucket at the batch density it goes 18.3% -> 45.8%
    and overtakes hard for the first time; the probe band's mass (99 of 303 above score 94)
    stays Hard, which is what keeps the name honest.
  - [Handover to step 2] The new AC's floor ("medium holds at least 20% of a seeded corpus
    of >= 200 line-solvable puzzles") is **not reachable below cutoff ~94 on a
    density-uniform corpus** — 85 gives 14.7%, 90 gives 17.4%. It is comfortably reachable
    on a corpus built in the density band the batch generator actually uses (d45-52:
    80 -> 23.9%, 85 -> 30.2%, 90 -> 36.9%). The step-2 corpus must be built there, or the
    AC must be restated against the non-trivial subset.

- [Step 2] 2026-09-23: **cutoff applied — `difficulty.MEDIUM_MAX_SCORE = 90.0`**,
  `EASY_MAX_SCORE` unchanged at 33.0. That one constant is the whole production change;
  everything else is the two tables parting company, the tests that encoded their old
  identity, and the docs. The full suite is green (minus the one known pre-existing
  failure, `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
  red before this card). No migration, no database touched, no `src/nonogram/admin/**`
  or `src/nonogram/export/**` change, golden-A4 tripwire untouched.

  - STRUCTURE: **`RUNG_BANDS` gets its own literal table; it is no longer zipped from
    `TIER_BANDS`** — and two named constants, `RUNG_OVERLAP_MAX_SCORE = 33.0` and
    `RUNG_LINE_DP_MAX_SCORE = 66.0`, are its source of truth. Why: the zip *encoded* the
    claim ADR-0029's History made and this card retires — that a tier is a rung. Keeping
    it would mean the next retune of a *tier* cutoff silently re-scaled every *score*,
    which is exactly the "no stored grade moves" guarantee this card sells. The two
    tables are now two facts: `RUNG_BANDS` turns a solve into a number (ADR-0029, and
    untouched here), `TIER_BANDS` files a number under a tier (ADR-0005, and the only
    thing that moved). `_BAND_TIERS` existed only to drive the zip and is gone.
  - STRUCTURE: **the named rung constants are deliberately NOT added to the ast guard's
    `_CUTOFF_NAMES`.** The guard (ADR-0025/R2) exists to keep exactly one *tier*
    classifier; comparing a score against a rung edge decides a rung, not a tier, so
    adding them would broaden the rule rather than keep it. The guard is unchanged and
    unweakened, and no module under `src/nonogram/` compares a score to anything.
  - STRUCTURE: **Easy's cutoff stays coincident with a rung boundary; Medium's
    deliberately does not.** `EASY_MAX_SCORE == 33.0 == RUNG_OVERLAP_MAX_SCORE` is what
    keeps "Easy" meaning exactly "the overlap rule finished it" and keeps a full-share
    bottom rung scoring 33.0 (ADR-0029, History 2026-09-13 — the correction that stopped
    the Easy band being empty). `MEDIUM_MAX_SCORE = 90.0` coincides with nothing: it cuts
    the probe rung at `(90-66)/34` = 70.6% of the grid. A tier boundary sitting *inside*
    a rung's band is what makes Medium reachable, and that sentence is now in the module
    docstring, `classify`'s docstring, `Tier.band`'s and §7 of the algorithm doc.
  - STRUCTURE: the new AC corpus is built through `random_grid.generate` + `compute_clues`
    + `solve` (the `test_difficulty_ladder.py::_real_puzzles` precedent), **not** through
    `orchestrator.generate`: step 1's 1001-puzzle orchestrator sweep took 200 s, and the
    suite gets the same grades for 12 s. It is cached on its seed with `functools.cache`
    so three tests share one build.

  - **Measured tier distribution of the new AC corpus** (seed 20260923, densities 45..52
    across 10x10..30x30, 315 line-solvable puzzles, 12.2 s):

    | rung | n | share | score range | tier at 66 | tier at 90 |
    |---|---:|---:|---|---|---|
    | `simple_overlap` | 202 | 64.1% | 33.000 exactly | Easy | Easy |
    | `line_dp` | 49 | 15.6% | 34.12..63.94 | Medium | Medium |
    | `probe_contradiction` | 64 | 20.3% | 66.68..98.83 | Hard | Medium (42) / Hard (22) |

    Tier split **64.1 / 15.6 / 20.3 -> 64.1 / 28.9 / 7.0**. Medium clears the AC's 20%
    floor with margin and would have failed it at the old cutoff (15.6%). The corpus is
    stable across seeds: 7 -> 30.5% medium, 991 -> 31.0%.
  - The direct path and the orchestrator path agree. 160 puzzles built through
    `orchestrator.generate` in the same band came back 64.4 / 35.0 / 0.6 against the
    corpus's 64.1 / 28.9 / 7.0 — the same grading, a different *keep* rule (the
    orchestrator repairs a non-unique grid under POL-006 instead of dropping it). Both
    differ from step 1's figure for the band (31.2 / 36.9 / 31.9) for a reason recorded
    in the test's docstring rather than tuned away: step 1 issued equal *requests* per
    (extent, density) cell, so its large extents counted as heavily as its small ones,
    while a corpus of direct draws is weighted by uniqueness yield and is therefore
    dominated by small — overwhelmingly Easy — grids. Neither weighting is wrong; the AC
    asks only that Medium be reachable on real puzzles in the production band.

  - SCOPE+ `tests/test_difficulty.py` — two tests asserted the rung table *is* the tier
    table. `test_the_three_rung_bands_are_adr_0005s_cutoffs_and_tile_the_scale` now reads
    the ladder's own two edge constants (it deliberately avoids the literals 33/66, which
    is why it needed named constants at all).
    `test_every_rung_band_is_the_band_of_the_tier_that_rung_means` is renamed
    `test_the_rung_table_and_the_tier_table_agree_only_at_the_easy_cutoff` and asserts the
    new relationship — same job (pin how the two tables relate), opposite expectation,
    which is the change this card *is*.
  - SCOPE+ `tests/property/test_difficulty_ladder.py` —
    `test_every_score_lands_on_the_scale_and_in_its_rungs_own_band` asserted
    `classify(score) is (EASY, MEDIUM, HARD)[rung]`. It now asserts containment in
    `RUNG_BANDS`, which is what its own name and docstring always claimed; the tier half
    of it was the rung==tier identity in disguise.
  - SCOPE+ `tests/test_resample.py` — AC-123's clock-dilation test pinned `resample
    .attempts == 3` / `regenerate.attempts == 8` for seed 1. Medium is a wider band now,
    so seed 1 is satisfied by its first candidate and the run stopped exercising POL-004
    at all. `_AC123_REQUEST`'s seed moves 1 -> 4, which restores the three resample rounds
    the constant's own docstring says it exists to produce (13 regenerate attempts). The
    claim under test — a dilated clock changes neither the grid nor the counts — is
    untouched.
  - SCOPE+ `tests/test_export_pdf.py` — `test_the_pdf_is_named_after_the_puzzle_and_its_tier`
    pinned ADR-0016's `cat-hard.pdf` example at `score=80.0`, which is a Medium score now.
    Lifted to a named `HARD_SCORE = 95.0` beside the existing `MEDIUM_SCORE`, for the
    reason that constant already gives: the claim is about the filename, so the figure
    moves with the band.
  - Not changed, deliberately: `scripts/measure_difficulty_cutoff.py` gained no
    `--density-band` flag. It already unions the in-force cutoff into its candidate set,
    so it reports correctly at 90.0 with no edit, and a density flag would not make an
    image-mode follow-up cheaper — image mode does not take a density. No change beat a
    speculative one (minimalism, §9).
  - `ruff`/`mypy` were not run: neither is configured in this repo (`pyproject.toml` has
    no config, the venv has neither installed) — see CLAUDE.md, "There is no
    lint/format/type-check tooling configured yet."
  - [Architect, still owed] ADR-0005 (History: the cutoff it was owed is now chosen, and
    the medium/hard edge no longer sits on a rung boundary), ADR-0029 (its History entry
    "ADR-0005's cutoffs now land exactly on rung boundaries" is half false from this date)
    and ADR-0031 need the new reading written back. Queued in
    `inputs/raw-requirements.md` per the [Architect] note above; not done in the worktree.

- [Scope] docs/GENERATION_ALGORITHM.md, scripts/measure_difficulty_cutoff.py, src/nonogram/difficulty.py, tests/property/test_difficulty_calibration.py, tests/property/test_difficulty_ladder.py, tests/test_difficulty.py, tests/test_difficulty_tiers.py, tests/test_export_pdf.py, tests/test_resample.py
- [Build gate] PASSED (full, 218s) — 4507 passed, 26 skipped, 1 deselected (the known
  pre-existing `test_size_configuration_applied`). Run under the repo full-suite lock with
  a private --basetemp (sibling worktrees run suites concurrently).
- [Scope gate] ⚠ grown: 5 of 9 changed files outside Touches —
  scripts/measure_difficulty_cutoff.py (new, step 1's committed measurement record),
  tests/property/test_difficulty_ladder.py, tests/test_difficulty.py,
  tests/test_export_pdf.py, tests/test_resample.py (all expectation-only, each recorded as
  SCOPE+ by the implementation agent). comp_spread 0 (only COMP-006 touched); no sibling
  card poached; no guardrail glob hit (src/nonogram/export/**, src/nonogram/admin/**,
  tests/fixtures/a4_golden/** all untouched).
- [Review 1/3] Score: 8.0 — crit: 0, imp: 2. Step 8h: 42 rules checked, 12 ✓ holds,
  30 ⚠ unchecked (29 no_eligible_fact, 1 check_ref_missing — ADR-0029/R2's named test
  `TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve` does not exist under tests/,
  a standing model gap already recorded by the CARD-116/121 reviews, not this card's),
  0 ✗ violated. Guardrails G-1..G-4 and CARD-113's golden-A4 tripwire all verified ✓.
  The load-bearing claim was verified directly against the code, not the docstring: the
  reviewer imported main's and HEAD's difficulty.py side by side — RUNG_BANDS is
  bit-identical and 200,000 synthetic signal records produced 0 differing scores, so no
  stored grade moves and only (66.0, 90.0] changes hands. Not a UI card — Step 8g N/A.
- [Review sync] 1 report → meta/review/
- [Adversarial] dropped false positive: "Hard's yield collapse is measured but its
  consequence is unstated" — REFUTED. The skeptic found both halves already in the doc the
  finding cites: docs/GENERATION_ALGORITHM.md:466-470 prints the 64.1/15.6/20.3 ->
  64.1/28.9/7.0 split and the per-rung re-filing, :477-479 gives the bimodality that keeps
  the mass Hard, and §8.3 at :617 and :644 states the effect on a request. It also refuted
  the finding's premise: the admin batch passes difficulty_tier=None
  (admin/batch_generator.py:438) and FR-034's book plan fills its Hard quota by SELECTING
  already-graded stored puzzles, so no retry budget is raced there at all.
- [Adversarial] dropped false positive: "the declared architect writeback was never
  queued" — REFUTED. The delta IS queued and committed on main:
  meta/architecture/inputs/raw-requirements.md:259-261, "## Delta 2026-09-23 (a) —
  difficulty recalibration (owner)", landed in f1b32f8. The reviewer greped the WORKTREE
  copy of meta/, which is stale by project convention (meta/ is never committed from a
  worktree), so the entry was invisible to it. The card's own claim that the writeback is
  queued is accurate.
- [Review 1/3] after adversarial verification: crit: 0, imp: 0 (both Important findings
  refuted) — severity gate open at score 8.0.
- [8h spot-check] ADR-0029/R1 reproduced — an independent skeptic re-derived the verdict
  with its own generator and its own seed (20260923): 200,000 synthetic signal records
  including the degenerate ones (total_cells == 0, all-zero histograms, over-counting
  histograms, a 1% injection of an unknown rung name) gave **0 differing score floats**
  compared by == and by float.hex(), while 43,711 records changed TIER label. It also
  settled the rule's last clause ("the line-solvable corpus populates every score band")
  under both readings: on the real 292-puzzle corpus, rung bands 258/8/26 and tier bands
  258/27/7 — all three populated either way, and the band-coverage test is byte-identical
  to main and green.
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0029/R1, ADR-0031/R1, ADR-0031/R3);
  G-1 re-derived as well. The second skeptic wrote its own ast.walk over
  src/nonogram/**/*.py: exactly two comparisons against a cutoff name exist in the whole
  package, both inside `classify` (difficulty.py:511, :513), zero bare-literal comparisons
  against 33/66/90 anywhere, and zero references to the two new rung constants outside
  difficulty.py. `_CUTOFF_NAMES` is byte-identical to main; tests/test_difficulty_tiers.py
  has exactly three hunks, two docstring-only and one changing the single assertion
  `MEDIUM_MAX_SCORE == 66.0` -> `== 90.0` — no assertion removed, retargeted or weakened.
- [Handover] Minor, not fixed on this card and worth a follow-up decision: the new
  `RUNG_OVERLAP_MAX_SCORE = 33.0` is an importable alias of `EASY_MAX_SCORE` that the AST
  guard's `_CUTOFF_NAMES` does not cover, so a future module could decide the easy/not-easy
  boundary through it and stay green. The skeptic judged it not a violation (the guard never
  caught bare literals either, and the other new constant `RUNG_LINE_DP_MAX_SCORE = 66.0` is
  no longer any tier cutoff at all, so the change removes more alias risk than it adds), and
  the omission is deliberate and documented in the STRUCTURE notes. Adding both names to
  `_CUTOFF_NAMES` would cost nothing today.
- [Review note] The cycle-1 report's coverage line says "tests/test_difficulty_tiers.py,
  262 passed"; that file holds 56 tests, so 262 is another run's count. Bookkeeping only —
  no verdict depends on it.
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — TestDifficulty_MediumIsReachableOnASeededCorpus /
    tests/property/test_difficulty_calibration.py::test_medium_is_reachable_on_a_seeded_corpus
    PASSED; independently re-measured by the gate agent: 315 line-solvable puzzles (floor
    `_MIN_CORPUS = 200` asserted in-test at :237), easy 202 / medium 91 / hard 22 — all
    three tiers non-empty, medium 28.9% >= 20%. Counterfactual at the old 66.0 cutoff on
    the SAME corpus: 15.6% — the criterion genuinely discriminates. Corpus densities
    {45..52}, asserted mechanically by
    `test_the_corpus_really_is_drawn_in_the_batch_generators_density_band` and stated in
    the test docstring, as the owner directed.
  AC-2 ✓ demonstrated — PropertyTest_Difficulty_TierIsMonotoneInScore /
    ::test_tier_is_monotone_in_score[137,1370,13700] + ::_on_real_solves PASSED; genuinely
    multi-case (3 seeds x 600 seeded scores spanning -10..110 plus every band edge ±1e-9,
    `assert len(scores) >= 600` in-test, plus the 315 real solves), cross-checked against
    an independent interval lookup rather than against `classify` itself.
  AC-3 ✓ demonstrated — SURVIVING-FACT reading (ADR-0031 retired Tier.GUESS, so the enum
    member the criterion names no longer exists; what was verified is that no module keys
    a TIER off branch_nodes, that branching is reported as the `guess` STRATEGY, and that
    easy/medium/hard hold only line-solvable puzzles). tests/test_difficulty_tiers.py 56
    passed; both `classify(` call sites (orchestrator.py:1157, admin/regrade.py:351) pass
    the score alone; branch_nodes is read only to append the strategy. Second half
    mechanical: the file's diff is 3 hunks, two docstring-only, one changing the single
    assertion `MEDIUM_MAX_SCORE == 66.0` -> `== 90.0` plus a test rename.
  G-1 ✓ demonstrated — the three guard tests PASSED and the guard source is untouched; an
    independent ast walk of all 57 src/nonogram/**/*.py files found exactly two comparisons
    against a cutoff constant or the literals 33/66/90, both inside `classify`
    (difficulty.py:511, :513), and zero references to the two new rung constants outside
    difficulty.py.
  G-2 ✓ demonstrated — PropertyTest_ScoreDifficulty_IndependentOfElapsedTime PASSED;
    SolverSignals declares only total_cells/branch_nodes/rung_cells (no clock, no size, no
    density); difficulty.py imports nothing but stdlib + nonogram.errors, so solver
    re-entry is unreachable rather than merely absent.
  G-3 ✓ demonstrated — `git diff --name-only main...HEAD` and `git status --porcelain`
    both filtered through the three guarded globs: no match in either. CARD-113's golden
    tripwire (tests/test_export_a4_golden.py + tests/property/test_cli_exports_byte_identity.py)
    66 passed, fixtures byte-unchanged.
  G-4 ✓ demonstrated — no migration file, no sqlite/connect/nonogram_admin anywhere in the
    diff, nothing rewriting a stored tier. The owner's DB was never opened: verified by
    `stat` only (mtime Sep 22 20:36, before the card started).
- [Build gate] PASSED (full, 261s) — 4507 passed, 26 skipped, 1 deselected. Re-run after the
  two post-review edits (orchestrator docstring, scripts/README.md).
- SCOPE+ `src/nonogram/orchestrator.py` — docstring only, one re-derived example.
  `_band_text`'s docstring opened with the literal example "Hard band (66-100) of the
  0-100 difficulty scale"; the function reads the figures off `Tier.band`, so its OUTPUT
  followed the cutoff on its own (verified: it now returns "Hard band (90-100)") while
  the example in the docstring did not. A declaration this card falsified, corrected in
  this card rather than left for a later reader. No code change, no behaviour change.
- [Docs] `scripts/README.md` — the directory gained `measure_difficulty_cutoff.py` and the
  README listed only the three admin shell scripts. Added a "Measurement scripts" section
  with what it measures, how to run it and why it is committed. Additive; nothing existing
  reordered or reworded. `tests/README.md` deliberately NOT touched: it is a legacy
  "Admin Panel Test Suite - Wave 1" document that does not enumerate `tests/property/` at
  all, so an entry for the new calibration test would be out of place rather than owed.
  `docs/`, `src/nonogram/` and `tests/property/` carry no README.
- [Commit] 7057837 — the success commit. Three commits on the branch:
  b7b961f (step 1, the measurement script), 09dc714 (step 2, the cutoff + tests + docs),
  7057837 (the two declarations the new cutoff falsified). meta/ deliberately not
  committed from the worktree.


- [Done] owner chose MEDIUM_MAX_SCORE = 90.0 (2026-09-23). Rebased onto main db74b04, full suite on the rebased tree with a private --basetemp: only the pre-existing e2e failure. Merged a949244 (--no-ff). Deferral scan: 0 hits. SCOPE+ 5 test files (expectation-only) + the step-1 script + an orchestrator docstring this card falsified. Regrade NOT run against the owner's DB (G-4) — the owner runs it from the panel.
