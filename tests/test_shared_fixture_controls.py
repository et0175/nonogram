"""CARD-219 — the controls on :mod:`tests.helpers.shared_fixture_controls`.

Three things are asserted here and nowhere else:

1. **The duplication cannot come back.** CARD-218 had to write nine helpers
   twice because a scope fence put the only shared home out of reach, and
   nothing asserted the copies agreed — eight were byte-identical and the
   ninth's assertion message prescribed a different remedy in each file.
   :class:`TestSharedControls_TheCopiesCannotComeBack` refuses any module that
   imports the shared home and also defines its own copy of one of its names —
   a ``def``, a ``class`` or an **assignment**, at any depth, because the
   first version of that guard read only top-level definitions and a faithful
   aliased copy therefore shipped green (cycle 1, F-003).

2. **Hole 1's closures each catch something the pre-card reading missed.**
   Every control below is a pair: the shape is found by
   :func:`~tests.helpers.shared_fixture_controls.declared_consumers` and
   **not** found by :func:`_as_card_218_read_it`, which is CARD-218's reading
   written out again here. A closure whose control passed both ways would be
   certifying nothing.

3. **Hole 2's channels, and the exemption the widening had to admit.** Same
   pair shape against :func:`_as_card_218_walked_it`, plus the controls on the
   exemption itself: a module-level ``@lru_cache`` store is reported apart
   from everything else, nothing that is not such a store may land in that
   allowance, and a cache the walk meets that the namespace never named is not
   an allowance at all.

4. **The fence.** The walk enters instances and containers, so it is also
   asserted *not* to leave the module it was asked about
   (:meth:`TestSharedControls_TheRetentionWalkSeesEveryChannel.test_the_fence_holds_at_each_edge_that_could_leave_it`).
   Neither the walk nor these controls claim to see every retained page: what
   they do and do not enter is enumerated in
   ``shared_fixture_controls._step``'s own docstring, which is the one place
   that list lives.

The synthetic namespaces are built **inside** functions on purpose. A
``class TestX`` at this module's top level would be collected by pytest and
error on a fixture that does not exist here; defined in a local scope and put
into a plain dict under the key the helper reads, the same class is data.
"""

from __future__ import annotations

import ast
import collections
import functools
import gc
import inspect
import re
import types
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pytest

from tests.helpers import shared_fixture_controls as controls

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = REPO_ROOT / "tests"

#: The shared home's own module name as an importer spells it.
HOME = "tests.helpers.shared_fixture_controls"

#: Its leaf module name, derived from :data:`HOME` so this file holds one
#: spelling of it and not two.
HOME_LEAF = HOME.rsplit(".", 1)[-1]

#: The home's own file and this module, by identity rather than by spelling.
#: Both name the leaf without importing it, so both sit outside the
#: cross-check in :func:`_files_that_name_the_home`.
HOME_FILE = (TESTS_ROOT / "helpers" / f"{HOME_LEAF}.py").resolve()
THIS_FILE = Path(__file__).resolve()

#: The leaf name as text, with this module's own *file* name excluded by
#: construction: ``tests/test_shared_fixture_controls.py`` carries the leaf as
#: a substring, so a card quoting this module's path in a docstring would
#: otherwise read as a file that reaches the home. Measured on CARD-220's fix
#: round: today the lookbehind changes nothing -- with and without it the text
#: reading returns the same three files -- so it is a pre-emption, not a live
#: exclusion.
NAMES_THE_HOME = re.compile(rf"(?<!test_){re.escape(HOME_LEAF)}")


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


def _imported_dotted_names(tree: ast.AST) -> set[str]:
    """Every dotted name an ``import`` statement in ``tree`` could bind.

    One reading of *all* the import statements rather than one pattern per
    shape somebody remembered (ADR-0039/R2): the set is derived from the
    statements themselves, so no form has to be anticipated by name.
    ``ast.walk`` is full depth, so an import deferred inside a function, a
    ``try`` or a class body is read exactly like a top-level one.

    For ``from X import y`` both ``X`` and ``X.y`` are reported, because
    whether ``y`` is a submodule or an attribute of ``X`` is not decidable
    from the statement -- and for this question it need not be: either way the
    file has the home's names in hand. A relative import keeps its leading
    dots, which is enough for the leaf match below and is why no package
    arithmetic is attempted here.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            names.add(base)
            names.update(
                f"{base.rstrip('.')}.{alias.name}"
                for alias in node.names
                if alias.name != "*"
            )
    return names


def _import_names_the_home(dotted: str) -> bool:
    """Whether one dotted import name reaches the shared home.

    The leaf is matched as a **whole dotted segment**, so
    ``shared_fixture_controls_extra`` is a different module and
    ``from tests.helpers import shared_fixture_controls as controls`` is this
    one.
    """
    return dotted == HOME or dotted == HOME_LEAF or dotted.endswith(f".{HOME_LEAF}")


def _importers() -> list[Path]:
    """Every test module that imports the shared home, found by parsing.

    An ``import`` statement is read out of the AST rather than grepped, so this
    module's own prose about the home is not an importer and a commented-out
    import is not either.

    **Every import form, not a list of two.** Until CARD-220's fix round 1
    this read exactly two shapes -- an ``ImportFrom`` whose *module* is the
    home, and an ``Import`` whose alias *is* the home -- and was therefore
    blind to ``from tests.helpers import shared_fixture_controls as controls``,
    which is the form this very module uses on itself and the only occurrence
    of it in the tree. Cycle 1's F-001 measured the cost: a synthetic importer
    written that way, carrying a live ``request.getfixturevalue`` consumer,
    ran **green** through
    :meth:`~TestSharedControls_TheCopiesCannotComeBack.test_no_importer_reaches_for_a_fixture_at_run_time`,
    while the same violation in a recognised form failed it. That became
    load-bearing the day CARD-220 retired the two per-file copies of that
    bound: each was keyed on its own ``__file__`` and so immune to any import
    refactor, and afterwards this function is the only thing that puts those
    two files inside the bound. It now asks the statements
    (:func:`_imported_dotted_names`) instead of matching remembered shapes.

    What it **cannot** analyse is a failure rather than an absence: an
    unparsable file raises here, and a file that names the home by a route no
    import statement declares is reported by name by
    :meth:`TestSharedControls_TheCopiesCannotComeBack.test_the_importer_set_is_not_empty`
    against :func:`_files_that_name_the_home`. Each recognised and refused
    form carries a row in :data:`IMPORT_FORMS`.
    """
    found: list[Path] = []
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        if path.resolve() in {HOME_FILE, THIS_FILE}:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover - the tree parses today
            raise AssertionError(
                f"{path.relative_to(REPO_ROOT)} does not parse, so this "
                "reading cannot establish that it is NOT an importer of the "
                "shared home. An unanalysable file is a failure here and not "
                "an absence (ADR-0039/R2): skipping it would silently shrink "
                f"the bound that file may be inside. {exc}"
            ) from exc
        if any(_import_names_the_home(name) for name in _imported_dotted_names(tree)):
            found.append(path)
    return found


def _files_that_name_the_home() -> list[Path]:
    """Every test file whose *text* names the shared home -- the crude reading.

    The second, independent answer to the same question, and the only thing
    that can catch :func:`_importers` losing a file (ADR-0039/R1). A module
    can reach the home by a route no import statement declares --
    ``importlib.import_module``, a fixture that hands the module object over,
    a helper that re-exports it -- and no structural reading sees any of
    those. This one sees every file that so much as names it, those included;
    the two sets are asserted **equal**, so a file one reading has and the
    other has not is named rather than merely absent from the bound.

    What escapes this reading too, stated rather than implied: a module that
    reaches the home without naming it anywhere in its own text -- a dotted
    name assembled at run time from pieces. Nothing in the tree does that.
    """
    return [
        path
        for path in sorted(TESTS_ROOT.rglob("*.py"))
        if path.resolve() not in {HOME_FILE, THIS_FILE}
        and NAMES_THE_HOME.search(path.read_text(encoding="utf-8"))
    ]


def _as_the_import_reading_was_before_card_220(tree: ast.AST) -> bool:
    """CARD-220's pre-fix-round :func:`_importers` predicate, in behaviour.

    Two shapes: an ``ImportFrom`` whose ``module`` is the home or ends with
    the leaf, and an ``Import`` whose alias name **is** the home. This is the
    missed-WITHOUT arm of every row of :data:`IMPORT_FORMS` (ADR-0039/R1), and
    it is a second implementation rather than the live function behind a flag:
    a flag would let one edit move both arms together.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and (
            node.module == HOME or node.module.endswith(HOME_LEAF)
        ):
            return True
        if isinstance(node, ast.Import) and any(
            alias.name == HOME for alias in node.names
        ):
            return True
    return False


def _reads_as_an_importer(source: str) -> bool:
    """:func:`_importers`' own predicate, asked of a source string."""
    return any(
        _import_names_the_home(name)
        for name in _imported_dotted_names(ast.parse(source))
    )


def _locally_defined_names(source: str) -> set[str]:
    """Every name this source **binds itself**, at any depth.

    Two readings in one, both derived from the AST's own notion of a binding
    rather than from a list of statement kinds:

    * a ``def``, an ``async def`` or a ``class``, wherever it stands --
      module level, inside a class, inside a function, inside an ``if`` or a
      ``try``;
    * every :class:`ast.Name` in a **store** context, which is how the
      grammar spells ``x = ...``, ``x: T = ...``, ``x += ...``,
      ``for x in ...``, ``with ... as x`` and ``(x := ...)``.

    CARD-219's first version of this read ``tree.body`` and only the three
    definition nodes -- *the one spelling its own three controls were written
    in* -- so a faithful third copy of a shared helper bound with
    ``_page_digest = _probe_own_digest`` shipped completely green (cycle 1,
    F-003, measured: 65 passed, 0 cells). An alias is the cheapest way to put
    a copy back, because every call site keeps working.

    **An ``import ... as`` binding is deliberately not a definition here.**
    It is a :class:`ast.alias`, not a stored ``Name``, and importing the
    shared helper under the private name a file used to spell its own copy
    with is exactly what this module asks importers to do -- each of the two
    CARD-218 files binds six of these names that way, and
    ``test_the_claims_edge_stays_green`` holds that spelling to staying green.

    **Depth-blind on purpose, and that has a cost worth stating.** A local
    variable or a method that happens to carry a shared helper's name is
    reported too, although it is not a copy of anything. The remedy the
    message prescribes (rename it) is cheap; the alternative is the blindness
    F-003 found.

    **That measurement was re-run 2026-10-24 (cycle 2, F-202) and the first
    reading was wrong. It said "zero such names in the tree"; there is one.**
    ``tests/helpers/book_corpus.py:757`` defines its own
    ``page_digest(page) -> Dict[str, Any]`` -- a hex sha256 in a dict -- beside
    this package's ``page_digest(page) -> bytes``, the raw 32 bytes. Two
    readings of one question, in the same package, in a module that is in
    CARD-219's own ``Touches``. It is **pre-existing** (present at the fork
    point ``808cf51f``) and it is not a live defect here:
    ``tests/test_book_puzzle_frame.py:138`` imports from this home, so the
    figures measured against it hold. The collision is routed to a successor
    card; what was defective was the sentence claiming there were none -- a
    figure stated as a measurement, which is the one thing no mutant can catch.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            found.add(node.id)
    return found


def _as_the_guard_first_read_it(source: str) -> set[str]:
    """CARD-219's first reading, kept as the **missed WITHOUT** arm (F-003).

    ``tree.body``, and only ``FunctionDef``/``AsyncFunctionDef``/``ClassDef``.
    A second implementation rather than a flag on the one above, so one edit
    cannot move both arms together.
    """
    return {
        node.name
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _copies_among(names: Iterable[str], shared: Iterable[str]) -> set[str]:
    """The ``names`` that are a copy of one of ``shared``, compared stripped.

    CARD-218's copies were module-private (``_case_of``), so a leading
    underscore is stripped from both sides before they are compared.
    """
    wanted = {name.lstrip("_") for name in shared}
    return {name for name in names if name.lstrip("_") in wanted}


#: ``(label, source)`` for a module that puts a **faithful** copy of a shared
#: helper back. Every row must be caught by :func:`_locally_defined_names` and
#: missed by :func:`_as_the_guard_first_read_it`: these are the spellings the
#: guard was **not** written from (ADR-0039/R1), and the first of them is
#: cycle 1's F-003 mutant verbatim.
AGREEMENT_SHAPES_CAUGHT = (
    (
        "faithful alias",
        "import hashlib\n"
        "\n"
        "\n"
        "def _probe_own_digest(page):\n"
        "    return hashlib.sha256(page.tobytes()).digest()\n"
        "\n"
        "\n"
        "_page_digest = _probe_own_digest\n",
    ),
    ("annotated alias", "_case_of: object = None\n"),
    (
        "alias bound in a try",
        "try:\n"
        "    from somewhere import digest as _page_digest\n"
        "except ImportError:\n"
        "    _page_digest = None\n",
    ),
    (
        "alias bound in an if",
        "import sys\n"
        "\n"
        "if sys.version_info >= (3, 14):\n"
        "    _declares = None\n"
        "else:\n"
        "    _declares = None\n",
    ),
    (
        "a method of a class",
        "class TestSomething:\n"
        "    def case_of(self, item):\n"
        "        return item.name\n",
    ),
    (
        "a function inside a function",
        "def helper():\n"
        "    def bitmap_bytes(value):\n"
        "        return 0\n"
        "\n"
        "    return bitmap_bytes\n",
    ),
)

#: ``(label, source)`` for a module that must stay **green** in both readings:
#: the claim's edge. A guard that reds here would make the one spelling this
#: module asks importers to use -- the import alias -- unusable.
AGREEMENT_SHAPES_GREEN = (
    (
        "the sanctioned import alias",
        "from tests.helpers.shared_fixture_controls import (\n"
        "    page_digest as _page_digest,\n"
        "    case_of as _case_of,\n"
        ")\n",
    ),
    ("a near miss", "_case_of_the_band = None\n"),
    (
        "an alias to something that is not a shared helper",
        "def _probe_own_digest(page):\n"
        "    return b''\n"
        "\n"
        "\n"
        "_my_own_digest = _probe_own_digest\n",
    ),
)

#: Every form a module could reach the shared home by, with what each of the
#: two readings makes of it: ``(label, source, seen now, seen before)``.
#: ``seen before`` is CARD-220's pre-fix-round two-shape reading
#: (:func:`_as_the_import_reading_was_before_card_220`), kept as the WITHOUT
#: arm so each widened row proves it closed something that was open rather
#: than restating something that already worked -- and the rows both readings
#: agree on keep the widening honest, because without them "seen now" would be
#: satisfied by a reading that answers ``True`` to everything.
IMPORT_FORMS = (
    (
        "a name out of the home",
        "from tests.helpers.shared_fixture_controls import case_of\n",
        True,
        True,
    ),
    (
        "a star out of the home",
        "from tests.helpers.shared_fixture_controls import *\n",
        True,
        True,
    ),
    (
        "the module itself, dotted and aliased",
        "import tests.helpers.shared_fixture_controls as controls\n",
        True,
        True,
    ),
    (
        "the module out of its package, aliased - F-001's form",
        "from tests.helpers import shared_fixture_controls as controls\n",
        True,
        False,
    ),
    (
        "the module out of its package, plain",
        "from tests.helpers import shared_fixture_controls\n",
        True,
        False,
    ),
    (
        "the module out of its package, relatively",
        "from .helpers import shared_fixture_controls as controls\n",
        True,
        False,
    ),
    (
        "deferred inside a function, aliased",
        "def _late():\n"
        "    from tests.helpers import shared_fixture_controls as controls\n"
        "    return controls\n",
        True,
        False,
    ),
    (
        "a longer sibling module, not the home",
        "from tests.helpers import shared_fixture_controls_extra\n",
        False,
        False,
    ),
    (
        "the home's name in prose only",
        '"""This module does not use shared_fixture_controls at all."""\n',
        False,
        False,
    ),
    (
        "a commented-out import",
        "# from tests.helpers import shared_fixture_controls as controls\n",
        False,
        False,
    ),
)


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
        """Non-vacuity, and the exactness a floor cannot give it.

        A check over no files passes however broken it is -- but a bare floor
        is a weak answer to that, and CARD-220's cycle 1 (F-001) measured how
        weak: this read ``len(importers) >= 2`` against a measured set of
        **three**, so one importer could drop out of the bound below and
        nothing would notice. It had by then become the *only* guard on that
        set, because the same card retired the two per-file copies of the
        bound, each of which was keyed on its own ``__file__`` and so could not
        be switched off by an import refactor.

        So the set is held to the second, independent reading of the same
        question (:func:`_files_that_name_the_home`) rather than to a number.
        A file that names the home and that the parse does not see is reported
        by name -- which is what makes an import form this reading cannot
        analyse a *failure* rather than an absence -- and a file that stops
        being seen reds here instead of quietly leaving the loop below.
        Measured on the fix round: deleting one importer's import line alone
        leaves the old floor green (3 -> 2, still ``>= 2``) and reds this.
        """
        importers = _importers()
        assert importers, (
            "no test module imports the shared control home, so the "
            f"redefinition check below has nothing to check: {importers}"
        )

        named = _files_that_name_the_home()
        assert set(importers) == set(named), {
            "names the home, not read as an importer": sorted(
                str(path.relative_to(REPO_ROOT)) for path in set(named) - set(importers)
            ),
            "read as an importer, does not name the home": sorted(
                str(path.relative_to(REPO_ROOT)) for path in set(importers) - set(named)
            ),
            "why this is red": (
                "the two readings of 'which modules reach the shared control "
                "home' disagree, so the bound below is over a set nothing "
                "agrees on. Either an import form `_importers` cannot analyse "
                "has appeared -- widen it, with its row in IMPORT_FORMS -- or "
                "a file only talks about the home, in which case it belongs "
                "in a named allowance here with its reason, deliberately "
                "rather than silently."
            ),
        }

    @pytest.mark.parametrize(
        "label, source, seen_now, seen_before",
        IMPORT_FORMS,
        ids=[row[0] for row in IMPORT_FORMS],
    )
    def test_the_import_reading_sees_every_form_and_no_near_miss(
        self, label: str, source: str, seen_now: bool, seen_before: bool
    ) -> None:
        """The control CARD-220's widening of :func:`_importers` owes.

        Cycle 1's F-001 was not a predicate gap -- the retired per-file copies
        were inlined copies of the shared bound's own body, so no predicate gap
        was possible -- it was a **scope selector** gap: *which file's source
        gets read*. Widening a selector with no control of its own is the same
        defect once more, so every form is asserted in both directions, with
        the pre-card reading as the WITHOUT arm.
        """
        assert _reads_as_an_importer(source) is seen_now, (
            f"the import form {label!r} is "
            f"{'invisible to' if seen_now else 'visible to'} `_importers`, so "
            "a module reaching the shared control home that way is "
            f"{'outside the' if seen_now else 'wrongly inside the'} "
            "dynamic-fixture bound below"
        )
        assert (
            _as_the_import_reading_was_before_card_220(ast.parse(source))
            is seen_before
        ), (
            f"the WITHOUT arm has moved on {label!r}. The pre-CARD-220 reading "
            "is written out here so each widened row proves it closed "
            "something that was open; a row the two readings agree on "
            "certifies nothing about the widening and belongs in the agreeing "
            "rows or in no row at all"
        )

    def test_the_shared_name_set_is_not_empty(self) -> None:
        """The other half of the same vacuity question."""
        names = _shared_names()
        assert len(names) >= 9, (
            f"the shared home exports {len(names)} names, fewer than the nine "
            f"helpers CARD-218 duplicated: {sorted(names)}"
        )

    @pytest.mark.parametrize(
        "label, source",
        AGREEMENT_SHAPES_CAUGHT,
        ids=[row[0] for row in AGREEMENT_SHAPES_CAUGHT],
    )
    def test_a_copy_in_this_spelling_is_caught_now_and_was_missed_before(
        self, label: str, source: str
    ) -> None:
        """The pair for every spelling the guard was **not** written from.

        Cycle 1's F-003: the guard read ``tree.body`` and only the three
        definition nodes, which is the one spelling its own three controls
        (M21/M22/M23) were written in — so a byte-for-byte third copy of a
        shared helper, aliased to a new ``def`` and used at every call site,
        shipped green. Found now, and the WITHOUT arm proves the closure is
        not certifying something that already worked.
        """
        shared = _shared_names()

        caught = _copies_among(_locally_defined_names(source), shared)
        missed = _copies_among(_as_the_guard_first_read_it(source), shared)

        assert caught, (
            f"a copy of a shared helper spelled as {label} is invisible to "
            "the agreement guard, so a module may import the helper and keep "
            "its own copy of it — the state CARD-218 shipped in (F-003)"
        )
        assert not missed, (
            f"the guard's first reading already caught {label}, so closing it "
            "certifies nothing and this row belongs in the GREEN table or in "
            "no table at all"
        )

    # CARD-220 examined this test and the one above as a deletion candidate
    # -- one table walked twice -- and KEPT BOTH. They walk DIFFERENT tables
    # carrying OPPOSITE claims: AGREEMENT_SHAPES_CAUGHT is what the guard must
    # report, AGREEMENT_SHAPES_GREEN is what it must not. Merging them into
    # one parametrisation would need a verdict column and would put both
    # claims behind one assertion. Neither is redundant and neither has a
    # named survivor, so neither may be retired under this card's rule.
    @pytest.mark.parametrize(
        "label, source",
        AGREEMENT_SHAPES_GREEN,
        ids=[row[0] for row in AGREEMENT_SHAPES_GREEN],
    )
    def test_the_claims_edge_stays_green(self, label: str, source: str) -> None:
        """The other direction, without which the reading above could be "all".

        A guard that reported every name would satisfy every row of the table
        above. These three are the rows it must **not** report: the import
        alias this module asks importers to use (both CARD-218 files bind nine
        names that way), a near miss, and an alias to a name that is not a
        shared helper at all.
        """
        shared = _shared_names()

        assert not _copies_among(_locally_defined_names(source), shared), (
            f"{label} is not a copy of a shared helper, and a guard that "
            "refuses it refuses the spelling this module exists to encourage"
        )

    def test_no_importer_defines_its_own_copy_of_a_shared_helper(self) -> None:
        """A module may import a helper or write its own — never both.

        The names are compared with a leading underscore stripped, because
        CARD-218's copies were module-private (``_case_of``) and a module that
        imports ``case_of`` under that same private alias and *also* defines
        ``_case_of`` has two readings of one question again.

        What counts as "defines" is :func:`_locally_defined_names` — every
        ``def``/``class`` and every stored ``Name`` at any depth, which is the
        reading cycle 1's F-003 forced; the two tests above are its own
        controls in both directions.
        """
        shadowed: dict[str, list[str]] = {}
        shared = _shared_names()
        for path in _importers():
            clash = sorted(
                _copies_among(
                    _locally_defined_names(path.read_text(encoding="utf-8")), shared
                )
            )
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
        which starts importing the shared home is covered the day it does --
        in **any** import form, at any depth. That claim was measured FALSE
        before CARD-220's fix round: cycle 1's F-001 planted a real importer
        spelled ``from tests.helpers import shared_fixture_controls as
        controls`` with a live violation in it and this test passed green, one
        of the two idiomatic forms being invisible to :func:`_importers`. The
        reading is widened and :data:`IMPORT_FORMS` is its control; the set
        this loop runs over is cross-checked against an independent reading by
        :meth:`test_the_importer_set_is_not_empty`, so a file dropping out of
        it reds there rather than quietly leaving this bound.
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


def _namespace_with_an_autouse_consumer() -> dict[str, object]:
    """An ``autouse`` fixture that takes the shared fixture (cycle 1, F-002).

    No test names anything. pytest gives the shared render to every test in
    the module all the same, so every test is a consumer — and the pre-fix
    reading returned an **empty** denominator, which made the refusal pass.
    """

    @pytest.fixture(scope="module")
    def shared() -> str:
        return "the shared render"

    @pytest.fixture(autouse=True)
    def _always(shared):  # noqa: ANN001, ANN202 - a fixture, read by signature
        return shared

    class TestAutoused:
        def test_asks_for_nothing(self) -> None: ...

    return {"shared": shared, "_always": _always, "TestAutoused": TestAutoused}


def _namespace_with_a_camel_case_consumer() -> dict[str, object]:
    """A consumer pytest's ``python_functions`` collects and ``test_`` misses.

    ``python_functions`` is unconfigured in this tree, so pytest's default
    ``test`` *prefix* collects ``testCamelCase``. CARD-218's reading, and
    CARD-219's first one, hard-coded ``test_`` (cycle 1, F-002).
    """

    @pytest.fixture(scope="module")
    def shared() -> str:
        return "the shared render"

    class TestCamel:
        def testCamelCase(self, shared) -> None: ...  # noqa: N802

    return {"shared": shared, "TestCamel": TestCamel}


#: ``(label, namespace builder, the consumer that must be found)``. One row per
#: open shape: hole 1's original four (transitive, inherited, nested,
#: ``usefixtures``) plus the module-mark variant of the fourth, plus the two
#: CARD-219's cycle 1 found still open (``autouse``, and a name the configured
#: prefix collects). Each row is one control, and the loop below runs both arms
#: of it.
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
    ("autouse", _namespace_with_an_autouse_consumer, "TestAutoused::test_asks_for_nothing"),
    (
        "configured name prefix",
        _namespace_with_a_camel_case_consumer,
        "TestCamel::testCamelCase",
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


class TestSharedControls_TheCollectedNameRulesComeFromTheConfig:
    """Which names are tests is pytest's answer, not a prefix written here.

    ADR-0039/R2: a guard's set comes from an authority the runtime can
    enumerate. ``python_functions`` and ``python_classes`` are exactly such an
    authority — ``config.getini`` returns them — and CARD-218's reading, kept
    by CARD-219's first round, hard-coded ``test_`` and ``Test`` instead. The
    cost was measured in cycle 1 (F-002): ``def testCamelCase(self, shared)``
    is collected by pytest and was in no denominator.
    """

    def test_the_fallbacks_are_still_what_this_pytest_collects_by(
        self, request
    ) -> None:
        """The one way a fallback written in the module could go stale.

        :data:`~tests.helpers.shared_fixture_controls.DEFAULT_FUNCTION_PATTERNS`
        exists for callers with no ``config`` in hand (every control in
        :mod:`tests.test_shared_fixture_controls` is one). It is only honest
        while this tree configures neither option, so that is asserted rather
        than assumed: configure either one and this reds, pointing at the
        guards that must then be handed the config's value.
        """
        assert tuple(request.config.getini("python_functions")) == (
            controls.DEFAULT_FUNCTION_PATTERNS
        ), (
            "this tree now configures `python_functions`, so the fallback in "
            "the shared home is no longer what pytest collects by: pass "
            "`config.getini('python_functions')` at every call site of "
            "`declared_consumers`, as "
            "`refuse_unless_every_consumer_is_collected` already does"
        )
        assert tuple(request.config.getini("python_classes")) == (
            controls.DEFAULT_CLASS_PATTERNS
        ), "same for `python_classes`"

    @pytest.mark.parametrize(
        "how, function_patterns, class_patterns",
        [
            ("prefix", ("check",), ("Check",)),
            ("glob", ("check_*",), ("Check*",)),
        ],
    )
    def test_a_configured_pattern_is_honoured_and_the_default_is_not_assumed(
        self, how: str, function_patterns, class_patterns
    ) -> None:
        """The reading really consults its patterns; it has not inlined them.

        A tree that collected ``check_*`` instead of ``test*`` would have
        every one of its consumers outside the denominator. Asserted in both
        directions on one namespace, so a reading that ignored the argument
        fails whichever way it hard-coded it — and once per arm of pytest's
        own matching, because pytest tries a pattern as a prefix *and* as a
        glob and ``check_it`` matches ``check_*`` only the second way.
        """

        @pytest.fixture(scope="module")
        def shared() -> str:
            return "the shared render"

        class CheckThing:
            def check_it(self, shared) -> None: ...

        namespace = {"shared": shared, "CheckThing": CheckThing}

        configured = controls.declared_consumers(
            namespace,
            "shared",
            function_patterns=function_patterns,
            class_patterns=class_patterns,
        )
        defaulted = controls.declared_consumers(namespace, "shared")

        assert configured == {"CheckThing::check_it"}, (
            f"a {how} pattern was not honoured: {sorted(configured)}"
        )
        assert defaulted == set(), (
            "a namespace whose names pytest's default patterns do not collect "
            f"reported consumers anyway: {sorted(defaulted)}"
        )

    def test_the_guard_itself_reads_the_rules_off_the_config(self) -> None:
        """Not just the reading — the **guard** asks the config.

        ``declared_consumers``' patterns are only derived if its caller
        derives them, and the caller that matters is
        ``refuse_unless_every_consumer_is_collected``: it is the default-deny
        guard and the one place in this module where a config exists. Today's
        tree configures neither option, so a guard that went back to a
        hard-coded ``test_`` would behave identically on it and no run over
        this tree could tell — which is why the control hands it a stub
        request whose config says ``check``. Without this, the call site's
        ``getini`` is a mechanism no mutant can kill.

        Both directions on one stub: with the rules the guard is handed, the
        uncollected consumer is named and refused; with pytest's own defaults
        the same namespace declares nothing and the guard answers.
        """

        @pytest.fixture(scope="module")
        def shared() -> str:
            return "the shared render"

        class CheckThing:
            def check_it(self, shared) -> None: ...

        namespace: dict[str, object] = {
            "__name__": "stub.module",
            "shared": shared,
            "CheckThing": CheckThing,
        }

        def stub(functions, classes) -> object:
            return types.SimpleNamespace(
                module=types.SimpleNamespace(__name__="stub.module"),
                session=types.SimpleNamespace(items=[]),
                config=types.SimpleNamespace(
                    getini=lambda name: {
                        "python_functions": list(functions),
                        "python_classes": list(classes),
                    }[name]
                ),
            )

        with pytest.raises(AssertionError) as raised:
            controls.refuse_unless_every_consumer_is_collected(
                stub(("check",), ("Check",)), namespace, "shared"
            )

        assert "CheckThing::check_it" in str(raised.value), (
            "the guard did not read `python_functions`/`python_classes` off "
            "the config it was handed, so a tree collecting by any other name "
            "has consumers outside the denominator this guard divides by "
            "(ADR-0039/R2; CARD-219 cycle 1, F-002)"
        )

        controls.refuse_unless_every_consumer_is_collected(
            stub(controls.DEFAULT_FUNCTION_PATTERNS, controls.DEFAULT_CLASS_PATTERNS),
            namespace,
            "shared",
        )

    def test_an_autouse_fixture_that_does_not_reach_it_makes_no_consumer(
        self,
    ) -> None:
        """``autouse`` widens the denominator only along the fixture graph.

        The over-counting direction of F-002's closure. An ``autouse`` fixture
        is requested by every test in its scope, but only one that
        (transitively) pulls the *shared* fixture in makes those tests
        consumers of it — and an over-counted denominator reds every
        whole-file run, because ``item.fixturenames`` will not back it up.
        """

        @pytest.fixture(scope="module")
        def shared() -> str:
            return "the shared render"

        @pytest.fixture(autouse=True)
        def _always() -> str:
            return "something else entirely"

        class TestAutousedElsewhere:
            def test_asks_for_nothing(self) -> None: ...

        found = controls.declared_consumers(
            {
                "shared": shared,
                "_always": _always,
                "TestAutousedElsewhere": TestAutousedElsewhere,
            },
            "shared",
        )

        assert found == set(), found

    def test_an_autouse_fixture_on_a_class_covers_only_that_class(self) -> None:
        """Scope, which the module-level arm above cannot show.

        pytest applies a class's ``autouse`` fixture to that class's tests and
        to classes nested inside it, and to nothing else. A reading that
        flattened it would declare the other class's tests consumers pytest
        never gives the fixture to.
        """

        @pytest.fixture(scope="module")
        def shared() -> str:
            return "the shared render"

        class TestInside:
            @pytest.fixture(autouse=True)
            def _always(self, shared):  # noqa: ANN001, ANN202
                return shared

            def test_covered(self) -> None: ...

        class TestOutside:
            def test_not_covered(self) -> None: ...

        found = controls.declared_consumers(
            {"shared": shared, "TestInside": TestInside, "TestOutside": TestOutside},
            "shared",
        )

        assert found == {"TestInside::test_covered"}, found


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


def _namespace_holding_a_page_in_a_deque() -> dict[str, object]:
    """A page in a :class:`collections.deque` — a container, but not one of the
    four types the walk listed by hand (cycle 1, F-001: 0 B reported)."""
    return {"__name__": "synthetic", "_RECENT": collections.deque([_Sheet()])}


def _namespace_holding_a_page_on_an_instance() -> dict[str, object]:
    """A page on an ordinary object's attribute (cycle 1, F-001: 0 B reported).

    The cheapest hiding place of the three: ``self.page = page`` in anything a
    module keeps a handle on.
    """

    class _Holder:
        def __init__(self) -> None:
            self.page = _Sheet()

    return {"__name__": "synthetic", "_HOLDER": _Holder()}


def _namespace_holding_a_page_on_a_slotted_instance() -> dict[str, object]:
    """A page on an object with ``__slots__`` and therefore no ``__dict__``.

    An instance-``vars()`` reading has nothing to read here; the collector
    reports the slot values, which is why the walk asks it instead.
    """

    class _Slotted:
        __slots__ = ("page",)

        def __init__(self) -> None:
            self.page = _Sheet()

    return {"__name__": "synthetic", "_SLOTTED": _Slotted()}


def _namespace_holding_a_page_behind_an_unnamed_cache() -> dict[str, object]:
    """An ``@lru_cache`` the walk *meets* but no module-level name declares.

    Cycle 1, F-001: a cache bound inside a list held a whole page bitmap and
    the walk reported 0 B — it refused to enter the wrapper *and*
    ``_caches_of`` never named it, so it was neither measured nor exempt. An
    unnamed cache is nobody's declared allowance, so its contents belong in
    ``by_name``: hence ``exempt=False`` on this row.
    """

    @functools.lru_cache(maxsize=None)
    def sheet_for(key: int) -> _Sheet:
        return _Sheet()

    sheet_for(1)
    return {"__name__": "synthetic", "_CACHES": [sheet_for]}


def _namespace_holding_a_page_on_a_plain_local_class() -> dict[str, object]:
    """A page on a class attribute of a class this module itself defines.

    The walk enters a class when ``python_classes`` would collect it *or* when
    the module being walked is where the class was defined — so the namespace
    here names this module, which is also where ``_Local`` comes from. A class
    imported from elsewhere stays a leaf; that bound is
    ``test_the_fence_holds_at_each_edge_that_could_leave_it``'s fourth arm.
    """

    class _Local:
        KEPT = _Sheet()

    return {"__name__": __name__, "_LOCAL": _Local}


HOLE_TWO_CHANNELS = (
    ("numpy array", _namespace_holding_a_numpy_page, SHEET_BYTES, False),
    ("lru_cache store", _namespace_holding_a_page_behind_a_cache, SHEET_BYTES, True),
    ("Test class attribute", _namespace_holding_a_page_on_a_class, SHEET_BYTES, False),
    ("nested two deep", _namespace_holding_a_page_nested_twice, SHEET_BYTES, False),
    ("deque", _namespace_holding_a_page_in_a_deque, SHEET_BYTES, False),
    ("instance attribute", _namespace_holding_a_page_on_an_instance, SHEET_BYTES, False),
    (
        "slotted instance",
        _namespace_holding_a_page_on_a_slotted_instance,
        SHEET_BYTES,
        False,
    ),
    (
        "unnamed lru_cache",
        _namespace_holding_a_page_behind_an_unnamed_cache,
        SHEET_BYTES,
        False,
    ),
    (
        "a plain class of the module's own",
        _namespace_holding_a_page_on_a_plain_local_class,
        SHEET_BYTES,
        False,
    ),
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

    def test_a_memoryview_held_page_is_counted_once_not_twice(self) -> None:
        """``memoryview`` in ``_SCALAR`` is a mechanism, not an optimisation.

        Cycle 2, F-201. The comment on ``controls._SCALAR`` used to call all
        nine of its types "a cheap short-circuit and **not** a mechanism: the
        collector reports no referents for any of these either". That is true
        of eight of them and **false of ``memoryview``**:
        ``gc.get_referents(memoryview(b"abcdef"))`` returns
        ``[<managedbuffer object>]``, and the collector reaches the view's own
        buffer -- the same pixels -- through it.

        So the entry is load-bearing in the direction that *inflates* a figure
        rather than hiding one, which is why no channel row caught it: remove
        it and a memoryview-held page is measured twice. This is that control,
        and it is what makes the deletion mutant killable. It is kept out of
        :data:`HOLE_TWO_CHANNELS` on purpose -- that table's second assertion
        requires the channel to have been invisible to CARD-218's walk, and
        CARD-218's ``_flat_bytes`` has a memoryview arm, so it measured this
        one at ``SHEET_BYTES`` and not 0 (verified 2026-10-24).
        """
        page = memoryview(bytearray(SHEET_BYTES))
        namespace = {"__name__": "synthetic", "_HELD": [page]}

        found = controls.retained_bitmap_bytes(namespace)

        assert sum(found.by_name.values()) == SHEET_BYTES, (
            f"a page held through a memoryview measures "
            f"{sum(found.by_name.values()):,} B, not the {SHEET_BYTES:,} B it "
            "holds -- if it is exactly double, the walk followed the view's "
            "managedbuffer and counted the same pixels twice, which is what "
            "`memoryview` in `controls._SCALAR` exists to prevent"
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

    @pytest.mark.parametrize(
        "label",
        ["an instance holding a module", "a function's own globals", "an imported class"],
    )
    def test_the_fence_holds_at_each_edge_that_could_leave_it(self, label: str) -> None:
        """The fence, re-asserted at each edge CARD-219's widening opened.

        Asking the collector what *any* object refers to is how three hiding
        places were closed (cycle 1, F-001) — and it is also how a walk starts
        following references out of the module it was asked about. The fence
        that stops it is
        :data:`~tests.helpers.shared_fixture_controls._OPAQUE`: a module, a
        function and a method are never entered, so ``__globals__`` — which
        ``gc.get_referents`` hands over freely, and which *is* another
        module's whole namespace — is unreachable however many instances and
        containers stand in front of it.

        One arm per edge rather than three asserts in one test: a plain pass
        stops at its first failure, so three arms in one body would make a
        surviving mechanism and an unreached assert look the same.

        The third arm is a **declared bound** and not a closure: a page parked
        on the class attribute of a class the walked module did not define is
        invisible, which is the price of not entering every imported class's
        ``vars()``. :func:`~tests.helpers.shared_fixture_controls._step`
        lists it with the rest.
        """
        class _Imported:
            KEPT = _Sheet()

        class _Holder:
            def __init__(self, held: object) -> None:
                self.held = held

        # Both carriers really do have a page behind them, so both arms can
        # fail: a module object whose namespace holds one, and a function
        # whose `__globals__` hold one. Pointing them at this module instead
        # would have made the arms unfailable, since nothing here keeps a page
        # at module level — the shape F-005 was about.
        elsewhere = types.ModuleType("card_219_probe_module")
        elsewhere.PAGE = _Sheet()
        scope: dict[str, object] = {"PAGE": _Sheet()}
        exec("def carrier():\n    return PAGE\n", scope)

        namespaces = {
            "an instance holding a module": {
                "__name__": "synthetic",
                "_H": _Holder(elsewhere),
            },
            "a function's own globals": {
                "__name__": "synthetic",
                "_H": _Holder(scope["carrier"]),
            },
            # `_Imported.__module__` is this module, and the namespace below
            # says it is `"synthetic"` — so the class is an imported one as
            # far as the walk is concerned, which is the bound being measured.
            "an imported class": {"__name__": "synthetic", "_CLS": _Imported},
        }

        found = controls.retained_bitmap_bytes(namespaces[label])

        assert found.by_name == {} and found.by_cache == {}, (
            f"the walk reached page bytes through {label}: {found}. The "
            "fence is what keeps this instrument a reading of one module's "
            "own data rather than of the whole interpreter."
        )


class TestSharedControls_TheCacheAllowanceIsAnExemptionWithAControl:
    """Widening a predicate and granting an exemption are the same edit.

    The widening makes a ``@lru_cache`` store visible for the first time, and
    CARD-218's band file has two that hold **25,192,183 B** between them
    (measured through this instrument 2026-10-24, agreeing with that card's
    own hand-measured 25,192,439 B total once its 256 B of digest is added).
    Those bytes are boolean ink masks and a font file, **not** page pixels, so
    they are not divided into a page bitmap here — the ratio this docstring
    used to give compared 1-byte cells with 3-byte pixels (cycle 1's open
    question, answered in ``retained_bitmap_bytes``' own docstring). Either
    way, "the module retains less than one page bitmap" could not survive the
    widening, and the honest shape is an equality on everything else plus a
    named allowance.

    The allowance is the half that gets forgotten, so it ships with its own
    controls: it admits exactly the module-level stores ``functools``
    produced, nothing else can get into it, and a cache the walk meets without
    a module-level name of its own is measured rather than allowed.
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

    def test_the_bound_on_a_numpy_arrays_contents_is_the_collectors(self) -> None:
        """A **declared bound**, with the premise it rests on asserted.

        The walk cannot see inside a numpy array: not a view's uncropped
        ``.base``, not an object-dtype array's elements. That is not a policy
        this module chose — it is what the collector offers, and the first
        assertion is that premise rather than prose about it. The day numpy
        starts reporting either as a referent, this reds and the bound can be
        closed (the same shape as the pytest-marker control above: a premise
        that would otherwise change silently).

        It matters because of the figure it costs. ``_set_once`` in
        ``tests/test_book_pdf_band.py`` caches 666 **cropped** boolean masks:
        24,435,107 B as views, whose 666 distinct bases hold 110,882,067 B
        (measured 2026-10-24). Only the first number is in
        :attr:`Retention.by_cache`, so that figure is not a ceiling on what
        the cache costs the process.
        """
        base = np.zeros((70, 100, 3), dtype=np.uint8)
        view = base[:10]
        boxed = np.empty(2, dtype=object)
        boxed[0] = _Sheet()
        boxed[1] = _Sheet()

        assert gc.get_referents(view) == [] and gc.get_referents(boxed) == [], (
            "numpy now reports an array's contents to the garbage collector, "
            "so this walk could follow a view to its base and an object array "
            "to its elements — close the bound and restate the 24,435,107 B "
            "cache figure, which understates its base memory 4.5-fold"
        )

        found = controls.retained_bitmap_bytes(
            {"__name__": "synthetic", "_V": view, "_BOXED": boxed}
        )

        assert found.by_name == {"_V": view.nbytes, "_BOXED": boxed.nbytes}, (
            f"{found.by_name}: the walk is meant to report each array's own "
            f"nbytes and nothing behind it — the uncropped {base.nbytes:,} B "
            "base and the two pages in the object array are the bound this "
            "test declares"
        )

    def test_the_same_page_reached_twice_is_counted_once(self) -> None:
        """The walk is over objects, not over paths to them."""
        page = _Sheet()
        namespace = {"__name__": "synthetic", "_KEPT": [page, page, {"again": page}]}

        found = controls.retained_bitmap_bytes(namespace)

        assert found.by_name == {"_KEPT": SHEET_BYTES}, found
