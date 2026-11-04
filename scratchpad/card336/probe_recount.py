"""CARD-336: an independent recount of the frame rule's width, at a mid-cell row."""
from __future__ import annotations
import sys
import numpy as np

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.page_ink import _dark, _groups, drawing_of, frame_centre_of
from tests.helpers.pdf_pages import interior_images

sys.path.insert(0, "tests")
import test_book_puzzle_frame as m

CASE = dict(columns=20, rows=20, row_depth=4, column_depth=5)
gen = BookPDFGenerator(m._book())
payload = BookPDFGenerator._payload(m._book_puzzle(**CASE, puzzle_id="x"))
cells = gen.cell_sizes([payload])
for tag, page in (
    ("raster", gen._blank_page(payload, 1, m.SINGLE_PAGE, cells)),
    ("vector", interior_images([gen.vector_puzzle_page(payload, 1, m.SINGLE_PAGE, cells)])[0]),
):
    d = drawing_of(page)
    b = frame_centre_of(page, d)
    dark = _dark(page)
    row = d.grid_top + round(d.cell / 2)
    runs = _groups(np.flatnonzero(dark[row]))
    holding = [r for r in runs if r[0] <= d.left <= r[-1]]
    col = d.grid_left + round(d.cell / 2)
    cruns = _groups(np.flatnonzero(dark[:, col]))
    cholding = [r for r in cruns if r[0] <= d.top <= r[-1]]
    print(f"{tag}: left_rule_px={b.left_rule_px} top_rule_px={b.top_rule_px} "
          f"row={row} recount_left={[len(r) for r in holding]} "
          f"col={col} recount_top={[len(r) for r in cholding]}")
