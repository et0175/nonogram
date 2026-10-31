"""CARD-318 fix round 2 — the new assertion discriminates, it is not a tautology.

Y1 (in y1_control.py) shows the assertion CAN fail. These two cells show it
fails for the right reason and that it has not made the flash assertion
redundant:

  Y2  the UNRELATED branch is broken instead — the CARD-066 status reset at the
      same route, same shape, three lines up. AC-142's node must stay GREEN:
      a control that reds on any edit to this route would not be evidence
      about the strategy filter.
  Y3  the reset is KEPT and only the flash's wording changes. The flash
      assertion must red and the listing assertion must stay green, i.e. the
      two assertions observe different things and neither is absorbed by the
      other.

Protocol identical to y1_control.py / final_mutants.py.
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY_BIN = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
APP = ROOT / "src/nonogram/admin/app.py"
TEST = ROOT / "tests/test_strategies.py"
NODE = ("tests/test_strategies.py::"
        "test_the_puzzle_list_route_offers_the_filter_and_ignores_an_unknown_value")

CELLS = [
    ("Y2", "            status = None\n", "            pass\n", "PASSED"),
    ("Y3", 'f"Unknown strategy {strategy!r} — showing every strategy instead",\n',
           'f"Unrecognised strategy {strategy!r} — showing every strategy instead",\n',
     "FAILED"),
]

original = APP.read_text()
base = hashlib.sha256(original.encode()).hexdigest()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sweep():
    for b in (ROOT / "src", ROOT / "tests"):
        for d in b.rglob("__pycache__"):
            shutil.rmtree(d, ignore_errors=True)
        for f in b.rglob("*.pyc"):
            f.unlink(missing_ok=True)


def go():
    sweep()
    proc = subprocess.run(
        [PY_BIN, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly", NODE,
         "--tb=line", "-q", "--no-header"],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=300)
    sweep()
    out = proc.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == 1, f"{ran} collected, expected 1\n{tail}"
    ln, arm = 0, ""
    for line in out.splitlines():
        m = re.search(r"/tests/test_strategies\.py:(\d+): ", line)
        if m:
            ln = int(m.group(1))
            arm = TEST.read_text().splitlines()[ln - 1].strip()
            break
    return ("FAILED" if proc.returncode else "PASSED"), ran, ln, arm


for name, old, new, expect in CELLS:
    assert sha(APP) == base, f"{name}: app.py not pristine before plant"
    hits = original.count(old)
    assert hits == 1, (name, old, hits)
    at = original[:original.index(old)].count("\n") + 1
    APP.write_text(original.replace(old, new, 1))
    assert sha(APP) != base
    try:
        v, ran, ln, arm = go()
    finally:
        APP.write_text(original)
        sweep()
        assert sha(APP) == base, f"{name}: restore FAILED"
    print(f"  {name} app.py:{at} collected={ran} {v:<7} expected={expect} "
          f"{'OK' if v == expect else 'UNEXPECTED'} line={ln or '-'} {arm[:72]}")
    assert v == expect, f"{name}: got {v}, expected {expect}"
    print(f"     restore ok, sha256 = {sha(APP)}")
