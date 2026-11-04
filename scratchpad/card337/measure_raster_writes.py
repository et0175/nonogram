"""CARD-337: what `_write_page` actually sees under the five-kind probe.

`test_no_mark_moves_on_any_page_bitmap` counts `_write_page` calls and uses
that running count as **the interior page number** (`number = checked + 1`,
then `if number == 1: ...the blank title page`). This script measures whether
those two quantities are still the same thing once the five convertible kinds
go vector.

Run with the probe's lift applied by hand (the probe is a pytest plugin, so
its `pytest_configure` is called here explicitly, as a plugin-free lift).
"""
from __future__ import annotations

import sys
from io import BytesIO
from PIL import Image

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from scratchpad.card338 import probe_five_kinds


class _Config:
    pass


probe_five_kinds.pytest_configure(_Config())

from nonogram.admin.book_pdf_generator import BookPDFGenerator, PageKind, page_medium, PageMedium
from nonogram.admin.book_page_spec import InkMode
from tests.helpers.book_corpus import BASELINE_PAGE_COUNT, baseline_puzzles, corpus_book, export_of

print("media after the lift:")
for kind in PageKind:
    print(f"  {kind.name:<16} {page_medium(kind).name}")

book = corpus_book("card-147")
book.interior_ink_mode = InkMode.BLACK_AND_WHITE.value
generator = BookPDFGenerator(book)

real_write_page = BookPDFGenerator._write_page
calls = []


def spy(self, pdf, page, *args, **kwargs):
    calls.append((page.mode, page.size))
    return real_write_page(self, pdf, page, *args, **kwargs)


BookPDFGenerator._write_page = spy
try:
    export_of(generator, baseline_puzzles())
finally:
    BookPDFGenerator._write_page = real_write_page

print(f"\nBASELINE_PAGE_COUNT (interior pages) = {BASELINE_PAGE_COUNT}")
print(f"_write_page calls (raster pages)     = {len(calls)}")
for i, (mode, size) in enumerate(calls, 1):
    print(f"  raster write {i}: mode={mode} size={size}")
assert len(calls) != BASELINE_PAGE_COUNT or True
