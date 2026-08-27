# CARD-009: Difficulty scoring formula from solver signals

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/009-difficulty-scoring
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-004, CARD-006, CARD-007
**Touches:** src/nonogram/difficulty.py, src/nonogram/solver/__init__.py, src/nonogram/solver/search.py, tests/test_difficulty.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-006 (Difficulty Scoring) — the second-riskiest thing in the plan after the solver, and
the reason Increment 2's checkpoint exists: the formula is untested until real puzzles are
scored.

1. **Solver signal emission (COMP-005).** The five signals of FR-009 are internal states of
   the hand-rolled solver (ADR-0009), so COMP-005 emits them: cells solved by line-only
   logic before the first branch, backtracking amount (branch nodes visited / depth), solve
   time, puzzle size, clue density. CARD-004 already returns them as part of the solve
   result — finish/normalize the surface here if a signal is missing, but do not change how
   the solver solves.
2. **Normalization and weighting (COMP-006, ADR-0013).** Normalize each signal to 0..1 and
   combine into a single 0..100 score with the ADR-0013 weights. Size and clue density are
   normalizers, not difficulty in themselves — a big easy puzzle must not out-score a small
   hard one purely on cell count.
3. **Monotonicity sanity.** A puzzle solved entirely by line logic with zero backtracking
   must land at the easiest end of the scale (AC-023). That is the anchor point of the whole
   scale; if the weights make it possible to score such a puzzle mid-range, the weights are
   wrong, not the test.
4. Keep `difficulty.py` a pure function of the solve result — no solver re-entry, no I/O.
   CARD-010's resample loop calls it once per candidate.

## Acceptance criteria

- **AC-022** (happy) — given solver signals for a 15x15 candidate (80% of cells solved by
  line-logic, low backtracking, 0.2s solve time), when the candidate is scored, then a single
  numeric difficulty score is produced reflecting the weighted combination of all signals.
  *test:* `TestScoreDifficulty_CombinesSignals`
- **AC-023** (boundary) — given a candidate solved entirely by line-logic with zero
  backtracking, when the candidate is scored, then the score falls at the easiest end of the
  scale.
  *test:* `TestScoreDifficulty_ZeroBacktrackingScoresEasiest`

## Guardrails

- G-1: Do not edit `src/nonogram/export/**` — owned by CARD-012 and CARD-013 this wave
- G-2: Do not edit `src/nonogram/sourcing/**` — owned by CARD-008 this wave
- G-3: Do not edit `src/nonogram/orchestrator.py`, `src/nonogram/cli.py` — the tier selector
  and resample loop are CARD-010; this card only produces a score
- G-4: **Solver semantics unchanged.** This card may extend the solver's signal *reporting*
  (Increment 2 is additive), but must not alter propagation, search order, or the uniqueness
  verdict. `PropertyTest_Solver_NeverFalsePositiveUniqueness`, `TestSolver_ReportsUniqueSolution`,
  `TestSolver_FailsFastOnSecondSolution` and `TestGenerate_50x50_RespectsTimeoutBound` must
  still pass unchanged (handoff Increment 2 Rollback: "revert without touching the solver or
  orchestrator's core generation logic")
  (test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- G-5: Difficulty is a heuristic score bucket, not a construction guarantee (CON-004). Do not
  add grid-construction logic that tries to *build* an easy or hard puzzle — scoring
  classifies candidates, it never shapes them
- G-6: Signal collection must not move the NFR-001 p95 budget — instrumentation stays O(1)
  per propagation step (test: BenchGenerate_20x20_p95Under5s)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-009
- **NFR:** —
- **CON:** CON-004
- **ADR:** ADR-0009, ADR-0013
- **Components:** COMP-006 (Difficulty Scoring), COMP-005 (signal emission)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
