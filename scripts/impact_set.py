#!/usr/bin/env python3
"""Derive the per-cycle test selection for `make test-impact`.

Why this exists
---------------
`meta/kanban/config.yml` sets ``review.test_scope: impact``. The forge skill's
``python-pro`` recipe narrows only with ``pytest-testmon`` installed and
otherwise does **no** narrowing at all -- it falls back to the full suite while
the gate note claims to be scoped. ``pytest-testmon`` is not in this venv, and
``cmd-start-review`` prefers a harness ``make test-impact`` target over its own
inline recipes ("one source of truth"), so this script is what makes the config
value mean something.

The reason the config flipped is not that the suite got slow. It is that
``full`` is **unreachable** at this board's concurrency: a full-suite gate takes
``meta/kanban/.full-suite.lock``, CARD-255's guard raises ``pytest.UsageError``
on a foreign holder, and so one card's full gate reds every pytest run a sibling
card's agent makes in its own worktree. With two cards live, whichever gates
first breaks the other.

What this script claims, and what it does not
---------------------------------------------
It claims only this: **for the changed paths it was given, the selection it
prints is a superset of the tests those paths can affect through an import edge
or a tree scan that this script can see.** It does not claim to be minimal, and
it does not claim completeness over couplings it cannot see -- a test that
reaches a module through a helper's re-export, or builds the module name at run
time from pieces, is invisible to both of the analyses below.

That bound is why the selection is a *cycle* gate and not the definition of
done. The full suite still runs at the merge gate, which is the backstop that
makes narrowing safe.

It fails CLOSED. Every path below that cannot be analysed returns ``FULL``,
which the Makefile turns into the whole suite. That is ADR-0039/R2's shape
applied to a selector rather than to a guard: *a shape it cannot analyse is a
FAILURE, never a silent pass.* A selector that guesses narrow is worse than no
selector, because its output looks like evidence.

The always-on set is DERIVED, not listed
----------------------------------------
22 test files in this suite scan the tracked tree (``git ls-files``,
``git grep``, ``rglob``) rather than importing the code they judge, which is
2749 of the suite's 8745 collected tests -- about 31%. Any tracked change at all
can red one of them. Two such reds have already been caused by prose: a
``backlog.md`` entry and a ``dispatcher.state`` note, each naming an environment
switch outside CARD-255's exempt prefixes.

So those files are included unconditionally for any non-empty change -- and the
set is **derived by scanning for the idioms**, never written down here. A
hard-coded list of 22 paths is exactly the defect this board keeps finding: the
23rd scanning test would be invisible to it, silently, and the selector would
report a narrowed run that had stopped covering the guards. If the derivation
finds nothing, that is a FAILURE too, not an empty set.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import warnings
import sys
from pathlib import Path

#: The sentinel the Makefile reads as "no narrowing -- run everything".
FULL = "FULL"

#: Changes whose blast radius this script does not model. Each one returns FULL.
#:
#: * ``tests/conftest.py`` -- every test in the suite depends on it, so there is
#:   no narrowing to do. (A docstring-only change to it narrows in principle;
#:   deciding that here would mean parsing intent, so it does not.)
#: * the dependency manifest and build config -- the skill's own rule.
#: * ``migrations/**`` -- ordering is global and merged order is what runs.
#: * this script and the Makefile that calls it -- a selector must not be
#:   allowed to narrow the run that would catch its own breakage.
UNANALYSABLE = (
    "tests/conftest.py",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "uv.lock",
    "poetry.lock",
    "Makefile",
    "scripts/impact_set.py",
)

#: Directory prefixes this script knows how to reason about. A changed path
#: under none of them returns FULL rather than being ignored: "I do not know
#: what this is" and "this affects nothing" are different answers, and only one
#: of them is safe.
KNOWN_ROOTS = ("src/", "tests/", "meta/", "docs/", "scripts/", "migrations/")

#: Source idioms that mean "this test reads the tree rather than importing it".
#: Matched against file text, because that is the authority available here: the
#: call shapes vary (``subprocess.run(["git", "ls-files"])``, a helper that
#: wraps it, ``Path.rglob``), and a narrower AST match would miss the wrappers
#: and report a smaller always-on set -- failing open.
SCAN_IDIOMS = (
    re.compile(r"""ls-files"""),
    re.compile(r"""git["']\s*,\s*["']grep"""),
    re.compile(r"""\.rglob\("""),
    re.compile(r"""os\.walk\("""),
)


def repo_root() -> Path:
    """The working tree this script is being run against."""
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(out.stdout.strip())


def test_files(root: Path) -> list[Path]:
    """Every collectible test file, as repo-relative paths.

    ``pyproject.toml`` sets ``testpaths = ["tests"]``, so that is the authority
    for where tests live; the glob mirrors pytest's own default naming.
    """
    found = sorted(
        p for p in (root / "tests").rglob("test_*.py") if "__pycache__" not in p.parts
    )
    return [p.relative_to(root) for p in found]


def always_on(root: Path) -> list[Path]:
    """The tree-scanning tests, derived by scanning for the idioms.

    Never a written-down list -- see the module docstring. An empty result is a
    failure of the derivation, not a true empty set, and the caller treats it
    as FULL.
    """
    out = []
    for rel in test_files(root):
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            # Unreadable file: cannot establish it is NOT a scanner.
            out.append(rel)
            continue
        if any(idiom.search(text) for idiom in SCAN_IDIOMS):
            out.append(rel)
    return out


def module_name_for(path: str) -> str | None:
    """``src/nonogram/db/session.py`` -> ``nonogram.db.session``."""
    if not path.startswith("src/") or not path.endswith(".py"):
        return None
    dotted = path[len("src/") : -len(".py")].replace("/", ".")
    return dotted[: -len(".__init__")] if dotted.endswith(".__init__") else dotted


def tests_module_name_for(path: str) -> str | None:
    """``tests/kill_matrix.py`` -> ``tests.kill_matrix`` (a test helper)."""
    if not path.startswith("tests/") or not path.endswith(".py"):
        return None
    name = Path(path).name
    if name.startswith("test_") or name == "conftest.py":
        return None
    dotted = path[: -len(".py")].replace("/", ".")
    return dotted[: -len(".__init__")] if dotted.endswith(".__init__") else dotted


def imported_names(root: Path, rel: Path) -> tuple[set[str], set[str]]:
    """What a file imports, as ``(named, bound_packages)``.

    The split is the whole correctness of this script, and getting it wrong in
    the generous direction was measured here before it was fixed: treating a
    bare package name as reach for *any* submodule selected 65 extra test files
    for one change to ``nonogram/db/session.py``, because 65 files say
    ``from nonogram import ...``. That form binds the **member**, not the
    package, so it gives no attribute path to a sibling submodule. The two sets
    therefore mean different things:

    ``named``
        modules this file imports directly. ``from A.B import C`` names ``A.B``
        and ``A.B.C``; ``import A.B.C`` names ``A.B.C``. A change to a named
        module affects this file.
    ``bound_packages``
        whatever is bound as an *object*, because an object that happens to be
        a package makes its whole subtree reachable by attribute access, which
        this script cannot follow and so must assume the worst about. Which
        name gets bound is the part that matters, and it differs per form:
        ``import A.B`` binds ``A`` (so the conservative answer is ``A``);
        ``import A.B as x`` binds exactly ``A.B``; and ``from A import B``
        binds ``A.B`` whatever it is called afterwards. That last form is why
        ``from nonogram import db`` followed by ``db.session`` is reach while
        ``from nonogram import errors`` is not -- the distinction the measured
        65-file over-selection came from getting wrong in both directions at
        once.

    Both are unioned with the file's dotted string literals, because
    ``importlib.import_module("nonogram.x")`` and ``monkeypatch.setattr``
    targets are real import edges the AST cannot see as imports.
    """
    try:
        text = (root / rel).read_text(encoding="utf-8")
    except OSError:
        return set(), set()

    named: set[str] = set()
    bound: set[str] = set()
    try:
        # SyntaxWarning is suppressed only for OUR parse, not for the suite's.
        # `src/nonogram/sourcing/templates/dog_in_house.py` carries an invalid
        # escape (`"\,"`), so parsing the tree emits that warning once per src
        # file scanned -- noise in every gate, for a defect this script neither
        # caused nor should hide from the suite. It is in the backlog instead.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text)
    except SyntaxError:
        # Unparseable: dotted strings only. The caller's fail-closed path
        # covers what that misses.
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    named.add(alias.name)
                    # `import A.B` binds `A`; `import A.B as x` binds `A.B`.
                    bound.add(
                        alias.name if alias.asname else alias.name.split(".")[0]
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                named.add(node.module)
                for alias in node.names:
                    dotted = f"{node.module}.{alias.name}"
                    named.add(dotted)
                    # `from A import B` binds the object A.B, under whatever
                    # name; if it is a package, A.B.* is reachable.
                    bound.add(dotted)

    named.update(re.findall(r"\b(?:nonogram|tests)(?:\.[A-Za-z_][A-Za-z0-9_]*)+", text))
    return named, bound


def src_import_graph(root: Path) -> dict[str, set[str]]:
    """``module -> the nonogram modules it imports``, over ``src/`` only.

    This is the half the first draft of this script simply did not have, and
    its absence was the real unsoundness: a test that imports
    ``nonogram.orchestrator`` is affected by a change to a module the
    orchestrator imports, while naming nothing but the orchestrator. Selecting
    on the test files' own imports alone fails **open** for every such edge.

    The forge skill's warning that "import-graph heuristics on Python are not
    trustworthy enough to gate on" is why the result is used only to *widen*
    the selection, never to narrow it below what the named edges already give,
    and why every unresolved shape still returns FULL upstream.
    """
    graph: dict[str, set[str]] = {}
    for path in sorted((root / "src").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        module = module_name_for(rel)
        if module is None:
            continue
        named, _ = imported_names(root, Path(rel))
        graph[module] = {n for n in named if n.split(".")[0] == "nonogram"}
    return graph


def modules_reaching(graph: dict[str, set[str]], module: str) -> set[str]:
    """``module`` plus every src module that transitively imports it."""
    reaching = {module}
    changed = True
    while changed:
        changed = False
        for src, imports in graph.items():
            if src in reaching:
                continue
            if any(target in reaching for target in imports):
                reaching.add(src)
                changed = True
    return reaching


def reaches(imported: tuple[set[str], set[str]], targets: set[str]) -> bool:
    """Does a file importing ``imported`` reach any module in ``targets``?

    Two ways, and only two: it names one of them, or it has a package bound as
    an object whose subtree contains one. ``targets`` is the changed module
    together with everything that transitively imports it
    (:func:`modules_reaching`).
    """
    named, bound = imported
    if named & targets:
        return True
    for pkg in bound:
        prefix = pkg + "."
        if any(t == pkg or t.startswith(prefix) for t in targets):
            return True
    return False


def select(root: Path, changed: list[str]) -> list[str] | str:
    """The selection for ``changed``, or :data:`FULL`.

    Returns FULL rather than a narrowed set whenever a changed path is one this
    script does not model, or when a changed code file has no visible importer
    -- an unimported module is not an unaffecting one, it is a coupling this
    script cannot see.
    """
    changed = [c for c in changed if c]
    if not changed:
        return []

    for path in changed:
        if path in UNANALYSABLE:
            return FULL
        if not path.startswith(KNOWN_ROOTS):
            return FULL

    scanners = always_on(root)
    if not scanners:
        # The derivation found no tree-scanning test. On this suite that is
        # false, so the derivation is broken -- never a licence to narrow.
        return FULL

    selected: set[Path] = set(scanners)
    all_tests = test_files(root)
    # Imports are read once per test file, not once per changed path.
    imports = {rel: imported_names(root, rel) for rel in all_tests}
    graph = src_import_graph(root)

    for path in changed:
        rel = Path(path)

        # A changed test file runs itself.
        if path.startswith("tests/") and rel.name.startswith("test_"):
            if (root / rel).exists():
                selected.add(rel)
            continue

        module = module_name_for(path) or tests_module_name_for(path)
        if module is None:
            # Prose, data, a shell script, a migration's neighbour: it changes
            # no import edge, and the always-on scanners already cover the
            # tracked-tree guards that DO read it. (This is the path that the
            # backlog.md and dispatcher.state reds took.)
            continue

        # The changed module, plus every src module that transitively imports
        # it -- so a test naming only a façade is still selected.
        targets = modules_reaching(graph, module) if module.startswith("nonogram") else {module}
        importers = [rel_t for rel_t in all_tests if reaches(imports[rel_t], targets)]
        if not importers:
            return FULL
        selected.update(importers)

    return sorted(str(p) for p in selected)


def changed_from_git(root: Path, base: str) -> list[str]:
    """Paths changed against ``base``: committed, staged, unstaged and new.

    The last of those is the one worth explaining. ``git diff`` does not list
    **untracked** files, so a card that adds a new test file and has not
    committed it yet would get a selection that silently omits the very test it
    just wrote -- failing *open*, which is the one direction this script must
    never fail. So new files are collected too.

    They are collected **only under ``src/`` and ``tests/``**, and that is not
    tidiness. This repo carries a large standing untracked set belonging to its
    owner (rendered PDFs, picture corpora) at the top level; sweeping those in
    would put paths outside :data:`KNOWN_ROOTS` into every changed set and so
    return FULL every time, which is safe and useless. Narrowing the sweep to
    the two code roots keeps the fail-closed property where it earns something
    and leaves the owner's working files alone.

    Honest bound: a new file added outside those two roots is invisible here.
    The scanners in the always-on set are what read the rest of the tree.
    """
    names: set[str] = set()
    commands = (
        ["diff", "--name-only", base],   # committed on this branch
        ["diff", "--name-only"],          # unstaged edits to tracked files
        ["diff", "--name-only", "--cached"],  # staged edits
        ["ls-files", "--others", "--exclude-standard", "--", "src", "tests"],
    )
    for args in commands:
        out = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        )
        names.update(line for line in out.stdout.splitlines() if line.strip())
    return sorted(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive the test selection for a changed set. Prints one "
        "path per line, or the single token FULL."
    )
    parser.add_argument(
        "--base", help="git revision to diff against (e.g. the merge-base)"
    )
    parser.add_argument("files", nargs="*", help="changed paths, repo-relative")
    args = parser.parse_args(argv)

    root = repo_root()
    if args.base:
        changed = changed_from_git(root, args.base) + list(args.files)
    else:
        changed = list(args.files)

    result = select(root, changed)
    if result == FULL:
        print(FULL)
    else:
        for path in result:
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
