"""CARD-337: EC-1's real page total, with and without the probe.

`EC1_PAGES = 117`'s comment says 117 is "the number the corpus above really
produces -- measured, not a bound with room in it -- so one page fewer fails".
This re-derives it, under both media, because a floor with slack in it is the
defect that constant's own comment claims to prevent (ADR-0039/R1).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "src")
sys.path.insert(0, ".")

if "--probe" in sys.argv:
    from scratchpad.card338 import probe_five_kinds

    class _Config:
        pass

    probe_five_kinds.pytest_configure(_Config())
    label = "five-kind probe (vector)"
else:
    label = "as committed (raster)"

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.admin.book_page_spec import InkMode
from tests.helpers.book_corpus import export_of
from tests.helpers.pdf_pages import pdf_page_count
from tests.test_book_pdf_ink_mode import EC1_BOOKS, EC1_PAGES, ec1_books, _ec1_book

total = 0
counts = []
for entry in ec1_books():
    bw = export_of(BookPDFGenerator(_ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE)), entry["puzzles"])
    n = pdf_page_count(bw)
    counts.append(n)
    total += n

print(f"{label}: books={len(counts)} (EC1_BOOKS={EC1_BOOKS})")
print(f"  per-book page counts: {counts}")
print(f"  total pages = {total}   EC1_PAGES constant = {EC1_PAGES}   slack = {total - EC1_PAGES}")
