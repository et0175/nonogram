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
from collections import Counter
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
#: read, by :class:`TestEngineLifecycle_TheDbCoverageDoesNotQuietlyVanish` —
#: see AC-4: the one "fix" for this card that must not happen is making
#: DB-mode tests skip, and this board's DB tests skip *green*, so a count that
#: nobody asserts is a count that can quietly go to zero.
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


def _test_functions_in(source: str):
    """``(every test function in source, those carrying db_required)``.

    Read from the module's own AST, not from ``request.session.items``
    (cycle-1 review F-003). The collection answers "how many db_required tests
    did this *run* select", so any legal targeted selection — one node id,
    ``-k``, ``--lf`` — made the count red for a reason that has nothing to do
    with the code: the single-node-id selection reported
    ``0 test(s) here carry db_required, expected 2``. On the card whose whole
    subject is that a red must mean the code, the run is the wrong source.

    Keys are ``Class::test`` (or the bare name for a module-level test), and a
    class-level ``@pytest.mark.db_required`` marks every test it contains, the
    way pytest applies it.
    """
    def marked(node) -> bool:
        return any(
            isinstance(decorator, ast.Attribute) and decorator.attr == "db_required"
            for decorator in node.decorator_list
        )

    def tests_in(body):
        return [
            child for child in body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and child.name.startswith("test")
        ]

    every, db_required = set(), set()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for child in tests_in(node.body):
                name = f"{node.name}::{child.name}"
                every.add(name)
                if marked(node) or marked(child):
                    db_required.add(name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            every.add(node.name)
            if marked(node):
                db_required.add(node.name)
    return every, db_required


def _global_names_assigned_by(function_name: str) -> frozenset:
    """The module-level names ``session.py``'s ``function_name`` declares global and assigns.

    Derived from ``session.py``'s own AST rather than hand-written (ADR-0039/R2):
    the set this guard consults is the set the module actually keeps, so a
    fourth global added to the builder tomorrow is inside the guard's reach on
    the day it is added, not on the day somebody remembers to extend a list.

    That is measured, not hoped for. Cycle-1 review mutant R4 added a fourth
    global (``_engine_dialect``) to :func:`~nonogram.db.session._init_engine`
    and ``test_it_resets_exactly_the_globals_the_builder_creates`` went red
    with exactly the message below. A shape this function cannot analyse
    biases it to red rather than to a pass: a missing function raises, a
    tuple or partial-tuple target is simply not collected into ``assigned``,
    and ``assert built`` in the caller catches a blind read.
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
#: number of times each one sets each name — an equality over **sites**, not a
#: floor and not a set of ``(file, name)`` pairs (ADR-0039/R3).
#:
#: These are ``monkeypatch.setattr`` calls, reversible and function-scoped,
#: and they exist to make :func:`nonogram.db.session._init_engine` rebuild so
#: that *its* behaviour can be observed. That is a different question from
#: retiring the engine after a schema rebuild, which is what
#: :func:`nonogram.db.session.reset_engine` is for.
#:
#: Nine sites, six pairs — which is why the counts are here. Cycle-1 review
#: mutant R1 added a *tenth* site under a pair already listed
#: (``monkeypatch.setattr(db_session, "engine", None)`` in
#: ``test_db_url_driver.py``) and the pair-set equality this replaced did not
#: notice. Now a tenth site, a site under a new name, and a site in a new
#: file each fail the guard below, so that somebody decides rather than
#: inherits. Controls:
#: ``test_a_tenth_site_in_an_already_exempt_pair_is_counted`` (R1) and mutant
#: M3 on CARD-252 (a new file).
_EXEMPT_PRIVATE_GLOBAL_SITES = {
    ("test_db_url_driver.py", "engine"): 1,
    ("test_db_url_driver.py", "_engine_url"): 1,
    ("test_db_url_driver.py", "SessionLocal"): 1,
    ("test_db_connect_timeout.py", "engine"): 2,
    ("test_db_connect_timeout.py", "_engine_url"): 2,
    ("test_db_connect_timeout.py", "SessionLocal"): 2,
}

#: The dotted paths that *are* the session module, whatever a file calls it.
#: ``src.`` because the Alembic subprocess imports the package that way.
_SESSION_MODULE_PATHS = frozenset({"nonogram.db.session", "src.nonogram.db.session"})

#: The packages a ``from … import session`` can name.
_SESSION_PARENT_MODULES = frozenset({"nonogram.db", "src.nonogram.db"})

#: Local names that mean the session module. A **floor**, not the whole
#: authority: :func:`_private_global_sites_in` adds whatever aliases the file
#: it is scanning binds for itself, and
#: ``test_the_alias_set_covers_every_way_the_tree_names_the_module`` holds this
#: literal to the aliases the tree's own imports bind.
_SESSION_ALIASES = frozenset({"session", "db_session", "db_session_module", "app_session"})


def _session_aliases_in(tree) -> set:
    """Every local name the parsed file ``tree`` binds to the session module.

    Both import spellings, because both bind a name the guard has to see
    through: ``from nonogram.db import session as X`` and
    ``import nonogram.db.session as X``. The second was missing until cycle-1
    review mutant R3 walked past both the guard and its completeness test with
    it; ``test_a_plain_import_alias_is_a_site`` is now the control.
    """
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _SESSION_PARENT_MODULES:
            for alias in node.names:
                if alias.name == "session":
                    aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                # ``import nonogram.db.session`` without ``as`` binds only
                # ``nonogram``; the usable spelling is then the full dotted
                # path, which :data:`_SESSION_MODULE_PATHS` already covers.
                if alias.name in _SESSION_MODULE_PATHS and alias.asname:
                    aliases.add(alias.asname)
    return aliases


def _dotted(node) -> str | None:
    """``a.b.c`` for a Name/Attribute chain; ``None`` if it is not one."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _names_the_session_module(dotted, aliases):
    """``True`` / ``False`` / ``None`` — and ``None`` means *cannot tell*.

    ADR-0039/R2: a spelling this cannot classify is a spelling the guard
    cannot see through, so its callers must turn ``None`` into a FAILURE and
    never into a silent pass. Today that is anything whose last component is
    ``session`` without being a path or an alias the tree binds — e.g.
    ``import nonogram.db as pkg`` followed by ``pkg.session.engine = …``, or a
    string target naming some other package's ``session`` module.
    """
    if dotted is None:
        return None
    if dotted in aliases or dotted in _SESSION_MODULE_PATHS:
        return True
    if dotted.rsplit(".", 1)[-1] == "session":
        return None
    return False


def _private_global_sites_in(source: str, filename: str, names):
    """``(Counter of (filename, name) per SITE, unanalysable spellings)``.

    Counts occurrences, not distinct ``(file, name)`` pairs, so that the
    equality in ``test_no_test_file_outside_the_exemption_sets_those_globals``
    is the decision :data:`_EXEMPT_PRIVATE_GLOBAL_SITES` says it is.

    Three spellings are recognised, each with its own control below:

    * ``db_session.engine = …`` — and any dotted chain, so
      ``nonogram.db.session.engine = …`` counts too (mutant M3's shape);
    * ``monkeypatch.setattr(db_session, "engine", …)`` (the nine exempt sites);
    * ``monkeypatch.setattr("nonogram.db.session.engine", …)`` — pytest's
      string-target spelling, which cycle-1 review mutant R2 showed the guard
      could not see at all.

    Everything else that touches one of ``names`` on something this cannot
    resolve to the session module is returned in the second list, which the
    guard fails on.
    """
    tree = ast.parse(source)
    aliases = set(_SESSION_ALIASES) | _session_aliases_in(tree)
    sites = Counter()
    unanalysable = []

    def record(dotted, name, node, spelling) -> None:
        verdict = _names_the_session_module(dotted, aliases)
        if verdict is True:
            sites[(filename, name)] += 1
        elif verdict is None:
            unanalysable.append(f"{filename}:{node.lineno}: {spelling}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr in names:
                    record(
                        _dotted(target.value), target.attr, node,
                        f"<{ast.unparse(target.value)}>.{target.attr} = ...",
                    )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setattr"
            and len(node.args) >= 2
        ):
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                prefix, _, name = first.value.rpartition(".")
                if prefix and name in names:
                    record(prefix, name, node, f'setattr("{first.value}", ...)')
            elif (
                isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
                and node.args[1].value in names
            ):
                record(
                    _dotted(first), node.args[1].value, node,
                    f'setattr({ast.unparse(first)}, "{node.args[1].value}", ...)',
                )
    return sites, unanalysable


def _private_global_sites(names):
    """:func:`_private_global_sites_in`, summed over every file under ``tests/``."""
    sites = Counter()
    unanalysable = []
    for path in sorted((REPO / "tests").rglob("*.py")):
        file_sites, file_unanalysable = _private_global_sites_in(
            path.read_text(encoding="utf-8"), path.name, names
        )
        sites.update(file_sites)
        unanalysable.extend(file_unanalysable)
    return sites, unanalysable


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

    Declared bound on the three survivors the test's name lists (cycle-1
    review F-005): two of them are independently falsifiable, the third is
    not. The engine identity is pinned by mutant M1 (the whole
    ``reset_engine()`` call deleted) and the pool by review mutant R5 (only
    the ``dispose()`` deleted). The **backend** assertion is an implied
    consequence of the pool one, not a third pin: any mutation that leaves a
    pre-rebuild backend alive also leaves its connection in that pool, so the
    pool assertion fires first and the backend poll is reached only when it
    is already going to pass. Measured — ``engine.dispose(close=False)``,
    SQLAlchemy's own way to abandon a pool without closing its sockets and
    the one realistic shape that leaves a backend alive, died on the pool
    assertion instead (review mutant R6). The poll is kept as the
    belt-and-braces reading of "no survivor" and as the thing that makes the
    failure message name a backend; it is not a control that can fail on its
    own.
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
        # This drives a real DROP SCHEMA / CREATE / `alembic upgrade head` at
        # whatever point in the run this test lands — the session fixture
        # drives the same routine before any test body has run. So this one
        # can inherit a transaction an earlier test left open, which the DDL's
        # `SET LOCAL lock_timeout = '10s'` turns into a lock-timeout error
        # *here* rather than in the fixture. If this test ever goes red that
        # way, the holder is an earlier test's leak, not this card (cycle-1
        # review F-006); `pg_stat_activity` names the blocking pid.
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


class TestEngineLifecycle_TheDbCoverageDoesNotQuietlyVanish:
    """AC-4: the fix does not buy its green by turning DB tests into skips.

    Renamed from ``TestEngineLifecycle_TheSkipProfileIsUnchanged`` (cycle-1
    review F-005), which claimed the suite's skip profile — the one thing
    below that is *not* asserted here. Nothing is retired: the same two tests
    carry on under the new name.

    The hazard only bites ``db_required`` tests, and this board's DB tests skip
    *green* when the database is absent — so narrowing the fixture, or simply
    not setting ``DATABASE_URL``, would remove every red without removing the
    defect and the suite would not complain.

    Two things are asserted, both as counts rather than as readings:

    * this module keeps exactly :data:`EXPECTED_DB_REQUIRED_TESTS` tests that
      need the live database, so the coverage that pins the fix cannot quietly
      drop to zero — counted from the module's own AST
      (:func:`_test_functions_in`) rather than from the run's collection, so
      that a targeted selection cannot red it (cycle-1 review F-003);
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
        self,
    ) -> None:
        here = Path(__file__).resolve()
        every, db_required = _test_functions_in(here.read_text(encoding="utf-8"))
        assert every, (
            "no test functions found in this module's own source, so the count "
            "below is vacuous"
        )
        assert len(db_required) == EXPECTED_DB_REQUIRED_TESTS, (
            f"{len(db_required)} test(s) in this module carry db_required, "
            f"expected {EXPECTED_DB_REQUIRED_TESTS}: {sorted(db_required)}. "
            "CARD-252's AC-4 — a fix that removes the symptom by removing the "
            "coverage is not a fix."
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
    nine pre-existing ``monkeypatch.setattr`` **sites** (six ``(file, name)``
    pairs) in ``tests/test_db_url_driver.py`` and
    ``tests/test_db_connect_timeout.py``. Those answer a different question —
    they force ``_init_engine`` to rebuild so that *its* behaviour can be
    observed — and they are held to an equality over sites with their counts
    (:data:`_EXEMPT_PRIVATE_GLOBAL_SITES`), not a floor and not a set of
    pairs, so a tenth site under an existing pair is a decision somebody makes
    rather than one they inherit (ADR-0039/R3).

    What the guard reaches, stated as what has a control (ADR-0039/R1). It
    sees three spellings — a dotted assignment, ``setattr(module, "name", …)``
    and ``setattr("dotted.path.name", …)`` — recognises the module by the
    aliases the scanned file itself binds (both import spellings) on top of
    :data:`_SESSION_ALIASES`, and **fails** rather than passes on a spelling
    it cannot resolve to the session module. Each of those four claims has a
    control in this class, and all four are verbatim mutants from CARD-252's
    cycle-1 review that SURVIVED the first version of the guard (R1, R2, R3,
    plus the deny-on-unanalysable shape R3 exposed).

    The bound that remains: the recognition is syntactic. A test file that
    reached the globals through something no AST walk can follow — a name
    bound by a fixture, ``importlib.import_module`` into a local, a
    ``globals()`` write — is outside the guard, and the failure path above
    only catches the spellings whose last component is still ``session``.
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
        """``conftest.py`` *calls* it — read as a call, not as a substring.

        A text search is the wrong instrument here, and this cycle proved it:
        narrowing ``_rebuild_public_schema``'s docstring for review finding
        F-004 put the literal ``reset_engine()`` into conftest's prose, so a
        substring check would have been satisfied with the call deleted.
        Mutant M1 (the call gone, the prose kept) is the control.

        Stated bound: the call has to be an attribute call on something that
        names the session module (``app_session.reset_engine()``). If conftest
        ever imports the function directly and calls it bare, this test reds
        and has to be widened — deliberately, rather than quietly accepting
        any call to anything of that name.
        """
        tree = ast.parse(CONFTEST_SOURCE.read_text(encoding="utf-8"))
        aliases = set(_SESSION_ALIASES) | _session_aliases_in(tree)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "reset_engine"
            and _names_the_session_module(_dotted(node.func.value), aliases) is True
        ]
        assert calls, (
            "tests/conftest.py never calls session.reset_engine() — a mention "
            "in a docstring is not a call site. Either the fix is gone or it "
            "is spelled some other way (AC-5)."
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

        ADR-0039/R2: the guard recognises the session module by alias, so an
        alias it does not know is a shape it cannot analyse. That must be a
        failure, not a silent pass — and it is twice over now: the scan unions
        the aliases of the file it is reading, and this test holds the literal
        to the whole tree's imports. Both spellings are collected
        (:func:`_session_aliases_in`), because cycle-1 review mutant R3 used
        ``import nonogram.db.session as X`` to slip past both.
        """
        aliases = set()
        for path in sorted((REPO / "tests").rglob("*.py")):
            aliases |= _session_aliases_in(ast.parse(path.read_text(encoding="utf-8")))
        assert aliases, "no test file imports nonogram.db.session (guard is blind)"
        assert aliases <= _SESSION_ALIASES, (
            f"tests/ names the session module as {sorted(aliases - _SESSION_ALIASES)}, "
            "which the private-globals guard's floor would not carry. Add it to "
            "_SESSION_ALIASES."
        )

    def test_no_test_file_outside_the_exemption_sets_those_globals(self) -> None:
        names = _global_names_assigned_by("_init_engine")
        sites, unanalysable = _private_global_sites(names)
        assert not unanalysable, (
            "these test-tree lines set one of session.py's engine globals on "
            "something this guard cannot resolve to the session module, so it "
            "cannot say whether they are exempt. ADR-0039/R2 makes that a "
            f"failure, not a pass:\n  " + "\n  ".join(unanalysable)
        )
        assert dict(sites) == _EXEMPT_PRIVATE_GLOBAL_SITES, (
            "the test-tree sites setting session.py's engine globals by hand "
            "have changed (counts are per site, not per (file, name) pair).\n"
            f"  found:  {sorted(sites.items())}\n"
            f"  expect: {sorted(_EXEMPT_PRIVATE_GLOBAL_SITES.items())}\n"
            "conftest.py in particular must go through reset_engine() (AC-5); "
            "any other new site — including a second one in a file that "
            "already has some — is a decision to record, not to inherit."
        )

    # --- the three shapes this guard was NOT written from ---------------
    # All three survived it in CARD-252's cycle-1 review (R1/R2/R3: 5 passed
    # each). They are controls now, because a claim about what a guard catches
    # needs a control that can fail (ADR-0039/R1). Each feeds source *text* to
    # the scanner rather than editing a real file, so the control is permanent
    # instead of being a mutant somebody has to remember to re-apply.

    def test_a_tenth_site_in_an_already_exempt_pair_is_counted(self) -> None:
        """R1: nine sites are six pairs, and the tenth must not hide in a pair."""
        names = _global_names_assigned_by("_init_engine")
        exempt_file = "test_db_url_driver.py"
        source = (REPO / "tests" / exempt_file).read_text(encoding="utf-8")
        before, _ = _private_global_sites_in(source, exempt_file, names)
        key = (exempt_file, "engine")
        assert before[key] == _EXEMPT_PRIVATE_GLOBAL_SITES[key], (
            "this control is measured against the real exempt file; its site "
            "count there has changed, so fix the exemption first."
        )
        mutated = source + (
            "\n\ndef test_r1_control(monkeypatch):\n"
            '    monkeypatch.setattr(db_session, "engine", None)\n'
        )
        after, unanalysable = _private_global_sites_in(mutated, exempt_file, names)
        assert not unanalysable
        assert after[key] == before[key] + 1, (
            "a tenth hand-set site inside an already-exempt (file, name) pair "
            "was not counted, so the exemption is a set of pairs again and "
            f"the comment on _EXEMPT_PRIVATE_GLOBAL_SITES is false: {after[key]}"
        )
        assert dict(after) != _EXEMPT_PRIVATE_GLOBAL_SITES, (
            "the guard's equality accepts a tenth site in an exempt pair"
        )

    def test_the_string_target_spelling_is_a_site(self) -> None:
        """R2: pytest's own ``setattr("pkg.mod.name", …)`` spelling."""
        names = _global_names_assigned_by("_init_engine")
        sites, unanalysable = _private_global_sites_in(
            "def test_r2_control(monkeypatch):\n"
            '    monkeypatch.setattr("nonogram.db.session.engine", None)\n',
            "test_not_exempt.py",
            names,
        )
        assert not unanalysable
        assert dict(sites) == {("test_not_exempt.py", "engine"): 1}, (
            "the string-target spelling of monkeypatch.setattr is invisible to "
            f"the guard, so AC-5's claim is wider than its reach: {dict(sites)}"
        )

    def test_a_plain_import_alias_is_a_site(self) -> None:
        """R3: ``import nonogram.db.session as X`` then ``X.engine = …``."""
        names = _global_names_assigned_by("_init_engine")
        source = (
            "import nonogram.db.session as probe\n\n"
            "def test_r3_control():\n"
            "    probe.engine = None\n"
        )
        assert _session_aliases_in(ast.parse(source)) == {"probe"}, (
            "the alias-completeness collection does not see the plain-import "
            "spelling, so its own docstring's promise is unmet"
        )
        sites, unanalysable = _private_global_sites_in(source, "test_not_exempt.py", names)
        assert not unanalysable
        assert dict(sites) == {("test_not_exempt.py", "engine"): 1}, (
            "a module aliased by `import nonogram.db.session as X` is invisible "
            f"to the guard: {dict(sites)}"
        )

    def test_a_spelling_the_guard_cannot_resolve_is_a_failure(self) -> None:
        """ADR-0039/R2's default: unanalysable is red, never a silent pass."""
        names = _global_names_assigned_by("_init_engine")
        sites, unanalysable = _private_global_sites_in(
            "import nonogram.db as pkg\n\n"
            "def test_unresolvable(monkeypatch):\n"
            "    pkg.session.engine = None\n"
            '    monkeypatch.setattr("some.other.session.SessionLocal", None)\n',
            "test_not_exempt.py",
            names,
        )
        assert dict(sites) == {}, (
            "neither spelling resolves to the session module, so neither is a "
            f"site: {dict(sites)}"
        )
        assert len(unanalysable) == 2, (
            "a reach the guard cannot classify must come back as a failure, "
            f"not as nothing to see: {unanalysable}"
        )
