"""The table of contents as PDF operators — CARD-297, ADR-0042/R1.

:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.create_toc_page` in
the other medium: the title, one line per row, each row's page number right
aligned on the measure's far edge with leader dots between, and the page's own
folio. Nothing is redesigned (G-1) — every expression below is that method's,
read from the same page plan, in the same order, with the same two fitting
steps and the same clip.

Where this module sits, and why it is not a generator method
-------------------------------------------------------------

**Downstream of** :mod:`nonogram.admin.book_pdf_generator`, exactly as
:mod:`nonogram.admin.book_guide_vector` is: it imports that module's
constants, its sheet reader and its page-parity rule rather than restating
any of them, and that module imports nothing back. The page is therefore a
module-level function taking the sheet, not a method on the generator — which
is :func:`~nonogram.admin.book_guide_vector.guide_pages`' own shape, down to
``spec_for`` arriving as a callable "so this module never holds a generator
and never reads a book".

That shape is load-bearing rather than tidy, and the reason is measured:
``tests/test_book_export_interior_cover.py``'s door-axis walk enumerates
**every** ``page_spec``/``book_page_spec`` call in ``src/`` and holds the
count on the generator (17) and the set of callers outside it (6) as
equalities — the mechanism that keeps a page *position* from being computed
in a second place. A method here would have added a fourth place that
computes one; taking the sheet (or the callable that answers for it) adds
none, which is the property that walk exists to protect. Three cards are in
flight on that file (CARD-276, CARD-287, CARD-292), so its figures are not
this card's to re-measure (G-5).

What a *row* is
---------------

:class:`~nonogram.admin.book_pdf_generator.TocEntry` — the value
``create_toc_page`` is handed, with its ``label``, its ``page`` and its
``starts_group``.

The one measurement that is not identical across the two media
--------------------------------------------------------------

**The leader dots' count.** Both media fill the gap between a label and its
number by measuring a repeated ``.`` and correcting the estimate in both
directions; the raster page measures with ``FreeTypeFont.getlength`` and this
one with the embedded face's own ``/Widths`` (:func:`advance_px`). The two
agree to within a fraction of a dot's advance, so a row's run can differ by at
most one dot between the media. It is a *type* measurement, which
:mod:`nonogram.admin.book_vector_draw`'s header already names as the one
arithmetic a writer does ("where a string sits is layout while how wide it
sets is type"), and it moves no row, no number and no folio — the three things
a reader uses the page for, and the three AC-4 compares against the plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, List, Sequence

from nonogram.admin.book_pdf_generator import (
    FOLIO_PT,
    GUIDE_TITLE_GAP_PT,
    GUIDE_TITLE_PT,
    TOC_ENTRY_GAP_PT,
    TOC_ENTRY_PT,
    TOC_GROUP_GAP_PT,
    TOC_TITLE,
    PageFrame,
    TocEntry,
    _toc_entries_per_page,
    page_frame,
    page_is_right_hand,
    type_px,
)
from nonogram.admin.book_vector import ContentStream, FontMetrics, interior_face_metrics
from nonogram.admin.book_vector_draw import (
    INK_GREY,
    advance_px,
    draw_folio,
    line_height_px,
    set_from_top,
    set_right_from_top,
)

__all__ = [
    "TocTypeSpec",
    "clipped_to",
    "leader_dots",
    "toc_page_stream",
    "toc_pages",
    "toc_type",
]


@dataclass(frozen=True)
class TocTypeSpec:
    """Every type figure one table-of-contents page is set from, in pixels.

    :func:`toc_type` is the only constructor, and it reads
    ``create_toc_page``'s own constants through
    :func:`~nonogram.admin.book_pdf_generator.type_px`. It is a value rather
    than seven arguments because it is one page's type, read in one order, and
    because the one thing a reader of :func:`toc_page_stream` should be able to
    check at a glance is that it derives none of it.

    Attributes:
        title_text: The page's own title line, repeated on every TOC page.
        title_size_px: The size the title is set at.
        title_gap_px: The white between the title's line and the first row.
        entry_size_px: The size a row is set at.
        entry_gap_px: One gap constant, read on both axes exactly as the
            raster page reads it — under a row, and beside a row's leader
            dots at each end.
        group_gap_px: The extra white above a row that opens a group.
        folio_size_px: The size the page number at the foot is set at.
    """

    title_text: str
    title_size_px: int
    title_gap_px: int
    entry_size_px: int
    entry_gap_px: int
    group_gap_px: int
    folio_size_px: int


def toc_type(dpi: int) -> TocTypeSpec:
    """``create_toc_page``'s own type figures at ``dpi``, in device pixels."""
    return TocTypeSpec(
        title_text=TOC_TITLE,
        title_size_px=type_px(GUIDE_TITLE_PT, dpi),
        title_gap_px=type_px(GUIDE_TITLE_GAP_PT, dpi),
        entry_size_px=type_px(TOC_ENTRY_PT, dpi),
        entry_gap_px=type_px(TOC_ENTRY_GAP_PT, dpi),
        group_gap_px=type_px(TOC_GROUP_GAP_PT, dpi),
        folio_size_px=type_px(FOLIO_PT, dpi),
    )


def clipped_to(text: str, size_px: float, metrics: FontMetrics, measure: float) -> str:
    """``text`` shortened with a trailing ellipsis until it fits ``measure``.

    :func:`~nonogram.admin.book_pdf_generator._clipped_to`'s loop over the
    embedded face's own advances — two characters off, one ellipsis on,
    stopping at a single character so no label is clipped away entirely.
    Reimplemented rather than called because that function measures with a
    ``FreeTypeFont``, which is the raster medium's reader and the one thing a
    vector writer must not need.

    It cannot fire for any row the structural list builds on any trim CON-018
    stocks (the longest is the guide's own title, about a fifth of the usable
    width); it is here because the raster page has it, and a future section's
    name is not this card's to bound.
    """
    clipped = text
    while len(clipped) > 1 and advance_px(clipped, size_px, metrics) > measure:
        clipped = clipped[:-2] + "…"
    return clipped


def leader_dots(run: float, size_px: float, metrics: FontMetrics) -> str:
    """The dots that fill ``run`` pixels, measured rather than divided.

    The raster page's own three steps, and the middle one is not the verdict:
    the division is a **first estimate, corrected both ways** — trimmed while
    the string overruns the gap, grown while another dot would still fit.
    Correcting only downwards would silently drop a dot on any face whose
    ``..`` pair measures narrower than two advances.

    A run too short for even one dot gets none, which is the row CARD-205's
    AC-6 keeps dotless.
    """
    dot = advance_px(".", size_px, metrics)
    if dot <= 0:  # pragma: no cover - a face with a zero-advance full stop
        return ""
    dots = "." * max(0, int(run // dot))
    while dots and advance_px(dots, size_px, metrics) > run:
        dots = dots[:-1]
    while advance_px(dots + ".", size_px, metrics) <= run:
        dots += "."
    return dots


def toc_page_stream(
    rows: Sequence[TocEntry],
    frame: PageFrame,
    dpi: int,
    page_number: int,
    *,
    type_spec: TocTypeSpec | None = None,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> ContentStream:
    """One page of the table of contents, as the stream its ``/Contents`` holds.

    ``rows`` is **this page's own slice**, already split by the interior's
    planning pass, so this draws whatever it is handed and never re-decides
    how many rows share a page — one source of truth for the split, not two
    (``create_toc_page``'s own rule). ``frame`` is that page's sheet, from
    :func:`~nonogram.admin.book_pdf_generator.page_frame`, which is where the
    raster page reads its own trim and usable area.

    A row with no page number prints its label alone, with no number and no
    leaders — there is nothing on the right for them to lead to. A row that
    opens a group is set a group's gap below what precedes it, suppressed for
    the page's **first** row, where there is no group above to separate from
    and the gap would only spend room the folio's own reserved line is
    counting on.
    """
    face = interior_face_metrics() if metrics is None else metrics
    spec = toc_type(dpi) if type_spec is None else type_spec
    stream = ContentStream(width_px=frame.width, height_px=frame.height, dpi=dpi)
    measure = frame.right - frame.left

    set_from_top(
        stream, spec.title_text, frame.left, frame.top, spec.title_size_px, face, grey=grey
    )
    y = frame.top + line_height_px(spec.title_size_px, face) + spec.title_gap_px

    size_px = spec.entry_size_px
    gap = spec.entry_gap_px
    row_height = line_height_px(size_px, face)
    line_height = row_height + gap

    bottom = y
    for index, row in enumerate(rows):
        if row.starts_group and index > 0:
            y += spec.group_gap_px
        if row.page is None:
            clipped = clipped_to(row.label, size_px, face, measure)
            set_from_top(stream, clipped, frame.left, y, size_px, face, grey=grey)
        else:
            number_text = str(row.page)
            number_width = advance_px(number_text, size_px, face)
            clipped = clipped_to(
                row.label, size_px, face, measure - number_width - 2 * gap
            )
            set_from_top(stream, clipped, frame.left, y, size_px, face, grey=grey)
            set_right_from_top(
                stream, number_text, frame.right, y, size_px, face, grey=grey
            )
            # Measured off what was actually drawn — the *clipped* label —
            # rather than off the label as it arrived: an ellipsised label is
            # narrower, and leaders starting where the full label would have
            # ended would leave a hole in the row.
            dot_left = frame.left + advance_px(clipped, size_px, face) + gap
            dot_right = frame.right - number_width - gap
            dots = leader_dots(dot_right - dot_left, size_px, face)
            if dots:
                set_from_top(stream, dots, dot_left, y, size_px, face, grey=grey)
        bottom = y + row_height
        y += line_height

    draw_folio(
        stream,
        frame.left,
        frame.top,
        frame.right,
        frame.bottom,
        str(page_number),
        spec.folio_size_px,
        face,
        right_hand=page_is_right_hand(page_number),
        content_bottom=bottom,
        grey=grey,
    )
    return stream


def toc_pages(
    rows: Sequence[TocEntry],
    spec_for: Any,
    dpi: int,
    first_page: int,
    *,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> Iterator[ContentStream]:
    """Every page of the table of contents ``rows`` take, in print order.

    ``spec_for`` is a callable taking an interior page number and returning
    that page's :class:`~nonogram.export.layout.PageSpec` — the shape
    :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.page_spec`
    already has, passed as a callable for the reason
    :func:`~nonogram.admin.book_guide_vector.guide_pages` takes one.

    The split across pages is **production's own**:
    :func:`~nonogram.admin.book_pdf_generator._toc_entries_per_page`, measured
    on the same page-1 frame ``interior_stream`` measures it on, so the plan
    and the draw can never disagree about how a long list breaks (G-1).

    One page at a time, by ``yield``, for the reason
    :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.vector_puzzle_pages`
    yields: a content stream is small, but holding a list of them is the shape
    CARD-145 removed.
    """
    face = interior_face_metrics() if metrics is None else metrics
    spec = toc_type(dpi)
    per_page = _toc_entries_per_page(page_frame(spec_for(1)), dpi)
    slices: List[Sequence[TocEntry]] = [
        rows[start : start + per_page] for start in range(0, len(rows), per_page)
    ]
    for index, slice_ in enumerate(slices):
        page_number = first_page + index
        yield toc_page_stream(
            slice_,
            page_frame(spec_for(page_number)),
            dpi,
            page_number,
            type_spec=spec,
            metrics=face,
            grey=grey,
        )
