# CARD-484: The admin hint points at the easiest deduction left, by the solver's own grade

**Status:** in_progress
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
**Review score:** —
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

—
