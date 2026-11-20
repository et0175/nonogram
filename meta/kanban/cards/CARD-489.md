# CARD-489: Two book_manager leaks: the hand-edit mark survives a count change, and memory mode hands out the live Book

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/489-book-manager-leaks
**Worktree:** ../PythonProject4-card-489
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-011 WSJF 3.46, IDEA-014 WSJF 3.08; one card because both live in src/nonogram/admin/book_manager.py.
**Idea:** IDEA-011, IDEA-014
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_manager.py, tests/test_book_plan_storage.py, tests/test_book_manager*.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T00:32Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-011 (CARD-120 F-007).** `revise_plan` keeps a hand-edit mark on a plan cell. Typing a cell back to its prefill reads as handled (the 2026-11-18 triage), but when the puzzle count changes the edits are still judged against the OLD prefill, so a cell can stay "hand-edited" (or lose the mark) for the wrong reason.
2. **IDEA-014 (CARD-136, owner-accepted 2026-09-23).** In memory-only mode `BookManager.get_book` returns `self.books.get(book_id)`, the live `Book`; a caller can write an invalid trim past `set_print_spec`'s validation. DB mode already returns a fresh object.

## What to implement

Re-verify each against main first, in a test, before changing code; drop any already closed with one line in the notes.

1. A count change re-judges the hand-edit marks against the NEW prefill (a cell equal to the new prefill is not hand-edited; one that differs is).
2. Memory mode's `get_book` returns a copy, so mutating it changes nothing stored; writes still go through the manager's own setters.

## Acceptance criteria

* **AC-1**: a count change followed by a read gives marks consistent with the new prefill; control: the old comparison reds it.
* **AC-2**: mutating the object `get_book` returns (memory mode) leaves the stored book unchanged; control: return the live object, it reds. Every existing memory-mode caller that mutated the returned book on purpose is found (by `ast`/grep of call sites, listed in the notes) and moved to a setter, or the card stops and reports.
* **AC-3**: net test count at most +2; report it.

## Guardrails

* **G-1**: DB mode's behaviour unchanged (its tests are `db_required`; run them armed at the worktree's own `_test` database and report the skip count with `-rfs`).
* **G-2**: no schema change.

## Worktree notes

### Implementer notes (2026-11-20)

**Premise check (before any code change).** Both items reproduced on the merge-base code, so neither is dropped.
- IDEA-011: typing a cell back to its prefill at an *unchanged* count already works (the existing `TestRevisePlan::test_typing_a_cell_back_to_its_prefill_un_edits_it`). The count-change case was still open. Recorded run: `revise_plan(DEFAULT_PLAN, 90, Split(40, 40, 20), cells)` with `<=15 x easy` typed 20 -> 12 (the 90-puzzle prefill) returned `edited == {(<=15, easy)}`. The reverse also happened: a stored edit typed to the old 150-puzzle prefill (16-20 x medium, 27) lost its mark, and the cell was re-derived to 16.
- IDEA-014: memory-mode `get_book` returned `self.books.get(book_id)`. The extended `test_get_book` wrote `trim_width_cm = "999"` through it, and a re-read returned `'999'`.

**What changed.**
- `revise_plan`: the reference prefill is now `prefill(typed.count, shown.split)` (the submitted count). Before, it was `prefill(shown.count, shown.split)`. The docstring now says this. The split stays the shown split, as before: this card covers count changes only.
- `BookManager.get_book` (memory mode) returns `copy.deepcopy` of the stored book. DB mode is unchanged.
- `BookManager.add_puzzles_reporting_refusals`: its memory branch now writes to `self.books[book_id]` and not to the `get_book` copy. It was the only src caller that wrote through the returned book. `remove_puzzle_reporting_confirmation` and `reorder_puzzles` already re-read `self.books.get` in their memory branch.

**AC-2 caller census** (by `ast` over src/ and tests/, scripts kept out of the repo). Before: 261 `get_book` call sites. 24 were flagged as writing through the result (attribute/subscript store, augassign, mutating call, or a fixture that returns the object), and one more `setattr` site was found after a red run. The flagged sites:
- src: `add_puzzles_reporting_refusals` was the real case and is fixed above. `remove_puzzle_reporting_confirmation` and `reorder_puzzles` were false positives, because they rebind from `self.books`.
- The fixtures `Panel.book` (`test_book_arrange_page_breaks.py`) and `choose` (`test_book_pdf.py`) return the object to callers that only read it. Their files pass unchanged.
- 20 test seed sites wrote stored state through the returned book. Most of that state is a value no setter accepts on purpose: an unreadable trim or ink mode, a raw player domain, margins with no setter, a raw or duplicated `puzzle_ids` order, or a status forced to published. The sites are in `test_book_detail_page.py` (6), `test_book_finalise_gutter.py` (6, one of them the `setattr` in `TestFinaliseCounts_ShowsWhyTheCountIsApproximate`), `test_book_floor.py` (5), `test_book_finalise_guide_preview.py` (1), `test_book_pdf_ink_mode.py` (1) and `test_book_uploaded_dividers.py` (1). **They were NOT moved to a setter, because no setter accepts those values.** Each one now writes to the memory store directly (`manager.books[book_id]`), which is the memory-mode version of the raw row write their DB branches already make. This changes test seeding only, not product behaviour. In `test_book_floor.py::...test_a_published_book_asks_before_it_takes_a_puzzle` the write moved inside its `memory` branch, so DB mode never touches `.books`.
- After: 242 call sites. 6 are flagged, all of them the false positives above plus `test_get_book`'s own deliberate write. There are 0 `setattr` sites.
- Not in scope: memory-mode `get_books_by_status` and `get_all_books` still return the stored objects.

**Controls** (each one reverted the mechanism and was then restored; `git diff --stat` of the src file was back to this card's diff each time).
- Old reference `prefill(shown.count, ...)`: `TestRevisePlan::test_a_count_change_judges_typed_cells_against_the_new_prefill` goes red on `assert revised.edited == {(B20, M)}` (the extra item is `(<=15, easy)` and the missing one is `(16-20, medium)`). The cell-value assert `revised.cell(B20, M) == 27` also goes red under the old code (the value is 16). I dropped a non-discriminating `cell(B15, E) == 12` assert.
- Live `return book` in `get_book`: `TestBookRetrieval::test_get_book` goes red with `assert ('999', '27.94') == ('21.59', '27.94')`. Its title and `puzzle_ids` asserts are each false under the same mutant (checked in a script).
- With the `self.books[book_id]` rebind removed from `add_puzzles_reporting_refusals`, 11 tests in `tests/test_book_manager.py` go red, for example `test_add_puzzles_to_book` with `assert 0 == 3`.

**Gate (unarmed, `-o addopts= -rfs`).**
- All 67 files `tests/test_book*.py` plus `tests/test_card_100_book_membership.py`: 3193 passed, 0 failed, 1 skipped. The skip is `test_book_pdf_memory.py` setrlimit(RLIMIT_AS), the platform skip.
- Neighbours, the 15 other test files that reference `get_book` or `.books` (`tests/property/test_book_{membership_floor,order,ready_gate,workflow}.py`, `test_admin_error_text`, `test_card_068/101/107/108_*`, `test_player_bundle`, `test_print_specs`, `test_puzzle_edit_routes`, `test_puzzle_editor_ui`, `test_puzzle_review_bulk_read`, `test_status_filter_default`): 694 passed, 4 skipped. The 4 skips are `DATABASE_URL is not set`, the db_required tests in `test_puzzle_edit_routes`.
- An earlier run of the book files had 3 reds. 2 of them were the `setattr` site, fixed above. The third was `test_book_pdf.py::TestShippedDefault_TheTestTreesRebindDoesNotHideIt::test_a_shipped_default_that_carries_writers_reds_the_pin`. Its subprocess pytest was refused because another worktree held the full-suite lock at the time. It passes alone and in the final run.

**G-1 (armed).** The book_manager and plan-storage tests have no `db_required` members: their DB mode runs on SQLite and is inside the unarmed figures above. So I ran all 29 collected `db_required` tests armed, at this worktree's own database (`DATABASE_URL=.../nonogram_pythonproject4_card_489_e94561bd2bd2_test`): 29 passed, 0 skipped. The first armed attempt used `.../nonogram_test`, which is not this worktree's resolved database. The suite said so, and 10 of the 29 failed on that mismatch. That attempt is not counted.

**G-2.** No schema change.

**AC-3 (net test count).** `--collect-only` over tests/: 10705 before, 10706 after, so +1. I added `test_a_count_change_judges_typed_cells_against_the_new_prefill` and extended `test_get_book` in place.
