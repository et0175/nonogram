# CARD-002: Clue derivation via run-length encoding

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/002-clue-derivation
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 2
**Depends on:** CARD-001
**Touches:** src/nonogram/clues.py, tests/test_clues.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-004 (Clue Derivation) — a pure function module, no state, no I/O.

Given a solution grid in the ADR-0012 boundary representation (`list[list[bool]]`), compute
the row clues and column clues by run-length encoding contiguous filled runs. A line with no
filled cells encodes to the empty-row marker `[0]` (AC-013) — not `[]`, so downstream
renderers and the solver see a uniform shape.

Also provide the inverse check used by INV-001 and by the solver's line logic: given a line
clue and a line, confirm the clue is exactly that line's run-length encoding. AC-014 is that
check applied to every row and column of an arbitrary grid.

This module is the first consumer of ADR-0012's boundary type. Keep the public signature in
that type (`list[list[bool]]` in, `tuple[tuple[int, ...], ...]` out) — the solver's internal
int-bitmask representation is CARD-004's business and must not leak into this API.

## Acceptance criteria

- **AC-012** (happy) — given a grid row with pattern `██·███··`, when clues are computed for
  that row, then the row clue equals `[2, 3]`.
  *test:* `TestComputeClues_EncodesRunLengths`
- **AC-013** (boundary) — given a grid row with no filled cells, when clues are computed for
  that row, then the row clue is the empty-row marker `[0]`.
  *test:* `TestComputeClues_HandlesEmptyRow`
- **AC-014** (boundary, INV-001) — given any solution grid, when clues are computed for every
  row and column, then decoding each clue against the grid confirms it exactly matches that
  line's run-length encoding.
  *test:* `TestComputeClues_MatchesGridExactly`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/**` — owned by CARD-003 this wave
- G-2: Do not edit `src/nonogram/cli.py`, `src/nonogram/orchestrator.py`,
  `pyproject.toml` — CARD-001's deliverable; this card adds a module, it does not rewire
  the entry point
- G-3: The public clue API stays in the ADR-0012 boundary type (`list[list[bool]]` /
  int tuples). Out of scope — no solver-internal bitmask representation here; that is
  CARD-004's private concern

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-005
- **NFR:** —
- **INV:** INV-001
- **ADR:** ADR-0012
- **Components:** COMP-004 (Clue Derivation)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
