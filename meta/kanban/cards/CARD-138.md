# CARD-138: Batch generation can ask for a difficulty

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/138-batch-difficulty-target
**Worktree:** ../PythonProject4-CARD-138
**Source:** owner, 2026-09-23 (after CARD-137's regrade: 37 mediums in ~300, a 150-puzzle book at 40/40/20 needs 60)
**Idea:** —
**Wave:** 25
**Depends on:** CARD-137
**Touches:** src/nonogram/admin/batch_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/batch_create.html, tests/test_batch_difficulty_target.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-23
**Closed:** 2026-09-23
**Actual:** 0.5d
**Merge commit:** cc64540
**Blocked by:** —

## What to implement

The engine can already generate to a tier: `GenerationRequest.difficulty` drives the
resample loop (a unique puzzle whose grade misses the requested tier is discarded and
the source is asked again, POL-004), and the CLI exposes it as `--difficulty`. The admin
batch generator hard-codes the opposite — `batch_generator.py:438`
`difficulty_tier=None,  # Accept any difficulty` — so the only way to fill a book's
medium quota is to generate at random and hope.

After CARD-137 moved the medium/hard cutoff to 90, medium is a wide band rather than a
sliver, so a targeted resample now terminates quickly. Before it, this field would have
been a trap.

Add the field:

1. **`generate_batch.html`** gains a difficulty select — Any (default, today's
   behaviour) / Easy / Medium / Hard — beside the existing size and count fields, using
   the existing form controls and tokens (no new CSS).
2. **The route** passes the chosen tier through to `batch_generator`, which passes it to
   `orchestrator.generate_batch(difficulty_tier=...)` instead of the hard-coded `None`.
   Parse the tier through `difficulty.parse_tier` — do not re-implement the mapping, and
   do not compare scores against cutoffs anywhere (ADR-0031/R1: `classify` is the only
   classifier).
3. **Report honestly when it gives up.** The resample loop is bounded; a batch that
   asked for 40 mediums and made 31 must say so in the batch note, the way CARD-093's
   early-stop note already does — not silently return fewer, and not fail the batch.
4. **Keep the existing stop rules.** `GenerationAbandoned` / `SolverTimeout` handling
   (batch_generator.py:433-445) is unchanged: work already made is kept and the batch
   completes with a note.

Out of scope: per-tier counts in one batch ("20 easy + 20 medium"), any change to the
resample bound itself, and image-mode generation (image mode takes no density and its
difficulty distribution is a separate question, already on the backlog).

## Acceptance criteria

- New: a batch requested as Medium returns only puzzles whose stored tier is medium, or
  fewer than requested with a note saying how many were made.
  test: TestBatchDifficulty_MediumBatchReturnsOnlyMediums
- New: a batch requested as Any behaves exactly as today (no tier filtering).
  test: TestBatchDifficulty_AnyIsUnchanged
- New: the generate form offers the four choices and defaults to Any.
  test: TestBatchDifficulty_FormOffersTheChoices
- New: when the loop cannot fill the count, the batch completes with the puzzles it made
  and the note names the shortfall.
  test: TestBatchDifficulty_ShortfallIsReportedNotSilent

## Guardrails

- G-1: `classify` stays the only place a score meets the cutoffs (the AST guard in
  tests/test_difficulty_tiers.py).
- G-2: Do not change the resample bound, `GenerationAbandoned`/`SolverTimeout` handling,
  or CARD-093's early-stop behaviour.
- G-3: Do not edit `src/nonogram/export/**`, `tests/fixtures/a4_golden/**`, or any book
  module (`book_*.py`) — this card is about generation, not assembly.
- G-4: The CLI's `--difficulty` path and its output stay byte-identical (CON-019).

## Architecture context

- **FR:** FR-008 (requested tier), FR-026
- **ADR:** ADR-0031 (three tiers), ADR-0029 (ladder), ADR-0005/CARD-137 (the cutoff)
- **Components:** COMP-002, COMP-009
- **Trace:** meta/architecture/trace.yml

## System contract

Standing rules applicable to this card's scope (assembled fresh from the model at
start, 2026-09-23 — the card carried no section before).

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package data instead, and doing so is not a dependency change. (TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py. (test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer. (review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX ratio — not from its as-decoded file ratio — is refused rather than cropped. The bounding box is computed and judged before any crop is applied, so a refused request is still refused before any cropping runs. (TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, clamped to MIN_SIZE at the bottom only and never at the top. A source whose ratio exceeds N/5 is refused with a message naming the smallest N that would accommodate it, never silently clamped. (PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
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
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with NotUniquelySolvable, any grid whose clues do not have exactly one solution — including one whose solve timed out or could not be attempted. No caller's assurance substitutes for that check, and no admin path writes a puzzle row by another route. (TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left operand of an order comparison, and renders as "N/A" wherever a score would be shown — templates, API responses and the book PDF alike, the book omitting the /100 denominator that a non-number does not take. recognizability carries the same rule in its own vocabulary. (TestUnmeasuredQuality_SurvivesTheFilter)
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
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens it, and no module under src/nonogram/admin/ names another bind address in code. Restates NFR-003 for the second inbound HTTP surface, which CON-009 does not reach. (TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the default), it refuses any request whose Host header does not name this machine — a bare authority, no userinfo, path, query or fragment, a port absent or all digits, and a host component in {localhost, 127.0.0.1, ::1} — and refuses a request carrying no Host header at all. With it set, it refuses any request whose Host is not exactly that hostname (a loopback Host included), any request not carrying the configured credential, and any request the browser marks as started by another site (a Sec-Fetch-Site outside {same-origin, none}, or an Origin whose host is not that hostname). The wrong-host refusal is indistinguishable from "no such page" in both modes, so it tells a scanner nothing. Holds however the socket was bound, including when the bind was widened by an option outside this package's control. (TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
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

## Worktree notes

- [Origin] Owner, 2026-09-23. CARD-137's regrade took production from 7 to 37 mediums in
  ~300 puzzles (~12%); a 150-puzzle book at 40/40/20 needs 60, so ~23 are missing and
  random generation fills that slowly. The owner chose this over moving the cutoff again
  (93 would call a 79%-probed grid "medium") and over editing the plan to match supply.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)
- [System contract] the card carried no section — assembled fresh from the model
  (system_rules.py --card CARD-138 --root meta/architecture): 47 rules, written onto
  the card as `## System contract` so the review judges against what the card records.

- [Implementation] 2026-09-23. The field is plumbed through, end to end, and nothing new
  was built to carry it. Four files:

  - `src/nonogram/admin/batch_generator.py` — `create_batch` takes
    `difficulty_tier: Optional[str] = None` and resolves it through
    `difficulty.parse_tier` beside the other parameter checks, so an unsupported tier is
    refused **before** a batch row or job exists and the admin owns no easy/medium/hard
    vocabulary of its own (G-1: no score is compared to anything under `admin/`). The
    canonical `.value` travels on, so the orchestrator's second parse cannot disagree
    with the first. `_generate_random_batch(batch_id, difficulty_tier=None)` takes it as
    an **argument**, not off the `batches` row: the table has no column for it and
    inventing one would mean a migration this card is not allowed to run. The hard-coded
    `difficulty_tier=None,  # Accept any difficulty` at the `generate_batch` call is now
    that argument.
  - Reporting lives where the card said it should — the existing `notes`/`refusal_note`
    block, same voice, no second mechanism. A targeted batch's abandonment sentence is a
    **separate branch** rather than a rewrite: "N of M candidates could not be made
    *medium* within the retry budget … The shortfall is the tier, not uniqueness: a
    candidate that came out uniquely solvable but graded outside medium is discarded and
    redrawn (POL-004) … Re-run for the rest, or ask for Any difficulty if you need the
    count more than the tier." The untargeted sentence is byte-identical to what it was
    (pinned by a test that asserts the whole string). CARD-093's early-stop note gains
    the tier in its count ("5 of 20 **medium** puzzles made") plus one sentence saying
    the request now includes the tier; the stop rule, the resample bound and the
    `GenerationAbandoned`/`SolverTimeout` handling are untouched (G-2).
  - `src/nonogram/admin/app.py` — three strictly local, additive edits in the
    `POST /batch/create` route: read `difficulty` off the form and convert empty/absent
    to `None` at that boundary (the one place "Any" is spelled), pass it to
    `create_batch`, and widen the existing `except ValueError` to
    `(ValueError, UnsupportedDifficulty)` so a bad tier is the same flash an out-of-range
    count is, never a 500. Plus `UnsupportedDifficulty` in the `nonogram.errors` import
    and two kwargs on `_render_batch_step_one`'s `render_template`
    (`difficulty_tiers=[tier.value for tier in Tier]`, read off the enum, and
    `default_count`). No reformatting, no reordering — CARD-118/CARD-130 also edit this
    file.
  - `src/nonogram/admin/templates/batch_create.html` — see SCOPE+ below.

- SCOPE+ `src/nonogram/admin/templates/batch_create.html` (instead of the card's
  `generate_batch.html`) — **the card's Touches field names the wrong template, and the
  form it describes did not exist.** `generate_batch.html` is the *image* flow's step 3
  (a confirmation checkbox over a table of pictures; it posts to
  `/batch/generate-puzzles`, which builds an `source="images"` batch and never reaches
  `_generate_random_batch`), and image mode is out of scope by this card's own words.
  There were no "existing size and count fields" anywhere: the random path is
  `POST /batch/create`, which has always read `count`/`sizes`/`theme`/`source` off a
  form — but **nothing on the panel ever sent them**, so a random batch could only be
  asked for from a script or a test. `DEFAULT_BATCH_COUNT`'s own docstring ("what the
  create-batch form asks for when the operator does not say") describes a form that was
  never built. So the difficulty select went where it can work: a compact "Or generate
  random puzzles" card added to `batch_create.html` (the page `GET /batch/create`
  renders), with How many / Size / **Difficulty** and a hidden `source=random`, using the
  existing Bootstrap controls and tokens — no new CSS, no new route, no new component.
  Size and count bounds come from `MIN_SIZE`/`MAX_SIZE`/`MAX_BATCH_COUNT` (already Jinja
  globals), never literals. Judged a missing *view of an existing route* rather than a
  new component, so not a `[BLOCKER] decomposition defect` — but the Touches field is
  wrong and a later card planning UI work here should not trust it.

- [Tests] `tests/test_batch_difficulty_target.py`, 23 tests, **0.6 s** for the file. The
  four named classes are all present and green:
  `TestBatchDifficulty_MediumBatchReturnsOnlyMediums` (5),
  `TestBatchDifficulty_AnyIsUnchanged` (5), `TestBatchDifficulty_FormOffersTheChoices` (5),
  `TestBatchDifficulty_ShortfallIsReportedNotSilent` (6), plus the DB-mode check.
  - **The source is stubbed, on purpose**, and the file's docstring says so and why.
    `generate_batch` makes its own unseeded `random.Random` and every candidate draws its
    own seed, so a real targeted batch is not reproducible — measured in this worktree, a
    real `count=10, sizes=[12], difficulty_tier="medium"` batch came back **9 of 10**
    (one candidate genuinely exhausted its resamples) in 0.3 s. That is the correct
    product behaviour and an intolerable test: the count depends on luck. So
    `orchestrator.generate` is replaced by `_ScriptedSource`, which stands in for "draw a
    grid, solve it, grade it" with a *seeded* `random.Random(138)` over CARD-137's
    measured tier shares (64/29/7) — stdlib only, no hypothesis.
  - What is **not** stubbed is the keep-or-resample decision: the stub builds a real
    `Puzzle` on the real `GenerationRequest`, resolves `requested_tier` through
    `difficulty.parse_tier` exactly as `orchestrator.generate` does, and asks
    `record_difficulty` — POL-004's own predicate — whether to keep the draw. A tier that
    failed to reach the request shows up as puzzles of the wrong grade, not as a mocked
    assertion. Scores come from `Tier.band`'s midpoint, so the tests state no cutoff of
    their own (G-1) and survive the next recalibration.
  - Shortfall tests script outcomes directly (the `tests/test_batch_keeps_partial_work.py`
    precedent) because there the premise is an outcome, not the grades behind it.
  - Smoke-checked for real outside the suite (not a test): `medium` 10/10 at 20x20 in
    0.8 s, `None` 10/10 mixed in 0.5 s, `hard` 5/10 in 2.6 s with the shortfall note.
    Hard is the expensive tier — the note is what tells the owner.

- [Build gate] Full suite PASSED (exit 0, ~230 s, private `--basetemp=/tmp/pytest-card138`)
  with only the known pre-existing deselect,
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
  (red before this card). One earlier run showed
  `tests/test_web_upload.py::…::test_the_page_reports_success_and_names_the_written_file`
  red — it globs the *shared* system temp dir for `nonogram-upload-*`, so a sibling
  worktree's concurrent suite trips it; green on both re-runs. `tests/test_difficulty_tiers.py`
  (the AST guard), `tests/test_cli.py` (the import-layering guard) and CARD-113's golden-A4
  tripwire are green and unmodified. `ruff`/`mypy` not run: neither is configured in this
  repo.

- [Guardrails] G-1 ✓ — nothing under `src/nonogram/admin/` compares a score to anything;
  the only tier logic added is a `parse_tier` delegation and an iteration over `Tier` for
  the form options; no new cutoff-named constant. G-2 ✓ — the resample bound, the
  `MAX_CONSECUTIVE_ABANDONMENTS` stop and CARD-093's keep-the-work behaviour are
  structurally unchanged; only their *note* learns the tier, and two tests pin the stop
  (work kept + COMPLETE) and the zero-puzzle case (still ERROR). G-3 ✓ — no
  `src/nonogram/export/**`, `tests/fixtures/a4_golden/**` or `book_*.py` in the diff.
  G-4 ✓ — `src/nonogram/cli.py` untouched; the CLI's `--difficulty` path is not on this
  diff at all.

- [For the owner / a later card] A batch does **not** record which tier it was asked for:
  `batches` has no column and this card writes no migration, so the request's tier is
  visible only in the note when the batch falls short. If the panel should show "this
  batch asked for Medium" on a *successful* batch, that is a column + migration decision,
  not an oversight here. Image-mode batches ignore the field by design (out of scope).

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/batch_generator.py,
  src/nonogram/admin/templates/batch_create.html, tests/test_batch_difficulty_target.py
- [Scope gate] ⚠ grown: 1 of 4 changed files outside Touches —
  `src/nonogram/admin/templates/batch_create.html` in place of the card's
  `generate_batch.html`, recorded as SCOPE+ by the implementation agent with the reason
  (generate_batch.html is the *image* flow's step 3 and image mode is out of this card's
  scope; the random path is `POST /batch/create`, whose form had never been built).
  comp_spread 0 (COMP-009 only, declared); no sibling card poached (CARD-118/127/130/134
  claim book_*/app.py/other templates, none claims batch_create.html); no guardrail glob
  hit (src/nonogram/export/**, tests/fixtures/a4_golden/**, book_*.py all untouched).
- [Card defect] the `Touches:` field names `src/nonogram/admin/templates/generate_batch.html`,
  which is the image flow's confirmation page, and describes "existing size and count
  fields" that did not exist on any rendered page. Source station: decompose. Not blocking
  this card — the AC is satisfiable on the route that actually runs a random batch — but a
  later UI card in this area must not trust the field.

- [Build gate] PASSED (full, 250s) — exit 0 under the repo full-suite lock with a private
  --basetemp, 4736 tests collected, the one known pre-existing failure deselected
  (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied,
  red before this card). Card file alone: tests/test_batch_difficulty_target.py 23 passed
  in 0.25s — the suite did not become slow.

- [Review 1/3] Score: 8.5 — crit: 0, imp: 1. Step 8h: 47 rules checked, 14 ✓ holds,
  33 ⚠ unchecked (all `no_eligible_fact` — repair/scoring/book/web/export code is not on
  this 4-file diff), 0 ✗ violated. Guardrails G-1..G-4 all ✓, each re-derived rather than
  read off the notes: the reviewer ran its own ast walk over src/nonogram/**/*.py and found
  the only score-vs-cutoff comparisons in the package are difficulty.py:511,513 inside
  `classify`, with src/nonogram/admin/ clean and tests/test_difficulty_tiers.py not in the
  diff. AC-2's "Any is unchanged" was proved byte-identical against main's string. The test
  stub was mutation-checked: deleting the tier hand-off kills 9 of 23 tests. Not a UI card
  by the pipeline's test and the repo has no Makefile run target, so Step 8g ran static-only
  against meta/design/brief.md + components.md and the rendered result was NOT verified.
- [Review sync] 1 report → meta/review/

- [Adversarial] F-001 CONFIRMED — "a targeted batch that runs out of its time budget
  reports no tier, and the new comment claims it does". An independent skeptic tried to
  refute it and could not: the comment at batch_generator.py:516-522 reads "A batch that
  asked for a tier says so in every sentence below (CARD-138)" — unscoped — and it is
  false for two of the five sentences (`not_attempted` :586-594 and the store refusal
  :595-603 both omit the tier); the `target` phrase is built at :523 and used exactly once
  (:532). The skeptic reproduced the batch independently with its own script and an
  injected `monotonic`: COMPLETE, 5 of 20 stored, the un-tiered time-budget sentence
  verbatim. It also found reachability worse than the finding argued — 30 resamples per
  candidate against a fixed BATCH_BUDGET_SECONDS = 75.0 and ~3.9s per 30x30 puzzle means
  one targeted candidate can burn the whole batch budget — and no test covers
  `not_attempted` with a tier. Severity kept at Important. Nothing under src/ or tests/ was
  touched by the verification.
- [Review 1/3] after adversarial verification: crit: 0, imp: 1 — severity gate CLOSED at
  score 8.5; fix mandatory.

- [Fix 1] pre-gate PASSED — all four named tests exist and are green
  (TestBatchDifficulty_TheClockShortfallNamesTheTierToo,
  TestBatchDifficulty_TheFormStatesNoBoundOfItsOwn,
  TestBatchDifficulty_FormOffersTheChoices, TestBatchDifficulty_TheFormDrivesARealBatch —
  13 tests in 0.16s). F-001 fixed plus five of the review's Minors; two answered
  `test: n/a` with a reason (inline JS with no JS runner in the suite; a lede change no
  test should pin). The declaration cross-check holds: the comment at
  batch_generator.py:538-559 no longer says "every sentence below" — it names the three
  shortfall sentences that carry the tier and names the store-refusal sentence as the
  deliberate exception, with CARD-080's reason (a store refusal is a generation-path bug,
  not a tier shortfall, so naming the tier there would invite the owner to work around a
  defect that is not theirs).
- [Fix 1] declarations: 2 updated (the note-site comment, `_generate_random_batch`'s
  docstring + `create_batch`'s Args for the new `MIN_RANDOM_BATCH_COUNT`), 0 confirmed,
  4 none (local branches).

- [Touches corrected] `generate_batch.html` -> `batch_create.html` on the field itself,
  2026-09-23. Not a convenience edit to make a gate pass: the reviewer verified the premise
  independently — `git grep 'batch/create' main -- templates/*.html` finds only `<a href>`
  links, no template on main posts to `POST /batch/create`, and `main:generate_batch.html`
  holds one form (the image flow's confirmation checkbox, no action, no count/size/
  difficulty). AC-3 is unsatisfiable without building a form, so the file the card named
  was the wrong one and the prediction is recalibrated to reality. The [Card defect] note
  above stands — decompose is still the station that got it wrong.
- [Build gate] PASSED (full, 233s) — exit 0, 4717 passed, 26 skipped, 1 deselected (the
  known pre-existing e2e failure). Re-run after the cycle-1 fixes, own private --basetemp.
  Note for the dispatcher: the repo full-suite lock was held as a REGULAR FILE by another
  pipeline for ~20 min, so the documented `mkdir`-based acquisition can never succeed
  against it; this gate was serialized against the sibling suites by waiting them out
  instead. Worth reconciling the two lock conventions before the next wave.

- [Review 2/3] Score: 9.0 — crit: 0, imp: 0. Step 8h: 47 rules checked, 14 ✓ holds,
  33 ⚠ unchecked (typed `no_eligible_fact`), 0 ✗ violated — every one of the card's 47
  ids carries its own verdict line (verified mechanically against the card's section: no
  id missing, none duplicated). Cycle 1's F-001 and all five Minors verified resolved. The
  five new findings are all Minor and none gates: the pre-existing `querySelector('form')`
  binding, a size default duplicated from the route, two comment/docstring wording defects
  in the new `MIN_RANDOM_BATCH_COUNT` block, and a flashed error discarding the operator's
  form input. Not a UI card by the pipeline's test and the repo has no Makefile run target,
  so Step 8g ran static-only and the rendered result was NOT verified.
- [Review sync] 2 reports → meta/review/

- [8h spot-check] 3/3 sampled holds reproduced (ADR-0031/R1, INV-002, CON-011), each by an
  independent skeptic re-running the evidence rather than reading the verdict.
  ADR-0031/R1: its own ast walk of all 57 src/nonogram/**/*.py found 6 score-vs-constant
  comparisons — 2 in `classify` (difficulty.py:511/513, the sanctioned site), 4 pre-existing
  in analysis/ — zero under admin/, zero bare 33/66/90; tests/test_difficulty_tiers.py 0-byte
  diff and 56 passed. CON-011: rendered the page off the WORKTREE src and asserted the
  emitted `min`/`max` equal `limits.MIN_SIZE`/`MAX_SIZE` programmatically rather than
  eyeballing 10/30. INV-002: re-derived the store call site as byte-identical to main and
  confirmed a refusal still increments `refused_count` and never `puzzle_count`.
  Two honest corrections the skeptics volunteered, neither changing a verdict: the cycle-2
  reviewer's ADR-0031/R1 sentence undercounts (it says 4 comparisons, there are 6), and half
  of its INV-002 verdict (the un-tiered refusal note) is a design note rather than evidence —
  the first clause carries the rule on its own.
- [Handover] Pre-existing, outside this card and outside the AST guard's reach:
  `src/nonogram/analysis/strategy_counter.py:138,140` is a SECOND easy/medium/hard mapping on
  its own bare 30/70 cutoffs. The guard matches cutoff NAMES, never literals, so it cannot
  see it. Untouched here; worth a card.
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — TestBatchDifficulty_MediumBatchReturnsOnlyMediums, 7 passed. Evidence
    class checked rather than assumed: the stored tier is not the request echoed back — the
    store callback passes `puzzle.difficulty_tier`, which is `difficulty.classify(score)`
    computed on read (orchestrator.py:1141-1157). Bound stated: `orchestrator.generate` is
    stubbed, so the real draw->solve->score->resample chain is not exercised here (it is
    pinned in tests/test_resample.py).
  AC-2 ✓ demonstrated — TestBatchDifficulty_AnyIsUnchanged, 5 passed; the load-bearing member
    asserts CARD-083's full note string verbatim, not a substring, and the untargeted clock
    sentence is pinned the same way.
  AC-3 ✓ demonstrated — TestBatchDifficulty_FormOffersTheChoices, 5 passed. The least-stubbed
    AC: a real GET /batch/create through the Flask client against the real template, exactly
    four options, `selected` occurring once and on the empty one.
  AC-4 ✓ demonstrated — TestBatchDifficulty_ShortfallIsReportedNotSilent, 6 passed — COMPLETE
    with 20 of 40 stored, the note naming the tier and the counts, the untargeted wording
    explicitly not reused, the consecutive-abandonment stop keeping its work, the zero-puzzle
    case still ERROR, and the note reaching a real sqlite row.
  G-1 ✓ demonstrated — tests/test_difficulty_tiers.py 56 passed incl. the guard's own
    meta-test (it is not passing vacuously); 0-byte diff against both main and the merge-base,
    so it was not weakened, retargeted or deleted.
  G-2 ✓ demonstrated — all four bounds live in orchestrator.py, which has an empty diff;
    the `except (GenerationAbandoned, SolverTimeout)` block is unchanged and only the note
    below it branches; tests/test_batch_keeps_partial_work.py 11 passed.
  G-3 ✓ demonstrated — the card's changed-file list carries no src/nonogram/export/**,
    tests/fixtures/a4_golden/** or book_*.py.
  G-4 ✓ demonstrated — cli.py 0-byte diff; CARD-113's tripwire green and unmodified
    (tests/test_export_a4_golden.py 63 passed, test_cli_exports_byte_identity.py 3 passed,
    fixtures 0-byte diff).
- [AC/EC check] ⚠ Method note worth keeping: `git diff main` is MISLEADING from this branch
  now that main has advanced (CARD-118 merged as 8765b91). Against main the diff lists
  main's newer files as deletions — including `src/nonogram/admin/book_proof.py`, which
  matches G-3's guarded `book_*.py` glob exactly. A gate trusting that output would have
  failed a card that never touched the file. Every verdict above was taken against the
  MERGE-BASE. Later cards in this wave must do the same.

- [Docs] No README owed. `src/nonogram/admin/` and `src/nonogram/admin/templates/` carry no
  README at all, and this card adds no module there — it edits two existing files and one
  existing template. `tests/README.md` exists but is the legacy "Admin Panel Test Suite -
  Wave 1" document, which does not enumerate the modern per-card test files; adding an entry
  for tests/test_batch_difficulty_target.py would be out of place rather than owed. Same
  judgement CARD-137 recorded for the same file.

- [Commit] 8888c6a — the success commit. Two commits on the branch: 6b48ace (the field
  plumbed through, the form, the tier-aware shortfall note) and 8888c6a (the cycle-1 review
  round). Four files staged by explicit pathspec; nothing under meta/ committed from the
  worktree. Working tree clean apart from the card copy and the two review YAMLs, both of
  which are the orchestrator's to carry out, not the branch's.
- [Owner] Nothing in this pipeline has ever SEEN the new form rendered. The repo has no
  Makefile run target, so both review cycles ran Step 8g static-only and no screenshot was
  captured at any stage; the only evidence is Flask-test-client assertions against the HTML
  source. Unseen: how the new "Or generate random puzzles" card sits beside the picture flow
  and its stepper (which still describes only pictures), the three fields' layout at panel
  widths, and — the one piece of this card with zero automated coverage — whether the inline
  submit-disable handler actually works. That handler matters: a random batch runs
  synchronously and can burn the full 75s budget, so without it a second click starts a
  second batch. Suggested eyeball: open /batch/create, submit one small Medium batch, watch
  the button state and the resulting batch note.

- [Done] Merged cc64540 on 2026-09-23. Review 9.0 after 2 cycles (8.5 -> 9.0, 0 critical,
  0 important at close; cycle 1's one Important F-001 was confirmed by a skeptic and
  fixed). AC-1..AC-4 and G-1..G-4 demonstrated. Two full-suite runs, both exit 0. Golden
  tripwire green and unmodified; cli.py untouched (G-4). Full suite green on the merge.
- [Card defect -> decompose] Touches named templates/generate_batch.html, but that file
  is the IMAGE flow's confirmation page and no template on main posts to
  POST /batch/create — AC-3 was unsatisfiable as written. The real file is
  templates/batch_create.html; the Touches line was corrected in the worktree.
- [Owner] The new form has never been seen rendered: there is no Makefile run target, so
  both review cycles ran static-only and no screenshot exists. The inline submit-disable
  handler has NO automated coverage (no JS runner in this repo) and a random batch runs
  synchronously for up to 75 s — without it, a second click starts a second batch. Open
  /batch/create, submit one small Medium batch, and watch both the button and the batch
  note.
- [Out of scope, deliberate] A successful targeted batch still stores no record of which
  tier it asked for; `batches` has no such column. That is a column + migration decision.
