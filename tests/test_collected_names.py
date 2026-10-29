"""Every name in ``tests/`` that declares a test is a name pytest collects.

CARD-294, review cycle 1, finding F-1 — and the reason this is its own module
rather than a class in the file that was defective.

**What happened.** ``tests/test_book_pdf_vector_primitives.py`` declared
``class PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts``,
holding the only control for EC(ADR-0042/R5): a 24-book corpus, a measured
per-page font-byte slope, and its own "a per-page face would be caught"
control. This repository configures no ``python_classes``, so pytest's default
``Test*`` applied and the class collected **zero tests**. The file collected
35 where it should have collected 38 (the figure cycle 1 measured with
``-o python_classes="Test* PropertyTest*"``); the card's "Tests, by node id"
table and
ADR-0042/R5's own comment both cited a node id that did not resolve; and the
round's and the pre-gate's shared headline figure — "145 passed, 0 skipped" —
is exactly what a silently-uncollected class produces. There was no skip, no
collection error and no warning. **A pass count cannot see this defect**,
which is why counting passes harder is not the answer and a guard is.

What this module asserts
------------------------

That no test-declaring name in the tree is uncollectible, where both halves
of that sentence are derived rather than decided here:

* **what pytest collects** comes from pytest's own effective configuration —
  :func:`pytest.Config.getini` for ``python_files``, ``python_classes`` and
  ``python_functions``, plus the ``unittest.TestCase`` exemption pytest
  applies whatever a class is called. Not a copy of the defaults: if
  ``pyproject.toml`` grows a ``python_classes`` tomorrow, this guard moves
  with it and ``PropertyTest_*`` stops being a finding on the same commit it
  stops being a defect (ADR-0039/R2 — a guard's set comes from an enumerable
  authority).
* **what declares a test** is a name beginning ``test`` or ``PropertyTest``,
  case-insensitively, with no leading underscore. That rule is default-deny
  over the 6,348 such names :func:`declaring_names` counts in this tree
  (functions, methods and classes together), and the leading-underscore
  exclusion is not a courtesy: ``_test_members``, ``_test_functions_in`` and
  ``_tests_by_whether_they_execute`` are helpers *about* tests, named with
  Python's own "not public" marker, and a guard that called them defective
  would be a guard nobody could keep green.

The rule is a pure function of source text — :func:`uncollectible_names` —
so the control feeds it a planted defect as a string rather than writing a
broken file into the tree. Both directions are measured:
``test_the_rule_catches_the_defect_it_was_written_for`` plants the exact
cycle-1 spelling and requires it to be found, and the live test requires the
tree to hold none.

What it does **not** reach, named rather than left to look covered
-----------------------------------------------------------------

* **A file pytest never opens.** A name is only checked if its file's
  basename matches ``python_files``, because a name in a module pytest does
  not collect is not claiming to be a collected test.
  :func:`non_collected_test_files` is the second half of that sentence: it
  reports the files under ``testpaths`` that *do* declare module-level
  ``test_*`` functions and are *not* collected, and
  ``test_the_file_pytest_never_opens_is_the_one_known_one`` holds that set
  to the **one** it is now measured to be, with its reason. It held two until
  CARD-301 resolved the second — ``tests/bench_generate.py``, which carried
  NFR-001/AC-037's 5 s p95 gate and never ran it — and the pin shrank in the
  same commit as the fix, because a pin outliving its hole is the
  declaration-outliving-its-hole defect.

  That test was **renamed from
  ``test_the_files_pytest_never_opens_are_the_two_known_ones``** by CARD-301,
  which resolved the second file; this line is here so a ``git grep`` for the
  retired spelling still lands in the live module. CARD-301's first cut kept
  the old name for that ref stability and gave the wrong reason for it, which
  review cycle 1 measured: forge's ``validators/utils.code_search()`` builds
  ``[':(exclude)meta/architecture', ':(exclude)*.md']``, so ``meta/review`` is
  inside the validator's **haystack** and is never a source of ``check:``/
  ``test:`` refs — a review YAML can make a dead ref look alive, but it cannot
  produce a finding when a name it quotes goes away, and neither validator arm
  named this test at all. Nothing mechanical read the name; what read it was a
  reader, to whom "two" over an assertion holding one is the same
  claim-wider-than-its-control defect this whole module exists for. The count
  lives in the assertion, which is where it can be checked.
* **A module silenced above its tests** (a module-scope ``pytest.skip``).
  That is a different defect with its own pair of guards already:
  ``tests/test_guard_integrity.py`` and ``tests/test_suite_profile.py`` watch
  each other for it. This module checks names, not silences, and a module
  skipped at import would be *collected* and so pass here.
* **A test collected but deselected** by a marker, a ``-k`` expression or
  ``pytest_collection_modifyitems``. Those are run-time choices, not names.
"""

from __future__ import annotations

import ast
import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: A name that declares itself a test: ``test_…``, ``Test…`` or
#: ``PropertyTest…``, in any case, with no leading underscore. See the module
#: docstring for why the underscore is excluded.
DECLARES_A_TEST = re.compile(r"(?i)^(property)?test")


def _prefix_or_glob(name: str, options: tuple[str, ...]) -> bool:
    """pytest's own matching rule for ``python_classes``/``python_functions``.

    Not plain :func:`fnmatch.fnmatch`, and getting that wrong is worth a
    comment: pytest's ``PyCollector._matches_prefix_or_glob_option`` treats an
    option as a **prefix** unless it contains one of ``*?[``, in which case it
    is a glob. The shipped defaults are ``("Test",)`` and ``("test",)``, which
    are prefixes and match nothing at all under ``fnmatch``. Reimplementing
    the rule rather than importing the private method is this tree's standing
    preference for a second implementation — and it is checked against the
    real thing by ``test_the_rules_come_from_pytest_and_not_from_this_file``
    and by the parametrised shapes, every one of which was run through pytest
    itself while this was written.
    """
    for option in options:
        if name.startswith(option):
            return True
        if any(character in option for character in "*?[") and fnmatch.fnmatch(name, option):
            return True
    return False


@dataclass(frozen=True)
class CollectionRules:
    """pytest's own answer to "what counts as a test", read from its config.

    Built by :func:`rules` from :func:`pytest.Config.getini` so that this
    module never restates pytest's defaults. ``pyproject.toml`` currently
    sets none of the three, which is precisely the condition F-1 fell into.
    """

    files: tuple[str, ...]
    classes: tuple[str, ...]
    functions: tuple[str, ...]

    def collects_file(self, name: str) -> bool:
        """``python_files`` is a pure glob, matched on the basename."""
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.files)

    def collects_class(self, name: str) -> bool:
        return _prefix_or_glob(name, self.classes)

    def collects_function(self, name: str) -> bool:
        return _prefix_or_glob(name, self.functions)


@dataclass(frozen=True)
class Finding:
    """One name that declares a test and is not collectible."""

    path: str
    line: int
    name: str
    why: str

    def __str__(self) -> str:  # pragma: no cover - only read on a failure
        return f"{self.path}:{self.line} {self.name} — {self.why}"


def rules(config: pytest.Config) -> CollectionRules:
    """pytest's effective collection patterns."""
    return CollectionRules(
        files=tuple(config.getini("python_files")),
        classes=tuple(config.getini("python_classes")),
        functions=tuple(config.getini("python_functions")),
    )


def _is_unittest_case(node: ast.ClassDef) -> bool:
    """Whether ``node`` inherits a name ending ``TestCase``.

    pytest collects a ``unittest.TestCase`` subclass whatever it is called, so
    a class spelled outside ``python_classes`` that inherits one is not a
    defect. Matched by the base's spelling because a static walk cannot
    resolve the import, which is stated rather than hidden: a class inheriting
    something *named* ``TestCase`` that is not one would be missed here.
    """
    for base in node.bases:
        spelled = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if spelled.endswith("TestCase"):
            return True
    return False


def _declaring_methods(node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        child
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        and DECLARES_A_TEST.match(child.name)
    ]


def _check_class(
    node: ast.ClassDef, path: str, rule: CollectionRules, reachable: bool
) -> list[Finding]:
    """Findings in ``node`` and in the classes nested inside it.

    ``reachable`` is whether pytest would descend this far at all: it
    collects a nested class only inside a class it already collected, so an
    inner ``TestSomething`` under an outer ``_Helper`` runs nothing.

    A class is judged only when it **holds** declaring methods. A class whose
    own name reads as a test but holds no test method collects nothing either
    way and is nobody's claim — ``class _ZeroSolutions`` in
    ``tests/test_puzzle_edit_store.py`` is the shape that taught this rule
    the difference: a stub with a nested stub and no tests at all.
    """
    collectible = rule.collects_class(node.name) or _is_unittest_case(node)
    methods = _declaring_methods(node)
    found: list[Finding] = []
    if methods and not (reachable and collectible):
        found.append(
            Finding(
                path,
                node.lineno,
                node.name,
                f"holds {len(methods)} test method(s) that pytest never runs: "
                + (
                    f"the class name matches none of "
                    f"python_classes={list(rule.classes)}"
                    if not collectible
                    else "its enclosing class is not collected"
                ),
            )
        )
    elif methods:
        found.extend(
            Finding(
                path,
                method.lineno,
                f"{node.name}::{method.name}",
                f"reads as a test but matches none of "
                f"python_functions={list(rule.functions)}",
            )
            for method in methods
            if not rule.collects_function(method.name)
        )
        if any(
            isinstance(child, ast.FunctionDef) and child.name == "__init__"
            for child in node.body
        ):
            found.append(
                Finding(
                    path,
                    node.lineno,
                    node.name,
                    "holds test methods and an __init__, which pytest refuses "
                    "to collect (it warns and moves on)",
                )
            )
    for child in node.body:
        if isinstance(child, ast.ClassDef):
            found.extend(_check_class(child, path, rule, reachable and collectible))
    return found


def uncollectible_names(source: str, path: str, rule: CollectionRules) -> list[Finding]:
    """Every name in ``source`` that declares a test pytest will not collect.

    ``path`` is used for the message only. ``source`` is parsed, never
    imported, so a module with an import-time cost or an import-time failure
    is still judged.
    """
    tree = ast.parse(source)
    found: list[Finding] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if DECLARES_A_TEST.match(node.name) and not rule.collects_function(node.name):
                found.append(
                    Finding(
                        path,
                        node.lineno,
                        node.name,
                        f"reads as a test but matches none of "
                        f"python_functions={list(rule.functions)}",
                    )
                )
        elif isinstance(node, ast.ClassDef):
            found.extend(_check_class(node, path, rule, reachable=True))
    return found


def declaring_names(source: str) -> list[str]:
    """Every name in ``source`` that declares a test, collectible or not.

    The non-vacuity floor's input: a walk that stopped finding anything would
    report no findings and read exactly like a clean tree.
    """
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if DECLARES_A_TEST.match(node.name):
                names.append(node.name)
    return names


def collection_roots(config: pytest.Config) -> list[Path]:
    """The directories pytest searches, from ``testpaths``."""
    return [REPO_ROOT / entry for entry in config.getini("testpaths")]


def python_files_under(roots: list[Path]) -> list[Path]:
    return sorted(path for root in roots for path in root.rglob("*.py"))


def non_collected_test_files(roots: list[Path], rule: CollectionRules) -> list[str]:
    """Files under ``roots`` that declare ``test_*`` functions and are skipped.

    "Skipped" in the collection sense: the basename matches no
    ``python_files`` pattern, so a plain ``pytest`` run never opens the file
    and the names in it never run — however much they look like tests.
    """
    found: list[str] = []
    for path in python_files_under(roots):
        # `conftest.py` is a plugin, not a test module: pytest imports it and
        # never collects tests from it, whatever is in it. `tests/conftest.py`
        # defines a *fixture* called `test_db_url`, which is why this
        # exclusion is here and not an oversight.
        if rule.collects_file(path.name) or path.name == "conftest.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and rule.collects_function(node.name)
            for node in tree.body
        ):
            found.append(str(path.relative_to(REPO_ROOT)))
    return sorted(found)


class TestCollectedNames_EveryTestDeclaringNameIsCollectible:
    """The live walk, and the controls that show it can fail."""

    #: The floor. :func:`declaring_names` counted **6,348** across the tree
    #: when this was written; the bound is far below that so ordinary
    #: deletions do not red it, and far above zero so a walk that found
    #: nothing cannot read as a clean tree.
    MIN_DECLARING_NAMES = 5000

    def test_no_name_in_the_tree_declares_a_test_pytest_will_not_collect(
        self, pytestconfig
    ):
        rule = rules(pytestconfig)
        roots = collection_roots(pytestconfig)
        assert roots and all(root.is_dir() for root in roots), roots

        findings: list[Finding] = []
        names = 0
        for path in python_files_under(roots):
            source = path.read_text(encoding="utf-8")
            names += len(declaring_names(source))
            if not rule.collects_file(path.name):
                continue
            findings.extend(
                uncollectible_names(source, str(path.relative_to(REPO_ROOT)), rule)
            )

        assert names >= self.MIN_DECLARING_NAMES, names
        assert findings == [], "\n".join(str(finding) for finding in findings)

    def test_the_rule_catches_the_defect_it_was_written_for(self, pytestconfig):
        """Control: the exact cycle-1 spelling, planted, is reported.

        ADR-0039/R1 spent on the control rather than on the claim. If this
        passed vacuously the live walk above would be measuring nothing, and
        a guard against a silent defect that is itself silent is worse than
        no guard.
        """
        rule = rules(pytestconfig)
        planted = (
            "class PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts:\n"
            "    def test_every_book_in_the_corpus_embeds_the_face_exactly_once(self):\n"
            "        assert True\n"
        )
        findings = uncollectible_names(planted, "tests/test_planted.py", rule)
        assert [finding.name for finding in findings] == [
            "PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts"
        ], findings

    @pytest.mark.parametrize(
        "source, expected",
        [
            pytest.param(
                "def property_check_of_the_slope():\n    assert True\n",
                [],
                id="a helper that does not read as a test",
            ),
            pytest.param(
                "def test_the_slope():\n    assert True\n",
                [],
                id="a module-level test",
            ),
            pytest.param(
                "class TestSlope:\n    def test_it(self):\n        assert True\n",
                [],
                id="a collectible class",
            ),
            pytest.param(
                "def propertyTest_the_slope():\n    assert True\n",
                ["propertyTest_the_slope"],
                id="a module-level property test, uncollectible",
            ),
            pytest.param(
                "class Slope:\n    def test_it(self):\n        assert True\n",
                ["Slope"],
                id="a bare class holding tests",
            ),
            pytest.param(
                "import unittest\n"
                "class PropertyTestSlope(unittest.TestCase):\n"
                "    def test_it(self):\n        assert True\n",
                [],
                id="a TestCase subclass, which pytest collects by type",
            ),
            pytest.param(
                "class TestSlope:\n"
                "    def __init__(self):\n        pass\n"
                "    def test_it(self):\n        assert True\n",
                ["TestSlope"],
                id="a class pytest refuses for its constructor",
            ),
            pytest.param(
                "class TestSlope:\n"
                "    def testing_the_slope(self):\n        assert True\n",
                [],
                id="a method pytest collects because test* is a prefix glob",
            ),
            pytest.param(
                "class TestOuter:\n"
                "    class Inner:\n"
                "        def test_it(self):\n            assert True\n",
                ["Inner"],
                id="a nested class holding tests",
            ),
        ],
    )
    def test_the_rule_on_one_shape_at_a_time(self, source, expected, pytestconfig):
        """Each direction of the rule, caught WITH it and missed WITHOUT it."""
        findings = uncollectible_names(source, "tests/test_planted.py", rules(pytestconfig))
        assert [finding.name for finding in findings] == expected, findings

    def test_the_rules_come_from_pytest_and_not_from_this_file(self, pytestconfig):
        """The authority is pytest's config, which is what keeps this honest.

        Asserted rather than assumed, because the whole value of the guard is
        that it tracks a ``python_classes`` this repository might one day set.
        What is pinned here is the *source* of the patterns — that each is
        non-empty and comes back from ``getini`` — not their values.
        """
        rule = rules(pytestconfig)
        assert rule.files and rule.classes and rule.functions
        # The shipped defaults are prefixes, not globs, which is why
        # `_prefix_or_glob` exists. Pinned so that a future `python_classes`
        # written as a glob is still matched the way pytest matches it.
        assert rule.collects_class("Test")
        assert rule.collects_class("TestAnything")
        assert rule.collects_function("test_anything")
        assert rule.collects_file("test_anything.py")
        # The condition F-1 fell into: nothing in the configuration widens
        # the class prefix, so a bare `PropertyTest_…` collects nothing. If
        # this line ever reds, the configuration changed and the guard has
        # already followed it.
        assert not rule.collects_class("PropertyTest_Anything")

    def test_the_file_pytest_never_opens_is_the_one_known_one(self, pytestconfig):
        """The scope statement above, as an assertion rather than as prose.

        **One file now, and the name says so.** It held two when CARD-294
        wrote it as
        ``test_the_files_pytest_never_opens_are_the_two_known_ones``; CARD-301
        resolved the second and shrank the pin in the same commit, and review
        cycle 1 established that nothing mechanical read the old spelling, so
        the name follows the assertion instead of the history — see the module
        docstring, which records the retired spelling for ``git grep``.

        * ``tests/integration_tests.py`` is a standalone script with its own
          report harness — its ``test_*`` functions take no fixtures and are
          called by its own runner. Not collected, and not meant to be.
        * ``tests/bench_generate.py`` **was** meant to be, and was not: its
          own docstring claimed it ran "inside ``pytest -q`` with the rest of
          the suite" while its three functions, AC-037's NFR-001 5 s p95 gate
          among them, collected nothing. Measured 2026-10-25 and again
          2026-10-29: a bare ``pytest --collect-only`` from the repo root
          collects 9,224 and then 9,570 tests and none was in that file.
          CARD-301 moved the gate to
          ``tests/test_nfr001_generation_time.py``, which the suite does
          open, and left the benchmark as an honest standalone that declares
          no name beginning ``test`` — so it is no longer a file whose names
          claim to run. It is out of this pin because the hole is closed, not
          because the pin was relaxed: a *second* such file still reds here,
          which is this test's standing job.
        """
        found = non_collected_test_files(collection_roots(pytestconfig), rules(pytestconfig))
        assert found == ["tests/integration_tests.py"], found
