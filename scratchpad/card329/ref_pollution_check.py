"""Can scratchpad/card329 resolve a check ref that tests/ does not already?

The architecture validator's check-ref search is a TEXT search over the repo
(excluding meta/architecture and *.md), so a symbol MENTIONED in a scratchpad
file can silence a dead-ref warning. This asks the narrow question: is every
test-like symbol my scratchpad mentions ALSO defined as a `def`/`class` in
tests/? If so the scratchpad cannot change any ref's resolution, because the
real definition already resolves it.
"""
import ast, re, sys
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-329")
SYMBOL = re.compile(r"\b((?:Test|PropertyTest|test)_?[A-Za-z0-9_]{4,})\b")

mentioned = set()
for path in sorted((ROOT / "scratchpad/card329").glob("*.py")):
    for name in SYMBOL.findall(path.read_text()):
        mentioned.add(name)

defined = set()
for path in (ROOT / "tests").rglob("*.py"):
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)

# Names that are plainly not symbols: module basenames, pytest internals.
module_names = {p.stem for p in (ROOT / "tests").rglob("*.py")}
noise = module_names | {"test_", "Test_", "Test", "pytest_configure", "testpaths"}

orphans = sorted(n for n in mentioned - defined - noise)
print(f"symbols mentioned in scratchpad/card329: {len(mentioned)}")
print(f"of those, NOT defined anywhere in tests/ and not a module name: {len(orphans)}")
for name in orphans:
    print(f"    {name}")
sys.exit(1 if orphans else 0)
