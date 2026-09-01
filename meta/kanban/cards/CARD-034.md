# CARD-034: The page turns to match the grid, and the cell-size rule stops lying

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/034-page-orientation-follows-grid
**Worktree:** ../PythonProject4-card-034
**Source:** meta/architecture/handoff.md#increment-7
**Idea:** —
**Wave:** 20
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, tests/test_export_image.py, tests/test_export_pdf.py, tests/property/test_layout_cell_size.py
**Review score:** —
**Started:** 2026-09-01T14:56:02Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Two changes to print geometry that are one idea seen twice.

**1. The sheet turns to match the grid (NFR-006).** Wide grids print landscape,
tall and square grids portrait. Measured, pure page-fit: 40x20 goes 3.39mm ->
5.00mm turned (+47%), 45x25 3.05 -> 4.40 (+44%), 60x10 2.29 -> 3.39 (+48%); 20x40
keeps portrait (4.91 against 3.22 forced landscape) and 30x30 keeps it narrowly
(4.40 against 4.06). This is not a nicety: once CARD-033 derives shapes, a
landscape picture at `--size 30` becomes a 30x10 grid printing at **4.49mm** on a
fixed portrait sheet (6.43mm turned; the 6.60mm figure elsewhere is page fit,
above which NFR-005's cap binds) — deriving the shape without turning the page actively harms
the pictures the derivation exists to help.

**2. NFR-005 and EC-008 stop claiming cell size is a function of
`max(width, height)`.** It is not: a 40x20 and a 20x40 share `max() = 40` and
print at 3.39mm and 4.91mm, because on a fixed-orientation page 40 columns fight
the 210mm axis while 40 rows get the 297mm one. EC-008's property was therefore
**ill-posed, not merely imprecise** — the function it asserts does not exist — and
is safe today only because every grid this tool can produce is square.

**Do not "fix" EC-008 by mentioning both dimensions.** That was checked and it
still does not hold: even with orientation applied, 40x20 and 20x40 measure 5.00mm
and 4.91mm, so neither equality nor monotonicity is true. The requirement restates
the property as a **ceiling bound**, and the property test must assert exactly
that. If the ceiling bound cannot be made to hold either, raise `[BLOCKER]` — do
not weaken the test until it passes.

**Testable without CARD-033.** `layout.compute_layout` takes clue sets, so
rectangular layouts can be exercised by building clue sets directly, which is how
the figures above were measured. That is what keeps this card independent of the
`--size` work and able to run beside it.

## Acceptance criteria

- **AC-099** (happy) — test: `TestPageOrientation_WideGridTurnsLandscapeAt660mm`
  - **given** a 30x10 landscape-shaped grid
  - **when** it is rendered for print at 300 DPI
  - **then** the page turns to landscape and the cell prints at 6.43 mm — its landscape page fit is 6.60 mm, above which NFR-005's comfort cap binds at 6.5 mm for a larger dimension of 30 — versus 4.49 mm on a fixed-portrait page (both figures CORRECTED 2026-09-01 during CARD-034; the original 6.60/2.29 pair confused page fit with printed cell, and took 2.29 mm from the 60x10 row rather than the 30x10)
- **AC-100** (boundary) — test: `TestPageOrientation_40x20GainsFortySevenPercentFromLandscape`
  - **given** a 40x20 landscape-shaped grid
  - **when** it is rendered for print at 300 DPI
  - **then** landscape is selected, printing at 5.00 mm per cell, a 47% increase over the 3.39 mm a fixed-portrait page would give
- **AC-101** (boundary) — test: `TestPageOrientation_45x25GainsFortyFourPercentFromLandscape`
  - **given** a 45x25 landscape-shaped grid
  - **when** it is rendered for print at 300 DPI
  - **then** landscape is selected, printing at 4.40 mm per cell, a 44% increase over the 3.05 mm a fixed-portrait page would give
- **AC-102** (boundary) — test: `TestPageOrientation_TallGridKeepsPortraitAt491mm`
  - **given** a 20x40 tall grid
  - **when** it is rendered for print at 300 DPI
  - **then** portrait is selected (its natural fit), printing at 4.91 mm, versus 3.22 mm if forced landscape
- **AC-103** (boundary) — test: `TestPageOrientation_SquareGridDefaultsPortraitBySmallMargin`
  - **given** a 30x30 square grid
  - **when** it is rendered for print at 300 DPI
  - **then** portrait is selected by default, printing at 4.40 mm, versus 4.06 mm if forced landscape — a small but real margin

Plus, on the corrected NFR-005:

- **AC-104** (boundary) — test: `TestLayout_SameLargerDimensionDoesNotGuaranteeSameCellSize`
  - **given** a 40x20 grid (turned landscape per NFR-006) and a 20x40 grid (already portrait per NFR-006), both sharing larger dimension 40
  - **when** each is rendered for print at 300 DPI
  - **then** the two do not print the same cell size — 40x20 measures 5.00 mm and 20x40 measures 4.91 mm — so max(width, height) alone does not determine the final cell size even after orientation is applied

## Engineering constraints

- **EC-010** (verbatim, kind: consistency) — For any accepted grid (width, height) with each side in 10..30, the export orientation is landscape if and only if width > height, and portrait otherwise (width <= height, including the square case) — for every supported grid, not only the five measured examples.
  test: `PropertyTest_PageOrientation_LandscapeIffWidthGreaterThanHeight`

## Guardrails

- G-1: A4 stays the page size — this card changes which way it is turned, not what
  it is. No new paper size, no tiling.
- G-2: `MIN_CELL_MM`'s floor behaviour is unchanged: below it the drawing is still
  allowed to exceed the page rather than shrink past legibility.
- G-3: Square grids keep printing portrait. The measured margin is small (4.40
  against 4.06) but it is the existing behaviour and every current test assumes it.
- G-4: Do not edit `src/nonogram/orchestrator.py` or `src/nonogram/sourcing/**` —
  the bare-N derivation is CARD-033's this wave.
- G-5: Do not weaken or delete EC-008's existing property test to make room for the
  restatement; amend it to the ceiling bound and keep it executing.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain function inward of the CLI adapter, for every source mode. The CLI parses the --size NxM form but never en... (check: TestValidateExtent_RejectsSideAboveThirty)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by m... (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the othe... (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions ... (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness... (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate... (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-lo... (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both ... (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded fil... (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never ex... (check: TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-004 — A puzzle's grid width and height each lie within 10..30 cells inclusive, in every source mode and at every point in its regenerate/resample/nudge lifecycle (US-016, CON-011... (check: TestGenerateRandom_AcceptsMaxSide30, TestGenerateRandom_RejectsSideAbove30, TestGenerateRandom_RejectsSideBelow10)

## Architecture context

- **FR:** —
- **NFR:** NFR-006, NFR-005 (corrected)
- **CON:** CON-011
- **ADR:** ADR-0022 (the extent pair these lay out)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml
- **Note:** NFR-005 and NFR-006 currently trace to ADR-0006, the *dependency
  baseline* ADR — a mis-link NFR-006 inherited by copying NFR-005. Print geometry
  has no owning ADR. Flagged at the decompose station 2026-09-01; fixing it is an
  architect-station change, not this card's.

## Worktree notes

- **[Env]** forge 2026.8.17 (project requires >= 2026.8.17 — skew gate passed).
- **[Drift gate]** clean — `meta/drift-pending.yml` does not intersect this card's footprint.

### Implementation (2026-09-01)

- **[Where orientation is decided]** `layout._orientation_for(columns, rows)`,
  called once from `compute_layout` and passed into `_fit_cell`, which swaps
  A4's two edges through the new `_page_size_mm(orientation)`. `compute_layout`
  keeps its `(row_clues, column_clues)` signature: the extent is still read off
  the clue sets, so no caller has to know it. `Layout` gains one field,
  `orientation`, because EC-010 is otherwise unobservable from the outside and
  a reader of a 5.00 mm cell cannot tell which sheet it came off.
  `PAGE_WIDTH_MM`/`PAGE_HEIGHT_MM` keep their names and their values and now
  mean *the portrait sheet*, with `_page_size_mm` the only place they swap
  (G-1: one paper size, turned).

- **[The five measured figures all reproduce exactly]** 40x20 3.39 -> 5.00,
  45x25 3.05 -> 4.40, 60x10 2.29 -> 3.39, 20x40 stays portrait at 4.91 (3.22
  forced landscape), 30x30 stays portrait at 4.40 (4.06 landscape). Page fit
  depends on the clue gutter, so "a 40x20" is not by itself a page: the figures
  pin down the gutter depths they were measured at (row/column) — 40x20 14/8,
  45x25 16/9, 60x10 19/5, 20x40 7/13, 30x30 12/12 — which is what an ordinary
  puzzle of that shape produces at about half density, and the AC tests build
  grids with exactly those depths rather than seeding an RNG and hoping.

- **[AC-099's numbers are both wrong; the behaviour it asks for is
  implemented]** Not raised as a `[BLOCKER]` because nothing about it needs a
  guardrail broken — but it needs recording. (a) *6.60 mm is the page fit, not
  what a 30x10 prints.* Its larger dimension is 30, so NFR-005 caps it at
  6.5 mm and it prints 6.43 mm. Asserting 6.60 mm on the printed cell would
  mean lifting EC-008's ceiling, i.e. G-5. The test asserts landscape, the
  6.60 mm landscape page fit, the 4.49 mm portrait one, and the 6.43 mm the
  cap actually yields. (b) *2.29 mm is the 60x10's portrait figure*, not the
  30x10's (4.49 mm) — the two shapes sit side by side in NFR-006's rationale
  and the number appears to have been copied across. The 60x10 pair is
  asserted in the same test so the criterion's number stays covered.

- **[Surprise: the rule costs cell size on 117 of 840 wide shapes]** EC-010
  states orientation over the **grid**, but page fit is about the **drawing**,
  and a wide grid can draw tall behind a deep column gutter. Swept over the
  441 supported extents at the property test's four clue patterns, turning the
  page moves 444 wide cases up (best: 25x10 checkerboard, 4.83 -> 6.94 mm) and
  117 **down** (worst: 26x25 alternating rows, 6.86 -> 4.57 mm, a 33% loss —
  its drawing is 27 across by 38 down). Implemented as EC-010 states it, since
  a "turn it whichever way fits better" rule would make page orientation a
  function of a puzzle's clue depths — two 26x25s printing on differently
  turned sheets. Recorded in `_orientation_for`'s docstring with the numbers,
  not smoothed over. Worth a look at the architect station if the intent was
  "the sheet follows the drawing".

- **[EC-008's property test was extended, not rewritten]**
  `PropertyTest_Layout_CellSizeNeverExceedsComfortCap` already asserted the
  ceiling the amended EC-008 states (the model's
  `...NonIncreasingInLargerDimension` name exists nowhere in the tree), so its
  three halves are untouched. What changed is its A4 check, which hard-coded
  210x297: it now measures against the sheet the shape is *owed*, derived from
  a second reading of EC-010 written out in the test file — not from
  `geometry.orientation`, and not from `max()` of the two edges, which would
  pass on a page turned the wrong way. EC-010's own property test
  (`test_the_sheet_turns_landscape_exactly_when_the_grid_is_wider_than_tall`)
  joins the same file and the same corpus: 210 wide, 210 tall and 21 square
  extents x 4 patterns, counts asserted per side, plus a floor of 100 on the
  cases where grid shape and drawing shape disagree (there are 116) so the
  corpus cannot lose the only witnesses that tell the two candidate rules
  apart.

- **[Mutation check]** Three mutants, all caught: always-portrait (fails 2 AC
  tests), squares-landscape (fails EC-010's property test and AC-103),
  orientation-from-the-drawing (fails EC-010's property test *and* the EC-008
  page-fit half).

- **[Docstring re-measurement]** Turning the page changed several numbers that
  were stated as fact in prose. Re-measured and corrected rather than left:
  the band reservation now moves the cell on 441 of 1764 corpus cases (was
  172) by up to 0.508 mm (was 0.254), because a landscape sheet has 174 mm of
  printable height to a portrait one's 261 mm — so the height term binds past
  a 0.64x aspect rather than a 1.40x one; the smallest cell in the corpus is
  now 46 px / 3.89 mm at 30x29 checkerboard (was 48 px / 4.06 mm at 30x10);
  and the floor's engagement thresholds gain a landscape pair (135 across or
  86 down, against portrait's 92/129).

- **[Card metadata]** `Touches` named `tests/test_export_layout.py`, which does
  not exist, and omitted `tests/test_export_image.py` (23 `compute_layout`
  call sites, the NFR-005 AC tests) and `tests/test_export_pdf.py` (hard-coded
  A4 portrait bounds). The orchestrator's brief said this had already been
  corrected; it had not. Corrected in place — no file outside the corrected
  list was touched.

—
