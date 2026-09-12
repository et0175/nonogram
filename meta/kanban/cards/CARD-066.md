# CARD-066: Filter the puzzle review by status (draft / approved / rejected / in book)

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/066-review-status-filter
**Worktree:** —
**Source:** owner, 2026-09-12: "On «Filter review and curation» I'd like to add «Filter by status (accepted/rejected/draft)»"
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py (the `/puzzles` route), src/nonogram/admin/templates/puzzles_list.html, tests
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The Puzzle Review page filters by date, book, name, size, difficulty and
quality, but not by status, so there is no way to list "everything I still
have to look at" (draft) or "what I rejected". The plumbing already exists:
`PuzzleFilter.status` is a field (`puzzle_review.py:31`) and the book
page uses it (`status="approved"`); the `/puzzles` route simply never reads
the parameter (confirmed 2026-09-12).

Statuses are `draft`, `approved`, `rejected`, `in_book`
(`PuzzleStatus`, `puzzle_review.py:14-20`).

## What to implement

1. `/puzzles` reads `status` from the query string and passes it to
   `PuzzleFilter`, the way `difficulty` is handled today.
2. A "Status" `<select>` in the filter form: "Any" plus the four statuses,
   keeping the current selection like the Difficulty control does. Label the
   options in the page's own words: Draft, Approved, Rejected, In book.
3. **Carry it through pagination.** `puzzles_list.html`'s
   `preserve_filters` macro (line 3-5) lists every filter in the page links;
   `status` has to be added, or paging silently drops the filter. This is
   the one part that is easy to miss and hard to notice.
4. An unknown status value (e.g. `?status=nonsense`) must not 500. Decide
   and state which: ignore it, or show the page's "Filter error" message the
   way an invalid size does.

## Acceptance criteria

- **AC-1** — `/puzzles?status=draft` lists only draft puzzles; the same for
  approved, rejected and in_book; with no `status` the list is unchanged
  from today (all statuses).
- **AC-2** — the rendered form marks the current status as selected, and
  "Any" when none is set.
- **AC-3** — the pagination links (First, Previous, the numbers, Next, Last)
  keep `status`, asserted on a rendered page with more than one page.
- **AC-4** — an unknown status behaves as decided in step 4, with no 500,
  pinned by a test.
- **AC-5** — the other filters, the sort and "Per Page" still work together
  with a status filter (one test combining two filters).

## Guardrails

- G-1: Do not change `PuzzleFilter`'s semantics or the store's filtering;
  this card only routes an existing field.
- G-2: Do not touch the book page's own status filtering
  (`/book/<id>/select-puzzles` passes `status="approved"` deliberately).
- G-3: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`.
