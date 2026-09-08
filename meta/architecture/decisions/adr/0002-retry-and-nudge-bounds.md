# ADR-0002: Retry and nudge bounds

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
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
