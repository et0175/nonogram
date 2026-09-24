"""CARD-141: an answer page's rows take the height they need (FR-042).

    New  TestAnswerLayout_SpareHeightFallsAtThePageFoot
    New  TestAnswerLayout_CellSizesAreUnchangedByRowPacking
    New  TestAnswerLayout_UniformPageIsUnchangedAboveTheFoot

The owner's ruling of 2026-09-23: the height a short row of answers does not
use belongs at the **foot** of the page, not as a white band between two rows.
Vertical centring inside each tile was the alternative and was rejected.

What does *not* move is the cell: it is still measured against the page's
``capacity`` equal tiles (ADR-0036/R2's one cell size per page), and only then
are the rows laid out at their content height. CARD-133's pinned millimetre
figures (AC-262, AC-265, AC-294, AC-295) are therefore untouched, and
``TestAnswerLayout_CellSizesAreUnchangedByRowPacking`` re-asserts them here
from the other side: the same answer prints at the same cell whoever it shares
its page and its row with.

Every expected number below is worked out from FR-042's definition and CON-018's
Book 1 literals, in floating-point millimetres, with none of ``layout``'s
helpers: usable width 215.9 − 12.7 − 9.525 = 193.675 mm, answer-page usable
height (no title band) 279.4 − 2 × 9.525 = 260.35 mm, a measured tile
(193.675 − 2) / 2 by (260.35 − heading − (rows − 1) × 2) / rows, a cell of
min(5.0, tile width / columns, (tile height − 6) / rows), and a row of
6 mm + the tallest ``rows × cell`` in it.

EC-031 and the standing no-overlap/no-overflow property are in
``tests/property/test_answer_page_layout.py``.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

import pytest

from nonogram.export.layout import (
    ANSWER_CAPTION_MM,
    ANSWER_HEADING_MM,
    ANSWER_MAX_CELL_MM,
    ANSWER_TILE_GAP_MM,
    DPI,
    AnswerPageLayout,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_answer_page_layout,
)

#: CON-018's Book 1 profile, as ``tests/test_layout_answer_tiles.py`` writes it
#: (an ``export`` test never imports the admin-side builder).
BOOK1_ODD = PageSpec(
    width_mm=215.9,
    height_mm=279.4,
    top_mm=9.525,
    bottom_mm=9.525,
    gutter_mm=12.7,
    outside_mm=9.525,
    band_mm=12.0,
    orientation=OrientationPolicy.PORTRAIT_ONLY,
    cell_cap=7.5,
    min_thin_rule_mm=0.25,
    parity=PageParity.ODD,
)
BOOK1_EVEN = dataclasses.replace(BOOK1_ODD, parity=PageParity.EVEN)

USABLE_WIDTH_MM = 193.675
#: No title band on an answer page: the trim minus the top and bottom margins.
USABLE_HEIGHT_MM = 260.35
TILE_WIDTH_MM = (USABLE_WIDTH_MM - ANSWER_TILE_GAP_MM) / 2
PX_PER_MM = DPI / 25.4
#: One device pixel in millimetres: every coordinate is rounded to a whole
#: pixel, so a difference of two of them is exact only to within 0.085 mm.
PIXEL_MM = 1.0 / PX_PER_MM

Extent = tuple[int, int]


def _measured_tile_height_mm(capacity: int, *, heading: bool) -> float:
    """The equal tile FR-042 measures the cell against — CARD-141 leaves it be."""
    rows = capacity // 2
    reserved = (ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM) if heading else 0.0
    return (USABLE_HEIGHT_MM - reserved - (rows - 1) * ANSWER_TILE_GAP_MM) / rows


def _cell_mm(extent: Extent, capacity: int, *, heading: bool) -> float:
    """FR-042's cell for one answer on one kind of page."""
    columns, rows = extent
    return min(
        ANSWER_MAX_CELL_MM,
        TILE_WIDTH_MM / columns,
        (_measured_tile_height_mm(capacity, heading=heading) - ANSWER_CAPTION_MM) / rows,
    )


def _row_height_mm(row: Sequence[Extent], capacity: int, *, heading: bool) -> float:
    """CARD-141's row: its caption line plus the tallest grid standing on it."""
    return ANSWER_CAPTION_MM + max(
        rows * _cell_mm((columns, rows), capacity, heading=heading)
        for columns, rows in row
    )


def _rows_of(extents: Sequence[Extent]) -> list[list[Extent]]:
    """The extents grouped into the rows they fill, two across."""
    return [list(extents[start : start + 2]) for start in range(0, len(extents), 2)]


def _reserved_mm(*, heading: bool) -> float:
    """What a level heading costs the tiles: its line plus one tile gap."""
    return (ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM) if heading else 0.0


def _row_tops_mm(
    extents: Sequence[Extent], capacity: int, *, heading: bool
) -> list[float]:
    """Each row's top, in millimetres below the usable area's own top."""
    top = _reserved_mm(heading=heading)
    tops = []
    for row in _rows_of(extents):
        tops.append(top)
        top += _row_height_mm(row, capacity, heading=heading) + ANSWER_TILE_GAP_MM
    return tops


def _page(
    extents: list[Extent],
    capacity: int,
    spec: PageSpec = BOOK1_ODD,
    heading: str | None = None,
) -> AnswerPageLayout:
    return compute_answer_page_layout(extents, capacity, spec, heading)


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


#: A six-up page whose top row is two small answers and whose other two rows
#: are full-height ones: the mixed page of the CARD-134 render the owner ruled
#: on (``~/Documents/nonogram-reviews/CARD-134/03-mixed-1.png``).
SHORT_TOP_ROW_SIX_UP: list[Extent] = [
    (10, 10),
    (12, 10),
    (20, 20),
    (20, 20),
    (18, 20),
    (20, 19),
]
#: The same shape four-up: a short row above a full one.
SHORT_TOP_ROW_FOUR_UP: list[Extent] = [(10, 10), (14, 12), (30, 30), (28, 30)]


class TestAnswerLayout_SpareHeightFallsAtThePageFoot:
    """The white band moves out from between the rows and down to the foot.

    Two claims, on a page whose top row is shorter than the ones below it: the
    only thing between two rows is :data:`ANSWER_TILE_GAP_MM`, and everything
    the rows did not use is one band below the bottom row.
    """

    @pytest.mark.parametrize(
        ("extents", "capacity"),
        [(SHORT_TOP_ROW_SIX_UP, 6), (SHORT_TOP_ROW_FOUR_UP, 4)],
    )
    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_only_the_tile_gap_separates_two_rows(
        self, extents: list[Extent], capacity: int, heading: str | None
    ) -> None:
        page = _page(extents, capacity, heading=heading)

        rows = [page.tiles[start : start + 2] for start in range(0, len(page.tiles), 2)]
        for above, below in zip(rows, rows[1:]):
            # A row is one band: both its tiles start and end together.
            assert {tile.tile_top for tile in above} == {above[0].tile_top}
            assert {tile.tile_bottom for tile in above} == {above[0].tile_bottom}
            assert _mm(below[0].tile_top - above[0].tile_bottom) == pytest.approx(
                ANSWER_TILE_GAP_MM, abs=PIXEL_MM
            )

    @pytest.mark.parametrize(
        ("extents", "capacity"),
        [(SHORT_TOP_ROW_SIX_UP, 6), (SHORT_TOP_ROW_FOUR_UP, 4)],
    )
    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_what_the_rows_do_not_use_is_a_band_below_the_bottom_row(
        self, extents: list[Extent], capacity: int, heading: str | None
    ) -> None:
        page = _page(extents, capacity, heading=heading)
        headed = heading is not None

        # The foot is what the measured tiles would have spent and the rows did not.
        spare_mm = sum(
            _measured_tile_height_mm(capacity, heading=headed)
            - _row_height_mm(row, capacity, heading=headed)
            for row in _rows_of(extents)
        )
        assert spare_mm > 10.0, "this page is meant to have real slack in it"

        foot_mm = _mm(page.usable_bottom - page.tiles[-1].tile_bottom)
        assert foot_mm == pytest.approx(spare_mm, abs=PIXEL_MM)

    def test_the_short_row_sits_directly_under_the_heading_line(self) -> None:
        page = _page(SHORT_TOP_ROW_SIX_UP, 6, heading="Easy")

        assert page.heading is not None
        # The heading costs the tiles its 6 mm line plus one 2 mm tile gap.
        assert _mm(page.tiles[0].tile_top - page.usable_top) == pytest.approx(
            _reserved_mm(heading=True), abs=PIXEL_MM
        )
        assert page.tiles[0].tile_top >= page.usable_top + page.heading.height
        assert _mm(page.tiles[0].tile_bottom - page.tiles[0].tile_top) == pytest.approx(
            ANSWER_CAPTION_MM + 10 * ANSWER_MAX_CELL_MM, abs=PIXEL_MM
        )

    def test_every_row_stands_where_the_millimetres_say(self) -> None:
        """The whole vertical walk, row by row, against the arithmetic above."""
        page = _page(SHORT_TOP_ROW_SIX_UP, 6)

        tops = _row_tops_mm(SHORT_TOP_ROW_SIX_UP, 6, heading=False)
        for index, tile in enumerate(page.tiles):
            row = index // 2
            assert _mm(tile.tile_top - page.usable_top) == pytest.approx(
                tops[row], abs=PIXEL_MM
            )
            assert _mm(tile.tile_bottom - tile.tile_top) == pytest.approx(
                _row_height_mm(_rows_of(SHORT_TOP_ROW_SIX_UP)[row], 6, heading=False),
                abs=PIXEL_MM,
            )

    def test_a_page_of_one_short_answer_leaves_the_rest_of_the_page_white(self) -> None:
        page = _page([(10, 10)], 6)

        tile = page.tiles[0]
        assert _mm(tile.tile_bottom - tile.tile_top) == pytest.approx(
            ANSWER_CAPTION_MM + 10 * ANSWER_MAX_CELL_MM, abs=PIXEL_MM
        )
        assert _mm(page.usable_bottom - tile.tile_bottom) == pytest.approx(
            USABLE_HEIGHT_MM - (ANSWER_CAPTION_MM + 50.0), abs=PIXEL_MM
        )


class TestAnswerLayout_CellSizesAreUnchangedByRowPacking:
    """G-1/G-2: the cell is still the equal tile's, and knows nothing of its row.

    The four pinned figures again — 3.97 mm for a 20x20 six-up, 3.87 mm under a
    heading, 3.19 mm for a 30x30 four-up and the 5.0 mm cap on a 10x10 — and
    then the claim this card could have broken: an answer's cell does not
    depend on which answers share its row or its page, nor on which row it
    lands in. A cell that fell out of the row's own height would.
    """

    @pytest.mark.parametrize(
        ("extent", "capacity", "heading", "expected"),
        [
            ((20, 20), 6, None, 3.97),
            ((20, 20), 6, "Easy", 3.87),
            ((30, 30), 4, None, 3.19),
            ((10, 10), 6, None, 5.0),
            ((10, 10), 4, "Easy", 5.0),
        ],
    )
    def test_the_pinned_cells_are_what_they_were(
        self, extent: Extent, capacity: int, heading: str | None, expected: float
    ) -> None:
        page = _page([extent] * capacity, capacity, heading=heading)

        for tile in page.tiles:
            assert tile.cell_mm == pytest.approx(expected, abs=0.05)
            assert tile.cell_mm == pytest.approx(
                _cell_mm(extent, capacity, heading=heading is not None), abs=1e-9
            )

    @pytest.mark.parametrize("capacity", [4, 6])
    def test_an_answer_keeps_its_cell_whoever_shares_its_row(
        self, capacity: int
    ) -> None:
        alone = _page([(20, 20)], capacity).tiles[0].cell_mm
        beside_a_small_one = _page([(20, 20), (10, 10)], capacity).tiles[0].cell_mm
        on_a_full_page = _page([(20, 20)] * capacity, capacity).tiles[0].cell_mm

        assert alone == beside_a_small_one == on_a_full_page
        assert alone == pytest.approx(
            _cell_mm((20, 20), capacity, heading=False), abs=1e-9
        )

    @pytest.mark.parametrize("capacity", [4, 6])
    def test_an_answer_keeps_its_cell_wherever_it_lands_on_the_page(
        self, capacity: int
    ) -> None:
        """Including in the last row, which is the one the foot's slack is under."""
        cells = []
        for slot in range(capacity):
            extents: list[Extent] = [(10, 10)] * capacity
            extents[slot] = (20, 20)
            cells.append(_page(extents, capacity).tiles[slot].cell_mm)

        assert len(set(cells)) == 1
        assert cells[0] == pytest.approx(
            _cell_mm((20, 20), capacity, heading=False), abs=1e-9
        )

    def test_a_tall_neighbour_does_not_stretch_a_short_answer(self) -> None:
        """The row is as tall as its tallest grid; the short one is not enlarged."""
        page = _page([(10, 10), (20, 20)], 6)

        small, large = page.tiles
        assert small.cell_mm == ANSWER_MAX_CELL_MM
        assert _mm(small.grid_bottom - small.grid_top) == pytest.approx(
            10 * ANSWER_MAX_CELL_MM, abs=PIXEL_MM
        )
        assert small.tile_bottom == large.tile_bottom
        assert small.grid_bottom < large.grid_bottom


class TestAnswerLayout_UniformPageIsUnchangedAboveTheFoot:
    """A page whose answers are all one size reads exactly as it did.

    Every row holds the same content, so every row is the same height and the
    rows keep their even pitch; the horizontal geometry, the caption lines and
    the first row's top are where they always were. The one difference is at
    the bottom — and on a height-bound page (a 20x20 six-up, whose cell is the
    tile's own height fit) there is not even that: the layout is the equal-tile
    one to the pixel.
    """

    UNIFORM: list[tuple[Extent, int]] = [
        ((20, 20), 6),
        ((15, 15), 6),
        ((10, 10), 6),
        ((30, 30), 4),
        ((10, 10), 4),
    ]

    @pytest.mark.parametrize(("extent", "capacity"), UNIFORM)
    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_the_rows_are_one_height_at_an_even_pitch(
        self, extent: Extent, capacity: int, heading: str | None
    ) -> None:
        page = _page([extent] * capacity, capacity, heading=heading)
        expected = _row_height_mm([extent], capacity, heading=heading is not None)

        # One height, and one pitch, to within the rounding of a coordinate to
        # a whole device pixel.
        for tile in page.tiles:
            assert _mm(tile.tile_bottom - tile.tile_top) == pytest.approx(
                expected, abs=PIXEL_MM
            )
        for index in range(0, len(page.tiles) - 2, 2):
            assert _mm(
                page.tiles[index + 2].tile_top - page.tiles[index].tile_top
            ) == pytest.approx(expected + ANSWER_TILE_GAP_MM, abs=PIXEL_MM)

    @pytest.mark.parametrize(("extent", "capacity"), UNIFORM)
    @pytest.mark.parametrize("spec", [BOOK1_ODD, BOOK1_EVEN])
    def test_the_horizontal_geometry_and_the_first_row_are_untouched(
        self, extent: Extent, capacity: int, spec: PageSpec
    ) -> None:
        page = _page([extent] * capacity, capacity, spec)
        columns, rows = extent
        cell = _cell_mm(extent, capacity, heading=False)

        assert page.tiles[0].tile_top == page.usable_top
        for tile in page.tiles:
            column = tile.index % 2
            assert _mm(tile.tile_left - page.usable_left) == pytest.approx(
                column * (TILE_WIDTH_MM + ANSWER_TILE_GAP_MM), abs=PIXEL_MM
            )
            assert _mm(tile.tile_right - tile.tile_left) == pytest.approx(
                TILE_WIDTH_MM, abs=PIXEL_MM
            )
            # Still centred across its own column, and still hanging from its
            # caption line: neither is a vertical-placement decision.
            assert _mm(tile.grid_left - tile.tile_left) == pytest.approx(
                (TILE_WIDTH_MM - columns * cell) / 2, abs=PIXEL_MM
            )
            assert tile.caption_top == tile.tile_top
            assert _mm(tile.grid_top - tile.caption_top) == pytest.approx(
                ANSWER_CAPTION_MM, abs=PIXEL_MM
            )
            assert _mm(tile.grid_bottom - tile.grid_top) == pytest.approx(
                rows * cell, abs=PIXEL_MM
            )
            assert tile.fits

    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_a_height_bound_uniform_page_is_the_equal_tile_layout_itself(
        self, heading: str | None
    ) -> None:
        """A 20x20 six-up fills its measured tile, so nothing moves at all.

        Its cell *is* the tile's height fit, so the row's content height and
        the measured tile height are the same number: the tops, the bottoms
        and the foot are the pre-CARD-141 ones to within a rounding step.
        """
        headed = heading is not None
        page = _page([(20, 20)] * 6, 6, heading=heading)
        tile_height = _measured_tile_height_mm(6, heading=headed)

        assert _row_height_mm([(20, 20)], 6, heading=headed) == pytest.approx(
            tile_height, abs=1e-9
        )
        for tile in page.tiles:
            expected_top = _reserved_mm(heading=headed) + (tile.index // 2) * (
                tile_height + ANSWER_TILE_GAP_MM
            )
            assert _mm(tile.tile_top - page.usable_top) == pytest.approx(
                expected_top, abs=PIXEL_MM
            )
            assert _mm(tile.tile_bottom - tile.tile_top) == pytest.approx(
                tile_height, abs=PIXEL_MM
            )
        # The rows spend the whole usable height: there is no foot at all.
        assert _mm(page.usable_bottom - page.tiles[-1].tile_bottom) == pytest.approx(
            0.0, abs=PIXEL_MM
        )
