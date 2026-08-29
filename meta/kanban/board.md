# Kanban Board

_Updated: 2026-08-29 10:32_

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
| 11 | CARD-017 P3 | ▶ active |

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
- Nudged image runs alter the picture silently until CARD-017 ships

## Architecture
_(none)_

## Ready
- **CARD-017** P3 · Nudge-count reporting in CLI output  _(wave 11)_
- **CARD-018** P2 · Strengthen solver search to meet AC-037 at 20x20 mid/low density  _(unscheduled — follow-up to CARD-006/AC-037, ADR-0001 revised)_

## In Progress
_(none)_

## Review
_(none)_

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

## Blocked
_(none)_

## Skipped
_(none)_
