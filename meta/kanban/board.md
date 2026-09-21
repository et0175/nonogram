# Kanban Board

_Updated: 2026-09-17 UTC_

## Wave plan
| Wave | Cards | Status |
|------|-------|--------|
| 1 | CARD-080 P1, CARD-001 P1, CARD-019 P1, CARD-022 P1, CARD-023 P1, CARD-024 P1, CARD-025 P2, CARD-045 P1, CARD-046 P2, CARD-047 P2, CARD-048 P3, CARD-049 P1, CARD-050 P1, CARD-051 P2, CARD-054 P3, CARD-055 P3, CARD-058 P3, CARD-059 P3, CARD-060 P3, CARD-061 P2, CARD-062 P2, CARD-063 P3, CARD-064 P2, CARD-065 P3, CARD-066 P3, CARD-067 P2, CARD-068 P2, CARD-069 P2, CARD-070 P2, CARD-071 P3, CARD-072 P2, CARD-073 P1, CARD-074 P1, CARD-075 P2, CARD-076 P1, CARD-077 P2, CARD-078 P3, CARD-079 P2, CARD-084 P3, CARD-085 P1, CARD-086 P2, CARD-087 P2, CARD-088 P1, CARD-089 P2, CARD-090 P2, CARD-091 P2, CARD-092 P3, CARD-093 P3, CARD-094 P3, CARD-095 P3, CARD-096 P2 | ▶ active |
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
- **CARD-060** P3 · Remove dead code in grid_renderer.py — grid_to_svg_bytes and get_svg_filename  _(wave 1)_
- **CARD-055** P3 · Confine MockGenerator's random metrics to test-only reach  _(wave 1)_
- **CARD-071** P3 · Architecture and docs hygiene — land the requirements registry on main, fix dangling references  _(wave 1)_ — also carries CARD-074's open findings F-001/F-002
- **CARD-078** P3 · Refuse density 0 and 100 — valid range 1..99  _(wave 1)_
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
- **CARD-101** P1 · The book's JSON columns are mutation-tracked — "move up", "move down" and every title after a book's first were silently discarded in DB mode; the page count too · fixed in three column declarations, no call site changed · measured before and after through fresh sessions · one mutant survived and is reported, not papered over · merged without a review cycle, at the owner's call · merged 3bc8fa6
- **CARD-100** P1 · A puzzle in a book is protected again — membership written to both `Book.puzzle_ids` and `Puzzle.book_id` in one gesture; the three per-puzzle status changes became one rule, so a booked puzzle cannot even be rejected · the book builder stops offering a puzzle another book holds · backfill ships with a dry run, owner runs it (G-2) · `remove_puzzle_from_book` did nothing in DB mode and is fixed — the four with the same bug are CARD-101 · merged without a review cycle, at the owner's call · merged 0360c05
- **CARD-068** P2 · Batch results — the per-puzzle Delete (rejected only, option (a)), confirmations that name their count, and reports that say what needed nothing · re-cut first: `db4e0dc` had shipped the three bulk actions outside the board, and AC-2's >100 clause was retired (MAX_BATCH_COUNT is 50) · the in-book clause left unbuilt and the sidebar's untrue reassurance removed — see CARD-100 · verified on the rendered page · merged without a review cycle, at the owner's call · merged 3223753
- **CARD-099** P2 · The generated page counts pictures and puzzles separately, and a picture's sizes read as a group — heading per picture (option (a), owner's pick) · fixes a count CARD-069 broke ("2 puzzles from 2 pictures" for one picture) · the shortfall no longer blames the quality threshold · verified on the rendered page · merged without a review cycle, at the owner's call · merged 2ac201a
- **CARD-069** P2 · Up to four size options per picture, one puzzle per size — the last of the 2026-09-12 admin review items · every pre-existing single-size test passed untouched · merged without a review cycle, at the owner's call · merged 19564e5
- **CARD-067** P2 · Preview cards — picture left, ink ratio right, remove a picture · re-cut 2026-09-19: the live-prediction half had shipped on main meanwhile, so the stale branch is retired as `card/067-superseded-2026-09-12` and the rest was rebuilt · verified on the rendered admin · merged without a review cycle, at the owner's call · merged 9c97d88
- **CARD-098** P2 · The Guess tier retired — three score bands, branching reported as the `guess` strategy; ADR-0031 supersedes ADR-0025 · never assigned in ~7,400 measured puzzles · one of the two standing suite failures deleted with it · merged without a review cycle, at the owner's call · merged 0df8d63
- **CARD-097** P2 · A database that never answers no longer stops the suite — connect deadline, reachability probed once a session, faulthandler net dumping to a file · with Postgres listening: never finished → 2 m 08 s · merged without a review cycle, at the owner's call · merged a073d5c
- **CARD-072** P2 · A puzzle records the strategies its solve needed — carried to the JSON export (with CARD-079's deferred `binarisation`, no schema bump) and filterable in the admin list · merged without a review cycle, at the owner's call · merged 50996b6
- **CARD-079** P2 · Silhouettes thresholded, photographs dithered, blank conversions guarded — owner's visual gate discharged, ADR-0026 Accepted; shipped vs dither over 125 conversions: 110 vs 109 made, 91 vs 80 unique first time, 39 vs 53 nudges, 0 regressions · merged without a review cycle, at the owner's call · merged 97dc287
- **CARD-075** P2 · Image-mode nudge adds one cell per attempt from where the solver's witnesses disagree — 107 of 125 corpus conversions made against 89, 0 regressions; admin loss 3/5/7/7 → 2/2/3/3 · AC-172 closed at 18 of 19, owner kept the ink-boundary ranking · merged without a review cycle, at the owner's call · merged bb35762
- **CARD-096** P2 · Image-mode abandonment measured by cause — admin loses 3-7 of 25 per preset; witnesses disagree on 4 cells in 27 of 34; CARD-075 revised from it · a measurement, merged at the owner's call · merged ade79e8
- **CARD-095** P3 · An image batch stops on its own clock, as a random batch does — checked before every generate call, unstarted pictures stay loaded · merged without a review cycle, at the owner's call · merged d50bce7
- **CARD-094** P3 · Nothing still says 20 attempts or 200 puzzles where it means the live bound; the image preview reads the real ceiling · merged without a review cycle, at the owner's call · merged 949471a
- **CARD-093** P3 · A random batch that stops early keeps the puzzles it made — stored as made, COMPLETE with a note · merged without a review cycle, at the owner's call · merged 3a7f309
- **CARD-092** P3 · The generation algorithm reference describes the loop the code runs — §8 repair, §9 batches, findings re-established, symbol references checked by script · merged without a review cycle, at the owner's call · merged 50ba053
- **CARD-091** P2 · K recalibrated from 3 to 5 — measured (30x30 95% → 99%, wall clock 329 s → 226 s) · merged without a review cycle, at the owner's call · merged b27435c
- **CARD-090** P2 · The retry bound moves to 30 — measured at the knee of the curve (85% → 95% at 30x30) · merged without a review cycle, at the owner's call · merged 5d4bc3a
- **CARD-089** P2 · The retry bound measured, and left at 20 · closed as a measurement, no code change · merged d575708
- **CARD-088** P1 · A batch stops on its own clock, not on the worker's · merged without a review cycle, at the owner's call · merged 55d83a5
- **CARD-087** P2 · The synthetic image fixtures are what their tests say they are · merged without a review cycle, at the owner's call · merged 964b3c7
- **CARD-084** P3 · Drop the legacy difficulty columns — the snapshots replaced them · merged without a review cycle, at the owner's call · merged 20e9203
- **CARD-086** P2 · Serve the deployed admin with gunicorn, bound its slowest route, and say why a request was refused · merged without a review cycle, at the owner's call · merged f381d62
- **CARD-085** P1 · The admin panel can be reached from somewhere other than this machine, but only with a credential · score 9.0 (cycle 2/2) · merged 84fcc46
- **CARD-083** P2 · A batch survives a candidate it had to abandon · score 8.0 (cycle 1/1) · merged d3db715
- **CARD-082** P2 · The suite baseline says what it means — three standing failures and one 40% flake · score 9.0 (cycle 1/1) · merged a13c9bf
- **CARD-070** P2 · Generation quick fixes — batch tier spelling, stale nudge pins, docstring drift · score 9.0 (cycle 1/1) · merged 4362a7e
- **CARD-080** P1 · No write path can store a puzzle that is not uniquely solvable · score 8.5 (cycle 2/2) · merged b40e6b1
- **CARD-077** P2 · Re-grade the admin DB under the ladder scale — admin action, backup first, legacy columns kept · score 8.5 (cycle 2/2) · merged 3de767f
- **CARD-081** P1 · The admin panel binds loopback like the web UI does, and a test says so · merged without a review cycle, at the owner's call · merged 44a5af4
- **CARD-076** P1 · Difficulty by strategy ladder and the Guess tier — no clock, no size, one classifier · score 9.0 (cycle 2/2) · merged 76c1df4
- **CARD-074** P1 · Repair before redraw — flip one filled/empty pair inside the disagreement set, K=3 per lineage, one shared bound · merged aa6d863 · review 8.5
- **CARD-073** Solver exposes the undecided mask, a second witness on MANY, and the rung that settled each cell · score 9.0 (cycle 2/2) · merged ab851eb
- **CARD-066** Filter the puzzle review by status (draft / approved / rejected / in book) · score 9.5 (cycle 3/3) · merged d07f2a2
- **CARD-065** Small follow-ups from CARD-061..064 — honest percentages, preset labels, stale tests · score 9.5 (cycle 2/3) · merged 18a2287
- **CARD-064** Thin pictures — move up to Large instead of cropping, or say it can't be done · score 9.0 (cycle 2/3) · merged be582ea
- **CARD-063** One source of truth for the grid size range — shared `limits` module · score 9.0 (cycle 2/3) · merged 0a77655
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
