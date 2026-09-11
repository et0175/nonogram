# CARD-050: quality_score and recognizability are hardcoded fakes, not measurements

**Status:** in_progress
**Priority:** P1
**Category:** bugfix
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/050-real-quality-recognizability
**Worktree:** ../PythonProject4-CARD-050
**Source:** meta/review/20260910T170025Z.yml#F-002,F-003
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/batch_generator.py, src/nonogram/generation/random_generator.py, src/nonogram/analysis/quality_metric.py, src/nonogram/admin/templates/batch_create.html
**Review score:** —
**Started:** 2026-09-11T10:15:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`quality_score` and `recognizability` are hardcoded constants on every admin
generation path, not real measurements:

- **Image mode** (`image_to_puzzle.py:118-124`): `quality_score` is computed
  purely from the *output grid's* fill density being close to 50% — it never
  compares the generated puzzle against the source picture it came from, so a
  nonsense pattern near 50% density scores higher than a faithful silhouette
  reproduction at, say, 15% or 85% density. `recognizability` is a literal
  hardcoded `"medium"` (line 129, comment: "Images always medium
  recognizability").
- **Random mode** (`batch_generator.py:310,463`): `quality_score = puzzle.quality_score
  if hasattr(puzzle, "quality_score") else 75` — `orchestrator.Puzzle`
  (`orchestrator.py:505`) has **no** `quality_score` attribute (grep-verified
  across the whole file), so this is unconditionally `75` for every puzzle ever
  generated this way. `recognizability` similarly always falls to
  `getattr(puzzle, "recognizability", "medium")`'s default.
- This is not cosmetic: `app.py:75-76`'s batch form exposes "Minimum Quality
  Score" as a real filter, and `app.py:350` (`if puzzle_data["quality_score"] <
  quality_filter: continue`) silently drops puzzles below it — for random mode
  this filter is inert by construction (every candidate scores exactly 75).
  `quality_score` is also rendered as "Quality: X/100" in `batch_status.html:144`,
  `book_select_puzzles.html:125`, `generated_puzzles.html:65`, and
  `puzzles_list.html:160,325`.
- A real, tested implementation exists and is unused:
  `nonogram.analysis.quality_metric.measure_quality()` + a `Recognizability`
  enum (`HIGH`/`MEDIUM`/`LOW`, matching the DB's stored string values exactly).
  It has its own passing tests (`tests/test_quality_metric.py`) and is imported
  only by `src/nonogram/generation/random_generator.py`, which nothing in
  production imports — zero production callers today.
  `meta/architecture/inputs/v2-batch-generation.md:75` explicitly specs
  `quality_score (auto-calculated)` — the raw requirement was real computation;
  the shipped code is a constant.

1. **Before wiring `nonogram.analysis` into any production path**, fix
   `src/nonogram/generation/random_generator.py:8-9`'s
   `from src.nonogram.analysis...` import to `from nonogram.analysis...` — the
   current form only resolves by accident of how this project's test suite
   happens to be invoked (`python -m pytest` from the repo root prepends cwd to
   `sys.path`), and would break under any other invocation (the installed
   console script, a different cwd, plain `pytest`). Mixing both import styles
   for the same module creates two distinct Python module objects with
   incompatible class identities — fix this first so it can't bite whatever
   this card wires in.
2. **Image mode**: call `nonogram.analysis.quality_metric.measure_quality()` (or
   equivalent) comparing the generated grid against the source picture.
   **Update since this card was written**: CARD-049 (merged, commit `98cdaaa`)
   moved real (non-preview) image-mode generation OUT of
   `image_to_puzzle.create_puzzle_from_image` and into `app.py`'s
   `generate_batch_puzzles` POST handler, calling `orchestrator.generate(...)`
   directly and mapping the returned `Puzzle` onto `puzzle_review.add_puzzle()`
   — see `app.py`'s per-image loop (~line 332-400 post-CARD-049). The density-
   only heuristic and hardcoded `"medium"` you're replacing now live in
   `image_to_puzzle.py` only as the code path for the two SVG-**preview**
   routes (`/api/puzzle-grid/<file_id>[/download]`), which per CARD-049's own
   documented decision deliberately do NOT store puzzles and are NOT where
   `quality_score`/`recognizability` need fixing — fixing them there would be
   wasted effort on values nothing persists. **Do this card's image-mode fix in
   `app.py`'s per-image loop**, right after `orchestrator.generate()` returns
   a `Puzzle` and before/alongside the `puzzle_review.add_puzzle(...)` call —
   you have the source image path (`image.file_path`) and the resulting
   `puzzle.grid` both in scope there. `image_to_puzzle.py`'s
   `create_puzzle_from_image`'s own `quality_score`/`recognizability`
   computation may be left as-is (it's dead weight for the preview routes,
   which don't read those two fields from its return dict) or cleaned up if
   trivial — implementer's judgment, not the point of this card.
3. **Random mode**: there is no "source picture" to compare against for a
   randomly-generated grid, so `quality_metric.measure_quality()` as-is doesn't
   apply. Either (a) define and wire a random-mode-appropriate quality signal
   (e.g., derived from solver signals already available on `orchestrator.Puzzle`
   — line-logic coverage, backtracking depth — which is a defensible, different
   definition of "quality" for a puzzle with no source image), or (b) if no
   sound metric exists yet, set `quality_score`/`recognizability` to `None` for
   random-mode puzzles rather than a value indistinguishable from a real
   measurement, and remove or clearly relabel the "Minimum Quality Score" filter
   for random-mode batches in `batch_create.html` so it stops implying a
   guarantee that doesn't hold. State which option was chosen and why in this
   card's Worktree notes.
4. Update `puzzle_review.py`'s `MockGenerator` (lines ~717-728) is explicitly
   **out of scope** for this card (test/scaffold-only, tracked separately) —
   don't touch it here.

## Acceptance criteria

- **AC-1** — given an image-mode puzzle is generated, when its `quality_score`/
  `recognizability` are computed, then they come from a real comparison between
  the generated grid and the source picture (via `nonogram.analysis.quality_metric`
  or an equivalent), not from output-grid density alone or a hardcoded string.
  *test:* to be named by the implementer, asserting the value differs
  meaningfully between a faithful and a degraded conversion of the same source
  image.
- **AC-2** — given a random-mode puzzle is generated, when its `quality_score` is
  read, then it is either a real, defined measurement (not the literal constant
  `75` for every puzzle) or explicitly absent/`None` with the UI updated to match
  — whichever option this card's implementer chose per step 3 above.
  *test:* to be named by the implementer — must generate two real puzzles via
  `orchestrator.generate_batch()` and confirm their `quality_score`s are not
  both exactly `75` (unless that is a coincidence the test controls for), or
  confirm the field is `None` and the UI no longer offers a quality filter for
  random mode.
- **AC-3** — `src/nonogram/generation/random_generator.py`'s import is fixed to
  `from nonogram.analysis...` before this card is closed.

## Guardrails

- G-1: Do not touch `MockGenerator` in `puzzle_review.py` — tracked separately,
  and it has no production caller today (not urgent).
- G-2: If random mode ends up with `quality_score = None` (option 3b), do not
  silently change the DB column's nullability assumptions elsewhere — check
  `nonogram.db.models.Puzzle.quality_score`'s column definition and any
  non-null constraint before choosing this option.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: test, ref TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair, never a scalar. (check: review-lens)

## Worktree notes

[Env] forge 2026.8.17 (no forge.min_version declared in .skills.yml — no comparison performed)
[System contract] assembled fresh via system_rules.py --scope 'src/nonogram/admin/**,src/nonogram/generation/**,src/nonogram/analysis/**' (card had no section — added: ADR-0006/R1, ADR-0022/R1)
[Known pre-existing gap] ADR-0006/R1's named check (TestDependencyBaseline_IsExactlyPillowAndNumpy) currently fails on `main` independent of any card — `reportlab` was added to pyproject.toml without updating the ADR/test (discovered during CARD-045's review). Tracked separately as CARD-057. Do not let this card's review spend a cycle on it; it cannot be fixed within this card's scope (pyproject.toml is out of Touches).
[Touches updated at start] Original Touches listed `image_to_puzzle.py`; corrected to `app.py` (real image-mode generation moved there by CARD-049, merged before this card started) plus `analysis/quality_metric.py` (the module this card wires in). See the "What to implement" step-2 update above for the full reasoning.
