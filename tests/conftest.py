"""Pytest configuration and fixtures for admin panel testing."""

import pytest
import os
from pathlib import Path
from sqlalchemy import text

# Local imports
from nonogram.admin.app import create_app
from nonogram.admin.puzzle_review import get_puzzle_review_service, MockGenerator, PuzzleReviewService
from nonogram.admin.batch_generator import get_batch_generator, BatchGenerator


def pytest_configure(config):
    """Register custom pytest markers."""
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


@pytest.fixture(scope="session")
def test_db_url():
    """Get test database URL from env or use default."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/nonogram_test"
    )


def pytest_runtest_setup(item):
    """Skip DB tests if Postgres is unreachable."""
    markers = [m.name for m in item.iter_markers()]
    if 'db_required' in markers:
        # Try to import and ping the DB
        try:
            from nonogram.db import engine
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            pytest.skip(f"Database not reachable: {e}")


@pytest.fixture(scope="function")
def db_session(test_db_url, monkeypatch):
    """Provide a fresh test database session with schema setup and teardown.

    - Sets DATABASE_URL to the test DB
    - Ensures schema exists (via alembic or Base.metadata.create_all)
    - Yields the SessionLocal factory
    - Truncates tables after test for isolation
    """
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
