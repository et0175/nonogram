"""R6/R7 — controls for the two FLOOR assertions the fix added.

A floor is a property of the CORPUS, so its mutant is on the corpus, not on
src/: R6 shrinks the random batch's extent back to MIN_SIZE (where every
candidate is measured to solve with the single rung), R7 swaps the second
picture for one whose ladder is measured identical to the first's. Each must
red the floor it belongs to, and no other assertion.

Protocol as before: SHA-256 of the TEST file before each plant and after each
restore, pyc sweep both ends, `-o addopts=`, collected count asserted = 1.
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
T = ROOT / "tests/test_solver_strategies.py"
C = ("tests/test_solver_strategies.py::"
     "TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::")
CASES = [
    ("R6", "    LADDER_EXTENT = 20", "    LADDER_EXTENT = MIN_SIZE",
     C + "test_a_random_batch_stores_a_real_list_for_every_row"),
    ("R7", '    IMAGES = ("bird1.jpg", "bird2.jpg")', '    IMAGES = ("bird1.jpg", "owl1.png")',
     C + "test_an_image_batch_stores_a_real_list_for_every_row"),
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sweep():
    for base in (ROOT / "src", ROOT / "tests"):
        for d in base.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)
        for f in base.rglob("*.pyc"): f.unlink(missing_ok=True)
    shutil.rmtree(ROOT / "__pycache__", ignore_errors=True)

base = sha(T)
orig = T.read_text()
print("baseline test sha256", base)
for name, old, new, node in CASES:
    assert sha(T) == base, f"{name}: test file not pristine"
    assert orig.count(old) == 1, (name, orig.count(old))
    sweep(); T.write_text(orig.replace(old, new))
    lines = T.read_text().splitlines()
    proc = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly", node,
                           "--tb=line", "-q", "--no-header"], cwd=ROOT, capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=300)
    out = proc.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == 1, (name, ran, tail)
    verdict = "FAILED" if proc.returncode else "PASSED"
    where = ""
    for line in out.splitlines():
        m = re.search(r"/(tests/test_solver_strategies\.py):(\d+): (.*)$", line)
        if m:
            where = f"{m.group(1)}:{m.group(2)} -> {lines[int(m.group(2))-1].strip()[:90]}"
            break
    print(f"{name} ({old.strip()} -> {new.strip()}): ran={ran} {verdict}  {where}")
    sweep(); T.write_text(orig)
    print(f"  {name} restore={'ok' if sha(T) == base else 'FAILED'}")
    assert sha(T) == base
sweep()
