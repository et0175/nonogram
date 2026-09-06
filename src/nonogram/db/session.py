"""Database session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nonogram_poc')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=Session)


def get_session() -> Session:
    """Create a database session."""
    return SessionLocal()
