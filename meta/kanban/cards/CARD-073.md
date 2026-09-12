# CARD-073: Solver exposes the undecided mask, a second witness on MANY, and the rung that settled each cell

**Status:** in_review
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/073-solver-mask-witness-rungs
**Worktree:** ../PythonProject4-CARD-073
**Source:** meta/architecture/handoff.md#increment-8
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** src/nonogram/solver/search.py, src/nonogram/solver/propagate.py, src/nonogram/solver/__init__.py, src/nonogram/orchestrator.py (Puzzle aggregate: store the three new result fields, nothing else), tests/test_solver.py, tests/property/test_solver_witnesses.py (new), meta/architecture/decisions/adr/0009-*.md and 0012-*.md (History entries only)
**Review score:** —
**Started:** 2026-09-12T15:44Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The walking skeleton of the 2026-09-12 delta: everything after it consumes
what this card exposes. CARD-074's repair draws its pair from the witness
disagreement set, CARD-075's nudge picks from the undecided mask, CARD-076
grades from the rung tags, and CARD-072 item 1 (the strategies list) is the
ordered rung list this card emits. The solver already computes all three
things internally — the first fixed point is where `line_logic_cells` is
counted, and the second distinct grid is what turns the count into MANY and
stops the fail-fast search — so this card makes them part of the result
without changing any verdict.

**Sequencing.** First card of wave 2; nothing depends on anything else
landing before it. CARD-074, CARD-075, CARD-076 and CARD-072 item 1 wait on
it.

## What to implement

COMP-005 (`solver/`) adds to `SolveResult` / `SolveSignals`, **without
changing any verdict**:

1. **Undecided mask** — the set of cells line logic left undecided at its
   FIRST propagation fixed point, as a grid-shaped `list[list[bool]]` of
   the puzzle's extent. Reported for every count (0, 1, MANY); empty for a
   line-solvable puzzle (AC-109); still reported on count 0 (AC-110).
2. **Second witness** — on MANY, a second solution distinct (TERM-009)
   from the first. The second solution the search already stops on IS the
   second witness (ADR-0009 History). No witness on count 0; one solution
   on count 1. `solution_count`, `solution`, `signals` keep their
   pre-existing meaning for every existing caller (EC-012).
3. **Per-cell rung tags** — for the verifying solve, the ladder rung that
   settled each cell, from the enum fixed by ADR-0029:
   `simple_overlap` < `line_dp` < `cross_line` < `probe_contradiction`.
   Definitions are normative (ADR-0029 Decision):
   - `simple_overlap` — settled by a line deduction the leftmost/rightmost
     overlap rule alone yields. Decided per line deduction by natively
     re-deriving the overlap masks (sum of runs + gaps vs line length,
     leftmost and rightmost placements intersected) and comparing with
     what `line_intersection` settled. **Native reimplementation inside
     `solver/` — no import of `clues.py`** (ADR-0007, ADR-0029/R4;
     precedent: `propagate.py`'s `mask_runs`).
   - `line_dp` — settled by a line deduction only the full placement
     intersection yields.
   - `cross_line` — settled in any propagation sweep after the first. A
     sweep is one pass of `propagate`'s outer loop over the dirty rows
     then the dirty columns; "the first sweep" starts from the blank
     board. Pinned as contract: a refactor that changes what a sweep is
     re-grades puzzles and must say so in an ADR-0029 revision.
   - `probe_contradiction` — forced because the opposite value
     contradicted under propagation (a probe refuted one value, no branch
     taken).
   `SolveSignals` gains the per-rung cell counts and the **ordered list of
   distinct rungs present** (ladder order). `guess` is NOT a rung and is
   not appended here — CARD-072 item 1 appends it iff `branch_nodes > 0`.
   Tags are scoped to the deciding restart round, like `branch_nodes`.
   `elapsed_seconds` stays as telemetry; no clock reading enters a tag
   (ADR-0029/R3).
4. **Boundary types.** All three cross the module boundary as grid-shaped
   `list[list[...]]` structures, never the internal filled/empty bitmask
   pair (ADR-0012 History, EC-012). Rung tags as `list[list[str | None]]`
   (or the enum member; `None` for a cell never settled by the deciding
   solve).
5. **Orchestrator (COMP-002)** stores the mask, the witnesses and the rung
   tags on the `Puzzle` aggregate in `judge_candidate` and resets them in
   `record_candidate` the way `difficulty_score` is. Nothing else changes:
   no repair (CARD-074), no nudge change (CARD-075), no scoring change
   (CARD-076).
6. **ADR History entries owed** (ADR-0024 "Related ADR revisions"):
   - ADR-0009 — History: the solver contract gains, on `SolveResult`, the
     first-fixed-point undecided mask and, on MANY, a second witness
     distinct from the first (FR-024); strategy, fail-fast on the second
     solution and the ADR-0014 oracle cross-check unchanged.
   - ADR-0012 — History: the boundary rule is extended — mask and witnesses
     cross the boundary as grid-shaped `list[list[bool]]`, never as the
     internal bitmask pair (EC-012).
   History entries only; no Decision/Rules text changes.
7. **Measure and record** (the number Increment 9 needs): on the oracle
   corpus, the share of MANY verdicts whose disagreement set contains at
   least one filled AND one empty cell of the parent grid (ADR-0024's
   repair precondition). Write it to Worktree notes.
8. `tests/bench_generate.py` at 20x20 before and after: within noise
   (ADR-0029 Negative: tagging is on the hot loop; `--difficulty`'s
   resample loop solves every candidate).

## Acceptance criteria

- **AC-107** (FR-024) — given the clues of a 10x10 grid containing exactly
  one 2x2 switching block, when solved, then the result reports MANY and
  carries two witness grids that differ in exactly those 4 cells.
  *test:* `TestSolver_ReportsSecondWitnessWhenMany`
- **AC-131** — given the two witnesses for the switching-block clues, when
  each is run-length encoded row by row and column by column, then both
  encodings equal the given clues exactly.
  *test:* `TestSolver_BothWitnessesReencodeToInputClues`
- **AC-108** — given the same clues, when solved, then the undecided mask
  has exactly those 4 cells set and every other cell clear.
  *test:* `TestSolver_UndecidedMaskListsCellsLeftAtFirstFixedPoint`
- **AC-109** — given clues of a 15x15 grid line logic decides completely
  (count 1, branch_nodes 0), when solved, then the mask has no cell set
  and no second witness is returned.
  *test:* `TestSolver_UndecidedMaskIsEmptyForLineSolvablePuzzle`
- **AC-110** — given a contradictory clue set with zero solutions, when
  solved, then solution_count is 0, no witness is returned, and the mask
  is still reported for the cells left open at the first fixed point.
  *test:* `TestSolver_NoWitnessWhenUnsolvable`
- **AC-A** (rung tags, handoff directed test; FR-029's solver half) — a
  fully line-solvable clue set tags every cell with a rung and never
  `probe_contradiction`; a set that needed a probe refutation tags at
  least one cell `probe_contradiction`.
  *test:* `TestSolver_LineSolvableSetTagsEveryCellWithoutProbeContradiction`
- **AC-B** (verdicts identical) — `tests/property/test_solver_uniqueness.py`
  and `tests/test_solver.py` unchanged and green; counts on the oracle
  corpus identical to today.

## Engineering constraints

- **EC-011** — For any clue set on which the solver reports MANY, the two
  witnesses it returns are distinct cell-by-cell (TERM-009), each
  re-encodes exactly to the input clues, and every cell on which they
  disagree is a member of the first-fixed-point undecided mask — because
  propagation only ever writes cells every solution agrees on. Holds for
  every clue set, not only the measured examples. Seeded corpus (stdlib
  `random.Random`), **>= 200 cases asserted inside the test**, no
  hypothesis.
  *test:* `PropertyTest_Solver_WitnessesDisagreeOnlyInsideUndecidedMask`
- **EC-012** — Every existing consumer of the solver's result (the
  orchestrator's solution_count == 1 gate, the difficulty scorer's signals
  protocol, the EC-001 oracle cross-check) continues to read
  solution_count, solution and signals with their pre-existing meaning,
  and neither addition is an int bitmask at the boundary.
  *test:* `TestSolver_ResultFieldsUnchangedForExistingCallers`
- **EC(ADR-0029/R2)** — Rung tags and the ordered rung list are computed
  inside the one verifying solve, never by a second `solve` entry or a
  re-propagation for classification.
  *test:* `TestSolver_RungTagsComputedInsideTheOneSolve` (wrap
  `propagate`/`_search` with call counters; a tagged solve makes no more
  calls than an untagged one)
- **EC(ADR-0029/R3)** — The rung tags and rung list are a pure function of
  the clue set: same clues, same tags, under a patched/dilated clock.
  *test:* `PropertyTest_Solver_RungTagsDeterministicPerClueSet`

## Guardrails

- G-1: No verdict changes — `tests/property/test_solver_uniqueness.py`,
  `tests/test_solver.py` and `tests/helpers/brute_force_oracle.py` are not
  edited; the oracle never imports `nonogram.solver` (ADR-0014).
- G-2: No lateral imports — `solver/` imports neither `clues.py` nor any
  capability module; the overlap masks are re-derived natively
  (ADR-0007, ADR-0029/R4). `tests/test_cli.py::test_every_import_in_the_package_points_inward`
  stays green.
- G-3: Bitmasks never cross the boundary in either direction (ADR-0012);
  the three new fields are `list[list[...]]`.
- G-4: The orchestrator only STORES the new fields — no repair step
  (CARD-074), no nudge change (CARD-075), no scoring change (CARD-076), no
  `guess` append (CARD-072). Do not edit `difficulty.py`, `sourcing/**`,
  `export/**`, `web/**`, `admin/**`.
- G-5: No clock reading enters a rung tag or the rung list (ADR-0029/R3,
  CON-014); `elapsed_seconds` stays telemetry only.
- G-6: ADR-0009 / ADR-0012 edits are History entries only.
- G-7: `tests/bench_generate.py` 20x20 within noise before/after — record
  both numbers in Worktree notes.
- G-8: Commit only your own files — the working tree carries a large
  standing set of unrelated staged/untracked changes; use explicit
  pathspecs.

## System contract

- CON-005 — the solver never reports a puzzle uniquely solvable when it has
  0 or >= 2 solutions (check: `tests/property/test_solver_uniqueness.py`,
  PropertyTest_Solver_NeverFalsePositiveUniqueness)
- ADR-0007 — capability modules never import each other laterally (check:
  test_every_import_in_the_package_points_inward)
- ADR-0012 — grids cross module boundaries as `list[list[bool]]`; the int
  bitmask pair never does (check: TestSolver_ResultFieldsUnchangedForExistingCallers)
- ADR-0029/R2 — technique classification computed inside the one verifying
  solve, never by re-solving (check: review-lens here; AC-135's
  TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve lands with CARD-072)
- ADR-0029/R3 — no clock, size or density term enters the rung tags
  (check: review-lens; PropertyTest_ScoreDifficulty_IndependentOfElapsedTime lands with CARD-076)
- ADR-0029/R4 — overlap masks re-derived natively inside `solver/` (check:
  test_every_import_in_the_package_points_inward)
- ADR-0011 — the cooperative deadline still bounds the solve; hook points
  in `propagate.py`/`search.py` unchanged (check: tests/test_timeout.py)
- ADR-0014 — the brute-force oracle stays independent of `nonogram.solver`
  (check: review-lens)

## Architecture context

- **FR:** FR-024 (AC-107..AC-110, AC-131); solver half of FR-029
- **NFR:** NFR-001 (bench within noise)
- **EC:** EC-011, EC-012
- **ADR:** ADR-0009, ADR-0012 (History entries owed), ADR-0024 (first
  consumer), ADR-0029 (R2, R3, R4 — rung definitions), ADR-0007, ADR-0014
- **Components:** COMP-005 (Solver), COMP-002 (Orchestrator — store only)
- **Domain:** EVT-006 now carries the mask (POL-002/POL-006 read it)
- **Trace:** meta/architecture/trace.yml (FR-024 row, FR-029 row)

**Checkpoint (handoff, verbatim):** `solve()` on a known-ambiguous clue set
returns two distinct witnesses whose disagreement lies entirely inside the
undecided mask, on the oracle corpus with identical counts to today; on a
line-solvable set every cell carries a rung. Measured on the corpus: the
share of `MANY` verdicts whose disagreement set contains at least one
filled AND one empty cell (ADR-0024's repair precondition) — the number
Increment 9 needs.
**Collapses:** FR-024, EC-011, EC-012, ADR-0024's "does a filled/empty pair
always exist" assumption (measured, not argued), the blocker on CARD-072
item 1.
**Rollback:** Purely additive fields on the solver result; revert the
branch. No stored data changes.

## Worktree notes

### Item 7 — ADR-0024's repair precondition, measured

**On the oracle corpus (`tests/property/test_solver_uniqueness.CASES`, 2400
cases, `SEED = 20260827`): 96.27% (232 / 241).**

That is the share of `MANY` verdicts *that have a parent grid* whose
witness-disagreement set contains at least one cell filled in the parent **and**
at least one cell empty in it — ADR-0024's precondition for drawing a repair
pair from the region.

    corpus cases                                         2400
    MANY verdicts                                         262
      ... of which carry a parent grid                    241   (21 have
          mutated clues and so no parent grid at all)
      ... whose disagreement set holds a filled AND
          an empty cell of the parent grid                232
    share of MANY-with-a-parent                        96.27%   (232/241)
    share of all MANY verdicts                         88.55%   (232/262)

**It is not 100%, and the nine exceptions have one shape.** ADR-0024's Context
argues the precondition "cannot happen" to fail, from the fact that two
solutions of the same row clues have equal filled counts per row. That argument
is sound *when the parent grid is one of the two witnesses* — and the corpus
bears it out exactly:

    parent grid IS one of the two witnesses               159   of 241
      ... and the filled/empty pair exists there          159   (100.00%)

The argument does not cover the case where the parent is a **third** solution.
All nine counterexamples are that case, and in every one of them the whole
disagreement set is empty in the parent (`values == {False}`), so there is no
filled cell to flip. The smallest is corpus case 260, a 5x5:

    rows ((1,), (1,), (0,), (1,1), (1,))   columns ((1,), (0,), (1,), (2,), (1,))

    parent      witness 1   witness 2
    ...#.       ..#..       ....#
    ...#.       ....#       ..#..
    .....       .....       .....
    ..#.#       #..#.       #..#.
    #....       ...#.       ...#.

The witnesses disagree at (0,2), (0,4), (1,2), (1,4); the parent is empty at
all four, because its own ambiguity lives in column 3. So Increment 9 needs the
fallback ADR-0024 already specifies ("should the region contain no filled/empty
pair of the parent grid ... the repair falls back"): it fires on roughly 1 case
in 27, not never. The code must not assume the pair exists — which is what the
ADR says, and now with a number behind it.

Reproduced by `measure_repair.py` (scratchpad, not committed): solve every
corpus case, keep the `MANY` ones with a source grid, diff the two witnesses,
look up each disagreeing cell in the parent.

### Item 8 — `tests/bench_generate.py` at 20x20, before and after

Within noise. Two runs of `report()` on each side, on the same machine,
`GENERATION_BUDGET_SECONDS = 30`:

    sample (density, seed)   before #1  before #2  |  after #1   after #2
    30, 0                      1.281s     1.409s   |   1.385s     1.334s
    40, 0                     30.002s    30.002s   |  30.001s    30.002s  (timeout)
    50, 0                      0.049s     0.051s   |   0.051s     0.050s
    60, 0                      0.004s     0.004s   |   0.005s     0.004s
    30, 1                      1.250s     1.281s   |   1.336s     1.418s
    40, 1                     30.001s    30.004s   |  30.002s    30.002s  (timeout)
    50, 1                      0.046s     0.051s   |   0.048s     0.046s
    60, 1                      0.005s     0.005s   |   0.005s     0.005s
    30, 2                      4.386s     4.674s   |   5.030s     4.501s
    40, 2                     30.002s    30.001s   |  30.001s    30.001s  (timeout)
    50, 2                      0.138s     0.150s   |   0.132s     0.131s
    60, 2                      0.002s     0.002s   |   0.002s     0.002s
    30, 3                      1.808s     1.905s   |   1.889s     1.962s
    40, 3                     30.001s    30.005s   |  30.000s    30.003s  (timeout)
    50, 3                      0.021s     0.027s   |   0.022s     0.022s
    60, 3                      0.002s     0.002s   |   0.002s     0.002s
    30, 4                      1.722s     1.928s   |   1.747s     1.744s
    40, 4                     15.039s    14.736s   |  14.765s    14.580s
    50, 4                      0.006s     0.006s   |   0.007s     0.006s
    60, 4                      0.005s     0.005s   |   0.006s     0.005s

    p95 (nearest-rank, n=20)  30.002s    30.004s   |  30.001s    30.002s

**p95 is unchanged to the millisecond** — but it is also useless as a
sensitivity measure here, because four of the twenty samples are censored at
the 30s budget, so the 19th-ranked sample is the budget itself whatever the
solver does. The honest number is the **sum of the sixteen uncensored
samples**:

    before   25.764s , 26.236s      (mean 26.00s, spread 0.47s)
    after    26.432s , 25.812s      (mean 26.12s, spread 0.62s)

**Difference of means +0.12s = +0.47%, inside a run-to-run spread of ~2.4%.**
Every individual after-sample lies inside or within ~7% of the two before-
samples' range, and the sample that moved most (density 30 / seed 2: 4.386 and
4.674 before, 5.030 and 4.501 after) straddles it in both directions across the
two runs. AC-037's gate itself is unaffected: it is timed against the same
saturated p95.

*Why it is this cheap.* The tagging work is off the hot loop by construction,
not by tuning. `simple_overlap`/`line_dp`/`cross_line` are recorded only during
the **one** propagation that starts from the blank board — `Board.clone()` drops
the tagger, and every board the search touches is a clone, so the probing loop
carries a single `is not None` per productive line deduction and nothing else.
`probe_contradiction` is not recorded during a probe at all (which value will
turn out to be forced is not known then); it is a row-mask diff of the forced
child against its parent, taken only when a value actually is forced —
`height` int ORs against a whole propagation.

### Design notes worth carrying forward

**Where the rungs are decided.** ADR-0029 defines the first sweep as one pass of
`propagate`'s outer loop over the dirty rows *and then* the dirty columns,
starting from the blank board. Taken literally — as it is here — the **column**
half of the first sweep already reads cells the row half wrote and is still
graded `simple_overlap`/`line_dp`, not `cross_line`. That is the pinned
contract, and it is worth knowing before someone reads a `cross_line`-free
grade as "no cross-line information was used".

**Scope of the tags.** Like `branch_nodes`, the tags are scoped to the deciding
restart round: forced deductions made in a round that was abandoned at its node
limit are discarded with the rest of that round's findings. And, also like
`branch_nodes`, they cover the whole round — including forced deductions made
below a guess. A puzzle that needed a guess is `Tier.GUESS` by ADR-0025 before
this scale is consulted, so that does not affect a grade; it does mean
`probe_contradiction` on a guessy puzzle reads as "the search refuted values",
not "the puzzle needs refutation and nothing more".

**Cells with no rung.** A cell settled only under a guess carries `None`. That
is deliberate: `guess` is not a rung of this ladder (ADR-0029, CARD-072 appends
it downstream iff `branch_nodes > 0`), so there is no honest rung to write.

**`overlap_masks` soundness.** The "empty" half of the overlap rule is *not*
"empty in both extreme placements" — that is unsound (`runs=(1,)` in a length-3
line leaves the middle cell empty at both extremes and yet some placement fills
it). It is "covered by no run's `[leftmost start, rightmost end]` window", which
is sound, and `tests/test_solver_witnesses_and_rungs.py` pins both halves
against an independent enumeration of every placement rather than against the
DP.

**Guardrails.** No file outside `solver/`, `orchestrator.py` (store only),
`tests/` and the two ADR History entries was touched. `propagate`'s signature is
unchanged — the tagger rides on `Board.tagger` — which is what keeps
`tests/test_timeout.py`'s `_blind_propagation` stub (a five-parameter stand-in
for `propagate`) working unedited, and keeps ADR-0011's two checkpoints exactly
where they were.
