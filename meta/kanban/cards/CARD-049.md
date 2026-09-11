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
