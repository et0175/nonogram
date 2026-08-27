# CARD-015: Uploaded-image conversion via resize and Floyd-Steinberg dithering

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/015-image-conversion
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-3
**Idea:** —
**Wave:** 9
**Depends on:** CARD-008, CARD-014
**Touches:** src/nonogram/sourcing/image.py, src/nonogram/sourcing/__init__.py, src/nonogram/cli.py, src/nonogram/orchestrator.py, tests/test_sourcing_image.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-003's third and last grid source. The handoff calls this "the last untested technical
risk" — dithering quality is unproven until real images run through it.

1. `sourcing/image.py` — load the user's file with Pillow (ADR-0006), convert to greyscale,
   **resize to exactly the target grid dimensions**, then apply Floyd-Steinberg
   error-diffusion dithering and binarize each cell into the ADR-0012 boundary type.
2. **Aspect ratio (AC-009).** The output grid has exactly the requested dimensions even when
   the source aspect ratio differs. Decide and document the policy in the module docstring
   (stretch vs. letterbox-then-crop) — either is acceptable to the AC, but it must be one
   deliberate choice, tested.
3. **Unreadable input (AC-008).** A missing or corrupt file raises a "cannot read image"
   domain error from `errors.py`; the CLI turns it into a clear message and a non-zero exit.
   Pillow's own exceptions must not leak to the user.
4. Register `image` in `sourcing/__init__.py`'s dispatch table, add `--image <path>` and
   `image` to `--mode`'s choices in `cli.py` (parsing only — the file-readability check is a
   domain concern), and route mode `image` through the orchestrator.
5. Add small fixture images under `tests/fixtures/` — a valid PNG, a non-square PNG, and a
   corrupt file. Keep them tiny; they live in the repo.

**Note on the retry policy:** image mode does **not** use POL-001's regenerate loop — an
uploaded image is fixed and cannot be re-drawn. The recovery path is CARD-016's bounded
pixel nudge. This card must leave the orchestrator's image branch failing cleanly on a
non-unique conversion, not silently regenerating.

## Acceptance criteria

- **AC-007** (happy) — given a valid PNG image and a target size of 25x25, when the image is
  converted, then a 25x25 black/white grid is produced via resize and dithering.
  *test:* `TestConvertImage_ProducesDitheredGrid`
- **AC-008** (negative) — given a path to a non-existent or corrupt image file, when
  conversion is requested, then the request fails with a "cannot read image" error and no
  grid is produced.
  *test:* `TestConvertImage_RejectsUnreadableFile`
- **AC-009** (boundary) — given a source image whose aspect ratio differs from the target
  grid, when the image is converted, then the output grid has exactly the requested target
  dimensions.
  *test:* `TestConvertImage_ProducesExactTargetDimensions`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/random_grid.py`,
  `src/nonogram/sourcing/library.py`, `src/nonogram/solver/**`,
  `src/nonogram/export/**`, `src/nonogram/clues.py`, `src/nonogram/difficulty.py` — image
  sourcing is the last additive module and must revert without touching random/library
  modes, the solver, or export (handoff Increment 3 Rollback)
  (test: TestGenerateRandom_ProducesRequestedSize, TestGenerateLibrary_ProducesCatGrid,
  TestExport_WritesPNG)
- G-2: No new dependency — resize and dithering via Pillow, arithmetic via NumPy
  (ADR-0006). Do not reach for OpenCV, scikit-image or similar
- G-3: Out of scope — no pixel-nudge recovery loop (FR-013, CARD-016) and no nudge-count
  reporting (FR-014, CARD-017). A non-unique conversion fails cleanly here; recovery lands
  in the next card
- G-4: Image mode must not be wired into POL-001's regenerate loop — an uploaded image is
  fixed and is never silently re-drawn (policies.yml POL-002 rationale)
  (test: TestRegenerate_FiresOnUniquenessFailure must remain scoped to random/library mode)
- G-5: `--image` validation stays inward of argparse (ADR-0010) — the file-readability check
  is a domain error, not an argparse `type=`
- G-6: INV-003's retry counter keeps its single home in COMP-002 — do not add a counter to
  `image.py`

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-003
- **NFR:** —
- **ADR:** ADR-0006, ADR-0010, ADR-0012
- **Components:** COMP-003 (Grid Sourcing — image path), COMP-001 (`--image` flag)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
