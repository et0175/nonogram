"""Resolve test refs by DEFINITION (ast), never by grep -lw.

Usage: python resolve_refs.py <tests_root> <name> [<name> ...]
Prints one line per name: FOUND <name> <file>:<line> <kind>  |  ABSENT <name>
"""
import ast, pathlib, sys

def index(root: pathlib.Path):
    defs = {}
    for p in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"!! SYNTAXERROR {p}: {e}", file=sys.stderr)
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "func"
                defs.setdefault(node.name, []).append((str(p), node.lineno, kind))
    return defs

if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1])
    defs = index(root)
    print(f"# indexed {len(defs)} distinct definition names under {root}", file=sys.stderr)
    for name in sys.argv[2:]:
        hits = defs.get(name)
        if hits:
            for f, ln, k in hits:
                print(f"FOUND   {name}  {f}:{ln} ({k})")
        else:
            print(f"ABSENT  {name}")
