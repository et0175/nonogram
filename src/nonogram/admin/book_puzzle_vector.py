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
the footer's grid-size label, the folio, and the pointer to the Play online
page (``book_pdf_generator._draw_page_frame``, CARD-200/CARD-222/CARD-391). None of it is a puzzle-page mark — every
interior page kind carries the same furniture off the same
:func:`~nonogram.export.layout.interior_frame`, and a page card that drew it
would be the second of four to do so.

**CARD-306 closed that gap, and not here.** This docstring said for three
cards that the furniture was drawn by nothing in the ADR-0042 phase and
named CARD-298 as the card that owed it; CARD-298 was narrowed to the
mechanism and could not. It is now drawn **once**, by
:mod:`nonogram.admin.book_sheet_vector`, and composed by
:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.vector_puzzle_page`
— which is where the words and the type sizes live. So the statement above
is still true of *this module*: a page drawn by
:func:`puzzle_page_stream` carries the drawing and the band and no sheet
furniture, and a page the **book** writes carries both.
``tests/test_book_puzzle_page_vector.py``'s
``TestPuzzlePageStream_TheBareWriterDrawsOnlyTheDrawingAndTheBand`` holds that
boundary where this docstring claims it is, on this module's own call.

**Two-up pages are in scope** (:func:`two_up_page_stream`), because a two-up
slot *is* a puzzle page — ``_two_up_page`` draws each of its two slots with
the same three calls a single page's drawing takes, plus the same band. The
pair's shared furniture is the sheet's, as above.
"""

from __future__ import annotations

from typing import Sequence

from nonogram.admin.book_vector import ContentStream, FontMetrics, interior_face_metrics
from nonogram.admin.book_plan import TIERS
from nonogram.admin.book_vector_draw import (
    INK_GREY,
    _middle_em,
    draw_clue_digits,
    draw_difficulty_dots,
    draw_frame,
    draw_ruled_grid,
    page_stream,
    set_centred,
)
from nonogram.difficulty import tier_of_record
from nonogram.export.layout import (
    DIFFICULTY_DOT_GAP_RATIO,
    DIFFICULTY_DOT_RATIO,
    INTERIOR_FOOTER_LINE_PT,
    HeaderBand,
    Layout,
    difficulty_dots,
    interior_header_rule_px,
)

__all__ = [
    "BAND_WIDTH_RATIO",
    "CLUE_SHADE",
    "MIN_BAND_FONT_RATIO",
    "band_type_size",
    "draw_band",
    "draw_puzzle_header",
    "draw_puzzle_slot",
    "draw_tier_dots",
    "puzzle_page_stream",
    "shade_clue_cells",
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


#: The band line's separator, ``book_pdf_generator.BAND_SEPARATOR``'s value:
#: restated rather than imported, because that module imports this one.
_SEPARATOR = " · "

#: The clue cells' tint (the approved mockup's #f1f2f4), as a grey level.
CLUE_SHADE = 0.945

#: The tier word against the number's size, and the stroke that sets the
#: number as a semibold on the one embedded face (ADR-0042/R5).
_TIER_RATIO = 0.75
_BOLD_RATIO = 0.04


def shade_clue_cells(stream: ContentStream, layout: Layout, *, shade: float = CLUE_SHADE) -> None:
    """Tint the row-clue and column-clue gutters, under the rules and digits.

    On a placed page the tint starts at the drawing's own edges: there the
    pitch is fractional and ``layout.cell`` is it floored, so ``gutter x cell``
    would stop short of the outermost clue box by up to a pixel per box.
    """
    stream.fill_grey(shade)
    placement = layout.page
    if layout.row_gutter_cells:
        left = (
            layout.grid_left - layout.row_gutter_cells * layout.cell
            if placement is None else placement.drawing_left
        )
        stream.rectangle(left, layout.grid_top, layout.grid_left, layout.grid_bottom, paint="fill")
    if layout.column_gutter_cells:
        top = (
            layout.grid_top - layout.column_gutter_cells * layout.cell
            if placement is None else placement.drawing_top
        )
        stream.rectangle(layout.grid_left, top, layout.grid_right, layout.grid_top, paint="fill")


def draw_puzzle_header(
    stream: ContentStream,
    layout: Layout,
    band: HeaderBand,
    text: str,
    room: float,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """The approved mockup's header: "Puzzle N" flush left, dots and tier flush right.

    ``text`` is ``band_identity``'s line; it is split at its separator, so the
    words are still that function's (ADR-0037/R1). A line with no tier prints
    the number alone. Both pieces share one baseline in the band.
    """
    if band.height <= 0 or not text:
        return
    number, _, tier = text.partition(_SEPARATOR)
    placement = layout.page
    left = band.center_x - room / 2 if placement is None else placement.usable_left
    right = band.center_x + room / 2 if placement is None else placement.usable_right
    size_px = band_type_size(text, band, room, metrics)
    # CON-020's floor: the tier word never sets under it.
    floor_px = INTERIOR_FOOTER_LINE_PT * stream.dpi / 72.0
    baseline = band.center_y + _middle_em(metrics) * size_px
    stream.text(
        number, left, baseline, stream.to_points(size_px), grey=grey,
        embolden_pt=stream.to_points(size_px) * _BOLD_RATIO,
    )
    if not tier:
        return
    word = tier.upper()
    tier_px = max(floor_px, size_px * _TIER_RATIO)
    word_left = right - metrics.advance(word) * tier_px
    stream.text(word, word_left, baseline, stream.to_points(tier_px), grey=grey)
    # The dots end one dot short of the word.
    draw_tier_dots(
        stream, tier, word_left - tier_px * 0.55 * 0.75,
        baseline - _cap_height_em(metrics) * tier_px / 2, tier_px, grey=grey,
    )


def draw_tier_dots(
    stream: ContentStream,
    tier: object,
    row_right: float,
    middle: float,
    type_px: float,
    *,
    grey: float = INK_GREY,
) -> None:
    """A tier's dots (one filled per rank, of three), ending at ``row_right``.

    CARD-228's glyph through the one round-mark site, sized to sit beside text
    set at ``type_px``, centred on ``middle``. Nothing for a tier the book's
    ladder does not hold.
    """
    record = tier_of_record(tier)
    if record is None or record not in TIERS:
        return
    diameter = type_px * 0.55
    box_h = diameter / DIFFICULTY_DOT_RATIO
    box_w = diameter * (1 + DIFFICULTY_DOT_GAP_RATIO) * len(TIERS)
    dots = difficulty_dots(
        round(row_right - box_w), round(middle - box_h / 2), round(row_right), round(middle + box_h / 2),
        filled=TIERS.index(record) + 1, total=len(TIERS),
    )
    if dots is not None:
        draw_difficulty_dots(stream, dots, grey=grey)


def _cap_height_em(metrics: FontMetrics) -> float:
    return metrics.cap_height / metrics.units_per_em


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
    shade_clue_cells(stream, layout)
    draw_ruled_grid(stream, layout, grey=grey)
    if layout.frame is not None:
        draw_frame(stream, layout.frame, grey=grey)
    draw_clue_digits(stream, layout, measured, grey=grey)
    draw_puzzle_header(stream, layout, band, text, room, measured, grey=grey)


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
    for index, (layout, band, text) in enumerate(slots):
        if index and band.height > 0 and layout.page is not None:
            # A lower slot's header gets the rule the page's header rule gives
            # the first, at the same weight (the approved mockup's two-up).
            rule_y = band.center_y + band.height * 0.35
            stream.stroke_grey(grey)
            stream.stroke_width(stream.to_points(interior_header_rule_px()))
            stream.line(layout.page.usable_left, rule_y, layout.page.usable_right, rule_y)
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
