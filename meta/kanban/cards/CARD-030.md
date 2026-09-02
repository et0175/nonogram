# CARD-030: Trim an uploaded picture to its ink bounding box, and move the aspect guard onto it

**Status:** review
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
**Review score:** 9.0 (cycle 2; cycle 1 7.0)
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
20x20: the as-decoded reading overstates what survives the crop on **22** of the 25
pictures — by more than 5 percentage points on 15 of those — reads exactly right on 1
(`eagle-silhouette1.jpg`, whose ink box *is* its file) and *understates* on 2
(`cat_Mouse.png`, `cat_dog.png`). Worst at `img_2.png` and `img_3.png`, which report
100% retained while 55% of the actual content survives. CON-012 promises never to
silently discard more than half *the user's picture*; blank margin is not the user's
picture.

> **Cycle-1 correction (F-002).** As first written this paragraph said "15 of 25
> ... overstates", which is the count only under an unstated >5-point materiality
> threshold. Re-derived on this tree: 22 overstate / 1 equal / 2 understate; 15 is the
> >5-point subset. Both numbers are now stated, with the threshold named.

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

## Failure matrix

Declared behaviour per operation x failure mode, in CARD-026's format. Every row names
the test that exercises it; "bound" says how far the declared behaviour reaches.

**Retires CARD-026 rows 12, 13 and 14.** Those three rows exist only because CARD-026's
guard read the *file header* and the decode could disagree with it: row 12 ("aspect
refusal costs no decode"), row 13 (`probe_extent` honouring EXIF orientation) and row 14
(the header-vs-decode disagreement class — the post-`IDAT` PNG `eXIf` chunk and the
orientation-tagged TIFF — and the re-check that patched it). `probe_extent` and
`_header_orientation` are deleted, so no extent is read from a header at all and the
disagreement class has no members. Row 13's surviving claim — the decode honours EXIF
orientation, so a sideways phone photo is measured and cropped along the axis the user
sees — is re-asserted on `load_greyscale` by `test_the_decode_honours_exif_orientation`
(nine values of the tag). Row 12 is replaced by row 5 below: refusal now costs exactly
one decode and still nothing else.

| # | Operation / boundary | Failure mode | DECLARED behaviour | Bound | Test |
|---|---|---|---|---|---|
| 1 | `ink_bounding_box` | the picture has **no ink at all** (blank sheet, or every pixel lighter than the threshold) | Returns the **whole extent**, not an empty box: there is nothing to trim to and trimming nothing is the honest answer. A flat mid-grey field is the case that matters — 128 is *not* ink by FR-022's own definition — and it converts exactly as it did before this card | Any picture whose `getbbox` on the ink mask is `None`; also a zero-pixel image, which returns its own zero extent for `validate_aspect_ratio` to report as the input error it is | `test_a_picture_with_no_ink_at_all_is_trimmed_by_nothing` (values 128 / 200 / 255, plus a full `generate` to a blank grid) |
| 2 | `ink_bounding_box` | the box is **near-degenerate** — a speck, a scan line, a 1px rule on one edge | **No floor, by decision.** The box is whatever the ink is, and both FR-021's guard and the resize then see it. Two outcomes, both intended: a square speck (2x2 on a 400x400 sheet) fits every square grid and the resize **upsamples it to a wholly filled grid** — the picture really is 4 black pixels, and a filled grid is the honest rendering of it; a 400x1 rule is **refused** by FR-021 for every grid in 10..30 (retains 0%), where before this card the square *sheet* would have been accepted. A floor is not added because any floor would have to guess which of the two the user meant | Every ink box down to 1x1. The refusal half is the same rule as row 4, reached by a different cause | `test_a_near_degenerate_ink_box_drives_the_guard_and_the_resize` (both ends, asserted on `generate`) |
| 3 | `ink_bounding_box` | `threshold` outside 0..256 | `ValueError` (`an ink threshold is a greyscale value in 0..256, got 257`) — **not** a `NonogramError`, so the CLI never maps it to an exit code. A threshold is not user input; an impossible one is a wiring bug, exactly as a zero-extent grid is | Any int outside 0..256. Both ends of the legal range are legal: nothing is ink at 0, everything at 256 | `test_an_ink_threshold_outside_the_greyscale_range_is_a_caller_bug` — matched on **this module's message**, because Pillow raises the same exception type for a 257-entry LUT and a bare `raises(ValueError)` let a loosened bound survive (cycle-1 F-009) |
| 4 | `validate_aspect_ratio` | the **ink box's** ratio differs from the grid's by more than 2x | `ImageNeedsManualCrop`, unchanged in wording and in the inclusive boundary. What changed is only the extent it judges — the box, never the file (CON-012 as revised) — so a file this guard used to accept can now be refused and vice versa. It errs both ways rather than conservatively; that is the ADR's choice, not a safe approximation | Every image request. Reachability cost measured and recorded under **[Reachability]** below | `test_property_aspect_guard_judges_the_ink_box_before_any_crop_is_applied` (208 pairs, ≥10 wrong-accepts and ≥10 wrong-refusals required of the corpus), `PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore` |
| 5 | `generate` | aspect refusal (replaces CARD-026 row 12) | **One decode, and nothing more.** The trim, the aspect crop, the resize, the dither, clue derivation and the solver are all unreachable for a refused request — that is EC-007 as narrowed on 2026-08-31 ("before any cropping, dithering or solver work"). The decode itself is the price the ADR accepted for judging the ink box | Every refused request, with no exceptions — unlike CARD-026 row 12, which had to except row 14's disagreement class | `test_property_aspect_guard_judges_the_ink_box_before_any_crop_is_applied` (instruments `fit_crop_box`, `binarize`, `to_grid` **and** `Image.Image.crop`), `test_a_refused_request_now_pays_for_a_decode_and_nothing_more` |
| 6 | `generate` | the file cannot be decoded, whatever grid was asked for | `UnreadableImage` — **always**, including for a request the old header probe would have refused with `ImageNeedsManualCrop`. Declared as a behaviour change rather than discovered: a truncated PNG asked for a grid it does not fit used to name the aspect problem and now names the decode | Every `OSError` / `ValueError` / `UnidentifiedImageError` / `DecompressionBombError` Pillow raises at open or load | `test_a_refused_request_now_pays_for_a_decode_and_nothing_more` (both branches on one file), `test_convert_image_rejects_an_unreadable_file_that_is_corrupt` |
| 7 | `generate` | the decode succeeds but `ink_bounding_box` raises | Cannot occur for any decoded picture. `load_greyscale` returns mode `"L"`, `Image.point` with a 256-entry LUT is total over it, and `getbbox` returns a box or `None` (row 1). The only raise in the function is row 3's caller-bug guard on `threshold`, which `generate` never passes | Every mode-`"L"` image Pillow can produce | covered by rows 1 and 3; no separate test, and none is possible without monkeypatching Pillow |
| 8 | the trim itself | blank margin **survives** the trim | **Best-effort, not an invariant** — declared, not a defect. `dear1.jpg` keeps 2 blank lines and `wolf1.jpeg` keeps 3, and `wolf1.jpeg` measures 3 deep before the trim too, so no threshold in the swept range reaches it: the margin there survives the resize and the dither, not the crop. A change that later fixes either must amend the criterion, not pass a laxer assertion | 23 of the 25 corpus pictures satisfy the at-most-one-blank-line rule at 20x20; the 2 that do not are named individually | `test_trim_to_ink_accepts_the_residual_blank_lines_on_dear1_jpg` (AC-088), `..._on_wolf1_jpeg` (AC-091), `test_trim_to_ink_fixes_17_of_the_19_corpus_violations` (AC-086) |

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

### Cycle-1 review fixes (2026-09-02) — score 7.0, gate failed

Findings F-001..F-010 of `meta/review/20260902T080013Z-CARD-030-cycle1.yml`.

- **[F-001 — the blocker] The shipped trim is now pinned.** The reviewer verified a
  surviving mutant: deleting `greyscale.crop(box)` from `generate` (compute the box,
  judge it, then throw it away — FR-022 entirely undelivered) left all 1471 tests
  green, because every AC test measures the trim *transform* through the
  `_untrimmed_grid`/`_trimmed_grid` helpers and every conversion fixture is a
  deliberate trim no-op. Added
  `test_the_shipped_conversion_applies_the_trim_the_criteria_measure`, which drives
  `image.generate` on `img_2.png` and asserts the result **equals** the trimmed grid,
  **differs from** the untrimmed one, and is at most 1 blank line deep at each edge
  while the untrimmed one is 6. Re-applied the mutation to confirm it now fails, then
  restored and re-verified `src/nonogram/sourcing/image.py` byte-identical (see the
  mutation proof in the fix report).
- **[F-002] The 15-of-25 figure was re-derived and corrected**, in both the module
  docstring (`image.py`) and "Why the guard has to move at all" above: the real counts
  at 20x20 are **22 overstate / 1 equal / 2 understate**, with 15 being the subset
  overstating by more than 5 percentage points. The `img_2`/`img_3` "100% vs 55%" half
  reproduces exactly (1.000 vs 0.546).
- **[F-003] `validate_aspect_ratio`'s docstring** no longer claims the predicate "runs
  before the picture's pixels are decoded" — this card retired exactly that, and
  `test_a_refused_request_now_pays_for_a_decode_and_nothing_more` in the same commit
  contradicted it. It now says what is true: the predicate's purity is what lets it run
  before any *cropping*, its source extent is the ink box, and it therefore necessarily
  runs after the decode.
- **[F-004] "exactly one extent in the pipeline, the decoded one"** was the wrong
  reason for a true conclusion — the judged extent is the ink box, a derived
  sub-extent. Reworded in `generate`'s docstring and in
  `test_the_decode_honours_exif_orientation` to the operative fact: no extent is read
  from a header any more, and the guard and the crop are handed the same one.
- **[F-005] `_fits_the_aspect_band`** (`tests/property/test_grid_dimensions.py`) now
  justifies itself with `bands.png`'s **ink box** being square, naming
  `test_the_fixture_images_are_present_and_shaped_as_documented` (which asserts
  `_ink_extent(BANDS) == (32, 32)`) as where that is checked. "bands.png is square" as
  a file fact stopped being the operative one when the guard moved onto the box.
- **[F-006] README re-measured.** The published ✓/✗ table had two cells this card made
  wrong — `dear1.jpg@12` ✓→ now abandoned, `dear1.jpg@20` ✗→ now converts — both
  reproduced. The table is rewritten per-picture rather than per-group (the old groups
  no longer share a row), the `35` column is replaced by `30` (35 is above MAX_SIZE and
  is refused outright — pre-existing error, folded in), and
  `eagle-silhouette1.jpg`'s 10/12 cells are corrected (wrong on `main` too —
  pre-existing). The pipeline sentence at README.md:90 now names the trim, which is the
  first thing that happens to the user's picture. **Disclosure: `README.md` is outside
  this card's `Touches:`** and was edited anyway, because this card changed the
  behaviour that file documents.
- **[F-007 — Reachability, the blast radius the card did not measure]** The
  implementation record measures the trim only as blank-edge depth. Re-ran the
  reviewer's sweep — 25 pictures x `{10,12,15,20,25,30}` square grids at seed 1 through
  `orchestrator.generate`, `main` vs this branch — and reproduce it exactly:

  | | |
  |---|---|
  | cases | 150 |
  | outcomes that change | **32** (21%) |
  | abandoned → converts | 23 |
  | converts → `GenerationAbandoned` | **9** |
  | net converting | 94 → **108** |

  The nine regressions: `butterfly1.png@10`, `dear.png@12`, `dear.png@15`,
  `dear1.jpg@12`, `duck2.png@15`, `duck2.png@20`, `img_6.png@30`, `konek.png@20`,
  `wolf_2.png@30`. Not a defect — `GenerationAbandoned` is a documented exit-code-4
  outcome and the net is strongly positive — but a known consequence, recorded here so
  a user report on `dear.png --size 12` arrives with a trace of having been
  anticipated. (One `SolverTimeout` case is unchanged on both trees.)
- **[F-008] `## Failure matrix` added** above, in CARD-026's format, with an explicit
  statement of which of its rows (12, 13, 14) this card retires and what replaces them.
  F-010's near-degenerate ink box is row 2.
- **[F-009] The ink-threshold upper bound is now genuinely pinned.** `<=256` → `<=257`
  survived because Pillow rejects a 257-entry LUT with its own `ValueError`, so the
  test pinned the exception type rather than this module's guard. It now matches on the
  module's own message.
- **[F-010] The near-degenerate ink box is declared and tested.** No floor is added —
  any floor would have to guess the user's intent. Failure-matrix row 2 declares both
  ends and `test_a_near_degenerate_ink_box_drives_the_guard_and_the_resize` pins them
  on `generate`: a 2x2 speck on a 400x400 sheet upsamples to a wholly filled 20x20
  grid, a 400x1 rule is refused by FR-021 at every grid in 10..30.
- **Not fixed, deliberately.** F-011, F-012 and F-013 are the reviewer's own
  out-of-scope findings. F-012 in particular (AC-087's "300 of 400", confirmed
  non-reproducing) needs a requirements amendment, not a code change; the implementation
  agent's handling of it stands and the code is untouched.
- **[Guardrails, re-checked]** G-4/G-5 hold: `src/nonogram/orchestrator.py`,
  `src/nonogram/export/**` and `pyproject.toml` are untouched by this fix pass (the
  reachability sweep *reads* the orchestrator, it does not edit it). G-6 holds: DEC-026
  is not implemented. G-1/G-2/G-3 are unaffected — no production behaviour changed in
  this pass; every source edit is prose.

## AC/EC gate (2026-09-02)

**Verdict: PASS, after one correction.** Seventeen criteria checked against the current
implementation: AC-071..AC-074 + EC-006 (FR-020), AC-075..AC-079 + EC-007 (FR-021),
AC-086..AC-091 (FR-022), and ADR-0022/R3's EC. Every named test resolves to exactly one
`def` — no missing test, unlike CARD-027's gate. All 125 tests in the two files pass.

FR-020 and FR-021 were re-verified rather than inherited from CARD-026, because **this
card changed their subject**: the guard now measures the ink box, so criteria stated over
the *source image's* ratio are no longer trivially about the thing being measured.
Checked both ways:

- The five `tests/fixtures/` images used by FR-020's criteria are all ink-tight
  (file extent == ink box: bands 32x32, landscape 60x40, portrait 40x60, tall 20x60,
  wide 60x20), so for those the two subjects coincide and the criteria are unaffected.
- FR-021's criteria run against the built `silhouette` fixture, whose inset is
  proportional (`width // 4`), so the ink box preserves the ratio: 600x600 -> 301x301
  (1.000 vs stated 1.000), 563x980 -> 284x491 (0.578 vs stated 0.574), 980x563 ->
  491x284 (1.729 vs stated 1.741). The stated `r_src` figures are now approximations of
  what the guard measures, but every accept/refuse verdict holds with a wide margin
  (AC-079's retained fraction moves 0.870 -> 0.865, against a 0.5 threshold). Recorded
  rather than corrected: the criteria are true as written.

### The correction

`test_aspect_guard_refuses_a_ratio_difference_above_two_fold` (AC-076) carried a
docstring claiming the refusal "reaches the caller before the picture's pixels are
decoded, observed by pointing the guard at a file whose header is fine and whose body is
not". **Both halves were false.** This card deleted the pre-decode path outright — that
is the cost the ADR accepts and that
`test_a_refused_request_now_pays_for_a_decode_and_nothing_more` pins — and the test body
uses a valid `silhouette(600, 600)`, with no corrupt-bodied file anywhere in it. The
paragraph also cited "Guardrail G-4", which is card-relative and on this card means
"do not edit orchestrator.py".

The text is CARD-026's (`2002bff`) and CARD-030 never touched the line, which is exactly
why **neither review cycle caught it: both reviewed the diff, and prose invalidated
*elsewhere* by a change is invisible to a diff review.** That is a structural limit of
diff-scoped review, not a reviewer error, and it is the seventh instance of this
project's docstring-truth family.

Corrected to state what is now true and to name the property that actually proves the
surviving ordering claim. Swept for siblings: `before any decode` / `without decoding` /
`from the header alone` across `src/`, `tests/` and `README.md` returns exactly two other
hits, both already correctly past-tense (`tests/test_sourcing_image.py:1265,1445`), plus
one unrelated line in `test_export_pdf.py`. One instance, now zero.

**Suite: 1473 passed, 1 xfailed** — unchanged; the edit is prose only.

[AC/EC check] All criteria/constraints ✓ (evidence: AC-086 test_trim_to_ink_fixes_17_of_the_19_corpus_violations, AC-087 test_trim_to_ink_reduces_the_worst_case_border_to_at_most_one_line, AC-088 test_trim_to_ink_accepts_the_residual_blank_lines_on_dear1_jpg, AC-091 test_trim_to_ink_accepts_the_residual_blank_lines_on_wolf1_jpeg, AC-089 test_trim_to_ink_mid_grey_threshold_outperforms_the_near_white_threshold, plus the shipped-path pin test_the_shipped_conversion_applies_the_trim_the_criteria_measure and the degenerate-box pin test_a_near_degenerate_ink_box_drives_the_guard_and_the_resize; EC-007 test_property_aspect_guard_accepts_exactly_those_requests_retaining_half_or_more; ADR-0022/R3 test_property_aspect_guard_judges_the_ink_box_before_any_crop_is_applied and test_fit_image_refuses_a_ratio_mismatch_beyond_twice; FR-020's AC-071..AC-074 + EC-006 and FR-021's AC-075..AC-079 re-verified against the CHANGED subject rather than inherited from CARD-026 — see "AC/EC gate (2026-09-02)" above; suite 1473 passed, 1 xfailed) — one docstring corrected by the gate; all seventeen criteria verified against the current implementation on 2026-09-02. Every name above was resolved to exactly one `def` before this line was written: a first draft of it carried six invented snake_case names, which is the same dead-arrow defect this project has been chasing, caught here only because the names were checked rather than trusted.
