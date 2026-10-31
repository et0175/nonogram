"""Y4 — reviewer's own probe: null the route's strategy wiring and see whether
ANYTHING in FR-029's impact set reds.  Same protocol as refire.py."""
import hashlib, os, re, shutil, subprocess
from pathlib import Path
ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
APP = ROOT / "src/nonogram/admin/app.py"
FILES = ["tests/test_strategies.py", "tests/test_solver_strategies.py",
         "tests/property/test_solve_strategies.py",
         "tests/test_puzzle_review_book_filter.py",
         "tests/test_puzzle_review_bulk_read.py", "tests/test_batch_generator.py"]
OLD = "                status=status,\n                strategy=strategy,\n"
NEW = "                status=status,\n                strategy=None,\n"
orig = APP.read_text(); BASE = hashlib.sha256(orig.encode()).hexdigest()
assert orig.count(OLD) == 1, orig.count(OLD)
def sweep():
    for b in (ROOT/"src", ROOT/"tests"):
        for d in b.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)
def run():
    sweep(); env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1"); env.pop("DATABASE_URL", None)
    p = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly",
                        *FILES, "-q", "--no-header", "-rs", "--tb=line"],
                       cwd=ROOT, capture_output=True, text=True, env=env, timeout=1800)
    sweep()
    tail = [l for l in p.stdout.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == 109, f"collected {ran}: {tail}"
    sk = sum(1 for l in p.stdout.splitlines() if l.startswith("SKIPPED"))
    return ("FAILED" if p.returncode else "PASSED"), tail, sk
print("baseline:", run())
APP.write_text(orig.replace(OLD, NEW, 1))
try:
    v, tail, sk = run()
    print(f"Y4 (route `strategy=strategy` -> `strategy=None`): {v} -> "
          f"{'KILLED' if v=='FAILED' else 'SURVIVED'} | {tail} | skipped={sk}")
finally:
    APP.write_text(orig); sweep()
    ok = hashlib.sha256(APP.read_bytes()).hexdigest() == BASE
    print("restore:", "ok" if ok else "FAILED"); assert ok
