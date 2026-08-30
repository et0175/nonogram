# CARD-018: Strengthen solver search to meet AC-037 at 20x20 mid/low density

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/018-solver-search-strength
**Worktree:** —
**Source:** meta/architecture/decisions/adr/0001-generation-time-thresholds.md (revision, DEC-019)
**Idea:** —
**Wave:** —
**Depends on:** CARD-006
**Touches:** src/nonogram/solver/search.py, src/nonogram/solver/propagate.py, tests/bench_generate.py, tests/test_solver.py
**Review score:** —
**Started:** —
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

   *Revised after review cycle 1 (F-002): probing does not start at node 0.* Round 0 is a
   plain, non-probing descent — see item 3 and the cycle-1 section at the end of these
   notes. Probing begins at round 1, on the boards round 0 could not settle inside its node
   budget, which is exactly the class this card exists for.
2. **A per-solve memo for the line DP (`propagate.LineCache`).** Probing multiplies
   `line_intersection` calls by roughly ten, and sibling probes at one node re-ask
   ninety-eight of a hundred lines the *identical* question. Measured hit rate on a hard
   20x20: **89.5%** (1,514,543 lookups, 158,830 misses). Without it probing is a net loss;
   with it a hard solve is ~5x faster on top of the tree reduction. The memo is created in
   `solve()` and dies with the call — no module state (the property
   `test_solving_the_same_clues_twice_gives_the_same_answer` pins that), and `propagate`'s
   new `cache=` argument defaults to `None`, which is the pre-CARD-018 behaviour exactly.
3. **A restart schedule (`_SEARCH_ROUNDS`).** A round that exceeds its node limit is
   abandoned whole and re-run with a **wider probe and a larger limit**. As shipped after
   review cycle 1: `(no probe, 400) → (8, 400) → (16, 1200) → (32, 3600) → (64, 10800)`,
   then the limit keeps tripling. **Round 0 does not probe at all** — it is the
   pre-CARD-018 descent (`_branch_cell`, one guessed cell, the second value deferred
   unpropagated as a `_Pending` until the search comes back for it), bounded so that a
   board it cannot settle quickly falls through to the probing rounds. Round 0 is also
   undiversified — it follows the heuristic's own best branch — so ordinary puzzles are on
   the same short path they were on before. Later rounds spread the branch choice over the
   candidates probing found equally live, chosen by a hash of `(round, node)` rather than a
   random draw, so the solver stays deterministic and pure (ADR-0007). Because the limit
   grows without bound, a round eventually gets the whole tree, which is what keeps
   restarting **complete**.

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

⚠️ **The "after" columns in the three tables immediately below are cycle-1 numbers**, taken
against the unconditional-probing search. They are kept because the *direction* they show
(30-40% collapsing from tens of seconds to seconds, the fast path not regressing) still
holds, but the cycle-1 fix changed round 0, so the exact figures no longer describe the
shipped solver. The re-measured, current numbers are the corrected sweep and fast-path
tables in the cycle-1 section at the end of these notes.

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

**The full 10-90% sweep AC-037 actually asks about.** ⚠️ The version of this table written
in cycle 1 has been **replaced** — its "before" column was wrong at density 10 (F-003) and
its "after" column was measured against the unconditional-probing search this fix replaced
(F-002). The corrected, re-measured table is in the cycle-1 section at the end of these
notes. Read that one.

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

**Met now** (re-measured after the cycle-1 fix; per-seed counts, not a hand-waved band):
every seed is under the 5s cap at densities **10, 20, 25, 30** and **48-100**. Still over
on **2 of 5** seeds at 32%, **5 of 5** at 35/38/40%, **4 of 5** at 42% and **1 of 5** at
45%. The benchmark's own corpus (30/40/50/60) therefore has its density-30 column newly
green and its density-40 column still red, which is why the gate still fails and the marker
still belongs there. (The cycle-1 text here claimed "10-32% and 45-100% met"; 32% and 45%
were never clean on all five seeds, in cycle 1 or now.)

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

---

### Review cycle 1 (2026-08-30): F-001 / F-002 / F-003 resolved

Report: `meta/review/20260830T094818Z-CARD-018-cycle1.yml` (score 6.5). Three Important
findings were confirmed and fixed here; F-004..F-009 were out of this fix's scope and are
untouched.

#### F-001 resolved by **(b)** — the broader meaning is kept, and every artifact that described the old one was corrected

Both halves of the finding are real, and they need different answers.

*The redefinition itself.* Option (a) — narrow `branch_nodes` back to "guesses only" — was
tried first and rejected on evidence, not preference. Under it the AC-015 fixture
`BRANCHING_ROWS/COLUMNS` reports `branch_nodes == 0`: probing settles that whole 6x6 by
forced deduction past a stalled fixed point, guessing nowhere. Three existing tests then
fail — `test_reports_unique_solution_that_needs_backtracking`,
`test_signals_report_partial_line_logic_coverage_when_guessing_is_needed` and
`test_difficulty.py::test_a_puzzle_that_needs_guessing_scores_above_one_that_does_not` —
and the third is in a file this fix is not scoped to touch. More to the point, the failure
is telling the truth: a puzzle whose entire search past line logic is forced deduction is
*not* free, and a term weighted 0.45 that scores it identically to a puzzle line logic
finished outright has lost the thing it was measuring. So `branch_nodes` keeps counting
**every node the search expands past line logic**, and the three places that described the
old meaning now describe this one:

- `SolveSignals.branch_nodes` / `.backtracks` (`search.py`) — rewritten, including *why*
  the meaning widened and what stayed true (`0` exactly when line logic alone finished,
  which is AC-023's anchor).
- `difficulty.SolverSignals.branch_nodes` (`difficulty.py`) — the protocol docstring, which
  still said "guesses the search had to make".
- **ADR-0013** — a dated `History` addendum (2026-08-30), appended, not a rewrite: the
  original Decision text is untouched, and the note records what the quantity its
  `(branch nodes / total cells)` term now measures and why the ADR's own two claims about
  it still hold.

*The restart accumulation.* This half was simply a bug and is fixed as such: `_Counters` is
now rebuilt per round in `solve()`, so the signals describe **the round that produced the
verdict** and never sum in the rounds it abandoned. An abandoned round proved nothing about
the puzzle; letting its nodes into ADR-0013's score made the difficulty a function of the
heuristic's luck. `backtracks`' own off-by-one is fixed too — a node where *both* probes are
refuted now counts 2, because two assignments were refuted.

*The test that would have caught it.* `test_the_signals_count_the_deciding_round_and_nothing_else`
(`tests/test_solver.py`) counts the search's real control flow independently — every
`_expand` call is a node expanded, every `_probe` that comes back refuted is a refuted
assignment, both bucketed per restart round — and asserts
`branch_nodes == expanded[-1]` and `backtracks == refuted[-1]`, with
`sum(expanded) > expanded[-1]` asserted first so the case cannot pass vacuously on a puzzle
that never restarted. Against the cycle-1 code it fails on both counters. The two existing
real-signal difficulty tests only asserted `== 0` / `> 0`, which is exactly why nothing
caught this.

#### F-002 resolved by **making round 0 a non-probing descent**, not by weakening probing

The regression reproduced, and the cause turned out to be sharper than "probing is
overhead". On 20x20 density 10 seed 0 (the twenty candidates one request judges), the
probing search visits **7,329** nodes against the old search's **4,139** — probing does not
shrink that tree at all, because these candidates are massively ambiguous and a second
solution is a couple of hundred plain nodes away — and pays **3.4x** per node for the
privilege: 2.29s against 0.37s.

So round 0 no longer probes. `_SEARCH_ROUNDS` is now
`(no probe, 400) → (8, 400) → (16, 1200) → (32, 3600) → (64, 10800)`, and round 0 is
`_descend`: the pre-CARD-018 heuristic (`_branch_cell` — the least free line, and within it
the cell whose perpendicular is least free), one guessed cell, and the *second* value handed
back as a `_Pending` — assigned and propagated only if the search actually comes back for
it. That laziness is why round 0 costs one propagation per node where the eager version
costs two, and it is what makes density 10 land **below** the pre-CARD-018 number rather
than merely near it.

Two things had to be got right, and both were measured rather than assumed:

- **The ranking matters as much as the width.** Round 0 could not simply take the top *one*
  cell of the probe ranking: with `((1, 10**9),)` on that same density-10 request, two of
  the twenty candidates did not finish in **85s** and **253s** (2.9M and 9.3M nodes), where
  `_branch_cell` settles every one of them in about 30ms. The probe ranking is built to
  surface contradictions; the round-0 ranking is built to find a solution on a board that
  has many. They are not interchangeable.
- **Round 0 must be bounded, and 400 is the price of the escape.** A board round 0 cannot
  settle in 400 nodes falls through to probing. That budget is not free at mid density —
  20 candidates x ~400 plain nodes is real work thrown away — which is why the laziness
  above matters: it halves it. Round-0 limits of 150/250/320/350/400/500 were all swept; 400
  is the knee, and it keeps `_SEARCH_ROUNDS`' node limits monotonic.

**Corrected 10-90% sweep**, `orchestrator.generate` end to end, 20x20, seeds 0-4, every
request censored at the 5s benchmark budget (`GENERATION_BUDGET_SECONDS = 5.0`), so a
`5.00+` entry is a lower bound. "before" is the merge base; "cycle 1" is commit `935e69f`;
"now" is this fix. Every request at 10-32% ends in `GenerationAbandoned` (20 candidates,
none unique) in **all three** columns — these timings are how fast the pipeline gives up,
not how fast it produces a puzzle. Densities 45+ are a mix of `unique` and `abandoned`.

| density | before (over cap) | cycle 1 (over cap) | now (over cap) | now, per seed |
|---|---|---|---|---|
| 10 | 0.34-0.38s (0/5) | 1.58-2.52s (0/5) | **0.26-0.29s** (0/5) | 0.29 0.26 0.27 0.26 0.28 |
| 20 | 0.56-**5.00+** (2/5) | 1.35-1.73s (0/5) | **0.38-0.55s** (0/5) | 0.54 0.55 0.52 0.38 0.53 |
| 25 | 1.21-**5.00+** (4/5) | 1.27-1.66s (0/5) | 0.69-2.00s (0/5) | 1.82 0.69 0.82 0.79 2.00 |
| 30 | **5.00+ x5** (5/5) | 1.28-2.47s (0/5) | 1.28-4.33s (0/5) | 1.50 1.28 4.33 1.94 1.90 |
| 32 | **5.00+ x5** (5/5) | 2.42-**5.32** (2/5) | 1.27-**5.00+** (2/5) | 4.12 5.00+ 1.27 5.00+ 3.43 |
| 35 | **5.00+ x5** (5/5) | — | **5.00+ x5** (5/5) | — |
| 38 | **5.00+ x5** (5/5) | — | **5.00+ x5** (5/5) | — |
| 40 | **5.00+ x5** (5/5) | — | **5.00+ x5** (5/5) | — |
| 42 | **5.00+ x5** (5/5) | — | **5.00+ x4**, 3.45 (4/5) | — |
| 45 | 0.80-**5.00+** (3/5) | — | 0.30-**5.00+** (1/5) | 0.30 5.00+ 2.33 1.44 0.83 |
| 48 | 0.06-1.39s (0/5) | — | 0.04-0.37s (0/5) | 0.13 0.37 0.28 0.10 0.04 |
| 50 | 0.01-0.13s (0/5) | — | 0.01-0.12s (0/5) | 0.05 0.04 0.12 0.02 0.01 |
| 60-90 | <=0.01s (0/5) | — | <=0.01s (0/5) | — |
| **total** | **39/80 over cap** | — | **22/80 over cap** | — |

The band this card exists for did **not** regress. A/B on the hard band, same corpus, 15s
budget, densities 32/35/40/42 x seeds 0-2, run on this build with only `_SEARCH_ROUNDS`
swapped: the cycle-1 ladder scores **122.5s total, 6/12 over cap**, the shipped ladder
**130.7s, 6/12** — sign-mixed per case (32/2 improves 3.55s → 1.23s, 42/0 improves
15.00s+ → 12.98s, 35/0 and 35/1 regress), identical over-cap count, ~7% more total. That is
the price paid for a 5-9x improvement across 10-25% and a 39/80 → 22/80 improvement over
the whole sweep.

**Fast path, re-measured** (best of 7 over 8 seeded grids each, per-grid average; this is a
fresh harness, so compare the two columns with each other and not with CARD-006's table):

| configuration | before (merge base) | now |
|---|---|---|
| 10x10 @ 50% | 0.77 ms | 0.78 ms |
| 20x20 @ 50% | 11.68 ms | **9.10 ms** |
| 20x20 @ 75% | 1.06 ms | 1.02 ms |
| 30x30 @ 75% | 2.98 ms | 2.96 ms |
| 40x40 @ 75% | 8.08 ms | 8.07 ms |
| 50x50 @ 75% | 17.47 ms | **16.13 ms** |

#### F-003 corrected: density 10 never timed out, and now runs faster than it did before the card

The claim in cycle 1's `xfail` reason and in these notes — "before this card the same sweep
timed out at the 30s cap on 3 of 5 seeds at density 10", "10-25% now runs 1.4-2.9s where it
also used to time out" — does not reproduce. Re-measured on the merge base with the repo's
own orchestrator, seeds 0-4:

**density 10 was the fastest point on the entire sweep before this card: 0.34 / 0.35 / 0.36 /
0.37 / 0.38s, 0 of 5 over cap at either the 5s or the 30s budget**, every one ending in
`GenerationAbandoned` via the 20-candidate retry limit — never a `SolverTimeout`. Cycle 1
made it **1.58-2.52s** (a 4-7x regression, which is F-002). This fix takes it to
**0.26-0.29s** — below the pre-card number, because round 0 now defers the second value's
propagation where the old search propagated it on the way back.

The rest of the cycle-1 claim does reproduce and is preserved in the corrected table above:
density 20 went 2/5 over cap → 0/5, density 25 4/5 → 0/5, density 30 5/5 → 0/5, density 45
3/5 → 1/5. Both reading hazards the review named are now stated: in the table's own preamble
(every 10-32% request is an *abandoned* request, so the timing is how fast the pipeline gives
up) and in the `xfail` reason itself (32% at 1.3-4.1s is inside noise of the 5s threshold,
not comfortably under it).

The wrong sweep table and the wrong "met band" sentence were corrected **in place** above
rather than deleted, with a pointer here.

#### Soundness (G-3) — what the new round-0 path adds to the argument

`_descend` makes exactly the same three moves the probing pass makes, on one cell instead of
`probe_width`: the first value's propagation survives (branch — both values still explored,
one now deferred), or it contradicts and the other value is **forced** (a deduction, sound
by the same "no solution extends `B + (c = v)`" step), or both contradict and the node is
refuted. `_Pending` defers *work*, never a decision: it is pushed on the stack beneath its
partner, so both values of the branch cell are always reached, and the assignment plus
propagation it carries out on being popped is byte-for-byte the work the eager path did. A
`_Pending` whose propagation contradicts is the classic backtrack — the subtree is empty and
was never entered.

Evidence, re-run against this build:

| check | scale | result |
|---|---|---|
| `tests/property/test_solver_uniqueness.py` (EC-001, in-suite) | 2400 cases, 1x1..8x8, each cross-checked against the ADR-0014 oracle | **0 mismatches** |
| Same oracle cross-check, **fresh seeds outside the suite** (1111/2222/3333/4444/5555/6666) | **12,000** further cases | **0 mismatches**; mix 3,661 unsolvable / 6,786 unique / 1,553 ambiguous |
| Verdict invariance, in-suite (`test_the_verdict_does_not_depend_on_probe_width_or_restarts`) | 96 grids 10x10..16x16 x 4 configurations, all of which bypass round 0 and therefore differ from the production path | **0 differing verdicts** |
| Verdict invariance, out of suite | 240 grids 10x10..16x16 x 5 configurations — including the cycle-1 probe-from-node-0 ladder and a plain-round-0-with-constant-restarts ladder — plus a round-trip check on every unique verdict | **0 differing verdicts, 0 bad grids** |

#### Guardrails, re-verified after the fix

- **G-1** — `solve(row_clues, column_clues, *, deadline=None)`, `SolveResult`,
  `SolveSignals` (same five fields, same types, same order) and `MANY` are unchanged;
  `src/nonogram/solver/__init__.py` is untouched by this fix. `_NO_PROBE`, `_descend`,
  `_Pending`, `_branch_cell` and `_preferred_value` are all module-private.
- **G-2** — AC-015/016/017 and AC-038 pass unchanged; not one assertion in those tests was
  edited. `tests/test_timeout.py` is untouched by this fix.
- **G-3** — see above: the EC-001 property passes, plus 12,000 fresh out-of-suite oracle
  cases and 1,200 out-of-suite invariance comparisons, all clean.
- **G-4** — `orchestrator.py`, `cli.py`, `export/**`, `sourcing/**`, `clues.py` and
  `pyproject.toml` are untouched. `difficulty.py` and ADR-0013 were edited, deliberately and
  only as F-001's option (b) requires: one protocol docstring and one appended `History`
  note, no behaviour and no formula changed.
- **G-5** — the diff to `tests/bench_generate.py` is the `reason=` string and nothing else
  (`git diff 935e69f -- tests/bench_generate.py` shows one hunk, inside `reason=`).
  `strict=True`, the censoring, the early stop, the corpus, the rank and the threshold are
  all as CARD-006 built them.

#### Test run after the fix

`./.venv/bin/python -m pytest`: **1165 passed, 1 xfailed, 0 failed**, exit 0. The +1 over
cycle 1's 1164 is `test_the_signals_count_the_deciding_round_and_nothing_else`; the xfail is
AC-037's benchmark, still strict, still narrowed rather than removed.
