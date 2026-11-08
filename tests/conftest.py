"""Pytest configuration and fixtures for admin panel testing."""

import pytest
import os
import re
import sqlite3 as _sqlite3
from pathlib import Path
from sqlalchemy import event as _sqlalchemy_event, text
from sqlalchemy.engine import Engine as _SQLAlchemyEngine

# Local imports
from nonogram.admin.app import create_app
from nonogram.admin.puzzle_review import get_puzzle_review_service, PuzzleReviewService
from nonogram.admin.batch_generator import get_batch_generator, BatchGenerator
from nonogram.admin import book_interior_vector as _book_interior_vector
from nonogram.admin import book_pdf_generator as _book_pdf_generator

from tests import db_name
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
    """Register custom markers and the diagnostic; start the hang guard; check
    the database.

    The lock check is first and the database check second, both raising:
    CARD-255's point is that the run must not *start* while another worktree
    is running the suite, and CARD-109's is that it must not begin against a
    database nobody chose. Beginning includes collection, and both land before
    any fixture exists, let alone one that connects (CARD-255 G-1).

    CARD-258's diagnostic is registered after all three, so a run one of them
    refuses never registers it; it costs nothing until an exception is being
    reported, and only then for one error class.
    """
    _full_suite_lock.pytest_configure(config)
    _database_guard.pytest_configure(config)
    _hang_guard_configure(config)
    _undefined_table_report.register(config)
    _wave_close_marker.register(config)
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

# CARD-255's full-suite lock guard, in its own module for the same reason
# again: its own tests start real runs in a subprocess and watch this refuse
# them. `pytest_terminal_summary` is imported under its own name because that
# is how it gets registered — and it, not the header line below, is what makes
# an override or an ignored stale lock visible, since `addopts = "-q"` means
# pytest prints no header at all in the runs this board actually does.
from tests import full_suite_lock as _full_suite_lock
from tests.full_suite_lock import (
    pytest_terminal_summary as _full_suite_lock_terminal_summary,
)

# CARD-258's undefined-table diagnostic. Registered as a named plugin from
# `pytest_configure` rather than imported as a hook, for two reasons: this
# conftest already owns four hook names and a fifth import would be one more
# name to keep from colliding, and a registration under a name is what
# `-p no:undefined-table-report` can block — so the diagnostic can be shown
# absent on the real suite, which is what AC-2 asks for.
from tests.helpers import undefined_table_report as _undefined_table_report

# CARD-395's wave-close marker: a registry hook in its own module, registered by
# name (`-p no:wave_close_marker` shows the suite without it). The marked test
# files carry no decorator; see the module docstring.
from tests import wave_close_marker as _wave_close_marker


def pytest_report_header(config):
    """Compose the three guards' header lines.

    Defined here rather than imported, because importing one name and then
    defining another of the same name would silently drop the first — and the
    hang guard's line is how a killed run's stack dump is findable.
    """
    lines = [
        _hang_guard_report_header(config),
        _database_guard.report_line(),
        _full_suite_lock.report_line(),
    ]
    said = [line for line in lines if line]
    return said or None


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Compose the lock guard's end-of-run line with CARD-349's.

    ``pyproject`` sets ``addopts = "-q"``, at which verbosity pytest prints no
    run header at all, so :func:`pytest_report_header` above is invisible in
    every run this board actually does. The terminal summary is the only
    channel that is not, which is why the lock guard says it twice — and why
    this card's note has to go here rather than in the header.

    Composed rather than imported. ``from tests.full_suite_lock import
    pytest_terminal_summary`` is how this hook used to arrive, and defining a
    second function of that name here would have silently dropped the lock
    guard's announcement — the trap this conftest's
    :func:`pytest_report_header` docstring already names. The lock guard's
    hook is therefore imported under a private alias and called first, so an
    overridden or ignored stale lock is still announced before anything this
    card adds.
    """
    _full_suite_lock_terminal_summary(terminalreporter, exitstatus, config)
    note = armed_database_note()
    if note:
        terminalreporter.write_line(note, yellow=True)


# --------------------------------------------------------------------------
# CARD-322 item 1 -- the test tree's default interior writer set is assembled.
# --------------------------------------------------------------------------
#
# ADR-0042/R1 makes every interior page operators, and the generator draws a
# kind it cannot write itself only through ``InteriorPageWriters``. Production
# keeps that set EMPTY by default (``NO_DOWNSTREAM_WRITERS``): the one site
# that writes an interior builds through ``book_interior_vector`` (D8), and
# every other ``BookPDFGenerator(`` refuses a kind it cannot draw. The tests
# build ``BookPDFGenerator(book)`` at several hundred sites and expect a page
# back, so for the TEST PROCESS the default is rebound to the assembled set
# (``BookPDFGenerator.__init__`` reads the module global when it is called, so
# one rebind reaches every site that did not pass ``pages=``).
#
# What this means, plainly: the test tree no longer exercises the shipped
# default. That is replaced by (1) ``SHIPPED_DEFAULT_WRITERS`` below, captured
# at import BEFORE the fixture can rebind it, which
# ``TestShippedDefault_TheTestTreesRebindDoesNotHideIt`` restores and reads,
# with a subprocess plant that rebinds the default in a copy of ``src/``; and
# (2) the ``ast`` cell in ``tests/test_book_pdf.py`` that holds every
# ``BookPDFGenerator(`` in ``src/`` to the two shapes D8 allows.
#
# SESSION scope, not function scope: a class- or module-scoped fixture that
# builds a generator runs BEFORE any function-scoped autouse fixture, and
# measured at the first attempt (144 refusals) a function-scoped rebind leaves
# exactly those fixtures on the shipped default. A test that must see the
# shipped default restores it itself, for its own duration, with
# ``monkeypatch.setattr`` -- and a child interpreter a test starts never sees
# this rebind (it imports the package afresh), so a child builds its generator
# through ``book_interior_vector.interior_generator`` as production does.
SHIPPED_DEFAULT_WRITERS = _book_pdf_generator.NO_DOWNSTREAM_WRITERS


@pytest.fixture(scope="session", autouse=True)
def _assembled_default_interior_writers():
    """Rebind the generator's default writer set to the assembled one, for the session."""
    patch = pytest.MonkeyPatch()
    patch.setattr(
        _book_pdf_generator,
        "NO_DOWNSTREAM_WRITERS",
        _book_interior_vector.DOWNSTREAM_WRITERS,
    )
    try:
        yield
    finally:
        patch.undo()


@pytest.fixture(scope="session")
def test_db_url():
    """The database the destructive fixtures below act on.

    An exported ``TEST_DATABASE_URL`` wins, verbatim. Otherwise the name is
    derived from this repo root (CARD-244, :mod:`tests.db_name`), so two
    worktrees running at once cannot erase each other's schema — which is
    what the single hardcoded ``nonogram_test`` default used to guarantee they
    would.
    """
    return db_name.resolve_test_database_url(os.environ, db_name.REPO_ROOT)


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
        # [CARD-244] When DATABASE_URL is the very database the destructive
        # fixtures resolved for this worktree, it may simply never have
        # existed: the name is derived from the repo root now, so a fresh
        # checkout's database is new. This hook runs before any fixture, so
        # without creating it here every db_required test in a new worktree
        # would skip — green, having tested nothing, which is the exact
        # failure this card exists to remove (AC-2, ADR-0038/R8).
        #
        # Narrow on purpose. It creates *only* the database the suite itself
        # resolved, and only one the refusal allows; any other DATABASE_URL —
        # the panel's own, say, under CARD-109's opt-out — is probed exactly
        # as before and never created. Nothing here can fail a test that
        # would have skipped (G-2): :func:`_unusable_reason` returns reasons.
        resolved = db_name.resolve_test_database_url(os.environ, db_name.REPO_ROOT)
        if database_url == resolved and _refusal_reason(database_url) is None:
            reason = _unusable_reason(database_url)
        else:
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

    [CARD-244] The decision itself moved into :func:`_refusal_reason`, which
    returns the message instead of raising it, so that the ``db_required``
    gate can ask the same question without turning a skip into a failure
    (G-2). This function is the only thing that raises, and it raises exactly
    the messages it raised before.
    """
    reason = _refusal_reason(database_url)
    if reason is not None:
        pytest.fail(reason, pytrace=False)


def _refusal_reason(database_url: str):
    """Why the destructive fixtures must not touch ``database_url``, or ``None``.

    The pure half of :func:`_refuse_unless_test_database`: same two checks,
    same wording, no raising and — as before — no connection. Split out by
    CARD-244 for two callers that must not raise: the ``db_required`` gate,
    which decides whether it may create a missing database, and
    :func:`_ensure_test_database`, which must be able to say "not this one"
    without failing a run that would otherwise have skipped.
    """
    from sqlalchemy.engine import make_url

    try:
        url = make_url(database_url)
    except Exception:  # noqa: BLE001 - the message must not carry the URL
        url = None
    if url is None:
        return (
            "Refusing to set up the test database: TEST_DATABASE_URL is not a "
            "URL SQLAlchemy can parse, and the db_session fixture erases the "
            "database it is given."
        )

    name = url.database or ""
    if not name.endswith("_test"):
        return (
            f"Refusing to set up the test database: TEST_DATABASE_URL names "
            f"{name!r}, and the db_session fixture erases the database it is "
            f"given. Point TEST_DATABASE_URL at a database whose name ends in "
            f"'_test'."
        )

    overrides = sorted(
        key for key in url.query if key.lower() in _DATABASE_OVERRIDE_PARAMETERS
    )
    if overrides:
        return (
            f"Refusing to set up the test database: TEST_DATABASE_URL names "
            f"{name!r} but its query parameter(s) {', '.join(overrides)} can make "
            f"the driver connect to a different database, and the db_session "
            f"fixture erases the database it connects to. Remove "
            f"{', '.join(overrides)} from the URL."
        )

    return None


#: The database a ``CREATE DATABASE`` is issued through. PostgreSQL cannot
#: create a database without being connected to another one, and ``postgres``
#: is the one every installation has. Nothing is read from it and nothing is
#: written to it; it is a doorway.
_MAINTENANCE_DATABASE = "postgres"

#: What a database name may contain for this fixture to create it: exactly the
#: characters :func:`tests.db_name.derive_test_database_name` produces.
#:
#: ADR-0039/R2 — default to deny. A derived name is always inside this set; an
#: *overridden* name need not be, and a name this cannot classify is not
#: guessed at. ``CREATE DATABASE`` takes no bind parameters, so the name has to
#: be interpolated into the statement; it is both quoted by the dialect's own
#: preparer *and* restricted to this set, because one of those two can be the
#: one that is wrong.
_CREATABLE_NAME = re.compile(r"[a-z0-9_]+\Z")

#: One creation attempt per URL per session, with the reason it failed — the
#: same reasoning as :data:`_DATABASE_VERDICTS`. ``db_session`` is
#: function-scoped and asks on every test.
_DATABASE_CREATION_ATTEMPTS: dict = {}


def _ensure_test_database(database_url: str):
    """Create the database ``database_url`` names, if it is absent.

    CARD-244. Deriving the name per worktree (:mod:`tests.db_name`) means the
    database a fresh checkout wants has never existed, and "it does not exist"
    reaches the suite as a *skip* — a green run that tested nothing, which is
    precisely the failure mode CARD-152 and ADR-0038/R8 are about. So the
    fixtures create it and carry on (AC-2).

    Returns ``None`` when the database is there (or has just been made),
    otherwise the reason it is not. The caller folds that reason into its skip
    message rather than discarding it: a creation that failed for any reason
    other than "Postgres is not running" is something somebody has to see, and
    an exception swallowed here would be invisible.

    Existence is asked of ``pg_database`` — the authority the runtime can
    enumerate (ADR-0039/R2) — not inferred from a failed connection, so an
    unreachable *server* and an absent *database* stay distinguishable.

    G-1, twice over. Every caller asks :func:`_refusal_reason` first, and this
    asks it again, because this is the function that issues DDL. Then the name
    must also match :data:`_CREATABLE_NAME`; anything else is left alone,
    uncreated, with a reason — never guessed at. Both refusals come back as a
    *reason*, not an exception: the callers that can only skip must be able to
    ask "may I create this?" without failing a run (G-2), and the one caller
    that must fail — :func:`_refuse_unless_test_database`, which every
    destructive fixture still runs first — does so on its own.

    Non-PostgreSQL URLs (SQLite, in the legacy paths) return ``None``
    untouched: there is nothing to create, and ``CREATE DATABASE`` is not a
    thing there.
    """
    if database_url in _DATABASE_CREATION_ATTEMPTS:
        return _DATABASE_CREATION_ATTEMPTS[database_url]

    # Belt and braces: every caller asks this first, and this is the one
    # function here that can bring a database into existence — "the caller
    # surely checked" is not a thing to find out about from ``nonogram_poc``.
    refused = _refusal_reason(database_url)
    if refused is not None:
        _DATABASE_CREATION_ATTEMPTS[database_url] = refused
        return refused

    from sqlalchemy import create_engine

    from nonogram.db import session as db_session

    url = db_session.normalized_url(database_url)
    if not url.get_backend_name().startswith("postgres"):
        _DATABASE_CREATION_ATTEMPTS[database_url] = None
        return None

    name = url.database or ""
    if not _CREATABLE_NAME.match(name):
        # Not refused — an existing database of that name is still perfectly
        # usable, and AC-3 says an explicit override is honoured as given. It
        # is simply not *created*, and the reason travels with the skip if it
        # turns out not to exist.
        reason = (
            f"the database {name!r} does not exist and this fixture will not "
            f"create a name outside [a-z0-9_]; create it yourself, or point "
            f"TEST_DATABASE_URL at a name it can"
        )
        _DATABASE_CREATION_ATTEMPTS[database_url] = reason
        return reason

    reason = None
    # AUTOCOMMIT because CREATE DATABASE cannot run inside a transaction
    # block, which is what SQLAlchemy would otherwise open.
    engine = create_engine(
        url.set(database=_MAINTENANCE_DATABASE),
        isolation_level="AUTOCOMMIT",
        **db_session._engine_options(database_url),
    )
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": name},
            ).scalar()
            if not exists:
                quoted = engine.dialect.identifier_preparer.quote(name)
                connection.execute(text(f"CREATE DATABASE {quoted}"))
    except Exception as error:  # noqa: BLE001 - any failure is reported, not raised
        # Not raised, because "Postgres is not running" must stay a skip and
        # not become a failure (G-2); not swallowed, because the text is the
        # only explanation of a creation that failed for some other reason.
        reason = f"could not create {name!r}: {error}"
    finally:
        engine.dispose()

    _DATABASE_CREATION_ATTEMPTS[database_url] = reason
    return reason


def _unusable_reason(database_url: str):
    """Why the destructive fixtures cannot use ``database_url``, or ``None``.

    Creation first, then reachability: a database that does not exist yet is
    made (CARD-244 AC-2), and only then is the server asked whether it
    answers. Reversing the two would cache an "unreachable" verdict for a
    database the fixture was about to create.

    When both steps fail, both reasons are reported. The skip gets longer, not
    quieter — ADR-0038/R8's principle, applied to a database rather than a
    browser.
    """
    creation = _ensure_test_database(database_url)
    reachability = _unreachable_reason(database_url)
    if reachability is None:
        return None
    if creation:
        return f"{reachability} ({creation})"
    return reachability


def _rebuild_public_schema(engine, database_url: str):
    """Empty and re-migrate ``public``, then retire any engine older than it.

    The destructive half of :func:`_test_database_tables`, lifted out of the
    fixture by CARD-252 so that the fixture and the control that pins it drive
    the *same* code. ``engine`` issues the DDL; ``database_url`` is handed to
    the Alembic subprocess. Returns the table names to truncate before each
    test (everything in ``public`` except ``alembic_version``).

    Three steps, in this order, and the order is the point:

    1. ``SET LOCAL lock_timeout`` → ``DROP SCHEMA public CASCADE`` →
       ``CREATE SCHEMA public``. Emptied first because ``alembic_version`` can
       say head while the tables beneath it are gone or drifted (CARD-156).
       The ten-second ``lock_timeout`` turns a connection somebody else holds
       open into an error rather than a hang.
    2. ``alembic upgrade head``, in a **subprocess**: its ``env.py`` calls
       ``logging.config.fileConfig``, which disables every logger already
       created in this process (and so every later ``caplog`` assertion), and
       imports the models a second time as ``src.nonogram``.
    3. :func:`nonogram.db.session.reset_engine` — **last**, so that retiring
       the engine is the final thing this routine does and no engine
       predating the new schema can exist when the fixture yields. That
       position is deliberate and **not** load-bearing.

    Why step 3 exists, why its position is not load-bearing, how that was
    measured, and what it does and does **not** pin, are CARD-252's record.
    They are on :func:`nonogram.db.session.reset_engine` (CARD-259): a
    fixture's reader needs the order, not a refutation, a re-measurement and a
    review mutant's name. Read that
    function, and the module docstring of ``tests/test_db_engine_lifecycle.py``
    it sends you to, before concluding this call fixed anything.

    That same statement carries the convention this call site stands on: a
    test retires the engine by calling that function, never by hand-setting
    ``engine``, ``SessionLocal`` or ``_engine_url`` — neither through a
    ``setattr(...)`` call nor as a ``.<name> =`` assignment — together with
    the bound on what little enforces it.
    """
    import subprocess
    import sys

    from nonogram.db import session as app_session

    with engine.begin() as connection:
        # Same reason as the per-test TRUNCATE: a connection another pipeline
        # holds open would make DROP SCHEMA wait on its lock until the hang
        # guard killed the run. This turns that wait into an error that says so.
        connection.execute(text("SET LOCAL lock_timeout = '10s'"))
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    repo = Path(__file__).resolve().parent.parent
    migrated = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(repo / "alembic.ini"), "upgrade", "head"],
        cwd=repo,
        env={**os.environ, "DATABASE_URL": database_url},
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

    # CARD-252. Last, so that no engine predating the schema above survives
    # into the run that queries it.
    app_session.reset_engine()

    return tables


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
    head``, once, and the app's module-global engine is retired afterwards —
    all three steps, with the reasons for their order, in
    :func:`_rebuild_public_schema`.

    The engine built here is disposed however the fixture exits — including a
    DROP or migration that fails.
    """
    _refuse_unless_test_database(test_db_url)
    reason = _unusable_reason(test_db_url)
    if reason:
        pytest.skip(f"Could not set up test database: {reason}")

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
        tables = _rebuild_public_schema(engine, test_db_url)
        yield engine, tables
    finally:
        engine.dispose()


# --------------------------------------------------------------------------
# CARD-349 — the armed database is ready before the first test, not before the
# first *marked* test.
# --------------------------------------------------------------------------
#
# The asymmetry this closes is not inside this file. ``pytest_runtest_setup``
# above reads ``DATABASE_URL`` and takes the create path only for an item
# carrying ``db_required`` — but conftest is not the only reader. An
# **unmarked** test that builds an admin app reaches
# ``nonogram.admin.app.create_app``, which reads ``DATABASE_URL`` itself and
# connects to whatever it names; CARD-109's guard deliberately *allows* that
# whenever the name reads as a test database. So in a worktree whose derived
# database has never existed, an unmarked test that sorts early connects
# first and the run reds before any marked test can create anything.
#
# Measured in this worktree, cold, with DATABASE_URL armed at the derived URL:
# five failures in
# ``tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine``
# ``::test_a_request_addressed_to_this_machine_is_served``, each
# ``FATAL: database "nonogram_…_test" does not exist``, in a module that also
# carries ``db_required`` tests — ``TestUndefinedTableReport_NamesWhatThe``
# ``FailingConnectionWasTalkingTo``'s among them — but *below* that class in
# the file, so they run after it. The second run of the same commit is green,
# which is the whole problem: the signature trains a re-run instead of a look.
#
# Why creating the database is **not** the fix, measured rather than reasoned.
# With the database created but no schema in it, the same five cells red again
# with ``relation "puzzles" does not exist`` — the stale-schema twin's
# signature, self-healing in exactly the same way. "Create if missing" alone
# therefore converts one self-healing red into the other and would have the
# next gate attribute it to the wrong card. What the unmarked reader needs is
# not a database but a *usable* one, so this requests the session fixture
# that builds the schema, and requests it before the first test instead of
# before the first marked test.
#
# It adds no DDL of its own, on purpose: the refusal, the creation, the
# ``DROP SCHEMA``/``alembic upgrade head`` and the engine retirement are the
# ones ``_test_database_tables`` already does, with their messages unchanged.
# For an armed full suite the work is not doubled either — that fixture is
# session-scoped, so pulling it early *moves* the one setup rather than
# adding a second. That sentence is scoped to a full suite on purpose; for an
# armed *selection* carrying zero ``db_required`` tests the rebuild is new
# work, disclosed in `_armed_database_is_ready`'s docstring rather than
# designed away.

#: What :func:`_armed_database_is_ready` decided and did, this session. Read
#: by :func:`armed_database_note`, which is what the terminal summary prints.
_ARMED_SETUP: dict = {}

#: ``DATABASE_URL`` is not set: nothing is armed and nothing is prepared.
_ARM_NOT_SET = "not-set"
#: ``DATABASE_URL`` is armed at a database that is **not** the one this
#: worktree resolved. Nothing is created — G-1 — and the run is told so.
_ARM_ELSEWHERE = "elsewhere"
#: ``DATABASE_URL`` is the resolved database but :func:`_refusal_reason`
#: refuses it. Nothing is created, and the refusal is the note.
_ARM_REFUSED = "refused"
#: ``DATABASE_URL`` is the resolved database and may be prepared.
_ARM_PREPARE = "prepare"


def _database_name_of(database_url):
    """The database a URL names, and never its credentials.

    Through ``make_url`` — the parser :func:`_refusal_reason` and the
    fixtures' own engines read the URL with — so the name in a note is the
    name the connection would use. An unparseable URL comes back as a
    placeholder rather than as itself: notes get pasted into issues and chat,
    and the one thing that must never travel is the password.
    """
    from sqlalchemy.engine import make_url

    try:
        return make_url(database_url).database or ""
    except Exception:  # noqa: BLE001 - the note must not carry the URL
        return "<a URL SQLAlchemy cannot parse>"


def _armed_database_plan(environ):
    """What may be prepared for ``environ``, decided without connecting.

    Returns ``(database_url, resolved, action)`` where *action* is one of
    :data:`_ARM_NOT_SET`, :data:`_ARM_ELSEWHERE`, :data:`_ARM_REFUSED` or
    :data:`_ARM_PREPARE`.

    Pure, and deliberately the *same* two questions
    :func:`pytest_runtest_setup` asks before it creates anything — the URL is
    the one this worktree resolved, and :func:`_refusal_reason` allows it —
    so there is one rule about what may be brought into existence and not
    two. Default to deny (ADR-0039/R2): every branch but
    :data:`_ARM_PREPARE` creates nothing, and a URL this cannot classify
    cannot reach the one that does.
    """
    database_url = environ.get("DATABASE_URL")
    if not database_url:
        return None, None, _ARM_NOT_SET
    resolved = db_name.resolve_test_database_url(environ, db_name.REPO_ROOT)
    if database_url != resolved:
        return database_url, resolved, _ARM_ELSEWHERE
    if _refusal_reason(database_url) is not None:
        return database_url, resolved, _ARM_REFUSED
    return database_url, resolved, _ARM_PREPARE


def armed_database_note():
    """The line the terminal summary owes this run, or ``None``.

    Silent on the two outcomes that need no words — ``DATABASE_URL`` unset,
    and a database that was prepared — because a line on every run is a line
    nobody reads by the third one. Otherwise it names the database by name and
    says what to do about it, which is the half of AC-1 that holds when the
    other half cannot: a bare ``psycopg2`` ``FATAL`` several screens into a
    traceback is not an instruction.
    """
    action = _ARMED_SETUP.get("action")
    if action in (None, _ARM_NOT_SET):
        return None
    database = _ARMED_SETUP.get("database")
    if action == _ARM_ELSEWHERE:
        return (
            f"database setup: DATABASE_URL names {database!r}, which is not the "
            f"database this worktree resolved ({_ARMED_SETUP.get('resolved')!r}), "
            f"so the suite neither created nor migrated it. Tests that build an "
            f"admin app will connect to {database!r} as given, and if it does "
            f"not exist they fail with the driver's own error. Create it, point "
            f"DATABASE_URL (or TEST_DATABASE_URL) at the resolved database, or "
            f"unset DATABASE_URL."
        )
    if action == _ARM_REFUSED:
        return (
            f"database setup: nothing was prepared for {database!r} — "
            f"{_ARMED_SETUP.get('reason')}"
        )
    reason = _ARMED_SETUP.get("reason")
    if reason:
        return (
            f"database setup: {database!r} could not be prepared before the "
            f"first test — {reason}. Every test that reads DATABASE_URL will "
            f"meet that database as it is. Fix the reason, or unset "
            f"DATABASE_URL to run the suite without a database."
        )
    return None


@pytest.fixture(scope="session", autouse=True)
def _armed_database_is_ready(request):
    """Bring the armed database to a usable state before the first test.

    Autouse and session-scoped, which is what buys the ordering: pytest sets
    up the widest scopes first, so this runs during the setup of whichever
    item happens to sort first — before any test body, and therefore before
    any unmarked test can reach ``create_app`` and read ``DATABASE_URL``.
    Nothing here depends on which item that is, which is the point: the
    exposed set cannot be enumerated (see
    ``tests/test_card_349_cold_database.py``), so the fix must not need it.

    Free when ``DATABASE_URL`` is unset — the ordinary run, and the one every
    ``db_required`` skip on this board comes from. No count is given for those
    skips, and this sentence's own history is the argument: it used to carry
    one — "this card's own module adds two ``db_required`` tests" — and the
    next commit on this very card added a third, so the figure was already
    wrong where it stood. It is deleted rather than corrected, because
    ``-rEfs`` answers it per run and cannot go stale. It is only an armed run
    that pays anything, and an armed run has already said which database it
    means.

    **No count of the ways ``_test_database_tables`` can stop is given here,
    and that is the point of review cycle 1's F-001.** This docstring used to
    say "both ways … are caught" beside a clause naming two classes, and the
    claim was false: ``_rebuild_public_schema`` sets ``lock_timeout`` and then
    runs ``DROP SCHEMA public CASCADE``, which under a lock another connection
    holds raises ``sqlalchemy.exc.OperationalError``; the Alembic subprocess
    raises ``subprocess.TimeoutExpired`` at its ``timeout=120``; the
    ``pg_tables`` projection adds a third. Measured: none of those is a
    subclass of ``pytest.skip.Exception`` or ``pytest.fail.Exception``. A
    counted claim about a set nothing enumerates is indistinguishable from a
    true one until something falls through, so the catch is stated by its
    **bound** instead, and the bound is what the except clauses say.

    Why an escape here is worse than an escape anywhere else, which is the
    irony this card has to own: before this fixture existed, a stop from
    ``_test_database_tables`` reached only the items that asked for the schema
    — the ``db_required`` tests. Out of a session-scoped **autouse** fixture it
    reaches every item in the suite, because pytest caches a session fixture's
    outcome and re-raises it to every later requester, and every one of those
    errors names ``_armed_database_is_ready``. An unrelated held lock would
    therefore read as this card's own fix being broken, on the card whose whole
    subject is misattribution.

    So the catch is wide, and nothing is made quieter by it (G-2,
    ADR-0038/R8):

    * ``pytest.skip`` and ``pytest.fail`` are named **first and explicitly,
      and that is not stylistic**: both derive from ``OutcomeException``,
      which derives from ``BaseException`` and **not** from ``Exception``, so
      an ``except Exception`` that dropped them would let a skip out of a
      session-autouse fixture and skip the entire suite. Measured in a
      synthetic project: catching ``Exception`` alone turns a stopped
      preparation into ``3 skipped`` / ``3 errors`` where the tuple gives
      ``1 passed, 2 skipped`` / ``1 passed, 2 errors``.
    * ``Exception`` covers the rest — the ``OperationalError``, the
      ``TimeoutExpired`` and whatever the next edit to
      ``_rebuild_public_schema`` adds, without this fixture having to be
      taught each one.
    * It stops at ``Exception`` rather than ``BaseException`` on purpose:
      ``KeyboardInterrupt`` and ``SystemExit`` must still end the run.
      Measured too — a ``BaseException`` that is not an ``OutcomeException``
      escapes a session fixture into a pytest-internal ``assert not
      self._finalizers`` identically whether this fixture swallows it or not,
      so widening to ``BaseException`` would buy nothing and cost the
      interrupt.

    Nothing is lost by being caught here, and that is **measured rather than
    reasoned**, because it is the whole safety argument: pytest caches a
    session fixture's outcome, exception included, so the first ``db_required``
    test that asks for ``db_session`` gets the identical stop through the
    unchanged path. In a synthetic project, an autouse session fixture that
    swallows an inner session fixture's stop still leaves a later direct
    requester skipped (for ``pytest.skip``) or errored (for ``pytest.fail``
    **and for a plain ``Exception`` subclass**), with the original reason, via
    both a direct parameter and a function-scoped fixture's
    ``getfixturevalue`` — while the unrelated test that never asks passes. The
    control is the same run with the swallow removed.
    ``test_the_eager_setup_hides_nothing_from_the_marked_path`` is the
    in-tree control for the structural half.

    A stop is **announced**, not merely swallowed, and the two kinds are
    recorded differently on measured grounds rather than taste. ``skip`` and
    ``fail`` from ``_test_database_tables`` carry a message that fixture
    composed for a reader ("Could not set up test database: …", "alembic
    upgrade head failed: …"), so their ``str`` is already a sentence and a
    ``Skipped:`` prefix would only pad it. An undesigned escape's ``str`` need
    not be legible at all — ``str(KeyError("tablename"))`` is ``'tablename'``,
    and ``OperationalError``'s names the wrapped driver class but not its own
    — so those are recorded as ``"{class name}: {message}"``. The class name
    is the datum: it is what distinguishes "the database is unavailable" from
    "something is badly wrong". The note's *instruction* is deliberately
    **not** varied with it; "fix the reason, or unset DATABASE_URL" is true of
    both kinds, and there is no evidence here for a second instruction.

    So widening the catch **restores** the pre-fix blast radius rather than
    silencing anything: every item that asks for the database still stops
    loudly, from the cache, carrying the original reason; only the items that
    never ask proceed — which is exactly the set that proceeded before this
    fixture existed. The fixture already fails narrowly, *via the cache,
    provided it catches*. Narrowing the catch is what widens the damage, which
    is the inversion that made F-001 easy to miss.
    ``test_a_swallowed_stop_still_errors_every_test_that_asks_for_the_database``
    is the behavioural control for that, against the real suite with a stop
    injected at the ``_rebuild_public_schema`` seam.

    What this adds is the note: the reason is named once, at the end, where
    ``-q`` cannot hide it.

    One residue, named rather than folded in (ADR-0039/R3), because no probe
    on this card has touched it: ``_rebuild_public_schema`` runs ``DROP
    SCHEMA`` → ``CREATE SCHEMA`` → ``alembic upgrade head`` →
    ``reset_engine()``, so a stop *between* the drop and the end of the
    migration leaves an **empty** schema behind **and** skips
    ``reset_engine()``, leaving a module-global engine that predates it. This
    fixture records and announces that stop correctly; it does not repair that
    state, and nothing here claims it does. Out of scope for this card
    deliberately — the owner is carding it.

    One cost, disclosed rather than redesigned (ADR-0039/R3, filed as review
    cycle 1's F-002): being autouse, this requests the schema fixture on every
    armed run, so an armed **selection** containing zero ``db_required`` tests
    now pays the ``DROP SCHEMA``/``alembic upgrade head`` rebuild where it
    previously did nothing. The paragraph above about the work not being
    doubled is scoped to an armed *full* suite, where it holds because the
    fixture is session-scoped; it does not speak for the selection case, and
    this sentence is what keeps that from reading as a claim.
    """
    database_url, resolved, action = _armed_database_plan(os.environ)
    _ARMED_SETUP.clear()
    _ARMED_SETUP["action"] = action
    if action == _ARM_NOT_SET:
        return
    _ARMED_SETUP["database"] = _database_name_of(database_url)
    _ARMED_SETUP["resolved"] = _database_name_of(resolved)
    if action == _ARM_REFUSED:
        _ARMED_SETUP["reason"] = _refusal_reason(database_url)
        return
    if action == _ARM_ELSEWHERE:
        return
    try:
        request.getfixturevalue("_test_database_tables")
    except (pytest.skip.Exception, pytest.fail.Exception) as stopped:
        # Named first, and not for style: OutcomeException derives from
        # BaseException, so the clause below would not catch these.
        _ARMED_SETUP["reason"] = str(stopped)
    except Exception as stopped:  # noqa: BLE001 - see the docstring's bound
        # An undesigned stop. Its class is the diagnostic, and str() alone
        # need not carry it (KeyError's is a bare quoted word).
        _ARMED_SETUP["reason"] = f"{type(stopped).__name__}: {stopped}"


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
    reason = _unusable_reason(test_db_url)
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
