"""CARD-079's gate — every corpus picture converted both ways, for the owner's eye.

    PYTHONPATH=src python meta/ops/binarisation_review.py OUTDIR \\
        [--sizes 10,15,20,25,30] [--pictures DIR] [--sheet-size 25] [--from-rows FILE]

Two outputs, because the decision needs both halves:

* **Sheets** — one PNG per picture: the source, then the grid the **threshold**
  path produces and the grid the **dither** path produces at ``--sheet-size``,
  side by side, each labelled with its outcome and nudge count. This is the
  gate (DEC-032, FR-027 ``_meta.gate``): whether the threshold path's grids
  still look like the owner's pictures is judged by eye and by nothing else.
* **Numbers** — AC-127's three clauses over ``--sizes``, per picture and in
  total: (a) first-solve-unique counts, (b) total nudges, (c) conversions the
  dither path makes that the threshold path does not — counted case by case,
  which is the clause the suite test cannot afford (see
  ``tests/test_sourcing_image.py``'s AC-127 section for why). Plus each
  picture's **mid-tone share**, which is the calibration ADR-0028 owes for
  ``MIDTONE_SHARE_THRESHOLD`` — recorded here so the owner can set the
  constant on data rather than on the provisional 0.10 guess.

Pictures are read, never written. Sheets go to OUTDIR, which should be outside
the repository — ``~/Documents/nonogram-reviews/CARD-079`` is where this
project puts renders.

Nothing here decides anything: the shipped default stays dither until the
owner says otherwise (CARD-079 guardrail G-1). Both paths are driven by
setting ``image.DEFAULT_BINARISATION`` around each run, which is exactly the
switch the owner's flip would move.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

from nonogram import orchestrator
from nonogram.errors import NonogramError
from nonogram.sourcing import image as image_source

PANEL = 320
PAD = 16
LABEL = 34
FILLED = (20, 20, 20)
EMPTY = (255, 255, 255)
GRIDLINE = (200, 200, 200)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def _panel(grid: list[list[bool]]) -> Image.Image:
    rows, columns = len(grid), len(grid[0])
    cell = max(4, PANEL // max(rows, columns))
    panel = Image.new("RGB", (columns * cell + 1, rows * cell + 1), GRIDLINE)
    draw = ImageDraw.Draw(panel)
    for row in range(rows):
        for column in range(columns):
            draw.rectangle(
                [column * cell + 1, row * cell + 1,
                 (column + 1) * cell - 1, (row + 1) * cell - 1],
                fill=FILLED if grid[row][column] else EMPTY,
            )
    return panel


#: The two columns. ``None`` is the shipped conversion since the owner's flip
#: — classifier per picture, plus the degenerate-ink guard — and ``DITHER`` is
#: the incumbent it replaced. Comparing *those* is the decision-relevant
#: comparison; comparing the two raw paths flatters the threshold, because it
#: credits it with pictures the guard sends straight back to the dither path.
COLUMNS = (("shipped", None), ("dither", image_source.DITHER))


def _convert(picture: Path, size: int, column: tuple[str, str | None]) -> dict:
    """One picture, one size, one column, through the real pipeline.

    ``DEFAULT_BINARISATION`` is moved rather than a ``path=`` argument threaded
    through the orchestrator: the point is to exercise what the switch actually
    does, including the guard and
    :func:`image_source.binarisation_for`'s recording on the aggregate.
    """
    label, path = column
    previous = image_source.DEFAULT_BINARISATION
    image_source.DEFAULT_BINARISATION = path
    started = time.monotonic()
    row = {"picture": picture.name, "size": size, "path": label}
    try:
        puzzle = orchestrator.generate(
            orchestrator.GenerationRequest(
                mode="image", image=picture, width=size, height=size, seed=1
            )
        )
        row |= {
            "outcome": "made",
            "nudges": puzzle.nudge.attempts,
            "first_solve_unique": puzzle.nudge.attempts == 0,
            "binarisation": puzzle.binarisation,
            "grid": puzzle.grid,
        }
    except NonogramError as error:
        row |= {
            "outcome": type(error).__name__,
            "nudges": None,
            "first_solve_unique": False,
            "binarisation": None,
            "grid": None,
        }
    finally:
        image_source.DEFAULT_BINARISATION = previous
    row["seconds"] = round(time.monotonic() - started, 2)
    return row


def _sheet(picture: Path, rows: list[dict], out: Path) -> Path | None:
    """Source, threshold, dither — the three panels the gate is decided on."""
    source = Image.open(picture).convert("RGB")
    source.thumbnail((PANEL, PANEL))
    share = image_source.midtone_share(image_source.load_greyscale(picture))
    panels = [(f"{picture.name} — mid-tone share {share:.3f}", source)]
    for row in rows:
        if row["grid"] is None:
            continue
        nudges = row["nudges"]
        used = row.get("binarisation") or row["path"]
        panels.append(
            (f"{row['path']} ({used}): made, {nudges} nudge{'' if nudges == 1 else 's'}",
             _panel(row["grid"]))
        )
    for row in rows:
        if row["grid"] is None:
            panels.append((f"{row['path']}: {row['outcome']}", Image.new("RGB", (PANEL, 8), (245, 245, 245))))
    if len(panels) == 1:
        return None
    width = sum(p.width for _, p in panels) + PAD * (len(panels) + 1)
    height = max(p.height for _, p in panels) + LABEL + PAD * 2
    sheet = Image.new("RGB", (width, height), (245, 245, 245))
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
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--sizes", default="10,15,20,25,30")
    parser.add_argument("--sheet-size", type=int, default=25)
    parser.add_argument("--pictures", default="pictures")
    parser.add_argument(
        "--from-rows",
        help="re-report a finished sweep from the JSON rows it printed on stderr",
    )
    args = parser.parse_args()

    directory = Path(args.pictures)
    if not directory.is_dir():
        print(f"no corpus at {directory} — nothing to review")
        return
    pictures = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES
    )
    sizes = [int(token) for token in args.sizes.split(",")]
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    if args.from_rows:
        saved = [
            json.loads(line)
            for line in Path(args.from_rows).read_text().splitlines()
            if line.startswith("{")
        ]
        shares = {
            picture.name: round(
                image_source.midtone_share(image_source.load_greyscale(picture)), 4
            )
            for picture in pictures
        }
        _report(saved, shares, out)
        return

    print(f"  {len(pictures)} pictures, sizes {sizes}, sheets at {args.sheet_size}")
    rows: list[dict] = []
    shares: dict[str, float] = {}
    for picture in pictures:
        shares[picture.name] = round(
            image_source.midtone_share(image_source.load_greyscale(picture)), 4
        )
        for size in sizes:
            for column in COLUMNS:
                row = _convert(picture, size, column)
                rows.append(row)
                print(
                    json.dumps({k: v for k, v in row.items() if k != "grid"}),
                    file=sys.stderr,
                    flush=True,
                )
        sheet_rows = [
            r for r in rows
            if r["picture"] == picture.name and r["size"] == args.sheet_size
        ]
        if _sheet(picture, sheet_rows, out):
            print(f"  sheet: {picture.name}", flush=True)

    _report(rows, shares, out)


def _report(rows: list[dict], shares: dict[str, float], out: Path) -> None:
    """Print AC-127's totals and the calibration table, and save the rows.

    Split out of :func:`main` so a finished sweep's rows can be re-reported
    without converting anything again (``--from-rows``): the sweep takes about
    twenty-five minutes, and the report is the part most likely to be re-cut.
    """
    def side(label: str) -> list[dict]:
        return [r for r in rows if r["path"] == label]

    print("\n  AC-127 — the shipped conversion against dither-everywhere")
    print(f"  {'':10} {'made':>6} {'1st-solve':>10} {'nudges':>8} {'failed':>8}")
    for label, _ in COLUMNS:
        these = side(label)
        made = sum(r["outcome"] == "made" for r in these)
        first = sum(bool(r["first_solve_unique"]) for r in these)
        nudges = sum(r["nudges"] or 0 for r in these)
        print(f"  {label:10} {made:>6} {first:>10} {nudges:>8} {len(these) - made:>8}")

    shipped_made = [r for r in side("shipped") if r["outcome"] == "made"]
    used = {}
    for r in shipped_made:
        used[r["binarisation"]] = used.get(r["binarisation"], 0) + 1
    print(f"  shipped conversions made, by the path actually used: {used}")

    made_by = {
        label: {(r["picture"], r["size"]) for r in side(label) if r["outcome"] == "made"}
        for label, _ in COLUMNS
    }
    regressions = sorted(made_by["dither"] - made_by["shipped"])
    gains = sorted(made_by["shipped"] - made_by["dither"])
    print(f"\n  (c) conversions dither makes and the shipped conversion does not: {len(regressions)}")
    for case in regressions:
        print(f"      REGRESSION {case[0]} at {case[1]}")
    print(f"  conversions the shipped conversion makes and dither does not: {len(gains)}")
    for case in gains:
        print(f"      gain {case[0]} at {case[1]}")

    print("\n  mid-tone share per picture (ADR-0028's calibration)")
    for name, share in sorted(shares.items(), key=lambda item: item[1]):
        flag = "dither" if share >= image_source.MIDTONE_SHARE_THRESHOLD else "threshold"
        print(f"      {share:>7.4f}  {flag:>9}  {name}")

    report = out / "binarisation_review.json"
    report.write_text(json.dumps(
        {"rows": [{k: v for k, v in r.items() if k != "grid"} for r in rows],
         "midtone_shares": shares},
        indent=1,
    ))
    print(f"\n  {report.name} in {out}")


if __name__ == "__main__":
    main()
