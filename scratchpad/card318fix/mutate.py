"""CARD-318 fix round 1 — re-fire cycle 1's four mutants on AC-139.

Protocol (the card's, unchanged): SHA-256 of the target asserted BEFORE each
plant and AFTER each restore; restore from the in-memory original, never
`git checkout --` (which restores to HEAD and would revert the fix, not the
mutant); PYTHONDONTWRITEBYTECODE=1 with a *.pyc/__pycache__ sweep before and
after each run; -o addopts=''; one cell per NODE ID, and for a failing node
the first failing assertion is recorded, because a test short-circuits.
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
BG = ROOT / "src/nonogram/admin/batch_generator.py"
APP = ROOT / "src/nonogram/admin/app.py"
NODES = {
    "random": "tests/test_solver_strategies.py::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::test_a_random_batch_stores_a_real_list_for_every_row",
    "image": "tests/test_solver_strategies.py::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::test_an_image_batch_stores_a_real_list_for_every_row",
}
ORIGINAL = "strategies_used=list(puzzle.strategies),"

MUTANTS = [
    ("R1", BG, 474, "strategies_used=[],"),
    ("R2", APP, 1993, "strategies_used=[],"),
    ("R3", BG, 474, "strategies_used=['simple_overlap'],"),
    ("R4", APP, 1993, "strategies_used=['simple_overlap'],"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep() -> None:
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)
    for f in ROOT.rglob("*.pyc"):
        f.unlink(missing_ok=True)


def run(node: str) -> tuple[str, str]:
    proc = subprocess.run(
        [PY, "-m", "pytest", "-o", "addopts=''", "-p", "no:randomly", node, "-x"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(Path.home())},
    )
    out = proc.stdout + proc.stderr
    verdict = "FAILED" if proc.returncode else "PASSED"
    # the first failing assertion line, as pytest prints it (E   assert ...)
    first = ""
    for line in out.splitlines():
        if line.startswith("E       assert") or line.startswith("E         assert"):
            first = line.strip()[2:].strip()
            break
    if not first:
        m = re.search(r"^E\s+(\w+Error.*)$", out, re.M)
        first = m.group(1) if m else ""
    return verdict, first


baseline = {BG: sha(BG), APP: sha(APP)}
originals = {BG: BG.read_text(), APP: APP.read_text()}
for path, text in originals.items():
    assert text.splitlines()[0] is not None

print("baseline sha256")
for path, digest in baseline.items():
    print("   ", path.name, digest)

rows = []
for name, path, lineno, replacement in MUTANTS:
    assert sha(path) == baseline[path], f"{name}: target not pristine before plant"
    lines = originals[path].splitlines(keepends=True)
    before = lines[lineno - 1]
    assert ORIGINAL in before, f"{name}: line {lineno} is not the target: {before!r}"
    lines[lineno - 1] = before.replace(ORIGINAL, replacement)
    sweep()
    path.write_text("".join(lines))
    planted = sha(path)
    assert planted != baseline[path]
    for label, node in NODES.items():
        sweep()
        verdict, first = run(node)
        rows.append((name, path.name, lineno, replacement, label, verdict, first))
        print(f"  {name} {path.name}:{lineno} -> {replacement:<40} {label:<7} {verdict}  {first[:110]}")
    sweep()
    path.write_text(originals[path])
    restored = sha(path) == baseline[path]
    print(f"  {name} restore={'ok' if restored else 'FAILED'}")
    assert restored, f"{name}: restore failed"

sweep()
print()
print("| # | site | plant | node | verdict | first failing assertion |")
print("|---|---|---|---|---|---|")
for name, fname, lineno, repl, label, verdict, first in rows:
    print(f"| {name} | `{fname}:{lineno}` | `{repl}` | AC-139 {label} | **{verdict}** | {first or '—'} |")
