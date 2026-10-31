"""CARD-329 AC-4: run both reader populations under the declaration-lifting
probe and report per-module red counts, with every skip attributed by reason.

Not a test and not under ``tests/`` (G-7). Run from the worktree root.

This is the measurement whose absence made AC-4 vacuous: on ``main`` nothing
is converted, so "all 21 modules pass" was satisfied by an empty diff. Under
the probe the puzzle page is operators, so the criterion can fail.

Discipline (every item has cost this board a round):

* the full environment is inherited (``dict(os.environ, ...)``) -- a stripped
  ``PATH`` makes a platform-gated test SKIP, which reads as a pass;
* ``-o addopts=`` as **two** argv items, never one quoted string;
* every call is file-scoped, and a zero collected count is an ERROR, not a
  pass (``-k`` selecting nothing exits 0);
* ``-rs`` on every call, and skips are reported with the reason the gate
  printed rather than named from memory (two different DB gates exist here);
* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept both ends.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
PROBE = "probe_puzzle_operators"

# Population A, derived by scratchpad/card329/derive_populations.py:
# ImportFrom tests.helpers.pdf_pages naming `pdf_pages`, the one-image reader.
POPULATION_A = (
    "tests/property/test_book_export_interior.py",
    "tests/test_book_arrange_page_breaks.py",
    "tests/test_book_export_interior_cover.py",
    "tests/test_book_guide_page.py",
    "tests/test_book_interior_face.py",
    "tests/test_book_pdf.py",
    "tests/test_book_pdf_band.py",
    "tests/test_book_pdf_ink_mode.py",
    "tests/test_book_pdf_memory.py",
    "tests/test_book_proof_pages.py",
    "tests/test_book_solved_answer_key.py",
    "tests/test_book_trim_persistence.py",
)

# Population B \ A, same deriver: a page from interior()/interior_pages() is
# used as an image downstream, directly or through a page-consuming helper.
# book_corpus.py is a helper with no test nodes of its own -- it is in the
# population and is exercised through every module that imports it.
POPULATION_B = (
    "tests/property/test_book_pairing.py",
    "tests/property/test_book_pdf_geometry.py",
    "tests/test_book_cell_size.py",
    "tests/test_book_difficulty_dots.py",
    "tests/test_book_divider_pages_option.py",
    "tests/test_book_pdf_levels.py",
    "tests/test_book_pdf_two_up.py",
    "tests/test_book_puzzle_frame.py",
)
B_HELPER = ("tests/helpers/book_corpus.py",)

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped|xfailed|xpassed)")
SKIP_LINE = re.compile(r"^SKIPPED \[(\d+)\] (.+)$", re.M)


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run(paths: tuple[str, ...], *, probe: bool) -> tuple[int, str]:
    sweep()
    argv = [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rs", "--tb=no"]
    if probe:
        argv += ["-p", PROBE]
    argv += list(paths)
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(Path(__file__).resolve().parent),
    )
    done = subprocess.run(
        argv, cwd=str(ROOT), env=env, capture_output=True, text=True
    )
    sweep()
    return done.returncode, done.stdout + done.stderr


def tally(text: str) -> dict[str, int]:
    return {word: int(number) for number, word in COUNT.findall(text)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-probe", action="store_true")
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()
    probe = not args.no_probe

    modules = args.only or (POPULATION_A + POPULATION_B)
    label = "UNDER THE PROBE" if probe else "AS COMMITTED (no probe)"
    print(f"=== {label}: {len(modules)} modules, one run each\n")

    rows = []
    for path in modules:
        code, out = run((path,), probe=probe)
        counts = tally(out)
        collected = sum(
            counts.get(k, 0)
            for k in ("passed", "failed", "error", "errors", "skipped",
                      "xfailed", "xpassed")
        )
        assert collected, f"{path}: collected NOTHING -- a green exit is not a pass\n{out}"
        skips = SKIP_LINE.findall(out)
        rows.append((path, code, counts, skips))
        red = counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)
        mark = "RED " if red else "green"
        print(f"{mark} {path:52} {counts}")
        for number, reason in skips:
            print(f"        SKIP x{number}: {reason}")

    total_red = sum(
        c.get("failed", 0) + c.get("error", 0) + c.get("errors", 0)
        for _, _, c, _ in rows
    )
    total_pass = sum(c.get("passed", 0) for _, _, c, _ in rows)
    total_skip = sum(c.get("skipped", 0) for _, _, c, _ in rows)
    reds = [p for p, _, c, _ in rows
            if c.get("failed", 0) + c.get("error", 0) + c.get("errors", 0)]
    print(f"\n=== {label}")
    print(f"    modules red: {len(reds)} / {len(rows)}")
    print(f"    failed+error: {total_red}   passed: {total_pass}   skipped: {total_skip}")
    for path in reds:
        print(f"    RED {path}")
    sweep()
    return 0


if __name__ == "__main__":
    sys.exit(main())
