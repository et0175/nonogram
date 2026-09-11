# CARD-047: predict_size() adds a synchronous full-image decode to batch page renders

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/047-precompute-source-shape-on-upload
**Worktree:** ../PythonProject4-CARD-047
**Source:** meta/review/20260910T164426Z.yml#F-005
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py
**Review score:** —
**Started:** 2026-09-11T12:45:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Before `ec18fb4`, `ImageFile.predict_size()` was pure arithmetic on
`self.dimensions`, which is read cheaply at upload time (`PILImage.open(...).size`
— a header read, no full decode). Since `ec18fb4`, `_source_shape()`
(`src/nonogram/admin/image_manager.py:42-65`) calls
`nonogram.sourcing.image.source_shape()` on first access, which fully decodes
the image (`load_greyscale`) and scans every pixel (`ink_bounding_box`'s
`Image.point` + `getbbox`) to compute the ink bounding box. The result is cached
per-instance, but the *first* call per image pays the full cost — and that first
call now happens **synchronously inside unpaginated per-batch template loops**:

- `image_preview.html`'s `{% set dims = image.predict_size() %}` inside a
  `{% for image in images %}` loop, rendered from `app.py:289-292` with no
  pagination
- `generate_batch.html`'s same pattern, rendered from `app.py:307-310`

The `/batch/preview-images` route's own validation allows up to 200 images per
batch (`app.py:256-257`), each up to 2000×2000px
(`image_manager.py:152`, `MAX_DIMENSIONS`). A full-batch first page load now
pays up to 200 synchronous PIL decodes + NumPy bounding-box scans before the
response is sent, where it previously paid none.

1. Compute and cache the ink bounding box **once, at `add_image()` time**
   (`image_manager.py:209-266`), alongside the existing `dimensions` read —
   the same place `dimensions` is already captured up front — rather than
   lazily inside the render-time `predict_size()` call. Store it as a field on
   `ImageFile` (or keep `_source_shape()`'s lazy-cache shape, just prime it
   during upload instead of on first render).
2. If eager computation at upload time is judged too costly for a single-image
   upload request, an acceptable alternative is documenting the measured cost
   (a real timing, not a guess) and an explicit accepted ceiling on batch size —
   but the default expectation is to move the cost off the render path.

## Acceptance criteria

- **AC-1** — given a batch of N images, when `GET /batch/preview-images` is
  requested for the first time after upload, then the total added latency from
  ink-bounding-box computation is measured (before/after this card) and either
  eliminated from the request path or reduced to a documented, accepted bound.
  *test:* a timing assertion or a documented measurement in the card's
  Worktree notes — implementer's judgment on the concrete mechanism.
- **AC-2** — existing behavior (predicted size correctness, the fix from
  `ec18fb4`) is unchanged; only the *timing* of when the ink bounding box is
  computed moves.

## Guardrails

- G-1: Do not change what `predict_size()` returns for any image — this is a
  performance-only card. Any accidental behavior change here should be treated
  as a regression of `ec18fb4`, not a fix.

## Worktree notes

**Implementation:** `ImageManager.add_image()` now calls
`image._source_shape()` immediately after constructing the `ImageFile`
record — while the request is already paying for one synchronous file
copy per image — instead of leaving the first access lazy until a
render-time `predict_size()` call inside `image_preview.html`/
`generate_batch.html`'s per-batch template loops. `_source_shape()`
never raises (falls back to `dimensions` on any decode failure), so
priming it can't turn a successful upload into a failed one. No other
behavior changes — `predict_size()`'s call path and the per-instance
`_cached_source_shape` mechanism are otherwise untouched (G-1).

**AC-1 (measured latency):** benchmarked `nonogram.sourcing.image.source_shape()`
directly (20-30 call average, after a filesystem-cache warm-up call):
- Worst case (2000x2000px, `MAX_DIMENSIONS`): **~5.2 ms/call** → up to
  **~1.0 s** added to a 200-image batch's *first* render, pre-fix.
- Typical case (800x600px): **~0.7 ms/call** → **~147 ms** for 200 images,
  pre-fix.

Both now happen during the `/batch/from-images` upload POST (already
O(N) synchronous work: N file copies), not during the subsequent
`/batch/preview-images` or `/batch/generate-puzzles` GET renders a user
is more likely to revisit/wait on interactively. Did not pursue
async/background computation (step 2's documented-ceiling alternative)
— eager computation at upload time was not judged too costly (the
measured cost above is well within what an upload request handling N
file copies already spends), so the default expectation (move the cost
off the render path) was followed directly.

**Tests:** new `tests/test_card_047_eager_source_shape.py` (4 tests):
- `test_add_image_primes_the_source_shape_cache_immediately` (AC-1):
  `_cached_source_shape` is populated the moment `add_image()` returns.
- `test_decode_happens_during_add_image_not_on_first_render` (AC-1, the
  decisive test): monkeypatches `nonogram.sourcing.image.source_shape`
  with a call counter and asserts it was already called exactly once
  **immediately after `add_image()` returns, before any `predict_size()`
  call** — deliberately checked before touching `predict_size()` at all,
  since "called exactly once ever" alone would hold even under the old
  lazy-on-first-render behavior and wouldn't distinguish the fix from
  the bug it replaces.
- Two AC-2/G-1 tests reusing CARD-046's margin-fixture pattern (a 300x100
  canvas with an 81x81 drawn square) and a plain borderless image, to
  confirm `predict_size()`'s return value is byte-identical to before
  this change — only the timing moved.

Red→green verified via `git stash` on just `image_manager.py`: both
AC-1 tests fail against the pre-fix code (`_cached_source_shape` is
`None` after `add_image()`; the call-count is `0` immediately after
`add_image()` returns, not `1`). Restored the fix; all 4 pass.

**Regression check:** new file + `test_wave3_e2e.py` +
`test_image_batch_size_fix.py` + `test_admin_image_uniqueness.py` +
`test_cli.py::test_every_import_in_the_package_points_inward` — 39/39
pass, 4 pre-existing skips. Specifically checked
`test_image_batch_size_fix.py`'s CARD-045 degenerate-image tests
(construct `ImageFile` directly, bypassing `add_image()` entirely) and
its Flask-integration degenerate-batch tests (call `add_image()` then
manually overwrite `dimensions`/`_cached_source_shape` afterward) —
neither interacts with the new eager-priming call; both still pass.
Full suite: 40 failures, all in the previously documented flaky/
corpus-dependent classes (`test_sourcing_image.py`/`test_derive_shape.py`/
`test_nudge.py`/`test_nudge_reporting.py`/`test_export_pdf.py`/
`property/test_grid_dimensions.py`; `test_batch_history.py`/
`test_wave1_e2e.py`/`test_wave2_async_generation.py`/`test_web_upload.py`)
— none touching `image_manager.py` or the new test file.
