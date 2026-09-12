# ADR-0028: Greyscale input recognition — mid-tone share of the source histogram

**Status:** Accepted (inert until ADR-0026 flips from Proposed to Accepted: with ADR-0026 not yet accepted there is one binarisation path and every input still dithers; the classifier chosen here selects nothing until a second path exists)
**Date:** 2026-09-12
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

ADR-0026 (Proposed, gated on the owner's visual review of the picture corpus)
introduces a second binarisation for image sourcing (FR-003, FR-020; COMP-003
inside CTX-001): for silhouette input, a plain inclusive 50% ink-coverage
threshold on the LANCZOS-resized cell value replaces Pillow's Floyd-Steinberg
error diffusion (`sourcing/image.py:594`). FR-027 states that under either
binarisation "genuinely greyscale input keeps the dithering path", and records
in its `_meta.gaps` that the intake gives no criterion for telling such input
apart. Once ADR-0026 lands, every upload must therefore be routed to one of two
paths, and the rule that routes it is the question here. The question is moot
while ADR-0026 stays Proposed — there is only one path today — and this DEC
carried `depends_on: [DEC-032]` for that reason.

The pipeline the rule must sit in is fixed by ADR-0022 and tabulated in
`docs/GENERATION_ALGORITHM.md` §4.3: `load_greyscale` opens the file, applies
the EXIF transpose and composites any alpha onto white, returning a mode `"L"`
image at its original pixel extent (`image.py:216-261`); then the ink bounding
box is found with `INK_THRESHOLD = 128` (strictly below is ink, `image.py:200`),
the >2x aspect guard runs on that box, the image is trimmed (FR-022), centred
cropped to the grid's ratio, and resized in one LANCZOS call to `width x
height` cells; `binarize` is the last step before `to_grid`. A classifier can
read the pixels at any point in that sequence; where it reads them determines
what it sees — the source's own tonal range before the resize, or the
per-cell coverage averages after it, which are mid-grey along every edge of
every silhouette by construction.

Several standing decisions bound the solution space. CON-013 declares
high-contrast black-and-white silhouettes the scope of image sourcing:
conversion quality, dither tuning and the nudge budget are calibrated for
silhouettes, photographs are out of scope rather than warned about, and
greyscale input is tolerated by FR-027 rather than promoted. ADR-0015 keeps
image mode rng-free: the same file at the same extent converts to the same
grid, with no seed involved. ADR-0010 fixes the CLI's argument surface and
ADR-0023 the export metadata schema (version 2, `width`/`height`); COMP-008's
web form and the admin batch upload both build a `GenerationRequest` from the
same fields, so any new per-upload option crosses every one of those
surfaces at once. ADR-0006/R1 fixes the dependency set at stdlib + Pillow +
NumPy, so whatever the rule computes must be a Pillow or NumPy primitive.

The forces: an automatic rule needs no new surface but can be wrong, and
the owner validates image-pipeline changes by eye (project memory), so a
wrong routing has to be at least *visible*; an explicit option is never
wrong but pushes a technical choice onto every upload for an input class
CON-013 says is not the target; and the pictures the owner actually uploads
are anti-aliased PNGs and JPEGs, not clean bilevel exports, so any rule keyed
on file format or exact colour count would misroute the common case.

## Decision

We will classify each upload automatically by the **mid-tone share of its
source histogram**: on the mode `"L"` image `load_greyscale` returns — after
the EXIF transpose and the alpha-onto-white composite, and BEFORE the trim,
the crop and the resize — compute the share of pixels whose grey value lies
in the closed mid band `[64, 191]`. If that share is at or above a named
constant `MIDTONE_SHARE_THRESHOLD` the input is genuinely greyscale and keeps
the Floyd-Steinberg dither path; otherwise it is a silhouette and takes
ADR-0026's inclusive 50% coverage threshold. The provisional value is
`MIDTONE_SHARE_THRESHOLD = 0.10`; it is **calibration-owed** — the
implementing card sets it on the owner's picture corpus (`pictures/`, the
owner's own trial folder, not in the repository at the time of writing) and
the number in this ADR is a starting point, not a measurement. Both the band
bounds and the share constant live beside `INK_THRESHOLD` in
`sourcing/image.py`, one tuning table for the module. The share is one
histogram pass (`Image.histogram()`, C-level, 256 bins summed over the band)
and adds no dependency.

The classification is a pure function of the file: no rng is consulted
(ADR-0015 — image mode stays rng-free), and the same file always classifies
the same way. The path taken is **recorded**, not inferred: a field
`binarisation: threshold | dither` is written to the puzzle's metadata and
carried into every export, so that a mis-classification is diagnosable from
the artefact rather than silent. Adding that field is a follow-up that
touches ADR-0023's export schema (a schema-version bump or an additive field
under its rules) and is not made here.

The rule reads the source image and not the resized one on purpose: after
the LANCZOS resize every boundary cell of every silhouette is a coverage
average — a mid-grey — so a histogram there would classify the silhouette
edge itself as tone. Before the resize, a silhouette's mid-greys are only
its anti-aliased edge pixels and compression ringing, a thin band around the
contour that is a small share of the picture; a genuinely greyscale picture
has mid-tones across regions, a large share. That is the property CON-013's
own phrase "high-contrast" names, which is why a histogram measures it
directly.

This decision is Accepted on its own terms but its effect is inert until
ADR-0026 is Accepted: with ADR-0026 Proposed, `binarize` has one path and all
input still dithers. If ADR-0026 is withdrawn at the owner's gate, this ADR
becomes moot without needing to be revised — it selects between two paths of
which only one would then exist — and its History records that outcome. It
was chosen over the alternatives because it adds zero new CLI/web/admin
surface, is consistent with CON-013 (silhouettes are the scope; greyscale is
tolerated, not promoted to a user-facing mode), and costs one C-level pass
over the pixels. The explicit option was passed over knowing it is the
lower-risk choice for classification accuracy; the reason is stated under
Alternatives and its fallback role is kept: if calibration on the corpus
proves the boundary unstable, `explicit_user_option` is the revision path.

## Alternatives considered

### `explicit_user_option` — a `--binarize {threshold,dither}` flag and matching web field (rejected; the fallback if calibration fails)
The user states which path to take; the CLI gains `--binarize` (default
`threshold`, since CON-013 declares silhouettes the scope), the web form and
the admin batch upload gain the same field, and the export records the
choice, so a conversion is reproducible from its metadata alone. No
mis-classification is possible — the owner's visual judgement, which
ADR-0026's gate already relies on, is the classifier — and the two paths are
selected, never inferred, so the tests are trivial. Rejected because the
blast radius is the whole request path: a new field through
`GenerationRequest`, the CLI (ADR-0010), the web form (COMP-008), the admin
batch upload and ADR-0023's export schema, all to serve an input class
CON-013 says is out of scope, while the default would do the right thing for
the declared scope anyway. It also puts a technical choice in front of the
user on every upload. It remains the named revision path should the
histogram constant prove impossible to calibrate on the corpus.

### `source_format_heuristic` — classify by what the file is (rejected)
Mode `"1"`, a two-colour palette, or a histogram with exactly two populated
values means silhouette; anything else dithers. The cheapest possible rule
and exact for clean bilevel exports from a drawing tool. Rejected because it
is wrong for the common case: a silhouette saved as an anti-aliased PNG, or
as a JPEG, has hundreds of populated grey values and would dither — the
corpus the owner actually uploads would mostly miss the threshold path
ADR-0026 chose for it. The mid-tone share is the same idea made tolerant of
those edge pixels: it asks how *much* of the picture is mid-grey, not
whether any of it is.

### Collapse to "silhouettes only, always threshold" (rejected by the owner)
Drop FR-027's greyscale clause: CON-013 says silhouettes are the scope, so
every input takes the threshold and no classifier exists. Cheapest of all —
no constant, no second path to route, DEC-033 disappears and ADR-0006's
"Pillow does the dithering" rationale is simply retired. The owner chose to
keep a dither path for genuinely greyscale input, so this alternative is
rejected by decision rather than by analysis; FR-027's statement stands as
written.

### `midtone_share_histogram` — the chosen option
Recorded above under Decision. The DEC's own cons are carried honestly into
Consequences: anti-aliased edges and JPEG ringing produce mid-greys too, the
boundary is soft, the constant is calibration-owed, and the rule is one more
hidden decision in the image pipeline the owner cannot override per picture
— which is exactly why the path taken is recorded on the artefact.

## Consequences

### Positive
- Zero new surface: no CLI flag (ADR-0010 untouched), no web-form field, no
  admin batch-upload field, no `GenerationRequest` change. The classifier is
  two constants next to `INK_THRESHOLD` and one histogram pass in
  `sourcing/image.py`.
- Deterministic and reproducible: a pure function of the decoded file,
  rng-free (ADR-0015), so the same upload always takes the same path and a
  regression is a fixture test, not a flake.
- Consistent with CON-013's framing: "high-contrast" is a histogram
  property, and the rule measures it directly on the source rather than
  guessing from file format. Greyscale input keeps working without being
  promoted to a user-facing mode.
- Diagnosable: the recorded `binarisation` field means a puzzle that looks
  wrong can be traced to its routing in one glance at the metadata, and the
  owner's rendered-grid eyeball has something to check against.
- Negligible cost: `Image.histogram()` is a single C-level pass over pixels
  that are already decoded (EC-007's one-decode guarantee is unaffected).

### Negative
- The boundary is soft. Anti-aliased silhouette edges and JPEG ringing
  produce mid-greys too — a thin-stroked or heavily compressed silhouette can
  cross the constant and dither where the owner expected a contour, and a
  low-contrast greyscale picture can fall below it and threshold into two
  flat blobs. The constant `0.10` is provisional; until it is calibrated on
  the corpus the rule is a guess, and the calibration is owed by the
  implementing card, not by this ADR.
- A mis-classification is silent at conversion time: nothing warns, and it is
  visible only through the recorded `binarisation` field and the rendered
  grid. The owner cannot override the routing per picture short of editing
  the picture (raising its contrast) or revising this ADR toward
  `explicit_user_option`.
- One more hidden rule in the image pipeline, with two magic numbers (band
  bounds, share constant) whose justification lives in a docstring and a
  corpus the repository does not contain.
- Follow-up debt: the `binarisation` metadata field touches ADR-0023's export
  schema (additive field or version bump) and the admin panel's stored
  puzzles; until that lands, the diagnosability argument above is a promise.
- `Migration: on-touch`: puzzles already stored by the admin panel were
  converted by the dither path with no recorded field; they are not
  re-converted or back-filled, and a picture uploaded before and after may
  yield a different grid.

### Neutral
- Inert until ADR-0026 is Accepted; if ADR-0026 is withdrawn at the owner's
  gate this ADR becomes moot with no revision needed — a History entry
  records the outcome.
- The classifier reads the `"L"` image `load_greyscale` returns, before the
  trim (FR-022) and the resize; ADR-0022's step order gains a read-only
  probe between "load" and "ink bounding box" and is otherwise unchanged.
  `docs/GENERATION_ALGORITHM.md` §4.3 needs one row when this lands.
- ADR-0006's "Pillow does the dithering" rationale narrows to the greyscale
  path rather than being retired — History touch only, R1 unaffected.
- FR-027's `_meta.gaps` entry on greyscale recognition is closed by this ADR
  and should be cleared on the next requirements touch, with an acceptance
  criterion pair (a corpus silhouette routes to `threshold`, a synthetic
  gradient routes to `dither`) added under FR-027 — not edited here.
- Calibration needs the corpus on disk and a small harness that prints each
  picture's mid-tone share next to its filename; that harness belongs in the
  test tree or a scratch script, not in `binarize`.
- If calibration is unstable, the revision path is `explicit_user_option`,
  which would then reuse the same `binarisation` metadata field to record
  the user's choice — the field is designed to survive that revision.

## References

- DEC-033 (resolved by this ADR)
- DEC-032 / ADR-0026 (the dependency: the second binarisation path this rule selects; Proposed, owner-gated)
- CTX-001 (the one bounded context; COMP-003 image sourcing)
- FR-027 (greyscale clause and `_meta.gaps` entry closed here), FR-003, FR-020, FR-022
- CON-013 (silhouettes are the declared scope; greyscale tolerated, not promoted)
- ADR-0015 (image mode stays rng-free), ADR-0010 (CLI surface unchanged), ADR-0023 (export schema — follow-up for the `binarisation` field), ADR-0022 (pipeline order), ADR-0006 (dependency baseline; History touch only)
- `src/nonogram/sourcing/image.py` — `load_greyscale` (`:216-261`), `INK_THRESHOLD` (`:200`), `binarize` (`:558-594`), module docstring `:117-136`
- `docs/GENERATION_ALGORITHM.md` §4.3

## History

- 2026-09-12: Created — Accepted, inert until ADR-0026 is Accepted. Chose
  the mid-tone share of the source histogram (band `[64, 191]`, provisional
  `MIDTONE_SHARE_THRESHOLD = 0.10`, calibration-owed on the picture corpus)
  over an explicit `--binarize` option, a source-format heuristic, and the
  "always threshold" collapse, for zero new surface and consistency with
  CON-013; the path taken is recorded as `binarisation: threshold|dither` on
  the puzzle/export metadata (ADR-0023 follow-up). Migration `on-touch`.

## Rules
```yaml
- id: ADR-0028/R1
  statement: The choice between the threshold and the dither binarisation is a pure function of the decoded source image (mid-tone share of the "L" histogram before trim and resize) against MIDTONE_SHARE_THRESHOLD — no rng, no request field, no per-upload override; and the path taken is recorded on the puzzle metadata as `binarisation`.
  scope: {code: ["src/nonogram/sourcing/image.py"]}
  check: {kind: review-lens}
  # Binding once ADR-0026 is Accepted and the second path exists; until then
  # there is one path and nothing to select. The check becomes a test ref
  # with the card that implements the classifier.
  severity: mandatory
```
