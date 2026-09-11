# CARD-047: predict_size() adds a synchronous full-image decode to batch page renders

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/047-precompute-source-shape-on-upload
**Worktree:** —
**Source:** meta/review/20260910T164426Z.yml#F-005
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py
**Review score:** —
**Started:** —
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
