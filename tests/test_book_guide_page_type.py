"""The guide page's type, measured off the page it is printed on (CARD-149).

Interior page 1 of every book this project prints is the guide page, and until
this card it was lettered in **pixels**: ``ImageFont.truetype(Arial, 48)`` for
its title and ``28`` for its body, on a surface COMP-007 measures at 300 DPI.
A point is 1/72 in, so 300 DPI puts 4.167 px in a point: 28 px is **6.7 pt** of
body under an **11.5 pt** "title" — body text smaller than a legal footnote,
under a title set at ordinary body size. The audience for these books is the
one that complains about small print (EV-0003, a 2* review of a competitor:
"Very tiny squares. Not good for older people."), so the page that explains
how to play was the worst page in the book to set that small.

**Everything here is measured off rendered pixels.** A test that reads
``GUIDE_BODY_PT`` back and asserts it is 11.0 proves only that a constant
equals itself; it would have passed just as well when the constant was 28 px.
So this module imports no type size from
:mod:`nonogram.admin.book_pdf_generator`. It renders the page, finds the rows
that carry ink, measures a line's glyph box in pixels, and turns that box back
into points using the face's **own measured** ink-to-em ratio and the page's
resolution — the reverse of the conversion the page did, done by a second
implementation. The point sizes it expects (11 pt body, 22 pt title, 1.4x
leading) are written out here as the acceptance criteria state them.

Where the numbers come from, measured on this machine at 300 DPI:

* body 11 pt -> 46 px em; its tallest line's glyph box (cap to descender)
  measures 43 px, and 43 / 0.9275 = 46.4 px = 11.1 pt;
* title 22 pt -> 92 px em; "How to Use This Book" has no descender, so its box
  measures 67 px of cap height, and 67 / 0.730 = 91.8 px = 22.0 pt;
* the advance between body lines is 71 px = 17.0 pt, against the 50 px (12 pt)
  the method used to add — 46 px of type on a 50 px line.

AC-236, AC-237, AC-238 and AC-239 of CARD-149, one class each.
"""

from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin import book_pdf_generator
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator, page_frame

from tests.helpers.book_corpus import corpus_book

# --------------------------------------------------------------------------
# What the acceptance criteria ask for, written out rather than imported
# --------------------------------------------------------------------------

#: The guide page's body size, in points (AC-236). Ordinary book body size.
BODY_PT = 11.0

#: Its title's size, in points (AC-236).
TITLE_PT = 22.0

#: The least a line may advance, as a multiple of the body's point size
#: (AC-239). 1.4x of 11 pt is 15.4 pt; anything tighter sets the type into its
#: own neighbour.
MIN_LEADING_RATIO = 1.4

#: The resolution a book page is drawn at (``nonogram.export.layout.DPI``),
#: written out here so that the conversion this module does is its own.
BOOK_DPI = 300

#: Points in an inch, by definition.
POINTS_PER_INCH = 72.0

#: The two pixel sizes the method set before CARD-149, kept so that the
#: assertions below can be shown to separate them from the sizes it sets now.
#: 48 px is 11.5 pt and 28 px is 6.7 pt at :data:`BOOK_DPI`.
TITLE_PX_BEFORE = 48
BODY_PX_BEFORE = 28

#: The advance the method added between body lines before CARD-149, in pixels
#: — 12 pt, less than the 46 px of type it would have had to clear.
LEADING_PX_BEFORE = 50

#: The guide page's title **as it stands** (CARD-167 retitled it from "How to
#: Use This Book"; its "g" reaches a descender, which the ratio below measures
#: off the same string, so nothing else here changes). CARD-149 did not touch the
#: wording (it is copy, and out of scope), and the string is transcribed here
#: because a glyph box only says what size type is when you know which glyphs
#: were set: "How to Use This Book" reaches from cap height to the baseline
#: and no lower. A card that changes the wording re-derives it here — the
#: first test in :class:`TestGuidePage_TypeIsBookSized` fails loudly if the
#: page no longer says this, rather than quietly measuring the wrong ratio.
TITLE_AS_IT_STANDS = "How to Solve Nonograms"

#: A probe that reaches from cap height to the bottom of a descender, which is
#: the tallest ink an ordinary line of body text can make. The guide page's
#: longest lines ("  1. Fill in the grid based on the clues") carry both.
CAP_TO_DESCENDER_PROBE = "Hg"

#: The size the ink-to-em ratios are measured at: large enough that one pixel
#: of rasterisation is a rounding error in the third decimal.
RATIO_PROBE_PX = 400

#: The face the guide page letters in, by the path the page asks for.
ARIAL = "/System/Library/Fonts/Arial.ttf"

#: Anything darker than this is ink. The page is pure black on pure white, so
#: the threshold only has to fall between them and clear the anti-aliasing.
INK_THRESHOLD = 128


# --------------------------------------------------------------------------
# Measuring a rendered page
# --------------------------------------------------------------------------


def face(size_px: int) -> ImageFont.ImageFont:
    """The face the guide page letters in, asked for at ``size_px``.

    The same two calls the page makes, reimplemented rather than imported
    (CLAUDE.md: prefer an independent second implementation). On a machine
    with no Arial both the page and this fall back to Pillow's own face at the
    same size, so the ratios measured here are the ratios of whatever face the
    page was actually drawn in.
    """
    try:
        return ImageFont.truetype(ARIAL, size_px)
    except OSError:  # pragma: no cover - only on a machine without Arial
        try:
            return ImageFont.load_default(size_px)
        except TypeError:  # pragma: no cover - Pillow < 10.1
            return ImageFont.load_default()


def ink_rows(page: Image.Image) -> np.ndarray:
    """The 0-based rows of ``page`` that carry ink, in order."""
    dark = np.asarray(page.convert("L")) < INK_THRESHOLD
    return np.flatnonzero(dark.any(axis=1))


def ink_bands(page: Image.Image) -> List[Tuple[int, int]]:
    """``(top, bottom)`` of each run of inked rows — one per drawn line.

    A line of type is a band of inked rows with white above and below it, so
    on a page of text set on leading that clears its type the bands *are* the
    lines: the first is the title, the rest are the body in order. Two lines
    whose ink touched would merge into one band, which is why AC-239 counts
    them.
    """
    bands: List[Tuple[int, int]] = []
    start = previous = None
    for row in ink_rows(page):
        row = int(row)
        if start is None:
            start = row
        elif row != previous + 1:
            bands.append((start, previous))
            start = row
        previous = row
    if start is not None:
        bands.append((start, previous))
    return bands


#: A row whose ink runs unbroken for longer than this many pixels is a ruled
#: line, not type: no glyph of the guide page's faces is this wide, and a
#: ruled line of the worked example is the width of its drawing.
RULE_RUN_PX = 300


def longest_run(row: np.ndarray) -> int:
    """The longest unbroken run of ``True`` in a boolean row."""
    padded = np.concatenate(([False], row, [False])).astype(np.int8)
    edges = np.flatnonzero(np.diff(padded))
    return int((edges[1::2] - edges[0::2]).max()) if edges.size else 0


def type_bands(page: Image.Image) -> List[Tuple[int, int]]:
    """:func:`ink_bands` without the drawn ones — the bands that are type.

    Since CARD-167 the guide page also carries the worked example's ruled
    lines, each a band of ink taller than a line of body text. A band with a
    ruled row in it (an unbroken run longer than :data:`RULE_RUN_PX`) is one of
    those drawings, and every other band is a line of type, measured as
    before.
    """
    dark = np.asarray(page.convert("L")) < INK_THRESHOLD
    return [
        (top, bottom)
        for top, bottom in ink_bands(page)
        if max(longest_run(dark[row]) for row in range(top, bottom + 1)) <= RULE_RUN_PX
    ]


def ink_box(page: Image.Image) -> Tuple[int, int, int, int]:
    """``(left, top, right, bottom)`` of every mark on ``page``, inclusive."""
    dark = np.asarray(page.convert("L")) < INK_THRESHOLD
    rows = np.flatnonzero(dark.any(axis=1))
    columns = np.flatnonzero(dark.any(axis=0))
    assert rows.size and columns.size, "the page is blank"
    return int(columns[0]), int(rows[0]), int(columns[-1]), int(rows[-1])


def probe_box(text: str, size_px: int) -> Tuple[int, int]:
    """The ``(width, height)`` of ``text``'s ink at ``size_px``, in pixels.

    Drawn on its own scratch image and measured the same way a page is, so a
    box measured here and a box measured off a page are the same measurement.
    """
    scratch = Image.new("RGB", (size_px * 40 + 40, size_px * 4), "white")
    ImageDraw.Draw(scratch).text(
        (20, size_px), text, fill="black", font=face(size_px)
    )
    left, top, right, bottom = ink_box(scratch)
    return right - left + 1, bottom - top + 1


def ink_to_em(text: str) -> float:
    """How much of the em ``text``'s ink fills vertically, in this face.

    Measured, not tabulated: ``text`` is set at :data:`RATIO_PROBE_PX` and its
    box divided by that em. Arial gives 0.9275 for cap-to-descender and 0.730
    for the title's cap height; a different face gives its own, which is the
    point — the ratio has to belong to the face the page was drawn in for
    :func:`measured_points` to be a measurement of that page.
    """
    _, height = probe_box(text, RATIO_PROBE_PX)
    return height / RATIO_PROBE_PX


def measured_points(box_height_px: int, text: str, dpi: int) -> float:
    """The point size of type whose ink for ``text`` measures ``box_height_px``.

    The reverse of what the page did, by a second route: divide the measured
    glyph box by the face's own ink-to-em ratio for the same glyphs to recover
    the em in device pixels, then turn those pixels into points at the
    resolution the page was drawn at. Nothing here reads a size off the page's
    font object or off a constant in the module under test.
    """
    em_px = box_height_px / ink_to_em(text)
    return em_px * POINTS_PER_INCH / dpi


def px_to_points(pixels: float, dpi: int) -> float:
    """``pixels`` on a surface at ``dpi``, as points."""
    return pixels * POINTS_PER_INCH / dpi


def points_to_px(points: float, dpi: int) -> int:
    """``points`` as the whole pixels a surface at ``dpi`` needs."""
    return round(points * dpi / POINTS_PER_INCH)


# --------------------------------------------------------------------------
# The books these pages are drawn on
# --------------------------------------------------------------------------

#: CON-018's Book 1 margins, as the ``books`` table stores them: the 0.5 in
#: gutter and 0.375 in outside margin, in centimetres to two places.
GUTTER_CM = "1.27"
OUTSIDE_CM = "0.95"

#: The smallest trim a book may be stored with
#: (``book_page_spec.MIN_TRIM_CM``), written out rather than imported.
MIN_TRIM_CM = 10.0

#: And the largest (``MAX_TRIM_WIDTH_CM`` x ``MAX_TRIM_HEIGHT_CM``).
MAX_TRIM_WIDTH_CM = 30.0
MAX_TRIM_HEIGHT_CM = 48.0


def book_on(width_cm: float, height_cm: float, book_id: str = "card-149") -> Book:
    """A book on CON-018's margins at an arbitrary trim."""
    return Book(
        book_id=book_id,
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-149's type tests draw.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{width_cm:.2f}",
        trim_height_cm=f"{height_cm:.2f}",
        gutter_margin_cm=GUTTER_CM,
        outside_margin_cm=OUTSIDE_CM,
    )


#: The counts the guide page prints into its text, and the reason the text's
#: length varies at all: a book of 4 puzzles and a book of 999,999 set
#: different numbers of digits. Seeded ``random.Random`` per CLAUDE.md — no
#: ``hypothesis`` — and the corpus asserts its own size inside the test that
#: uses it, so it cannot silently shrink.
CORPUS_SEED = 149
CORPUS_CASES = 48


def count_and_trim_corpus() -> List[Dict[str, object]]:
    """Books and puzzle counts to draw a guide page for.

    Every trim from the smallest a book may be stored at to the largest, on
    the profile's margins, crossed with counts from a four-puzzle book to a
    six-digit one. The first case is pinned to the smallest trim and the
    largest counts — the worst case, which a random draw might not happen to
    include.
    """
    source = random.Random(CORPUS_SEED)
    cases: List[Dict[str, object]] = [
        {
            "width_cm": MIN_TRIM_CM,
            "height_cm": MIN_TRIM_CM,
            "counts": (999_999, 333_333, 333_333, 333_333),
        }
    ]
    while len(cases) < CORPUS_CASES:
        easy = source.randint(0, 400_000)
        medium = source.randint(0, 400_000)
        hard = source.randint(0, 400_000)
        cases.append(
            {
                "width_cm": round(source.uniform(MIN_TRIM_CM, MAX_TRIM_WIDTH_CM), 2),
                "height_cm": round(source.uniform(MIN_TRIM_CM, MAX_TRIM_HEIGHT_CM), 2),
                "counts": (easy + medium + hard, easy, medium, hard),
            }
        )
    return cases


@pytest.fixture(scope="module")
def book1_generator() -> BookPDFGenerator:
    """The generator for the book this project ships (CON-018's Book 1)."""
    return BookPDFGenerator(corpus_book())


@pytest.fixture(scope="module")
def book1_frame(book1_generator) -> object:
    """Interior page 1's trim and usable area, as COMP-007 reports it."""
    return page_frame(book1_generator.page_spec(1))


@pytest.fixture(scope="module")
def guide_page(book1_generator) -> Image.Image:
    """The guide page of a four-puzzle book, rendered."""
    return book1_generator.create_guide_page(4, 2, 1, 1)


@pytest.fixture(scope="module")
def guide_bands(guide_page) -> List[Tuple[int, int]]:
    """Its lines of type: the title first, then one per body line."""
    bands = type_bands(guide_page)
    assert len(bands) >= 9, (
        "the guide page draws a title and eight or more body lines; only "
        f"{len(bands)} bands of ink were found, so either the page's text "
        "shrank or two lines' ink ran together"
    )
    return bands


class TestGuidePage_TypeIsBookSized:
    """AC-236 — 11 pt body, 22 pt title, measured off the rendered glyphs.

    The measurement is the whole point of this class. Each test renders the
    page, finds a line's glyph box in pixels and converts that box back into
    points; none of them reads a size from the module under test. Two of them
    also check the box against what the pre-CARD-149 pixel sizes would have
    measured, so the assertions can be seen to separate 11 pt from 6.7 pt
    rather than accepting anything.
    """

    def test_the_titles_glyph_box_is_the_box_of_22pt_type(self, guide_page, guide_bands):
        """The title's ink is exactly the ink of the title set at 22 pt.

        Both boxes are measured the same way — the page's off the page, the
        reference's off a scratch image — so they are comparable to the pixel.
        This is also what keeps :data:`TITLE_AS_IT_STANDS` honest: if the
        page's wording changes, the reference no longer matches and this test
        says so instead of the ratio tests quietly measuring glyphs that are
        not there.
        """
        top, bottom = guide_bands[0]
        left, _, right, _ = ink_box(guide_page.crop((0, top, guide_page.width, bottom + 1)))
        measured = (right - left + 1, bottom - top + 1)

        expected = probe_box(TITLE_AS_IT_STANDS, points_to_px(TITLE_PT, BOOK_DPI))
        assert measured == expected, (
            f"the title's glyph box is {measured} px, and {TITLE_PT} pt at "
            f"{BOOK_DPI} DPI measures {expected} px"
        )

        before = probe_box(TITLE_AS_IT_STANDS, TITLE_PX_BEFORE)
        assert measured != before, (
            "the title still measures what it measured at "
            f"{TITLE_PX_BEFORE} px ({before} px), which is "
            f"{px_to_points(TITLE_PX_BEFORE, BOOK_DPI):.1f} pt"
        )

    def test_the_titles_measured_point_size_is_22(self, guide_bands):
        """22 pt, recovered from the height of the title's ink."""
        top, bottom = guide_bands[0]
        measured = measured_points(bottom - top + 1, TITLE_AS_IT_STANDS, BOOK_DPI)
        assert measured == pytest.approx(TITLE_PT, abs=0.4), (
            f"the title measures {measured:.2f} pt on the page, not {TITLE_PT} pt"
        )

    def test_the_bodys_measured_point_size_is_11(self, guide_bands):
        """11 pt, recovered from the tallest body line's ink.

        The tallest body line is the one that reaches from a cap (or a digit)
        down to a descender, which is the same extent
        :data:`CAP_TO_DESCENDER_PROBE` has — "  1. Fill in the grid based on
        the clues" is such a line, and the page draws several.
        """
        tallest = max(bottom - top + 1 for top, bottom in guide_bands[1:])
        measured = measured_points(tallest, CAP_TO_DESCENDER_PROBE, BOOK_DPI)
        assert measured == pytest.approx(BODY_PT, abs=0.4), (
            f"the body measures {measured:.2f} pt on the page, not {BODY_PT} pt; "
            f"its tallest line's glyph box is {tallest} px"
        )

        em_px = tallest / ink_to_em(CAP_TO_DESCENDER_PROBE)
        assert em_px == pytest.approx(points_to_px(BODY_PT, BOOK_DPI), abs=1.5), (
            f"the body's em measures {em_px:.1f} px, and {BODY_PT} pt at "
            f"{BOOK_DPI} DPI is {points_to_px(BODY_PT, BOOK_DPI)} px "
            f"(it was {BODY_PX_BEFORE} px = "
            f"{px_to_points(BODY_PX_BEFORE, BOOK_DPI):.1f} pt before CARD-149)"
        )

    def test_the_title_is_the_largest_type_on_the_page(self, guide_bands):
        """The title reads as a title: no body line's ink is as tall as it.

        The defect this card fixes was not only that the body was small. The
        "title" was set at 48 px against 28 px of body — 1.7x, which on a page
        is a bold line of body text. At 22 pt against 11 pt the title's cap
        height alone (67 px) clears the body's whole cap-to-descender extent
        (43 px).
        """
        title_height = guide_bands[0][1] - guide_bands[0][0] + 1
        tallest_body = max(bottom - top + 1 for top, bottom in guide_bands[1:])
        assert title_height > tallest_body, (
            f"the title's ink is {title_height} px and a body line's is "
            f"{tallest_body} px, so the title does not read as one"
        )


class TestGuidePage_TextFitsTheUsableFrame:
    """AC-237 — the longest text the book ships fits inside the frame.

    Bigger type is only a fix if it still fits. Since CARD-167 the page wraps
    its text at spaces to the usable measure and is set in the first of three
    forms (full text; the worked example with full captions; the example with
    short labels) whose last mark sits above the bottom margin. Neither the
    wrapping nor the choice of form is trusted here: "it fits" is measured on
    the page — every mark inside the usable area COMP-007 reported, and the
    last mark above the bottom margin — on Book 1, on the 10 cm minimum trim,
    and across the corpus of trims and counts below.
    """

    def test_every_mark_sits_inside_the_usable_area(self, book1_generator, book1_frame):
        """On the book this project ships, with the largest counts it prints."""
        page = book1_generator.create_guide_page(999_999, 333_333, 333_333, 333_333)
        left, top, right, bottom = ink_box(page)
        assert left >= book1_frame.left, f"ink at x={left}, margin at {book1_frame.left}"
        assert right <= book1_frame.right, f"ink at x={right}, margin at {book1_frame.right}"
        assert top >= book1_frame.top, f"ink at y={top}, margin at {book1_frame.top}"
        assert bottom <= book1_frame.bottom, (
            f"the last line's ink reaches y={bottom} and the bottom margin is "
            f"at {book1_frame.bottom}"
        )

    def test_it_fits_the_smallest_trim_a_book_may_be_stored_at(self):
        """A 10x10 cm book on the profile's margins — the narrowest measure."""
        generator = BookPDFGenerator(book_on(MIN_TRIM_CM, MIN_TRIM_CM))
        frame = page_frame(generator.page_spec(1))
        page = generator.create_guide_page(999_999, 333_333, 333_333, 333_333)
        left, top, right, bottom = ink_box(page)
        assert (left, top) >= (frame.left, frame.top)
        assert right <= frame.right, (
            f"the longest line reaches x={right} of a measure that ends at "
            f"{frame.right} on a {MIN_TRIM_CM} cm trim"
        )
        assert bottom <= frame.bottom

    def test_the_whole_corpus_of_trims_and_counts_fits(self):
        """Every trim a book may be stored at, with counts from 4 to 999,999."""
        corpus = count_and_trim_corpus()
        # Both bounds are load-bearing: the builder sizes the corpus from
        # CORPUS_CASES, so the first bound alone would hold at any value. The
        # second pins the constant against a literal, so lowering CORPUS_CASES
        # is what fails -- the same double bound as
        # tests/test_books_list_plan_stats.py's corpus floor.
        assert len(corpus) >= CORPUS_CASES >= 48, (
            f"the corpus is {len(corpus)} cases at CORPUS_CASES={CORPUS_CASES} "
            f"and must be at least 48"
        )
        for case in corpus:
            generator = BookPDFGenerator(
                book_on(float(case["width_cm"]), float(case["height_cm"]))
            )
            frame = page_frame(generator.page_spec(1))
            page = generator.create_guide_page(*case["counts"])
            left, top, right, bottom = ink_box(page)
            where = (
                f"{case['width_cm']}x{case['height_cm']} cm, counts "
                f"{case['counts']}"
            )
            assert left >= frame.left, f"{where}: ink at x={left} < {frame.left}"
            assert right <= frame.right, f"{where}: ink at x={right} > {frame.right}"
            assert top >= frame.top, f"{where}: ink at y={top} < {frame.top}"
            assert bottom <= frame.bottom, f"{where}: ink at y={bottom} > {frame.bottom}"


class TestGuidePage_PointSizeIsIndependentOfDpi:
    """AC-238 — the same size in points on pages of two different resolutions.

    This is the test that pins the fix rather than its numbers. 46 px is
    11 pt only on a 300 DPI page; the defect was that the method named pixels,
    so a book rendered at another resolution would have printed the same page
    at another size without a line of code changing.

    **Where a page's resolution comes from here.** A
    :class:`~nonogram.export.layout.PageSpec` states the sheet in millimetres
    and carries no DPI of its own: the resolution that turns those millimetres
    into a page's pixels is ``nonogram.export.layout.DPI``, and it reaches this
    method as :attr:`BookPDFGenerator.dpi`, taken at construction. So that is
    what these tests vary — the resolution the page's type is measured
    against, which is the half of "a page spec at a different DPI" this card
    owns. The frame itself is COMP-007's and G-3 forbids this card from
    touching it.
    """

    @staticmethod
    def generator_at(dpi: int, monkeypatch) -> BookPDFGenerator:
        """A generator whose pages are drawn at ``dpi``."""
        monkeypatch.setattr(book_pdf_generator, "DPI", dpi)
        generator = BookPDFGenerator(corpus_book())
        assert generator.dpi == dpi
        return generator

    def measure(self, dpi: int, monkeypatch) -> Dict[str, float]:
        """The point sizes and glyph boxes of a guide page drawn at ``dpi``."""
        page = self.generator_at(dpi, monkeypatch).create_guide_page(4, 2, 1, 1)
        bands = type_bands(page)
        assert len(bands) >= 9, f"only {len(bands)} lines of ink at {dpi} DPI"
        title_px = bands[0][1] - bands[0][0] + 1
        body_px = max(bottom - top + 1 for top, bottom in bands[1:])
        return {
            "title_px": title_px,
            "body_px": body_px,
            "title_pt": measured_points(title_px, TITLE_AS_IT_STANDS, dpi),
            "body_pt": measured_points(body_px, CAP_TO_DESCENDER_PROBE, dpi),
        }

    def test_300_and_600_dpi_print_the_same_point_size(self, monkeypatch):
        """Twice the pixels, the same type."""
        at_300 = self.measure(300, monkeypatch)
        at_600 = self.measure(600, monkeypatch)

        assert at_600["title_pt"] == pytest.approx(at_300["title_pt"], abs=0.25), (
            f"the title measures {at_300['title_pt']:.2f} pt at 300 DPI and "
            f"{at_600['title_pt']:.2f} pt at 600 DPI"
        )
        assert at_600["body_pt"] == pytest.approx(at_300["body_pt"], abs=0.25), (
            f"the body measures {at_300['body_pt']:.2f} pt at 300 DPI and "
            f"{at_600['body_pt']:.2f} pt at 600 DPI"
        )
        for dpi, measured in ((300, at_300), (600, at_600)):
            assert measured["body_pt"] == pytest.approx(BODY_PT, abs=0.4), (
                f"{dpi} DPI: body {measured['body_pt']:.2f} pt"
            )
            assert measured["title_pt"] == pytest.approx(TITLE_PT, abs=0.4), (
                f"{dpi} DPI: title {measured['title_pt']:.2f} pt"
            )

    def test_the_pixels_do_change_with_the_resolution(self, monkeypatch):
        """And the page really was drawn twice, at two resolutions.

        Without this, the test above could be satisfied by a method that
        ignored the page's resolution entirely and drew the same pixels twice:
        the conversion back into points would then differ by 2x and the
        comparison would fail — but only for the reason that the *measurement*
        divided by the right number, which is easy to misread. So the glyph
        box in pixels is asserted to double as well.
        """
        at_300 = self.measure(300, monkeypatch)
        at_600 = self.measure(600, monkeypatch)
        for key in ("title_px", "body_px"):
            ratio = at_600[key] / at_300[key]
            assert 1.9 <= ratio <= 2.1, (
                f"{key} went from {at_300[key]} px at 300 DPI to "
                f"{at_600[key]} px at 600 DPI ({ratio:.2f}x)"
            )


class TestGuidePage_LeadingClearsTheType:
    """AC-239 — consecutive lines sit at least 1.4x the body size apart.

    46 px of type on the 50 px advance the method used to add would have set
    each line 4 px clear of the next, which on a printed page is one block of
    grey. The leading has to be stated with the type, and the page has to be
    measured to show that it was: every line's ink separated from its
    neighbour's, and the advance itself at least 1.4x the body's point size.
    """

    def test_consecutive_lines_advance_by_at_least_1_4_of_the_body(self, guide_bands):
        """Measured top to top, over the body's own lines.

        The body's lines are all set in one size, so the distance from one
        band's top to the next's *is* the advance between their baselines, to
        within the pixel or two by which one line's first glyph may be a cap
        and the next's an x-height letter. Blank lines in the page's text show
        up as a doubled advance, so the smallest gap is the advance itself.
        """
        tops = [top for top, _ in guide_bands[1:]]
        assert len(tops) >= 8, f"only {len(tops)} body lines"
        gaps = [later - earlier for earlier, later in zip(tops, tops[1:])]
        smallest = min(gaps)
        floor_pt = MIN_LEADING_RATIO * BODY_PT
        measured_pt = px_to_points(smallest, BOOK_DPI)
        assert measured_pt >= floor_pt, (
            f"the tightest advance on the page is {smallest} px = "
            f"{measured_pt:.2f} pt, and {MIN_LEADING_RATIO}x of {BODY_PT} pt "
            f"is {floor_pt:.2f} pt"
        )
        assert smallest > LEADING_PX_BEFORE, (
            f"the advance is still {smallest} px, the pre-CARD-149 "
            f"{LEADING_PX_BEFORE} px = "
            f"{px_to_points(LEADING_PX_BEFORE, BOOK_DPI):.1f} pt"
        )

    def test_no_two_lines_ink_runs_together(self, guide_page, guide_bands):
        """Every line has white above and below it, the title included.

        :func:`ink_bands` starts a new band only after a blank row, so bands
        are separated by construction and comparing neighbouring bands proves
        nothing. What does is the count: two lines whose ink touches come out
        as one band, so the page has fewer bands than it has lines. The counts
        are pinned for the four-puzzle Book 1 page (the full form, CARD-167),
        written out rather than derived from the generator's text:

        * 14 lines of type — the title; the explanation (2 lines); the four
          count lines; "Worked example: ..."; the four step captions (1, 1, 2
          and 1 lines); the closing line;
        * 4 drawings — one per step of the worked example, each the same
          one-row line, so all four bands are the same height.

        A caption touching its drawing merges into the drawing's band: the
        type count drops to 13 and that drawing's band grows taller than the
        other three. Two lines of type touching drop the type count.
        """
        every_band = ink_bands(guide_page)
        drawings = [band for band in every_band if band not in guide_bands]
        assert len(guide_bands) == 14, (
            f"{len(guide_bands)} lines of type found where the page sets 14: "
            "a line was lost, or two lines' ink ran together"
        )
        assert len(drawings) == 4, (
            f"{len(drawings)} drawn bands found where the worked example "
            "draws 4"
        )
        heights = {bottom - top + 1 for top, bottom in drawings}
        assert len(heights) == 1, (
            f"the worked example's four lines are {sorted(heights)} px tall: "
            "one has merged with the ink next to it"
        )
