"""Impact set re-run.  zsh does NOT word-split unquoted vars — the first attempt
passed all six paths as ONE argv item and exited 4 with `no tests ran`, which a
`grep -c '^SKIPPED'` on the output still reports as 0.  Hence a Python runner
with asserted counts."""
import os, re, subprocess, shutil
from pathlib import Path
ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
FILES = ["tests/test_strategies.py", "tests/test_solver_strategies.py",
         "tests/property/test_solve_strategies.py",
         "tests/test_puzzle_review_book_filter.py",
         "tests/test_puzzle_review_bulk_read.py", "tests/test_batch_generator.py"]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1"); env.pop("DATABASE_URL", None)
print("DATABASE_URL in env:", "DATABASE_URL" in env)

def sweep():
    for b in (ROOT/"src", ROOT/"tests"):
        for d in b.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)

per = {}
for f in FILES:
    p = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly",
                        "--collect-only", "-q", "--no-header", f],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    n = len([l for l in p.stdout.splitlines() if "::" in l])
    per[f] = n
    print(f"  collect {n:>4}  {f}")
print("sum of per-file collected:", sum(per.values()))

sweep()
p = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly",
                    *FILES, "-rs", "-q", "--no-header"],
                   cwd=ROOT, capture_output=True, text=True, env=env, timeout=1800)
sweep()
out = p.stdout
tail = [l for l in out.splitlines() if l.strip()][-1]
print("\nrun tail:", tail)
print("exit:", p.returncode)
nums = dict((k, int(v)) for v, k in re.findall(r"(\d+) (passed|failed|error|skipped|xfailed|xpassed)", tail))
print("parsed:", nums)
skiplines = [l for l in out.splitlines() if l.startswith("SKIPPED")]
print("SKIPPED lines:", len(skiplines), skiplines[:5])
db = [l for l in out.splitlines() if "[db]" in l]
print("\nnode ids carrying [db] in collection:")
p2 = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly",
                     "--collect-only", "-q", "--no-header",
                     "tests/test_puzzle_review_bulk_read.py"],
                    cwd=ROOT, capture_output=True, text=True, env=env)
dbn = [l for l in p2.stdout.splitlines() if "[db" in l]
print("  count:", len(dbn)); print("  e.g.:", dbn[:3])
# and prove they really ran: -v on just the db ones
p3 = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly",
                     "tests/test_puzzle_review_bulk_read.py", "-k", "db", "-v",
                     "--no-header", "-rs"],
                    cwd=ROOT, capture_output=True, text=True, env=env, timeout=900)
t3 = [l for l in p3.stdout.splitlines() if l.strip()][-1]
print("\n[db]-selected run:", t3, "| exit", p3.returncode,
      "| SKIPPED:", sum(1 for l in p3.stdout.splitlines() if l.startswith("SKIPPED")))
assert "no tests ran" not in t3
