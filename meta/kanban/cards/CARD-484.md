# CARD-484: The admin hint points at the easiest deduction left, by the solver's own grade

**Status:** review
**Priority:** P3
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/484-hint-easiest-first
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-484
**Source:** roadmap rescore 2026-11-18, wave 2 (IDEA-192, WSJF 1.23); premise re-read against main on 2026-11-19.
**Idea:** IDEA-192
**Wave:** 81
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_*.py
**UI surface:** admin solve page (hint ladder)
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-19T11:55Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`hintCell` (`solver_state.js`) returns the first forced cell in **row-major** order, from one pass of `lineForced`, not iterated to a fixed point. So a hint lands on the topmost deduction, not the easiest one. The solver already computes, per cell, which technique settled it (`SolveResult.rung_tags`: `simple_overlap`, `line_dp`, `probe_contradiction`); it is set on the in-memory puzzle at generation (`orchestrator.py`) but **never persisted** — the database keeps only the strategies list — so it never reaches the page. (Premise corrected 2026-11-19 at start: the card first said "stored on the puzzle".) The hint ladder already explains which line to look at and why (CARD-327 onwards), so what remains is the **order**.

## What to implement

Admin solve page only. The grade derives from the solution, so CON-021 / ADR-0038/R6 keep it behind the door. Public mode is untouched.

1. **Owner's decision 2026-11-19: solve on page open.** The admin solve route runs the solver once on the puzzle's clues, under a bounded deadline, and passes the resulting rung grid to the page. No schema change, no migration.
2. Among the undecided cells today's single `lineForced` pass forces from the current marks, the hint picks the one with the lowest rung; ties go row-major. (Amended 2026-11-19 after review cycle 1: not a fixed point, because `hintLine` needs the cell forced by one line, G-2.)
3. Where no rung grid is available (the solve timed out or failed), behave exactly as today; the page still opens.

## Acceptance criteria

* **AC-1**: on a puzzle whose top rows need `line_dp` and a lower row is settled by `simple_overlap`, the first hint highlights the lower row.
* **AC-2**: when the grid is unavailable (solve timed out), the page opens and gives the same hint sequence as main (pin one).
* **AC-3**: the public player's page and payload are byte-identical to main's (assemble and diff); the grid never appears in public mode.
* **AC-4**: one control per AC-1 (plant row-major order back: it reds). Net test count at most +2.

## Guardrails

* **G-1**: the player test set plus cheap guards is the gate (player-card rule, 2026-11-09).
* **G-2**: the hint ladder's rungs, wording and focus behaviour are unchanged.
* **G-3**: not published until the owner asks.
* **G-4**: the page-open solve is bounded: a deadline short enough that the page never waits on a hard puzzle for more than about 2 s.

## Worktree notes

**What changed (code commit "CARD-484: the admin hint reveals the easiest forced cell first").**
- `puzzle_review.hint_rungs(grid)`: one `solve()` of the grid's clues under `HINT_GRADE_DEADLINE_SECONDS = 1.5`; returns each cell's index in `RUNG_ORDER` (None for an untagged cell), or None on `SolverTimeout` (logged at info) or a non-unique clue set.
- `puzzle_solve` (app.py) passes it to the template as `hint_rungs`. `puzzle_solve.html` renders `<script type="application/json" id="puzzle-player-rungs">` only when it is truthy. The six-key payload is unchanged, so the editor page and the public page carry no grade.
- `solver.js` `readRungs` reads that element (no element, or one of the wrong shape, gives null). The one `hintCell` call passes it as a fifth argument. No new reads of `editing` or `publicMode`, so the read counts in the header contract stand.
- `hintCell(..., ranks = null)`: among the cells today's single pass forces, it picks the lowest rank. Null ranks come after every number, and ties go row-major. With no ranks, or with `solution === null`, it returns exactly as before.

**Decision: single pass, not a fixed point.** If `lineForced` were iterated to a fixed point, the hint could pick a cell that no single line forces from the current knowns. `hintLine` would then throw its "(c) drifted" RangeError, or rungs 1-2 would point at a line that does not decide the cell (G-2). So the forced set stays today's single pass and only the order among those cells changes. The pick is always forced by its own row or column, so `hintLine` finds it. The card's text says "iterating `lineForced` to a fixed point"; this note supersedes that, as the brief asked.

**ADR check.** ADR-0029/R2 ("never by re-solving") is scoped to solver/, difficulty.py and orchestrator.py. It governs the stored grade and strategies list. This solve stores nothing and grades nothing, and `admin/regrade.py` already re-solves in the admin package. The tags are a pure function of the clue set (ADR-0029/R3, R5). I judged that this does not forbid the owner's decision, but that is a judgement, not a test. CON-021 / ADR-0038/R6: the grade derives from the solution and never reaches the public page (AC-3 below).

**AC evidence.**
- AC-1: `TestSolverHint_EasiestFirst::test_the_first_hint_is_the_easiest`. A 10x10 board with rows 0-3's simple_overlap cells marked. From the solver's tags, row-major would pick line_dp cell (3,4); the graded page highlights row 4 only and reveals simple_overlap cell (4,6).
- AC-2: `TestSolverHint_EasiestFirst::test_a_timed_out_grade_hints_as_main_did`. The deadline is monkeypatched to -1.0, so the route's solve raises SolverTimeout. The page opens with no `#puzzle-player-rungs`, and three reveals follow the row-major oracle. Pinned: the first reveal is (3,4). At module level, `test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell` still makes main's four-argument call on the unchanged corpus.
- Extended existing tests (no new count): the property test gained a graded arm with random ranks per shape against a sort-based oracle, and asserts `reordered >= 100`. `TestSolverHintModule::test_cases` gained ungraded, graded, null-last and public-ignores-grade cases. The page oracle `_grid_hint` now passes GRID's real grade.
- AC-4 control, mutant 1: `const graded = false;` in hintCell (row-major planted back). That reds `test_the_first_hint_is_the_easiest` (highlighted rows {3}, not {4}), the property test and `TestSolverHintModule::test_cases`. The timeout test stays green, as it should.
- AC-4 control, mutant 2: drop `rungs` from solver.js's hintCell call. That reds `test_the_first_hint_is_the_easiest`. Both mutants were reverted.
- AC-3: I assembled the site from one bundle (`write_bundle` from tests/test_public_player.py) on base c9244284 (`git archive`) and on this branch, each with its own `scripts/assemble_player_site.py --bundle B --out S`, then ran `diff -rq`. 22 files each side; all 11 html/json files (pages and payloads) are identical. Only `solver.js` and `solver_state.js` differ, because they are byte copies of the admin files by design. `puzzle-player-rungs` appears only in the copied solver.js reader code, never in a page.

**Cost (G-4).** Random 30x30 grids that time out under a 1.5 s deadline stopped at 1.502 s (two of 40 draws, seed 484; those were non-unique and cannot be stored). The hardest unique 30x30 I found took 0.21 s to solve (seed 4841). The route on that grid took 0.21-0.57 s per page open through the Flask test client.

**Gate.** Player set + cheap guards, 39 files (`-o addopts= -rfs`): 3 failed / 1962 passed / 0 skipped. Two of the failures were pins I then fixed and reran: 112 passed in tests/test_browser_fixture_scope.py + tests/test_player_public_mode.py. The fixes were the two new node ids added to `ADDED_SINCE_BEFORE`, and `_NEXTHINT_READ` updated to the new call line. The third, `tests/test_book_landing_page.py::test_the_way_back_from_a_puzzle_keeps_the_sections_and_the_place` (scrollY 145 vs 220), reds identically on base c9244284. It predates this card and is untouched by it.

**Net test count.** By `--collect-only -o addopts=`: tests/ 10698 on base, 10700 on the branch (+2). test_puzzle_solver_hint.py 60 to 62.

[Review 1/3] Score: 9.0, nothing gating, certified. Mutants M1-M7 each red a named test (row-major planted back, rank argument dropped, grade returning None, timeout uncaught, tie order flipped, grade honoured in public mode, null ranks sorted first); public fragment and play page sha256-identical to main; 330 passed, 0 skipped over the changed files plus test_cli and test_timeout. Low findings fixed inline by the orchestrator: F-1 a lost space in solver.js `start`; F-2 `hint_rungs` now degrades on any solve failure, not only a timeout (card item 3); F-3 the timeout log names the page-open deadline instead of quoting the generation-deadline message, and a non-unique clue set logs a warning; F-4 card item 2 amended to the single pass; F-5 `test_no_served_file_contains_a_solution_string` now also refuses any served page carrying `id="puzzle-player-rungs"` (a template mutant rendering it unconditionally reds it: `['index.html'] == []`). No test added.
