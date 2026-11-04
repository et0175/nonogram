"""CARD-336: does an OVERFLOWING page (MIN_CELL_MM floor wins) still read framed?"""
from __future__ import annotations
import sys, random

MODE = sys.argv[1] if len(sys.argv) > 1 else "vector"
if MODE == "vector":
    import probe_five_kinds
    class _C: pass
    probe_five_kinds.pytest_configure(_C())

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of, frame_centre_of

sys.path.insert(0, "tests/property")
import test_book_pdf_geometry as g

rng = random.Random(1160022)
extents = [(c, r) for c in range(MIN_SIZE, MAX_SIZE + 1, 2) for r in range(MIN_SIZE, MAX_SIZE + 1, 2)]
extents += [(30, 10), (30, 12), (29, 11), (28, 10), (30, 15)]
worst_ink = worst_ctr = 0.0
for sheet in (g.BOOK1, g._random_sheet(rng)):
    puzzles = [g._puzzle(rng, c, r) for c, r in extents]
    gen = BookPDFGenerator(sheet.book)
    toc = gen.section_plan(puzzles).toc_page_count
    pages = g._interior(gen, puzzles)
    book_cells = sheet.book_cell_mm([g._extent(p) for p in puzzles])
    over = ok = 0
    for i, p in enumerate(puzzles):
        page = pages[3 + toc + i]
        cols, rws, acr, dwn = g._extent(p)
        d = drawing_of(page)
        overflow = sheet.page_fit_mm(acr, dwn) < g.MIN_CELL_MM
        tms = sheet.drawing_top_mm(acr, dwn, book_cells[(cols, rws)])
        ink = min(abs(g._mm(d.top) - t) for t in tms)
        try:
            c = frame_centre_of(page, d)
            ctr = min(abs(g._mm(c.frame_top) - t) for t in tms)
        except ValueError as e:
            print(f"  REFUSED {cols}x{rws} overflow={overflow} framed={d.framed}: {str(e)[:60]}")
            continue
        worst_ink = max(worst_ink, ink); worst_ctr = max(worst_ctr, ctr)
        if overflow: over += 1
        else: ok += 1
    print(f"sheet {sheet.width_mm:.0f}x{sheet.height_mm:.0f}: overflow={over} normal={ok}")
print(f"{MODE}: worst ink top residual {worst_ink:.4f} mm, worst centre {worst_ctr:.4f} mm, bound {3*g.HALF_PIXEL_MM:.4f}")
