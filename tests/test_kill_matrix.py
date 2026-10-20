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
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests import kill_matrix as km
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


def _independent_assert_count(path: Path) -> int:
    """A second implementation of the denominator, never the one under test.

    ``ast.walk`` over a fresh parse, counting ``ast.Assert`` nodes. It shares no
    code with :func:`kill_matrix.assert_linenos`, which is the point: a figure's
    control is recomputation by another route.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))


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


def test_ac1_the_planted_shifting_mutant_runs_green_and_reports_nothing(simple_target):
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

    gone = len(DELETABLE.splitlines())
    shifted = pristine.replace(DELETABLE, "", 1)
    assert len(shifted.splitlines()) == len(pristine.splitlines()) - gone
    simple_target.write_text(shifted, encoding="utf-8")
    try:
        records, exit_code, output = runner._pytest(Pass.RECORDING)
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

    Every string constant and every subprocess argument list in
    ``kill_matrix.py`` is walked; a ``git`` anywhere among them is the finding.
    Default-deny: a subprocess call whose argument list this cannot enumerate
    fails the test rather than being skipped.
    """
    tree = ast.parse(INSTRUMENT.read_text(encoding="utf-8"), filename=str(INSTRUMENT))
    commands = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = ast.unparse(node.func)
        if not callee.startswith("subprocess."):
            continue
        assert node.args, f"unanalysable subprocess call at line {node.lineno}"
        argv = node.args[0]
        assert isinstance(argv, (ast.List, ast.Tuple)), (
            f"subprocess argv at line {node.lineno} is not an enumerable literal "
            f"list: {ast.unparse(argv)}"
        )
        head = argv.elts[0]
        if isinstance(head, ast.Constant):
            commands.append(head.value)
            continue
        # The one non-literal that exists: the interpreter running this process,
        # which is how the instrument re-enters pytest. Anything else is a shape
        # this enumeration cannot analyse, and that is a FAILURE, not a pass.
        assert ast.unparse(head) == "sys.executable", (
            f"subprocess argv[0] at line {node.lineno} is neither a literal nor "
            f"sys.executable: {ast.unparse(head)}"
        )
        commands.append("sys.executable")

    assert commands, "no subprocess call found; the enumeration is dead"
    assert "cp" in commands and "diff" in commands and "shasum" in commands, commands
    assert not [name for name in commands if "git" in str(name)], commands

    invoked = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.match(r"git(\s|$)", node.value)
    ]
    assert invoked == [], invoked


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
#: source line occurs four times, because ``:816`` asserts ``built`` where the
#: other four assert ``names``. Measured here rather than carried over, and
#: both numbers are asserted below so neither can drift.
NAMES_BLIND_MESSAGE = "no module-level globals found in _init_engine (guard is blind)"
NAMES_BLIND_LINE = (
    '        assert names, "no module-level globals found in _init_engine '
    '(guard is blind)"'
)
NAMES_BLIND_OCCURRENCES = (816, 859, 914, 960, 1087)
#: ``:859`` is CARD-257's ``NAMES-BLIND`` arm -- the second occurrence, which is
#: the whole point: a caller who did not name it would have mutated ``:816``,
#: in a different test, and read the answer off the wrong arm.
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
    ``NAMES-BLIND`` arm at ``:859``, and a caller who did not name it would have
    silently mutated ``:816``, which belongs to a different test.
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
    assert occurrence != NAMES_BLIND_ARM_OCCURRENCE or lineno == 859


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
        assert str(result.denominator) in printed, (class_name, method_name, printed)


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


def test_g2_a_lock_in_the_tree_refuses_the_start(simple_target, tmp_path):
    """Planted in a tmp tree. The board's real lock is never created or touched."""
    lock = tmp_path / "meta" / "kanban" / ".full-suite.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("worktree: planted-by-test\n", encoding="utf-8")

    with pytest.raises(LockHeld, match="holds the board's full-suite lock"):
        Runner(selection=[str(simple_target)], repo_root=tmp_path)

    lock.unlink()
    assert Runner(selection=[str(simple_target)], repo_root=tmp_path).target


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
    with pytest.raises(MutantRefused, match="carries the database guard"):
        Edit(path=Path("tests") / "conftest.py", old="a = 1", new="a = 2")


def test_the_generated_plugin_names_exactly_the_env_vars_the_runner_sets():
    """The plugin is generated source, so its env-var names can drift from the
    runner's constants. Enumerated here rather than trusted: the three names the
    runner puts in the child environment are exactly the three the plugin reads.
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
    read_by_plugin = set(re.findall(r"KILL_MATRIX_[A-Z_]+", rendered))
    assert read_by_plugin == set(constants), (read_by_plugin, set(constants))
    assert "KILL_MATRIX" not in km._PLUGIN_SOURCE, (
        "the plugin source still hard-codes an env-var name, so it can drift "
        "from the runner's constants"
    )


def test_g4_the_instrument_imports_stdlib_only():
    """Enumerated from the AST; the baseline is stdlib plus nothing."""
    tree = ast.parse(INSTRUMENT.read_text(encoding="utf-8"), filename=str(INSTRUMENT))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 or node.module, f"unanalysable import at {node.lineno}"
            roots.add((node.module or "").split(".")[0])
    assert roots <= set(sys.stdlib_module_names), roots - set(sys.stdlib_module_names)


def test_g6_the_instrument_takes_no_timing_measurement():
    """No clock is read, so no figure here can be a duration.

    Enumerated two ways: no timing module is imported, and no timing function
    is named anywhere in the source. ``subprocess``'s ``timeout=`` is a bound on
    a hung child, not a measurement, and is deliberately outside this set --
    the control for that distinction is that the names below *would* red.
    """
    source = INSTRUMENT.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(INSTRUMENT))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported.isdisjoint({"time", "timeit", "datetime", "resource", "cProfile"})

    for name in ("perf_counter", "monotonic", "process_time", "time()", "elapsed"):
        assert name not in source, f"{name} is a clock; G-6 forbids reading one"


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
    assert _independent_assert_count(LOCK_GUARD_TEST) == 130

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
    "::test_both_convention_texts_agree_on_the_mechanisms_parameters"
)
#: CARD-257's four arms, restated from its cycle-3 record and re-derived from
#: the unmodified parse below rather than trusted.
PREAMBLE, NAMES, HEADS, POINTER = 859, 878, 889, 897
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
    """``tests/test_db_engine_lifecycle.py`` at ``b441ba00``: the second anchor.

    The arms sit at ``:859`` (preamble), ``:878`` (names), ``:889`` (heads) and
    ``:897`` (pointer) -- re-derived from the unmodified parse here, never
    reused from a previous reading. What must come back is CARD-257's grid, cell
    for cell: six ``DOC-NAME-DEL`` cells RED at ``:878``, four ``DOC-HEAD-DEL``
    cells RED at ``:889``, ``NAMES-BLIND`` RED at ``:859`` with the three arms
    below it NOT-REACHED, ``POINTER-ROT`` and ``POINTER-DEL-WORD`` RED at
    ``:897``, ``CONTROLS-RENAME-ONLY`` PASS, and SHIPPED all-PASS.

    The two arms inside the ``for label, text in texts`` loop run twice, once
    per text, so each ``DOC-NAME-DEL`` cell records ``['RED','PASS']`` or
    ``['PASS','RED']`` -- which is why ANY-RED is doing real work here and not
    only in a fixture.
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
