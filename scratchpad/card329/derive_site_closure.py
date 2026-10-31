"""The site walk closed over the call graph, for F-001.

Prints each EDGE_TOLERANCE_MM site's direct reader set, its transitive
closure, and the stream readers each intersects.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "tests/test_book_pdf.py"
HELPERS = sorted((ROOT / "tests/helpers").glob("*.py"))

sys.path.insert(0, str(ROOT / "scratchpad/card329"))
from derive_stream_readers import functions as _owner_functions  # noqa: E402


def _names(node):
    out = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Name):
            out.add(inner.id)
        elif isinstance(inner, ast.Attribute):
            out.add(inner.attr)
    return out


def helper_bodies():
    """name -> the names its body mentions, for every function a site could
    reach: this module's own and every tests/helpers module's."""
    table = {}
    for path in [MODULE] + HELPERS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                table.setdefault(node.name, set()).update(_names(node))
    return table


def sites():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    found = []

    def visit(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, prefix + (child.name,))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names = _names(child)
                if "EDGE_TOLERANCE_MM" in names:
                    found.append(("::".join(prefix + (child.name,)), names))
                visit(child, prefix + (child.name,))
            else:
                visit(child, prefix)

    visit(tree, ())
    return found


def close(direct, table):
    out = set(direct)
    for _ in range(len(table) + 1):
        grown = set()
        for name in out:
            grown |= table.get(name, set())
        if grown <= out:
            break
        out |= grown
    return out


def main():
    table = helper_bodies()
    # the derived stream readers, module-level public only
    owners = {}
    for path in ("tests/helpers/pdf_vector.py", "tests/helpers/pdf_pages.py"):
        owners.update(_owner_functions(path))
    engines = {"PDFTOPPM", "PDFTOTEXT"}
    keys = {b"Contents", b"Resources"}
    crossing = {
        n for n, (p, nm, c) in owners.items()
        if nm & engines or c & keys or "stream" in p
    }
    for _ in range(len(owners) + 1):
        grown = {n for n, (_p, nm, _c) in owners.items()
                 if n not in crossing and nm & crossing}
        if not grown:
            break
        crossing |= grown
    readers = {n for n in crossing if not n.startswith("_")}

    for name, direct in sites():
        closed = close(direct, table)
        print(name)
        print("   direct  ∩ readers:", sorted(direct & readers))
        print("   closed  ∩ readers:", sorted(closed & readers))
        print("   drawing_of direct:", "drawing_of" in direct,
              " closed:", "drawing_of" in closed,
              " |direct|=%d |closed|=%d" % (len(direct), len(closed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
