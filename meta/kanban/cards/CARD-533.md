# CARD-533: The arrange screen's page plan fails loudly if its labels stop covering the printed rows

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 15, cut 2026-11-23 on the owner's "pick the next no-decision wave from the backlog". IDEA-022 (CARD-140 F-005).
**Idea:** IDEA-022
**Wave:** 94
**Created wave:** 94
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, its arrange-screen tests
**UI surface:** —
**Review score:** —
**Started:** —
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
