# CARD-063: One source of truth for the grid size range — a shared `limits` module instead of hardcoded 10/30

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/063-shared-limits-module
**Worktree:** —
**Source:** project owner, 2026-09-11 ("let it be constant, but not using magic numbers everywhere in the code"); whether to allow 40x40 is undecided and NOT part of this card
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/limits.py (new), src/nonogram/sourcing/random_grid.py, src/nonogram/difficulty.py, src/nonogram/admin/app.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/batch_generator.py, src/nonogram/admin/image_manager.py, src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/templates/puzzles_list.html, src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/web/metadata.py, src/nonogram/web/static/metadata.js (+ whatever web page renders it), tests/test_cli.py (`_SHARED`), meta/architecture/decisions/adr/0007-internal-module-architecture.md, meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md (History notes only)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The supported grid range is 10..30 cells per side (ADR-0022). The 30 comes
from printing, not the solver: `docs/cell_size.md` stops at 30 (6.5 mm
cells). The owner may want to revisit it (40x40 is undecided), and whatever
is decided should be a one-line change, not a hunt for literals.

Today the core has constants, but they are not the only source:

- `sourcing/random_grid.py:79-80` defines `MIN_SIZE = 10`, `MAX_SIZE = 30`.
  `admin/image_manager.py` imports them.
- `difficulty.py:256-262` keeps its **own** copy
  (`MIN_SUPPORTED_CELLS = 10 * 10`, `MAX_SUPPORTED_CELLS = 30 * 30`). This is
  on purpose: ADR-0007 forbids one capability module importing another, so
  it cannot reach `random_grid`. A shared constant for the core therefore
  needs a home every layer may import — the same kind of innermost shared
  module `errors.py` already is.
- Range checks and form bounds written as literals (grep of 2026-09-11):
  - `admin/puzzle_review.py:308-309` — `10 <= width <= 30 and 10 <= height <= 30`
  - `admin/batch_generator.py:194-195` — `10 <= s <= 30` for batch sizes
  - `admin/image_manager.py:508` — `10 <= size_value <= 30` in
    `update_image_size()` (left literal by CARD-061)
  - `admin/templates/image_preview.html:35-36, 88-90` — `min="10" max="30"`
    and the "10-30" labels
  - `admin/templates/puzzles_list.html:60` and
    `admin/templates/book_select_puzzles.html:30` — size filter inputs
  - `web/static/metadata.js:97` — `suggestDimensions(metadata, minSize = 10,
    maxSize = 30)`; `web/metadata.py:4` states the range in prose

## What to implement

1. **New `src/nonogram/limits.py`**, import-free like `errors.py`:
   `MIN_SIZE = 10`, `MAX_SIZE = 30`, with a comment summarising why (ADR-0022:
   the print constraint). `sourcing/random_grid.py` re-exports them
   (`from nonogram.limits import MAX_SIZE, MIN_SIZE`) so every existing import
   of `random_grid.MIN_SIZE`/`MAX_SIZE` and its `__all__` keep working.
2. **Import guard** (`tests/test_cli.py`): add `limits` to `_SHARED` next to
   `errors`, so every layer may import it and it may import nothing back.
   Add a forbidden-edge case `limits -> capability` alongside the existing
   `errors-reaches-back` one. If `_SHARED` is not pinned by a literal test,
   pin it the way `_ADAPTERS` is pinned
   (`test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`): a
   shared layer that grows quietly is how the layering erodes.
3. **`difficulty.py`**: derive `MIN_SUPPORTED_CELLS`/`MAX_SUPPORTED_CELLS`
   from `limits` (`MIN_SIZE ** 2`, `MAX_SIZE ** 2`) instead of literals.
4. **Admin**: replace the literal checks in `puzzle_review.py`,
   `batch_generator.py` and `image_manager.py` with the constants. The admin
   panel is outside the core pipeline, so it may import `limits` directly.
   For templates, register `MIN_SIZE`/`MAX_SIZE` as Jinja globals in
   `create_app()` and use them in the `min`/`max` attributes and "10-30"
   labels.
5. **Web**: `metadata.js` cannot import Python, so the page should hand it
   the bounds: data attributes rendered by the server, or fields in the
   metadata response, whichever the page already uses. Remove the `10`/`30`
   default-parameter literals. `web/metadata.py` uses the constants wherever
   it actually computes with the range.
6. **ADR History notes, no decision change**:
   - ADR-0007: `limits` joins `errors` as the innermost shared layer
     (constants only, imports nothing).
   - ADR-0022: the range now lives in `nonogram.limits`; the values are
     unchanged.

## Out of scope (deliberately)

- **Changing the range.** Whether to allow 40x40 is a separate owner decision
  and an ADR-0022 revision. This card only makes that a one-line change
  later.
- **The admin presets** (`app.py` `size_mapping`: small = 10 on the short
  side, medium 20, large 30) are product choices, not range bounds. Keep them
  literal. Whether "large" should follow a raised maximum is for the owner to
  decide when the range changes.
- **`generation/random_generator.py`**: orphaned package, and CARD-053
  decides whether to remove it.
- **`export/layout.py:197`** (the `(30, 6.5)` cell-size row): this is print
  data keyed by grid size, not a bound. See AC-4 for the guard that keeps it
  honest.
- **`book_setup_print.html:49,60`** (`min="10" max="30"/"48"`): centimetres
  of book trim size, not grid cells.
- **Prose** that states "10..30" in docstrings and comments. Update only
  where a docstring describes a check this card changes.

## Acceptance criteria

- **AC-1** — repeating the 2026-09-11 grep for literal range checks and
  form bounds in `src/` finds only `limits.py`, the out-of-scope items above,
  and prose.
- **AC-2** — every enforced bound follows `limits`. Tests assert that
  `random_grid.MAX_SIZE is limits.MAX_SIZE`, that `difficulty`'s cell bounds
  equal `limits.MAX_SIZE ** 2`/`MIN_SIZE ** 2`, that each admin validator
  accepts `MAX_SIZE` and rejects `MAX_SIZE + 1` (and likewise at `MIN_SIZE`),
  and that the rendered admin pages' `min`/`max` attributes and the web
  page's bounds equal the constants.
- **AC-3** — the import guard passes with `limits` in the shared rank, and a
  fabricated `limits -> capability` import is rejected.
- **AC-4** — a new test asserts the export layout's cell-size table covers
  every grid side up to `MAX_SIZE`. A future raise then fails loudly until
  the print table is extended, instead of silently printing unmeasured cell
  sizes.
- **AC-5** — no behaviour change: the full suite matches `main`'s baseline
  (the known pre-existing failures only), and the admin and web pages
  still show 10..30.

## Guardrails

- G-1: Pure refactor. The range stays 10..30 and no preset value changes.
- G-2: `limits.py` imports nothing — not from `nonogram`, not from third
  parties.
- G-3: Do not touch `generation/` (CARD-053), the book trim-size inputs, or
  the print cell-size data values.
- G-4: Do not weaken the import guard. `limits` enters the shared rank by an
  explicit, pinned edit; the ranking rule is not loosened.
