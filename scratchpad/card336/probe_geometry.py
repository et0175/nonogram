"""CARD-336: are the geometry module's measured pages framed, and what do the
four placed-edge cells read, ink vs boundary, under each medium?"""
from __future__ import annotations
import sys, random

MODE = sys.argv[1] if len(sys.argv) > 1 else "raster"
if MODE == "vector":
    import probe_five_kinds
    class _C: pass
    probe_five_kinds.pytest_configure(_C())

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.page_ink import drawing_of, frame_centre_of
from tests.helpers.two_up_ink import drawings_of

sys.path.insert(0, "tests/property")
import test_book_pdf_geometry as g

print(f"=== {MODE} ===")
rng = random.Random(1160019)
sheet = g.BOOK1
puzzle = g._puzzle(rng)
columns, rows, across, down = g._extent(puzzle)
gen = BookPDFGenerator(sheet.book)
toc = gen.section_plan([puzzle]).toc_page_count
pages = g._interior(gen, [puzzle])
d = drawing_of(pages[3 + toc])
c = frame_centre_of(pages[3 + toc], d)
tops = sheet.drawing_top_mm(across, down)
print("test1 puzzle page framed:", d.framed, "rules", c.left_rule_px, c.top_rule_px)
print("  ink  top residual mm:", min(abs(g._mm(d.top) - t) for t in tops), "bound", 3*g.HALF_PIXEL_MM)
print("  ctr  top residual mm:", min(abs(g._mm(c.frame_top) - t) for t in tops))

# test 3: three copies + answer pages
rng3 = random.Random(1160032)
for case in range(40):
    s = g.BOOK1 if case % 10 == 0 else g._random_sheet(rng3)
    p = g._puzzle(rng3)
    cols, rws, acr, dwn = g._extent(p)
    if s.page_fit_mm(acr, dwn) < g.MIN_CELL_MM: continue
    if cols <= 15 and rws <= 20: continue
    book_rows = [dict(p, difficulty_tier="easy", id="p-easy"),
                 dict(p, difficulty_tier="medium", id="p-medium"),
                 dict(p, id="p-ungraded")]
    gen3 = BookPDFGenerator(s.book)
    toc3 = gen3.section_plan(book_rows).toc_page_count
    pgs = g._interior(gen3, book_rows)
    for label, number in (("puzzle", 7+toc3), ("answer", 10+toc3)):
        dd = drawing_of(pgs[number-1])
        cc = frame_centre_of(pgs[number-1], dd)
        exp_left = s.drawing_left_mm(number, acr, dwn)
        tms = s.drawing_top_mm(acr, dwn)
        print(f"test3 {label} p{number} framed={dd.framed} rules={cc.left_rule_px}/{cc.top_rule_px} "
              f"ink_left={abs(g._mm(dd.left)-exp_left):.4f} ctr_left={abs(g._mm(cc.frame_left)-exp_left):.4f} "
              f"(bound {2*g.HALF_PIXEL_MM:.4f}) "
              f"ink_top={min(abs(g._mm(dd.top)-t) for t in tms):.4f} ctr_top={min(abs(g._mm(cc.frame_top)-t) for t in tms):.4f} "
              f"(bound {3*g.HALF_PIXEL_MM:.4f})")
    break
