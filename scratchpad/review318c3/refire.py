"""CARD-318 review cycle 3 — Y1/Y2/Y3 re-fired, independently of the fix round.

Protocol (independently written, same discipline):
  * SHA-256 of app.py asserted before plant and after restore; restore from the
    in-memory original, never git checkout.
  * __pycache__/*.pyc swept both ends; PYTHONDONTWRITEBYTECODE=1.
  * plants located BY TEXT, single occurrence asserted; never by line number.
  * `-o addopts=` as two UNQUOTED argv items.
  * collected count asserted on every run; `0 skipped` asserted on the baseline.
  * full environment inherited (dict(os.environ, ...)) — a stripped PATH has
    silently skipped whole files on this board.
"""
import hashlib, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
APP = ROOT / "src/nonogram/admin/app.py"
TEST = ROOT / "tests/test_strategies.py"

NODE = ("tests/test_strategies.py::"
        "test_the_puzzle_list_route_offers_the_filter_and_ignores_an_unknown_value")

PLANTS = {
    # Y1 — the strategy reset removed: an unknown value really filters.
    "Y1": ("            strategy = None\n", "            pass\n"),
    # Y2 — the UNRELATED CARD-066 status reset removed, same shape, 3 lines up.
    "Y2": ("            status = None\n", "            pass\n"),
    # Y3 — flash wording changed, the reset kept.
    "Y3": ('f"Unknown strategy {strategy!r} — showing every strategy instead",\n',
           'f"Strategy {strategy!r} is not in the vocabulary — showing all",\n'),
}

original = APP.read_text()
BASE = hashlib.sha256(original.encode()).hexdigest()


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def sweep():
    for b in (ROOT / "src", ROOT / "tests"):
        for d in b.rglob("__pycache__"):
            shutil.rmtree(d, ignore_errors=True)
        for f in b.rglob("*.pyc"):
            f.unlink(missing_ok=True)


def run(targets, expect):
    sweep()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("DATABASE_URL", None)
    p = subprocess.run(
        [PY, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly",
         *targets, "--tb=line", "-q", "--no-header", "-rs"],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=900)
    sweep()
    out = p.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == expect, f"collected {ran}, expected {expect}\n{tail}"
    nskip = sum(1 for l in out.splitlines() if l.startswith("SKIPPED"))
    where = ""
    for line in out.splitlines():
        m = re.search(r"test_strategies\.py:(\d+): ", line)
        if m:
            n = int(m.group(1))
            where = f"{n}: {TEST.read_text().splitlines()[n-1].strip()[:70]}"
            break
    return ("FAILED" if p.returncode else "PASSED"), ran, nskip, where, tail


print("app.py sha256:", BASE)
assert sha(APP) == BASE

print("\n== baselines (unmutated) ==")
v, ran, sk, w, tail = run([NODE], 1)
print(f"  named node   collected={ran} skipped={sk} {v}  | {tail}")
assert v == "PASSED" and sk == 0, "baseline must be green with 0 skipped"
v, ran, sk, w, tail = run(["tests/test_strategies.py"], 17)
print(f"  whole file   collected={ran} skipped={sk} {v}  | {tail}")
assert v == "PASSED" and sk == 0, "baseline must be green with 0 skipped"

results = {}
for name, (old, new) in PLANTS.items():
    hits = original.count(old)
    assert hits == 1, f"{name}: {hits} occurrences of the anchor"
    idx = original[:original.index(old)].count("\n") + 1
    print(f"\n== {name} planted by text at app.py:{idx} ==")
    APP.write_text(original.replace(old, new, 1))
    assert sha(APP) != BASE
    try:
        v, ran, sk, w, tail = run([NODE], 1)
        verdict = "KILLED" if v == "FAILED" else "SURVIVED"
        print(f"  named node   collected={ran} skipped={sk} {v} -> {verdict}")
        print(f"               fail site: {w or '-'}")
        print(f"               {tail}")
        results[name] = (verdict, w)
    finally:
        APP.write_text(original)
        sweep()
        assert sha(APP) == BASE, "RESTORE FAILED"
        print(f"  restored, sha256 ok")

print("\n== summary ==")
for k, (verdict, w) in results.items():
    print(f"  {k}: {verdict}  {w}")
print("\nfinal sha256:", sha(APP), "== base:", sha(APP) == BASE)
