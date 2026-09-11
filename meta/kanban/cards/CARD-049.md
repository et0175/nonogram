# CARD-049: Route admin image-mode generation through the solver-verified pipeline

**Status:** done
**Priority:** P1
**Category:** bugfix
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/049-admin-image-mode-uniqueness
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-001
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_to_puzzle.py, src/nonogram/admin/app.py, tests/integration_tests.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-09-11T09:30:00Z
**Closed:** 2026-09-11T10:00:00Z
**Actual:** 0.1d
**Merge commit:** 98cdaaa
**Blocked by:** —

## What to implement

`image_to_grid()`/`create_puzzle_from_image()` in `src/nonogram/admin/image_to_puzzle.py`
(lines 21-177) never call `nonogram.solver` or `nonogram.orchestrator`. The canonical
image-mode path — `orchestrator.generate(GenerationRequest(mode="image", ...))`,
`orchestrator.py:1231-1275` — runs every image-derived grid through `judge_candidate`
(clue derivation + a real solver uniqueness check) and, if the candidate is not
uniquely solvable, a bounded pixel-nudge recovery loop (POL-002:
`image_source.nudge` + re-judge, up to a configured attempt bound), raising
`GenerationAbandoned` only if no nudge attempt succeeds. Admin's path has none of
this: a grid produced by `image_to_grid` could have zero or multiple solutions and
nothing detects it. `difficulty_score`/`difficulty_tier` are also currently
computed from grid size alone (`image_to_puzzle.py:126-136`) as a direct symptom of
never having real `SolverSignals` to score — this card fixes that too, for free,
by using the real pipeline.

1. In the admin batch-image-generation loop (`app.py:332-373`, inside
   `generate_batch_puzzles`'s POST handler) and anywhere else
   `create_puzzle_from_image` is called for a real (non-preview) puzzle, replace
   the call with `orchestrator.generate(GenerationRequest(mode="image",
   image=Path(image.file_path), image_filename=image.original_filename,
   width=width, height=height))` — **one call per image**, in the existing loop.
   `orchestrator.generate_batch()` is **not** usable here: it has no per-item
   image-path parameter (verified — its `GenerationRequest` construction only
   sets `mode`/`width`/`height`/`density`/`difficulty`, nothing image-specific).
2. Map the returned `Puzzle` onto what `puzzle_review.add_puzzle()` expects:
   `puzzle.grid`, `puzzle.clues.rows`/`puzzle.clues.columns` (convert to list if
   the storage layer needs lists — check `puzzle_review.py`'s `add_puzzle`
   signature), `puzzle.difficulty_score`, `puzzle.difficulty_tier` (a
   `difficulty.Tier` `StrEnum`, string-compatible for DB storage).
3. Catch `GenerationAbandoned` (and other `NonogramError` subclasses) **per image**
   in the existing loop, the same way `app.py:372-373` already catches
   `Exception` there — an abandoned image should append to `errors` and continue
   the batch, not fail the whole request.
4. `create_puzzle_from_image`/`image_to_grid` in `image_to_puzzle.py` become
   either dead code (remove) or stay only as what the `/api/puzzle-grid/<file_id>`
   preview routes use (check `app.py:1159-1225` — these are SVG *previews*, not
   real puzzle storage; decide whether they should also route through
   `orchestrator.generate` for consistency, or are acceptable as a lighter-weight
   preview-only path — state the decision in this card's Worktree notes).

## Acceptance criteria

- **AC-1** — given a real image uploaded through the admin batch flow, when
  puzzles are generated, then every stored puzzle's grid has been verified
  uniquely solvable by the actual solver (not merely produced by the image
  conversion), the same guarantee `nonogram generate --mode image` gives.
  *test:* to be named by the implementer — assert via the same mechanism
  `orchestrator`'s own tests use to check solution-count, on a puzzle generated
  through this admin code path.
- **AC-2** — given an image whose conversion cannot be made uniquely solvable
  within the nudge bound, when it's processed in a batch, then the batch
  continues for the remaining images and the failure is recorded in that batch's
  error list (not a whole-request 500).
  *test:* to be named by the implementer.
- **AC-3** — `difficulty_score`/`difficulty_tier` for admin-generated image-mode
  puzzles come from `nonogram.difficulty.score_difficulty` via real
  `SolverSignals` (through `orchestrator.generate`), not from grid size alone.

## Guardrails

- G-1: `src/nonogram/admin/image_to_puzzle.py`'s `generate_clues()` is CARD-051's
  territory (a separate fix) — don't refactor it as part of this card beyond
  what's needed to remove/replace `create_puzzle_from_image`'s call to it, to
  avoid the two cards' worktrees conflicting on the same file more than
  necessary.
- G-2: Do not change the crop/sizing behavior `ec18fb4`/CARD-045..048 established
  — this card is about adding solver verification, not revisiting how the
  target grid is derived from the source image.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: test, ref TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair, never a scalar. (check: review-lens)

## Worktree notes

[Env] forge 2026.8.17 (no forge.min_version declared in .skills.yml — no comparison performed)
[System contract] assembled fresh via system_rules.py --scope 'src/nonogram/admin/**' (card had no section — added: ADR-0006/R1, ADR-0022/R1)
[Known pre-existing gap] ADR-0006/R1's named check (TestDependencyBaseline_IsExactlyPillowAndNumpy) currently fails on `main` independent of any card — `reportlab` was added to pyproject.toml without updating the ADR/test (discovered during CARD-045's review). Tracked separately as CARD-057. Do not let this card's review spend a cycle on it; it cannot be fixed within this card's scope (pyproject.toml is out of Touches).

--- Implementation agent notes (pulled from worktree) ---

**Scope**: `src/nonogram/admin/app.py`, `tests/test_admin_image_uniqueness.py`
(new file). `src/nonogram/admin/image_to_puzzle.py` was **not** touched —
G-1's `generate_clues()` boundary is CARD-051's, and nothing about the storage
path required editing that file (see step-4 decision below).

**`src/nonogram/admin/app.py`**:
- Import block (~line 25): added `orchestrator` to the existing
  `from nonogram import clues` line and a new
  `from nonogram.errors import NonogramError`.
- `generate_batch_puzzles`'s POST handler, per-image loop (~line 332-395):
  replaced the `create_puzzle_from_image(...)` call with
  `orchestrator.generate(orchestrator.GenerationRequest(mode="image",
  image=Path(image.file_path), image_filename=image.original_filename,
  width=width, height=height))` — one call per image, same loop, predicted
  size unchanged (G-2). Mapped the returned `Puzzle` onto
  `puzzle_review.add_puzzle()`'s existing kwargs the way
  `batch_generator.py`'s `_generate_random_batch` (the established random-mode
  path) does: `puzzle.grid`, `puzzle.clues.rows`/`.columns`,
  `puzzle.width`/`.height`, `puzzle.difficulty_score`, `puzzle.difficulty_tier`
  (the `Tier` StrEnum, stored as-is), `quality_score` via the same
  `hasattr(puzzle, "quality_score")` fallback-to-75 pattern (unchanged —
  CARD-050's territory), `recognizability="medium"`, `strategies_used=[]`.
- Exception handling: added an explicit `except NonogramError as e:` branch
  ahead of the pre-existing `except Exception as e:`, both appending to
  `errors` and continuing the loop (AC-2).
- **Bug found and fixed while implementing**: naming the new local variable
  `request` shadowed Flask's module-level `request` import for the whole
  `generate_batch_puzzles` function, causing `UnboundLocalError` at the
  earlier `if request.method == "GET":` check. Renamed to `gen_request`.
  Caught by the new tests, not shipped.

**Step 4 decision — `create_puzzle_from_image`/`image_to_grid` stay as the
lighter-weight preview-only path** (the SVG-preview-only routes
`/api/puzzle-grid/<file_id>[/download]`, confirmed to not call
`puzzle_review.add_puzzle`), not routed through `orchestrator.generate`.
Reasoning: (1) cost — every preview render would pay for a full solve plus up
to 5 nudge re-solves, for a page re-rendered on every hover/reload; (2)
determinism mismatch — the nudge loop is unseeded, so two preview renders
could differ, trading the preview's current simple deterministic contract for
a different non-matching one; (3) a raw preview is exactly what "preview"
means — solvability is guaranteed where the puzzle is actually stored (this
card's fix), which is what AC-1 requires.

**Why a new test file** (`tests/test_admin_image_uniqueness.py`) instead of
extending `tests/integration_tests.py`: the latter isn't pytest-collected
today (doesn't match `test_*.py`/`*_test.py` discovery, confirmed via
`--collect-only`) and hardcodes paths into a sibling checkout. Left untouched,
still passes (`python tests/integration_tests.py --suite smoke` → 5/5).

**AC verification**:
- AC-1 (`test_ac1_stored_puzzle_grid_is_solver_verified_uniquely_solvable`):
  uploads a real fixture through the actual Flask routes, independently
  re-derives clues from the stored grid via `nonogram.clues.compute_clues`,
  runs `nonogram.solver.solve` directly, asserts `solution_count == 1`.
- AC-2 (`test_ac2_abandoned_image_recorded_as_error_and_batch_continues`):
  monkeypatches `orchestrator.generate` to raise `GenerationAbandoned` for one
  image in a two-image batch (real pipeline for the other); asserts 302 (not
  500), surviving image still stored, failure named in flashed messages.
- AC-3 (`test_ac3_difficulty_comes_from_real_solver_signals_not_grid_size`):
  asserts the stored `difficulty_tier` is a real lowercase `difficulty.Tier`
  value and `difficulty.tier_for_score(stored_score).value == stored_tier` —
  true by construction for the real pipeline, not the old size-only formula.

**Regression check**: via `git stash` on `app.py` only, AC-2 and AC-3 both
fail against the unmodified code (AC-1 happens to still pass pre-fix for this
particular fixture — expected, the property is "guaranteed unique", not "this
image was already broken"). Confirms non-tautological.

**Full-suite check**: ran the suite 4x across stash/no-stash combinations;
failure counts varied run-to-run even with ZERO changes present (41 then 39
on two successive stashed-app.py runs) — confirms pre-existing flakiness
unrelated to this card. `test_admin_image_uniqueness.py` +
`test_e2e/test_admin_workflow.py` together pass 21/21 on every repeated run;
`test_image_batch_size_fix.py` (CARD-045's suite) stays green 17/17.

**Note on `predict_size()`/range validation**: passing the predicted
`(width, height)` through as an explicit `GenerationRequest` means
`orchestrator._resolved_extent` uses it exactly as given (G-2 preserved). If
`predict_size()` ever returned a value outside `[10, 30]`,
`orchestrator.generate` would now raise `SizeOutOfRange` where the old code
silently produced whatever it produced — caught by the new `except
NonogramError` branch, recorded as a per-image batch error like any other.

`.venv` created fresh (gitignored). Incidental `src/nonogram.egg-info/*`
diffs from the editable install were left unstaged, excluded from the commit
— only `app.py` and the new test file were staged.

[Build gate] PASSED (full — python-pro has no testmon installed; 41
pre-existing failures, none in fix_scope, within the suite's already-
documented run-to-run flakiness range (37-41 observed across this and the
implementation agent's own repeated runs) — confirmed via a fresh same-run
main baseline showing 37, with the delta entirely in test_batch_history.py/
test_wave1_e2e.py/test_wave2_async_generation.py, none of which reference
generate_batch_puzzles/create_puzzle_from_image/orchestrator.generate)
[Scope] src/nonogram/admin/app.py, tests/test_admin_image_uniqueness.py
(reverted incidental src/nonogram.egg-info/* changes from the worktree's
local pip install before this check)

[Review 1/3] Score: 9.0 — crit: 0, imp: 0
[Review sync] 1 report(s) → meta/review/ (20260911T082753Z-CARD-049-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review): AC-1/AC-2/AC-3 verified non-aspirationally
(independent solver re-check for AC-1, real per-image exception path for
AC-2, differential tier check for AC-3 that would fail against the old
size-only formula). G-1/G-2 both confirmed held (image_to_puzzle.py diff
empty; predict_size()/crop logic untouched). ADR-0022/R1 ✓ holds;
ADR-0006/R1 ⚠ unchecked — stale_check (the pre-existing, unrelated
reportlab/CARD-057 gap, correctly not filed as a new finding here since
pyproject.toml diff is empty). 2 Minor notes (quality_score's dead
hardcoded-75 fallback — CARD-050's territory, correctly left alone; AC-2's
failure trigger is a monkeypatch of GenerationAbandoned rather than a real
nudge-exhaustion scenario — a reasoned, documented trade-off). 2 Out-of-scope
notes (app.py is a high-churn/defect-density hotspot generally; the two
SVG-preview routes still skip uniqueness verification, correctly per this
card's own Step 4 decision). Risk: LOW, lane: FAST. Zero Critical/Important —
severity gate open, score 9.0 ≥ min_score 8.

[8h spot-check] 1/1 sampled holds reproduced (ADR-0022/R1) — independent
skeptic confirmed GenerationRequest.width/height are two separate int|None
fields (orchestrator.py:234-235), never merged into a scalar, and the diff's
construction/storage-read path passes them as a pair throughout.

[AC/EC check] All criteria/constraints ✓ (evidence):
AC-1 ✓ demonstrated — evidence: test_ac1_stored_puzzle_grid_is_solver_verified_uniquely_solvable uploads bird1.jpg through the real Flask routes, independently re-derives clues via nonogram.clues.compute_clues, runs nonogram.solver.solve directly, asserts solution_count == 1 and is_unique. PASSED.
AC-2 ✓ demonstrated — evidence: test_ac2_abandoned_image_recorded_as_error_and_batch_continues drives a real two-image batch, patches orchestrator.generate to raise GenerationAbandoned for one image only; asserts 302 (not 500), 1 surviving puzzle stored, failure named in flashed "info" messages. PASSED.
AC-3 ✓ demonstrated — evidence: test_ac3_difficulty_comes_from_real_solver_signals_not_grid_size asserts stored difficulty_tier is a real lowercase Tier value and tier_for_score(stored_score).value == stored_tier. PASSED.
G-1 ✓ demonstrated — evidence: git diff main...HEAD -- src/nonogram/admin/image_to_puzzle.py is completely empty.
G-2 ✓ demonstrated — evidence: git diff main...HEAD -- src/nonogram/admin/image_manager.py src/nonogram/sourcing/image.py is completely empty; image.predict_size() called unchanged in app.py, result passed straight through.

All five items independently re-verified by a fresh AC-check agent against
the code (not trusted from any prior self-report or review claim). Gate
passes.

[Docs] No README under src/nonogram/admin/ or tests/ needs updating — no new
directory, no structural/purpose change (a new test file in an existing
tests/ directory whose README, per CARD-045's earlier check, doesn't attempt
to enumerate every file).

[Commit] Implementation was already committed as 8b9f28a
(fix(admin): route image-mode batch generation through solver-verified
pipeline) during implementation; nothing changed during review/fix/AC-gate
(zero fix cycles needed — cycle 1 passed clean), so 8b9f28a stands as the
final commit for this card.

CYCLE 1 COMPLETE — SUCCESS. Ready for `/kanban done CARD-049`.
