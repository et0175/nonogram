"""CARD-133: the packed answer key's tile geometry, at layout level (FR-042).

    AC-262  TestBookAnswerKey_TwentyInSixUpTileCellSize
    AC-265  TestBookAnswerKey_ThirtyInFourUpTileCellSize
    AC-267  TestBookAnswerKey_AnswerDrawsGridOnlyNoClues
    AC-294  TestBookAnswerKey_SmallAnswerCellCappedAtFiveMm
    AC-295  TestBookAnswerKey_HeadingPageTwentyInSixUpTileCellSize
    The call's contract: TestAnswerPage_RefusesSpecsThatHaveNoAnswerTiles,
            TestAnswerPage_RefusesMalformedPages, TestAnswerPage_TileGeometry,
            TestAnswerPage_ValueObjectRefusesAnInvalidPage

These are the layout-level halves of FR-042's criteria; CARD-134 re-asserts
them on the book PDF. EC-031's standing property is in
``tests/property/test_book_answer_tiles.py``.

Every expected cell is worked out here from FR-042's own definition, in
millimetres, as a literal: Book 1's usable width is 215.9 − 12.7 − 9.525 =
193.675 mm and its answer-page usable height — no title band — is
279.4 − 2 × 9.525 = 260.35 mm. A tile is (193.675 − 2) / 2 mm wide and
(260.35 − heading − (rows − 1) × 2) / rows tall, where ``heading`` is 6 + 2 mm
on a page carrying a level heading and 0 otherwise. The cell is
min(5.0, tile width / columns, (tile height − 6) / rows). Nothing is asked of
``layout``'s helpers.

A note on AC-295's two readings: the card's prose quotes an 83.45 mm six-up
tile under a heading, which reserves only the 6 mm heading line; the card's
*formula* reserves the line plus the 2 mm gap (8 mm) and gives 82.78 mm. The
formula is implemented, and both readings land inside AC-295's stated
3.87 +/- 0.05 mm — see the card's worktree notes.
"""

from __future__ import annotations

import dataclasses

import pytest

from nonogram.clues import compute_clues
from nonogram.export.layout import (
    ANSWER_CAPTION_MM,
    ANSWER_HEADING_MM,
    ANSWER_MAX_CELL_MM,
    ANSWER_TILE_GAP_MM,
    DEFAULT_PAGE_SPEC,
    DPI,
    AnswerPageLayout,
    CellCapPolicy,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_answer_page_layout,
)
from nonogram.export.png import render_answer_page

#: CON-018's Book 1 profile (the same literal as tests/test_layout_two_up.py;
#: ``export`` tests never import the admin-side builder).
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

BOOK1_USABLE_WIDTH_MM = 193.675
#: No title band on an answer page: the trim minus the top and bottom margins.
BOOK1_ANSWER_HEIGHT_MM = 260.35
TILE_WIDTH_MM = (BOOK1_USABLE_WIDTH_MM - 2.0) / 2
PX_PER_MM = DPI / 25.4
HALF_PIXEL_MM = 0.5 / PX_PER_MM
#: One device pixel in millimetres. Every measurement below is a difference of
#: coordinates that were each rounded to a whole pixel, so a millimetre figure
#: is exact only to within a pixel — 0.085 mm at 300 DPI.
PIXEL_MM = 1.0 / PX_PER_MM


def _tile_height_mm(capacity: int, *, heading: bool) -> float:
    """FR-042's tile height on the Book 1 profile, written out again here."""
    rows = capacity // 2
    reserved = (6.0 + 2.0) if heading else 0.0
    return (BOOK1_ANSWER_HEIGHT_MM - reserved - (rows - 1) * 2.0) / rows


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _page(
    extents: list[tuple[int, int]],
    capacity: int,
    spec: PageSpec = BOOK1_ODD,
    heading: str | None = None,
) -> AnswerPageLayout:
    return compute_answer_page_layout(extents, capacity, spec, heading)


def _grid(columns: int, rows: int) -> list[list[bool]]:
    """A grid whose every row and column holds at least one run and one gap.

    ``(row + column) % 3 != 0`` gives a pattern with real runs in both
    directions at any extent 10 or more, so its clues are never ``(0,)``.
    """
    return [[(row + column) % 3 != 0 for column in range(columns)] for row in range(rows)]


class TestBookAnswerKey_TwentyInSixUpTileCellSize:
    """AC-262: a 20x20 on a six-up page with no heading prints at 3.97 mm.

    79.45 mm of tile grid area (85.45 mm tile − the 6 mm caption line) over 20
    rows. The width term (95.84 / 20 = 4.79 mm) and the 5 mm cap are both
    looser, so the height term is the one that binds.
    """

    def test_the_cell_is_the_tile_height_fit(self) -> None:
        assert _tile_height_mm(6, heading=False) == pytest.approx(85.45, abs=0.005)

        page = _page([(20, 20)] * 6, 6)

        for tile in page.tiles:
            assert tile.cell_mm == pytest.approx(3.97, abs=0.05)
            assert tile.cell_mm == pytest.approx(
                (_tile_height_mm(6, heading=False) - 6.0) / 20, abs=1e-9
            )

    def test_it_is_the_same_cell_on_either_parity(self) -> None:
        odd = _page([(20, 20)] * 6, 6, BOOK1_ODD)
        even = _page([(20, 20)] * 6, 6, BOOK1_EVEN)

        assert [tile.cell_mm for tile in odd.tiles] == [tile.cell_mm for tile in even.tiles]
        assert _mm(odd.usable_right - odd.usable_left) == pytest.approx(
            _mm(even.usable_right - even.usable_left), abs=PIXEL_MM
        )
        # Parity moves the usable area sideways by gutter − outside, never its size.
        assert _mm(odd.usable_left - even.usable_left) == pytest.approx(
            12.7 - 9.525, abs=PIXEL_MM
        )


class TestBookAnswerKey_ThirtyInFourUpTileCellSize:
    """AC-265: a 30x30 on a four-up page prints at 3.19 mm — the *width* term.

    95.84 mm of tile width over 30 columns. The four-up tile is 129.18 mm tall,
    so its grid area over 30 rows would allow 4.11 mm; the narrow side decides.
    """

    def test_the_cell_is_the_tile_width_fit(self) -> None:
        assert _tile_height_mm(4, heading=False) == pytest.approx(129.18, abs=0.005)

        page = _page([(30, 30)] * 4, 4)

        for tile in page.tiles:
            assert tile.cell_mm == pytest.approx(3.19, abs=0.05)
            assert tile.cell_mm == pytest.approx(TILE_WIDTH_MM / 30, abs=1e-9)

    def test_a_heading_does_not_move_a_width_bound_answer(self) -> None:
        under_heading = _page([(30, 30)] * 4, 4, heading="Hard")

        assert under_heading.tiles[0].cell_mm == pytest.approx(TILE_WIDTH_MM / 30, abs=1e-9)


class TestBookAnswerKey_SmallAnswerCellCappedAtFiveMm:
    """AC-294: a 10x10 on a six-up page prints at the 5 mm cap, not at 7.94 mm."""

    def test_the_cell_is_the_answer_cap(self) -> None:
        tile_fit = (_tile_height_mm(6, heading=False) - 6.0) / 10
        assert tile_fit == pytest.approx(7.94, abs=0.005)

        page = _page([(10, 10)] * 6, 6)

        for tile in page.tiles:
            assert tile.cell_mm == pytest.approx(5.0, abs=0.05)
            assert tile.cell_mm == ANSWER_MAX_CELL_MM

    @pytest.mark.parametrize(
        ("extent", "capped"),
        [((10, 10), True), ((15, 15), True), ((16, 16), False), ((20, 20), False)],
    )
    def test_the_cap_binds_up_to_fifteen_a_side(
        self, extent: tuple[int, int], capped: bool
    ) -> None:
        tile = _page([extent], 6).tiles[0]

        assert (tile.cell_mm == ANSWER_MAX_CELL_MM) is capped
        assert tile.cell_mm <= ANSWER_MAX_CELL_MM


class TestBookAnswerKey_HeadingPageTwentyInSixUpTileCellSize:
    """AC-295: a 20x20 on the first six-up page of a level — under the heading.

    The heading line costs the tile rows 6 mm of heading plus the same 2 mm gap
    that separates two tile rows, so the tile is 82.78 mm tall, its grid area
    76.78 mm, and the cell 3.84 mm — inside AC-295's 3.87 +/- 0.05 mm. (The
    card's prose quotes the 6 mm-only reading, 3.87 mm; both pass, and the
    formula is what is implemented. See the module docstring.)
    """

    def test_the_cell_is_the_tile_height_fit_under_the_heading(self) -> None:
        page = _page([(20, 20)] * 6, 6, heading="Easy")

        for tile in page.tiles:
            assert tile.cell_mm == pytest.approx(3.87, abs=0.05)
            assert tile.cell_mm == pytest.approx(
                (_tile_height_mm(6, heading=True) - 6.0) / 20, abs=1e-9
            )

    def test_the_heading_costs_the_tiles_exactly_its_line_and_one_gap(self) -> None:
        plain = _page([(20, 20)] * 6, 6)
        titled = _page([(20, 20)] * 6, 6, heading="Easy")

        lost_mm = _mm(
            (plain.tiles[0].tile_bottom - plain.tiles[0].tile_top)
            - (titled.tiles[0].tile_bottom - titled.tiles[0].tile_top)
        )
        assert lost_mm == pytest.approx(
            (ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM) / 3, abs=PIXEL_MM
        )

    def test_the_heading_line_sits_at_the_top_of_the_usable_area(self) -> None:
        titled = _page([(20, 20)] * 6, 6, heading="Easy")

        assert titled.heading is not None
        assert _mm(titled.heading.height) == pytest.approx(ANSWER_HEADING_MM, abs=PIXEL_MM)
        top = titled.heading.center_y - titled.heading.height // 2
        assert top == titled.usable_top
        assert titled.tiles[0].tile_top >= titled.usable_top + titled.heading.height
        assert _page([(20, 20)], 6).heading is None


class TestBookAnswerKey_AnswerDrawsGridOnlyNoClues:
    """AC-267: a rendered 15x15 answer tile is the filled grid and nothing else.

    "No clue number" is asserted structurally rather than by reading digits: on
    a page holding one answer with an empty caption, *every* inked pixel must
    lie inside the answer's own grid rectangle (widened by half a heavy rule).
    A row-clue gutter would put ink to the left of ``grid_left`` and a column
    gutter above ``grid_top``, so this fails on any clue the renderer might
    draw, wherever it drew it.
    """

    def test_the_tile_draws_the_filled_grid_and_no_clue(self) -> None:
        grid = _grid(15, 15)
        row_clues, column_clues = compute_clues(grid)
        assert all(clue != (0,) for clue in row_clues + column_clues)

        image = render_answer_page([(grid, "")], 6, BOOK1_ODD)
        tile = _page([(15, 15)], 6).tiles[0]

        # Every filled cell is inked and every empty one is not.
        pixels = image.load()
        assert pixels is not None
        xs, ys = tile.column_boundaries, tile.row_boundaries
        for row in range(15):
            for column in range(15):
                centre = (
                    (xs[column] + xs[column + 1]) // 2,
                    (ys[row] + ys[row + 1]) // 2,
                )
                assert (pixels[centre] == (0, 0, 0)) is grid[row][column], (row, column)

        # And no ink anywhere outside that grid: no clue numbers, no gutters.
        ink = image.convert("L").point(lambda value: 255 if value < 128 else 0).getbbox()
        assert ink is not None
        slack = tile.thick_rule
        assert ink[0] >= tile.grid_left - slack
        assert ink[1] >= tile.grid_top - slack
        assert ink[2] <= tile.grid_right + slack + 1
        assert ink[3] <= tile.grid_bottom + slack + 1

    def test_the_caption_and_heading_are_the_only_other_ink(self) -> None:
        grid = _grid(15, 15)

        image = render_answer_page([(grid, "Puzzle 1")], 6, BOOK1_ODD, heading="Easy")
        page = _page([(15, 15)], 6, heading="Easy")
        tile = page.tiles[0]

        # The caption prints on its own line, above the grid and inside the tile.
        caption = image.crop(
            (tile.tile_left, tile.caption_top, tile.tile_right, tile.caption_bottom)
        )
        assert caption.convert("L").point(lambda value: 255 if value < 128 else 0).getbbox()
        assert tile.caption_bottom <= tile.grid_top

        # The strip left of the grid, below the caption, stays white: still no gutter.
        assert page.heading is not None
        gutter = image.crop(
            (tile.tile_left, tile.grid_top, tile.grid_left - tile.thick_rule, tile.tile_bottom)
        )
        assert gutter.convert("L").point(lambda value: 255 if value < 128 else 0).getbbox() is None


class TestAnswerPage_TileGeometry:
    """The page a caller gets: two columns, the fill order, and the reserved lines."""

    @pytest.mark.parametrize(("capacity", "tile_rows"), [(6, 3), (4, 2)])
    def test_the_page_is_two_tiles_across(self, capacity: int, tile_rows: int) -> None:
        page = _page([(15, 15)] * capacity, capacity)

        assert (page.capacity, page.tile_columns, page.tile_rows) == (
            capacity,
            2,
            tile_rows,
        )
        assert len(page.tiles) == capacity
        assert _mm(page.tiles[0].tile_right - page.tiles[0].tile_left) == pytest.approx(
            TILE_WIDTH_MM, abs=PIXEL_MM
        )
        # CARD-141: a tile is as tall as its row's content — the caption line
        # plus the tallest grid in the row — not as tall as the equal tile the
        # cell was measured against. A 15x15 is cap-bound (the AC-294 case
        # above), so every row here is 6 + 15 x 5 = 81 mm and the height the
        # rows do not use falls at the foot of the page.
        assert page.tiles[0].cell_mm == ANSWER_MAX_CELL_MM
        assert _mm(
            page.tiles[0].tile_bottom - page.tiles[0].tile_top
        ) == pytest.approx(ANSWER_CAPTION_MM + 15 * ANSWER_MAX_CELL_MM, abs=PIXEL_MM)
        assert _tile_height_mm(capacity, heading=False) > 81.0

    def test_tiles_fill_left_to_right_then_top_to_bottom(self) -> None:
        page = _page([(15, 15)] * 6, 6)

        assert page.tiles[0].tile_top == page.tiles[1].tile_top
        assert page.tiles[0].tile_left < page.tiles[1].tile_left
        assert page.tiles[1].tile_bottom <= page.tiles[2].tile_top
        assert [tile.index for tile in page.tiles] == [0, 1, 2, 3, 4, 5]
        # The 2 mm gap, both ways.
        assert _mm(page.tiles[1].tile_left - page.tiles[0].tile_right) == pytest.approx(
            ANSWER_TILE_GAP_MM, abs=PIXEL_MM
        )
        assert _mm(page.tiles[2].tile_top - page.tiles[0].tile_bottom) == pytest.approx(
            ANSWER_TILE_GAP_MM, abs=PIXEL_MM
        )

    def test_a_half_filled_page_keeps_its_capacity_tile_size(self) -> None:
        full = _page([(15, 15)] * 6, 6)
        partial = _page([(15, 15)] * 2, 6)

        assert len(partial.tiles) == 2
        assert partial.tiles[0].tile_bottom == full.tiles[0].tile_bottom
        assert partial.tiles[1].tile_left == full.tiles[1].tile_left

    def test_each_tile_reserves_its_caption_line_above_the_grid(self) -> None:
        tile = _page([(20, 20)] * 6, 6).tiles[0]

        assert tile.caption_top == tile.tile_top
        assert _mm(tile.caption_bottom - tile.caption_top) == pytest.approx(
            ANSWER_CAPTION_MM, abs=PIXEL_MM
        )
        assert tile.grid_top == tile.caption_bottom
        assert tile.caption_center_x == (tile.tile_left + tile.tile_right) // 2
        assert tile.fits

    def test_the_grid_is_centred_across_its_tile_and_ruled_every_fifth_line(self) -> None:
        tile = _page([(10, 10)] * 6, 6).tiles[0]

        assert (tile.grid_left - tile.tile_left) == pytest.approx(
            tile.tile_right - tile.grid_right, abs=1
        )
        assert len(tile.vertical_lines) == 11
        assert len(tile.horizontal_lines) == 11
        assert [line.index for line in tile.vertical_lines if line.major] == [0, 5, 10]
        assert tile.column_boundaries == tuple(
            line.position for line in tile.vertical_lines
        )
        # ADR-0037/R2: at least 0.25 mm thin, heavy exactly twice it.
        assert _mm(tile.thin_rule) >= 0.25
        assert tile.thick_rule == 2 * tile.thin_rule

    def test_the_page_is_the_trim_and_carries_its_parity(self) -> None:
        page = _page([(15, 15)], 4, BOOK1_EVEN)

        assert page.parity is PageParity.EVEN
        assert _mm(page.width) == pytest.approx(215.9, abs=HALF_PIXEL_MM + 1e-9)
        assert _mm(page.height) == pytest.approx(279.4, abs=HALF_PIXEL_MM + 1e-9)
        assert _mm(page.usable_top) == pytest.approx(9.525, abs=HALF_PIXEL_MM + 1e-9)
        assert _mm(page.usable_bottom) == pytest.approx(
            279.4 - 9.525, abs=HALF_PIXEL_MM + 1e-9
        )
        # An answer page has no title band: the tiles have the whole height.
        assert _mm(page.usable_bottom - page.usable_top) == pytest.approx(
            BOOK1_ANSWER_HEIGHT_MM, abs=PIXEL_MM
        )


class TestAnswerPage_RefusesSpecsThatHaveNoAnswerTiles:
    """The default A4 sheet has no answer tiles, and neither has a comfort-cap spec."""

    def test_the_default_spec_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no answer tiles"):
            compute_answer_page_layout([(15, 15)], 6, DEFAULT_PAGE_SPEC)

    def test_a_spec_without_a_flat_cap_is_refused(self) -> None:
        curved = dataclasses.replace(BOOK1_ODD, cell_cap=CellCapPolicy.COMFORT_CURVE)

        with pytest.raises(ValueError, match="no answer tiles"):
            compute_answer_page_layout([(15, 15)], 6, curved)

    def test_a_non_spec_is_a_type_error(self) -> None:
        with pytest.raises(TypeError, match="PageSpec"):
            compute_answer_page_layout([(15, 15)], 6, "Book 1")  # type: ignore[arg-type]


class TestAnswerPage_RefusesMalformedPages:
    """Capacities, counts and extents FR-042 does not define."""

    @pytest.mark.parametrize("capacity", [0, 1, 2, 3, 5, 7, 8, 12])
    def test_only_four_and_six_are_capacities(self, capacity: int) -> None:
        with pytest.raises(ValueError, match="4 or 6"):
            compute_answer_page_layout([(15, 15)], capacity, BOOK1_ODD)

    def test_an_empty_page_is_refused(self) -> None:
        with pytest.raises(ValueError, match="at least one answer"):
            compute_answer_page_layout([], 6, BOOK1_ODD)

    def test_more_answers_than_the_capacity_is_refused(self) -> None:
        with pytest.raises(ValueError, match="holds 4"):
            compute_answer_page_layout([(15, 15)] * 5, 4, BOOK1_ODD)

    @pytest.mark.parametrize(
        "extent", [(0, 10), (10, 0), (-1, 10), (10.5, 10), (10,), (10, 10, 10), "1010"]
    )
    def test_an_extent_that_is_not_a_pair_of_cell_counts_is_refused(
        self, extent: object
    ) -> None:
        with pytest.raises(ValueError, match="answer 0"):
            compute_answer_page_layout([extent], 6, BOOK1_ODD)  # type: ignore[list-item]

    def test_a_page_too_short_for_its_caption_lines_is_refused(self) -> None:
        stunted = dataclasses.replace(BOOK1_ODD, height_mm=40.0)

        with pytest.raises(ValueError, match="caption lines"):
            compute_answer_page_layout([(15, 15)], 6, stunted)

    def test_a_ragged_answer_grid_is_refused_by_the_renderer(self) -> None:
        ragged = [[True] * 15, [True] * 14]

        with pytest.raises(ValueError, match="rectangular"):
            render_answer_page([(ragged, "")], 6, BOOK1_ODD)


class TestAnswerPage_ValueObjectRefusesAnInvalidPage:
    """EC-031 is a property of the type: an overlapping or oversized page cannot exist."""

    def test_overlapping_tiles_are_refused(self) -> None:
        page = _page([(15, 15)] * 6, 6)
        # The same tile twice: each one fits its own bounds, and together they
        # are the one thing a page may not do.
        collided = dataclasses.replace(page.tiles[0], index=1)

        with pytest.raises(ValueError, match="overlapping"):
            dataclasses.replace(page, tiles=(page.tiles[0], collided))

    def test_a_tile_outside_the_usable_area_is_refused(self) -> None:
        page = _page([(15, 15)] * 4, 4)
        shrunk = page.tiles[0].tile_bottom - 1

        with pytest.raises(ValueError, match="inside the usable area"):
            dataclasses.replace(page, tiles=(page.tiles[0],), usable_bottom=shrunk)

    def test_a_grid_outside_its_own_tile_is_refused(self) -> None:
        page = _page([(15, 15)] * 4, 4)
        spilled = dataclasses.replace(page.tiles[0], grid_bottom=page.tiles[0].tile_bottom + 1)

        with pytest.raises(ValueError, match="inside its own tile"):
            dataclasses.replace(page, tiles=(spilled,))

    def test_a_cell_above_the_answer_cap_is_refused(self) -> None:
        page = _page([(15, 15)] * 4, 4)
        fat = dataclasses.replace(page.tiles[0], cell_mm=ANSWER_MAX_CELL_MM + 0.1)

        with pytest.raises(ValueError, match="answer cap"):
            dataclasses.replace(page, tiles=(fat,))

    def test_a_capacity_that_is_not_two_columns_of_tiles_is_refused(self) -> None:
        page = _page([(15, 15)] * 4, 4)

        with pytest.raises(ValueError, match="tiles"):
            dataclasses.replace(page, tile_rows=3)
