# CARD-046: Regression test for ink-bbox-vs-file-dimensions sizing fix

**Status:** done
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
**Review score:** 9.5 (cycle 1/3)
**Started:** 2026-09-11T12:15:00Z
**Closed:** 2026-09-11T12:35:00Z
**Actual:** 0.04d
**Merge commit:** 261706a
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

## Worktree notes

**Implementation:** Added two tests to `tests/test_wave3_e2e.py`
(`TestWave3ImageGeneration`), following the existing class/fixture style.
No production code change — the fix (`ImageFile._source_shape()`,
`ec18fb4`) was already correct; only the missing regression test was
added, per the card's Engineering constraints.

**Fixture design:** every pre-existing test image in this suite is a
solid, borderless `PILImage.new(...)` rectangle, for which
`ink_bounding_box` always equals the whole canvas — none of them can tell
the fix apart from the bug it replaced. The new fixture draws an 81x81
black square (via `ImageDraw.rectangle`) with real blank white margin on
a 300x100 landscape canvas, so the canvas's own aspect ratio (3:1) is
deliberately different from the drawn content's (1:1).

- `test_predict_size_follows_ink_bounding_box_not_canvas_dimensions`
  (AC-1): `ImageFile.predict_size()` in default "fixed" mode
  (`size_value=20`) must return `(20, 20)` — following the square ink
  box — not a landscape-shaped size derived from the 300x100 file.
- `test_source_shape_primitive_ignores_blank_canvas_margin` (step 3,
  optional lower-level pin): `nonogram.sourcing.image.source_shape()`
  on the same constructed image returns `(81, 81)`, not
  `Image.open(...).size` (`(300, 100)`).

**AC-2 verified manually** (per the card's own instruction, mirroring the
review's mutation-check discipline): temporarily replaced
`ImageFile._source_shape()`'s body with `return self.dimensions`
unconditionally (the exact reverted behavior `ec18fb4` fixed), reran the
new tests — `test_predict_size_follows_ink_bounding_box_not_canvas_dimensions`
failed (`(20, 10) != (20, 20)`, reproducing a version of the original
crop-the-content bug), confirming the test is a real regression guard, not
tautological. The lower-level primitive test correctly stayed green (it
exercises `nonogram.sourcing.image.source_shape()` directly, which the
`ImageFile`-level revert doesn't touch — by design, since it pins a
different layer). Restored the fix; both tests pass.

**Regression check:** `test_wave3_e2e.py` — 18/18 (14 pass + 4 pre-existing
skips, unchanged). `test_wave3_e2e.py` + `test_image_batch_size_fix.py` +
`test_admin_image_uniqueness.py` +
`test_cli.py::test_every_import_in_the_package_points_inward` — 35/35,
4 skips. Full suite: 39 failures, all in the previously documented flaky/
corpus-dependent classes (`test_sourcing_image.py`/`test_derive_shape.py`/
`test_nudge.py`/`test_nudge_reporting.py`/`test_export_pdf.py` — pictures/
corpus and packaging-environment dependent; `test_batch_history.py`/
`test_wave1_e2e.py`/`test_wave2_async_generation.py`/`test_web_upload.py`/
`property/test_grid_dimensions.py` — DB/timing-dependent) — none touching
`test_wave3_e2e.py` or `image_manager.py`.

## System contract

- ADR-0022/R4 — predict_size() follows the picture's own ink bounding box, never the raw file's canvas dimensions. (check: test, ref TestWave3ImageGeneration::test_predict_size_follows_ink_bounding_box_not_canvas_dimensions)
- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy + ReportLab. (check: test, ref TestDependencyBaseline_IsExactlyPillowAndNumpy)

[Review 1/3] Score: 9.5 — crit: 0, imp: 0
[Review sync] 1 report(s) → meta/review/ (20260911T104433Z-CARD-046-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review): test-only diff, zero production code
touched (matches the card's Engineering constraints). AC-1 independently
recomputed by the reviewer (derive_extent(20, 81, 81) → (20, 20)).
AC-2 independently re-verified — not just trusted from the Worktree notes
— by the reviewer's own separate mutation of _source_shape() to
`return self.dimensions`, reproducing the exact (20, 10) failure and
confirming a clean restore afterward. No duplicate coverage found in
test_image_batch_size_fix.py/test_admin_image_uniqueness.py. Zero
Critical/Important; 1 Minor (cosmetic canvas-construction duplication
between the two new tests, not worth a fix cycle on a 0.25d card,
optional follow-up only). Risk: LOW, lane: FAST. Score 9.5 ≥ min_score 8
— severity gate OPEN. Cleared on cycle 1 of 3.

[8h spot-check] 1/1 sampled holds reproduced — independently re-ran both
new tests fresh (2/2 pass) and re-confirmed the diff still touches only
tests/test_wave3_e2e.py (62 insertions, 0 production lines).

[AC/EC check] All criteria ✓ (evidence):
AC-1 ✓ demonstrated — evidence: test_predict_size_follows_ink_bounding_box_not_canvas_dimensions passes; math independently recomputed by two independent parties (implementer and reviewer) to (20, 20).
AC-2 ✓ demonstrated — evidence: manual mutation of _source_shape() to `return self.dimensions` reproduced twice independently (implementer, then reviewer) — both times the test failed with (20, 10) != (20, 20), reproducing the original bug; restored cleanly both times.

Both items independently re-verified against the final one-cycle state.
Gate passes. No engineering constraints beyond the pinned property (per
the card itself); none violated.

[Docs] No README under tests/ or src/nonogram/admin/ carries a per-file
test inventory that would need updating for this diff.

[Commit] Final state is 1 commit on the branch: 18de0a7 (test addition).
Nothing further needed — cycle 1 cleared cleanly.

CYCLE 1 COMPLETE — SUCCESS. Ready for `/kanban done CARD-046`.
