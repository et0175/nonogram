"""CARD-156 — the db_session fixture builds the schema once and erases only ``*_test``.

AC-2 runs everywhere: it never needs, and must never make, a connection.
AC-3 needs the real test database and skips without it, like every other
``db_required`` test; it is verified against ``nonogram_test``.
"""

from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from tests.conftest import _refuse_unless_test_database

REPO = Path(__file__).resolve().parent.parent

#: A password the refusal must never print.
_SECRET = "s3cr3t-pw"


class TestDbFixture_RefusesANonTestDatabase:
    """AC-2: a URL whose database name does not end in ``_test`` stops the
    fixture before anything connects.

    The host is TEST-NET-1 (192.0.2.1, RFC 5737), which routes nowhere, so
    even a guard that failed open could not reach a real ``nonogram_dev``
    (G-1). The spies are the actual proof: they record any attempt to build an
    engine or open a DBAPI connection, and the test asserts there was none.
    """

    @pytest.fixture(params=[
        "nonogram_dev",
        "nonogram_poc",
        "nonogram",
        "test_nonogram",         # contains "test" — enough for CARD-109, not here
        "nonogram_test_backup",  # likewise
    ])
    def test_db_url(self, request):
        return f"postgresql://someone:{_SECRET}@192.0.2.1:5432/{request.param}"

    @pytest.fixture
    def connection_attempts(self, monkeypatch):
        import psycopg2
        import sqlalchemy

        from nonogram.db import session as db_session_module

        attempts = []

        def spy(name):
            def record(*args, **kwargs):
                attempts.append(name)
                raise AssertionError(f"{name} called by a refused fixture")
            return record

        monkeypatch.setattr(sqlalchemy, "create_engine", spy("sqlalchemy.create_engine"))
        monkeypatch.setattr(db_session_module, "create_engine", spy("session.create_engine"))
        monkeypatch.setattr(psycopg2, "connect", spy("psycopg2.connect"))
        return attempts

    def test_db_session_fails_without_connecting(self, request, test_db_url, connection_attempts):
        # Requested here rather than as a parameter, so the refusal is
        # something this test can catch instead of a setup error.
        with pytest.raises(pytest.fail.Exception) as refused:
            request.getfixturevalue("db_session")

        name = test_db_url.rsplit("/", 1)[-1]
        message = str(refused.value)
        assert repr(name) in message
        assert _SECRET not in message
        assert connection_attempts == []

    def test_a_test_database_is_allowed(self):
        # The other side of the line, so the guard cannot pass AC-2 by
        # refusing everything. Pure: no fixture, no connection.
        _refuse_unless_test_database("postgresql://u:p@192.0.2.1:5432/nonogram_test")
        _refuse_unless_test_database("postgresql://u:p@192.0.2.1/nonogram_test?sslmode=require")


@pytest.fixture
def per_test_sql():
    """Every SQL statement any engine runs from here until the test ends."""
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", record)
    yield statements
    event.remove(Engine, "before_cursor_execute", record)


@pytest.mark.db_required
class TestDbFixture_SchemaIsBuiltOncePerSession:
    """AC-3: no DROP per test; the schema comes from the migrations, once.

    Each test asks for ``_test_database_tables`` (session-scoped, so already
    built or built now) *before* ``per_test_sql`` starts listening, and for
    ``db_session`` after it. What ``per_test_sql`` sees is therefore exactly
    ``db_session``'s own per-test work.
    """

    def test_per_test_setup_truncates_and_never_drops_or_creates(
        self, _test_database_tables, per_test_sql, db_session
    ):
        setup_sql = [s.strip().upper() for s in per_test_sql]
        assert not [s for s in setup_sql if s.startswith(("DROP", "CREATE", "ALTER"))]
        assert [s for s in setup_sql if s.startswith("TRUNCATE")]

        # Left behind on purpose: the next test must not see it.
        from nonogram.db.models import Batch

        session = db_session()
        try:
            session.add(Batch(theme="card-156"))
            session.commit()
        finally:
            session.close()

    def test_the_next_test_starts_empty_on_the_migrated_schema(
        self, _test_database_tables, per_test_sql, db_session
    ):
        setup_sql = [s.strip().upper() for s in per_test_sql]
        assert not [s for s in setup_sql if s.startswith(("DROP", "CREATE", "ALTER"))]

        from alembic.config import Config
        from alembic.script import ScriptDirectory

        # Head read from the migration scripts themselves (no env.py run), as
        # the independent side of the comparison.
        heads = ScriptDirectory.from_config(Config(str(REPO / "alembic.ini"))).get_heads()

        session = db_session()
        try:
            assert session.execute(text("SELECT count(*) FROM batches")).scalar() == 0
            version = session.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        finally:
            session.close()
        assert version == heads
