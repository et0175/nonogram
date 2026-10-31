"""CARD-329: what each red under the probe actually is, grouped by cause.

Not a test, not under ``tests/`` (G-7). Read-only. Same discipline as
``measure_probe.py``: environment inherited, ``-o addopts=`` as two argv
items, file-scoped calls, ``-rs``, bytecode off and swept.

Prints one line per failing node with the exception's first line, so the
card's triage classifies a module by the cause its reds carry rather than by
the module's name.
"""

from __future__ import annotations

import collections
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_probe import POPULATION_A, POPULATION_B  # noqa: E402

LINE = re.compile(r"^(\S+\.py):(\d+): (.*)$", re.M)


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def main() -> int:
    paths = sys.argv[1:] or list(POPULATION_A + POPULATION_B)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=str(Path(__file__).resolve().parent))
    for path in paths:
        sweep()
        done = subprocess.run(
            [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rs",
             "--tb=line", "-p", "probe_puzzle_operators", path],
            cwd=str(ROOT), env=env, capture_output=True, text=True,
        )
        out = done.stdout + done.stderr
        causes = collections.Counter()
        for _file, _lineno, message in LINE.findall(out):
            causes[message.strip()[:150]] += 1
        print(f"\n########## {path}")
        for message, count in causes.most_common():
            print(f"   x{count:<4} {message}")
    sweep()
    return 0


if __name__ == "__main__":
    sys.exit(main())
