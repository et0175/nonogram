# CARD-013: CSV export and exact round-trip fidelity

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/013-csv-export-roundtrip
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-006, CARD-007
**Touches:** src/nonogram/export/csv_export.py, src/nonogram/export/json_export.py, src/nonogram/export/__init__.py, tests/test_export_csv.py, tests/property/test_export_roundtrip.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Completes FR-012: CARD-007 delivered the JSON writer; this card adds CSV and proves the
round-trip property that makes both formats trustworthy as an interchange representation.

1. `export/csv_export.py` — write the full solution grid and the row/column clues. CSV is
   flat, so pick a layout that survives decoding unambiguously (e.g. a grid block and a
   clue block with explicit section markers, or a header row naming each block) and document
   it in the module docstring. Ragged clue rows must round-trip exactly, including the
   empty-row marker `[0]`.
2. A **decoder** for both JSON and CSV (the JSON decoder lands alongside CARD-007's writer in
   `export/json_export.py` — that file is this card's to extend, the CSV half is new). The
   round-trip is not testable without one, and EC-002 asserts a property of the pair, not of
   the writer alone.
3. Register `csv` in `export/__init__.py`'s dispatch table. `--export`'s accepted values are
   derived from that registry (CARD-007), so this card needs **no** `cli.py` edit.
4. EC-002's property test: for any finalized puzzle, decode → compare. Round-trip fidelity
   holds because ADR-0012 exports the boundary type (`list[list[bool]]` + clue tuples), never
   the solver's internal bitmask — if a change here makes the property fail, the fix is the
   representation, not the tolerance.

## Acceptance criteria

- **AC-032** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported as
  CSV, then the CSV file contains the full solution grid and clues.
  *test:* `TestExport_WritesCSV`
- **AC-033** (boundary) — given a puzzle exported as JSON, when that JSON is decoded back,
  then the resulting grid and clues are exactly identical to the original puzzle's.
  *test:* `TestExport_JSONRoundTripsExactly`

## Engineering constraints

- **EC-002** (consistency, instances: AC-033) — For any finalized puzzle, decoding its
  exported JSON or CSV representation reproduces the exact original solution grid and clues.
  *test:* `PropertyTest_Export_RoundTripsExactlyForAnyPuzzle`
  A genuinely multi-case property test: generate puzzles across the supported size range and
  a spread of densities (including all-empty and all-filled lines), export, decode, and
  assert exact equality of both grid and clues — for **both** formats, not just JSON.

## Guardrails

- G-1: Do not edit `src/nonogram/export/png.py`, `src/nonogram/export/svg.py`,
  `src/nonogram/export/layout.py` — owned by CARD-012 this wave. `export/__init__.py` is
  shared with CARD-012 (both register a format): keep the edit to adding a row to the
  dispatch table, never restructuring it
- G-2: Do not edit `src/nonogram/sourcing/**` (CARD-008), `src/nonogram/difficulty.py`
  (CARD-009), `src/nonogram/orchestrator.py` and `src/nonogram/cli.py` (CARD-008/CARD-011
  this wave)
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py` — export is additive on
  top of Increment 1 and must revert without touching the solver or the orchestrator's core
  generation logic (handoff Increment 2 Rollback)
- G-4: Serialize the ADR-0012 boundary type only — never the solver's internal bitmask.
  EC-002's fidelity is a consequence of that decision (trace.yml FR-012 note)
- G-5: No new dependency — stdlib `json` and `csv` (ADR-0006)
- G-6: Out of scope — no PDF (CARD-014), no interactive/playable output (CON-002)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-012 (completion — CSV + round-trip)
- **NFR:** —
- **EC:** EC-002
- **CON:** CON-002
- **ADR:** ADR-0012, ADR-0015
- **Components:** COMP-007 (Export Renderers)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
