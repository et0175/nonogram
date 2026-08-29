# CARD-017: Nudge-count reporting in CLI output

**Status:** in_progress
**Priority:** P3
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/017-nudge-count-reporting
**Worktree:** ../PythonProject4-card-017
**Source:** meta/architecture/handoff.md#increment-3
**Idea:** —
**Wave:** 11
**Depends on:** CARD-016
**Touches:** src/nonogram/cli.py, src/nonogram/orchestrator.py, tests/test_nudge_reporting.py
**Review score:** —
**Started:** 2026-08-29T10:40:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The last card of the plan, and deliberately the smallest: make the nudges visible.

FR-014 exists because ADR-0004 resolved DEC-004 — a tool that quietly alters the user's
picture and says nothing is not acceptable, but a diff view or a per-pixel report is more
than the CLI needs. The decision is a single count line at export time.

1. `nudge_count` is already carried on the `Puzzle` aggregate by COMP-002 (CARD-016). At
   export time COMP-001 prints one line stating how many cells were nudged.
2. **Zero nudges → no line at all** (AC-041). Not "0 cells nudged" — the absence of the line
   is the signal that the image came through untouched.
3. COMP-007 writes **no** nudge metadata into the image exports — the report is a CLI output
   line only (trace.yml FR-014 note).

## Acceptance criteria

- **AC-040** (happy) — given an exported puzzle whose image conversion required 2 pixel
  nudges to reach uniqueness, when the puzzle is exported, then the CLI output includes a
  line stating that 2 cells were nudged.
  *test:* `TestExport_ReportsNudgeCount`
- **AC-041** (boundary) — given an exported puzzle whose image conversion reached uniqueness
  with zero nudges, when the puzzle is exported, then no nudge-count line is printed.
  *test:* `TestExport_OmitsNudgeCountWhenZero`

## Guardrails

- G-1: Do not edit `src/nonogram/export/**` — COMP-007 writes no nudge metadata into the
  image exports; the report is a CLI output line only (trace.yml FR-014 note)
  (test: TestExport_WritesPNG, TestExport_WritesPDFPageOneBlankWithHeader)
- G-2: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/solver/**`,
  `src/nonogram/clues.py`, `src/nonogram/difficulty.py` — reporting is additive and must
  revert without touching random/library modes, the solver, or export (handoff Increment 3
  Rollback)
- G-3: Zero nudges prints nothing — do not "improve" this into a `0 cells nudged` line
  (AC-041 is the decision, ADR-0004)
- G-4: Out of scope — no per-pixel diff, no before/after image, no nudge coordinates.
  ADR-0004 chose the count over the diff deliberately
- G-5: The nudge count is read from the aggregate, not recomputed — do not re-derive it by
  comparing grids in `cli.py`

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-014
- **NFR:** —
- **ADR:** ADR-0004
- **Components:** COMP-001 (prints), COMP-002 (carries the count)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
