"""CARD-239 -- the guards in ``tests/test_suite_profile.py``, judged from outside.

That module carries CARD-238's two structural guards: no tracked source
reaches the gitignored ``meta/kanban`` timing log, and nothing in the guarded
tree goes quiet on what the host happens to hold. Both of them judge the
tree, and one thing they cannot judge is the module they live in going quiet
*above* them. A module-scope ``pytest.skip(..., allow_module_level=True)``
stops pytest collecting anything in the file, so the guard that would report
it is never collected either. Measured on 2026-10-17 by planting exactly that
mutant: ``tests/test_suite_profile.py`` went from **398 passed** to
``1 skipped in 0.03s``, rc=0 -- the 398 guards gone and the run green. That
is the fresh-worktree case that hid the original defect, and CARD-238's review cycle 3 established it is irreducible from
inside one module: the comparison that would notice is itself one of the
silenced tests. It was recorded as F-308 and carded here, and **a second
module is the only route** (CARD-239, AC-4).

So this module is that second pair of eyes, and the eyes are mutual: the
module-scope rule here is run over ``tests/test_suite_profile.py``, and
``tests/test_suite_profile.py``'s own
``test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones``
runs CARD-238's detector over every guarded source including *this* one. So
a silence planted in either module is reported by the other, and neither is
its own judge. Both directions were measured with a planted mutant, not
reasoned about; the card's worktree notes carry the verdicts.

Two deliberately independent mechanisms, rather than one imported from the
module under test -- the repo's standing preference (CLAUDE.md: "prefer an
independent second implementation over re-deriving a value with the same
function you're testing"), and here it is not a preference but the point: a
guard that consulted the other module's detector would be silenced by the
same edit that silenced it.

* an **import** probe. ``pytest.skip`` raises at module scope, so simply
  importing the guard module by path answers the question without parsing
  anything. It is caught explicitly, because an uncaught ``Skipped`` inside a
  test makes the test *skip* -- which would reproduce the defect in the
  guard against it;
* a **module-scope** AST rule, written here and nowhere else, which is
  **default-deny**: it reports every module-scope idiom that could stop
  collection, including ones nobody in this tree writes
  (``pytest.importorskip``, ``pytestmark``, ``sys.exit``). A new spelling is
  therefore a failing test rather than something the rule quietly does not
  understand. Nothing enumerates the ways a module can go quiet, so
  enumerating what is *allowed* is the only side of it that can be complete.

It also holds two things CARD-239 adds that want a home outside the module
they are about: the deliberate timing-log reader
(``meta/profiling/rank_durations.py --check-log``, AC-6) and the interpreter
floor (AC-3).
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD_MODULE = REPO_ROOT / "tests" / "test_suite_profile.py"
RANKER_PATH = REPO_ROOT / "meta" / "profiling" / "rank_durations.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"
GUIDANCE = REPO_ROOT / "CLAUDE.md"

#: The territories the repo is answerable for, the same two
#: ``tests/test_suite_profile.py`` names. Written out rather than imported,
#: for the reason in the docstring: an import would share the edit.
GUARDED_DIRECTORIES = ("tests", "meta/profiling")

#: The option that reads a timing log on purpose, held as a constant so the
#: structural rule below can look for it by value -- the same deliberate
#: indirection ``LIVE_LOG_STEM`` is in the other module, and for the same
#: reason: a module-level binding is not an invocation, and a rule that
#: flagged one would flag itself.
CHECK_LOG_OPTION = "--check-log"


def _load_by_path(path: Path, name: str) -> ModuleType:
    """Import ``path`` under ``name``, the way the ranker is loaded.

    Registered in ``sys.modules`` before execution, for the reason the other
    module's ``_load_ranker`` gives: ``@dataclass`` resolves annotations
    through ``sys.modules[cls.__module__]``.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, str(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _python_sources() -> list[Path]:
    """Every ``*.py`` under the guarded territories, as this module sees them.

    A plain walk, deliberately. The other module resolves the same question
    through ``git ls-files`` with a manifest and a fallback, which is the
    right answer there -- an untracked scratch file must not decide a verdict
    -- and re-deriving it here would re-derive the thing most worth having a
    second opinion on.

    The two answers differ in both directions and neither is a superset of
    the other: a walk admits an untracked file the tracked list excludes, and
    the tracked list names a file that has been deleted but not staged, which
    a walk cannot see. For *this* rule the walk is the safe one -- it reports
    what is on disk, and a module that is on disk is a module pytest will
    collect -- and that is the whole claim made for it.
    """
    return sorted(
        path
        for directory in GUARDED_DIRECTORIES
        for path in (REPO_ROOT / directory).rglob("*.py")
        if "__pycache__" not in path.parts
    )


#: Module-scope calls that can stop a file being collected, or stop the
#: process. Everything not named here is allowed at module scope; everything
#: named here is reported, under any condition or none.
#:
#: Default-deny, because the alternative does not work. No authority
#: enumerates "the ways a pytest module can go quiet": CARD-238 found five
#: such spellings over five review cycles, each time by a review finding
#: rather than by a test, because each pass enumerated the ones it knew. The
#: list below is of *silencers*, and the claim it makes is the narrow one --
#: these stop collection -- while the completeness claim is carried by the
#: shape of the rule: a module-scope statement this rule does not understand
#: is reported, not ignored.
#:
#: Four members, and the two that are NOT here are a decision rather than an
#: omission. ``pytest.fail`` at module scope raises during collection, which
#: pytest reports as an **error** -- loud, which is the opposite of the
#: property that makes a silence dangerous; and there is no
#: ``pytest.skip_module``, which this set named in its first draft until
#: ``test_every_silencer_it_names_has_a_control`` was red on it. A member
#: nobody can write is the F-403 shape, and it was caught here by the control
#: the rule inherited from CARD-238 rather than by a reviewer.
_MODULE_SCOPE_SILENCERS = frozenset({"skip", "exit", "importorskip", "xfail"})


def _module_scope_silences(
    source: str, silencers: frozenset[str] = _MODULE_SCOPE_SILENCERS
) -> list[tuple[str, str]]:
    """``(what stops it, the condition)`` for every module-scope silence.

    Written from scratch, not from ``_conditional_silences``. It looks at one
    thing that function also looks at and at nothing else it does: the
    statements at module scope, plus the ones directly inside a module-scope
    ``if``/``try``. Decorators, in-body skips and marks on tests are the other
    module's business and are not re-judged here.

    Reported, whatever the condition:

    * a call at module scope whose function's last name component is in
      ``silencers`` (:data:`_MODULE_SCOPE_SILENCERS`) -- ``pytest.skip(...)``,
      ``pytest.importorskip(...)``, ``sys.exit(...)``, an alias of any of
      them, with or without ``allow_module_level``;
    * any binding of ``pytestmark``, which is pytest's documented way to mark
      a whole module and was CARD-238 cycle 1's worst miss.

    Not reported: the same calls inside a function or a class body, which is
    where a test legitimately skips itself and is the other detector's
    territory. ``if TYPE_CHECKING:`` and the like carry no calls and so carry
    no silence.

    ``silencers`` is a parameter rather than a module global the caller
    rebinds, for the reason :class:`Spellings` gives in the other module: a
    test that narrowed a global and restored it in a ``finally`` would be
    shared mutable state in the unit tier.
    """
    tree = ast.parse(source)
    found: list[tuple[str, str]] = []

    def statements_at_module_scope() -> list[tuple[ast.stmt, str]]:
        """Module-scope statements, each with the condition it runs under.

        A compound statement is expanded rather than scanned, so a skip
        inside a module-scope ``if`` is reported once, under that ``if``'s
        condition, instead of twice.

        One exemption, keyed on shape: the body of ``if __name__ ==
        "__main__":`` is not module scope as far as pytest is concerned,
        because pytest imports a module under its own name and that branch
        never runs. Two scripts that live under ``tests/`` --
        ``integration_tests.py`` and ``fixtures/a4_golden/regenerate.py`` --
        call ``sys.exit`` there, and reporting them would have meant either a
        false positive or a baseline entry for something that is not a
        silence. Pinned both ways by
        ``test_the_main_guard_exemption_is_keyed_on_the_guard_and_not_on_exit``.
        """
        out: list[tuple[ast.stmt, str]] = []
        pending: list[tuple[ast.stmt, str]] = [
            (statement, "") for statement in tree.body
        ]
        compound = (ast.If, ast.Try, ast.With)
        while pending:
            statement, condition = pending.pop()
            if isinstance(
                statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                # A skip in a body is the in-body rule's business, and
                # descending here would report every test that skips
                # anything.
                continue
            if isinstance(statement, ast.If) and re.search(
                r"\b__name__\b", ast.unparse(statement.test)
            ):
                continue
            if not isinstance(statement, compound):
                out.append((statement, condition))
            if isinstance(statement, ast.If):
                inner = ast.unparse(statement.test)
                pending.extend(
                    (child, condition or inner)
                    for child in [*statement.body, *statement.orelse]
                )
            elif isinstance(statement, ast.Try):
                pending.extend(
                    (child, condition or "an except/else/finally branch")
                    for handler in statement.handlers
                    for child in handler.body
                )
                pending.extend(
                    (child, condition)
                    for child in [
                        *statement.body, *statement.orelse, *statement.finalbody
                    ]
                )
            elif isinstance(statement, ast.With):
                pending.extend((child, condition) for child in statement.body)
        return out

    for statement, condition in statements_at_module_scope():
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            if any(
                isinstance(target, ast.Name) and target.id == "pytestmark"
                for target in targets
            ):
                found.append(("pytestmark", condition))
        for node in ast.walk(statement):
            if not isinstance(node, ast.Call):
                continue
            name = ast.unparse(node.func).rsplit(".", 1)[-1]
            if name in silencers:
                found.append((f"{name}() at module scope", condition))
    return found


#: Every module-scope silence in the guarded tree. Empty, measured
#: 2026-10-17 over every ``*.py`` under :data:`GUARDED_DIRECTORIES` -- and an
#: equality rather than a ``== []`` assertion for the reason CARD-238's
#: baseline is one: it is red when a new one appears AND when a recorded one
#: is fixed without being struck.
#:
#: Being empty is what makes the rule's default-deny affordable. If a future
#: card needs ``pytest.importorskip`` at module scope, the test goes red and
#: the entry comes here with the reason -- a decision on the record, which is
#: the point of G-4 in both cards.
MEASURED_MODULE_SCOPE_SILENCES: tuple[tuple[str, str, str], ...] = ()


#: Sources whose module scope does go quiet, each measured here. Positive
#: controls for the rule: without them "no module-scope silence exists" would
#: be a sentence nothing could distinguish from a rule that reports nothing.
MODULE_SCOPE_SILENCES: tuple[tuple[str, str], ...] = (
    (
        # The F-308 shape itself: the mutant that silences the guard module
        # including both of its guard classes.
        "pytest's imperative module skip on host state",
        "import pytest\n"
        "if not LOG.exists():\n"
        '    pytest.skip("no log here", allow_module_level=True)\n'
        "def test_x() -> None:\n    assert LOG.read_text()\n",
    ),
    (
        "the same with no condition at all",
        "import pytest\n"
        'pytest.skip("not here", allow_module_level=True)\n'
        "def test_x() -> None:\n    assert True\n",
    ),
    (
        "pytest's documented module mark",
        "import pytest\n"
        'pytestmark = pytest.mark.skipif(not LOG.exists(), reason="absent")\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        "a list of module marks, which is also documented",
        "import pytest\n"
        "pytestmark = [pytest.mark.slow, pytest.mark.skipif(True, reason=\"x\")]\n"
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # Not a spelling anyone in this tree writes, and reported anyway:
        # that is what default-deny means. A module that cannot import its
        # subject does not get to report green.
        "pytest.importorskip at module scope",
        "import pytest\n"
        'mod = pytest.importorskip("nonogram.not_here")\n'
        "def test_x() -> None:\n    assert mod\n",
    ),
    (
        "an aliased module skip",
        "from pytest import skip\n"
        'skip("aliased", allow_module_level=True)\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The condition is not host state and it is still reported: a module
        # that stops collecting is a hole in the gate whatever it is keyed
        # on, and a version gate belongs in the baseline with its reason
        # rather than in a rule's blind spot.
        "a module skip on the interpreter version",
        "import pytest\n"
        "import sys\n"
        "if sys.version_info < (3, 14):\n"
        '    pytest.skip("needs 3.14", allow_module_level=True)\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        "a module skip inside a try/except, which no condition describes",
        "import pytest\n"
        "try:\n"
        "    import nonogram.not_here\n"
        "except ImportError:\n"
        '    pytest.skip("optional", allow_module_level=True)\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        "sys.exit at module scope, which stops more than collection",
        "import sys\n"
        "if not LOG.exists():\n"
        "    sys.exit(0)\n"
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # Nobody writes this either, and it is reported for the same reason
        # `importorskip` is: an xfail at module scope reports green without
        # the tests having run, and the owner's standing rule is that an
        # xfail standing in for a defect blocks a merge.
        "pytest.xfail at module scope",
        "import pytest\n"
        'pytest.xfail("not today")\n'
        "def test_x() -> None:\n    pass\n",
    ),
)


#: Module scopes that are NOT silences, so the rule's width is measured from
#: the other side too. Without these, reporting everything would pass every
#: test above.
NOT_A_MODULE_SCOPE_SILENCE: tuple[tuple[str, str], ...] = (
    (
        "a test that skips itself, which the other detector judges",
        "import pytest\n"
        "def test_x() -> None:\n"
        "    if not LOG.exists():\n"
        '        pytest.skip("absent")\n'
        "    assert True\n",
    ),
    (
        "a skipif mark on a test, likewise",
        "import pytest\n"
        '@pytest.mark.skipif(not LOG.exists(), reason="absent")\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        "a fixture that skips, likewise",
        "import pytest\n"
        "@pytest.fixture\n"
        "def thing() -> int:\n"
        '    pytest.skip("absent")\n'
        "    return 1\n",
    ),
    (
        "a class-level mark, likewise",
        "import pytest\n"
        '@pytest.mark.skipif(True, reason="x")\n'
        "class TestThing:\n"
        "    def test_x(self) -> None:\n        pass\n",
    ),
    (
        "an ordinary module-scope conditional",
        "import sys\n"
        "WINDOWS = sys.platform == \"win32\"\n"
        "SEPARATOR = chr(92) if WINDOWS else '/'\n",
    ),
    (
        "a module-scope import guarded by try/except with no skip in it",
        "try:\n"
        "    import numpy\n"
        "except ImportError:\n"
        "    numpy = None\n",
    ),
    (
        # The `__main__` exemption. A script that lives under tests/ and
        # exits when run directly is not a pytest module going quiet:
        # pytest imports it under its own name and the branch never runs.
        # Two real files do this (`tests/integration_tests.py`,
        # `tests/fixtures/a4_golden/regenerate.py`), which is how the rule
        # found out.
        "sys.exit under a __main__ guard, which pytest never runs",
        "import sys\n"
        "def main() -> int:\n    return 0\n"
        'if __name__ == "__main__":\n'
        "    sys.exit(main())\n",
    ),
)


class TestGuardModule_CannotGoQuietAboveItsOwnGuards:
    """AC-4: the module-scope hole CARD-238 could not close from inside.

    F-308, recorded there and closed here. Two mechanisms, and they fail
    differently on purpose: the import probe answers for the guard module
    specifically and needs no parser, while the AST rule answers for the
    whole guarded tree and needs no import.
    """

    def test_the_guard_module_imports_without_going_quiet(self) -> None:
        # `pytest.skip` raises at module scope, so this is the whole question
        # asked directly. `BaseException` rather than `Exception` because
        # `Skipped` is an `OutcomeException`, which is not an `Exception` --
        # and if it were allowed to propagate out of this test, pytest would
        # report THIS test as skipped. A guard that goes quiet on the thing
        # it guards against is the defect, so it is caught and turned into a
        # failure by hand.
        try:
            module = _load_by_path(GUARD_MODULE, "card239_guard_probe")
        except BaseException as raised:  # noqa: BLE001 - see above
            raise AssertionError(
                f"importing {GUARD_MODULE.name} did not finish: "
                f"{type(raised).__name__}: {raised}. A module-scope "
                "pytest.skip stops pytest collecting the guards in that "
                "file at all, so nothing in it can report this"
            ) from raised
        # And that the file still holds its guards, so a module emptied
        # rather than silenced is reported too. Counted without pytest,
        # which is the independence this module is for.
        classes = [
            name
            for name, value in vars(module).items()
            if name.startswith("Test") and isinstance(value, type)
        ]
        tests = [
            f"{name}.{method}"
            for name in classes
            for method in vars(vars(module)[name])
            if method.startswith("test")
        ]
        assert len(tests) >= 60, (classes, len(tests))
        for guard in (
            "TestSuiteTiming_NoTestReadsTheLiveLog",
            "TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog",
        ):
            assert guard in classes, (guard, classes)

    def test_no_guarded_module_silences_itself_at_module_scope(self) -> None:
        found = tuple(
            sorted(
                (str(path.relative_to(REPO_ROOT)), what, condition)
                for path in _python_sources()
                for what, condition in _module_scope_silences(
                    path.read_text(encoding="utf-8")
                )
            )
        )
        assert found == tuple(sorted(MEASURED_MODULE_SCOPE_SILENCES)), (
            "a module under tests/ or meta/profiling/ stops being collected "
            "on a condition, which takes every guard in that file with it "
            "and reads as a skip rather than as a failure. Either the module "
            "should judge the code instead, or the silence belongs in "
            f"MEASURED_MODULE_SCOPE_SILENCES with the reason: {found}"
        )

    def test_the_walk_sees_both_guarded_trees(self) -> None:
        # Guards this guard: a mistyped directory would make the rule above
        # pass by reading nothing.
        walked = _python_sources()
        assert len(walked) > 100, len(walked)
        assert GUARD_MODULE in walked
        assert RANKER_PATH in walked
        assert Path(__file__).resolve() in walked

    @pytest.mark.parametrize(
        "source", [source for _, source in MODULE_SCOPE_SILENCES],
        ids=[name for name, _ in MODULE_SCOPE_SILENCES],
    )
    def test_every_way_a_module_goes_quiet_is_reported(self, source: str) -> None:
        assert _module_scope_silences(source) != [], source

    @pytest.mark.parametrize(
        "source", [source for _, source in NOT_A_MODULE_SCOPE_SILENCE],
        ids=[name for name, _ in NOT_A_MODULE_SCOPE_SILENCE],
    )
    def test_what_this_rule_must_not_claim_is_not_claimed(
        self, source: str
    ) -> None:
        assert _module_scope_silences(source) == [], source

    def test_the_main_guard_exemption_is_keyed_on_the_guard_and_not_on_exit(
        self,
    ) -> None:
        # The exemption's discriminating control. `sys.exit` under a
        # `__main__` guard is exempt; the *same call* one indentation level
        # out, or under any other condition, is reported. Were the exemption
        # keyed on the call instead, a module could exit on host state and
        # this rule would wave it through -- and `sys.exit` at import makes
        # pytest report an error for the whole session, which is the loudest
        # version of the hole this module exists to close.
        exempt = (
            "import sys\n"
            'if __name__ == "__main__":\n'
            "    sys.exit(0)\n"
        )
        reported = "import sys\nsys.exit(0)\n"
        assert _module_scope_silences(exempt) == []
        assert _module_scope_silences(reported) != []

    def test_every_silencer_it_names_has_a_control(self) -> None:
        # The CARD-238 pattern: a set a guard consults needs a completeness
        # test, and every member needs a control that depends on the
        # membership. Both halves, parametrised from the set itself, so a
        # member added without a control is red on the next run.
        caught = [
            source
            for _, source in MODULE_SCOPE_SILENCES
            if _module_scope_silences(source) != []
        ]
        uncontrolled = sorted(
            name
            for name in _MODULE_SCOPE_SILENCERS
            if not any(re.search(rf"\b{name}\(", source) for source in caught)
        )
        assert uncontrolled == [], (
            "a silencer is named in _MODULE_SCOPE_SILENCERS with no control "
            f"that the rule actually reports it: {uncontrolled}"
        )

    @pytest.mark.parametrize("silencer", sorted(_MODULE_SCOPE_SILENCERS))
    def test_the_control_for_each_silencer_depends_on_the_set(
        self, silencer: str
    ) -> None:
        # And the step past that, which is CARD-238's single most
        # transferable artefact: a control has to be caught WITH its member
        # and missed WITHOUT it. A source caught by the `pytestmark` branch
        # whatever the set holds proves nothing about the set.
        #
        # `fail` and `xfail` are the two members with no silence of their own
        # in this tree, so each gets a generated source rather than a written
        # one -- generated from the member, which is only a control for the
        # mechanism; the set's width is bounded by the completeness rule
        # above, as in the other module.
        narrowed = frozenset(_MODULE_SCOPE_SILENCERS - {silencer})
        generated = (
            "import pytest\n"
            f'pytest.{silencer}("x")\n'
            "def test_x() -> None:\n    pass\n"
        )
        sources = [source for _, source in MODULE_SCOPE_SILENCES] + [generated]
        discriminating = []
        for source in sources:
            if _module_scope_silences(source) == []:
                continue
            if _module_scope_silences(source, silencers=narrowed) == []:
                discriminating.append(source)
        assert discriminating != [], (
            f"every source {silencer} is supposed to be reported by is "
            "reported just as well with it removed from the set, so none of "
            "them measures this member"
        )


class TestCheckLog_TheDeliberateReader:
    """AC-6: ``rank_durations.py --check-log``, over logs the tests construct.

    CARD-238 removed the only thing that would ever notice a malformed line
    in the live log, and the thing it removed had *worked* -- it is how
    CARD-217's bad entry was found. Removing it from the suite was right: a
    test's verdict must not depend on a gitignored file. Having nothing at
    all was the gap, and this is where it closes: a subcommand somebody runs
    on a path they name.

    Everything below is over text these tests build. **No test invokes the
    subcommand**, which
    ``test_no_guarded_source_invokes_the_check_log_subcommand`` asserts
    structurally over the whole guarded tree -- a test that ran it on the
    owner's log would be CARD-238's defect with a new badge. What that leaves
    unexecuted is the argparse wiring, three lines of it, and that is checked
    structurally rather than by running it; the limit is stated rather than
    papered over.
    """

    GOOD = (
        "# a header comment, as the real log carries\n"
        "2026-10-06T17:20:55Z wave-35 full-suite 770s PASS "
        "(6618 passed, 9 skipped, 0 failed)\n"
        "2026-10-15T05:34:34Z wave-39 card-217-profiling-run 931s PASS "
        "(7073 passed, 9 skipped, 0 failed) [131ms/test]\n"
    )
    #: The shape CARD-238 ruled illegal and named its writer for: a bare
    #: trailing note after the rate bracket, outside any parentheses.
    BARE_TRAILING_NOTE = (
        "2026-10-15T09:50:34Z wave-39 card-217-merge-gate 963s PASS "
        "(7156 passed, 9 skipped, 0 failed) [135ms/test] -- the profiling "
        "card's own gate\n"
    )
    #: And the legal one it is a corruption of.
    PARENTHESISED_NOTE = (
        "2026-10-14T19:20:17Z wave-38 card-212-merge-gate 1123s PASS "
        "(7053 passed, 9 skipped, 0 failed) [159ms/test] "
        "(a first attempt on a shared host failed at 1476s)\n"
    )

    @staticmethod
    def _ranker() -> ModuleType:
        return _load_by_path(RANKER_PATH, "card239_ranker")

    def test_a_well_formed_log_is_reported_clean_and_exits_zero(self) -> None:
        lines, status = self._ranker().check_log_report(self.GOOD)
        assert status == 0, lines
        assert "entries: 2" in lines
        assert "malformed: 0" in lines

    def test_a_malformed_line_is_named_and_exits_non_zero(self) -> None:
        lines, status = self._ranker().check_log_report(
            self.GOOD + self.BARE_TRAILING_NOTE
        )
        assert status == 1, lines
        assert "malformed: 1" in lines
        assert any("card-217-merge-gate" in line for line in lines), lines
        # And the entry count does not quietly swallow it: the malformed
        # line is not an entry.
        assert "entries: 2" in lines

    def test_the_legal_trailing_note_is_not_reported(self) -> None:
        # The companion to the case above, and the thing that makes the
        # check worth running: the two shapes differ by two characters, and
        # CARD-238's parser fix was exactly about telling them apart.
        lines, status = self._ranker().check_log_report(
            self.GOOD + self.PARENTHESISED_NOTE
        )
        assert status == 0, lines
        assert "malformed: 0" in lines

    def test_it_reports_how_many_rated_lines_give_their_rate_back(self) -> None:
        # The question CARD-238's review could only answer for the two
        # entries it had in front of it (six bracket-bearing lines, three
        # rate fields). Over a log that parses, the two numbers are equal.
        lines, _ = self._ranker().check_log_report(
            self.GOOD + self.PARENTHESISED_NOTE
        )
        assert "rate recovered: 2 of 2 lines carrying a rate bracket" in lines

    def test_a_rated_line_that_does_not_parse_is_counted_as_a_loss(self) -> None:
        # Non-vacuity of the pair: the bare-trailing-note line carries a
        # rate bracket and yields no fields at all, so the recovery count
        # has to be short. If this test ever reads "1 of 1" the counter is
        # measuring the same thing twice.
        lines, status = self._ranker().check_log_report(self.BARE_TRAILING_NOTE)
        assert status == 1, lines
        assert "rate recovered: 0 of 1 lines carrying a rate bracket" in lines

    def test_an_empty_log_is_clean(self) -> None:
        lines, status = self._ranker().check_log_report("# only a header\n")
        assert status == 0, lines
        assert "entries: 0" in lines

    def test_the_subcommand_is_wired_to_that_function(self) -> None:
        # The three lines no test executes, read instead of run. AC-6 forbids
        # a test invoking the subcommand, so this is the bound and it is
        # stated: the option's registration and its branch are asserted
        # structurally, and `check_log_report` carries the behaviour the
        # tests above measure. A rename that left the option pointing at
        # nothing would be red here; a logic error inside the three lines
        # would not, and that is the limit.
        tree = ast.parse(RANKER_PATH.read_text(encoding="utf-8"))
        main = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        registered = [
            ast.unparse(node)
            for node in ast.walk(main)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func).endswith("add_argument")
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == CHECK_LOG_OPTION
        ]
        assert len(registered) == 1, registered
        # No default path: a default would put the owner's gitignored log's
        # path into a file the AC-1 guard walks, which is review cycle 2's
        # surviving mutant verbatim.
        assert "default=None" in registered[0], registered[0]
        called = [
            ast.unparse(node)
            for node in ast.walk(main)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func).endswith("check_log_report")
        ]
        assert len(called) == 1, called

    def test_no_guarded_source_invokes_the_check_log_subcommand(self) -> None:
        # AC-6's other half. The suite must not depend on this check -- that
        # is the whole point of CARD-238 -- so passing the option anywhere
        # under tests/ or meta/profiling/ is an offence, with one exemption
        # keyed on SHAPE and not on a filename: the string that *registers*
        # the option (`add_argument("--check-log", ...)`) is a definition,
        # and so is a module-level binding of it to a constant, which is how
        # this module holds it. Everything else -- a subprocess argv, a
        # `main([...])` call, a shell string -- is an invocation.
        #
        # Keyed on shape because a filename exemption is borrowable: the
        # ranker is the file that defines the option, and a test added to it
        # tomorrow would inherit the exemption.
        offenders: dict[str, list[str]] = {}
        for path in _python_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            definitions = {
                id(node.args[0])
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and ast.unparse(node.func).endswith("add_argument")
                and node.args
            } | {
                id(node.value)
                for node in tree.body
                if isinstance(node, ast.Assign)
            }
            invocations = sorted(
                {
                    ast.unparse(parent)[:80]
                    for parent in ast.walk(tree)
                    for node in ast.iter_child_nodes(parent)
                    if isinstance(node, ast.Constant)
                    and node.value == CHECK_LOG_OPTION
                    and id(node) not in definitions
                }
            )
            if invocations:
                offenders[str(path.relative_to(REPO_ROOT))] = invocations
        assert offenders == {}, (
            "something under tests/ or meta/profiling/ passes the deliberate "
            "log-reading option, so the suite would be reading the owner's "
            "gitignored log again -- which is the defect CARD-238 removed. "
            f"Run it by hand instead: {offenders}"
        )

    @pytest.mark.parametrize(
        "source",
        [
            'import subprocess\nsubprocess.run(["python", "r.py", "--check-log", "x"])\n',
            'from r import main\nmain(["--check-log", "x"])\n',
            'import os\nos.system("r.py --check-log x")\n',
            'ARGV = ["--check-log", "x"]\nrun(ARGV)\n',
        ],
        ids=["a subprocess argv", "main() directly", "a shell string", "argv in a list"],
    )
    def test_the_invocation_rule_catches_every_way_of_passing_it(
        self, source: str, tmp_path: Path
    ) -> None:
        # The rule above is measured on fabricated sources, the way both
        # guards in the other module are, so it cannot pass by inspecting
        # nothing. The shell-string case is caught because the option is in
        # the string that `os.system` is called with -- a constant that is a
        # call argument and not an `add_argument` definition.
        tree = ast.parse(source)
        definitions = {
            id(node.args[0])
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func).endswith("add_argument")
            and node.args
        } | {id(node.value) for node in tree.body if isinstance(node, ast.Assign)}
        hits = [
            ast.unparse(parent)
            for parent in ast.walk(tree)
            for node in ast.iter_child_nodes(parent)
            if isinstance(node, ast.Constant)
            and CHECK_LOG_OPTION in str(node.value)
            and id(node) not in definitions
        ]
        assert hits != [], source

    def test_the_definition_shape_is_not_an_invocation(self) -> None:
        # The exemption's own control: the registration passes, and the same
        # string one line over in a subprocess argv does not. Without this,
        # the rule could be satisfied by exempting the ranker by name.
        definition = (
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            'p.add_argument("--check-log", default=None)\n'
        )
        tree = ast.parse(definition)
        definitions = {
            id(node.args[0])
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func).endswith("add_argument")
            and node.args
        }
        hits = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and node.value == CHECK_LOG_OPTION
            and id(node) not in definitions
        ]
        assert hits == []


class TestTheInterpreterFloor:
    """AC-3's second clause: the floor is declared in exactly one place.

    ``pyproject.toml`` said ``>=3.9`` and CLAUDE.md said 3.14, so the range
    the suite supports was written down twice and differently -- a
    pre-existing contradiction review cycle 5 flagged while recording F-502.
    **pyproject.toml is authoritative**: it is the machine-readable
    declaration, it is what an installer enforces, and CLAUDE.md is a
    document about it. The floor is 3.14, because that is the interpreter the
    project is developed and run on and the one CLAUDE.md's own setup command
    creates.
    """

    @staticmethod
    def _declared_floor() -> tuple[int, int]:
        requires = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))[
            "project"
        ]["requires-python"]
        match = re.fullmatch(r">=\s*(\d+)\.(\d+)", requires.strip())
        assert match is not None, (
            f"requires-python is {requires!r}; this guard reads a single "
            "'>=X.Y' floor, and a range or a set of specifiers needs it "
            "widened rather than ignored"
        )
        return int(match[1]), int(match[2])

    def test_the_floor_is_declared_in_pyproject_and_followed_by_the_guidance(
        self,
    ) -> None:
        floor = self._declared_floor()
        setup = re.findall(
            r"python(\d+)\.(\d+)\s+-m\s+venv",
            GUIDANCE.read_text(encoding="utf-8"),
        )
        assert setup, "CLAUDE.md no longer shows how to create the venv"
        stated = {(int(major), int(minor)) for major, minor in setup}
        assert stated == {floor}, (
            f"pyproject.toml declares requires-python >= {floor[0]}.{floor[1]} "
            f"and CLAUDE.md's setup uses {sorted(stated)}. The floor is "
            "declared in pyproject.toml and nowhere else; CLAUDE.md follows it"
        )

    def test_the_pypi_classifier_states_the_same_floor(self) -> None:
        # The third place the floor was written. `requires-python` said
        # ">=3.9" and the classifier said "3.9+" while CLAUDE.md said 3.14,
        # so two of the three agreed with each other and not with the
        # interpreter anyone runs. The classifier is PyPI's vocabulary for
        # the same number and has to track it.
        floor = self._declared_floor()
        classifiers = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))[
            "project"
        ]["classifiers"]
        versions = [
            value.rsplit("::", 1)[-1].strip()
            for value in classifiers
            if value.startswith("Programming Language :: Python ::")
        ]
        assert versions == [f"{floor[0]}.{floor[1]}"], (versions, floor)

    def test_this_interpreter_satisfies_the_declared_floor(self) -> None:
        # So the declaration cannot drift above what anyone actually runs.
        assert sys.version_info[:2] >= self._declared_floor(), (
            sys.version_info[:2], self._declared_floor()
        )
