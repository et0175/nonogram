"""Read back the pages of a PDF Pillow wrote, and tell pages apart (CARD-135).

The dependency baseline has no PDF reader (ADR-0006), but it does not need
one for the book export: ``BookPDFGenerator`` writes every page as a single
image through Pillow, and Pillow's own :mod:`PIL.PdfParser` reads that file's
page tree back. Each page's one image XObject is DCT (JPEG) data, which
Pillow decodes. This helper deliberately does not call the generator — it
reads the bytes a route or ``export_book`` produced.

:func:`same_page` compares two page images tolerantly, because the PDF's JPEG
round trip changes pixels a little. It compares ink (dark pixels) masks, so a
mostly-white guide page and a mostly-white title cover — whose mean colours
are nearly equal — still read as different pages.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, PdfParser

#: Down-sampling factor for comparisons: fast, and still far finer than text.
_REDUCE = 6
#: A pixel darker than this (0..255 grey) is ink.
_INK_LEVEL = 128


def pdf_pages(data: bytes) -> list[Image.Image]:
    """Every page of ``data`` in page order, as the image the page draws."""
    parser = PdfParser.PdfParser(buf=data)
    try:
        images = []
        for ref in parser.pages:
            page = parser.read_indirect(ref)
            xobjects = page[b"Resources"][b"XObject"]
            assert len(xobjects) == 1, "a book page is exactly one image"
            (stream_ref,) = xobjects.values()
            stream = parser.read_indirect(stream_ref)
            assert stream.dictionary[b"Filter"] == b"DCTDecode"
            image = Image.open(BytesIO(stream.buf))
            image.load()
            images.append(image.convert("RGB"))
        return images
    finally:
        parser.close()


def pdf_page_count(data: bytes) -> int:
    """How many pages the PDF's page tree holds."""
    parser = PdfParser.PdfParser(buf=data)
    try:
        return len(parser.pages)
    finally:
        parser.close()


def _ink(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L").reduce(_REDUCE)) < _INK_LEVEL


def _grey(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L").reduce(_REDUCE), dtype=np.int16)


def same_page(a: Image.Image, b: Image.Image) -> bool:
    """Whether ``a`` and ``b`` are the same page, up to JPEG noise."""
    if a.size != b.size:
        return False
    ink_a, ink_b = _ink(a), _ink(b)
    union = np.logical_or(ink_a, ink_b).sum()
    if union:
        overlap = np.logical_and(ink_a, ink_b).sum() / union
        if overlap < 0.9:
            return False
    return float(np.abs(_grey(a) - _grey(b)).mean()) < 6.0
