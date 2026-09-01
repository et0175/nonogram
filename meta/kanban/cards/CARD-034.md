# CARD-034: The page turns to match the grid, and the cell-size rule stops lying

**Status:** in_progress
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
**Touches:** src/nonogram/export/layout.py, tests/property/test_layout_cell_size.py, tests/test_export_pdf.py, tests/test_export_image.py
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

**Read this before touching EC-008 — the model was corrected, the CODE was already
right.** Verified at the decompose station 2026-09-01: the existing property test
is `PropertyTest_Layout_CellSizeNeverExceedsComfortCap`
(`tests/property/test_layout_cell_size.py`) and it already asserts a **ceiling
bound**, which is exactly what the amended EC-008 now states. The name the model
used to carry, `PropertyTest_Layout_CellSizeNonIncreasingInLargerDimension`,
exists nowhere in the codebase — it was a dead check ref, and the amendment
incidentally fixed it. So EC-008 needs **no rewrite of its property**. What it
needs is EXTENSION: the ceiling must be shown to still hold once rectangles and
orientation exist. Do not replace a correct test.

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
- G-5: Do not weaken, delete or rewrite `PropertyTest_Layout_CellSizeNeverExceedsComfortCap`.
  It already asserts the ceiling the amended EC-008 states — extend it to rectangles
  and to the orientation rule, and keep every existing case executing.
- G-6: `tests/test_export_image.py` uses `compute_layout` in 23 places and both it
  and `tests/test_export_pdf.py` hard-code `PAGE_WIDTH_MM`/`PAGE_HEIGHT_MM`. They are
  IN this card's Touches precisely because turning the page will reach them. Update
  them to the orientation rule where they assert page geometry; do NOT relax an
  assertion into a tautology to make it pass on both orientations.

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

- **[Card defect fixed at the decompose station, 2026-09-01]** `Touches:` named
  `tests/test_export_layout.py`, which does not exist, and omitted the two files
  that actually assert page geometry — `tests/test_export_pdf.py` (3 uses of
  `compute_layout`) and `tests/test_export_image.py` (23). Corrected before the card
  was started: a footprint declared too narrow is what makes the SCOPE GATE fire on
  a card's own legitimate work, and it is the failure mode cmd-decompose 6c source 3
  exists to prevent.

## Architecture revision (2026-09-01) — NFR-006's rule changed after cycle 1

**Reason:** cycle-1 review passed at 9.0, but its out-of-scope notes showed
NFR-006 itself was wrong. Settled with the project owner the same day.

**Was:** orientation is the grid's shape — `landscape iff columns > rows`.

**Should be:** orientation is **whichever of the two sheets prints the LARGER
cell**, ties resolving to portrait. Not a function of the grid's extent at all.

**Why the shape rule is wrong:** it states orientation over the GRID while page
fit is governed by the DRAWING, and a wide grid can draw tall behind a deep
column gutter. It is the wrong choice in **102 of 882** in-range cases, worst a
26x25 alternating-rows puzzle printing **4.57mm** on the landscape sheet its
shape asks for against **6.86mm** upright — a 33% loss. Mean printed cell in
range: shape rule 6.626mm, drawing-based 6.746mm, larger-cell-wins 6.749mm.
Larger-cell-wins is optimal by construction, and it is the only formulation
without a circularity: a drawing's extent depends on cell size, which depends on
page size, which depends on orientation.

**Delta:**
- `_orientation_for(columns, rows)` is replaced. Orientation can no longer be
  decided from the extent — compute the cell BOTH ways and keep the larger;
  equal cells resolve to portrait. Structure this so `_fit_cell` is evaluated
  per orientation without recursion through `compute_layout`.
- `Layout.orientation` stays; its meaning is unchanged from the outside.
- **Three of the five original criteria asserted unrequestable grids** (40x20,
  45x25, 20x40 — all outside CON-011's 10..30). Every criterion is now in range:
  AC-099 30x10, AC-100 26x10, AC-101 30x20, AC-102 10x30, AC-103 30x30, plus new
  AC-105 (the 26x25 witness) and AC-106 (small grids never turn).
- EC-010 restated: a function of the whole puzzle, not of (width, height). Two
  grids of identical extent can print on differently turned sheets when their
  clue gutters differ. `PropertyTest_PageOrientation_LargerCellWinsTiesToPortrait`.

**What survives unchanged:** the tall (10x30) and square (30x30) outcomes are the
same, but they are now DERIVED from the cell comparison rather than asserted as
shape rules — squares in particular are no longer a special case. Guardrails
G-1..G-5 all still apply. The cycle-1 fixes (F-001..F-004) stay: the two helpers'
orientation assertions remain correct, since they compare against
`geometry.orientation` for the sheet the puzzle is OWED — that expectation now
comes from the cell comparison rather than the extent, so both helpers need their
expectation recomputed, not removed.

**Do NOT add a small-grid floor or a minimum-gain threshold.** Both were
considered and rejected. A grid whose larger side is <= 15 already never turns,
because it is cap-bound in both orientations and the tie resolves to portrait
(swept: smallest turning dimension is 16). That is a DERIVED consequence and
AC-106 pins it; legislating it would add an arbitrary number next to the cap
table and would suppress the 5-9 turns per dimension at 16..21 that gain real
cell size.
