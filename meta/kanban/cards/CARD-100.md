# CARD-100: A puzzle in a book is not protected — book membership is recorded in one place and read from another

**Status:** ready
**Priority:** P1
**Category:** bugfix
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/100-book-membership-is-one-fact
**Worktree:** —
**Source:** found 2026-09-20 while starting CARD-068; demonstrated end to end before the card was opened, and re-confirmed on `main` at `0861e24`
**Idea:** —
**Wave:** 1
**Depends on:** — _(CARD-068 merged 3223753 left `BookManager.book_listing` behind, which answers "which book holds this puzzle" from the side that actually knows)_
**Touches:** src/nonogram/admin/book_manager.py (membership writes both sides), src/nonogram/admin/puzzle_review.py (the guards, the `unassigned` filter, `get_approved_puzzles`, `mark_in_book`), src/nonogram/admin/app.py (the bulk reports gain their clause), a backfill for existing rows, tests
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Every "never touch a puzzle that is in a book" rule in the admin panel reads
`Puzzle.book_id` (or the `in_book` status). Nothing in production writes
either one.

Book membership is recorded in `Book.puzzle_ids` by
`BookManager.add_puzzles_to_book`, which does not touch the puzzle row.
`PuzzleReviewService.mark_in_book` — the only code that sets `Puzzle.book_id`
and the `in_book` status — **has no production caller at all**; searched
across `src/`, it is reached only from tests. So the column the guards consult
is, in a running panel, always `None`.

Measured on `main` at `16a7180`, in-memory mode, with the real
`BookManager`:

```
book lists the puzzle: True
puzzle row after booking: {'status': 'draft', 'book_id': None}
delete_rejected outcome: BulkOutcome(changed=1, unchanged=0, in_book=0)
puzzle still in the store: False
book STILL lists the deleted puzzle: True
```

A puzzle a book lists was rejected, then deleted by "Delete rejected", and the
book now points at an id that no longer exists. The same hole lets "Approve
all" and "Reject all" rewrite the status of a puzzle a book is built on.

This is why the bulk actions in CARD-068 report what they changed but say
nothing about what a book held back: the number would be zero however many
puzzles a book actually lists, and a confident "0 left alone: in a book" is
worse than silence.

### Three more things the same root cause breaks (found 2026-09-20)

Surveyed after the card was opened, by reading every site that consults the
column:

- **The book builder offers puzzles that are already in a book.** Step 2 of
  the book flow filters `book_id="unassigned"` with the comment "Only show
  puzzles NOT in any book" — and since nothing sets the column, *every* puzzle
  matches. A puzzle already bound into book A is offered while building book
  B, and nothing stops it being used twice. This is the one symptom an owner
  can see without reading code.
- **`get_approved_puzzles(book_id)` cannot return anything.** It filters
  `status == in_book AND book_id == <id>`, neither of which is ever written,
  so it is empty for every book. It has no production caller — the PDF path
  reads `Book.puzzle_ids` — so this is dead code that would be wrong if it
  were revived. Decide whether it is repaired or removed.
- **The dashboard's "in_book" count is always zero**, for the same reason.

**Two smaller defects found with it:**

- `reject_puzzle` and `restore_puzzle` change a puzzle's status with no
  in-book check at all, so even where `book_id` *is* set, a per-puzzle Reject
  walks straight past the protection the bulk path takes care over.
- `mark_in_book`'s DB branch assigns `book_id` without converting a `str` to a
  `UUID`, so it raises `AttributeError: 'str' object has no attribute 'hex'`
  in DB mode on the same argument its in-memory branch accepts. Since nothing
  calls it in production, nothing has noticed.

## What to implement

1. **One fact, written once.** Decide which side owns membership and make the
   other follow, in both storage modes:
   - **(a) The puzzle row owns it.** `add_puzzles_to_book` and
     `remove_puzzle_from_book` set and clear `Puzzle.book_id` (and the
     `in_book` status) as they edit `Book.puzzle_ids`. The existing guards
     start working unchanged. Needs a backfill.
   - **(b) The book owns it.** Drop `Puzzle.book_id`/`in_book` and have every
     guard ask the book side. Fewer places to keep in step, but every guard
     becomes a scan or a join, and the `book_id`/`unassigned` filters in
     `filter_puzzles` are rewritten.

   **(a) is recommended:** the column exists, the guards already read it, the
   `"unassigned"` filter already depends on it, and `Book.puzzle_ids` is a
   JSON list that cannot be joined or indexed.

2. **Backfill the existing rows.** A live database has books whose puzzles all
   carry `book_id = NULL`; until they are filled in, the guard stays false for
   every book made before this card. One-shot, driven from `Book.puzzle_ids`,
   reported rather than silent — and see G-2.

3. **Close the per-puzzle bypass.** `reject_puzzle` and `restore_puzzle` apply
   the same rule the bulk path does, or say why they should not.

4. **Fix `mark_in_book`'s DB branch** to convert a `str` book id, the way
   every other method in that module does, whatever else this card decides
   about its future.

## Acceptance criteria

- **AC-1** — a puzzle added to a book through `BookManager` is protected from
  Approve all, Reject all and Delete rejected, in both storage modes, and the
  reproduction above ends with the puzzle still in the store.
- **AC-2** — removing a puzzle from a book releases it, and it can then be
  rejected and deleted as normal.
- **AC-3** — a book never lists a puzzle id that is not in the store, before
  or after any bulk action.
- **AC-4** — the backfill sets `book_id` for every puzzle listed by an
  existing book, changes nothing else, and reports how many rows it touched.
- **AC-5** — per-puzzle Reject and Restore obey the same in-book rule as the
  bulk actions.
- **AC-6** — `mark_in_book(puzzle_id, "some-uuid-string")` works in DB mode.
- **AC-7** — CARD-068's bulk messages gain the "left alone: in a book" clause
  once the number can be trusted, and it is covered by a test that books a
  puzzle through `BookManager` rather than through `mark_in_book`.
- **AC-8** — the book builder stops offering a puzzle that another book
  already holds, and the `"unassigned"` filter means what its comment says.
- **AC-9** — `get_approved_puzzles` either returns a book's puzzles or is
  gone; it does not stay as a method that silently answers "none".

## Guardrails

- G-1: No puzzle is deleted by this card's backfill or by any repair step —
  it writes `book_id`, nothing else.
- G-2: The backfill is not run against the live database as part of this card
  (CARD-077's G-1 rule): it ships, it is tested against a copy, and the owner
  runs it.
- G-3: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`.
- G-4: Do not delete or weaken the existing in-book tests; several assert the
  guard using `mark_in_book`, and they stay true whichever option is taken.
- G-5: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** — (admin curation and books)
- **Components:** the admin panel's review surface and book manager
- **Trace:** none
