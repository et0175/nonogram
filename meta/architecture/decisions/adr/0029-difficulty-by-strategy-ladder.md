# ADR-0029: Difficulty is the rung of the hardest solving strategy required

**Status:** Accepted (replaces ADR-0013)
**Date:** 2026-09-12
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** rewrite
**Pattern:** —
**API-Posture:** —

## Context

FR-026 (2026-09-12) requires a puzzle solved entirely by line logic to be
graded across the *whole* difficulty scale by how much line reasoning it
needed, so that two line-solvable puzzles of different depth land in
different bands (AC-118: a >= 200-puzzle line-solvable corpus must populate
Easy, Medium and Hard; AC-119: the deeper of two line-solvable 20x20 puzzles
scores strictly higher). Under ADR-0013's `score = 100 * effort * relief` that
is impossible by construction: the two effort terms a line-solvable puzzle
zeroes carry 85 points of the scale between them, so such a puzzle scores at
most 15 (`docs/GENERATION_ALGORITHM.md` §7, `src/nonogram/difficulty.py`) and
can never leave Easy. Retuning ADR-0013's weight table cannot fix that — the
formula's *shape* has to change, which is why FR-026 marks ADR-0013 as
pending supersession rather than revision.

NFR-007 and CON-014 add a second force: no term of the score and no input of
the tier decision may be derived from elapsed wall-clock time (AC-122,
EC-016). ADR-0013 rejected exactly that (`exclude_wall_clock_time`) on the
grounds that FR-009 listed solve time among its five signals; today its
`time_pressure` term (weight 0.15, budget 5s per 400 cells) makes a boundary
candidate score differently on a slower machine, so ADR-0015's "same seed
replays the same run" holds only when no `--difficulty` is requested
(`docs/GENERATION_ALGORITHM.md` §10.2 finding 3, AC-123).

ADR-0025 (DEC-030), which this decision depends on, has already fixed the
tier model: `Tier` is Easy, Medium, Hard, **Guess**; any solve with
`branch_nodes >= 1` is Guess by that fact alone (EC-015), and the three score
bands grade *line-solvable* puzzles only. The scale this ADR defines therefore
has no branch term to carry — it must order puzzles the search never
branched on, using signals the solve already produces: propagation sweeps to
fixed point, the share of cells settled early, and which lines needed the
full placement DP rather than the simple leftmost/rightmost overlap
(FR-026's minimum signal list). ADR-0005's 33/66 tertile cutoffs sit on
whatever scale replaces ADR-0013's and must be accounted for.

A third force arrived with the same intake. FR-029 (owner request, CARD-072)
requires every generated puzzle to carry the *ordered list of solving
strategies* its verifying solve required, drawn from one fixed enum
(provisionally `simple_overlap`, `line_dp`, `cross_line`,
`probe_contradiction`, `guess`), derived from the same solve that confirmed
uniqueness and never from a second one (ADR-0013's no-solver-re-entry rule,
which survives whatever else changes), a pure function of the clues
(EC-017, EC-018), persisted in the DB column `strategies_used`, exported as a
`strategies` array (AC-140) and shown and filterable in the admin review
(AC-141..AC-143). The solver's `SolveSignals` (COMP-005,
`src/nonogram/solver/search.py`) today reports `line_logic_cells`,
`total_cells`, `branch_nodes`, `backtracks` and `elapsed_seconds` — none of
which says which technique settled which cell. Whatever grades line depth
has to be reconciled with that list: a numeric scale defined independently
of it would be a second account of the same solve, kept consistent by hand.

The constraints on any answer: ADR-0007's lateral-import rule (the solver may
not import `clues.py`; enforced by `tests/test_cli.py`'s structural guard),
CON-004 (difficulty is a classifier of produced candidates, never a
construction target), and the existing consumers of a numeric 0..100 score —
the JSON export, the admin DB's `difficulty_score` column, POL-004's resample
predicate and the web UI — which have no reason to be broken if the scale
can keep its range.

## Decision

We adopt **strategy_ladder_ordinal**: the difficulty of a line-solvable
puzzle is the **rung of the hardest solving technique its one verifying solve
required**, on the ordered ladder

    simple_overlap  <  line_dp  <  cross_line  <  probe_contradiction

`guess` is *not* a rung on this scale: a solve with `branch_nodes >= 1` is
`Tier.GUESS` under ADR-0025 and is not graded here. Within a rung, puzzles are
ordered by a secondary count fixed by this ADR: **the number of cells whose
settling deduction was at that rung, divided by the puzzle's total cells**.

This satisfies FR-026/AC-118/AC-119 because line-solvable puzzles are now
spread over four qualitatively different levels of line reasoning instead of
being pinned under 15 points; it satisfies NFR-007/CON-014/EC-016 because a
technique classification has no clock in it by construction; and it satisfies
FR-029 because the same classification *is* the strategies list. That last
point is the decisive advantage over the alternative: one derivation, taken
once from the one verifying solve, feeds both the tier and CARD-072's
`strategies_used` — the ordered list of rungs present is the FR-029 list, and
the highest rung present is the difficulty. There is no second scale to keep
consistent with the list, no weight table that can drift from it, and the
grade explains itself to a book editor in the list's own words ("needs
cross-line reasoning").

Concretely:

- **Classification lives in the solver (COMP-005) as part of the one solve.**
  Each cell records the rung of the deduction that settled it; nothing is
  re-solved to classify (ADR-0013's no-re-entry rule is carried forward
  unchanged as ADR-0029/R2). The four rungs are defined over the solver's
  own events:
  - `simple_overlap` — the cell is settled by a line deduction that the
    leftmost/rightmost overlap rule alone yields. Decided *per line
    deduction* by natively re-deriving the overlap masks (sum of runs plus
    gaps against the line length, leftmost and rightmost placements
    intersected) and comparing them with what the full placement DP
    settled: a cell the overlap masks already fix is `simple_overlap`.
    This is a native reimplementation inside `solver/` — no import of
    `clues.py` (ADR-0007, `tests/test_cli.py`), following the precedent of
    `propagate.py`'s `mask_runs`.
  - `line_dp` — the cell is settled by a line deduction only the full
    placement intersection yields (the DP fixed it and the overlap masks did
    not).
  - `cross_line` — the cell is settled in any propagation sweep after the
    first, i.e. the deduction needed cells fed in from perpendicular lines.
    This ADR pins the sweep semantics as part of the contract: a sweep is
    one pass of `propagate`'s outer loop over the dirty rows and then the
    dirty columns, and "the first sweep" is the pass that starts from the
    blank board; a solver refactor that changes what a sweep is re-grades
    puzzles and must say so in a revision of this ADR.
  - `probe_contradiction` — the cell is forced because assigning it the
    opposite value contradicted under propagation (a probe refuted one
    value; no branch was taken, so `branch_nodes` stays 0 only when every
    node the search expanded resolved this way — otherwise ADR-0025 applies
    first).
  The ordered list of distinct rungs present, in ladder order, is FR-029's
  `strategies` list; `guess` is appended if and only if `branch_nodes > 0`
  (EC-017), which is the same fact ADR-0025 keys the tier on.
- **The 0..100 score is retained as a derived presentation, not as the
  grade.** `score = rung_base + within_rung_share * rung_width`, with the
  four rungs mapped onto equal 25-point bands: `simple_overlap` 0..25,
  `line_dp` 25..50, `cross_line` 50..75, `probe_contradiction` 75..100. The
  within-rung share is the secondary count above (cells settled at the top
  rung / total cells), so two puzzles topping out at the same rung differ by
  how much of the grid needed that technique. The export, the DB column and
  POL-004 keep a numeric score in the same range; the *meaning* of the number
  is now "which rung, and how much of it", and the tier is derived from the
  rung, not the other way round.
- **ADR-0005's cutoffs stay at 33/66 for now and therefore fall inside
  rungs** (33 inside `line_dp`, 66 inside `cross_line`). This is provisional
  by design: a tier-per-rung mapping (e.g. Easy = `simple_overlap`, Medium =
  `line_dp`, Hard = `cross_line` and `probe_contradiction`, or bands drawn on
  rung boundaries) is the expected recalibration once a >= 200-puzzle
  line-solvable corpus (AC-118) has been measured. That recalibration is
  **owed, not decided** here; ADR-0005 is revised by this ADR only in that
  its bands now sit over rungs rather than over a weighted sum.
- **Size and density no longer enter the score.** This is an explicit
  departure from ADR-0013, where both acted as normalisers of *effort*
  (branch nodes per cell, time against a size-relative budget). A rung is not
  effort: which technique a puzzle needs is a fact about the puzzle, not
  about the grid's size, and a 30x30 that never leaves simple overlap is
  exactly as Easy as a 10x10 that never does. The within-rung share is
  already normalised by total cells, which is the only place size appears.
- **No wall-clock term anywhere.** `elapsed_seconds` stays on `SolveSignals`
  as telemetry (NFR-001 is still measured by it) and is not an input to the
  scorer or the tier decision (CON-014). ADR-0013's rejected alternative
  `exclude_wall_clock_time` thereby becomes the rule; ADR-0015's "same seed
  replays the same run" consequence now holds with `--difficulty` as well,
  on any machine and at any host speed (AC-123).
- **The classifier interface between COMP-005 and COMP-006 is unchanged in
  kind.** The solver reports per-rung cell counts (and the ordered rung
  list) on `SolveSignals`; `difficulty.py` stays a pure function of those
  counts and `branch_nodes`, with ADR-0025's single `(score, branch_nodes)`
  classifier now taking the rung-derived score. The scorer still never
  imports the solver (ADR-0007; the `SolverSignals` protocol gains members).

The owner chose the ladder after seeing a worked `depth_weighted_sum`
example. The weighted sum is the smaller change to today's code and orders
puzzles more finely, but it would put a second scale beside the strategies
list — a set of weights that are guesses until calibrated, and a number a
book editor cannot read back into what the puzzle demands. The ladder's
coarseness inside a rung is the price of the grade being the same fact the
strategies list records.

## Alternatives considered

### depth_weighted_sum (the surfaced default)

Keep ADR-0013's shape — normalised signals, fixed weights, one named tunable
table, `0..100` — and replace the effort signals with sweeps to completion
(against a size-relative sweep budget), one minus the first-sweep decided
share, and the share of lines that needed the DP; drop `time_pressure`; with
ADR-0025's tier the branch term leaves the score. This is the smallest
conceptual move from ADR-0013 and keeps the score continuous, so AC-119's
strictly-greater case is met without a technique classifier. The owner saw a
worked example and rejected it: the weights and the sweep budget are
calibration guesses on a scale nobody has observed (the same weakness
ADR-0005 accepted once already), the sweep count is a property of *this*
propagation order and would silently re-grade every puzzle on a solver
refactor, and — decisively — it would be a second account of the solve next
to FR-029's strategies list, with nothing but discipline keeping the two
consistent. Once CARD-072 ships the list, the weighted sum's only remaining
advantage (finer ordering) is bought with a number that explains nothing.

### keep ADR-0013 (retune the weights)

Leave `score = 100 * effort * relief` and retune `SIGNAL_WEIGHTS` so that
line-solvable puzzles spread further. Rejected because it cannot meet
FR-026: a line-solvable puzzle zeroes the line-logic-gap and branch-pressure
terms exactly, so its score is bounded by `100 * w_solve_time` whatever the
weights are — it can never leave Easy without giving the wall-clock term the
majority of the scale, which is precisely what NFR-007/CON-014 forbid. The
formula also keeps the machine-dependent `time_pressure` term, so ADR-0015's
reproducibility promise would stay broken under `--difficulty`.

## Consequences

### Positive

- Line-solvable puzzles span the whole scale by the kind of reasoning they
  need (AC-118, AC-119), and the grade is legible to a non-programmer: a
  Hard puzzle "needs cross-line reasoning", a Medium one "needs the full
  placement DP on some lines".
- One derivation feeds two artefacts. The ordered rung list is FR-029's
  `strategies` (CARD-072) and its maximum is the difficulty; they cannot
  disagree because they are the same data read twice (AC-135, EC-018).
- Deterministic on every machine and at every host speed by construction:
  no clock, no size budget, no weight table. NFR-007, CON-014, EC-016 and
  AC-122/AC-123 hold structurally, and ADR-0015's same-seed guarantee now
  covers requests with `--difficulty`.
- No calibration surface to guess at before data exists: the ladder order is
  a statement about techniques, not a weight to tune. The only owed
  calibration (where the tier boundaries sit on the ladder) is a single
  mapping change once AC-118's corpus is measured.
- The 0..100 range, the export field, the DB column and POL-004's predicate
  survive unchanged in type; only the number's meaning changes.

### Negative

- Coarse inside a rung: puzzles that all top out at `line_dp` are separated
  only by the within-rung share. AC-119's strictly-greater case must hold
  through the tiebreak when both puzzles share a top rung — the classifier
  test must cover that, not only the cross-rung case.
- A technique classifier inside the solver is a larger change than adding
  counters: every settling deduction must be tagged with its rung, the
  overlap masks re-derived natively per line deduction, and the sweep
  semantics pinned. The rungs are a design choice of ours (two classifiers
  could rank the same puzzle differently), so the definitions in the
  Decision are normative and a change to any of them re-grades the corpus.
- **Every stored `difficulty_score` and tier in the admin DB is wrong under
  this scale and must be re-graded by re-solving** (Migration: rewrite).
  Grandfathering is not an option: NFR-007's machine-independence would be
  false for old rows, and a book assembled from a mix of ADR-0013 and
  ADR-0029 grades would be mislabelled. A re-grade batch over the admin DB
  is a real operational job — it re-solves every accepted puzzle — and is
  flagged as a risk in this ADR's return.
- ADR-0005's 33/66 cutoffs now cut through rungs, so until the owed
  recalibration lands, "Medium" straddles the top of `line_dp` and the bottom
  of `cross_line`. The tier boundaries are therefore less legible than the
  rungs themselves for the interim.
- Per-cell rung tagging adds work to the solver's hot loop; CARD-072's AC-5
  (20x20 benchmark within noise, `tests/bench_generate.py`) is the guard, and
  the tag must be cheap enough that `--difficulty`'s resample loop, which
  solves every candidate, does not slow measurably.

### Neutral

- ADR-0013 is superseded by this ADR (its formula, its five-signal
  combination and its size/density normalisers are all retired; its
  no-solver-re-entry rule and its 0..100 range are carried forward). The
  superseded stamp on ADR-0013 itself is a follow-up edit, as is marking
  DEC-013 superseded in `resolved.yml`.
- ADR-0005 is revised, not superseded: its cutoffs are unchanged in value but
  now sit over rungs; the tier-per-rung recalibration is owed once AC-118's
  corpus is measured. ADR-0015 gains a History entry: reproducibility now
  holds with `--difficulty` (§10.2 finding 3 closed). ADR-0025 is the tier
  model this ADR sits under and is untouched.
- FR-009's AC-022 ("weighted combination of all signals") and AC-023 ("zero
  backtracking scores easiest") are superseded by this decision and must be
  re-worded in `requirements.yml` as a follow-up (not done here); FR-029's
  provisional enum members are confirmed as written — `simple_overlap`,
  `line_dp`, `cross_line`, `probe_contradiction`, `guess` — and its
  `enum_provisional` note can be closed.
- `SolveSignals` gains per-rung cell counts and the ordered rung list;
  `line_logic_cells` remains for NFR-001 reporting but no longer drives the
  score. `difficulty.py`'s `SignalWeights`, `SIGNAL_WEIGHTS`,
  `NormalizedSignals`, `clue_density` and `SECONDS_PER_CELL_BUDGET` are
  retired with the formula.
- CARD-072's item 1 (solver telemetry) is unblocked: the taxonomy is fixed,
  and the card's provisional enum is now the decided one. The re-grade of
  stored rows is a separate card (the migration), not part of CARD-072.
- `docs/GENERATION_ALGORITHM.md` §7 (the formula) and §10.2 finding 3 need
  rewriting to match.

## References

- DEC-031 (resolved by this ADR)
- CTX-001 (Puzzle Creation — owns the solve, the score, the tier and every
  surface the strategies list reaches)
- FR-026, AC-118, AC-119 (line-solvable puzzles span the scale)
- FR-029, AC-135..AC-143, EC-017, EC-018 (strategies saved with the puzzle;
  the same derivation)
- NFR-007, CON-014, EC-016, AC-122, AC-123 (no wall-clock term; identical
  classification on every machine)
- EC-015, ADR-0025 / DEC-030 (Guess is a tier keyed on `branch_nodes`, not a
  rung of this scale)
- ADR-0013 / DEC-013 (superseded: formula, signals, normalisers; its
  no-re-entry rule carried forward)
- ADR-0005 / DEC-005 (revised: cutoffs now sit over rungs; recalibration
  owed after AC-118)
- ADR-0015 (consequence amended: same seed + same request classifies
  identically on any machine, with or without `--difficulty`)
- ADR-0007 (lateral-import rule: the overlap masks are re-derived natively in
  the solver), ADR-0009 (solver implementation the rungs are defined over)
- FR-009, AC-022, AC-023 (to be re-worded); CON-004 (difficulty remains a
  classifier of produced candidates)
- CARD-072 (solver telemetry, storage, export and admin display of the list)
- `src/nonogram/difficulty.py`, `src/nonogram/solver/search.py`
  (`SolveSignals`), `src/nonogram/solver/propagate.py` (`propagate`,
  `line_intersection`, `mask_runs`) — as they stand before this decision
- `docs/GENERATION_ALGORITHM.md` §6, §7, §10.2

## History

- 2026-09-12: Created — resolves DEC-031 by grading line-solvable puzzles on
  the rung of the hardest technique their one verifying solve required
  (`simple_overlap` < `line_dp` < `cross_line` < `probe_contradiction`, with
  the share of cells settled at that rung as the within-rung order), keeping
  0..100 as a derived presentation over four equal bands; chosen over a
  depth-weighted sum because the rung list is FR-029's strategies list and
  one derivation feeds both. Replaces ADR-0013; wall-clock time leaves the
  score for good (NFR-007/CON-014). Migration: rewrite — stored scores and
  tiers are re-graded by re-solving.

## Rules

```yaml
- id: ADR-0029/R1
  statement: The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < cross_line < probe_contradiction) and the share of cells settled at that rung; a deeper solve of the same extent scores strictly higher, and the line-solvable corpus populates every score band.
  scope: {contexts: [CTX-001], code: ["src/nonogram/difficulty.py", "src/nonogram/solver/**"]}
  check: {kind: test, ref: TestScoreDifficulty_DeeperLineReasoningScoresHigher}   # AC-119; AC-118's TestScoreDifficulty_LineSolvableCorpusSpansAllThreeBands covers the band-coverage half
  severity: mandatory
- id: ADR-0029/R2
  statement: Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from that same list — no second derivation, no second solver entry.
  scope: {contexts: [CTX-001], code: ["src/nonogram/solver/**", "src/nonogram/difficulty.py", "src/nonogram/orchestrator.py"]}
  check: {kind: test, ref: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve}   # AC-135
  severity: mandatory
- id: ADR-0029/R3
  statement: No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and branch_nodes, identical on every machine.
  scope: {contexts: [CTX-001], code: ["src/nonogram/difficulty.py", "src/nonogram/solver/**", "src/nonogram/orchestrator.py"]}
  check: {kind: test, ref: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime}   # EC-016; EC-018's PropertyTest_SolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd covers the list
  severity: mandatory
- id: ADR-0029/R4
  statement: The overlap masks used to distinguish simple_overlap from line_dp are re-derived natively inside the solver package; the solver never imports clues.py or any other capability module for the purpose (ADR-0007).
  scope: {contexts: [CTX-001], code: ["src/nonogram/solver/**"]}
  check: {kind: test, ref: test_every_import_in_the_package_points_inward}   # tests/test_cli.py structural guard (ADR-0007)
  severity: mandatory
```
