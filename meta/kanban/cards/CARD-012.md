# CARD-012: PNG and SVG export renderers

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/012-png-svg-export
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-006, CARD-007
**Touches:** src/nonogram/export/png.py, src/nonogram/export/svg.py, src/nonogram/export/layout.py, src/nonogram/export/__init__.py, src/nonogram/orchestrator.py, tests/test_export_image.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The print-ready half of COMP-007: a finalized puzzle rendered as the **blank** grid plus its
row and column clues — what a person prints and solves. The solution is deliberately not on
these outputs (it is the JSON/CSV export's job, and the PDF answer key's).

1. `export/layout.py` — the shared geometry: clue gutter widths derived from the longest
   row/column clue, cell size, grid lines with heavier every-5th rules. Both renderers and
   CARD-014's PDF consume this, so keep it a pure function of (grid size, clues) returning
   coordinates — no Pillow or SVG types in its signature.
2. `export/png.py` — raster via Pillow (ADR-0006), at a resolution that stays legible when
   printed at A4. **This raster path is what CARD-014's PDF reuses** (CON-006: PDF is a
   second sink on this path, not a new dependency), so expose the rendered `Image` object,
   not only the file-writing wrapper.
3. `export/svg.py` — vector output via stdlib string/XML generation; no new dependency.
4. Register both formats in `export/__init__.py`'s dispatch table. `--export`'s accepted
   values are derived from that registry (CARD-007), so this card needs **no** `cli.py` edit.
5. **AC-030 — the INV-002 export gate.** Export of an unverified puzzle is refused and
   nothing is written. The check is enforced in COMP-002 (CARD-005/007 built it); this card
   adds the test that proves the gate holds for the image formats and that no partial file
   is left on disk.

## Acceptance criteria

- **AC-028** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported
  as PNG, then a PNG file containing the blank grid and clues is written to disk.
  *test:* `TestExport_WritesPNG`
- **AC-029** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported
  as SVG, then an SVG file containing the blank grid and clues is written to disk.
  *test:* `TestExport_WritesSVG`
- **AC-030** (negative, INV-002) — given a puzzle that has not yet passed the uniqueness
  check, when export is requested, then export is rejected and nothing is written, because
  the puzzle is not ready.
  *test:* `TestExport_RejectsUnverifiedPuzzle`

## Guardrails

- G-1: Do not edit `src/nonogram/export/csv_export.py`, `src/nonogram/export/json_export.py`
  — owned by CARD-013 this wave. `export/__init__.py` is shared with CARD-013 (both register
  a format): keep the edit to adding rows to the dispatch table, never restructuring it
- G-2: Do not edit `src/nonogram/sourcing/**` (CARD-008), `src/nonogram/difficulty.py`
  (CARD-009), `src/nonogram/cli.py` (CARD-008 and CARD-011 own it this wave) — registering
  the formats in `export/__init__.py` is sufficient, because `--export`'s accepted values
  are derived from that registry (CARD-007)
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py` — export is additive on
  top of Increment 1 and must revert without touching the solver or the orchestrator's core
  generation logic (handoff Increment 2 Rollback)
- G-4: No new dependency — PNG via Pillow, SVG via stdlib string generation (ADR-0006,
  CON-006). Do not reach for `svgwrite`, `cairosvg`, `reportlab` or similar
- G-5: The INV-002 readiness gate stays in COMP-002 (ADR-0007, trace.yml FR-011 note) — do
  not duplicate the check inside the renderers
- G-6: Out of scope — no interactive or playable output; v1 ships static files only
  (CON-002). No PDF (CARD-014)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-011
- **NFR:** —
- **INV:** INV-002
- **CON:** CON-002, CON-006
- **ADR:** ADR-0006, ADR-0007, ADR-0008
- **Components:** COMP-007 (Export Renderers), COMP-002 (readiness gate)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
