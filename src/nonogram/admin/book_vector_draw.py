"""Drawing a COMP-007 ``Layout`` with ADR-0042's operator vocabulary.

CARD-295. **This module knows no page kind.** It is handed a
:class:`~nonogram.export.layout.Layout` — or the pieces of one: its ruled
lines, its frame, its clue entries — and records the operators that draw them
onto a :class:`~nonogram.admin.book_vector.ContentStream`. It cannot tell a
puzzle page from the guide's worked example from an answer tile, and that is
the point: ADR-0042's phase has three page cards and a fourth that mixes the
media, and a grid drawn in each of them is four grids to keep in step.

Why it is not part of :mod:`nonogram.admin.book_vector`
------------------------------------------------------

That module is the *vocabulary* — "nothing in this file knows what a puzzle
is", and nothing in it knows what a ``Layout`` is either: every coordinate it
takes is an argument. This module is the one place that reads COMP-007's
geometry and turns it into that vocabulary's calls. Keeping the two apart is
what lets ``book_vector``'s own tests stay a vocabulary's tests.

Why it is not part of the puzzle page's module
----------------------------------------------

CARD-296's AC-4 and CARD-297's own scope both say the guide's worked example
and the answer tiles must **reuse** the puzzle page's grid rather than grow a
second copy. A routine that lives in a module named for the puzzle page is a
routine the next card has to reach past its name to use, and the cheapest
thing to do with a name like that is to write a fresh one. So the routines
live here, named for what they draw, and the puzzle page is one consumer of
them (:mod:`nonogram.admin.book_puzzle_vector`).

What it derives, and what it refuses to
---------------------------------------

**No geometry** (ADR-0042/R3, restating ADR-0036/R2). Every position, every
extent and every stroke width below is read off the ``Layout``. Two kinds of
arithmetic happen here and neither is a position:

* **units** — a ``Layout`` is device pixels and a stroke is points, so a
  width goes through :meth:`~nonogram.admin.book_vector.ContentStream.to_points`.
  The conversion is the stream's own and the DPI is the ``Layout``'s.
* **type** — where a *string* sits for a given centre is the sum of its
  glyphs' advances, which only the face knows (see :func:`set_centred`).
  ``book_vector`` assigns that arithmetic to the caller in so many words:
  "Centring a string is the caller's arithmetic over
  ``FontMetrics.advance``, because where a string sits is layout while how
  wide it sets is type."

**Tone is the exception, and it is a finding rather than a licence.**
ADR-0042/R3 says every *tone* comes from the ``Layout`` too, and the
``Layout`` states none: today's interior is :data:`~nonogram.export.png.INK`
on :data:`~nonogram.export.png.BACKGROUND` and nothing else, and ``INK`` is
a renderer constant that COMP-007 never sees. So the tone is taken from that
same constant, converted by :func:`as_grey`, and is an argument everywhere
below — it is **not** a literal in any drawing routine, so the card that
gives tone a home (CARD-227, whose 0.35 grey cell line is the first tone this
project will have had) changes one default and no call site. G-1 forbids this
card from being that card.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from nonogram.admin.book_vector import CLUE_DIGIT_TAG, ContentStream, FontMetrics
from nonogram.export.layout import ClueEntry, GridLine, Layout, PuzzleFrame
from nonogram.export.png import INK

__all__ = [
    "INK_GREY",
    "advance_px",
    "as_grey",
    "ascent_px",
    "descent_px",
    "draw_clue_digits",
    "draw_frame",
    "draw_grid_lines",
    "draw_folio",
    "draw_ruled_grid",
    "line_height_px",
    "page_stream",
    "set_centred",
    "set_from_top",
    "set_right_from_top",
    "set_right_middle",
]


def as_grey(colour: tuple[int, int, int]) -> float:
    """An ``(r, g, b)`` the interior draws with, as a content-stream grey.

    Raises:
        ValueError: ``colour`` is not achromatic. A ``g``/``G`` operand is one
            number, so a coloured ink has no grey to be converted to — and
            silently taking one channel would print a tone nobody chose. The
            interior is ink on paper (ADR-0042 leaves colour to the cover), so
            this is a guard on the conversion rather than a branch the project
            reaches.
    """
    red, green, blue = colour
    if not red == green == blue:
        raise ValueError(
            f"{colour!r} is not achromatic, so it has no single grey level: a "
            "content stream's g/G operand is one number"
        )
    return red / 255.0


#: The interior's one ink, as a grey level. Derived from
#: :data:`nonogram.export.png.INK` — the constant the raster renderers draw
#: every interior mark with — rather than written as ``0.0``, so the two
#: media cannot disagree about what "ink" is without a test noticing.
INK_GREY = as_grey(INK)


def page_stream(layout: Layout) -> ContentStream:
    """An empty stream the size and resolution ``layout`` is measured at.

    The one place a page's extent is taken from a ``Layout``, so no page card
    has to remember which of ``width``/``height``/``dpi`` the ``MediaBox``
    comes from. A placed page's ``width``/``height`` are the trim
    (:class:`~nonogram.export.layout.PagePlacement`), which is what a book
    page's ``MediaBox`` must be.
    """
    return ContentStream(
        width_px=layout.width, height_px=layout.height, dpi=layout.dpi
    )


def draw_grid_lines(
    stream: ContentStream,
    verticals: Sequence[GridLine],
    horizontals: Sequence[GridLine],
    *,
    grey: float = INK_GREY,
) -> None:
    """Stroke ``verticals`` and ``horizontals``, thin rules first.

    Takes the two line sequences rather than a ``Layout`` so that a caller
    holding lines from somewhere else — a pair's slot, a probe layout — needs
    no ``Layout`` to wrap them in. :func:`draw_ruled_grid` is the ``Layout``
    door onto it.

    **Thin rules first, then the every-fifth and border rules**, which is the
    order :func:`nonogram.admin.book_pdf_generator._stroke_drawing` and
    ``png._draw_grid`` both stroke in: where a heavy line crosses a thin one
    the heavy line is drawn last and stays visually continuous. The sort is
    stable and keyed on :attr:`~nonogram.export.layout.GridLine.major` alone,
    so within each half the lines keep COMP-007's own order.

    **The graphics state is set when it changes, not per line.** A 30x30 page
    has 62 lines, so this emits a handful of ``w`` and ``G`` operators rather
    than 62 of each — the stream's state is the PDF's own and persists until it
    is set again (``book_vector.ContentStream``'s own contract). The first line
    always sets both a width and a tone, whatever the stream was handed in:
    nothing here assumes a state it did not set.

    **"A handful" and not "one per weight", because that was measured**
    (CARD-227; the attribution corrected in review cycle 1, F-006). A book
    page has three weights and two tones, and **this function** emits
    **six** ``w`` operators on a 20x20 rather than three: the sort above is
    keyed on :attr:`~nonogram.export.layout.GridLine.major`, which has two
    values, so inside the heavy half the border and the fifth lines interleave
    in COMP-007's own order and the width changes on each — 0.3, then
    1.3 / 0.8 / 1.3 / 0.8 / 1.3. That costs operators and nothing else — both
    heavy tiers are the same pure black, so no crossing looks different
    whichever of the two is on top. Keying the sort on
    :attr:`~nonogram.export.layout.GridLine.tier` would make it three, and
    that is a change to **stroke order** in four renderers rather than to a
    number, which CARD-227's G-2 keeps out of that card.

    The **page**'s count is **seven**: :func:`draw_frame`'s own unconditional
    set is the seventh, re-stating 1.3 pt after the last border line already
    set it. That seven is what ``tests/test_book_grid_rules.py`` records,
    because it reads the finished page — so the number in that assertion is
    the page's, not this function's, and neither is a frozen accident of one
    shape: 22x13 and 30x30 derive to six here and seven there as well, while
    a 5x5 with no fifth lines at all derives to two and three.

    **Where each width and each tone comes from (CARD-227, ADR-0037/R2).**
    A line that carries a *declared* weight
    (:attr:`~nonogram.export.layout.GridLine.width_pt`) is stroked at it, in
    the points it is stated in, and at its own
    :attr:`~nonogram.export.layout.GridLine.grey`. A line that carries none
    keeps what every line did before: its device-pixel width through
    :meth:`~nonogram.admin.book_vector.ContentStream.to_points`, and the
    caller's ``grey``. **No arithmetic is added either way** — a declared
    width is already in the stream's own unit, so this reads a number rather
    than converting one, and ADR-0042/R3's "the writer derives nothing" is
    stricter here than it was before. ``grey`` therefore stays the default for
    a layout that declares no tone, which is every layout but a book's, and
    the three weights reach the stream through the ``w``/``G`` primitives
    CARD-294 already had — no new one (G-2).
    """
    oriented: list[tuple[GridLine, bool]] = [
        *((line, True) for line in verticals),
        *((line, False) for line in horizontals),
    ]
    width: float | None = None
    tone: float | None = None
    for line, vertical in sorted(oriented, key=lambda pair: pair[0].major):
        declared = (
            stream.to_points(line.width) if line.width_pt is None else line.width_pt
        )
        wanted = grey if line.grey is None else line.grey
        if wanted != tone:
            stream.stroke_grey(wanted)
            tone = wanted
        if declared != width:
            stream.stroke_width(declared)
            width = declared
        if vertical:
            stream.line(line.position, line.start, line.position, line.end)
        else:
            stream.line(line.start, line.position, line.end, line.position)


def draw_ruled_grid(
    stream: ContentStream, layout: Layout, *, grey: float = INK_GREY
) -> None:
    """Stroke every ruled line of ``layout``'s grid (FR-041)."""
    draw_grid_lines(
        stream, layout.vertical_lines, layout.horizontal_lines, grey=grey
    )


def draw_frame(
    stream: ContentStream, frame: PuzzleFrame, *, grey: float = INK_GREY
) -> None:
    """Stroke the box a framed drawing is closed off with (CARD-144).

    One ``re``, not four lines, and the difference is the corners: a stroked
    rectangle is one path, so a viewer joins its sides, where four separately
    stroked lines meet at butt caps and leave a notch half a rule wide at each
    corner. The raster renderer strokes four lines because Pillow has no
    stroked-rectangle-with-joins to ask for; PDF does, and it is also one
    operator instead of four.

    The four boundaries and the width are the frame's own — and since
    CARD-227 that width is the grid's **border** weight where the sheet
    declares one (:attr:`~nonogram.export.layout.PuzzleFrame.width_pt`,
    1.3 pt on a book), falling back to
    :attr:`~nonogram.export.layout.PuzzleFrame.width`, the ``Layout``'s heavy
    rule in device pixels, where it does not. Still no new weight
    (ADR-0037/R2, G-1): the frame continues the grid's outer border and is
    stroked at exactly the border's own figure, which is what keeps the two
    from reading as a misprint where they coincide.
    """
    stream.stroke_grey(grey if frame.grey is None else frame.grey)
    stream.stroke_width(
        stream.to_points(frame.width) if frame.width_pt is None else frame.width_pt
    )
    stream.rectangle(frame.left, frame.top, frame.right, frame.bottom)


def set_centred(
    stream: ContentStream,
    text: str,
    center_x: float,
    center_y: float,
    size_px: float,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """Set ``text`` centred on ``(center_x, center_y)`` in both axes.

    The vector spelling of Pillow's ``anchor="mm"``, which is how every
    centred mark on an interior page is placed today — the clue numbers
    (``png._draw_clues``), a band's one piece (``pdf._draw_header``'s
    ``"lm"``, whose vertical half is the same rule) and an answer tile's
    caption. Both halves are the face's own measurements, so neither renderer
    has to know the other's rasteriser:

    * **horizontally**, by the string's own advance — :meth:`FontMetrics.advance`
      is the width a viewer will set it at, not an estimate of it, because the
      embedded face is ``/TrueType`` with ``/WinAnsiEncoding`` and a viewer
      consults neither ``GPOS`` nor ``kern`` for one;
    * **vertically**, on the midpoint between the face's ascender and
      descender, which is what Pillow's ``m`` anchor means. **Deliberately not
      the cap height**: a cap-height centring would put a digit's ink
      elsewhere than the raster page puts it, and ADR-0042 changes the medium,
      not the design.

    ``size_px`` is device pixels, because that is the unit every type size in
    a ``Layout`` is stated in (``clue_font_size``, ``HeaderBand.font_size``);
    the ``Tf`` operand is the point size that is, which is the stream's own
    conversion.
    """
    size_pt = stream.to_points(size_px)
    left = center_x - metrics.advance(text) * size_px / 2.0
    baseline = center_y + _middle_em(metrics) * size_px
    stream.text(text, left, baseline, size_pt, grey=grey)


def _middle_em(metrics: FontMetrics) -> float:
    """How far below the ascender/descender midpoint the baseline sits, in ems.

    ``(ascent + descent) / 2``, with ``descent`` negative as a PDF descriptor
    states it — so for the bundled face this is ``(928 - 236) / 2000``. The
    same quantity Pillow's ``m`` vertical anchor uses, and the reason it is a
    function rather than inlined twice is that it is the one number both
    ``set_centred`` and its control have to agree about.
    """
    return (metrics.ascent + metrics.descent) / 2000.0


# --------------------------------------------------------------------------
# The rest of Pillow's anchors, and the face measurements behind them
# --------------------------------------------------------------------------
#
# CARD-297. :func:`set_centred` above is the vector spelling of Pillow's
# ``"mm"``; the table of contents and the answer caption are set with three
# more of that vocabulary's anchors, and they belong beside it rather than in
# either page's own module — a page kind that has to reach past a sibling
# page's name for an anchor conversion writes its own, which is the argument
# this module's own header makes about the grid.
#
# Every one is the same two-line conversion: Pillow is handed a *box* edge and
# ``ContentStream.text`` is handed a *baseline*, so the horizontal half is the
# string's own advance and the vertical half is either the ascender (the
# ``"a"`` anchors, which measure from the top of the line) or the
# ascender/descender midpoint (the ``"m"`` anchors, :func:`_middle_em`).
# Both halves are the embedded face's own numbers, which is what lets the two
# media put a string in the same place without sharing a rasteriser.


def advance_px(text: str, size_px: float, metrics: FontMetrics) -> float:
    """How wide ``text`` sets at ``size_px``, in device pixels.

    :meth:`~nonogram.admin.book_vector.FontMetrics.advance` is the authority
    rather than an estimate of one: the face is written ``/TrueType`` with
    ``/WinAnsiEncoding``, for which a viewer consults neither ``GPOS`` nor
    ``kern``, so the sum of the ``/Widths`` the writer emits *is* the width
    the reader's viewer will set.
    """
    return metrics.advance(text) * size_px


def ascent_px(size_px: float, metrics: FontMetrics) -> float:
    """The face's ascender at ``size_px``, in device pixels.

    The number that turns a *top of line* into a baseline — the one
    conversion the two media disagree about, because Pillow's default anchor
    puts the ascender at the ``y`` it is given and
    :meth:`~nonogram.admin.book_vector.ContentStream.text` puts the baseline
    there.
    """
    return metrics.ascent / 1000.0 * size_px


def descent_px(size_px: float, metrics: FontMetrics) -> float:
    """The face's descender depth at ``size_px``, in device pixels (positive).

    ``FontDescriptor``'s ``/Descent`` is negative, as a PDF states it; a
    renderer wants a depth, so the sign is flipped here and not at four call
    sites.
    """
    return -metrics.descent / 1000.0 * size_px


def line_height_px(size_px: float, metrics: FontMetrics) -> float:
    """Ascender plus descender at ``size_px`` — one line's vertical extent.

    The vector reading of the raster pages' ``ascent + descent`` out of
    ``PIL.ImageFont.FreeTypeFont.getmetrics``, which is what every one of them
    measures a line's depth with.
    """
    return ascent_px(size_px, metrics) + descent_px(size_px, metrics)


def set_right_middle(
    stream: ContentStream,
    text: str,
    right: float,
    center_y: float,
    size_px: float,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """Set ``text`` ending at ``right``, centred on ``center_y``.

    Pillow's ``anchor="rm"`` — how a solved slot's caption is placed, so that
    the reader's eye runs down the grid's right edge and meets the picture's
    name there (CARD-203). The vertical half is :func:`set_centred`'s own.
    """
    size_pt = stream.to_points(size_px)
    left = right - advance_px(text, size_px, metrics)
    baseline = center_y + _middle_em(metrics) * size_px
    stream.text(text, left, baseline, size_pt, grey=grey)


def set_from_top(
    stream: ContentStream,
    text: str,
    left: float,
    top: float,
    size_px: float,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """Set ``text`` with its left edge at ``left`` and its ascender at ``top``.

    Pillow's **default** anchor, ``"la"`` — the one every line of the table of
    contents and of the guide's prose is drawn at, because a page that sets
    one line under another advances a pen down the page rather than naming a
    centre for each line.
    """
    # The point size is bound before the call, not computed inside it. Both
    # ``set_centred`` above and this do it, and it is load-bearing rather than
    # stylistic: ``tests/test_book_difficulty_dots.py``'s round-mark walk
    # excuses a ``ContentStream`` call only while no positional argument is a
    # *call result* (``_hides_a_sequence_argument`` — a result could be a
    # vertex list, which is where a disc hides), so a ``Tf`` operand computed
    # in the argument list takes this module out of that excuse and reds that
    # file's equality.
    size_pt = stream.to_points(size_px)
    stream.text(text, left, top + ascent_px(size_px, metrics), size_pt, grey=grey)


def set_right_from_top(
    stream: ContentStream,
    text: str,
    right: float,
    top: float,
    size_px: float,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """Set ``text`` ending at ``right``, with its ascender at ``top``.

    Pillow's ``anchor="ra"`` — a table-of-contents row's page number, right
    aligned on the measure's far edge while sharing the label's own line.
    """
    set_from_top(
        stream,
        text,
        right - advance_px(text, size_px, metrics),
        top,
        size_px,
        metrics,
        grey=grey,
    )


def draw_folio(
    stream: ContentStream,
    left: float,
    top: float,
    right: float,
    bottom: float,
    text: str,
    size_px: float,
    metrics: FontMetrics,
    *,
    right_hand: bool,
    content_bottom: float | None = None,
    content_right: float | None = None,
    content_left: float | None = None,
    grey: float = INK_GREY,
) -> bool:
    """``text`` at the bottom-outer corner of a usable area, or nothing (FR-043).

    :func:`~nonogram.admin.book_pdf_generator._draw_folio`'s corner path in
    operators, **omit-rather-than-collide rule included**: the four edges are
    one page's usable area in device pixels, ``content_bottom`` the lowest
    pixel the page's own content already reaches, and
    ``content_right``/``content_left`` its rightmost/leftmost — read only when
    the vertical check already shows no room, exactly as the raster function
    reads them, so a caller with no horizontal figure keeps the more
    conservative rule.

    Returns whether the folio was drawn, because "this page prints no page
    number" is a fact a caller may have to pass on (the raster function's
    callers learn it from the pixels; a stream's caller would have to parse
    its own output back).

    ``right_hand`` is the caller's, not derived here:
    :func:`~nonogram.admin.book_pdf_generator.page_is_right_hand` is the one
    reader of a page number's parity and it lives where the page numbers do
    (this module imports no page kind — see its header).

    **The baseline is ``bottom``, measured rather than reasoned.** Pillow's
    ``"rb"``/``"lb"`` anchor puts the *glyph box's* bottom at the ``y`` it is
    given, and a plain decimal number has no descender, so for this one string
    the anchor is the baseline: measured at ``FOLIO_PT`` on this face at
    1200 DPI, ``anchor="ls"`` (an explicit baseline) and ``anchor="lb"`` put
    the same digits' ink within 2 px of each other, against the 40 px the
    descender would have moved them. The ``"b"`` anchor is **not** the
    descender line for this text, which is what the equivalent conversion in
    :mod:`nonogram.admin.book_guide_vector` already assumes for the guide's
    own folio.
    """
    if content_bottom is not None and bottom - content_bottom < line_height_px(
        size_px, metrics
    ):
        width = advance_px(text, size_px, metrics)
        if right_hand:
            clear = content_right is not None and content_right <= right - width
        else:
            clear = content_left is not None and content_left >= left + width
        if not clear:
            return False
    x = right - advance_px(text, size_px, metrics) if right_hand else left
    # Bound before the call for the reason :func:`set_from_top` states.
    size_pt = stream.to_points(size_px)
    stream.text(text, x, bottom, size_pt, grey=grey)
    return True


def draw_clue_digits(
    stream: ContentStream,
    layout: Layout,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """Set every clue number of ``layout``, each centred where it was placed.

    :attr:`~nonogram.export.layout.ClueEntry.value` is printed exactly as
    ``nonogram.clues`` encoded it, the ``0`` of an empty line included
    (AC-013) — this draws the clue set it is handed and judges none of it.

    Every entry is set at :attr:`~nonogram.export.layout.Layout.clue_font_size`,
    which COMP-007 derived from the shared cell. CON-020's 10 pt floor
    excepts clue digits for exactly that reason: their size follows the cell,
    not the reader.

    **And since CARD-314 the digits say so in the stream.** They are set inside
    a :data:`~nonogram.admin.book_vector.CLUE_DIGIT_TAG` marked-content
    sequence, which is how the exemption above survives the medium change: it
    is keyed on *this function*, and a content stream otherwise records no
    caller, so a stream-read floor could tell an exempt 8.64 pt digit from
    8.64 pt of body type only by its size — and exempting by size is exempting
    any body face that happens to measure it. That constant's own comment holds
    the reasoning; what matters here is that **this is the one place in the
    package that emits the tag**, because the mark is a claim and a claim with
    two authors is a claim nobody checks. ``tests/test_book_interior_type_floor.py``
    holds ``src/`` to that by walking it with :mod:`ast`.

    The pair brackets the whole clue set rather than each digit — one ``BMC``
    and one ``EMC`` per call rather than one of each **per clue entry**, which
    on a 30×30 page is **at most 900** of them (2 × 30 lines × ⌈30/2⌉ runs per
    line, the bound and not an observation; the random 30×30s this project's
    own corpora build measure 449–468, and the baseline puzzle page the tests
    render sets 204) — and is
    closed on every path, including the one where ``layout`` places no clue
    entries at all: an open sequence is refused by
    :func:`~nonogram.admin.book_vector.write_vector_page`, so a mark left open
    here would be a page nobody could write rather than a page read wrong.
    """
    stream.begin_marked(CLUE_DIGIT_TAG)
    try:
        _set_entries(
            stream, layout.clue_entries, layout.clue_font_size, metrics, grey
        )
    finally:
        stream.end_marked()


def _set_entries(
    stream: ContentStream,
    entries: Iterable[ClueEntry],
    size_px: float,
    metrics: FontMetrics,
    grey: float,
) -> None:
    for entry in entries:
        set_centred(
            stream,
            str(entry.value),
            entry.center_x,
            entry.center_y,
            size_px,
            metrics,
            grey=grey,
        )
