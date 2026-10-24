"""CARD-219 — the controls on :mod:`tests.helpers.shared_fixture_controls`.

Three things are asserted here and nowhere else:

1. **The duplication cannot come back.** CARD-218 had to write nine helpers
   twice because a scope fence put the only shared home out of reach, and
   nothing asserted the copies agreed — eight were byte-identical and the
   ninth's assertion message prescribed a different remedy in each file.
   :class:`TestSharedControls_TheCopiesCannotComeBack` refuses any module that
   imports the shared home and also defines its own copy of one of its names.

2. **Hole 1's four closures each catch something the pre-card reading missed.**
   Every control below is a pair: the shape is found by
   :func:`~tests.helpers.shared_fixture_controls.declared_consumers` and
   **not** found by :func:`_as_card_218_read_it`, which is CARD-218's reading
   written out again here. A closure whose control passed both ways would be
   certifying nothing.

3. **Hole 2's four channels, and the exemption the widening had to admit.**
   Same pair shape against :func:`_as_card_218_walked_it`, plus the controls on
   the exemption itself: a ``@lru_cache`` store is reported apart from
   everything else, and nothing that is not such a store may land in that
   allowance.

The synthetic namespaces are built **inside** functions on purpose. A
``class TestX`` at this module's top level would be collected by pytest and
error on a fixture that does not exist here; defined in a local scope and put
into a plain dict under the key the helper reads, the same class is data.
"""

from __future__ import annotations

import ast
import functools
import inspect
from pathlib import Path

import numpy as np
import pytest

from tests.helpers import shared_fixture_controls as controls

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = REPO_ROOT / "tests"

#: The shared home's own module name as an importer spells it.
HOME = "tests.helpers.shared_fixture_controls"


# --------------------------------------------------------------------------
# The two pre-card readings, written out so every claim below has a WITHOUT arm
# --------------------------------------------------------------------------


def _as_card_218_read_it(namespace: dict[str, object], fixture: str) -> set[str]:
    """CARD-218's ``_declared_consumers``, verbatim in behaviour.

    A top-level test function's own signature, and a top-level ``Test`` class's
    own ``vars()``. Nothing else. This is the **missed WITHOUT** arm of every
    hole-1 control below (ADR-0039/R1), and it is a second implementation
    rather than the shared function called with a flag: a flag would let one
    edit move both arms together.
    """
    found: set[str] = set()
    for name, value in namespace.items():
        if isinstance(value, type) and name.startswith("Test"):
            found.update(
                f"{name}::{attr}"
                for attr, member in vars(value).items()
                if attr.startswith("test_") and controls.declares(member, fixture)
            )
        elif name.startswith("test_") and controls.declares(value, fixture):
            found.add(name)
    return found


def _as_card_218_walked_it(namespace: dict[str, object]) -> dict[str, int]:
    """CARD-218's ``_retained_bitmap_bytes``, verbatim in behaviour.

    Each module-level name, and **one** level inside a module-level list,
    tuple, set or dict. The four channels it declared it could not see are
    exactly what the controls below put in front of it.
    """
    found: dict[str, int] = {}
    for name, value in sorted(namespace.items()):
        if name.startswith("__"):
            continue
        held = _flat_bytes(value)
        if isinstance(value, dict):
            held += sum(_flat_bytes(item) for item in value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            held += sum(_flat_bytes(item) for item in value)
        if held:
            found[name] = held
    return found


def _flat_bytes(value: object) -> int:
    """CARD-218's ``_bitmap_bytes``: no numpy arm, which is hole 2's first half."""
    if isinstance(value, memoryview):
        return value.nbytes
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    width = getattr(value, "width", None)
    height = getattr(value, "height", None)
    bands = getattr(value, "getbands", None)
    if isinstance(width, int) and isinstance(height, int) and callable(bands):
        return width * height * len(bands())
    return 0


class _Sheet:
    """A stand-in for a drawn page: the geometry both walks measure, no pixels.

    ``bitmap_bytes`` reads ``width``/``height``/``getbands`` and allocates
    nothing, so a stand-in is measured exactly as a real page is and costs
    three attributes instead of 25 MB.
    """

    def __init__(self, width: int = 100, height: int = 70) -> None:
        self.width = width
        self.height = height

    def getbands(self) -> tuple[str, str, str]:
        return ("R", "G", "B")


#: What one :class:`_Sheet` is worth to either walk.
SHEET_BYTES = 100 * 70 * 3


# --------------------------------------------------------------------------
# 1. The copies cannot come back
# --------------------------------------------------------------------------


def _shared_names() -> set[str]:
    """Every public function and class the shared home defines, by introspection.

    Derived from the module object rather than from a list in this file
    (ADR-0039/R2): a helper added there is covered here without anyone
    remembering to add it.
    """
    return {
        name
        for name, value in vars(controls).items()
        if not name.startswith("_")
        and (inspect.isfunction(value) or inspect.isclass(value))
        and getattr(value, "__module__", None) == controls.__name__
    }


def _importers() -> list[Path]:
    """Every test module that imports the shared home, found by parsing.

    An ``import`` statement is read out of the AST rather than grepped, so this
    module's own prose about the home is not an importer and a commented-out
    import is not either.
    """
    found: list[Path] = []
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        if path == Path(__file__).resolve():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - the tree parses today
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and (
                node.module == HOME or node.module.endswith("shared_fixture_controls")
            ):
                found.append(path)
                break
            if isinstance(node, ast.Import) and any(
                alias.name == HOME for alias in node.names
            ):
                found.append(path)
                break
    return found


class TestSharedControls_TheCopiesCannotComeBack:
    """The agreement guard CARD-218's two copies never had.

    There is no longer anything to cross-check, because there is one
    definition — and that is the claim this class holds. Its subject is the
    *re-appearance* of a copy: a module that imports the shared home and then
    shadows one of its names with a local definition is back to two readings of
    the same question, and that is the state the nine helpers were in before
    this card.
    """

    def test_the_importer_set_is_not_empty(self) -> None:
        """Non-vacuity: a check over no files passes however broken it is."""
        importers = _importers()
        assert len(importers) >= 2, (
            "no test module imports the shared control home, so the "
            f"redefinition check below has nothing to check: {importers}"
        )

    def test_the_shared_name_set_is_not_empty(self) -> None:
        """The other half of the same vacuity question."""
        names = _shared_names()
        assert len(names) >= 9, (
            f"the shared home exports {len(names)} names, fewer than the nine "
            f"helpers CARD-218 duplicated: {sorted(names)}"
        )

    def test_no_importer_defines_its_own_copy_of_a_shared_helper(self) -> None:
        """A module may import a helper or write its own — never both.

        The names are compared with a leading underscore stripped, because
        CARD-218's copies were module-private (``_case_of``) and a module that
        imports ``case_of`` under that same private alias and *also* defines
        ``_case_of`` has two readings of one question again.
        """
        shadowed: dict[str, list[str]] = {}
        shared = _shared_names()
        for path in _importers():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            local = {
                node.name.lstrip("_")
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            }
            clash = sorted(local & {name.lstrip("_") for name in shared})
            if clash:
                shadowed[str(path.relative_to(REPO_ROOT))] = clash
        assert not shadowed, (
            f"{len(shadowed)} module(s) import the shared control home and "
            f"also define their own copy of one of its names: {shadowed}. That "
            "is the state CARD-218 shipped in — nine helpers in two files, "
            "eight byte-identical and the ninth prescribing a different remedy "
            "in each — and nothing asserted the copies agreed. Delete the local "
            "copy and import it, or give the local one a name that is not the "
            "shared one's."
        )

    def test_a_denominator_read_off_another_module_is_refused(self, request) -> None:
        """The agreement guard on the namespace a caller hands over.

        ``refuse_unless_every_consumer_is_collected`` reads the denominator off
        a namespace and the collected consumers off ``request.module``. Handed
        one module's ``globals()`` while running in another it would not answer
        a weaker question, it would answer a different one — and depending on
        which way round the mistake went it would red every whole-file run or
        pass every narrow one. Nothing in the tree makes that mistake today,
        which is why the assertion needs this: without it the guard is a line
        that cannot fail, and CARD-218's cycle 2 (F-005) deleted exactly such a
        conjunct from one of these controls.
        """
        with pytest.raises(AssertionError) as raised:
            controls.refuse_unless_every_consumer_is_collected(
                request, {"__name__": "tests.some.other.module"}, "pages"
            )

        assert "tests.some.other.module" in str(raised.value)

    def test_no_importer_reaches_for_a_fixture_at_run_time(self) -> None:
        """Hole 1's one remaining channel, held to zero across every importer.

        ``request.getfixturevalue`` is invisible to **both** halves of the
        selection guard and no static reading can fix that, so the shared home
        offers a bound instead
        (:func:`~tests.helpers.shared_fixture_controls.refuse_unless_nothing_is_taken_dynamically`).
        It is applied here rather than once per consumer file so that a module
        which starts importing the shared home is covered the day it does.
        """
        for path in _importers():
            controls.refuse_unless_nothing_is_taken_dynamically(path)


# --------------------------------------------------------------------------
# 2. Hole 1 — the four shapes the denominator used to miss
# --------------------------------------------------------------------------


def _namespace_with_a_transitive_consumer() -> dict[str, object]:
    """A test that takes the shared fixture through another module fixture."""

    @pytest.fixture(scope="module")
    def shared() -> str:
        return "the shared render"

    @pytest.fixture
    def through(shared):  # noqa: ANN001, ANN201 - a fixture, read by signature
        return shared

    class TestThrough:
        def test_reads_it_through_another_fixture(self, through) -> None: ...

    return {"shared": shared, "through": through, "TestThrough": TestThrough}


def _namespace_with_an_inherited_consumer() -> dict[str, object]:
    """A test defined on a base class and collected on the subclass."""

    @pytest.fixture(scope="module")
    def shared() -> str:
        return "the shared render"

    class _Reads:
        def test_inherited(self, shared) -> None: ...

    class TestSubclass(_Reads):
        def test_its_own(self) -> None: ...

    return {"shared": shared, "TestSubclass": TestSubclass}


def _namespace_with_a_nested_consumer() -> dict[str, object]:
    """A test in a ``Test`` class nested inside another ``Test`` class."""

    @pytest.fixture(scope="module")
    def shared() -> str:
        return "the shared render"

    class TestOuter:
        class TestInner:
            def test_nested(self, shared) -> None: ...

    return {"shared": shared, "TestOuter": TestOuter}


def _namespace_with_a_marked_consumer() -> dict[str, object]:
    """A test that asks for the fixture with ``usefixtures`` and not by name."""

    @pytest.fixture(scope="module")
    def shared() -> str:
        return "the shared render"

    class TestMarked:
        @pytest.mark.usefixtures("shared")
        def test_marked(self) -> None: ...

    return {"shared": shared, "TestMarked": TestMarked}


def _namespace_with_a_module_marked_consumer() -> dict[str, object]:
    """``pytestmark`` at module level, which pytest applies to every test."""

    @pytest.fixture(scope="module")
    def shared() -> str:
        return "the shared render"

    class TestModuleMarked:
        def test_asks_for_nothing(self) -> None: ...

    return {
        "shared": shared,
        "TestModuleMarked": TestModuleMarked,
        "pytestmark": [pytest.mark.usefixtures("shared")],
    }


#: ``(label, namespace builder, the consumer that must be found)``. The set is
#: exactly hole 1's four open shapes plus the module-mark variant of the
#: fourth; each row is one control, and the loop below runs both arms of it.
HOLE_ONE_SHAPES = (
    (
        "transitive",
        _namespace_with_a_transitive_consumer,
        "TestThrough::test_reads_it_through_another_fixture",
    ),
    ("inherited", _namespace_with_an_inherited_consumer, "TestSubclass::test_inherited"),
    ("nested", _namespace_with_a_nested_consumer, "TestInner::test_nested"),
    ("usefixtures", _namespace_with_a_marked_consumer, "TestMarked::test_marked"),
    (
        "module pytestmark",
        _namespace_with_a_module_marked_consumer,
        "TestModuleMarked::test_asks_for_nothing",
    ),
)


class TestSharedControls_TheDenominatorSeesEveryConsumerShape:
    """Hole 1, closed shape by shape, each with its own failing WITHOUT arm.

    CARD-218's cycle 2 measured the cost of a consumer the denominator cannot
    see: taken as a parameter a late mutating class is caught in 2 failure
    cells, taken through ``getfixturevalue`` it is missed with 40 passed and 0
    cells. The four shapes below were left open after that round — a consumer
    reached through another fixture, an inherited one, one in a nested class,
    and one asking by mark — and each is a **false negative in a default-deny
    guard**, which is the one direction ADR-0039/R2 does not tolerate.

    Read the pair, not the single assertion: "found now" alone would pass on an
    implementation that returned every test in the module.
    """

    @pytest.mark.parametrize(
        "label, build, consumer",
        HOLE_ONE_SHAPES,
        ids=[row[0] for row in HOLE_ONE_SHAPES],
    )
    def test_the_shape_is_found_now_and_was_missed_before(
        self, label: str, build, consumer: str
    ) -> None:
        namespace = build()

        found = controls.declared_consumers(namespace, "shared")
        missed = _as_card_218_read_it(namespace, "shared")

        assert consumer in found, (
            f"a {label} consumer of the shared fixture is absent from the "
            f"denominator: {sorted(found)}. A default-deny guard that divides "
            "by this set would not refuse a selection that left it out "
            "(ADR-0039/R2)."
        )
        assert consumer not in missed, (
            f"CARD-218's reading already found the {label} consumer, so "
            "closing it certifies nothing — this control cannot fail and the "
            "claim must be narrowed to the shapes that really were open"
        )

    def test_a_test_that_asks_for_nothing_is_not_a_consumer(self) -> None:
        """The other direction, which the shapes above cannot show.

        A widened reading that said "every test" would satisfy every assertion
        above. It would also red every whole-file run, because
        ``item.fixturenames`` would not back it up — so this is the control for
        the over-counting half, asserted on the same namespaces.
        """
        for label, build, consumer in HOLE_ONE_SHAPES:
            namespace = build()
            found = controls.declared_consumers(namespace, "shared")
            if label == "module pytestmark":
                continue  # a module mark really does make every test one
            bystanders = {
                name for name in found if name != consumer
            }
            assert not bystanders, (
                f"the {label} namespace reports {sorted(bystanders)} as "
                "consumers of a fixture they never ask for: an over-counted "
                "denominator reds every whole-file run, because pytest's own "
                "`item.fixturenames` will not list them"
            )

    def test_one_class_s_helper_does_not_make_another_class_s_a_consumer(self) -> None:
        """Two classes, one fixture name, only one of them chained to the render.

        The hazard the transitive closure creates: resolved over a flat
        namespace, ``TestB``'s own ``through()`` would inherit ``TestA``'s
        ``through(shared)`` edge and ``TestB::test_b`` would be declared a
        consumer pytest never gives the fixture to — a red on every whole-file
        run. The closure is layered innermost-first instead, as pytest resolves
        names.
        """

        @pytest.fixture(scope="module")
        def shared() -> str:
            return "the shared render"

        class TestA:
            @pytest.fixture
            def through(self, shared):  # noqa: ANN001, ANN202
                return shared

            def test_a(self, through) -> None: ...

        class TestB:
            @pytest.fixture
            def through(self):  # noqa: ANN202
                return "something else entirely"

            def test_b(self, through) -> None: ...

        namespace = {"shared": shared, "TestA": TestA, "TestB": TestB}

        found = controls.declared_consumers(namespace, "shared")

        assert found == {"TestA::test_a"}, (
            "the fixture graph was resolved flat rather than per class: "
            f"{sorted(found)}"
        )


class TestSharedControls_TheFixtureGraphReadsPytestsOwnMarker:
    """The transitive closure's one silent failure mode, held to a control.

    The closure is built over the fixtures a namespace defines, and a fixture
    is recognised by the marker ``pytest.fixture`` leaves behind. pytest has
    already renamed that marker once — ``_pytestfixturefunction`` became
    ``_fixture_function_marker`` in 9.0 — and a rename does not raise: it
    empties the graph, which **thins the denominator**, which makes a
    default-deny guard *pass*. So the graph's non-emptiness is asserted here
    rather than left to be discovered by a guard that stopped guarding.
    """

    def test_the_graph_names_the_fixtures_this_pytest_builds(self) -> None:
        namespace = _namespace_with_a_transitive_consumer()

        graph = controls._fixture_graph(namespace)

        assert set(graph) == {"shared", "through"}, (
            "pytest's fixture marker is not being recognised, so the "
            f"transitive closure has no graph to walk: {graph}. A renamed "
            "marker empties this silently and the denominator thins with it."
        )
        assert graph["through"] == frozenset({"shared"}), graph

    def test_a_plain_function_is_not_a_fixture(self) -> None:
        """The other direction: the marker is what counts, not the signature."""

        def through(shared):  # noqa: ANN001, ANN202 - deliberately unmarked
            return shared

        graph = controls._fixture_graph({"through": through})

        assert graph == {}, graph


class TestSharedControls_TheDynamicChannelIsABoundAndNotAGap:
    """The one shape no static reading can close, and the bound's own control."""

    def test_a_module_that_reaches_for_a_fixture_at_run_time_is_refused(
        self, tmp_path: Path
    ) -> None:
        """The bound can fail — measured, not asserted in prose."""
        offender = tmp_path / "takes_it_at_run_time.py"
        offender.write_text(
            "def test_x(request):\n"
            "    page = request.getfixturevalue('shared')\n"
            "    assert page\n",
            encoding="utf-8",
        )

        with pytest.raises(AssertionError) as raised:
            controls.refuse_unless_nothing_is_taken_dynamically(offender)

        assert "line(s) [2]" in str(raised.value)

    def test_the_word_in_a_docstring_is_not_a_consumer(self, tmp_path: Path) -> None:
        """Why it parses rather than greps.

        The shared home's own docstrings name the idiom, and so does every file
        that explains why the bound exists. A grep would refuse all of them.
        """
        innocent = tmp_path / "only_talks_about_it.py"
        innocent.write_text(
            '"""This module explains request.getfixturevalue and uses none."""\n'
            "GUIDANCE = 'do not call request.getfixturevalue here'\n",
            encoding="utf-8",
        )

        controls.refuse_unless_nothing_is_taken_dynamically(innocent)

        assert controls.fixtures_taken_dynamically(
            innocent.read_text(encoding="utf-8")
        ) == []


# --------------------------------------------------------------------------
# 3. Hole 2 — the four channels, and the allowance the widening had to admit
# --------------------------------------------------------------------------


def _namespace_holding_a_numpy_page() -> dict[str, object]:
    """A page's pixels as a numpy array, which read 0 before this card."""
    return {"__name__": "synthetic", "_PIXELS": np.zeros((70, 100, 3), dtype=np.uint8)}


def _namespace_holding_a_page_behind_a_cache() -> dict[str, object]:
    """A page inside an ``@lru_cache`` store, which ``functools`` does not expose."""

    @functools.lru_cache(maxsize=None)
    def _sheet_for(key: int) -> _Sheet:
        return _Sheet()

    _sheet_for(1)
    return {"__name__": "synthetic", "_sheet_for": _sheet_for}


def _namespace_holding_a_page_on_a_class() -> dict[str, object]:
    """A page on a ``Test`` class attribute, which a module-level walk is not."""

    class TestHolder:
        KEPT = _Sheet()

    return {"__name__": "synthetic", "TestHolder": TestHolder}


def _namespace_holding_a_page_nested_twice() -> dict[str, object]:
    """A page two containers down, where the one-level walk stops."""
    return {"__name__": "synthetic", "_DEEP": {"run": [[_Sheet()]]}}


HOLE_TWO_CHANNELS = (
    ("numpy array", _namespace_holding_a_numpy_page, SHEET_BYTES, False),
    ("lru_cache store", _namespace_holding_a_page_behind_a_cache, SHEET_BYTES, True),
    ("Test class attribute", _namespace_holding_a_page_on_a_class, SHEET_BYTES, False),
    ("nested two deep", _namespace_holding_a_page_nested_twice, SHEET_BYTES, False),
)


class TestSharedControls_TheRetentionWalkSeesEveryChannel:
    """Hole 2, channel by channel, each against the walk that could not see it.

    CARD-218 declared all four in prose and widened nothing, deliberately:
    round 6 had no review left in front of it. Each is closed here with the
    same pair shape as hole 1 — found by the widened walk, invisible to
    CARD-218's — because a channel asserted in prose and never measured is how
    that card's own 433.4 MB stayed invisible in the first place.
    """

    @pytest.mark.parametrize(
        "label, build, expected, exempt",
        HOLE_TWO_CHANNELS,
        ids=[row[0] for row in HOLE_TWO_CHANNELS],
    )
    def test_the_channel_is_measured_now_and_was_invisible_before(
        self, label: str, build, expected: int, exempt: bool
    ) -> None:
        namespace = build()

        found = controls.retained_bitmap_bytes(namespace)
        side = found.by_cache if exempt else found.by_name
        blind = _as_card_218_walked_it(namespace)

        assert sum(side.values()) == expected, (
            f"a page retained through a {label} measures "
            f"{sum(side.values()):,} B, not the {expected:,} B it holds: "
            f"{found}"
        )
        assert sum(blind.values()) == 0, (
            f"CARD-218's walk already saw the {label} channel, so widening it "
            "certifies nothing and the claim must be narrowed"
        )

    def test_the_walk_does_not_leave_the_module_s_own_data(self) -> None:
        """A namespace holding a module object is not a walk over the process.

        ``gc.get_referents`` on a function hands back its ``__globals__``, so a
        walk that followed everything would reach ``sys.modules`` and measure
        the whole interpreter. This is the control that it does not: a
        namespace whose only name is this very module reports nothing, although
        this module transitively refers to numpy arrays through its own
        helpers.
        """
        import sys

        namespace = {"__name__": "synthetic", "_MOD": sys.modules[__name__]}

        found = controls.retained_bitmap_bytes(namespace)

        assert found.by_name == {} and found.by_cache == {}, found


class TestSharedControls_TheCacheAllowanceIsAnExemptionWithAControl:
    """Widening a predicate and granting an exemption are the same edit.

    The widening makes a ``@lru_cache`` store visible for the first time, and
    CARD-218's band file has two that hold **25,192,183 B — 0.9979 of one page
    bitmap** between them (measured through this instrument 2026-10-24,
    agreeing with that card's own hand-measured 25,192,439 B total once its
    256 B of digest is added). So "the module retains less than one page
    bitmap" could not survive the widening, and the honest shape is an
    equality on everything else plus a named allowance.

    The allowance is the half that gets forgotten, so it ships with its own
    controls: it admits exactly the stores ``functools`` produced, and nothing
    else can get into it.
    """

    def test_the_exemption_admits_exactly_the_cache_stores(self) -> None:
        """A page in a cache is exempt; the same page in a list is not."""
        cached = _namespace_holding_a_page_behind_a_cache()
        listed = {"__name__": "synthetic", "_KEPT": [_Sheet()]}

        in_cache = controls.retained_bitmap_bytes(cached)
        in_list = controls.retained_bitmap_bytes(listed)

        assert in_cache.by_name == {} and set(in_cache.by_cache) == {"_sheet_for"}
        assert in_list.by_cache == {} and set(in_list.by_name) == {"_KEPT"}

    def test_a_cache_holding_no_page_is_not_reported_as_an_allowance(self) -> None:
        """The exemption is measured, not granted by the decorator's presence.

        A module may memoise integers. Reporting such a cache as an allowance
        would invite a reader to treat the decorator itself as the licence
        rather than the bytes.
        """

        @functools.lru_cache(maxsize=None)
        def _double(value: int) -> int:
            return value * 2

        _double(21)

        found = controls.retained_bitmap_bytes({"__name__": "synthetic", "_double": _double})

        assert found.by_cache == {}, found

    def test_the_two_halves_do_not_double_count(self) -> None:
        """One page, one side of the split, whichever side that is."""
        namespace = _namespace_holding_a_page_behind_a_cache()
        namespace["_ALSO"] = [_Sheet()]

        found = controls.retained_bitmap_bytes(namespace)

        assert found.total == 2 * SHEET_BYTES, found
        assert sum(found.by_name.values()) == SHEET_BYTES
        assert sum(found.by_cache.values()) == SHEET_BYTES

    def test_the_same_page_reached_twice_is_counted_once(self) -> None:
        """The walk is over objects, not over paths to them."""
        page = _Sheet()
        namespace = {"__name__": "synthetic", "_KEPT": [page, page, {"again": page}]}

        found = controls.retained_bitmap_bytes(namespace)

        assert found.by_name == {"_KEPT": SHEET_BYTES}, found
