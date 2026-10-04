# Wave 32 — 2026-10-04   (tag: wave-32)

_Roadmap wave 1 (meta/kanban/roadmap.md), carded as CARD-164..CARD-168._

## Shipped
- CARD-164 (tech-debt): main goes green — the two tests red since wave 20 were stale (one hollow since it was written)   score 9.5
- CARD-165 (feature): the book page numbers puzzles the way the printed book will   score 9.0   FR-041/FR-043
- CARD-166 (feature): "25×15" in the player, unclipped plan inputs at 390 px, empty ?status= keeps approved-only   score 9.5   FR-044 AC-323
- CARD-167 (feature): the guide page becomes "How to Solve Nonograms" with a one-page worked example   score 9.0   FR-041 AC-324..326
- CARD-168 (ops): render.yaml marked non-authoritative + docs/deploy/render.md; test runner defaults to nonogram_test   score 9.5

## Requirements closed
- FR-044 AC-322/AC-323 ✓, FR-041 AC-324/325/326 ✓, book-page printed numbering matches the PDF bands ✓, book-selection status default ✓ — goal-backward, by memory-mode probe on main 168c6f4
- Requirement deltas this wave: FR-044 AC-323 amended (×); FR-041 gained AC-324..AC-326 (guide page)

## Convergence
- ✅ converged — every target holds on main, UI surfaces present
- The FULL SUITE EXITS 0 on main for the first time since wave 20 (6083 passed); the kanban test-gate baseline is now "no failures"

## Known gaps / escalations
- No escalations; every card closed in 1–2 review cycles
- Owner items: fill docs/deploy/render.md's TODO(owner) rows from the Render dashboard; look at CARD-167's guide page on paper (Book 1 page ends ~55% down; the "3 1" example takes one crossing-column fact); decide ?status=all on book selection (shows nothing)
- To check: the goal-check's PDF recorder saw the highest-tier answer-key band drawn twice ("Puzzle 5 · Hard") — likely a measure-then-draw pass, not a printed duplicate; unconfirmed

## Migrations
- none
