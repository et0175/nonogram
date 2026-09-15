"""CARD-092 AC-4 — does every code reference in a document point at something real?

    python meta/ops/check_doc_references.py [docs/GENERATION_ALGORITHM.md]

The generation reference points into ``src/nonogram`` by *symbol*, not by line
(CARD-092 Q-1): line anchors went stale within three days when the orchestrator
grew by a thousand lines. Symbols survive edits, but they can still be renamed
or deleted, so this resolves each one with ``ast`` and prints where it lives.

What counts as a reference -- a backtick span that is

* ``module.symbol[.member...]``, where ``module`` names a module under
  ``src/nonogram`` by its dotted path (``solver.search``) or by an unambiguous
  basename (``search``); the rest is resolved through classes, functions,
  nested functions and module- or class-level assignments;
* a bare ``UPPER_CASE`` name, checked to be assigned somewhere in the package;
* ``path/to/file.py`` under ``src/nonogram``, ``tests`` or ``meta``, checked to
  exist, with an optional ``::test_name`` checked inside it.

A line ending in ``<!-- historical -->`` inverts the check for its spans: they
name things the code *removed*, and must no longer resolve.

Anything else in backticks (``random.Random``, ``--size WxH``, prose code) is not
ours to check and is counted as skipped. A leftover ``file.py:123`` line anchor
is reported as a failure: the document decided not to use them.

Exit status 1 when anything fails to resolve.
"""

from __future__ import annotations

import ast
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "nonogram"

SPAN = re.compile(r"`([^`\n]+)`")
DOTTED = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)+(\(\))?$")
CONSTANT = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
PATH = re.compile(r"^((?:src/nonogram|tests|meta)/[\w./-]+\.(?:py|md|yml|png))(?:::(\w+))?$")
LINE_ANCHOR = re.compile(r"\.py:\d+")


def _modules() -> dict[str, list[Path]]:
    names: dict[str, list[Path]] = {}
    for path in PACKAGE.rglob("*.py"):
        dotted = ".".join(path.relative_to(PACKAGE).with_suffix("").parts)
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        names.setdefault(dotted, []).append(path)
        names.setdefault(dotted.rsplit(".", 1)[-1], []).append(path)
    return names


def _members(node: ast.AST, path: Path | None = None) -> dict[str, ast.AST | Path]:
    found: dict[str, ast.AST | Path] = {}
    for child in ast.iter_child_nodes(node):
        # A package re-export (``from .search import solve`` in ``solver/__init__``)
        # counts as the package's member; resolution continues in the source module.
        if path is not None and isinstance(child, ast.ImportFrom) and (
            child.level or (child.module or "").startswith("nonogram.")
        ):
            if child.level:
                base = path.parent
                for _ in range(child.level - 1):
                    base = base.parent
            else:
                base = PACKAGE.parent
            target = base.joinpath(*(child.module or "").split(".")).with_suffix(".py")
            for alias in child.names:
                if target.exists():
                    found[alias.asname or alias.name] = (target, alias.name)  # type: ignore[assignment]
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found[child.name] = child
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = child
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            found[child.target.id] = child
    return found


def _resolve(path: Path, parts: list[str], trees: dict[Path, ast.Module]) -> tuple[Path, int] | None:
    node: ast.AST = trees.setdefault(path, ast.parse(path.read_text()))
    for index, part in enumerate(parts):
        members = _members(node, path if index == 0 else None)
        if part not in members:
            return None
        found = members[part]
        if isinstance(found, tuple):  # followed a re-export
            source, name = found
            return _resolve(source, [name, *parts[index + 1 :]], trees)
        node = found
    return path, getattr(node, "lineno", 1)


def main() -> int:
    document = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "GENERATION_ALGORITHM.md"
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    text = document.read_text()
    modules = _modules()
    trees: dict[Path, ast.Module] = {}
    constants = {
        name
        for path in PACKAGE.rglob("*.py")
        for name, node in _members(trees.setdefault(path, ast.parse(path.read_text()))).items()
        if CONSTANT.match(name)
    } | {
        name
        for path in PACKAGE.rglob("*.py")
        for cls in ast.walk(trees[path]) if isinstance(cls, ast.ClassDef)
        for name in _members(cls) if CONSTANT.match(name)
    }

    # Every name defined at module or class level anywhere in the package, so a
    # historical line can claim a bare name (``SignalWeights``) is really gone.
    top_level = {
        name
        for path in PACKAGE.rglob("*.py")
        for node in ast.walk(trees[path])
        if isinstance(node, (ast.Module, ast.ClassDef))
        for name in _members(node)
    }

    resolved: list[str] = []
    failed: list[str] = []
    skipped = 0
    for number, line in enumerate(text.splitlines(), 1):
        historical = line.rstrip().endswith("<!-- historical -->")
        # Line anchors are refused anywhere, not only in backticks: the old
        # pipeline diagram carried them inside a code block.
        outside = SPAN.sub("", line)
        if LINE_ANCHOR.search(outside):
            failed.append(f"{number}: line anchor outside backticks: {outside.strip()}")
        for span in SPAN.findall(line):
            span = span.strip()
            if historical:
                parts = span.removesuffix("()").split(".")
                alive = span in constants or span in top_level or any(
                    modules.get(".".join(parts[:cut]))
                    and _resolve(modules[".".join(parts[:cut])][0], parts[cut:], trees)
                    for cut in range(len(parts) - 1, 0, -1)
                )
                (failed if alive else resolved).append(
                    f"{number}: `{span}` (historical) {'still exists' if alive else 'is gone, as stated'}"
                )
                continue
            if LINE_ANCHOR.search(span):
                failed.append(f"{number}: `{span}` is a line anchor")
                continue
            if match := PATH.match(span):
                target = ROOT / match.group(1)
                if not target.exists():
                    failed.append(f"{number}: `{span}` -- no such file")
                elif match.group(2) and not re.search(rf"def {match.group(2)}\b", target.read_text()):
                    failed.append(f"{number}: `{span}` -- no such test in the file")
                else:
                    resolved.append(f"{number}: `{span}`")
                continue
            if CONSTANT.match(span):
                if span in constants:
                    resolved.append(f"{number}: `{span}`")
                else:
                    failed.append(f"{number}: `{span}` -- no such constant in src/nonogram")
                continue
            if not DOTTED.match(span):
                skipped += 1
                continue
            parts = span.removesuffix("()").split(".")
            # longest module prefix wins: solver.search._search before search
            for cut in range(len(parts), 0, -1):
                candidates = modules.get(".".join(parts[:cut]))
                if candidates:
                    break
            else:
                skipped += 1  # not a nonogram module: random.Random, Tier.GUESS, ...
                continue
            if len(set(candidates)) > 1:
                failed.append(f"{number}: `{span}` -- module name is ambiguous: {sorted({str(c.relative_to(ROOT)) for c in candidates})}")
                continue
            path = candidates[0]
            where = _resolve(path, parts[cut:], trees)
            if where is None:
                failed.append(f"{number}: `{span}` -- not found in {path.relative_to(ROOT)}")
            else:
                resolved.append(f"{number}: `{span}` -> {where[0].relative_to(ROOT)}:{where[1]}")

    for entry in resolved:
        print("ok  ", entry)
    for entry in failed:
        print("FAIL", entry)
    print(f"\n{len(resolved)} resolved, {len(failed)} failed, {skipped} other backtick spans skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
