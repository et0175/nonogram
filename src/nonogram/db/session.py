"""Database session management."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = None
SessionLocal = None
_engine_url = None  # DATABASE_URL the current engine/SessionLocal were built for

#: How long a connection attempt may take before it is an error (CARD-097).
#:
#: libpq's default is **no deadline at all**, and "no deadline" is not a
#: theoretical problem: Postgres.app shows a macOS permission dialog on first
#: connect, and until it is confirmed the TCP handshake completes while
#: authentication never does. A client in that state is not slow, it is
#: stopped — and it looks exactly like a healthy connection to everything
#: except the clock. One such attempt sat for eleven minutes inside a test
#: run, and took the whole suite with it, because the very hook that skips
#: database tests when the database is unreachable had to connect to find out.
#:
#: Ten seconds, which is far longer than a local or same-region connection
#: needs and far shorter than a person's patience. It is a *connection*
#: deadline, not a query one: a slow query is a different problem with a
#: different answer (a statement timeout), and this must not be mistaken for
#: one.
CONNECT_TIMEOUT_SECONDS = 10

#: URL schemes the option above belongs to. ``connect_timeout`` is a libpq
#: connection parameter; SQLite's driver has no such keyword and raises
#: ``TypeError`` when handed one, and this project runs on SQLite in every
#: legacy and test path. So the option is applied by scheme rather than
#: unconditionally — trading a rare hang for a certain crash would be a poor
#: bargain.
_TIMEOUT_SCHEMES = ("postgresql", "postgres")


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
        engine = create_engine(database_url, **_engine_options(database_url))
        SessionLocal = sessionmaker(bind=engine, class_=Session)
        _engine_url = database_url


def _engine_options(database_url: str) -> dict:
    """Extra ``create_engine`` keywords for ``database_url``.

    Only the connection deadline today, and only for PostgreSQL — see
    :data:`CONNECT_TIMEOUT_SECONDS` and :data:`_TIMEOUT_SCHEMES`.
    """
    scheme = database_url.split(":", 1)[0].split("+", 1)[0].lower()
    if scheme in _TIMEOUT_SCHEMES:
        return {"connect_args": {"connect_timeout": CONNECT_TIMEOUT_SECONDS}}
    return {}


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
