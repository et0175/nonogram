"""CARD-331: re-derive the three floors on the corpus as it is finally built."""
import sys
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-331/src")
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-331")
import tests.test_book_difficulty_dots as dd
from tests.helpers.round_ink import ink_regions, stream_marks

page = dd._arm_page()
regions = ink_regions(page.bitmap, dd.MARK_LEVEL)
print(f"raster arm: {len(regions)} ink regions at MARK_LEVEL on the bitmap page")
print(f"            {len(ink_regions(page.bitmap, dd.INK_LEVEL))} at INK_LEVEL")
print(f"            round: {[r.box for r in regions if r.is_round]}")

total = shaped = 0
pages = 0
for name, rows in dd.VECTOR_CORPUS_SOURCES:
    streams = dd._vector_pages(rows())
    per = []
    for stream in streams:
        marks = stream_marks(dd._stream_text(stream))
        per.append(len(marks))
        total += len(marks)
        shaped += sum(1 for m in marks if not m.is_degenerate)
    pages += len(streams)
    print(f"{name}: rows={len(rows())} pages={len(streams)} subpaths={per}")
print(f"corpus: {pages} pages, {total} painted subpaths, {shaped} shaped")
