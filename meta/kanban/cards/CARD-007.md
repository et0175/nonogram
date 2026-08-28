# CARD-007: JSON export and the export-readiness gate

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/007-json-export
**Worktree:** ../PythonProject4-card-007
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 5
**Depends on:** CARD-005
**Touches:** src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/orchestrator.py, src/nonogram/cli.py, tests/test_export_json.py
**Review score:** —
**Started:** 2026-08-28T08:42:21Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-007 (Export Renderers), **JSON only** — the minimal export that closes the
increment-1 walking skeleton (`nonogram generate --mode random --size 10 --seed 42
--export json` end to end). The other four formats are Increment 2.

1. `export/__init__.py` — the format registry / dispatch table plus the shared "write to
   `--out`" plumbing. Keep it a thin table: CARD-012 (PNG/SVG), CARD-013 (CSV) and CARD-014
   (PDF) each add a row, so the table is the one shared file in this module and must stay
   trivial to extend. **Derive `--export`'s accepted values from this registry** rather than
   listing them in `cli.py` — that is what lets the four later format cards ship without
   editing the CLI adapter at all.
2. `export/json_export.py` — serialize the finalized puzzle: the full solution grid and the
   row/column clues, in the ADR-0012 boundary types (`list[list[bool]]` + clue tuples),
   never the solver's internal bitmask. Also record the seed (ADR-0015) so an exported
   puzzle can be traced back to the request that produced it.
3. **Wire the INV-002 gate.** Export is refused unless the orchestrator's
   `ready_for_export` flag is set (CARD-005 owns the flag; this card is its first consumer).
   The check is enforced in COMP-002, not inside the renderer — ADR-0007's
   single-enforcement-point rule, so all five formats inherit one gate rather than five.
4. CLI wiring: `--export json --out <path>` writes the file and reports the written path.

## Acceptance criteria

- **AC-031** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported
  as JSON, then the JSON file contains the full solution grid and clues.
  *test:* `TestExport_WritesJSON`

_Note: FR-012's CSV output (AC-032), the exact round-trip (AC-033) and EC-002's round-trip
property test are CARD-013 — this card delivers FR-012's JSON half per the Increment 1
scope line ("minimal JSON export (FR-012, partial)")._

## Guardrails

- G-1: Do not edit `src/nonogram/solver/**`, `src/nonogram/errors.py` — `solver/**` and the
  error hierarchy's timeout additions are owned by CARD-006 this wave
- G-2: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/clues.py`, `pyproject.toml` —
  outside this card's footprint. Serialization uses stdlib `json`; the ADR-0006 dependency
  baseline is closed
- G-3: The INV-002 readiness gate is enforced in COMP-002 (`orchestrator.py`), not inside
  the renderer (ADR-0007, trace.yml FR-011 note). Do not duplicate the check into
  `export/`
- G-4: The exported representation is the ADR-0012 boundary type. Do not export the solver's
  internal bitmask — EC-002's round-trip fidelity (CARD-013) depends on that choice
- G-5: Out of scope — no PNG, SVG, CSV or PDF renderer (Increment 2: CARD-012, CARD-013,
  CARD-014), and no interactive/playable output ever (CON-002)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-012 (partial — JSON half)
- **NFR:** —
- **INV:** INV-002
- **CON:** CON-002, CON-003
- **ADR:** ADR-0007, ADR-0012, ADR-0015
- **Components:** COMP-007 (Export Renderers), COMP-002 (readiness gate)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
