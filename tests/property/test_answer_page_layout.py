"""CARD-141: the answer page's vertical rule as a standing property (FR-042).

    New  PropertyTest_AnswerLayout_RowsNeverOverlapNorOverflow
        -> test_PropertyTest_AnswerLayout_RowsNeverOverlapNorOverflow
           (a seeded corpus of mixed pages: every capacity, both parities, with
           and without a heading, one answer to a full page)
        -> test_PropertyTest_AnswerLayout_RowsNeverOverlapNorOverflow_exhaustive
           (every pair of extents that can share a row, at both capacities)

The claim, for **any** mix of answers a page can be handed: no row overlaps the
next, no answer leaves the usable area, the only thing between two rows is
:data:`ANSWER_TILE_GAP_MM`, and whatever height the rows do not use is one band
at the foot of the page. The corpus deliberately runs over the whole supported
extent range (:data:`~nonogram.limits.MIN_SIZE`..``MAX_SIZE``) at both
capacities, not only the extents INV-011 admits: this property is geometry and
must hold even on a page the capacity rule would not have built. EC-031's cell
floor is the *other* property, swept by
``tests/property/test_book_answer_tiles.py`` over the extents INV-011 allows,
and nothing here asserts a floor.

How the expectation is independent: the expected cell and row height are
FR-042's definitions written out again here in floating-point millimetres over
CON-018's Book 1 literals — a measured tile of (193.675 − 2) / 2 by
(260.35 − heading − (rows − 1) × 2) / rows, a cell of min(5.0, tile width /
columns, (tile height − 6) / rows), and a row of 6 mm plus the tallest
``rows × cell`` standing on it — with no exact-fraction arithmetic, no pixel
rounding and none of ``layout``'s helpers. Overlap is re-derived here as a
rectangle intersection rather than read off the type.

No ``hypothesis`` (CLAUDE.md): stdlib ``random.Random`` at a fixed seed, with
the case counts asserted in the test itself.
"""

from __future__ import annotations

import dataclasses
import random
from collections.abc import Sequence

from nonogram.export.layout import (
    ANSWER_CAPTION_MM,
    ANSWER_HEADING_MM,
    ANSWER_MAX_CELL_MM,
    ANSWER_TILE_CAPACITIES,
    ANSWER_TILE_GAP_MM,
    AnswerPageLayout,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_answer_page_layout,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE

DPI = 300
PX_PER_MM = DPI / 25.4
PIXEL_MM = 1.0 / PX_PER_MM

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

# CON-018's Book 1 profile, as literals, for the expectations below.
USABLE_WIDTH_MM = 215.9 - 12.7 - 9.525
#: An answer page has no title band: the trim minus the two margins.
USABLE_HEIGHT_MM = 279.4 - 2 * 9.525
TILE_WIDTH_MM = (USABLE_WIDTH_MM - ANSWER_TILE_GAP_MM) / 2
TILE_COLUMNS = 2

Extent = tuple[int, int]


def _measured_tile_height_mm(capacity: int, *, heading: bool) -> float:
    """The equal tile the cell is fitted to — CARD-141 does not move it."""
    rows = capacity // TILE_COLUMNS
    reserved = (ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM) if heading else 0.0
    return (USABLE_HEIGHT_MM - reserved - (rows - 1) * ANSWER_TILE_GAP_MM) / rows


def _cell_mm(extent: Extent, capacity: int, *, heading: bool) -> float:
    columns, rows = extent
    return min(
        ANSWER_MAX_CELL_MM,
        TILE_WIDTH_MM / columns,
        (_measured_tile_height_mm(capacity, heading=heading) - ANSWER_CAPTION_MM) / rows,
    )


def _row_height_mm(row: Sequence[Extent], capacity: int, *, heading: bool) -> float:
    return ANSWER_CAPTION_MM + max(
        rows * _cell_mm((columns, rows), capacity, heading=heading)
        for columns, rows in row
    )


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _overlap(one, other) -> bool:
    """Do two tiles share any area? Touching edges do not count (re-derived here)."""
    return (
        one.tile_left < other.tile_right
        and other.tile_left < one.tile_right
        and one.tile_top < other.tile_bottom
        and other.tile_top < one.tile_bottom
    )


def _check_page(
    page: AnswerPageLayout,
    extents: Sequence[Extent],
    capacity: int,
    *,
    heading: bool,
) -> float:
    """The vertical rule on one page; returns the foot band's depth in mm."""
    rows = [
        list(page.tiles[start : start + TILE_COLUMNS])
        for start in range(0, len(page.tiles), TILE_COLUMNS)
    ]
    expected_rows = [
        list(extents[start : start + TILE_COLUMNS])
        for start in range(0, len(extents), TILE_COLUMNS)
    ]
    assert len(rows) == len(expected_rows)

    first_row_top = page.usable_top + (page.heading.height if page.heading else 0)
    # A heading costs the tiles its own line plus one tile gap; a page without
    # one starts its first row at the top of the usable area.
    reserved_mm = (ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM) if heading else 0.0
    assert abs(_mm(rows[0][0].tile_top - page.usable_top) - reserved_mm) <= PIXEL_MM
    assert rows[0][0].tile_top >= first_row_top

    for index, (row, members) in enumerate(zip(rows, expected_rows)):
        # A row is one band: its tiles begin and end together.
        assert {tile.tile_top for tile in row} == {row[0].tile_top}, index
        assert {tile.tile_bottom for tile in row} == {row[0].tile_bottom}, index
        # And it is exactly as tall as its content asks.
        expected_height = _row_height_mm(members, capacity, heading=heading)
        assert abs(_mm(row[0].tile_bottom - row[0].tile_top) - expected_height) <= PIXEL_MM
        # Never taller than the tile its cells were measured against, which is
        # what keeps the rows inside the page.
        assert (
            _mm(row[0].tile_bottom - row[0].tile_top)
            <= _measured_tile_height_mm(capacity, heading=heading) + PIXEL_MM
        )
        for tile, (columns, cells_down) in zip(row, members):
            assert (tile.columns, tile.rows) == (columns, cells_down)
            # The answer stays inside its own tile and inside the page.
            assert tile.fits
            assert tile.caption_top == tile.tile_top
            assert tile.grid_top == tile.caption_bottom
            assert page.usable_left <= tile.tile_left
            assert tile.tile_right <= page.usable_right
            assert first_row_top <= tile.tile_top
            assert tile.tile_bottom <= page.usable_bottom
            assert abs(
                _mm(tile.grid_bottom - tile.grid_top)
                - cells_down * _cell_mm((columns, cells_down), capacity, heading=heading)
            ) <= PIXEL_MM

    # Nothing but the tile gap between one row and the next.
    for above, below in zip(rows, rows[1:]):
        assert above[0].tile_bottom < below[0].tile_top
        assert abs(_mm(below[0].tile_top - above[0].tile_bottom) - ANSWER_TILE_GAP_MM) <= PIXEL_MM

    # No two tiles anywhere on the page share any area.
    for position, earlier in enumerate(page.tiles):
        for later in page.tiles[position + 1 :]:
            assert not _overlap(earlier, later), (earlier.index, later.index)

    foot_mm = _mm(page.usable_bottom - rows[-1][0].tile_bottom)
    assert foot_mm >= -PIXEL_MM
    return foot_mm


def _extents(capacity: int) -> list[Extent]:
    """Every extent the supported range holds — INV-011's rule is not applied."""
    return [
        (columns, rows)
        for columns in range(MIN_SIZE, MAX_SIZE + 1)
        for rows in range(MIN_SIZE, MAX_SIZE + 1)
    ]


def test_PropertyTest_AnswerLayout_RowsNeverOverlapNorOverflow() -> None:
    """For any mix of answers, on either parity, with or without a heading, and
    on a page filled from one answer to the capacity: each row is one band as
    tall as its own content, the only thing between two rows is the 2 mm tile
    gap, no two tiles overlap, no answer leaves the usable area, and the height
    the rows do not use is a single band at the foot of the page."""
    rng = random.Random(20260923141)
    pages = partial = mixed_rows = deep_foot = 0
    for _ in range(3000):
        capacity = rng.choice(ANSWER_TILE_CAPACITIES)
        spec = rng.choice((BOOK1_ODD, BOOK1_EVEN))
        heading = rng.choice((None, "Easy", "Medium", "Hard"))
        allowed = _extents(capacity)
        extents = [rng.choice(allowed) for _ in range(rng.randint(1, capacity))]

        page = compute_answer_page_layout(extents, capacity, spec, heading)

        foot_mm = _check_page(page, extents, capacity, heading=heading is not None)
        pages += 1
        partial += len(extents) < capacity
        mixed_rows += any(
            len({extents[start], extents[start + 1]}) == 2
            for start in range(0, len(extents) - 1, TILE_COLUMNS)
        )
        deep_foot += foot_mm > 20.0

    assert pages == 3000
    # The shapes the property is really about are all in the corpus.
    assert partial >= 600, partial
    assert mixed_rows >= 1500, mixed_rows
    assert deep_foot >= 500, deep_foot


def test_PropertyTest_AnswerLayout_RowsNeverOverlapNorOverflow_exhaustive() -> None:
    """The pairing that decides a row's height, swept: every square extent the
    range holds beside every other, at both capacities and under a heading."""
    squares = [(side, side) for side in range(MIN_SIZE, MAX_SIZE + 1)]
    checked = 0
    for capacity in ANSWER_TILE_CAPACITIES:
        for heading in (None, "Easy"):
            for left in squares:
                for right in squares:
                    extents = [left, right] * (capacity // TILE_COLUMNS)
                    page = compute_answer_page_layout(
                        extents, capacity, BOOK1_ODD, heading
                    )
                    _check_page(page, extents, capacity, heading=heading is not None)
                    # The taller of the pair sets the row, and the shorter one
                    # is not stretched to meet it.
                    row = page.tiles[:TILE_COLUMNS]
                    taller = max(row, key=lambda tile: tile.grid_bottom - tile.grid_top)
                    assert taller.grid_bottom <= taller.tile_bottom
                    assert abs(
                        _mm(taller.tile_bottom - taller.grid_bottom)
                    ) <= PIXEL_MM
                    checked += 1

    assert checked == len(ANSWER_TILE_CAPACITIES) * 2 * len(squares) ** 2
    assert checked >= 1_700, checked
