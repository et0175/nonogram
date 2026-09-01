# CARD-030: Trim an uploaded picture to its ink bounding box, and move the aspect guard onto it

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/030-trim-to-ink-bounding-box
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-6
**Idea:** —
**Wave:** 19
**Depends on:** CARD-027
**Touches:** src/nonogram/sourcing/image.py, tests/test_sourcing_image.py, tests/property/test_image_fit.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Trim an uploaded picture to its ink bounding box (ink = a greyscale pixel below 128)
before FR-020's aspect fit, and **move the >2x aspect guard onto that trimmed extent**.
The two changes ship together — they are one revert — because the guard's new subject
only exists once the trim does.

**The pipeline order is prescribed by ADR-0022 and is not an implementation choice:**

```
open -> flatten -> greyscale -> COMPUTE ink box -> GUARD on the box's dimensions
     -> apply the trim crop -> aspect crop -> resize -> dither
```

Computing a bounding box reads pixels but writes nothing and discards nothing, so a
refused request is still refused before any cropping runs — which is what keeps EC-007
literally true with a trim in the pipeline. Guarding *after* the trim had been applied
would break it.

**Why the guard has to move at all.** The merged CARD-026 guard measures the as-decoded
file extent, and ADR-0022 was revised on 2026-09-01 with `Migration: rewrite` precisely
because that reading becomes wrong here. Measured over the committed 25-image corpus at
20x20: on 15 of 25 pictures the as-decoded reading overstates what survives the crop,
worst at `img_2.png` and `img_3.png`, which report 100% retained while 55% of the actual
content survives. CON-012 promises never to silently discard more than half *the user's
picture*; blank margin is not the user's picture.

**Known cost, already accepted in the ADR — do not try to preserve it.** The pre-decode
refusal path CARD-026 built is retired. A trim can move a ratio in either direction, so
no sound refusal follows from the file header alone, and every image request now pays
for a decode. Removing that path is correct here, not a regression.

**The trim is best-effort, not an invariant.** `dear1.jpg` keeps 2 blank lines and
`wolf1.jpeg` keeps 3 after trimming; `wolf1.jpeg` measures 3 deep *before* trimming too,
so no threshold in the swept range helps it. AC-088 and AC-091 pin those residuals
deliberately. A change that later fixes either should amend the criterion, never silently
pass it.

## Acceptance criteria

- **AC-086** (happy) — test: `TestTrimToInk_Fixes17Of19CorpusViolations`
  - **given** the 25-image corpus committed under pictures/, each fitted to a 20x20 grid at seed 1: 19 of the 25 carry more than one all-empty row or column at some edge before trimming
  - **when** each picture is trimmed to its ink bounding box (ink < 128) before the same 20x20 fit
  - **then** 17 of those 19 satisfy the at-most-one-blank-line-per-edge rule; exactly 2 do not (see AC-088), so 23 of 25 hold overall
- **AC-087** (boundary) — test: `TestTrimToInk_ReducesWorstCaseBorderToAtMostOneLine`
  - **given** img_2.png, the corpus's worst pre-trim case at 6 blank lines deep (300 of 400 cells spent on border; img_3.png ties it at 6), fitted to a 20x20 grid at seed 1
  - **when** the picture is trimmed to its ink bounding box (ink < 128) before the fit
  - **then** the resulting grid has at most one blank row or column at each edge
- **AC-088** (boundary) — test: `TestTrimToInk_AcceptsResidualBlankLinesOnDear1Jpg`
  - **given** dear1.jpg fitted to a 20x20 grid at seed 1 and trimmed to its ink bounding box (ink < 128)
  - **when** the resulting grid is inspected
  - **then** it still shows 2 blank lines at one edge — an accepted residual, not a defect
- **AC-091** (boundary) — test: `TestTrimToInk_AcceptsResidualBlankLinesOnWolf1Jpeg`
  - **given** wolf1.jpeg fitted to a 20x20 grid at seed 1 and trimmed to its ink bounding box (ink < 128)
  - **when** the resulting grid is inspected
  - **then** it still shows 3 blank lines at one edge — the corpus's worst accepted residual
- **AC-089** (boundary) — test: `TestTrimToInk_MidGreyThresholdOutperformsNearWhiteThreshold`
  - **given** the same 25-image corpus fitted to a 20x20 grid at seed 1, trimmed at a near-white threshold (ink < 245)
  - **when** the resulting grids are inspected
  - **then** 6 of the 25 violate the at-most-one-blank-line-per-edge rule, against 2 at ink < 128

## Engineering constraints

- **EC-007** (verbatim from `requirements.yml`, kind: consistency) — For any source image
  dimensions and any (width, height) pair in 10..30, the request is accepted if and only
  if `min(r_src, r_tgt) / max(r_src, r_tgt) >= 0.5` with `r = width/height` — every
  accepted request therefore retains at least half the source area under FR-020's centred
  crop, and every request that would retain less is refused before any cropping, dithering
  or solver work runs.
  test: `PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore`
  **Note for this card:** `r_src` is now the INK BOX ratio. The "before any cropping" half
  must be re-proved with the trim in the pipeline — instrument `fit_crop_box`, `binarize`
  and `to_grid` and show none is reached for a refused request.
- **EC(ADR-0022/R3):** a request whose grid ratio differs by more than 2x from the
  source's ink-box ratio is refused rather than cropped, and the bounding box is computed
  and judged before any crop is applied.
  test: `PropertyTest_AspectGuard_JudgesInkBoxBeforeAnyCropIsApplied`

## Guardrails

- G-1: FR-020's crop-not-stretch, crop-not-letterbox policy is unchanged — the trim adds a
  step before the aspect fit, it does not replace it (test: `TestFitImage_CropsToRequestedAspectRatio`)
- G-2: AC-072's `width == height` case still reproduces today's square crop box on an
  already-tight source (test: `TestFitImage_SquareGridReproducesSquareCropBox`)
- G-3: The runtime dependency set stays stdlib + Pillow + NumPy — the ink box is computed
  with Pillow, no new package (ADR-0006/R1)
- G-4: Do not edit `src/nonogram/orchestrator.py` — owned by CARD-031 this wave
- G-5: Do not edit `src/nonogram/export/**` or `pyproject.toml` — owned by CARD-032
- G-6: Out of scope — the `<name>-<WxH>-<difficulty>.pdf` filename change is DEC-026, held
  open until CARD-027 merges. Do not implement it here.

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

- **FR:** FR-022, FR-020, FR-021
- **NFR:** —
- **CON:** CON-012 (its subject changed with the ADR-0022 revision), CON-013
- **ADR:** ADR-0022 (revised 2026-09-01, `Migration: rewrite` — this card is that migration), ADR-0006
- **Components:** COMP-003
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
