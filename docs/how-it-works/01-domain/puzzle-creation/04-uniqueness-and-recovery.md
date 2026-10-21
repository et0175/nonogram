# 04 — Uniqueness verification and automatic recovery (CAP-003 / COMP-005)

> Scope: `src/nonogram/solver/` (`propagate.py` 1205 lines, `search.py` 1815
> lines, `__init__.py` 116 lines) plus the recovery policies POL-001/002/003/006
> that live in `orchestrator.py`, and the reveal policy CARD-214 added.
>
> **This is the correctness-critical component.** CON-005 is the model's one
> mandatory-severity constraint, and everything below is shaped by it.

## Why a hand-rolled solver at all

A nonogram with two solutions is not a puzzle. CAP-003 exists to guarantee that
every finished puzzle has exactly one logical solution, and to recover
automatically when a candidate does not.

ADR-0009 chose a hand-rolled constraint-propagation solver over a SAT/CP encoding,
and was explicit that this is exactly where a false-positive uniqueness verdict
would hide. The dependency baseline (ADR-0006, `pyproject.toml:23`: Pillow and
NumPy, nothing else at runtime) is the other half of that decision: there is no
solver library in the tree to defer to.

The whole public surface is five names (`solver/__init__.py:102`):

```
solve(row_clues, column_clues, *, givens=None, deadline=None) -> SolveResult
choose_givens(grid, row_clues, column_clues, *, cap, deadline=None) -> Givens
revealed_cells(givens)
SolveResult · SolveSignals · Givens · RungTags
MANY · RUNG_ORDER · RUNG_* · STRATEGY_GUESS
```

`solve` is a **pure function of its clues** — no filesystem, no CLI, no
randomness, no module state (`solver/search.py:551`). That purity is not an
aesthetic: it is what lets EC-001 be property-tested at the scale it is, against
an independent oracle, with no fixture machinery at all.

## `solution_count` is `0`, `1` or `MANY`, and `MANY` is 2

```python
MANY = 2   # search.py:254 — means ">= 2", never "exactly 2"
```

The search stops the instant a second distinct solution is recorded (AC-017).
`search.py:92` gives the reason in cost terms: the retry loop calls this on
*every* candidate grid it generates, and "enumerating the 40,000 solutions of a
sloppy clue set to answer 'not 1' would make the uniqueness check the most
expensive part of generation for the least useful information."

## The shape of one solve

See [diagrams/04-solve-flow.puml](diagrams/04-solve-flow.puml). From
`search.py:7`:

0. **Three stratified fixed points**, each continuing from the board the previous
   one left: the knowledge-relative overlap rule alone (`simple_overlap`), then
   the full placement intersection (`line_dp`), then probe refutation
   (`probe_contradiction`).
1. If levels 1+2 fully decide the board, it is the only solution reachable without
   lookahead and the solve is over.
1b. Otherwise **round 0's plain descent runs once, purely to detect `MANY`.** A
   clue set this round shows to be ambiguous is answered here, with the two
   witnesses it found. A round that instead ran out of nodes, or finished with 0
   or 1 solutions, "has proved nothing this solve keeps: its findings *and* its
   counters are discarded whole" and the solve carries on as though it had never
   run. That is how a uniquely solvable clue set always reaches level 3 with fresh
   counters, so its rung tags stay complete and order-independent.
2. Level 3 probes every still-unknown cell with both values, forcing the survivor
   wherever one value contradicts, to a fixed point. If that completes the board
   the solve is over **with `branch_nodes == 0`** — no search node was ever
   expanded.
3. Otherwise search, from the level-3 fixed point, with an explicit stack rather
   than recursion (`search.py:58`: depth is bounded by the number of guesses,
   which at 30×30 can exceed CPython's default recursion limit, and "an explicit
   stack makes the worst case a memory question instead of a `RecursionError`").

Levels 1 and 2 together **are** line logic's first fixed point. Monotone
propagation is confluent, so splitting it in two and running the cheaper technique
to exhaustion first settles exactly the same cells — which is why
`line_logic_cells` and the undecided mask are read between levels 2 and 3 and mean
what they always meant.

### Why probing is sound

`search.py:63` carries the argument, and it rests entirely on what `propagate`
already promises: propagation only ever writes cells that *every* placement of
some line agrees on given what is known, and returns `False` only when some line
admits no placement at all. So for any board `B`:

- probe `c = v` contradicts → no solution extends `B + (c = v)`; since `c` is
  filled or empty in every solution, forcing `¬v` discards nothing, and keeping the
  probe's own propagated board discards nothing either;
- both probes contradict → no solution extends `B`, so refuting the node discards
  nothing;
- neither contradicts → nothing is deduced and nothing discarded; the two probe
  boards become the children, and their union covers every solution extending `B`
  because they disagree only on `c`.

"Branch ordering and the restart schedule move work around; neither can add or
remove a solution, because both children of a branch are always explored and a
cut-off pass is discarded whole rather than half-believed."

### The restart schedule, and the measurement that produced it

`_SEARCH_ROUNDS` (`search.py:295`) is `(probe_width, node_limit)` per round:

```python
(_NO_PROBE, 400), (8, 400), (16, 1200), (32, 3600), (64, 10800)
```

Past the last entry the probe width stays put and the node limit keeps multiplying
by `_NODE_LIMIT_GROWTH = 3`, so **the limit is unbounded in the limit and a search
that needs the whole tree eventually gets it.** That is what keeps restarting
complete: a verdict is only ever taken from a round that finished on its own
terms, never from one that ran out of nodes.

Round 0 does **not** probe. It looks at the one cell the pre-CARD-018 heuristic
would have guessed at and branches there — the old search plus a free
contradiction check. `search.py:272` records that this escape hatch is not
decoration but what the first cut of the card got wrong (review cycle 1, F-002):
probing from node 0 pays for pruning on boards that need none. At 20×20 and 10–25%
density a candidate is massively ambiguous, a second solution turns up a couple of
hundred nodes in, and the tree probing builds there is the *same size* as the plain
one — 7,329 nodes against 4,139 on one measured request — for 3.4× the cost per
node. Over that request's twenty candidates: plain 0.37 s, probing 2.29 s. The
cell ranking matters as much as the width: width 1 over the *probe* ranking does
not finish that request at all.

The probing rounds widen on both axes at once, because measurement showed the two
failure modes are different — some instances are hard because one early guess was
wrong (a re-run that branches elsewhere finds a solution in milliseconds), others
because the inference is too weak to prune (a wider probe cuts them from tens of
seconds to one).

## CON-005's self-check: every completed board is re-encoded

`search.py:100`:

> every completed board is re-encoded from its finished masks and compared against
> the clues it was solved from before it is allowed to count as a solution. A
> mismatch is a solver bug, not a puzzle outcome, so it **raises** rather than
> being quietly discarded: a wrong answer that crashes is recoverable, a wrong
> answer that looks right is what CON-005 forbids.

The re-encoding uses `propagate.mask_runs`, not `clues.encode_line`, even though
the grid is complete by then and the clue module's function would be safe on it —
ADR-0007 forbids the lateral import. The solver consumes the clue *contract* (the
boundary tuples of ADR-0012) without importing the clue *module*. See
[01-the-layered-pipeline.md](01-the-layered-pipeline.md).

## The one mandatory property, and the oracle that proves it

EC-001 / CON-005 is verified by `tests/property/test_solver_uniqueness.py` in two
directions ADR-0014 names:

1. **Cross-check against a brute-force oracle** —
   `tests/helpers/brute_force_oracle.py`, "a second, deliberately naive solver
   that shares *no* code with `nonogram.solver`: two implementations agreeing is
   evidence, one implementation checking itself is not." It derives clues through
   `nonogram.clues` (independently written and independently property-tested) and
   never touches the solver's bitmask representation. **This is the direction that
   can see a missed second solution** — the exact failure CON-005 forbids and the
   one a solver cannot detect about itself.
2. **Free-direction round-trip** — clues derived from a real grid have at least
   that grid as a solution, so the solver must never answer 0, and when it answers
   1 the grid it returns must be the original. No oracle needed.

The oracle itself has two counters that check each other
(`brute_force_oracle.py:13`): `count_solutions` enumerates every line pattern per
row and walks the cartesian product; `count_solutions_by_cell` enumerates all
`2 ** (height * width)` grids and is "unarguably exhaustive, unarguably correct,
and unusable above about 16 cells. It exists to check the first counter on small
grids — an oracle nobody has verified is just a second guess."

Corpus sizes, as the code states them:

| | Floor asserted | Cases actually run | Seed |
|---|---|---|---|
| unseeded (EC-001) | `REQUIRED_CASES = 1000` | `CASE_COUNT = 2400` | `SEED = 20260827` |
| seeded / givens (AC-6) | `REQUIRED_GIVEN_CASES = 500` | `GIVEN_CASE_COUNT = 1500` | `GIVEN_SEED = 20261013` |

The floors are asserted **inside the tests** (`:215`, `:399`) "so shrinking the
corpus can never quietly drop below the bar." Sizes are `(1,2,3,4,5,6,7,8)` and
densities `(0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0)` — both extremes
included deliberately, because they produce the degenerate clue sets the `(0,)`
marker exists for.

The corpus tops out at 8×8 because that is where the oracle stops being free (its
cost is the product of each row's candidate count: 1–4 ms per case to 8×8, with
rare unsatisfiable sets reaching ~0.2 s, growing sharply beyond). The two seeds
are separate "so that re-pinning one must not silently reshuffle the other's
thousands of cases."

`test_solver_uniqueness.py:66` states the dependency rule in its own words:
**"No `hypothesis`: ADR-0006's dependency baseline is closed, and CARD-002's
property test set the house pattern of a seeded RNG plus hand-picked edge
shapes."**

The seeded corpus is deliberately built to contain three populations the unseeded
one cannot reach — reveals taken from the source grid, reveals *contradicting* it
(the only way to exercise EC-001's "solver says 1, truth says 0" half), and reveals
on top of mutated clues where no grid is guaranteed to satisfy them at all — plus
the two degenerate ends of nothing and everything revealed.

## The cooperative deadline is enforced, at two checkpoint kinds

ADR-0011's deadline is an absolute `time.monotonic` reading computed **once per
generation request** by the orchestrator (`orchestrator.py:1793`) and threaded
into the solver. `propagate.check_deadline` (`propagate.py:190`) is the single
place it is read:

```python
if deadline is not None:
    overshoot = time.monotonic() - deadline
    if overshoot >= 0:
        raise SolverTimeout(...)
```

It is called at every propagation fixed point (`propagate.py:983`, `:1129`) and at
every branch node (`search.py:1180`, `:1259`). `time.monotonic` and not
`perf_counter` because the deadline is compared against the orchestrator's own
reading; `SolveSignals.elapsed_seconds` keeps its own clock separately
(`propagate.py:211`).

Stopping happens **between whole steps, never mid-deduction**, which is what keeps
CON-005 true: the search can never abandon with a half-formed uniqueness verdict
(`search.py:181`). A timed-out solve has *no* answer, so `confirm_uniqueness` is
never reached and INV-002 leaves the puzzle unexportable.

With `deadline=None` — the default, and what the property tests use — the solve
runs to completion however long that takes.

## What a solve reports besides the count

`SolveResult` (`search.py:394`). Everything past `signals` was added by CARD-073
and is purely additive (EC-012): the three pre-existing fields keep their meaning
for every caller and no verdict changed.

| Field | Meaning |
|---|---|
| `solution_count` | `0`, `1` or `MANY` |
| `solution` | the grid when count is 1; on `MANY` it is the *first* witness, "not 'the' solution, and callers gated on uniqueness must not use it" |
| `second_witness` | on `MANY`, a second solution distinct cell by cell. **Not found on purpose** — it is the very solution whose discovery stops the fail-fast search, kept instead of dropped (FR-024) |
| `undecided_mask` | cells line logic left undecided at its **first** fixed point, reported for every count — empty for a line-solvable puzzle (AC-109), still reported when the count is 0 (AC-110) |
| `rung_tags` | the ladder rung that settled each cell. **Reported only when `solution_count == 1`** |
| `signals` | `SolveSignals` — the difficulty inputs |

The witnesses "agree on every cell line logic settled, so the cells they disagree
on are exactly the ambiguity, and every one of them is inside `undecided_mask`
(EC-011)." That is what makes the repair in the next section possible.

`undecided_mask` is the *first* fixed point and not the deciding round's,
deliberately: it is a property of the clue set, independent of how the search that
followed chose to branch.

### The ladder has **three** rungs

```python
RUNG_ORDER = (RUNG_SIMPLE_OVERLAP, RUNG_LINE_DP, RUNG_PROBE_CONTRADICTION)
#  propagate.py:148  —  "simple_overlap" < "line_dp" < "probe_contradiction"
```

A fourth rung, `cross_line`, was a member until the 2026-09-12 ADR-0029 revision
and is **gone for good**. `propagate.py:141` records why: it meant "settled in a
propagation sweep after the first", which is a statement about iteration rather
than inference, and because `propagate` sweeps all rows before all columns it made
a puzzle grade differently from its own transpose. The first cut of CARD-073
"graded 92% of line-solvable grids differently from their own transpose"
(`propagate.py:645`).

> **Model drift.** `meta/architecture/c4/components-CTX-001.puml:95` still
> describes COMP-005's ladder as four rungs, `simple_overlap < line_dp <
> cross_line < probe_contradiction`. The code is the authority: there are three,
> and the name `cross_line` appears nowhere in `src/`.

`RungTagger` (`propagate.py:627`) is a two-field record rather than a classifier,
and that *is* the revision: which rung a cell gets is decided by **which phase was
running**, not by anything about the individual deduction. Monotone propagation is
confluent, so "the cells level L settled" is a function of the clue set alone
(ADR-0029/R5). The tags accumulate into a single shared map and an earlier phase's
claim is never overwritten, because a later phase only ever visits cells no earlier
one settled.

`STRATEGY_GUESS = "guess"` (`propagate.py:168`) is **not** a rung and is
deliberately absent from `RUNG_ORDER` and from `SolveSignals.rungs`. "A rung is a
kind of deduction; branching is the search admitting there is none available", so
it is keyed on `branch_nodes` and appended by whoever reports the strategies —
exactly once, in `orchestrator.Puzzle.record_difficulty` (`:1302`).

A cell the *search* settles carries no rung at all. Below a guess, which cell a
refutation reaches depends on where the search branched, so a tag written there
would be a fact about the search order rather than about the clue set — ADR-0029/R5
forbids it.

## Recovery: four remedies, one shared budget

The policies live in COMP-002, not in the solver. The split is deliberate and
trace.yml's FR-013 note states it for POL-002: the policy (when, how often, what to
say at the cap) is the orchestrator's, the mechanism (which cell to flip) is
`sourcing.image`'s, "which own the grid the image produced and count nothing."

See [diagrams/04-recovery-policies.puml](diagrams/04-recovery-policies.puml).

### POL-006 repair, then POL-001 redraw — random mode only

A random-mode candidate the solver rejects is **always** rejected for ambiguity:
its clues came from a real grid, so a count of 0 cannot happen
(`orchestrator.py:1645`). And the solver says *where*.

`repair_candidate` (`orchestrator.py:796`) flips one filled and one empty cell
inside the ambiguous region. It is a **pure function** of the candidate grid and
what the solver reported — no rng draw, no clock, no host state — so the same seed
replays the same repair lineage on every machine (ADR-0024/R4). The pair choice is
the region's first filled and first empty cell of the *parent* grid, where "first"
is row-major rank, which comes free from reading the mask in order
(`_region_cells`, `:716`): "there is no sort, no rng and no host state anywhere in
the choice."

One filled and one empty, exactly, so the repaired grid has its parent's filled
count and the requested density holds **by construction** rather than by ADR-0003's
tolerance (ADR-0024/R3, AC-114).

The region is the witness-disagreement set, with the undecided mask as fallback.
`:811` insists that fallback is a live path, not a defensive branch — the per-row
filled-count argument in ADR-0024's Context only applies when the candidate is
itself one of the two witnesses, and CARD-073's measurement found **9 of 241 real
`MANY` verdicts (~3.7%)** where it does not hold, every one a disagreement set
entirely empty in the parent. Both rules are written as one loop over two regions
"so neither can be dead."

After `MAX_CONSECUTIVE_REPAIRS = 5` consecutive repairs on one lineage without a
unique verdict, the lineage is dropped and the next attempt draws a fresh grid
(`:2055`). Leaving `pending_repair` unset "is what 'discard and redraw' is in
code." Both kinds of attempt advance the **same** `regenerate` counter, so
ADR-0002's one bound of 30 covers them together.

`RecoveryLog` (`orchestrator.py:863`) tallies how that budget divided — and its
docstring is explicit that it is **observability and nothing else**: "nothing reads
these numbers to decide anything, no bound is checked against them, and deleting
the field would change no verdict." It exists because ADR-0024 named the K
recalibration as owed and said what data it needs. `repeated_attempts` is the
subtle field: it counts repairs that re-judged a grid their own lineage had already
seen, which is the one number that tells `lineages_at_repair_cap` apart into its
two populations — a lineage still reaching new grids might convert with a larger K,
a lineage cycling between two grids provably will not. Measured at ~7% of lineages,
~99% of those an immediate reversal of the previous flip (`:2019`).

### POL-002 pixel nudge — image mode only

POL-001's premise is that a rejected candidate can be replaced by a *different*
one. That holds for random (a fresh draw) and for library (the same template at a
different boundary tie-break). It does **not** hold for an uploaded image, whose
conversion at a given extent is fully determined. `orchestrator.py:55` spells out
the failure that would otherwise occur: asking `sourcing.image` for another grid
returns the grid it just returned, so image mode through the regenerate loop would
"spend the whole retry budget re-confirming one verdict and then report an
'abandoned after 30 attempts' that never had more than one attempt in it."

So image mode converts once and its `regenerate`/`resample` counters **stay at
zero** — that zero is the observable form of "this mode is not in POL-001/POL-004".

Its remedy is `MAX_NUDGE_ATTEMPTS = 5` rounds, each flipping *one more* cell of the
**original** conversion (`:2149`: `image_source.nudge(converted, nudged_cells)`),
so attempt *n* differs from the user's picture by exactly *n* pixels and no earlier
edit can be undone by a later one. The cell is chosen from what the solver reported
about the grid the **previous** round was judged on — its witness disagreement, or
its undecided mask when those are used up (`image_source.next_nudge_cell`). Each
nudged grid then goes through the one `judge_candidate` path, so the solver's
verdict on it is the only thing that ends the loop successfully.

At the cap, POL-003's refusal lives in `run_bounded`'s exhaustion branch — "which
is what 'stops altering the image' is in code (AC-035). There is no fallback
attempt after it." A conversion that is unique but misses the requested *tier* is
not nudged at all and ends the run (`:2176`): nudging is a uniqueness remedy, not a
difficulty dial.

### The reveal policy — opt-in, and tried last

All three recoveries above *change the picture*. CARD-214 added a fourth that does
not, gated on `GenerationRequest.reveal_given_cells` (default `False`,
`orchestrator.py:436`). When set, and only **after** the mode's own recovery has
exhausted its own bound, the run's **first** sourced grid is accepted unaltered
with as many cells of its solution *revealed* as it takes to make the clues have
exactly one solution.

`solver.choose_givens` (`search.py:834`) does the choosing: it solves, and while
the count is `MANY` reveals the first cell (by row then column) on which the two
witnesses disagree, to the value the real solution grid holds, and solves again.
Pure — no rng, no clock, no host state — "so the same grid yields the same givens
in the same order on every machine."

The cap is `given_cells_cap(grid)` (`orchestrator.py:842`):
`MAX_GIVEN_CELL_SHARE_PERCENT = 5` percent of the grid's own cells, floored —
**5 cells at 10×10, 20 at 20×20, 45 at 30×30**, integer arithmetic throughout so
there is no rounding mode to get wrong. A share and not a count, because "five
revealed cells is a hint on a 10×10 and invisible on a 30×30" (`:272`). Beyond the
cap the run raises `GivenCellsCapExceeded` and the picture is **still not altered**
— "the honest report is 'this picture is not a puzzle at the price we are willing to
pay', not a repaired grid" (`errors.py:105`).

Four properties of this policy are load-bearing and all four are structural:

- it is the **last** thing tried, so a puzzle that could be had with nothing given
  away still is;
- `pristine_candidate` is the run's *first* sourced grid, copied once on the draw
  that cannot be a repair or a nudge (`:2038`) — deliberately not the last grid
  judged, because by then it is "a repair of a repair or a five-pixel nudge";
- it changes no cell and no clue, so INV-001 holds untouched;
- the accepted puzzle is accepted only on a **fresh seeded solve** through the same
  `judge_candidate` as every other candidate — "uniqueness is never inferred from
  the fact that cells were revealed". If the chooser and that verifying solve ever
  disagree, the code raises a `RuntimeError` naming it a solver defect (`:1969`).

Seeding is sound for the same one-line reason probing is (`search.py:156`):
propagation only ever writes cells every *remaining* solution agrees on, and a
given removes from consideration exactly the solutions that disagree with it. So
the seeded count is the number of solutions of the clue set that extend the
givens — 0 when a given contradicts the clues, and at most the unseeded count.

> `accept_by_revealing`'s docstring (`orchestrator.py:1926`) records an open
> modelling debt in its own words: this is "a new policy ADR-0024 does not yet
> cover; the card records the delta the architect station owes (a fourth recovery
> route, and INV-002's 'given its given cells' clause). The id the card calls
> POL-007 is already taken in `domain/policies.yml` by FR-034's plan matrix, so no
> id is minted here." The policy therefore ships **without a POL id**.

## Performance is asymmetric by design

Line logic alone finishes easy and dense grids in milliseconds. The hard class is
random mid-density grids at larger extents, and the orchestrator's own measurements
are the honest figures: at density 50, a puzzle costs about **0.06 s at 20×20,
0.55 s at 25×25 and 3.90 s at 30×30** (`orchestrator.py:299`). That is the curve
`BATCH_BUDGET_SECONDS = 75.0` was chosen against, and why a flat batch count
cannot be right at both ends.

`ADR-0001`'s 30 s per-request deadline is the enforced ceiling; its 5 s p95 for
grids up to 20×20 is a benchmark gate in `tests/bench_generate.py`, not a failure
boundary.

## Bounds and honest gaps

- `SolveSignals.backtracks` is **telemetry only** (`search.py:360`): ADR-0013's
  formula does not read it, "which is why probing finding *more* of them than
  guessing did changes no score."
- `SolveSignals.elapsed_seconds` is telemetry only and may never enter a grade
  (ADR-0029/R3, CON-014, NFR-007). It is "the one field here a second run on a
  slower machine changes, which is exactly why nothing graded may depend on it."
- `rung_tags` and `SolveSignals.rungs` are empty for every clue set whose count is
  not 1. A clue set with 0 or ≥2 solutions is not a puzzle: it has no grade and no
  strategies list, whatever the deduction phases happened to settle on the way to
  that verdict.
- ADR-0014 also asks for the free-direction check to be scaled to 30×30. That is
  deliberately **not** done in the property test, and the file says so
  (`:81`): without the deadline, one pathological large grid would hang the suite
  instead of failing it. `tests/test_solver.py` carries a bounded larger-grid
  round-trip instead.

## Related

- [01-the-layered-pipeline.md](01-the-layered-pipeline.md) · [05-difficulty-calibration.md](05-difficulty-calibration.md) · [02-sourcing-a-solution-grid.md](02-sourcing-a-solution-grid.md)
- ADRs: [ADR-0009](../../../../meta/architecture/decisions/adr/0009-solver-implementation.md) · [ADR-0011](../../../../meta/architecture/decisions/adr/0011-generation-timeout-mechanism.md) · [ADR-0014](../../../../meta/architecture/decisions/adr/0014-uniqueness-correctness-oracle.md) · [ADR-0024](../../../../meta/architecture/decisions/adr/0024-random-mode-repair-then-redraw.md) · [ADR-0029](../../../../meta/architecture/decisions/adr/0029-difficulty-by-strategy-ladder.md)
