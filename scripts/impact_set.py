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

**Since CARD-286 (owner ruling 2026-11-06) the merge gate runs this derivation
too**: the impact selection plus the always-on set, with the full suite at wave
close and whenever the answer is ``FULL``. That moved the script from advisory
to load-bearing, so the couplings an import edge cannot carry are derived here
rather than left to the backstop: a static asset is read by the tests that
name it or declare its selectors, and by the browser tests that reach a page
linking it; a test file is read by the tests that import it, name it, match it
by glob, or census the tests tree; a relative import is an edge. Anything
still underivable returns ``FULL`` *with the path and the rule*.

The gate invocation (one pasteable block)::

    python scripts/impact_set.py --gate --against main

The repository's Makefile carries ``test-impact`` / ``impact-set`` targets that
call this script in its plain mode; the script is the single source of truth and
the Makefile only reads its stdout (``FULL`` or one path per line, exit 0 --
that contract is unchanged).

``--gate`` prints the answer, the selection's size against the full suite's
collected count (derived by ``pytest --collect-only``, never carried) and, when
``FULL``, the path and rule that caused it. Its exit code branches:

* ``0``  -- a SELECTION, with both counts collected: run those files.
* ``10`` -- FULL: run the whole suite.
* ``11`` -- the count could not be collected (a collection error, a held
  full-suite lock, a selection that collects 0 tests). Treated as FULL: a
  selection nobody could size is not vouched for.
* ``12`` -- EMPTY: no changed path. Not a pass; a failed diff looks like this.

Run it with NO full-suite lock held: the collection is a pytest run.

Not modelled (declared, so nobody reads silence as coverage): a test that
builds the path of an asset from pieces (``STATIC / f"{stem}{ext}"``,
``os.path.join(..., "solver" + ".js")``) is invisible to the name rule and is
caught only by a declared selector, a directory walk or the browser-wide rule
for admin statics; merge-order effects (main moved after the branch);
behavioural coupling through JSON field names; frozen cross-card censuses
beyond the tree-scanning tests (the wave-close full run owns those).

It fails CLOSED. Every path below that cannot be analysed returns ``FULL``,
which the caller reads as the whole suite. That is ADR-0039/R2's shape
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
import fnmatch
import re
import subprocess
import warnings
import sys
from pathlib import Path
from typing import NamedTuple

#: The sentinel a caller reads as "no narrowing -- run everything".
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


def _absolute_module(rel: Path, node: ast.ImportFrom) -> str | None:
    """The dotted module a ``from ... import`` names, resolving relative forms.

    ``from .session import X`` inside ``src/nonogram/db/__init__.py`` is an
    edge to ``nonogram.db.session``. Before CARD-286 this read ``node.module``
    alone, so the edge was ``session`` -- a name no test imports -- and a test
    that does ``from nonogram.db import get_session`` was not selected for a
    change to ``session.py``: a fail-OPEN hole, five relative imports wide.
    """
    if not node.level:
        return node.module
    parts = list(rel.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    package = parts[:-1]  # the directory is the package, __init__ or not
    if node.level - 1 > len(package):
        return None
    package = package[: len(package) - (node.level - 1)]
    if node.module:
        package = package + node.module.split(".")
    return ".".join(package) or None


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
            elif isinstance(node, ast.ImportFrom):
                module = _absolute_module(rel, node)
                if not module:
                    continue
                named.add(module)
                for alias in node.names:
                    dotted = f"{module}.{alias.name}"
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


def modules_reaching_any(graph: dict[str, set[str]], seeds: set[str]) -> set[str]:
    """:func:`modules_reaching` for many seeds at once, in one reverse sweep."""
    importers_of: dict[str, set[str]] = {}
    for src, imports in graph.items():
        for target in imports:
            importers_of.setdefault(target, set()).add(src)
    reaching = set(seeds)
    frontier = list(seeds)
    while frontier:
        for importer in importers_of.get(frontier.pop(), ()):
            if importer not in reaching:
                reaching.add(importer)
                frontier.append(importer)
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


# ---------------------------------------------------------------------------
# CARD-286: the couplings an import edge cannot carry.
# ---------------------------------------------------------------------------

#: What a tree-WALKING test looks like when the walk is a ``glob`` / ``iterdir``
#: rather than one of :data:`SCAN_IDIOMS`. These are NOT always-on (twenty-odd
#: tests glob their own tmp dirs); they are selected only when a changed path
#: lies under a root the test also names -- see :func:`_tree_readers`.
WALK_IDIOMS = (
    re.compile(r"""\.glob\("""),
    re.compile(r"""iterdir\("""),
    re.compile(r"""listdir\("""),
    re.compile(r"""scandir\("""),
    re.compile(r"""glob\.glob\("""),
)

#: A test that censuses COLLECTION (a ``--collect-only`` child, or the API). It
#: reaches the tests tree through a subprocess, so no import edge exists, and a
#: name-based rule cannot see it either when the family is globbed. CARD-271's
#: merge gate went red on exactly this shape.
COLLECTION_IDIOMS = (
    re.compile(r"""--collect-only"""),
    re.compile(r"""collect_only"""),
)

#: What it means to EXECUTE a stylesheet or a script: something has to run a
#: browser (or node). Reaching the page that links the asset is not enough; a
#: test that renders HTML in Python and asserts on the string cannot be changed
#: by the asset's content.
EXECUTOR_IDIOMS = (
    re.compile(r"""playwright"""),
    re.compile(r"""browser_page"""),
    re.compile(r"""chromium"""),
    re.compile(r"""selenium"""),
    re.compile(r"""["']node["']"""),
)

#: Every non-Python file shipped under ``src/`` has a rule, keyed by
#: :func:`asset_key` (the suffix, or the file name when there is none). The
#: table is asserted EQUAL to the shipped types by
#: ``TestImpactSet_EveryShippedAssetHasADerivation``: a new type fails the
#: suite instead of joining the silent class, and so does a rule for nothing.
#:
#: Kinds (see :data:`ASSET_KINDS`):
#:
#: * ``executed`` -- run by a browser. Readers: tests that name the file, tests
#:   that name a selector it declares, and the executor tests that reach a
#:   module rendering a page that links it.
#: * ``template`` -- rendered by Python. Readers: tests that name it, and every
#:   test reaching a module that names it (through ``include``/``extends``).
#: * ``named`` -- read as data or bytes. Readers: tests that name it.
#: * ``inert`` -- OS litter; no reader can exist. Only the scanners apply.
ASSET_RULES = {
    ".css": "executed",
    ".js": "executed",
    ".html": "template",
    ".ttf": "named",
    ".txt": "named",
    "LICENSE": "named",
    "PKG-INFO": "named",
    ".DS_Store": "inert",
}
ASSET_KINDS = ("executed", "template", "named", "inert")

#: Suffixes whose readers can be derived even OUTSIDE :data:`KNOWN_ROOTS` -- the
#: repo-root ``player/`` site is the case. G-6 keeps the roots closed; what
#: changes is that a stylesheet, script, page or Python file there is no longer
#: refused for its location alone but analysed like its ``src/`` twin, and still
#: ends in FULL (naming the path and the rule) when nobody reads it. A root-level
#: ``.md`` / ``.ini`` / ``.db`` is NOT here: ``ONLINE_GAME_SPECIFICATION.md``
#: stays FULL.
OUTSIDE_ROOT_DERIVABLE = (".css", ".js", ".html", ".py")

#: Tracked probe scripts and measurement records. Nothing ships from them and a
#: test reads one only by naming it, so they are NAMED, never forced to FULL:
#: a test naming the file is selected, the always-on scanners cover the tracked
#: tree, and an unread one adds nothing. Measured over 50 merges, 11 of the 19
#: FULL answers were only a card committing a probe script here.
INSTRUMENT_ROOTS = ("scratchpad/", "meta/profiling/")

#: Modules whose change reaches every browser test, not only the ones that
#: import them: the Flask app serves every page a browser test drives, and a
#: test can get the app from a helper test module, a fixture or a subprocess.
BROWSER_SURFACE_MODULES = ("nonogram.admin.app",)

#: Exit codes of ``--gate`` (the plain mode always exits 0 so the Makefile's
#: stdout contract -- ``FULL`` or paths -- is unchanged).
EXIT_SELECTION = 0      # a selection, with a collected count to vouch for it
EXIT_FULL = 10          # run the whole suite
EXIT_COUNT_FAILED = 11  # the count could not be collected: treated as FULL
EXIT_EMPTY = 12         # no changed path: NOT a pass, check the diff base

#: The rule ids a ``FULL`` reason carries.
RULE_UNANALYSABLE = "unanalysable"
RULE_OUTSIDE_ROOTS = "outside-known-roots"
RULE_MIGRATIONS = "migrations"
RULE_CONFTEST = "conftest"
RULE_CONFTEST_CLOSURE = "conftest-closure"
RULE_COUNT_UNAVAILABLE = "count-unavailable"
RULE_NO_SCANNERS = "no-scanners"
RULE_NO_IMPORTER = "no-importer"
RULE_NO_READER = "no-reader"
RULE_UNKNOWN_ASSET = "unknown-asset-type"


class Reason(NamedTuple):
    """Why an answer is ``FULL``: the path, the rule that fired, and the detail."""

    path: str
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path} -- rule {self.rule}: {self.detail}"


class Derivation:
    """The verdict. ``full`` and ``files`` are exclusive: a FULL carries no list.

    A plain class, not a dataclass: the tests load this file by path without
    registering it in ``sys.modules``, which dataclasses require.
    """

    def __init__(
        self,
        files: list[str] | None = None,
        full: bool = False,
        reasons: list[Reason] | None = None,
        empty: bool = False,
    ):
        self.files = files if files is not None else []
        self.full = full
        self.reasons = reasons if reasons is not None else []
        self.empty = empty  # no changed path at all: a fact about the diff, not a pass


def asset_key(path: str) -> str:
    """``admin/static/a.css`` -> ``.css``; ``fonts/LICENSE`` -> ``LICENSE``."""
    p = Path(path)
    return p.suffix or p.name


def _read(root: Path, rel: Path | str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _read_strict(root: Path, rel: Path | str) -> str | None:
    """The text, or ``None`` when the file cannot be read at all."""
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _tests_dotted(path: str) -> str | None:
    """``tests/helpers/x.py`` -> ``tests.helpers.x`` for ANY py under tests/."""
    if not path.startswith("tests/") or not path.endswith(".py"):
        return None
    dotted = path[: -len(".py")].replace("/", ".")
    return dotted[: -len(".__init__")] if dotted.endswith(".__init__") else dotted


class _Names:
    """Does a text name ``path``? Either as the repo-relative path, or as the
    base name when it has a suffix (a test builds ``STATIC / "solver.js"`` from
    pieces, so the full path never appears), or as ``parent/name`` for
    suffix-less and ``__init__`` files. The lookbehind stops ``solver.js``
    matching inside ``mysolver.js`` and ``solver_state.js``.

    A plain substring test runs first: it is the fast reject for the ~99% of
    files that do not name the path, and the regex only confirms the boundary
    on the few that do (measured: 8 s a derivation with the regex alone).
    """

    def __init__(self, path: str):
        p = Path(path)
        forms = {path}
        if p.suffix and p.name != "__init__.py":
            forms.add(p.name)
        else:
            forms.add(f"{p.parent.name}/{p.name}")
        self.forms = sorted(forms, key=len, reverse=True)
        self.regex = re.compile(
            r"(?<![\w.-])(?:" + "|".join(re.escape(f) for f in self.forms) + r")(?![\w])"
        )

    def search(self, text: str):
        if not any(f in text for f in self.forms):
            return None
        return self.regex.search(text)


def _name_pattern(path: str) -> _Names:
    return _Names(path)


def _identifiers(path: str, text: str) -> set[str]:
    """Selectors/identifiers an asset DECLARES, for matching against test text.

    Only compound names (a dash or underscore) are taken for a stylesheet, and
    only dashed string literals for a script: a bare ``card`` or ``row`` would
    name nearly every test, and a JSON key like ``difficulty_tier`` is a server
    field, not a DOM name. Measured on this tree: admin.css declares 334
    compound names and 54 test files name one.
    """
    out: set[str] = set()
    if path.endswith(".css"):
        t = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        out |= set(re.findall(r"(?<![\w-])\.([A-Za-z_][\w-]*)", t))
        out |= set(re.findall(r"#([A-Za-z_][\w-]*)\s*[{,.:>\[+~ ]", t))
        out |= set(re.findall(r"(--[A-Za-z][\w-]*)", t))
        return {i for i in out if "-" in i or "_" in i}
    if path.endswith(".js"):
        t = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        t = re.sub(r"(?m)^\s*//.*$", "", t)
        for lit in re.findall(r"""["'`]([^"'`\n]{1,120})["'`]""", t):
            out |= set(
                re.findall(
                    r"(?<![\w-])([A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)(?![\w-])", lit
                )
            )
    return out


class _Corpus:
    """Everything read once per derivation: texts, imports, both import graphs."""

    def __init__(self, root: Path):
        self.root = root
        self.tests = test_files(root)
        self.test_paths = [t.as_posix() for t in self.tests]
        self.sources = sorted(
            p.relative_to(root)
            for p in (root / "tests").rglob("*.py")
            if "__pycache__" not in p.parts
        )
        self.text: dict[Path, str] = {}
        self.unreadable: set[Path] = set()
        for s in self.sources:
            got = _read_strict(root, s)
            if got is None:
                self.unreadable.add(s)
            self.text[s] = got or ""
        self.imports = {s: imported_names(root, s) for s in self.sources}
        self.src_graph = src_import_graph(root)
        self.tests_graph: dict[str, set[str]] = {}
        for s in self.sources:
            dotted = _tests_dotted(s.as_posix())
            if dotted:
                named, _ = self.imports[s]
                self.tests_graph[dotted] = {
                    n for n in named if n.split(".")[0] in ("tests", "nonogram")
                }
        # ONE graph over src AND test modules, with every module importing its
        # ancestor packages (importing a.b.c runs a/__init__ and a/b/__init__).
        # A browser test that gets the app from `tests.test_puzzle_solver_page`
        # reaches the app only through this: the src-only graph never saw it.
        self.graph_all: dict[str, set[str]] = {m: set(v) for m, v in self.src_graph.items()}
        for m, v in self.tests_graph.items():
            self.graph_all.setdefault(m, set()).update(v)
        for module in list(self.graph_all):
            parts = module.split(".")
            for i in range(1, len(parts)):
                ancestor = ".".join(parts[:i])
                if ancestor in self.graph_all:
                    self.graph_all[module].add(ancestor)
        self._conftest: tuple[set[str], set[str]] | None = None
        self._fixture_users: set[Path] | None = None
        self._executors: set[Path] | None = None
        self._src_texts: list[tuple[Path, str]] | None = None
        self._token_cache: dict[Path, set[str]] = {}
        self._extra_texts: dict[str, list[tuple[Path, str]]] = {}
        self._loading: dict[str, list[tuple[Path, str]]] = {}
        self._tokens: dict[Path, list[str]] | None = None
        self._side: dict[str, dict[Path, str]] = {}

    def scanners(self) -> list[Path]:
        """The always-on set, from the texts already read (same idioms as
        :func:`always_on`, which stays the standalone entry point)."""
        return [
            t
            for t in self.tests
            if t in self.unreadable or any(i.search(self.text[t]) for i in SCAN_IDIOMS)
        ]

    def tokens(self, test: Path) -> set[str]:
        """Maximal ``[\\w-]`` runs in a test's text. Membership here is the same
        claim as a ``(?<![\\w-])name(?![\\w-])`` match, without trying a 300-way
        alternation at every offset of every file (measured: 9 s a derivation)."""
        if test not in self._token_cache:
            self._token_cache[test] = set(re.findall(r"[\w-]+", self.text[test]))
        return self._token_cache[test]

    def src_texts(self, extra: str | None = None) -> list[tuple[Path, str]]:
        if self._src_texts is None:
            self._src_texts = [(f, _read(self.root, f)) for f in _src_files(self.root)]
        if extra is None:
            return self._src_texts
        if extra not in self._extra_texts:
            self._extra_texts[extra] = [
                (f, _read(self.root, f)) for f in _src_files(self.root, (extra,))
            ]
        return self._src_texts + self._extra_texts[extra]

    def loading_texts(self, extra: str | None = None) -> list[tuple[Path, str]]:
        key = extra or ""
        if key not in self._loading:
            self._loading[key] = [
                (f, _loading_text(f.as_posix(), t)) for f, t in self.src_texts(extra)
            ]
        return self._loading[key]

    def dir_namers(self, top: str) -> set[Path]:
        """Tests whose text names the directory ``top`` as a path segment."""
        token = re.compile(rf"""["'/]{re.escape(top)}["'/]""")
        return {t for t in self.tests if token.search(self.text[t])}

    # -- who imports what ---------------------------------------------------

    def importers(self, src_modules: set[str], tests_modules: set[str]) -> set[Path]:
        """Test files reaching any of the modules, by import (transitively)."""
        targets = modules_reaching_any(self.graph_all, src_modules | tests_modules)
        return {t for t in self.tests if reaches(self.imports[t], targets)}

    # -- conftest ------------------------------------------------------------

    def conftest_closure(self) -> tuple[set[str], set[str]]:
        """``(test_modules, src_modules)`` that ``tests/conftest.py`` imports,
        transitively. Every test loads conftest, so a helper in the first set is
        a global dependency (FULL, like conftest) and a module in the second is
        one the fixtures it defines run against."""
        if self._conftest is None:
            seen: set[str] = set()
            frontier = ["tests.conftest"] if "tests.conftest" in self.graph_all else []
            while frontier:
                for target in self.graph_all.get(frontier.pop(), ()):
                    if target not in seen:
                        seen.add(target)
                        frontier.append(target)
            seen.discard("tests.conftest")
            self._conftest = (
                {m for m in seen if m.split(".")[0] == "tests"},
                {m for m in seen if m.split(".")[0] == "nonogram"},
            )
        return self._conftest

    def conftest_users(self) -> set[Path]:
        """Test files that use a fixture ``tests/conftest.py`` defines.

        By ast: a function parameter named like a fixture, or a string equal to
        one (``usefixtures``). Derived from the conftest itself, never listed.
        """
        if self._fixture_users is None:
            conftest = Path("tests/conftest.py")
            names: set[str] = set()
            if conftest in self.text:
                try:
                    tree = ast.parse(self.text[conftest])
                except SyntaxError:
                    tree = None
                for node in ast.walk(tree) if tree else ():
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                        "fixture" in ast.unparse(d) for d in node.decorator_list
                    ):
                        names.add(node.name)
            users: set[Path] = set()
            for t in self.tests:
                try:
                    tree = ast.parse(self.text[t])
                except SyntaxError:
                    users.add(t)  # cannot read its parameters: assume it uses them
                    continue
                # A name the file defines as its own fixture, or imports into its
                # namespace, shadows the conftest one for that file (pytest takes
                # the closest definition), so `app` as a local fixture is not a use.
                shadow: set[str] = set()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                        "fixture" in ast.unparse(d) for d in node.decorator_list
                    ):
                        shadow.add(node.name)
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        shadow.update((a.asname or a.name).split(".")[0] for a in node.names)
                wanted = names - shadow
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        a = node.args
                        args = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs}
                        if args & wanted:
                            users.add(t)
                            break
                    elif isinstance(node, ast.Constant) and node.value in wanted:
                        users.add(t)
                        break
            self._fixture_users = users
        return self._fixture_users

    # -- who names what -----------------------------------------------------

    def naming(self, path: str) -> set[Path]:
        """Test files whose text names ``path``, plus the tests importing a
        test-tree helper whose text names it (one reader behind a helper is
        still a reader)."""
        pattern = _name_pattern(path)
        hits: set[Path] = set()
        helper_modules: set[str] = set()
        for s in self.sources:
            if s.as_posix() == path or not pattern.search(self.text[s]):
                continue
            if s in self.tests:
                hits.add(s)
            dotted = _tests_dotted(s.as_posix())
            if dotted:
                helper_modules.add(dotted)
        if helper_modules:
            hits |= self.importers(set(), helper_modules)
        return hits

    def matching_by_glob_or_prefix(self, path: str) -> set[Path]:
        """Tests whose text carries a ``test_...`` name, glob or prefix that
        ``path`` matches -- how a family guard names a family it never imports."""
        if self._tokens is None:
            self._tokens = {
                t: re.findall(r"test_[A-Za-z0-9_*?\[\]]+(?:\.py)?", self.text[t])
                for t in self.tests
            }
        base = Path(path).name
        hits: set[Path] = set()
        for t, tokens in self._tokens.items():
            if t.as_posix() == path:
                continue
            for tok in tokens:
                if any(c in tok for c in "*?["):
                    glob = tok if tok.endswith(".py") else tok + "*"
                    ok = fnmatch.fnmatch(base, glob)
                elif tok.endswith(".py"):
                    ok = tok == base
                else:
                    ok = base.startswith(tok)
                if ok:
                    hits.add(t)
                    break
        return hits

    def tree_readers(self, root_name: str) -> set[Path]:
        """Tests that WALK the ``root_name`` tree without a scan idiom: a glob or
        listing that also names the root. Selected only for a change under it."""
        token = re.compile(rf"""["'/]{re.escape(root_name)}["'/]""")
        out = set()
        for t in self.tests:
            text = self.text[t]
            if token.search(text) and any(w.search(text) for w in WALK_IDIOMS):
                out.add(t)
            if root_name == "tests" and any(c.search(text) for c in COLLECTION_IDIOMS):
                out.add(t)
        return out

    # -- who executes what --------------------------------------------------

    def executors(self) -> set[Path]:
        """Tests that drive a browser (or node), directly or via a helper/fixture
        module they import. Derived by idiom, never listed."""
        if self._executors is None:
            seeds = {
                s
                for s in self.sources
                if any(i.search(self.text[s]) for i in EXECUTOR_IDIOMS)
            }
            modules = {d for s in seeds if (d := _tests_dotted(s.as_posix()))}
            found = {t for t in self.tests if t in seeds}
            found |= self.importers(set(), modules)
            self._executors = found
        return self._executors


def _src_files(root: Path, extra: tuple[str, ...] = ()) -> list[Path]:
    out = []
    for base in (("src", "scripts") if not extra else extra):
        for p in sorted((root / base).rglob("*")) if (root / base).is_dir() else []:
            if (
                p.is_file()
                and "__pycache__" not in p.parts
                and p.suffix not in (".pyc", ".ttf")
                and p.name != ".DS_Store"
                and ".egg-info" not in str(p)
            ):
                out.append(p.relative_to(root))
    return out


_LOADING_LINE = re.compile(r"""@import|url\(|\bimport\b|importScripts|fetch\(|\bsrc\b|\bhref\b""")


def _loading_text(path: str, text: str) -> str:
    """The part of ``text`` that can LOAD another file, comments and docs removed.

    Without this the reference chain followed mentions, not loads: ``admin.css``
    says in a comment that ``solver.js`` styles the board, so the sheet became a
    "referencer" of the script, ``base.html`` links the sheet, and one change to
    ``solver.js`` selected every page-rendering test in the suite (95 files,
    58% of the tests, measured). A Python module loads a file through a string
    in code, never through a docstring or comment; a template through a tag or
    attribute, never a ``{# #}``/``<!-- -->`` comment; a stylesheet or script
    through an import/url/fetch/src line.
    """
    if path.endswith(".py"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text)
        except SyntaxError:
            return text
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    docstrings.add(id(body[0].value))
        return "\n".join(
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
        )
    if path.endswith(".html"):
        text = re.sub(r"\{#.*?#\}", "", text, flags=re.S)
        return re.sub(r"<!--.*?-->", "", text, flags=re.S)
    if path.endswith((".css", ".js")):
        return "\n".join(l for l in text.splitlines() if _LOADING_LINE.search(l))
    return text


def _referencers(
    corpus: _Corpus, path: str, extra: str | None = None
) -> tuple[set[str], set[str], set[str]]:
    """Files under ``src/`` and ``scripts/`` that name ``path``, to a fixpoint.

    Returns ``(src_modules, assets, scripts)``: the Python modules that name it
    (or name something that names it -- a template ``include``), the non-Python
    files in the chain (the asset itself excluded), and the scripts that do.
    The chain is what turns ``admin.css`` into ``base.html`` into the module
    that renders ``base.html``.
    """
    files = corpus.loading_texts(extra)
    seen = {path}
    frontier = [path]
    modules: set[str] = set()
    assets: set[str] = set()
    scripts: set[str] = set()
    while frontier:
        pat = _name_pattern(frontier.pop())
        for f, text in files:
            fp = f.as_posix()
            if fp in seen or not pat.search(text):
                continue
            seen.add(fp)
            if fp.endswith(".py") and fp.startswith("src/"):
                module = module_name_for(fp)
                if module:
                    modules.add(module)
            elif fp.endswith(".py") or fp.startswith("scripts/"):
                scripts.add(fp)
            else:
                assets.add(fp)
                frontier.append(fp)
    return modules, assets, scripts


def _classify_pre(path: str) -> Reason | None:
    """The paths no corpus is needed to refuse."""
    if path in UNANALYSABLE:
        return Reason(path, RULE_UNANALYSABLE, "listed in UNANALYSABLE; its blast radius is not modelled")
    if Path(path).name == "conftest.py":
        return Reason(path, RULE_CONFTEST, "a conftest applies to every test beneath it")
    if path.startswith(INSTRUMENT_ROOTS):
        return None  # named, never forced to FULL (see INSTRUMENT_ROOTS)
    if not path.startswith(KNOWN_ROOTS):
        if Path(path).suffix in OUTSIDE_ROOT_DERIVABLE:
            return None  # readers are derived from the file itself (G-6)
        return Reason(
            path,
            RULE_OUTSIDE_ROOTS,
            "not under " + ", ".join(KNOWN_ROOTS) + f" and a {Path(path).suffix or 'suffix-less'} file has no derivation; "
            "'unknown' and 'affects nothing' differ",
        )
    if path.startswith("migrations/"):
        return Reason(path, RULE_MIGRATIONS, "revision order is global and merged order is what runs")
    return None


def derive(root: Path, changed: list[str], corpus: _Corpus | None = None) -> Derivation:
    """The verdict for ``changed``: a selection, or FULL with every reason.

    ``FULL`` carries no file list (so a caller cannot downgrade it by reading
    one) and at least one :class:`Reason` naming a path and a rule. An empty
    changed set is neither: it is ``empty=True``, a fact about the diff.
    """
    changed = [c for c in changed if c]
    if not changed:
        return Derivation(empty=True)

    reasons = [r for c in changed if (r := _classify_pre(c))]
    if reasons:
        return Derivation(full=True, reasons=reasons)

    corpus = corpus or _Corpus(root)
    scanners = corpus.scanners()
    if not scanners:
        # The derivation found no tree-scanning test. On this suite that is
        # false, so the derivation is broken -- never a licence to narrow.
        return Derivation(
            full=True,
            reasons=[Reason(changed[0], RULE_NO_SCANNERS, "no tree-scanning test was found; the derivation itself is broken")],
        )

    selected: set[Path] = set(scanners)
    for walked in ("src", "tests", "meta", "docs", "scripts", "scratchpad"):
        if any(c.startswith(walked + "/") for c in changed):
            selected |= corpus.tree_readers(walked)

    closure_tests, _ = corpus.conftest_closure()
    for path in changed:
        dotted = _tests_dotted(path)
        if dotted and dotted in closure_tests:
            # Every test loads conftest, and conftest loads this: the same
            # blast radius as conftest itself (hang_guard 300 -> 0.05 kills
            # tests/test_solver.py, which no selection of 47 files contained).
            reasons.append(
                Reason(path, RULE_CONFTEST_CLOSURE, "imported (transitively) by tests/conftest.py, which every test loads")
            )
            continue
        got, reason = _derive_one(root, corpus, path)
        if reason:
            reasons.append(reason)
        selected |= got

    if reasons:
        return Derivation(full=True, reasons=reasons)
    return Derivation(files=sorted(p.as_posix() for p in selected))


def _derive_one(root: Path, corpus: _Corpus, path: str) -> tuple[set[Path], Reason | None]:
    rel = Path(path)
    exists = (root / rel).exists()

    # --- a test file: itself, whoever imports it, names it, or globs it ------
    if path.startswith("tests/") and rel.name.startswith("test_") and path.endswith(".py"):
        got: set[Path] = set()
        if exists:
            got.add(rel)
        dotted = _tests_dotted(path)
        got |= corpus.importers(set(), {dotted} if dotted else set())
        got |= corpus.naming(path) | corpus.matching_by_glob_or_prefix(path)
        return got, None

    # --- a Python module under src/ or a helper under tests/ -----------------
    module = module_name_for(path) or tests_module_name_for(path)
    if module is not None:
        if module.startswith("nonogram"):
            got = corpus.importers({module}, set())
            _, conftest_src = corpus.conftest_closure()
            if module in conftest_src:
                # conftest imports it, so every fixture it defines runs on it.
                got |= corpus.conftest_users()
            if module in BROWSER_SURFACE_MODULES:
                got |= corpus.executors()
        else:
            got = corpus.importers(set(), {module})
        got |= corpus.naming(path)
        if not got:
            return got, Reason(path, RULE_NO_IMPORTER, "no test imports it or names it; an unimported module is not an unaffecting one")
        return got, None

    # --- a probe script or a measurement record: named, never FULL -----------
    if path.startswith(INSTRUMENT_ROOTS):
        return corpus.naming(path), None

    # --- an asset shipped under src/, or a derivable file outside the roots --
    outside = not path.startswith(KNOWN_ROOTS)
    if path.startswith("src/") or (outside and rel.suffix in (".css", ".js", ".html")):
        return _derive_asset(root, corpus, path)

    # --- code or data outside src/: named by a reader, or FULL ---------------
    prose_root = path.startswith(("meta/", "docs/")) and not path.endswith(".py")
    got = corpus.naming(path)
    if prose_root:
        # Board prose and data. The scanners (always-on) and the tree readers
        # are the readers of record, so an unnamed one is NOT default-denied:
        # that is the shape the backlog.md / dispatcher.state reds took, and the
        # answer for it has always been "the scanners".
        return got, None
    if not got:
        return got, Reason(path, RULE_NO_READER, "no test names this file, and it is not board prose")
    return got, None


def _derive_asset(root: Path, corpus: _Corpus, path: str) -> tuple[set[Path], Reason | None]:
    key = asset_key(path)
    kind = ASSET_RULES.get(key)
    if kind is None:
        return set(), Reason(path, RULE_UNKNOWN_ASSET, f"no rule for asset type {key!r}; add it to ASSET_RULES with a reader derivation")
    if kind == "inert":
        return set(), None

    in_src = path.startswith("src/")
    readers = corpus.naming(path)
    chain_assets: set[str] = set()
    modules: set[str] = set()
    scripts: set[str] = set()
    top = path.split("/")[0] if not path.startswith(KNOWN_ROOTS) else None
    modules, chain_assets, scripts = _referencers(corpus, path, top)
    for asset in chain_assets:
        readers |= corpus.naming(asset)
    for script in scripts:
        readers |= corpus.naming(script)

    if kind == "executed":
        ids = _identifiers(path, _read(root, path))
        if ids:
            readers |= {t for t in corpus.tests if ids & corpus.tokens(t)}
        if modules:
            readers |= corpus.importers(modules, set()) & corpus.executors()
        if top:
            # A page outside src/ is driven by a browser that names its directory.
            readers |= corpus.dir_namers(top) & corpus.executors()
    elif modules:
        readers |= corpus.importers(modules, set())

    if not readers and not modules and not chain_assets and not scripts:
        # Nothing names it, declares a selector a test uses, loads or renders it:
        # the cheap rule below must not paper over an asset nobody reads.
        return readers, Reason(path, RULE_NO_READER, f"a {kind} asset that no test names, no declared selector reaches, and no module renders")

    if in_src and kind in ("executed", "template"):
        # The cheap safe rule. Tracing which browser test renders which page is
        # not provably complete (a test gets the app from a helper module, a
        # fixture or a subprocess; cycle 1 proved two misses by exactly that),
        # so an admin/web static asset or template selects EVERY browser test
        # and every test using a conftest fixture.
        readers |= corpus.executors() | corpus.conftest_users()

    return readers, None


def select(root: Path, changed: list[str], corpus: _Corpus | None = None) -> list[str] | str:
    """The selection for ``changed``, or :data:`FULL`.

    Returns FULL rather than a narrowed set whenever a changed path is one this
    script does not model, or when a changed file has no derivable reader -- an
    unimported module is not an unaffecting one, it is a coupling this script
    cannot see. :func:`derive` carries the reasons; this is its list-or-FULL form.
    """
    derived = derive(root, changed, corpus=corpus)
    return FULL if derived.full else derived.files


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

    ``--no-renames`` is deliberate: git's default rename detection lists only
    the NEW name, so the tests importing the OLD module would not be selected
    -- and they are exactly the ones that break.

    Honest bound: a new file added outside those two roots is invisible here.
    The scanners in the always-on set are what read the rest of the tree.
    """
    names: set[str] = set()
    commands = (
        ["diff", "--name-only", "--no-renames", base],   # committed on this branch
        ["diff", "--name-only", "--no-renames"],          # unstaged edits to tracked files
        ["diff", "--name-only", "--no-renames", "--cached"],  # staged edits
        ["ls-files", "--others", "--exclude-standard", "--", "src", "tests"],
    )
    for args in commands:
        out = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        )
        names.update(line for line in out.stdout.splitlines() if line.strip())
    return sorted(names)


def collect_count(root: Path, files: list[str] | None) -> int:
    """How many tests pytest COLLECTS for ``files`` (``None`` = the whole suite).

    Derived by a real ``pytest --collect-only``, never carried: the suite's size
    moves with every card, and a figure copied from a note is stale by the next
    gate. ``-o addopts=`` keeps the project's own options out of the count, and
    a collection error raises rather than counting what did collect.
    """
    if files is not None and not files:
        return 0
    cmd = [
        sys.executable, "-m", "pytest", "--collect-only", "-q",
        "-o", "addopts=", "-p", "no:cacheprovider",
        *(files or []),
    ]
    out = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    text = out.stdout + out.stderr
    if out.returncode != 0:
        tail = "\n".join(text.strip().splitlines()[-6:])
        raise RuntimeError(f"pytest --collect-only exited {out.returncode}: {tail}")
    summary = re.search(r"(\d+)(?:/(\d+))? tests? collected", text)
    if summary:
        return int(summary.group(2) or summary.group(1))
    return sum(1 for line in out.stdout.splitlines() if "::" in line)


def gate_verdict(root: Path, changed: list[str], count=None) -> tuple[str, int]:
    """The gate's one pasteable block AND its exit code.

    ``count`` is injectable so the format is testable without spawning pytest;
    the real default derives both figures by collection. A selection is only
    vouched for ("nothing more is owed") when BOTH counts were collected and the
    selection is non-empty: a failed or zero count is FULL
    (``count-unavailable``), never a quiet pass -- a collection error or a held
    full-suite lock must not read as a narrow, green gate.
    """
    if count is None:
        def count(files):
            return collect_count(root, files)

    derived = derive(root, changed)
    shown = [c for c in changed if c]
    head = ", ".join(shown[:6]) + (f", ... +{len(shown) - 6} more" if len(shown) > 6 else "")
    lines = ["IMPACT GATE", f"changed ({len(shown)}): {head or '(nothing)'}"]
    codes = f"exit codes: {EXIT_SELECTION} selection | {EXIT_FULL} FULL | {EXIT_COUNT_FAILED} count failed (= FULL) | {EXIT_EMPTY} empty"

    if derived.empty:
        lines += [
            "answer: EMPTY -- no changed path. This is NOT a pass: a wrong --base/--against,",
            "  a detached tree or a failed diff looks exactly like this. Check the base.",
            f"exit code: {EXIT_EMPTY}",
            codes,
        ]
        return "\n".join(lines), EXIT_EMPTY

    try:
        total, total_error = count(None), None
    except Exception as exc:
        total, total_error = None, str(exc)

    if derived.full:
        lines.append("answer: FULL -- run the whole suite")
        lines.append(
            f"tests: {total} of {total} collected (100%)"
            if total is not None
            else f"tests: ? of unavailable ({total_error})"
        )
        lines.append("FULL because:")
        lines += [f"  - {r}" for r in derived.reasons]
        lines += [f"exit code: {EXIT_FULL}", codes]
        return "\n".join(lines), EXIT_FULL

    chosen, chosen_error = None, None
    if total is not None:
        try:
            chosen = count(derived.files)
        except Exception as exc:
            chosen_error = str(exc)
    if total is None or chosen is None or chosen == 0:
        why = total_error or chosen_error or "the selection collected 0 tests"
        reason = Reason("(gate)", RULE_COUNT_UNAVAILABLE, f"the size could not be collected, so the selection cannot be vouched for: {why}")
        lines.append("answer: FULL -- the count failed, so this is treated as FULL")
        lines.append(f"tests: ? of {total if total is not None else 'unavailable'}")
        lines.append("FULL because:")
        lines.append(f"  - {reason}")
        lines += [f"exit code: {EXIT_COUNT_FAILED}", codes]
        return "\n".join(lines), EXIT_COUNT_FAILED

    pct = f" ({100 * chosen / total:.1f}%)" if total else ""
    lines.append("answer: SELECTION -- run the files below, then nothing more is owed")
    lines.append(f"tests: {chosen} of {total} collected{pct}")
    lines.append(f"files: {len(derived.files)} test files, {len(always_on(root))} of them always-on")
    lines += [f"exit code: {EXIT_SELECTION}", codes, "selection:"]
    lines += [f"  {f}" for f in derived.files]
    return "\n".join(lines), EXIT_SELECTION


def gate_report(root: Path, changed: list[str], count=None) -> str:
    """:func:`gate_verdict`'s block alone."""
    return gate_verdict(root, changed, count)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive the test selection for a changed set. Prints one "
        "path per line, or the single token FULL (the reasons go to stderr); "
        "always exits 0. With --gate: one pasteable block with the selection's "
        "size against the full suite's collected count, and an exit code that "
        f"branches ({EXIT_SELECTION} selection, {EXIT_FULL} FULL, "
        f"{EXIT_COUNT_FAILED} count failed = FULL, {EXIT_EMPTY} empty)."
    )
    parser.add_argument(
        "--base", help="git revision to diff against (e.g. the merge-base)"
    )
    parser.add_argument(
        "--against",
        help="a branch to diff against via its merge-base with HEAD "
        "(the gate form: --gate --against main)",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="print the gate block instead of the bare list",
    )
    parser.add_argument("files", nargs="*", help="changed paths, repo-relative")
    args = parser.parse_args(argv)

    root = repo_root()
    base = args.base
    if args.against:
        base = subprocess.run(
            ["git", "-C", str(root), "merge-base", args.against, "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    changed = (changed_from_git(root, base) if base else []) + list(args.files)

    if args.gate:
        block, code = gate_verdict(root, changed)
        print(block)
        return code

    derived = derive(root, changed)
    if derived.full:
        print(FULL)
        for reason in derived.reasons:
            print(f"FULL because: {reason}", file=sys.stderr)
    else:
        for path in derived.files:
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
