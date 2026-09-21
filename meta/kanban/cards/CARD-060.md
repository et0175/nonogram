# CARD-060: Remove dead code in grid_renderer.py — grid_to_svg_bytes and get_svg_filename

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** n/a — a deletion; the guard is a test that the names stay gone
**Branch:** card/060-remove-dead-grid-renderer-helpers
**Worktree:** ../PythonProject4-CARD-060
**Source:** CARD-059 cycle 1 review (Minor finding) — meta/review/20260911T123052Z-CARD-059-cycle1.yml
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/grid_renderer.py, tests
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.25d
**Merge commit:** —
**Blocked by:** —

## What to implement

`src/nonogram/admin/grid_renderer.py` has two functions with zero callers
anywhere in the repository, confirmed 2026-09-11 during CARD-059:

- `get_svg_filename` (line 74) — became fully dead as a **direct
  consequence** of CARD-059 removing `api_puzzle_grid_download`, its only
  caller. Left in place by CARD-059 deliberately, since that card's
  `Touches` was `src/nonogram/admin/app.py` only and cleaning up a second
  file would have been undisclosed scope creep.
- `grid_to_svg_bytes` (line 57) — was **already** fully dead before
  CARD-059 touched anything; an unrelated, pre-existing case, noticed
  in passing during the same investigation.

`grid_to_svg` itself (line 7) is NOT dead — it is still used by the live,
verified `/api/puzzle/<puzzle_id>/grid` routes and their download/PDF
siblings in `app.py`. Do not touch it.

1. Confirm fresh (grep `src/` and `tests/`, re-verify — don't assume the
   2026-09-11 finding still holds if anything has touched `admin/` since)
   that both `get_svg_filename` and `grid_to_svg_bytes` still have zero
   callers.
2. Remove both functions from `grid_renderer.py`.
3. Check whether removing them leaves any now-unused imports in
   `grid_renderer.py` itself (e.g. if either function was the only user
   of some import).

## Acceptance criteria

- **AC-1** — given both functions are removed, when the full test suite
  runs, then nothing fails (confirming the zero-callers claim held).
- **AC-2** — a fresh grep for `grid_to_svg_bytes` and `get_svg_filename`
  across the repository returns no matches after this card, except in
  this card's own file and any CHANGELOG/kanban record of the removal.
- **AC-3** — `grid_to_svg` (the one function in this module that IS
  used) is unchanged and its existing callers/tests are unaffected.

## Guardrails

- G-1: Do not touch `grid_to_svg` — it has real, live callers
  (`/api/puzzle/<puzzle_id>/grid` and siblings in `app.py`) and is out of
  this card's scope.
- G-2: Do not touch `src/nonogram/admin/app.py` — that file's dead-route
  cleanup was CARD-059's territory and is already done.

### Delivered 2026-09-21

**Re-confirmed before deleting** (step 1), on `main` at `7edf1d3`: a grep
across `src/`, `tests/` and the templates finds `grid_to_svg_bytes` and
`get_svg_filename` only at their own definitions, and in this card's and
CARD-059's notes. The 2026-09-11 finding still held.

**Both functions removed.** `grid_to_svg` is untouched (G-1), and `app.py` was
not opened at all (G-2).

**Two imports went with them** (step 3) — and neither was made dead by this
card: `BytesIO` was never referenced by any function in the module, and
`Tuple` by none either. They were already unused on the day the card was
written; the card asked to check, so they are reported rather than quietly
swept up.

**AC-2 is a test, not a grep.** `tests/test_card_060_grid_renderer_surface.py`
asserts the two names are absent from the module and that no file under `src/`
mentions them, so the answer keeps being checked instead of having been true
on the day someone looked. It also asserts `grid_to_svg` still renders — the
risk in a deletion card is not only that dead code survives it, but that live
code leaves with it, and this module's one real function serves every
`/api/puzzle/<id>/grid` request.

**Full suite: 3,596 passed, 0 failed** (AC-1), 26 skipped, one deselection.
