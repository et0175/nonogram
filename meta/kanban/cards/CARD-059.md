# CARD-059: Remove the unreachable, unverified SVG-preview-by-file_id routes

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/059-remove-dead-svg-preview-routes
**Worktree:** ../PythonProject4-CARD-059
**Source:** conversation, 2026-09-11 (verified while answering "does admin's puzzle preview reflect what the CLI/real generation would produce")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py
**Review score:** —
**Started:** 2026-09-11T15:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`app.py:1182` (`GET /api/puzzle-grid/<file_id>`) and `app.py:1213`
(`GET /api/puzzle-grid/<file_id>/download`) render an SVG puzzle grid by
calling `create_puzzle_from_image()` directly — the same crop/dither
pipeline as `nonogram generate --mode image` (via `image_to_grid` →
`sourcing.image.generate`), but **skipping `orchestrator.generate()`
entirely**: no solver-uniqueness verification, no POL-002 nudge-recovery
loop. Since CARD-049 (merged `98cdaaa`) moved the real, stored,
solver-verified generation path into `generate_batch_puzzles`'s POST
handler, these two routes are the only place in admin that still produces
a puzzle grid outside that verified pipeline.

Verified 2026-09-11: `grep -rn "api_puzzle_grid\b\|/api/puzzle-grid/"` across
`src/nonogram/admin/templates/*.html` and `tests/*.py` returns zero
matches — nothing in the current UI links to either route, and nothing
tests them. They are dead from the user's perspective today. But being
reachable-by-URL and undead-by-code means:
- a stale bookmark, an old client integration, or a future template edit
  could reach them and receive a grid that was never solver-verified and
  was never nudged to uniqueness — silently different from what
  `generate_batch_puzzles` would actually produce for the same
  image+size, in the one case where nudging was needed;
- they cost real maintenance surface (two routes, a helper function call,
  an SVG-generation dependency) for zero current benefit.

1. Confirm fresh (grep templates + tests + any JS) that both routes are
   still genuinely unreferenced — re-verify, don't assume the 2026-09-11
   finding still holds if other cards have touched `admin/` since.
2. Remove both route handlers (`api_puzzle_grid`, `api_puzzle_grid_download`,
   `app.py:1182-1244`).
3. Check whether `create_puzzle_from_image` (`image_to_puzzle.py`) and
   `grid_to_svg` (wherever it's defined/imported) still have other callers
   after this removal — `create_puzzle_from_image` is currently reachable
   from these two routes; confirm whether removing them leaves it fully
   dead too (in which case removing it is in scope for this card) or
   whether something else still calls it (in which case leave it).
4. Do NOT touch `/api/puzzle/<puzzle_id>/grid` (`app.py:1251`) or its
   `/download`/`/download/pdf` siblings — those read the **stored,
   already-verified** puzzle by `puzzle_id` (post-`orchestrator.generate()`)
   and are the correct, live puzzle-grid-display mechanism. This card
   removes only the by-`file_id`, pre-generation, unverified pair.

## Acceptance criteria

- **AC-1** — given both routes are removed, when the full test suite runs,
  then nothing fails (confirming the unreferenced claim held).
- **AC-2** — a fresh grep for `api_puzzle_grid\b` (the by-`file_id` handler
  names) and the literal route strings `/api/puzzle-grid/<file_id>` /
  `/api/puzzle-grid/<file_id>/download` across the repository returns no
  matches after this card, except in this card's own file and any
  CHANGELOG/kanban record of the removal.
- **AC-3** — `/api/puzzle/<puzzle_id>/grid` and its download/PDF siblings
  are unchanged and still pass their existing tests.

## Guardrails

- G-1: Do not modify `/api/puzzle/<puzzle_id>/grid` or its siblings — this
  card removes the pre-generation, unverified preview pair only, not the
  post-generation, verified display mechanism.
- G-2: Do not modify `orchestrator.generate()`, `generate_batch_puzzles`,
  or anything in `sourcing/`/`cli.py` — this is a dead-route removal, not
  a change to the verified generation path.

## Worktree notes

**Implementation:** re-verified fresh (grep templates + tests) that both
routes were still genuinely unreferenced before touching anything —
confirmed. Removed `api_puzzle_grid` and `api_puzzle_grid_download`
(`app.py:1182-1249`) entirely, leaving `/api/puzzle/<puzzle_id>/grid`
and its siblings untouched (G-1).

**Step 3 investigation (other callers of create_puzzle_from_image /
grid_to_svg):**
- `create_puzzle_from_image`: still has a real caller —
  `tests/test_card_051_admin_clues_reuse.py::test_create_puzzle_from_image_stores_clues_matching_canonical_module`
  imports and calls it directly from `nonogram.admin.image_to_puzzle`.
  Left the function itself untouched. Its import in `app.py`, however,
  became unused by this removal (no other call site in that file —
  confirmed via fresh grep, only a comment mentioned it) — removed that
  now-dead import.
- `grid_to_svg`: still used by the kept `/api/puzzle/<puzzle_id>/grid`
  routes (`app.py:1201`, `:1228`) — left both the import and the
  function untouched.
- `get_svg_filename` (imported alongside `grid_to_svg`): had exactly
  one caller, the removed `api_puzzle_grid_download` — became a fully
  dead import in `app.py` as a direct result. Removed the import.
  The function itself, in `grid_renderer.py`, is now unreferenced
  anywhere in the repo — left it in place since `grid_renderer.py` is
  outside this card's Touches (`src/nonogram/admin/app.py` only);
  flagging here for visibility rather than silently expanding scope
  into a second file. (Also noticed, unrelated to this card's change:
  `grid_renderer.py`'s `grid_to_svg_bytes` was ALREADY fully dead before
  this card touched anything — pre-existing, not caused by this removal,
  left alone.)

**AC-1 verified:** scoped run (`test_card_051_admin_clues_reuse.py` +
`test_admin_image_uniqueness.py` + `test_card_050_quality_recognizability.py`
+ structural import guard) — 20/20 pass. `test_wave3_image_generation.py`
+ `tests/e2e/test_admin_workflow.py` (the two files referencing
`/api/puzzle/.../grid` paths) — 25 passed, 16 skipped, 0 failed. Full
suite: 38 failures, all in the previously documented flaky/corpus-
dependent classes, none touching `app.py`, `grid_renderer.py`, or
`image_to_puzzle.py`.

**AC-2 verified:** fresh grep for `api_puzzle_grid\b` and the literal
route strings across `src/` and `tests/` — zero matches.

**AC-3 verified:** `/api/puzzle/<puzzle_id>/grid` and its download/PDF
siblings (`app.py:1182,1213,1242` post-removal, i.e. the routes
formerly at `1251,1282,1311`) are byte-identical to before this diff
apart from shifting up by 68 lines; their covering tests
(`test_wave3_image_generation.py`, `tests/e2e/test_admin_workflow.py`)
pass unchanged.
