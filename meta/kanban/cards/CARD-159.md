# CARD-159: Book forms keep what you typed and say the right step

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/159-book-forms-keep-input
**Worktree:** —
**Source:** CARD-130 handover, CARD-136 handover (backlog); templates re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 30
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_setup_print.html, src/nonogram/admin/templates/book_create.html, src/nonogram/admin/app.py, tests/test_book_workflow_steps.py, tests/test_book_create.py (new)
**Review score:** 9.4 (cycle 1/3)
**Started:** 2026-10-02T18:45:38Z
**Closed:** 2026-10-03T02:41:40Z
**Actual:** 1.0d
**Merge commit:** 7101fbf
**Blocked by:** —

## What to implement

Three form defects on the book workflow:

1. **"Step 1 of 4" next to a five-step stepper.**
   `book_setup_print.html:12` still says "Step 1 of 4". CARD-130's G-4 kept this
   file frozen while CARD-118 was in flight; CARD-118 has merged since. The prose
   guard in `tests/test_book_workflow_steps.py:1052` skips this step on purpose
   (`PROSE_CHECKED = (0, 2, 3, 4)`), and the comment beside it explains how to
   re-enable it.
2. **The inches option can't be used.** The width and height inputs carry fixed
   `min="10" max="30"` (and `48`) values in centimetres
   (`book_setup_print.html:46` and its siblings). With "Inches" selected, a real
   8.5 in trim fails the browser's own validation before it is submitted.
3. **`/book/create` throws away what you typed.** On error, the route flashes the
   message and re-renders `book_create.html` with no form values (`app.py:2438-2440`).
   Edit was fixed for this same defect in CARD-130; create was left frozen by that
   card's objective 3.

## What to do

1. Fix the step text (or derive it from the stepper's own step list, so it
   can't drift again) and add step 1 to `PROSE_CHECKED`.
2. Make the inputs' `min`/`max` follow the selected unit: switch them when the
   unit radio changes, or drop the browser bounds and rely on the server's
   validation, which already reports out-of-range trims. Either way, an inches
   value inside KDP's bounds must submit.
3. Re-render `/book/create`'s refusal with the submitted values filled in, the
   same way edit does after CARD-130.

## Acceptance criteria

- **AC-1:** Print setup's prose names the step the stepper marks as current, and
  the prose guard checks every step.
  *test: the prose guard in tests/test_book_workflow_steps.py with step 1 restored*
- **AC-2:** With the inches unit chosen, an 8.5 x 11 in trim is accepted by the
  rendered form's bounds and by the server.
  *test: TestPrintSetup_InchesTrimIsReachable*
- **AC-3:** A refused `/book/create` shows the form again with the submitted
  title and fields filled in.
  *test: TestBookCreate_RefusalKeepsTypedInput*

## Guardrails

- G-1: Server-side trim validation is unchanged (KDP bounds stay where they are).
- G-2: Use existing tokens and components only.
- G-3: The owner checks the rendered forms in both units (see
  owner-validates-visually). Put the renders in
  `~/Documents/nonogram-reviews/CARD-159/`.

## Architecture context

- **FR:** FR-038 (book workflow steps, as CARD-130), FR-030 and FR-031 (print setup, as CARD-136)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## System contract

_Assembled 2026-10-02 by system_rules.py --card CARD-159 (scope: Touches); 44 mandatory rules._

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

## Worktree notes

- [Origin] Form-side leftovers from CARD-130 and CARD-136. Cut on 2026-10-02.
- [Env] forge 2026.8.17
- [System contract] section stale — refreshed from the model: +44 rules (card had no section) / −none
- [Impl] Obj 1: `book_setup_print.html` lede now `{{ stepper.book_step_of(1) }}` (renders "Step 2 of 5"); its breadcrumb also said a hand-written "step 1" and now uses `book_step_number(1)` like the sibling step pages. `PROSE_CHECKED = (0, 1, 2, 3, 4)` with the stale G-4 comment replaced — the restored step also turns on the breadcrumb guard for Print setup, which caught the crumb.
- [Impl] Obj 2: approach = **dropped the browser min/max** on the width/height inputs (kept `step="0.01"` and `required`). Chosen over a unit-switching script because the server's `validate_trim_size` is already the one statement of KDP bounds and reports out-of-range trims with entries carried back; per-unit browser bounds would need rounding care (e.g. the Limits box's "18.90 in" is 48.006 cm, which the server refuses) and an untestable JS branch in a project with no browser harness. Server validation untouched (G-1). Test: `TestPrintSetup_InchesTrimIsReachable` (inches and cm initial renders, reopen-on-inches-trim, server stores 8.5x11/8x10/6x9 in, server still refuses 12 in width).
- [Impl] Obj 3: `create_book` now mirrors `edit_book`'s refusal: passes `submitted=request.form` and `error_fields` (`InvalidBookDetails.fields`, else none) to `book_create.html`; template already read both, only its comments changed. `test_the_create_screen_is_untouched_by_the_marking` (which asserted the old inert behaviour) is revised to `test_the_create_screen_marks_like_the_edit_screen`. New `tests/test_book_create.py::TestBookCreate_RefusalKeepsTypedInput` covers all four refusal reasons, field marking, HTML-special escaping, a plain ValueError naming no field, fresh GET, happy path.
- [Impl] Mutation-checked: restoring old create route fails 10/12 create tests; restoring `min="10" max="30"` fails 4 inches tests; restoring "Step 1 of 4"/"step 1" fails 2 prose/crumb tests.
- [Impl] Follow-up (not done, outside scope/G-1): the Limits box text "18.90 in" / "11.81 in" are rounded inch forms; 18.90 in exceeds 48 cm and would be refused by the server. Consider deriving the box from the server constants.
- [Impl] No SCOPE+ — all edits within Touches.
- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/book_create.html, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_create.py, tests/test_book_workflow_steps.py
- [Build gate] impact underivable (test_scope: full; python-pro without pytest-testmon) — full suite
- [Build gate] PASSED (full, 400s) — 5858 passed, 9 skipped, 2 failed = exactly the main baseline (tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders); no new failures
- [Scope gate 1] IN_SCOPE — 5 files, all within Touches (tests/test_book_create.py is the declared new file); comp_spread none (COMP-009 only); no ready siblings to poach; G-1/G-2/G-3 behavioral/visual, no structural globs
- [Visual] review.visual off (no harness run target) — review runs Step 8g static-only
- [Review 1/3] Score: 9.4 — crit: 0, imp: 0 (Minor: F-001 Limits box '18.90 in' exceeds the 48 cm the server accepts; F-002 no route test for below-minimum/zero/negative trims; F-003 create refusal reuses edit-mode alert copy. Out-of-scope: F-004 components.md stale 'Step 1 of 4' note; F-005 trim refusals worded in cm after an inches submit — print_specs.py frozen by G-1)
- [Adversarial] no gating findings in cycle 1 — nothing to verify
- [Review 1/3] Step 8h coverage: 44/44 card rule ids carry a verdict line (6 ✓ holds, 38 ⚠ unchecked no_eligible_fact, 0 ✗)
- [Review 1/3] mutation check: 7 mutants, 7 killed, 0 survived (M1 drop submitted, M2 empty error_fields, M3 min=10 width, M4 'Step 1 of 4', M5 title|safe, M6 max=10 height, M7 'step 1' crumb)
- [Review 1/3] Step 8g static: tokens ✓, inventory/states ✓, anti-defaults ✓, a11y statics ✓ — rendered result not verified by the reviewer (visual off)
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Score: 9.4 ✓ threshold reached + no critical/important
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1 — test_the_dependency_baseline_is_still_closed, traced to TestDependencyBaseline_IsExactlyPillowAndNumpy at tests/test_export_pdf.py:622-624, 1 passed; ADR-0019/R1 — test_every_import_in_the_package_points_inward 1 passed, no src import added; CON-015 — TestAdminPanel_BindsLoopbackOnlyByDefault 7 passed, no bind/host literal added)
- [Renders] ~/Documents/nonogram-reviews/CARD-159/ — before-* (main 47a5204) and after-* (233678f) at 1440/390: print-setup-cm, print-setup-inches-typed-8.5x11, print-setup-inches-reopened, book-create-refused; driven in headless Chromium: on main the browser's checkValidity() BLOCKS 8.5 in (width min=10), lede 'Step 1 of 4', refused create comes back empty; on the branch 8.5x11 in passes checkValidity, the server stores 21.59 x 27.94 cm and redirects to puzzle selection, the reopened page shows Inches with 8.50/11.00, lede 'Step 2 of 5', refused create keeps description (with <, &, quotes literal) and audience and marks only title. Final after-* renders written 22:2x local, after the last source commit (21:51:37 +0300). A first capture caught the unit toggle mid-CSS-transition (washed out); re-captured with an 800 ms settle — artifact, not a defect. 390 plan-table input clipping ('2(' for 20) is pre-existing: before/after cm-390 differ only in the lede band (y 32-228).
- [AC/EC check] All criteria/constraints ✓ (evidence) — with one ruling, stated: G-3 returned ⚠ partial because its second half (the owner looks at the forms) is a human act at done that no worktree change can produce; its in-pipeline half (current renders in ~/Documents/nonogram-reviews/CARD-159/) is demonstrated. G-3 is handed to the dispatcher as a pre-merge owner check, not counted as verified. No fix loop run for it (it cannot converge). Card has no ## Engineering constraints section (no EC items).
-   AC-1 ✓ demonstrated — evidence: PROSE_CHECKED = (0, 1, 2, 3, 4) (tests/test_book_workflow_steps.py:1052); TestBookStepPages_ProseAgreesWithTheStepper 17 passed
-   AC-2 ✓ demonstrated — evidence: TestPrintSetup_InchesTrimIsReachable 9 passed — rendered-form bounds under inches (8.5x11, 8x10, 6x9) via an independent model of the browser's min/max/step checks, server stores 8.5x11 in as 21.59x27.94 cm, 12 in still refused (Flask test-client, real template/route; no e2e harness) — corroborated by a real-Chromium checkValidity() run in the renders
-   AC-3 ✓ demonstrated — evidence: TestBookCreate_RefusalKeepsTypedInput (tests/test_book_create.py) 12 passed
-   G-1 ✓ demonstrated — evidence: print_specs.py and the setup_print route absent from the diff; test_print_specs + test_book_trim_persistence + test_book_scaffolding + beyond-KDP refusal 245 passed; no trim-bound assertion removed from tests/
-   G-2 ✓ demonstrated — evidence: added template lines carry no new class/style/colour/px literal or markup (only the pre-existing class="lede" line, text swapped for a macro); no CSS/token file changed
-   G-3 ⚠ partial — after-* renders for cm, inches 8.5x11 (typed and reopened) and refused /book/create at 1440 and 390, newer than the last commit; the owner's visual check happens at done and is not verified here
- [Docs] skipped — the changed src/ directories have no per-directory README (convention is an open owner decision, backlog line 10); tests/README.md names no book test file, so nothing in it went stale with this card
- [Commit] success commit 233678f (the implementation commit — cycle 1 passed with no fix and no README change, so /commit had nothing further to stage; meta/ excluded). Card stays review until done.
- [G-3] 2026-10-03 — ⚠ OWNER-PENDING at merge: the owner chose "merge now, I'll check later" (answered to the dispatcher). Renders: ~/Documents/nonogram-reviews/CARD-159/ (after-* from 233678f, before-* from main 47a5204). If the check finds a problem, it becomes a follow-up card. Not recorded as ✓.
- [Merged] 2026-10-03 — 7101fbf into main (--no-ff). Merge gate: rebase was a no-op (main still at 47a5204 = branch base), so the merged tree is the one that passed the full suite (400s; only the 2 baseline failures); not re-run — the wave-30 smoke test runs next. Deferral scan: 0 hits. Trace write-back: FR-038 (2), FR-030 (1); statuses stay `partial`. F-004 fixed at close-out (meta/design/components.md no longer claims Print setup carries hand-written "Step 1 of 4"). F-001/F-002/F-003/F-005 captured to backlog.
