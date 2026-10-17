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
* a **module-scope** AST rule, written here and nowhere else. It reports an
  **enumerated set** of silencing spellings, including ones nobody in this
  tree writes (``pytest.importorskip``, ``pytestmark``, ``sys.exit``), and
  everything it does not recognise at module scope it passes -- which it has
  to, because a test module's module scope is legitimately full of imports,
  constants and helper definitions. So the set is where the completeness
  question lives, and it is answered in the two halves it can be answered
  in: pytest's own silencers are a **projection over** ``dir(pytest)``
  (:data:`PYTEST_SURFACE`), so a name pytest offers that nobody has judged
  is a failing test; the routes that are not pytest's are **explicit
  members with reasons** (:data:`_NON_PYTEST_SILENCERS`,
  :data:`_MODULE_SCOPE_SILENCING_BINDINGS`), each measured and each with a
  control that is caught WITH it and missed WITHOUT it. What is left over is
  not implied to be covered: :data:`MEASURED_MODULE_SCOPE_MISSES` names the
  spellings this rule is measured NOT to see, and goes red the day it grows
  past one of them. Review cycle 1 of this card is why all of that is
  written this way: the first draft described the rule as default-deny,
  which it never was, and a module-scope ``raise unittest.SkipTest(...)``
  -- ``1 skipped``, rc=0, the F-308 verdict verbatim -- went unreported.

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


def _check_log_invocations(source: str) -> list[str]:
    """Every place in ``source`` that PASSES :data:`CHECK_LOG_OPTION` on.

    One function, and **the** rule for AC-6's structural half: the guard
    below and both of its control tests call this, so a control cannot be
    green against a predicate that is not deployed. That is review cycle
    1's F-002 and its root cause (RC-1). Before it, all three tests
    re-derived the predicate inline and the positive control's copy was
    strictly wider than the guard's -- ``CHECK_LOG_OPTION in
    str(node.value)`` against ``node.value == CHECK_LOG_OPTION`` -- so the
    "a shell string" control passed against a rule the guard did not run.
    Measured on disk, one mutant per fresh pytest process: a guarded source
    calling ``os.system("python meta/profiling/rank_durations.py
    --check-log meta/kanban/suite-timing.log")`` left the guard **GREEN, 1
    passed**, which is a tracked test shelling out to the deliberate reader
    against the owner's live gitignored log with nothing reporting it.

    The predicate is therefore the wide one -- a **substring** match, not an
    equality -- because a command line is one string and the option is
    inside it. The shape of the module's own idiom, as its sweep row F-8
    says of the other module: six ``git ls-files`` listings.

    Three exemptions, each keyed on SHAPE rather than on a filename -- a
    filename exemption is borrowable, since the ranker is the file that
    *defines* the option and a test added to it tomorrow would inherit the
    exemption -- and each with its own control in
    :data:`NOT_A_CHECK_LOG_INVOCATION`:

    * an argument of ``add_argument(...)``, which registers the option;
    * an argument of ``error(...)`` on a receiver whose unparsed text
      also receives an ``add_argument(...)`` call somewhere in the same
      source. The parser that defines the option is allowed to name it in
      its own usage message, which ``meta/profiling/rank_durations.py``
      does, and the same call on a receiver that registers nothing **is**
      reported -- that control is in :data:`CHECK_LOG_INVOCATIONS`, not
      here. What this exemption is **not**, and review cycle 2 measured
      both halves of it: it is not a check that a parser exists. It is
      keyed on two method *names* and on receiver text, so a
      ``maker().add_argument(...)`` beside a ``maker().error("<the option
      inside a command line>")`` is exempt with no ``ArgumentParser``
      anywhere in the source, and an ``error`` that shells out what it is
      handed is exempt too -- "the exempt shape executes nothing" is a
      property of ``argparse.ArgumentParser``, not of this rule. The bound
      is recorded with a control in :data:`MEASURED_CHECK_LOG_MISSES`;
    * a module-scope binding to a constant (``CHECK_LOG_OPTION =
      "--check-log"``, which is how this module holds it) and a bare string
      expression, i.e. a docstring. Prose about the option is not an
      invocation, and both guarded modules' docstrings mention it by name.
    """
    tree = ast.parse(source)
    #: Receivers that register arguments: the parser that defines the option.
    parsers = {
        ast.unparse(node.func.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
    }
    # A module-scope binding, and every docstring: definitions and prose.
    exempt: set[int] = {
        id(node.value) for node in tree.body if isinstance(node, ast.Assign)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr):
            exempt.add(id(node.value))
            continue
        if not isinstance(node, ast.Call):
            continue
        attribute = (
            node.func.attr if isinstance(node.func, ast.Attribute) else None
        )
        if isinstance(node.func, ast.Name):
            attribute = node.func.id
        receiver = (
            ast.unparse(node.func.value)
            if isinstance(node.func, ast.Attribute)
            else None
        )
        if attribute == "add_argument" or (
            attribute == "error" and receiver in parsers
        ):
            exempt |= {
                id(argument)
                for argument in [
                    *node.args, *(keyword.value for keyword in node.keywords)
                ]
            }
    return sorted(
        {
            ast.unparse(parent)[:80]
            for parent in ast.walk(tree)
            for node in ast.iter_child_nodes(parent)
            if isinstance(node, ast.Constant)
            and CHECK_LOG_OPTION in str(node.value)
            and id(node) not in exempt
        }
    )


#: Sources that DO pass the option, each **built from**
#: :data:`CHECK_LOG_OPTION` rather than written out. Same reason the other
#: module holds :data:`REINTRODUCTIONS` as a module constant: written inline
#: under ``pytest.mark.parametrize(...)`` the option's text would itself be
#: a call argument and this module would report itself -- which is the
#: predicate being wide, working. The ``%s`` indirection is the one
#: ``LIVE_LOG_STEM`` is over there.
#:
#: The third and fourth entries are review cycle 1's surviving mutant: the
#: shell-string forms, which the deployed rule missed while a control
#: certified a copy of it.
CHECK_LOG_INVOCATIONS: tuple[tuple[str, str], ...] = tuple(
    (name, template % CHECK_LOG_OPTION)
    for name, template in (
        (
            "a subprocess argv",
            'import subprocess\n'
            'subprocess.run(["python", "r.py", "%s", "x"])\n',
        ),
        ("main() directly", 'from r import main\nmain(["%s", "x"])\n'),
        (
            "a shell string",
            "import os\n"
            # The destination is spelled PATH and not the owner's log:
            # the other module's AC-1 guard walks this file and reports a
            # source that names the live log, which is that guard
            # working. The shape under test is the shell string, not the
            # path inside it.
            'os.system("python meta/profiling/rank_durations.py %s PATH")\n',
        ),
        (
            "a shell string with shell=True",
            "import subprocess\n"
            'subprocess.run("r.py %s x", shell=True)\n',
        ),
        ("argv in a list", 'ARGV = ["%s", "x"]\nrun(ARGV)\n'),
        (
            "the option inside an f-string command",
            "import os\n"
            'os.system(f"{RANKER} %s {LOG}")\n',
        ),
        (
            # The `error()` exemption's discriminating control: the same
            # call shape on a receiver that registers no arguments is NOT a
            # parser and is reported. Without this the exemption would be
            # borrowable by anything with an `error` method.
            "a message from something that is not an argument parser",
            'reporter.error("ran with %s")\n',
        ),
    )
)

#: And the shapes that are definitions or prose rather than invocations,
#: so the rule's width is measured from the other side too. Without these,
#: reporting every constant would pass every entry above.
NOT_A_CHECK_LOG_INVOCATION: tuple[tuple[str, str], ...] = tuple(
    (name, template % CHECK_LOG_OPTION)
    for name, template in (
        (
            "the add_argument registration",
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            'p.add_argument("%s", default=None)\n',
        ),
        (
            # `meta/profiling/rank_durations.py`'s real usage message, which
            # names the option it has just registered.
            "the parser's own usage message",
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            'p.add_argument("artefact", nargs="?")\n'
            'p.error("give an artefact to rank, or %s PATH")\n',
        ),
        (
            "a module-scope binding to a constant",
            'OPTION = "%s"\n',
        ),
        (
            "a docstring that documents how to run it by hand",
            '"""Run rank_durations.py %s PATH when you want to."""\n'
            "import os\n",
        ),
    )
)

#: And what this rule is measured **not** to see, named rather than left
#: inside the emptiness of its baseline. The same shape
#: :data:`MEASURED_MODULE_SCOPE_MISSES` has, for the reason review cycle 2
#: of this card stated in one sentence and this module had not applied to
#: its own exemptions: *an exemption is a claim, and it needs the same
#: control a set member needs -- caught WITH it, missed WITHOUT it, and the
#: residue recorded as a bound.* Each entry is asserted to still return
#: ``[]`` (``test_the_disclosed_check_log_misses_are_still_misses``), so a
#: route closed without its entry being struck is a failing test.
#:
#: Both are measured against the deployed rule on 2026-10-17, and the first
#: is **carded as CARD-242**, which is where the discriminator that closes
#: it belongs rather than in a further pass here: the sibling rule
#: ``_live_log_references`` in the other module already answers "does this
#: bound name ever reach an executor?" with its taint step, and this rule
#: reimplemented the shape without that half.
#:
#: The bound is **measured non-vacuous**, not merely asserted: the deployed
#: rule returns ``[]`` for the first entry, while the same rule with its
#: module-scope exemption narrowed to value equality -- one of the two
#: closures CARD-242 can take -- returns that constant's whole line. So the
#: day the route closes, the test below is red and this entry is the thing
#: to strike.
MEASURED_CHECK_LOG_MISSES: tuple[tuple[str, str], ...] = tuple(
    (name, template % CHECK_LOG_OPTION)
    for name, template in (
        (
            # F-201. The module-scope binding exemption is keyed on the
            # constant's immediate parent and not on its value, so the
            # shell string that IS caught inline (the third entry of
            # :data:`CHECK_LOG_INVOCATIONS`) becomes invisible the moment
            # it is hoisted into a constant -- the most idiomatic spelling
            # in this repository. Measured end to end, each mutant in its
            # own fresh process: the inline form planted in a guarded
            # module is RED, the hoisted form SURVIVED at 854 passed, rc=0.
            # Open, and CARD-242's to close.
            "the command line hoisted into a module-scope constant",
            "import os\n"
            'CMD = "python meta/profiling/rank_durations.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    os.system(CMD)\n",
        ),
        (
            # F-203, and the real bound of the `error(...)` exemption: two
            # method NAMES and a receiver's unparsed text, with no parser
            # required and nothing stopping the exempt `error` from
            # executing what it is given. Narrow in practice -- it takes an
            # object with an `add_argument`-named method -- and recorded
            # because a bound stated wider than it is, is this card's own
            # subject.
            "an error() on any receiver that an add_argument() names too",
            "import os\n"
            "class Reporter:\n"
            "    def add_argument(self, *names: str) -> None: ...\n"
            "    def error(self, command: str) -> None:\n"
            "        os.system(command)\n"
            "r = Reporter()\n"
            'r.add_argument("--z")\n'
            'r.error("python r.py %s PATH")\n',
        ),
    )
)


KIND_SILENCER = "silencer"
KIND_NOT_A_SILENCER = "not a silencer"


def _pytest_surface() -> frozenset[str]:
    """Every public callable ``dir(pytest)`` offers on this installation.

    The same two mechanical filters :func:`_stdlib_directory_surface` applies
    in the other module, and for the same reasons that can be checked rather
    than taken on trust: a leading underscore is not public API, and a
    non-callable cannot be the function of a call, while every call-shaped
    rule below fires on a *call*. Measured on 2026-10-17 against pytest
    9.1.1: 88 public names, 84 of them callable (``mark``, ``annotations``,
    ``HIDDEN_PARAM`` and ``version_tuple`` are the four that are not, and
    ``pytestmark = pytest.mark.skipif(...)`` is caught by the *binding* rule
    rather than by a call).
    """
    return frozenset(
        name
        for name in dir(pytest)
        if not name.startswith("_") and callable(getattr(pytest, name, None))
    )


#: Every name on that surface, classified, grouped by the reason so the
#: reason is written once and every name carries it.
#:
#: This is review cycle 1's F-001, and it is the shape the *other* module
#: already had: the sets its guards consult are a projection over
#: ``dir(os)``/``dir(os.path)``/``dir(glob)``/``dir(pathlib.Path)``, audited
#: by a completeness test that is red on an unclassified name. The first
#: draft of this module had no equivalent and described itself as
#: "default-deny" instead -- which it was not, and the review measured the
#: cost: a module-scope ``raise unittest.SkipTest(...)`` reports ``1
#: skipped``, rc=0, byte-for-byte the F-308 verdict this card exists to end,
#: and the rule returned ``[]`` for it.
#:
#: ``dir(pytest)`` is a real authority for *pytest's own* module-level
#: silencers, so that half is derived here. The half it is not an authority
#: for is below (:data:`_NON_PYTEST_SILENCERS`).
_PYTEST_CLASSIFICATION: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        KIND_SILENCER,
        "stops this module being collected, or stops the session, without "
        "a failure being reported -- the property that makes a silence "
        "dangerous",
        (
            "exit", "importorskip", "skip", "xfail"
        ),
    ),
    (
        KIND_NOT_A_SILENCER,
        "raises at module scope, which pytest reports as an **error**: "
        "loud, which is the opposite of a silence. This is the member the "
        "first draft of the set carried; "
        "``test_every_silencer_it_names_has_a_control`` was red on it",
        ("fail",),
    ),
    (
        KIND_NOT_A_SILENCER,
        "an exception or warning class. Raising one at module scope is an "
        "error pytest reports loudly, and a warning class is not raised at "
        "all",
        (
            "FixtureLookupError", "PytestAssertRewriteWarning",
            "PytestCacheWarning", "PytestCollectionWarning",
            "PytestConfigWarning", "PytestDeprecationWarning",
            "PytestExperimentalApiWarning", "PytestFDWarning",
            "PytestRemovedIn10Warning", "PytestReturnNotNoneWarning",
            "PytestUnhandledThreadExceptionWarning",
            "PytestUnknownMarkWarning", "PytestUnraisableExceptionWarning",
            "PytestWarning", "UsageError"
        ),
    ),
    (
        KIND_NOT_A_SILENCER,
        "a collection-tree, report, fixture or plugin type pytest "
        "constructs itself; naming it at module scope builds an object and "
        "collects nothing",
        (
            "Cache", "CallInfo", "CaptureFixture", "Class", "CollectReport",
            "Collector", "Config", "Dir", "Directory", "DoctestItem",
            "ExceptionInfo", "ExitCode", "File", "FixtureDef",
            "FixtureRequest", "Function", "HookRecorder", "Item",
            "LineMatcher", "LogCaptureFixture", "Mark", "MarkDecorator",
            "MarkGenerator", "Metafunc", "Module", "MonkeyPatch",
            "OptionGroup", "Package", "Parser", "PytestPluginManager",
            "Pytester", "RaisesExc", "RaisesGroup", "RecordedHookCall",
            "RunResult", "ScopeName", "Session", "Stash", "StashKey",
            "SubtestReport", "Subtests", "TempPathFactory",
            "TempdirFactory", "TerminalReporter", "TestReport",
            "TestShortLogReport", "Testdir", "WarningsRecorder"
        ),
    ),
    (
        KIND_NOT_A_SILENCER,
        "declares or decorates a test, fixture, mark or hook; it adds to "
        "what is collected rather than stopping it",
        (
            "fixture", "freeze_includes", "hookimpl", "hookspec", "param",
            "register_assert_rewrite", "register_fixture", "yield_fixture"
        ),
    ),
    (
        KIND_NOT_A_SILENCER,
        "an assertion, capture or debugging helper; it returns a value or "
        "fails loudly, and neither stops collection",
        (
            "approx", "deprecated_call", "raises", "set_trace", "warns"
        ),
    ),
    (
        KIND_NOT_A_SILENCER,
        "runs pytest as a program: it starts a session rather than stopping "
        "this one from collecting",
        (
            "cmdline", "console_main", "main"
        ),
    ),
)

#: The classification as a mapping, with every name's reason on the record.
#: An exclusion here is a decision somebody can argue with; an omission is
#: red (``test_every_name_pytest_offers_is_classified``).
PYTEST_SURFACE: dict[str, tuple[str, str]] = {
    name: (kind, reason)
    for kind, reason, names in _PYTEST_CLASSIFICATION
    for name in names
}


def _pytest_silencers() -> frozenset[str]:
    """The classified pytest silencers this installation actually offers.

    Intersected with the live surface for the reason ``_guard_set`` gives in
    the other module: a spelling nobody can write cannot be a hole, so a
    name a future pytest drops costs nothing, while the table keeps the
    entry because the table is the record of the decision.

    The direction that is *claimed* is therefore the subset one: a
    KIND_SILENCER name missing from ``dir(pytest)`` is red
    (``test_every_silencer_it_names_is_a_real_pytest_name``), which is what
    catches a typo or an invented member. The other direction is **not**
    claimed: a KIND_NOT_A_SILENCER name absent from an older or newer pytest
    is not reported, because nothing here can measure which pytest version
    introduced which name.
    """
    return (
        frozenset(
            name for name, (kind, _) in PYTEST_SURFACE.items()
            if kind == KIND_SILENCER
        )
        & _pytest_surface()
    )


#: The module-scope silencing routes that are **not** pytest's: explicit
#: members, each with the reason it is one and each measured on 2026-10-17
#: in a real pytest module, not reasoned about. Every one has a control in
#: :data:`MODULE_SCOPE_SILENCES` that is caught WITH the member and missed
#: WITHOUT it (``test_the_control_for_each_silencer_depends_on_the_set``).
#:
#: Why these two are hand-enumerated is **two** reasons and not one, and
#: review cycle 2 of this card measured the difference rather than letting
#: one sentence cover both. Under the same two filters this module applies
#: everywhere (public, callable): ``"_exit" in`` public-callable
#: ``dir(os)`` is ``False``, so ``os._exit`` is genuinely nobody's
#: projection -- but ``"SkipTest" in`` public-callable ``dir(unittest)`` is
#: ``True``, so ``dir(unittest)`` is as much an authority for
#: ``unittest.SkipTest`` as ``dir(pytest)`` is for ``pytest.skip``, and the
#: projection-plus-audit shape one function above was available for it.
#: ``SkipTest`` is a hand-enumerated member **by choice**, not by
#: necessity: one name in one namespace, where a second projection would
#: buy a whole classification table over a module whose other silencing
#: names (``skip``, ``skipIf``, ``skipUnless``) are decorators and whose
#: ``main()`` raises ``SystemExit`` loudly. The cost of that choice is that
#: the unittest half carries no completeness audit, and that is the claim
#: -- not "no ``dir()`` could ever supply one".
#:
#: Matching is on the call's **last name component**, so ``exit`` above
#: covers ``sys.exit`` and a bare ``exit()`` as well as ``pytest.exit``.
_NON_PYTEST_SILENCERS: dict[str, str] = {
    "SkipTest": "unittest.SkipTest raised at module scope. Measured as a "
                "real pytest module: `1 skipped in 0.00s`, rc=0 -- "
                "byte-for-byte the F-308 verdict, and the rule returned [] "
                "for it until review cycle 1 of this card",
    "_exit": "os._exit, which leaves the interpreter without unwinding. "
             "Measured: rc=0 and no output at all -- quieter than the skip",
}

#: The module-scope *bindings* that silence, which are not calls at all and
#: so cannot be derived from any namespace's ``dir()``: a name whose mere
#: assignment at module scope changes what pytest collects. Explicit members
#: with reasons, each with its own control and each discriminating
#: (``test_the_control_for_each_binding_depends_on_the_set``).
_MODULE_SCOPE_SILENCING_BINDINGS: dict[str, str] = {
    "pytestmark": "pytest's documented way to mark a whole module, and "
                  "CARD-238 cycle 1's worst miss",
    "collect_ignore": "conftest's documented way to drop files from "
                      "collection entirely. Measured: the named module is "
                      "not collected, nothing reports it, and the rule "
                      "returned [] for it until review cycle 1",
    "collect_ignore_glob": "the same by pattern rather than by name",
    "__test__": "pytest's own module-level opt-out, and the quietest route "
                "of the four. Measured 2026-10-17 on pytest 9.1.1: a module "
                "carrying `__test__ = False` and two failing guards collects "
                "as `collected 0 items`, `no tests ran`, rc=5 on its own, "
                "and beside one other module as `1 passed in 0.10s`, rc=0 "
                "-- both failures gone and the session green. Planted in a "
                "guarded module of 386 tests it took the run from 854 passed "
                "to 468 with both guard modules green. Quieter than "
                "`collect_ignore`, which only works in a conftest, and "
                "quieter than `raise unittest.SkipTest`, which at least "
                "prints `1 skipped`. Reported on ANY binding of the name, "
                "not only a falsy one: every member of this set is "
                "value-blind, and a value test here would be a fourth "
                "exemption in a module whose review history is about "
                "exemptions. No `__test__` binding exists anywhere in the "
                "guarded tree today, so this is a hole closed before it is "
                "a violation -- the same standing `importorskip` and "
                "`xfail` are reported under. Review cycle 2's F-202",
}

#: The call-shaped silencers the rule consults: pytest's own, derived, plus
#: the routes that are nobody's ``dir()``.
_MODULE_SCOPE_SILENCERS = _pytest_silencers() | frozenset(_NON_PYTEST_SILENCERS)

#: Module scopes this rule is measured **not** to report, in the shape the
#: other module's :data:`MEASURED_STRUCTURAL_MISSES` already uses: each one
#: asserted to still return ``[]``
#: (``test_the_disclosed_module_scope_misses_are_still_misses``), so the
#: bound goes red the day the rule grows past it and the sentence describing
#: it is the thing to edit. These are named rather than implied to be
#: covered -- which is the whole subject of this card, and of review cycle
#: 1's F-001 one module in.
MEASURED_MODULE_SCOPE_MISSES: tuple[tuple[str, str], ...] = (
    (
        # The rule does not descend into function bodies, deliberately: a
        # skip in a body is the other detector's territory and descending
        # would report every test that skips anything. The cost is that a
        # module-scope *call into* such a helper is a silence this rule does
        # not see. Closing it means either resolving the call (a module-local
        # call graph) or reporting every module-scope call, which in a test
        # module reports everything.
        #
        # This is the **local** half only, and saying so is review cycle 2's
        # F-206: the entry below is the same shape through an import, and
        # its reason is a different and wider one.
        "a module-scope call into a local helper that skips",
        "import pytest\n"
        "def _bail() -> None:\n"
        '    pytest.skip("no log here", allow_module_level=True)\n'
        "_bail()\n"
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The silencer reached through a name bound to it first. The binding
        # itself is an attribute, not a call, and the call names the alias --
        # so neither half matches. `from pytest import skip` IS caught (the
        # call's last component is still `skip`, and it has a control); this
        # is the form where the callable changes name.
        "the silencer bound to a new name, then called through it",
        "import pytest\n"
        "quiet = pytest.skip\n"
        'quiet("no log here", allow_module_level=True)\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The helper indirection one import away -- and a **different**,
        # wider reason than the local form above: the body is in another
        # file, so this one would still be missed by a rule that did
        # descend into the bodies it can see. The rule cannot read a body
        # it cannot see. Review cycle 2's F-206.
        "a module-scope call into an imported helper that skips",
        "from tests.helpers.bail import bail\n"
        "bail()\n"
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The binding half written through the namespace dict. The
        # assignment's target is a Subscript and not a Name, so the binding
        # branch never looks at it, and the only call in the statement is
        # `globals()`. Quiet and exotic; measured, not reasoned.
        "a silencing binding written through globals()[...]",
        "import pytest\n"
        'globals()["pytestmark"] = pytest.mark.skipif(True, reason="x")\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The call half fetched by name at run time: the function of the
        # call is itself a call, so there is no last name component for the
        # rule to match. Same family as the alias entry above, resolved one
        # step later.
        "a silencer fetched with getattr and called immediately",
        "import pytest\n"
        'getattr(pytest, "skip")("no log here", allow_module_level=True)\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The one that is an exact alias of an enumerated member: the rule
        # reports `sys.exit(0)` and calls that the loudest version of the
        # hole this module exists to close, and `raise SystemExit(0)` is
        # that same statement spelled as the exception it raises -- the
        # only call is `SystemExit`, which is in no silencer set. Recorded
        # rather than closed because its verdict is the loud one: measured
        # 2026-10-17 as a real pytest module beside a passing one,
        # `INTERNALERROR> SystemExit: 0`, `no tests ran`, rc=3. Nothing
        # about that run reads as green.
        "raise SystemExit(0), the exit spelled as its exception",
        "if not LOG.exists():\n"
        "    raise SystemExit(0)\n"
        "def test_x() -> None:\n    pass\n",
    ),
)


def _module_scope_silences(
    source: str,
    silencers: frozenset[str] = _MODULE_SCOPE_SILENCERS,
    bindings: frozenset[str] = frozenset(_MODULE_SCOPE_SILENCING_BINDINGS),
) -> list[tuple[str, str]]:
    """``(what stops it, the condition)`` for every module-scope silence.

    Written from scratch, not from ``_conditional_silences``. It looks at one
    thing that function also looks at and at nothing else it does: the
    statements at module scope, plus the ones directly inside a module-scope
    ``if``/``try``. Decorators, in-body skips and marks on tests are the other
    module's business and are not re-judged here.

    An **enumerated** rule, stated as such: what is listed is what is
    *reported*, and a module-scope statement it does not understand is
    passed. Reported, whatever the condition:

    * a call at module scope whose function's last name component is in
      ``silencers`` (:data:`_MODULE_SCOPE_SILENCERS` -- pytest's own
      silencers derived from ``dir(pytest)``, plus
      :data:`_NON_PYTEST_SILENCERS`) -- ``pytest.skip(...)``,
      ``pytest.importorskip(...)``, ``sys.exit(...)``, ``os._exit(...)``,
      ``raise unittest.SkipTest(...)``, an alias of any of them, with or
      without ``allow_module_level``;
    * any binding of a name in ``bindings``
      (:data:`_MODULE_SCOPE_SILENCING_BINDINGS`) -- ``pytestmark``,
      ``collect_ignore``, ``collect_ignore_glob``, ``__test__``.

    Not reported: the same calls inside a function or a class body, which is
    where a test legitimately skips itself and is the other detector's
    territory. ``if TYPE_CHECKING:`` and the like carry no calls and so carry
    no silence. And not reported either: the two routes in
    :data:`MEASURED_MODULE_SCOPE_MISSES`, which say so with a control rather
    than leaving it to be inferred from this paragraph.

    Both sets are parameters rather than module globals the caller rebinds,
    for the reason :class:`Spellings` gives in the other module: a test that
    narrowed a global and restored it in a ``finally`` would be shared
    mutable state in the unit tier.
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
            found.extend(
                (target.id, condition)
                for target in targets
                if isinstance(target, ast.Name) and target.id in bindings
            )
        for node in ast.walk(statement):
            if not isinstance(node, ast.Call):
                continue
            name = ast.unparse(node.func).rsplit(".", 1)[-1]
            if name in silencers:
                found.append((f"{name}() at module scope", condition))
    return found


#: Every module-scope silence **this rule reports** in the guarded tree.
#: Empty, measured 2026-10-17 over every ``*.py`` under
#: :data:`GUARDED_DIRECTORIES` -- and an equality rather than a ``== []``
#: assertion for the reason CARD-238's baseline is one: it is red when a new
#: one appears AND when a recorded one is fixed without being struck.
#:
#: The qualifier is review cycle 1's F-001 and it is not pedantry: this
#: baseline is empty of the spellings the rule enumerates, and what the rule
#: does not see is in :data:`MEASURED_MODULE_SCOPE_MISSES` rather than
#: silently inside this emptiness. If a future card needs
#: ``pytest.importorskip`` at module scope, the test goes red and the entry
#: comes here with the reason -- a decision on the record, which is the point
#: of G-4 in both cards.
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
        # Not a spelling anyone in this tree writes, and reported
        # anyway: an enumerated rule reports what it enumerates, whoever
        # does or does not write it. (This comment said "that is what
        # default-deny means" until review cycle 2; the sentence it leaned
        # on was falsified in cycle 1 and corrected everywhere but here.)
        # A module that cannot import its subject does not get to report
        # green.
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
    (
        # Review cycle 1's F-001, the measurement that broke the
        # "default-deny" sentence. Run as a real pytest module this reports
        # `1 skipped in 0.00s`, rc=0 -- byte-for-byte the F-308 verdict the
        # whole card exists to end -- and the rule returned [] for it. Not
        # pytest's API at all, so no `dir()` was ever going to find it;
        # it is an explicit member with its reason instead.
        "unittest.SkipTest raised at module scope",
        "import unittest\n"
        "if not LOG.exists():\n"
        '    raise unittest.SkipTest("no timing log on this host")\n'
        "def test_x() -> None:\n    assert LOG.read_text()\n",
    ),
    (
        # And the quieter sibling: rc=0 with no output at all, measured.
        "os._exit under a host-state condition",
        "import os\n"
        "if not LOG.exists():\n"
        "    os._exit(0)\n"
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The binding route that is not pytest's either: conftest's
        # documented file exclusion. The named module is simply not
        # collected, and nothing says so.
        "conftest's collect_ignore",
        'collect_ignore = ["test_suite_profile.py"]\n',
    ),
    (
        "the same by pattern",
        'collect_ignore_glob = ["test_suite_*.py"]\n',
    ),
    (
        # Review cycle 2's F-202, and the quietest control in this tuple:
        # a module that binds `__test__` falsy is collected as *nothing*.
        # Measured beside one other module: `1 passed`, rc=0, with these
        # two failing guards simply absent -- no skip, no error, no line of
        # output naming the file.
        "pytest's module-level __test__ opt-out",
        "__test__ = False\n"
        "def test_x() -> None:\n    assert False\n"
        "def test_y() -> None:\n    assert False\n",
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
    (
        # The KIND_NOT_A_SILENCER classification, measured from this side.
        # `pytest.fail` at module scope raises during collection, which
        # pytest reports as an ERROR -- loud, and loudness is the opposite
        # of what makes a silence dangerous. The exclusion carries that
        # reason in :data:`_PYTEST_CLASSIFICATION`, and this is the control
        # that makes it a measurement rather than an assertion.
        "pytest.fail at module scope, which errors loudly rather than "
        "silencing",
        "import pytest\n"
        'pytest.fail("loudly")\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # Another classified non-silencer, in the group that *adds* to what
        # is collected. A rule that reported every `pytest.<anything>` call
        # at module scope would report this, and this is a real idiom.
        "a module-scope pytest call that collects more rather than less",
        "import pytest\n"
        'pytest.register_assert_rewrite("tests.helpers")\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The binding rule is keyed on module scope, like the call rule: the
        # same name inside a function is an ordinary local.
        "a local variable that happens to be called collect_ignore",
        "def build() -> list[str]:\n"
        "    collect_ignore = []\n"
        "    return collect_ignore\n",
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
        # And that the import produced the guards the file declares.
        # Counted without pytest, which is the independence this module is
        # for.
        #
        # Review cycle 1, F-003: this used to assert `len(tests) >= 60`
        # against a file that declares 94 test methods (398 collected after
        # parametrisation) while its comment claimed "a module emptied
        # rather than silenced is reported too" -- a floor that permits
        # gutting is not the claim the sentence made. Two assertions now,
        # and each says only what it can:
        #
        #   * the **derived** one, which needs no number: what the import
        #     produced is exactly what the file's own source declares. A
        #     guard that fails to materialise at import -- a class defined
        #     under a condition, a method lost to a conditional `del`, a
        #     name shadowed -- is named rather than counted past;
        #   * a floor, which is a hand-maintained number near the real
        #     count and is stated as that. It catches the file being
        #     *emptied*, where the derived equality cannot (an empty file
        #     declares nothing and so agrees with itself). Deleting guards
        #     is G-2's territory and is enforced where it can be: the
        #     dispatcher `ast`-diffs the test function names against the
        #     base commit. Raise this number when the module grows; it is
        #     not a measurement of anything.
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
        declared = [
            f"{node.name}.{method.name}"
            for node in ast.parse(
                GUARD_MODULE.read_text(encoding="utf-8")
            ).body
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
            for method in node.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
            and method.name.startswith("test")
        ]
        assert sorted(tests) == sorted(declared), (
            "importing the guard module produced a different set of guards "
            "than its source declares, so something in it is conditional on "
            "the import rather than on the code: "
            f"{sorted(set(declared) ^ set(tests))}"
        )
        assert len(tests) >= 90, (classes, len(tests))
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

    # ----------------------------------------------------------------
    # Review cycle 1, F-001: the set's own completeness, in the two halves
    # it can be answered in. Until these existed the only
    # completeness-shaped test ran the CONVERSE direction (every member has
    # a control), which is why it caught `skip_module` and `fail` and could
    # not catch an absent member.
    # ----------------------------------------------------------------

    def test_every_name_pytest_offers_is_classified(self) -> None:
        # The audit this module did not have, and the other one did: red
        # when pytest offers a public callable nobody here has judged, so
        # the next `pytest.skip`-shaped addition is a failing test rather
        # than a quiet hole. Exactly `test_every_spelling_the_stdlib_offers_is_classified`
        # over `dir(os)`, one module across.
        unclassified = sorted(_pytest_surface() - set(PYTEST_SURFACE))
        assert unclassified == [], (
            "pytest offers a public callable PYTEST_SURFACE does not "
            "classify, so nothing says whether it can stop a module being "
            "collected. Classify each one KIND_SILENCER, or "
            f"KIND_NOT_A_SILENCER with the reason it is not one: "
            f"{unclassified}"
        )

    def test_every_classification_carries_a_reason(self) -> None:
        # An exclusion is a decision somebody can argue with only if the
        # reason is written down; this is what stops the table becoming a
        # list of bare names.
        assert {kind for kind, _, _ in _PYTEST_CLASSIFICATION} == {
            KIND_SILENCER, KIND_NOT_A_SILENCER,
        }
        unreasoned = sorted(
            name for name, (_, reason) in PYTEST_SURFACE.items()
            if len(reason.strip()) < 20
        )
        assert unreasoned == [], unreasoned
        for mapping in (_NON_PYTEST_SILENCERS, _MODULE_SCOPE_SILENCING_BINDINGS):
            bare = sorted(
                name for name, reason in mapping.items()
                if len(reason.strip()) < 20
            )
            assert bare == [], bare

    def test_no_pytest_name_is_classified_twice(self) -> None:
        # The grouping writes the reason once per group, so a name in two
        # groups would quietly last-win and carry the wrong reason. The
        # other module's `test_no_spelling_is_classified_twice`.
        seen: dict[str, int] = {}
        for _, _, names in _PYTEST_CLASSIFICATION:
            for name in names:
                seen[name] = seen.get(name, 0) + 1
        assert sorted(name for name, count in seen.items() if count > 1) == []
        assert len(seen) == len(PYTEST_SURFACE)

    def test_every_silencer_it_names_is_a_real_pytest_name(self) -> None:
        # The typo direction, and the only direction that can hold on every
        # pytest version: a KIND_SILENCER name pytest does not offer would
        # sit in the set matching nothing. `skip_module` -- which this set
        # carried in its first draft and which does not exist in pytest at
        # all -- is the member this would have caught.
        #
        # KIND_NOT_A_SILENCER names are exempt deliberately: the table is
        # read on every installation and is allowed to carry names another
        # pytest version offers. That direction is NOT claimed, and
        # `_pytest_silencers`' docstring says so rather than implying it.
        surface = _pytest_surface()
        phantom = sorted(
            name for name, (kind, _) in PYTEST_SURFACE.items()
            if kind == KIND_SILENCER and name not in surface
        )
        assert phantom == [], (
            "a name classified KIND_SILENCER is not on this pytest's public "
            f"callable surface, so nothing can ever match it: {phantom}"
        )

    def test_the_silencer_set_is_derived_and_not_hand_written(self) -> None:
        # The structural half, the way the other module pins the same claim
        # (`test_the_guard_sets_are_derived_and_not_hand_written`): the
        # projection equality cannot fail while the set IS a projection, so
        # the claim that it is one is a separate test that reads this
        # module's own source. Red the day `_MODULE_SCOPE_SILENCERS`
        # becomes a literal frozenset again, which is what it was before
        # review cycle 1.
        tree = ast.parse(Path(__file__).resolve().read_text(encoding="utf-8"))
        assignments = {
            target.id: ast.unparse(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        assert assignments.get("_MODULE_SCOPE_SILENCERS") == (
            "_pytest_silencers() | frozenset(_NON_PYTEST_SILENCERS)"
        ), assignments.get("_MODULE_SCOPE_SILENCERS")

    def test_every_binding_it_names_has_a_control(self) -> None:
        # The same pair of claims the call-shaped half carries, for the
        # half that is not a call: every binding named has a control the
        # rule is measured to report.
        caught = [
            source
            for _, source in MODULE_SCOPE_SILENCES
            if _module_scope_silences(source) != []
        ]
        uncontrolled = sorted(
            name
            for name in _MODULE_SCOPE_SILENCING_BINDINGS
            if not any(
                re.search(rf"^{name}\s*(:[^=]+)?=", source, re.MULTILINE)
                for source in caught
            )
        )
        assert uncontrolled == [], (
            "a silencing binding is named with no control that the rule "
            f"actually reports it: {uncontrolled}"
        )

    @pytest.mark.parametrize(
        "binding", sorted(_MODULE_SCOPE_SILENCING_BINDINGS)
    )
    def test_the_control_for_each_binding_depends_on_the_set(
        self, binding: str
    ) -> None:
        # And the step past that: caught WITH the member, missed WITHOUT
        # it. A source caught through the *call* branch whatever the
        # bindings hold proves nothing about the bindings.
        narrowed = frozenset(_MODULE_SCOPE_SILENCING_BINDINGS) - {binding}
        discriminating = [
            source
            for _, source in MODULE_SCOPE_SILENCES
            if _module_scope_silences(source) != []
            and _module_scope_silences(source, bindings=narrowed) == []
        ]
        assert discriminating != [], (
            f"every source {binding} is supposed to be reported by is "
            "reported just as well with it removed from the bindings"
        )

    @pytest.mark.parametrize(
        "source", [source for _, source in MEASURED_MODULE_SCOPE_MISSES],
        ids=[name for name, _ in MEASURED_MODULE_SCOPE_MISSES],
    )
    def test_the_disclosed_module_scope_misses_are_still_misses(
        self, source: str
    ) -> None:
        # Not an aspiration: the measured bound of this rule, in the shape
        # the other module's `MEASURED_STRUCTURAL_MISSES` has. If the rule
        # grows past one of these, this goes red and the sentence describing
        # the bound is the thing to edit -- which is the only way a bound
        # stated in prose ever gets corrected.
        assert _module_scope_silences(source) == []


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
        # under tests/ or meta/profiling/ is an offence.
        #
        # The rule is :func:`_check_log_invocations`, called and not
        # re-derived: review cycle 1's F-002 was that this test's own
        # positive control reimplemented the predicate inline and wider, so
        # a shell-string invocation was certified by a copy and missed by
        # the guard. The exemptions and their reasons are in that function's
        # docstring, with a control for each.
        offenders = {
            str(path.relative_to(REPO_ROOT)): invocations
            for path in _python_sources()
            if (
                invocations := _check_log_invocations(
                    path.read_text(encoding="utf-8")
                )
            )
        }
        assert offenders == {}, (
            "something under tests/ or meta/profiling/ passes the deliberate "
            "log-reading option, so the suite would be reading the owner's "
            "gitignored log again -- which is the defect CARD-238 removed. "
            f"Run it by hand instead: {offenders}"
        )

    @pytest.mark.parametrize(
        "source", [source for _, source in CHECK_LOG_INVOCATIONS],
        ids=[name for name, _ in CHECK_LOG_INVOCATIONS],
    )
    def test_the_invocation_rule_catches_every_way_of_passing_it(
        self, source: str
    ) -> None:
        # The rule above is measured on fabricated sources, the way both
        # guards in the other module are, so it cannot pass by inspecting
        # nothing -- and it is **the same function** the guard runs, which
        # is the half review cycle 1 found missing. The shell-string cases
        # are caught because the predicate is a substring match: the option
        # is inside the one string `os.system` is called with.
        assert _check_log_invocations(source) != [], source

    @pytest.mark.parametrize(
        "source", [source for _, source in NOT_A_CHECK_LOG_INVOCATION],
        ids=[name for name, _ in NOT_A_CHECK_LOG_INVOCATION],
    )
    def test_the_definition_shape_is_not_an_invocation(
        self, source: str
    ) -> None:
        # The exemptions' own controls, through the same function: the
        # registration, the defining parser's usage message, the module
        # binding and a docstring all pass, while every entry above does
        # not. Without this side the rule could be satisfied by reporting
        # nothing; without the other it could be satisfied by exempting the
        # ranker by name.
        assert _check_log_invocations(source) == [], source

    @pytest.mark.parametrize(
        "source", [source for _, source in MEASURED_CHECK_LOG_MISSES],
        ids=[name for name, _ in MEASURED_CHECK_LOG_MISSES],
    )
    def test_the_disclosed_check_log_misses_are_still_misses(
        self, source: str
    ) -> None:
        # The third side, and the one review cycle 2 found missing: the
        # exemptions' controls above measure what they are *meant* to
        # exempt, and nothing measured what they must not **absorb**. These
        # are the two shapes they do absorb, recorded rather than fixed --
        # the first is CARD-242's, and striking an entry here is how either
        # route gets closed, because closing one without striking it turns
        # this red.
        assert _check_log_invocations(source) == [], source

    def test_the_invocation_rule_is_the_one_the_guard_runs(self) -> None:
        # RC-1, pinned structurally so it cannot come back: every test in
        # this class that asks the invocation question asks it by calling
        # `_check_log_invocations`, and none of them re-derives the
        # predicate from `ast` itself. Read off this module's own source,
        # the way the other module pins its derived sets.
        tree = ast.parse(Path(__file__).resolve().read_text(encoding="utf-8"))
        own_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "TestCheckLog_TheDeliberateReader"
        )
        callers = {
            method.name
            for method in own_class.body
            if isinstance(method, ast.FunctionDef)
            for call in ast.walk(method)
            if isinstance(call, ast.Call)
            and ast.unparse(call.func) == "_check_log_invocations"
        }
        rederivers = sorted(
            method.name
            for method in own_class.body
            if isinstance(method, ast.FunctionDef)
            and method.name not in callers
            and any(
                isinstance(call, ast.Call)
                and ast.unparse(call.func).startswith("ast.")
                for call in ast.walk(method)
            )
            # The wiring test reads the ranker's argparse registration,
            # which is a different question and has to parse to ask it.
            and method.name != "test_the_subcommand_is_wired_to_that_function"
            and method.name != "test_the_invocation_rule_is_the_one_the_guard_runs"
        )
        assert len(callers) >= 3, sorted(callers)
        assert rederivers == [], (
            "a test in this class asks the invocation question by walking "
            "the AST itself instead of calling _check_log_invocations, so a "
            "control can be green against a predicate the guard does not "
            f"run: {rederivers}"
        )


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
