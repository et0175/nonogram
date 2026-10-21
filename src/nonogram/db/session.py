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

#: How many times :func:`reset_engine` has run in this process. Read through
#: :func:`reset_count`; see that function for why it exists and who reads it.
#:
#: Incremented with ``+=``, which is an ``ast.AugAssign`` and therefore
#: *outside* the ``ast.Assign`` sweep CARD-252's
#: ``test_it_resets_exactly_the_globals_the_builder_creates`` derives its
#: globals from: that test's agreement between builder and reset is silent
#: about this name rather than covering it (CARD-258 declared bound 9).
_reset_count = 0

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
            exception is deliberately *not* chained: SQLAlchemy has echoed the
            offending string back in that message before, and that string is
            the one place a password lives (EC-1).

            "Cannot parse" is two exception types, not one. ``make_url`` raises
            ``ArgumentError`` for a malformed scheme, and a bare ``ValueError``
            out of ``int(port)`` when the authority's port is not a number —
            identically on SQLAlchemy 2.0.52 and 2.1.0. That second family is
            not exotic: ``postgresql://u:p@2001:db8::1:5432/db``, an IPv6
            address written without its brackets, is the commonest
            ``DATABASE_URL`` typo there is, and ``…@host:/db`` is a truncated
            port. Catching only the first let those spellings escape as
            ``ValueError: invalid literal for int()``, so for them this
            docstring was false and neither the scheme-only message nor the
            ``from None`` shield ran at all.
    """
    # Computed *before* the try, so that the handler's body cannot raise. An
    # exception from inside the handler — from a non-``str`` argument, say —
    # would resurface SQLAlchemy's own error, which echoes the whole URL and
    # its password, as an unsuppressed ``__context__``: the exact traceback
    # ``from None`` exists to block. The handler is therefore kept incapable of
    # raising rather than merely unlikely to, and :func:`_scheme_of` is total
    # for the same reason.
    scheme = _scheme_of(database_url)
    try:
        url = make_url(database_url)
    except (ArgumentError, ValueError):
        # Both are named because ``ArgumentError`` is not a ``ValueError``.
        raise RuntimeError(
            "DATABASE_URL is not a URL SQLAlchemy can parse "
            f"(scheme: {scheme!r}). "
            "Expected something like postgresql://user:password@host:5432/dbname"
        ) from None

    backend, _, driver = url.drivername.partition("+")
    if backend.lower() not in _TIMEOUT_SCHEMES:
        return url
    return url.set(
        drivername=f"{_POSTGRES_BACKEND}+{(driver or POSTGRES_DRIVER).lower()}"
    )


def _scheme_of(database_url: object) -> str:
    """The URL's scheme when it has a real one, otherwise a fixed placeholder.

    The candidate is the text before the first ``://``, cut again at its first
    ``:``, and it is returned only if it matches RFC 3986 scheme grammar,
    ``[A-Za-z][A-Za-z0-9+.-]*`` (which admits ``postgresql+psycopg2``).
    Anything else becomes ``"<malformed scheme>"``; a string with no ``://``
    is ``"<no scheme>"`` and a non-string is ``"<not a string>"``.

    So nothing after ``://`` is ever returned, and of the text before it only
    a leading, scheme-shaped token is: a secret glued on with a ``:``
    (``postgresql:hunter2://…``) is cut off, and one behind an ``@``
    (``hunter2@h://…``) fails the grammar. Two shapes remain beyond any
    check, because they *are* scheme-shaped: a secret that is the leading token
    itself (``hunter2://…``, ``hunter2:x://…``) and one appended to the scheme
    using only scheme characters (``postgresqlhunter2://…``). Those are
    echoed; a username before the first ``:`` (``panel:pw@h://…``) is too.

    Total for *any* input, deliberately: this value goes into the message of an
    error raised while another one is being handled, and a ``TypeError`` from a
    ``bytes`` or ``None`` argument there would pull SQLAlchemy's URL-echoing
    message into the traceback as the context of the new failure. Returning a
    placeholder is worth more than a type error nobody wanted (EC-1).
    """
    if not isinstance(database_url, str):
        return "<not a string>"
    before, separator, _ = database_url.partition("://")
    if not separator:
        return "<no scheme>"
    candidate = before.partition(":")[0]
    ascii_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if (
        candidate
        and candidate[0] in ascii_letters
        and all(c in ascii_letters or c in "0123456789+.-" for c in candidate)
    ):
        return candidate
    return "<malformed scheme>"


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


def reset_engine() -> None:
    """Retire the module-global engine; the next session request builds a new one.

    Disposes the engine's connection pool (if one was ever built) and clears
    the cache key :func:`_init_engine` compares against, so the very next
    :func:`get_session` or :func:`session_scope` constructs a fresh engine
    against whatever ``DATABASE_URL`` then says — pool included.

    Who calls it and why
    --------------------
    CARD-252. The one caller is ``tests/conftest.py``'s
    ``_rebuild_public_schema``, which the session-scoped
    ``_test_database_tables`` fixture drives: it empties ``public`` with
    ``DROP SCHEMA public CASCADE``, rebuilds it with ``alembic upgrade head``,
    and then calls this — last, so that retiring the engine is the final thing
    the rebuild does and nothing can hand out a connection older than the
    schema once the fixture yields.

    That position is deliberate but **not** load-bearing: this function builds
    nothing, so calling it before the migration cannot leave "a fresh engine
    pointed at a half-built schema". Measured, not reasoned — moving the call
    ahead of the Alembic subprocess leaves ``tests/test_db_engine_lifecycle.py``
    fully green (CARD-252 G-3). The half-built-schema hazard belongs to that
    card's original sketch, which rebuilt the engine eagerly, not to this
    implementation.

    What is pinned, and what is not
    -------------------------------
    Pinned: without this call, :func:`_init_engine`'s "rebuild only when the
    URL changed" cache keeps whatever engine the process had already built for
    that URL, pool and all, so a connection opened *before* the
    ``DROP SCHEMA`` is still in the pool *after* it, ready to be handed back
    out. ``tests/test_db_engine_lifecycle.py``'s AC-1 forces exactly that
    connection to exist and goes red when this call — or only its
    ``dispose()`` — is removed.

    **Not** pinned: that such a survivor corrupts anything. Four consecutive
    waves of this board's build gates reported failures that reproduced on no
    second run (``relation "puzzles" does not exist``; a ``UUID`` column
    arriving as a float, so that ``uuid.UUID(hex=inf)`` called ``.replace`` on
    it). Those failures are the **motive** for this function, not a measured
    consequence of its absence. CARD-252 tried to reproduce the corruption
    deterministically and **withdrew** that acceptance criterion (AC-3): 24/24
    queries through a connection that outlived a ``DROP SCHEMA`` returned
    correct values, ``pg_prepared_statements`` held 0 rows after 40
    executions, and ``puzzles.id`` came back as OID 2950 every time — so the
    recorded signature is unreachable on psycopg2, and the gate failures
    remain **unexplained**. Of those three numbers only the
    ``pg_prepared_statements`` zero is a standing assertion
    (``test_no_server_side_prepared_statement_is_ever_created``); the 24/24
    and the OID 2950 are recorded on CARD-252's ``## Worktree notes``, not
    asserted anywhere, so do not go looking for them in the class named
    below. Read
    ``tests/test_db_engine_lifecycle.py``'s module docstring before concluding
    this function fixed them; ``TestEngineLifecycle_WhyTheHazardCannotBeForced``
    there measures why the hazard could not be forced, and goes red the day a
    driver that caches schema-dependent per-connection state arrives — which
    is the day the attribution becomes testable again.

    What the function therefore removes is the hazard's **precondition**. It
    is a published function rather than three assignments in a test file so
    that a later reader of this module can see that something retires the
    engine, and find out who.

    The convention, and what little enforces it
    -------------------------------------------
    CARD-254. **Tests do not hand-set this module's engine globals** --
    ``engine``, ``SessionLocal`` and ``_engine_url``. They call this function.
    ``tests/test_db_url_driver.py`` and ``tests/test_db_connect_timeout.py``
    are the two recorded exceptions: they monkeypatch the globals to force
    :func:`_init_engine` to rebuild so that *its* behaviour can be observed,
    which is a different question from retiring an engine after a schema
    rebuild. A third exception is a card, not a commit.

    **This docstring is the only statement of that convention and of the bound
    below.** ``TestEngineLifecycle_TheResetIsAPublishedSeam`` in
    ``tests/test_db_engine_lifecycle.py`` lists the controls and points here
    for the rest, instead of repeating it in the same words — a doubling that
    was itself a claim, with nothing to red when the two copies drifted.
    ``test_both_convention_texts_agree_on_the_mechanisms_parameters`` is what
    reds now: it holds both texts to the mechanism's own parameters — the
    globals :func:`_init_engine` creates and the two spellings that are
    counted — read from this module's AST and from the scan's own patterns,
    never quoted.

    That is a **convention, enforced at review**. The only mechanism behind it
    is a textual count in ``tests/test_db_engine_lifecycle.py``
    (``test_no_test_file_outside_the_exemption_sets_those_globals``): per file
    under ``tests/``, how many times each of these three names appears beside a
    ``setattr(`` or on the left of an attribute assignment, held to an equality
    against a declared exemption. It therefore reds on a new file, a new name,
    or a tenth site in a file that already has some.

    What that count does **not** enforce:

    * It counts **text**, not reaches. It does not know what object a counted
      line sets, so a ``monkeypatch.setattr`` naming one of these three
      attributes on an unrelated class is counted too, as is an occurrence in a
      docstring, a comment or a string literal. It over-reds; that is the safe
      direction for a backstop, not a guarantee of precision.
    * It is blind to every spelling that does not put one of the three literal
      names beside a ``setattr(`` or a ``.<name> =``. A name computed at
      runtime, a ``globals()`` or ``vars()`` write, ``importlib`` into a local,
      a ``sys.modules`` swap, ``monkeypatch.delattr``, an attribute target
      nested in a list unpacking, every element but the last of a tuple
      unpacking, a target handed over as one whole dotted-path string (the
      quoted literal is then the path, not the bare name), and a ``setattr(``
      whose **receiver argument itself contains parentheses** — ``setattr``
      applied to ``sys.modules.get(…)`` rather than to a plain name — all reach
      or replace these globals without being counted. Nothing here says they
      cannot happen; only that this count will not tell you when they do.
    * Where the name sits in the file is **not** one of those blind cases. The
      scan stops at a parenthesis, never at a newline, so a ``setattr(`` call a
      formatter wrapped across lines is counted exactly as the same call
      written on one line is — that being the spelling a formatter actually
      produces, a backstop blind to it would have no job left. Crossing
      newlines costs over-reads, in the same safe direction and with a price: a
      ``setattr(`` left unclosed in prose, a comment or a string literal
      reaches a quoted global name further down the file, because the scan
      stops only at a parenthesis and prose routinely has none. So prose in
      ``tests/`` that quotes a ``setattr(`` spelling must keep a parenthesis or
      a ``)`` between it and any quoted global name — which is why neither
      spelling example above writes one of the three names out.
    * It is therefore **not** a proof that no test hand-sets these globals, and
      nothing in this project claims it is. An AST deny-default was tried for
      exactly that claim and withdrawn: in a dynamic language a proof claim
      always has one more axis, and that predecessor caught zero real
      violations while its own reach claim kept failing review. A convention
      enforced at review is honest about being a convention; this count makes
      its cheap half mechanical and claims nothing further.

    Not part of any production path. Nothing in ``src/`` calls it, and it
    changes no behaviour for a process that never does — it exists so that the
    test tree does not have to reach into ``engine``, ``SessionLocal`` and
    ``_engine_url`` by hand.
    """
    global engine, SessionLocal, _engine_url, _reset_count
    if engine is not None:
        engine.dispose()
    engine = None
    SessionLocal = None
    _engine_url = None
    _reset_count += 1


def reset_count() -> int:
    """How many times :func:`reset_engine` has run since this process started.

    Read-only and additive (CARD-258 G-1): a process that never calls it
    behaves exactly as it did before this existed.

    What holds "nothing in ``src/`` reaches it", and how far
    ------------------------------------------------------
    ``test_nothing_in_src_calls_the_reset_counter`` parses every file under
    ``src`` and reds on four shapes, each with its own control:

    * a call whose callee it can name -- ``reset_count(...)`` or
      ``<obj>.reset_count(...)``;
    * a bare reference to the name or the attribute, which is the alias
      spelling (``f = session.reset_count`` then ``f()``) and also a
      re-export or a callback hand-off;
    * the string ``"reset_count"``, or any string ending in
      ``.reset_count``, which is the ``getattr`` / ``globals()[...]`` /
      ``vars(...)[...]`` / dotted-path spelling;
    * **and, by deny-default, any call site whose callee it cannot name at
      all** -- that is a failure and not a silent pass (ADR-0039/R2), held to
      an equality over **counted sites** against the three such sites that
      exist today, each a named exemption with its reason and its site count,
      so that a third site under an exempt key reds rather than being
      absorbed (ADR-0039/R3).

    It is still not a proof, and nothing here claims one: a name assembled at
    runtime from pieces (``"reset_" + "count"``), or reached through a
    ``sys.modules`` entry under a computed attribute name, is spelled nowhere
    the parse can see it. The deny-default narrows that to shapes which also
    do not *call* anything the sweep can name -- which is the honest bound,
    not an exhaustive claim. The direct evidence behind G-1 today is
    independent of all of it: every textual occurrence of the name under
    ``src`` is in this module -- the private counter it reads, the ``global``
    statement and the increment in :func:`reset_engine`, this ``def``, and
    this module's own comments and docstrings -- and not one of them is a
    call. (The number of occurrences moves whenever this prose is edited, so
    it is not quoted; what reproduces is that they are all here and none is
    a call.)

    Who reads it, and why. ``tests/helpers/undefined_table_report.py`` is the
    one reader: on a ``relation "puzzles" does not exist`` failure it records
    which engine object the process had, and "has this engine been retired
    since the schema was rebuilt, and how often" is part of that question.
    Four build gates have reported that failure with no data behind it; the
    engine's ``id()`` alone cannot distinguish an engine that is fresh because
    :func:`reset_engine` ran from one that was simply never built, and this
    counter can.

    It counts **calls**, not disposals: :func:`reset_engine` increments
    whether or not there was an engine to dispose of, because "it was called
    and there was nothing to retire" is itself a thing a reader of that report
    needs to be able to see.
    """
    return _reset_count


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
