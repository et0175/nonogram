# ADR-0005: Difficulty tier cutoffs

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-009 requires combining five solver signals into a single numeric difficulty
score, and FR-010 requires regenerating or resampling a candidate puzzle
until its estimated difficulty score falls within the requested tier's
threshold range (Easy/Medium/Hard), bounded by a maximum retry count
(AC-024, AC-025). Neither FR-009 nor FR-010 states where those per-tier
threshold ranges actually sit; docs/requirements.md explicitly defers the
numeric cutoffs as "tunable later."

ADR-0013 (DEC-013) settled the shape of the scale this decision places its
cutoffs on: the five FR-009 signals (line-logic coverage, backtracking
amount, solver time, puzzle size, clue density) are each normalized against
size-relative denominators and combined via a fixed-weight sum into a single
0..100 score, with the weights living in one named, tunable constant table
separate from the solver. DEC-005 is the decision ADR-0013 explicitly left
open: given that fixed 0..100 scale now exists, where inside it do the
Easy/Medium/Hard tier boundaries sit?

The resample loop (FR-010, POL-004) evaluates this boundary on every
candidate it scores, so the cutoffs must be a small number of fixed, named
constants a developer can read and reason about, not a threshold recomputed
per run — otherwise resample behavior would be nondeterministic across runs
on the same inputs. No empirical score distribution exists yet, since no
puzzle has ever been scored under the ADR-0013 formula, so any cutoff chosen
now is necessarily provisional.

## Decision

We adopt **tertile_split**: the 0..100 score range established by ADR-0013
is divided into three equal-width bands — Easy = [0, 33], Medium = (33, 66],
Hard = (66, 100] — with the two boundary constants (33 and 66) living in the
same named, tunable constant table convention ADR-0013 already established
for the signal weights.

This satisfies FR-009/FR-010 with the least new machinery: because ADR-0013
already fixed the scale to a known, bounded 0..100 range, dividing it into
three equal bands requires no calibration data before the first puzzle is
ever scored, and gives an immediately usable answer to "what are the
threshold ranges" the resample loop needs from day one. Keeping the cutoffs
as two named constants — rather than deriving them from the signal weights a
second time — means cutoffs and weights can be retuned together, from the
same real score distributions, once the tool has generated enough puzzles to
observe one, without touching any code beyond that constant table.

## Alternatives considered

### signal_weighted_fixed_cutoffs

Hand-pick fixed cutoffs directly from the weighting of line-logic coverage
against backtracking amount, rather than dividing the ADR-0013 0..100 range
evenly. This was rejected because it requires upfront calibration before any
puzzle has ever been scored — someone would have to decide, in the absence
of any observed data, exactly how much backtracking "feels like" a Hard
puzzle — and that judgment would likely need revisiting anyway once real
score distributions from ADR-0013's formula become available. It also
duplicates tuning effort that ADR-0013's weight table already owns: the
relative importance of each signal is baked into the score itself, so
re-deriving tier boundaries from raw signal weights a second time,
independently of the score, risks the two derivations drifting apart over
time.

## Consequences

### Positive

- Zero calibration data is required before the first release; the cutoffs
  are available and usable the moment ADR-0013's score exists.
- The rule is trivial to state, implement, and test: two constants and two
  comparisons, no additional module or dependency.
- Cutoffs and score weights live on the same "tunable later" axis (a small,
  named constant table), so future retuning driven by real puzzle-score data
  touches one place rather than two independently-evolving schemes.

### Negative

- The three bands carry no principled meaning until real score distributions
  are gathered — a boundary at exactly 33/66 has no justification beyond
  "divide by three," so early tier labels (e.g. "Hard") may not match a
  player's intuitive sense of difficulty.
- If the score distribution ADR-0013's formula actually produces turns out
  skewed (e.g. most puzzles cluster in the 20-40 range), equal tertile bands
  could leave one tier — most likely Hard — under-populated, causing the
  resample loop (FR-010) to retry more often than intended and hit AC-025's
  maximum-retry bound more frequently than a data-derived split would.

### Neutral

- The two cutoff constants need a single named table, per the tuning-surface
  convention ADR-0013 already established — no new state is introduced, but
  a follow-up "retune cutoffs from observed score data" task is implicitly
  created once the tool has scored enough real puzzles to make that
  worthwhile.
- Revisiting this decision later (e.g. moving to signal_weighted_fixed_cutoffs
  or an empirically-derived split) is a constant-table change plus a
  documented rationale; no consumer of the difficulty score needs to change.

## References

- DEC-005 (resolved by this ADR)
- DEC-013 / ADR-0013 (establishes the 0..100 normalized-weighted-sum scale
  this decision divides into tiers)
- FR-009, FR-010 (criteria this decision satisfies)
- AC-024, AC-025 (resample accept/reject behavior gated on tier threshold
  ranges)

## History

- 2026-08-27: Created — resolves DEC-005 by dividing the ADR-0013 0..100
  score scale into three equal tertile bands for Easy/Medium/Hard.
