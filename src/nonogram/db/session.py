"""Database session management."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nonogram_poc')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=Session)


def get_session() -> Session:
    """Create a database session."""
    return SessionLocal()


def get_db() -> Session:
    """Dependency for FastAPI (alias for get_session)."""
    return get_session()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations.

    Commits on success, rolls back on error, always closes the session.
    Usage:
        with session_scope() as db:
            db.add(obj)
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
