"""Database session management."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = None
SessionLocal = None
_engine_url = None  # DATABASE_URL the current engine/SessionLocal were built for


def _init_engine():
    """Initialize (or reinitialize) the database engine for the current DATABASE_URL.

    Reads the environment fresh on every call, and rebuilds the engine when the
    value has changed since the last call — so a DATABASE_URL set or changed
    after this module was first imported (e.g. via monkeypatch in tests, or a
    caller that imports this module before the process's env is fully set up)
    takes effect on the next session request instead of being silently ignored
    by a value captured once at import time.
    """
    global engine, SessionLocal, _engine_url
    database_url = os.getenv('DATABASE_URL', None)
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL not set. Database persistence disabled. "
            "Set DATABASE_URL to enable it (e.g. postgresql://user:pass@localhost/dbname)"
        )
    if engine is None or database_url != _engine_url:
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine, class_=Session)
        _engine_url = database_url


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
