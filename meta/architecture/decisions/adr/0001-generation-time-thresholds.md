# ADR-0001: Generation-time thresholds for random puzzle generation

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

NFR-001 requires random puzzle generation to feel interactive for common grid sizes, and NFR-002 already bounds the regenerate/resample retry loop's iteration count — but neither NFR pins down the actual wall-clock numbers a generation run must meet. docs/requirements.md's NFR-1 only says generation should complete in "a few seconds" for typical sizes, and NFR-2/AC-038 (the 50x50 case) only says the largest supported size must complete "within the configured timeout bound or fail clearly with a timeout error — it never hangs indefinitely," without stating what that bound is.

This leaves two numbers open: (a) the p95 generation-time cap for grids up to 20x20, the size range NFR-001's "typical hardware" condition and AC-037 target, and (b) the hard timeout bound for larger grids (up to the 50x50 maximum size AC-038 exercises), where the regenerate loop's own retry cap (NFR-002) does not guarantee an overall time bound because a single unlucky solve can itself run long. No empirical solver benchmarks exist yet to derive either number from measured performance; both are threshold choices to be validated once the solver (FR-006) is implemented and can be profiled at 20x20 and 50x50.

## Decision

We adopt a 5-second p95 generation-time cap for grids up to and including 20x20, and a 30-second hard timeout for larger grids up to the 50x50 maximum. This satisfies NFR-001 because 5s directly matches docs/requirements.md's "a few seconds" language for the common case, and it gives AC-038's 50x50 case a single, simple timeout bound rather than a second tunable parameter to justify. The two thresholds are independent: the 5s figure is a p95 target validated by benchmark (AC-037, test BenchGenerate_20x20_p95Under5s), while the 30s figure is a hard ceiling enforced as a failure boundary (AC-038, test TestGenerate_50x50_RespectsTimeoutBound) — exceeding it must produce a clear timeout error, not a hang.

## Alternatives considered

### 10s_cap_60s_timeout

Doubles both numbers: a 10s p95 cap for grids up to 20x20 and a 60s hard timeout for larger sizes. This was rejected because it gives up the direct match to docs/requirements.md's "a few seconds" phrasing for the 20x20 case in exchange for headroom that has not been shown to be necessary — no benchmark data yet indicates the solver needs it. The extra headroom mainly protects against slower hardware or unusually dense grids, but at the cost of a less "interactive" feel for a CLI tool used interactively, which is precisely the property NFR-001 exists to protect.

## Consequences

### Positive
- Gives NFR-001 and AC-037/AC-038 concrete, testable numbers, unblocking benchmark test implementation (BenchGenerate_20x20_p95Under5s, TestGenerate_50x50_RespectsTimeoutBound) instead of leaving them as placeholder thresholds.
- Keeps the common-case experience (grids up to 20x20) genuinely interactive, matching the "a few seconds" intent from docs/requirements.md rather than drifting toward a looser, less-CLI-appropriate bound.
- A single hard timeout for all larger sizes (up to 50x50) is simple to implement and reason about — one deadline mechanism, no per-size sliding scale.

### Negative
- 30s may feel slow for a CLI tool if a user is waiting interactively on a large grid, since nothing in this decision distinguishes "still working" from "about to fail" during that window.
- Neither number is validated against actual solver performance yet; if profiling after FR-006 is implemented shows the solver routinely takes longer than 5s at 20x20 or needs more than 30s at 50x50 on typical hardware, this ADR will need to be revisited.

### Neutral
- This ADR fixes the threshold NUMBERS only; the MECHANISM by which the 30s deadline is enforced and a running generation is interrupted is a separate decision (tracked as DEC-011, which depends on this one being resolved).
- The 5s figure becomes a benchmark gate (AC-037) rather than a hard failure boundary, while the 30s figure becomes a hard failure boundary (AC-038) — future work should keep this asymmetry explicit rather than treating both as the same kind of threshold.
- Once real benchmark data exists, these thresholds are candidates for the same "tunable later" treatment other unvalidated numeric constants in this model (e.g. DEC-005's difficulty cutoffs) already have.

## References

- DEC-001 (resolved by this ADR)
- NFR-001 (p95 generation-completion-time metric this decision fixes)
- AC-037, AC-038 (acceptance criteria this decision makes testable)
- DEC-011 (the timeout ENFORCEMENT MECHANISM, dependent on this ADR's numbers)

## History

- 2026-08-27: Created — fixed the 5s p95 cap for grids <=20x20 and the 30s hard timeout for larger sizes, matching docs/requirements.md's "a few seconds" language over the more conservative 10s/60s alternative.
