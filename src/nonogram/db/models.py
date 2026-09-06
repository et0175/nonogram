"""Database ORM models for nonogram platform."""

from sqlalchemy import Column, String, Integer, DateTime, UUID, ForeignKey, Text
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


class Nonogram(Base):
    """Generated nonogram puzzle."""

    __tablename__ = 'nonograms'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    theme = Column(String, nullable=True)  # 'christmas', 'newyear', etc
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    difficulty_score = Column(Integer, nullable=True)  # 1-100
    difficulty_tier = Column(String, nullable=True)  # 'Easy', 'Medium', 'Hard'
    quality_score = Column(Integer, nullable=True)  # 1-100 (image fidelity)
    strategies_used = Column(Text, nullable=True)  # JSON array as string
    solution_grid = Column(Text, nullable=True)  # JSON array as string
    clues_rows = Column(Text, nullable=True)  # JSON array as string
    clues_cols = Column(Text, nullable=True)  # JSON array as string
    image_source_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='draft')  # 'draft', 'approved', 'in_book'


class Book(Base):
    """Collection of nonograms curated into a book."""

    __tablename__ = 'books'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    theme = Column(String, nullable=True)
    target_audience = Column(String, nullable=True)  # 'seniors', 'general'
    nonogram_ids = Column(Text, nullable=True)  # JSON array as string
    cover_image_url = Column(String, nullable=True)
    pdf_url = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    status = Column(String, default='draft')  # 'draft', 'ready', 'published'
    kdp_asin = Column(String, nullable=True)  # Amazon book ID
    created_at = Column(DateTime, default=datetime.utcnow)


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
