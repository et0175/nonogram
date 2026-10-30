"""Re-derive the two reader populations AC-3 names. No pasted figures."""
import ast, pathlib, sys, json

root = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-309")
tests = root / "tests"

A, B = set(), set()
for p in sorted(tests.rglob("*.py")):
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    rel = str(p.relative_to(root))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("helpers.pdf_pages"):
            if any(a.name == "pdf_pages" for a in node.names):
                A.add(rel)
        if isinstance(node, ast.Attribute) and node.attr in ("interior", "interior_pages"):
            B.add(rel)
print("A (imports the one-image reader):", len(A))
for m in sorted(A): print("   ", m)
print("B (calls .interior/.interior_pages):", len(B))
for m in sorted(B): print("   ", m)
print("A&B:", len(A & B))
print("B-A:", len(B - A))
for m in sorted(B - A): print("   ", m)
print("A-B:", len(A - B))
for m in sorted(A - B): print("   ", m)
json.dump({"A": sorted(A), "B": sorted(B)}, open(root/"scratchpad/card309/readers.json","w"), indent=1)
