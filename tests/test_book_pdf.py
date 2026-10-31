"""CARD-116 — the book PDF on its own trim (FR-030, FR-032, FR-043, ADR-0036).

    AC-175  TestBookPdf_CellSizedForBookTrimNotA4
    AC-176  TestBookPdf_CellFollowsStoredTrim
    AC-177  TestBookPdf_PageSizeEqualsStoredTrim
    AC-178  TestBookPdf_EmptyMarginsFallBackToBook1Profile
    AC-189  TestBookPdf_WideGridPrintsOnPortraitPage
    AC-366/AC-367  TestBookPdf_PuzzleTopEdgeFloatsWithTheSpare
                   (replaces AC-190's TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage,
                    retired with AC-190 on 2026-10-17 — CARD-224)
    AC-240  TestBookPdf_WideGridPrintsUprightNeverRotated
    AC-274  TestBookPdf_DrawingCentredOnRightHandPage
    AC-275  TestBookPdf_DrawingCentredOnLeftHandPage
    AC-276  TestBookPdf_ParityNeverMovesTopEdge
    AC-287  TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1
            (re-measured 2026-10-17 for CARD-206: interior page 6, left-hand)
    CARD-330's own four classes carry no AC of this card's: TestEdgeOffset_*,
            which measure where the raster and the vector media put the same
            grid against a position derived from the page spec, and pin this
            module's placed-edge expectations to the medium they were measured
            in. See :data:`EDGE_TOLERANCE_MM`.

Since CARD-128 the interior opens each non-empty level with a divider page,
since CARD-200 a table-of-contents page (or pages) sits between the guide and
that divider, and since CARD-206 the interior opens with a blank title /
copyright page, so a one-level, small book (every book below is far under one
TOC page's own capacity, so this is always exactly one page) runs the blank
title page 1 (CARD-206), the 2-page
guide (CARD-201), the 1-page table of contents (CARD-200), divider page 5, and
its puzzles from interior page 6 (AC-287 — before CARD-201 the guide was one
page and puzzles started at interior page 3; before CARD-200 the TOC did not
exist and puzzles started at interior page 4; before CARD-206 they started at
interior page 5 — each card's own front-matter
addition shifts every later page by one, and flips its parity). Every page
index below counts those pages through :data:`FIRST_PUZZLE_PAGE`; what the
dividers say and where they go is
``tests/test_book_pdf_levels.py``'s.

Every number asserted here is measured off the **page**, by
``tests/helpers/page_ink.py``, and compared against a figure worked out in
this module in millimetres from CON-018's profile and FR-030's definition of
page fit. Neither side of that comparison calls ``compute_layout`` or
``book_page_spec``, so the two are independent (CLAUDE.md).

The pages come from ``BookPDFGenerator(book).interior_pages(...)`` — the
interior in print order, ``pages[n - 1]`` being interior page ``n`` — except
where an AC is about the PDF **file**, which is read back with Pillow's own
parser (``tests/helpers/pdf_pages.py``, and ``page_ink.pdf_page_boxes`` for
the MediaBox a printer measures).

AC-176 and AC-177 are about the trim a book is **stored** on, and since
CARD-136 the admin panel's Print setup step is how a trim gets there. Their
books are therefore not hand-built: the trim is typed into the real form and
saved through the real route (``print_setup`` below), and the export is built
from the :class:`Book` that comes back out of storage. A hand-built Book would
satisfy both criteria on columns no screen had ever written — which is exactly
the state the product was in until CARD-136.

The last two classes carry no AC. They pin the module's **failure contract**
— what a puzzle that will not render does to the pages of the ones around it
— which is the contract the payload-first pass in ``interior_pages`` exists
to keep. See their own docstrings for what they are and are not evidence of.
"""

from __future__ import annotations

import ast
import pathlib
import random
import re
from dataclasses import dataclass
from importlib import resources

import numpy as np
import pytest
from PIL import Image

from nonogram import clues
from nonogram.admin import book_vector
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    _RASTER_DECLARATIONS,
    GUIDE_PAGE_COUNT,
    TITLE_PAGE_COUNT,
    BookPDFGenerator,
    DividerPagePlan,
    PageKind,
    PageMedium,
    PuzzlePagePlan,
    RasterDeclaration,
    page_frame,
    page_medium,
    puzzle_page_plan,
)
from nonogram.export import pdf as export_pdf
from nonogram.export.layout import DEFAULT_PAGE_SPEC
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests import full_suite_lock
from tests.helpers import pdf_vector
from tests.helpers.page_ink import drawing_of, pdf_page_boxes
from tests.helpers.pdf_pages import (
    PageMediumRefused,
    _derived_dpi,
    interior_images,
    page_image,
    page_medium_of,
    pdf_pages,
)

#: CON-018's Book 1 profile, in millimetres, written out here rather than
#: imported: 8.5 x 11 in, 0.5 in gutter, 0.5 in outside, 0.55 in top,
#: 0.47 in bottom (CON-018 as amended 2026-10-17), the
#: 12 mm title band (TERM-028) and NFR-008's 7.5 mm standard cell.
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
# CON-018's margins as amended 2026-10-17 (CARD-222): the outside margin
# moved 0.375 -> 0.5 in, the top to 0.55 in and the bottom to 0.47 in, and the
# gutter deliberately stayed at KDP's 0.5 in. Written out here, as this file
# writes every other figure out, rather than imported.
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5

#: 6 x 9 in, the other trim the ACs measure.
SIX_BY_NINE_MM = (6 * 25.4, 9 * 25.4)

#: Device pixels per millimetre at the 300 DPI every page is drawn at.
PX_PER_MM = 300 / 25.4

#: Tolerances the ACs state: the cell to 0.05 mm, a placed edge to 0.1 mm.
#:
#: **Every placed-edge expectation in this module is the RASTER interior's,
#: measured on Pillow's bitmap at 300 DPI through
#: ``page_ink.drawing_of``** — which reads a rule's first inked pixel line, so
#: it sits half a rule outside the boundary the page spec states (CARD-330:
#: 2 px for the 6 px border, 1 px for the 3 px cell line). The expectations are
#: pinned to that medium rather than re-tuned for both, because the interior is
#: going vector and **CARD-322's conversion retires them**; the pin is derived
#: rather than declared, by
#: :class:`TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium`. The bound
#: itself is NOT widened and the reason is measured — see
#: :data:`EDGE_TOLERANCE_EXEMPTIONS`, which is empty.
CELL_TOLERANCE_MM = 0.05
EDGE_TOLERANCE_MM = 0.1

#: A one-level small book's own front matter, in interior pages, written out
#: here rather than derived from the generator's constants: page 1 the blank
#: title / copyright page (CARD-206), pages 2-3 the guide (CARD-201's 2-page
#: tutorial), page 4 the one-page table of contents (CARD-200 — every book in
#: this file is far under one TOC page's capacity), page 5 the "Easy" divider
#: (CARD-128). So the **first puzzle page is interior page 6**, which is an
#: even, left-hand page (AC-287 as re-measured 2026-10-17), and the first
#: right-hand puzzle page is interior page 7 — the page AC-274 is about.
#: ``pages[n - 1]`` is interior page ``n``, so an index is one less.
FIRST_PUZZLE_PAGE = 6
DIVIDER_PAGE = FIRST_PUZZLE_PAGE - 1


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book(
    width_mm: float = BOOK1_WIDTH_MM,
    height_mm: float = BOOK1_HEIGHT_MM,
    gutter_mm: float | None = GUTTER_MM,
    outside_mm: float | None = OUTSIDE_MM,
) -> Book:
    """A book carrying a stored print specification, as a ``books`` row does.

    ``None`` for a margin is an empty column — the pre-print-margins row of
    AC-178. The trim is likewise left empty when it is ``None``.
    """
    return Book(
        book_id="book-116",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="A test book.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=None if width_mm is None else _cm(width_mm),
        trim_height_cm=None if height_mm is None else _cm(height_mm),
        gutter_margin_cm=None if gutter_mm is None else _cm(gutter_mm),
        outside_margin_cm=None if outside_mm is None else _cm(outside_mm),
    )


@pytest.fixture
def print_setup(monkeypatch):
    """Choose a book's trim the way the owner does: on the Print setup step.

    Returns ``choose(width_mm, height_mm) -> Book`` — a new book whose trim was
    submitted to ``POST /book/<id>/setup-print`` in centimetres and then read
    back out of the book store, so what the export is built from is whatever
    that route stored (CARD-136). The panel runs in its in-memory mode with a
    book store of its own, restored afterwards by ``monkeypatch``.
    """
    import nonogram.admin.book_manager as book_manager_module

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    monkeypatch.setattr(
        book_manager_module,
        "_book_manager",
        book_manager_module.BookManager(session_factory=None),
    )
    app = create_app()
    app.config["TESTING"] = True

    def choose(width_mm: float, height_mm: float) -> Book:
        book_id = app.book_manager.create_book(
            "Winter Pictures", "A test book.", "generic", "adults"
        )
        response = app.test_client().post(
            f"/book/{book_id}/setup-print",
            data={"unit": "cm", "width": _cm(width_mm), "height": _cm(height_mm)},
        )
        assert response.status_code == 302, "Print setup refused the trim"
        return app.book_manager.get_book(book_id)

    return choose


def _gutter_grid(columns: int, rows: int, depth: int) -> list[list[bool]]:
    """A grid whose row **and** column clues are exactly ``depth`` entries deep.

    Every other cell filled along both axes, stopped after ``depth`` runs:
    a line that carries any ink carries ``depth`` isolated single cells, and
    every other line is empty (``(0,)``, one entry). So the deepest clue in
    each direction is ``depth`` — which is what the ACs specify, and what
    decides how many cells wide and tall the *drawing* is.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    return [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]


def _puzzle(columns: int, rows: int, depth: int, name: str = "Snowflake") -> dict:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _gutter_grid(columns, rows, depth)
    found = clues.compute_clues(grid)
    assert max(len(clue) for clue in found.rows) == depth
    assert max(len(clue) for clue in found.columns) == depth
    return {
        "id": f"{name}-{columns}x{rows}",
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": "easy",
    }


def _expected_cell_mm(
    columns: int,
    rows: int,
    depth: int,
    *,
    width_mm: float = BOOK1_WIDTH_MM,
    height_mm: float = BOOK1_HEIGHT_MM,
    gutter_mm: float = GUTTER_MM,
    outside_mm: float = OUTSIDE_MM,
) -> float:
    """FR-030 in millimetres: ``min(standard cell, usable width / drawing columns,
    usable height / drawing rows)`` — a second implementation, written here."""
    usable_width = width_mm - gutter_mm - outside_mm
    usable_height = height_mm - TOP_MM - BOTTOM_MM - BAND_MM
    return min(
        STANDARD_CELL_MM,
        usable_width / (depth + columns),
        usable_height / (depth + rows),
    )


def _expected_left_mm(
    columns: int,
    depth: int,
    cell_mm: float,
    *,
    right_hand: bool,
    width_mm: float = BOOK1_WIDTH_MM,
    gutter_mm: float = GUTTER_MM,
    outside_mm: float = OUTSIDE_MM,
) -> float:
    """CARD-224 (FR-032's own centring, restored): the drawing centred across
    the usable width, which parity moves and the alignment does not. A
    right-hand (odd) page has the gutter margin on its left, a left-hand
    (even) page the outside margin, and in each case the drawing sits half
    this page's spare in from it. Between CARD-204 and CARD-224 this returned
    the flush-outer anchor instead (gutter + the *whole* spare on a
    right-hand page, the outside margin exactly on a left-hand one)."""
    usable_width = width_mm - gutter_mm - outside_mm
    spare = usable_width - (depth + columns) * cell_mm
    left_margin = gutter_mm if right_hand else outside_mm
    return left_margin + spare / 2


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _interior(book: Book, puzzles: list[dict]) -> list:
    """The book's interior pages in print order; ``pages[n - 1]`` is page ``n``."""
    return BookPDFGenerator(book).interior_pages(puzzles)


# --------------------------------------------------------------------------
# The cell the book's own trim gives a puzzle
# --------------------------------------------------------------------------


class TestBookPdf_CellSizedForBookTrimNotA4:
    """AC-175 — a 30x30 with 9-deep gutters draws a 4.885 mm cell on Book 1.

    Re-measured on CON-018's amended margins (2026-10-17): 190.5 mm of usable
    width over 39 cells, where the retired 0.375 in outside margin gave
    193.675 / 39 = 4.966 mm.
    """

    PUZZLE = (30, 30, 9)

    def test_the_page_draws_the_cell_the_book_trim_allows(self):
        book = _book()
        # interior page 6: title 1 (CARD-206), guide 2-3, TOC 4 (CARD-200),
        # "Easy" divider 5
        page = _interior(book, [_puzzle(*self.PUZZLE)])[FIRST_PUZZLE_PAGE - 1]

        drawn_mm = _mm(drawing_of(page).cell)

        assert abs(drawn_mm - 4.8853) < CELL_TOLERANCE_MM, drawn_mm
        expected = _expected_cell_mm(*self.PUZZLE)
        assert abs(drawn_mm - expected) < CELL_TOLERANCE_MM, (drawn_mm, expected)

    def test_it_is_not_the_cell_the_a4_layout_used_to_give_it(self):
        """The defect this AC pins: 190.5 mm over 39 cells, not A4's 186 mm."""
        book = _book()
        page = _interior(book, [_puzzle(*self.PUZZLE)])[FIRST_PUZZLE_PAGE - 1]

        a4_cell_mm = (210.0 - 2 * 12.0) / 39
        assert abs(a4_cell_mm - 4.7692) < 1e-3  # what the A4 sheet gave it
        # 4.885 against A4's 4.769: the gap narrowed with the amended
        # margins (it was 4.966) and the book's cell is still the larger.
        assert _mm(drawing_of(page).cell) - a4_cell_mm > 0.1


class TestBookPdf_CellFollowsStoredTrim:
    """AC-176 — the same 15x15 draws 5.77 mm on a 6 x 9 in book, 7.5 mm on 8.5 x 11.

    Both books are set up through Print setup (CARD-136), so the criterion is
    about the trim the owner chose and the product stored.
    """

    PUZZLE = (15, 15, 7)

    def test_a_six_by_nine_book_draws_the_smaller_cell(self, print_setup):
        width_mm, height_mm = SIX_BY_NINE_MM
        book = print_setup(width_mm, height_mm)
        page = _interior(book, [_puzzle(*self.PUZZLE)])[FIRST_PUZZLE_PAGE - 1]

        drawn_mm = _mm(drawing_of(page).cell)

        # 127.0 mm of usable width over 22 cells on the amended margins
        # (130.175 / 22 = 5.917 mm on the retired ones).
        assert abs(drawn_mm - 5.7743) < CELL_TOLERANCE_MM, drawn_mm
        expected = _expected_cell_mm(
            *self.PUZZLE, width_mm=width_mm, height_mm=height_mm
        )
        assert abs(drawn_mm - expected) < CELL_TOLERANCE_MM, (drawn_mm, expected)

    def test_the_same_puzzle_on_the_book_one_trim_is_held_at_the_standard_cell(
        self, print_setup
    ):
        book = print_setup(BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM)
        page = _interior(book, [_puzzle(*self.PUZZLE)])[FIRST_PUZZLE_PAGE - 1]

        drawn_mm = _mm(drawing_of(page).cell)

        assert abs(drawn_mm - STANDARD_CELL_MM) < CELL_TOLERANCE_MM, drawn_mm

    def test_changing_the_trim_is_what_changes_the_cell(self, print_setup):
        """The two halves side by side: one puzzle, two chosen trims."""
        puzzle = _puzzle(*self.PUZZLE)
        six_by_nine = _mm(drawing_of(_interior(print_setup(*SIX_BY_NINE_MM), [puzzle])[FIRST_PUZZLE_PAGE - 1]).cell)
        book_one = _mm(
            drawing_of(_interior(print_setup(BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM), [puzzle])[FIRST_PUZZLE_PAGE - 1]).cell
        )

        assert book_one - six_by_nine > 1.0, (book_one, six_by_nine)


class TestBookPdf_PageSizeEqualsStoredTrim:
    """AC-177 — every page of a 6 x 9 in book's PDF is 1800 x 2700 px at 300 DPI.

    Both halves of the AC are measured. The pixel size is the raster the page
    embeds; the **MediaBox** is what the page measures when printed, and only
    it can tell 1800 x 2700 px at 300 DPI (6 x 9 in) from the same raster
    written at some other resolution.
    """

    TRIM_PX = (1800, 2700)

    #: 6 x 9 in in PDF points (1/72 in): 432 x 648 pt. Written out here in
    #: inches x 72, not read back off the page.
    TRIM_PT = (0.0, 0.0, 6 * 72.0, 9 * 72.0)

    @pytest.fixture
    def export(self, print_setup):
        book = print_setup(*SIX_BY_NINE_MM)
        puzzles = [_puzzle(15, 15, 7), _puzzle(20, 20, 6), _puzzle(30, 30, 9)]
        return BookPDFGenerator(book).export_book(puzzles, book.metadata.title)

    #: This fixture's interior: the 2-page guide (CARD-201), the 1-page table
    #: of contents (CARD-200 — 3 entries, far under one TOC page's capacity),
    #: the "Easy" divider that opens the book's one level (CARD-128), three
    #: puzzle pages (none of these three pairs) and the SOLUTIONS divider,
    #: then three answer pages — one full solved page per puzzle (CARD-198,
    #: up from the packed key's one four-up page before that card). The
    #: leading ``1`` is CARD-206's blank title / copyright page.
    PAGES = 1 + 2 + 1 + 1 + 3 + 1 + 3

    def test_every_interior_page_of_the_pdf_is_the_stored_trim(self, export):
        pages = pdf_pages(export.interior.getvalue())

        assert len(pages) == self.PAGES
        assert [page.size for page in pages] == [self.TRIM_PX] * len(pages)

    def test_every_interior_page_measures_six_by_nine_inches_when_printed(self, export):
        """The "at 300 DPI" half: 1800 px across a page 432 pt (6 in) wide."""
        boxes = pdf_page_boxes(export.interior.getvalue())

        assert boxes == [self.TRIM_PT] * self.PAGES

    def test_the_cover_file_is_the_stored_trim_too(self, export):
        (cover,) = pdf_pages(export.cover.getvalue())

        assert cover.size == self.TRIM_PX
        assert pdf_page_boxes(export.cover.getvalue()) == [self.TRIM_PT]

    def test_it_is_not_the_hard_coded_letter_page(self, export):
        assert (2550, 3300) not in {page.size for page in pdf_pages(export.interior.getvalue())}


class TestBookPdf_EmptyMarginsFallBackToBook1Profile:
    """AC-178 — a row from before print margins were set prints on the profile."""

    PUZZLE = (30, 30, 9)

    @pytest.mark.parametrize(
        "book",
        [
            pytest.param(_book(gutter_mm=None, outside_mm=None), id="margins-empty"),
            pytest.param(
                _book(width_mm=None, height_mm=None, gutter_mm=None, outside_mm=None),
                id="whole-print-spec-empty",
            ),
        ],
    )
    def test_the_cell_is_the_one_the_con_018_margins_give(self, book):
        page = _interior(book, [_puzzle(*self.PUZZLE)])[FIRST_PUZZLE_PAGE - 1]

        drawn_mm = _mm(drawing_of(page).cell)

        assert abs(drawn_mm - 4.8853) < CELL_TOLERANCE_MM, drawn_mm
        assert abs(drawn_mm - _expected_cell_mm(*self.PUZZLE)) < CELL_TOLERANCE_MM

    def test_the_page_is_the_profile_trim(self):
        book = _book(width_mm=None, height_mm=None, gutter_mm=None, outside_mm=None)

        pages = _interior(book, [_puzzle(*self.PUZZLE)])

        assert {page.size for page in pages} == {(2550, 3300)}

    def test_that_page_measures_eight_and_a_half_by_eleven_inches_when_printed(self):
        """2550 x 3300 px is the profile trim only at 300 DPI: 612 x 792 pt."""
        book = _book(width_mm=None, height_mm=None, gutter_mm=None, outside_mm=None)

        export = BookPDFGenerator(book).export_book(
            [_puzzle(*self.PUZZLE)], book.metadata.title
        )

        letter_pt = (0.0, 0.0, 8.5 * 72.0, 11 * 72.0)
        # 1 title (CARD-206) + 2 guide + 1 TOC (CARD-200) + 1 divider +
        # 1 puzzle + 1 SOLUTIONS + 1 answer = 8.
        assert pdf_page_boxes(export.interior.getvalue()) == [letter_pt] * 8
        assert pdf_page_boxes(export.cover.getvalue()) == [letter_pt]


# --------------------------------------------------------------------------
# Portrait, upright, and a top edge that never moves (FR-032)
# --------------------------------------------------------------------------


class TestBookPdf_WideGridPrintsOnPortraitPage:
    """AC-189 — a 30-wide x 15-tall puzzle prints on a 2550 x 3300 px page."""

    def test_the_page_is_portrait_at_the_book_trim(self):
        pages = _interior(_book(), [_puzzle(30, 15, 5)])

        page = pages[FIRST_PUZZLE_PAGE - 1]
        assert page.size == (2550, 3300)
        assert page.size[0] < page.size[1], "portrait"

    def test_every_page_of_that_book_is_portrait(self):
        pages = _interior(_book(), [_puzzle(30, 15, 5)])

        assert {page.size for page in pages} == {(2550, 3300)}


class TestBookPdf_WideGridPrintsUprightNeverRotated:
    """AC-240 — 30 columns across the page and 15 rows down it."""

    def test_the_grid_is_drawn_unrotated(self):
        page = _interior(_book(), [_puzzle(30, 15, 5)])[FIRST_PUZZLE_PAGE - 1]

        drawing = drawing_of(page)

        assert (drawing.columns, drawing.rows) == (30, 15)

    # CARD-220 examined this test and the one above as a deletion candidate
    # and KEPT BOTH. `drawing_of` is read one way above (a 30x15 puzzle reads
    # 30x15) and the other way here (a 15x30 reads 15x30), so this test is the
    # other's instrument proof: delete it and "the grid is drawn unrotated" is
    # satisfied by a measurement that reports the declared dimensions whatever
    # the page actually holds. Neither has a named survivor.
    def test_the_measurement_would_have_seen_a_rotation(self):
        """The negative has teeth: a 15-wide x 30-tall puzzle reads the other way."""
        page = _interior(_book(), [_puzzle(15, 30, 5)])[FIRST_PUZZLE_PAGE - 1]

        drawing = drawing_of(page)

        assert (drawing.columns, drawing.rows) == (15, 30)


class TestBookPdf_PuzzleTopEdgeFloatsWithTheSpare:
    """AC-366/AC-367 — a 15x15 and a 30x30 no longer start on the same pixel
    row: each floats at 42% of its page's own puzzle-area spare.

    **This class replaces AC-190's** (``TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage``,
    "a 15x15 and a 30x30 start on the same pixel row"), which the registry
    retired with its test on 2026-10-17 when FR-032's fixed top edge became
    the 42% float. It is that test's named survivor at the PDF level (CARD-220's
    rule): the same two pages of the same book, measured off the same ink, with
    the claim the amendment put in its place. AC-366/AC-367's own designated
    test is ``TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare``, which
    states the ratio itself; what is here is the pair of pages AC-190 used, so
    that the page kind it watched keeps a test of its own.

    AC-367's arithmetic, restated: the 15x15's drawing is 22 cells at the
    7.5 mm cap (165.0 mm) and the 30x30's is 39 cells at page fit (190.5 mm),
    so the shallower drawing has 25.5 mm more spare and floats 0.42 of that —
    10.71 mm — lower than the deeper one.
    """

    def test_the_two_puzzle_pages_no_longer_start_at_the_same_top_edge(self):
        pages = _interior(_book(), [_puzzle(15, 15, 7), _puzzle(30, 30, 9)])

        small, large = drawing_of(pages[FIRST_PUZZLE_PAGE - 1]), drawing_of(pages[FIRST_PUZZLE_PAGE])

        assert small.top != large.top
        assert small.cell != large.cell, "the two do print different cells"

    def test_the_shallower_drawing_sits_10_71_mm_lower(self):
        pages = _interior(_book(), [_puzzle(15, 15, 7), _puzzle(30, 30, 9)])

        small, large = drawing_of(pages[FIRST_PUZZLE_PAGE - 1]), drawing_of(pages[FIRST_PUZZLE_PAGE])

        # 0.42 x (190.5 - 165.0) mm, off the drawn ink of both pages.
        assert _mm(small.top - large.top) == pytest.approx(10.71, abs=0.1)


# --------------------------------------------------------------------------
# Mirrored margins (FR-032 amended 2026-09-22 (c), FR-043)
# --------------------------------------------------------------------------

#: AC-274/AC-275's book: three 15x15 puzzles with 7-deep clue gutters, so the
#: puzzle pages are interior pages 6, 7 and 8 (:data:`FIRST_PUZZLE_PAGE` and
#: the two after it — before CARD-206 these were pages 5, 6 and 7; before
#: CARD-200 pages 4, 5 and 6; before CARD-201 pages 2, 3 and 4. Each card's
#: own front-matter insertion moves every later page by one and flips its
#: parity, so the **first** puzzle page — right-hand under CARD-200's count
#: (page 5) — is left-hand again under CARD-206's (page 6), and AC-274's
#: right-hand illustration moves on with it, to the second puzzle, interior
#: page 7).
_MIRRORED_PUZZLE = (15, 15, 7)


def _mirrored_pages():
    return _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE, name=f"P{n}") for n in range(3)])


class TestBookPdf_DrawingCentredOnRightHandPage:
    """AC-274 — on interior page 7 the drawing's left edge is 25.45 mm in.

    **CARD-206 moved which page this is.** The claim is about a *right-hand*
    page, and the book's first puzzle page became a left-hand one when the
    blank title page went in front of the front matter, so the right-hand
    illustration is now the second puzzle, interior page 7
    (:data:`FIRST_PUZZLE_PAGE` + 1). The figure it reads is unchanged: on the
    amended profile the two side margins are equal, so a centred drawing's
    left edge is the same number at either parity (see the identity recorded
    in ``test_on_book_1_the_miscount_is_invisible_in_the_drawing``).


    **The number AC-274 states, and this class's own name, are correct again
    (CARD-224).** 15x15, depth 7: drawing width 22 x 7.5 mm = 165 mm; usable
    width 190.5 mm (CON-018 as amended 2026-10-17); spare 25.5 mm, split in
    half — gutter margin 12.7 mm plus 12.75 mm = 25.45 mm. Between CARD-204
    and this card the drawing was flush with the outer (right) edge instead
    and this test read 38.2 mm, the gutter plus the *whole* spare.
    """

    def test_the_drawing_sits_25_45_mm_from_the_left_trim_edge(self):
        page = _mirrored_pages()[FIRST_PUZZLE_PAGE]  # interior page 7, right-hand

        left_mm = _mm(drawing_of(page).left)

        assert abs(left_mm - 25.45) < EDGE_TOLERANCE_MM, left_mm

    def test_that_is_the_usable_width_centred_with_the_gutter_on_the_left(self):
        page = _mirrored_pages()[FIRST_PUZZLE_PAGE]

        left_mm = _mm(drawing_of(page).left)
        expected = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=True)

        assert abs(left_mm - expected) < EDGE_TOLERANCE_MM, (left_mm, expected)
        # 25.5 mm of slack, half of it on each side of the drawing.
        assert abs((left_mm - GUTTER_MM) - 25.5 / 2) < EDGE_TOLERANCE_MM


class TestBookPdf_DrawingCentredOnLeftHandPage:
    """AC-275 — on interior page 6 the same drawing's left edge is 12.7 mm in.

    CARD-200 (SCOPE+): the TOC's own one page moved this card's illustrative
    page from 4 to 6 (and its parity's own illustration from the second
    puzzle to the third, since the second puzzle is now the right-hand one —
    see `_MIRRORED_PUZZLE`'s own note).

    **CARD-206** moved it back to the **first** puzzle page: the blank title
    page flips every later page's parity, so interior page 6 — still the
    left-hand illustration, still the same figure — is now
    :data:`FIRST_PUZZLE_PAGE` itself rather than the page after it.

    **CARD-224:** the offset is the outside margin plus half the spare —
    12.7 + 12.75 = 25.45 mm on the amended profile, the same figure as the
    right-hand page's because that profile's two side margins are equal (the
    registry's own note on EC-032: on Book 1 this equality makes a parity
    comparison an identity, and the mirroring is observable only on a book
    storing unequal margins, which is what ``tests/test_layout_page_spec.py``
    and ``tests/property/test_book_layout.py`` sweep). Between CARD-204 and
    this card it was exactly the outside margin, 12.7 mm.
    """

    def test_the_drawing_sits_25_45_mm_from_the_left_trim_edge(self):
        page = _mirrored_pages()[FIRST_PUZZLE_PAGE - 1]  # interior page 6, left-hand (CARD-206)

        left_mm = _mm(drawing_of(page).left)

        assert abs(left_mm - 25.45) < EDGE_TOLERANCE_MM, left_mm

    def test_that_is_the_usable_width_centred_with_the_gutter_on_the_right(self):
        page = _mirrored_pages()[FIRST_PUZZLE_PAGE - 1]

        left_mm = _mm(drawing_of(page).left)
        expected = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=False)

        assert abs(left_mm - expected) < EDGE_TOLERANCE_MM, (left_mm, expected)
        # Half the spare in from the outside margin (CARD-224).
        assert abs((left_mm - OUTSIDE_MM) - 25.5 / 2) < EDGE_TOLERANCE_MM

    def test_the_two_pages_differ_by_the_gutter_less_the_outside_margin(self):
        """CARD-224: centring restores EC-032's own invariant — the two pages'
        drawings differ by exactly ``gutter - outside``, the spare's two equal
        halves cancelling out of the subtraction. Between CARD-204 and this
        card the difference was ``(gutter - outside) + spare`` instead,
        because flush-right and flush-left anchor at different edges.

        **Since the 2026-10-17 amendment ``gutter - outside`` is zero** — both
        side margins are 0.5 in — so on this profile the assertion below says
        the two drawings sit at the *same* x, and that is an identity rather
        than evidence that mirroring works (the registry's own note on
        EC-032). The formula is kept rather than collapsed to ``== 0``,
        because the formula is the rule, and the books that make it bite are
        swept with unequal margins in
        ``tests/property/test_book_layout.py::test_PropertyTest_BookLayout_ParityMirroringHoldsUnderCentring``.
        """
        pages = _mirrored_pages()

        right_hand = drawing_of(pages[FIRST_PUZZLE_PAGE]).left
        left_hand = drawing_of(pages[FIRST_PUZZLE_PAGE - 1]).left

        assert abs(_mm(right_hand - left_hand) - (GUTTER_MM - OUTSIDE_MM)) < EDGE_TOLERANCE_MM


class TestBookPdf_ParityNeverMovesTopEdge:
    """AC-276 — parity moves the drawing sideways only.

    **The premise this class needs, and where it now comes from (CARD-224
    review cycle 1, F-006).** "Parity never moves the top edge" is only a
    claim about parity if the two pages compared really are opposite parities.
    Until CARD-222's amendment the drawing's own left edge said so; on the
    amended profile the two side margins are both 0.5 in, so a centred drawing
    lands on the same pixel column either way and that edge says nothing. The
    premise is therefore read off the furniture that *does* mirror — CARD-223's
    2 cm QR placeholder, which sits in the footer's **outer** bottom corner, so
    it is at the right-hand end of a right-hand page and the left-hand end of a
    left-hand one — the same signal
    ``tests/test_book_pdf_memory.py::test_parity_still_counts_from_interior_page_1``
    reads, asserted here rather than cross-referenced, because a premise in
    another file cannot fail this test.
    """

    #: The QR placeholder's own box and the usable area's two edges in this
    #: page's own pixels, written out rather than imported: a 20 mm icon and
    #: 0.5 in margins on a 8.5 in trim at 300 DPI.
    ICON_PX = round(20.0 / 25.4 * 300)
    USABLE_LEFT_PX = round(GUTTER_MM / 25.4 * 300)
    USABLE_RIGHT_PX = round((BOOK1_WIDTH_MM - OUTSIDE_MM) / 25.4 * 300)

    @classmethod
    def _footer_icon_ends(cls, page) -> tuple[int, int]:
        """``(ink at the left end, ink at the right end)`` of this page's
        footer strip — the two boxes the 2 cm icon could occupy."""
        ink = np.asarray(page.convert("L")) < 128
        strip = ink[-cls.ICON_PX :]
        left = int(strip[:, cls.USABLE_LEFT_PX : cls.USABLE_LEFT_PX + cls.ICON_PX].sum())
        right = int(strip[:, cls.USABLE_RIGHT_PX - cls.ICON_PX : cls.USABLE_RIGHT_PX].sum())
        return left, right

    def test_the_two_drawings_share_a_top_pixel_row(self):
        pages = _mirrored_pages()

        right_hand = drawing_of(pages[FIRST_PUZZLE_PAGE])
        left_hand = drawing_of(pages[FIRST_PUZZLE_PAGE - 1])

        # The premise: these two really are opposite parities, read off the
        # footer icon's end of the strip (see the class docstring).
        odd_left, odd_right = self._footer_icon_ends(pages[FIRST_PUZZLE_PAGE])
        even_left, even_right = self._footer_icon_ends(pages[FIRST_PUZZLE_PAGE - 1])
        assert odd_right > 4 * odd_left, (
            "interior page 7 is right-hand, so its footer icon belongs at the "
            "right-hand end of the strip",
            odd_left,
            odd_right,
        )
        assert even_left > 4 * even_right, (
            "interior page 6 is left-hand, so its footer icon belongs at the "
            "left-hand end of the strip",
            even_left,
            even_right,
        )

        # The claim: parity moved the page's furniture and not the drawing's
        # top row.
        assert right_hand.top == left_hand.top
        # And on the amended profile the two side margins are equal, so a
        # centred drawing lands on the same x at either parity — "sideways
        # only" has nothing left to move here. Recorded, not read as evidence.
        assert abs(GUTTER_MM - OUTSIDE_MM) < 1e-9
        assert right_hand.left == left_hand.left

    def test_they_are_the_same_drawing_at_the_same_cell(self):
        pages = _mirrored_pages()

        right_hand = drawing_of(pages[FIRST_PUZZLE_PAGE])
        left_hand = drawing_of(pages[FIRST_PUZZLE_PAGE - 1])

        assert (right_hand.columns, right_hand.rows) == (left_hand.columns, left_hand.rows)
        assert abs(right_hand.cell - left_hand.cell) <= 1


class TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1:
    """AC-287 (FR-043, INV-013) — the first puzzle page is interior page 6, left-hand.

    **CARD-206 note (SCOPE+): these numbers shifted by one again, and the
    parity flipped a third time.** The interior now runs the blank title /
    copyright page (CARD-206), the 2-page guide
    (CARD-201), the 1-page table of contents (CARD-200 — this book's one
    entry is far under a TOC page's own capacity), then the "Easy" divider
    (CARD-128), then the first puzzle — so that puzzle is interior page
    **6**, an even page, with the 12.7 mm outside margin on its **left** (the
    gutter margin is on its right). Before this card (CARD-200 + CARD-201)
    this same puzzle sat at interior page 5, an odd page, gutter on the
    left — the opposite parity; before CARD-200 it was page 4, even again,
    and before CARD-201 page 3.
    The claim AC-287 itself makes (parity counts from interior page 1, not
    from a miscount that includes the cover) is unchanged; only which page
    number and which parity the first puzzle page actually has moved, which
    is exactly this card's own ripple (one extra front-matter page) and not a
    defect in the parity rule — the same shape of ripple CARD-200's and
    CARD-201's own notes here already described for their own one-page
    additions. The registry re-measured AC-287 to this reading on 2026-10-17.

    The usable area's left edge is asserted through the drawing's (CARD-224):
    the drawing is centred in the usable area, so on this left-hand page its
    left edge is the outside margin plus *half* the spare. Between CARD-204 and
    this card it was the outer margin plus the whole spare.

    **Where the miscount is caught (CARD-224 review cycle 1, F-002).** On
    CON-018 as amended both side margins are 0.5 in, so a centred drawing sits
    on the same pixel column at either parity and *every* left-edge comparison
    on Book 1 is an identity — including the one that is supposed to exclude
    the miscounted, right-hand reading of this page (the reading a count that
    forgot CARD-206's own title page would give it). The exclusion is therefore
    made on an **unequal-margin book** (:attr:`WIDE_GUTTER_MM` /
    :attr:`NARROW_OUTSIDE_MM`), exactly as
    :class:`TestBookPdf_UnbuildablePuzzleNeverShiftsALaterPage` and
    :class:`TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity` already
    do, where the two readings are 10 mm (118 px) apart. The Book 1
    assertions are kept for the figures they still state, and the identity is
    asserted explicitly so it cannot be mistaken for evidence.
    """

    #: An **unequal**-margin book, for the two tests below that need the
    #: miscount to be visible in the drawing's own x. A 20 mm gutter against a
    #: 10 mm outside margin moves the drawing by 10 mm between the parities.
    WIDE_GUTTER_MM = 20.0
    NARROW_OUTSIDE_MM = 10.0

    @classmethod
    def _unequal_expected_left_mm(cls, *, right_hand: bool) -> float:
        return _expected_left_mm(
            15,
            7,
            STANDARD_CELL_MM,
            right_hand=right_hand,
            gutter_mm=cls.WIDE_GUTTER_MM,
            outside_mm=cls.NARROW_OUTSIDE_MM,
        )

    @classmethod
    def _unequal_pages(cls, count: int = 1):
        book = _book(gutter_mm=cls.WIDE_GUTTER_MM, outside_mm=cls.NARROW_OUTSIDE_MM)
        return _interior(
            book,
            [_puzzle(*_MIRRORED_PUZZLE, name=f"P{n}") for n in range(count)],
        )

    def test_the_first_puzzle_page_is_left_hand(self):
        """Interior page 6's drawing is at the left-hand position.

        Asserted on both books: Book 1 for the figure AC-287 states, and the
        unequal-margin book for the fact that it is the *left-hand* one
        (CARD-224 review cycle 1, F-002 — on Book 1 the two positions are the
        same number).
        """
        pages = _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])

        left_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1]).left)
        expected = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=False)

        assert abs(left_mm - expected) < EDGE_TOLERANCE_MM, (left_mm, expected)

        unequal_mm = _mm(drawing_of(self._unequal_pages()[FIRST_PUZZLE_PAGE - 1]).left)

        assert abs(unequal_mm - self._unequal_expected_left_mm(right_hand=False)) < (
            EDGE_TOLERANCE_MM
        ), unequal_mm

    def test_its_usable_area_starts_at_the_outside_margin(self):
        """12.7 mm from the left trim edge: 0.5 in, the outside margin (CON-018).

        A left-hand page carries the gutter on its **right**, so its usable
        area starts at the outside margin. On CON-018 as amended both side
        margins are 0.5 in, so the figure is the one this test has always
        read; which margin it *is* changed with CARD-206's parity flip, and
        that is what the name and the assertion below now say.

        CARD-224: the drawing's own left edge is the usable area's left edge
        plus *half* this page's spare (centred). Under CARD-204's flush-outer
        anchor it was that edge plus the whole spare.
        """
        pages = _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])

        left_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1]).left)
        spare = (BOOK1_WIDTH_MM - GUTTER_MM - OUTSIDE_MM) - (7 + 15) * STANDARD_CELL_MM

        assert abs(OUTSIDE_MM - 12.7) < 1e-9, "the profile's outside margin is 0.5 in"
        assert abs((left_mm - spare / 2) - OUTSIDE_MM) < EDGE_TOLERANCE_MM, left_mm

    def test_it_is_not_the_right_hand_page_a_miscount_would_give_it(self):
        """Forgetting the title page would make this page 5, gutter margin left.

        That is the miscount this card's own ripple creates, and it is the
        same shape as the older one (counting the cover as interior page 1):
        both put this drawing one page earlier, at the opposite parity.

        **Measured on an unequal-margin book** (CARD-224 review cycle 1,
        F-002): the gap between the right-hand and left-hand positions is
        ``gutter - outside`` (centring's own invariant, EC-032), which on
        CON-018 as amended is **zero** — so on Book 1 a miscounted parity
        moves this drawing nowhere and the exclusion this test exists to make
        is unmakeable there. On a 20 mm gutter against a 10 mm outside margin
        the two readings are 10 mm apart, and the drawing is asserted to be at
        the left-hand one and **not** at the right-hand one.
        """
        pages = self._unequal_pages()

        left_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1]).left)
        right_hand = self._unequal_expected_left_mm(right_hand=True)
        left_hand = self._unequal_expected_left_mm(right_hand=False)

        assert abs(right_hand - left_hand) == pytest.approx(10.0), (
            "this book must really move the drawing between the parities, or "
            "the refutation below is an identity",
            right_hand,
            left_hand,
        )
        assert abs(left_mm - left_hand) < EDGE_TOLERANCE_MM, (left_mm, left_hand)
        assert abs(left_mm - right_hand) > EDGE_TOLERANCE_MM, (
            "interior page 6 is left-hand; a count that forgot the title page "
            "(or included the cover) would put this drawing at the right-hand "
            "position instead",
            left_mm,
            right_hand,
        )

    def test_on_book_1_the_miscount_is_invisible_in_the_drawing(self):
        """Why the test above does not use this book, recorded as a measurement.

        On CON-018 as amended the two side margins are equal, so the centred
        drawing's left edge is the *same* number at either parity: the
        identity is asserted here, where it is the subject, instead of being
        left to look like evidence in a test named for a refutation.
        """
        pages = _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])

        left_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1]).left)
        right_hand = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=True)
        left_hand = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=False)

        assert abs(GUTTER_MM - OUTSIDE_MM) < 1e-9, "both side margins are 0.5 in"
        assert right_hand == left_hand
        assert abs(left_mm - left_hand) < EDGE_TOLERANCE_MM

    def test_the_divider_did_not_take_the_puzzle_pages_place(self):
        """Interior page 5 is the level divider, and carries no drawing at all.

        Without it (and without the blank title page, the guide's own second
        page and the table of
        contents) the first puzzle would be page 2 — the reading this AC
        replaced — so the pages that moved it are checked to be there.
        """
        pages = _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])
        divider = np.asarray(pages[DIVIDER_PAGE - 1].convert("L")) < 128

        assert divider.any(), "interior page 5 is blank"
        assert divider.sum() < pages[DIVIDER_PAGE - 1].width * pages[DIVIDER_PAGE - 1].height / 1000

    def test_the_parities_alternate_from_there(self):
        """Pages 6, 7, 8 are left, right, left — each page's own position.

        **On the unequal-margin book** (CARD-224 review cycle 1, F-002), where
        the alternation is a 10 mm move and not a zero one: pages 6 and 8 share
        a left edge, page 7 sits 10 mm away from both. On the amended Book 1
        profile all three numbers coincide, so the sequence there cannot tell
        "left, right, left" from "left, left, left".
        """
        pages = self._unequal_pages(count=3)

        lefts = [_mm(drawing_of(page).left) for page in pages[FIRST_PUZZLE_PAGE - 1 : FIRST_PUZZLE_PAGE + 2]]
        expected = {
            hand: self._unequal_expected_left_mm(right_hand=hand) for hand in (True, False)
        }

        assert abs(expected[True] - expected[False]) == pytest.approx(10.0)
        assert abs(lefts[0] - expected[False]) < EDGE_TOLERANCE_MM, lefts
        assert abs(lefts[1] - expected[True]) < EDGE_TOLERANCE_MM, lefts
        assert abs(lefts[2] - expected[False]) < EDGE_TOLERANCE_MM, lefts
        assert abs(lefts[0] - lefts[2]) < EDGE_TOLERANCE_MM, lefts
        # EC-032's own formula, on a profile where it is not an identity.
        # Since CARD-206 the first of the three is the left-hand page, so the
        # right-hand reading is the second one's.
        assert abs(
            lefts[1] - lefts[0] - (self.WIDE_GUTTER_MM - self.NARROW_OUTSIDE_MM)
        ) < EDGE_TOLERANCE_MM, lefts


# --------------------------------------------------------------------------
# What a puzzle that will not render does to the pages around it
# --------------------------------------------------------------------------


def _unbuildable_puzzle(name: str = "Broken") -> dict:
    """A book row no ``ExportPayload`` can be built from.

    Its ``clues_rows`` is a number, so ``_payload``'s ``tuple(tuple(row) for
    row in ...)`` raises before any page position has been handed out.
    """
    return {
        "id": f"{name}-unbuildable",
        "grid": [[True]],
        "clues_rows": 5,
        "clues_cols": [[1]],
        "width": 1,
        "height": 1,
        "puzzle_name": name,
        "difficulty_tier": "easy",
    }


def _undrawable_puzzle(name: str = "Ghost") -> dict:
    """A book row whose payload builds and whose page then will not draw.

    Real clues, no grid: ``compute_layout`` is happy, and the renderer fails
    when it reaches the cells it is asked to reveal.
    """
    puzzle = _puzzle(*_MIRRORED_PUZZLE, name=name)
    puzzle["id"] = f"{name}-undrawable"
    puzzle["grid"] = None
    return puzzle


def _unmeasurable_puzzle(name: str = "Half", tier: str = "easy") -> dict:
    """A book row whose payload builds and which no layout call can measure.

    Row clues and **no** column clues: ``_payload`` is happy (it turns an empty
    list into an empty clue set), and both of COMP-007's layout calls refuse a
    pair of clue sets that disagree about the grid — ``compute_layout`` when
    the row prints alone, ``compute_pair_layout`` when the pairing walk offers
    it beside a same-tier neighbour. The two stages are the point: this row
    fails at *layout* time, where the ``grid=None`` row above fails at *draw*
    time, and until CARD-127's review only the draw-time failure was named.
    """
    puzzle = _puzzle(*_MIRRORED_PUZZLE, name=name)
    puzzle["id"] = f"{name}-unmeasurable"
    puzzle["clues_cols"] = []
    puzzle["difficulty_tier"] = tier
    return puzzle


class TestBookPdf_UnbuildablePuzzleNeverShiftsALaterPage:
    """A dropped puzzle leaves every surviving page on its own parity.

    This is an **API-contract** test, not a production scenario: the store's
    write path refuses a row like this today (``add_puzzle`` re-derives the
    clues from the grid), so the malformed row is fed straight to
    ``interior_pages``, which is where the contract lives. The contract is the
    reason ``interior_pages`` builds every payload before it hands out a
    single page position: a puzzle dropped *after* positions were handed out
    would leave a hole in the numbering and mirror every later page's margins
    the wrong way round.
    """

    def test_the_survivors_sit_where_their_own_positions_put_them(self):
        pages = _interior(
            _book(),
            [
                _puzzle(*_MIRRORED_PUZZLE, name="First"),
                _unbuildable_puzzle(),
                _puzzle(*_MIRRORED_PUZZLE, name="Second"),
            ],
        )

        # The blank title page 1 (CARD-206), guide 2-3 (CARD-201), the 1-page
        # TOC (CARD-200), the "Easy" divider
        # 5, the two survivors 6 and 7, the SOLUTIONS divider 8, and the
        # answer section: both survivors are 15x15 (qualifying, width<=15 and
        # height<=20) and the same tier, so CARD-202 packs them onto one
        # shared answer page, 9 — not two full pages.
        assert len(pages) == 9
        first_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1]).left)
        second_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE]).left)

        # Interior page 6 is left-hand, page 7 right-hand (CARD-206: the title
        # page flips the parity CARD-200's own version of this comment once
        # stated).
        assert abs(first_mm - _expected_left_mm(
            15, 7, STANDARD_CELL_MM, right_hand=False
        )) < EDGE_TOLERANCE_MM, first_mm
        assert abs(second_mm - _expected_left_mm(
            15, 7, STANDARD_CELL_MM, right_hand=True
        )) < EDGE_TOLERANCE_MM, second_mm

    #: An **unequal**-margin book, for the one test below that needs the
    #: mirroring to be visible in the drawing's own x. On CON-018 as amended
    #: 2026-10-17 the gutter and the outside margin are both 0.5 in, so a
    #: centred drawing (CARD-224) lands on the same pixel column at both
    #: parities and a left-edge comparison cannot tell a right-hand page from
    #: a left-hand one at all — the identity the registry's note on EC-032
    #: warns a reviewer not to read as evidence. A 20 mm gutter against a
    #: 10 mm outside margin moves the drawing by 10 mm between the two.
    WIDE_GUTTER_MM = 20.0
    NARROW_OUTSIDE_MM = 10.0

    def test_the_second_survivor_did_not_inherit_the_dropped_page_parity(self):
        """The failure this pins: the survivor left on page 8's margins.

        Had the drop happened after page 7 was handed to the broken puzzle,
        the second survivor would be interior page 8 — left-hand, the same
        left edge as the first survivor — instead of page 7.

        **CARD-224**: measured on an unequal-margin book (see
        :attr:`WIDE_GUTTER_MM`), because a centred drawing on the equal-margin
        Book 1 profile sits at the same x on either parity, so this failure
        would be invisible there. The two expected figures are 10 mm apart,
        which is 118 px — not a tolerance.
        """
        book = _book(gutter_mm=self.WIDE_GUTTER_MM, outside_mm=self.NARROW_OUTSIDE_MM)
        pages = _interior(
            book,
            [
                _puzzle(*_MIRRORED_PUZZLE, name="First"),
                _unbuildable_puzzle(),
                _puzzle(*_MIRRORED_PUZZLE, name="Second"),
            ],
        )

        first_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1]).left)
        second_mm = _mm(drawing_of(pages[FIRST_PUZZLE_PAGE]).left)
        expected = {
            hand: _expected_left_mm(
                15,
                7,
                STANDARD_CELL_MM,
                right_hand=hand,
                gutter_mm=self.WIDE_GUTTER_MM,
                outside_mm=self.NARROW_OUTSIDE_MM,
            )
            for hand in (True, False)
        }

        assert abs(expected[True] - expected[False]) == pytest.approx(10.0)
        assert abs(first_mm - expected[False]) < EDGE_TOLERANCE_MM, first_mm
        assert abs(second_mm - expected[True]) < EDGE_TOLERANCE_MM, second_mm
        # EC-032's own formula, on the profile where it is not an identity.
        # Since CARD-206 the first survivor is the **left-hand** page of the
        # two, so the right-hand reading is the second one's.
        assert abs(
            second_mm - first_mm - (self.WIDE_GUTTER_MM - self.NARROW_OUTSIDE_MM)
        ) < EDGE_TOLERANCE_MM

    def test_the_drop_leaves_a_trace_in_the_log(self, caplog):
        """It is the only trace: nothing else says the book lost a member.

        Through the module's logger, so a served request records it — a
        ``print`` here lands nowhere.
        """
        with caplog.at_level("WARNING", logger="nonogram.admin.book_pdf_generator"):
            _interior(_book(), [_unbuildable_puzzle(), _puzzle(*_MIRRORED_PUZZLE)])

        (record,) = [r for r in caplog.records if "Broken-unbuildable" in r.getMessage()]
        assert record.levelname == "WARNING"
        assert record.name == "nonogram.admin.book_pdf_generator"


class TestBookPdf_PagePlanGuardIsLive:
    """The self-check fires when the pages built stop matching the page plan.

    It compares this call's **input** — the puzzles that survived the payload
    pass — against the pages the loop produced, so a later change to the
    make-up of the interior (a divider per level, a two-up page) that forgets
    :func:`interior_page_count` is caught here. It used to take its number
    from a list the same loop built, which reads as a drift guard while
    measuring the output against itself; no input makes the two disagree
    today, so what this test pins is that the guard is *live* at all.
    """

    def test_a_plan_that_no_longer_describes_the_pages_aborts(self, monkeypatch):
        import nonogram.admin.book_pdf_generator as generator_module

        planned = generator_module.interior_page_count
        monkeypatch.setattr(
            generator_module,
            "interior_page_count",
            # The plan now also takes how many pages the puzzles and the
            # answers actually take — two-up pairing (CARD-127) can make the
            # first fewer than the count, and FR-042's packed key (CARD-134)
            # the second — and, since CARD-200, the table of contents' own
            # length, and since CARD-305 whether the SOLUTIONS divider is a
            # page at all. All four are passed straight through, so what this
            # monkeypatch changes is the total and nothing else — and this
            # stub mirrors the real signature rather than swallowing the rest
            # in ``**kwargs`` on purpose: a parameter added to the function
            # and forgotten here would then be dropped silently, and this
            # guard would start asserting against a plan computed without it.
            # CARD-305 found it the loud way, which is the right way.
            lambda count, puzzle_pages=None, answer_pages=None, level_dividers=0, toc_pages=None, solutions_divider=True: (
                planned(
                    count,
                    puzzle_pages,
                    answer_pages,
                    level_dividers,
                    toc_pages=toc_pages,
                    solutions_divider=solutions_divider,
                )
                + 1
            ),
        )

        with pytest.raises(RuntimeError) as raised:
            _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])

        assert "interior has 8 pages, its page plan says 9" in str(raised.value)

    def test_a_walk_that_loses_a_puzzle_aborts_before_a_page_is_drawn(self, monkeypatch):
        """The half the page-count check cannot make (CARD-127 review F-002).

        Since two-up pairing, the puzzle-page term of that check comes from
        ``len(plan)`` — the walk's own output — so a walk that dropped a puzzle
        would agree with itself: the book would ship without that puzzle while
        its answer page was still printed. This is the guard taken over the
        call's *input* instead.
        """
        from nonogram.admin.book_pdf_generator import BookPDFGenerator as generator

        walk = generator.puzzle_pages
        monkeypatch.setattr(
            generator,
            "puzzle_pages",
            lambda self, payloads, *args, **kwargs: walk(
                self, payloads, *args, **kwargs
            )[:-1],
        )

        with pytest.raises(RuntimeError) as raised:
            _interior(
                _book(),
                [_puzzle(*_MIRRORED_PUZZLE, name=f"P{n}") for n in range(3)],
            )

        assert "the page plan prints [1, 2], not puzzles 1..3" in str(raised.value)


class TestBookPdf_UndrawablePuzzleAbortsNamingThePuzzle:
    """A puzzle that will not draw aborts the export, and the raise names it.

    Also an **API-contract** test: no store write path produces a puzzle with
    real clues and no grid today. The contract is deliberate — a page plan
    that no longer describes the file is worse than a refusal — and its price
    is that one bad member stops a whole book, so the owner has to be able to
    tell *which* member from the message alone (a 120-puzzle book offers no
    other way to look).
    """

    def test_interior_pages_raises_and_names_the_puzzle(self):
        puzzles = [
            _puzzle(*_MIRRORED_PUZZLE, name="First"),
            _undrawable_puzzle(),
            _puzzle(*_MIRRORED_PUZZLE, name="Second"),
        ]

        with pytest.raises(RuntimeError) as raised:
            _interior(_book(), puzzles)

        assert "Ghost-undrawable" in str(raised.value)
        assert raised.value.__cause__ is not None, "the original failure is kept"

    def test_the_export_route_sees_the_same_named_failure(self):
        """``export_book`` is what the routes call; the id survives to there."""
        book = _book()
        puzzles = [_puzzle(*_MIRRORED_PUZZLE), _undrawable_puzzle()]

        with pytest.raises(RuntimeError) as raised:
            BookPDFGenerator(book).export_book(puzzles, book.metadata.title)

        assert "Ghost-undrawable" in str(raised.value)

    # A row can also fail *before* any page is drawn, when the pairing walk
    # (CARD-127) offers it to COMP-007's pair-aware call and the measurement
    # itself refuses it. Whether a given malformed row takes that path is
    # decided by its neighbour's tier — and since INV-009 groups the book order
    # by tier, almost every member has a same-tier neighbour — so the contract
    # this class states is only kept if the layout stage names the puzzle too.
    # It did not: the four cases below raised a bare ``ValueError`` reading
    # "first: clue sets disagree about the grid", naming no puzzle and keeping
    # no cause, in exactly the two cases a real book most often produces.

    def test_a_pair_that_cannot_be_laid_out_names_the_malformed_member(self):
        """The finding's own case: a malformed row with a same-tier neighbour."""
        puzzles = [
            _unmeasurable_puzzle(),
            _puzzle(*_MIRRORED_PUZZLE, name="Second"),  # easy, as the row is
        ]

        with pytest.raises(RuntimeError) as raised:
            _interior(_book(), puzzles)

        message = str(raised.value)
        assert "Half-unmeasurable" in message, message
        assert "could not be laid out" in message, message
        assert isinstance(raised.value.__cause__, ValueError), "the original failure is kept"

    def test_the_second_member_of_the_pair_is_named_too(self):
        """The malformed row *after* a good one: "second: ..." named neither a
        puzzle nor a position, so the id is the only handle there has ever been."""
        puzzles = [
            _puzzle(*_MIRRORED_PUZZLE, name="First"),
            _unmeasurable_puzzle(),
        ]

        with pytest.raises(RuntimeError) as raised:
            _interior(_book(), puzzles)

        message = str(raised.value)
        assert "Half-unmeasurable" in message, message
        assert "could not be laid out" in message, message

    @pytest.mark.parametrize(
        "neighbour_tier",
        [pytest.param(None, id="alone"), pytest.param("hard", id="different-tier")],
    )
    def test_the_same_row_is_named_whatever_neighbour_it_has(self, neighbour_tier):
        """The other half of the consistency: a row with no same-tier neighbour
        never reaches the pair call and is named at draw time instead. Both
        stages abort, both name the id — which is the whole contract."""
        puzzles = [_unmeasurable_puzzle()]
        if neighbour_tier is not None:
            neighbour = _puzzle(*_MIRRORED_PUZZLE, name="Other")
            neighbour["difficulty_tier"] = neighbour_tier
            puzzles.append(neighbour)

        with pytest.raises(RuntimeError) as raised:
            _interior(_book(), puzzles)

        assert "Half-unmeasurable" in str(raised.value)
        assert raised.value.__cause__ is not None, "the original failure is kept"

    # CARD-225 review cycle 1, F-002. The editor's page-count entry
    # (``puzzle_page_plan``, CARD-251) asks the same walk for the same book,
    # and since CARD-225 it settles the book's cell map first — so the map's
    # own fail-closed ValueError reached it ahead of the walk, bare: a
    # ``ValueError`` with no cause, no id and no position, for all three
    # neighbour shapes at once, although this class's contract and that
    # function's own ``Raises:`` block both say the abort names the member.
    # The "alone" shape below exists on no earlier tree at all: before this
    # card it reached neither stage from this entry and planned fine.

    @pytest.mark.parametrize(
        "neighbour_tier",
        [
            pytest.param("easy", id="same-tier"),
            pytest.param(None, id="alone"),
            pytest.param("hard", id="different-tier"),
        ],
    )
    def test_the_editors_page_count_names_the_member_whatever_neighbour_it_has(
        self, neighbour_tier
    ) -> None:
        """``puzzle_page_plan`` aborts named, for every neighbour shape."""
        puzzles = [_unmeasurable_puzzle()]
        if neighbour_tier is not None:
            neighbour = _puzzle(*_MIRRORED_PUZZLE, name="Other")
            neighbour["difficulty_tier"] = neighbour_tier
            puzzles.append(neighbour)

        with pytest.raises(RuntimeError) as raised:
            puzzle_page_plan(_book(), puzzles)

        message = str(raised.value)
        assert "Half-unmeasurable" in message, message
        assert "could not be laid out" in message, message
        assert isinstance(raised.value.__cause__, ValueError), (
            "the original failure is kept"
        )
        # The good neighbour is not accused of the bad one's fault.
        assert "Other" not in message, message

    def test_an_unreadable_print_specification_is_the_books_own_failure(self) -> None:
        """F-006/F-001: a book-level fault stays a bare ``ValueError``, naming no member.

        ``cell_sizes`` reads the book's sheet, so a book whose stored trim is
        unreadable could in principle arrive at the per-puzzle handler above
        and come back out as
        ``RuntimeError("puzzle <every member> could not be laid out: ...")`` —
        120 numbers for a failure that belongs to none of them. It cannot,
        and what stops it is **`BookPDFGenerator.__init__`**: its
        ``page_frame(self.page_spec(1))`` lays the sheet out when the
        generator is built, before either entry has a payload to measure, so
        an unreadable specification is refused with the bare ``ValueError``
        the failure matrix's row F-3b declares (CARD-225 review cycle 2,
        F-001).

        **What this test discriminates, measured.** The constructor's read:
        make that line fall back to a default sheet instead of raising and
        the ``puzzle_page_plan`` call below reaches the cell map and raises
        the per-puzzle ``RuntimeError`` this test forbids. It does **not**
        discriminate the two sheet pre-reads fix cycle 1 added to the entries
        themselves — deleting either one failed nothing, which is F-001; the
        dead one is deleted and the other claims nothing about its position.
        """
        book = _book()
        book.trim_width_cm = "abc"
        puzzles = [
            _puzzle(*_MIRRORED_PUZZLE, name="First"),
            _puzzle(*_MIRRORED_PUZZLE, name="Second"),
        ]

        for call in (
            lambda: puzzle_page_plan(book, puzzles),
            lambda: BookPDFGenerator(book).section_plan(puzzles),
        ):
            with pytest.raises(ValueError) as raised:
                call()
            message = str(raised.value)
            # Exactly ``ValueError``, not a subclass of it: the per-puzzle
            # abort this must not be is a ``RuntimeError``, which
            # ``pytest.raises(ValueError)`` would already have let through,
            # so asserting `not isinstance(..., RuntimeError)` inside this
            # block asserted nothing at all (review cycle 2, F-005).
            assert type(raised.value) is ValueError, message
            assert "trim_width_cm" in message, message
            assert "could not be laid out" not in message, message
            assert "First" not in message and "Second" not in message, message


class TestBookPdf_PageFrameNeedsABookPageSpec:
    """``page_frame`` refuses a spec with no parity, rather than reading None.

    ``DEFAULT_PAGE_SPEC`` is imported only as *a spec that is not a book
    page* — nothing here derives a measurement from it, so the module's
    independence from ``compute_layout``/``book_page_spec`` is untouched.
    """

    def test_a_spec_without_parity_is_refused(self):
        with pytest.raises(ValueError) as raised:
            page_frame(DEFAULT_PAGE_SPEC)

        assert "book_page_spec" in str(raised.value)


# --------------------------------------------------------------------------
# The extents the ACs are stated over are the supported ones
# --------------------------------------------------------------------------


def test_the_measured_extents_are_inside_con_011() -> None:
    """Every extent above is a grid the tool supports (CON-011), so none of
    these numbers describes a puzzle that could not exist."""
    for columns, rows, _ in ((30, 30, 9), (15, 15, 7), (30, 15, 5), (20, 20, 6)):
        assert MIN_SIZE <= columns <= MAX_SIZE
        assert MIN_SIZE <= rows <= MAX_SIZE


# --------------------------------------------------------------------------
# ADR-0042/R5 — the interior's face (CARD-294, AC-1)
# --------------------------------------------------------------------------


def test_the_interior_embeds_the_projects_own_face() -> None:
    """AC-1 / ADR-0042/R5 — the node id that rule's check now names.

    Until this card, R5's check was ``{kind: review-lens}`` with this test's
    name written in a comment beside it, as a placeholder for the card that
    would write the font embedding. CARD-294 is that card, so the lens is
    flipped to ``{kind: test, ref: …}`` pointing here, in the same change —
    a lens left in place after its delivery card merges is a rule that
    quietly stopped being verified.

    Three claims, because R5 makes three:

    * the face is **embedded**, and the embedded bytes are *this repository's*
      ``src/nonogram/export/fonts/DejaVuSans.ttf`` — compared byte for byte,
      so a different build of DejaVu, a subset, or a table-stripped sfnt all
      fail here;
    * it is embedded **exactly once per file**, not once per page — the
      interior writes three font objects however many pages show text (the
      slope across page counts is
      ``PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts``'s);
    * and **no base-14 face is referenced**, which is the half R5 states as a
      prohibition. Every ``/BaseFont`` the file names is checked against the
      fourteen, rather than only the one this writer sets, because the
      prohibition is about the file and not about one object.

    The face bytes are read here through :mod:`importlib.resources` — the
    same mechanism the writer uses and the one ``export/pdf.py`` and
    ``export/png.py`` publish — rather than by a filesystem path, so this test
    does not become the second place that knows where the file lives.
    """
    on_disk = (
        resources.files(export_pdf.FONT_PACKAGE)
        .joinpath(export_pdf.FONT_RESOURCE)
        .read_bytes()
    )
    assert on_disk[:4] == b"\x00\x01\x00\x00", "that is not a TrueType file"

    pages = []
    for index in range(3):
        sheet = book_vector.ContentStream(width_px=600, height_px=600, dpi=300)
        sheet.text(f"Puzzle {index + 1} · Easy", 20, 40, 10.0)
        pages.append(sheet)
    data = book_vector.write_vector_pdf(pages, len(pages)).getvalue()

    embedded = pdf_vector.embedded_faces(data)
    assert len(embedded) == 1, f"{len(embedded)} faces in a three-page interior"
    assert embedded[0] == on_disk

    names = pdf_vector.base_font_names(data)
    assert names == [book_vector.FACE_BASE_FONT], names
    assert not set(names) & book_vector.BASE_14_FACES, names
    # And the prohibition stated over the whole file, not only its font
    # objects: a base-14 name cannot appear anywhere in the bytes. The
    # embedded face is Flate-compressed, so its own internal `name` table
    # cannot smuggle one of these in uncompressed.
    for forbidden in sorted(book_vector.BASE_14_FACES):
        assert f"/{forbidden}".encode("ascii") not in data, forbidden


def test_the_face_check_above_can_fail() -> None:
    """Control for AC-1: each of its three claims, broken on purpose.

    ADR-0039/R1 — a claim needs a control that can fail. Without this, a
    reader cannot tell "the face is embedded once and is ours" from "the
    reader returned an empty list".
    """
    sheet = book_vector.ContentStream(width_px=600, height_px=600, dpi=300)
    sheet.text("Puzzle 1", 20, 40, 10.0)

    # A different face: still exactly one, still not base-14, and the byte
    # comparison is what catches it.
    other = (
        resources.files(export_pdf.FONT_PACKAGE)
        .joinpath(export_pdf.FONT_RESOURCE)
        .read_bytes()
    )
    swapped = book_vector.write_vector_pdf(
        [sheet], 1, face_bytes=other[:-4] + b"XXXX", metrics=book_vector.interior_face_metrics()
    ).getvalue()
    faces = pdf_vector.embedded_faces(swapped)
    assert len(faces) == 1
    assert faces[0] != other, "the byte comparison would not notice a changed face"

    # And the reader is not simply returning nothing: the real file has one.
    real = book_vector.write_vector_pdf([sheet], 1).getvalue()
    assert pdf_vector.embedded_faces(real) == [other]


# ==========================================================================
# CARD-298 — the medium is chosen per page, and every bitmap page is declared
# ==========================================================================
#
# ADR-0042/R1 (no interior page references an image XObject) and R2 (a raster
# page is declared with a reason; an expired declaration is a defect). Both
# were shipped as ``review-lens`` on 2026-10-25 because their tests did not
# exist; the two node ids below are the tests their comments name.
#
# **Everything here classifies a page off the WRITTEN FILE**, never off the
# plan that asked for it: the plan is what the guard is checking, so a guard
# that read the plan would be comparing the plan with itself. The one thing
# taken from the plan is the list of page *kinds* — which is the question
# "what medium should this page have been?" and has no other source.


#: How one page of a written PDF was drawn, as classified from its own
#: ``/Resources``. :data:`_UNCLASSIFIABLE` is the third value and it is the
#: whole of ADR-0039/R2 in this file: a page that is neither is a **failure**,
#: not a page quietly counted as whichever the walk reached first.
#:
#: CARD-299 moved the three values and the classification itself into
#: ``tests/helpers/pdf_vector``, because ADR-0042/R6's readers live in several
#: modules and all of them have to ask one file the same question. These names
#: are kept pointing at them rather than retired: this module spells
#: ``_RASTER`` in a dozen assertions, and a rename would be a diff about
#: spelling in the middle of a card about readers.
_RASTER = pdf_vector.RASTER
_VECTOR = pdf_vector.VECTOR
_UNCLASSIFIABLE = pdf_vector.UNCLASSIFIABLE


def _page_media(data: bytes) -> list[str]:
    """Each page of ``data``, classified by medium — default-DENY.

    A page is :data:`_RASTER` iff its resources name an ``/XObject`` and no
    ``/Font``, and :data:`_VECTOR` iff they name a ``/Font`` and no
    ``/XObject``. **Both, or neither, is :data:`_UNCLASSIFIABLE`** — there is
    no third medium in this project and no fallback: a page shaped like
    nothing this writer emits is a page nobody has classified, which
    ADR-0039/R2 makes a failure rather than a pass.

    The two keys are read through
    :func:`tests.helpers.pdf_vector.page_resource_keys`, which decodes
    ``PdfName`` keys to strings for the reason its own docstring gives: a
    ``bytes``-keyed membership test on a ``PdfName``-iterating dictionary
    reads ``False`` silently, which is exactly how "this page carries no image
    XObject" would pass without being true.

    A **vector page with no ink at all still names the face** — every page
    :func:`~nonogram.admin.book_vector.write_vector_page` writes does — so the
    blank title page's vector twin classifies as :data:`_VECTOR` and not as
    unclassifiable. That is measured by
    ``test_a_vector_page_with_no_operators_is_still_classified_vector``, not
    assumed.

    **CARD-299 moved the body to**
    :func:`tests.helpers.pdf_vector.page_media` **and left this call here.**
    Not an indirection for its own sake: ADR-0042/R6's conversion gives the
    same question to readers in three other modules, and this classification
    is the one place "what medium is this page" is answered — a second copy is
    how two readers of one file would come to disagree about it.
    """
    return pdf_vector.page_media(data)


def _declaration_findings(media_by_kind) -> list[str]:
    """Every way the media a file actually used disagree with the declarations.

    The **one** implementation of ADR-0042/R2's rule, driven by AC-2 over a
    file with no defect in it and by AC-2's two mutants and AC-3 over files
    that do have one — so the live assertion and its controls cannot be
    checking two different rules.

    ``media_by_kind`` maps each :class:`~nonogram.admin.book_pdf_generator.PageKind`
    **the file actually held a page of** to the set of media its pages were
    written in. A kind the file held no page of is not judged: the file is the
    authority here, and a kind off this page plan has nothing to say about
    this file. (That is why the expiry clause below is a statement about a
    kind that *is* present — see AC-3.)

    The four findings, and each is a direction something can be wrong in:

    1. **an unclassifiable page** — :func:`_page_media` could not tell which
       medium it is, so nothing below can be true of it;
    2. **a raster page with no declaration** — ADR-0042/R1's violation, the
       one the rule exists for;
    3. **a declaration whose reason has expired** — the kind is declared a
       bitmap and the file wrote it as operators, which is the day CARD-231
       lands and the divider's entry is left behind (R2's own clause);
    4. **a declaration that states no reason, no authority, or an expiry that
       is not a card id** — a declaration is only a declaration if it says
       why, on whose authority, and who removes it.
    """
    findings: list[str] = []
    for kind in sorted(media_by_kind, key=lambda k: k.value):
        media = set(media_by_kind[kind])
        declaration = _RASTER_DECLARATIONS.get(kind)
        if _UNCLASSIFIABLE in media:
            findings.append(f"{kind.value}: a page whose medium cannot be determined")
        if _RASTER in media and declaration is None:
            findings.append(f"{kind.value}: a raster page with no declaration")
        if declaration is not None and _RASTER not in media:
            findings.append(
                f"{kind.value}: a declaration whose reason has expired — the "
                f"page is written {sorted(media)} and the declaration says "
                f"raster ({declaration.expires_with or 'permanent'})"
            )
        if declaration is not None:
            if not declaration.reason.strip():
                findings.append(f"{kind.value}: a declaration with no reason")
            if not declaration.authority.strip():
                findings.append(f"{kind.value}: a declaration with no authority")
            for card in declaration.expires_with:
                if re.fullmatch(r"CARD-\d+", card) is None:
                    findings.append(
                        f"{kind.value}: {card!r} is not a card id, so nobody "
                        "owns removing this declaration"
                    )
    return findings


def _interior_with_every_page_kind():
    """A book whose interior holds a page of every kind the plan can produce.

    Three easy puzzles on Book 1's trim: the blank title page, the two guide
    pages, one TOC page, the "Easy" divider, the puzzle pages, the SOLUTIONS
    divider and the answer pages. Returned as ``(generator, puzzles)`` so each
    caller walks the plan itself — ``interior_stream`` is single-use.
    """
    book = _book()
    puzzles = [_puzzle(10, 10, 3, name=f"P{index}") for index in range(3)]
    return BookPDFGenerator(book), puzzles


def _media_by_kind(generator, puzzles) -> tuple[dict, tuple, list[str]]:
    """``(media_by_kind, page_kinds, media)`` for one book's written interior.

    The pages are enumerated from the **page plan**
    (:attr:`~nonogram.admin.book_pdf_generator.InteriorStream.page_kinds`) and
    the media from the **file**, and the two are zipped ``strict=True`` so a
    plan that does not describe the file is a failure rather than a short walk.
    """
    kinds = generator.interior_stream(puzzles).page_kinds
    data = generator.export_interior(puzzles).getvalue()
    media = _page_media(data)
    by_kind: dict = {}
    for kind, medium in zip(kinds, media, strict=True):
        by_kind.setdefault(kind, set()).add(medium)
    return by_kind, kinds, media


def test_no_interior_page_carries_an_image_xobject() -> None:
    """AC-1 (ADR-0042/R1) — no page of a vector kind references an image.

    **Derived over the page plan, not over a written list.** The kinds come
    from ``interior_stream``'s own plan, the media from the file, and the two
    are compared page by page; the assertion is an **equivalence** in both
    directions, so a page written as operators under a raster declaration reds
    here exactly as a bitmap under a vector one does.

    Default-DENY twice over: a page :func:`_page_media` cannot classify fails,
    and a kind :func:`~nonogram.admin.book_pdf_generator.page_medium` refuses
    fails (it raises on anything that is not a
    :class:`~nonogram.admin.book_pdf_generator.PageKind`).

    **What this measures today, stated plainly.** Every interior kind is
    still declared raster at this commit — see :data:`_RASTER_DECLARATIONS`,
    whose five temporary entries name their blockers and now all name
    CARD-322 — so the *vector* arm of the equivalence is not exercised by
    production's own default. It is exercised, through production's own
    writer, by
    :func:`test_no_interior_page_carries_an_image_xobject_in_a_mixed_file`
    below, which lifts one declaration and watches a real mixed-media interior
    come out, and by
    :class:`TestAssemblyPoint_TheDownstreamWritersAreReachable`, which lifts
    **all five** and watches a wholly vector interior come out. Without those
    companions this test would be a true sentence about a file with no vector
    page in it.

    The expectation is read off :func:`page_medium` per page and is
    deliberately **not** a list of which kinds are vector: the registry is the
    authority (ADR-0042/R2), and a kind list here would be a second opinion
    about the medium that goes stale the next time one converts.
    """
    generator, puzzles = _interior_with_every_page_kind()
    by_kind, kinds, media = _media_by_kind(generator, puzzles)

    assert _UNCLASSIFIABLE not in media, [
        (index + 1, kinds[index].value)
        for index, medium in enumerate(media)
        if medium == _UNCLASSIFIABLE
    ]
    # The plan really does cover every kind an interior can hold, so the
    # equivalence below is swept over all of them rather than over whichever
    # this book happened to produce.
    assert set(by_kind) == {
        PageKind.TITLE,
        PageKind.GUIDE,
        PageKind.TOC,
        PageKind.DIVIDER,
        PageKind.PUZZLE,
        PageKind.ANSWER,
    }, sorted(kind.value for kind in by_kind)

    for index, (kind, medium) in enumerate(zip(kinds, media, strict=True), start=1):
        expected = (
            _RASTER if page_medium(kind) is PageMedium.RASTER else _VECTOR
        )
        assert medium == expected, (
            f"interior page {index} is a {kind.value} page: its kind declares "
            f"{expected} and the file holds {medium}"
        )


def test_no_interior_page_carries_an_image_xobject_in_a_mixed_file(
    monkeypatch,
) -> None:
    """AC-1's vector arm, driven through production's own writer.

    The declaration registry is the **only** lever that decides a medium, so
    lifting one entry is how a kind goes vector — this is what the day
    CARD-299 lands looks like for the first kind it unblocks. The blank title
    page is chosen because its two media draw the same page by construction
    (white bitmap, empty stream), so nothing a reader sees changes and the
    only difference is the file.

    Both directions are asserted on the same file: page 1 carries the face and
    **no** XObject, and every page whose kind is still declared a bitmap still
    carries one. A mixed file is the point — ADR-0042/R2's "per-page mixing is
    a sanctioned end state" — so a writer that silently converted the whole
    file, or none of it, reds here.

    **The second half is derived, not listed** (CARD-309). It used to read
    ``set(media[1:]) == {_RASTER}``, which was true only while the title page
    was the one undeclared kind; the puzzle page is undeclared now, so the
    expectation for every page after page 1 comes from
    :func:`page_medium` on that page's own kind. Both arms are then asserted
    to be non-empty, so the file really is mixed and neither arm can go quiet
    as the registry shrinks.
    """
    import nonogram.admin.book_pdf_generator as generator_module

    monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.TITLE)
    assert page_medium(PageKind.TITLE) is PageMedium.VECTOR

    generator, puzzles = _interior_with_every_page_kind()
    kinds = generator.interior_stream(puzzles).page_kinds
    data = generator.export_interior(puzzles).getvalue()
    keys = pdf_vector.page_resource_keys(data)
    media = _page_media(data)

    assert kinds[0] is PageKind.TITLE
    assert "XObject" not in keys[0], keys[0]
    assert "Font" in keys[0], keys[0]
    assert media[0] == _VECTOR
    rest = [
        (index + 2, kind.value, medium)
        for index, (kind, medium) in enumerate(
            zip(kinds[1:], media[1:], strict=True)
        )
        if medium
        != (_RASTER if page_medium(kind) is PageMedium.RASTER else _VECTOR)
    ]
    assert rest == [], rest
    # And the file really is mixed, which is this cell's whole subject: page 1
    # is vector (asserted above) and something after it is a bitmap. Asserted
    # as a *membership* rather than as ``set(media[1:]) == {_RASTER}``, which
    # is what it used to be and which would red the day a second kind
    # converts — the assertion above already holds every page to its own
    # kind's declared medium, so this one only has to stop the file from
    # being all of one thing.
    assert _RASTER in set(media[1:]), media
    # The face is embedded once for the file however many pages are vector
    # (ADR-0042/R5), and a raster-only file embeds none — the two halves of
    # the same claim, on two files written by the same call.
    assert len(pdf_vector.embedded_faces(data)) == 1
    # And the other half of ADR-0042/R5's "once per file": with the
    # declaration back, the same call writes a file with **no** face in it at
    # all, so the three font objects are not three unused objects on a
    # raster-only interior.
    monkeypatch.setitem(
        generator_module._RASTER_DECLARATIONS,
        PageKind.TITLE,
        RasterDeclaration(
            reason="restored by this test",
            authority="this test",
            expires_with=("CARD-299",),
        ),
    )
    raster_only = generator.export_interior(
        [_puzzle(10, 10, 3, name=f"R{index}") for index in range(3)]
    ).getvalue()
    assert pdf_vector.embedded_faces(raster_only) == []
    assert set(_page_media(raster_only)) == {_RASTER}


def test_a_vector_page_with_no_operators_is_still_classified_vector(
    monkeypatch,
) -> None:
    """:func:`_page_media`'s own control: an empty stream is not nothing.

    The blank title page's vector twin emits no operator at all, so "a page
    with no ink" is the shape most likely to fall through a classifier. It
    does not: ``write_vector_page`` names the face on every page it writes, so
    the page is :data:`_VECTOR` by the same key every other vector page is.
    Measured here rather than asserted in :func:`_page_media`'s docstring.
    """
    import nonogram.admin.book_pdf_generator as generator_module

    monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.TITLE)
    generator = BookPDFGenerator(_book())
    blank = generator.vector_title_page(1)
    assert blank.operators == (), blank.operators
    data = generator._write_pdf(
        iter([blank]), 1, mode="L", kinds=(PageKind.TITLE,)
    ).getvalue()
    assert _page_media(data) == [_VECTOR]


def test_every_raster_page_is_declared_with_its_reason() -> None:
    """AC-2 (ADR-0042/R2) — every bitmap page matches a live declaration.

    The live assertion is that :func:`_declaration_findings` is **empty** over
    a written interior and a written cover, with the kinds taken from the page
    plan and the media from the files. Three directions red, and each has its
    own control below rather than being argued here:

    * an **undeclared** raster page —
      :func:`test_an_undeclared_raster_page_is_a_defect` (inside the claimed
      region: a puzzle page, the dominant kind);
    * a raster page whose declaration is **removed while it is still a
      bitmap** — :func:`test_a_raster_page_whose_declaration_is_removed_is_a_defect`
      (the claim's **edge**: the divider, exactly the page ADR-0042/R2 names);
    * a page whose medium **cannot be determined** —
      :func:`test_a_page_whose_medium_cannot_be_determined_is_a_defect`.

    The cover is included because it is the one declaration with no expiry,
    and it is written by a different call on a different colour space: a guard
    that only read the interior would never check the one permanent entry.
    """
    generator, puzzles = _interior_with_every_page_kind()
    by_kind, _, _ = _media_by_kind(generator, puzzles)

    cover = generator.export_cover("Winter Pictures").getvalue()
    cover_media = _page_media(cover)
    assert cover_media == [_RASTER], cover_media
    by_kind.setdefault(PageKind.COVER, set()).update(cover_media)

    findings = _declaration_findings(by_kind)
    assert findings == [], findings

    # And the registry is not empty for a reason unrelated to the file: every
    # entry it holds is one of this project's page kinds, so a key that is not
    # a kind at all cannot sit in it unnoticed (`page_medium` would still
    # return VECTOR for the kind it was meant to cover).
    assert set(_RASTER_DECLARATIONS) <= set(PageKind), sorted(
        str(key) for key in _RASTER_DECLARATIONS if key not in set(PageKind)
    )


def test_an_undeclared_raster_page_is_a_defect(monkeypatch) -> None:
    """AC-2's first mutant, **inside** the claimed region: the puzzle page.

    The file is written first, with the puzzle page's declaration in place, so
    what changes is the declaration and not the page — the shape ADR-0042/R1
    is actually about is a bitmap nobody claimed, not a bitmap nobody wrote.
    """
    import nonogram.admin.book_pdf_generator as generator_module

    generator, puzzles = _interior_with_every_page_kind()
    by_kind, _, _ = _media_by_kind(generator, puzzles)
    assert _declaration_findings(by_kind) == []

    monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.PUZZLE)
    findings = _declaration_findings(by_kind)
    assert findings == ["puzzle: a raster page with no declaration"], findings


def test_a_raster_page_whose_declaration_is_removed_is_a_defect(
    monkeypatch,
) -> None:
    """AC-2's second mutant, at the claim's **edge**: the section divider.

    ADR-0042/R2's own second instance, and the one whose declaration is
    *meant* to go away — so the mutant is the mistake that is actually
    plausible: CARD-231's author deletes the entry and leaves the page a
    bitmap. The guard reds on the page, not on the entry, which is the
    direction that catches it.
    """
    import nonogram.admin.book_pdf_generator as generator_module

    generator, puzzles = _interior_with_every_page_kind()
    by_kind, _, _ = _media_by_kind(generator, puzzles)

    monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.DIVIDER)
    findings = _declaration_findings(by_kind)
    assert findings == ["divider: a raster page with no declaration"], findings


def test_a_declaration_whose_reason_expired_is_a_defect(monkeypatch) -> None:
    """AC-3 (ADR-0042/R2's expiry clause) — a stale declaration reds.

    *"Once CARD-231 lands, the divider's exception goes with it."* **Nothing
    else in the tree will notice the day it does not**, which is why this is
    its own criterion: the page is then operators, the declaration still says
    bitmap, and every other assertion in this file is happy.

    Simulated exactly as that day will look, through production's own writer:
    the divider's declaration is lifted so the medium rule makes the page
    vector, a divider page is written as a content stream, and the declaration
    is then put back — which is the commit that forgets to delete it. The
    guard reds on the **direction nobody tests for**: declared raster, written
    vector.
    """
    import nonogram.admin.book_pdf_generator as generator_module

    generator = BookPDFGenerator(_book())

    # CARD-231 has landed: the divider's exception is gone and its page is
    # born vector, which `page_medium` now says and `_write_pdf` now demands.
    monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.DIVIDER)
    assert page_medium(PageKind.DIVIDER) is PageMedium.VECTOR
    frame = page_frame(generator.page_spec(5))
    divider = book_vector.ContentStream(
        width_px=frame.width, height_px=frame.height, dpi=generator.dpi
    )
    divider.text("Easy", 100.0, 200.0, 24.0)
    data = generator._write_pdf(
        iter([divider]), 1, mode="L", kinds=(PageKind.DIVIDER,)
    ).getvalue()
    media = _page_media(data)
    assert media == [_VECTOR], media
    # With the exception correctly deleted, nothing is wrong.
    assert _declaration_findings({PageKind.DIVIDER: set(media)}) == []

    # And now the defect: the same page, with the declaration left behind.
    monkeypatch.setitem(
        generator_module._RASTER_DECLARATIONS,
        PageKind.DIVIDER,
        RasterDeclaration(
            reason=(
                "CARD-231 replaces the divider page outright, so the new "
                "design can be born vector instead"
            ),
            authority="owner decision 2026-10-25, recorded in ADR-0042/R2",
            expires_with=("CARD-231",),
        ),
    )
    findings = _declaration_findings({PageKind.DIVIDER: set(media)})
    assert len(findings) == 1, findings
    assert findings[0].startswith(
        "divider: a declaration whose reason has expired"
    ), findings


# --------------------------------------------------------------------------
# AC-3's OTHER direction — the landing direction (CARD-298 fix round 1)
# --------------------------------------------------------------------------
#
# Review cycle 1's F-002. The expiry finding in :func:`_declaration_findings`
# fires only on ``declaration is not None and _RASTER not in media`` — only
# when a page's medium actually **changed**. ADR-0042/R2's own clause is
# written in the other direction: *"once CARD-231 lands, the divider's
# exception goes with it"*. Measured on the branch: ``expires_with`` was read
# in exactly two places in the whole tree — the finding's message text and a
# ``re.fullmatch(r"CARD-\d+")`` FORMAT check — and **nothing read a card's
# status**, so a declaration went silently stale on the day its own expiry
# card landed. That is the direction below, and it is a **new coupling from
# ``tests/`` to the kanban board**, built deliberately rather than inherited.


#: The board's whole status vocabulary: the statuses ``forge:kanban``'s card
#: format defines, plus ``parked``, which this board uses and the format does
#: not. Only ``done`` and ``skipped`` are terminal (see
#: :data:`_TERMINAL_STATUSES`).
#:
#: **DERIVED FROM THE FORMAT, NOT FROM A SNAPSHOT OF THE BOARD — and that
#: correction cost a red ``main``.** This set was first derived on 2026-10-29
#: "by reading every card in the main working tree", and on that day the board
#: had **no card in flight** (wave 68 closed with none), so no card file
#: carried an in-flight status at all. What went in instead was
#: ``"in progress"`` **with a space** — the spelling of ``board.md``'s
#: ``## In Progress`` heading, not of any ``**Status:**`` field. The pipeline
#: writes ``in_progress``. Measured 2026-10-30, the moment wave 69 dispatched
#: two cards: :func:`test_no_declaration_outlives_the_cards_that_remove_it`
#: failed on ``main`` with ``['CARD-268', 'CARD-309']``, because
#: :func:`_card_status` returned the default-DENY ``None`` for a spelling it
#: had never been given. The guard was right and its vocabulary was wrong.
#:
#: Two consequences are now load-bearing and are why this is written out:
#:
#: * ``in_progress`` and ``review`` are the two statuses a card holds **while
#:   a human is waiting for it**, so they are exactly the ones a status set
#:   derived from an idle board cannot contain. ``review`` has never appeared
#:   on this board (`board.md`'s Review column says so of the field, not of
#:   the pipeline) and is included anyway: the next card to reach its review
#:   phase would otherwise red ``main`` a second time, for the same reason, on
#:   a different word.
#: * ``"in progress"`` is **gone**, not kept as an alias. 126 historical cards
#:   carried it and **none in the live tree does**; keeping a spelling that
#:   cannot occur is what let the synthetic control below exercise an
#:   impossible case while the real one went unguarded (see
#:   ``CARD-90003``).
#:
#: ``reverted`` is deliberately **absent**. The format defines it, no card has
#: ever carried it, and its terminality is a real question (a reverted card's
#: work is rolled back, so a declaration naming one arguably waits forever —
#: like ``skipped``). An unanalysable shape is a FAILURE here per ADR-0039/R2,
#: so the first revert on this board will red this guard rather than be read
#: as "not done" — which is the correct, loud outcome, and the decision gets
#: made then with a case in hand instead of now with none.
#:
#: **No per-status counts are written here, and that is deliberate:**
#: the ones this comment first carried were already two cells out within the
#: day (``done`` and ``ready`` both moved when CARD-291 merged and CARD-308
#: started), which is the drift :mod:`tests/test_cli.py`'s component map and
#: CARD-261 were built to stop — and which the comment a hundred lines below
#: refuses for the same reason. The **set** is the load-bearing claim and it is
#: mechanically pinned by
#: :func:`test_no_declaration_outlives_the_cards_that_remove_it`, which
#: requires every card on the board to have a readable status, so an eighth
#: spelling reds rather than drifting. An **eighth** spelling is an unanalysable shape, which
#: ADR-0039/R2 makes a failure here rather than a card quietly read as
#: not-done — the direction that cannot ship a false green.
#:
#: **RE-DERIVED 2026-10-30 (CARD-309), and one spelling was wrong.** The set
#: first written here held ``"in progress"`` with a SPACE. No card on the board
#: has ever carried that spelling: the dispatcher writes ``in_progress`` with
#: an underscore, which nothing could observe on 2026-10-29 because the board
#: had **no card in flight** that day (``acd0a386``: *"wave 68 closes with no
#: card in flight"*). Wave 69 opened two — and both of them reded this cell at
#: once, exactly as the paragraph above promises a new spelling will, on a
#: branch whose own diff had not touched the registry. The space form was
#: retracted rather than kept beside the real one (ADR-0039/R4): a vocabulary
#: carrying a spelling the board does not use is a set that cannot be checked
#: against anything, and it was the half doing no work.
#:
#: **CORRECTED 2026-10-30, CARD-309 fix round 1 (its review's F-004): this
#: note now records a correction that is already landed, not an edit the
#: branch makes.** CARD-309's round wrote these lines while it carried the
#: widening; its rebase then resolved this file in ``main``'s favour, because
#: ``main``'s set is a strict superset — it had added ``in_progress`` **and**
#: ``review`` and dropped the dead space form. So the diff no longer changes
#: :data:`_BOARD_STATUSES` at all, and two sentences written for the other
#: state survived it: one claimed ``in_progress`` *joins* the vocabulary here
#: (it was already in), and one wrote out the vocabulary as **six** spellings
#: while the frozenset below holds **seven**. Both are gone. The widening is
#: ``main``'s; what this file carries is the paragraph explaining it.
#:
#: **``in_progress`` is in the vocabulary and deliberately NOT in**
#: :data:`_TERMINAL_STATUSES` — a card in flight is the most open a card gets,
#: so a declaration naming one stays alive. The control for that arm is
#: :func:`test_a_declaration_outliving_its_done_card_is_a_defect`'s
#: ``CARD-90003``, which is written in this spelling for that reason.
#:
#: **And the vocabulary is still not re-stated in prose, for the reason the
#: paragraph above gives.** The six-spelling list was exactly the drift it
#: warns about: it omitted a spelling two cards carry today (``review`` —
#: CARD-309 itself is one of them) and asserted one that no card in the live
#: tree carries. The **set** is the claim, it is the frozenset below, and it is
#: mechanically pinned by
#: :func:`test_no_declaration_outlives_the_cards_that_remove_it`, which
#: requires every card on the board to have a readable status — so a spelling
#: outside it reds instead of drifting, whichever direction the board moves.
#:
#: **This is a finding about the board's own gate, not about CARD-309.** The
#: cell's verdict is a function of the main working tree's card directory (see
#: :func:`_board_cards`), so dispatching *any* card to *any* worktree reds
#: every in-flight branch until the spelling is known here. That is CARD-310's
#: subject — "a card's *name* is a structural fact that may be walked from
#: ``tests/``, a card's *status* is a board-time fact that may not" — and
#: nothing here is the hoist.
_BOARD_STATUSES = frozenset(
    {"done", "ready", "in_progress", "review", "blocked", "parked", "skipped"}
)
_DONE = "done"

#: The statuses a card never leaves, so a declaration naming only such cards
#: has nobody left to remove it. ``done`` is the obvious one; ``skipped`` is
#: here because forge:kanban's own ``skip`` command defines it as unblocking
#: dependents **"as if the dependency were done"** — a skipped card is a card
#: that will not be built, and a declaration waiting on one waits forever.
#:
#: Added 2026-10-29, when ``skipped`` first appeared on this board (CARD-307,
#: cut after a fourth premise re-measurement) and this file's tripwire reded on
#: the sixth spelling exactly as its docstring promised. The tripwire is why
#: the status was extended **deliberately** rather than discovered later: a
#: parser that silently read ``skipped`` as "not done" would have kept every
#: declaration naming it alive forever, which is the false-green direction this
#: guard exists to refuse. Widening ``_BOARD_STATUSES`` alone would have opened
#: exactly that hole, so the two changes are one change.
#:
#: No declaration names a skipped card at HEAD, so this set's effect is
#: unobservable over the real board and is proved only by
#: :func:`test_a_declaration_outliving_its_done_card_is_a_defect` over its
#: synthetic one — which is the division of labour the live cell's docstring
#: already describes.
_TERMINAL_STATUSES = frozenset({"done", "skipped"})

#: ``**Status:** <value>`` on a line of its own, which is how every card on
#: this board writes it (asserted, not counted — see above). Parsed with a regex and not a YAML library because
#: there is no YAML parser in the dependency baseline (ADR-0006/R1) and the
#: shape being read is one line — the precedent CARD-291 set for exactly this.
_CARD_STATUS = re.compile(r"^\*\*Status:\*\*[ \t]*(\S.*?)[ \t]*$", re.MULTILINE)


def _board_cards() -> pathlib.Path:
    """``meta/kanban/cards`` of the **main working tree**, not of this checkout.

    A card worktree does not carry board updates — this board's ``/commit``
    excludes ``meta/`` — so a linked worktree's ``meta/kanban/cards`` is a
    snapshot of whatever commit the branch was cut from, and a card cut *after*
    that cut is simply absent from it. **Measured on this very branch**: the
    worktree's board holds 304 card files and the main working tree's holds
    308, and ``CARD-309`` — the card all five interior declarations now name —
    is one of the four it is missing. Reading the snapshot would make "the
    board has never heard of this card" (the ``expires_with`` typo case, the
    one the format regex cannot catch) indistinguishable from "this checkout
    is older than the card", and the first of those must red.

    The walk from a linked worktree back to the main checkout is **not
    re-implemented here**: ``tests/full_suite_lock.main_repo_root`` already
    does it, for the same reason stated in its own docstring ("a linked
    worktree has to follow its ``.git`` file back there"), it is driven by
    ``tests/test_full_suite_lock.py``'s own synthetic-worktree cells, and a
    second transcription of a path walk is how the two would come to disagree.
    **What that redirection costs, stated because review cycle 2 measured it
    and the sentence here used to deny it.** The retired claim was that in an
    ordinary checkout ``main_repo_root`` returns the checkout itself "so CI and
    a fresh clone see no difference". That is true of the *return value* and
    **false of this test's verdict**: imposing ordinary-checkout semantics on
    this worktree (``main_repo_root = lambda worktree: worktree``, which is the
    documented fall-through when ``.git`` is a directory) makes
    :func:`test_no_declaration_outlives_the_cards_that_remove_it` **red** with
    ``Left contains one more item: 'CARD-309'`` — measured, from an out-of-tree
    plugin, with the instrument first proven on the unmutated tree. So the
    "no difference" case is precisely the case that fails.

    The honest property, which a reader should have instead: **this cell's
    verdict is a function of the main working tree's card directory, not of a
    commit.** Marking ``CARD-309`` done on ``main`` reds this branch with no
    commit made to this branch. Three things keep that from being a defect
    today rather than a design to like — it is a false RED and never a false
    green; the merge gate runs from the main worktree; and a fresh clone of
    ``main`` carries every card, so it is green there. **This repo has no CI**
    (no ``ci/``, no ``.github/``), so that half is latent rather than broken.
    The direction worth taking is to hoist this check into the board's own
    gate, where the board is the subject rather than a neighbour — not a
    conditional skip, which would be an ungated door.
    """
    return full_suite_lock.main_repo_root(
        pathlib.Path(__file__).resolve().parent.parent
    ) / "meta" / "kanban" / "cards"


def _card_status(card: str, cards: pathlib.Path) -> str | None:
    """``CARD-NNN``'s status on the board, or ``None`` when it is undeterminable.

    ``None`` is the **default-DENY** value and every caller below turns it
    into a finding. Five shapes produce it, and ADR-0039/R2 is why none of
    them is a pass:

    #. the card file is **absent** — the ``expires_with`` typo case, which
       ``re.fullmatch(r"CARD-\\d+")`` cannot catch because ``CARD-9999`` is a
       perfectly well-formed id for a card nobody ever cut;
    #. it cannot be read (permissions, a directory of that name, bad UTF-8);
    #. it carries **no** ``**Status:**`` line;
    #. it carries **more than one**, so which one is the status is a guess;
    #. its status word is outside :data:`_BOARD_STATUSES` — an eighth
       spelling on the board reds here instead of being read as "not done",
       because "not done" is the answer that ships a stale declaration.
       Measured 2026-10-30: this is the shape that reds, and the vocabulary
       was the thing at fault, not the board (see :data:`_BOARD_STATUSES`).

    Kept out of the assertions on purpose, so
    :func:`test_a_declaration_outliving_its_done_card_is_a_defect` can drive
    it over a **synthetic** board and prove it discriminates: at HEAD no
    declaration is stale, so a test asserting over the real board would pass
    whatever this returned, ``return None``/``return "ready"`` included.
    """
    try:
        text = (cards / f"{card}.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    found = _CARD_STATUS.findall(text)
    if len(found) != 1:
        return None
    return found[0] if found[0] in _BOARD_STATUSES else None


def _landing_findings(declarations, cards: pathlib.Path) -> list[str]:
    """Declarations that have outlived the cards named to remove them.

    The **one** implementation of the landing direction, driven by
    :func:`test_no_declaration_outlives_the_cards_that_remove_it` over the real
    registry and the real board and by
    :func:`test_a_declaration_outliving_its_done_card_is_a_defect` over a
    synthetic board — so the live assertion and its control cannot be checking
    two different rules (the shape :func:`_declaration_findings` already uses).

    Two findings, and each is a direction something can be wrong in:

    #. **a card whose status the board cannot give** — nobody can be shown to
       own removing the declaration, so the ``expires_with`` is decoration;
    #. **every card named is ``done`` and the entry is still here** — the
       expiry is the day the *last* of them lands (the field is a tuple
       precisely because a kind can be held by more than one unlanded piece of
       work), so all-done plus still-present is the defect.

    An entry with an **empty** ``expires_with`` is not judged at all: that is
    the cover's permanent exception, which has no expiry to outlive. A
    deny-everything version of this function would claim it, and the control
    checks that it does not.
    """
    findings: list[str] = []
    for kind in sorted(declarations, key=lambda k: k.value):
        named = declarations[kind].expires_with
        if not named:
            continue
        statuses = {card: _card_status(card, cards) for card in named}
        unreadable = sorted(card for card, status in statuses.items() if status is None)
        if unreadable:
            findings.append(
                f"{kind.value}: {unreadable} name no card whose status this "
                "board can give, so nobody can be shown to own removing this "
                "declaration"
            )
            continue
        if all(status in _TERMINAL_STATUSES for status in statuses.values()):
            reached = sorted({str(status) for status in statuses.values()})
            findings.append(
                f"{kind.value}: a declaration outliving its own expiry — "
                f"{sorted(named)} have all reached a terminal status "
                f"({reached}) and the entry is still here"
            )
    return findings


def test_no_declaration_outlives_the_cards_that_remove_it() -> None:
    """AC-3's landing direction, live over the real registry and the real board.

    This is the cell that reds **the day CARD-309 (or CARD-231) is marked
    done** and its declarations are still in :data:`_RASTER_DECLARATIONS`.
    Nothing in the tree did that before CARD-298's fix round 1.

    Three non-vacuity checks first, because this assertion is an *emptiness*
    and emptiness is what a broken derivation also returns:

    #. the registry really does hold temporary entries — a registry of purely
       permanent exceptions would make :func:`_landing_findings` skip
       everything. A floor and not the count, for the reason the comment on it
       gives;
    #. the board really is there and really is the board — at least 300 card
       files;
    #. **every** card on it has a status this file can read, which is the one
       assertion that proves :func:`_card_status` parses rather than returning
       ``None``, and which reds on a sixth status spelling appearing on the
       board (ADR-0039/R2's direction: an unanalysable shape is a failure).

    The discrimination itself — reds on done, stays green on open — is proved
    over a synthetic board by
    :func:`test_a_declaration_outliving_its_done_card_is_a_defect`, because at
    HEAD no declaration is stale and this cell would pass whatever the
    derivation did.
    """
    temporary = {
        kind for kind, entry in _RASTER_DECLARATIONS.items() if entry.expires_with
    }
    # A floor, deliberately NOT the count: the registry is the authority for
    # how many exceptions there are, and a number restated beside the mapping
    # is the drift CARD-261 found twice. All this needs is that there is
    # something to judge, so that an emptiness below means "nothing stale"
    # and not "nothing looked at".
    assert len(temporary) >= 2, sorted(kind.value for kind in temporary)
    assert _RASTER_DECLARATIONS[PageKind.COVER].expires_with == ()

    cards = _board_cards()
    assert cards.is_dir(), cards
    on_the_board = sorted(path.stem for path in cards.glob("CARD-*.md"))
    assert len(on_the_board) >= 300, len(on_the_board)

    statuses = {card: _card_status(card, cards) for card in on_the_board}
    assert [card for card, status in statuses.items() if status is None] == [], [
        card for card, status in statuses.items() if status is None
    ]
    assert sum(1 for status in statuses.values() if status == _DONE) >= 200
    assert sum(1 for status in statuses.values() if status != _DONE) >= 10

    # And every card any declaration names is one the board actually holds --
    # stated separately from the findings below so a typo is read as a typo.
    named = sorted(
        {card for entry in _RASTER_DECLARATIONS.values() for card in entry.expires_with}
    )
    assert named == sorted(set(named) & set(on_the_board)), [
        card for card in named if card not in set(on_the_board)
    ]

    findings = _landing_findings(_RASTER_DECLARATIONS, cards)
    assert findings == [], findings


#: The card whose round wrote this cell, and the one id the registry must not
#: name. Spelled out rather than derived, because what it pins is a decision
#: and not a measurement: see the test below.
_THE_CLOSING_CARD = "CARD-309"
#: The card the five interior declarations were re-pointed at.
_THE_CONVERTING_CARD = "CARD-322"


def test_no_declaration_names_the_card_that_is_closing() -> None:
    """CARD-309's AC-1 half that is bookkeeping, and it is load-bearing.

    :func:`test_no_declaration_outlives_the_cards_that_remove_it` above reds
    the day **every** card an entry names is ``done`` — so an entry still
    naming :data:`_THE_CLOSING_CARD` reds on ``main`` the moment that card is
    marked done, which is the merge gate and not the review. That cell cannot
    be the control for this one: it reads the *board*, and while this card is
    ``in_progress`` it passes with CARD-309 named all over the registry
    (measured — planting ``("CARD-299", "CARD-309")`` back onto an entry
    leaves it green). This is the cell that fails instead.

    **Why the re-point rather than the removal.** CARD-309 built ADR-0042/R1's
    assembly point and measured the reader conversion that is left; the
    measurement is in its Worktree notes and in each entry's ``reason``, and
    it is larger than the card's AC-3 predicted. Its own body sanctions
    exactly this outcome — *"if this card converts only some kinds ... it must
    re-point the surviving entries at whatever card finishes the job, in the
    same commit. Say which, explicitly."* — and
    :data:`_THE_CONVERTING_CARD` is which.

    Both directions, because "names no CARD-309" is also true of a registry
    that names nobody at all.
    """
    named = {
        kind: entry.expires_with
        for kind, entry in _RASTER_DECLARATIONS.items()
        if entry.expires_with
    }
    assert len(named) >= 2, sorted(kind.value for kind in named)
    offenders = sorted(
        kind.value for kind, cards in named.items() if _THE_CLOSING_CARD in cards
    )
    assert offenders == [], offenders
    # And the interior kinds really were re-pointed, so the registry is not
    # merely silent about who removes them. The divider is excluded by name
    # because its expiry is CARD-231's and always was (ADR-0042/R2, G-2).
    interior = {
        kind: cards for kind, cards in named.items() if kind is not PageKind.DIVIDER
    }
    assert len(interior) >= 4, sorted(kind.value for kind in interior)
    unpointed = sorted(
        kind.value
        for kind, cards in interior.items()
        if _THE_CONVERTING_CARD not in cards
    )
    assert unpointed == [], unpointed


class TestRasterDeclarations_TheCommentAgreesWithTheRegistry:
    """F-001's control — the registry's own prose, held to the registry.

    CARD-309's review cycle 1 found two sentences in the ``#:`` comment above
    :data:`~nonogram.admin.book_pdf_generator._RASTER_DECLARATIONS` asserting
    that this card had taken an entry out of the mapping. Re-derived at that
    commit: seven entries, the same seven as ``main``, and ``git diff`` removed
    **none**. The second of the two sentences invoked CARD-261's drift
    precedent as its reason for writing no count, while *being* that drift —
    and the comment nominates this mapping as "the one honest reading of how
    far ADR-0042/R1 has actually got", so the false claim sat on the one thing
    the comment claims is honest.

    A prose fix with no control is the same finding one card later. This board
    has measured that twice (CARD-261: both copies of the component map had
    drifted, in different places), which is why that map's rows were retired to
    a place where a test holds them. These lines get the same treatment.

    **Both directions, because either one alone passes a lie.**

    * a comment claiming a removal the registry cannot show is F-001 itself;
    * a registry that quietly loses an entry while the comment still says
      nothing was taken out is the same defect with the signs swapped — and it
      is the one the *next* card walks into, because CARD-322 is the card that
      converts these kinds, and the day it does, the paragraph it has to
      re-derive is this one.

    :meth:`removal_claims` is a pure function of text, so the guard-the-guard
    cell drives it with strings rather than writing a module into the tree
    (ADR-0039/R1), and the vocabulary is controlled in **both** polarities:
    sentences that must be caught, and legitimate sentences already standing in
    this comment that must not be, so the reading cannot degenerate into a
    substring match on "remove" or "shrink".
    """

    #: Resolved from this file rather than from the working directory, so the
    #: guard reads the same module whatever pytest was invoked from — the same
    #: resolution :class:`TestWritePdf_TheMediumIsChosenInOnePlace` uses.
    MODULE = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "nonogram"
        / "admin"
        / "book_pdf_generator.py"
    )

    #: The assignment whose ``#:`` comment block is the claim under test.
    REGISTRY = "_RASTER_DECLARATIONS"

    #: ``(label, pattern)`` for every way this comment has claimed, or could
    #: claim, that the mapping has already lost an entry. Matched
    #: case-insensitively against the block joined into **one** line, because
    #: the two sentences cycle 1 found were each wrapped across two.
    #:
    #: Written as a vocabulary rather than a bare ``"remov" in text`` because
    #: the comment legitimately contains "CARD-322 is the card that removes
    #: these four" (a FUTURE removal, which is the mapping's whole point), "the
    #: shrink is guarded in two directions", and "CARD-309 removed no entry" —
    #: all three are in :data:`PASSES` below and none may be caught.
    REMOVAL_CLAIMS: tuple[tuple[str, str], ...] = (
        ("n-fewer", r"\b(?:one|two|three|four|five|six|seven|\d+)\s+fewer\b"),
        ("fewer-since", r"\bfewer\s+since\b"),
        ("one-less", r"\bone\s+less\b"),
        (
            "removed-n-entries",
            r"\bremoved\s+(?:one|two|three|four|five|six|seven|an?|another|\d+)"
            r"(?:\s+\w+){0,2}\s+(?:entry|entries|declaration|declarations)\b",
        ),
        (
            "removed-the-entry",
            r"\bremoved\s+(?:this|that|the|its)"
            r"(?:\s+\w+){0,2}\s+(?:entry|entries|declaration|declarations)\b",
        ),
        (
            "entry-is-gone",
            r"\b(?:entry|entries|declaration|declarations)\s+"
            r"(?:is|are|was|were)\s+(?:now\s+)?gone\b",
        ),
        ("shrank", r"\bshr(?:ank|unk)\b"),
        ("no-longer-declared", r"\bno\s+longer\s+declared\b"),
        (
            "entry-was-removed",
            r"\b(?:entry|entries|declaration|declarations)\s+"
            r"(?:was|were|has\s+been|have\s+been)\s+removed\b",
        ),
    )

    #: Sentences the reading MUST catch. The first two are the verbatim pair
    #: review cycle 1 measured false, line-joined exactly as
    #: :meth:`comment_block` would deliver them; the rest are the shapes a
    #: later card would reach for.
    CLAIMS = (
        "**Two of these are the ADR's own; the rest are CARD-298's findings, "
        "one fewer since CARD-309.**",
        "No count of them is written here on purpose — CARD-309 removed one "
        "entry and a number in this comment would have been the drift "
        "CARD-261 found twice, in a comment nobody re-reads when the mapping "
        "shrinks.",
        "CARD-322 removed two entries and the rest stay.",
        "The mapping has shrunk since CARD-322.",
        "The puzzle page's declaration is now gone.",
        "PageKind.PUZZLE is no longer declared here.",
    )

    #: Sentences the reading MUST NOT catch — every one of them either stands
    #: in this comment today or is the true form of a retraction. A reading
    #: that fires on these is a reading no honest comment can satisfy, which is
    #: the failure mode of the first draft of any text guard.
    PASSES = (
        "**Two of these are the ADR's own; the rest are CARD-298's findings, "
        "and CARD-309 removed no entry.**",
        "It built ADR-0042/R1's assembly point, **converted nothing**, and "
        "**re-pointed five entries** from itself at CARD-322.",
        "**CARD-322 is the card that removes these four**, and `expires_with` "
        "names it instead of CARD-309.",
        "**Each entry names the cards that between them remove it, and the "
        "shrink is guarded in two directions.**",
        "a number in a comment nobody re-reads is exactly what goes stale "
        "when the mapping *does* shrink",
        "``test_a_raster_page_whose_declaration_is_removed_is_a_defect`` reds "
        "when a declaration is removed while the page is still a bitmap",
        "reds the day the last card named in an ``expires_with`` reaches "
        "``done`` and the entry is still here",
        "The mapping did not shrink.",
    )

    @classmethod
    def comment_block(cls, source: str) -> list[str]:
        """The contiguous ``#:`` lines directly above the registry assignment.

        Returns ``[]`` when the assignment is absent, which is a measured
        outcome rather than a pass — :meth:`test_the_block_is_the_one_above_the_registry`
        drives that arm, because a reading that silently finds nothing would
        make every claim cell below vacuously green.
        """
        lines = source.splitlines()
        anchor = None
        for index, line in enumerate(lines):
            if re.match(rf"^{cls.REGISTRY}\b", line):
                anchor = index
                break
        if anchor is None:
            return []
        block: list[str] = []
        cursor = anchor - 1
        while cursor >= 0 and lines[cursor].startswith("#:"):
            block.append(lines[cursor][2:].strip())
            cursor -= 1
        return list(reversed(block))

    @classmethod
    def removal_claims(cls, text: str) -> list[str]:
        """Every label in :data:`REMOVAL_CLAIMS` that ``text`` triggers."""
        return sorted(
            label
            for label, pattern in cls.REMOVAL_CLAIMS
            if re.search(pattern, text, re.IGNORECASE)
        )

    @classmethod
    def block_text(cls) -> str:
        block = cls.comment_block(cls.MODULE.read_text(encoding="utf-8"))
        return " ".join(block)

    def test_the_block_is_the_one_above_the_registry(self) -> None:
        """The extractor's own control, in both polarities.

        Everything below reads this block, so a block the reading cannot find
        is a green suite that checked nothing.
        """
        block = self.comment_block(self.MODULE.read_text(encoding="utf-8"))
        assert len(block) >= 20, len(block)
        joined = " ".join(block)
        assert "ADR-0042/R2's declared set" in joined, joined[:200]
        # It really is THIS assignment's block and not the file's first
        # comment: the registry's own name is in the line below the block.
        source_lines = self.MODULE.read_text(encoding="utf-8").splitlines()
        anchor = next(
            index
            for index, line in enumerate(source_lines)
            if re.match(rf"^{self.REGISTRY}\b", line)
        )
        assert source_lines[anchor - 1].startswith("#:"), source_lines[anchor - 1]
        # And the negative arm: no assignment, no block.
        assert self.comment_block("#: a comment above nothing\nx = 1\n") == []

    def test_the_comment_claims_no_removal_the_registry_cannot_show(self) -> None:
        """F-001's cell. **Two arms, and which one applies is derived.**

        The question is not "does this comment mention a removal" — the mapping
        exists to name future removals. It is "does the comment's account of
        what has **already** been taken out agree with what is in the mapping".

        * nothing taken out yet → the comment may claim no removal;
        * something taken out → the comment must say so, or it reads as
          further from done than it is, which is the mirror defect.

        So this cell does not have to be edited when CARD-322 converts a kind;
        it flips arm, and reds until the paragraph is re-derived.
        """
        gone = sorted(kind.value for kind in set(PageKind) - set(_RASTER_DECLARATIONS))
        claims = self.removal_claims(self.block_text())
        if gone:
            assert claims, (
                "the registry no longer declares "
                f"{gone} and the comment above it claims nothing was taken out"
            )
        else:
            assert claims == [], (
                "the comment claims a removal the registry cannot show "
                f"({claims}); every PageKind is still declared raster"
            )

    def test_the_registry_lost_nothing_and_five_entries_name_the_converting_card(
        self,
    ) -> None:
        """The shape the corrected paragraph asserts, derived from the enum.

        Seven is not written here as a number: it is
        ``set(PageKind) == set(_RASTER_DECLARATIONS)``, i.e. **no page kind has
        converted**, which is the fact "CARD-309 removed no entry" rests on.
        Five is written once, beside a second derivation that writes no number
        at all, because the paragraph writes "five" and a figure a comment
        states is a figure a cell owes.
        """
        kinds = set(PageKind)
        declared = set(_RASTER_DECLARATIONS)
        assert declared == kinds, sorted(kind.value for kind in kinds ^ declared)
        re_pointed = {
            kind
            for kind, entry in _RASTER_DECLARATIONS.items()
            if _THE_CONVERTING_CARD in entry.expires_with
        }
        assert re_pointed == declared - {PageKind.COVER, PageKind.DIVIDER}, sorted(
            kind.value for kind in re_pointed
        )
        assert len(re_pointed) == 5, sorted(kind.value for kind in re_pointed)
        assert [
            kind.value
            for kind, entry in _RASTER_DECLARATIONS.items()
            if _THE_CLOSING_CARD in entry.expires_with
        ] == []

    def test_the_reading_catches_the_claims_and_spares_the_honest_sentences(
        self,
    ) -> None:
        """Guard-the-guard, measured per sentence in both polarities."""
        missed = [text for text in self.CLAIMS if not self.removal_claims(text)]
        assert missed == [], missed
        caught = [
            (text, self.removal_claims(text))
            for text in self.PASSES
            if self.removal_claims(text)
        ]
        assert caught == [], caught
        # And the vocabulary is not one pattern doing all the work: at least
        # four distinct labels fire across CLAIMS.
        labels = {
            label for text in self.CLAIMS for label in self.removal_claims(text)
        }
        assert len(labels) >= 4, sorted(labels)


def test_a_declaration_outliving_its_done_card_is_a_defect(tmp_path) -> None:
    """The control the new board coupling owes, over a **synthetic** board.

    A guard added because a hole was found has to be shown to close the hole
    *and* shown not to be vacuous. At HEAD no declaration is stale and every
    card named is open, so asserting over the real board would pass whatever
    :func:`_landing_findings` did — including ``return []`` and ``return
    ["everything"]``. So the cards are written into ``tmp_path``: no real card
    file is read, edited or depended on, and the synthetic ids are far outside
    the board's range so a stray real file cannot answer for one.

    Both directions, and all five undeterminable shapes
    :func:`_card_status` names.
    """

    def card(name: str, body: str) -> None:
        (tmp_path / f"{name}.md").write_text(body, encoding="utf-8")

    def status_card(name: str, status: str) -> None:
        card(name, f"# {name}: a probe\n\n**Status:** {status}\n**Priority:** P2\n")

    def declared(*cards: str):
        return {
            PageKind.PUZZLE: RasterDeclaration(
                reason="a probe", authority="a probe", expires_with=cards
            )
        }

    status_card("CARD-90001", "done")
    status_card("CARD-90008", "done")
    status_card("CARD-90002", "ready")
    status_card("CARD-90003", "in_progress")  # the spelling the pipeline WRITES
    status_card("CARD-90010", "review")  # in flight too, and never yet seen live
    status_card("CARD-90009", "skipped")  # terminal, but not "done"
    status_card("CARD-90004", "shipped")  # a status word the board does not use
    card("CARD-90005", "# CARD-90005: a probe\n\nno status line at all\n")
    card("CARD-90006", "# p\n\n**Status:** done\n**Status:** ready\n")
    (tmp_path / "CARD-90007.md").mkdir()  # a directory where a card should be

    # ---- the defect: the card is done and the declaration is still here ----
    reds = _landing_findings(declared("CARD-90001"), tmp_path)
    assert len(reds) == 1, reds
    assert reds[0].startswith("puzzle: a declaration outliving its own expiry"), reds
    assert "CARD-90001" in reds[0]

    # ---- and NOT a defect while the card is still open ----
    # This is the half that stops a deny-everything derivation from passing
    # the assertion above.
    for still_open in ("CARD-90002", "CARD-90003", "CARD-90010"):
        assert _landing_findings(declared(still_open), tmp_path) == [], still_open

    # ---- THE TWO IN-FLIGHT STATUSES ARE NOT TERMINAL ----
    # Added 2026-10-30, after this guard reded `main` the moment wave 69
    # dispatched two cards: `_BOARD_STATUSES` held "in progress" (the spelling
    # of board.md's heading) while the pipeline writes `in_progress`, so a card
    # in flight came back from `_card_status` as the default-DENY None. The
    # guard was right; its vocabulary was wrong.
    #
    # That both words are READ as themselves is asserted with the other
    # statuses near the end of this test, where a parser returning a constant
    # is what is being refused. What is asserted HERE is the half that has no
    # home there and no witness on the real board: neither word is terminal. A
    # card in flight will reach `done` and can still remove its declaration, so
    # putting either in `_TERMINAL_STATUSES` would report a live declaration as
    # outliving its expiry. `review` additionally has never appeared on this
    # board, so the real board would pass whether the word were in the
    # vocabulary or not — without a synthetic card carrying it, its membership
    # is a claim with no control (ADR-0039/R1), and the next card to reach its
    # review phase would have reded `main` a second time on a different word.
    assert "in_progress" not in _TERMINAL_STATUSES
    assert "review" not in _TERMINAL_STATUSES

    # ---- and the dead spelling cannot be read as a status again ----
    # "in progress" was carried by 126 historical cards and by none in the live
    # tree. It is out of the vocabulary, so it now takes the same default-DENY
    # path as any unknown word — which is what stops this control from
    # exercising an impossible case while the real one goes unguarded, the
    # exact shape that hid the defect above.
    status_card("CARD-90011", "in progress")
    assert _card_status("CARD-90011", tmp_path) is None

    # ---- the expiry is the LAST card, not the first ----
    assert _landing_findings(declared("CARD-90001", "CARD-90002"), tmp_path) == []
    assert _landing_findings(declared("CARD-90002", "CARD-90001"), tmp_path) == []
    both_done = _landing_findings(declared("CARD-90001", "CARD-90008"), tmp_path)
    assert len(both_done) == 1, both_done
    assert "CARD-90001" in both_done[0] and "CARD-90008" in both_done[0], both_done

    # ---- SKIPPED is terminal too, and this is the only control for that ----
    # Added 2026-10-29 with ``_TERMINAL_STATUSES``. A skipped card will never be
    # built, so a declaration waiting on one waits forever — forge:kanban's own
    # ``skip`` defines the status as unblocking dependents "as if the dependency
    # were done". No declaration names a skipped card at HEAD, so the real board
    # cannot witness this and would pass whether ``skipped`` were terminal or
    # not; without these four lines the membership would be a claim with no
    # control, which ADR-0039/R1 forbids.
    skipped_only = _landing_findings(declared("CARD-90009"), tmp_path)
    assert len(skipped_only) == 1, skipped_only
    assert skipped_only[0].startswith(
        "puzzle: a declaration outliving its own expiry"
    ), skipped_only
    assert "CARD-90009" in skipped_only[0], skipped_only
    assert "skipped" in skipped_only[0], skipped_only

    # done + skipped is still terminal, and the message names both statuses
    mixed_terminal = _landing_findings(
        declared("CARD-90001", "CARD-90009"), tmp_path
    )
    assert len(mixed_terminal) == 1, mixed_terminal
    assert "done" in mixed_terminal[0] and "skipped" in mixed_terminal[0], (
        mixed_terminal
    )

    # ---- but a skipped card alongside an OPEN one is not yet expired ----
    # The direction that stops ``skipped`` from being read as "expire now".
    assert _landing_findings(declared("CARD-90009", "CARD-90002"), tmp_path) == []

    # ---- a permanent exception has no expiry to outlive ----
    assert (
        _landing_findings(
            {
                PageKind.COVER: RasterDeclaration(
                    reason="a photograph", authority="ADR-0042/R2", expires_with=()
                )
            },
            tmp_path,
        )
        == []
    )

    # ---- and every undeterminable shape FAILS rather than passing ----
    # CARD-90099 is the typo case: a well-formed id naming no card at all,
    # which `re.fullmatch(r"CARD-\d+")` accepts and only the board can reject.
    for undeterminable in (
        "CARD-90099",  # absent
        "CARD-90004",  # a status outside the board's vocabulary
        "CARD-90005",  # no **Status:** line
        "CARD-90006",  # two of them
        "CARD-90007",  # a directory, so unreadable
    ):
        findings = _landing_findings(declared(undeterminable), tmp_path)
        assert len(findings) == 1, (undeterminable, findings)
        assert "name no card whose status this board can give" in findings[0], (
            undeterminable,
            findings,
        )
        assert undeterminable in findings[0], (undeterminable, findings)
        assert _card_status(undeterminable, tmp_path) is None, undeterminable

    # One done card beside one undeterminable one reports the undeterminable
    # one and does NOT also claim the expiry, so the two findings cannot stand
    # in for each other.
    mixed = _landing_findings(declared("CARD-90001", "CARD-90099"), tmp_path)
    assert len(mixed) == 1, mixed
    assert "name no card whose status this board can give" in mixed[0], mixed

    # The statuses the board does use are read as themselves, not merely as
    # "not done" -- a parser returning a constant would pass the arms above.
    assert _card_status("CARD-90001", tmp_path) == "done"
    assert _card_status("CARD-90002", tmp_path) == "ready"
    assert _card_status("CARD-90003", tmp_path) == "in_progress"
    assert _card_status("CARD-90010", tmp_path) == "review"


def test_a_page_whose_medium_cannot_be_determined_is_a_defect() -> None:
    """AC-2's third clause, on two shapes the guard was **not** written from.

    Neither of these is a page any writer in this project emits, which is the
    point: ADR-0039/R2's default-DENY is a claim about the pages nobody has
    thought of, so the control has to be one of them. Both are built by
    driving ``PIL.PdfParser`` directly — the same parser both writers drive —
    rather than by editing bytes, so each really is a readable PDF page.

    * **Both** an ``/XObject`` and a ``/Font``: a page that looks raster to a
      reader that tests for one key and vector to a reader that tests for the
      other. A classifier with an ``if``/``else`` instead of three branches
      calls it whichever it tested first.
    * **Neither**: a page with an empty resource dictionary. A classifier that
      read "no XObject" as "vector" would call this an ADR-0042/R1 page.
    """
    from io import BytesIO

    from PIL import PdfParser

    def one_page(resources) -> bytes:
        written = BytesIO()
        pdf = PdfParser.PdfParser(f=written, filename="", mode="w+b")
        image_ref = pdf.next_object_id(0)
        font_ref = pdf.next_object_id(0)
        page_ref = pdf.next_object_id(0)
        contents_ref = pdf.next_object_id(0)
        pdf.pages.append(page_ref)
        pdf.start_writing()
        pdf.write_header()
        pdf.write_catalog()
        pdf.write_obj(image_ref, Type=PdfParser.PdfName("XObject"))
        pdf.write_obj(font_ref, Type=PdfParser.PdfName("Font"))
        pdf.write_page(
            page_ref,
            Resources=resources(image_ref, font_ref),
            MediaBox=[0, 0, 100, 100],
            Contents=contents_ref,
        )
        pdf.write_obj(contents_ref, stream=b"")
        pdf.write_xref_and_trailer()
        pdf.close()
        return written.getvalue()

    both = one_page(
        lambda image_ref, font_ref: PdfParser.PdfDict(
            XObject=PdfParser.PdfDict(image=image_ref),
            Font=PdfParser.PdfDict(F1=font_ref),
        )
    )
    neither = one_page(lambda image_ref, font_ref: PdfParser.PdfDict())

    assert _page_media(both) == [_UNCLASSIFIABLE], _page_media(both)
    assert _page_media(neither) == [_UNCLASSIFIABLE], _page_media(neither)
    for data in (both, neither):
        findings = _declaration_findings({PageKind.PUZZLE: set(_page_media(data))})
        assert any("cannot be determined" in finding for finding in findings), findings


class TestWritePdf_TheMediumIsChosenInOnePlace:
    """AC-4 — the choice of medium is made at exactly one place, by AST.

    ADR-0039/R2. The guard is **derived from the module's own syntax tree**,
    not from a list of functions that are allowed to decide: the question it
    answers is "how many places in this module turn a page kind into a
    medium?", and the answer has to be one, because a second one is a file
    whose cover is raster for one reason and whose divider is raster for
    another.

    **Two node shapes carry the decision, and both are watched.**

    * a read of :data:`~nonogram.admin.book_pdf_generator._RASTER_DECLARATIONS`
      — the registry *is* the decision, so reading it anywhere but inside
      :data:`DECIDER` is a second decision wherever it is;
    * a ``PageMedium.<member>`` attribute — producing a medium value.

    **Default-DENY.** A ``PageMedium`` attribute is allowed in exactly two
    shapes: inside :data:`DECIDER` (the decision itself), or as an operand of
    a comparison (reading a medium somebody else decided). **Every other
    shape is a finding**, including shapes nobody has thought of — a medium
    assigned to a name, returned, put in a container, passed as an argument or
    used in a conditional expression outside the decider. That is the half
    this class is controlled on: :data:`PLANTS` holds four shapes, three of
    which are not the one the first version of this guard would have caught.
    """

    #: Resolved from this file rather than from the working directory, so the
    #: guard reads the same module whatever pytest was invoked from.
    MODULE = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "nonogram"
        / "admin"
        / "book_pdf_generator.py"
    )

    #: The one function allowed to turn a kind into a medium.
    DECIDER = "page_medium"

    #: The name whose every read is a decision.
    REGISTRY = "_RASTER_DECLARATIONS"

    #: The enumeration whose members are medium values.
    MEDIUM = "PageMedium"

    @staticmethod
    def _owners(tree):
        """``{id(node): enclosing FunctionDef or None}``, by descent.

        By descent and not :func:`ast.walk`, for the reason
        ``tests/test_book_solved_answer_key.py``'s own door walk gives: a
        function defined *inside* another would otherwise be attributed to
        whichever one :func:`ast.walk` reached first, and the decider is the
        shape most likely to acquire a nested helper.
        """
        owner: dict = {}
        parent: dict = {}

        def descend(node, current):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                current = node
            for child in ast.iter_child_nodes(node):
                owner[id(child)] = current
                parent[id(child)] = node
                descend(child, current)

        owner[id(tree)] = None
        descend(tree, None)
        return owner, parent

    @classmethod
    def findings(cls, source: str) -> list[str]:
        """Every place in ``source`` that decides a medium outside the decider.

        A pure function of source text, so :data:`PLANTS` can be strings
        rather than files written into the tree.
        """
        tree = ast.parse(source)
        owner, parent = cls._owners(tree)
        found: list[str] = []

        for node in ast.walk(tree):
            # -- the registry: every read is a decision ---------------------
            if isinstance(node, ast.Name) and node.id == cls.REGISTRY:
                above = parent.get(id(node))
                if isinstance(node.ctx, ast.Store) or isinstance(
                    above, (ast.AnnAssign, ast.Assign)
                ):
                    continue  # the declaration itself, at module level
                enclosing = owner.get(id(node))
                if enclosing is None or enclosing.name != cls.DECIDER:
                    where = "module level" if enclosing is None else enclosing.name
                    found.append(f"{cls.REGISTRY} read in {where} (line {node.lineno})")
                continue
            # -- a medium value --------------------------------------------
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == cls.MEDIUM
            ):
                enclosing = owner.get(id(node))
                if enclosing is not None and enclosing.name == cls.DECIDER:
                    continue
                above = parent.get(id(node))
                if isinstance(above, ast.Compare):
                    continue
                shape = type(above).__name__ if above is not None else "module"
                where = "module level" if enclosing is None else enclosing.name
                found.append(
                    f"{cls.MEDIUM}.{node.attr} in {where} as a {shape} "
                    f"(line {node.lineno})"
                )
        return sorted(found)

    def test_the_shipped_module_decides_in_one_place(self) -> None:
        """The live assertion: no finding, on the module that ships.

        **Not an independent reading of** :meth:`test_each_plant_is_found`,
        and recorded here so the two cells are not counted as two (review
        cycle 1, A-7). Both route through the same :meth:`findings`
        classmethod: a defect inside ``findings`` reds both or neither. That
        is the intended design — one implementation, driven from the clean
        side here and from the four planted sides there, which is the same
        shape :func:`_declaration_findings` uses — but it buys *drive in both
        directions*, not *corroboration*.
        """
        source = self.MODULE.read_text(encoding="utf-8")
        assert self.findings(source) == [], self.findings(source)

    def test_the_decider_is_the_only_function_that_reads_the_registry(self) -> None:
        """And the decider really does read it — the guard is not vacuous.

        A guard over "nobody outside ``page_medium`` reads the registry" is
        trivially true of a module where nobody reads it at all, which is the
        state this would be in if the medium came from somewhere else
        entirely. Measured: exactly one read, inside the decider.
        """
        source = self.MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        owner, parent = self._owners(tree)
        reads = [
            owner[id(node)].name
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and node.id == self.REGISTRY
            and isinstance(node.ctx, ast.Load)
            and not isinstance(parent.get(id(node)), (ast.AnnAssign, ast.Assign))
            and owner[id(node)] is not None
        ]
        assert reads == [self.DECIDER], reads

    def test_the_writer_asks_the_decider_once_per_page(self) -> None:
        """``_write_pdf`` reads the medium through the decider, nowhere else.

        The call count is the measurement: one ``page_medium(...)`` call in
        the writer (over ``kinds``, so once per page) and no second source of
        a medium. Enumerated by AST rather than asserted in prose, because
        "the writer decides nothing" is exactly the claim a later edit breaks.

        **``produce``'s figure moved from 1 to 5 in CARD-309, and the number
        is re-derived rather than carried.** The interior's page walk asks the
        decider once per page *kind* it can draw two ways — TITLE (CARD-298),
        then GUIDE, TOC, PUZZLE and ANSWER (CARD-309) — so the tally is the
        count of gated kinds and not a count of pages, and it grows only when
        a kind acquires a second medium. DIVIDER has no gate: it has no vector
        writer, so lifting its declaration is refused by ``_write_pdf``'s
        representation check rather than branched on here. What this assertion
        still holds is the load-bearing half: ``produce`` *asks* and never
        decides (a ``PageMedium`` member outside the decider is a finding
        unless it is a comparison operand — :meth:`findings` above), and
        ``_write_pdf`` asks exactly once.
        """
        source = self.MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        callers: dict = {}
        owner, _ = self._owners(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == self.DECIDER
            ):
                enclosing = owner[id(node)]
                name = "module level" if enclosing is None else enclosing.name
                callers[name] = callers.get(name, 0) + 1
        assert callers == {"_write_pdf": 1, "produce": 5}, callers

    #: Four plants, each a shape that decides a medium outside the decider.
    #: **Three of the four are not the shape the obvious guard catches** — a
    #: second ``if``/``else`` is the one anybody would plant, and a medium put
    #: in a dictionary, returned from a helper, or read out of the registry
    #: are the ones that would have walked past a guard written only against
    #: it (ADR-0039/R1's "a control the guard was not written from").
    PLANTS = (
        (
            "a second if/else in the page loop",
            """
def _write_pdf(self, pages, page_count, *, mode, kinds):
    for kind in kinds:
        if kind is PageKind.PUZZLE:
            medium = PageMedium.RASTER
        else:
            medium = PageMedium.VECTOR
""",
        ),
        (
            "a medium in a container",
            """
def interior_stream(self, puzzles):
    overrides = {PageKind.TITLE: PageMedium.VECTOR}
    return overrides
""",
        ),
        (
            "a helper that returns a medium",
            """
def _medium_for(kind):
    return PageMedium.VECTOR
""",
        ),
        (
            "the registry read somewhere else",
            """
def interior_stream(self, puzzles):
    if PageKind.TITLE in _RASTER_DECLARATIONS:
        pass
""",
        ),
    )

    def test_each_plant_is_found(self) -> None:
        """Every plant reds, and the clean module is clean — both directions.

        The clean half is the shipped module's own two shapes (the decider's
        returns and the comparisons that read them), parsed as a string here
        so that "the guard passes what it should pass" is measured on the same
        pure function the plants are.
        """
        clean = """
_RASTER_DECLARATIONS: Dict[PageKind, RasterDeclaration] = {}


def page_medium(kind):
    if not isinstance(kind, PageKind):
        raise TypeError(kind)
    return PageMedium.RASTER if kind in _RASTER_DECLARATIONS else PageMedium.VECTOR


def _write_pdf(self, pages, page_count, *, mode, kinds):
    media = [page_medium(kind) for kind in kinds]
    any_vector = PageMedium.VECTOR in media
    for index, _ in enumerate(media):
        if media[index] is PageMedium.RASTER:
            pass
    return any_vector
"""
        assert self.findings(clean) == [], self.findings(clean)
        for label, plant in self.PLANTS:
            assert self.findings(clean + plant) != [], label


# --------------------------------------------------------------------------
# EC(ADR-0042/R1) and EC(ADR-0042/R2) — the two media over a seeded corpus
# --------------------------------------------------------------------------

#: The corpus both properties sweep: trims, puzzle counts and tier mixes,
#: built with stdlib ``random.Random`` on a fixed seed (no ``hypothesis`` —
#: it is not in the dependency baseline, CLAUDE.md). The trims are the three
#: this project measures on (Book 1, 6x9 in, and the 10 cm square CARD-297
#: measured its clip divergence on), crossed with puzzle counts that put the
#: plan in different shapes: 1 puzzle (no pairing, one answer page), 3
#: (pairing possible), and 7 (packing possible).
_CORPUS_TRIMS = (
    (BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM),
    SIX_BY_NINE_MM,
    (100.0, 100.0),
)
_CORPUS_COUNTS = (1, 3, 7)


def _corpus_books():
    """``(label, generator, puzzles)`` per corpus case, in a stable order."""
    import random

    rng = random.Random(298)
    tiers = ("easy", "medium", "hard")
    cases = []
    for width_mm, height_mm in _CORPUS_TRIMS:
        for count in _CORPUS_COUNTS:
            puzzles = []
            for index in range(count):
                columns = rng.choice((10, 15, 20))
                puzzle = _puzzle(columns, columns, 3, name=f"C{index}")
                puzzle["difficulty_tier"] = tiers[index % len(tiers)]
                puzzles.append(puzzle)
            label = f"{width_mm:.0f}x{height_mm:.0f}mm, {count} puzzle(s)"
            cases.append(
                (label, BookPDFGenerator(_book(width_mm, height_mm)), puzzles)
            )
    return cases


def test_PropertyTest_Interior_NoVectorPageCarriesABitmap(monkeypatch) -> None:
    """EC(ADR-0042/R1) — swept over a seeded corpus of books.

    Nine books over three trims and three puzzle counts, each exported
    **twice**: once with the declarations as they ship (every interior kind a
    bitmap) and once with the title page's declaration lifted, which is the
    only kind that can go vector at this commit and so the only way this
    property can be swept over a page that is actually operators.

    The minimum case count is asserted inside the test, as this tree's
    property tests do, so the corpus cannot silently shrink — and it is
    asserted **per arm**, because a corpus that lost its vector arm would
    otherwise still clear a total.
    """
    import nonogram.admin.book_pdf_generator as generator_module

    vector_pages = 0
    raster_pages = 0
    books = 0
    for label, generator, puzzles in _corpus_books():
        books += 1
        by_kind, kinds, media = _media_by_kind(generator, puzzles)
        for index, (kind, medium) in enumerate(
            zip(kinds, media, strict=True), start=1
        ):
            assert medium != _UNCLASSIFIABLE, (label, index, kind.value)
            if page_medium(kind) is PageMedium.VECTOR:
                vector_pages += 1
                assert medium == _VECTOR, (label, index, kind.value)
            else:
                raster_pages += 1
                assert medium == _RASTER, (label, index, kind.value)

    assert books == 9, books
    assert raster_pages >= 90, raster_pages
    # As it ships, no interior page is of a vector kind — which is why the
    # arm below exists rather than this figure being left to read as a sweep.
    assert vector_pages == 0, vector_pages

    monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.TITLE)
    mixed_vector = 0
    mixed_raster = 0
    for label, generator, puzzles in _corpus_books():
        by_kind, kinds, media = _media_by_kind(generator, puzzles)
        for index, (kind, medium) in enumerate(
            zip(kinds, media, strict=True), start=1
        ):
            assert medium != _UNCLASSIFIABLE, (label, index, kind.value)
            if page_medium(kind) is PageMedium.VECTOR:
                mixed_vector += 1
                assert medium == _VECTOR, (label, index, kind.value)
            else:
                mixed_raster += 1
                assert medium == _RASTER, (label, index, kind.value)

    # One title page per book, so the vector arm is nine pages — the floor is
    # the corpus size, not a number chosen to be clearable.
    assert mixed_vector >= 9, mixed_vector
    assert mixed_raster >= 90, mixed_raster


def test_PropertyTest_Interior_RasterPagesEqualDeclaredRasterPages(
    monkeypatch,
) -> None:
    """EC(ADR-0042/R2) — the two sets are equal, **neither direction slack**.

    Over the same corpus: the set of page kinds the file wrote as bitmaps is
    exactly the set of kinds this plan held *and* the registry declares. Both
    inclusions are asserted separately so the message says which way it broke
    — a bitmap nobody declared, or a declaration whose page is no longer one.

    The second arm lifts the title page's declaration so that the equality is
    swept over a plan where the two sets genuinely differ from the set of all
    kinds, rather than over nine books in which every kind is declared and
    the equality holds for the least interesting reason.
    """
    import nonogram.admin.book_pdf_generator as generator_module

    def arm() -> int:
        swept = 0
        for label, generator, puzzles in _corpus_books():
            by_kind, kinds, _ = _media_by_kind(generator, puzzles)
            written_raster = {
                kind for kind, media in by_kind.items() if _RASTER in media
            }
            declared_here = {kind for kind in by_kind if kind in _RASTER_DECLARATIONS}
            assert written_raster - declared_here == set(), (
                label,
                "a bitmap page kind with no declaration",
                sorted(k.value for k in written_raster - declared_here),
            )
            assert declared_here - written_raster == set(), (
                label,
                "a declared kind this plan wrote as operators",
                sorted(k.value for k in declared_here - written_raster),
            )
            assert _declaration_findings(by_kind) == [], label
            swept += 1
        return swept

    assert arm() == 9

    monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.TITLE)
    assert arm() == 9


def test_the_proof_sheet_is_the_one_pdf_outside_the_medium_decision() -> None:
    """A gap AC-1 names and this card does **not** close, measured not argued.

    AC-1 says "any interior PDF on any export path — the interior, the proof
    sheet, any future one". The interior and the cover both go through
    ``_write_pdf`` and are therefore inside :func:`page_medium`'s reach. **The
    proof sheet does not**: :func:`nonogram.admin.book_proof.render_proof_pdf`
    writes its pages through ``Image.save(format="PDF", save_all=True)`` — a
    second writer, the one ``_write_pdf`` replaced for the book in CARD-145 —
    so its pages have no :class:`~nonogram.admin.book_pdf_generator.PageKind`,
    no declaration and no medium decision behind them.

    That is recorded here rather than closed because closing it means calling
    a private method of a module that ``book_proof``'s own docstring says is
    out of its reach ("its writer is private and G-3 puts the module out of
    this card's reach"), and because a proof sheet is a press check over a
    real puzzle page rather than a book interior. **Both halves are asserted**
    — the pages really are bitmaps, and the writer really is the other one —
    so the day someone brings the proof sheet through ``_write_pdf`` this cell
    reds and the note goes with it instead of standing as a stale sentence.
    """
    from nonogram.admin import book_proof

    data = book_proof.render_proof_pdf(_book()).getvalue()
    media = _page_media(data)
    assert media and set(media) == {_RASTER}, media

    # And the writer really is the other one, by AST over its own module:
    # ``render_proof_pdf`` reaches ``Image.save(..., save_all=True)`` and never
    # ``_write_pdf``, so no page of it passes a page kind to anything. Derived
    # rather than read off the bytes — both writers drive ``PIL.PdfParser`` and
    # stamp the same ``% created by Pillow PDF driver`` comment, measured, so
    # the file cannot tell them apart.
    from nonogram.admin import book_proof as proof_module

    tree = ast.parse(
        pathlib.Path(proof_module.__file__).read_text(encoding="utf-8")
    )
    writer = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "render_proof_pdf"
    )
    reached = {
        node.func.attr
        for node in ast.walk(writer)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "save" in reached, sorted(reached)
    assert "_write_pdf" not in reached, sorted(reached)
    assert any(
        keyword.arg == "save_all"
        for node in ast.walk(writer)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
    )


class TestWritePdf_RefusesWhatItCannotWrite:
    """The writer's own refusals, each driven — the runtime half of default-DENY.

    ``_write_pdf`` lays its object table out from the page kinds before a page
    exists, so what can be wrong about them is refused at two different
    moments — and **review cycle 1's F-006 was right that an earlier wording
    collapsed them into one.** Stated exactly:

    * **Before the buffer exists**: ``mode`` is not a colour space this writer
      knows, and ``kinds`` is not one kind per planned page. Both precede
      ``written = BytesIO()``, so nothing at all is built.
    * **Per page, inside the loop, and necessarily so**: a page that arrives
      in the other medium's representation from the one its kind declares. The
      pages arrive one at a time from a generator (CARD-145), so their *types*
      cannot be known before the buffer exists. "Refused before the buffer"
      is not true of this half and cannot be made true of it.

    The substance is unaffected, which is why this is a wording fix and not a
    code one: the buffer is a **local** ``BytesIO`` and the ``TypeError``
    propagates out of the method, so a refusal at page *k* of *N* takes its
    partial bytes with it and no caller is handed a truncated PDF. That
    property is ``tests/test_book_pdf_memory.py``'s
    ``TestBookPdfMemory_NothingHalfWrittenEscapes``, not this class's.

    Neither shape is one production reaches today, which is exactly why each
    has a cell: they are the refusals that make a half-converted interior
    impossible to ship rather than merely unlikely.
    """

    def _generator(self):
        return BookPDFGenerator(_book())

    def test_a_kind_list_that_is_not_one_per_page_is_refused(self) -> None:
        generator = self._generator()
        page = Image.new("RGB", (60, 80), "white")
        with pytest.raises(ValueError) as raised:
            generator._write_pdf(
                iter([page, page]), 2, mode="RGB", kinds=(PageKind.PUZZLE,)
            )
        assert "2 page kind(s)" in str(raised.value), str(raised.value)

    def test_a_bitmap_under_a_vector_declaration_is_refused(
        self, monkeypatch
    ) -> None:
        """The day a declaration is lifted and a page writer is not converted.

        This is the failure mode the medium decision exists to make loud: the
        registry says the title page is operators now, and the walk still hands
        over a bitmap. It raises rather than writing a DCTDecode page under a
        vector declaration.
        """
        import nonogram.admin.book_pdf_generator as generator_module

        monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.TITLE)
        generator = self._generator()
        with pytest.raises(TypeError) as raised:
            generator._write_pdf(
                iter([generator.create_title_page(1)]),
                1,
                mode="L",
                kinds=(PageKind.TITLE,),
            )
        assert "vector title page" in str(raised.value), str(raised.value)

    def test_a_stream_under_a_raster_declaration_is_refused(self) -> None:
        """And the other direction, which no plan reaches either."""
        generator = self._generator()
        frame = page_frame(generator.page_spec(5))
        stream = book_vector.ContentStream(
            width_px=frame.width, height_px=frame.height, dpi=generator.dpi
        )
        with pytest.raises(TypeError) as raised:
            generator._write_pdf(
                iter([stream]), 1, mode="L", kinds=(PageKind.DIVIDER,)
            )
        assert "declared divider bitmap" in str(raised.value), str(raised.value)

    def test_the_decider_refuses_something_that_is_not_a_page_kind(self) -> None:
        """``page_medium``'s own default-DENY: a medium is per kind, or nothing.

        The string ``"puzzle"`` is the plausible mistake — the kinds carry
        string values, so a caller that passed one would otherwise get
        ``VECTOR`` (it is not a key of the registry) and ship a bitmap under a
        vector declaration.
        """
        for wrong in ("puzzle", None, 0, PageKind):
            with pytest.raises(TypeError):
                page_medium(wrong)


def test_the_page_kinds_are_the_positions_the_plan_itself_states() -> None:
    """The kind list, re-derived off a second **ordering authority** (CARD-298).

    ``interior_stream`` builds :attr:`InteriorStream.page_kinds` by walking its
    own five sections in order, so nothing in AC-1 or AC-2 can tell a
    mislabelled page from a correctly labelled one while every kind shares one
    medium: a mutant that gave the section dividers ``PageKind.PUZZLE``
    **survived** the whole of this card's own guard set, measured, because
    both kinds are declared bitmaps and both pages come out bitmaps.

    **What is genuinely independent here, stated exactly** (review cycle 1's
    F-005 corrected an earlier docstring that claimed more). It is the
    **ordering authority**, and only that: production reads kind-at-position
    from *enumeration order*, this test reads it from the **page number each
    plan object carries** — :attr:`DividerPagePlan.page_number` and
    :attr:`PuzzlePagePlan.page_number`, the numbers the Arrangement screen
    asks where a puzzle prints. That is a real second fact, and it would catch
    a :class:`SectionPlan` whose ``pages`` order disagreed with its own
    ``page_number`` values, which nothing else in the tree checks.

    **What is NOT independent, and the earlier wording overstated.** It is the
    same *door*: :meth:`BookPDFGenerator.interior_stream` itself calls
    ``self.section_plan(puzzles)`` and reads ``decided.pages``, so this test
    calls the same method on the same objects and gets them in the same order.
    And the kind discrimination is the **same predicate transcribed twice** —
    production writes ``PageKind.DIVIDER if isinstance(entry, DividerPagePlan)
    else PageKind.PUZZLE``, the loop below writes the same ``isinstance``
    chain. So both readings derive the kind from the plan object's class; they
    do **not** "share nothing about which kind sits at which position", which
    is what this docstring used to say. The value that remains is as a
    **control**: because the transcription is this test's own, a
    production-only mutant in the kind mapping still dies here.

    Two further restatements rather than second readings, both named so neither
    reads as evidence:

    * the front matter is rebuilt from the two page constants, which is the
      same arithmetic stated in a different place;
    * the answer tail is rebuilt from ``stream.answer_page_count`` **and is not
      production-equivalent**: production guards the SOLUTIONS divider on
      ``if payloads:`` while the ``if generator.divider_pages`` below does not.
      The corpus always has payloads, so the branch is unexercised rather than
      wrong — but a restatement that diverges is strictly worse than one that
      does not, and it is written down here instead of being discovered on the
      first book with no drawable member.
    """
    generator, puzzles = _interior_with_every_page_kind()
    decided = generator.section_plan(puzzles)
    stream = generator.interior_stream(puzzles)

    front = TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + decided.toc_page_count
    expected = [PageKind.TITLE] * TITLE_PAGE_COUNT
    expected += [PageKind.GUIDE] * GUIDE_PAGE_COUNT
    expected += [PageKind.TOC] * decided.toc_page_count

    # The section's own pages, placed by the number each plan object carries
    # rather than by the order they were appended in.
    section: dict = {}
    for entry in decided.pages:
        if isinstance(entry, DividerPagePlan):
            section[entry.page_number] = PageKind.DIVIDER
        elif isinstance(entry, PuzzlePagePlan):
            section[entry.page_number] = PageKind.PUZZLE
        else:  # default-DENY: an entry kind this reading does not know
            raise AssertionError(f"unclassified section entry: {entry!r}")
    assert sorted(section) == list(range(front + 1, front + 1 + len(decided.pages))), (
        sorted(section),
        front,
    )
    expected += [section[position] for position in sorted(section)]

    if generator.divider_pages:
        expected += [PageKind.DIVIDER]
    expected += [PageKind.ANSWER] * stream.answer_page_count

    assert list(stream.page_kinds) == expected, (
        [kind.value for kind in stream.page_kinds],
        [kind.value for kind in expected],
    )
    # And the dividers really are where a reader turns: the level divider and
    # the SOLUTIONS page, four and one on this book, so the comparison above
    # is over a list that actually holds both divider roles.
    assert expected.count(PageKind.DIVIDER) >= 2, expected
    assert expected.count(PageKind.PUZZLE) >= 1, expected


# --------------------------------------------------------------------------
# CARD-309 — the assembly point (AC-5)
# --------------------------------------------------------------------------
#
# ADR-0042/R1's third blocker, in its own words: *"`book_guide_vector`,
# `book_toc_vector` and `book_answer_vector` all import `book_pdf_generator` at
# module level, so the interior's own page walk — which lives in that module —
# cannot call three of the four vector page writers. The assembly point for a
# vector interior is downstream of all of them and does not exist yet."*
#
# It exists now, and these cells are what say so rather than a docstring. Two
# claims, and they are different kinds of claim:
#
# * a **structural** one — which module imports which — asserted by AST over
#   ``src/`` so that a lazy import inside a function body (the same cycle with
#   its direction hidden) reds here and is not mistaken for a resolution;
# * a **runtime** one — the walk really draws all four kinds through the
#   writers the assembly point binds — asserted by lifting every interior
#   declaration and reading back the interior that comes out. That is the only
#   way to reach the vector arms while the registry still declares every
#   interior kind a bitmap, and it is the same lever
#   ``test_no_interior_page_carries_an_image_xobject_in_a_mixed_file`` pulls
#   for one kind.


#: The assembly point, and the three writers it exists to reach.
_ASSEMBLY_POINT = "nonogram.admin.book_interior_vector"
_DOWNSTREAM_WRITERS = (
    "nonogram.admin.book_guide_vector",
    "nonogram.admin.book_toc_vector",
    "nonogram.admin.book_answer_vector",
)
#: Every module of the package, as ``{dotted name: path}``. Walked from disk so
#: a module a later card adds is covered the moment it lands (ADR-0039/R2 — the
#: set is derived, never listed), and so that "nothing imports the assembly
#: point" is a statement about the package and not about a list.
_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "nonogram"


def _package_modules() -> dict[str, pathlib.Path]:
    found: dict[str, pathlib.Path] = {}
    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        parts = path.relative_to(_PACKAGE_ROOT).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        found[".".join(("nonogram", *parts))] = path
    return found


def _imported_names(source: str) -> set[str]:
    """Every ``nonogram.*`` name ``source`` imports, **at any depth**.

    :func:`ast.walk` and not a scan of the module's top level, which is the
    half that matters here: a ``from nonogram.admin.book_guide_vector import
    guide_page`` inside a function body is the cycle this card exists to
    resolve, taken anyway with its direction hidden in a call. It would be
    invisible to a top-level reading and is a finding to this one.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return {name for name in names if name.split(".")[0] == "nonogram"}


class TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden:
    """AC-5's structural half, by AST over the package on disk.

    What makes the resolution a *direction* rather than a loop with a door in
    it is three facts together, and each is asserted separately because each
    can be lost on its own:

    #. the generator imports **none** of the three writers that import it —
       at any depth, so a function-body import is caught;
    #. the assembly point imports **all three** and the generator;
    #. **nothing in the package imports the assembly point**, so it is a leaf
       and no module can reach the writers back through it.

    The third is the one a reader is most likely to think unnecessary. It is
    the load-bearing one: without it a later card could import the assembly
    point from ``app.py`` *and* from ``book_guide_vector``, and the cycle
    would be back with an extra module in it.
    """

    def test_the_generator_imports_none_of_the_writers_that_import_it(self) -> None:
        modules = _package_modules()
        source = modules["nonogram.admin.book_pdf_generator"].read_text(
            encoding="utf-8"
        )
        imported = _imported_names(source)
        reached = sorted(name for name in _DOWNSTREAM_WRITERS if name in imported)
        assert reached == [], reached
        # Guard the guard: the reading really does see this module's imports,
        # so an empty answer above means "none of the three" and not "the walk
        # found nothing at all".
        assert "nonogram.admin.book_puzzle_vector" in imported, sorted(imported)
        assert "nonogram.admin.book_sheet_vector" in imported, sorted(imported)

    def test_each_writer_really_does_import_the_generator(self) -> None:
        """The premise of the whole card, measured and not quoted.

        If one of the three stopped importing the generator, the assembly
        point would be machinery for a cycle that no longer exists — which is
        a thing to notice rather than to keep.
        """
        modules = _package_modules()
        importers = sorted(
            name
            for name in _DOWNSTREAM_WRITERS
            if "nonogram.admin.book_pdf_generator"
            in _imported_names(modules[name].read_text(encoding="utf-8"))
        )
        assert importers == sorted(_DOWNSTREAM_WRITERS), importers

    def test_the_assembly_point_imports_all_of_them(self) -> None:
        modules = _package_modules()
        imported = _imported_names(
            modules[_ASSEMBLY_POINT].read_text(encoding="utf-8")
        )
        missing = sorted(name for name in _DOWNSTREAM_WRITERS if name not in imported)
        assert missing == [], missing
        assert "nonogram.admin.book_pdf_generator" in imported, sorted(imported)

    def test_nothing_in_the_package_imports_the_assembly_point(self) -> None:
        modules = _package_modules()
        assert _ASSEMBLY_POINT in modules, sorted(modules)
        importers = sorted(
            name
            for name, path in modules.items()
            if name != _ASSEMBLY_POINT
            and _ASSEMBLY_POINT in _imported_names(path.read_text(encoding="utf-8"))
        )
        assert importers == [], importers

    def test_the_import_reading_finds_a_planted_edge_at_any_depth(self) -> None:
        """The control :meth:`_imported_names` owes, in both shapes.

        A top-level import is the shape anybody would plant; the one that
        matters is the **function-body** import, because that is how the cycle
        gets taken while a top-level reading stays clean. Both are planted as
        source text rather than as files, so nothing is written into the tree.
        """
        top_level = "from nonogram.admin.book_guide_vector import guide_page\n"
        in_a_body = (
            "def draw():\n"
            "    from nonogram.admin.book_toc_vector import toc_page_stream\n"
            "    return toc_page_stream\n"
        )
        plain_module = "import math\n\n\ndef draw():\n    return math.pi\n"

        assert "nonogram.admin.book_guide_vector" in _imported_names(top_level)
        assert "nonogram.admin.book_toc_vector" in _imported_names(in_a_body)
        assert _imported_names(plain_module) == set()


class TestAssemblyPoint_TheDownstreamWritersAreReachable:
    """AC-5's runtime half: the walk draws all four kinds as operators.

    Every interior declaration is lifted at once, so
    :func:`~nonogram.admin.book_pdf_generator.page_medium` calls every interior
    kind vector and the walk has to find a writer for each of them. The cover
    and the section divider keep theirs (G-1, G-2), which is also what makes
    the file a *mixed* one and the assertion below an equivalence rather than
    a sweep.

    **This is not the shipped interior and does not claim to be.** No
    declaration is removed by CARD-309 — see :data:`_RASTER_DECLARATIONS`,
    whose reasons say why — so what these cells measure is that the
    *mechanism* is complete: the day CARD-322 removes an entry, the page it
    unblocks is already drawn and already read back. That is the whole of what
    an assembly point can be asserted to do before a kind converts.
    """

    #: The interior kinds whose declarations are lifted. Derived from the
    #: registry rather than listed: every temporary entry that is not the
    #: divider's is an interior kind this card's walk gates, so a sixth kind
    #: joining the registry is swept here instead of silently skipped.
    @staticmethod
    def _interior_kinds() -> list[PageKind]:
        return sorted(
            (
                kind
                for kind, entry in _RASTER_DECLARATIONS.items()
                if entry.expires_with and kind is not PageKind.DIVIDER
            ),
            key=lambda kind: kind.value,
        )

    #: A book whose answer section holds **both** shapes an answer page comes
    #: in — one full solved page and one CARD-202 packed page — so both of the
    #: two answer bindings are used. Measured, not assumed: the 30x30 answer
    #: will not pack and the 10x10's will, and
    #: :meth:`test_each_of_the_four_bindings_was_used` is the cell that keeps
    #: it true. A book of three 10x10s (this class's first draft) packs every
    #: answer, leaves the lone-answer binding unexercised, and lets a mutant
    #: that binds the packed writer to the lone slot survive — measured.
    BOOK = ((30, 30, 10), (10, 10, 3))

    def _puzzles(self):
        return [
            _puzzle(columns, rows, depth, name=f"P{index}")
            for index, (columns, rows, depth) in enumerate(self.BOOK)
        ]

    def _vector_interior(self, monkeypatch):
        import nonogram.admin.book_interior_vector as assembly
        import nonogram.admin.book_pdf_generator as generator_module

        lifted = self._interior_kinds()
        # The floor is a floor and not the count, for the reason the registry's
        # own comment gives: all this needs is that there is more than one kind
        # to reach, so the equivalence below is not about a single page.
        assert len(lifted) >= 4, [kind.value for kind in lifted]
        for kind in lifted:
            monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, kind)
            assert page_medium(kind) is PageMedium.VECTOR

        puzzles = self._puzzles()
        generator = assembly.interior_generator(_book())
        kinds = generator.interior_stream(puzzles).page_kinds
        data = generator.export_interior(puzzles).getvalue()
        return generator, kinds, data, lifted

    def test_each_of_the_four_bindings_was_used(self, monkeypatch) -> None:
        """Every field of the writer set is reached, counted at the binding.

        The cells below read the *file*, which says what was drawn and not
        **which binding drew it**: a set that bound the packed-answer writer to
        the lone-answer field would still produce an interior of operators on
        a book whose answers all pack. So the four bindings are wrapped in
        counters here — the set is otherwise
        :data:`~nonogram.admin.book_interior_vector.DOWNSTREAM_WRITERS`
        itself, field for field, derived from its own ``__dataclass_fields__``
        so a fifth field added later is counted rather than silently skipped.
        """
        import dataclasses

        import nonogram.admin.book_interior_vector as assembly
        import nonogram.admin.book_pdf_generator as generator_module

        for kind in self._interior_kinds():
            monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, kind)

        used: dict[str, int] = {}

        def counted(name, writer):
            def inner(*args, **keywords):
                used[name] = used.get(name, 0) + 1
                return writer(*args, **keywords)

            return inner

        fields = [field.name for field in dataclasses.fields(assembly.InteriorPageWriters)]
        assert len(fields) >= 4, fields
        wrapped = generator_module.InteriorPageWriters(
            **{
                name: counted(name, getattr(assembly.DOWNSTREAM_WRITERS, name))
                for name in fields
            }
        )
        generator = assembly.interior_generator(_book(), pages=wrapped)
        generator.export_interior(self._puzzles())

        assert sorted(used) == sorted(fields), (sorted(used), fields)
        assert all(count >= 1 for count in used.values()), used

    def test_every_interior_page_is_written_as_operators(self, monkeypatch) -> None:
        _generator, kinds, data, lifted = self._vector_interior(monkeypatch)
        media = _page_media(data)
        keys = pdf_vector.page_resource_keys(data)

        assert _UNCLASSIFIABLE not in media, [
            (index + 1, kinds[index].value)
            for index, medium in enumerate(media)
            if medium == _UNCLASSIFIABLE
        ]
        # The plan really did hold a page of every kind that was lifted, so
        # none of the four writers went unexercised.
        assert set(lifted) <= set(kinds), (
            sorted(kind.value for kind in lifted),
            sorted({kind.value for kind in kinds}),
        )
        for index, (kind, medium, resources) in enumerate(
            zip(kinds, media, keys, strict=True), start=1
        ):
            if kind in set(lifted):
                assert medium == _VECTOR, (index, kind.value, medium)
                assert "XObject" not in resources, (index, kind.value, resources)
            else:
                assert medium == _RASTER, (index, kind.value, medium)
        # And the divider really is still a bitmap on this file, so the
        # equivalence above has both arms (G-2).
        assert _RASTER in set(media), media
        # ADR-0042/R5: once per file, however many pages set text — and this
        # file's vector pages are most of it, so a face embedded per page
        # would be caught here as well as by that rule's own corpus test.
        assert len(pdf_vector.embedded_faces(data)) == 1

    def test_the_four_writers_each_drew_their_own_page(self, monkeypatch) -> None:
        """Not just "vector" — the right words on the right page.

        A walk that drew the puzzle page's stream four times would pass the
        cell above: every page would be operators and carry no image. So each
        kind is identified by text only its own writer sets, read out of the
        page's own stream, which is ADR-0042/R6's reading.
        """
        _generator, kinds, data, _lifted = self._vector_interior(monkeypatch)
        streams = pdf_vector.content_streams(data)
        by_kind: dict[PageKind, list[str]] = {}
        for kind, stream in zip(kinds, streams, strict=True):
            by_kind.setdefault(kind, []).append(stream)

        # Each of these is a string the kind's own writer sets and no other
        # writer does: the guide's title, the TOC's title, the answer page's
        # caption word, and the puzzle page's QR invitation.
        from nonogram.admin.book_pdf_generator import (
            GUIDE_TITLE,
            QR_CAPTION_TEXT,
            TOC_TITLE,
        )

        wanted = {
            PageKind.GUIDE: GUIDE_TITLE,
            PageKind.TOC: TOC_TITLE,
            PageKind.PUZZLE: QR_CAPTION_TEXT,
        }
        for kind, word in wanted.items():
            pages = by_kind[kind]
            assert pages, kind.value
            assert any(word in stream for stream in pages), (kind.value, word)
        # The answer pages are identified by the word every answer caption
        # carries, taken from the module that composes it rather than spelled
        # here, so a renamed caption reds instead of following silently.
        from nonogram.admin.book_answer_key import answer_caption

        caption = answer_caption(1, None)
        assert any(caption in stream for stream in by_kind[PageKind.ANSWER]), caption

    def test_a_generator_with_no_downstream_writer_refuses(
        self, monkeypatch
    ) -> None:
        """Default-DENY: the refusal names the module that supplies the writer.

        ``BookPDFGenerator(book)`` is every route's own call and is what a
        card that lifted a declaration without composing through the assembly
        point would be holding. It must not fall back to the bitmap — that is
        exactly the "a bitmap under a vector declaration" the writer's own
        refusal exists for (G-6) — and it must say where the writer comes
        from, because "no writer" is otherwise a ``TypeError`` on ``None``.
        """
        import nonogram.admin.book_pdf_generator as generator_module

        monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.GUIDE)
        generator = BookPDFGenerator(_book())
        puzzles = self._puzzles()
        with pytest.raises(ValueError) as raised:
            generator.export_interior(puzzles)
        message = str(raised.value)
        assert "guide page is written as operators" in message, message
        assert "book_interior_vector" in message, message

    def test_a_partial_writer_set_refuses_only_the_kind_it_is_missing(
        self, monkeypatch
    ) -> None:
        """The other side of the refusal, so it is not "any missing writer".

        A set carrying the guide but not the TOC must draw the guide and
        refuse the TOC — a refusal keyed on the kind rather than on the set
        being incomplete. Without this cell a ``_downstream_writer`` that
        raised whenever *any* field were ``None`` would pass the cell above.
        """
        import nonogram.admin.book_interior_vector as assembly
        import nonogram.admin.book_pdf_generator as generator_module

        monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.GUIDE)
        monkeypatch.delitem(generator_module._RASTER_DECLARATIONS, PageKind.TOC)
        puzzles = self._puzzles()

        guide_only = generator_module.InteriorPageWriters(
            guide=assembly.guide_page_stream
        )
        generator = assembly.interior_generator(_book(), pages=guide_only)
        with pytest.raises(ValueError) as raised:
            generator.export_interior(puzzles)
        message = str(raised.value)
        assert "toc page is written as operators" in message, message
        assert "guide" not in message, message


# --------------------------------------------------------------------------
# CARD-330 — where the two media put the grid, measured against the spec
# --------------------------------------------------------------------------
#
# CARD-309's round measured that the raster and the vector place "the same
# grid 2 device pixels apart on all four edges" (ink ``grid_left/right``
# 963/1849 against stream 965/1851) and routed the 0.169 mm that follows to a
# convention decision. Re-derived here, over a seeded corpus and against a
# position worked out from the page spec alone, **that premise is false**, and
# the three numbers below say why: the specified boundary, the vector's stream
# coordinate and the raster's own rule *centreline* are one number, and the
# 2 px is :func:`tests.helpers.page_ink.drawing_of`'s **leading ink edge** of a
# rule that is centred on that boundary, differenced against a centreline. The
# two figures CARD-309 subtracted are an ink extent and a path coordinate —
# two instruments with different domains — so neither medium is off spec and
# there is nothing to hold a convention about.
#
# What a conversion really moves is measured here too, because that is the
# figure CARD-322 inherits: read ink against ink, by one oracle at one
# resolution, the grid's four edges differ by **1 device pixel** (0.0847 mm,
# inside :data:`EDGE_TOLERANCE_MM`) and the drawing's own left/top edges by
# **3** (0.254 mm, outside it). Both differences are rule-thickness
# rasterisation, not placement: the raster strokes 6 whole pixels through
# Pillow while the vector strokes ADR-0037/R2's declared 1.3 pt (5.4167 px)
# through poppler, and a framed drawing's single stroked ``re`` mitres its
# outer corner where four butt-capped Pillow lines do not.

#: Poppler, which did not write the file, is the independent half of the
#: vector reading (``tests/helpers/pdf_vector.py``'s own docstring). A host
#: without it says so rather than passing quietly.
_needs_poppler = pytest.mark.skipif(
    pdf_vector.PDFTOPPM is None,
    reason="poppler's pdftoppm is not installed, so the vector page cannot be rendered",
)

#: How much of the puzzle area's spare height goes above the drawing —
#: FR-032 as amended 2026-10-17. Written out here, as this module writes every
#: other figure out.
_SPARE_ABOVE = 0.42

#: Where the band's own rule is struck, as a share of the band measured down
#: from the top margin: seven eighths of it, so the rule is lifted one eighth
#: of the band off the band's foot (CARD-222). The puzzle area's top edge.
_HEADER_RULE_SHARE = 1 - 1 / 8

#: The footer strip the puzzle area stops above, in millimetres: the 20 mm QR
#: slot, the 10 pt footer line and the two 9 pt gaps around them (CARD-248).
_FOOTER_STRIP_MM = 20.0 + (10.0 + 2 * 9.0) * 25.4 / 72

#: The raster grid's thin rule, in whole device pixels: the book's 0.25 mm
#: floor rounded **up** at 300 DPI. The heavy rule is exactly twice it, and
#: at every cell a book trim can give, that floor is what binds.
_RASTER_THIN_PX = 3
_RASTER_HEAVY_PX = 2 * _RASTER_THIN_PX

#: ADR-0037/R2's declared interior weights, in points.
_DECLARED_BORDER_PT = 1.3
_DECLARED_CELL_PT = 0.3

#: How far the derived millimetre figure may sit from a renderer's own
#: boundary. Three whole-pixel roundings separate them and none of them is a
#: placement: the trim's own extent (a 235 mm trim is 2774 px, i.e. 234.86 mm),
#: each boundary rounded once from exact fractions, and the committed pitch.
#: Each contributes at most half a pixel, so 1.5 px is the derived ceiling.
#: It is a bound on the *derivation*, not on a placed edge, and it is
#: deliberately not :data:`EDGE_TOLERANCE_MM`.
#:
#: **This is the derivation's ceiling and no longer a live bound.** It is
#: asserted only as the ceiling the two *measured* bounds below must stay
#: under. Until CARD-330 cycle 1's F-003 it was AC-1's sole control, and
#: measured it held nothing: tightening it to 1.05 px passed, and loosening it
#: to 12.0 px passed too. It is also 0.127 mm — *wider* than the
#: :data:`EDGE_TOLERANCE_MM` this card declined to widen, which is the
#: asymmetry a reader re-deriving from this test used to inherit.
_SPEC_ROUNDING_PX = 1.5

#: The live bound on the grid edges' derived-against-stream agreement. The
#: **measured** worst disagreement over the corpus below is 1.0 px exactly
#: (``22x28 d1 page 16 on 190x235 mm``, ``grid_bottom`` — FR-032's
#: footer-bound arm, the one anchored on the rounded trim extent, as the
#: ceiling above predicts), so this bound is that figure plus 5 %. 1.05 px is
#: 0.0889 mm, **inside** :data:`EDGE_TOLERANCE_MM`, and the span test asserts
#: that relation so the derivation's bound can never again sit looser than the
#: placed-edge bound it is not.
_SPEC_MEASURED_PX = 1.05

#: The same, for the drawing's own outer edges — where the raster's ink is
#: *at* the specified margin and the only disagreement is sub-pixel rounding.
#: Measured worst 0.5437 px (``16x25 d5 page 13 on 190x235 mm``,
#: ``drawing_left``), so the bound is 0.6 px = 0.0508 mm. Two live bounds
#: rather than one is F-003's other half: no single constant decides AC-1's
#: answer any more.
_SPEC_DRAWING_MEASURED_PX = 0.6

#: The corpus's **floor**, asserted inside the tests that read it so the
#: corpus cannot silently shrink — CLAUDE.md's test style in terms:
#: "asserting a minimum case count inside the test itself so the corpus can't
#: silently shrink. Prefer an independent second implementation over
#: re-deriving a value with the same function you're testing." G-5 forbids
#: lowering it.
#:
#: Both are **literals**, asserted equal to the enumerated span AC-1 names
#: (``len(_EDGE_TRIMS) * len(_EDGE_PARITIES) * len(_EDGE_BOUNDS) *
#: _EDGE_DRAWS_PER_COMBINATION``, and ``_MIN_EDGE_CASES * len(_GRID_EDGES)``)
#: rather than computed from it, and deliberately **not** the constant the
#: fixture counts with (:data:`_EDGE_CASE_COUNT`). Until CARD-330 cycle 1's
#: F-001 the floor and the generator were one constant, which made both floor
#: assertions satisfied by construction for any value of it: lowering it from
#: 24 to 3 left all 24 tests green with 87.5 % of the corpus gone.
_MIN_EDGE_CASES = 24
_MIN_EDGE_READINGS = 96

#: The four grid boundaries every reading carries, and the drawing's own two
#: outer edges — the ones AC-274's 25.45 mm is read from.
_GRID_EDGES = ("grid_left", "grid_right", "grid_top", "grid_bottom")
_DRAWING_EDGES = ("drawing_left", "drawing_top")

#: The three trims the corpus sweeps. Book 1's own 8.5 x 11 in first, then
#: the two smaller trims the panel offers — the cell is fitted to the page,
#: so a one-trim corpus would hold one cell.
_EDGE_TRIMS = (
    (BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM),
    (7.5 * 25.4, 9.25 * 25.4),
    (6.0 * 25.4, 9.0 * 25.4),
)

#: The other two dimensions of that span, enumerated for the same two
#: reasons: the floor is asserted against them, and each is asserted against
#: the drawn corpus as a set equality — so dropping a dimension reds the
#: floor rather than quietly halving the corpus.
_EDGE_PARITIES = (0, 1)
_EDGE_BOUNDS = ("ratio", "footer")

#: The quotient that takes the three structural dimensions to the corpus size:
#: 24 / (3 trims x 2 parities x 2 bounds). **Not** a guarantee of two draws per
#: combination, and this comment used to say it was (cycle 2's F-202). Trim and
#: parity are structural, but the vertical bound is **emergent** from the seeded
#: RNG, so the realized distribution over the 12 combinations is measured at
#: 1/2/3 -- four combinations each -- rather than 2 apiece. All 12 *are*
#: realized, which is better than the assertions guarantee; what is not true is
#: that each is sampled twice. AC-1 claims span, not balance, and the span is
#: asserted as a set equality per dimension, so F-001's anchor is unaffected:
#: shrinking any dimension still reds.
_EDGE_DRAWS_PER_COMBINATION = 2

#: How many cases the fixture actually draws. Deliberately separate from
#: :data:`_MIN_EDGE_CASES`: lowering this reds the floor instead of travelling
#: with it, which is the whole point of the two not being one constant.
_EDGE_CASE_COUNT = 24


def _specified_grid_mm(
    columns: int,
    rows: int,
    depth: int,
    *,
    width_mm: float,
    height_mm: float,
    page: int,
) -> dict[str, float]:
    """Where this page's grid boundaries **should** be, in millimetres.

    A second implementation, written here from CON-018's profile, FR-030's
    page fit and FR-032's centring, exactly as :func:`_expected_left_mm` and
    :func:`_expected_cell_mm` are — and like them it reads neither renderer,
    no ``compute_layout`` and no ``book_page_spec``. That is what makes it
    usable as the *specified* column of the three numbers AC-1 asks for: a
    position taken from either renderer could not tell which renderer was
    right.

    Horizontally this is :func:`_expected_left_mm`'s own arithmetic carried on
    through the row-clue gutter to the grid's two borders. Vertically the
    drawing floats at :data:`_SPARE_ABOVE` of the **puzzle area**'s spare
    height — the strip between the band's own rule (:data:`_HEADER_RULE_SHARE`
    of the band below the top margin) and the footer strip
    (:data:`_FOOTER_STRIP_MM` up from the bottom margin) — and is held at the
    band's foot instead on a drawing too deep to clear both rules, which is
    FR-032's own "footer" bound.

    Args:
        columns: The grid's columns.
        rows: The grid's rows.
        depth: The clue gutter's depth, in cells, on both axes.
        width_mm: The trim's width.
        height_mm: The trim's height.
        page: The interior page number, whose parity mirrors the margins.

    Returns:
        ``grid_left``/``grid_right``/``grid_top``/``grid_bottom`` and the
        drawing's own ``drawing_left``/``drawing_top``, in millimetres from
        the trim's top-left corner, plus the ``cell`` they were derived at and
        the ``bound`` (``"ratio"`` or ``"footer"``) that placed the top edge.
    """
    usable_width = width_mm - GUTTER_MM - OUTSIDE_MM
    usable_height = height_mm - TOP_MM - BOTTOM_MM - BAND_MM
    cell = min(
        STANDARD_CELL_MM,
        usable_width / (depth + columns),
        usable_height / (depth + rows),
    )
    right_hand = page % 2 == 1
    left_margin = GUTTER_MM if right_hand else OUTSIDE_MM
    spare_width = usable_width - (depth + columns) * cell
    drawing_left = left_margin + max(spare_width, 0.0) / 2

    area_top = TOP_MM + BAND_MM * _HEADER_RULE_SHARE
    area_bottom = height_mm - BOTTOM_MM - _FOOTER_STRIP_MM
    band_bottom = TOP_MM + BAND_MM
    drawing_height = (depth + rows) * cell
    spare_height = (area_bottom - area_top) - drawing_height
    # The clearance each gap has to pay: half the drawing's own heavy rule,
    # half the heavier of the two furniture rules, and the pixel that makes
    # "clear" strict. The header's 0.6 pt is 3 px at 300 DPI and the footer's
    # 0.4 pt is 2, so the heavier of the two is 3 — and both halves are
    # rounded up, as a minimum is.
    _furniture_px = 3
    clearance_px = -(-_RASTER_HEAVY_PX // 2) + -(-_furniture_px // 2) + 1
    clearance_mm = clearance_px / PX_PER_MM
    gap_above = _SPARE_ABOVE * spare_height
    if gap_above < clearance_mm or spare_height - gap_above < clearance_mm:
        # One pixel of drawing past the footer rule, or the band's foot if
        # that is lower on the page — whichever refuses the footer group.
        drawing_top = max(band_bottom, area_bottom + 1 / PX_PER_MM - drawing_height)
        bound = "footer"
    else:
        drawing_top = area_top + gap_above
        bound = "ratio"

    return {
        "cell": cell,
        "bound": bound,
        "drawing_left": drawing_left,
        "drawing_top": drawing_top,
        "grid_left": drawing_left + depth * cell,
        "grid_right": drawing_left + (depth + columns) * cell,
        "grid_top": drawing_top + depth * cell,
        "grid_bottom": drawing_top + (depth + rows) * cell,
    }


#: One ``m ... l S`` stroke of a content stream, and the ``w`` that set its
#: width. Spelled here rather than imported from ``tests/helpers/pdf_vector``
#: because what is wanted is the grid's two **border** rules and nothing else,
#: which is a width comparison and not a mark taxonomy.
_STREAM_NUMBER = r"-?\d+(?:\.\d+)?"
_STREAM_WIDTH = re.compile(rf"^({_STREAM_NUMBER}) w$")
_STREAM_STROKE = re.compile(
    rf"^({_STREAM_NUMBER}) ({_STREAM_NUMBER}) m "
    rf"({_STREAM_NUMBER}) ({_STREAM_NUMBER}) l S$"
)


def _stream_grid_mm(written: bytes) -> dict[str, float]:
    """The grid's four boundaries as the **content stream** places them, in mm.

    The stream's own operands, converted out of PDF points and flipped onto
    the page's top-left origin — so this reads the written file and not the
    geometry that wrote it. The grid's boundaries are its two
    :data:`_DECLARED_BORDER_PT` rules on each axis, which are the heaviest
    strokes a puzzle page sets; the frame's box is a single ``re`` and is not
    a stroke this reads at all.

    **The flip is against the page's own MediaBox and not against the stored
    trim**, and that is not a detail: a PDF's y grows upward from the page
    foot, the page's height is the trim rounded to whole device pixels (a
    235 mm trim is 2774 px, i.e. 234.86 mm), and flipping 235 mm against a
    234.86 mm page shifts every horizontal reading by 1.6 px. Measured: it
    made the vertical edges of one trim in three read 3 px out instead of 2,
    which is an instrument error that looks exactly like a medium
    disagreeing.
    """
    (_left, _bottom, _right, top), *_rest = pdf_page_boxes(written)
    height_mm = top * 25.4 / 72
    (stream_text,) = pdf_vector.content_streams(written)
    width: float | None = None
    verticals: list[float] = []
    horizontals: list[float] = []
    for line in stream_text.splitlines():
        line = line.strip()
        setting = _STREAM_WIDTH.match(line)
        if setting is not None:
            width = float(setting.group(1))
            continue
        stroke = _STREAM_STROKE.match(line)
        if stroke is None or width != _DECLARED_BORDER_PT:
            continue
        x1, y1, x2, y2 = (float(operand) for operand in stroke.groups())
        if x1 == x2:
            verticals.append(x1 * 25.4 / 72)
        elif y1 == y2:
            horizontals.append(height_mm - y1 * 25.4 / 72)
    if len(verticals) < 2 or len(horizontals) < 2:
        raise ValueError(
            f"this stream sets no pair of {_DECLARED_BORDER_PT} pt border "
            f"rules on each axis: {len(verticals)} vertical, "
            f"{len(horizontals)} horizontal"
        )
    return {
        "grid_left": min(verticals),
        "grid_right": max(verticals),
        "grid_top": min(horizontals),
        "grid_bottom": max(horizontals),
    }


@dataclass(frozen=True)
class _EdgeReading:
    """One page's grid edges, read three ways, in millimetres.

    Attributes:
        label: The case, for a failure message.
        page: The interior page number this was drawn as — its parity is what
            mirrors the margins.
        trim_mm: The trim it was drawn on, ``(width, height)``.
        framed: Whether the raster page's drawing is closed off by a frame,
            read off the page.
        bound: What placed the drawing's top edge — ``"ratio"`` or
            ``"footer"``, from the derivation and not from the renderer.
        specified: :func:`_specified_grid_mm`'s answer — the page spec's own
            arithmetic, which neither renderer was asked.
        raster_ink: What ``page_ink.drawing_of`` reads off the **raster**
            page: Pillow's bitmap at 300 DPI, measured as the first inked
            pixel line of each rule.
        vector_stream: What the written **content stream** places, from its
            own operands (:func:`_stream_grid_mm`).
        vector_ink: What the same ``drawing_of`` reads off a **poppler**
            render of that stream at the same 300 DPI — the ink half of the
            vector medium, by an engine that did not write the file.
    """

    label: str
    page: int
    trim_mm: tuple[float, float]
    framed: bool
    bound: str
    specified: dict[str, float]
    raster_ink: dict[str, float]
    vector_stream: dict[str, float]
    vector_ink: dict[str, float]


def _edge_case(index: int, out_dir: pathlib.Path) -> _EdgeReading:
    """Draw one puzzle page **both** ways and read all three numbers off it.

    The same book, the same payload, the same puzzle number, the same interior
    page and the same committed cell on both sides — the shape
    ``tests/test_book_puzzle_page_vector.py``'s ``twin`` fixture takes, and for
    its reason: the only difference between the two readings has to be the
    medium, or a disagreement between them means nothing. ``cell_sizes`` is
    the one call both media share, which is the point; no geometry is read
    from it.
    """
    rng = random.Random(330 + index)
    width_mm, height_mm = _EDGE_TRIMS[index % len(_EDGE_TRIMS)]
    columns = rng.randrange(MIN_SIZE, MAX_SIZE + 1)
    rows = rng.randrange(MIN_SIZE, MAX_SIZE + 1)
    depth = rng.randrange(1, min(6, (min(columns, rows) + 1) // 2) + 1)
    page = FIRST_PUZZLE_PAGE + index  # both parities, many pages
    number = index + 1

    generator = BookPDFGenerator(_book(width_mm=width_mm, height_mm=height_mm))
    row = _puzzle(columns, rows, depth, name=f"Edge {index}")
    payload = BookPDFGenerator._payload(row)
    sizes = generator.cell_sizes([payload])

    bitmap = generator._blank_page(payload, number, page, sizes)
    ink = drawing_of(bitmap)

    stream = generator.vector_puzzle_page(payload, number, page, sizes)
    written = book_vector.write_vector_pdf([stream], 1).getvalue()
    # ``out_dir`` because ``rendered_page`` writes the PDF and poppler's PNG
    # beside each other and defaults to the CURRENT directory — which is the
    # repo root under pytest, so every other caller in this tree hands it a
    # tmp path and so does this one.
    rendered = pdf_vector.rendered_page(written, 300, 1, out_dir=out_dir)
    vector_ink = drawing_of(
        rendered if isinstance(rendered, Image.Image) else Image.fromarray(rendered)
    )

    specified = _specified_grid_mm(
        columns, rows, depth, width_mm=width_mm, height_mm=height_mm, page=page
    )
    return _EdgeReading(
        label=f"{columns}x{rows} d{depth} page {page} on {width_mm:.0f}x{height_mm:.0f} mm",
        page=page,
        trim_mm=(width_mm, height_mm),
        framed=ink.framed,
        bound=specified["bound"],
        specified={key: specified[key] for key in _GRID_EDGES + _DRAWING_EDGES},
        raster_ink=_ink_edges_mm(ink),
        vector_stream=_stream_grid_mm(written),
        vector_ink=_ink_edges_mm(vector_ink),
    )


def _ink_edges_mm(drawing) -> dict[str, float]:
    """A :class:`~tests.helpers.page_ink.Drawing`'s six edges in millimetres.

    ``grid_*`` is the first inked pixel line of each border rule and ``left``
    / ``top`` the drawing's own outer edges, so every one of these is an **ink
    extent** and not a boundary — which is the whole finding of CARD-330, and
    the reason this helper exists rather than the figures being read inline.
    """
    return {
        "grid_left": _mm(drawing.grid_left),
        "grid_right": _mm(drawing.grid_right),
        "grid_top": _mm(drawing.grid_top),
        "grid_bottom": _mm(drawing.grid_bottom),
        "drawing_left": _mm(drawing.left),
        "drawing_top": _mm(drawing.top),
    }


@pytest.fixture(scope="module")
def edge_corpus(tmp_path_factory) -> list[_EdgeReading]:
    """The seeded corpus, drawn once for the module.

    Hand-built with :class:`random.Random` — ``hypothesis`` is not in the
    dependency baseline (ADR-0006/R1) — and module-scoped because each case
    draws a full bitmap page *and* shells out to poppler for the vector one,
    which is the same reason ``tests/test_book_pdf_band.py`` gave its own
    render fixture one.
    """
    out_dir = tmp_path_factory.mktemp("card330-edges")
    return [
        _edge_case(index, out_dir / str(index)) for index in range(_EDGE_CASE_COUNT)
    ]


@_needs_poppler
class TestEdgeOffset_TheThreeNumbersAreDerivedPerEdge:
    """AC-1 — specified, raster and vector, per edge, over a seeded corpus.

    The *specified* column is :func:`_specified_grid_mm`, which reads the
    trim, the margins, the band, the footer strip and the puzzle's own extents
    and nothing else. That is what the card's first question needs: a position
    taken from one of the two renderers could not say which renderer was
    right, which is how "the two media disagree by 0.169 mm" came to be read
    as a convention question in the first place.
    """

    def test_the_corpus_spans_trims_parities_and_both_vertical_bounds(
        self, edge_corpus
    ) -> None:
        """The minimum, asserted here so the corpus cannot silently shrink.

        **The floor is not the number the fixture counts with** (CARD-330
        cycle 1, F-001: it was, so both floor assertions were satisfied by
        construction for any value of it, and lowering it from 24 to 3 left
        all of this card's tests green). It is a literal, checked here against
        the enumerated span this corpus exists to cover — so lowering the
        floor, or dropping one of the span's dimensions, reds *here*, while
        shrinking :data:`_EDGE_CASE_COUNT` reds the floor itself. That is the
        independent second implementation CLAUDE.md's test style asks for: the
        span is enumerated, not re-derived from the generator.
        """
        span = (
            len(_EDGE_TRIMS)
            * len(_EDGE_PARITIES)
            * len(_EDGE_BOUNDS)
            * _EDGE_DRAWS_PER_COMBINATION
        )
        assert _MIN_EDGE_CASES == span, (_MIN_EDGE_CASES, span)
        assert _MIN_EDGE_READINGS == _MIN_EDGE_CASES * len(_GRID_EDGES), (
            _MIN_EDGE_READINGS,
            _MIN_EDGE_CASES,
            len(_GRID_EDGES),
        )
        assert len(edge_corpus) >= _MIN_EDGE_CASES, len(edge_corpus)
        assert len(edge_corpus) * len(_GRID_EDGES) >= _MIN_EDGE_READINGS
        parities = {reading.page % 2 for reading in edge_corpus}
        assert parities == set(_EDGE_PARITIES), parities
        trims = {reading.trim_mm for reading in edge_corpus}
        assert trims == set(_EDGE_TRIMS), trims
        # Both arms of FR-032's vertical placement, so the derivation is
        # exercised on the 42 % split *and* on the footer bound.
        assert {reading.bound for reading in edge_corpus} == set(_EDGE_BOUNDS)
        # F-003's second control: the derivation's live bounds are inside the
        # derived ceiling AND inside the placed-edge bound this card refused
        # to widen, so neither can drift back out to 0.127 mm unnoticed.
        assert _SPEC_DRAWING_MEASURED_PX <= _SPEC_MEASURED_PX <= _SPEC_ROUNDING_PX, (
            _SPEC_DRAWING_MEASURED_PX,
            _SPEC_MEASURED_PX,
            _SPEC_ROUNDING_PX,
        )
        # ``_STATED_EDGE_TOLERANCE_MM`` and not ``EDGE_TOLERANCE_MM``: the
        # criteria's own figure, which AC-4's own site asserts the live
        # constant equals — and naming the live one here would make this a
        # placed-edge site for the medium pin below without its reading a
        # page, which is the one thing that register exists to keep rare.
        assert _SPEC_MEASURED_PX / PX_PER_MM < _STATED_EDGE_TOLERANCE_MM, (
            _SPEC_MEASURED_PX / PX_PER_MM,
            _STATED_EDGE_TOLERANCE_MM,
        )

    def test_every_edge_of_every_case_carries_all_three_numbers(
        self, edge_corpus
    ) -> None:
        """Three readings per edge, in millimetres, none of them missing."""
        for reading in edge_corpus:
            for edge in _GRID_EDGES:
                three = (
                    reading.specified[edge],
                    reading.raster_ink[edge],
                    reading.vector_stream[edge],
                )
                assert all(isinstance(value, float) for value in three), (
                    reading.label,
                    edge,
                    three,
                )
                assert all(value > 0 for value in three), (reading.label, edge, three)

    def test_the_specified_position_is_where_the_content_stream_puts_the_grid(
        self, edge_corpus
    ) -> None:
        """**The answer to the card's first question.**

        The derived boundary and the vector's own operand are the same number
        on every edge of every case, inside :data:`_SPEC_MEASURED_PX` — the
        **measured** worst disagreement over this corpus plus 5 %, which is
        0.0889 mm and therefore inside the placed-edge bound this card
        declined to widen. So the vector writer is **not** placing the grid
        off spec: CARD-330's G-4 is not triggered and no blocker is raised.

        The bound used to be :data:`_SPEC_ROUNDING_PX`, the *derived* ceiling
        of three half-pixel roundings; cycle 1's F-003 measured that 1.05 px
        passed here and that 12.0 px passed too, so the one control AC-1 had
        was 0.45 px looser than anything the corpus exercises and 0.127 mm
        wide. The derivation is still written down above; what is asserted is
        now what was measured.
        """
        worst = max(
            (
                (
                    abs(reading.vector_stream[edge] - reading.specified[edge])
                    * PX_PER_MM,
                    reading.label,
                    edge,
                )
                for reading in edge_corpus
                for edge in _GRID_EDGES
            ),
        )
        assert worst[0] < _SPEC_MEASURED_PX, worst

    def test_the_specified_position_is_not_either_mediums_ink_reading(
        self, edge_corpus
    ) -> None:
        """So the derived column cannot have been copied off a page.

        Both media's ink sits a measurable distance outside the specified
        boundary on **every** edge of every case — the raster's by more than
        one device pixel and the vector's by more than two — which is what
        tells a derivation from a reading. An ``_specified_grid_mm`` that had
        quietly become a renderer's answer would read zero here.
        """
        for reading in edge_corpus:
            for edge in _GRID_EDGES:
                raster = (reading.specified[edge] - reading.raster_ink[edge]) * PX_PER_MM
                vector = (reading.specified[edge] - reading.vector_ink[edge]) * PX_PER_MM
                assert raster > 1, (reading.label, edge, raster)
                assert vector > 2, (reading.label, edge, vector)


@_needs_poppler
class TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels:
    """AC-2 — the gap is uniform, and it is not what CARD-309 read it as.

    It **is** uniformly 2 device pixels, on all four edges and across the
    corpus, between the raster's ink and the stream's coordinate. What it is
    not is a disagreement about where the grid goes: those two readings have
    different domains — one is the first inked pixel line of a rule, the other
    is the rule's path — and the 2 px is half the rule that sits between them.
    The control below is what separates those two readings of the same figure:
    a *quantisation* of the grid's position would not change with the rule's
    weight, and this does, exactly as ``(width - 1) // 2``.
    """

    def test_the_rasters_ink_is_two_device_pixels_outside_the_stream_on_every_edge(
        self, edge_corpus
    ) -> None:
        offsets = {
            round((reading.raster_ink[edge] - reading.vector_stream[edge]) * PX_PER_MM)
            for reading in edge_corpus
            for edge in _GRID_EDGES
        }
        assert offsets == {-2}, offsets
        assert len(edge_corpus) >= _MIN_EDGE_CASES, len(edge_corpus)

    def test_that_two_pixels_is_half_a_rule_and_not_a_quantisation_step(
        self, edge_corpus
    ) -> None:
        """The control: the offset tracks the **rule's weight**, not the grid.

        A rule is centred on its boundary, so a reading taken at its first
        inked line sits ``(width - 1) // 2`` outside that boundary — 2 px for
        the raster's 6 px border and 1 px for its 3 px cell line. A
        quantisation of the grid's *position* would be the same figure for
        both. The two widths are read off the page here, so this is the page's
        answer and not arithmetic restated.
        """
        assert (_RASTER_HEAVY_PX - 1) // 2 == 2
        assert (_RASTER_THIN_PX - 1) // 2 == 1

        page = _interior(_book(), [_puzzle(20, 20, 4)])[FIRST_PUZZLE_PAGE - 1]
        mask = np.asarray(page.convert("L")) < 128
        drawing = drawing_of(page)
        # The middle of a cell ROW, so the scan crosses the grid's vertical
        # rules and no horizontal one: a row landing on a horizontal rule
        # reads one unbroken run the whole width of the grid, which is the
        # reading this choice of row exists to avoid.
        inside = drawing.grid_top + round(drawing.cell / 2)
        # One cell past the right border, so the last rule's own run is whole:
        # ``grid_right`` is its FIRST inked column, which is the reading this
        # test is about, so a slice ending there would cut it to 1 px.
        spans = [
            len(group)
            for group in _consecutive(
                np.flatnonzero(
                    mask[
                        inside,
                        drawing.grid_left : drawing.grid_right + round(drawing.cell),
                    ]
                )
            )
        ]
        assert len(spans) == drawing.columns + 1, (len(spans), drawing.columns)

        assert max(spans) == _RASTER_HEAVY_PX, spans
        assert min(spans) == _RASTER_THIN_PX, spans
        # And the offset the corpus measured is half the heavier of the two,
        # which is the rule the grid's own borders are stroked at.
        offsets = {
            round((reading.raster_ink[edge] - reading.vector_stream[edge]) * PX_PER_MM)
            for reading in edge_corpus
            for edge in _GRID_EDGES
        }
        assert offsets == {-((max(spans) - 1) // 2)}, (offsets, spans)

    def test_the_two_media_ink_differs_by_one_device_pixel_not_two(
        self, edge_corpus
    ) -> None:
        """**The figure a conversion actually moves**, ink against ink.

        One oracle, one resolution, one page: the vector's rendered grid edge
        sits exactly one device pixel — 0.0847 mm — outside the raster's, on
        all four edges of every case, because the two media stroke different
        widths by design (ADR-0037/R2's declared 1.3 pt against COMP-007's
        proportional 6 px). That is **inside** :data:`EDGE_TOLERANCE_MM`, so
        the grid's own placed edges do not need the bound moved.
        """
        offsets = {
            round((reading.vector_ink[edge] - reading.raster_ink[edge]) * PX_PER_MM)
            for reading in edge_corpus
            for edge in _GRID_EDGES
        }
        assert offsets == {-1}, offsets
        assert 1 / PX_PER_MM < EDGE_TOLERANCE_MM, 1 / PX_PER_MM
        assert len(edge_corpus) >= _MIN_EDGE_CASES, len(edge_corpus)

    def test_the_drawings_own_edge_is_where_the_media_pass_the_tolerance(
        self, edge_corpus
    ) -> None:
        """And this is the figure CARD-322 inherits, which is 3 px and not 2.

        ``Drawing.left`` / ``Drawing.top`` are what every 25.45 mm assertion
        in this module reads, and there the raster's ink is **at** the
        specified margin — Pillow strokes a framed drawing as four butt-capped
        lines, so the frame's top side begins above where its left side does
        and the reading lands on the path. Poppler strokes the frame as one
        ``re`` and mitres its outer corner, which puts the same reading three
        device pixels further out: 0.254 mm, **outside**
        :data:`EDGE_TOLERANCE_MM`.

        It is still not a placement: both writers put the frame's left side at
        the same coordinate. It is a corner.
        """
        # The raster arm is a max rather than a per-reading assertion, so the
        # message names the worst case and the bound is the measured figure
        # (0.5437 px) rather than the derived ceiling — cycle 1's F-003.
        worst_raster = max(
            (
                abs((reading.raster_ink[edge] - reading.specified[edge]) * PX_PER_MM),
                reading.label,
                edge,
            )
            for reading in edge_corpus
            for edge in _DRAWING_EDGES
        )
        assert worst_raster[0] < _SPEC_DRAWING_MEASURED_PX, worst_raster
        for reading in edge_corpus:
            for edge in _DRAWING_EDGES:
                vector = (reading.vector_ink[edge] - reading.raster_ink[edge]) * PX_PER_MM
                assert round(vector) == -3, (reading.label, edge, vector)
        assert 3 / PX_PER_MM > EDGE_TOLERANCE_MM, 3 / PX_PER_MM
        # Every case is framed, which is what the mitre needs to exist: a
        # placed book page is framed by default (PageSpec.framed), and an
        # unframed one would be a different reading.
        assert all(reading.framed for reading in edge_corpus)


def _consecutive(indices: np.ndarray) -> list[list[int]]:
    """``indices`` split into runs of consecutive values — one run per rule."""
    groups: list[list[int]] = []
    for index in indices.tolist():
        if groups and index == groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


#: What :data:`EDGE_TOLERANCE_MM` admits **beyond** the 0.1 mm the ACs state,
#: each entry naming what it lets through and the card that removes it.
#:
#: **Empty, deliberately (CARD-330, AC-4/G-1).** The card was written against
#: the hazard of widening this bound to admit the vector medium, and the
#: measurement above is why it is not widened: the figure a conversion moves
#: on the grid's four edges is 1 device pixel (0.0847 mm), which 0.1 mm
#: already admits, and the figure it moves on the drawing's own edges —
#: 3 px, 0.254 mm — is a mitred frame corner read as a placed edge, so
#: widening to 0.3 mm would be loosening a placed-edge bound to admit an
#: instrument's artefact. What that reading needs is an oracle that reads the
#: frame rule's **centre** rather than its first inked line, which keeps it a
#: pixel oracle (G-2) and is CARD-322's to write with the conversion.
EDGE_TOLERANCE_EXEMPTIONS: dict[str, str] = {}

#: The placed-edge tolerance the ACs state, written out so a change to
#: :data:`EDGE_TOLERANCE_MM` has something to be a change *from*.
_STATED_EDGE_TOLERANCE_MM = 0.1


def _tolerance_is_declared(bound_mm: float, exemptions: dict[str, str]) -> bool:
    """Whether a placed-edge bound is one the board has actually declared.

    The standing rule in one predicate: the bound is either the figure the ACs
    state, with nothing exempted, or a wider one that ships **with** the
    exemptions naming what it now admits. A bound moved on its own is neither,
    and so is an exemption registered against the stated bound — a declaration
    for a widening that did not happen.
    """
    if bound_mm < _STATED_EDGE_TOLERANCE_MM:
        return False
    at_the_stated_bound = bound_mm == _STATED_EDGE_TOLERANCE_MM
    return at_the_stated_bound is not bool(exemptions)


class TestEdgeOffset_ATolerenceChangeCarriesItsExemption:
    """AC-4 — the bound is unchanged, and a change to it could not be silent.

    The name is the AC's own spelling, kept so the criterion and its test can
    be matched by search.
    """

    def test_the_bound_is_the_figure_the_criteria_state_and_nothing_is_exempt(
        self,
    ) -> None:
        assert EDGE_TOLERANCE_MM == _STATED_EDGE_TOLERANCE_MM, EDGE_TOLERANCE_MM
        assert EDGE_TOLERANCE_EXEMPTIONS == {}, EDGE_TOLERANCE_EXEMPTIONS
        assert _tolerance_is_declared(EDGE_TOLERANCE_MM, EDGE_TOLERANCE_EXEMPTIONS)

    def test_a_widening_without_its_exemption_is_refused(self) -> None:
        """The control, on the predicate, so it is not dormant.

        Both the figure that would admit the mitred corner and the smallest
        widening there is are refused while the register is empty — the second
        is the one that matters, because a bound creeps.
        """
        assert not _tolerance_is_declared(0.3, {})
        assert not _tolerance_is_declared(_STATED_EDGE_TOLERANCE_MM + 1e-9, {})

    def test_an_exemption_without_its_widening_is_refused_too(self) -> None:
        """And the other direction, so the pair is a biconditional.

        A register that filled up while the bound stayed at 0.1 mm would be a
        declaration for a widening nobody made — which reads, to the next
        card, as permission already granted.
        """
        assert not _tolerance_is_declared(
            _STATED_EDGE_TOLERANCE_MM, {"CARD-322": "the mitred frame corner"}
        )

    def test_a_widening_that_carries_its_exemption_is_admitted(self) -> None:
        """The arm AC-4 leaves open, asserted so the predicate is not a
        constant ``False`` for everything but today's pair."""
        assert _tolerance_is_declared(0.3, {"CARD-322": "the mitred frame corner"})

    def test_a_narrower_bound_is_refused_rather_than_silently_admitted(self) -> None:
        """Default-DENY on the third shape (ADR-0039/R2): a bound *below* the
        stated one is not "safe", it is a figure nobody declared, and it would
        red every placed-edge assertion in this module without saying why."""
        assert not _tolerance_is_declared(0.05, {})
        assert not _tolerance_is_declared(0.05, {"CARD-322": "a tighter bound"})


class TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium:
    """The owner's steer, made mechanical: medium-**pinned**, not medium-aware.

    *"Let's aim at switching on vector for the interior (not dividers) — don't
    spend much time on fixing-updating raster."* So the raster's placed-edge
    expectations are not re-tuned; they are pinned to the medium they were
    measured in, and CARD-322's conversion retires them. A pin written in
    prose would not notice a conversion, so it is derived instead: every
    assertion in this module that compares against
    :data:`EDGE_TOLERANCE_MM` must sit in a test that reads its page through
    ``page_ink.drawing_of`` — the raster ink oracle — and none may read a
    content stream. When CARD-322 converts a page under one of them, the
    reading changes medium and this goes red until the site says so.

    Default-DENY per ADR-0039/R2: a site whose medium cannot be determined is
    a FAILURE, not a pass — and, since CARD-330 cycle 1's F-002, a site that
    cannot be *told apart* is one too. The map is keyed on the
    **class-qualified** name because this module holds two different tests
    under one bare name, which keyed on the bare name silently dropped one of
    them; the walk returns a list so the key count can be asserted equal to
    the site count, and a future collision reds instead of shrinking the dict.

    **Two depths, and the difference is the point (CARD-329 cycle 1's
    F-001).** The requirement that a site read through ``drawing_of`` is
    stated on the site's **own body**, where the oracle call is written. The
    prohibition on reading a content stream is stated **twice**: once on the
    site's own body, and once on everything the site can *reach*, to a fixed
    point (:meth:`_closed_sites`). The second is not a stronger spelling of
    the first — it is the one that catches the shape the house style actually
    produces, a one-line ``interior_images(...)`` seam at the module's
    page-source helper rather than inside the test. Measured: the same
    crossing written inside a site is killed by either cell; written at
    ``_interior``, one frame in, only the closed one sees it.

    The set of readers that count as crossing is **derived** from the two
    owning helpers' source (:meth:`_stream_readers`), not written out — the
    hand-written form had an existence control and none for omission, and
    omission is the permissive direction.
    """

    #: The reader that makes a site's medium the raster bitmap.
    _RASTER_READER = "drawing_of"

    #: The two helpers that own every reader a site could reach across the
    #: medium: CARD-294's content-stream reader and CARD-329's page reader.
    _READER_OWNERS = (
        "tests/helpers/pdf_vector.py",
        "tests/helpers/pdf_pages.py",
    )

    #: Poppler's two engines. A function that reaches one of them reads the
    #: page **as drawn**, operators included, whatever medium it was written
    #: in — which is the whole hazard this class pins.
    _POPPLER_ENGINES = frozenset({"PDFTOPPM", "PDFTOTEXT"})

    #: The two PDF keys a page's content stream and its medium hang off.
    #: ``/Contents`` *is* the stream; ``/Resources`` is the dictionary whose
    #: ``/XObject`` and ``/Font`` keys are the only thing that says which
    #: medium a page is in (:func:`tests.helpers.pdf_vector.page_media`).
    _STREAM_KEYS = frozenset({b"Contents", b"Resources"})

    #: A parameter by this name is a decoded content stream handed in as
    #: text — the signature every operator reader in ``pdf_vector`` takes.
    _STREAM_PARAM = "stream"

    #: The public module-level readers of the two owners that the derivation
    #: below classifies as **not** crossing the medium, named here so the
    #: classification is a partition with nothing unclassified rather than a
    #: filter whose omissions are invisible.
    #:
    #: Each one reads either an already-rasterised array (``ink_mask``,
    #: ``ink_box``), a bitmap's pixels (``same_page``), the file's object
    #: table rather than any page's stream (``embedded_faces``,
    #: ``font_objects``, ``font_file_lengths``, ``base_font_names``), the page
    #: *tree*'s length (``pdf_page_count``), a page object's Python type
    #: (``page_medium_of``), or bytes it was handed (``to_buffer``). None of
    #: their answers moves when a page converts, which is exactly what makes
    #: a site calling one still medium-pinned.
    #:
    #: Held to existing — and to being disjoint from the derived set — by
    #: :meth:`test_every_public_reader_of_the_two_owners_is_classified`, so
    #: this cannot rot into a blanket exemption.
    _MEDIUM_BLIND_READERS = frozenset(
        {
            # tests/helpers/pdf_vector.py
            "base_font_names",
            "embedded_faces",
            "font_file_lengths",
            "font_objects",
            "ink_box",
            "ink_mask",
            "to_buffer",
            # tests/helpers/pdf_pages.py
            "page_medium_of",
            "pdf_page_count",
            "same_page",
        }
    )

    @classmethod
    def _owner_functions(cls) -> tuple[dict[str, tuple[set[str], set[str], set[bytes]]],
                                       set[str]]:
        """Every function of the two owners, and their public module-level names.

        ``{name: (its parameters, the names and attributes its body mentions,
        the bytes literals it holds)}`` — enough for the derivation below to
        decide, from the source, whether a reader can cross the medium.
        """
        root = pathlib.Path(__file__).resolve().parent.parent
        table: dict[str, tuple[set[str], set[str], set[bytes]]] = {}
        public: set[str] = set()
        for path in cls._READER_OWNERS:
            tree = ast.parse((root / path).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                params = {
                    argument.arg
                    for argument in (
                        node.args.posonlyargs
                        + node.args.args
                        + node.args.kwonlyargs
                    )
                }
                names = {
                    inner.id
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Name)
                } | {
                    inner.attr
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Attribute)
                }
                literals = {
                    inner.value
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Constant)
                    and isinstance(inner.value, bytes)
                }
                held = table.get(node.name, (set(), set(), set()))
                table[node.name] = (
                    held[0] | params,
                    held[1] | names,
                    held[2] | literals,
                )
            for node in tree.body:
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not node.name.startswith("_"):
                    public.add(node.name)
        return table, public

    @classmethod
    def _stream_readers(cls) -> frozenset[str]:
        """The readers that would make a site's medium the content stream —
        **derived** from the two owners' source, to a fixed point.

        The set used to be hand-written, and CARD-329 cycle 1's F-002 is what
        that cost: it had a control that every *listed* name was a real reader
        and none that a name which *should* be listed was, and omission from
        this set forbids nothing (ADR-0039/R2 makes that the wrong default).
        Measured at the time: ``pdf_vector`` defines 20 public functions, the
        set named 4 of them, and the one it most obviously wanted —
        ``rendered_page``, the stream reader that returns pixels and the one
        :func:`~tests.helpers.pdf_pages.page_image` itself delegates to — was
        absent.

        A function crosses the medium when its body reaches poppler
        (:data:`_POPPLER_ENGINES`), or holds one of the PDF keys a page's
        stream and medium hang off (:data:`_STREAM_KEYS`), or takes a decoded
        stream as a parameter (:data:`_STREAM_PARAM`) — and then, **to a fixed
        point**, when it calls anything that does. The closure is the same
        lesson :func:`_page_consuming_functions` learned: ``page_media`` reads
        no key itself, it asks ``page_resource_keys``, and ``interior_images``
        rasterises nothing itself, it calls ``page_image``.

        Narrowed to the owners' **public module-level** functions, because
        those are the names a test site can actually write.
        """
        table, public = cls._owner_functions()
        crossing = {
            name
            for name, (params, names, literals) in table.items()
            if names & cls._POPPLER_ENGINES
            or literals & cls._STREAM_KEYS
            or cls._STREAM_PARAM in params
        }
        # Bounded by the function count, and it terminates because `crossing`
        # only grows and stays a subset of the names enumerated above.
        for _round in range(len(table) + 1):
            grown = {
                name
                for name, (_params, names, _literals) in table.items()
                if name not in crossing and names & crossing
            }
            if not grown:
                break
            crossing |= grown
        return frozenset(crossing & public)

    #: The two placed-edge sites this module holds under **one** bare
    #: function name, in different classes. Keyed on the bare name, as the
    #: walk below was until CARD-330 cycle 1's F-002, one of them was
    #: overwritten and never checked — measured: converting the
    #: right-hand one to a content-stream reader left all four assertions in
    #: this class green, while the identical change to the left-hand one red
    #: two. Both are named here so neither can go back to being invisible.
    _COLLIDING_SITES = frozenset(
        {
            "TestBookPdf_DrawingCentredOnRightHandPage"
            "::test_the_drawing_sits_25_45_mm_from_the_left_trim_edge",
            "TestBookPdf_DrawingCentredOnLeftHandPage"
            "::test_the_drawing_sits_25_45_mm_from_the_left_trim_edge",
        }
    )

    @staticmethod
    def _walk() -> list[tuple[str, str, set[str]]]:
        """``(class-qualified name, bare name, the readers it calls)`` for
        every ``EDGE_TOLERANCE_MM`` comparison in this module, as a **list**.

        A list and not a dict, so :meth:`_sites`' own control can compare the
        two lengths: two sites that collapsed into one key would otherwise
        disappear rather than fail, which is exactly what ADR-0039/R2's
        default-DENY forbids.
        """
        tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
        found: list[tuple[str, str, set[str]]] = []

        def visit(node: ast.AST, prefix: tuple[str, ...]) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    visit(child, prefix + (child.name,))
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names = {
                        inner.id
                        for inner in ast.walk(child)
                        if isinstance(inner, ast.Name)
                    }
                    if "EDGE_TOLERANCE_MM" in names:
                        attributes = {
                            inner.attr
                            for inner in ast.walk(child)
                            if isinstance(inner, ast.Attribute)
                        }
                        found.append(
                            (
                                "::".join(prefix + (child.name,)),
                                child.name,
                                names | attributes,
                            )
                        )
                    visit(child, prefix + (child.name,))
                else:
                    visit(child, prefix)

        visit(tree, ())
        return found

    @classmethod
    def _sites(cls) -> dict[str, set[str]]:
        """``{class-qualified function: the readers it calls}`` for every
        ``EDGE_TOLERANCE_MM`` comparison in this module.

        **Class-qualified**, because the bare name is not unique in this
        module (see :data:`_COLLIDING_SITES`).
        """
        return {qualified: readers for qualified, _, readers in cls._walk()}

    @classmethod
    def _bare(cls, qualified: str) -> str:
        """The function part of a key.

        Used only where the class genuinely does not matter: the walk's own
        floor control, which asks whether a known test was found at all.
        It is deliberately **not** used to match the exemption register —
        that lookup stripped the class until cycle 2's F-008, and a bare
        name is not unique in this module (:data:`_COLLIDING_SITES`).
        """
        return qualified.rsplit("::", 1)[-1]

    @staticmethod
    def _callable_bodies() -> dict[str, set[str]]:
        """``{function name: the names and attributes its body mentions}`` for
        every function a site could call: this module's own and every
        ``tests/helpers`` module's.

        Keyed on the bare name and **unioned** across files, because a site
        names a callable and not a file — and a union is the default-DENY
        direction when two modules define the same name (CARD-329 cycle 1's
        F-001: a classification that depends on which file a reader came from
        is one the pin cannot make from a site's source).
        """
        root = pathlib.Path(__file__).resolve().parent
        paths = [root / "test_book_pdf.py"] + sorted(
            (root / "helpers").glob("*.py")
        )
        bodies: dict[str, set[str]] = {}
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                mentioned = {
                    inner.id
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Name)
                } | {
                    inner.attr
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.Attribute)
                }
                bodies.setdefault(node.name, set()).update(mentioned)
        return bodies

    @classmethod
    def _closed_sites(cls) -> dict[str, set[str]]:
        """``_sites()`` with each site's reader set closed over the call graph.

        A site's own body is depth 0; this follows every name it mentions into
        that callable's body, and on, **to a fixed point** — so a reader
        reached through this module's ``_interior`` or through a
        ``tests/helpers`` function is in the set. The fixed point is what
        makes "however indirectly" a property of the walk rather than a word
        in a docstring, which is the correction cycle 1's F-001 asked for.
        """
        bodies = cls._callable_bodies()
        closed: dict[str, set[str]] = {}
        for qualified, direct in cls._sites().items():
            reachable = set(direct)
            # Bounded by the callable count; terminates because `reachable`
            # only grows and stays inside the names enumerated above.
            for _round in range(len(bodies) + 1):
                grown: set[str] = set()
                for name in reachable:
                    grown |= bodies.get(name, set())
                if grown <= reachable:
                    break
                reachable |= grown
            closed[qualified] = reachable
        return closed

    def test_the_walk_finds_the_sites_it_is_supposed_to_guard(self) -> None:
        """The instrument's own control: a walk that found nothing would pass
        every assertion below. The count is a floor, not a frozen number, so
        a new placed-edge test does not red this on arrival."""
        sites = self._sites()
        assert len(sites) >= 10, sorted(sites)
        assert "test_the_drawing_sits_25_45_mm_from_the_left_trim_edge" in {
            self._bare(name) for name in sites
        }

    def test_no_two_sites_collapse_into_one_key(self) -> None:
        """F-002's control: a collision is a FAILURE, not a silent merge.

        The walk returns a list and the map is built from it, so the two
        lengths differ exactly when two sites share a key. Keyed on the bare
        function name this module already had one such pair, and the site it
        dropped could have started reading a content stream with all of this
        class's assertions still green. Both members of that pair are asserted
        present by key, so the dict can only shrink by a deliberate rename
        that G-6 forbids.
        """
        walked = self._walk()
        sites = self._sites()
        assert len(walked) == len(sites), (
            len(walked),
            len(sites),
            sorted(qualified for qualified, _, _ in walked),
        )
        assert self._COLLIDING_SITES <= set(sites), sorted(
            self._COLLIDING_SITES - set(sites)
        )

    #: The sites that name the bound without measuring a page with it:
    #: CARD-330's own, which assert the bound itself or compare one medium's
    #: figure against another's. Every site NOT listed here must read its
    #: page through the raster ink oracle, so a new site that measures
    #: nothing has to be added here deliberately — and every name listed is
    #: asserted to still exist, so the list cannot rot into a blanket
    #: exemption.
    #:
    #: **Class-qualified, exactly as :meth:`_sites` keys them — cycle 2's
    #: F-008.** The register used to hold bare function names and the two
    #: denies below consulted it through :meth:`_bare`, which strips the
    #: class. The bare name is not unique in this module (see
    #: :data:`_COLLIDING_SITES`), so a future site in ANY class whose bare
    #: name happened to equal a registered one was exempted from the closed
    #: deny AND from the raster-oracle requirement, with nothing added here
    #: and no cell reporting it — measured: the one-frame-in medium crossing
    #: written under its own name reds two cells, and the identical crossing
    #: with only its bare name changed to collide left all five green.
    #: Omission is the permissive direction (ADR-0039/R2), and this module
    #: has already lost a site to a bare-name collision once (CARD-330
    #: cycle 1's F-002), which is why :meth:`_sites` is keyed this way.
    _BOUND_ONLY_SITES = frozenset(
        {
            "TestEdgeOffset_ATolerenceChangeCarriesItsExemption"
            "::test_the_bound_is_the_figure_the_criteria_state_and_nothing_is_exempt",
            "TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_the_two_media_ink_differs_by_one_device_pixel_not_two",
            "TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels"
            "::test_the_drawings_own_edge_is_where_the_media_pass_the_tolerance",
        }
    )

    #: The cells that consult :data:`_BOUND_ONLY_SITES`. Named here so the
    #: lookup control below can resolve them by ``ast`` rather than trust a
    #: sentence: each one must match the register on the **whole** key.
    _EXEMPTING_CELLS = (
        "test_the_exemption_list_names_only_sites_that_exist",
        "test_every_site_reads_its_page_through_the_raster_ink_oracle",
        "test_no_site_reaches_a_stream_reader_through_a_helper_either",
    )

    def test_the_exemption_list_names_only_sites_that_exist(self) -> None:
        """No dead entry: a renamed test would otherwise leave a name that
        exempts nothing and hides the next site that takes it.

        Resolved on the **whole** key since cycle 2's F-008, so a register
        entry whose class moved is as dead as one whose function was renamed.
        The non-emptiness assertion is the control on this cell itself: a
        register that collapsed to ``frozenset()`` would satisfy every
        subset assertion here and silently exempt nothing while reading as
        a checked list.
        """
        sites = set(self._sites())
        assert self._BOUND_ONLY_SITES, "the exemption register is empty"
        assert self._BOUND_ONLY_SITES <= sites, sorted(
            self._BOUND_ONLY_SITES - sites
        )

    def test_the_exemption_lookup_does_not_strip_the_class(self) -> None:
        """F-008's control: the register is class-qualified **and consulted
        that way**, in both directions.

        Measured when the lookup stripped the class: the house one-frame-in
        seam (``interior_images`` at a module-level page-source helper),
        planted at a placed-edge site under its own name, reds two of this
        class's cells; the identical plant with only its bare name changed to
        collide with a registered entry in a *different* class left all five
        green and added nothing to the register. So both halves are asserted:

        * every entry is class-qualified and exempts the site it names;
        * the same bare name under any other class is **not** exempt;
        * and no consulting cell calls :meth:`_bare`, which is the exact
          degradation that opened the hole — a sentence in a docstring would
          not have caught it, so this half is resolved by ``ast``.
        """
        assert self._BOUND_ONLY_SITES, "the exemption register is empty"
        for entry in sorted(self._BOUND_ONLY_SITES):
            assert "::" in entry, entry
            # The negative direction: the bare name alone, and the bare name
            # under a class that is not the entry's, are both outside the
            # register — so a colliding site elsewhere stays denied.
            bare = self._bare(entry)
            assert bare not in self._BOUND_ONLY_SITES, bare
            assert (
                f"TestEdgeOffset_ANameThatCollidesInAnotherClass::{bare}"
                not in self._BOUND_ONLY_SITES
            ), bare

        tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
        consulting = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in self._EXEMPTING_CELLS
        }
        assert set(consulting) == set(self._EXEMPTING_CELLS), sorted(consulting)
        for name, node in sorted(consulting.items()):
            mentioned = {
                inner.attr
                for inner in ast.walk(node)
                if isinstance(inner, ast.Attribute)
            }
            assert "_BOUND_ONLY_SITES" in mentioned, name
            assert "_bare" not in mentioned, name

    def test_every_site_reads_its_page_through_the_raster_ink_oracle(self) -> None:
        for name, readers in self._sites().items():
            if name in self._BOUND_ONLY_SITES:
                continue
            assert self._RASTER_READER in readers, (name, sorted(readers))

    def test_every_stream_reader_named_here_is_a_real_reader(self) -> None:
        """No dead member: a name the guard treats as a reader that nothing in
        the two owners defines would forbid nothing, and the set would rot into
        a list of words while reading as a guard.

        Each is resolved to a ``def`` in the helper that owns it — not to a
        mention, which is the distinction CARD-309 had to correct and
        CARD-329 re-derived (a check ref that resolves to a text hit warns
        about nothing while verifying nothing). Since cycle 1's F-002 the set
        is derived from those definitions rather than written out, so this cell
        is now a control on the **derivation's plumbing**: a walk that started
        collecting call sites, imports or docstring words instead of
        definitions would pass nothing here.
        """
        root = pathlib.Path(__file__).resolve().parent
        defined: set[str] = set()
        for path in self._READER_OWNERS:
            tree = ast.parse((root.parent / path).read_text(encoding="utf-8"))
            defined |= {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
        readers = self._stream_readers()
        assert readers, "the derivation found no stream reader at all"
        assert readers <= defined, sorted(readers - defined)

    def test_every_public_reader_of_the_two_owners_is_classified(self) -> None:
        """F-002's completeness control: a **partition**, not a filter.

        The hand-written set had an existence control and none for omission,
        and under ADR-0039/R2 omission is the permissive direction — a stream
        reader missing from it forbade nothing. So every public module-level
        function of the two owners must land either in the derived set or in
        :data:`_MEDIUM_BLIND_READERS`, and in exactly one of them. A reader
        added to ``pdf_vector`` or ``pdf_pages`` that the derivation does not
        recognise reds here instead of quietly being allowed under the bound.
        """
        _table, public = self._owner_functions()
        readers = self._stream_readers()
        assert public, "the walk found no public reader in either owner"
        assert not (readers & self._MEDIUM_BLIND_READERS), sorted(
            readers & self._MEDIUM_BLIND_READERS
        )
        assert readers | self._MEDIUM_BLIND_READERS == public, {
            "unclassified": sorted(public - readers - self._MEDIUM_BLIND_READERS),
            "named but not public": sorted(
                (readers | self._MEDIUM_BLIND_READERS) - public
            ),
        }

    def test_the_derivation_decides_both_directions_and_not_just_one(
        self,
    ) -> None:
        """The control on the classifier itself — `cycle 1 F-002`.

        A derivation that returned every public function would satisfy the
        partition above as surely as the right one, so both directions are
        named. The crossing direction holds the seven the set carried when it
        was hand-written **plus** the member it was missing; the blind
        direction holds the readers whose answer a conversion cannot move.
        """
        readers = self._stream_readers()
        was_declared = {
            "content_streams",
            "operator_tokens",
            "operator_tally",
            "page_media",
            "page_image",
            "interior_images",
            "pdf_pages",
        }
        assert was_declared <= readers, sorted(was_declared - readers)
        # The member the hand-written set omitted, and the one `page_image`
        # itself delegates to: the stream reader that returns pixels.
        assert "rendered_page" in readers, sorted(readers)
        assert {"extracted_text", "word_boxes"} <= readers, sorted(readers)
        # And the other direction: these read a page that is already pixels,
        # or the file's object table, so a conversion moves no answer of
        # theirs. A derivation that said "crossing" to all of them would be
        # a constant, not a classifier.
        assert not (readers & {"ink_mask", "ink_box", "to_buffer", "same_page"}), (
            sorted(readers & {"ink_mask", "ink_box", "to_buffer", "same_page"})
        )

    def test_the_pixel_returning_stream_readers_really_cross_the_medium(
        self,
    ) -> None:
        """The reason the three ``pdf_pages`` members are in the set: each one
        can be handed an operators page and hand back pixels.

        Asserted on the reader, not on the derivation — a name the walk
        classified as crossing by reading its source would pass the cells
        above and this one would not.
        """
        _generator, bitmap, stream = _one_vector_page()
        assert page_medium_of(stream) == "vector"
        crossed = page_image(stream)
        assert isinstance(crossed, Image.Image), type(crossed)
        assert crossed.size == bitmap.size
        # And the raster side does NOT cross: the same call on a bitmap is the
        # identity, which is what makes the medium the page's and not the
        # reader's.
        assert page_image(bitmap) is bitmap

    def test_no_site_reads_a_content_stream(self) -> None:
        """G-2 and the pin together: these expectations are the raster's, and
        a site that quietly started reading the stream would be asserting a
        0.169 mm different number against the same bound.

        Depth 0 — the reader named in the site's **own** body. The frame below
        is where the house style would actually put it.
        """
        readers = self._stream_readers()
        for name, called in self._sites().items():
            assert not (called & readers), (name, sorted(called & readers))

    def test_no_site_reaches_a_stream_reader_through_a_helper_either(
        self,
    ) -> None:
        """The same deny, closed over the call graph — `cycle 1 F-001`.

        The pin was shut at depth 0 only, and measured: with the three
        ``pdf_pages`` names in the set, a medium crossing written *inside* a
        site was killed, and the identical crossing written one frame in — at
        this module's own page-source helper, ``_interior`` — **survived**.

        That is not an exotic shape. The one-line seam
        ``interior_images(...)`` at a module's page-source function is exactly
        what CARD-329 standardised across five modules and exactly what
        CARD-322 is instructed to apply to nine more; applied here it would
        have silently retired this pin over 30 of the 38 reds the card says
        it protects. The lesson was already on the board one walk over:
        :func:`_page_consuming_functions` needs a fixed point because
        ``drawing_of`` hands its page to ``_dark`` one frame in. The closure
        was applied to the population walk and not to this pin; this is that
        correction.

        :data:`_BOUND_ONLY_SITES` is exempt here for the reason it is exempt
        from the raster-oracle cell: those sites measure no page with the
        bound, they *compare the two media's* figures against it, so reaching
        a stream reader is their job — and, measured, both of them do
        (``content_streams`` and ``rendered_page``, through ``_edge_reading``).
        Every other site must reach none.

        The exemption is matched on the **whole** key, class included —
        cycle 2's F-008. Matched on the bare name, as it was, any future
        site in any class could take a registered name and buy itself out of
        this deny and the raster-oracle cell at once, with nothing added to
        the register; measured, that dodge turned a two-cell red into five
        green. :meth:`test_the_exemption_lookup_does_not_strip_the_class` is
        the control.
        """
        readers = self._stream_readers()
        for name, reachable in self._closed_sites().items():
            if name in self._BOUND_ONLY_SITES:
                continue
            assert not (reachable & readers), (
                name,
                sorted(reachable & readers),
            )

    def test_the_site_walk_closes_over_the_call_graph_it_claims_to(
        self,
    ) -> None:
        """F-001's own control: the closure is a property of the walk, not a
        sentence in the docstring above it.

        Stated on the site the plant used, and in both directions: the
        reader set the site's body names must be a **strict** subset of what
        it can reach, and the names that prove the further frames were
        entered are the ones the site itself never writes. The page-source
        chain at this site is three frames deep —
        ``_mirrored_pages`` → ``_interior`` → ``interior_pages`` — and
        ``_interior`` is where the seam goes, so a closure removed, or taken
        at depth 1 and *called* a fixed point, fails here.

        And it is **not only** those two depths, which is cycle 2's scope
        note: hard-stopped at two rounds this cell still passed, because
        every name it named is within two frames. The oracle chain at this
        same site runs one frame further — ``drawing_of`` → ``_dark`` →
        ``ink_mask`` → :data:`~tests.helpers.page_ink.INK_LEVEL`, and no
        body nearer than ``ink_mask``'s mentions that threshold — so the
        depth-3 assertion below reds any bounded stop at 2 as well. The walk
        itself settles at 4 rounds here, measured.
        """
        direct = self._sites()
        closed = self._closed_sites()
        site = (
            "TestBookPdf_DrawingCentredOnRightHandPage"
            "::test_the_drawing_sits_25_45_mm_from_the_left_trim_edge"
        )
        assert site in direct and site in closed, sorted(direct)
        # Depth 0: the only page-source name the site's own body writes.
        assert "_mirrored_pages" in direct[site], sorted(direct[site])
        assert "_interior" not in direct[site], sorted(direct[site])
        # Depth 1, and the function a seam edit would change.
        assert "_interior" in closed[site], sorted(closed[site])
        # Depth 2: `_interior`'s own body, two frames from the site — so this
        # is a fixed point and not one extra hop.
        assert "interior_pages" in closed[site], sorted(closed[site])
        assert direct[site] < closed[site], (
            len(direct[site]),
            len(closed[site]),
        )
        # And the lesson that taught the board the closure: `drawing_of`
        # reads nothing off its own page and hands it to `_dark`.
        assert "drawing_of" in direct[site]
        assert "_dark" in closed[site], sorted(closed[site])
        # Depth 2 and depth 3 on that same chain: `_dark` asks `ink_mask`,
        # whose body is the only one within reach that names the threshold.
        # A walk hard-stopped at two rounds reaches `ink_mask` and stops,
        # passing everything above and failing the next line.
        assert "ink_mask" in closed[site], sorted(closed[site])
        assert "INK_LEVEL" in closed[site], sorted(closed[site])


class TestEdgeOffset_ThePixelOraclesStillReadPixels:
    """AC-5 — ``drawing_of`` and ``two_up_ink`` are still oracles.

    R6 exempts them by name as independent second implementations, and an
    oracle that shared the subject's mechanism would have stopped being one
    (CLAUDE.md's stated reason for having two). CARD-330 changed their
    *documentation* and not their reading, and this is what says so.
    """

    _ORACLES = ("tests/helpers/page_ink.py", "tests/helpers/two_up_ink.py")

    @staticmethod
    def _module(path: str) -> ast.Module:
        root = pathlib.Path(__file__).resolve().parent.parent
        return ast.parse((root / path).read_text(encoding="utf-8"))

    def test_neither_oracle_imports_the_content_stream_reader(self) -> None:
        for path in self._ORACLES:
            imported = {
                name
                for node in ast.walk(self._module(path))
                for name in (
                    [alias.name for alias in node.names]
                    if isinstance(node, (ast.Import, ast.ImportFrom))
                    else []
                )
            }
            assert not {"pdf_vector", "tests.helpers.pdf_vector"} & imported, (
                path,
                sorted(imported),
            )

    #: What each oracle's own measuring entry point has to go through: the
    #: ink mask, which *is* the pixel reading. ``two_up_ink``'s
    #: :func:`~tests.helpers.two_up_ink.drawings_of` reaches it one step
    #: further out — it finds the page's split row and hands each half to
    #: ``page_ink``'s own reader — so the two functions named here are the
    #: ones that touch a bitmap, and ``drawings_of`` is checked to still
    #: delegate to the first of them.
    _MASK_READERS = frozenset({"_dark", "ink_mask"})

    def _calls(self, path: str, function: str) -> set[str]:
        found = [
            node
            for node in ast.walk(self._module(path))
            if isinstance(node, ast.FunctionDef) and node.name == function
        ]
        assert len(found) == 1, (path, function, len(found))
        return {
            inner.id for inner in ast.walk(found[0]) if isinstance(inner, ast.Name)
        }

    def test_the_measuring_functions_still_reduce_a_bitmap_to_a_mask(self) -> None:
        """The positive half, on each oracle's own pixel-reading entry point."""
        for path, function in (
            ("tests/helpers/page_ink.py", "drawing_of"),
            ("tests/helpers/two_up_ink.py", "split_row"),
        ):
            called = self._calls(path, function)
            assert called & self._MASK_READERS, (path, function, sorted(called))

    def test_the_two_up_reader_still_delegates_to_the_pixel_oracle(self) -> None:
        """So ``two_up_ink`` cannot have grown a reading of its own that is
        not ``page_ink``'s — the cross-check lives in having one reader."""
        assert "drawing_of" in self._calls(
            "tests/helpers/two_up_ink.py", "drawings_of"
        )

    def test_drawing_of_still_takes_a_page_and_not_a_file(self) -> None:
        """Behaviourally, not just structurally: it reads an image, so bytes
        are not a page it can measure."""
        page = _interior(_book(), [_puzzle(15, 15, 7)])[FIRST_PUZZLE_PAGE - 1]
        assert drawing_of(page).columns == 15
        with pytest.raises((AttributeError, TypeError, ValueError)):
            drawing_of(b"%PDF-1.4")


class TestEdgeOffset_TheAdrRecordsTheCanonicalMedium:
    """AC-3 — the answer lives in ADR-0042, in one place, for three cards.

    CARD-312, CARD-322 and CARD-329 all read this decision, so it is recorded
    where a rule is recorded rather than in a card's notes.
    """

    @staticmethod
    def _adr() -> str:
        root = pathlib.Path(__file__).resolve().parent.parent
        path = (
            root
            / "meta/architecture/decisions/adr"
            / "0042-book-interior-is-vector-cover-stays-raster.md"
        )
        assert path.exists(), path
        return path.read_text(encoding="utf-8")

    def test_it_names_the_canonical_medium_for_a_placed_edge_claim(self) -> None:
        adr = self._adr().lower()
        assert "card-330" in adr
        assert "canonical for a placed-edge claim" in adr
        # And names which medium it is, beside the question.
        where = adr.index("canonical for a placed-edge claim")
        assert "content stream" in adr[where : where + 400], adr[where : where + 400]

    def test_it_records_the_three_numbers_and_what_the_gap_turned_out_to_be(
        self,
    ) -> None:
        """The figures, not just the verdict: a reader who only has the
        verdict re-measures, and this board has re-measured this one twice."""
        adr = self._adr()
        for figure in ("0.0847", "0.254", "1.3 pt"):
            assert figure in adr, figure

    def test_it_records_that_the_device_floor_is_unresolved_for_the_interior(
        self,
    ) -> None:
        """ADR-0037/R2 holds furniture to a 2-device-pixel floor and
        ADR-0042/R7 makes the floor inapplicable to the interior. Nothing on
        the board owns the collision, two cards wait on it, and this ADR must
        say so rather than let a reader infer a floor neither rule grants."""
        adr = self._adr()
        assert "unresolved for interior furniture" in adr
        assert "ADR-0037/R2" in adr and "R7" in adr
        assert "CARD-208" in adr and "CARD-226" in adr
        # The figure that makes the question real, at the resolution it was
        # measured at — an instrument's domain is part of its figure.
        assert "150 DPI" in adr and "1200 DPI" in adr


# ==========================================================================
# CARD-329 — the one-image reader learns the content stream
#
# ADR-0042/R1 writes an interior page as content-stream operators, and such a
# page has NO image XObject. `tests/helpers/pdf_pages.py` indexed
# `Resources/XObject` unconditionally, so a legal page came back as
# `KeyError: b'XObject'` from a line that reads as a parse failure. These
# three sections are AC-1, AC-2 and AC-3 of that card.
#
# Why the tests live HERE: this module already owns the book PDF's read-back
# (see its own header) and already holds the only other call in this tree that
# writes one `ContentStream` out and measures poppler's raster of it
# (`_edge_reading`). `tests/helpers/pdf_pages.py` is in CARD-329's `Touches`
# and so is this file.
# ==========================================================================


def _one_vector_page(page: int = FIRST_PUZZLE_PAGE):
    """One puzzle page as operators, with the bitmap of the same page beside it.

    Both from the same generator, the same payload and the same cell map, so
    the only difference between the two is the medium -- the shape
    `_edge_reading` above takes, and for its reason.
    """
    generator = BookPDFGenerator(_book())
    payload = BookPDFGenerator._payload(_puzzle(10, 10, 2, name="Reader"))
    sizes = generator.cell_sizes([payload])
    bitmap = generator._blank_page(payload, 1, page, sizes)
    stream = generator.vector_puzzle_page(payload, 1, page, sizes)
    return generator, bitmap, stream


#: The DPI every book page is drawn at (``BookPDFGenerator.dpi``'s default),
#: named here because the reader's refusal control hands it back in.
_READER_DPI = 300
#: A pixel darker than this (0..255 grey) is ink -- the level
#: ``tests/helpers/pdf_pages.py`` and ``page_ink.py`` both read at.
_READER_INK_LEVEL = 128


def _old_one_image_reader(data: bytes) -> list[bytes]:
    """CARD-135's reader, reimplemented here: every page's decoded RGB bytes.

    The **reference** AC-2 is measured against, and deliberately a second
    implementation rather than a call to the helper under test: re-deriving
    "unchanged" with the function whose change is in question proves nothing
    (CLAUDE.md, "prefer an independent second implementation"). This is the
    body `pdf_pages` had before CARD-329, reduced to the bytes it produced --
    `Resources/XObject` indexed unconditionally, the one DCTDecode stream
    decoded by Pillow, converted to RGB.
    """
    from io import BytesIO

    from PIL import PdfParser

    parser = PdfParser.PdfParser(buf=data)
    try:
        out = []
        for ref in parser.pages:
            page = parser.read_indirect(ref)
            xobjects = page[b"Resources"][b"XObject"]
            assert len(xobjects) == 1
            (stream_ref,) = xobjects.values()
            stream = parser.read_indirect(stream_ref)
            assert stream.dictionary[b"Filter"] == b"DCTDecode"
            image = Image.open(BytesIO(stream.buf))
            image.load()
            out.append(image.convert("RGB").tobytes())
        return out
    finally:
        parser.close()


class TestPdfPagesReader_AnOperatorsPageIsNotAKeyError:
    """AC-1 — a page written as operators reads, and never as `KeyError`.

    The exception the defect raised is the thing asserted against: a legal
    page is not a parse failure. Three arms, because the reader has three
    doors an operators page can arrive at -- a live page object, a page inside
    a file, and the classification both go through.
    """

    def test_a_live_operators_page_reads_as_pixels_and_not_as_a_key_error(
        self, tmp_path
    ) -> None:
        _generator, bitmap, stream = _one_vector_page()
        # The defect, asserted as an absence: nothing in this call may raise
        # KeyError, and in particular not on b"XObject".
        try:
            image = page_image(stream, out_dir=tmp_path)
        except KeyError as key_error:  # pragma: no cover - the defect
            raise AssertionError(
                f"the reader still raises KeyError({key_error!r}) on a legal "
                f"operators page"
            ) from key_error
        assert isinstance(image, Image.Image), type(image)
        # Device pixels at the page's own DPI -- the same extent the bitmap of
        # the same page has, which is what puts the two readings in one domain
        # (CARD-330). Equality, not a tolerance: both are the same MediaBox
        # at the same DPI, so a difference here is a scale error, not noise.
        assert image.size == bitmap.size, (image.size, bitmap.size)
        # And it really carries the drawing: a blank render would satisfy
        # every assertion above.
        assert np.asarray(image.convert("L")).min() < _READER_INK_LEVEL, "no ink"

    def test_an_operators_page_inside_a_file_reads_beside_its_raster_pages(
        self, tmp_path, monkeypatch
    ) -> None:
        """A file that mixes the media -- ADR-0042/R2's own sanctioned end
        state, not a migration artefact -- read back in one call.

        **The counterfactual, and why it has to be one.** Every one of the
        seven page kinds is declared raster on `main`
        (`_RASTER_DECLARATIONS`), so there is no kind this test could ask the
        writer for that would come back as operators: a mixed file cannot be
        built from the rules in force. So the declaration is lifted for the
        duration of this one test -- `monkeypatch` puts it back -- which is
        the mechanism CARD-329's own session probe uses for a whole run and
        the state CARD-322's conversion will make permanent. Nothing on disk
        changes and no page is converted (G-1): this test stands the
        counterfactual up, it does not perform it.
        """
        monkeypatch.delitem(_RASTER_DECLARATIONS, PageKind.PUZZLE, raising=False)
        assert page_medium(PageKind.COVER) is PageMedium.RASTER
        assert page_medium(PageKind.PUZZLE) is PageMedium.VECTOR, (
            "the lift did not take, so this test measures a raster file"
        )
        generator, bitmap, stream = _one_vector_page()
        written = generator._write_pdf(
            [bitmap, stream],
            2,
            mode="RGB",
            kinds=[PageKind.COVER, PageKind.PUZZLE],
        ).getvalue()

        raster_page, vector_page = pdf_pages(written, out_dir=tmp_path)
        assert raster_page.size == vector_page.size
        # Both pages carry ink, and they are NOT the same array: this arm's
        # control against a reader that read page 1 twice and called the
        # second one page 2. Stated on the arrays rather than through
        # `same_page`, because `same_page`'s tolerances were calibrated for a
        # JPEG round trip and comparing a poppler render with a Pillow bitmap
        # through them would be an instrument used outside its domain
        # (CARD-330).
        assert np.asarray(vector_page.convert("L")).min() < _READER_INK_LEVEL
        assert raster_page.tobytes() != vector_page.tobytes()
        # The raster half of a MIXED file is read exactly as the pre-CARD-329
        # reader read an all-raster one: measured byte for byte against
        # `_old_one_image_reader` over the same bitmap written on its own, so
        # the comparison is one JPEG decode against another -- like with like
        # (CARD-330), and no tolerance in sight.
        raster_only = generator._write_pdf(
            [bitmap], 1, mode="RGB", kinds=[PageKind.COVER]
        ).getvalue()
        (reference,) = _old_one_image_reader(raster_only)
        assert raster_page.tobytes() == reference

    def test_a_file_whose_dpi_cannot_be_established_is_refused_by_name(
        self,
    ) -> None:
        """The one case the reader cannot answer, and it says so.

        An all-operators file carries no raster page to derive a DPI from, so
        there is no scale to rasterise at. ADR-0039/R2: a shape the reader
        cannot analyse is a FAILURE -- named, not guessed at.
        """
        _generator, _bitmap, stream = _one_vector_page()
        written = book_vector.write_vector_pdf([stream], 1).getvalue()
        with pytest.raises(PageMediumRefused) as refused:
            pdf_pages(written)
        message = str(refused.value)
        assert "operators" in message, message
        assert "ADR-0042/R1" in message, message
        assert "dpi=" in message, message

    def test_the_same_file_reads_when_the_caller_names_the_dpi(
        self, tmp_path
    ) -> None:
        """The matched control for the refusal above: the refusal is about a
        missing scale and nothing else, so naming the scale reads the file."""
        _generator, bitmap, stream = _one_vector_page()
        written = book_vector.write_vector_pdf([stream], 1).getvalue()
        (page,) = pdf_pages(written, dpi=_READER_DPI, out_dir=tmp_path)
        assert page.size == bitmap.size, (page.size, bitmap.size)

    def test_a_missing_poppler_is_a_missing_reading_and_never_a_skip(
        self, monkeypatch
    ) -> None:
        """AC-1's other refusal arm, driven -- `cycle 1 F-003`.

        The card states this as doctrine ("a missing engine is a missing
        reading, never a skip", ADR-0038/R8) and until now nothing in the tree
        set :data:`tests.helpers.pdf_vector.PDFTOPPM` to ``None``: the branch
        was two `raise` statements no control could reach, which ADR-0039/R1
        forbids. Both doors are driven, because both carry the branch --
        `page_image` for a live page and `pdf_pages` for one inside a file.

        The first assertion is the **matched control** and it is deliberately
        a failure and not a skip on a host without poppler: this card's reader
        depends on the engine, and a cell that skipped itself away here would
        be the very thing the doctrine forbids.
        """
        assert pdf_vector.PDFTOPPM is not None, (
            "poppler's pdftoppm is not on this host, so this card's reader has "
            "no engine: the reading is MISSING, not passed (ADR-0038/R8)"
        )
        _generator, _bitmap, stream = _one_vector_page()
        monkeypatch.setattr(pdf_vector, "PDFTOPPM", None)

        with pytest.raises(PageMediumRefused) as refused:
            page_image(stream)
        message = str(refused.value)
        assert "pdftoppm" in message, message
        assert "MISSING" in message, message
        assert "operators" in message, message

        # The same branch in `pdf_pages`, reached with the DPI named so the
        # file gets past the scale refusal above and fails on the engine.
        written = book_vector.write_vector_pdf([stream], 1).getvalue()
        with pytest.raises(PageMediumRefused) as refused_in_file:
            pdf_pages(written, dpi=_READER_DPI)
        in_file = str(refused_in_file.value)
        assert "pdftoppm" in in_file, in_file
        assert "MISSING" in in_file, in_file

    def test_raster_pages_at_disagreeing_dpis_are_refused_not_averaged(
        self, tmp_path, monkeypatch
    ) -> None:
        """`_derived_dpi`'s second ``None`` arm, driven -- `cycle 1 F-003`.

        Both the function's docstring and the refusal's own text state this
        case ("this file's N raster page(s) do not settle one") and only the
        *zero*-raster-page arm was exercised. A file whose raster pages
        disagree has no single scale, and guessing one would put the vector
        page's reading in a domain nobody named.

        **The file is synthesised, because this tree's writer cannot produce
        one.** Pillow's PDF writer takes one resolution per file and derives
        every MediaBox from it, so pixel width over box width is constant
        across the pages it writes -- which is exactly why the branch needs an
        adversarial file rather than a counterfactual declaration. One page's
        MediaBox width is halved **in the written bytes, at equal byte
        length**, so the file's xref offsets stay valid and only the physical
        extent of page 1 changes: 2550 px over 4.25 in (600 DPI) beside
        2550 px over 8.5 in (300 DPI).
        """
        monkeypatch.delitem(_RASTER_DECLARATIONS, PageKind.PUZZLE, raising=False)
        generator, bitmap, stream = _one_vector_page()
        written = generator._write_pdf(
            [bitmap, bitmap, stream],
            3,
            mode="RGB",
            kinds=[PageKind.COVER, PageKind.DIVIDER, PageKind.PUZZLE],
        ).getvalue()

        # The matched control FIRST: the unpatched file's two raster pages
        # agree, so the scale is derived and the file reads. Without this the
        # cell below could pass on a file that was broken some other way.
        agreeing = pdf_pages(written, out_dir=tmp_path)
        assert len(agreeing) == 3, len(agreeing)
        assert agreeing[2].size == bitmap.size, (agreeing[2].size, bitmap.size)

        box = b"/MediaBox [ 0 0 612.0 792.0 ]"
        assert written.count(box) == 3, written.count(box)
        halved = box.replace(b"612.0", b"306.0", 1)
        assert len(halved) == len(box), (len(halved), len(box))
        patched = written.replace(box, halved, 1)
        assert len(patched) == len(written), (len(patched), len(written))

        with pytest.raises(PageMediumRefused) as refused:
            pdf_pages(patched)
        message = str(refused.value)
        assert "do not settle one" in message, message
        assert "2 raster page(s)" in message, message
        assert "dpi=" in message, message
        # And naming the scale reads the same patched file, so the refusal is
        # about the disagreement and nothing else.
        read = pdf_pages(patched, dpi=_READER_DPI, out_dir=tmp_path)
        assert len(read) == 3, len(read)

    def test_the_dpi_derivation_itself_answers_none_only_when_it_must(
        self,
    ) -> None:
        """The same arm at the function, both directions -- `cycle 1 F-003`.

        `_derived_dpi` is a pure function of a file's boxes and its decoded
        raster pages, so its three outcomes can be stated directly: a derived
        figure when the pages agree, ``None`` when they disagree, and ``None``
        when there is nothing to derive from. The cell above drives the middle
        one through the reader; this one pins all three, so a future
        `len(derived) != 1` relaxed to `>= 1` (which would silently pick a
        page) reds here as well as there.
        """
        two_inch = (0.0, 0.0, 144.0, 216.0)
        one_inch = (0.0, 0.0, 72.0, 108.0)
        at_300 = Image.new("RGB", (600, 900), "white")
        also_300 = Image.new("RGB", (300, 450), "white")

        assert _derived_dpi([two_inch, one_inch], {0: at_300, 1: also_300}) == 300.0
        assert _derived_dpi([two_inch, two_inch], {0: at_300, 1: also_300}) is None
        assert _derived_dpi([two_inch, one_inch], {}) is None

    def test_a_page_in_neither_medium_is_a_failure_not_a_silent_pass(self) -> None:
        """ADR-0039/R2 at the classification itself."""
        with pytest.raises(PageMediumRefused) as refused:
            page_medium_of("a page is not a string")
        assert "str" in str(refused.value)

    def test_the_medium_of_each_page_is_named_rather_than_guessed(self) -> None:
        _generator, bitmap, stream = _one_vector_page()
        assert page_medium_of(bitmap) == "raster"
        assert page_medium_of(stream) == "vector"


class TestPdfPagesReader_ARasterPageIsUnchanged:
    """AC-2 — the raster path behaves exactly as before, byte for byte.

    The cover and the divider stay raster by ADR-0042/R2, so this is not a
    legacy path: it is half of the end state. Measured against
    `_old_one_image_reader`, a second implementation of CARD-135's reader,
    rather than against the reader under test.
    """

    def test_an_all_raster_file_reads_byte_for_byte_as_it_did_before(self) -> None:
        book = _book()
        export = BookPDFGenerator(book).export_book(
            [_puzzle(10, 10, 2, name="Raster")], book.metadata.title
        )
        data = export.cover.getvalue()
        assert _old_one_image_reader(data), "the reference read nothing"
        assert [page.tobytes() for page in pdf_pages(data)] == (
            _old_one_image_reader(data)
        )

    def test_every_raster_page_of_a_whole_book_is_unchanged(self) -> None:
        """The interior too, not just the one-page cover: on `main` every
        interior page is a bitmap, so this is the regression AC-2 names."""
        book = _book()
        export = BookPDFGenerator(book).export_book(
            [_puzzle(10, 10, 2, name="A"), _puzzle(12, 12, 2, name="B")],
            book.metadata.title,
        )
        data = export.interior.getvalue()
        reference = _old_one_image_reader(data)
        assert len(reference) > 5, f"only {len(reference)} pages compared"
        assert [page.tobytes() for page in pdf_pages(data)] == reference

    def test_a_live_raster_page_is_handed_back_as_the_very_same_object(
        self,
    ) -> None:
        """Identity, which is stronger than equal bytes and is what "exactly
        as before" means for a caller that reads `tobytes()` off the page: the
        reader did not convert, copy or re-encode it."""
        _generator, bitmap, _stream = _one_vector_page()
        assert page_image(bitmap) is bitmap
        pages = interior_images([bitmap, bitmap])
        assert pages[0] is bitmap and pages[1] is bitmap

    def test_the_reference_reader_can_tell_a_changed_page(self) -> None:
        """The control for both cells above: `_old_one_image_reader` is not
        answering "equal" to everything. Without this the two byte-for-byte
        assertions would pass against a reference that returned a constant."""
        book = _book()
        export = BookPDFGenerator(book).export_book(
            [_puzzle(10, 10, 2, name="Raster")], book.metadata.title
        )
        cover = _old_one_image_reader(export.cover.getvalue())
        interior = _old_one_image_reader(export.interior.getvalue())
        assert cover != interior[:1]


#: CARD-329 AC-3, population A's filter, as code: a module is in A when its
#: own AST contains an ``ImportFrom`` of the one-image reader's module that
#: names ``pdf_pages`` -- the reader itself. A module importing only
#: ``pdf_page_count`` or ``same_page`` is NOT in A, because neither of those
#: ever reaches an image XObject and so neither can meet the hazard.
_READER_MODULE = "tests.helpers.pdf_pages"
_READER_NAME = "pdf_pages"

#: Population B's filter: the page SOURCE. A module in B never imports the
#: reader and reaches the same hazard through one of these.
_PAGE_SOURCES = frozenset({"interior", "interior_pages"})

#: The PIL image surface a page is used *as an image* through. Reading any of
#: these off a page is the hazard: a page written as operators is a
#: ``ContentStream`` and has none of them.
_PIL_IMAGE_SURFACE = frozenset(
    {
        "size", "width", "height", "mode", "getpixel", "crop", "convert",
        "load", "resize", "reduce", "tobytes", "getbbox", "getdata",
        "point", "split", "paste", "copy", "save", "transpose", "rotate",
    }
)

#: The three files CARD-329 deliberately does not own (G-2, G-3). Each IS in
#: a population -- they are excluded from the card's `Touches`, not from the
#: derivation, which is the distinction ADR-0039/R2 turns on.
_NOT_THIS_CARDS = {
    "tests/test_book_difficulty_dots.py": "CARD-331 (G-3)",
    "tests/helpers/round_ink.py": "CARD-331 (G-3)",
    "tests/helpers/page_ink.py": "CARD-330 (G-2)",
}

#: The five population-B modules CARD-329 repairs (its `Touches`, less the
#: helper and this file).
_REPAIRED_BY_CARD_329 = frozenset(
    {
        "tests/test_book_pdf_levels.py",
        "tests/test_book_pdf_two_up.py",
        "tests/property/test_book_pdf_geometry.py",
        "tests/test_book_puzzle_frame.py",
        "tests/test_book_cell_size.py",
    }
)


def _test_tree_modules() -> list[pathlib.Path]:
    root = pathlib.Path(__file__).resolve().parent
    return sorted(
        path
        for path in root.rglob("*.py")
        if path.name != "__init__.py" and "fixtures" not in path.parts
    )


def _as_posix(path: pathlib.Path) -> str:
    return path.relative_to(pathlib.Path(__file__).resolve().parents[1]).as_posix()


def _helper_imports(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _READER_MODULE:
            names |= {alias.name for alias in node.names}
    return names


def _attrs(tree: ast.AST) -> set[str]:
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}


def _calls(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                out.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                out.add(node.func.attr)
    return out


def _page_consuming_functions(trees: dict[str, ast.Module]) -> set[str]:
    """Functions that use one of their own PARAMETERS as an image, **however
    indirectly** -- to a fixed point.

    Pass 1 of population B's derivation, and the reason the card's filter is
    the **hazard** rather than a direct attribute: a module that hands its
    page to one of these is exposed through it, and an attribute-only filter
    does not see that module at all.

    The closure is not an embellishment. Taken at depth 1 this walk does not
    recognise ``tests/helpers/page_ink.py``'s ``drawing_of`` -- the tree's
    central pixel oracle -- because it reads nothing off its own ``page``
    parameter and passes it to ``_dark``, one frame further in. CARD-329
    measured that: the depth-1 form left ``drawing_of`` out, so "however
    indirectly" was a word in a docstring and not a property of the walk. A
    fixed point is what makes the phrase true, and the cell
    ``test_the_files_this_card_does_not_own_are_excluded_by_name_not_missed``
    is what holds it.
    """
    consumers: set[str] = set()
    functions: list[tuple[str, set[str], ast.AST]] = []
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    (
                        node.name,
                        {
                            arg.arg
                            for arg in (
                                node.args.posonlyargs
                                + node.args.args
                                + node.args.kwonlyargs
                            )
                        },
                        node,
                    )
                )

    def reads_a_parameter(node: ast.AST, params: set[str]) -> bool:
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Attribute)
                and inner.attr in _PIL_IMAGE_SURFACE
                and isinstance(inner.value, ast.Name)
                and inner.value.id in params
            ):
                return True
        return False

    def hands_a_parameter_on(node: ast.AST, params: set[str]) -> bool:
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            called = (
                inner.func.id
                if isinstance(inner.func, ast.Name)
                else inner.func.attr
                if isinstance(inner.func, ast.Attribute)
                else None
            )
            if called not in consumers:
                continue
            handed = [argument for argument in inner.args] + [
                keyword.value for keyword in inner.keywords
            ]
            for argument in handed:
                if isinstance(argument, ast.Name) and argument.id in params:
                    return True
        return False

    for name, params, node in functions:
        if reads_a_parameter(node, params):
            consumers.add(name)
    # The closure. Bounded by the function count, and it terminates because
    # `consumers` only grows and is a subset of the names enumerated above.
    for _round in range(len(functions) + 1):
        grown = {
            name
            for name, params, node in functions
            if name not in consumers and hands_a_parameter_on(node, params)
        }
        if not grown:
            break
        consumers |= grown
    return consumers


class TestPdfPagesReader_BothReaderPopulationsAreDerived:
    """AC-3 — both populations derived by AST, with nothing unclassified.

    **The derivation is what is asserted, not the count.** Every cell below
    states a property of the filter or of each member; the two totals are
    reported in the card's notes, where a figure can carry its basis. One
    count IS asserted -- a floor, so the walk cannot silently stop finding
    modules -- and it is anchored to the enumerated set it came from rather
    than to a literal a fixture could then build (CARD-330's gating finding:
    a floor whose fixture built `range(THE_FLOOR)` enforced 3, not 24).

    ADR-0039/R2: a module the walk cannot classify is a FAILURE.
    """

    @staticmethod
    def _trees() -> dict[str, ast.Module]:
        return {
            _as_posix(path): ast.parse(path.read_text(), filename=str(path))
            for path in _test_tree_modules()
        }

    @classmethod
    def _populations(cls) -> tuple[dict[str, set[str]], dict[str, str], list[str]]:
        trees = cls._trees()
        consumers = _page_consuming_functions(trees)
        population_a = {
            name: _helper_imports(tree)
            for name, tree in trees.items()
            if _READER_NAME in _helper_imports(tree)
        }
        population_b: dict[str, str] = {}
        unclassified: list[str] = []
        for name, tree in trees.items():
            if name in population_a:
                continue
            if not (_PAGE_SOURCES & (_attrs(tree) | _calls(tree))):
                continue
            direct = _PIL_IMAGE_SURFACE & _attrs(tree)
            indirect = consumers & _calls(tree)
            if direct:
                population_b[name] = f"PIL surface {sorted(direct)[:3]}"
            elif indirect:
                population_b[name] = f"hands the page to {sorted(indirect)[:3]}"
            else:
                unclassified.append(name)
        return population_a, population_b, unclassified

    def test_nothing_the_walk_meets_is_left_unclassified(self) -> None:
        """ADR-0039/R2, stated first because it is the one that can fail
        silently: a module with a page source that the walk can neither place
        in B nor rule out is an unanalysable shape, and that is a FAILURE."""
        _a, _b, unclassified = self._populations()
        assert unclassified == [], unclassified

    def test_population_a_is_the_reader_and_not_a_mention(self) -> None:
        """A's filter: the reader, not the module. CARD-309's own correction.

        Every member imports `pdf_pages` by name, and every module that
        imports something else from the same helper and not the reader is
        OUTSIDE A -- which is the whole content of "a mention count is not a
        reader count", and the reason the orchestrator's independent 14 and
        this derivation's 12 are the same measurement at two filters.
        """
        trees = self._trees()
        population_a, _b, _u = self._populations()
        assert population_a, "population A came back empty"
        for name, names in population_a.items():
            assert _READER_NAME in names, (name, names)
        mentions = {
            name for name, tree in trees.items() if _helper_imports(tree)
        }
        outside = mentions - set(population_a)
        assert outside, (
            "no module imports from the helper WITHOUT importing the reader, "
            "so this cell is no longer measuring the difference between the "
            "two filters"
        )
        for name in outside:
            assert _READER_NAME not in _helper_imports(trees[name]), name

    def test_population_a_reproduces_a_second_independent_reading(self) -> None:
        """The same set, derived a second way: a text scan for the import
        statement rather than an AST walk.

        Two implementations rather than the same one twice (CLAUDE.md). They
        can disagree -- a commented-out import, an import inside a string --
        and the point of the cell is that here they do not.
        """
        population_a, _b, _u = self._populations()
        root = pathlib.Path(__file__).resolve().parents[1]
        # Both forms of the statement, because CARD-329's own round measured
        # the single-line form MISSING this very module: the import it added
        # here is parenthesised over five lines, and a scan that stopped at
        # the newline reported a disagreement the AST walk was right about.
        # That is the whole reason for having two implementations.
        pattern = re.compile(
            r"^\s*from\s+"
            + re.escape(_READER_MODULE)
            + r"\s+import\s+(?:\(([^)]*)\)|([^(\n]*))",
            re.M,
        )
        scanned = set()
        for path in _test_tree_modules():
            for parenthesised, plain in pattern.findall(path.read_text()):
                imported = parenthesised or plain
                if re.search(r"\b" + _READER_NAME + r"\b", imported):
                    scanned.add(_as_posix(path))
        assert scanned == set(population_a), (
            scanned ^ set(population_a),
            "the AST walk and the text scan disagree about population A",
        )
        del root

    def test_every_population_b_member_reaches_the_hazard(self) -> None:
        """B's filter: a page from `interior`/`interior_pages` is used as an
        image downstream, **however indirectly**.

        Each member is re-checked here against both halves of that filter, so
        a member admitted by neither would red. The indirect half is the one
        the orchestrator's attribute-only derivation did not have, and it is
        why B is derived by the hazard rather than by the attribute.
        """
        trees = self._trees()
        _a, population_b, _u = self._populations()
        assert population_b, "population B came back empty"
        consumers = _page_consuming_functions(trees)
        for name, why in population_b.items():
            tree = trees[name]
            assert _PAGE_SOURCES & (_attrs(tree) | _calls(tree)), name
            assert (_PIL_IMAGE_SURFACE & _attrs(tree)) or (
                consumers & _calls(tree)
            ), (name, why)

    def test_the_two_populations_are_disjoint(self) -> None:
        """B is defined as B \\ A -- a module that imports the reader is
        classified by that, not counted twice."""
        population_a, population_b, _u = self._populations()
        assert set(population_a).isdisjoint(population_b)

    def test_the_five_modules_this_card_repairs_are_all_in_population_b(
        self,
    ) -> None:
        """The link between the derivation and CARD-329's `Touches`: the card
        repairs population-B modules, so each of the five has to BE one. A
        module in `Touches` that the derivation does not place in B would mean
        the card is repairing something its own triage never found."""
        _a, population_b, _u = self._populations()
        assert _REPAIRED_BY_CARD_329 <= set(population_b), (
            _REPAIRED_BY_CARD_329 - set(population_b)
        )

    def test_the_files_this_card_does_not_own_are_excluded_by_name_not_missed(
        self,
    ) -> None:
        """G-2/G-3 are exclusions from `Touches`, not from the derivation.

        `tests/test_book_difficulty_dots.py` is a population-B module and
        CARD-331's; `tests/helpers/page_ink.py` and
        `tests/helpers/round_ink.py` are the pixel oracles, which never
        obtain a page themselves -- they are handed one, which is exactly why
        they are the `_page_consuming_functions` that put other modules in B.
        Either way none of the three is in this card's `Touches`.
        """
        _a, population_b, _u = self._populations()
        for name, owner in _NOT_THIS_CARDS.items():
            assert pathlib.Path(name).exists(), name
            assert name not in _REPAIRED_BY_CARD_329, (name, owner)
        assert "tests/test_book_difficulty_dots.py" in population_b, (
            "CARD-331's module is a population-B module; if the derivation no "
            "longer finds it, B's filter has narrowed"
        )
        consumers = _page_consuming_functions(self._trees())
        assert "drawing_of" in consumers, (
            "page_ink's oracle is no longer recognised as a page consumer, so "
            "B's indirect half has gone dead"
        )

    def test_the_walk_finds_at_least_as_many_modules_as_it_is_handed(
        self,
    ) -> None:
        """The floor, anchored to an enumerated authority.

        Not a literal: the floor is the number of modules this card and its
        two siblings NAME -- the five in `Touches` plus the three in
        `_NOT_THIS_CARDS` -- which is a set written down for other reasons and
        therefore cannot be quietly shrunk to match the walk. The walk has to
        account for every one of them, in A, in B, or as a page consumer.
        """
        population_a, population_b, _u = self._populations()
        named = _REPAIRED_BY_CARD_329 | set(_NOT_THIS_CARDS)
        consumers = _page_consuming_functions(self._trees())
        classified = set(population_a) | set(population_b)
        for name in named:
            if name in classified:
                continue
            tree = ast.parse(pathlib.Path(name).read_text(), filename=name)
            assert _page_consuming_functions({name: tree}) & consumers, (
                f"{name} is named by CARD-329 or a sibling and the walk "
                f"places it in neither population nor among the page "
                f"consumers"
            )
        assert len(classified) >= len(named), (len(classified), len(named))
