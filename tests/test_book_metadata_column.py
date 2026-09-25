"""The book's metadata column is written, not SQLAlchemy's ``MetaData``.

Reported from production, 2026-09-25: generating a PDF for a stored book
failed with ``'MetaData' object does not support item assignment``.

``Book`` is a declarative model, so ``Book.metadata`` is a **reserved
attribute** — it is the declarative base's :class:`sqlalchemy.MetaData`, the
schema registry, and it exists on every model whether or not that model has a
column of its own by that name. This book's column is ``book_metadata``
(``models.py:118``), and three writers reached for ``book_row.metadata``
instead:

* ``set_cover_image`` — ``cover_image_url``
* ``set_pdf_url``     — ``pdf_url``
* ``set_kdp_asin``    — ``kdp_asin``

which is exactly the three keys ``book_metadata``'s own column comment lists.

Two things made it invisible until a deploy:

* the guard above each write is ``if book_row.metadata is None`` — and a
  ``MetaData`` instance is never ``None``, so the guard never fired and never
  reported anything;
* **in-memory mode is unaffected.** There a book's metadata is a plain dict, so
  every one of these paths works. Only the stored path breaks, and only at the
  moment of writing.

These tests therefore run in DB mode on purpose. A memory-mode test of the same
three calls passes against the bug.
"""

from __future__ import annotations

import pytest

from nonogram.admin.book_manager import BookManager
from tests.helpers.db import sqlite_session_scope


@pytest.fixture()
def stored_book(tmp_path):
    """A book in a real database, and the manager that speaks to it.

    SQLite rather than Postgres, following ``tests/test_book_floor.py``: the
    defect is in which attribute the ORM writes, not in the backend, and a
    sqlite file needs no server to be running for this to fail.
    """
    manager = BookManager(session_factory=sqlite_session_scope(tmp_path, "meta.db"))
    book_id = manager.create_book(
        title="Метадані",
        description="a book whose metadata column is written",
        theme="generic",
        target_audience="adults",
    )
    return manager, book_id


class TestBookMetadata_WritesReachTheColumn:
    """Each writer lands in ``book_metadata`` and survives a fresh read."""

    def test_the_pdf_url_is_stored(self, stored_book) -> None:
        """The one production reported: generate-pdf calls this."""
        manager, book_id = stored_book

        assert manager.set_pdf_url(book_id, "PDF generated on 2026-09-25") is True

        book = manager.get_book(book_id)
        assert book.metadata.pdf_url == "PDF generated on 2026-09-25"

    def test_the_cover_image_url_is_stored(self, stored_book) -> None:
        manager, book_id = stored_book

        assert manager.set_cover_image(book_id, "/covers/1.png") is True

        assert manager.get_book(book_id).metadata.cover_image_url == "/covers/1.png"

    def test_the_kdp_asin_is_stored(self, stored_book) -> None:
        manager, book_id = stored_book

        assert manager.set_kdp_asin(book_id, "B0TEST") is True

        assert manager.get_book(book_id).metadata.kdp_asin == "B0TEST"

    def test_the_three_writers_do_not_overwrite_each_other(self, stored_book) -> None:
        """Each writes one key into the same dict, so the last must not win.

        Written because the fix replaces a read of a shared, always-present
        object with a read of a per-book column: if a writer reassigned the
        column instead of setting a key in it, every test above would still
        pass on its own.
        """
        manager, book_id = stored_book

        manager.set_cover_image(book_id, "/covers/1.png")
        manager.set_pdf_url(book_id, "generated")
        manager.set_kdp_asin(book_id, "B0TEST")

        stored = manager.get_book(book_id).metadata
        assert stored.cover_image_url == "/covers/1.png"
        assert stored.pdf_url == "generated"
        assert stored.kdp_asin == "B0TEST"

    def test_a_missing_book_is_refused_not_raised(self, stored_book) -> None:
        """The early return stays an answer, not an exception."""
        manager, _ = stored_book

        absent = "00000000-0000-4000-8000-000000000000"
        assert manager.set_pdf_url(absent, "generated") is False


class TestBookMetadata_TheReservedAttributeIsNotWritten:
    """The declarative ``MetaData`` is left alone.

    This is the assertion that actually refutes the bug rather than reporting
    its symptom: the writers must not touch ``Book.metadata``, whose tables are
    the schema itself.
    """

    def test_the_schema_registry_still_holds_the_books_table(
        self, stored_book
    ) -> None:
        from nonogram.db.models import Book

        manager, book_id = stored_book
        manager.set_pdf_url(book_id, "generated")

        assert Book.metadata.tables, "the declarative MetaData lost its tables"
        assert "books" in Book.metadata.tables
