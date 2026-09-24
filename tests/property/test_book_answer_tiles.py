"""CARD-133: the answer page's standing property, over seeded corpora (FR-042).

    EC-031  PropertyTest_BookAnswerKey_CellAtLeast319AndTilesInsideUsableArea
        -> test_PropertyTest_BookAnswerKey_CellAtLeast319AndTilesInsideUsableArea
           (the exhaustive sweep: every extent 10..30 a side, every capacity,
           both parities, with and without a level heading, every tile position)
        -> test_PropertyTest_BookAnswerKey_CellAtLeast319AndTilesInsideUsableArea_mixed
           (the real shape of a page: different extents in one page's tiles, over
           a seeded random corpus)

How the expectation is independent
----------------------------------
The expected cell is FR-042's definition written out again here in
floating-point millimetres — min(5.0, tile width / columns, (tile height −
6) / rows) over a tile of (193.675 − 2) / 2 by (260.35 − heading − (rows − 1)
× 2) / rows — with no exact-fraction arithmetic, no pixel rounding and none of
``layout``'s helpers. The Book 1 numbers are literals, as CON-018 states them:
215.9 x 279.4 mm trim, 9.525 mm margins, a 12.7 mm gutter, and **no title
band** on an answer page.

Why the corpus pairs a capacity with an extent range
-----------------------------------------------------
EC-031's floor is 3.19 mm, and it holds because of INV-011, not by accident: a
six-up page holds nothing above 20 cells on its longest side, a four-up page up
to 30. The same Book 1 tile would print a 25x25 six-up at 3.18 mm and a 30x30
six-up at 2.65 mm, both under the floor. So the corpus offers a six-up page
only the answers INV-011 lets it hold — which is exactly the rule the caller
(CARD-134) applies — and the floor is then a real property of every page the
book can build, rather than of an arbitrary one. The tightest case in range is
a 30-wide answer four-up at 3.1946 mm, and it is asserted by name below so the
margin cannot silently erode.

No ``hypothesis`` (CLAUDE.md): stdlib ``random.Random`` at a fixed seed, each
test asserting its own minimum case counts and its own coverage of the sweep.
"""

from __future__ import annotations

import dataclasses
import random

from nonogram.export.layout import (
    ANSWER_CAPTION_MM,
    ANSWER_HEADING_MM,
    ANSWER_MAX_CELL_MM,
    ANSWER_TILE_CAPACITIES,
    ANSWER_TILE_GAP_MM,
    AnswerPageLayout,
    AnswerTile,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_answer_page_layout,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE

DPI = 300
PX_PER_MM = DPI / 25.4
PIXEL_MM = 1.0 / PX_PER_MM
BOOK_MIN_THIN_RULE_MM = 0.25
STANDARD_CELL_MM = 7.5

#: EC-031's range for an answer's cell, in millimetres.
ANSWER_FLOOR_MM = 3.19
#: INV-011: a six-up page holds nothing above this on its longest side.
SIX_UP_LONGEST_SIDE = 20

BOOK1_ODD = PageSpec(
    width_mm=215.9,
    height_mm=279.4,
    top_mm=9.525,
    bottom_mm=9.525,
    gutter_mm=12.7,
    outside_mm=9.525,
    band_mm=12.0,
    orientation=OrientationPolicy.PORTRAIT_ONLY,
    cell_cap=STANDARD_CELL_MM,
    min_thin_rule_mm=BOOK_MIN_THIN_RULE_MM,
    parity=PageParity.ODD,
)
BOOK1_EVEN = dataclasses.replace(BOOK1_ODD, parity=PageParity.EVEN)

# CON-018's Book 1 profile, as literals, for the expectations below.
TRIM_WIDTH_MM = 215.9
TRIM_HEIGHT_MM = 279.4
MARGIN_MM = 9.525
GUTTER_MM = 12.7
USABLE_WIDTH_MM = TRIM_WIDTH_MM - GUTTER_MM - MARGIN_MM
USABLE_HEIGHT_MM = TRIM_HEIGHT_MM - 2 * MARGIN_MM


def _expected_tile_mm(capacity: int, *, heading: bool) -> tuple[float, float]:
    """FR-042's tile, in millimetres, re-derived from the profile's own numbers."""
    rows = capacity // 2
    reserved = (ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM) if heading else 0.0
    return (
        (USABLE_WIDTH_MM - ANSWER_TILE_GAP_MM) / 2,
        (USABLE_HEIGHT_MM - reserved - (rows - 1) * ANSWER_TILE_GAP_MM) / rows,
    )


def _expected_cell_mm(
    extent: tuple[int, int], capacity: int, *, heading: bool
) -> float:
    """FR-042's answer cell for one extent on one kind of page."""
    columns, rows = extent
    tile_width, tile_height = _expected_tile_mm(capacity, heading=heading)
    return min(
        ANSWER_MAX_CELL_MM,
        tile_width / columns,
        (tile_height - ANSWER_CAPTION_MM) / rows,
    )


def _extents_for(capacity: int) -> list[tuple[int, int]]:
    """Every extent INV-011 lets a page of this capacity hold."""
    top = SIX_UP_LONGEST_SIDE if capacity == 6 else MAX_SIZE
    return [
        (columns, rows)
        for columns in range(MIN_SIZE, top + 1)
        for rows in range(MIN_SIZE, top + 1)
    ]


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _check_tile(
    page: AnswerPageLayout,
    tile: AnswerTile,
    spec: PageSpec,
    capacity: int,
    *,
    heading: bool,
) -> None:
    """EC-031, on one tile of one page.

    The cell is in [3.19, 5.0] mm and is FR-042's own number; the grid and the
    6 mm caption line lie inside the tile; the tile lies inside the usable
    area, below the heading line when there is one.
    """
    expected = _expected_cell_mm((tile.columns, tile.rows), capacity, heading=heading)
    assert abs(tile.cell_mm - expected) < 1e-9, (capacity, heading, tile.columns, tile.rows)
    assert ANSWER_FLOOR_MM <= tile.cell_mm <= ANSWER_MAX_CELL_MM, tile

    # The grid and the caption line lie inside the tile.
    assert tile.fits, tile
    assert tile.caption_top == tile.tile_top
    assert abs(_mm(tile.caption_bottom - tile.caption_top) - ANSWER_CAPTION_MM) <= PIXEL_MM
    assert tile.grid_top == tile.caption_bottom
    assert len(tile.vertical_lines) == tile.columns + 1
    assert len(tile.horizontal_lines) == tile.rows + 1
    assert tile.column_boundaries[0] == tile.grid_left
    assert tile.row_boundaries[-1] == tile.grid_bottom
    # The grid really is the cell it reports, to within the one rounding step.
    assert abs(_mm(tile.grid_right - tile.grid_left) - tile.columns * tile.cell_mm) <= PIXEL_MM
    assert abs(_mm(tile.grid_bottom - tile.grid_top) - tile.rows * tile.cell_mm) <= PIXEL_MM

    # ADR-0037/R2 holds on an answer tile too.
    assert _mm(tile.thin_rule) >= BOOK_MIN_THIN_RULE_MM
    assert tile.thick_rule == 2 * tile.thin_rule

    # The tile lies inside the usable area, below the heading line.
    first_row_top = page.usable_top + (page.heading.height if page.heading else 0)
    assert page.usable_left <= tile.tile_left
    assert tile.tile_right <= page.usable_right
    assert first_row_top <= tile.tile_top
    assert tile.tile_bottom <= page.usable_bottom

    # The tile is the size FR-042 says, and the page is the trim. Across, that
    # is the measured tile itself; down, it is the row's own content — the
    # caption line plus the tallest grid sharing the row (CARD-141) — which is
    # never taller than the measured tile the cell was fitted to.
    tile_width_mm, tile_height_mm = _expected_tile_mm(capacity, heading=heading)
    assert abs(_mm(tile.tile_right - tile.tile_left) - tile_width_mm) <= PIXEL_MM
    row_height_mm = ANSWER_CAPTION_MM + max(
        other.rows
        * _expected_cell_mm((other.columns, other.rows), capacity, heading=heading)
        for other in page.tiles
        if other.index // page.tile_columns == tile.index // page.tile_columns
    )
    assert abs(_mm(tile.tile_bottom - tile.tile_top) - row_height_mm) <= PIXEL_MM
    assert _mm(tile.tile_bottom - tile.tile_top) <= tile_height_mm + PIXEL_MM
    assert page.parity is spec.parity


def _check_page(
    page: AnswerPageLayout, spec: PageSpec, capacity: int, *, heading: bool
) -> int:
    """EC-031 over a whole page; returns how many tiles it checked."""
    assert page.capacity == capacity
    assert page.tile_columns * page.tile_rows == capacity
    assert abs(_mm(page.width) - TRIM_WIDTH_MM) <= PIXEL_MM
    assert abs(_mm(page.height) - TRIM_HEIGHT_MM) <= PIXEL_MM
    assert abs(_mm(page.usable_bottom - page.usable_top) - USABLE_HEIGHT_MM) <= PIXEL_MM
    assert abs(_mm(page.usable_right - page.usable_left) - USABLE_WIDTH_MM) <= PIXEL_MM

    if heading:
        assert page.heading is not None
        assert abs(_mm(page.heading.height) - ANSWER_HEADING_MM) <= PIXEL_MM
        assert page.heading.center_y - page.heading.height // 2 >= page.usable_top
        assert page.heading.font_size <= page.heading.height
    else:
        assert page.heading is None

    for tile in page.tiles:
        _check_tile(page, tile, spec, capacity, heading=heading)

    # No two tiles overlap.
    for position, earlier in enumerate(page.tiles):
        for later in page.tiles[position + 1 :]:
            assert not (
                earlier.tile_left < later.tile_right
                and later.tile_left < earlier.tile_right
                and earlier.tile_top < later.tile_bottom
                and later.tile_top < earlier.tile_bottom
            ), (earlier, later)
    return len(page.tiles)


def test_PropertyTest_BookAnswerKey_CellAtLeast319AndTilesInsideUsableArea() -> None:
    """EC-031: for every answer extent INV-011 lets a page hold, on either parity,
    with and without a level heading, at every tile position, the cell is in
    [3.19, 5.0] mm and is FR-042's number, the grid and its 6 mm caption line lie
    inside the tile, and every tile lies inside the usable area without
    overlapping another."""
    checked = 0
    seen: dict[int, set[tuple[int, int]]] = {4: set(), 6: set()}
    positions: set[tuple[int, int]] = set()
    for capacity in ANSWER_TILE_CAPACITIES:
        for spec in (BOOK1_ODD, BOOK1_EVEN):
            for heading in (None, "Easy"):
                for extent in _extents_for(capacity):
                    page = compute_answer_page_layout(
                        [extent] * capacity, capacity, spec, heading
                    )
                    checked += _check_page(
                        page, spec, capacity, heading=heading is not None
                    )
                    seen[capacity].add(extent)
                    positions.update((capacity, tile.index) for tile in page.tiles)

    # The sweep really is exhaustive: every extent INV-011 allows, every slot.
    assert seen[6] == set(_extents_for(6)) and len(seen[6]) == 121
    assert seen[4] == set(_extents_for(4)) and len(seen[4]) == 441
    assert positions == {(6, index) for index in range(6)} | {
        (4, index) for index in range(4)
    }
    assert checked >= 9_900, checked

    # The tightest case in the whole range, by name: a 30-wide answer four-up.
    tightest = compute_answer_page_layout([(30, 30)], 4, BOOK1_ODD, "Hard")
    assert abs(tightest.tiles[0].cell_mm - (USABLE_WIDTH_MM - ANSWER_TILE_GAP_MM) / 2 / 30) < 1e-9
    assert ANSWER_FLOOR_MM <= tightest.tiles[0].cell_mm < ANSWER_FLOOR_MM + 0.01


def test_PropertyTest_BookAnswerKey_CellAtLeast319AndTilesInsideUsableArea_mixed() -> None:
    """EC-031 on the page shape the book actually produces: a page whose tiles hold
    different answers, and a last page of a level that is only partly filled."""
    rng = random.Random(20260922133)
    checked = pages = partial = 0
    capped = floored = 0
    for _ in range(2000):
        capacity = rng.choice(ANSWER_TILE_CAPACITIES)
        spec = rng.choice((BOOK1_ODD, BOOK1_EVEN))
        heading = rng.choice((None, "Easy", "Medium", "Hard"))
        allowed = _extents_for(capacity)
        extents = [rng.choice(allowed) for _ in range(rng.randint(1, capacity))]

        page = compute_answer_page_layout(extents, capacity, spec, heading)

        assert [(tile.columns, tile.rows) for tile in page.tiles] == extents
        assert [tile.index for tile in page.tiles] == list(range(len(extents)))
        checked += _check_page(page, spec, capacity, heading=heading is not None)
        pages += 1
        partial += len(extents) < capacity
        capped += any(tile.cell_mm == ANSWER_MAX_CELL_MM for tile in page.tiles)
        floored += any(tile.cell_mm < 3.3 for tile in page.tiles)

    assert pages == 2000
    assert checked >= 5_000, checked
    # Both ends of the range are really exercised, not just the comfortable middle.
    assert capped >= 200, capped
    assert floored >= 100, floored
    assert partial >= 400, partial
