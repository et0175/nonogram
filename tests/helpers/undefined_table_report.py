"""CARD-258 -- make the next ``relation "puzzles" does not exist`` say what it
was talking to.

The same red has appeared on this board's build gates in waves 47, 48 and 50:
five failures in
``tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine``,
``relation "puzzles" does not exist`` raised while the fixture owned the
schema, every occurrence solo, guard-enforced, and green on a re-run of the
same commit. Two explanations have been offered and both are dead -- psycopg2
has no ``prepare_threshold`` (wave 45), and CARD-252's ``reset_engine()`` is in
the tree that CARD-256's gates still ran red then green on. CARD-252's own
record -- what its gates measured, and what its fix does and does not pin --
is kept on :func:`nonogram.db.session.reset_engine`.

So this module is not a third hypothesis and it fixes nothing. It records, on
the next occurrence, the four things no traceback currently shows:

1. which database the failing connection was attached to,
2. which engine object the process had, and how many times it had been retired,
3. which process and thread, and whether a werkzeug server frame is involved,
4. what the schema actually held at that moment.

"The table is missing" and "we were looking in the wrong place" are different
failures with the same message, and today's output cannot tell them apart.

Two traps, and how each is answered
-----------------------------------
**The capture must not go through the connection that failed.** That
connection is in an aborted transaction -- libpq refuses every further
statement on it with ``InFailedSqlTransaction`` -- so the obvious
implementation reports nothing on exactly the run it was built for. Groups 1
and 2 are therefore read from the failing connection's **libpq attributes
only**, which answer while the transaction is aborted and issue no SQL; every
question that needs SQL is asked on a **separate** connection opened here
(group 4). ``test_the_capture_answers_while_the_failing_connection_cannot``
holds both halves.

**It must be free on the runs that pass.** The module implements exactly one
hook, ``pytest_exception_interact``, which pytest calls only while an
exception is being reported -- never per test on the happy path (G-4). That it
is the only hook here is held mechanically by
``test_the_plugin_implements_exactly_one_hook_and_it_is_the_failure_one``, and
that it changes nothing on a passing or ordinarily-failing run is held by two
byte comparisons (AC-3, AC-4).

What it is **not**
------------------
* It does not name the engine the failing connection came out of. Nothing in
  the exception names one: all it carries is a DBAPI connection, so group 2
  reports the process's module-global engine beside that connection's dbname
  and leaves the two for a reader to compare. A failing connection from some
  other engine would be reported with ``dbname_matches_app_engine=no`` and
  nothing further. Group 4's verdict compares the same two names once more
  under the label ``vs-app-engine`` -- still a comparison of databases and
  not a provenance of connections -- and keeps the capture connection's own
  database on a separately labelled pair, because that one answers a
  different question (whether ``schema-now`` describes the same database)
  and is legitimately different whenever ``DATABASE_URL`` and
  ``TEST_DATABASE_URL`` disagree.
* It does not report the failing connection's ``search_path``. That needs a
  query, and the one connection that could answer it is the one that cannot be
  queried. The capture connection's ``search_path`` is reported as the capture
  connection's, labelled as such, and ``pg_stat_activity`` is asked about the
  failing **backend** instead -- which does give its database from the server's
  side, independently of libpq.
* It does not fire on the other variant these gates produced (a ``UUID``
  column arriving as a float). That is a different exception class and this
  hook is silent for it.

Why a named plugin rather than a hook imported into the conftest: a
registration under :data:`PLUGIN_NAME` is what ``-p no:undefined-table-report``
can block, so the diagnostic can be shown absent on the real suite.
"""

from __future__ import annotations

import os
import sys
import threading

__all__ = [
    "PLUGIN_NAME",
    "SECTION_NAME",
    "UNDEFINED_TABLE_SQLSTATE",
    "describe",
    "pytest_exception_interact",
    "register",
    "undefined_table_error",
]

#: The name the conftest registers this module under, and therefore the name
#: ``-p no:...`` blocks it by.
PLUGIN_NAME = "undefined-table-report"

#: The section heading the report is attached under. Carries the card number
#: because the next person to see it will want to know why it is there.
SECTION_NAME = "CARD-258 undefined-table binding"

#: PostgreSQL's ``undefined_table``. The whole error class this hook answers
#: to; every other sqlstate, and every non-database failure, leaves it silent.
UNDEFINED_TABLE_SQLSTATE = "42P01"

#: How far the exception chain is walked. A bound rather than a loop: a
#: diagnostic that hangs on a cyclic ``__context__`` would be worse than none.
_CHAIN_LIMIT = 32

#: How much of any one value reaches the report. Every line is one line, so a
#: long statement is cut rather than wrapped.
_VALUE_LIMIT = 240

#: The libpq dsn keys worth printing. A whitelist, not a filter: psycopg2's
#: ``get_dsn_parameters()`` already omits the password, and naming the keys
#: means a future libpq that adds one cannot widen what this prints.
_DSN_KEYS = ("dbname", "host", "port", "user", "options")


def register(config):
    """Register this module as a plugin named :data:`PLUGIN_NAME`.

    Returns ``None`` when the name is blocked (``-p no:...``), which is how
    the diagnostic is shown absent without editing anything, and also when
    this module is **already** registered -- which happens when a run loads
    it by its import path (``-p tests.helpers.undefined_table_report``) and
    then lets the conftest register it too. pluggy refuses one plugin object
    under a second name, so without that check the run dies at configure
    time with ``INTERNALERROR> ValueError: Plugin already registered under a
    different name``. A diagnostic whose whole contract is "never make a run
    worse" does not get to end one.

    What the check restores is the run, not the registration: under
    ``-p <import path>`` pytest has already registered this module under
    *that* name, so ``hasplugin(PLUGIN_NAME)`` is false and
    ``test_the_diagnostic_is_registered_in_this_very_run`` reds -- one
    informative failure instead of an aborted session. No documented
    invocation takes that path (``addopts`` is ``-q``; the probes run under
    their own rootdir, where this conftest is not loaded).
    """
    if config.pluginmanager.is_registered(sys.modules[__name__]):
        return None
    return config.pluginmanager.register(sys.modules[__name__], PLUGIN_NAME)


def pytest_exception_interact(node, call, report):
    """Attach the binding report when -- and only when -- this is the error class."""
    excinfo = getattr(call, "excinfo", None)
    error = undefined_table_error(getattr(excinfo, "value", None))
    if error is None:
        return
    try:
        lines = describe(error, excinfo)
    except (KeyboardInterrupt, SystemExit):
        # Control flow, not a diagnostic failure. The capture can wait on a
        # connection for up to ``CONNECT_TIMEOUT_SECONDS``, and a Ctrl-C that
        # lands in that window must stop the run rather than be formatted
        # into a report line and carried on from.
        raise
    except BaseException as failure:  # noqa: BLE001 - named, never swallowed
        # A diagnostic that masks the defect it was built for is worse than
        # none (AC-5). Nothing here may escape into pytest's reporting, and
        # nothing here may disappear either.
        lines = [f"the diagnostic itself failed: {_named(failure)}"]
    try:
        _attach(report, "\n".join(lines))
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:  # noqa: BLE001 - the channel itself is gone
        # :func:`_attach` is the only channel this hook has, so a failure
        # *in* it cannot be named -- it can only be kept out of pytest's
        # reporting, where it would mask the very failure AC-5 exists to
        # protect. **Declared bound:** a report whose ``longrepr`` rejects
        # both spellings carries no section and says nothing about why.
        pass


# --------------------------------------------------------------------------
# The decision: is this the error class?
# --------------------------------------------------------------------------


def undefined_table_error(exc):
    """The ``undefined_table`` error in ``exc``'s chain, or ``None``.

    Two spellings are accepted and both are live, for different inputs:

    * ``pgcode == "42P01"`` -- the sqlstate, read from whatever carries it.
      **Declared reach:** no real psycopg2 error reaches this arm without also
      matching the one below, because psycopg2 maps that sqlstate onto
      ``UndefinedTable`` itself. What exercises it is the fabrication in
      ``test_the_detector_fires_on_the_error_class_and_nothing_else[pgcode]``,
      and what it is *for* is a driver whose class is not psycopg2's. That is a
      declared bound, not a measured one.
    * ``isinstance(..., psycopg2.errors.UndefinedTable)`` -- the class, which
      is the arm every provoked error takes, and the only arm a hand-built
      error can take (``pgcode`` is a read-only C attribute that such an
      instance leaves ``None``).

    The chain is walked over ``orig``, ``__cause__`` and ``__context__``
    together, because SQLAlchemy wraps the driver's error in a
    ``ProgrammingError`` and only the inner object carries the sqlstate.
    """
    for candidate in _chain(exc):
        if _is_undefined_table(candidate):
            return candidate
    return None


def _is_undefined_table(candidate) -> bool:
    if getattr(candidate, "pgcode", None) == UNDEFINED_TABLE_SQLSTATE:
        return True
    undefined_table = _undefined_table_class()
    return undefined_table is not None and isinstance(candidate, undefined_table)


def _undefined_table_class():
    """psycopg2's ``UndefinedTable``, or ``None`` if psycopg2 is not there.

    Imported here rather than at module scope so that importing this module
    costs nothing and cannot fail: it is imported by the conftest, on every
    run, including ones with no database in sight.
    """
    try:
        import psycopg2.errors
    except Exception:  # noqa: BLE001 - no driver means no verdict
        return None
    return getattr(psycopg2.errors, "UndefinedTable", None)


def _chain(exc):
    """``exc`` and everything reachable from it, breadth-first and bounded.

    All three links are followed rather than one: ``orig`` is SQLAlchemy's
    name for the driver error, ``__cause__`` is what ``raise ... from`` sets,
    and ``__context__`` is what an exception raised inside a handler carries.
    Identity-compared, so a cycle terminates.
    """
    found: list = []
    queue = [exc]
    while queue and len(found) < _CHAIN_LIMIT:
        current = queue.pop(0)
        if current is None or any(item is current for item in found):
            continue
        found.append(current)
        for attribute in ("orig", "__cause__", "__context__"):
            queue.append(getattr(current, attribute, None))
    return found


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def describe(error, excinfo=None) -> list[str]:
    """The four groups, one line each, in the card's order.

    Every group is built inside its own guard, so one unanswerable question
    costs its own line and not the report. Every group emits its label
    whatever happened, because a label with a reason behind it is a datum and
    a missing label is a puzzle.
    """
    # Searched from the **top** of the chain, not from ``error``: SQLAlchemy's
    # wrapper is what carries ``statement``, and the inner driver error this
    # hook fired on has no link back up to it.
    root = getattr(excinfo, "value", None)
    if root is None:
        root = error
    dbapi = _dbapi_connection(root)
    lines: list[str] = []
    lines += _guarded("group-1", lambda: _failing_connection_lines(error, dbapi, root))
    lines += _guarded("group-2", lambda: _engine_lines(dbapi))
    lines += _guarded("group-3", lambda: _process_lines(excinfo))
    lines += _guarded("group-4", lambda: _capture_lines(dbapi))
    return lines


def _guarded(group: str, build) -> list[str]:
    """``build()``, or one line naming why it could not answer.

    ``KeyboardInterrupt`` and ``SystemExit`` are re-raised ahead of the catch
    rather than reported: they are the run being stopped, not a question the
    diagnostic failed to answer, and turning a Ctrl-C into
    ``group-N unavailable`` would make the run carry on past it. Every
    :class:`BaseException` handler in this module is preceded by that
    re-raise, and
    ``test_no_guard_in_the_diagnostic_absorbs_control_flow``
    holds that over the module's own AST rather than over this one site.
    """
    try:
        return build()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - named, never swallowed
        return [f"{group} unavailable: {_named(failure)}"]


# -- group 1: the failing connection, from libpq only ----------------------


def _failing_connection_lines(error, dbapi, root) -> list[str]:
    """Which database the failing connection was attached to.

    Read from libpq attributes and **no SQL**: ``get_dsn_parameters()`` and
    ``get_backend_pid()`` answer from the client's own handle, so they answer
    while the transaction is aborted -- which is the state this connection is
    always in by the time this runs.
    """
    if dbapi is None:
        first = (
            "group-1 failing-connection: unavailable, the error carries no "
            "cursor so there is no connection to read"
        )
    else:
        parameters = dbapi.get_dsn_parameters()
        fields = " ".join(
            f"{key}={_one_line(parameters.get(key))}" for key in _DSN_KEYS
        )
        first = (
            f"group-1 failing-connection: {fields} "
            f"backend_pid={dbapi.get_backend_pid()} "
            f"libpq_status={_libpq_name('STATUS_', dbapi.status)} "
            f"txn_status={_libpq_name('TRANSACTION_STATUS_', dbapi.get_transaction_status())} "
            f"[libpq attributes, no SQL]"
        )
    diagnostics = getattr(error, "diag", None)
    return [
        first,
        f"group-1 failing-statement: {_one_line(_statement_of(root))}",
        (
            f"group-1 error: class={type(error).__module__}.{type(error).__name__} "
            f"sqlstate={_one_line(getattr(error, 'pgcode', None))} "
            f"schema={_one_line(getattr(diagnostics, 'schema_name', None))} "
            f"table={_one_line(getattr(diagnostics, 'table_name', None))} "
            f"message={_one_line(getattr(diagnostics, 'message_primary', None) or error)}"
        ),
    ]


def _dbapi_connection(root):
    """The DBAPI connection the error was raised on, if it carries one.

    psycopg2 hangs the cursor off the error object, and the cursor holds its
    connection; the traceback keeps both alive. When there is no cursor --
    a hand-built error, a failure raised before execution -- this is ``None``
    and group 1 says so.
    """
    for candidate in _chain(root):
        cursor = getattr(candidate, "cursor", None)
        connection = getattr(cursor, "connection", None)
        if connection is not None:
            return connection
    return None


def _statement_of(root):
    """The SQL text, from whichever link in the chain carries it."""
    for candidate in _chain(root):
        statement = getattr(candidate, "statement", None)
        if statement:
            return statement
    return None


def _libpq_name(prefix: str, value) -> str:
    """psycopg2's own name for one of its status integers.

    Enumerated from ``psycopg2.extensions`` rather than tabulated here
    (ADR-0039/R2: the authority the runtime can enumerate). A value the module
    has no name for is printed as the integer it is, never guessed at.
    """
    try:
        import psycopg2.extensions as extensions
    except Exception:  # noqa: BLE001
        return str(value)
    names = sorted(
        name[len(prefix):]
        for name in dir(extensions)
        if name.startswith(prefix) and getattr(extensions, name) == value
    )
    return names[0] if names else str(value)


# -- group 2: the engine ---------------------------------------------------


def _engine_lines(dbapi) -> list[str]:
    """Which engine object this process had, and how often it was retired.

    The reset count is :func:`nonogram.db.session.reset_count`, an additive
    read-only accessor added by this card. G-1 -- nothing in ``src/`` reaches
    it -- is held by ``test_nothing_in_src_calls_the_reset_counter`` over the
    AST of every file under ``src``, in the reach that test declares: no
    call, no bare name or attribute reference, and no string spelling of the
    name, plus a deny-default on the call sites whose callee it cannot name,
    which are held to an equality over counted sites against a declared
    exemption list -- so a second site under a key that already has one reds
    rather than being absorbed. What that test does **not**
    see is listed at it, and the call shapes that reach a function without
    naming it anywhere (a name computed at runtime) are not among the shapes
    it enumerates but are among the things its deny-default reds on.
    """
    from nonogram.db import session as app_session

    engine = app_session.engine
    if engine is None:
        first = (
            "group-2 app-engine: none, no engine has been built in this "
            f"process reset_engine_calls={app_session.reset_count()}"
        )
        engine_dbname = None
    else:
        engine_dbname = engine.url.database
        first = (
            f"group-2 app-engine: id={hex(id(engine))} "
            f"url={engine.url.render_as_string(hide_password=True)} "
            f"pool={_one_line(engine.pool.status())} "
            f"engine_url_key_dbname={_one_line(_dbname_of(app_session._engine_url))} "
            f"reset_engine_calls={app_session.reset_count()}"
        )
    if dbapi is None:
        second = "group-2 failing-dbapi-connection: none to compare"
    else:
        failing_dbname = dbapi.get_dsn_parameters().get("dbname")
        matches = "unknown" if engine is None else _yes_no(failing_dbname == engine_dbname)
        second = (
            f"group-2 failing-dbapi-connection: id={hex(id(dbapi))} "
            f"dbname={_one_line(failing_dbname)} "
            f"dbname_matches_app_engine={matches} "
            f"[the exception names no engine; this is a comparison, not a provenance]"
        )
    return [first, second]


def _dbname_of(database_url):
    """Just the database name out of a URL -- never the URL, never a password."""
    if not database_url:
        return None
    from sqlalchemy.engine import make_url

    return make_url(database_url).database


# -- group 3: process and thread -------------------------------------------


def _process_lines(excinfo) -> list[str]:
    """Which process and thread, and the werkzeug question the card asks.

    The thread named is the one **this hook** runs on, which is pytest's own
    and not necessarily the one that raised -- a traceback does not cross
    threads. So the thread question is answered in three parts that are each
    only what they are: the hook's own thread, every thread alive at that
    moment (which is what says whether a server thread existed at all), and
    every traceback frame inside werkzeug, each naming its module -- so
    ``werkzeug/serving.py``, the threaded server, is distinguishable from
    ``werkzeug/test.py``, the in-process client.

    That distinction is the card's "confirm rather than assume", and on the
    five tests this card comes from the assumption does not survive it: a
    provoked instance of exactly those failures reports
    ``werkzeug_frames=['werkzeug/test.py:...']`` with
    ``alive_threads=['MainThread']``. They do not serve HTTP from a thread at
    all; they drive Flask's test client in the main thread. One provoked
    instance is what that rests on.
    """
    current = threading.current_thread()
    frames = _werkzeug_frames(excinfo)
    return [
        (
            f"group-3 process: pid={os.getpid()} "
            f"hook_thread={current.name}/ident={current.ident} "
            f"alive_threads={sorted(thread.name for thread in threading.enumerate())} "
            f"[the thread this hook runs on, not necessarily the one that raised]"
        ),
        (
            f"group-3 traceback: werkzeug_frames={frames} "
            f"frames={_frame_count(excinfo)}"
        ),
    ]


def _traceback_frames(excinfo):
    traceback = getattr(excinfo, "tb", None)
    frames = []
    while traceback is not None and len(frames) < 500:
        frames.append(traceback.tb_frame)
        traceback = traceback.tb_next
    return frames


def _frame_count(excinfo) -> int:
    return len(_traceback_frames(excinfo))


def _werkzeug_frames(excinfo) -> list[str]:
    """``package/module.py:line:function`` for each traceback frame in werkzeug.

    The module name is kept, not just the basename: ``serving.py`` and
    ``test.py`` are the whole point of asking, and a bare ``test.py`` would
    have read as this project's own.
    """
    marker = f"{os.sep}werkzeug{os.sep}"
    found = []
    for frame in _traceback_frames(excinfo):
        filename = frame.f_code.co_filename
        if marker not in filename:
            continue
        inside = filename.split(marker, 1)[1].replace(os.sep, "/")
        found.append(f"werkzeug/{inside}:{frame.f_lineno}:{frame.f_code.co_name}")
    return found


# -- group 4: what the schema holds, through a separate connection ---------


def _capture_lines(dbapi) -> list[str]:
    """The questions that need SQL, asked on a connection opened here.

    Never the failing one: that connection's transaction is aborted and every
    statement on it raises ``InFailedSqlTransaction``, so an implementation
    that reused it would print nothing on exactly the run this exists for.

    The URL is derived the way every other test derives it -- CARD-244's
    :func:`tests.db_name.resolve_test_database_url` -- and the suite's own
    refusal (:func:`tests.conftest._refusal_reason`) is consulted before any
    connection is opened, so a ``TEST_DATABASE_URL`` naming anything but a
    ``*_test`` database is reported and not connected to (G-2).

    **That derivation reads ``TEST_DATABASE_URL`` or the per-worktree name,
    never ``DATABASE_URL``** -- which the app engine *is* built from -- so
    this connection's own database is not evidence about where the failing
    connection was bound. The two are different databases in any run where
    those two variables disagree, a configuration ``scripts/README.md``
    documents and the suite's refusal admits. Hence
    :func:`_capture_answers` prints two separately labelled pairs rather than
    one unlabelled verdict, and the binding one is ``vs-app-engine``.

    **A declared bound, not a closed one.** These imports are lazy, and a lazy
    import can emit a warning -- which pytest would record *outside* the
    section and which would therefore break the two byte comparisons that hold
    this hook's contract. That is deliberately left as it is: such a warning
    *is* the diagnostic changing something besides the section, so a red
    comparison is the right outcome and not a nuisance. Measured today: with
    the imports below, both comparisons are green. Wrapping them in
    ``warnings.catch_warnings()`` was tried and removed -- it deleted with
    zero test failures (a dead mechanism), and all it could ever have done is
    hide the violation those comparisons exist to catch.
    """
    from sqlalchemy import create_engine, text

    from nonogram.db import session as app_session
    from tests import conftest as suite_conftest
    from tests import db_name

    raw = db_name.resolve_test_database_url(os.environ, db_name.REPO_ROOT)
    url = app_session.normalized_url(raw)
    shown = url.render_as_string(hide_password=True)

    refusal = suite_conftest._refusal_reason(raw)
    if refusal is not None:
        return _no_capture(shown, f"NOT OPENED: {_one_line(refusal)}")

    engine = create_engine(url, **app_session._engine_options(raw))
    try:
        with engine.connect() as connection:
            return _capture_answers(connection, text, shown, dbapi)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as failure:  # noqa: BLE001 - named, never swallowed
        return _no_capture(shown, f"FAILED: {_named(failure)}")
    finally:
        engine.dispose()


def _capture_answers(connection, text, shown: str, dbapi) -> list[str]:
    """The four questions, on the fresh connection."""
    here = connection.execute(
        text(
            "SELECT current_database(), current_schema(), "
            "current_setting('search_path'), pg_backend_pid()"
        )
    ).one()
    schema = connection.execute(
        text(
            "SELECT to_regclass('public.puzzles')::text, "
            "to_regclass('puzzles')::text"
        )
    ).one()
    tables = connection.execute(
        text(
            "SELECT schemaname, tablename, tableowner FROM pg_tables "
            "WHERE tablename = 'puzzles' ORDER BY schemaname"
        )
    ).all()

    failing_pid = None
    failing_dbname = None
    if dbapi is not None:
        failing_pid = dbapi.get_backend_pid()
        failing_dbname = dbapi.get_dsn_parameters().get("dbname")
    app_dbname = _app_engine_dbname()

    if failing_pid is None:
        backend = (
            "group-4 failing-backend-from-server: unavailable, no failing "
            "connection to ask about"
        )
    else:
        row = connection.execute(
            text(
                "SELECT datname, usename, state, application_name, query "
                "FROM pg_stat_activity WHERE pid = :pid"
            ),
            {"pid": failing_pid},
        ).first()
        if row is None:
            backend = (
                f"group-4 failing-backend-from-server: pid={failing_pid} "
                f"has no pg_stat_activity row"
            )
        else:
            backend = (
                f"group-4 failing-backend-from-server: pid={failing_pid} "
                f"datname={_one_line(row[0])} usename={_one_line(row[1])} "
                f"state={_one_line(row[2])} application_name={_one_line(row[3])} "
                f"query={_one_line(row[4])} [the server's own view of it]"
            )

    return [
        (
            f"group-4 capture-connection: url={shown} "
            f"current_database={_one_line(here[0])} "
            f"current_schema={_one_line(here[1])} "
            f"search_path={_one_line(here[2])} "
            f"backend_pid={here[3]} [a connection opened here, not the failing one]"
        ),
        (
            f"group-4 schema-now: to_regclass('public.puzzles')={_one_line(schema[0])} "
            f"to_regclass('puzzles')={_one_line(schema[1])} "
            f"pg_tables(puzzles)={[tuple(row) for row in tables]}"
        ),
        backend,
        (
            f"group-4 verdict: failing-dbname={_one_line(failing_dbname)} "
            f"app-engine-dbname={_one_line(app_dbname)} "
            f"capture-dbname={_one_line(here[0])} "
            f"vs-app-engine={_same_database(failing_dbname, app_dbname)} "
            f"vs-capture={_same_database(failing_dbname, here[0])} "
            f"[vs-app-engine is the binding verdict: the app engine is built "
            f"from DATABASE_URL, so this is the pair that says whether the "
            f"failing connection went where it was told. vs-capture only says "
            f"whether schema-now above describes that same database -- the "
            f"capture resolves TEST_DATABASE_URL or the derived name, never "
            f"DATABASE_URL]"
        ),
    ]


def _same_database(left, right) -> str:
    """``MATCH``/``MISMATCH`` for two database names, ``unknown`` if either is absent.

    Deliberately not a verdict about anything by itself: the caller names the
    pair it is comparing, because this card's own review found a single
    unlabelled ``MISMATCH`` being read as "the connection was on the wrong
    database" when what it compared was the *capture's* database against the
    failing one -- two names that are legitimately different whenever
    ``DATABASE_URL`` and ``TEST_DATABASE_URL`` do not agree.
    """
    if left is None or right is None:
        return "unknown"
    return "MATCH" if left == right else "MISMATCH"


def _app_engine_dbname():
    """The database this process's module-global engine is bound to, or ``None``.

    The same reading group 2 takes (``engine.url.database``), and the right
    discriminator for "did the failing connection go where the app was told
    to go": :func:`nonogram.db.session._init_engine` builds that engine from
    ``DATABASE_URL``. The capture's own database is *not* that signal -- it
    comes from :func:`tests.db_name.resolve_test_database_url`, which reads
    ``TEST_DATABASE_URL`` or derives the per-worktree name and never looks at
    ``DATABASE_URL``.
    """
    from nonogram.db import session as app_session

    engine = app_session.engine
    return None if engine is None else engine.url.database


def _no_capture(shown: str, why: str) -> list[str]:
    """Group 4 when there is no capture connection, with the reason in place."""
    return [
        f"group-4 capture-connection: {why} url={shown}",
        "group-4 schema-now: unavailable, no capture connection",
        "group-4 failing-backend-from-server: unavailable, no capture connection",
        "group-4 verdict: unavailable, no capture connection",
    ]


# --------------------------------------------------------------------------
# Plumbing
# --------------------------------------------------------------------------


def _attach(report, body: str) -> None:
    """Put ``body`` under :data:`SECTION_NAME`, leaving the rest of the report alone.

    ``longrepr.addsection`` is preferred because it prints unconditionally;
    ``report.sections`` is the fallback for a report whose ``longrepr`` is a
    bare string, and it is filtered by ``--show-capture``.
    """
    addsection = getattr(getattr(report, "longrepr", None), "addsection", None)
    if callable(addsection):
        addsection(SECTION_NAME, body)
        return
    sections = getattr(report, "sections", None)
    if sections is not None:
        sections.append((SECTION_NAME, body))


def _one_line(value, limit: int = _VALUE_LIMIT) -> str:
    """``value`` as one line, cut to ``limit``.

    Every line of the report is one line: a reader greps it, and
    ``_section_line`` in the tests reads it by its label.
    """
    text = "None" if value is None else str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _named(failure: BaseException) -> str:
    return f"{type(failure).__module__}.{type(failure).__name__}: {_one_line(failure)}"
