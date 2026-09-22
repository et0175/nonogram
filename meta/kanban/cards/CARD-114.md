# CARD-114: PageSpec — compute_layout learns a second sheet, only when told (book cap, portrait-only, book strokes)

**Status:** done
**Priority:** P1
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/114-page-spec
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-13
**Idea:** —
**Wave:** 21
**Depends on:** CARD-113
**Touches:** src/nonogram/export/layout.py, src/nonogram/export/png.py, src/nonogram/export/pdf.py, src/nonogram/export/__init__.py, tests/test_layout_page_spec.py, tests/property/test_book_layout.py
**Review score:** 8.8 (cycle 1/3)
**Started:** 2026-09-22T16:33:08Z
**Closed:** 2026-09-22T17:24:16Z
**Actual:** 0.1d
**Merge commit:** e854cfc
**Blocked by:** —

## What to implement

This card is the first implementation of ADR-0036, and it is the central bet of the book
generator: one `compute_layout` must serve both A4 and the book without disturbing A4.

1. **The `PageSpec` value object in COMP-007** (`export/layout.py`, exported from
   `nonogram.export`). It is frozen and holds physical units:
   - the page size (width and height in mm);
   - four margins: top, bottom, and the two side margins (gutter and outside);
   - the **page parity** (2026-09-22 (c), ADR-0036 clarification "Mirrored margins"):
     `None` on the default spec; `ODD` (right-hand page, gutter margin on the **left**)
     or `EVEN` (left-hand page, gutter margin on the **right**) on a book spec. Page 1
     of the book's **interior** PDF (the guide page; the cover is a separate file,
     FR-043, 2026-09-22 (d)) is right-hand. The spec only carries the parity it is
     given; which page is page 1 is the admin's (CARD-135/CARD-116);
   - the reserved title band height;
   - the **orientation policy**: `LARGER_CELL_WINS` (NFR-006) or `PORTRAIT_ONLY`;
   - the **cell-cap policy**: `COMFORT_CURVE` (NFR-005) or a flat cap in mm;
   - the **stroke minimum** (ADR-0037/R2): the book sets thin ≥ 0.25 mm and heavy = 2 × thin, pure black. The default is "none", which keeps today's `cell / 30` rule.

   The module-level default instance reproduces today's constants exactly: A4, 12 mm
   margins, `HEADER_BAND_MM`, NFR-006, NFR-005 and today's strokes.
2. **`compute_layout(row_clues, column_clues, page_spec=None)`.** `None` or the default
   spec takes today's code path. `_fit_cell`, `_orientation_for`, `_page_size_mm` and
   `_rule_widths` read their numbers from the spec instead of module constants. Under a
   book spec:
   - the drawing is **portrait and never rotated** (the grid's columns run across the
     page);
   - the cell is `min(flat cap, page fit)`, where page fit uses the usable area:
     trim − gutter − outside across, and trim − top − bottom − band down. Parity moves
     the usable area sideways and never changes its size;
   - the clue gutters are the **real** clue depth (`_gutter_depth`), not an estimate;
   - the drawing's top edge sits at a fixed offset (top margin + band), not centred
     vertically;
   - the drawing is **centred horizontally across the usable width** of that page's
     parity (FR-032 amended 2026-09-22 (c)). Its left edge moves with the parity by
     gutter − outside (3.175 mm on the Book 1 profile), and its top edge does not move.

   `Layout` must carry what a caller needs to place the drawing on the trim, such as
   the page size in px and the drawing origin. Add those fields in a way that leaves
   the default path's serialized `Layout` byte-identical to CARD-113's golden. If a new
   field would change the serialization, get the book path's values from a separate
   accessor instead.
3. **Thread the spec through the renderers** so the book PDF can use them: add an
   optional, defaulted `page_spec` parameter to `png.render_image` and
   `pdf.render_pages`. Do not change the behaviour of any caller that does not pass it.
4. **Rewrite the module docstring's guardrail G-1** ("no second paper size"), as
   ADR-0036 requires. COMP-007 now knows more than one sheet, but **only through an
   explicit `PageSpec`, never by guessing**. Keep the 441-extent A4 measurements and
   mark them as describing the default spec only.
5. **Measured book-spec tests.** Build a Book 1 `PageSpec` literal inside the test (the
   admin-side builder is CARD-115, so the test must not import `nonogram.admin`). Use it
   to pin AC-236..AC-239 at layout level, plus the EC-019 and stroke properties below.

Horizontal placement is **decided** (owner, 2026-09-22 (c); FR-030/FR-032 amended):
mirrored margins by page parity, drawing centred across the usable width, top edge
fixed. It is no longer a Worktree-notes choice. The measured parity criteria are
AC-272/AC-273 (CARD-115, the book builder) and AC-274..AC-276 (CARD-116, the PDF). This
card carries EC-032's layout half.

## Acceptance criteria

- **AC-236** (NFR-008) — given a Book 1 profile book holding a 15x15 puzzle with 7-deep row- and column-clue gutters (page fit 8.8 mm), when its book cell is computed, then cell == 7.5 mm.
  *test:* `TestBookCell_CappedAtStandardCell`
- **AC-237** (NFR-008) — given a 10x10 puzzle that the CLI layout prints at a 9.0 mm cell, when it is laid out in a Book 1 profile book, then cell == 7.5 mm (the book cap wins over NFR-005's curve).
  *test:* `TestBookCell_BookCapOverridesCliComfortCurve`
- **AC-238** (NFR-008) — given a Book 1 profile book holding a 30x30 puzzle with 9-deep row- and column-clue gutters, when its book cell is computed, then cell >= 4.8 mm (4.97 mm).
  *test:* `TestBookCell_ThirtyByThirtyNineDeepAboveFloor`
- **AC-239** (NFR-008) — given a Book 1 profile book holding a 30-wide x 25-tall puzzle with a 12-deep row-clue gutter, when its book cell is computed, then cell < 4.8 mm (4.61 mm) and the puzzle is flagged below the floor (FR-031).
  *test:* `TestBookCell_TwelveDeepBandFallsBelowFloor` — _this card asserts the 4.61 mm cell only; the flag is CARD-121/CARD-123._
- **AC-180** — given a fixed 30x30 puzzle request (seed 42) exported by `nonogram generate` as PNG, SVG and PDF on the commit before the book geometry lands, when the same request is exported after it lands, then all three files are byte-identical to the earlier ones.
  *test:* `TestCliExports_ByteIdenticalAfterBookGeometry` (written by CARD-113 — must stay green here)

## Engineering constraints

- **EC-019** (consistency) — For any puzzle of 10..30 cells per side, any real clue depth and any stored trim and margins, the drawn puzzle (grid plus both clue gutters) fits inside the usable area (trim minus margins minus the title band) and its cell never exceeds the 7.5 mm standard cell — and the PDF page is the trim size, for every extent, not only the measured examples.
  *test:* `PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell` — _layout half here (fit + cap for arbitrary PageSpecs, including the 4.8 mm-and-below cases that overflow only at the MIN_CELL_MM floor; state how that floor interacts); the "PDF page is the trim size" half is CARD-116._
- **EC-020** (compatibility) — For any CLI generation request, the PNG, SVG and PDF files written are byte-identical whether or not the book geometry exists — the book's page size and margins never reach the CLI's layout (CON-019), under whichever alternative the geometry DEC selects.
  *test:* `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` (CARD-113's corpus — must stay green)
- EC(ADR-0036/R1): `compute_layout` without a PageSpec, and with the default PageSpec passed explicitly, produces exactly today's A4 geometry.
  *test:* `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` (CARD-113), plus an explicit-default case added here
- EC(ADR-0037/R2): under a book PageSpec every thin rule is ≥ 0.25 mm (≥ 3 px at 300 DPI), every heavy rule is exactly 2 × thin, and strokes are pure black, for every cell size in 4.0..7.5 mm. The default spec's strokes are unchanged.
  *test:* `PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin`
- (from EC-022, layout half) under a portrait-only PageSpec the orientation is portrait and the grid is unrotated for every extent 10..30 × 10..30, and the drawing's top offset equals top margin + band.
  *test:* `PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent` — _layout-level cases here; the PDF-level cases are CARD-116._
- **EC-032** (consistency; added 2026-09-22 (c), layout half) — For any puzzle extent of 10..30 per side, any clue depth, any stored trim and margins and any page position, the gutter margin lies on the binding side of the page (left on odd pages, right on even pages), the drawing's horizontal centre is the centre of that page's usable width, and the drawing's left edge on an odd page minus its left edge on an even page equals gutter margin minus outside margin — while its top edge is identical on both.
  *test:* `PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity` — _layout-level cases here (every PageSpec parity); the PDF-level cases are CARD-116._

## Guardrails

- G-1: CLI and web A4 output stay byte-identical (CON-019, ADR-0036/R1). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden, TestCliExports_ByteIdenticalAfterBookGeometry, PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry. A red golden test is fixed in `src/`, never by regenerating `tests/fixtures/a4_golden/**`.
- G-2: NFR-005's comfort curve and NFR-006's larger-cell-wins rule stay in force for the default spec. The book spec opts out explicitly and nothing else does (ADR-0036 Neutral). test: `PropertyTest_Layout_CellSizeNeverExceedsComfortCap`, `PropertyTest_PageOrientation_LargerCellWinsTiesToPortrait` stay green unmodified.
- G-3: Do not edit `tests/fixtures/a4_golden/**` or `tests/test_export_a4_golden.py`. They are CARD-113's tripwire.
- G-4: Do not edit `src/nonogram/admin/**`, `src/nonogram/db/**` or `migrations/**`. Nothing in `export/` learns about the admin panel (ADR-0007; the import guard in `tests/test_cli.py`).
- G-5: Rollback clause: `PageSpec` is an optional parameter with a byte-identical default. No existing public signature loses or reorders a parameter.
- G-6: The default A4 spec has **no parity** and is unchanged by it (ADR-0036 clarification). test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden stays green with the parity field present.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as … (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it … (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from … (check: review-lens)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions from one. (check: review-lens)
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
- CON-019 — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's exports: for any generation request the PNG, SVG and PDF files … (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
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

- **FR:** FR-030, FR-032
- **NFR:** NFR-008, NFR-005, NFR-006
- **CON:** CON-019
- **ADR:** ADR-0036, ADR-0037, ADR-0007
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Failure matrix

No I/O, concurrency or retry boundary exists here: `PageSpec` and `compute_layout` are
pure functions of their arguments, and the renderers only allocate a Pillow image. The
boundaries that can fail are the value object's constructor (poison specs, for example
ones built from bad stored trim or margin values in CARD-115) and the layout fit (a
drawing that cannot fit). Units: 1 px = 25.4/300 mm ≈ 0.0847 mm.

| Operation / boundary | Failure mode (poison input) | Declared behaviour | Numeric bound |
|---|---|---|---|
| `PageSpec(...)` | any size, margin, band, cap or stroke that is not a finite real number (NaN, ±inf, `bool`, `str`, `None` where a number is required) | `ValueError` naming the field; no spec is created | — |
| `PageSpec(...)` | trim width or height ≤ 0 | `ValueError` | width, height > 0 mm |
| `PageSpec(...)` | a negative margin or band | `ValueError` | each margin ≥ 0, band ≥ 0 |
| `PageSpec(...)` | margins exceed the trim, or the usable area is non-positive (width − gutter − outside ≤ 0, or height − top − bottom − band ≤ 0) | `ValueError` ("usable area is non-positive") | usable width and height > 0 mm |
| `PageSpec(...)` | flat cell cap ≤ 0 or not finite | `ValueError` | cap > 0 mm |
| `PageSpec(...)` | stroke minimum ≤ 0 or not finite (`None` is allowed and means today's `cell/30` rule) | `ValueError` | minimum > 0 mm |
| `PageSpec(...)` | parity that is not `PageParity.ODD`, `PageParity.EVEN` or `None` (for example the raw string `"odd"`, `1`, `True`) | `ValueError` ("invalid parity") | — |
| `PageSpec(...)` | orientation or cap policy that is not a member of its enum (or, for the cap, a finite float) | `ValueError` | — |
| `PageSpec(...)` | a spec with no parity whose four margins differ (a drawing-sized image has one uniform border, so unequal margins have no meaning there) | `ValueError` | — |
| `PageSpec(...)` | a spec with parity whose orientation policy is `LARGER_CELL_WINS` (a placed trim page is never turned, FR-032) | `ValueError` | — |
| `compute_layout(..., page_spec=x)` | `x` is neither `None` nor a `PageSpec` | `TypeError`; nothing is computed | — |
| `compute_layout` | one clue set is empty and the other is not (unchanged) | `ValueError`, as today | — |
| `compute_layout`, default path | page fit < `MIN_CELL_MM` (unchanged; no constructible 10..30 puzzle gets there) | the floor wins and the image grows past A4, as today | cell = 24 px |
| `compute_layout`, placed (book) path | page fit ≥ `MIN_CELL_MM` (this includes every cell below NFR-008's 4.8 mm floor, which the layout does not flag; FR-031 does that in CARD-121/123) | the drawing fits the usable area exactly: its top-left and bottom-right grid and gutter boundaries lie inside `[usable_left, drawing_top] × [usable_right, usable_bottom]` in whole device pixels; `page.fits` is `True` | 0 px geometric overflow. Strokes are centred on their line, so ink can reach half the heavy rule beyond it (≤ 3 px = 0.25 mm on a 0.25 mm book stroke), which lands in the margin and never off the trim when the margin is ≥ 0.25 mm |
| `compute_layout`, placed (book) path | page fit < `MIN_CELL_MM` (2.0 mm), for example a tiny stored trim | the floor still wins (it keeps a markable cell). The drawing is anchored at the usable area's left edge instead of centred, and its top stays at top + band. It overflows right and down, `page.fits` is `False`, and the caller decides (CARD-116 refuses or flags). It never raises and never shrinks below the floor | cell_mm = 2.0 exactly; overflow = drawing width (or height) at 2.0 mm minus the usable width (or height). Pillow clips any part past the trim |
| `compute_layout`, placed path | cell cap | `cell_mm = min(cap, page fit)` computed in mm, so it never exceeds the cap, even by rounding | cell_mm ≤ cap exactly (7.5 mm on Book 1) |
| `compute_layout`, placed path | pixel quantisation of a fractional cell | grid lines at `round(x0 + i·pitch)` | every cell is within 1 px of `cell_mm`; the span of n cells is within 1 px of n·`cell_mm` |
| `compute_layout`, placed path | parity | the placed path computes in exact rationals (`fractions.Fraction`) and rounds each boundary once, half up. The usable width is exactly the same on both parities before rounding. The drawing's left edge on an odd page minus the one on an even page is the difference of two roundings of values exactly gutter − outside apart | shift is < 1 px (0.085 mm) from gutter − outside; horizontal centre within 0.5 px of the usable centre; the top and bottom edges and the cell are identical on both parities; reported usable and drawing widths differ by at most 1 px between parities |
| `_rule_widths` under a stroke minimum | the rounded `cell/30` rule falls below the minimum | thin = max(ceil(minimum px), round(cell/30)), heavy = 2 × thin | thin ≥ 3 px ≥ 0.25 mm for a 0.25 mm minimum, for every cell |
| `render_image` / `render_pages` with `page_spec` | any of the above | raises exactly what `compute_layout` raises, before any image is allocated | image size = trim px (for example 2550 × 3300 on Book 1) |

## Worktree notes

—

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)
- STRUCTURE: `PageSpec` is a frozen, slotted dataclass in `export/layout.py`, re-exported from `nonogram.export`, together with two `StrEnum` policies (`OrientationPolicy`, `PageParity`), a one-member `CellCapPolicy.COMFORT_CURVE` (the cap is `CellCapPolicy | float`) and `DEFAULT_PAGE_SPEC`. It checks its own invariants in `__post_init__`, so an invalid spec cannot exist and `compute_layout` never re-validates one. Why: this is DDD's value object, and it matches `Layout`/`GridLine`, the module's existing frozen-dataclass idiom. Enums rather than bare strings make an invalid parity or policy unrepresentable once validated.
- STRUCTURE: parity selects the **layout mode**. `parity is None` means a **drawing-sized image** with one uniform border: today's code path, and every number is read from the spec (the default spec is A4, 12 mm and so on). `parity` set means a **placed page**: Layout coordinates are trim-page coordinates, the image is the trim, and the drawing is centred across the usable width with its top at top + band. Why: a page that doesn't know which side of the spread it is on cannot put its gutter margin anywhere, so "placed" and "has a parity" are the same fact. The invariants enforce the pairing (no parity ⇒ equal margins; parity ⇒ `PORTRAIT_ONLY`), so no third, half-defined mode exists.
- STRUCTURE: on the placed path the cell is **fractional**. `cell_mm = min(cap, usable/total)` is computed exactly, in `fractions.Fraction` millimetres, from the spec's decimals (`Fraction(repr(x))`: 9.525 mm is exactly 112.5 px). Grid and gutter boundaries fall at `round_half_up(x0 + i·pitch)`, and nothing is rounded before that single step, so "fits the usable area" is exact rather than true to within a float's last bit. With float margins, Book 1's half-pixel outside margin had lost half a pixel of usable width (4.965 mm against FR-030's 4.966). Why: at 300 DPI a whole-pixel cell cannot express the ACs' numbers (4.61 mm would be 54 px = 4.57 mm; 7.5 mm would be 88 px = 7.45 mm, and 89 px exceeds the cap). A fractional pitch makes the printed average equal to the number the tile (FR-031) shows, which is what "the same value the PDF would print" requires. The same boundary arithmetic serves the default path: with an integer origin and an integer cell, `round(origin + i·cell)` is today's `origin + i·cell` exactly, and clue centres are `b_k + (b_{k+1} − b_k)//2`, which equals today's `+ cell//2`.
- STRUCTURE: `Layout` gains **one** defaulted trailing field, `page: PagePlacement | None = None`. It is `None` on the drawing-sized path, so the default path's values and golden serialization are unchanged: `golden.serialize_layout` reads an explicit field list that deliberately excludes fields added later. `PagePlacement` (frozen) carries parity, `cell_mm`, the usable box, and the drawing box in px, plus a `fits` property. Everything a caller needs to place the band and the drawing is in one value, and the admin places nothing itself (ADR-0036/R2). On the placed path `Layout.width/height` are the trim in px, `Layout.cell` is the floored nominal cell, and `Layout.margin` is the top margin in px. The renderers need no new branch for the drawing: `png.render_image` simply returns a trim-sized page.
- STRUCTURE: `header_band(layout, page_spec=None)` is additive. On a placed page the band is the strip `[usable_top, drawing_top)`, and it is drawn in place on the trim page instead of growing the canvas (`pdf.render_pages`). Why: the band's height is a spec field (ADR-0036 Neutral), and a trim page cannot grow.
- STRUCTURE: the private helpers keep their existing signatures and take a trailing keyword `page_spec=DEFAULT_PAGE_SPEC` (`_fit_cell`, `_orientation_for`, `_page_size_mm`, `_rule_widths`). The existing tests call `_fit_cell` directly, and G-2's tests stay unmodified.
- STRUCTURE: the `MIN_CELL_MM` floor interacts with EC-019 like this. On a placed page the floor still wins, as it does on A4. EC-019's fit is guaranteed and property-tested for every spec whose page fit is ≥ 2 mm, which includes every cell under NFR-008's 4.8 mm book floor (FR-031 flags those; the layout does not). Below a 2 mm page fit, which only a freakishly small stored trim reaches, the drawing anchors at the usable left edge, overflows right and down, and `page.fits` is `False`. It never raises, so the caller (CARD-116) decides. Pinned by its own property test.
- SCOPE: no edits outside Touches. `tests/fixtures/a4_golden/**`, `tests/test_export_a4_golden.py`, `admin/`, `db/`, `migrations/` and `svg.py` are untouched (svg never receives a spec).
- NOTE for anyone running `tests/fixtures/a4_golden/regenerate.py`: its `_check_field_lists_are_complete` now sees `Layout.page` and will refuse. That is intended: the golden's field list deliberately excludes fields added later (golden.py's own comment), and regeneration is never how this card, or any later one, fixes a red test (G-3).
- NOTE for CARD-115: `book_cell_mm` should return `layout.page.cell_mm`. Converting `layout.cell` from px to mm would give the floored pixel (4.57 mm, not 4.61), because on a placed page `Layout.cell` is the pitch floored to a whole pixel.
- NOTE for CARD-116/117: `pdf.render_pages(payload, page_spec=spec)` already returns two trim-sized pages with the drawing placed and today's `<name> — <tier>` header set inside the band. `Layout.page` (`PagePlacement`) gives the usable box, the band (`usable_top`..`drawing_top`) and the drawing box in trim px.
- SUMMARY: `PageSpec` value object, three policy enums, `DEFAULT_PAGE_SPEC` and `PagePlacement` in `export/layout.py`, re-exported from `nonogram.export`. `compute_layout(row_clues, column_clues, page_spec=None)` has a drawing-sized path (today's code, reading its numbers from the spec) and a placed path (portrait only, flat cap, real clue gutters, exact fractional cell, centred across the usable width by parity, top edge fixed at top + band). The ADR-0037 stroke minimum (thin ≥ ceil(0.25 mm) = 3 px, heavy = 2 × thin). An optional `page_spec` on `png.render_image`, `pdf.render_pages` and `header_band`. `_reveal` now reads cell edges off the grid lines, which gives identical rectangles on A4. G-1 is rewritten in the module docstring, and the A4 measurements are marked default-spec-only. Tests: `tests/test_layout_page_spec.py` (AC-236..239, the explicit-default golden case, PageSpec poison rows, parity numbers, renderer threading) and `tests/property/test_book_layout.py` (EC-019 with its floor cases, the ADR-0037/R2 strokes in the layout and in pixels, EC-022 over all 441 extents × 5 specs, EC-032, and the PageSpec invariant as a property). Measured on Book 1: 15×15 at 7-deep → 7.5 mm; 10×10 → 7.5 mm (9.0 on A4); 30×30 at 9-deep → 4.966 mm; 30×25 at 12/8-deep → 4.611 mm; 15×15 left edge 27.01 mm odd / 23.88 mm even, same top row. Renders for the owner: `~/Documents/nonogram-reviews/CARD-114/` (15×15, 30×30, 30×15; odd/even; puzzle/answer).
- [Scope] src/nonogram/export/__init__.py, src/nonogram/export/layout.py, src/nonogram/export/pdf.py, src/nonogram/export/png.py, tests/property/test_book_layout.py, tests/test_layout_page_spec.py
- [Build gate] impact underivable (python-pro without pytest-testmon) — full suite
- [Build gate] PASSED (full, 144s) — 3955 passed, 26 skipped; known pre-existing failure deselected: tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied
- [Scope gate] cycle 1: IN_SCOPE — 6/6 files within Touches, no guardrail hits
- [System contract] fresh lens == card section (40 rules)
- [Review 1/3] Score: 8.8 — crit: 0, imp: 0
- [Review 1/3] Score: 8.8 ✓ threshold reached + no critical/important
- [Review sync] 1 report(s) → meta/review/
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, ADR-0019/R1, CON-019 — CON-019 incl. independent branch-vs-main CLI diff over 6 requests × PNG/SVG/PDF: identical except PDF /CreationDate,/ModDate)
- [AC/EC check] All criteria/constraints ✓ (evidence): AC-236 ✓ (7.5 mm) · AC-237 ✓ (A4 9.0 → book 7.5) · AC-238 ✓ (4.97 mm) · AC-239 ✓ this card's half (4.61 mm; flag is CARD-121/123) · AC-180 ✓ · EC-019 layout half ✓ (1500-spec seeded corpus + 300 floor cases) · EC-020 ✓ · EC(ADR-0036/R1) ✓ (no-spec + explicit-default goldens, 61 ids) · EC(ADR-0037/R2) ✓ (351 caps + 12 rendered; pixel probe horizontal rules only) · EC-022 layout half ✓ (5×441) · EC-032 layout half ✓ (≥600 draws) · G-1..G-6 ✓ (goldens/admin/db/migrations untouched; G-2 tests unmodified+green; 39 signatures compared, only trailing defaulted additions). Named tests 184 passed; e2e pre-existing failure only.
- [Docs] skipped — no per-directory README in src/nonogram/export/ or tests/property/ (module docstrings are the canonical map; G-1 docstring rewritten in-card); tests/README.md is admin-wave-1 only, unaffected
- [Commit] /commit: working tree clean outside meta/ (0 fix cycles, nothing left to commit) — card commit is 9d0b40c on card/114-page-spec; ready for dispatcher merge
- [Review 1/3] Minor (non-gating, for follow-up): F-001 np.float64 trim → unnamed ValueError in _exact_mm; F-002 height-only floor overflow stays centred (matrix says anchors left); F-003 no trim upper bound (huge image alloc) — CARD-115 builder; F-004 placed-path render_pages prints '<name> — <tier>' in book band, ADR-0037/R1 forbids — CARD-116/117 must not rely on it; F-005 two A4-only sentences in layout.py docstrings. OOS: O-2 7.5 cap rests on CARD-115 passing 7.5; O-3 zero margins accepted

- [Done] main unchanged since branch base a9e70eb; the card's full-suite gate (3955 passed, pre-existing e2e failure excluded) ran on this exact tree. Merged e854cfc (--no-ff). Deferral scan: 0 hits. Handover notes pushed to CARD-115 (cell_mm), CARD-116/117 (band F-004).
