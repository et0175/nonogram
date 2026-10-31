"""CARD-318 fix round 1 — the whole mutant set, re-fired on the COMMITTED code.

One cell per (plant, node id). For every run the collected count is asserted
to be exactly 1 and the failing assertion's own line is recorded, because a
test short-circuits at its first failing assert and a FAILED cell alone says
nothing about the arms that never ran.

Protocol: SHA-256 of every target asserted before each plant and after each
restore; restore from the in-memory original (never `git checkout --`, which
restores to HEAD); *.pyc/__pycache__ swept before and after each run;
`-o addopts=` (NOT `-o "addopts=''"` — that reads as an addopts of `''`, adds
an empty path argument and collects 10,016 tests, which is how the first run
of this harness came to run most of the suite).
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
BG = ROOT / "src/nonogram/admin/batch_generator.py"
APP = ROOT / "src/nonogram/admin/app.py"
PR = ROOT / "src/nonogram/admin/puzzle_review.py"
SEARCH = ROOT / "src/nonogram/solver/search.py"
TEST = ROOT / "tests/test_solver_strategies.py"
C = ("tests/test_solver_strategies.py::"
     "TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::")
RANDOM, IMAGE = C + "test_a_random_batch_stores_a_real_list_for_every_row", C + "test_an_image_batch_stores_a_real_list_for_every_row"
HAND = "strategies_used=list(puzzle.strategies),"

FILES = [BG, APP, PR, SEARCH, TEST]
orig = {p: p.read_text() for p in FILES}
base = {p: hashlib.sha256(orig[p].encode()).hexdigest() for p in FILES}

# (name, [(file, lineno, old, new)], [nodes], note)
PLANTS = [
    ("R1", [(BG, 474, HAND, "strategies_used=[],")], [("random", RANDOM), ("image", IMAGE)]),
    ("R2", [(APP, 1993, HAND, "strategies_used=[],")], [("random", RANDOM), ("image", IMAGE)]),
    ("R3", [(BG, 474, HAND, "strategies_used=['simple_overlap'],")], [("random", RANDOM), ("image", IMAGE)]),
    ("R4", [(APP, 1993, HAND, "strategies_used=['simple_overlap'],")], [("random", RANDOM), ("image", IMAGE)]),
    ("R5a", [(PR, 946, "if not strategies_used:", "if True:                 ")], [("random", RANDOM)]),
    ("R5b", [(PR, 946, "if not strategies_used:", "if True:                 "),
             (BG, 474, HAND, "strategies_used=['simple_overlap'],")], [("random", RANDOM)]),
    ("R6", [(TEST, 458, "LADDER_EXTENT = 20", "LADDER_EXTENT = MIN_SIZE")], [("random", RANDOM)]),
    ("R7", [(TEST, 469, 'IMAGES = ("bird1.jpg", "bird2.jpg")', 'IMAGES = ("bird1.jpg", "owl1.png")')], [("image", IMAGE)]),
    ("R8", [(SEARCH, 629, "rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung]),",
             "rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung])[:1],")], [("random", RANDOM)]),
]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def sweep():
    for b in (ROOT / "src", ROOT / "tests"):
        for d in b.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)
        for f in b.rglob("*.pyc"): f.unlink(missing_ok=True)
    shutil.rmtree(ROOT / "__pycache__", ignore_errors=True)


def go(node):
    proc = subprocess.run([PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly", node,
                           "--tb=line", "-q", "--no-header"], cwd=ROOT, capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=300)
    out = proc.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    verdict = "FAILED" if proc.returncode else "PASSED"
    lineno, arm = 0, ""
    for line in out.splitlines():
        m = re.search(r"/tests/test_solver_strategies\.py:(\d+): ", line)
        if m:
            lineno = int(m.group(1))
            arm = TEST.read_text().splitlines()[lineno - 1].strip()
            break
    return verdict, ran, lineno, arm


rows = []
for name, plants, nodes in PLANTS:
    for p, *_ in plants:
        assert sha(p) == base[p], f"{name}: {p.name} not pristine before plant"
    sweep()
    for p, lineno, old, new in plants:
        lines = orig[p].splitlines(keepends=True)
        # The line is LOCATED by its text and the hardcoded number is checked
        # against it, so a plant can never land on a line that moved.
        hits = [i for i, l in enumerate(lines) if old in l]
        assert len(hits) == 1, (name, p.name, old, hits)
        if hits[0] + 1 != lineno:
            print(f"  note: {name} {p.name} target moved {lineno} -> {hits[0] + 1}")
        lineno = hits[0] + 1
        lines[lineno - 1] = lines[lineno - 1].replace(old, new)
        p.write_text("".join(lines))
        assert sha(p) != base[p]
    for label, node in nodes:
        sweep()
        verdict, ran, lineno, arm = go(node)
        assert ran == 1, f"{name}/{label}: {ran} collected, expected 1"
        rows.append((name, plants, label, verdict, ran, lineno, arm))
        print(f"  {name:<4} {label:<7} collected={ran} {verdict:<7} line={lineno or '-':<5} {arm[:88]}", flush=True)
    sweep()
    for p, *_ in plants:
        p.write_text(orig[p])
        ok = sha(p) == base[p]
        print(f"  {name} restore {p.name}={'ok' if ok else 'FAILED'}", flush=True)
        assert ok
sweep()
print("\nall targets pristine:", all(sha(p) == base[p] for p in FILES))
print("sha256 of every target, after the last restore:")
for p in FILES:
    print("   ", p.relative_to(ROOT), sha(p))
