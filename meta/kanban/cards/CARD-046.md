# CARD-046: Regression test for ink-bbox-vs-file-dimensions sizing fix

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/046-source-shape-regression-test
**Worktree:** —
**Source:** meta/review/20260910T164426Z.yml#F-004
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** tests/test_wave3_e2e.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The bug `ec18fb4` fixed (a heron's feet/beak, a bird's legs silently cropped
away in the admin panel but not in `nonogram serve`) was caused by
`ImageFile.predict_size()` deriving the target grid extent from the raw file's
pixel dimensions instead of the picture's **ink bounding box** (the new
`_source_shape()`, `src/nonogram/admin/image_manager.py:42-65`).

Every test image in the current suite (`tests/test_wave3_e2e.py:18,23,28`,
`tests/test_image_batch_size_fix.py:33,190,234,265,298`) is a solid
`PILImage.new(..., color=X)` rectangle with **zero blank margin** — for these,
`ink_bounding_box` always returns the whole extent, so `_source_shape()` returns
exactly `self.dimensions` and is indistinguishable from the reverted (buggy)
behavior in every test that runs today. `tests/integration_tests.py` exercises
`image_to_grid` against real `silhouette/animals/birds/*.jpg` files but only
asserts grid shape (`len(grid) == target_height`), never content retention.

**No test in the repository would fail if `_source_shape()` were changed back to
`return self.dimensions` unconditionally.** The exact regression this diff fixed
has no regression test.

1. Build a test image with a real drawn shape plus blank margin — e.g. use
   `PIL.ImageDraw` to fill a rectangle covering roughly 70% of a canvas that is
   otherwise white, on a canvas taller (or wider) than the drawn shape, so the
   canvas's own aspect ratio genuinely differs from the drawn content's.
2. Assert `ImageFile.predict_size()`'s returned aspect ratio tracks the **drawn
   content's** ratio, not the canvas's — this is the property the fix
   established and the property a regression would break.
3. Optionally, add the same style of assertion directly against
   `nonogram.sourcing.image.source_shape()` vs. the file's raw `Image.open(...).size`
   on the same constructed image, to pin the lower-level primitive too.

## Acceptance criteria

- **AC-1** — given an image whose drawn content's aspect ratio differs from its
  canvas's aspect ratio (blank margin present), when `predict_size()` is called
  in `"fixed"` mode, then the returned `(width, height)` ratio matches the drawn
  content's ratio (within rounding), not the canvas's.
  *test:* to be named by the implementer.
- **AC-2** — the added test fails against a reverted `_source_shape()` that
  returns `self.dimensions` unconditionally (verify manually while writing it,
  as the review's own mutation-check discipline would).

## Engineering constraints

None beyond the general property this pins — no new production code is
expected for this card unless AC-1 surfaces a real gap.
