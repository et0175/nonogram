"""Database session management."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
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

#: The PostgreSQL DBAPI this project installs, and therefore the only one it
#: may be connected through (CARD-148).
#:
#: ``psycopg2-binary`` is what ``requirements.txt`` and pyproject's ``db``
#: extra ship, and this constant is the code saying so out loud. Before it,
#: ``DATABASE_URL`` reached :func:`create_engine` exactly as the environment
#: gave it, so a bare ``postgresql://`` — which is the only shape Render's
#: managed Postgres hands out — left the choice of DBAPI to whatever
#: SQLAlchemy's default happened to be on the day of the build. On 2026-09-25
#: that default moved: SQLAlchemy 2.1.0 resolves a bare ``postgresql://`` to
#: ``psycopg`` (v3) rather than ``psycopg2``, the next deploy resolved
#: ``sqlalchemy>=2.0`` to it, and the panel stopped booting with
#: ``ModuleNotFoundError: No module named 'psycopg'`` without a single line of
#: this repository having changed.
#:
#: Naming the driver is the fix, and it is deliberately *this* driver rather
#: than psycopg 3: moving the database packages is out of scope here
#: (ADR-0006/R1 keeps them in the ``db`` extra, and swapping one for another is
#: a decision, not a defect fix). Upgrading later means changing this one name
#: and the extra together — which is the whole point of there being one name.
POSTGRES_DRIVER = "psycopg2"

#: The canonical backend name for every spelling in :data:`_TIMEOUT_SCHEMES`.
#: Render still issues the legacy ``postgres://`` alias that SQLAlchemy dropped
#: in 1.4, so normalising the backend is not cosmetic: ``make_url`` parses
#: ``postgres://`` happily and then ``get_dialect()`` raises ``NoSuchModuleError``.
_POSTGRES_BACKEND = "postgresql"


def normalized_url(database_url: str) -> URL:
    """``database_url`` as a :class:`~sqlalchemy.engine.URL` that names its driver.

    For a PostgreSQL URL the backend is canonicalised to ``postgresql`` and,
    when the URL does not already name a DBAPI, :data:`POSTGRES_DRIVER` is
    filled in — so ``postgres://…`` and ``postgresql://…`` both become
    ``postgresql+psycopg2://…``. A URL that *does* name one is left with it:
    the defect this closes is inheriting a default, and an explicit
    ``postgresql+psycopg://`` is somebody's decision, not an accident. Every
    non-PostgreSQL URL (SQLite, in every legacy and test path here) is returned
    untouched.

    Nothing else about the URL moves — host, port, database, query parameters
    and credentials are carried by the :class:`URL` object itself rather than
    reassembled from text, which is the only way to be sure of that. Returning
    the object rather than a string is part of the same care: ``str(url)``
    renders the password as ``***``, so a caller that went through text would
    quietly hand :func:`create_engine` a URL it cannot authenticate with.

    Raises:
        RuntimeError: if ``database_url`` is not a URL SQLAlchemy can parse.
            The message names the scheme and nothing else, and the underlying
            ``ArgumentError`` is deliberately *not* chained: SQLAlchemy has
            echoed the offending string back in that message before, and that
            string is the one place a password lives (EC-1).
    """
    try:
        url = make_url(database_url)
    except ArgumentError:
        raise RuntimeError(
            "DATABASE_URL is not a URL SQLAlchemy can parse "
            f"(scheme: {_scheme_of(database_url)!r}). "
            "Expected something like postgresql://user:password@host:5432/dbname"
        ) from None

    backend, _, driver = url.drivername.partition("+")
    if backend.lower() not in _TIMEOUT_SCHEMES:
        return url
    return url.set(
        drivername=f"{_POSTGRES_BACKEND}+{(driver or POSTGRES_DRIVER).lower()}"
    )


def _scheme_of(database_url: str) -> str:
    """The text before ``://``, which is the one part that cannot be a secret.

    Credentials follow the separator, and :meth:`str.partition` splits on its
    first occurrence, so what comes back is a scheme or nothing at all — never
    a password, however mangled the rest of the string is.
    """
    scheme, separator, _ = database_url.partition("://")
    return scheme if separator else "<no scheme>"


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
        # The normalised URL goes to create_engine (CARD-148); the raw value
        # stays the cache key, because it is what the environment will be
        # compared against on the next call.
        engine = create_engine(
            normalized_url(database_url), **_engine_options(database_url)
        )
        SessionLocal = sessionmaker(bind=engine, class_=Session)
        _engine_url = database_url


def _engine_options(database_url: str) -> dict:
    """Extra ``create_engine`` keywords for ``database_url``.

    Only the connection deadline today, and only for PostgreSQL — see
    :data:`CONNECT_TIMEOUT_SECONDS` and :data:`_TIMEOUT_SCHEMES`.

    Takes the *raw* ``DATABASE_URL`` rather than the normalised one, so both
    spellings in :data:`_TIMEOUT_SCHEMES` are still live here. That makes the
    scheme it reads one step removed from the one :func:`create_engine` ends up
    with, which is why ``test_the_connect_deadline_still_reaches_a_normalised_url``
    pins that CARD-097's deadline survived CARD-148's rewrite.
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
