"""The puzzle page drawn as PDF operators — CARD-295, ADR-0042/R1.

Every claim *about the vector page* is made against **the content stream of a
written PDF** (ADR-0042/R6) or against **poppler**, an engine that did not
write it: no claim about it is made by counting dark pixels. A **raster** page
is read in two places, and neither of them is a reading of the vector page:

* AC-1's **positive control** — the raster twin of the same page really does
  carry an image XObject, which is what makes AC-1's reading capable of
  failing;
* the **cross-medium seam** (:class:`TestPuzzlePage_AgreesWithTheRasterTwin`)
  — the one place the two media are read *against each other*, the raster
  side off its own ink. That class's own docstring says why a seam that read
  only the stream was not one.

Both take the same bitmap from the ``twin`` fixture, so the whole module
allocates **one** page raster; its other 35 tests allocate none, which is the
point of the card.

The two readings, and what each is for
--------------------------------------

* **The stream, against an independent recomputation** (AC-2, the EC). The
  oracle in :class:`Expected` walks a ``Layout`` in :class:`~decimal.Decimal`
  and produces the marks that ``Layout`` demands; the parser in
  :func:`marks_of` reads the marks the writer actually emitted out of the
  file. Neither calls the other's arithmetic, and neither calls
  ``book_vector._number``. The oracle is independent of the **writer**; it is
  not independent of COMP-007, and it must not be — "every coordinate equals
  the value the ``Layout`` states" is a claim *about* COMP-007's values.
* **Poppler, for type** (AC-3, AC-4). Where a string's glyphs actually land
  is the one thing the stream cannot answer: a ``Td`` operand is a pen
  position, and the ink is the pen plus the face's advances. ``pdftotext
  -bbox`` reports the box poppler laid the glyphs out in, so the clue digits
  and the band are checked where a *reader* finds them. The face's own
  numbers are held against FreeType by CARD-294's
  ``TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader``; this module
  does not re-derive them.

What is deliberately **not** converted here (G-4)
-------------------------------------------------

``tests/test_book_pdf_band.py``, ``tests/test_book_puzzle_frame.py`` and
``tests/test_book_cell_size.py`` keep every one of their pixel-reading sites,
and every node id they declare. The reason is the board's state rather than
the card's text: the puzzle page this card writes is **not yet the page the
book ships**. CARD-298 is the card that makes ``_write_pdf`` choose a medium
per page, and until it lands the raster page is the artefact, so converting
its assertions would drop the control on what ships in exchange for a control
on what does not. The conversion is CARD-298's to trigger and CARD-299's to
finish; what this module adds is the stream-side half, beside the ink-side
half rather than instead of it. ``TestPuzzlePage_AgreesWithTheRasterTwin``
is the seam that makes the two halves comparable while both exist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from random import Random
from typing import Iterator, Sequence

import pytest
from PIL import Image

from nonogram.admin import book_puzzle_vector, book_vector_draw
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    _BAND_WIDTH_RATIO,
    _MIN_BAND_FONT_RATIO,
    _QR_PLACEHOLDER_MODULES,
    FOLIO_PT,
    QR_CAPTION_TEXT,
    SIZE_LABEL_PT,
    BookPDFGenerator,
    PageKind,
    band_identity,
    example_line_layout,
    grid_size_label,
    guide_icon_layout,
    page_is_right_hand,
    print_order,
    qr_group_caption,
    qr_link,
    type_px,
)
from nonogram.admin.book_vector import (
    POINTS_PER_INCH,
    ContentStream,
    FontMetrics,
    interior_face_metrics,
    write_vector_pdf,
)
from nonogram.export import pdf as export_pdf
from nonogram.export.layout import (
    DPI,
    INTERIOR_FOOTER_LINE_PT,
    GridLine,
    HeaderBand,
    InteriorFrame,
    Layout,
    PageRule,
    PageSpec,
    QrCaption,
    QrSlot,
    compute_layout,
    header_band,
    interior_frame,
    qr_caption,
    qr_slot,
)
from nonogram.admin.book_page_spec import GRID_RULES
from nonogram.export.png import INK
from tests.helpers import page_ink, pdf_vector
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, puzzle
from tests.helpers.shared_fixture_controls import page_digest

NO_POPPLER = "poppler (pdftotext) is not installed: AC-3's independent engine is absent"
needs_poppler = pytest.mark.skipif(pdf_vector.PDFTOTEXT is None, reason=NO_POPPLER)

#: How many places :mod:`nonogram.admin.book_vector` writes a number to.
#: Re-derived here as a quantum rather than imported, so the oracle rounds on
#: its own authority.
PLACES = Decimal("0.001")

#: The interior position the first puzzle page falls on in a book with no
#: level dividers. Any page would do for geometry; a stated one keeps the
#: parity of these cases decided rather than incidental.
A_PUZZLE_PAGE = 6


# --------------------------------------------------------------------------
# The independent recomputation (AC-2's oracle)
# --------------------------------------------------------------------------


def _pt(pixels: int | Decimal, dpi: int) -> Decimal:
    """``pixels`` at ``dpi``, in points, rounded as a PDF number is.

    Exact rational arithmetic and one rounding at the end, against the
    writer's float arithmetic and ``f"{value:.3f}"``. The two agree exactly
    and not approximately, and that is checkable rather than lucky: at 300 DPI
    a whole pixel is 0.24 pt exactly, and the finest position this page can
    state — a string's centred left edge, whose denominator is 2000 — lands at
    most five decimals out, never on a half-way case at the fourth. See
    ``test_the_oracle_and_the_writer_round_the_same_way``.
    """
    return (Decimal(pixels) * Decimal(72) / Decimal(dpi)).quantize(
        PLACES, rounding=ROUND_HALF_EVEN
    )


@dataclass(frozen=True)
class Stroke:
    """One stroked path: its operands in points, and the width it was set at."""

    kind: str
    numbers: tuple[Decimal, ...]
    width: Decimal
    grey: Decimal


@dataclass(frozen=True)
class Shown:
    """One text object: what it shows, where its pen was, and at what size."""

    text: str
    x: Decimal
    y: Decimal
    size: Decimal
    grey: Decimal


Mark = Stroke | Shown

#: The :attr:`Stroke.width` a **filled** rectangle is recorded with. A fill
#: has no stroke width — the ``f`` operator does not read one — so recording
#: whatever ``w`` happened to be set last would make the mark's identity
#: depend on a piece of graphics state the viewer never consults for it. A
#: sentinel instead, so the oracle states it too and the comparison is of
#: what the operator actually carries (CARD-306).
FILLED = Decimal(-1)


def _in_stroke_order(layout: Layout) -> list[tuple[GridLine, bool]]:
    """``layout``'s ruled lines as ``(line, is_vertical)``, in stroke order.

    Verticals then horizontals, stably sorted on
    :attr:`~nonogram.export.layout.GridLine.major` alone — thin rules first,
    then the every-fifth and border rules — because *that order is part of the
    claim*: a heavy rule drawn before a thin one is a different page where
    they cross. Stated once here because two things depend on it being the
    same order: :meth:`Expected.grid` and :func:`_state_operators`.
    """
    return sorted(
        [
            *((line, True) for line in layout.vertical_lines),
            *((line, False) for line in layout.horizontal_lines),
        ],
        key=lambda pair: pair[0].major,
    )


@dataclass(frozen=True)
class _QrGroup:
    """One QR group as the test tree states it: a box, an anchor, two strings."""

    icon: QrSlot
    caption: QrCaption
    invitation: str
    link: str


@dataclass(frozen=True)
class _Furniture:
    """One page's sheet furniture, **recomputed in the test tree** (CARD-306).

    The oracle's input, and the point of the class is that nothing in
    ``book_sheet_vector`` and nothing in ``BookPDFGenerator._sheet_furniture``
    builds one: :func:`_furniture_of` composes it from COMP-007's own
    measurements (:func:`~nonogram.export.layout.interior_frame`,
    :func:`~nonogram.export.layout.qr_slot`,
    :func:`~nonogram.export.layout.qr_caption`) and from the generator's
    public strings and type sizes. So "the folio is centred on the trim" and
    "the label is on the gutter side" are claims *about those objects* rather
    than a comparison of the writer with itself — which is what the
    production :class:`~nonogram.admin.book_sheet_vector.SheetFurniture`
    would have made this.
    """

    frame: InteriorFrame
    folio: str
    folio_size_px: int
    size_label: str | None
    label_size_px: int
    caption_size_px: int
    qr_modules: int
    groups: tuple[_QrGroup, ...]
    content_bottom: int | None
    right_hand: bool


def _furniture_of(
    layout: Layout, spec: PageSpec, page_number: int, puzzle_numbers: Sequence[int]
) -> _Furniture:
    """``layout``'s page's furniture, derived from COMP-007 and the strings.

    ``puzzle_numbers`` is the page's puzzles in print order — one on a single
    page, two on a two-up page — and it is what decides the invitation's form
    (:data:`QR_CAPTION_TEXT` for one group, :func:`qr_group_caption`'s named
    form for several), the same distinction ``_draw_qr_caption``'s
    ``name_the_puzzle`` makes.

    The QR groups a **two-up** page carries are not composed here: their
    insets are the pairing walk's (``_two_up_qr_insets``), and recomputing
    those would be re-deriving the pairing verdict rather than reading it.
    This builds the single-page group, which is one icon at inset 0.
    """
    placement = layout.page
    assert placement is not None, "a book page's Layout is placed"
    frame = interior_frame(spec)
    icon, caption = qr_slot(layout), qr_caption(layout)
    groups: tuple[_QrGroup, ...] = ()
    if icon is not None and caption is not None:
        (number,) = puzzle_numbers
        groups = (
            _QrGroup(icon, caption, QR_CAPTION_TEXT, qr_link(number)),
        )
    return _Furniture(
        frame=frame,
        folio=str(page_number),
        folio_size_px=type_px(FOLIO_PT, DPI),
        size_label=grid_size_label(layout.columns, layout.rows),
        label_size_px=type_px(SIZE_LABEL_PT, DPI),
        caption_size_px=type_px(INTERIOR_FOOTER_LINE_PT, DPI),
        qr_modules=_QR_PLACEHOLDER_MODULES,
        groups=groups,
        content_bottom=placement.drawing_bottom,
        right_hand=page_is_right_hand(page_number),
    )


class Expected:
    """What a ``Layout`` demands be drawn, derived from the ``Layout`` alone.

    A second implementation of the page, in the sense CLAUDE.md's test style
    asks for: it reads COMP-007's numbers and states what a conforming writer
    must emit, without calling anything the writer calls. It walks the lines
    in the order the raster renderer strokes them (thin, then major) because
    *that order is part of the claim* — a heavy rule drawn before a thin one
    is a different page where they cross.
    """

    def __init__(self, layout: Layout, grey: Decimal, metrics: FontMetrics) -> None:
        self.layout = layout
        self.grey = grey
        self.metrics = metrics

    def _y(self, pixels: int | Decimal) -> Decimal:
        return _pt(Decimal(self.layout.height) - Decimal(pixels), self.layout.dpi)

    def _x(self, pixels: int | Decimal) -> Decimal:
        return _pt(pixels, self.layout.dpi)

    def grid(self) -> list[Mark]:
        marks: list[Mark] = []
        for line, vertical in _in_stroke_order(self.layout):
            if vertical:
                numbers = (
                    self._x(line.position),
                    self._y(line.start),
                    self._x(line.position),
                    self._y(line.end),
                )
            else:
                numbers = (
                    self._x(line.start),
                    self._y(line.position),
                    self._x(line.end),
                    self._y(line.position),
                )
            marks.append(
                Stroke("line", numbers, self._declared(line), self._tone(line))
            )
        return marks

    def _declared(self, line: GridLine) -> Decimal:
        """The width a conforming writer sets ``line`` at, in points.

        Two arms, and the oracle has to state both because the ``Layout``
        does: a sheet that declares ADR-0037/R2's physical weights
        (:attr:`~nonogram.export.layout.GridLine.width_pt`) demands **that**
        number, in the points it is stated in and through no conversion at
        all, and a sheet that declares none demands its device width
        converted, which is every sheet but the book's. ``Decimal(str(...))``
        rather than ``Decimal(float)`` so the figure the artifact states is
        the figure compared, not its binary neighbour.
        """
        if line.width_pt is None:
            return self._x(line.width)
        return Decimal(str(line.width_pt))

    def _tone(self, line: GridLine) -> Decimal:
        """The tone a conforming writer sets ``line`` at.

        The line's own where it has one — the cell lines' 0.35 grey, the first
        tone this project has had (CARD-227) — and the caller's default
        otherwise, which is the one ink every interior mark was drawn in
        before.
        """
        return self.grey if line.grey is None else Decimal(str(line.grey))

    def frame(self) -> list[Mark]:
        frame = self.layout.frame
        if frame is None:
            return []
        return [
            Stroke(
                "box",
                (
                    self._x(frame.left),
                    self._y(frame.bottom),
                    self._x(frame.right - frame.left),
                    self._x(frame.bottom - frame.top),
                ),
                self._x(frame.width)
                if frame.width_pt is None
                else Decimal(str(frame.width_pt)),
                self.grey if frame.grey is None else Decimal(str(frame.grey)),
            )
        ]

    def shown(self, text: str, center_x: int, center_y: int, size_px: int) -> Shown:
        """Where a string centred on ``(center_x, center_y)`` sets its pen.

        The advance is the face's own, summed from ``widths_1000`` in exact
        decimal — the same *numbers* the writer uses (they are the face's, and
        CARD-294 holds them against FreeType) through different arithmetic.
        The vertical rule is Pillow's ``m`` anchor, stated here from the
        descriptor's ascent and descent rather than read out of
        ``book_vector_draw``.
        """
        em = Decimal(size_px)
        advance = (
            sum(Decimal(self.metrics.widths_1000[byte]) for byte in text.encode("cp1252"))
            / 1000
        )
        middle = Decimal(self.metrics.ascent + self.metrics.descent) / 2000
        return Shown(
            text,
            self._x(Decimal(center_x) - advance * em / 2),
            self._y(Decimal(center_y) + middle * em),
            self._x(size_px),
            self.grey,
        )

    def clues(self) -> list[Mark]:
        return [
            self.shown(
                str(entry.value),
                entry.center_x,
                entry.center_y,
                self.layout.clue_font_size,
            )
            for entry in self.layout.clue_entries
        ]

    def band(self, band: HeaderBand, text: str, room: int) -> list[Mark]:
        if band.height <= 0 or not text:
            return []
        size = band.font_size
        advance = (
            sum(Decimal(self.metrics.widths_1000[byte]) for byte in text.encode("cp1252"))
            / 1000
        )
        if advance * size > Decimal(room) * Decimal(str(_BAND_WIDTH_RATIO)):
            usable = Decimal(room) * Decimal(str(_BAND_WIDTH_RATIO))
            size = max(
                round(band.font_size * _MIN_BAND_FONT_RATIO),
                int(Decimal(size) * usable / (advance * size)),
            )
        return [self.shown(text, band.center_x, band.center_y, size)]

    def page(self, band: HeaderBand, text: str, room: int) -> list[Mark]:
        return self.grid() + self.frame() + self.clues() + self.band(band, text, room)

    # -- CARD-306: the sheet's furniture ------------------------------------

    def _advance(self, text: str, size_px: int | Decimal) -> Decimal:
        return (
            sum(Decimal(self.metrics.widths_1000[byte]) for byte in text.encode("cp1252"))
            / 1000
            * Decimal(size_px)
        )

    def _set(
        self, text: str, x: int, baseline: int, size_px: int, align: str
    ) -> Shown:
        """Where a footer mark anchored at ``x`` by ``align`` sets its pen.

        The row **is** the baseline, which is the one convention every vector
        footer mark in this package uses; the horizontal half is the face's
        own advance, summed in exact decimal from ``widths_1000`` rather than
        borrowed from ``advance_px``.
        """
        advance = self._advance(text, size_px)
        if align == "right":
            pen = Decimal(x) - advance
        elif align == "centre":
            pen = Decimal(x) - advance / 2
        else:
            pen = Decimal(x)
        return Shown(text, self._x(pen), self._y(baseline), self._x(size_px), self.grey)

    def _rule(self, rule: PageRule) -> Stroke:
        return Stroke(
            "line",
            (self._x(rule.left), self._y(rule.y), self._x(rule.right), self._y(rule.y)),
            self._x(rule.width),
            self.grey,
        )

    def furniture(self, sheet: _Furniture) -> list[Mark]:
        """What a conforming writer must emit for ``sheet``'s furniture.

        A second implementation of ``book_sheet_vector.draw_sheet_furniture``
        in the sense CLAUDE.md's test style asks for: it reads COMP-007's
        :class:`~nonogram.export.layout.InteriorFrame`,
        :class:`~nonogram.export.layout.QrSlot` and
        :class:`~nonogram.export.layout.QrCaption` and states the marks they
        demand, calling nothing in ``book_sheet_vector`` — not
        ``qr_module_boxes``, not ``footer_is_clear``, not ``_set_at_baseline``.
        Independent of the **writer**, not of COMP-007, for the reason this
        class's own docstring gives.
        """
        frame = sheet.frame
        marks: list[Mark] = [self._rule(frame.header_rule)]
        if sheet.content_bottom is not None and sheet.content_bottom > frame.footer_rule.y:
            # The corner fallback: ``draw_folio``'s own two checks, restated.
            ascent = Decimal(self.metrics.ascent) * Decimal(sheet.folio_size_px) / 1000
            descent = -Decimal(self.metrics.descent) * Decimal(sheet.folio_size_px) / 1000
            if Decimal(frame.page_bottom - sheet.content_bottom) >= ascent + descent:
                marks.append(
                    self._set(
                        sheet.folio,
                        frame.header_rule.right if sheet.right_hand else frame.header_rule.left,
                        frame.page_bottom,
                        sheet.folio_size_px,
                        "right" if sheet.right_hand else "left",
                    )
                )
            return marks
        marks.append(self._rule(frame.footer_rule))
        if sheet.size_label is not None:
            marks.append(
                self._set(
                    sheet.size_label,
                    frame.label_x,
                    frame.baseline,
                    sheet.label_size_px,
                    "right" if frame.label_right_aligned else "left",
                )
            )
        marks.append(
            self._set(
                sheet.folio, frame.folio_x, frame.baseline, sheet.folio_size_px, "centre"
            )
        )
        border = self._x(frame.footer_rule.width)
        for group in sheet.groups:
            icon = group.icon
            marks.append(
                Stroke(
                    "box",
                    (
                        self._x(icon.left),
                        self._y(icon.bottom),
                        self._x(icon.right - icon.left),
                        self._x(icon.bottom - icon.top),
                    ),
                    border,
                    self.grey,
                )
            )
            side = Decimal(icon.right - icon.left)
            step = side / sheet.qr_modules
            for row in range(sheet.qr_modules):
                for column in range(sheet.qr_modules):
                    if (row + column) % 2 == 0:
                        continue
                    left = icon.left + _half_even(column * step)
                    top = icon.top + _half_even(row * step)
                    right = icon.left + _half_even((column + 1) * step)
                    bottom = icon.top + _half_even((row + 1) * step)
                    marks.append(
                        Stroke(
                            "box_fill",
                            (
                                self._x(left),
                                self._y(bottom),
                                self._x(right - left),
                                self._x(bottom - top),
                            ),
                            FILLED,
                            self.grey,
                        )
                    )
            align = "right" if group.caption.right_aligned else "left"
            marks.append(
                self._set(
                    group.invitation,
                    group.caption.x,
                    group.caption.caption_baseline,
                    sheet.caption_size_px,
                    align,
                )
            )
            marks.append(
                self._set(
                    group.link,
                    group.caption.x,
                    group.caption.link_baseline,
                    sheet.caption_size_px,
                    align,
                )
            )
        return marks


def _half_even(value: Decimal) -> int:
    """``round`` on a :class:`~decimal.Decimal`, the way CPython rounds a float.

    The chequer's boundaries are ``round(column * step)`` in the writer, on a
    binary float; here the same product is exact, so the tie rule has to be
    stated rather than inherited — and CPython's ``round`` is half-to-even,
    which is what ``ROUND_HALF_EVEN`` is.
    """
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def _slot_room(layout: Layout) -> int:
    """The width a band on ``layout`` has to fit inside, in device pixels.

    Read off COMP-007's :class:`~nonogram.export.layout.PagePlacement`
    directly rather than through ``book_puzzle_vector.slot_room``, which is
    the function under test. **This is cycle 1's F-005**: the oracle used to
    call ``slot_room``, so making it return a page's usable *height* where its
    *width* is wanted left all 35 tests green — the one quantity on the page
    that confirmed itself. The arithmetic is two fields of one dataclass, so
    stating it here is cheaper than borrowing it, and
    ``test_the_band_fits_the_way_the_raster_page_fits_it`` now holds
    ``slot_room``'s own answer against the same two fields so the module under
    test is measured rather than trusted.
    """
    placement = layout.page
    assert placement is not None, "a book page's Layout is placed on a page"
    return placement.usable_right - placement.usable_left


# --------------------------------------------------------------------------
# Reading the marks back out of the written file
# --------------------------------------------------------------------------

_N = pdf_vector.NUMBER
_PATTERNS = {
    "grey": re.compile(rf"^({_N}) G$"),
    "width": re.compile(rf"^({_N}) w$"),
    "line": re.compile(rf"^({_N}) ({_N}) m ({_N}) ({_N}) l S$"),
    "box": re.compile(rf"^({_N}) ({_N}) ({_N}) ({_N}) re S$"),
    "fill": re.compile(rf"^({_N}) g$"),
    "box_fill": re.compile(rf"^({_N}) ({_N}) ({_N}) ({_N}) re f$"),
    "text": re.compile(
        rf"^({_N}) g BT /(\w+) ({_N}) Tf ({_N}) ({_N}) Td \((.*)\) Tj ET$"
    ),
}


def marks_of(stream_text: str) -> list[Mark]:
    """Every mark ``stream_text`` draws, with the state each was drawn in.

    **Default-DENY** (ADR-0039/R2): a line this parser cannot classify is an
    ``AssertionError`` naming it, never a mark quietly skipped. That is what
    makes "the page emits nothing else" a claim rather than a filter — an
    image XObject's ``Do``, a Bézier's ``c``, a clipping path's ``W`` would
    each stop the suite here.

    A **fill** tone and a **filled rectangle** were two of those until
    CARD-306, and the history is worth keeping because it is the shape of the
    refusal rather than a list of operators. A bare ``N g`` —
    ``ContentStream.fill_grey``'s own spelling — matched nothing and raised;
    :data:`_PATTERNS` carried a ``"fill"`` entry that cycle 1's F-008 found
    the if-chain never consulting, so the table described a classification
    that did not happen while the refusal that did happen was invisible. The
    entry came back when a mark that *is* filled arrived: the QR
    placeholder's chequer (CARD-306), whose dark modules are ``re f``. Both
    are now read, and the if-chain below really consults both — which is what
    F-008 was about, not the presence of the entry.

    **Default-DENY is unchanged by that.** A filled shape this module cannot
    place is still an ``AssertionError`` naming it: ``re f`` is read, ``re B``
    (fill *and* stroke) is not, ``Do`` is not, ``c`` is not, ``W`` is not.
    (The ``g`` that is read *inside* a text object is a third thing again —
    there it is the glyphs' tone.)
    """
    width: Decimal | None = None
    grey: Decimal | None = None
    fill: Decimal | None = None
    marks: list[Mark] = []
    for row in stream_text.splitlines():
        if not row.strip():
            continue
        if match := _PATTERNS["grey"].match(row):
            grey = Decimal(match.group(1))
        elif match := _PATTERNS["fill"].match(row):
            fill = Decimal(match.group(1))
        elif match := _PATTERNS["box_fill"].match(row):
            assert fill is not None, row
            marks.append(
                Stroke(
                    "box_fill", tuple(Decimal(g) for g in match.groups()), FILLED, fill
                )
            )
        elif match := _PATTERNS["width"].match(row):
            width = Decimal(match.group(1))
        elif match := _PATTERNS["line"].match(row):
            assert width is not None and grey is not None, row
            marks.append(
                Stroke("line", tuple(Decimal(g) for g in match.groups()), width, grey)
            )
        elif match := _PATTERNS["box"].match(row):
            assert width is not None and grey is not None, row
            marks.append(
                Stroke("box", tuple(Decimal(g) for g in match.groups()), width, grey)
            )
        elif match := _PATTERNS["text"].match(row):
            fill, _resource, size, x, y, text = match.groups()
            marks.append(
                Shown(text, Decimal(x), Decimal(y), Decimal(size), Decimal(fill))
            )
        else:
            raise AssertionError(
                f"the page emitted an operator this module does not know how to "
                f"read, so nothing can be said about it: {row!r}"
            )
    return marks


# --------------------------------------------------------------------------
# The cases
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    """One drawn puzzle page, with everything an assertion needs about it."""

    label: str
    row: dict
    layout: Layout
    band: HeaderBand
    text: str
    stream: ContentStream
    spec: PageSpec
    page_number: int
    puzzle_number: int

    @property
    def furniture(self) -> _Furniture:
        """This page's sheet furniture, recomputed in the test tree (CARD-306)."""
        return _furniture_of(
            self.layout, self.spec, self.page_number, (self.puzzle_number,)
        )

    @property
    def oracle(self) -> Expected:
        return Expected(
            self.layout, Decimal(str(book_vector_draw.INK_GREY)), interior_face_metrics()
        )

    @property
    def puzzle_marks(self) -> list[Mark]:
        """The marks that make this page a **puzzle** page: ``book_puzzle_vector``'s.

        Split out from :attr:`expected` by CARD-306, which added the sheet's
        furniture to the production call: the two halves are drawn by two
        modules and a failure that names which half it is in is worth the
        property.
        """
        return self.oracle.page(self.band, self.text, _slot_room(self.layout))

    @property
    def furniture_marks(self) -> list[Mark]:
        """The marks that make this page a **sheet**: ``book_sheet_vector``'s."""
        return self.oracle.furniture(self.furniture)

    @property
    def expected(self) -> list[Mark]:
        return self.puzzle_marks + self.furniture_marks

    @property
    def found(self) -> list[Mark]:
        """The marks this page really emitted, read back out of a written PDF.

        Through :data:`_MARKS` when the page was written as part of a whole
        interior, and otherwise by writing a PDF of its own.

        **What this cache buys has changed, and the change is on main.** This
        docstring used to say that writing one PDF per assertion is slower
        than the ink assertion it replaces — 29.17 ms against 20.58 ms —
        because ADR-0042/R5 Flate-compresses the whole 757 KB face once per
        *file* and that one term was 98.8 % of a one-page write. ``5d84976c``
        memoises the compressed face, and after it the same arm measures
        **14.54x faster** than the ink assertion (1.54 ms against 22.39 ms),
        while the arm that shares one written interior is now the **slower**
        of the two file-writing arms at 8.55x — it re-extracts a 24-page PDF's
        content streams on every assertion.

        So what the cache here still removes is **extraction, not writing**:
        :func:`_read_back_together` parses one sixty-page file once for the
        whole module and each assertion reads a parsed result. *Parse a shared
        PDF once per fixture* is the guidance that survived; *share the written
        file* is the one that was retracted. Both figures, the no-cache
        control that reproduces the old 0.71x, and the retraction are in
        ``meta/profiling/card-295-puzzle-page-price.md``'s post-cache
        addendum, which is also where to re-measure them — on a quiet box.
        """
        held = _MARKS.get(id(self.stream))
        if held is not None:
            return held[1]
        pdf = write_vector_pdf([self.stream], 1).getvalue()
        (written,) = pdf_vector.content_streams(pdf)
        return marks_of(written)


def _cm(millimetres: float) -> str:
    return f"{millimetres / 10:.2f}"


def _book(width_mm: float, height_mm: float, book_id: str) -> Book:
    """A book on a stated trim, as the ``books`` table carries one."""
    return Book(
        book_id=book_id,
        metadata=BookMetadata(
            title="Winter Pictures",
            description="CARD-295's corpus.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(width_mm),
        trim_height_cm=_cm(height_mm),
        gutter_margin_cm=_cm(0.5 * 25.4),
        outside_margin_cm=_cm(0.5 * 25.4),
    )


#: The three KDP trims the corpus sweeps, in millimetres. Book 1's own
#: 8.5x11 in first, then the two smaller trims the panel offers, because the
#: cell — and so the clue type size, and so every centred position — is fitted
#: to the page and a one-trim corpus would hold one cell.
TRIMS = (
    (8.5 * 25.4, 11 * 25.4),
    (7.5 * 25.4, 9.25 * 25.4),
    (6.0 * 25.4, 9.0 * 25.4),
)

#: The corpus's floor, asserted inside the test that uses it so it cannot
#: silently shrink (CLAUDE.md's test style, G-6).
MIN_CASES = 54
MIN_EXTENTS = 20
MIN_PAGES_WITH_TEXT = 54


def _generators() -> list[BookPDFGenerator]:
    return [
        BookPDFGenerator(_book(width, height, f"card295-{index}"))
        for index, (width, height) in enumerate(TRIMS)
    ]


def _corpus(seed: int = 295, cases: int = 60) -> list[Case]:
    """``cases`` puzzle pages over seeded extents, trims, densities and parities.

    Hand-built with :class:`random.Random`, because ``hypothesis`` is not in
    the dependency baseline (ADR-0006/R1) and this tree builds its property
    corpora by hand.
    """
    rng = Random(seed)
    generators = _generators()
    built: list[Case] = []
    for index in range(cases):
        generator = generators[index % len(generators)]
        columns = rng.randrange(10, 31)
        rows = rng.randrange(10, 31)
        depth = rng.randrange(1, min(6, (min(columns, rows) + 1) // 2) + 1)
        number = rng.randrange(1, 400)
        tier = rng.choice(("easy", "medium", "hard"))
        page = A_PUZZLE_PAGE + index  # both parities, many pages
        row = puzzle(
            f"card295-{index}", columns, rows, depth, tier, f"Picture {index}"
        )
        built.append(
            _case(generator, row, number, page, f"{columns}x{rows} d{depth} p{page}")
        )
    return built


def _case(
    generator: BookPDFGenerator,
    row: dict,
    number: int,
    page: int,
    label: str,
) -> Case:
    """One page drawn through the production call, with its inputs recovered.

    The stream comes from :meth:`BookPDFGenerator.vector_puzzle_page` — the
    call a book really makes — and the ``Layout`` is then recomputed from the
    same spec, which is the same answer because ``compute_layout`` is pure and
    total (``_blank_page`` relies on exactly that for its own second call).
    """
    payload = BookPDFGenerator._payload(row)
    sizes = generator.cell_sizes([payload])
    stream = generator.vector_puzzle_page(payload, number, page, sizes)
    spec = generator._puzzle_page_spec(
        page, sizes[BookPDFGenerator._grid_size(payload)]
    )
    layout = compute_layout(payload.row_clues, payload.column_clues, spec)
    return Case(
        label=label,
        row=row,
        layout=layout,
        band=header_band(layout),
        text=band_identity(number, payload.difficulty),
        stream=stream,
        spec=spec,
        page_number=page,
        puzzle_number=number,
    )


#: ``{id(stream): (stream, its marks)}`` for pages written together as one
#: interior. The stream is held in the value so the ``id`` cannot be reused by
#: a later object — a cache keyed on identity has to keep what it keyed on.
_MARKS: dict[int, tuple[ContentStream, list[Mark]]] = {}


def _read_back_together(cases: Sequence[Case]) -> None:
    """Write every case's page into ONE PDF and parse all of them from it.

    One write and **one extraction** for sixty pages instead of sixty of
    each, and post-``5d84976c`` the second half is the half that pays: the
    price document's own shared-interior arm, which re-extracts per
    assertion, measures 8.55x against the ink assertion where a per-assertion
    *write* now measures 14.54x. See the addendum in
    ``meta/profiling/card-295-puzzle-page-price.md``; this shape pays
    extraction once per fixture, which is the recommendation that survived
    the cache.
    """
    pdf = write_vector_pdf([case.stream for case in cases], len(cases)).getvalue()
    written = pdf_vector.content_streams(pdf)
    assert len(written) == len(cases), (len(written), len(cases))
    for case, text in zip(cases, written, strict=True):
        _MARKS[id(case.stream)] = (case.stream, marks_of(text))


@pytest.fixture(scope="module")
def corpus() -> list[Case]:
    """The seeded corpus, drawn once and written once for the module.

    The same shape ``tests/test_book_pdf_band.py``'s own shared-render fixture
    takes, for the same reason CARD-218 gave it one.
    """
    cases = _corpus()
    _read_back_together(cases)
    return cases


#: The hero page's clue depth. 15 is the deepest a 30x30 can carry
#: (``_gutter_grid`` needs ``2 * depth - 1`` cells) and it is the depth that
#: puts **480** digits on the page — the spike measured its own hero at 540,
#: and AC-3 asks for that order of magnitude. The baseline book's own 30x30 is
#: 9 deep and carries 204, which is why this page is built rather than found.
HERO_DEPTH = 15
MIN_HERO_DIGITS = 400


@pytest.fixture(scope="module")
def hero() -> Case:
    """A 30x30 at the deepest clue set it can carry: the page with the most digits."""
    generator = BookPDFGenerator(corpus_book())
    row = puzzle("card295-hero", 30, 30, HERO_DEPTH, "hard", "Hero Picture")
    return _case(generator, row, 4, A_PUZZLE_PAGE, "30x30 hero")


@pytest.fixture(scope="module")
def min_trim_hero() -> Case:
    """The same 30x30 on the **smallest trim the panel offers**.

    AC-3 was asserted on one page until cycle 1's F-006, and the page it was
    asserted on is the roomiest the book has: 8.5x11 in, cell 50, clue type 32
    px. The cell is fitted to the trim, so the smallest trim prints the
    smallest clue digits the book can print — cell 33, clue type 21 — and the
    centring arithmetic divides by the type size. If poppler and the writer
    were going to disagree anywhere it is here.
    """
    width, height = TRIMS[-1]
    generator = BookPDFGenerator(_book(width, height, "card295-min-trim"))
    row = puzzle("card295-min-hero", 30, 30, HERO_DEPTH, "hard", "Small Hero")
    return _case(generator, row, 4, A_PUZZLE_PAGE, "30x30 at the minimum trim")


@dataclass(frozen=True)
class Twin:
    """One puzzle drawn **both** ways: the stream, and the raster page's ink.

    The same row, the same puzzle number, the same interior page, the same
    book — so the only difference between the two sides is the medium, which
    is what makes a disagreement between them mean something.

    Attributes:
        generator: The book this page belongs to.
        case: The vector side, read back out of a written PDF like every
            other :class:`Case`.
        page: The raster side's page bitmap. **The module's only one.**
        drawing: What :func:`tests.helpers.page_ink.drawing_of` measures off
            that bitmap — the grid's box and its rule count, in device
            pixels, found by looking at the page and nothing else. That
            helper imports no ``nonogram.export.layout`` and no
            ``book_page_spec`` (its own docstring), so it is a reading of the
            ink rather than a second statement of the geometry.
        digest: ``page``'s pixels when the fixture drew it, so a consumer
            that drew on the shared bitmap is a failure rather than a
            surprise for whatever ran next (see
            :class:`TestPuzzlePage_TheSharedPagesAreNotMutated`).
    """

    generator: BookPDFGenerator
    case: Case
    page: Image.Image
    drawing: page_ink.Drawing
    digest: bytes


@pytest.fixture(scope="module")
def twin() -> Twin:
    """The first baseline puzzle, drawn as a stream and as a bitmap, once.

    One bitmap for the whole module: AC-1's positive control and the
    cross-medium seam both take this fixture rather than drawing a page each.
    """
    generator = BookPDFGenerator(corpus_book())
    row = print_order(baseline_puzzles())[0]
    case = _case(generator, row, 1, A_PUZZLE_PAGE, "the raster twin's own page")
    page = generator._blank_page(
        BookPDFGenerator._payload(row),
        1,
        A_PUZZLE_PAGE,
        generator.cell_sizes([BookPDFGenerator._payload(row)]),
    )
    return Twin(
        generator=generator,
        case=case,
        page=page,
        drawing=page_ink.drawing_of(page),
        digest=page_digest(page),
    )


def _furniture_words(sheet: _Furniture) -> list[str]:
    """Every word the sheet's furniture sets, in no particular order (CARD-306).

    Derived from the furniture the page carries — the footer's verdict
    included, so a page that fell back to the corner folio contributes its
    one number and nothing else, and a page that lost its footer entirely
    contributes nothing. Split on whitespace because that is what
    ``pdftotext -bbox`` reports: ``"20 x 25"`` reaches a reader as three
    words, not one.
    """
    if sheet.content_bottom is not None and sheet.content_bottom > sheet.frame.footer_rule.y:
        # The corner fallback is itself conditional; what it draws is read
        # from the stream by the all-or-nothing tests, not guessed here.
        return []
    words = list(sheet.folio.split())
    if sheet.size_label is not None:
        words += sheet.size_label.split()
    for group in sheet.groups:
        words += group.invitation.split() + group.link.split()
    return words


def _furniture_rows(case: Case) -> tuple[int, ...]:
    """The rows this page's **furniture** rules are stroked on (CARD-306).

    Derived from COMP-007's :class:`~nonogram.export.layout.InteriorFrame`
    and from the footer's own all-or-nothing verdict — the header rule
    always, the footer hairline only where the page's content clears it — so
    this moves with the sheet rather than naming two numbers.
    """
    frame = case.furniture.frame
    bottom = case.furniture.content_bottom
    rows = [frame.header_rule.y]
    if bottom is None or bottom <= frame.footer_rule.y:
        rows.append(frame.footer_rule.y)
    return tuple(rows)


def _grid_strokes(case: Case) -> list[Stroke]:
    """``case``'s ruled lines with the **sheet's** rules taken out (CARD-306).

    Every reader below this point is asking about the *grid* — how many rules
    a column boundary gets, which weights the drawing carries, how the ink and
    the stream place the same box. Since CARD-306 the page also carries the
    interior frame's two horizontal rules, which are furniture and answer none
    of those questions.

    **Default-DENY, not a filter** (ADR-0039/R2): the rows that come out are
    :func:`_furniture_rows`' derived set, and exactly one stroke must be found
    on each. A furniture rule that moved, doubled or vanished reds here rather
    than quietly leaving the grid's readings one rule short — which is the
    failure mode a ``!=`` filter would have.
    """
    wanted = {
        _pt(Decimal(case.layout.height - row), case.layout.dpi): row
        for row in _furniture_rows(case)
    }
    grid: list[Stroke] = []
    found: dict[Decimal, int] = {y: 0 for y in wanted}
    for mark in case.found:
        if not isinstance(mark, Stroke) or mark.kind != "line":
            continue
        _x1, y1, _x2, y2 = mark.numbers
        if y1 == y2 and y1 in found:
            found[y1] += 1
            continue
        grid.append(mark)
    assert all(count == 1 for count in found.values()), (found, wanted)
    return grid


def _device_rules(case: Case) -> tuple[list[tuple[Decimal, Decimal]], ...]:
    """``case``'s ruled lines back in **device pixels**, as the raster has them.

    Returns ``(verticals, horizontals)``, each a list of
    ``(position, width)``: the position of a vertical is its ``x`` and of a
    horizontal its ``y`` **measured down from the page's top**, because that
    is the frame a bitmap is indexed in and a comparison between two media
    has to be made in one of them. Only ``Stroke``s are read — the frame's
    ``re`` box and the text are not ruled lines — and the conversion is the
    one the stream itself did, run backwards.
    """
    scale = Decimal(POINTS_PER_INCH) / Decimal(case.layout.dpi)
    height = Decimal(case.layout.height)
    verticals: list[tuple[Decimal, Decimal]] = []
    horizontals: list[tuple[Decimal, Decimal]] = []
    for mark in _grid_strokes(case):
        x1, y1, x2, _y2 = mark.numbers
        if x1 == x2:
            verticals.append((x1 / scale, mark.width / scale))
        else:
            horizontals.append((height - y1 / scale, mark.width / scale))
    return verticals, horizontals


def _inked_rule_widths(twin: Twin) -> list[int]:
    """How wide the raster page's rules really are, counted in its own pixels.

    One scanline through the middle of the first row of cells, and the
    lengths of its unbroken runs of ink. Exactly the reading
    ``tests/test_book_pdf_band.py``'s ``TestBookPdf_EveryFifthGridLineWider``
    makes, and exactly the reading
    ``meta/profiling/card295_puzzle_page_price.py``'s **ink arm** makes — that
    instrument cross-checks it against the stream's ``w`` operands before it
    times anything, and this is that cross-check moved to where something
    runs it.

    The scan starts at the grid's left border and runs one cell past its
    right one, so the first and last runs are heavy rules and every run
    between them is a rule of one of the two weights; a clue digit's ink is
    outside the box on both axes.
    """
    drawing = twin.drawing
    mask = page_ink.ink_mask(twin.page)
    middle = drawing.grid_top + round(
        (drawing.grid_bottom - drawing.grid_top) / drawing.rows / 2
    )
    cell = round((drawing.grid_right - drawing.grid_left) / drawing.columns)
    widths: list[int] = []
    run = 0
    for inked in mask[middle, drawing.grid_left : drawing.grid_right + cell].tolist():
        if inked:
            run += 1
        elif run:
            widths.append(run)
            run = 0
    if run:
        widths.append(run)
    assert len(widths) >= drawing.columns + 1, widths
    return sorted(set(widths))


# --------------------------------------------------------------------------
# AC-1 / EC(ADR-0042/R1) — the page carries no bitmap
# --------------------------------------------------------------------------


class TestPuzzlePage_CarriesNoImageXObject:
    """AC-1 and EC(ADR-0042/R1), on the pages this card writes.

    ADR-0042/R1's own derived guard is CARD-298's and checks *every* interior
    page kind at once; this is the page-local control that fails first.

    Two readings, because "no image" can be true in two different ways and
    only one of them is checked by looking at ``/Resources``: a page could
    name no XObject and still paint one through a form, and a page could name
    one and never paint it. So the resource dictionary is read **and** the
    operator alphabet is closed (``Do`` is the operator that paints an
    XObject, and it is not in the set).
    """

    def test_no_page_of_a_whole_books_puzzle_section_names_an_xobject(self) -> None:
        generator = BookPDFGenerator(corpus_book())
        payloads = [
            BookPDFGenerator._payload(row) for row in print_order(baseline_puzzles())
        ]
        streams = list(generator.vector_puzzle_pages(payloads))
        pdf = write_vector_pdf(streams, len(streams)).getvalue()

        keys = pdf_vector.page_resource_keys(pdf)
        # The floor: an empty reading passes a `for` loop trivially.
        assert len(keys) == len(streams) >= 3, (len(keys), len(streams))
        for page in keys:
            assert page == {"ProcSet", "Font"}, page

    def test_the_corpus_names_none_either_at_any_page_count(
        self, corpus: list[Case]
    ) -> None:
        """EC(ADR-0042/R1): "at any page count", over the seeded corpus.

        Written as one file of sixty pages rather than sixty files of one, so
        the claim is about a document the size of a real book's puzzle section
        and not about a cover sheet.
        """
        assert len(corpus) >= MIN_CASES, len(corpus)
        pdf = write_vector_pdf(
            [case.stream for case in corpus], len(corpus)
        ).getvalue()

        keys = pdf_vector.page_resource_keys(pdf)
        assert len(keys) == len(corpus)
        assert {frozenset(page) for page in keys} == {frozenset({"ProcSet", "Font"})}

    def test_the_operator_alphabet_is_closed_at_what_this_page_draws(
        self, hero: Case
    ) -> None:
        """Default-DENY over the operators, not a denylist of forbidden ones.

        The page sets a stroke tone, a width, lines, stroked boxes, a fill
        tone, filled boxes and text, and the set below is the whole of it. An
        image's ``Do`` fails this, and so does anything else a later edit
        reaches for.

        **``f`` joined the set in CARD-306 and that is the QR block's medium
        decision, visible here as one letter** (AC-4): the placeholder chequer
        is filled rectangles, so there is no image XObject to declare and
        ``Do`` is still absent. ``B`` — fill *and* stroke — is absent too,
        which is what keeps the addition one operator rather than a licence.

        The identity below is counted rather than asserted as a constant: a
        ``line`` is ``m l S`` and a rectangle is ``re`` followed by its own
        paint operator, so the strokes that are *not* lines (the drawing's
        frame and each QR icon's border) are ``S - m`` on one side and
        ``re - f`` on the other. Two independent ways of counting the same
        rectangles, which is what makes it a check and not a restatement.
        """
        (written,) = pdf_vector.content_streams(
            write_vector_pdf([hero.stream], 1).getvalue()
        )
        tally = pdf_vector.operator_tally(written)

        assert set(tally) == {
            "G", "w", "m", "l", "S", "re", "f", "g", "BT", "Tf", "Td", "Tj", "ET"
        }
        assert tally["m"] == tally["l"]
        assert tally["S"] - tally["m"] == tally["re"] - tally["f"] >= 2

    def test_the_page_draws_no_bezier(self, hero: Case) -> None:
        """No curve — stated as "no Bézier", which is what can be measured.

        **Not** "no round shape", and the difference is a measurement rather
        than a quibble: ``ContentStream`` offers ``begin_path``/``line_to``/
        ``close_path``/``paint``, so a disc can be approximated by a polygon
        of straight segments and no count of vertices separates one from a
        legitimate shape (CARD-296 measured a vertex bound impossible — the
        guide page's own arrow head needs three points and so does a
        triangle). The honest claim is about the operator, and the
        straight-segment approximation is a **named limit**: nothing here
        would notice one. It belongs to the card that reads every interior
        page kind at once, **CARD-298**.
        """
        (written,) = pdf_vector.content_streams(
            write_vector_pdf([hero.stream], 1).getvalue()
        )
        assert "c" not in pdf_vector.operator_tally(written)

    def test_the_raster_twin_of_the_same_page_does_carry_one(self, twin: Twin) -> None:
        """The control: this reading can fail, and here is it failing.

        The same puzzle, the same page number, the same book — drawn the way
        the book draws it today and written by the generator's own
        ``_write_pdf``. If this page's resources did *not* name an XObject,
        every assertion in this class would be measuring nothing.
        """
        raster = twin.generator._write_pdf(
            iter([twin.page]), 1, mode="L", kinds=(PageKind.PUZZLE,)
        ).getvalue()

        keys = pdf_vector.page_resource_keys(raster)
        assert len(keys) == 1
        assert "XObject" in keys[0], keys


# --------------------------------------------------------------------------
# AC-2 / EC(ADR-0042/R3) — every number is the Layout's
# --------------------------------------------------------------------------


class TestPropertyTest_PuzzlePage_EveryCoordinateComesFromTheLayout:
    """AC-2, over a seeded corpus of extents, trims, densities and parities.

    The class is ``TestPropertyTest_…`` and not the ``PropertyTest_…`` the
    card's AC spells, and the difference is the whole of CARD-294's review
    finding F-1: this repository configures no ``python_classes``, so pytest's
    default ``Test*`` applies and a class named ``PropertyTest_…`` collects
    **zero** tests with no skip, no error and no warning.
    ``tests/test_collected_names.py`` is the guard that now makes that a
    failure; the card's spelling would trip it.
    """

    def test_the_corpus_is_as_wide_as_it_claims(self, corpus: list[Case]) -> None:
        assert len(corpus) >= MIN_CASES, len(corpus)
        extents = {(case.layout.columns, case.layout.rows) for case in corpus}
        assert len(extents) >= MIN_EXTENTS, sorted(extents)
        assert len({case.layout.width for case in corpus}) == len(TRIMS)
        assert len({case.layout.cell for case in corpus}) > 1
        # Both parities, because a parity moves the usable area and so every
        # x in the stream.
        assert len({case.layout.page.parity for case in corpus}) == 2

    def test_every_mark_on_every_page_is_the_one_the_layout_demands(
        self, corpus: list[Case]
    ) -> None:
        for case in corpus:
            assert case.found == case.expected, case.label

    def test_every_page_draws_something(self, corpus: list[Case]) -> None:
        """The non-vacuity floor: an empty page agrees with an empty oracle."""
        drawn = [len(case.found) for case in corpus]
        assert min(drawn) >= 2 * (10 + 1) + 1, min(drawn)
        assert len([n for n in drawn if n > 0]) >= MIN_PAGES_WITH_TEXT

    def test_the_comparison_notices_one_pixel(self, corpus: list[Case]) -> None:
        """The control: a page drawn one pixel out fails the comparison.

        One device pixel at 300 DPI is 0.24 pt — the smallest move the stream
        can express at a whole-pixel ``Layout``, and three orders of magnitude
        above the 0.001 pt the numbers are written to. If the oracle could not
        see it, nothing above would mean anything.
        """
        case = corpus[0]
        moved = book_vector_draw.page_stream(case.layout)
        moved.stroke_grey(book_vector_draw.INK_GREY)
        moved.stroke_width(moved.to_points(case.layout.thin_rule))
        line = case.layout.vertical_lines[0]
        moved.line(line.position + 1, line.start, line.position + 1, line.end)

        (written,) = pdf_vector.content_streams(
            write_vector_pdf([moved], 1).getvalue()
        )
        assert marks_of(written)[0] != case.expected[0]

    def test_the_oracle_and_the_writer_round_the_same_way(self) -> None:
        """Exactly, not approximately — and this is where that is measured.

        Every number the page emits is a whole pixel converted to points, or
        a half-advance away from one. At 300 DPI the first kind is a multiple
        of 0.24 and the second has at most five decimal places with a
        denominator of 2000, so neither can land on the half-way case the two
        roundings would resolve differently. Swept here over every pixel of a
        page's width and every advance the face has.
        """
        dpi = 300
        for pixels in range(0, 3301):
            assert _pt(pixels, dpi) == Decimal(f"{pixels * 72 / dpi:.3f}"), pixels
        metrics = interior_face_metrics()
        for width in sorted(set(metrics.widths_1000.values())):
            for size in (13, 14, 59):
                exact = Decimal(width) * Decimal(size) / 2000
                assert _pt(exact, dpi) == Decimal(
                    f"{float(width) * size / 2000 * 72 / dpi:.3f}"
                ), (width, size)


class TestPropertyTest_PuzzlePage_WriterDerivesNoGeometry:
    """EC(ADR-0042/R3): no fallback, no rounding, no default when a Layout is silent.

    The AC's own sketch — "a ``Layout`` stub whose every accessor is recorded,
    asserting the stream contains no number the stub was not asked for" — is
    not quite the claim that can be made, and the correction is worth stating
    because it is about what R3 means. Two of the numbers a page emits are
    **not** values the ``Layout`` states and could not be: a string's centred
    left edge is a ``Layout`` coordinate minus half the face's advance, and a
    point size is a pixel size through the stream's own DPI. ``book_vector``
    assigns both to the caller in so many words. So the stream is held against
    the oracle above, which derives exactly those two from the ``Layout`` and
    the face and nothing else, and what is left for this class is the half an
    oracle cannot see: **what the writer does when the ``Layout`` says
    nothing**, which is where a fallback would live.
    """

    def _drawn(self, layout: Layout, band: HeaderBand, text: str, room: int) -> list[Mark]:
        stream = book_puzzle_vector.puzzle_page_stream(layout, band, text, room)
        (written,) = pdf_vector.content_streams(
            write_vector_pdf([stream], 1).getvalue()
        )
        return marks_of(written)

    def test_an_unframed_layout_gets_no_frame(self, corpus: list[Case]) -> None:
        """``frame is None`` draws nothing, rather than a box round the grid.

        The guide's cell icon is exactly this layout (CARD-201), so the branch
        is live rather than theoretical.
        """
        case = corpus[0]
        bare = _replace_layout(case.layout, frame=None)
        marks = self._drawn(bare, case.band, case.text, 10_000)

        assert not [mark for mark in marks if getattr(mark, "kind", "") == "box"]
        assert [mark for mark in case.found if getattr(mark, "kind", "") == "box"]

    def test_a_layout_with_no_clues_sets_no_digits(self, corpus: list[Case]) -> None:
        case = corpus[0]
        silent = _replace_layout(case.layout, row_clues=(), column_clues=())
        shown = [m for m in self._drawn(silent, case.band, "", 10_000) if isinstance(m, Shown)]

        assert shown == []

    def test_a_zero_width_rule_is_emitted_as_zero(self, corpus: list[Case]) -> None:
        """No floor, no ``max(1, …)``, no device minimum.

        The plant whose shape the writer was not built for: a ``Layout``
        stating a **zero** thin rule. ADR-0037/R2's device floor was an
        artefact of rasterisation and ADR-0042 removes it for the interior, so
        a writer that quietly lifted a zero to a hairline would be reinstating
        it where no test looks. The page must say what it was told.
        """
        case = corpus[0]
        flattened = _replace_layout(
            case.layout,
            vertical_lines=tuple(
                _replace_line(line, width=0, width_pt=0.0)
                for line in case.layout.vertical_lines
            ),
        )
        widths = {
            mark.width
            for mark in self._drawn(flattened, case.band, case.text, 10_000)
            if isinstance(mark, Stroke)
        }

        assert Decimal(0) in widths, widths

    def test_a_band_with_no_height_is_not_set(self, corpus: list[Case]) -> None:
        """A sheet that reserves no band has nowhere to put one."""
        case = corpus[0]
        empty = HeaderBand(height=0, center_x=100, center_y=10, font_size=12)
        shown = [
            m for m in self._drawn(case.layout, empty, case.text, 10_000) if isinstance(m, Shown)
        ]

        assert [m.text for m in shown] == [
            str(entry.value) for entry in case.layout.clue_entries
        ]

    def test_an_unplaced_layout_is_refused_rather_than_defaulted(self) -> None:
        """A drawing-sized ``Layout`` has no usable width, so none is invented."""
        payload = BookPDFGenerator._payload(puzzle("x", 10, 10, 3, "easy", "p"))
        unplaced = compute_layout(payload.row_clues, payload.column_clues)

        with pytest.raises(ValueError, match="PagePlacement"):
            book_puzzle_vector.slot_room(unplaced)

    def test_every_tone_comes_from_the_layout_and_the_grid_carries_two(
        self, corpus: list[Case]
    ) -> None:
        """ADR-0042/R3's tone half, which CARD-227 made satisfiable.

        **This used to be a declared gap.** Until CARD-227 the ``Layout``
        stated no tone at all, so R3's "every tone comes from the ``Layout``"
        could only be held as "the vector page's one tone is the *same
        constant* the raster page draws with, converted" — the writer's
        default, not the geometry's statement. ADR-0037/R2's cell lines are
        the first tone this project has had, and now the stronger claim is
        available: every tone on the page is one the ``Layout`` states, and
        the page carries **two** of them.

        Both arms are asserted, because either alone is weak. The *set*
        equality alone would pass on a page that had collapsed to one tone if
        the corpus happened to hold no fifth line; the *count* alone would
        pass on two tones nobody chose. And the default is still held against
        ``png.INK``, because the heavy rules are that same one ink and the two
        media must not disagree about what ink is.
        """
        assert book_vector_draw.INK_GREY == INK[0] / 255
        stated = {
            Decimal(str(book_vector_draw.INK_GREY if line.grey is None else line.grey))
            for case in corpus
            for line in case.layout.grid_lines
        }
        greys = {mark.grey for case in corpus for mark in case.found}

        assert len(stated) == 2, stated
        assert greys == stated, (greys, stated)


def _replace_layout(layout: Layout, **changes) -> Layout:
    """``dataclasses.replace`` for a slotted frozen ``Layout``."""
    from dataclasses import replace

    return replace(layout, **changes)


def _replace_line(line, **changes):
    from dataclasses import replace

    return replace(line, **changes)


# --------------------------------------------------------------------------
# AC-3 — the clue digits, read by an engine that did not write them
# --------------------------------------------------------------------------


@needs_poppler
class TestPuzzlePage_EveryClueDigitRendersWhereTheLayoutPutIt:
    """AC-3, on the spike's own hero page: a 30x30 at the book's cell.

    ``pdftotext -bbox`` is asked what it found and where. Both halves matter:
    the *what* exercises the embedded face's ``/Widths`` and ``/Encoding``
    (a wrong encoding extracts the wrong characters), and the *where*
    exercises the centring arithmetic against an engine that laid the glyphs
    out itself.
    """

    #: How far poppler's own box for a word may sit from the centre the
    #: ``Layout`` states, in points. **A margin over a measurement, not a
    #: guess** (cycle 1's F-006, which found the old 0.05 pt was ~125x the
    #: residual and so passed anything between 0.0005 and 0.05 pt silently):
    #: the residual was measured at **0.0004 pt** worst case, on four shapes
    #: — the hero, the minimum trim at 30x30, and a 10x10 at each — over
    #: every clue word, with nothing unmatched. 0.005 pt is twelve times that
    #: worst case and 48x tighter than the figure it replaces; one device
    #: pixel at 300 DPI, which is the smallest move the stream can express at
    #: a whole-pixel ``Layout``, is 0.24 pt, i.e. still 48x the tolerance, so
    #: the control below discriminates with two orders of magnitude to spare.
    SLACK_PT = 0.005

    def test_the_page_carries_a_digit_for_every_clue_entry(
        self, hero: Case, tmp_path
    ) -> None:
        pdf = write_vector_pdf([hero.stream], 1).getvalue()
        words = pdf_vector.word_boxes(pdf, out_dir=tmp_path)

        expected = [str(entry.value) for entry in hero.layout.clue_entries]
        assert len(expected) >= MIN_HERO_DIGITS, len(expected)
        found = [word.text for word in words]
        # The band's words, plus — since CARD-306 — the sheet's furniture's,
        # derived from the furniture this page really carries rather than
        # listed, so a mark that stopped being drawn reds here too.
        furniture = _furniture_words(hero.furniture)
        assert len(furniture) >= 8, furniture
        assert sorted(found) == sorted(expected + hero.text.split() + furniture), (
            len(found),
            len(expected),
            furniture,
        )

    def test_the_digits_are_the_clue_sets_own_encoding(self, hero: Case) -> None:
        """The values are ``clues.encode_line``'s, row by row and column by column.

        Re-derived from the puzzle's grid by COMP-002 rather than read off the
        ``Layout`` the page was drawn from, so the chain the page rests on —
        grid, clue set, layout, stream — is closed at both ends.
        """
        from nonogram import clues

        computed = clues.compute_clues(hero.row["grid"])
        by_line: dict[tuple[str, int], list[int]] = {}
        for kind, entries in (
            ("row", hero.layout.row_clues),
            ("column", hero.layout.column_clues),
        ):
            for entry in entries:
                by_line.setdefault((kind, entry.line), []).append(entry.value)

        for index, clue in enumerate(computed.rows):
            assert tuple(by_line[("row", index)]) == clue, index
        for index, clue in enumerate(computed.columns):
            assert tuple(by_line[("column", index)]) == clue, index

    def test_each_digit_is_centred_where_the_layout_placed_it(
        self, hero: Case, tmp_path
    ) -> None:
        """Poppler's own box for each word, against the ``Layout``'s centre.

        The tolerance is :data:`SLACK_PT`, and what it is a margin over is
        stated there rather than here, because the figure is the claim: the
        agreement is exact to within 0.0004 pt and anything looser than that
        would be describing an engine's rounding as a tolerance.
        """
        pdf = write_vector_pdf([hero.stream], 1).getvalue()
        words = pdf_vector.word_boxes(pdf, out_dir=tmp_path)
        scale = POINTS_PER_INCH / hero.layout.dpi
        wanted = {
            (
                round(entry.center_x * scale, 3),
                round(entry.center_y * scale, 3),
                str(entry.value),
            )
            for entry in hero.layout.clue_entries
        }

        matched = 0
        for word in words:
            for x, y, text in wanted:
                if (
                    word.text == text
                    and abs(word.center_x - x) <= self.SLACK_PT
                    and abs(word.center_y - y) <= self.SLACK_PT
                ):
                    matched += 1
                    break
        assert matched == len(hero.layout.clue_entries), (matched, len(wanted))

    def test_the_smallest_digits_the_book_prints_land_there_too(
        self, min_trim_hero: Case, tmp_path
    ) -> None:
        """The same reading at the other end of the trim range (F-006).

        A 30x30 on 6.0x9.0 in: cell 33 px and clue type 21 px, against the
        hero's 50 and 32. The type size is the divisor in both halves of
        ``set_centred``'s arithmetic, so the smallest type is where a rounding
        that the hero's page absorbs would show. It does not: the residual
        here measures 0.0003 pt, the same order as the hero's.
        """
        pdf = write_vector_pdf([min_trim_hero.stream], 1).getvalue()
        words = pdf_vector.word_boxes(pdf, out_dir=tmp_path)
        layout = min_trim_hero.layout
        scale = POINTS_PER_INCH / layout.dpi
        wanted = {
            (
                round(entry.center_x * scale, 3),
                round(entry.center_y * scale, 3),
                str(entry.value),
            )
            for entry in layout.clue_entries
        }

        assert len(layout.clue_entries) >= MIN_HERO_DIGITS, len(layout.clue_entries)
        assert layout.cell < 40 and layout.clue_font_size < 32, (
            layout.cell,
            layout.clue_font_size,
        )
        matched = 0
        for word in words:
            for x, y, text in wanted:
                if (
                    word.text == text
                    and abs(word.center_x - x) <= self.SLACK_PT
                    and abs(word.center_y - y) <= self.SLACK_PT
                ):
                    matched += 1
                    break
        assert matched == len(layout.clue_entries), (matched, len(wanted))

    def test_the_placement_check_can_fail(self, hero: Case, tmp_path) -> None:
        """The control: a digit set one pixel off is outside the tolerance.

        The plant is **not** a shifted page — the writer would shift the
        expectation with it. It is one digit drawn at a position the
        ``Layout`` never states, one device pixel from a clue's own centre,
        and the question asked is whether poppler reports it where it was put
        rather than where the clue is.

        Drawn on a stream of its own rather than onto ``hero``'s: the fixture
        is module-scoped, a ``ContentStream`` is mutable, and this control
        written the obvious way put a stray ``7`` on the hero page for every
        test that ran after it. That was a real failure in this module's first
        run, and ``test_the_shared_hero_is_what_the_fixture_drew`` is what
        keeps it from coming back quietly.
        """
        entry = hero.layout.clue_entries[0]
        stream = book_vector_draw.page_stream(hero.layout)
        book_vector_draw.set_centred(
            stream,
            "7",
            entry.center_x + 1,
            entry.center_y,
            hero.layout.clue_font_size,
            interior_face_metrics(),
        )
        pdf = write_vector_pdf([stream], 1).getvalue()
        scale = POINTS_PER_INCH / hero.layout.dpi

        planted = [w for w in pdf_vector.word_boxes(pdf, out_dir=tmp_path) if w.text == "7"]
        assert planted, "the plant was not rendered at all"
        assert all(
            abs(word.center_x - entry.center_x * scale) > self.SLACK_PT
            for word in planted
        )


# --------------------------------------------------------------------------
# AC-4 — the band
# --------------------------------------------------------------------------


class TestPuzzlePage_BandCarriesNumberAndTierAndNeverTheTitle:
    """AC-4 / ADR-0037/R1: the number and the tier, and never the picture.

    The half that can fail is the second one, so it is asserted over every
    page of a whole book's puzzle section rather than over one page — the
    same shape CARD-297's AC-2 is told to take for the answer key.
    """

    def _streams_and_names(self) -> tuple[list[ContentStream], list[str], list[str]]:
        generator = BookPDFGenerator(corpus_book())
        rows = print_order(baseline_puzzles())
        payloads = [BookPDFGenerator._payload(row) for row in rows]
        bands = [
            band_identity(number, payload.difficulty)
            for number, payload in enumerate(payloads, start=1)
        ]
        names = [row["puzzle_name"] for row in rows]
        return list(generator.vector_puzzle_pages(payloads)), bands, names

    def test_every_band_the_section_shows_is_a_number_and_a_tier(self) -> None:
        streams, bands, _ = self._streams_and_names()
        pdf = write_vector_pdf(streams, len(streams)).getvalue()

        shown = [
            text
            for written in pdf_vector.content_streams(pdf)
            for text in _shown_strings(written)
        ]
        assert set(bands) <= set(shown), (sorted(set(bands) - set(shown)))
        assert all(re.fullmatch(r"Puzzle \d+(?: · \w+)?", band) for band in bands), bands

    def test_no_page_of_the_puzzle_section_shows_a_picture_title(self) -> None:
        streams, _, names = self._streams_and_names()
        pdf = write_vector_pdf(streams, len(streams)).getvalue()
        text = "\n".join(pdf_vector.content_streams(pdf))

        assert names and all(name for name in names), names
        for name in names:
            assert name not in text, name

    def test_the_title_is_absent_because_it_is_never_passed(self) -> None:
        """Where ADR-0037/R1 is kept, named rather than inferred.

        The raster page keeps it by *clearing* the payload's name before
        ``render_pages`` reads it (``_puzzle_payload``). The vector page never
        reaches the name at all: the band is ``band_identity``'s line and
        nothing else is set on the page. The control is a payload whose name
        is unmistakable.
        """
        generator = BookPDFGenerator(corpus_book())
        row = puzzle("named", 12, 12, 3, "medium", "ZZZ-UNMISTAKABLE-ZZZ")
        payload = BookPDFGenerator._payload(row)
        stream = generator.vector_puzzle_page(
            payload, 7, A_PUZZLE_PAGE, generator.cell_sizes([payload])
        )

        (written,) = pdf_vector.content_streams(
            write_vector_pdf([stream], 1).getvalue()
        )
        assert "ZZZ-UNMISTAKABLE-ZZZ" not in written
        assert "Puzzle 7 · Medium" in written

    @needs_poppler
    def test_a_reader_can_select_the_band(self, hero: Case, tmp_path) -> None:
        """And it is ink a reader gets, not only an operand.

        ``·`` is U+00B7, is not ASCII, and is the one character on the page
        that a wrong ``/Encoding`` would turn into a different glyph. Read
        back through poppler for that reason.
        """
        pdf = write_vector_pdf([hero.stream], 1).getvalue()
        extracted = pdf_vector.extracted_text(pdf, out_dir=tmp_path)

        assert hero.text in extracted, (hero.text, extracted[:200])
        assert " · " in hero.text

    def test_the_band_fits_the_way_the_raster_page_fits_it(
        self, corpus: list[Case]
    ) -> None:
        """One fitting rule in three places, held equal from here.

        ``book_puzzle_vector`` reimplements the two ratios natively rather
        than importing them across a module boundary (this package's standing
        convention), which is only safe while something holds the copies
        together. Three now, where
        ``test_a_two_up_band_is_fitted_by_the_exports_own_header_ratios``
        holds two.

        The **third** quantity the rule needs is the room the line is fitted
        into, and until cycle 1's F-005 nothing held it at all: the raster
        callers compute ``placement.usable_right - placement.usable_left``
        inline (``_two_up_page``, ``pdf.render_pages``), so there is no
        constant to compare and ``slot_room``'s answer was only ever checked
        against itself. It is held here against the two
        :class:`~nonogram.export.layout.PagePlacement` fields the raster
        callers read, over the whole corpus — which is the most that *can* be
        held across this boundary while the other two copies are expressions
        rather than names.
        """
        assert book_puzzle_vector.BAND_WIDTH_RATIO == _BAND_WIDTH_RATIO
        assert book_puzzle_vector.MIN_BAND_FONT_RATIO == _MIN_BAND_FONT_RATIO
        assert book_puzzle_vector.BAND_WIDTH_RATIO == export_pdf._HEADER_WIDTH_RATIO
        assert book_puzzle_vector.MIN_BAND_FONT_RATIO == export_pdf._MIN_HEADER_FONT_RATIO

        assert len(corpus) >= MIN_CASES, len(corpus)
        rooms = set()
        for case in corpus:
            placement = case.layout.page
            assert placement is not None, case.label
            assert book_puzzle_vector.slot_room(case.layout) == (
                placement.usable_right - placement.usable_left
            ), case.label
            rooms.add(book_puzzle_vector.slot_room(case.layout))
        # Not one room repeated sixty times: the three trims and both parities
        # give the equality something to be wrong about.
        assert len(rooms) >= len(TRIMS), rooms

    def test_a_band_too_wide_for_its_room_is_set_smaller(self, corpus: list[Case]) -> None:
        """The shrink, which no real band reaches, exercised where it does.

        A band is about a tenth of a page's usable width, so the correction
        below is unreachable from a real book — which is exactly why it needs
        a case of its own rather than a comment saying it works.
        """
        case = corpus[0]
        metrics = interior_face_metrics()
        room = book_puzzle_vector.slot_room(case.layout)

        assert (
            book_puzzle_vector.band_type_size(case.text, case.band, room, metrics)
            == case.band.font_size
        )
        long_line = "Puzzle 1 · " + "Elephant " * 20
        shrunk = book_puzzle_vector.band_type_size(long_line, case.band, room, metrics)
        assert shrunk < case.band.font_size
        assert shrunk >= round(case.band.font_size * _MIN_BAND_FONT_RATIO)
        assert metrics.advance(long_line) * shrunk <= room * _BAND_WIDTH_RATIO


def _shown_strings(stream_text: str) -> list[str]:
    return [mark.text for mark in marks_of(stream_text) if isinstance(mark, Shown)]


# --------------------------------------------------------------------------
# The grid routine is a routine, not a page (CARD-296's AC-4, pointed back)
# --------------------------------------------------------------------------


class TestGridRoutine_DrawsALayoutItWasNotWrittenFor:
    """CARD-296 and CARD-297 are told to consume this card's grid routine.

    That claim is usually made by a guard that forbids a second
    implementation. CARD-296 built one and measured its hole (F-302): a
    default-DENY rule over "which routines may read a ``Layout``'s grid"
    cannot see a frozen dataclass with a ``sheet: Layout`` field, because the
    annotation arm reads function parameters and the rebinding arm skips an
    ``AnnAssign`` with no value — and five more shapes escape at helper level.

    So the claim is made from the other end, where it can be *measured*: the
    routine is run on the layouts the **next** card has to draw, and its
    output is held against the same oracle. A routine that needed to know it
    was drawing a puzzle page would fail here, and a card that can draw its
    own page with this call has no reason to write a second one.

    **The limit, by its shape rather than as an enumeration**: nothing here
    stops a later card writing a second grid walk anyway. Only its author's
    reading of this file would. Closing that syntactically is the hole
    CARD-296 measured; it is not closed here and it is not owned.
    """

    @staticmethod
    def _marks(stream: ContentStream, layout: Layout) -> tuple[list[Mark], list[Mark]]:
        (written,) = pdf_vector.content_streams(
            write_vector_pdf([stream], 1).getvalue()
        )
        oracle = Expected(
            layout, Decimal(str(book_vector_draw.INK_GREY)), interior_face_metrics()
        )
        return marks_of(written), oracle.grid() + oracle.frame()

    def test_it_draws_the_guides_worked_example_line(self) -> None:
        """CARD-296's item 1: "the small grid, its clues"."""
        spec = BookPDFGenerator(corpus_book()).page_spec(2)
        layout = example_line_layout(spec, (3, 1), 10)
        stream = book_vector_draw.page_stream(layout)
        book_vector_draw.draw_ruled_grid(stream, layout)
        if layout.frame is not None:
            book_vector_draw.draw_frame(stream, layout.frame)

        found, expected = self._marks(stream, layout)
        assert found == expected
        assert len(found) >= 10 + 1

    def test_it_draws_the_guides_single_cell_icon(self) -> None:
        """The unframed, one-cell layout — the shape that has no frame at all.

        ``guide_icon_layout`` drops its frame deliberately (CARD-201), which
        is why ``_stroke_drawing``'s own ``frame is None`` guard is live. The
        same guard is live here, and this is the case that takes it.
        """
        spec = BookPDFGenerator(corpus_book()).page_spec(2)
        layout = guide_icon_layout(spec)
        assert layout.frame is None
        stream = book_vector_draw.page_stream(layout)
        book_vector_draw.draw_ruled_grid(stream, layout)

        found, expected = self._marks(stream, layout)
        assert found == expected
        assert len(found) == 4

    def test_the_routine_imports_nothing_that_knows_a_page_kind(self) -> None:
        """What the module *couples* to, read off its imports rather than its prose.

        Default-DENY over the module's whole import list: a page kind reaches
        a module through an import, and this one's is closed at the drawing
        vocabulary, COMP-007's geometry and the renderers' ink. The day it
        imports ``book_pdf_generator`` — where ``band_identity``, the folio
        and every other page-kind word live — it has stopped being a routine
        and this fails naming the import.

        An import list is checkable where a docstring's adjectives are not,
        and its hole is stated: a page kind passed in as an *argument* would
        not be seen here. That is what the two cases above measure instead.
        """
        import ast
        from pathlib import Path

        tree = ast.parse(
            Path(book_vector_draw.__file__).read_text(encoding="utf-8")
        )
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)

        assert imported == {
            "__future__",
            "typing",
            "nonogram.admin.book_vector",
            "nonogram.export.layout",
            "nonogram.export.png",
        }, sorted(imported)


# --------------------------------------------------------------------------
# The seam between the two media, while both exist
# --------------------------------------------------------------------------


class TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture:
    """The boundary this card stops at, held where its docstring claims it.

    ``book_puzzle_vector``'s docstring says the sheet's furniture — the
    interior frame's two rules, the footer's grid-size label, the folio and
    the QR caption — is **not drawn** *by that module*, because every
    interior page kind carries the same furniture off the same
    ``interior_frame`` and a page card that drew it would be the second of
    four to do so. A declaration that outlives its hole is the defect this
    board gates on most, so it is checked rather than written.

    **CARD-306 moved what was behind that boundary, and did not move the
    boundary.** When this class was written the docstring also said the
    furniture was drawn by *nothing*, and the test below read the page
    ``BookPDFGenerator.vector_puzzle_page`` composes — the two were the same
    page, because nothing else drew on it. They are no longer: the furniture
    is drawn by :mod:`nonogram.admin.book_sheet_vector` and composed into the
    production page, so this class now reads
    :func:`~nonogram.admin.book_puzzle_vector.puzzle_page_stream`'s **own**
    output, which is the call the docstring's claim is about. The whole page is
    read by :class:`TestSheetFurniture_TheProductionPageCarriesTheFurniture`
    instead, and the two together say what each module draws.
    """

    def test_the_page_shows_only_the_clue_digits_and_the_band(self, hero: Case) -> None:
        bare = book_puzzle_vector.puzzle_page_stream(
            hero.layout, hero.band, hero.text
        )
        pdf = write_vector_pdf([bare], 1).getvalue()
        (written,) = pdf_vector.content_streams(pdf)
        shown = [mark.text for mark in marks_of(written) if isinstance(mark, Shown)]
        expected = [str(entry.value) for entry in hero.layout.clue_entries]

        assert sorted(shown) == sorted(expected + [hero.text])
        # The control: the production page of the *same* layout shows more,
        # so this reading is a statement about the module and not about a
        # page that has no furniture anywhere.
        composed = [mark.text for mark in hero.found if isinstance(mark, Shown)]
        assert len(composed) > len(shown)

    def test_the_raster_twin_shows_more(self, twin: Twin) -> None:
        """The other side of the same statement, measured not assumed.

        The raster page of the same puzzle carries a folio, a grid-size label
        and a QR caption. Named here so the gap is a number somebody can act
        on rather than a sentence in a docstring.
        """
        from nonogram.export.layout import interior_frame

        frame = interior_frame(twin.generator.page_spec(A_PUZZLE_PAGE))
        assert frame.header_rule.width > 0 and frame.footer_rule.width > 0
        assert twin.page.size == (
            twin.generator.page_width_px,
            twin.generator.page_height_px,
        )


class TestPuzzlePage_AgreesWithTheRasterTwin:
    """The seam: the drawn **bitmap** and the written **stream**, against each
    other.

    **This class read only the stream until CARD-295's fix round, and that is
    the hole it now closes** (cycle 1, F-001): "the raster renderer would
    stroke the same ``Layout``, so the vector page uses it unchanged" is a
    syllogism, not a measurement, and the first two tests below prove only its
    second half. Cycle 1 measured the gap — it reversed ``png._draw_grid``'s
    major sort *and* moved every vertical rule 7 device pixels, so that the
    two media genuinely disagreed about both order and position, and this
    module stayed 35-green while the raster's own file went red. A seam that
    cannot see the other side of itself is not a seam, and G-4's refusal to
    convert the three pixel-reading files rests on this one: the stream half
    is added **beside** the ink half, which is only safe while something stops
    the two drifting.

    So the last two tests read the raster page's **own ink** —
    :func:`tests.helpers.page_ink.drawing_of` and one scanline — and hold it
    against the operands the stream really emitted. What is compared is only
    what *can* be compared across the two media, and each is named below
    rather than left as "they agree":

    * **counted** — one vertical rule group per column boundary, in both;
    * **spanned** — the grid's width and height in device pixels, identically;
    * **placed** — the two media's edges differ by **one** offset, the same
      number on all four, and no more than half a heavy rule. That residue is
      Pillow's own line-cap convention for an even-width stroke and not a
      disagreement about geometry: PDF strokes a path centred on its
      coordinate and Pillow's thick line does not, so the constant is the
      thing to hold rather than zero;
    * **weighted** — the widths the ink measures are the widths the stream
      sets, which is the comparison
      ``meta/profiling/card295_puzzle_page_price.py``'s ``claim`` arm already
      made (ink ``[3, 6]`` device pixels against stream ``[0.72, 1.44]``
      points) and that nothing in the suite ran.

    **What the seam does not reach**, by its shape rather than as a list: it
    compares the *grid*, because the grid is the mark both media draw from the
    same ``Layout`` fields and the only one whose ink is identifiable without
    a second renderer. The clue digits are not compared across the media —
    their ink is the face's rasterisation on one side and poppler's on the
    other — and AC-3 holds them against poppler instead. The band is text and
    the same applies. A later card that makes the two media *interchangeable*
    (**CARD-298**) is where that widens.
    """

    def test_every_ruled_line_is_at_the_layouts_own_device_position(
        self, hero: Case
    ) -> None:
        scale = Decimal(POINTS_PER_INCH) / Decimal(hero.layout.dpi)
        # The **grid's** rules: since CARD-306 the page also carries the
        # interior frame's two, which are the sheet's and are read by
        # ``TestSheetFurniture_*`` instead (:func:`_grid_strokes`).
        lines = _grid_strokes(hero)
        strokes = lines

        assert len(lines) == len(hero.layout.vertical_lines) + len(
            hero.layout.horizontal_lines
        )
        # The widths are compared in **points**, not device pixels, because
        # since CARD-227 that is the unit the sheet states them in: a book
        # page declares ADR-0037/R2's three physical weights and the stream
        # sets them through no conversion, so dividing by ``scale`` here would
        # be inventing a device reading of a number no device chose. The
        # positions above are still device pixels, which is the half of this
        # test that ``scale`` is for.
        widths = {mark.width for mark in lines}
        assert widths == {Decimal("0.3"), Decimal("0.8"), Decimal("1.3")}, widths

    def test_the_thin_rules_are_stroked_before_the_heavy_ones(
        self, hero: Case
    ) -> None:
        """The ordering claim, which is the one a set comparison cannot make."""
        thin = Decimal("0.3")
        order = [
            mark.width == thin for mark in hero.found if isinstance(mark, Stroke)
        ]
        assert any(order) and not all(order), order
        assert order == sorted(order, reverse=True), order

    def test_the_ink_and_the_stream_rule_the_same_grid(self, twin: Twin) -> None:
        """Counted, spanned and placed — the geometry half of the seam.

        The raster side is read off the bitmap by ``page_ink``, which is told
        nothing about the ``Layout``; the vector side is the operands of a
        written PDF, converted back to device pixels. Neither number comes
        from the other's arithmetic, and neither comes from ``compute_layout``
        at all, so this is the one assertion in the module that would notice
        the **raster** page moving.
        """
        verticals, horizontals = _device_rules(twin.case)
        drawing = twin.drawing
        heavy = max(width for _position, width in verticals + horizontals)
        major_x = sorted(position for position, width in verticals if width == heavy)
        major_y = sorted(position for position, width in horizontals if width == heavy)

        # counted
        assert len(verticals) == drawing.columns + 1, (len(verticals), drawing.columns)
        assert len(horizontals) == drawing.rows + 1, (len(horizontals), drawing.rows)
        assert len(major_x) >= 2 and len(major_y) >= 2, (major_x, major_y)
        # spanned
        assert major_x[-1] - major_x[0] == drawing.grid_right - drawing.grid_left
        assert major_y[-1] - major_y[0] == drawing.grid_bottom - drawing.grid_top
        # placed — one offset on all four edges, inside half a heavy rule
        offsets = {
            Decimal(drawing.grid_left) - major_x[0],
            Decimal(drawing.grid_right) - major_x[-1],
            Decimal(drawing.grid_top) - major_y[0],
            Decimal(drawing.grid_bottom) - major_y[-1],
        }
        assert len(offsets) == 1, offsets
        assert abs(offsets.pop()) * 2 <= heavy, (offsets, heavy)
        # and the frame is drawn, or not, in both
        boxes = [
            mark
            for mark in twin.case.found
            if isinstance(mark, Stroke) and mark.kind == "box"
        ]
        assert bool(boxes) is drawing.framed is (twin.case.layout.frame is not None)

    def test_the_inked_widths_are_never_the_declared_figures(self, twin: Twin) -> None:
        """The weighted half, **re-expressed by CARD-227 and now a stronger seam.**

        Until CARD-227 this arm compared ``[3, 6]`` device pixels off the page
        against ``[0.72, 1.44]`` points off the stream and asserted the two
        were the same two rules. **That comparison is now false by design**,
        and not because either medium drifted: ADR-0037/R2 as amended
        2026-10-25 states the interior's weights as physical points — 0.3 /
        0.8 / 1.3 — which hold *only* in a content stream, while the raster
        twin keeps COMP-007's proportional ``cell / 30`` device rule. Two
        media that state different widths is the card. A seam that kept
        asserting they agreed would have had to be satisfied by undoing it.

        So what is held here instead is the thing R2 actually makes falsifiable
        on real ink, and it is the measured form of AC-7: **no width this page
        was rasterised at is the device count of a declared figure.** At
        300 DPI those counts are 1 / 3 / 5 px — the one-pixel grey cell grid
        7 of 17 reviews of the 450-puzzle book complained about — and the
        raster twin's own widths are 3 and 6 px.

        Both hierarchies are asserted intact first, so the comparison cannot
        pass by either side collapsing to one weight, and the positive arm —
        the instrument's **reach** — is that the reading can see a width the
        twin really does stroke, so its silence about 1 px is a measurement
        rather than a blind spot.

        **That reach arm is keyed on the layout's own ``thin_rule``, not on a
        declared figure's count** (review cycle 1, F-007). It used to be
        ``counts[1] in inked``, which was true only by a coincidence of this
        book's fitted cell: ``counts[1]`` is ``round(0.8 pt at 300 DPI)`` = 3
        and ``layout.thin_rule`` is also 3, so on a book whose thin rule
        fitted to 4 px the arm would have reddened with nothing wrong. The
        page is known to ink ``thin_rule`` for a reason that has nothing to do
        with the declared weights — it is COMP-007's proportional
        ``cell / 30`` under the 0.25 mm raster floor — so keying on it makes
        the reach arm independent of the figures the negative arm is about.
        The coincidence itself is recorded rather than relied on.

        **Each figure stays in its own domain.** The stream's widths are read
        in points, because points are the unit it states them in; the ink's
        are read in device pixels, because that is what a bitmap has. The one
        number that crosses is the declared figures' *device count*, which is
        the quantity ADR-0037/R2 names and the only one the two sides can be
        compared through at all.
        """
        stated = sorted({mark.width for mark in _grid_strokes(twin.case)})
        inked = _inked_rule_widths(twin)
        counts = sorted(
            round(rule.width_pt * twin.case.layout.dpi / 72)
            for rule in (GRID_RULES.cell, GRID_RULES.fifth, GRID_RULES.border)
        )

        # Both media still carry a hierarchy of their own.
        assert stated == [Decimal("0.3"), Decimal("0.8"), Decimal("1.3")], stated
        assert inked == sorted(
            {twin.case.layout.thin_rule, twin.case.layout.thick_rule}
        ), (inked, twin.case.layout.thin_rule, twin.case.layout.thick_rule)

        # The refused configuration is not on the page: 1 px is absent.
        assert counts == [1, 3, 5], counts
        assert counts[0] not in inked, (inked, counts)
        # ... and the reading can see a width the page is known to ink for a
        # reason independent of the declared figures, so its silence about
        # 1 px is a measurement rather than a blind spot.
        assert twin.case.layout.thin_rule in inked, (
            inked,
            twin.case.layout.thin_rule,
        )
        # The coincidence F-007 named, declared rather than relied on: on this
        # book thin_rule and counts[1] happen to be the same 3 px.
        assert twin.case.layout.thin_rule == counts[1] == 3, (
            twin.case.layout.thin_rule,
            counts,
        )


class TestPuzzlePage_TheSharedPagesAreNotMutated:
    """A ``ContentStream`` is mutable and two fixtures here are module-scoped.

    Written because this module's first run had the defect: a control that
    planted one extra digit drew it onto the shared hero, and every later test
    saw a page with a stray ``7`` on it. The same family as
    ``tests/test_book_pdf_band.py``'s
    ``TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated``, which exists for
    the same reason on images.
    """

    def test_the_shared_hero_is_what_the_fixture_drew(self, hero: Case) -> None:
        fresh = BookPDFGenerator(corpus_book()).vector_puzzle_page(
            BookPDFGenerator._payload(hero.row),
            4,
            A_PUZZLE_PAGE,
            BookPDFGenerator(corpus_book()).cell_sizes(
                [BookPDFGenerator._payload(hero.row)]
            ),
        )
        assert hero.stream.operators == fresh.operators

    def test_every_page_of_the_shared_corpus_still_matches_its_layout(
        self, corpus: list[Case]
    ) -> None:
        """The corpus's own version of the same question, cheaply.

        Operator counts rather than a redraw: a mutation adds or removes
        operators, and sixty redraws to find that out would cost more than the
        whole module does today.
        """
        for case in corpus:
            assert len(case.stream.operators) == len(
                case.expected
            ) + _state_operators(case.layout) + _furniture_state_operators(
                case.furniture
            ), case.label

    def test_the_operator_count_holds_on_a_page_of_many_widths(
        self, corpus: list[Case]
    ) -> None:
        """:func:`_state_operators`' own control, which it had none of.

        The corpus has exactly two rule widths on every page, so a derivation
        that counted *distinct* widths and one that counts *changes of* width
        agree on all sixty — which is how cycle 1's F-009 went unnoticed. The
        case that tells them apart is a page whose widths alternate, so equal
        widths are no longer contiguous after the sort: here the two
        derivations read **21** and **7**, and the stream agrees with the one
        that counts changes.
        """
        case = corpus[0]
        # Stripes the **declared** width, which is what this sheet's writer
        # sets: a book page states ADR-0037/R2's physical weights, so striping
        # the device ``width`` alone would leave the stream unchanged and this
        # control vacuous — the near-miss worth naming, because the test that
        # would have gone on passing is this one.
        striped = _replace_layout(
            case.layout,
            vertical_lines=tuple(
                _replace_line(line, width=1 if index % 2 else 5, width_pt=0.24 if index % 2 else 1.2)
                for index, line in enumerate(case.layout.vertical_lines)
            ),
        )
        stream = book_puzzle_vector.puzzle_page_stream(
            striped, case.band, case.text, 10_000
        )
        expected = Expected(
            striped, Decimal(str(book_vector_draw.INK_GREY)), interior_face_metrics()
        ).page(case.band, case.text, 10_000)

        naive = 1 + len(
            {
                line.width if line.width_pt is None else line.width_pt
                for line in striped.grid_lines
            }
        )
        naive += 2 if striped.frame is not None else 0
        assert _state_operators(striped) > naive + 5, (
            _state_operators(striped),
            naive,
        )
        assert len(stream.operators) == len(expected) + _state_operators(striped)

    def test_the_shared_raster_twin_is_the_bitmap_the_fixture_drew(
        self, twin: Twin
    ) -> None:
        """The same question about the module's one page bitmap.

        A ``PIL.Image`` is mutable and the twin is handed to the generator's
        own ``_write_pdf`` by AC-1's control, so the seam's ink reading is
        only a reading of *that* page while nothing has drawn on it since.
        ``page_digest`` is ``tests/helpers/shared_fixture_controls.py``'s, the
        same reader ``tests/test_book_pdf_band.py`` checks its shared interior
        with.
        """
        assert page_digest(twin.page) == twin.digest


def _furniture_state_operators(sheet: _Furniture) -> int:
    """How many ``G``/``w``/``g`` operators the **furniture** emits beside its marks.

    :func:`_state_operators`' sibling for CARD-306's marks, derived the same
    way — from what the sheet actually carries, not from a constant:

    * the header rule sets a tone and a width, always: **2**;
    * a page whose footer is not clear stops there, and its fallback corner
      folio is a text object that carries its own ``g`` inside the ``BT``
      block (which :func:`marks_of` reads as part of the mark);
    * a page with a footer adds the hairline's own tone and width: **2**;
    * each QR group sets a tone and a width for the icon's border and a
      **fill** tone for the chequer: **3** apiece.
    """
    if sheet.content_bottom is not None and sheet.content_bottom > sheet.frame.footer_rule.y:
        return 2
    return 2 + 2 + 3 * len(sheet.groups)


def _state_operators(layout: Layout) -> int:
    """How many ``G``/``w`` operators a page emits beside its marks.

    One ``G`` for the grid's tone, one ``w`` **per change of width along the
    stroke order**, and — where the drawing is framed — one ``G`` and one
    ``w`` for the frame.

    The width term used to be ``len({widths})``, which is the same number
    only while equal widths are contiguous after the sort — true of every
    page the corpus holds (two widths, thin then major) and false in general.
    Cycle 1's F-009 built a ``Layout`` whose non-major verticals alternate
    1, 5, 1, 5 px: ``draw_grid_lines`` sets the width on change, so it emitted
    16 ``w`` operators and still agreed with the oracle exactly, while the
    old derivation predicted 7. It now counts the changes
    ``draw_grid_lines`` makes, over the one stroke order
    :func:`_in_stroke_order` states, so it moves with any page rather than
    with a two-width one.

    **The tone term was a constant ``1`` until CARD-227 and is now counted
    the same way**, for exactly the reason the width term is: a book page has
    two tones (0.35 grey cell lines under pure-black fifths and border), the
    writer sets the tone on change over the same stroke order, and a page
    whose tones alternate emits one ``G`` per change rather than one per page.
    A derivation that kept the ``1`` would have been right on every page the
    corpus holds and wrong on the first page that interleaved its tones —
    which is the shape of the defect F-009 already found once here.
    """
    lines = [line for line, _vertical in _in_stroke_order(layout)]
    widths = [
        line.width if line.width_pt is None else line.width_pt for line in lines
    ]
    tones = [
        book_vector_draw.INK_GREY if line.grey is None else line.grey
        for line in lines
    ]

    def changes(values: list[object]) -> int:
        return sum(1 for before, after in zip([None, *values], values) if before != after)

    return changes(widths) + changes(tones) + (2 if layout.frame is not None else 0)


# --------------------------------------------------------------------------
# CARD-306 — the sheet's furniture on the vector puzzle page
# --------------------------------------------------------------------------


def _text_marks(case: Case) -> list[Shown]:
    return [mark for mark in case.found if isinstance(mark, Shown)]


def _furniture_only(case: Case) -> list[Mark]:
    """``case``'s marks with the puzzle's own taken off the front (CARD-306).

    The furniture is drawn after the puzzle, so it is the tail — and the head
    must be exactly :attr:`Case.puzzle_marks`, which is asserted rather than
    assumed, so a puzzle mark that moved into the tail reds here instead of
    being read as furniture.
    """
    head = case.puzzle_marks
    assert case.found[: len(head)] == head, case.label
    return case.found[len(head) :]


def _stream_of(sheet: _Furniture, layout: Layout) -> ContentStream:
    """``sheet``'s furniture alone, on an empty page of ``layout``'s extent.

    The production writer through the production spec type, so a test that
    varies one field of the furniture is varying the real writer's input.
    """
    from nonogram.admin.book_sheet_vector import SheetFurniture, draw_sheet_furniture

    stream = book_vector_draw.page_stream(layout)
    draw_sheet_furniture(
        stream,
        SheetFurniture(
            frame=sheet.frame,
            folio=sheet.folio,
            folio_size_px=sheet.folio_size_px,
            size_label=sheet.size_label,
            label_size_px=sheet.label_size_px,
            caption_size_px=sheet.caption_size_px,
            qr_modules=sheet.qr_modules,
            groups=tuple(
                _production_group(group) for group in sheet.groups
            ),
            content_bottom=sheet.content_bottom,
            right_hand=sheet.right_hand,
        ),
        interior_face_metrics(),
    )
    return stream


def _production_group(group: _QrGroup):
    from nonogram.admin.book_sheet_vector import QrGroup

    return QrGroup(
        icon=group.icon,
        caption=group.caption,
        invitation=group.invitation,
        link=group.link,
    )


def _marks_of_stream(stream: ContentStream) -> list[Mark]:
    (written,) = pdf_vector.content_streams(write_vector_pdf([stream], 1).getvalue())
    return marks_of(written)


class TestSheetFurniture_TheProductionPageCarriesTheFurniture:
    """AC-1: the folio, the frame rules, the grid-size label and the QR block.

    **Each asserted by its own operators in the stream**, never by a rendered
    bitmap — so "the page carries a folio" is a text object at the trim's own
    centre and not a count of dark pixels. The oracle's half of this is
    :meth:`Expected.furniture`, which the module's own
    ``test_every_mark_on_every_page_is_the_one_the_layout_demands`` already
    holds over sixty pages; what these tests add is that each *named* piece is
    present and identified, so a failure says which piece went missing rather
    than that a list of 540 marks differs somewhere.
    """

    def test_the_page_carries_all_four_pieces_of_furniture(self, hero: Case) -> None:
        sheet = hero.furniture
        frame = sheet.frame
        tail = _furniture_only(hero)
        rules = [
            mark
            for mark in tail
            if isinstance(mark, Stroke) and mark.kind == "line"
        ]
        texts = [mark for mark in tail if isinstance(mark, Shown)]
        filled = [
            mark
            for mark in tail
            if isinstance(mark, Stroke) and mark.kind == "box_fill"
        ]
        icons = [
            mark for mark in tail if isinstance(mark, Stroke) and mark.kind == "box"
        ]

        # the frame rules: both of them, on COMP-007's own rows
        assert [mark.numbers[1] for mark in rules] == [
            _pt(Decimal(hero.layout.height - frame.header_rule.y), hero.layout.dpi),
            _pt(Decimal(hero.layout.height - frame.footer_rule.y), hero.layout.dpi),
        ], rules
        # the folio: one mark, centred on the TRIM's own centre
        folio = [mark for mark in texts if mark.text == sheet.folio]
        assert len(folio) == 1, texts
        assert abs(frame.folio_x * 2 - hero.layout.width) <= 1, (
            frame.folio_x,
            hero.layout.width,
        )
        # The coincidence this book makes, declared rather than relied on:
        # its gutter and outside margins are equal, so the trim's centre and
        # the usable area's are the same column here and this page cannot
        # tell the two rules apart. The claim that it is the *trim's* is the
        # equality above, which is a reading of the sheet.
        assert frame.folio_x == (frame.header_rule.left + frame.header_rule.right) // 2
        # the grid-size label: this puzzle's own extent, on the gutter side
        assert sheet.size_label == f"{hero.layout.columns} x {hero.layout.rows}"
        assert [mark.text for mark in texts].count(sheet.size_label) == 1, texts
        # the QR block: one bordered chequer and its two lines
        assert len(sheet.groups) == 1, sheet.groups
        (group,) = sheet.groups
        assert len(icons) == 1, icons
        assert len(filled) == sheet.qr_modules**2 // 2, len(filled)
        assert {mark.text for mark in texts} >= {group.invitation, group.link}

    def test_the_reading_sees_each_piece_go_missing(self, hero: Case) -> None:
        """The instrument's control: each of the four reads can fail (ADR-0039/R1).

        The page above is unmutated; what is mutated here is the **reading**,
        by taking one piece out of the marks the page emitted and re-running
        the assertion that names it. A read that passed on a page with no
        folio would be measuring nothing, and this is where that is shown
        rather than argued. The code-level mutants — deleting the folio's
        draw, breaking the all-or-nothing coupling — are run out of tree
        against this same module; these are the in-suite halves that run on
        every commit.
        """
        sheet = hero.furniture
        tail = _furniture_only(hero)
        (group,) = sheet.groups
        gone = {
            "folio": [m for m in tail if not (isinstance(m, Shown) and m.text == sheet.folio)],
            "label": [
                m for m in tail if not (isinstance(m, Shown) and m.text == sheet.size_label)
            ],
            "rules": [
                m for m in tail if not (isinstance(m, Stroke) and m.kind == "line")
            ],
            "chequer": [
                m for m in tail if not (isinstance(m, Stroke) and m.kind == "box_fill")
            ],
            "caption": [
                m
                for m in tail
                if not (isinstance(m, Shown) and m.text in {group.invitation, group.link})
            ],
        }
        for piece, without in gone.items():
            assert len(without) < len(tail), piece
        assert not [
            m for m in gone["folio"] if isinstance(m, Shown) and m.text == sheet.folio
        ]
        assert not [m for m in gone["rules"] if isinstance(m, Stroke) and m.kind == "line"]

    def test_the_footer_lines_sit_where_the_raster_page_sets_them(
        self, twin: Twin
    ) -> None:
        """The anchor claim, measured across the two media (CARD-306).

        ``book_sheet_vector`` takes the footer row as a **baseline**, which is
        the convention every vector footer mark in this package uses. Pillow's
        ``b`` anchor — what the raster page uses — puts the *ink box's* bottom
        on the row instead. For a string with no descender those are the same
        place; for one with a descender they are not, and the one footer mark
        that has a descender is the typed link.

        Measured on the bundled face at the footer's own size rather than
        reasoned: the three descender-free strings agree exactly, the link
        differs by the face's descender depth, and both halves are asserted
        so neither can drift unnoticed.
        """
        from importlib import resources
        from io import BytesIO

        from PIL import ImageFont

        size = type_px(INTERIOR_FOOTER_LINE_PT, DPI)
        face = ImageFont.truetype(
            BytesIO(
                resources.files(export_pdf.FONT_PACKAGE)
                .joinpath(export_pdf.FONT_RESOURCE)
                .read_bytes()
            ),
            size=size,
        )
        sheet = twin.case.furniture
        (group,) = sheet.groups
        no_descender = (sheet.folio, sheet.size_label, group.invitation)
        for text in no_descender:
            assert _ink_rows(face, text, "lb") == _ink_rows(face, text, "ls"), text
        # ... and the one that does descend. The two media put its ink in
        # different places by exactly its own descender, which is a figure
        # rather than a surprise: 9 device pixels at the book's 300 DPI, or
        # 0.76 mm.
        _top_b, bottom_b = _ink_rows(face, group.link, "lb")
        _top_s, bottom_s = _ink_rows(face, group.link, "ls")
        offset = bottom_s - bottom_b
        assert offset == 9, offset
        assert 0 < offset <= face.getmetrics()[1], (offset, face.getmetrics())
        # The property that matters, and it holds: the lower ink still lands
        # inside the footer strip, clear of the bottom margin by most of the
        # icon's own row.
        assert group.caption.link_baseline + offset < sheet.frame.page_bottom, (
            group.caption.link_baseline,
            offset,
            sheet.frame.page_bottom,
        )


def _ink_rows(face, text: str, anchor: str) -> tuple[int, int]:
    """The top and bottom rows ``text``'s ink occupies at ``anchor``.

    Drawn on a scratch bitmap and read back, because the question is where
    Pillow puts the glyphs and not what its metrics say it will.
    """
    import numpy as np
    from PIL import ImageDraw

    canvas = Image.new("L", (2000, 600), 255)
    ImageDraw.Draw(canvas).text((20, 400), text, font=face, fill=0, anchor=anchor)
    rows = np.nonzero((np.asarray(canvas) < 128).any(axis=1))[0]
    return int(rows.min()), int(rows.max())


#: The corpus floor for the all-or-nothing count, asserted inside the test
#: that uses it so it cannot silently shrink (CLAUDE.md's test style).
MIN_FOOTER_PAGES = 54


class TestSheetFurniture_TheFooterIsAllOrNothing:
    """AC-2 and EC(all-or-nothing footer), in **both** directions.

    ``_draw_page_frame``'s footer group is all-or-nothing, so the vector
    version must be: *a page with a frame and no number, or a number and no
    frame, is a defect, not a degraded state.* Both halves are asserted
    directly, and each has a mutant — the code-level pair is run out of tree
    (both reds recorded on the card), and what runs here is the behaviour
    those mutants break.
    """

    def test_a_clear_footer_draws_the_rule_and_the_number_together(
        self, hero: Case
    ) -> None:
        sheet = hero.furniture
        assert sheet.content_bottom <= sheet.frame.footer_rule.y
        tail = _furniture_only(hero)
        rows = [
            mark.numbers[1]
            for mark in tail
            if isinstance(mark, Stroke) and mark.kind == "line"
        ]
        folio_row = _pt(
            Decimal(hero.layout.height - sheet.frame.baseline), hero.layout.dpi
        )

        assert len(rows) == 2, rows
        assert [
            mark for mark in tail if isinstance(mark, Shown) and mark.text == sheet.folio
        ][0].y == folio_row

    def test_a_blocked_footer_draws_neither_the_rule_nor_the_number(
        self, hero: Case
    ) -> None:
        """The other direction, on the production writer.

        The sheet is the hero's own, with **one field** changed: the content's
        own bottom row moved one pixel past the footer rule, which is the
        figure ``_draw_page_frame`` reaches its verdict from. Nothing else
        about the page differs, so what is measured is the verdict and not a
        second page.
        """
        from dataclasses import replace

        blocked = replace(
            hero.furniture,
            content_bottom=hero.furniture.frame.footer_rule.y + 1,
            groups=(),
        )
        marks = _marks_of_stream(_stream_of(blocked, hero.layout))
        rules = [m for m in marks if isinstance(m, Stroke) and m.kind == "line"]
        texts = [m for m in marks if isinstance(m, Shown)]

        # The header rule is unconditional; the footer's hairline is gone.
        assert len(rules) == 1, rules
        assert rules[0].numbers[1] == _pt(
            Decimal(hero.layout.height - blocked.frame.header_rule.y), hero.layout.dpi
        )
        # No centred folio and no label on the footer line, because there is
        # no footer line. Whether the CORNER folio is drawn is CARD-200's own
        # omit-rather-than-collide rule, and the oracle states which.
        assert [m.y for m in texts] == [
            m.y for m in hero.oracle.furniture(blocked) if isinstance(m, Shown)
        ]
        assert blocked.size_label is not None
        assert blocked.size_label not in {m.text for m in texts}

    def test_the_one_pixel_either_side_of_the_verdict_decides_it(
        self, hero: Case
    ) -> None:
        """The claim's **edge**, which is the mutant ADR-0039/R1 asks for.

        ``content_bottom == footer_rule.y`` draws the footer and
        ``content_bottom == footer_rule.y + 1`` does not. One pixel, and the
        page changes from four pieces of furniture to one — so the inequality
        is ``<=`` and not ``<``, which is the off-by-one a reading of the
        whole page would not localise.
        """
        from dataclasses import replace

        row = hero.furniture.frame.footer_rule.y
        counts = []
        for bottom in (row, row + 1):
            sheet = replace(hero.furniture, content_bottom=bottom, groups=())
            marks = _marks_of_stream(_stream_of(sheet, hero.layout))
            counts.append(
                len([m for m in marks if isinstance(m, Stroke) and m.kind == "line"])
            )

        assert counts == [2, 1], counts

    def test_the_corpus_counts_folios_and_frames_equal(
        self, corpus: list[Case]
    ) -> None:
        """EC(all-or-nothing footer) over the seeded corpus of trims and extents.

        The count of pages carrying a **centred folio** equals the count
        carrying a **footer rule** — read off each page's own stream, not
        derived from the verdict the writer returned.
        """
        assert len(corpus) >= MIN_FOOTER_PAGES, len(corpus)
        with_rule = 0
        with_folio = 0
        for case in corpus:
            sheet = case.furniture
            tail = _furniture_only(case)
            rules = [m for m in tail if isinstance(m, Stroke) and m.kind == "line"]
            baseline = _pt(
                Decimal(case.layout.height - sheet.frame.baseline), case.layout.dpi
            )
            centred = [
                m
                for m in tail
                if isinstance(m, Shown) and m.text == sheet.folio and m.y == baseline
            ]
            assert len(rules) in (1, 2), (case.label, rules)
            with_rule += len(rules) == 2
            with_folio += len(centred) == 1

        assert with_rule == with_folio, (with_rule, with_folio)
        # The floor, and it is the reason this corpus is worth sweeping: the
        # equality would hold trivially on a corpus where every page, or no
        # page, had a footer. **Measured: 47 of these 60 pages carry one and
        # 13 do not** — the 13 are the page-fit-bound grids whose drawing
        # reaches past the footer rule, which is exactly the branch
        # ``_draw_page_frame`` keeps CARD-200's corner for. So both arms of
        # the all-or-nothing verdict are exercised by this one count.
        assert with_rule == 47, with_rule
        assert 0 < len(corpus) - with_rule == 13, (with_rule, len(corpus))

    def test_a_footer_that_is_not_there_cannot_carry_a_qr_group(
        self, hero: Case
    ) -> None:
        """The refusal, which is the coupling made structural.

        ``qr_slot`` answers ``None`` on exactly the figure the footer's own
        verdict reads, so a caller composing both from one layout cannot
        produce this. One that measured the icon on a different extent can —
        the defect CARD-248 removed from the raster two-up page — and the
        writer refuses it rather than drawing a chequer on a page with no
        footer line.
        """
        from dataclasses import replace

        from nonogram.admin.book_sheet_vector import SheetFurnitureError

        blocked = replace(
            hero.furniture, content_bottom=hero.furniture.frame.footer_rule.y + 1
        )
        assert blocked.groups, "the hero's own group, kept"

        with pytest.raises(SheetFurnitureError, match="no footer"):
            _stream_of(blocked, hero.layout)


#: The numeric literals ``book_sheet_vector`` is allowed to contain, each with
#: the reason it is not a coordinate. **A default-DENY allowlist**
#: (ADR-0039/R2): the guard below collects every numeric constant in the
#: module's AST and asserts set equality against this, so a literal nobody
#: justified is a FAILURE rather than something the walk did not look for.
#:
#: * ``0`` — ``(row + column) % 2 != 0`` and ``modules <= 0``;
#: * ``1`` — ``range``'s own step is not here, but ``column + 1``/``row + 1``
#:   are: the chequer's far edge is one module along;
#: * ``2`` — the chequer's parity, and the halving a centred string needs;
#: * ``0.0`` — the type-size defaults on :class:`SheetFurniture`, which say
#:   "this page prints no mark at this size" and are read only when the
#:   matching string is ``None``;
#: * ``2.0`` — the float form of the halving, so the division is not integer.
#:
#: No coordinate, no row, no weight, no point size. That is G-2 and AC-3: a
#: magic number copied from ``_draw_page_frame`` is the defect they exist to
#: catch, and this is the instrument that would catch it.
SHEET_VECTOR_LITERALS = frozenset({0, 1, 2, 0.0, 2.0})


class TestSheetFurniture_OneDefinitionNotTwo:
    """AC-3: every piece's geometry comes from one source shared with the raster.

    Three readings, because "one definition" can fail in three ways:

    * a **coordinate** written into the vector module — caught by the literal
      allowlist above, derived from the module's own AST;
    * a **weight** picked rather than read — caught by holding the QR icon's
      border against the footer hairline's own width, which is where the
      raster placeholder's literal ``width=2`` really comes from;
    * an **import** that would let the vector module re-derive a position —
      caught by walking its imports, the same reading
      ``TestGridRoutine_DrawsALayoutItWasNotWrittenFor`` already makes of
      ``book_vector_draw``.
    """

    MODULE = "src/nonogram/admin/book_sheet_vector.py"

    def _tree(self):
        import ast
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        source = (root / self.MODULE).read_text()
        return ast.parse(source), source

    def test_the_module_writes_no_coordinate_of_its_own(self) -> None:
        import ast

        tree, _source = self._tree()
        found = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        }

        assert found == SHEET_VECTOR_LITERALS, sorted(
            found.symmetric_difference(SHEET_VECTOR_LITERALS), key=repr
        )

    def test_no_number_is_handed_to_a_drawing_call(self) -> None:
        """The arm the value allowlist alone does **not** have, measured.

        ``2`` is on the allowlist for the chequer's parity and for halving a
        centred string, so a transcription that happens to be ``2`` passes
        it — and the one transcription most likely to be written here is
        exactly that: ``stroke_width(to_points(2))``, the raster
        placeholder's own literal border weight, which on a book page is
        **numerically identical** to the hairline the writer is supposed to
        read off the frame. Mutant M5 planted it and every other guard in
        this module stayed green.

        So the second arm is structural rather than numeric: **no numeric
        literal reaches any call as an argument.** A number may be compared
        (``modules <= 0``), may be a modulus (``% 2``), may be a divisor
        (``/ 2.0``) and may be a field default — none of those is a figure
        being handed to something that draws. One that is handed to a call is
        either a coordinate, a weight or a size, and all three belong to the
        caller.
        """
        import ast

        tree, _source = self._tree()
        # ``bool`` is an ``int``, and ``@dataclass(frozen=True, slots=True)``
        # hands two of them to a call on every dataclass in the module. A
        # ``True`` is not a figure, so it is excluded by type and not by value.
        handed = [
            (node.lineno, argument.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            for argument in [*node.args, *(kw.value for kw in node.keywords)]
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, (int, float))
            and not isinstance(argument.value, bool)
        ]

        assert handed == [], handed

    def test_the_call_argument_walk_sees_the_numerically_identical_plant(self) -> None:
        """Its control, which is mutant M5 run in-suite.

        The plant is the border weight the raster page really does write as a
        literal, and it draws the **same line** this module draws today — so
        a reading of the page cannot tell it apart and only this walk can.
        The negative half: the same number in a modulus is not a figure handed
        to a call, and the walk stays silent on it.
        """
        import ast

        _tree, source = self._tree()

        planted = source.replace(
            "stream.to_points(furniture.frame.footer_rule.width)",
            "stream.to_points(2)",
        )
        assert planted != source
        found = [
            argument.value
            for node in ast.walk(ast.parse(planted))
            if isinstance(node, ast.Call)
            for argument in [*node.args, *(kw.value for kw in node.keywords)]
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, (int, float))
            and not isinstance(argument.value, bool)
        ]
        assert found == [2], found

        # The near miss: ``% 2`` is the chequer's own parity, not a figure
        # handed to anything, and the walk does not rise on it.
        assert "(row + column) % 2 != 0" in source
        quiet = [
            argument.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            for argument in [*node.args, *(kw.value for kw in node.keywords)]
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, (int, float))
            and not isinstance(argument.value, bool)
        ]
        assert quiet == [], quiet

    def test_the_walk_sees_a_planted_coordinate(self, tmp_path) -> None:
        """The instrument's positive control, and its negative (ADR-0039/R4).

        The **positive**: the same walk over the module's text with one
        coordinate planted in it — ``_draw_page_frame``'s own kind of number —
        finds it and the equality reds. The **negative**: the walk over a
        near-miss, the same number written inside a *docstring*, does **not**
        rise, because a number in prose is not a number in code and a guard
        that could not tell them apart would red on every paragraph this
        module has.
        """
        import ast

        _tree, source = self._tree()

        planted = source.replace(
            "    side = icon.right - icon.left",
            "    side = icon.right - icon.left - 2806",
        )
        assert planted != source
        found = {
            node.value
            for node in ast.walk(ast.parse(planted))
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
        }
        assert found != SHEET_VECTOR_LITERALS
        assert 2806 in found

        near_miss = source.replace(
            "not a lighter glyph", "not a lighter glyph (y=2806)"
        )
        assert near_miss != source
        quiet = {
            node.value
            for node in ast.walk(ast.parse(near_miss))
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
        }
        assert quiet == SHEET_VECTOR_LITERALS, sorted(quiet, key=repr)

    def test_the_icons_border_is_the_hairlines_own_weight(self, hero: Case) -> None:
        """The raster's literal ``width=2`` is the hairline, and here it is read.

        ``_draw_qr_placeholder`` strokes the icon's border at a literal 2
        device pixels, which is the 2-device-pixel furniture floor
        CARD-222/CARD-248 cite — and that floor is what ``interior_frame``
        already rounded ``INTERIOR_FOOTER_RULE_PT`` up to. The vector writer
        reads it off the frame, and that the two are the same number is
        asserted here rather than assumed, on the sheet a real book page uses.
        """
        frame = hero.furniture.frame
        tail = _furniture_only(hero)
        icons = [m for m in tail if isinstance(m, Stroke) and m.kind == "box"]

        assert frame.footer_rule.width == 2, frame.footer_rule
        assert len(icons) == 1, icons
        assert icons[0].width == _pt(
            Decimal(frame.footer_rule.width), hero.layout.dpi
        ), icons

    def test_the_module_imports_nothing_that_could_re_derive_a_position(self) -> None:
        """Its imports are COMP-007's measurements and the stream vocabulary.

        No page kind, no generator, no ``PageSpec`` door — so there is nothing
        it *could* measure a frame from even if a later edit wanted to, and
        ``book_pdf_generator`` can keep importing it without a cycle.
        """
        import ast

        tree, _source = self._tree()
        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        modules |= {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }

        assert modules == {
            "__future__",
            "dataclasses",
            "nonogram.admin.book_vector",
            "nonogram.admin.book_vector_draw",
            "nonogram.export.layout",
        }, sorted(modules)


class TestSheetFurniture_TheQrBlockIsOperatorsAndTheWriterRefusesAnXObject:
    """AC-4: the QR block's medium is declared, and the other choice is refused.

    **Decided: operators.** The icon is CARD-204's placeholder — a bordered
    square around a plain alternating chequer, never a real module pattern —
    so it is rectangles, not a photograph. Declaring it raster would mean an
    entry in ``_RASTER_DECLARATIONS`` with a reason, an ``expires_with`` and
    an image object on every page of the book, to ship a 5×5 chequer.

    The second half of the AC is the one that needs a mechanism rather than a
    preference: *an undeclared XObject on a vector page must be refused by the
    writer, not merely reported.* Leaving ``/XObject`` out of the resources —
    which ``write_vector_page`` already did — makes such an image unreachable
    to a **viewer**; it does not stop the operator being written, and a page
    whose stream paints something the file cannot resolve shows less than it
    says. So the writer now refuses a stream carrying ``Do``.
    """

    def test_the_chequer_is_filled_rectangles_and_the_count_is_derived(
        self, hero: Case
    ) -> None:
        from nonogram.admin.book_sheet_vector import qr_module_boxes

        sheet = hero.furniture
        (group,) = sheet.groups
        tail = _furniture_only(hero)
        filled = [m for m in tail if isinstance(m, Stroke) and m.kind == "box_fill"]

        # The count is the chequer's odd diagonal, derived from the module
        # count the generator owns rather than from the number 12.
        dark = sum(
            1
            for row in range(sheet.qr_modules)
            for column in range(sheet.qr_modules)
            if (row + column) % 2 != 0
        )
        assert len(filled) == dark == len(qr_module_boxes(group.icon, sheet.qr_modules))
        assert dark >= 1 and sheet.qr_modules >= 3, (dark, sheet.qr_modules)

    def test_the_vector_chequer_inks_where_the_raster_chequer_inks(
        self, twin: Twin
    ) -> None:
        """The cross-medium check on the one piece this card reimplemented.

        ``book_sheet_vector.qr_module_boxes`` is ``_draw_qr_placeholder``'s
        own tiling written natively, because that generator cannot be imported
        from a module it imports. So the two are held against each other here,
        where the import *is* legal: the same ``QrSlot``, the same module
        count, and the dark squares' own boxes compared edge for edge.

        The one documented difference is Pillow's inclusive rectangle: a
        raster module is one device pixel wider and taller than the path's,
        which is 0.085 mm at 300 DPI and is asserted as exactly one pixel
        rather than waved at.
        """
        from nonogram.admin.book_pdf_generator import (
            _QR_PLACEHOLDER_MODULES,
            _draw_qr_placeholder,
        )
        from nonogram.admin.book_sheet_vector import qr_module_boxes

        sheet = twin.case.furniture
        (group,) = sheet.groups
        icon = group.icon

        # The raster side, drawn on its own scratch page and read back as the
        # boxes it filled -- through the production function, not a copy.
        recorded: list[tuple] = []

        class _Spy:
            def rectangle(self, box, **kwargs):
                recorded.append((box, kwargs))

        _draw_qr_placeholder(_Spy(), icon)

        border, *modules = recorded
        assert border[1].get("width") == 2, border
        ours = qr_module_boxes(icon, _QR_PLACEHOLDER_MODULES)
        assert len(modules) == len(ours), (len(modules), len(ours))
        for (box, kwargs), mine in zip(modules, ours, strict=True):
            assert kwargs.get("fill") is not None, kwargs
            assert box == mine, (box, mine)

    def test_the_writer_refuses_a_page_that_paints_an_xobject(
        self, hero: Case
    ) -> None:
        """The refusal, with the page it refuses built by hand.

        ``ContentStream`` has no XObject vocabulary, so the only way to reach
        this is to append the operator — which is the case worth refusing, and
        the only one there is.
        """
        from nonogram.admin.book_vector import ContentStreamError

        smuggled = book_vector_draw.page_stream(hero.layout)
        smuggled.rectangle(0, 0, 10, 10)
        smuggled._operators.append("/Im0 Do")

        with pytest.raises(ContentStreamError, match="paints no XObject"):
            write_vector_pdf([smuggled], 1)

    def test_the_refusal_does_not_fire_on_a_near_miss(self, hero: Case) -> None:
        """Its negative control: ``Do`` inside a string, and a resource named Do.

        A text object whose literal happens to contain ``Do`` is not a painted
        XObject, and neither is a word ending in ``Do``. A refusal keyed on a
        substring would red on both, which would make it a guard nobody could
        keep — so the near-miss is measured rather than trusted to the regex's
        shape.
        """
        near = book_vector_draw.page_stream(hero.layout)
        near.text("Done. Do", 10, 10, 10.0)
        near.text("Dodo", 10, 40, 10.0)

        pdf = write_vector_pdf([near], 1).getvalue()
        (written,) = pdf_vector.content_streams(pdf)
        assert "Do" in written
        assert [m.text for m in marks_of(written)] == ["Done. Do", "Dodo"]


#: The furniture's own stroke floor, in **device pixels**. Not ADR-0037/R2's:
#: that rule binds the puzzle **grid** and has never bound furniture (its
#: History, 2026-10-17, which corrected CARD-222's reading of it and measured
#: the exemption that card wrote as vacuous). The floor the interior frame's
#: rules meet is the 2-device-pixel **dropout** floor CARD-222/CARD-225/
#: CARD-248 cite directly, applied inside ``interior_frame`` by
#: ``_pt_to_px_at_least``. Named here with its real authority, because this
#: card's own EC attributes it to R2 and R2 disclaims it.
FURNITURE_FLOOR_PX = 2


class TestPropertyTest_SheetFurniture_EveryFrameRuleMeetsTheFurnitureFloor:
    """EC(the furniture's stroke floor) over the corpus of trims and extents.

    Read **from the stream** — the width operand each rule was really stroked
    at, converted back to device pixels — and not off ink, which is CARD-299's
    re-expression of the two pixel-reading property tests this card's EC
    points at.

    The class is ``TestPropertyTest_…`` and not ``PropertyTest_…`` for the
    reason the module's other property class states: this repository
    configures no ``python_classes``, so a class named ``PropertyTest_…``
    collects **zero** tests with no skip and no warning.
    """

    def test_the_corpus_is_as_wide_as_it_claims(self, corpus: list[Case]) -> None:
        assert len(corpus) >= MIN_CASES, len(corpus)
        trims = {(case.layout.width, case.layout.height) for case in corpus}
        assert len(trims) >= 3, trims

    def test_every_frame_rule_meets_the_floor(self, corpus: list[Case]) -> None:
        seen = 0
        for case in corpus:
            scale = Decimal(POINTS_PER_INCH) / Decimal(case.layout.dpi)
            for mark in _furniture_only(case):
                if not isinstance(mark, Stroke) or mark.kind != "line":
                    continue
                seen += 1
                assert mark.width / scale >= FURNITURE_FLOOR_PX, (
                    case.label,
                    mark.width,
                )
        # The floor on the reading itself: 47 pages with two rules and 13 with
        # one is 107 rules, and a reading that found none would pass the loop
        # above trivially.
        assert seen == 107, seen

    def test_the_reading_would_see_a_sub_floor_rule(self, hero: Case) -> None:
        """Its control: the same reading on a frame whose rules are one pixel.

        A hairline of 1 device pixel is precisely the dropout the furniture
        floor exists to refuse, and ADR-0037's own 2026-10-17 entry records
        the one-pixel grey grid that 7 of 17 reviews of the 450-puzzle book
        complained about. Planted into the **frame** — the single source the
        writer reads — so what is shown is that the floor reading
        discriminates, not that a constant is still 2.
        """
        from dataclasses import replace

        thin = replace(
            hero.furniture,
            frame=replace(
                hero.furniture.frame,
                header_rule=replace(hero.furniture.frame.header_rule, width=1),
                footer_rule=replace(hero.furniture.frame.footer_rule, width=1),
            ),
            groups=(),
        )
        scale = Decimal(POINTS_PER_INCH) / Decimal(hero.layout.dpi)
        marks = _marks_of_stream(_stream_of(thin, hero.layout))
        rules = [m for m in marks if isinstance(m, Stroke) and m.kind == "line"]

        assert len(rules) == 2, rules
        assert all(mark.width / scale < FURNITURE_FLOOR_PX for mark in rules), rules


class TestSheetFurniture_TheTwoUpPageCarriesItToo:
    """A two-up slot *is* a puzzle page, so it gets the furniture as well.

    The page CARD-306's title is about: if the conversion card flipped the
    declaration while a two-up page had no folio, the printed book would ship
    pages with no number — and a two-up page is the book's dominant shape at
    small grid sizes.

    What differs from a single page, and each of it read: **no grid-size
    label** (two slots carry two sizes, so ``_draw_page_frame`` is passed
    ``None`` there and so is this), **two** QR groups rather than one, and
    their invitations in :func:`qr_group_caption`'s **named** form so a reader
    can tell which link is which.
    """

    @staticmethod
    def _page():
        generator = BookPDFGenerator(corpus_book())
        rows = [
            puzzle(f"card306-{index}", 10, 10, 2, "easy", f"Small {index}")
            for index in range(6)
        ]
        payloads = [BookPDFGenerator._payload(row) for row in rows]
        plans = [plan for plan in generator.puzzle_pages(payloads) if plan.is_two_up]
        assert plans, "six 10x10s pair up, which is what makes this page a pair"
        plan = plans[0]
        stream = generator.vector_two_up_page(
            plan, [payloads[number - 1] for number in plan.numbers]
        )
        return generator, plan, stream

    def test_the_pair_carries_one_folio_two_links_and_no_size_label(self) -> None:
        generator, plan, stream = self._page()
        frame = interior_frame(generator.page_spec(plan.page_number))
        marks = _marks_of_stream(stream)
        texts = [mark.text for mark in marks if isinstance(mark, Shown)]

        # One folio for the sheet, at the footer line's centre.
        assert texts.count(str(plan.page_number)) == 1, texts
        # Two groups, each naming its own puzzle (CARD-248's AC-3).
        for number in plan.numbers:
            assert qr_group_caption(number) in texts, (number, texts)
            assert qr_link(number) in texts, (number, texts)
        # No grid-size label: there is no one grid size on this page.
        assert not [
            text for text in texts if grid_size_label(10, 10) == text
        ], texts
        # Both frame rules, and the whole footer group with them.
        rows = [
            mark.numbers[1]
            for mark in marks
            if isinstance(mark, Stroke) and mark.kind == "line"
        ]
        height = Decimal(stream.height_px)
        for rule in (frame.header_rule, frame.footer_rule):
            assert _pt(height - rule.y, int(stream.dpi)) in rows, rule

    def test_the_two_groups_are_drawn_where_the_raster_pair_draws_them(self) -> None:
        """The insets are the pairing walk's, read through one definition.

        ``_two_up_qr_insets`` is the only thing that decides where a group
        sits, and both media read it — which is AC-3 on the one piece of
        furniture a two-up page places differently from a single page. Held
        here against the raster writer's own call on the same pair.
        """
        generator, plan, stream = self._page()
        pair = plan.pair
        placements = generator._two_up_qr_insets(pair, plan.numbers)
        marks = _marks_of_stream(stream)
        texts = {
            mark.text: mark.x for mark in marks if isinstance(mark, Shown)
        }

        assert len(placements) == len(plan.numbers) == 2, placements
        for number, inset in placements:
            caption = qr_caption(pair.lower, inset_px=inset)
            assert caption is not None
            pen = texts[qr_link(number)]
            # Right-aligned on an ODD page, left-aligned on an EVEN one: the
            # anchor is the caption's own x and the direction is its own flag,
            # so the pen is one advance in from it or exactly on it.
            anchor = _pt(Decimal(caption.x), int(stream.dpi))
            if caption.right_aligned:
                assert pen < anchor, (pen, anchor)
            else:
                assert pen == anchor, (pen, anchor)
