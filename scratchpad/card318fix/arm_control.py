"""R5 — the control for the hand-off IDENTITY arm (tests/...:517).

R3/R4 red at the ROW identity arm (:503), because a non-empty hand-off is
echoed by the store, so the row sees the wrong value first. That leaves the
hand-off identity assertion without a mutant of its own. The scenario it
exists for is a store that STOPS echoing — then the row is right and only the
hand-off can see the wrong caller. Planted as two lines, which is the whole
point: one line cannot express it.

  R5a  puzzle_review.py:946  `if not strategies_used:` -> `if True:`   (alone)
  R5b  R5a + batch_generator.py:474 -> strategies_used=['simple_overlap']

Same protocol: SHA-256 before each plant and after each restore, pyc sweep
both ends, `-o addopts=`, collected count asserted to be 1.
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
BG = ROOT / "src/nonogram/admin/batch_generator.py"
PR = ROOT / "src/nonogram/admin/puzzle_review.py"
NODE = ("tests/test_solver_strategies.py::"
        "TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::"
        "test_a_random_batch_stores_a_real_list_for_every_row")
test_lines = (ROOT / "tests/test_solver_strategies.py").read_text().splitlines()

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sweep():
    for base in (ROOT / "src", ROOT / "tests"):
        for d in base.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)
        for f in base.rglob("*.pyc"): f.unlink(missing_ok=True)
    shutil.rmtree(ROOT / "__pycache__", ignore_errors=True)

base_sha = {BG: sha(BG), PR: sha(PR)}
orig = {BG: BG.read_text(), PR: PR.read_text()}

def plant(path, lineno, old, new):
    lines = orig[path].splitlines(keepends=True)
    assert old in lines[lineno - 1], (path.name, lineno, lines[lineno - 1])
    lines[lineno - 1] = lines[lineno - 1].replace(old, new)
    path.write_text("".join(lines))

def go(label):
    proc = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly", NODE,
                           "--tb=line", "-q", "--no-header"], cwd=ROOT, capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=300)
    out = proc.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == 1, (label, ran, tail)
    verdict = "FAILED" if proc.returncode else "PASSED"
    where = ""
    for line in out.splitlines():
        m = re.search(r"/(tests/test_solver_strategies\.py):(\d+): (.*)$", line)
        if m:
            where = f"{m.group(1)}:{m.group(2)} -> {test_lines[int(m.group(2))-1].strip()}  [{m.group(3)[:80]}]"
            break
    print(f"{label}: ran={ran} {verdict} {where}")

for path, digest in base_sha.items():
    print("baseline", path.name, digest)

# R5a — the store stops echoing, call sites pristine
assert sha(PR) == base_sha[PR]
sweep(); plant(PR, 946, "if not strategies_used:", "if True:                 ")
go("R5a store-always-derives, call sites pristine")

# R5b — same store, plus the constant at the random call site
assert sha(BG) == base_sha[BG]
sweep(); plant(BG, 474, "strategies_used=list(puzzle.strategies),", "strategies_used=['simple_overlap'],")
go("R5b store-always-derives + constant hand-off")

sweep()
for path in (BG, PR):
    path.write_text(orig[path])
    print(f"restore {path.name}={'ok' if sha(path) == base_sha[path] else 'FAILED'}")
    assert sha(path) == base_sha[path]
sweep()
