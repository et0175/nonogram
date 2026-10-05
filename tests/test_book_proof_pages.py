"""CARD-118 — ADR-0037's proof pages, on the book's own sheet.

    CK-1  TestBookProof_TwoTrimSizedPagesAtExpectedCells
    CK-2  TestBookProof_FollowsStoredTrim
    CK-3  TestBookProof_StrokesMeetBookMinimum
    EC    test_PropertyTest_BookProof_EveryStoredPrintSpecPrintsItsOwnSheet

CARD-172 — square and landscape trims carry the note in a clear spot:

    AC-1  TestBookProof_SquareTrimsCarryTheNote
    AC-2  TestBookProof_LandscapeTrimsCarryTheNote
    AC-3  TestBookProof_FallbackNoteHoldsTheTenPointFloor
    AC-4  test_PropertyTest_BookProof_EveryStoredPrintSpecPrintsItsOwnSheet (extended)
    AC-5  test_a_trim_with_no_room_for_the_note_is_refused_and_says_so,
          test_a_trim_with_no_room_for_the_note_is_reported_not_served
    AC-6  TestBookProof_PortraitProofsAreByteIdentical

CARD-179 — the wrapped fallback note keeps each number with its unit:

    AC-1  TestBookProof_WrappedNoteKeepsUnitsWithNumbers
    AC-2  TestBookProof_WrappedNoteKeepsUnitsWithNumbers
    AC-3  test_PropertyTest_ProofNoteWrap_NeverSplitsAUnitOrStartsWithTimes
    AC-4  TestBookProof_SquareTrimsCarryTheNote (unchanged),
          TestBookProof_FallbackLeadingTightensOnlyWhenNeeded

ADR-0037 makes the band's wording and the book's stroke minimum final only
once the owner has measured them on printed paper. These tests cover the
automatable half of that: that the paper the panel produces *is* the book's
own sheet, at the cells the checkpoint names, with rules at the weights the
ADR fixes.

What is measured, and where it is measured
------------------------------------------
Everything is read back off the **rendered output**, never off the arguments
that produced it:

* page count, pixel size and the printed **MediaBox** come from the PDF bytes
  (``tests/helpers/pdf_pages.py`` and ``page_ink.pdf_page_boxes``). The box is
  the other half of "2550 x 3300 px at 300 DPI" — a file whose DPI was dropped
  would keep every pixel assertion green while printing at the wrong size;
* the grid's extent, its printed cell and the drawing's position come from
  ``page_ink.drawing_of``, which finds the grid by its own ink and imports
  nothing from ``nonogram.export.layout``;
* rule thicknesses and their colour are counted along a scanline taken between
  two rules of the other axis, the technique CARD-117's
  ``tests/test_book_pdf_band.py`` established. They are measured on the page
  **as drawn** rather than on the PDF's page, because the file's DCT round
  trip greys the edges of a 3-pixel rule and "pure black" is exactly what is
  being asserted.

Millimetres are converted here with :data:`PX_PER_MM`, worked out from the
300 DPI the book is printed at — not read off a :class:`Layout`.

The annotation is checked without an OCR
----------------------------------------
Nothing in the dependency baseline turns ink back into letters, so the note is
asserted in three parts that together say what one OCR would:
:func:`~nonogram.admin.book_proof.annotation_lines` is required to state
exactly what a ruler measures on the page it annotates (the numbers, formatted
by a second implementation of the format here); the page's foot is required to
carry ink where a plain COMP-007 page carries none; and changing the book's
trim is required to change that ink, so the note cannot be a fixed picture.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import re
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pytest
from PIL import Image

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.book_proof as book_proof_module
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import BookPDFGenerator, page_frame
from nonogram.admin.print_specs import PrintSpec
from nonogram.admin.book_proof import (
    PROOF_PUZZLES,
    annotation_lines,
    proof_pages,
    render_proof_pdf,
)
from nonogram.export.layout import compute_layout
from nonogram.export.pdf import render_pages
from nonogram.limits import MAX_SIZE
from tests.helpers.page_ink import drawing_of, pdf_page_boxes
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages

# --------------------------------------------------------------------------
# CON-018's Book 1 profile and the sheets these tests use, in millimetres.
# Written out here rather than imported, as tests/test_book_pdf_band.py does.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
SIX_BY_NINE_WIDTH_MM = 6 * 25.4
SIX_BY_NINE_HEIGHT_MM = 9 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4
TOP_MM = BOTTOM_MM = 0.375 * 25.4

#: The title band above each puzzle (TERM-028).
BAND_MM = 12.0

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = 300 / 25.4

#: A pixel darker than this (0..255 grey) is ink.
INK_LEVEL = 128

#: ADR-0037/R2's floor on a thin grid rule, and what it is in whole pixels at
#: 300 DPI: 0.25 mm is 2.95 px, which rounds *up* to 3.
MIN_THIN_RULE_MM = 0.25
MIN_THIN_RULE_PX = 3

#: The checkpoint's two cells (CARD-118, ADR-0037): the 30x30 with 9-deep
#: gutters and the 15x15 with 7-deep ones, on the Book 1 profile.
LARGE_CELL_MM = 4.97
SMALL_CELL_MM = 7.5
CELL_TOLERANCE_MM = 0.05

#: The gutter depths the two cells above are a consequence of.
LARGE_DEPTH = 9
SMALL_SIDE = 15
SMALL_DEPTH = 7

#: The band each proof page carries, written out here from ADR-0037's wording
#: rather than composed with the function under test.
EXPECTED_BANDS = ("Puzzle 1 · Hard", "Puzzle 2 · Easy")


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book(
    width_mm: float = BOOK1_WIDTH_MM,
    height_mm: float = BOOK1_HEIGHT_MM,
    gutter_mm: float = GUTTER_MM,
    outside_mm: float = OUTSIDE_MM,
    book_id: str = "book-118",
) -> Book:
    """A book carrying these print columns, and no puzzles at all."""
    return Book(
        book_id=book_id,
        metadata=BookMetadata(
            title="Winter Pictures",
            description="A test book.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(width_mm),
        trim_height_cm=_cm(height_mm),
        gutter_margin_cm=_cm(gutter_mm),
        outside_margin_cm=_cm(outside_mm),
    )


def _px(millimetres: float) -> int:
    """Millimetres as whole device pixels at 300 DPI, half rounded up."""
    return int(millimetres * PX_PER_MM + 0.5)


@pytest.fixture(scope="module")
def book1_pdf() -> bytes:
    """The proof PDF of a Book 1 profile book, rendered once for the module."""
    return render_proof_pdf(_book()).getvalue()


@pytest.fixture(scope="module")
def six_by_nine_pdf() -> bytes:
    return render_proof_pdf(_book(SIX_BY_NINE_WIDTH_MM, SIX_BY_NINE_HEIGHT_MM)).getvalue()


@pytest.fixture(scope="module")
def book1_large_page() -> Image.Image:
    """The 30x30 proof page as drawn, before the PDF's DCT round trip."""
    return proof_pages(_book())[0]


# --------------------------------------------------------------------------
# Reading ink off a page
# --------------------------------------------------------------------------


def _dark(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L")) < INK_LEVEL


def _has_ink(image: Image.Image) -> bool:
    return bool(_dark(image).any())


def _runs(mask: Iterable[bool]) -> list[list[int]]:
    """The consecutive runs of ``True`` in ``mask``, as lists of indices."""
    runs: list[list[int]] = []
    for index, is_set in enumerate(mask):
        if not is_set:
            continue
        if runs and runs[-1][-1] == index - 1:
            runs[-1].append(index)
        else:
            runs.append([index])
    return runs


def _scan(page: Image.Image, axis: str, mode: str = "L") -> np.ndarray:
    """One scanline across ``page``'s grid, cut to the grid's own extent.

    CARD-117's technique: the line is taken through the middle of the first
    cell of the *other* axis, so every run of ink it meets is a rule of this
    axis and nothing else — no clue digit, no band, no proof note.
    """
    drawing = drawing_of(page)
    pixels = np.asarray(page.convert(mode))
    past_last_rule = round(drawing.cell)
    if axis == "vertical":
        row = drawing.grid_top + round(drawing.cell / 2)
        return pixels[row, drawing.grid_left : drawing.grid_right + past_last_rule]
    column = drawing.grid_left + round(drawing.cell / 2)
    return pixels[drawing.grid_top : drawing.grid_bottom + past_last_rule, column]


def _rule_widths(scan: np.ndarray) -> list[int]:
    """The thickness in pixels of each ruled line a scanline crosses."""
    return [len(run) for run in _runs(scan < INK_LEVEL)]


def _band_strip(page: Image.Image) -> Image.Image:
    """The page's title band: the 12 mm below the top margin (TERM-028)."""
    top = round(TOP_MM * PX_PER_MM)
    return page.crop((0, top, page.width, top + round(BAND_MM * PX_PER_MM)))


def _foot_strip(page: Image.Image) -> Image.Image:
    """Everything below the drawing: where a proof note is, if there is one."""
    drawing = drawing_of(page)
    return page.crop(
        (0, drawing.grid_bottom + round(drawing.cell), page.width, page.height)
    )


def _ink_box(image: Image.Image) -> tuple[int, int, int, int]:
    """``(left, top, right, bottom)`` of every dark pixel, ends inclusive."""
    ys, xs = np.nonzero(_dark(image))
    if not len(xs):
        raise AssertionError("no ink to measure")
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


#: One device pixel per cell, in millimetres. The note states the layout's
#: *exact* cell while the page draws the pitch floored to whole pixels, so a
#: claim and a ruler may differ by that much and no more.
CELL_PITCH_SLACK_MM = 25.4 / 300

_STATED_CELL = re.compile(r"cell (\d+\.\d+) mm")


def _stated_cell_mm(geometry: str) -> float:
    """The cell the note claims, read out of its own text."""
    match = _STATED_CELL.search(geometry)
    assert match, f"the note states no cell: {geometry!r}"
    return float(match.group(1))


def _measured(page: Image.Image) -> dict[str, float]:
    """What a ruler reads off ``page``: its trim, its cell and its two rules."""
    widths = _rule_widths(_scan(page, "vertical"))
    drawing = drawing_of(page)
    heavy = max(widths)
    thin = min(widths)
    return {
        "width_mm": page.width / PX_PER_MM,
        "height_mm": page.height / PX_PER_MM,
        "cell_mm": drawing.cell / PX_PER_MM,
        "thin_mm": thin / PX_PER_MM,
        "heavy_mm": heavy / PX_PER_MM,
        "columns": drawing.columns,
        "rows": drawing.rows,
    }


# --------------------------------------------------------------------------
# CK-1 — two Book 1 pages, at the two cells the checkpoint names
# --------------------------------------------------------------------------


class TestBookProof_TwoTrimSizedPagesAtExpectedCells:
    """CK-1 — the Book 1 profile: 2 pages, 2550 x 3300 px, 4.97 mm and 7.5 mm."""

    TRIM_PX = (2550, 3300)
    #: 8.5 x 11 in in PDF points, which is what a printer trims to.
    TRIM_PT = (0.0, 0.0, 612.0, 792.0)

    def test_the_proof_is_exactly_two_pages(self, book1_pdf: bytes) -> None:
        assert pdf_page_count(book1_pdf) == 2

    def test_every_page_is_the_books_trim_in_pixels_and_in_its_page_box(
        self, book1_pdf: bytes
    ) -> None:
        """Both halves of "2550 x 3300 px at 300 DPI" (AC-177's technique)."""
        assert [page.size for page in pdf_pages(book1_pdf)] == [self.TRIM_PX] * 2
        assert pdf_page_boxes(book1_pdf) == [self.TRIM_PT] * 2

    def test_page_one_is_the_thirty_by_thirty_at_the_books_smallest_cell(
        self, book1_pdf: bytes
    ) -> None:
        """The 30x30 with 9-deep gutters: 4.97 mm (+/- 0.05), measured on the page."""
        drawing = drawing_of(pdf_pages(book1_pdf)[0])
        assert (drawing.columns, drawing.rows) == (MAX_SIZE, MAX_SIZE)
        assert drawing.cell / PX_PER_MM == pytest.approx(
            LARGE_CELL_MM, abs=CELL_TOLERANCE_MM
        )

    def test_page_two_is_the_fifteen_by_fifteen_at_the_cap(self, book1_pdf: bytes) -> None:
        """The 15x15 with 7-deep gutters: NFR-008's flat 7.5 mm cap."""
        drawing = drawing_of(pdf_pages(book1_pdf)[1])
        assert (drawing.columns, drawing.rows) == (SMALL_SIDE, SMALL_SIDE)
        assert drawing.cell / PX_PER_MM == pytest.approx(
            SMALL_CELL_MM, abs=CELL_TOLERANCE_MM
        )

    def test_the_two_pages_face_each_other(self, book1_pdf: bytes) -> None:
        """Proof page 1 is right-hand and page 2 left-hand (FR-032/FR-043).

        So the owner sees both mirrorings on the two sheets in hand. Page 1's
        30x30 fills the usable width, so its drawing starts at the gutter
        margin; page 2's 15x15 is narrower and is centred in a usable area
        that begins at the *outside* margin, which Increment 13's checkpoint
        puts at 23.875 mm from the trim edge on an even page (CARD-116).
        """
        odd, even = (drawing_of(page) for page in pdf_pages(book1_pdf))
        assert odd.left / PX_PER_MM == pytest.approx(GUTTER_MM, abs=0.1)
        assert even.left / PX_PER_MM == pytest.approx(23.875, abs=0.05)


# --------------------------------------------------------------------------
# CK-2 — the pages follow the book's stored trim
# --------------------------------------------------------------------------


class TestBookProof_FollowsStoredTrim:
    """CK-2 — a 6 x 9 in book proofs at 1800 x 2700 px."""

    TRIM_PX = (1800, 2700)
    TRIM_PT = (0.0, 0.0, 432.0, 648.0)

    def test_every_page_is_the_smaller_trim(self, six_by_nine_pdf: bytes) -> None:
        assert pdf_page_count(six_by_nine_pdf) == 2
        assert [page.size for page in pdf_pages(six_by_nine_pdf)] == [self.TRIM_PX] * 2
        assert pdf_page_boxes(six_by_nine_pdf) == [self.TRIM_PT] * 2

    def test_the_same_fixtures_take_the_smaller_sheets_own_cells(
        self, six_by_nine_pdf: bytes
    ) -> None:
        """The proof measures the *book*, not a remembered Book 1 number.

        The two fixtures are the same grids as CK-1's, so a proof that printed
        a stored geometry rather than this book's would report Book 1's cells
        on a 6 x 9 page. Both are smaller here — the sheet is narrower, so page
        fit binds on the 30x30 and beats the cap on the 15x15 too.
        """
        pages = pdf_pages(six_by_nine_pdf)
        large = drawing_of(pages[0]).cell / PX_PER_MM
        small = drawing_of(pages[1]).cell / PX_PER_MM
        assert large < LARGE_CELL_MM
        assert small < SMALL_CELL_MM
        # Still the book's own sheet: 39 and 22 cells across its usable width.
        usable_mm = SIX_BY_NINE_WIDTH_MM - GUTTER_MM - OUTSIDE_MM
        assert large == pytest.approx(usable_mm / (MAX_SIZE + LARGE_DEPTH), abs=0.05)
        assert small == pytest.approx(usable_mm / (SMALL_SIDE + SMALL_DEPTH), abs=0.05)

    def test_the_extents_do_not_change_with_the_trim(self, six_by_nine_pdf: bytes) -> None:
        """The fixtures are fixed; only the sheet they are laid on changes."""
        pages = pdf_pages(six_by_nine_pdf)
        assert (drawing_of(pages[0]).columns, drawing_of(pages[0]).rows) == (
            MAX_SIZE,
            MAX_SIZE,
        )
        assert (drawing_of(pages[1]).columns, drawing_of(pages[1]).rows) == (
            SMALL_SIDE,
            SMALL_SIDE,
        )


# --------------------------------------------------------------------------
# CK-3 — the strokes ADR-0037 fixes, measured on the proof
# --------------------------------------------------------------------------


class TestBookProof_StrokesMeetBookMinimum:
    """CK-3 — on the 30x30 proof page: thin >= 3 px, heavy = 2 x thin, pure black.

    Measured on the page as drawn rather than on the PDF's page: the file's
    DCT round trip greys a 3-pixel rule's edges, and the colour is half of
    what is being asserted.
    """

    #: Heavy rules: the borders and every 5th line of a 30-cell grid.
    HEAVY_INDICES = (0, 5, 10, 15, 20, 25, 30)

    @pytest.mark.parametrize("axis", ["vertical", "horizontal"])
    def test_every_thin_rule_clears_the_quarter_millimetre_floor(
        self, book1_large_page: Image.Image, axis: str
    ) -> None:
        widths = _rule_widths(_scan(book1_large_page, axis))
        assert len(widths) == MAX_SIZE + 1, "a 30-cell grid is ruled 31 times"
        thin = [
            width
            for index, width in enumerate(widths)
            if index not in self.HEAVY_INDICES
        ]
        assert min(thin) >= MIN_THIN_RULE_PX
        assert min(thin) / PX_PER_MM >= MIN_THIN_RULE_MM

    @pytest.mark.parametrize("axis", ["vertical", "horizontal"])
    def test_every_heavy_rule_is_twice_its_thin_rule(
        self, book1_large_page: Image.Image, axis: str
    ) -> None:
        widths = _rule_widths(_scan(book1_large_page, axis))
        heavy = [widths[index] for index in self.HEAVY_INDICES]
        thin = [
            width
            for index, width in enumerate(widths)
            if index not in self.HEAVY_INDICES
        ]
        assert min(heavy) > max(thin)
        assert set(heavy) == {2 * width for width in set(thin)}

    @pytest.mark.parametrize("axis", ["vertical", "horizontal"])
    def test_the_rule_pixels_are_pure_black(
        self, book1_large_page: Image.Image, axis: str
    ) -> None:
        """#000 or the paper, never a grey: a softened rule prints lighter."""
        greys = set(np.unique(_scan(book1_large_page, axis)).tolist())
        assert greys <= {0, 255}, f"the scanline carries greys: {sorted(greys)}"

        colour = _scan(book1_large_page, axis, mode="RGB").reshape(-1, 3)
        ink = colour[(colour < INK_LEVEL).all(axis=1)]
        assert len(ink), "no ink on the scanline"
        assert {tuple(pixel) for pixel in np.unique(ink, axis=0).tolist()} == {(0, 0, 0)}


# --------------------------------------------------------------------------
# The fixtures the two measurements depend on
# --------------------------------------------------------------------------


class TestBookProof_FixturesAreTheDepthsTheMeasurementsAssume:
    """4.97 mm and 7.5 mm are claims about *these* extents at *these* depths.

    A fixture edited to a different gutter depth would change the printed cell
    and silently retire the checkpoint's numbers, so the depths are pinned in
    the fixture and then re-read off the drawn page.
    """

    def test_the_large_fixture_is_the_biggest_grid_with_nine_deep_gutters(
        self,
    ) -> None:
        large = PROOF_PUZZLES[0]
        assert (large.width, large.height) == (MAX_SIZE, MAX_SIZE)
        assert large.row_gutter_depth == LARGE_DEPTH
        assert large.column_gutter_depth == LARGE_DEPTH

    def test_the_small_fixture_is_fifteen_by_fifteen_with_seven_deep_gutters(
        self,
    ) -> None:
        small = PROOF_PUZZLES[1]
        assert (small.width, small.height) == (SMALL_SIDE, SMALL_SIDE)
        assert small.row_gutter_depth == SMALL_DEPTH
        assert small.column_gutter_depth == SMALL_DEPTH

    def test_there_are_exactly_two_proof_puzzles(self) -> None:
        assert len(PROOF_PUZZLES) == 2

    @pytest.mark.parametrize(
        "index,depth", [(0, LARGE_DEPTH), (1, SMALL_DEPTH)]
    )
    def test_the_page_actually_draws_those_gutters(
        self, index: int, depth: int
    ) -> None:
        """Read back off the ink: the gutter is the drawing's edge to the grid's."""
        drawing = drawing_of(proof_pages(_book())[index])
        assert round((drawing.grid_left - drawing.left) / drawing.cell) == depth
        assert round((drawing.grid_top - drawing.top) / drawing.cell) == depth

    def test_the_fixtures_come_from_this_module_and_not_from_a_book(self) -> None:
        """A book with no puzzles at all proofs exactly like any other.

        Proofs come before curation (CARD-118), so the proof set cannot be
        drawn from the book's membership — and a book holding nothing is the
        case that proves it.
        """
        empty = _book(book_id="empty-draft")
        assert not empty.puzzle_ids
        by_book = [page.tobytes() for page in proof_pages(empty)]
        by_profile = [page.tobytes() for page in proof_pages(None)]
        assert by_book == by_profile

    def test_the_clues_on_the_page_are_the_fixtures_own_encoding(self) -> None:
        """INV-001: the clues drawn are the run-length encoding of the grid.

        Asserted on the page rather than on the dataclass: the fixture's clues
        are handed to COMP-007, so a page laid out from a different clue set
        would have a different gutter and a different cell.
        """
        for index, puzzle in enumerate(PROOF_PUZZLES):
            spec = book_page_spec(_book(), index + 1)
            layout = compute_layout(puzzle.row_clues, puzzle.column_clues, spec)
            assert layout.row_gutter_cells == puzzle.row_gutter_depth
            assert layout.column_gutter_cells == puzzle.column_gutter_depth


# --------------------------------------------------------------------------
# The band, and the proof-only annotation
# --------------------------------------------------------------------------


class TestBookProof_BandAndAnnotation:
    """Each page carries its "Puzzle N · Tier" band and one note at the foot."""

    @pytest.mark.parametrize("index,band", list(enumerate(EXPECTED_BANDS)))
    def test_each_page_carries_its_own_puzzle_number_band(
        self, index: int, band: str
    ) -> None:
        """The band strip matches the page COMP-007 draws for that exact line.

        The line is written out above from ADR-0037's wording, not composed
        with ``band_identity``, so this is a second statement of the rule.
        """
        page = proof_pages(_book())[index]
        puzzle = PROOF_PUZZLES[index]
        spec = book_page_spec(_book(), index + 1)
        expected, _ = render_pages(puzzle.payload(band), page_spec=spec)

        assert _has_ink(_band_strip(page)), "the band is blank"
        assert _band_strip(page).tobytes() == _band_strip(expected).tobytes()

    @pytest.mark.parametrize("index", [0, 1])
    def test_the_note_states_what_a_ruler_measures_on_that_page(
        self, index: int
    ) -> None:
        """The note's numbers, against the ink beside them.

        The formatting is restated here rather than imported: the assertion is
        that the page's claim and the page's ink agree, which is exactly the
        check the owner makes with a ruler.
        """
        book = _book()
        page = proof_pages(book)[index]
        puzzle = PROOF_PUZZLES[index]
        layout = compute_layout(
            puzzle.row_clues, puzzle.column_clues, book_page_spec(book, index + 1)
        )
        measured = _measured(page)
        trim, geometry = annotation_lines(layout)

        assert f"{measured['width_mm']:.1f} × {measured['height_mm']:.1f} mm" in trim
        assert _stated_cell_mm(geometry) == pytest.approx(
            measured["cell_mm"], abs=CELL_PITCH_SLACK_MM
        )
        assert f"thin rule {measured['thin_mm']:.2f} mm" in geometry
        assert f"heavy rule {measured['heavy_mm']:.2f} mm" in geometry
        assert (
            f"grid {measured['columns']} × {measured['rows']}" in geometry
        )

    @pytest.mark.parametrize("index", [0, 1])
    def test_the_note_is_ink_a_plain_book_page_does_not_carry(
        self, index: int
    ) -> None:
        """The control: COMP-007's own page of the same payload has a blank foot."""
        book = _book()
        page = proof_pages(book)[index]
        puzzle = PROOF_PUZZLES[index]
        plain, _ = render_pages(
            puzzle.payload(EXPECTED_BANDS[index]),
            page_spec=book_page_spec(book, index + 1),
        )
        assert not _has_ink(_foot_strip(plain))
        assert _has_ink(_foot_strip(page))

    def test_changing_the_trim_changes_what_the_note_says(self) -> None:
        """So the note cannot be a fixed picture pasted onto every book."""
        letter = _foot_strip(proof_pages(_book())[0])
        six_by_nine = _foot_strip(
            proof_pages(_book(SIX_BY_NINE_WIDTH_MM, SIX_BY_NINE_HEIGHT_MM))[0]
        )
        assert _has_ink(letter) and _has_ink(six_by_nine)
        assert letter.size != six_by_nine.size or letter.tobytes() != six_by_nine.tobytes()

    @pytest.mark.parametrize(
        "width_mm,height_mm",
        [
            (BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM),
            (SIX_BY_NINE_WIDTH_MM, SIX_BY_NINE_HEIGHT_MM),
            (5 * 25.4, 8 * 25.4),
        ],
    )
    @pytest.mark.parametrize("index", [0, 1])
    def test_the_note_sits_inside_the_books_own_margins(
        self, width_mm: float, height_mm: float, index: int
    ) -> None:
        """Inside the margins on both parities, mirrored with the page.

        The margins are worked out here from the stored columns, so the note's
        position is compared against the book's sheet rather than against the
        frame the module drew it in.
        """
        page = proof_pages(_book(width_mm, height_mm))[index]
        left, top, right, bottom = _ink_box(_foot_strip(page))
        inner_left = _px(GUTTER_MM if index % 2 == 0 else OUTSIDE_MM)
        inner_right = page.width - _px(OUTSIDE_MM if index % 2 == 0 else GUTTER_MM)

        assert left >= inner_left, "the note starts outside the inner margin"
        assert right <= inner_right, "the note runs past the outer margin"
        # ``_foot_strip`` is cropped from the drawing's bottom, so the note's
        # own bottom is measured against the page's foot through the crop.
        strip_top = page.height - _foot_strip(page).height
        assert strip_top + bottom <= page.height - _px(BOTTOM_MM)
        assert top >= 0

    def test_a_trim_with_no_room_for_the_note_is_refused_and_says_so(self) -> None:
        """A small square (15 x 15 cm): no spot on the sheet holds the note.

        The drawing fills the sheet top to bottom, so there is no foot strip;
        the side strips are 4.4 mm, too narrow for a 10 pt word; and the 30 x
        30's blank clue corner is about 27 mm square, too small for the note
        wrapped at 10 pt (CARD-172). Printing the note across the grid would
        make it unreadable where it has to be read, and printing it in the
        margin would break the rule it exists to demonstrate, so the export
        refuses. The 8.5 x 8.5 in trim this test used to pin now carries the
        note in its clue corner (``TestBookProof_SquareTrimsCarryTheNote``).
        """
        square = _book(150.0, 150.0)
        with pytest.raises(ValueError, match="no room for the proof note"):
            proof_pages(square)


class TestBookProof_AnnotationIsProofOnly:
    """A real book page never grows the proof note (CARD-118)."""

    def test_a_book_page_of_the_same_fixture_carries_no_note(self) -> None:
        """The fixture, put through the book export instead: a blank foot.

        The same grid and clues, rendered by ``BookPDFGenerator`` as an
        ordinary member of a book, must come out as COMP-007's page and nothing
        more — which is how "the annotation cannot reach the book" is asserted
        as behaviour rather than as an intention.
        """
        book = _book()
        puzzle = PROOF_PUZZLES[0]
        row = {
            "id": "proof-as-a-book-puzzle",
            "grid": [list(line) for line in puzzle.grid],
            "clues_rows": [list(clue) for clue in puzzle.row_clues],
            "clues_cols": [list(clue) for clue in puzzle.column_clues],
            "width": puzzle.width,
            "height": puzzle.height,
            "puzzle_name": "Proof",
            "difficulty_tier": "hard",
        }
        # Interior page 3 is the first puzzle page: page 1 is the guide page
        # and page 2 the "Hard" divider that opens this book's one level
        # (FR-043, CARD-128).
        page = BookPDFGenerator(book).interior_pages([row])[2]
        expected, _ = render_pages(
            puzzle.payload("Puzzle 1 · Hard"), page_spec=book_page_spec(book, 3)
        )
        assert not _has_ink(_foot_strip(page))
        assert page.tobytes() == expected.tobytes()

    def test_nothing_on_the_book_export_path_imports_this_module(self) -> None:
        """Only the panel's router reaches ``book_proof``.

        Walked with ``ast`` like the layering guard in ``tests/test_cli.py``:
        the note has one caller, so there is no path from a book download to
        this ink at all.
        """
        package = Path(__file__).resolve().parents[1] / "src" / "nonogram"
        importers = set()
        for path in sorted(package.rglob("*.py")):
            if path.name == "book_proof.py":
                continue
            with warnings.catch_warnings():
                # Parsing a module can re-raise its own SyntaxWarnings, which
                # belong to that module and not to this walk.
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [
                        f"{node.module or ''}.{alias.name}" for alias in node.names
                    ]
                    if node.level:  # from .book_proof import ...
                        names += [alias.name for alias in node.names]
                        names += [node.module or ""]
                if any("book_proof" in name for name in names):
                    importers.add(path.name)
        assert importers == {"app.py"}, importers


# --------------------------------------------------------------------------
# The route and the action that reaches it
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch, tmp_path):
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
    app.config["BOOK_COVER_DIR"] = str(tmp_path / "covers")
    with app.app_context():
        yield app


def _draft_book(app, width_cm: str = "21.59", height_cm: str = "27.94") -> str:
    """A draft book on the given trim, with no puzzles selected."""
    book_id = app.book_manager.create_book(
        title="Winter Pictures",
        description="Twenty winter pictures.",
        theme="generic",
        target_audience="adults",
        size=f"{width_cm}×{height_cm}",
    )
    assert app.book_manager.set_print_spec(book_id, PrintSpec(width_cm, height_cm))
    return book_id


class TestBookProof_ProofPagesRoute:
    """``GET /book/<id>/proof-pages`` serves the PDF (CARD-118)."""

    def test_a_draft_book_with_no_puzzles_downloads_two_proof_pages(
        self, admin_app
    ) -> None:
        book_id = _draft_book(admin_app)
        client = admin_app.test_client()

        response = client.get(f"/book/{book_id}/proof-pages")

        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert "attachment" in response.headers["Content-Disposition"]
        assert "proof_pages.pdf" in response.headers["Content-Disposition"]
        assert pdf_page_count(response.get_data()) == 2

    def test_the_downloaded_pages_are_the_books_stored_trim(self, admin_app) -> None:
        book_id = _draft_book(admin_app, "15.24", "22.86")
        client = admin_app.test_client()

        data = client.get(f"/book/{book_id}/proof-pages").get_data()

        assert [page.size for page in pdf_pages(data)] == [(1800, 2700)] * 2

    def test_a_trim_with_no_room_for_the_note_is_reported_not_served(
        self, admin_app
    ) -> None:
        """A trim no spot fits (15 x 15 cm) reaches the owner as a message, not a 500.

        The route sends them back to Print setup, which is where the trim that
        caused it is changed.
        """
        book_id = _draft_book(admin_app, "15.00", "15.00")
        client = admin_app.test_client()

        response = client.get(f"/book/{book_id}/proof-pages")

        assert response.status_code == 302
        assert f"/book/{book_id}/setup-print" in response.headers["Location"]
        with client.session_transaction() as session:
            messages = [text for _, text in session["_flashes"]]
        assert any("no room for the proof note" in text for text in messages), messages

    def test_an_unknown_book_is_sent_back_to_the_list(self, admin_app) -> None:
        response = admin_app.test_client().get("/book/no-such-book/proof-pages")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/books")

    def test_print_setup_offers_the_download(self, admin_app) -> None:
        """§11 UI: the action is on the screen that decides the trim."""
        book_id = _draft_book(admin_app)
        page = admin_app.test_client().get(f"/book/{book_id}/setup-print")

        assert page.status_code == 200
        body = page.get_data(as_text=True)
        assert f"/book/{book_id}/proof-pages" in body
        assert "Download proof pages" in body


# --------------------------------------------------------------------------
# EC — a proof page is the book's own sheet, for any stored print spec
# --------------------------------------------------------------------------

#: KDP paperback trims a puzzle book is actually printed on, **as the two
#: ``books`` columns store them** — portrait sheets, whose note sits at the
#: foot. These nine are also the trims ``TestBookProof_PortraitProofsAreByteIdentical``
#: pins to main's pixels (CARD-172 AC-6). Square and landscape trims are
#: :data:`FALLBACK_TRIMS_CM`; a small square that fits no spot is covered by
#: ``TestBookProof_BandAndAnnotation.test_a_trim_with_no_room_for_the_note_is_refused_and_says_so``.
CORPUS_TRIMS_CM: tuple[tuple[str, str], ...] = (
    ("12.70", "20.32"),  # 5 x 8 in
    ("13.34", "20.32"),  # 5.25 x 8 in
    ("13.97", "21.59"),  # 5.5 x 8.5 in
    ("15.24", "22.86"),  # 6 x 9 in
    ("15.60", "23.39"),  # 6.14 x 9.21 in
    ("17.78", "25.40"),  # 7 x 10 in
    ("19.05", "23.50"),  # 7.5 x 9.25 in
    ("20.32", "25.40"),  # 8 x 10 in
    ("21.59", "27.94"),  # 8.5 x 11 in (CON-018's Book 1 profile)
)

#: Square and landscape trims, stored the same way (CARD-172): the drawing
#: reaches the bottom margin, so the note moves to the outer side strip or the
#: 30 x 30's blank clue corner.
FALLBACK_TRIMS_CM: tuple[tuple[str, str], ...] = (
    ("20.96", "20.96"),  # 8.25 x 8.25 in
    ("21.59", "21.59"),  # 8.5 x 8.5 in
    ("20.96", "15.24"),  # 8.25 x 6 in (KDP landscape)
    ("27.94", "21.59"),  # 11 x 8.5 in
)

#: Side margins the corpus draws from, stored the same way: KDP's 0.25 in
#: floor (``MIN_SIDE_MARGIN_MM``) upwards.
CORPUS_MARGINS_CM: tuple[str, str, str, str] = ("0.64", "0.95", "1.27", "1.91")

#: The two-decimal centimetre strings CON-018's profile itself stores, and the
#: exact millimetres they stand for. ``book_page_spec`` reads a stored value
#: that *is* the profile's own storage form as the profile's exact number —
#: 0.375 in is 9.525 mm and stores as "0.95" — so a book created on the
#: profile and a legacy book with empty columns are the same sheet to the
#: micrometre. Restated here rather than imported: the corpus has to know what
#: it stored, and this is the rule, not the function that applies it.
PROFILE_STORED_MM = {"21.59": 215.9, "27.94": 279.4, "1.27": 12.7, "0.95": 9.525}


def _stored_mm(centimetres: str) -> float:
    """The millimetres a stored centimetre column means (see above)."""
    return PROFILE_STORED_MM.get(centimetres, float(centimetres) * 10)


def _book_cm(
    width_cm: str, height_cm: str, gutter_cm: str, outside_cm: str, book_id: str
) -> Book:
    """A book carrying exactly these stored print columns."""
    book = _book(book_id=book_id)
    book.trim_width_cm = width_cm
    book.trim_height_cm = height_cm
    book.gutter_margin_cm = gutter_cm
    book.outside_margin_cm = outside_cm
    return book

#: The corpus cannot silently shrink: no ``hypothesis`` in the dependency
#: baseline, so the floor is asserted inside the test (CLAUDE.md).
MIN_BOOKS = 36
MIN_PAGES = 72


def test_PropertyTest_BookProof_EveryStoredPrintSpecPrintsItsOwnSheet() -> None:
    """EC — for any stored print spec, a proof page *is* that book's page.

    A seeded corpus of books across KDP's portrait trims, the square and
    landscape trims of CARD-172, and the margin range. For every book, both
    proof pages are required to be:

    * the stored trim, to within half a device pixel, measured off the rendered
      image and converted here at 300 DPI;
    * drawn inside that book's **own** mirrored margins — the odd page's
      drawing starting at the gutter, the even page's at the outside margin,
      each worked out from what the corpus stored, never from the layout;
    * ruled at ADR-0037/R2's weights, thin >= 0.25 mm and heavy exactly twice
      it, whatever cell the sheet gave;
    * carrying a note whose stated cell is the cell the page actually draws.

    That last point is what makes the others load-bearing: a proof page is
    only a proof if its claim and its ink are the same measurement.
    """
    random_source = random.Random(20260923)
    books = 0
    pages_checked = 0
    cells_seen: set[float] = set()
    trims_seen: set[tuple[float, float]] = set()

    for index in range(MIN_BOOKS + 4):
        # Every square and landscape trim is taken once up front, so the
        # corpus covers each of them whatever the seed draws afterwards.
        if index < len(FALLBACK_TRIMS_CM):
            width_cm, height_cm = FALLBACK_TRIMS_CM[index]
        else:
            width_cm, height_cm = random_source.choice(
                CORPUS_TRIMS_CM + FALLBACK_TRIMS_CM
            )
        gutter_cm = random_source.choice(CORPUS_MARGINS_CM)
        outside_cm = random_source.choice(CORPUS_MARGINS_CM)
        book = _book_cm(width_cm, height_cm, gutter_cm, outside_cm, f"corpus-{index}")
        width_mm, height_mm = _stored_mm(width_cm), _stored_mm(height_cm)
        gutter_mm, outside_mm = _stored_mm(gutter_cm), _stored_mm(outside_cm)
        trims_seen.add((width_mm, height_mm))

        pages = proof_pages(book)
        assert len(pages) == 2
        for position, page in enumerate(pages, start=1):
            half_pixel_mm = 0.5 / PX_PER_MM
            assert page.width / PX_PER_MM == pytest.approx(
                width_mm, abs=half_pixel_mm
            ), f"book {index} page {position} is not the stored trim"
            assert page.height / PX_PER_MM == pytest.approx(
                height_mm, abs=half_pixel_mm
            )

            drawing = drawing_of(page)
            inner_mm = gutter_mm if position % 2 else outside_mm
            outer_mm = outside_mm if position % 2 else gutter_mm
            assert drawing.left / PX_PER_MM >= inner_mm - 0.05, (
                f"book {index} page {position} starts inside its margin"
            )
            assert (page.width - drawing.grid_right) / PX_PER_MM >= outer_mm - 0.05

            widths = _rule_widths(_scan(page, "vertical"))
            thin, heavy = min(widths), max(widths)
            assert thin >= MIN_THIN_RULE_PX, (index, position, widths)
            assert heavy == 2 * thin, (index, position, widths)

            puzzle = PROOF_PUZZLES[position - 1]
            layout = compute_layout(
                puzzle.row_clues, puzzle.column_clues, book_page_spec(book, position)
            )
            _, geometry = annotation_lines(layout)
            measured_cell = drawing.cell / PX_PER_MM
            assert _stated_cell_mm(geometry) == pytest.approx(
                measured_cell, abs=CELL_PITCH_SLACK_MM
            ), (
                f"book {index} page {position} claims {geometry!r} but draws "
                f"{measured_cell:.3f} mm"
            )
            cells_seen.add(round(measured_cell, 2))
            pages_checked += 1
        books += 1

    assert books >= MIN_BOOKS, books
    assert pages_checked >= MIN_PAGES, pages_checked
    assert len(trims_seen) >= 10, trims_seen
    fallback_mm = {(_stored_mm(w), _stored_mm(h)) for w, h in FALLBACK_TRIMS_CM}
    assert fallback_mm <= trims_seen, fallback_mm - trims_seen
    assert len(cells_seen) >= 8, cells_seen
    assert min(cells_seen) < 4.8 <= max(cells_seen), cells_seen


# --------------------------------------------------------------------------
# CARD-172 — square and landscape trims carry the note in a clear spot
# --------------------------------------------------------------------------
#
# The note is found on the page as the ink a proof page carries and COMP-007's
# own page of the same payload on the same spec does not: everything else on a
# proof page *is* that page (the band test above pins it). The plain page's ink
# is then exactly the drawing, its clue digits and the band — what the note
# must never touch.

#: CON-018's Book 1 margins as the ``books`` columns store them.
BOOK1_GUTTER_CM = "1.27"
BOOK1_OUTSIDE_CM = "0.95"

#: The clear air CARD-172 asks the fallback note to keep from the drawing's
#: rules, and what it is in whole pixels at 300 DPI, rounded down so a note
#: placed a full millimetre away always passes.
FALLBACK_INSET_MM = 1.0
FALLBACK_INSET_PX = int(FALLBACK_INSET_MM * PX_PER_MM)

#: CON-020's floor, and DejaVu Sans's cap height as a share of its em
#: (OS/2 sCapHeight 1493 over unitsPerEm 2048 in the bundled face).
FLOOR_PT = 10
DEJAVU_CAP_HEIGHT_RATIO = 1493 / 2048
FLOOR_CAP_PX = FLOOR_PT * 300 / 72 * DEJAVU_CAP_HEIGHT_RATIO

SQUARE_TRIMS_CM = (("20.96", "20.96"), ("21.59", "21.59"))
LANDSCAPE_TRIMS_CM = (("20.96", "15.24"), ("27.94", "21.59"))

#: The pages whose foot strip cannot hold the note, so it falls back: the
#: 30 x 30 on every square and landscape trim, and the 15 x 15 on 8.25 x 6 in,
#: whose drawing also reaches the bottom margin. On the squares and on
#: 11 x 8.5 in the 15 x 15 leaves 13.5 to 19.9 mm of foot, so its note stays
#: at the foot (CARD-172 Worktree notes).
FALLBACK_PAGES = (
    ("20.96", "20.96", 0),
    ("21.59", "21.59", 0),
    ("20.96", "15.24", 0),
    ("20.96", "15.24", 1),
    ("27.94", "21.59", 0),
)


def _book1_margins(width_cm: str, height_cm: str) -> Book:
    return _book_cm(
        width_cm, height_cm, BOOK1_GUTTER_CM, BOOK1_OUTSIDE_CM, f"card172-{width_cm}x{height_cm}"
    )


def _plain_page(book: Book, index: int) -> Image.Image:
    """COMP-007's page of proof puzzle ``index`` on ``book``'s sheet, no note."""
    plain, _ = render_pages(
        PROOF_PUZZLES[index].payload(EXPECTED_BANDS[index]),
        page_spec=book_page_spec(book, index + 1),
    )
    return plain


def _note_box(page: Image.Image, plain: Image.Image) -> tuple[int, int, int, int]:
    """The ink box of what the proof page adds to COMP-007's page."""
    added = _dark(page) & ~_dark(plain)
    ys, xs = np.nonzero(added)
    assert len(xs), "the page carries no note"
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _plain_ink_near(
    plain: Image.Image, box: tuple[int, int, int, int], pad: int
) -> int:
    """How many of the plain page's ink pixels lie within ``pad`` of ``box``."""
    left, top, right, bottom = box
    region = _dark(plain)[
        max(0, top - pad) : bottom + pad + 1, max(0, left - pad) : right + pad + 1
    ]
    return int(region.sum())


def _margins_px(page: Image.Image, index: int) -> tuple[int, int, int, int]:
    """The usable area from the stored Book 1 margins, mirrored by parity."""
    gutter, outside = _px(GUTTER_MM), _px(OUTSIDE_MM)
    inner_left = gutter if index % 2 == 0 else outside
    inner_right = page.width - (outside if index % 2 == 0 else gutter)
    return inner_left, _px(TOP_MM), inner_right, page.height - _px(BOTTOM_MM)


def _drawing_ink_box(plain: Image.Image) -> tuple[int, int, int, int]:
    """The drawing's ink box on the plain page: its ink from the drawing's top down."""
    drawing = drawing_of(plain)
    below_band = plain.crop((0, drawing.top - MIN_THIN_RULE_PX, plain.width, plain.height))
    left, top, right, bottom = _ink_box(below_band)
    offset = drawing.top - MIN_THIN_RULE_PX
    return left, top + offset, right, bottom + offset


def _assert_note_inside_margins_and_clear(
    page: Image.Image, plain: Image.Image, index: int
) -> tuple[int, int, int, int]:
    """The note is inside the book's own margins and touches no ink of the page."""
    box = _note_box(page, plain)
    inner_left, inner_top, inner_right, inner_bottom = _margins_px(page, index)
    left, top, right, bottom = box
    assert left >= inner_left and right < inner_right, (box, inner_left, inner_right)
    assert top >= inner_top and bottom < inner_bottom, (box, inner_top, inner_bottom)
    assert _plain_ink_near(plain, box, 0) == 0, "the note overprints the page's ink"
    erased = _dark(plain) & ~_dark(page)
    assert not erased.any(), "the note erased ink of the page"
    return box


class TestBookProof_SquareTrimsCarryTheNote:
    """AC-1 — 8.25 x 8.25 and 8.5 x 8.5 in: two pages, each note clear of the puzzle."""

    @pytest.mark.parametrize("width_cm,height_cm", SQUARE_TRIMS_CM)
    def test_both_pages_render_at_the_trim(self, width_cm: str, height_cm: str) -> None:
        pages = proof_pages(_book1_margins(width_cm, height_cm))
        side = _px(_stored_mm(width_cm))
        assert [page.size for page in pages] == [(side, side)] * 2

    @pytest.mark.parametrize("index", [0, 1])
    @pytest.mark.parametrize("width_cm,height_cm", SQUARE_TRIMS_CM)
    def test_the_note_is_inside_the_margins_and_touches_no_rule_or_digit(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        book = _book1_margins(width_cm, height_cm)
        page = proof_pages(book)[index]
        _assert_note_inside_margins_and_clear(page, _plain_page(book, index), index)

    @pytest.mark.parametrize("width_cm,height_cm", SQUARE_TRIMS_CM)
    def test_page_one_note_sits_inside_the_blank_clue_corner(
        self, width_cm: str, height_cm: str
    ) -> None:
        """Inside the box where the clue gutters meet, a millimetre off its rules.

        The corner is read off the plain page's ink: the drawing's outer edges
        and the grid's top-left border. Nothing of the plain page — no rule,
        no digit — lies within 1 mm of the note's ink.
        """
        book = _book1_margins(width_cm, height_cm)
        page = proof_pages(book)[0]
        plain = _plain_page(book, 0)
        drawing = drawing_of(plain)
        left, top, right, bottom = _note_box(page, plain)

        assert drawing.left < left and right < drawing.grid_left
        assert drawing.top < top and bottom < drawing.grid_top
        assert _plain_ink_near(plain, (left, top, right, bottom), FALLBACK_INSET_PX) == 0


    @pytest.mark.parametrize("width_cm,height_cm,index", FALLBACK_PAGES)
    def test_no_wrapped_line_starts_with_a_separator_dot(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        """The wrap keeps each " · " on the end of the line before it.

        Read off the ink: the note's printed lines are its bands of ink rows,
        and each line's first glyph — its first run of ink columns — must be
        a letter, digit or bracket, never the separator's dot. At 10 pt the
        dot is a few pixels tall; every other first glyph the note can start a
        line with is at least the face's x-height, so half the cap height
        tells them apart. On 8.5 x 8.5 in a plain greedy wrap would start a
        line with the dot.
        """
        book = _book1_margins(width_cm, height_cm)
        page = proof_pages(book)[index]
        added = _dark(page) & ~_dark(_plain_page(book, index))
        lines = _runs(added.any(axis=1))
        assert len(lines) >= 2, "the note did not wrap"
        for rows in lines:
            band = added[rows[0] : rows[-1] + 1]
            columns = _runs(band.any(axis=0))[0]
            first = band[:, columns[0] : columns[-1] + 1]
            glyph_rows = np.nonzero(first.any(axis=1))[0]
            height = int(glyph_rows.max() - glyph_rows.min() + 1)
            assert height >= FLOOR_CAP_PX / 2, (rows[0], height)


class TestBookProof_LandscapeTrimsCarryTheNote:
    """AC-2 — 8.25 x 6 and 11 x 8.5 in: the note in the outer side strip.

    Right of the drawing on the odd (right-hand) page, left of it on the even
    one: the outer margin's side, never the gutter's. On 11 x 8.5 in the
    15 x 15 page leaves 19.9 mm of foot, so its note keeps the foot placement
    that is unchanged wherever it fits.
    """

    SIDE_PAGES = (
        ("20.96", "15.24", 0),
        ("20.96", "15.24", 1),
        ("27.94", "21.59", 0),
    )

    @pytest.mark.parametrize("width_cm,height_cm", LANDSCAPE_TRIMS_CM)
    def test_both_pages_render_at_the_trim(self, width_cm: str, height_cm: str) -> None:
        pages = proof_pages(_book1_margins(width_cm, height_cm))
        size = (_px(_stored_mm(width_cm)), _px(_stored_mm(height_cm)))
        assert [page.size for page in pages] == [size] * 2

    @pytest.mark.parametrize("width_cm,height_cm,index", SIDE_PAGES)
    def test_the_note_is_in_the_outer_side_strip_clear_of_the_drawing(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        book = _book1_margins(width_cm, height_cm)
        page = proof_pages(book)[index]
        plain = _plain_page(book, index)
        left, top, right, bottom = _assert_note_inside_margins_and_clear(
            page, plain, index
        )
        d_left, d_top, d_right, d_bottom = _drawing_ink_box(plain)

        if index % 2 == 0:  # odd page: the outer margin is on the right
            assert left > d_right + FALLBACK_INSET_PX, (left, d_right)
        else:  # even page: the outer margin is on the left
            assert right < d_left - FALLBACK_INSET_PX, (right, d_left)
        assert top >= d_top, "the note rises into the band"

    def test_the_eleven_by_eight_and_a_half_small_page_keeps_its_foot_note(self) -> None:
        book = _book1_margins("27.94", "21.59")
        page = proof_pages(book)[1]
        plain = _plain_page(book, 1)
        _, top, _, _ = _assert_note_inside_margins_and_clear(page, plain, 1)
        assert top > _drawing_ink_box(plain)[3], "the note is not below the drawing"


class TestBookProof_FallbackNoteHoldsTheTenPointFloor:
    """AC-3 — a side-strip or corner note is set at no less than 10 pt.

    Measured on the ink: the first glyph of the note is the capital P of
    "PROOF", whose height is the face's cap height. At 10 pt and 300 DPI that
    is 41.7 px of em times DejaVu Sans's 0.729 cap ratio, 30.4 px. The foot
    note's 2.6 mm (31 px of em) would give 22.6 px.
    """

    @pytest.mark.parametrize("width_cm,height_cm,index", FALLBACK_PAGES)
    def test_the_first_capital_is_at_least_ten_point_cap_height(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        book = _book1_margins(width_cm, height_cm)
        page = proof_pages(book)[index]
        plain = _plain_page(book, index)
        added = _dark(page) & ~_dark(plain)
        left, top, _, _ = _note_box(page, plain)

        # The P's columns: the first run of note-ink columns from the left of
        # the first line. Its height: the first run of ink rows in them.
        line = added[top : top + round(FLOOR_PT * 300 / 72 * 1.2)]
        columns = _runs(line.any(axis=0))
        first_glyph = line[:, columns[0][0] : columns[0][-1] + 1]
        cap_height = len(_runs(first_glyph.any(axis=1))[0])

        assert cap_height >= FLOOR_CAP_PX, (cap_height, FLOOR_CAP_PX)


class TestBookProof_PortraitProofsAreByteIdentical:
    """AC-6 — every portrait corpus trim prints exactly the pixels main printed.

    The digests were recorded from main (b05c443) before CARD-172 changed
    ``book_proof.py``; the fixture says how.
    """

    BASELINE = json.loads(
        (Path(__file__).parent / "fixtures" / "proof_baseline_card172.json").read_text(
            encoding="utf-8"
        )
    )

    def test_the_baseline_covers_every_portrait_corpus_trim(self) -> None:
        assert set(self.BASELINE["digests"]) == {f"{w}x{h}" for w, h in CORPUS_TRIMS_CM}

    @pytest.mark.parametrize("width_cm,height_cm", CORPUS_TRIMS_CM)
    def test_both_pages_match_mains_pixels(self, width_cm: str, height_cm: str) -> None:
        book = _book_cm(
            width_cm,
            height_cm,
            self.BASELINE["gutter_margin_cm"],
            self.BASELINE["outside_margin_cm"],
            f"baseline-{width_cm}x{height_cm}",
        )
        digests = [hashlib.sha256(page.tobytes()).hexdigest() for page in proof_pages(book)]
        assert digests == self.BASELINE["digests"][f"{width_cm}x{height_cm}"]


# --------------------------------------------------------------------------
# CARD-179 — the wrapped note keeps each number with its unit
# --------------------------------------------------------------------------

#: The fallback note's face in device pixels: CON-020's 10 pt at 300 DPI.
FALLBACK_FACE_PX = round(FLOOR_PT * 300 / 72)

#: The two line pitches CARD-179 allows the fallback note: 1.2 and 1.07 of
#: the 42 px face, written out as the pixels a ruler reads.
NORMAL_PITCH_PX = 50
TIGHT_PITCH_PX = 45

#: The breaks the wrap must not make, written as patterns over the printed
#: text — a second statement of the rule, independent of how ``_wrapped``
#: tokenises. A number and the unit after it ...
_NUMBER_WITH_UNIT = re.compile(r"\d+(?:\.\d+)? (?:mm|in\)|dpi)")
#: ... and an "N × M" group with its leading bracket, unit and trailing comma.
_TIMES_GROUP = re.compile(r"\(?\d+(?:\.\d+)? × \d+(?:\.\d+)?(?: (?:mm|in\)|dpi))?,?")


def _layout_and_frame(book: Book, index: int):
    """COMP-007's layout and frame for proof puzzle ``index`` on ``book``."""
    spec = book_page_spec(book, index + 1)
    payload = PROOF_PUZZLES[index].payload(EXPECTED_BANDS[index])
    return compute_layout(payload.row_clues, payload.column_clues, spec), page_frame(spec)


def _fallback_of(width_cm: str, height_cm: str, index: int):
    """What ``_fallback_note`` chooses for this page: spot, lines, face, leading."""
    layout, frame = _layout_and_frame(_book1_margins(width_cm, height_cm), index)
    chosen = book_proof_module._fallback_note(annotation_lines(layout), layout, frame)
    assert chosen is not None, "no fallback spot holds the note"
    return chosen


def _break_offsets(lines: list[str]) -> list[int]:
    """Where each line break falls in ``" ".join(lines)``: the joining space's index."""
    offsets, position = [], 0
    for line in lines[:-1]:
        position += len(line)
        offsets.append(position)
        position += 1
    return offsets


def _bad_breaks(lines: list[str], font, width: int) -> list[str]:
    """Every break in ``lines`` that CARD-179's rules 1-3 forbid, described."""
    text = " ".join(lines)
    breaks = _break_offsets(lines)
    bad = [f"line starts with ×: {line!r}" for line in lines if line.startswith("×")]
    for match in _NUMBER_WITH_UNIT.finditer(text):
        bad += [
            f"unit parted from its number: {match.group()!r}"
            for offset in breaks
            if match.start() < offset < match.end()
        ]
    for match in _TIMES_GROUP.finditer(text):
        inside = [offset for offset in breaks if match.start() < offset < match.end()]
        if font.getlength(match.group()) <= width:
            bad += [f"group that fits is broken: {match.group()!r}" for _ in inside]
        else:
            after_times = match.start() + match.group().index("×") + 1
            bad += [
                f"over-wide group broken other than after ×: {match.group()!r}"
                for offset in inside
                if offset != after_times
            ]
    return bad


class TestBookProof_WrappedNoteKeepsUnitsWithNumbers:
    """AC-1, AC-2 — no "4.58 / mm", no line starting with "×".

    Read off the lines ``_fallback_note`` hands ``_annotate`` to print on each
    fallback page. Main's wrap broke at every space, so it printed
    ``cell 4.58`` / ``mm`` and ``grid 30 ×`` / ``30,`` in the square corners
    and started a line with ``× 6.00 in)`` on 8.25 x 6 in.
    """

    @pytest.mark.parametrize("width_cm,height_cm,index", FALLBACK_PAGES)
    def test_no_line_ends_on_a_number_whose_unit_starts_the_next(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        _, lines, _, _ = _fallback_of(width_cm, height_cm, index)
        for line, following in zip(lines, lines[1:]):
            parted = re.search(r"\d$", line) and re.match(r"(?:mm|in\)|dpi)(?!\w)", following)
            assert not parted, (line, following)

    @pytest.mark.parametrize("width_cm,height_cm,index", FALLBACK_PAGES)
    def test_no_line_starts_with_times(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        _, lines, _, _ = _fallback_of(width_cm, height_cm, index)
        assert not [line for line in lines if line.startswith("×")], lines

    @pytest.mark.parametrize("width_cm,height_cm,index", FALLBACK_PAGES)
    def test_every_group_that_fits_sits_on_one_line(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        spot, lines, font, _ = _fallback_of(width_cm, height_cm, index)
        assert _bad_breaks(lines, font, spot.right - spot.left) == [], lines

    @pytest.mark.parametrize("index", [0, 1])
    def test_the_over_wide_trim_group_breaks_only_after_the_times(self, index: int) -> None:
        """8.25 x 6 in: "209.6 × 152.4 mm" is wider than the side strip."""
        spot, lines, font, _ = _fallback_of("20.96", "15.24", index)
        assert font.getlength("209.6 × 152.4 mm") > spot.right - spot.left
        breaks = [
            (line, following)
            for line, following in zip(lines, lines[1:])
            if line.endswith("209.6 ×")
        ]
        assert len(breaks) == 1, lines
        assert breaks[0][1].startswith("152.4 mm"), lines
        assert "(8.25 × 6.00 in)" in lines[lines.index(breaks[0][0]) + 2], lines

    def test_a_group_exactly_as_wide_as_the_width_stays_whole(self) -> None:
        """A group that measures exactly ``width`` fits: it is not broken.

        The 8.25 x 6 in note wrapped at the trim group's own measured width,
        which the face gives as a whole number of pixels. Kills ``<=`` -> ``<``
        on the group-fit check (CARD-179 F-002).
        """
        layout, _ = _layout_and_frame(_book1_margins("20.96", "15.24"), 0)
        font = book_proof_module._note_font(FALLBACK_FACE_PX)
        group = "209.6 × 152.4 mm"
        width = font.getlength(group)
        assert width == int(width), width
        lines = book_proof_module._wrapped(
            " · ".join(annotation_lines(layout)), font, int(width)
        )
        assert lines is not None
        assert any(group in line for line in lines), lines

    @pytest.mark.parametrize("width_cm,height_cm,index", FALLBACK_PAGES)
    def test_the_lines_rejoin_to_the_note(
        self, width_cm: str, height_cm: str, index: int
    ) -> None:
        """The wrap only chooses breaks: it drops and adds no word (G-2)."""
        layout, _ = _layout_and_frame(_book1_margins(width_cm, height_cm), index)
        _, lines, _, _ = _fallback_of(width_cm, height_cm, index)
        assert " ".join(lines) == " · ".join(annotation_lines(layout))


#: Widths the property draws from, in device pixels: narrower than every
#: fallback spot measured on the Book 1 margins (374 px) up past the widest
#: (474 px), so both a group that fits and one that does not are drawn.
WRAP_WIDTHS_PX = (250, 520)
WIDTHS_PER_NOTE = 10
MIN_WRAP_CASES = 200


def test_PropertyTest_ProofNoteWrap_NeverSplitsAUnitOrStartsWithTimes() -> None:
    """AC-3 — at every drawn width, a wrap of the note obeys rules 1-3, keeps every word and fits.

    The notes are those of both proof pages on every corpus and fallback trim
    (26 texts, different trims and cells), each wrapped at seeded widths. The
    rules are checked by :func:`_bad_breaks`, which states them as patterns
    over the printed text rather than reusing the wrap's own tokens.
    """
    font = book_proof_module._note_font(FALLBACK_FACE_PX)
    rng = random.Random(179)
    cases = wrapped = over_wide_broken = 0
    for width_cm, height_cm in CORPUS_TRIMS_CM + FALLBACK_TRIMS_CM:
        book = _book1_margins(width_cm, height_cm)
        for index in (0, 1):
            layout, _ = _layout_and_frame(book, index)
            text = " · ".join(annotation_lines(layout))
            for _ in range(WIDTHS_PER_NOTE):
                width = rng.randint(*WRAP_WIDTHS_PX)
                lines = book_proof_module._wrapped(text, font, width)
                cases += 1
                if lines is None:
                    continue
                wrapped += 1
                assert " ".join(lines) == " ".join(text.split()), (width, lines)
                assert all(font.getlength(line) <= width for line in lines), (width, lines)
                assert _bad_breaks(lines, font, width) == [], (width, lines)
                # A line may end on × only where a group is wider than the
                # width (checked by _bad_breaks): count that the corpus draws it.
                over_wide_broken += any(line.endswith("×") for line in lines)
    assert cases >= MIN_WRAP_CASES, cases
    assert wrapped >= MIN_WRAP_CASES, wrapped
    assert over_wide_broken > 0, "no drawn width made a group break after its ×"


class TestBookProof_FallbackLeadingTightensOnlyWhenNeeded:
    """AC-4 — 45 px in the square corners, 50 px wherever 1.2 fits.

    The pitch is read off the ink: the note's printed lines are its bands of
    ink rows, and the pitch is the median step between band tops (a line
    whose first glyph is a bracket rises a few pixels above one that starts
    with a digit, so single steps wobble; the median does not).
    """

    PITCHES = (
        ("20.96", "20.96", 0, TIGHT_PITCH_PX),
        ("21.59", "21.59", 0, TIGHT_PITCH_PX),
        ("20.96", "15.24", 0, NORMAL_PITCH_PX),
        ("20.96", "15.24", 1, NORMAL_PITCH_PX),
        ("27.94", "21.59", 0, NORMAL_PITCH_PX),
    )

    @pytest.mark.parametrize("width_cm,height_cm,index,pitch", PITCHES)
    def test_the_printed_line_pitch(
        self, width_cm: str, height_cm: str, index: int, pitch: int
    ) -> None:
        book = _book1_margins(width_cm, height_cm)
        added = _dark(proof_pages(book)[index]) & ~_dark(_plain_page(book, index))
        tops = [rows[0] for rows in _runs(added.any(axis=1))]
        _, lines, _, _ = _fallback_of(width_cm, height_cm, index)
        assert len(tops) == len(lines), (len(tops), len(lines))
        steps = sorted(b - a for a, b in zip(tops, tops[1:]))
        assert steps[len(steps) // 2] == pitch, steps

    def test_a_spot_tries_the_tight_leading_before_the_next_spot(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A first spot holding the note only at 45 px wins over a roomy second one."""
        layout, frame = _layout_and_frame(_book1_margins("20.96", "20.96"), 0)
        lines = annotation_lines(layout)
        width = 457
        font = book_proof_module._note_font(FALLBACK_FACE_PX)
        count = len(book_proof_module._wrapped(" · ".join(lines), font, width))
        Spot = book_proof_module._Spot
        snug = Spot("snug", 0, 0, width, count * TIGHT_PITCH_PX)
        roomy = Spot("roomy", 0, 0, width, count * NORMAL_PITCH_PX * 2)
        monkeypatch.setattr(book_proof_module, "_fallback_spots", lambda *_: (snug, roomy))
        spot, _, _, leading = book_proof_module._fallback_note(lines, layout, frame)
        assert (spot.name, leading) == ("snug", TIGHT_PITCH_PX)

    def test_a_spot_that_holds_the_note_at_one_point_two_keeps_it(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        layout, frame = _layout_and_frame(_book1_margins("20.96", "20.96"), 0)
        lines = annotation_lines(layout)
        width = 457
        font = book_proof_module._note_font(FALLBACK_FACE_PX)
        count = len(book_proof_module._wrapped(" · ".join(lines), font, width))
        exact = book_proof_module._Spot("exact", 0, 0, width, count * NORMAL_PITCH_PX)
        monkeypatch.setattr(book_proof_module, "_fallback_spots", lambda *_: (exact,))
        _, _, _, leading = book_proof_module._fallback_note(lines, layout, frame)
        assert leading == NORMAL_PITCH_PX

    def test_a_spot_too_short_at_either_leading_is_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        layout, frame = _layout_and_frame(_book1_margins("20.96", "20.96"), 0)
        lines = annotation_lines(layout)
        width = 457
        font = book_proof_module._note_font(FALLBACK_FACE_PX)
        count = len(book_proof_module._wrapped(" · ".join(lines), font, width))
        short = book_proof_module._Spot("short", 0, 0, width, count * TIGHT_PITCH_PX - 1)
        monkeypatch.setattr(book_proof_module, "_fallback_spots", lambda *_: (short,))
        assert book_proof_module._fallback_note(lines, layout, frame) is None
