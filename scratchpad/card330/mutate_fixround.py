"""CARD-330 fix-round mutant driver (cycle 1 -> cycle 2).

Each mutant carries TWO anchors: ``pre`` for the file as it stood at cycle 1's
HEAD (54e9e553) and ``post`` for the fixed file. Run

    python scratchpad/card330/mutate_fixround.py pre
    python scratchpad/card330/mutate_fixround.py post

The ``pre`` phase is the MATCHED CONTROL: it shows which of these plants the
suite absorbed before the fix. Both phases need a committed, clean tree --
``git checkout --`` restores to HEAD and would discard uncommitted work (for
the ``pre`` phase the fix is kept in ``git stash``, not in the working tree).
Anchors are located by TEXT and asserted unique; never by line number.
"""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-330")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"

MODULE = "tests/test_book_pdf.py"
EDGE = [MODULE, "-k", "EdgeOffset"]
PIN = [MODULE + "::TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium"]

_RIGHT_HAND = (
    "        page = _mirrored_pages()[FIRST_PUZZLE_PAGE]  # interior page 7, right-hand\n"
    "\n"
    "        left_mm = _mm(drawing_of(page).left)\n"
)
_LEFT_HAND = (
    "        page = _mirrored_pages()[FIRST_PUZZLE_PAGE - 1]"
    "  # interior page 6, left-hand (CARD-206)\n"
    "\n"
    "        left_mm = _mm(drawing_of(page).left)\n"
)
_STREAM = "        left_mm = _mm(pdf_vector.content_streams(page))\n"

# (id, finding, file, args, {phase: (old, new)}, region, note)
MUTANTS = [
    (
        "R1", "F-001", MODULE, EDGE,
        {
            "pre": ("_MIN_EDGE_CASES = 24", "_MIN_EDGE_CASES = 3"),
            "post": ("_EDGE_CASE_COUNT = 24", "_EDGE_CASE_COUNT = 3"),
        },
        "inside",
        "the corpus shrinks to 3 cases and the floor is not touched",
    ),
    (
        "R2", "F-001", MODULE, EDGE,
        {
            "pre": ("_MIN_EDGE_CASES = 24", "_MIN_EDGE_CASES = 23"),
            "post": ("_EDGE_CASE_COUNT = 24", "_EDGE_CASE_COUNT = 23"),
        },
        "edge",
        "the smallest shrink there is: one case fewer",
    ),
    (
        "R3", "F-001", MODULE, EDGE,
        {
            "pre": ("_MIN_EDGE_CASES = 24", "_MIN_EDGE_CASES = 12"),
            "post": ("_MIN_EDGE_CASES = 24", "_MIN_EDGE_CASES = 12"),
        },
        "edge",
        "the FLOOR itself halved, which is the move G-5 forbids the next card",
    ),
    (
        "R4", "F-002", MODULE, PIN,
        {
            "pre": (_RIGHT_HAND, _RIGHT_HAND.replace(
                "        left_mm = _mm(drawing_of(page).left)\n", _STREAM)),
            "post": (_RIGHT_HAND, _RIGHT_HAND.replace(
                "        left_mm = _mm(drawing_of(page).left)\n", _STREAM)),
        },
        "inside",
        "the FIRST of the two same-named placed-edge sites starts reading a content stream",
    ),
    (
        "R5", "F-002", MODULE, PIN,
        {
            "pre": (_LEFT_HAND, _LEFT_HAND.replace(
                "        left_mm = _mm(drawing_of(page).left)\n", _STREAM)),
            "post": (_LEFT_HAND, _LEFT_HAND.replace(
                "        left_mm = _mm(drawing_of(page).left)\n", _STREAM)),
        },
        "edge",
        "the SECOND of the pair, identical change -- the control that makes R4 a measurement",
    ),
    (
        "R6", "F-002", MODULE, PIN,
        {
            "post": (
                '                                "::".join(prefix + (child.name,)),',
                "                                child.name,",
            ),
        },
        "inside",
        "the key goes back to the bare function name (post only: it mutates the fix itself)",
    ),
    (
        "R7", "F-003", MODULE, EDGE,
        {
            "pre": (
                "        specified={key: specified[key] for key in _GRID_EDGES + _DRAWING_EDGES},",
                "        specified={key: specified[key] + 0.3 / PX_PER_MM"
                " for key in _GRID_EDGES + _DRAWING_EDGES},",
            ),
            "post": (
                "        specified={key: specified[key] for key in _GRID_EDGES + _DRAWING_EDGES},",
                "        specified={key: specified[key] + 0.3 / PX_PER_MM"
                " for key in _GRID_EDGES + _DRAWING_EDGES},",
            ),
        },
        "inside",
        "the derived column moves 0.3 px, so the worst spec-vs-stream gap is 1.3 px",
    ),
    (
        "R8", "F-003", MODULE, EDGE,
        {
            "pre": (
                "        specified={key: specified[key] for key in _GRID_EDGES + _DRAWING_EDGES},",
                "        specified={key: specified[key] + 0.06 / PX_PER_MM"
                " for key in _GRID_EDGES + _DRAWING_EDGES},",
            ),
            "post": (
                "        specified={key: specified[key] for key in _GRID_EDGES + _DRAWING_EDGES},",
                "        specified={key: specified[key] + 0.06 / PX_PER_MM"
                " for key in _GRID_EDGES + _DRAWING_EDGES},",
            ),
        },
        "edge",
        "0.06 px: the smallest move the measured bound catches and the derived one absorbed",
    ),
]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep() -> None:
    for pyc in ROOT.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [PY, "-m", "pytest", *args, "-o", "addopts=", "-p", "no:randomly", "--tb=no", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    tail = proc.stdout.strip().splitlines()
    return proc.returncode, (tail[-1] if tail else proc.stderr[-300:])


def main() -> None:
    phase = sys.argv[1]
    assert phase in {"pre", "post"}, phase
    clean = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout.strip()
    assert not clean, f"tracked tree is NOT clean: {clean!r}"
    for ident, finding, rel, args, anchors, region, note in MUTANTS:
        if phase not in anchors:
            print(f"{ident:3} {'N/A':9} {finding} ({region}) -- no {phase} anchor: {note}")
            continue
        old, new = anchors[phase]
        target = ROOT / rel
        before = sha(target)
        sweep()
        text = target.read_text(encoding="utf-8")
        assert text.count(old) == 1, (ident, phase, "anchor not unique", text.count(old))
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        assert sha(target) != before, (ident, "the mutant did not change the file")
        code, summary = run(args)
        sweep()
        subprocess.run(["git", "checkout", "--", rel], cwd=ROOT, check=True)
        assert sha(target) == before, (ident, "restore did not return the file")
        sweep()
        verdict = "KILLED" if code != 0 else "SURVIVED"
        print(f"{ident:3} {verdict:9} {finding} ({region})  {summary}")
        print(f"     {note}")


if __name__ == "__main__":
    main()
