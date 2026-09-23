"""CARD-116: the book PDF's standing geometry, measured off the rendered pages.

    EC-019 (PDF half)  PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell
        -> test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages
    EC-022 (PDF half)  PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent
        -> test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages
    EC-032 (PDF half)  PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity
        -> test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages

``tests/property/test_book_layout.py`` holds CARD-114's layout halves of the
same three properties — the same statements about ``compute_layout``'s numbers.
These are the halves CARD-116 owes: the same statements about the **pages the
book's PDF actually contains**, so that a correct layout reached by a page the
generator numbered, specced or placed wrongly still fails.

How the expectations are independent
------------------------------------
Nothing here imports ``compute_layout``, ``PageSpec`` or ``book_page_spec``.
A case is a stored print specification (centimetre strings, as the ``books``
table holds them) and a real clue set; the expected cell, the expected drawing
width and the expected left edge are worked out below in millimetres, from
FR-030's own definition of page fit and FR-032's centring rule. What the page
*did* is read back from its ink by ``tests/helpers/page_ink.py``, which knows
nothing about either. The two are compared with a stated tolerance, because
one side rounds every edge to a device pixel and the other does not.

No ``hypothesis`` (CLAUDE.md): stdlib ``random.Random`` at fixed seeds, and
each test asserts its own minimum case count so the corpus cannot shrink
silently.
"""

from __future__ import annotations

import random

from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.clues import compute_clues
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of
from tests.helpers.two_up_ink import drawings_of

#: 300 DPI, the resolution every book page is drawn at.
PX_PER_MM = 300 / 25.4
HALF_PIXEL_MM = 0.5 / PX_PER_MM

#: CON-018's profile, in millimetres. Top and bottom have no stored column and
#: always come from it; the band is TERM-028's 12 mm and the cap NFR-008's
#: standard cell.
TOP_MM = BOTTOM_MM = 0.375 * 25.4
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
#: The cell-size floor COMP-007 keeps even when the sheet cannot hold it.
MIN_CELL_MM = 2.0

#: The stored forms that mean "the profile's own value" to the builder
#: (``book_page_spec``: ``"0.95"`` is 0.375 in, not 9.5 mm). A random case
#: never draws one, so a case's millimetres are exactly what its strings say.
_PROFILE_FORMS = {"21.59", "27.94", "1.27", "0.95"}


def _book(width_cm: str, height_cm: str, gutter_cm: str, outside_cm: str) -> Book:
    """A book carrying one stored print specification."""
    return Book(
        book_id="book-116",
        metadata=BookMetadata(
            title="Property Book",
            description="",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=width_cm,
        trim_height_cm=height_cm,
        gutter_margin_cm=gutter_cm,
        outside_margin_cm=outside_cm,
    )


class Sheet:
    """One case's stored print specification and its millimetres."""

    def __init__(self, width_cm, height_cm, gutter_cm, outside_cm):
        self.book = _book(width_cm, height_cm, gutter_cm, outside_cm)
        self.width_mm = float(width_cm) * 10
        self.height_mm = float(height_cm) * 10
        self.gutter_mm = float(gutter_cm) * 10
        self.outside_mm = float(outside_cm) * 10

    def __repr__(self):
        return (
            f"Sheet({self.width_mm}x{self.height_mm} mm, gutter {self.gutter_mm}, "
            f"outside {self.outside_mm})"
        )

    @property
    def usable_width_mm(self) -> float:
        return self.width_mm - self.gutter_mm - self.outside_mm

    @property
    def usable_height_mm(self) -> float:
        return self.height_mm - TOP_MM - BOTTOM_MM - BAND_MM

    def page_fit_mm(self, across: int, down: int) -> float:
        """FR-030's page fit: the largest cell the usable area holds the drawing at."""
        return min(self.usable_width_mm / across, self.usable_height_mm / down)

    def cell_mm(self, across: int, down: int) -> float:
        """``min(standard cell, page fit)``, never under the floor."""
        return max(MIN_CELL_MM, min(STANDARD_CELL_MM, self.page_fit_mm(across, down)))

    def left_margin_mm(self, page_number: int) -> float:
        """The margin on the page's left: the gutter on an odd (right-hand) page."""
        return self.gutter_mm if page_number % 2 else self.outside_mm

    def drawing_left_mm(self, page_number: int, across: int, down: int) -> float:
        """FR-032: the drawing centred across the usable width of *that* page."""
        spare = self.usable_width_mm - across * self.cell_mm(across, down)
        return self.left_margin_mm(page_number) + max(spare, 0.0) / 2


#: CON-018's Book 1 profile as a sheet, stated in its own stored form.
BOOK1 = Sheet("21.59", "27.94", "1.27", "0.95")


def _random_sheet(rng: random.Random) -> Sheet:
    """Any print specification a ``books`` row could hold: a portrait trim
    inside KDP's bounds and two side margins above the 0.25 in minimum."""
    while True:
        values = [
            f"{rng.uniform(10.0, 22.0):.2f}",
            f"{rng.uniform(14.0, 30.0):.2f}",
            f"{rng.uniform(0.70, 2.50):.2f}",
            f"{rng.uniform(0.70, 2.00):.2f}",
        ]
        if set(values) & _PROFILE_FORMS:
            continue  # the profile's own stored form means the profile's exact mm
        sheet = Sheet(*values)
        if (
            sheet.height_mm > sheet.width_mm  # a book is portrait
            and sheet.usable_width_mm > 0
            and sheet.usable_height_mm > 0
        ):
            return sheet


def _alternating(columns: int, rows: int) -> list[list[bool]]:
    """Every other cell filled: the deepest gutters an extent can have."""
    return [[(row + column) % 2 == 0 for column in range(columns)] for row in range(rows)]


def _clue_depths(rows, columns) -> tuple[int, int]:
    return max(len(c) for c in rows), max(len(c) for c in columns)


def _puzzle(rng: random.Random, columns: int | None = None, rows: int | None = None) -> dict:
    """A real puzzle of a random extent in CON-011's range and clue depth."""
    columns = rng.randint(MIN_SIZE, MAX_SIZE) if columns is None else columns
    rows = rng.randint(MIN_SIZE, MAX_SIZE) if rows is None else rows
    if rng.random() < 0.3:
        grid = _alternating(columns, rows)
    else:
        density = rng.uniform(0.2, 0.8)
        grid = [[rng.random() < density for _ in range(columns)] for _ in range(rows)]
    found = compute_clues(grid)
    return {
        "id": f"p{columns}x{rows}",
        "grid": grid,
        "clues_rows": [list(c) for c in found.rows],
        "clues_cols": [list(c) for c in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": "P",
        "difficulty_tier": "easy",
        "_rows": found.rows,
        "_columns": found.columns,
    }


def _extent(puzzle: dict) -> tuple[int, int, int, int]:
    """``(columns, rows, drawing columns, drawing rows)`` — the drawing's own extent."""
    row_depth, column_depth = _clue_depths(puzzle["_rows"], puzzle["_columns"])
    columns, rows = puzzle["width"], puzzle["height"]
    return columns, rows, row_depth + columns, column_depth + rows


def _trim_px(sheet: Sheet) -> tuple[float, float]:
    return sheet.width_mm * PX_PER_MM, sheet.height_mm * PX_PER_MM


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages() -> None:
    """EC-019 (PDF half): for any extent, clue depth and stored trim/margins, every
    page of the book's PDF is the trim, and the drawn puzzle fits inside the usable
    area below the band at a cell that never exceeds the 7.5 mm standard cell."""
    rng = random.Random(1160019)
    checked = at_cap = below_book_floor = 0
    for case in range(220):
        sheet = BOOK1 if case % 10 == 0 else _random_sheet(rng)
        puzzle = _puzzle(rng)
        columns, rows, across, down = _extent(puzzle)
        if sheet.page_fit_mm(across, down) < MIN_CELL_MM:
            continue  # the floor wins and the drawing is allowed to overflow
        expected_cell = sheet.cell_mm(across, down)

        pages = BookPDFGenerator(sheet.book).interior_pages([puzzle])
        assert len(pages) == 4, "guide, puzzle, divider, answer"

        # Every page of the book is the trim, at 300 DPI — not only the puzzle's.
        trim_width_px, trim_height_px = _trim_px(sheet)
        for number, page in enumerate(pages, start=1):
            assert abs(page.size[0] - trim_width_px) <= 0.5, (sheet, number, page.size)
            assert abs(page.size[1] - trim_height_px) <= 0.5, (sheet, number, page.size)

        drawing = drawing_of(pages[1])  # interior page 2, the puzzle
        assert (drawing.columns, drawing.rows) == (columns, rows)

        # The cell is FR-030's, never above the standard cell.
        drawn_cell_mm = _mm(drawing.cell)
        assert drawn_cell_mm <= STANDARD_CELL_MM + 2 * HALF_PIXEL_MM, (sheet, drawn_cell_mm)
        assert abs(drawn_cell_mm - expected_cell) < 0.05, (sheet, drawn_cell_mm, expected_cell)

        # The whole drawing lies inside the usable area, below the band.
        page_number = 2
        usable_left = sheet.left_margin_mm(page_number) * PX_PER_MM
        usable_right = (sheet.left_margin_mm(page_number) + sheet.usable_width_mm) * PX_PER_MM
        usable_bottom = (sheet.height_mm - BOTTOM_MM) * PX_PER_MM
        assert drawing.left >= usable_left - 1, (sheet, drawing.left, usable_left)
        assert drawing.grid_right <= usable_right + 1, (sheet, drawing.grid_right)
        assert drawing.grid_bottom <= usable_bottom + 1, (sheet, drawing.grid_bottom)
        assert abs(_mm(drawing.top) - (TOP_MM + BAND_MM)) <= HALF_PIXEL_MM + 1e-9

        # The grid is exactly as wide and as tall as its cells say it is.
        assert abs(_mm(drawing.grid_right - drawing.grid_left) - columns * expected_cell) < 0.2
        assert abs(_mm(drawing.grid_bottom - drawing.grid_top) - rows * expected_cell) < 0.2

        checked += 1
        at_cap += abs(expected_cell - STANDARD_CELL_MM) < 1e-9
        below_book_floor += expected_cell < 4.8
    assert checked >= 200, checked
    # Both regimes are exercised: held at the cap, and fitted below NFR-008's floor.
    assert at_cap >= 20, at_cap
    assert below_book_floor >= 20, below_book_floor


def test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages() -> None:
    """EC-022 (PDF half): every puzzle page of a book is portrait, its grid is drawn
    unrotated, and its top edge lies at the one fixed offset — top margin plus band —
    whatever the extent and wherever the page falls in the interior."""
    rng = random.Random(1160022)
    extents = [
        (columns, rows)
        for columns in range(MIN_SIZE, MAX_SIZE + 1, 2)
        for rows in range(MIN_SIZE, MAX_SIZE + 1, 2)
    ]
    # The wide grids NFR-006 would turn on A4 are the case this property is
    # really about, so they are in the corpus by name rather than by luck.
    extents += [(30, 10), (30, 12), (29, 11), (28, 10), (30, 15)]
    assert len(extents) >= 120, len(extents)

    counted = overflowed = 0
    for sheet in (BOOK1, _random_sheet(rng)):
        puzzles = [_puzzle(rng, columns, rows) for columns, rows in extents]
        # One puzzle to a page: neighbours are given different tiers, which is
        # the rule that stops two-up pairing (FR-040, INV-010, CARD-127)
        # without touching the extents this property is stated over. A book's
        # two-up pages are the sibling below.
        for index, puzzle in enumerate(puzzles):
            puzzle["difficulty_tier"] = "easy" if index % 2 else "medium"
        pages = BookPDFGenerator(sheet.book).interior_pages(puzzles)
        trim_width_px, trim_height_px = _trim_px(sheet)
        expected_top_mm = TOP_MM + BAND_MM
        tops: set[int] = set()

        for index, puzzle in enumerate(puzzles):
            page = pages[1 + index]  # interior page 2 + index
            columns, rows, across, down = _extent(puzzle)

            assert page.size[0] < page.size[1], (sheet, "portrait")
            assert abs(page.size[0] - trim_width_px) <= 0.5
            assert abs(page.size[1] - trim_height_px) <= 0.5

            drawing = drawing_of(page)
            # The top edge is the property's subject, and it is measurable on
            # every page: the grid's left border starts there whether or not
            # the drawing fits (a trim too small for it anchors at the usable
            # area's left edge and overflows to the right, keeping this edge).
            assert abs(_mm(drawing.top) - expected_top_mm) <= HALF_PIXEL_MM + 1e-9
            tops.add(drawing.top)

            if sheet.page_fit_mm(across, down) < MIN_CELL_MM:
                # The MIN_CELL_MM floor won and the drawing runs off the trim,
                # so its far rules are not on the page to be counted. CARD-114's
                # layout half owns that case; what it does not stop being is
                # portrait with this top edge, which is asserted above.
                overflowed += 1
                continue
            # Unrotated: the grid's width runs across the page, its height down.
            assert (drawing.columns, drawing.rows) == (columns, rows), (sheet, columns, rows)
            counted += 1

        assert len(tops) == 1, (sheet, "the top edge never varies between puzzle pages")

    assert counted >= 150, counted
    # The overflowing sheet is a declared case, not a silent gap in the corpus.
    assert overflowed >= 1, overflowed


def test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages() -> None:
    """EC-032 (PDF half): on every page of the book's PDF the gutter margin is on the
    binding side, the drawing is centred across that page's usable width, the odd
    page's left edge minus the even page's is gutter - outside, and the top edge is
    the same on both.

    One book of the same puzzle twice puts it on interior page 2 (left-hand) and
    page 3 (right-hand), and its two answer pages on 5 (right-hand) and 6
    (left-hand) — so both parities are measured on both page kinds, with the
    drawing held constant.
    """
    rng = random.Random(1160032)
    checked = 0
    for case in range(110):
        sheet = BOOK1 if case % 10 == 0 else _random_sheet(rng)
        puzzle = _puzzle(rng)
        columns, rows, across, down = _extent(puzzle)
        if sheet.page_fit_mm(across, down) < MIN_CELL_MM:
            continue

        # The same drawing twice, on two tiers, so the two copies never share a
        # page (FR-040, CARD-127): this property's subject is parity, and it
        # needs the *same* drawing on two pages of opposite parity.
        pages = BookPDFGenerator(sheet.book).interior_pages(
            [puzzle, dict(puzzle, difficulty_tier="medium")]
        )
        assert len(pages) == 6, "guide, two puzzles, divider, two answers"

        # (interior page number, the page) for every page carrying the drawing.
        # The two blank puzzle pages are also measured for width and cell; an
        # answer page's revealed cells are long runs of ink themselves, so its
        # rules cannot be counted (see ``tests/helpers/page_ink.py``) and only
        # its two placed edges are read.
        placed = [(2, pages[1]), (3, pages[2]), (5, pages[4]), (6, pages[5])]
        by_number = {}
        for number, page in placed:
            drawing = drawing_of(page)
            by_number[number] = drawing
            expected_left = sheet.drawing_left_mm(number, across, down)
            assert abs(_mm(drawing.left) - expected_left) <= 2 * HALF_PIXEL_MM + 1e-9, (
                sheet, number, _mm(drawing.left), expected_left
            )
            # The top edge is the same fixed offset on every one of them.
            assert abs(_mm(drawing.top) - (TOP_MM + BAND_MM)) <= HALF_PIXEL_MM + 1e-9

        for number in (2, 3):
            drawing = by_number[number]
            assert (drawing.columns, drawing.rows) == (columns, rows)
            # Centred across this page's usable width: the white left of the
            # drawing equals the white right of it, both measured off the page.
            # (The drawing runs ``across`` cells from its left edge — a cell
            # being the rule-to-rule pitch the grid itself shows.)
            if sheet.usable_width_mm - across * sheet.cell_mm(across, down) >= 0:
                left_spare = _mm(drawing.left) - sheet.left_margin_mm(number)
                right_spare = sheet.usable_width_mm - left_spare - across * _mm(drawing.cell)
                assert abs(left_spare - right_spare) <= 4 * HALF_PIXEL_MM + 1e-9, (
                    sheet, number, left_spare, right_spare
                )

        odd_pages = (by_number[3], by_number[5])
        even_pages = (by_number[2], by_number[6])
        for odd in odd_pages:
            for even in even_pages:
                shift_mm = _mm(odd.left - even.left)
                assert abs(shift_mm - (sheet.gutter_mm - sheet.outside_mm)) < 2 * HALF_PIXEL_MM, (
                    sheet, shift_mm
                )
                # Parity moves the drawing sideways only.
                assert odd.top == even.top, (sheet, odd.top, even.top)
        assert by_number[2].grid_bottom == by_number[3].grid_bottom
        assert abs(by_number[2].cell - by_number[3].cell) <= 1

        # Every one of those pages is the same trim.
        assert len({page.size for page in pages}) == 1
        checked += 1
    assert checked >= 100, checked


def test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_two_up_pages() -> None:
    """EC-022 (PDF half), two-up pages — CARD-127 adds them to this corpus.

    FR-040 lets two puzzles of one tier share a page. The clause this property
    states about such a page is that **the upper puzzle's** drawing top edge is
    the same fixed offset — top margin plus band — that every single puzzle
    page uses, so a reader leafing through the book sees one top edge whatever
    a page holds. Both drawings are still portrait and unrotated.

    The corpus is one book of small same-tier neighbours, so the walk pairs
    many of them; which pages it paired is read back off the ink rather than
    predicted here (that walk is EC-027's own property,
    ``tests/property/test_book_pairing.py``), and this test only requires that
    two-up pages really did occur.
    """
    rng = random.Random(1270022)
    extents = [
        (columns, rows)
        for columns in range(MIN_SIZE, 23, 2)
        for rows in range(MIN_SIZE, 17, 2)
    ]
    assert len(extents) >= 24, len(extents)

    sheet = BOOK1
    puzzles = [_puzzle(rng, columns, rows) for columns, rows in extents]
    pages = BookPDFGenerator(sheet.book).interior_pages(puzzles)
    trim_width_px, trim_height_px = _trim_px(sheet)
    expected_top_mm = TOP_MM + BAND_MM

    counted = two_up = single = 0
    tops: set[int] = set()
    index = 0
    page_number = 2
    while index < len(puzzles):
        page = pages[page_number - 1]
        assert page.size[0] < page.size[1], (page_number, "portrait")
        assert abs(page.size[0] - trim_width_px) <= 0.5
        assert abs(page.size[1] - trim_height_px) <= 0.5

        drawings = drawings_of(page)
        assert 1 <= len(drawings) <= 2, (page_number, len(drawings))
        for offset, drawing in enumerate(drawings):
            columns, rows, _, _ = _extent(puzzles[index + offset])
            # Unrotated: the grid's width runs across the page, its height down.
            assert (drawing.columns, drawing.rows) == (columns, rows), (page_number, offset)
            counted += 1
        # The page's *upper* drawing carries the fixed top edge, on a page
        # holding one puzzle and on a page holding two alike.
        assert abs(_mm(drawings[0].top) - expected_top_mm) <= HALF_PIXEL_MM + 1e-9
        tops.add(drawings[0].top)
        if len(drawings) == 2:
            two_up += 1
            assert drawings[1].top > drawings[0].top, "the lower slot is below it"
        else:
            single += 1
        index += len(drawings)
        page_number += 1

    assert len(tops) == 1, "the top edge never varies between puzzle pages"
    assert counted == len(puzzles), counted
    # Both page make-ups are really in the corpus.
    assert two_up >= 5, two_up
    assert single >= 5, single
