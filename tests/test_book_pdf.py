"""CARD-116 — the book PDF on its own trim (FR-030, FR-032, FR-043, ADR-0036).

    AC-175  TestBookPdf_CellSizedForBookTrimNotA4
    AC-176  TestBookPdf_CellFollowsStoredTrim
    AC-177  TestBookPdf_PageSizeEqualsStoredTrim
    AC-178  TestBookPdf_EmptyMarginsFallBackToBook1Profile
    AC-189  TestBookPdf_WideGridPrintsOnPortraitPage
    AC-190  TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage
    AC-240  TestBookPdf_WideGridPrintsUprightNeverRotated
    AC-274  TestBookPdf_DrawingCentredOnRightHandPage
    AC-275  TestBookPdf_DrawingCentredOnLeftHandPage
    AC-276  TestBookPdf_ParityNeverMovesTopEdge

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

import pytest

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator, page_frame
from nonogram.export.layout import DEFAULT_PAGE_SPEC
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of, pdf_page_boxes
from tests.helpers.pdf_pages import pdf_pages

#: CON-018's Book 1 profile, in millimetres, written out here rather than
#: imported: 8.5 x 11 in, 0.5 in gutter, 0.375 in outside/top/bottom, the
#: 12 mm title band (TERM-028) and NFR-008's 7.5 mm standard cell.
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4
TOP_MM = BOTTOM_MM = 0.375 * 25.4
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5

#: 6 x 9 in, the other trim the ACs measure.
SIX_BY_NINE_MM = (6 * 25.4, 9 * 25.4)

#: Device pixels per millimetre at the 300 DPI every page is drawn at.
PX_PER_MM = 300 / 25.4

#: Tolerances the ACs state: the cell to 0.05 mm, a placed edge to 0.1 mm.
CELL_TOLERANCE_MM = 0.05
EDGE_TOLERANCE_MM = 0.1


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
    """FR-032: the drawing centred across the usable width, the gutter margin on
    the binding side — left on a right-hand (odd) page, right on a left-hand one."""
    usable_width = width_mm - gutter_mm - outside_mm
    spare = usable_width - (depth + columns) * cell_mm
    return (gutter_mm if right_hand else outside_mm) + spare / 2


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _interior(book: Book, puzzles: list[dict]) -> list:
    """The book's interior pages in print order; ``pages[n - 1]`` is page ``n``."""
    return BookPDFGenerator(book).interior_pages(puzzles)


# --------------------------------------------------------------------------
# The cell the book's own trim gives a puzzle
# --------------------------------------------------------------------------


class TestBookPdf_CellSizedForBookTrimNotA4:
    """AC-175 — a 30x30 with 9-deep gutters draws a 4.97 mm cell on Book 1."""

    PUZZLE = (30, 30, 9)

    def test_the_page_draws_the_cell_the_book_trim_allows(self):
        book = _book()
        page = _interior(book, [_puzzle(*self.PUZZLE)])[1]  # interior page 2

        drawn_mm = _mm(drawing_of(page).cell)

        assert abs(drawn_mm - 4.9660) < CELL_TOLERANCE_MM, drawn_mm
        expected = _expected_cell_mm(*self.PUZZLE)
        assert abs(drawn_mm - expected) < CELL_TOLERANCE_MM, (drawn_mm, expected)

    def test_it_is_not_the_cell_the_a4_layout_used_to_give_it(self):
        """The defect this AC pins: 193.675 mm over 39 cells, not A4's 186 mm."""
        book = _book()
        page = _interior(book, [_puzzle(*self.PUZZLE)])[1]

        a4_cell_mm = (210.0 - 2 * 12.0) / 39
        assert abs(a4_cell_mm - 4.7692) < 1e-3  # what the A4 sheet gave it
        assert _mm(drawing_of(page).cell) - a4_cell_mm > 0.15


class TestBookPdf_CellFollowsStoredTrim:
    """AC-176 — the same 15x15 draws 5.92 mm on a 6 x 9 in book, 7.5 mm on 8.5 x 11.

    Both books are set up through Print setup (CARD-136), so the criterion is
    about the trim the owner chose and the product stored.
    """

    PUZZLE = (15, 15, 7)

    def test_a_six_by_nine_book_draws_the_smaller_cell(self, print_setup):
        width_mm, height_mm = SIX_BY_NINE_MM
        book = print_setup(width_mm, height_mm)
        page = _interior(book, [_puzzle(*self.PUZZLE)])[1]

        drawn_mm = _mm(drawing_of(page).cell)

        assert abs(drawn_mm - 5.9170) < CELL_TOLERANCE_MM, drawn_mm
        expected = _expected_cell_mm(
            *self.PUZZLE, width_mm=width_mm, height_mm=height_mm
        )
        assert abs(drawn_mm - expected) < CELL_TOLERANCE_MM, (drawn_mm, expected)

    def test_the_same_puzzle_on_the_book_one_trim_is_held_at_the_standard_cell(
        self, print_setup
    ):
        book = print_setup(BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM)
        page = _interior(book, [_puzzle(*self.PUZZLE)])[1]

        drawn_mm = _mm(drawing_of(page).cell)

        assert abs(drawn_mm - STANDARD_CELL_MM) < CELL_TOLERANCE_MM, drawn_mm

    def test_changing_the_trim_is_what_changes_the_cell(self, print_setup):
        """The two halves side by side: one puzzle, two chosen trims."""
        puzzle = _puzzle(*self.PUZZLE)
        six_by_nine = _mm(drawing_of(_interior(print_setup(*SIX_BY_NINE_MM), [puzzle])[1]).cell)
        book_one = _mm(
            drawing_of(_interior(print_setup(BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM), [puzzle])[1]).cell
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

    #: This fixture's interior: the guide page, three puzzle pages (none of
    #: these three pairs) and the SOLUTIONS divider, then the **one** answer
    #: page FR-042's packed key takes — the three answers are one level, and
    #: the 30x30 among them makes the page four-up, which holds all three
    #: (CARD-134).
    PAGES = 1 + 3 + 1 + 1

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
        page = _interior(book, [_puzzle(*self.PUZZLE)])[1]

        drawn_mm = _mm(drawing_of(page).cell)

        assert abs(drawn_mm - 4.9660) < CELL_TOLERANCE_MM, drawn_mm
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
        assert pdf_page_boxes(export.interior.getvalue()) == [letter_pt] * 4
        assert pdf_page_boxes(export.cover.getvalue()) == [letter_pt]


# --------------------------------------------------------------------------
# Portrait, upright, and a top edge that never moves (FR-032)
# --------------------------------------------------------------------------


class TestBookPdf_WideGridPrintsOnPortraitPage:
    """AC-189 — a 30-wide x 15-tall puzzle prints on a 2550 x 3300 px page."""

    def test_the_page_is_portrait_at_the_book_trim(self):
        pages = _interior(_book(), [_puzzle(30, 15, 5)])

        page = pages[1]
        assert page.size == (2550, 3300)
        assert page.size[0] < page.size[1], "portrait"

    def test_every_page_of_that_book_is_portrait(self):
        pages = _interior(_book(), [_puzzle(30, 15, 5)])

        assert {page.size for page in pages} == {(2550, 3300)}


class TestBookPdf_WideGridPrintsUprightNeverRotated:
    """AC-240 — 30 columns across the page and 15 rows down it."""

    def test_the_grid_is_drawn_unrotated(self):
        page = _interior(_book(), [_puzzle(30, 15, 5)])[1]

        drawing = drawing_of(page)

        assert (drawing.columns, drawing.rows) == (30, 15)

    def test_the_measurement_would_have_seen_a_rotation(self):
        """The negative has teeth: a 15-wide x 30-tall puzzle reads the other way."""
        page = _interior(_book(), [_puzzle(15, 30, 5)])[1]

        drawing = drawing_of(page)

        assert (drawing.columns, drawing.rows) == (15, 30)


class TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage:
    """AC-190 — a 15x15 and a 30x30 start on the same pixel row."""

    def test_both_puzzle_pages_start_at_the_same_top_edge(self):
        pages = _interior(_book(), [_puzzle(15, 15, 7), _puzzle(30, 30, 9)])

        small, large = drawing_of(pages[1]), drawing_of(pages[2])

        assert small.top == large.top
        assert small.cell != large.cell, "the two do print different cells"

    def test_that_edge_is_the_top_margin_plus_the_band(self):
        pages = _interior(_book(), [_puzzle(15, 15, 7), _puzzle(30, 30, 9)])

        for page in pages[1:3]:
            assert abs(_mm(drawing_of(page).top) - (TOP_MM + BAND_MM)) <= _mm(0.5) + 1e-9


# --------------------------------------------------------------------------
# Mirrored margins (FR-032 amended 2026-09-22 (c), FR-043)
# --------------------------------------------------------------------------

#: AC-274/AC-275's book: three 15x15 puzzles with 7-deep clue gutters, so the
#: puzzle pages are interior pages 2, 3 and 4 (page 1 is the guide page).
_MIRRORED_PUZZLE = (15, 15, 7)


def _mirrored_pages():
    return _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE, name=f"P{n}") for n in range(3)])


class TestBookPdf_DrawingCentredOnRightHandPage:
    """AC-274 — on interior page 3 the drawing's left edge is 27.05 mm in."""

    def test_the_drawing_sits_27_05_mm_from_the_left_trim_edge(self):
        page = _mirrored_pages()[2]  # interior page 3, right-hand

        left_mm = _mm(drawing_of(page).left)

        assert abs(left_mm - 27.05) < EDGE_TOLERANCE_MM, left_mm

    def test_that_is_the_usable_width_centred_with_the_gutter_on_the_left(self):
        page = _mirrored_pages()[2]

        left_mm = _mm(drawing_of(page).left)
        expected = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=True)

        assert abs(left_mm - expected) < EDGE_TOLERANCE_MM, (left_mm, expected)
        assert abs((left_mm - GUTTER_MM) - 14.35) < EDGE_TOLERANCE_MM  # 14.35 mm inside


class TestBookPdf_DrawingCentredOnLeftHandPage:
    """AC-275 — on interior page 4 the same drawing's left edge is 23.875 mm in."""

    def test_the_drawing_sits_23_875_mm_from_the_left_trim_edge(self):
        page = _mirrored_pages()[3]  # interior page 4, left-hand

        left_mm = _mm(drawing_of(page).left)

        assert abs(left_mm - 23.875) < EDGE_TOLERANCE_MM, left_mm

    def test_that_is_the_usable_width_centred_with_the_gutter_on_the_right(self):
        page = _mirrored_pages()[3]

        left_mm = _mm(drawing_of(page).left)
        expected = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=False)

        assert abs(left_mm - expected) < EDGE_TOLERANCE_MM, (left_mm, expected)
        assert abs((left_mm - OUTSIDE_MM) - 14.35) < EDGE_TOLERANCE_MM

    def test_the_two_pages_differ_by_the_gutter_less_the_outside_margin(self):
        pages = _mirrored_pages()

        right_hand = drawing_of(pages[2]).left
        left_hand = drawing_of(pages[3]).left

        assert abs(_mm(right_hand - left_hand) - (GUTTER_MM - OUTSIDE_MM)) < EDGE_TOLERANCE_MM


class TestBookPdf_ParityNeverMovesTopEdge:
    """AC-276 — parity moves the drawing sideways only."""

    def test_the_two_drawings_share_a_top_pixel_row(self):
        pages = _mirrored_pages()

        right_hand = drawing_of(pages[2])
        left_hand = drawing_of(pages[3])

        assert right_hand.top == left_hand.top
        assert right_hand.left != left_hand.left, "they do sit on different parities"

    def test_they_are_the_same_drawing_at_the_same_cell(self):
        pages = _mirrored_pages()

        right_hand = drawing_of(pages[2])
        left_hand = drawing_of(pages[3])

        assert (right_hand.columns, right_hand.rows) == (left_hand.columns, left_hand.rows)
        assert abs(right_hand.cell - left_hand.cell) <= 1


class TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1:
    """INV-013's parity half — the first puzzle page is interior page 2, left-hand.

    Page 1 is the guide page and the cover is a separate file that is never
    numbered (FR-043), so the first puzzle directly follows the guide page and
    lands on a **left-hand** page. Until level dividers exist (CARD-128) that
    is the whole of it, and it is the reading that distinguishes counting from
    interior page 1 from the two ways of getting it wrong: counting from the
    cover, or treating the first puzzle page as page 1.
    """

    def test_the_first_puzzle_page_is_left_hand(self):
        pages = _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])

        left_mm = _mm(drawing_of(pages[1]).left)
        expected = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=False)

        assert abs(left_mm - expected) < EDGE_TOLERANCE_MM, (left_mm, expected)

    def test_it_is_not_the_right_hand_page_a_miscount_would_give_it(self):
        pages = _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])

        left_mm = _mm(drawing_of(pages[1]).left)
        right_hand = _expected_left_mm(15, 7, STANDARD_CELL_MM, right_hand=True)

        assert abs(left_mm - right_hand) > EDGE_TOLERANCE_MM
        assert abs(right_hand - left_mm - (GUTTER_MM - OUTSIDE_MM)) < EDGE_TOLERANCE_MM

    def test_the_parities_alternate_from_there(self):
        """Pages 2, 3, 4 are left, right, left — each page's own position."""
        pages = _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE, name=f"P{n}") for n in range(3)])

        lefts = [_mm(drawing_of(page).left) for page in pages[1:4]]

        assert abs(lefts[0] - lefts[2]) < EDGE_TOLERANCE_MM
        assert abs(lefts[1] - lefts[0] - (GUTTER_MM - OUTSIDE_MM)) < EDGE_TOLERANCE_MM


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

        # Guide 1, the two survivors 2 and 3, divider 4, and the packed key's
        # one page 5 — both answers are one level and fit a six-up page
        # (FR-042, CARD-134).
        assert len(pages) == 5
        first_mm = _mm(drawing_of(pages[1]).left)
        second_mm = _mm(drawing_of(pages[2]).left)

        # Interior page 2 is left-hand, page 3 right-hand.
        assert abs(first_mm - _expected_left_mm(
            15, 7, STANDARD_CELL_MM, right_hand=False
        )) < EDGE_TOLERANCE_MM, first_mm
        assert abs(second_mm - _expected_left_mm(
            15, 7, STANDARD_CELL_MM, right_hand=True
        )) < EDGE_TOLERANCE_MM, second_mm

    def test_the_second_survivor_did_not_inherit_the_dropped_page_parity(self):
        """The failure this pins: the survivor left on page 4's margins.

        Had the drop happened after page 3 was handed to the broken puzzle,
        the second survivor would be interior page 4 — left-hand, the same
        left edge as the first survivor — instead of page 3.
        """
        pages = _interior(
            _book(),
            [
                _puzzle(*_MIRRORED_PUZZLE, name="First"),
                _unbuildable_puzzle(),
                _puzzle(*_MIRRORED_PUZZLE, name="Second"),
            ],
        )

        first_mm = _mm(drawing_of(pages[1]).left)
        second_mm = _mm(drawing_of(pages[2]).left)

        assert abs(second_mm - first_mm) > EDGE_TOLERANCE_MM
        assert abs(second_mm - first_mm - (GUTTER_MM - OUTSIDE_MM)) < EDGE_TOLERANCE_MM

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
            # the second. Both are passed straight through, so what this
            # monkeypatch changes is the total and nothing else.
            lambda count, puzzle_pages=None, answer_pages=None: planned(
                count, puzzle_pages, answer_pages
            )
            + 1,
        )

        with pytest.raises(RuntimeError) as raised:
            _interior(_book(), [_puzzle(*_MIRRORED_PUZZLE)])

        assert "interior has 4 pages, its page plan says 5" in str(raised.value)

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
