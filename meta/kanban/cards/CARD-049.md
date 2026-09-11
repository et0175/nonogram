# CARD-049: Route admin image-mode generation through the solver-verified pipeline

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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

## Worktree notes

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
  `puzzle_review.add_puzzle()`'s existing kwargs exactly the way
  `batch_generator.py`'s `_generate_random_batch` (the orchestrator's
  already-established random-mode path) does: `puzzle.grid`,
  `puzzle.clues.rows`/`.columns`, `puzzle.width`/`.height`,
  `puzzle.difficulty_score`, `puzzle.difficulty_tier` (the `Tier` StrEnum,
  stored as-is — lowercase `"easy"/"medium"/"hard"`, string-compatible,
  matching the same precedent), `quality_score` via the same
  `hasattr(puzzle, "quality_score")` fallback-to-75
  `_generate_random_batch` already uses (the orchestrator's `Puzzle` carries
  no `quality_score` field), `recognizability="medium"`,
  `strategies_used=[]`.
- Exception handling: added an explicit `except NonogramError as e:` branch
  (covers `GenerationAbandoned` and any other domain error
  `orchestrator.generate`/`sourcing`/`solver` can raise) ahead of the
  pre-existing `except Exception as e:`, both appending to `errors` and
  continuing the loop — per-image failure, whole-batch continues (AC-2). The
  existing `except Exception` already structurally covered this (every
  `NonogramError` is an `Exception`), so this is a clarity/intent change, not
  a behavior change on its own.
- **Bug found and fixed while implementing**: naming the new local variable
  `request` (`orchestrator.GenerationRequest(...)`) shadowed Flask's
  module-level `request` import for the *whole* `generate_batch_puzzles`
  function body — Python's scoping rules make a name assigned anywhere in a
  function local to that function throughout, so the earlier
  `if request.method == "GET":` check (line ~307, *before* the loop) started
  raising `UnboundLocalError` at request time. Renamed the local to
  `gen_request`. Caught immediately by the new test suite, not shipped.

**Step 4 decision — `create_puzzle_from_image`/`image_to_grid` stay as the
lighter-weight preview-only path, not dead code, not routed through
`orchestrator.generate`.**
Both remaining call sites (`app.py`'s `/api/puzzle-grid/<file_id>` and
`/api/puzzle-grid/<file_id>/download`, ~line 1160-1215 after this card's
edits) are SVG *previews* of the raw conversion, not real puzzle storage —
confirmed by reading both routes end to end; neither calls
`puzzle_review.add_puzzle` or anything DB-adjacent. Reasoning for not routing
them through `orchestrator.generate` too:
1. **Cost**: every preview render would pay for a full uniqueness solve plus,
   on a non-unique conversion, up to `MAX_NUDGE_ATTEMPTS` (5) re-solves — for
   a page that's re-rendered on every hover/reload while the admin browses
   images, not a one-shot generation.
2. **Determinism mismatch**: `orchestrator.generate`'s nudge loop draws from a
   `random.Random()` seeded per call (no seed threaded through from the
   preview route), so two preview renders of the same file could nudge
   differently and show a grid that isn't byte-identical to what a later
   *storage* call (also via `orchestrator.generate`, also unseeded) would
   produce — the preview already doesn't promise pixel-identity with the
   stored puzzle today (it's `image_to_grid`'s single deterministic
   conversion, no nudge), and adding nudge to the preview would trade that
   known, simple contract for a different non-matching one, not a matching
   one.
3. A raw, unverified-uniqueness SVG preview is exactly what "preview" means
   here — the admin is looking at what the picture roughly turns into, not
   confirming solvability. Solvability is guaranteed at the point a puzzle is
   actually stored (this card's fix), which is the only point that matters
   for AC-1.
`create_puzzle_from_image`/`image_to_grid` are therefore kept unchanged and
undocumented as anything other than the preview path; `tests/integration_tests.py`
(a non-pytest report script, see below) also still calls `image_to_grid`
directly and continues to pass.

**Why a new test file (`tests/test_admin_image_uniqueness.py`) instead of
extending `tests/integration_tests.py`**: the latter is a hand-rolled
report-printing script (`run_smoke_test`/`run_full_suite`, functions taking a
positional `report` argument, no pytest fixtures) that pytest doesn't even
collect today — its filename doesn't match pytest's default
`test_*.py`/`*_test.py` discovery patterns, confirmed via
`pytest --collect-only` before touching it. It also hard-codes absolute paths
into a *sibling* checkout (`/Users/.../PythonProject4/silhouette/...`, not this
worktree). Extending it would mean rewriting its shape for no benefit; a real
pytest file against the actual Flask app (mirroring
`tests/e2e/test_admin_workflow.py`'s fixture style) is the direct path to
AC-1/AC-2/AC-3 coverage. `tests/integration_tests.py` itself is untouched and
still passes (`python tests/integration_tests.py --suite smoke` → 5/5 PASS).

**AC verification**:
- **AC-1** (`test_ac1_stored_puzzle_grid_is_solver_verified_uniquely_solvable`):
  uploads a real fixture (`tests/fixtures/bird1.jpg`) through the actual
  `/batch/from-images` → `/batch/generate-puzzles` Flask routes, fetches the
  stored puzzle from `batch_generator.get_batch_puzzles`, independently
  re-derives clues from the stored grid via `nonogram.clues.compute_clues`
  (cross-check against what was stored, not a re-read), and runs
  `nonogram.solver.solve` on them directly, asserting
  `solution_count == 1` / `is_unique`.
- **AC-2** (`test_ac2_abandoned_image_recorded_as_error_and_batch_continues`):
  monkeypatches `orchestrator.generate` to raise `GenerationAbandoned` for one
  specific uploaded image (by filename) while running the real pipeline for
  the other, in a two-image batch through the same real Flask routes; asserts
  the response is a 302 redirect (not a 500), the surviving image is still
  stored (`get_batch_puzzles` returns exactly 1), and the failure is present
  in the flashed `"info"` messages naming the failed file.
- **AC-3** (`test_ac3_difficulty_comes_from_real_solver_signals_not_grid_size`):
  same real-flow upload as AC-1; asserts the stored `difficulty_tier` is a
  member of the real `difficulty.Tier` StrEnum's lowercase values (the old
  code stored capitalized `"Easy"/"Medium"/"Hard"` literals, never derived
  from a score) *and* that `difficulty.tier_for_score(stored_score).value ==
  stored_tier` — true by construction for the real pipeline
  (`Puzzle.difficulty_tier` *is* `tier_for_score(difficulty_score)`) but not
  for the old size-only formula, whose "Easy" score band (20..50) mostly
  falls in the real Medium band (33..66].

**Regression check (pre-fix vs. post-fix on the exact same 3 tests)**: via
`git stash` on `app.py` only, AC-2 and AC-3 both fail against the unmodified
code (AC-1 happens to still pass pre-fix for this particular fixture image —
expected, since the property under test is "the pipeline *guarantees*
uniqueness", not "this one image was already broken"; the old path's own
`image_to_grid`→`generate_clues` round-trip is internally consistent, it's
just never solver-checked). Confirms the new tests exercise the actual
change, not tautologies.

**Full-suite check**: ran `pytest tests/` four times across this session
(`git stash`/no-stash combinations) to separate my changes from pre-existing
flakiness — failure counts varied run-to-run **even with zero changes
present** (41, then 39 failures on two successive stashed-app.py runs with no
code difference at all), confirming the suite has inherent test-order/timing
flakiness unrelated to this card (matches the card's own "~40 known
pre-existing failures" note and CARD-057's tracked reportlab/ADR-0006 gap). No
failure was reproducibly and exclusively attributable to this card's change:
`tests/test_admin_image_uniqueness.py` + `tests/e2e/test_admin_workflow.py`
together pass 21/21 on every one of several repeated runs, and
`tests/test_image_batch_size_fix.py` (CARD-045's suite, same file area) stays
green (17/17).

**Note on `image.predict_size()` / range validation**: passing the predicted
`(width, height)` straight through as an explicit `GenerationRequest(width=,
height=)` means `orchestrator._resolved_extent` uses it exactly as given
(both sides stated) and never re-derives from the source — G-2 preserved. If
`predict_size()` ever returned a value outside `random_grid`'s `[10, 30]`
range, `orchestrator.generate` would now raise `SizeOutOfRange` (a
`NonogramError` subclass) where the old code silently produced whatever
`sourcing_image.generate` did; this is caught by the new `except
NonogramError` branch and recorded as a per-image batch error like any other
`NonogramError`, not a special case.

`.venv` created fresh in the worktree (`python3.14 -m venv .venv && pip
install -e '.[dev,admin,db]'`), gitignored, not committed. Incidental
`src/nonogram.egg-info/*` diffs from the editable install were left unstaged
and excluded from the commit (explicit pathspec, per project convention) —
only `src/nonogram/admin/app.py` and the new test file were staged.
