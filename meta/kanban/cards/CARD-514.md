# CARD-514: The last one-session-per-puzzle loops, and the largest-board flake with the database armed

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/514-session-loops-flake
**Worktree:** ../PythonProject4-card-514
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-045 (CARD-157 F-004) and IDEA-148 (CARD-183 merge-gate flake watch).
**Idea:** IDEA-045, IDEA-148
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/books/book_manager.py, tests/test_puzzle_solver_page.py
**UI surface:** books list (load time only)
**Review score:** —
**Started:** 2026-11-21T10:25Z
**Blocked by:** —

## Why this card exists

1. **IDEA-045.** Two loops still open one database session per puzzle: `_book_member_records` (the /books list, app.py) and the floor-check loop in book_manager.py. Both can use `PuzzleReviewService.get_puzzles`, as CARD-157 did for the others. On the production database (~250 ms per query, memory: /books took 131 s) this is the books list's cost.
2. **IDEA-148.** `tests/test_puzzle_solver_page.py::TestSolverPageFits::test_the_largest_board_fits_a_laptop_screen[row-clues]` returned a server 500 reading the puzzle once with DATABASE_URL set (CARD-183's gate) and passed 3/3 alone. Find whether it is still reproducible (several armed runs of the class and of the file in suite order) and, if a cause shows, fix it; if it never reproduces, say how many runs and close it as unreproduced with that figure.

## What to implement

Re-verify each against main first.

## Acceptance criteria

* **AC-1**: both loops read their puzzles in one call; a session or query-count spy on an existing test shows one read for N puzzles (control: main's loop reds it with N).
* **AC-2**: the /books list and the floor check give the same results as before for a book with several puzzles (existing tests stay green, armed).
* **AC-3**: IDEA-148 is either fixed with a control, or recorded as not reproduced in K armed runs (state K and the selections).
* **AC-4**: net test count at most +1; report it.

## Guardrails

* **G-1**: never connect to the production database; armed runs use the worktree's own `*_test` database on localhost.
* **G-2**: no behaviour change in what the pages show.

## Worktree notes
