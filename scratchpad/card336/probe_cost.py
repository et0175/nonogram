"""CARD-336: how long test 2's corpus takes under the five-kind probe when it
runs to COMPLETION, with and without the frame-centre reading. No pytest, so
no 120 s per-test hang guard."""
from __future__ import annotations
import sys, time

import probe_five_kinds
class _C: pass
probe_five_kinds.pytest_configure(_C())

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of, frame_centre_of

sys.path.insert(0, "tests/property")
import test_book_pdf_geometry as g

WITH = "--with" in sys.argv
extents = [(c, r) for c in range(MIN_SIZE, MAX_SIZE + 1, 2) for r in range(MIN_SIZE, MAX_SIZE + 1, 2)]
extents += [(30, 10), (30, 12), (29, 11), (28, 10), (30, 15)]
start = time.perf_counter()
pages_seen = 0
import random
rng = random.Random(1160022)
for sheet in (g.BOOK1, g._random_sheet(rng)):
    puzzles = [g._puzzle(rng, c, r) for c, r in extents]
    gen = BookPDFGenerator(sheet.book)
    toc = gen.section_plan(puzzles).toc_page_count
    t0 = time.perf_counter()
    pages = g._interior(gen, puzzles)
    t1 = time.perf_counter()
    book_cells = sheet.book_cell_mm([g._extent(p) for p in puzzles])
    for i, p in enumerate(puzzles):
        page = pages[3 + toc + i]
        d = drawing_of(page)
        if WITH:
            frame_centre_of(page, d)
        pages_seen += 1
    t2 = time.perf_counter()
    print(f"  sheet {sheet.width_mm:.0f}x{sheet.height_mm:.0f}: "
          f"interior {t1-t0:.1f}s, measuring {t2-t1:.1f}s, pages {len(pages)}")
print(f"{'WITH' if WITH else 'WITHOUT'} frame_centre_of: total {time.perf_counter()-start:.1f}s "
      f"over {pages_seen} measured pages")
