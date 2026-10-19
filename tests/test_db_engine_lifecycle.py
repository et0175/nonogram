"""CARD-252 — the session's schema rebuild leaves behind no engine older than the schema.

What this file does and does not demonstrate
--------------------------------------------
Read this before trusting any assertion below, because the whole point of
CARD-252 is a defect that makes evidence unreliable, and a control that cannot
fail inside *that* card would be worse than no control at all.

The defect: ``src/nonogram/db/session.py`` keeps a module-global engine and
rebuilds it only when ``DATABASE_URL`` changes. The test session rebuilds the
``public`` schema under it (``DROP SCHEMA public CASCADE`` → ``CREATE SCHEMA``
→ ``alembic upgrade head``) on its own engine. So a process that had already
built the global engine for that URL kept it, pool and all, and connections
opened before the DROP were handed back out after it. Four consecutive build
gates on this board reported failures that reproduced on no second run,
including ``relation "puzzles" does not exist`` and a ``UUID`` column arriving
as the float ``inf`` so that ``uuid.UUID(hex=inf)`` called ``.replace`` on it.

**AC-3 — a deterministic reproduction of that corruption — is withdrawn.** It
was attempted and could not be forced; the condition it needs is absent from
the driver this project names, and :class:`TestEngineLifecycle_WhyTheHazardCannotBeForced`
below is the measurement that says so, so that the question reopens by going
red if the driver ever changes. What was attempted, and what each attempt did,
is recorded on CARD-252's ``## Worktree notes``.

**So what is pinned here is the hazard's PRECONDITION, not the absence of the
race.** :class:`TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema`
forces an engine to exist, to have queried ``puzzles``, and to hold that
connection in its pool; then it drives the *same* rebuild routine the session
fixture drives; then it asserts that no engine, pool or backend process from
before the rebuild survives it. That is a real, deterministic, failing-first
control over the fix — and it is a statement about what the fixture *leaves
behind*, never a statement that a stale connection would have corrupted a
result had one survived.

**To pin the race itself** one would need a driver or a layer that caches
schema-dependent state per connection and reuses it across a DDL change —
psycopg 3 with ``prepare_threshold`` reached, a server-side cursor held open
across the DROP, or a connection left idle-in-transaction so the DROP takes
the lock-timeout path. None of those exist on this code path today
(psycopg2 2.9, SQLAlchemy 2.0, pool reset on return), and manufacturing one
would be testing the manufactured thing rather than the suite.
"""

from __future__ import annotations

import ast
import os
import time
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from nonogram.db import session as app_session
from tests import db_name
from tests.conftest import (
    _rebuild_public_schema,
    _refusal_reason,
    _unusable_reason,
)

REPO = Path(__file__).resolve().parent.parent
SESSION_SOURCE = REPO / "src" / "nonogram" / "db" / "session.py"
CONFTEST_SOURCE = REPO / "tests" / "conftest.py"

#: How many tests in *this* module need the live test database. Asserted, not
#: read, by :class:`TestEngineLifecycle_TheSkipProfileIsUnchanged` — see AC-4:
#: the one "fix" for this card that must not happen is making DB-mode tests
#: skip, and this board's DB tests skip *green*, so a count that nobody
#: asserts is a count that can quietly go to zero.
EXPECTED_DB_REQUIRED_TESTS = 2

#: How long to wait for PostgreSQL to reap a backend whose client socket was
#: closed by ``dispose()``. Closing is synchronous on this side; the server's
#: own cleanup is not, so the assertion polls instead of racing it. Generous
#: by two orders of magnitude on purpose — this is a deadline for a failure
#: message, not a measurement of anything.
_BACKEND_REAP_DEADLINE_SECONDS = 5.0


def _backend_pid(session) -> int:
    """The PostgreSQL backend process serving ``session``'s current connection."""
    return session.execute(text("SELECT pg_backend_pid()")).scalar()


def _live_backend_pids(engine, pids) -> set:
    """Which of ``pids`` PostgreSQL still shows as live backends.

    Asked through ``engine`` — the fixture's own, never the one under test —
    so the question cannot be answered by the connection it is about.
    """
    if not pids:
        return set()
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT pid FROM pg_stat_activity WHERE pid = ANY(:pids)"),
            {"pids": list(pids)},
        ).scalars().all()
    return set(rows)


def _global_names_assigned_by(function_name: str) -> frozenset:
    """The module-level names ``session.py``'s ``function_name`` declares global and assigns.

    Derived from ``session.py``'s own AST rather than hand-written (ADR-0039/R2):
    the set this guard consults is the set the module actually keeps, so a
    fourth global added to the builder tomorrow is inside the guard's reach on
    the day it is added, not on the day somebody remembers to extend a list.
    """
    tree = ast.parse(SESSION_SOURCE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            declared = {
                name for child in ast.walk(node)
                if isinstance(child, ast.Global) for name in child.names
            }
            assigned = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            assigned.add(target.id)
            return frozenset(declared & assigned)
    raise AssertionError(
        f"session.py has no module-level function {function_name!r}; this guard "
        "reads it from the source and cannot default to a pass (ADR-0039/R2)."
    )


#: Test files allowed to set ``session.py``'s engine globals by hand, with the
#: names each one sets — an equality, not a floor (ADR-0039/R3).
#:
#: These are ``monkeypatch.setattr`` calls, reversible and function-scoped,
#: and they exist to make :func:`nonogram.db.session._init_engine` rebuild so
#: that *its* behaviour can be observed. That is a different question from
#: retiring the engine after a schema rebuild, which is what
#: :func:`nonogram.db.session.reset_engine` is for. A tenth such site, or one
#: in a new file, fails the guard below so that somebody decides rather than
#: inherits.
_EXEMPT_PRIVATE_GLOBAL_SITES = frozenset({
    ("test_db_url_driver.py", "engine"),
    ("test_db_url_driver.py", "_engine_url"),
    ("test_db_url_driver.py", "SessionLocal"),
    ("test_db_connect_timeout.py", "engine"),
    ("test_db_connect_timeout.py", "_engine_url"),
    ("test_db_connect_timeout.py", "SessionLocal"),
})

#: The names a test file may be referring to when it names the session module.
#: Every ``from nonogram.db import session as X`` alias used under ``tests/``.
_SESSION_ALIASES = frozenset({"session", "db_session", "db_session_module", "app_session"})


def _private_global_sites(names) -> set:
    """Every ``(file, name)`` under ``tests/`` that sets one of ``names`` on the session module.

    Covers both spellings: ``monkeypatch.setattr(db_session, "engine", …)`` and
    a plain ``db_session.engine = …``. The module is recognised by alias
    (:data:`_SESSION_ALIASES`), which is why that set is checked for
    completeness against the tree's own imports by
    ``test_the_alias_set_covers_every_way_the_tree_names_the_module``.
    """
    found = set()
    for path in sorted((REPO / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id in _SESSION_ALIASES
                        and target.attr in names
                    ):
                        found.add((path.name, target.attr))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in _SESSION_ALIASES
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in names
            ):
                found.add((path.name, node.args[1].value))
    return found


@pytest.mark.db_required
class TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema:
    """AC-1 and AC-2: the rebuild retires the app's global engine, and removing
    the line that does it turns this red.

    The precondition is *forced*, not hoped for, which is what makes this a
    control rather than a description. At the moment the session fixture runs
    for real, whether the global engine has been built yet is a property of
    test ordering — so an assertion that merely looked at the engine after the
    fixture would pass with the fix removed on most orderings. Here the test
    builds the engine itself, runs a real ``puzzles`` query through it, checks
    that the connection went back into the pool, and only then drives the
    rebuild.

    It drives :func:`tests.conftest._rebuild_public_schema` — the same function
    ``_test_database_tables`` drives, extracted by this card for exactly this
    reason. So the mutant for AC-2 is one line in the code the fixture runs,
    not a line in a copy of it.

    Scope of the claim: this says the fixture leaves no engine, pool or backend
    process predating the schema. It does **not** say that such a survivor
    would have corrupted a query — see this module's docstring, and AC-3's
    withdrawal.
    """

    def test_no_engine_pool_or_backend_predating_the_rebuild_survives_it(
        self, db_session, test_db_url, request
    ) -> None:
        fixture_engine, _tables = request.getfixturevalue("_test_database_tables")

        # --- force the precondition -------------------------------------
        app_session.reset_engine()
        app_session._init_engine()
        before_engine = app_session.engine
        before_pool = before_engine.pool
        probe = app_session.SessionLocal()
        try:
            before_pid = _backend_pid(probe)
            # A real query against the table whose metadata the recorded
            # signatures were about, so the connection is not merely open.
            probe.execute(text("SELECT id FROM puzzles")).all()
        finally:
            probe.close()  # returns the connection to the pool, rolled back

        assert before_pool.checkedin() == 1, (
            "precondition not forced: the engine's pool holds no connection "
            f"from before the rebuild ({before_pool.status()}), so this test "
            "would pass whether or not the rebuild retires it."
        )
        assert _live_backend_pids(fixture_engine, {before_pid}) == {before_pid}, (
            "precondition not forced: the backend this engine's pooled "
            "connection was using is already gone before the rebuild."
        )

        # --- the thing under test ---------------------------------------
        try:
            _rebuild_public_schema(fixture_engine, test_db_url)

            # --- AC-1 ---------------------------------------------------
            assert app_session.engine is not before_engine, (
                "the app's global engine survived the schema rebuild: the next "
                "session request will hand out a connection older than the "
                "schema it queries."
            )
            assert before_pool.checkedin() == 0, (
                "the pre-rebuild pool still holds a connection "
                f"({before_pool.status()}): it was not disposed."
            )

            deadline = time.monotonic() + _BACKEND_REAP_DEADLINE_SECONDS
            still_live = _live_backend_pids(fixture_engine, {before_pid})
            while still_live and time.monotonic() < deadline:
                time.sleep(0.05)
                still_live = _live_backend_pids(fixture_engine, {before_pid})
            assert still_live == set(), (
                f"backend {before_pid}, which queried puzzles before the schema "
                "was rebuilt, is still connected: its connection can still be "
                "handed back out."
            )

            # The next session request builds a new engine against the new
            # schema, and it cannot be the retired backend.
            assert app_session.SessionLocal is None, (
                "the session factory still points at the retired engine"
            )
            fresh = app_session.get_session()
            try:
                assert _backend_pid(fresh) != before_pid
                assert fresh.execute(text("SELECT id FROM puzzles")).all() == []
            finally:
                fresh.close()
        finally:
            app_session.reset_engine()


class TestEngineLifecycle_WhyTheHazardCannotBeForced:
    """AC-3's withdrawal, as a measurement that reopens the question by failing.

    AC-3 asked for the corruption itself — a global engine that has queried
    ``puzzles``, a schema rebuilt underneath it, and then one of the recorded
    signatures out of the same query. It was attempted directly (build the
    engine, insert and read ``puzzles`` twelve times so the pool and
    SQLAlchemy's compiled cache are warm, rebuild the schema, query again
    through the same pooled connection, four query shapes × six attempts) and
    produced **no error at all**.

    The condition that could not be forced: *a cached, schema-dependent
    per-connection statement*. psycopg2 sends every statement for parse on
    every execution and typecasts each result from the OIDs in that result's
    own ``RowDescription``, so a connection that outlives a ``DROP SCHEMA``
    carries nothing about the old tables to be wrong about. Unlike psycopg 3,
    it has no auto-prepare threshold to pass — there is no knob, not merely a
    high one. (Even a hand-written ``PREPARE`` survives: PostgreSQL re-analyses
    the stored parse tree, so the recreated table is found by name.)

    These two tests exist so the withdrawal is not a sentence in a card that
    nobody re-reads. They go red if the project adopts a driver that does cache
    such state, which is the day AC-3 becomes reachable again.
    """

    def test_the_named_driver_has_no_statement_cache_to_go_stale(self) -> None:
        assert app_session.POSTGRES_DRIVER == "psycopg2", (
            "CARD-252 withdrew AC-3 because psycopg2 caches no schema-dependent "
            "per-connection state. The driver has changed, so AC-3's "
            "deterministic reproduction may now be reachable — reopen it."
        )
        assert not hasattr(psycopg2.extensions.connection, "prepare_threshold"), (
            "this psycopg2 exposes an auto-prepare threshold; the condition "
            "CARD-252 could not force may now be forceable."
        )

    @pytest.mark.db_required
    def test_no_server_side_prepared_statement_is_ever_created(self, db_session) -> None:
        """Forty identical executions on one pooled connection prepare nothing.

        The authority is ``pg_prepared_statements``, which the server
        enumerates, rather than a claim about the driver's source.
        """
        session = db_session()
        try:
            for _ in range(40):
                session.execute(
                    text("SELECT id FROM puzzles WHERE width = :w"), {"w": 1}
                ).all()
            prepared = session.execute(
                text("SELECT count(*) FROM pg_prepared_statements")
            ).scalar()
        finally:
            session.close()
        assert prepared == 0, (
            f"{prepared} server-side prepared statement(s) exist; a plan cached "
            "across the schema rebuild is exactly the condition AC-3 needed."
        )


class TestEngineLifecycle_TheSkipProfileIsUnchanged:
    """AC-4: the fix does not buy its green by turning DB tests into skips.

    The hazard only bites ``db_required`` tests, and this board's DB tests skip
    *green* when the database is absent — so narrowing the fixture, or simply
    not setting ``DATABASE_URL``, would remove every red without removing the
    defect and the suite would not complain.

    Two things are asserted, both as counts rather than as readings:

    * this module keeps exactly :data:`EXPECTED_DB_REQUIRED_TESTS` tests that
      need the live database, so the coverage that pins the fix cannot quietly
      drop to zero;
    * given a PostgreSQL that answers, the ``db_required`` gate produces
      exactly **zero** skip reasons for this worktree's own derived test
      database — so those tests run.

    What this cannot assert, and where it is recorded instead: the *suite's*
    skip profile. A test inside the run cannot count the run's own skips
    without depending on collection order, and pytest reports the number only
    after every test has finished. On this machine that number is 1 — the
    platform ``setrlimit`` skip in ``tests/test_book_pdf_memory.py``, which
    macOS refuses at every value — and it is checked at the gate and recorded
    on CARD-252. Treat the sentence above as a pointer, not as coverage.

    The reachability probe here is deliberately a second implementation: a
    bare ``psycopg2.connect`` to the maintenance database rather than
    ``conftest``'s cached SQLAlchemy verdict, so that a bug in the verdict
    cannot make this guard agree with it.
    """

    def test_exactly_the_expected_number_of_tests_here_need_the_database(
        self, request
    ) -> None:
        here = Path(__file__).resolve()
        mine = [
            item for item in request.session.items
            if Path(str(item.fspath)).resolve() == here
        ]
        assert mine, "this module collected no tests, so the count below is vacuous"
        db_required = [
            item for item in mine if item.get_closest_marker("db_required")
        ]
        assert len(db_required) == EXPECTED_DB_REQUIRED_TESTS, (
            f"{len(db_required)} test(s) here carry db_required, expected "
            f"{EXPECTED_DB_REQUIRED_TESTS}: "
            f"{[item.name for item in db_required]}. CARD-252's AC-4 — a fix "
            "that removes the symptom by removing the coverage is not a fix."
        )

    def test_a_reachable_postgres_yields_no_db_mode_skip_reasons(self) -> None:
        resolved = db_name.resolve_test_database_url(os.environ, db_name.REPO_ROOT)
        url = make_url(resolved)
        try:
            probe = psycopg2.connect(
                host=url.host,
                port=url.port,
                user=url.username,
                password=url.password,
                dbname="postgres",
                connect_timeout=5,
            )
        except Exception as error:  # noqa: BLE001 - no server here is a legitimate skip
            pytest.skip(
                "PostgreSQL does not answer on this machine, so a db_required "
                f"skip is legitimate and AC-4 has nothing to guard: {error}"
            )
        probe.close()

        reasons = [
            reason for reason in (
                _refusal_reason(resolved),
                _unusable_reason(resolved),
            ) if reason is not None
        ]
        assert len(reasons) == 0, (
            "PostgreSQL answers, yet the db_required gate would skip this "
            f"worktree's test database for {len(reasons)} reason(s): {reasons}. "
            "That is a green run that tested nothing (AC-4, ADR-0038/R8)."
        )


class TestEngineLifecycle_TheResetIsAPublishedSeam:
    """AC-5: the reset is a named function on ``session.py``, not three
    assignments in a test file.

    The decision (recorded as a ``STRUCTURE:`` note on CARD-252): the fixture
    calls :func:`nonogram.db.session.reset_engine`. The alternative — the card's
    own sketch, ``app_session.engine = None`` and friends inside
    ``conftest.py`` — is the same four lines, but it leaves ``session.py``
    silent about the fact that something retires its engine, and silent is how
    the module got here.

    The guard's set is ``tests/conftest.py``, and the named exemption is the
    nine pre-existing ``monkeypatch.setattr`` sites in
    ``tests/test_db_url_driver.py`` and ``tests/test_db_connect_timeout.py``.
    Those answer a different question — they force ``_init_engine`` to rebuild
    so that *its* behaviour can be observed — and they are held to an equality
    (:data:`_EXEMPT_PRIVATE_GLOBAL_SITES`), not a floor, so a tenth site is a
    decision somebody makes rather than one they inherit (ADR-0039/R3).
    """

    def test_reset_engine_is_public_and_says_who_calls_it(self) -> None:
        reset = getattr(app_session, "reset_engine", None)
        assert callable(reset), "session.py publishes no reset_engine()"
        assert not reset.__name__.startswith("_")
        doc = reset.__doc__ or ""
        assert "conftest" in doc, (
            "reset_engine's docstring does not name its caller; AC-5 asks that "
            "a later reader of session.py can find out who resets it and why."
        )

    def test_conftest_names_the_seam_at_its_call_site(self) -> None:
        source = CONFTEST_SOURCE.read_text(encoding="utf-8")
        assert "reset_engine()" in source, (
            "tests/conftest.py never calls reset_engine(); either the fix is "
            "gone or it is spelled some other way."
        )

    def test_it_resets_exactly_the_globals_the_builder_creates(self) -> None:
        built = _global_names_assigned_by("_init_engine")
        assert built, "no module-level globals found in _init_engine (guard is blind)"
        reset = _global_names_assigned_by("reset_engine")
        assert reset == built, (
            f"reset_engine() resets {sorted(reset)} but _init_engine() builds "
            f"{sorted(built)}. A global the builder sets and the reset leaves "
            "behind is a cache key that outlives the schema."
        )

    def test_the_alias_set_covers_every_way_the_tree_names_the_module(self) -> None:
        """Completeness for :data:`_SESSION_ALIASES`, derived from the tree's imports.

        ADR-0039/R2: the guard below recognises the session module by alias, so
        an alias it does not know is a shape it cannot analyse. That must be a
        failure, not a silent pass.
        """
        aliases = set()
        for path in sorted((REPO / "tests").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "nonogram.db":
                    for alias in node.names:
                        if alias.name == "session":
                            aliases.add(alias.asname or alias.name)
        assert aliases, "no test file imports nonogram.db.session (guard is blind)"
        assert aliases <= _SESSION_ALIASES, (
            f"tests/ names the session module as {sorted(aliases - _SESSION_ALIASES)}, "
            "which the private-globals guard would not see. Add it to "
            "_SESSION_ALIASES."
        )

    def test_no_test_file_outside_the_exemption_sets_those_globals(self) -> None:
        names = _global_names_assigned_by("_init_engine")
        sites = _private_global_sites(names)
        assert sites == set(_EXEMPT_PRIVATE_GLOBAL_SITES), (
            "the set of test files setting session.py's engine globals by hand "
            f"has changed.\n  new: {sorted(sites - set(_EXEMPT_PRIVATE_GLOBAL_SITES))}"
            f"\n  gone: {sorted(set(_EXEMPT_PRIVATE_GLOBAL_SITES) - sites)}\n"
            "conftest.py in particular must go through reset_engine() (AC-5); "
            "any other new site is a decision to record, not to inherit."
        )
