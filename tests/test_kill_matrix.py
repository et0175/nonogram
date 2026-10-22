"""CARD-260 — the kill instrument's six known traps, each as a control that fails.

Every acceptance criterion here is certified against a **planted failure**, not
against the instrument's own report of success. An instrument that certifies
itself is exactly the defect CARD-256 gated on three times, so each trap gets:

* the shape that bites (planted, measured, asserted);
* the instrument's refusal or its corrected reading;
* and, where the trap is a wrong *reading* rather than an unmeasurable one, the
  naive reading kept beside the corrected one so the two must disagree.

AC-7's two reproductions are the independent anchors: ``test_full_suite_lock.py``
at ``ddb1731b`` and ``test_db_engine_lifecycle.py`` at ``b441ba00``, two matrices
this board already measured three separate ways in wave 50.
"""

from __future__ import annotations

import ast
import io
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

from tests import full_suite_lock, kill_matrix as km
from tests.kill_matrix import (
    BLIND,
    FAIL,
    NOT_REACHED,
    PASS,
    Edit,
    KillMatrix,
    LeakedPatch,
    LockHeld,
    Matrix,
    Mutant,
    MutantRefused,
    Pass,
    Runner,
    SelectionRefused,
)

REPO = Path(__file__).resolve().parent.parent
INSTRUMENT = Path(km.__file__).resolve()

# --------------------------------------------------------------------------
# The structural censuses, each as ONE callable — ADR-0039/R1
# --------------------------------------------------------------------------
#
# Every guardrail below (G-4's import allowance, G-5's two halves, G-6's two
# halves, the plugin's env-var names) used to be a comprehension written inline
# in its own test, asserted to find **nothing** in `kill_matrix.py`. An
# absence-assertion over a clean source has only R1's "missed WITHOUT" half: an
# inert predicate and a holding predicate are indistinguishable, which was
# measured — breaking the `"git"` substring, the git-command pattern or the
# clock-module set each left the whole file green.
#
# So each census is one function here, called **twice**: once on the
# instrument's own source, asserted to find nothing, and once on a small
# planted source that does contain the violation, asserted to find and name it.
# A planted positive routed through a *re-spelling* of the predicate would be
# the same defect again, so there is exactly one spelling of each and both
# halves call it. Killing a census's mechanism now reds its WITH half.

#: A git invocation as it appears in a string constant: anchored at the head so
#: ``/usr/bin/git status`` is inside it while prose about "no git command
#: anywhere" is not. One spelling, shared by the census, by the two asserts that
#: demonstrate its semantics, and by the run-time-assembly bound below — which
#: is what makes those asserts controls rather than copies.
GIT_COMMAND = re.compile(r"(\S*/)?git(\s|$)")

#: Modules a ``from X import name`` would let a spawn be called under a bare
#: name, which is not spawn-shaped at its call site and so invisible to the argv
#: census. Held as one set so deleting a member reds the WITH half.
SPAWN_IMPORT_MODULES = frozenset({"subprocess", "os", "multiprocessing", "posix", "pty"})

#: G-6's first half: importing any of these is reading a clock.
TIMING_MODULES = frozenset({"time", "timeit", "datetime", "resource", "cProfile"})

#: G-6's second half: naming any of these is reading a clock. ``time()`` carries
#: its parenthesis on purpose — the bare word appears in prose.
CLOCK_NAMES = ("perf_counter", "monotonic", "process_time", "time()", "elapsed")

#: An env-var name of this instrument, as it appears in text. The generated
#: plugin must carry none literally (it takes them as format fields), and the
#: *rendered* plugin must read exactly the three the runner sets.
ENV_NAME_SHAPE = re.compile(r"KILL_MATRIX[A-Z_]*")


def _aliased_spawn_imports(tree: ast.AST) -> list[str]:
    """Every ``from <spawn module> import ...`` in `tree`, as module names."""
    return [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module in SPAWN_IMPORT_MODULES
    ]


def _spawn_argv_heads(tree: ast.AST) -> list[str]:
    """``argv[0]`` of every spawn-shaped call in `tree`, in walk order.

    Spawn-shapedness is the module's own ``_SPAWN`` pattern, so ``os.system``,
    ``os.execv``, ``Popen``, ``check_output`` and ``multiprocessing`` are inside
    the walk and not only ``subprocess.*``.

    **Default-deny**, and that is why this raises rather than returning a
    partial list: a spawn with no argument list, an argv this cannot enumerate,
    or a non-literal ``argv[0]`` other than ``sys.executable`` is a FAILURE, not
    a silently skipped entry. ``test_g5_the_argv_census_fails_rather_than_skips``
    plants one of each and is the control for that sentence.
    """
    heads: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not km._SPAWN.search(ast.unparse(node.func)):
            continue
        assert node.args, f"unanalysable spawn-shaped call at line {node.lineno}"
        argv = node.args[0]
        assert isinstance(argv, (ast.List, ast.Tuple)), (
            f"subprocess argv at line {node.lineno} is not an enumerable literal "
            f"list: {ast.unparse(argv)}"
        )
        head = argv.elts[0]
        if isinstance(head, ast.Constant):
            heads.append(head.value)
            continue
        # The one non-literal that exists: the interpreter running this process,
        # which is how the instrument re-enters pytest. Anything else is a shape
        # this enumeration cannot analyse, and that is a FAILURE, not a pass.
        assert ast.unparse(head) == "sys.executable", (
            f"subprocess argv[0] at line {node.lineno} is neither a literal nor "
            f"sys.executable: {ast.unparse(head)}"
        )
        heads.append("sys.executable")
    return heads


def _git_among(heads: list[str]) -> list[str]:
    """The argv heads that name git. Substring, so ``/usr/bin/git`` is inside."""
    return [name for name in heads if "git" in str(name)]


def _git_command_strings(tree: ast.AST) -> list[str]:
    """Every string constant in `tree` shaped like a git invocation."""
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and GIT_COMMAND.match(node.value)
    ]


def _timing_module_imports(tree: ast.AST) -> list[str]:
    """The timing modules `tree` imports, sorted. G-6's first half."""
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    return sorted(imported & TIMING_MODULES)


def _clock_names_in(source: str) -> list[str]:
    """The clock-reading names `source` mentions, in declaration order."""
    return [name for name in CLOCK_NAMES if name in source]


def _hard_coded_env_names(template: str) -> list[str]:
    """Env-var names of this instrument spelled out literally in `template`."""
    return ENV_NAME_SHAPE.findall(template)


# --------------------------------------------------------------------------
# Fixtures — small target files, written out so a planted failure is real
# --------------------------------------------------------------------------

#: Two tests, five assertion nodes, one of them inside a two-iteration loop.
#: The node count (5) and the collected test count (2) differ on purpose: a
#: figure that quotes one while meaning the other is trap 1, and it cannot be
#: caught on a file where the two numbers happen to agree.
SIMPLE_TARGET = '''\
"""A target with 5 assertion nodes and 2 collected tests."""
# These three comment lines exist to be deleted. Trap 6's mutant removes them,
# which leaves the file running green while every assert below shifts by three
# -- far enough that no shifted lineno lands on a pristine one, so the whole
# matrix reads NOT-REACHED rather than being quietly misattributed.
import km_leaky

MARK = "shipped"
LIMIT = 1


def test_arms():
    assert MARK == "shipped"
    assert len(MARK) == 7
    assert km_leaky.LEAK == "shipped"


def test_loop_arm():
    seen = []
    for index in (0, 1):
        seen.append(index)
        assert index >= LIMIT - 1
    assert seen == [0, 1]
'''

#: The line trap 6's planted mutant deletes. Removing it shifts every assert
#: below it and the file still runs green, which is the whole trap.
DELETABLE = (
    "# which leaves the file running green while every assert below shifts by three\n"
    "# -- far enough that no shifted lineno lands on a pristine one, so the whole\n"
    "# matrix reads NOT-REACHED rather than being quietly misattributed.\n"
)

#: Trap 2's mutant: on SHIPPED the loop arm passes on both iterations; with
#: ``LIMIT = 2`` it reds on iteration 0 and passes on iteration 1, so the
#: records arrive RED-then-GREEN and last-write-wins loses the RED.
def _loop_mutant(target: Path) -> Mutant:
    return Mutant(
        "LIMIT-ROT", (Edit(path=target, old="LIMIT = 1", new="LIMIT = 2"),)
    )


#: One arm whose truth depends on a child pytest's outcome, and the child runs
#: a test out of this same file. ``CHILD_MARK`` is what a mutant moves.
CHILD_TARGET = '''\
"""A child-spawning arm. The child runs one test out of this same file."""
import os
import subprocess
import sys

CHILD_MARK = "ok"


def test_the_child_arm():
    if os.environ.get("KILL_MATRIX_FIXTURE_CHILD") == "1":
        assert CHILD_MARK == "ok", "the arm the mutant moves, inside the child"
        return
    child = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
         __file__ + "::test_the_child_arm"],
        capture_output=True,
        text=True,
        env={**os.environ, "KILL_MATRIX_FIXTURE_CHILD": "1"},
    )
    assert child.returncode == 0, child.stdout + child.stderr
'''


def _write(folder: Path, name: str, source: str) -> Path:
    path = folder / name
    path.write_text(source, encoding="utf-8")
    return path


#: A module the target imports and asserts on. AC-4's planted leak lives here,
#: because a patch left in a file the measurement never reads cannot red
#: SHIPPED -- and a leak SHIPPED cannot see is not the trap.
LEAKY = 'LEAK = "shipped"\n'


@pytest.fixture
def simple_target(tmp_path) -> Path:
    _write(tmp_path, "km_leaky.py", LEAKY)
    return _write(tmp_path, "km_simple_target.py", SIMPLE_TARGET)


@pytest.fixture
def child_target(tmp_path) -> Path:
    return _write(tmp_path, "km_child_target.py", CHILD_TARGET)


def _runner(target: Path, **kwargs) -> Runner:
    return Runner(selection=[str(target)], repo_root=target.parent, **kwargs)


#: Token types that can only precede the first token of a statement.
_STATEMENT_HEADS = frozenset(
    {tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT}
)


def _independent_assert_count(path: Path) -> int:
    """The denominator counted by a second **route**, not a second copy.

    ``ast.walk`` over a fresh parse would be the same route rewritten: a shared
    misconception about what an ``ast.Assert`` node enumerates — the exact
    failure a control exists to catch — would be invisible to it. This one
    never builds a tree. It tokenises the source and counts the ``assert``
    keyword in **statement position**: immediately after a NEWLINE / NL /
    INDENT / DEDENT, or after a ``:`` or ``;`` (``if x: assert y``), or at the
    very start. A comment or a string containing the word is a COMMENT or
    STRING token and is not counted.
    """
    source = path.read_text(encoding="utf-8")
    counted = 0
    previous: object = None
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            continue
        if token.type in _STATEMENT_HEADS:
            previous = token.type
            continue
        if (
            token.type == tokenize.NAME
            and token.string == "assert"
            and (previous is None or previous in _STATEMENT_HEADS or previous == ":;")
        ):
            counted += 1
        previous = (
            ":;"
            if token.type == tokenize.OP and token.string in {":", ";"}
            else token.type
        )
    return counted


# ==========================================================================
# AC-1 (trap 6) — a line-count-shifting deletion mutant is refused
# ==========================================================================


def test_ac1_a_line_count_shifting_mutant_is_refused(simple_target):
    """The refusal, and it must name the line-count change it refuses."""
    source = simple_target.read_text(encoding="utf-8")
    lines = len(source.splitlines())

    with pytest.raises(MutantRefused) as refusal:
        km.apply_edit(source, Edit(path=simple_target, old=DELETABLE, new=""))

    said = str(refusal.value)
    assert "line-count-shifting" in said, said
    gone = len(DELETABLE.splitlines())
    assert gone == 3, gone
    assert f"newlines {lines} -> {lines - gone}" in said, said
    assert f"splitlines {lines} -> {lines - gone}" in said, said


@pytest.mark.parametrize(
    "new",
    [
        pytest.param(
            "# a replacement of the same line count.\n" * 3, id="same-line-count"
        ),
        pytest.param("# two lines\n# for three.\n", id="fewer-lines-is-refused"),
        pytest.param("# four\n" * 4, id="more-lines-is-refused"),
        pytest.param("", id="deleted-is-refused"),
    ],
)
def test_ac1_the_edge_of_the_claim_is_the_line_count_and_nothing_else(
    simple_target, new
):
    """One mutant inside the claimed region, two at its edge.

    The claim is *the line count*, not *the deletion*: a two-line replacement
    for a one-line original must be refused too, and a same-line substitution
    of the very same text must be accepted. Both halves are measured, because a
    check that only rejected the empty string would pass the deletion case and
    be narrative about the other.
    """
    source = simple_target.read_text(encoding="utf-8")
    edit = Edit(path=simple_target, old=DELETABLE, new=new)
    if len(new.splitlines()) == len(DELETABLE.splitlines()):
        mutated = km.apply_edit(source, edit)
        assert mutated.count("\n") == source.count("\n")
        assert len(mutated.splitlines()) == len(source.splitlines())
    else:
        with pytest.raises(MutantRefused, match="line-count-shifting"):
            km.apply_edit(source, edit)


def test_g1_the_two_construction_refusals_each_have_a_control(tmp_path):
    """ADR-0039/R1 for the two refusals nothing exercised.

    Both are construction-time and cheap, and the empty-edit-set one is
    measurement-relevant: without it ``_apply`` is a no-op and the mutant's
    column publishes as a survivor, which is trap 5's own shape. Re-derive the
    refusals rather than the expectations if either reds.
    """
    with pytest.raises(MutantRefused, match="edits nothing"):
        km.Mutant("EDITS-NOTHING", ())

    with pytest.raises(MutantRefused, match="occurrence must be 1-based"):
        km.Edit(path=tmp_path / "x.py", old="a", new="b", occurrence=0)

    # The ordinary path still constructs, so neither refusal can be satisfied
    # by refusing always.
    ok = km.Edit(path=tmp_path / "x.py", old="a", new="b", occurrence=1)
    assert km.Mutant("ORDINARY", (ok,)).edits == (ok,)


def test_ac1_the_planted_shifting_mutant_runs_green_and_reports_nothing(
    simple_target, tmp_path
):
    """Why the refusal is load-bearing, measured rather than asserted in prose.

    The shifting mutant is written to disk **past** :func:`apply_edit`, which is
    the only way to see what the refusal prevents. The deleted line is a
    comment, so the mutated file still runs **green** — and every assert below
    it now carries a ``lineno`` one less than the matrix's, so every cell in the
    matrix reports ``NOT-REACHED``. A green run with a blank matrix is
    indistinguishable from a file that never ran, which is trap 6.
    """
    pristine = simple_target.read_text(encoding="utf-8")
    linenos = km.assert_linenos(pristine, str(simple_target))
    runner = _runner(simple_target)
    # ``_pytest`` is driven directly here, and only ``run`` ends a run and
    # discards the temp tree -- so this one is pointed at a directory pytest
    # owns rather than at a machine-wide temp dir nothing cleans up.
    runner._workdir = tmp_path / "km-workdir-shifting"
    runner._workdir.mkdir()

    gone = len(DELETABLE.splitlines())
    shifted = pristine.replace(DELETABLE, "", 1)
    assert len(shifted.splitlines()) == len(pristine.splitlines()) - gone
    simple_target.write_text(shifted, encoding="utf-8")
    try:
        records, exit_code, output = runner._pytest(Pass.RECORDING)
        # And the refusal itself, exercised rather than described. ``_measure``
        # is where it lives, and the off-key condition asserted below is
        # exactly its trigger -- so without this call the test demonstrates
        # the trap and never demonstrates the guard, which is ADR-0039/R1's
        # "missed WITHOUT" half with no "caught WITH". Re-derive the refusal
        # rather than the expectation if this ever reds.
        with pytest.raises(MutantRefused, match="no cell for"):
            runner._measure("SHIFTED", Pass.RECORDING, len(linenos), pristine)
    finally:
        simple_target.write_text(pristine, encoding="utf-8")

    assert exit_code == 0, output
    assert km.collected_tests(output) == 2, output
    assert set(records) == {lineno - gone for lineno in linenos}, sorted(records)
    assert not set(records) & set(linenos), (
        "the shifted numbering overlapped the pristine one, so this fixture "
        "cannot show the trap"
    )
    assert all(
        km.aggregate_any_red(records.get(lineno, [])) == NOT_REACHED
        for lineno in linenos
    ), sorted(records)


# --------------------------------------------------------------------------
# AC-1, the rest of trap 6 — equal line counts are not a stable numbering
# --------------------------------------------------------------------------

#: Two arms and a comment line, so that a substitution can trade places with
#: an assert, swap the two asserts, or put both on one line — all three with
#: the line count preserved, which is what ``_refuse_line_shift`` checks and
#: all this one can check.
TOPOLOGY_TARGET = '''\
"""Two arms and a comment line a mutant can trade places with."""

MARK = "shipped"


def test_two_arms():
    # a comment line the mover swaps with the assert below it
    assert MARK == "shipped", "the first arm"
    assert len(MARK) == 7, "the second arm"
'''

COMMENT_LINE = "    # a comment line the mover swaps with the assert below it\n"
FIRST_ARM = '    assert MARK == "shipped", "the first arm"\n'
SECOND_ARM = '    assert len(MARK) == 7, "the second arm"\n'


@pytest.fixture
def topology_target(tmp_path) -> Path:
    return _write(tmp_path, "km_topology_target.py", TOPOLOGY_TARGET)


def test_ac1_an_equal_line_count_edit_that_moves_an_assert_is_refused(
    topology_target,
):
    """The shape ``_refuse_line_shift`` passes, and what it costs.

    Line count preserved, so the only check that ran before accepted it — and
    the moved arm's cell then read ``NOT-REACHED`` while the arm had run and
    **failed**: a genuine kill published as "never reached", with exit code 0,
    no refusal, and ``raw_cells`` agreeing with ``cells`` so there was no
    internal disagreement to notice. The card's own notes call that the worse
    of the two outcomes, because a misattributed cell looks like a measurement.
    """
    pristine = topology_target.read_text(encoding="utf-8")
    edit = Edit(
        path=topology_target,
        old=COMMENT_LINE + FIRST_ARM,
        new=FIRST_ARM + COMMENT_LINE,
    )

    moved = km.apply_edit(pristine, edit)
    assert len(moved.splitlines()) == len(pristine.splitlines()), (
        "this control only certifies the new check if the line-count check "
        "accepts the mutant"
    )
    assert km.assert_linenos(moved) != km.assert_linenos(pristine), (
        km.assert_linenos(moved),
        km.assert_linenos(pristine),
    )

    with pytest.raises(MutantRefused, match="moved the target's assert topology"):
        _runner(topology_target).run(Pass.RECORDING, [Mutant("MOVE", (edit,))])

    assert topology_target.read_text(encoding="utf-8") == pristine, (
        "the refusal must still leave the target restored"
    )


def test_ac1_two_asserts_swapped_are_refused_though_the_linenos_are_identical(
    topology_target,
):
    """The variant a lineno-tuple comparison cannot see.

    Swapping two asserts keeps the tuple of linenos **identical**, so there is
    no off-key record anywhere and the misattribution is evidence-free: each
    cell carries the other arm's outcome. What the matrix needs is not the key
    set but the key set *together with what each key means*, which is why the
    check compares :func:`kill_matrix.assert_shapes`.
    """
    pristine = topology_target.read_text(encoding="utf-8")
    edit = Edit(
        path=topology_target,
        old=FIRST_ARM + SECOND_ARM,
        new=SECOND_ARM + FIRST_ARM,
    )

    swapped = km.apply_edit(pristine, edit)
    assert km.assert_linenos(swapped) == km.assert_linenos(pristine), (
        "this control certifies the stronger check only while the lineno tuple "
        "is untouched: a swap must leave nothing off-key behind"
    )
    assert km.assert_shapes(swapped) != km.assert_shapes(pristine)

    with pytest.raises(MutantRefused, match="moved the target's assert topology"):
        _runner(topology_target).run(Pass.RECORDING, [Mutant("SWAP", (edit,))])


def test_ac1_a_mutant_that_merges_two_asserts_onto_one_line_is_refused(
    topology_target,
):
    """The collision refusal, re-checked on the file that will actually run.

    ``Runner.run`` refuses a target with two asserts on one lineno — and
    computed it once, on the pristine source. A line-count-preserving mutant
    that merges two asserts onto one line reintroduced exactly that shape past
    the check: one cell for two nodes, plus a ``NOT-REACHED`` for a node that
    no longer exists.
    """
    pristine = topology_target.read_text(encoding="utf-8")
    edit = Edit(
        path=topology_target,
        old=FIRST_ARM + SECOND_ARM,
        new=FIRST_ARM.rstrip("\n") + "; " + SECOND_ARM.strip() + "\n    pass\n",
    )

    merged = km.apply_edit(pristine, edit)
    linenos = km.assert_linenos(merged)
    assert len(set(linenos)) == 1 and len(linenos) == 2, linenos

    with pytest.raises(MutantRefused, match="moved the target's assert topology"):
        _runner(topology_target).run(Pass.RECORDING, [Mutant("MERGE", (edit,))])


def test_ac1_a_mutant_that_leaves_the_target_unparsable_is_refused(topology_target):
    """The degenerate case of the same check: no keys at all.

    A blank matrix and a file that never ran are the same reading, so this is a
    refusal rather than a zero.
    """
    edit = Edit(path=topology_target, old=SECOND_ARM, new="    assert (\n")
    with pytest.raises(MutantRefused, match="unparsable"):
        _runner(topology_target).run(Pass.RECORDING, [Mutant("BREAK", (edit,))])


def test_ac1_a_mutant_that_does_not_touch_the_target_is_not_refused(
    simple_target, tmp_path
):
    """The check's false-positive cost, measured: it is a no-op elsewhere.

    The grid AC-7 reproduces mutates ``src/nonogram/db/session.py`` while the
    target is a test file, so a topology check that fired on any mutant would
    refuse every real campaign this instrument runs.
    """
    result = _runner(simple_target).run(
        Pass.RECORDING,
        [
            Mutant(
                "LEAK-FREE",
                (Edit(path=tmp_path / "km_leaky.py", old="shipped", new="rotted!"),),
            )
        ],
    )
    assert result.mutants["LEAK-FREE"].failed, result.mutants["LEAK-FREE"].table()


# ==========================================================================
# AC-2 (trap 2) — ANY-RED across executions, never last-write-wins
# ==========================================================================


@pytest.mark.parametrize(
    ("outcomes", "any_red", "last_write"),
    [
        pytest.param([False, True], FAIL, PASS, id="red-then-green"),
        pytest.param([True, False], FAIL, FAIL, id="green-then-red"),
        pytest.param([True, True], PASS, PASS, id="both-green"),
        pytest.param([], NOT_REACHED, NOT_REACHED, id="never-ran"),
    ],
)
def test_ac2_any_red_and_last_write_wins_disagree_where_it_matters(
    outcomes, any_red, last_write
):
    """The control for the aggregation is the aggregation that loses the RED.

    ``red-then-green`` is the shape that bit: the loop's first iteration reds,
    the second passes, and last-write-wins reports ``PASS``. The other rows are
    the claim's edge — the two aggregations must agree everywhere else, or the
    disagreement would say nothing about ordering.
    """
    assert km.aggregate_any_red(outcomes) == any_red
    assert km.aggregate_last_write_wins(outcomes) == last_write


def test_ac2_a_two_iteration_arm_aggregates_red_in_a_real_run(simple_target):
    """The same disagreement, measured through a real pytest rather than a list.

    Under ``LIMIT-ROT`` the loop arm reds on iteration 0 and passes on iteration
    1, so the recorded outcomes arrive in that order from the instrumented run
    itself. ANY-RED calls the arm ``FAIL``; last-write-wins, fed the **identical
    records**, calls it ``PASS``. That second reading is the planted failure,
    and it is the one that would have lost 3 of 6 kills in wave 50.
    """
    result = _runner(simple_target).run(Pass.RECORDING, [_loop_mutant(simple_target)])
    matrix = result.mutants["LIMIT-ROT"]
    loop_arm = max(
        lineno for lineno, got in matrix.records.items() if len(got) > 1
    )

    assert matrix.records[loop_arm] == (False, True), matrix.records[loop_arm]
    assert km.aggregate_any_red(matrix.records[loop_arm]) == FAIL
    assert km.aggregate_last_write_wins(matrix.records[loop_arm]) == PASS, (
        "the control cannot fail, which would be the finding: last-write-wins "
        "must lose this RED or it is not the trap"
    )
    assert matrix.cells[loop_arm] == FAIL, matrix.table()
    assert result.shipped.cells[loop_arm] == PASS, result.shipped.table()


# ==========================================================================
# AC-3 (trap 3) — suppressed propagation across a process boundary
# ==========================================================================


def test_ac3_one_transformer_and_the_recording_pass_is_its_failing_state():
    """Both passes are the same transformer; only the handler differs.

    This is the free control the architecture gives: the re-raising pass's
    claim ("propagation is intact") has a failing state that exists on disk —
    the recording pass — rather than being hypothesised.
    """
    source = "def f():\n    assert 1 == 2\n"
    bodies = {}
    for reraise in (False, True):
        tree = km._Recorder(reraise).visit(ast.parse(source))
        ast.fix_missing_locations(tree)
        bodies[reraise] = ast.unparse(tree)

    assert "raise" not in bodies[False], bodies[False]
    assert "raise" in bodies[True], bodies[True]
    assert bodies[False] == bodies[True].replace("\n        raise", ""), (
        "the two passes are not one transformer apart; the control is only free "
        "while the recording pass *is* the handler that forgot the raise"
    )


def test_the_transformer_rewrites_every_assert_at_any_depth(simple_target):
    """The transformer's own node list, checked against an independent walk.

    Not against itself: :func:`kill_matrix.assert_linenos` is one enumeration
    and :attr:`_Recorder.seen` is the transformer's record of what it actually
    rewrote, and the two must agree as multisets. A rewrite that missed an
    assert nested in a ``with``, a ``try`` or a comprehension's enclosing
    function would show up here as a shorter list, not as a silently smaller
    matrix.
    """
    nested = (
        "def test_depth():\n"
        "    with open(__file__):\n"
        "        for _ in (1,):\n"
        "            try:\n"
        "                assert True\n"
        "            except AssertionError:\n"
        "                assert True\n"
        "            else:\n"
        "                assert True\n"
        "    assert True\n"
    )
    for source in (simple_target.read_text(encoding="utf-8"), nested):
        recorder = km._Recorder(reraise=False)
        recorder.visit(ast.parse(source))
        assert sorted(recorder.seen) == sorted(km.assert_linenos(source)), (
            sorted(recorder.seen),
            sorted(km.assert_linenos(source)),
        )
    assert len(km.assert_linenos(nested)) == 4


def test_two_asserts_sharing_one_lineno_are_refused(tmp_path):
    """A shape the matrix cannot attribute is a FAILURE, never one merged cell.

    ``assert a; assert b`` on one line gives two ``ast.Assert`` nodes with the
    same ``lineno``. The matrix is keyed on that lineno, so one cell would have
    to stand for both -- which is a quieter version of trap 2. Refused instead.
    """
    target = _write(
        tmp_path,
        "km_collision.py",
        "def test_two_on_one_line():\n    assert True; assert True\n",
    )
    assert _independent_assert_count(target) == 2
    with pytest.raises(SelectionRefused, match="more than one assert on line"):
        _runner(target).run(Pass.RECORDING)


def test_ac3_child_dependent_arms_are_derived_from_the_target_ast(child_target):
    """The blind-spot set comes from the target's own AST, never a hand list."""
    source = child_target.read_text(encoding="utf-8")
    marked = km.child_dependent_linenos(source, str(child_target))
    linenos = km.assert_linenos(source, str(child_target))

    rc_arm = max(linenos)
    in_child_arm = min(linenos)
    assert rc_arm in marked, marked
    assert in_child_arm not in marked, (
        "the arm *above* the spawn is not child-dependent; a rule that marked "
        "every assert in the function would make the overlay unfalsifiable"
    )


def test_ac3_the_blind_spot_rule_over_marks_and_its_bound_is_measured():
    """The rule's direction and its declared limit, both measured.

    Over-marking: an arm that sits after a spawn but reads nothing from it is
    still marked, because the rule is intra-function position, not dataflow.
    That is the fail-closed direction -- never a silent PASS on an arm that
    might be suppressed.

    The bound: an arm that reads a child's outcome through a **helper's** return
    value is **not** marked. Declared, not claimed sound, and asserted here so
    the declaration cannot quietly become false.
    """
    over_marks = (
        "import subprocess\n"
        "def test_after_a_spawn_but_unrelated():\n"
        "    subprocess.run(['true'])\n"
        "    assert 1 == 1\n"
    )
    assert km.child_dependent_linenos(over_marks) == frozenset({4}), (
        "an arm after a spawn must be marked even when it reads nothing from "
        "it; a dataflow rule here would be a silent PASS on a suppressed arm"
    )

    through_a_helper = (
        "import subprocess\n"
        "def _child():\n"
        "    return subprocess.run(['true'])\n"
        "def test_reads_the_helpers_result():\n"
        "    assert _child().returncode == 0\n"
    )
    assert km.child_dependent_linenos(through_a_helper) == frozenset(), (
        "the declared bound moved: the rule is intra-function, so this arm is "
        "outside it -- update the bound rather than the expectation"
    )


def test_ac3_the_rejected_fail_closed_set_would_relabel_nothing_on_either_anchor():
    """Bound 2's cost argument, measured on the anchors rather than asserted.

    The set bound 2 rejects is "every ``NOT-REACHED`` arm in a file that spawns
    anything". **What rejects it** is that it decides a cell from position
    standing in for a cause the instrument cannot observe -- a targeted
    selection legitimately leaves most of a file's asserts ``NOT-REACHED``, so
    the set relabels every arm the selection never ran. **What it would cost on
    this card's two anchors is nothing**, and an earlier wording of the bound
    claimed those anchors refuted the set. Both halves are measured here so
    neither can quietly become false again.
    """
    lifecycle = (REPO / "tests" / "test_db_engine_lifecycle.py").read_text(
        encoding="utf-8"
    )
    spawns = [
        node.lineno
        for node in ast.walk(ast.parse(lifecycle))
        if isinstance(node, ast.Call) and km._SPAWN.search(ast.unparse(node.func))
    ]
    assert spawns == [], (
        f"anchor 2's target spawns at {spawns}, so the rejected set's "
        "precondition is satisfied there after all -- re-derive the bound "
        "rather than the expectation"
    )
    assert km.child_dependent_linenos(lifecycle) == frozenset(), (
        "anchor 2's target has no child-dependent arm, so the set would "
        "relabel nothing in it -- including the three NAMES-BLIND arms the "
        "bound's earlier wording said it would break"
    )

    lock_guard = LOCK_GUARD_TEST.read_text(encoding="utf-8")
    assert km.child_dependent_linenos(lock_guard), (
        "anchor 1's target must spawn, or the two anchors do not bracket the "
        "rejected set at all"
    )
    # Anchor 1 spawns but has no NOT-REACHED arm to relabel:
    # test_ac7_the_lock_guard_file_reproduces_130_of_130_pass_and_reached
    # measures that half (``matrix.not_reached == ()``) in a real run.


def test_ac3_the_recording_pass_declares_the_blind_spot_the_re_raising_pass_kills(
    child_target,
):
    """Both passes over one child-spawning arm. The two must differ.

    Planted failure: the mutant moves ``CHILD_MARK``, so the assert *inside the
    child* is false. With the child instrumented too:

    * recording pass — the child's wrapper swallows the ``AssertionError``, the
      child reports a pass with exit 0, and the parent's ``returncode == 0``
      premise records ``PASS`` **by construction**. That raw reading is kept and
      asserted here, because it is the lie; the instrument reports ``BLIND``.
    * re-raising pass — the child re-raises, exits non-zero, and the parent's
      premise records the kill.
    """
    source = child_target.read_text(encoding="utf-8")
    rc_arm = max(km.assert_linenos(source, str(child_target)))
    in_child_arm = min(km.assert_linenos(source, str(child_target)))
    mutant = Mutant(
        name="CHILD-MARK-ROT",
        edits=(Edit(path=child_target, old='CHILD_MARK = "ok"', new='CHILD_MARK = "no"'),),
    )

    recording = _runner(child_target, child_instrumentation=True).run(
        Pass.RECORDING, [mutant]
    )
    reraising = _runner(child_target, child_instrumentation=True).run(
        Pass.RERAISING, [mutant]
    )

    recorded = recording.mutants["CHILD-MARK-ROT"]
    reraised = reraising.mutants["CHILD-MARK-ROT"]

    assert recorded.raw_cells[rc_arm] == PASS, (
        "the trap did not bite, so nothing here certifies the overlay: the "
        f"naive recording reading was {recorded.raw_cells[rc_arm]}"
    )
    assert recorded.cells[rc_arm] == BLIND, recorded.table()
    assert reraised.cells[rc_arm] == FAIL, reraised.table()
    assert recorded.cells[rc_arm] != reraised.cells[rc_arm]
    assert recorded.blind == (rc_arm,), recorded.table()
    assert reraised.blind == (), reraised.table()

    # The two passes' exit codes are the same difference seen from outside: the
    # recording pass swallowed everything and pytest called the run green.
    assert recorded.exit_code == 0, recorded.figure()
    assert reraised.exit_code != 0, reraised.figure()

    assert recorded.cells[in_child_arm] == FAIL, (
        "the child's own arm is where the recording pass earns its keep: it is "
        "attributed from the child's pid even though the child reported a pass"
    )


def test_ac3_the_flag_off_reading_on_a_child_spawning_target_is_the_bound(
    child_target,
):
    """The **default** configuration's reading on the same target, cell for cell.

    The declared bound used to say that with ``child_instrumentation=False``
    "the child is pristine, propagation is intact, and those arms are measured
    for real". That is true of the **parent's** arm, which reads the child's
    returncode, and false of the arm that executes only *inside* the child: it
    writes no record at all and reads ``NOT-REACHED`` though it ran and failed.
    Measured here beside the flag-on reading, because the exempted state had no
    control of its own — and that is also why both figures must state which
    setting produced them: with the overlay off no ``BLIND`` cell can exist, so
    ``0 BLIND`` would otherwise be indistinguishable from "no arm is blind".
    """
    source = child_target.read_text(encoding="utf-8")
    linenos = km.assert_linenos(source, str(child_target))
    in_child_arm, rc_arm = min(linenos), max(linenos)
    assert rc_arm in km.child_dependent_linenos(source, str(child_target))
    assert in_child_arm not in km.child_dependent_linenos(source, str(child_target)), (
        "the in-child arm sits above the spawn, so the position rule does not "
        "mark it -- which is why the bound is narrowed rather than the overlay "
        "being applied to the marked set with the flag off"
    )
    mutant = Mutant(
        name="CHILD-MARK-ROT",
        edits=(
            Edit(path=child_target, old='CHILD_MARK = "ok"', new='CHILD_MARK = "no"'),
        ),
    )

    off = _runner(child_target).run(Pass.RECORDING, [mutant])
    on = _runner(child_target, child_instrumentation=True).run(
        Pass.RECORDING, [mutant]
    )
    off_cells = off.mutants["CHILD-MARK-ROT"]
    on_cells = on.mutants["CHILD-MARK-ROT"]

    assert off_cells.cells[in_child_arm] == NOT_REACHED, off_cells.table()
    assert on_cells.cells[in_child_arm] == FAIL, on_cells.table()
    assert off_cells.cells[rc_arm] == FAIL, off_cells.table()
    assert on_cells.cells[rc_arm] == BLIND, on_cells.table()
    assert off_cells.blind == (), off_cells.table()

    for figure in (off_cells.figure(), off.figure(), off.table()):
        assert "child instrumentation off" in figure, figure
    for figure in (on_cells.figure(), on.figure(), on.table()):
        assert "child instrumentation on" in figure, figure


# ==========================================================================
# AC-4 (trap 4) — SHIPPED is re-run between mutants, and a leak fails it
# ==========================================================================


def test_ac4_two_sequential_mutants_each_see_a_clean_shipped(simple_target, tmp_path):
    """The honest path: one SHIPPED reading per mutant, each FAIL-free."""
    second = _write(tmp_path, "km_side.py", 'SIDE = "shipped"\n')
    runner = _runner(simple_target)
    mutants = [
        Mutant(
            "MARK-ROT",
            (Edit(path=simple_target, old='MARK = "shipped"', new='MARK = "rotted!"'),),
        ),
        Mutant("SIDE-ROT", (Edit(path=second, old='"shipped"', new='"rotted"'),)),
    ]

    result = runner.run(Pass.RECORDING, mutants)

    assert set(result.shipped_between) == {"MARK-ROT", "SIDE-ROT"}
    for name, matrix in result.shipped_between.items():
        assert matrix.failed == (), f"{name}: {matrix.table()}"
        assert matrix.cells == result.shipped.cells, name
    assert second.read_text(encoding="utf-8") == 'SIDE = "shipped"\n'


def test_ac4_a_leaked_patch_is_caught_by_the_shipped_re_run_between_mutants(
    simple_target, tmp_path
):
    """The leak is planted in the bookkeeping, which is the shape it took.

    Not a skipped restore of a registered file — that the ``diff -q`` and
    ``shasum`` verification would catch on its own. The real leak was a path
    **outside** the restore registry, so every verification that ran was
    satisfied and the mutation stayed on disk into the next mutant. Only the
    between-mutants SHIPPED re-run can see that, and this is how we know it can.
    """
    leaky = tmp_path / "km_leaky.py"

    class LeakingRunner(Runner):
        def _backup_registry(self, paths):
            return super()._backup_registry(
                [path for path in paths if path != leaky]
            )

    runner = LeakingRunner(
        selection=[str(simple_target)], repo_root=simple_target.parent
    )
    mutants = [
        Mutant(
            "LEAKS",
            (Edit(path=leaky, old='LEAK = "shipped"', new='LEAK = "leaked!!"'),),
        ),
        Mutant(
            "AFTER",
            (Edit(path=simple_target, old='MARK = "shipped"', new='MARK = "rotted!"'),),
        ),
    ]

    with pytest.raises(LeakedPatch) as caught:
        runner.run(Pass.RECORDING, mutants)

    assert "after LEAKS" in str(caught.value), str(caught.value)
    assert leaky.read_text(encoding="utf-8") == 'LEAK = "leaked!!"\n', (
        "the plant must actually leak, or this test certifies nothing"
    )


def test_ac4_restoring_uses_cp_p_backups_and_no_git_command_anywhere():
    """G-5, enumerated from the instrument's own AST rather than by reading.

    Two halves, each with its own reach, stated rather than conflated.

    **Argv.** Every call whose callee is *spawn-shaped* — matched with the
    module's own ``_SPAWN`` pattern, so ``os.system``, ``os.execv``,
    ``Popen``, ``check_output`` and ``multiprocessing`` are inside the walk and
    not only ``subprocess.*`` — must pass an enumerable literal argv, and a
    ``git`` among those heads is the finding. Default-deny: a spawn whose
    argument list this cannot enumerate fails the test rather than being
    skipped. A spawn imported under a bare name (``from subprocess import run``)
    would not be spawn-shaped at its call site, so that import is refused
    separately, below.

    **Strings.** Every string constant, matched command-shaped and anchored —
    ``GIT_COMMAND``, the one spelling of ``(\\S*/)?git(\\s|$)`` in this file —
    so ``/usr/bin/git status`` is inside it while prose about "no git command
    anywhere" is not. **Declared bound:** a command assembled at run time from
    pieces that are not themselves ``git`` is outside both halves, which is why
    the argv heads are enumerated rather than grepped.

    Demonstrated rather than accepted, in bound 1's shape: the last block runs
    **both** halves — ``_spawn_argv_heads`` and ``_git_command_strings``, the
    same two callables used above and not a re-spelling of them — over a source
    that assembles a ``git`` command out of non-``git`` pieces, and asserts they
    miss it, so the bound reds if it ever becomes false instead of standing as
    prose.

    This is the WITHOUT half of R1 — the censuses find nothing here, and on a
    clean source that alone cannot tell a holding predicate from an inert one.
    Their WITH halves are
    ``test_g5_the_argv_census_catches_a_planted_git_spawn``,
    ``test_g5_the_string_census_catches_a_planted_git_command``,
    ``test_g5_the_bare_name_spawn_import_census_catches_a_planted_import`` and
    ``test_g5_the_argv_census_fails_rather_than_skips``, which call the same
    callables on planted sources. Measured per assertion, not asserted in
    prose: narrowing ``GIT_COMMAND`` to a never-matching pattern reds the
    absolute-path arm here and the planted-command arm there; widening it until
    it matches prose reds the ``invoked == []`` arm here — on this module's own
    sentence — the prose arm beside it, and the planted-command arm there;
    breaking the ``"git"`` substring reds the planted-spawn arm; dropping a
    ``SPAWN_IMPORT_MODULES`` member reds the planted-import arm; and neutering
    the ``_SPAWN`` walk reds five arms across three of these tests.
    """
    tree = ast.parse(INSTRUMENT.read_text(encoding="utf-8"), filename=str(INSTRUMENT))
    aliased = _aliased_spawn_imports(tree)
    assert aliased == [], (
        f"{aliased} is imported from, so a spawn could be called under a bare "
        "name that is not spawn-shaped and the enumeration below would not see "
        "it"
    )

    commands = _spawn_argv_heads(tree)
    assert commands, "no spawn-shaped call found; the enumeration is dead"
    # An EQUALITY rather than three membership checks, the way G-4 holds its
    # import allowance: a spawn of any *new* name reds here on the day it is
    # added, `git` among them, without depending on the git predicate below.
    assert sorted(set(commands)) == ["cp", "diff", "shasum", "sys.executable"], commands
    assert _git_among(commands) == [], commands

    invoked = _git_command_strings(tree)
    assert invoked == [], invoked
    assert GIT_COMMAND.match("/usr/bin/git status"), (
        "the widened pattern no longer reaches an absolute path, which is the "
        "shape it was widened for"
    )
    assert not GIT_COMMAND.match("No git command anywhere"), (
        "the pattern now matches prose, so it would red on the module's own "
        "claim rather than on an invocation"
    )

    # The declared bound, demonstrated rather than accepted -- bound 1's shape.
    # A git command assembled at run time out of pieces that are not themselves
    # ``git`` passes both halves: argv[0] is an enumerable literal that is not
    # git, and no string constant is command-shaped git. Default-deny catches
    # the easy spellings (a Name, a BinOp or an f-string in argv[0] all fail the
    # argv half above), so this is the shape that is genuinely outside -- and it
    # must stay named as a bound rather than quietly become false.
    assembled = (
        "import os, subprocess\n"
        "def restore(path):\n"
        "    tool = os.environ['VCS']\n"
        "    subprocess.run(['sh', '-c', tool + ' checkout ' + path])\n"
    )
    outside_tree = ast.parse(assembled)
    heads = _spawn_argv_heads(outside_tree)
    named = _git_command_strings(outside_tree)
    assert heads == ["sh"] and named == [], (
        "the declared bound moved: this source assembles a git command out of "
        "pieces that are not themselves `git`, and both halves of the "
        f"enumeration above are supposed to miss it (heads {heads}, strings "
        f"{named}) -- update the bound rather than the expectation"
    )


#: A target that violates the argv half: a spawn whose head is bare ``git``, one
#: whose head is an absolute path to git, and one the census must NOT call git,
#: so the plant measures the predicate from both sides.
GIT_SPAWN_TARGET = '''\
import subprocess

def restore(path):
    subprocess.run(["git", "checkout", "--", path])
    subprocess.run(["/usr/bin/git", "status"])
    subprocess.run(["cp", "-p", path])
'''

#: A target that violates the strings half: a bare git command, an absolute one,
#: the module's own prose claim (which must stay outside, or the WITHOUT half
#: would red on `kill_matrix.py`'s own sentence), and a word that merely
#: contains the substring (which a command-shaped pattern must not match).
GIT_STRING_TARGET = '''\
"""No git command anywhere -- except the two constants below."""
CHECKOUT = "git checkout -- one"
ABSOLUTE = "/opt/homebrew/bin/git status"
PROSE = "legit grievance"
'''

#: A source that imports a spawn under a bare name from every member of
#: ``SPAWN_IMPORT_MODULES``. Written out rather than generated from the set: a
#: plant derived from the set shrinks with it, and the equality it feeds would
#: then hold however many members were deleted.
SPAWN_IMPORT_TARGET = '''\
from subprocess import run
from os import system
from multiprocessing import Process
from posix import execv
from pty import spawn
from pathlib import Path
'''


def test_g5_the_argv_census_catches_a_planted_git_spawn():
    """R1's WITH half for the argv census: the git heads are found and named.

    The WITHOUT half (``test_ac4_restoring_uses_cp_p_backups_and_no_git_command_
    anywhere``) asserts the instrument's own source yields none. That alone
    cannot tell an inert predicate from a holding one -- measured: with
    ``"git" in str(name)`` turned into ``"gxt" in str(name)`` the whole file
    stayed green. This is the same two callables over a planted positive, so
    that mutation reds here.

    An EQUALITY on the whole finding, not a membership test: a predicate that
    answered "everything is git" would also be inert, and the ``cp`` head in the
    plant catches it from the other side.
    """
    heads = _spawn_argv_heads(ast.parse(GIT_SPAWN_TARGET))
    assert sorted(heads) == ["/usr/bin/git", "cp", "git"], heads
    assert sorted(_git_among(heads)) == ["/usr/bin/git", "git"], (
        "the argv census no longer recognises a git head -- its empty finding "
        f"in the WITHOUT half is therefore vacuous (heads {heads})"
    )


def test_g5_the_string_census_catches_a_planted_git_command():
    """R1's WITH half for the strings census, through the shared pattern.

    ``GIT_COMMAND`` has exactly one spelling, used by the census, by the two
    semantics asserts beside it and by the run-time-assembly bound. Measured
    before the hoist: four copies meant breaking the one actually in use left
    67 tests green, because each assert tested its own copy. One constant makes
    this test its control.

    Both sides, because a widened pattern is as inert as a narrowed one: the two
    commands are caught, and the prose and the substring-in-a-word are not.
    """
    named = _git_command_strings(ast.parse(GIT_STRING_TARGET))
    assert sorted(named) == [
        "/opt/homebrew/bin/git status",
        "git checkout -- one",
    ], (
        "the strings census no longer finds a command-shaped git constant -- "
        f"its empty finding in the WITHOUT half is therefore vacuous: {named}"
    )
    assert "No git command anywhere" in GIT_STRING_TARGET, GIT_STRING_TARGET
    assert "legit" in GIT_STRING_TARGET, GIT_STRING_TARGET


def test_g5_the_bare_name_spawn_import_census_catches_a_planted_import():
    """R1's WITH half for the bare-name-spawn import refusal.

    ``SPAWN_IMPORT_MODULES`` is hand-written -- no authority enumerates "modules
    whose members spawn" -- which ADR-0039/R2 allows only while both sides are
    controlled. The plant below is **written out literally** rather than
    generated from the set, and the finding is compared against a **literal**
    rather than against the set, which is the whole of what makes this a
    control: either shortcut would shrink with the set, so removing a member
    would leave both sides agreeing and nothing would red. Written out, a member
    replaced or deleted stops being found in a source that still imports it,
    and a member added reds the pin beside it.
    """
    found = _aliased_spawn_imports(ast.parse(SPAWN_IMPORT_TARGET))
    # A LITERAL, not ``sorted(SPAWN_IMPORT_MODULES)``: the census filters by
    # that set, so a finding compared against the set agrees with it however
    # many members are deleted -- the self-certifying shape this section exists
    # to remove. Written out, a member deleted or replaced stops being found in
    # a source that still imports it and this reds.
    assert sorted(found) == [
        "multiprocessing",
        "os",
        "posix",
        "pty",
        "subprocess",
    ], (
        "a module was dropped from or replaced in SPAWN_IMPORT_MODULES, so a "
        "spawn imported under a bare name from it is now invisible to both "
        f"halves of G-5: found {found}"
    )
    # And the set against the same literal, so a member ADDED cannot slip in
    # without a plant: the two asserts together make any change to the set red.
    assert sorted(SPAWN_IMPORT_MODULES) == [
        "multiprocessing",
        "os",
        "posix",
        "pty",
        "subprocess",
    ], (
        "SPAWN_IMPORT_MODULES changed: plant the new member in "
        "SPAWN_IMPORT_TARGET and re-derive both literals, or it is uncontrolled"
    )
    assert _aliased_spawn_imports(ast.parse("from pathlib import Path")) == [], (
        "the import census now flags a module that cannot spawn"
    )


def test_g5_the_argv_census_fails_rather_than_skips():
    """The default-deny sentence in ``_spawn_argv_heads``, with its control.

    The docstring claims a spawn this cannot enumerate is a FAILURE rather than
    a skipped entry. Three shapes, one per refusal, each asserted to raise and
    to say which shape it was -- without this, "default-deny" is prose and a
    census that silently returned ``[]`` on an unreadable argv would read
    exactly like a clean source.
    """
    for planted, expected in (
        ("import subprocess\nsubprocess.run()\n", "unanalysable spawn-shaped call"),
        ("import subprocess\nsubprocess.run(argv)\n", "not an enumerable literal"),
        (
            "import subprocess\nsubprocess.run([interp, '-m', 'pytest'])\n",
            "neither a literal nor sys.executable",
        ),
    ):
        with pytest.raises(AssertionError, match=expected):
            _spawn_argv_heads(ast.parse(planted))
    # And the shape it *can* read is not refused, or the three above would pass
    # for a census that refuses everything.
    assert _spawn_argv_heads(
        ast.parse("import subprocess, sys\nsubprocess.run([sys.executable, '-m'])\n")
    ) == ["sys.executable"]


def test_g5_a_restore_failure_still_restores_every_registered_path(tmp_path):
    """The restore loop used to abandon its tail at the first failure.

    Planted: the first registered path's backup is removed, so ``cp -p`` cannot
    restore it however the loop goes. The path **after** it must come back
    anyway. Registry order is insertion order, target first, so in this card's
    second anchor the file left behind would have been
    ``src/nonogram/db/session.py`` — a tracked source file, with G-5 forbidding
    a restore with git.
    """
    target = _write(tmp_path, "km_restore_target.py", "def test_x():\n    assert True\n")
    first = _write(tmp_path, "km_first.py", "FIRST = 1\n")
    second = _write(tmp_path, "km_second.py", "SECOND = 1\n")
    runner = Runner(selection=[str(target)], repo_root=tmp_path)
    runner._workdir = tmp_path / "km-workdir-restore"
    runner._workdir.mkdir()
    registry = runner._backup_registry([first, second])
    assert list(registry) == [first, second], list(registry)

    first.write_text("FIRST = mutated\n", encoding="utf-8")
    second.write_text("SECOND = mutated\n", encoding="utf-8")
    registry[first].unlink()

    with pytest.raises(LeakedPatch) as caught:
        runner._restore(registry)

    assert "km_first.py" in str(caught.value), str(caught.value)
    assert "every registered path was restored" in str(caught.value).lower(), str(
        caught.value
    )
    assert second.read_text(encoding="utf-8") == "SECOND = 1\n", (
        "the tail of the registry was abandoned at the first failure, so a "
        "mutated file stayed on disk"
    )
    assert first.read_text(encoding="utf-8") == "FIRST = mutated\n", (
        "the plant must actually fail to restore, or this test certifies nothing"
    )


#: A ``cp`` that reports success and copies nothing, put first on ``PATH``.
#:
#: It shims **restores only** -- ``cp -p <backup> <path>``, recognised by which
#: end the backup is on -- so the backups a restore is verified *against* are
#: still made by the real binary. This is the one shape the second half of G-5
#: exists for: a restore whose exit code says it worked while the bytes on disk
#: are not the backup's. No exit code and no absent-``git`` census can see
#: that; only comparing the two files can, which is what "verified two ways"
#: means.
CP_THAT_COPIES_NOTHING = '''\
#!/bin/sh
# argv is always "-p <source> <destination>": Runner._backup_registry and
# Runner._restore are its only two callers, and they differ in which end the
# backup is on. A source under a "backup." name is a restore -- report success
# and write nothing. Anything else is a backup being made, and runs the real cp.
case "$2" in
    */backup.*) exit 0 ;;
esac
for real in /bin/cp /usr/bin/cp; do
    [ -x "$real" ] && exec "$real" "$@"
done
exit 127
'''


def _cp_that_copies_nothing(folder: Path, monkeypatch) -> Path:
    """Install :data:`CP_THAT_COPIES_NOTHING` first on ``PATH``.

    ``prepend=":"`` rather than ``os.pathsep``: this suite already spawns
    ``cp``, ``diff`` and ``shasum`` by bare name and is POSIX-only for that
    reason, so the separator is not worth an import root.
    """
    shim_dir = folder / "km-lying-cp"
    shim_dir.mkdir()
    shim = shim_dir / "cp"
    shim.write_text(CP_THAT_COPIES_NOTHING, encoding="utf-8")
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", str(shim_dir), prepend=":")
    assert shutil.which("cp") == str(shim), shutil.which("cp")
    return shim_dir


def _a_restore_that_copies_nothing(tmp_path, monkeypatch) -> tuple[str, Path, Path]:
    """Drive the real ``_restore`` over a pair the restore left unequal.

    The order is the whole plant: the ``cp -p`` backups are real, the files are
    **then** mutated, and only then does the lying ``cp`` go on ``PATH``. So
    every ``cp -p`` of the restore exits 0, the loop appends no ``cp`` failure
    at all, and the mutant's bytes are still on disk when the verification runs
    -- the only state in which ``diff -q`` and ``shasum -a 256`` have anything
    to say. Returns what ``_restore`` raised, and the two registered paths.

    One plant, two tests, each asserting only its own arm's message: the two
    comparisons cannot be separated by *input* (both of them read bytes), so
    they are separated by which test names which finding.
    """
    first = _write(tmp_path, "km_lying_first.py", "FIRST = 1\n")
    second = _write(tmp_path, "km_lying_second.py", "SECOND = 1\n")
    runner = Runner(selection=[str(first)], repo_root=tmp_path)
    runner._workdir = tmp_path / "km-workdir-lying-cp"
    runner._workdir.mkdir()
    registry = runner._backup_registry([first, second])

    first.write_text("FIRST = mutated\n", encoding="utf-8")
    second.write_text("SECOND = mutated\n", encoding="utf-8")
    _cp_that_copies_nothing(tmp_path, monkeypatch)

    with pytest.raises(LeakedPatch) as caught:
        runner._restore(registry)

    said = str(caught.value)
    # The plant must be real, or both tests below certify a mismatch that was
    # never there: the files still hold the mutant's bytes, the backups still
    # hold the pristine ones, and no `cp` reported a failure.
    assert first.read_text(encoding="utf-8") == "FIRST = mutated\n", first.read_text(
        encoding="utf-8"
    )
    assert second.read_text(encoding="utf-8") == "SECOND = mutated\n", (
        second.read_text(encoding="utf-8")
    )
    assert registry[first].read_text(encoding="utf-8") == "FIRST = 1\n", registry[
        first
    ].read_text(encoding="utf-8")
    assert "cp -p could not restore" not in said, (
        "the restore must report success, or this is the missing-backup control "
        "again rather than the wrong-bytes one"
    )
    return said, first, second


def test_g5_a_restore_that_copied_nothing_is_caught_by_diff_q(tmp_path, monkeypatch):
    """R1's WITH half for the ``diff -q`` arm of "verified two ways".

    G-5's no-git half is enumerated from the instrument's own AST; *this* half
    had no control that can fail. Both comparisons in
    :meth:`Runner._verification_failures` were neutered line-for-line
    (``if diff.returncode != 0 and 0:`` and ``if len(digests) != len(digests):``)
    and the whole file stayed green -- so a ``cp -p`` that restored the **wrong
    bytes** was reported as verified and nothing here noticed. The two calls
    were pinned only in that they must still be *present*: the argv equality in
    ``test_ac4_restoring_uses_cp_p_backups_and_no_git_command_anywhere`` reds if
    either is deleted. Presence is not catching.

    Measured per arm: neutering the ``diff -q`` comparison alone reds this test
    and leaves its ``shasum`` sibling green, because the sibling asserts only
    the digest finding; neutering both reds the ``pytest.raises`` in the plant
    itself.
    """
    said, first, second = _a_restore_that_copies_nothing(tmp_path, monkeypatch)
    assert f"diff -q says {first} is not its backup" in said, said
    assert f"diff -q says {second} is not its backup" in said, said


def test_g5_a_restore_that_copied_nothing_is_caught_by_shasum_256(
    tmp_path, monkeypatch
):
    """R1's WITH half for the ``shasum -a 256`` arm, over the same plant.

    The second way is not a second spelling of the first: ``diff -q`` compares
    two files, ``shasum -a 256`` reduces each to a digest and compares those,
    and the pair is the reason "verified two ways" is in G-5 at all. Neutering
    the digest comparison alone reds this test and leaves the ``diff -q``
    sibling green.
    """
    said, first, second = _a_restore_that_copies_nothing(tmp_path, monkeypatch)
    assert f"shasum -a 256 says {first} is not its backup" in said, said
    assert f"shasum -a 256 says {second} is not its backup" in said, said


def test_g5_a_restore_that_copied_nothing_fails_the_run_from_its_finally(
    simple_target, tmp_path, monkeypatch
):
    """The same plant, through the real ``finally`` rather than a direct call.

    ``run`` makes its own ``cp -p`` backups -- the lying ``cp`` passes those
    through to the real binary, because the backup is the *destination* there
    -- applies the mutant, and restores in a ``finally``. With the restore
    copying nothing, that ``finally`` is where both verifications meet a
    mismatched pair, and the run must fail there rather than return a matrix:
    the reading is already taken, and a mutant left on disk is what the
    between-mutants re-run and the outer ``finally`` exist to refuse. The temp
    tree is kept, because the backup is then the only intact copy, and the
    exception names the directory it kept.
    """
    runner = _runner(simple_target)
    runner._workdir = tmp_path / "km-workdir-finally"
    runner._workdir.mkdir()
    _cp_that_copies_nothing(tmp_path, monkeypatch)

    with pytest.raises(LeakedPatch, match="backups are kept at") as refusal:
        runner.run(Pass.RECORDING, [_loop_mutant(simple_target)])

    said = str(refusal.value)
    assert f"diff -q says {simple_target} is not its backup" in said, said
    assert f"shasum -a 256 says {simple_target} is not its backup" in said, said
    assert str(runner._workdir) in said, said
    assert (tmp_path / "km-workdir-finally").is_dir(), (
        "a restore that did not verify is the one case where the tree must "
        "survive, and the backup it holds is now the only intact copy"
    )
    assert "LIMIT = 2" in simple_target.read_text(encoding="utf-8"), (
        "the plant must leave the mutant's bytes on disk, or the finally "
        "verified a pair that matched and this test certifies nothing"
    )


def test_g5_a_shasum_that_could_not_run_is_counted_as_a_failure(tmp_path, monkeypatch):
    """The third arm of the same function, and no test reached it.

    The sentence is the module's own: *a ``shasum`` that could not run counted
    as one of those failures*. The binary is external -- ``kill_matrix.py``
    imports no ``hashlib`` on purpose -- so "absent" is a real state of a real
    machine, and until this test the ``OSError`` / ``CalledProcessError`` branch
    that states it ran nowhere.

    Planted by narrowing ``PATH`` to a directory holding ``cp`` and ``diff`` and
    no ``shasum`` at all, so the restore itself genuinely **succeeds**: the file
    comes back, ``diff -q`` agrees, and the only finding is the verification
    that could not run. Asserted together with the *absence* of a ``diff -q``
    finding, which is what holds this test to its own arm instead of
    re-measuring the mismatch above.
    """
    target = _write(tmp_path, "km_no_shasum.py", "VALUE = 1\n")
    runner = Runner(selection=[str(target)], repo_root=tmp_path)
    runner._workdir = tmp_path / "km-workdir-no-shasum"
    runner._workdir.mkdir()
    registry = runner._backup_registry([target])
    target.write_text("VALUE = mutated\n", encoding="utf-8")

    narrow = tmp_path / "km-path-without-shasum"
    narrow.mkdir()
    for tool in ("cp", "diff"):
        real = shutil.which(tool)
        assert real, f"{tool} is not on PATH to begin with"
        (narrow / tool).symlink_to(real)
    monkeypatch.setenv("PATH", str(narrow))
    assert shutil.which("shasum") is None, "the plant did not remove shasum"

    with pytest.raises(LeakedPatch) as caught:
        runner._restore(registry)

    said = str(caught.value)
    assert "shasum -a 256 could not verify" in said, said
    assert "a verification that did not run is not a verification" in said, said
    assert "diff -q says" not in said, (
        "the restore must succeed here, or this is the wrong-bytes control "
        "again rather than the unrunnable-verification one"
    )
    assert target.read_text(encoding="utf-8") == "VALUE = 1\n", (
        "cp -p must still have restored the file: the failure under test is "
        "the verification, not the restore"
    )


def test_g5_a_finished_run_discards_its_temp_tree_and_a_failed_restore_keeps_it(
    simple_target, tmp_path
):
    """The backups, the generated plugin and every ``records-*`` dir.

    One tree per :class:`Runner` and one ``records-*`` per reading used to stay
    in the machine-wide temp directory for good, and this instrument's own
    tests are now part of every gate. Removed when ``run`` returns — and
    **kept** when a restore did not verify, because there the backup is the
    only intact copy; the exception then names the directory it kept.
    """
    runner = _runner(simple_target)
    workdir = runner.workdir
    assert workdir.is_dir(), workdir
    runner.run(Pass.RECORDING, [_loop_mutant(simple_target)])
    assert not workdir.exists(), (
        f"{workdir} outlived the run that made it; a gate calling this "
        "instrument repeatedly accumulates one tree per Runner"
    )
    assert runner._workdir is None

    kept = _runner(simple_target)
    kept._workdir = tmp_path / "kept-workdir"
    kept._workdir.mkdir()

    def _never_verifies(registry):
        raise LeakedPatch("diff -q says a registered path is not its backup")

    kept._restore = _never_verifies
    with pytest.raises(LeakedPatch, match="backups are kept at") as refusal:
        kept.run(Pass.RECORDING)
    assert str(kept._workdir) in str(refusal.value), str(refusal.value)
    assert (tmp_path / "kept-workdir").is_dir(), (
        "the one case where the tree must survive is a restore that did not "
        "verify, and it did not"
    )


# ==========================================================================
# AC-5 (trap 5) — a no-op mutant, and an occurrence the caller did not mean
# ==========================================================================


def test_ac5_a_no_op_mutant_is_refused(simple_target):
    """A mutant whose ``old`` is absent writes nothing and every assert passes."""
    with pytest.raises(MutantRefused) as refusal:
        km.apply_edit(
            simple_target.read_text(encoding="utf-8"),
            Edit(path=simple_target, old='MARK = "<placeholder>"', new='MARK = "rot"'),
        )
    said = str(refusal.value)
    assert "no-op mutant" in said, said
    assert "indistinguishable from a surviving one" in said, said


#: The five-occurrence case from the wild, named in CARD-257's cycle-3 record.
#: A correction that is itself trap 5's shape: what occurs **five** times in
#: ``tests/test_db_engine_lifecycle.py`` is the assert's *message*; the whole
#: source line occurs four times, because ``:950`` asserts ``built`` where the
#: other four assert ``names``. Measured here rather than carried over, and
#: both numbers are asserted below so neither can drift.
#:
#: The **line numbers** are a position in a live file and they have moved. The two
#: *counts* (5 and 4) and the arm's *occurrence* (2) did not move, which is the
#: reason they, and not the positions, are what the anchor is about. Re-derive
#: these from the file rather than trusting them.
NAMES_BLIND_MESSAGE = "no module-level globals found in _init_engine (guard is blind)"
NAMES_BLIND_LINE = (
    '        assert names, "no module-level globals found in _init_engine '
    '(guard is blind)"'
)
NAMES_BLIND_OCCURRENCES = (950, 1060, 1222, 1268, 1395)
#: ``:1060`` is CARD-257's ``NAMES-BLIND`` arm -- the second occurrence, which
#: is the whole point: a caller who did not name it would have mutated
#: ``:950``, in a different test, and read the answer off the wrong arm.
NAMES_BLIND_ARM_OCCURRENCE = 2
LIFECYCLE = REPO / "tests" / "test_db_engine_lifecycle.py"


def test_ac5_the_five_occurrence_case_from_the_wild_must_be_targeted_explicitly():
    """``expect=1`` on text that occurs five times is refused, naming the count.

    And the two counts are held apart, because confusing them is trap 5 again:
    the message occurs **5** times, the whole source line **4**.
    """
    source = LIFECYCLE.read_text(encoding="utf-8")
    assert source.count(NAMES_BLIND_MESSAGE) == len(NAMES_BLIND_OCCURRENCES) == 5, (
        "the fixture moved: this card's AC-5 is the five-occurrence case"
    )
    assert source.count(NAMES_BLIND_LINE) == 4, (
        "the whole line occurs four times -- :816 asserts `built`, not `names`"
    )

    with pytest.raises(MutantRefused) as refusal:
        km.apply_edit(
            source,
            Edit(path=LIFECYCLE, old=NAMES_BLIND_MESSAGE, new="moved by the fixture"),
        )
    said = str(refusal.value)
    assert "occurs 5 times" in said, said
    assert "occurrence=" in said, said


@pytest.mark.parametrize(
    ("occurrence", "lineno"),
    list(enumerate(NAMES_BLIND_OCCURRENCES, start=1)),
)
def test_ac5_an_explicit_occurrence_hits_exactly_that_lineno(occurrence, lineno):
    """Each of the five is reachable, and each hits its own line and no other.

    This is trap 5's second half in the wild: ``occurrence=2`` is CARD-257's
    ``NAMES-BLIND`` arm at ``:1060``, and a caller who did not name it would
    have silently mutated ``:950``, which belongs to a different test.
    """
    source = LIFECYCLE.read_text(encoding="utf-8")
    mutated = km.apply_edit(
        source,
        Edit(
            path=LIFECYCLE,
            old=NAMES_BLIND_MESSAGE,
            new="moved by the AC-5 fixture",
            occurrence=occurrence,
        ),
    )
    moved = [
        number
        for number, (before, after) in enumerate(
            zip(source.splitlines(), mutated.splitlines()), start=1
        )
        if before != after
    ]
    assert moved == [lineno], moved
    assert occurrence != NAMES_BLIND_ARM_OCCURRENCE or lineno == 1060


def test_ac5_an_occurrence_past_the_end_is_refused():
    with pytest.raises(MutantRefused, match="there is no occurrence 6"):
        km.apply_edit(
            LIFECYCLE.read_text(encoding="utf-8"),
            Edit(
                path=LIFECYCLE,
                old=NAMES_BLIND_MESSAGE,
                new="moved by the AC-5 fixture",
                occurrence=6,
            ),
        )


# ==========================================================================
# AC-6 (trap 1) — every figure carries its domain and its denominator
# ==========================================================================


def test_ac6_the_denominator_is_an_assertion_node_count_not_a_collected_test_count(
    simple_target,
):
    """Recomputed by a second route, and held apart from the test count.

    The fixture has 5 assertion nodes and 2 collected tests on purpose: on a
    file where the two numbers agreed, this check could not fail.
    """
    matrix = _runner(simple_target).run(Pass.RECORDING).shipped

    independent = _independent_assert_count(simple_target)
    assert independent == 5, independent
    assert matrix.denominator == independent
    assert matrix.collected_tests == 2, matrix.figure()
    assert matrix.denominator != matrix.collected_tests, (
        "this fixture cannot certify trap 1: pick one where the assertion node "
        "count and the collected test count differ"
    )


def test_ac6_a_figure_quotes_the_node_count_and_names_which_count_it_is(simple_target):
    """The planted mutant for trap 1 swaps the two numbers inside the figure.

    So the figure's number is parsed back out and compared with the independent
    ``ast.walk`` count. A figure that quoted ``collected_tests`` where it says
    "assertion nodes" reds here.
    """
    matrix = _runner(simple_target).run(Pass.RECORDING).shipped
    figure = matrix.figure()

    quoted = re.search(r"of (\d+) assertion nodes", figure)
    assert quoted, figure
    assert int(quoted.group(1)) == _independent_assert_count(simple_target), figure
    assert "collected tests: 2" in figure, figure


def test_ac6_every_figure_this_instrument_prints_carries_its_pass(simple_target):
    """Enumerated from the instrument's AST, defaulting to deny.

    The reporting surface is *derived*: every method of :class:`Matrix` and
    :class:`KillMatrix` named ``figure`` or ``table``. Each one is called and
    its output must name the pass it came from and the denominator's domain. A
    reporting method added tomorrow is inside this check on the day it is added;
    one this cannot call is a failure, never a silent pass.
    """
    tree = ast.parse(INSTRUMENT.read_text(encoding="utf-8"), filename=str(INSTRUMENT))
    reporters = {
        (node.name, method.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for method in node.body
        if isinstance(method, ast.FunctionDef)
        and method.name in {"figure", "table", "report"}
    }
    assert reporters == {
        ("Matrix", "figure"),
        ("Matrix", "table"),
        ("KillMatrix", "figure"),
        ("KillMatrix", "table"),
    }, reporters

    result = _runner(simple_target).run(
        Pass.RERAISING,
        [Mutant("NO-OP-FREE", (Edit(path=simple_target, old="LIMIT = 1", new="LIMIT = 2"),))],
    )
    subjects = {"Matrix": result.shipped, "KillMatrix": result}
    for class_name, method_name in sorted(reporters):
        subject = subjects[class_name]
        printed = getattr(subject, method_name)()
        assert Pass.RERAISING.value in printed, (class_name, method_name, printed)
        assert "assertion node" in printed, (class_name, method_name, printed)
        # The denominator in its LABELLED position, not anywhere in the string.
        # `str(denominator) in printed` read stronger than it was: on this
        # fixture it is satisfied by the "5 PASS" of the counts, so trap 1's own
        # plant -- `{self.denominator}` printed as `{self.collected_tests}` --
        # left this arm green and AC-6 survived only because a sibling test
        # reds. Every one of the four reporters carries the number immediately
        # in front of the domain word, so the position is the claim.
        assert re.search(rf"\b{result.denominator} assertion nodes?\b", printed), (
            class_name,
            method_name,
            printed,
        )
        # The domain is three things, not one: which pass, whether a pytest the
        # target spawned was instrumented too (without which a ``0 BLIND`` is
        # ambiguous), and whether pytest ran at all (without which a FAIL-free
        # reading is ambiguous). Enumerated over the same derived surface.
        assert "pytest exit" in printed, (class_name, method_name, printed)
        assert "child instrumentation off" in printed, (
            class_name,
            method_name,
            printed,
        )


def test_ac6_a_figure_cannot_be_obtained_without_naming_its_pass(simple_target):
    """What happens if the caller does not name the domain: it raises.

    ``pass_`` is positional with no default on :meth:`Runner.run`, and
    :class:`Matrix` refuses a ``pass_`` that is not a :class:`Pass` member. So
    there is no route to a figure that does not carry its domain.
    """
    runner = _runner(simple_target)
    with pytest.raises(TypeError):
        runner.run()
    with pytest.raises(TypeError, match="must be a Pass member"):
        runner.run("recording")

    cells = {1: PASS}
    with pytest.raises(TypeError, match="must be a Pass member"):
        Matrix(
            target=simple_target,
            pass_="recording",
            label="SHIPPED",
            denominator=1,
            cells=cells,
            records={},
            raw_cells=cells,
            collected_tests=1,
            exit_code=0,
            child_instrumentation=False,
        )
    with pytest.raises(TypeError):
        Matrix(
            target=simple_target,
            label="SHIPPED",
            denominator=1,
            cells=cells,
            records={},
            raw_cells=cells,
            collected_tests=1,
            exit_code=0,
            child_instrumentation=False,
        )


def test_ac6_a_matrix_must_report_every_assertion_node(simple_target):
    """The denominator is not a free-text number: it equals the cell count."""
    cells = {1: PASS}
    with pytest.raises(ValueError, match="cells for a denominator"):
        Matrix(
            target=simple_target,
            pass_=Pass.RECORDING,
            label="SHIPPED",
            denominator=5,
            cells=cells,
            records={},
            raw_cells=cells,
            collected_tests=2,
            exit_code=0,
            child_instrumentation=False,
        )


# ==========================================================================
# Guardrails — each with a planted failure, none of them touching the board
# ==========================================================================


def test_g1_an_empty_or_unresolvable_selection_is_refused(tmp_path):
    with pytest.raises(SelectionRefused, match="never runs the full suite"):
        Runner(selection=[], repo_root=tmp_path)
    with pytest.raises(SelectionRefused, match="does not name an existing file"):
        Runner(selection=["tests"], repo_root=REPO)
    with pytest.raises(SelectionRefused, match="does not name an existing file"):
        Runner(selection=["."], repo_root=REPO)


def test_g1_a_selection_spanning_two_files_is_refused(simple_target, tmp_path):
    second = _write(tmp_path, "km_other.py", "def test_x():\n    assert True\n")
    with pytest.raises(SelectionRefused, match="spans 2 files"):
        Runner(selection=[str(simple_target), str(second)], repo_root=tmp_path)


def test_g1_a_run_pytest_never_made_is_not_published_as_a_fail_free_matrix(
    simple_target,
):
    """A resolvable file plus a node id that does not exist. Planted, measured.

    The selection resolves, so no ``SelectionRefused`` fires; pytest then exits
    **4** having collected nothing. Every cell of the reading that follows is
    ``NOT-REACHED``, no cell is ``FAIL``, and the baseline comparison is
    vacuous against an equally blank baseline — so every mutant measured after
    it reads "survived everywhere". ``exit_code`` was recorded and read by
    nothing.

    Exit code is the precondition rather than ``collected_tests`` because that
    number is regex-scraped from pytest's ``-q`` summary: a wording change
    would make it ``None`` on a perfectly good run. It stays print-only.
    """
    runner = Runner(
        selection=[f"{simple_target}::test_no_such_arm"],
        repo_root=simple_target.parent,
    )
    linenos = km.assert_linenos(simple_target.read_text(encoding="utf-8"))

    records, exit_code, output = runner._pytest(Pass.RECORDING)
    assert exit_code not in (0, 1), output
    assert records == {}, records
    assert km.collected_tests(output) is None, output
    assert all(
        km.aggregate_any_red(records.get(lineno, [])) == NOT_REACHED
        for lineno in linenos
    ), "the reading this would have published is not blank, so nothing is shown"

    with pytest.raises(km.UnmeasuredRun, match="is not a reading") as refusal:
        runner.run(Pass.RECORDING)
    assert f"pytest exited {exit_code}" in str(refusal.value), str(refusal.value)


def test_g1_a_run_whose_tests_failed_is_a_reading_and_is_published(simple_target):
    """The other side of that precondition, so it cannot be widened by mistake.

    Exit **1** is what a killed mutant and the whole re-raising pass look like
    from outside, so it must stay inside the set. The recording pass exits 0
    because it suppresses the ``AssertionError``; the re-raising pass does not.
    """
    mutant = Mutant(
        "MARK-ROT",
        (Edit(path=simple_target, old='MARK = "shipped"', new='MARK = "rotted!"'),),
    )
    killed = _runner(simple_target).run(Pass.RERAISING, [mutant]).mutants["MARK-ROT"]

    assert killed.exit_code == 1, killed.figure()
    assert killed.failed, killed.table()
    assert f"pytest exit {killed.exit_code}" in killed.figure()


#: Every arm of this file sits behind a fixture that errors, so pytest exits 1
#: with **no** assertion node reached. That is the SHIPPED half of the shape
#: F-202 reproduced: a blank baseline against which every mutant "survived"
#: every arm.
ERRORING_TARGET = '''\
"""Two arms, both behind a fixture that errors before any assert runs."""
import pytest


@pytest.fixture
def broken():
    raise RuntimeError("the fixture errored before any assert ran")


def test_one(broken):
    assert broken == 1


def test_two(broken):
    assert broken == 2
'''

#: One in-domain arm, plus a test whose failure is expressed through
#: ``pytest.raises`` — outside the matrix's domain of ``ast.Assert`` nodes, so
#: no cell can account for it. The sibling is what the two mutants edit.
OUT_OF_DOMAIN_TARGET = '''\
"""One assertion node, and one kill this matrix has no cell for."""
import pytest

import km_raiser


def test_in_domain():
    assert km_raiser.MARK == "shipped"


def test_out_of_domain():
    with pytest.raises(ValueError):
        km_raiser.boom()
'''

RAISER = '''\
MARK = "shipped"


def boom():
    raise ValueError("shipped")
'''


def test_g1_a_shipped_that_reached_nothing_is_not_a_baseline(tmp_path):
    """The blank baseline, planted first and then refused.

    pytest exits **1** here (two errors), which is a reading, and every cell is
    ``NOT-REACHED`` with no cell ``FAIL`` — so the reading is published shape
    for shape, and as a baseline it makes every later mutant survive every arm
    by construction. The gate that already owns "SHIPPED must be trustworthy"
    refuses it on the quantity its own aggregate figure already prints
    (``0 FAIL of 0 reached``), not on the exit code: ``exit 1`` with no ``FAIL``
    cell is *also* what a kill outside the matrix's domain looks like, and
    position cannot tell the two apart.
    """
    target = _write(tmp_path, "km_erroring_target.py", ERRORING_TARGET)
    runner = _runner(target)
    pristine = target.read_text(encoding="utf-8")
    linenos = km.assert_linenos(pristine)
    assert len(linenos) == 2, linenos

    blank = runner._measure("SHIPPED", Pass.RECORDING, len(linenos), pristine)
    assert blank.exit_code == 1, blank.figure()
    assert blank.failed == (), blank.table()
    assert blank.not_reached == tuple(sorted(linenos)), blank.table()

    with pytest.raises(LeakedPatch, match="reached no assertion node") as refusal:
        runner.run(Pass.RECORDING)
    said = str(refusal.value)
    assert "0 FAIL" in said and "2 NOT-REACHED" in said, said
    assert "pytest exit 1" in said, (
        "the refusal must carry the shape it refused, including the exit code "
        "it deliberately did not key on"
    )


def test_g1_a_kill_outside_the_matrix_domain_is_attributable_in_the_figure(tmp_path):
    """Two mutants with **identical** cells, told apart by the figure alone.

    The matrix's domain is ``ast.Assert`` nodes. ``MESSAGE-ROT`` is a genuine
    survivor (exit 0). ``RAISE-WRONG-TYPE`` is a genuine, correctly detected
    kill expressed through ``pytest.raises`` (exit 1) — a failure **no cell can
    account for**, so its column is FAIL-free and cell-for-cell identical to
    the survivor's. Neither is refused: a refusal keyed on *exit 1 and no FAIL
    cell* cannot tell either from a run that never happened, and
    ``UnmeasuredRun`` propagates out of ``run``, so it would destroy the whole
    run's readings over one out-of-domain kill. The distinction is carried
    instead — each mutant's own exit code and reached count, in the aggregate
    figure a consumer reads.
    """
    raiser = _write(tmp_path, "km_raiser.py", RAISER)
    target = _write(tmp_path, "km_out_of_domain_target.py", OUT_OF_DOMAIN_TARGET)
    survivor = Mutant(
        "MESSAGE-ROT",
        (Edit(path=raiser, old='ValueError("shipped")', new='ValueError("rotted!")'),),
    )
    out_of_domain = Mutant(
        "RAISE-WRONG-TYPE", (Edit(path=raiser, old="ValueError", new="TypeError"),)
    )
    result = _runner(target).run(Pass.RERAISING, [survivor, out_of_domain])

    assert result.denominator == 1, result.figure()
    killed = result.mutants["RAISE-WRONG-TYPE"]
    lived = result.mutants["MESSAGE-ROT"]
    assert killed.cells == lived.cells == result.shipped.cells, result.table()
    assert killed.failed == () and lived.failed == (), result.table()
    assert killed.exit_code == 1, killed.figure()
    assert lived.exit_code == 0, lived.figure()

    figure = result.figure()
    assert "RAISE-WRONG-TYPE exit 1 with 1 reached and 0 FAIL" in figure, figure
    assert "MESSAGE-ROT exit 0 with 1 reached and 0 FAIL" in figure, figure
    assert figure in result.table(), result.table()
    assert result.shipped.cells[next(iter(result.shipped.cells))] == PASS, (
        "the in-domain arm must be reached, or this measures a blank baseline "
        "instead of an out-of-domain kill"
    )


def test_g2_the_lock_it_watches_is_the_one_the_gates_write(monkeypatch, tmp_path):
    """The resolved path, compared against its owner. The control that can fail.

    The previous control planted a lock in ``tmp_path`` and passed
    ``repo_root=tmp_path``, which a tmp tree makes unfalsifiable: it has no
    ``.git``, so ``main_repo_root(tmp_path)`` is ``tmp_path`` itself and the
    re-derived path and the owner's coincide — the control passed under the
    broken implementation and under the fixed one alike.

    Driven from a linked worktree they diverge, and the divergence is the whole
    finding: every gate writes the **main** checkout's file whichever worktree
    it runs the suite in (``tests/test_full_suite_lock.py``'s own
    ``test_every_worktree_resolves_the_one_lock_the_gates_write`` — "a
    per-worktree lock path would be a guard that cannot see contention").
    """
    monkeypatch.delenv(full_suite_lock.LOCK_PATH_VAR, raising=False)
    worktree = full_suite_lock.this_worktree()
    main = full_suite_lock.main_repo_root(worktree)

    assert km.board_lock_path() == full_suite_lock.lock_path()
    assert km.board_lock_path() == main.joinpath(*full_suite_lock.LOCK_RELATIVE_PATH)
    if main != worktree:
        assert worktree not in km.board_lock_path().parents, (
            "this run is in a linked worktree and the instrument is still "
            "watching a path inside it: that is a guard that cannot see the "
            "only contention there is"
        )

    monkeypatch.setenv(full_suite_lock.LOCK_PATH_VAR, str(tmp_path / "elsewhere"))
    assert km.board_lock_path() == tmp_path / "elsewhere", (
        "the override the board relocates the lock with is not honoured, so the "
        "guard cannot be pointed at the right file either"
    )


def test_g2_a_foreign_lock_refuses_the_start_and_repo_root_does_not_move_it(
    simple_target, tmp_path, monkeypatch
):
    """Planted on a tmp path via the override. The board's real lock is never
    created, deleted or touched — the override exists for exactly that.

    The decoy is the other half: a lock at ``repo_root/meta/kanban/`` is the
    file the broken implementation watched and no gate writes, so it must
    **not** refuse. That is what reds if the two jobs are conflated again.

    The holder named here is an **absolute path that is not this tree**, so the
    refusal under test is the foreign-holder branch and not the unanalysable
    one a relative ``worktree:`` takes (that one has its own control below).
    """
    monkeypatch.delenv(full_suite_lock.OVERRIDE, raising=False)
    lock = tmp_path / "planted" / ".full-suite.lock"
    lock.parent.mkdir(parents=True)
    monkeypatch.setenv(full_suite_lock.LOCK_PATH_VAR, str(lock))
    foreign = tmp_path / "another-worktree"

    decoy = tmp_path.joinpath(*full_suite_lock.LOCK_RELATIVE_PATH)
    decoy.parent.mkdir(parents=True)
    decoy.write_text(f"worktree: {foreign}\n", encoding="utf-8")
    assert not lock.exists()
    assert Runner(selection=[str(simple_target)], repo_root=tmp_path).target, (
        "a lock under the given repo_root is not a lock any gate wrote"
    )

    lock.write_text(f"worktree: {foreign}\n", encoding="utf-8")
    with pytest.raises(LockHeld, match="holds the board's full-suite lock") as held:
        Runner(selection=[str(simple_target)], repo_root=tmp_path)
    assert str(lock) in str(held.value), str(held.value)

    lock.write_text("worktree: planted-by-test\n", encoding="utf-8")
    with pytest.raises(LockHeld, match="holds the board's full-suite lock"):
        Runner(selection=[str(simple_target)], repo_root=tmp_path)

    lock.unlink()
    assert Runner(selection=[str(simple_target)], repo_root=tmp_path).target


def test_g2_a_lock_this_worktree_holds_does_not_refuse_the_start(
    simple_target, tmp_path, monkeypatch
):
    """The gate's own lock. This is what reds if the strict rule comes back.

    Every full-suite gate writes this file naming the worktree it then runs the
    suite in, and holds it for the whole run — so an implementation that
    refuses on *any* lock cannot run inside the gate that must certify it. It
    was measured exactly once, as 23 reds in build gate 3 with one cause, and
    it is the condition no solo run can produce: standing alone the same file
    was 60/60 twenty minutes earlier, because no lock was held then.

    ``this_worktree()`` is the owner's own notion of "this tree" — the parent of
    the ``tests/`` directory these modules live in — which is what the gate
    writes and what :func:`full_suite_lock.verdict` compares against. Planted on
    a tmp path through the override, so the real file is still never touched.
    """
    monkeypatch.delenv(full_suite_lock.OVERRIDE, raising=False)
    lock = tmp_path / "planted" / ".full-suite.lock"
    lock.parent.mkdir(parents=True)
    monkeypatch.setenv(full_suite_lock.LOCK_PATH_VAR, str(lock))
    lock.write_text(
        f"holder: a full-suite gate\nworktree: {full_suite_lock.this_worktree()}\n",
        encoding="utf-8",
    )

    assert km.board_lock_path() == lock, "the plant is not the file the guard reads"
    assert Runner(selection=[str(simple_target)], repo_root=tmp_path).target, (
        "a lock this instrument's own worktree holds refused the start: that is "
        "the rule that cannot run inside the gate that must certify it"
    )


def test_g2_the_refusal_is_its_owners_verdict_and_not_a_second_opinion(
    simple_target, tmp_path, monkeypatch
):
    """Four lock states, and the instrument's answer is the owner's every time.

    The equality is the point: ``_refuse_if_lock_held`` takes
    :func:`full_suite_lock.current_verdict` **whole** rather than re-deriving a
    rule, so this reds the day a second opinion is written into the instrument
    — which is how F-001 happened the first time (a re-derived path) and how
    build gate 3's 23 reds happened the second (a re-derived strictness).

    The two relaxations that come with the verdict are controlled here rather
    than only declared: a foreign holder past
    :data:`full_suite_lock.STALE_SECONDS` is presumed gone by the board, and an
    announced override says run anyway. Both are the decision that admitted
    *this* pytest process, and an instrument stricter than that reds a suite the
    board deliberately decided to run. The stale case is a fixed date in the
    past and the fresh one is the lock file's own mtime, so no clock is read
    here either (G-6).
    """
    lock = tmp_path / "planted" / ".full-suite.lock"
    lock.parent.mkdir(parents=True)
    monkeypatch.setenv(full_suite_lock.LOCK_PATH_VAR, str(lock))
    foreign = f"worktree: {tmp_path / 'another-worktree'}\n"
    mine = f"worktree: {full_suite_lock.this_worktree()}\n"
    # No ``at:`` means the file's own mtime stands in, and these are written a
    # line above the reading — fresh without a clock being read here.
    fresh = ""
    ancient = "at: 2020-01-01T00:00:00Z\n"

    cases = {
        "a foreign tree holds it": (foreign + fresh, False, False),
        "this tree holds it": (mine + fresh, False, True),
        "a foreign tree left it behind": (foreign + ancient, False, True),
        "a foreign tree holds it, override set": (foreign + fresh, True, True),
    }
    for name, (text, overridden, expected) in cases.items():
        lock.write_text(text, encoding="utf-8")
        if overridden:
            monkeypatch.setenv(full_suite_lock.OVERRIDE, "1")
        else:
            monkeypatch.delenv(full_suite_lock.OVERRIDE, raising=False)

        owner_allowed, _ = full_suite_lock.current_verdict()
        try:
            Runner(selection=[str(simple_target)], repo_root=tmp_path)
            instrument_allowed = True
        except LockHeld:
            instrument_allowed = False

        assert instrument_allowed is expected, name
        assert instrument_allowed is owner_allowed, (
            f"{name}: the instrument answered {instrument_allowed} where its "
            f"owner answers {owner_allowed} — that is a second opinion, and the "
            "two divergences this card has already paid for were both one"
        )


def test_g3_an_edit_that_touches_the_database_guard_is_refused(tmp_path):
    """The live panel's database is never named, and the guard is never widened."""
    with pytest.raises(MutantRefused, match="database guard"):
        Edit(
            path=tmp_path / "anything.py",
            old="_refuse_unless_test_database(url)",
            new="pass",
        )
    with pytest.raises(MutantRefused, match="nonogram_poc"):
        Edit(path=tmp_path / "anything.py", old="a = 1", new='a = "nonogram_poc"')


@pytest.mark.parametrize(
    "spelling",
    [
        pytest.param(Path("tests") / "conftest.py", id="conftest"),
        pytest.param(Path("tests") / "database_guard.py", id="database_guard"),
        pytest.param(Path("tests") / "CONFTEST.py", id="mis-cased-file"),
        pytest.param(Path("TESTS") / "conftest.py", id="mis-cased-directory"),
        pytest.param(Path("tests") / "DATABASE_GUARD.py", id="mis-cased-other-half"),
        pytest.param(
            Path("tests") / "helpers" / ".." / "conftest.py", id="dot-dot-spelling"
        ),
        pytest.param(REPO / "tests" / "Conftest.py", id="absolute-mis-cased"),
    ],
)
def test_g3_every_spelling_of_a_guard_file_is_refused(spelling):
    """Both halves of the guard, under every spelling that names the same file.

    The shipped refusal compared raw path *parts*, so on this board's
    case-insensitive volume ``tests/CONFTEST.py`` named ``tests/conftest.py``
    and walked straight past it — and ``Edit.__post_init__`` is the only gate
    there is, because ``Runner._apply`` writes to ``edit.path`` with no
    re-check. ``tests/database_guard.py`` is the half that had no control at
    all; it is the guard's other half (``verdict``, ``OPT_OUT``,
    ``report_line`` and a ``pytest_configure`` that raises), so an edit to it
    is the same hazard as an edit to the first.
    """
    with pytest.raises(MutantRefused, match="carries the database guard"):
        Edit(path=spelling, old="a = 1", new="a = 2")


def test_g3_an_edit_that_defeats_the_guard_without_naming_it_is_refused_by_path():
    """The text half's blind spot, and what actually closes it.

    ``_FORBIDDEN_TEXT`` is two literals, and an edit can defeat the guard
    without naming either: ``tests/conftest.py`` decides there whether the
    database its fixtures erase must be named ``*_test``, and dropping the
    suffix preserves the line count and names neither literal — so
    ``_refuse_line_shift`` and the text refusal both pass it. What refuses it
    is the **path** half, by identity, which is the whole argument for keeping
    the path refusal by identity rather than enumerating more strings.
    """
    guard = REPO / "tests" / "conftest.py"
    source = guard.read_text(encoding="utf-8")
    defeat, kept = '.endswith("_test")', '.endswith("")'
    assert defeat in source, (
        "the check this control is built on moved: find the one that decides "
        "which database the destructive fixtures may erase, and re-derive it"
    )
    assert "DROP SCHEMA public CASCADE" in source, (
        "the destructive statement this guard stands in front of moved"
    )
    assert source.count(defeat) == 1, source.count(defeat)
    assert not [
        banned
        for banned in km._FORBIDDEN_TEXT
        if banned in defeat or banned in kept
    ], (
        "this control certifies nothing if the edit names a banned literal: it "
        "exists to show what the text half cannot see"
    )
    assert len(source.replace(defeat, kept).splitlines()) == len(source.splitlines())

    for spelling in (guard, Path("tests") / "CONFTEST.py"):
        with pytest.raises(MutantRefused, match="carries the database guard"):
            Edit(path=spelling, old=defeat, new=kept)


def test_the_generated_plugin_names_exactly_the_env_vars_the_runner_sets():
    """The plugin is generated source, so its env-var names can drift from the
    runner's constants. Enumerated here rather than trusted: the three names the
    runner puts in the child environment are exactly the three the plugin reads.

    Two directions, both through ``_hard_coded_env_names``: the **rendered**
    plugin must read exactly those three, and the **unrendered** template must
    carry none of them literally. The second is an absence-assertion, so it sits
    beside a planted template that does hard-code one -- without that plant, an
    inert ``ENV_NAME_SHAPE`` would read as a clean template. Measured:
    neutering that pattern reds the rendered-equality arm and the planted arm.
    """
    constants = {
        km._ENV_TARGET: "target",
        km._ENV_RECORD_DIR: "record dir",
        km._ENV_RERAISE: "reraise flag",
    }
    assert len(constants) == 3, constants
    rendered = km._PLUGIN_SOURCE.format(
        instrument_dir="/dev/null",
        env_target=km._ENV_TARGET,
        env_record_dir=km._ENV_RECORD_DIR,
        env_reraise=km._ENV_RERAISE,
    )
    read_by_plugin = set(_hard_coded_env_names(rendered))
    assert read_by_plugin == set(constants), (read_by_plugin, set(constants))
    # The absence half, with its control: the *unrendered* template must carry
    # no env-var name literally, or it can drift from the runner's constants.
    # `_hard_coded_env_names` is the same callable the equality above runs
    # through, and it finds the names in a planted template, so an inert
    # pattern reds there rather than reading as a clean template here.
    assert _hard_coded_env_names(km._PLUGIN_SOURCE) == [], (
        "the plugin source still hard-codes an env-var name, so it can drift "
        "from the runner's constants"
    )
    planted = f"import os\nT = os.environ['{km._ENV_TARGET}']\n"
    assert _hard_coded_env_names(planted) == [km._ENV_TARGET], (
        "the env-name census no longer finds a hard-coded name, so the empty "
        "finding above is vacuous"
    )
    assert _hard_coded_env_names("import os\nT = os.environ[env_target]\n") == [], (
        "the env-name census now flags the format field, which is the shape the "
        "template is supposed to use"
    )


def test_g4_the_instrument_imports_stdlib_and_one_named_sibling():
    """Enumerated from the AST; the baseline is stdlib plus a pinned allowance.

    G-4 is about a new **runtime dependency**. The one non-stdlib root here is a
    module of this same ``tests/`` directory — ``full_suite_lock``, which
    *owns* the lock path G-2 refuses on and is imported precisely so that path
    is not re-derived a second way (that divergence was F-001). Both spellings
    of that one import appear, because the module is imported as
    ``tests.kill_matrix`` by this suite and as bare ``kill_matrix`` by the
    generated plugin.

    The allowance is pinned to that set rather than opened to "anything local":
    a third-party import reds here on the day it is added, and so does a
    sibling nobody declared.
    """
    tree = ast.parse(INSTRUMENT.read_text(encoding="utf-8"), filename=str(INSTRUMENT))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 or node.module, f"unanalysable import at {node.lineno}"
            roots.add((node.module or "").split(".")[0])

    extra = roots - set(sys.stdlib_module_names)
    assert extra == {"tests", "full_suite_lock"}, extra
    assert (REPO / "tests" / "__init__.py").is_file()
    assert (REPO / "tests" / "full_suite_lock.py").is_file(), (
        "the allowance names a module that is not a file of this tree's tests/"
    )


#: A source that reads a clock every way G-6's two censuses claim to see: it
#: imports every member of ``TIMING_MODULES`` and names every member of
#: ``CLOCK_NAMES``. Written out rather than generated from those sets -- a plant
#: generated from a set shrinks with it, so a deleted member would leave the
#: finding and the expectation agreeing and nothing would red, which is the
#: defect this whole section exists to remove.
CLOCK_READING_TARGET = '''\
import cProfile
import datetime
import resource
import time
import timeit

START = time.perf_counter()
TICK = time.monotonic()
CPU = time.process_time()
WALL = time.time()
SPENT = "elapsed"
'''


def test_g6_the_instrument_takes_no_timing_measurement():
    """No clock is read, so no figure here can be a duration.

    Enumerated two ways: ``TIMING_MODULES`` is not imported, and no member of
    ``CLOCK_NAMES`` is named anywhere in the source. ``subprocess``'s
    ``timeout=`` is a bound on a hung child, not a measurement, and is
    deliberately outside both sets.

    This is the WITHOUT half of R1, and on a clean source it cannot tell a
    holding set from a set of nonsense -- measured: replacing the module set
    with one non-existent name left the whole file green. Its WITH half is
    ``test_g6_the_timing_censuses_catch_a_planted_clock``, which runs these same
    two callables over a source that reads a clock every way the two sets name,
    and which also carries the ``timeout=`` distinction as an assertion rather
    than as this sentence. Replacing a member of either set now reds there.
    """
    source = INSTRUMENT.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(INSTRUMENT))
    assert _timing_module_imports(tree) == [], _timing_module_imports(tree)
    assert _clock_names_in(source) == [], (
        f"{_clock_names_in(source)} is a clock; G-6 forbids reading one"
    )


def test_g6_the_timing_censuses_catch_a_planted_clock():
    """R1's WITH half for both of G-6's censuses.

    Neither set has an authority to be derived from -- "modules that read a
    clock" and "functions that read a clock" are hand-written, which
    ADR-0039/R2 allows only while both sides are controlled. So
    ``CLOCK_READING_TARGET`` spells out **every** member of both sets, as text
    rather than generated from them, and the findings are held to **literals**
    rather than to the sets themselves -- a census filters by its own set, so a
    finding compared against that set agrees with it however many members are
    deleted, which is the self-certifying shape this section exists to remove.
    The WITHOUT half cannot do any of this: a set of nothing but nonsense names
    finds nothing in a clean source either.
    """
    # LITERALS on both sides, not ``sorted(TIMING_MODULES)`` / ``CLOCK_NAMES``:
    # each census filters by its own set, so a finding compared against that set
    # agrees with it however many members are deleted. Against a literal, a
    # member deleted or replaced stops being found in a source that still reads
    # it (the first assert of each pair), and a member added cannot slip in
    # without a plant (the second).
    planted_modules = ["cProfile", "datetime", "resource", "time", "timeit"]
    found_modules = _timing_module_imports(ast.parse(CLOCK_READING_TARGET))
    assert found_modules == planted_modules, (
        "a module was dropped from or replaced in TIMING_MODULES, so importing "
        f"it is now invisible to G-6: found {found_modules}"
    )
    assert sorted(TIMING_MODULES) == planted_modules, (
        "TIMING_MODULES changed: plant the new member in CLOCK_READING_TARGET "
        "and re-derive this literal, or it is uncontrolled"
    )

    planted_names = [
        "perf_counter",
        "monotonic",
        "process_time",
        "time()",
        "elapsed",
    ]
    found_names = _clock_names_in(CLOCK_READING_TARGET)
    assert found_names == planted_names, (
        "a name was dropped from or replaced in CLOCK_NAMES, so naming it is "
        f"now invisible to G-6: found {found_names}"
    )
    assert list(CLOCK_NAMES) == planted_names, (
        "CLOCK_NAMES changed: plant the new member in CLOCK_READING_TARGET and "
        "re-derive this literal, or it is uncontrolled"
    )

    # The other side, or a census that answered "everything is a clock" would be
    # just as inert: `timeout=` is a bound on a hung child, not a measurement,
    # and the instrument's own spelling of it must stay outside both halves.
    outside = "import subprocess\nsubprocess.run(['cp'], timeout=600)\n"
    assert _timing_module_imports(ast.parse(outside)) == [], outside
    assert _clock_names_in(outside) == [], outside


# ==========================================================================
# AC-7 — the two matrices this board already measured three independent ways
# ==========================================================================

LOCK_GUARD_TEST = REPO / "tests" / "test_full_suite_lock.py"


def test_ac7_the_lock_guard_file_reproduces_130_of_130_pass_and_reached():
    """``tests/test_full_suite_lock.py`` at ``ddb1731b``: the first anchor.

    CARD-256's record, corroborated there by an independent ``ast.walk`` count
    and by a ``sys.monitoring`` LINE tracer: **130** assertion nodes, 130 PASS
    and reached, zero NOT-REACHED. And ``41`` is the *collected test* count, not
    an assertion count -- the confusion that was gating finding #1.
    """
    counted = _independent_assert_count(LOCK_GUARD_TEST)
    assert counted == 130, (
        f"{LOCK_GUARD_TEST.name} now has {counted} assertion nodes, not 130. "
        "This anchor pins a live file that keeps gaining census-moving asserts: "
        "re-derive the bound rather than the expectation -- confirm the new "
        "count independently, then update it here and in the card's AC-7 record."
    )

    runner = Runner(selection=[str(LOCK_GUARD_TEST)], repo_root=REPO)
    matrix = runner.run(Pass.RECORDING).shipped

    assert matrix.denominator == 130, matrix.figure()
    assert len(matrix.passed) == 130, matrix.table()
    assert matrix.not_reached == (), matrix.table()
    assert matrix.failed == (), matrix.table()
    assert matrix.collected_tests == 41, (
        "41 is the collected test count and must never be the denominator: "
        + matrix.figure()
    )


SESSION_PY = REPO / "src" / "nonogram" / "db" / "session.py"
FOUR_ARM = (
    "tests/test_db_engine_lifecycle.py"
    "::TestEngineLifecycle_TheResetIsAPublishedSeam"
    "::test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters"
)
#: CARD-257's four arms, restated from its cycle-3 record and re-derived from
#: the unmodified parse below rather than trusted.
PREAMBLE, NAMES, HEADS, POINTER = 1060, 1136, 1143, 1149
WORD = r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])"


def _docstring_span(path: Path, kind, name: str) -> tuple[int, int]:
    """Character offsets of one function's or class's docstring in its file."""
    source = path.read_text(encoding="utf-8")
    starts = [0]
    for line in source.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if isinstance(node, kind) and getattr(node, "name", None) == name:
            doc = node.body[0].value
            assert isinstance(doc, ast.Constant), name
            return (
                starts[doc.lineno - 1] + doc.col_offset,
                starts[doc.end_lineno - 1] + doc.end_col_offset,
            )
    raise AssertionError(f"{name} has no docstring in {path}")


def _scoped_edits(
    path: Path, span: tuple[int, int], needle: str, replacement: str, *, whole_word: bool
) -> tuple[Edit, ...]:
    """Edits that hit ``needle`` only inside ``span``, by explicit occurrence.

    This is trap 5's second half applied to the anchor itself: ``setattr(``
    occurs 6 times in one docstring and 32 times in the file around it, so a
    by-text or first-occurrence substitution would mutate code rather than the
    text under measurement. Every edit therefore names its 1-based occurrence,
    counted over the whole file, and they are emitted in **descending** order so
    an earlier replacement cannot renumber a later one.
    """
    source = path.read_text(encoding="utf-8")
    start, end = span
    plain = [match.start() for match in re.finditer(re.escape(needle), source)]
    pattern = WORD.format(re.escape(needle)) if whole_word else re.escape(needle)
    targets = [
        match.start()
        for match in re.finditer(pattern, source)
        if start <= match.start() < end
    ]
    assert targets, (path.name, needle, whole_word)
    assert "\n" not in replacement and needle not in replacement
    return tuple(
        Edit(path=path, old=needle, new=replacement, occurrence=plain.index(offset) + 1)
        for offset in sorted(targets, reverse=True)
    )


def _init_engine_globals() -> tuple[str, ...]:
    """The three globals, from ``session.py``'s own AST — the arms' own authority."""
    tree = ast.parse(SESSION_PY.read_text(encoding="utf-8"), filename=str(SESSION_PY))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_init_engine":
            declared = {
                name
                for child in ast.walk(node)
                if isinstance(child, ast.Global)
                for name in child.names
            }
            assigned = {
                target.id
                for child in ast.walk(node)
                if isinstance(child, ast.Assign)
                for target in child.targets
                if isinstance(target, ast.Name)
            }
            return tuple(sorted(declared & assigned))
    raise AssertionError("session.py has no _init_engine")


def _four_arm_grid() -> tuple[list[Mutant], dict[str, frozenset[int]]]:
    """CARD-257's AC-2 columns, derived from the two texts rather than quoted.

    Returns the mutants and, per mutant, the arms CARD-257 recorded as RED. The
    three names and the two spelling heads come from the same authority the arms
    themselves read, so this set cannot drift away from them (ADR-0039/R2).
    """
    names = _init_engine_globals()
    assert len(names) == 3, names
    head_name = names[0]
    prod = _docstring_span(SESSION_PY, ast.FunctionDef, "reset_engine")
    guard = _docstring_span(
        LIFECYCLE, ast.ClassDef, "TestEngineLifecycle_TheResetIsAPublishedSeam"
    )
    texts = (("prod", SESSION_PY, prod), ("guard", LIFECYCLE, guard))

    mutants: list[Mutant] = []
    reds: dict[str, frozenset[int]] = {}

    # Six DOC-NAME-DEL cells: one global dropped from one text as a whole word.
    for name in names:
        for label, path, span in texts:
            key = f"DOC-NAME-DEL[{name}@{label}]"
            mutants.append(
                Mutant(
                    key,
                    _scoped_edits(path, span, name, "Z" * len(name), whole_word=True),
                )
            )
            reds[key] = frozenset({NAMES})

    # Four DOC-HEAD-DEL cells: two spelling heads x two texts. The heads are
    # read off the scan's own patterns; the texts write the second one with the
    # ``<name>`` placeholder, which is the form on disk.
    for head, written in (("setattr(", "setattr("), (f".{head_name}", ".<name>")):
        for label, path, span in texts:
            key = f"DOC-HEAD-DEL[{head}@{label}]"
            mutants.append(
                Mutant(
                    key,
                    _scoped_edits(
                        path,
                        span,
                        written,
                        "_" + written[1:] if written.startswith(".") else "setattrX",
                        whole_word=False,
                    ),
                )
            )
            reds[key] = frozenset({HEADS})

    # NAMES-BLIND: the derived set goes empty, so the preamble reds and the
    # three arms below it are never reached. ``global`` appears twice in
    # session.py, which is why this one names its occurrence too.
    declaration = f"global {', '.join(('engine', 'SessionLocal', '_engine_url'))}"
    assert SESSION_PY.read_text(encoding="utf-8").count(declaration) == 2
    init_span = _function_span(SESSION_PY, "_init_engine")
    mutants.append(
        Mutant(
            "NAMES-BLIND",
            _scoped_edits(
                SESSION_PY,
                init_span,
                declaration,
                "global " + "_".ljust(len(declaration) - 7, "z"),
                whole_word=False,
            ),
        )
    )
    reds["NAMES-BLIND"] = frozenset({PREAMBLE})

    # The pointer arm's three readings, which is where CARD-257's cycle 2 found
    # its defect: two kills and one deliberate PASS.
    dotted = f"nonogram.db.session.{'reset_engine'}"
    mutants.append(
        Mutant(
            "POINTER-ROT",
            _scoped_edits(LIFECYCLE, guard, dotted, dotted[:-12] + "gone_engine", whole_word=False),
        )
    )
    reds["POINTER-ROT"] = frozenset({POINTER})
    mutants.append(
        Mutant(
            "POINTER-DEL-WORD",
            _scoped_edits(LIFECYCLE, guard, "reset_engine", "ZZZZZZZZZZZZ", whole_word=True),
        )
    )
    reds["POINTER-DEL-WORD"] = frozenset({POINTER})
    mutants.append(
        Mutant(
            "CONTROLS-RENAME-ONLY",
            _scoped_edits(
                LIFECYCLE,
                guard,
                "test_reset_engine_is_public_and_says_who_calls_it",
                "test_the_reset_of_engines_is_public_and_says_caller",
                whole_word=False,
            ),
        )
    )
    reds["CONTROLS-RENAME-ONLY"] = frozenset()
    return mutants, reds


def _function_span(path: Path, name: str) -> tuple[int, int]:
    source = path.read_text(encoding="utf-8")
    starts = [0]
    for line in source.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    for node in ast.parse(source, filename=str(path)).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return (
                starts[node.lineno - 1],
                starts[node.end_lineno - 1] + node.end_col_offset,
            )
    raise AssertionError(f"{path} has no top-level {name}")


def test_ac7_the_four_arm_grid_of_card_257_reproduces():
    """``tests/test_db_engine_lifecycle.py``: the second anchor, CARD-257's grid.

    The **grid** is CARD-257's, measured at ``b441ba00``. The **positions** are
    not: they are ``:1060`` (preamble), ``:1136`` (names), ``:1143`` (heads)
    and ``:1149`` (pointer) at HEAD. That is the anchor's own distinction: what reproduces is
    the grid cell for cell, not an address. Re-derived from the unmodified
    parse here, never reused from a previous reading.

    **The shift still overlaps, measured rather than assumed.** Of the four
    previous addresses, none (``:1077``, ``:1121``, ``:1128``, ``:1134``) is an
    assert lineno at HEAD, so a stale constant reads loudly here. That is the
    seventh shape this
    instrument refuses for a *mutant* standing inside its own anchor, whose
    precondition (``set(arms) <= linenos``) is a membership test and cannot
    tell the two apart. Recorded, not routed around: the constants above are
    updated in the same commit as the file they index.

    What must come back: six ``DOC-NAME-DEL`` cells RED at the names arm, four
    ``DOC-HEAD-DEL`` cells RED at the heads arm, ``NAMES-BLIND`` RED at the
    preamble with the three arms below it NOT-REACHED, ``POINTER-ROT`` and
    ``POINTER-DEL-WORD`` RED at the pointer arm, ``CONTROLS-RENAME-ONLY`` PASS,
    and SHIPPED all-PASS.

    The two arms inside the ``for label, text in texts`` loop run **three**
    times now, once per text (CARD-259 added ``conftest.py``'s pointer as the
    third), so each ``DOC-NAME-DEL`` cell records one RED among three outcomes
    -- which is why ANY-RED is doing real work here and not only in a fixture.
    The mutant count stays 14 because this anchor scopes its edits to the two
    texts it can reach: the third lives in ``tests/conftest.py``, which the
    instrument refuses to edit by identity. CARD-252's record is kept on
    :func:`nonogram.db.session.reset_engine`, and since
    CARD-259 the set of texts that anchored test holds is derived off the disk
    rather than listed, so the **three** texts above is a reading of today's
    tree and not a constant.
    """
    source = LIFECYCLE.read_text(encoding="utf-8")
    linenos = set(km.assert_linenos(source, str(LIFECYCLE)))
    arms = (PREAMBLE, NAMES, HEADS, POINTER)
    assert set(arms) <= linenos, arms

    mutants, reds = _four_arm_grid()
    assert len(mutants) == 14, [m.name for m in mutants]

    result = Runner(selection=[FOUR_ARM], repo_root=REPO).run(Pass.RECORDING, mutants)

    for arm in arms:
        assert result.shipped.cells[arm] == PASS, result.shipped.table()

    for name, red_arms in reds.items():
        for arm in arms:
            got = result.cell(name, arm)
            if arm in red_arms:
                assert got == FAIL, f"{name} at :{arm} is {got}, expected FAIL"
            elif name == "NAMES-BLIND" and arm != PREAMBLE:
                assert got == NOT_REACHED, f"{name} at :{arm} is {got}, expected n/r"
            else:
                assert got == PASS, f"{name} at :{arm} is {got}, expected PASS"
