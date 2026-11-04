"""CARD-336: geometry test 3's three placed-edge sites over its OWN corpus,
ink vs boundary, in each medium. Plain Python: no pytest, no full-suite lock."""
from __future__ import annotations
import sys, random

MODE = sys.argv[1]
if MODE == "vector":
    import probe_five_kinds
    class _C: pass
    probe_five_kinds.pytest_configure(_C())

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.page_ink import drawing_of, frame_centre_of

sys.path.insert(0, "tests/property")
import test_book_pdf_geometry as g

rng = random.Random(1160032)
worst = {k: [0.0, None] for k in ("ink_left", "ctr_left", "ink_top", "ctr_top",
                                  "ink_spare", "ctr_spare")}
checked = 0
for case in range(160):
    sheet = g.BOOK1 if case % 10 == 0 else g._random_sheet(rng)
    puzzle = g._puzzle(rng)
    columns, rows, across, down = g._extent(puzzle)
    if sheet.page_fit_mm(across, down) < g.MIN_CELL_MM: continue
    if columns <= 15 and rows <= 20: continue
    book_rows = [dict(puzzle, difficulty_tier="easy", id="p-easy"),
                 dict(puzzle, difficulty_tier="medium", id="p-medium"),
                 dict(puzzle, id="p-ungraded")]
    gen = BookPDFGenerator(sheet.book)
    toc = gen.section_plan(book_rows).toc_page_count
    pages = g._interior(gen, book_rows)
    numbers = (7 + toc, 8 + toc, 10 + toc, 11 + toc)
    spare = sheet.usable_width_mm - across * sheet.cell_mm(across, down)
    for number in numbers:
        page = pages[number - 1]
        d = drawing_of(page)
        c = frame_centre_of(page, d)
        exp_left = sheet.drawing_left_mm(number, across, down)
        tms = sheet.drawing_top_mm(across, down)
        for key, value in (
            ("ink_left", abs(g._mm(d.left) - exp_left)),
            ("ctr_left", abs(g._mm(c.frame_left) - exp_left)),
            ("ink_top", min(abs(g._mm(d.top) - t) for t in tms)),
            ("ctr_top", min(abs(g._mm(c.frame_top) - t) for t in tms)),
        ):
            if value > worst[key][0]:
                worst[key] = [value, (sheet.width_mm, sheet.height_mm, number, columns, rows)]
        if spare >= 0 and number in numbers[:2]:
            for key, edge in (("ink_spare", g._mm(d.left)), ("ctr_spare", g._mm(c.frame_left))):
                ls = edge - sheet.left_margin_mm(number)
                value = abs(ls - (spare - ls))
                if value > worst[key][0]:
                    worst[key] = [value, (sheet.width_mm, sheet.height_mm, number)]
    checked += 1
H = g.HALF_PIXEL_MM
print(f"=== {MODE} === checked={checked}  HALF_PIXEL_MM={H:.6f} mm")
for key, bound in (("left", 2), ("top", 3), ("spare", 4)):
    for which in ("ink", "ctr"):
        v, where = worst[f"{which}_{key}"]
        print(f"  {key:6s} {which}: worst {v:.6f} mm = {v/H:.3f} x HALF_PIXEL  "
              f"bound {bound} x  -> {'GREEN' if v <= bound*H + 1e-9 else 'RED'}   {where}")
