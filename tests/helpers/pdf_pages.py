"""Read back the pages of a book PDF, in whichever medium each page was
written, and tell pages apart (CARD-135, CARD-329).

The dependency baseline has no PDF reader (ADR-0006), and for a **raster**
page it does not need one: ``BookPDFGenerator`` writes such a page as a
single image through Pillow, and Pillow's own :mod:`PIL.PdfParser` reads the
file's page tree back. Each raster page's one image XObject is DCT (JPEG)
data, which Pillow decodes.

:func:`same_page` compares two page images tolerantly, because the PDF's JPEG
round trip changes pixels a little. It compares ink (dark pixels) masks, so a
mostly-white guide page and a mostly-white title cover — whose mean colours
are nearly equal — still read as different pages.

The medium (CARD-329)
---------------------
ADR-0042/R1 writes the interior's pages as content-stream **operators**, and
such a page has no image XObject at all. Before CARD-329 the reader below
indexed ``Resources/XObject`` unconditionally and a legal operators page came
back as ``KeyError: b'XObject'`` — an exception that names neither the medium
nor a remedy, from a line that reads as a parse failure. That was the defect.

**The decision, and why.** The reader now *returns a usable result*: it
rasterises an operators page with **poppler** and hands back an
:class:`PIL.Image.Image` like any other page. It refuses — loudly, naming the
medium — only when it genuinely cannot, which is when no DPI to rasterise at
can be established. Both halves were on the table and the reason for this one
is that **a refusal changes no verdict**. Every caller here reads a page's
pixels; swapping ``KeyError`` for a well-worded exception leaves each of them
exactly as red as it was, which is a better message and not a reader that
survived a conversion. ADR-0042/R6 asks that a claim about an interior page be
*asserted against* that page, so the reader has to produce one.

**Why poppler and not an operator interpreter of our own.** The engine must
not be the engine that wrote the file: an agreement between this project's
writer and this project's reader proves only that two of its functions agree
(CLAUDE.md, "prefer an independent second implementation"). ``pdftoppm`` did
not write the file. This is also the seam the tree had already chosen — see
``tests/test_book_pdf.py``'s edge-reading helper, which writes one
``ContentStream`` out with ``write_vector_pdf`` and measures poppler's
raster of it — and :mod:`tests.helpers.pdf_vector`, CARD-294's vector reader,
is where that call lives. A missing poppler is a **missing engine**, so it is
said out loud and never skipped green (ADR-0038/R8).

**Both readings stay in one domain.** A page this module returns is always
device pixels at the page's own DPI, whether Pillow decoded a JPEG or poppler
rasterised operators, so a caller comparing two of them is comparing like
with like (CARD-330). :func:`page_medium_of` says which, for a caller that
needs to know rather than guess.

**What is still not here.** The independent pixel *oracles* —
``drawing_of`` and ``two_up_ink`` — are ``tests/helpers/page_ink.py``'s and
stay there: this module is a reader that assertions use, not the oracle they
assert through, and folding the two together would destroy the cross-check
(CARD-329 G-2). Nothing below measures a drawing.
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterator, Optional, Sequence, Union

import numpy as np
from PIL import Image, PdfParser

from nonogram.admin.book_vector import ContentStream, write_vector_pdf
from tests.helpers import pdf_vector

#: A page as this tree hands one around: the bitmap a raster page is, or the
#: operators a vector page is (``BookPDFGenerator.interior_pages``' own union).
Page = Union[Image.Image, ContentStream]

#: What :func:`page_medium_of` answers. The same two words
#: ``tests/helpers/pdf_vector.py``'s :func:`~tests.helpers.pdf_vector.page_media`
#: uses, so "raster" and "vector" mean one thing across the test tree.
RASTER = "raster"
VECTOR = "vector"

#: PDF points per inch. The unit a MediaBox is in.
_POINTS_PER_INCH = 72.0


@contextmanager
def _scratch(out_dir: Optional[Path]) -> Iterator[Path]:
    """Where poppler writes the PDF it reads and the PNG it produces.

    ``pdftoppm`` writes both side by side and
    :func:`tests.helpers.pdf_vector.rendered_page` defaults that location to
    the **current** directory, which under pytest is the repo root — so every
    caller in this tree hands it a path. This reader hands it a fresh
    temporary directory when its own caller gave none, rather than passing the
    default through: a reader that litters the checkout on a page it was
    merely asked to read is a trap, and a caller deep inside a page walk has
    no ``tmp_path`` to offer.
    """
    if out_dir is not None:
        yield out_dir
        return
    with tempfile.TemporaryDirectory(prefix="pdf_pages-") as directory:
        yield Path(directory)


class PageMediumRefused(AssertionError):
    """A page could not be read, and the message names the medium.

    An :class:`AssertionError` because every caller is a test assertion and
    this is one of them failing — not a bug in the reader. It replaces
    ``KeyError: b'XObject'``, which named nothing.
    """


def page_medium_of(page: Page) -> str:
    """Which medium ``page`` is written in: :data:`RASTER` or :data:`VECTOR`.

    Raises:
        PageMediumRefused: ``page`` is neither, so the reader cannot classify
            it. An unanalysable shape is a FAILURE, not a silent pass
            (ADR-0039/R2).
    """
    if isinstance(page, Image.Image):
        return RASTER
    if isinstance(page, ContentStream):
        return VECTOR
    raise PageMediumRefused(
        f"a book page is a bitmap or a content stream; this one is a "
        f"{type(page).__name__}, whose medium this reader cannot name"
    )


def page_image(page: Page, *, out_dir: Optional[Path] = None) -> Image.Image:
    """``page`` as the bitmap it draws, whichever medium it was written in.

    A raster page is returned **unchanged** — the very object handed in, not a
    copy and not a conversion, so a caller reading ``tobytes()`` off it reads
    the same bytes it read before CARD-329 (AC-2). A vector page is written
    out as a one-page PDF and rasterised by poppler at the stream's **own**
    DPI, so the result is device pixels on the same scale as the raster page
    beside it.

    Args:
        page: One page of ``interior_pages()`` / ``interior().pages``.
        out_dir: Where poppler's scratch files go. A fresh temporary
            directory when omitted (:func:`_scratch`), so reading a page never
            writes into the checkout.

    Raises:
        PageMediumRefused: the page is operators and poppler is not on this
            host, so there is no engine to read it with. Said out loud rather
            than skipped (ADR-0038/R8).
    """
    if page_medium_of(page) == RASTER:
        return page
    if pdf_vector.PDFTOPPM is None:
        raise PageMediumRefused(
            "this page is written as content-stream operators (ADR-0042/R1) "
            "and poppler's pdftoppm, the engine that reads one, is not on "
            "this host: the reading is MISSING, not passed"
        )
    written = write_vector_pdf([page], 1).getvalue()
    with _scratch(out_dir) as directory:
        rendered = pdf_vector.rendered_page(
            written, int(round(page.dpi)), 1, out_dir=directory
        )
    image = Image.fromarray(np.asarray(rendered, dtype=np.uint8), mode="L")
    return image.convert("RGB")


def interior_images(
    pages: Sequence[Page], *, out_dir: Optional[Path] = None
) -> list[Image.Image]:
    """Every page of ``pages`` as a bitmap, in order — :func:`page_image` over
    a whole interior.

    The one-line seam a module measuring a rendered interior moves to so its
    claims survive ADR-0042/R1's conversion: the pages arrive in whichever
    medium their kind declares and leave as device pixels at each page's own
    DPI, which is the domain every assertion downstream of it already reads.
    """
    return [page_image(page, out_dir=out_dir) for page in pages]


def _derived_dpi(boxes: list[tuple[float, float, float, float]],
                 images: dict[int, Image.Image]) -> Optional[float]:
    """The DPI a file's own **raster** pages are drawn at, or ``None``.

    Derived from the file, not asked of the generator: a page's pixel width
    over its MediaBox width in inches. That is an independent second reading
    of the same number the writer used (CLAUDE.md), and it is the only way a
    reader holding nothing but bytes can know the scale to rasterise a vector
    page to so that it matches its raster neighbours.

    ``None`` when the file has no raster page to derive it from, and when its
    raster pages disagree — a file drawn at two DPIs has no single answer, and
    guessing one is how a reading ends up in a domain nobody named.
    """
    derived = set()
    for index, image in images.items():
        left, bottom, right, top = boxes[index]
        inches = (right - left) / _POINTS_PER_INCH
        if inches <= 0:
            continue
        derived.add(round(image.width / inches, 3))
    return derived.pop() if len(derived) == 1 else None


def pdf_pages(data: bytes, *, dpi: Optional[float] = None,
              out_dir: Optional[Path] = None) -> list[Image.Image]:
    """Every page of ``data`` in page order, as the image the page draws.

    A page drawn as one image XObject is decoded by Pillow, exactly as it was
    before CARD-329. A page drawn as operators is rasterised by poppler at
    ``dpi``, or — when ``dpi`` is not given — at the DPI the file's own raster
    pages are drawn at (:func:`_derived_dpi`), so that a mixed-medium book
    comes back as one stack of comparable bitmaps and a caller needs no
    argument it did not need before.

    Args:
        data: A book PDF's bytes, as a route or ``export_book`` produced them.
        dpi: The scale to rasterise an operators page at. Derived from the
            file when omitted.
        out_dir: Poppler's scratch directory; a fresh temporary one when
            omitted. See :func:`page_image`.

    Raises:
        PageMediumRefused: the file holds an operators page and the DPI to
            read it at could not be established — no ``dpi`` was given and the
            file carries no raster page to derive one from (or carries raster
            pages at disagreeing DPIs). The message names the medium and the
            page.
        PageMediumRefused: poppler is not on this host.
    """
    parser = PdfParser.PdfParser(buf=data)
    try:
        boxes: list[tuple[float, float, float, float]] = []
        operators: dict[int, bytes] = {}
        images: dict[int, Image.Image] = {}
        for index, ref in enumerate(parser.pages):
            page = parser.read_indirect(ref)
            left, bottom, right, top = page[b"MediaBox"]
            boxes.append((float(left), float(bottom), float(right), float(top)))
            resources = page[b"Resources"]
            if b"XObject" not in resources:
                # A legal page, and the one CARD-329 exists for: operators,
                # so there is no image to decode. Held until the whole page
                # tree is read, because the DPI to rasterise it at is derived
                # from the file's *other* pages.
                operators[index] = parser.read_indirect(page[b"Contents"]).decode()
                continue
            xobjects = resources[b"XObject"]
            assert len(xobjects) == 1, "a raster book page is exactly one image"
            (stream_ref,) = xobjects.values()
            stream = parser.read_indirect(stream_ref)
            assert stream.dictionary[b"Filter"] == b"DCTDecode"
            image = Image.open(BytesIO(stream.buf))
            image.load()
            images[index] = image.convert("RGB")
    finally:
        parser.close()

    if operators:
        scale = dpi if dpi is not None else _derived_dpi(boxes, images)
        if scale is None:
            raise PageMediumRefused(
                f"page {min(operators) + 1} of {len(boxes)} is written as "
                f"content-stream operators (ADR-0042/R1), not as an image "
                f"XObject, and the DPI to rasterise it at could not be "
                f"established: no dpi= was given and this file's "
                f"{len(images)} raster page(s) do not settle one. Pass dpi=, "
                f"or read the stream itself with tests/helpers/pdf_vector.py"
            )
        if pdf_vector.PDFTOPPM is None:
            raise PageMediumRefused(
                f"page {min(operators) + 1} of {len(boxes)} is written as "
                f"content-stream operators (ADR-0042/R1) and poppler's "
                f"pdftoppm, the engine that reads one, is not on this host: "
                f"the reading is MISSING, not passed"
            )
        with _scratch(out_dir) as directory:
            for index in operators:
                rendered = pdf_vector.rendered_page(
                    data, int(round(scale)), index + 1, out_dir=directory
                )
                images[index] = Image.fromarray(
                    np.asarray(rendered, dtype=np.uint8), mode="L"
                ).convert("RGB")

    return [images[index] for index in range(len(boxes))]

#: Down-sampling factor for comparisons: fast, and still far finer than text.
_REDUCE = 6
#: A pixel darker than this (0..255 grey) is ink.
_INK_LEVEL = 128


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
