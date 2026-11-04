"""CARD-336: the built oracle, in both media, against Layout's coordinate."""
from __future__ import annotations
import sys

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.export.layout import compute_layout
from tests.helpers.page_ink import drawing_of, frame_centre_of
from tests.helpers.two_up_ink import drawings_of
from tests.helpers.pdf_pages import interior_images

sys.path.insert(0, "tests")
import test_book_puzzle_frame as m

CASE = dict(columns=20, rows=20, row_depth=4, column_depth=5)
gen = BookPDFGenerator(m._book())
row = m._book_puzzle(**CASE, puzzle_id="ac1")
payload = BookPDFGenerator._payload(row)
cells = gen.cell_sizes([payload])
PAGE_NUMBER = 4
spec = gen._puzzle_page_spec(PAGE_NUMBER, cells.get(BookPDFGenerator._grid_size(payload)))
frame = compute_layout(payload.row_clues, payload.column_clues, spec).frame
print("COORDINATE layout.frame left/top =", frame.left, frame.top)

reads = {}
for tag, page in (
    ("raster", gen._blank_page(payload, 1, PAGE_NUMBER, cells)),
    ("vector", interior_images([gen.vector_puzzle_page(payload, 1, PAGE_NUMBER, cells)])[0]),
):
    d = drawing_of(page)
    c = frame_centre_of(page, d)
    reads[tag] = c
    print(f"{tag}: ink {d.left}/{d.top}  -> {c}")
    print(f"   boundary residual  left {c.frame_left-frame.left:+.3f}  top {c.frame_top-frame.top:+.3f}")
    print(f"   ink      residual  left {d.left-frame.left:+.3f}  top {d.top-frame.top:+.3f}")
print("CROSS-MEDIUM boundary: left %.3f top %.3f" % (
    abs(reads["raster"].frame_left - reads["vector"].frame_left),
    abs(reads["raster"].frame_top - reads["vector"].frame_top)))

# Refusals (ADR-0039/R2)
from nonogram.export.layout import DEFAULT_PAGE_SPEC
from nonogram.export.png import render_image
import dataclasses
plain = render_image(m._payload(**CASE), page_spec=dataclasses.replace(m._spec(), frame=False))
d = drawing_of(plain)
print("unframed drawing framed =", d.framed)
try:
    frame_centre_of(plain, d)
    print("REFUSAL MISSING")
except ValueError as e:
    print("refused unframed:", str(e)[:70])
