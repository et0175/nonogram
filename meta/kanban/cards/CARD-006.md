# CARD-006: Cooperative generation deadline and SolverTimeout

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/006-cooperative-deadline
**Worktree:** ../PythonProject4-card-006
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 5
**Depends on:** CARD-004, CARD-005
**Touches:** src/nonogram/solver/propagate.py, src/nonogram/solver/search.py, src/nonogram/orchestrator.py, src/nonogram/errors.py, tests/test_timeout.py, tests/bench_generate.py
**Review score:** —
**Started:** 2026-08-28T08:42:21Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

NFR-001's hard guarantee: a 50x50 request must **never hang**. Per ADR-0011 the mechanism is
a cooperative deadline, not a thread or a signal — the deadline is computed once by COMP-002
and checked inside COMP-005 at every propagation fixed point and every branch node.

1. **Deadline computation (COMP-002).** The orchestrator derives an absolute deadline from
   the request (30s hard bound up to 50x50 — ADR-0001) and passes it into every solver call.
   The deadline covers the whole generation request including regenerate retries, not each
   solve in isolation — otherwise 20 retries × 30s is a 10-minute "timeout".
2. **Cooperative checks (COMP-005).** At each propagation fixed point and each branch node,
   check the deadline and raise `SolverTimeout` when it has passed. Checks must be frequent
   enough that the observed overshoot is small, and cheap enough not to move the NFR-001
   p95 target for 20x20.
3. **Abandonment path.** The orchestrator converts `SolverTimeout` into the EVT-012
   abandonment path — a clean, clearly-worded failure with a non-zero exit code. Never a
   partial or unverified puzzle: INV-002 still holds, a timed-out puzzle is not exportable.
4. **Benchmark.** `BenchGenerate_20x20_p95Under5s` measures p95 completion for 20x20
   including regenerate retries. Keep it runnable and deterministic enough to be a gate
   (fixed seeds, fixed sample size); if p95 is not met, the finding is the deliverable —
   the fix belongs in the solver's propagation strength, not in loosening the threshold.

## Acceptance criteria

- **AC-037** (boundary) — given a 20x20 random-grid generation request under typical
  hardware, when generation runs, including any regenerate retries, then p95 completion time
  is ≤ 5s.
  *test:* `BenchGenerate_20x20_p95Under5s`
- **AC-038** (boundary) — given a 50x50 random-grid generation request (the largest
  supported size), when generation runs, then it completes within 30s or fails clearly with
  a `SolverTimeout` error (cooperative deadline enforced inside the solver — ADR-0011) — it
  never hangs indefinitely.
  *test:* `TestGenerate_50x50_RespectsTimeoutBound`

## Guardrails

- G-1: Do not edit `src/nonogram/export/**`, `src/nonogram/cli.py` — `export/**` is owned by
  CARD-007 this wave; the CLI flag surface is CARD-001's
- G-2: Solver semantics unchanged — this card adds deadline checks, it does not alter the
  propagation or search results. `PropertyTest_Solver_NeverFalsePositiveUniqueness`,
  `TestSolver_ReportsUniqueSolution`, `TestSolver_ReportsUnsolvable` and
  `TestSolver_FailsFastOnSecondSolution` must still pass unchanged
  (test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- G-3: No threads, subprocesses or signal handlers — the deadline is cooperative by decision
  (ADR-0011), and a preemptive mechanism would leave the `Puzzle` aggregate in an
  indeterminate state
- G-4: A timed-out puzzle is never marked ready for export (INV-002); the timeout path is an
  abandonment, not a degraded success
- G-5: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/clues.py`, `pyproject.toml` —
  outside this card's footprint

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** —
- **NFR:** NFR-001
- **INV:** INV-002
- **ADR:** ADR-0001, ADR-0009, ADR-0011, ADR-0012
- **Components:** COMP-002, COMP-005, COMP-003
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
