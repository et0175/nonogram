# Kanban Board

_Updated: 2026-09-11 16:35_

## Wave plan
| Wave | Cards | Status |
|------|-------|--------|
| 1 | CARD-001 P1, CARD-019 P1, CARD-022 P1, CARD-023 P1, CARD-024 P1, CARD-025 P2, CARD-045 P1, CARD-046 P2, CARD-047 P2, CARD-048 P3, CARD-049 P1, CARD-050 P1, CARD-051 P2, CARD-054 P3, CARD-055 P3, CARD-058 P3, CARD-059 P3, CARD-060 P3, CARD-061 P2, CARD-062 P2, CARD-063 P3 | ▶ active |
| 2 | CARD-002 P1, CARD-003 P1, CARD-020 P1, CARD-026 P1, CARD-029 P3, CARD-052 P2, CARD-053 P3, CARD-056 P3 | ⏳ blocked (→ wave 1) |
| 3 | CARD-004 P1, CARD-021 P2, CARD-027 P1 | ⏳ blocked (→ wave 2) |
| 4 | CARD-005 P1, CARD-028 P2, CARD-030 P2, CARD-031 P2, CARD-032 P2 | ⏳ blocked (→ wave 3) |
| 5 | CARD-006 P1, CARD-007 P1, CARD-033 P2, CARD-034 P2, CARD-035 P2, CARD-037 P2, CARD-038 P2, CARD-040 P2, CARD-041 P2, CARD-042 P2 | ⏳ blocked (→ wave 4) |
| 6 | CARD-008 P2, CARD-009 P1, CARD-011 P2, CARD-012 P1, CARD-013 P1, CARD-018 P2, CARD-039 P3, CARD-043 P2, CARD-044 P1 | ⏳ blocked (→ wave 5) |
| 7 | CARD-010 P1 | ⏳ blocked (→ wave 6) |
| 8 | CARD-014 P2 | ⏳ blocked (→ wave 7) |
| 9 | CARD-015 P2 | ⏳ blocked (→ wave 8) |
| 10 | CARD-016 P2 | ⏳ blocked (→ wave 9) |
| 11 | CARD-017 P3 | ⏳ blocked (→ wave 10) |

_Note: waves 2-11 are mechanically "blocked" only because wave 1 is not fully done — most of their own cards are individually already `done` (or, for CARD-037/CARD-044, confirmed genuinely still outstanding — see Ready below) with satisfied dependencies. This is an artifact of two unrelated card families (the original CLI/web pipeline build-out, and the newly-added bugfix cards CARD-045..056) sharing wave numbers by coincidence of dependency-depth, not a real blocker._

_Gantt: [meta/kanban/gantt.md](gantt.md)_

## Backlog
_(none — meta/kanban/backlog.md not found)_

## Architecture
_(none)_

## Ready
- **CARD-063** P3 · One source of truth for the grid size range — shared `limits` module instead of hardcoded 10/30  _(wave 1)_ — pure refactor; 40x40 undecided, not in scope
- **CARD-060** P3 · Remove dead code in grid_renderer.py — grid_to_svg_bytes and get_svg_filename  _(wave 1)_
- **CARD-055** P3 · Confine MockGenerator's random metrics to test-only reach  _(wave 1)_
- **CARD-052** P2 · Regression tests for real quality_score/recognizability values  _(wave 2)_
- **CARD-053** P3 · Document or remove the orphaned generation/ and analysis/ packages  _(wave 2)_
- **CARD-056** P3 · Formalize an ADR/invariant for admin puzzle uniqueness and quality metrics  _(wave 2)_
- **CARD-030** P2 · Display inline success/error messages on form page  _(wave 4)_
- **CARD-031** P2 · Show image metadata and suggested puzzle dimensions after upload  _(wave 4)_
- **CARD-032** P2 · Restrict web form to image-only mode  _(wave 4)_
- **CARD-033** P2 · Add output directory selector and improve form styling  _(wave 5)_
- **CARD-034** P2 · Calculate image metadata on file upload (client-side)  _(wave 5)_
- **CARD-037** P2 · Persist uploaded image for retry without re-upload  _(wave 5)_ — not on `main`, but its orphaned worktree holds real uncommitted implementation work; preserved as a patch, see card notes
- **CARD-043** P2 · Clear error/success message when new image is uploaded  _(wave 6)_
- **CARD-044** P1 · Fix image preview with persisted uploads (bridges CARD-037, 042, 043)  _(wave 6)_ — reverted from a false "done" state; genuinely unimplemented on `main`, see card notes

## In Progress
_(none)_

## Review
_(none)_

## Done
- **CARD-062** Admin batch — retry an abandoned picture at long side ±1 before giving up · score 9.5 (cycle 2/3) · merged 696871d
- **CARD-061** Admin "small" preset — 10 is the short side, the long side follows the picture (+ large preset 30) · score 9.0 (cycle 2/3) · merged 3cf8517
- **CARD-058** Surface a note when admin silently substitutes the predicted puzzle size · score 8.5 (cycle 1/3) · merged 6f87e3c
- **CARD-059** Remove the unreachable, unverified SVG-preview-by-file_id routes · score 9.5 (cycle 1/3) · merged 47ca753
- **CARD-057** ADR-0006/R1's dependency baseline is stale — reportlab was added without updating it · score 9.0 (cycle 1/3) · merged 94c5a8d
- **CARD-054** Remove dead code — BatchGenerator._generate_puzzle_with_metrics · score 9.5 (cycle 1/3) · merged 77c450f
- **CARD-048** Widen ADR-0022/R3 and R4 scope.code to include the admin panel · score 9.5 (cycle 2/3) · merged b154886
- **CARD-047** predict_size() adds a synchronous full-image decode to batch page renders · score 9.0 (cycle 1/3) · merged 8e5b818
- **CARD-046** Regression test for ink-bbox-vs-file-dimensions sizing fix · score 9.5 (cycle 1/3) · merged 261706a
- **CARD-051** Stop reimplementing clue encoding in admin — call nonogram.clues · score 9.5 (cycle 1/3) · merged 352670f
- **CARD-050** quality_score and recognizability are hardcoded fakes, not measurements · score 9.0 (cycle 3/3) · merged 62f8c62
- **CARD-049** Route admin image-mode generation through the solver-verified pipeline · score 9.0 (cycle 1/3) · merged 98cdaaa
- **CARD-045** predict_size() can crash a whole batch page on a degenerate image · score 9.0 (cycle 1/3) · merged 2fc8094
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
- **CARD-020** Web UI generation submission — form to pipeline to result page
- **CARD-021** Image upload via hand-rolled multipart parsing
- **CARD-022** Repair the web adapter's false claims and vacuous guards
- **CARD-023** Narrow the supported grid range to 10..30 project-wide, with a measured 30x30 deadline fixture
- **CARD-024** Export metadata carries width and height at schema version 2
- **CARD-025** Printed cell size becomes min(comfort cap, page fit)
- **CARD-026** Fit uploaded images to the requested grid shape, refusing a >2x aspect mismatch
- **CARD-027** Grid extent as a (width, height) pair through the request, `--size NxM`, and all three source modes
- **CARD-028** Web form's size field accepts the `NxM` extent token
- **CARD-029** Retire the last stale 10..50 range claims left by CON-011
- **CARD-035** Include source image filename in export (traceability)
- **CARD-038** Clear previous result message when submitting new generation ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-039** Clear size field when new image is uploaded ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-040** Implement suggestion algorithm (metadata.py module) ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-041** Add colored backgrounds to result messages (success/error visual distinction) ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-042** Display image preview after upload ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes

## Repository integrity note

`main` and the `card/037-044` worktree branches share **no common git
ancestor** (two disjoint root commits: `main` → `fb2ec7f`, the old chain →
`b7d14ca`). `96da6ac "feat: restore core nonogram modules and silhouette
images"` (2026-09-08) is a file-level restore from a backup onto `main`, not a
git merge — it is why `main` independently has equivalent functionality for
5 of these 7 cards despite no shared history.

**2026-09-11 — worktree cleanup, on confirmation:** `../PythonProject4-CARD-038`,
`-039`, `-041`, `-044` removed (`git worktree remove`, all clean, no uncommitted
changes). `../PythonProject4-CARD-037` removal was **correctly refused by git**
— it holds real, never-committed CARD-037 implementation work, preserved as a
patch (see CARD-037's own Worktree notes) before deciding what to do with it.
`../PythonProject4-CARD-040` and `../PythonProject4-CARD-042` also removed
(confirmed clean immediately before removal). The only worktree remaining
outside the main repo is `../PythonProject4-CARD-037`, kept deliberately —
it holds the uncommitted CARD-037 implementation work (see that card's notes).

Branch objects (`card/038-...` etc.) were not deleted — `git worktree remove`
only removes the working-tree checkout, not the branch ref itself.
