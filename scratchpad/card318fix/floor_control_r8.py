"""R8 — a deterministic control for the random half's non-degeneracy floor.

R6 (extent back to MIN_SIZE) is not a deterministic control: measured, 89 of
100 10x10 candidates solve with the single rung and 4 of 10 batches are
*entirely* single-rung, so it reds about 40% of the time — which is the very
fact that disqualifies MIN_SIZE as this test's extent, but makes it a poor
mutant. R8 truncates every ladder to its first rung in the solver itself, so
the condition holds at any extent.

It is also the discriminating plant: the test's expected value is re-derived
through the same solver, so handed == derived still holds and the identity
arms stay green. Only the floor can see this one.

  src/nonogram/solver/search.py:629
    rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung]),
    -> rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung])[:1],
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
S = ROOT / "src/nonogram/solver/search.py"
NODE = ("tests/test_solver_strategies.py::"
        "TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::"
        "test_a_random_batch_stores_a_real_list_for_every_row")
OLD = "rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung]),"
NEW = "rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung])[:1],"
test_lines = (ROOT / "tests/test_solver_strategies.py").read_text().splitlines()

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sweep():
    for base in (ROOT / "src", ROOT / "tests"):
        for d in base.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)
        for f in base.rglob("*.pyc"): f.unlink(missing_ok=True)
    shutil.rmtree(ROOT / "__pycache__", ignore_errors=True)

base = sha(S)
orig = S.read_text()
print("baseline search.py sha256", base)
lines = orig.splitlines(keepends=True)
assert OLD in lines[628], repr(lines[628])
lines[628] = lines[628].replace(OLD, NEW)
sweep(); S.write_text("".join(lines))
assert sha(S) != base
for attempt in (1, 2):
    sweep()
    proc = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly", NODE,
                           "--tb=line", "-q", "--no-header"], cwd=ROOT, capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=300)
    out = proc.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == 1, (ran, tail)
    verdict = "FAILED" if proc.returncode else "PASSED"
    where = ""
    for line in out.splitlines():
        m = re.search(r"/(tests/test_solver_strategies\.py):(\d+): (.*)$", line)
        if m:
            where = f"{m.group(1)}:{m.group(2)} -> {test_lines[int(m.group(2))-1].strip()[:90]}"
            break
    print(f"R8 run{attempt}: ran={ran} {verdict}  {where}")
sweep(); S.write_text(orig)
print(f"R8 restore={'ok' if sha(S) == base else 'FAILED'}")
assert sha(S) == base
sweep()
