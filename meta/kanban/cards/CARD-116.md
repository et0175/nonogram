# CARD-116: The book PDF on its own trim — trim-sized pages at 300 DPI, portrait, upright, fixed top edge

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/116-book-pdf-on-trim
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-13
**Idea:** —
**Wave:** 23
**Depends on:** CARD-115, CARD-135
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/app.py, tests/test_book_pdf.py, tests/property/test_book_pdf_geometry.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Today `BookPDFGenerator` hard-codes a 2550 × 3300 px letter page, treats the trim as
"informational", and prints each puzzle through the A4 `render_pages`, so a book puzzle
is sized for A4 inside a letter page. This card produces the book on the trim.

1. `generate_book_pdf` takes the **book** (or its `PageSpec` from CARD-115's
   `book_page_spec`), not loose trim strings. The `/book/<id>/generate-pdf` and
   `/book/<id>/download-pdf` routes pass it through.
2. **Every page is the trim at 300 DPI**: the interior's guide, puzzle pages, the
   SOLUTIONS divider and the answer pages, and the separate one-page cover file
   (CARD-135). On the Book 1 profile that is 2550 × 3300 px. On 6×9 in it is
   1800 × 2700 px.
3. Puzzle and answer pages are drawn with `render_pages(payload, page_spec=spec)` (or
   the layout CARD-114 exposes) and placed on the trim page at the drawing origin the
   layout reports. The drawing's **top edge sits at top margin + band on every puzzle
   page**, and the page is portrait with the grid unrotated (FR-032). The admin code
   positions the finished drawing only. It fits no cell and places no grid line
   (ADR-0036/R2).
4. **Mirrored margins** (decided 2026-09-22 (c); FR-030/FR-032 amended, ADR-0036
   clarification). Number the **interior** PDF's pages from 1 — page 1 is the guide
   page and is right-hand (decided 2026-09-22 (d), FR-043; the cover is CARD-135's
   separate file and is never numbered) — and build each page with
   `book_page_spec(book, page_number)` (CARD-115). The gutter margin is on the left of
   odd pages and on the right of even pages. The drawing is centred across the usable
   width, and its top edge never moves. Every page kind takes its parity from its
   interior position: guide, puzzle, divider and answer pages alike. Until level
   dividers exist (CARD-128), the first puzzle page directly follows the guide page and
   is therefore interior page 2, left-hand. That is expected. CARD-128 asserts the
   divider case (AC-287).
   The answer pages stay one per puzzle here. CARD-134 replaces them with the packed
   6-up / 4-up answer key (FR-042).
5. This card does **not** change the band's content, picture titles or line weights
   (that is CARD-117). Keep today's header behaviour on the puzzle page until then, and
   note it.

Owner visual check (see CARD-118 for the checkpoint as a whole): put a render of a
Book 1 PDF (15×15, 30×30, a 30×15 wide grid) and a 6×9 PDF in
`~/Documents/nonogram-reviews/CARD-116/`. Never write them beside the repo.

## Acceptance criteria

- **AC-175** — given a book on the Book 1 profile (trim 21.59 x 27.94 cm, gutter 1.27 cm, outside/top/bottom 0.95 cm) holding a 30x30 puzzle whose row-clue and column-clue gutters are each 9 entries deep, when the book PDF is generated, then that puzzle's page draws a 4.97 mm cell (+/- 0.05 mm; 193.7 mm usable width over 39 cells) — not the 4.77 mm the A4 layout gives it today.
  *test:* `TestBookPdf_CellSizedForBookTrimNotA4`
- **AC-176** — given a 6 x 9 in book (trim 15.24 x 22.86 cm, Book 1 margins) holding a 15x15 puzzle whose row-clue gutter is 7 entries deep and column-clue gutter 7 deep, when the book PDF is generated, then that puzzle's page draws a 5.92 mm cell (+/- 0.05 mm; 130.2 mm usable width over 22 cells), where the same puzzle on the 8.5 x 11 trim draws 7.5 mm.
  *test:* `TestBookPdf_CellFollowsStoredTrim`
- **AC-177** — given a 6 x 9 in book (trim 15.24 x 22.86 cm) holding 3 puzzles, when the book PDF is generated, then every page of the PDF is 1800 x 2700 px at 300 DPI — not the hard-coded 2550 x 3300 px letter page.
  *test:* `TestBookPdf_PageSizeEqualsStoredTrim`
- **AC-178** — given a book row created before print margins were set, whose gutter_margin_cm and outside_margin_cm are empty, holding a 30x30 puzzle with 9-deep clue gutters, when the book PDF is generated, then the cell equals the one computed on the CON-018 margins (4.97 mm on the 8.5 x 11 trim).
  *test:* `TestBookPdf_EmptyMarginsFallBackToBook1Profile`
- **AC-189** — given a Book 1 profile book holding a 30-wide x 15-tall puzzle, when the book PDF is generated, then that puzzle's page is portrait, 2550 px wide by 3300 px tall.
  *test:* `TestBookPdf_WideGridPrintsOnPortraitPage`
- **AC-190** — given a Book 1 profile book holding a 15x15 puzzle and a 30x30 puzzle, when the book PDF is generated, then the top edge of the puzzle drawing is on the same pixel row on both pages.
  *test:* `TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage`
- **AC-240** — given a Book 1 profile book holding a 30-wide x 15-tall puzzle, when the book PDF is generated, then the puzzle's grid is drawn with 30 columns across the page and 15 rows down it (unrotated).
  *test:* `TestBookPdf_WideGridPrintsUprightNeverRotated`
- **AC-274** (FR-032, added 2026-09-22 (c); reworded (d)) — given a Book 1 profile book whose interior page 3 (right-hand) holds a 15x15 puzzle with 7-deep row- and column-clue gutters (22 cells x 7.5 mm = 165 mm drawing width), when the book PDF is generated, then the drawing's left edge is 27.05 mm (+/- 0.1 mm) from the page's left trim edge — 14.35 mm inside each side of the usable width.
  *test:* `TestBookPdf_DrawingCentredOnRightHandPage`
- **AC-275** (FR-032, added 2026-09-22 (c); reworded (d)) — given the same puzzle printed on interior page 4 (left-hand) of the same book, when the book PDF is generated, then the drawing's left edge is 23.875 mm (+/- 0.1 mm) from the page's left trim edge.
  *test:* `TestBookPdf_DrawingCentredOnLeftHandPage`
- **AC-276** (FR-032, added 2026-09-22 (c)) — given the pages of AC-274 and AC-275, when the top edges of the two drawings are compared, then they lie on the same pixel row — parity moves the drawing sideways only.
  *test:* `TestBookPdf_ParityNeverMovesTopEdge`

## Engineering constraints

- **EC-019** (consistency) — For any puzzle of 10..30 cells per side, any real clue depth and any stored trim and margins, the drawn puzzle (grid plus both clue gutters) fits inside the usable area (trim minus margins minus the title band) and its cell never exceeds the 7.5 mm standard cell — and the PDF page is the trim size, for every extent, not only the measured examples.
  *test:* `PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell` — _extend CARD-114's property with the PDF-page half (page size == trim for every extent and trim)._
- **EC-022** (consistency) — For any puzzle extent of 10..30 per side and any clue depth, the book's puzzle page is portrait, the grid is drawn unrotated (width across the page, height down it), and the drawing's top edge — the upper puzzle's on a two-up page — lies at one fixed offset (top margin plus title band) from the top of the trim, so that offset never varies between puzzle pages of a book.
  *test:* `PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent`
- **EC-032** (consistency; added 2026-09-22 (c), PDF half) — For any puzzle extent of 10..30 per side, any clue depth, any stored trim and margins and any page position, the gutter margin lies on the binding side of the page (left on odd pages, right on even pages), the drawing's horizontal centre is the centre of that page's usable width, and the drawing's left edge on an odd page minus its left edge on an even page equals gutter margin minus outside margin — while its top edge is identical on both.
  *test:* `PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity` — _extend CARD-114's layout-level property with PDF pages at both parities._
- **EC-034** (consistency, INV-013; parity half, added 2026-09-22 (d)) — For any book (any members, levels, pairing, answer-key layout and cover or no cover) and every export route, the interior PDF holds no cover page, its page 1 is the guide page, each page's parity is its 1-based position in the interior (page 1 odd, right-hand), the page count finalise checks equals the interior's page count, and exactly one cover file of one trim-size page is produced beside it — for every book, not only the measured examples.
  *test:* `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` — _extend CARD-135's property: every interior page's PageSpec parity equals its 1-based interior position, and the cover file is the trim size._

## Guardrails

- G-1: The admin panel fits no cells and places no grid lines itself. Geometry comes only from `compute_layout(..., page_spec=book spec)` (ADR-0036/R2).
- G-2: CLI and web A4 output stay byte-identical (CON-019). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry.
- G-3: Do not edit `src/nonogram/export/**`. Consume CARD-114's API as delivered. If something is missing there, escalate rather than widen export here.
- G-4: Do not edit `src/nonogram/admin/book_manager.py`, `src/nonogram/db/**` or `migrations/**`. They are owned by CARD-121 this wave.
- G-5: The `admin/pdf_generator.py` (single-puzzle admin PDF) keeps its current A4 output. It is not a book path.

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

- **FR:** FR-030, FR-032, FR-043 (EC-034 parity half)
- **NFR:** NFR-008
- **CON:** CON-018, CON-019
- **ADR:** ADR-0036
- **Components:** COMP-009, COMP-007 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
