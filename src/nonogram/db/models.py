"""Database ORM models for nonogram platform."""

from sqlalchemy import Column, String, Integer, DateTime, UUID, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User account for website access."""

    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    subscription_tier = Column(String, default='free')  # 'free', 'premium'
    puzzles_generated_month = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    puzzles = relationship("Puzzle", back_populates="batch")


class Puzzle(Base):
    """Generated nonogram puzzle at any review status."""

    __tablename__ = 'puzzles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'), nullable=True)
    grid = Column(JSON, nullable=False)  # list[list[bool]]
    clues_rows = Column(JSON, nullable=False)  # list[list[int]] — display only
    clues_cols = Column(JSON, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    theme = Column(String, nullable=True)
    difficulty_score = Column(Integer, nullable=True)  # 1-100
    difficulty_tier = Column(String, nullable=True)  # 'Easy', 'Medium', 'Hard'
    quality_score = Column(Integer, nullable=True)  # 1-100 (image fidelity)
    recognizability = Column(String, nullable=True)
    strategies_used = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default='draft')  # 'draft', 'approved', 'rejected', 'in_book'
    source_image = Column(String, nullable=True)
    puzzle_name = Column(String, nullable=True)  # human-readable name for filtering/sorting
    book_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("Batch", back_populates="puzzles")


class Book(Base):
    """Collection of nonograms curated into a book."""

    __tablename__ = 'books'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    theme = Column(String, nullable=True)
    target_audience = Column(String, nullable=True)  # 'seniors', 'general'
    puzzle_ids = Column(JSON, nullable=False, default=[])  # list[str] of puzzle UUIDs
    puzzle_titles = Column(JSON, nullable=False, default={})  # {puzzle_id: "custom title"}
    metadata = Column(JSON, nullable=False, default={})  # Stores: size, cover_image_url, pdf_url, kdp_asin
    status = Column(String, default='draft')  # 'draft', 'ready_for_pdf', 'pdf_generated', 'ready_for_kdp', 'published'
    # Print specifications (Step 1)
    trim_width_cm = Column(String, nullable=True, default='15.24')  # stored as string for precision
    trim_height_cm = Column(String, nullable=True, default='22.86')
    gutter_margin_cm = Column(String, nullable=True)  # inside margin
    outside_margin_cm = Column(String, nullable=True)
    outside_margin_bleed_cm = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GenerationHistory(Base):
    """Log of generated puzzles for analytics."""

    __tablename__ = 'generation_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey('nonograms.id'), nullable=True)
    image_url = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class UserSelectedBook(Base):
    """Many-to-many relationship: users select puzzles for books."""

    __tablename__ = 'user_selected_books'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey('nonograms.id'), primary_key=True)
    book_id = Column(UUID(as_uuid=True), ForeignKey('books.id'), primary_key=True)
    selected_at = Column(DateTime, default=datetime.utcnow)
