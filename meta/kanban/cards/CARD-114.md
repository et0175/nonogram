# CARD-114: PageSpec — compute_layout learns a second sheet, only when told (book cap, portrait-only, book strokes)

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
     of the book PDF is right-hand;
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
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is at most 20 cells on its longest side, and at most 4 … (check: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns it to draft as part of that change (FR-037, FR-038; … (check: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)

## Architecture context

- **FR:** FR-030, FR-032
- **NFR:** NFR-008, NFR-005, NFR-006
- **CON:** CON-019
- **ADR:** ADR-0036, ADR-0037, ADR-0007
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
