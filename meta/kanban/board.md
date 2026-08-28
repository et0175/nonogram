# Kanban Board

_Updated: 2026-08-28 11:55_

## Wave plan
| Wave | Cards | Status |
|------|-------|--------|
| 1 | CARD-001 P1 | ✓ done |
| 2 | CARD-002 P1, CARD-003 P1 | ✓ done |
| 3 | CARD-004 P1 | ✓ done |
| 4 | CARD-005 P1 | ✓ done |
| 5 | CARD-006 P1, CARD-007 P1 | ✓ done |
| 6 | CARD-008 P2, CARD-009 P1, CARD-011 P2, CARD-012 P1, CARD-013 P1 | ✓ done |
| 7 | CARD-010 P1 | ▶ active |
| 8 | CARD-014 P2 | ⏳ blocked (→ CARD-010) |
| 9 | CARD-015 P2 | ⏳ blocked (→ CARD-014) |
| 10 | CARD-016 P2 | ⏳ blocked (→ CARD-015) |
| 11 | CARD-017 P3 | ⏳ blocked (→ CARD-016) |

_Gantt: [meta/kanban/gantt.md](gantt.md)_

## Backlog
- Support color/multi-value nonograms (not just black/white)
- Interactive/playable puzzle output (web or local UI to solve the puzzle)

## Architecture
_(none)_

## Ready
- **CARD-010** P1 · Difficulty tier selection and resample loop  _(wave 7)_
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
- **CARD-011** Puzzle naming (auto-generated and --name override)
- **CARD-012** PNG and SVG export renderers
- **CARD-013** CSV export and exact round-trip fidelity

## Blocked
_(none)_

## Skipped
_(none)_
