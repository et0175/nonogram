"""CARD-329: is poppler's antialiasing why a rendered vector page's ink extent
sits further out than the raster page's?

Not a test and not under ``tests/`` (G-7). A measurement, run before any
tolerance was touched -- CARD-330's gating rule is that a tolerance is never
widened to make a reading agree, so the question is whether the INSTRUMENT is
wrong, not whether the number is close enough.

Both media of the SAME page, at the same DPI, measured with the same oracle
(``page_ink.drawing_of``), which is the only way the two readings are in one
domain (CARD-330). Reported as the per-edge device-pixel difference.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nonogram.admin import book_vector
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.clues import compute_clues
from tests.helpers.page_ink import drawing_of

PDFTOPPM = "/opt/homebrew/bin/pdftoppm"
DPI = 300
PAGE = 6


def book() -> Book:
    """One book on US Letter, the trim the geometry property's reds carry."""
    return Book(
        book_id="book-329",
        metadata=BookMetadata(
            title="Aliasing probe",
            description="",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm="21.59",
        trim_height_cm="27.94",
        gutter_margin_cm="1.27",
        outside_margin_cm="0.95",
    )


def puzzle(columns=10, rows=10):
    grid = [
        [(column + row) % 3 == 0 for column in range(columns)] for row in range(rows)
    ]
    row_clues, column_clues = compute_clues(grid)
    return {
        "id": "p1",
        "name": "P1",
        "width": columns,
        "height": rows,
        "grid": grid,
        "clues_rows": [list(clue) for clue in row_clues],
        "clues_cols": [list(clue) for clue in column_clues],
        "difficulty_tier": "easy",
    }


def render(data: bytes, directory: Path, *, aa: str) -> Image.Image:
    source = directory / f"page-{aa}.pdf"
    source.write_bytes(data)
    subprocess.run(
        [PDFTOPPM, "-r", str(DPI), "-f", "1", "-l", "1", "-gray", "-png",
         "-aa", aa, "-aaVector", aa, str(source), str(directory / f"out-{aa}")],
        check=True, capture_output=True,
    )
    (png,) = sorted(directory.glob(f"out-{aa}-*.png"))
    with Image.open(png) as image:
        return image.convert("RGB")


def main() -> int:
    generator = BookPDFGenerator(book())
    row = puzzle()
    payload = BookPDFGenerator._payload(row)
    sizes = generator.cell_sizes([payload])

    bitmap = generator._blank_page(payload, 1, PAGE, sizes)
    stream = generator.vector_puzzle_page(payload, 1, PAGE, sizes)
    data = book_vector.write_vector_pdf([stream], 1).getvalue()

    raster = drawing_of(bitmap)
    print(f"raster bitmap size {bitmap.size}")
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for aa in ("yes", "no"):
            image = render(data, directory, aa=aa)
            reading = drawing_of(image)
            print(f"\n--- poppler -aa {aa} -aaVector {aa}: size {image.size}")
            for edge in ("left", "top", "grid_left", "grid_top",
                         "grid_right", "grid_bottom"):
                a = getattr(raster, edge)
                b = getattr(reading, edge)
                print(f"    {edge:12} raster={a:6} poppler={b:6} "
                      f"diff={b - a:+4} px = {(b - a) * 25.4 / DPI:+.4f} mm")
            print(f"    columns/rows raster=({raster.columns},{raster.rows}) "
                  f"poppler=({reading.columns},{reading.rows})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
