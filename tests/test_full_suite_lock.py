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
    is the way to make the read fail that is deterministic on every host; what
    ``chmod 0o000`` does to its own owner is host-dependent (on this one it
    raises, which is why the claim is stated as the directory's determinism
    rather than as something measured about ``chmod``).
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


@pytest.mark.parametrize(
    ("value", "turns_it_on"),
    [("1", True), ("0", True), ("false", True), ("no", True), ("", False)],
)
def test_any_non_empty_value_turns_the_override_on_including_zero(
    tmp_path, monkeypatch, value, turns_it_on
):
    """The spelling the override documents, held by a test and not by prose.

    ``overridden=bool(os.getenv(OVERRIDE))``: any non-empty value is on, ``=0``
    and ``=false`` included. That is deliberate — it is the same convention
    ``tests/database_guard.py`` reads its own opt-out with
    (``opted_out=bool(os.getenv(OPT_OUT))``), kept so the two guards have one
    convention rather than two — but it was documented and measured by nothing:
    every other override case here either hands :func:`guard.verdict` a bool
    directly or sets ``=1`` in a child process, so a mutant tightening the
    spelling to a truthy set (``in {"1", "true", "yes", "on"}``) changed a
    documented behaviour with the file green.

    ``=0`` switching a guard **on** is the surprising direction, so it is the
    one pinned: a future tidy-up that makes ``=0`` mean off has to red this.
    The empty value is the other boundary — unset and ``=''`` are the same
    answer, and the lock stands.
    """
    lock = tmp_path / "foreign.full-suite.lock"
    lock.write_text(gate_lock())
    monkeypatch.setenv(guard.LOCK_PATH_VAR, str(lock))
    monkeypatch.setenv(guard.OVERRIDE, value)

    allowed, said = guard.current_verdict()

    assert allowed is turns_it_on, (
        f"{guard.OVERRIDE}={value!r} did not {'enable' if turns_it_on else 'leave off'} "
        "the override"
    )
    assert said is not None
    if turns_it_on:
        assert guard.OVERRIDE in said, "an overridden run walked past a lock quietly"
        assert "running anyway" in said
    else:
        assert "Refusing to start" in said


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

#: The shapes those two directories are exempted *for*. The clause bounds the
#: **extension** and nothing else: an executable ``.md`` or ``.yml`` under
#: either prefix is exempted too, probed live at mode 100755. What closes that
#: axis is a separate equality — every file git tracks under the two prefixes
#: is mode ``100644`` today
#: (:func:`test_the_exempted_prefixes_hold_nothing_a_shell_can_run`), so a
#: file that changes it reds that test instead of slipping past this clause.
#:
#: A bare prefix exempts a whole directory and says nothing
#: about a file's shape, so a runner dropped into either one would set the
#: override for every run through it and leave this scan green. Probed, not
#: reasoned about: two executable ``run-the-suite.sh`` files, one under each
#: prefix, each carrying ``export NONOGRAM_IGNORE_FULL_SUITE_LOCK=1``, were
#: visible to ``git grep`` and invisible to the scan below while the exemption
#: matched on the prefix alone. Its control is
#: :func:`test_an_executable_setter_under_an_allowlisted_prefix_is_still_caught`.
#:
#: The prefixes' trailing slashes are load-bearing in the same way:
#: ``meta/review-archive/`` and ``meta/reviews/`` do not match them.
#:
#: These two shapes are the whole tracked population of those directories, not
#: a guess at it: ``git ls-files meta/kanban/cards meta/review`` in the main
#: checkout is 256 ``.md`` and 286 ``.yml`` files and nothing else. A prose
#: file in a third format is a one-word edit here *and* a deliberate one.
PROSE_SHAPES = (".md", ".yml")


def _scan(cwd):
    """Every tracked file naming either of the guard's two env switches.

    One definition for both scans below — the tree scan and its control — so
    the mutant that drops a name from it is a single edit and both of them
    red on it. ``git grep -l -e A -e B`` is the union, not an intersection.
    """
    return subprocess.run(
        ["git", "grep", "-l", "-e", guard.OVERRIDE, "-e", guard.LOCK_PATH_VAR],
        cwd=cwd,
        capture_output=True,
        text=True,
    ).stdout.split()


def _tracked_modes(cwd):
    """The git index mode of every tracked file under the exempted prefixes.

    One definition for the equality over the real tree and for its own control
    in a throwaway repo, so the two cannot drift apart.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-s", *OVERRIDE_PROSE],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return [line.split()[0] for line in listed]


def _scan_offenders(paths):
    """Of the scanned files that name a switch, the ones with no business.

    Two exemptions, each bounded on an axis it can be bounded on.
    :data:`OVERRIDE_NAMERS` is an equality over three exact paths — the shape
    ADR-0039/R3 asks for. :data:`OVERRIDE_PROSE` cannot be an equality (the
    filenames under it are per-card and are created after this test is
    written), so it is bounded on the other axis instead, by
    :data:`PROSE_SHAPES`: prose exempts prose *by extension*, so a ``.sh``
    under an exempted prefix is still an offender — an executable ``.md`` is
    not, and the mode axis is closed by an equality of its own rather than by
    this clause (see :data:`PROSE_SHAPES`). Both halves of the clause are
    load-bearing and both are controlled: without ``endswith`` the exemption
    takes in a runner under either prefix, and without ``startswith`` it
    becomes "any prose shape anywhere" and takes in ``ci/forge-ci.yml`` and
    ``.github/workflows/*.yml``.
    """
    return [
        path
        for path in paths
        if path not in OVERRIDE_NAMERS
        and not (path.startswith(OVERRIDE_PROSE) and path.endswith(PROSE_SHAPES))
    ]


def test_nothing_in_the_tree_sets_either_of_the_guards_env_switches():
    """AC-1/AC-4's premise: a switch the producers set is not a switch.

    CARD-256 widened this from the override alone (it was
    ``test_nothing_in_the_tree_sets_the_override_for_a_run``) to both of the
    guard's env switches, because the second one is the silent one and had no
    scan at all. The route is the same file: ``scripts/run_admin_tests.sh`` is
    an in-tree pytest wrapper with a block of ``export``s, and an
    ``export NONOGRAM_FULL_SUITE_LOCK=<a path holding no lock>`` there would
    make every verdict "no lock, go ahead" for every run through it. CARD-255
    cycle 2 proved this scan reds when the *override* is exported in such a
    file; that it reds on the other name too is measured, as the mutant that
    drops the second token from :func:`_scan` — it reds the control below.
    Two tokens, one scan, the same exemptions.

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
    that they set neither name is checked by reading them, not here.
    """
    hits = _scan(REPO)

    offenders = _scan_offenders(hits)

    assert not offenders, (
        f"{offenders} name {guard.OVERRIDE} or {guard.LOCK_PATH_VAR}; a tree that sets "
        "either one has neither an override nor a guard"
    )

    conftest = (REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert guard.OVERRIDE not in conftest
    assert guard.LOCK_PATH_VAR not in conftest


def test_an_executable_setter_under_an_allowlisted_prefix_is_still_caught(tmp_path):
    """The prose exemption's own control: what it must not be able to absorb.

    ADR-0039/R3 — an exemption set must be enumerable and controlled. The scan
    above is the whole tracked tree, and that reach was paid for with a prefix
    exemption for ``meta/kanban/cards/`` and ``meta/review/``. A prefix carries
    no constraint on a file's shape, so before :data:`PROSE_SHAPES` existed two
    executable ``run-the-suite.sh`` scripts — one under each prefix, each with
    ``export NONOGRAM_IGNORE_FULL_SUITE_LOCK=1`` — were listed by ``git grep``
    and the scan above stayed green with two live in-tree setters. That is
    cycle 1's finding one directory over: a setter nobody had written yet.

    So the probe becomes the control. In a **throwaway** repo on purpose: this
    test must never add a file under the real ``meta/``, where the board's own
    lock lives and where a gate may be running. The scan is the same
    ``git grep -l`` and the same predicate.
    """
    repo = tmp_path / "throwaway-tree"
    prose = {
        "meta/kanban/cards/CARD-999.md": f"the way out is `{guard.OVERRIDE}=1 pytest ...`\n",
        "meta/review/20261020T000000Z-CARD-999-cycle1.yml": f"title: {guard.OVERRIDE} is quoted\n",
    }
    setters = {
        "meta/kanban/cards/run-the-suite.sh": f'export {guard.OVERRIDE}=1\nexec pytest "$@"\n',
        "meta/review/run-the-suite.sh": f'export {guard.OVERRIDE}=1\nexec pytest "$@"\n',
        "meta/kanban/cards/point-the-guard-elsewhere.sh": (
            f'export {guard.LOCK_PATH_VAR}=/tmp/there-is-no-lock-here\nexec pytest "$@"\n'
        ),
    }
    elsewhere = {
        "ci/forge-ci.yml": f"env:\n  {guard.OVERRIDE}: '1'\n",
        ".github/workflows/suite.yml": (
            f"env:\n  {guard.LOCK_PATH_VAR}: /tmp/there-is-no-lock-here\n"
        ),
        "docs/running-the-suite.md": f"`{guard.LOCK_PATH_VAR}=/tmp/there-is-no-lock-here pytest`\n",
    }
    for relative, body in {**prose, **setters, **elsewhere}.items():
        written = repo / relative
        written.parent.mkdir(parents=True, exist_ok=True)
        written.write_text(body, encoding="utf-8")
        if written.suffix == ".sh":
            written.chmod(0o755)
    for command in (["git", "init", "-q"], ["git", "add", "-Af", "."]):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)

    hits = _scan(repo)

    assert sorted(hits) == sorted({**prose, **setters, **elsewhere}), (
        f"the probe is not what this test thinks it is: the scan saw {hits}"
    )
    assert all(path.startswith(OVERRIDE_PROSE) for path in setters), (
        "the setters no longer sit under the exempted prefixes, so they prove nothing "
        "about the clause that bounds them"
    )
    assert not any(path.startswith(OVERRIDE_PROSE) for path in elsewhere) and all(
        path.endswith(PROSE_SHAPES) for path in elsewhere
    ), (
        "the files outside the prefixes are no longer prose-shaped, so they prove "
        "nothing about the clause that bounds the exemption to those two directories"
    )

    assert sorted(_scan_offenders(hits)) == sorted({**setters, **elsewhere}), (
        "an executable setter under an allowlisted prefix was absorbed by the exemption; "
        "the scan above would be green with a live in-tree setter"
    )
    assert sorted(_scan_offenders(list(elsewhere))) == sorted(elsewhere), (
        "a `.md`/`.yml` setter outside both exempted prefixes was absorbed: with the "
        "prefix half of the clause gone the exemption is 'any prose shape anywhere', "
        "which takes in ci/forge-ci.yml and .github/workflows/*.yml"
    )
    assert _scan_offenders(list(prose)) == [], (
        "the per-card prose the exemption exists for is no longer exempt"
    )

    assert "100755" in _tracked_modes(repo), (
        "the mode axis cannot be measured: this repo holds an executable under an "
        "exempted prefix and git does not record it, so the equality in "
        "test_the_exempted_prefixes_hold_nothing_a_shell_can_run cannot fail and "
        "claims nothing"
    )


def test_the_exempted_prefixes_hold_nothing_a_shell_can_run():
    """The mode axis the extension clause cannot bound, closed by an equality.

    :data:`PROSE_SHAPES` bounds the exemption to ``.md`` and ``.yml``, which
    is an extension and not a capability: an executable ``.md`` under either
    prefix is exempted by that clause, and the exemption's own control
    (:func:`test_an_executable_setter_under_an_allowlisted_prefix_is_still_caught`)
    cannot see it because it probes the extension axis.

    So the other axis is held here, as the equality ADR-0039/R3 asks for and
    over the whole tracked population rather than a sample: ``git ls-files -s``
    over both prefixes, every mode ``100644``. Nothing under those two
    directories is executable today, which is what makes "prose exempts
    prose" a measured claim; the first file that changes that reds this test,
    where the question "should the exemption see a file's mode?" can be
    answered on purpose instead of in silence.
    """
    modes = _tracked_modes(REPO)

    assert len(modes) >= 500, (
        f"the exempted prefixes hold {len(modes)} tracked files; the population this "
        "equality was measured over (546) cannot have shrunk by an order of magnitude, "
        "so the pathspecs no longer name what they did"
    )

    assert set(modes) == {"100644"}, (
        f"{sorted(set(modes))} under {OVERRIDE_PROSE}: something a shell can run sits "
        "under a prefix the scan exempts by extension, so an executable .md/.yml setter "
        "there would be absorbed"
    )


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


def test_a_redirected_run_says_which_lock_it_read(monkeypatch, tmp_path):
    """AC-3. The hole F-203 probed, which was the silent kind.

    Pointed at a path holding no lock, the guard reported ``386 passed``,
    ``current_verdict() == (True, None)`` and ``report_line() is None`` — so
    on a board where the real file would have refused that run, it is a run
    allowed that should have been refused, printing nothing at all. That is
    the certifier's probe, re-run in this card's evidence and now answered
    with a line. The redirection is not the defect and is not
    removed here (the tests above need it, and must never touch the board's
    own lock); the silence is. So what is held is the sentence, and the mutant
    this test exists for deletes the announcement, not the redirection.
    """
    elsewhere = tmp_path / "pretend.lock"
    monkeypatch.setenv(guard.LOCK_PATH_VAR, str(elsewhere))

    note = guard.redirect_note()

    assert note is not None, "the lock path was redirected and the run said nothing"
    assert str(elsewhere) in note, "the announcement does not name the lock it read"
    assert guard.LOCK_PATH_VAR in note, (
        "the announcement does not name the switch that redirected the guard"
    )
    assert str(guard.default_lock_path()) in note, (
        "the announcement does not say which lock was not read"
    )


def test_an_ordinary_run_says_nothing_about_where_its_lock_came_from(monkeypatch):
    """AC-3's other half, and the half that rots.

    Unset is the production configuration — the scan above holds that no
    tracked file in this tree names the variable, and the only setters in the
    tree are this file's own tests — and a provenance line on an unredirected
    run would be noise in the output the override and the stale-lock
    walk-past have to be visible in. This is also the only place the unset
    case *can* be measured: every real-process case in this file redirects the
    path by construction, because none of them may read the board's own lock.

    The empty value is the same answer as unset, which is how
    :func:`guard.lock_path` reads it (``if named:``) — stated here because a
    line that announced a redirection that did not happen would be a false
    announcement, the same defect in the other direction.
    """
    monkeypatch.delenv(guard.LOCK_PATH_VAR, raising=False)

    assert guard.redirect_note() is None, (
        "a run reading the board's own lock announced a redirection"
    )

    monkeypatch.setenv(guard.LOCK_PATH_VAR, "")

    assert guard.redirect_note() is None, (
        f"{guard.LOCK_PATH_VAR}='' redirects nothing, so there is nothing to announce"
    )


def test_the_summary_hook_says_nothing_when_there_is_nothing_to_say(monkeypatch):
    """AC-3/AC-5 at the hook: silence is the default, and it is measured here.

    Every real-process case in this file redirects the lock path, so every one
    of them now has something to announce — which leaves the *silent* branch
    of :func:`guard.pytest_terminal_summary` unreachable in a subprocess
    without pointing a run at the board's own lock, and G-5 forbids that. So
    the hook is called directly, both ways, with a reporter that records what
    it is handed.

    The mutant this closes prints on every run regardless
    (``if _ANNOUNCEMENT`` widened): ``write_line`` does not reject ``None``,
    so under it every ordinary run on the board grows a line reading
    ``None`` — and nothing in a real-process case here could tell.
    """

    class Reporter:
        def __init__(self):
            self.lines = []

        def write_line(self, line, **_markup):
            self.lines.append(line)

    quiet = Reporter()
    monkeypatch.setattr(guard, "_ANNOUNCEMENT", None)
    guard.pytest_terminal_summary(quiet, 0, None)

    assert quiet.lines == [], (
        f"a run with nothing to report wrote {quiet.lines} to the summary"
    )

    loud = Reporter()
    monkeypatch.setattr(guard, "_ANNOUNCEMENT", "full-suite lock: something happened")
    guard.pytest_terminal_summary(loud, 0, None)

    assert loud.lines == ["full-suite lock: something happened"], (
        f"a decision was taken and the summary said {loud.lines}"
    )


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

    # Exit 4, not merely non-zero. ``pytest.UsageError`` is pytest's
    # USAGE_ERROR and is the only outcome this abort has, which is what the
    # card's "What a gate sees now" block states; a different code means the
    # abort moved to another mechanism. Measured: the mutant that aborts with
    # ``pytest.exit(said)`` instead exits 2, and every real-run assertion in
    # this file that asked only for non-zero stayed green under it.
    assert result.returncode == 4, combined
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

    Two rules, and what the second adds to the first is exactly two names.
    The first is a **text** rule over the whole file, prose included: a
    docstring that explained the abort by naming the alternative would red it,
    and that is the intended strictness — it fails in the safe direction. It
    runs first, so while it passes five of the seven names below cannot be
    spelled anywhere in the module at all: ``skip``, ``skipif`` and
    ``importorskip`` are forbidden as substrings of ``"skip"``, and
    ``add_marker`` and ``xfail`` by name.

    The syntax rule's independent reach is therefore the non-result *exit*
    APIs — ``exit`` and ``Exit`` — which no substring rule here forbids. One
    name of it is demonstrably live: the mutant replacing
    ``raise pytest.UsageError(said)`` with ``pytest.exit(said)`` is killed
    here, and (before the exit-code assertion in
    :func:`test_a_foreign_lock_aborts_a_real_run_before_collection`) was killed
    nowhere else. Walking the syntax rather than the text is also what makes
    the claim "the module *calls* no such API" instead of "never writes the
    word".
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
    forbidden_apis = {
        "skip",
        "skipif",
        "importorskip",
        "xfail",
        "add_marker",
        "exit",
        "Exit",
    }

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
    for verdict_said in ("Refusing to start", "running anyway", "stale"):
        assert verdict_said not in combined, (
            f"the gate's own run reports a lock verdict nobody needs to read: {verdict_said!r}"
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


def test_a_redirected_real_run_announces_it_in_the_terminal_summary(tmp_path):
    """AC-3 in a real process, at ``-q``, which is where every gate runs.

    ``pyproject`` sets ``addopts = "-q"`` and pytest prints no run header at
    that verbosity, so the header line :func:`guard.report_line` feeds cannot
    be where this is proved — the terminal summary is, for the same reason the
    override's announcement goes through it.

    The lock path here holds no lock at all: that is F-203's probe exactly, a
    run that would have been refused had it read the board's own file, and the
    one that used to print nothing.
    """
    result = _run_pytest(tmp_path / "there-is-no-lock-here.lock")
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "1 passed" in combined
    assert str(tmp_path / "there-is-no-lock-here.lock") in combined, (
        "a run that read its lock from somewhere else did not say which file"
    )
    assert guard.LOCK_PATH_VAR in combined, (
        "a redirected run did not name the switch that redirected it"
    )


def test_a_tree_with_no_lock_runs_exactly_as_it_did_before(tmp_path):
    """AC-5 — the ordinary run: unchanged, and silent about all of this.

    "Silent" is the **verdict** and the skip profile, which is what CARD-255
    proved here and what has not moved. Since CARD-256 this run also carries
    one line it asks for itself: it points :data:`guard.LOCK_PATH_VAR` at a
    temp path, because it may not read the board's own lock, and a redirected
    run says so. The production case — the variable unset, nothing said at all
    — is :func:`test_an_ordinary_run_says_nothing_about_where_its_lock_came_from`,
    which is where it can be measured without a lock file anywhere near it.
    """
    result = _run_pytest(tmp_path / "there-is-no-lock-here.lock")
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "1 passed" in combined
    assert "skipped" not in combined, "the abort became a skip, which is AC-5's whole worry"
    assert guard.OVERRIDE not in combined, (
        "a run with no lock advertises the override, which is noise on every run"
    )
    for verdict_said in ("Refusing to start", "running anyway", "stale"):
        assert verdict_said not in combined, (
            f"a run with no lock in sight reports a verdict: {verdict_said!r}"
        )
