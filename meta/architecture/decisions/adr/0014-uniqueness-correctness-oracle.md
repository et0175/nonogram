# ADR-0014: Uniqueness correctness oracle

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

CON-005 is the one mandatory-severity constraint in the entire model: "the uniqueness check must never produce a false positive" — a puzzle the tool accepts as unique must never actually have 0 or more than 1 solutions. EC-001 turns that constraint into a testable property, `PropertyTest_Solver_NeverFalsePositiveUniqueness`, requiring that the solver never report `solution_count = 1` for a clue set that actually has 0 or more than 1 solutions, for any input clue set.

A property test needs something to check the solver's verdict against, and no such oracle was specified. This gap is not academic: ADR-0009 already committed the tool to a hand-rolled line solver (constraint propagation + backtracking, fail-fast on the second distinct solution) precisely because it is the only implementation strategy that natively produces FR-009's difficulty signals. ADR-0009 explicitly named this decision as its mitigation — a hand-rolled search is exactly where an off-by-one in line-possibility generation, an early-terminating fixed-point loop, or a branch-and-bound that misses a second solution would hide, and CON-005 makes such a bug unacceptable. Without an independent way to check the solver's uniqueness verdict, ADR-0009's correctness risk would be carried forward but never actually tested — EC-001 would exist on paper with no way to enforce it. This ADR is what makes ADR-0009's solver choice testable against an independent implementation.

## Decision

We use a brute-force reference oracle. A deliberately naive, obviously-correct reference solver — exhaustive enumeration of every line placement combination — is written and used only in tests, never shipped in the production path. Two complementary property tests exercise it:

1. **Cross-check on small grids.** For randomly generated grids up to 8x8 (where exhaustive enumeration is cheap), assert that the fast solver's solution count agrees exactly with the reference solver's count, across many random clue sets.
2. **Free-direction round-trip, at any size.** Generate a random grid, derive its clues, and assert the fast solver always finds at least that grid as a solution. This direction needs no oracle at all and scales to 50x50, the tool's full supported grid range.

Together these give EC-001 an actual enforcement mechanism: the cross-check catches count-of-solutions errors (the false positive/negative class CON-005 forbids) on grids small enough to brute-force, and the round-trip check extends coverage of "the solver at least finds a known-valid solution" to the full size range where brute force is infeasible.

## Consequences

### Positive
- CON-005 — the model's one mandatory-severity constraint — now has a genuine independent check. Two implementations agreeing is real evidence of correctness; one implementation self-checking its own output is not.
- EC-001's property test, `PropertyTest_Solver_NeverFalsePositiveUniqueness`, becomes enforceable as an actual property over randomly generated clue sets, not a handful of hand-picked examples.
- The reference solver's naivety is a feature: exhaustive enumeration is short and simple enough to eyeball for correctness, which is exactly what makes it trustworthy as ground truth.
- The round-trip direction requires no oracle and costs nothing to scale, so it extends meaningful coverage all the way to 50x50 — the full grid range NFR-001/DEC-001 commit the tool to — where exhaustive cross-checking is not affordable.
- ADR-0009's correctness risk, explicitly deferred to this decision, is now actually mitigated rather than just acknowledged.

### Negative
- A second solver implementation has to be written and kept in the test tree indefinitely — it is not throwaway scaffolding, since the property test depends on it for the life of the project.
- Exhaustive agreement is only affordable on small grids (<= 8x8). Confidence at larger sizes rests on the strictly weaker round-trip property, which can prove the solver finds a valid solution but cannot prove it correctly detects a SECOND one — the exact failure mode CON-005 forbids. Large-grid false-positive risk is therefore reduced, not eliminated, by this decision.

### Neutral
- This decision fixes the ORACLE STRATEGY only. The reference solver's exact enumeration order, the random-grid generation distribution used to drive the property tests, and the number of trial iterations are left to implementation, not to this ADR.
- This ADR and ADR-0009 should be read together: ADR-0009 explains why solver correctness risk exists (a hand-rolled search was chosen for its difficulty-signal and fail-fast properties over safer black-box alternatives), and this ADR explains how that risk is caught before it reaches users.

## Alternatives considered

### curated_fixture_corpus

Assert the fast solver's behavior against a checked-in corpus of published nonograms with known solution counts (unique, ambiguous, contradictory). This is cheap to build and would catch gross regressions on realistic inputs. It was rejected because fixtures are examples, not a property — EC-001's statement is "for any input clue set," which a finite fixture list structurally cannot establish. It also pushes the hard problem onto curation: hand-verifying that a hand-picked case is genuinely ambiguous or genuinely contradictory is itself error-prone, and sourcing published puzzles raises a needless provenance/licensing question for a hobby CLI tool.

### self_consistency_only

Verify only that every solution the solver returns actually satisfies its own clues — cheap, and always checkable with no independent oracle. This catches the "solver returns a grid that doesn't match its own clues" class of bug, but it is blind to the one failure CON-005 actually forbids: the solver missing a second valid solution and wrongly reporting a count of 1. A verifier that only checks returned grids can never detect a solution the solver failed to find, which is precisely where a false-positive uniqueness verdict lives. This alternative would leave the tool's one mandatory-severity property untested and was rejected on that basis alone.

## References

- DEC-014 (resolved by this ADR)
- CON-005 (the mandatory correctness constraint this oracle exists to enforce)
- EC-001 (the property test, `PropertyTest_Solver_NeverFalsePositiveUniqueness`, this oracle makes enforceable)
- FR-006, AC-015, AC-016, AC-017 (uniqueness-check behavior this oracle validates)
- ADR-0009 (hand-rolled solver implementation; named this decision as its correctness-risk mitigation)
- DEC-001 (50x50 as the tool's upper supported grid size, the ceiling the round-trip check is scaled to)

## History

- 2026-08-27: Created — chose a brute-force reference oracle (exhaustive cross-check on <=8x8 grids plus a free-direction round-trip check to 50x50) over a curated fixture corpus and a self-consistency-only check, because it is the only alternative that gives EC-001 a genuine independent property rather than examples or a check blind to CON-005's actual failure mode.
