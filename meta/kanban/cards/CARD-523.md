# CARD-523: On narrow phones the board stays put on solve: Show grid takes Line's place

**Status:** in_progress
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/523-show-grid-takes-line
**Worktree:** ../PythonProject4-card-523
**Source:** roadmap wave 12, cut 2026-11-22 on the owner's "let's take your suggestions for first 4 ideas". IDEA-225 (CARD-511 notes and review F-001).
**Idea:** IDEA-225
**Wave:** 91
**Created wave:** 91
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/templates (solver page), tests/test_puzzle_solver_maybe.py
**UI surface:** admin solver page toolbar (solved state, portrait phones)
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-22T13:38Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

After CARD-511, on portrait phones 327-339 px and 421-451 px wide the board still moves down about 25-27 px when a puzzle is solved: once Line hides, Probe plus Show grid need about 96 px, the probe bar's share of the row narrows, and its counters wrap to a row of their own. Owner's ruling 2026-11-22: once solved, Show grid takes Line's place in the toolbar, so the row keeps its width and the board does not move.

## What to implement

Re-verify on main first with the existing solve sweep (tests/test_puzzle_solver_maybe.py's sweep and `test_wraps`, real solves in Chromium): measure the board's dx/dy on solve across portrait widths 320-600 px, and confirm the two bands. Then put Show grid in Line's slot once the puzzle is solved (markup order, CSS, or both: the smallest change that keeps one control per slot), so the solved toolbar fits its row at every width.

The public player has no Show grid (CARD-511's publish record), so the public toolbar must stay as it is; the public site is a build-time copy of these admin files, so check that copy too.

## Acceptance criteria

* **AC-1**: across portrait widths 320-600 px (the sweep's own steps, including 327-339 and 421-451), a real solve moves the board by 0 px in x and y (control: main's code shows the two bands moving).
* **AC-2**: wider and landscape layouts the sweep already covers stay at 0 movement; Show grid and every other solved-state control stays reachable and labelled.
* **AC-3**: the public player's toolbar is unchanged: an assembled site's play page shows the same controls as before, before and after solving.
* **AC-4**: net test count 0; extend the sweep's widths rather than adding a test. Report it.

## Guardrails

* **G-1**: no publish; the owner publishes the player.
* **G-2**: renders for the owner go to ~/Documents/nonogram-reviews/CARD-523/ (before/after at 330 px and 430 px, solved); never into the repo.

## Worktree notes

### Implementation (2026-11-22)

**Premise, re-measured on main before any change.** A scratch probe (copied into tests/ only while it ran, never committed; it asserts `nonogram` resolves to this worktree) used `_solve_and_measure` from tests/test_puzzle_solver_maybe.py on GRID ("Lighthouse") at every portrait width 320-600 px, step 1, height 900 (281 viewports). Board movement on the real solving click: 320-324 none; **325-340 dy +24.797** (dx 0); 341-420 none; **421-451 dy +27.203** (dx 0); 452-600 none. So both bands hold; the first is 325-340, a little wider than the card's 327-339. No sideways page overflow at any width. Outside the bands the controls also reshuffled on solve (at 400 px Check jumped to row 1 once Line left it), without moving the board.

**Premise correction (AC-3).** The public player DOES show Show grid once solved. A base assembly (scripts/assemble_player_site.py, `--bundle` the main checkout's build/player-bundle, no `--analytics`, into /private/tmp/claude-501/card523/site-base) served locally with the `/play/:key` rewrite, puzzles 914fa7acf6 and 22f1a32460 solved for real (solution from `nonogram.solver.solve` on the served clues) at 330x800, 430x900, 600x900, 390x844, 1100x700 and 800x400: unsolved Brush, Region, Undo, Redo, Reset, (Line on compact), Hint, zoom, Probe; solved the same without Line, plus **Show grid** beside Probe. The board moved 0/0 in all 12 cases. The CARD-511 publish record in docs/deploy/player.md lists the unsolved toolbar only; it was not edited here.

**Change.** admin.css, `@media (max-width: 600px) and (orientation: portrait)`, after CARD-511's rule, five rules, all keyed `.player-toolbar.is-solved:has([data-player-action="check"])`, so admin only (CARD-385 removes Check from the public page) and solved only:
- the toolbar keeps CARD-440's 4 px column gap while Show grid is shown;
- `.player-probe { display: contents }`, so Show grid is a toolbar item;
- `order: 1` on Hint, Check, the zoom pill and the probe bar's other children, and `order: 2` on the counters (was 1), so Show grid (order 0) is drawn right after Reset, in Line's slot;
- the toolbar's `::after` stands in for the bar's box: `flex: 1 1 0`, `min-width: 44px`, order 1 (right after Probe), `margin-inline-start: calc(-44px - var(--space-1))`. Without it (measured) the counters took the bar's share of row 2, went from two lines to one at 510-600 px, and the board ROSE 5.594 px. It is empty and 0 px tall (the toolbar aligns flex-start), so it covers nothing; a `pointer-events: none` on it was tried and dropped because no measurement could tell it mattered.
solver.js and the template are untouched. Tab order is unchanged: Show grid's Tab stop stays after Probe (visual order now puts it after Reset on an upright phone only).

**After, same probe, 281 portrait widths 320-600 step 1.** Board movement dx 0, dy 0 at every width. Every visible toolbar control, counters included, has the same box (rounded to 1 px) before and after the solve, except that Show grid appears in exactly Line's box: 0 differing widths out of 281. No sideways overflow.

**AC-3, after.** Same assembly into site-after: only admin.css differs from site-base (`diff -r`), and it is byte-identical to src (`cmp`). The same 12 public cases: control names and boxes (to 0.01 px) identical to base unsolved and solved, board 0/0, all solved, 0 page errors.

**Tests (AC-1, AC-2, AC-4; net 0).** `TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth::test_sweep`: `_SWEEP` gains `(w, 900) for w in range(320, 600, 10)` (28 viewports; 330, 340, 430, 440, 450 lie in the two bands), `checked == len(_SWEEP) == 57` (was 29); and per viewport, new helper `_taps_itself`: "Show grid" and "Probe" each found by role and exact name, visible, and the point at its centre hits it (`unreachable == []`). Docstring says so. No node id changes, so tests/test_browser_fixture_scope.py is untouched. `test_wraps` unchanged. test_sweep took about 80 s here (was about 30 s); step 6 (47 widths) was measured at 108 s and dropped to protect the gate. Collected: 10693 before, 10693 after.

**Controls.**
1. Main's admin.css (`git show HEAD:`): `test_sweep` red, `AssertionError: 330:+0,+24.7969 340:+0,+24.7969 430:+0,+27.2031 440:+0,+27.2031 450:+0,+27.2031`.
2. The `::after` stand-in removed: `test_sweep` red, `AssertionError: 600:-1.42188,-5.59375 510:+0,-5.59375 520:+0,-5.59375 ... 590:+0,-5.59375`.
3. The reachability assert: a stand-in that covers Probe (`align-self: stretch; position: relative; z-index: 1` added to `::after`): `test_sweep` red, `AssertionError: assert [(390, {'Show... False}), ...] == []`, `first extra item: (390, {'Show grid': True, 'Probe': False})`, 30 viewports. (The same mutant without `align-self: stretch` passed: a 0 px tall box covers nothing.)
After each, admin.css copied back and `cmp`-checked; `git diff --stat` shows only the two intended files.

**Renders (G-2).** ~/Documents/nonogram-reviews/CARD-523/before/ and .../after/: admin 330x900 and 430x900, unsolved and solved; public/ under each: both puzzles at the six viewports above, unsolved and solved.

**Gate (unarmed, `-o addopts= -rfs`).** tests/test_puzzle_solver_maybe.py (touched) and neighbours tests/test_puzzle_solver_phone.py, test_puzzle_solver_solved_reveal.py, test_player_base_css.py, test_admin_design_tokens.py, test_player_public_mode.py, test_player_shared_ui_site.py, test_public_player.py, test_browser_fixture_scope.py, test_puzzle_solver_probe.py, test_puzzle_solver_line.py, test_player_viewport_matrix.py: 322 passed, 0 failed, 0 skipped. No DB-armed run: the card names none and nothing touched reaches the database.

**Not established.** Real phones (Chromium headless only). Portrait heights other than 900 and 844 were not swept; the rules do not read the height.

[Review 1/3] Score: 9.0, nothing gating, certified. `test_sweep` 1 passed (80.6 s, 27% of the 300 s guard); control 1 (main's admin.css) red with the five band widths; 12 extra solves at heights 780, 640 and 932 inside both bands all dx 0, dy 0. Public site with HEAD's admin.css: 12 of 12 cases identical to the base build, board 0/0; every solved public toolbar ends "Probe", "Show grid", so the card's premise that the public player has no Show grid was wrong. Chromium's accessibility tree keeps group "Probe" under `display: contents`. Renders: row 1 reads Brush, Region, Undo, Redo, Reset, Show grid, nothing clipped. F-001 (low): Show grid sits in Line's slot but is tabbed last (after Probe); acceptable under WCAG 2.4.3 here, recorded. F-002 (low): admin-only scoping relies on public mode removing Check at runtime (`PUBLIC_ABSENT`); if Check were ever hidden instead of removed, the rules would reach the public toolbar. F-003 (low): the AC-3 note's "site-after's admin.css is byte-identical to src" was taken before the `pointer-events: none` line was dropped; the reviewer's re-run with HEAD's admin.css gives the same result.

**Orchestrator correction (F-003).** AC-3's evidence is the reviewer's re-run with HEAD's admin.css (12 of 12 identical to the base build), not the implementer's site-after copy, which predates the last CSS edit.
