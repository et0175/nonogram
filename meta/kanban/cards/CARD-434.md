# CARD-434: A clue circles only when its run is closed by white — rule D is withdrawn

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: the rule itself is a deletion — pinnedNumbers and its branch in circledNumbers. The cost is the test population: rule D was landed with a measured corpus (21,316 numbers), and withdrawing it has to be measured the same way rather than asserted, plus the behaviour cells that assert D flip. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner's play-test doc "Гра - тест", 2026-11-12, item 3: *"Circle clues only if they're surrounded by white (dots)"*. Ruled the same day, asked because rule D exists precisely to circle runs that are NOT closed: **"Dots or the board edge"** — revert rule D; a number circles only when its run has an actual white dot, or the grid edge, on both sides.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py
<!-- Derived 2026-11-12. circledNumbers, pinnedNumbers and earliestStarts are all in solver_state.js; tests/test_puzzle_solver_clues.py is the only module that imports circledNumbers and holds TestSolverClues_PinnedNumbersCircle (line 3397 on main at the time of writing — resolve it by NAME). earliestStarts is also reachable from lineForced's family: check before deleting it, it may have a second caller. Re-derive the full set with scripts/impact_set.py --gate. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Rule D was the owner's ruling of **2026-11-10 — two days before this card** (CARD-400): *"circle a number when the marks pin it down"*. A run sitting on the same cells in every placement that fits the marks circles even when its neighbour is an unmarked blank or a "?". It was landed with a measurement: over every line up to 7 cells, 21,316 settled numbers circled; 46,901 beside a blank, 34,643 beside a "?" and 1,124 closed-with-a-repeated-value had not circled before.

Played with, it reads wrong. A circle appearing beside a cell the reader has not marked tells them a thing they did not deduce, on a line they have not finished. The owner now wants the circle to mean what the reader can see: **this run is closed**.

Rules A, B and C all already require a closed run, and all three treat the board edge as closing one, which is exactly what the ruling asks for. So this card is a clean withdrawal of D, not a new rule.

## What this is NOT

This is not "circles are wrong". Rules A, B and C stay exactly as they are, including rule C's deliberate absence of an ordering check — that is a separate known case, documented in `solver_state.js` and still a later card. Do not tidy it while here.

## What to implement

1. Remove rule D from `circledNumbers`: `pinnedNumbers` and its branch.
2. Remove `pinnedNumbers`, and `earliestStarts` **only if nothing else calls it** — derive that, do not assume; `lineForced` builds a similar table and may or may not share it.
3. Rewrite the rule-D paragraph in the `circledNumbers` doc comment: it must record that D existed, what it circled, that the owner withdrew it on 2026-11-12 after play-testing, and this card's number. A future reader who finds the measurement in the git history must not conclude the rule was lost by accident.

## Acceptance criteria

- **AC-1** (an open run does not circle): a line whose clue pins a run exactly, with the run fully dark and an unmarked blank beside it, circles nothing. (test: `tests/test_puzzle_solver_clues.py::TestSolverClues_PinnedNumbersCircle` — **rewritten, not deleted**: it keeps its fixtures and inverts its expectation, and its docstring names the ruling of 2026-11-12 that inverted it. Renaming it is a G-T breach; if the name is now wrong, say so in the notes and leave it.)
- **AC-2** (a "?" beside a pinned run does not circle): the same, with "?" in place of the blank. (test: the same cell.)
- **AC-3** (the edge still closes): a run that ends at the board edge with a white dot on its only open side still circles. (test: the existing rule-A/B cells, unchanged — this is the half of the ruling that is already true, and the AC exists to prove the card did not break it.)
- **AC-4** (rules A, B and C are untouched): every circle cell in `tests/test_puzzle_solver_clues.py` that predates CARD-400 passes unchanged. (test: those cells, unchanged.)
- **AC-5** (the withdrawal is measured, not asserted): over the same corpus rule D was landed with — every line up to 7 cells, every clue and every marking that fits — report how many numbers stop circling, and check that number against the 21,316 CARD-400 recorded. A figure that disagrees means one of the two measurements is wrong, and the card says which before merging. (evidence: the figure, in the notes.)

**Net test count: 0 added, and possibly fewer** — if rule D owns cells beyond `TestSolverClues_PinnedNumbersCircle`, they are rewritten or, where the behaviour no longer exists, removed with the count reported. Deleting a cell to make a gate pass is still forbidden; deleting one whose subject the owner withdrew is the point of the card. Say which, per cell.

## Worktree notes
