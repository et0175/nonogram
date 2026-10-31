"""G-6 + G-7 re-derived with `ast`: node ids per test file, before vs after.

A node id here = a module-level `test_*` function, plus `Test*`-class methods
named `test_*` (pytest's default python_classes is the PREFIX `Test`, so a
`PropertyTest_*` class is NOT collected and must not be counted).  Decorators
are reported, because a parametrize/skipif changes the collected count.
"""
import ast, subprocess, sys

ROOT = "/Users/omelnikova/PycharmProjects/PythonProject4-card-318"
FILES = ["tests/test_strategies.py", "tests/test_solver_strategies.py",
         "tests/test_batch_generator.py", "tests/test_puzzle_review_book_filter.py",
         "tests/test_puzzle_review_bulk_read.py", "tests/test_difficulty.py"]
REVS = {"before (2ee0be38)": "2ee0be38", "after (HEAD)": "HEAD",
        "branch base (ef242847)": "ef242847"}

def blob(rev, path):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def ids(src):
    tree = ast.parse(src)
    out, decos = [], 0
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
            out.append(n.name); decos += len(n.decorator_list)
        elif isinstance(n, ast.ClassDef) and n.name.startswith("Test"):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test"):
                    out.append(f"{n.name}::{m.name}"); decos += len(m.decorator_list)
    return sorted(out), decos

for path in FILES:
    print(f"\n{path}")
    sets = {}
    for label, rev in REVS.items():
        src = blob(rev, path)
        if src is None:
            print(f"  {label:<24} (absent)"); continue
        s, d = ids(src)
        sets[label] = s
        print(f"  {label:<24} {len(s)} node ids, {d} decorators")
    keys = list(sets)
    if "before (2ee0be38)" in sets and "after (HEAD)" in sets:
        same = sets["before (2ee0be38)"] == sets["after (HEAD)"]
        print(f"  before == after as sorted sets: {same}")
        if not same:
            print("   added:", set(sets['after (HEAD)']) - set(sets['before (2ee0be38)']))
            print("   removed:", set(sets['before (2ee0be38)']) - set(sets['after (HEAD)']))
# nested helper check
src = blob("HEAD", "tests/test_strategies.py")
t = ast.parse(src)
nested = []
for n in ast.walk(t):
    if isinstance(n, ast.FunctionDef) and n.name == "listed":
        nested.append(n.lineno)
print(f"\n`listed` defined at lines {nested} — module-level test ids contain 'listed': "
      f"{'listed' in ids(src)[0]}")
