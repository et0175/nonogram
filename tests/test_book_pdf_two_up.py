"""CARD-127 — two puzzles to a page: the walk, the page, the bands (FR-040).

    AC-242 (INV-010)  TestBookPdf_TwoSmallSameTierNeighboursShareAPage
    AC-243 (INV-010)  TestBookPdf_TwelvePairSharesPageBelowStandardCell
    AC-244 (INV-010)  TestBookPdf_PairJustAboveTwoUpMinimumShares
    AC-245 (INV-010)  TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare
    AC-246 (INV-010)  TestBookPdf_FifteenPlusTwelveDoesNotPair
    AC-247 (INV-010)  TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare
    AC-248 (INV-010)  TestBookPdf_DifferentTiersNeverPair
    AC-249 (INV-010)  TestBookPdf_PairingNeverReordersToFindAPartner
    AC-250 (INV-010)  TestBookPdf_OddPuzzleOutPrintsAlone
    AC-251            TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand
    AC-252            TestBookPdf_TwoUpUpperSlotSharesFixedTopEdge

Every verdict is read off the **rendered interior**, never asked of the code
that produced it: how many pages the book has, how many drawings are on a page,
how big their cells are and where their top edges sit all come from the ink,
through ``tests/helpers/two_up_ink.py`` (which splits a two-up page and then
measures each half with CARD-116's ``page_ink``). The expected cells are FR-040
written out again here in floating-point millimetres — ``min(7.5 mm, usable
width / the wider drawing's columns, (trim height − top − bottom − two bands) /
both drawings' rows)`` — over CON-018's profile stated in inches. Nothing in
this module imports ``compute_pair_layout``, ``compute_layout`` or
``book_page_spec``.

A band is ink, and nothing in the dependency baseline turns ink back into
letters, so AC-251 does what CARD-117's band tests do: it renders the line this
card specifies through COMP-007's own header and compares the two bands' ink.
The comparison is on each band's **tight ink box** rather than on the strip it
sits in, because the lower slot's band starts wherever the pair's spare height
leaves it and the reference page's starts at the top margin — a comparison that
required them to agree to the pixel would be measuring the crop, not the words.
It carries the box's **left edge on the page** beside the glyphs (``_Ink``),
because a tight crop alone says what was set and not where: a band centred on
the trim's centre rather than on its slot's would be the same picture moved
sideways by (gutter − outside) / 2, and the glyph comparison would pass it.
The vertical placement is pinned by the millimetres the strips are cropped at.
"""

from __future__ import annotations

from typing import NamedTuple, Optional, Sequence

import numpy as np
import pytest
from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.export import ExportPayload
from nonogram.export.pdf import render_pages
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of
from tests.helpers.two_up_ink import drawings_of

# --------------------------------------------------------------------------
# CON-018's Book 1 profile in millimetres, written out rather than imported —
# the same figures tests/test_book_pdf.py and tests/test_book_pdf_band.py use.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = TOP_MM = BOTTOM_MM = 0.375 * 25.4

#: The title band above each puzzle (TERM-028), and NFR-008's standard cell.
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5

#: FR-040's two-up minimum: two puzzles share a page only at this cell or more.
TWO_UP_MINIMUM_MM = 7.0

#: The page's usable width, and the height a page has left once it reserves a
#: band for each of **two** puzzles: 193.675 mm and 236.35 mm on Book 1.
USABLE_WIDTH_MM = BOOK1_WIDTH_MM - GUTTER_MM - OUTSIDE_MM
PAIR_HEIGHT_MM = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = 300 / 25.4

#: How close a measured cell has to be to the millimetres worked out here: one
#: device pixel is 0.085 mm, and each of the grid's edges is rounded to one.
CELL_TOLERANCE_MM = 0.05

#: A pixel darker than this (0..255 grey) is ink, as ``page_ink`` reads one.
INK_LEVEL = 128


# --------------------------------------------------------------------------
# The book and its puzzles
# --------------------------------------------------------------------------


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book() -> Book:
    """A book on CON-018's Book 1 profile, as a ``books`` row carries it."""
    return Book(
        book_id="book-127",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="A test book.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(BOOK1_WIDTH_MM),
        trim_height_cm=_cm(BOOK1_HEIGHT_MM),
        gutter_margin_cm=_cm(GUTTER_MM),
        outside_margin_cm=_cm(OUTSIDE_MM),
    )


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> list[list[bool]]:
    """A grid whose row clues are ``row_depth`` deep and columns ``column_depth``.

    The two gutters are set **independently**, which is what several of these
    criteria are stated over (a 15x15 with a 5-deep column gutter beside a
    10x10 with a 3-deep one). Row 0 carries ``row_depth`` single cells with a
    gap between each, so it encodes to that many runs and no row is deeper;
    column 0 does the same down the page. They share the cell at the corner,
    which is one run of each, so neither count is disturbed.
    """
    if 2 * row_depth - 1 > columns or 2 * column_depth - 1 > rows:
        raise ValueError(
            f"a {columns}x{rows} grid cannot carry {row_depth}-deep row clues "
            f"and {column_depth}-deep column clues"
        )
    grid = [[False] * columns for _ in range(rows)]
    for step in range(row_depth):
        grid[0][2 * step] = True
    for step in range(column_depth):
        grid[2 * step][0] = True
    return grid


def _puzzle(
    columns: int = MIN_SIZE,
    rows: int = MIN_SIZE,
    depth: int = 4,
    column_depth: Optional[int] = None,
    tier: object = "easy",
    name: Optional[str] = "Snowflake",
    puzzle_id: str = "p",
) -> dict:
    """One book puzzle, in the shape the review service hands the generator.

    ``depth`` is the row-clue gutter's depth; ``column_depth`` the column-clue
    gutter's, defaulting to the same.
    """
    down_depth = depth if column_depth is None else column_depth
    grid = _grid(columns, rows, depth, down_depth)
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": tier,
    }


def _interior(puzzles: Sequence[dict]) -> list[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``."""
    return BookPDFGenerator(_book()).interior_pages(list(puzzles))


# --------------------------------------------------------------------------
# FR-040's arithmetic, written out here
# --------------------------------------------------------------------------


def _across(puzzle: dict) -> int:
    """The drawing's width in cells: the row-clue gutter plus the grid."""
    return max(len(clue) for clue in puzzle["clues_rows"]) + puzzle["width"]


def _down(puzzle: dict) -> int:
    """The drawing's height in cells: the column-clue gutter plus the grid."""
    return max(len(clue) for clue in puzzle["clues_cols"]) + puzzle["height"]


def _shared_cell_mm(first: dict, second: dict) -> float:
    """FR-040's shared cell for one pair on one Book 1 page, in millimetres."""
    return min(
        STANDARD_CELL_MM,
        USABLE_WIDTH_MM / max(_across(first), _across(second)),
        PAIR_HEIGHT_MM / (_down(first) + _down(second)),
    )


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


# --------------------------------------------------------------------------
# Reading a page's make-up off its ink
# --------------------------------------------------------------------------


def _page_shapes(pages: Sequence[Image.Image], first: int, count: int) -> list[list[tuple[int, int]]]:
    """The ``(columns, rows)`` of every drawing on each of ``count`` puzzle pages.

    ``first`` is the 1-based interior position of the first puzzle page. One
    inner list per page, in print order, each holding its drawings top to
    bottom — so the concatenation of the whole thing is the book's print order
    as the paper shows it.
    """
    return [
        [(drawing.columns, drawing.rows) for drawing in drawings_of(pages[number - 1])]
        for number in range(first, first + count)
    ]


class _Ink(NamedTuple):
    """A strip's ink: the tight crop, and where on the page it starts.

    The crop says *what* was set, ``left`` says *where* — the x of the leftmost
    ink pixel in the page's own pixels. Both are compared (``_same_ink``),
    because a tight crop is the same picture wherever it sits: a band centred
    on the trim's centre instead of on the slot's would be identical ink shifted
    by (gutter − outside) / 2, and every AC-251 assertion would still pass.
    """

    image: Image.Image
    left: int


def _ink(image: Image.Image, origin: int = 0) -> Optional[_Ink]:
    """``image`` cropped to its ink, or ``None`` when it carries none.

    ``origin`` is the crop's own x on the page, so ``left`` comes back in page
    pixels rather than in the strip's.
    """
    dark = np.asarray(image.convert("L")) < INK_LEVEL
    rows, columns = np.flatnonzero(dark.any(axis=1)), np.flatnonzero(dark.any(axis=0))
    if not rows.size:
        return None
    return _Ink(
        image.crop((columns[0], rows[0], columns[-1] + 1, rows[-1] + 1)),
        origin + int(columns[0]),
    )


#: How far inside the band's own 12 mm the strip compared below is taken. The
#: band's line is set at 5 mm, centred, so a millimetre off each end is white
#: whatever the line says — and it keeps the strip clear of the drawing's top
#: rule, which is centred on the band's lower edge and would otherwise be
#: counted as part of the band's ink.
_BAND_INSET_MM = 1.0


def _band_ink(page: Image.Image, top_mm: float) -> Optional[_Ink]:
    """The ink of the 12 mm band starting ``top_mm`` down the trim (TERM-028).

    ``top_mm`` is worked out in millimetres by the caller, from CON-018's
    profile and FR-040's own geometry, never read off a layout. The strip runs
    the full width of the trim, so the ``left`` that comes back is the band's
    own placement across the page and not an artefact of the crop.
    """
    top = round((top_mm + _BAND_INSET_MM) * PX_PER_MM)
    bottom = round((top_mm + BAND_MM - _BAND_INSET_MM) * PX_PER_MM)
    return _ink(page.crop((0, top, page.width, bottom)))


def _reference_band(puzzle: dict, page_number: int, identity: str) -> Optional[_Ink]:
    """The ink COMP-007 sets for ``identity`` on this puzzle's own single page.

    The same payload the generator builds from the row, except that this test
    supplies the two header fields: no picture name (a puzzle page carries
    none, ADR-0037/R1) and the band line, written out by the caller. Its band
    is the 12 mm below the top margin, where a single page's always is.
    """
    payload = ExportPayload(
        grid=puzzle["grid"],
        row_clues=tuple(tuple(clue) for clue in puzzle["clues_rows"]),
        column_clues=tuple(tuple(clue) for clue in puzzle["clues_cols"]),
        seed=0,
        mode="random",
        width=puzzle["width"],
        height=puzzle["height"],
        name=None,
        difficulty=identity,
    )
    blank, _ = render_pages(payload, page_spec=book_page_spec(_book(), page_number))
    return _band_ink(blank, TOP_MM)


def _same_ink(first: Optional[_Ink], second: Optional[_Ink]) -> bool:
    """The same letters **in the same place across the page**.

    Both bands are measured on a page of the same parity, so a band the slot
    centred correctly and the same band on a single page start on the same
    pixel column; the left edges are compared exactly, like the glyphs.
    """
    if first is None or second is None:
        return False
    return (
        first.left == second.left
        and first.image.size == second.image.size
        and first.image.tobytes() == second.image.tobytes()
    )


# --------------------------------------------------------------------------
# AC-242 — two small same-tier neighbours share a page at the standard cell
# --------------------------------------------------------------------------

#: The pair AC-242, AC-251 and AC-252 are all stated over: two easy 10x10
#: puzzles with 4-deep gutters both ways, so each drawing is 14 cells square.
_SMALL_PAIR = dict(columns=10, rows=10, depth=4)


class TestBookPdf_TwoSmallSameTierNeighboursShareAPage:
    """AC-242 — two easy 10x10s with 4-deep gutters print on one page at 7.5 mm.

    Their combined drawing height is 28 cells, which 236.35 mm of usable
    height fits at 8.44 mm — above NFR-008's standard cell, so the cap binds
    and the shared cell is 7.5 mm.
    """

    def test_the_page_fit_this_pair_asks_for_is_above_the_standard_cell(self):
        """The arithmetic the AC names, before any page is drawn."""
        first = _puzzle(**_SMALL_PAIR)

        assert _down(first) == 14 and _across(first) == 14
        assert abs(PAIR_HEIGHT_MM / 28 - 8.4411) < 1e-3
        assert abs(_shared_cell_mm(first, first) - STANDARD_CELL_MM) < 1e-9

    def test_both_puzzles_print_on_one_page(self):
        pages = _interior(
            [_puzzle(**_SMALL_PAIR, puzzle_id="a"), _puzzle(**_SMALL_PAIR, puzzle_id="b")]
        )

        # Guide, one shared puzzle page, divider, two answer pages.
        assert len(pages) == 5
        assert _page_shapes(pages, 2, 1) == [[(10, 10), (10, 10)]]

    def test_both_slots_print_at_the_standard_cell(self):
        pages = _interior(
            [_puzzle(**_SMALL_PAIR, puzzle_id="a"), _puzzle(**_SMALL_PAIR, puzzle_id="b")]
        )

        upper, lower = drawings_of(pages[1])

        for slot in (upper, lower):
            assert abs(_mm(slot.cell) - STANDARD_CELL_MM) < CELL_TOLERANCE_MM, _mm(slot.cell)
        assert abs(upper.cell - lower.cell) <= 1, "one shared cell"

    def test_printed_alone_they_would_have_taken_two_pages(self):
        """The saving this AC is about: the same two puzzles, different tiers."""
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, puzzle_id="a"),
                _puzzle(**_SMALL_PAIR, tier="medium", puzzle_id="b"),
            ]
        )

        assert len(pages) == 6
        assert _page_shapes(pages, 2, 2) == [[(10, 10)], [(10, 10)]]


# --------------------------------------------------------------------------
# AC-243 — a pair whose shared cell falls below the standard cell
# --------------------------------------------------------------------------


class TestBookPdf_TwelvePairSharesPageBelowStandardCell:
    """AC-243 — two easy 12x12s with 4-deep gutters share a page at 7.39 mm.

    32 cells of drawing height into 236.35 mm: the height fit binds, not the
    cap, so the pair prints at a cell the standard one never reaches.
    """

    PAIR = dict(columns=12, rows=12, depth=4)

    def test_both_puzzles_print_on_one_page_at_the_fitted_cell(self):
        pages = _interior([_puzzle(**self.PAIR, puzzle_id="a"), _puzzle(**self.PAIR, puzzle_id="b")])

        assert len(pages) == 5
        assert _page_shapes(pages, 2, 1) == [[(12, 12), (12, 12)]]
        for slot in drawings_of(pages[1]):
            assert abs(_mm(slot.cell) - 7.39) < CELL_TOLERANCE_MM, _mm(slot.cell)

    def test_that_cell_is_the_236_35_mm_over_32_cells_the_ac_names(self):
        first = _puzzle(**self.PAIR)

        assert _down(first) == 16
        assert abs(PAIR_HEIGHT_MM - 236.35) < 1e-9
        expected = _shared_cell_mm(first, first)
        assert abs(expected - 236.35 / 32) < 1e-9
        assert abs(expected - 7.39) < CELL_TOLERANCE_MM

    def test_it_is_below_the_standard_cell_and_above_the_two_up_minimum(self):
        first = _puzzle(**self.PAIR)
        cell = _shared_cell_mm(first, first)

        assert TWO_UP_MINIMUM_MM <= cell < STANDARD_CELL_MM


# --------------------------------------------------------------------------
# AC-244 / AC-245 — the 7.0 mm boundary, one cell of clue gutter apart
# --------------------------------------------------------------------------

#: AC-244's pair: an easy 15x15 with a 5-deep column-clue gutter followed by an
#: easy 10x10 with a 3-deep one — 20 + 13 = 33 cells down, 7.16 mm.
_FIFTEEN = dict(columns=15, rows=15, depth=5, column_depth=5)
_TEN = dict(columns=10, rows=10, depth=3, column_depth=3)

#: AC-245's: the same 15x15 with one more cell of column-clue gutter — 34 cells
#: down, 6.95 mm, under the minimum.
_FIFTEEN_DEEPER = dict(columns=15, rows=15, depth=5, column_depth=6)


class TestBookPdf_PairJustAboveTwoUpMinimumShares:
    """AC-244 — 33 cells of drawing height share a page at 7.16 mm."""

    def test_the_pair_prints_on_one_page(self):
        pages = _interior([_puzzle(**_FIFTEEN, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")])

        assert len(pages) == 5
        assert _page_shapes(pages, 2, 1) == [[(15, 15), (10, 10)]]

    def test_both_slots_print_at_the_shared_7_16_mm_cell(self):
        pages = _interior([_puzzle(**_FIFTEEN, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")])

        for slot in drawings_of(pages[1]):
            assert abs(_mm(slot.cell) - 7.16) < CELL_TOLERANCE_MM, _mm(slot.cell)

    def test_that_cell_is_33_cells_of_height_and_is_at_or_above_the_minimum(self):
        first, second = _puzzle(**_FIFTEEN), _puzzle(**_TEN)

        assert (_down(first), _down(second)) == (20, 13)
        cell = _shared_cell_mm(first, second)
        assert abs(cell - PAIR_HEIGHT_MM / 33) < 1e-9
        assert abs(cell - 7.16) < CELL_TOLERANCE_MM
        assert cell >= TWO_UP_MINIMUM_MM


class TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare:
    """AC-245 — one more cell of column-clue gutter, 6.95 mm, and they separate."""

    def test_the_two_puzzles_print_on_two_pages(self):
        pages = _interior(
            [_puzzle(**_FIFTEEN_DEEPER, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")]
        )

        assert len(pages) == 6, "guide, two puzzle pages, divider, two answers"
        assert _page_shapes(pages, 2, 2) == [[(15, 15)], [(10, 10)]]

    def test_the_cell_that_pair_would_need_is_under_the_minimum(self):
        first, second = _puzzle(**_FIFTEEN_DEEPER), _puzzle(**_TEN)

        assert (_down(first), _down(second)) == (21, 13)
        cell = _shared_cell_mm(first, second)
        assert abs(cell - PAIR_HEIGHT_MM / 34) < 1e-9
        assert abs(cell - 6.95) < CELL_TOLERANCE_MM
        assert cell < TWO_UP_MINIMUM_MM

    def test_one_cell_of_gutter_is_the_whole_difference(self):
        """AC-244 and AC-245 differ by a single cell of column-clue gutter."""
        shallow, deeper = _puzzle(**_FIFTEEN), _puzzle(**_FIFTEEN_DEEPER)

        assert (shallow["width"], shallow["height"]) == (deeper["width"], deeper["height"])
        assert _down(deeper) - _down(shallow) == 1


# --------------------------------------------------------------------------
# AC-246 — a pair that misses the minimum by more than a rounding
# --------------------------------------------------------------------------


class TestBookPdf_FifteenPlusTwelveDoesNotPair:
    """AC-246 — 36 cells of drawing height (6.57 mm) print on two pages."""

    TWELVE = dict(columns=12, rows=12, depth=4, column_depth=4)

    def test_the_two_puzzles_print_on_two_pages(self):
        pages = _interior([_puzzle(**_FIFTEEN, puzzle_id="a"), _puzzle(**self.TWELVE, puzzle_id="b")])

        assert len(pages) == 6
        assert _page_shapes(pages, 2, 2) == [[(15, 15)], [(12, 12)]]

    def test_the_cell_that_pair_would_need_is_6_57_mm(self):
        first, second = _puzzle(**_FIFTEEN), _puzzle(**self.TWELVE)

        assert _down(first) + _down(second) == 36
        cell = _shared_cell_mm(first, second)
        assert abs(cell - 6.57) < CELL_TOLERANCE_MM, cell
        assert cell < TWO_UP_MINIMUM_MM


# --------------------------------------------------------------------------
# AC-247 — the width term refuses a pair the height would have allowed
# --------------------------------------------------------------------------


class TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare:
    """AC-247 — a 22-wide drawing 28 cells across cannot hold 7.0 mm.

    193.675 mm of usable width over 28 cells is 6.92 mm, so the pair is
    refused on **width** although its combined height fits comfortably — the
    case that a fit measured down the page alone would wave through.
    """

    WIDE = dict(columns=22, rows=10, depth=6, column_depth=2)

    def test_the_two_puzzles_print_on_two_pages(self):
        pages = _interior([_puzzle(**self.WIDE, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")])

        assert len(pages) == 6
        assert _page_shapes(pages, 2, 2) == [[(22, 10)], [(10, 10)]]

    def test_the_height_would_have_fitted_and_the_width_is_what_refuses(self):
        wide, small = _puzzle(**self.WIDE), _puzzle(**_TEN)

        assert _across(wide) == 28
        assert USABLE_WIDTH_MM / 28 < TWO_UP_MINIMUM_MM
        assert abs(USABLE_WIDTH_MM / 28 - 6.92) < CELL_TOLERANCE_MM
        # The height term on its own would have allowed a 7.0 mm cell.
        assert PAIR_HEIGHT_MM / (_down(wide) + _down(small)) > TWO_UP_MINIMUM_MM
        assert _shared_cell_mm(wide, small) < TWO_UP_MINIMUM_MM


# --------------------------------------------------------------------------
# AC-248 — tiers first: a pair that fits but is not the same level
# --------------------------------------------------------------------------


class TestBookPdf_DifferentTiersNeverPair:
    """AC-248 — the book's last easy and first medium never share a page.

    Both are 10x10 with 4-deep gutters, so they are the pair of AC-242 in every
    respect but their tier. The page they do not share is the proof that the
    tier is consulted before the fit.
    """

    def test_the_easy_and_the_medium_print_on_two_pages(self):
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, tier="easy", puzzle_id="easy"),
                _puzzle(**_SMALL_PAIR, tier="medium", puzzle_id="medium"),
            ]
        )

        assert len(pages) == 6
        assert _page_shapes(pages, 2, 2) == [[(10, 10)], [(10, 10)]]

    def test_the_same_two_drawings_do_share_a_page_at_one_tier(self):
        """The control: only the tier changed between this and the AC's book."""
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, tier="easy", puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, tier="easy", puzzle_id="two"),
            ]
        )

        assert len(pages) == 5

    @pytest.mark.parametrize(
        "first_tier, second_tier",
        [
            ("easy", "Easy"),
            ("EASY", "easy"),
            ("hard", "guess"),
            ("Medium", "medium"),
        ],
    )
    def test_two_spellings_of_one_tier_are_one_tier(self, first_tier, second_tier):
        """ADR-0031's tier of record, not the string: "easy" and "Easy" pair, and
        so do "hard" and ADR-0031/R3's retired "guess"."""
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, tier=first_tier, puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, tier=second_tier, puzzle_id="two"),
            ]
        )

        assert len(pages) == 5

    @pytest.mark.parametrize("tier", [None, "", "extreme", 17])
    def test_a_row_with_no_tier_of_record_never_pairs(self, tier):
        """A puzzle whose stored grade is not a tier has no tier, so it has no
        tier equal to its neighbour's — not even another ungraded row's."""
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, tier=tier, puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, tier=tier, puzzle_id="two"),
            ]
        )

        assert len(pages) == 6


# --------------------------------------------------------------------------
# AC-249 / AC-250 — the walk goes forward, in order, and leaves no gap
# --------------------------------------------------------------------------


class TestBookPdf_PairingNeverReordersToFindAPartner:
    """AC-249 — A, B, C with A and C a fitting pair still prints three pages.

    A and C are the two halves of AC-242's page. B, an easy 20x20 with 8-deep
    gutters, fits with neither. A book that moved C up beside A would save a
    page and silently overrule the order the owner arranged (INV-009).
    """

    BIG = dict(columns=20, rows=20, depth=8, column_depth=8)

    def _book_order(self):
        return [
            _puzzle(**_SMALL_PAIR, puzzle_id="A"),
            _puzzle(**self.BIG, puzzle_id="B"),
            _puzzle(**_SMALL_PAIR, puzzle_id="C"),
        ]

    def test_the_three_puzzles_print_on_three_pages_in_order(self):
        pages = _interior(self._book_order())

        assert len(pages) == 8, "guide, three puzzle pages, divider, three answers"
        assert _page_shapes(pages, 2, 3) == [[(10, 10)], [(20, 20)], [(10, 10)]]

    def test_a_and_c_would_have_fitted_together(self):
        """The saving the walk declines to take, stated as the AC states it."""
        a, b, c = self._book_order()

        assert _shared_cell_mm(a, c) >= TWO_UP_MINIMUM_MM
        assert _shared_cell_mm(a, b) < TWO_UP_MINIMUM_MM
        assert _shared_cell_mm(b, c) < TWO_UP_MINIMUM_MM

    def test_moving_c_next_to_a_is_what_would_have_paired_them(self):
        """The control: the same three puzzles in an order that does pair."""
        a, b, c = self._book_order()

        pages = _interior([a, c, b])

        assert len(pages) == 7, "one page saved: the answer section is unchanged"
        assert _page_shapes(pages, 2, 2) == [[(10, 10), (10, 10)], [(20, 20)]]


class TestBookPdf_OddPuzzleOutPrintsAlone:
    """AC-250 — three fitting same-tier neighbours make a pair and a single."""

    def _three(self):
        return [_puzzle(**_SMALL_PAIR, puzzle_id=name) for name in ("one", "two", "three")]

    def test_puzzles_one_and_two_share_a_page_and_three_prints_alone(self):
        pages = _interior(self._three())

        assert len(pages) == 7, "guide, two puzzle pages, divider, three answers"
        assert _page_shapes(pages, 2, 2) == [[(10, 10), (10, 10)], [(10, 10)]]

    def test_the_third_page_is_a_single_puzzle_page(self):
        """Interior page 3 carries one drawing, at the cell a single page gives
        a 10x10 with 4-deep gutters: the standard cell."""
        pages = _interior(self._three())

        (alone,) = drawings_of(pages[2])

        assert (alone.columns, alone.rows) == (10, 10)
        assert abs(_mm(alone.cell) - STANDARD_CELL_MM) < CELL_TOLERANCE_MM

    def test_a_fourth_puzzle_joins_the_odd_one_out(self):
        """The walk resumes at the puzzle left alone, so a fourth pairs with it."""
        pages = _interior(self._three() + [_puzzle(**_SMALL_PAIR, puzzle_id="four")])

        assert len(pages) == 8, "guide, two shared puzzle pages, divider, four answers"
        assert _page_shapes(pages, 2, 2) == [
            [(10, 10), (10, 10)],
            [(10, 10), (10, 10)],
        ]


# --------------------------------------------------------------------------
# AC-251 — each slot under its own band, numbered in print order
# --------------------------------------------------------------------------


class TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand:
    """AC-251 — the upper band reads "Puzzle 1 · Easy", the lower "Puzzle 2 · Easy".

    The two lines are written out here, set through COMP-007's own header on a
    single page of the same book, and compared with the ink each band of the
    two-up page carries. A band saying anything else — the wrong number, a
    stored ``"easy"`` unlabelled, the picture's title — is different ink.
    """

    #: Where each band starts, in millimetres down the trim. The upper band is
    #: where every single page's is, the top margin. The lower one is worked
    #: out from the bottom up: the lower drawing's 14 cells at the 7.5 mm
    #: shared cell end on the bottom margin, and its band is the 12 mm above
    #: them — 279.4 − 9.525 − 105 − 12 = 152.875 mm.
    UPPER_BAND_TOP_MM = TOP_MM
    LOWER_BAND_TOP_MM = BOOK1_HEIGHT_MM - BOTTOM_MM - 14 * STANDARD_CELL_MM - BAND_MM

    def _page(self):
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, puzzle_id="two"),
            ]
        )
        assert len(pages) == 5, "the pair does share a page"
        return pages[1]  # interior page 2

    def test_the_lower_band_sits_where_the_pair_leaves_it(self):
        """The millimetres the crops below are taken at, stated before use."""
        assert abs(self.LOWER_BAND_TOP_MM - 152.875) < 1e-9

    def test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two(self):
        page = self._page()
        puzzle = _puzzle(**_SMALL_PAIR)

        upper = _band_ink(page, self.UPPER_BAND_TOP_MM)
        lower = _band_ink(page, self.LOWER_BAND_TOP_MM)

        assert upper is not None, "the upper band is blank"
        assert lower is not None, "the lower band is blank"
        assert _same_ink(upper, _reference_band(puzzle, 2, "Puzzle 1 · Easy"))
        assert _same_ink(lower, _reference_band(puzzle, 2, "Puzzle 2 · Easy"))

    def test_the_two_bands_are_not_the_same_line(self):
        """The measurement has teeth: one band is not the other's ink."""
        page = self._page()

        assert not _same_ink(
            _band_ink(page, self.UPPER_BAND_TOP_MM),
            _band_ink(page, self.LOWER_BAND_TOP_MM),
        )

    def test_neither_band_carries_the_pictures_title(self):
        """ADR-0037/R1 on a two-up page: rename both pictures and the page is
        identical, pixel for pixel."""
        named = _interior(
            [
                _puzzle(**_SMALL_PAIR, name="Snowflake", puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, name="Snowflake", puzzle_id="two"),
            ]
        )
        renamed = _interior(
            [
                _puzzle(**_SMALL_PAIR, name="Iguanodon Skeleton", puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, name="Pterodactyl", puzzle_id="two"),
            ]
        )

        assert named[1].tobytes() == renamed[1].tobytes()
        # The control: the answer pages, which do carry the title, differ.
        assert named[3].tobytes() != renamed[3].tobytes()

    def test_the_numbers_follow_the_pages_before_this_one(self):
        """Puzzle numbers are 1..n in print order, whatever the pages hold: a
        two-up page after a single page carries 2 and 3, not 1 and 2."""
        pages = _interior(
            [
                _puzzle(**_FIFTEEN_DEEPER, tier="hard", puzzle_id="alone"),
                _puzzle(**_SMALL_PAIR, puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, puzzle_id="two"),
            ]
        )
        assert _page_shapes(pages, 2, 2) == [[(15, 15)], [(10, 10), (10, 10)]]
        puzzle = _puzzle(**_SMALL_PAIR)

        page = pages[2]  # interior page 3, the two-up page
        assert _same_ink(
            _band_ink(page, self.UPPER_BAND_TOP_MM),
            _reference_band(puzzle, 3, "Puzzle 2 · Easy"),
        )
        assert _same_ink(
            _band_ink(page, self.LOWER_BAND_TOP_MM),
            _reference_band(puzzle, 3, "Puzzle 3 · Easy"),
        )


# --------------------------------------------------------------------------
# AC-252 — the upper slot's drawing starts on a single page's top edge
# --------------------------------------------------------------------------


class TestBookPdf_TwoUpUpperSlotSharesFixedTopEdge:
    """AC-252 — the upper puzzle's drawing starts on the 20x20's pixel row.

    EC-022's fixed offset — top margin plus band — is what every puzzle page of
    a book puts its drawing's top edge on, and a two-up page's upper slot is
    not an exception to it.
    """

    BIG = dict(columns=20, rows=20, depth=8, column_depth=8)

    def _pages(self):
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, puzzle_id="two"),
                _puzzle(**self.BIG, tier="medium", puzzle_id="big"),
            ]
        )
        assert _page_shapes(pages, 2, 2) == [[(10, 10), (10, 10)], [(20, 20)]]
        return pages

    def test_the_upper_slot_and_the_single_page_share_a_top_pixel_row(self):
        pages = self._pages()

        upper, lower = drawings_of(pages[1])
        single = drawing_of(pages[2])

        assert upper.top == single.top
        assert lower.top > upper.top, "the lower slot is a second drawing below it"

    def test_that_row_is_the_top_margin_plus_the_band(self):
        pages = self._pages()

        upper, _ = drawings_of(pages[1])

        assert abs(_mm(upper.top) - (TOP_MM + BAND_MM)) <= _mm(0.5) + 1e-9

    def test_the_two_pages_really_do_print_different_cells(self):
        """The negative control: a shared top edge is not two identical pages."""
        pages = self._pages()

        upper, _ = drawings_of(pages[1])
        single = drawing_of(pages[2])

        assert abs(upper.cell - single.cell) > 1


# --------------------------------------------------------------------------
# The two copies of the export's header-fitting ratios are pinned equal
# --------------------------------------------------------------------------


def test_a_two_up_band_is_fitted_by_the_exports_own_header_ratios() -> None:
    """``_set_band``'s shrink-to-fit is COMP-007's, not a second tuning.

    ``book_pdf_generator`` restates ``pdf``'s two header ratios rather than
    importing them, because they are private to that module and G-3 forbids
    widening its surface. The restatement is only safe while the two agree: if
    COMP-007 retuned its header fitting, a band drawn on a two-up page and the
    same band drawn on a single page would start shrinking at different widths,
    and no AC above would notice — "Puzzle 1 · Easy" never reaches the shrink
    branch, so the ink comparisons never exercise these numbers.

    Importing the private names is legal here and nowhere else: the test tree
    is where the project cross-checks a deliberate reimplementation against its
    original (CLAUDE.md, the ``clues.encode_line`` precedent).
    """
    from nonogram.admin import book_pdf_generator
    from nonogram.export import pdf

    assert (
        book_pdf_generator._BAND_WIDTH_RATIO,
        book_pdf_generator._MIN_BAND_FONT_RATIO,
    ) == (pdf._HEADER_WIDTH_RATIO, pdf._MIN_HEADER_FONT_RATIO)


# --------------------------------------------------------------------------
# The extents these criteria are stated over are the supported ones
# --------------------------------------------------------------------------


def test_the_measured_extents_are_inside_con_011() -> None:
    """Every grid above is one the tool supports (CON-011)."""
    for shape in (_SMALL_PAIR, _FIFTEEN, _FIFTEEN_DEEPER, _TEN,
                  dict(columns=12, rows=12), dict(columns=22, rows=10),
                  dict(columns=20, rows=20)):
        assert MIN_SIZE <= shape["columns"] <= MAX_SIZE
        assert MIN_SIZE <= shape["rows"] <= MAX_SIZE
