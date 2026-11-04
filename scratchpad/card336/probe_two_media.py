"""CARD-336 AC-1: the same book page drawn in both media, against Layout's coordinate."""
from __future__ import annotations
import sys
import numpy as np

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.export.layout import compute_layout
from tests.helpers.page_ink import _dark, _longest_runs, _rule_groups, drawing_of
from tests.helpers.pdf_pages import interior_images

sys.path.insert(0, "tests")
import test_book_puzzle_frame as m


def centre(page, drawing):
    dark = _dark(page)
    vband = dark[drawing.top : drawing.grid_bottom + 1]
    v0 = _rule_groups(_longest_runs(vband.T.copy()))[0]
    t = len(v0)
    start = max(0, drawing.top - t)
    box = dark[start : drawing.grid_bottom + 1, v0[0] : drawing.grid_right + 1]
    h0 = _rule_groups(_longest_runs(box.copy()))[0]
    return (v0[0] + v0[-1]) / 2, (h0[0] + h0[-1]) / 2 + start, len(v0), len(h0)


CASE = dict(columns=20, rows=20, row_depth=4, column_depth=5)
gen = BookPDFGenerator(m._book())
row = m._book_puzzle(**CASE, puzzle_id="ac1")
payload = BookPDFGenerator._payload(row)
cells = gen.cell_sizes([payload])
PAGE_NUMBER = 4
spec = gen._puzzle_page_spec(PAGE_NUMBER, cells.get(BookPDFGenerator._grid_size(payload)))
layout = compute_layout(payload.row_clues, payload.column_clues, spec)
frame = layout.frame
print("COORDINATE frame.left/top =", frame.left, frame.top, " grid", layout.grid_left, layout.grid_top)

raster = gen._blank_page(payload, 1, PAGE_NUMBER, cells)
stream = gen.vector_puzzle_page(payload, 1, PAGE_NUMBER, cells)
vector = interior_images([stream])[0]
print("sizes", raster.size, vector.size)
out = {}
for tag, page in (("raster", raster), ("vector", vector)):
    d = drawing_of(page)
    c = centre(page, d)
    out[tag] = (d, c)
    print(f"{tag}: ink left/top = {d.left}/{d.top}  centre = {c[0]}/{c[1]} rules {c[2]}/{c[3]}")
    print(f"   ink   residual vs coordinate: left {d.left-frame.left:+.3f}  top {d.top-frame.top:+.3f}")
    print(f"   centre residual vs coordinate: left {c[0]-frame.left:+.3f}  top {c[1]-frame.top:+.3f}")
dr, cr = out["raster"]; dv, cv = out["vector"]
print(f"CROSS-MEDIUM ink   disagreement: left {abs(dr.left-dv.left)}  top {abs(dr.top-dv.top)}")
print(f"CROSS-MEDIUM centre disagreement: left {abs(cr[0]-cv[0])}  top {abs(cr[1]-cv[1])}")
