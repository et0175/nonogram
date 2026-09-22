"""CARD-125: the pair-aware layout call, measured at layout level (FR-040).

    AC-242  TestPairLayout_TwoTenByTensShareAtStandardCell
    AC-243  TestPairLayout_TwelvePairAtSevenThirtyNine
    AC-244  TestPairLayout_JustAboveTwoUpMinimum
    AC-245  TestPairLayout_JustBelowTwoUpMinimumIsNone
    AC-246  TestPairLayout_FifteenPlusTwelveIsNone
    AC-247  TestPairLayout_WidthFailureAtTwoUpMinimumIsNone
    AC-252 (layout half)  TestPairLayout_UpperSlotSharesSinglePageTopRow
    The call's contract: TestPairLayout_RefusesSpecsThatNeverPair,
            TestPairLayout_RefusesMalformedClues, TestPairLayout_SlotGeometry,
            TestPairLayout_ValueObjectRefusesAnInvalidPair

These are the layout-level halves of FR-040's criteria; CARD-127 re-asserts
them on the book PDF. The standing properties (EC-028 and the ADR-0037/R2
strokes on two-up pages) are in ``tests/property/test_book_two_up.py``.

Every expected cell is worked out here from FR-040's own definition, in
millimetres, as a literal: Book 1's usable width is 215.9 − 12.7 − 9.525 =
193.675 mm, and the height left for the two drawings is 279.4 − 2 × 9.525 −
2 × 12 = 236.35 mm. The cell is min(7.5, 236.35 / combined rows, 193.675 /
the wider drawing's columns). Nothing is asked of ``layout``'s helpers.
"""

from __future__ import annotations

import dataclasses

import pytest

from nonogram import export
from nonogram.export.layout import (
    DEFAULT_PAGE_SPEC,
    DPI,
    TWO_UP_MIN_CELL_MM,
    CellCapPolicy,
    OrientationPolicy,
    PageParity,
    PageSpec,
    PairLayout,
    compute_layout,
    compute_pair_layout,
    header_band,
)

#: CON-018's Book 1 profile (the same literal as tests/test_layout_page_spec.py;
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
BOOK1_TWO_UP_HEIGHT_MM = 236.35
PX_PER_MM = DPI / 25.4
HALF_PIXEL_MM = 0.5 / PX_PER_MM

type Puzzle = tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]


def _puzzle(columns: int, rows: int, *, row_depth: int, column_depth: int) -> Puzzle:
    """A ``columns`` x ``rows`` puzzle whose gutters are exactly that deep.

    Each clue is ``depth`` runs of 1, which needs ``2 * depth - 1`` cells: a
    10-cell line holds up to 5, a 15-cell line up to 7.
    """
    return (
        tuple((1,) * row_depth for _ in range(rows)),
        tuple((1,) * column_depth for _ in range(columns)),
    )


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _pair(first: Puzzle, second: Puzzle, spec: PageSpec = BOOK1_ODD) -> PairLayout:
    pair = compute_pair_layout(first, second, spec)
    assert pair is not None
    return pair


class TestPairLayout_TwoTenByTensShareAtStandardCell:
    """AC-242: two 10x10s with 4-deep gutters (28 rows) fit 8.44 mm; they share 7.5 mm."""

    def test_the_shared_cell_is_the_standard_cell(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        page_fit = BOOK1_TWO_UP_HEIGHT_MM / 28
        assert page_fit == pytest.approx(8.44, abs=0.005)

        pair = _pair(ten, ten)

        assert pair.cell_mm == 7.5
        assert pair.upper.page is not None and pair.lower.page is not None
        assert pair.upper.page.cell_mm == pair.lower.page.cell_mm == 7.5


class TestPairLayout_TwelvePairAtSevenThirtyNine:
    """AC-243: two 12x12s with 4-deep gutters, 236.35 mm over 32 rows = 7.39 mm."""

    def test_the_shared_cell_is_the_height_fit(self) -> None:
        twelve = _puzzle(12, 12, row_depth=4, column_depth=4)

        pair = _pair(twelve, twelve)

        assert pair.cell_mm == pytest.approx(7.39, abs=0.05)
        assert pair.cell_mm == pytest.approx(BOOK1_TWO_UP_HEIGHT_MM / 32, abs=1e-9)


class TestPairLayout_JustAboveTwoUpMinimum:
    """AC-244: a 15x15 (5-deep columns) over a 10x10 (3-deep): 33 rows, 7.16 mm."""

    def test_the_pair_shares_just_above_seven_millimetres(self) -> None:
        fifteen = _puzzle(15, 15, row_depth=3, column_depth=5)
        ten = _puzzle(10, 10, row_depth=3, column_depth=3)

        pair = _pair(fifteen, ten)

        assert pair.cell_mm == pytest.approx(7.16, abs=0.05)
        assert pair.cell_mm == pytest.approx(BOOK1_TWO_UP_HEIGHT_MM / 33, abs=1e-9)
        assert pair.cell_mm >= TWO_UP_MIN_CELL_MM == 7.0


class TestPairLayout_JustBelowTwoUpMinimumIsNone:
    """AC-245: the same pair with a 6-deep column gutter is 34 rows, 6.95 mm: no pairing."""

    def test_no_pairing(self) -> None:
        fifteen = _puzzle(15, 15, row_depth=3, column_depth=6)
        ten = _puzzle(10, 10, row_depth=3, column_depth=3)
        assert BOOK1_TWO_UP_HEIGHT_MM / 34 == pytest.approx(6.95, abs=0.005)

        assert compute_pair_layout(fifteen, ten, BOOK1_ODD) is None
        assert compute_pair_layout(fifteen, ten, BOOK1_EVEN) is None


class TestPairLayout_FifteenPlusTwelveIsNone:
    """AC-246: a 15x15 (5-deep) over a 12x12 (4-deep) is 36 rows, 6.57 mm: no pairing."""

    def test_no_pairing(self) -> None:
        fifteen = _puzzle(15, 15, row_depth=3, column_depth=5)
        twelve = _puzzle(12, 12, row_depth=4, column_depth=4)
        assert BOOK1_TWO_UP_HEIGHT_MM / 36 == pytest.approx(6.57, abs=0.005)

        assert compute_pair_layout(fifteen, twelve, BOOK1_ODD) is None


class TestPairLayout_WidthFailureAtTwoUpMinimumIsNone:
    """AC-247: a 22-wide x 10-tall with a 6-deep row gutter is 28 across, 6.92 mm at most.

    The height alone would allow it (13 + 13 rows, 9.09 mm), so ``None`` here
    is the width rule (b), not the height rule (a).
    """

    def test_no_pairing_on_width(self) -> None:
        wide = _puzzle(22, 10, row_depth=6, column_depth=3)
        ten = _puzzle(10, 10, row_depth=3, column_depth=3)
        assert BOOK1_TWO_UP_HEIGHT_MM / 26 > 7.5
        assert BOOK1_USABLE_WIDTH_MM / 28 == pytest.approx(6.92, abs=0.005)

        assert compute_pair_layout(wide, ten, BOOK1_ODD) is None
        # Either order: the width rule is per puzzle, not per slot.
        assert compute_pair_layout(ten, wide, BOOK1_ODD) is None

    def test_the_same_pair_without_the_wide_gutter_does_pair(self) -> None:
        # Control: a 4-deep row gutter is 26 across, 7.45 mm, so the width no longer fails.
        wide = _puzzle(22, 10, row_depth=4, column_depth=3)
        ten = _puzzle(10, 10, row_depth=3, column_depth=3)

        pair = _pair(wide, ten)

        assert pair.cell_mm == pytest.approx(BOOK1_USABLE_WIDTH_MM / 26, abs=1e-9)


class TestPairLayout_UpperSlotSharesSinglePageTopRow:
    """AC-252's layout half: the upper slot is a single page's drawing, on its fixed row."""

    @pytest.mark.parametrize("spec", [BOOK1_ODD, BOOK1_EVEN], ids=["odd", "even"])
    def test_upper_drawing_top_is_the_single_page_top(self, spec: PageSpec) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        twenty = compute_layout(*_puzzle(20, 20, row_depth=8, column_depth=8), spec)

        pair = _pair(ten, ten, spec)

        assert pair.upper.page is not None and twenty.page is not None
        assert pair.upper.page.drawing_top == twenty.page.drawing_top
        assert abs(_mm(pair.upper.page.drawing_top) - (9.525 + 12.0)) <= HALF_PIXEL_MM + 1e-9

    @pytest.mark.parametrize("spec", [BOOK1_ODD, BOOK1_EVEN], ids=["odd", "even"])
    def test_at_the_same_cell_the_upper_slot_is_the_single_page(self, spec: PageSpec) -> None:
        """A 10x10 alone also prints 7.5 mm: every line and clue is where the pair puts it."""
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        single = compute_layout(*ten, spec)

        pair = _pair(ten, ten, spec)

        upper = pair.upper
        assert single.page is not None and upper.page is not None
        assert upper.grid_lines == single.grid_lines
        assert upper.clue_entries == single.clue_entries
        assert (upper.thin_rule, upper.thick_rule) == (single.thin_rule, single.thick_rule)
        assert (upper.width, upper.height, upper.margin) == (single.width, single.height, single.margin)
        assert upper.page.drawing_left == single.page.drawing_left


class TestPairLayout_SlotGeometry:
    """Where the two slots sit: earlier on top, each under its own band, never overlapping."""

    def test_the_earlier_puzzle_takes_the_upper_slot(self) -> None:
        fifteen = _puzzle(15, 15, row_depth=3, column_depth=5)
        ten = _puzzle(10, 10, row_depth=3, column_depth=3)

        pair = _pair(fifteen, ten)

        assert (pair.upper.columns, pair.upper.rows) == (15, 15)
        assert (pair.lower.columns, pair.lower.rows) == (10, 10)
        assert pair.upper.page is not None and pair.lower.page is not None
        assert pair.upper.page.drawing_bottom <= pair.lower.page.drawing_top

    @pytest.mark.parametrize("spec", [BOOK1_ODD, BOOK1_EVEN], ids=["odd", "even"])
    def test_each_slot_has_its_own_band_and_the_slots_do_not_overlap(self, spec: PageSpec) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        pair = _pair(ten, ten, spec)
        upper, lower = pair.upper.page, pair.lower.page
        assert upper is not None and lower is not None

        # The upper slot starts at the top margin, the lower one ends at the bottom margin.
        assert abs(_mm(upper.usable_top) - 9.525) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(lower.drawing_bottom) - (279.4 - 9.525)) <= HALF_PIXEL_MM + 1e-9
        assert lower.usable_bottom == lower.drawing_bottom
        # One boundary between the slots; the lower band lies between the drawings.
        assert upper.usable_bottom == lower.usable_top
        assert upper.drawing_bottom <= lower.usable_top < lower.drawing_top
        for slot in (pair.upper, pair.lower):
            band = header_band(slot)
            assert abs(_mm(band.height) - 12.0) <= 2 * HALF_PIXEL_MM
            assert slot.page is not None and slot.page.fits
        # The spare height (236.35 − 28 × 7.5 = 26.35 mm) falls between the slots.
        assert _mm(lower.usable_top - upper.drawing_bottom) == pytest.approx(26.35, abs=2 * HALF_PIXEL_MM)

    def test_each_slot_is_centred_across_the_usable_width_on_either_parity(self) -> None:
        fifteen = _puzzle(15, 15, row_depth=3, column_depth=5)
        ten = _puzzle(10, 10, row_depth=3, column_depth=3)
        cell = BOOK1_TWO_UP_HEIGHT_MM / 33
        for spec, left_margin in ((BOOK1_ODD, 12.7), (BOOK1_EVEN, 9.525)):
            pair = _pair(fifteen, ten, spec)
            for slot, across in ((pair.upper, 18), (pair.lower, 13)):
                assert slot.page is not None
                expected_left = left_margin + (BOOK1_USABLE_WIDTH_MM - across * cell) / 2
                assert abs(_mm(slot.page.drawing_left) - expected_left) <= HALF_PIXEL_MM + 1e-9

    def test_both_slots_use_the_book_strokes(self) -> None:
        twelve = _puzzle(12, 12, row_depth=4, column_depth=4)
        pair = _pair(twelve, twelve)
        for slot in (pair.upper, pair.lower):
            assert slot.thin_rule >= 3 and _mm(slot.thin_rule) >= 0.25
            assert slot.thick_rule == 2 * slot.thin_rule
            majors = [line.index for line in slot.vertical_lines if line.major]
            assert majors == [0, 5, 10, 12]


class TestPairLayout_RefusesSpecsThatNeverPair:
    """Only a placed page with a flat cap pairs; the default A4 spec never does."""

    def test_default_spec_raises(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        with pytest.raises(ValueError, match="never pairs"):
            compute_pair_layout(ten, ten, DEFAULT_PAGE_SPEC)

    def test_comfort_curve_placed_spec_raises(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        spec = dataclasses.replace(BOOK1_ODD, cell_cap=CellCapPolicy.COMFORT_CURVE)
        with pytest.raises(ValueError, match="flat"):
            compute_pair_layout(ten, ten, spec)

    def test_portrait_only_spec_without_parity_raises(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        spec = dataclasses.replace(
            BOOK1_ODD, parity=None, top_mm=10.0, bottom_mm=10.0, gutter_mm=10.0, outside_mm=10.0
        )
        with pytest.raises(ValueError, match="placed"):
            compute_pair_layout(ten, ten, spec)

    def test_not_a_spec_raises_type_error(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        with pytest.raises(TypeError):
            compute_pair_layout(ten, ten, None)  # type: ignore[arg-type]

    def test_a_cap_below_the_two_up_minimum_never_pairs(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        assert compute_pair_layout(ten, ten, dataclasses.replace(BOOK1_ODD, cell_cap=6.9)) is None

    def test_a_page_too_short_for_two_bands_is_none_not_an_error(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        # 60 − 2 × 9.525 = 40.95 mm between the margins: one 21 mm band fits, two (42 mm) do not.
        spec = dataclasses.replace(BOOK1_ODD, height_mm=60.0, band_mm=21.0)
        assert compute_pair_layout(ten, ten, spec) is None


class TestPairLayout_RefusesMalformedClues:
    """A malformed puzzle is a caller bug, raised like compute_layout raises it."""

    def test_rows_without_columns(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        with pytest.raises(ValueError, match="second: clue sets disagree"):
            compute_pair_layout(ten, (ten[0], ()), BOOK1_ODD)

    def test_not_a_pair(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        with pytest.raises(ValueError, match="first must be"):
            compute_pair_layout((ten[0],), ten, BOOK1_ODD)  # type: ignore[arg-type]


class TestPairLayout_ValueObjectRefusesAnInvalidPair:
    """PairLayout enforces its own invariants, whoever builds it."""

    def test_two_different_cells(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        twelve = _puzzle(12, 12, row_depth=4, column_depth=4)
        a, b = _pair(ten, ten), _pair(twelve, twelve)
        with pytest.raises(ValueError, match="one shared cell"):
            PairLayout(upper=a.upper, lower=b.lower, cell_mm=a.cell_mm)

    def test_below_the_two_up_minimum(self) -> None:
        wide = _puzzle(22, 10, row_depth=6, column_depth=3)
        single = compute_layout(*wide, BOOK1_ODD)
        assert single.page is not None and single.page.cell_mm < 7.0
        with pytest.raises(ValueError, match="at least"):
            PairLayout(upper=single, lower=single, cell_mm=single.page.cell_mm)

    def test_overlapping_slots(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        pair = _pair(ten, ten)
        with pytest.raises(ValueError, match="overlap"):
            PairLayout(upper=pair.lower, lower=pair.upper, cell_mm=pair.cell_mm)

    def test_a_drawing_sized_layout_is_not_a_slot(self) -> None:
        ten = _puzzle(10, 10, row_depth=4, column_depth=4)
        default = compute_layout(*ten)
        with pytest.raises(ValueError, match="placed-page"):
            PairLayout(upper=default, lower=default, cell_mm=7.5)


def test_export_package_re_exports_the_pair_types() -> None:
    assert export.PairLayout is PairLayout
    assert export.TWO_UP_MIN_CELL_MM == TWO_UP_MIN_CELL_MM == 7.0
