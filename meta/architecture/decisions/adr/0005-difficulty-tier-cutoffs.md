# ADR-0005: Difficulty tier cutoffs

**Status:** Accepted (revised by ADR-0029, 2026-09-12; cutoff *values* unchanged)
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** 2026-09-13 (History: the bands now sit over ADR-0029's rungs; recalibration owed)
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-009 requires combining five solver signals into a single numeric difficulty
score, and FR-010 requires regenerating or resampling a candidate puzzle
until its estimated difficulty score falls within the requested tier's
threshold range (Easy/Medium/Hard), bounded by a maximum retry count
(AC-024, AC-025). Neither FR-009 nor FR-010 states where those per-tier
threshold ranges actually sit; the intake requirements document explicitly deferred the
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

- 2026-09-13 (revision note, CARD-076): **the bands now sit over rungs, and the
  cutoff constants did not move.**

  ADR-0029 replaced ADR-0013's scale, which is the scale this decision divided.
  It did not, however, re-draw the cutoffs: it mapped its three rungs onto
  *them*. `simple_overlap` occupies 0..33, `line_dp` 33..66 and
  `probe_contradiction` 66..100, so `EASY_MAX_SCORE = 33.0` and
  `MEDIUM_MAX_SCORE = 66.0` are unchanged in value and no stored grade moved on
  account of a band edge (CARD-076 guardrail G-5). What changed is what a band
  *means*: Easy is now "the puzzle never left the overlap rule", Medium "it
  needed the full placement intersection", Hard "it needed a refuted probe" —
  and ADR-0025 adds a fourth tier, `guess`, which is **not** a band at all and
  is keyed on the solve's `branch_nodes` (EC-015). This decision's own model,
  "a tier is a bucket a scored candidate fell into", therefore holds for three
  of the four members and is broken for the fourth by design.

  It is also worth recording that this arithmetic is load-bearing in a way the
  original decision could not have anticipated. ADR-0029's first draft mapped
  the rungs onto idealised thirds (33.33 / 66.67), which places a band edge a
  third of a point *above* the cutoff it is supposed to be — and since a puzzle
  topping out at `simple_overlap` has a within-rung share of exactly 1.0 by
  definition, every Easy puzzle would have scored 33.33 and classified Medium.
  The Easy band would have been empty. Corrected in ADR-0029's History entry of
  2026-09-13 by taking "the cutoffs are the rung boundaries" literally, which
  works precisely because this decision wrote its bands with *inclusive* upper
  bounds.

  **The recalibration this decision was owed is now half discharged and half
  still open.** The tier-per-rung mapping falls out of ADR-0029 and needs no
  data. What remains owed is the *within-rung* ordering — whether the share of
  cells settled at the top rung spreads puzzles usefully inside a band. The
  measurement AC-118 asked for exists (CARD-076's Worktree notes; 292
  uniquely-solvable random puzzles, 10x10..30x30):

  | tier | rung | n | share | score range |
  |---|---|---:|---:|---|
  | Easy | `simple_overlap` | 258 | 88.4% | 33.000 only |
  | Medium | `line_dp` | 8 | 2.7% | 36.667..59.400 |
  | Hard | `probe_contradiction` | 26 | 8.9% | 68.116..98.640 |
  | Guess | — | 0 | 0% | — |

  Two things in it bear on the open half. **Easy is a single point on the
  scale** — every puzzle that never leaves overlap settles *all* its cells
  there, so the secondary count is 1.0 for all 258 of them and the within-rung
  ordering this decision is waiting on does not exist inside the bottom band,
  which is where 88% of the corpus is. And the distribution is lopsided in the
  way this ADR's own Negative section predicted a skew might make it ("equal
  tertile bands could leave one tier under-populated, causing the resample loop
  to retry more often than intended"): requesting Medium at a random extent and
  density really does resample, and `--difficulty guess` cannot be filled at
  all on today's sources. CARD-076 recorded this and deliberately retuned
  nothing.

- 2026-08-27: Created — resolves DEC-005 by dividing the ADR-0013 0..100
  score scale into three equal tertile bands for Easy/Medium/Hard.
