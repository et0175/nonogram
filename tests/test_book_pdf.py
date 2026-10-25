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

from importlib import resources

import numpy as np
import pytest

from nonogram import clues
from nonogram.admin import book_vector
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    page_frame,
    puzzle_page_plan,
)
from nonogram.export import pdf as export_pdf
from nonogram.export.layout import DEFAULT_PAGE_SPEC
from nonogram.limits import MAX_SIZE, MIN_SIZE
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
            # length. All three are passed straight through, so what this
            # monkeypatch changes is the total and nothing else.
            lambda count, puzzle_pages=None, answer_pages=None, level_dividers=0, toc_pages=None: (
                planned(count, puzzle_pages, answer_pages, level_dividers, toc_pages=toc_pages) + 1
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
