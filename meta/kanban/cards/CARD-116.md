# CARD-116: The book PDF on its own trim — trim-sized pages at 300 DPI, portrait, upright, fixed top edge

**Status:** done
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
**Review score:** 9.3 (cycle 2/3)
**Started:** 2026-09-23T01:25:42Z
**Closed:** 2026-09-23T03:35:32Z
**Actual:** 0.3d
**Merge commit:** dff610b
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

- [Handover from CARD-114, 2026-09-22] F-004: the book-path `render_pages` currently prints "<name> — <tier>" in the band. ADR-0037/R1 forbids the picture name on a book puzzle page — replace it with "Puzzle N · Tier"; do not rely on the current band text.

- [Handover from CARD-115, 2026-09-22] setup_print still writes the chosen trim only into book_metadata.size, never trim_width_cm/trim_height_cm, so book_page_spec keeps seeing the Book 1 profile trim. AC-176/AC-177 need that persistence — carry it here or card it.
- [Handover from CARD-115] Measure through book_cell_mm, not test_layout_page_spec.py's private _book_cell_mm helper.

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)

### CARD-116 implementation, 2026-09-23

**What changed.** `BookPDFGenerator` now takes the **book** (`BookPDFGenerator(book)`,
`book=None` meaning "no stored print spec", i.e. CON-018's profile) and builds one
`book_page_spec(book, page_number)` per page, where `page_number` is that page's
1-based position in the interior (FR-043). Every page is the book's trim at 300 DPI:
guide, puzzle pages, SOLUTIONS divider, answer pages and the cover file's single
page — 2550x3300 px on Book 1, 1800x2700 px on 6x9 in. Puzzle and answer pages go
through `render_pages(payload, page_spec=spec)` unchanged; the hard-coded
2550x3300 letter page and the unused `trim_width_cm`/`trim_height_cm` arguments of
`export_book`/`generate_book_pdf` are gone (one door onto the sheet, not two).

**G-1 held.** The admin panel fits no cell and places no grid line. Everything it
needs beyond `render_pages` — the trim and the usable area for the guide, divider
and cover pages — is read off `compute_layout(..., book spec)` through the new
`page_frame(spec)`, which lays out a one-cell probe purely to read `Layout.width`
/ `.height` and the `PagePlacement`'s usable edges back. No millimetre is
converted to a pixel in `admin/`.

**Answer-page parity.** A puzzle's blank page and its answer page are at different
interior positions, so when those positions disagree in parity they are different
sheets. `_puzzle_and_answer` renders the second sheet only in that case.

**Page numbering and failures.** Payloads are built in a first pass, so a puzzle
that cannot be turned into an `ExportPayload` is dropped *before* any position is
handed out (it used to be dropped mid-way, which with per-page specs would have
mis-parified every later page). A failure after that point is no longer swallowed:
the page plan `interior_page_count` states would no longer describe the file.

**Band content deliberately unchanged (CARD-117's).** The puzzle page's band still
prints today's `"<name> — <tier>"` via `payload.name`/`payload.difficulty`.
ADR-0037/R1's "Puzzle N · Tier" is CARD-117's change and nothing here was built on
the current text — `_payload` says so at the one place that feeds it.

**Tests.** `tests/test_book_pdf.py` (AC-175..AC-178, AC-189, AC-190, AC-240,
AC-274..AC-276, plus INV-013's `TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1`,
which CARD-135 recorded as this card's half and which did not exist yet) and
`tests/property/test_book_pdf_geometry.py` (the PDF halves of EC-019, EC-022,
EC-032). Every geometric assertion is **measured off the rendered page's ink**
(`tests/helpers/page_ink.py`) and compared against a figure worked out in
millimetres in the test from CON-018's profile and FR-030/FR-032 — a second
implementation, not a re-derivation: no test module here imports `compute_layout`,
`PageSpec` or `book_page_spec`. Full suite green (1 pre-existing deselect:
`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`).

**SCOPE+ lines.**
- `SCOPE+ tests/helpers/page_ink.py — new shared test helper.` Reads a drawing's
  placed edges, its cell and its rule counts back off a rendered page, so the ACs
  and the three properties are all measured the same, independent way. It is a
  helper, not a fixture of one test file, because CARD-117/CARD-134 will measure
  the same pages.
- `SCOPE+ tests/property/test_book_export_interior.py — EC-034's parity half.` The
  card's EC-034 says "extend CARD-135's property", and this is that file. The
  extension is additive: every interior page is asserted to be the trim, and every
  page carrying a drawing (puzzle pages and answer pages) is asserted to draw it
  where a page of *its own* 1-based position puts it. The stale comment saying
  parity was not yet observable was replaced by the assertions that observe it.

**[Handover to a later card] `setup_print` still does not persist the chosen trim.**
CARD-115's handover is NOT resolved here, on purpose. `setup_print` writes the
chosen trim into `book.metadata.size` only; there is **no existing `book_manager`
API that stores `trim_width_cm`/`trim_height_cm`** (the print columns are written
once, by `create_book`). Persisting them would mean editing
`src/nonogram/admin/book_manager.py` and/or `src/nonogram/db/**`, which G-4 gives
to CARD-121 this wave. Assigning the attributes on the `Book` object in `app.py`
was rejected as a half-fix: it would stick in the in-memory manager and vanish in
DB mode, making the trim mode-dependent. **What is still missing:** a
`book_manager` method (e.g. `set_print_spec(book_id, trim_width_cm,
trim_height_cm)`) writing the two `books` columns, called from `setup_print` after
`PrintSpecValidator.create_spec` succeeds. Until then a book set up through the UI
keeps the Book 1 profile trim, and only its `metadata.size` string shows the
chosen one. AC-176/AC-177 are satisfied at the generator level with a book that
carries a stored trim, which is what the export reads (`_export_part` passes the
real `Book`), so the moment those columns are written the whole export follows
with no further change here.

**Owner renders.** `~/Documents/nonogram-reviews/CARD-116/` — `book1_interior.pdf`
/ `book1_cover.pdf` and `6x9_interior.pdf` / `6x9_cover.pdf`, plus a PNG per page.
The interior is guide (page 1, odd) → heart 15x15 (page 2, even/left-hand) →
snowflake 30x30 (page 3, odd/right-hand) → fish 30x15 wide (page 4, even) → heart
15x15 (page 5, odd) → SOLUTIONS divider → four answer pages.

- [Review sync] entering review phase; implementation commit a89b6a6

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_pdf_generator.py, tests/helpers/page_ink.py, tests/property/test_book_export_interior.py, tests/property/test_book_pdf_geometry.py, tests/test_book_pdf.py
- [Build gate] impact underivable (python-pro without pytest-testmon) — full suite
- [Build gate] PASSED (full, 184s)
- [Build gate] ⚠ first full run showed one failure, tests/test_book_ready_gate.py::TestBookPlanEdit_OnANonDraftBookReturnsItToDraft::test_save_plan_returns_the_book_to_draft[db-ready_for_kdp], in CARD-124's area and untouched by this diff. Not reproducible in isolation nor over tests/ without the subdirectories; the run carried pytest's "(rm_rf) error removing .../pytest-of-omelnikova/garbage-..." warning, i.e. a CONCURRENT full suite (CARD-121's) garbage-collecting the shared pytest tmp base dir underneath it. Re-run under the full-suite lock with --basetemp isolated: green. Process hazard for the dispatcher, not a card defect — the full-suite lock does not isolate pytest's tmp root.
- [Scope gate] ⚠ grown: 2 files outside Touches (tests/helpers/page_ink.py — new shared measuring helper; tests/property/test_book_export_interior.py — EC-034 says to extend CARD-135's property, and that is the file). Both recorded as SCOPE+ by the implementer. No component spread, no guardrail hit, no sibling poaching (1 of CARD-121's 7 Touches entries).

- [Review 1/3] Score: 8.5 — crit: 0, imp: 1
- [Review sync] 1 report(s) → meta/review/20260923T022234Z-CARD-116-cycle1.yml
- [Review 1/3] Step 8h: 44/44 card rules carry a verdict line (11 ✓ holds, 32 ⚠ unchecked, 1 ✗ ADR-0037/R1 — recorded for coverage, owned by CARD-117 by this card's own objective 5). Coverage guard satisfied.
- [Severity gate 1/3] Score >= threshold but 0 critical / 1 important findings — fix mandatory

- [Adversarial] F-001 (render failure aborts the whole book export, untested, error names no puzzle) CONFIRMED — the skeptic reproduced it against both checkouts: on main a grid=None or an empty column-clue puzzle printed "Failed to render puzzle <id>" and the export returned 6 pages minus that puzzle; on the branch the same inputs raise out of interior_pages and the whole export is lost. Trimmed, not refuted: neither input is producible through the store's write path (add_puzzle refuses a non-rectangular grid; both real callers pass computed clues), and the new docstring states the non-swallowing as a deliberate trade — so it is an intended behaviour change with an unnamed-puzzle error and no test, not an accident. 1 confirmed important finding.

- [Fix 1] FIXED F-001 (test: TestBookPdf_UnbuildablePuzzleNeverShiftsALaterPage, TestBookPdf_UndrawablePuzzleAbortsNamingThePuzzle), F-002 MediaBox (test: TestBookPdf_PageSizeEqualsStoredTrim, TestBookPdf_EmptyMarginsFallBackToBook1Profile), page-plan guard (TestBookPdf_PagePlanGuardIsLive), dropped-puzzle logger, page_frame guard (TestBookPdf_PageFrameNeedsABookPageSpec), dead imports. app.py deliberately NOT edited this round — the routes' existing flash now carries the puzzle id because the raised message does, so CARD-121's file was left alone.
- [Fix 1] declarations: 2 updated (interior_pages Raises: contract, interior_page_count's drift wording; log text), 3 confirmed still correct (module docstring, _payload, app.py export docstrings), 4 none. Stated design change: puzzle["id"] acquires a second job — from log label to the identifying signal of a raised error contract.
- [Fix pre-gate] all 6 named tests exist and pass (15 tests). Verified by revert by the fix agent: pre-fix code fails both new tests with the finding's own symptoms (unnamed TypeError; second survivor at 23.876 mm instead of 27.05 mm).
- [Build gate] PASSED (full, 181s)

- [Review 2/3] Score: 9.3 ✓ threshold reached + no critical/important — crit: 0, imp: 0. All six cycle-1 findings ✓ resolved; three of them re-derived by mutation (dpi 300→150 killed the new MediaBox assertions; the pre-fix unnamed abort killed the naming test; the pre-card mid-loop drop put the second survivor at 23.876 mm instead of 27.05 mm — the exact mis-parification, and the exact number, the fix claimed). 3 Minors remain, none gating.
- [Review 2/3] Step 8h: 44/44 card rules carry a verdict line (10 ✓ holds, 33 ⚠ unchecked, 1 ✗ ADR-0037/R1 — deliberate, CARD-117 owns it). Coverage guard satisfied. Cycle 2 corrected cycle 1 on ADR-0006/R1: its check ref TestDependencyBaseline_IsExactlyPillowAndNumpy does not exist under tests/ (cycle 1 reported it green — an over-claim on a name); the baseline is in fact covered by tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed.
- [Review sync] 2 report(s) → meta/review/20260923T030029Z-CARD-116-cycle2.yml

- [8h spot-check] 3/3 sampled holds reproduced (ADR-0019/R1, ADR-0036/R1, INV-013). ADR-0019/R1: the ast guard is non-vacuous on this card — it walks 57 modules, ranks `admin` as a rank-0 adapter and discovers book_pdf_generator.py; the fix's only added import is stdlib `logging`. ADR-0036/R1: 66 tests green, and the a4_golden fixtures are byte-identical to main by blob hash (main == HEAD == working tree for all 5 files) — nothing regenerated; the card in fact removes the one spec-less render_pages call, moving book code off the default path, and a same-process check showed no global-state leak into the default layout. INV-013: the EC-034 property is a real seeded corpus (28 cases, 4 routes, floors incl. the card's new right-hand >= 10 / left-hand >= 10), the diff genuinely adds the trim-on-every-page and own-position-parity assertions, and the generator's position arithmetic reads exactly 1=guide, 2..1+n=puzzles, 2+n=divider, 3+n..2+2n=answers. One cosmetic note: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry is a docstring-level property label, not a runnable pytest node id (it maps to three snake_case functions).

- [AC/EC check] All criteria/constraints ✓ (evidence): all 10 ACs, all 4 ECs and all 5 guardrails ✓ demonstrated by a fresh-evidence gate.
  AC-175 4.9660 mm vs the A4 4.7692 mm; AC-176 5.9170 mm on 6x9 in and 7.5 mm on 8.5x11; AC-177 both halves — every page raster 1800x2700 px AND every MediaBox (0,0,432,648) pt (the "at 300 DPI" clause, added this fix round); AC-178 4.9660 mm on empty margins and on a wholly empty print spec, 612x792 pt; AC-189/AC-240 portrait 2550x3300 with rule counts read off the ink giving (30, 15) and a 15x30 negative control proving the measurement can see a rotation; AC-190/AC-276 same top pixel row; AC-274 27.05 mm, AC-275 23.875 mm, difference = gutter - outside.
  EC-019 220 seeded cases, floors checked>=200 / at_cap>=20 / below_book_floor>=20; EC-022 121 systematic extents over CON-011's band + 5 wide grids on 2 sheets, floors len(extents)>=120 / counted>=150 / overflowed>=1, len(tops)==1 pinning the single top offset; EC-032 110 cases, floor checked>=100, both parities on both page kinds; EC-034 28 cases x 4 routes with per-route, cover, empty-book and right-hand>=10 / left-hand>=10 floors. All stdlib random.Random, no hypothesis.
  G-1 no drawing primitive and no mm->px arithmetic anywhere in book_pdf_generator.py; G-2 171 tests green and tests/fixtures/a4_golden/** byte-identical to main (never regenerated); G-3/G-4/G-5 no path in the card's change set touches the guarded globs.
  Note on method: main advanced mid-run (CARD-121 merged, tip 0594dd8, merge-base 6dd667a), so the gate used three-dot main...HEAD — a two-dot diff would have falsely attributed CARD-121's book_manager.py/db/migrations files to this card and failed G-4 spuriously.
- [Docs] no README change: only tests/README.md exists among the changed directories, and it is a Wave-1-scoped document that enumerates four unrelated feature test files rather than the tree, so this card's files do not change what it states. src/nonogram/admin/, tests/helpers/ and tests/property/ carry no README in this project.

- [Commit] f532aea fix(admin): review fix round — diagnostic render failure with puzzle id (3 files: src/nonogram/admin/book_pdf_generator.py, tests/helpers/page_ink.py, tests/test_book_pdf.py). Branch card/116-book-pdf-on-trim now carries a89b6a6 + f532aea; nothing under meta/ committed. Pipeline stops here — the dispatcher merges.


### Review fix round 1, 2026-09-23 (F-001 Important + the cheap Minors)
**F-001 — the render failure that aborted the book without naming a puzzle.**
The trade the review confirmed is kept: a puzzle dropped *before* any interior
position is handed out is what keeps every later page's parity right, and a
failure *after* that point still aborts rather than being swallowed. What
changed is that the abort is now diagnosable. Each puzzle's own `id` travels
beside its payload through the first pass, and the render is wrapped so a
failure becomes `RuntimeError(f"puzzle {id!r} could not be drawn: {e}")` with
the original kept as `__cause__`. **The signal is the row's `id`**, not the
position in `puzzles` (which stops matching the interior the moment a member
is dropped), not the interior page number (which points at no row at all),
and not `puzzle_name` (not unique, and optional). `id` is the key the book's
membership stores and `puzzle_review.get_puzzle` looks up, so it is the one
identifier that leads back to the row. The routes needed no change: their
existing `flash(f"Error generating PDF: {e}")` now carries the id — `app.py`
is deliberately untouched, CARD-121 is editing it this wave.
**The invariant enforced:** every page of the interior sits at the 1-based
interior position its own kind and order give it, and `interior_page_count`
describes the file that is actually written — so the export either produces a
file matching its page plan, or produces none and says which puzzle stopped
it. Both halves are now tested at the module's API.
**Tests (all in `tests/test_book_pdf.py`, all API-contract tests — their
docstrings say so).** Neither malformed row is reachable through the store's
write path today (`add_puzzle` re-derives clues from the grid), but the
contract lives at `interior_pages`, so that is where it is pinned.
- `TestBookPdf_UnbuildablePuzzleNeverShiftsALaterPage` — a row whose payload
  cannot be built, placed *between* two good puzzles; the survivors are
  asserted to sit at the left edges interior pages 2 (left-hand) and 3
  (right-hand) imply, measured through `tests/helpers/page_ink.py` like the
  rest of the file. **Verified by revert:** restoring the pre-card mid-loop
  drop puts the second survivor at 23.876 mm (page 4's left-hand edge)
  instead of 27.05 mm — the exact mis-parification the restructuring exists
  to prevent.
- `TestBookPdf_UndrawablePuzzleAbortsNamingThePuzzle` — a row that builds a
  payload and then will not draw (`grid=None`), through `interior_pages` and
  through `export_book`. **Verified by revert:** the pre-fix code fails it
  with the finding's own symptom, `TypeError: 'NoneType' object is not
  subscriptable` out of `export/pdf.py`, naming no puzzle.
**Minors folded in.**
- *AC-177's "at 300 DPI" clause is now asserted.* New
  `page_ink.pdf_page_boxes()` reads each page's **MediaBox** straight off the
  PDF — 6x9 in is `(0, 0, 432, 648) pt`, Book 1 is `(0, 0, 612, 792) pt` —
  so a regression in `_save_pdf`'s `dpi=(300,300)` can no longer keep every
  pixel assertion green while the book prints at the wrong physical trim.
  Asserted in `TestBookPdf_PageSizeEqualsStoredTrim` (interior and cover) and
  `TestBookPdf_EmptyMarginsFallBackToBook1Profile`.
- *The page-plan self-check now reads from the input.* It compares the pages
  built against `interior_page_count(len(payloads))` rather than against a
  list the same loop produced. No input makes the two disagree *today* — the
  gain is that a future change to the interior's make-up that forgets the
  plan is caught. `TestBookPdf_PagePlanGuardIsLive` pins that the guard fires
  on drift at all (it was worth checking: a guard that cannot fail reads like
  one that can).
- *The dropped-puzzle log goes to the module's `logger`*, at warning, with a
  message saying what was dropped and why — it is the only trace of a member
  that did not reach the file, and a `print` lands nowhere in a served
  request. Pinned by
  `TestBookPdf_UnbuildablePuzzleNeverShiftsALaterPage::test_the_drop_leaves_a_trace_in_the_log`;
  reverting to `print` fails it.
- *`page_frame`'s no-parity guard is kept and tested* —
  `TestBookPdf_PageFrameNeedsABookPageSpec`. `page_frame` is a new public
  symbol and the guard is what stops it reading attributes off `None`;
  `DEFAULT_PAGE_SPEC` is imported there only as *a spec that is not a book
  page*, and no measurement is derived from it, so the module's independence
  from `compute_layout`/`book_page_spec` is untouched.
- *Dead imports removed* from the block the diff edited: `Path`, `datetime`,
  `clues`.
**Declarations re-derived.** `interior_pages` gained a `Raises:` section
stating the new error contract (the old wording said only "is not
swallowed"). `interior_page_count`'s docstring was corrected: the payload
skip is now stated as the *only* way its count and the book's members differ,
because a later failure aborts instead of shortening the file. The module
docstring, `_payload`'s docstring and `app.py`'s `_export_part` and route
docstrings were re-read and state nothing about the failure lifecycle — still
correct, left alone. No README states it. One design note: `puzzle["id"]`
acquires a second job — it was a log label, it is now the identifying signal
of a raised error contract that a reviewer will search a 120-puzzle book by.
**Left alone on purpose.** The band still printing `"<name> — <tier>"`
(objective 5 defers it to CARD-117); the CARD-115 `setup_print` persistence
gap (G-4 gives `book_manager.py`/`db/**`/`migrations/**` to CARD-121);
`src/nonogram/export/**` (G-3) and `admin/pdf_generator.py` (G-5).
**Verification.** Full suite green from the worktree root with the stated
deselect and `--basetemp`; the CON-019 golden-A4 tripwire
(`tests/test_export_a4_golden.py`,
`tests/property/test_cli_exports_byte_identity.py`) green with
`tests/fixtures/a4_golden/**` untouched.

- [Done] rebased onto main 0594dd8 (after CARD-121), full suite on the rebased tree with --basetemp: only the pre-existing e2e failure. Merged dff610b (--no-ff). Deferral scan: 0 hits. SCOPE+ x2 (tests/helpers/page_ink.py, tests/property/test_book_export_interior.py) judged necessary. CARD-115's trim-persistence handover deliberately NOT resolved here (G-4) — carded as CARD-136.
