# CARD-079: Threshold binarisation for silhouettes behind a switch, mid-tone classifier, corpus rendered both ways for the owner's eye

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/079-threshold-binarisation-gated
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-12
**Idea:** —
**Wave:** 1
**Depends on:** CARD-072, CARD-075, CARD-076
**Touches:** src/nonogram/sourcing/image.py (binarize switch, MIDTONE_SHARE_THRESHOLD + band, classifier, module rationale rewrite), src/nonogram/orchestrator.py (Puzzle carries `binarisation`), src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/export/csv_export.py (`binarisation` metadata field, ADR-0023 rules), tests/test_sourcing_image.py, tests/test_export_json.py, tests/test_export_csv.py, tests/property/test_export_roundtrip.py, tools/render_binarisation_review.py or tests/bench-style script (new — renders the corpus both ways into a review folder), docs/GENERATION_ALGORITHM.md (§4.3 one row, §11), meta/architecture/decisions/adr/0006-*.md (History touch)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Floyd-Steinberg dithering preserves average density, not contour: on a
silhouette it seeds isolated cells and ragged edges along the boundary —
exactly the one-cell runs and 2x2 switching blocks that make a nonogram
non-unique and that the nudge then repairs one cell at a time. ADR-0026
(DEC-032, **Proposed**) chooses an inclusive 50% ink-coverage threshold
after the LANCZOS resize for CON-013 silhouette input; ADR-0028 (DEC-033,
Accepted but inert until ADR-0026 is) recognises genuinely greyscale input
by the mid-tone share of the source histogram and keeps it on the dither
path. The hypothesis — more first-solve-unique conversions, fewer nudges —
is measured by AC-127, but the gate is the owner's eye on rendered grids
(memory: image-pipeline changes need a rendered-grid eyeball, not green
tests).

**The gate (FR-027 _meta.gate, binding):** this card ends when the
side-by-side render of every corpus picture is in front of the owner with
AC-127's two numbers per picture. Flipping ADR-0026 to Accepted and the
switch's default to threshold is the owner's action, not the card's. Until
then the default stays dither.

**Sequencing.** Last card of wave 2 and owner-gated. After CARD-075 (AC-127
counts nudges — the mask-driven nudge must be the one measured), after
CARD-076 and CARD-072 (export schema touched in order: guess value,
`strategies`, then `binarisation` — one more version bump at most). The
corpus `pictures/` is the owner's own trial folder and is not on disk at
the time of writing (memory: layout undecided, do not restructure) — the
render script and the AC-127 test skip cleanly when it is absent, like the
existing corpus tests in `tests/test_sourcing_image.py`.

## What to implement

1. **Named switch, both paths exist.** `sourcing/image.py`'s `binarize`
   gains a `BinarisationPath` (`threshold` | `dither`) selected by a
   module-level default (`DEFAULT_BINARISATION = "dither"` until the owner
   flips it) plus the classifier below; both paths are callable so the
   review render and AC-127 can run each explicitly. Threshold:
   `Image.point` at 128 on the resized "L" image producing mode "1" —
   ink coverage >= 50% fills (ADR-0026/R1; the AC-126 fixture pins the LUT
   cut-point against Pillow's LANCZOS rounding). Dither: today's
   `convert("1", dither=FLOYDSTEINBERG)`, unchanged.
2. **Mid-tone classifier (ADR-0028/R1).** On the "L" image
   `load_greyscale` returns — after EXIF transpose and alpha-onto-white,
   BEFORE trim/crop/resize — the share of pixels in the closed band
   `[64, 191]` (one `Image.histogram()` pass). Share >=
   `MIDTONE_SHARE_THRESHOLD` (provisional 0.10) -> genuinely greyscale ->
   dither; else silhouette -> threshold. Constants live beside
   `INK_THRESHOLD`. Pure function of the file: no rng, no request field,
   no per-upload override. **Calibration-owed:** record the mid-tone share
   of every corpus picture in Worktree notes so the owner can set the
   constant on data; do not tune it on this card.
3. **`binarisation` recorded, not inferred:** the path taken is set on the
   `Puzzle` aggregate for image mode and carried into the JSON/CSV export
   metadata as `binarisation: threshold | dither` (ADR-0023 follow-up: an
   additive field, or a `SCHEMA_VERSION` bump if an existing reader could
   not survive — decide by ADR-0023/R2's own rule; JSON accepts unknown
   keys, CSV rejects them, so CSV likely needs the bump). Random/library
   puzzles carry no such field (or `null`) — say which.
4. **Review render.** A script (test-tree or `tools/`) that converts every
   picture under `pictures/` both ways at the batch's predicted extent
   (`derive_extent`, the CARD-061/064 presets) and writes a side-by-side
   rendered grid per picture (PNG via the existing renderer, threshold
   left, dither right) plus AC-127's two numbers per picture
   (first-solve unique? nudges needed) into a review folder outside `src/`
   (e.g. `review/binarisation-<date>/`, untracked — not committed). Skips
   cleanly when `pictures/` is absent.
5. **Docs and ADR touches:** the module rationale "dither before
   threshold, not instead of it" (`image.py:133-136`) is rewritten to
   describe both paths and the switch; `docs/GENERATION_ALGORITHM.md` §4.3
   step 8 row and §11; ADR-0006 History touch ("Pillow does the dithering"
   narrows to the greyscale path). FR-003's statement and AC-007's test
   name are re-worded **only after** the gate passes — not on this card
   (ADR-0026 Negative).
6. **Stop at the gate.** Put the review folder and the per-picture numbers
   in front of the owner (Worktree notes carry the folder path and the
   AC-127 totals). The card is done when that is in front of the owner;
   the owner's confirmation flips ADR-0026's Status and
   `DEFAULT_BINARISATION` in a follow-up commit that is theirs to ask for.

## Acceptance criteria

- **AC-124** — given a resized cell with 80% ink coverage (grey 51), when
  binarised under the threshold path, then the cell is filled.
  *test:* `TestBinarize_ThresholdFillsCellAtOrAboveHalfInkCoverage`
- **AC-125** — given 49% coverage, then the cell is empty.
  *test:* `TestBinarize_ThresholdLeavesCellEmptyBelowHalfInkCoverage`
- **AC-126** — given exactly 50% coverage, then the cell is filled (the
  boundary is inclusive).
  *test:* `TestBinarize_ExactlyHalfCoverageIsFilled` (ADR-0026/R1's check
  ref — goes live with this card)
- **AC-127** — given the corpus under `pictures/`, each converted at a bare
  `--size 25` by both paths, when the first-solve uniqueness verdicts and
  nudge counts are compared, then the threshold path's count of
  first-solve-unique conversions is >= the dither path's and its total
  nudges <= the dither path's. Skips cleanly when `pictures/` is absent.
  *test:* `TestBinarize_ThresholdCorpusNeedsNoMoreNudgesThanDither`
- **AC-A** (classifier) — a silhouette fixture (mid-tone share well below
  0.10) classifies `threshold`; a greyscale-gradient fixture (share well
  above) classifies `dither`; the classification is identical on repeated
  loads and reads the source image, not the resized one.
  *test:* `TestBinarize_ClassifierIsDeterministicAndReadsSourceHistogram`
- **AC-B** (recorded path) — an image-mode puzzle carries `binarisation`
  on the aggregate and in the JSON and CSV export, round-tripping
  (EC-002 style); random/library puzzles carry none.
  *test:* `TestBinarize_RecordsBinarisationPathOnPuzzleAndExport`
- **AC-C** (default unchanged until the gate) — with the shipped default,
  every existing image-mode test in `tests/test_sourcing_image.py` and
  `tests/test_nudge.py` passes unchanged in assertion (the dither path is
  still what ships).
- **AC-D** (the gate, handoff checkpoint) — a side-by-side render of every
  corpus picture (threshold vs dither, at the batch's predicted extent) is
  in front of the owner with AC-127's two numbers per picture; Worktree
  notes record the folder, the totals and each picture's mid-tone share.

## Engineering constraints

- **EC(ADR-0028/R1)** — the path choice is a pure function of the decoded
  source image against `MIDTONE_SHARE_THRESHOLD`: same file, same path, on
  every load and every host; no rng, request field or override enters it.
  *test:* `PropertyTest_Binarize_ClassifierPureFunctionOfSourceImage`
  (seeded synthetic images: silhouettes with varying anti-alias width,
  gradients with varying mid-tone share)
- **EC(ADR-0026/R1, gated)** — under the threshold path, for any resized
  grey value g: filled iff g <= 127; never applied before the resize;
  never error diffusion.
  *test:* `PropertyTest_Binarize_ThresholdIsInclusiveHalfCoverageOnResizedImage`

## Guardrails

- G-1: The shipped default stays `dither` on this card; flipping
  `DEFAULT_BINARISATION` and ADR-0026's Status to Accepted is the owner's
  action after the visual gate — never this card's commit.
- G-2: Pipeline order unchanged (ADR-0022/R3): trim, ink-box aspect guard,
  centred crop, LANCZOS resize, THEN binarisation, then `to_grid`, then
  the orchestrator's uniqueness check and the FR-013 nudge. The classifier
  reads the source image before trim/crop/resize (ADR-0028).
- G-3: No new runtime dependency (ADR-0006/R1); Pillow primitives only.
- G-4: Image mode stays rng-free (ADR-0015); no request field or CLI/web
  option selects the path (ADR-0028 rejected `--binarize`).
- G-5: Stored image puzzles are never re-converted (Migration: on-touch).
- G-6: No edits under `src/nonogram/solver/`, `difficulty.py`; the nudge
  mechanism (CARD-075) and the recovery loop (CARD-074) untouched; the
  oracle and `tests/property/test_solver_uniqueness.py` untouched.
- G-7: Do not restructure or commit the owner's picture corpus
  (`pictures/`, `pic1/` — memory: experiments, layout undecided); the
  review folder is untracked output.
- G-8: FR-003's statement and AC-007's test name are not re-worded here
  (post-gate follow-up).
- G-9: Commit only your own files — explicit pathspecs.

## System contract

- ADR-0026/R1 (GATED — intent under test until Status flips; review must
  not flag the shipped dither against it) — inclusive 50% ink-coverage
  threshold on the resized grey value, never before the resize, never
  error diffusion (check: TestBinarize_ExactlyHalfCoverageIsFilled)
- ADR-0028/R1 — path choice is a pure function of the source histogram
  against MIDTONE_SHARE_THRESHOLD; path recorded as `binarisation` (check:
  TestBinarize_RecordsBinarisationPathOnPuzzleAndExport)
- ADR-0022/R3 — trim, aspect guard, centred crop, resize order unchanged
  (check: tests/test_sourcing_image.py, tests/property/test_image_fit.py)
- ADR-0006/R1 — dependency baseline: stdlib + Pillow + NumPy (+ reportlab
  per CARD-057) — nothing new (check: review-lens)
- ADR-0023/R1 — export records width/height, never a scalar size;
  ADR-0023/R2 — decoder accepts only its own SCHEMA_VERSION (check:
  TestExport_RejectsSupersededSchemaVersion)
- ADR-0015 — image mode draws nothing from the rng (check: review-lens)
- CON-013 — image sourcing scoped to high-contrast silhouettes; greyscale
  is tolerated via the dither path, not promoted to a mode (check:
  review-lens)
- ADR-0007 — no lateral imports (check: test_every_import_in_the_package_points_inward)

## Architecture context

- **FR:** FR-027 (AC-124..AC-127), FR-003 (amended; re-worded post-gate),
  FR-013 (nudge runs after either path)
- **CON:** CON-013
- **ADR:** ADR-0026 (Proposed, R1 gated), ADR-0028 (R1), ADR-0022,
  ADR-0006 (History touch), ADR-0023 (metadata field), ADR-0015
- **Decisions:** DEC-032 (gate), DEC-033
- **Components:** COMP-003 (sourcing/image), COMP-002 (aggregate field),
  COMP-007 (metadata)
- **Trace:** meta/architecture/trace.yml (FR-027 row)

**Checkpoint (handoff, verbatim):** A side-by-side render of every corpus
picture (threshold vs dither, at the batch's predicted extent) is in front
of the owner, with AC-127's two numbers per picture; the owner says which
path ships. Until then the default is unchanged (dither).
**Collapses:** FR-027, the "dither creates the ambiguity the nudge then
repairs" hypothesis, ADR-0028's mid-tone constant (calibrated on the corpus
rather than guessed), DEC-032's gate.
**Rollback:** On-touch: the switch default reverts to dither; stored image
puzzles are never re-converted.

## Worktree notes

—
