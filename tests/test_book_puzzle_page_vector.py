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
    BookPDFGenerator,
    band_identity,
    example_line_layout,
    guide_icon_layout,
    print_order,
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
    GridLine,
    HeaderBand,
    Layout,
    compute_layout,
    header_band,
)
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
                Stroke("line", numbers, self._x(line.width), self.grey)
            )
        return marks

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
                self._x(frame.width),
                self.grey,
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

    A **fill** tone is one of those, and deliberately: a bare ``N g`` —
    ``ContentStream.fill_grey``'s own spelling — matches nothing below and
    raises. :data:`_PATTERNS` carried a ``"fill"`` entry until cycle 1's
    F-008 noticed the if-chain never consulted it, so the table described a
    classification that did not happen while the refusal that did happen was
    invisible. The entry is gone and the refusal is the behaviour: a filled
    shape on an interior page is a page nothing here can speak for. (The
    ``g`` that *is* read is the one inside a text object, where it is the
    glyphs' tone.)
    """
    width: Decimal | None = None
    grey: Decimal | None = None
    marks: list[Mark] = []
    for row in stream_text.splitlines():
        if not row.strip():
            continue
        if match := _PATTERNS["grey"].match(row):
            grey = Decimal(match.group(1))
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

    @property
    def expected(self) -> list[Mark]:
        return Expected(
            self.layout, Decimal(str(book_vector_draw.INK_GREY)), interior_face_metrics()
        ).page(self.band, self.text, _slot_room(self.layout))

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
    for mark in case.found:
        if not isinstance(mark, Stroke) or mark.kind != "line":
            continue
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

        The page sets a tone, a width, lines, one box and text, and the set
        below is the whole of it. An image's ``Do`` fails this, and so does
        anything else a later edit reaches for.
        """
        (written,) = pdf_vector.content_streams(
            write_vector_pdf([hero.stream], 1).getvalue()
        )
        tally = pdf_vector.operator_tally(written)

        assert set(tally) == {"G", "w", "m", "l", "S", "re", "g", "BT", "Tf", "Td", "Tj", "ET"}
        assert tally["m"] == tally["l"] == tally["S"] - tally["re"]

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
        raster = twin.generator._write_pdf(iter([twin.page]), 1, mode="L").getvalue()

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
                _replace_line(line, width=0) for line in case.layout.vertical_lines
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

    def test_the_tone_is_the_raster_renderers_own_ink(self, corpus: list[Case]) -> None:
        """One ink across the two media, derived from one constant.

        The ``Layout`` states no tone at all — every mark on an interior page
        is ``png.INK`` today — so ADR-0042/R3's "every tone comes from the
        Layout" cannot be satisfied literally. What is held instead is that
        the vector page's tone is the *same constant* the raster page draws
        with, converted. The card that gives tone a home is CARD-227.
        """
        assert book_vector_draw.INK_GREY == INK[0] / 255
        greys = {mark.grey for case in corpus for mark in case.found}
        assert greys == {Decimal(str(book_vector_draw.INK_GREY))}


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
        assert sorted(found) == sorted(expected + hero.text.split()), (
            len(found),
            len(expected),
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
    the QR caption — is **not drawn**, and that no card in the ADR-0042 phase
    draws it. A declaration that outlives its hole is the defect this board
    gates on most, so it is checked rather than written: the page is the
    drawing and the band, and the day somebody adds the folio this test is
    what tells them to delete the paragraph.
    """

    def test_the_page_shows_only_the_clue_digits_and_the_band(self, hero: Case) -> None:
        shown = [mark.text for mark in hero.found if isinstance(mark, Shown)]
        expected = [str(entry.value) for entry in hero.layout.clue_entries]

        assert sorted(shown) == sorted(expected + [hero.text])

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
        strokes = [mark for mark in hero.found if isinstance(mark, Stroke)]
        lines = [mark for mark in strokes if mark.kind == "line"]

        assert len(lines) == len(hero.layout.vertical_lines) + len(
            hero.layout.horizontal_lines
        )
        widths = {mark.width / scale for mark in lines}
        assert widths == {
            Decimal(hero.layout.thin_rule),
            Decimal(hero.layout.thick_rule),
        }, widths

    def test_the_thin_rules_are_stroked_before_the_heavy_ones(
        self, hero: Case
    ) -> None:
        """The ordering claim, which is the one a set comparison cannot make."""
        scale = Decimal(POINTS_PER_INCH) / Decimal(hero.layout.dpi)
        thin = Decimal(hero.layout.thin_rule) * scale
        order = [
            mark.width == thin for mark in hero.found if isinstance(mark, Stroke)
        ]
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

    def test_the_ink_measures_the_two_widths_the_stream_sets(self, twin: Twin) -> None:
        """The weighted half: the claim arm's own cross-medium check, run.

        ``[3, 6]`` device pixels off the page against ``[0.72, 1.44]`` points
        off the stream — the same two rules, which is the comparison
        ``card295_puzzle_page_price.py`` makes before it times either arm. The
        widths are asserted to be two and ordered first, so the comparison
        cannot pass by both sides collapsing to one weight.
        """
        verticals, horizontals = _device_rules(twin.case)
        stated = sorted({width for _position, width in verticals + horizontals})
        inked = _inked_rule_widths(twin)

        assert len(stated) == 2 and stated[1] > stated[0], stated
        assert [Decimal(width) for width in inked] == stated, (inked, stated)


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
            assert len(case.stream.operators) == len(case.expected) + _state_operators(
                case.layout
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
        striped = _replace_layout(
            case.layout,
            vertical_lines=tuple(
                _replace_line(line, width=1 if index % 2 else 5)
                for index, line in enumerate(case.layout.vertical_lines)
            ),
        )
        stream = book_puzzle_vector.puzzle_page_stream(
            striped, case.band, case.text, 10_000
        )
        expected = Expected(
            striped, Decimal(str(book_vector_draw.INK_GREY)), interior_face_metrics()
        ).page(case.band, case.text, 10_000)

        naive = 1 + len({line.width for line in striped.grid_lines})
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


def _state_operators(layout: Layout) -> int:
    """How many ``G``/``w`` operators a page emits beside its marks.

    One ``G`` for the grid's tone, one ``w`` **per change of width along the
    stroke order**, and — where the drawing is framed — one ``G`` and one
    ``w`` for the frame.

    The middle term used to be ``len({widths})``, which is the same number
    only while equal widths are contiguous after the sort — true of every
    page the corpus holds (two widths, thin then major) and false in general.
    Cycle 1's F-009 built a ``Layout`` whose non-major verticals alternate
    1, 5, 1, 5 px: ``draw_grid_lines`` sets the width on change, so it emitted
    16 ``w`` operators and still agreed with the oracle exactly, while the
    old derivation predicted 7. It now counts the changes
    ``draw_grid_lines`` makes, over the one stroke order
    :func:`_in_stroke_order` states, so it moves with any page rather than
    with a two-width one.
    """
    widths = [line.width for line, _vertical in _in_stroke_order(layout)]
    changes = sum(
        1 for before, after in zip([None, *widths], widths) if before != after
    )
    return 1 + changes + (2 if layout.frame is not None else 0)
