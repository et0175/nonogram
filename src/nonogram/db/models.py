"""Database ORM models for nonogram platform."""

from sqlalchemy import Column, String, Integer, DateTime, UUID, ForeignKey, Text, JSON, func
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    """User account for website access."""

    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    subscription_tier = Column(String, default='free')  # 'free', 'premium'
    puzzles_generated_month = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())


class Batch(Base):
    """A batch generation job."""

    __tablename__ = 'batches'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, nullable=False, default="pending")  # pending/generating/complete/error/cancelled
    source = Column(String, nullable=False, default="random")   # "random" | "images"
    total_count = Column(Integer, nullable=False, default=0)
    completed_count = Column(Integer, nullable=False, default=0)
    puzzle_count = Column(Integer, nullable=False, default=0)
    sizes = Column(JSON, nullable=True)
    theme = Column(String, nullable=True)
    quality_filter = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)

    puzzles = relationship("Puzzle", back_populates="batch")


class Puzzle(Base):
    """Generated nonogram puzzle at any review status."""

    __tablename__ = 'puzzles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'), nullable=True)
    # Left as plain JSON, unlike Book's columns (CARD-101): these are written
    # whole and never edited in place, and `MutableList` tracks only top-level
    # mutation — on a list of rows it would report nothing while a cell
    # changed, which is worse than not claiming to track them at all.
    grid = Column(JSON, nullable=False)  # list[list[bool]]
    clues_rows = Column(JSON, nullable=False)  # list[list[int]] — display only
    clues_cols = Column(JSON, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    theme = Column(String, nullable=True)
    difficulty_score = Column(Integer, nullable=True)  # 0-100 (ADR-0029's scale)
    difficulty_tier = Column(String, nullable=True)  # 'easy'/'medium'/'hard'/'guess'
    quality_score = Column(Integer, nullable=True)  # 1-100 (image fidelity)
    recognizability = Column(String, nullable=True)
    strategies_used = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default='draft')  # 'draft', 'approved', 'rejected', 'in_book'
    source_image = Column(String, nullable=True)
    puzzle_name = Column(String, nullable=True)  # human-readable name for filtering/sorting
    # CARD-103: constrained at last. CARD-100 made this column the record of
    # book membership that every in-book guard in the panel reads, and until
    # now nothing checked it — a puzzle could name a book that did not exist,
    # which is what `book_membership.backfill`'s `missing` verdict is for.
    #
    # SET NULL rather than RESTRICT: deleting a book releases its puzzles,
    # which is what `remove_puzzle_from_book` already does one at a time.
    # RESTRICT would turn "delete this book" into an error the panel has no
    # wording for, and would leave a deleted book's puzzles permanently
    # unrejectable — a worse hole than the one this closes.
    book_id = Column(
        UUID(as_uuid=True), ForeignKey('books.id', ondelete='SET NULL'), nullable=True
    )
    created_at = Column(DateTime, default=func.now())

    batch = relationship("Batch", back_populates="puzzles")


class Book(Base):
    """Collection of nonograms curated into a book."""

    __tablename__ = 'books'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    theme = Column(String, nullable=True)
    target_audience = Column(String, nullable=True)  # 'seniors', 'general'
    # CARD-101: mutation-tracked, not plain JSON. SQLAlchemy decides what to
    # write by comparing object identity, so `row.puzzle_ids[i] = x` — or the
    # commoner `ids = row.puzzle_ids; ids.remove(x); row.puzzle_ids = ids` —
    # changed the object in memory and wrote nothing at all. In DB mode, which
    # is production, that silently lost every "move up", every "move down", and
    # every title after a book's first.
    #
    # Wrapping the columns rather than rebuilding the value at each assignment
    # is deliberate: the losing pattern is the one that looks correct, it is
    # invisible in a diff, and it did not even fail consistently — a write
    # while the column was still NULL persisted, because `or {}` built a new
    # dict. A rule that has to be remembered at every call site had already
    # been forgotten at four of them.
    # (`default=list` over `default=[]` is tidiness, not a fix: measured, the
    # shared literal does not leak between rows, because the value is
    # serialised per insert and rebuilt per load.)
    puzzle_ids = Column(MutableList.as_mutable(JSON), nullable=False, default=list)  # list[str] of puzzle UUIDs
    puzzle_titles = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)  # {puzzle_id: "custom title"}
    book_metadata = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)  # Stores: size, cover_image_url, pdf_url, kdp_asin
    status = Column(String, default='draft')  # 'draft', 'ready_for_pdf', 'pdf_generated', 'ready_for_kdp', 'published'
    # CARD-120 (FR-034, ADR-0034): the book's distribution plan — count, split,
    # the 4 x 3 per-bucket matrix and the hand-edited cells, as one JSON
    # document (see BookManager for its shape). NULL for a book created before
    # migration 010: no backfill, a plan-less book stays readable and editable
    # (ADR-0035 refuses it at the gate, CARD-124). MutableDict follows the
    # CARD-101 precedent above, but it tracks only TOP-LEVEL key assignment
    # (doc["count"] = ...); the plan's data sits in nested lists ("cells",
    # "edited", the "split" dict), and an in-place edit there such as
    # doc["cells"][2][2] = 20 is NOT flagged dirty and is silently lost.
    # The document must therefore always be replaced whole — assign
    # plan_to_json(plan), as BookManager.save_plan does.
    distribution_plan = Column(MutableDict.as_mutable(JSON), nullable=True)
    # Print specifications (Step 1)
    trim_width_cm = Column(String, nullable=True, default='21.59')  # stored as string for precision; 8.5 × 11 in
    trim_height_cm = Column(String, nullable=True, default='27.94')
    gutter_margin_cm = Column(String, nullable=True)  # inside margin
    outside_margin_cm = Column(String, nullable=True)
    outside_margin_bleed_cm = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class GenerationHistory(Base):
    """Log of generated puzzles for analytics."""

    __tablename__ = 'generation_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey('puzzles.id'), nullable=True)
    image_url = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())


class UserSelectedBook(Base):
    """Many-to-many relationship: users select puzzles for books."""

    __tablename__ = 'user_selected_books'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey('puzzles.id'), primary_key=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey('books.id'), primary_key=True)
    selected_at = Column(DateTime, default=func.now())
