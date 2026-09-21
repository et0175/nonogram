# CARD-107: A puzzle pointing at a book that is gone — the state the backfill cannot see

**Status:** review
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green, then reproduced and fixed against real Postgres
**Branch:** card/107-release-orphaned-book-ids
**Worktree:** ../PythonProject4-CARD-107
**Source:** a failed production deploy, 2026-09-21
**Idea:** —
**Wave:** 1
**Depends on:** CARD-100 (the backfill), CARD-103 (the constraint that exposed this)
**Touches:** src/nonogram/admin/book_membership.py, src/nonogram/admin/puzzle_review.py, tests
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.5d
**Merge commit:** —
**Blocked by:** —

## Why

The Render deploy of migration `009` failed::

    psycopg2.errors.ForeignKeyViolation: insert or update on table "puzzles"
    violates foreign key constraint "fk_puzzles_book_id_books"
    DETAIL:  Key (book_id)=(128c64f2-…) is not present in table "books".

The migration behaved exactly as written: it refused, changed nothing, left the
database at `008` and named the offending row. Because the *build* failed,
Render never swapped the service, so production kept running the old code.

**The check the owner was told to run first could not have caught it.**
`book_membership.backfill` walks books and their `puzzle_ids`. A puzzle whose
book has been *deleted* is never visited — the book is not there to iterate —
so the report comes back clean. "Re-run the backfill report first, the
migration refuses safely" was advice with a hole in it, and this is the hole.

How the rows got there: a book was deleted after the backfill ran. Nothing
cleared its puzzles' `book_id`, because the foreign key that would have done so
is the very thing the migration was adding.

## What this delivers

**`release_orphans(book_manager, puzzle_store, dry_run)`** — the query in the
other direction. It walks *puzzles*, finds those whose `book_id` names a book
that is not in `books`, and clears the column.

**NULL is not a choice made here.** The constraint says `ON DELETE SET NULL`,
so NULL is what these rows would already hold if the key had existed when their
book was deleted. The repair applies that rule to rows that predate it, rather
than inventing one — which is what CARD-103's G-2 reserved for the owner, and
is why this is a card rather than a quiet fix.

It is wired into `python -m nonogram.admin.book_membership`, so the command the
owner already knows now reports and repairs both directions, and still writes
nothing without `--write`.

## Verified by reproducing the deploy

Against the development Postgres, at revision `008` with an orphan planted:

```
ForeignKeyViolation: … violates constraint "fk_puzzles_book_id_books"
DETAIL:  Key (book_id)=(3ffcc31f-…) is not present in table "books".
  revision: 008
```

Then the repair, then the migration that had just failed:

```
would release 1 puzzle(s) from 1 book(s) that no longer exist.
  book no longer in the store: 3ffcc31f-…
Nothing was written. Re-run with --write to apply this.

released 1 puzzle(s) from 1 book(s) that no longer exist.

Running upgrade 008 -> 009 …
  revision: 009 (head)
```

## Two things found on the way

**A bug in the first cut of this code**, caught by CARD-100's command test: the
in-memory branch asked the module-level book manager which books exist, rather
than the one it was working with, so every booked puzzle looked orphaned. The
manager is passed in now, as `backfill` already did it.

**The orphan state is unreachable in a schema that has the constraint** —
deleting the book cascades and clears the column, which is the point of
`ON DELETE SET NULL`. So the test that builds it has to switch enforcement off
for the delete, and says so: it is reproducing the old schema, not working
around the new one.

## Acceptance criteria

- **AC-1** — the report names every puzzle whose book is gone, and each missing
  book once however many puzzles point at it.
- **AC-2** — the repair clears `book_id` and changes no other column, and no
  puzzle or book row is deleted.
- **AC-3** — a dry run writes nothing; a second run reports nothing left.
- **AC-4** — a puzzle whose book exists, and one in no book, are untouched.
- **AC-5** — migration `009` applies after the repair.

## Guardrails

- G-1: Not run against production from here. It ships; the owner runs it.
- G-2: No row is deleted — this clears a column, nothing more.
- G-3: `backfill` is not changed. Its blind spot is inherent to walking books,
  and the fix is the query in the other direction, not a patch to that loop.

## Tests

`tests/test_card_107_orphaned_book_ids.py`, 9 tests, including one that pins
**the backfill's blindness itself** — a deliberate record that the older tool
reports a clean bill in this state, so nobody later mistakes its silence for
assurance.

**Full suite: 3,652 passed, 0 failed.**

## A hazard worth writing down

Running the suite with `DATABASE_URL` exported points DB-mode tests at that
database. It happened during this card: four e2e tests failed after the dev
database was emptied mid-run, and an earlier run left a stray book row behind.
Harmless against a scratch database, and not harmless against a real one. The
suite should probably refuse to run against a `DATABASE_URL` it did not create
— worth its own card.
