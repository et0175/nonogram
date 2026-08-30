# CARD-018: Strengthen solver search to meet AC-037 at 20x20 mid/low density

**Status:** review
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
**Review score:** 9.0 (cycle 2/3)
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
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate/resample/nudge attempts) never exceeds its configured maximum bound (check: TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)

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

---

### Implementation summary (CARD-018, this worktree)

Three changes, all inside `src/nonogram/solver/`, in the order they matter:

1. **Probing replaces plain guessing at every search node (`search.py`).** At a stalled
   board the search now takes the most constrained unknown cells and, for each, tentatively
   assigns *both* values and propagates. A value whose propagation contradicts cannot appear
   in any solution, so the other one is **forced** — applied for real, with the probe's own
   propagated board kept, so nothing is recomputed. If both contradict, the node is refuted
   outright. Only when a whole pass forces nothing does the search branch, on the cell whose
   two probes propagated furthest, reusing the two boards the probes already built. This is
   the lever CARD-006's notes and ADR-0001's revision named: a wrong subtree is rejected at
   the node instead of hundreds of levels down.
2. **A per-solve memo for the line DP (`propagate.LineCache`).** Probing multiplies
   `line_intersection` calls by roughly ten, and sibling probes at one node re-ask
   ninety-eight of a hundred lines the *identical* question. Measured hit rate on a hard
   20x20: **89.5%** (1,514,543 lookups, 158,830 misses). Without it probing is a net loss;
   with it a hard solve is ~5x faster on top of the tree reduction. The memo is created in
   `solve()` and dies with the call — no module state (the property
   `test_solving_the_same_clues_twice_gives_the_same_answer` pins that), and `propagate`'s
   new `cache=` argument defaults to `None`, which is the pre-CARD-018 behaviour exactly.
3. **A restart schedule (`_SEARCH_ROUNDS`).** A round that exceeds its node limit is
   abandoned whole and re-run with a **wider probe and a larger limit**:
   `(8, 400) → (16, 1200) → (32, 3600) → (64, 10800)`, then the limit keeps tripling.
   Round 0 is undiversified — it follows the heuristic's own best branch, so ordinary
   puzzles are on the same short path they were on before. Later rounds spread the branch
   choice over the candidates probing found equally live, chosen by a hash of
   `(round, node)` rather than a random draw, so the solver stays deterministic and pure
   (ADR-0007). Because the limit grows without bound, a round eventually gets the whole
   tree, which is what keeps restarting **complete**.

Public API untouched (G-1): `solve(row_clues, column_clues, *, deadline=None)`,
`SolveResult`, `SolveSignals`, `MANY` are all as they were, and
`solver/__init__.py` was not edited at all. `LineCache`/`LINE_CACHE_LIMIT` are additions to
`solver.propagate`'s `__all__`, not to the package's re-exports.

**Why the restart schedule is in scope even though the card said "probing".** It is not a
second idea bolted on; it is what the probing measurements demanded. With probing alone,
26 of 439 sampled 20x20 candidates (5.9%) still exceeded 2s. A *randomised* depth-first
descent — no probing at all — found two distinct solutions for one of them in **0.05s**
where the probing search had run **300s** without finding any. That is the signature of a
heuristic getting stuck, not of a hard instance, and no single fixed heuristic escapes it:
each one has its own ~5% adversarial set. Restarting is the only lever that addresses it,
and widening the probe on restart addresses the *other* failure shape at the same time (see
the schedule comparison below).

### Why the pruning is sound (G-3) — the argument, before the evidence

Everything rests on one property `propagate` already had: **it only ever writes cells that
every placement of some line agrees on, given what is known, and it only ever returns
`False` when some line admits no placement at all.** So for any board `B`, every solution
extending `B` also extends the board propagation leaves behind, and `propagate(B) == False`
means no solution extends `B`. Given that, probing cell `c` with value `v`:

- **The probe contradicts.** Then no solution extends `B + (c = v)`. Every solution
  extending `B` assigns `c` one of exactly two values, so every one of them extends
  `B + (c = ¬v)`. Forcing `¬v` therefore discards nothing. Keeping the probe's *propagated*
  board discards nothing either: its extra cells are forced deductions from a board every
  remaining solution extends.
- **Both probes contradict.** No solution extends `B + (c = filled)` and none extends
  `B + (c = empty)`, so none extends `B`. Refuting the node discards nothing.
- **Neither contradicts.** Nothing is deduced and nothing is discarded. The two probe
  boards become the node's children, and their union covers every solution extending `B`
  precisely because they disagree only on `c`.

Every step a probing pass takes is one of those three, so **no branch that could still lead
to a valid solution is ever rejected.** Nothing new is *gained* either — the other half of
CON-005 — because a board is only counted as a solution after `_verified_grid` re-encodes
every finished line from its masks and compares it with the clue it was solved from, exactly
as before.

Branch ordering and restarts cannot change a verdict for a separate, weaker reason: **both
children of a branch are always explored**, so ordering only moves work in time; and **a
cut-off round is discarded whole**, never half-believed, so a partial exploration can never
contribute a count. A verdict is only ever taken from a round that finished on its own terms.

*One place the argument had a hole, found by testing and closed.* If a probing pass ever
finished with nothing forced *and* nothing to branch on, while the board still had unknown
cells, the node would have been silently treated as refuted — a solvable puzzle reported as
having no solutions. It is unreachable in production (an incomplete board has an unknown
cell, and the candidate ranking sees every unknown cell before taking its first
`probe_width`), but a probe width of 0 reaches it by slicing the candidate list to nothing,
and the first draft returned "dead" there. It now raises a `RuntimeError` naming itself a
solver defect, and `test_a_probe_that_cannot_branch_raises_instead_of_reporting_no_solutions`
pins that. This is the one bug this card's soundness work actually caught, and it was caught
by the differential test below, not by the argument.

### Evidence that it is sound, not just argued

| check | scale | result |
|---|---|---|
| `tests/property/test_solver_uniqueness.py` (EC-001, in-suite) | 2400 cases, 1x1..8x8, every one cross-checked against the ADR-0014 oracle | **0 mismatches** |
| Same oracle cross-check, **fresh seeds outside the suite** (101/202/303/404/505/606/707/808) | **24,000** further cases (8 seeds x 3000) | **0 mismatches**; verdict mix ~7,290 unsolvable / ~13,607 unique / ~3,103 ambiguous |
| Verdict invariance across search configurations, EC-001 corpus | 2400 cases x 5 configurations (probe width 1, probe width "all", restart after every node, tiny limits, one unbounded round) | **0 differing verdicts** |
| Verdict invariance at sizes the property corpus omits | 240 grids 10x10..16x16 x 5 configurations, plus a round-trip check that every unique verdict returns the source grid | **0 differing verdicts, 0 bad grids** |

The invariance checks matter more than their size suggests: EC-001's corpus stops at 8x8,
where almost nothing is large enough to reach a restart, so the diversified branch path
would otherwise have been **untested by the mandatory property**. Shrinking the schedule
instead of growing the puzzles is what puts every one of those 2400 cases through it. Both
invariance checks are now in `tests/test_solver.py` as
`test_the_verdict_does_not_depend_on_probe_width_or_restarts`.

### Fresh measurements

All on this machine, Python 3.14.3, `deadline` set as noted. "Before" is this branch's
merge base (CARD-004's search + CARD-006's deadline).

**Per-solve, 20x20, uncensored (300s budget), the six seeds CARD-006 sampled.**

| density / seed | before | after | before branch nodes | after branch nodes |
|---|---|---|---|---|
| 30 / 1 | 13.108s | **0.050s** | 16,854 | 76 |
| 30 / 3 | 11.250s | **0.058s** | 17,862 | 73 |
| 40 / 0 | 97.844s | **1.954s** | 133,913 | 1,646 |
| 40 / 4 | 28.610s | 0.4s-class | 59,296 | — |

**Whole requests, CARD-006's exact benchmark corpus, uncensored at the real 30s budget** —
directly comparable to the table in CARD-006's own notes:

| density | before (CARD-006) | after |
|---|---|---|
| 30 | 30.000s x5, **all timed out** | 1.440 / 2.132 / 1.257 / 2.569 / 1.317s — **all completed** (abandoned after 20 candidates) |
| 40 | 30.000s x5, **all timed out** | 30.003 timeout / 30.002 timeout / 25.546 / 29.946 / 13.095s |
| 50 | 0.006-0.134s | 0.006-0.176s |
| 60 | 0.002-0.005s | 0.002-0.005s |

p95 (nearest-rank, n=20) is still censored at the cap, because 2 of 20 samples exceed it —
but the *median* moved from 30.000s (half the corpus never finished) to **0.06s**.

**The full 10-90% sweep AC-037 actually asks about**, censored at the 5s cap exactly as the
benchmark does (`GENERATION_BUDGET_SECONDS = 5.0`, so an over-cap request is a censored
lower bound), 5 seeds per density:

| density | request times (s) | over cap |
|---|---|---|
| 10 | 2.88 2.05 2.54 2.37 2.55 | 0/5 |
| 20 | 1.47 1.62 1.59 1.52 1.98 | 0/5 |
| 25 | 1.50 1.91 1.36 1.64 1.46 | 0/5 |
| 30 | 1.63 2.46 2.50 4.67 2.82 | 0/5 |
| 32 | 3.82 **5.00+** 3.57 3.20 2.85 | 1/5 |
| 35 | **5.00+ x5** | 5/5 |
| 38 | **5.00+ x5** | 5/5 |
| 40 | **5.00+ x5** | 5/5 |
| 42 | **5.00+ x4**, 3.11 | 4/5 |
| 45 | 0.28 **5.00+** 0.84 1.73 0.81 | 1/5 |
| 48 | 0.13 0.40 0.30 0.07 0.04 | 0/5 |
| 50 | 0.06 0.06 0.18 0.02 0.01 | 0/5 |
| 60 | <=0.01 | 0/5 |
| 70 / 80 / 90 | <=0.01 | 0/5 |

Before this card the same sweep timed out at the **30s** cap on 3 of 5 seeds at density 10,
2 of 5 at 20, 1 of 5 at 30 and 4 of 5 at 40 — i.e. the gap was never only "30-40%" as
CARD-006's four-density corpus suggested; it reached down to 10%. That part is now closed.

**No regression on the fast path** (best of 7 over 8 seeded grids each; the CARD-006 column
is that card's own table, measured the same way):

| configuration | CARD-006 | after |
|---|---|---|
| 10x10 @ 50% | 6.58 ms | 3.57 ms |
| 20x20 @ 50% | 90.10 ms | 69.20 ms |
| 20x20 @ 75% | 8.21 ms | 7.64 ms |
| 30x30 @ 75% | 22.79 ms | 23.79 ms |
| 40x40 @ 75% | 62.67 ms | 63.73 ms |
| 50x50 @ 75% | 126.44 ms | 125.91 ms |

Line-solvable grids never branch, so they never probe: they are unchanged, as they should
be. The two configurations that do branch got faster.

### AC-037: the `xfail` was **narrowed, not removed** — and exactly which band remains

Per the card's instruction and G-5, the marker stays and only its `reason=` text changed.
`strict=True`, the censoring mechanics, the early stop, the corpus, the rank and the
threshold are all untouched (the diff to `tests/bench_generate.py` is the reason string and
nothing else).

**Met now, across the whole seed set:** densities **10-32%** and **45-100%**.
**Still unmet:** roughly **32-45%**, worst at **35-42%**, where a 20x20 request runs
13-30s+ against a 5s cap. The benchmark's own corpus (30/40/50/60) therefore has its
density-30 column newly green and its density-40 column still red, which is why the gate
still fails and the marker still belongs there.

**Why the residual band is where it is, and why more of the same would not close it.** At
35-42% a random 20x20 sits at the uniqueness phase transition: candidates have very few
solutions, so a request pays for near-exhaustive refutation on each of up to 20 candidates.
The shape is a heavy tail, not a uniform slowdown — at density 35, 18 of 20 candidates
finish in under 0.5s and two take 4.3s and 9.6s. Two candidates were checked directly to
separate "hard for this heuristic" from "hard in itself": **200 randomised depth-first
restarts of 3,000 nodes each — 600,000 nodes, with the branch order rerolled every time —
found zero solutions** for either. Instances that survive that are not waiting on a better
branch heuristic. Closing this band needs a different class of inference (clause learning,
or a line-placement encoding handed to a real CP/SAT engine), which is an ADR-scale decision
about ADR-0006's closed dependency baseline, not a tuning pass.

Time is now dominated by `line_intersection` itself (55% of a hard solve after memoisation,
88% before it), so the remaining constant-factor headroom in pure Python is small — well
under the 3.6x that density 35 alone would need, and far under what 40% would.

**Schedule tuning is not the missing piece either**, and it was measured rather than assumed.
On the 26-instance corpus of candidates probing alone could not finish, the shipped schedule
`(8,400)(16,1200)(32,3600)(64,10800)` left **1** unfinished at 15s against **7** and **5**
for two other width/limit ladders. At whole-request level over densities 32/35/40/42 x seeds
0-2 (15s cap): shipped **121.3s total, 6/12 over cap**; a faster-bailing ladder
`(8,150)(24,600)(48,2400)(96,9600)` **101.6s, 5/12**; a wider-earlier one
`(8,300)(32,900)(64,2700)(128,8100)` **123.4s, 6/12**. The faster-bailing ladder wins on
total but regresses a case that the shipped one keeps at 5.7s to over 15s — sign-mixed on 12
samples, and decisively behind on the 26-instance corpus. Not worth trading a validated
ladder for.

**The two ingredients are both load-bearing.** On the same 26-instance corpus: restarting
that re-runs the *same* branch order settles none of them (by construction — it revisits the
same nodes) and left 13 of 26 unfinished at 20s; restarting with a diversified order left
**5**; adding the widening probe to that left **1**. At whole-request level, in the same
32/35/40/42 x seeds 0-2 comparison, disabling restarts entirely (one unbounded round of
probing at width 8) costs **159.3s total, 9/12 over cap** against the shipped schedule's
**121.3s, 6/12** — so the restart ladder earns its complexity even inside the band it does
not close. Probing without restarts is what produced the 26 in the first place.

### `test_timeout.py` fixture check (CARD-006's follow-up note) — checked, not assumed

CARD-006's notes warned that if this card's work made `size=50, density=50, seed=7`
finishable inside the scaled 0.25s budget, all three tests sharing that fixture would break
together and would *look* like a deadline-mechanism regression. Checked explicitly:

- at the scaled **0.25s** budget: `SolverTimeout` after **0.2502s** — still unfinishable,
  overshoot still ~0.2ms;
- at the real **30s** budget: `SolverTimeout` after **30.0002s** — still unfinishable on real
  solver work, i.e. the fixture is nowhere near the boundary, not merely on the right side of
  it;
- `tests/test_timeout.py` in isolation: **16 passed**, including all six AC-038 tests.

So the fixture did **not** get easy and needs no replacement. That is unsurprising in
hindsight: a mid-density 50x50 is orders of magnitude beyond a mid-density 20x20, and this
card's gains are largest exactly where the tree was small enough for probing to collapse it.

### Test run result

`./.venv/bin/python -m pytest` (fresh venv, Python 3.14.3): **1164 passed, 1 xfailed,
0 failed** — the xfail being AC-037's benchmark, narrowed as described above.

- `tests/property/test_solver_uniqueness.py` — the mandatory EC-001 property — passes; run
  repeatedly and, additionally, cross-checked against the ADR-0014 oracle over 24,000 further
  cases at eight fresh seeds outside the suite: **0 mismatches**.
- `tests/test_solver.py` — AC-015/016/017 pass **unchanged**; 8 tests added (probe/restart
  verdict invariance x4 configurations, restart-schedule completeness, the "cannot branch"
  defect guard, the `backtracks` signal, and the line memo's fidelity to the DP).
- `tests/test_timeout.py` — AC-038 passes, see the fixture check above.
- `tests/bench_generate.py` — `test_20x20_p95_is_under_5s` XFAIL (strict, so it is still a
  real gate that will fail loudly the day it starts passing); the benchmark's own two
  contract tests pass.

### Scope

[Scope] Predicted Touches matched for `src/nonogram/solver/search.py`,
`src/nonogram/solver/propagate.py`, `tests/bench_generate.py`, `tests/test_solver.py`.
**One deviation, flagged rather than done silently:** `tests/test_timeout.py` — its
`_blind_propagation` test double reimplements `propagate`'s signature, so it had to grow the
new `cache=` keyword and forward it. Signature-only; not one assertion, threshold or fixture
was touched, and this is the same kind of change CARD-006 itself made to
`tests/test_orchestrator.py` for the `deadline=` keyword. Guardrail G-4's files
(`orchestrator.py`, `cli.py`, `export/**`, `sourcing/**`, `clues.py`, `pyproject.toml`) are
all untouched, as is `src/nonogram/solver/__init__.py` (G-1).

### Orchestrator notes

- **[Scope]** Independently confirmed: touched files exactly match predicted
  plus the one flagged `tests/test_timeout.py` deviation (signature-only,
  verified by reading the diff directly). G-1/G-4 confirmed clean (empty
  diff on `solver/__init__.py`, `orchestrator.py`, `cli.py`, `export/**`,
  `sourcing/**`, `clues.py`, `pyproject.toml`). `bench_generate.py`'s diff
  confirmed to be the `reason=` string only — `strict=True` and all
  censoring/early-stop/corpus/rank/threshold mechanics untouched (G-5).
- **[Build gate]** PASSED (full, independently re-run by orchestrator in a
  fresh venv: 1164 passed, 1 xfailed, exit 0). The mandatory property test
  independently re-run 3 additional times (deterministic per house style —
  seeded `random.Random`, not flaky-random). Independently reproduced one
  headline performance number from scratch (20x20/density30/seed1): 0.049s,
  matching the implementer's claimed 0.050s exactly.
- **[Guard]** Implementation work was present but uncommitted in the worktree
  (`git log main..HEAD` empty; six files modified in the working tree,
  matching the documented summary exactly). Committed on `card/018-solver-
  search-strength` as `935e69f` before entering the review cycle.
- **[System contract]** section stale — refreshed from the model:
  +INV-002, +INV-003 (`system_rules.py --card CARD-018`; their scope globs
  include `src/nonogram/solver/**.py`, which this card touches). CON-005/
  INV-001 unchanged.
- **[Scope]** Independently confirmed: `excess` = `tests/test_timeout.py`
  outside the card's `Touches:` (1/5 changed files, ~20%, below the ~25%
  GROWN threshold); `comp_spread` = 0 (the file matches no additional
  component's `code:` glob in trace.yml — COMP-005 is `src/nonogram/
  solver/**.py` only). No ready sibling cards to poach from. Verdict:
  IN_SCOPE.
- **[Review 1/3]** Score: 6.5 — crit: 0, imp: 3. Report:
  `meta/review/20260830T094818Z-CARD-018-cycle1.yml` (synced from worktree).
  System contract: 4/4 rules ✓ holds (CON-005, INV-001, INV-002, INV-003) — no
  violations. Findings: F-001 `branch_nodes`/`backtracks` silently redefined,
  ADR-0013's difficulty formula reads the stale meaning (violates: G-1);
  F-002 unconditional probing regresses 20x20 low-density by 5-6x (violates:
  NFR-001); F-003 the xfail reason's density-10 "before" number doesn't
  reproduce and hides F-002's regression. No Critical findings.
- **[Review sync]** 1 report(s) → meta/review/.
- **[Adversarial]** F-001 CONFIRMED — independent skeptic re-derived the meaning
  change directly from `search.py`/`difficulty.py` (branch_nodes now counts every
  popped node incl. probe-refuted/settled, accumulates across abandoned restart
  rounds; backtracks counts forced deductions too), confirmed ADR-0013/difficulty.py
  docstrings still state the old meaning, confirmed no test's assertion would catch
  either change.
- **[Adversarial]** F-002 CONFIRMED — independent skeptic reproduced a 2.6x-8.5x
  regression on isolated 20x20 low-density `solve()` calls (best-of-3, module
  identity asserted per-subprocess) and confirmed the mechanism: round 0's
  unconditional 16-probe pass has no density-aware fast path.
- **[Adversarial]** F-003 CONFIRMED — independent skeptic re-benchmarked density-10
  on `main` (5 seeds, ~0.35-0.42s each, `GenerationAbandoned`, 0/5 near either cap),
  contradicting the xfail reason's and the card's own "used to time out" claim.
- **[Review 1/3]** 0 CONFIRMED critical, 3 CONFIRMED important → severity gate
  blocks success regardless of score. Entering fix cycle 1.
- **[Fix 1] declarations** — commit `d7a9ec9` (new commit; `935e69f` intact).
  F-001 resolved by option (b): the widened `branch_nodes` meaning is KEPT and
  all three declaration sites updated (`SolveSignals` docstrings,
  `difficulty.SolverSignals` protocol docstring, ADR-0013 dated History
  addendum). Option (a) was attempted first and rejected on evidence — narrowing
  to guesses-only reports `0` for a search that was entirely forced deduction,
  scoring real work as free, and broke 3 tests. Two genuine bugs fixed either
  way: `_Counters` is now rebuilt per restart round (no summing across abandoned
  rounds), and a double-refuted node counts 2 backtracks, not 1. New test
  `test_the_signals_count_the_deciding_round_and_nothing_else` fails against
  cycle-1 behaviour.
  F-002 resolved by making round 0 NON-probing (`_descend`, the pre-CARD-018
  heuristic with the sibling deferred as `_Pending`) rather than by weakening
  probing: `_SEARCH_ROUNDS` is now (no probe,400) → (8,400) → (16,1200) →
  (32,3600) → (64,10800). Density 10 is now 0.26-0.29s — BELOW the pre-card
  0.34-0.38s. Hard band 32-42% unregressed (A/B at 15s: 6-of-12 over cap both
  ladders). Whole-sweep over-cap count 39/80 (before) → 22/80 (now).
  F-003 corrected in place with verified numbers in both the xfail `reason=`
  and the card's own tables/prose, including both reading hazards the review
  named (10-32% are *abandoned* requests; 32% sits in threshold noise).
- **[Scope]** ⚠ Fix cycle 1 edited two files outside the card's `Touches:`
  — `src/nonogram/difficulty.py` (ONE protocol docstring) and
  `meta/architecture/decisions/adr/0013-difficulty-scoring-formula.md` (appended
  History note, Decision text untouched). Both verified documentation-only, no
  behaviour or formula change. Directed deliberately by the fix instruction as
  F-001 option (b)'s "update all three declaration sites" — the review had filed
  the `difficulty.py` half under Out-of-scope observations for a follow-up card,
  so this is a conscious in-card resolution instead, recorded rather than
  silent. G-4's forbidden set (`orchestrator.py`, `cli.py`, `export/**`,
  `sourcing/**`, `clues.py`, `pyproject.toml`) remains untouched — independently
  verified via `git diff --name-only 935e69f..HEAD`.
- **[Build gate]** PASSED (full suite, fix agent): 1165 passed, 1 xfailed, 0
  failed, exit 0. The +1 vs cycle 1 is the new signals test; the xfail is
  AC-037, still `strict=True`. EC-001 property passes, plus 12,000 fresh
  out-of-suite oracle cases (0 mismatches) and 240 grids x 5 configurations
  including the cycle-1 ladder (0 differing verdicts).
- **[Review 2/3]** Score: 9.0 — crit: 0, imp: 0 ✓ threshold reached + no
  critical/important. Report:
  `meta/review/20260830T111102Z-CARD-018-cycle2.yml` (synced from worktree).
  CONFIRMATION MODE, but **0 verdict lines carried** — the reviewer's own
  intersection check found every rule's scope covers `solver/**.py` and/or
  `difficulty.py`, both in the fix delta (CON-005 is `scope: global`), so all 4
  system rules and all 5 guardrails were re-verified from scratch.
  System contract: 4 rules checked, 4 ✓ holds, 0 ⚠ unchecked, 0 ✗ violated.
  All three cycle-1 findings independently re-derived as RESOLVED, not accepted
  on the fix agent's claims: F-001 verified by tabulating the actual increment
  sites against the docstrings (1 site for `branch_nodes`, 5 for `backtracks`)
  and by a scratch-copy revert experiment proving the new test fails on the old
  behaviour (`assert 21 == 7`); F-002 verified by the reviewer's own three-tree
  interleaved measurement (density 10: merge base 0.346-0.380s → cycle 1
  1.489-2.247s → now 0.266-0.288s, i.e. ~1.3x faster than pre-card) plus the
  discriminating hard-band A/B (cycle-1 ladder 8/15 over cap vs shipped 7/15 —
  the statistic AC-037 decides on does not regress); F-003 verified against the
  merge base. G-3's `_Pending` soundness re-derived from the code, including the
  load-bearing clone-before-propagate premise the fix agent's own argument had
  omitted.
  3 Minor findings, none gating: the new regression test pins 1 of 3 counter
  changes; no in-suite configuration exercises `_descend`/`_Pending` past round
  0's budget; one non-reproducing superlative ("fastest point on the whole
  sweep") survives inside the corrected xfail `reason=`.
- **[Review sync]** 1 report(s) → meta/review/.
- **[8h spot-check]** 3/3 sampled holds reproduced (CON-005, INV-002, INV-003)
  by an independent skeptic re-deriving each verdict's cited evidence rather
  than re-arguing it: property test 2 passed/exit 0; `-k unverified` 1 passed
  each on json+pdf/exit 0; nudge 6 / orchestrator 6 / resample 3, all exit 0.
  Its own AST comparison against `main` independently confirms `SolveSignals`'
  field names/types/ORDER, the `solve()` signature and `MANY == 2` are
  untouched. Went beyond the cited evidence: a 2,252-case differential against
  `brute_force_oracle.count_solutions` at a fresh seed, run BOTH stock and with
  `_SEARCH_ROUNDS` monkeypatched to `((0,3),(2,3),(4,5))` to force constant
  cut-offs and `_Pending` re-entry — **0 mismatches** in both configurations.
  Enumerated all four paths that discard a stack item and found each sound.
  Confirmed the new geometric restart ladder introduces no unboundedness that
  pre-card `main` did not already have (main had no node limit at all).
- **[Merge hazard]** ⚠ `meta/kanban/cards/CARD-018.md` was committed ON THE
  BRANCH (in `935e69f`, my error at the commit step — the kanban procedure
  excludes `meta/` from worktree commits precisely because this file has two
  writers). The branch copy is STALE: it predates every orchestrator note in
  main's copy ([Review 1/3], [Adversarial] x3, [Fix 1], [Review 2/3],
  [8h spot-check], Review score 9.0). At merge, main's copy of this file must
  win — do not let the branch version replay over it. `meta/architecture/
  decisions/adr/0013-difficulty-scoring-formula.md` is also committed on the
  branch, but that one is legitimate content that SHOULD reach main (the F-001
  History addendum) and main has no competing edit to it.
- **[AC/EC check]** GATE: 6 verified, 0 violated, 0 unverified. No
  `## Engineering constraints` section on this card, so no EC verified directly
  — EC-001 is covered under G-3.
  **AC-037 verified as CORRECTLY DECLARED UNMET**: the criterion itself is NOT
  satisfied and the card did not fake it. `test_20x20_p95_is_under_5s` collects
  and reports XFAIL (not XPASS) with `strict=True` intact. The verifier
  re-measured the whole sweep independently and reproduced the card's table
  point for point (0/5 over cap at 10/20/25/30, 2/5 at 32, 5/5 at 35/38/40, 4/5
  at 42, 1/5 at 45, 0/5 at 48+) — judging the claimed ~32-45% residual band
  conservative rather than understated.
  G-1 verified incl. byte-identical `__all__`/`MANY`/`SolveSignals` field order
  /`solve()` signature vs the merge base, and `propagate.__all__` additive only
  (6 → 8 entries, none removed). Noted non-violation: `branch_nodes`' SEMANTICS
  changed while its SURFACE did not — deliberate, reviewed, documented.
  G-2 verified mechanically: `tests/test_solver.py` is +280/-0 (zero deletions,
  so no AC-015/016/017 assertion could have been edited); `test_timeout.py`'s
  +6/-2 is confined to the `_blind_propagation` double's `cache=` forwarding.
  CARD-006's fixture hazard did NOT materialise — all 16 timeout tests pass.
  G-3 verified in two independent ways beyond the property test: every mutation
  site in `search.py` enumerated (only lines 692/697, both on `board.clone()`),
  proving a `_Pending`'s captured board is immutable for its stack lifetime;
  plus a differential against the merge-base solver over 280 grids at 10x10-
  16x16 (large enough to actually engage restarts, unlike EC-001's 1x1-8x8
  corpus) — IDENTICAL verdicts AND byte-identical witness grids. Plus 6,000
  fresh out-of-suite oracle cases at verifier-chosen seeds, 0 mismatches.
  G-4/G-5 verified mechanically (ADR-0013 is +21/-0 appended under `## History`;
  `bench_generate.py` is exactly 1 hunk, all inside `reason=`, `strict=True`
  unchanged context).
