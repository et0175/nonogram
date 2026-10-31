"""Which ASSERTION fires for each mutant — per arm, not per file.

Same protocol as mutate2.py; `--tb=line` so the failing assertion's own
file:line is the output, because a test short-circuits at its first failing
assert and a FAILED cell alone does not say which arm ran.
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
BG = ROOT / "src/nonogram/admin/batch_generator.py"
APP = ROOT / "src/nonogram/admin/app.py"
C = "tests/test_solver_strategies.py::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage"
ORIGINAL = "strategies_used=list(puzzle.strategies),"
CASES = [
    ("R1", BG, 474, "strategies_used=[],", f"{C}::test_a_random_batch_stores_a_real_list_for_every_row"),
    ("R2", APP, 1993, "strategies_used=[],", f"{C}::test_an_image_batch_stores_a_real_list_for_every_row"),
    ("R3", BG, 474, "strategies_used=['simple_overlap'],", f"{C}::test_a_random_batch_stores_a_real_list_for_every_row"),
    ("R4", APP, 1993, "strategies_used=['simple_overlap'],", f"{C}::test_an_image_batch_stores_a_real_list_for_every_row"),
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sweep():
    for base in (ROOT / "src", ROOT / "tests"):
        for d in base.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)
        for f in base.rglob("*.pyc"): f.unlink(missing_ok=True)
    shutil.rmtree(ROOT / "__pycache__", ignore_errors=True)

base_sha = {BG: sha(BG), APP: sha(APP)}
orig = {BG: BG.read_text(), APP: APP.read_text()}
src_lines = {p: t.splitlines() for p, t in orig.items()}
test_lines = (ROOT / "tests/test_solver_strategies.py").read_text().splitlines()

for name, path, lineno, repl, node in CASES:
    assert sha(path) == base_sha[path]
    lines = orig[path].splitlines(keepends=True)
    lines[lineno - 1] = lines[lineno - 1].replace(ORIGINAL, repl)
    sweep(); path.write_text("".join(lines))
    proc = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly", node,
                           "--tb=line", "-q", "--no-header"], cwd=ROOT, capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=300)
    out = proc.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == 1, (name, ran, tail)
    loc = ""
    for line in out.splitlines():
        m = re.search(r"/(tests/test_solver_strategies\.py):(\d+): (.*)$", line)
        if m:
            loc = f"{m.group(1)}:{m.group(2)}"
            arm = test_lines[int(m.group(2)) - 1].strip()
            print(f"{name}: {loc}\n     arm -> {arm}\n     msg -> {m.group(3)[:160]}")
            break
    if not loc:
        print(name, "NO LOCATION", tail)
    sweep(); path.write_text(orig[path])
    assert sha(path) == base_sha[path], f"{name}: restore failed"
    print(f"  {name} restore=ok ran={ran}")
sweep()
