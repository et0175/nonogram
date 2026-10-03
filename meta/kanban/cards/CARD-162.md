# CARD-162: The solver counts errors and celebrates a solved puzzle

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** owner design doc "Nonograms - Print layout" (Google Doc 1pJKF2qX6mC9qw4Cf9Nv3hblTDmtoHwP5Tb8wzK1_WqM), section "Online solver"
**Idea:** —
**Wave:** 31
**Depends on:** CARD-161
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_progress.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** architect delta — same as CARD-160 (CON-002 amendment, solver FR, client/testing ADR), plus CARD-161

## What to implement

The document's top bar: "the number of errors and hint button (or we can go
without hints for now)", plus "some animation when the puzzle is solved".
**Hints are left out** of this card, as the document allows; they're on
the backlog.

1. **Error count** at the top of the page, compared against the solution
   CARD-160 put in the page.
   **Definition, check it with the owner:** an error is a cell currently
   marked black where the solution is white, or marked white where the
   solution is black. Undecided cells are never errors. The count is live,
   so it goes back down when a mistake is undone or corrected. The other
   common reading counts every wrong mark ever made, a running total that
   never decreases. Pick the live count unless the owner says otherwise,
   and note it.
2. **Solved state:** the puzzle is solved when every solution-black cell is
   marked black and no solution-white cell is marked black. White marks are
   optional, as on paper. On solve:
   - show the picture's name (the reveal the printed answer key also gives);
   - play a short animation (the document's request);
   - stop accepting marks until the person chooses to keep looking or
     reset.
   Respect `prefers-reduced-motion` with a non-animated reveal.
3. **Reset:** a button that clears the board after a confirmation. Use an
   in-page confirm, not a browser `confirm()` dialog.

## Acceptance criteria

- **AC-1:** Marking a solution-white cell black increases the error count
  by one; undoing that mark decreases it by one; an undecided cell never
  counts.
  *test: TestSolverProgress_LiveErrorCount*
- **AC-2:** Filling exactly the solution's black cells, with any or no
  white marks, triggers the solved state and shows the picture's name. One
  extra black cell does not.
  *test: TestSolverProgress_SolvedWhenBlacksMatch*
- **AC-3:** The solved check agrees with a direct cell-by-cell comparison
  over a seeded corpus of at least 200 random boards per grid shape tried.
  *test: PropertyTest_SolverProgress_SolvedMatchesTheSolution*
- **AC-4:** With `prefers-reduced-motion: reduce`, the solved state appears
  without animation.
  *test: TestSolverProgress_ReducedMotion*

## Guardrails

- G-1: No new runtime dependency; plain JS as decided in CARD-160's ADR.
- G-2: No hint feature in this card. If one seems needed, it's a backlog
  item.
- G-3: Nothing is persisted: no score, no time, no progress row.

## Architecture context

- **FR:** — (pending the architect delta; see Blocked by)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/ (tokens only; error counter and solved state registered in components.md)
- **Screens:** /puzzle/<id>/solve

## Worktree notes

- [Origin] Cut 2026-10-03 from the owner's design doc at the owner's request.
