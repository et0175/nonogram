"""CARD-107 — a puzzle pointing at a book that is gone.

    AC-1  the report finds puzzles whose book no longer exists
    AC-2  the repair sets those to NULL, and nothing else
    AC-3  it is idempotent, and a dry run writes nothing
    AC-4  migration 009 applies once the repair has run

Found by a failed production deploy on 2026-09-21::

    psycopg2.errors.ForeignKeyViolation: insert or update on table "puzzles"
    violates foreign key constraint "fk_puzzles_book_id_books"
    DETAIL:  Key (book_id)=(128c64f2-…) is not present in table "books".

The migration refused and changed nothing, which is what it was built to do.
But the check the owner was told to run first — ``book_membership.backfill`` —
**cannot see this state**. It iterates books and their ``puzzle_ids``, so a
puzzle whose book has been deleted is never visited: the book is not there to
iterate. The blind spot is exactly where the failure lives.

NULL is not a guess. The constraint being added says ``ON DELETE SET NULL``, so
NULL is what these rows would already hold if the key had existed when the book
was deleted. This applies that rule retroactively rather than inventing one.
"""

from __future__ import annotations

import uuid

import pytest

from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_membership import backfill, release_orphans
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import make_batch, make_book, sqlite_session_scope


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path)


@pytest.fixture
def panel(scope):
    store = PuzzleReviewService(session_factory=scope)
    return store, BookManager(session_factory=scope, puzzle_store=store)


def _add(store, batch_id, name="p.png"):
    return store.add_puzzle(
        grid=[[True] * 10 for _ in range(10)],
        clues_rows=[[10]] * 10,
        clues_cols=[[10]] * 10,
        width=10,
        height=10,
        theme="test",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=batch_id,
        source_image=name,
    )


def _delete_book_the_old_way(scope, book_id):
    """Remove a book row without the constraint noticing.

    The orphan state is **unreachable** in a schema that has CARD-103's
    foreign key: deleting the book cascades ``ON DELETE SET NULL`` and clears
    the column, which is the whole point of the constraint. It exists only in a
    database that predates it — production, at revision 008 — so the setup
    switches enforcement off for the delete, exactly as the old schema was.
    """
    from sqlalchemy import text

    from nonogram.db.models import Book

    with scope() as db:
        db.execute(text("PRAGMA foreign_keys=OFF"))
        db.query(Book).filter(Book.id == uuid.UUID(book_id)).delete()
        db.commit()
        db.execute(text("PRAGMA foreign_keys=ON"))


def _orphan(store, scope, batch_id):
    """A puzzle whose book has been deleted — production's exact state."""
    puzzle_id = _add(store, batch_id)
    book_id = make_book(scope, title="Since deleted")
    store.assign_to_book([puzzle_id], book_id)
    _delete_book_the_old_way(scope, book_id)
    return puzzle_id, book_id


# --------------------------------------------------------------------------
# AC-1 — the state the backfill cannot see
# --------------------------------------------------------------------------


def test_the_backfill_cannot_see_an_orphaned_puzzle(panel, scope):
    """Pinned as the reason this card exists, not as a defect to fix there.

    ``backfill`` walks books. A puzzle whose book is gone is not reachable that
    way, so it reports a clean bill — which is why "re-run the backfill first"
    did not prevent the failed deploy.
    """
    store, books = panel
    _orphan(store, scope, make_batch(scope))

    outcome = backfill(books, store, dry_run=True)

    assert outcome.repaired == 0
    assert not outcome.needs_an_operator, "the backfill claims nothing is wrong"


def test_release_orphans_finds_it(panel, scope):
    store, books = panel
    puzzle_id, book_id = _orphan(store, scope, make_batch(scope))

    found = release_orphans(books, store, dry_run=True)

    assert found.released == 1
    assert found.books == (book_id,)
    assert store.get_puzzle(puzzle_id)["book_id"] == book_id, "a dry run wrote"


def test_a_puzzle_whose_book_exists_is_left_alone(panel, scope):
    store, books = panel
    puzzle_id = _add(store, make_batch(scope))
    book_id = books.create_book("Kept", "a book", "christmas", "adults")
    books.add_puzzles_to_book(book_id, [puzzle_id])

    found = release_orphans(books, store, dry_run=True)

    assert found.released == 0
    assert store.get_puzzle(puzzle_id)["book_id"] == book_id


def test_a_puzzle_in_no_book_is_left_alone(panel, scope):
    store, books = panel
    puzzle_id = _add(store, make_batch(scope))

    assert release_orphans(books, store, dry_run=True).released == 0
    assert store.get_puzzle(puzzle_id)["book_id"] is None


# --------------------------------------------------------------------------
# AC-2 / AC-3 — the repair
# --------------------------------------------------------------------------


def test_the_repair_nulls_the_column_and_nothing_else(panel, scope):
    store, books = panel
    puzzle_id, _ = _orphan(store, scope, make_batch(scope))
    before = dict(store.get_puzzle(puzzle_id))

    release_orphans(books, store, dry_run=False)

    after = store.get_puzzle(puzzle_id)
    assert after["book_id"] is None
    assert {k for k in before if before[k] != after.get(k)} == {"book_id"}


def test_the_repair_is_idempotent(panel, scope):
    store, books = panel
    _orphan(store, scope, make_batch(scope))
    release_orphans(books, store, dry_run=False)

    assert release_orphans(books, store, dry_run=False).released == 0


def test_the_repair_leaves_the_other_puzzles_alone(panel, scope):
    store, books = panel
    batch_id = make_batch(scope)
    orphaned, _ = _orphan(store, scope, batch_id)
    kept = _add(store, batch_id, "kept.png")
    book_id = books.create_book("Kept", "a book", "christmas", "adults")
    books.add_puzzles_to_book(book_id, [kept])
    loose = _add(store, batch_id, "loose.png")

    release_orphans(books, store, dry_run=False)

    assert store.get_puzzle(orphaned)["book_id"] is None
    assert store.get_puzzle(kept)["book_id"] == book_id
    assert store.get_puzzle(loose)["book_id"] is None
    assert all(store.get_puzzle(p) is not None for p in (orphaned, kept, loose))


def test_several_puzzles_of_one_missing_book_are_reported_once(panel, scope):
    store, books = panel
    batch_id = make_batch(scope)
    ids = [_add(store, batch_id, f"{n}.png") for n in range(3)]
    book_id = make_book(scope, title="Since deleted")
    store.assign_to_book(ids, book_id)
    _delete_book_the_old_way(scope, book_id)

    found = release_orphans(books, store, dry_run=False)

    assert found.released == 3
    assert found.books == (book_id,), "one missing book, named once"


# --------------------------------------------------------------------------
# AC-4 — the constraint applies afterwards
# --------------------------------------------------------------------------


def test_the_column_can_take_the_constraint_after_the_repair(panel, scope):
    """The point of the whole exercise, checked rather than assumed.

    SQLite enforces foreign keys here (CARD-102), and ``Base.metadata`` already
    carries the constraint, so a row that would fail migration 009 is a row
    this store cannot re-assign afterwards.
    """
    store, books = panel
    puzzle_id, _ = _orphan(store, scope, make_batch(scope))

    release_orphans(books, store, dry_run=False)

    assert store.get_puzzle(puzzle_id)["book_id"] is None
    book_id = books.create_book("New", "a book", "christmas", "adults")
    books.add_puzzles_to_book(book_id, [puzzle_id])
    assert store.get_puzzle(puzzle_id)["book_id"] == book_id
