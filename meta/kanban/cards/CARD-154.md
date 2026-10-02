# CARD-154: Print setup saves the plan and the trim together, and refuses "nan"

**Status:** done
**Priority:** P2
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/154-plan-and-trim-together
**Worktree:** —
**Source:** CARD-136 handover (2026-09-23), two backlog entries; code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** src/nonogram/admin/print_specs.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, tests/test_print_specs.py (new), tests/test_book_plan_storage.py
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-10-02T14:05:14Z
**Closed:** 2026-10-02T14:50:25Z
**Actual:** 0.1d
**Merge commit:** 677744c
**Blocked by:** —

## What to implement

Print setup writes a book's distribution plan and its trim size as two separate
DB transactions: `BookManager.save_plan` (`book_manager.py:728`, commits at
~:773) and then `set_print_spec` (:776). If the second write fails, the first one
has already committed.

There is a real input that makes this happen:
`PrintSpecValidator.validate_trim_size` (`print_specs.py:138`) checks the trim
with `<`/`>` comparisons only. `float("nan")` fails every comparison, so the
string `"nan"` passes validation, `create_spec` builds a spec, `save_plan`
commits, and only then does `set_print_spec`'s `math.isfinite` guard (:849)
raise. The book ends up with the new plan and the old trim. The same goes for
`"inf"`.

## What to do

1. Refuse a non-finite trim in `validate_trim_size`, so it never reaches storage.
   Keep `set_print_spec`'s guard as defence in depth.
2. Write the plan and the trim in **one** session in DB mode, so either both
   are stored or neither is. In memory-only mode, keep the same all-or-nothing
   behaviour.
3. Check the margin validators for the same NaN gap while you're there, and
   close it if it exists.

## Acceptance criteria

- **AC-1:** `validate_trim_size` refuses `"nan"`, `"inf"` and `"-inf"` for
  either dimension, with the same message shape as other invalid input.
  *test: TestTrimValidation_RefusesNonFiniteValues*
- **AC-2:** If writing the trim fails after the plan has been accepted, the stored
  plan is unchanged (DB mode).
  *test: TestPrintSetup_PlanAndTrimCommitTogether*
- **AC-3:** Submitting `"nan"` as the width on Print setup re-renders the form with
  the refusal, and neither the plan nor the trim changes.
  *test: TestPrintSetup_NanWidthChangesNothing*

## Guardrails

- G-1: Don't change any valid trim, margin or plan behaviour. Existing Print setup
  tests stay green without edits, unless they asserted the two-transaction shape.
- G-2: No schema change, no migration.
- G-3: The regression tests must run against a database (use
  `sqlite_session_scope`, since DB-mode tests skip silently without
  `nonogram_test`). Don't make them depend on the owner's Postgres.

## System contract

_Assembled 2026-10-02 by system_rules.py --card CARD-154 (scope: Touches globs); 44 mandatory rules._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package data instead, and doing so is not a dependency change. (test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py. (test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer. (review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by more than 2x from the source's INK BOUNDING BOX ratio — not from its as-decoded file ratio — is refused rather than cropped. The bounding box is computed and judged before any crop is applied, so a refused request is still refused before any cropping runs. (test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the other side from the source's own aspect ratio, clamped to MIN_SIZE at the bottom only and never at the top. A source whose ratio exceeds N/5 is refused with a message naming the smallest N that would accommodate it, never silently clamped. (test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
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
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the grid it was handed and refuses, with NotUniquelySolvable, any grid whose clues do not have exactly one solution — including one whose solve timed out or could not be attempted. No caller's assurance substitutes for that check, and no admin path writes a puzzle row by another route. (test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle never satisfies a quality minimum, is never the left operand of an order comparison, and renders as "N/A" wherever a score would be shown — templates, API responses and the book PDF alike, the book omitting the /100 denominator that a non-number does not take. recognizability carries the same rule in its own vocabulary. (test: TestUnmeasuredQuality_SurvivesTheFilter)
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
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a parameter: no supported call into nonogram.admin.app widens it, and no module under src/nonogram/admin/ names another bind address in code. Restates NFR-003 for the second inbound HTTP surface, which CON-009 does not reach. (test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not pass the door in force. With it unset (the default), it refuses any request whose Host header does not name this machine — a bare authority, no userinfo, path, query or fragment, a port absent or all digits, and a host component in {localhost, 127.0.0.1, ::1} — and refuses a request carrying no Host header at all. With it set, it refuses any request whose Host is not exactly that hostname (a loopback Host included), any request not carrying the configured credential, and any request the browser marks as started by another site (a Sec-Fetch-Site outside {same-origin, none}, or an Origin whose host is not that hostname). The wrong-host refusal is indistinguishable from "no such page" in both modes, so it tells a scanner nothing. Holds however the socket was bound, including when the bind was widened by an option outside this package's control. (test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
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

- **FR:** FR-030, FR-031 (print setup, as CARD-136); CON-018 (margin defaults)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] CARD-136's handover listed the NaN edge and the two-transaction writer
  as separate items. They're one defect: NaN is the input that makes the split
  write visible. Cut on 2026-10-02.
- [Related, not in scope] memory-only `get_book` returns the live `Book`, so a
  caller can write an invalid trim past validation (CARD-136, owner-accepted).
  That stays on the backlog.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +44 (card had no section) / −0
- [Impl 2026-10-02] `PrintSpecValidator.validate_trim_size` refuses a non-finite width/height
  (nan/inf/-inf, any case/whitespace, "1e999") with the existing "Trim size must be numeric
  values" message. `BookManager.save_plan(book_id, plan, print_spec=None)` gained an optional
  `print_spec`: the spec is checked first (`_checked_print_spec`, the checks lifted verbatim out
  of `set_print_spec`, which keeps them as defence in depth), then plan + trim + ink mode are
  written in ONE session / ONE commit (DB) or assigned together after all checks (memory).
  `_apply_print_spec` is the shared column write. Print setup calls `save_plan(..., print_spec=spec)`
  on a plan edit and `set_print_spec` alone when the plan is unchanged. No schema change (G-2).
- [Margins] Gap existed: `create_spec` did not validate margins at all ("nan"/"inf"/"abc" went
  into the spec). New `PrintSpecValidator.validate_margins` refuses a given margin that is not a
  finite number ("<Label> must be a numeric value"); None/"" still mean default. Not reachable
  from Print setup (no margin field) and `set_print_spec` never writes margins; the read path
  (`book_page_spec._stored_mm`) already refused non-finite stored margins via Decimal.is_finite.
- [Tests] tests/test_print_specs.py (new). AC-1 → TestTrimValidation_RefusesNonFiniteValues
  (11 spellings x 2 dimensions + seeded 2000-case finite corpus against literal KDP bounds);
  AC-2 → TestPrintSetup_PlanAndTrimCommitTogether; AC-3 → TestPrintSetup_NanWidthChangesNothing
  (Flask client, cm and inches, asserts alert + message re-rendered and plan/trim/status/ink
  unchanged); item 3 → TestMarginValidation_RefusesNonFiniteValues. Storage/route tests run in
  three stores: memory, sqlite_session_scope, and the REAL nonogram_test Postgres via conftest's
  `db_session` — all ran, none skipped (`-rs` shows no skips; 104 passed in the file).
- [AC-2 revert check] Restoring the two-commit shape inside save_plan (save_plan commit, then
  set_print_spec) makes 17 AC-2 cases fail (15 refused-spec x 3 stores + the before_flush
  injected-failure case on sqlite and Postgres); restored → all pass. The injected failure is a
  SQLAlchemy before_flush listener that raises when a books row's trim is dirty, i.e. after the
  plan was accepted and while it is pending in the same transaction.
- SCOPE+ tests/test_book_trim_persistence.py — TestBookTrim_AWriteThatStoredNothingIsReported
  [set_print_spec] asserted the two-writer shape (a book vanishing BETWEEN the plan write and
  the trim write, a window this card removes): with a plan edit the route no longer calls
  set_print_spec. Edited minimally: that parametrization now submits the unchanged default plan
  so the route takes the trim-only path through set_print_spec; F-004's "Book not found" is still
  asserted for both writers. No other existing test edited.
- [Render] Print setup HTML unchanged in structure; a non-finite trim now re-renders with the
  existing flash "Error: Trim size must be numeric values" (previously "Error: a book's
  trim_width_cm must be a finite number of cm, not 'nan'" after the plan had been stored).
- [Run] related files (19 incl. test_cli import guard, book plan/trim/page-spec/pdf/scaffolding):
  1082 passed, 0 skipped, via the lock wrapper.
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/print_specs.py, tests/test_book_trim_persistence.py, tests/test_print_specs.py
- [Build gate] PASSED (full, 391s) — 5772 passed, 9 skipped, 2 failed; the 2 failures are exactly the known main baseline (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders), treated as baseline
- [Scope gate] in_scope — 5 files, 1 outside Touches (tests/test_book_trim_persistence.py, 20%, recorded SCOPE+ under G-1's two-transaction exception); all COMP-009; no guarded paths (no alembic/migration/model files)
- [Review sync] 1 report(s) → meta/review/ (20261002T142605Z-CARD-154-cycle1.yml)
- [Adversarial] F-001 CONFIRMED — skeptic reproduced: old two-commit route wiring passes 888 tests across 14 book/print files; AC-2 test calls save_plan directly, never the route
- [Review 1/3] Score: 8.5 — crit: 0, imp: 1 (Step 8h: 44/44 ids covered, 11 ✓ / 33 ⚠ no_eligible_fact / 0 ✗; 8f-mutation deferred(cost))
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory
- [fix cycle 1, F-001] Invariant enforced: Print setup stores the plan and the trim together or
  neither. Discriminator: the raw `books` row (distribution_plan, trim_width_cm, trim_height_cm,
  status) re-read in a fresh session, not a return value. New route-level AC-2 case
  TestPrintSetup_PlanAndTrimCommitTogether::test_print_setup_route_stores_neither_when_the_trim_write_fails
  [sqlite, postgres]: a Flask client POSTs a plan edit with a VALID 20.32x25.40 trim to
  /book/<id>/setup-print while the before_flush listener refuses the trim flush, then asserts
  the row still holds DEFAULT_PLAN, the 6x9 trim and the original status. Revert check: app.py:3061 changed to the
  two-commit probe `save_plan(book_id, new_plan) and set_print_spec(book_id, spec)` → 2 failed
  ("the plan was stored while the trim was refused"); restored (md5 3da4edd8…ff7) → 2 passed, 0
  skipped. Test-only fix; no behaviour or declaration changed.
- [fix cycle 1, F-002] Intended: "inf"/"-inf" were refused before this card too, by the bound
  checks ("cannot exceed"/"must be at least"), and only "nan" got through (the card's "the same goes for
  inf" overstated it). They now get AC-1's "Trim size must be numeric values", as does a huge
  inches entry ("1e308") that inches_to_cm overflows to inf. No code change.
- [Fix 1] FIXED F-001 — test: tests/test_print_specs.py::TestPrintSetup_PlanAndTrimCommitTogether::test_print_setup_route_stores_neither_when_the_trim_write_fails (pre-gate: 2 passed; revert-to-two-commit route → 2 failed with the finding's symptom); SKIPPED F-002 (Minor, intended per AC-1, dismissed in YAML)
- [Fix 1] declarations: 0 updated, 0 confirmed, 1 none (test-only fix)
- [Build gate] PASSED (full, 376s) — 5774 passed, 9 skipped, 2 failed = the known main baseline
- [Scope gate] cycle 2: in_scope (same 5 files)
- [Review 2/3] Score: 9.5 — crit: 0, imp: 0 (confirmation mode; F-001 ✓ resolved, revert probe reproduced; Step 8h: 44/44 ids covered, 11 ✓ / 33 ⚠ / 0 ✗, all carried(cycle 1, delta-clean))
- [Review 2/3] Score: 9.5 ✓ threshold reached + no critical/important
- [Mutation] 8f certifying cycle: 9 mutants, 9 killed, 0 survived (trim isfinite x2, margin guard x2, save_plan spec-check skip, plan-commit-before-spec, memory ordering, route save_plan w/o spec, route trim-only branch)
- [8h spot-check] skipped — pool empty: every cycle-2 ✓ holds is carried(cycle 1, delta-clean), none freshly asserted
- [Review sync] 2 report(s) → meta/review/ (cycle1, 20261002T144154Z-CARD-154-cycle2.yml)
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-1 ✓ demonstrated — TestTrimValidation_RefusesNonFiniteValues 26 PASSED (11 spellings x 2 dimensions; same message as 'abc')
  AC-2 ✓ demonstrated — TestPrintSetup_PlanAndTrimCommitTogether 25 PASSED, 0 skipped, incl. route-level test_print_setup_route_stores_neither_when_the_trim_write_fails[sqlite|postgres] and in-transaction rollback on real nonogram_test
  AC-3 ✓ demonstrated — TestPrintSetup_NanWidthChangesNothing 18 PASSED (real route, cm+inches, memory/sqlite/postgres; 200 + alert + message; plan/trim/status/ink unchanged)
  G-1 ✓ demonstrated — 30 existing plan/trim/print-setup files + test_cli: 1338 passed; only edit = test_book_trim_persistence [set_print_spec] param, asserted the two-transaction shape, assertions unchanged
  G-2 ✓ demonstrated — changed files contain no model/migration/schema path; no Column/ALTER/add_column in added src lines
  G-3 ✓ demonstrated — every AC-2/AC-3 DB case has a sqlite_session_scope variant (no Postgres needed) plus a real nonogram_test variant (guarded _test); 0 skips
- [Docs] forge:readme: src/nonogram/admin/ has no README and gained no files/responsibility; tests/README.md does not enumerate test files — both current, nothing to update
- [Render] ~/Documents/nonogram-reviews/CARD-154/print-setup-nan-{before-main,after}.{html,png} — 'nan' width on Print setup: main stores plan 120 beside the old trim and shows 'trim_width_cm must be a finite number'; card branch keeps plan 150 + trim and shows 'Trim size must be numeric values'. Page structure unchanged.
- [Commit] success commit 87b3d6a on card/154-plan-and-trim-together (on top of implementation 3ee27fb); 5 files, +556/−48; score 9.5 (cycle 2/3)
- [Merged] 2026-10-02 — 677744c into main (--no-ff). Merge gate: rebase was a no-op (main still at 14fca25 = branch base), so the merged tree is the one that passed the post-fix full suite (376s; only the 2 baseline failures); not re-run — the wave-29 smoke test runs the full suite on main next. Deferral scan: 0 hits. Trace write-back: 3 evidence tests appended to FR-030 and FR-031; statuses stay `partial` (FR-030 is still listed by open CARD-158/159). F-002 noted: the card's "the same goes for inf" was inaccurate — inf/-inf were already refused by the bound checks; only nan got through.
