# CARD-051: Stop reimplementing clue encoding in admin — call nonogram.clues

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/051-admin-clues-reuse
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-004
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_to_puzzle.py
**Review score:** —
**Started:** —
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
