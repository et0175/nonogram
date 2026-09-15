"""CARD-096 AC-4 — put every failing picture in front of the owner's eyes.

    PYTHONPATH=src python meta/ops/image_abandonment_contact_sheet.py SWEEP.json OUTDIR

Reads the JSON ``image_abandonment_sweep.py`` wrote and, for each picture that
was abandoned or timed out at some size, renders one PNG: the source picture,
then the **original** conversion at every failing size (no nudge applied), with
the cells the solver's line logic could not decide tinted — dark red where the
conversion filled them, pink where it left them empty. That tint is the
ambiguity a fix has to remove; how much of the picture it covers is the
difference between CARD-075's population and CARD-079's.

Why a render and not a number: fidelity is judged by eye (a change that converts
more pictures can convert them worse), and the undecided count alone cannot show
*where* the ambiguity sits. Output goes to OUTDIR, which should be outside the
repository — nothing rendered is committed.
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

from nonogram import clues, solver
from nonogram.errors import SolverTimeout
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS
from nonogram.sourcing import image as image_source

PANEL = 300
PAD = 16
LABEL = 34
FILLED = (20, 20, 20)
EMPTY = (255, 255, 255)
UNDECIDED_FILLED = (150, 20, 30)
UNDECIDED_EMPTY = (250, 190, 200)
GRIDLINE = (200, 200, 200)


def _grid_panel(grid, mask) -> Image.Image:
    rows, cols = len(grid), len(grid[0])
    cell = max(4, PANEL // max(rows, cols))
    panel = Image.new("RGB", (cols * cell + 1, rows * cell + 1), GRIDLINE)
    draw = ImageDraw.Draw(panel)
    for r in range(rows):
        for c in range(cols):
            undecided = bool(mask and mask[r][c])
            colour = (UNDECIDED_FILLED if grid[r][c] else UNDECIDED_EMPTY) if undecided else (
                FILLED if grid[r][c] else EMPTY)
            draw.rectangle([c * cell + 1, r * cell + 1, (c + 1) * cell - 1, (r + 1) * cell - 1], fill=colour)
    return panel


def render(picture: Path, failures: list[dict], out: Path) -> Path:
    source = Image.open(picture).convert("RGB")
    source.thumbnail((PANEL, PANEL))
    panels = [(f"{picture.name} (source)", source)]
    for row in failures:
        width, height = row["extent"]
        grid = image_source.generate(picture, width, height, random.Random(0))
        rows, columns = clues.compute_clues(grid)
        try:
            verdict = solver.solve(
                rows, columns, deadline=time.monotonic() + GENERATION_BUDGET_SECONDS
            )
        except SolverTimeout:
            # The same budget generation gets; past it there is no mask to draw.
            panels.append((f"{width}x{height} timeout: no verdict in {GENERATION_BUDGET_SECONDS:.0f}s",
                           _grid_panel(grid, None)))
            continue
        undecided = sum(map(sum, verdict.undecided_mask)) if verdict.undecided_mask else 0
        label = f"{width}x{height} {row['outcome']}: {undecided} undecided"
        panels.append((label, _grid_panel(grid, verdict.undecided_mask)))
    sheet_w = sum(p.width for _, p in panels) + PAD * (len(panels) + 1)
    sheet_h = max(p.height for _, p in panels) + LABEL + PAD * 2
    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    x = PAD
    for label, panel in panels:
        draw.text((x, PAD), label, fill=(0, 0, 0))
        sheet.paste(panel, (x, PAD + LABEL))
        x += panel.width + PAD
    target = out / f"{picture.stem}.png"
    sheet.save(target)
    return target


def main() -> None:
    sweep, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rows = json.loads(sweep.read_text())["engine"]
    pictures_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("pictures")
    failing: dict[str, list[dict]] = {}
    for row in rows:
        if row["outcome"] in ("abandoned", "timeout") and row["extent"]:
            failing.setdefault(row["picture"], []).append(row)
    for name, failures in failing.items():
        print(render(pictures_dir / name, failures, out), flush=True)
    print(f"{len(failing)} sheets in {out}")


if __name__ == "__main__":
    main()
