"""The disagreeing-DPI file F-003's second arm needs, built and proven.

Shows that this tree's writer cannot produce one (Pillow takes one
resolution per file) and that an equal-length byte patch of one page's
MediaBox does, with the xref offsets left valid.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from nonogram.admin.book_pdf_generator import _RASTER_DECLARATIONS, PageKind  # noqa
from tests.helpers.pdf_pages import PageMediumRefused, _derived_dpi, pdf_pages  # noqa
import tests.test_book_pdf as T  # noqa

del _RASTER_DECLARATIONS[PageKind.PUZZLE]
generator, bitmap, stream = T._one_vector_page()
written = generator._write_pdf(
    [bitmap, bitmap, stream], 3, mode="RGB",
    kinds=[PageKind.COVER, PageKind.DIVIDER, PageKind.PUZZLE],
).getvalue()
boxes = re.findall(rb"/MediaBox[^\]]*\]", written)
print("MediaBoxes:", boxes)
print("bitmap size:", bitmap.size)

target = boxes[0]
m = re.match(rb"/MediaBox \[ 0 0 ([0-9.]+) ([0-9.]+) \]", target)
print("match:", m and m.groups())
if m:
    w = m.group(1)
    half = b"%.*f" % (len(w.split(b".")[1]), float(w) / 2)
    print("width %r -> %r  (same length: %s)" % (w, half, len(w) == len(half)))
    patched = written.replace(target, target.replace(w, half, 1), 1)
    print("count of target in file:", written.count(target), " len same:", len(patched) == len(written))
    try:
        pdf_pages(patched)
        print("NO REFUSAL -- arm not reached")
    except PageMediumRefused as refused:
        print("REFUSED:", str(refused)[:300])
    except Exception as other:
        print("OTHER:", type(other).__name__, other)
