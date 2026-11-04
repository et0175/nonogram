"""CARD-336 AC-3: derive the placed-edge population of the two Touches modules."""
from __future__ import annotations
import ast, pathlib, sys, dataclasses

sys.path.insert(0, ".")
from tests.helpers.page_ink import Drawing

INK_EDGES = frozenset(
    f.name for f in dataclasses.fields(Drawing)
    if f.type in ("int",) and f.name not in {"columns", "rows"}
)
print("INK_EDGES derived from Drawing:", sorted(INK_EDGES))

MODULES = ("tests/property/test_book_pdf_geometry.py", "tests/test_book_puzzle_frame.py")


def qualname(tree):
    out = {}
    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + "::")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[child] = prefix + child.name
                walk(child, prefix + child.name + ".")
            else:
                walk(child, prefix)
    walk(tree, "")
    return out


for path in MODULES:
    tree = ast.parse(pathlib.Path(path).read_text())
    names = qualname(tree)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    print(f"\n########## {path}")
    for fn, qn in sorted(names.items(), key=lambda kv: kv[0].lineno):
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assert):
                continue
            reads = [
                n for n in ast.walk(node)
                if isinstance(n, ast.Attribute) and n.attr in INK_EDGES
            ]
            if not reads:
                continue
            # pairing: nearest enclosing BinOp/Compare/Call holding >= 2 reads
            unpaired = []
            for r in reads:
                cur, paired = r, False
                for _ in range(6):
                    cur = parents.get(cur)
                    if cur is None or isinstance(cur, (ast.Assert, ast.stmt)):
                        break
                    if isinstance(cur, (ast.BinOp, ast.Compare, ast.Call)):
                        inner = [
                            n for n in ast.walk(cur)
                            if isinstance(n, ast.Attribute) and n.attr in INK_EDGES
                        ]
                        if len(inner) >= 2:
                            paired = True
                            break
                if not paired:
                    unpaired.append(r)
            tag = "PAIRED" if not unpaired else "UNPAIRED"
            print(f"  L{node.lineno:5d} {tag:8s} {qn}  reads={[r.attr for r in reads]}"
                  f" unpaired={sorted({r.attr for r in unpaired})}")
