# Kanban Board

_Updated: 2026-09-03 11:15_

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
| 14 | CARD-020 ✓ done | ✓ done |
| 15 | CARD-021 P2 | ⏸ ready — CARD-020 done |
| 16 | CARD-023 ✓ done · CARD-025 ✓ done · CARD-024 ✓ done | ✓ done |
| 17 | CARD-026 P1 | ✓ done |
| 18 | CARD-027 ✓ done | ✓ done |
| 19 | CARD-028 ✓ done, CARD-030 ✓ done, CARD-031 ✓ done, CARD-032 ✓ done | ✓ done |
| 20 | CARD-033 ✓ done, CARD-034 ✓ done | ✓ done |
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
- **Two mechanical checks for the docstring-truth family** — dead test-name arrows, live citation of a retired id (with the exclusions both need)
- **Random mode can't make a large rectangle at mid density** — 30x20 abandons at every density 10..45; CON-011 promises what the generator can't deliver
- **CARD-027 deferred:** the ADR-0022/R1 guard is defeated by a type alias or `NewType` (both pinned as declared gaps)

## Architecture
_(none)_

## Ready
- **CARD-021** P2 · Image upload via hand-rolled multipart parsing  _(wave 14/15 — UNBLOCKED, CARD-020 done)_
- **CARD-029** P3 · Retire the last stale 10..50 range claims left by CON-011  _(no wave — READY, CARD-023/025 done)_

## Done
- **CARD-028** Web form's size field accepts the `NxM` extent token
- **CARD-020** Web UI generation submission — form to pipeline to result page, plus the cross-origin refusal (NFR-004/CON-010)
- **CARD-033** A bare `--size N` derives the shorter side from the source's shape
- **CARD-031** Image-mode puzzles auto-name from the source file's stem
- **CARD-030** Trim an uploaded picture to its ink bounding box, and move the aspect guard onto it
- **CARD-027** Grid extent as a (width, height) pair through the request, `--size NxM`, and all three source modes
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
- **CARD-032** Ship a Unicode TTF as package data so a non-ASCII name prints in the PDF header
- **CARD-034** The page turns whichever way prints the larger cell; NFR-005/EC-008 corrected
- **CARD-024** Export metadata carries width and height at schema version 2
