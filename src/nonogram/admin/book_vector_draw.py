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

from nonogram.admin.book_vector import ContentStream, FontMetrics
from nonogram.export.layout import ClueEntry, GridLine, Layout, PuzzleFrame
from nonogram.export.png import INK

__all__ = [
    "INK_GREY",
    "as_grey",
    "draw_clue_digits",
    "draw_frame",
    "draw_grid_lines",
    "draw_ruled_grid",
    "page_stream",
    "set_centred",
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
    has 62 lines and two distinct widths, so this emits two ``w`` operators
    instead of 62 — the stream's state is the PDF's own and persists until it
    is set again (``book_vector.ContentStream``'s own contract). The first
    line always sets a width, whatever the stream was handed in: nothing here
    assumes a state it did not set.
    """
    stream.stroke_grey(grey)
    oriented: list[tuple[GridLine, bool]] = [
        *((line, True) for line in verticals),
        *((line, False) for line in horizontals),
    ]
    width: int | None = None
    for line, vertical in sorted(oriented, key=lambda pair: pair[0].major):
        if line.width != width:
            stream.stroke_width(stream.to_points(line.width))
            width = line.width
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

    The four boundaries and the width are the frame's own
    (:attr:`~nonogram.export.layout.PuzzleFrame.width`, which is the
    ``Layout``'s heavy rule — no new weight, ADR-0037/R2 and G-1).
    """
    stream.stroke_grey(grey)
    stream.stroke_width(stream.to_points(frame.width))
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
    """
    _set_entries(stream, layout.clue_entries, layout.clue_font_size, metrics, grey)


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
