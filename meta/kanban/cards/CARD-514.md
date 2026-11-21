# CARD-514: The last one-session-per-puzzle loops, and the largest-board flake with the database armed

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/514-session-loops-flake
**Worktree:** —
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-045 (CARD-157 F-004) and IDEA-148 (CARD-183 merge-gate flake watch).
**Idea:** IDEA-045, IDEA-148
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/books/book_manager.py, tests/test_puzzle_solver_page.py
**UI surface:** books list (load time only)
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-21T10:25Z
**Closed:** 2026-11-21T12:24Z
**Actual:** 2c — ratio 2/2 = 1.0
**Merge commit:** 187d765f8df17af93e43dd089c68b0b5d0bc1a97
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
- [Path] The card's `src/nonogram/books/book_manager.py` does not exist; the floor loop is in `src/nonogram/admin/book_manager.py` (`BookManager._below_floor_for`). Both loops found by `ast` (calls to `get_puzzle` inside `create_app._book_member_records` and `BookManager._below_floor_for`).
- [Premise, measured before any change] Armed, main's code, the extended spy `TestBookPaths_SessionCountDoesNotScaleWithBookSize::test_the_book_paths_cost_the_same_at_both_sizes`: books list 8 sessions at 6 puzzles vs 62 at 60; floor check 8 vs 62 (N + 2 each).
- [Impl] `_book_member_records` (app.py): one `puzzle_review.get_puzzles` over `str()` of the book's own `puzzle_ids`; book order and repeats kept, a falsy/absent record left out as before. `BookManager._below_floor_for`: the submission is read with one `self.puzzle_store.get_puzzles(puzzle_ids)` before the loop; the loop is unchanged otherwise. Log change only: a non-UUID id now gets the "matches no stored puzzle" warning instead of the separate "no row can match (error)" one, because `get_puzzles` leaves both kinds out without saying which (results unchanged).
- [AC-1] The existing CARD-157 spy `measure_paths` (tests/test_puzzle_review_bulk_read.py) now also counts GET /books and `_below_floor_for` over a submission of N fresh puzzles, and deletes its book after measuring so the list shows one book. After the fix, armed: 6-puzzle {select 4, status 3, arrange 9, books 3, floor 3} = 60-puzzle, same figures. The test is renamed from `test_the_three_paths_cost_the_same_at_both_sizes` to `test_the_book_paths_cost_the_same_at_both_sizes` (it now covers five paths).
- [Control] app.py reverted to main alone: red, "sessions grew with the book: 6 puzzles {... 'books': 8 ...}, 60 puzzles {... 'books': 62 ...}". book_manager.py reverted to main alone: red, "{'floor': 8} != {'floor': 62}". Files restored; `git diff --stat` showed only the intended changes.
- [Tests changed] tests/test_book_floor.py: `_interleave` and the two read-count tests spied on `get_puzzle` only, so they went blind (3 red because the mid-add change never fired; 3 red because `read == []`). `_interleave` now wraps both `get_puzzle` and `get_puzzles`; the new helper `_record_reads` records ids from both. `test_the_paste_ids_route_measures_the_submission_once` now counts the POST alone and reads the page from the redirect afterwards with the spy removed (the detail page's own bulk read of the book's members is not a second measurement). Control: a mutant that calls `get_puzzles(puzzle_ids)` twice in `_below_floor_for` turns all 3 read-count tests red ("the submission was measured more than once: [p1, p2, p1, p2]").
- [AC-2] The gate below is green armed and unarmed. Books-list and floor neighbours are in it: test_books_list_plan_stats, test_books_list_mobile, test_book_manager, test_book_floor, property/test_book_membership_floor, test_book_cell_size, test_book_interior_type_floor, test_book_select_floor_tiles, test_book_detail_page, test_book_workflow_steps and property/test_book_workflow, chosen by a text search for `/books`, `_book_plan_stats`, `below_floor` and `FloorRefusal`.
- [AC-3, IDEA-148] Not reproduced. Armed runs at nonogram_pythonproject4_card_514_fc79cf1eb9b5_test on localhost (the header confirmed the name each time): 10 runs of `tests/test_puzzle_solver_page.py::TestSolverPageFits`, 16 runs of the whole file, 10 runs of the file behind its three predecessors in collection order (test_puzzle_solver_marking, _maybe, _mirror; 184 tests), and 1 armed gate run. That is K = 37 armed runs and 37 armed executions of `[row-clues]`, with 0 failures and 0 server errors. Code path: `puzzle_solve` -> `_board_page_payload` -> `PuzzleReviewService.get_puzzle`, over the SQLite `session_scope` that `_build_app` patches in. That fixture also overrides DATABASE_URL, so the armed Postgres is not on this path. Each request opens and closes its own session, nothing is shared across the server's threads, and a malformed id's ValueError is caught and turned into a 404. No obvious cause was found, so there is no fix. Closed as not reproduced. Armed test time spent here was about 33 min, more than the brief's 15 min: each suite-order run took 2.5 to 3.2 min, which was not measured before the loop was started.
- [AC-4] Net collected count 10690 -> 10690 (+0).
- [Gate] Files: the 11 neighbours above + tests/test_puzzle_review_bulk_read.py, tests/test_puzzle_solver_page.py, tests/test_kanban_review_record.py. Unarmed: 647 passed, 0 failed, 0 skipped. Armed: 647 passed, 0 failed, 0 skipped.

[Review 1/3] Score: 9.5, nothing gating, certified. Same results confirmed by a differential of main's two functions against the branch's, memory and armed Postgres stores (empty book, order, repeats, missing, malformed, upper-case and `uuid.UUID` ids, all-bad, mixed): identical member records, floor refusals and tiers. AC-1 controls re-run armed: head {books 3, floor 3} at 6 and 60; app.py alone reverted reds (8 vs 62); book_manager.py alone reverted reds (8 vs 62). The renamed bulk-read test is named by no ref under meta/architecture/, tests/ or docs/; test_check_ref_resolution and test_browser_fixture_scope 59 passed. The four spy mutants in test_book_floor red as the notes say. F-001 (low): IDEA-148's closure is mis-stated: `live` goes through `_build_app("sqlite")`, which sets DATABASE_URL to sqlite and patches `session_scope` to a tmp SQLite file, and did so at CARD-183's commit too, so the reported "with DATABASE_URL set" condition cannot reach Postgres on this path; the 37 runs are SQLite runs. F-002 (low): a non-UUID id's warning wording changed; nothing reads either string. F-003 (info, pre-existing): a `_tier_of` mutant ignoring `known=` leaves all 15 add tests green (every read-count test adds to an empty book). F-004 (info): "one read" is one bulk call, three sessions per path at both sizes, as CARD-157 read it.

**Orchestrator correction to AC-3 (review F-001).** IDEA-148 is closed as **not reachable as reported**, not as "not reproduced": on today's path, and at CARD-183's commit, the solver-page test's app reads puzzles from a temporary SQLite file whatever DATABASE_URL holds, so arming the suite does not change what that test reads. The 37 runs show the SQLite path green 37 times; they say nothing about Postgres.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 9016 passed / 30 skipped (the unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 13 deselected / 1 xfailed / 0 failed, then 11 passed marked.
