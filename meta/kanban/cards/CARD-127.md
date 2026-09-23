# CARD-127: Two-up pages in the book PDF — walk the order, pair same-tier fitting neighbours, never reorder

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/127-book-two-up-pages
**Worktree:** ../PythonProject4-CARD-127
**Source:** meta/architecture/handoff.md#increment-15 (COMP-009 half of FR-040)
**Idea:** —
**Wave:** 25
**Depends on:** CARD-117, CARD-125
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_two_up.py, tests/property/test_book_pairing.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-23
**Closed:** 2026-09-23
**Actual:** 1d
**Merge commit:** 679e78a
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
   CARD-128/129 and the checkpoint can print it. Both counts are **interior** page
   counts: the cover is a separate file and never counted (FR-043, CARD-135; 2026-09-22
   (d)). Each page's parity comes from its interior position, so a pair that saves a
   page flips the parity of every later page — expected, not a defect.
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
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the book's page count is the interior's; the cover is … (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-040
- **NFR:** NFR-008
- **ADR:** ADR-0036, ADR-0037
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

- [Handover from CARD-125, 2026-09-22] Call compute_pair_layout(earlier, later, spec for THAT page's parity). None = print each alone with compute_layout; otherwise draw .upper/.lower and call header_band(slot) for each. It does NOT decide pairing (tier, adjacency, the walk), puzzle numbers, band text or PDF composition. A slot's usable_bottom is where the NEXT band starts, not the page margin. Open: the lower slot is anchored to the bottom margin, so spare height falls BETWEEN the puzzles (F-002, queued to the architect) — settle before pinning PDF geometry.

### CARD-127 — implementation summary (2026-09-23)

**The walk.** `BookPDFGenerator.puzzle_pages(payloads, first_page=2)` is the whole
of FR-040's decision in `book_pdf_generator.py`. It walks the drawable payloads in
book order; when puzzle *i* and *i+1* have the same **tier of record**
(`_pairable_tier`, i.e. `difficulty.tier_of_record` of the stored text — a row
whose grade is unreadable has no tier and never pairs, not even with another
such row), it offers the two clue sets to CARD-125's `compute_pair_layout` on the
spec of **the page the walk has reached**. A `PairLayout` back puts both on that
page and advances by 2; `None` prints *i* alone and advances by 1. Greedy,
forward-only, never reorders. It returns a list of `PuzzlePagePlan(page_number,
numbers, pair)` — `numbers` are the 1-based print numbers, upper slot first.

**An exception from `compute_pair_layout` is not `None`** (review F-001). `None`
means *measured, and the shared cell is too small*; a raise means the member
cannot be measured at all (clue sets that disagree about the grid) or the spec
is not a book page. The walk therefore takes `ids` — parallel to `payloads`,
passed by `interior()` — and re-raises as
`RuntimeError("puzzle <ids> could not be laid out: …") from e`, naming both
members of the offered pair. Without it, a malformed row aborted the export
with a bare `ValueError` reading only "first:"/"second:" whenever it had a
same-tier neighbour — which, since INV-009 groups the order by tier, is the
common case — while the same row alone was named. Declining to pair instead
would have hidden it until draw time and made `None` mean two different things.
Both stages now name the id: "could not be laid out", "could not be drawn".

**Composition.** `export/` exposes no call that draws a *given* `Layout`
(`render_image`/`render_pages` each fit their own from a payload + spec), and G-3
forbids touching `export/`, so `_two_up_page` composes the page in admin from the
numbers COMP-007 measured: `_stroke_drawing` (thin rules first, heavy last),
`_write_clues` (`anchor="mm"` on the placed centres, Pillow's default face at
`Layout.clue_font_size`) and `_set_band` (the packaged DejaVu Sans via the public
`pdf.FONT_PACKAGE`/`FONT_RESOURCE`, one piece, `anchor="lm"` at
`center_x - width/2`, the export's own shrink-to-fit ratios). No coordinate is
computed here — G-1/ADR-0036/R2 hold. Verified: the upper slot's band ink is
pixel-identical to the same puzzle's band on a single page, **and starts on the
same pixel column** (review F-005 — the comparison carries the ink box's left
edge, so a band centred on the trim rather than on its slot fails it). The two
restated fitting ratios are pinned equal to `pdf`'s by
`test_a_two_up_band_is_fitted_by_the_exports_own_header_ratios` (review F-003),
and `_set_band`'s docstring now records that it reproduces two of the export's
three fitting steps and why the third — eliding the first piece at the font
floor — cannot be reached by a one-piece band (review F-004).

**How pages are enumerated after pairing — read this, CARD-134.** See the
`[Handover]` note below.

**Page counts (item 4).** `interior_page_count(puzzle_count, puzzle_pages=None)`
— `puzzle_pages` defaults to `puzzle_count`, so the one-argument call is the
**un-paired** plan and is exactly what it was (app.py's Finalise call is
untouched; CARD-129 owns EC-034). `BookPDFGenerator.interior(puzzles)` returns a
new `Interior(pages, unpaired_page_count)` with `page_count` and `pages_saved`;
`interior_pages()` is now `interior().pages`. `BookExport` gained
`unpaired_interior_page_count` and a `pages_saved` property;
`interior_page_count` still means the real, post-pairing interior count.
The page-plan tripwire now compares the built pages against
`interior_page_count(count, len(plan))` — a plan derived from the actual walk —
and still raises `RuntimeError("interior has N pages, its page plan says M")`.
Because that puzzle-page term is now the walk's **output**, `interior()` also
checks the walk against its own **input** before drawing anything (review
F-002): `[n for e in plan for n in e.numbers] == list(range(1, count + 1))`, or
`RuntimeError("the page plan prints …, not puzzles 1..N")`. A walk that dropped
a puzzle would otherwise agree with the page-count check — the book would ship
without that puzzle and still print its answer page.

**F-002 consumed as delivered.** The lower slot is anchored to the bottom margin,
so a pair's spare height falls between the two puzzles; on the Book 1 renders that
gap is visible (see the review PDF). Per guardrail G-3 that is CARD-125's
behaviour and this card did not redistribute it. If the architect settles F-002
the other way, the fix belongs in `compute_pair_layout`, not here — nothing in
`book_pdf_generator.py` would need to change.

**SCOPE+ (files edited outside the card's Touches):**

- `SCOPE+ tests/property/test_book_pdf_geometry.py` — EC-022's named test asked for
  two-up pages in its corpus (card text). Added
  `test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_two_up_pages`
  (appended, plus one import line); and the existing `_pdf_pages` sibling now
  alternates its puzzles' tiers, and the EC-032 sibling gives its second copy a
  different tier, so each keeps one puzzle to a page — both properties are about a
  single drawing's placement, and pairing would otherwise change which page holds
  what.
- `SCOPE+ tests/property/test_book_export_interior.py` — EC-034's corpus asserted
  `1 + n + (n+1)` interior pages and `page 2 + index` per puzzle. Rewritten to an
  independent pairing walk (`_pairs`, `_puzzle_page_plan`, `_shared_cell_mm`, all
  written out in mm here) and to measuring both slots of a two-up page; counters
  assert both page make-ups occur. Review F-006: every third case is now drawn
  small and same-tier, so two-up pages land on **both** parities (9 left, 6
  right over the corpus) and the floors are `>= 5` two-up and `>= 2` per parity.
- `SCOPE+ tests/test_book_pdf.py` — `TestBookPdf_PagePlanGuardIsLive` monkeypatches
  `interior_page_count`; its lambda now takes the second argument. Review F-001
  and F-002 added the layout-time naming cases (`_unmeasurable_puzzle`, a row
  with row clues and no column clues) and the dropped-puzzle guard case.
- `SCOPE+ tests/test_book_pdf_band.py` — CARD-117's band property corpus drew
  10..15 rows with 3-deep gutters, which now pairs; its rows are 14..19 so every
  puzzle of that corpus keeps a page of its own (the comparison is whole-page).
  Two-up bands are covered by this card's own corpus instead.
- `SCOPE+ tests/helpers/two_up_ink.py` (new) — splits a two-up page at the widest
  gap between grid rules and measures each half with CARD-116's `page_ink`, so a
  slot is measured by the same helper a single page is. Its own rule threshold
  (0.25 of the page's longest run, against `page_ink`'s 0.9) is there because the
  two slots of a pair need not be the same width.

**Renders for the owner:** `~/Documents/nonogram-reviews/CARD-127/` —
`CARD-127-two-up-interior.pdf` (a 9-puzzle Book 1 book: 17 interior pages against
20 un-paired, 3 saved) and `CARD-127-interior-page-{2,3,4,5}.png`.

- [Handover to CARD-134 (the packed answer key), 2026-09-23] The answer-page code
  path is untouched: still one page per puzzle, in puzzle-number order, built by
  `BookPDFGenerator._answer_page(payload, puzzle_number, answer_page)` (the old
  `_puzzle_and_answer` is gone — it is now `_blank_page` + `_answer_page`, because
  a paired puzzle's blank page is not rendered by `render_pages` at all).
  **How pages are enumerated now.** `interior()` builds the payload list first
  (dropping unbuildable rows, which is what fixes the puzzle numbers: a puzzle's
  `N` is its 1-based index among the survivors), then calls
  `self.puzzle_pages(payloads)` **before drawing anything**, because how many
  pages the puzzles take is what puts everything after them:
  * interior page 1 — the guide page;
  * pages `2 .. 1 + len(plan)` — the puzzle pages, one `PuzzlePagePlan` each,
    `len(plan) <= len(payloads)`; `plan[k].page_number == 2 + k`;
  * page `2 + len(plan)` — the SOLUTIONS divider;
  * pages `3 + len(plan) + i` — puzzle `i+1`'s answer page (`first_answer_page`
    in the code). **This is the line you change**: replace the per-puzzle answer
    loop with the packed key's pages and make `interior_page_count`'s answer term
    (`puzzle_count + 1 if puzzle_count else 0`) the packed count, or the page-plan
    tripwire at the end of `interior()` will fire — which is the intended
    behaviour, not an obstacle.
  **Two guards you will meet, both deliberate.** Before any page is drawn,
  `interior()` requires the walk's plan to print puzzles 1..count exactly once
  in order (review F-002) — that one is about the *puzzle* pages, so a packed
  answer key does not touch it — and the page-count tripwire at the end still
  compares `len(pages)` against `interior_page_count(count, len(plan))`, whose
  answer term is the line you change. Failures inside the walk itself come out
  as `RuntimeError("puzzle <id> could not be laid out: …")`, the layout-time
  twin of the draw-time raise, so every abort of `interior()` names an id.
  Every page is still built on `self.page_spec(its own 1-based position)`, so
  parity follows the real position; pairing shortens the book and therefore flips
  the parity of every later page, which is expected (card item 4). `Interior` and
  `BookExport` carry both page counts — keep `interior_page_count` meaning the
  real one.
- [Scope] src/nonogram/admin/book_pdf_generator.py, tests/helpers/two_up_ink.py, tests/property/test_book_export_interior.py, tests/property/test_book_pairing.py, tests/property/test_book_pdf_geometry.py, tests/test_book_pdf.py, tests/test_book_pdf_band.py, tests/test_book_pdf_two_up.py
- [Scope gate] ⚠ grown: 4 existing files outside Touches (all test corpora the pairing walk invalidates; each recorded as SCOPE+) + 1 new helper. No guardrail glob touched (G-1..G-4 clean); comp_spread 0; no sibling card's scope poached.
- [System contract] section fresh — system_rules.py --card CARD-127 returns the same 44 ids.
- [Build gate] PASSED (full, 239s; 4757 tests, 1 known-red e2e deselected: tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied)
- [Visual] not a UI card (no ## Design context, Skill python-pro) — review runs static-only. The implementation agent left owner renders in ~/Documents/nonogram-reviews/CARD-127/.
- [Review 1/3] Score: 8.0 — crit: 0, imp: 1
- [Review sync] 1 report(s) → meta/review/
- [Review 1/3] Step 8h coverage: all 44 card rules carry a verdict line (13 ✓ holds, 31 ⚠ unchecked/no_eligible_fact, 0 ✗) — count line present.
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important finding — fix mandatory
- [Adversarial] F-001 (layout failure escapes interior() unnamed) CONFIRMED — an independent skeptic reproduced all four cases: a malformed member beside a SAME-tier neighbour raises a bare ValueError naming no puzzle id, while alone or beside a different-tier neighbour it raises the documented id-naming RuntimeError; _payload does not drop the row and the existing guard test cannot see it (its fixture fails at draw time).
- [Fix 1] declarations: 5 updated (interior Raises, puzzle_pages Raises + ids arg, module header, _set_band, band-ratio constants), 1 confirmed (interior_page_count's contract re-derived and still correct), 0 none
- [Fix 1] pre-gate: all 14 named tests exist and pass; every FIXED line carries a DECLARATIONS line. F-001/F-002/F-005 verified by revert/mutation by the fix agent.
- [Build gate] PASSED (full, 233s; 4737 tests, same known-red e2e deselected)
- [Review 2/3] Score: 9.0 — crit: 0, imp: 3 minor only ✓ threshold reached + no critical/important
- [Review sync] 2 report(s) → meta/review/
- [Review 2/3] Step 8h coverage: all 44 card rules carry a fresh verdict line (13 ✓ holds, 31 ⚠ no_eligible_fact, 0 ✗); nothing carried — the fix delta touches src/nonogram/admin/**, which every rule's scope glob reaches.
- [Review 2/3] cycle-1 findings F-001..F-006 all verified ✓ resolved by the reviewer; F-007/F-008 remain out-of-scope (CARD-129 / accepted).
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, ADR-0036/R1) — independent skeptics re-ran each cited check and made their own violation pass. Two wording imprecisions noted, neither load-bearing: the ADR-0006/R1 check name is a docstring label (the collectible node is tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed), and ADR-0019/R1's 'a comment and a docstring' is really one comment in admin (the docstrings are inside export/pdf.py itself).
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-242 ✓ demonstrated — tests/test_book_pdf_two_up.py::TestBookPdf_TwoSmallSameTierNeighboursShareAPage (4/4 PASSED); shapes [[(10,10),(10,10)]] off the rendered ink, both slots 7.5 mm ±0.05, the 8.44 mm page fit and the cap asserted separately.
  AC-243 ✓ demonstrated — ::TestBookPdf_TwelvePairSharesPageBelowStandardCell (3/3 PASSED); measured slot cell 7.39 mm ±0.05, 236.35/32 re-derived independently.
  AC-244 ✓ demonstrated — ::TestBookPdf_PairJustAboveTwoUpMinimumShares (3/3 PASSED); shapes [[(15,15),(10,10)]], 7.16 mm ±0.05, >= 7.0.
  AC-245 ✓ demonstrated — ::TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare (3/3 PASSED); 6 interior pages, needed cell 6.95 mm < 7.0, one cell of gutter is the whole difference.
  AC-246 ✓ demonstrated — ::TestBookPdf_FifteenPlusTwelveDoesNotPair (2/2 PASSED); 36 cells combined, 6.57 mm, two pages off the ink.
  AC-247 ✓ demonstrated — ::TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare (2/2 PASSED); the height term alone would have allowed >= 7.0 while 193.675/28 ≈ 6.92 — the width is what refuses.
  AC-248 ✓ demonstrated — ::TestBookPdf_DifferentTiersNeverPair (10 PASSED) incl. a same-tier positive control, 4 tier spellings (with ADR-0031/R3's retired "guess") and 4 ungraded cases.
  AC-249 ✓ demonstrated — ::TestBookPdf_PairingNeverReordersToFindAPartner (3/3 PASSED); A,B,C → 8 pages, the reordered control → 7, so the declined saving is real.
  AC-250 ✓ demonstrated — ::TestBookPdf_OddPuzzleOutPrintsAlone (3/3 PASSED); shapes [[(10,10),(10,10)],[(10,10)]], and a fourth puzzle joins the odd one out.
  AC-251 ✓ demonstrated — ::TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand (5/5 PASSED); each band compared as ink (glyphs AND page-left edge) against COMP-007's own header on a single page of the same parity, with a negative control and the offset "Puzzle 2/3" case.
  AC-252 ✓ demonstrated — ::TestBookPdf_TwoUpUpperSlotSharesFixedTopEdge (3/3 PASSED); upper.top == single.top exactly, that row is top margin + 12 mm band within half a pixel, and the two pages provably print different cells.
  EC-027 ✓ demonstrated — tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly (+ its _interior_pages sibling) PASSED. Genuinely property-based: stdlib Random(20260923127), 900 books × 2 trims, extents across all of CON-011, depths 1..6, 13 tier spellings; the oracle is an independent re-implementation (imports neither compute_pair_layout nor book_page_spec); all four EC clauses asserted; minimum counts asserted in-test (books>=850, pages>=3000, paired>=100, refused_on_tier>=1000, refused_on_fit>=350, ungraded>=400, odd_tail>=600, near_threshold<=5).
  EC-022 ✓ demonstrated — tests/property/test_book_layout.py::test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent, tests/property/test_book_pdf_geometry.py::..._pdf_pages and the card's new ..._two_up_pages, all PASSED. The single-page sibling still sweeps 125+ extents over 10..30 on two sheets; the two-up node asserts the fixed top edge on the upper drawing of every page (len(tops)==1), portrait and unrotated for both slots, two_up>=5 / single>=5. Noted: the two-up corpus is 10..22 × 10..16 on Book 1 only — above that nothing can pair at 7.0 mm, so the narrowing follows the property's own reachability.
  G-1 ✓ demonstrated — book_pdf_generator.py read end to end plus two greps: every mm/cell literal is in a docstring or comment; puzzle_pages only compares tiers and calls compute_pair_layout; _two_up_page consumes pair.upper/.lower and header_band(slot). The only numbers the panel computes are the two text-fitting ratios (pinned equal to the export's by a green test) and center_x - width/2 for anchor="lm". Bounded: one module read, not a proof about all of admin/.
  G-2 ✓ demonstrated — three-dot changed-file set (merge base 89facec) + git status --porcelain, then path-scoped diffs over src/nonogram/db/*, migrations/*, book_manager.py → empty. Pairing is computed inside interior()/puzzle_pages() at PDF time with nothing written back.
  G-3 ✓ demonstrated — structural: git diff main...HEAD --name-only -- src/nonogram/export/* → empty. Behavioral: tests/test_export_a4_golden.py + tests/property/test_cli_exports_byte_identity.py → 66 passed; tests/test_layout_page_spec.py::TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden → 63 passed. Not-weakened: the tripwire test files and tests/fixtures/a4_golden/** are byte-identical to main (blob hashes compared), nothing regenerated.
  G-4 ✓ demonstrated — path-scoped diff over book_proof.py and admin/templates/* → empty; none of the five CARD-118/130-owned files is in the committed or uncommitted change set.
- [Docs] forge:readme — no README change: the card adds two test modules and one test helper to directories whose purpose is unchanged, src/nonogram/admin/ has no per-directory README, and tests/README.md is a pre-existing "Wave 1" document that enumerates no test file this card touches. Rewriting it would be drive-by scope with four cards running in parallel.
- [Commit] cbbb755 fix(admin): CARD-127 review round — a pairing failure names its puzzle (4 files; parent ed8d20e feat: CARD-127 two puzzles to a book page, in the owner's order). Nothing under meta/ committed; explicit pathspecs only.
- [Owner] Renders to eyeball: ~/Documents/nonogram-reviews/CARD-127/ — CARD-127-two-up-interior.pdf (9-puzzle Book 1: 17 interior pages against 20 un-paired, 3 saved) and CARD-127-interior-page-{2,3,4,5}.png.
- [Owner question] CARD-125's F-002 is visible in the renders: the lower slot is anchored to the bottom margin, so a pair's spare height falls BETWEEN the two puzzles as a wide white band mid-page. This card consumed that as delivered (G-3) and AC-252/EC-022 pin only the upper slot's top edge, which holds. If Olga wants the slack elsewhere, the fix belongs in compute_pair_layout (COMP-007), not in book_pdf_generator.py.

- [Done] Merged 679e78a on 2026-09-23. Review 9.0 (cycle 2; cycle 1 was 8.0 with one
  Important, reproduced by a skeptic and fixed). AC/EC/G 17/17 demonstrated off rendered
  ink or a named green test. Full suite green on the merge. Golden tripwire green and
  byte-identical by blob hash.
- [SCOPE+] Touches grew: four existing test corpora edited plus a new helper
  (tests/helpers/two_up_ink.py). Pairing invalidated their one-puzzle-per-page premise,
  so both reviews judged the growth necessary. No guardrail glob touched, no sibling's
  scope poached.
- [Handover -> CARD-134] Page numbering after pairing: guide = interior page 1; puzzle
  pages 2..1+len(plan) with plan[k].page_number == 2+k; divider at 2+len(plan); answers
  at 3+len(plan)+i. Replace that answer loop and interior_page_count's answer term
  TOGETHER or the page-plan tripwire fires (that is intended). The answer path is
  otherwise untouched. Puzzle numbers are 1-based over surviving payloads, now guarded by
  a printed == 1..count check. puzzle_pages(payloads, ids=...) raises RuntimeError naming
  the puzzle on a layout failure.
- [Owner question — CARD-125's F-002, still unresolved] The lower slot is anchored to the
  bottom margin, so a pair's spare height lands BETWEEN the two puzzles as a visible white
  band mid-page. Consumed as delivered per G-3; AC-252/EC-022 pin only the upper slot's
  top edge, which holds. Moving the slack is a change to compute_pair_layout (COMP-007) —
  nothing in book_pdf_generator.py would change.
- [Owner] Renders: ~/Documents/nonogram-reviews/CARD-127/CARD-127-two-up-interior.pdf
  (9-puzzle Book 1: 17 interior pages against 20 un-paired) plus
  interior-page-{2,3,4,5}.png.
- [Later card, not this one] The Finalise screen now OVERSTATES the interior by
  pages_saved (17 against 20 on the render). CARD-129's KDP gutter refusal is about to
  consume that number and must read BookExport.interior_page_count, not
  interior_page_count(len(puzzles)).
