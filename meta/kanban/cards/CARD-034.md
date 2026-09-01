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
- G-3: **AMENDED 2026-09-01 with NFR-006's rule change.** Was: "square grids keep
  printing portrait". That is false in general under the amended rule and must not
  be restored — a square whose row gutters run deeper than its column gutters draws
  wider than tall and genuinely prints larger turned (measured on the property
  corpus: 18x18 and 19x19 at random density turn; 20x20 and 30x30 stay upright).
  Removing the square special case is the POINT of the amendment. What survives is
  the specific outcome AC-103 pins: a 30x30 prints portrait, at 5.76mm against
  3.81mm turned — derived from the cell comparison, not asserted as a shape rule.
  Do not add a square branch to make the old sentence true again.
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
  cases where grid shape and drawing shape disagree (there are 129 — 121 wide, 8 tall; the 116 first recorded here was wrong, cycle-1 F-001) so the
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

### Revision implementation — larger-cell-wins (2026-09-01, after cycle 1)

Implements the `## Architecture revision` section below. The notes above stand
as the record of the shape-based version; where they conflict with these, these
are current.

- **[Where orientation is decided, and how the recursion is avoided]**
  `_orientation_for` keeps its name and its single call site in
  `compute_layout`, but takes the *drawing's* totals instead of the grid's
  extent and returns `"landscape" if turned > upright else "portrait"`, where
  each side is one `_fit_cell` call with the sheet passed in. The trap is real
  and the escape is one-directional: `_fit_cell` takes `orientation` as an
  **argument** and never consults a chosen one, so it can be evaluated per
  sheet without re-entering the chooser. `compute_layout` names the four
  numbers describing the drawing once (`drawing_columns`, `drawing_rows`,
  `larger_dimension`, `HEADER_BAND_MM`) and hands the same four to the chooser
  and then to the winning `_fit_cell` — three calls total, no recursion, and no
  way for the choice and the cell to be measured on different drawings.
  `_orientation_for` also moved below `_fit_cell` in the file, since it now
  depends on it. Signature of `compute_layout` unchanged; `Layout.orientation`
  unchanged from outside.

- **[All seven in-range AC figures reproduce exactly]** AC-099 30x10
  alternating-rows 6.4347 landscape / 5.9267 portrait; AC-100 26x10
  checkerboard 6.8580 / 4.7413 (gain 2.1167); AC-101 30x20 alternating-rows
  5.9267 portrait / 5.7573 landscape; AC-102 10x30 5.7573 / 3.8100; AC-103
  30x30 5.7573 / 3.8100; AC-105 26x25 alternating-rows 6.8580 portrait /
  4.5720 landscape (66.7% of it); AC-106 zero turns among the 144 cases at 15
  or fewer. The requirement leaves AC-102/AC-103's clue pattern unstated —
  alternating rows is the one that produces its figures, and the tests say so.
  AC-104's 40x20/20x40 pair (NFR-005, not amended) still measures 4.9953 and
  4.9107 and still lands landscape/portrait, so it needed no change.

- **[How the two helpers' expectation is computed, and why it is not
  circular]** `_assert_fits_printable_area` (image) and `_a4_bounds_pt` (PDF)
  each grew a `_owed_orientation(geometry)` helper that lays the same puzzle
  out on **both** sheets — `layout._fit_cell` twice, orientation supplied, the
  drawing's totals read off the `Layout`'s gutter depths and extent — and
  returns the sheet with the larger cell, portrait on a tie. What is under test
  is the orientation *choice*; what the oracle asks for is a *cell size*, from
  a function that takes the sheet as a parameter and has no opinion about which
  one a puzzle gets. `geometry.orientation` would have been the value under
  test compared against itself; `columns > rows` would have asserted the
  superseded rule. Cycle-1's F-002/F-003 orientation assertions stay exactly
  where they were — only the expectation behind them changed.

- **[The EC-010 property test uses a fully independent oracle]**
  `PropertyTest_PageOrientation_LargerCellWinsTiesToPortrait` (renamed from the
  `...LandscapeIff...` test) does not call `layout._fit_cell` at all:
  `_independent_cell_px` re-derives NFR-005's whole `min(cap, page_fit)`
  formula from A4's edges, the 12mm margin, the 12mm band, the five chosen cap
  values and the 2mm floor — all as literals, now pinned against the module's
  constants in the file's one tie-down test. It sweeps all 441 extents x 4
  patterns and asserts both the orientation and that `geometry.cell` equals the
  better of the two sheets. Witness floors, all measured on the corpus: 446
  turn / 1318 do not (floors 300 / 1000); 443 ties of which 279 on wide grids,
  so "ties go to portrait" is distinguishable from "ties go to the shape"
  (floors 200 / 100); **398 cases where the shape rule and this rule disagree**
  (floor 300) — the witness set the card asked for; and 152 of the 441 extents
  whose four puzzles do not all land on the same sheet (floor 100), which is
  EC-010's "not a function of (width, height)" half.

- **[Mutation results — 4 mutants, all killed]** `columns > rows` (the
  reverted shape rule): **5 tests fail** — EC-010's property test, AC-101,
  AC-105, AC-106 and AC-082[wide]. Always-portrait: 7 fail (property test,
  AC-099, AC-100, AC-106, AC-104 and both wide PDF cases). Always-landscape:
  17 fail. Tie-to-landscape (`>=` for `>`): 7 fail, incl. AC-106 and the
  property test. Source restored and verified byte-identical after each run
  (sha256 `bb4c891f61df…`). Separately confirmed the claim the image helper's
  docstring makes: with orientation forced portrait, AC-099's and AC-100's
  grids still pass the *bounds* — only the orientation assertion catches them,
  which is why that assertion has to exist.

- **[Docstring figures re-measured under the new rule]** Every stated number
  that moved: the shape rule's cost is **102 of 882** (441 extents x the two
  gutter-heavy patterns) with means 6.626mm / 6.749mm — both reproduce the
  requirement exactly. Turns in the four-pattern sweep: **446 of 1764**, none
  below a larger dimension of 16 (the requirement's rationale says 419; the
  ordinal facts it rests on — smallest turning dimension 16, concentration at
  27..30 — do reproduce, so the docstrings quote the measured 446 and the card
  records the discrepancy rather than repeating a figure that did not).
  Band-reservation cost: **353 of 1764** (checkerboard 151, alternating-rows
  118, random 74, sparse 10), still at most 0.508mm — down from the 441 the
  shape rule produced, because fewer pages are landscape now; the historical
  all-portrait figures (172, at most 0.254mm) re-measured unchanged. Smallest
  cell in the corpus: **48px / 4.0640mm**, three checkerboards (30x28, 30x29,
  30x30), all portrait — was 46px / 3.89mm at 30x29 landscape. The
  band-removal regression witness count in `_alternating_rows`'s docstring:
  **235** over the three pre-existing patterns (151/74/10), first at 10x25
  checkerboard — was 234. `_assert_the_page_fits_a4`'s and `comfort_cap_mm`'s
  claims that a 12x10 and a 10x12 "no longer share a sheet" were made false by
  this change (both are cap-bound ties and both print portrait) and were
  rewritten; the AC-082 parametrize ids `landscape`/`portrait` became wrong for
  the same reason and are now `wide`/`tall`. One pre-existing claim was
  corrected while it was being touched: "from about 20 cells a side up page fit
  is the smaller term every time" was already false before this card (560 of
  those cases were cap-bound under all-portrait) and is now stated as measured
  — 564 page-fit-bound against 800 cap-bound at 20 cells a side or more.

- **[G-3's original wording is superseded, as the revision says]** "Squares
  keep printing portrait" holds for AC-103's 30x30 (5.76mm against 3.81mm) but
  is **not** universally true any more, and cannot be under a rule with no
  square case: two random-density squares in the property corpus, an 18x18 and
  a 19x19, have row gutters deeper than their column gutters, draw wider than
  tall (25x23 and 27x24) and genuinely print larger turned. They turn. That is
  the rule working, not a defect — the revision explicitly retires the square
  special case — but it is recorded here because the guardrail's old sentence
  reads as if it forbade this.

- **[Not done, deliberately]** `meta/architecture/trace.yml`'s NFR-006 row
  still lists the five superseded test names and says "not yet implemented".
  Trace write-back is the card-close step, not this one's, and cycle 1 left it
  the same way; flagging it so it is not missed at close.

—

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
