"""Pytest configuration and fixtures for admin panel testing."""

import pytest
import os
import sqlite3 as _sqlite3
from pathlib import Path
from sqlalchemy import event as _sqlalchemy_event, text
from sqlalchemy.engine import Engine as _SQLAlchemyEngine

# Local imports
from nonogram.admin.app import create_app
from nonogram.admin.puzzle_review import get_puzzle_review_service, PuzzleReviewService
from nonogram.admin.batch_generator import get_batch_generator, BatchGenerator

from tests.helpers.mock_generator import MockGenerator


# CARD-102: SQLite enforces foreign keys only when each connection asks it to;
# Postgres always does. Registered here, against the Engine class rather than
# any one engine, so that it covers every SQLite engine any test builds —
# including ones written after this card, which is the point. Per-file
# registration would leave the next DB-mode test file running the old way and
# passing for it.
#
# What it was hiding: every DB-mode test passed a fabricated batch uuid to
# add_puzzle. SQLite accepted the rows, Postgres refused all 43 of them, and
# the suite was green either way — so "the tests pass" said nothing about the
# engine production runs on.
@_sqlalchemy_event.listens_for(_SQLAlchemyEngine, "connect")
def _enforce_foreign_keys_on_sqlite(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, _sqlite3.Connection):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


#: Reachability verdicts, one per database URL, for the life of the session:
#: ``None`` when the database answered, otherwise the reason it did not.
#:
#: CARD-097. Asking the question costs a connection attempt, and since that
#: attempt now has a ten-second deadline instead of none, asking it once per
#: test is expensive in exactly the case it is meant to handle: with a
#: Postgres that listens and never answers, the ~25 `test_wave3_*` tests paid
#: two attempts each in fixture setup and the suite took eight minutes to
#: report the same 26 skips it reports in ninety seconds. The answer cannot
#: change usefully within a run, so it is taken once.
_DATABASE_VERDICTS: dict = {}


def _unreachable_reason(database_url: str):
    """Why ``database_url`` cannot be used, or ``None`` if it can.

    Probed through the same engine options production uses — including the
    connection deadline — so a database that hangs is reported as unreachable
    rather than waited on forever.
    """
    if database_url in _DATABASE_VERDICTS:
        return _DATABASE_VERDICTS[database_url]

    from sqlalchemy import create_engine

    from nonogram.db import session as db_session

    reason = None
    try:
        probe = create_engine(
            # Through production's driver naming as well as its engine options
            # (CARD-148). Without this the probe resolves the DBAPI from
            # SQLAlchemy's default while the panel names one, so on a
            # SQLAlchemy whose default is not installed every database test
            # would report "unreachable" and skip green against a database that
            # is in fact right there.
            db_session.normalized_url(database_url),
            **db_session._engine_options(database_url),
        )
        try:
            with probe.connect() as connection:
                connection.execute(text("SELECT 1"))
        finally:
            probe.dispose()
    except Exception as error:  # noqa: BLE001 - any failure means "do not use it"
        reason = str(error)
    _DATABASE_VERDICTS[database_url] = reason
    return reason


def pytest_configure(config):
    """Register custom markers; start the hang guard; check the database.

    The database check is first and raises: CARD-109's whole point is that the
    run must not begin against a database nobody chose, and beginning includes
    collection.
    """
    _database_guard.pytest_configure(config)
    _hang_guard_configure(config)
    config.addinivalue_line("markers", "unit: isolated component tests")
    config.addinivalue_line("markers", "integration: multi-component tests")
    config.addinivalue_line("markers", "e2e: end-to-end workflow tests")
    config.addinivalue_line("markers", "smoke: quick sanity checks")
    config.addinivalue_line("markers", "slow: tests that take >5 seconds")
    config.addinivalue_line("markers", "performance: performance benchmarks")
    config.addinivalue_line("markers", "db_required: tests requiring a live Postgres database")


def pytest_collection_modifyitems(config, items):
    """Skip image-dependent tests if fixtures are missing."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    skip_image_tests = not fixtures_dir.exists()

    if skip_image_tests:
        skip_marker = pytest.mark.skip(reason="Image fixtures not found in tests/fixtures/")
        for item in items:
            test_path = str(item.fspath)
            test_name = item.name if hasattr(item, "name") else ""
            # Skip tests that depend on image fixtures
            image_tests = [
                "sourcing_image", "nudge", "derive_shape", "portrait", "landscape", "bands",
                "image_fit", "image_run", "bare_size_image", "image_request", "image_bare_size",
            ]
            if any(pattern in test_path or pattern in test_name for pattern in image_tests):
                item.add_marker(skip_marker)


# CARD-097's hang guard, registered for the whole suite by importing its hook
# into this conftest's namespace. It lives in its own module so that its own
# test can load it into a subprocess with `-p tests.hang_guard` and watch it
# fire, which a hook defined here could not do.
from tests.hang_guard import (  # noqa: F401
    pytest_configure as _hang_guard_configure,
    pytest_report_header as _hang_guard_report_header,
    pytest_runtest_protocol,
)

# CARD-109's database guard, in its own module for the same reason as the hang
# guard: its own test loads it into a subprocess and watches it refuse a run,
# which a hook defined here could not do.
from tests import database_guard as _database_guard


def pytest_report_header(config):
    """Compose the two guards' header lines.

    Defined here rather than imported, because importing one name and then
    defining another of the same name would silently drop the first — and the
    hang guard's line is how a killed run's stack dump is findable.
    """
    lines = [_hang_guard_report_header(config), _database_guard.report_line()]
    said = [line for line in lines if line]
    return said or None


@pytest.fixture(scope="session")
def test_db_url():
    """Get test database URL from env or use default."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/nonogram_test"
    )


def pytest_runtest_setup(item):
    """Skip DB tests if Postgres is unreachable.

    The verdict is cached for the session (:func:`_unreachable_reason`): the
    point of this hook is to *skip quickly*, and before CARD-097 it could not
    — its own ``SELECT 1`` was the call that hung, so the skip it exists to
    produce never arrived.
    """
    markers = [m.name for m in item.iter_markers()]
    if 'db_required' in markers:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            pytest.skip("Database not reachable: DATABASE_URL is not set")
        reason = _unreachable_reason(database_url)
        if reason:
            pytest.skip(f"Database not reachable: {reason}")


#: Query parameters through which a URL can name a database other than its
#: path: the psycopg2 dialect passes ``url.query`` to the driver *after* the
#: path's ``dbname``, so ``…/nonogram_test?dbname=nonogram_dev`` connects to
#: ``nonogram_dev``; ``database`` is the same override for drivers that spell
#: it that way. Compared case-insensitively.
_DATABASE_OVERRIDE_PARAMETERS = frozenset({"dbname", "database"})


def _refuse_unless_test_database(database_url: str) -> None:
    """Stop, before any connection, unless ``database_url`` names a ``*_test`` database.

    CARD-156. The fixtures below drop the whole ``public`` schema once per
    session and truncate every table before each test, so the URL they are
    given decides which database gets wiped. That must never be anything but a
    database made for it (G-1: never ``nonogram_dev``), and the decision is
    made from the URL's text alone — asking the database would already be
    touching it.

    Stricter than CARD-109's run guard, which only asks that the name
    *contain* "test": that guard protects against reading and writing, this one
    against erasing.

    The URL is parsed with SQLAlchemy's ``make_url`` — the parser the fixture's
    engine itself is built from, so the guard reads the URL the way the
    connection will — and two things are checked: the path's database name
    ends in ``_test``, and no query parameter overrides it
    (:data:`_DATABASE_OVERRIDE_PARAMETERS`). [Fix 1, F-004] Reading only the
    path let ``…/nonogram_test?dbname=nonogram_dev`` through to a driver that
    would have connected to ``nonogram_dev``. Messages name the database and
    the parameter, never the password; an unparseable URL is refused without
    echoing it at all.

    A failure, not a skip: a skip is green, and a green run is exactly how
    "DB mode passes" came to mean "DB mode skipped". Pointing the fixture at a
    database it must not erase is a configuration mistake somebody has to see.
    """
    from sqlalchemy.engine import make_url

    try:
        url = make_url(database_url)
    except Exception:  # noqa: BLE001 - the message must not carry the URL
        url = None
    if url is None:
        pytest.fail(
            "Refusing to set up the test database: TEST_DATABASE_URL is not a "
            "URL SQLAlchemy can parse, and the db_session fixture erases the "
            "database it is given.",
            pytrace=False,
        )

    name = url.database or ""
    if not name.endswith("_test"):
        pytest.fail(
            f"Refusing to set up the test database: TEST_DATABASE_URL names "
            f"{name!r}, and the db_session fixture erases the database it is "
            f"given. Point TEST_DATABASE_URL at a database whose name ends in "
            f"'_test'.",
            pytrace=False,
        )

    overrides = sorted(
        key for key in url.query if key.lower() in _DATABASE_OVERRIDE_PARAMETERS
    )
    if overrides:
        pytest.fail(
            f"Refusing to set up the test database: TEST_DATABASE_URL names "
            f"{name!r} but its query parameter(s) {', '.join(overrides)} can make "
            f"the driver connect to a different database, and the db_session "
            f"fixture erases the database it connects to. Remove "
            f"{', '.join(overrides)} from the URL.",
            pytrace=False,
        )


@pytest.fixture(scope="session")
def _test_database_tables(test_db_url):
    """Build the schema once per session; yield an engine and the tables to truncate.

    CARD-156. The fixture this replaces dropped ``puzzles`` and ``batches``
    before every test inside an uncommitted ``engine.begin()`` and called
    ``Base.metadata.create_all(engine)`` in the same block. ``create_all``
    checks for the tables on another pooled connection, which still saw them,
    so it created nothing — and the commit then removed them. Every other test
    ran without the two tables. ``CASCADE`` also stripped whatever the
    migrations hung off them, so the schema drifted from what production runs.

    Now: the ``public`` schema is emptied and rebuilt with ``alembic upgrade
    head``, once. Emptied first because ``alembic_version`` can say head while
    the tables beneath it are gone or drifted — which is the state the old
    fixture left ``nonogram_test`` in, and the state any branch still carrying
    it will leave it in again.

    Alembic runs in a subprocess, not in-process: its ``env.py`` calls
    ``logging.config.fileConfig``, which disables every logger already created
    in this process (and so every later ``caplog`` assertion), and imports the
    models a second time as ``src.nonogram``.

    The DROP runs under a ten-second ``lock_timeout`` (a connection held open
    elsewhere becomes an error, not a hang), and the engine is disposed
    however the fixture exits — including a DROP or migration that fails.
    """
    _refuse_unless_test_database(test_db_url)
    reason = _unreachable_reason(test_db_url)
    if reason:
        pytest.skip(f"Could not set up test database: {reason}")

    import subprocess
    import sys

    from sqlalchemy import create_engine

    from nonogram.db import session as db_session

    engine = create_engine(
        db_session.normalized_url(test_db_url),
        **db_session._engine_options(test_db_url),
    )
    # [Fix 1, F-003] Disposed on every exit, not only the happy one: a DROP
    # that times out, a failed migration and the end of the session all leave
    # through the ``finally``.
    try:
        with engine.begin() as connection:
            # Same reason as the per-test TRUNCATE: several pipelines share
            # nonogram_test, and a connection one of them holds open would make
            # DROP SCHEMA wait on its lock until the hang guard killed the run.
            # This turns that wait into an error that says so.
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))

        repo = Path(__file__).resolve().parent.parent
        migrated = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(repo / "alembic.ini"), "upgrade", "head"],
            cwd=repo,
            env={**os.environ, "DATABASE_URL": test_db_url},
            capture_output=True,
            text=True,
            timeout=120,
        )
        if migrated.returncode != 0:
            pytest.fail(f"alembic upgrade head failed:\n{migrated.stderr}", pytrace=False)

        with engine.connect() as connection:
            tables = connection.execute(text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )).scalars().all()
        yield engine, tables
    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_url, request, monkeypatch):
    """Point ``DATABASE_URL`` at an empty, fully migrated test database.

    Yields the ``SessionLocal`` factory. Isolation is by ``TRUNCATE`` before
    each test, not by rolling back an outer transaction: the admin app opens
    and commits its own sessions through ``session_scope``, which a
    transaction held here would never see. Truncating at setup rather than at
    teardown means a test always starts empty even when the last one died
    mid-way.
    """
    # The guard and the reachability check come before the session fixture is
    # even requested — hence getfixturevalue rather than a parameter, which
    # pytest would resolve before this body ran. A refused URL must not get as
    # far as a connection, and an unreachable one must cost one cached deadline
    # for the whole run, not one per test (CARD-097).
    _refuse_unless_test_database(test_db_url)
    reason = _unreachable_reason(test_db_url)
    if reason:
        pytest.skip(f"Could not set up test database: {reason}")
    engine, tables = request.getfixturevalue("_test_database_tables")

    with engine.begin() as connection:
        # A session some earlier test leaked open would make TRUNCATE wait on
        # its lock forever; this turns that into an error that names it.
        connection.execute(text("SET LOCAL lock_timeout = '10s'"))
        connection.execute(text(
            "TRUNCATE TABLE " + ", ".join(f'"{table}"' for table in tables)
            + " RESTART IDENTITY CASCADE"
        ))

    monkeypatch.setenv("DATABASE_URL", test_db_url)
    from nonogram.db import SessionLocal

    yield SessionLocal


@pytest.fixture(scope="function")
def app(db_session):
    """Create Flask test app with test database.

    Depends on db_session to ensure DB schema is set up before app instantiation.
    """
    # db_session already sets DATABASE_URL via monkeypatch

    # Create app (will use DATABASE_URL env var for DB-backed services)
    test_app = create_app(debug=True)
    test_app.config["TESTING"] = True

    return test_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def puzzle_review_service():
    """Get a fresh puzzle review service for each test (not singleton)."""
    # Create a new instance instead of using the singleton
    return PuzzleReviewService()


@pytest.fixture
def batch_generator_service(puzzle_review_service):
    """Get batch generator service with puzzle review injected."""
    # Create a fresh instance for each test (not singleton)
    # This avoids test pollution from batch jobs persisting across tests
    return BatchGenerator(puzzle_review_service=puzzle_review_service)


@pytest.fixture
def generator():
    """Get nonogram generator for testing."""
    return MockGenerator(seed=2026)


@pytest.fixture
def sample_puzzle(generator):
    """Generate a single sample puzzle for testing."""
    puzzles = generator.generate_batch(count=1, sizes=[15], theme='christmas')
    return puzzles[0] if puzzles else None


@pytest.fixture
def sample_puzzles(generator):
    """Generate 10 sample puzzles for testing."""
    return generator.generate_batch(count=10, sizes=[10, 15, 20], theme='christmas')


@pytest.fixture
def cleanup_puzzles(puzzle_review_service):
    """Clean up puzzles after test."""
    yield
    # Cleanup would go here if needed
    # For now, tests are independent via transaction rollback or test DB
