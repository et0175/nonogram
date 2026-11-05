"""CARD-349 — the armed database exists and is usable before the first test.

What the defect was, measured in this worktree rather than carried
-----------------------------------------------------------------
``tests/conftest.py``'s ``pytest_runtest_setup`` takes the create-if-missing
path only for an item carrying ``db_required``. Conftest is not the only
reader of ``DATABASE_URL``: ``nonogram.admin.app.create_app`` reads it and
connects to whatever it names, and CARD-109's guard deliberately *allows*
that whenever the name reads as a test database. So in a worktree whose
derived database has never existed, an unmarked test that sorts early
connects first.

Reproduced cold, with ``DATABASE_URL`` armed at the derived URL, before the
fix: **5 failed, 9 passed** in
``tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine``,
every failure ``FATAL: database "nonogram_…_test" does not exist``. After the
fix, from the same cold state: **14 passed**. The card's dated reading of that
class, that count and that signature all reproduce.

The refutation this module exists to hold
-----------------------------------------
The card's second remedy — "make the create-if-missing path eager" — was
measured and is a **false fix**. With the database created but no schema in
it, the same five cells red again with ``relation "puzzles" does not exist``:
the stale-schema twin's signature, self-healing in exactly the same way, and
the signature the card's own two-hazard table would have attributed to the
*other* card. So the two hazards are not siblings one marker apart; the second
is the immediate successor of the first under the card's own remedy. The fix
therefore requests the session fixture that *migrates* the database, not a
``CREATE DATABASE``.

Why the fix cannot be keyed on a set of tests
---------------------------------------------
AC-2 asks for the exposed set, derived. Derived, it is not what the card
expected. **No collected test module in this tree reads ``DATABASE_URL`` in
its own code at all** — the only runtime readers under ``tests/`` are the
suite's own infrastructure, ``conftest.py`` and ``database_guard.py``. The
exposure is entirely *indirect*, through production functions that read the
variable themselves, and an indirect set can only ever be over-approximated:
a call graph by name is not a proof of reachability. So the fix is
set-independent by construction — an autouse session fixture that runs
whatever the first item turns out to be — and these tests hold the derivation
rather than a list (ADR-0039/R2).

The two gates stay separately attributable (AC-4): nothing here changes either
``pytest.skip`` in ``pytest_runtest_setup``, and the eager path announces
itself on a third channel with its own prefix.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# One of the two classes review cycle 1's F-001 measured escaping the old
# catch: ``_rebuild_public_schema``'s ``DROP SCHEMA public CASCADE`` under
# another connection's lock raises it. Its sibling is
# ``subprocess.TimeoutExpired``, reached through the already-imported
# ``subprocess``. Imported rather than spelled as a string, so a rename in
# either library breaks this module instead of silently un-parametrising it.
from sqlalchemy.exc import OperationalError

import tests.conftest as suite_conftest
from tests import db_name

#: This worktree's root — the tree the subprocess probes run pytest in, so the
#: lock guard resolves them to this worktree and recognises them as this run's
#: own rather than refusing them.
REPO = Path(__file__).resolve().parent.parent

#: The environment variable the whole card is about.
VAR = "DATABASE_URL"

#: The selection the probes run: the class the cold red was measured in, and
#: the one parametrised test of it that reds. Named rather than discovered,
#: because it is the *evidence*; that it still resolves is held by
#: :func:`test_the_demonstrated_selection_still_resolves`.
EXPOSED_SELECTION = (
    "tests/test_admin_binding.py"
    "::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine"
)

#: How many cells that class holds, measured: 5 reds and 9 passes cold before
#: the fix, 14 passes cold after it.
EXPOSED_CELLS = 14

#: A class in the same module that *does* carry ``db_required``, for the
#: marker API's matched control.
MARKED_SELECTION_MODULE = "tests/test_admin_binding.py"


# --------------------------------------------------------------------------
# The derivation (AC-2). Two authorities, both enumerable by the runtime:
# `ast` for the environment read, pytest's own marker API for the marker.
# --------------------------------------------------------------------------


def _reads_the_variable(node) -> bool:
    """Is ``node`` a runtime *read* of :data:`VAR` from the environment?

    Four spellings, and reads only: ``os.environ["DATABASE_URL"]`` in a load
    context, ``os.environ.get(...)``, ``os.getenv(...)`` and the bare
    ``getenv``/``environ`` forms an ``from os import …`` makes available. A
    *write* — ``monkeypatch.setenv``, ``delenv``, ``os.environ[...] = …`` — is
    not a read, which is the distinction a text search cannot make and is the
    whole reason the grep calibration (79 of 215 ``tests/*.py`` mention the
    name) is not the answer.
    """

    def _is_environ(candidate) -> bool:
        return (
            isinstance(candidate, ast.Attribute) and candidate.attr == "environ"
        ) or (isinstance(candidate, ast.Name) and candidate.id == "environ")

    def _names_it(candidate) -> bool:
        return isinstance(candidate, ast.Constant) and candidate.value == VAR

    if isinstance(node, ast.Subscript):
        return (
            _is_environ(node.value)
            and _names_it(node.slice)
            and isinstance(node.ctx, ast.Load)
        )
    if isinstance(node, ast.Call):
        first = node.args[0] if node.args else None
        if not _names_it(first):
            return False
        func = node.func
        name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else (func.id if isinstance(func, ast.Name) else None)
        )
        if name == "getenv":
            return True
        if name == "get":
            return _is_environ(getattr(func, "value", None))
    return False


def _referenced_names(node) -> set[str]:
    """Every call target and attribute name reachable inside ``node``.

    An over-approximation on purpose: a name is counted whether it is called
    or merely touched, because ``nonogram.db.SessionLocal`` is an *attribute
    access* that runs ``__getattr__`` and reads the variable. Under-counting
    here would be a silent pass.
    """
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def _clears_the_variable(node) -> bool:
    """Does ``node`` take :data:`VAR` out of the environment, or overwrite it?"""
    if not isinstance(node, ast.Call):
        return False
    first = node.args[0] if node.args else None
    if not (isinstance(first, ast.Constant) and first.value == VAR):
        return False
    func = node.func
    name = (
        func.attr
        if isinstance(func, ast.Attribute)
        else (func.id if isinstance(func, ast.Name) else None)
    )
    return name in {"delenv", "pop", "setenv"}


def _scopes_reading_the_variable(path: Path) -> list[tuple[str, ...]]:
    """The enclosing scopes in ``path`` whose own code reads :data:`VAR`.

    A module whose text will not parse yields one sentinel scope rather than
    nothing: a shape this cannot analyse is a refusal, not a silent pass
    (ADR-0039/R2).
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return [("<a module this derivation cannot parse>",)]

    found: list[tuple[str, ...]] = []

    def walk(node, stack: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                walk(child, stack + [child.name])
            else:
                if _reads_the_variable(child):
                    found.append(tuple(stack))
                walk(child, stack)

    walk(tree, [])
    return sorted(set(found))


def _production_readers(src_root: Path) -> set[str]:
    """Every function name under ``src_root`` that can reach a read of :data:`VAR`.

    The direct readers first — a function whose own body reads it — then the
    fixpoint over a name-keyed call graph. Name-keyed, so it over-approximates
    in both directions and is not a proof of reachability; that is exactly why
    the fix below is not allowed to depend on the answer.
    """
    graph: dict[str, set[str]] = {}
    direct: set[str] = set()
    for path in sorted(src_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:  # pragma: no cover - the tree parses
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                graph.setdefault(node.name, set()).update(_referenced_names(node))
                if any(_reads_the_variable(c) for c in ast.walk(node)):
                    direct.add(node.name)

    reaching = set(direct)
    while True:
        grown = {
            name
            for name, calls in graph.items()
            if name not in reaching and calls & reaching
        }
        if not grown:
            return reaching
        reaching |= grown


def _collected_test_modules() -> list[Path]:
    """Every file under ``tests/`` pytest collects tests from.

    ``test_*.py`` is pytest's own default ``python_files`` and this repo
    configures none, so the two agree; the point of deriving it is that
    ``conftest.py`` and ``database_guard.py`` are *not* in it, and that is why
    their reads of the variable are infrastructure rather than exposure.
    """
    return sorted(
        path
        for path in (REPO / "tests").rglob("test_*.py")
        if "__pycache__" not in path.parts
    )


def _indirectly_exposed(readers: set[str]) -> list[tuple[Path, tuple[str, ...]]]:
    """Test scopes that reach a production reader without clearing :data:`VAR`."""
    exposed: list[tuple[Path, tuple[str, ...]]] = []
    for path in _collected_test_modules():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            exposed.append((path, ("<a module this derivation cannot parse>",)))
            continue

        def walk(node, stack: list[str]) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    walk(child, stack + [child.name])
                else:
                    walk(child, stack)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _referenced_names(node) & readers and not any(
                    _clears_the_variable(c) for c in ast.walk(node)
                ):
                    exposed.append((path, tuple(stack)))

        walk(tree, [])
    return exposed


# --------------------------------------------------------------------------
# The subprocess probes (AC-1, AC-3)
# --------------------------------------------------------------------------


def _sentinel_url(tmp_root: Path) -> str:
    """A ``*_test`` URL for a database no worktree owns.

    Derived the way ``conftest.py`` derives the real one, from a throwaway
    root, so it carries the ``_test`` suffix ``_refuse_unless_test_database``
    requires and the ``[a-z0-9_]`` shape ``_ensure_test_database`` will
    create — without being any live worktree's database, and without this
    module ever naming a database it made up.
    """
    return db_name.default_test_database_url(tmp_root)


def _maintenance_engine(database_url: str):
    from nonogram.db import session as db_session

    url = db_session.normalized_url(database_url)
    return create_engine(
        url.set(database=suite_conftest._MAINTENANCE_DATABASE),
        isolation_level="AUTOCOMMIT",
        **db_session._engine_options(database_url),
    )


def _drop_if_present(database_url: str) -> None:
    """Remove the sentinel database, having first proved it is the sentinel.

    Four conditions, all of them checked here and not upstream: the name ends
    in ``_test``, ``conftest._refusal_reason`` allows it, it is not **this**
    worktree's own derived database, and it matches
    ``conftest._CREATABLE_NAME``. G-1 is the reason this reads like paranoia —
    the one operation in this module that destroys anything must not be able
    to destroy anything else.

    What that is and is **not**, stated exactly, because review cycle 1
    flagged the sentence this replaces as an overclaim. These four do *not*
    establish that the name belongs to no *other* live worktree: that would
    need an enumeration of the worktrees on the host, which this module has
    no authority for. What closes the gap instead is provenance — the only
    URL any caller passes is :func:`_sentinel_url` over a ``tmp_path``, a
    directory no worktree is rooted at — and the first two conditions, which
    the live panel's database fails on their own.
    """
    name = make_url(database_url).database or ""
    assert name.endswith("_test"), name
    assert suite_conftest._refusal_reason(database_url) is None, name
    assert name != db_name.derive_test_database_name(REPO), name
    assert suite_conftest._CREATABLE_NAME.match(name), name
    engine = _maintenance_engine(database_url)
    try:
        with engine.connect() as connection:
            quoted = engine.dialect.identifier_preparer.quote(name)
            connection.execute(text(f"DROP DATABASE IF EXISTS {quoted}"))
    finally:
        engine.dispose()


def _run(database_url: str, *, cold: bool) -> tuple[int, str]:
    """One pytest run of the exposed selection, cold or warm.

    *cold* removes the database first; warm leaves whatever the previous run
    left. That pairing is the defect's actual signature and it is **not** the
    one AC-3 describes — see
    :func:`TestColdDatabase_TheSecondRunIsNotTheFirstRunsRescue.test_a_cold_run_and_a_warm_run_agree`.

    Run from :data:`REPO` so the real ``tests/conftest.py`` — the thing under
    test — is loaded, and so the lock guard resolves the probe to this
    worktree and lets it through rather than refusing it as a foreign holder.
    ``TEST_DATABASE_URL`` and ``DATABASE_URL`` are both the sentinel, which is
    what makes the probe's ``DATABASE_URL`` the resolved one and so puts it on
    the branch the fix acts on.
    """
    if cold:
        _drop_if_present(database_url)
    completed = subprocess.run(
        [
            sys.executable, "-m", "pytest", EXPOSED_SELECTION,
            "-p", "no:cacheprovider", "-o", "addopts=",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=600,
        env={
            **os.environ,
            "DATABASE_URL": database_url,
            "TEST_DATABASE_URL": database_url,
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    return completed.returncode, completed.stdout + completed.stderr


# --------------------------------------------------------------------------
# The re-raise control (G-2). The catch is only safe because pytest caches a
# session fixture's outcome and re-raises it to every later requester; this is
# the apparatus that measures that against the real suite rather than against
# a synthetic project.
# --------------------------------------------------------------------------

#: Two **collected** node ids, resolved by ``--collect-only`` rather than by
#: reading the files: one test that requests ``db_session`` and one that
#: touches no database at all. A text search is how this pair was first got
#: wrong — ``grep`` for a ``db_session`` parameter matched
#: ``test_db_isolation.py``'s ``_PROBE``, a **string literal** holding a
#: generated file that is deliberately not part of the suite, and pytest
#: refused the node id with "not found". Both of these collect.
_ASKS_FOR_THE_DATABASE = "tests/test_db_e2e_smoke.py::test_db_session_fixture_works"
_NEVER_ASKS = (
    "tests/test_db_isolation.py"
    "::TestTestDbUrl_NameIsDerivedPerWorktree"
    "::test_the_same_root_always_derives_the_same_name"
)

#: Text the injected stop carries, asserted present in the run's output: it
#: is how "the reason survived the swallow" is distinguished from "something
#: else went wrong".
_STOP_MARKER = "STOP-INJECTED-BY-THE-F001-RE-RAISE-CONTROL"

#: pytest's own words for an error raised while a fixture was being set up,
#: as opposed to inside the test. This is the evidence that the asking test's
#: **body never ran** — and it is asserted rather than a marker the body
#: would print, because the body is an existing test this module does not
#: edit, so a "marker absent" assertion over it could never have failed.
_AT_SETUP = "ERROR at setup of "

#: A ``-p`` plugin that makes ``_rebuild_public_schema`` raise the class
#: F-001 measured escaping the old clause. Injected at the
#: ``_rebuild_public_schema`` seam rather than by holding a real lock, so the
#: control needs no second connection and no timing: the point under test is
#: what the *fixture machinery* does with a non-outcome exception, not that
#: Postgres can produce one. That it can is the measured type fact recorded
#: in ``_armed_database_is_ready``'s docstring.
_STOP_INJECTOR = f'''\
"""Generated by tests/test_card_349_cold_database.py. Not part of the suite."""

from sqlalchemy.exc import OperationalError

MARKER = {_STOP_MARKER!r}


def pytest_configure(config):
    import tests.conftest as suite_conftest

    def _stop(engine, database_url):
        raise OperationalError("DROP SCHEMA public CASCADE", {{}}, Exception(MARKER))

    suite_conftest._rebuild_public_schema = _stop
'''


def _run_the_pair(tmp_path: Path, *, inject: bool) -> tuple[int, str]:
    """Run the two node ids in the real tree, with or without the stop.

    ``-rEfs`` because the verdict is read off the short summary: ``-rfs``
    omits ERRORs, which is the whole signal here. ``DATABASE_URL`` is left as
    the ambient armed value rather than redirected at a sentinel — this
    control is about the fixture machinery, not about which database is named,
    and the ``db_required`` marker skips it when nothing is armed.
    """
    selection = [_ASKS_FOR_THE_DATABASE, _NEVER_ASKS]
    plugin = ["-p", "card349_stop_injector"] if inject else []
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *selection, *plugin,
         "-p", "no:cacheprovider", "-o", "addopts=", "-rEfs"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=600,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join(
                [str(tmp_path), os.environ.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep),
        },
    )
    return completed.returncode, completed.stdout + completed.stderr


@pytest.fixture(scope="module")
def a_cold_run_then_a_warm_one(tmp_path_factory):
    """One run from cold, then the same run again on what it left behind.

    Module-scoped so the pair costs two subprocess runs rather than four, and
    so AC-1 and AC-3 look at the same evidence: AC-1 asks what the *first* run
    did, AC-3 asks whether the second differed from it.
    """
    url = _sentinel_url(tmp_path_factory.mktemp("card349"))
    try:
        yield [_run(url, cold=True), _run(url, cold=False)]
    finally:
        _drop_if_present(url)


def _fixture_body(fixture):
    """The plain function a ``@pytest.fixture`` decorator wrapped.

    Needed because the only thing that writes ``conftest._ARMED_SETUP`` in a
    real run is ``_armed_database_is_ready``, and a fixture object cannot be
    called: pytest rejects that at runtime on purpose. Review cycle 1's F-001
    was exactly this seam — every note test drove the pure planner and the
    pure formatter and hand-injected the dict between them, so the recording
    in the middle was covered by nothing and swallowing it entirely went
    unnoticed.

    pytest has spelled the unwrapping differently across versions, so three
    are tried in the order they were introduced, newest first. A pytest that
    spells it a fourth way is a **refusal** naming its own version
    (ADR-0039/R2): falling back to calling the fixture object would raise a
    pytest error that reads like a bug in this test rather than like a shape
    it could not analyse.
    """
    getter = getattr(fixture, "_get_wrapped_function", None)
    if callable(getter):
        return getter()
    wrapped = getattr(fixture, "__pytest_wrapped__", None)
    if wrapped is not None and hasattr(wrapped, "obj"):
        return wrapped.obj
    if getattr(fixture, "_pytestfixturefunction", None) is not None:
        return fixture
    raise AssertionError(
        f"cannot resolve the function behind a pytest fixture on pytest "
        f"{pytest.__version__}; this test drives the fixture body directly "
        f"and will not guess: {sorted(a for a in dir(fixture) if a[0] != '_')}"
    )


class _StubRequest:
    """Just enough ``request`` for ``_armed_database_is_ready``'s one call.

    It records what was asked for, so the branches that must *not* reach for
    the schema can be shown not to have.
    """

    def __init__(self, raises=None):
        self.asked: list[str] = []
        self._raises = raises

    def getfixturevalue(self, name: str):
        self.asked.append(name)
        if self._raises is not None:
            raise self._raises
        return object()


def _outcome(output: str) -> str:
    """The run's own summary line, which is its result in one string."""
    lines = [
        line.strip()
        for line in output.splitlines()
        if " passed" in line or " failed" in line or " error" in line
    ]
    return lines[-1].split(" in ")[0] if lines else "<no summary line>"


# --------------------------------------------------------------------------


class TestColdDatabase_ThePreparationHappensBeforeTheFirstTest:
    """AC-1 — a cold armed run is green, and never meets a bare driver error."""

    @pytest.mark.db_required
    def test_a_cold_armed_run_is_green_and_shows_no_bare_driver_error(
        self, a_cold_run_then_a_warm_one
    ) -> None:
        """The first run from cold, not the second.

        Both halves are asserted because a fix can pass either alone: a run
        that is green proves nothing if the database was already there, and a
        run with no ``FATAL`` in it proves nothing if it failed some other
        way. The two signatures named are the two self-healing reds — the
        missing **database** (this card) and the missing **table** that
        creating the database without migrating it produces (the twin). A fix
        that only created the database passes the ``FATAL`` check and fails
        the return code, which is how this test tells the false fix from the
        real one.
        """
        returncode, output = a_cold_run_then_a_warm_one[0]
        assert "does not exist" not in output, output[-4000:]
        assert returncode == 0, output[-4000:]
        assert f"{EXPOSED_CELLS} passed" in output, _outcome(output)

    def test_the_demonstrated_selection_still_resolves(self) -> None:
        """The evidence is a node id, so it has to still be one.

        A rename in ``test_admin_binding.py`` would otherwise leave the probes
        above collecting nothing and passing on an empty selection.
        """
        completed = subprocess.run(
            [
                sys.executable, "-m", "pytest", EXPOSED_SELECTION,
                "--collect-only", "-o", "addopts=", "-q",
                "-p", "no:cacheprovider",
            ],
            cwd=str(REPO), capture_output=True, text=True, timeout=300,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        collected = [
            line for line in completed.stdout.splitlines()
            if "::" in line and line.startswith("tests/")
        ]
        assert len(collected) == EXPOSED_CELLS, completed.stdout

    def test_a_database_url_pointed_elsewhere_is_named_and_not_prepared(
        self, monkeypatch
    ) -> None:
        """AC-1's other half, for the case the fix must *not* act on.

        When ``DATABASE_URL`` names something other than the database this
        worktree resolved, nothing may be created — it could be the live
        panel's, reached under CARD-109's opt-out. What the run gets instead is
        a line that names the database and says what to do, which is the thing
        a bare ``psycopg2`` ``FATAL`` several screens into a traceback is not.
        """
        monkeypatch.setattr(
            suite_conftest, "_ensure_test_database",
            lambda url: pytest.fail(f"prepared {url!r}", pytrace=False),
        )
        elsewhere = "postgresql://u:p@192.0.2.1:5432/somebody_elses_test"
        environ = {"DATABASE_URL": elsewhere, "TEST_DATABASE_URL": _sentinel_url(REPO)}
        _url, _resolved, action = suite_conftest._armed_database_plan(environ)
        assert action == suite_conftest._ARM_ELSEWHERE

        monkeypatch.setitem(suite_conftest._ARMED_SETUP, "action", action)
        monkeypatch.setitem(suite_conftest._ARMED_SETUP, "database", "somebody_elses_test")
        monkeypatch.setitem(suite_conftest._ARMED_SETUP, "resolved", "ours_test")
        note = suite_conftest.armed_database_note()
        assert note is not None
        assert "somebody_elses_test" in note
        assert "unset DATABASE_URL" in note
        assert "p@192.0.2.1" not in note

    def test_the_note_is_silent_when_nothing_is_armed(self, monkeypatch) -> None:
        """The control for the one above, and for the edge mutant.

        A check that "passes when ``DATABASE_URL`` is unset for an unrelated
        reason" is the mutant this closes: the note must be ``None`` because
        the plan said *not armed*, and it must still be ``None`` on the happy
        armed path, where there is nothing to say. Two different silences, both
        required, so a note that fired on every run could not pass here either.
        """
        _url, _resolved, action = suite_conftest._armed_database_plan({})
        assert action == suite_conftest._ARM_NOT_SET
        monkeypatch.setattr(suite_conftest, "_ARMED_SETUP", {"action": action})
        assert suite_conftest.armed_database_note() is None
        monkeypatch.setattr(
            suite_conftest, "_ARMED_SETUP",
            {"action": suite_conftest._ARM_PREPARE, "database": "x_test", "reason": None},
        )
        assert suite_conftest.armed_database_note() is None

    def test_a_preparation_that_failed_names_the_database_and_what_to_do(
        self, monkeypatch
    ) -> None:
        """The edge mutant: a refusal whose message omits the database name.

        ``_test_database_tables`` can stop for reasons this card does not fix
        — Postgres not running, a migration that will not apply. The run then
        proceeds, because that must stay a skip rather than become a failure
        (G-2), and the note is the only thing that says why. A note that
        dropped the name would leave the reader with the reason and no
        database, which on a host holding sixty-six ``*_test`` databases is
        not an instruction either.
        """
        monkeypatch.setattr(
            suite_conftest, "_ARMED_SETUP",
            {
                "action": suite_conftest._ARM_PREPARE,
                "database": "nonogram_whatever_test",
                "reason": "Postgres is not running",
            },
        )
        note = suite_conftest.armed_database_note()
        assert "nonogram_whatever_test" in note
        assert "Postgres is not running" in note
        assert "unset DATABASE_URL" in note


class TestColdDatabase_ThePreparationRecordsAndAnnouncesWhatStoppedIt:
    """G-2 / ADR-0038/R8 — the catch is only allowed because the reason survives it.

    Review cycle 1, F-001. ``_armed_database_is_ready`` catches a stop from
    ``_test_database_tables``, because letting one out of a session-autouse
    fixture would skip or error the *whole suite* — the permanent false green
    this card exists to avoid. What the catch **rests on** is that the reason
    is recorded and announced instead, and that claim had no control:
    replacing ``_ARMED_SETUP["reason"] = str(stopped)`` with ``pass`` —
    a preparation failure swallowed in total silence — left this module and
    ``tests/test_full_suite_lock.py`` entirely green. Measured, before and
    after; the mutant now dies here.

    **Review cycle 1 second reading, F-001.** The catch was *also* too narrow,
    and this class's own parametrisation is where that was invisible: it named
    ``pytest.skip`` and ``pytest.fail`` only, matching a docstring that
    claimed those were "both ways" the preparation can stop. They are not.
    ``_rebuild_public_schema``'s ``DROP SCHEMA public CASCADE`` under a lock
    raises ``sqlalchemy.exc.OperationalError``, its Alembic subprocess raises
    ``subprocess.TimeoutExpired``, and neither is an ``OutcomeException``
    subclass — so each escaped a session-autouse fixture and errored every
    item in the suite under *this card's* fixture name. The parametrisation
    below now spans both kinds, and the recorded form is asserted per kind,
    because the two are recorded differently on purpose.

    Every test in this class drives the **real fixture body** rather than the
    pure planner and the pure formatter either side of it. That seam is what
    F-001 found, so closing it means crossing it.
    """

    @staticmethod
    def _drive(monkeypatch, environ_url, *, request, test_database_url=None):
        """Run ``_armed_database_is_ready``'s body against a fresh recording.

        ``TEST_DATABASE_URL`` is set or removed explicitly rather than
        inherited, because ``resolve_test_database_url`` returns it verbatim:
        a value in the ambient shell would otherwise decide which branch the
        plan takes and these tests would pass or fail on the environment the
        suite happened to be started in. That is the defect one layer up —
        a verdict that is a property of the shell rather than of the code
        (``tests/database_guard.py``'s own opening).

        **A stop that escapes the body is converted to an assertion failure
        here, and that is load-bearing.** Without it this helper cannot kill
        the mutant that matters most: narrow the fixture's clause to a bare
        ``except Exception`` — the broadening phrased as a *replacement* of
        the two outcome classes rather than an addition to them — and
        ``pytest.skip.Exception`` escapes the body, propagates out of the test
        function, and the cell is reported **SKIPPED**. Measured: that mutant
        left the skip cell green-by-silence while only the failure cell died.
        A skip is not a kill (G-2), and the escaping-skip direction is the one
        that takes the whole suite with it out of a session-autouse fixture.
        The bound caught here is deliberately the same one the fixture claims,
        so a ``BaseException`` that is not an ``OutcomeException`` still
        escapes both — the fixture does not catch those on purpose.
        """
        recorded: dict = {}
        monkeypatch.setattr(suite_conftest, "_ARMED_SETUP", recorded)
        if test_database_url is None:
            monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("TEST_DATABASE_URL", test_database_url)
        if environ_url is None:
            monkeypatch.delenv(VAR, raising=False)
        else:
            monkeypatch.setenv(VAR, environ_url)
        try:
            _fixture_body(suite_conftest._armed_database_is_ready)(request)
        except (pytest.skip.Exception, pytest.fail.Exception, Exception) as escaped:
            raise AssertionError(
                f"_armed_database_is_ready let {type(escaped).__name__} escape "
                f"instead of recording it. Out of a session-scoped autouse "
                f"fixture that skips or errors every item in the suite, each "
                f"naming this fixture: {escaped}"
            ) from escaped
        return recorded

    @pytest.mark.parametrize(
        ("stop", "announces_its_class"),
        [
            # The two stops ``_test_database_tables`` authors itself. Their
            # message is already a sentence, so it is recorded verbatim.
            pytest.param(pytest.skip.Exception, False, id="a-skip"),
            pytest.param(pytest.fail.Exception, False, id="a-failure"),
            # The stops it does not author, and which the pre-F-001 clause
            # let escape into every item in the suite. Real paths, named: the
            # DROP under a lock, the Alembic subprocess at its timeout.
            pytest.param(OperationalError, True, id="a-lock-on-the-drop"),
            pytest.param(subprocess.TimeoutExpired, True, id="the-alembic-timeout"),
            # Edge: a class whose ``str`` is NOT a legible sentence. Without
            # the class-name prefix the note would read "— 'Postgres is not
            # running'" with nothing saying what went wrong.
            pytest.param(KeyError, True, id="an-illegible-str"),
            # Edge: the ``pg_tables`` projection's third class, and the
            # generic case that proves the clause is not a list of two more.
            pytest.param(RuntimeError, True, id="an-unanticipated-class"),
        ],
    )
    def test_a_stop_is_recorded_by_the_fixture_and_reaches_the_note(
        self, monkeypatch, stop, announces_its_class
    ) -> None:
        """A stop of either kind, through the real recording.

        Parametrised across the ``except`` clause's **bound** rather than a
        list of the classes it names, because a counted claim about this set
        is exactly what F-001 refuted. ``OperationalError`` and
        ``TimeoutExpired`` are included as the measured real paths; ``KeyError``
        and ``RuntimeError`` as edges — the first because its ``str`` carries
        no clue to its identity, the second because it is anticipated nowhere
        in ``_rebuild_public_schema`` and must still be caught.

        The two kinds assert **different recorded forms**, which is the
        discriminator: an authored skip or failure is recorded verbatim, an
        undesigned escape as ``"{class name}: {message}"``. Asserting the
        class name is *absent* for the authored kinds is what stops a tidy-up
        from collapsing the two clauses into one and padding every skip.

        The database name is asserted to be the derived one rather than any
        string, which is what makes ``_database_name_of``'s use *inside* the
        fixture covered too — the second symptom F-001 named.
        """
        ours = db_name.default_test_database_url(REPO)
        if stop is OperationalError:
            raised = stop("DROP SCHEMA public CASCADE", {},
                          Exception("Postgres is not running"))
        elif stop is subprocess.TimeoutExpired:
            raised = stop(["alembic", "upgrade", "head"], 120)
        else:
            raised = stop("Postgres is not running")
        request = _StubRequest(raises=raised)
        recorded = self._drive(monkeypatch, ours, request=request)

        assert request.asked == ["_test_database_tables"]
        assert recorded["action"] == suite_conftest._ARM_PREPARE
        assert recorded["database"] == db_name.derive_test_database_name(REPO)
        # Caught at all — the pre-fix clause let the lower four out of the
        # fixture entirely, so this line is the one that reds without the fix.
        assert "reason" in recorded, (
            f"{stop.__name__} escaped the fixture instead of being recorded"
        )

        note = suite_conftest.armed_database_note()
        assert db_name.derive_test_database_name(REPO) in note
        assert "unset DATABASE_URL" in note
        # Announced, not merely swallowed: the stop's own words reach the note.
        if stop is subprocess.TimeoutExpired:
            assert "timed out after 120 seconds" in note
        else:
            assert "Postgres is not running" in note
        # And announced *as what it was*, for the kinds whose str is not
        # self-describing — the half that distinguishes "the database is
        # unavailable" from "something is badly wrong".
        assert (stop.__name__ in recorded["reason"]) is announces_its_class, (
            stop.__name__, recorded["reason"],
        )
        assert (stop.__name__ in note) is announces_its_class

    def test_a_preparation_that_succeeded_records_no_reason_and_says_nothing(
        self, monkeypatch
    ) -> None:
        """The matched control, on the same path.

        Without it, a fixture that recorded a reason unconditionally would
        satisfy the test above. The happy armed path must record the action
        and the names and **no** reason, and the note must then be silent —
        a line on every run is a line nobody reads by the third one.
        """
        ours = db_name.default_test_database_url(REPO)
        request = _StubRequest()
        recorded = self._drive(monkeypatch, ours, request=request)

        assert request.asked == ["_test_database_tables"]
        assert recorded["action"] == suite_conftest._ARM_PREPARE
        assert recorded["database"] == db_name.derive_test_database_name(REPO)
        assert "reason" not in recorded
        assert suite_conftest.armed_database_note() is None

    def test_the_elsewhere_case_is_recorded_without_asking_for_the_schema(
        self, monkeypatch
    ) -> None:
        """The third symptom F-001 named, on the same seam.

        ``_ARM_ELSEWHERE`` is the G-1 branch: ``DATABASE_URL`` names something
        other than the database this worktree resolved, so nothing may be
        created or migrated. Two things have to hold and both are asserted
        from the real fixture rather than from injected strings — the schema
        fixture is never requested at all, and both database *names* are
        recorded so the note can tell the reader which is which.
        """
        elsewhere = "postgresql://u:p@192.0.2.1:5432/somebody_elses_test"
        request = _StubRequest(raises=AssertionError("asked for the schema"))
        recorded = self._drive(
            monkeypatch, elsewhere, request=request,
            test_database_url=db_name.default_test_database_url(REPO),
        )

        assert request.asked == []
        assert recorded["action"] == suite_conftest._ARM_ELSEWHERE
        assert recorded["database"] == "somebody_elses_test"
        assert recorded["resolved"] == db_name.derive_test_database_name(REPO)

        note = suite_conftest.armed_database_note()
        assert "somebody_elses_test" in note
        assert db_name.derive_test_database_name(REPO) in note
        assert "p@192.0.2.1" not in note

    def test_an_unarmed_run_records_only_that_and_asks_for_nothing(
        self, monkeypatch
    ) -> None:
        """The other control: the fixture is free when ``DATABASE_URL`` is unset.

        This is the branch every ordinary run takes, so it is also the branch
        a cost regression would hide in. Asserting ``asked == []`` is what
        makes "free" a claim that can fail rather than a sentence in a
        docstring.
        """
        request = _StubRequest(raises=AssertionError("asked for the schema"))
        recorded = self._drive(monkeypatch, None, request=request)

        assert request.asked == []
        assert recorded == {"action": suite_conftest._ARM_NOT_SET}
        assert suite_conftest.armed_database_note() is None


class TestColdDatabase_TheSecondRunIsNotTheFirstRunsRescue:
    """AC-3 — the self-healing signature is the defect, so its absence is the fix."""

    @pytest.mark.db_required
    def test_a_cold_run_and_a_warm_run_agree(
        self, a_cold_run_then_a_warm_one
    ) -> None:
        """AC-3's claim, measured on the pair that actually carries it.

        **AC-3 as written does not hold the defect, and this is a finding.**
        It asks that "running twice from the same cold state gives the same
        result both times" — and the defect satisfies that: drop the database
        before each of two runs and both red identically, ``5 failed, 9
        passed`` twice. Measured, not reasoned: planted as mutant M1 (the
        eager preparation removed), the cold/cold equality assertion
        **passed** and only the return code caught it.

        The self-healing signature is cold-red then *warm*-green, so the pair
        that carries the acceptance is a cold run and the run after it. Before
        the fix those two differed — ``5 failed, 9 passed`` then ``14
        passed``; after it they agree. That difference is the whole defect,
        because it trains a re-run instead of a look.
        """
        cold, warm = a_cold_run_then_a_warm_one
        assert _outcome(cold[1]) == _outcome(warm[1]), (
            _outcome(cold[1]), _outcome(warm[1])
        )
        assert cold[0] == warm[0] == 0


class TestColdDatabase_TheExposedSetIsDerived:
    """AC-2 — derived from the environment read and the marker, never listed."""

    def test_no_collected_test_module_reads_the_variable_in_its_own_code(self) -> None:
        """Derived, and the answer is zero — which refutes the card's premise.

        The card expected "a large set of test modules referencing
        ``DATABASE_URL`` and carrying no marker". A text search agrees with it:
        79 of 215 ``tests/*.py`` mention the name. Resolved by ``ast`` to
        *runtime reads*, the count over every collected test module is **0**;
        the only readers under ``tests/`` are ``conftest.py`` and
        ``database_guard.py``, which pytest collects no tests from. Nearly
        every one of those 79 mentions is a ``monkeypatch.delenv`` — a test
        taking the variable *away*.

        One-sided on purpose, and it can fail: a test module that starts
        reading the variable itself is a new shape of exposure, and the board
        should re-read this card's reasoning on the commit that introduces it
        rather than two waves later at a gate.
        """
        readers = {
            path: scopes
            for path in _collected_test_modules()
            if (scopes := _scopes_reading_the_variable(path))
        }
        assert readers == {}, {
            str(p.relative_to(REPO)): ["::".join(s) for s in v]
            for p, v in readers.items()
        }

    def test_the_suites_own_infrastructure_is_where_the_reads_live(self) -> None:
        """The matched control for the test above: the derivation is not vacuous.

        If ``_reads_the_variable`` matched nothing at all, the emptiness above
        would mean nothing. It finds the reads that are really there, in the
        two files pytest collects no tests from.
        """
        found = {
            path.name
            for path in sorted((REPO / "tests").glob("*.py"))
            if _scopes_reading_the_variable(path)
        }
        assert "conftest.py" in found
        assert "database_guard.py" in found

    def test_the_indirectly_exposed_set_spans_more_than_one_module(self) -> None:
        """The population the fix had to speak about, and why it is not a list.

        Measured on 2026-11-04: **4** direct production readers
        (``create_app``, ``_init_engine``, ``_services``, ``nonogram.db``'s
        ``__getattr__``), **10** names transitively reaching them, and **78**
        unguarded test scopes across **19** collected modules. The card said
        the fix's shape changes between "one class" and "twenty"; it is
        nineteen modules, and the derivation that produced that number is a
        name-keyed over-approximation rather than a proof, so the honest
        conclusion is that the set cannot be the fix's input at all.

        A floor rather than the figure, because deleting a test is a correct
        board operation and would move it down. Two modules is the claim that
        matters — more than one, therefore not "one class" — and it sits far
        below the nineteen measured.
        """
        readers = _production_readers(REPO / "src")
        assert {"create_app", "_init_engine"} <= readers, sorted(readers)
        exposed = _indirectly_exposed(readers)
        modules = {path for path, _scope in exposed}
        assert len(modules) >= 2, sorted(str(m.name) for m in modules)
        assert (REPO / "tests" / "test_admin_binding.py") in modules

    def test_a_module_the_derivation_cannot_parse_is_counted_not_skipped(
        self, tmp_path
    ) -> None:
        """ADR-0039/R2 — a shape the guard cannot analyse is a refusal.

        The silent-pass version of this derivation swallows the
        ``SyntaxError`` and reports a module with no reads, which is
        indistinguishable from a clean one.
        """
        broken = tmp_path / "test_unparseable.py"
        broken.write_text("def test_x(:\n", encoding="utf-8")
        assert _scopes_reading_the_variable(broken) == [
            ("<a module this derivation cannot parse>",)
        ]

    def test_the_marker_authority_is_pytests_own_and_the_exposed_class_is_unmarked(
        self,
    ) -> None:
        """The marker half of AC-2, asked of pytest rather than of the text.

        ``test_admin_binding.py`` *mentions* ``db_required`` nine times, which
        is why a module-level text census is the wrong unit: those nine
        marked tests sit eight hundred lines below the exposed class and run
        after it. pytest's own ``-m`` resolution is asked instead, once of the
        exposed class — which must collect nothing — and once of the whole
        module, which must collect those nine. The second is the matched
        control: without it, a broken ``-m`` expression would make the first
        pass for the wrong reason.
        """

        def collected(selection: str, marker_expression: str) -> int:
            completed = subprocess.run(
                [
                    sys.executable, "-m", "pytest", selection,
                    "-m", marker_expression, "--collect-only", "-q",
                    "-o", "addopts=", "-p", "no:cacheprovider",
                ],
                cwd=str(REPO), capture_output=True, text=True, timeout=300,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            return len([
                line for line in completed.stdout.splitlines()
                if "::" in line and line.startswith("tests/")
            ])

        assert collected(EXPOSED_SELECTION, "db_required") == 0
        assert collected(MARKED_SELECTION_MODULE, "db_required") >= 1


class TestColdDatabase_TheTwoDatabaseGatesStayAttributable:
    """AC-4 — a skip or a red still says which gate fired."""

    @staticmethod
    def _marked_item():
        class _Marker:
            name = "db_required"

        class _Item:
            def iter_markers(self):
                return [_Marker()]

        return _Item()

    def test_the_bare_variable_gate_and_the_resolution_gate_differ(
        self, monkeypatch
    ) -> None:
        """CARD-278's gate attributed its skips by reading these two apart.

        The bare-``DATABASE_URL`` check and the per-worktree resolution are
        deliberately distinguishable, and a fix that merged them would lose a
        diagnostic the board uses to say which of 27 skips came from where.
        Both reasons are provoked here and compared, so a tidy-up that gave
        them one wording fails.
        """
        monkeypatch.delenv(VAR, raising=False)
        with pytest.raises(pytest.skip.Exception) as bare:
            suite_conftest.pytest_runtest_setup(self._marked_item())

        monkeypatch.setenv(VAR, db_name.resolve_test_database_url(os.environ, REPO))
        monkeypatch.setattr(
            suite_conftest, "_unusable_reason",
            lambda _url: "the per-worktree database said so",
        )
        with pytest.raises(pytest.skip.Exception) as resolved:
            suite_conftest.pytest_runtest_setup(self._marked_item())

        assert f"{VAR} is not set" in str(bare.value)
        assert "the per-worktree database said so" in str(resolved.value)
        assert str(bare.value) != str(resolved.value)

    def test_the_resolution_gate_still_passes_a_usable_database_through(
        self, monkeypatch
    ) -> None:
        """The matched control: neither gate fires when there is nothing wrong."""
        monkeypatch.setenv(VAR, db_name.resolve_test_database_url(os.environ, REPO))
        monkeypatch.setattr(suite_conftest, "_unusable_reason", lambda _url: None)
        suite_conftest.pytest_runtest_setup(self._marked_item())

    def test_the_eager_setups_note_is_a_third_channel(self, monkeypatch) -> None:
        """It announces itself under its own prefix, so an attribution is possible.

        Both existing gates skip with ``Database not reachable: …``. This
        card's line is a terminal-summary note under ``database setup:`` — a
        different channel *and* a different prefix, so a reader counting the
        board's 26 database skips never has to wonder whether one of them came
        from here.
        """
        monkeypatch.setattr(
            suite_conftest, "_ARMED_SETUP",
            {
                "action": suite_conftest._ARM_PREPARE,
                "database": "nonogram_whatever_test",
                "reason": "something",
            },
        )
        note = suite_conftest.armed_database_note()
        assert note.startswith("database setup:")
        assert "Database not reachable" not in note

    def test_the_eager_setup_hides_nothing_from_the_marked_path(self) -> None:
        """G-2 — the eager fixture cannot make either gate quieter.

        It catches any stop from ``_test_database_tables``, which it must:
        letting one out of a session-autouse fixture would skip or error the
        *whole suite*, which is the permanent false green ADR-0038/R8 forbids.
        What makes that catch safe is that the marked path never consults what
        it recorded —
        ``db_session`` and ``pytest_runtest_setup`` reach the same skip through
        ``_refuse_unless_test_database`` and ``_unusable_reason`` as before,
        and pytest re-raises a session fixture's cached exception to every
        later requester.

        Derived from the conftest's own text rather than asserted in prose, so
        a later edit that made either gate read this card's state fails here.
        """
        tree = ast.parse(
            (REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
        )
        gates = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name in {"db_session", "pytest_runtest_setup"}
        }
        assert set(gates) == {"db_session", "pytest_runtest_setup"}
        this_cards_names = {
            "_ARMED_SETUP", "armed_database_note", "_armed_database_plan",
            "_armed_database_is_ready", "_database_name_of",
        }
        for name, node in gates.items():
            touched = {
                child.id for child in ast.walk(node) if isinstance(child, ast.Name)
            } | _referenced_names(node)
            assert not touched & this_cards_names, (name, sorted(touched & this_cards_names))

    @pytest.mark.db_required
    @pytest.mark.slow
    def test_a_swallowed_stop_still_errors_every_test_that_asks_for_the_database(
        self, tmp_path
    ) -> None:
        """G-2, behaviourally — the half the structural test above cannot see.

        ``test_the_eager_setup_hides_nothing_from_the_marked_path`` checks by
        ``ast`` that neither gate *reads* this card's recorded state. That is
        a real guard and it is not this one: it would hold just as well if
        pytest discarded a swallowed session-fixture stop entirely, which is
        the failure mode that would make the widened catch a G-2 violation.
        The catch's whole justification is pytest's fixture-result cache, and
        until now that claim was unguarded in the tree — the same defect one
        layer deeper than F-001's.

        So this runs the **real** suite in a subprocess with a stop injected
        into ``_rebuild_public_schema``, as the class the old clause could not
        catch, and asserts the shape that makes widening a *restoration* of
        the pre-fix blast radius rather than a silencing of it:

        * the test that asks for ``db_session`` **errors**, carrying the
          injected stop's own message, re-raised from the cache;
        * its body never runs — an error at setup, not a pass;
        * the test that never asks **passes**, which is the matched control
          for "the eager fixture did swallow it"; without the swallow that
          test would error too, under this card's fixture name, which is
          exactly F-001's measured regression.

        And the second matched control is the same selection with nothing
        injected: both tests pass. Without it, a selection that errored for
        some unrelated reason would satisfy every assertion above.
        """
        injector = tmp_path / "card349_stop_injector.py"
        injector.write_text(_STOP_INJECTOR, encoding="utf-8")

        clean_code, clean_output = _run_the_pair(tmp_path, inject=False)
        assert clean_code == 0, clean_output
        # Substrings rather than ``_outcome`` equality: that helper keeps
        # pytest's ``=`` decoration and any ``, N warnings`` clause, so the
        # existing probes only ever compare two of its results to each other
        # and never to a literal.
        assert "2 passed" in clean_output, clean_output
        assert " error" not in clean_output, clean_output

        code, output = _run_the_pair(tmp_path, inject=True)
        assert code != 0, output

        # The asker errors, and the error carries the injected reason.
        assert f"ERROR {_ASKS_FOR_THE_DATABASE}" in output, output
        assert _STOP_MARKER in output, output
        assert "OperationalError" in output, output
        # An error at *setup*, in pytest's own words, so the body never ran.
        assert f"{_AT_SETUP}test_db_session_fixture_works" in output, output
        # The matched control: the test that never asks is untouched.
        assert f"ERROR {_NEVER_ASKS}" not in output, output
        assert f"FAILED {_NEVER_ASKS}" not in output, output
        assert "1 passed" in output, output
        assert "1 error" in output, output
        # And the eager fixture did swallow it — otherwise the note would be
        # absent and the error above would name this card's fixture instead.
        assert "database setup:" in output, output
        assert f"{_AT_SETUP}test_the_same_root_always" not in output, output


class TestColdDatabase_TheRefusalIsNeitherWidenedNorBypassed:
    """AC-5 — ``_refuse_unless_test_database`` is untouched, and still first.

    The acceptance test AC-5 names is the existing one,
    ``tests/test_card_156_db_fixture.py``
    ``::TestDbFixture_RefusesANonTestDatabase::test_db_session_fails_without_connecting``:
    it provokes the refusal and asserts, through a spy on
    ``sqlalchemy.create_engine``, ``session.create_engine`` and
    ``psycopg2.connect``, that nothing connected before the refusal. What is
    added here is the one thing that test cannot know about — that this card's
    new path asks the same question first.
    """

    def test_a_non_test_database_is_refused_before_anything_is_prepared(
        self, monkeypatch
    ) -> None:
        """The live panel's own database, fed in as the armed and resolved one.

        ``nonogram_poc`` is what ``_refuse_unless_test_database`` exists to
        keep out of reach, so it is the case to put in front of the new plan.
        ``_ensure_test_database`` is made to fail loudly if it is ever
        reached: the refusal has to come from the URL's text, before a
        connection, and not from a second opinion downstream.
        """
        monkeypatch.setattr(
            suite_conftest, "_ensure_test_database",
            lambda url: pytest.fail(f"prepared {url!r}", pytrace=False),
        )
        live = "postgresql://u:p@localhost:5432/nonogram_poc"
        _url, _resolved, action = suite_conftest._armed_database_plan(
            {"DATABASE_URL": live, "TEST_DATABASE_URL": live}
        )
        assert action == suite_conftest._ARM_REFUSED

    def test_the_prepare_branch_is_reachable_only_past_the_refusal(self) -> None:
        """The matched control, and the structural half.

        The test above would also pass against a plan that refused
        *everything*, so the other side of the line is asserted too: this
        worktree's own derived URL reaches the prepare branch. And the
        conftest's text is read to confirm the decision still goes through
        ``_refusal_reason`` rather than a second copy of the suffix rule — a
        widened guard is most likely to arrive as a re-implementation.
        """
        ours = db_name.default_test_database_url(REPO)
        _url, _resolved, action = suite_conftest._armed_database_plan(
            {"DATABASE_URL": ours, "TEST_DATABASE_URL": ours}
        )
        assert action == suite_conftest._ARM_PREPARE

        source = (REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
        plan = next(
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef)
            and node.name == "_armed_database_plan"
        )
        assert "_refusal_reason" in _referenced_names(plan)
        assert "endswith" not in _referenced_names(plan)

    def test_the_suffix_rule_itself_is_unchanged(self) -> None:
        """The refusal still refuses by name, and still admits what it admitted.

        Three names the guard was shipped refusing, and one it was shipped
        admitting. If a later card widens the rule to admit a prefix — the
        change ``tests/db_name.py``'s docstring explains was deliberately
        avoided — this fails beside the existing CARD-156 tests rather than
        instead of them.
        """
        for refused in (
            "postgresql://u:p@h:5432/nonogram_poc",
            "postgresql://u:p@h:5432/nonogram_test_backup",
            "postgresql://u:p@h:5432/nonogram_dev",
        ):
            assert suite_conftest._refusal_reason(refused) is not None, refused
        assert suite_conftest._refusal_reason(
            "postgresql://u:p@h:5432/nonogram_test"
        ) is None
