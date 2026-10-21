"""CARD-260 — a per-assertion kill matrix, with its six known traps as controls.

What this module measures
-------------------------
For one target test file and a set of mutants, it reports **every**
``ast.Assert`` node in that file as ``PASS``, ``FAIL``, ``NOT-REACHED`` or
``BLIND``. That is the whole claim: a per-assertion reading, keyed on each
node's own ``lineno``.

Why per-assertion at all: a test short-circuits at its first failing assert, so
one ``FAILED`` line says nothing about the arms that never ran — **a surviving
mutant and a never-reached assert look identical** in a test-level reading.

The two passes, and why both
----------------------------
Both are built from **one** transformer, :class:`_Recorder`, differing only in
whether its handler re-raises. That is not an economy; it is the control. The
recording pass *is* the handler that forgot the ``raise``, so the re-raising
pass's control has a failing state that exists on disk rather than being
hypothesised.

* :attr:`Pass.RECORDING` — the handler records and continues. Every arm of a
  test is measured independently and no short-circuit can hide one. The price
  is suppressed propagation: with ``child_instrumentation=True`` an assertion
  whose truth depends on a child pytest's outcome **cannot record FAIL**, so
  such cells are reported ``BLIND`` rather than ``PASS``.
* :attr:`Pass.RERAISING` — the handler records and re-raises. True propagation
  and true cross-process semantics, at the price of stopping at the first
  failing assert in a test, which leaves the later arms ``NOT-REACHED``.

Neither pass alone is the kill set. Stated as the generalisation this board
measured: *an instrumented-only kill is an attribution a plain run cannot make;
a plain-only kill is an observation the instrument cannot make — and only the
second kind corrupts a figure.* An instrumented-only kill does **not** establish
that an arm has its own control (a subsumed arm reds under the instrument too),
only that the attribution needs the instrument.

The six traps, each an acceptance criterion with a control that can fail
-----------------------------------------------------------------------
1. A **test count** reported as an assertion count. :class:`Matrix` carries
   ``denominator`` (``ast.Assert`` nodes) and ``collected_tests`` as separate
   fields, and every figure it prints names which one it is quoting.
2. **Last-write-wins** aggregation losing a RED from an assert inside a loop.
   :func:`aggregate_any_red` is what runs; :func:`aggregate_last_write_wins` is
   kept beside it as the failing control.
3. **Suppressed propagation** across a process boundary — see ``BLIND`` above.
4. A **leaked patch**: SHIPPED is re-run and asserted all-PASS *between*
   mutants, not only at the start.
5. A **no-op mutant** whose ``old`` string is absent, and a mutant that hits a
   different occurrence than the caller meant. Both are refused.
6. **Line-count-shifting** mutants: refused, because the numbering shifts and
   every later assert then reports ``NOT-REACHED``. Equal line counts are not
   the invariant, only the cheap half of it: the target's assert **topology**
   (each node's ``lineno`` *and* what the assertion at it says) is re-derived
   from disk after every mutant is applied, so a moved, swapped or merged
   assert is refused rather than silently reported under another arm's cell.

A reading that is not a run
---------------------------
pytest's exit code is part of the figure, and only ``0`` (all green) and ``1``
(tests ran, some failed) are readings at all. ``2``/``3``/``4``/``5`` mean the
run was interrupted, broke internally, was refused before collection (what the
board's full-suite lock raises) or collected nothing — and the matrix those
produce is all-``NOT-REACHED`` and FAIL-free, which is indistinguishable from a
mutant every arm survived. Those are refused, not published.

**What exit ``1`` does not say is which cause it was.** The matrix's domain is
``ast.Assert`` nodes, so a failure expressed any other way — ``pytest.raises``,
``pytest.fail``, a ``unittest`` assertion, an assert inside a helper, or an
error before the first assert — is a real kill **no cell can account for**, and
its reading is ``0 FAIL`` at exit ``1``. That is published, not refused: a
refusal keyed on the position *exit 1 and no FAIL cell* cannot tell it from an
unattributed failure, and :class:`UnmeasuredRun` propagates out of
:meth:`Runner.run`, so one out-of-domain kill would destroy every other
mutant's reading in the same run — refusing hardest exactly where the target is
least assert-shaped. The distinction is **carried** instead: every mutant's own
``exit_code`` and reached count are in :meth:`KillMatrix.figure`, so a reader
separates ``0 reached, exit 1`` (nothing ran) from ``1 PASS, exit 1`` (a kill
outside the domain) from ``1 PASS, exit 0`` (a true survivor) with no predicate
that can be wrong about which cause it was. The one refusal is on **SHIPPED**:
a reading that reached no arm is not a baseline whatever its exit code, because
every mutant compared against it survives every arm by construction
(:meth:`Runner._refuse_unless_clean`).

Safety discipline
-----------------
* Refuses to start while **another worktree** holds the board's full-suite
  lock, at the path :mod:`tests.full_suite_lock` resolves (its
  ``LOCK_PATH_VAR`` override, else the **main** checkout's
  ``meta/kanban/.full-suite.lock`` — a linked worktree's own copy of that path
  is not where any gate writes). The verdict is that module's
  :func:`~tests.full_suite_lock.current_verdict`, not a second opinion
  assembled here: identity is the worktree, so a lock this instrument's **own**
  tree holds does not refuse — every full-suite gate holds one for its whole
  duration, and a strict reading therefore cannot run inside the gate that
  must certify it. It never writes a lock anywhere, and the ``repo_root`` it is
  handed does not move this path.
* Takes a targeted selection resolving to exactly one existing file; refuses an
  empty selection, a directory, anything that is not an existing file, and a
  selection spanning more than one file.
* ``cp -p`` backups, every later edit's content read **from the backup**,
  restore in a ``finally`` verified with ``diff -q`` **and** ``shasum -a 256``
  — every registered path restored *before* any verification failure is
  raised, and a ``shasum`` that could not run counted as one of those failures.
  Each of those three is held by a **planted failure** rather than by this
  sentence: a ``cp`` that reports success and copies nothing reds the
  ``diff -q`` arm and the digest arm in separate tests, a ``PATH`` with no
  ``shasum`` on it reds the third, and a removed backup reds the
  restore-every-path rule (:meth:`Runner._verification_failures` names them).
  **No git command anywhere**, which ``test_kill_matrix.py`` enumerates from
  this module's own AST. The whole temp tree — the backups, the generated
  plugin and every ``records-*`` directory — is removed when :meth:`Runner.run`
  returns, and **kept** when a restore did not verify: there the backup is the
  only intact copy, and the exception names the directory.
* Refuses an edit whose text names ``_refuse_unless_test_database`` or
  ``nonogram_poc``, and an edit that lands on ``tests/conftest.py`` or
  ``tests/database_guard.py`` **by identity** — after ``realpath``, compared
  ``casefold``-ed and cross-checked with ``samefile``, so a mis-cased spelling,
  a mis-cased directory, a ``..`` or a symlink all lose. That is a
  path-and-text refusal, not an analysis of what an edit would do: it is the
  set of sites that carry the guard today, and the text half catches only an
  edit that *names* one of two literals (see ``_FORBIDDEN_TEXT``).
* Takes no timing measurements and reports none. The ``timeout=`` passed to
  ``subprocess.run`` is a bound on a hung child, not a measurement: nothing
  reads a clock and no figure here is a duration.

Stdlib (``ast``, ``collections.abc``, ``dataclasses``, ``enum``, ``json``,
``os``, ``pathlib``, ``re``, ``shutil``, ``subprocess``, ``sys``, ``tempfile``
— every one of them, and no ``hashlib``: the digest comes from the external
``shasum`` binary) plus exactly one module from this tree's own
``tests/`` directory — :mod:`tests.full_suite_lock`, which **owns** the lock
path above and is imported rather than re-derived from. No new runtime
dependency; ``test_g4_the_instrument_imports_stdlib_and_one_named_sibling``
holds that set.
"""

from __future__ import annotations

import ast
import enum
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

try:  # imported as ``tests.kill_matrix`` by the suite ...
    from tests import full_suite_lock
except ImportError:  # pragma: no cover - ... and as bare ``kill_matrix`` by the
    import full_suite_lock  # generated plugin, which puts ``tests/`` on sys.path

__all__ = [
    "BLIND",
    "FAIL",
    "NOT_REACHED",
    "PASS",
    "Edit",
    "KillMatrix",
    "LeakedPatch",
    "LockHeld",
    "Matrix",
    "Mutant",
    "MutantRefused",
    "Pass",
    "Runner",
    "SelectionRefused",
    "UnmeasuredRun",
    "aggregate_any_red",
    "aggregate_last_write_wins",
    "assert_linenos",
    "assert_shapes",
    "board_lock_path",
    "collected_tests",
    "child_dependent_linenos",
]

PASS = "PASS"
FAIL = "FAIL"
NOT_REACHED = "NOT-REACHED"
BLIND = "BLIND"

#: The record sink's name in the instrumented module's own globals.
_SINK = "__kill_matrix_record__"

#: Env vars the generated pytest plugin reads. Child processes that inherit the
#: environment and the plugin flag are instrumented too; that is what makes the
#: recording pass's blind spot real rather than hypothesised.
_ENV_TARGET = "KILL_MATRIX_TARGET"
_ENV_RECORD_DIR = "KILL_MATRIX_RECORD_DIR"
_ENV_RERAISE = "KILL_MATRIX_RERAISE"

#: Nothing this instrument edits may touch the database guard. Refused, not
#: warned about: ``nonogram_poc`` is the live admin panel's database.
#:
#: **What these two literals cannot catch, stated plainly:** they catch an edit
#: that *names* one of them, and nothing else. An edit that defeats the guard
#: without naming either is easy to write and preserves the line count —
#: ``'.endswith("_test")'`` -> ``'.endswith("")'`` on ``tests/conftest.py:287``
#: is one, and it reaches the ``DROP SCHEMA public CASCADE`` at
#: ``tests/conftest.py:505``. What closes that is the **path** half below, by
#: identity: both halves of the guard live in exactly those two files, so such
#: an edit is refused for *where it lands* rather than for what it says. The
#: text half's own reach is an edit to a copy of the guard somewhere else in a
#: tree, and any edit that re-introduces the live panel's database name.
_FORBIDDEN_TEXT = ("_refuse_unless_test_database", "nonogram_poc")
_FORBIDDEN_PATHS = (("tests", "conftest.py"), ("tests", "database_guard.py"))

#: The same two files in *this* tree, by identity rather than by spelling —
#: ``kill_matrix.py`` sits beside them, so no path arithmetic is needed.
_GUARD_FILES = tuple(
    Path(__file__).resolve().parent / forbidden[-1] for forbidden in _FORBIDDEN_PATHS
)


def _refuse_forbidden_path(path: Path) -> None:
    """Refuse an edit that lands on either half of the database guard (G-3).

    Three spellings of the same file all have to lose, because the window a
    raw tuple compare opened is not hypothetical: the mutant sits on disk for
    the length of that mutant's pytest subprocess, which is exactly when the
    destructive fixtures would run. (The ``cp -p`` backup names the same inode,
    so the file *is* restored afterwards — the hazard is the window, not a
    persistent clobber.)

    * ``..`` and symlinks — compared after ``os.path.realpath``, which resolves
      both even when the tail does not exist.
    * **case** — compared ``casefold``-ed, because this board's volume is
      case-insensitive and ``os.path.normcase`` is the identity on posix, so
      ``tests/CONFTEST.py`` named the same file and walked straight past a raw
      tuple compare. Every part is folded, not only the file name:
      ``TESTS/conftest.py`` is the same file too.
    * **identity** — ``os.path.samefile`` against the two guard files in this
      tree, which catches a spelling no suffix comparison can predict: a hard
      link, or a symlinked directory anywhere above ``tests/``.

    Fail-closed on a case-sensitive volume: a genuinely distinct
    ``tests/CONFTEST.py`` would be refused there too. That direction is
    deliberate — this is the refusal standing between a mutant and the live
    panel's database, and a false refusal costs a rename.
    """
    resolved = Path(os.path.realpath(path))
    folded = tuple(part.casefold() for part in resolved.parts)
    for forbidden in _FORBIDDEN_PATHS:
        want = tuple(part.casefold() for part in forbidden)
        if folded[-len(want) :] == want:
            raise MutantRefused(
                f"refusing an edit to {'/'.join(forbidden)} (named here as "
                f"{path}): it carries the database guard"
            )
    for guard in _GUARD_FILES:
        try:
            same = guard.exists() and os.path.samefile(resolved, guard)
        except OSError:  # pragma: no cover - a path that cannot be stat'ed
            continue
        if same:
            raise MutantRefused(
                f"refusing an edit to {guard}, which is the same file as "
                f"{path}: it carries the database guard"
            )


class Pass(enum.Enum):
    """Which pass a figure came from. There is no default anywhere."""

    RECORDING = "recording"
    RERAISING = "re-raising"

    @property
    def reraise(self) -> bool:
        return self is Pass.RERAISING


class MutantRefused(Exception):
    """A mutant this instrument cannot measure honestly. Never a silent pass."""


class LeakedPatch(Exception):
    """SHIPPED is not usable as a baseline, so no later reading is trustworthy.

    Three shapes raise it, and the name is the first of them: a FAIL cell (an
    earlier patch is still on disk), a cell that moved against SHIPPED's own
    first reading (a leak that *removes* coverage), and a SHIPPED that reached
    **no** arm at all (nothing to be a baseline of — see
    :meth:`Runner._refuse_unless_clean`). Also raised by :meth:`Runner._restore`
    when a restore did not verify, which is the same claim about the disk.
    """


class SelectionRefused(Exception):
    """A selection this instrument will not run (empty, not a file, or the suite)."""


class LockHeld(Exception):
    """Another worktree holds the board's full-suite lock; it owns the host.

    Raised for a **foreign** holder only. A lock this instrument's own tree
    holds is the one every full-suite gate writes before running the suite
    this instrument's tests are part of, and is not this exception's subject.
    """


class UnmeasuredRun(Exception):
    """pytest did not run the selection, so there is nothing to report.

    Separate from :class:`MutantRefused` on purpose: nothing is wrong with the
    mutant, and separate from :class:`SelectionRefused` because the selection
    resolved. The run itself never happened, and the matrix it would produce is
    all-``NOT-REACHED`` and FAIL-free — the shape a mutant every arm survived
    also has.
    """


#: pytest exit codes that are a reading. ``0`` all green; ``1`` tests ran and
#: some failed — which is what a killed mutant and the whole re-raising pass
#: look like from outside. Everything else (``2`` interrupted, ``3`` internal
#: error, ``4`` usage error — a conftest hook refusing the run before
#: collection, which is what the board's full-suite lock raises — ``5`` nothing
#: collected) means the selection did not run.
#:
#: Chosen over ``collected_tests``, which is **regex-scraped** from pytest's
#: ``-q`` summary and would read ``None`` on a perfectly good run the day that
#: summary's wording changes. It stays print-only for that reason.
_RAN_EXIT_CODES = frozenset({0, 1})


def board_lock_path() -> Path:
    """The lock file the board's gates write, resolved by its **owner**.

    Not re-derived here. :func:`tests.full_suite_lock.lock_path` honours that
    module's :data:`~tests.full_suite_lock.LOCK_PATH_VAR` override (spelled
    there, not copied here: a tree-wide scan in
    ``test_nothing_in_the_tree_sets_either_of_the_guards_env_switches`` holds
    the set of files allowed to name it, and this is not one of them) and
    otherwise follows a linked worktree's
    ``.git`` pointer back to the main checkout — which is where every gate
    writes, whichever worktree it runs the suite in. Deriving this path from a
    caller's ``repo_root`` instead gave the *worktree's own* copy of it, and a
    per-worktree lock path is a guard that cannot see contention: the only
    contention there is was written to a file the instrument never looked at.
    """
    return full_suite_lock.lock_path()


# --------------------------------------------------------------------------
# The transformer — one of it, for both passes
# --------------------------------------------------------------------------


class _Recorder(ast.NodeTransformer):
    """Wrap every ``ast.Assert`` in a recording ``try/except AssertionError``.

    Keyed on each node's **own** ``lineno``, lifted into the rewritten code as
    a literal, so no by-text or first-occurrence targeting is used anywhere and
    a repeated assert source line cannot be confused with another.

    ``reraise`` is the only difference between the two passes. With it false
    this *is* the handler that forgot the ``raise``.
    """

    def __init__(self, reraise: bool) -> None:
        self.reraise = reraise
        self.seen: list[int] = []

    def visit_Assert(self, node: ast.Assert) -> ast.AST:
        self.generic_visit(node)
        lineno = node.lineno
        self.seen.append(lineno)
        handler_body: list[ast.stmt] = [self._record(lineno, False)]
        if self.reraise:
            handler_body.append(ast.Raise())
        wrapped = ast.Try(
            body=[node],
            handlers=[
                ast.ExceptHandler(
                    type=ast.Name(id="AssertionError", ctx=ast.Load()),
                    name=None,
                    body=handler_body,
                )
            ],
            orelse=[self._record(lineno, True)],
            finalbody=[],
        )
        return ast.fix_missing_locations(ast.copy_location(wrapped, node))

    @staticmethod
    def _record(lineno: int, ok: bool) -> ast.stmt:
        return ast.Expr(
            ast.Call(
                func=ast.Name(id=_SINK, ctx=ast.Load()),
                args=[ast.Constant(lineno), ast.Constant(ok)],
                keywords=[],
            )
        )


def assert_linenos(source: str, filename: str = "<target>") -> tuple[int, ...]:
    """Every ``ast.Assert`` node's own ``lineno``, at any depth, in order.

    This is the matrix's denominator and its domain: assertion **nodes**, never
    collected tests. Derived by walking the tree, not by reading the file.
    """
    tree = ast.parse(source, filename=filename)
    return tuple(
        node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)
    )


def assert_shapes(
    source: str, filename: str = "<target>"
) -> tuple[tuple[int, str], ...]:
    """Every ``ast.Assert`` as ``(lineno, normalised source)``, sorted.

    The matrix's key set **together with what each key means**, which is
    strictly more than :func:`assert_linenos` carries. Two asserts swapped keep
    the tuple of linenos identical while every cell now reports the other arm's
    outcome — a misattribution that leaves no off-key record behind for anything
    to notice. Two asserts merged onto one line keep the line count while
    turning two nodes into one cell.

    ``ast.unparse`` normalises the node, so re-indenting or re-wrapping an
    assertion is not a change here, while a different assertion is.
    """
    tree = ast.parse(source, filename=filename)
    return tuple(
        sorted(
            (node.lineno, ast.unparse(node))
            for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
        )
    )


# --------------------------------------------------------------------------
# Trap 3 — which arms read a child process's outcome
# --------------------------------------------------------------------------

#: Call spellings that may start another process. Default-deny: a call whose
#: callee mentions any of these counts as a spawn, and an unparsable callee
#: counts as a spawn too.
_SPAWN = re.compile(
    r"\b(subprocess|Popen|check_output|check_call|spawn|popen|fork|execv|"
    r"multiprocessing|os\.system)\b"
)


def child_dependent_linenos(source: str, filename: str = "<target>") -> frozenset[int]:
    """Assert linenos whose truth may depend on a child process's outcome.

    Derived from the target's own AST (ADR-0039/R2), not hand-written: within
    each function, every ``ast.Assert`` that sits **after** a call which may
    start a process is child-dependent.

    It defaults to deny, so it over-marks rather than under-marks: a callee
    this cannot unparse is treated as a spawn, and every later arm of the same
    function is marked whether or not it reads the child's result.

    **Declared bound:** the analysis is intra-function. An arm that reads a
    child's outcome through a value a *helper* returned, or through a fixture,
    is not marked by this rule.
    """
    tree = ast.parse(source, filename=filename)
    marked: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        spawns: list[int] = []
        asserts: list[int] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                try:
                    callee = ast.unparse(child.func)
                except Exception:  # pragma: no cover - default-deny branch
                    spawns.append(child.lineno)
                    continue
                if _SPAWN.search(callee):
                    spawns.append(child.lineno)
            elif isinstance(child, ast.Assert):
                asserts.append(child.lineno)
        if not spawns:
            continue
        first = min(spawns)
        marked.update(lineno for lineno in asserts if lineno > first)
    return frozenset(marked)


# --------------------------------------------------------------------------
# Trap 2 — aggregation
# --------------------------------------------------------------------------


def aggregate_any_red(outcomes: Sequence[bool]) -> str:
    """``FAIL`` if **any** execution of this assert failed. What runs.

    An assert inside a ``for`` loop executes once per iteration, and an assert
    in a test parametrised or run in two processes executes once per run. One
    RED anywhere is a kill.
    """
    if not outcomes:
        return NOT_REACHED
    return PASS if all(outcomes) else FAIL


def aggregate_last_write_wins(outcomes: Sequence[bool]) -> str:
    """The failing control for :func:`aggregate_any_red`, kept so it can fail.

    This is trap 2 as it bit: the last execution overwrites the earlier ones,
    so a RED on the first iteration of a loop is lost. It is never used to
    report a figure; ``test_kill_matrix.py`` holds the two to disagreeing on a
    two-iteration arm, which is the only thing that keeps this honest.
    """
    if not outcomes:
        return NOT_REACHED
    return PASS if outcomes[-1] else FAIL


# --------------------------------------------------------------------------
# Mutants
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Edit:
    """One text substitution, validated before it is applied.

    ``expect`` is the number of occurrences of ``old`` the caller asserts are
    in the file; all of them are replaced. ``occurrence`` (1-based) instead
    targets exactly one of them, which is what a repeated assert source line
    forces a caller to do.
    """

    path: Path
    old: str
    new: str
    expect: int = 1
    occurrence: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        if self.occurrence is not None and self.occurrence < 1:
            raise MutantRefused(
                f"occurrence must be 1-based, got {self.occurrence!r}"
            )
        for text in (self.old, self.new):
            for banned in _FORBIDDEN_TEXT:
                if banned in text:
                    raise MutantRefused(
                        f"refusing an edit that mentions {banned!r}: the database "
                        "guard is never widened or bypassed, and the live panel's "
                        "database is never named here"
                    )
        _refuse_forbidden_path(self.path)


@dataclass(frozen=True)
class Mutant:
    """A named set of edits, applied together and restored together."""

    name: str
    edits: tuple[Edit, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "edits", tuple(self.edits))
        if not self.edits:
            raise MutantRefused(f"mutant {self.name!r} edits nothing")

    @property
    def paths(self) -> tuple[Path, ...]:
        seen: list[Path] = []
        for edit in self.edits:
            if edit.path not in seen:
                seen.append(edit.path)
        return tuple(seen)


def apply_edit(source: str, edit: Edit) -> str:
    """``source`` with ``edit`` applied, or :class:`MutantRefused`.

    Three refusals, all of them because the alternative is a reading that
    cannot be told apart from a real one:

    * ``old`` absent — a **no-op mutant**. It writes nothing, every assert
      passes, and that is indistinguishable from a surviving mutant (trap 5).
    * ``old`` present a different number of times than ``expect``, with no
      ``occurrence`` named — the caller does not know which site it is hitting,
      and a by-text substitution on a repeated line mutates a different test
      and returns a false reading (trap 5).
    * the substitution changes the **line count** — every later assert's
      ``lineno`` shifts, so the whole matrix below the edit reports
      ``NOT-REACHED`` and a shifted numbering is indistinguishable from a
      wholly unreached file (trap 6).

    The line-count check is a *text* check and it is not the invariant the
    matrix needs; it is only the half that can be seen before the edit is on
    disk. The invariant — each assert still at its own lineno, still saying
    what it said — is re-derived from the mutated file by
    :meth:`Runner._refuse_unless_topology_holds`, which is what catches an
    equal-line-count substitution that moves, swaps or merges an assert.
    """
    found = source.count(edit.old)
    if found == 0:
        raise MutantRefused(
            f"no-op mutant: {edit.old!r} does not occur in {edit.path} — a "
            "mutant that changes nothing is indistinguishable from a surviving "
            "one"
        )
    if edit.occurrence is None:
        if found != edit.expect:
            raise MutantRefused(
                f"{edit.old!r} occurs {found} times in {edit.path}, not "
                f"{edit.expect}: target the intended occurrence explicitly with "
                "occurrence=<1-based index>, because a by-text substitution on a "
                "repeated line mutates a different site and returns a false "
                "reading"
            )
        mutated = source.replace(edit.old, edit.new)
    else:
        if edit.occurrence > found:
            raise MutantRefused(
                f"{edit.old!r} occurs {found} times in {edit.path}; there is no "
                f"occurrence {edit.occurrence}"
            )
        head, sep, tail = _split_at_occurrence(source, edit.old, edit.occurrence)
        mutated = head + edit.new + tail
        assert sep == edit.old
    _refuse_line_shift(source, mutated, edit)
    return mutated


def _split_at_occurrence(source: str, old: str, occurrence: int):
    index = -1
    for _ in range(occurrence):
        index = source.index(old, index + 1)
    return source[:index], source[index : index + len(old)], source[index + len(old) :]


def _refuse_line_shift(source: str, mutated: str, edit: Edit) -> None:
    """Equal newline counts **and** equal ``splitlines()`` length, both checked.

    **Necessary, not sufficient**, and the gap is not academic: an
    equal-line-count substitution can still move an assert to another line, or
    swap two of them, or put two on one line. This check cannot see any of
    those — only :meth:`Runner._refuse_unless_topology_holds` can, by parsing
    the file that is actually about to be measured. Keep them apart: this one
    runs before anything is written, on text, for any edit to any file; that
    one runs after ``_apply``, on the target's AST.

    Two checks rather than one because they do not see the same thing: a
    trailing newline added or removed at the end of the file moves
    ``count("\\n")`` without moving ``len(splitlines())``, and a lone ``\\r``
    or ``\\x0b`` introduced by a substitution moves ``len(splitlines())``
    without moving ``count("\\n")``.
    """
    before = (source.count("\n"), len(source.splitlines()))
    after = (mutated.count("\n"), len(mutated.splitlines()))
    if before != after:
        raise MutantRefused(
            f"line-count-shifting mutant on {edit.path}: newlines "
            f"{before[0]} -> {after[0]}, splitlines {before[1]} -> {after[1]}. "
            "Every assert below the edit would shift its lineno and report "
            "NOT-REACHED, which is indistinguishable from a file that never "
            "ran — substitute a line, do not delete one"
        )


# --------------------------------------------------------------------------
# Figures — a figure that does not carry its domain is the defect
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Matrix:
    """One pass over one target under one mutant.

    ``pass_`` and ``denominator`` have no defaults, and every figure this
    prints names both. The denominator is the number of ``ast.Assert`` nodes in
    the target, which is **not** the collected test count: ``collected_tests``
    is carried separately, precisely so that a figure cannot quote one while
    meaning the other.
    """

    target: Path
    pass_: Pass
    label: str
    denominator: int
    cells: Mapping[int, str]
    #: Every execution's outcome per assert, in order, across all pids. Carried
    #: so the aggregation's control can be fed the identical records: an assert
    #: inside a ``for`` loop records once per iteration, and one in a test that
    #: also runs in a child process records once per pid.
    records: Mapping[int, tuple[bool, ...]]
    #: The same reading **before** the ``BLIND`` overlay. Kept so the
    #: blind-spot claim has a control that can fail: on a child-dependent arm
    #: in the recording pass this says ``PASS`` where :attr:`cells` says
    #: ``BLIND``, and that disagreement is the trap, measured.
    raw_cells: Mapping[int, str]
    collected_tests: int | None
    exit_code: int
    #: Whether a pytest the target *spawned* was instrumented too. Carried and
    #: printed because it is the second half of this figure's domain: with it
    #: **off** no ``BLIND`` cell can exist, so a ``0 BLIND`` reading means
    #: "the overlay never ran" rather than "no arm is blind", and an arm that
    #: executes only inside the child records nothing here. A figure that does
    #: not carry its domain is the defect this instrument exists to prevent.
    child_instrumentation: bool

    def __post_init__(self) -> None:
        if not isinstance(self.pass_, Pass):
            raise TypeError(
                "pass_ must be a Pass member: a figure that does not carry its "
                "domain is the defect this instrument exists to prevent"
            )
        if len(self.cells) != self.denominator:
            raise ValueError(
                f"{len(self.cells)} cells for a denominator of {self.denominator}: "
                "the matrix must report every assertion node, reached or not"
            )

    def of(self, outcome: str) -> tuple[int, ...]:
        return tuple(sorted(l for l, cell in self.cells.items() if cell == outcome))

    @property
    def passed(self) -> tuple[int, ...]:
        return self.of(PASS)

    @property
    def failed(self) -> tuple[int, ...]:
        return self.of(FAIL)

    @property
    def not_reached(self) -> tuple[int, ...]:
        return self.of(NOT_REACHED)

    @property
    def blind(self) -> tuple[int, ...]:
        return self.of(BLIND)

    def figure(self) -> str:
        """The only sentence this class prints, and it carries all of it.

        Domain: which pass, **and** whether the child was instrumented — a
        ``0 BLIND`` is ambiguous without the second. Denominator: assertion
        nodes, named as such. Plus pytest's own exit code, because a reading
        taken from a run that never happened is FAIL-free too. There is no
        shorter accessor that omits any of them, and no ``__str__`` that does.
        """
        counts = ", ".join(
            f"{len(self.of(outcome))} {outcome}"
            for outcome in (PASS, FAIL, NOT_REACHED, BLIND)
        )
        child = "on" if self.child_instrumentation else "off"
        return (
            f"{self.label} / {self.pass_.value} pass over {self.target.name}: "
            f"{counts} of {self.denominator} assertion nodes"
            f" (collected tests: {self.collected_tests};"
            f" pytest exit {self.exit_code};"
            f" child instrumentation {child})"
        )

    def table(self) -> str:
        """One line per assertion node, each naming the pass it came from."""
        header = f"# {self.figure()}"
        rows = [
            f"{self.target.name}:{lineno} {self.cells[lineno]} [{self.pass_.value}]"
            for lineno in sorted(self.cells)
        ]
        return "\n".join([header, *rows])


@dataclass(frozen=True)
class KillMatrix:
    """SHIPPED plus one :class:`Matrix` per mutant, all from the same pass."""

    target: Path
    pass_: Pass
    denominator: int
    shipped: Matrix
    mutants: Mapping[str, Matrix]
    shipped_between: Mapping[str, Matrix]
    #: The same second half of the domain :class:`Matrix` carries, so the
    #: aggregate figure states it without having to reach into ``shipped``.
    child_instrumentation: bool

    def cell(self, mutant: str, lineno: int) -> str:
        return self.mutants[mutant].cells[lineno]

    def figure(self) -> str:
        """Carries the pass, the denominator and its domain, unconditionally.

        ``SHIPPED 0 FAIL`` is not a reassurance on its own — a run pytest
        refused before collection has no FAILs either — so the sentence also
        carries how many of SHIPPED's arms were reached, pytest's exit code and
        its collected-test count, and whether the child was instrumented.

        **And the same for every mutant, not only SHIPPED.** A mutant's cells
        can be FAIL-free for three different reasons, and the grid is identical
        for the **last two** of them -- the first is separated by the reached
        count, which is derived from the cells: nothing ran (``0 reached``),
        the kill was expressed
        outside this matrix's domain of ``ast.Assert`` nodes and no cell can
        account for it (``exit 1`` with arms reached and none FAIL), or the arms
        genuinely survived (``exit 0``). Each mutant's own ``exit_code`` and
        reached count are therefore in this sentence — the module's own rule
        that a figure which does not carry its domain is the defect it exists to
        prevent, applied to the aggregate a consumer actually reads.
        :meth:`table` carries all of it too, because its header is this
        sentence. Carried rather than decided: no predicate here can be wrong
        about which of the three it was.
        """
        reached = self.denominator - len(self.shipped.not_reached)
        child = "on" if self.child_instrumentation else "off"
        per_mutant = (
            "; ".join(
                f"{name} exit {matrix.exit_code} with "
                f"{self.denominator - len(matrix.not_reached)} reached and "
                f"{len(matrix.failed)} FAIL"
                for name, matrix in self.mutants.items()
            )
            or "none"
        )
        return (
            f"{len(self.mutants)} mutants / {self.pass_.value} pass over "
            f"{self.target.name}: {self.denominator} assertion nodes "
            f"(ast.Assert node count, not a collected test count); "
            f"SHIPPED {len(self.shipped.failed)} FAIL of {reached} reached "
            f"(pytest exit {self.shipped.exit_code}, collected tests "
            f"{self.shipped.collected_tests}); child instrumentation {child}; "
            f"per mutant: {per_mutant}"
        )

    def table(self) -> str:
        """The grid, with the pass and the denominator in its header."""
        names = list(self.mutants)
        lines = [f"# {self.figure()}", "assert | SHIPPED | " + " | ".join(names)]
        for lineno in sorted(self.shipped.cells):
            row = [f"{self.target.name}:{lineno}", self.shipped.cells[lineno]]
            row += [self.mutants[name].cells[lineno] for name in names]
            lines.append(" | ".join(row))
        lines.append(f"# domain: {self.pass_.value} pass")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# The runner
# --------------------------------------------------------------------------

_PLUGIN_SOURCE = '''\
"""Generated by tests/kill_matrix.py. Instruments one target module."""
import ast, json, os, pathlib, sys, types

_TARGET = pathlib.Path(os.environ[{env_target!r}]).resolve()
_RECORD_DIR = pathlib.Path(os.environ[{env_record_dir!r}])
_RERAISE = os.environ.get({env_reraise!r}) == "1"

sys.path.insert(0, {instrument_dir!r})
import kill_matrix as _km


def _module_name(path):
    parts = [path.stem]
    folder = path.parent
    while (folder / "__init__.py").exists():
        parts.insert(0, folder.name)
        folder = folder.parent
    return ".".join(parts), folder


def _sink():
    handle = open(_RECORD_DIR / ("%d.jsonl" % os.getpid()), "a", buffering=1)

    def record(lineno, ok):
        handle.write(json.dumps([lineno, ok]) + "\\n")

    return record


def pytest_configure(config):
    name, root = _module_name(_TARGET)
    if name in sys.modules:
        return
    tree = ast.parse(_TARGET.read_text(encoding="utf-8"), filename=str(_TARGET))
    tree = _km._Recorder(_RERAISE).visit(tree)
    ast.fix_missing_locations(tree)
    code = compile(tree, str(_TARGET), "exec")
    module = types.ModuleType(name)
    module.__file__ = str(_TARGET)
    module.__dict__[_km._SINK] = _sink()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    sys.modules[name] = module
    exec(code, module.__dict__)
'''

_OUTCOME = re.compile(
    r"(\d+) (?:passed|failed|errors?|skipped|xfailed|xpassed|deselected)"
)


def collected_tests(output: str) -> int | None:
    """How many tests pytest reported, summed from its own summary line.

    Kept strictly apart from the matrix's denominator and never used as one:
    this is trap 1's number, and the only reason to carry it at all is so a
    figure can print both and name which is which.
    """
    for line in reversed(output.splitlines()):
        counts = _OUTCOME.findall(line)
        if counts:
            return sum(int(count) for count in counts)
    return None


@dataclass
class Runner:
    """Measures one target file under a targeted selection.

    Refuses to start while **another worktree** holds the board's real
    full-suite lock (G-2) — at the path :func:`board_lock_path` resolves, which
    ``repo_root`` does not move — never writes one, and never runs the full
    suite: the selection must be non-empty and every item must name an existing
    file (G-1). A lock its **own** tree holds does not refuse; see
    :meth:`_refuse_if_lock_held` for why that is G-2 read correctly rather than
    G-2 weakened.

    ``repo_root`` is the pytest ``cwd`` and the base a relative selection
    resolves against. Those two jobs only; it used to carry a third, the lock
    path, and the three wanted different values (F-001).

    ``child_instrumentation`` decides whether a pytest the target *spawns*
    inherits the instrumentation. Default **off**, because turning it on
    perturbs the target's own subprocess harness. With it **on**, the recording
    pass's suppression crosses the process boundary and the arms
    :func:`child_dependent_linenos` names are reported ``BLIND``: the child
    swallows its own ``AssertionError``, reports a pass with exit 0, and the
    parent's premise would otherwise record ``PASS`` by construction.

    With it **off** the child is pristine and propagation across the boundary
    is intact, so the arms that *read* a child's outcome are measured for
    real — and that is the whole of what default-off buys. **Declared bound:**
    an arm that executes only *inside* the child writes no record at all, so it
    is reported ``NOT-REACHED`` though it ran, and may have failed. With the
    overlay off ``NOT-REACHED`` therefore means "no execution recorded in the
    instrumented process", never "this arm did not run"; ``0 BLIND`` means the
    overlay never ran, not that no arm is blind. Both figures state the flag so
    neither reading can be quoted without it, and
    ``test_ac3_the_flag_off_reading_on_a_child_spawning_target_is_the_bound``
    measures the cell-for-cell difference the two settings produce.
    """

    selection: Sequence[str]
    repo_root: Path
    child_instrumentation: bool = False
    env: Mapping[str, str] = field(default_factory=dict)
    _workdir: Path | None = None

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root)
        self._refuse_if_lock_held()
        self.target = self._resolve_selection()

    # -- refusals ----------------------------------------------------------

    def _refuse_if_lock_held(self) -> None:
        """Refuse while a **foreign** worktree holds the board's lock (G-2).

        The verdict is :func:`full_suite_lock.current_verdict`'s, taken whole
        and not re-assembled here. Identity is the worktree, not a pid, and the
        rule is that module's: *refuse a foreign lock, ignore its own*. An
        own-tree lock was never the hazard G-2 guards — that hazard is two
        *different* worktrees running heavy pytest at once, and a child pytest
        this instrument spawns inside its own tree is already serialised by
        being one process tree, which is why that child's own hook resolves the
        same tree and lets it through. The composition F-001 closed stays
        closed: a **foreign** lock still refuses the start, so this instrument
        can still never begin a run whose child the hook would kill.

        Checking *any* lock instead was F-001's fix overshooting, and it could
        only be seen from inside a gate: every full-suite gate holds this exact
        lock for its whole duration, so "stricter" meant the instrument could
        not run inside the gate that must certify it (23 reds, one cause).

        **The staleness window and the override come with the verdict, by
        choice:** this code runs inside a pytest the owner's own
        ``pytest_configure`` already admitted, so any extra strictness reds a
        suite the board deliberately decided to run — a foreign lock past
        :data:`~tests.full_suite_lock.STALE_SECONDS`, whose holder the board
        presumes gone, or an announced override — while any laxity would start
        a run whose child that same hook kills. One function, one answer, so
        the two agree structurally rather than as two copies that happen to
        match. Neither relaxation is silent: the owner's terminal-summary hook
        announces a stale lock walked past and an override used.
        """
        allowed, said = full_suite_lock.current_verdict()
        if allowed:
            return
        raise LockHeld(
            f"{board_lock_path()} names another worktree, which holds the "
            "board's full-suite lock. This instrument refuses to start and "
            f"never writes one.\n\n{said}"
        )

    def _resolve_selection(self) -> Path:
        """One target file, derived from the selection. Default-deny.

        **Declared bound:** exactly one file per run, so the matrix's domain is
        never ambiguous. A selection naming two files, a directory, or nothing
        is refused rather than interpreted.
        """
        if not self.selection:
            raise SelectionRefused(
                "empty selection: this instrument never runs the full suite"
            )
        files = []
        for item in self.selection:
            head = item.split("::", 1)[0]
            path = Path(head)
            if not path.is_absolute():
                path = self.repo_root / path
            if not path.is_file():
                raise SelectionRefused(
                    f"{item!r} does not name an existing file. A selection this "
                    "instrument cannot resolve to one file is a FAILURE, never a "
                    "silent pass, and a directory is not resolved at all"
                )
            if path not in files:
                files.append(path)
        if len(files) != 1:
            raise SelectionRefused(
                f"selection spans {len(files)} files: a matrix reports one "
                f"target, and {[str(f) for f in files]} is more than one"
            )
        return files[0]

    # -- backups, the only restore mechanism -------------------------------

    def _backup_registry(self, paths: Iterable[Path]) -> dict[Path, Path]:
        """``cp -p`` backups for every path a mutant edits.

        A seam on purpose: ``test_kill_matrix.py`` plants an **incomplete**
        registry here, which is the shape the leaked patch actually took — two
        of three mutated files restored, with the third outside the bookkeeping
        so no restore verification ever looked at it. The between-mutants
        SHIPPED re-run is what catches that, and the plant is how we know it
        can.
        """
        registry: dict[Path, Path] = {}
        for path in paths:
            backup = self.workdir / f"backup.{len(registry)}.{path.name}"
            subprocess.run(["cp", "-p", str(path), str(backup)], check=True)
            registry[path] = backup
        return registry

    def _restore(self, registry: Mapping[Path, Path]) -> None:
        """Restore from the ``cp -p`` backup, verified two ways. No git, ever.

        **Every** registered path is restored before any failure is raised, and
        the failures are then reported together. Raising from inside the loop
        skipped every path after the first failure, and the outer ``finally``'s
        second call failed at the same point — so the tail of the registry
        stayed mutated. Registry order is insertion order, target first, so in
        this card's own second anchor the file left edited would have been
        ``src/nonogram/db/session.py``, a tracked source file, with G-5
        forbidding a git restore.
        """
        failures: list[str] = []
        for path, backup in registry.items():
            try:
                subprocess.run(["cp", "-p", str(backup), str(path)], check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                failures.append(f"cp -p could not restore {path}: {exc}")
                continue
            failures.extend(self._verification_failures(path, backup))
        if failures:
            raise LeakedPatch(
                "; ".join(failures)
                + ". Every registered path was restored before this was raised"
            )

    def _verification_failures(self, path: Path, backup: Path) -> list[str]:
        """``diff -q`` **and** ``shasum -a 256``, neither of them skippable.

        A verification that could not run is a failure, not a pass: ``shasum``
        is an external binary, and where it is absent the ``check=True`` call
        used to leave the restore loop through the same door as a real
        mismatch, part-way through.

        **Each of the three arms has its own control**, because until they did,
        neutering *both* comparisons line-for-line (``!= 0 and 0``,
        ``!= len(digests)``) left every test of this card green: a ``cp -p``
        that put back the **wrong bytes** read as verified. The two calls being
        *present* was all that was pinned — by the argv equality in
        ``test_ac4_restoring_uses_cp_p_backups_and_no_git_command_anywhere`` —
        and presence is not catching. The controls plant a ``cp`` that reports
        success and copies nothing, which leaves a real mismatch for the
        verification to find:
        ``test_g5_a_restore_that_copied_nothing_is_caught_by_diff_q`` and
        ``..._is_caught_by_shasum_256`` assert one finding each over that one
        plant, ``..._fails_the_run_from_its_finally`` is the same plant through
        :meth:`Runner.run`'s own ``finally``, and
        ``test_g5_a_shasum_that_could_not_run_is_counted_as_a_failure`` narrows
        ``PATH`` until the binary is gone, with the restore succeeding, so the
        branch below is reached on its own terms.
        """
        said: list[str] = []
        diff = subprocess.run(
            ["diff", "-q", str(backup), str(path)], capture_output=True
        )
        if diff.returncode != 0:
            said.append(f"diff -q says {path} is not its backup")
        try:
            sums = subprocess.run(
                ["shasum", "-a", "256", str(backup), str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            said.append(
                f"shasum -a 256 could not verify {path} ({exc}): a verification "
                "that did not run is not a verification"
            )
        else:
            digests = {line.split()[0] for line in sums.stdout.splitlines()}
            if len(digests) != 1:
                said.append(f"shasum -a 256 says {path} is not its backup")
        return said

    @property
    def workdir(self) -> Path:
        """This run's temp tree: the ``cp -p`` backups, the generated plugin
        and one ``records-*`` directory per pytest invocation.

        Created on first use and removed by :meth:`_discard_workdir` when
        :meth:`run` returns, so a gate that calls this instrument repeatedly
        does not accumulate one tree per :class:`Runner` and one ``records-*``
        per reading in the machine-wide temp directory. **Declared bound:**
        only :meth:`run` ends a run, so a :class:`Runner` whose helpers are
        driven directly keeps its tree — the two tests that drive
        :meth:`_pytest` and :meth:`_backup_registry` without a run point
        ``_workdir`` at a directory pytest owns instead.
        """
        if self._workdir is None:
            self._workdir = Path(tempfile.mkdtemp(prefix="kill-matrix-"))
        return self._workdir

    def _discard_workdir(self) -> None:
        """Remove this run's temp tree. Never called when a restore failed.

        There the backup is the only intact copy of the file on disk, so the
        tree is kept and :meth:`run` names the directory in the exception.
        """
        if self._workdir is None:
            return
        shutil.rmtree(self._workdir, ignore_errors=True)
        self._workdir = None

    # -- running -----------------------------------------------------------

    def run(self, pass_: Pass, mutants: Sequence[Mutant] = ()) -> KillMatrix:
        """SHIPPED, then each mutant, with SHIPPED re-run **between** them.

        ``pass_`` is positional and has no default: a caller cannot obtain a
        figure without naming the domain it came from.
        """
        if not isinstance(pass_, Pass):
            raise TypeError("pass_ must be a Pass member; there is no default")
        pristine = self.target.read_text(encoding="utf-8")
        linenos = assert_linenos(pristine, str(self.target))
        collisions = sorted({l for l in linenos if linenos.count(l) > 1})
        if collisions:
            raise SelectionRefused(
                f"{self.target} has more than one assert on line(s) {collisions}: "
                "the matrix is keyed on a lineno, so two asserts sharing one are "
                "a shape it cannot attribute. Refused rather than collapsed into "
                "a single cell"
            )
        denominator = len(linenos)
        paths: list[Path] = [self.target]
        for mutant in mutants:
            for path in mutant.paths:
                if path not in paths:
                    paths.append(path)
        registry = self._backup_registry(paths)
        try:
            shipped = self._measure("SHIPPED", pass_, denominator, pristine)
            self._refuse_unless_clean(shipped, None, "before any mutant")
            measured: dict[str, Matrix] = {}
            between: dict[str, Matrix] = {}
            for mutant in mutants:
                self._apply(mutant, registry)
                try:
                    self._refuse_unless_topology_holds(
                        pristine, f"mutant {mutant.name}"
                    )
                    measured[mutant.name] = self._measure(
                        mutant.name, pass_, denominator, pristine
                    )
                finally:
                    self._restore(registry)
                check = self._measure(
                    f"SHIPPED after {mutant.name}", pass_, denominator, pristine
                )
                between[mutant.name] = check
                self._refuse_unless_clean(check, shipped, f"after {mutant.name}")
            return KillMatrix(
                target=self.target,
                pass_=pass_,
                denominator=denominator,
                shipped=shipped,
                mutants=measured,
                shipped_between=between,
                child_instrumentation=self.child_instrumentation,
            )
        finally:
            try:
                self._restore(registry)
            except LeakedPatch as exc:
                raise LeakedPatch(
                    f"{exc}. The cp -p backups are kept at {self.workdir} "
                    "rather than discarded: a restore that did not verify is "
                    "the one case where the backup is the only intact copy"
                ) from exc
            self._discard_workdir()

    def _refuse_unless_clean(
        self, matrix: Matrix, baseline: Matrix | None, when: str
    ) -> None:
        """A leaked patch and a real kill look identical, so SHIPPED is re-run.

        Not only at the start: **between** mutants, because the shape this
        caught in wave 50 was an earlier patch surviving into every later
        mutant.

        Three conditions, because a targeted selection legitimately leaves most
        of a file's asserts ``NOT-REACHED``: no cell may be ``FAIL``, at least
        one cell must have been **reached**, and once there is a baseline every
        cell must equal the baseline's cell for cell. The second is what catches
        a leak that *removes* coverage instead of reddening an arm.

        The reached condition is this gate's own job, not a new one: a SHIPPED
        that accounted for nothing is not a baseline whatever pytest exited
        with, and every mutant compared against it then "survives" every arm by
        construction. It cannot false-positive — a reading that reached no arm
        has no baseline to be — and the quantity is the one
        :meth:`KillMatrix.figure` already prints as ``0 FAIL of 0 reached``. It
        is deliberately *not* a rule about the exit code: ``exit 1`` with no
        ``FAIL`` cell is also what a kill outside the matrix's domain looks like
        (see the module docstring), and position cannot tell the two apart.
        """
        if matrix.failed:
            raise LeakedPatch(
                f"SHIPPED is not FAIL-free {when}: {matrix.figure()} — "
                f"FAIL {matrix.failed}. A leaked patch and a real kill look "
                "identical, so no later reading from this run is trustworthy"
            )
        reached = matrix.denominator - len(matrix.not_reached)
        if not reached:
            raise LeakedPatch(
                f"SHIPPED reached no assertion node {when}: {matrix.figure()} — "
                "a reading that accounts for nothing is not a baseline, and "
                "every mutant compared against it would survive every arm by "
                "construction. pytest's exit code cannot stand in for this: "
                "exit 1 with no FAIL cell is also a kill outside this matrix's "
                "domain of ast.Assert nodes"
            )
        if baseline is None:
            return
        moved = {
            lineno: (baseline.cells[lineno], cell)
            for lineno, cell in matrix.cells.items()
            if baseline.cells[lineno] != cell
        }
        if moved:
            raise LeakedPatch(
                f"SHIPPED does not reproduce its own baseline {when}: "
                f"{matrix.figure()} — moved cells {moved}. A leaked patch and a "
                "real kill look identical, so no later reading from this run is "
                "trustworthy"
            )

    def _refuse_unless_topology_holds(self, pristine: str, when: str) -> None:
        """The target's assert topology, re-derived from disk after ``_apply``.

        The matrix's keys are derived **once**, from the pristine source, and
        both ``cells`` and ``records`` are attributed through them. Until this
        check existed nothing ever looked at the file that actually ran, and
        three equal-line-count shapes went through:

        * an assert **moved** — its cell reads ``NOT-REACHED`` while the arm
          ran and failed, a genuine kill published as "never reached";
        * two asserts **swapped** — the lineno tuple is identical, so there is
          no off-key record anywhere and the misattribution is evidence-free:
          each cell carries the other arm's outcome;
        * two asserts **merged onto one line** — one cell for two nodes, plus a
          ``NOT-REACHED`` for a node that no longer exists. ``run`` refuses
          that collision on the pristine source and never re-checked it.

        It is a **no-op for a mutant that edits anything but the target**: the
        target is re-read either way, and a file nobody edited reproduces its
        own shapes. Running it unconditionally rather than on
        ``self.target in mutant.paths`` is deliberate — an edit that reaches
        the target through another spelling of its path is still an edit to it.
        """
        mutated = self.target.read_text(encoding="utf-8")
        try:
            after = assert_shapes(mutated, str(self.target))
        except SyntaxError as exc:
            raise MutantRefused(
                f"{when} left {self.target} unparsable ({exc}): the matrix has "
                "no keys at all, and the blank reading that follows is "
                "indistinguishable from a file that never ran"
            ) from exc
        before = assert_shapes(pristine, str(self.target))
        if after == before:
            return
        gone = [shape for shape in before if shape not in after]
        arrived = [shape for shape in after if shape not in before]
        raise MutantRefused(
            f"{when} moved the target's assert topology. The matrix is keyed on "
            f"the pristine linenos, so {gone} would be reported NOT-REACHED "
            f"while {arrived} ran under cells that are not theirs. Equal line "
            "counts are not enough: an assert may not move to another line, "
            "swap with another, or share a line. Substitute what the assertion "
            "reads, not the assertion"
        )

    def _apply(self, mutant: Mutant, registry: Mapping[Path, Path]) -> None:
        """Apply every edit, with each path's content read from its backup.

        Reading from the backup rather than from disk is what makes a sequence
        of mutants independent of each other.
        """
        by_path: dict[Path, list[Edit]] = {}
        for edit in mutant.edits:
            by_path.setdefault(edit.path, []).append(edit)
        for path, edits in by_path.items():
            source_file = registry.get(path, path)
            source = source_file.read_text(encoding="utf-8")
            for edit in edits:
                source = apply_edit(source, edit)
            path.write_text(source, encoding="utf-8")

    def _measure(
        self, label: str, pass_: Pass, denominator: int, pristine: str
    ) -> Matrix:
        records, exit_code, output = self._pytest(pass_)
        if exit_code not in _RAN_EXIT_CODES:
            raise UnmeasuredRun(
                f"{label}: pytest exited {exit_code}, which is not a reading. "
                f"Only {sorted(_RAN_EXIT_CODES)} are — 0 all green, 1 tests ran "
                "and some failed. 2 is interrupted, 3 an internal error, 4 a "
                "usage error (a conftest hook refusing the run before "
                "collection, which is what the board's full-suite lock raises), "
                "5 nothing collected. The matrix this would publish is "
                "all-NOT-REACHED and FAIL-free, which is exactly the shape of a "
                "mutant every arm survived. Collected tests reported: "
                f"{collected_tests(output)}.\n--- pytest tail ---\n"
                f"{output[-2000:]}"
            )
        linenos = assert_linenos(pristine, str(self.target))
        off_key = sorted(set(records) - set(linenos))
        if off_key:
            raise MutantRefused(
                f"{label}: the run recorded assert lineno(s) {off_key} that the "
                "matrix has no cell for, so the file that ran is not the file "
                "the keys came from. Each such record is a real execution "
                "attributed to nothing, and the cells it should have filled "
                "read NOT-REACHED"
            )
        raw: dict[int, str] = {}
        for lineno in linenos:
            raw[lineno] = aggregate_any_red(records.get(lineno, []))
        cells = dict(raw)
        if pass_ is Pass.RECORDING and self.child_instrumentation:
            for lineno in child_dependent_linenos(pristine, str(self.target)):
                if cells.get(lineno) == PASS:
                    cells[lineno] = BLIND
        return Matrix(
            target=self.target,
            pass_=pass_,
            label=label,
            denominator=denominator,
            cells=cells,
            records={lineno: tuple(got) for lineno, got in records.items()},
            raw_cells=raw,
            collected_tests=collected_tests(output),
            exit_code=exit_code,
            child_instrumentation=self.child_instrumentation,
        )

    def _pytest(self, pass_: Pass):
        """One pytest, instrumented, with records read back per pid."""
        instrument_dir = str(Path(__file__).resolve().parent)
        plugin_dir = self.workdir / "plugin"
        plugin_dir.mkdir(exist_ok=True)
        (plugin_dir / "kill_matrix_plugin.py").write_text(
            _PLUGIN_SOURCE.format(
                instrument_dir=instrument_dir,
                env_target=_ENV_TARGET,
                env_record_dir=_ENV_RECORD_DIR,
                env_reraise=_ENV_RERAISE,
            ),
            encoding="utf-8",
        )
        record_dir = Path(tempfile.mkdtemp(prefix="records-", dir=self.workdir))
        env = {
            **os.environ,
            **self.env,
            _ENV_TARGET: str(self.target),
            _ENV_RECORD_DIR: str(record_dir),
            _ENV_RERAISE: "1" if pass_.reraise else "0",
            # A mutant edit is often byte-identical in length to the pristine
            # file and can land in the same mtime second as the reading before
            # it, at which point the .pyc that reading wrote still validates
            # and the next child imports a file that is no longer on disk.
            # Observed once here, as a single cell reading PASS where its re-run
            # read FAIL. No reading writes bytecode now, so no later reading can
            # read one written in the same second; a .pyc from before the run
            # predates every mutant's mtime and is invalidated normally.
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join(
                [str(plugin_dir), *filter(None, [os.environ.get("PYTHONPATH")])]
            ),
        }
        if self.child_instrumentation:
            env["PYTEST_ADDOPTS"] = " ".join(
                filter(None, [os.environ.get("PYTEST_ADDOPTS"), "-p kill_matrix_plugin"])
            )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "kill_matrix_plugin",
                "-p",
                "no:cacheprovider",
                *self.selection,
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            env=env,
            timeout=1800,
        )
        records: dict[int, list[bool]] = {}
        for jsonl in sorted(record_dir.glob("*.jsonl")):
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                lineno, ok = json.loads(line)
                records.setdefault(lineno, []).append(ok)
        return records, result.returncode, result.stdout + result.stderr
