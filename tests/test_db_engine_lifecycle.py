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
opened before the DROP were handed back out after it. What that cost the
board -- how many runs failed, in how many waves, and which of them were build
gates -- is a **measurement**, and it is on
:func:`nonogram.db.session.reset_engine` (CARD-259). The
signatures were ``relation "puzzles" does not exist`` and a ``UUID`` column
arriving as the float ``inf`` so that ``uuid.UUID(hex=inf)`` called
``.replace`` on it.

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

**CARD-254 shrank the AC-5 half of this file.** What used to live here was an
AST deny-default over the test tree -- nine helpers, ~180 lines of machinery and
eleven controls -- that claimed no test could reach ``session.py``'s engine
globals unseen. It caught zero real violations, and its own claim about its
reach is what gated the card. What is left is the part that had authority: a
derived check that ``reset_engine`` retires exactly what ``_init_engine``
builds, two checks that the seam is published and really called, and a per-file
**textual count** standing behind a declared convention. The convention, and an
explicit list of what the count does not enforce, is on
:func:`nonogram.db.session.reset_engine`;
:class:`TestEngineLifecycle_TheResetIsAPublishedSeam` lists the controls that
stand behind it and points there.
"""

from __future__ import annotations

import ast
import os
import re
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

    Measured, not hoped for: a fourth global added to
    :func:`~nonogram.db.session._init_engine` reds
    ``test_it_resets_exactly_the_globals_the_builder_creates`` with the message
    below (mutant R4). A shape this function cannot analyse biases it to red
    rather than to a pass: a missing function raises, a tuple or partial-tuple
    target is simply not collected into ``assigned``, and ``assert built`` in
    the caller catches a blind read.
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


#: Test files allowed to hand-set ``session.py``'s engine globals, with the
#: number of times the textual scan below counts each name in each one — an
#: equality over **counted sites**, not a floor and not a set of
#: ``(file, name)`` pairs (ADR-0039/R3).
#:
#: These are ``monkeypatch.setattr`` calls, reversible and function-scoped,
#: and they exist to make :func:`nonogram.db.session._init_engine` rebuild so
#: that *its* behaviour can be observed. That is a different question from
#: retiring the engine after a schema rebuild, which is what
#: :func:`nonogram.db.session.reset_engine` is for.
#:
#: Counts rather than a set of pairs, because a pair-set equality does not
#: notice a *tenth* site under a pair already listed (CARD-252, mutant R1). A
#: tenth site, a site under a new name and a site in a new file each red the
#: equality below. Control:
#: ``test_the_count_reds_on_a_new_file_a_new_name_and_a_tenth_site``.
#:
#: This dict is a declaration, not a derivation, and the equality is its
#: control: if the scan ever goes blind it reports ``{}``, which is not this
#: dict, so blindness is red rather than green.
_EXEMPT_HAND_SET_SITES = {
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


def _session_aliases_in(tree) -> set:
    """Every local name the parsed file ``tree`` binds to the session module.

    Both import spellings, because both bind a name:
    ``from nonogram.db import session as X`` and
    ``import nonogram.db.session as X``.

    Derived from the scanned file's own imports rather than held as a literal
    floor (ADR-0039/R2), which is why
    ``test_conftest_names_the_seam_at_its_call_site`` keeps working when
    ``conftest.py`` renames its alias. Its one consumer is that test; it makes
    no claim about anything else in the tree.
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


def _hand_set_spellings(name: str):
    """The two text shapes that count as hand-setting ``name``.

    A regex pair, built from the name rather than written out, so the three
    names come from :func:`_global_names_assigned_by` and nothing here has to
    be kept in step by hand (ADR-0039/R2):

    * ``setattr(… "name" …)`` — any ``setattr``-spelled call that carries the
      attribute name as a quoted literal, whatever its receiver and however
      its arguments are bound. The scan is **newline-insensitive**: the only
      character that stops it between the ``setattr(`` and the quoted name is
      a parenthesis, so a call a formatter wrapped across lines counts exactly
      as the same call written on one line does — which is the spelling a
      formatter actually produces. Control:
      :meth:`TestEngineLifecycle_TheResetIsAPublishedSeam.test_a_wrapped_call_is_counted_and_a_parenthesised_receiver_is_not`.
    * ``.name =`` — an attribute of that name on the left of a plain
      assignment, whatever the receiver is.

    The parenthesis exclusion is what keeps the first pattern from running
    past the end of its own call and matching a name belonging to the next
    one — measured as a match *position* by arm 2b of that control, because a
    count cannot see it: ``re.finditer`` is non-overlapping, so an
    over-reaching match swallows the next call whole and the total is the same
    either way. It is also why a ``setattr(`` whose *receiver argument* itself
    contains parentheses stays invisible, and it is the only thing that stops
    the scan: a ``setattr(`` left unclosed in prose or a comment reaches a
    quoted global name further down the file (arm 4). The convention text
    declares both halves.

    Word boundaries are the quotes and the leading dot, which is what keeps
    ``"create_engine"`` and ``._engine_url`` out of ``engine``'s count.
    """
    escaped = re.escape(name)
    return (
        re.compile(rf'setattr\([^()]*?["\']{escaped}["\']'),
        re.compile(rf"\.{escaped}\s*=(?!=)"),
    )


#: What either convention text writes where one of the global names would go,
#: so a text can show the attribute-assignment spelling without quoting a name.
_NAME_PLACEHOLDER = "<name>"


def _spelling_heads(name: str) -> tuple:
    """How each spelling in :func:`_hand_set_spellings` opens, read off the patterns.

    Each pattern's leading literal run -- everything before its first
    metacharacter or metasequence -- unescaped: the call spelling, and the
    dotted attribute with ``name`` where the pattern puts it. Derived, never
    quoted: change either pattern's head and the texts held to it red.
    """
    head = re.compile(r"(?:[^\\\[\](){}*+?|^$.]|\\[^0-9A-Za-z])*")
    return tuple(
        re.sub(r"\\(.)", r"\1", head.match(pattern.pattern).group())
        for pattern in _hand_set_spellings(name)
    )


def _hand_set_sites_in(source: str, filename: str, names) -> Counter:
    """``Counter`` of ``(filename, name)`` per text match of a hand-set spelling.

    A grep, deliberately — see
    :class:`TestEngineLifecycle_TheResetIsAPublishedSeam` for what that does
    and does not mean. It reads text, not syntax: it does not know what object
    is being set, it does not know whether the line executes, and a spelling
    that does not put one of ``names`` next to a ``setattr(`` or a ``.name =``
    in the file's text is invisible to it. "Next to" is newline-insensitive and
    parenthesis-sensitive — see :func:`_hand_set_spellings` for exactly what
    that means and which spelling it therefore still misses.
    """
    sites = Counter()
    for name in names:
        for pattern in _hand_set_spellings(name):
            for _ in pattern.finditer(source):
                sites[(filename, name)] += 1
    return sites


def _hand_set_sites(names) -> Counter:
    """:func:`_hand_set_sites_in`, summed over every file under ``tests/``."""
    sites = Counter()
    for path in sorted((REPO / "tests").rglob("*.py")):
        sites.update(
            _hand_set_sites_in(path.read_text(encoding="utf-8"), path.name, names)
        )
    return sites


#: Where this file looks for a text that restates CARD-252's record: every
#: ``*.py`` file under these two roots, enumerated from disk. Not a list of
#: files -- a list is what three cards running found short by one -- and not a
#: grep either: each file is parsed, and only module, class and function
#: docstrings count, so a mention in running code or in a comment is out of
#: scope by construction. Declared reach: a docstring outside these two roots
#: is invisible to it; measured at **zero** such docstrings in this repository
#: on 2026-10-22 (CARD-259).
_CARD_252_AUTHORITY_ROOTS = (REPO / "src" / "nonogram", REPO / "tests")

#: What marks a docstring as speaking about CARD-252's record: the record's own
#: card id, as a whole token. The *set* of texts is derived (ADR-0039/R2); this
#: predicate is not, and that is its declared bound -- a docstring that
#: restates the record without ever naming the card is outside the derivation's
#: reach, and that residue is not measured here.
_CARD_252_SIGNATURE = re.compile(r"(?<![A-Za-z0-9_])CARD-252(?![0-9])")

#: One whole-word match, left and right. Used for the globals and for the
#: pointer.
_WORD_BOUNDED = r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])"


def _card_252_record_texts(roots=None):
    """Every docstring under ``roots`` that names the record's card as a whole word.

    The authority is the file system plus :mod:`ast`, which the runtime can
    enumerate; the alternative was a tuple of texts written by hand, and the
    reason it is gone is on :func:`nonogram.db.session.reset_engine`. Returns a
    tuple of ``(label, path, qualname, doc)``, where ``label`` is
    ``path:lineno qualname`` -- the string every arm interpolates, so that a
    failure names the text it failed on even in a run with no instrument.

    Deny by default (ADR-0039/R2): a root that is not a directory, and a file
    that does not parse, raise :class:`AssertionError` here rather than
    shrinking the set quietly. A file this cannot analyse is a failure, never a
    silent pass.
    """
    found = []
    for root in roots if roots is not None else _CARD_252_AUTHORITY_ROOTS:
        assert Path(root).is_dir(), (
            f"{root} is not a directory, so this guard's authority is empty "
            "and it would pass by finding nothing (ADR-0039/R2)"
        )
        for path in sorted(Path(root).rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                raise AssertionError(
                    f"{path} does not parse ({exc}), so this guard cannot say "
                    "whether it restates the record. A shape the derivation "
                    "cannot analyse is a FAILURE, never a silent pass "
                    "(ADR-0039/R2)."
                ) from exc
            for node in ast.walk(tree):
                if not isinstance(
                    node,
                    (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    continue
                doc = ast.get_docstring(node, clean=False)
                if doc is None or not _CARD_252_SIGNATURE.search(doc):
                    continue
                qualname = getattr(node, "name", "<module>")
                lineno = getattr(node, "lineno", 1)
                found.append((f"{path}:{lineno} {qualname}", path, qualname, doc))
    return tuple(found)


def _is_the_keeper(entry, pointer) -> bool:
    """Is this derived text the one docstring allowed to state the record?

    Read off the function object -- its name, and the file this module already
    reads its AST from -- rather than off a path spelling a reader could get
    subtly wrong. The keeper is :func:`nonogram.db.session.reset_engine`.
    """
    _label, path, qualname, _doc = entry
    return path == SESSION_SOURCE and qualname == pointer.__name__


def _names_shown_in(text: str, names) -> set:
    """Which of ``names`` ``text`` holds as a whole word."""
    return {
        name
        for name in names
        if re.search(_WORD_BOUNDED.format(re.escape(name)), text)
    }


def _head_shown_in(head: str, text: str) -> bool:
    """Does ``text`` show this spelling head, without an identifier extending it?

    The right boundary is applied only when the head *ends* in an identifier
    character, which is derived from the head rather than decided per head:
    ``.SessionLocal`` gets one, so ``.SessionLocalFactory`` no longer satisfies
    it, and ``setattr(`` gets none, because ``(`` cannot continue an
    identifier.
    """
    pattern = re.escape(head)
    if head[-1].isalnum() or head[-1] == "_":
        pattern += r"(?![A-Za-z0-9_])"
    return re.search(pattern, text) is not None


def _texts_not_pointing_at_the_keeper(derived, pointer) -> tuple:
    """The labels of derived texts that are neither the keeper nor a pointer to it.

    The deny-default arm's whole content: a docstring that names the record's
    card and does not carry :func:`nonogram.db.session.reset_engine`'s dotted
    path, word-bounded on both sides, is returned here and the caller fails on
    it. Empty means every text in the derived set is accounted for.
    """
    target = f"{pointer.__module__}.{pointer.__name__}"
    bounded = _WORD_BOUNDED.format(re.escape(target))
    return tuple(
        entry[0]
        for entry in derived
        if not _is_the_keeper(entry, pointer) and not re.search(bounded, entry[3])
    )


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
    on CARD-252, whose record is kept on
    :func:`nonogram.db.session.reset_engine`. Treat the sentence above as a
    pointer, not as coverage.

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

    The decision is recorded as a ``STRUCTURE:`` note on CARD-252, and *why* it
    went that way -- who calls the seam, and what the call does and does not
    pin -- is written once on :func:`nonogram.db.session.reset_engine`
    (CARD-259). What this docstring keeps is the decision's *input*: the
    alternative was to assign ``None`` to ``engine``, ``SessionLocal`` and
    ``_engine_url`` from inside ``conftest.py``, the same four lines, bought at
    the price of a module that stays silent -- and silent is how it got here.
    That sentence is the only place this docstring names all three globals, and
    :meth:`test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters`
    holds this docstring to naming each of them as a whole word.

    The convention behind the backstop below -- and the bound on what that
    backstop enforces, whose blind-to list is this guard's declared limit --
    is on :func:`nonogram.db.session.reset_engine`; this class and
    ``conftest.py``'s step 3 at the call site point there.
    Both used to, "in the same words", which was a claim with
    nothing to red when the copies drifted;
    :meth:`test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters`
    is what replaces that rule -- over every text a derivation finds off the
    disk, rather than over a list of texts, because three cards running found
    that list short by exactly one (CARD-259).

    Controls
    --------
    1. :meth:`test_it_resets_exactly_the_globals_the_builder_creates` -- the
       only *derived* authority here, and the one check that protects the
       product change: ``reset_engine``'s global set equals ``_init_engine``'s,
       read from ``session.py``'s own AST, so a fourth global added to the
       builder tomorrow is inside the check that day.
    2. :meth:`test_reset_engine_is_public_and_says_who_calls_it`,
       :meth:`test_conftest_names_the_seam_at_its_call_site` -- the seam: a
       public, documented function that names its caller, and a real AST
       **call** in ``conftest.py``, not a mention of its name in prose.
    3. :meth:`test_no_test_file_outside_the_exemption_sets_those_globals` --
       the backstop: per file under ``tests/``, how many times each of the
       three global names appears next to a ``setattr(`` or in a ``.<name> =``
       assignment (:func:`_hand_set_sites_in`), held to an equality against
       :data:`_EXEMPT_HAND_SET_SITES`;
       :meth:`test_the_count_reds_on_a_new_file_a_new_name_and_a_tenth_site`
       is what shows it reds on a new file, a new name, a tenth site.
    4. :meth:`test_a_wrapped_call_is_counted_and_a_parenthesised_receiver_is_not`
       -- the *shape* of call that count sees, where three sentences of the
       declared bound stop being prose: the wrapped call it counts, the
       parenthesised receiver it does not, the unclosed ``setattr(`` in prose
       it over-reads.
    5. :meth:`test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters`
       -- what replaced "the same words in two places", and, since CARD-259,
       the hand-written list of which texts those were.
    6. :class:`TestCard259_TheDerivedSetOfTextsDeniesByDefault` -- the control
       for the derivation above: a planted text, shown failing and then not.

    Measured over the whole tree, not reasoned: of the ``setattr(``
    occurrences under ``tests/``, twelve have a quoted global name downstream,
    nine of those are the counted sites, the other three are stopped by their
    own ``)`` -- arm 2b's property holding in the real tree rather than in a
    probe. The over-reding costs zero false positives today: an accident of how
    the tree is written, not a property of the scan.

    Why this file is not itself an exemption, which is two things and not one:
    its probe strings are built from the derived names at runtime, so no probe
    writes a name out; and the only literal, quoted spellings of the three
    names in it are the keys of :data:`_EXEMPT_HAND_SET_SITES`, which sit
    above every ``setattr(`` occurrence, so no unclosed one in the prose below
    them can reach a name. Both halves are load-bearing, and the equality is
    what checks the result: an entry for this file would break the dict.
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

        A text search is the wrong instrument here, and CARD-252 proved it:
        narrowing ``_rebuild_public_schema``'s docstring for review finding
        F-004 put the literal ``reset_engine()`` into conftest's prose, so a
        substring check would have been satisfied with the call deleted.
        Mutant M1 (the call gone, the prose kept) is the control.

        Stated bound: the call has to be an attribute call whose receiver
        ``conftest.py`` itself binds to the session module, or spells as the
        module's dotted path (:func:`_session_aliases_in`,
        :data:`_SESSION_MODULE_PATHS`). If conftest ever imports the function
        directly and calls it bare, this test reds and has to be widened —
        deliberately, rather than quietly accepting any call to anything of
        that name. Nothing else about conftest's shape is read here, and
        CARD-252's record is kept on
        :func:`nonogram.db.session.reset_engine`.
        """
        tree = ast.parse(CONFTEST_SOURCE.read_text(encoding="utf-8"))
        receivers = _session_aliases_in(tree) | set(_SESSION_MODULE_PATHS)
        assert _session_aliases_in(tree), (
            "tests/conftest.py imports nonogram.db.session under no name this "
            "check can see, so it could not find a call through one either"
        )
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "reset_engine"
            and ast.unparse(node.func.value) in receivers
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

    def test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters(
        self,
    ) -> None:
        """AC-2/AC-5: the set of texts is derived off the disk and denies by default.

        The convention used to be written twice, "in the same words" -- a claim
        with no control: nothing red when the copies drifted, and the doubling
        was the rule. CARD-257 replaced the rule with the equality below.
        CARD-259 replaced the rule's **set**.

        **Why the set is derived and not a tuple.** It was a tuple written by
        hand, two entries long and then three. Three cards running found that
        tuple short by exactly one text: CARD-257's residue was one file over,
        and CARD-259's was one file over again -- this module's own docstring,
        which by then had drifted away from the keeper by a whole unit of
        measurement, one saying "four build gates" where the other said "four
        waves of build gates". A hand-list of four gets a fifth text, so there
        is no list. :func:`_card_252_record_texts` enumerates every ``*.py``
        under :data:`_CARD_252_AUTHORITY_ROOTS` off the disk, parses each one,
        and keeps every module, class and function docstring that names
        ``CARD-252`` as a whole word. A file it cannot parse it **fails** on:
        a shape the derivation cannot analyse is a failure, never a silent
        pass (ADR-0039/R2).

        **Deny by default (AC-5).** Of the texts it finds, exactly one may
        state the record -- :func:`nonogram.db.session.reset_engine`,
        identified by the function object, not by a path spelling. Every other
        one must carry that dotted path, word-bounded on both sides. A
        docstring that names CARD-252 and points nowhere is a FAILURE that
        names its own file, line and qualified name.
        :class:`TestCard259_TheDerivedSetOfTextsDeniesByDefault` plants such a
        text into a tree of its own and shows the failure happening, and then
        stopping when the plant is removed.

        **The parameters.** A text held here is held to the mechanism's own
        parameters -- the globals (:func:`_global_names_assigned_by`) and the
        two spellings the scan counts (:func:`_spelling_heads`), both read
        from the code. Deliberately **not** a string comparison of
        docstrings, which would be the same uncontrolled rule with a test
        attached. A text may
        hold the names in double backticks, which the scan does not count, and
        writes :data:`_NAME_PLACEHOLDER` where the attribute spelling would
        otherwise quote one.

        **Second declared bound, on the heads arm.** The heads come from
        ``sorted(names)[0]`` alone, so the arm asks no text to show a
        ``.<other name> =`` spelling; and the dotted head is matched with a
        right word boundary, so an identifier that merely *extends* it
        (``.SessionLocalFactory``) no longer satisfies it. ``setattr(`` needs
        no boundary: ``(`` cannot continue an identifier. Measured at HEAD:
        **zero** extending occurrences in any of the **three** texts the heads
        arm holds, and exactly **one** anywhere in the derived set -- the
        illustrative spelling in this sentence, in a text that enumerates no
        global and so is not held to this arm at all. That is the bound, not a
        clean sweep (CARD-259, closing the half of cycle-1 F-108 that was
        closable).

        **How a failure names itself without the instrument.** Each arm's
        message interpolates the failing text's own ``label`` -- its path, its
        line and its qualified name -- so a plain ``pytest``, which reports one
        first-failing assert and no per-arm matrix, still says *which* text
        failed. That is the property that carries the reading. The claim that
        used to stand here, that the ``conftest.py`` text "is read **first**",
        was refuted by execution in cycle 1 -- swapping the read order leaves
        this test passing at exit 0, and first-versus-last give byte-identical
        evidence -- and is deleted rather than reworded. The property that
        replaced it has a control that can fail:
        :meth:`test_each_arm_of_the_agreement_names_the_text_it_failed_on`
        reads this method's own AST and reds if an arm's message stops
        interpolating ``label``.

        Reds under **GLOBAL-ADD** (a fourth global in ``_init_engine``, which
        no text names), **DOC-NAME-DEL**[*name*@*text*] (one global dropped
        from one text as a whole word -- one mutant per name per text over the
        texts the names arm holds, which is three names over three texts
        today: the **six** cells on ``src/nonogram/db/session.py`` and on this
        file are held by
        ``tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces``,
        and the **three** on ``tests/conftest.py`` are held by no committed
        control and structurally cannot be -- the per-assertion instrument
        refuses an edit landing on that path by identity, because it carries
        the database guard, and widening that refusal is forbidden; those
        three are a card-time plain-``pytest`` reading recorded on CARD-259
        and asserted nowhere), **SPELL-HEAD-RENAME** / **ASSIGN-HEAD-RENAME**
        (a spelling's head changed, so no text describes the mechanism any
        more), and **POINTER-ROT** (both ``:func:`` references renamed to a
        function that does not exist) or **POINTER-DEL-WORD** (every
        whole-word ``reset_engine`` gone).

        The pointer is read off :func:`nonogram.db.session.reset_engine`'s own
        function object, not the bare name: the class docstring it reads also
        carries ``reset_engine`` inside a control's own method name, which is
        not a pointer and which on its own satisfies a bare substring test.
        Renaming that method is therefore not a lost pointer, and does not
        red. The match is word-bounded on both sides, so an identifier that
        merely *extends* the dotted path (``...reset_engine_pool``) no longer
        satisfies it -- a substring test it did satisfy, with no occurrence of
        that shape anywhere under ``src/`` or ``tests/`` to prove it mattered
        (CARD-257 L-3: a measured bound, closed here because closing it is a
        lookahead).
        """
        names = _global_names_assigned_by("_init_engine")
        assert names, "no module-level globals found in _init_engine (guard is blind)"
        heads = _spelling_heads(sorted(names)[0])
        pointer = app_session.reset_engine
        target = f"{pointer.__module__}.{pointer.__name__}"
        guard = type(self).__doc__ or ""

        derived = _card_252_record_texts()
        keepers = [entry for entry in derived if _is_the_keeper(entry, pointer)]
        # Flattened, because CPython dedents a docstring at compile time while
        # the AST keeps the literal's own indentation: the two are the same
        # prose and never the same bytes. What this holds is that the text read
        # off disk is the live docstring, so the arms below are reading the
        # object the convention actually ships.
        assert len(keepers) == 1 and _flattened(keepers[0][3]) == _flattened(
            pointer.__doc__ or ""
        ), (
            "the derivation did not find exactly one keeper whose text on disk "
            f"is {target}'s live docstring (found {[e[0] for e in keepers]}): "
            "its authority roots, or the file it reads, no longer reach the "
            "keeper, and every arm below would then be measuring the wrong "
            "texts or none at all (ADR-0039/R2: no silent pass)"
        )
        conftest_tree = ast.parse(CONFTEST_SOURCE.read_text(encoding="utf-8"))
        receivers = _session_aliases_in(conftest_tree) | set(_SESSION_MODULE_PATHS)
        callers = {
            node.name
            for node in ast.walk(conftest_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == pointer.__name__
                and ast.unparse(call.func.value) in receivers
                for call in ast.walk(node)
            )
        }
        assert callers, (
            f"no function in {CONFTEST_SOURCE} calls `{target}` through a "
            "receiver this check can see, so the text at that call site is "
            "held to nothing it says about the mechanism"
        )
        stated_in = {
            (SESSION_SOURCE, pointer.__name__),
            (REPO / "tests" / Path(__file__).name, type(self).__name__),
        } | {(CONFTEST_SOURCE, name) for name in callers}
        reached = {(path, qualname) for _label, path, qualname, _doc in derived}
        unreached = sorted(f"{path}::{qualname}" for path, qualname in stated_in - reached)
        assert not unreached, (
            "the derivation does not reach "
            + ", ".join(unreached)
            + f" -- a text `{target}`'s convention is stated in, so the two "
            "arms below would not see it at all"
        )
        texts = tuple(
            (label, doc)
            for label, path, qualname, doc in derived
            if (path, qualname) in stated_in
            or len(_names_shown_in(doc, names)) > 1
        )
        assert keepers[0][0] in {label for label, _doc in texts}, (
            "the keeper is not in the set held to the mechanism's parameters, "
            "so the two arms below would run over texts that do not include "
            "the one text that defines them -- or over nothing at all"
        )

        for label, text in texts:
            # The names are read from the text as it ships. Substituting the
            # placeholder first would put names[0] back into every text that
            # has one, which is a check that cannot fail for that name.
            #
            # Whole words, not substrings: ``engine`` sits inside
            # ``_init_engine`` and ``_engine_url``, which all these texts
            # mention, and inside ``reset_engine``, which the pointer assert
            # below forces into the guard text -- so a substring test for that
            # name could not fail on any of them. Word bounds are what make
            # each of the three names red on its own.
            assert _names_shown_in(text, names) == set(names), (
                f"{label} does not name every global _init_engine() creates "
                f"({sorted(names)}) as a whole word -- ``engine`` inside "
                "``reset_engine`` is not a mention of the global: a global the "
                "convention omits is one nobody knows not to hand-set"
            )
            shown = text.replace(_NAME_PLACEHOLDER, sorted(names)[0])
            assert {head for head in heads if _head_shown_in(head, shown)} == set(heads), (
                f"{label} does not show every spelling _hand_set_spellings "
                f"counts ({list(heads)}): either the scan changed without the "
                "text, or the text was reworded away from the scan"
            )

        assert re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(target)}(?![A-Za-z0-9_])", guard
        ), (
            f"this class's docstring no longer carries `{target}`, the "
            "convention's single source -- and the bare name is not the "
            "pointer: this docstring carries it inside a control's own method "
            "name too, which is what kept a substring test green. A pointer "
            "that rots is how the duplication came back last time"
        )

        unpointed = _texts_not_pointing_at_the_keeper(derived, pointer)
        assert not unpointed, (
            "a docstring names CARD-252 and is neither the keeper nor a "
            f"pointer to `{target}`, so CARD-252's record has a home nothing "
            "holds to the keeper (AC-5; ADR-0039/R2 denies by default):\n"
            + "\n".join(f"  {label}" for label in unpointed)
        )

    def test_each_arm_of_the_agreement_names_the_text_it_failed_on(self) -> None:
        """The property that carries the uninstrumented reading, given a control.

        Cycle 1 refuted the claim that the attribution came from reading one
        text first; it comes from the per-text ``label`` interpolated into
        every arm's message, which is what a plain ``pytest`` prints when it
        reports its one first-failing assert. A property credited with
        evidence needs a state that makes it red (ADR-0039/R1), so this reads
        the agreement's own AST: every ``assert`` inside its
        ``for label, text in texts`` loop must carry a message that
        interpolates ``label``. Delete the interpolation from either arm and
        this reds, naming the line. CARD-252's record is kept on
        :func:`nonogram.db.session.reset_engine`.
        """
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        agreement = (
            "test_every_text_that_names_card_252_points_here_"
            "and_agrees_on_the_parameters"
        )
        bodies = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == agreement
        ]
        assert len(bodies) == 1, f"{agreement} is not in this file exactly once"
        loops = [
            node
            for node in ast.walk(bodies[0])
            if isinstance(node, ast.For)
            and isinstance(node.target, ast.Tuple)
            and [getattr(e, "id", None) for e in node.target.elts] == ["label", "text"]
        ]
        assert len(loops) == 1, "the per-text loop is not there to read"
        arms = [node for node in ast.walk(loops[0]) if isinstance(node, ast.Assert)]
        assert len(arms) >= 2, f"only {len(arms)} arms inside the per-text loop"
        for arm in arms:
            interpolated = {
                getattr(value.value, "id", None)
                for value in ast.walk(arm.msg or ast.Constant(value=""))
                if isinstance(value, ast.FormattedValue)
            }
            assert "label" in interpolated, (
                f"the arm at :{arm.lineno} does not interpolate the text's own "
                "label into its message, so an uninstrumented run would report "
                "a failure without saying which text failed"
            )
    def test_no_test_file_outside_the_exemption_sets_those_globals(self) -> None:
        """The convention's backstop: a per-file textual count, held to an equality.

        Read the class docstring for what this does not enforce. In one line:
        it counts text, so it cannot say that a counted line sets one of
        ``session.py``'s globals, and it cannot see a hand-set written any
        other way.
        """
        names = _global_names_assigned_by("_init_engine")
        assert names, "no module-level globals found in _init_engine (guard is blind)"
        sites = _hand_set_sites(names)
        assert dict(sites) == _EXEMPT_HAND_SET_SITES, (
            "the per-file count of session.py's engine global names written "
            "next to a setattr( or as an attribute assignment has changed "
            "(counts are per text match, not per (file, name) pair).\n"
            f"  found:  {sorted(sites.items())}\n"
            f"  expect: {sorted(_EXEMPT_HAND_SET_SITES.items())}\n"
            "The convention, and the files it excepts, are on "
            "nonogram.db.session.reset_engine: tests call reset_engine(), and a "
            "site the exemption above does not already account for — including "
            "a second one in a file that has some — is a card, not a commit."
        )

    def test_the_count_reds_on_a_new_file_a_new_name_and_a_tenth_site(self) -> None:
        """Every direction the equality claims to catch, each fed as source text.

        Not mutants somebody has to remember to re-apply: each arm builds its
        hand-set line from a name derived from ``session.py``, which is also
        why this file contributes no counted site of its own.

        The claim under control is the equality's, and only the equality's:
        each arm produces a count the exemption does not account for, and
        asserts that count and nothing else. None asserts the equality's
        *reaction* to it: ``dict(...) == _EXEMPT_HAND_SET_SITES`` reacts to any
        difference by construction, so there is no mechanism there to delete
        and nothing for an arm to kill. Nor does any arm claim the scan sees
        every way a global can be set -- the convention text on
        :func:`nonogram.db.session.reset_engine` says the opposite, at length.

        Three arms, with the mutant that reds each (measured per assert, never
        off a single pytest result -- see the note on
        :meth:`test_a_wrapped_call_is_counted_and_a_parenthesised_receiver_is_not`):

        1. both spellings are counted at all, in a file no exemption lists --
           without which the rest would be vacuous, and it is also the *new
           file* direction, the probe file being no exemption's. Reds if either
           regex in :func:`_hand_set_spellings` is dropped;
        2. a new name -- the same, under a name no exemption entry covers; reds
           if the ``setattr(`` spelling stops being counted;
        3. a tenth site inside a pair the exemption already lists (CARD-252's
           cycle-1 mutant R1, which a pair-*set* equality did not notice) --
           reds if the counter is collapsed to one per ``(file, name)`` pair,
           which is the mechanism this arm exists for.
        """
        names = sorted(_global_names_assigned_by("_init_engine"))
        assert names, "no module-level globals found in _init_engine (guard is blind)"
        probe_file = "test_not_exempt.py"
        assert not any(
            key[0] == probe_file for key in _EXEMPT_HAND_SET_SITES
        ), f"{probe_file} has become a real exemption; pick another probe name"

        def setattr_spelling(name: str) -> str:
            # Built, never written out, so the literal name never appears in
            # this file's own text and the tree-wide count stays clean.
            return f'    monkeypatch.setattr(db_session, "{name}", None)\n'

        def assignment_spelling(name: str) -> str:
            return f"    db_session.{name} = None\n"

        # 1. both spellings are counted, in a file the exemption does not
        #    list -- the two halves of _hand_set_spellings, each load-bearing
        #    on its own, and the new-file direction with them.
        for spelling, label in (
            (setattr_spelling, "a quoted attribute name in a setattr( call"),
            (assignment_spelling, "an attribute assignment"),
        ):
            counted = _hand_set_sites_in(
                f"def test_spelling(monkeypatch):\n{spelling(names[0])}",
                probe_file,
                names,
            )
            assert dict(counted) == {(probe_file, names[0]): 1}, (
                f"{label} is not counted, so the equality cannot red on it: "
                f"{dict(counted)}"
            )

        # 2. a new name: a site under a name no exemption entry covers.
        # Derived so it cannot collide with a real global and turn this arm
        # into a false red the day session.py grows a fourth one.
        intruder = "_engine_probe"
        while intruder in names:
            intruder += "_"
        exempt_file = "test_db_url_driver.py"
        new_name = _hand_set_sites_in(
            f"def test_new_name(monkeypatch):\n{setattr_spelling(intruder)}",
            exempt_file,
            [*names, intruder],
        )
        assert dict(new_name) == {(exempt_file, intruder): 1}, (
            "a site under a name outside the exemption is not counted, so a "
            f"fourth global could be hand-set silently: {dict(new_name)}"
        )
        assert (exempt_file, intruder) not in _EXEMPT_HAND_SET_SITES

        # 3. a tenth site inside a pair the exemption already lists.
        listed = sorted(
            name for name in names if (exempt_file, name) in _EXEMPT_HAND_SET_SITES
        )
        assert listed, (
            f"{exempt_file} lists none of {names}, so this arm has nothing to "
            "add a tenth site to; fix the exemption or this control first."
        )
        tenth = listed[0]
        source = (REPO / "tests" / exempt_file).read_text(encoding="utf-8")
        before = _hand_set_sites_in(source, exempt_file, names)
        key = (exempt_file, tenth)
        assert before[key] == _EXEMPT_HAND_SET_SITES[key], (
            "this arm is measured against the real exempt file; its count "
            "there has changed, so fix the exemption first."
        )
        after = _hand_set_sites_in(
            source + f"\n\ndef test_r1_control(monkeypatch):\n{setattr_spelling(tenth)}",
            exempt_file,
            names,
        )
        assert after[key] == before[key] + 1, (
            "a tenth hand-set site inside an already-exempt (file, name) pair "
            "was not counted, so the exemption is a set of pairs again and the "
            f"comment on _EXEMPT_HAND_SET_SITES is false: {after[key]}"
        )

    def test_a_wrapped_call_is_counted_and_a_parenthesised_receiver_is_not(
        self,
    ) -> None:
        """What the scan sees of a ``setattr(`` call's *shape*, in both directions.

        The scan stops between a ``setattr(`` and the quoted name at a
        parenthesis and at nothing else — not at a newline. So a call a
        formatter wrapped across lines is counted, that being the spelling the
        line is actually written in; the remaining blind case, parentheses in
        the receiver argument, is declared instead of closed.

        One arm per claim the convention text makes about that shape, each
        named with the mutation that reds it. There are two: **NORM-DEL**,
        which puts ``\n`` back into :func:`_hand_set_spellings`' character
        class, and **PAREN-DEL**, which deletes the parenthesis exclusion
        (``[^()]*?`` → ``.*?`` under ``re.DOTALL``).

        Measure that **per assertion, never per test run**: every arm below is
        an ``assert`` in this one function, so pytest can only report that the
        function failed, and an arm after the first failing one is never
        evaluated at all.

        1. **arm 1** — a wrapped call is counted exactly as the one-line form
           is. NORM-DEL.
        2. **arm 2a** — a wrapped call carrying a name that is *not* one of the
           three globals manufactures no match, even with a global name quoted
           further down the probe. PAREN-DEL. Without it, widening the scan
           would be a false-positive engine over every file in ``tests/``: the
           equality is a count, so one spurious match reds the suite for
           everyone.
        3. **arm 2b** — of two wrapped calls in a row, only the second carrying
           a global name, the match *starts* at the second. PAREN-DEL (it
           starts at the first instead) and NORM-DEL (it does not match at
           all). Asserted as a **position**, because a count cannot see this
           property at all: ``re.finditer`` yields non-overlapping matches, so
           a first match that over-reaches swallows the second call whole and
           the total stays 1 either way.
        4. **arm 3, the declared blind case** — a receiver argument that itself
           contains parentheses is *not* counted. PAREN-DEL. It is the one item
           of the blind-to list on
           :func:`nonogram.db.session.reset_engine` with a control of its own,
           which is what makes that sentence measured rather than prose.
        5. **arm 4, the declared over-read** — a ``setattr(`` never closed, in
           a comment or in prose, *is* counted against a quoted global name
           further down the file. NORM-DEL. The false-positive surface the
           newline-insensitivity buys, wrong in the safe direction (a loud red,
           never a silent miss) and declared in the convention text; this arm
           keeps that declaration measured rather than composed from two other
           bullets.
        """
        names = sorted(_global_names_assigned_by("_init_engine"))
        assert names, "no module-level globals found in _init_engine (guard is blind)"
        probe_file = "test_not_exempt.py"
        assert not any(
            key[0] == probe_file for key in _EXEMPT_HAND_SET_SITES
        ), f"{probe_file} has become a real exemption; pick another probe name"
        name = names[0]

        # The name is interpolated, never written out, so this file still
        # contributes no counted site of its own -- which the equality in
        # test_no_test_file_outside_the_exemption_sets_those_globals checks.
        wrapped = _hand_set_sites_in(
            "def test_wrapped(monkeypatch):\n"
            "    monkeypatch.setattr(\n"
            f'        db_session, "{name}", None\n'
            "    )\n",
            probe_file,
            names,
        )
        assert dict(wrapped) == {(probe_file, name): 1}, (
            "a setattr( call wrapped across lines -- what any formatter "
            "produces once the line passes the column limit -- is not "
            "counted, so the backstop is blind to the most likely spelling of "
            f"the thing it exists to red (mutant M3c): {dict(wrapped)}"
        )

        # 2a. an unrelated attribute name, wrapped, with a global name quoted
        #     further down the file: no match may be manufactured.
        unrelated = _hand_set_sites_in(
            "def test_unrelated(monkeypatch):\n"
            "    monkeypatch.setattr(\n"
            '        db_session, "pool_pre_ping", True\n'
            "    )\n"
            f'    assert probe == "{name}"\n',
            probe_file,
            names,
        )
        assert dict(unrelated) == {}, (
            "widening the scan past newlines made it match a global name "
            "against an unrelated setattr( call, which would red the equality "
            f"for every future file in tests/: {dict(unrelated)}"
        )

        # 2b. two wrapped calls in a row, only the second carrying the name:
        #     the match has to START at the second one -- a POSITION, because
        #     re.finditer is non-overlapping and the count is 1 either way.
        two_calls_source = (
            "def test_two_calls(monkeypatch):\n"
            "    monkeypatch.setattr(\n"
            '        db_session, "pool_pre_ping", True\n'
            "    )\n"
            "    monkeypatch.setattr(\n"
            f'        db_session, "{name}", None\n'
            "    )\n"
        )
        setattr_pattern = _hand_set_spellings(name)[0]
        match = setattr_pattern.search(two_calls_source)
        second_call = two_calls_source.rindex("setattr(")
        # The probe needs two calls for the position below to discriminate:
        # rindex finds the LAST one, so on a one-call probe the assertion
        # would be trivially green. Asserted, as this file's other probe
        # preconditions are, rather than read off the probe above.
        assert two_calls_source.count("setattr(") == 2, (
            "this arm's probe no longer spells two calls, so its position "
            "assertion cannot discriminate: rindex() would be finding the "
            "only call there is"
        )
        assert match is not None and match.start() == second_call, (
            "the scan ran past one setattr( call's closing parenthesis into "
            "the next call's arguments: the match starts at "
            f"{None if match is None else match.start()}, not at the second "
            f"setattr( at {second_call}"
        )

        # 3. the declared blind case: parentheses inside the receiver argument.
        receiver_parens = _hand_set_sites_in(
            "def test_receiver_parens():\n"
            '    setattr(sys.modules.get("nonogram.db.session"), '
            f'"{name}", None)\n',
            probe_file,
            names,
        )
        assert dict(receiver_parens) == {}, (
            "a setattr( whose receiver argument contains parentheses is now "
            "counted, which is more than the convention text claims; widen "
            "that text or narrow this control: "
            f"{dict(receiver_parens)}"
        )

        # 4. the declared over-read: an unclosed setattr( in a comment reaches
        #    a quoted global name on a later line, because [^()]*? stops only
        #    at a parenthesis and prose routinely has none. Wrong in the safe
        #    direction, and measured rather than composed from two other
        #    bullets.
        prose = _hand_set_sites_in(
            "def test_prose():\n"
            "    # a hand-set is written setattr(\n"
            f'    assert probe == "{name}"\n',
            probe_file,
            names,
        )
        assert dict(prose) == {(probe_file, name): 1}, (
            "an unclosed setattr( in prose no longer reaches a quoted global "
            "name further down the file. That is a narrower scan than the "
            "convention text declares: narrow that text, and drop the "
            "warning that prose in tests/ quoting a setattr( "
            f"spelling has to keep a parenthesis before any global name: {dict(prose)}"
        )


#: One retired clause of CARD-252's record per row, with the statement that
#: carries it today. The record used to stand in three texts; CARD-257 retired
#: one copy and CARD-259 retired the rest, and G-2 on CARD-259 says no clause
#: may be retired without a **named** surviving statement. A count is not a
#: name, so this is the names.
#:
#: Each row is ``(retired_from, clause, home, surviving_phrase, kind)``:
#:
#: * ``retired_from`` -- which retired text the clause comes from, and
#:   ``-reworded`` where that text is also the clause's home today;
#: * ``clause`` -- the clause as the retired text wrote it, verbatim;
#: * ``home`` -- ``<repo-relative path>::<qualname>`` of the docstring that
#:   carries it now (``<module>`` for a module docstring);
#: * ``surviving_phrase`` -- a phrase of that home, verbatim at HEAD, that
#:   carries the clause. Compared with whitespace flattened, because both
#:   texts are line-wrapped prose and a line-wrap is not a drift;
#: * ``kind`` -- ``figure`` for a measurement, ``bound`` for a declared limit,
#:   ``narration`` for the rest. A ``figure`` or a ``bound`` must additionally
#:   appear in **exactly one** text of the derived set: those are the clauses
#:   whose doubling is what this card exists to retire.
#:
#: How to recompute the ``clause`` column rather than trusting it:
#: ``git diff -U0 <merge-base>..HEAD -- tests/conftest.py
#: tests/test_db_engine_lifecycle.py``, take the removed docstring lines,
#: join them, split at sentence boundaries and then at ``;``
#: and at em-dash-introduced independent clauses. That split is what produced
#: these rows, and it is stated here because CARD-259's cycle 1 shipped a
#: count (44) whose script was never committed and could not be reproduced --
#: so that figure is **withdrawn** and replaced by this table, whose method is
#: written down and whose check is :meth:`TestCard259_TheDerivedSetOfTextsDeniesByDefault.test_every_retired_clause_has_a_named_surviving_statement`.
_CARD_252_CLAUSE_SURVIVAL = (
    (
        "conftest",
        "Deliberate, but not load-bearing",
        "src/nonogram/db/session.py::reset_engine",
        "That position is deliberate but **not** load-bearing",
        "bound",
    ),
    (
        "conftest",
        "the earlier reading of G-3 here was wrong",
        "src/nonogram/db/session.py::reset_engine",
        "An earlier reading of that guardrail, written at the call site in ``conftest.py``, had it backwards",
        "bound",
    ),
    (
        "conftest",
        "``reset_engine()`` builds nothing, so putting it before step 2 cannot point a fresh engine at a half-built schema",
        "src/nonogram/db/session.py::reset_engine",
        "this function builds nothing, so calling it before the migration cannot leave",
        "bound",
    ),
    (
        "conftest",
        "Measured",
        "src/nonogram/db/session.py::reset_engine",
        "Measured, not reasoned",
        "narration",
    ),
    (
        "conftest",
        "moved ahead of the Alembic subprocess, ``tests/test_db_engine_lifecycle.py`` stays green",
        "src/nonogram/db/session.py::reset_engine",
        "moving the call ahead of the Alembic subprocess leaves ``tests/test_db_engine_lifecycle.py`` fully green",
        "figure",
    ),
    (
        "conftest",
        "(CARD-252's own refutation, re-measured as cycle-1 review mutant R7)",
        "src/nonogram/db/session.py::reset_engine",
        "re-measured as CARD-257's cycle-1 review mutant R7",
        "figure",
    ),
    (
        "conftest",
        "The half-built-schema hazard belongs to the card's original sketch, which rebuilt eagerly.",
        "src/nonogram/db/session.py::reset_engine",
        "The half-built-schema hazard belongs to that card's original sketch, which rebuilt the engine eagerly",
        "bound",
    ),
    (
        "conftest",
        "Step 3 is the fix CARD-252 exists for.",
        "src/nonogram/db/session.py::reset_engine",
        "CARD-252. The one caller is ``tests/conftest.py``'s",
        "narration",
    ),
    (
        "conftest",
        "``session.py`` keeps a module-global engine and rebuilds it only when ``DATABASE_URL`` changes, so a process that had already built one for this URL kept it, pool and all, across the ``DROP SCHEMA`` above",
        "src/nonogram/db/session.py::reset_engine",
        "cache keeps whatever engine the process had already built for that URL, pool and all",
        "narration",
    ),
    (
        "conftest",
        "leaving a connection older than the schema in the pool, ready to be handed back out.",
        "src/nonogram/db/session.py::reset_engine",
        "ready to be handed back out",
        "narration",
    ),
    (
        "conftest",
        "``tests/test_db_engine_lifecycle.py`` pins that this function leaves no such engine behind.",
        "src/nonogram/db/session.py::reset_engine",
        "AC-1 forces exactly that connection to exist and goes red",
        "bound",
    ),
    (
        "conftest",
        "It does **not** pin that such a connection corrupts a query.",
        "src/nonogram/db/session.py::reset_engine",
        "**Not** pinned: that such a survivor corrupts anything",
        "bound",
    ),
    (
        "conftest",
        "Four consecutive build gates on this board reported failures that reproduced on no second run, and they are the motive for the card",
        "src/nonogram/db/session.py::reset_engine",
        "one failing run in each of four consecutive waves -- 45, 46, 47 and 48",
        "figure",
    ),
    (
        "conftest",
        "the deterministic reproduction was attempted and CARD-252's AC-3 was **withdrawn** for being unforceable on psycopg2, so those gate failures stay unexplained.",
        "src/nonogram/db/session.py::reset_engine",
        "**withdrew** that acceptance criterion (AC-3)",
        "bound",
    ),
    (
        "conftest",
        "The test module's docstring says exactly what the control does and does not demonstrate",
        "src/nonogram/db/session.py::reset_engine",
        "module docstring before concluding this function fixed them",
        "narration",
    ),
    (
        "conftest-reworded",
        "read it before concluding this call fixed them.",
        "tests/conftest.py::_rebuild_public_schema",
        "before concluding this call fixed anything",
        "narration",
    ),
    (
        "guard-reworded",
        "The decision (recorded as a ``STRUCTURE:`` note on CARD-252): the fixture calls :func:`nonogram.db.session.reset_engine`.",
        "tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam",
        "The decision is recorded as a ``STRUCTURE:`` note on CARD-252",
        "narration",
    ),
    (
        "guard-reworded",
        "The alternative -- the card's own sketch, assigning ``None`` to ``engine``, ``SessionLocal`` and ``_engine_url`` from inside ``conftest.py``",
        "tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam",
        "the alternative was to assign ``None`` to ``engine``, ``SessionLocal`` and ``_engine_url`` from inside ``conftest.py``",
        "bound",
    ),
    (
        "guard-reworded",
        "is the same four lines, but it leaves ``session.py`` silent about the fact that something retires its engine, and silent is how the module got here.",
        "tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam",
        "the same four lines, bought at the price of a module that stays silent",
        "narration",
    ),
    (
        "guard-reworded",
        "That sentence is the only place this docstring names all three globals.",
        "tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam",
        "That sentence is the only place this docstring names all three globals",
        "bound",
    ),
    (
        "guard-reworded",
        'It used to, "in the same words", which was a claim with nothing to red when the two copies drifted.',
        "tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam",
        'Both used to, "in the same words", which was a claim with nothing to red when the copies drifted',
        "narration",
    ),
    (
        "module",
        'Four consecutive build gates on this board reported failures that reproduced on no second run, including ``relation "puzzles" does not exist`` and a ``UUID`` column arriving as the float ``inf`` so that ``uuid.UUID(hex=inf)`` called ``.replace`` on it.',
        "src/nonogram/db/session.py::reset_engine",
        "one failing run in each of four consecutive waves -- 45, 46, 47 and 48",
        "figure",
    ),

)


def _flattened(text: str) -> str:
    """``text`` with every run of whitespace collapsed to one space."""
    return " ".join(text.split())


def _docstring_at(home: str) -> str:
    """The docstring named by ``<repo-relative path>::<qualname>``, read off disk.

    ``<module>`` names a module docstring. A home that does not exist raises
    rather than returning an empty string, so a row pointing at a statement
    that is gone reds instead of passing on an empty haystack.
    """
    rel, qualname = home.split("::")
    path = REPO / rel
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        if getattr(node, "name", "<module>") != qualname:
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc is not None:
            return doc
    raise AssertionError(f"{home} names no docstring that exists")


class TestCard259_TheDerivedSetOfTextsDeniesByDefault:
    """AC-5: the set the guard holds is derived, and an unaccounted text FAILS.

    The guard is
    :meth:`TestEngineLifecycle_TheResetIsAPublishedSeam.test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters`;
    its authority is :data:`_CARD_252_AUTHORITY_ROOTS` plus :mod:`ast`, and the
    record it guards is kept on :func:`nonogram.db.session.reset_engine`. What
    this class adds is the thing a derivation most easily lacks: evidence that
    it can **fail**. Each test below plants a text into a tree of its own --
    never into this repository -- and shows the failure in both states, present
    and removed, because a plant that does not red is exactly the defect AC-5
    exists to prevent.
    """

    @staticmethod
    def _plant(root: Path, name: str, docstring: str) -> Path:
        path = root / name
        path.write_text(f'"""{docstring}"""\n', encoding="utf-8")
        return path

    def test_a_planted_text_that_names_the_record_and_points_nowhere_is_named(
        self, tmp_path
    ) -> None:
        """Planted: a FAILURE naming the plant. Removed: nothing to report.

        The two states of the control, measured in the same test so neither can
        be reported without the other.
        """
        pointer = app_session.reset_engine
        target = f"{pointer.__module__}.{pointer.__name__}"

        planted = self._plant(
            tmp_path,
            "fifth_text.py",
            "A fifth text. CARD-252's record restated once more, with no "
            "pointer anywhere in it.",
        )
        derived = _card_252_record_texts(roots=(tmp_path,))
        assert [entry[0] for entry in derived] == [f"{planted}:1 <module>"], derived
        unpointed = _texts_not_pointing_at_the_keeper(derived, pointer)
        assert unpointed == (f"{planted}:1 <module>",), unpointed
        assert str(planted) in unpointed[0] and ":1" in unpointed[0], (
            "the failure must name the file and the line of the text it found, "
            "or an uninstrumented run cannot act on it"
        )

        planted.write_text(
            f'"""A fifth text. CARD-252\'s record is kept on '
            f'``{target}``; this text points there."""\n',
            encoding="utf-8",
        )
        derived = _card_252_record_texts(roots=(tmp_path,))
        assert len(derived) == 1, derived
        assert _texts_not_pointing_at_the_keeper(derived, pointer) == (), (
            "the same text, now carrying the pointer, must stop being a "
            "failure -- otherwise the arm reds on everything and measures "
            "nothing"
        )

    def test_a_text_that_extends_the_pointer_does_not_satisfy_it(
        self, tmp_path
    ) -> None:
        """The pointer is word-bounded on both sides, here and in the guard.

        CARD-257's L-3: an identifier that merely *extends* the dotted path
        satisfies a substring test without being a pointer. Planted, because
        the shape does not occur in this repository -- which is a bound, not a
        reason to leave the arm unbounded.
        """
        pointer = app_session.reset_engine
        target = f"{pointer.__module__}.{pointer.__name__}"
        planted = self._plant(
            tmp_path,
            "extending.py",
            f"CARD-252, pointed at ``{target}_pool``, which is not this "
            "function and does not exist.",
        )
        derived = _card_252_record_texts(roots=(tmp_path,))
        assert _texts_not_pointing_at_the_keeper(derived, pointer) == (
            f"{planted}:1 <module>",
        ), "an identifier extending the dotted path was taken for the pointer"

    def test_a_planted_partial_enumeration_fails_the_names_arm(
        self, tmp_path
    ) -> None:
        """More than one global named is an enumeration, and must name them all.

        The names arm's trigger is derived from the globals themselves, not
        chosen per text: a text naming two of three is a partial enumeration
        and fails; the same text naming all three passes.
        """
        names = sorted(_global_names_assigned_by("_init_engine"))
        assert len(names) > 2, names

        partial = ", ".join(f"``{name}``" for name in names[:-1])
        assert len(_names_shown_in(partial, names)) > 1, partial
        assert _names_shown_in(partial, names) != set(names), (
            "a text naming all but one global must not satisfy the names arm"
        )

        whole = ", ".join(f"``{name}``" for name in names)
        assert _names_shown_in(whole, names) == set(names), whole

        lone = f"``{names[0]}``"
        assert len(_names_shown_in(lone, names)) == 1, (
            "the declared bound: one name is prose, not an enumeration"
        )

    def test_a_file_the_derivation_cannot_analyse_is_a_failure(
        self, tmp_path
    ) -> None:
        """ADR-0039/R2's second half: no silent pass on a shape it cannot read.

        An unparseable file and a missing root are the two ways this
        derivation can go blind, and both raise here rather than returning a
        shorter set.
        """
        (tmp_path / "broken.py").write_text("def (:\n", encoding="utf-8")
        try:
            _card_252_record_texts(roots=(tmp_path,))
        except AssertionError as exc:
            assert "broken.py" in str(exc) and "does not parse" in str(exc), exc
        else:
            raise AssertionError(
                "an unparseable file passed silently, which is the whole shape "
                "ADR-0039/R2 forbids"
            )

        (tmp_path / "broken.py").unlink()
        assert _card_252_record_texts(roots=(tmp_path,)) == ()

        missing = tmp_path / "not-a-directory"
        try:
            _card_252_record_texts(roots=(missing,))
        except AssertionError as exc:
            assert "not a directory" in str(exc), exc
        else:
            raise AssertionError("a missing authority root passed silently")

    def test_every_retired_clause_has_a_named_surviving_statement(self) -> None:
        """G-2, with names: every row of :data:`_CARD_252_CLAUSE_SURVIVAL` holds.

        Each clause's surviving phrase must be present, verbatim up to
        whitespace, in the docstring the row names. Every ``figure`` and every
        ``bound`` row must additionally occur in **exactly one** text of the
        derived set, which is what single-sourcing a measurement means here --
        and it is the row that caught cycle 1's drift: the retired phrase
        "Four consecutive build gates on this board" was absent from the named
        keeper and present verbatim in a text the card did not name at all.
        The record itself is on :func:`nonogram.db.session.reset_engine`.
        """
        rows = _CARD_252_CLAUSE_SURVIVAL
        assert len(rows) >= 22, (
            f"the survival table has shrunk to {len(rows)} rows; a clause "
            "removed from it is a clause nothing claims a home for"
        )
        derived = [_flattened(entry[3]) for entry in _card_252_record_texts()]
        for retired_from, clause, home, phrase, kind in rows:
            assert kind in ("figure", "bound", "narration"), kind
            flat = _flattened(phrase)
            assert flat in _flattened(_docstring_at(home)), (
                f"the clause {clause[:60]!r}... retired from the {retired_from} "
                f"text is claimed to survive at {home}, and the phrase "
                f"{phrase!r} is not there"
            )
            if kind in ("figure", "bound"):
                hits = [text for text in derived if flat in text]
                assert len(hits) == 1, (
                    f"{kind} {phrase!r} stands in {len(hits)} texts of the "
                    "derived set; a measurement or a bound is stated once, and "
                    "two copies of it are what this card retired"
                )

    def test_an_identifier_extending_a_spelling_head_does_not_satisfy_it(self) -> None:
        """The heads arm's right boundary, with the plant that makes it measured.

        The mechanism is in :func:`_head_shown_in`, and a deletion mutant on it
        reds nothing in this repository: no text holds the extending shape, so
        the lookahead buys a bound rather than a kill. That is precisely why it
        needs a planted control -- a mechanism nothing can fail on is the shape
        this card exists to retire. The boundary is derived from the head, not
        chosen per head, so both directions are checked here.
        """
        names = sorted(_global_names_assigned_by("_init_engine"))
        heads = _spelling_heads(names[0])
        dotted = next(head for head in heads if head.startswith("."))
        call = next(head for head in heads if head.endswith("("))

        assert _head_shown_in(dotted, f"a text writing ``{dotted}`` = None")
        assert not _head_shown_in(dotted, f"a text writing ``{dotted}Factory``"), (
            "an identifier extending the dotted spelling head satisfied the "
            "heads arm, which is the substring hazard the boundary closes"
        )
        assert _head_shown_in(call, f"a text writing ``{call}obj, name, None)``"), (
            "the call head must NOT carry a right boundary: `(` cannot "
            "continue an identifier, and a boundary there would stop the arm "
            "matching every real spelling of the call"
        )
