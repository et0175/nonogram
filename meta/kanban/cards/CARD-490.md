# CARD-490: The arrange page marks a puzzle that will not print, as the book page already does

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/490-arrange-not-printed
**Worktree:** ../PythonProject4-card-490
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-024, WSJF 3.46 (CARD-140 F-007).
**Idea:** IDEA-024
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/test_book_arrange*.py
**UI surface:** admin book arrange page (page labels)
**Review score:** —
**Started:** 2026-11-20T01:11Z
**Closed:** —
**Actual:** —
**Merge commit:** —
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
