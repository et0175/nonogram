# Wave 34 — 2026-10-06   (tag: wave-34)

_Roadmap wave 1 of the 2026-10-05 re-plan (CARD-177..184) plus the owner's solver test doc items 2 and 4 (CARD-186, CARD-188)._

## Shipped
- CARD-177 (compliance): Finalise and PDF export flash a generic message; the exception text goes to the log only   score 9.0
- CARD-178 (feature): a book stored at 48 cm reopens in inches as 18.89, not 18.90   score 9.5   FR-038
- CARD-179 (feature): the proof note keeps numbers with units and never starts a line with ×   score 9.0   FR-033
- CARD-180 (feature): book selection `?status=all` lists every status   score 9.5   FR-036
- CARD-181 (feature): batches record the tier they asked for (migration 014)   score 9.4   FR-008
- CARD-182 (feature): 24 px player tap targets on phones; wide boards scroll inside the player   score 9.5   FR-044
- CARD-183 (feature): Hint button reveals one line-deducible cell (fallback from the solution), counted and undoable   score 9.0   FR-044 (delta owed)
- CARD-184 (tech-debt): one test holds every interior face to the 10 pt floor; answer key and divider fixed   score 9.5   CON-020
- CARD-186 (feature): "?" mark and Maybe brush; banner takes the tools' place on solve   score 9.0   FR-044 (delta owed)
- CARD-188 (feature): clue numbers circle when the marks settle their run   score 9.0   FR-044 (delta owed)

## Requirements closed
- Goal-backward on main: every card-local AC ✓ (owner render sign-offs 177, 178, 180, 184, 186, 188 recorded as pending by owner choice; 179, 182, 183 accepted)
- Cross-card player checks ✓: "?" reads as undecided for clue circles and hints; the 24 px phone floor holds with the four-tool toolbar
- FR-008, FR-030, FR-031, FR-033, FR-036, FR-038, FR-041..FR-044 tests, CON-005/011/015/016/019/021, invariants ✓

## Convergence
- ⚠ code converged, model NOT: FR-044's statement and AC-304/AC-310/EC-036 contradict the shipped Hint, "?" mark and clue circles; CON-020's check is still review-lens and its trace lacks CARD-184's test; trace.yml not updated for any wave-34 card — follow-up: the /forge:architect session before wave 35 (also CON-021 for CARD-185)
- Wave smoke: full suite on main 6498 passed, 9 skipped, exit 0 (755 s, +27% vs wave 33: new Playwright player tests)

## Known gaps / escalations
- CARD-188 escalated twice (decompose: a protected test vs AC-5 → owner narrowed G-1; implementation: review stalled at 8.0 on a vertical-centring claim → owner-chosen fix found a real 1 px row-ring offset, fixed)
- CARD-182 re-decided: "fit 15×15" measured at 17 px (15×15s already fit on main) → owner chose 24 px with scrolling
- OWNER ACTION: apply migration 014 to nonogram_poc (pg_dump first) and Render before using/deploying — batch pages 500 at 013
- 13 other app.py handlers still flash raw exception text (backlog, CARD-177 OOS)
- Flake watch: TestSolverPageFits[row-clues] returned one server 500 (CARD-183 gate)

## Migrations
- 014_batch_requested_tier (nullable `batches.requested_tier`) — applied to nonogram_test only
