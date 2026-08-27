# ADR-0015: Random seed source and reproducibility

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

Randomness is threaded through the puzzle-generation pipeline at several points: random grid generation and its density control (FR-001, FR-004), the automatic regenerate-on-uniqueness-failure loop (POL-001), the pixel-nudge recovery loop for uploaded images (POL-002), and the difficulty resample loop (POL-004). None of the domain model, the requirements, or the policies specify where this randomness is sourced from, whether a given run can be reproduced, or how test code is meant to exercise these stochastic paths deterministically.

FR-012 requires that a JSON/CSV export be "sufficient to exactly reconstruct the puzzle," which today covers only the grid and clues — it says nothing about the generation run that produced a random or library-sourced grid in the first place. Several acceptance criteria (e.g. AC-019, AC-027) exercise retry-bound behavior — requests that are constructed to remain infeasible across the full retry budget — which is difficult to assert reliably if the stochastic components draw from shared global state rather than an isolable source. CON-001 fixes the interface as a single-process CLI with no network or external service, so any solution must live entirely inside that one process's argument surface and file output.

The open question is threefold: should the CLI expose a seed to the user at all; if so, how do the four stochastic call sites (FR-001/FR-004 sourcing, POL-001, POL-002, POL-004) actually consume it; and should that seed be recorded in the export FR-012 produces.

## Decision

We will add an explicit `--seed` flag to the CLI, source all stochastic behavior in the pipeline from one injected `random.Random` instance, and record the seed together with the generation parameters in the JSON export. When `--seed` is not supplied, a seed is drawn from the OS entropy pool and printed to the user so the run remains reproducible after the fact. This satisfies FR-001/FR-004/FR-012 because it makes random and library-sourced generation reproducible end-to-end — from CLI invocation through to the exported artifact — and it satisfies NFR-002's testability needs because injecting one `Random` instance (rather than relying on the `random` module's global state) makes every stochastic path, including the regenerate (POL-001), pixel-nudge (POL-002), and difficulty-resample (POL-004) loops, deterministic and directly testable by construction, not by monkeypatching.

## Alternatives considered

### seed_flag_not_exported

Offer `--seed` for reproducibility and testing, but keep the export payload exactly as FR-012 originally specifies — grid and clues only, with no seed or parameters attached. This alternative delivers the same internal testability benefit (one injected `Random` instance) but was rejected because it leaves a gap in FR-012's own stated intent: an exported puzzle would be reproducible only for as long as the user separately remembers or records the seed and parameters used to produce it. Once the export file is the only artifact that survives, the puzzle it contains could never be regenerated or verified against its origin. Given that the export schema change needed to close this gap is small, there was no compensating benefit to leaving it open.

### implicit_global_random

Use the `random` module's implicit global state directly at each call site, with no seed control exposed anywhere. This was rejected outright: it provides no reproducibility for the user at all, and it makes the four stochastic call sites (FR-001/FR-004, POL-001, POL-002, POL-004) untestable except by monkeypatching global module state around each test — precisely the fragility that property-based and deterministic testing (EC-001, EC-002, NFR-002) are meant to eliminate. It offered no advantage over the chosen alternative beyond having nothing to build, which does not offset the cost to test reliability and to FR-012's reconstruction intent.

## Consequences

### Positive
- Every acceptance test that depends on randomness — including the retry-bound tests (AC-019, AC-027) that require a reproducibly infeasible request — becomes deterministic and non-flaky, since the test can construct the shared `Random` instance with a fixed seed instead of relying on or patching global state.
- A puzzle exported at any point in the past becomes reproducible from its own JSON file: the seed and generation parameters travel with the grid and clues, completing FR-012's "sufficient to exactly reconstruct the puzzle" intent for random and library-sourced puzzles, not just for the static grid content.
- Injecting one `random.Random` instance through the pipeline, rather than reaching for the module-level global, is a small, one-time cost (a single constructor argument threaded through the orchestrator and into POL-001/POL-002/POL-004) that pays for itself immediately in testability.

### Negative
- The CLI surface and the JSON export schema both grow slightly: a new `--seed` flag, and new `seed` plus generation-parameter fields in the export payload alongside the existing grid and clue data.
- EC-002's round-trip property test must be written carefully to treat the seed and parameters as metadata rather than as part of the grid/clue equality it asserts — otherwise two exports of the same puzzle with different seeds could be wrongly judged unequal, or the property could be weakened to ignore fields it should be checking.

### Neutral
- Every stochastic call site in the pipeline (FR-001/FR-004 sourcing, POL-001 regenerate, POL-002 pixel-nudge, POL-004 difficulty resample) must be threaded with the same injected `Random` instance rather than instantiating or importing randomness independently — this is an internal wiring convention future capability modules must follow, not a new external dependency.
- When no `--seed` is given, the tool must print the auto-drawn seed to the user at run time; this is a small but permanent piece of CLI output behavior that downstream UX or logging changes need to preserve.

## References

- DEC-015 (resolved by this ADR)
- CTX-001 (Puzzle Creation — the single bounded context all four stochastic call sites live inside)
- FR-001, FR-004, FR-012 (criteria this decision satisfies)
- POL-001, POL-002, POL-004 (policies whose stochastic behavior this decision governs)

## History

- 2026-08-27: Created — adopted an explicit `--seed` flag with a single injected `random.Random` instance and seed-plus-parameters recorded in the JSON export, to make FR-012's reconstruction guarantee cover random/library-sourced puzzles and to make the pipeline's stochastic paths deterministically testable.
