"""CARD-075 — the two candidate nudge rankings, side by side, for the owner's eye.

    PYTHONPATH=src python meta/ops/nudge_ranking_contact_sheet.py \\
        BEFORE.json OUTDIR [PICTURES_DIR]

``BEFORE.json`` is the sweep ``image_abandonment_sweep.py`` wrote on ``main``
(CARD-096's run). Every conversion it records as abandoned or timed out is
replayed here under **both** candidate rankings, and one PNG per case is
written:

    source | original conversion | ink-boundary ranking | (row, column) ranking

The conversion panel tints the cells line logic could not decide — dark red
where the conversion filled them, pink where it left them empty. The two result
panels tint the cells the nudge **flipped**, in blue, so "how much of the
picture did this cost" is visible rather than counted. A panel labelled
*abandoned* is the grid the run gave up on.

Why this exists: the two rankings differ by one conversion in 125
(``frog1.jpeg`` at 30, which only the (row, column) rule makes), so the yield
argument is nearly a tie and the decision is a fidelity one — where the flipped
pixels land. That is judged by eye, which is what this renders. It is the same
reasoning ``image_abandonment_contact_sheet.py`` was written under, and the
panel code is deliberately its own rather than imported: ``meta/ops`` scripts
are one-offs kept for re-running, not a library.

Output goes to OUTDIR, which should be outside the repository — nothing
rendered here is committed.
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
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS, MAX_NUDGE_ATTEMPTS
from nonogram.sourcing import image as image_source

PANEL = 300
PAD = 16
LABEL = 34
FILLED = (20, 20, 20)
EMPTY = (255, 255, 255)
UNDECIDED_FILLED = (150, 20, 30)
UNDECIDED_EMPTY = (250, 190, 200)
FLIPPED_ON = (20, 70, 200)
FLIPPED_OFF = (170, 200, 255)
GRIDLINE = (200, 200, 200)


def _panel(grid, tint_filled=None, tint_empty=None, marked=frozenset()):
    """One grid, cells the size of the panel's budget, marked cells tinted."""
    rows, columns = len(grid), len(grid[0])
    cell = max(4, PANEL // max(rows, columns))
    panel = Image.new("RGB", (columns * cell + 1, rows * cell + 1), GRIDLINE)
    draw = ImageDraw.Draw(panel)
    for row in range(rows):
        for column in range(columns):
            on = grid[row][column]
            if (row, column) in marked:
                colour = (tint_filled or FLIPPED_ON) if on else (tint_empty or FLIPPED_OFF)
            else:
                colour = FILLED if on else EMPTY
            draw.rectangle(
                [column * cell + 1, row * cell + 1,
                 (column + 1) * cell - 1, (row + 1) * cell - 1],
                fill=colour,
            )
    return panel


def _mask_cells(mask):
    if not mask:
        return frozenset()
    return frozenset(
        (row, column)
        for row, mask_row in enumerate(mask)
        for column, cell in enumerate(mask_row)
        if cell
    )


def _solve(grid, deadline):
    line_clues = clues.compute_clues(grid)
    return solver.solve(line_clues.rows, line_clues.columns, deadline=deadline)


def _replay(original, deadline):
    """POL-002's loop over the ranking currently installed. -> (grid, flipped, made)."""
    flipped: list[tuple[int, int]] = []
    judged = original
    verdict = _solve(original, deadline)
    if verdict.solution_count == 1:
        return original, [], True
    for _ in range(MAX_NUDGE_ATTEMPTS):
        cell = image_source.next_nudge_cell(
            judged,
            flipped,
            witnesses=verdict.witnesses,
            undecided_mask=verdict.undecided_mask,
        )
        if cell is None:
            break
        flipped.append(cell)
        judged = image_source.nudge(original, flipped)
        verdict = _solve(judged, deadline)
        if verdict.solution_count == 1:
            return judged, flipped, True
    return judged, flipped, False


def _flat(rows):
    """Every cell the same distance: the ranking collapses to (row, column)."""
    return [[0] * len(rows[0]) for _ in rows]


def render(picture: Path, width: int, height: int, out: Path) -> Path:
    deadline = time.monotonic() + GENERATION_BUDGET_SECONDS
    source = Image.open(picture).convert("RGB")
    source.thumbnail((PANEL, PANEL))
    original = image_source.generate(picture, width, height, random.Random(0))

    try:
        verdict = _solve(original, deadline)
        undecided = _mask_cells(verdict.undecided_mask)
        conversion_label = f"conversion {width}x{height}: {len(undecided)} undecided"
    except SolverTimeout:
        undecided = frozenset()
        conversion_label = f"conversion {width}x{height}: no verdict in {GENERATION_BUDGET_SECONDS:.0f}s"

    panels = [
        (f"{picture.name} (source)", source),
        (conversion_label,
         _panel(original, UNDECIDED_FILLED, UNDECIDED_EMPTY, undecided)),
    ]

    real = image_source._boundary_distances
    for label, ranking in (("ink-boundary", real), ("(row, column)", _flat)):
        image_source._boundary_distances = ranking
        try:
            grid, flipped, made = _replay(original, time.monotonic() + GENERATION_BUDGET_SECONDS)
            outcome = f"made, {len(flipped)} flipped" if made else f"abandoned after {len(flipped)}"
        except SolverTimeout:
            grid, flipped, outcome = original, [], "timeout"
        finally:
            image_source._boundary_distances = real
        panels.append((f"{label}: {outcome}", _panel(grid, marked=frozenset(flipped))))

    sheet_width = sum(p.width for _, p in panels) + PAD * (len(panels) + 1)
    sheet_height = max(p.height for _, p in panels) + LABEL + PAD * 2
    sheet = Image.new("RGB", (sheet_width, sheet_height), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    x = PAD
    for label, panel in panels:
        draw.text((x, PAD), label, fill=(0, 0, 0))
        sheet.paste(panel, (x, PAD + LABEL))
        x += panel.width + PAD
    target = out / f"{picture.stem}_{width}x{height}.png"
    sheet.save(target)
    return target


def main() -> None:
    before, out = Path(sys.argv[1]), Path(sys.argv[2])
    pictures = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("pictures")
    out.mkdir(parents=True, exist_ok=True)
    rows = json.loads(before.read_text())["engine"]
    cases = [r for r in rows if r["outcome"] != "made" and r["extent"]]
    for row in cases:
        print(render(pictures / row["picture"], *row["extent"], out), flush=True)
    print(f"{len(cases)} sheets in {out}")


if __name__ == "__main__":
    main()
