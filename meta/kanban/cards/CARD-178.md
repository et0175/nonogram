# CARD-178: A book reopened in inches never shows a trim outside the stated limits

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/178-reopen-inches-inside-limits
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-05 (IDEA-103, CARD-174 review F-003)
**Idea:** IDEA-103
**Wave:** 34
**Depends on:** —
**Touches:** src/nonogram/admin/print_specs.py, src/nonogram/admin/app.py, tests/test_print_specs.py, tests/test_book_trim_persistence.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (read on main 1ebf337).** When the unit preference is
inches, `app.py:setup_print` (lines 3191-3196) fills the trim fields with
`PrintSpecValidator.cm_to_inches(stored_cm)` (`print_specs.py:107`). That is
`f"{cm / 2.54:.2f}"`, so it rounds to the nearest hundredth. The Limits box
and the inch refusals read `PrintSpecValidator.trim_limits()`
(`print_specs.py:147`, CARD-174), which rounds **inward**: maxima down, the
minimum up (3.94 / 11.81 / 18.89 in).

So a book stored at 48.00 cm high reopens showing **18.90 in**, beside a
Limits box that says the maximum is 18.89 in. An untouched Save is still
accepted. `_submitted_trim_cm` (`app.py:2905`, comparison at line 2941) sees
the page's own string come back and keeps the stored 48.00 cm (CARD-136
F-002). But if the owner types 18.90 themselves, it converts to 48.01 cm and
is refused.

Verified by enumerating every stored value on a 0.01 cm grid inside the KDP
bounds (10.00-30.00 width, 10.00-48.00 height). Exactly one value displays
outside its limit: height 48.00 cm shows 18.90 in, which converts back to
48.01 cm and fails `validate_trim_size`. Every other value displays inside the
limits, and its inch figure converts back to an accepted trim.

**Target behaviour.**

1. Add one axis-aware display conversion in `print_specs.py`, next to
   `trim_limits()`. Suggested shape:
   `PrintSpecValidator.trim_inches_shown(cm: str, axis: "width" | "height") -> str`.
   It returns `cm_to_inches(cm)`, except when the stored cm is at or inside
   that axis's limits and the rounded figure lies outside the matching
   `trim_limits()` inch figure. Then it returns that limit figure instead
   (`max_width_in`, `max_height_in` or `min_in`). Derive everything from
   `trim_limits()`; do not write 18.89 anywhere.
2. A stored value **outside** the limits (a legacy row) keeps today's plain
   `cm_to_inches` figure. Do not pull it inward: that would hide a bad stored
   trim behind a valid-looking one.
3. `setup_print`'s inches reopen (lines 3193-3194) uses the new function for
   width and height.
4. `_submitted_trim_cm` compares the submission against **the same** shown
   form. It takes the axis and calls the new function instead of
   `cm_to_inches` at line 2941. Both callers at lines 3069-3070 pass their axis.
   This is required: if the page shows 18.89 but the comparison still builds
   18.90, an untouched Save stops matching and stores 47.98 cm. That is the
   silent drift CARD-136 F-002 fixed.
5. `cm_to_inches` itself does not change. It stays a plain nearest-hundredth
   conversion. Its only callers are the two sites above and
   `tests/test_book_scaffolding.py`. After this card the app no longer calls it
   for display. No other code converts cm to inches for display: `book_kdp.py`
   and `book_page_spec.py` have their own `_CM_PER_INCH` for KDP trim matching,
   and the template's `setDefaultSize()` JS writes fixed strings.

Result: a book stored at 48.00 cm reopens showing 18.89 in. An untouched Save
keeps 48.00 cm. Typing 18.89 is accepted. Every other stored value on the
grid displays exactly as today.

## Acceptance criteria

- **AC-1:** Given a book stored at 21.59 x 48.00 cm and the inches preference, when Print setup is reopened, then the fields show `8.50` and `18.89`, and the page does not contain `18.90`.
  *test: TestBookTrim_ReopenInInchesStaysInsideLimits (in tests/test_book_trim_persistence.py)*
- **AC-2:** Given that page, when it is saved untouched (five times in a row), then the stored columns stay exactly `21.59` x `48.00`. Typing `18.89` for the height on a book stored at a different height stores 47.98 cm.
  *test: TestBookTrim_ReopenInInchesStaysInsideLimits (in tests/test_book_trim_persistence.py)*
- **AC-3:** For every stored cm value on a 0.01 grid inside each axis's limits (the test asserts at least 5,800 cases), the shown inch figure lies inside that axis's `trim_limits()` inch figures, and `inches_to_cm(shown)` passes `validate_trim_size`. It checks with the validator, not by re-deriving the clamp.
  *test: PropertyTest_TrimInchesShown_InsideLimitsAndAccepted (in tests/test_print_specs.py)*
- **AC-4:** Over the same grid, the shown figure equals `cm_to_inches(stored)` for every value except height 48.00 cm. A stored value outside the limits (for example 50.00 cm high, 9.00 cm wide) shows the plain `cm_to_inches` figure.
  *test: PropertyTest_TrimInchesShown_InsideLimitsAndAccepted (in tests/test_print_specs.py)*
- **AC-5:** With the KDP bound constants moved to seeded random values on a 0.01 cm grid (monkeypatched, as CARD-174's moved-bounds corpus does), AC-3's two properties still hold. So the clamp follows `trim_limits()` and is not a literal.
  *test: PropertyTest_TrimInchesShown_InsideLimitsAndAccepted (in tests/test_print_specs.py)*
- **AC-6:** For stored values at each limit (10.00 / 30.00 / 48.00 cm) and one inside value, an untouched inches resubmission through the route stores the original cm exactly, in memory, sqlite and postgres `nonogram_test` modes.
  *test: TestBookTrim_ReopenInInchesStaysInsideLimits (in tests/test_book_trim_persistence.py)*

## Guardrails

- G-1: KDP bounds and verdicts do not move. `MIN_TRIM_CM` / `MAX_TRIM_*_CM` (`book_page_spec.py`), `validate_trim_size` and `trim_limits()` (3.94 / 11.81 / 18.89 in) are unchanged. CARD-174's `TestTrimRefusal_StatedInchLimitIsAccepted`, `TestTrimRefusal_ExactCmBoundaryInInchesIsAccepted`, `TestTrimRefusal_CmWordingUnchanged`, `TestPrintSetup_InchesRefusalSpeaksInches` and `TestPrintSetup_LimitsBoxAgreesWithRefusals` stay green.
- G-2: Conversion does not change. `inches_to_cm` and `cm_to_inches` keep their rounding and output: 8.5 x 11 in still stores 21.59 x 27.94 cm, and `cm_to_inches("48.00")` still returns `"18.90"`. `tests/test_book_scaffolding.py` stays green unchanged.
- G-3: CARD-136 F-002 holds. The untouched-field discriminator stays string equality with the shown form, with no tolerance window. `TestBookTrim_ReopeningInInchesDoesNotShiftIt` (15.00 x 20.00 cm shows 5.91 x 7.87 in) stays green unchanged.
- G-4: CARD-173's path does not change. `_stored_trim_cm` and the unreadable-column fallback to cm in `setup_print` (`except ValueError`) stay as they are. `TestBookTrim_ThePageCarriesOneUnit` stays green.
- G-5: A refused submission still stores nothing (AC-197). It carries the owner's entries back exactly as typed, not re-clamped.
- G-6: The cm reopen, the template (`book_setup_print.html`), the refusal wording and the success flash (in cm) do not change.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-178` (52 rules). A projection — fix the source artifact, never this list._

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
- **ADR:** — (no ADR on display rounding); CON-018 (Book 1 print profile defaults, unchanged)
- **Components:** COMP-009 (admin panel)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Screen:** Print setup (`/book/<id>/setup-print`) reopened with the inches preference. The trim height field for a book stored at 48.00 cm.
- **Owner-visible change:** that field now reads 18.89 instead of 18.90. Nothing else on the page changes.
- **Renders:** ~/Documents/nonogram-reviews/CARD-178/ (owner visual check: before/after of a 21.59 x 48.00 cm book reopened in inches, showing the field beside the Limits box; 1440 and 390)

## Worktree notes

- [Origin] Roadmap wave 1: IDEA-103 (CARD-174 review F-003, dismissed there as out of scope because CARD-174's G-3 froze `cm_to_inches` rounding). This card changes how the stored trim is **displayed** in inches.
- [Decision, scoped] The brief allowed changing `cm_to_inches` rounding here. The card instead leaves `cm_to_inches` as a pure conversion and adds an axis-aware display function. Reason: `cm_to_inches` has no axis, so it cannot know which limit to round toward. A global "round inward" has no meaning for an interior value. Enumeration shows only 48.00 cm needs a different figure. If the owner prefers to change `cm_to_inches` itself, AC-4 and G-2 must be rewritten.
- [Facts] Callers of `cm_to_inches`: `app.py:2941` (inside `_submitted_trim_cm`, def at 2905, called at 3069-3070), `app.py:3193-3194` (inches reopen in `setup_print`, def at 2948), and `tests/test_book_scaffolding.py:14,18,34` (approx/raise checks only). There are no other callers in src/ or tests/.
- [Facts] Enumeration on main 1ebf337 (0.01 cm grid, both axes, KDP bounds) found exactly one bad value: height 48.00 cm shows 18.90 in, which converts back to 48.01 cm and is refused. Width 30.00 shows 11.81 (accepted). Minimum 10.00 shows 3.94, rounded up, which is already inward.
- [Facts] Today an untouched Save of the 18.90 page is accepted only because `_submitted_trim_cm` matches the page's own string and keeps the stored cm. Item 4 keeps that match working once the shown string becomes 18.89.
- [Behaviour note] After this card, typing exactly `18.89` on a book stored at 48.00 cm keeps 48.00 cm and does not store 47.98 cm. This is the same CARD-136 rule that today keeps 15.00 cm when 5.91 is typed. AC-2's 47.98 case therefore uses a book stored at a different height.
- [Tests] `_shown_trim`, `_set_trim`, `_prefer`, `_page` and `_stored_columns` already exist in `tests/test_book_trim_persistence.py` for the route tests. CARD-174's moved-bounds corpus in `tests/test_print_specs.py` (class `TestTrimRefusal_StatedInchLimitIsAccepted`, line 426) shows how to monkeypatch the bounds for AC-5.
- [AC cross-check] Every AC was re-read against the body. AC-2's "typing 18.89 stores 47.98" was first written for the 48.00 book. That contradicted item 4 (the shown form is kept). The AC was changed to use a book stored at a different height, so AC and body now agree.
