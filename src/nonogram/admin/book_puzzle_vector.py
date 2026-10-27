"""The puzzle page as PDF operators: the grid, the frame, the digits, the band.

CARD-295, the second implementation of **ADR-0042** (DEC-048) and the first
*page* under it. The book's dominant page kind, drawn as a content stream
instead of a 25,245,000-byte RGB bitmap written into the file as a JPEG
XObject.

Everything geometric this module draws, it draws through
:mod:`nonogram.admin.book_vector_draw`, which knows no page kind. What is
*here* is only what makes a page a **puzzle page**, and it is a short list:

* a puzzle page's slot is a drawing (grid, frame, clue digits) **plus a band**;
* the band reads ``"Puzzle 12 · Easy"`` — :func:`~nonogram.admin.book_pdf_generator.band_identity`'s
  line, the number and the tier — and **never the picture's title**
  (ADR-0037/R1: the answer key is the only place a title is printed);
* the band is set at the size COMP-007's
  :func:`~nonogram.export.layout.header_band` states, shrunk once if the line
  would not fit the room it is given, by the same rule the raster page uses.

What this module deliberately does **not** draw, named rather than left to
look covered
----------------------------------------------------------------------------

**The sheet's furniture**: the interior frame's header rule and footer rule,
the footer's grid-size label, the folio, and the QR icon with its two caption
lines (``book_pdf_generator._draw_page_frame``, ``_draw_qr_caption``,
CARD-200/CARD-222/CARD-223). None of it is a puzzle-page mark — every
interior page kind carries the same furniture off the same
:func:`~nonogram.export.layout.interior_frame`, and a page card that drew it
would be the second of four to do so. It is **not drawn by any card in the
ADR-0042 phase as the phase stands on 2026-10-26**, which is a gap this card
raises rather than closes: the card that makes the medium real per page is
**CARD-298**, and it cannot land a vector puzzle page that has no page number
on it. ``tests/test_book_puzzle_page_vector.py``'s
``TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture`` holds the
boundary where this docstring claims it is, so the gap cannot quietly close
or quietly widen.

**Two-up pages are in scope** (:func:`two_up_page_stream`), because a two-up
slot *is* a puzzle page — ``_two_up_page`` draws each of its two slots with
the same three calls a single page's drawing takes, plus the same band. The
pair's shared furniture is the sheet's, as above.
"""

from __future__ import annotations

from typing import Sequence

from nonogram.admin.book_vector import ContentStream, FontMetrics, interior_face_metrics
from nonogram.admin.book_vector_draw import (
    INK_GREY,
    draw_clue_digits,
    draw_frame,
    draw_ruled_grid,
    page_stream,
    set_centred,
)
from nonogram.export.layout import HeaderBand, Layout

__all__ = [
    "BAND_WIDTH_RATIO",
    "MIN_BAND_FONT_RATIO",
    "band_type_size",
    "draw_band",
    "draw_puzzle_slot",
    "puzzle_page_stream",
    "slot_room",
    "two_up_page_stream",
]

#: How much of a slot's usable width a band's line may fill before it is set
#: smaller. The raster page's own figure, which is one number held in two
#: places already — ``book_pdf_generator._BAND_WIDTH_RATIO`` for a two-up
#: slot and ``export.pdf._HEADER_WIDTH_RATIO`` for every other page — and is
#: reimplemented here rather than imported, per this package's standing
#: convention for logic shared across a boundary (``_stroke_drawing``,
#: ``mask_runs``). The three are held equal from the test tree, where the
#: imports are legal, by
#: ``TestPuzzlePage_TheBandFitsTheWayTheRasterPageFitsIt``.
BAND_WIDTH_RATIO = 0.9

#: The floor the shrink stops at, as a fraction of the band's own type size.
#: The same number, in the same two places, for the same reason.
MIN_BAND_FONT_RATIO = 1 / 3


def slot_room(layout: Layout) -> int:
    """The width a band drawn on ``layout`` has to fit inside, in pixels.

    The slot's usable extent, which is the measurement both the raster
    callers fit a header against — ``_two_up_page``'s
    ``placement.usable_right - placement.usable_left`` and
    ``pdf.render_pages``' ``room``. Read off the placement rather than
    computed: this is COMP-007's number (ADR-0042/R3).

    Raises:
        ValueError: ``layout`` is not a placed page. An unplaced drawing has
            no usable area and no reserved band — the raster path grows a
            taller canvas for one (``pdf._titled``), which a book page cannot
            do because its size is the trim. A caller holding one is holding
            the wrong layout, and that is worth a name rather than a default.
    """
    placement = layout.page
    if placement is None:
        raise ValueError(
            "a puzzle page's band is measured against its placed page's usable "
            "width, and this layout has no PagePlacement: it was computed with "
            "no PageSpec, so it is a drawing-sized image rather than a book page"
        )
    return placement.usable_right - placement.usable_left


def band_type_size(
    text: str, band: HeaderBand, room: float, metrics: FontMetrics
) -> float:
    """The size ``text`` is set at in ``band``: its own, or shrunk once to fit.

    :attr:`~nonogram.export.layout.HeaderBand.font_size` unless the line
    would set wider than :data:`BAND_WIDTH_RATIO` of ``room``, in which case
    it is set at the largest size that fits, floored at
    :data:`MIN_BAND_FONT_RATIO` of the stated size. **One measurement and one
    correction**, exactly as ``_set_band`` and ``pdf._draw_header`` do it,
    because a face's advances scale with its size and so the first correction
    is already the answer.

    The export's *third* fitting step — eliding the first piece — is
    deliberately absent, and cannot be reached: it exists for a picture's
    name, and a puzzle page's band is the one piece
    :func:`~nonogram.admin.book_pdf_generator.band_identity` composes, bounded
    by the book's membership and ADR-0031's three tier labels. Eliding that
    piece would cut the number the answer key is looked up by. (``_set_band``
    makes the same argument at greater length; this is the same two steps for
    the same reason.)
    """
    size = band.font_size
    usable = room * BAND_WIDTH_RATIO
    width = metrics.advance(text) * size
    if width > usable:
        size = max(
            round(band.font_size * MIN_BAND_FONT_RATIO), int(size * usable / width)
        )
    return size


def draw_band(
    stream: ContentStream,
    band: HeaderBand,
    text: str,
    room: float,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """Set ``text`` in ``band``, centred, shrunk if it would not fit ``room``.

    Nothing is drawn for an empty line or a band with no height — a sheet
    whose ``PageSpec`` reserves no band has nowhere to put one, and a page
    with no identity has nothing to say. Both are ``_set_band``'s own two
    guards.
    """
    if band.height <= 0 or not text:
        return
    set_centred(
        stream,
        text,
        band.center_x,
        band.center_y,
        band_type_size(text, band, room, metrics),
        metrics,
        grey=grey,
    )


def draw_puzzle_slot(
    stream: ContentStream,
    layout: Layout,
    band: HeaderBand,
    text: str,
    room: float,
    *,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> None:
    """Draw one puzzle onto ``stream``: its drawing and its band.

    The whole of a puzzle page's own ink, in the order the raster page puts it
    down (``_two_up_page``: the grid, the clues, the band; the frame last of
    the three ruled marks, as ``_stroke_drawing`` strokes it, so a heavy line
    crossing a thin one stays continuous).

    A slot rather than a page, because a two-up page holds two of them and
    the band is per *puzzle* while the sheet is per *page*
    (:func:`two_up_page_stream`).

    Args:
        stream: The page being drawn.
        layout: The slot's geometry, from ``compute_layout`` or a
            ``PairLayout``'s ``upper``/``lower``.
        band: ``header_band(layout)`` — COMP-007's strip for this slot.
        text: The band's line, ``band_identity``'s. ADR-0037/R1 is a property
            of *what is passed here*, and the caller is where it is kept: this
            function sets the string it is given.
        room: The width the band fits inside (:func:`slot_room`).
        metrics: The embedded face's metrics; the interior's own by default.
        grey: The ink, as a grey level.
    """
    measured = interior_face_metrics() if metrics is None else metrics
    draw_ruled_grid(stream, layout, grey=grey)
    if layout.frame is not None:
        draw_frame(stream, layout.frame, grey=grey)
    draw_clue_digits(stream, layout, measured, grey=grey)
    draw_band(stream, band, text, room, measured, grey=grey)


def puzzle_page_stream(
    layout: Layout,
    band: HeaderBand,
    text: str,
    room: float | None = None,
    *,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> ContentStream:
    """One single-puzzle page, as the stream its ``/Contents`` holds.

    ``room`` defaults to :func:`slot_room`'s answer for ``layout``, which is
    what every book page's caller wants; it is an argument so that a caller
    with a measured room (a pair's slot) can state it.
    """
    stream = page_stream(layout)
    draw_puzzle_slot(
        stream,
        layout,
        band,
        text,
        slot_room(layout) if room is None else room,
        metrics=metrics,
        grey=grey,
    )
    return stream


def two_up_page_stream(
    slots: Sequence[tuple[Layout, HeaderBand, str]],
    *,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> ContentStream:
    """A page holding several puzzles, each with its own band.

    The pair's two slots are the same size — a ``PairLayout`` places both on
    one trim — so the page's extent is the first slot's, exactly as
    ``_two_up_page`` builds its canvas from ``pair.upper``.

    Raises:
        ValueError: ``slots`` is empty. A page with no puzzle on it is not a
            puzzle page, and an empty stream would be a blank sheet in the
            middle of the book.
    """
    if not slots:
        raise ValueError("a puzzle page carries at least one puzzle")
    stream = page_stream(slots[0][0])
    for layout, band, text in slots:
        draw_puzzle_slot(
            stream,
            layout,
            band,
            text,
            slot_room(layout),
            metrics=metrics,
            grey=grey,
        )
    return stream
