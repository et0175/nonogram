# CARD-127: Two-up pages in the book PDF — walk the order, pair same-tier fitting neighbours, never reorder

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/127-book-two-up-pages
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-15 (COMP-009 half of FR-040)
**Idea:** —
**Wave:** 25
**Depends on:** CARD-117, CARD-125
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_two_up.py, tests/property/test_book_pairing.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

1. **The pairing walk** in `book_pdf_generator.py` goes through the book order from the
   first puzzle. It offers puzzle *i* and puzzle *i+1* to CARD-125's
   `compute_pair_layout` **only when their tiers are equal**. If the call returns a
   pair, both go on one page and the walk moves to *i+2*. Otherwise *i* prints alone and
   the walk moves to *i+1*. The last puzzle of an odd run prints alone. The walk
   **never reorders**: concatenating the pages front to back yields the book order
   exactly. The walk decides only **which neighbours to offer**. The shared cell and the
   slot positions come from COMP-007 (ADR-0036/R2).
2. **Two-up page composition.** Each slot sits under its own band, "Puzzle N · Tier"
   (CARD-117's band renderer). The upper slot is the earlier puzzle, and its drawing top
   edge is on the same pixel row as a single page's (EC-022). Puzzle numbers stay
   1..n in print order.
3. **Answer key.** Not this card. Since 2026-09-22 (c) the answer key is FR-042's packed
   6-up / 4-up pages, which CARD-134 builds in the same wave (and in the same file,
   `book_pdf_generator.py`, so `run` serializes the two). Leave the answer-page code
   path as you find it. Answer-key level headings are CARD-128.
4. **Page-count saving.** Report the page count before and after pairing (the number
   the owner's "big books" research asks for) as a value returned by the generator, so
   CARD-128/129 and the checkpoint can print it.
5. Order input: this card consumes the stored order as CARD-126 leaves it. Level
   grouping at print time and dividers are CARD-128. Until then pairing works on
   whatever order is stored, and the tier-equality rule already holds.

## Acceptance criteria

- **AC-242** (INV-010) — given a Book 1 profile book whose order starts with two easy 10x10 puzzles, each with 4-deep row- and column-clue gutters (combined drawing height 28 cells), when the book PDF is generated, then both puzzles print on one page at a 7.5 mm shared cell (the page fit of 8.44 mm capped at the standard cell).
  *test:* `TestBookPdf_TwoSmallSameTierNeighboursShareAPage`
- **AC-243** (INV-010) — given a Book 1 profile book whose order starts with two easy 12x12 puzzles, each with 4-deep row- and column-clue gutters (combined drawing height 32 cells), when the book PDF is generated, then both puzzles print on one page at a 7.39 mm shared cell (+/- 0.05 mm; 236.35 mm over 32 cells).
  *test:* `TestBookPdf_TwelvePairSharesPageBelowStandardCell`
- **AC-244** (INV-010) — given a Book 1 profile book whose order has an easy 15x15 puzzle with a 5-deep column-clue gutter followed by an easy 10x10 puzzle with a 3-deep column-clue gutter (combined drawing height 33 cells), when the book PDF is generated, then both puzzles print on one page at a 7.16 mm shared cell (+/- 0.05 mm) — at or above the 7.0 mm two-up minimum.
  *test:* `TestBookPdf_PairJustAboveTwoUpMinimumShares`
- **AC-245** (INV-010) — given the same book but the 15x15 puzzle's column-clue gutter is 6 deep (combined drawing height 34 cells, 6.95 mm shared cell), when the book PDF is generated, then the two puzzles print on two separate pages.
  *test:* `TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare`
- **AC-246** (INV-010) — given a Book 1 profile book whose order has an easy 15x15 puzzle with a 5-deep column-clue gutter followed by an easy 12x12 puzzle with a 4-deep one (combined 36 cells, 6.57 mm), when the book PDF is generated, then the two puzzles print on two separate pages.
  *test:* `TestBookPdf_FifteenPlusTwelveDoesNotPair`
- **AC-247** (INV-010) — given a Book 1 profile book whose order has an easy 22-wide x 10-tall puzzle with a 6-deep row-clue gutter (28 cells across, at most 6.92 mm on the 193.7 mm usable width) followed by an easy 10x10 puzzle with 3-deep gutters, when the book PDF is generated, then the two puzzles print on two separate pages — the pair fits the height but the wide puzzle's drawing does not fit the width at 7.0 mm.
  *test:* `TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare`
- **AC-248** (INV-010) — given a Book 1 profile book whose last easy puzzle and first medium puzzle are both 10x10 with 4-deep gutters and adjacent in the book order, when the book PDF is generated, then the two puzzles print on two separate pages.
  *test:* `TestBookPdf_DifferentTiersNeverPair`
- **AC-249** (INV-010) — given a Book 1 profile book ordered easy 10x10 A, easy 20x20 B (8-deep gutters), easy 10x10 C, where A and C would fit together, when the book PDF is generated, then A and C print on separate pages.
  *test:* `TestBookPdf_PairingNeverReordersToFindAPartner`
- **AC-250** (INV-010) — given a Book 1 profile book whose order has three adjacent easy 10x10 puzzles with 4-deep gutters, puzzles 1, 2 and 3, when the book PDF is generated, then puzzle 3 prints alone on its own page, after the page puzzles 1 and 2 share.
  *test:* `TestBookPdf_OddPuzzleOutPrintsAlone`
- **AC-251** — given the two-up page of AC-242 holding the book's puzzles 1 and 2, when its bands are read, then the upper band reads "Puzzle 1 · Easy" and the lower band reads "Puzzle 2 · Easy".
  *test:* `TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand`
- **AC-252** — given a Book 1 profile book holding the two-up page of AC-242 and a single-puzzle page with a 20x20 puzzle, when the book PDF is generated, then the upper puzzle's drawing on the two-up page starts on the same pixel row as the 20x20 puzzle's drawing.
  *test:* `TestBookPdf_TwoUpUpperSlotSharesFixedTopEdge`

## Engineering constraints

- **EC-027** (consistency, INV-010) — For any book order of any length, tiers and clue depths, the pages produced hold one or two puzzles each; a page holds two only when their tiers are equal, they are consecutive in the book order and fit at a shared cell of at least 7.0 mm; a puzzle that could pair with its successor under that rule is never left alone by the in-order walk; and concatenating the pages' puzzles front to back yields the book order exactly — for every order, not only the measured examples.
  *test:* `PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly`
- **EC-022** (consistency) — For any puzzle extent of 10..30 per side and any clue depth, the book's puzzle page is portrait, the grid is drawn unrotated (width across the page, height down it), and the drawing's top edge — the upper puzzle's on a two-up page — lies at one fixed offset (top margin plus title band) from the top of the trim, so that offset never varies between puzzle pages of a book.
  *test:* `PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent` (CARD-116 — add two-up pages to its corpus)

## Guardrails

- G-1: The admin panel decides only which neighbours to offer. It fits no shared cell and places no slot geometry itself (ADR-0036/R2).
- G-2: Pairing is decided at PDF time and nothing is stored (Increment 15 Rollback). Do not edit `src/nonogram/db/**`, `migrations/**` or `src/nonogram/admin/book_manager.py`.
- G-3: CLI and web A4 output stay byte-identical (CON-019). Do not edit `src/nonogram/export/**`; CARD-125's call is consumed as delivered.
- G-4: Do not edit `src/nonogram/admin/book_proof.py`, `src/nonogram/admin/templates/book_setup_print.html`, `src/nonogram/admin/templates/book_detail.html`, `src/nonogram/admin/templates/books_list.html` or `src/nonogram/admin/templates/_stepper.html`. They are owned by CARD-118 / CARD-130 this wave.

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
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)

## Architecture context

- **FR:** FR-040
- **NFR:** NFR-008
- **ADR:** ADR-0036, ADR-0037
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
