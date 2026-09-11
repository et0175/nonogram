# CARD-059: Remove the unreachable, unverified SVG-preview-by-file_id routes

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/059-remove-dead-svg-preview-routes
**Worktree:** —
**Source:** conversation, 2026-09-11 (verified while answering "does admin's puzzle preview reflect what the CLI/real generation would produce")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py
**Review score:** 9.5 (cycle 1/3)
**Started:** 2026-09-11T15:20:00Z
**Closed:** 2026-09-11T15:45:00Z
**Actual:** 0.03d
**Merge commit:** 47ca753
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

## System contract

_(no rule's scope.code covers this diff at a code-check level applicable here — confirmed via review; POL-002, the domain policy the removed routes bypassed, has no mechanical check registered.)_

[Review 1/3] Score: 9.5 — crit: 0, imp: 0
[Review sync] 1 report(s) → meta/review/ (20260911T123052Z-CARD-059-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review): independently re-derived every claim in
the Worktree notes rather than trusting them — re-grepped for both
removed imports' other usages, confirmed create_puzzle_from_image's
real test caller by reading the test file directly, confirmed
grid_to_svg's live usage in the kept routes by reading them directly.
Went beyond the card's own AC-1 evidence by running the FULL suite on
BOTH main and this branch and diffing the failure sets — identical 40
failures except one flaky sub-case swap in test_batch_history.py
(order/data-dependent, unrelated to app.py) — stronger proof of zero
regressions than a single-branch run. Judged the two disclosed-but-
untouched dead-code items (get_svg_filename now fully dead repo-wide;
grid_to_svg_bytes already dead pre-diff) as correct scope discipline
for a Touches:app.py-only card, not a finding requiring action. Zero
Critical/Important; 1 Minor (suggest a small follow-up card to clean
up both now/already-dead grid_renderer.py functions in one pass — not
created here, flagged for the user). Risk: LOW, lane: FAST. Score 9.5
≥ min_score 8, zero Critical/Important — severity gate OPEN. Cleared
on cycle 1 of 3.

[8h spot-check] 2/2 sampled holds reproduced — independently re-ran
the full suite fresh (41 failures, none touching app.py/grid_renderer.py/
image_to_puzzle.py) and re-confirmed the diff is exactly 1 file,
70 deletions + 1 insertion.

[AC/EC check] All criteria/guardrails ✓ (evidence):
AC-1 ✓ demonstrated — evidence: reviewer's own full-suite diff (main vs branch) shows an identical failure set bar one unrelated flaky swap; this gate's independent re-run: 41 failures, none touching the changed file.
AC-2 ✓ demonstrated — evidence: fresh grep for api_puzzle_grid\b and the literal route strings across src/ and tests/, zero matches.
AC-3 ✓ demonstrated — evidence: test_wave3_image_generation.py + tests/e2e/test_admin_workflow.py — 25 passed, 16 skipped, 0 failed, fresh.
G-1 ✓ demonstrated — evidence: git diff main...HEAD --stat shows exactly src/nonogram/admin/app.py touched; the kept /api/puzzle/<puzzle_id>/grid routes are byte-identical (only shifted).
G-2 ✓ demonstrated — evidence: same diff-scope check; zero touches to orchestrator.py, sourcing/, or cli.py.

All five items independently re-verified across implementer, reviewer,
and this gate. Gate passes.

[Docs] No README under src/nonogram/admin/ carries a route-level
inventory that would need updating for this diff.

[Commit] Final state is 1 commit on the branch: c6a7dbd (dead route +
unused-import removal). Nothing further needed — cycle 1 cleared
cleanly.

CYCLE 1 COMPLETE — SUCCESS. Ready for `/kanban done CARD-059`.

Note for follow-up (not created here, per protocol): both reviewer and
implementer flagged `grid_renderer.py`'s `get_svg_filename` (newly dead
as a direct result of this card) and `grid_to_svg_bytes` (already dead
before this card) as worth a small cleanup card in one pass.
