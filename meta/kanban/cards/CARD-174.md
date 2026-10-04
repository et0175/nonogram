# CARD-174: Trim refusals and the Limits box speak the same inches

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/174-trim-refusals-in-inches
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (IDEA-049 + IDEA-048, CARD-159 review F-005 + F-001)
**Idea:** IDEA-049, IDEA-048
**Wave:** 33
**Depends on:** —
**Touches:** src/nonogram/admin/print_specs.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_setup_print.html, tests/test_print_specs.py, tests/test_book_workflow_steps.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (read on main 2e071b4).** On Print setup, an inches
submission is converted to cm before it is checked. `app.py:setup_print`
(inches branch around line 3043) calls `_submitted_trim_cm` (line 2881), which
calls `PrintSpecValidator.inches_to_cm`. The cm strings then go to
`PrintSpecValidator.create_spec` (line 3066), which calls `validate_trim_size`
(`print_specs.py:139`). Its three bound refusals are written only in cm
(`print_specs.py:165`, `:172`, `:178`):

- `Trim size must be at least 10.0 cm in both dimensions`
- `Trim width cannot exceed 30.0 cm (Amazon KDP limit)`
- `Trim height cannot exceed 48.0 cm (Amazon KDP limit)`

So typing 12 x 11 in shows "Trim width cannot exceed 30.0 cm". The owner has to
convert units in their head, and the message never says what they typed.

Separately, the Limits box on the same page (`book_setup_print.html:93-100`)
hard-codes its inch values: "Minimum 10 × 10 cm (3.94 × 3.94 in)", "Maximum
width 30 cm (11.81 in)", "Maximum height 48 cm (18.90 in)". 18.90 in converts
to 48.01 cm, which the server refuses (CARD-159 F-001 / IDEA-048). Since
CARD-159 dropped the browser min/max, this box is the page's only statement of
the inch limits.

**Target behaviour.**

1. A bound refusal for an **inches** submission states the limit in inches and
   quotes the submitted value as the owner entered it (stripped), in inches.
   Example shape: `Trim width cannot exceed 11.81 in (Amazon KDP limit); you
   entered 12 in`. Keep the existing message prefixes ("Trim width cannot
   exceed", "Trim height cannot exceed", "Trim size must be at least"). The
   existing route test checks the prefix.
2. The inch limit printed must itself be accepted by the server. Round a
   maximum **down** and a minimum **up** to two decimals: max width 11.81 in
   (30 cm = 11.811 in), max height 18.89 in (48 cm = 18.898 in), minimum
   3.94 in (10 cm = 3.937 in). Do not print 18.90 in: it converts to 48.01 cm,
   which is refused. Derive these from `MIN_TRIM_CM` / `MAX_TRIM_WIDTH_CM` /
   `MAX_TRIM_HEIGHT_CM`. Do not hard-code them.
3. A **cm** submission gets exactly today's messages, character for character.
4. `BookManager._checked_print_spec` (`book_manager.py:908`) calls
   `validate_trim_size` with cm values only. It keeps today's cm wording.
   Suggested shape: an optional keyword on `validate_trim_size` / `create_spec`
   (for example `unit="cm"` plus the entered strings), defaulting to today's
   behaviour. Another shape is fine if both callers keep working unchanged.
5. **One source for the inch limits (IDEA-048).** Put the always-accepted
   inch limits (and their cm forms) in one place in `print_specs.py`, for
   example a `PrintSpecValidator` method or constant returning
   min / max-width / max-height in cm and in inches. The refusals in item 1
   and the Limits box both read from it. `setup_print` passes it into the
   template context. The template prints those values and no literal numbers.
   After this the box reads 3.94 / 11.81 / **18.89** in. Its cm figures and
   its wording otherwise stay as they are.

Which field the refusal quotes: the min refusal covers both dimensions, so
quote the field(s) that failed. The non-numeric refusal for inches is already
in inches (`Invalid inch value: …`, raised by `inches_to_cm`). Leave it alone.

## Acceptance criteria

- **AC-1:** Given Print setup in inches, when 12 x 11 in is submitted, then the re-rendered page's error says `11.81 in` and `12 in`, contains no `cm` limit, and nothing is stored.
  *test: TestPrintSetup_InchesRefusalSpeaksInches (in tests/test_book_workflow_steps.py)*
- **AC-2:** Given inches, when the height is over the limit (e.g. 8.5 x 19 in) or a side is under it (e.g. 3 x 11 in), then the error states `18.89 in` or `3.94 in` respectively and quotes the entered value.
  *test: TestPrintSetup_InchesRefusalSpeaksInches (in tests/test_book_workflow_steps.py)*
- **AC-3:** Every inch limit the refusal states is accepted when submitted: 11.81 x 18.89 in and 3.94 x 3.94 in each store and redirect. Checked against `inches_to_cm` + `validate_trim_size`, and through the route.
  *test: TestTrimRefusal_StatedInchLimitIsAccepted (in tests/test_print_specs.py)*
- **AC-4:** Given cm, when 31 x 20, 20 x 49 or 9 x 20 cm is submitted, then each error is byte-identical to today's three cm messages (pinned as literals in the test, not rebuilt from the constants).
  *test: TestTrimRefusal_CmWordingUnchanged (in tests/test_print_specs.py)*
- **AC-5:** `validate_trim_size(width_cm, height_cm)` called the way `BookManager` calls it (no unit) returns today's cm messages. A storage refusal still reads `a book's trim cannot be stored: Trim width cannot exceed 30.0 cm …`.
  *test: TestTrimRefusal_CmWordingUnchanged (in tests/test_print_specs.py)*
- **AC-6:** Given Print setup rendered (in cm and in inches), then the Limits box shows `3.94`, `11.81` and `18.89` in, never `18.90`, and each inch value equals the inch limit the matching refusal states. The test reads both from the rendered page and the refusal, and checks the shared source returns those values, so a literal put back in the template fails. Every value shown is accepted when submitted (AC-3).
  *test: TestPrintSetup_LimitsBoxAgreesWithRefusals (in tests/test_book_workflow_steps.py)*

## Guardrails

- G-1: KDP bounds do not move. `MIN_TRIM_CM` / `MAX_TRIM_*_CM` in `book_page_spec.py` stay the one statement of them. The same submissions are accepted and refused as before (only the wording changes). `TestPrintSetup_InchesTrimIsReachable` and `TestTrimValidation_RefusesNonFiniteValues` stay green.
- G-2: Stay off CARD-173's path (unreadable stored specs). Do not change `_stored_trim_cm`, the reopen-in-cm fallback in `setup_print` (the `except ValueError` around line 3165), or the stored-value comparison in `_submitted_trim_cm`.
- G-3: Conversion and storage do not change. `inches_to_cm` / `cm_to_inches` keep their rounding, so 8.5 x 11 in still stores 21.59 x 27.94 cm. An untouched inches field still keeps the stored cm (CARD-136 F-002, tests in `tests/test_book_trim_persistence.py`). The success flash stays in cm.
- G-4: A refused submission still stores nothing (trim, plan or ink mode; AC-197 posture) and carries the entries back in the unit they were typed in.
- G-5: In `book_setup_print.html`, change only the Limits box's numbers (to read from the shared source). The trim inputs (no browser min/max since CARD-159, `step="0.01"`, `required`), the unit radios, the plan table and the stepper/prose stay as they are. `TestPrintSetup_InchesTrimIsReachable` and `TestBookStepPages_ProseAgreesWithTheStepper` stay green.
- G-6: The blank-field refusal (`_blank_trim_error`) and the margin and ink-mode refusals keep their wording.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-174` (52 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniq… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when th… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws n… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on dens… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzz… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pur… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with th… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attributi… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the gr… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle neve… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membersh… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percent… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm toolcha… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a paramet… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No ot… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) nev… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement,… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is a… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns i… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the bo… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-030 (trim-aware book; the trim of record), FR-038 (re-entry step workflow / Print setup); AC-197 (a refused submission stores nothing)
- **ADR:** — (no ADR on refusal wording); CON-018 (Book 1 print profile defaults, unchanged)
- **Components:** COMP-009 (admin panel)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Screen:** Print setup (`/book/<id>/setup-print`): the error flash after a refused trim (in inches and in cm) and the Limits box
- **Renders:** ~/Documents/nonogram-reviews/CARD-174/ (owner visual check: before/after of a refused 12 x 11 in submission, an unchanged cm refusal, and the Limits box showing 18.89 in; 1440 and 390)

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-049 (CARD-159 review F-005). Trim refusals are worded in cm after an inches submission. CARD-159's G-1 kept `print_specs.py` frozen, so this was deferred. IDEA-048 (CARD-159 F-001, Limits box "18.90 in") folded in on the coordinator's instruction, 2026-10-04, so the page and the refusals agree.
- [Decision, default pending owner confirmation] The inch limits are rounded so each one is accepted: maxima rounded down, the minimum rounded up, to 2 dp (11.81 / 18.89 / 3.94 in). The alternative is to show the exact limit with cm next to it, e.g. "18.89 in (48 cm)". If the owner picks that, only the wording changes. The one-source rule (item 5) still holds.
- [Facts] No test pins the Limits box text today (grep of tests/ for "18.90 in", "Maximum height 48", "Limits." finds nothing). The box sits at `book_setup_print.html:93-100` and has no template variables yet.
- [Facts] The cm messages are at `print_specs.py:165/172/178`. The inches conversion happens in `app.py:_submitted_trim_cm` (2881) before `create_spec` (3066), so `validate_trim_size` sees only cm today. The unit is known in `setup_print` as `unit` (`request.form.get("unit", "cm")`), along with the raw `width_input` / `height_input`.
- [Facts] The existing test that pins the current wording is `tests/test_book_workflow_steps.py:1336`, `assert "Trim width cannot exceed" in body` (in `TestPrintSetup_InchesTrimIsReachable.test_the_server_still_refuses_an_inches_trim_beyond_kdp`). Keep the prefix and it stays green. No test pins the min/height wording. `tests/test_print_specs.py:51` pins only `NOT_NUMERIC`.
- [Facts] Boundary arithmetic through `inches_to_cm` (2-dp): 11.81 in → 30.00 cm (accepted), 11.82 → 30.02 (refused); 18.89 → 47.98 (accepted), 18.90 → 48.01 (refused); 3.94 → 10.01 (accepted), 3.93 → 9.98 (refused).
- [Related] IDEA-050 (route tests for below-min/zero/negative trims; wave 5) overlaps AC-2's below-min case. It is not a dependency. Do not take on its New-book alert half.
