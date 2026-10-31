"""Derive the stream-reader set and the site-walk closure, for F-001/F-002.

Run: python scratchpad/card329/derive_stream_readers.py
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OWNERS = ("tests/helpers/pdf_vector.py", "tests/helpers/pdf_pages.py")
#: The poppler engines, and the PDF keys a page's own content stream and
#: medium hang off.
ENGINES = {"PDFTOPPM", "PDFTOTEXT"}
KEYS = {b"Contents", b"Resources"}
STREAM_PARAM = "stream"


def _names(node):
    out = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Name):
            out.add(inner.id)
        elif isinstance(inner, ast.Attribute):
            out.add(inner.attr)
    return out


def _constants(node):
    return {
        inner.value
        for inner in ast.walk(node)
        if isinstance(inner, ast.Constant) and isinstance(inner.value, bytes)
    }


def functions(path):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = {
                a.arg
                for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            }
            out[node.name] = (params, _names(node), _constants(node))
    return out


def main():
    table = {}
    public = set()
    for path in OWNERS:
        for name, value in functions(path).items():
            table[name] = value
            if not name.startswith("_"):
                public.add(name)

    crossing = set()
    for name, (params, names, consts) in table.items():
        if names & ENGINES or consts & KEYS or STREAM_PARAM in params:
            crossing.add(name)
    # fixed point over calls between the two helpers' own functions
    for _ in range(len(table) + 1):
        grown = {
            name
            for name, (_p, names, _c) in table.items()
            if name not in crossing and names & crossing
        }
        if not grown:
            break
        crossing |= grown

    derived = crossing & public
    print("public functions of the two helpers:", len(public))
    print("DERIVED stream readers (%d):" % len(derived))
    for n in sorted(derived):
        print("   ", n)
    print("NON-CROSSING public (%d):" % len(public - derived))
    for n in sorted(public - derived):
        print("   ", n)
    print("private matched (excluded by the public filter):",
          sorted(crossing - public))
    return 0


if __name__ == "__main__":
    sys.exit(main())
