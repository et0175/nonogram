# ADR-0013: Difficulty scoring formula

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-009 requires the five difficulty signals the solver produces — cells solved
by line-only logic before the first branch, backtracking amount, solver wall-clock
time, puzzle size, and clue density — to be combined into "a single numeric
score," and AC-022 tests exactly that combination. Nothing in the inputs
specifies the combining FORMULA itself: no weighting scheme, no normalization,
and no statement of whether solver wall-clock time belongs in the score at all
or is only telemetry.

DEC-005 asks a related but strictly later question — where the Easy/Medium/Hard
tier cutoffs sit on the difficulty scale — but DEC-005 cannot be answered until
the scale itself exists. This ADR is what establishes that scale: it fixes the
score's 0..100 range and the shape of the function that produces it, which is
the surface DEC-005/ADR-0005 will place its tier cutoffs on. Getting this
formula wrong or leaving it ambiguous would make any tier-cutoff decision
arbitrary, since the cutoffs would be drawn on a scale with no fixed meaning.

The five signals are heterogeneous by construction. Line-logic coverage and
backtracking amount are counts naturally scaled by puzzle size (a 50x50 grid
has vastly more cells and possible branch nodes than a 10x10 grid); density
is a percentage with a known non-monotonic relationship to difficulty (both
very sparse and very dense grids tend to be easier than mid-density ones);
and solver wall-clock time is machine- and load-dependent in a way the other
four signals are not. Combining them naively (e.g. a raw sum) would let size
alone dominate the score, making every large puzzle "Hard" regardless of how
little backtracking it actually needed — which is precisely the failure this
decision has to avoid, and which AC-023 (a puzzle solved entirely by line
logic, with zero backtracking, must land at the easy extreme regardless of
size) tests directly.

## Decision

We adopt the **normalized_weighted_sum** alternative: each of the five FR-009
signals is normalized to the 0..1 range against a size-relative denominator
before being combined, and the normalized signals are then combined with a
fixed-weight sum into a single 0..100 score.

Concretely:
- Line-logic coverage is normalized as (solved-before-first-branch cells /
  total cells), inverted, so that full line-logic coverage contributes toward
  the easy end of the scale.
- Backtracking amount is normalized as (branch nodes / total cells), capped at
  1.0, so a puzzle's branch count is judged relative to its own size rather
  than against an absolute count that would favor large grids toward "Hard."
- Density enters as distance from the hardest midpoint — |density - 0.5| —
  since both very sparse and very dense grids tend to be easier, and this
  normalizer captures that non-monotonic relationship directly rather than
  treating density as a linearly increasing difficulty term.
- Size and density act as NORMALIZERS on the other signals rather than as
  independent additive terms in their own right, which is what keeps scores
  comparable across the 10x10..50x50 range instead of letting a raw sum make
  every large puzzle "Hard" by size alone.
- The five normalized values are combined via a fixed-weight sum into a
  0..100 score. The weights live in one named, tunable constant table,
  separate from the solver, exactly as docs/requirements.md FR-10's "tunable
  later" language requires.

This satisfies AC-022 (a score reflecting the weighted combination of all
five named signals) and AC-023 by construction: a puzzle solved entirely by
line logic with zero backtracking normalizes to the easy extreme regardless
of its size, because size only ever appears as a denominator. It also gives
DEC-005 the fixed, meaningful 0..100 scale its tertile_split (or any other)
tier-cutoff scheme needs before cutoffs can be chosen.

## Alternatives considered

### backtracking_dominant_with_tiebreak

Score driven almost entirely by branch count — the signal closest to the
human intuition of what makes a nonogram hard — with line-logic coverage used
only as a tiebreaker; size and density would be recorded as telemetry but
excluded from the score itself. This was rejected because AC-022 explicitly
requires the score to reflect the weighted combination of ALL FIVE signals,
and this alternative drops two of them outright, which would require amending
the acceptance criterion rather than satisfying it. It also collapses badly
for the common case of puzzles the solver finishes with zero branches — most
Easy puzzles — which would all score identically under a branch-count-dominant
scheme, losing exactly the differentiation FR-009 exists to provide.

### exclude_wall_clock_time

Otherwise identical to normalized_weighted_sum, but drops solver wall-clock
time from the score entirely, keeping it only as reported telemetry, on the
grounds that timing is machine- and load-dependent and would make the same
puzzle score differently across runs or hardware. This was rejected because
it departs from FR-009's literal five-signal list, which would require
amending FR-009/AC-022 rather than implementing them as written, and because
it discards a signal that does genuinely correlate with search effort. The
chosen alternative keeps wall-clock time in the score as FR-009 specifies;
reproducibility concerns about timing variance are a separate, narrower
problem than the combining formula this ADR settles.

## Consequences

### Positive

- Establishes the fixed 0..100 difficulty scale that DEC-005/ADR-0005 needs
  before it can place tier cutoffs — that decision is now unblocked.
- Satisfies AC-023 by construction: zero backtracking with full line-logic
  coverage normalizes to the easy extreme independent of puzzle size, because
  size enters only as a denominator, never as an additive term.
- Keeps scores comparable across the full 10x10..50x50 size range, preventing
  the raw-sum failure mode where large puzzles are scored "Hard" by size
  alone rather than by actual solving difficulty.
- Puts all five FR-009 signals in the score as AC-022 requires, satisfying the
  acceptance criterion as written rather than needing it amended.
- The weight table is one named, tunable constant set, separate from the
  solver — exactly the tuning surface FR-10's "tunable later" requirement and
  DEC-005's tertile_split option both need.

### Negative

- The weights are guesses until real score distributions are observed across
  a range of generated puzzles; they will likely need recalibration once
  empirical data exists.
- The normalization denominators (total cells, the 0.5 density midpoint, the
  backtracking cap) are themselves judgement calls, not derived from any
  external reference — a different but equally defensible set of denominators
  could produce a materially different scale.
- Solver wall-clock time remains in the score, so the same puzzle can score
  slightly differently across machines or under load, which downstream
  consumers (the resample loop, POL-004, and any AC test asserting an exact
  score) need to tolerate rather than assume away.

### Neutral

- This ADR fixes the SCALE and the COMBINING FORMULA only; DEC-005 (where the
  Easy/Medium/Hard cutoffs sit on this 0..100 scale) remains a separate,
  now-unblocked decision.
- The weight constant table is a natural target for recalibration once real
  puzzles have been scored, in the same way other unvalidated numeric
  constants in this model (e.g. ADR-0001's timing thresholds) are expected to
  be revisited.
- Because wall-clock time is included, any future decision to make scores
  strictly reproducible across machines (the rejected exclude_wall_clock_time
  alternative) would be a revision of this ADR, not an unrelated change.

## References

- DEC-013 (resolved by this ADR)
- FR-009, FR-010, CON-004 (criteria this decision satisfies)
- AC-022, AC-023 (acceptance criteria this decision makes testable)
- DEC-005 / ADR-0005 (tier cutoffs placed on the scale this ADR establishes)
- DEC-009 (solver implementation that produces the five raw signals)

## History

- 2026-08-27: Created — adopted a normalized weighted sum with size-relative
  denominators over a backtracking-dominant score and over excluding solver
  wall-clock time, establishing the 0..100 difficulty scale FR-009 requires.
