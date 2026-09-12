# ADR-0026: Silhouette binarisation — 50% ink-coverage threshold after the resize

**Status:** Proposed (gated: Accepted once the owner has eyeballed rendered grids of the picture corpus (`pictures/`, currently not on disk — the owner's own trial folder) converted both ways and confirmed the threshold path; AC-127 is the measurable half of the gate)
**Date:** 2026-09-12
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

Image sourcing (FR-003, FR-020; COMP-003 inside CTX-001) turns an uploaded
picture into a solution grid through a fixed sequence whose order ADR-0022
prescribes and `docs/GENERATION_ALGORITHM.md` §4.3 tabulates: extent check,
greyscale load with alpha composited onto white, ink bounding box
(`INK_THRESHOLD = 128`, strictly below is ink), the >2x aspect guard on that
box (ADR-0022/R3), trim to the box (FR-022), a centred crop to the grid's
ratio, and one LANCZOS `resize` to `width x height` cells. After that resize
every cell is one grey value, and because LANCZOS averages the whole
neighbourhood a cell covers, that value *is* the cell's ink coverage
(`sourcing/image.py:193`). The last step turns that grey value into a boolean:
today it is `scaled.convert("1", dither=Image.Dither.FLOYDSTEINBERG)`
(`image.py:594`) — Pillow's built-in Floyd-Steinberg error diffusion, chosen
when FR-003 was written on the argument recorded in the module docstring
("dither before threshold, not instead of it": a plain cut turns a photograph
into two flat blobs, while error diffusion trades grey *level* for filled-cell
*density* and keeps a mid-tone region readable at grid resolution).

CON-013 has since narrowed the declared scope of image sourcing to
high-contrast black-and-white silhouettes: conversion quality, dithering
tuning and the uniqueness/nudge budget are calibrated for silhouettes, and
photographs are out of scope rather than unsupported-with-a-warning. On a
silhouette the property error diffusion preserves — average density over a
region — is not the property that matters; the contour is. The converted grid
is then handed to the uniqueness solver, and when it is not unique the
orchestrator applies at most five pixel nudges (POL-002, ADR-0002), each of
which — under the 2026-09-12 FR-013 amendment — flips cells chosen from the
solver's own undecided/disagreement mask (FR-024), nearest the ink boundary
first. The nudge is a repair that runs after binarisation on whatever
ambiguity binarisation produced.

The 2026-09-12 intake (raw-requirements.md entry 6) proposed replacing the
dither with a plain threshold for silhouettes and stated a hypothesis: clean
outlines and longer runs make conversions unique on the first solve more
often and need fewer nudges. FR-027 formalises this NEUTRALLY, as an open
choice between (a) a threshold — a cell is filled when its ink coverage is at
least 50%, inclusive (AC-124..AC-126) — and (b) today's dither, with the
hypothesis written as a criterion measured over the committed picture corpus
at a bare `--size 25` (AC-127, holds under every alternative). FR-027's
`_meta.gate` is binding on the resolution: the owner's visual validation of
the converted corpus, not a green test, is what lets the change land
(project memory: image-pipeline changes need a rendered-grid eyeball). The
corpus itself is the owner's own experimental folder and is not in the
repository at the time of writing.

Two further facts bound the solution space. ADR-0006/R1 fixes the runtime
dependency set at stdlib + Pillow + NumPy, and its Positive consequences
record the rationale that "FR-003's dithering ... remain[s] a Pillow library
call, not a hand-written algorithm" — any binarisation must stay a Pillow
primitive. And FR-027 states that under either alternative genuinely
greyscale input keeps the dithering path, while recording as a gap that the
intake gives no criterion for telling such input apart; that criterion is
DEC-033, which depends on this decision and is not decided here.

## Decision

We will binarise silhouette input by a plain, inclusive 50% ink-coverage
threshold applied to the resized image: after the LANCZOS resize to the grid
extent, a cell is filled when its resized grey value is `<= 127` — ink
coverage at or above 50% — and empty otherwise, implemented as an
`Image.point` lookup at 128 (the same strictly-below-128 reading
`INK_THRESHOLD` already gives the ink bounding box) producing a mode `"1"`
image, in place of `convert("1", dither=FLOYDSTEINBERG)` for the silhouette
case. The trim, the ink-box aspect guard, the centred crop and the resize —
ADR-0022's order — are unchanged; the FR-013 nudge still runs after the
conversion, on the solver's mask, exactly as before. The boundary is
inclusive by requirement (AC-126: exactly 50% is filled); the implementing
card owns making Pillow's integer rounding at the resize land that fixture on
the filled side, and the AC-126 test pins it.

This decision is CONDITIONAL on FR-027's gate and is therefore recorded as
Proposed, not Accepted. It becomes Accepted once the owner has looked at the
rendered grids of the picture corpus converted both ways and confirmed the
threshold path; AC-127 — first-solve uniqueness count and total nudge count
over the corpus, threshold no worse than dither on both — is the measurable
half of that gate and cannot discharge it alone. If the rendered grids fail
the owner's look, this ADR is withdrawn and `floyd_steinberg_dither` stands
as recorded under Alternatives; the Status line and History are the record
of which way it went.

The reasoning: error diffusion is designed to preserve average density, not
contour. On a silhouette — CON-013's declared scope — it seeds isolated cells
and ragged edges along the boundary: precisely the one-cell runs and 2x2
switching blocks that make a nonogram non-unique and that the nudge then has
to repair one cell at a time within a cap of five. A 50% coverage threshold
turns the same boundary into a clean contour with longer runs, which is the
shape line logic solves. The mechanism costs one Pillow call and no new
dependency (ADR-0006/R1 untouched). The hypothesis that this yields more
first-solve-unique conversions and fewer nudges is exactly that — a
hypothesis — until AC-127 is measured; the geometry argument is what makes it
worth measuring, and the gate is what keeps it from landing on argument
alone.

This ADR decides the silhouette case only. Whether a dither path is retained
for genuinely greyscale input, and by what rule such input is recognised, is
DEC-033 (open, `depends_on: [DEC-032]`); this ADR neither removes the dither
path nor commits to keeping it beyond what FR-027 already states, and the
"Pillow does the dithering" rationale in ADR-0006 narrows to whatever path
DEC-033 leaves standing.

## Alternatives considered

### `floyd_steinberg_dither` — keep the single dither path, rely on the mask-driven nudge (rejected, subject to the gate)
Keep `convert("1", dither=FLOYDSTEINBERG)` for every input and pursue
silhouette quality through the FR-013 amendment alone: the nudge now picks
cells from the solver's undecided/disagreement mask, so part of the expected
gain arrives regardless of binarisation. Its genuine advantages are that
there is no second path, no classification problem (DEC-033 would be moot),
no owner gate, and mid-tone regions stay readable — the reason the dither was
chosen in the first place. Rejected because the nudge repairs ambiguity after
the fact while the threshold avoids creating it: on a silhouette the
diffusion's boundary speckle is the very set of switching blocks the nudge
then spends its five attempts on, and CON-013 says mid-tone readability is
not what this pipeline is tuned for. It also leaves AC-127's measurement
unmade, so the intake's hypothesis would be neither confirmed nor refuted.
Should the owner's visual gate fail, this alternative is what remains in
force — it is rejected on the geometry argument, not on measured evidence,
and the ADR says so.

### `ink_coverage_threshold_50pct` — the chosen option
Recorded above under Decision. The DEC's own cons are carried honestly into
Consequences below rather than softened: thin strokes narrower than half a
cell vanish, a second binarisation path is introduced, and the module's
"dither before threshold" rationale is overturned for the silhouette case.

## Consequences

### Positive
- A silhouette's boundary becomes a clean contour: no error-diffusion
  speckle, no isolated cells along the edge, longer runs — the shapes line
  logic solves without search, and the shapes the FR-013 nudge otherwise has
  to reconstruct one cell at a time within ADR-0002's cap of five.
- Deterministic per cell and explainable to the owner in one sentence —
  "more than half ink, filled" — and, being a pure function of the resized
  grey value, it keeps image mode rng-free (ADR-0015): the same file at the
  same extent still converts to the same grid.
- Same Pillow primitives, no new dependency: ADR-0006/R1 is untouched;
  `Image.point` is already in use for the ink bounding box, so the module
  gains no new idiom.
- AC-127 is finally measured rather than argued: whichever way the gate goes,
  the project ends up with a number (first-solve uniqueness count and nudge
  total, both paths, over the corpus at `--size 25`) instead of a hypothesis.

### Negative
- Thin strokes narrower than half a cell vanish entirely under the threshold
  where the dither would have kept them as scattered cells; a fine-line
  silhouette (whiskers, antennae, a thin outline drawn rather than filled)
  can lose features the owner expects to see. This is the concrete failure
  the visual gate exists to catch, and the most likely reason for it to fail.
- The change is a hypothesis until AC-127 is measured and the owner has
  eyeballed the corpus; the gate can fail, and then this ADR is withdrawn.
  Work built on it before the gate is passed (docstring rewrites, test
  renames) is at risk of reversal.
- A second binarisation path exists once this lands, and with it DEC-033's
  classification problem: which uploads take the threshold and which keep
  the dither. Until DEC-033 resolves, the implementing card cannot be cut
  cleanly — FR-027 says greyscale input keeps dithering but gives no rule.
- The module's own recorded rationale — "dither before threshold, not
  instead of it" (`image.py:133-136`) — is overturned for the silhouette
  case and must be rewritten, not left contradicting the code; FR-003's
  statement ("Floyd-Steinberg error-diffusion dithering before binarizing
  each cell") and AC-007's test name (`TestConvertImage_ProducesDitheredGrid`)
  describe what ships today and will need re-wording once the gate passes.
  Not edited here; follow-up on resolution.
- `Migration: on-touch`: puzzles already converted and stored by the admin
  panel (`admin/image_to_puzzle.py` calls `sourcing.image.generate`) are not
  re-converted. A picture uploaded before and after the change yields
  different grids, and the export metadata (ADR-0023) does not record which
  binarisation produced a stored puzzle.

### Neutral
- Pipeline order is unchanged: trim, ink-box aspect guard, centred crop,
  LANCZOS resize (ADR-0022/R3 as written), then the threshold, then
  `to_grid`, then the orchestrator's uniqueness check and FR-013 nudge. Only
  step 8 of §4.3's table changes; `docs/GENERATION_ALGORITHM.md` §4.3 and
  §11 need that one row updated when the change lands.
- ADR-0006 takes a History entry only: its "Pillow does the dithering"
  rationale narrows to the greyscale path if DEC-033 keeps one, or is retired
  if DEC-033 collapses to "always threshold". R1's statement, scope and check
  are unaffected — no rule change.
- DEC-033 is unblocked by this ADR and stays open: it owns both whether a
  dither path survives and how greyscale input is recognised (histogram
  share, explicit option, or source-format heuristic). Its resolution is to
  be folded into this ADR as a Decision clause on revision, not written as a
  separate ADR.
- AC-127's measurement needs the corpus on disk and a harness that runs both
  paths over it; that harness is a test-tree concern
  (`TestBinarize_ThresholdCorpusNeedsNoMoreNudgesThanDither`) and should not
  add a runtime switch to `binarize` that survives the decision.
- The inclusive boundary at exactly 50% depends on how Pillow rounds the
  LANCZOS average to an integer grey value; the AC-126 fixture pins the
  observable behaviour, and the implementation is free to choose the LUT
  cut-point that satisfies it as long as AC-124 and AC-125 hold too.

## References

- DEC-032 (resolved by this ADR, conditionally — see Status)
- DEC-033 (open; `depends_on: [DEC-032]`; greyscale recognition, not decided here)
- CTX-001 (the one bounded context; COMP-003 image sourcing)
- FR-027, AC-124..AC-127 (the requirement and its gate; `_meta.gate` is binding)
- FR-003 (today's dither statement — amended 2026-09-12, re-worded on resolution, not here)
- FR-013, FR-024 (the mask-driven nudge that runs after binarisation), ADR-0002 (its bound of five)
- CON-013 (silhouettes are the declared scope)
- ADR-0006 (dependency baseline; History touch only — "Pillow does the dithering" rationale)
- ADR-0022 (pipeline order; R3 unchanged), ADR-0015 (image mode stays rng-free), ADR-0023 (export metadata records no binarisation path)
- `src/nonogram/sourcing/image.py` — `binarize` (`:558-594`), `RESAMPLING` (`:194`), `INK_THRESHOLD` (`:200`), module docstring `:117-136`
- `docs/GENERATION_ALGORITHM.md` §4.3, §11

## History

- 2026-09-12: Created — Proposed. Chose the 50% ink-coverage threshold after
  the LANCZOS resize for CON-013 silhouette input over keeping Floyd-Steinberg
  dithering, on the geometry argument (contour over density; the dither's
  boundary speckle is the ambiguity the nudge then repairs), CONDITIONAL on
  FR-027's owner visual gate over the picture corpus, with AC-127 as the
  measured half of that gate. Migration `on-touch`: stored image puzzles are
  not re-converted. DEC-033 (greyscale recognition) left open and dependent.

## Rules
```yaml
- id: ADR-0026/R1
  statement: For silhouette input the per-cell binarisation is a plain inclusive 50% ink-coverage threshold applied to the grey value of the cell AFTER the LANCZOS resize to the grid extent — never a threshold on the source pixels before the resize, and never error diffusion. Exactly 50% coverage is a filled cell.
  scope: {code: ["src/nonogram/sourcing/image.py"]}
  check: {kind: test, ref: TestBinarize_ExactlyHalfCoverageIsFilled}
  # Binding once Status flips to Accepted (FR-027 gate); the check ref goes
  # live with the card that implements FR-027 and is expected to be the
  # AC-126 test. Until then this rule is the intent under test, not the
  # contract — review should not flag the shipped dither against it.
  severity: mandatory
```
