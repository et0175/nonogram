"""CARD-336: which of test 3's four measured pages read framed=False, and why."""
from __future__ import annotations
import sys, random

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.page_ink import drawing_of, frame_centre_of

sys.path.insert(0, "tests/property")
import test_book_pdf_geometry as g

rng = random.Random(1160032)
tally = {}
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
    for label, number in (("puzzle", 7+toc), ("puzzle2", 8+toc),
                          ("answer", 10+toc), ("answer2", 11+toc)):
        d = drawing_of(pages[number-1])
        key = (label, d.framed)
        tally[key] = tally.get(key, 0) + 1
        if not d.framed and tally[key] <= 2:
            print(f"  UNFRAMED {label} p{number} {columns}x{rows} on "
                  f"{sheet.width_mm:.0f}x{sheet.height_mm:.0f}: {d}")
    checked += 1
print("checked", checked)
for k in sorted(tally, key=str):
    print(" ", k, tally[k])
