"""The assembly point for a vector book interior (CARD-309, ADR-0042/R1).

**What this module exists to resolve.** ADR-0042/R1 says the interior's four
page kinds — the guide, the table of contents, the puzzle pages and the answer
pages — are written as PDF content-stream operators. Four cards built the
writers, and three of them sit on the **wrong side of an import**:

* :mod:`nonogram.admin.book_guide_vector`,
  :mod:`nonogram.admin.book_toc_vector` and
  :mod:`nonogram.admin.book_answer_vector` import
  :mod:`nonogram.admin.book_pdf_generator` **at module level**, for the guide's
  and the TOC's text, the type sizes, ``page_frame``, ``type_px``,
  ``band_identity`` and ``_toc_entries_per_page``;
* :mod:`nonogram.admin.book_pdf_generator` holds the interior's **page walk**
  (``interior_stream``), and imports :mod:`nonogram.admin.book_puzzle_vector`
  and :mod:`nonogram.admin.book_sheet_vector`, both of which import no
  generator.

So the walk can reach the puzzle writer and **cannot reach the other three**:
importing them back is a cycle, and doing it lazily inside the walk is the
same cycle with its direction hidden in a function body. ADR-0042/R1's own
note records this as the third of its three blockers, and CARD-306 built
``book_sheet_vector`` kind-agnostic for all five kinds precisely so that the
furniture would not be the fourth.

**How it is resolved: the direction becomes a parameter, and this module is
the one place that can fill it.** ``book_pdf_generator`` states the shape it
needs — :class:`~nonogram.admin.book_pdf_generator.InteriorPageWriters`, four
callables with the downstream writers' own signatures — and nothing more; the
walk calls through an instance and imports no writer that imports it. This
module is downstream of **all** of them, so it is the only module in the
package that can see every page writer at once, and it is a leaf: **nothing in
``src/`` imports it**, which is what keeps the resolution a direction rather
than a loop with a door in it.

The puzzle page is deliberately **not** in the writer set. Its writer imports
no generator, so ``book_pdf_generator`` already imports it and composes the
page itself (``vector_puzzle_page``/``vector_two_up_page``, CARD-295 with
CARD-306's furniture). That is why the puzzle page is the kind CARD-309
converts and the other four are CARD-322's: converting it needs no assembly
point at all, so the two halves of this card can be judged separately.

**What this module does NOT do.** It chooses no medium. Which kinds are
operators is :func:`~nonogram.admin.book_pdf_generator.page_medium`'s single
decision, read off
:data:`~nonogram.admin.book_pdf_generator._RASTER_DECLARATIONS`, and a
generator built here draws exactly the kinds that registry leaves undeclared.
Composing an interior through this module therefore does **not** make the
interior vector; lifting a declaration does, and this module is what stops
that lift from being a refusal.

It also measures nothing and draws nothing: every figure a page is drawn from
is the walk's own (ADR-0042/R3), and the four entries below are bindings, not
adapters — three of them are the writer's own function and the fourth unwraps
:class:`~nonogram.admin.book_guide_vector.GuidePage` to the stream the walk
yields.
"""

from __future__ import annotations

from typing import Any, Optional

from nonogram.admin.book_answer_vector import answer_page, packed_answer_page
from nonogram.admin.book_guide_vector import guide_page
from nonogram.admin.book_pdf_generator import BookPDFGenerator, InteriorPageWriters
from nonogram.admin.book_toc_vector import toc_page_stream
from nonogram.admin.book_vector import ContentStream
from nonogram.export.layout import PageSpec

__all__ = [
    "DOWNSTREAM_WRITERS",
    "guide_page_stream",
    "interior_generator",
]


def guide_page_stream(
    spec: PageSpec,
    dpi: int,
    page_number: int,
    *,
    puzzle_count: int = 0,
    easy_count: int = 0,
    medium_count: int = 0,
    hard_count: int = 0,
) -> ContentStream:
    """One guide page as the stream the interior's walk yields.

    :func:`~nonogram.admin.book_guide_vector.guide_page`'s own call, in its own
    order, returning its :class:`~nonogram.admin.book_guide_vector.GuidePage`'s
    ``stream``. It exists because that writer hands back the page *and* the
    measurements its own tests read, while the walk yields one page object per
    page — so the unwrapping is the assembly point's business and not a second
    guide-page function.
    """
    return guide_page(
        spec,
        dpi,
        page_number,
        puzzle_count=puzzle_count,
        easy_count=easy_count,
        medium_count=medium_count,
        hard_count=hard_count,
    ).stream


#: Every downstream interior page writer, bound for the walk that cannot
#: import them.
#:
#: A module-level constant rather than a factory because it holds no state and
#: binds no book: the four entries are functions, and the figures each page is
#: drawn from arrive at the call. One instance per process is therefore the
#: honest shape, and a caller that wants a narrower set (one kind only, for a
#: control) builds its own
#: :class:`~nonogram.admin.book_pdf_generator.InteriorPageWriters`.
DOWNSTREAM_WRITERS = InteriorPageWriters(
    guide=guide_page_stream,
    toc=toc_page_stream,
    answer=answer_page,
    packed_answer=packed_answer_page,
)


def interior_generator(
    book: Any = None, pages: Optional[InteriorPageWriters] = None
) -> BookPDFGenerator:
    """A :class:`~nonogram.admin.book_pdf_generator.BookPDFGenerator` that can
    write **every** interior kind in the medium its kind declares.

    The one call a route or a test makes to get an assembled interior:
    ``BookPDFGenerator(book)`` is the same generator with no downstream writers
    at all, which refuses — rather than rasterises — a kind
    :func:`~nonogram.admin.book_pdf_generator.page_medium` calls vector and it
    cannot draw.

    ``pages`` overrides :data:`DOWNSTREAM_WRITERS` and is here for a control
    that needs a partial set: the refusal's own test has to be able to hand in
    a writer set with one kind missing, and reaching into a module constant to
    do it would be mutating the thing under test.
    """
    return BookPDFGenerator(
        book, pages=DOWNSTREAM_WRITERS if pages is None else pages
    )
