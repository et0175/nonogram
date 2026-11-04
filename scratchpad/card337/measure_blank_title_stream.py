"""CARD-337: does the blank title page's CONTENT STREAM state its blankness?

`test_no_mark_moves_on_any_page_bitmap` and EC-1's agreement test both assert
"interior page 1 is the blank title page (CARD-206)" by counting white pixels
on a bitmap. Page 1 is TITLE, which the five-kind probe converts, so that
reading has no subject. This measures whether the vector page carries an
equivalent declaration: a stream that paints nothing.

Reports, per interior page: the medium, the page's kind as the writer planned
it, the operator count, and every PDF PAINTING operator present.
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
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, export_of

# Every PDF operator that puts marks on the page: path painting, text showing,
# shading and XObject painting. Derived from PDF 32000-1 table 59/107/108/74,
# so "paints nothing" is a claim about the whole vocabulary rather than about
# the operators this page happens to use.
PAINTING = (
    "S", "s", "f", "F", "f*", "B", "B*", "b", "b*",
    "Tj", "TJ", "'", '"',
    "sh", "Do", "BI", "EI",
)

book = corpus_book("card-147")
book.interior_ink_mode = InkMode.BLACK_AND_WHITE.value

gen = BookPDFGenerator(book)
data = export_of(gen, baseline_puzzles())

parser = PdfParser.PdfParser(buf=data)
try:
    for n, ref in enumerate(parser.pages, 1):
        page = parser.read_indirect(ref)
        res = page[b"Resources"]
        if b"XObject" in res:
            print(f"page {n:>2}: raster")
            continue
        raw = zlib.decompress(parser.read_indirect(page[b"Contents"]).buf)
        toks = raw.decode("latin-1").split()
        painting = [t for t in toks if t in PAINTING]
        print(f"page {n:>2}: vector  stream_bytes={len(raw):<6} tokens={len(toks):<6} "
              f"painting_ops={len(painting)} {sorted(set(painting))}")
finally:
    parser.close()
