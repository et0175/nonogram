# CARD-533: The arrange screen's page plan fails loudly if its labels stop covering the printed rows

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/533-arrange-count-check
**Worktree:** ../PythonProject4-card-533
**Source:** roadmap wave 15, cut 2026-11-23 on the owner's "pick the next no-decision wave from the backlog". IDEA-022 (CARD-140 F-005).
**Idea:** IDEA-022
**Wave:** 94
**Created wave:** 94
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, its arrange-screen tests
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-23T17:51Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The arrange screen labels each puzzle with its interior page through `_printed_places` in `src/nonogram/admin/app.py`, whose `places` maps `id(row)` of the rows the caller passed to the plan's page. Re-checked on main at the cut: the book's arrange view builds the labels with `places.get(id(puzzle), {})`. A row missing from `places` silently gets no page label, and nothing compares how many rows were labelled with how many the plan prints. That is safe today, because `section_plan` keeps the caller's row objects. If that ever stops holding (a copy, a re-read, a dict rebuilt), every label quietly disappears and the screen looks like a plan with no page breaks. The agreed remedy (CARD-140 F-005): keep the `id(row)` key and add a count check that sets `page_plan_failed`.

## What to implement

1. In the arrange view, after `_printed_places`, compare the rows the screen will label against the plan's printed rows: every id in `printed` must be the id of a row in `puzzles_in_book`. Do it in the view or in `_printed_places`, whichever keeps the check next to the key it guards; record why in the notes. On a mismatch, log it (as the existing unexpected-failure branch logs) and set `page_plan_failed = True` with the same empty `places`/`divider_pages`/`printed` fallback, so the owner sees the existing page-plan notice.
2. One test, by changing an existing arrange-screen test file and not adding a file: make the plan return copies of the rows (monkeypatch at the seam), and assert the notice shows and no page label is rendered. Show it red with the check deleted.
3. Do not change the key (`id(row)`) or the `unprinted` marking (CARD-490).

## Acceptance criteria

- AC-1: a plan whose printed rows are not the caller's row objects sets `page_plan_failed` and shows the page-plan notice; the test is red without the check.
- AC-2: the existing arrange-screen tests pass unchanged.
- AC-3: net tests +1 at most.

## Worktree notes

**2026-11-23 (implementation).**

- Premise, re-verified by a run on unchanged main code (a temporary probe in `test_a_bug_in_the_seam_itself_is_logged_with_its_traceback`, with `section_plan` monkeypatched to plan `dict(row)` copies of the rows; probe removed): `notice: False labels: ['page 5 · Easy divider page'] unprinted: [('Not printed: cannot be drawn', None)]`. So it is worse than the card says: no puzzle page label and no notice, as stated, but the divider label (keyed by tier, not row) still renders and the row is wrongly marked "Not printed: cannot be drawn", because the CARD-490 `printed` set is keyed by `id(row)` too.
- Fix: the check lives in `_printed_places`, beside the `id(row)` key it guards (also the only place that holds both the caller's rows and `plan.printed`; the view would have had to re-derive the plan or receive the plan object). Any row of `plan.printed` whose id is not the id of a row passed in raises `LookupError`. LookupError is deliberately neither `RuntimeError` nor `ValueError` (the seam's declared failures), so the arrange view's existing `except Exception` branch handles it unchanged: `app.logger.exception(...)` with the traceback, empty `places`/`divider_pages`/`printed`, `page_plan_failed = True`, the existing `page-plan-unavailable` notice. No new notice text, no change to the view's control flow; its comment now names this case. Key (`id(row)`) and the CARD-490 `unprinted` marking unchanged: with `page_plan_failed` set no row is marked.
- Test: no new test. `test_a_bug_in_the_seam_itself_is_logged_with_its_traceback` (tests/test_book_arrange_page_breaks.py) gets a third broken variant, `copies` (`section_plan` planning `dict(row)` copies), and two asserts: `shown_unprinted(markup) == []` for every variant, and for `copies` a logged `LookupError` naming "not the caller's row objects" (so the count check fired, not some other error).
- AC-1: the `copies` variant shows the notice, renders no page label (`shown_labels == []`), marks no row, logs with traceback. Control: the check (the `given`/`strangers`/`raise` block) deleted, the test is red at its first assert: `AssertionError: ('section_plan', 'the owner is still told')` / `assert 'id="page-plan-unavailable"' in '...'`. The later asserts are not reached in that run; the probe above (control code == main code) shows each would be red too: labels `['page 5 · Easy divider page']`, unprinted `[('Not printed: cannot be drawn', None)]`, and no error logged for that book (only book_000001/000002, the other two variants). Restored; `git diff --stat` shows only the intended two files.
- AC-2: the existing arrange-screen tests pass unchanged (the two existing variants' assertions are untouched; the added unprinted assert holds for them).
- AC-3: net tests +0 (10713 collected before and after; tests/test_book_arrange_page_breaks.py 20 and 20).
- Gate, unarmed, `-o addopts= -rfs`: tests/test_book_arrange_page_breaks.py, tests/test_book_arrange_play_link.py, tests/test_book_arrange_position.py, tests/test_book_arrange_size_filter.py, tests/test_book_arrange_sort_by_size.py, tests/test_book_detail_page.py (book detail + CARD-490 not-printed tests), tests/test_book_toc.py and tests/test_book_finalise_gutter.py (the other two files that reach the page-plan path): 385 passed, 0 failed, 0 skipped. Nothing skipped unarmed, so no db_required test sits in this set's path; not run armed (the card asks for no armed run).

[Review 1/3] Score: 9.5, certified. Re-derived: on main code a plan over `dict(row)` copies shows no notice, no row labels, marks the row "Not printed: cannot be drawn" and logs nothing; a four-row book with every second row copied loses a label and falsely marks two rows. On the branch both show the notice, no labels, no marking, and log a `LookupError` with traceback ("2 of 4 rows"); an unbroken plan shows no notice. With the check deleted, each of the six asserts for the copies variant is red on its own (soft-assert copy). `LookupError` escapes `(RuntimeError, ValueError)` and is logged by `except Exception`. `_printed_places` has one call site (ast over src/, tests/, scripts/). Gate files 385 passed, 0 skipped. Net 0. F-1 (low): the test comment "not a KeyError downstream" overstates the `isinstance(..., LookupError)` check; the message match is what pins it. F-2 (info): the guard checks identity of every printed row, which is stronger than the title's "count check" and matches step 1 word for word.
