# CARD-006: Cooperative generation deadline and SolverTimeout

**Status:** blocked
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/006-cooperative-deadline
**Worktree:** ../PythonProject4-card-006
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 5
**Depends on:** CARD-004, CARD-005
**Touches:** src/nonogram/solver/propagate.py, src/nonogram/solver/search.py, src/nonogram/orchestrator.py, src/nonogram/errors.py, tests/test_timeout.py, tests/bench_generate.py
**Review score:** —
**Started:** 2026-08-28T08:42:21Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** escalated — architect: AC-037 (20x20 p95 ≤5s) genuinely unmet at 30-40% density (median hits the 30s cap); user chose to revisit ADR-0001's threshold rather than merge-and-defer or block on solver work

## What to implement

NFR-001's hard guarantee: a 50x50 request must **never hang**. Per ADR-0011 the mechanism is
a cooperative deadline, not a thread or a signal — the deadline is computed once by COMP-002
and checked inside COMP-005 at every propagation fixed point and every branch node.

1. **Deadline computation (COMP-002).** The orchestrator derives an absolute deadline from
   the request (30s hard bound up to 50x50 — ADR-0001) and passes it into every solver call.
   The deadline covers the whole generation request including regenerate retries, not each
   solve in isolation — otherwise 20 retries × 30s is a 10-minute "timeout".
2. **Cooperative checks (COMP-005).** At each propagation fixed point and each branch node,
   check the deadline and raise `SolverTimeout` when it has passed. Checks must be frequent
   enough that the observed overshoot is small, and cheap enough not to move the NFR-001
   p95 target for 20x20.
3. **Abandonment path.** The orchestrator converts `SolverTimeout` into the EVT-012
   abandonment path — a clean, clearly-worded failure with a non-zero exit code. Never a
   partial or unverified puzzle: INV-002 still holds, a timed-out puzzle is not exportable.
4. **Benchmark.** `BenchGenerate_20x20_p95Under5s` measures p95 completion for 20x20
   including regenerate retries. Keep it runnable and deterministic enough to be a gate
   (fixed seeds, fixed sample size); if p95 is not met, the finding is the deliverable —
   the fix belongs in the solver's propagation strength, not in loosening the threshold.

## Acceptance criteria

- **AC-037** (boundary) — given a 20x20 random-grid generation request under typical
  hardware, when generation runs, including any regenerate retries, then p95 completion time
  is ≤ 5s.
  *test:* `BenchGenerate_20x20_p95Under5s`
- **AC-038** (boundary) — given a 50x50 random-grid generation request (the largest
  supported size), when generation runs, then it completes within 30s or fails clearly with
  a `SolverTimeout` error (cooperative deadline enforced inside the solver — ADR-0011) — it
  never hangs indefinitely.
  *test:* `TestGenerate_50x50_RespectsTimeoutBound`

## Guardrails

- G-1: Do not edit `src/nonogram/export/**`, `src/nonogram/cli.py` — `export/**` is owned by
  CARD-007 this wave; the CLI flag surface is CARD-001's
- G-2: Solver semantics unchanged — this card adds deadline checks, it does not alter the
  propagation or search results. `PropertyTest_Solver_NeverFalsePositiveUniqueness`,
  `TestSolver_ReportsUniqueSolution`, `TestSolver_ReportsUnsolvable` and
  `TestSolver_FailsFastOnSecondSolution` must still pass unchanged
  (test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- G-3: No threads, subprocesses or signal handlers — the deadline is cooperative by decision
  (ADR-0011), and a preemptive mechanism would leave the `Puzzle` aggregate in an
  indeterminate state
- G-4: A timed-out puzzle is never marked ready for export (INV-002); the timeout path is an
  abandonment, not a degraded success
- G-5: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/clues.py`, `pyproject.toml` —
  outside this card's footprint

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** —
- **NFR:** NFR-001
- **INV:** INV-002
- **ADR:** ADR-0001, ADR-0009, ADR-0011, ADR-0012
- **Components:** COMP-002, COMP-005, COMP-003
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### Implementation summary (CARD-006, this worktree)

ADR-0011's cooperative deadline, end to end. `orchestrator.generate` derives one absolute
`time.monotonic()` instant per generation **request** and hands that same instant to every
`solver.solve` call the request makes, retries included; the solver checks it at ADR-0011's
two named checkpoints — the top of `propagate`'s fixed-point sweep and the top of `search`'s
branch loop — and raises the pre-existing `nonogram.errors.SolverTimeout` the moment it has
passed. No threads, no subprocesses, no signal handlers (G-3). Solver semantics are
untouched (G-2): the deadline is a keyword-only argument defaulting to `None`, and with
`None` no clock is read at all, so the solver stays the pure function ADR-0007 and the
EC-001 property corpus rely on.

Public surface added:

- `orchestrator.GENERATION_BUDGET_SECONDS = 30.0` — ADR-0001's hard bound, per request.
- `solver.solve(row_clues, column_clues, *, deadline=None)`.
- `solver.propagate.propagate(board, dirty_rows, dirty_columns, deadline=None)`.
- `solver.propagate.check_deadline(deadline)` — the whole mechanism, one function.

**Test results** (`./.venv/bin/python -m pytest`, Python 3.14.3): **636 passed, 1 failed**
(independently reconfirmed by the orchestrator after rebasing onto CARD-007). The one
failure is AC-037's benchmark and it is a genuine finding, not a defect in this card's work
— see "AC-037: p95 NOT met" below. The 582 pre-existing tests all pass; CARD-004's solver
tests (`TestSolver_*`, `PropertyTest_Solver_NeverFalsePositiveUniqueness`, AC-015/016/017)
pass **unchanged** — no file under `src/nonogram/solver/` changed behaviour for a caller
that does not pass a deadline, and `tests/test_solver.py` and `tests/property/` were not
edited at all.

### AC-038 — met (`tests/test_timeout.py::TestGenerate_50x50_RespectsTimeoutBound`)

Both halves of the criterion's "or", plus the two properties that make "never hangs" mean
something:

| test | what it shows | budget |
|---|---|---|
| `test_the_enforced_bound_is_adr_0001s_thirty_seconds` | the number in force is 30.0 | — |
| `test_a_50x50_request_the_solver_can_finish_completes_inside_the_bound` | a real 50x50 request returns a verified unique puzzle (~30 ms) | **real 30 s, unfaked** |
| `test_a_50x50_request_the_solver_cannot_finish_raises_solver_timeout` | the known-hard class stops with `SolverTimeout` | 0.25 s |
| `test_the_overshoot_past_the_deadline_is_small` | it stops *when* it should, not merely eventually | 0.25 s |
| `test_a_timed_out_request_yields_no_puzzle_at_all` + `..._never_ready_for_export` | INV-002 / G-4 | 0.25 s |

The hard case (`size=50, density=50, seed=7`) was independently verified against the **real
30 s budget** outside the suite: `SolverTimeout` after **30.0016 s** — i.e. the production
path genuinely reaches the deadline on real solver work and returns 1.6 ms past it. The
test scales the budget down only so the suite does not spend 30 s per run; ADR-0011 names
that affordance explicitly ("triggered deterministically in tests by injecting a
near-immediate deadline, with no reliance on real wall-clock waits"), and the 30.0 constant
is pinned by its own test so the substitution scales a checked number.

Measured overshoot: **~1 ms at 50x50 mid-density**, at both 0.25 s and 30 s budgets. ADR-0011
lists granularity as this mechanism's one negative consequence; in practice it is four
orders of magnitude below the budget.

**Abandonment path.** `SolverTimeout` propagates out of `run_bounded` untouched — it is
*not* converted to `GenerationAbandoned`, and not retried. That is deliberate and matches
the test a prior card pinned (`test_a_solver_timeout_is_not_treated_as_a_uniqueness_failure`):
retrying a timeout would spend a budget that has already expired, and ADR-0002's attempt
bound and ADR-0001's time bound are meant to operate "together but independently". EVT-012's
user-visible shape is already in place without touching `cli.py` (G-1): `cli._EXIT_CODES`
maps `SolverTimeout` to `ExitCode.GENERATION_FAILED` (4) and `main` prints
`nonogram: error: solver passed its generation deadline 0.001s ago and stopped without a
verdict (ADR-0011 cooperative deadline); the puzzle is abandoned, not accepted` to stderr.
INV-002 holds structurally: `confirm_uniqueness` is the only writer of `ready_for_export`
and the timeout path never reaches it.

### AC-037 — **NOT met. This is the finding, and it is the deliverable.**

`tests/bench_generate.py::test_20x20_p95_is_under_5s` **fails**, deliberately not softened.
Independently reconfirmed by the orchestrator after the rebase onto main (same 2-of-2
5s-cap timeouts at densities 30/40).

Uncensored measurement, 20 requests (densities 30/40/50/60 x seeds 0..4), real 30 s budget:

| density | seeds 0-4 | outcome |
|---------|-----------|---------|
| 30 | 30.000 s x5 | all five **timed out** |
| 40 | 30.000 s x5 | all five **timed out** |
| 50 | 0.006-0.134 s | 4 unique, 1 abandoned |
| 60 | 0.002-0.005 s | all unique |

**p95 (nearest-rank, n=20) = 30.000 s — and that is censored at the hard bound; the true
p95 is unbounded.** The median is also 30.000 s: *half* the corpus never finishes. Against
ADR-0001's 5 s cap this is not a near miss.

The split is entirely by density, and it is sharp:

- **densities >= 50%: AC-037 is met with enormous margin** (worst sample 0.134 s, ~37x under
  the cap). Line logic settles most of the board and the search barely runs.
- **densities 30-40%: the solver does not finish at all** within 30 s on most seeds. Per-solve
  instrumentation at 20x20/30%: `line_logic_cells = 0/400` on 11 of 12 candidates, and the
  search grinds through 5,000-7,000+ branch nodes with a ~98% backtrack rate before either
  finishing (2.4-4.1 s) or timing out.

This directly corroborates and *extends* CARD-004's own performance findings. That card
identified mid-density **40x40+** as the known-hard class and measured 20x20/30% at
0.02-0.09 s — but from only three seeded grids per cell. With 12 seeds the same cell splits
bimodally: 6 of 12 finish in under 0.06 s and 4 of 12 exceed 5 s. The hard class starts at
**20x20**, not 40x40; CARD-004's table under-sampled the tail rather than being wrong.

Per the card's own instruction and ADR-0009's "performance tuning at the upper end is our
problem to solve", **the threshold was not loosened and the corpus was not narrowed to the
easy densities.** The levers, for whoever picks this up:

1. **Solver propagation strength** (CARD-004's own recommendation #3 and ADR-0009's
   acknowledged cost): probing / limited lookahead, so a wrong subtree is rejected near the
   root instead of hundreds of levels down. CARD-004 already established that propagation is
   *sound* on these grids — a descent guided by the true grid reaches the solution in 47-283
   guesses — so the cost is entirely in rejecting wrong subtrees, not in the representation.
2. **Revisit ADR-0001**, which anticipated exactly this in its own Negative section: "if
   profiling after FR-006 is implemented shows the solver routinely takes longer than 5 s at
   20x20 ... this ADR will need to be revisited."
3. **Scope AC-037's density range.** AC-037 says "a 20x20 random-grid generation request"
   without naming a density, and `--density` has no CLI default — so "what density does a
   typical request use" is an open modelling question this card cannot answer alone. If the
   product's answer is ">= 50%", AC-037 is already met and the *requirement* should say so;
   if it is "any valid percentage", lever 1 is required.

This is a decision for the reviewer/orchestrator, not for the benchmark to make by picking a
friendlier corpus.

### Structural decisions

**STRUCTURE-1: the deadline is one function, `propagate.check_deadline`, imported by
`search` — not two inline comparisons.** Both checkpoints then raise the same error with the
same wording and read the same clock, and there is exactly one place to test, to patch in a
test, and to change if the granularity ever needs revisiting. It lives in `propagate.py`
rather than a new module because `search` already imports from `propagate` and ADR-0007's
layering test enumerates modules — a third solver module would be a decomposition change
this card has no reason to make.

**STRUCTURE-2: `time.monotonic` in the solver, `time.perf_counter` left alone in
`SolveSignals`.** The deadline is a value produced in `orchestrator` and consumed in
`solver`, so both ends must read the same clock, and ADR-0011 names the monotonic one.
`SolveSignals.elapsed_seconds` keeps `perf_counter`: it is a duration measured entirely
inside one call and never compared against anything from outside it.

**STRUCTURE-3: `deadline` is keyword-only with a `None` default, and `None` reads no clock.**
ADR-0011's second Negative consequence is that the deadline gets "threaded through the
solver's public signature, which every caller ... must now account for, even when they don't
care about timeouts". Defaulting it pays that down to nothing: not one line of
`tests/test_solver.py` or `tests/property/` needed to change. `None` short-circuiting before
`time.monotonic()` also keeps the solver a *strictly* pure function on the default path,
which is what CARD-004's purity tests and the fixture-free EC-001 corpus rely on — a test
pins that no clock is read (`test_a_deadline_never_reads_the_clock_when_it_is_none`).

**STRUCTURE-4 — the placement/frequency tradeoff, which is this card's central judgement
call.** The requirement pulls two ways: frequent enough that overshoot is small, cheap enough
not to move CARD-004's timing on the already-fast 10x10-30x30 line-solvable cases.

*Where the checks went.* Exactly ADR-0011's two boundaries, and one level up from the
obvious spot in each:

- **`propagate`: top of the outer `while pending` loop**, i.e. once per fixed-point *sweep* —
  not once per line inside the two `for` loops. A sweep is at most `height + width` line DPs
  (100 at 50x50, each O(length x runs)), which bounds a sweep's cost in the tens of
  milliseconds. Pushing the check into the per-line loops would multiply clock reads by ~100
  to buy back tens of milliseconds against a 30-second budget — invisible where it matters,
  and a real cost on grids that reach their fixed point in a handful of sweeps, which is the
  entire NFR-001 p95 population.
- **`search`: top of the `while stack` loop**, i.e. once per *guess attempt* — not on the
  `branch_nodes += 1` push. The expensive shape of a hard 50x50 is a long run of guesses that
  each hit an immediate contradiction and `continue` without ever pushing a frame; a check on
  the push alone would sit out precisely the search that most needs stopping. The loop top
  also covers the frame-pop iterations, which do no propagation at all and would otherwise be
  unchecked.

*Measured against both halves of the requirement.* Overshoot: **~1 ms** at 50x50 mid-density
(measured at 0.25 s and at the real 30 s budget) — the coarser granularity is not costing
anything observable. Cost: solve time with a far-future deadline versus `deadline=None`, best
of 7 runs over 8 grids per configuration —

| configuration | `deadline=None` | with deadline | delta |
|---|---|---|---|
| 10x10 @ 50% | 6.58 ms | 6.76 ms | +2.7% |
| 20x20 @ 50% | 90.10 ms | 85.87 ms | -4.7% |
| 20x20 @ 75% | 8.21 ms | 7.97 ms | -2.9% |
| 30x30 @ 75% | 22.79 ms | 23.31 ms | +2.3% |
| 40x40 @ 75% | 62.67 ms | 61.92 ms | -1.2% |
| 50x50 @ 75% | 126.44 ms | 121.79 ms | -3.7% |

Deltas land on both sides of zero at ±5%, i.e. inside run-to-run noise: the check is not
measurable on the fast path. (It could not be much else — one `monotonic()` call is ~50 ns
against a sweep costing microseconds to milliseconds.) A per-line check would have been a
different conversation; a per-sweep one is free.

**STRUCTURE-5: the deadline is derived per request, and the tests prove it rather than
assuming it.** `generate` computes `time.monotonic() + GENERATION_BUDGET_SECONDS` once,
before the first attempt, outside `attempt_candidate`. `test_every_attempt_in_one_request_shares_one_deadline`
records the deadline each of a 4-attempt run's solves receives and asserts all four are the
same float; `test_the_deadline_is_the_budget_measured_from_the_start_of_the_request` pins the
arithmetic. Without these, a future refactor moving the computation inside the closure would
silently turn a 30 s bound into a 20 x 30 s = 10-minute one with every test still green.

**STRUCTURE-6: the mechanism tests were mutation-checked, not just written.** Three mutations
were applied to the source and the suite re-run:

| mutation | caught by |
|---|---|
| delete the branch-node check | `test_the_search_checks_the_deadline_at_every_branch_node`, `test_the_branch_checkpoint_alone_stops_a_search_propagation_would_not` |
| delete the propagation check | `test_propagation_checks_the_deadline_at_every_fixed_point_sweep`, `test_propagation_stops_at_the_sweep_after_the_deadline_passes` |
| hoist the propagation check *out* of the sweep loop (still checked once, on entry) | the same two |

The third is the one that matters: a check on entry to `propagate` passes every "it timed
out" test while making "never hangs" false, because a single propagation that keeps finding
more to deduce would run unchecked. It is caught because the tests assert *where* and *how
often*, via a fake monotonic clock substituted for `propagate`'s `time` module, not merely
that an exception appeared.

**STRUCTURE-7: a fake clock, installed by rebinding `propagate.time` rather than patching the
stdlib.** `_FakeClock` stands still, then jumps past the deadline on a chosen read, and
counts reads. This is what makes "checked once per sweep" and "checked at every branch node"
*assertions* instead of statistical hopes.

**STRUCTURE-8: the benchmark censors at the cap and stops as soon as the verdict is settled.**
Two changes make it ~10 s without weakening it: per-request budget is set to the cap itself
(5 s, so an over-cap request is recorded as a censored lower bound, which costs the criterion
nothing since "p95 <= 5s" is decided by count-over-cap, never magnitude); the corpus stops
once a 2nd over-cap sample proves p95 > cap (nearest-rank nth = 19 of 20, so one failure is
tolerable, two is proof). Neither shortcut touches the threshold or the corpus composition.

**STRUCTURE-9: `tests/conftest.py` exists solely so `bench_generate.py` is collected.**
pytest's default `python_files` doesn't match that filename; widening it project-wide in
`pyproject.toml` is outside this card's footprint (G-5) and a decision about the whole test
tree. A `pytest_collect_file` hook adds exactly this one file.

### Scope

[Scope] Predicted Touches matched for solver/propagate.py, solver/search.py,
orchestrator.py, tests/test_timeout.py, tests/bench_generate.py. Three small, forced
deviations: errors.py NOT touched (SolverTimeout already existed); solver/__init__.py
docstring-only (stale signature otherwise); tests/conftest.py new (STRUCTURE-9,
new-file-near-scope, same kind as CARD-004's test-package __init__.py files);
tests/test_orchestrator.py two stub signatures widened to absorb the new deadline= keyword
(no assertion changed). export/**, cli.py untouched (G-1). sourcing/**, clues.py,
pyproject.toml untouched (G-5). orchestrator.py edit kept deliberately minimal/additive to
reduce conflict with CARD-007's parallel export wiring — confirmed by the orchestrator: the
rebase onto CARD-007's merge was clean, zero conflicts.

[Build gate] PASSED except one deliberate, honest finding — independently re-run by orchestrator after rebasing onto main (CARD-007 merged first): 636 passed, 1 failed (tests/bench_generate.py::test_20x20_p95_is_under_5s — AC-037 not met, see above). All 582 pre-existing tests pass unchanged; tests/test_solver.py (31) and tests/property/test_solver_uniqueness.py (2) independently re-run in isolation, confirmed unchanged pass counts (G-2 held).

[Escalated] 2026-08-28T12:40:00Z — AC-037 (20x20 p95 ≤5s) genuinely unmet at 30-40% density: p95 censored at the 30s hard cap (true p95 unbounded), median also 30s. Not a defect in this card — the deadline mechanism itself (AC-038) is solid and independently verified. Root cause is the solver's search strength at mid/low density (a CARD-004-adjacent gap, out of this card's scope per G-2). ADR-0001 itself anticipated this exact scenario in its own Negative-consequences section. User chose: escalate to architect to revisit ADR-0001's threshold, rather than (a) merge-and-defer to a follow-up solver-strength card, or (b) block the wave until the solver is strengthened first. Station: architect. Route: /forge:architect to revisit ADR-0001 (and possibly AC-037's density scoping), then re-run this card's benchmark against whatever the revised requirement says. Worktree and branch kept (card/006-cooperative-deadline, ../PythonProject4-card-006) — the deadline-mechanism implementation is not discarded, only the benchmark's pass/fail criterion is in question.
