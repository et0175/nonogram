"""CARD-318 fix round 1 — re-fire cycle 1's four mutants on AC-139.

Protocol: SHA-256 of the target asserted BEFORE each plant and AFTER each
restore; restore from the in-memory original, never `git checkout --` (which
restores to HEAD and would revert the fix, not the mutant);
PYTHONDONTWRITEBYTECODE=1 with a *.pyc/__pycache__ sweep before and after each
run; `-o addopts=` ; one cell per NODE ID, and for each run the COLLECTED
COUNT is asserted to be exactly 1 — the first version of this harness passed
`-o "addopts=''"` (quotes inside the argv entry), which pytest read as an
addopts of `''`, adding an empty path argument that collected 10,016 tests.
An exit code is not a verdict; the count and the failure cell are.
"""
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
BG = ROOT / "src/nonogram/admin/batch_generator.py"
APP = ROOT / "src/nonogram/admin/app.py"
CLASS = "tests/test_solver_strategies.py::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage"
NODES = {
    "random": f"{CLASS}::test_a_random_batch_stores_a_real_list_for_every_row",
    "image": f"{CLASS}::test_an_image_batch_stores_a_real_list_for_every_row",
}
ORIGINAL = "strategies_used=list(puzzle.strategies),"
MUTANTS = [
    ("R1", BG, 474, "strategies_used=[],"),
    ("R2", APP, 1993, "strategies_used=[],"),
    ("R3", BG, 474, "strategies_used=['simple_overlap'],"),
    ("R4", APP, 1993, "strategies_used=['simple_overlap'],"),
]
SWEEP_ROOTS = [ROOT / "src", ROOT / "tests", ROOT]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep() -> None:
    for base in SWEEP_ROOTS:
        pattern_dirs = base.rglob("__pycache__") if base is not ROOT else [ROOT / "__pycache__"]
        for d in pattern_dirs:
            shutil.rmtree(d, ignore_errors=True)
    for base in (ROOT / "src", ROOT / "tests"):
        for f in base.rglob("*.pyc"):
            f.unlink(missing_ok=True)


def run(node: str) -> tuple[str, int, str, float]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly", node, "-rN", "--no-header"],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=300,
    )
    out = proc.stdout + proc.stderr
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    verdict = "FAILED" if proc.returncode else "PASSED"
    first = ""
    for line in out.splitlines():
        if line.lstrip().startswith("E ") and "assert" in line:
            first = line.strip()[1:].strip()
            break
    if not first:
        m = re.search(r"^E\s+(\w+(?:Error|Exception).*)$", out, re.M)
        first = m.group(1) if m else ""
    secs = float(re.search(r"in ([\d.]+)s", tail).group(1)) if re.search(r"in ([\d.]+)s", tail) else -1.0
    return verdict, ran, first, secs


rows = []
print("== baseline, unmutated ==")
for label, node in NODES.items():
    sweep()
    verdict, ran, first, secs = run(node)
    print(f"  baseline {label:<7} collected={ran} {verdict} {secs}s")
    assert ran == 1, f"baseline {label}: {ran} tests ran, expected 1"
    assert verdict == "PASSED", f"baseline {label} is not green: {first}"
    sweep()

baseline = {BG: sha(BG), APP: sha(APP)}
originals = {BG: BG.read_text(), APP: APP.read_text()}
print("baseline sha256")
for path, digest in baseline.items():
    print("   ", path.name, digest)

for name, path, lineno, replacement in MUTANTS:
    assert sha(path) == baseline[path], f"{name}: target not pristine before plant"
    lines = originals[path].splitlines(keepends=True)
    before = lines[lineno - 1]
    assert ORIGINAL in before, f"{name}: line {lineno} is not the target: {before!r}"
    lines[lineno - 1] = before.replace(ORIGINAL, replacement)
    sweep()
    path.write_text("".join(lines))
    assert sha(path) != baseline[path]
    for label, node in NODES.items():
        sweep()
        verdict, ran, first, secs = run(node)
        assert ran == 1, f"{name}/{label}: {ran} tests ran, expected 1"
        rows.append((name, path.name, lineno, replacement, label, verdict, first, secs))
        print(f"  {name} {path.name}:{lineno} -> {replacement:<36} {label:<7} ran={ran} {verdict} {secs}s  {first[:100]}", flush=True)
    sweep()
    path.write_text(originals[path])
    ok = sha(path) == baseline[path]
    print(f"  {name} restore={'ok' if ok else 'FAILED'}", flush=True)
    assert ok, f"{name}: restore failed"

sweep()
print()
print("| # | site | plant | node | verdict | first failing assertion |")
print("|---|---|---|---|---|---|")
for name, fname, lineno, repl, label, verdict, first, secs in rows:
    print(f"| {name} | `{fname}:{lineno}` | `{repl}` | AC-139 {label} | **{verdict}** | {first or '—'} |")
