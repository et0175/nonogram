"""Book management service for admin panel.

Handles book creation, puzzle curation, PDF generation setup, and KDP metadata.
Supports both in-memory storage (legacy) and database-backed storage (when session_factory provided).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import json
import logging
import uuid as uuid_module

from nonogram.admin.book_page_spec import BOOK1_PROFILE
from nonogram.admin.book_plan import (
    BUCKETS,
    DEFAULT_PLAN,
    TIERS,
    DistributionPlan,
    InvalidPlan,
    LongestSideBucket,
    Split,
    planned_cells,
    prefill,
    selection_cells,
    with_split,
)
from nonogram.difficulty import Tier

logger = logging.getLogger(__name__)


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
    # The stored print specification (the ``books`` print columns, cm as
    # strings). ``None`` is an empty column: ``book_page_spec`` falls back to
    # CON-018's Book 1 profile for it. create_book stores the profile (AC-181).
    trim_width_cm: Optional[str] = None
    trim_height_cm: Optional[str] = None
    gutter_margin_cm: Optional[str] = None
    outside_margin_cm: Optional[str] = None
    outside_margin_bleed_cm: Optional[str] = None

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


# --------------------------------------------------------------------------
# The readiness gate (CARD-124; FR-037, INV-007, ADR-0035)
# --------------------------------------------------------------------------
#
# A book leaves draft only as *the book that was planned*. The verdict is a
# pure function of the stored plan and the selection's records, so it is the
# same verdict in both storage modes and can be read on its own.

#: How far one longest-side x tier cell may sit from its planned share and
#: still leave draft, in percentage points. The bound is **inclusive**: a cell
#: exactly 3 points out passes (AC-219), one 4 points out does not (AC-220).
READY_TOLERANCE_POINTS = 3

#: What a book with no stored plan is told at the gate (ADR-0035 (c)). Every
#: book created since ADR-0034 starts on the default plan, so this is the
#: pre-migration row's remedy, and it is one save on Print setup.
NO_PLAN_REFUSAL = (
    "This book has no stored plan, so it cannot leave draft. "
    "Store one on Print setup first."
)


def off_plan_cells(plan: DistributionPlan, puzzles) -> List[tuple]:
    """The cells whose count is further from the plan than the tolerance.

    ``(bucket, tier, actual_count, planned_count)`` per offending cell, in
    :data:`BUCKETS` x :data:`TIERS` order; empty when the selection matches
    the plan. ``puzzles`` are the selection's stored records, counted by
    CARD-119's :func:`~nonogram.admin.book_plan.selection_cells` — the one
    bucketing function (EC-024), never re-derived here.

    Both shares are taken over the **planned** total (ADR-0035 (b)): a cell's
    actual share is its count divided by ``plan.count``, and its planned share
    is the plan's own cell divided by the same number. "Ready" therefore means
    the planned book, not merely the planned mix — an under-filled selection
    fails even when its proportions are right.

    The plan's ``count`` is the denominator, not the matrix's sum: the two
    differ only for a hand-edited matrix that already disagrees with its split
    (:attr:`DistributionPlan.disagrees_with_split`, reported and allowed), and
    the total the owner planned is the book ADR-0035 measures against. It is
    also never zero (INV-005), so the comparison has no degenerate case.

    The comparison is exact integer arithmetic — ``|actual - planned| * 100 <=
    tolerance * total`` rather than a difference of two floats against 3.0 —
    because the bound is inclusive and AC-219 and AC-220 sit either side of
    exactly that boundary.
    """
    planned = planned_cells(plan)
    actual = selection_cells(puzzles)
    return [
        (bucket, tier, actual[(bucket, tier)], planned[(bucket, tier)])
        for bucket in BUCKETS
        for tier in TIERS
        if abs(actual[(bucket, tier)] - planned[(bucket, tier)]) * 100
        > READY_TOLERANCE_POINTS * plan.count
    ]


def _whole_percent(count: int, total: int) -> int:
    """``count`` as a whole percent of ``total``, rounded half up, in integers."""
    return (2 * 100 * count + total) // (2 * total)


def ready_refusal(plan: Optional[DistributionPlan], puzzles) -> Optional[str]:
    """Why this selection may not leave draft, or ``None`` when it may.

    ADR-0035/R1 in one place: no stored plan is a refusal with its remedy, and
    otherwise every cell must be within :data:`READY_TOLERANCE_POINTS` of its
    planned share. A refusal names **every** offending cell with its actual and
    planned share, so the owner sees the whole of what is wrong at once
    (AC-221).
    """
    if plan is None:
        return NO_PLAN_REFUSAL
    offenders = off_plan_cells(plan, puzzles)
    if not offenders:
        return None
    named = "; ".join(
        f"{bucket.label} x {tier.value}:"
        f" {_whole_percent(actual, plan.count)}%"
        f" against {_whole_percent(planned, plan.count)}%"
        for bucket, tier, actual, planned in offenders
    )
    return (
        "This book does not match its plan, so it cannot leave draft. "
        f"More than {READY_TOLERANCE_POINTS} percentage points out: {named}."
    )


class BookManager:
    """Service for managing books and their puzzles.

    Supports both in-memory storage (legacy, for backward compatibility) and
    database-backed storage (when session_factory is provided).
    """

    def __init__(self, session_factory=None, puzzle_store=None):
        """Initialize book manager.

        Args:
            session_factory: Optional callable that yields a DB session.
                           If None, uses in-memory dict storage (legacy mode).
                           If provided, uses database backend.
            puzzle_store: The :class:`PuzzleReviewService` that owns the puzzle
                           rows (CARD-100). Membership is two facts that must be
                           written together — this book's list, and each
                           puzzle's ``book_id`` — and puzzle rows are not this
                           module's to write, so it asks the store. A manager
                           built without one keeps its books correctly and says
                           so in the log rather than pretending; every manager
                           ``create_app`` builds has one.
        """
        self._session_factory = session_factory
        self.puzzle_store = puzzle_store
        # In-memory book storage (used only in legacy mode when session_factory is None)
        self.books: Dict[str, Book] = {}
        # In-memory plans, keyed by book id (CARD-120). Kept beside the books
        # rather than on the Book dataclass so that saving a plan has nothing
        # of the selection within reach (G-2), exactly as in DB mode where
        # save_plan writes one column.
        self._plans: Dict[str, DistributionPlan] = {}
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

            # AC-181 (CON-018): a new book stores the Book 1 print profile.
            book = Book(book_id=book_id, metadata=metadata, **BOOK1_PROFILE.stored_columns())
            self.books[book_id] = book
            # ADR-0034: every new book starts on the default plan.
            self._plans[book_id] = DEFAULT_PLAN

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
                    book_metadata=metadata,
                    status=BookStatus.DRAFT.value,
                    # ADR-0034: every new book starts on the default plan.
                    distribution_plan=plan_to_json(DEFAULT_PLAN),
                    # AC-181 (CON-018): a new book stores the Book 1 print
                    # profile, explicitly rather than through column defaults.
                    **BOOK1_PROFILE.stored_columns(),
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
        # Parse metadata JSON (stored in book_metadata database column)
        metadata_dict = book_row.book_metadata or {}

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
            trim_width_cm=book_row.trim_width_cm,
            trim_height_cm=book_row.trim_height_cm,
            gutter_margin_cm=book_row.gutter_margin_cm,
            outside_margin_cm=book_row.outside_margin_cm,
            outside_margin_bleed_cm=book_row.outside_margin_bleed_cm,
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

    def get_plan(self, book_id: str) -> Optional[DistributionPlan]:
        """The book's stored distribution plan (FR-034), read back from storage.

        ``None`` for a book that has no plan — one created before migration 010
        and never set up since (no backfill, G-3) — and for an unknown book.
        """
        if self._session_factory is None:
            return self._plans.get(book_id)

        from nonogram.db.models import Book as DBBook

        with self._session_factory() as db:
            book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
            if book_row is None or book_row.distribution_plan is None:
                return None
            return plan_from_json(book_row.distribution_plan)

    def save_plan(self, book_id: str, plan: DistributionPlan) -> bool:
        """Store ``plan`` as the book's distribution plan (FR-034, FR-035).

        ``plan`` must be a :class:`DistributionPlan`: the aggregate has already
        refused a split that does not sum to 100 and any negative or fractional
        cell (INV-005), so nothing reaches storage that it would not accept.

        Writes the plan and nothing else of the book's content — never the
        selection, its order or its custom titles (G-2, FR-038).

        A plan edit on a book that has **left draft returns it to draft**
        (owner's decision, CARD-124; the same rule ADR-0035's "Membership
        change after draft" gives a membership edit, INV-012). The plan is what
        :meth:`set_book_status` measures the selection against, so changing it
        changes the verdict that let the book out — and a book whose verdict is
        no longer known must be judged again before a PDF or a KDP upload is
        built from it. A book already in draft is left where it is.

        Returns:
            True if stored, False if the book does not exist.

        Raises:
            InvalidPlan: ``plan`` is not a DistributionPlan.
        """
        if not isinstance(plan, DistributionPlan):
            raise InvalidPlan(f"a book's plan must be a DistributionPlan, got {type(plan).__name__}")

        if self._session_factory is None:
            book = self.books.get(book_id)
            if not book:
                return False
            self._plans[book_id] = plan
            book.status = BookStatus.DRAFT.value
            book.updated_at = datetime.utcnow()
            return True

        from nonogram.db.models import Book as DBBook

        with self._session_factory() as db:
            book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
            if not book_row:
                return False
            book_row.distribution_plan = plan_to_json(plan)
            book_row.status = BookStatus.DRAFT.value
            book_row.updated_at = datetime.utcnow()
            db.commit()
            return True

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

            self._mirror_onto_puzzles(new_puzzles, book_id)
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
                if book_row.book_metadata is None:
                    book_row.book_metadata = {}
                book_row.book_metadata['page_count'] = max(1, len(book_row.puzzle_ids) // 2)
                book_row.updated_at = datetime.utcnow()

                db.commit()

            self._mirror_onto_puzzles(new_puzzles, book_id)
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

            self._mirror_onto_puzzles([puzzle_id], None)
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

                # A NEW list, not the same one mutated and assigned back
                # (CARD-100). `puzzle_ids` is a plain JSON column: SQLAlchemy
                # compares identity to decide what is dirty, so removing from
                # the list in place and reassigning it changed nothing at all —
                # in DB mode, which is production, taking a puzzle out of a book
                # silently did not happen. `add_puzzles_to_book` was never
                # affected because it builds a new list by concatenation.
                book_row.puzzle_ids = [p for p in puzzle_ids if p != puzzle_id]

                # Update page count in metadata
                book_row.book_metadata = {
                    **(book_row.book_metadata or {}),
                    'page_count': max(1, len(book_row.puzzle_ids) // 2),
                }
                book_row.updated_at = datetime.utcnow()

                # Also remove custom title if it exists — a new dict, same reason
                if book_row.puzzle_titles and puzzle_id in book_row.puzzle_titles:
                    book_row.puzzle_titles = {
                        k: v for k, v in book_row.puzzle_titles.items() if k != puzzle_id
                    }

                db.commit()

            self._mirror_onto_puzzles([puzzle_id], None)
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

    def _selection_records(self, puzzle_ids) -> List[Dict[str, Any]]:
        """The stored record of each puzzle in a selection, for the gate.

        A puzzle id no row matches contributes to no cell — the same verdict
        :func:`~nonogram.admin.book_plan.selection_cells` makes on a record
        with no recognisable tier or a side outside the supported range.

        A manager built without a puzzle store cannot see the selection at
        all, so it reads as empty and the gate refuses rather than waving the
        book through. That is the honest failure (the same choice
        :meth:`_mirror_onto_puzzles` makes), not a way past ADR-0035/R1; every
        manager ``create_app`` builds has a store.
        """
        if self.puzzle_store is None:
            logger.warning(
                "No puzzle store: the selection of %d puzzle(s) cannot be read, so "
                "the plan check (ADR-0035) sees an empty book and refuses.",
                len(list(puzzle_ids)),
            )
            return []

        records: List[Dict[str, Any]] = []
        for puzzle_id in puzzle_ids:
            try:
                record = self.puzzle_store.get_puzzle(str(puzzle_id))
            except (ValueError, TypeError) as error:
                logger.warning(
                    "Book holds puzzle id %r that no row can match (%s); it counts "
                    "towards no plan cell.",
                    puzzle_id,
                    error,
                )
                continue
            if record is not None:
                records.append(record)
        return records

    def _refuse_unless_the_planned_book(
        self, book_id: str, current_status: str, new_status: str, puzzle_ids
    ) -> None:
        """ADR-0035/R1: an exit from draft that does not match the plan is refused.

        The gate runs **at the exit from draft only** — every target status,
        including a direct ``draft -> ready_for_kdp`` or ``draft -> published``
        jump, which is the status-jump bypass ADR-0035 (a) closes. ``draft ->
        draft`` is not an exit, and a move between two non-draft statuses is
        past the gate already.

        Raises:
            ValueError: no stored plan, or a cell out of tolerance. The
                message is the refusal the owner is shown.
        """
        if current_status != BookStatus.DRAFT.value or new_status == BookStatus.DRAFT.value:
            return
        refusal = ready_refusal(self.get_plan(book_id), self._selection_records(puzzle_ids))
        if refusal is not None:
            raise ValueError(refusal)

    def set_book_status(self, book_id: str, status: str) -> bool:
        """Update book status.

        Every transition **out of draft** — to ``ready_for_pdf`` or to any
        later status — is gated on the book's stored plan (ADR-0035/R1,
        FR-037, INV-007): the book must have a plan, and every longest-side x
        tier cell of its selection must be within
        :data:`READY_TOLERANCE_POINTS` percentage points of that cell's share
        of the planned total. A refusal leaves the status unchanged and names
        every offending cell (see :func:`ready_refusal`).

        Membership outside draft
        ------------------------
        The gate runs at the exit from draft, not continuously. Adding or
        removing a puzzle on a book that has **left** draft returns the book to
        draft (INV-012, ADR-0035's "Membership change after draft"), so it
        passes this gate again before it can leave — a KDP upload is never
        built from a book that no longer matches its plan. Editing the plan
        does the same (:meth:`save_plan`). CARD-131 implements the return to
        draft on the membership paths; there is no bypass either way, because a
        book back in draft leaves it only through this gate, like any other
        draft book.

        Args:
            book_id: ID of book
            status: New status (draft, ready_for_pdf, pdf_generated, ready_for_kdp, published)

        Returns:
            True if updated, False if not found

        Raises:
            ValueError: If invalid status, or the transition is refused
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

            self._refuse_unless_the_planned_book(
                book_id, current_status, status, list(book.puzzle_ids)
            )

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

                current_status = book_row.status
                selection = list(book_row.puzzle_ids or [])

            # Judged with no session of this method's open, exactly as
            # `_mirror_onto_puzzles` is called outside one: the plan and the
            # selection's records are each read through their own.
            self._refuse_unless_the_planned_book(book_id, current_status, status, selection)

            with self._session_factory() as db:
                book_row = db.query(DBBook).filter(DBBook.id == uuid_module.UUID(book_id)).first()
                if not book_row:
                    return False

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

            # CARD-108: let go of the puzzles before the book that held them
            # disappears. In DB mode the foreign key does this on its own
            # (`ON DELETE SET NULL`, CARD-103); in memory mode nothing did, so
            # a deleted book left its puzzles naming it for ever — and since
            # CARD-100 every in-book guard reads that column, they could no
            # longer be rejected, restored, approved or deleted by anything.
            # Done explicitly in both branches so the two modes cannot disagree
            # about what deleting a book means.
            self._mirror_onto_puzzles(list(book.puzzle_ids or []), None)
            del self.books[book_id]
            self._plans.pop(book_id, None)
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

                held = list(book_row.puzzle_ids or [])
                db.delete(book_row)
                db.commit()

            # CARD-108: belt to the foreign key's braces. `ON DELETE SET NULL`
            # has already cleared these; saying so here keeps the two storage
            # modes doing the same thing for the same stated reason, rather
            # than one relying on a constraint the other does not have.
            self._mirror_onto_puzzles(held, None)
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
                    book_row.book_metadata = {}
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
                    book_row.book_metadata = {}
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
                    book_row.book_metadata = {}
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

    def _mirror_onto_puzzles(self, puzzle_ids, book_id) -> None:
        """Write this membership change onto the puzzle rows too (CARD-100).

        ``Book.puzzle_ids`` and ``Puzzle.book_id`` are two halves of one fact.
        Until this card only the first half was ever written, so every guard in
        the panel — which reads the second — waved through puzzles a book was
        built on, and "Delete rejected" removed them outright.

        A manager with no store keeps its own half correctly and says so, which
        is the honest failure: the alternative is a book whose puzzles are
        unprotected and nothing anywhere saying why. The backfill repairs a
        history of exactly that.
        """
        if not puzzle_ids:
            return
        if self.puzzle_store is None:
            logger.warning(
                "No puzzle store: book membership for %d puzzle(s) was recorded "
                "on the book only, so the puzzles are not protected from bulk "
                "actions (CARD-100). Run the membership backfill.",
                len(list(puzzle_ids)),
            )
            return
        if book_id is None:
            self.puzzle_store.release_from_book(puzzle_ids)
        else:
            self.puzzle_store.assign_to_book(puzzle_ids, book_id)

    def book_listing(self, puzzle_id: str) -> Optional[str]:
        """The id of a book that lists this puzzle, or ``None`` (CARD-068).

        Asks the side that actually records membership. Every other in-book
        check in the panel reads ``Puzzle.book_id``, which nothing in
        production writes — a puzzle a book is built on carries ``None``
        there, so those checks wave through a puzzle they were meant to stop
        (CARD-100). Until that is repaired, a caller that would *destroy* a
        booked puzzle asks here instead.

        A scan, because ``Book.puzzle_ids`` is a JSON list that can be neither
        indexed nor joined. Affordable for one puzzle at a time — a Delete the
        owner clicked — and precisely why it is not the answer for the bulk
        paths, which is CARD-100's problem to solve properly.
        """
        for book in self.get_all_books():
            if puzzle_id in (book.puzzle_ids or []):
                return book.book_id
        return None


# --------------------------------------------------------------------------
# The stored shape of a distribution plan (CARD-120)
# --------------------------------------------------------------------------
#
#     {"count": 150,
#      "split": {"easy": 40, "medium": 40, "hard": 20},
#      "cells": [[e, m, h], ...4 rows, one per bucket in BUCKETS order],
#      "edited": [["<=15", "easy"], ...]}
#
# Buckets and tiers are stored by their labels/values, not by position in
# BUCKETS/TIERS, so reordering either tuple can never silently move an edited
# mark to a different cell. Decoding goes back through DistributionPlan, so a
# stored document the aggregate would not accept is refused on the way out too.


def plan_to_json(plan: DistributionPlan) -> dict:
    """The JSON document ``books.distribution_plan`` holds for ``plan``."""
    return {
        "count": plan.count,
        "split": {"easy": plan.split.easy, "medium": plan.split.medium, "hard": plan.split.hard},
        "cells": [list(row) for row in plan.cells],
        "edited": sorted([bucket.value, tier.value] for bucket, tier in plan.edited),
    }


def plan_from_json(document: Dict[str, Any]) -> DistributionPlan:
    """The :class:`DistributionPlan` a stored document describes.

    Raises:
        InvalidPlan: the document is not a plan INV-005 allows.
    """
    try:
        split = document["split"]
        return DistributionPlan(
            count=document["count"],
            split=Split(split["easy"], split["medium"], split["hard"]),
            cells=tuple(tuple(row) for row in document["cells"]),
            edited=frozenset(
                (LongestSideBucket(bucket), Tier(tier)) for bucket, tier in document.get("edited", [])
            ),
        )
    except InvalidPlan:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidPlan(f"stored distribution plan is malformed: {error}") from error


def revise_plan(
    current: Optional[DistributionPlan],
    count: int,
    split: Split,
    submitted_cells,
) -> DistributionPlan:
    """The plan a Print setup submission asks for (FR-034, POL-007).

    ``current`` is the stored plan (``None`` for a plan-less book, which the
    form shows as :data:`DEFAULT_PLAN`). ``submitted_cells`` is the 4 x 3
    matrix as the owner submitted it.

    Whether a cell is hand-edited is decided per cell against the plan the
    page showed (``shown``). The form cannot tell "left alone" from "retyped
    the same value", so only a *changed* value counts as an owner action:

    * submitted value **equal to the shown value** — the owner left it alone,
      so it keeps the mark it had: a stored hand edit stays edited (even when
      its value happens to equal a prefill), an unedited cell stays unedited;
    * submitted value **different from the shown value** — the owner typed
      into it: it becomes hand-edited, unless the new value is the shown
      plan's prefill for that cell, which is the owner deliberately putting
      it back (the edit mark is cleared).

    Hand-edited cells keep their values; every other cell is re-derived from
    ``count`` and ``split`` (POL-007 via :func:`with_split`), so a changed
    split re-derives an un-edited matrix. A value is never made edited or
    un-edited just by coinciding with a prefill: an edit survives any number
    of unchanged resubmissions and split changes (CARD-120 review F-001).

    Raises:
        InvalidPlan: ``count`` or a submitted cell is not one INV-005 allows.
    """
    shown = current if current is not None else DEFAULT_PLAN
    reference = prefill(shown.count, shown.split)
    typed = DistributionPlan(count=count, split=shown.split, cells=submitted_cells)

    def is_edited(bucket, tier) -> bool:
        value = typed.cell(bucket, tier)
        if value == shown.cell(bucket, tier):
            return (bucket, tier) in shown.edited
        return value != reference.cell(bucket, tier)

    edited = frozenset(
        (bucket, tier) for bucket in BUCKETS for tier in TIERS if is_edited(bucket, tier)
    )
    return with_split(
        DistributionPlan(count=count, split=shown.split, cells=typed.cells, edited=edited), split
    )


# Global book manager instance (legacy in-memory mode)
_book_manager = BookManager(session_factory=None)


def get_book_manager(session_factory=None, puzzle_store=None) -> BookManager:
    """Get the book manager.

    Args:
        session_factory: Optional DB session factory. If provided, uses DB mode.
                        If None, returns the singleton in-memory instance.

    Returns:
        BookManager instance (either singleton or new DB-backed instance)
    """
    if session_factory is None:
        # Return the singleton in-memory instance, wiring its store on first
        # use if the caller brought one (CARD-100).
        if puzzle_store is not None:
            _book_manager.puzzle_store = puzzle_store
        return _book_manager
    else:
        # Return a new DB-backed instance
        return BookManager(session_factory=session_factory, puzzle_store=puzzle_store)
