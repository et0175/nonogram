# CARD-045: predict_size() can crash a whole batch page on a degenerate image

**Status:** ready
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/045-predict-size-uncaught-value-error
**Worktree:** —
**Source:** meta/review/20260910T164426Z.yml#F-001,F-002,F-003
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py, tests/test_image_batch_size_fix.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`ImageFile.predict_size()` (`src/nonogram/admin/image_manager.py:68-121`, landed in
`ec18fb4`) calls `derive_extent(stated, None, src_width, src_height)` and catches
`SizeTooSmallForSource` and `NonogramError`, but `derive_extent` →
`_checked_extents` can also raise a plain `ValueError` (not a `NonogramError`
subclass) when the source shape has a non-positive axis. `src_width`/`src_height`
come from `_source_shape()` (lines 42-65), which falls back to `self.dimensions`
on any exception — and `self.dimensions` can genuinely be `(0, 0)`: `add_image()`
(lines 240-246) defaults it to `(0, 0)` and only overwrites it inside a bare
`except Exception: pass` around a second, independent `PILImage.open()` on the
copied temp file. If that second open fails (distinct from the upload-time
validation open, which already succeeded once), the image is still stored as
"successfully added" with `dimensions=(0, 0)`.

When that happens, `_source_shape()`'s own fallback also lands on `(0, 0)`, and
`derive_extent(stated, None, 0, 0)` raises an uncaught `ValueError`. This
propagates out of `predict_size()` into two **unprotected** `render_template()`
calls that loop over every image in the batch with no try/except around the
render:
- `app.py:289-292` (`preview_batch_images` GET — the page users land on right
  after upload)
- `app.py:307-310` (`generate_batch_puzzles` GET confirmation page)

One degenerate image in a batch of up to 200 would 500 the *entire* preview
page, not just the broken image. (The actual generation POST loop at
`app.py:332-373` already has a per-image `try/except Exception`, so it is not at
risk — this is specifically the two GET render paths.)

Separately: the `except NonogramError: return (stated, stated)` branch at line
120 is dead code and gives false confidence this case is handled. `stated` is
always pre-clamped into `[MIN_SIZE, MAX_SIZE]` at line 106 before the
`derive_extent` call, so `validate_extent(stated, stated)` inside `derive_extent`
can never raise, and the only other `NonogramError` subclass `derive_extent` can
raise (`SizeTooSmallForSource`) is already caught by the preceding `except`
clause — so this branch can never execute.

1. Add `ValueError` to the exception handling around the `derive_extent` call at
   `image_manager.py:109` (either an explicit `except ValueError:` returning a
   safe fallback like `(MIN_SIZE, MIN_SIZE)`, or validate `src_width > 0 and
   src_height > 0` in `_source_shape()` itself before returning, falling back to
   a safe minimum rather than propagating a bad shape onward).
2. Remove or repurpose the dead `except NonogramError` branch at line 120 so it
   actually covers a reachable case (or delete it if the `ValueError` fix above
   makes it redundant).
3. Add a regression test constructing an `ImageFile` with `dimensions=(0, 0)`
   (or an image whose second `PILImage.open()` can be made to fail) and asserting
   `predict_size()` returns a safe fallback tuple instead of raising.

## Acceptance criteria

- **AC-1** — given an `ImageFile` whose `dimensions` is `(0, 0)` (the documented
  reachable state from `add_image`'s silent second-decode failure), when
  `predict_size()` is called, then it returns a valid `(width, height)` tuple in
  `[MIN_SIZE, MAX_SIZE]` on both sides instead of raising `ValueError`.
  *test:* to be named by the implementer, in `tests/test_image_batch_size_fix.py`.
- **AC-2** — given the same degenerate image is included in a batch, when
  `GET /batch/preview-images` or `GET /batch/generate-puzzles` is requested, then
  the page renders successfully (200) for the whole batch, not just a 500.
  *test:* to be named by the implementer (Flask test client).
- **AC-3** — the `except NonogramError` branch at `image_manager.py:120` is
  either removed or demonstrably reachable (not dead code) after the fix.

## Guardrails

- G-1: Do not change `predict_size()`'s return contract for any already-working
  image (a real, positive-dimension picture) — this card only closes the
  degenerate-input gap, it must not touch the ink-bbox / `derive_extent` logic
  that CARD ec18fb4 just fixed.
