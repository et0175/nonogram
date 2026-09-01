# CARD-026: Fit uploaded images to the requested grid shape, refusing a >2x aspect mismatch

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/026-image-fit-to-grid-shape
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 17
**Depends on:** CARD-023
**Touches:** src/nonogram/sourcing/image.py, src/nonogram/errors.py, src/nonogram/cli.py, tests/test_sourcing_image.py, tests/property/test_image_fit.py, tests/fixtures/
**Review score:** 4.0 (cycle 1/3), 8.0 (cycle 2/3) — fixes 303b997, c08fe50 applied
**Started:** 2026-08-31T09:45:00Z
**Closed:** 2026-08-31T15:57:07Z
**Actual:** 0.8d
**Merge commit:** 547d3179b7dfaee56c643eb89b72ddea9e414c13
**Blocked by:** —

## What to implement

The only genuinely **new algorithm** in this increment. Today `image.binarize(greyscale,
size)` crops to `square_crop_box(...)` and resizes to `(size, size)`. FR-020 generalizes
that: take the largest **centred crop of the source having the requested grid's aspect
ratio** (`width / height`), then resize that crop to `width x height`. Today's square crop
becomes the `width == height` case — the crop-not-stretch, crop-not-letterbox policy is
generalized, not replaced.

FR-021 adds the refusal that makes the generalization safe: the centred crop retains
exactly `min(r_src, r_tgt) / max(r_src, r_tgt)` of the source (`r = width / height`), so
"discards more than half the user's picture" is precisely "the ratios differ by more than
2x". Such a request is **refused with an explanatory error telling the user to crop the
picture themselves first**, rather than silently cropped to a third of itself. **The
boundary is INCLUSIVE**: retaining exactly 50% (a ratio difference of exactly 2.000x) is
accepted.

### Ordering — why this card comes BEFORE the extent pair (CARD-027)

Both new pieces are **pure functions of four integers** (`source_w, source_h, target_w,
target_h`) and are fully testable at any target shape without a rectangular request
existing. Shipping them first means the request-side pair (CARD-027) can be wired to an
already-correct crop, so a non-square image request never passes through an interim
anisotropic stretch — which ADR-0022/R3 forbids outright and which would otherwise exist
for a whole wave.

So in this card:

1. **`fit_crop_box(source_width, source_height, target_width, target_height)`** replaces
   `square_crop_box(width, height)`. The largest centred sub-rectangle of the source whose
   aspect ratio equals `target_width / target_height`: it lies entirely within the source
   bounds and touches both source edges on at least one axis. Preserve the existing
   half-pixel-bias handling on the cropped axis (discarded margins differ by at most 1
   pixel, AC-073) and the existing zero-pixel-source refusal.
2. **The aspect guard** — a pure predicate over the same four integers, applied **before**
   any conversion, dithering or solver work runs. On refusal raise a new
   `nonogram.errors.NonogramError` subclass (name it for what the user must do, not for
   where it was raised) whose message states that the user should crop the picture
   themselves before retrying (AC-077). Check `cli.py`'s `exit_code_for` MRO walk: the new
   error is grouped by what the user must do — a bad *input* — so it should fall into an
   existing group; add a case only if the walk does not already reach one.
3. **`binarize(greyscale, target_width, target_height)`** resizes to `(target_width,
   target_height)` using `fit_crop_box`. Keep the crop and resize as the single `resize(...,
   box=...)` call they are today.
4. **`image.generate` still takes the scalar `size` in this card** and calls the two new
   functions with `(size, size)`. CARD-027 flips that caller to the request's
   `(width, height)` pair; that is the whole of its image-mode work, precisely because
   this card left a correct general function behind it.
5. **The module docstring's aspect-ratio policy section** (the "Stretch / Crop /
   Letterbox" argument at the top of `image.py`) is normative and must move with the code:
   it currently justifies a *square* crop against an AC-009 that has been superseded by
   AC-059. Restate it over the requested grid's ratio, and record the refusal rule.
6. **CON-013 scope note** — image sourcing targets high-contrast black-and-white
   silhouettes only, not photographs. Say so in the docstring if it does not already;
   photographic input is out of scope rather than unsupported-with-a-warning.
7. **Fixtures.** AC-071..AC-079 name concrete source dimensions (563x980, 600x600,
   980x563). `pictures/eagle-silhouette1.jpg` is the increment's worked example; the
   synthetic `WIDE`/`TALL`/`BANDS` fixtures already in `tests/test_sourcing_image.py` are
   the right vehicle for the geometry cases.

## Acceptance criteria

- **AC-071** (FR-020): given a 563x980 portrait silhouette and a requested 15x30 grid
  (target ratio 0.500), when the crop box is computed, then the crop box has aspect ratio
  0.500 and is the largest such rectangle fitting inside 563x980 (490x980).
  kind: happy — test: `TestFitImage_CropsToRequestedAspectRatio`
- **AC-072** (FR-020): given a 563x980 source and a requested 20x20 grid (target ratio
  1.000), when the crop box is computed, then the crop box equals the one today's
  `square_crop_box` returns for 563x980, so the square case is unchanged by the
  generalization.
  kind: boundary — test: `TestFitImage_SquareGridReproducesSquareCropBox`
- **AC-073** (FR-020): given a 563x980 source and a requested 15x30 grid, when the crop box
  is computed, then the discarded margins on the cropped axis differ by at most 1 pixel, so
  the crop is centred.
  kind: boundary — test: `TestFitImage_CropIsCentredOnBothAxes`
- **AC-074** (FR-020): given a 563x980 source and a requested 15x30 grid, when the image is
  converted end to end, then the resulting grid is exactly 15 columns by 30 rows, with no
  letterbox padding row or column and no anisotropic stretch of the crop.
  kind: boundary — test: `TestFitImage_ProducesExactDimensionsWithoutLetterbox`
- **AC-075** (FR-021): given a 600x600 square source (r_src 1.000) and a requested 30x15
  grid (r_tgt 2.000), ratios differing by exactly 2.000x so the retained fraction is exactly
  0.500, when generation is requested, then the request is accepted and a 30x15 grid is
  produced.
  kind: boundary — test: `TestAspectGuard_AcceptsExactlyTwoFoldRatioDifference`
- **AC-076** (FR-021): given a 600x600 square source (r_src 1.000) and a requested 30x14
  grid (r_tgt 2.143), retained fraction 0.467, when generation is requested, then the
  request is refused with an aspect-ratio error and no grid is produced.
  kind: negative — test: `TestAspectGuard_RefusesRatioDifferenceAboveTwoFold`
- **AC-077** (FR-021): given the aspect-ratio refusal raised for a 600x600 source into a
  30x14 grid, when the error is rendered to the user, then the message states that the user
  should crop the picture themselves before retrying.
  kind: negative — test: `TestAspectGuard_RefusalMessageSuggestsManualCrop`
- **AC-078** (FR-021): given a 980x563 landscape source (r_src 1.741) and a requested 12x30
  portrait grid (r_tgt 0.400), retained fraction 0.230, when generation is requested, then
  the request is refused with the same aspect-ratio error, so the threshold is symmetric in
  which of the two is the wider.
  kind: boundary — test: `TestAspectGuard_ThresholdIsSymmetricInSourceAndTarget`
- **AC-079** (FR-021): given a 563x980 portrait silhouette (r_src 0.574) and a requested
  15x30 grid (r_tgt 0.500), retained fraction 0.870, when generation is requested, then the
  request is accepted and a 15x30 grid is produced.
  kind: happy — test: `TestAspectGuard_AcceptsWellMatchedPortraitSource`
- **AC-059** (FR-003, supersedes AC-009): given a 563x980 portrait source image (ratio
  0.574) and a 15x30 target grid (ratio 0.500), whose ratios differ by 1.15x — inside
  FR-021's accepted 2x band — when the image is converted, then the output grid has exactly
  15 columns and 30 rows.
  kind: boundary — test: `TestConvertImage_ProducesExactTargetDimensionsWithinAcceptedRatioBand`

  AC-009 is superseded (its unqualified "differs from the target grid" became false the
  moment a >2x difference became a refusal). Preserve it verbatim in
  `requirements.yml`-mirroring comments if the test file references it; do not reuse its
  test name `TestConvertImage_ProducesExactTargetDimensions`.

## Engineering constraints

- **EC-006** (FR-020, verbatim from requirements.yml)
  - statement: For any source image dimensions and any accepted (width, height) request,
    the crop box is the largest centred sub-rectangle of the source whose aspect ratio
    equals width/height: it lies entirely within the source bounds and touches both source
    edges on at least one axis, for every such input.
  - kind: consistency
  - instances: AC-071, AC-072, AC-073
  - test: `PropertyTest_FitImage_CropBoxIsLargestCentredRectangleOfTargetAspect`
- **EC-007** (FR-021, verbatim from requirements.yml)
  - statement: For any source image dimensions and any (width, height) pair in 10..30, the
    request is accepted if and only if `min(r_src, r_tgt) / max(r_src, r_tgt) >= 0.5` with
    `r = width/height` — every accepted request therefore retains at least half the source
    area under FR-020's centred crop, and every request that would retain less is refused
    before any cropping, dithering or solver work runs.
    (Wording narrowed 2026-08-31 by the EC-007 amendment this card raised — see
    `meta/architecture/inputs/raw-requirements.md`. "conversion" was too broad.)
  - kind: consistency
  - instances: AC-075, AC-076, AC-078
  - test: `PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore`

  "If and only if" is the whole claim: a corpus that only checks refusals passes on a guard
  that refuses everything. Both directions, and the inclusive boundary explicitly.
- **EC(ADR-0022/R3):** For every source and every target shape, the fitted image is
  produced by a centred crop followed by an isotropic resize — never by stretching the
  whole source and never by padding. No output carries a letterbox row or column, and the
  crop's own aspect ratio equals the target's for every input, not just the examples.
  test: `PropertyTest_FitImage_NeverStretchesAndNeverPads`

## Guardrails

- G-1: Do not edit `src/nonogram/clues.py`, `src/nonogram/solver/**` — COMP-004 and
  COMP-005 are already rectangle-native; an 8x14 grid solves uniquely and round-trips
  today, verified empirically (test: PropertyTest_Solver_NeverFalsePositiveUniqueness).
- G-2: Out of scope — do not introduce the `(width, height)` pair on `GenerationRequest`,
  the CLI's `--size NxM` parsing, or `validate_extent`; and do not change
  `image.generate`'s signature. This card ships the pure crop/guard functions and
  `binarize`'s target pair; wiring the request's extent through is CARD-027's (FR-018,
  ADR-0022/R1).
- G-3: Do not edit `src/nonogram/sourcing/random_grid.py` or
  `src/nonogram/sourcing/library.py` — image mode's use of the shared
  `random_grid.validate_size` stays a delegation, restated nowhere (ADR-0022/R2). Do not
  change `MIN_SIZE`/`MAX_SIZE`: CARD-023 already narrowed them.
- G-4: The refusal happens **before** any conversion work. Cropping, dithering, clue
  derivation and every solver call must be unreachable for a refused request, and that is
  the reason the guard is a predicate on four integers rather than a check on a converted
  grid (test: TestAspectGuard_RefusesRatioDifferenceAboveTwoFold).
  **Narrowed by review cycle 2, and the narrowing is the fix for F-002, not a retreat from
  it.** Loading and greyscaling are unreachable for every request the *header probe*
  refuses — the common case, and the only case before this card. They are **not**
  unreachable on the re-check path: where the header and the decode disagree about the
  picture's shape (rows 13, 14), the refusal necessarily comes after `load_greyscale`,
  because the extent being judged is the one only the decode knows. Everything downstream
  of that decode is still unreachable. EC-007's wording as it stood ("refused before any
  conversion") was *literally false* on that path. A card may not edit a requirement it is
  implementing, so it was raised to forge:architect as a requirements delta via
  `inputs/raw-requirements.md`; **the amendment landed 2026-08-31** and EC-007 now reads
  "refused before any **cropping**, dithering or solver work runs" (same id, same kind,
  same instances, same test — a wording correction, not a supersession). This guardrail
  and the requirement now agree.
- G-5: The 2x boundary is INCLUSIVE. A retained fraction of exactly 0.500 is ACCEPTED. Do
  not implement it as a strict `>` on the retained fraction or as a float comparison that
  makes the exact case flaky — AC-075 exists precisely to pin the boundary that a naive
  implementation gets wrong (test: TestAspectGuard_AcceptsExactlyTwoFoldRatioDifference).
- G-6: The existing image behaviours are unchanged: Floyd-Steinberg error diffusion and the
  ink-is-a-filled-cell binarization (FR-003, AC-007), the "cannot read image" failure for an
  unreadable or corrupt file (AC-008), the alpha-flatten-onto-white step, and the bounded
  pixel-nudge recovery loop and its reporting (FR-013/FR-014, INV-003). Only the crop and
  the target shape move (test: TestConvertImage_ProducesDitheredGrid,
  TestConvertImage_RejectsUnreadableFile, TestNudge_ReportsFailureAtCap).
- G-7: Do not edit `src/nonogram/orchestrator.py`, `src/nonogram/export/**`,
  `src/nonogram/web/**` — the refusal is a domain error that funnels through
  `NonogramError` exactly as every other one does; no orchestrator or adapter special-case
  is needed for it (ADR-0007, ADR-0010).

## System contract

- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its
  current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has
  confirmed exactly one solution (US-005, FR-011). (check:
  TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library
  mode, resample attempts for difficulty matching, or pixel-nudge attempts for image
  mode) never exceeds its configured maximum bound (NFR-002). (check:
  TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound,
  TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-004 — A puzzle's grid width and height each lie within 10..30 cells inclusive, in
  every source mode and at every point in its regenerate/resample/nudge lifecycle
  (US-016, CON-011, FR-019). (check: TestGenerateRandom_AcceptsMaxSide30,
  TestGenerateRandom_RejectsSideAbove30, TestGenerateRandom_RejectsSideBelow10)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted
  as unique must never actually have 0 or more than 1 solutions. This is the mandatory
  correctness property the whole tool depends on. (check:
  PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback)
  only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052
  as a gate-enforced mandatory constraint — a `check:` the system contract actually
  collects — so BCON-0001's socket-reach half is discharged by more than a threshold
  visible only in requirements.yml. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as
  cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header
  naming a non-loopback host), and refuses any absolute-form request target whose
  authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced
  mandatory constraint — a `check:` the system contract actually collects — so
  BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach
  half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets
  Host from the request's target url, not from the page's origin. (check:
  PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE
  project-wide and applies to every source mode (random, built-in library, uploaded
  image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range
  FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019
  restates the behaviour over the narrowed range. (check:
  PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded
  source image's by more than 2x is refused with an explanatory error rather than
  converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) /
  max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule
  "never silently discard more than half the user's picture". Retaining exactly 50% (a
  ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (check:
  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only —
  routing, form rendering, request parsing, and mapping onto
  orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py;
  it may import the orchestrator but no capability module may import it or cli.py.
  (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No
  public function signature, request field, or export field reduces a grid's extent to a
  single scalar "size", and no source mode constructs a grid from one integer. (check:
  review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain
  function inward of the CLI adapter, for every source mode. The CLI parses the --size
  NxM form but never enforces the range itself. (check:
  TestValidateExtent_RejectsSideAboveThirty)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a
  centred crop, never by stretching and never by padding. A request whose grid and
  source aspect ratios differ by more than 2x is refused rather than cropped. (check:
  TestFitImage_RefusesRatioMismatchBeyondTwice)


## Architecture context

- **FR:** FR-003, FR-020, FR-021
- **NFR:** —
- **CON:** CON-012, CON-013
- **ADR:** ADR-0007, ADR-0022
- **Components:** COMP-003
- **Trace:** meta/architecture/trace.yml
| 18 | `generate` | the row-14 re-check, at a **square** target | Behaviourally inert **today**, and deliberately kept anyway. The guard's condition is symmetric under transposition of the source extent when `target_width == target_height`, and an EXIF disagreement is always a transposition (orientations 5..8 exchange the axes; 1..4 leave the extent alone) — so on the only targets `generate` accepts under G-2 the re-check can never change a verdict. Proved by sweep: **0 differing verdicts in 94,269 square cases; 35,104 of 101,761 rectangular ones differ.** It is therefore correct, unreachable-as-behaviour, and load-bearing the moment CARD-027 wires the `(width, height)` pair in — which is why it is written now, in the function CARD-027 will change, rather than left as a note. Consequence for the oracle, declared rather than discovered: deleting the re-check from `generate` alone kills no test, because the observable path today is the `_convert` mirror | Every square request; nothing else exists yet | `test_the_guard_judges_the_extent_the_crop_will_actually_use` and `test_the_guard_runs_before_the_picture_is_decoded` both kill the mutant **in the mirror** (verified cycle 2); no test pins `generate`'s own copy until CARD-027 |

## Failure matrix

Declared behaviour per operation x failure mode. Every row is exercised by a
named test; "bound" says how far the declared behaviour reaches. Wrong-but-
declared beats undeclared: where a row records a deliberate imperfection (the
one-pixel clamp, the PNG-EXIF gap) it says so and says what it costs.

| # | Operation / boundary | Failure mode | DECLARED behaviour | Bound | Test |
|---|---|---|---|---|---|
| 1 | `fit_crop_box` | a source axis is 0 or negative | `UnreadableImage`, message `image has no pixels to convert (its size is 0x10)` — the user's *file* is the reason, so it is the same input error as an undecodable one. Preserved verbatim from `square_crop_box`. | Checked first, before any ratio arithmetic, for every target shape | `test_an_image_with_no_pixels_is_an_input_error`, `test_property_a_degenerate_source_is_refused_before_the_ratio_is_considered` (441x3x2 cases) |
| 2 | `validate_aspect_ratio` | a source axis is 0 or negative | Same `UnreadableImage`, raised **before** the ratio is considered — a zero-extent source has no ratio to judge | Same | same two tests |
| 3 | `fit_crop_box` / `validate_aspect_ratio` | a target extent is 0 or negative | `ValueError` (`grid extents are at least 1 cell a side, got 0x20`) — **not** a `NonogramError`, so the CLI never maps it to an exit code. Grid extents arrive validated to 10..30 (CON-011), so a zero is a wiring bug, exactly as `nudge`'s zeroth attempt is | Any non-positive integer on either axis | `test_a_zero_extent_grid_is_a_caller_bug_and_not_an_input_error` |
| 4 | `fit_crop_box` | source smaller than the target grid (upscaling) | Allowed, no special case. The crop is computed identically and Pillow upscales it to the grid. There is no minimum source size | Every source down to 1x1; the grid is still exactly `target_width x target_height` | `test_property_fit_image_crop_box_is_the_largest_centred_rectangle_of_target_aspect` (corpus includes 1x1, 2x3, 1x30, 30x1) |
| 5 | `fit_crop_box` | degenerate 1xN / 2xN source where the floored crop extent would be **0** px | Clamped to 1 px. The crop's ratio is then **not** the grid's — a declared, deliberate imperfection: a zero-extent box is not a usable `resize` argument, and the alternative (refusing) would reject a request the guard accepted | Reachable only when the exact crop extent is < 1 px; inside the accepted 2x band that needs a source axis of 1 or 2 px. Swept 1..39 x 1..39 sources against all 441 grid shapes: the only accepted-and-clamped source shapes are **(1,1), (1,2), (2,1)**, and the resulting ratio deviation is bounded by the guard's own 2x band — worst case measured **1.0 relative** (a 1x1 source into a 10x20 grid yields a 1x1 crop, ratio 1.0 against a target 0.5). Reachable through the CLI: `generate` on a 1x1 PNG at size 10 returns a 10x10 grid (measured) | the same property test (bracket has an explicit `exact < 1 -> cropped == 1` branch) |
| 6 | `fit_crop_box` | integer overflow or rounding on the crop box | Cannot occur. All arithmetic is Python integer multiply + floor-divide, arbitrary precision (verified at 2^40 x 2^41). Rounding is one floor on one axis, and the two discarded margins differ by at most 1 px with the extra pixel on the **far** side | Every source extent Pillow can decode | `test_fit_image_crop_is_centred_on_both_axes` (margins 36 / 37), property test claim 4 |
| 7 | `validate_aspect_ratio` | ratios differ by **exactly** 2.000x | **ACCEPTED** — the boundary is inclusive (G-5). Decided by `2 * min(a, b) >= max(a, b)` on integer cross-products; no float is involved in the decision | All 441 grid shapes x 3 scales, both orientations, constructed exactly | `test_aspect_guard_accepts_exactly_a_two_fold_ratio_difference` (AC-075), `test_property_aspect_guard_pins_both_sides_of_the_inclusive_boundary` (2646 constructed boundary cases) |
| 8 | `validate_aspect_ratio` | ratios differ by one pixel **past** 2x | `ImageNeedsManualCrop`, message names both extents, the retained percentage and says `Crop the picture yourself to roughly the grid's proportions first`. The percentage is **floored, not rounded** (`100 * kept // whole`): rounding reported 401x200 -> 20x20 (retains 0.4988) as `50% of the picture` while keeping exactly 50% is the *accepted* boundary, so the message contradicted the rule it was enforcing. Floored it reads 49%, and every refusal now reports at most 49% (measured: 0.4988 -> 49%, 0.4667 -> 46%; max reported refusal is exactly 49 over a 199x199x20 sweep). Side effect, declared so it is not rediscovered: the message can now sit one point below an AC that quotes the unrounded fraction — AC-078 quotes 0.230 for 980x563 -> 12x30 where the message reads `22%` (true value 0.2298). Both are correct; only the convention differs | Same corpus, `source_width + 1` on the exactly-2x source | same two tests + `test_aspect_guard_refusal_message_suggests_a_manual_crop` (AC-077) |
| 9 | CLI | `ImageNeedsManualCrop` reaches the adapter | exit code 3 `INVALID_INPUT` — the same group as a bad size or an unreadable file, because the user changes what they passed in. A row of its own in `_EXIT_CODES`: the MRO walk reaches nothing else, since the error deliberately does **not** subclass `UnreadableImage` | Every raise site | `test_every_domain_error_has_an_exit_code`, `test_domain_error_maps_to_its_exit_code[ImageNeedsManualCrop]` |
| 10 | `probe_extent` | unreadable / corrupt file (bad header) | `UnreadableImage` (`cannot read image '<path>': ...`) — AC-008's error, raised **before** the aspect ratio is considered, because the shape is not known at all | Every `OSError` / `ValueError` / `UnidentifiedImageError` / `DecompressionBombError` Pillow raises at open. A file whose header parses but whose EXIF block does not is **not** in this set and is not an unreadable picture — see row 17 | `test_the_probe_reports_an_unreadable_file_as_one`, `test_convert_image_rejects_an_unreadable_file_that_is_corrupt` |
| 11 | `generate` | valid header, corrupt/truncated **body** | If the shape fits: the header read succeeds, the guard passes, and the decode fails with `UnreadableImage`. If the shape does not fit: `ImageNeedsManualCrop` comes back instead and the body is never decoded. So a refused request can mask a corrupt file — declared, and acceptable, since both messages are actionable and the aspect one is the cheaper truth | Any file whose header parses | `test_the_guard_runs_before_the_picture_is_decoded` (asserts *both* branches on one file) |
| 12 | `generate` | aspect refusal (G-4) | No pixel decode, no greyscale, no dither, no clue derivation, no solver call. Only the header is read. This is why the guard is a predicate on four integers | Every request the **header probe** refuses — which is every refused request except row 14's badly-chunked PNG, where the decode happens first and only the dither, the clue derivation and the solver stay unreachable | `test_the_guard_runs_before_the_picture_is_decoded`, `test_aspect_guard_refuses_a_ratio_difference_above_two_fold` (AC-076) |
| 13 | `probe_extent` | EXIF orientation | The **displayed** extent is returned: axes exchanged for exactly orientations 5..8, matching `ImageOps.exif_transpose`. 1..4 and any value outside the defined range leave the extent alone in both | **JPEG, PNG and WEBP** — measured: those three are the formats whose raw EXIF block `Image.open` puts in `info`. **TIFF carries none there** (`info` has no `exif` key at all), so `_header_orientation` returns `None` for every TIFF. That does **not** make probe and loader agree on one, and cycle 2 refuted the claim that it did: Pillow's TIFF reader applies the orientation to `size` at `Image.open`, and `exif_transpose` then applies it a **second** time. A 60x40 raster saved with `tiffinfo={274: 6}` probes `(40, 60)` and decodes `(60, 40)` (measured, Pillow 12.3.0) — so an orientation-tagged TIFF is a second, independent member of row 14's disagreement class, reached by a different mechanism than the PNG. All nine values measured against `load_greyscale(...).size`, not inferred from the four-value set | `test_the_probe_honours_exif_orientation` (parametrised over 1..8 plus an out-of-range 9; each asserts both the expected extent and equality with `load_greyscale`), `test_the_probe_reads_the_repo_fixtures_at_their_stored_extent` (the five repo fixtures, which the test now asserts carry no EXIF, so it is a no-orientation claim and is named as one) |
| 14 | `probe_extent` | EXIF present but **not** in the header (a PNG `eXIf` chunk after `IDAT`) | The probe does not see the orientation and reports the **stored** extent, while `exif_transpose` rotates the pixels — the one input on which probe and decode disagree. `generate` (and `_convert`) therefore **re-run the guard on the decoded extent whenever it differs from the probed one**, so the crop is never judged on a shape it will not use. Cost, both directions measured on a 563x980-stored / 980x563-displayed PNG: a 15x30 request (retains 0.287 of the displayed picture) is **refused after the decode instead of before it** — it used to be silently accepted, which is what violated CON-012; and a 30x15 request (retains 0.870) is **refused when it should be accepted**, because the cheap probe refuses it before the decode that would have corrected the shape. A false refusal carrying an actionable message is the acceptable half of the trade; discarding 71% of the picture in silence is not. EC-007 as **originally worded** ("before any conversion") was false on this path, and cycle 2's F-102 is what caught it; the requirement has since been narrowed to "before any **cropping**, dithering or solver work runs" (2026-08-31), which does hold here: the re-check sits between `load_greyscale` and `binarize`, so the crop, the dither, the clue derivation and the solver are all still unreachable — only the decode is paid for. Not closed at the probe because `Image.getexif()` on a PNG calls `load()`, decoding every PNG on every conversion and destroying row 12's guarantee | **Not a format, a mechanism: any source whose `Image.open` extent differs from `exif_transpose`'s.** Two members measured — a PNG whose `eXIf` chunk follows `IDAT` (the header parse never sees the orientation) and an orientation-tagged TIFF (the orientation is applied twice, row 13). The cost is not one example: swept over all 441 grid shapes against the 563x980/980x563 disagreement, **105 are accepted, 168 are refused after the decode (the correct outcome, and the CON-012 fix), and 168 (38%) are false refusals**. Identical for the TIFF construction. G-4 as narrowed, not as originally written: the re-check is downstream of a decode that a probe-refused request never reaches, but a re-check-refused request does pay for it | `test_the_guard_judges_the_extent_the_crop_will_actually_use` (asserts the disagreement, both refusals and an accepted 20x20 conversion through the same file) |
| 15 | `binarize` | target extent not validated by the caller | `binarize` assumes validated extents, exactly as it assumed a validated `size` before this card. A caller that skips the guard gets a hard crop rather than an error. `generate` is the only entry point and validates both the range and the ratio first | — | `test_the_size_rule_is_checked_before_the_file_is_opened` (the range half, unchanged) |
| 16 | `binarize` | crop box with a zero-area axis reaching `resize` | Unreachable: row 5's clamp guarantees both extents >= 1 px | Every input `fit_crop_box` accepts | property test claim 1 (`0 <= left < right <= source_width`) |
| 17 | `probe_extent` | header parses, EXIF block is **corrupt** | `_header_orientation` is total: any parse failure is answered as "no orientation", which is independently what `exif_transpose` concludes, so the picture converts at its stored extent. Was a **regression** — `Image.Exif().load` raises `SyntaxError: not a TIFF file` on a bad magic and `struct.error: unpack requires a buffer of 4 bytes` on a block cut off inside the TIFF header (both measured, Pillow 12.3.0); neither is in row 10's set and neither is a `NonogramError`, so both escaped `cli.exit_code_for` as a stack trace on a file that converted cleanly at base `cbf5ae2` | Any exception the EXIF parser raises — caught as `Exception`, because the set a third-party header parser can raise is not enumerable and every member of it means the same thing here | `test_a_corrupt_exif_block_is_not_an_unreadable_picture` (both crafts; asserts probe == `load_greyscale` size and a full `generate` to a 20x20 grid) |

## Worktree notes

- **[Env]** forge 2026.8.17, skew gate clean. Baseline 1314 passed, 1 xfailed.
- **[Drift gate]** ⚠ `src/nonogram/sourcing/image.py` has unprocessed drift
  events in `meta/drift-pending.yml` (2026-08-27/28, predating the CARD-018/022/
  023/025 merges). `drift.gate` unset → default `warn`: noted, proceeding.
- **[Fixtures]** ⚠ `pictures/` is NOT visible in the worktree — those files are
  staged-but-uncommitted in main, so no branch can see them. AC-071..079 cite
  `pictures/eagle-silhouette1.jpg` (563x980) as the increment's worked example;
  it is illustrative, and the card already names the synthetic
  `wide.png`/`tall.png`/`bands.png` in `tests/fixtures/` as the right vehicle
  for the geometry cases. All four fixtures confirmed present. Same class of
  worktree-meta staleness that hid `docs/cell_size.md` from CARD-025.

### Review cycle 1 -> 2: the eight findings, and what was measured

Report: `meta/review/20260831T113303Z-CARD-026-cycle1.yml` (score 4.0; 1
critical, 3 high, CON-012 and ADR-0022/R3 both VIOLATED). Every figure below
was measured against this tree in this session.

- **F-001 (critical, a regression) — fixed.** `_header_orientation` is now
  total: the `Image.Exif().load` sits in its own `try/except Exception` and a
  parse failure answers `None`, which is independently what `exif_transpose`
  concludes about the same block. Measured before the fix, on a JPEG whose APP1
  segment is rebuilt by hand with a correct length and a nonsense payload:
  `Exif\x00\x00\xff\xff\xff\xff\x00\x00\x00\x08` -> `SyntaxError: not
  a TIFF file`; `Exif\x00\x00MM\x00\x2a\x00` (cut off inside the eight-byte
  TIFF header) -> `struct.error: unpack requires a buffer of 4 bytes`. After the
  fix both files probe to `(60, 40)`, agree with `load_greyscale(...).size`, and
  `generate(path, 20, rng)` returns a 20x20 grid. Widening `_UNREADABLE` was
  rejected: it would report a perfectly readable picture as unreadable. A
  *complete* TIFF header pointing at a missing IFD does **not** raise (Pillow
  warns and yields no tags), so it is not one of the crafts — measured, not
  assumed. (Cycle 2 checked the attribution: the cycle-1 report never said
  "IFD" — it said "a truncated block", which is accurate. The measurement
  stands; it corrects a claim nobody made.) New row 17.
- **F-002 (high; CON-012 + ADR-0022/R3) — fixed, G-4 intact.** `generate` (and
  the `_convert` mirror in the test tree) re-runs `validate_aspect_ratio` on
  `greyscale.size` when it differs from the probed extent. Measured on a 563x980
  PNG with a valid `eXIf` orientation-6 chunk spliced in after `IDAT`: probe
  reports (563, 980), the decode produces (980, 563). Before: a 15x30 request
  was ACCEPTED and retained 0.287 of the displayed picture. After: refused with
  the manual-crop error. The declared residue is the other direction — a 30x15
  request retains 0.870 and is still refused, before the decode, by the cheap
  probe. Row 14 now states both directions instead of "a crop along the stored
  axis". G-4 holds: the re-check is downstream of a decode no refused request
  reaches.
- **F-003 (high) — fixed.** `test_the_probe_honours_exif_orientation` is
  parametrised over 1..8 plus an out-of-range 9 on one stored 60x40 raster, and
  each case asserts both the expected extent and equality with
  `load_greyscale(...).size`. The vacuous companion is renamed
  `test_the_probe_reads_the_repo_fixtures_at_their_stored_extent` and now
  asserts what made it vacuous (`"exif" not in opened.info` for all five
  fixtures), so it is a no-orientation claim that says so. Row 13's format bound
  corrected by measurement: JPEG, PNG and WEBP populate `info["exif"]`; TIFF
  does not, and `exif_transpose` is inert on one, so probe and loader still
  agree.
- **F-004 (high) — fixed and mutation-proved.** The brute-force search now
  bounds the box from **above** as well: with `(W, H)` the largest exact-ratio
  rectangle the search found and `(p, q)` the target ratio in lowest terms, the
  box must reach neither `W + p` nor `H + q`. Mutants applied in memory and
  reverted, running that one test:

  | mutant | cycle-1 oracle | fixed oracle |
  |---|---|---|
  | `return (0, 0, source_width, source_height)` | SURVIVED | **KILLED** |
  | crop the other axis | SURVIVED | **KILLED** |
  | `ceil` instead of `floor` | SURVIVED | **KILLED** |
  | unmutated baseline | passes | passes |

  Renamed to `..._is_bracketed_by_the_exact_ratio_rectangles_that_fit`, and the
  docstring that claimed the two named mutants were caught now says which bound
  catches them.
- **F-005 (medium) — fixed.** The refusal percentage is floored
  (`100 * kept // whole`), so 401x200 -> 20x20 reads `49% of the picture`
  instead of `50%`, and every refusal reports at most 49% (refusal means
  `2*kept < whole`). Both figures pinned in
  `test_aspect_guard_refusal_message_suggests_a_manual_crop` (49% and 46%),
  together with the accepted 400x200 neighbour that must raise nothing.
- **F-006 (medium) — fixed, both halves.** (a) The symmetry property now counts
  both verdicts (measured split 405 accepted / 395 refused of 800; floors set at
  100). Measured: before, an accept-everything guard and a refuse-everything
  guard both survived it; after, both fail it. (b) The float claim is struck and
  replaced by what was measured: substituting `(kept / whole) >= 0.5` for
  `2 * kept >= whole` leaves all four guard properties green, because with
  sources <= 4000 px and grid sides <= 30 both cross-products stay under 120000,
  are exactly representable, and `x / 2x` is exact. The integer form stays as a
  bound that does not need re-checking when the input bound moves, and the
  docstring now says that rather than claiming a test catches it. The module
  docstring's blanket per-side promise is narrowed to the properties that carry
  it, with the measured splits (796/704 of 1500 on the primary EC-007 corpus).
- **F-007 (medium) — fixed.** Rows 13 and 5 rewritten above. Row 5's clamp now
  carries its magnitude: swept 1..39 x 1..39 sources against all 441 grid
  shapes, the only accepted-and-clamped source shapes are (1,1), (1,2) and
  (2,1), and the worst relative ratio deviation is exactly **1.0** (a 1x1 source
  into a 10x20 grid), i.e. bounded by the guard's own 2x band. A 1x1 PNG at
  size 10 does reach `generate` and returns a 10x10 grid.
- **F-008 (low) — fixed.** The three assertions implied by the pinned box in
  `test_fit_image_crops_to_the_requested_aspect_ratio` are replaced by one
  independent derivation (the widest column count whose `2 * columns` rows fit
  in 980, found by search over the source width) compared against both the
  search result and the criterion's literal; the implied `abs(near - far) <= 1`
  in the centring test is dropped with a note saying why. The two unclosed
  `load_greyscale` handles are inside `with` blocks.

- **[Build gate]** 1354 passed, 1 xfailed (baseline 1344 / 1 xfailed, so +10:
  eight parametrised orientations, the corrupt-EXIF regression and the
  trailing-`eXIf` guard test). No new warnings: the image module's tests are
  clean under `-W error::UserWarning`.
- **[Guardrails]** G-1/G-3/G-7 files untouched. G-2 held: `generate`'s signature
  is still `(source, size, rng)`, no `validate_extent`, no `GenerationRequest`
  pair, no `--size NxM`. G-4 held (see F-002). G-5 unchanged — the decision is
  still `2 * kept >= whole` on integer cross-products. G-6 unchanged. Nothing
  under `meta/` is committed.

### STRUCTURE decisions

CARD-027 wires its request pair straight into these, so the shapes below are
what it will find.

- **STRUCTURE: `fit_crop_box(source_width, source_height, target_width,
  target_height)` replaces `square_crop_box(width, height)` outright, rather
  than being added beside it** — because `square_crop_box` is exactly
  `fit_crop_box(w, h, n, n)` (pinned as a property over 1200 cases, not just
  AC-072's one example), and two functions where one suffices would leave a
  second crop policy to drift. `square_crop_box` is gone from `__all__` and from
  the module.
- **STRUCTURE: the guard is `validate_aspect_ratio(sw, sh, tw, th) -> None`,
  raising, with a private `_retained(...) -> (kept, whole)` kernel** — a
  *validate* rather than an *is_ok* because every caller would immediately raise
  on `False`, and returning the pair rather than a float keeps the inclusive
  boundary exact. `_retained` is private: the percentage is needed only for the
  message, and a public "how much would this keep" accessor has no caller today
  (§9 minimalism). CARD-027 calls `validate_aspect_ratio` with the request pair
  and needs nothing else.
- **STRUCTURE: the two degenerate-extent checks live in one private
  `_checked_extents`, shared by both public functions, and they raise
  *different* kinds of error** — `UnreadableImage` for a zero-pixel source (the
  user's file), `ValueError` for a zero-cell grid (a caller bug, following
  `nudge`'s precedent for a zeroth attempt). Sharing them is what makes "the
  guard reports the degenerate source, because it runs first" true rather than
  coincidental.
- **STRUCTURE: a new `probe_extent(source) -> (width, height)` reads the
  displayed extent from the header without decoding** — G-4 says loading and
  greyscaling must be unreachable for a refused request, and the guard's four
  integers cannot be known without *some* read. A header parse is the least that
  works. It costs a second `Image.open` on the accepted path (a header parse)
  and buys: a refused request never decodes, and a badly-shaped 12-megapixel
  photo is refused in milliseconds. `_header_orientation` parses the raw EXIF
  block out of `info` rather than calling `getexif()`, which for PNG calls
  `load()` — see failure-matrix rows 13/14.
- **STRUCTURE: `binarize(greyscale, target_width, target_height)` does not
  re-validate.** It assumes validated extents exactly as it assumed a validated
  `size` before, so the guard has one home on the `generate` path. Keeping the
  crop and the resize as the single `resize(..., box=...)` call is unchanged.
- **STRUCTURE: the new error is `ImageNeedsManualCrop`, a direct
  `NonogramError` subclass with its own `_EXIT_CODES` row.** The card says to
  add a case only if the MRO walk does not already reach one — it does not, and
  the alternative (subclassing `UnreadableImage` so the walk finds it) would
  tell the user their file is unreadable when it read perfectly, sending them to
  fix the wrong thing. The row maps it to `INVALID_INPUT`, the same group, which
  is the observable contract the card asked for.
- **STRUCTURE: `image.generate` keeps its scalar `size` (G-2)** and calls
  `validate_aspect_ratio(*probe_extent(source), size, size)` then
  `binarize(greyscale, size, size)`. CARD-027 replaces those two `size, size`
  pairs with the request's `(width, height)` and changes nothing else in this
  module. `tests/test_sourcing_image.py::_convert` is that body written out, and
  exists so AC-071..AC-079 can be tested at a rectangular target today.

### Measured, not quoted

Every figure below was computed against this tree (`fit_crop_box` /
`validate_aspect_ratio`), not carried over from the ADR.

| source | grid | r_src | r_tgt | retained | crop box | verdict |
|---|---|---|---|---|---|---|
| 563x980 (eagle shape) | 15x30 | 0.574 | 0.500 | **0.870** | 490x980 | accepted |
| 563x980 | 20x20 | 0.574 | 1.000 | **0.574** | 563x563 | accepted |
| 563x980 | 30x15 | 0.574 | 2.000 | **0.287** | — | REFUSED |
| 600x600 | 30x15 | 1.000 | 2.000 | **0.500** | 600x300 | accepted (inclusive boundary) |
| 600x600 | 30x14 | 1.000 | 2.143 | **0.467** | — | REFUSED |
| 400x200 | 20x20 | 2.000 | 1.000 | **0.500** | 200x200 | accepted (boundary, other orientation) |
| 401x200 | 20x20 | 2.005 | 1.000 | **0.499** | — | REFUSED (one pixel past) |
| 980x563 | 30x15 | 1.741 | 2.000 | **0.870** | 980x490 | accepted |
| 980x563 | 12x30 | 1.741 | 0.400 | **0.230** | — | REFUSED |
| 60x40 (`landscape.png`) | 20x20 | 1.500 | 1.000 | **0.667** | 40x40 | accepted |
| 60x20 (`wide.png`) | 20x20 | 3.000 | 1.000 | **0.333** | — | REFUSED |
| 60x20 (`wide.png`) | 30x10 | 3.000 | 3.000 | **1.000** | 60x20 | accepted |

The ADR's own claims reproduce: the eagle shape keeps 57% under a square crop
and 87% at 15x30. Its "the square crop discards 23-43% of nearly every
silhouette" is consistent with the 0.574 row above.

### SCOPE+ (files changed beyond `## Touches`)

- **SCOPE+ `tests/fixtures/landscape.png`, `tests/fixtures/portrait.png` —**
  `wide.png` (60x20) and `tall.png` are 3:1, and FR-021 now **refuses** a 3:1
  source into a square grid: it keeps 33%. Every conversion test in the tree
  that used them at a square size therefore stopped being a valid request. Two
  new 60x40 / 40x60 fixtures (3:2, keeps 67%) carry the same discriminating
  structure — outer black bands that a centred square crop discards *exactly*,
  so "outer columns empty" still tells cropping from stretching — and
  `wide.png`/`tall.png` stay in the tree as the natural refusal witnesses. 111
  and 105 bytes.
- **SCOPE+ `tests/test_nudge.py`, `tests/test_nudge_reporting.py` —** the same
  consequence. Four pinned real-image cases ran `wide.png` at 20x20 and 22x22;
  both are now refusals. Re-pinned by re-running the 10..25 sweep those files'
  own docstrings prescribe: `landscape.png` at 22 reaches the five-nudge cap and
  at 20 converts uniquely with zero nudges — the same two sizes, which is a
  coincidence and is labelled as one in the code. `test_nudge.py` also pins
  `image.__all__`, which this card changes.
- **SCOPE+ `tests/test_cli.py` —** `test_every_domain_error_has_an_exit_code`
  walks `vars(errors)` and requires every `NonogramError` subclass to appear in
  `ERROR_EXIT_CODES`; the new error is one.

### Notes on the ACs

- **AC-009 is superseded and its test name is not reused.** The old
  `test_convert_image_produces_exact_target_dimensions` ran `[WIDE, TALL, BANDS]
  x [10, 17, 25, 30]`, two thirds of which are now refusals. It is replaced by
  `test_convert_image_produces_exact_target_dimensions_within_the_accepted_ratio_band`
  (AC-059, on the criterion's own 563x980 -> 15x30) plus a generalised square
  sweep over the accepted fixtures. AC-009's text is preserved in the test
  module's docstring, with why it went false.
- **AC-074's "no letterbox" is asserted where padding is falsifiable**: a wholly
  black source converts to a wholly filled grid, so any padding row or column
  would arrive as an empty cell. Swept over eight source/grid shape pairs in the
  property module as well.

### Orchestrator notes

- **[Scope]** ⚠ Confirmed, and wider than `Touches:` — legitimately. G-1/G-3/G-5/
  G-6/G-7 forbidden files all absent from the diff; G-2 verified: `generate`'s
  signature is still `(source, size, rng)`, no `validate_extent`, no
  `GenerationRequest` pair, no `--size NxM` — CARD-027's work did not leak in.
  Three files outside `Touches:` were forced by this card's OWN rule:
  `wide.png`/`tall.png` are 3:1 and become FR-021 refusals against a square
  grid (33% retained), invalidating every conversion test that used them.
  Verified this is a re-pin and NOT a weakening — assertion counts are identical
  either side (`test_nudge.py` 72/72, `test_nudge_reporting.py` 6/6); only the
  fixture changed, `wide.png` -> `landscape.png` (3:2, 67% retained).
- **[Build gate]** PASSED — 1344 passed, 1 xfailed, independently re-run
  (baseline 1314, so +30).
- **[Boundary verification]** The card's central correctness property, checked
  independently rather than accepted. The decision is an integer cross-product
  (`2*min(a,b) >= max(a,b)` over `a = sw*th`, `b = sh*tw`) — **no float touches
  it**; the percentage appears only in the message. Verified against a
  `Fraction` oracle: **1323 constructed exact-1/2 boundary shapes, 0
  violations**, and every one-pixel-past partner correctly refused. Spot cases:
  600x600 -> 30x15 retains exactly 0.5000 and is ACCEPTED (inclusive boundary);
  401x200 -> 20x20 retains 0.4988 and is REFUSED.
- **[The motivating case, measured]** `fit_crop_box(563, 980, ...)` — the eagle
  silhouette that started this increment: a **square** grid keeps 57.4% (today's
  behaviour, which is what cuts the head and feet off), a **15x30** grid keeps
  **87.0%**. Crop ratio exact, inside source bounds, touching a source edge, and
  the half-pixel bias preserved (worst margin asymmetry 1px across four shapes,
  AC-073).
- **[AC-077]** The refusal message names both shapes, quantifies the loss and
  offers two remedies: "a 980x563 picture is too differently shaped from a 12x30
  grid: fitting it would keep only 23% of the picture. Crop the picture yourself
  to roughly the grid's proportions first, or ask for a grid shaped more like
  the picture." `exit_code_for` reaches it via the MRO walk at exit 3
  (INVALID_INPUT) — correctly NOT a subclass of `UnreadableImage`, since the
  file read perfectly.

- **[Review 1/3]** Score: **4.0** — crit: 1, high: 3, med: 3, low: 1. Report:
  `meta/review/20260831T113303Z-CARD-026-cycle1.yml`. Severity gate BLOCKS.
  System contract: 13 checked, 5 ✓ holds, 6 ⚠ unchecked, **2 ✗ VIOLATED**
  (CON-012 and ADR-0022/R3 — both the same root cause as F-002).
  The review agent died writing its prose summary, but the YAML report was
  written in full (22KB) and the worktree is clean.
- **[Adversarial]** F-001 CONFIRMED by the orchestrator, including its
  regression claim. A JPEG carrying a malformed EXIF block makes `probe_extent`
  raise **`SyntaxError: not a TIFF file`** — not a `NonogramError`, so it
  escapes `exit_code_for` and reaches the user as a stack trace. Verified it is a
  REGRESSION and not pre-existing: `load_greyscale` handles the same file
  cleanly on BOTH base `cbf5ae2` and head (Pillow's `exif_transpose` tolerates
  it). The crash is in `probe_extent`, which this card ADDED and which now runs
  first, ahead of the decode. So a picture that converted fine before this card
  now dies.
- **[The failure matrix earned its keep — against the card]** The architectural
  obligation to declare failure semantics BEFORE writing code is what makes
  F-002 and F-003 legible as findings rather than discoveries: row 14 declared
  the PNG-eXIf-after-IDAT gap's cost as "crop along the stored axis", and the
  reviewer refuted that — the guard **fails OPEN**, judging the stored extent
  while the conversion crops the transposed one, so a request that should be
  refused is accepted. Row 13 declared orientation handling across 5..8 with
  exactly one orientation tested and its second cited test vacuous. A card that
  had not declared these would have shipped them as silence.

- **[Fix 1] declarations** — commit `303b997` (new commit; `2002bff` intact).
  All 8 findings addressed. Independently verified by the orchestrator:
  **F-001 (Critical) FIXED** — `_header_orientation` is now total. Both crash
  crafts re-tested: a garbage TIFF header (`\xff\xff\xff\xff`) and a truncated
  one now probe to `(60,40)` and AGREE with `load_greyscale(...).size`, where
  before they raised `SyntaxError` and `struct.error` respectively. The bare
  `except Exception` is justified in the docstring — the set a third-party
  header parser can raise is not enumerable and every member means the same
  thing ("no readable orientation"), which is exactly what `exif_transpose`
  already concludes.
  **F-002 (High) + CON-012 ✗ + ADR-0022/R3 ✗ FIXED** — reproduced the
  fails-open case directly: a 563x980 PNG whose `eXIf` orientation-6 chunk
  follows `IDAT` probes as `(563,980)` but decodes as `(980,563)`. Before the
  fix a 15x30 request was ACCEPTED at 0.287 retained; it is now REFUSED. The
  two-stage guard preserves G-4 — the cheap header probe still refuses the
  common case with no decode, and the rare probe/decode disagreement is caught
  after the decode instead of never.
  **The residual is fail-CLOSED and declared**: 30x15 against that same file is
  refused before decoding even though the decoded extent would retain 0.870.
  A false refusal, not a false acceptance — the safe direction, recorded in
  failure-matrix row 14 rather than left silent.
  **F-004 (High) FIXED** — the oracle now bounds the box from ABOVE as well as
  below. Verified by mutation in memory (source restored clean): the
  whole-source mutant is now KILLED where it previously SURVIVED. The agent
  reports the wrong-axis and ceil mutants likewise killed.
  F-003/F-005/F-006/F-007/F-008 addressed; failure-matrix rows 5, 8, 10, 12, 13,
  14 rewritten and a row 17 added.
- **[Build gate]** PASSED — 1354 passed, 1 xfailed, independently re-run
  (baseline 1344, so +10). Forbidden files clean; G-2 still holds — `generate`
  is `(source, size, rng)`, no request pair.
- **[Note]** The agent corrected TWO of the review's own claims rather than
  inheriting them: the report's "truncated inside the IFD" wording (a complete
  TIFF header pointing at a missing IFD does not raise — Pillow warns), and
  row 13's "JPEG/TIFF" reach (TIFF does not populate `info["exif"]`, though
  `exif_transpose` is inert there so probe and loader still agree). Both
  measured. That is the discipline this project has spent three cycles learning.

- **[Review 2/3]** Score: **8.0** — crit: 0, high: 0, **important: 2**, minor: 3.
  Report: `meta/review/20260831T121656Z-CARD-026-cycle2.yml`. Severity gate
  PASSES. System contract: 13 checked, **7 ✓ holds, 6 ⚠ unchecked, 0 ✗
  violated** — both cycle-1 violations (CON-012, ADR-0022/R3) re-derived
  adversarially rather than accepted as fixed. Carry rule applied honestly:
  5 items carried as delta-clean, 8 re-verified because `image.py` is in the
  delta; no item carried on a file the delta touched. Both new findings are
  **declaration** defects — the shipped code was correct on both counts.
- **[Adversarial]** F-101 CONFIRMED by the orchestrator, against the fixer's
  own claim. `Image.new("L",(60,40)).save(p, tiffinfo={274: 6})` →
  `Image.open` reports `(40, 60)` (Pillow's TIFF reader has *already* applied
  the orientation), `info` carries no `exif` key, and `exif_transpose` applies
  it a **second** time → `load_greyscale` gives `(60, 40)`. Probe and loader
  **disagree**. Row 13's "exif_transpose is likewise inert on one" was false.
  The reviewer's sharpest point stands: the fix's *code* is right for a reason
  its own *declaration* denied — had F-002 been closed narrowly for PNG rather
  than generally on `greyscale.size != probed`, TIFF would today be a live
  fail-OPEN CON-012 violation. The 168 false refusals reproduce exactly, and
  the 105/168/168 split is consistent with the 273 the probe accepts.
- **[Discovered during the fix, not by the review]** A mutation check on
  `generate`'s re-check **survived**. Cause is not a defect: the guard's
  condition is symmetric under transposition of the source extent when
  `target_width == target_height`, and an EXIF disagreement is always a
  transposition — so at square targets, the only ones G-2 permits, the
  re-check cannot change a verdict. Swept: **0 differing verdicts in 94,269
  square cases; 35,104 of 101,761 rectangular**. The re-check is therefore
  correct, behaviourally inert today, and load-bearing the moment CARD-027
  wires in the `(width, height)` pair. Declared as failure-matrix row 18,
  including the oracle consequence: today the mutant dies only in the
  `_convert` mirror, which is verified to kill it (both G-4 tests fail when
  the mirror's re-check is removed; source restored md5-identical).
- **[Fix 2] declarations** — commit `c08fe50`. F-101..F-105 addressed; G-4
  narrowed; `_header_orientation`'s guard extended over the tag lookup; the
  G-4 test given a disagreeing source so the narrowed claim is pinned rather
  than resting on an EXIF-free file. Suite **1354 passed, 1 xfailed** —
  unchanged, because the work extended existing tests rather than adding any.
- **[Requirements delta, APPLIED 2026-08-31]** EC-007 reads "refused **before any
  conversion**, dithering or solver work runs". That is literally false on the
  re-check path, where `load_greyscale` precedes the refusal. The card narrows
  its own G-4 wording, but a card may not edit the requirement it implements —
  **this needs forge:architect to amend EC-007** (and the same clause in G-4's
  source) to "before any *cropping*, dithering or solver work".
  **Done:** routed through `inputs/raw-requirements.md` (the intake step the
  architect skill requires — `requirements.yml` is never edited directly), then
  formalized by `forge:architect-domain-extraction` in delta mode. EC-007 keeps
  its id, `kind: consistency`, `instances: [AC-075, AC-076, AC-078]` and test
  ref byte-identical: a wording correction, not a supersession. Validators
  0 errors / 30 warnings (all pre-existing). The card's G-4 and its `## System
  contract` copy were realigned, and failure-matrix row 14's claim that the OLD
  wording "still holds on this path" — the very claim F-102 refuted — corrected.
- **[Card sync]** ⚠ The worktree copy of this card had diverged from the main
  copy and is **untracked in the worktree**, so neither the merge nor the
  branch would have carried it: the rewritten matrix (rows 5/8/10/12/13/14,
  17, 18) existed only in a file scheduled for deletion at `done`. Synced to
  main before fixing, and a stale duplicate `## Worktree notes` block removed
  from both copies. This is the second time this session that a worktree-only
  meta file nearly took measured work with it.
- **[AC verification gate]** **PASS — all 12 criteria ✓** (AC-071..079, AC-059,
  EC-006, EC-007), each verified in a clean context from FRESH evidence: the
  named test run green, and every stated figure re-derived rather than accepted.
  Nothing disagreed with the card. Reproduced independently: crop box
  `(36,0,526,980)` = 490x980 at exactly ratio 1/2 (cross-checked against a
  brute-force scan for the largest exact-ratio rectangle), the square case
  `(0,208,563,771)`, centring margins 36/37, retained fractions 0.5000 / 0.4667
  / 0.2298 / 0.8703 / 0.4988, the 46% / 49% / 22% message percentages, and the
  1500 -> 796/704 and 800 -> 405/395 corpus splits (so EC-007's iff is
  non-vacuous in BOTH directions). EC-007 was checked against the AMENDED
  statement and the card's verbatim copy matches `requirements.yml` exactly.
  The gate re-derived the narrowed clause on the hard path itself: with a
  trailing-`eXIf` PNG and `fit_crop_box`/`binarize`/`to_grid` instrumented, the
  post-decode refusal called none of them — cropping, dithering and solver work
  provably unreachable, which is what the amended wording claims.
  **Declared limitation:** AC-074/075/076/079/059's "a grid is produced" halves
  are exercised through the `_convert` mirror, not `generate`, because G-2 keeps
  `generate` scalar until CARD-027. The production entry point is not what that
  evidence exercises — stated here rather than left implicit.
- **[Done 2026-09-01]** Closed out of band. The merge itself had already happened
  on 2026-08-31 (`547d317`, `--no-ff`, branch fully contained in main) but `done`
  was interrupted before its bookkeeping, so the card sat at `review` with a live
  worktree for a day. Completed now: gate check, deferral scan, artefact sync,
  worktree/branch removal, card fields, changelog, trace write-back.
  - **Gate check PASS** with a wording variance recorded rather than waived: the
    evidence line reads `[AC verification gate] PASS — all 12 criteria ✓`, not the
    `[AC/EC check] All criteria/constraints ✓` string cmd-done greps for. Substance
    is present and specific (AC-071..079, AC-059, EC-006, EC-007, each re-derived
    from fresh evidence), so this was accepted as evidence, not forced through with
    `--force`. No `[Gate override]` was needed.
  - **Deferral scan: 0 hits** across the 1740-line insertion diff (no TODO/FIXME/
    "later card"/stub markers). Nothing to capture to the backlog. The card's one
    declared limitation — AC-074/075/076/079/059's "a grid is produced" halves run
    through the `_convert` mirror because G-2 keeps `generate` scalar — is already
    tracked as CARD-027's scope, so it is not duplicated as backlog debt.
  - **Artefact sync: already clean.** Both review reports (cycle 1 and cycle 2)
    were byte-identical to the copies in the main repo, and the main card copy was
    the RICHER one — the worktree copy had never advanced past `Status: in_progress`
    / `Review score: —`. The earlier `[Card sync]` note is why: the notes were pushed
    to main by hand mid-cycle. Nothing was lost to the worktree removal.
  - **Trace write-back:** FR-020 and FR-021 flipped `partial` → `covered` (no open
    card lists either; all 5 + 6 named tests resolve in code via the modules'
    AC→test mapping docstrings). CON-012's "Check ref is PLANNED" note is now
    false and was corrected — `tests/property/test_image_fit.py` defines it. The
    `_convert`-mirror limitation was carried into both `notes:` rather than left
    implicit in a closed card. FR-003 stays `partial`: CARD-021 still lists it.
    Validators after the edit: **0 errors, 56 warnings** (none naming FR-020,
    FR-021 or CON-012).

## Follow-up required (2026-09-01)

The card is closed and merged (`547d317`), but the architecture changed after merge.

**Reason:** ADR-0022 was revised on 2026-09-01 (resolving DEC-025) with
`Migration: rewrite`. Its rule R3 now requires the >2x aspect guard to measure the
source's **ink bounding box**, not the as-decoded file extent this card shipped.

**What's needed:** CARD-030 — already cut, and it carries this migration explicitly.
No new card is required.

**Why this card's guard is not merely stale but wrong once FR-022 lands:** measured over
the committed 25-image corpus at 20x20, the as-decoded reading overstates what survives
the crop on 15 of 25 pictures, worst at `img_2.png`/`img_3.png` which report 100%
retained while 55% of the actual content survives. Nothing this card did was incorrect
against the decision as it stood — the decision moved underneath it.

**Also retired by CARD-030, deliberately:** the two-stage pre-decode refusal path this
card built (the header probe that refuses without decoding). A trim can move a ratio in
either direction, so no sound refusal follows from the file header alone. That is
recorded as an accepted Negative consequence in the revised ADR-0022, not as a
regression against this card.

**Urgency:** CARD-030 depends on CARD-027, so this resolves in the normal queue order.
Until then the merged guard is conformant with the code as it exists (there is no trim
yet), so nothing is broken in the meantime — this is scheduled debt, not a live defect.

**Revision pending deliberately left `false`:** the field is a gate that `start` and
`run` act on, and this card is `done` — it will never be started again. The follow-up is
tracked as CARD-030, which is where the work actually is; setting a permanent ⚠ on a
merged card would gate nothing and never clear.

