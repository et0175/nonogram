# ADR-0029: Difficulty is the rung of the hardest solving strategy required

**Status:** Accepted (replaces ADR-0013)
**Date:** 2026-09-12
**Deciders:** Puzzle Creator (project owner)
**Revised:** 2026-09-12 (rung definitions made order-independent)
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
(provisionally `simple_overlap`, `line_dp`, `cross_line` —
the last dropped by the 2026-09-12 revision below —
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

    simple_overlap  <  line_dp  <  probe_contradiction

`guess` is *not* a rung on this scale: a solve with `branch_nodes >= 1` is
`Tier.GUESS` under ADR-0025 and is not graded here. Within a rung, puzzles are
ordered by a secondary count fixed by this ADR: **the number of cells whose
settling deduction was at that rung, divided by the puzzle's total cells**.

This satisfies FR-026/AC-118/AC-119 because line-solvable puzzles are now
spread over three qualitatively different levels of line reasoning instead of
being pinned under 15 points; it satisfies NFR-007/CON-014/EC-016 because a
technique classification has no clock in it by construction; and it satisfies
FR-029 because the same classification *is* the strategies list. That last
point is the decisive advantage over the alternative: one derivation, taken
once from the one verifying solve, feeds both the tier and CARD-072's
`strategies_used` — the ordered list of rungs present is the FR-029 list, and
the highest rung present is the difficulty. There is no second scale to keep
consistent with the list, no weight table that can drift from it, and the
grade explains itself to a book editor in the list's own words ("needs the
full placement intersection, not just overlap").

Concretely:

- **Classification lives in the solver (COMP-005) as part of the one solve,
  and the ladder is applied as a sequence of fixed points.** The solve runs
  the cheapest technique to a fixed point first, then the next, each
  continuing from the board the previous one left — never resetting, never
  re-entering the solver (ADR-0029/R2). A cell's rung is the level at whose
  fixed point it was first settled:
  - `simple_overlap` — the cell is settled by propagating the
    leftmost/rightmost overlap rule alone to a fixed point over all rows and
    columns. The rule is applied **relative to what is already known on the
    line**: the leftmost and the rightmost placement *consistent with the
    line's known cells* are intersected. Re-derived natively inside
    `solver/` — no import of `clues.py` (ADR-0007, `tests/test_cli.py`),
    following the precedent of `propagate.py`'s `mask_runs`.
  - `line_dp` — from that fixed point, the full placement intersection
    (every placement, not only the two extremes) is propagated to a fixed
    point. Cells newly settled here are the ones overlap alone could never
    reach, at any point in the solve.
  - `probe_contradiction` — from that fixed point, a tentative assignment
    whose propagation contradicts forces the opposite value; propagated to a
    fixed point. A cell newly settled here needed one-step lookahead. (A
    real branch is not a rung: `branch_nodes >= 1` makes the puzzle
    `Tier.GUESS` under ADR-0025 and it is not graded on this ladder.)

  **Why each rung is a fixed point, and why that is the whole point of this
  revision.** Monotone propagation is confluent: the fixed point a technique
  reaches depends on the technique and the clue set, never on the order the
  lines were visited. So "the set of cells settled by level L" is a function
  of the clue set alone — which is what makes a rung a fact about the puzzle,
  as this ADR claims throughout, rather than a fact about how the solver
  happened to walk the grid.

- **`cross_line` is removed from the ladder.** It was never a technique. As
  originally written it meant "settled in a propagation sweep after the
  first", which is a statement about iteration, not about inference — and
  because `propagate` sweeps all rows before all columns, it made the rungs
  depend on grid orientation. Measured on the first implementation
  (CARD-073): a line examined from a blank board is settled identically by
  the overlap rule and by the full DP in 4000 of 4000 random cases, so every
  `line_dp` tag was in fact a sweep-0 *column* tag; and 205 of 224
  line-solvable grids (92%) graded differently from their own transpose, a
  7x7 sample moving from `{simple_overlap 30, line_dp 6, cross_line 13}` to
  `{simple_overlap 30, line_dp 15, cross_line 4}`. A puzzle and its transpose
  are the same puzzle to a solver. Feeding information between rows and
  columns until nothing more can be deduced is what propagation *is* at every
  level of the ladder, so it is part of each rung rather than a rung of its
  own.

- **Rung attribution is scoped to uniquely-solvable clue sets.** Rung tags,
  the per-rung cell counts and the ordered rung list are reported **only for a
  clue set with exactly one solution**. A clue set with 0 or >= 2 solutions is
  not a puzzle: it has no grade, no tier and no strategies list, and it gets no
  attribution at all — empty or `None` per-cell tags, an all-zero histogram,
  an empty rung list. This is a scoping rule, not a weakening of the ladder:
  everything the ladder claims, it claims about puzzles, and "which technique
  this puzzle needs" is a question that has no answer for a clue set that is
  not one. The generator already treats the two cases as different kinds of
  thing — a non-unique candidate is discarded, never graded, exported or
  stored (INV-002, CON-004) — so no consumer loses a number it was reading.

  The practical consequence is that a solve which has already established that
  a clue set is ambiguous has nothing left to attribute, and may therefore skip
  the ladder's dearest rung entirely. That is a permitted optimisation
  *because* of this rule and only because of it: the rungs of a puzzle are
  still the fixed points of the three techniques, computed in full, on every
  clue set that has a grade.

- **The 0..100 score is retained as a derived presentation, not as the
  grade.** `score = rung_base + within_rung_share * rung_width`, with the
  three rungs mapped onto equal bands: `simple_overlap` 0..33.33, `line_dp`
  33.33..66.67, `probe_contradiction` 66.67..100. The
  within-rung share is the secondary count above (cells settled at the top
  rung / total cells), so two puzzles topping out at the same rung differ by
  how much of the grid needed that technique. The export, the DB column and
  POL-004 keep a numeric score in the same range; the *meaning* of the number
  is now "which rung, and how much of it", and the tier is derived from the
  rung, not the other way round.
- **ADR-0005's cutoffs now land exactly on rung boundaries.** With three
  rungs over 0..100 the existing 33/66 cutoffs are the rung boundaries to
  within rounding, so the tier-per-rung mapping ADR-0005 was owed falls out
  of this revision rather than waiting on calibration: Easy = the puzzle
  never left overlap, Medium = it needed the full placement intersection,
  Hard = it needed a refuted probe, and Guess = it needed a real branch
  (ADR-0025). The cutoff *constants* are unchanged, so no stored grade moves
  on account of this bullet alone. What remains owed to the >= 200-puzzle
  corpus (AC-118) is only the **within-rung** ordering — whether the share of
  cells settled at the top rung spreads puzzles usefully inside a band, or
  wants a different secondary count.

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
- The ladder is coarse: three rungs decide the band, and everything that
  distinguishes two puzzles inside one band is the share of cells settled at
  the top rung. Whether that share spreads puzzles usefully is the open
  calibration question, and the >= 200-puzzle corpus (AC-118) is what
  answers it.
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
  provisional enum members are fixed by this ADR as **`simple_overlap`,
  `line_dp`, `probe_contradiction`, `guess`** — `cross_line` is NOT a member
  (see the 2026-09-12 revision) — and its `enum_provisional` note can be
  closed against that list. Any card or requirement text still naming four
  rungs predates the revision and is stale.
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

- 2026-09-12 (scoping, same day): **rung attribution applies to
  uniquely-solvable clue sets only.** Added to the Decision and to R5: rung
  tags, per-rung counts and the rung list are reported only for a clue set with
  exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle,
  has no grade, and carries no attribution. R5's transposition invariance is
  scoped to uniquely-solvable clue sets accordingly — and holds trivially for
  the rest, because both orientations of a non-puzzle report nothing.

  **What this is for.** The revision above made probe refutation (level 3) a
  *phase* of the solve: every still-unknown cell tried with both values, to a
  fixed point, with no cap and no ordering heuristic, because any of those
  would make a rung a fact about the solver. On a puzzle that is cheap and
  decisive. On the generator's discard path it was neither: a 20x20 candidate
  at 20% density leaves ~300 cells open at line logic's fixed point, so level 3
  paid ~600 propagations to force almost nothing — a massively ambiguous board
  is exactly the board single-cell lookahead cannot refute anything on — and
  CARD-073's cycle-2 measurement put the discard path at 2.4x its previous
  cost (0.508s -> 1.204s per 20x20 density-20 request). Every mitigation
  available *inside* the ladder (a probe budget, a width cap, a "skip when the
  undecided mask is large" predicate) buys that back by making which cell gets
  which rung depend on the solver's bookkeeping, which is the defect the
  revision exists to remove. This scoping buys it back from outside the ladder
  instead: the candidates that cost the most are precisely the ones whose
  attribution is never read, because they are discarded rather than graded.
  A solve may therefore establish ambiguity first — with a bounded round of
  the ordinary search, whose findings are kept only if they *prove* two
  solutions and are otherwise discarded whole — and skip level 3 for the clue
  sets that turn out not to be puzzles. Every uniquely-solvable clue set still
  runs all three fixed points in full, so its attribution is as complete and as
  order-independent as before. Measured after the change (CARD-073 cycle 3):
  600/600 grids transpose-identical, 275 of them uniquely solvable; 20x20
  generation at density 20 down from 1.196s to 0.553s per request, and at
  density 25 from 1.660s to 1.074s.

  **Why the Guess tier is not affected.** One-step lookahead solves every
  uniquely-solvable grid the current sources produce: 0 of 6,620 random and
  structured grids from 8x8 to 20x20 needed a real branch after level 3
  (CARD-073, 2026-09-12). So skipping level 3 can never cost a puzzle its
  grade — a clue set level 3 would have finished is uniquely solvable, and a
  uniquely-solvable clue set never takes the skip. See ADR-0025's History entry
  of the same date for what that measurement means for `Tier.GUESS`.

  No verdict changes: two verified distinct solutions are the same `MANY` the
  full sequence would have reached, from a board every solution extends
  (CON-005 untouched). No stored data moves; Migration stays `rewrite` from the
  revision below.

- 2026-09-12 (revision, same day): **rung definitions made order-independent.**
  The ladder as first written graded a puzzle differently from its own
  transpose, because `cross_line` meant "settled in a sweep after the first"
  and `propagate` sweeps all rows before all columns — so rows were always
  deduced from a blank line and columns from a partly-known one. CARD-073's
  implementation made it measurable: `line_dp` was unreachable for a line
  examined from a blank board (4000/4000 agreement between the overlap rule
  and the full DP), so every `line_dp` tag was really a sweep-0 column tag,
  and 92% of line-solvable grids graded differently from their transpose.
  Fixed at the root: `cross_line` is removed from the ladder (it was
  iteration, not inference), each remaining rung is applied as a **fixed
  point** rather than as a sweep, and the overlap rule is applied relative to
  the line's known cells. Monotone propagation is confluent, so a level's
  fixed point — and therefore every rung — is now a function of the clue set
  alone. Consequences: three rungs rather than four, bands of 33.33 rather
  than 25, ADR-0005's 33/66 cutoffs now falling on rung boundaries (the
  tier-per-rung mapping it was owed), and R1/R2/R4 amended plus R5 added.
  No verdict changes: the final fixed point under the full technique set is
  the same set of cells whichever order the techniques were applied in, so
  CON-005 and the uniqueness counts are untouched. Migration stays `rewrite`.

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
  statement: The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction) and the share of cells settled at that rung; each rung is the fixed point of its technique, so the rung of a cell is a function of the clue set alone; a deeper solve of the same extent scores strictly higher, and the line-solvable corpus populates every score band.
  scope: {contexts: [CTX-001], code: ["src/nonogram/difficulty.py", "src/nonogram/solver/**"]}
  check: {kind: test, ref: TestScoreDifficulty_DeeperLineReasoningScoresHigher}   # AC-119; AC-118's TestScoreDifficulty_LineSolvableCorpusSpansAllThreeBands covers the band-coverage half
  severity: mandatory
- id: ADR-0029/R2
  statement: Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzzle's strategies list, and the tier is derived from that same list — no second derivation, no second solver entry. The ladder's fixed points are phases of that one monotone forward solve — each continues from the board the previous left, the board is never reset and the search is never re-entered — so running a cheaper technique to exhaustion before a dearer one is not re-solving.
  scope: {contexts: [CTX-001], code: ["src/nonogram/solver/**", "src/nonogram/difficulty.py", "src/nonogram/orchestrator.py"]}
  check: {kind: test, ref: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve}   # AC-135
  severity: mandatory
- id: ADR-0029/R3
  statement: No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pure function of the rung tags of the solve and branch_nodes, identical on every machine.
  scope: {contexts: [CTX-001], code: ["src/nonogram/difficulty.py", "src/nonogram/solver/**", "src/nonogram/orchestrator.py"]}
  check: {kind: test, ref: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime}   # EC-016; EC-018's PropertyTest_SolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd covers the list
  severity: mandatory
- id: ADR-0029/R4
  statement: The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with them, intersected), and are re-derived natively inside the solver package; the solver never imports clues.py or any other capability module for the purpose (ADR-0007).
  scope: {contexts: [CTX-001], code: ["src/nonogram/solver/**"]}
  check: {kind: test, ref: test_every_import_in_the_package_points_inward}   # tests/test_cli.py structural guard (ADR-0007)
  severity: mandatory
- id: ADR-0029/R5
  statement: Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attribution at all (empty or None per-cell tags, an all-zero per-rung histogram, an empty rung list). For uniquely-solvable clue sets, rung attribution is invariant under transposition and under line-visit order — a clue set and its transpose yield the same per-rung cell counts, the same rung list and the same score — and a change to the solver's iteration order may change how a fixed point is reached but never which cells belong to which rung. The invariance holds trivially for the non-unique ones too, since both orientations report nothing.
  scope: {contexts: [CTX-001], code: ["src/nonogram/solver/**", "src/nonogram/difficulty.py"]}
  check: {kind: test, ref: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition}
  severity: mandatory
```
