"""CARD-101 — a JSON column mutated in place is a change, and is written.

    AC-1  moving a puzzle up or down survives a new session
    AC-2  setting, changing and clearing a title each survive
    AC-3  what already worked keeps working, in DB mode
    AC-4  a test fails if the columns stop being mutation-tracked

Every assertion reads the row back through a **fresh session**. That is not
ceremony: the bug is invisible while the original object is still in the
session's identity map, because the in-memory object does hold the change. It
is the write that never happens.

Why this was not one bug but three shapes of one
------------------------------------------------
Measured before the fix, against SQLite:

* ``move_puzzle_up`` / ``move_puzzle_down`` never persisted — they read the
  column's own list, swapped two entries in place and assigned it back to the
  same attribute, which SQLAlchemy compares by identity and sees as nothing.
* ``set_puzzle_title`` persisted **exactly once per book**: while the column
  was still ``NULL``, ``book_row.puzzle_titles or {}`` built a *new* dict and
  that assignment was seen. Every write afterwards mutated the dict the column
  by then held, and vanished.
* ``reorder_puzzles`` was fine all along — it assigns the caller's list, a
  different object — and ``add_puzzles_to_book`` concatenates into a new one.

A bug that works the first time, and only for some callers, is why the fix is
``MutableList``/``MutableDict`` on the columns rather than a new object at each
assignment: the pattern that fails is the one that looks most obviously
correct.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import pytest

from nonogram.admin.book_manager import BookManager
from nonogram.admin.puzzle_review import PuzzleReviewService


@pytest.fixture
def session_factory(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from nonogram.db.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'books.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    @contextmanager
    def scope():
        db = factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return scope


@pytest.fixture
def books(session_factory):
    """A DB-backed manager — the mode this bug only ever affected."""
    store = PuzzleReviewService(session_factory=session_factory)
    return BookManager(session_factory=session_factory, puzzle_store=store)


@pytest.fixture
def book(books):
    """A book of three puzzles, in a known order."""
    store = books.puzzle_store
    ids = [
        store.add_puzzle(
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
            batch_id="7c9e6679-7425-40de-944b-e07fc1f90ae7",
            source_image=f"{name}.png",
        )
        for name in ("a", "b", "c")
    ]
    book_id = books.create_book("Winter", "a book", "christmas", "adults")
    books.add_puzzles_to_book(book_id, ids)
    return book_id, ids


def _order(books, book_id):
    """The stored order, read back through a session of its own."""
    return books.get_book(book_id).puzzle_ids


# --------------------------------------------------------------------------
# AC-1 — the arrange page's buttons
# --------------------------------------------------------------------------


def test_moving_a_puzzle_up_survives(books, book):
    book_id, (a, b, c) = book

    assert books.move_puzzle_up(book_id, c)

    assert _order(books, book_id) == [a, c, b]


def test_moving_a_puzzle_down_survives(books, book):
    book_id, (a, b, c) = book

    assert books.move_puzzle_down(book_id, a)

    assert _order(books, book_id) == [b, a, c]


def test_a_sequence_of_moves_lands_where_it_says(books, book):
    """Each move reads what the last one wrote, not what it started with."""
    book_id, (a, b, c) = book

    books.move_puzzle_down(book_id, a)   # b a c
    books.move_puzzle_down(book_id, a)   # b c a
    books.move_puzzle_up(book_id, c)     # c b a

    assert _order(books, book_id) == [c, b, a]


def test_moving_past_the_end_is_still_refused(books, book):
    book_id, (a, _b, c) = book

    assert books.move_puzzle_up(book_id, a) is False
    assert books.move_puzzle_down(book_id, c) is False


# --------------------------------------------------------------------------
# AC-2 — the three title paths, because the first one always worked
# --------------------------------------------------------------------------


def test_setting_the_first_title_survives(books, book):
    book_id, (a, _b, _c) = book

    assert books.set_puzzle_title(book_id, a, "Snowfall")

    assert books.get_puzzle_title(book_id, a) == "Snowfall"


def test_changing_an_existing_title_survives(books, book):
    """The path the first write hid: by now the column holds a real dict."""
    book_id, (a, _b, _c) = book
    books.set_puzzle_title(book_id, a, "Snowfall")

    assert books.set_puzzle_title(book_id, a, "Second try")

    assert books.get_puzzle_title(book_id, a) == "Second try"


def test_clearing_a_title_survives(books, book):
    book_id, (a, _b, _c) = book
    books.set_puzzle_title(book_id, a, "Snowfall")

    assert books.set_puzzle_title(book_id, a, "")

    assert books.get_puzzle_title(book_id, a) is None


def test_a_second_puzzles_title_does_not_disturb_the_first(books, book):
    book_id, (a, b, _c) = book
    books.set_puzzle_title(book_id, a, "Snowfall")

    books.set_puzzle_title(book_id, b, "Thaw")

    assert books.get_puzzle_title(book_id, a) == "Snowfall"
    assert books.get_puzzle_title(book_id, b) == "Thaw"


# --------------------------------------------------------------------------
# AC-3 — and the page count, which had the same fault
# --------------------------------------------------------------------------


def test_reorder_still_works(books, book):
    book_id, (a, b, c) = book

    assert books.reorder_puzzles(book_id, [c, b, a])

    assert _order(books, book_id) == [c, b, a]


def test_removing_a_puzzle_still_works(books, book):
    book_id, (a, b, c) = book

    assert books.remove_puzzle_from_book(book_id, b)

    assert _order(books, book_id) == [a, c]


def test_the_page_count_follows_the_puzzles(books, book):
    """``book_metadata['page_count']`` was assigned into in place too."""
    book_id, _ids = book
    store = books.puzzle_store
    more = [
        store.add_puzzle(
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
            batch_id="7c9e6679-7425-40de-944b-e07fc1f90ae7",
            source_image=f"extra{n}.png",
        )
        for n in range(3)
    ]

    books.add_puzzles_to_book(book_id, more)

    assert books.get_book(book_id).metadata.page_count == 3


# --------------------------------------------------------------------------
# AC-4 — the guard: these columns are tracked, or this fails
# --------------------------------------------------------------------------


def test_a_list_column_mutated_in_place_is_written(books, book, session_factory):
    """The pattern that used to lose data, asserted to work.

    This is the regression guard for the fix itself. Unwrap the column and it
    fails — which is the point, since the losing pattern is the one that looks
    correct and nothing in a diff would show it coming back.
    """
    from nonogram.db.models import Book as DBBook
    import uuid as uuid_module

    book_id, (a, _b, _c) = book

    with session_factory() as db:
        row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
        row.puzzle_ids.append("a-new-id")

    assert "a-new-id" in _order(books, book_id)


def test_a_dict_column_mutated_in_place_is_written(books, book, session_factory):
    from nonogram.db.models import Book as DBBook
    import uuid as uuid_module

    book_id, (a, _b, _c) = book

    with session_factory() as db:
        row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
        row.puzzle_titles[a] = "Written in place"

    assert books.get_puzzle_title(book_id, a) == "Written in place"


def test_the_book_columns_hand_back_tracked_containers(books, book, session_factory):
    """Named directly, so the reason survives someone tidying the model.

    A plain ``JSON`` column hands back an ordinary ``list``/``dict``; a wrapped
    one hands back a ``MutableList``/``MutableDict`` that tells the session
    when it changes. Asserting the type says *why* the tests above pass.
    """
    import uuid as uuid_module

    from sqlalchemy.ext.mutable import MutableDict, MutableList

    from nonogram.db.models import Book as DBBook

    book_id, (a, _b, _c) = book
    books.set_puzzle_title(book_id, a, "Snowfall")

    with session_factory() as db:
        row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()

        assert isinstance(row.puzzle_ids, MutableList)
        assert isinstance(row.puzzle_titles, MutableDict)
        assert isinstance(row.book_metadata, MutableDict)


def test_two_books_do_not_share_one_container(books):
    """Each book's containers are its own, now that they are tracked.

    The obvious worry when wrapping these columns is that ``default=[]`` hands
    every new row the same object, so a tracked container shared by two rows
    would carry one book's puzzles into another. **Measured: it does not** —
    reverting the defaults to ``[]``/``{}`` keeps this test passing, because
    the value is serialised per insert and rebuilt per load. The columns were
    changed to ``default=list``/``default=dict`` anyway, as the form that
    cannot be misread, but that is tidiness rather than a fix.

    The test stays because the property it pins is worth pinning whatever the
    reason: one book's edits never reach another.
    """
    first = books.create_book("Winter", "a book", "christmas", "adults")
    second = books.create_book("Spring", "another", "easter", "adults")

    store = books.puzzle_store
    puzzle_id = store.add_puzzle(
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
        batch_id="7c9e6679-7425-40de-944b-e07fc1f90ae7",
        source_image="p.png",
    )
    books.add_puzzles_to_book(first, [puzzle_id])
    books.set_puzzle_title(first, puzzle_id, "Snowfall")

    assert books.get_book(second).puzzle_ids == []
    assert books.get_puzzle_title(second, puzzle_id) is None
