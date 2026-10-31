"""CARD-329 G-5: the node-id set difference, derived from the AST on disk.

Not a test and not under ``tests/`` (G-7). G-5 forbids a test being deleted,
renamed, skipped or merged, ``parametrize`` ids included. Run with a git
revision to compare this worktree against it:

    python scratchpad/card329/node_ids.py f7ba9c96

Derived with ``ast`` over the files, not from ``--collect-only``: with
``addopts = "-q"`` in ``pyproject.toml`` a ``--collect-only -q`` prints no
node ids at all, and the quoted ``-o "addopts="`` form silently collects the
whole suite. A guard that reads a number off a command that can go quiet is
not a guard.

``python_classes`` is unset, so pytest collects ``Test*`` only -- a
``PropertyTest_*`` class is never collected, and this walk applies the same
rule so the two agree.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "tests/helpers/pdf_pages.py",
    "tests/test_book_pdf.py",
    "tests/test_book_pdf_levels.py",
    "tests/test_book_pdf_two_up.py",
    "tests/property/test_book_pdf_geometry.py",
    "tests/test_book_puzzle_frame.py",
    "tests/test_book_cell_size.py",
)


def ids(path: str, source: str) -> set[str]:
    out: set[str] = set()
    tree = ast.parse(source, filename=path)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test"):
                out.add(f"{path}::{node.name}")
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for item in node.body:
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and item.name.startswith("test"):
                    out.add(f"{path}::{node.name}::{item.name}")
    return out


def at(revision: str, path: str) -> str:
    done = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=str(ROOT), capture_output=True, text=True, check=True,
    )
    return done.stdout


def main() -> int:
    revision = sys.argv[1] if len(sys.argv) > 1 else "f7ba9c96"
    before: set[str] = set()
    after: set[str] = set()
    for path in FILES:
        before |= ids(path, at(revision, path))
        after |= ids(path, (ROOT / path).read_text())
    lost = sorted(before - after)
    gained = sorted(after - before)
    print(f"base {revision}: {len(before)} node ids")
    print(f"worktree:      {len(after)} node ids")
    print(f"\nLOST ({len(lost)}) -- any is a G-5 violation")
    for node in lost:
        print(f"    {node}")
    print(f"\nGAINED ({len(gained)})")
    for node in gained:
        print(f"    {node}")
    assert not lost, "G-5: a node id disappeared"
    return 0


if __name__ == "__main__":
    sys.exit(main())
