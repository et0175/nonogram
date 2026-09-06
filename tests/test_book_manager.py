"""Tests for book management service."""

import pytest
from src.nonogram.admin.book_manager import (
    BookManager,
    BookStatus,
    BookMetadata,
    Book,
    get_book_manager,
)


@pytest.fixture
def book_manager():
    """Get a fresh book manager for testing."""
    return BookManager()


class TestBookCreation:
    """Test book creation."""

    def test_create_book_valid(self, book_manager):
        """Create a book with valid parameters."""
        book_id = book_manager.create_book(
            title="Christmas Puzzles",
            description="Holiday themed nonograms",
            theme="christmas",
            target_audience="seniors",
        )

        assert book_id is not None
        assert book_id.startswith("book_")

    def test_created_book_is_draft(self, book_manager):
        """New books start in draft status."""
        book_id = book_manager.create_book(
            title="Christmas Puzzles",
            description="Holiday themed nonograms",
            theme="christmas",
            target_audience="seniors",
        )

        book = book_manager.get_book(book_id)
        assert book.status == BookStatus.DRAFT.value

    def test_create_book_invalid_title(self, book_manager):
        """Reject book with empty title."""
        with pytest.raises(ValueError):
            book_manager.create_book(
                title="",
                description="Description",
                theme="christmas",
                target_audience="seniors",
            )

    def test_create_book_invalid_theme(self, book_manager):
        """Reject book with invalid theme."""
        with pytest.raises(ValueError):
            book_manager.create_book(
                title="Book",
                description="Description",
                theme="invalid_theme",
                target_audience="seniors",
            )

    def test_create_multiple_books(self, book_manager):
        """Create multiple books with unique IDs."""
        id1 = book_manager.create_book(
            title="Book 1",
            description="Description 1",
            theme="christmas",
            target_audience="seniors",
        )
        id2 = book_manager.create_book(
            title="Book 2",
            description="Description 2",
            theme="halloween",
            target_audience="kids",
        )

        assert id1 != id2


class TestPuzzleManagement:
    """Test adding/removing puzzles from books."""

    def test_add_puzzles_to_book(self, book_manager):
        """Add puzzles to a book."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        puzzle_ids = ["puzzle_000001", "puzzle_000002", "puzzle_000003"]
        result = book_manager.add_puzzles_to_book(book_id, puzzle_ids)

        assert result is True
        book = book_manager.get_book(book_id)
        assert len(book.puzzle_ids) == 3
        assert all(pid in book.puzzle_ids for pid in puzzle_ids)

    def test_add_puzzles_updates_page_count(self, book_manager):
        """Page count updates when puzzles added."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        book_manager.add_puzzles_to_book(
            book_id, ["puzzle_000001", "puzzle_000002", "puzzle_000003", "puzzle_000004"]
        )

        book = book_manager.get_book(book_id)
        assert book.metadata.page_count == 2  # 4 puzzles / 2 per page

    def test_add_puzzles_prevents_duplicates(self, book_manager):
        """Adding duplicate puzzles doesn't create duplicates."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        book_manager.add_puzzles_to_book(book_id, ["puzzle_000001", "puzzle_000002"])
        book_manager.add_puzzles_to_book(book_id, ["puzzle_000001", "puzzle_000003"])

        book = book_manager.get_book(book_id)
        assert len(book.puzzle_ids) == 3

    def test_add_empty_puzzles_rejected(self, book_manager):
        """Cannot add empty puzzle list."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        with pytest.raises(ValueError):
            book_manager.add_puzzles_to_book(book_id, [])

    def test_remove_puzzle_from_book(self, book_manager):
        """Remove a puzzle from a book."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        puzzle_ids = ["puzzle_000001", "puzzle_000002", "puzzle_000003"]
        book_manager.add_puzzles_to_book(book_id, puzzle_ids)

        result = book_manager.remove_puzzle_from_book(book_id, "puzzle_000002")

        assert result is True
        book = book_manager.get_book(book_id)
        assert len(book.puzzle_ids) == 2
        assert "puzzle_000002" not in book.puzzle_ids

    def test_remove_nonexistent_puzzle(self, book_manager):
        """Removing non-existent puzzle returns False."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        result = book_manager.remove_puzzle_from_book(book_id, "nonexistent")

        assert result is False


class TestPuzzleReordering:
    """Test reordering puzzles in a book."""

    def test_reorder_puzzles(self, book_manager):
        """Reorder puzzles in a book."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        original = ["puzzle_000001", "puzzle_000002", "puzzle_000003"]
        book_manager.add_puzzles_to_book(book_id, original)

        new_order = ["puzzle_000003", "puzzle_000001", "puzzle_000002"]
        result = book_manager.reorder_puzzles(book_id, new_order)

        assert result is True
        book = book_manager.get_book(book_id)
        assert book.puzzle_ids == new_order

    def test_reorder_invalid_puzzle_ids(self, book_manager):
        """Cannot reorder with different puzzle set."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        book_manager.add_puzzles_to_book(
            book_id, ["puzzle_000001", "puzzle_000002"]
        )

        with pytest.raises(ValueError):
            book_manager.reorder_puzzles(
                book_id, ["puzzle_000001", "puzzle_000003"]
            )


class TestBookStatus:
    """Test book status transitions."""

    def test_set_book_status(self, book_manager):
        """Update book status."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        book_manager.add_puzzles_to_book(book_id, ["puzzle_000001"])

        result = book_manager.set_book_status(book_id, BookStatus.READY_FOR_PDF.value)

        assert result is True
        book = book_manager.get_book(book_id)
        assert book.status == BookStatus.READY_FOR_PDF.value

    def test_set_invalid_status(self, book_manager):
        """Reject invalid status."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        with pytest.raises(ValueError):
            book_manager.set_book_status(book_id, "invalid_status")

    def test_cannot_advance_empty_book(self, book_manager):
        """Cannot advance status without puzzles."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        with pytest.raises(ValueError):
            book_manager.set_book_status(book_id, BookStatus.READY_FOR_PDF.value)

    def test_cannot_change_published_book_status(self, book_manager):
        """Cannot change status of published book."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        book_manager.add_puzzles_to_book(book_id, ["puzzle_000001"])
        book_manager.set_book_status(book_id, BookStatus.PUBLISHED.value)

        with pytest.raises(ValueError):
            book_manager.set_book_status(book_id, BookStatus.DRAFT.value)


class TestBookMetadata:
    """Test setting book metadata."""

    def test_set_cover_image(self, book_manager):
        """Set cover image URL."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        result = book_manager.set_cover_image(book_id, "https://example.com/cover.jpg")

        assert result is True
        book = book_manager.get_book(book_id)
        assert book.metadata.cover_image_url == "https://example.com/cover.jpg"

    def test_set_pdf_url(self, book_manager):
        """Set PDF URL."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        result = book_manager.set_pdf_url(book_id, "https://example.com/book.pdf")

        assert result is True
        book = book_manager.get_book(book_id)
        assert book.metadata.pdf_url == "https://example.com/book.pdf"

    def test_set_kdp_asin(self, book_manager):
        """Set KDP ASIN."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        result = book_manager.set_kdp_asin(book_id, "B0ABC123XYZ")

        assert result is True
        book = book_manager.get_book(book_id)
        assert book.metadata.kdp_asin == "B0ABC123XYZ"


class TestBookRetrieval:
    """Test retrieving books."""

    def test_get_book(self, book_manager):
        """Get a book by ID."""
        book_id = book_manager.create_book(
            title="Book",
            description="Description",
            theme="christmas",
            target_audience="seniors",
        )

        book = book_manager.get_book(book_id)

        assert book is not None
        assert book.book_id == book_id
        assert book.metadata.title == "Book"

    def test_get_nonexistent_book(self, book_manager):
        """Getting non-existent book returns None."""
        book = book_manager.get_book("nonexistent")

        assert book is None

    def test_get_books_by_status(self, book_manager):
        """Get all books with a given status."""
        # Create books
        id1 = book_manager.create_book(
            title="Book 1",
            description="Description 1",
            theme="christmas",
            target_audience="seniors",
        )
        id2 = book_manager.create_book(
            title="Book 2",
            description="Description 2",
            theme="halloween",
            target_audience="kids",
        )

        # Change status of first book
        book_manager.add_puzzles_to_book(id1, ["puzzle_000001"])
        book_manager.set_book_status(id1, BookStatus.READY_FOR_PDF.value)

        # Get books by status
        draft_books = book_manager.get_books_by_status(BookStatus.DRAFT.value)
        ready_books = book_manager.get_books_by_status(BookStatus.READY_FOR_PDF.value)

        assert len(draft_books) == 1
        assert draft_books[0].book_id == id2
        assert len(ready_books) == 1
        assert ready_books[0].book_id == id1

    def test_get_all_books(self, book_manager):
        """Get all books sorted by creation date."""
        # Create multiple books
        ids = []
        for i in range(3):
            book_id = book_manager.create_book(
                title=f"Book {i}",
                description=f"Description {i}",
                theme="christmas",
                target_audience="seniors",
            )
            ids.append(book_id)

        books = book_manager.get_all_books()

        # Should be in reverse order (newest first)
        assert len(books) == 3
        assert books[0].book_id == ids[2]
        assert books[1].book_id == ids[1]
        assert books[2].book_id == ids[0]


class TestBookToDict:
    """Test book serialization."""

    def test_book_to_dict(self, book_manager):
        """Convert book to dictionary."""
        book_id = book_manager.create_book(
            title="Christmas Puzzles",
            description="Holiday themed nonograms",
            theme="christmas",
            target_audience="seniors",
            cover_image_url="https://example.com/cover.jpg",
        )

        book_manager.add_puzzles_to_book(book_id, ["puzzle_000001", "puzzle_000002"])

        book = book_manager.get_book(book_id)
        data = book.to_dict()

        assert data["book_id"] == book_id
        assert data["metadata"]["title"] == "Christmas Puzzles"
        assert data["puzzle_count"] == 2
        assert data["status"] == BookStatus.DRAFT.value


class TestSingleton:
    """Test singleton pattern."""

    def test_get_book_manager_singleton(self):
        """Book manager is a singleton."""
        mgr1 = get_book_manager()
        mgr2 = get_book_manager()

        assert mgr1 is mgr2
