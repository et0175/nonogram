# Kanban Board

_Updated: 2026-08-27 17:51_

## Wave plan
| Wave | Cards | Status |
|------|-------|--------|
| 1 | CARD-001 P1 | ▶ active |
| 2 | CARD-002 P1, CARD-003 P1 | ⏳ blocked (→ CARD-001) |
| 3 | CARD-004 P1 | ⏳ blocked (→ CARD-002) |
| 4 | CARD-005 P1 | ⏳ blocked (→ CARD-003, CARD-004) |
| 5 | CARD-006 P1, CARD-007 P1 | ⏳ blocked (→ CARD-004, CARD-005) |
| 6 | CARD-009 P1, CARD-012 P1, CARD-013 P1, CARD-008 P2, CARD-011 P2 | ⏳ blocked (→ CARD-006, CARD-007) |
| 7 | CARD-010 P1 | ⏳ blocked (→ CARD-009, CARD-011) |
| 8 | CARD-014 P2 | ⏳ blocked (→ CARD-010, CARD-012, CARD-013) |
| 9 | CARD-015 P2 | ⏳ blocked (→ CARD-008, CARD-014) |
| 10 | CARD-016 P2 | ⏳ blocked (→ CARD-015) |
| 11 | CARD-017 P3 | ⏳ blocked (→ CARD-016) |

_Wave checkpoints: [meta/kanban/waves.yml](waves.yml) — increment 1 closes at wave 5,
increment 2 at wave 8, increment 3 at wave 11._

_Gantt: [meta/kanban/gantt.md](gantt.md)_

## Backlog
- Support color/multi-value nonograms (not just black/white)
- Interactive/playable puzzle output (web or local UI to solve the puzzle)

## Architecture
_(none — 18 ADRs accepted, 0 open decisions; handoff absorbed)_

## Ready
- **CARD-001** P1 · Package scaffolding and CLI entry point  _(wave 1)_
- **CARD-002** P1 · Clue derivation via run-length encoding  _(wave 2)_
- **CARD-003** P1 · Random grid sourcing with size and density validation  _(wave 2)_
- **CARD-004** P1 · Nonogram solver with fail-fast uniqueness check  _(wave 3)_
- **CARD-005** P1 · Pipeline orchestrator and regenerate-on-failure loop  _(wave 4)_
- **CARD-006** P1 · Cooperative generation deadline and SolverTimeout  _(wave 5)_
- **CARD-007** P1 · JSON export and the export-readiness gate  _(wave 5)_
- **CARD-008** P2 · Built-in image library sourcing  _(wave 6)_
- **CARD-009** P1 · Difficulty scoring formula from solver signals  _(wave 6)_
- **CARD-010** P1 · Difficulty tier selection and resample loop  _(wave 7)_
- **CARD-011** P2 · Puzzle naming (auto-generated and --name override)  _(wave 6)_
- **CARD-012** P1 · PNG and SVG export renderers  _(wave 6)_
- **CARD-013** P1 · CSV export and exact round-trip fidelity  _(wave 6)_
- **CARD-014** P2 · Two-page PDF export with answer key  _(wave 8)_
- **CARD-015** P2 · Uploaded-image conversion via resize and Floyd-Steinberg dithering  _(wave 9)_
- **CARD-016** P2 · Bounded pixel-nudge recovery loop for image mode  _(wave 10)_
- **CARD-017** P3 · Nudge-count reporting in CLI output  _(wave 11)_

## In Progress
_(none)_

## Review
_(none)_

## Done
_(none)_
