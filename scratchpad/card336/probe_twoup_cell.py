"""CARD-336: geometry test 4's two-up cell (bound 1 x HALF_PIXEL_MM), both media."""
from __future__ import annotations
import sys

MODE = sys.argv[1]
if MODE == "vector":
    import probe_five_kinds
    class _C: pass
    probe_five_kinds.pytest_configure(_C())

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import frame_centre_of
from tests.helpers.two_up_ink import drawings_of

sys.path.insert(0, "tests/property")
import test_book_pdf_geometry as g

extents = [(c, r) for c in range(MIN_SIZE, 23, 2) for r in range(MIN_SIZE, 17, 2)]
sheet = g.BOOK1
puzzles = [g._shallow_puzzle(c, r, 2, "easy") for c, r in extents]
gen = BookPDFGenerator(sheet.book)
toc = gen.section_plan(puzzles).toc_page_count
pages = g._interior(gen, puzzles)
band_foot_mm = g.TOP_MM + g.BAND_MM
bound = g.HALF_PIXEL_MM
index = 0
page_number = 5 + toc
worst_ink = worst_ctr = 0.0
n = 0
while index < len(puzzles):
    page = pages[page_number - 1]
    drawings = drawings_of(page)
    if len(drawings) == 2:
        d = drawings[0]
        c = frame_centre_of(page, d)
        ink = abs(g._mm(d.top) - band_foot_mm)
        ctr = abs(g._mm(c.frame_top) - band_foot_mm)
        worst_ink = max(worst_ink, ink); worst_ctr = max(worst_ctr, ctr)
        n += 1
    index += len(drawings)
    page_number += 1
print(f"{MODE}: two-up pages={n} bound={bound:.6f} mm ({1.0} px)")
print(f"   worst INK  residual {worst_ink:.6f} mm = {worst_ink*g.PX_PER_MM:.4f} px  ({worst_ink/bound:.2f}x bound)")
print(f"   worst CTR  residual {worst_ctr:.6f} mm = {worst_ctr*g.PX_PER_MM:.4f} px  ({worst_ctr/bound:.2f}x bound)")
