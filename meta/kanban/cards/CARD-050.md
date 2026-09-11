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

## Worktree notes

**Pre-implementation research confirmed:**
- CARD-049 (merged) moved production image-mode generation into
  `app.py`'s `generate_batch_puzzles` POST handler (`src/nonogram/admin/app.py`,
  `orchestrator.generate(gen_request)` at what is now line ~352). The old
  `image_to_puzzle.create_puzzle_from_image` density/hardcoded-"medium" code
  (`src/nonogram/admin/image_to_puzzle.py:90-160`) is now reachable only from
  two SVG-preview-only routes (`/api/puzzle-grid/<file_id>` and its
  `/download` variant, `app.py:1183`/`1214`) that render a grid for on-screen
  preview and never persist `quality_score`/`recognizability` to the DB — so
  fixing it there would not touch what AC-1 actually observes. Per the task
  brief, `image_to_puzzle.py` was left untouched; the fix went into `app.py`.

**Random-mode design decision (step 3): option 3b chosen — `quality_score`/
`recognizability` are `None` for random-mode puzzles, not a fabricated
number.**

Reasoning: `orchestrator.Puzzle` (the type `orchestrator.generate_batch()`
returns) exposes exactly one solver-derived signal —
`difficulty_score`/`difficulty_tier` (FR-009/ADR-0013, itself a composite of
line-logic coverage, backtracking branch pressure, solve time, size and
density) — and nothing else. There is no second, independently-meaningful
"quality" signal already sitting on `Puzzle` to repurpose: the only
candidate the card's own step-3 text names ("line-logic coverage,
backtracking depth") is already fully consumed by `difficulty_score` under a
different name and a different axis of meaning (*how hard was this to
solve*, not *how good is this puzzle*). Relabeling `difficulty_score` as
`quality_score` would be exactly the kind of fake the card exists to remove
— a number that looks like a real per-puzzle measurement but is actually
someone else's number wearing a different label. Building a genuinely new
random-mode quality signal (e.g. instrumenting the solver for a real
distinctness/elegance metric) would require touching `orchestrator.py`
and/or `solver/`, neither of which is in this card's Touches list — that is
real scope creep for a 1-day bugfix card, not a "define a metric" card.
`quality_metric.measure_quality()` itself is fundamentally an
image-comparison function (visual similarity + silhouette match + density
match against a *source picture*) and has no meaningful application to a
puzzle with no source picture at all — using it as-is for random mode isn't
an option (the DB's own column comment agrees: `quality_score = Column(...)
# 1-100 (image fidelity)`, `src/nonogram/db/models.py:61`).
Option 3b — `None`, explicitly — is therefore the only choice that doesn't
either misuse an existing signal or invent a new one outside scope. It is
also the literal DB-safe option: `Puzzle.quality_score`/`recognizability`
are both `Column(..., nullable=True)` already (`db/models.py:61-62`), so no
migration is needed (G-2 satisfied).

**Consequence for the "Minimum Quality Score" filter:** traced its actual
behaviour before touching anything. `None >= quality_filter` in
`_generate_random_batch` (`batch_generator.py`, old line ~316) would raise
`TypeError: '>=' not supported between instances of 'NoneType' and 'int'`
in Python 3 the moment `quality_score` became `None` — confirmed this would
crash every random-mode batch before making the change. Fixed by dropping
the quality-filter comparison entirely for random mode (every candidate the
orchestrator returns is now stored, per the "meaningless for random mode"
call already scoped in the card) rather than papering over it with a
default. Also traced where the UI actually exposes this filter:
`batch_create.html`'s "Minimum Quality Score" field posts to
`/batch/from-images` — the image-mode-only upload wizard — and no template
anywhere else renders a quality filter control, so the UI was **already**
scoped to image-mode-only before this card; the random-mode `source="random"`
path through `POST /batch/create` (`app.py:126`) is reachable only
programmatically/by tests, never through a rendered form. Given that,
`batch_create.html` needed no functional change; added a clarifying help-text
sentence to the field (`src/nonogram/admin/templates/batch_create.html`)
stating explicitly that the filter measures fidelity to the uploaded image
and does not apply to randomly-generated puzzles, satisfying the card's
"clearly relabel" instruction even though the filter was never functionally
reachable for random-mode batches.

**Known, accepted residual gap (out of Touches scope, not fixed):** four
display templates render `puzzle.quality_score`/`recognizability` for
listing/detail views — `batch_status.html:144` (`{{ puzzle.quality_score }}`
→ renders literally `"Quality: None"` for a random-mode puzzle, verified
against Jinja2's default `None` rendering), `generated_puzzles.html:65`
(`{{ puzzle.get('quality_score', 0)|int }}` → Jinja's `int` filter catches
the `TypeError` and silently renders `"0/100"`, which is misleading but not
a crash), and `book_select_puzzles.html:125` / `puzzles_list.html:160,325`
(already guarded with `or 'N/A'`, so these two render correctly as-is).
None of these four files are in this card's Touches list and AC-2 does not
require fixing them (AC-2's own UI requirement is specifically about the
quality *filter*, which is addressed above). Flagging this here rather than
silently fixing files outside declared scope, per the scope-discipline
instructions — a follow-up card should update `batch_status.html` and
`generated_puzzles.html` to render `"Quality: N/A"`-style text for a `None`
`quality_score`, mirroring the other two templates.

**SCOPE+ — `src/nonogram/generation/random_generator.py` needed more than a
one-line import fix (unplanned, discovered during implementation, but the
file itself is fully within Touches):**

Fixing AC-3's import exactly as literally stated in the card
(`from src.nonogram.analysis...` → `from nonogram.analysis...`) makes both
of this file's analysis imports visible to
`tests/test_cli.py::test_every_import_in_the_package_points_inward` — the
ADR-0007 structural guard CLAUDE.md documents ("capability modules never
import ... each other laterally"). The corrected import is immediately
flagged as a **new, genuine test failure**: `nonogram.generation` and
`nonogram.analysis` are both capability-rank modules, so one importing the
other laterally is a real violation — one the old `src.`-prefixed form had
been silently hiding from the checker all along (it resolves to a component
name, `"src"`, the checker's walk doesn't recognize), not one this card's
fix newly introduces. Verified this is the trigger by reverting the fix
under `git stash` and re-running the guard test — it passes with the broken
import, fails immediately with the "correct" one.

Resolution: followed this project's own documented precedent for exactly
this situation (`solver/propagate.py`'s `mask_runs`, per CLAUDE.md) —
reimplemented natively, in `random_generator.py`, the one piece of
`strategy_counter.calculate_difficulty_from_strategies` this file's
`generate_puzzle()` actually uses (`_difficulty_from_strategy_flags`,
verified to produce byte-identical output to the original for every
strategy/backtracking combination the file can construct — see
`test_ac3_reimplemented_difficulty_formula_matches_the_original_independently`
in the new test file, which cross-checks it against the real
`strategy_counter` module from the test tree, where that import is legal).
The dead `measure_quality` import (imported, never called anywhere in the
file) was simply dropped. Result: `random_generator.py` now carries zero
`nonogram.analysis` imports of any kind — AC-3 satisfied in the strongest
sense (no more fragile import at all, not just a corrected prefix) and the
structural guard test stays green. This file still has zero production
callers (confirmed via repo-wide grep for `RandomNonogramGenerator`/
`get_generator` — only its own test file references it), so nothing
downstream depends on its internals beyond the two files touched. Its own
`quality_score`/`recognizability` fields (`int(60 + 35 * ...)` heuristic,
hardcoded `"medium"`) are the same bug pattern this card targets elsewhere,
but fixing them is out of this card's step-3 scope (step 3 targets
`batch_generator.py`'s production path, not this dead module) — left
untouched, flagged here for visibility only.

**Files changed:**
- `src/nonogram/admin/app.py:28-30` (new imports), `:359-373` (AC-1: real
  `measure_quality()` call replacing the density/hardcoded-medium fallback
  in `generate_batch_puzzles`), `:392` (`recognizability=recognizability`).
- `src/nonogram/admin/batch_generator.py:32-38` (`PuzzleMetrics.quality_score`/
  `recognizability` now `Optional`), `:286-305` (dropped dead `quality_filter`
  extraction), `:311-347` (`_generate_random_batch`: AC-2, `None`/`None`,
  filter no longer applied), `:475-489` (`_generate_puzzle_with_metrics`:
  same AC-2 fix).
- `src/nonogram/admin/templates/batch_create.html:74-82` (clarifying help
  text on the quality filter).
- `src/nonogram/generation/random_generator.py`: AC-3 import fix plus the
  SCOPE+ reimplementation described above (module docstring, new
  `_difficulty_from_strategy_flags` function, `generate_puzzle()` updated to
  use it).
- `tests/test_card_050_quality_recognizability.py` (new): 9 tests covering
  AC-1/AC-2/AC-3.

**AC verification evidence:**
- AC-1: `test_ac1a_faithful_and_degraded_conversions_of_same_image_score_differently`
  (direct `measure_quality()` unit test: faithful vs. degraded conversion of
  the same source image score 20+ points apart, differing recognizability
  tiers) and `test_ac1b_image_mode_batch_stores_real_measure_quality_output`
  (full Flask-app integration test through `/batch/from-images` →
  `/batch/generate-puzzles` using the real `bird1.jpg` fixture; the stored
  `quality_score`/`recognizability` are asserted equal to an independent
  fresh `measure_quality()` recomputation against the same source file and
  stored grid — a hardcoded/density-only value could not coincidentally
  match this). Both pass; both were confirmed to **fail** against the
  pre-fix code via `git stash`.
- AC-2: `test_ac2_random_mode_quality_score_is_none_not_75` (10 real puzzles
  via `BatchGenerator.create_batch(source="random")`; every `quality_score`/
  `recognizability` is `None`, none is `75`) and
  `test_ac2_quality_filter_no_longer_drops_or_crashes_random_batches`
  (`quality_filter=80` no longer drops or crashes — all 10 puzzles stored).
  Both pass; the first fails against pre-fix code via `git stash`.
- AC-3: three tests — no `from src.nonogram` import statement remains
  (ast-based), no import resolves to the `nonogram.analysis` component at
  all (ast-based, the exact condition the structural guard checks), and the
  reimplemented difficulty formula matches the original independently
  across 6 strategy/backtracking scenarios. All three pass; two of three
  fail against pre-fix code via `git stash`.
  Also directly verified:
  `./.venv/bin/python -m pytest tests/test_cli.py::test_every_import_in_the_package_points_inward`
  — passes after the fix, and was confirmed (via `git stash`) to **newly
  fail** if the import were "fixed" to `from nonogram.analysis...` without
  the accompanying SCOPE+ reimplementation.

**Full regression check:** `tests/test_quality_metric.py` (17/17, unchanged
baseline), `tests/test_random_generator.py` (21/21), `tests/test_batch_generator.py`
(16/16), `tests/test_admin_image_uniqueness.py` (3/3, CARD-049's own suite,
unaffected), `tests/test_card_050_quality_recognizability.py` (9/9, new).
Filtered subset `pytest tests/ -k "admin or image or quality"`: 17 pre-existing
failures, byte-identical failure list before/after this change (confirmed via
`git stash` diff) — all in `tests/test_sourcing_image.py`/`test_derive_shape.py`/
`test_nudge.py`/`property/test_grid_dimensions.py`, referencing a `pictures/`
corpus directory not present in this worktree, per the picture-corpora-are-
experiments convention. Full suite: 39-41 failures before/after (documented
as flaky in the task brief; independently confirmed flaky here — two
consecutive full-suite runs produced different failure sets in
`test_batch_history.py`/`test_wave2_async_generation.py`, both DB/random-seed
dependent and untouched by this card).
