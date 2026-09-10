"""Database session management."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', None)

engine = None
SessionLocal = None


def _init_engine():
    """Initialize the database engine lazily."""
    global engine, SessionLocal
    if engine is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL not set. Database persistence disabled. "
                "Set DATABASE_URL to enable it (e.g. postgresql://user:pass@localhost/dbname)"
            )
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine, class_=Session)


def get_session() -> Session:
    """Create a database session."""
    _init_engine()
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
    _init_engine()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
