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
    """AC-2: a URL that would let the fixture connect to a database whose name
    does not end in ``_test`` stops the fixture before anything connects.

    The host is TEST-NET-1 (192.0.2.1, RFC 5737), which routes nowhere, so
    even a guard that failed open could not reach a real ``nonogram_dev``
    (G-1). The spies are the actual proof: they record any attempt to build an
    engine or open a DBAPI connection, and the test asserts there was none.

    [Fix 1, F-002] The spies raise, and ``_unreachable_reason`` swallows every
    ``Exception`` and turns it into a *skip* — so a guard moved below the
    reachability check used to report SKIPPED, green in a "0 failed" gate. The
    test now turns a skip into a failure and checks the recorded attempts in a
    ``finally``, so the attempt itself is what fails it. The session's
    reachability cache is emptied for the test too: a cached verdict would
    answer without the probe the spies watch for.
    """

    @pytest.fixture(params=[
        # (what follows the host, what the refusal must name)
        ("nonogram_dev", "'nonogram_dev'"),
        ("nonogram_poc", "'nonogram_poc'"),
        ("nonogram", "'nonogram'"),
        ("test_nonogram", "'test_nonogram'"),          # contains "test" — enough for CARD-109, not here
        ("nonogram_test_backup", "'nonogram_test_backup'"),  # likewise
        # [Fix 1, F-004] The path says _test; the query sends the driver elsewhere.
        ("nonogram_test?dbname=nonogram_dev", "dbname"),
        ("nonogram_test?database=nonogram_dev", "database"),
        ("nonogram_test?sslmode=disable&DBNAME=nonogram_dev", "DBNAME"),
    ], ids=lambda case: case[0])
    def refused_case(self, request):
        return request.param

    @pytest.fixture
    def test_db_url(self, refused_case):
        return f"postgresql://someone:{_SECRET}@192.0.2.1:5432/{refused_case[0]}"

    @pytest.fixture
    def connection_attempts(self, monkeypatch):
        import psycopg2
        import sqlalchemy

        import tests.conftest as suite_conftest
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
        monkeypatch.setattr(suite_conftest, "_DATABASE_VERDICTS", {})
        return attempts

    def test_db_session_fails_without_connecting(
        self, request, refused_case, connection_attempts
    ):
        # Requested here rather than as a parameter, so the refusal is
        # something this test can catch instead of a setup error.
        try:
            with pytest.raises(pytest.fail.Exception) as refused:
                request.getfixturevalue("db_session")
        except pytest.skip.Exception as skipped:
            pytest.fail(
                f"db_session skipped instead of refusing: {skipped}", pytrace=False
            )
        finally:
            assert connection_attempts == [], (
                f"the fixture tried to connect before refusing: {connection_attempts}"
            )

        message = str(refused.value)
        assert refused_case[1] in message
        assert _SECRET not in message

    def test_an_unparseable_url_is_refused_without_echoing_it(self):
        # A port that is not a number makes make_url raise; the refusal must
        # not carry the URL (and so the password) along with it.
        with pytest.raises(pytest.fail.Exception) as refused:
            _refuse_unless_test_database(f"postgresql://u:{_SECRET}@host:notaport/nonogram_test")
        assert _SECRET not in str(refused.value)

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


#: What each AC-3 test saw of the session fixture: the engine it yielded and
#: the OID Postgres gave the ``batches`` table. A per-test rebuild yields a new
#: engine *and* creates a new table, and the OID is the database's own record
#: of that — independent of anything the fixture code says about itself.
_SESSION_SCHEMA_SEEN: list = []


def _remember_the_session_schema(test_database_tables, session_factory):
    engine, _tables = test_database_tables
    session = session_factory()
    try:
        oid = session.execute(text("SELECT 'batches'::regclass::oid")).scalar()
    finally:
        session.close()
    _SESSION_SCHEMA_SEEN.append((engine, oid))


@pytest.mark.db_required
class TestDbFixture_SchemaIsBuiltOncePerSession:
    """AC-3: no DROP per test; the schema comes from the migrations, once.

    Two signals, because each alone misses a regression:

    * ``per_test_sql`` — each test asks for ``_test_database_tables`` before
      ``per_test_sql`` starts listening, so what it sees is ``db_session``'s
      own per-test work: TRUNCATE, never DROP/CREATE/ALTER.
    * [Fix 1, F-001] That ordering also hides the session fixture's own work
      from the recording, so a ``_test_database_tables`` turned function-scoped
      — DROP SCHEMA plus alembic before every test — passed it. The first test
      therefore records the engine the fixture yielded and the ``batches``
      table's OID, and the second asserts it got the same engine and the same
      table. The two run as a pair, in file order; the second refuses to pass
      on its own, since a once-per-session property cannot be seen in one test.
    """

    def test_per_test_setup_truncates_and_never_drops_or_creates(
        self, _test_database_tables, per_test_sql, db_session
    ):
        setup_sql = [s.strip().upper() for s in per_test_sql]
        assert not [s for s in setup_sql if s.startswith(("DROP", "CREATE", "ALTER"))]
        assert [s for s in setup_sql if s.startswith("TRUNCATE")]

        _SESSION_SCHEMA_SEEN.clear()
        _remember_the_session_schema(_test_database_tables, db_session)

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

        assert len(_SESSION_SCHEMA_SEEN) == 1, (
            "run this class as a whole: the previous test records what the "
            "session fixture built, and this one compares against it"
        )
        _remember_the_session_schema(_test_database_tables, db_session)
        (first_engine, first_oid), (engine, oid) = _SESSION_SCHEMA_SEEN
        assert engine is first_engine, "the session fixture built a new engine for this test"
        assert oid == first_oid, "the batches table was dropped and recreated between tests"

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
