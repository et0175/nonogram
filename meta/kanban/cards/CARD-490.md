# CARD-490: The arrange page marks a puzzle that will not print, as the book page already does

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/490-arrange-not-printed
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-024, WSJF 3.46 (CARD-140 F-007).
**Idea:** IDEA-024
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/test_book_arrange*.py
**UI surface:** admin book arrange page (page labels)
**Review score:** 9.6 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-20T01:11Z
**Closed:** 2026-11-20T02:56Z
**Actual:** 2c — ratio 2/1 = 2.0
**Merge commit:** 728130842900d4cc6d549c70e210fe1ef5ed473b
**Blocked by:** —

## Why this card exists

On the arrange page (`arrange_puzzles_in_book`, `book_arrange_puzzles.html`) a puzzle the interior cannot draw sits between the "page 3" and "page 4" labels with no marker, so the screen says it prints on page 3. The template has only the `page_plan_failed` branch. The book detail page (`book_detail`) already says "Not printed: cannot be drawn" for the same rows (CARD-165).

## What to implement

1. Reproduce first: a book holding one undrawable puzzle; record what the arrange page shows today.
2. The arrange page marks such a row "Not printed: cannot be drawn", with the same wording and the same source of truth as `book_detail` (reuse the computation; do not derive "undrawable" a second way).
3. The row does not sit under a page label it will not print on.

## Acceptance criteria

* **AC-1**: an undrawable puzzle's row on the arrange page carries the marker and no page number; control: drop the marker from the template, it reds.
* **AC-2**: a book with no undrawable puzzle renders the arrange page byte-identical to main (compare the HTML of one ordinary book before and after).
* **AC-3**: net test count at most +1; report it.

## Guardrails

* **G-1**: the page plan itself is unchanged; this is display only.
* **G-2**: the marker's wording is `book_detail`'s, not new copy.

## Worktree notes

### Implementation (2026-11-20)

**Reproduced first** (scratch capture script, ids made deterministic): on the base, a book of three big easy puzzles with the middle one undrawable rendered `page 6` / row(page 6) / row(no `data-page`, no marker) / `page 7` / row(page 7), so the undrawable row read as printing on page 6. A second shape, found while reproducing: three small easy puzzles with the middle one undrawable pair the outer two onto page 6, and the third row (page 6, not opening its page) then sat after the unmarked row with no label at all.

**What changed**
- `app.py`: module constant `NOT_PRINTED_CANNOT_BE_DRAWN`, used by `book_detail` (replacing its literal) and by `arrange_puzzles_in_book`, which sets `puzzle["unprinted"]` for a row the plan was built over but `_printed_places` did not place (its keys are exactly `section_plan`'s `printed` rows, the set `book_detail` numbers from). No plan (`page_plan_failed`): no row is marked; the existing notice speaks for all. Page plan untouched (G-1).
- `book_arrange_puzzles.html`: an unprinted row gets a `page-break-divider data-unprinted="true"` with the wording where a page label would stand, and the row carries `data-unprinted="true"`; a printed row right after an unprinted one says its page label again (`loop.previtem`). Whitespace control keeps ordinary books' output unchanged.
- Tests (`tests/test_book_arrange_page_breaks.py`): helper `shown_unprinted`; assertions added to `test_an_undrawable_member_shifts_no_other_rows_page` and `test_the_step_still_answers_when_the_book_cannot_be_planned`; one new test `test_a_row_after_an_unprinted_one_says_its_page_again`.

**AC evidence**
- AC-1: `test_an_undrawable_member_shifts_no_other_rows_page` asserts the marker directly above the row and the row has no page. Control C1 (marker block dropped from the template): that test and `test_a_row_after_an_unprinted_one_says_its_page_again` red, `assert [] == [('Not printe...drawn', None)]`.
- AC-2: arrange HTML of an ordinary book (6 puzzles, 3 levels, two paired pages), all sizes and the `<=15` band, captured on the base commit and on the branch with the same script: `cmp` identical for both.
- AC-3: collected 10705 on the base, 10706 on the branch (net +1).
- G-2: the wording is one constant shared with `book_detail`; `test_shows_a_dash_and_a_reason_instead_of_a_number` (book page) and the arrange tests both pin the literal.

**Other controls** (each restored; `git diff --stat` empty afterwards)
- C2 (re-label clause dropped): `test_a_row_after_an_unprinted_one_says_its_page_again` red, "the row after the unprinted one is labelled with the page it prints on".
- C3 (`not page_plan_failed` guard dropped): `test_the_step_still_answers_when_the_book_cannot_be_planned` red, `assert [('Not printe...drawn', None)] == []` (its following `"Not printed" not in markup` assert is not reached, so it is not separately controlled).
- C4 (route computation replaced by `None`): the same two tests as C1 red with the same assertion.

**Gate** (unarmed, `-rfs`): `tests/test_book_arrange_page_breaks.py`, `test_book_arrange_play_link.py`, `test_book_arrange_position.py`, `test_book_arrange_size_filter.py`, `test_book_arrange_sort_by_size.py`, `test_book_detail_page.py`, `test_book_level_order.py`, `test_book_workflow_steps.py`: 367 passed, 0 failed, 0 skipped. Not visually eyeballed in a browser: the marker reuses the `page-break-divider` style, no new CSS.

### Fix round 1 (review cycle 1: F-001, F-002)

- **F-002**: `_printed_places` now returns `(places, divider_pages, printed)`, where `printed` is `{id(row) for row in plan.printed}`, `section_plan`'s own printed rows and the set `book_detail` numbers from. `arrange_puzzles_in_book` marks a row from that set (`id(puzzle) not in printed`) instead of from its absence from `places`. Page plan unchanged.
- **F-001**: `test_a_row_after_an_unprinted_one_says_its_page_again` now uses four small easy puzzles with the middle two undrawable. Measured on the route before writing the asserts: rows `[6, None, None, 6]`, two markers each with page None, labels `page 5 · Easy divider page`, `page 6 · two puzzles` twice, no `page None`. No test added.
- **Controls** (run together over the arrange page-break, book-detail and size-filter files, 96 tests; each restored, tree clean afterwards):
  - M9 (`puzzle.page and` dropped from the re-label condition): the test reds at "a row with no page is never labelled with one". Per assertion, checked on the mutant's markup: rows held, markers held, no-`page None` failed, labels failed (`['page 5 · Easy divider page', 'page 6 · two puzzles', 'page None', 'page 6 · two puzzles']`), plan held.
  - C5 (printed set diverged to `plan.puzzles`): `test_an_undrawable_member_shifts_no_other_rows_page` and `test_a_row_after_an_unprinted_one_says_its_page_again` red, `assert [] == [('Not printe...drawn', None)]`.
  - C1–C4 re-run on the new code: C1 and C4 red the same two tests with the same line; C2 reds the re-label test at "the row after the unprinted one is labelled with the page it prints on"; C3 reds `test_the_step_still_answers_when_the_book_cannot_be_planned`, `assert [('Not printe...drawn', None)] == []`.
- **AC-2** re-captured against the merge-base f158f589: ordinary book, all sizes and `<=15`, `cmp` identical.
- **Gate** (unarmed, `-rfs`, the round-0 files): 367 passed, 0 failed, 0 skipped. **Count**: 10705 at the merge-base, 10706 on the branch (net +1).

[Review 1/3] Score: 9.0, one gating finding, not certified. F-001 two ADJACENT undrawable rows had no test: a mutant dropping `puzzle.page and` from the re-label condition printed "page None" above the second of them with all 96 arrange/detail/size-filter tests green; F-002 (low) the arrange page derived "unprinted" from "not placed" while book_detail uses "not in plan.printed" — equal today, by coincidence of `puzzle_section`; F-003 (low, owner's visual question) the repeated "page 6 · two puzzles" label and the marker styled exactly like a page label (screenshots in ~/Documents/nonogram-reviews/CARD-490/); F-004 (info, pre-existing on main) a pair's second puzzle shows no page label when a size filter hides the first; F-005 (info) the row's `data-unprinted` attribute is read by nothing. Byte-identical ordinary page re-captured over seven filter views; same rows marked as book_detail on a six-undrawable book. Fixed in `06b68d52`: F-001 by extending the re-label test to four puzzles (two adjacent undrawable), F-002 by marking from the plan's own printed set. F-003 left for the owner; F-004, F-005 not taken.

[Review 2/3] Score: 9.6, nothing gating, certified. F-001 closed: M9 reds the extended test on two separate assertions ("page None" absent; the label list), every figure in the test is what HEAD's route produces. F-002 closed: four mutants diverging the arrange page's set from book_detail's each red (2-4 tests); the two `except` branches' three-tuples each have a red control. Ordinary book byte-identical against the merge-base over 7 captures; page plan unchanged on the six-undrawable book. F-003 (owner's visual question), F-004 (pre-existing, size filter hides a pair's first puzzle), F-005 (`data-unprinted` unread) carried; F-006 (info) the cycle-1 "not placed" definition passes every test, as it must while the plan places every printed row. 367 passed over the 8 gate files; net +1.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 9032 passed / 30 skipped (the expected unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed / 0 failed, plus 11 marked (wave_close_only) passed in the lifted files; 2 marked tests owed at the wave close. F-003 (the repeated page label and the marker's styling) is the owner's question, asked 2026-11-20; merged as reviewed.
