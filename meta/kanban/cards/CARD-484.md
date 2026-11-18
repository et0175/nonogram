# CARD-484: The admin hint points at the easiest deduction left, by the solver's own grade

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 2 (IDEA-192, WSJF 1.23); premise re-read against main on 2026-11-19.
**Idea:** IDEA-192
**Wave:** —
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_*.py
**UI surface:** admin solve page (hint ladder)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`hintCell` (`solver_state.js`) returns the first forced cell in **row-major** order, from one pass of `lineForced`, not iterated to a fixed point. So a hint lands on the topmost deduction, not the easiest one. The solver already computes, per cell, which technique settled it (`SolveResult.rung_tags`: `simple_overlap`, `line_dp`, `probe_contradiction`); it is stored on the puzzle (`orchestrator.py`) and never reaches the page. The hint ladder already explains which line to look at and why (CARD-327 onwards), so what remains is the **order**.

## What to implement

Admin solve page only. The grade derives from the solution, so CON-021 / ADR-0038/R6 keep it behind the door. Public mode is untouched.

1. Pass the puzzle's rung grid to the admin solve page.
2. The hint picks the undecided cell with the lowest rung that the current marks force, iterating `lineForced` to a fixed point; it breaks ties in row-major order.
3. Where the rung grid is absent (older puzzles), behave exactly as today.

## Acceptance criteria

* **AC-1**: on a puzzle whose top rows need `line_dp` and a lower row is settled by `simple_overlap`, the first hint highlights the lower row.
* **AC-2**: a puzzle with no stored rung grid gives the same hint sequence as main (pin one).
* **AC-3**: the public player's page and payload are byte-identical to main's (assemble and diff); the grid never appears in public mode.
* **AC-4**: one control per AC-1 (plant row-major order back: it reds). Net test count at most +2.

## Guardrails

* **G-1**: the player test set plus cheap guards is the gate (player-card rule, 2026-11-09).
* **G-2**: the hint ladder's rungs, wording and focus behaviour are unchanged.
* **G-3**: not published until the owner asks.

## Worktree notes

—
