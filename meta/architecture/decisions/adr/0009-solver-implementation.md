# ADR-0009: Solver implementation strategy

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-006 already fixes the solver's TECHNIQUE — constraint propagation combined with backtracking, with fail-fast the moment a second distinct solution is found (AC-017) — but it does not fix the solver's IMPLEMENTATION. Three implementation paths were on the table: hand-roll a nonogram-specific line solver, encode the puzzle into OR-Tools CP-SAT and use its enumerate-with-limit-2 mode, or model the grid as variables in a generic pure-Python CSP library (e.g. python-constraint) and enumerate solutions.

This is the single most consequential technology choice in the tool. Two things make it so: CON-005 makes solver correctness mandatory — a false-positive "this puzzle has a unique solution" result is unacceptable — and the solver is also the sole source of the difficulty signals FR-009 needs (cells solved by line-only logic before the first branch, and how much backtracking a puzzle demands). Whatever implementation is chosen has to satisfy NFR-001's performance bounds, honor CON-005's correctness bar, and expose FR-009's signals as a natural by-product rather than a bolt-on.

## Decision

We hand-roll the line solver. The implementation performs per-line clue-to-possibility propagation — computing the intersection of all placements of a line's clue that are consistent with the currently known cells — iterating across rows and columns to a fixed point. When propagation alone stalls, it branches on the most-constrained unknown cell and recurses, terminating (fail-fast) the moment a second distinct full-grid solution is reached.

This is the only one of the three alternatives that natively produces FR-009's difficulty signals, because those signals — how much a puzzle yields to line-only logic before any guess is needed, and how much backtracking it demands — are internal states of exactly this algorithm; a black-box solver would require reimplementing this same logic as a second pass just to get the signal. It also makes AC-017's fail-fast-on-second-solution requirement a two-line change deep inside our own search, keeps the tool free of an external solver dependency (testable as a pure function for the EC-001 property test), and the classic line-solver algorithm is well documented and small (a few hundred lines) rather than a research undertaking.

## Consequences

### Positive
- FR-009's difficulty signals (line-logic-solvable cell count, backtracking depth/amount) fall out of the algorithm's own execution trace instead of requiring a second, separately-maintained analysis pass.
- AC-017 (fail-fast on a second distinct solution) is a natural, local check inside our own recursive search — no black-box API to coax into stopping early.
- No external solver dependency: the puzzle domain, requirements, and generation module (DEC-006's lean baseline) stay in pure Python with nothing to encode, no solver binary to bundle, no license or version-compat surface to track.
- The solver is testable as a pure function, satisfying the EC-001 property test requirement directly.

### Negative
- Correctness is entirely on us. CON-005 states a false-positive uniqueness result is unacceptable, and a hand-rolled search is exactly where such a bug would hide — in an off-by-one in line-possibility generation, a fixed-point loop that terminates early, or a branch-and-bound that misses a second solution. This risk is real and is explicitly not eliminated by this decision alone; it is mitigated by a separate decision, DEC-014 (ADR-0014), which establishes a brute-force reference oracle used as a ground truth in testing to catch exactly this class of false positive/negative.
- Performance tuning at the upper end of the supported grid range (up to 50x50, per DEC-001's timeout bound) is our problem to solve — there is no battle-hardened search engine underneath to absorb pathological cases.

### Neutral
- This decision fixes the solver's IMPLEMENTATION STRATEGY only. The specific data structures, the branching heuristic's tie-breaking rule, and micro-optimizations are left to implementation and code review, not to this ADR.
- Because correctness risk is carried forward rather than eliminated, this ADR and DEC-014/ADR-0014 should be read together: this decision explains why the risk exists, that ADR explains how it is caught before it reaches users.

## Alternatives considered

### cp_sat_encoding

Encode the clues as an OR-Tools CP-SAT model (an automaton/regular constraint per line) and use its enumerate-all-solutions mode with a solution limit of 2. This has a battle-hardened search engine going for it — very fast, with fail-fast for the second-solution check available for free via the solution limit — and it moves correctness risk out of the search itself. It was rejected for two reasons that were each independently disqualifying. First, FR-009's difficulty signals become unavailable or meaningless: CP-SAT's internal conflict/branching counts do not correspond to "cells a human would get from line logic alone," so CAP-004 would still need a second, hand-rolled line-logic pass just to produce the signal FR-009 requires — defeating the point of outsourcing the search. Second, encoding bugs replace search bugs rather than removing CON-005's risk, and OR-Tools is a very large dependency (tens of MB) for a hobby CLI tool, directly contradicting DEC-006's lean-baseline decision.

### generic_constraint_library

Model the grid as variables in a generic pure-Python CSP library (e.g. python-constraint) and enumerate solutions. This is pure Python and a small dependency, with less code to write than hand-rolling. It was rejected because generic CSP solvers are orders of magnitude too slow for nonogram-scale line constraints at 20x20 and above, which would break NFR-001's performance bounds outright — not a tuning problem but a fundamental mismatch between a generic constraint solver's search strategy and the structure nonogram lines actually have. It also shares the first alternative's flaw of yielding no usable FR-009 difficulty signal, since a generic CSP library's internal state has no correspondence to line-logic-solvable cells or backtracking amount.

## References

- DEC-009 (resolved by this ADR)
- FR-006 (fixes the solver technique; this ADR fixes its implementation)
- FR-009 (difficulty signals this decision's algorithm produces as a natural by-product)
- NFR-001 (performance bound this implementation must meet)
- CON-005 (correctness mandate; see Negative consequences)
- EC-001 (property test this implementation must satisfy as a pure function)
- DEC-014 / ADR-0014 (brute-force reference oracle mitigating this ADR's correctness risk)
- DEC-006 (lean dependency baseline, a reason the CP-SAT alternative was rejected)

## History

- 2026-08-27: Created — chose the hand-rolled line solver over a CP-SAT encoding and a generic CSP library, because it is the only alternative that natively yields FR-009's difficulty signals; correctness risk is acknowledged and deferred to DEC-014's brute-force oracle.
