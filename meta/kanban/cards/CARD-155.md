# CARD-155: One difficulty classifier — retire the prototype's 30/70 tiers

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/155-one-difficulty-classifier
**Worktree:** —
**Source:** CARD-138 handover and CARD-137 leftovers (backlog); code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** src/nonogram/analysis/strategy_counter.py, src/nonogram/analysis/__init__.py, src/nonogram/difficulty.py, tests/test_difficulty_tiers.py, tests/test_strategy_counter.py
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-10-02T00:00:00Z
**Closed:** 2026-10-02T12:45:56Z
**Actual:** —
**Merge commit:** 05a4ff6
**Blocked by:** —

## What to implement

ADR-0031/R1 says `difficulty.classify` is the only place a score becomes a tier.
`src/nonogram/analysis/strategy_counter.py:137-142` has a second
easy/medium/hard mapping on bare `30` and `70` literals, inside
`calculate_difficulty_from_strategies`.

The AST guard in `tests/test_difficulty_tiers.py` (:447, `_CUTOFF_NAMES`) only
recognises the cutoff **names** `EASY_MAX_SCORE` and `MEDIUM_MAX_SCORE`, so it
can't see a literal. It also doesn't know CARD-137's newer cutoff names
(`RUNG_OVERLAP_MAX_SCORE` and its siblings in `difficulty.py`).

Today nothing in production calls `calculate_difficulty_from_strategies`. It is
exported from `nonogram.analysis` and used only by `tests/test_strategy_counter.py`.
So the second classifier is dormant, not live. It's one import away from
becoming a second source of truth, and the guard wouldn't notice.

Also from CARD-137: `difficulty.py`'s docstring still has the retired "fourth
tier" section, with an example `classify(score, branch_nodes)` that raises
`TypeError`.

## What to do

1. Remove the tier output from `calculate_difficulty_from_strategies` (return the
   score only), or delete the prototype function if nothing needs it. Check
   `src/nonogram/__init__.py`'s package docstring, which mentions it.
   **Don't** route its score through `classify`: its 0-100 scale is not the
   solver score `classify` expects.
2. Add the CARD-137 cutoff names to `_CUTOFF_NAMES`, and extend the guard so a
   string literal `"Easy"`/`"Medium"`/`"Hard"` assigned outside `difficulty.py`
   fails it. Use a narrow rule: catching tier strings is enough, numeric literals
   are too noisy.
3. Remove the stale "fourth tier" section from `difficulty.py`'s docstring.

## Acceptance criteria

- **AC-1:** No module outside `difficulty.py` maps a score to a tier name.
  *test: the extended guard in tests/test_difficulty_tiers.py*
- **AC-2:** The guard fails if the old 30/70 mapping is put back in
  `strategy_counter.py` (checked by temporarily restoring it).
  *test: the extended guard*

## Guardrails

- G-1: No stored puzzle's tier changes, and `classify` and its cutoffs are untouched.
- G-2: The capability-module import guard in `tests/test_cli.py` stays green.

## System contract

_Assembled fresh by system_rules.py --card CARD-155 (card scope: touches) at start, 2026-10-02._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package data instead, and doing so is not a dependency change. (test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py. (test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer. (review-lens)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired. (test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit on one lineage, is a named constant beside it and is never a second bound; exhausting the counter raises GenerationAbandoned whichever kind of attempt came last. (test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled count is preserved and no cell outside the region changes. (test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, so a seed replays the same repair lineage everywhere. (review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of that range. (test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims that one does. (test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each rung is the fixed point of its technique, so the rung of a cell is a function of the clue set alone; a deeper solve of the same extent scores strictly higher, and the line-solvable corpus populates every score band. (test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from that same list — no second derivation, no second solver entry. The ladder's fixed points are phases of that one monotone forward solve — each continues from the board the previous left, the board is never reset and the search is never re-entered — so running a cheaper technique to exhaustion before a dearer one is not re-solving. (test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and branch_nodes, identical on every machine. (test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside the solver package; the solver never imports clues.py or any other capability module for the purpose (ADR-0007). (test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero per-rung histogram, an empty rung list). For uniquely-solvable clue sets, rung attribution is invariant under transposition and under line-visit order — a clue set and its transpose yield the same per-rung cell counts, the same rung list and the same score — and a change to the solver's iteration order may change how a fixed point is reached but never which cells belong to which rung. The invariance holds trivially for the non-unique ones too, since both orientations report nothing. (test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0031/R1 — Tier has exactly three members — easy, medium, hard — and every one has a score band. classify takes the score alone; no module derives a tier from branch_nodes. (test: TestTiers_ThreeBandsAndNoFourthTier)
- ADR-0031/R2 — A solve that branched is reported as the `guess` strategy (solver.STRATEGY_GUESS) in FR-029's strategies list, never as a tier. (test: TestTiers_BranchingIsAStrategyNotATier)
- ADR-0031/R3 — A stored difficulty_tier of "guess" reads back as Tier.HARD and is never rewritten by this decision; no migration runs and no production database is touched. (test: TestTiers_LegacyGuessRowReadsAsHard)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id). (review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percentage points of that cell's planned share. (test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's socket-reach half is discharged by more than a threshold visible only in requirements.yml. (test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form request target whose authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced mandatory constraint — a `check:` the system contract actually collects — so BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets Host from the request's target url, not from the page's origin. (test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019 restates the behaviour over the narrowed range. (test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an explanatory error rather than converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) / max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule "never silently discard more than half the user's picture". Retaining exactly 50% (a ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-014 — Wall-clock solve time — the solver's elapsed_seconds or any other reading of a clock — never enters the difficulty score or the tier decision made on it (NFR-007). The score is a pure function of the solve's structural signals and the puzzle's clues; the cooperative deadline (ADR-0011) bounds the solve but is not a scoring input. (test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never exceeds its configured maximum bound (NFR-002). (test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR-008). (test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement, changed only by an explicit move inside that level (FR-041). (test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm), each under its own band; pairing never changes the book order (FR-040). (test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 once it holds one longer than 20; no answer-key page holds answers of two levels (FR-042). (test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; ADR-0035 clarification). (test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is produced as a separate file (FR-043). (test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **ADR:** ADR-0031/R1 (one classifier)
- **Components:** COMP-006
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Why P3] Dormant code: no production caller today. It's cheap to remove now and
  easy to reintroduce by accident later.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +42 rules (card had no section) / −0
- [Implementation 2026-10-02, commit 3ca551a] Kept the prototype (CARD-053 kept it
  deliberately; DIFFICULTY_ENGINE.md and GENERATION_ALGORITHM.md still describe it) and
  removed only its tier output: `calculate_difficulty_from_strategies` now returns the
  0-100 `int` score. Not routed through `classify` (different scale). `__init__.py`
  re-export unchanged (name/shape kept); `src/nonogram/__init__.py` docstring still true,
  so not touched.
- [Guard] `tests/test_difficulty_tiers.py`: `_CUTOFF_NAMES` += `RUNG_OVERLAP_MAX_SCORE`,
  `RUNG_LINE_DP_MAX_SCORE`. New rule: an Assign/AnnAssign/AugAssign/Return whose value is
  a bare tier-name string (`easy`/`medium`/`hard`, case-insensitive) or an IfExp yielding
  one. Boundary (documented in the checker docstring, pinned by the "legitimate shapes"
  test): dict keys, call args/keyword defaults, and class-body assignments (enum members)
  are not offences. Scanned src/nonogram/** first: the only legitimate uses were
  admin `"medium"` size defaults (call args), `SIZE_PRESETS` / `plan_to_json` dict keys,
  `ProofPuzzle(tier="hard")` keywords, and `Recognizability.MEDIUM`/`Tier` enum members —
  none flagged. The checker was split into `_tier_deciding_offences_in_source` so it can
  run on a string. Dropped the unused `_SOLVE_FACT` constant (dead since CARD-098).
- [AC-2] Self-checking: `test_the_rule_catches_the_retired_prototype_mapping` runs the
  checker over the old mapping verbatim and expects 3 offences. Manual check also done:
  restored `strategy_counter.py` from HEAD~ and ran
  `test_no_module_but_difficulty_classifies_a_tier` -> FAILED with
  `['strategy_counter.py:139 binds a tier name', ':141 ...', ':143 ...']`; file restored.
- [difficulty.py] Module docstring only: "The fourth tier (ADR-0025)" section replaced by a
  short "One classifier (ADR-0031/R1)" section; Usage example `classify(score,
  branch_nodes)` -> `classify(score)`. `classify` code and all cutoff values untouched (G-1).
- SCOPE+ docs/REQUIREMENTS/DIFFICULTY_ENGINE.md — its usage example unpacked
  `score, tier = calculate_difficulty_from_strategies(...)`, false after this card.
  tests/test_card_050_quality_recognizability.py:306 comment is historical (describes
  deleted tests) and still true — left alone.
- Tests: test_difficulty_tiers + test_strategy_counter + test_cli + test_difficulty:
  200 passed (G-2 import guard green). Full suite not run (orchestrator's job).
- [Scope] docs/REQUIREMENTS/DIFFICULTY_ENGINE.md, src/nonogram/analysis/strategy_counter.py, src/nonogram/difficulty.py, tests/test_difficulty_tiers.py, tests/test_strategy_counter.py
- [Build gate] PASSED (full, 307s; baseline: exactly the 2 known pre-existing failures on main dc26103 — tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied and tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders; 5555 passed, 7 skipped, no other failure)
- [Scope gate] cycle 1: IN_SCOPE — 1/5 files outside Touches (docs/REQUIREMENTS/DIFFICULTY_ENGINE.md, recorded SCOPE+), analysis/ maps to no component, no guardrail hit
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (pre-adversarial; F-001 stale Tier.GUESS claims in difficulty.py :227-228/:243/:379)
- [Review sync] 1 report(s) → meta/review/
- [Adversarial] F-001 CONFIRMED — Tier has only EASY/MEDIUM/HARD (:274-276) and classify(score) takes one arg (:462), yet :227-228/:243/:379 still describe Tier.GUESS as live; skeptic also flagged :282 label docstring
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (post-adversarial)
- [Review 1/3] Step 8h coverage: 42/42 card rules have verdict lines (9 holds, 33 unchecked no_eligible_fact, 0 violated)
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [Mutation] deferred(cost) in cycle 1 — gating findings present
- [Fix 1] Review cycle 1: F-001 stale live-GUESS prose in difficulty.py fixed (RUNG comment,
  Tier summary, label, branch_nodes, parse_tier Raises "all four", EC-015 ref; docstrings only,
  AST-identical code, G-1) + paragraph-level regression guard; F-002 tier-name rule now also
  catches Tier.EASY/MEDIUM/HARD, mixed tuples, yield/yield from, lambda, walrus (vocabulary
  tuples exempt; 0 hits over src/nonogram), remaining gaps listed; F-003 doc header points at
  TIER_BANDS, 30/70 table marked historical; F-004 guard re-cites ADR-0031/R1. 206 targeted passed.
- [Fix 1] FIXED F-001, F-002, F-003, F-004; pre-gate: named tests 13/13 green; G-1 independently verified (difficulty.py AST minus docstrings identical to main)
- [Fix 1] declarations: 1 updated (F-002 doc _tier_deciding_offences_in_source/_is_tier_name), 0 confirmed, 3 none
- [Build gate] PASSED (full, 291s; baseline-only: the same 2 known pre-existing failures; 5562 passed, 7 skipped)
- [Scope gate] cycle 2: IN_SCOPE — same 5 files, no new paths
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0 (confirmation mode; F-001..F-004 ✓ resolved; Minor F-005 open: docstring regression test regex narrow)
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: 42/42 card rules have verdict lines (10 fresh holds, 32 carried(cycle 1, delta-clean), 0 violated)
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Mutation] cycle 2: 8 mutants, 8 killed, 0 survived (guard rule branches, vocabulary-tuple exemption, docstring regression test, prototype return); tree restored byte-identical
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0031/R1, ADR-0031/R3, ADR-0029/R1) — R1 skeptic did not re-run mutants M2/M8 (not defined in the verdict line); all other cited evidence re-derived
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — evidence: tests/test_difficulty_tiers.py::test_no_module_but_difficulty_classifies_a_tier PASSED (+ rule sub-tests, 15 passed); bounded: the guard catches only the shapes its docstring names
  AC-2 ✓ demonstrated — evidence: checker over dc26103 strategy_counter.py → ['strategy_counter.py:139/141/143 binds a tier name']; copy-aside restore made the live guard FAIL with the ADR-0031/R1 violation message; file restored (sha matched); test_the_rule_catches_the_retired_prototype_mapping PASSED
  G-1 ✓ demonstrated — evidence: difficulty.py AST (docstrings stripped) equal to dc26103; test_difficulty_tiers + test_difficulty + test_strategy_counter 113 passed; calculate_difficulty_from_strategies has no production caller (src/, scripts/, web/ grep)
  G-2 ✓ demonstrated — evidence: tests/test_cli.py 94 passed incl. test_every_import_in_the_package_points_inward; tests/test_cli.py unchanged in the diff
- [Docs] forge:readme over changed dirs (docs/REQUIREMENTS, src/nonogram, src/nonogram/analysis, tests): no structure change, existing READMEs current — no update
- [Inline fallback] docs step (forge:readme check) ran inline in the orchestrator; all other agents (implementation, 2 reviews, 1 adversarial skeptic, fix, 3 8h skeptics, AC check) were separate background subagents
- [Commit] success commit a93f3da on card/155-one-difficulty-classifier (on top of implementation 3ca551a); card stays in review until done
- [Merge note] main advanced to 0b759c8 (CARD-151 merged; scripts/ only, no overlap with this card's 5 files) — rebase at done
- [Merged] 2026-10-02 — 05a4ff6 into main (--no-ff). Rebased onto 0b759c8 (CARD-151) cleanly → tip 949c97c. Merge gate: full suite on the rebased tree under the lock (waited 79s, ran 317s); only the 2 baseline failures red on dc26103. Deferral scan: 0 hits. Actual left —: `Started` was stamped as a placeholder (00:00:00Z), not the real start time. No trace write-back: no FR on the card. Out-of-scope items captured to backlog.
