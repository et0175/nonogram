# CARD-129: Finalise refuses when the page count needs a larger KDP gutter than the stored one

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/129-finalise-kdp-gutter-check
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-15 (finalise gutter check, ADR-0036 clarification; AC-179 of FR-030; closes Increment 15)
**Idea:** —
**Wave:** 27
**Depends on:** CARD-128, CARD-123, CARD-134
**Touches:** src/nonogram/admin/book_kdp.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_finalise_gutter.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

ADR-0036 clarification ("Gutter margin and page count") breaks the circularity by
refusing rather than iterating. The book **always lays out with its stored gutter**,
and finalise checks the result.

1. **`admin/book_kdp.py`**: `kdp_min_gutter_cm(page_count)` returns 0.375 in (0.9525 cm)
   up to 150 pages and 0.5 in (1.27 cm) for 151–300 (FR-030, CON-018). Above 300 pages
   the requirements are silent. Refuse with "KDP gutter table not modelled above 300
   pages" rather than guess, and record it.
2. **Finalise** (`/book/<id>/finalize`): take the **actual** page count of the
   generated **interior PDF** (guide, dividers, one- and two-up pages, SOLUTIONS
   divider, and the **packed answer-key pages** of FR-042; the count CARD-127/128/134
   report). The cover is a separate file and is **never counted** (FR-043, decided
   2026-09-22 (d); AC-288).
   The answer key is part of the count (AC-271). It is what brings a 150-puzzle book
   back from 300+ pages to the ~120–190-page model. If the stored gutter is below
   `kdp_min_gutter_cm(count)`, **refuse**, and name KDP's minimum for that page band
   against the stored value. **The stored gutter is never changed** (no silent raise).
   (The (c) open question — PDF pages vs KDP's count without the cover — is closed:
   the interior PDF's page count, cover excluded.)
3. The finalise summary shows the page count, the page count before pairing, and the
   answer-key page count, for the checkpoint.

## Increment 15 checkpoint (this card closes it)

The PDF of a real curated book on the Book 1 profile runs divider "Easy", two-up and
single pages, divider "Medium", …, with bands "Puzzle 1 · Easy" / "Puzzle 2 · Easy" on
the first shared page. A 12+12 pair measures 7.39 mm (±0.05 mm) on the printed page, and
the upper slot's top edge sits on the same pixel row as a single 20×20 page's drawing.
The page count before and after pairing is reported for that book, together with its
answer-key page count (6-up / 4-up; a 150-answer book with 90 answers ≤20 first takes
30 answer pages, not 150; the three-level default plan takes 31 after one SOLUTIONS
page). The page count is the interior's; the cover file is not counted. A book whose count, answer key included, crosses 150 pages
with a stored 0.375 in gutter is refused at finalise with the KDP reason. Rendered pages go to `~/Documents/nonogram-reviews/CARD-129/` for the owner's
eye.

## Acceptance criteria

- **AC-179** (reworded 2026-09-22 (d)) — given a book storing a 0.60 cm gutter margin whose interior PDF runs to 180 pages, when the book is finalised, then finalise is refused, naming KDP's 1.27 cm (0.5 in) minimum for 151-300 pages against the stored 0.60 cm; the stored gutter is not changed.
  *test:* `TestBookFinalise_RefusesGutterBelowKdpMinimumForPageCount`
- **AC-271** (FR-042, added 2026-09-22 (c); reworded (d)) — given a book storing a 0.95 cm (0.375 in) gutter margin whose interior pages before the answer key (guide page through the SOLUTIONS divider) number 125 and whose 150 answers lay out on 30 answer pages (155 interior pages; the separate cover file not counted), when the book is finalised, then finalise is refused, naming KDP's 1.27 cm (0.5 in) minimum for 151-300 pages — the answer-key pages are counted.
  *test:* `TestBookFinalise_PageCountIncludesAnswerKeyPages`
- **AC-288** (FR-043, added 2026-09-22 (d)) — given a book storing a 0.95 cm (0.375 in) gutter margin whose interior PDF is exactly 150 pages, when the book is finalised, then finalise is not refused on the gutter — 150 interior pages is within KDP's 0.375 in range; the cover file does not make it 151.
  *test:* `TestBookFinalise_PageCountExcludesCoverFile`
- CK-1 (Increment 15 checkpoint) — given a book with a stored 0.375 in gutter whose page count crosses 150, when it is finalised, then it is refused with the KDP reason; at ≤ 150 pages it is accepted.
  *test:* `TestBookFinalise_GutterCheckAtHundredFiftyPageBoundary`

## Engineering constraints

- **EC-034** (consistency, INV-013; finalise page-count half, added 2026-09-22 (d)) — For any book (any members, levels, pairing, answer-key layout and cover or no cover) and every export route, the interior PDF holds no cover page, its page 1 is the guide page, each page's parity is its 1-based position in the interior (page 1 odd, right-hand), the page count finalise checks equals the interior's page count, and exactly one cover file of one trim-size page is produced beside it — for every book, not only the measured examples.
  *test:* `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` — _extend CARD-135's property: the page count finalise reads equals the interior PDF's page count for every generated book, and the cover never changes it._

## Guardrails

- G-1: The stored gutter is never raised or rewritten by finalise (ADR-0036 clarification; AC-179 "the stored gutter is not changed").
- G-2: Layout always uses the stored gutter. There is no iteration between page count and layout.
- G-3: The admin panel fits no cells itself (ADR-0036/R2). Do not edit `src/nonogram/export/**`.
- G-4: No schema change. Do not edit `src/nonogram/db/**` or `migrations/**`.

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

- **FR:** FR-030 (AC-179), FR-042 (AC-271), FR-043 (AC-288, EC-034 page-count half)
- **NFR:** —
- **CON:** CON-018
- **ADR:** ADR-0036
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ — brief.md, tokens.css, components.md
- **UI components:** Flash / Alert (reuse — danger, the KDP refusal), StatBlock (reuse — page count before/after pairing)
- **Screens:** /book/<id>/finalize
- **Standards:** forge:engineering-standards §11

## Worktree notes

—

- [Handover from CARD-115, 2026-09-22] AC-179's illustrative 0.60 cm gutter is below book_page_spec's 6.35 mm floor, so the builder refuses it before finalise can name the KDP band. Reconcile here (this card's checkpoint already uses the KDP-legal 0.375 in).
