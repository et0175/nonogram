# CARD-073: Solver exposes the undecided mask, a second witness on MANY, and the rung that settled each cell

**Status:** done
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
**Review score:** 9.0 (cycle 2/2)
**Started:** 2026-09-12T15:44Z
**Closed:** 2026-09-13T09:20Z
**Actual:** —
**Merge commit:** ab851eb
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

  **AMENDED 2026-09-12 (owner decision, cycle-3 repair only): `tests/test_solver.py`
  may be edited, for this repair and nothing else.** The reason the file was
  frozen is that it is the independent witness to "no verdict changed" — and
  that is still exactly what it is for: no verdict, no count and no solution
  grid asserted anywhere in it moves, and `tests/property/test_solver_uniqueness.py`,
  `tests/test_timeout.py`, `tests/test_cli.py` and
  `tests/helpers/brute_force_oracle.py` stay frozen and green, so the CON-005
  cross-check is untouched. What the amendment covers is three assertions —
  two here and one in `tests/test_difficulty.py` — that pin a *premise about
  the fixture* rather than a verdict: that the 6x6 `BRANCHING_ROWS` /
  `BRANCHING_COLUMNS` clue set needs a guess. Since ADR-0029's 2026-09-12
  revision made probe refutation a phase of the solve, it does not: 16 cells at
  `simple_overlap`, 20 at `probe_contradiction`, `branch_nodes == 0`, verdict
  still 1 and the same grid. The card's own invariant — that `branch_nodes` is
  0 when level 3 completes a puzzle, so it is gradeable Hard rather than
  `Tier.GUESS` — and those three assertions cannot both hold, and weakening
  level 3 to keep the fixture branching would be exactly the hidden solver
  constant ADR-0029/R1 and R5 forbid. A straight fixture swap is not available
  either: no random clue set branches after level 3 (0 of 6,620 searched), so
  there is no line-solvable replacement to point them at. Each test is
  therefore re-pointed at what it actually needs — see the cycle-3 notes below.
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

## Revision pending — ADR-0029 revised 2026-09-12 (after this card's cycle-1 review)

The cycle-1 review measured what this card's own checkpoint asked for and found
the rung definitions order-dependent: `line_dp` was unreachable for a line
examined from a blank board (4000/4000 agreement between the overlap rule and
the full DP), so every `line_dp` tag was a sweep-0 *column* tag, and 205 of 224
line-solvable grids (92%) graded differently from their own transpose. ADR-0029
was revised at the root rather than patched here.

**Unaffected and still good as committed (d81c387):** the undecided mask and the
second witness — items 1, 2, 4, 5 of "What to implement", AC-107, AC-108,
AC-109, AC-110, AC-131, EC-011, EC-012, and both measurements in the worktree
notes. Those are what CARD-074 and CARD-075 consume and they need no rework.

**To rework (item 3, the rung tags):**
- The ladder is now `simple_overlap < line_dp < probe_contradiction`.
  `cross_line` is gone — it was iteration, not inference.
- Each rung is a **fixed point**, not a sweep: propagate the overlap rule alone
  to exhaustion over rows and columns, then the full placement intersection to
  exhaustion, then probe refutation. A cell's rung is the level at whose fixed
  point it was first settled. Monotone propagation is confluent, so a rung
  becomes a function of the clue set alone.
- The overlap rule is applied **relative to the line's known cells** (leftmost
  and rightmost placements consistent with what is known, intersected), not to
  the bare clue.
- ADR-0029/R2 still forbids re-solving, and the phases satisfy it: one monotone
  forward solve, the board never reset, the search never re-entered. Cheapest
  technique first should not cost more than today's single mixed pass.
- Verdicts must stay identical (CON-005): the final fixed point under the full
  technique set is the same set of cells whichever order the techniques ran in.
- New AC from ADR-0029/R5: a clue set and its transpose yield identical per-rung
  counts, rung list and score.
  *test:* `PropertyTest_SolveStrategies_RungsInvariantUnderTransposition`
- AC-A is re-worded by the above; the existing `probe_contradiction` overlay
  from refuted siblings survives as the third level's fixed point.

Sequencing unchanged: CARD-074/075 may start on the mask and witnesses now;
CARD-076 and CARD-072 item 1 wait on the reworked tags.

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


### Rung rework (ADR-0029 revision of 2026-09-12) — what changed

Item 3 only. The undecided mask, the second witness, `SolveResult.witnesses`,
the orchestrator storage and their tests (AC-107..AC-110, AC-131, EC-011,
EC-012) are untouched from d81c387.

**The ladder is three rungs, applied as stratified fixed points.**
`cross_line` is deleted entirely — constant, tag, `RUNG_ORDER` member, export
and tests. `solve` now runs three phases over **one** board, never resetting it
and never re-entering the search (ADR-0029/R2):

1. `propagate_overlap` — the knowledge-relative leftmost/rightmost overlap rule
   alone, to a fixed point over rows and columns. Everything it settles is
   `simple_overlap`.
2. `propagate` — the existing full `line_intersection`, continuing from level
   1's board and starting with **every line dirty**. Everything newly settled
   is `line_dp`. Levels 1 and 2 together reach exactly today's first
   `propagate` fixed point (monotone propagation is confluent, and level 2
   examines every line at least once under the dearer rule), which is what
   keeps `line_logic_cells`, the undecided mask and every verdict where they
   were.
3. `_probe_fixed_point` — if the board is still open, probe every still-unknown
   cell with both values; a value whose propagation contradicts forces the
   opposite one, which is propagated; repeat until a full pass forces nothing.
   Everything newly settled is `probe_contradiction`, attributed by diffing the
   phase's end state against its start rather than by watching individual
   deductions (a deduction's cascade is the order-sensitive part). No cap, no
   budget, no width limit, no ordering heuristic — deliberately, because any of
   those would make a rung a fact about the solver.

The search then runs exactly as before, on the level-3 fixed point.

**The search writes no rung tags.** `_record_forced` / `_tags_with_forced` and
the `forced` accumulator threaded through `_search`/`_expand`/`_descend` are
gone. Which cell a refutation reaches below a guess depends on where the search
branched, so a tag written there is a fact about search order, not about the
clue set (ADR-0029/R5) — and a puzzle whose search ran at all is `Tier.GUESS`
under ADR-0025 rather than graded on this ladder. Cells the search settles
carry `None`.

**Level 3 calls `_lookahead`, not `_probe`.** Same six lines, deliberately a
different module-level name: `_probe` is the *search's* unit of work —
`backtracks` counts its refusals and `tests/test_solver.py` spies on it to
check the signals describe the deciding round — and level 3 runs before any
round exists. Level 3's refutations are therefore not counted in `backtracks`,
which keeps that signal's pre-existing meaning.

**Level 3 does not report a zero-solution verdict itself.** When both values of
some cell are refuted, the phase stops and hands the last consistent board to
the search, which reaches count 0 with its own `branch_nodes` / `backtracks`.
Reporting 0 from the phase would have meant a contradictory clue set coming
back with both search signals at zero, i.e. claiming line logic had settled it.
The cost is one extra node on a path generation almost never takes (a candidate
derived from a real grid always has at least one solution).

**The level-1 greedy, and the trap in it.** `overlap_extremes` computes the
leftmost and rightmost start of every run *consistent with the line's known
cells*, natively in `solver/` (ADR-0029/R4 — no `clues.py` import;
`tests/test_cli.py`'s structural guard stays green). Consistency is two
conditions, not one: no run may overlap a known-**empty** cell, **and** no
known-**filled** cell may be left uncovered. The second is what a naive greedy
misses — it strands a filled cell in a gap and every mask read off the result
then claims cells no placement agrees on. It is handled by computing a
feasibility table backwards first (`feasible[idx][pos]`, where skipping a cell
is legal only when it is not known filled) and taking the earliest start that
keeps the remainder feasible, so coverage is a property of the table rather
than a fix-up. The rightmost placement is the leftmost one of the mirrored
line, so the delicate half exists once.

Those starts are the componentwise **minimum and maximum** over all feasible
placements, not just two particular placements (argument in the docstring), and
that is cross-checked rather than argued:
`test_the_overlap_greedy_finds_the_true_extreme_start_of_every_run` compares
them against an enumeration of every feasible placement over a seeded corpus of
**800** `(runs, length, known_filled, known_empty)` triples (floor asserted at
500 inside the test, ≥200 of them feasible), and
`test_overlap_deduction_never_claims_more_than_every_placement_agrees_on` pins
both directions of the rung's definition on the same corpus: the rule never
claims more than every placement agrees on (soundness — an unsound level 1
would write a cell some solution contradicts, i.e. CON-005), and never claims
more than `line_intersection` does (weakness — otherwise "only the DP could
reach this cell" means nothing).

**New test, ADR-0029/R5:**
`PropertyTest_SolveStrategies_RungsInvariantUnderTransposition` ->
`tests/property/test_solver_witnesses.py::test_rungs_are_invariant_under_transposition`,
240 seeded cases (floor 200 asserted inside the test). It checks four things of
increasing strength — per-rung cell counts, the ordered rung list, ADR-0029's
derived 0..100 score, and the per-cell tag map being the exact transpose — plus
that whether the search ran at all is orientation-free. Measured separately on
600 random grids of 3..15 a side: **600/600 transpose-identical**, against 92%
*differing* before the rework.

All three rungs are reachable, which the first cut's `line_dp` was not. On that
600-grid survey: `(simple_overlap,)` 440, `(simple_overlap, probe_contradiction)`
65, `(simple_overlap, line_dp, probe_contradiction)` 46, `(simple_overlap,
line_dp)` 20, `(probe_contradiction,)` 15, `()` 14.

### Measurements

**Item 8 — `tests/bench_generate.py` at 20x20, `report()`, two runs a side,
`GENERATION_BUDGET_SECONDS = 30`:**

    sample (density, seed)   before #1  before #2  |  after #1   after #2
    30, 0                      1.316s     1.326s   |   2.478s     2.466s
    40, 0                     30.002s    30.002s   |  30.002s    30.002s  (timeout)
    50, 0                      0.050s     0.049s   |   0.090s     0.088s
    60, 0                      0.004s     0.004s   |   0.009s     0.009s
    30, 1                      1.250s     1.250s   |   2.117s     2.119s
    40, 1                     30.003s    30.003s   |  30.001s    30.003s  (timeout)
    50, 1                      0.046s     0.046s   |   0.103s     0.104s
    60, 1                      0.005s     0.005s   |   0.010s     0.010s
    30, 2                      4.311s     4.345s   |   4.986s     5.010s
    40, 2                     30.002s    30.003s   |  30.001s    30.024s  (timeout)
    50, 2                      0.128s     0.128s   |   0.248s     0.566s
    60, 2                      0.002s     0.002s   |   0.004s     0.007s
    30, 3                      1.712s     1.720s   |   2.462s     2.629s
    40, 3                     29.057s    28.989s   |  18.718s    18.594s
    50, 3                      0.021s     0.022s   |   0.034s     0.033s
    60, 3                      0.002s     0.002s   |   0.005s     0.005s
    30, 4                      1.700s     1.721s   |   2.381s     2.402s
    40, 4                     14.029s    14.119s   |  24.425s    24.500s
    50, 4                      0.006s     0.006s   |   0.008s     0.008s
    60, 4                      0.005s     0.006s   |   0.011s     0.011s

    p95 (nearest-rank, n=20)  30.002s    30.003s   |  30.001s    30.003s

**p95 is unchanged**, and as the previous cycle noted it is useless as a
sensitivity measure: it is censored at the budget. The honest numbers:

    sum of all 20 samples         143.651 , 143.748  |  148.093 , 148.590   (+3.2%)
    sum minus the 3 censored       53.644 ,  53.740  |   58.089 ,  58.561   (+8.4%)
    sum minus all four density-40  10.558 ,  10.632  |   14.946 ,  15.467   (+43%)

The last row is the clean one — the sixteen samples that are not bounded by the
30s budget at all — and it says the solve got about **43% slower** on this
corpus. AC-037's gate is still met for the same reason as before (it is timed
against the same saturated p95), but the cost is real and is not hidden by it.
The two density-40 samples that moved in opposite directions (seed 3: 29.0s ->
18.7s; seed 4: 14.0s -> 24.5s) are budget-bound requests where level 3 changes
which candidates are discarded and how far the request gets before the deadline;
they are not a speedup and a slowdown, they are noise at the budget.

**The generation discard path — `orchestrator.generate` on 20 seeded 20x20
requests at density 20, all of which end in `GenerationAbandoned` (20 candidates
each, none unique), so every candidate pays level 3 in full and nothing
amortises it:**

    run              before      after
    #1              10.191s     25.420s
    #2              10.127s     22.754s
    mean per request  0.508s      1.204s

**This is a 2.4x regression (+137%) and it is the cost of the rework, not a
tuning oversight.** Level 3 probes every still-unknown cell with both values
before the search starts; a 20x20 density-20 candidate leaves ~300 cells open
at line logic's fixed point, so that is ~600 extra propagations per candidate,
on a path where today's round-0 descent finds a second solution in a couple of
hundred plain nodes. The phase is pure overhead on an ambiguous candidate — it
forces almost nothing there, by construction, because a massively ambiguous
board is exactly the board single-cell lookahead cannot refute anything on.

It is reported rather than tuned away on purpose. Every obvious mitigation — a
probe budget, a width cap, a "skip level 3 when the undecided mask is large"
predicate — buys the time back by making which cell gets which rung depend on
the solver's bookkeeping, which is the exact defect this revision exists to
remove (ADR-0029/R1, R5). Whether the discard path can afford it is an owner
decision, and the honest levers are at a different level: run level 3 only when
a grade is actually wanted (`--difficulty` / the admin re-grade batch) and not
on every discarded candidate, or accept the cost. Both are outside this card.

**Item 7 — ADR-0024's repair precondition, re-measured.** The change *could*
have moved it: the search now starts from the level-3 fixed point, so it can
find a different witness pair. Re-measured on the same corpus
(`tests/property/test_solver_uniqueness.CASES`, 2400 cases, `SEED = 20260827`):

    MANY verdicts                                         262   (unchanged)
      ... of which carry a parent grid                    241   (unchanged)
      ... whose disagreement set holds a filled AND
          an empty cell of the parent grid                232   (unchanged)
    share of MANY-with-a-parent                        96.27%   (232/241, unchanged)
    share of all MANY verdicts                         88.55%   (232/262, unchanged)

    parent grid IS one of the two witnesses               162   (was 159)
      ... and the filled/empty pair exists there          162   (100.00%)

**The headline number is unchanged.** The only shift is that three more
`MANY` verdicts now return the parent grid as one of the two witnesses, which
is the search starting from a board level 3 had already narrowed. The nine
counterexamples and their shape (parent is a *third* solution, whole
disagreement set empty in it) are the same nine; Increment 9 still needs
ADR-0024's fallback on roughly 1 case in 27.

### Test results and one unresolved conflict

Full suite: **2903 tests, 41 failed, 26 skipped, 0 errors.** The four files the
rework was not allowed to touch are unedited (`git diff` empty) and green:
`tests/test_solver.py` apart from the two failures below, `tests/test_timeout.py`,
`tests/test_cli.py` (including the ADR-0007 structural import guard) and
`tests/property/test_solver_uniqueness.py` (EC-001/CON-005, 2400 cases,
identical counts).

**Three new failures, one root cause, and it is a direct collision between two
of this rework's own requirements.** ADR-0029's revision makes probing a
*phase*, and the card's own invariant is that when level 3 completes a puzzle
`branch_nodes` must be 0, so that the puzzle is gradeable Hard rather than
`Tier.GUESS`. `BRANCHING_ROWS`/`BRANCHING_COLUMNS` — the 6x6 fixture three
tests use as "the puzzle that needs a guess" — **is** completed by level 3:
16 cells at `simple_overlap`, 20 at `probe_contradiction`, `branch_nodes` 0,
verdict still `1`. The fixture's premise is now false about the puzzle:

    tests/test_solver.py::test_reports_unique_solution_that_needs_backtracking
        assert result.signals.branch_nodes > 0
    tests/test_solver.py::test_signals_report_partial_line_logic_coverage_when_guessing_is_needed
        assert signals.branch_nodes >= 1
    tests/test_difficulty.py::test_a_puzzle_that_needs_guessing_scores_above_one_that_does_not
        assert needs_guessing.signals.branch_nodes > 0

No verdict moved and no count moved; what moved is that this particular puzzle
no longer needs a guess. The three assertions cannot be satisfied at the same
time as the branch-nodes-zero invariant, so they are left failing for the owner
rather than papered over — weakening level 3 to keep a fixture green would be
exactly the hidden constant ADR-0029/R1 and R5 forbid, and `test_solver.py` is
a guardrail file this card may not edit. The remedy is a one-line fixture swap
in each: a clue set that still branches after level 3 — the 10x10 switching
block (`branch_nodes` 3) or `tests/test_timeout.py`'s 8x8 seed-22 grid
(`branch_nodes` 6) — both of which survive the probing phase with cells open.
`test_difficulty.py` is left failing with them deliberately, so the three
instances of the one decision stay visible together.

The remaining 38 failures are the machine's pre-existing set (13
`test_sourcing_image.py`, 5 `test_wave1_e2e.py`, 5 `test_batch_history.py`, 4
`test_wave2_async_generation.py`, 4 `test_derive_shape.py`, 3 `test_nudge.py`,
one each in `test_web_upload.py`, `test_nudge_reporting.py`,
`test_export_pdf.py`, `property/test_grid_dimensions.py`) — the same files and
the same causes as the recorded baseline of 40, with the known order-flakiness
in the three async/DB files accounting for the difference (batch_history 5
rather than 6, wave1 5 rather than 4, wave2 4 rather than 5). None of them
touches the solver.

### Cycle 3 — scoping attribution to puzzles, and what it bought

**The change in one sentence.** ADR-0029 and ADR-0025 were amended (Decision,
R5 and a History entry on ADR-0029; a History entry only on ADR-0025), and the
solve now establishes ambiguity *before* paying for level 3, so the generator's
discard path no longer computes an attribution nobody reads.

**How the speculative MANY check is sequenced.** Between level 2 and level 3,
on a board line logic did not finish, `solve` runs round 0's plain descent once
— `_round(0)`, so the same probe width and the same node limit the restart
schedule already gives it — with its own throwaway `_Counters`. Two verified
distinct solutions is a verdict on its own terms: both are checked against the
clues by `_verified_grid`, sibling branches are disjoint so they differ, and
the board searched is line logic's fixed point, which every solution extends.
So that case returns immediately as `MANY`, carrying the two witnesses, the
level-2 undecided mask, that round's own counters as the signals (it *is* the
deciding round, F-001), and no rung attribution — level 3 never runs. Anything
else — a cut-off, or a round that finished with 0 or 1 solutions — proves
nothing this solve keeps: its findings **and its counters are discarded whole**,
the established `_CUT_OFF` treatment, and the solve carries on into level 3 and
the real restart loop with fresh counters exactly as before. A uniquely
solvable clue set therefore always reaches level 3, so its tags stay complete
and order-independent, and the only price it pays is one bounded round of work
it would have done anyway.

Attribution is dropped in one place, `solve`'s local `finish`, for every exit
whose count is not 1 — not only the speculative one. That is the ADR rule, not
an optimisation: a clue set with 0 or >= 2 solutions is not a puzzle and has no
grade, so a `MANY` verdict reached the long way round reports nothing either.

**`_probe_fixed_point`'s pass restart.** Checked; the defect reported in the
cycle-2 review is not present in the code as committed to this worktree. The
pass already continues scanning after a forced value (it skips cells that
became known on the way, `search.py`'s `if board.cell_is_known(...): continue`)
and breaks out only on a contradiction or on a completed board; the outer loop
repeats only while something was forced. That is the O(U)-per-pass shape the
review asked for, so no change was made. The fixed point is, as before, the
first complete pass that forces nothing.

### Measurements

**Density sweep at 20x20 — 6 seeded `orchestrator.generate` requests per
density, seconds per request, two runs:**

    density   before cycle 3   after #1   after #2   change
    20             1.196         0.553      0.555     -54%
    25             1.660         1.074      1.073     -35%
    30             2.803         2.508      2.481     -11%
    35             6.346         6.164      6.141      -3%
    50             0.094         0.074      0.075     -21%
    65             0.004         0.003      0.004       --

Run-to-run spread is under 1% on every density, so the shape is real. The gain
is concentrated exactly where the cycle-2 regression was: the low-density
discard path, where every candidate is ambiguous and level 3 used to probe
~300 open cells with both values before the search got to find a second
solution a couple of hundred plain nodes in. Density 20 at 0.553s/request is
now within ~9% of the 0.508s/request the *pre-rework* solver managed on the
cycle-2 discard-path corpus, against the 1.204s the rework cost there — so the
2.4x regression cycle 2 reported and refused to tune away is paid back
essentially in full, and paid back at the level ADR-0029 says it must be (what
gets attributed) rather than inside the ladder (how it gets attributed).

The higher densities move least, and that is the expected shape rather than a
disappointment. At density 35 a growing share of candidates are uniquely
solvable — they take no skip at all and pay for level 3 in full, as they must
to be graded — and the remaining time is budget-bound requests where the
deadline, not the solver, decides when to stop. At 50 and 65 line logic
finishes nearly every candidate at level 2, so neither the speculative round
nor level 3 ever runs.

**Transposition invariance (ADR-0029/R5) — still holds.** 600 random grids of
3..15 a side, seeded, each solved upright and transposed, comparing per-rung
cell counts, the ordered rung list, the per-cell tag map (as an exact
transpose) and whether the search ran at all:

    transpose-identical                600 / 600
      ... of which uniquely solvable   275 / 275   (the non-trivial half)
    verdicts                           275 unique, 325 MANY

The 275 uniquely-solvable cases are where the check has teeth — they carry full
attribution in both orientations. The 325 ambiguous ones now report nothing
either way round, which is R5's trivial half by the amended rule rather than an
untested case. The corpus property test
(`tests/property/test_solver_witnesses.py::test_rungs_are_invariant_under_transposition`,
240 cases, floor 200 asserted inside the test) passes unchanged, including its
`reached == set(RUNG_ORDER)` guard that the corpus still exercises all three
rungs.

**Rung mix over those 600 grids:** `(simple_overlap,)` 269,
`(simple_overlap, probe_contradiction)` 4, `(simple_overlap, line_dp)` 2, and
`()` 325 — the ambiguous ones, which by the amended rule now report an empty
list rather than the tags of a grade they do not have.

### The three stale tests, repaired (G-1 amendment)

`tests/test_solver.py`

- `test_reports_unique_solution_that_needs_backtracking` ->
  **`test_reports_unique_solution_settled_by_lookahead_without_a_branch`**. It
  now asserts the true and more valuable fact about this clue set: propagation
  stalls (`line_logic_cells < total_cells`), level 3 finishes it, and
  `branch_nodes == 0`, so ADR-0025 grades it on the ladder instead of calling
  it `Tier.GUESS`. The verdict and the round-trip check on the solution grid
  are unchanged, character for character.
- `test_signals_report_partial_line_logic_coverage_when_guessing_is_needed` ->
  **`test_signals_report_partial_line_logic_coverage_when_lookahead_is_needed`**.
  Same fixture, same `line_logic_cells < total_cells` claim — which was always
  the point of the test — with the branch assertion inverted to `branch_nodes
  == 0` and `backtracks == 0`, because the signals must now say *both* things
  at once: partial line-logic coverage and no search.
- **New: `test_signals_report_the_search_running_on_an_ambiguous_clue_set`.**
  Genuine search-effort coverage, kept rather than lost. It uses the 10x10
  switching block — an *ambiguous* clue set, where lookahead can refute nothing
  because both values of all four block cells extend to a real solution, so the
  `MANY` verdict can only come from the search branching. Verified before being
  relied on: `solution_count == MANY`, `branch_nodes == 3`,
  `line_logic_cells == 96` of 100.

`tests/test_difficulty.py`

- `test_a_puzzle_that_needs_guessing_scores_above_one_that_does_not` ->
  **`test_a_puzzle_that_needs_lookahead_scores_above_one_solved_by_overlap`**.
  Its old premise is dead for generated puzzles, so it is re-pointed at the
  ladder's actual ordering claim (ADR-0029/R1): a puzzle whose list carries a
  `probe_contradiction` rung scores strictly above one solved by overlap alone.
  Both puzzles are still solved for real; the test additionally pins that it is
  the *rung* and not a branch that separates them (`branch_nodes == 0` on the
  harder one). `difficulty.py` is untouched (G-4) — CARD-076 still owns the
  formula.

The `BRANCHING_ROWS` / `BRANCHING_COLUMNS` constants are kept under their
historical name in both files, with a comment saying why, so the round-trip
checks stay comparable across the change. Only the assertions about branching
moved.

Two tests of this card's own — `tests/test_solver_witnesses_and_rungs.py`'s
`test_guess_is_not_appended_to_the_rung_list` and
`test_a_cell_the_search_settles_carries_no_rung` — asserted the *old* rule that
a `MANY` solve tags every cell but the ambiguous ones. Under the amended R5 it
tags none of them, so the first was re-pointed at the two shapes that could
still leak a fourth name into the list (a puzzle needing a probe, and an
ambiguous clue set) and the second was re-purposed as
**`test_a_clue_set_that_is_not_a_puzzle_carries_no_rung_attribution`**, which
pins the new rule directly on a `MANY` and a zero-solution clue set.
`_replay_untagged`, the ADR-0029/R2 no-extra-work baseline, mirrors the
speculative round so the call counts stay comparable.

### Test results

Full suite: **2904 tests, 36 failed, 26 skipped, 0 errors.**

The three files this card may not edit are unedited (`git diff` empty) and
green: `tests/property/test_solver_uniqueness.py` (EC-001/CON-005, 2400 cases,
identical counts), `tests/test_timeout.py` and `tests/test_cli.py` — including
ADR-0007's structural import guard. `tests/helpers/brute_force_oracle.py` is
also unedited.

All 36 failures are the machine's pre-existing set, in the same files and with
the same causes as the recorded baseline of 40 (13 `test_sourcing_image.py`, 5
`test_batch_history.py`, 4 `test_derive_shape.py`, 4
`test_wave2_async_generation.py`, 3 `test_nudge.py`, 3 `test_wave1_e2e.py`, one
each in `test_export_pdf.py`, `test_nudge_reporting.py`, `test_web_upload.py`
and `property/test_grid_dimensions.py`). The difference from 40 is the known
order-flakiness in the three async/DB files. **No solver or difficulty test
fails**, and the three stale failures from cycle 2 are gone.
