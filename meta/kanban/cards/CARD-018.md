# CARD-018: Strengthen solver search to meet AC-037 at 20x20 mid/low density

**Status:** in_progress
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/018-solver-search-strength
**Worktree:** ../PythonProject4-card-018
**Source:** meta/architecture/decisions/adr/0001-generation-time-thresholds.md (revision, DEC-019)
**Idea:** —
**Wave:** —
**Depends on:** CARD-006
**Touches:** src/nonogram/solver/search.py, src/nonogram/solver/propagate.py, tests/bench_generate.py, tests/test_solver.py
**Review score:** —
**Started:** 2026-08-29T11:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CARD-006's benchmark (`BenchGenerate_20x20_p95Under5s`, AC-037) empirically confirmed that
20x20 generation is genuinely uninteractive at 30-40% density: p95 is unbounded (half the
sampled requests hit the 30s hard cap), because line-logic propagation resolves almost
nothing at that density (0/400 cells on 11 of 12 sampled candidates) and the backtracking
search visits thousands of wrong subtrees before finding two solutions or exhausting. ADR-0001
was revised (2026-08-28, resolves DEC-019) to reaffirm the 5s/20x20 target rather than narrow
it, on the strength of CARD-004's own finding that the search's *propagation* is sound on
these grids — a descent guided by the true solution needs only 47-283 guesses — so the cost is
specifically in how many wrong subtrees get visited before finding a right one. This card is
that follow-up: strengthen subtree rejection so fewer wrong branches are explored per solve.

1. **Add a lookahead/probing step to branch selection (`solver/search.py`).** Before
   committing to a guessed value at the chosen branch cell, do a cheap forward check — e.g.
   tentatively assign the value, run one bounded round of `propagate` (or a lighter
   consistency check), and reject the branch immediately if it produces a contradiction,
   instead of pushing a full frame and discovering the contradiction several levels deeper.
   This is the specific lever CARD-006's Worktree notes name: "a wrong subtree is rejected
   near the root instead of hundreds of levels down."
2. **Keep the existing fail-fast/counting contract unchanged.** AC-015/016/017 (CARD-004) and
   AC-037/AC-038 (CARD-006) must still hold — this card changes *how fast* wrong subtrees are
   rejected, not the solver's correctness, its solution-counting semantics, or its public API.
   `solve()`'s signature (including the `deadline` keyword CARD-006 added) does not change.
3. **Re-enable AC-037's benchmark.** `tests/bench_generate.py::test_20x20_p95_is_under_5s`
   is currently `xfail`-marked (CARD-006, citing this card). Once the p95 target is genuinely
   met across the full density range at 20x20, remove the `xfail` marker so the benchmark
   becomes a real, enforced gate again — do not remove it while any density still exceeds the
   cap; if full coverage isn't reachable this cycle, narrow the fix's scope and report exactly
   which density range remains a gap, rather than silently declaring victory on partial data.
4. **Re-measure, don't assume.** Use the same benchmark methodology CARD-006 established
   (censored-at-cap sampling, `tests/bench_generate.py`) to produce fresh p95 numbers across
   the density range 10-90%, and record them in this card's Worktree notes so the next reader
   doesn't have to re-derive whether the fix actually worked.

## Acceptance criteria

- **AC-037** (boundary) — given a 20x20 random-grid generation request under typical hardware,
  at any valid density, when generation runs (including any regenerate retries), then p95
  completion time is ≤5s.
  *test:* `BenchGenerate_20x20_p95Under5s`

## Guardrails

- G-1: Do not change the solver's public API (`solve(row_clues, column_clues, *, deadline=None)`,
  `SolveResult`, `SolveSignals`, `MANY`) — this card is an internal search-strategy change,
  not a signature change. `src/nonogram/solver/__init__.py`'s re-exports are out of scope
  unless a genuine new export is needed, and if so it must be additive only
- G-2: AC-015/016/017 (CARD-004) and AC-038 (CARD-006) must still pass completely unchanged —
  this card must not alter solution-counting correctness or the cooperative-deadline mechanism,
  only how quickly wrong branches are rejected
- G-3: `EC-001`/`PropertyTest_Solver_NeverFalsePositiveUniqueness` must still pass — a faster
  but incorrect subtree-rejection heuristic is worse than the current slow-but-correct one.
  Any new pruning logic must be provably sound (never reject a branch that could still lead to
  a valid solution), not merely empirically fast
- G-4: Do not edit `src/nonogram/orchestrator.py`, `src/nonogram/cli.py`,
  `src/nonogram/export/**`, `src/nonogram/sourcing/**`, `src/nonogram/clues.py`,
  `pyproject.toml` — outside this card's footprint
- G-5: Do not remove or weaken `tests/bench_generate.py::test_20x20_p95_is_under_5s`'s
  assertion strength (the censoring/early-stop mechanics CARD-006 built) — only its `xfail`
  marker may be removed, and only once the underlying numbers genuinely support it

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)

## Architecture context

- **FR:** FR-006
- **NFR:** NFR-001
- **ADR:** ADR-0001 (revised 2026-08-28), ADR-0009, ADR-0012
- **Components:** COMP-005 (Solver)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Context] This card exists because of ADR-0001's 2026-08-28 revision (DEC-019): the
`keep_and_track_gap` resolution — the 20x20/5s target was reaffirmed rather than narrowed,
specifically because CARD-004 established the search's propagation is sound and the gap is a
tractable search-strength problem. Read ADR-0001's full revised text (Context + Decision +
History) before starting — it explains why this card exists instead of a requirement change.
Read CARD-004's Worktree notes (STRUCTURE-3/4, the performance findings table) and CARD-006's
Worktree notes (the AC-037 finding, the exact density/seed breakdown) before designing the
lookahead — both already contain detailed profiling data this card should build on rather than
re-measure from scratch.

[Follow-up from CARD-006 review, cycle 1] `tests/test_timeout.py` has three tests sharing one
fixture case (`size=50, density=50, seed=7` at a scaled 0.25s budget) to exercise the
"solver cannot finish in time" path. If this card's search strengthening makes that specific
case finishable within 0.25s, all three will break together, and the failure will look like a
timeout-mechanism regression rather than "the fixture got easy — pick a harder one." Check
this before concluding CARD-006's mechanism broke.
