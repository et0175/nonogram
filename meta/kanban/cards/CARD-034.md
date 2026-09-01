# CARD-034: The page turns to match the grid, and the cell-size rule stops lying

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/034-page-orientation-follows-grid
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-7
**Idea:** —
**Wave:** 20
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, tests/test_export_layout.py, tests/property/test_layout_cell_size.py
**Review score:** —
**Started:** —
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
landscape picture at `--size 30` becomes a 30x10 grid printing at **2.29mm** on a
fixed portrait sheet — deriving the shape without turning the page actively harms
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
  - **then** the page turns to landscape and the cell prints at 6.60 mm, versus 2.29 mm on a fixed-portrait page
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

—
