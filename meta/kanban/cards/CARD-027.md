# CARD-027: Grid extent as a (width, height) pair through the request, `--size NxM`, and all three source modes

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/027-grid-extent-width-height-pair
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 18
**Depends on:** CARD-023, CARD-024, CARD-026
**Touches:** src/nonogram/cli.py, src/nonogram/orchestrator.py, src/nonogram/sourcing/random_grid.py, src/nonogram/sourcing/library.py, src/nonogram/sourcing/image.py, src/nonogram/difficulty.py, tests/test_cli.py, tests/test_orchestrator.py, tests/test_sourcing_random.py, tests/test_sourcing_library.py, tests/test_sourcing_image.py, tests/property/test_grid_dimensions.py, README.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The core of the increment: grid extent stops being one scalar and becomes a
`(width, height)` pair carried through the request, all three source modes, and the CLI
(FR-018, FR-019, ADR-0022/R1 and R2). Everything else in Increment 5 either precedes this
card or follows it.

1. **`orchestrator.GenerationRequest`** — `size: int | None` becomes `width: int | None`
   and `height: int | None`. It remains ADR-0012's unvalidated, syntactically-typed
   CLI/domain boundary type: a request may carry an out-of-range side all the way to the
   domain function that rejects it. The `Puzzle` aggregate's `size` property and
   `_mode_args`'s per-mode argument tuples move with it, as do
   `orchestrator.py`'s docstrings that describe extent as one number (including
   `DEFAULT_DEADLINE`'s "50x50 maximum size" comment at ~line 177, left stale by CARD-023
   because that card does not own this file).
2. **`sourcing/random_grid.py`** — `validate_size(size)` becomes `validate_extent(width,
   height)`, validating **each side** to `MIN_SIZE..MAX_SIZE` (10..30 after CARD-023) and
   naming the offending side in the error. It stays a **pure domain function inward of the
   adapter** and stays the single definition every mode delegates to (ADR-0022/R2).
   `filled_target` and `generate` take the pair; the row-slicing at the end of `generate`
   becomes `height` rows of `width` cells.
3. **`sourcing/library.py`** — `coverage(template, width, height)` and `render(template,
   width, height, threshold)`. `_axis_overlaps(source_len, target_len)` is already written
   per axis, so this is mostly threading the two target lengths to the two calls that
   currently both receive `size`. The module docstring's exact-magnification discussion
   (which sizes are whole-number magnifications of a template) is stated over one dimension
   and must be restated over both.
4. **`sourcing/image.py`** — `generate(source, width, height, rng)` calls
   `validate_extent` and passes the pair to `binarize`. CARD-026 already shipped
   `fit_crop_box`, the aspect guard and `binarize`'s target pair, so this card's image-mode
   work is the call site only — and no non-square request ever passes through an
   anisotropic stretch.
5. **`cli.py`** — `--size` accepts both forms through the **single existing flag**:
   `--size 30` means 30x30, `--size 30x20` means 30 wide by 20 tall. **Splitting the `NxM`
   token is a parsing concern and stays in argparse (ADR-0010).** Range validation does
   **not**: no `choices=`, no range-checking `type=`. A malformed token (`30x`, `x20`,
   `3x4x5`) is an argparse usage error naming the flag; an out-of-range but well-formed
   token (`40x20`) parses fine and is rejected inward by `validate_extent`. Update the
   flag's help text and `README.md`.
6. **`difficulty.py`** — `total_cells` follows the grid, which is already how it is
   computed. **Only** what is needed to keep it correct for a rectangle; the area-based
   normalizer question stays open (G-4).

## Acceptance criteria

- **AC-062** (FR-018): given the CLI invoked with `--size 30x20`, when the arguments are
  parsed, then the `GenerationRequest` carries width 30 and height 20.
  kind: happy — test: `TestCLI_ParsesRectangularSizeToken`
- **AC-063** (FR-018): given the CLI invoked with `--size 30` (the square shorthand), when
  the arguments are parsed, then the `GenerationRequest` carries width 30 and height 30.
  kind: boundary — test: `TestCLI_SquareSizeShorthandSetsBothSides`
- **AC-064** (FR-018): given the CLI invoked with `--size 30x` (a malformed NxM token),
  when the arguments are parsed, then argparse fails with a usage error naming the flag,
  and no `GenerationRequest` is constructed.
  kind: negative — test: `TestCLI_RejectsMalformedSizeToken`
- **AC-065** (FR-018): given the CLI invoked with `--size 40x20`, whose width is outside the
  supported range, when the arguments are parsed, then parsing succeeds and the request
  reaches the domain, where validation raises a size-range `NonogramError` naming the
  offending side — argparse never applies a `choices=`/`type=` range check (ADR-0010).
  kind: negative — test: `TestCLI_OutOfRangeSideRejectedByDomainNotArgparse`
- **AC-066** (FR-019): given a request for a 20x20 random grid, when the grid is generated,
  then a 20-column, 20-row black/white grid is produced.
  kind: happy — test: `TestGenerateRandom_ProducesRequestedDimensions`
- **AC-067** (FR-019): given a request for a 30x12 random grid, when the grid is generated,
  then a grid of 12 rows of 30 columns is produced, not a square.
  kind: happy — test: `TestGenerateRandom_ProducesRectangularGrid`
- **AC-068** (FR-019, INV-004): given a request for 30x30, the largest supported grid, when
  the grid is generated, then a 30x30 grid is produced without error.
  kind: boundary — test: `TestGenerateRandom_AcceptsMaxSide30`
- **AC-069** (FR-019, INV-004): given a request for a 31x30 grid, whose width is one past
  the supported maximum, when generation is requested, then the request is rejected with a
  size-range error and no grid is produced.
  kind: negative — test: `TestGenerateRandom_RejectsSideAbove30`
- **AC-070** (FR-019, INV-004): given a request for a 30x9 grid, whose height is one below
  the supported minimum, when generation is requested, then the request is rejected with a
  size-range error and no grid is produced.
  kind: negative — test: `TestGenerateRandom_RejectsSideBelow10`

Also required by ADR-0022/R2's own `check:` — the direct unit on the shared validator:
`TestValidateExtent_RejectsSideAboveThirty`.

## Engineering constraints

- **EC-005** (FR-019, verbatim from requirements.yml)
  - statement: For any requested (width, height) pair with either side outside 10..30, and
    in every source mode (random, built-in library, uploaded image), the request is rejected
    with a size-range error before any grid is produced — the bound is a property of the
    request, not of one sourcing path.
  - kind: consistency
  - instances: AC-069, AC-070
  - test: `PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30`

  This generalizes CARD-023's scalar predecessor
  (`PropertyTest_SizeRange_EverySourceModeRejectsSizeOutside10To30`) to independent width
  and height; replace that test rather than keeping both. The corpus must vary the two
  sides independently — a corpus that only ever moves them together cannot distinguish "each
  side is checked" from "the larger side is checked".

- **EC(ADR-0022/R1):** Grid extent crosses every module boundary as a `(width, height)`
  pair. No public function signature, request field, or export field in
  `src/nonogram/**` reduces a grid's extent to a single scalar `size`, and no source mode
  constructs a grid from one integer.
  test: `PropertyTest_Extent_NoPublicBoundaryReducesGridToOneScalar`

  Follow the precedent already in the repo: `tests/test_cli.py`'s structural import guard
  walks `src/nonogram/**/*.py` on disk with `ast` and fails the suite on a violation. The
  same shape works here — walk the public signatures and dataclass fields and assert no
  scalar-extent parameter survives — so the rule is enforced for modules added later, not
  just for the ones this card edits.

- **EC(ADR-0022/R2):** Each grid side is validated to 10..30 inclusive by one pure domain
  function inward of the CLI adapter, reached by every source mode; the CLI parses the
  `--size NxM` form and never enforces the range itself. For every well-formed token a user
  can type, the rejection comes from the domain, not from argparse.
  test: `PropertyTest_Extent_RangeRejectionAlwaysComesFromTheDomain`

## Guardrails

- G-1: Do not edit `src/nonogram/clues.py`, `src/nonogram/solver/**`. COMP-004 and COMP-005
  are ALREADY rectangle-native — verified empirically: an 8x14 grid solves uniquely and
  round-trips, and a 3x5 computes correct clues. The increment states they need no change;
  a diff here is a finding (test: PropertyTest_Solver_NeverFalsePositiveUniqueness,
  TestComputeClues_MatchesGridExactly).
- G-2: argparse parses, it does not judge (ADR-0010). No `choices=` and no range-checking
  `type=` appears on `--size`; a well-formed out-of-range token reaches the domain
  untouched. The existing "out of domain range values pass the parser untouched" table must
  keep asserting that for `--size` (extend it with rectangular tokens; do not delete its
  `--size` rows) (test: TestCLI_OutOfRangeSideRejectedByDomainNotArgparse).
- G-3: `--size` stays ONE flag. Do not add `--width`/`--height`, and do not add a second
  positional form. FR-018 is explicit: the CLI expresses the pair through the single
  existing flag, and the square shorthand keeps working (test:
  TestCLI_SquareSizeShorthandSetsBothSides).
- G-4: Out of scope — do not change `difficulty.py`'s area-based normalizer
  (`size_pressure`'s use of `total_cells` against `MIN_SUPPORTED_CELLS`/
  `MAX_SUPPORTED_CELLS`) or the tier weights. Whether area is the right normalizer for a
  rectangle is a deliberately OPEN question that no card in this increment decides; touch
  `difficulty.py` only as far as keeping `total_cells` correct for a rectangle requires
  (test: the existing tests/test_difficulty.py and tests/test_difficulty_tiers.py suites).
- G-5: Do not edit `src/nonogram/export/**` or `tests/test_export_*.py` /
  `tests/property/test_export_roundtrip.py`. CARD-024 already moved the export payload and
  both file formats to a width/height pair at schema v2; this card only supplies the two
  values at the single `ExportPayload(...)` construction site inside `orchestrator.py`
  (ADR-0023/R1).
- G-6: The image crop geometry and the aspect guard are unchanged — `fit_crop_box`, the >2x
  refusal predicate and `binarize`'s internals are CARD-026's and are already correct for
  any target shape. This card owns `image.py` only as far as `generate`'s signature, its
  `validate_extent` call and its call into those functions; a diff inside their bodies is a
  finding (test: PropertyTest_FitImage_CropBoxIsLargestCentredRectangleOfTargetAspect,
  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore).
- G-7: Do not edit `src/nonogram/web/**` — CARD-028 owns the web form's extent field. Note
  the ordering consequence: between this card's merge and CARD-028's, the web adapter is the
  one caller that has not been moved to the pair. If that makes the suite red rather than
  merely feature-incomplete, raise `[BLOCKER]` and escalate to the decompose station for a
  re-slice; do not fix it here.
- G-8: Do not edit `MIN_SIZE`/`MAX_SIZE` values or `MAX_SUPPORTED_CELLS`. CARD-023 already
  narrowed the range to 10..30; this card generalizes *what* is validated, not the bound.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain function inward of the CLI adapter, for every source mode. The CLI parses the --size NxM form but never en... (check: TestValidateExtent_RejectsSideAboveThirty)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by m... (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
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

- **FR:** FR-018, FR-019
- **NFR:** —
- **CON:** CON-011
- **ADR:** ADR-0007, ADR-0010, ADR-0012, ADR-0022
- **Components:** COMP-001, COMP-002, COMP-003, COMP-006
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
