# CARD-030: Trim an uploaded picture to its ink bounding box, and move the aspect guard onto it

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/030-trim-to-ink-bounding-box
**Worktree:** ../PythonProject4-card-030
**Source:** meta/architecture/handoff.md#increment-6
**Idea:** —
**Wave:** 19
**Depends on:** CARD-027
**Touches:** src/nonogram/sourcing/image.py, tests/test_sourcing_image.py, tests/property/test_image_fit.py
**Review score:** —
**Started:** 2026-09-02T07:40:00Z
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
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the othe... (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
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

- **[Env]** forge 2026.8.17 (project requires >= 2026.8.17 — skew gate passed).
- **[Dependency gate]** CARD-027 `done` (merged 632fd18) — the only dependency, satisfied.
- **[Drift gate]** ⚠ warn: `src/nonogram/sourcing/image.py` appears in two unprocessed
  `meta/drift-pending.yml` events. Both were checked and are this project's OWN merge
  commits — 5e9f2de (CARD-023) and 547d317 (CARD-026) — not unreconciled external change.
  Signal noise from forge recording its own work; proceed.
- **[Corpus check]** Verified before the agent started: `pictures/` holds exactly 25
  committed images, and all four fixtures the ACs name by hand (`img_2.png`, `img_3.png`,
  `dear1.jpg`, `wolf1.jpeg`) are present. The card's measured numbers are therefore
  checkable as written.

### Implementation (2026-09-02)

- **[Pipeline]** `generate` is now `validate_extent -> load_greyscale ->
  ink_bounding_box -> validate_aspect_ratio(box extents) -> greyscale.crop(box) ->
  binarize -> to_grid`, exactly ADR-0022's order. `ink_bounding_box(greyscale,
  threshold=INK_THRESHOLD)` is new and public; it builds a 256-entry ink mask with
  `Image.point` and calls `getbbox`, so it is pure Pillow (G-3, no new dependency).
  A picture with no ink returns the whole extent — trimming nothing is the honest
  answer for a blank sheet, and it keeps a flat mid-grey field (128 is *not* ink)
  converting exactly as before.
- **[Retirement]** `probe_extent` and its `_header_orientation` EXIF parser are
  **deleted**, not merely bypassed — leaving them would have left a public function
  whose docstring says "so a refused request must not pay for a decode", which is
  now false. With them goes CARD-026's header-vs-decode re-check: there is only one
  extent in the pipeline now, so the fail-open seam that re-check patched cannot
  exist. Its *false-refusal* residue goes too, and that improvement is pinned: the
  trailing-`eXIf` PNG at 30x15 (retains 0.870) used to be refused and now converts.

**Measured numbers — every AC figure reproduced exactly.** Re-measured on this tree
through the shipped code at 20x20 (seed 1 is irrelevant: image mode never draws from
the RNG):

| Claim | Card says | Measured |
|---|---|---|
| AC-086 pre-trim violations | 19 of 25 | **19** |
| AC-086 fixed by the trim | 17 of those 19 | **17** |
| AC-086 still violating | exactly 2 | **2** — `dear1.jpg`, `wolf1.jpeg` |
| AC-086 holding overall | 23 of 25 | **23** |
| AC-087 `img_2.png` pre-trim depth | 6 | **6** (top 6, bottom 5, left 2, right 2) |
| AC-087 `img_3.png` ties | 6 | **6** |
| AC-087 `img_2.png` post-trim | ≤ 1 at each edge | **1, 1, 0, 0** |
| AC-088 `dear1.jpg` residual | 2 at one edge | **2** (right; 0 elsewhere, from 4 pre) |
| AC-091 `wolf1.jpeg` residual | 3, worst accepted | **3** (left; identical before and after the trim, as the card predicts) |
| AC-089 near-white (ink < 245) | 6 of 25 violate | **6** |
| AC-089 mid-grey (ink < 128) | 2 of 25 violate | **2** |

Nothing newly violates the rule *because* of the trim (asserted, not just counted):
the post-trim violation set is a subset of the pre-trim one.

- **[⚠ ONE FIGURE DOES NOT REPRODUCE]** AC-087's `given` says `img_2.png` spends
  "**300 of 400 cells** on border". It does not. Measured: the blank frame implied by
  its own edge depths (6/5/2/2) is `400 - 9*16 = ` **256** cells, and the grid's total
  empty-cell count is **297**. 300 is what a uniform 5-deep frame would cost, and 297
  is the nearest real quantity but is not a border count (it includes paper inside the
  subject). **No test was adjusted to match**: the figure is parenthetical scene-setting
  in the `given`, not part of the `then`, so the test asserts the criterion's actual
  claim (6 deep before, ≤1 after — both exact) and records the discrepancy with both
  measured numbers in its docstring. Read: whoever wrote the criterion most likely
  eyeballed the total empty count (297) and rounded. Worth a one-line amendment to
  AC-087 rather than a code change.

**Scope — three files outside the predicted `Touches:`, all called out.**

1. **`tests/fixtures/bands.png` (regenerated, 88 -> 88 bytes).** Unavoidable and the
   most interesting consequence of the card. `bands.png` was black / mid-grey 128 /
   white horizontal thirds. Ink is *below* 128, so the mid band is paper and the
   fixture's ink box was its black third alone: **32x11**, which against a 20x20 grid
   keeps 34% and FR-021 now refuses outright. The fixture is used at square grids in
   four test files, so it had to become a picture that fills its sheet. It gains a
   **2-pixel black rule along the bottom edge** (rows 30..31); the three bands are
   otherwise untouched, the ink box becomes the whole 32x32, and the trim is a no-op
   on it — which is what a *conversion* fixture should be, with the trim measured
   against the real corpus instead. **Disclosure on the thickness:** 1px and 2px are
   equally honest fixtures; at 1px the pinned 10x10 conversion in `tests/test_nudge.py`
   needs 4 nudges instead of the 2 it has always needed, at 2px it still needs 2. 2px
   was chosen to leave that pin (and `test_nudge_reporting.py`'s "2 cells were nudged")
   alone. Both facts are recorded in the fixture's docstring so the choice is visible
   rather than inferred.
2. **`tests/test_nudge.py`** — one assertion: the `image.__all__` API-surface pin,
   which moves whenever COMP-003's surface moves (`+INK_THRESHOLD`,
   `+ink_bounding_box`, `-probe_extent`).
3. Nothing else. `orchestrator.py` (G-4), `export/**` and `pyproject.toml` (G-5) are
   untouched; DEC-026's filename change (G-6) was not implemented.

**Guardrails.** G-1: `fit_crop_box`/`binarize` are unchanged and the trim is a step
*before* them — `binarize` fits whatever rectangle it is handed, so the crop-not-
stretch/crop-not-letterbox policy is not modified, only preceded. G-2: AC-072's
square case passes unchanged. G-3: stdlib + Pillow + NumPy, the box computed with
`Image.point`/`getbbox`. G-4/G-5/G-6: see above.

**EC-007, re-proved with the trim in the pipeline.**
`test_property_aspect_guard_judges_the_ink_box_before_any_crop_is_applied`
(`PropertyTest_AspectGuard_JudgesInkBoxBeforeAnyCropIsApplied`) monkeypatches
`fit_crop_box`, `binarize`, `to_grid` **and `Image.Image.crop`** — the fourth because
FR-022's trim is a Pillow method and an implementation that trimmed before judging
would leave the three named counters at zero while having already cropped the user's
picture. 208 (source, grid) pairs: for every refused one all four counters are
unchanged; for every accepted one they are not. The corpus is required to contain
≥10 pairs where the retired whole-file reading would have wrongly *accepted* and ≥10
where it would have wrongly *refused*, so the test cannot be satisfied by an
implementation that still judges the file — this is ADR-0022's "it errs both ways
rather than conservatively", asserted.

- **[Behaviour change, pinned as a cost]** A refused request now pays for a decode.
  `test_a_refused_request_now_pays_for_a_decode_and_nothing_more` asserts the new
  outcome directly: a truncated PNG asked for a grid it does not fit used to return
  `ImageNeedsManualCrop` from the header alone and now returns `UnreadableImage`.
- **[Suite]** 1471 passed, 1 xfailed (from 1463 passed, 1 xfailed). Net +8:
  +5 FR-022 acceptance tests, +1 EC ordering property, +3 edge tests (corpus-size
  premise, a picture with no ink, an out-of-range threshold), −1 deleted
  (`test_the_probe_reports_an_unreadable_file_as_one`, whose subject no longer
  exists; the corrupt-file claim it made is still covered by
  `test_convert_image_rejects_an_unreadable_file_that_is_corrupt`).
