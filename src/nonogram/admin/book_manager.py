"""Book management service for admin panel.

Handles book creation, puzzle curation, PDF generation setup, and KDP metadata.
Supports both in-memory storage (legacy) and database-backed storage (when session_factory provided).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import json
import uuid as uuid_module


class BookStatus(Enum):
    """Status of a book in the publishing workflow."""

    DRAFT = "draft"
    READY_FOR_PDF = "ready_for_pdf"
    PDF_GENERATED = "pdf_generated"
    READY_FOR_KDP = "ready_for_kdp"
    PUBLISHED = "published"


@dataclass
class BookMetadata:
    """Metadata for KDP book submission."""

    title: str
    description: str
    theme: str
    target_audience: str
    size: str  # e.g., "8x10" (trim size)
    page_count: int
    cover_image_url: Optional[str] = None
    pdf_url: Optional[str] = None
    kdp_asin: Optional[str] = None


@dataclass
class Book:
    """Represents a book with puzzles and metadata."""

    book_id: str
    metadata: BookMetadata
    puzzle_ids: List[str] = field(default_factory=list)
    puzzle_titles: Dict[str, str] = field(default_factory=dict)  # {puzzle_id: "custom title"}
    status: str = BookStatus.DRAFT.value
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "book_id": self.book_id,
            "metadata": {
                "title": self.metadata.title,
                "description": self.metadata.description,
                "theme": self.metadata.theme,
                "target_audience": self.metadata.target_audience,
                "size": self.metadata.size,
                "page_count": self.metadata.page_count,
                "cover_image_url": self.metadata.cover_image_url,
                "pdf_url": self.metadata.pdf_url,
                "kdp_asin": self.metadata.kdp_asin,
            },
            "puzzle_count": len(self.puzzle_ids),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BookManager:
    """Service for managing books and their puzzles.

    Supports both in-memory storage (legacy, for backward compatibility) and
    database-backed storage (when session_factory is provided).
    """

    def __init__(self, session_factory=None):
        """Initialize book manager.

        Args:
            session_factory: Optional callable that yields a DB session.
                           If None, uses in-memory dict storage (legacy mode).
                           If provided, uses database backend.
        """
        self._session_factory = session_factory
        # In-memory book storage (used only in legacy mode when session_factory is None)
        self.books: Dict[str, Book] = {}
        self._next_id = 1

    def create_book(
        self,
        title: str,
        description: str,
        theme: str,
        target_audience: str,
        size: str = "8x10",
        cover_image_url: Optional[str] = None,
    ) -> str:
        """Create a new book.

        Args:
            title: Book title
            description: Book description
            theme: Book theme (e.g., 'christmas')
            target_audience: Target audience (e.g., 'seniors')
            size: Trim size for KDP (default "8x10")
            cover_image_url: URL to cover image

        Returns:
            book_id

        Raises:
            ValueError: If parameters invalid
        """
        if not title or len(title.strip()) == 0:
            raise ValueError("Title cannot be empty")
        if not description or len(description.strip()) == 0:
            raise ValueError("Description cannot be empty")
        if theme not in ("christmas", "halloween", "easter", "valentine", "generic"):
            raise ValueError(f"Invalid theme: {theme}")
        if not target_audience or len(target_audience.strip()) == 0:
            raise ValueError("Target audience cannot be empty")

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book_id = f"book_{self._next_id:06d}"
            self._next_id += 1

            metadata = BookMetadata(
                title=title,
                description=description,
                theme=theme,
                target_audience=target_audience,
                size=size,
                page_count=0,  # Updated when puzzles added
                cover_image_url=cover_image_url,
            )

            book = Book(book_id=book_id, metadata=metadata)
            self.books[book_id] = book

            return book_id
        else:
            # DB mode: insert Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                metadata = {
                    'size': size,
                    'cover_image_url': cover_image_url,
                    'pdf_url': None,
                    'kdp_asin': None,
                }

                book = DBBook(
                    title=title,
                    description=description,
                    theme=theme,
                    target_audience=target_audience,
                    puzzle_ids=[],
                    puzzle_titles={},
                    metadata=metadata,
                    status=BookStatus.DRAFT.value,
                )
                db.add(book)
                db.flush()  # get the auto-generated UUID
                return str(book.id)

    def _row_to_book(self, book_row) -> Book:
        """Convert SQLAlchemy Book ORM row to Book dataclass.

        Args:
            book_row: SQLAlchemy Book ORM instance

        Returns:
            Book dataclass instance
        """
        # Parse metadata JSON
        metadata_dict = book_row.metadata or {}

        # Build BookMetadata object
        metadata = BookMetadata(
            title=book_row.title,
            description=book_row.description,
            theme=book_row.theme,
            target_audience=book_row.target_audience,
            size=metadata_dict.get('size', '8x10'),
            page_count=metadata_dict.get('page_count', max(1, len(book_row.puzzle_ids) // 2)),
            cover_image_url=metadata_dict.get('cover_image_url'),
            pdf_url=metadata_dict.get('pdf_url'),
            kdp_asin=metadata_dict.get('kdp_asin'),
        )

        puzzle_titles = book_row.puzzle_titles or {}

        return Book(
            book_id=str(book_row.id),
            metadata=metadata,
            puzzle_ids=book_row.puzzle_ids or [],
            puzzle_titles=puzzle_titles,
            status=book_row.status,
            created_at=book_row.created_at,
            updated_at=book_row.updated_at or book_row.created_at,
        )

    def get_book(self, book_id: str) -> Optional[Book]:
        """Get a book by ID.

        Args:
            book_id: ID of book

        Returns:
            Book object, or None if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            return self.books.get(book_id)
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if book_row:
                    return self._row_to_book(book_row)
                return None

    def add_puzzles_to_book(
        self, book_id: str, puzzle_ids: List[str]
    ) -> bool:
        """Add puzzles to a book.

        Args:
            book_id: ID of book
            puzzle_ids: IDs of puzzles to add

        Returns:
            True if added, False if book not found

        Raises:
            ValueError: If puzzle_ids empty or book already published
        """
        if not puzzle_ids:
            raise ValueError("Must provide at least one puzzle")

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            if book.status == BookStatus.PUBLISHED.value:
                raise ValueError("Cannot add puzzles to published book")

            # Add unique puzzle IDs (avoid duplicates)
            existing = set(book.puzzle_ids)
            new_puzzles = [pid for pid in puzzle_ids if pid not in existing]
            book.puzzle_ids.extend(new_puzzles)

            # Update page count (rough estimate: ~2 puzzles per page)
            book.metadata.page_count = max(1, len(book.puzzle_ids) // 2)
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.status == BookStatus.PUBLISHED.value:
                    raise ValueError("Cannot add puzzles to published book")

                # Add unique puzzle IDs (avoid duplicates)
                existing_puzzles = book_row.puzzle_ids or []
                existing = set(existing_puzzles)
                new_puzzles = [pid for pid in puzzle_ids if pid not in existing]
                book_row.puzzle_ids = existing_puzzles + new_puzzles

                # Update page count in metadata
                if book_row.metadata is None:
                    book_row.metadata = {}
                book_row.metadata['page_count'] = max(1, len(book_row.puzzle_ids) // 2)
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def remove_puzzle_from_book(self, book_id: str, puzzle_id: str) -> bool:
        """Remove a puzzle from a book.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle to remove

        Returns:
            True if removed, False if book/puzzle not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book or puzzle_id not in book.puzzle_ids:
                return False

            book.puzzle_ids.remove(puzzle_id)
            book.metadata.page_count = max(1, len(book.puzzle_ids) // 2)
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                puzzle_ids = book_row.puzzle_ids or []
                if puzzle_id not in puzzle_ids:
                    return False

                puzzle_ids.remove(puzzle_id)
                book_row.puzzle_ids = puzzle_ids

                # Update page count in metadata
                if book_row.metadata is None:
                    book_row.metadata = {}
                book_row.metadata['page_count'] = max(1, len(book_row.puzzle_ids) // 2)
                book_row.updated_at = datetime.utcnow()

                # Also remove custom title if it exists
                if book_row.puzzle_titles and puzzle_id in book_row.puzzle_titles:
                    del book_row.puzzle_titles[puzzle_id]

                db.commit()
                return True

    def reorder_puzzles(self, book_id: str, puzzle_ids: List[str]) -> bool:
        """Reorder puzzles in a book.

        Args:
            book_id: ID of book
            puzzle_ids: Ordered list of puzzle IDs

        Returns:
            True if reordered, False if book not found

        Raises:
            ValueError: If puzzle IDs don't match book's puzzles
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            if set(puzzle_ids) != set(book.puzzle_ids):
                raise ValueError("Puzzle IDs must match book's current puzzles")

            book.puzzle_ids = puzzle_ids
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if set(puzzle_ids) != set(book_row.puzzle_ids or []):
                    raise ValueError("Puzzle IDs must match book's current puzzles")

                book_row.puzzle_ids = puzzle_ids
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def move_puzzle_up(self, book_id: str, puzzle_id: str) -> bool:
        """Move a puzzle up one position in the book.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle to move

        Returns:
            True if moved, False if already at top or not found

        Raises:
            ValueError: If book not found or puzzle not in book
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                raise ValueError("Book not found")

            if puzzle_id not in book.puzzle_ids:
                raise ValueError("Puzzle not in book")

            current_index = book.puzzle_ids.index(puzzle_id)
            if current_index == 0:
                return False  # Already at top

            # Swap with previous puzzle
            book.puzzle_ids[current_index], book.puzzle_ids[current_index - 1] = (
                book.puzzle_ids[current_index - 1],
                book.puzzle_ids[current_index],
            )
            book.updated_at = datetime.utcnow()
            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    raise ValueError("Book not found")

                puzzle_ids = book_row.puzzle_ids or []
                if puzzle_id not in puzzle_ids:
                    raise ValueError("Puzzle not in book")

                current_index = puzzle_ids.index(puzzle_id)
                if current_index == 0:
                    return False  # Already at top

                # Swap with previous puzzle
                puzzle_ids[current_index], puzzle_ids[current_index - 1] = (
                    puzzle_ids[current_index - 1],
                    puzzle_ids[current_index],
                )
                book_row.puzzle_ids = puzzle_ids
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def move_puzzle_down(self, book_id: str, puzzle_id: str) -> bool:
        """Move a puzzle down one position in the book.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle to move

        Returns:
            True if moved, False if already at bottom or not found

        Raises:
            ValueError: If book not found or puzzle not in book
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                raise ValueError("Book not found")

            if puzzle_id not in book.puzzle_ids:
                raise ValueError("Puzzle not in book")

            current_index = book.puzzle_ids.index(puzzle_id)
            if current_index == len(book.puzzle_ids) - 1:
                return False  # Already at bottom

            # Swap with next puzzle
            book.puzzle_ids[current_index], book.puzzle_ids[current_index + 1] = (
                book.puzzle_ids[current_index + 1],
                book.puzzle_ids[current_index],
            )
            book.updated_at = datetime.utcnow()
            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    raise ValueError("Book not found")

                puzzle_ids = book_row.puzzle_ids or []
                if puzzle_id not in puzzle_ids:
                    raise ValueError("Puzzle not in book")

                current_index = puzzle_ids.index(puzzle_id)
                if current_index == len(puzzle_ids) - 1:
                    return False  # Already at bottom

                # Swap with next puzzle
                puzzle_ids[current_index], puzzle_ids[current_index + 1] = (
                    puzzle_ids[current_index + 1],
                    puzzle_ids[current_index],
                )
                book_row.puzzle_ids = puzzle_ids
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def set_puzzle_title(self, book_id: str, puzzle_id: str, title: str) -> bool:
        """Set custom title for a puzzle in the book.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle
            title: Custom title for this puzzle in the book

        Returns:
            True if updated, False if not found

        Raises:
            ValueError: If puzzle not in book
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            if puzzle_id not in book.puzzle_ids:
                raise ValueError("Puzzle not in book")

            if title.strip():
                book.puzzle_titles[puzzle_id] = title.strip()
            elif puzzle_id in book.puzzle_titles:
                del book.puzzle_titles[puzzle_id]  # Remove custom title

            book.updated_at = datetime.utcnow()
            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if puzzle_id not in (book_row.puzzle_ids or []):
                    raise ValueError("Puzzle not in book")

                puzzle_titles = book_row.puzzle_titles or {}
                if title.strip():
                    puzzle_titles[puzzle_id] = title.strip()
                elif puzzle_id in puzzle_titles:
                    del puzzle_titles[puzzle_id]

                book_row.puzzle_titles = puzzle_titles
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def get_puzzle_title(self, book_id: str, puzzle_id: str) -> Optional[str]:
        """Get custom title for a puzzle in the book.

        Args:
            book_id: ID of book
            puzzle_id: ID of puzzle

        Returns:
            Custom title if set, None otherwise
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return None

            return book.puzzle_titles.get(puzzle_id)
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return None

                puzzle_titles = book_row.puzzle_titles or {}
                return puzzle_titles.get(puzzle_id)

    def set_book_status(self, book_id: str, status: str) -> bool:
        """Update book status.

        Args:
            book_id: ID of book
            status: New status (draft, ready_for_pdf, pdf_generated, ready_for_kdp, published)

        Returns:
            True if updated, False if not found

        Raises:
            ValueError: If invalid status
        """
        valid_statuses = {s.value for s in BookStatus}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            # Status progression rules
            current_status = book.status
            if current_status == BookStatus.PUBLISHED.value:
                raise ValueError("Cannot change status of published book")

            if len(book.puzzle_ids) == 0 and status != BookStatus.DRAFT.value:
                raise ValueError("Must have puzzles before advancing status")

            book.status = status
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                # Status progression rules
                if book_row.status == BookStatus.PUBLISHED.value:
                    raise ValueError("Cannot change status of published book")

                if len(book_row.puzzle_ids or []) == 0 and status != BookStatus.DRAFT.value:
                    raise ValueError("Must have puzzles before advancing status")

                book_row.status = status
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def delete_book(self, book_id: str) -> bool:
        """Delete a book (only draft books).

        Args:
            book_id: ID of book to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If book is not in draft status
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            if book.status != BookStatus.DRAFT.value:
                raise ValueError(f"Cannot delete {book.status} book. Only draft books can be deleted.")

            del self.books[book_id]
            return True
        else:
            # DB mode: delete Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.status != BookStatus.DRAFT.value:
                    raise ValueError(f"Cannot delete {book_row.status} book. Only draft books can be deleted.")

                db.delete(book_row)
                db.commit()
                return True

    def set_cover_image(self, book_id: str, cover_url: str) -> bool:
        """Set cover image URL.

        Args:
            book_id: ID of book
            cover_url: URL to cover image

        Returns:
            True if updated, False if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            book.metadata.cover_image_url = cover_url
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.metadata is None:
                    book_row.metadata = {}
                book_row.metadata['cover_image_url'] = cover_url
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def set_pdf_url(self, book_id: str, pdf_url: str) -> bool:
        """Set generated PDF URL.

        Args:
            book_id: ID of book
            pdf_url: URL to generated PDF

        Returns:
            True if updated, False if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            book.metadata.pdf_url = pdf_url
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.metadata is None:
                    book_row.metadata = {}
                book_row.metadata['pdf_url'] = pdf_url
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def set_kdp_asin(self, book_id: str, asin: str) -> bool:
        """Set KDP ASIN (Amazon product ID).

        Args:
            book_id: ID of book
            asin: Amazon ASIN

        Returns:
            True if updated, False if not found
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            book = self.books.get(book_id)
            if not book:
                return False

            book.metadata.kdp_asin = asin
            book.updated_at = datetime.utcnow()

            return True
        else:
            # DB mode: update Book row
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

                if book_row.metadata is None:
                    book_row.metadata = {}
                book_row.metadata['kdp_asin'] = asin
                book_row.updated_at = datetime.utcnow()

                db.commit()
                return True

    def get_books_by_status(self, status: str) -> List[Book]:
        """Get all books with a given status.

        Args:
            status: Status to filter by

        Returns:
            List of books
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            return [b for b in self.books.values() if b.status == status]
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                rows = db.query(DBBook).filter(DBBook.status == status).order_by(DBBook.created_at.desc()).all()
                return [self._row_to_book(row) for row in rows]

    def get_all_books(self) -> List[Book]:
        """Get all books sorted by creation date (newest first).

        Returns:
            List of all books
        """
        if self._session_factory is None:
            # Legacy mode: in-memory dict
            return sorted(self.books.values(), key=lambda b: b.created_at, reverse=True)
        else:
            # DB mode: query database
            from nonogram.db.models import Book as DBBook

            with self._session_factory() as db:
                rows = db.query(DBBook).order_by(DBBook.created_at.desc()).all()
                return [self._row_to_book(row) for row in rows]


# Global book manager instance (legacy in-memory mode)
_book_manager = BookManager(session_factory=None)


def get_book_manager(session_factory=None) -> BookManager:
    """Get the book manager.

    Args:
        session_factory: Optional DB session factory. If provided, uses DB mode.
                        If None, returns the singleton in-memory instance.

    Returns:
        BookManager instance (either singleton or new DB-backed instance)
    """
    if session_factory is None:
        # Return the singleton in-memory instance
        return _book_manager
    else:
        # Return a new DB-backed instance
        return BookManager(session_factory=session_factory)
