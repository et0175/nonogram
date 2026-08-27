# CARD-004: Nonogram solver with fail-fast uniqueness check

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/004-solver-uniqueness
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 3
**Depends on:** CARD-002
**Touches:** src/nonogram/solver/__init__.py, src/nonogram/solver/propagate.py, src/nonogram/solver/search.py, tests/test_solver.py, tests/property/test_solver_uniqueness.py, tests/helpers/brute_force_oracle.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-005 (Solver) — the card the whole increment plan is ordered around. The handoff puts
it first because the riskiest open question is whether the hand-rolled solver is actually
correct; this card is where that is settled empirically rather than argued.

1. **Constraint propagation + backtracking (ADR-0009).** Hand-rolled, no third-party solver.
   Line-logic propagation to a fixed point, then branch on the most constrained undecided
   cell. Internal line representation is the int bitmask of ADR-0012 (the performance
   mechanism NFR-001's p95 target relies on); the public API stays in the boundary type.
2. **Solution counting with fail-fast (FR-006).** Report `0`, `1`, or `>=2`. On finding a
   second distinct solution, stop immediately — do **not** enumerate the rest. This is what
   makes the uniqueness check affordable inside CARD-005's retry loop.
3. **Purity (ADR-0007).** The solver is a pure function of clues: no filesystem, no CLI, no
   global state. That purity is precisely what makes EC-001's property test cheap to run at
   scale with no fixtures.
4. **Difficulty signal hooks.** Return the internal states CARD-009 will normalize into a
   score (cells solved by line-only logic before the first branch, backtracking amount,
   solve time). Emit them as part of the solve result now so CARD-009 does not have to
   reopen the solver's control flow later — but do not score anything here.
5. **Brute-force reference oracle (ADR-0014)** as a test helper in
   `tests/helpers/brute_force_oracle.py`: exhaustive enumeration for small grids, used only
   by the property test. It is the oracle, not a production path.

## Acceptance criteria

- **AC-015** (happy) — given clues with exactly one valid solution, when the puzzle is
  solved, then the solver reports `solution_count = 1` and returns that solution grid.
  *test:* `TestSolver_ReportsUniqueSolution`
- **AC-016** (negative) — given clues with zero valid solutions (a contradictory clue set),
  when the puzzle is solved, then the solver reports `solution_count = 0` and no solution
  grid is returned.
  *test:* `TestSolver_ReportsUnsolvable`
- **AC-017** (boundary) — given clues admitting more than one valid solution, when the puzzle
  is solved, then the solver stops immediately after finding a second distinct solution and
  reports `solution_count >= 2`, without enumerating every solution.
  *test:* `TestSolver_FailsFastOnSecondSolution`

## Engineering constraints

- **EC-001** (consistency, instances: AC-015) — The solver never reports
  `solution_count = 1` for a clue set that actually has 0 or more than 1 solutions, for any
  input clue set (the uniqueness check must never produce a false positive).
  *test:* `PropertyTest_Solver_NeverFalsePositiveUniqueness`
  This is a genuinely multi-case property test, not an example test: generate random grids
  up to 8x8, derive their clues (CARD-002), and cross-check the solver's verdict against
  ADR-0014's brute-force oracle. The increment-1 checkpoint requires ≥1000 cases passing.
  CON-005 makes it the one mandatory correctness property of the whole tool.

## Guardrails

- G-1: Hand-rolled solver only — do not introduce a third-party solver, SAT/CP library, or
  any dependency beyond the ADR-0006 baseline (ADR-0009 rejected the library route; ADR-0006
  closed the dependency baseline)
- G-2: `src/nonogram/solver/**` stays a pure function of clues — no filesystem, no CLI
  imports, no module-level mutable state (ADR-0007). The property test must need no fixture
- G-3: Do not edit `src/nonogram/clues.py` — CARD-002's deliverable. The solver consumes the
  clue API; the internal bitmask representation is private to `solver/` and must not leak
  back into the clue module's public type (ADR-0012)
- G-4: Do not edit `src/nonogram/cli.py`, `src/nonogram/orchestrator.py`,
  `src/nonogram/sourcing/**`, `pyproject.toml` — outside this card's footprint
- G-5: Out of scope — no difficulty scoring (FR-009, CARD-009), no timeout/deadline
  enforcement (ADR-0011, CARD-006), no retry loop (FR-007, CARD-005). This card emits the
  signals and exposes the propagation fixed points those cards hook into; it does not
  consume them

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-006
- **NFR:** NFR-001 (partial — the bitmask representation is the performance mechanism)
- **CON:** CON-005 (mandatory)
- **EC:** EC-001
- **ADR:** ADR-0009, ADR-0011, ADR-0012, ADR-0014
- **Components:** COMP-005 (Solver)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Follow-up from CARD-002 review, cycle 1] `nonogram.clues.clue_matches_line` is a
per-cell, tuple-allocating equality check meant for validating a COMPLETE line against
a clue (e.g. export/orchestrator-level checks) — do NOT call it inside this card's hot
propagation loop. ADR-0012 fixes the solver's internal state as bitmask ints specifically
to avoid per-cell overhead at the "millions of intersections per generation run" scale;
`clue_matches_line` reintroduces exactly that. It is also unsafe for PARTIAL lines: it
reads any falsy/truthy value as empty/filled with no type check, so an unknown-cell
sentinel fed into it silently mismatches rather than erroring. If this card needs a
line-vs-clue check during propagation, implement it natively against the bitmask
representation; if it needs a POST-HOC full-line sanity check, `clue_matches_line` is
fine for that narrower use only.

[Follow-up from CARD-002 review, cycle 2] The same caveat applies to `clues.encode_line`
itself, not just `clue_matches_line`: its docstring still says it "accepts any iterable
of truthy/falsy cells so the solver's line logic can pass a generator or a transposed
column," which invites the identical partial-line misuse (a `None`/unknown-cell sentinel
is silently read as falsy/empty, not rejected). Do not feed partial lines to
`encode_line` either — both functions are scoped to complete lines only.

---

### Implementation summary (CARD-004, this worktree)

`src/nonogram/solver/` is a pure function of clues: `solve(row_clues, column_clues)` ->
`SolveResult(solution_count, solution, signals)` with `solution_count` in `{0, 1, MANY}`
where `MANY == 2` reads as ">= 2". Line logic runs to a fixed point, then the search
branches on the most constrained unknown cell and backtracks, stopping the instant a
second distinct solution is recorded. Boundary types only at the seam (clue tuples in,
`list[list[bool]]` out); bitmasks never leave `solver/` (G-3).

Both CARD-002 review notes were honoured: neither `clue_matches_line` nor `encode_line`
is called anywhere in `solver/`. All three-valued line reasoning is native to the
bitmasks, and even the post-hoc full-line check is native (see STRUCTURE-5 for why the
post-hoc use the notes *do* permit was still not taken).

Test results (`./.venv/bin/python -m pytest -q`, Python 3.14.3): **534 passed, 0 failed,
3.7 s for the whole suite** — 32 of those tests are this card's (`tests/test_solver.py`
plus `tests/property/`), 3.3 s of that time.

- AC-015 `test_reports_unique_solution` (+ `_that_needs_backtracking`,
  `_for_an_all_empty_grid`, `_for_an_all_filled_grid`, `test_solution_grid_is_not_transposed`)
- AC-016 `test_reports_unsolvable` (+ `_when_the_filled_totals_disagree`,
  `_only_after_searching` — the last pinned at 0 by an exhaustive 2^16-grid enumeration)
- AC-017 `test_fails_fast_on_second_solution` — a 12x12 all-`(1,)` clue set whose
  solutions are the 12! = 479,001,600 permutation matrices; the solver returns `MANY`
  after 11 branch nodes in ~3 ms (asserted: < 200 branch nodes, < 1 s)
- EC-001 `test_never_false_positive_uniqueness` — **2400 cases** (>= the 1000-case
  checkpoint, asserted in the test itself), sizes 1x1..8x8, every case cross-checked
  against the ADR-0014 brute-force oracle. Verdict mix: 1380 unique / 758 unsolvable /
  262 ambiguous. **Runtime 1.33 s.** Plus `test_finds_the_source_grid` (ADR-0014's
  free direction, 0.10 s). An additional 3000 cross-checks at a different seed were run
  outside the suite during development: 0 mismatches.

### Structural decisions

**STRUCTURE-1: two modules behind one `__init__` — `propagate.py` (line logic + board
state) and `search.py` (branching, counting, public API) — because the two halves fail
differently.** Line logic is a pure per-line deduction that is exhaustively checkable
against enumeration (`test_line_intersection_agrees_with_exhaustive_enumeration`); the
search is a control-flow problem where fail-fast and signal accounting live. Keeping them
apart means the DP can be tested without constructing a search, which is where the
subtle placement bugs ADR-0009 warns about actually are. `__init__.py` re-exports only
`solve`, `SolveResult`, `SolveSignals`, `MANY` — the surface CARD-005/CARD-009 may bind
to; anything else moving is not a breaking change.

**STRUCTURE-2: two ints per line, both orientations kept in parallel, bit `i` = cell `i`
— ADR-0012's representation with its "parallel masks" option rather than a transpose.**
`Board` holds `row_filled/row_empty` (indexed by row, column bits) and
`column_filled/column_empty` (indexed by column, row bits). A cell set in neither mask is
unknown; set in both is a state the code never constructs. Transposing the board on every
column pass was rejected because a propagation step only touches the handful of cells it
just decided, so pushing those bits into the perpendicular masks is O(changed cells)
where a transpose is O(n^2) per sweep. Two derived fields ride along: `decided` (running
count of known cells — FR-009's line-logic signal would otherwise cost a popcount sweep
per pass) and `row_placements/column_placements` (see STRUCTURE-4). Backtracking is four
shallow list copies of <= 50 immutable ints, which is ADR-0012's "undo is essentially
free" consequence taken literally.

**STRUCTURE-3: line logic is a bottom-up DP over `(position, run index)` returning
`(forced_filled, forced_empty, placement_count)` or `None`.** From each state a placement
either leaves the current cell empty or starts the next run exactly here, so every
placement is exactly one path and OR-ing each transition's masks yields the union over
*all* placements without enumerating any (a 50-cell line can have >10^13). Cells in the
filled union but never the empty union are forced filled, and vice versa. Evaluated as a
reverse loop rather than a memoised recursion after measurement: at these sizes CPython's
per-call overhead cost several times the arithmetic it wrapped. Three fast paths carry
their weight: the runs-do-not-fit reject, the empty-clue case, and the fully-decided line
(checked with `mask_runs` in one pass — this fires constantly near the leaves). States
whose remaining cells cannot hold their remaining runs are skipped entirely, roughly
halving the state space on long many-run lines.

**STRUCTURE-4: propagation is a dirty-flag sweep to a fixed point; branching picks the
cell where the two lines through it have the fewest remaining placements, and tries the
better-supported value first.** A line is re-examined whenever anything writes into it,
so at the fixed point *every* line is known to admit at least one placement — which is
what makes "no unknown cells left" equivalent to "solved" without a separate verification
pass. "Most constrained" is measured in placements, not unknown cells: a 50-cell line
with twenty unknowns and two placements is one guess from settled, while four unknowns
and six placements is not. The counts are cached on the `Board` by the same DP that
deduced the cells, so the heuristic is a scan of two int lists. Value ordering (try the
value whose row and column still admit more placements) costs two extra line DPs per node
and only reorders work — both values are always tried, so it cannot change the count.
Measured on random 20x20 grids at 30% density, the two heuristics together took the worst
observed case from >5 s (unknown-cell counting, filled-first) to 0.089 s. The search uses
an explicit stack, not recursion: guess depth is bounded by cell count (2500 at 50x50),
which would blow CPython's default recursion limit on a pathological puzzle.

**STRUCTURE-5: the CON-005 self-check re-encodes finished lines natively
(`propagate.mask_runs`) instead of calling `clues.compute_clues`.** The plan was the
post-hoc full-line check the CARD-002 notes explicitly permit — but `tests/test_cli.py`
(CARD-001's ADR-0007 guard) fails any lateral import between capability modules, and
`clues` is COMP-004's capability, not a shared kernel. `solver/` therefore consumes the
clue *contract* (ADR-0012's boundary tuples) without importing the clue *module*. This
costs the self-check its independence, so two things compensate: `mask_runs` is pinned
against `clues.encode_line` for all 256 length-8 lines from the test tree, where the
import is legal, and the real independent evidence is EC-001's oracle cross-check, which
is external by construction. Note the tension for the reviewer: the card's G-3 says "the
solver consumes the clue API", and at the module level ADR-0007 forbids exactly that.

**STRUCTURE-6: ADR-0011's deadline is not implemented, but its two hook points exist and
are documented in place** (top of the fixed-point sweep in `propagate`, and the branch
node in `search`). G-5 puts enforcement in CARD-006; ADR-0011's "Neutral" note asks that
whatever solver technique lands preserve those checkpoints, and it does — the check is a
single added line at each, with no restructuring.

**STRUCTURE-7: the test tree became a package.** `tests/__init__.py`,
`tests/helpers/__init__.py` and `tests/property/__init__.py` (docstring-only) were added
so `tests.helpers.brute_force_oracle` imports by name from both `tests/test_solver.py`
and `tests/property/`, without a `sys.path` prelude in a test file or a `conftest.py`.
This is the only deviation from the card's predicted **Touches**; `pyproject.toml` was
not touched (G-4) and no production file outside `src/nonogram/solver/` was either.

**STRUCTURE-8: the oracle enumerates line placements, not `2 ** (size * size)` grids —
and a second oracle enumerates the grids to check the first.** The card describes
exhaustive per-cell enumeration, which is 65,536 grids at 4x4 but 6.9e10 at 6x6; the
property test needs thousands of cases at 6x6 and above. `count_solutions` therefore
enumerates every pattern matching each row clue (brute force over `2 ** width`, filtered
through `clues.encode_line`) and walks the product, pruning on "is this partial column
the prefix of some fully enumerated column candidate" — a lookup in a set that was itself
built by brute force, so it provably cannot discard a solution. Still exhaustive, still
eyeball-checkable, and it shares no code with `nonogram.solver`. `count_solutions_by_cell`
keeps the literal reading and is capped at 16 cells (~0.2 s; 5x5 would be a minute, 6x6
days); `test_the_two_oracles_agree` runs them against each other. Practical caps:
by-cell 4x4, line-candidate oracle comfortable to 8x8 (typically 1-4 ms per clue set,
worst observed ~0.22 s on an unsatisfiable mutated 8x8).

### Performance findings — read before CARD-005/CARD-006

Not a blocker for this card (NFR-001 is only partial here, and enforcement is CARD-006's),
but the numbers matter for the cards that consume this one. Measured on this machine,
3 seeded random grids per cell, 5 s cut-off:

| size | density 30% | density 50% | density 70% |
|------|-------------|-------------|-------------|
| 12   | <0.01 s     | <0.01 s     | <0.01 s     |
| 20   | 0.02-0.09 s | <0.01 s     | <0.01 s     |
| 30   | 0.1 s / 1 cut-off | 0.1-0.2 s / 1 cut-off | <0.01 s |
| 40   | 2.7 s / 2 cut-off | all 3 cut off | ~0.01 s |
| 50   | 1.7 s / 2 cut-off | all 3 cut off | ~0.03 s |

Line-solvable grids are trivial at every supported size — a 50x50 at 70% density is
~30 ms with zero branching, and 10x10/20x20/30x30 round-trips are pinned as tests. What
is expensive is the known-hard class: random *mid-density* grids at 40x40 and up, where
line logic settles almost nothing (22 of 2500 cells on one 50x50 sample) and the search
has to grind. Propagation itself is sound there — a descent guided by the true grid
reaches the solution in 47-283 guesses with no false contradiction — the cost is in
rejecting the wrong subtrees. Consequences worth planning around:

1. CARD-006's ADR-0011 deadline is not optional at these sizes; without it a single
   candidate can run unbounded. The hooks are in place (STRUCTURE-6).
2. CARD-005's retry loop should expect `SolverTimeout` to be a *normal* outcome for
   mid-density 40x40+ candidates, not an exceptional one, and INV-003's bound must be
   able to absorb a run of them.
3. If 40x40+ generation turns out to abandon too often in practice, the lever is a
   stronger search (probing / limited lookahead), not a different representation —
   ADR-0012's masks are not the bottleneck; subtree rejection is.

This is also why the property corpus stops at 8x8 and the larger-size round-trip in
`tests/test_solver.py` is fixed at 75% density: until the deadline exists, an unlucky
mid-density grid would hang the suite rather than fail it.

### Review cycle 1 — fixes applied

The one Important finding was a stale docstring on `propagate.mask_runs`: it claimed
`search` "still verifies finished grids through `clues.compute_clues`", which is the
opposite of STRUCTURE-5 — `search._verified_grid` re-encodes natively *because*
ADR-0007 forbids `solver/` importing the `clues` capability module laterally, and
`tests/test_cli.py` fails any such import. Left alone, it invited a contributor to
"restore" an import that breaks CARD-001's guard. The docstring now states the actual
arrangement and its reason, and points at the test-tree pinning against
`clues.encode_line` as where the independence is bought back. Two Minors were taken as
well: a comment in `search.solve` on why the solutions list needs no duplicate check
(sibling branches are disjoint by construction — a frame fixes one cell that was
unknown at its node and tries both values in separate subtrees, so `MANY` really means
two *distinct* grids), and a directed test pinning `solution_count = 1` for a grid with
no cells, documenting that the ADR-0014 oracle's `0` there is its degenerate-dimension
shortcut and is unreachable from EC-001's 1x1..8x8 corpus. No production behaviour and
no oracle behaviour was changed. M-2, M-4 and M-5 were left as recorded (not gating).
`./.venv/bin/python -m pytest` — **535 passed, 0 failed, 3.7 s** (534 + the new test).

## Failure matrix

`solver/` is a pure function (ADR-0007, G-2): no filesystem, no network, no clock beyond
`perf_counter` for the FR-009 signal, no concurrency, no retries, no module-level mutable
state. There is no I/O boundary to enumerate — but "no I/O" is not "no failure-bearing
boundary", so the ones that exist are stated here rather than waved off.

| # | Boundary | Failure mode | Detection | Handling | Covered by |
|---|----------|--------------|-----------|----------|------------|
| F-1 | Clue set in (caller-supplied `tuple[tuple[int, ...], ...]`) | Malformed clue: a run <= 0, a bool, a non-int, or `0` alongside other runs | `canonical_clue` validates every run before any search starts | `ValueError` — deliberately *not* `solution_count = 0`: a typo reported as "unsolvable" would send CARD-005's loop into an endless regenerate cycle chasing a bug | `test_malformed_clues_raise_rather_than_reporting_unsolvable` |
| F-2 | Clue set in | Well-formed but unsatisfiable clues (contradictory, or contradictory only under search) | Line DP returns `None`, or the search exhausts every branch | Domain outcome, not an error: `solution_count = 0`, `solution = None` (AC-016) | `test_reports_unsolvable*` (3 tests), EC-001 corpus (758 zero-count cases) |
| F-3 | Search -> caller (the CON-005 boundary) | A completed grid that does not actually satisfy its clues — the false-positive uniqueness verdict CON-005 forbids | Every completed board is re-encoded from its masks and compared with the clues it was solved from, in both orientations, before it is counted | `RuntimeError` naming it a solver defect. Crashing loudly beats returning a wrong "unique" — this is the one failure the model rates mandatory | `test_never_false_positive_uniqueness` (2400 oracle cross-checks), `test_mask_runs_agrees_with_the_clue_module` |
| F-4 | Search -> caller | Missing a second solution (reports 1 when 2+ exist) — invisible to any self-check, since a solver cannot detect a solution it never found | Independent brute-force oracle (ADR-0014), test-time only | No runtime handling is possible by construction; mitigated by evidence, which is exactly why ADR-0014 exists | `test_never_false_positive_uniqueness` (262 ambiguous cases + 1380 unique ones), `test_the_two_oracles_agree` |
| F-5 | Search -> wall clock | Unbounded run time on a hard instance (see the performance table) | None *in this card* — G-5 assigns the cooperative deadline to CARD-006 | Deferred by design: the ADR-0011 hook points are in place; until then the caller sees a long-running call, never a wrong answer | Bounded sizes in the test corpus; STRUCTURE-6 |
| F-6 | Search -> memory / stack | Deep guess chains at 50x50 (up to 2500 levels) | — | Structural: the search is an explicit stack, so depth is heap-bounded rather than a `RecursionError` at CPython's default limit of 1000 | STRUCTURE-4 (design-level; no test forces 1000+ deep guessing) |

No rows for retries, timeouts-of-dependencies, partial writes, idempotency or concurrency:
this component calls nothing, writes nothing, and shares nothing.
