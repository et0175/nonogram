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
import builtins
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
#: reason: a module-level binding whose name reaches nothing that runs it
#: is not an invocation, and a rule that flagged one would flag itself.
#: (``CHECK_LOG_OPTION`` is such a binding, and
#: ``test_no_guarded_source_invokes_the_check_log_subcommand`` walks this
#: file, so the clause after the comma is measured on every run.)
CHECK_LOG_OPTION = "--check-log"

#: CARD-239's claim sweep, which **recorded** the bound CARD-242 closes
#: (rows E-9 and G-16). Read by
#: ``test_the_struck_bound_and_the_closed_route_agree``, which holds the
#: document and the deployed rule to each other: a bound struck in the
#: sweep while the route is still open is red, and a route closed while the
#: sweep still records it as open is red too.
CLAIM_SWEEP = REPO_ROOT / "meta" / "review" / "CARD-239-claim-sweep.md"

#: The two rows of that sweep that recorded F-201: the claim row and its
#: entry in the bounds section.
SWEEP_BOUND_ROWS = ("E-9", "G-16")

#: The verdict those two rows carry once -- and only once -- the route is
#: closed. A sentinel rather than a prose match, so the test reads a
#: decision and not a turn of phrase.
SWEEP_CLOSED_MARKER = "CLOSED by CARD-242"


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


def _with_option(template: str) -> str:
    """``template`` with every ``%s`` standing in for the option.

    The ``%s`` indirection the corpora above use, as a function rather than
    a ``%`` application, because the controls below need the option in two
    places in one source and a bare ``template % CHECK_LOG_OPTION`` takes
    exactly one. Same reason as over there: written out, the option's text
    would itself be a call argument in this file and the rule would report
    its own corpora.
    """
    return template.replace("%s", CHECK_LOG_OPTION)


#: The exemption keys, named once so the table below and the rule itself
#: cannot drift apart on a string literal --
#: ``test_the_invocation_rule_is_the_one_the_guard_runs`` reads the rule's
#: own source and is red if one of these is not branched on in it.
EXEMPT_REGISTRATION = "registration"
EXEMPT_USAGE_MESSAGE = "usage message"
EXEMPT_DEFINITION = "definition"
EXEMPT_PROSE = "prose"

#: The rule's exemptions, one row each, with **both** controls the promoted
#: rule of CARD-239's review cycle 2 asks for: *an exemption is a claim, and
#: it needs the same control a set member needs -- caught WITH it, missed
#: WITHOUT it, and the residue recorded as a bound.*
#:
#: So each row carries
#:
#: * ``absorbed`` -- what the exemption is **for**. Asserted ``[]`` with the
#:   exemption enabled and non-``[]`` with that one key removed from
#:   ``exemptions``, which is the "missed WITH it, caught WITHOUT it" half
#:   and the half that makes the exemption non-vacuous
#:   (``test_every_exemption_absorbs_its_control_only_because_it_is_on``);
#: * ``rejected`` -- what it must **not** absorb, asserted non-``[]`` with
#:   every exemption enabled
#:   (``test_no_exemption_absorbs_what_it_must_not``). CARD-239 shipped the
#:   ``absorbed`` half alone for all four keys, and the measured cost was
#:   F-201: the module-scope row absorbed a real invocation for a whole
#:   card, because nothing stated what it must not take.
#:
#: The ``rejected`` column of the ``definition`` row is review cycle 2's
#: surviving mutant M2, and this card's AC-1.
CHECK_LOG_EXEMPTIONS: tuple[tuple[str, str, str, str, str], ...] = tuple(
    # The reason goes through ``_with_option`` as well: a row that spelled
    # the option out would hold it as a constant inside a nested tuple,
    # which no exemption reaches and the rule therefore reports. Measured
    # by writing it out -- the real-tree guard named this file.
    (
        key,
        name,
        _with_option(reason),
        _with_option(absorbed),
        _with_option(rejected),
    )
    for key, name, reason, absorbed, rejected in (
        (
            EXEMPT_REGISTRATION,
            "the add_argument registration",
            "the call that REGISTERS the option: argparse is handed the "
            "option's text to define it, which is the one thing that has "
            "to name it. Keyed on the arguments of that call and on "
            "nothing else in the source",
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            'p.add_argument("%s", default=None)\n',
            # It must not spread from the call to the file: a source that
            # registers the option AND hoists a command line that is
            # executed is reported for the second thing.
            "import argparse\n"
            "import os\n"
            "p = argparse.ArgumentParser()\n"
            'p.add_argument("%s", default=None)\n'
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    os.system(CMD)\n",
        ),
        (
            EXEMPT_USAGE_MESSAGE,
            "the parser's own usage message",
            "an `error(...)` call whose receiver text also receives an "
            "`add_argument(...)` call somewhere in the same source. "
            "`meta/profiling/rank_durations.py` names the option in the "
            "usage message of the parser that has just registered it. "
            "What this is NOT is a check that a parser exists -- review "
            "cycle 2's F-203 measured both halves, and the bound is "
            "recorded in :data:`MEASURED_CHECK_LOG_MISSES`",
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            'p.add_argument("artefact", nargs="?")\n'
            'p.error("give an artefact to rank, or %s PATH")\n',
            # And it must not spread from that receiver to every `error`:
            # the same call on a receiver that registers nothing is
            # reported even while the real parser's message beside it is
            # exempt.
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            'p.add_argument("artefact", nargs="?")\n'
            'p.error("give an artefact to rank, or %s PATH")\n'
            'reporter.error("ran with %s")\n',
        ),
        (
            EXEMPT_DEFINITION,
            "a module-scope binding to a constant",
            "a module-scope binding whose bound name never reaches "
            'anything that executes it -- `CHECK_LOG_OPTION = "%s"`, '
            "which is how this module holds it, and "
            "`SANDBOX_CONTROL_MODULE` in the other one, which holds a "
            "whole fabricated module's source as text. The dataflow "
            "condition is CARD-242: keyed on the parent alone this "
            "exemption absorbed a command line that was then executed "
            "(F-201, mutant M2, SURVIVED at 854 passed)",
            'OPTION = "%s"\n',
            # F-201 itself: the inline shell string of
            # :data:`CHECK_LOG_INVOCATIONS`, hoisted. The constant's
            # parent says "definition"; `os.system(CMD)` says otherwise,
            # and the taint step is what asks.
            "import os\n"
            'CMD = "python meta/profiling/rank_durations.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    os.system(CMD)\n",
        ),
        (
            EXEMPT_PROSE,
            "a docstring that documents how to run it by hand",
            "a bare string expression: a docstring. Both guarded modules' "
            "docstrings name the option, and `tests/README.md` carries it "
            "as a runnable example",
            '"""Run rank_durations.py %s PATH when you want to."""\n'
            "import os\n",
            # Prose in the same file as an invocation does not cover the
            # invocation.
            '"""Run rank_durations.py %s PATH when you want to."""\n'
            "import os\n"
            'os.system("python r.py %s PATH")\n',
        ),
    )
)

#: The keys the rule consults, as a set it takes as a parameter -- so a
#: control can remove exactly one and measure what that exemption was
#: doing, the way :func:`_module_scope_silences` takes ``silencers`` and
#: ``bindings``. A parameter rather than a global the test rebinds, for the
#: reason that rule's docstring gives: a global narrowed and restored in a
#: ``finally`` is shared mutable state in the unit tier.
_CHECK_LOG_EXEMPTIONS: frozenset[str] = frozenset(
    key for key, *_ in CHECK_LOG_EXEMPTIONS
)

#: And the shapes that are definitions or prose rather than invocations,
#: so the rule's width is measured from the other side too. Without these,
#: reporting every constant would pass every entry above. Derived from the
#: table so a row cannot carry an exemption with no control, and the four
#: ids are the ones CARD-239 shipped.
NOT_A_CHECK_LOG_INVOCATION: tuple[tuple[str, str], ...] = tuple(
    (name, absorbed) for _, name, _, absorbed, _ in CHECK_LOG_EXEMPTIONS
)

#: The calls that **execute** what they are handed, by last name component
#: -- the matching :func:`_module_scope_silences` uses, so ``system``
#: covers ``os.system`` and a bare ``system()`` alike. This is the set the
#: taint step consults: a module-scope binding is a definition until its
#: name reaches one of these.
#:
#: An **enumerated** set, stated as such, and every member carries a
#: control that depends on its membership
#: (``test_the_control_for_each_executor_depends_on_the_set``). It is not a
#: projection over any namespace's ``dir()``: ``dir(os)`` offers 300-odd
#: names of which these few execute, and the classification table that
#: would make such a projection honest is the shape
#: :data:`PYTEST_SURFACE` has for a surface of 88. What is left over is
#: recorded rather than implied to be covered -- an executor reached under
#: a name this set does not hold is an entry in
#: :data:`MEASURED_CHECK_LOG_MISSES`, with its control.
_CHECK_LOG_EXECUTOR_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "hands a string to a shell, which is review cycle 1's surviving "
        "mutant and the shape the hoist of F-201 used",
        ("system", "popen"),
    ),
    (
        "subprocess's documented runners: argv or, with shell=True, one "
        "command line",
        (
            "run", "call", "check_call", "check_output", "Popen",
            "getoutput", "getstatusoutput",
        ),
    ),
    (
        "replaces or spawns the process directly, with no shell in "
        "between -- the family that takes argv as a list, so a hoisted "
        "option reaches it the way `main([...])` does",
        (
            "execv", "execve", "execvp", "execl", "execlp", "spawnv",
            "spawnl", "posix_spawn",
        ),
    ),
    (
        "runs the reader in THIS process: no child, no shell, and the "
        "cheapest spelling of the offence AC-6 forbids. CARD-242's AC-1 "
        "names it",
        ("main",),
    ),
    (
        "runs a FILE as a program, by path rather than by import, and in "
        "this process -- the recorded bound G-19 of CARD-239's sweep until "
        "review cycle 2 of CARD-242 closed it, which took one member and "
        "its reason. The control comes from the generated source in "
        "``test_the_control_for_each_executor_depends_on_the_set``, and the "
        "entry that recorded the bound was struck in the same diff",
        ("run_path",),
    ),
)

#: The flattened set, with every member's reason reachable from it.
_CHECK_LOG_EXECUTORS: dict[str, str] = {
    name: reason
    for reason, names in _CHECK_LOG_EXECUTOR_GROUPS
    for name in names
}
_CHECK_LOG_EXECUTOR_NAMES: frozenset[str] = frozenset(_CHECK_LOG_EXECUTORS)


def _bound_keys(target: ast.AST) -> list[str]:
    """The names a binding target binds, keyed as the taint step keys them.

    A plain name by its identifier and an attribute by its unparsed text
    (``Paths.CMD``), the two keyings the sibling module's
    :func:`_tainted_names` uses -- and tuple unpacking deliberately
    over-approximately, every element of it, because the question is "could
    this name carry the command line".

    A parameter (:class:`ast.arg`) by its own identifier, because a
    parameter default is a binding :func:`_bindings` walks and the name it
    binds is the parameter's.
    """
    if isinstance(target, ast.Starred):
        return _bound_keys(target.value)
    if isinstance(target, (ast.Tuple, ast.List)):
        return [key for element in target.elts for key in _bound_keys(element)]
    if isinstance(target, (ast.Name, ast.Attribute)):
        return [ast.unparse(target)]
    if isinstance(target, ast.arg):
        return [target.arg]
    return []


def _names_within(node: ast.AST) -> set[str]:
    """Every name an expression mentions, keyed the way :func:`_bound_keys` is."""
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(ast.unparse(child))
    return found


def _bindings(node: ast.AST) -> list[tuple[list[ast.AST], ast.AST]]:
    """The ``(targets, value)`` pairs ``node`` binds, for the settling loop.

    **The family statement of the taint step, and the whole of it.** The
    settling loop follows a name backwards only through a node that holds
    BOTH the name it binds and the expression that name takes its value
    from: an assignment (``Assign``, ``AnnAssign``, ``AugAssign``, a walrus
    ``NamedExpr``), a ``for`` or ``async for`` target over the iterable it
    is drawn from, a comprehension's target over its iterable, a ``with
    ... as`` name over its context expression, and a parameter over its
    default. Those node types are enumerated here and each one carries a
    positive control in :data:`CHECK_LOG_INVOCATIONS`.

    Every other way a name can acquire the option's value is a route this
    step does not follow, and the ones measured are recorded in
    :data:`MEASURED_CHECK_LOG_MISSES`: a parameter filled at the CALL site
    rather than from a default, a value returned by a call, an ``except
    ... as`` alias (what it binds comes from the ``raise``, not from the
    handler, so the value is not in this node at all), and a name bound in
    another module. Review cycle 3 of CARD-242's gate found three blind
    routes recorded nowhere -- a parameter default, an augmented
    assignment, and the twin of the ``registration`` exemption. The first
    two are binding forms, so they are walked here; the third is a
    receiver's method name and is recorded. Enumerating the binding nodes
    rather than those instances found two further forms nobody had measured
    (a ``for``/comprehension target and a ``with ... as`` name), which is
    why this reads as a node-type enumeration and not as a list of the
    instances someone happened to notice.

    Over-approximate in the same direction the rest of the step is: a
    ``for`` target takes the taint of the whole iterable, not of one
    element, and a parameter default taints by the parameter's bare name
    module-wide, so a default on any ``def`` whose parameter shares a name
    with an executed one counts. Guessing wide is the safe direction for a
    rule whose job is to report.
    """
    if isinstance(node, ast.Assign):
        return [(node.targets, node.value)]
    if isinstance(node, (ast.AnnAssign, ast.NamedExpr, ast.AugAssign)):
        # `AnnAssign` is the one of the three that can be a bare
        # declaration (`CMD: str`) with no value to follow.
        if node.value is None:
            return []
        return [([node.target], node.value)]
    if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
        return [([node.target], node.iter)]
    if isinstance(node, ast.withitem):
        if node.optional_vars is None:
            return []
        return [([node.optional_vars], node.context_expr)]
    if isinstance(node, ast.arguments):
        # Positional defaults align with the TAIL of the positional
        # parameters, and keyword-only defaults elementwise with the
        # keyword-only ones, where a `None` means "no default".
        positional = [*node.posonlyargs, *node.args]
        return [
            ([parameter], default)
            for parameter, default in (
                *zip(positional[len(positional) - len(node.defaults):],
                     node.defaults),
                *zip(node.kwonlyargs, node.kw_defaults),
            )
            if default is not None
        ]
    return []


def _executed_names(
    tree: ast.Module,
    executors: frozenset[str] = _CHECK_LOG_EXECUTOR_NAMES,
    passes: int | None = None,
) -> frozenset[str]:
    """Names in ``tree`` that reach something which **executes** them.

    CARD-242, and the half :func:`_check_log_invocations` was missing. The
    sibling rule ``_live_log_references`` in ``tests/test_suite_profile.py``
    answers the same shape of question with ``_tainted_names`` /
    ``_string_values``: it follows the strings that *name the log* forward,
    and then asks whether a path position holds one. Here the
    option-bearing side is already answered -- the reporting predicate is a
    substring match over every constant -- so the end that was missing is
    the other one: of the names a module binds, which ones reach a call
    that runs them. Written natively rather than imported, which is this
    repository's standing preference (CLAUDE.md, and
    ``solver/propagate.py``'s ``mask_runs``) and here also the point: the
    two guard modules must not share an edit.

    Over-approximate in the reporting direction, deliberately: *every* name
    mentioned anywhere inside an executor call's arguments counts, so
    ``os.system(" ".join([SH, CMD]))`` taints both. Guessing wide is the
    safe direction for a rule whose job is to report.

    Which bindings the settling loop follows -- and which it does not, so
    the rest is recorded rather than implied -- is :func:`_bindings`, and
    that function's docstring is this step's family statement. Review cycle
    3 of CARD-242 is why it reads as a node-type enumeration: the loop
    walked ``Assign`` / ``AnnAssign`` / ``NamedExpr``, which was neither
    stated nor bounded anywhere, and four more binding forms laundered a
    hoisted command line straight past it.

    The settling loop runs to a **fixpoint**: it re-walks the tree until
    ``executed`` stops growing, so a chain settles backwards from the
    executor however long it is -- ``CMD = "<the command line>"``,
    ``ARGV = ["sh", "-c", CMD]``, ``subprocess.run(ARGV)`` has ``ARGV``
    executed by the call and ``CMD`` by being what ``ARGV`` is built from,
    and that one settles in a single walk. The loop terminates because
    ``executed`` only grows and every member is a name the module mentions,
    so the number of walks is bounded by that finite set.

    A fixed count of passes is what this step shipped with first
    (``range(3)``), and review cycle 2 of CARD-242 measured what the number
    meant rather than what its comment claimed. The inner walk visits
    bindings in **source order**, so a binding already passed in this walk
    is not revisited when ``executed`` grows later in the same walk. A chain
    declared in the idiomatic order -- the command line first, the executor
    last -- therefore settles one link per pass and was reached exactly
    three links deep and no further, while the same chain declared
    executor-first settles in one pass at any depth. The literal ``3`` was
    an undisclosed depth bound on the idiomatic declaration order, and
    nothing in the repository told ``1`` from ``3``: the whole file passed
    at ``range(1)``, ``range(2)``, ``range(3)`` and ``range(4)`` alike, and
    only ``range(0)`` was red. Both halves of that measurement are now a
    control --
    ``test_the_settling_loop_runs_to_a_fixpoint_and_not_to_a_count`` -- and
    the number is gone rather than raised.

    ``passes`` is that control's knob and not the rule's: an integer bounds
    the settling to that many walks, which is exactly what the step did
    before, so a control can measure the fixpoint against the mechanism it
    replaced. The default settles.

    Matching is on the call's **last name component**
    (:data:`_CHECK_LOG_EXECUTORS`), the convention
    :func:`_module_scope_silences` uses one rule up, so ``os.system``, a
    bare ``system(...)`` and ``from os import system`` all match while an
    executor reached by ``getattr`` does not -- that one is recorded in
    :data:`MEASURED_CHECK_LOG_MISSES` with a control.
    """
    executed: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if ast.unparse(node.func).rsplit(".", 1)[-1] not in executors:
            continue
        for argument in [
            *node.args, *(keyword.value for keyword in node.keywords)
        ]:
            executed |= _names_within(argument)
    walked = 0
    while passes is None or walked < passes:
        walked += 1
        before = len(executed)
        for node in ast.walk(tree):
            for targets, value in _bindings(node):
                bound = {
                    key for target in targets for key in _bound_keys(target)
                }
                if bound & executed:
                    executed |= _names_within(value)
        if len(executed) == before:
            break
    return frozenset(executed)


def _check_log_invocations(
    source: str,
    exemptions: frozenset[str] = _CHECK_LOG_EXEMPTIONS,
    executors: frozenset[str] = _CHECK_LOG_EXECUTOR_NAMES,
    passes: int | None = None,
) -> list[str]:
    """Every place in ``source`` this rule SEES passing :data:`CHECK_LOG_OPTION` on.

    "Sees", because review cycle 2 of CARD-239 read the old first line
    ("every place that passes the option on") as the claim it was, and
    measured it wider than the mechanism. What the mechanism does not see
    is :data:`MEASURED_CHECK_LOG_MISSES`, with a control per entry.

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

    The exemptions are a **table** (:data:`CHECK_LOG_EXEMPTIONS`), one row
    per key, and ``exemptions`` is a parameter so a control can remove
    exactly one and measure what that row was doing -- the shape
    :func:`_module_scope_silences` has for its two sets, applied to
    exemptions because review cycle 2 of CARD-239 measured what their
    absence costs. Each row carries both controls: what it is *for*
    (:data:`NOT_A_CHECK_LOG_INVOCATION`, derived from the table) and what
    it must **not absorb**. Each is keyed on SHAPE rather than on a
    filename -- a filename exemption is borrowable, since the ranker is the
    file that *defines* the option and a test added to it tomorrow would
    inherit the exemption:

    * ``registration`` -- an argument of ``add_argument(...)``, which
      registers the option;
    * ``usage message`` -- an argument of ``error(...)`` on a receiver whose unparsed text
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
    * ``definition`` -- a module-scope binding whose bound name **never
      reaches anything that executes it** (``CHECK_LOG_OPTION =
      "--check-log"``, which is how this module holds it, and
      ``SANDBOX_CONTROL_MODULE`` over in the other one, which holds a whole
      fabricated module's source as text and is handed to ``write_text``).
      The dataflow condition is CARD-242 and the whole of it: keyed on the
      binding's parent alone, this row was true of prose and false of a
      command line that is then executed, and review cycle 2 measured the
      cost -- the inline shell string of :data:`CHECK_LOG_INVOCATIONS`
      hoisted into a constant SURVIVED at 854 passed, rc=0, while the
      identical command inline was killed. The question is now asked, by
      :func:`_executed_names`, and the hoisted forms are positive controls;
    * ``prose`` -- a bare string expression, i.e. a docstring. Prose about
      the option is not an invocation, and both guarded modules' docstrings
      mention it by name. It exempts the string and not the file: a
      docstring beside an invocation does not cover the invocation, which
      is that row's ``rejected`` control.

    What the widened rule still cannot see is in
    :data:`MEASURED_CHECK_LOG_MISSES` with a control each, rather than
    inside the emptiness of the baseline.

    ``passes`` is handed straight to :func:`_executed_names` and exists for
    the same reason ``exemptions`` and ``executors`` do: so a control can
    measure one half of the rule against the mechanism it replaced, here
    the settling fixpoint against the fixed three passes CARD-242 first
    shipped. The deployed rule passes it on unset, and no guard sets it.
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
    # A module-scope binding is a definition until its name reaches
    # something that runs it. CARD-242: the taint step, and the only
    # reason this rule tells `CMD = "<a command line>"` + `os.system(CMD)`
    # apart from `SANDBOX_CONTROL_MODULE = "<a module's source>"`.
    exempt: set[int] = set()
    if EXEMPT_DEFINITION in exemptions:
        executed = _executed_names(tree, executors, passes)
        exempt |= {
            id(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and not executed & {
                key for target in node.targets for key in _bound_keys(target)
            }
        }
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr):
            # Every docstring, and nothing else: an `Expr` whose value is
            # not a string carries no constant this rule reports.
            if EXEMPT_PROSE in exemptions:
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
        if (
            EXEMPT_REGISTRATION in exemptions and attribute == "add_argument"
        ) or (
            EXEMPT_USAGE_MESSAGE in exemptions
            and attribute == "error"
            and receiver in parsers
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
#: The two four-deep chains below, named once so the fixpoint control can
#: fetch its two sources out of this corpus rather than holding a second
#: copy of them: the sources a control measures have to be the sources the
#: corpus asserts are reported, or the two can drift apart.
CHAIN_SECOND_CONSTANT = "a hoisted command line reached through a second constant"
DEEP_CHAIN_FORWARD = "a four-deep chain declared forwards, the idiomatic order"
DEEP_CHAIN_REVERSE = "the same four-deep chain declared executor-first"

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
        # ------------------------------------------------------------------
        # CARD-242, AC-1: the same four executions with the command line
        # **hoisted** into a module-scope constant first. The first of them
        # is review cycle 2's mutant M2 -- measured SURVIVING at 854
        # passed, rc=0, while M3 (the identical command inline, the third
        # entry above) was KILLED. Measured again at function level against
        # the rule as CARD-239 left it, before the taint step: all four
        # returned ``[]``. What catches them is
        # :func:`_executed_names`, and the control that it is the taint
        # step catching them rather than some other half of the rule is
        # ``test_the_hoisted_command_is_caught_by_the_taint_step``.
        # ------------------------------------------------------------------
        (
            "a shell string hoisted into a module-scope constant",
            "import os\n"
            # The destination is spelled PATH here too, and for the same
            # reason the inline shell string above gives.
            'CMD = "python meta/profiling/rank_durations.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    os.system(CMD)\n",
        ),
        (
            "a hoisted shell string handed to subprocess with shell=True",
            "import subprocess\n"
            'CMD = "r.py %s x"\n'
            "def _never_called() -> None:\n"
            "    subprocess.run(CMD, shell=True)\n",
        ),
        (
            "a hoisted option inside a subprocess argv list",
            "import subprocess\n"
            'OPTION = "%s"\n'
            "def _never_called() -> None:\n"
            '    subprocess.run(["python", "r.py", OPTION, "x"])\n',
        ),
        (
            "a hoisted option passed to main() in this process",
            "from r import main\n"
            'OPTION = "%s"\n'
            "def _never_called() -> None:\n"
            '    main([OPTION, "x"])\n',
        ),
        (
            # The chain, and the control for the settling loop existing at
            # all: the executor is handed `ARGV`, and `CMD` is only what
            # `ARGV` is built from. Measured, this entry is the single
            # failure when the loop is taken away altogether (CARD-242's
            # mutant M-C, `range(3)` -> `range(0)`). What it is NOT is a
            # control for the number of passes: it is reported at one pass
            # exactly as at three, because `ARGV` is bound after `CMD` and
            # one walk in source order reaches both. The control for the
            # loop running to a **fixpoint** is the four-deep forward chain
            # below -- review cycle 2's F-001.
            CHAIN_SECOND_CONSTANT,
            "import subprocess\n"
            'CMD = "python r.py %s PATH"\n'
            'ARGV = ["sh", "-c", CMD]\n'
            "def _never_called() -> None:\n"
            "    subprocess.run(ARGV)\n",
        ),
        (
            # CARD-242 review cycle 2: the route recorded as bound G-19,
            # closed by one member. The source is the one the struck entry
            # of :data:`MEASURED_CHECK_LOG_MISSES` held, unchanged, so the
            # strike and the closure are the same two lines read twice.
            "an executor the set now enumerates, by path",
            "import runpy\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    runpy.run_path(CMD)\n",
        ),
        (
            # ------------------------------------------------------------
            # CARD-242 review cycle 2, F-001. The settling loop's depth,
            # in the declaration order every module is actually written
            # in: the command line first, the executor last. Four links,
            # so three passes reach `C1` and stop one short of the
            # constant -- measured, and the asymmetry measured with it in
            # `test_the_settling_loop_runs_to_a_fixpoint_and_not_to_a_count`.
            # ------------------------------------------------------------
            DEEP_CHAIN_FORWARD,
            "import subprocess\n"
            'C0 = "python r.py %s PATH"\n'
            "C1 = [C0]\n"
            "C2 = [C1]\n"
            "C3 = [C2]\n"
            "ARGV = [C3]\n"
            "def _never_called() -> None:\n"
            "    subprocess.run(ARGV)\n",
        ),
        (
            # The same chain, same depth, declared the other way round:
            # one walk in source order follows it end to end, so a fixed
            # pass count never bit this order and the fixed count's bound
            # was a property of the *idiomatic* one. Both are reported now.
            DEEP_CHAIN_REVERSE,
            "import subprocess\n"
            "ARGV = [C3]\n"
            "C3 = [C2]\n"
            "C2 = [C1]\n"
            "C1 = [C0]\n"
            'C0 = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    subprocess.run(ARGV)\n",
        ),
        # ------------------------------------------------------------------
        # CARD-242 review cycle 3. One control per binding node
        # :func:`_bindings` walks, because the settling loop followed
        # ``Assign`` / ``AnnAssign`` / ``NamedExpr`` only and every other
        # way a name acquires the command line was a route nothing saw and
        # nothing recorded -- the same statement-of-completeness defect as
        # F-001 and the sweep's G-16, one table further in. Each of the six
        # below was measured ``[]`` against the deployed rule before the
        # loop learned its node type, and the node types are enumerated in
        # :func:`_bindings` rather than listed as these instances.
        # ------------------------------------------------------------------
        (
            "a hoisted command line reached through a parameter default",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called(command: str = CMD) -> None:\n"
            "    os.system(command)\n",
        ),
        (
            "a hoisted command line built up by an augmented assignment",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            'ARGV = ""\n'
            "ARGV += CMD\n"
            "def _never_called() -> None:\n"
            "    os.system(ARGV)\n",
        ),
        (
            "a hoisted command line drawn from a for-loop target",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    for command in [CMD]:\n"
            "        os.system(command)\n",
        ),
        (
            # The same node type's async spelling, controlled rather than
            # assumed: `ast.AsyncFor` shares `_bindings`' branch with
            # `ast.For`, and a branch covering a node type no control
            # exercises is a coverage claim with no failing control --
            # ADR-0039/R1, which is the rule this card applies.
            "a hoisted command line drawn from an async for target",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "async def _never_called() -> None:\n"
            "    async for command in _stream(CMD):\n"
            "        os.system(command)\n",
        ),
        (
            "a hoisted command line drawn from a comprehension target",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    [os.system(command) for command in [CMD]]\n",
        ),
        (
            "a hoisted command line bound by a with ... as name",
            "import os\n"
            "import contextlib\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    with contextlib.nullcontext(CMD) as command:\n"
            "        os.system(command)\n",
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
#: Every entry is measured against the deployed rule. The **first** of them
#: is CARD-239's -- the ``error(...)`` receiver, sweep row G-11 -- and
#: **every entry after it** is CARD-242's: six its build pass added and
#: three its review cycle 3 measured, all 2026-10-17. No total is written
#: out, because the table is the enumeration and each entry's own comment
#: names the cycle that measured it -- an earlier wording here said two
#: where the table held one, and the card's AC-6 line said six where it
#: held seven. CARD-239's
#: other entry, *the command line hoisted into a module-scope constant*
#: (review cycle 2's F-201 and mutant M2), is **struck**: that is why its
#: share of this table is one row and not the two an earlier wording of
#: this comment claimed. That route is closed by :func:`_executed_names`,
#: it is a positive control in :data:`CHECK_LOG_INVOCATIONS` in four
#: shapes, and the bound came out in the same diff
#: (``test_the_struck_bound_and_the_closed_route_agree`` holds the two to
#: each other, and to the sweep row that recorded it).
#:
#: Review cycle 2 of CARD-242 moved one more and added none. ``runpy.run_path``
#: is now a member of :data:`_CHECK_LOG_EXECUTORS`, so the instance that
#: recorded "an executor this set does not enumerate" is closed and sits in
#: the positive controls; the **family** is not closed with it, and the
#: entry keeps an instance measured still missed (``pty.spawn``). What that
#: cycle did NOT have to record is a depth: the settling loop runs to a
#: fixpoint, so a chain of any length in either declaration order settles,
#: and the bound the old fixed pass count left is gone rather than
#: disclosed (``test_the_settling_loop_runs_to_a_fixpoint_and_not_to_a_count``).
#:
#: Review cycle 3 added three, and found them by enumerating the binding
#: nodes the settling loop walks instead of the routes anyone had thought
#: of: the loop followed ``Assign`` / ``AnnAssign`` / ``NamedExpr`` only,
#: so a parameter default, an augmented assignment, a ``for`` or
#: comprehension target and a ``with ... as`` name each laundered a hoisted
#: command line past it, measured ``[]`` and recorded nowhere. Those are
#: **closed**, with a control each; what the enumeration left over is here.
#:
#: **The family, in one sentence:** the step follows a name backwards only
#: through a node that holds both the name and the expression it takes its
#: value from (:func:`_bindings` enumerates them), so every other way a
#: name can acquire the command line is a route it cannot see -- a
#: parameter filled at the call site, a value returned by a call, an
#: ``except ... as`` alias, a name bound in another module, or an executor
#: or receiver reached under a name the step cannot resolve. Each entry
#: below is one of those, measured by calling the deployed rule on exactly
#: the source it holds.
MEASURED_CHECK_LOG_MISSES: tuple[tuple[str, str], ...] = tuple(
    # Through :func:`_with_option` rather than a ``%`` application, because
    # the last entry holds the option in two halves on purpose and a
    # ``template % CHECK_LOG_OPTION`` takes exactly one ``%s``.
    (name, _with_option(template))
    for name, template in (
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
        (
            # The executor under another name. The taint step matches a
            # call's last name component, so the call `EXECUTE(CMD)` names
            # nothing in :data:`_CHECK_LOG_EXECUTORS` and the binding
            # `EXECUTE = os.system` is an attribute, not a call -- neither
            # half matches. Exactly the sibling rule's "the silencer bound
            # to a new name, then called through it", one module across.
            "the executor reached through an alias",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "EXECUTE = os.system\n"
            "def _never_called() -> None:\n"
            "    EXECUTE(CMD)\n",
        ),
        (
            # And the same family resolved one step later: the function of
            # the call is itself a call, so there is no last name
            # component to match. The sibling's `getattr(pytest, "skip")`
            # entry, verbatim in shape.
            "the executor fetched with getattr and called immediately",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            '    getattr(os, "system")(CMD)\n',
        ),
        (
            # An executor the enumerated set does not hold. The set is
            # enumerated and says so, so this is its bound rather than a
            # defect, and closing one instance of it is adding a member
            # with a reason -- which is what review cycle 2 of CARD-242 did
            # to the instance this entry used to hold (`runpy.run_path`,
            # sweep row G-19, now a member and a positive control below).
            # The FAMILY is unchanged by that, so it keeps an instance that
            # is measured still missed: `pty.spawn` hands what it is given
            # to `execlp`, and `spawn` is not one of the set's `spawnv` /
            # `spawnl` / `posix_spawn`. Recorded rather than closed,
            # because a set closed around the instance someone happened to
            # record is the F-001 mistake one table across.
            "an executor this set does not enumerate",
            "import pty\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    pty.spawn(CMD)\n",
        ),
        (
            # The executor one function call away. The step does not
            # resolve a module-local call graph, which is the same bound
            # the sibling module records for a module-scope call into a
            # local helper -- and descending would mean deciding what any
            # local wrapper does with what it is handed.
            "the executor behind a local wrapper function",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _run_it(command: str) -> None:\n"
            "    os.system(command)\n"
            "def _never_called() -> None:\n"
            "    _run_it(CMD)\n",
        ),
        (
            # The price of the `definition` exemption, stated rather than
            # implied: each file is judged on its own, so a command line
            # bound in one module and executed from another is a definition
            # as far as the file holding it can tell. The guard walks every
            # file, so the *executing* module is reported if the option is
            # a constant there -- this entry is the defining half alone,
            # which is what the exemption absorbs.
            "a command line bound in one module and executed from another",
            'CMD = "python r.py %s PATH"\n',
        ),
        (
            # Not the taint step's bound but the reporting predicate's, and
            # measured here because this is where the rule's bounds live: a
            # substring match needs a constant that CONTAINS the option,
            # and an option assembled from pieces is in no single constant.
            # Inline, so it is nothing to do with the exemptions.
            "the option assembled from pieces, so no constant holds it",
            "import os\n"
            'os.system("python r.py --check" + "-log PATH")\n',
        ),
        (
            # CARD-242 review cycle 3. The `registration` exemption's twin
            # of the `error(...)` bound above, and the same shape: the row
            # is keyed on a method NAME, and nothing stops the exempt
            # method from executing what it is handed. It needs strictly
            # less than the `error(...)` entry -- no second method and one
            # call -- so it is its own instance rather than that one
            # re-measured. RECORDED and not closed: seeing it would mean
            # teaching the taint step about a call's receiver and what the
            # receiver's own class does with the argument, which is the
            # method-resolution work the alias (G-17) and `getattr` (G-18)
            # bounds are also waiting on, not one more binding node.
            "an add_argument() whose own method executes what it is given",
            "import os\n"
            "class Registrar:\n"
            "    def add_argument(self, command: str) -> None:\n"
            "        os.system(command)\n"
            "r = Registrar()\n"
            'r.add_argument("python r.py %s PATH")\n',
        ),
        (
            # The binding-form family's own edge, measured while
            # enumerating what :func:`_bindings` walks: an `except ... as`
            # alias binds a name, but what it binds comes from the `raise`
            # and not from the handler, so the value is not in the binding
            # node at all and there is nothing for the loop to follow. The
            # node types it does walk all hold the target and the
            # expression together; this one does not, which is the line
            # between what review cycle 3 closed and what it recorded.
            "an except ... as alias carrying what the raise was given",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            "    try:\n"
            "        raise ValueError(CMD)\n"
            "    except ValueError as command:\n"
            "        os.system(command)\n",
        ),
        (
            # And the return direction of the bound G-20 records forwards:
            # the step resolves no module-local call graph, in EITHER
            # direction -- it does not follow what a local function does
            # with what it is handed, and it does not follow what a local
            # function hands back. One family, two directions, recorded as
            # two sources because each is measured on its own.
            "a command line handed back by a local function's return",
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _command() -> str:\n"
            "    return CMD\n"
            "def _never_called() -> None:\n"
            "    os.system(_command())\n",
        ),
    )
)


#: The module-scope bindings the real tree holds that mention the option,
#: as ``(file, bound name)`` pairs: what the ``definition`` exemption
#: absorbs **in the tree it is deployed over**, measured on 2026-10-17.
#:
#: An EQUALITY and not a floor, which is review cycle 2's F-003: ADR-0039/R3
#: asks that an exemption state what it absorbs exactly, the way the sibling
#: module's ``test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones``
#: does, because ``>= 2`` lets a third absorbed site appear unnoticed -- and
#: an exemption that quietly grows a site is the shape of F-201. Two files
#: and two names, so the test measures the tree's idiom rather than one
#: module's.
MODULE_SCOPE_OPTION_BINDINGS: tuple[tuple[str, str], ...] = (
    ("tests/test_guard_integrity.py", "CHECK_LOG_OPTION"),
    ("tests/test_suite_profile.py", "SANDBOX_CONTROL_MODULE"),
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

    def test_the_prose_the_real_tree_holds_is_present_and_still_silent(
        self,
    ) -> None:
        # CARD-242's AC-2, over the real tree rather than a fixture, and
        # the reason the naive narrowing is not the fix. Keying the
        # exemption on the value instead of asking the dataflow question
        # reports two module-scope constants that mention the option and
        # execute nothing -- `SANDBOX_CONTROL_MODULE` in the other module,
        # which holds a whole fabricated test module as text, and
        # `CHECK_LOG_OPTION` in this one. Measured by removing the
        # exemption: the guard above then names both files, which is this
        # card's mutant M-B.
        #
        # So the baseline is not merely empty: it is empty *while* the tree
        # holds the shapes the exemption exists for. Without this, a
        # future narrowing could pass by the tree having stopped holding
        # them.
        bindings = sorted(
            (str(path.relative_to(REPO_ROOT)), ast.unparse(target))
            for path in _python_sources()
            for node in ast.parse(path.read_text(encoding="utf-8")).body
            if isinstance(node, ast.Assign)
            and CHECK_LOG_OPTION in ast.unparse(node.value)
            for target in node.targets
        )
        # Pinned as an equality, which is review cycle 2's F-003: two
        # bindings in two files is what makes this measure the exemption
        # against the real tree rather than one module's idiom, and `>= 2`
        # would let a THIRD absorbed module-scope site appear here
        # unnoticed. ADR-0039/R3 asks an exemption to state what it
        # absorbs exactly, and the sibling's
        # `test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones`
        # is the same shape one module across.
        assert bindings == sorted(MODULE_SCOPE_OPTION_BINDINGS), (
            "the module-scope bindings that mention the option are no "
            "longer the two measured ones -- there have to be at least two "
            "of them, in at least two files, or nothing here measures the "
            "definition exemption against the real tree, and a third one "
            "is a decision rather than something that may arrive quietly: "
            f"{bindings} against {sorted(MODULE_SCOPE_OPTION_BINDINGS)}"
        )
        reported = {
            path: invocations
            for path, _ in bindings
            if (
                invocations := _check_log_invocations(
                    (REPO_ROOT / path).read_text(encoding="utf-8")
                )
            )
        }
        assert reported == {}, reported

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
        # exempt and what they must not absorb, and this measures what the
        # rule does not see at all. Striking an entry here is how a route
        # gets closed, because closing one without striking it turns this
        # red -- which is exactly what happened to the entry CARD-239 left
        # for CARD-242, and how that bound came out in the same diff as
        # its closure.
        assert _check_log_invocations(source) == [], source

    # ------------------------------------------------------------------
    # CARD-242, AC-3: an exemption is a claim, and it gets the same two
    # controls a set member gets. CARD-239 wrote the first half for all
    # four keys and the second for none of them, and F-201 is what that
    # cost: the `definition` row absorbed a real invocation for a whole
    # card, because nothing said what it must not take.
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "key,absorbed",
        [(key, absorbed) for key, _, _, absorbed, _ in CHECK_LOG_EXEMPTIONS],
        ids=[name for _, name, _, _, _ in CHECK_LOG_EXEMPTIONS],
    )
    def test_every_exemption_absorbs_its_control_only_because_it_is_on(
        self, key: str, absorbed: str
    ) -> None:
        # Non-vacuity, the way `test_the_control_for_each_silencer_depends_on_the_set`
        # measures a member: the source is missed WITH the exemption and
        # caught WITHOUT it, so the row is load-bearing rather than
        # decorative. An exemption no control depends on is one nobody can
        # tell from a predicate that never fires.
        assert _check_log_invocations(absorbed) == [], absorbed
        narrowed = _CHECK_LOG_EXEMPTIONS - {key}
        assert _check_log_invocations(absorbed, exemptions=narrowed) != [], (
            f"the {key} exemption's control is exempt just as well with "
            "that exemption removed, so nothing here measures it"
        )

    @pytest.mark.parametrize(
        "key,rejected",
        [(key, rejected) for key, _, _, _, rejected in CHECK_LOG_EXEMPTIONS],
        ids=[name for _, name, _, _, _ in CHECK_LOG_EXEMPTIONS],
    )
    def test_no_exemption_absorbs_what_it_must_not(
        self, key: str, rejected: str
    ) -> None:
        # The half that was missing. Each row's `rejected` source is one
        # the exemption must NOT reach: the registration must not spread
        # from its call to the file, the usage message must not spread from
        # its receiver to every `error`, prose must not cover an invocation
        # standing beside it, and a module-scope binding must not cover a
        # command line that is then executed -- which is F-201, mutant M2,
        # and this card.
        assert _check_log_invocations(rejected) != [], (
            f"the {key} exemption absorbs a source it must not: {rejected}"
        )

    def test_the_hoisted_command_is_caught_by_the_taint_step(self) -> None:
        # And *which* half catches it, so the control cannot drift onto
        # some other part of the rule: with the executor set emptied the
        # same source is exactly the definition the exemption is for, and
        # the rule is silent. That is review cycle 2's M2 verdict
        # reproduced on demand, beside the closure that ends it.
        hoisted = next(
            rejected
            for key, _, _, _, rejected in CHECK_LOG_EXEMPTIONS
            if key == EXEMPT_DEFINITION
        )
        assert _check_log_invocations(hoisted) != [], hoisted
        assert _check_log_invocations(
            hoisted, executors=frozenset()
        ) == [], (
            "the hoisted command line is reported even with nothing in the "
            "executor set, so what catches it is not the taint step and "
            "this control measures something else"
        )

    def test_the_settling_loop_runs_to_a_fixpoint_and_not_to_a_count(
        self,
    ) -> None:
        # Review cycle 2's F-001, and the control the literal `3` never
        # had. The number this card first shipped is measured here rather
        # than narrated: the same chain, four links long, is reported when
        # the loop settles and silent when it is bounded to three passes --
        # caught WITH the fixpoint, missed WITHOUT it, which is the shape
        # ADR-0039/R1 asks of any claim a guard makes.
        sources = dict(CHECK_LOG_INVOCATIONS)
        forward = sources[DEEP_CHAIN_FORWARD]
        assert _check_log_invocations(forward) != [], forward
        assert _check_log_invocations(forward, passes=3) == [], (
            "the four-deep forward chain is reported at three passes too, "
            "so nothing here measures a depth and the fixpoint claims "
            "nothing the fixed count did not already do"
        )
        assert _check_log_invocations(forward, passes=4) != [], forward
        # And the asymmetry that number carried, which is why raising it
        # was not the fix either: the inner walk visits bindings in source
        # order, so ONE pass follows a chain declared executor-first
        # however deep it is, while a chain declared in the order a module
        # is actually written in -- the command line first -- settles one
        # link per pass. A fixed count is a depth bound on the idiomatic
        # order alone, which is the half nothing disclosed.
        reverse = sources[DEEP_CHAIN_REVERSE]
        assert _check_log_invocations(reverse, passes=1) != [], reverse
        assert _check_log_invocations(forward, passes=1) == [], forward
        # The loop existing at all is a different claim from it settling,
        # and the plain two-link chain is the control for that one: it is
        # reported at a single pass and silent only with no walk at all,
        # which is mutant M-C. So M-C kills the loop's existence while the
        # four-deep forward chain above kills the count.
        chain = sources[CHAIN_SECOND_CONSTANT]
        assert _check_log_invocations(chain, passes=1) != [], chain
        assert _check_log_invocations(chain, passes=0) == [], chain

    @pytest.mark.parametrize("executor", sorted(_CHECK_LOG_EXECUTOR_NAMES))
    def test_the_control_for_each_executor_depends_on_the_set(
        self, executor: str
    ) -> None:
        # Every member of the executor set carries a control that is caught
        # WITH it and missed WITHOUT it -- CARD-238's most transferable
        # artefact, applied to this set. The four shapes AC-1 names are
        # hand-written in :data:`CHECK_LOG_INVOCATIONS`; the rest get a
        # source generated from the member, which is a control for the
        # mechanism only, and the set's own width is bounded by
        # :data:`MEASURED_CHECK_LOG_MISSES` rather than by this test.
        narrowed = _CHECK_LOG_EXECUTOR_NAMES - {executor}
        generated = _with_option(
            "import os\n"
            'CMD = "python r.py %s PATH"\n'
            "def _never_called() -> None:\n"
            f"    {executor}(CMD)\n"
        )
        sources = [source for _, source in CHECK_LOG_INVOCATIONS] + [generated]
        discriminating = [
            source
            for source in sources
            if _check_log_invocations(source) != []
            and _check_log_invocations(source, executors=narrowed) == []
        ]
        assert discriminating != [], (
            f"every source {executor} is supposed to be reported by is "
            "reported just as well with it removed from the executor set, "
            "so none of them measures this member"
        )

    def test_every_executor_it_names_carries_one_reason(self) -> None:
        # The set is a grouped table so the reason is written once per
        # group and every member carries it; a name in two groups would
        # last-win and carry the wrong one. The other module's
        # `test_no_spelling_is_classified_twice`, and the same floor on the
        # reason's length `test_every_classification_carries_a_reason` uses.
        seen: dict[str, int] = {}
        for _, names in _CHECK_LOG_EXECUTOR_GROUPS:
            for name in names:
                seen[name] = seen.get(name, 0) + 1
        assert sorted(name for name, count in seen.items() if count > 1) == []
        assert len(seen) == len(_CHECK_LOG_EXECUTORS)
        bare = sorted(
            name
            for name, reason in _CHECK_LOG_EXECUTORS.items()
            if len(reason.strip()) < 20
        )
        assert bare == [], bare

    def test_the_struck_bound_and_the_closed_route_agree(self) -> None:
        # CARD-242's AC-5. Three statements about one route have to move
        # together: the deployed rule's verdict on the hoisted command
        # line, this module's recorded bound for it, and the two rows of
        # CARD-239's claim sweep that recorded it. Closing the route
        # without striking the record leaves a bound that is no longer a
        # bound; striking the record without closing the route leaves the
        # route open with nothing naming it. Either way this is red.
        hoisted = next(
            rejected
            for key, _, _, _, rejected in CHECK_LOG_EXEMPTIONS
            if key == EXEMPT_DEFINITION
        )
        closed = _check_log_invocations(hoisted) != []
        recorded = any(
            source == hoisted for _, source in MEASURED_CHECK_LOG_MISSES
        )
        assert closed != recorded, (
            "the hoisted command line is both reported and recorded as a "
            "miss, or neither: closed is "
            f"{closed} and MEASURED_CHECK_LOG_MISSES records it {recorded}"
        )
        rows = {
            row.split("|")[1].strip(): row
            for row in CLAIM_SWEEP.read_text(encoding="utf-8").splitlines()
            if re.match(r"^\| [A-G]-[0-9]+ \|", row)
        }
        missing = [row for row in SWEEP_BOUND_ROWS if row not in rows]
        assert missing == [], (
            "CARD-239's sweep no longer carries the rows that recorded this "
            f"bound, so nothing here can check what they say: {missing}"
        )
        disagreeing = sorted(
            row
            for row in SWEEP_BOUND_ROWS
            if (SWEEP_CLOSED_MARKER in rows[row]) != closed
        )
        assert disagreeing == [], (
            f"the rule reports the hoisted command line: {closed}; these "
            f"sweep rows say otherwise: {disagreeing}"
        )

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
        # CARD-242 extends the same pin to the taint step, which is the
        # half the widening adds and therefore the next thing a control
        # could certify a private copy of. Two claims, both read off this
        # source:
        #
        # * the taint step runs INSIDE the deployed rule -- `_executed_names`
        #   is called from `_check_log_invocations` and not from a test, so
        #   the tree the guard walks is the tree the taint step was asked
        #   about;
        # * no test calls the taint helpers directly. A control that called
        #   `_executed_names` itself would be measuring the step in
        #   isolation from the exemption it is supposed to condition, which
        #   is review cycle 1's F-002 one level in.
        rule = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_check_log_invocations"
        )
        deployed = ast.unparse(rule)
        assert "_executed_names" in deployed, deployed[:200]
        # And the binding enumeration is the one the taint step runs, which
        # is review cycle 3's claim: `_bindings` is where the family
        # statement lives -- which binding forms the settling loop follows
        # and which it does not -- so a copy of that enumeration inside
        # `_executed_names` would leave the statement describing a function
        # nothing calls. Same defect as F-002, one level further in.
        #
        # Read as a CALL and not as a substring, which is measured rather
        # than preferred: mutant M-N12 inlines an `Assign`-only copy of the
        # enumeration back into the step, and `"_bindings" in
        # ast.unparse(step)` stays true because the step's own docstring
        # names the function. The six binding controls kill that mutant; it
        # is this assertion that must not be the thing claiming to.
        step = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_executed_names"
        )
        enumerators = [
            ast.unparse(call.func)
            for call in ast.walk(step)
            if isinstance(call, ast.Call)
            and ast.unparse(call.func) == "_bindings"
        ]
        assert enumerators != [], (
            "the taint step does not call _bindings, so the binding forms "
            "the settling loop follows are enumerated somewhere other than "
            "the function whose docstring states them"
        )
        helpers = {
            "_executed_names", "_names_within", "_bound_keys", "_bindings",
        }
        borrowers = sorted(
            method.name
            for method in own_class.body
            if isinstance(method, ast.FunctionDef)
            for call in ast.walk(method)
            if isinstance(call, ast.Call)
            and ast.unparse(call.func) in helpers
        )
        assert borrowers == [], (
            "a test in this class calls the taint step directly instead of "
            "through _check_log_invocations, so it can be green about a "
            f"step the rule does not apply: {borrowers}"
        )
        # And every exemption key the table declares is branched on in the
        # rule: a key added to the table but never consulted would give a
        # row whose controls measure nothing, which is F-201's shape with
        # the names changed.
        declared = sorted(
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name) and target.id.startswith("EXEMPT_")
        )
        assert len(declared) == len(_CHECK_LOG_EXEMPTIONS), declared
        unbranched = [name for name in declared if name not in deployed]
        assert unbranched == [], (
            "an exemption key is declared and never consulted by the rule: "
            f"{unbranched}"
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


# --------------------------------------------------------------------------
# CARD-264 -- the claims CLAUDE.md makes about the code, held to the code
# --------------------------------------------------------------------------
#
# This module already holds one CLAUDE.md claim to its authority
# (``TestTheInterpreterFloor``: pyproject.toml declares the floor and
# CLAUDE.md follows it). CARD-264's claims are the same shape against a
# different authority -- the package itself -- so they live beside it rather
# than in ``tests/test_cli.py``, where CARD-261's component-map controls are
# still moving. See the card's worktree notes for that scope decision.

SRC_PACKAGE = REPO_ROOT / "src" / "nonogram"

#: The paragraphs of CLAUDE.md whose claims this rule reads, each located by
#: its **bold lead-in** and never by line number. That is CARD-264's own
#: subject in miniature: the three defects it fixes were reported at three
#: different line numbers by three readings, because CARD-261 rewrote the
#: block above them in between. A lead-in this rule cannot find is a
#: **FAILURE, not a skip** (ADR-0039/R2) -- a renamed paragraph would retire
#: the control silently, which is ``_WEB_SOURCES``' empty-glob defect with
#: the names changed.
GUARDED_PARAGRAPHS = (
    "**Boundary types vs. internal representation.**",
    "**The dependency baseline is closed.**",
    "**The solver (`solver/`) is the correctness-critical component.**",
)

#: Spans this rule reads as a keyword rather than as a symbol: CLAUDE.md
#: names argparse's ``choices=``/``type=`` to say the project does *not* use
#: them, so there is nothing in ``src/`` for them to resolve to. An
#: exemption is a claim (ADR-0039/R3), so it is held to an **equality**
#: against the spans that exist today by
#: ``test_the_keyword_exemption_absorbs_exactly_the_spans_it_was_measured_on``:
#: a new keyword-shaped span is a red that has to be judged, not absorbed.
MEASURED_KEYWORD_SPANS = ("choices=", "type=")

#: What this rule is measured **not** to see, declared rather than implied
#: (ADR-0039/R3). It reads the three paragraphs above and no others, and
#: within them only backtick-quoted spans: an unquoted claim ("the solver
#: checks the deadline six times") is prose it cannot analyse and does not
#: pretend to. ``_adapter_counts`` in ``tests/test_cli.py`` is the precedent
#: for closing one such shape when it matters; the general case is open and
#: is proposed as a standing check on the card.
MEASURED_CLAIM_MISSES = (
    "a claim written without backticks, anywhere in the file",
    "a claim in a paragraph whose lead-in is not in GUARDED_PARAGRAPHS",
    "a false type-or-literal claim: a span that parses and whose every name"
    " resolves in dir(builtins) is accepted for its *shape*, and is never"
    " compared against the annotations in the code (review cycle 1, F-6)",
)

_BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")

#: A fenced code block opener. ``_BACKTICK_SPAN`` cannot match across the
#: triple backticks and the newlines, so a claim written inside a fence that
#: sits directly under a guarded paragraph -- no blank line, so still the same
#: block -- was read by nothing (review cycle 1, F-5). CLAUDE.md already
#: carries four fences, so the shape is live in this very file, which is why
#: the fence is **denied** rather than added to :data:`MEASURED_CLAIM_MISSES`:
#: a declared miss that the file is one blank line away from reaching is a
#: worse trade than a deny-side rule whose cost is rewording one paragraph.
_FENCE = re.compile(r"^[ \t]*```.*$", re.MULTILINE)
_IDENTIFIER_CHAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_PATH_SUFFIXES = (".py", ".toml", ".md", ".yml", ".cfg", ".txt")


def _guarded_paragraphs(text: str) -> tuple[dict[str, tuple[int, str]], list[str]]:
    """The guarded paragraphs of ``text``, as ``{lead-in: (line, body)}``.

    Returns the paragraphs found and the lead-ins that are missing, so the
    caller fails on a missing one instead of quietly reading fewer claims.
    """
    found: dict[str, tuple[int, str]] = {}
    line = 1
    for block in text.split("\n\n"):
        for lead_in in GUARDED_PARAGRAPHS:
            if block.lstrip().startswith(lead_in):
                before = block[: block.index(lead_in)]
                found[lead_in] = (line + before.count("\n"), block)
        line += block.count("\n") + 2
    return found, [lead_in for lead_in in GUARDED_PARAGRAPHS if lead_in not in found]


def _claims(paragraph: str, first_line: int) -> list[tuple[int, str]]:
    """Every backtick-quoted span in ``paragraph``, as ``(line, span)``.

    A fence opener is emitted as a span of its own so that
    :func:`_classify` denies it as unanalysable: the alternative is reading
    the fenced region with a regex that provably cannot see into it, which is
    the vacuous arm this card is about (F-5). Document order is preserved by
    sorting on match position rather than on ``(line, span)``, so the
    fabricated single-defect cases below keep their one-to-one mapping.
    """
    spans = [
        (match.start(), match.group(1)) for match in _BACKTICK_SPAN.finditer(paragraph)
    ] + [(match.start(), match.group(0).strip()) for match in _FENCE.finditer(paragraph)]
    return [
        (first_line + paragraph[:start].count("\n"), span)
        for start, span in sorted(spans)
    ]


def _src_symbols() -> tuple[dict[str, set[str]], set[str], list[str]]:
    """The package's own vocabulary, enumerated from the package.

    ``({symbol: {module stems defining it}}, {module and package names},
    [files that would not parse])`` -- the authority ADR-0039/R2 asks for,
    walked from disk the way ``tests/test_cli.py``'s import guard walks it,
    rather than a second hand-written list of names (G-3). A file that will
    not parse is returned rather than skipped, so the caller fails on it.
    """
    symbols: dict[str, set[str]] = {}
    modules: set[str] = set()
    unparsable: list[str] = []
    for path in sorted(SRC_PACKAGE.rglob("*.py")):
        modules.add(path.stem)
        modules.update(part for part in path.relative_to(SRC_PACKAGE).parts[:-1])
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:  # pragma: no cover - a broken checkout
            unparsable.append(f"{path.name}: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                symbols.setdefault(node.name, set()).add(path.stem)
        for node in tree.body:
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
                if isinstance(node, ast.AnnAssign)
                else []
            )
            for target in targets:
                if isinstance(target, ast.Name):
                    symbols.setdefault(target.id, set()).add(path.stem)
    return symbols, modules, unparsable


def _repo_paths() -> set[str]:
    """Every file under the trees CLAUDE.md's guarded paragraphs can name.

    ``__pycache__`` is excluded (review cycle 1, F-11). The walk used to glob
    ``*`` outright, so the set's size moved with whatever had been run, and
    the card's own census figure was non-reproducible by construction. The
    effect on the rule was nil -- a ``.pyc`` can satisfy neither a span ending
    in one of :data:`_PATH_SUFFIXES` nor a ``dir/`` span -- but a figure that
    cannot be reproduced is a figure a later reader cannot check, which is
    this card's subject. Held by
    ``test_the_path_authority_counts_no_bytecode``.
    """
    paths = {
        str(path.relative_to(REPO_ROOT).as_posix())
        for tree in ("src", "tests", "docs")
        for path in (REPO_ROOT / tree).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    paths.update(
        path.name for path in REPO_ROOT.iterdir() if path.is_file()
    )
    return paths


def _declared_distributions() -> tuple[set[str], dict[str, set[str]]]:
    """``(runtime, {extra: dists})`` from pyproject.toml, which is the authority.

    ADR-0006/R1's baseline is ``project.dependencies``; the extras have
    always been outside it, and pyproject.toml's own comment says so. Read
    rather than restated (G-3), so CLAUDE.md's dependency paragraph can be
    checked against it without a second copy of either list.
    """
    table = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]

    def _name(requirement: str) -> str:
        return re.split(r"[<>=!~;\[ ]", requirement, maxsplit=1)[0].strip().lower()

    runtime = {_name(item) for item in table["dependencies"]}
    extras = {
        extra: {_name(item) for item in items}
        for extra, items in table.get("optional-dependencies", {}).items()
    }
    return runtime, extras


#: What :func:`_dependency_claim_defects` is measured **not** to see, declared
#: rather than implied (ADR-0039/R3, review cycle 2, M-4: AC-3's rule was the
#: one new rule here with no declared reach). Both shapes were re-derived
#: against the live function with pyproject.toml's own tables, and both are
#: held on the miss side by
#: ``TestClaudeMd_TheDependencyClaimMatchesPyproject.test_the_rule_names_what_it_cannot_see``.
#:
#: What is **not** declared away is the half that matters: a restatement by
#: *member* is caught backtick-independently, because ``mentioned()`` matches
#: on a word boundary and not on quoting -- "Flask, Werkzeug, reportlab and
#: gunicorn are admin-only" reds once per member with no backtick anywhere.
#: Only the restatement-by-*extra-name* arm is backtick-keyed, which is the
#: first miss below.
MEASURED_DEPENDENCY_CLAIM_MISSES = (
    "an extra restated by name without backticks -- \"the dev, admin and db"
    " extras sit outside it\" -- because the restatement arm looks for"
    " f\"`{extra}`\" and nothing else",
    "a denial of a runtime distribution -- \"`pyproject.toml` no longer"
    " declares Pillow or NumPy at runtime\" -- because mentioned() asks"
    " whether the name appears, not what the sentence says about it",
)


def _dependency_claim_defects(
    paragraph: str,
    runtime: set[str],
    extras: dict[str, set[str]],
) -> list[str]:
    """Every way CLAUDE.md's dependency paragraph and pyproject.toml disagree.

    Both directions, and both against pyproject.toml rather than against a
    second list (G-3): a runtime distribution the paragraph stops naming is a
    defect, a distribution it names that lives only in an extra is a defect
    (that is the shipped error -- ``pytest`` presented as the one extra), an
    extra named in backticks is a restatement of a table that has grown three
    times, and a paragraph that cites no authority is a defect because the
    reader has nowhere to check it.

    Takes the two tables rather than reading pyproject.toml itself, so the
    rule can be run against a fabricated one below and cannot pass vacuously.

    What this is measured **not** to see is declared in
    :data:`MEASURED_DEPENDENCY_CLAIM_MISSES` and held there, rather than left
    for a later reader to discover.
    """
    defects: list[str] = []

    def mentioned(name: str) -> bool:
        pattern = rf"(?<![\w-]){re.escape(name)}(?![\w-])"
        return re.search(pattern, paragraph, re.IGNORECASE) is not None

    for name in sorted(runtime):
        if not mentioned(name):
            defects.append(
                "the dependency paragraph no longer names the runtime "
                f"dependency {name!r}"
            )
    for extra, declared in sorted(extras.items()):
        for name in sorted(declared - runtime):
            if mentioned(name):
                defects.append(
                    f"the dependency paragraph names {name!r}, which "
                    f"pyproject.toml declares only in the {extra!r} extra"
                )
    restated = sorted(extra for extra in extras if f"`{extra}`" in paragraph)
    if restated:
        defects.append(
            "the dependency paragraph restates pyproject.toml's extras by "
            f"name: {restated}"
        )
    if "pyproject.toml" not in paragraph:
        defects.append(
            "the dependency paragraph does not cite pyproject.toml, which is "
            "the authority for both halves of the claim"
        )
    return defects


def _is_type_expression(span: str) -> bool:
    """True for a span that is a type or literal written out of builtins.

    ``list[list[bool]]``, ``tuple[tuple[int, ...], ...]``, ``(0,)`` and
    ``()`` are the boundary-type paragraph's subject and name nothing in
    ``src/``. Decided by parsing the span and resolving every name in it
    against ``dir(builtins)`` -- enumerated, not listed (ADR-0039/R2).
    """
    try:
        tree = ast.parse(span, mode="eval")
    except SyntaxError:
        return False
    names = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
    return all(name in dir(builtins) for name in names)


def _classify(
    span: str,
    symbols: dict[str, set[str]],
    modules: set[str],
    paths: set[str],
    distributions: set[str],
) -> tuple[str, str]:
    """``(kind, detail)`` for one backtick-quoted span.

    Default-deny: every shape this function recognises is named, and
    everything left over is ``"unanalysable"`` -- a FAILURE for the caller,
    never a silent pass (ADR-0039/R2).
    """
    if span.endswith("/") or any(span.endswith(suffix) for suffix in _PATH_SUFFIXES):
        bare = span.rstrip("/")
        if span.endswith("/"):
            hit = any(f"/{bare}/" in f"/{path}" for path in paths)
        else:
            hit = any(path == span or path.endswith(f"/{span}") for path in paths)
        return ("path", "") if hit else ("path", "names no file in the repo")
    if span in MEASURED_KEYWORD_SPANS:
        return "keyword", ""
    if _IDENTIFIER_CHAIN.fullmatch(span):
        parts = span.split(".")
        name, qualifier = parts[-1], parts[-2] if len(parts) > 1 else None
        if name in symbols:
            if qualifier in modules and qualifier not in symbols[name]:
                return "symbol", (
                    f"says {qualifier}.{name}, but {name} is defined in "
                    f"{sorted(symbols[name])}"
                )
            return "symbol", ""
        if name in modules:
            return "module", ""
        if name.lower() in distributions:
            return "distribution", ""
        return "symbol", "names no symbol defined in src/nonogram"
    if _is_type_expression(span):
        return "type-expression", ""
    return "unanalysable", "is a shape this rule cannot read, so it is denied"


def _claim_defects(
    claims: list[tuple[int, str]],
    symbols: dict[str, set[str]],
    modules: set[str],
    paths: set[str],
    distributions: set[str],
) -> list[str]:
    """Every claim in ``claims`` that its authority does not bear out.

    Takes the enumerated authorities rather than reading disk, so the rule
    can be run against a fabricated package and a fabricated paragraph and
    cannot pass vacuously -- the shape ``_map_defects`` and
    ``_outward_imports`` in ``tests/test_cli.py`` already use.
    """
    defects = []
    for line, span in claims:
        kind, detail = _classify(span, symbols, modules, paths, distributions)
        if detail:
            defects.append(f"CLAUDE.md:{line}: `{span}` ({kind}) {detail}")
    return defects


class TestClaudeMd_EverySymbolItNamesExists:
    """AC-1 (CARD-264): the every-session file's code claims, held to the code.

    ``CLAUDE.md`` is loaded as project instructions in every session and step
    7a of the kanban ``start`` procedure extracts its sections into every
    implementation agent's brief, so a false claim here is **acted on**. It
    named ``sourcing/random_grid.py``'s ``validate_size`` for about six weeks
    (``git log -L`` puts the two touches of those lines at 2026-09-08 and
    2026-10-22, and nothing in the repo maps the former to a wave number, so
    that date range is the honest figure and a wave count is not derivable).
    ``validate_size`` has **zero definitions anywhere in src/**: the public
    validator is ``validate_extent``, and ADR-0022/R1's refusal of a
    one-integer public validator is recorded in ``_validate_side``'s own
    docstring -- "half an extent is not a thing the model validates".

    The symbol set is **enumerated from the package** (:func:`_src_symbols`),
    never from a second hand-written list, so a symbol that stops existing
    reds here instead of going quiet (ADR-0039/R2, G-3).
    """

    @staticmethod
    def _authorities() -> tuple[dict[str, set[str]], set[str], set[str], set[str]]:
        symbols, modules, unparsable = _src_symbols()
        assert unparsable == [], unparsable
        assert symbols, "the package walk found no symbols"
        assert modules, "the package walk found no modules"
        runtime, extras = _declared_distributions()
        return symbols, modules, _repo_paths(), runtime | set().union(*extras.values())

    def test_the_guarded_paragraphs_are_all_present(self) -> None:
        """Located by text, never by line number -- and a missing lead-in is a
        failure, because a renamed paragraph would otherwise retire the whole
        rule the way an empty glob retires a source sweep."""
        found, missing = _guarded_paragraphs(GUIDANCE.read_text(encoding="utf-8"))

        assert missing == [], (
            "CLAUDE.md no longer carries these paragraph lead-ins, so the "
            "claims below are read from nothing: " + repr(missing)
        )
        assert len(found) == len(GUARDED_PARAGRAPHS)

    def test_every_claim_in_them_resolves_against_the_package(self) -> None:
        found, missing = _guarded_paragraphs(GUIDANCE.read_text(encoding="utf-8"))
        assert not missing, missing
        symbols, modules, paths, distributions = self._authorities()

        claims = [
            claim
            for lead_in, (line, body) in found.items()
            for claim in _claims(body, line)
        ]
        assert len(claims) >= 10, (
            f"only {len(claims)} backtick-quoted claims found across "
            "CLAUDE.md's guarded paragraphs; the rule is reading too little"
        )
        defects = _claim_defects(claims, symbols, modules, paths, distributions)

        assert defects == [], "\n".join(defects)

    def test_the_keyword_exemption_absorbs_exactly_the_spans_it_was_measured_on(
        self,
    ) -> None:
        """ADR-0039/R3: an exemption is a claim, held to an equality against
        the spans that exist today. A new keyword-shaped span is a red to be
        judged rather than something this exemption quietly absorbs."""
        found, missing = _guarded_paragraphs(GUIDANCE.read_text(encoding="utf-8"))
        assert not missing, missing
        symbols, modules, paths, distributions = self._authorities()

        exempted = sorted(
            {
                span
                for line, body in found.values()
                for _, span in _claims(body, line)
                if _classify(span, symbols, modules, paths, distributions)[0] == "keyword"
            }
        )

        assert exempted == sorted(MEASURED_KEYWORD_SPANS), (
            "the keyword exemption and the spans it absorbs have diverged: "
            f"{exempted} vs {sorted(MEASURED_KEYWORD_SPANS)}"
        )

    def test_the_rule_names_what_it_cannot_see(self) -> None:
        """ADR-0039/R3's last clause: the residual hole is declared, not implied.

        Each case reads the entry it demonstrates (review cycle 2, M-3). The
        demonstrations were already here and already executable, but none of
        them touched :data:`MEASURED_CLAIM_MISSES`, so the tuple's *text* was
        the one unguarded thing in a class about unguarded text: mutant
        F6-DECL-GUTTED emptied the third entry's middle line and survived,
        because ``assert MEASURED_CLAIM_MISSES`` was still satisfied by the
        other two. Keying each case on a fragment of its own entry makes a
        gutted or reworded declaration red here.
        """
        assert MEASURED_CLAIM_MISSES
        symbols, modules, paths, distributions = self._authorities()

        # The first declared miss, demonstrated rather than asserted in prose:
        # the same dead symbol unquoted is invisible to this rule, and quoted
        # is not.
        unquoted = "range validation happens in random_grid's validate_size"
        quoted = "range validation happens in `random_grid.validate_size`"

        assert _claim_defects(_claims(unquoted, 1), symbols, modules, paths, distributions) == []
        assert _claim_defects(_claims(quoted, 1), symbols, modules, paths, distributions)
        assert "written without backticks" in MEASURED_CLAIM_MISSES[0]

        # The second: the same quoted dead symbol under a lead-in that is not
        # guarded is never reached at all, because _guarded_paragraphs finds
        # no paragraph to hand on. Shown both ways round, so this is a
        # statement about the lead-in and not about the paragraph's body.
        unguarded = f"**Test style.** {quoted}\n"
        guarded = f"{GUARDED_PARAGRAPHS[0]} {quoted}\n"

        assert _guarded_paragraphs(unguarded)[0] == {}
        assert sorted(_guarded_paragraphs(unguarded)[1]) == sorted(GUARDED_PARAGRAPHS)
        assert set(_guarded_paragraphs(guarded)[0]) == {GUARDED_PARAGRAPHS[0]}
        assert "lead-in is not in GUARDED_PARAGRAPHS" in MEASURED_CLAIM_MISSES[1]

        # The third declared miss, demonstrated the same way (F-6): a span
        # that parses and resolves in dir(builtins) is accepted for its shape,
        # so a *false* boundary type passes -- while a dead symbol smuggled
        # inside a builtin-shaped subscript is still denied, because that
        # branch is tight about names and blind about truth.
        false_type = "clues cross the boundary as `dict[str, frozenset[bytes]]`"
        assert _claim_defects(
            _claims(false_type, 1), symbols, modules, paths, distributions
        ) == []
        assert _claim_defects(
            _claims("`list[validate_size]`", 1), symbols, modules, paths, distributions
        )
        assert "resolves in dir(builtins)" in MEASURED_CLAIM_MISSES[2]

    def test_a_fence_inside_a_guarded_paragraph_is_denied(self) -> None:
        """F-5, closed rather than declared: a fenced block that sits directly
        under a guarded paragraph is part of the same block, and the span
        regex provably cannot see into it.

        Caught WITH the fence and missed WITHOUT, on a fabricated paragraph:
        the dead symbol inside the fence is invisible to the span reader, so
        the fence itself is what reds. The second half is the other state --
        the same paragraph without the fence is clean, so this is a rule about
        fences and not a rule that cannot pass.
        """
        symbols, modules, paths, distributions = self._authorities()
        fenced = (
            "**The dependency baseline is closed.** as shipped\n"
            "```python\n"
            "validate_size(30)\n"
            "```\n"
        )

        defects = _claim_defects(
            _claims(fenced, 46), symbols, modules, paths, distributions
        )

        assert len(defects) == 2, defects
        assert defects[0].startswith("CLAUDE.md:47: ````python`"), defects
        assert defects[1].startswith("CLAUDE.md:49: `````"), defects
        assert all(
            "is a shape this rule cannot read, so it is denied" in defect
            for defect in defects
        ), defects
        assert _claim_defects(
            _claims("**The dependency baseline is closed.** as shipped\n", 46),
            symbols,
            modules,
            paths,
            distributions,
        ) == []

    def test_the_path_authority_counts_no_bytecode(self) -> None:
        """F-11: the path census is reproducible, so a figure quoted from it
        can be checked by a later reader.

        The walk globs ``*``, so it used to count ``__pycache__/*.pyc`` and
        the size moved with whatever had been run. Harmless to the rule -- the
        set is consulted only for membership, and the second half below is why
        a ``.pyc`` could never have satisfied a span anyway -- but a census
        figure nobody can reproduce is exactly the kind of claim this card
        exists to deny.
        """
        paths = _repo_paths()
        assert paths, "the path walk found nothing"

        assert [path for path in paths if "__pycache__" in path] == []
        assert [path for path in paths if path.endswith(".pyc")] == []
        assert _repo_paths() == paths


class TestClaudeMd_APlantedDeadSymbolReds:
    """AC-2 (CARD-264): the control, caught WITH the defect and missed WITHOUT.

    The on-disk half of this is run from the card's worktree notes (a planted
    ``CLAUDE.md`` reference, red with it and green without, restored under a
    ``cp -p`` backup verified by ``shasum -a 256`` and ``diff -q``). What is
    committed here is the same rule against fabricated paragraphs, so every
    defect kind has a case that reds on every run and none of them depends on
    mutating a tracked file.
    """

    @staticmethod
    def _authorities() -> tuple[dict[str, set[str]], set[str], set[str], set[str]]:
        return TestClaudeMd_EverySymbolItNamesExists._authorities()

    @pytest.mark.parametrize(
        ("paragraph", "fragment"),
        [
            pytest.param(
                "validation happens in `sourcing/random_grid.py`'s `validate_size`",
                "`validate_size` (symbol) names no symbol defined in src/nonogram",
                id="the-defect-this-card-fixes",
            ),
            pytest.param(
                "the boundary type is `orchestrator.GenerationRequesst`",
                "names no symbol defined in src/nonogram",
                id="a-typo-in-a-real-symbol",
            ),
            pytest.param(
                "the public validator is `clues.validate_extent`",
                "says clues.validate_extent, but validate_extent is defined in",
                id="a-real-symbol-attributed-to-the-wrong-module",
            ),
            pytest.param(
                "the pipeline is described in `docs/NO_SUCH_FILE.md`",
                "names no file in the repo",
                id="a-path-that-does-not-exist",
            ),
            pytest.param(
                "the solver's state is `a pair of (filled, empty` masks",
                "is a shape this rule cannot read, so it is denied",
                id="a-shape-the-rule-cannot-read-defaults-to-deny",
            ),
        ],
    )
    def test_a_planted_claim_reds_naming_the_span_and_its_line(
        self, paragraph: str, fragment: str
    ) -> None:
        symbols, modules, paths, distributions = self._authorities()

        defects = _claim_defects(
            _claims(paragraph, 46), symbols, modules, paths, distributions
        )

        assert len(defects) == 1, defects
        assert defects[0].startswith("CLAUDE.md:46: "), defects
        assert fragment in defects[0], defects

    def test_the_same_claims_pass_once_the_planted_span_is_removed(self) -> None:
        """The other state: with the dead symbol replaced by the live one, the
        identical rule is green -- so the reds above are the plant and not a
        rule that cannot pass."""
        symbols, modules, paths, distributions = self._authorities()
        repaired = (
            "validation happens in `sourcing/random_grid.py`'s `validate_extent`"
            " / `validate_density`, never as `choices=` constraints, and the"
            " boundary type is `orchestrator.GenerationRequest` carrying"
            " `list[list[bool]]`"
        )

        assert _claim_defects(
            _claims(repaired, 46), symbols, modules, paths, distributions
        ) == []

    def test_the_real_symbols_the_paragraph_names_are_each_resolvable(self) -> None:
        """Caught WITH the authority, missed WITHOUT it: fed a package whose
        walk found nothing, the rule reds on claims the real walk resolves --
        so the green above is the package agreeing, not an authority that
        accepts anything."""
        paths = _repo_paths()

        assert _claim_defects(
            _claims("`validate_extent`", 46), {}, set(), paths, set()
        )


class TestClaudeMd_TheDependencyClaimMatchesPyproject:
    """AC-3 (CARD-264): the dependency paragraph, and the shape that shipped.

    **The shape that shipped is "do not restate".** CLAUDE.md's paragraph
    said "stdlib + Pillow + NumPy as runtime dependencies (plus ``pytest`` as
    a dev-only extra)" while pyproject.toml carries extras of its own,
    enumerated there and deliberately not repeated here -- neither their
    members nor how many of them there are (review cycle 2, M-6: a count in
    prose that no control reads is the same shape as "closed at two names").
    Naming their members in this docstring would be the same second copy AC-3
    removed from CLAUDE.md, one file over, and nothing reads a docstring
    (review cycle 1, F-10, and G-3).
    A corrected list in CLAUDE.md would have been a second copy of a table
    that has grown more than once, which is the disease CARD-261 treated in
    the component map, so the paragraph now names the runtime baseline
    ADR-0006/R1 is about and points at pyproject.toml for the extras instead
    of enumerating them.

    Both halves are controlled, from pyproject.toml itself (G-3): the runtime
    distributions it declares must each be named, and no distribution that
    lives only in an extra -- nor an extra's own name -- may appear. The
    second half is what keeps ADR-0038/R7 readable from here: ``pytest`` and
    ``pytest-playwright`` are dev-only, and a paragraph that listed either
    beside Pillow and NumPy would be claiming otherwise.
    """

    @staticmethod
    def _paragraph() -> str:
        found, missing = _guarded_paragraphs(GUIDANCE.read_text(encoding="utf-8"))
        assert not missing, missing
        return found["**The dependency baseline is closed.**"][1]

    def test_the_paragraph_names_the_runtime_baseline_and_no_extra(self) -> None:
        runtime, extras = _declared_distributions()
        assert runtime, "pyproject.toml declares no runtime dependency"
        assert extras, "pyproject.toml declares no extras"

        defects = _dependency_claim_defects(self._paragraph(), runtime, extras)

        assert defects == [], "\n".join(defects)

    @pytest.mark.parametrize(
        ("paragraph", "fragment"),
        [
            pytest.param(
                "`pyproject.toml` declares exactly stdlib + Pillow as runtime deps",
                "no longer names the runtime dependency 'numpy'",
                id="a-runtime-dependency-gone-missing",
            ),
            pytest.param(
                "`pyproject.toml` declares stdlib + Pillow + NumPy (plus pytest"
                " as a dev-only extra)",
                "names 'pytest', which pyproject.toml declares only in the 'dev' extra",
                id="the-defect-this-card-fixes",
            ),
            pytest.param(
                "`pyproject.toml` declares Pillow + NumPy; the `dev`, `admin` and"
                " `db` extras are outside the baseline",
                "restates pyproject.toml's extras by name",
                id="a-restatement-of-three-extras-named-literally",
            ),
            pytest.param(
                "runtime dependencies are exactly Pillow and NumPy",
                "does not cite pyproject.toml, which is the authority",
                id="a-paragraph-that-cites-no-authority",
            ),
        ],
    )
    def test_a_planted_divergence_reds(self, paragraph: str, fragment: str) -> None:
        runtime, extras = _declared_distributions()

        defects = _dependency_claim_defects(paragraph, runtime, extras)

        assert any(fragment in defect for defect in defects), defects

    def test_the_restatement_rule_covers_every_extra_pyproject_declares(
        self,
    ) -> None:
        """The parametrized case above names three extras in a *fabricated*
        paragraph, which is defensible but would not notice a fourth. This one
        builds its paragraph from pyproject.toml's own keys, so the day an
        extra is added the rule is already covering it and no list here has to
        be edited (G-3)."""
        runtime, extras = _declared_distributions()
        assert extras, "pyproject.toml declares no extras"

        for extra in sorted(extras):
            paragraph = (
                "`pyproject.toml` declares Pillow + NumPy as the runtime "
                f"baseline; the `{extra}` extra sits outside it"
            )

            defects = _dependency_claim_defects(paragraph, runtime, extras)

            assert any(
                f"restates pyproject.toml's extras by name: ['{extra}']" in defect
                for defect in defects
            ), (extra, defects)

    def test_the_rule_reds_when_the_authority_moves_under_it(self) -> None:
        """Caught WITH the authority, missed WITHOUT: the same shipped
        paragraph against a fabricated pyproject that moved Pillow into an
        extra reds, so the green above is agreement with the real table."""
        defects = _dependency_claim_defects(
            self._paragraph(), {"numpy"}, {"imaging": {"pillow"}}
        )

        assert any("only in the 'imaging' extra" in defect for defect in defects), defects

    def test_the_rule_names_what_it_cannot_see(self) -> None:
        """ADR-0039/R3's last clause for AC-3 (review cycle 2, M-4): the two
        shapes that evade this rule, each with a fabricated paragraph on the
        miss side, and the member restatement that does **not** evade it.

        The third assertion is the one that keeps the declaration from being
        written wider than it was measured: the restatement arm is the only
        backtick-keyed one, so a paragraph that lists an extra's *members*
        unquoted still reds, once per member.
        """
        runtime, extras = _declared_distributions()
        assert MEASURED_DEPENDENCY_CLAIM_MISSES
        assert extras, "pyproject.toml declares no extras"

        unquoted_extras = (
            "`pyproject.toml` declares Pillow + NumPy as the runtime baseline;"
            f" the {', '.join(sorted(extras))} extras sit outside it"
        )
        denial = "`pyproject.toml` no longer declares Pillow or NumPy at runtime"

        assert _dependency_claim_defects(unquoted_extras, runtime, extras) == []
        assert _dependency_claim_defects(denial, runtime, extras) == []

        extra, members = next(
            (name, sorted(declared - runtime))
            for name, declared in sorted(extras.items())
            if declared - runtime
        )
        caught = _dependency_claim_defects(
            "`pyproject.toml` declares Pillow + NumPy; "
            f"{', '.join(members)} are {extra}-only",
            runtime,
            extras,
        )
        assert len(caught) == len(members), caught
        assert all(f"only in the {extra!r} extra" in defect for defect in caught), caught

        assert "without backticks" in MEASURED_DEPENDENCY_CLAIM_MISSES[0]
        assert "a denial of a runtime distribution" in MEASURED_DEPENDENCY_CLAIM_MISSES[1]


class TestClaudeMd_TheTimeoutClaimNamesItsTest:
    """AC-6 (CARD-264): no surviving claim about the solver's timeout that no
    test pins.

    The paragraph said the cooperative timeout's "hook points [are] already
    present in ``propagate.py``/``search.py``, not yet enforced". It is fully
    enforced: ``orchestrator`` fixes one ``time.monotonic`` deadline per
    request and passes it inward, six sites check it across ``propagate.py``
    and ``search.py``, and ``propagate.py`` raises ``SolverTimeout``.
    Correcting "not yet enforced" to "enforced" would have been false again
    the day someone removed a check site, with nothing to notice -- so the
    clause now says what the code guarantees and **names the test that pins
    it**, and this control holds that pairing: the sentence that mentions the
    deadline must cite a path under ``tests/`` that exists.

    The count is pinned at the one sentence there is today, the way
    ``_LAUNCH_EDGE`` is pinned as one ordered pair: dropping the clause is a
    legitimate decision, and this makes it a deliberate edit to this line
    rather than a quiet loss of the citation.
    """

    _VOCABULARY = ("timeout", "deadline")

    #: What this rule is measured **not** to see, declared rather than implied
    #: (ADR-0039/R3, review cycle 1, F-8). Held executably by
    #: ``test_the_rule_names_what_its_two_words_cannot_reach``, so a widening
    #: of either bound has to edit this tuple with it. Both are deliberate:
    #: the vocabulary is two words because a wider one would select sentences
    #: about export deadlines and process timeouts and turn an exact pin at
    #: one into noise; and the sentence split is the stdlib-simple one, so a
    #: clause welded onto the citation-bearing sentence is a sentence this
    #: rule reads as already cited -- which is weaker than it sounds, since
    #: the clause then sits inside the sentence that does carry the citation.
    #:
    #: The second entry was corrected in review cycle 2 (M-1). It claimed an
    #: em-dash breaks the split; re-measured against ``_timeout_sentences``,
    #: an em-dash-joined clause is **one** sentence, exactly like the colon
    #: and the comma, because ``(?<=[.;])\s+`` looks behind for a full stop or
    #: a semicolon and nothing else. The semicolon, which the entry did not
    #: mention, is the second joiner that does break it. Both sides are held
    #: per joiner by ``test_the_rule_names_what_its_two_words_cannot_reach``,
    #: which also reads these entries' own text.
    MEASURED_TIMEOUT_CLAIM_MISSES = (
        'a claim phrased without "timeout" or "deadline" ("the solver also'
        ' gives up on its own after a while")',
        "a second claim joined to the cited sentence by a colon, a comma or"
        " an em-dash, none of which the sentence split breaks on (a full stop"
        " or a semicolon does, and reds)",
    )

    @classmethod
    def _timeout_sentences(cls, body: str) -> list[str]:
        """The sentences of ``body`` that speak about the solver's deadline.

        Takes the body rather than reading CLAUDE.md, so both the vocabulary
        bound and the sentence split can be exercised against fabricated
        paragraphs that this file cannot satisfy by being edited.
        """
        return [
            sentence
            for sentence in re.split(r"(?<=[.;])\s+", body)
            if any(word in sentence.lower() for word in cls._VOCABULARY)
        ]

    def _sentences(self) -> list[str]:
        found, missing = _guarded_paragraphs(GUIDANCE.read_text(encoding="utf-8"))
        assert not missing, missing
        return [
            sentence
            for _line, body in found.values()
            for sentence in self._timeout_sentences(body)
        ]

    def test_the_claim_is_one_sentence_and_it_names_an_existing_test(self) -> None:
        sentences = self._sentences()
        paths = _repo_paths()

        assert len(sentences) == 1, (
            "the number of sentences in CLAUDE.md's guarded paragraphs that "
            "speak about the solver's deadline has changed; each one has to "
            f"name the test that pins it: {sentences}"
        )
        cited = re.findall(r"`(tests/[\w./-]+\.py)`", sentences[0])
        assert cited, (
            "CLAUDE.md claims something about the solver's deadline without "
            f"naming the test that enforces it: {sentences[0]!r}"
        )
        missing = [path for path in cited if path not in paths]
        assert missing == [], missing

    def test_the_rule_names_what_its_two_words_cannot_reach(self) -> None:
        """ADR-0039/R3's last clause for AC-6: both bounds declared and held.

        AC-6 reads "no claim about the solver's timeout survives that no test
        pins", and the *selection* is narrower than that sentence: two words,
        and a sentence split that breaks on a full stop or a semicolon and on
        nothing else. Each declared family gets a fabricated body on the miss
        side and each breaking joiner gets one on the caught side, so the
        declaration states the reach rather than being a sentence beside it.

        The em-dash body sits on the **miss** side as of review cycle 2 (M-1).
        It used to sit on the caught side as ``f"{cited} \u2014 and the exporter
        has a deadline of its own."``, which does read as two sentences -- but
        on the full stop ``cited`` already ends with, not on the em-dash. With
        the full stop removed, the em-dash joins the clause into one sentence
        like the colon and the comma do.
        """
        assert self.MEASURED_TIMEOUT_CLAIM_MISSES
        cited = (
            "The solver checks one cooperative deadline per request, pinned by"
            " `tests/test_timeout.py`."
        )
        assert len(self._timeout_sentences(cited)) == 1

        for missed in (
            f"{cited} The solver also gives up on its own after a while.",
            f"{cited} A time budget is also applied inside the exporter.",
            f"{cited[:-1]}: a second budget applies inside the exporter too.",
            f"{cited[:-1]}, and a second budget applies inside the exporter.",
            f"{cited[:-1]} \u2014 and the exporter has a deadline of its own.",
        ):
            assert len(self._timeout_sentences(missed)) == 1, missed

        for caught in (
            f"{cited} A second deadline applies inside the exporter.",
            f"{cited} The exporter enforces its own timeout.",
            f"{cited[:-1]}; the exporter enforces its own timeout.",
        ):
            assert len(self._timeout_sentences(caught)) == 2, caught

        assert 'without "timeout" or "deadline"' in self.MEASURED_TIMEOUT_CLAIM_MISSES[0]
        joiners = self.MEASURED_TIMEOUT_CLAIM_MISSES[1]
        assert "a colon, a comma or an em-dash" in joiners
        assert "a full stop or a semicolon does" in joiners

    def test_no_guarded_paragraph_says_the_mechanism_is_unenforced(self) -> None:
        """The specific stale shape, denied by value. Deny-side, so the cost is
        a false positive: a future sentence that legitimately describes
        something as not yet enforced must reword or edit this line."""
        found, missing = _guarded_paragraphs(GUIDANCE.read_text(encoding="utf-8"))
        assert not missing, missing

        offenders = [
            f"{lead_in}: {phrase}"
            for lead_in, (_line, body) in found.items()
            for phrase in ("not yet enforced", "not enforced", "hook points")
            if phrase in body.lower()
        ]

        assert offenders == [], offenders

    @staticmethod
    def _supported_range() -> dict[str, int]:
        source = (SRC_PACKAGE / "limits.py").read_text(encoding="utf-8")
        bounds = {
            name: int(value)
            for name, value in re.findall(r"^(MIN_SIZE|MAX_SIZE) = (\d+)$", source, re.M)
        }
        assert bounds.keys() == {"MIN_SIZE", "MAX_SIZE"}, bounds
        return bounds

    @staticmethod
    def _figures_outside(bodies: dict[str, str], bounds: dict[str, int]) -> list[str]:
        """Every ``NxM`` figure in ``bodies`` that ``limits.py`` cannot produce.

        Takes the paragraphs and the bounds rather than reading either, so the
        rule has a case that reds on every run even though the shipped file now
        carries no such figure at all. That matters: this is a deny-side rule
        with **no instance left in the tree**, and a rule with no instance and
        no fabricated case is exactly the unfalsifiable arm this card is about.
        """
        return [
            f"{where} claims a {side}-cell side, outside "
            f"{bounds['MIN_SIZE']}..{bounds['MAX_SIZE']}"
            for where, body in bodies.items()
            for side, _other in re.findall(r"\b(\d+)\s*[x\u00d7]\s*(\d+)\b", body)
            if not bounds["MIN_SIZE"] <= int(side) <= bounds["MAX_SIZE"]
        ]

    def test_no_guarded_paragraph_claims_a_grid_size_the_limits_forbid(self) -> None:
        """The paragraph's other defect: it named a known-hard class at
        "40x40+", a side ``limits.py`` caps at MAX_SIZE, so no such grid can
        be produced. The figure is gone and the paragraph points at
        ``limits.MAX_SIZE`` instead of restating a number (G-3)."""
        found, missing = _guarded_paragraphs(GUIDANCE.read_text(encoding="utf-8"))
        assert not missing, missing
        bodies = {lead_in: body for lead_in, (_line, body) in found.items()}

        assert self._figures_outside(bodies, self._supported_range()) == []

    def test_the_figure_rule_reds_on_the_figure_that_shipped(self) -> None:
        """Caught WITH the defect, missed WITHOUT it."""
        bounds = self._supported_range()

        assert self._figures_outside(
            {"solver": "random mid-density grids at 40x40+ are hard"}, bounds
        ) == ["solver claims a 40-cell side, outside 10..30"]
        assert self._figures_outside(
            {"solver": "random mid-density grids at 30x30 are hard"}, bounds
        ) == []
