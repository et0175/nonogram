"""CARD-318 fix round 2 — Y1 re-fired, the control review cycle 2's F-009 wanted.

Y1 is the review's own plant: delete the `strategy = None` reset in the
unknown-strategy branch of the /puzzles route, so an unknown value IS applied
as a filter and NOTHING is listed — the refusal AC-142's `then` rules out.
Cycle 2 measured Y1 SURVIVING: the named node and 88 tests across four files
all stayed green. This re-fires it against the extended test.

Same protocol as final_mutants.py, and the same traps avoided:
  * SHA-256 of the target asserted before the plant and after the restore;
    restore from the in-memory original, never `git checkout --`.
  * __pycache__/*.pyc swept before and after every run; PYTHONDONTWRITEBYTECODE=1.
  * the plant located BY TEXT with an asserted single occurrence, never by line
    number (round 1 had hardcoded plant lines go stale under a docstring edit).
  * `-o addopts=` spelled UNQUOTED in the subprocess argv — `-o "addopts=''"`
    reads as an addopts of `''`, adds an empty path argument and collects the
    whole suite.
  * the collected count asserted on every run, because a `-k`/argv mistake
    exits 0 with nothing collected and a green exit proves nothing.
"""
import hashlib, os, re, shutil, subprocess
from pathlib import Path

ROOT = Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY_BIN = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
APP = ROOT / "src/nonogram/admin/app.py"
TEST = ROOT / "tests/test_strategies.py"

NODE = ("tests/test_strategies.py::"
        "test_the_puzzle_list_route_offers_the_filter_and_ignores_an_unknown_value")
# The four files cycle 2 fired Y1 across, where it left 88 tests green.
FOUR = ["tests/test_strategies.py", "tests/test_solver_strategies.py",
        "tests/test_puzzle_review_book_filter.py", "tests/test_puzzle_review_bulk_read.py"]

# Line-count preserving, exactly as the review spelled it.
OLD, NEW = "            strategy = None\n", "            pass\n"

original = APP.read_text()
base_sha = hashlib.sha256(original.encode()).hexdigest()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sweep():
    for b in (ROOT / "src", ROOT / "tests"):
        for d in b.rglob("__pycache__"):
            shutil.rmtree(d, ignore_errors=True)
        for f in b.rglob("*.pyc"):
            f.unlink(missing_ok=True)


def go(targets, expect):
    sweep()
    proc = subprocess.run(
        [PY_BIN, "-m", "pytest", "-o", "addopts=", "-p", "no:randomly",
         *targets, "--tb=line", "-q", "--no-header", "-rs"],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=600)
    sweep()
    out = proc.stdout
    tail = [l for l in out.splitlines() if l.strip()][-1]
    ran = sum(int(n) for n in re.findall(r"(\d+) (?:passed|failed|error)", tail))
    assert ran == expect, f"{ran} collected, expected {expect}\n{tail}"
    skipped = sum(1 for l in out.splitlines() if l.startswith("SKIPPED"))
    lineno, arm = 0, ""
    for line in out.splitlines():
        m = re.search(r"/tests/test_strategies\.py:(\d+): ", line)
        if m:
            lineno = int(m.group(1))
            arm = TEST.read_text().splitlines()[lineno - 1].strip()
            break
    return ("FAILED" if proc.returncode else "PASSED"), ran, skipped, lineno, arm, tail


print("target sha256 before plant:", base_sha)
assert sha(APP) == base_sha

print("\n-- baseline, unmutated --")
for label, targets, expect in (("named node", [NODE], 1), ("four files", FOUR, 88)):
    v, ran, sk, ln, arm, tail = go(targets, expect)
    print(f"  {label:<11} collected={ran} skipped={sk} {v:<7} {tail}")
    assert v == "PASSED", f"baseline not green for {label}"

print("\n-- Y1 planted: `strategy = None` -> `pass` at app.py --")
hits = [i for i, l in enumerate(original.splitlines(keepends=True)) if l == OLD]
assert len(hits) == 1, hits
print(f"  located by text at app.py:{hits[0] + 1}")
APP.write_text(original.replace(OLD, NEW, 1))
assert sha(APP) != base_sha
try:
    for label, targets, expect in (("named node", [NODE], 1), ("four files", FOUR, 88)):
        v, ran, sk, ln, arm, tail = go(targets, expect)
        verdict = "KILLED " if v == "FAILED" else "SURVIVED"
        print(f"  {label:<11} collected={ran} skipped={sk} {v:<7} {verdict} "
              f"line={ln or '-'} {arm[:80]}")
        print(f"              {tail}")
finally:
    APP.write_text(original)
    sweep()
    ok = sha(APP) == base_sha
    print(f"\nrestore app.py = {'ok' if ok else 'FAILED'}; sha256 after restore: {sha(APP)}")
    assert ok
