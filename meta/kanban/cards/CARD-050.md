# CARD-050: quality_score and recognizability are hardcoded fakes, not measurements

**Status:** ready
**Priority:** P1
**Category:** bugfix
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/050-real-quality-recognizability
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-002,F-003
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_to_puzzle.py, src/nonogram/admin/batch_generator.py, src/nonogram/generation/random_generator.py, src/nonogram/admin/templates/batch_create.html
**Review score:** —
**Started:** —
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
   equivalent) comparing the generated grid against the source picture, in
   `create_puzzle_from_image` (or wherever CARD-049 ends up placing image-mode
   generation) — replacing the density-only heuristic and the hardcoded
   `"medium"`.
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
