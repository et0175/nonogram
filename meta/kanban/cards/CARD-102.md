# CARD-102: The tests run without foreign keys; production runs with them

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/102-tests-enforce-foreign-keys
**Worktree:** —
**Source:** found 2026-09-21 while creating the development Postgres database and re-verifying CARD-100 and CARD-101 against it
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** tests/conftest.py (enforce FKs on every SQLite engine), tests/test_card_068_batch_curation.py, tests/test_card_100_book_membership.py, tests/test_card_101_mutable_json_columns.py (create the batch rows they reference), possibly src/nonogram/db/models.py + a migration (the `book_id` decision below)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

SQLite does not enforce foreign keys unless each connection asks it to.
Postgres always does. Every DB-mode test in this repository builds its own
SQLite engine and therefore runs with referential integrity **off**, while the
database those tests stand in for runs with it **on**.

This is not theoretical. The first attempt to re-verify CARD-100 against the
new development Postgres failed immediately::

    ForeignKeyViolation: insert or update on table "puzzles"
    violates foreign key constraint "fk_puzzles_batch_id_batches"
    DETAIL:  Key (batch_id)=(7c9e6679-…) is not present in table "batches".

Every one of those tests passes a **fabricated batch UUID** to `add_puzzle`.
Under SQLite nothing objects. Under Postgres none of them can insert a row.

**Measured 2026-09-21** by running the suite with a listener that issues
`PRAGMA foreign_keys=ON` for every SQLite connection:

| | |
|---|---|
| failures | 29 |
| errors | 14 |
| still passing | 3,563 |

All 43 are in the three DB-mode files — `test_card_068_batch_curation.py`,
`test_card_100_book_membership.py`, `test_card_101_mutable_json_columns.py`.
The rest of the suite is untouched because it never opens a database at all.
Every failure is the same insert, refused for the same reason.

So the suite's 3,606 green tests include a set that would fail against the
engine production uses, and the only reason CARD-100's and CARD-101's fixes
*are* known to work on Postgres is that they were re-verified by hand
afterwards.

## The related gap, which is the more interesting half

`puzzles.book_id` has **no foreign key at all**::

    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'), nullable=True)
    book_id  = Column(UUID(as_uuid=True), nullable=True)          # <- no FK

CARD-100 made that column the load-bearing record of book membership — every
in-book guard in the panel reads it. It can point at a book that does not
exist, and nothing anywhere will object. That is not hypothetical either: it
is precisely what `book_membership.backfill`'s `missing` and `contested`
verdicts are for, and they exist because the database will not answer the
question for us.

The schema's five foreign keys are on `generation_history` (×2),
`user_selected_books` (×3) and `puzzles.batch_id`. The one relationship the
admin panel actually depends on is the one without a constraint.

## What to implement

1. **Make the tests run the way production runs.** A single `PRAGMA
   foreign_keys=ON` listener, registered once in `tests/conftest.py` so it
   covers every SQLite engine any test builds — not per-file, or the next
   DB-mode test file inherits the old behaviour by default. (A working
   version of this listener is in the card's own investigation; it is four
   lines.)
2. **Fix the 43, by making them true rather than by loosening the check.**
   Each needs a real `batches` row for the id it uses. Prefer one shared
   helper over 43 local fixes — the fabricated-uuid habit is the defect, and
   a helper is what stops it recurring.
3. **Decide the `book_id` question** (below) and either add the constraint
   with a migration or write down why not.

## The decision this card needs (for the owner)

Should `puzzles.book_id` gain a foreign key to `books.id`?

- **(a) Add it, `ON DELETE SET NULL`.** Deleting a book releases its puzzles
  instead of leaving them pointing at nothing. The database then guarantees
  what CARD-100's guard assumes, and `backfill`'s `missing` verdict becomes
  a report about history rather than about an ongoing possibility. Needs a
  migration, and needs the existing rows to be clean before it can be added —
  which is exactly what the backfill produces, so the order is backfill
  first, constraint second.
- **(b) Add it, `ON DELETE RESTRICT`.** A book cannot be deleted while it
  holds puzzles. Safer for the data, but it turns "delete this book" into an
  error the admin panel has no wording for today.
- **(c) Leave it unconstrained** and rely on `BookManager` writing both sides
  (CARD-100) plus the backfill for repair. No migration, no risk to existing
  rows, and the guarantee stays a convention that one missed call site can
  break — which is the failure this whole sequence of cards came from.

**Recommendation: (a), but not in this card.** The constraint cannot be added
until the live data is repaired, and the backfill has not been run against
production yet. This card should do items 1 and 2 — which are pure test
fidelity and block nothing — and record the decision for a follow-up that
lands after the backfill has actually run.

## Acceptance criteria

- **AC-1** — every SQLite engine built by the test suite enforces foreign
  keys, and the enforcement is registered in one place.
- **AC-2** — the suite is green with enforcement on, and no test achieves
  that by removing a `batch_id` or by using `None` where it means to name a
  batch.
- **AC-3** — a test that inserts a puzzle against a non-existent batch fails,
  and is present deliberately, so the enforcement itself cannot be silently
  switched off later.
- **AC-4** — the `book_id` decision is recorded in this card, and if the
  answer is (a) or (b) a follow-up card exists naming the backfill as its
  precondition.

## Guardrails

- G-1: Do not remove or weaken a foreign key to make a test pass; the
  constraint is what production has.
- G-2: No schema migration in this card unless the decision above says
  otherwise — test fidelity and a data-model change are separate risks and
  should not merge together.
- G-3: Production code is not changed to accommodate the tests.
- G-4: Commit only your own files — explicit pathspecs.

## Found alongside, deliberately out of scope

The `books` table carries four columns no model declares —
`cover_image_url`, `pdf_url`, `page_count`, `kdp_asin` — left behind when
those values moved into the `book_metadata` JSON blob. All four are nullable,
so nothing breaks. Worth its own card if the drift is to be cleaned up; not
folded in here, because dropping columns is a migration and this card is
about tests.

## Architecture context

- **FR:** — (test fidelity)
- **Components:** the test suite; `nonogram.db.models`
- **Trace:** none
