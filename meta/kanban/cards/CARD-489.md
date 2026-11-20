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
* **AC-2**: mutating the object `get_book` returns (memory mode) leaves the stored book unchanged; control: return the live object, it reds. Every existing memory-mode caller that mutated the returned book on purpose is found (by `ast`/grep of call sites, listed in the notes) and moved to a setter, or the card stops and reports. (Amended 2026-11-20 by the orchestrator after the implementation: a TEST seed site that stores a value no setter accepts on purpose — an unreadable trim or ink mode, a raw puzzle order, a forced status — writes the memory store directly, `manager.books[book_id]`, as its DB branch writes the row; product callers still go through setters.)
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
- 20 test seed sites wrote stored state through the returned book. **Fix round 1 (review F-001) re-sorted them by trying the setter on each value**, using a memory manager probe, not by reading:
  - **Moved to `set_print_spec` (4 sites, because the setter accepts the value):**
    - `test_book_uploaded_dividers.py::...test_the_flash_names_the_slot_both_sizes_and_the_remedy_then_remove_exports` (trim 15.24 x 22.86). Its generator now reads the book back with `get_book`.
    - `test_book_finalise_guide_preview.py::...test_the_play_sentence_and_the_page_numbers_are_the_printed_ones` (domain `https://nonogram.adverax.io`).
    - `test_book_finalise_gutter.py::...test_a_stored_domain_adds_the_page_and_its_blank_and_the_band_follows` (its `self.DOMAIN` write).
    - `test_book_finalise_gutter.py::...test_end_to_end_through_the_real_unreadable_spec_path` (trim height "12.00").
    - The two domain sites pass the book's own stored trim back in. The "12.00" site passes the stored width.
    - The trim half of `test_book_finalise_gutter.py`'s `Panel.book` (`TRIM_CM`, accepted) moved too.
  - **Kept as a direct write to `manager.books[book_id]` (16 sites), because the setter refuses the value or no setter exists for it:**
    - `set_print_spec` refuses it (ValueError, probed): the `None` trim in `test_book_detail_page.py::...test_a_book_with_no_print_spec_says_not_set_and_links_to_print_setup`; the "not-a-number" trim in `...test_an_unreadable_stored_trim_says_so_and_links_to_print_setup` and in `...test_a_book_whose_page_plan_cannot_be_built_shows_no_numbers`; the "wide-ish" and "not a number" trims at `test_book_floor.py`'s 4 sites (`_unreadable_trim`, `test_a_book_whose_trim_cannot_be_read_takes_nothing_and_names_the_column`, `test_the_store_raises_naming_the_column_and_the_remedy`, `test_it_refuses_nothing_even_when_the_trim_cannot_be_read`); "not a domain" (the second write in the stored-domain test); width "5" (one parameter of `TestFinaliseCounts_ShowsWhyTheCountIsApproximate`); and ink "sepia" in `test_book_pdf_ink_mode.py::...test_finalise_says_so_when_the_stored_mode_cannot_be_read`.
    - No setter exists for margins: the margin half of `Panel.book`, the "1.27" gutter in `test_the_scenario_really_has_that_many_pages`, and the 0.60 gutter parameter of `TestFinaliseCounts_...` (that `setattr` site carries both parameters, so it is one site).
    - `reorder_puzzles` would refuse the order (`is_level_order` is False, probed):
      - `test_book_detail_page.py::_book_stored_as` with `MIXED`. For a caller that passes an already-grouped order, the write equals what `add_puzzles_to_book` already stored.
      - `test_a_repeated_member_is_numbered_at_each_place_it_prints` (M1, E1, E1, which is also a duplicate).
      - `test_numbers_equal_the_export_over_a_seeded_corpus`: replaying seed 165 outside the test, 8 of its 14 stored orders are ungrouped (refused) and 6 are grouped (accepted, stored identically). I kept one write path for the corpus rather than branching per book, so this site qualifies on 8 of 14 only.
    - `set_book_status` refuses it: forcing `published` in `test_book_floor.py::...test_a_published_book_asks_before_it_takes_a_puzzle`. That one-puzzle book is checked against `DEFAULT_PLAN`, which `off_plan_cells` puts 10 cells off on an empty selection, and one puzzle moves one cell, so the ready gate refuses it. The write sits inside the test's `memory` branch.
  - Writing `manager.books[...]` directly in tests is not new to this card. The tree already had such writes, for example in `test_player_bundle.py`, `test_book_trim_persistence.py` and `test_book_level_order.py`.
  - This changes test seeding only, not product behaviour.
- After fix round 1: 246 call sites (the 4 moved sites read the book back with `get_book`). 6 are flagged, all of them the false positives above plus `test_get_book`'s own deliberate write. There are 0 `setattr` sites.
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

**Fix round 1 (review cycle 1) notes.**
- F-001: re-sorted the 20 seed sites as listed above (4 moved, 16 kept). Re-run unarmed, `-o addopts= -rfs`, over the 8 touched files (`test_book_uploaded_dividers`, `test_book_finalise_guide_preview`, `test_book_finalise_gutter`, `test_book_detail_page`, `test_book_floor`, `test_book_pdf_ink_mode`, `test_book_manager`, `test_book_plan_storage`): 512 passed, 0 failed, 0 skipped. Net collected count is unchanged at 10706 (+1 over the 10705 before the card).
- F-002: reading of "What to implement" item 1. The count change re-judges only the cells the owner *typed into*. A stored edit the owner left alone keeps its mark across a count change, even when it equals the new prefill (CARD-120 F-001's rule, kept by `revise_plan`'s "equal to the shown value" branch).
- F-003: no test pins which split the reference uses. A count change and a split change in one submission still judge typed cells against the *shown* split, as main did. This is out of scope and recorded for the backlog.
