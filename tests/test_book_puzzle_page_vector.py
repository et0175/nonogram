"""The puzzle page drawn as PDF operators — CARD-295, ADR-0042/R1.

Every claim here is made against **the content stream of a written PDF**
(ADR-0042/R6) or against **poppler**, an engine that did not write it. No
claim is made by counting dark pixels, and the one place this module looks at
a raster is a deliberate positive control: the *raster* twin of the same page
really does carry an image XObject, which is what makes AC-1's reading
capable of failing.

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
from nonogram.export.layout import HeaderBand, Layout, compute_layout, header_band
from nonogram.export.png import INK
from tests.helpers import pdf_vector
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, puzzle

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
        oriented = [
            *((line, True) for line in self.layout.vertical_lines),
            *((line, False) for line in self.layout.horizontal_lines),
        ]
        marks: list[Mark] = []
        for line, vertical in sorted(oriented, key=lambda pair: pair[0].major):
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


# --------------------------------------------------------------------------
# Reading the marks back out of the written file
# --------------------------------------------------------------------------

_N = pdf_vector.NUMBER
_PATTERNS = {
    "grey": re.compile(rf"^({_N}) G$"),
    "fill": re.compile(rf"^({_N}) g$"),
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
        ).page(self.band, self.text, book_puzzle_vector.slot_room(self.layout))

    @property
    def found(self) -> list[Mark]:
        """The marks this page really emitted, read back out of a written PDF.

        Through :data:`_MARKS` when the page was written as part of a whole
        interior, and otherwise by writing a PDF of its own. The cache is not
        a convenience: writing one PDF per assertion is **slower than the ink
        assertion it replaces** — 29.17 ms against 20.58 ms, measured in
        ``meta/profiling/card-295-puzzle-page-price.md`` §3 — because
        ADR-0042/R5 Flate-compresses the whole 757 KB face once per *file*,
        and that one term is 98.8 % of a one-page write. Shared across an
        interior the same assertion costs 2.47 ms, which is 8.3x cheaper than
        the ink form. A module that measured that and then ignored it would be
        the first test file to make the phase's saving disappear.
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

    The shape §3 of the price document measures at 8.3x against the ink
    assertion, where a PDF per assertion measures at 0.71x.
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

    def test_the_raster_twin_of_the_same_page_does_carry_one(self) -> None:
        """The control: this reading can fail, and here is it failing.

        The same puzzle, the same page number, the same book — drawn the way
        the book draws it today and written by the generator's own
        ``_write_pdf``. If this page's resources did *not* name an XObject,
        every assertion in this class would be measuring nothing.
        """
        generator = BookPDFGenerator(corpus_book())
        row = print_order(baseline_puzzles())[0]
        payload = BookPDFGenerator._payload(row)
        page = generator._blank_page(payload, 1, A_PUZZLE_PAGE, generator.cell_sizes([payload]))
        raster = generator._write_pdf(iter([page]), 1, mode="L").getvalue()

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

    SLACK_PT = 0.05

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

        The tolerance is 0.05 pt — a fiftieth of a device pixel at 300 DPI —
        because poppler's box is the pen plus the face's advances and that is
        exactly what the writer centred on. It is not slack: a digit placed in
        the wrong cell is a whole cell out, two orders of magnitude above this.
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

    def test_the_band_fits_the_way_the_raster_page_fits_it(self) -> None:
        """One fitting rule in three places, held equal from here.

        ``book_puzzle_vector`` reimplements the two ratios natively rather
        than importing them across a module boundary (this package's standing
        convention), which is only safe while something holds the copies
        together. Three now, where
        ``test_a_two_up_band_is_fitted_by_the_exports_own_header_ratios``
        holds two.
        """
        assert book_puzzle_vector.BAND_WIDTH_RATIO == _BAND_WIDTH_RATIO
        assert book_puzzle_vector.MIN_BAND_FONT_RATIO == _MIN_BAND_FONT_RATIO
        assert book_puzzle_vector.BAND_WIDTH_RATIO == export_pdf._HEADER_WIDTH_RATIO
        assert book_puzzle_vector.MIN_BAND_FONT_RATIO == export_pdf._MIN_HEADER_FONT_RATIO

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

    def test_the_raster_twin_shows_more(self) -> None:
        """The other side of the same statement, measured not assumed.

        The raster page of the same puzzle carries a folio, a grid-size label
        and a QR caption. Named here so the gap is a number somebody can act
        on rather than a sentence in a docstring.
        """
        generator = BookPDFGenerator(corpus_book())
        row = print_order(baseline_puzzles())[0]
        payload = BookPDFGenerator._payload(row)
        page = generator._blank_page(
            payload, 1, A_PUZZLE_PAGE, generator.cell_sizes([payload])
        )

        from nonogram.export.layout import interior_frame

        frame = interior_frame(generator.page_spec(A_PUZZLE_PAGE))
        assert frame.header_rule.width > 0 and frame.footer_rule.width > 0
        assert page.size == (generator.page_width_px, generator.page_height_px)


class TestPuzzlePage_AgreesWithTheRasterTwin:
    """The two media put the grid in the same place, measured on the stream.

    Not a pixel comparison and not a claim about ink: the raster page's own
    geometry is the same ``Layout``, so what is held here is that the vector
    page uses it unchanged — every ruled line of the vector page is a line the
    raster renderer would stroke at the same device coordinates and the same
    width. It is the seam that makes the two halves of the suite comparable
    while CARD-298 has not yet chosen between them.
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
                case
            ), case.label


def _state_operators(case: Case) -> int:
    """How many ``G``/``w`` operators a page emits beside its marks.

    One ``G`` for the grid's tone, one ``w`` per distinct ruled width, and —
    where the drawing is framed — one ``G`` and one ``w`` for the frame. Stated
    as a derivation rather than as a number, so it moves with the page.
    """
    widths = {line.width for line in case.layout.grid_lines}
    return 1 + len(widths) + (2 if case.layout.frame is not None else 0)
