# CARD-051: Stop reimplementing clue encoding in admin — call nonogram.clues

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/051-admin-clues-reuse
**Worktree:** ../PythonProject4-CARD-051
**Source:** meta/review/20260910T170025Z.yml#F-004
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_to_puzzle.py
**Review score:** —
**Started:** 2026-09-11T11:30:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`src/nonogram/admin/image_to_puzzle.py`'s `generate_clues()` (lines 79-114)
reimplements run-length clue encoding locally (its own `encode_line` at
lines 91-103) instead of calling `nonogram.clues.compute_clues()`/`encode_line()`
— which admin already imports and calls correctly elsewhere:
`app.py:1295-1296` does `clues.encode_line(row)` for a different code path. So
admin is internally inconsistent about whether to reuse the canonical encoder or
duplicate it.

Two concrete divergences from `src/nonogram/clues.py:64-103`:
1. Admin's version returns `list`s (`clues if clues else [0]`), not the
   ADR-0012 boundary `tuple`s `nonogram.clues.encode_line`/`compute_clues`
   return.
2. Admin's version has no equivalent of `compute_clues`'s
   `zip(*grid, strict=True)` ragged-grid guard. The canonical module's own
   docstring explains why that check exists: a ragged grid is a programming
   error that would otherwise silently produce clues disagreeing with the grid
   (violating INV-001 without anything failing). Admin's version
   (`for j in range(width): column = [grid[i][j] for i in range(height)]`,
   lines 109-111) would raise an uncontrolled `IndexError` on an actually
   ragged grid instead of the canonical module's explicit, named error.

1. Replace `generate_clues()`'s body with a call to
   `nonogram.clues.compute_clues(grid)`.
2. Convert the returned `Clues` namedtuple's `rows`/`columns` tuples to lists at
   the call site **only if** `create_puzzle_from_image`'s callers specifically
   need list-typed clues — check whether `puzzle_review.add_puzzle`'s storage
   layer (in-memory dict vs. DB JSON column) cares about tuple vs. list before
   adding an unnecessary conversion step.
3. Remove the now-dead local `encode_line` helper.

## Acceptance criteria

- **AC-1** — given any grid `create_puzzle_from_image` produces, when clues are
  computed, then the result is byte-for-byte identical to what
  `nonogram.clues.compute_clues` would produce for the same grid (trivially
  true once it's the same call, but worth a test pinning it against the old
  behavior for the corpus of real silhouette images this project already has
  under `silhouette/`).
  *test:* to be named by the implementer.
- **AC-2** — given a ragged grid (rows of unequal length) reaches
  `generate_clues`, when it's processed, then a clear, named error is raised
  (matching `nonogram.clues.compute_clues`'s behavior) rather than an
  uncontrolled `IndexError`.
  *test:* to be named by the implementer.

## Guardrails

- G-1: `src/nonogram/admin/image_to_puzzle.py`'s `create_puzzle_from_image` is
  CARD-049's territory for its solver-verification fix — this card should touch
  only `generate_clues` and its local helper, to minimize overlap if both cards
  run in the same wave.

## Worktree notes

**Implementation:** `image_to_puzzle.generate_clues()` now delegates
directly to `nonogram.clues.compute_clues(grid)`, returning its
`rows`/`columns` ADR-0012 boundary tuples unchanged. The local `encode_line`
helper is removed entirely.

**List-vs-tuple call-site question (step 2 of the card) resolved:** traced
`create_puzzle_from_image`'s only two callers (`app.py`'s
`/api/puzzle-grid/<file_id>` and its `/download` variant — both SVG-preview
routes per CARD-049's finding that real batch generation moved to
`app.py`'s `generate_batch_puzzles` and no longer calls this helper at all).
Both callers read only `puzzle_data["grid"]` for SVG rendering; neither
touches `clues_rows`/`clues_cols`. No downstream consumer cares about
tuple vs. list, so no conversion was added at the call site — returning the
canonical module's own tuples directly is the simplest correct choice.

**Tests:** new `tests/test_card_051_admin_clues_reuse.py` (8 tests):
AC-1 — a synthetic grid, an all-empty grid, and three real fixture images
(`tests/fixtures/bird1.jpg`, `dolphin1.jpg`, `dove1.jpg`, run through
`image_to_grid`) all produce clues identical to both
`nonogram.clues.compute_clues` directly and an independent inline
reimplementation of the exact pre-fix `encode_line` logic (pinning
old-vs-new behavior equivalence), plus an integration test that
`create_puzzle_from_image`'s stored `clues_rows`/`clues_cols` match
`compute_clues` for the grid it also returns. AC-2 — a ragged grid raises
`ValueError` (not `IndexError`), and the error type matches what
`compute_clues` itself raises for the same input.

Red→green verified via `git stash`: all 8 new tests fail against the
pre-fix code, including AC-2 reproducing the exact `IndexError` the card
describes (`list index out of range` at the old `column = [grid[i][j] ...]`
line).

**Regression check:** `test_card_051_admin_clues_reuse.py` +
`test_clues.py` + `test_admin_image_uniqueness.py` +
`test_card_050_quality_recognizability.py` +
`test_cli.py::test_every_import_in_the_package_points_inward` — 406/406
pass. Full suite: 42 failures, all in `test_sourcing_image.py`/
`test_derive_shape.py`/`test_nudge.py`/`test_nudge_reporting.py` (pictures/
corpus not present in this worktree) and `test_batch_history.py`/
`test_wave1_e2e.py`/`test_wave2_async_generation.py`/`test_web_upload.py`
(DB/timing-dependent, previously documented as flaky) — none touching
`image_to_puzzle.py` or clue encoding, consistent with the pre-existing
39-42 failure baseline documented on CARD-050.
