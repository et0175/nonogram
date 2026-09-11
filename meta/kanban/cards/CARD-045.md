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

## Worktree notes

Implemented the fix exactly as scoped, no files outside
`src/nonogram/admin/image_manager.py` and `tests/test_image_batch_size_fix.py`
touched.

**`src/nonogram/admin/image_manager.py`** (`predict_size()`, ~line 95-127):
- Added `except ValueError:` after the existing `except SizeTooSmallForSource:`
  clause around the `derive_extent(stated, None, src_width, src_height)` call,
  returning `(MIN_SIZE, MIN_SIZE)` — a safe fallback square, both sides
  trivially inside `[MIN_SIZE, MAX_SIZE]`. This is the plain `ValueError`
  `derive_extent` raises (not a `NonogramError` subclass) when
  `_source_shape()` reports a non-positive axis, e.g. the documented `(0, 0)`
  fallback from `add_image`'s silent second-decode failure.
- Removed the dead `except NonogramError: return (stated, stated)` branch
  (was unreachable per the card's own analysis: `stated` is pre-clamped
  before `derive_extent` runs, so `validate_extent(stated, stated)` can never
  raise, and the only other `NonogramError` subclass `derive_extent` can
  raise, `SizeTooSmallForSource`, is already caught by the preceding clause).
  Adjusted the `from nonogram.errors import ...` line accordingly (only
  `SizeTooSmallForSource` is still needed).
- Nothing else in `predict_size()`, `_source_shape()`, or `derive_extent`
  changed — the ink-bbox / aspect-fit logic for real, positive-dimension
  images is untouched (G-1).

**`tests/test_image_batch_size_fix.py`**: added three new test classes
alongside the existing ones (file was already in scope from an earlier
card):
- `TestPredictSizeDegenerateInput` (AC-1) — constructs an `ImageFile` with
  `dimensions=(0, 0)` and an unreadable `file_path` (so `_source_shape()`
  also falls back to `(0, 0)`) and asserts `predict_size()` returns a
  `(width, height)` tuple inside `[MIN_SIZE, MAX_SIZE]` instead of raising.
  Parametrized across all three `size_mode` values. Also includes
  `test_predict_size_real_image_unaffected`, a direct G-1 regression check:
  a real 200x100 picture at `size_value=20` still predicts exactly `(20, 10)`
  (unchanged from `ec18fb4`).
- `TestPredictSizeNonogramErrorBranchNotDead` (AC-3) — asserts
  `"except NonogramError"` no longer appears in `predict_size`'s source via
  `inspect.getsource`, i.e. the dead branch is gone rather than merely
  unreached-but-present.
- `TestBatchPreviewDegenerateImageIntegration` (AC-2) — real Flask test
  client (`create_app(debug=True)`, in-memory mode, `DATABASE_URL` unset via
  `monkeypatch.delenv`) against a batch containing a degenerate image
  (loaded via the real `add_image()` path, then `dimensions`/
  `_cached_source_shape` reset to `(0, 0)` to reproduce the documented
  failure state). Asserts `GET /batch/preview-images` and
  `GET /batch/generate-puzzles` both return 200, including a mixed
  good+degenerate batch case.

**Regression verification**: manually confirmed both new integration tests
fail against the pre-fix code (`git stash` the fix, rerun) with the exact
`ValueError: a source's own shape has a positive extent on both axes, got
0x0` the card predicts, propagating out of
`image_preview.html`'s/`generate_batch.html`'s `image.predict_size()` Jinja
call as an uncaught 500 — then pass after the fix.

**Test results**:
- `./.venv/bin/python -m pytest tests/test_image_batch_size_fix.py -v` →
  17 passed.
- `./.venv/bin/python -m pytest tests/ -k "admin or image" -q` → same 17
  pre-existing failures before and after this change (all in
  `tests/test_sourcing_image.py`, `tests/test_derive_shape.py`,
  `tests/test_nudge.py`, `tests/property/test_grid_dimensions.py`; all
  `FileNotFoundError`/`UnreadableImage` from a missing `pictures/` corpus in
  this worktree, unrelated to `image_manager.py` — confirmed identical via
  `git stash`/`git stash pop` around the same sweep). No regressions
  introduced.

**AC verification**:
- AC-1: met — `test_predict_size_zero_dimensions_returns_safe_fallback` and
  the parametrized `size_mode` variant.
- AC-2: met — `test_preview_batch_images_get_survives_degenerate_image`,
  `test_generate_batch_puzzles_get_survives_degenerate_image`,
  `test_preview_batch_images_mixed_batch_all_render`.
- AC-3: met — the branch is removed (not merely made reachable);
  `test_dead_nonogram_error_branch_removed` guards against reintroduction.

**Guardrail verification**:
- G-1: met — `test_predict_size_real_image_unaffected` pins the exact
  pre-existing behaviour (200x100 → predicted (20, 10) at `size_value=20`)
  for a real image; no line inside the ink-bbox/`derive_extent` derivation
  itself was touched, only the exception handling wrapped around the call.

No `.venv` existed in this worktree; created one per the setup command in
`CLAUDE.md` and installed `.[dev,admin,db]` (the `admin`/`db` extras are
needed to import `Flask`/`SQLAlchemy` for `tests/conftest.py` and the
Flask-test-client AC-2 tests) — `.venv/` is gitignored, not committed. Also
reverted incidental `src/nonogram.egg-info/*` changes made by that `pip
install -e` before committing, to keep the commit scoped to the two intended
files.
