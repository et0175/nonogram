# CARD-004: Nonogram solver with fail-fast uniqueness check

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/004-solver-uniqueness
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 3
**Depends on:** CARD-002
**Touches:** src/nonogram/solver/__init__.py, src/nonogram/solver/propagate.py, src/nonogram/solver/search.py, tests/test_solver.py, tests/property/test_solver_uniqueness.py, tests/helpers/brute_force_oracle.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-005 (Solver) — the card the whole increment plan is ordered around. The handoff puts
it first because the riskiest open question is whether the hand-rolled solver is actually
correct; this card is where that is settled empirically rather than argued.

1. **Constraint propagation + backtracking (ADR-0009).** Hand-rolled, no third-party solver.
   Line-logic propagation to a fixed point, then branch on the most constrained undecided
   cell. Internal line representation is the int bitmask of ADR-0012 (the performance
   mechanism NFR-001's p95 target relies on); the public API stays in the boundary type.
2. **Solution counting with fail-fast (FR-006).** Report `0`, `1`, or `>=2`. On finding a
   second distinct solution, stop immediately — do **not** enumerate the rest. This is what
   makes the uniqueness check affordable inside CARD-005's retry loop.
3. **Purity (ADR-0007).** The solver is a pure function of clues: no filesystem, no CLI, no
   global state. That purity is precisely what makes EC-001's property test cheap to run at
   scale with no fixtures.
4. **Difficulty signal hooks.** Return the internal states CARD-009 will normalize into a
   score (cells solved by line-only logic before the first branch, backtracking amount,
   solve time). Emit them as part of the solve result now so CARD-009 does not have to
   reopen the solver's control flow later — but do not score anything here.
5. **Brute-force reference oracle (ADR-0014)** as a test helper in
   `tests/helpers/brute_force_oracle.py`: exhaustive enumeration for small grids, used only
   by the property test. It is the oracle, not a production path.

## Acceptance criteria

- **AC-015** (happy) — given clues with exactly one valid solution, when the puzzle is
  solved, then the solver reports `solution_count = 1` and returns that solution grid.
  *test:* `TestSolver_ReportsUniqueSolution`
- **AC-016** (negative) — given clues with zero valid solutions (a contradictory clue set),
  when the puzzle is solved, then the solver reports `solution_count = 0` and no solution
  grid is returned.
  *test:* `TestSolver_ReportsUnsolvable`
- **AC-017** (boundary) — given clues admitting more than one valid solution, when the puzzle
  is solved, then the solver stops immediately after finding a second distinct solution and
  reports `solution_count >= 2`, without enumerating every solution.
  *test:* `TestSolver_FailsFastOnSecondSolution`

## Engineering constraints

- **EC-001** (consistency, instances: AC-015) — The solver never reports
  `solution_count = 1` for a clue set that actually has 0 or more than 1 solutions, for any
  input clue set (the uniqueness check must never produce a false positive).
  *test:* `PropertyTest_Solver_NeverFalsePositiveUniqueness`
  This is a genuinely multi-case property test, not an example test: generate random grids
  up to 8x8, derive their clues (CARD-002), and cross-check the solver's verdict against
  ADR-0014's brute-force oracle. The increment-1 checkpoint requires ≥1000 cases passing.
  CON-005 makes it the one mandatory correctness property of the whole tool.

## Guardrails

- G-1: Hand-rolled solver only — do not introduce a third-party solver, SAT/CP library, or
  any dependency beyond the ADR-0006 baseline (ADR-0009 rejected the library route; ADR-0006
  closed the dependency baseline)
- G-2: `src/nonogram/solver/**` stays a pure function of clues — no filesystem, no CLI
  imports, no module-level mutable state (ADR-0007). The property test must need no fixture
- G-3: Do not edit `src/nonogram/clues.py` — CARD-002's deliverable. The solver consumes the
  clue API; the internal bitmask representation is private to `solver/` and must not leak
  back into the clue module's public type (ADR-0012)
- G-4: Do not edit `src/nonogram/cli.py`, `src/nonogram/orchestrator.py`,
  `src/nonogram/sourcing/**`, `pyproject.toml` — outside this card's footprint
- G-5: Out of scope — no difficulty scoring (FR-009, CARD-009), no timeout/deadline
  enforcement (ADR-0011, CARD-006), no retry loop (FR-007, CARD-005). This card emits the
  signals and exposes the propagation fixed points those cards hook into; it does not
  consume them

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-006
- **NFR:** NFR-001 (partial — the bitmask representation is the performance mechanism)
- **CON:** CON-005 (mandatory)
- **EC:** EC-001
- **ADR:** ADR-0009, ADR-0011, ADR-0012, ADR-0014
- **Components:** COMP-005 (Solver)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
