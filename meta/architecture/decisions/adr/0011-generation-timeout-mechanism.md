# ADR-0011: Generation timeout enforcement mechanism

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

NFR-001 and AC-038 require that a 50x50 generation run "completes within the configured timeout bound or fails clearly with a timeout error — it never hangs indefinitely." ADR-0001 fixed the NUMBER for that bound (a 30-second hard timeout for grids larger than 20x20), but left open the MECHANISM by which that deadline is actually enforced and a running generation is interrupted.

The regenerate/resample retry bound from NFR-002 does not, by itself, provide this guarantee: it caps the number of attempts, not the wall-clock time of any single attempt, and a single unlucky solver invocation (FR-006's constraint-propagation-plus-backtracking search) can exceed the entire time budget on its own before the retry loop ever gets a chance to give up and try again. The mechanism therefore has to reach into an in-flight generation attempt and stop it once the deadline has passed, not merely bound how many attempts are made.

The design is constrained by vision.md's single-process, local-file-I/O topology (no second process or service is assumed to exist), by CON-005's mandatory requirement that the solver's uniqueness verdict never be a false positive (an interruption mechanism must not leave the search in a state that could produce a wrong answer), and by the existing failure-handling shape of the domain model, where CMD-011 already defines a clean generation-abandonment path (EVT-012, GenerationAbandoned) for cases where generation cannot succeed within its bounds. The mechanism must also work correctly regardless of the runtime environment the tool is exercised in, including test runners that may execute code across threads or worker processes (e.g. pytest-xdist), and regardless of host OS.

## Decision

We will enforce the generation deadline cooperatively inside the solver rather than by interrupting it from the outside. The orchestrator computes a deadline (the current monotonic time plus the ADR-0001 timeout bound) and passes it into the solver call; the solver checks the monotonic clock at each propagation fixed-point and at each branch node during its search, and raises a `SolverTimeout` exception the instant the deadline has passed. The orchestrator catches `SolverTimeout` and converts it into the same clean abandonment path the domain model already defines for other unrecoverable generation failures — CMD-011's EVT-012 `GenerationAbandoned` event — rather than inventing a second, parallel failure mode.

This satisfies NFR-001/AC-038 because the check happens frequently enough (once per propagation pass or branch node, not once per whole solve) that the solver cannot run unboundedly past the deadline, while adding negligible cost relative to the propagation work itself. It is chosen over the alternatives because it is portable and deterministic: it behaves identically on every OS and inside any thread or process a test runner happens to use, and it can be unit-tested directly by injecting an artificially near deadline, with no reliance on OS-level interrupt delivery or a second process.

## Alternatives considered

### signal_alarm

Set `signal.alarm`/`SIGALRM` around the generation call and convert the interrupt into a timeout error. This was rejected because it is POSIX main-thread only — it breaks under pytest-xdist workers, on Windows, and in any future context where the solver is invoked off the main thread. It also interrupts execution at an arbitrary bytecode boundary, which risks leaving the `Puzzle` aggregate in an undefined state mid-nudge or mid-resample, something CON-005's correctness requirement cannot tolerate.

### subprocess_with_timeout

Run generation in a child process and kill it on timeout. This was rejected because it introduces a second process into a design that vision.md pins as single-process, which would surface as an additional container in the C4 view for no domain benefit, and it requires serializing grids and export data across the process boundary purely to support a timeout — heavy machinery disproportionate to a hobby CLI tool.

### no_enforced_timeout

Rely solely on the NFR-002 retry bound and document that a single pathological solve may run long. This was rejected because it directly fails AC-038 as written ("never hangs indefinitely") — the worst case remains unbounded precisely at the 50x50 size where the guarantee matters most, and the retry bound offers no protection against a single invocation that itself exceeds the whole time budget.

## Consequences

### Positive
- Gives NFR-001/AC-038 a concrete, testable enforcement path: a `SolverTimeout` can be triggered deterministically in tests by injecting a near-immediate deadline, with no reliance on real wall-clock waits or OS interrupt timing.
- Reuses the existing EVT-012 `GenerationAbandoned` failure path instead of adding a second, parallel failure mode for the orchestrator and callers to handle.
- Portable by construction — identical behavior on every OS, inside threads, and under test runners that parallelize across processes (e.g. pytest-xdist), which the signal-based alternative could not offer.
- Overshoot is bounded and safe: because the check happens between propagation/branch steps rather than mid-operation, the solver never raises `SolverTimeout` in a state that could produce an incorrect or partial uniqueness verdict, preserving CON-005.

### Negative
- Granularity is bounded by how long a single propagation pass or branch step takes; a pathological single pass (e.g. an unusually expensive line intersection at 50x50) can cause the actual return time to overshoot the configured deadline slightly rather than stopping at the exact instant it elapses.
- Threads the deadline (or a remaining-time budget) through the solver's public signature, which every caller of the solver — including the property tests for EC-001 — must now account for, even when they don't care about timeouts.

### Neutral
- This ADR fixes the enforcement MECHANISM only; the timeout NUMBER itself (30s for grids larger than 20x20) was already fixed by ADR-0001 and is not reopened here.
- The choice of solver implementation (DEC-009, still open at the time of this ADR) must expose fixed-point and branch-node boundaries the deadline check can hook into; any solver technique adopted under DEC-009 needs to preserve those checkpoints for this mechanism to remain applicable.
- `SolverTimeout` becomes a new exception type in the solver's public contract, alongside whatever exceptions already signal contradiction/no-solution outcomes; downstream code (the orchestrator, tests) needs to distinguish it from those.

## References

- DEC-011 (resolved by this ADR)
- ADR-0001 (fixes the timeout NUMBER this ADR's mechanism enforces)
- NFR-001, AC-038 (requirements this decision makes achievable in practice, not just in principle)
- FR-006 (the solver technique this mechanism instruments)
- CON-005 (mandatory solver-correctness constraint the mechanism must not violate)
- CMD-011, EVT-012 (the existing GenerationAbandoned path this mechanism reuses)
- DEC-009 (solver implementation choice this mechanism's checkpoints depend on)

## History

- 2026-08-27: Created — adopted a cooperative deadline checked inside the solver at each propagation/branch step, raising `SolverTimeout` into the existing GenerationAbandoned path, over signal-based interruption and a subprocess-based hard kill.
