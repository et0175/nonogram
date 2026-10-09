"""CARD-202 review F-1 (fix cycle 1): ``compute_packed_solved_layout`` declines

rather than silently overlapping two different puzzles' ink, at layout level.

The reviewer reproduced the bug directly against the real production code: on
a valid KDP-minimum 10cm x 10cm book trim, four qualifying small answers
(width<=15, height<=20) with realistic deep clue gutters computed a shared
cell floored at ``MIN_CELL_MM``, with every slot's drawing overflowing its own
tile by far more than the 4mm inter-tile gap — one puzzle's ink spilling into
a neighbour's tile, unprintable, and nothing in the old code aborted, warned
or fell back.

These tests pin the fix directly on :func:`~nonogram.export.layout.compute_packed_solved_layout`:
it now returns ``None`` — the same "decline below the minimum" contract
:func:`~nonogram.export.layout.compute_pair_layout` already has for a pair —
whenever the shared cell every member needs would fall below
:data:`~nonogram.export.layout.MIN_CELL_MM`, instead of flooring the cell up
and letting a slot's drawing spill past its own tile.

    TestPackedSolvedLayout_FourUpDeclinesOnTheKdpMinimumTrim
    TestPackedSolvedLayout_TheSameAnswersPackTwoUpInstead
    TestPackedSolvedLayout_EvenTwoUpDeclinesWhenTheGuttersAreDeepEnough
    TestPackedSolvedLayout_EverySurvivingSlotActuallyFitsItsOwnTile

The end-to-end proof that a real book with this shape still exports, with no
two slots' drawing extents overlapping, is
``tests/test_book_solved_answer_key.py::TestBookSolvedAnswerKey_InfeasiblePackedPagesDegradeGracefully``
(review F-1's integration half).
"""

from __future__ import annotations

import dataclasses

import pytest

from nonogram.export.layout import (
    DPI,
    MIN_CELL_MM,
    OrientationPolicy,
    PageParity,
    PageSpec,
    PackedSolvedLayout,
    compute_packed_solved_layout,
)

type Puzzle = tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]


def _puzzle(columns: int, rows: int, *, row_depth: int, column_depth: int) -> Puzzle:
    """A ``columns`` x ``rows`` puzzle whose gutters are exactly that deep.

    The same synthetic builder ``tests/test_layout_two_up.py`` uses: a literal
    clue set, not a grid, so the geometry formula is exercised directly and
    the depth asked for is exact rather than whatever a real grid happens to
    produce.
    """
    return (
        tuple((1,) * row_depth for _ in range(rows)),
        tuple((1,) * column_depth for _ in range(columns)),
    )


#: A valid KDP-minimum book trim (``book_page_spec.MIN_TRIM_CM`` is 10.0 cm),
#: at the minimum side margin KDP allows (``MIN_SIDE_MARGIN_MM`` 6.35 mm) and
#: the Book 1 profile's fixed top/bottom (9.525 mm) and title band (12.0 mm) —
#: exactly the trim the reviewer reproduced F-1 against.
KDP_MIN_ODD = PageSpec(
    width_mm=100.0,
    height_mm=100.0,
    top_mm=9.525,
    bottom_mm=9.525,
    gutter_mm=6.35,
    outside_mm=6.35,
    band_mm=12.0,
    orientation=OrientationPolicy.PORTRAIT_ONLY,
    cell_cap=7.5,
    min_thin_rule_mm=0.25,
    parity=PageParity.ODD,
)

#: The four qualifying small answers the review reproduced F-1 with: all
#: width<=15 and height<=20 (CARD-202's packing threshold), heights
#: 10/15/18/20, each with a 5-deep clue gutter on both axes — deep enough
#: that every one of the four fails the 4-up tile's drawing-height fit on
#: this trim, but shallow enough that a 2-up tile (double the height) still
#: clears it.
_ANSWERS = (
    _puzzle(15, 10, row_depth=5, column_depth=5),
    _puzzle(15, 15, row_depth=5, column_depth=5),
    _puzzle(15, 18, row_depth=5, column_depth=5),
    _puzzle(15, 20, row_depth=5, column_depth=5),
)


class TestPackedSolvedLayout_FourUpDeclinesOnTheKdpMinimumTrim:
    """Review F-1: the exact reviewer scenario now declines instead of overlapping."""

    def test_the_four_up_call_returns_none(self) -> None:
        assert compute_packed_solved_layout(_ANSWERS, 4, KDP_MIN_ODD) is None

    def test_the_decline_is_really_about_the_floor(self) -> None:
        """Sanity: the KDP-min 4-up tile really cannot clear MIN_CELL_MM here.

        Worked by hand from the trim: usable height is
        100 - 2 x 9.525 = 80.95 mm; a 4-up tile's drawing height is
        (80.95 - 4.0) / 2 - 12.0 = 26.475 mm. The tallest member (20 rows,
        5-deep column gutter) needs 26.475 / 25 = 1.059 mm/cell, already
        under MIN_CELL_MM (2.0 mm) before the width term is even considered.
        """
        tile_height_mm = (100.0 - 2 * 9.525 - 4.0) / 2
        drawing_height_mm = tile_height_mm - 12.0
        worst_fit = drawing_height_mm / (5 + 20)
        assert worst_fit == pytest.approx(1.059, abs=0.01)
        assert worst_fit < MIN_CELL_MM


class TestPackedSolvedLayout_TheSameAnswersPackTwoUpInstead:
    """Review F-1: the next lower density (2-up) still fits these same answers."""

    def test_the_first_pair_packs_two_up(self) -> None:
        layout = compute_packed_solved_layout(_ANSWERS[:2], 2, KDP_MIN_ODD)
        assert isinstance(layout, PackedSolvedLayout)
        assert layout.capacity == 2
        assert len(layout.slots) == 2

    def test_the_second_pair_packs_two_up(self) -> None:
        layout = compute_packed_solved_layout(_ANSWERS[2:], 2, KDP_MIN_ODD)
        assert isinstance(layout, PackedSolvedLayout)
        assert layout.capacity == 2
        assert len(layout.slots) == 2

    def test_the_two_up_cell_clears_the_floor(self) -> None:
        layout = compute_packed_solved_layout(_ANSWERS[2:], 2, KDP_MIN_ODD)
        assert layout is not None
        assert layout.cell_mm >= MIN_CELL_MM


class TestPackedSolvedLayout_EvenTwoUpDeclinesWhenTheGuttersAreDeepEnough:
    """Review F-1: deep enough gutters decline at 2-up too (full fallback needed)."""

    #: Column-clue depth 25 on this trim's 2-up tile (drawing height 68.95 mm,
    #: see the module docstring's worked numbers) pushes even the *smallest*
    #: height (10) under MIN_CELL_MM: 68.95 / (25 + 10) = 1.97 mm.
    _DEEP = tuple(
        _puzzle(15, height, row_depth=5, column_depth=25)
        for height in (10, 15, 18, 20)
    )

    def test_four_up_declines(self) -> None:
        assert compute_packed_solved_layout(self._DEEP, 4, KDP_MIN_ODD) is None

    def test_every_two_up_pair_also_declines(self) -> None:
        assert compute_packed_solved_layout(self._DEEP[:2], 2, KDP_MIN_ODD) is None
        assert compute_packed_solved_layout(self._DEEP[2:], 2, KDP_MIN_ODD) is None


class TestPackedSolvedLayout_EverySurvivingSlotActuallyFitsItsOwnTile:
    """Review F-1: a layout this function *does* return never overflows a tile.

    This is the structural half of the guarantee — not "the reviewer's exact
    numbers no longer overflow" but "no cell this function ever hands back can
    overflow a tile", because the decline above is unconditional on every
    member clearing the floor at once, not just the one the reviewer measured.
    """

    def test_every_slot_fits_its_tile_on_a_surviving_layout(self) -> None:
        layout = compute_packed_solved_layout(_ANSWERS[:2], 2, KDP_MIN_ODD)
        assert layout is not None
        for slot in layout.slots:
            assert slot.page is not None
            assert slot.page.fits

    def test_the_four_up_capacity_still_works_for_shallow_gutters(self) -> None:
        """Control: the same shape at a shallow gutter still 4-ups normally.

        Even this KDP-minimum trim's 4-up tile (drawing height 26.475 mm,
        see the module docstring) has room for a shallow-gutter small answer:
        depth 1 on both axes, heights 8-11, lands at 2.206 mm/cell — above
        MIN_CELL_MM, so this is the non-degenerate case the fix must not
        break.
        """
        shallow = tuple(
            _puzzle(15, height, row_depth=1, column_depth=1)
            for height in (8, 9, 10, 11)
        )
        layout = compute_packed_solved_layout(shallow, 4, KDP_MIN_ODD)
        assert isinstance(layout, PackedSolvedLayout)
        assert layout.capacity == 4
        assert len(layout.slots) == 4
        for slot in layout.slots:
            assert slot.page is not None
            assert slot.page.fits
