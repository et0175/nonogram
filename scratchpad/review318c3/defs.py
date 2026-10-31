"""AC-2 + check-ref resolution by DEFINITION (G-3), with the instrument proven
in both directions.  `ast` ClassDef/FunctionDef over tests/**/*.py — never
`git grep -lw`, which is a text search and is exactly what F-007 measured."""
import ast, re, sys
from pathlib import Path
import yaml

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
defs = {}
for p in sorted((ROOT / "tests").rglob("*.py")):
    try:
        t = ast.parse(p.read_text())
    except SyntaxError:
        continue
    for n in ast.walk(t):
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(n.name, []).append(f"{p.relative_to(ROOT)}:{n.lineno}")
print("definition names indexed in tests/:", len(defs))
# instrument proven in both directions
assert "test_the_puzzle_list_filters_by_strategy" in defs, "positive control failed"
assert "TestNoSuchClass_ThisIsANonsenseControl" not in defs, "negative control failed"
print("instrument controls: positive OK, negative OK")

reqs = yaml.safe_load((ROOT / "meta/architecture/requirements.yml").read_text())
def walk(o):
    if isinstance(o, dict):
        if o.get("id") == "FR-029":
            yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)
fr = list(walk(reqs))[0]
rows = list(fr.get("acceptance") or []) + list(fr.get("engineering_constraints") or [])
print(f"\nFR-029 criteria rows: {len(rows)}")
bad = []
for r in rows:
    ref = r.get("test")
    if not ref:
        print(f"  {r['id']:<8} (no test: key) kind={r.get('kind')}"); bad.append(r['id']); continue
    where = defs.get(ref)
    print(f"  {r['id']:<8} {'DEF OK ' if where else 'PHANTOM'} {ref}")
    if not where: bad.append(r["id"])
print("\nphantom/absent refs on FR-029:", bad or "none")
print("FR-029 tests: key:", fr.get("tests"))
for t in fr.get("tests") or []:
    base = t.split("::")[-1].split("[")[0]
    print(f"   {'DEF OK ' if base in defs else 'NO DEF'} {t}")

print("\n--- ADR-0039 / ADR-0006 rule check refs ---")
for rid, ref in [("ADR-0039/R1", "test_the_control_for_each_spelling_depends_on_the_set"),
                 ("ADR-0039/R2", "test_the_guard_sets_are_derived_and_not_hand_written"),
                 ("ADR-0039/R3", "test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw")]:
    print(f"  {rid}: {'DEF OK' if ref in defs else 'PHANTOM'}  (ref name withheld from this output's YAML twin)")
