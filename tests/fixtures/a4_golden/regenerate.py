"""Capture CARD-113's golden A4 fixtures from the code as it is checked out.

    ./.venv/bin/python -m tests.fixtures.a4_golden.regenerate --capture-from-clean-src

Run from the repository root. It writes ``layout.json`` and ``cli_exports.json``
beside this file, each headed with the commit it was captured from.

**This is not how a red golden test is fixed** (CARD-113 G-3). The goldens were
captured once, from ``main`` at CARD-113's base commit, *before* any
``PageSpec`` change, and they are the "before" side of CON-019/ADR-0036/R1: a
red golden test means a change moved the A4 geometry or the CLI/web bytes, and
the fix belongs in that change. Re-capturing is legitimate only for a
deliberate, reviewed change to today's A4 output (or to the renderer's
dependencies, e.g. a Pillow upgrade that re-encodes the JPEG inside the PDF),
and then the commit doing it says so.

Two guards make the accidental case harder:

* it refuses to run while ``src/`` has uncommitted changes — a golden has to
  name the commit it came from, and a dirty tree has no such commit;
* it refuses without ``--capture-from-clean-src``, so it cannot be run by
  reflex.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import platform
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import PIL

from nonogram import cli
from nonogram.clues import compute_clues
from nonogram.export.layout import ClueEntry, GridLine, Layout, compute_layout
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.fixtures.a4_golden import golden
from tests.property import test_cli_exports_byte_identity as ec020

REPO_ROOT = golden.FIXTURE_DIR.parents[2]
COMMAND = "./.venv/bin/python -m tests.fixtures.a4_golden.regenerate --capture-from-clean-src"

#: The layout corpus's own seed.
LAYOUT_SEED = 20260922

#: Extents every pattern is laid out at: the band's corners, its middle, and
#: the comfort curve's decided points (NFR-005).
_ANCHOR_EXTENTS: tuple[tuple[int, int], ...] = (
    (MIN_SIZE, MIN_SIZE),
    (MAX_SIZE, MAX_SIZE),
    (MIN_SIZE, MAX_SIZE),
    (MAX_SIZE, MIN_SIZE),
    (15, 15),
    (20, 20),
    (25, 25),
)

#: How many further extents to draw at random, each with a random pattern.
_DRAWN_EXTENTS = 25

type Grid = list[list[bool]]


def _random(width: int, height: int, rng: random.Random) -> Grid:
    density = rng.uniform(0.3, 0.8)
    return [[rng.random() < density for _ in range(width)] for _ in range(height)]


def _checkerboard(width: int, height: int, rng: random.Random) -> Grid:
    return [[(row + column) % 2 == 0 for column in range(width)] for row in range(height)]


def _alternating_rows(width: int, height: int, rng: random.Random) -> Grid:
    return [[row % 2 == 0] * width for row in range(height)]


def _alternating_columns(width: int, height: int, rng: random.Random) -> Grid:
    return [[column % 2 == 0 for column in range(width)] for _ in range(height)]


def _sparse(width: int, height: int, rng: random.Random) -> Grid:
    grid = [[False] * width for _ in range(height)]
    grid[rng.randrange(height)][rng.randrange(width)] = True
    return grid


#: Clue patterns spanning both gutter extremes: deep row gutters
#: (``alternating_columns``), deep column gutters (``alternating_rows``), both
#: (``checkerboard``), neither (``sparse``), and ordinary puzzles (``random``).
#: Together with the extents they reach both NFR-006 orientations and both
#: NFR-005 regimes; the golden test asserts that they do.
_PATTERNS = {
    "random": _random,
    "checkerboard": _checkerboard,
    "alternating_rows": _alternating_rows,
    "alternating_columns": _alternating_columns,
    "sparse": _sparse,
}


def _layout_inputs() -> dict[str, tuple[Any, Any]]:
    """``{case id: (row clues, column clues)}`` for the layout golden."""
    rng = random.Random(LAYOUT_SEED)
    inputs: dict[str, tuple[Any, Any]] = {}
    extents = [(extent, pattern) for extent in _ANCHOR_EXTENTS for pattern in _PATTERNS]
    for _ in range(_DRAWN_EXTENTS):
        extent = (rng.randint(MIN_SIZE, MAX_SIZE), rng.randint(MIN_SIZE, MAX_SIZE))
        extents.append((extent, rng.choice(sorted(_PATTERNS))))
    for index, ((width, height), pattern) in enumerate(extents):
        clues = compute_clues(_PATTERNS[pattern](width, height, rng))
        inputs[f"{index:02d}-{pattern}-{width}x{height}"] = (clues.rows, clues.columns)
    inputs[golden.AC180_CASE_ID] = _ac180_clues()
    return inputs


def _ac180_clues() -> tuple[Any, Any]:
    """The clues of AC-180's seeded 30x30, read back from the CLI's own JSON export."""
    size, density, seed, name = golden.AC180_REQUEST
    with tempfile.TemporaryDirectory() as scratch:
        argv = ["generate", "--mode", "random", "--size", size, "--density", str(density)]
        argv += ["--seed", str(seed), "--name", name, "--export", "json", "--out", scratch]
        if cli.main(argv) != 0:
            raise SystemExit(f"AC-180's request failed: {argv}")
        document = json.loads((Path(scratch) / f"{name}.json").read_text(encoding="utf-8"))
    rows = tuple(tuple(clue) for clue in document["clues"]["rows"])
    columns = tuple(tuple(clue) for clue in document["clues"]["columns"])
    return rows, columns


def _check_field_lists_are_complete() -> None:
    """The explicit field lists in ``golden`` name every field there is today."""
    expected = {
        Layout: golden.LAYOUT_SCALAR_FIELDS + golden.LAYOUT_SEQUENCE_FIELDS,
        GridLine: golden.GRID_LINE_FIELDS,
        ClueEntry: golden.CLUE_ENTRY_FIELDS,
    }
    for cls, listed in expected.items():
        actual = {field.name for field in dataclasses.fields(cls)}
        if set(listed) != actual:
            raise SystemExit(f"golden's field list for {cls.__name__} is {listed}, not {actual}")


def _base_commit() -> str:
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "src"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    if dirty:
        raise SystemExit(
            "refusing to capture goldens: src/ has uncommitted changes, so the "
            f"output would not correspond to any commit:\n{dirty}"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _header(commit: str, what: str) -> dict[str, str]:
    return {
        "what": what,
        "generated_from_commit": commit,
        "generated_by": COMMAND,
        "python": platform.python_version(),
        "pillow": PIL.__version__,
        "regenerating": (
            "Never how a red golden test is fixed (CARD-113 G-3): a red test "
            "means the A4 layout or the CLI/web bytes changed, which CON-019 / "
            "ADR-0036/R1 forbid. See regenerate.py's docstring."
        ),
    }


def _write(path: Path, header: dict[str, str], cases: dict[str, Any]) -> None:
    """Deterministic JSON: sorted keys, one compact case per line, for readable diffs."""
    lines = [
        f"  {json.dumps(case_id)}: {json.dumps(case, sort_keys=True, separators=(',', ':'))}"
        for case_id, case in sorted(cases.items())
    ]
    text = (
        '{\n"_header": '
        + json.dumps(header, sort_keys=True, indent=2)
        + ',\n"cases": {\n'
        + ",\n".join(lines)
        + "\n}\n}\n"
    )
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--capture-from-clean-src", action="store_true", required=True)
    parser.parse_args(argv)

    commit = _base_commit()
    _check_field_lists_are_complete()

    layout_cases = {
        case_id: {
            "row_clues": [list(clue) for clue in rows],
            "column_clues": [list(clue) for clue in columns],
            "layout": golden.serialize_layout(compute_layout(rows, columns)),
        }
        for case_id, (rows, columns) in _layout_inputs().items()
    }
    _write(
        golden.LAYOUT_GOLDEN,
        _header(commit, "compute_layout(row_clues, column_clues), every Layout field"),
        layout_cases,
    )

    cli_cases: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as scratch:
        pinned = [(golden.AC180_CASE_ID, golden.AC180_REQUEST)]
        pinned += [(case.case_id, case.request) for case in ec020.CASES]
        for case_id, request in pinned:
            exports = golden.run_cli(request, Path(scratch) / case_id)
            cli_cases[case_id] = {"request": list(request), "exports": exports}
    _write(
        golden.CLI_GOLDEN,
        _header(
            commit,
            "SHA-256 of the PNG/SVG/PDF `nonogram generate` writes per request "
            "(PDF after zeroing Pillow's /CreationDate and /ModDate; see golden.py)",
        ),
        cli_cases,
    )
    print(f"captured {len(layout_cases)} layouts and {len(cli_cases)} CLI requests at {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
