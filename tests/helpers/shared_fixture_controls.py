"""One home for the controls a module-scoped shared render needs (CARD-219).

CARD-218 shared one drawn book per test module and had to prove three things
about each shared fixture: that no consumer drew on it, that the book was
drawn once, and that nothing was left holding a page bitmap afterwards. Those
proofs need nine small readers of pytest's own collection data, and CARD-218
had to write all nine **twice** -- once in ``tests/test_book_puzzle_frame.py``
and once in ``tests/test_book_pdf_band.py`` -- because its scope fence put
``tests/conftest.py`` out of reach. Eight of the nine were byte-identical in
code; the ninth differed only in the remedy its assertion message prescribed,
so one condition had two answers depending on which file you read. Nothing
asserted the copies agreed.

This module is the one home, and :mod:`tests.test_shared_fixture_controls` is
the guard that the copies cannot come back: it refuses any consumer module
that redefines a name this module exports.

It lives under ``tests/helpers/`` rather than in ``tests/conftest.py`` on
purpose. Both ``tests/conftest.py`` and ``tests/helpers/book_corpus.py`` are
declared ``conflict.hotspots`` in ``meta/kanban/config.yml``; ``tests/helpers``
is already an importable package; and every function here is a plain
module-level helper rather than a fixture, so none of them needs conftest's
injection.

**Two holes CARD-218 left open are closed here**, and both are stated as what
the instrument can and cannot see rather than as a universal:

*Hole 1 -- the consumer denominator.* :func:`declared_consumers` used to read
only a test function's own signature at module top level. Six shapes of
consumer were therefore absent from the denominator a default-deny guard
divides by, and ADR-0039/R2 does not tolerate a false negative in that
direction. All six are closed: a test that reaches the fixture through
*another* fixture, a test **inherited** from a base class, a test in a
**nested** ``Test`` class, a fixture requested by ``@pytest.mark.usefixtures``
or ``pytestmark``, a fixture declared ``autouse=True`` (CARD-219 cycle 1,
F-002: the shape made **every** collected test in its scope a consumer and the
denominator emptied, so the refusal never fired), and a test whose name
pytest's ``python_functions`` collects but a hard-coded ``test_`` prefix does
not -- ``def testCamelCase(self, shared)`` (same finding; the prefix is read
from ``config.getini`` now, which is the enumerable authority ADR-0039/R2
asks for).

The shapes that remain invisible are named in :func:`declared_consumers`'s own
docstring, each with the reason it cannot be read and what stands in for it.

*Hole 2 -- the retention walk.* :func:`bitmap_bytes` could not see a page's
pixels as a numpy array, and the old walk entered a module-level container
exactly one level deep. A page behind an ``@lru_cache``, on a ``Test`` class
attribute, or nested two containers down was therefore retained invisibly.
:func:`retained_bitmap_bytes` walks those with :func:`gc.get_referents` --
stdlib, so ADR-0006/R1's dependency baseline is untouched -- and reports the
``@lru_cache`` stores **separately** from everything else, because a widening
and an exemption are the same edit. See that function for why the split is a
measured allowance and not a threshold, and :func:`_step` for the exact set of
places the walk enters and the places it declines to -- the walk is a
**bounded** reading of a module's own data, never a universal one (CARD-219
cycle 1, F-001: three further hiding places held 75,735,000 B invisibly while
the docstrings here claimed "anywhere").

Nothing in this file imports production code, and nothing in production
imports it.
"""

from __future__ import annotations

import ast
import fnmatch
import functools
import gc
import hashlib
import inspect
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

__all__ = [
    "DEFAULT_CLASS_PATTERNS",
    "DEFAULT_FUNCTION_PATTERNS",
    "Retention",
    "bitmap_bytes",
    "case_of",
    "consumers_among",
    "declared_consumers",
    "declares",
    "fixtures_taken_dynamically",
    "lru_cache_names",
    "page_digest",
    "refuse_unless_every_consumer_is_collected",
    "refuse_unless_nothing_is_taken_dynamically",
    "refuse_unless_nothing_takes_it_later",
    "retained_bitmap_bytes",
]


# --------------------------------------------------------------------------
# A page's identity, cheaply
# --------------------------------------------------------------------------


def page_digest(page: Any) -> bytes:
    """A 32-byte witness for exactly which pixels a page carries.

    A control on a shared render compares pages for *equality*, so a sha256 of
    the page's bytes discriminates exactly as well as the 25,245,000 bytes
    themselves -- and that is not a micro-optimisation here. pytest keeps a
    test module in ``sys.modules`` for the rest of the session, so an
    accumulator a module-scoped fixture filled outlives the fixture: holding
    the bytes held 8 page bitmaps alive in one of CARD-218's files and 10 in
    the other, to the end of every run that collected them (CARD-218 cycle 1,
    F-001). 32 B says the same thing.

    ``hashlib`` is stdlib, so ADR-0006/R1's dependency baseline is untouched.
    """
    return hashlib.sha256(page.tobytes()).digest()


# --------------------------------------------------------------------------
# Hole 1: who consumes a fixture, read off the module and off the collection
# --------------------------------------------------------------------------


#: pytest's own ini defaults for ``python_functions`` / ``python_classes``,
#: used **only** when a caller has no ``config`` to read them off. Every guard
#: in this module that runs inside pytest passes
#: ``request.config.getini(...)`` instead (ADR-0039/R2: the authority is the
#: config, not a prefix written out here), and
#: ``TestSharedControls_TheCollectedNameRulesComeFromTheConfig`` fails if this
#: tree ever configures either option away from these values, which is the one
#: way a fallback written here could go quietly stale.
DEFAULT_FUNCTION_PATTERNS = ("test",)
DEFAULT_CLASS_PATTERNS = ("Test",)


def _matches_any(name: str, patterns: Iterable[str]) -> bool:
    """pytest's own ``python_functions`` / ``python_classes`` name matching.

    pytest tries each configured pattern as a **prefix** first and, only when
    the pattern looks like a glob, as an :mod:`fnmatch` pattern -- both arms
    and that condition are
    ``_pytest.python.Class._matches_prefix_or_glob_option`` (pytest 9.1.1,
    ``python.py:385``), copied rather than approximated so this reading's
    answer is pytest's.

    So the default ``test`` collects ``test_x`` *and* ``testCamelCase``, and a
    configured ``check_*`` collects by glob. The prefix arm is where CARD-219
    cycle 1's F-002 landed: a hard-coded ``test_`` misses
    ``def testCamelCase(self, shared)``, which pytest collects, so that
    consumer was in no denominator.

    **The glob-character condition is dead weight here and is recorded as
    such rather than claimed.** pytest guards the ``fnmatch`` call because
    ``fnmatch`` is expensive to call for every name in every module, not
    because the two answers differ, and on POSIX ``os.path.normcase`` is the
    identity -- so ``fnmatch(name, pattern)`` on a glob-free pattern is exact
    equality, which the prefix arm already covers. Measured: deleting the
    condition kills nothing (CARD-219 fix round, B3c survived), and the
    control written to kill it could not fail and was deleted with it.
    Deleting either *arm* does kill: B3a reds the glob row, B3b reds 12 cells.
    """
    return any(
        name.startswith(pattern)
        or (
            any(character in pattern for character in "*?[")
            and fnmatch.fnmatch(name, pattern)
        )
        for pattern in patterns
    )


def case_of(item: object) -> str:
    """``Class::function`` for a collected item, parametrised cases collapsed.

    One name per test *function*, so a set read off collected items compares
    with a set read off the module's own definitions: ``test_x[a]`` and
    ``test_x[b]`` are one consumer, because one function asks for the fixture.

    The owner is the item's **immediate** class, which is also how
    :func:`declared_consumers` spells a nested class's tests -- pytest reports
    ``item.cls`` as the innermost class, not the chain.
    """
    name = getattr(item, "originalname", None) or item.name
    owner = getattr(item, "cls", None)
    return f"{owner.__name__}::{name}" if owner is not None else name


def declares(member: object, fixture: str) -> bool:
    """Does this test function take ``fixture`` as an argument?"""
    function = getattr(member, "__func__", member)
    if not callable(function):
        return False
    try:
        return fixture in inspect.signature(function).parameters
    except (TypeError, ValueError):  # not a Python callable
        return False


def _underlying(member: object) -> object:
    """The plain function behind a bound method or a fixture definition object.

    pytest 9 wraps a fixture in a ``FixtureFunctionDefinition`` and keeps the
    function on ``_fixture_function``; earlier versions returned the function
    itself with a marker attribute on it. Both are unwrapped here so the rest
    of this module reads one shape.
    """
    member = getattr(member, "_fixture_function", member)
    return getattr(member, "__func__", member)


def _parameters(member: object) -> frozenset[str]:
    """Every argument name this callable takes; empty if it is not introspectable."""
    function = _underlying(member)
    if not callable(function):
        return frozenset()
    try:
        return frozenset(inspect.signature(function).parameters)
    except (TypeError, ValueError):
        return frozenset()


def _fixture_marker(value: object) -> object | None:
    """pytest's own "this is a fixture" marker, whichever name it goes under.

    ``_fixture_function_marker`` since pytest 9, ``_pytestfixturefunction``
    before it. Read as a pair rather than pinned to one, because the only
    failure mode that matters is silent: a renamed marker would empty
    :func:`_fixture_graph` and with it the transitive half of the denominator,
    and an emptier denominator is a *passing* guard. ``test_the_fixture_graph``
    tests in :mod:`tests.test_shared_fixture_controls` are the control for
    exactly that, and they fail rather than thin out.
    """
    for attribute in ("_fixture_function_marker", "_pytestfixturefunction"):
        marker = getattr(value, attribute, None)
        if marker is not None:
            return marker
    return None


def _marked_fixtures(*owners: object) -> frozenset[str]:
    """Fixture names requested by ``usefixtures`` marks on any of ``owners``.

    ``owners`` is read in the order given and the results are unioned, so a
    test function, its class and its module's ``pytestmark`` all contribute --
    which is exactly how pytest itself assembles them. A mark object is read
    structurally (``.name``/``.args``) rather than by importing pytest's mark
    classes, so this helper stays free of any pytest version's internals.
    """
    found: set[str] = set()
    for owner in owners:
        if owner is None:
            continue
        marks = getattr(owner, "pytestmark", None)
        if isinstance(owner, Mapping):
            marks = owner.get("pytestmark")
        if marks is None:
            continue
        if not isinstance(marks, (list, tuple)):
            marks = [marks]
        for mark in marks:
            if getattr(mark, "name", None) != "usefixtures":
                continue
            found.update(str(arg) for arg in getattr(mark, "args", ()) or ())
    return frozenset(found)


def _fixture_graph(namespace: Mapping[str, object]) -> dict[str, frozenset[str]]:
    """Each fixture this namespace defines, against the fixtures it asks for.

    A fixture is recognised by the marker ``pytest.fixture`` leaves behind
    (:func:`_fixture_marker`) -- pytest's own, so the set is derived from an
    authority the runtime can enumerate rather than hand-written (ADR-0039/R2).
    Its edges are its own argument names, plus any ``usefixtures`` mark it
    carries.
    """
    graph: dict[str, frozenset[str]] = {}
    for name, value in namespace.items():
        if name.startswith("__"):
            continue
        marker = _fixture_marker(value)
        if marker is None:
            continue
        declared_name = getattr(marker, "name", None) or name
        graph[declared_name] = _parameters(value) | _marked_fixtures(
            _underlying(value)
        )
    return graph


def _autouse_fixtures(namespace: Mapping[str, object]) -> frozenset[str]:
    """The fixtures this namespace declares ``autouse=True``.

    Read off the same marker :func:`_fixture_marker` already returns -- pytest
    records the flag on it as ``.autouse`` -- so this is the config's own
    authority rather than a convention about names (ADR-0039/R2).

    An autouse fixture is requested by **every test in its scope** without any
    test naming it, which is why it was CARD-219 cycle 1's F-002: with
    ``@pytest.fixture(autouse=True) def _always(shared)`` in a module,
    pytest's own ``request.fixturenames`` listed ``shared`` for every test
    while :func:`declared_consumers` returned ``[]``. An empty denominator
    makes :func:`refuse_unless_every_consumer_is_collected` *pass*, which is
    the one direction ADR-0039/R2 does not tolerate.
    """
    found: set[str] = set()
    for name, value in namespace.items():
        if name.startswith("__"):
            continue
        marker = _fixture_marker(value)
        if marker is None:
            continue
        if getattr(marker, "autouse", False):
            found.add(getattr(marker, "name", None) or name)
    return frozenset(found)


def _implying_fixtures(fixture: str, graph: Mapping[str, frozenset[str]]) -> frozenset[str]:
    """Every fixture name whose use pulls ``fixture`` in, ``fixture`` included.

    The transitive closure pytest computes when it builds an item's fixture
    closure, computed here over the module's **own** fixture definitions. A
    chain that passes through a fixture defined in a ``conftest.py`` or in a
    plugin is therefore **not** closed here: those definitions are not in the
    namespace this is handed. That bound costs nothing on the collected side
    (``item.fixturenames`` is pytest's own full closure and does see them) and
    it can only make this set *smaller*, which is the direction that under-
    counts a denominator -- so :func:`refuse_unless_every_consumer_is_collected`
    states it and :mod:`tests.test_shared_fixture_controls` holds it to a
    control that fails when the chain is local.
    """
    implying = {fixture}
    frontier = [fixture]
    while frontier:
        target = frontier.pop()
        for name, needs in graph.items():
            if name in implying or target not in needs:
                continue
            implying.add(name)
            frontier.append(name)
    return frozenset(implying)


def _test_members(
    owner: type,
    enclosing: tuple[type, ...] = (),
    *,
    function_patterns: Iterable[str] = DEFAULT_FUNCTION_PATTERNS,
    class_patterns: Iterable[str] = DEFAULT_CLASS_PATTERNS,
) -> Iterator[tuple[str, str, object, tuple[type, ...]]]:
    """``(class name, attribute, member, owner chain)`` for every test it collects.

    Walks the MRO rather than ``vars(owner)``, so a test method **inherited**
    from a base class counts as the subclass's own -- which is how pytest
    collects it, and one of hole 1's shapes. Nested classes whose names
    ``class_patterns`` collects are recursed into and reported under their
    **own** name, matching :func:`case_of`'s reading of ``item.cls``.

    A member counts as a test when ``function_patterns`` matches its name the
    way pytest matches ``python_functions`` (:func:`_matches_any`). The
    patterns are the caller's, read off ``config.getini`` where there is a
    config to read: a hard-coded ``test_`` missed ``testCamelCase``, which
    pytest collects (CARD-219 cycle 1, F-002).

    The owner chain is outermost class first and the immediate owner last. It
    is what lets a caller resolve a *class*-level fixture the way pytest does:
    the innermost definition of a name wins over an enclosing one and over the
    module's.
    """
    chain = (*enclosing, owner)
    function_patterns = tuple(function_patterns)
    class_patterns = tuple(class_patterns)
    seen: set[str] = set()
    for klass in owner.__mro__:
        if klass is object:
            continue
        for attr, member in vars(klass).items():
            if attr in seen:
                continue
            seen.add(attr)
            if attr.startswith("__"):
                continue
            if isinstance(member, type) and _matches_any(attr, class_patterns):
                yield from _test_members(
                    member,
                    chain,
                    function_patterns=function_patterns,
                    class_patterns=class_patterns,
                )
            elif _matches_any(attr, function_patterns):
                yield owner.__name__, attr, member, chain


def declared_consumers(
    namespace: Mapping[str, object],
    fixture: str,
    *,
    function_patterns: Iterable[str] = DEFAULT_FUNCTION_PATTERNS,
    class_patterns: Iterable[str] = DEFAULT_CLASS_PATTERNS,
) -> set[str]:
    """Every test in this module that asks for ``fixture``, read off the module.

    The controls' denominator, **derived rather than written down**: a consumer
    added or taken away moves it without anyone having to remember a number.

    A test counts as a consumer when it asks for ``fixture`` itself or for any
    fixture that pulls ``fixture`` in (:func:`_implying_fixtures`), by argument
    name, by a ``usefixtures`` mark on the function, on its class or on the
    module, or because an ``autouse`` fixture in its scope pulls it in
    (:func:`_autouse_fixtures`). Which names are tests and which are test
    classes is ``function_patterns``/``class_patterns``, i.e.
    ``config.getini("python_functions")``/``("python_classes")`` where the
    caller has a config -- :func:`refuse_unless_every_consumer_is_collected`
    always does.

    CARD-218's version read a top-level test function's own signature and
    nothing else; the six shapes that reading missed -- transitive, inherited,
    nested, marked, ``autouse``, and a name the configured prefix collects but
    ``test_`` does not -- are each held to a failing **pair** of controls in
    :mod:`tests.test_shared_fixture_controls` (found now, missed by that
    reading).

    **What this reading still cannot see.** Each entry is a bound, not a
    silent gap, and it is here rather than in prose somewhere else because the
    one way a default-deny guard fails is by dividing by a set that is too
    small:

    1. ``request.getfixturevalue(...)`` -- the fixture's name is an expression
       evaluated at run time, so no static reading can have it. Invisible to
       the collected half too, and held to zero instead by
       :func:`refuse_unless_nothing_is_taken_dynamically`, which has its own
       failing control.
    2. A transitive chain whose middle link is defined **outside**
       ``namespace`` -- a ``conftest.py`` or plugin fixture. Those definitions
       are not in the mapping this is handed. The collected half does see them
       (``item.fixturenames`` is pytest's own full closure).
    3. An ``autouse`` fixture defined outside ``namespace``, i.e. in a
       ``conftest.py`` or a plugin. pytest resolves such a fixture's own
       arguments against the *requesting* item, so a ``conftest.py`` autouse
       fixture taking ``pages`` would make every test in every module a
       consumer and this reading would not know. Measured 2026-10-24:
       ``tests/conftest.py`` declares **no** autouse fixture, and the four
       modules in this tree that do (``test_admin_serving.py``,
       ``test_admin_auth.py``, ``test_card_037_upload_retry.py``,
       ``test_card_044_preview_after_submit.py``) declare theirs locally,
       where :func:`_autouse_fixtures` does see them.
    4. A consumer bound into ``namespace`` by something other than a ``def``,
       a ``class`` or an assignment the module executed -- e.g. a test
       function injected with ``globals()[name] = ...`` at import time. It is
       in the namespace by the time this runs if the injection ran first, and
       is missed only if it runs later.
    """
    function_patterns = tuple(function_patterns)
    class_patterns = tuple(class_patterns)
    module_graph = _fixture_graph(namespace)
    module_marks = _marked_fixtures(namespace)
    module_autouse = _autouse_fixtures(namespace)
    at_module = _implying_fixtures(fixture, module_graph)
    found: set[str] = set()
    for name, value in namespace.items():
        if isinstance(value, type) and _matches_any(name, class_patterns):
            for owner_name, attr, member, chain in _test_members(
                value,
                function_patterns=function_patterns,
                class_patterns=class_patterns,
            ):
                # pytest resolves a fixture name innermost-first, so a class's
                # own definition shadows an enclosing class's and the module's.
                # The graph is layered the same way round, which is what keeps
                # one class's `helper(pages)` from making another class's
                # unrelated `helper()` look like a consumer.
                graph = dict(module_graph)
                autouse = set(module_autouse)
                for klass in chain:
                    for ancestor in reversed(klass.__mro__):
                        graph.update(_fixture_graph(vars(ancestor)))
                        autouse |= _autouse_fixtures(vars(ancestor))
                implying = _implying_fixtures(fixture, graph)
                asked = _parameters(member) | module_marks | autouse
                for klass in chain:
                    asked |= _marked_fixtures(klass)
                asked |= _marked_fixtures(member)
                if asked & implying:
                    found.add(f"{owner_name}::{attr}")
        elif _matches_any(name, function_patterns):
            asked = (
                _parameters(value)
                | _marked_fixtures(value)
                | module_marks
                | module_autouse
            )
            if asked & at_module:
                found.add(name)
    return found


def consumers_among(items: Iterable[object], fixture: str, module: str) -> set[str]:
    """The consumers of ``fixture`` *from* ``module`` among collected items."""
    return {
        case_of(item)
        for item in items
        if getattr(getattr(item, "function", None), "__module__", None) == module
        and fixture in getattr(item, "fixturenames", ())
    }


def _module_of(request: Any) -> str:
    """The dotted name of the module the requesting test lives in."""
    return request.module.__name__


def refuse_unless_every_consumer_is_collected(
    request: Any, namespace: Mapping[str, object], fixture: str
) -> None:
    """Default-deny (ADR-0039/R2) on a denominator this control cannot see.

    A render-count control reads a counter that only the tests pytest actually
    runs increment, so a selection narrower than the module narrows the
    denominator with it: with one consumer selected, *one render* and *one
    render per test* are the same observation, and the control passes whatever
    the fixture's scope is. That is CARD-218 cycle 1's F-002, measured on a
    real file: with the module fixture mutated to class scope, the whole file
    reds, and the control class alone, the control node id alone and
    ``-k one_render`` all returned a silent green.

    So the control refuses to answer instead of answering wrongly. The cost is
    stated rather than hidden: selecting one of these controls on its own reds,
    with a message saying what it could not evaluate and how to. The whole-file
    runs the gates use are unaffected.

    ``namespace`` must be the requesting module's own ``globals()``. That is
    asserted rather than trusted: a denominator read off one module and
    compared with items from another is not a weaker check, it is a different
    question, and it would red every whole-file run or pass every narrow one
    depending on which way round the mistake went.
    """
    module = _module_of(request)
    assert namespace.get("__name__") == module, (
        f"this control was handed {namespace.get('__name__')!r}'s namespace "
        f"while running in {module!r}: the denominator would be read off one "
        "module and the collected consumers off another. Pass this module's "
        "own `globals()`."
    )
    declared = declared_consumers(
        namespace,
        fixture,
        # The names pytest itself collects by, from pytest itself. A prefix
        # written out in this module would be the hand-written set
        # ADR-0039/R2 refuses, and `test_` -- the one CARD-218 wrote -- really
        # does miss a name the default `test` collects (cycle 1, F-002).
        function_patterns=request.config.getini("python_functions"),
        class_patterns=request.config.getini("python_classes"),
    )
    collected = consumers_among(request.session.items, fixture, module)
    absent = sorted(declared - collected)
    assert not absent, (
        f"this control cannot evaluate its own denominator: {len(collected)} "
        f"of this module's {len(declared)} {fixture!r} consumers were "
        f"collected by this selection, so one render and one render per test "
        f"are the same observation here. Not collected: {absent}. Select at "
        "least every consumer listed — the whole file always does, and for a "
        "class-scoped render its own class does — because a narrower run "
        "cannot see the fixture's scope, and passing would be the vacuous "
        "green ADR-0039/R2 forbids."
    )


def refuse_unless_nothing_takes_it_later(
    request: Any, fixture: str, *, siblings_excepted: bool
) -> None:
    """A control on a shared render must be the last thing that takes it.

    CARD-218's read-only controls said in prose that they run last "because
    pytest collects a module in file order", and nothing asserted it -- cycle
    1's F-006. This asserts it off the collected order of *this* run rather
    than off the premise: a consumer collected after the control is a test the
    control cannot speak for, because it had not yet had its chance to draw on
    the shared page.

    ``siblings_excepted`` drops this control's own class from the question. The
    other tests in a control class are controls too -- they digest and measure,
    and a reader cannot mutate -- so a sibling collected after the control is
    not a gap. A control on a *class*-scoped render passes ``False``: there the
    consumers are the classmates.

    The remedy in the message is **one** remedy. CARD-218's two copies
    prescribed two different ones for the same condition ("move it below them"
    in one file, "move its class to the end of the file" in the other), which
    is the drift this module exists to make impossible: the condition is that a
    consumer is collected later, and the fix is to put this control's class
    after every test that takes the fixture.
    """
    module = _module_of(request)
    items = list(request.session.items)
    try:
        mine = items.index(request.node)
    except ValueError:  # the node is always in the session
        mine = len(items)
    later = sorted(
        {
            case_of(item)
            for item in items[mine + 1 :]
            if getattr(getattr(item, "function", None), "__module__", None) == module
            and fixture in getattr(item, "fixturenames", ())
            and not (siblings_excepted and getattr(item, "cls", None) is request.cls)
        }
    )
    assert not later, (
        f"this control reads the shared render before {len(later)} test(s) "
        f"that also take {fixture!r}, so it cannot speak for them: {later}. "
        "A control on a shared render goes after everything that takes it: "
        "move this control's class below every test that takes the fixture, "
        "or run the file in its own order rather than naming node ids in "
        "another one."
    )


def fixtures_taken_dynamically(source: str) -> list[int]:
    """The lines of ``source`` that reach for a fixture at run time.

    Every ``…getfixturevalue`` attribute access, by line number, found by
    parsing rather than by grepping -- so the word in a docstring (this one
    included, in the module that calls it) is not a hit.
    """
    return sorted(
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute) and node.attr == "getfixturevalue"
    )


def refuse_unless_nothing_is_taken_dynamically(path: str | Path) -> None:
    """The one consumer shape **both** halves of the guard are blind to, held to zero.

    :func:`declared_consumers` reads a module's definitions and
    :func:`consumers_among` reads ``item.fixturenames``; a test that takes a
    shared render with ``request.getfixturevalue("pages")`` appears in neither,
    so it is in no denominator and in no later-consumer set. CARD-218 cycle 2
    measured the consequence with one mutation drawn two ways: a late class
    putting a 9 px line on a shared page is **caught** (2 failure cells) when
    it takes the fixture as a parameter and **missed** (40 passed, 0 cells)
    when it takes it that way.

    The idiom is live in this tree -- 9 sites, one of them
    ``tests/test_puzzle_solver_page.py:671``, ``return
    request.getfixturevalue("page")``, the same fixture name as one of
    CARD-218's class-scoped renders -- so this is not hypothetical. It is a
    **declared bound with its own failing control** (ADR-0039/R3) rather than a
    silent gap: a module that calls this asserts it uses the idiom zero times,
    and anyone who adds one reds here immediately. No static reading can do
    better, because the name of the fixture is an expression evaluated at run
    time.
    """
    taken = fixtures_taken_dynamically(Path(path).read_text(encoding="utf-8"))
    assert not taken, (
        f"{len(taken)} test(s) in {Path(path).name} take a fixture at run "
        f"time, at line(s) {taken}: a consumer taken that way is invisible to "
        "both halves of the selection guard — to `declared_consumers`, which "
        "reads this module's definitions, and to `consumers_among`, which "
        "reads `item.fixturenames` — so a control on a shared render would "
        "pass without covering it (CARD-218 cycle 2 F-002, measured: 2 cells "
        "when declared, 0 when taken this way). Take the fixture as a "
        "parameter."
    )


# --------------------------------------------------------------------------
# Hole 2: what a module is still holding when its fixtures are finalised
# --------------------------------------------------------------------------


def bitmap_bytes(value: object) -> int:
    """The page-bitmap bytes ``value`` is holding; 0 if it holds none.

    An image is measured from its geometry rather than through ``tobytes()``,
    so asking the question allocates nothing. A numpy array is measured through
    its own ``nbytes``, which is hole 2's first half: a page's pixels as
    ``np.asarray(page)`` read **0** here before CARD-219 while that array's
    ``nbytes`` is 25,245,000, and a numpy page array is exactly the working
    form of the band file's own scan. It is recognised by duck-typing
    (``nbytes`` plus ``dtype``) so this module needs no numpy import of its
    own.
    """
    if isinstance(value, memoryview):
        return value.nbytes
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    nbytes = getattr(value, "nbytes", None)
    if isinstance(nbytes, int) and hasattr(value, "dtype"):
        return nbytes
    width = getattr(value, "width", None)
    height = getattr(value, "height", None)
    bands = getattr(value, "getbands", None)
    if isinstance(width, int) and isinstance(height, int) and callable(bands):
        return width * height * len(bands())
    return 0


@dataclass(frozen=True)
class Retention:
    """What a module will still be holding once its fixtures are finalised.

    Attributes:
        by_name: Per module-level name, the page-bitmap bytes reachable from
            it along the edges :func:`_step` enters, **without** entering a
            module-level ``@lru_cache`` store. This is the half a control holds
            to an equality. It is the module's own accumulators and what they
            reach *through those edges* -- a bounded reading, not "anything
            they reach": :func:`_step` names both the edges it follows and the
            ones it declines to follow, and a page parked behind a declined
            edge is not in this figure.
        by_cache: Per ``@lru_cache``-decorated module-level name, the bytes
            inside its store. Reported separately because it is an
            **exemption**, and an exemption is a claim of its own -- see
            :func:`retained_bitmap_bytes`. A cache the walk *meets* without
            ``namespace`` naming it is not covered by the exemption and its
            contents land in :attr:`by_name`.
    """

    by_name: dict[str, int]
    by_cache: dict[str, int]

    @property
    def total(self) -> int:
        """Everything the walk found, exempt and non-exempt alike."""
        return sum(self.by_name.values()) + sum(self.by_cache.values())


#: **The fence.** These are never entered, and that is what keeps the walk
#: inside the module's own data: ``gc.get_referents`` on a function hands back
#: its ``__globals__``, and a module object *is* another module's globals, so
#: following either would walk the whole interpreter and measure every page
#: anything in the process holds.
#: ``test_the_walk_does_not_leave_the_module_s_own_data`` is the control that
#: it does not, and it fails if any of these becomes an edge.
_OPAQUE = (
    types.ModuleType,
    types.FunctionType,
    types.MethodType,
    types.BuiltinFunctionType,
    types.BuiltinMethodType,
)

#: Types the walk measures but never steps into. **Eight of the nine are a
#: cheap short-circuit. ``memoryview`` is a mechanism, and the comment that
#: stood here said otherwise about all nine.**
#:
#: Measured 2026-10-24 (cycle 2, F-201): ``gc.get_referents`` returns ``[]``
#: for the other eight, so skipping those changes no figure and only keeps the
#: frontier short. For a memoryview it returns ``[<managedbuffer object>]``,
#: and the collector reaches the **same pixels again** through it. Removing
#: ``memoryview`` from this tuple therefore **doubles** a memoryview-held page:
#: 25,245,000 -> 50,490,000 B on a real page, 21,000 -> 42,000 B on this
#: module's stand-in. Its control is
#: ``test_a_memoryview_held_page_is_counted_once_not_twice``.
#:
#: It is deliberately **not** a ``HOLE_TWO_CHANNELS`` row, and the reason is
#: that table's second assertion: CARD-218's walk already measured a memoryview
#: (its ``_flat_bytes`` has a memoryview arm -- verified 2026-10-24 at
#: 21,000 B, not 0), so this is not a channel that was invisible before. It is
#: a **double count this tuple prevents**, which is a different claim and needs
#: a different control.
_SCALAR = (str, bytes, bytearray, memoryview, int, float, complex, bool, type(None))


def _step(
    value: object, *, enter_caches: bool, exempt: frozenset[int], home: str | None
) -> list[object]:
    """The objects the walk continues into from ``value``.

    **This function is the whole of what the retention walk can see**, so it
    is written as an enumeration of edges rather than described as a universal
    anywhere else (CARD-219 cycle 1, F-001: three hiding places held
    75,735,000 B while two docstrings said "anywhere" and "however deeply
    nested").

    The authority on what an object refers to is :func:`gc.get_referents` --
    the collector's own view, stdlib, ADR-0006/R1 untouched -- and this
    function is **three edits to it**, nothing more. That shape is deliberate:
    CARD-219's first version had a list of container types *and* a generic
    container arm *and* an instance-``vars()`` arm, and each made the others
    unnecessary, so deleting any one of them survived (the M11/M11b shape this
    card had already paid for once; cycle 1's C6b/C8 found it again). One
    mechanism per edge, so one mutant kills it:

    1. **the fence** -- :data:`_OPAQUE` is not entered at all. A function's
       referents include its ``__globals__`` and a module *is* a namespace, so
       without this the walk would leave the module it was asked about and
       measure everything the process holds;
    2. **the exemption** -- an ``@lru_cache`` wrapper is entered on the
       ``by_cache`` pass, and on the ``by_name`` pass only when ``namespace``
       does **not** name it, because an unnamed cache is nobody's declared
       allowance (cycle 1: a cache bound inside a list held a whole page
       bitmap and measured 0 B);
    3. **classes** -- a class's own attributes are read with ``vars()``,
       dunders excluded, and only when ``python_classes`` would collect its
       name or the module being walked (``home``) is where it was defined.
       Entering every class would follow ``__mro__`` out into every base an
       imported class has.

    Everything else -- a mapping, a list, a tuple, a set, a
    :class:`collections.deque`, any other container, an instance's own
    attributes, an instance with ``__slots__`` and no ``__dict__`` at all --
    is one ``gc.get_referents`` call, which is also why no container type is
    named anywhere in this function. The collector is asked rather than the
    object iterated, so a container with a side-effecting ``__iter__`` is
    never run.

    **And what it declines**, each of which can therefore hide a page bitmap
    from :func:`retained_bitmap_bytes`. This list is the reason nothing here
    says "anywhere":

    * a class attribute of an **imported** class whose name no pattern
      collects (edit 3);
    * anything reachable only through a function, a method or a module
      (edit 1, deliberately -- see :data:`_OPAQUE`);
    * a numpy array's contents: the uncropped **base** of a view, and the
      elements of an object-dtype array. Not a choice but a measured limit --
      ``gc.get_referents`` returns ``[]`` for both (2026-10-24), so the
      collector offers this walk no edge to follow. The figure that costs is
      measured too: the 666 boolean masks
      ``tests/test_book_pdf_band.py``'s ``_set_once`` caches measure
      24,435,107 B as views, while the 666 distinct bases they keep alive hold
      110,882,067 B, and only the first number is in
      :attr:`Retention.by_cache`;
    * anything held by a C extension that exposes it to neither the collector
      nor ``vars()``.
    """
    if isinstance(value, _OPAQUE):
        return []
    if isinstance(value, _SCALAR):
        return []
    if isinstance(value, functools._lru_cache_wrapper):
        if enter_caches or id(value) not in exempt:
            return gc.get_referents(value)
        return []
    if isinstance(value, type):
        if _matches_any(value.__name__, DEFAULT_CLASS_PATTERNS) or (
            home is not None and getattr(value, "__module__", None) == home
        ):
            return [
                member
                for attr, member in vars(value).items()
                if not attr.startswith("__")
            ]
        return []
    return gc.get_referents(value)


def _reachable_bytes(
    root: object,
    *,
    enter_caches: bool,
    exempt: frozenset[int] = frozenset(),
    home: str | None = None,
) -> int:
    """Page-bitmap bytes reachable from ``root``, each object counted once.

    Termination is the ``seen`` set of object ids. How far the walk can get is
    :func:`_step`, which lists both the edges it follows and the ones it does
    not; the fence that keeps it out of the rest of the process is
    :data:`_OPAQUE`.
    """
    seen: set[int] = set()
    total = 0
    frontier = [root]
    while frontier:
        value = frontier.pop()
        key = id(value)
        if key in seen:
            continue
        seen.add(key)
        total += bitmap_bytes(value)
        frontier.extend(
            _step(value, enter_caches=enter_caches, exempt=exempt, home=home)
        )
    return total


def _caches_of(namespace: Mapping[str, object]) -> dict[str, functools._lru_cache_wrapper]:
    """The module-level ``@lru_cache`` wrappers, found by type.

    Derived from the type ``functools.lru_cache`` actually produces, not from a
    list of names a reader has to keep up to date (ADR-0039/R2).
    """
    return {
        name: value
        for name, value in sorted(namespace.items())
        if not name.startswith("__")
        and isinstance(value, functools._lru_cache_wrapper)
    }


def lru_cache_names(namespace: Mapping[str, object]) -> set[str]:
    """Which module-level names are ``@lru_cache`` stores, whatever they hold.

    The exemption :func:`retained_bitmap_bytes` grants is to these names, so a
    control on the exemption has to be able to ask *which* names it covers
    without asking how many bytes are in them. That distinction is the whole
    point: ``currsize`` depends on the content a run put through the cache and
    on which tests the selection ran, so a control written over
    :attr:`Retention.by_cache` alone would make a selection-**independent**
    claim depend on selection -- it would red on any narrow selection that left
    a cache cold. This answers from the decorator's own type instead, which no
    selection can change.
    """
    return set(_caches_of(namespace))


def retained_bitmap_bytes(namespace: Mapping[str, object]) -> Retention:
    """Everything a module will outlive its fixtures holding, split in two.

    pytest keeps a test module in ``sys.modules``, so a module-level name
    outlives the module-scoped fixture that filled it. CARD-218's walk read
    each module-level name and **one** level inside a module-level list, tuple,
    set or dict, which is where its F-001's 433.4 MB was found -- and it
    declared four channels it could not see rather than widening. Those four
    are walked now -- a page's pixels as a numpy array
    (:func:`bitmap_bytes`), a container nested arbitrarily deep, a bitmap on a
    ``Test`` class attribute, and a bitmap inside an ``@lru_cache`` store --
    and so are three CARD-219's cycle 1 found still open: a deque or any other
    container the old list of types did not name, an ordinary object's own
    attributes (``__slots__`` included), and a cache the walk meets that
    ``namespace`` never named.

    **It is still not a universal, and :func:`_step` is the authority on what
    it is.** That function enumerates every edge this walk follows and every
    edge it declines, which is the honest shape: cycle 1 parked one page
    bitmap in each of three declined places and measured 0 B three times while
    two docstrings claimed "anywhere".

    **Why the result is a split and not a total.** Widening a predicate and
    adding an exemption are one edit, and the exemption is the half that gets
    forgotten. A ``@lru_cache`` store is genuinely out of a shared-fixture
    control's subject -- it is the memoisation the module was written with, not
    something a fixture left behind -- and in CARD-218's band file the two
    pre-existing ones hold **25,192,183 B**, measured through this walk on
    2026-10-24: ``_set_once`` 24,435,107 B at currsize 666 and ``_font_bytes``
    757,076 B. So a "``total <`` one page bitmap" bound **cannot** survive this
    widening, and raising the bound to admit the caches would be an exemption
    granted silently to everything else as well. That retention predates
    CARD-218 (the same two decorators are at ``c7cca514``) and is backlogged in
    its own right.

    **The unit those bytes are in, which CARD-219 cycle 1 asked for and is
    answered here rather than left implied.** :func:`bitmap_bytes` returns
    *bytes of image or array memory*, and that is the only unit
    :attr:`Retention.by_cache` is in. It is **not** page-bitmap bytes, and the
    two must not be divided into one another: a page of this book is
    2550x3300 RGB at three bytes a pixel, while ``_set_once`` caches cropped
    **boolean ink masks** at one byte a cell (measured 2026-10-24: all 666
    cached values are ``dtype('bool')``). "0.9979 of a page bitmap", which the
    docstrings here used to say, compares 1-byte cells with 3-byte pixels and
    is dropped. Nor is 24,435,107 B an upper bound on what that cache costs
    the process: each cached mask is a numpy **view** of an uncropped mask, and
    the 666 distinct bases those views keep alive measure **110,882,067 B** --
    4.5x the figure above, through an edge :func:`_step` declines (it never
    walks inside something it has measured). Both numbers are facts about
    pre-existing retention, and CARD-219 changed neither it nor the
    exemption's mechanism; the larger one is recorded because the smaller one
    reads like a ceiling and is not.

    :attr:`Retention.by_name` is therefore the half a control holds to an
    **equality** -- the accumulators hold ``32 B`` per page they signed or they
    are wrong -- and :attr:`Retention.by_cache` is the allowance, reported per
    cache so a control can assert **which** names are exempt (a set equality
    over :func:`_caches_of`, derived by type) without asserting how many bytes
    they hold. The byte figure deliberately gets no assertion: a cache's
    ``currsize`` depends on the content the run put through it and on which
    tests the selection ran, and a control whose subject is
    selection-independent must not be made to depend on selection.
    """
    caches = _caches_of(namespace)
    home = namespace.get("__name__")
    # The exemption is to these *objects*, identified the way the walk meets
    # them. By name it could not be: a cache the walk reaches inside a
    # container has no module-level name, so a name-based skip would have
    # exempted it silently — 25 MB of allowance nobody granted (CARD-219
    # cycle 1, F-001: an `@lru_cache` bound inside a list measured 0 B).
    exempt = frozenset(id(cache) for cache in caches.values())
    by_name: dict[str, int] = {}
    for name, value in sorted(namespace.items()):
        if name.startswith("__"):
            continue
        held = _reachable_bytes(
            value,
            enter_caches=False,
            exempt=exempt,
            home=home if isinstance(home, str) else None,
        )
        if held:
            by_name[name] = held
    by_cache = {
        name: _reachable_bytes(
            cache,
            enter_caches=True,
            exempt=exempt,
            home=home if isinstance(home, str) else None,
        )
        for name, cache in caches.items()
    }
    return Retention(by_name=by_name, by_cache={
        name: held for name, held in by_cache.items() if held
    })
