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
   every later assert then reports ``NOT-REACHED``.

Safety discipline
-----------------
* Refuses to start if ``meta/kanban/.full-suite.lock`` exists under the repo
  root it is given, and never writes a lock anywhere.
* Takes a targeted selection resolving to exactly one existing file; refuses an
  empty selection, a directory, anything that is not an existing file, and a
  selection spanning more than one file.
* ``cp -p`` backups, every later edit's content read **from the backup**,
  restore in a ``finally`` verified with ``diff -q`` **and** ``shasum -a 256``.
  **No git command anywhere**, which ``test_kill_matrix.py`` enumerates from
  this module's own AST.
* Refuses an edit whose text names ``_refuse_unless_test_database`` or
  ``nonogram_poc``, and an edit to ``tests/conftest.py`` or
  ``tests/database_guard.py``. That is a path-and-text refusal, not an analysis
  of what an edit would do: it is the set of sites that carry the guard today.
* Takes no timing measurements and reports none. The ``timeout=`` passed to
  ``subprocess.run`` is a bound on a hung child, not a measurement: nothing
  reads a clock and no figure here is a duration.

Stdlib only (``ast``, ``pathlib``, ``subprocess``, ``hashlib``, ``json``,
``os``, ``re``, ``sys``, ``tempfile``) — no new runtime dependency.
"""

from __future__ import annotations

import ast
import enum
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

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
    "aggregate_any_red",
    "aggregate_last_write_wins",
    "assert_linenos",
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
_FORBIDDEN_TEXT = ("_refuse_unless_test_database", "nonogram_poc")
_FORBIDDEN_PATHS = (("tests", "conftest.py"), ("tests", "database_guard.py"))


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
    """SHIPPED did not come back all-PASS, so an earlier patch is still on disk."""


class SelectionRefused(Exception):
    """A selection this instrument will not run (empty, not a file, or the suite)."""


class LockHeld(Exception):
    """The board's full-suite lock exists; another worktree owns the host."""


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
        parts = self.path.parts
        for forbidden in _FORBIDDEN_PATHS:
            if parts[-len(forbidden) :] == forbidden:
                raise MutantRefused(
                    f"refusing an edit to {'/'.join(forbidden)}: it carries the "
                    "database guard"
                )


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
        """The only sentence this class prints, and it carries both.

        Domain: which pass. Denominator: assertion nodes, named as such. There
        is no shorter accessor that omits either, and no ``__str__`` that does.
        """
        counts = ", ".join(
            f"{len(self.of(outcome))} {outcome}"
            for outcome in (PASS, FAIL, NOT_REACHED, BLIND)
        )
        return (
            f"{self.label} / {self.pass_.value} pass over {self.target.name}: "
            f"{counts} of {self.denominator} assertion nodes"
            f" (collected tests: {self.collected_tests})"
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

    def cell(self, mutant: str, lineno: int) -> str:
        return self.mutants[mutant].cells[lineno]

    def figure(self) -> str:
        """Carries the pass, the denominator and its domain, unconditionally."""
        return (
            f"{len(self.mutants)} mutants / {self.pass_.value} pass over "
            f"{self.target.name}: {self.denominator} assertion nodes "
            f"(ast.Assert node count, not a collected test count); "
            f"SHIPPED {len(self.shipped.failed)} FAIL"
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

    Refuses to start while the board's real full-suite lock exists (G-2), never
    writes one, and never runs the full suite: the selection must be non-empty
    and every item must name an existing file (G-1).

    ``child_instrumentation`` decides whether a pytest the target *spawns*
    inherits the instrumentation. Default **off**, because turning it on
    perturbs the target's own subprocess harness. With it **on**, the recording
    pass's suppression crosses the process boundary and the arms
    :func:`child_dependent_linenos` names are reported ``BLIND``: the child
    swallows its own ``AssertionError``, reports a pass with exit 0, and the
    parent's premise would otherwise record ``PASS`` by construction. With it
    **off** the child is pristine, propagation is intact, and those arms are
    measured for real — which is why the ``BLIND`` overlay is applied only when
    it is on.
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
        lock = self.repo_root / "meta" / "kanban" / ".full-suite.lock"
        if lock.exists():
            raise LockHeld(
                f"{lock} exists: another worktree holds the board's full-suite "
                "lock. This instrument refuses to start and never writes one"
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
        """Restore from the ``cp -p`` backup, verified two ways. No git, ever."""
        for path, backup in registry.items():
            subprocess.run(["cp", "-p", str(backup), str(path)], check=True)
            diff = subprocess.run(
                ["diff", "-q", str(backup), str(path)], capture_output=True
            )
            if diff.returncode != 0:
                raise LeakedPatch(f"diff -q says {path} is not its backup")
            sums = subprocess.run(
                ["shasum", "-a", "256", str(backup), str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
            digests = {line.split()[0] for line in sums.stdout.splitlines()}
            if len(digests) != 1:
                raise LeakedPatch(f"shasum -a 256 says {path} is not its backup")

    @property
    def workdir(self) -> Path:
        if self._workdir is None:
            self._workdir = Path(tempfile.mkdtemp(prefix="kill-matrix-"))
        return self._workdir

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
            )
        finally:
            self._restore(registry)

    def _refuse_unless_clean(
        self, matrix: Matrix, baseline: Matrix | None, when: str
    ) -> None:
        """A leaked patch and a real kill look identical, so SHIPPED is re-run.

        Not only at the start: **between** mutants, because the shape this
        caught in wave 50 was an earlier patch surviving into every later
        mutant.

        Two conditions, because a targeted selection legitimately leaves most
        of a file's asserts ``NOT-REACHED``: no cell may be ``FAIL``, and once
        there is a baseline every cell must equal the baseline's cell for cell.
        The second is what catches a leak that *removes* coverage instead of
        reddening an arm.
        """
        if matrix.failed:
            raise LeakedPatch(
                f"SHIPPED is not FAIL-free {when}: {matrix.figure()} — "
                f"FAIL {matrix.failed}. A leaked patch and a real kill look "
                "identical, so no later reading from this run is trustworthy"
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
        raw: dict[int, str] = {}
        for lineno in assert_linenos(pristine, str(self.target)):
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
