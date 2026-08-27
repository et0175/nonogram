# CARD-014: Two-page PDF export with answer key

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/014-pdf-export
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 8
**Depends on:** CARD-010, CARD-012, CARD-013
**Touches:** src/nonogram/export/pdf.py, src/nonogram/export/__init__.py, src/nonogram/export/layout.py, src/nonogram/orchestrator.py, tests/test_export_pdf.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

A fifth renderer inside COMP-007, **not** a new component: CON-006 makes PDF a second sink
on the existing PNG raster path (trace.yml FR-016 note).

1. **Two pages.** Page 1: the blank puzzle with clues, i.e. exactly CARD-012's PNG raster.
   Page 2: the answer key — the same layout with the solution grid revealed. Both pages
   carry a header reading `<name> — <difficulty tier>` (the name from FR-015/CARD-011, the
   tier from FR-008/CARD-010).
2. **Assembly (ADR-0006, CON-006).** Render each page as a Pillow raster through CARD-012's
   `layout.py` + `png.py` path, then `save(..., save_all=True, append_images=[page2])`.
   Pillow's built-in PDF save is the whole mechanism — **no new dependency**, and ADR-0006's
   baseline is not reopened.
3. **Filename (ADR-0016).** The on-disk name is `<name>-<difficulty>.pdf`. Sanitize the
   puzzle name into a filesystem-safe slug (it can come from `--name` with arbitrary user
   input).
4. **Collision handling (ADR-0017).** On an existing file, append an incrementing suffix.
   That suffix search is export-path logic COMP-007 owns and must test — including the
   sequence beyond the first collision (`-1`, `-2`, ...) and the case where an intervening
   file appears.
5. **AC-048 — the INV-002 gate.** Same gate as AC-030: an unverified puzzle is refused and
   no PDF is written. Enforced in COMP-002, not COMP-007 (ADR-0007).

## Acceptance criteria

- **AC-046** (happy) — given a finalized, uniqueness-confirmed puzzle named `"cat"` with
  difficulty tier `"Medium"`, when it is exported as PDF, then a two-page PDF file is written
  to disk whose page 1 shows the blank grid with clues and a header reading `"cat — Medium"`.
  *test:* `TestExport_WritesPDFPageOneBlankWithHeader`
- **AC-047** (happy) — given the same finalized puzzle exported as PDF, when page 2 is
  inspected, then page 2 shows the revealed solution grid with the same `"cat — Medium"`
  header.
  *test:* `TestExport_WritesPDFPageTwoAnswerKeyWithHeader`
- **AC-048** (negative, INV-002) — given a puzzle that has not yet passed the uniqueness
  check, when PDF export is requested, then export is rejected and no PDF file is written,
  because the puzzle is not ready.
  *test:* `TestExport_RejectsUnverifiedPuzzleForPDF`

## Guardrails

- G-1: **No new third-party dependency.** PDF is the existing PNG raster path saved with
  Pillow's `save_all`/`append_images` (CON-006, ADR-0006). Do not add `reportlab`, `fpdf`,
  `weasyprint` or similar, and do not edit `pyproject.toml`'s dependency list
- G-2: Do not edit `src/nonogram/export/png.py`, `src/nonogram/export/svg.py`,
  `src/nonogram/export/csv_export.py` — CARD-012/013's deliverables. This card **reuses**
  the raster path; if it needs a change to be reusable, that is an escalation, not an edit
  (test: TestExport_WritesPNG, TestExport_WritesSVG)
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`,
  `src/nonogram/sourcing/**`, `src/nonogram/difficulty.py` — export is additive on top of
  Increment 1 and must revert without touching the solver or the orchestrator's core
  generation logic (handoff Increment 2 Rollback)
- G-4: The INV-002 readiness gate stays in COMP-002 (ADR-0007, trace.yml FR-016 note) — do
  not duplicate the check inside `pdf.py`
- G-5: Collision handling never overwrites an existing file (ADR-0017) — the suffix search
  must be the only outcome, including when the base name is already taken several times over
- G-6: Out of scope — no interactive/playable output; the PDF is a static print artifact
  (CON-002). No embedded solver state or nudge metadata in the image exports
  (trace.yml FR-014 note)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-016
- **NFR:** —
- **INV:** INV-002
- **CON:** CON-002, CON-006
- **ADR:** ADR-0006, ADR-0007, ADR-0016, ADR-0017
- **Components:** COMP-007 (Export Renderers), COMP-002 (readiness gate)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
