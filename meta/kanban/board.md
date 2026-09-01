# Kanban Board

_Updated: 2026-09-01 16:10_

<!-- forge:wave wave=12 start=2026-08-30 -->


## Wave plan
| Wave | Cards | Status |
|------|-------|--------|
| 1 | CARD-001 P1 | ✓ done |
| 2 | CARD-002 P1, CARD-003 P1 | ✓ done |
| 3 | CARD-004 P1 | ✓ done |
| 4 | CARD-005 P1 | ✓ done |
| 5 | CARD-006 P1, CARD-007 P1 | ✓ done |
| 6 | CARD-008 P2, CARD-009 P1, CARD-011 P2, CARD-012 P1, CARD-013 P1 | ✓ done |
| 7 | CARD-010 P1 | ✓ done |
| 8 | CARD-014 P2 | ✓ done |
| 9 | CARD-015 P2 | ✓ done |
| 10 | CARD-016 P2 | ✓ done |
| 11 | CARD-017 P3 | ✓ done |
| 12 | CARD-019 P1 | ✓ done |
| 13 | CARD-022 P1 | ✓ done |
| 14 | CARD-020 P1 | ⏸ ready |
| 15 | CARD-021 P2 | ⏳ blocked (→ CARD-020) |
| 16 | CARD-023 ✓ done · CARD-025 ✓ done · CARD-024 P1 | ▶ active (CARD-024 in progress) |
| 17 | CARD-026 P1 | ✓ done |
| 18 | CARD-027 P1 ⚠ | ⏳ blocked (→ CARD-024) · revision pending — gated |
| 19 | CARD-028 P2, CARD-030 P1, CARD-031 P2, CARD-032 P2 | ⏳ blocked (→ CARD-020, CARD-027) · CARD-032 has no deps |
| — | CARD-018 ✓ done · CARD-029 P3 | ⏸ ready (CARD-023/025 both done) |

_Increment 5 starts at wave 16, not 15: this table renumbered increment 4 when CARD-022
was inserted at wave 13, while `waves.yml` and the CARD-020/021 files still read 13/14.
Wave 15 is left unused so the new cards collide under neither numbering._

_Gantt: [meta/kanban/gantt.md](gantt.md)_

## Backlog
- Support color/multi-value nonograms (not just black/white)
- Interactive/playable puzzle output (web or local UI to solve the puzzle)
- Retune difficulty score weights/cutoffs (ADR-0005/ADR-0013) — Hard tier unreachable
- Decision needed: non-ASCII `--name` renders as tofu boxes in the PDF header
- Vacuous PNG gutter-ink test (`test_the_png_contains_the_clues`)
- Stale README Status section
- PDF pages embed lossy JPEG raster
- Export metadata doesn't record `--image` path or `--library-key`
- Image mode can spend up to 6 solves against the shared deadline instead of 1
- AC-040 test pins only a substring, not the full disclosure sentence
- In-browser preview of the generated puzzle in the web UI
- Progress/status feedback in the web UI for long-running generations
- Browse/list previously generated puzzles from the web UI
- `test_the_form_lists_every_registered_export_format` is a weak/vacuous web test
- Measure or permanently retire CARD-019's withdrawn shutdown bound
- Three inaccurate prose claims in `src/nonogram/web/handler.py`
- **Measure how close the finished puzzle is to the source picture** — nothing does today
- **Elaborate difficulty measurement** — 12 analyzer intake lines written 2026-08-30, never formalized
- **40x40 advanced mode — image/library only** — random already times out at 25-30
- **NFR-005's max(w,h) model breaks on rectangles** — 40x20 vs 20x40 differ 45%; trap in CARD-027's path

## Architecture
_(none)_

## Ready
- **CARD-020** P1 · Web UI generation submission — form to pipeline to result page  _(wave 14)_
- **CARD-021** P2 · Image upload via hand-rolled multipart parsing  _(wave 15, after CARD-020)_
- **CARD-027** P1 · Grid extent as a (width, height) pair through the request, `--size NxM`, and all three source modes ⚠ ← revision pending  _(wave 18 — GATED: `--size N` semantics being changed before it is built)_
- **CARD-028** P2 · Web form's size field accepts the `NxM` extent token  _(wave 19, after CARD-020/027)_
- **CARD-029** P3 · Retire the last stale 10..50 range claims left by CON-011  _(unblocked — CARD-023/025 done)_
- **CARD-030** P1 · Trim an uploaded picture to its ink bounding box, and move the aspect guard onto it  _(wave 19, after CARD-027)_
- **CARD-031** P2 · Image-mode puzzles auto-name from the source file's stem  _(wave 19, after CARD-027)_
- **CARD-032** P2 · Ship a Unicode TTF as package data so a non-ASCII name prints in the PDF header  _(wave 19, no dependencies — runnable now)_

## In Progress
- **CARD-024** Export metadata carries width and height at schema version 2
  `worktree: ../PythonProject4-card-024` · `branch: card/024-export-extent-schema-v2`
  `elapsed: 1.2d / 1d est`

## Done
- **CARD-001** Package scaffolding and CLI entry point
- **CARD-002** Clue derivation via run-length encoding
- **CARD-003** Random grid sourcing with size and density validation
- **CARD-004** Nonogram solver with fail-fast uniqueness check
- **CARD-005** Pipeline orchestrator and regenerate-on-failure loop
- **CARD-006** Cooperative generation deadline and SolverTimeout
- **CARD-007** JSON export and the export-readiness gate
- **CARD-008** Built-in image library sourcing
- **CARD-009** Difficulty scoring formula from solver signals
- **CARD-010** Difficulty tier selection and resample loop
- **CARD-011** Puzzle naming (auto-generated and --name override)
- **CARD-012** PNG and SVG export renderers
- **CARD-013** CSV export and exact round-trip fidelity
- **CARD-014** Two-page PDF export with answer key
- **CARD-015** Uploaded-image conversion via resize and Floyd-Steinberg dithering
- **CARD-016** Bounded pixel-nudge recovery loop for image mode
- **CARD-017** Nudge-count reporting in CLI output
- **CARD-018** Strengthen solver search to meet AC-037 at 20x20 mid/low density
- **CARD-019** Web UI server skeleton, `nonogram serve`, and the adapter import allowlist
- **CARD-022** Repair the web adapter's false claims and vacuous guards
- **CARD-023** Narrow the supported grid range to 10..30 project-wide, with a measured 30x30 deadline fixture
- **CARD-025** Printed cell size becomes min(comfort cap, page fit)
- **CARD-026** Fit uploaded images to the requested grid shape, refusing a >2x aspect mismatch  ⚠ follow-up → CARD-030 (ADR-0022 revised)
