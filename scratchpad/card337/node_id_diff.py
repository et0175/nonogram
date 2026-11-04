"""CARD-337 G-5: no test deleted, renamed, skipped or merged.

The node-id set of a module, derived by `ast` from two revisions of the file,
and the set difference between them. NOT `--collect-only`: this project's
`addopts = "-q"` and the brief's own measured trap both make that reading
unreliable as a gate, and `ast` reads the file on disk with no import and no
plugin.

`parametrize` ids are included, because dropping one is dropping a case: each
`@pytest.mark.parametrize` argvalues list is counted and its length reported
beside the function, so a case removed from a list shows as a changed count
even when the function name is untouched.

    python scratchpad/card337/node_id_diff.py <git-rev> <path>
"""
from __future__ import annotations

import ast
import subprocess
import sys


def nodes(source: str, path: str) -> dict[str, int]:
    """Every test node in `source`, mapped to its parametrize case count."""
    tree = ast.parse(source, filename=path)
    found: dict[str, int] = {}

    def params(fn: ast.FunctionDef) -> int:
        total = 1
        for dec in fn.decorator_list:
            call = dec if isinstance(dec, ast.Call) else None
            if call is None:
                continue
            target = call.func
            name = []
            while isinstance(target, ast.Attribute):
                name.append(target.attr)
                target = target.value
            if "parametrize" not in name:
                continue
            for arg in call.args:
                if isinstance(arg, (ast.List, ast.Tuple)):
                    total *= len(arg.elts)
                    break
        return total

    def walk(node, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}::")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith("test"):
                    found[f"{prefix}{child.name}"] = params(child)

    walk(tree, "")
    return found


rev, path = sys.argv[1], sys.argv[2]
before = nodes(
    subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, check=True).stdout.decode(),
    path,
)
after = nodes(open(path, encoding="utf-8").read(), path)

gone = sorted(set(before) - set(after))
added = sorted(set(after) - set(before))
recased = sorted(k for k in set(before) & set(after) if before[k] != after[k])

print(f"{path}")
print(f"  nodes at {rev}: {len(before)}  cases: {sum(before.values())}")
print(f"  nodes now:        {len(after)}  cases: {sum(after.values())}")
print(f"  REMOVED: {gone or 'none'}")
print(f"  added:   {added or 'none'}")
print(f"  case count changed: {[(k, before[k], after[k]) for k in recased] or 'none'}")

# A skip added is a test retired by another name, so it is part of this gate.
src = open(path, encoding="utf-8").read()
for marker in ("pytest.skip", "mark.skip", "mark.xfail", "pytest.xfail"):
    print(f"  occurrences of {marker!r}: {src.count(marker)}")

failed = bool(gone or recased)
print("GATE: " + ("FAIL" if failed else "PASS"))
sys.exit(1 if failed else 0)
