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

    Three conditions, all of them checked here and not upstream: the name ends
    in ``_test``, ``conftest._refusal_reason`` allows it, and it is not any
    database a live worktree or the live panel owns. G-1 is the reason this
    reads like paranoia — the one operation in this module that destroys
    anything must not be able to destroy anything else.
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

        It catches ``pytest.skip`` and ``pytest.fail`` from
        ``_test_database_tables``, which it must: letting either out of a
        session-autouse fixture would skip or error the *whole suite*, which
        is the permanent false green ADR-0038/R8 forbids. What makes that
        catch safe is that the marked path never consults what it recorded —
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
