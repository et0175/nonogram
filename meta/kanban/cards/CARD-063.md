# CARD-063: One source of truth for the grid size range — a shared `limits` module instead of hardcoded 10/30

**Status:** done
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
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-11T17:35:12Z
**Closed:** 2026-09-11T18:18:00Z
**Actual:** 0.03d
**Merge commit:** 0a77655
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

## Worktree notes

[Env] forge 2026.8.17 (no `meta/.skills.yml`, so no min_version comparison).

**Implementation.**
- **New `src/nonogram/limits.py`**: `MIN_SIZE = 10` and `MAX_SIZE = 30`, the
  ADR-0022 reasoning in a comment, and no imports. `sourcing/random_grid.py`
  imports and re-exports both names (its `__all__` is unchanged), and its own
  definitions are gone. `difficulty.py` computes `MIN_SUPPORTED_CELLS` and
  `MAX_SUPPORTED_CELLS` as `MIN_SIZE * MIN_SIZE` and `MAX_SIZE * MAX_SIZE`.
- **Admin**: `puzzle_review.py` (filter size check), `batch_generator.py`
  (batch sizes; the separate *count* check `10 <= count <= 200` is not a grid
  size and stays) and `image_manager.py` (`update_image_size`) import the
  constants. `create_app()` registers both as Jinja globals, so
  `image_preview.html`, `puzzles_list.html` and `book_select_puzzles.html`
  use `{{ MIN_SIZE }}`/`{{ MAX_SIZE }}` for `min`/`max`, placeholders and
  labels. One label also changed wording: "10-30 pixels" is now "… cells",
  since the value was always cells.
- **Web**: `metadata.py`'s `suggest_dimensions` defaults come from `limits`.
  For the browser side, both form pages render
  `data-min-size="{MIN_SIZE:d}" data-max-size="{MAX_SIZE:d}"` onto the
  `metadata.js` `<script>` tag, and the script reads its own tag once, while
  loading (`document.currentScript`). `suggestDimensions` no longer has
  `10`/`30` defaults.
  - Why the script tag and not the suggestions `<div>`: a test pins that
    div's exact opening tag (`test_web_metadata.py:178`).
  - Why `:d`: it is the same safety argument `pages.py` already makes for
    `{seed:d}`, an int-only format spec.

**Guard (AC-3)**: `_SHARED = {"errors", "limits"}`, pinned literally by a
new `test_the_shared_layer_is_closed_at_errors_and_limits`. New
forbidden-edge cases `limits-reaches-back` (limits → capability) and
`limits-to-errors` (shared → shared, so `limits` stays import-free). The
legitimate-edges test gains capability → `limits` and adapter → `limits`.
`limits` is added to the walk's sanity set.

**SCOPE+**, beyond the predicted Touches, each forced by an existing pin:
- `pages.py` docstring and `tests/test_web_server.py`'s escaping-rule
  class: the interpolation counts 49/19/30 → 53/19/34, a fifth kind in the
  docstring, and `MIN_SIZE`/`MAX_SIZE` in `_UNESCAPED_PAGE_INTERPOLATIONS`.
- `web/__init__.py` docstring and
  `test_the_package_imports_exactly_what_the_docstring_names`: the web
  package now imports `limits`.
- `CLAUDE.md`: "their only shared dependency is `errors.py`" would have
  become false.

**Evidence so far.**
- **AC-1**: the literal grep for range checks and form bounds in `src/`
  finds only out-of-scope items: the batch *count* check, the book
  trim-size inputs (cm), and `generation/random_generator.py` (CARD-053).
- **Red check**: against `main`'s `src/` the new test file cannot even
  import `nonogram.limits`.
- **Targeted suites**: 392 passed. That is the new file plus `test_cli`,
  `test_web_server`, `test_web_metadata`, `test_puzzle_review`,
  `test_batch_generator`, the CARD-058/061/062 tests and
  `test_image_batch_size_fix`.
- **Validators**: `system_rules.py --verify-refs` has no dead refs;
  `validate.py --phase all` gives 0 errors and the 2 old warnings.
- **Full-suite comparison (AC-5)**, the branch against a clean export of
  `main` (`f7c5692`): 40 failed, 2724 passed on the branch; 40 failed, 2698
  passed on `main`. The +26 passes are exactly this card's new tests. Only
  two tests differ:
  - failing only on the branch:
    `test_the_package_imports_exactly_what_the_docstring_names`. The run
    started before its fix, and it passes in the later targeted run (392
    passed);
  - failing only on `main`: the flaky async
    `test_wave2_async_generation.py::TestBookManagement::test_create_book_with_approved_puzzles`.

  No new failures.

[Review 1/3] Score: 8.5 — crit: 0, imp: 0, minor: 4
[Review sync] 1 report(s) → meta/review/ (20260911T175925Z-CARD-063-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review, independent agent): AC-1..AC-5 and G-1..G-4
all held. The reviewer's own evidence:
- rendered all three admin pages and both web pages on base and branch:
  10 and 30 everywhere;
- removing `limits` from `_SHARED` fails 4 tests;
- `MAX_SIZE = 40` fails the print-table test;
- giving `limits.py` an import fails the guard and the AST test;
- full suite on clean exports: base 40 failed, branch 38, no branch-only
  failure;
- `:d` spec and `document.currentScript` placement judged safe.
Minors:
- F-001: `metadata.js` has no fallback if the bounds are missing;
- F-002: the template test read source text only, so a bound wired to the
  wrong constant would pass;
- F-003: the `metadata.js` wiring is untested by execution;
- F-004: a stale "43/16/27" docstring above the escaping-count asserts.
Out of scope: "Size (px)" labels on the two filter templates; redundant
function-local `random_grid` imports in `image_manager.py`; difficulty
bands in `image_to_puzzle.py` that stop at 30. Severity gate OPEN.

[Fix delta after cycle 1]
- F-002 fixed: rendered-page tests for the image-preview page, the puzzle
  list filter and the book puzzle filter. Each parses the rendered size
  `<input>` and asserts its `min`/`max`/placeholder values, so a
  wrong-constant binding fails. The source check stays alongside: it catches
  a reintroduced literal that happens to render correctly.
- F-004 fixed: the docstring now reads 53/19/34.
- Delta commit `dc64456`; targeted suites 395 passed. Mutation check in a
  scratch copy: the per-image input in `image_preview.html` set to
  `max="{{ MIN_SIZE }}"` makes `test_the_image_preview_page_renders_the_range`
  fail with `('10', '10') == ('10', '30')`; restoring the template makes it
  pass again.

[Review 2/3] Score: 9.0 — crit: 0, imp: 0, minor: 3 (confirmation mode, delta d2ed15d..dc64456)
[Review sync] 1 report(s) → meta/review/ (20260911T181558Z-CARD-063-cycle2.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 2 summary: pure confirmation. Re-verified AC-2, AC-4 and AC-5.
Carried AC-1, AC-3 and G-1..G-4, since the delta touches test files only.
- Wrong-constant check: the rendered tests catch min, max and placeholder
  on the puzzle-list and book filters, and both inputs plus the "cells"
  label on the image preview. 13 of 14 template mutations fail.
- Full suite: base 39 failed, branch 41. The 3 branch-only failures are
  pre-existing flaky tests (see the spot-check).
Minors:
- F-005 (new): the "apply to all" hint label at `image_preview.html:36`
  is not asserted.
- F-001 and F-003: acceptance judged reasonable. The reviewer notes the
  suggested F-001 fix was a console message, which would need no literals.
All three recorded, not fixed; a fix would need a cycle 3. Severity gate
OPEN. Cleared on cycle 2 of 3.

[8h spot-check] 1/1 sampled hold reproduced independently — the
"branch-only failures are pre-existing flakes" claim. Run alone,
`tests/test_batch_history.py` fails on both trees with different subsets
each run: 5 failed on the branch, 6 on `main`.

[AC/EC check] All criteria/guardrails ✓ (evidence):
AC-1 ✓ demonstrated — grep in `src/`: only out-of-scope hits remain (batch count, trim-size cm, `generation/`, presets, layout table, prose).
AC-2 ✓ demonstrated — AST single-definition test; validators at MIN/MAX±1; rendered pages assert min/max/placeholder; 13/14 template mutations caught.
AC-3 ✓ demonstrated — `_SHARED` pinned; removing `limits` fails 4 tests; `limits → capability` and `limits → errors` rejected.
AC-4 ✓ demonstrated — `MAX_SIZE = 40` fails the print-table test (both reviewers).
AC-5 ✓ demonstrated — full suite: no branch-only failure attributable to the card, on three independent runs.
G-1..G-4 ✓ demonstrated — values and messages unchanged; `limits.py` import-free; out-of-scope files untouched; guard rule unchanged, `_SHARED` pinned.

[Commit] 2 commits on the branch: d2ed15d (implementation + tests),
dc64456 (cycle-1 test fixes).
- F-001 accepted: both pages always render the attributes, and a fallback
  would mean writing 10/30 into the JS again, which is what this card
  removes.
- F-003 accepted: the project has no JavaScript test runner (the dependency
  baseline is closed), so executing `metadata.js` in a test is out of scope
  for this card.
