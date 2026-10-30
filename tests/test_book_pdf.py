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
import re
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
from tests.helpers.pdf_pages import pdf_pages

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
    declared raster at this commit — see :data:`_RASTER_DECLARATIONS`, whose
    five temporary entries name their blockers — so the *vector* arm of the
    equivalence is not exercised by production's own default. It is exercised,
    through production's own writer, by
    :func:`test_no_interior_page_carries_an_image_xobject_in_a_mixed_file`
    below, which lifts one declaration and watches a real mixed-media interior
    come out. Without that companion this test would be a true sentence about
    a file with no vector page in it.
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
    **no** XObject, and every page after it still carries an XObject. A mixed
    file is the point — ADR-0042/R2's "per-page mixing is a sanctioned end
    state" — so a writer that silently converted the whole file, or none of
    it, reds here.
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
    assert set(media[1:]) == {_RASTER}, media
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


#: The board's whole status vocabulary, derived 2026-10-29 by reading every
#: ``meta/kanban/cards/CARD-*.md`` in the main working tree. Only ``done`` is
#: terminal. **No per-status counts are written here, and that is deliberate:**
#: the ones this comment first carried were already two cells out within the
#: day (``done`` and ``ready`` both moved when CARD-291 merged and CARD-308
#: started), which is the drift :mod:`tests/test_cli.py`'s component map and
#: CARD-261 were built to stop — and which the comment a hundred lines below
#: refuses for the same reason. The **set** is the load-bearing claim and it is
#: mechanically pinned by
#: :func:`test_no_declaration_outlives_the_cards_that_remove_it`, which
#: requires every card on the board to have a readable status, so a sixth
#: spelling reds rather than drifting. A **sixth** spelling is an unanalysable shape, which
#: ADR-0039/R2 makes a failure here rather than a card quietly read as
#: not-done — the direction that cannot ship a false green.
_BOARD_STATUSES = frozenset(
    {"done", "ready", "in progress", "blocked", "parked", "skipped"}
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
    #. its status word is outside :data:`_BOARD_STATUSES` — a sixth spelling
       on the board reds here instead of being read as "not done", because
       "not done" is the answer that ships a stale declaration.

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
    status_card("CARD-90003", "in progress")
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
    for still_open in ("CARD-90002", "CARD-90003"):
        assert _landing_findings(declared(still_open), tmp_path) == [], still_open

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
    assert _card_status("CARD-90003", tmp_path) == "in progress"


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
        assert callers == {"_write_pdf": 1, "produce": 1}, callers

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
