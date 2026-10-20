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
    """``(every test function, those carrying db_required, the Test* classes seen)``.

    Read from the module's own AST, not from ``request.session.items``
    (cycle-1 review F-003). The collection answers "how many db_required tests
    did this *run* select", so any legal targeted selection — one node id,
    ``-k``, ``--lf`` — made the count red for a reason that has nothing to do
    with the code: the single-node-id selection reported
    ``0 test(s) here carry db_required, expected 2``. On the card whose whole
    subject is that a red must mean the code, the run is the wrong source.

    Keys are ``Class::test`` (or the bare name for a module-level test). A
    class-level ``@pytest.mark.db_required`` marks every test the class
    contains.

    This walk is deliberately **not** a model of pytest's marker resolution,
    and does not claim to be (cycle-2 review C2-F-002). What it sees is:
    AST-visible ``@pytest.mark.db_required`` decorators on ``Test``-prefixed
    classes and their direct ``test*`` methods, and on module-level ``test*``
    functions. Nothing else. Everything it misses biases the count to **red**,
    which is the safe direction here and costs nothing — measured, by feeding
    source text to this function and comparing against pytest's own
    collection: a module-level ``pytestmark``, a class-level ``pytestmark``, a
    marker inherited from a base class, the parenthesised
    ``@pytest.mark.db_required()`` form and a nested test class all come back
    as 0 where pytest collects 1 or 2.

    Two directions could fail **open**, and only the first is closed here.
    One: a class renamed off pytest's ``Test*`` prefix — pytest then collects
    nothing from it while a walk that took ``test*`` methods out of any
    ``ClassDef`` still counted them, so the coverage AC-4 exists to protect
    would go to zero with the count still green. Hence the ``Test`` prefix is
    a filter here, and the third return value is the set of classes that
    passed it, so the caller can assert the filter did not silently empty the
    walk. Control: ``test_a_class_renamed_off_pytests_prefix_is_not_counted``.
    Two: a ``Test*`` class that carries an ``__init__`` — pytest refuses to
    collect it and says so (``PytestCollectionWarning: cannot collect test
    class ... because it has a __init__ constructor``) while this walk still
    counts its methods. Measured, on a class holding one ``db_required``
    marker and one ``test_a``: pytest 0 collected, this walk ``db_required ==
    {'TestHasInit::test_a'}`` (cycle-3 review C3-F-002). That direction is
    stated rather than filtered: the warning makes the loss loud in the run,
    and the module's two ``db_required`` tests are independently pinned by the
    AC-1/AC-2 controls.
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

    every, db_required, test_classes = set(), set(), set()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("Test"):
                continue
            test_classes.add(node.name)
            for child in tests_in(node.body):
                name = f"{node.name}::{child.name}"
                every.add(name)
                if marked(node) or marked(child):
                    db_required.add(name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            every.add(node.name)
            if marked(node):
                db_required.add(node.name)
    return every, db_required, test_classes


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


def _is_setattr_call(node) -> bool:
    """Any call *named* ``setattr``: ``anything.setattr(...)`` or the builtin.

    The match is on the NAME, not on what the name is bound to: ``sa = setattr``
    followed by ``sa(app_session, "engine", None)`` is invisible here. That sits
    inside this guard's declared "names, not values" bound and is measured at
    zero sites in this tree — it is said out loud because "``setattr``-shaped",
    which this docstring used to say, promises a reach the mechanism does not
    have (cycle-3 review, suggestion (c)).

    Both spellings, because the deny default below is only total over the shapes
    it binds if neither spelling gets to decide that it is out of scope.
    Requiring ``node.func`` to be an ``ast.Attribute`` is what let cycle-2
    review mutant X2
    (``setattr(app_session, "engine", None)``) through the previous version
    while this class's docstring named ``setattr(module, "name", …)`` as a
    spelling it saw. The builtin is also the more dangerous of the two —
    ``monkeypatch`` reverses itself at teardown and ``setattr`` does not — and
    this tree uses it on modules and classes at a dozen sites.
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        (isinstance(func, ast.Attribute) and func.attr == "setattr")
        or (isinstance(func, ast.Name) and func.id == "setattr")
    )


def _string_target_tail(node) -> str | None:
    """The attribute name a ``setattr`` string target ends in, or ``None``.

    ``"nonogram.db.session.engine"`` → ``"engine"``. Also ``f"{MOD}.engine"``
    and ``MOD + ".engine"`` → ``"engine"``: the trailing literal segment of a
    computed target is statically readable even when the module part is not,
    which is what keeps the total default from reding on the tree's real
    computed targets (``monkeypatch.setattr(f"{__name__}._WEB_SOURCES", [])``
    names ``_WEB_SOURCES``, so it is nothing to this guard). ``None`` means
    the guard cannot read the name at all, and its caller fails on that.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.rpartition(".")[2]
    if isinstance(node, ast.JoinedStr) and node.values:
        tail = node.values[-1]
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        tail = node.right
    else:
        return None
    if isinstance(tail, ast.Constant) and isinstance(tail.value, str) and "." in tail.value:
        return tail.value.rpartition(".")[2]
    return None


def _string_target_module(node) -> str | None:
    """The module part of a ``setattr`` string target, or ``None`` if unreadable.

    Only a whole string literal is readable. A computed target
    (``f"{MOD}.engine"``) returns ``None``, and the caller turns that into a
    FAILURE rather than a pass, because it cannot rule out that the computed
    part is the session module — cycle-2 review mutant X3.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.rpartition(".")[0]
    return None


def _private_global_sites_in(source: str, filename: str, names):
    """``(Counter of (filename, name) per SITE, unanalysable spellings)``.

    Counts occurrences, not distinct ``(file, name)`` pairs, so that the
    equality in ``test_no_test_file_outside_the_exemption_sets_those_globals``
    is the decision :data:`_EXEMPT_PRIVATE_GLOBAL_SITES` says it is.

    The deny default is total **over the shapes it binds**, and that is the
    whole design. The shapes it binds are two: every ``setattr``-shaped call
    with **two or more positional arguments** (the arity dispatch below), and
    every **simple** attribute assignment target
    (``isinstance(target, ast.Attribute)`` in an :class:`ast.Assign`). What
    falls between them reaches no branch at all, so it is neither recorded nor
    appended to ``unanalysable``: a ``setattr`` whose target or name arrives as
    a keyword, and an attribute target nested in a tuple or list unpacking or
    carried by an annotated, ``for`` or ``with`` target. Both are measured at
    zero sites in this tree and held there by
    ``test_the_binding_frontier_is_empty_in_this_tree`` (cycle-3 review
    C3-F-001). Cycles 1
    and 2 of this card's review each widened this function by enumerating
    spellings and then described a reach one shape wider than the new
    enumeration; a fourth shape exists for any finite list. So the rule here
    is not a list of shapes:

    * every ``setattr``-shaped call is analysed — ``anything.setattr(...)``
      **and** the bare builtin (:func:`_is_setattr_call`);
    * a readable attribute name that is not in ``names`` ends the analysis:
      the call demonstrably does not touch one of ``session.py``'s engine
      globals;
    * a target the guard resolves to some **other** module or object ends it
      too. That discrimination is the reason the default can be total without
      drowning in false reds — measured over this tree, it is what keeps 13
      sites (a non-literal attribute name on a target that is plainly not the
      session module) and 315 more (a readable attribute name that simply is
      not one of the engine globals) out of the failure list. It has its own
      control (``test_a_setattr_on_another_module_is_not_this_guards_business``);
    * everything that is left is a FAILURE, appended to the second list: a
      target the guard cannot rule out, and an attribute name it cannot read
      while the target is — or might be — the session module (ADR-0039/R2).

    The two argument shapes are told apart by **arity**, which is what
    distinguishes them in Python rather than a guess: three or more positional
    arguments is ``setattr(obj, "name", value)``; two is ``monkeypatch``'s
    ``setattr("dotted.path.name", value)``, and the builtin cannot take two.
    Alongside them, the dotted assignment ``db_session.engine = …`` (any
    chain, so ``nonogram.db.session.engine = …`` counts too — mutant M3's
    shape), whose attribute name is always readable and whose receiver is a
    failure whenever the guard cannot rule it out.

    The one residual, stated because it is **not** covered: this guard
    follows *names*, not values. A call whose target is a computed value (a
    subscript, a call result) *and* whose attribute name is also non-literal
    gives it nothing on either axis, so it is skipped rather than failed.
    Measured over this tree, exactly two such sites exist —
    ``tests/property/test_book_membership_floor.py:190`` and
    ``tests/test_book_finalise_gutter.py:1511``, both
    ``setattr(<a book row>, column, value)`` — and failing on them would be a red the guard cannot
    discriminate without guessing. When the attribute name *is* readable the
    target's provenance stops mattering:
    ``setattr(sys.modules["nonogram.db.session"], "engine", …)`` fails.
    Control: ``test_a_computed_target_with_an_unreadable_name_is_the_declared_bound``.
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
        elif _is_setattr_call(node) and len(node.args) >= 3:
            # ``setattr(obj, name, value)`` — the attribute name is args[1].
            target, name_node = node.args[0], node.args[1]
            readable = (
                name_node.value
                if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str)
                else None
            )
            if readable is not None and readable not in names:
                continue  # a readable name outside `names` is nothing to this guard
            chain = _dotted(target)
            if _names_the_session_module(chain, aliases) is False:
                continue  # some other module or object — none of this guard's business
            if readable is not None:
                record(
                    chain, readable, node,
                    f'setattr({ast.unparse(target)}, "{readable}", ...)',
                )
            elif chain is None:
                continue  # the declared bound: a computed target AND an unreadable name
            else:
                unanalysable.append(
                    f"{filename}:{node.lineno}: "
                    f"setattr({ast.unparse(target)}, {ast.unparse(name_node)}, ...) "
                    "— the attribute name is not a literal this guard can read, and "
                    "the target is not ruled out"
                )
        elif _is_setattr_call(node) and len(node.args) == 2:
            # ``setattr("dotted.path.name", value)`` — monkeypatch's string target.
            target = node.args[0]
            tail = _string_target_tail(target)
            if tail is None:
                unanalysable.append(
                    f"{filename}:{node.lineno}: setattr({ast.unparse(target)}, ...) "
                    "— the target string is not one this guard can read"
                )
            elif tail in names:
                module = _string_target_module(target)
                if module is None:
                    unanalysable.append(
                        f"{filename}:{node.lineno}: setattr({ast.unparse(target)}, ...) "
                        f"— names {tail!r} on a module this guard cannot read"
                    )
                else:
                    record(module, tail, node, f'setattr("{target.value}", ...)')
    return sites, unanalysable


def _binding_frontier_reaches_in(source: str, filename: str, names):
    """The reaches that fall OUTSIDE :func:`_private_global_sites_in`'s dispatch.

    That function binds two shapes — a ``setattr``-shaped call with two or more
    positional arguments, and a *simple* attribute target in an
    :class:`ast.Assign`. This one reports what falls between them and still
    reaches ``session.py``: a ``setattr`` with fewer than two positional
    arguments (target or name bound by keyword, or starred), and an attribute
    target naming one of ``names`` while nested in a tuple/list unpacking or
    carried by an annotated, ``for`` or ``with`` target. Cycle-3 review
    C3-F-001 measured both at zero sites in this tree; this is what keeps that
    measured instead of asserted in prose.

    Scoped by the guard's own discrimination — a target resolved to some
    **other** module is none of its business — and deliberately coarser than
    the guard on the keyword half: it does not read a keyword-bound attribute
    name, so any such call on the session module is reported whichever
    attribute it names. That over-reds relative to the guard's "a readable name
    outside ``names`` ends the analysis" rule, which is the safe direction for
    a frontier that is empty.
    """
    def non_simple_attribute_targets(node):
        """``(attribute target, the shape carrying it)``, or ``[]``."""
        if isinstance(node, ast.Assign):
            carriers = [t for t in node.targets if isinstance(t, (ast.Tuple, ast.List))]
            shape = "nested in a tuple/list unpacking"
        elif isinstance(node, ast.AnnAssign):
            carriers, shape = [node.target], "an annotated assignment target"
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            carriers, shape = [node.target], "a for-loop target"
        elif isinstance(node, ast.withitem):
            carriers = [node.optional_vars] if node.optional_vars is not None else []
            shape = "a with-statement target"
        else:
            return []
        return [
            (inner, shape) for carrier in carriers for inner in ast.walk(carrier)
            if isinstance(inner, ast.Attribute)
        ]

    tree = ast.parse(source)
    aliases = set(_SESSION_ALIASES) | _session_aliases_in(tree)
    reaches = []

    def not_ruled_out(node) -> bool:
        # `None` (unreadable) stays in, like everywhere else in this guard.
        return _names_the_session_module(_dotted(node), aliases) is not False

    for node in ast.walk(tree):
        if _is_setattr_call(node) and len(node.args) < 2:
            receiver = node.args[0] if node.args else next(
                (kw.value for kw in node.keywords if kw.arg == "target"), None
            )
            if not_ruled_out(receiver):
                reaches.append(
                    f"{filename}:{node.lineno}: {ast.unparse(node)} "
                    "— fewer than two positional arguments, so neither arity "
                    "branch analyses it"
                )
        for target, shape in non_simple_attribute_targets(node):
            if target.attr in names and not_ruled_out(target.value):
                reaches.append(
                    f"{filename}:{target.lineno}: {ast.unparse(target)} = ... as "
                    f"{shape} — not a simple ast.Assign attribute target, so no "
                    "branch analyses it"
                )
    return reaches


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


def _binding_frontier_reaches(names):
    """:func:`_binding_frontier_reaches_in`, over every file under ``tests/``."""
    reaches = []
    for path in sorted((REPO / "tests").rglob("*.py")):
        reaches.extend(
            _binding_frontier_reaches_in(path.read_text(encoding="utf-8"), path.name, names)
        )
    return reaches


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
        every, db_required, test_classes = _test_functions_in(
            here.read_text(encoding="utf-8")
        )
        assert test_classes, (
            "no ``Test``-prefixed class survived the class-name filter in "
            "_test_functions_in, so the count below is vacuous — the filter "
            "must not be able to silently empty the walk (cycle-2 review "
            "C2-F-002)"
        )
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

    def test_a_class_renamed_off_pytests_prefix_is_not_counted(self) -> None:
        """C2-F-002: the one direction the AST count could fail *open*.

        Rename a class off pytest's ``Test*`` prefix and pytest collects
        nothing from it — the coverage AC-4 exists to protect goes to zero.
        The cycle-1 collection-based count caught that shape; the AST count
        that replaced it did not, because it took ``test*`` methods out of any
        ``ClassDef`` regardless of the class's own name, so the count stayed
        at 2 while pytest collected 0. The ``Test`` prefix is a filter now,
        and this is its control: the renamed class contributes neither a test
        nor a ``db_required`` marker, so the equality above goes red instead
        of hiding the loss.

        Every other divergence from pytest's marker resolution biases the
        count to red and is declared in :func:`_test_functions_in` rather than
        fixed here — this is the only one that biased it to green.
        """
        source = (
            "import pytest\n\n"
            "@pytest.mark.db_required\n"
            "class TestKeptByTheFilter:\n"
            "    def test_one(self):\n"
            "        pass\n\n"
            "@pytest.mark.db_required\n"
            "class RenamedOffThePytestPrefix:\n"
            "    def test_two(self):\n"
            "        pass\n"
        )
        every, db_required, test_classes = _test_functions_in(source)
        assert test_classes == {"TestKeptByTheFilter"}, (
            "the class-name filter does not match pytest's default "
            f"``python_classes``, so the count is not about what runs: {sorted(test_classes)}"
        )
        assert every == {"TestKeptByTheFilter::test_one"}, (
            "a class pytest does not collect still contributes tests to the "
            f"count, which is the fail-open direction of C2-F-002: {sorted(every)}"
        )
        assert db_required == {"TestKeptByTheFilter::test_one"}, (
            "a class pytest does not collect still contributes db_required "
            f"tests, so renaming it would hide the lost coverage: {sorted(db_required)}"
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
    recognises three spellings — a dotted assignment,
    ``setattr(obj, "name", …)`` in **both** the ``monkeypatch.setattr`` and
    the bare-builtin form, and ``setattr("dotted.path.name", …)`` — by the
    aliases the scanned file itself binds (both import spellings) on top of
    :data:`_SESSION_ALIASES`; **and it fails on anything ``setattr``-shaped
    whose target or whose attribute name it cannot read.** That second
    sentence holds inside one frontier, stated here because it is where the
    mechanism stops: the analysis is over **positional** argument binding and
    **simple** assignment targets. A ``setattr`` whose target or whose
    attribute name arrives as a *keyword*
    (``monkeypatch.setattr(app_session, name="engine", value=None)``), and an
    attribute target nested in a tuple or list unpacking or carried by an
    annotated, ``for`` or ``with`` target
    (``app_session.engine, app_session.SessionLocal = None, None``), are
    outside it — they really do set the globals, and this guard passes them
    silently. Both are measured at **zero sites** in this tree, and
    ``test_the_binding_frontier_is_empty_in_this_tree`` is what keeps that
    true: a control that reds on the first such site, rather than a sentence
    promising there can be none. Cycle 1 of this card's review widened a list
    of three spellings and claimed three; cycle 2 found the next three out;
    cycle 3 widened the mechanism and claimed it had no outside. A claim about
    a finite shape list always has a fourth shape.

    Each clause has a control in this class, and six of them are verbatim
    mutants from the two review cycles that SURVIVED the guard version they
    were aimed at — R1, R2, R3 (cycle 1) and X1, X2, X3 (cycle 2) — plus the
    deny-on-unanalysable default R3 exposed. The *discrimination* that makes a
    total default affordable has its own control as well
    (``test_a_setattr_on_another_module_is_not_this_guards_business``):
    without it the guard would red on idioms this tree already uses: measured,
    13 sites set a non-literal attribute name on a target that is plainly not
    the session module, and 315 more set a readable attribute name that simply
    is not one of the engine globals.

    Measured on this head, over every file under ``tests/``: the total guard
    finds **nine sites** (six ``(file, name)`` pairs) and **zero**
    unanalysable spellings. So :data:`_EXEMPT_PRIVATE_GLOBAL_SITES` is an
    equality over the entire set the guard sees, not over a subset of it —
    there is nothing the guard reports that the exemption does not account
    for, and nothing it declines to report that it could have read.

    The bound that remains, and it is one bound said twice: the guard follows
    **names, not values**. A test file that reached the globals through
    something no AST walk can follow — a name bound by a fixture,
    ``importlib.import_module`` into a local, a ``globals()`` or ``vars()``
    write — is outside it. So is the single ``setattr`` corner where the
    target is a computed value *and* the attribute name is non-literal, which
    gives the guard nothing on either axis; that corner is measured at two
    book-row sites in this tree (measured, not estimated) and is skipped
    rather than failed for exactly that reason (:func:`_private_global_sites_in`, and
    ``test_a_computed_target_with_an_unreadable_name_is_the_declared_bound``
    pins both it and its edge).
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

    def test_the_binding_frontier_is_empty_in_this_tree(self) -> None:
        """The frontier of :func:`_private_global_sites_in`, asserted not said.

        That function binds *positional* argument binding and *simple*
        assignment targets. Shapes that fall between its branches reach
        ``session.py``'s engine globals and pass it silently — a ``setattr``
        whose target or name arrives as a keyword, and an attribute target
        nested in a tuple or list unpacking or carried by an annotated,
        ``for`` or ``with`` target. Cycle-3 review C3-F-001 measured every one
        of them at **zero sites** in this tree, which is why the remedy was
        this assertion rather than a fourth widening of the mechanism: the
        frontier stops being a sentence and becomes a control that reds on the
        first such site, naming its file, line and spelling.

        Two halves, because a frontier assertion over a tree that is empty
        would also pass if the scan saw nothing at all: each named shape is
        fed to the scan as source text and must be reported, and the whole of
        ``tests/`` must report nothing. The third assertion is the edge — the
        same keyword-bound spelling on a target that is plainly **not** the
        session module is not a finding here and must not become one, or this
        control would be a different, wrong claim
        (``test_a_setattr_on_another_module_is_not_this_guards_business``).
        """
        names = _global_names_assigned_by("_init_engine")
        imported = "from nonogram.db import session as app_session\n"
        for shape in (
            '    monkeypatch.setattr(app_session, name="engine", value=None)',
            '    monkeypatch.setattr(target=app_session, name="engine", value=None)',
            "    setattr(*TRIPLE_NAMING_THE_SESSION_MODULE)",
            "    app_session.engine, app_session.SessionLocal = None, None",
            "    [app_session.engine] = [None]",
            "    app_session.engine: object = None",
            "    for app_session.engine in [None]: pass",
            '    with open("x") as app_session.engine: pass',
        ):
            source = f"{imported}\n\ndef test_frontier_probe(monkeypatch):\n{shape}\n"
            assert _binding_frontier_reaches_in(source, "test_not_exempt.py", names), (
                "this spelling reaches session.py's engine globals through a "
                "shape the AC-5 guard does not analyse, and the frontier scan "
                f"does not report it either, so nothing sees it: {shape.strip()}"
            )
            sites, unanalysable = _private_global_sites_in(source, "test_not_exempt.py", names)
            assert dict(sites) == {} and unanalysable == [], (
                "the guard itself now analyses this shape, so it is no longer "
                "outside the frontier: widen the frontier's statement and this "
                f"control together. {shape.strip()}: {dict(sites)} / {unanalysable}"
            )

        assert not _binding_frontier_reaches_in(
            "import other_module\n\n"
            "def test_edge(monkeypatch):\n"
            '    monkeypatch.setattr(other_module, name="engine", value=None)\n',
            "test_not_exempt.py",
            names,
        ), (
            "the frontier reds on a keyword-bound setattr aimed at a module "
            "this guard has already resolved to something other than "
            "session.py, which makes it a different and wrong claim"
        )

        outside = _binding_frontier_reaches(names)
        assert not outside, (
            "these test-tree lines set one of session.py's engine globals "
            "through a shape the AC-5 guard does not analyse at all — it "
            "neither counts them as sites nor reports them as unanalysable, "
            "so they pass it silently. Either route the reset through "
            "reset_engine() (AC-5), or widen _private_global_sites_in and the "
            "frontier stated on this class together (cycle-3 review "
            "C3-F-001):\n  " + "\n  ".join(outside)
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

    # --- the three shapes cycle 2 found one layer out -------------------
    # X1/X2/X3 are the cycle-2 review's verbatim mutants. All three SURVIVED
    # the cycle-1 guard (9 passed, unanalysable empty), two of them while the
    # class docstring above named their spelling. They are controls for the
    # *total* deny default rather than for three more branches: X2 pins the
    # call-shape axis, X1 the attribute-name axis, X3 the string-target axis.

    def test_the_bare_builtin_setattr_spelling_is_a_site(self) -> None:
        """X2: ``setattr(app_session, "engine", None)``, no monkeypatch receiver.

        The guard required ``node.func`` to be an ``ast.Attribute``, so the
        builtin was invisible — while the claim above literally named
        ``setattr(module, "name", …)``. It is the more dangerous of the two
        spellings as well: ``monkeypatch`` undoes itself at teardown and this
        does not.
        """
        names = _global_names_assigned_by("_init_engine")
        sites, unanalysable = _private_global_sites_in(
            "from nonogram.db import session as app_session\n\n"
            "def test_x2_control():\n"
            '    setattr(app_session, "engine", None)\n',
            "test_not_exempt.py",
            names,
        )
        assert not unanalysable
        assert dict(sites) == {("test_not_exempt.py", "engine"): 1}, (
            "the bare builtin setattr is invisible to the guard, so a spelling "
            f"the AC-5 claim names is outside its mechanism: {dict(sites)}"
        )

    def test_a_non_literal_attribute_name_is_a_failure(self) -> None:
        """X1: ``monkeypatch.setattr(app_session, name, None)`` — the tree's own idiom.

        The target resolves to the session module and the attribute name
        cannot be read, so the guard cannot say *which* global is set and
        therefore cannot say the site is exempt. ADR-0039/R2 makes that a
        failure, not nothing to see. This spelling is at six sites in this
        tree today, on other objects.
        """
        names = _global_names_assigned_by("_init_engine")
        sites, unanalysable = _private_global_sites_in(
            "from nonogram.db import session as app_session\n\n"
            '@pytest.mark.parametrize("name", ["engine", "SessionLocal"])\n'
            "def test_x1_control(monkeypatch, name):\n"
            "    monkeypatch.setattr(app_session, name, None)\n",
            "test_not_exempt.py",
            names,
        )
        assert dict(sites) == {}, (
            f"a non-literal name cannot be counted as a site: {dict(sites)}"
        )
        assert len(unanalysable) == 1, (
            "a setattr on the session module whose attribute name the guard "
            "cannot read must come back as a failure, not as nothing to see: "
            f"{unanalysable}"
        )

    def test_a_computed_string_target_is_a_failure(self) -> None:
        """X3: ``monkeypatch.setattr(f"{MOD}.engine", None)`` and ``MOD + ".engine"``.

        The trailing literal segment names ``engine``, so the guard knows the
        call sets one of ``session.py``'s globals; the module part is computed,
        so it cannot rule out that it is the session module. Both halves of
        that are needed — reading the tail is what keeps
        ``monkeypatch.setattr(f"{__name__}._WEB_SOURCES", [])`` (which this
        tree really does contain) out of the failure list. The third spelling
        here is a target the guard cannot read at all (a bare name holding the
        path), which is a failure for the same reason.
        """
        names = _global_names_assigned_by("_init_engine")
        sites, unanalysable = _private_global_sites_in(
            '_X3_MODULE = "nonogram.db.session"\n'
            '_X3_TARGET = "nonogram.db.session.engine"\n\n'
            "def test_x3_control(monkeypatch):\n"
            '    monkeypatch.setattr(f"{_X3_MODULE}.engine", None)\n'
            '    monkeypatch.setattr(_X3_MODULE + ".SessionLocal", None)\n'
            "    monkeypatch.setattr(_X3_TARGET, None)\n",
            "test_not_exempt.py",
            names,
        )
        assert dict(sites) == {}, (
            f"a computed module part cannot be resolved to a site: {dict(sites)}"
        )
        assert len(unanalysable) == 3, (
            "a string target the guard cannot read must be a failure for every "
            "spelling of it — a computed module part, a concatenation, and a "
            f"target it cannot read at all: {unanalysable}"
        )

    def test_a_setattr_on_another_module_is_not_this_guards_business(self) -> None:
        """The discrimination that makes the total deny default affordable.

        Two things end the analysis without a failure: a target the guard
        resolves to something that is **not** the session module, and an
        attribute name it *can* read that is not one of the engine globals.
        Without them a total default would red on idioms this tree already
        uses — ``monkeypatch.setattr(SomeClass, name, …)``, the bare builtin on
        a class, and a computed string target naming some other module's
        attribute. Measured: 13 sites in the first arm, 315 in the second.

        This is the control for both arms, and the measurement that says they
        are enough is ``test_no_test_file_outside_the_exemption_sets_those_globals``
        itself: zero unanalysable spellings over the whole of ``tests/``.
        """
        names = _global_names_assigned_by("_init_engine")
        sites, unanalysable = _private_global_sites_in(
            "from nonogram.book.pdf import BookPDFGenerator\n"
            "from nonogram.db import session as app_session\n\n"
            "def test_other_targets(monkeypatch, name):\n"
            "    monkeypatch.setattr(BookPDFGenerator, name, None)\n"
            "    setattr(BookPDFGenerator, name, None)\n"
            '    monkeypatch.setattr(f"{__name__}._WEB_SOURCES", [])\n'
            '    monkeypatch.setattr("nonogram.web.pages._CACHE", None)\n'
            '    monkeypatch.setattr(app_session, "get_session", None)\n',
            "test_not_exempt.py",
            names,
        )
        assert dict(sites) == {}, (
            "none of these touches one of session.py's engine globals, so none "
            f"is a site: {dict(sites)}"
        )
        assert unanalysable == [], (
            "the guard reds on setattr calls that are plainly none of its "
            "business, which is how a total deny default becomes unusable: "
            f"{unanalysable}"
        )

    def test_a_computed_target_with_an_unreadable_name_is_the_declared_bound(
        self,
    ) -> None:
        """The residual, pinned so that it stays *stated* rather than drifting.

        The guard follows names, not values. When the target is a computed
        value **and** the attribute name is non-literal it has nothing on
        either axis, and it skips: there are exactly two such sites in this
        tree (``tests/property/test_book_membership_floor.py:190``,
        ``tests/test_book_finalise_gutter.py:1511``), both setting a book
        row's column, and failing on them would be a red that cannot be
        discriminated without guessing.

        The edge of that bound is the second half here: as soon as the
        attribute name *is* readable, how the target was computed stops
        mattering and the call fails. So the bound is exactly one corner wide,
        not "computed targets are outside the guard".
        """
        names = _global_names_assigned_by("_init_engine")
        skipped, quiet = _private_global_sites_in(
            "def test_sets_a_row_column(panel, book_id, column):\n"
            "    setattr(panel.books.get_book(book_id), column, 1)\n",
            "test_not_exempt.py",
            names,
        )
        assert dict(skipped) == {} and quiet == [], (
            "the declared bound has moved: a computed target with a "
            "non-literal name is reported, which reds the two book-row sites "
            f"this tree already has: {dict(skipped)} / {quiet}"
        )
        sites, unanalysable = _private_global_sites_in(
            "import sys\n\n"
            "def test_via_sys_modules():\n"
            '    setattr(sys.modules["nonogram.db.session"], "engine", None)\n',
            "test_not_exempt.py",
            names,
        )
        assert dict(sites) == {}, (
            f"sys.modules[...] is not a name the guard resolves: {dict(sites)}"
        )
        assert len(unanalysable) == 1, (
            "a readable attribute name in `names` must fail however the target "
            f"was computed — that is the edge of the declared bound: {unanalysable}"
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
