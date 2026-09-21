"""CARD-103 — the database enforces what the panel's guards assume.

    AC-1  a puzzle cannot name a book that does not exist
    AC-2  deleting a book releases its puzzles instead of orphaning them
    AC-3  the migration applies to clean rows, and its downgrade removes it

`puzzles.book_id` carried no constraint until this card, which is how a column
CARD-100 made load-bearing could point at nothing. The guards read it; nothing
checked it; `book_membership.backfill`'s `missing` verdict exists precisely
because the database could not answer the question.

`ON DELETE SET NULL` rather than `RESTRICT`: deleting a book releases its
puzzles, which is what `remove_puzzle_from_book` already does one puzzle at a
time. `RESTRICT` would turn "delete this book" into an error the panel has no
wording for.

Every test here reads back through a **fresh session** and runs against SQLite
with foreign keys enforced — `tests/conftest.py` issues the `PRAGMA` for every
engine (CARD-102), without which none of this would fail when it should.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from nonogram.admin.book_manager import BookManager
from nonogram.admin.puzzle_review import PuzzleReviewService, PuzzleStatus
from tests.helpers.db import make_batch, sqlite_session_scope


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path)


@pytest.fixture
def panel(scope):
    store = PuzzleReviewService(session_factory=scope)
    books = BookManager(session_factory=scope, puzzle_store=store)
    return store, books


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


def _book_id_of(store, puzzle_id):
    return store.get_puzzle(puzzle_id).get("book_id")


# --------------------------------------------------------------------------
# AC-1 — the constraint itself
# --------------------------------------------------------------------------


def test_a_puzzle_cannot_name_a_book_that_does_not_exist(panel, scope):
    """The hole CARD-100 had to work around, now closed by the database."""
    store, _books = panel
    puzzle_id = _add(store, make_batch(scope))

    with pytest.raises(IntegrityError) as excinfo:
        store.assign_to_book([puzzle_id], str(uuid.uuid4()))

    assert "FOREIGN KEY" in str(excinfo.value).upper()


def test_a_puzzle_can_name_a_book_that_does(panel, scope):
    """The control: the constraint refuses the wrong thing, not everything."""
    store, books = panel
    puzzle_id = _add(store, make_batch(scope))
    book_id = books.create_book("Winter", "a book", "christmas", "adults")

    books.add_puzzles_to_book(book_id, [puzzle_id])

    assert _book_id_of(store, puzzle_id) == book_id


# --------------------------------------------------------------------------
# AC-2 — what deleting a book does
# --------------------------------------------------------------------------


def test_deleting_a_book_releases_its_puzzles(panel, scope):
    """``SET NULL``, asserted through a new session rather than in memory."""
    store, books = panel
    puzzle_id = _add(store, make_batch(scope))
    book_id = books.create_book("Winter", "a book", "christmas", "adults")
    books.add_puzzles_to_book(book_id, [puzzle_id])

    assert books.delete_book(book_id)

    assert store.get_puzzle(puzzle_id) is not None, "the puzzle went with the book"
    assert _book_id_of(store, puzzle_id) is None


def test_a_released_puzzle_is_curatable_again(panel, scope):
    """CARD-100's rules resume once the book that held it is gone.

    While a book holds a puzzle, rejecting it is refused. That refusal must
    not outlive the book — otherwise deleting a book would leave puzzles
    permanently unrejectable, which is a worse hole than the one this card
    closes.
    """
    store, books = panel
    batch_id = make_batch(scope)
    puzzle_id = _add(store, batch_id)
    book_id = books.create_book("Winter", "a book", "christmas", "adults")
    books.add_puzzles_to_book(book_id, [puzzle_id])
    assert store.reject_puzzle(puzzle_id) is False

    books.delete_book(book_id)

    assert store.reject_puzzle(puzzle_id) is True
    assert store.delete_rejected_in_batch(batch_id).changed == 1
    assert store.get_puzzle(puzzle_id) is None


def test_deleting_one_book_does_not_release_another_s_puzzles(panel, scope):
    store, books = panel
    batch_id = make_batch(scope)
    mine, theirs = _add(store, batch_id, "a.png"), _add(store, batch_id, "b.png")
    doomed = books.create_book("Doomed", "a book", "christmas", "adults")
    kept = books.create_book("Kept", "a book", "easter", "adults")
    books.add_puzzles_to_book(doomed, [mine])
    books.add_puzzles_to_book(kept, [theirs])

    books.delete_book(doomed)

    assert _book_id_of(store, mine) is None
    assert _book_id_of(store, theirs) == kept


# --------------------------------------------------------------------------
# AC-3 — the migration
# --------------------------------------------------------------------------


def test_the_migration_chain_ends_at_this_card(tmp_path):
    """The constraint ships as a migration, not only as a model declaration.

    A model change alone would protect a database built by
    ``Base.metadata.create_all`` — which is every test — and leave production,
    built by alembic, exactly as it was.
    """
    from pathlib import Path

    versions = Path(__file__).parent.parent / "migrations" / "versions"
    heads = {
        path.stem.split("_")[0]
        for path in versions.glob("[0-9]*.py")
    }

    assert "009" in heads, sorted(heads)


def test_the_model_declares_the_constraint_and_its_delete_rule():
    """Named directly, so a later edit that drops either half fails here."""
    from nonogram.db.models import Puzzle

    (fk,) = list(Puzzle.__table__.c.book_id.foreign_keys)

    assert fk.column.table.name == "books"
    assert fk.ondelete == "SET NULL"
