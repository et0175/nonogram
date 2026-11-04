"""CARD-337 G-8: can scratchpad/card337 resolve a check ref tests/ does not?

The architecture validator's check-ref search is a TEXT search over tracked
files (excluding meta/architecture and *.md), so a test symbol MENTIONED in a
tracked scratchpad file can SILENCE a dead-ref warning -- measured on main and
carded as CARD-335. `mutation_runs.py` names eleven real test functions in its
must-red and control lists, which is exactly the shape that hazard takes, so
this card owes the check rather than the assurance.

The narrow question, and the only one that matters: is every test-like symbol
this scratchpad mentions ALSO defined as a `def`/`class` **in tests/**? If so
the scratchpad cannot change any ref's resolution, because the real definition
already resolves it -- and a name that is NOT so defined is a dead ref this
scratchpad would revive.

CARD-329's `ref_pollution_check.py` is the pattern. Reimplemented natively
rather than imported: a sibling card's scratchpad is not a dependency, and its
ROOT is hardcoded to that card's own worktree.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "scratchpad" / "card337"
SYMBOL = re.compile(r"\b((?:Test|PropertyTest|test)_?[A-Za-z0-9_]{4,})\b")

mentioned: set[str] = set()
for path in sorted(HERE.glob("*.py")):
    mentioned.update(SYMBOL.findall(path.read_text(encoding="utf-8")))

defined: set[str] = set()
for path in (ROOT / "tests").rglob("*.py"):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)

module_names = {p.stem for p in (ROOT / "tests").rglob("*.py")}

#: Names that are plainly not symbols: module basenames, pytest internals, and
#: one PREFIX FRAGMENT classified rather than bucketed (ADR-0039/R2).
#:
#: ``test_book_`` is matched out of ``cross_tab.py``'s
#: ``Path(m).name.replace("test_book_", "")`` -- a string-manipulation literal,
#: not a symbol. It is admitted here because it was CHECKED, not because the
#: gate was inconvenient: the token ``test_book_`` followed by a non-word
#: character occurs nowhere in ``meta/architecture`` at all, so there is no
#: check ref it could resolve, and it already sits in an instrument the
#: previous round committed. A name that is a real test symbol never reaches
#: this set.
noise = module_names | {
    "test_", "Test_", "Test", "pytest_configure", "testpaths", "test_book_",
}

orphans = sorted(n for n in mentioned - defined - noise)
print(f"symbols mentioned in scratchpad/card337: {len(mentioned)}")
print(f"of those, NOT defined as a def/class in tests/ and not a module name: "
      f"{len(orphans)}")
for name in orphans:
    print(f"    {name}")
print("GATE: " + ("FAIL -- a tracked instrument would revive these refs" if orphans else "PASS"))
sys.exit(1 if orphans else 0)
