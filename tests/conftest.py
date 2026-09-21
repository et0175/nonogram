"""Pytest configuration and fixtures for admin panel testing."""

import pytest
import os
import sqlite3 as _sqlite3
from pathlib import Path
from sqlalchemy import event as _sqlalchemy_event, text
from sqlalchemy.engine import Engine as _SQLAlchemyEngine

# Local imports
from nonogram.admin.app import create_app
from nonogram.admin.puzzle_review import get_puzzle_review_service, MockGenerator, PuzzleReviewService
from nonogram.admin.batch_generator import get_batch_generator, BatchGenerator


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
            database_url, **db_session._engine_options(database_url)
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


@pytest.fixture(scope="function")
def db_session(test_db_url, monkeypatch):
    """Provide a fresh test database session with schema setup and teardown.

    - Sets DATABASE_URL to the test DB
    - Ensures schema exists (via alembic or Base.metadata.create_all)
    - Yields the SessionLocal factory
    - Truncates tables after test for isolation
    """
    # Asked before the schema work below, and cached for the session: a
    # database that never answers must cost one deadline for the whole run,
    # not one per test that wants it (CARD-097).
    reason = _unreachable_reason(test_db_url)
    if reason:
        pytest.skip(f"Could not set up test database: {reason}")

    # Set test DB URL in environment
    monkeypatch.setenv("DATABASE_URL", test_db_url)

    try:
        from nonogram.db import engine, SessionLocal, Base
        from nonogram.db.models import Batch, Puzzle
    except ImportError as e:
        pytest.skip(f"Database dependencies not installed: {e}")

    # Try to create schema
    try:
        # First, try to drop/recreate tables to ensure clean state
        with engine.begin() as conn:
            # Drop FK constraints first (Postgres requires this order)
            conn.execute(text("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN ('puzzles', 'batches')
            """))
            # Use CASCADE to drop dependent objects
            conn.execute(text("DROP TABLE IF EXISTS puzzles CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS batches CASCADE"))
            # Recreate tables from models
            Base.metadata.create_all(engine)
    except Exception as e:
        # If we can't access the DB, skip DB-dependent tests
        pytest.skip(f"Could not set up test database: {e}")

    yield SessionLocal

    # Teardown: truncate tables for next test
    try:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE puzzles CASCADE"))
            conn.execute(text("TRUNCATE TABLE batches CASCADE"))
    except Exception:
        pass  # Ignore teardown errors


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
