"""CARD-337 item 0, part 3: MEASURE what CARD-329's seam closes, per module.

Not a test and not under ``tests/`` (G-8). It mutates a test module by text,
measures, and **restores from captured content** -- never ``git checkout``, so
a dirty working tree is restored to exactly what it was and not to HEAD.

The card's own ``[UNMEASURED PREMISE]`` note asks for exactly this:

    "apply the seam to the three biggest and report before/after per module
     before touching the other six"

Discipline, every item of which this board has paid for once:

* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept at **both** ends;
* SHA-256 of the file before the plant and after the restore, compared;
* the plant is applied **by text** with its occurrence count asserted to be
  exactly 1 -- a 2-occurrence replace is a different experiment;
* ``-rEfs`` as ONE flag (``-rfs`` omits ERRORs, which under-counted this
  family's census by 10%);
* ``-o addopts=`` as **two** argv items (``addopts = "-q"`` otherwise stacks to
  ``-qq`` and prints no count line);
* the whole environment is inherited, so a platform gate SKIPS for its own
  reason and not because ``PATH`` was stripped;
* a run that collects **nothing** is an ERROR, not a pass.

Run::

    python scratchpad/card337/seam_experiment.py tests/test_book_pdf_band.py
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
PROBE_PATH = ROOT / "scratchpad" / "card338"

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped|xfailed|xpassed)")
SKIP = re.compile(r"^SKIPPED \[(\d+)\] (.+)$", re.M)

#: (module, [(old, new), ...]) -- the seam, written out per module because the
#: page-source function's text differs. Derived from
#: ``derive_seam_sites.py``'s S1/S2b classes; a module it places in S3 has no
#: entry here because there is nothing to wrap.
PLANTS: dict[str, list[tuple[str, str]]] = {
    "tests/test_book_pdf_band.py": [
        (
            "from tests.helpers.pdf_pages import pdf_pages\n",
            "from tests.helpers.pdf_pages import interior_images, pdf_pages\n",
        ),
        (
            "    return BookPDFGenerator(book if book is not None else _book()).interior_pages(\n"
            "        list(puzzles)\n"
            "    )\n",
            "    return interior_images(\n"
            "        BookPDFGenerator(book if book is not None else _book()).interior_pages(\n"
            "            list(puzzles)\n"
            "        )\n"
            "    )\n",
        ),
    ],
    "tests/test_book_solved_answer_key.py": [
        (
            "from tests.helpers.page_ink import drawing_of\n",
            "from tests.helpers.page_ink import drawing_of\n"
            "from tests.helpers.pdf_pages import interior_images\n",
        ),
        (
            "    return BookPDFGenerator(book if book is not None else _book()).interior(\n"
            "        list(puzzles)\n"
            "    ).pages\n",
            "    return interior_images(\n"
            "        BookPDFGenerator(book if book is not None else _book())\n"
            "        .interior(list(puzzles))\n"
            "        .pages\n"
            "    )\n",
        ),
    ],
}


def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(rel: str) -> tuple[dict[str, int], list[tuple[str, str]], str]:
    sweep()
    argv = [
        str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rEfs",
        "--tb=line", "-p", "probe_five_kinds", rel,
    ]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=str(PROBE_PATH))
    done = subprocess.run(argv, cwd=str(ROOT), env=env,
                          capture_output=True, text=True)
    sweep()
    text = done.stdout + done.stderr
    counts = {word: int(n) for n, word in COUNT.findall(text)}
    collected = sum(counts.get(k, 0) for k in
                    ("passed", "failed", "error", "errors", "skipped",
                     "xfailed", "xpassed"))
    assert collected, f"{rel}: collected NOTHING -- a green exit is not a pass\n{text[-2500:]}"
    return counts, SKIP.findall(text), text


def red(counts: dict[str, int]) -> int:
    return counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)


def main() -> int:
    rel = sys.argv[1]
    assert rel in PLANTS, f"{rel}: no seam derived for it (S3 -- nothing to wrap)"
    path = ROOT / rel
    before_sha = digest(path)
    original = path.read_text()

    print(f"=== {rel}")
    print(f"    sha256 BEFORE plant: {before_sha}")

    base_counts, base_skips, _ = run(rel)
    print(f"    baseline (no seam):  red={red(base_counts):<4} "
          f"passed={base_counts.get('passed', 0):<5} "
          f"skipped={base_counts.get('skipped', 0)}")
    for n, why in base_skips:
        print(f"        SKIP x{n}: {why}")

    text = original
    for old, new in PLANTS[rel]:
        found = text.count(old)
        assert found == 1, (
            f"{rel}: the plant text occurs {found} times, not exactly 1 -- "
            f"a different experiment from the one this script claims\n"
            f"--- text ---\n{old}"
        )
        text = text.replace(old, new)
    path.write_text(text)
    try:
        seam_counts, seam_skips, output = run(rel)
    finally:
        # Restored from CAPTURED CONTENT, never `git checkout`: the working
        # tree here is not clean and checkout would discard a sibling change.
        path.write_text(original)
        sweep()
    after_sha = digest(path)
    print(f"    WITH seam:           red={red(seam_counts):<4} "
          f"passed={seam_counts.get('passed', 0):<5} "
          f"skipped={seam_counts.get('skipped', 0)}")
    for n, why in seam_skips:
        print(f"        SKIP x{n}: {why}")
    print(f"    sha256 AFTER restore: {after_sha}")
    assert after_sha == before_sha, (
        f"{rel}: NOT restored -- {before_sha} -> {after_sha}"
    )
    closed = red(base_counts) - red(seam_counts)
    print(f"    => the seam closes {closed} of {red(base_counts)} "
          f"({red(seam_counts)} survive)")
    survivors = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if survivors:
        survivors.write_text(output)
        print(f"    survivors' output: {survivors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
