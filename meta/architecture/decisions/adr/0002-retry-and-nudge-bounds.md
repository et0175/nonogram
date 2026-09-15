# ADR-0002: Retry and nudge bounds

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** R1 (2026-09-14, CARD-090) — the retry bound is 30, measured
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

NFR-002 requires a maximum bound on the regenerate/resample loop that produces a
candidate puzzle: a random or library-sourced grid is generated, checked for a
unique solution (FR-006, FR-007) and, when a difficulty tier was requested,
resampled against the difficulty score (FR-009, FR-010) until it lands in range.
FR-013 separately requires a cap on pixel-nudge attempts, the recovery mechanism
used in image mode when a user-supplied picture does not by itself yield a
uniquely solvable grid: individual cells are nudged and the uniqueness/difficulty
checks are re-run.

Neither the retry-loop bound nor the nudge-attempt cap has a numeric value in the
inputs. Without an upper bound, a genuinely infeasible request (a density/size/
difficulty combination with no satisfying grid, or an image with no nearby valid
nudge) has no way to fail — the tool would loop indefinitely or until the process
is killed, which conflicts with the CLI's need to terminate predictably. The bound
also interacts with NFR-001's overall time budget: each retry or nudge attempt
re-invokes the solver, so a larger bound trades a lower chance of spurious
abandonment for a slower worst-case failure path. The two numbers (retry count,
nudge count) must be picked together since both draw on the same solver-invocation
budget within a single generation run.

## Decision

> **R1 (2026-09-14, CARD-090): the retry bound is now 30, not 20.** The nudge
> cap of 5 is unchanged. Everything this section says about *why* both loops
> need a bound at all still holds — only the retry number moved, and it moved
> because it was finally measured. See the History entry and the revised
> alternatives section below; the original text is kept as written so the
> reasoning that was superseded stays legible.

We will adopt alternative **20_retries_5_nudges**: the regenerate/resample loop
(random/library generation plus difficulty resampling) is capped at 20 attempts,
and the pixel-nudge recovery loop (image mode) is capped at 5 attempts. This
satisfies NFR-002 and FR-013 by giving both loops a concrete, enforceable upper
bound: exceeding either cap terminates the run with a clear abandonment failure
rather than continuing indefinitely. Twenty retries is generous enough that a
reasonable request (a density/size/difficulty combination that has a genuinely
satisfying grid) will rarely hit the ceiling, while still failing fast — within a
bounded, small number of solver invocations — on a request that is truly
infeasible. Five nudge attempts keeps the image-mode recovery path, which
existed specifically to make a small, bounded correction to a user's picture,
from drifting the exported puzzle far from what the user actually uploaded.

## Alternatives considered

### 50_retries_10_nudges

> **Superseded by measurement (R1, CARD-090).** Both of the two claims this
> rejection rests on are false, and CARD-089 measured them at 30x30, density 50,
> over 100 seeded requests through the real generation path:
>
> | bound | abandoned | success | total wall clock |
> |---|---|---|---|
> | 20 | 14 | 85% | 583 s |
> | **30** | **4** | **95%** | **340 s** |
> | 40 | 3 | 96% | 482 s |
> | 60 | 1 | 98% | 375 s |
>
> *"It directly worsens the worst-case failure latency"* — it does not. A single
> request's worst case is set by the NFR-001 deadline mechanism decided later
> (`GENERATION_BUDGET_SECONDS`, one deadline per request shared by every attempt
> in it), not by the attempt count; the longest request was 30.0 s at **every**
> bound tried. Nor does a larger bound cost throughput: total wall clock *fell*
> as the bound rose, because an abandonment is the expensive outcome — it spends
> the entire budget and returns nothing, while a success usually lands early.
> This ADR reasoned as though attempts were the scarce resource. They are not;
> abandonments are.
>
> *"A combination that cannot be satisfied in 20 attempts is not meaningfully
> more likely to be satisfied in 50"* — ten of the fourteen grids abandoned at
> bound 20 are produced at bound 30, from the *same seeds*. They were not
> infeasible combinations. They were false negatives, and the user saw
> "infeasible" for a request that was not.
>
> What survives is this section's *instinct* that doubling is more than the
> problem needs: 30 captures ten of the eleven conversions that 40 delivers, and
> the curve is visibly flat past it. The bound moved to 30, not to 50.
>
> The lesson this ADR records for its successors is the one its own Negative
> consequences predicted in writing: a number chosen without measurement, and
> then defended with an argument about a cost that was never measured either,
> will be wrong in a direction nobody can guess from the armchair. It was wrong
> in the direction that made the tool *both* less reliable and slower.

Doubling both bounds (50 regenerate/resample attempts, 10 pixel-nudge attempts)
was considered. It would lower the chance of spurious abandonment for
hard-to-satisfy density/difficulty combinations near the edges of the supported
range. It was rejected because it directly worsens the worst-case failure
latency this decision is meant to bound: each additional attempt is a full
solver invocation, and NFR-001's overall time budget has to absorb the
infeasible-request path as well as the happy path. A larger bound also does
not change what is achievable — a combination that cannot be satisfied in 20
attempts is not meaningfully more likely to be satisfied in 50 — so the extra
attempts mostly extend the time to a failure that was already going to happen.

## Consequences

### Positive

- Both stochastic loops (regenerate/resample and pixel-nudge) now have a
  concrete, enforceable termination condition, closing the indefinite-loop gap
  NFR-002 and FR-013 identify.
- The bound is small enough that an infeasible request fails within a bounded
  and predictable number of solver invocations, keeping worst-case latency
  compatible with NFR-001's overall time budget.
- A fixed, low nudge cap (5) keeps the image-mode recovery path faithful to its
  purpose — a small correction to a user's picture, not a wholesale
  regeneration of it.
- The two numbers are named constants in one place, so they can be re-tuned
  later without touching the solver or the orchestration logic that calls it.

### Negative

- Both numbers are chosen without empirical tuning against real solver
  performance or real density/difficulty distributions; they may prove too
  tight or too loose once observed, and will likely need revisiting once usage
  data exists.
- A legitimate but statistically unlucky request could still be abandoned
  within 20 attempts even though a satisfying grid exists, producing a
  false-negative "infeasible" result from the user's point of view.

### Neutral

- Introduces GenerationAbandoned as the uniform failure outcome for both the
  regenerate/resample loop and the pixel-nudge loop once their respective caps
  are exceeded, rather than distinct failure modes per loop.
- These two constants become a natural target for the mechanism decided in a
  later ADR that enforces the NFR-001 wall-clock deadline (DEC-011) — that
  mechanism bounds total time per run, while this decision bounds the number
  of attempts within it; the two operate together but independently.
- Future recalibration of either bound is a self-contained change (a constant
  update), not an architectural one.

## References

- DEC-002 (resolved by this ADR)
- NFR-002, FR-007, FR-010, FR-013 (criteria this decision satisfies)

## History

- 2026-08-27: Created — adopted 20 regenerate/resample retries and 5
  pixel-nudge attempts as the default bounds for NFR-002 and FR-013.
- 2026-09-13: History (ADR-0024, CARD-074) — random-mode recovery now REPAIRS
  a non-unique candidate before it redraws it, and repairs and redraws share
  this ADR's one 20-attempt bound: both kinds of attempt advance the same
  `RetryCounter`, and `GenerationAbandoned` is raised whichever kind came last.
  ADR-0024's `MAX_CONSECUTIVE_REPAIRS` (K, initially 3) is an *interleaving
  split* of that budget — how long one repair lineage may run before the loop
  goes back to drawing independent samples — and is never a second bound. The
  20 and the 5 stand, unchanged and unrecalibrated; the one visible
  consequence is that "20 attempts" in an abandonment message now mixes
  redraws and repairs, which ADR-0024 accepts explicitly.
- 2026-09-14: **Revised — R1 (CARD-090).** The regenerate/resample bound moves
  from 20 to 30. CARD-089 built the seeded sweep this ADR's Negative
  consequences asked for (`meta/ops/retry_bound_sweep.py`) and measured 20, 40
  and 60; the owner left the number at 20 on that evidence, then took the middle
  value once the shape of the curve was clear, and CARD-090 measured 30 rather
  than interpolating it. Result: 85% -> 95% at 30x30, with total wall clock
  falling. The `50_retries_10_nudges` rejection reasoning is marked superseded
  above on both of its claims. `MAX_NUDGE_ATTEMPTS` (5) is untouched and remains
  a separate judgement about a different question — how much of a user's own
  picture may be altered — and `MAX_CONSECUTIVE_REPAIRS` (ADR-0024's K, still 3)
  is untouched too, though the same measurement suggests it, not this bound, is
  now the larger lever; recalibrating it is still scheduled and still undone.
