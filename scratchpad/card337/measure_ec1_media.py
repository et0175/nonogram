"""CARD-337: the medium composition of EC-1's corpus, per book.

`test_the_two_modes_agree_on_every_page_of_every_book` reads every page as an
image XObject. This measures, per corpus book, how many pages are raster and
how many vector once the five kinds are lifted -- which is what says whether a
medium-gated re-expression still has a subject on each book, or whether some
book's raster arm is empty (an ADR-0039/R1 control that cannot fail).

Also reports each page's MediaBox, the medium-independent statement of the
trim that EC-019 names.
"""
from __future__ import annotations

import sys
import zlib

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from scratchpad.card338 import probe_five_kinds


class _Config:
    pass


probe_five_kinds.pytest_configure(_Config())

from PIL import PdfParser

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.admin.book_page_spec import InkMode
from tests.helpers.book_corpus import export_of
from tests.test_book_pdf_ink_mode import ec1_books, _ec1_book
from tests.helpers.page_ink import pdf_page_boxes


def media(data: bytes):
    parser = PdfParser.PdfParser(buf=data)
    try:
        out = []
        for ref in parser.pages:
            page = parser.read_indirect(ref)
            res = page[b"Resources"]
            if b"XObject" in res:
                (sref,) = res[b"XObject"].values()
                stream = parser.read_indirect(sref)
                cs = stream.dictionary[b"ColorSpace"]
                out.append(("raster", getattr(cs, "name", cs)))
            else:
                out.append(("vector", None))
        return out
    finally:
        parser.close()


total_raster = total_vector = total_pages = 0
books_with_no_raster = []
boxsets = set()
for entry in ec1_books():
    bw = export_of(BookPDFGenerator(_ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE)), entry["puzzles"])
    colour = export_of(BookPDFGenerator(_ec1_book(entry["trim"], InkMode.COLOUR)), entry["puzzles"])
    mb, mc = media(bw), media(colour)
    r = sum(1 for k, _ in mb if k == "raster")
    v = len(mb) - r
    total_raster += r
    total_vector += v
    total_pages += len(mb)
    if r == 0:
        books_with_no_raster.append(entry["label"])
    cs_bw = {c for k, c in mb if k == "raster"}
    cs_col = {c for k, c in mc if k == "raster"}
    boxes = pdf_page_boxes(bw)
    boxsets.add(tuple(sorted({tuple(b) for b in boxes})))
    print(f"{entry['label']:<28} pages={len(mb):>3}  raster={r:<3} vector={v:<3} "
          f"raster CS: bw={sorted(cs_bw)} colour={sorted(cs_col)}  "
          f"boxes_match={pdf_page_boxes(bw) == pdf_page_boxes(colour)}")

print()
print(f"books={len(ec1_books())}  pages={total_pages}  raster={total_raster}  vector={total_vector}")
print(f"books whose raster arm is EMPTY: {books_with_no_raster or 'none'}")
print(f"distinct MediaBox sets across the corpus: {len(boxsets)}")
