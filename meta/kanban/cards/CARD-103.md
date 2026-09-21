# CARD-103: Constrain puzzles.book_id — after the backfill has run

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/103-constrain-puzzle-book-id
**Worktree:** —
**Source:** CARD-102's open decision, recorded there and deferred here
**Idea:** —
**Wave:** 1
**Depends on:** CARD-100 (the backfill) — and on the backfill having **actually been run** against the target database; CARD-102 (the tests enforce foreign keys at all)
**Touches:** src/nonogram/db/models.py (`Puzzle.book_id`), a new alembic migration, tests
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** the membership backfill has not been run against production (2026-09-21)

## Why

`puzzles.book_id` carries no foreign key::

    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'), nullable=True)
    book_id  = Column(UUID(as_uuid=True), nullable=True)          # <- no FK

CARD-100 made that column the load-bearing record of book membership: every
in-book guard in the admin panel reads it, and `BookManager` writes it as it
edits `Book.puzzle_ids`. The database does not check it, so a puzzle can name
a book that no longer exists and nothing will object.

The schema's five foreign keys are on `generation_history` and
`user_selected_books` and `puzzles.batch_id`. The one relationship the panel
actually depends on is the one without a constraint.

`book_membership.backfill`'s `missing` and `contested` verdicts exist because
the database cannot answer this question today. With a constraint, `missing`
becomes impossible going forward and the verdict is only ever a report about
history.

## Why this is a separate card, and why it is blocked

A foreign key cannot be added while rows violate it. Every puzzle in a book
created before CARD-100 carries `book_id = NULL` — those are fine — but any
row already pointing at a deleted book would refuse the migration. The
backfill is what makes the data clean, and **it has not been run against
production**. Adding the constraint before that is a migration that fails on
deploy, which is the worst place to discover it.

The order is: deploy CARD-100 → run the backfill → read its report → then this
card.

## The decision (recorded in CARD-102, restated here)

Recommended: **(a) `ON DELETE SET NULL`.** Deleting a book releases its
puzzles rather than leaving them pointing at nothing, which matches what
`remove_puzzle_from_book` already does one puzzle at a time.

The alternative considered was `ON DELETE RESTRICT` — a book cannot be deleted
while it holds puzzles. Safer for the data, but it turns "delete this book"
into an error the admin panel has no wording for, and `delete_book` has no
such path today. If RESTRICT is chosen, that wording is part of this card.

## What to implement

1. **Check first, in the target database**: are there rows whose `book_id`
   names a book that is not in `books`? The backfill's report answers it; a
   direct query is better, and it belongs in the card's notes before the
   migration is written.
2. `ForeignKey('books.id', ondelete='SET NULL')` on `Puzzle.book_id`.
3. An alembic migration adding the constraint, with a downgrade that drops it.
4. A test that a puzzle cannot name a book that does not exist, and one that
   deleting a book releases its puzzles rather than orphaning them.

## Acceptance criteria

- **AC-1** — inserting or updating a puzzle with a `book_id` that names no
  book is refused by the database.
- **AC-2** — deleting a book sets its puzzles' `book_id` to NULL, and those
  puzzles become deletable and rejectable again (CARD-100's rules resume).
- **AC-3** — the migration applies to a database whose rows are already
  clean, and its downgrade removes the constraint.
- **AC-4** — the backfill's `missing` verdict is documented as historical
  once this lands: it can still report rows written before the constraint,
  and can no longer describe anything new.

## Guardrails

- G-1: Do not run the migration against the live database from here — it
  ships, the owner runs it (CARD-077's G-1 rule).
- G-2: Do not delete or NULL any row to make the migration apply. If rows
  violate the constraint, report them and stop; deciding what a puzzle
  pointing at a missing book should become is the owner's call.
- G-3: Admin-only and schema-only; no change to what the guards do, which is
  CARD-100's work and is already done.
- G-4: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** — (admin curation; data integrity)
- **Components:** `nonogram.db.models`, the admin panel's book manager
- **Trace:** none
