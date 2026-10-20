"""CARD-255 — a pytest run refuses to start while another worktree holds the lock.

    AC-1  a lock written by another worktree stops the run before collection,
          printing the holder, the commit and the lock's age
    AC-2  with the abort removed, AC-1's test fails (the control; exercised as
          a mutant, recorded in the card)
    AC-3  a stale lock does not wedge the board — the run proceeds and says
          why it ignored the lock
    AC-4  the override lets a contended run through and announces itself;
          unset, nothing announces one
    AC-5  a tree with no lock behaves exactly as before — no skip, no line

``_same_tree`` is the function the whole card reduces to, so it is measured
directly as well as through :func:`verdict`
(:func:`test_same_tree_is_exact_identity_not_a_prefix_or_a_spelling`,
:func:`test_a_value_that_is_not_an_absolute_path_names_no_tree`). Reached only
through ``verdict`` it is always handed two already-resolved, exactly-equal
absolute paths, which is the one case that cannot tell an exact comparison
from a prefix test, or ``realpath`` from no normalisation at all: three
mutants of it survived the suite before those tests existed.

``meta/kanban/.full-suite.lock`` was written by every full-suite gate and read
by nobody. The gate's own guard refuses to *start* beside another pytest, which
is a check at the door that cannot stop someone entering afterwards: CARD-225's
build gate 2 shared its fifteen-minute window with a 288-test Chromium suite
and came back 2-failed on tests unrelated to the card. One gate re-run, one
attribution written down and then withdrawn.

**The trap this file exists to avoid.** The obvious test writes a lock, starts
pytest in the same process and catches the abort — and *passes with a guard
that only ever refuses itself*, which is the opposite of what is wanted,
because the gate writes the lock and then runs the suite under it. So every
abort case here is paired with the gate's own self-run case
(:func:`test_the_gates_own_lock_does_not_block_the_gates_own_run`,
:func:`test_a_gate_running_under_its_own_lock_is_not_refused`), and the mutant
that proves the pair is "treat every lock as foreign": it must leave the
refusal green and turn the self-run case red. Two holder identities, not one.

Identity is the lock's ``worktree`` field, not a pid: the gate writes the lock
and then launches pytest as a *child*, so no pid in the file can ever be the
pid of the process the guard runs in — but every gate runs pytest in the
worktree it names.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests import full_suite_lock as guard

REPO = Path(__file__).resolve().parent.parent

#: A worktree this run is certainly not in. Under ``/tmp`` on purpose: a
#: sibling path next to the repo could one day exist and be *this* tree.
ANOTHER_WORKTREE = "/tmp/nonogram-card-255-not-this-worktree"


def _stamp(seconds_ago: float = 0.0) -> str:
    """An ``at:`` value in the exact format every gate script writes."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - seconds_ago))


def gate_lock(worktree: str = ANOTHER_WORKTREE, *, at: str | None = None) -> str:
    """The lock exactly as ``gate.sh`` writes it: why folded into ``holder``.

    Reproduced field for field from the producer rather than invented, because
    G-4 is that those scripts keep working unchanged — they are not in this
    card's Touches and nobody edits them to make this guard pass.
    """
    return (
        "holder: gate CARD-254 fake-gate-for-the-test\n"
        f"at: {at if at is not None else _stamp()}\n"
        f"worktree: {worktree}\n"
        "commit: 0ff1ce0\n"
    )


def gate_lock_with_why(worktree: str = ANOTHER_WORKTREE) -> str:
    """The other shape in use: ``gate-247.sh``/``gate-250.sh`` write ``why:``."""
    return (
        "holder: CARD-247 gate (wave 48)\n"
        f"at: {_stamp()}\n"
        f"worktree: {worktree}\n"
        "commit: 9a31a8b\n"
        "why: the first post-fix gate ran concurrently with review cycle 2\n"
    )


# --------------------------------------------------------------------------
# The rule, as a pure function
# --------------------------------------------------------------------------


def test_no_lock_file_is_the_ordinary_case():
    """AC-5. Nearly every run: no lock, no verdict to report, nothing said."""
    allowed, said = guard.verdict(None, worktree=str(REPO), age_seconds=None, overridden=False)

    assert allowed is True
    assert said is None, "a run with no lock in sight must print nothing at all"


def test_a_lock_held_by_another_worktree_refuses_the_run():
    """AC-1 — and it names the holder, the commit and the age, not 'busy'."""
    allowed, said = guard.verdict(
        gate_lock(), worktree=str(REPO), age_seconds=412.0, overridden=False
    )

    assert allowed is False
    assert "gate CARD-254 fake-gate-for-the-test" in said, "the refusal does not name the holder"
    assert "0ff1ce0" in said, "the refusal does not name the holder's commit"
    assert "412" in said, "the refusal does not say how old the lock is"
    assert ANOTHER_WORKTREE in said, "the refusal does not name the worktree holding it"


def test_the_gates_own_lock_does_not_block_the_gates_own_run():
    """The self-run case — the one the trap's test cannot tell apart.

    The gate writes the lock, then runs the suite in the worktree it named.
    A guard that refused this would stop every gate on the board, so this is
    the case the mutant "treat every lock as foreign" must turn red.
    """
    allowed, said = guard.verdict(
        gate_lock(worktree=str(REPO)), worktree=str(REPO), age_seconds=5.0, overridden=False
    )

    assert allowed is True, "the gate's own lock refused the gate's own run"
    assert said is None, "a gate running under its own lock has nothing to report"


def test_the_two_shapes_the_gate_scripts_write_are_both_understood():
    """G-4 — ``why`` as its own field, or folded into ``holder``: both in use."""
    for text in (gate_lock(), gate_lock_with_why()):
        allowed, said = guard.verdict(
            text, worktree=str(REPO), age_seconds=10.0, overridden=False
        )
        assert allowed is False
        assert "wave 48" in said or "fake-gate-for-the-test" in said

    allowed, said = guard.verdict(
        gate_lock_with_why(worktree=str(REPO)),
        worktree=str(REPO),
        age_seconds=10.0,
        overridden=False,
    )
    assert allowed is True, "the why-shaped lock is not recognised as its own holder's"


def test_a_field_the_reader_has_never_heard_of_changes_nothing():
    """G-4 the other way: the format may grow, and old locks lack the new line.

    Both directions are the same assertion — a lock is read for the fields it
    has, so a gate script that one day adds ``pid:`` and one that never does
    both get the same verdict.
    """
    grown = gate_lock() + "pid: 4242\nsome-future-field: whatever\n"

    allowed_grown, said_grown = guard.verdict(
        grown, worktree=str(REPO), age_seconds=10.0, overridden=False
    )
    allowed_old, _said_old = guard.verdict(
        gate_lock(), worktree=str(REPO), age_seconds=10.0, overridden=False
    )

    assert allowed_grown is allowed_old is False
    assert "4242" in said_grown, "a field the reader does not know is dropped from the refusal"


def test_a_lock_that_names_no_worktree_is_refused_rather_than_assumed_ours():
    """ADR-0039/R2 — a shape the guard cannot analyse is a refusal, not a pass.

    ``tests/README.md`` used to document ``echo "profiling run, started ..."``
    as the way to take the lock, which names no holder at all. Assuming such a
    lock is ours would be a silent pass in exactly the contended case this card
    exists for, so it is refused and the refusal says why it could not tell.
    """
    allowed, said = guard.verdict(
        "profiling run, started 2026-10-20T05:15:11Z\n",
        worktree=str(REPO),
        age_seconds=30.0,
        overridden=False,
    )

    assert allowed is False
    assert "worktree" in said


def test_a_relative_worktree_value_is_refused_rather_than_resolved_against_the_reader():
    """ADR-0039/R2 again: ``worktree: .`` names a path, but not a tree.

    ``realpath`` resolves a relative value against the *reading* process's
    cwd, and every gate runs pytest from its worktree root. So a foreign
    holder's ``worktree: .`` would resolve, inside every *other* worktree, to
    that worktree: the guard would recognise a lock it has never held as its
    own, let the run through, and print nothing — CARD-225's defect restored.
    It is the same unanalysable shape as a lock with no ``worktree:`` line and
    takes the same branch, with the refusal saying which of the two it was.

    No gate script writes a relative value (all three write ``worktree: $WT``),
    but ``tests/README.md`` now tells a human to hand-write a lock.
    """
    # The dangerous spelling exactly: a relative value resolves to the reading
    # process's own cwd, which is what used to make this a silent pass.
    allowed, said = guard.verdict(
        gate_lock(worktree="."), worktree=os.getcwd(), age_seconds=30.0, overridden=False
    )

    assert allowed is False, "a foreign lock reading 'worktree: .' was taken for this run's own"
    assert "not an absolute path" in said, "the refusal does not say why it could not tell"

    for relative in (".", "./", "../PythonProject4-card-254", "PythonProject4-card-255"):
        allowed, said = guard.verdict(
            gate_lock(worktree=relative),
            worktree=str(REPO),
            age_seconds=30.0,
            overridden=False,
        )

        assert allowed is False, f"worktree: {relative!r} let a foreign lock through"
        assert "worktree" in said
        assert relative in said, "the refusal does not quote the value it could not resolve"


def test_same_tree_is_exact_identity_not_a_prefix_or_a_spelling(tmp_path):
    """The identity rule, measured on its own function rather than through a verdict.

    Every other case here hands :func:`guard.verdict` two already-resolved,
    exactly-equal absolute paths, under which an exact comparison, a
    ``startswith`` and a bare string equality are indistinguishable — all
    three were live mutants that the suite passed. The pairs below are the
    board's real neighbours, not invented ones: the worktrees are siblings of
    the main checkout and of each other, and their paths share prefixes.
    """
    tree = tmp_path / "PythonProject4-card-255"
    sibling = tmp_path / "PythonProject4-card-25"
    main = tmp_path / "PythonProject4"
    for directory in (tree, sibling, main):
        directory.mkdir()
    through_symlink = tmp_path / "reached-through-a-symlink"
    through_symlink.symlink_to(tree)
    me = str(tree)

    # Exactness: every one of these is a *different* tree that shares a prefix.
    assert guard._same_tree(str(sibling), me) is False, "…-card-25 read as …-card-255"
    assert guard._same_tree(me, str(sibling)) is False, "…-card-255 read as …-card-25"
    assert guard._same_tree(str(main), me) is False, "the main checkout read as a worktree of it"
    assert guard._same_tree(me, str(main)) is False
    assert guard._same_tree(me + "-and-more", me) is False

    # Normalisation: every one of these is the *same* tree, spelled differently.
    assert guard._same_tree(me, me) is True
    assert guard._same_tree(me + "/", me) is True, "a trailing slash made a tree foreign"
    assert guard._same_tree(me + "/.", me) is True
    assert guard._same_tree(str(through_symlink), me) is True, (
        "a worktree reached through a symlink read as a different worktree — the "
        "expensive direction: a gate refused by its own lock"
    )
    assert guard._same_tree("~", os.path.realpath(os.path.expanduser("~"))) is True, (
        "a leading ~ is not expanded"
    )


def test_a_value_that_is_not_an_absolute_path_names_no_tree():
    """The clause that makes a relative ``worktree:`` unanalysable, directly."""
    assert guard._names_a_tree(str(REPO)) is True
    assert guard._names_a_tree("/tmp/some-other-worktree") is True
    assert guard._names_a_tree("~/PycharmProjects/PythonProject4") is True

    assert guard._names_a_tree(None) is False, "a missing worktree: names a tree"
    assert guard._names_a_tree("") is False
    assert guard._names_a_tree("   ") is False, "whitespace names a tree"
    assert guard._names_a_tree(".") is False
    assert guard._names_a_tree("./") is False
    assert guard._names_a_tree("../PythonProject4-card-254") is False
    assert guard._names_a_tree("PythonProject4-card-255") is False


def test_a_lock_that_cannot_be_read_is_not_the_same_as_no_lock(tmp_path, monkeypatch):
    """"There is a lock and I cannot read it" is a refusal, not a clear road.

    :func:`guard.read_lock` answers ``""`` for a file it cannot read and
    ``None`` only for one that is not there, and the difference is the entire
    verdict: ``None`` returns early as "no lock at all", while ``""`` parses to
    no fields, names no worktree, and is refused. A directory at the lock path
    is the deterministic way to make the read fail — ``chmod 0o000`` does not
    stop the file's own owner on every host.
    """
    unreadable = tmp_path / "unreadable.full-suite.lock"
    unreadable.mkdir()

    assert guard.read_lock(unreadable) == "", "a lock that cannot be read read as no lock"
    assert guard.read_lock(tmp_path / "there-is-nothing-here.lock") is None

    monkeypatch.delenv(guard.OVERRIDE, raising=False)
    monkeypatch.setenv(guard.LOCK_PATH_VAR, str(unreadable))
    allowed, said = guard.current_verdict()

    assert allowed is False, "an unreadable lock let the run start"
    assert "worktree" in said


# --------------------------------------------------------------------------
# AC-3 — a dead holder must not wedge the board
# --------------------------------------------------------------------------


def test_a_stale_lock_is_ignored_and_says_why():
    allowed, said = guard.verdict(
        gate_lock(),
        worktree=str(REPO),
        age_seconds=guard.STALE_SECONDS + 1.0,
        overridden=False,
    )

    assert allowed is True
    assert said is not None, "a lock was ignored and the run did not say so"
    assert "stale" in said.lower()
    assert str(int(guard.STALE_SECONDS)) in said, "the threshold it was judged against is not named"


def test_a_lock_one_second_inside_the_threshold_still_refuses():
    """The boundary, because a threshold with no boundary test is a number."""
    allowed, _said = guard.verdict(
        gate_lock(),
        worktree=str(REPO),
        age_seconds=guard.STALE_SECONDS - 1.0,
        overridden=False,
    )

    assert allowed is False


def test_the_threshold_clears_the_longest_gate_this_board_has_recorded():
    """Why this number: a live gate must never read as stale.

    The longest lock-hold on record is CARD-245's gate wrapper at 4126s (its
    pytest session was 1196s; the gap is recorded as unexplained in that card).
    A threshold at or below that would hand a running gate's window to a second
    pytest — the exact defect this card removes.
    """
    assert guard.STALE_SECONDS >= 4 * 4126, (
        "the stale threshold does not clear the longest gate this board has recorded"
    )


def test_an_age_that_cannot_be_determined_is_not_treated_as_stale():
    """Unknown age is not 'old enough' — the refusal stands."""
    allowed, _said = guard.verdict(
        gate_lock(), worktree=str(REPO), age_seconds=None, overridden=False
    )

    assert allowed is False


def test_a_lock_stamped_in_the_future_refuses_and_says_so_in_words():
    """Clock skew between a writer and this reader, or a hand-written stamp.

    The verdict is the safe one either way — a negative age is below the
    threshold, so the refusal stands — but the refused person used to be shown
    ``age: -3600s``, which reads as nonsense.
    """
    allowed, said = guard.verdict(
        gate_lock(), worktree=str(REPO), age_seconds=-3600.0, overridden=False
    )

    assert allowed is False, "a lock stamped in the future stopped being a lock"
    assert "-3600" not in said, "the refusal prints a negative age"
    assert "future" in said, "the refusal does not say the stamp is ahead of this clock"
    assert str(int(guard.STALE_SECONDS)) in said


# --------------------------------------------------------------------------
# AC-4 — the override
# --------------------------------------------------------------------------


def test_the_override_allows_a_contended_run_and_names_itself():
    allowed, said = guard.verdict(
        gate_lock(), worktree=str(REPO), age_seconds=10.0, overridden=True
    )

    assert allowed is True
    assert said is not None, "the override was used and the run said nothing"
    assert guard.OVERRIDE in said
    assert "gate CARD-254 fake-gate-for-the-test" in said, (
        "an overridden run does not say whose lock it walked past"
    )


def test_the_refusal_says_how_to_proceed_on_purpose():
    _allowed, said = guard.verdict(
        gate_lock(), worktree=str(REPO), age_seconds=10.0, overridden=False
    )

    assert guard.OVERRIDE in said, "the refusal does not name the way out"


#: Files whose job is to *name* the override: the guard (reads it and prints
#: it), this file (sets it in a child process on purpose — the AC-4 test), and
#: ``tests/README.md`` (documents it as the way out).
OVERRIDE_NAMERS = frozenset(
    {
        "tests/full_suite_lock.py",
        "tests/test_full_suite_lock.py",
        "tests/README.md",
    }
)

#: And the board's prose, which quotes the refusal: card text and review
#: reports. Prefixes, because the filenames are per-card.
OVERRIDE_PROSE = ("meta/kanban/cards/", "meta/review/")


def test_nothing_in_the_tree_sets_the_override_for_a_run():
    """AC-4's premise: an override the producers set is not an override.

    The scan is the **whole tree**, because that is the claim. A hand-written
    pathspec (it was ``tests src pyproject.toml``) cannot see
    ``scripts/run_admin_tests.sh``, an in-tree pytest runner that already
    exports env for the suite and is the closest co-change peer of
    ``tests/conftest.py``: one ``export NONOGRAM_IGNORE_FULL_SUITE_LOCK=1``
    line there would switch this guard off for every run through it and leave
    a pathspec'd scan green. Same for ``scripts/README.md``, ``start.sh``,
    ``Dockerfile``, ``docker-compose.yml`` and ``.env.example``. Widening the
    scan costs nothing: the allowlist below already pins the files legitimately
    allowed to name the variable.

    Two bounds of the measurement, stated rather than left to be discovered.
    ``git grep`` reads **tracked** files only, so an untracked runner is
    invisible to it. And the gate scripts live outside the repo (the
    orchestrator's scratchpad), so they cannot be held by this test at all —
    that they do not set it is checked by reading them, not here.
    """
    hits = subprocess.run(
        ["git", "grep", "-l", guard.OVERRIDE],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout.split()

    offenders = [
        path
        for path in hits
        if path not in OVERRIDE_NAMERS and not path.startswith(OVERRIDE_PROSE)
    ]

    assert not offenders, (
        f"{offenders} mention the override; a tree that sets it has no override"
    )

    conftest = (REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert guard.OVERRIDE not in conftest


# --------------------------------------------------------------------------
# Where the lock is, and why every worktree finds the same one
# --------------------------------------------------------------------------


def test_every_worktree_resolves_the_one_lock_the_gates_write(tmp_path):
    """A per-worktree lock path would be a guard that cannot see contention.

    Every gate script writes the **main** repo's
    ``meta/kanban/.full-suite.lock``, whichever worktree it runs. So a linked
    worktree must follow its ``.git`` file back to the main tree, and the main
    tree must answer with itself.
    """
    main = tmp_path / "MainTree"
    (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
    linked = tmp_path / "MainTree-card-999"
    linked.mkdir()
    (linked / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n")

    assert guard.main_repo_root(linked) == main
    assert guard.main_repo_root(main) == main
    assert guard.default_lock_path(linked) == guard.default_lock_path(main)


def test_the_production_default_is_the_boards_own_lock():
    """No env var set: the path is the real file the gates write, nothing else."""
    default = guard.default_lock_path(REPO)

    assert default.parts[-3:] == ("meta", "kanban", ".full-suite.lock")
    assert default == guard.main_repo_root(REPO) / "meta" / "kanban" / ".full-suite.lock"


def test_the_lock_path_is_injectable_so_a_test_never_touches_the_real_one(monkeypatch, tmp_path):
    elsewhere = tmp_path / "pretend.lock"
    monkeypatch.setenv(guard.LOCK_PATH_VAR, str(elsewhere))

    assert guard.lock_path() == elsewhere

    monkeypatch.delenv(guard.LOCK_PATH_VAR)

    assert guard.lock_path() == guard.default_lock_path(guard.this_worktree())


def test_the_age_comes_from_the_at_field_the_gates_write(tmp_path):
    lock = tmp_path / "with-at.lock"
    lock.write_text(gate_lock(at=_stamp(600)))

    age = guard.lock_age_seconds(guard.parse_fields(lock.read_text()), path=lock)

    assert age is not None
    assert 590 <= age <= 700, age


def test_a_lock_whose_at_is_unreadable_falls_back_to_its_mtime(tmp_path):
    lock = tmp_path / "no-at.lock"
    lock.write_text("holder: someone\nworktree: /elsewhere\nat: not-a-timestamp\n")
    os.utime(lock, (time.time() - 900, time.time() - 900))

    age = guard.lock_age_seconds(guard.parse_fields(lock.read_text()), path=lock)

    assert age is not None
    assert 890 <= age <= 1000, age


# --------------------------------------------------------------------------
# The guard in a real run — the wiring, not the function
# --------------------------------------------------------------------------

#: One pure unit test from this file, selected in the subprocess runs below.
#: Cheap, and it needs no database, so what the run reports is the guard's
#: decision and nothing else.
SELECTION = "tests/test_full_suite_lock.py::test_no_lock_file_is_the_ordinary_case"


def _run_pytest(lock: Path, *, override: str | None = None):
    """A real pytest, in this repo, through ``tests/conftest.py``'s wiring.

    ``-q`` on purpose rather than ``-v``: it is what ``pyproject`` sets and
    what every gate therefore runs at, and it is the verbosity at which pytest
    prints no run header — so an announcement that only reached the header
    would be invisible in exactly the runs that matter.
    """
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO / "src"),
        guard.LOCK_PATH_VAR: str(lock),
    }
    env.pop(guard.OVERRIDE, None)
    if override is not None:
        env[guard.OVERRIDE] = override
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-o", "addopts=-q", "-p", "no:cacheprovider", SELECTION],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )


@pytest.fixture
def foreign_lock(tmp_path):
    lock = tmp_path / "foreign.full-suite.lock"
    lock.write_text(gate_lock())
    return lock


def test_a_foreign_lock_aborts_a_real_run_before_collection(foreign_lock):
    """AC-1 in a real process. Not 'the function returns False'."""
    result = _run_pytest(foreign_lock)
    combined = result.stdout + result.stderr

    assert result.returncode != 0, combined
    assert "1 passed" not in combined, "the run collected and ran a test anyway"
    assert "gate CARD-254 fake-gate-for-the-test" in combined
    assert "0ff1ce0" in combined
    assert guard.OVERRIDE in combined


def test_the_guard_cannot_turn_a_refusal_into_a_skip():
    """AC-5 — the abort must never become a silent skip.

    A guard that skipped instead of aborting would remove the symptom by
    removing the coverage, and a run that skipped the suite would still exit
    0. The module names no skip API at all, so there is nowhere for that to
    come from; the three allowed cases below each assert ``1 passed`` and
    ``skipped`` nowhere in the output, which is the same claim from the other
    side.

    Two rules, because they measure different things. The first is a **text**
    rule over the whole file, prose included: a docstring that explained the
    abort by naming the alternative would red it, and that is the intended
    strictness — it fails in the safe direction. The second is the claim
    itself, read off the module's syntax: no call in it resolves to a name
    that can turn a failure into a non-result.
    """
    source = Path(guard.__file__).read_text(encoding="utf-8")

    for forbidden in ("skip", "add_marker", "xfail"):
        assert forbidden not in source, (
            f"the lock guard names {forbidden!r}; its only outcomes are an abort, "
            "a printed line, and silence"
        )

    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
    }
    forbidden_apis = {"skip", "skipif", "importorskip", "xfail", "add_marker", "exit"}

    assert not called & forbidden_apis, (
        f"the lock guard calls {sorted(called & forbidden_apis)}; its only outcomes are "
        "an abort, a printed line, and silence"
    )


def test_a_gate_running_under_its_own_lock_is_not_refused(tmp_path):
    """The self-run case, in a real process — the mutant's target.

    This is the whole reason the test needs two holder identities: with the
    lock naming *this* tree, the run must go through, and a guard that treats
    every lock as foreign reds here while the refusal above stays green.
    """
    lock = tmp_path / "own.full-suite.lock"
    lock.write_text(gate_lock(worktree=str(REPO)))

    result = _run_pytest(lock)
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "1 passed" in combined
    assert "skipped" not in combined, "the abort became a skip, which is AC-5's whole worry"
    assert "full-suite lock" not in combined, (
        "the gate's own run reports a lock verdict nobody needs to read"
    )


def test_a_relative_worktree_value_does_not_disable_the_guard_in_a_real_run(tmp_path):
    """The pure function's verdict, confirmed where the cwd is real.

    This is the shape that matters: pytest is started *from the worktree
    root*, so before the ``isabs`` clause a lock reading ``worktree: .`` was
    recognised as this tree's own in every tree that read it — exit 0, the
    test ran, and the output said nothing about a lock at all.
    """
    lock = tmp_path / "relative.full-suite.lock"
    lock.write_text(gate_lock(worktree="."))

    result = _run_pytest(lock)
    combined = result.stdout + result.stderr

    assert result.returncode != 0, combined
    assert "1 passed" not in combined, "a lock reading 'worktree: .' let the run through"
    assert "gate CARD-254 fake-gate-for-the-test" in combined
    assert "not an absolute path" in combined


def test_a_stale_lock_does_not_wedge_the_board(tmp_path):
    """AC-3 — and the run says why it walked past the file."""
    lock = tmp_path / "stale.full-suite.lock"
    lock.write_text(gate_lock(at=_stamp(guard.STALE_SECONDS + 60)))

    result = _run_pytest(lock)
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "1 passed" in combined
    assert "skipped" not in combined, "the abort became a skip, which is AC-5's whole worry"
    assert "stale" in combined.lower(), "a lock was ignored and the run never said so"


def test_the_override_lets_a_contended_run_through_and_announces_itself(foreign_lock):
    """AC-4 — the lock above refused this very run a moment ago."""
    result = _run_pytest(foreign_lock, override="1")
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "1 passed" in combined
    assert "skipped" not in combined, "the abort became a skip, which is AC-5's whole worry"
    assert guard.OVERRIDE in combined, "the override was used and the run was quiet about it"


def test_a_tree_with_no_lock_runs_exactly_as_it_did_before(tmp_path):
    """AC-5 — the ordinary run: unchanged, and silent about all of this."""
    result = _run_pytest(tmp_path / "there-is-no-lock-here.lock")
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "1 passed" in combined
    assert "skipped" not in combined, "the abort became a skip, which is AC-5's whole worry"
    assert guard.OVERRIDE not in combined, (
        "a run with no lock advertises the override, which is noise on every run"
    )
    assert "full-suite lock" not in combined
