"""CARD-096 — how often, and why, an owner's picture cannot be made into a puzzle.

    PYTHONPATH=src python meta/ops/image_abandonment_sweep.py \\
        [--sizes 10,15,20,25,30] [--presets small,medium,large,auto] \\
        [--small-share PERCENT] [--out FILE] [--pictures DIR] [--report FILE]

Two halves, because they answer different questions:

* **Engine** — every picture through ``orchestrator.generate`` in image mode at
  each bare size. Per conversion: outcome, extent, nudges used, and — the point
  of the card — the ambiguity of the **original** conversion (its undecided-mask
  size and how many cells its two witnesses disagree on), captured at the first
  solve rather than read off the aggregate afterwards, which holds the *last*
  nudge's mask. Each abandonment is classified as small residual, widespread or
  timeout by ``--small-share``: the share of the grid the original conversion
  left undecided. A share, not a count, because the grids run from 100 to 900
  cells. CARD-096 measured a clean gap — every abandonment was at most 8.0% or at
  least 22.5% — and set the default between them.
``--report FILE`` re-prints the tables from a saved run without converting
anything, so the classification can be re-cut without a twenty-minute re-run.

* **Admin** — every picture the way ``/batch/generate-puzzles`` runs it, per size
  preset: the fit policy (``ImageFile.size_fit``) and CARD-062's neighbour retry
  (``admin.app._generate_image_puzzle``). This is the loss rate the owner sees.

Pictures are read, never written: the admin half copies each into a throwaway
``ImageManager``, whose clean-up deletes only its own copies.

CARD-075 and CARD-079 are meant to re-run exactly this command for their
*after*. Outcome counts are load-independent; the timeout column is not, so run
it on a quiet machine.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

from nonogram import orchestrator, solver
from nonogram.errors import GenerationAbandoned, NonogramError, SolverTimeout

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _count(mask) -> int | None:
    return None if mask is None else sum(sum(1 for cell in row if cell) for row in mask)


def _disagreement(witnesses) -> int | None:
    if not witnesses or len(witnesses) < 2:
        return None
    first, second = witnesses[0], witnesses[1]
    return sum(a != b for ra, rb in zip(first, second) for a, b in zip(ra, rb))


class _FirstSolve:
    """Records every verdict ``solver.solve`` returns during one request."""

    def __init__(self) -> None:
        self.verdicts: list = []
        self._real = solver.solve

    def __enter__(self):
        def recording(*args, **kwargs):
            verdict = self._real(*args, **kwargs)
            self.verdicts.append(verdict)
            return verdict

        solver.solve = recording
        return self

    def __exit__(self, *exc) -> None:
        solver.solve = self._real


def engine(pictures: list[Path], sizes: list[int]) -> list[dict]:
    created: list = []
    real_puzzle = orchestrator.Puzzle

    class _Recorded(real_puzzle):  # type: ignore[valid-type,misc]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.append(self)

    orchestrator.Puzzle = _Recorded
    rows = []
    try:
        for picture in pictures:
            for size in sizes:
                created.clear()
                started = time.monotonic()
                with _FirstSolve() as solves:
                    try:
                        orchestrator.generate(
                            orchestrator.GenerationRequest(
                                mode="image", image=picture, image_filename=picture.name,
                                width=size, height=None,
                            )
                        )
                        outcome = "made"
                    except GenerationAbandoned:
                        outcome = "abandoned"
                    except SolverTimeout:
                        outcome = "timeout"
                    except NonogramError as error:
                        outcome = type(error).__name__
                puzzle = created[-1] if created else None
                first = solves.verdicts[0] if solves.verdicts else None
                grid = puzzle.grid if puzzle is not None else None
                rows.append({
                    "picture": picture.name,
                    "size": size,
                    "outcome": outcome,
                    "extent": list(puzzle.extent) if puzzle is not None and puzzle.extent else None,
                    "nudges": puzzle.nudge.attempts if puzzle is not None else None,
                    "first_unique": None if first is None else first.solution_count == 1,
                    "first_undecided": None if first is None else _count(first.undecided_mask),
                    "first_disagreement": None if first is None else _disagreement(first.witnesses),
                    "cells": None if not grid else len(grid) * len(grid[0]),
                    "seconds": round(time.monotonic() - started, 2),
                })
                print(json.dumps(rows[-1]), file=sys.stderr, flush=True)
    finally:
        orchestrator.Puzzle = real_puzzle
    return rows


def admin(pictures: list[Path], presets: list[str]) -> list[dict]:
    from nonogram.admin.app import _generate_image_puzzle
    from nonogram.admin.image_manager import CANNOT_FIT, SIZE_PRESETS, ImageManager

    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        manager = ImageManager(temp_dir=scratch)
        for picture in pictures:
            image = manager.add_image(str(picture), picture.name)
            if image is None:
                rows.append({"picture": picture.name, "preset": None, "outcome": "unreadable"})
                continue
            for preset in presets:
                value, mode = SIZE_PRESETS[preset]
                image.size_value, image.size_mode = value, mode
                fit = image.size_fit()
                started = time.monotonic()
                used = None
                if fit.status == CANNOT_FIT:
                    outcome = "cannot_fit"
                else:
                    try:
                        _, used = _generate_image_puzzle(image, *fit.extent)
                        outcome = "made" if tuple(used) == tuple(fit.extent) else "made_at_neighbour"
                    except GenerationAbandoned:
                        outcome = "abandoned"
                    except SolverTimeout:
                        outcome = "timeout"
                    except NonogramError as error:
                        outcome = type(error).__name__
                rows.append({
                    "picture": picture.name,
                    "preset": preset,
                    "fit": fit.status,
                    "extent": list(fit.extent),
                    "used": list(used) if used else None,
                    "outcome": outcome,
                    "seconds": round(time.monotonic() - started, 2),
                })
                print(json.dumps(rows[-1]), file=sys.stderr, flush=True)
            manager.remove_image(image.file_id)
    return rows


def classify(row: dict, small_share: float) -> str | None:
    if row["outcome"] == "timeout":
        return "timeout"
    if row["outcome"] != "abandoned":
        return None
    undecided = row["first_undecided"]
    if undecided is None or not row["cells"]:
        return "unknown"
    return "small residual" if 100 * undecided / row["cells"] <= small_share else "widespread"


def report(engine_rows: list[dict], admin_rows: list[dict], small_share: float) -> None:
    sizes = sorted({row["size"] for row in engine_rows})
    print("\n  ENGINE — orchestrator.generate, image mode, bare size")
    print(f"  {'size':>5} {'made':>5} {'first':>6} {'nudged':>7} {'aband':>6} {'t/out':>6} "
          f"{'small':>6} {'wide':>5}")
    for size in sizes:
        rows = [row for row in engine_rows if row["size"] == size]
        made = [row for row in rows if row["outcome"] == "made"]
        causes = collections.Counter(classify(row, small_share) for row in rows)
        print(f"  {size:>5} {len(made):>5} {sum(1 for r in made if not r['nudges']):>6} "
              f"{sum(1 for r in made if r['nudges']):>7} "
              f"{sum(1 for r in rows if r['outcome'] == 'abandoned'):>6} {causes['timeout']:>6} "
              f"{causes['small residual']:>6} {causes['widespread']:>5}")

    shares = sorted(round(100 * row["first_undecided"] / row["cells"], 1) for row in engine_rows
                    if row["outcome"] == "abandoned" and row["first_undecided"] is not None and row["cells"])
    if shares:
        print(f"\n  original conversion, share of grid undecided, abandoned only (n={len(shares)}): "
              f"median {statistics.median(shares):.1f}%")
        print(f"  sorted: {shares}")
    disagreements = collections.Counter(row["first_disagreement"] for row in engine_rows
                                        if row["outcome"] == "abandoned")
    print(f"  cells the two witnesses disagree on, abandoned only: {dict(sorted(disagreements.items(), key=str))}")
    print(f"  small residual = at most {small_share:g}% of the grid undecided")

    by_picture: dict[str, list[dict]] = collections.OrderedDict()
    for row in engine_rows:
        by_picture.setdefault(row["picture"], []).append(row)
    always = [name for name, rows in by_picture.items() if all(r["outcome"] != "made" for r in rows)]
    print(f"\n  fails at every size: {', '.join(always) or 'none'}")

    if admin_rows:
        print("\n  ADMIN — /batch/generate-puzzles per preset (fit policy + neighbour retry)")
        print(f"  {'preset':>7} {'made':>5} {'at nbr':>7} {'aband':>6} {'t/out':>6} {'no fit':>7} {'lost':>6}")
        for preset in dict.fromkeys(row["preset"] for row in admin_rows if row["preset"]):
            rows = [row for row in admin_rows if row["preset"] == preset]
            c = collections.Counter(row["outcome"] for row in rows)
            lost = c["abandoned"] + c["timeout"]
            print(f"  {preset:>7} {c['made']:>5} {c['made_at_neighbour']:>7} {c['abandoned']:>6} "
                  f"{c['timeout']:>6} {c['cannot_fit']:>7} {lost:>3}/{len(rows):<3}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", default="10,15,20,25,30")
    parser.add_argument("--presets", default="small,medium,large,auto")
    parser.add_argument("--small-share", type=float, default=15.0)
    parser.add_argument("--report", help="re-print the tables from a saved JSON run")
    parser.add_argument("--pictures", default="pictures")
    parser.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "image_abandonment_sweep.json"))
    args = parser.parse_args()
    if args.report:
        saved = json.loads(Path(args.report).read_text())
        report(saved["engine"], saved["admin"], args.small_share)
        return

    pictures = sorted(p for p in Path(args.pictures).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    sizes = [int(part) for part in args.sizes.split(",") if part]
    presets = [part for part in args.presets.split(",") if part]
    print(f"  {len(pictures)} pictures, sizes {sizes}, presets {presets}", flush=True)

    engine_rows = engine(pictures, sizes)
    admin_rows = admin(pictures, presets) if presets else []
    Path(args.out).write_text(json.dumps({"engine": engine_rows, "admin": admin_rows}, indent=1))
    report(engine_rows, admin_rows, args.small_share)
    print(f"\n  rows written to {args.out}")


if __name__ == "__main__":
    main()
