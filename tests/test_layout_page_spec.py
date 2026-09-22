"""CARD-114: the PageSpec value object, and the book cell measured at layout level.

    AC-236  TestBookCell_CappedAtStandardCell
    AC-237  TestBookCell_BookCapOverridesCliComfortCurve
    AC-238  TestBookCell_ThirtyByThirtyNineDeepAboveFloor
    AC-239  TestBookCell_TwelveDeepBandFallsBelowFloor   (the 4.61 mm cell only;
            the below-floor flag is CARD-121/CARD-123)
    EC(ADR-0036/R1)  TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden
            -> the explicit-default case CARD-114 adds beside CARD-113's
               (``tests/test_export_a4_golden.py`` holds the no-spec case)
    PageSpec's own invariants and the renderers' threading of the spec:
            TestPageSpec_*, TestRenderers_*

The standing properties (EC-019, EC-022's and EC-032's layout halves, the
ADR-0037/R2 strokes) are in ``tests/property/test_book_layout.py``.

The Book 1 spec is a literal here, from CON-018's own numbers. The admin-side
builder is CARD-115, and ``export`` tests never import ``nonogram.admin``.
Expected cells are worked out from FR-030's definition in millimetres, written
as literals (193.675 mm usable width is 8.5 in − 0.5 in − 0.375 in), never by
asking ``layout`` for its page-fit helper.
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from nonogram import export
from nonogram.clues import compute_clues
from nonogram.export import pdf, png
from nonogram.export.layout import (
    DEFAULT_PAGE_SPEC,
    DPI,
    HEADER_BAND_MM,
    PAGE_HEIGHT_MM,
    PAGE_MARGIN_MM,
    PAGE_WIDTH_MM,
    CellCapPolicy,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_layout,
)
from tests.fixtures.a4_golden import golden

#: CON-018's Book 1 profile, in mm: 8.5 x 11 in trim, 0.5 in gutter, 0.375 in
#: outside/top/bottom, the 12 mm band (TERM-028), portrait only, the flat
#: 7.5 mm standard cell (NFR-008) and ADR-0037's 0.25 mm thin-rule minimum.
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

#: FR-030's usable width on the Book 1 trim: 215.9 − 12.7 − 9.525 mm.
BOOK1_USABLE_WIDTH_MM = 193.675


def _px_to_mm(pixels: float) -> float:
    return pixels / DPI * 25.4


def _clues_of_depth(lines: int, depth: int) -> tuple[tuple[int, ...], ...]:
    """``lines`` clues, each exactly ``depth`` runs of 1 (what a gutter that deep holds).

    ``(1, 1, ..., 1)`` of ``depth`` entries needs ``2 * depth - 1`` cells. So
    a 15-cell line holds a 7-deep clue, a 30-cell line a 12-deep one.
    """
    return tuple((1,) * depth for _ in range(lines))


def _book_cell_mm(columns: int, rows: int, *, row_depth: int, column_depth: int) -> float:
    layout = compute_layout(
        _clues_of_depth(rows, row_depth), _clues_of_depth(columns, column_depth), BOOK1_ODD
    )
    assert layout.page is not None
    assert (layout.columns, layout.rows) == (columns, rows)
    assert (layout.row_gutter_cells, layout.column_gutter_cells) == (row_depth, column_depth)
    return layout.page.cell_mm


class TestBookCell_CappedAtStandardCell:
    """AC-236: a 15x15 with 7-deep gutters fits 8.8 mm on Book 1, and prints 7.5 mm."""

    def test_fifteen_by_fifteen_seven_deep_is_held_at_the_standard_cell(self) -> None:
        page_fit_mm = BOOK1_USABLE_WIDTH_MM / (7 + 15)
        assert round(page_fit_mm, 1) == 8.8  # the AC's own premise

        assert _book_cell_mm(15, 15, row_depth=7, column_depth=7) == 7.5


class TestBookCell_BookCapOverridesCliComfortCurve:
    """AC-237: the CLI prints a 10x10 at NFR-005's 9.0 mm; the book prints it at 7.5 mm."""

    def test_ten_by_ten_is_nine_mm_on_a4_and_seven_and_a_half_in_the_book(self) -> None:
        rows, columns = _clues_of_depth(10, 1), _clues_of_depth(10, 1)

        cli = compute_layout(rows, columns)
        # NFR-005's cap for a 10-cell grid is 9.0 mm, truncated to whole pixels.
        assert cli.cell == int(9.0 / 25.4 * DPI)
        assert round(_px_to_mm(cli.cell), 1) == 9.0
        assert cli.page is None

        book = compute_layout(rows, columns, BOOK1_ODD)
        assert book.page is not None
        assert book.page.cell_mm == 7.5


class TestBookCell_ThirtyByThirtyNineDeepAboveFloor:
    """AC-238: a 30x30 with 9-deep gutters prints 4.97 mm on Book 1, above the 4.8 mm floor."""

    def test_thirty_by_thirty_nine_deep_is_four_point_nine_seven(self) -> None:
        cell = _book_cell_mm(30, 30, row_depth=9, column_depth=9)

        assert cell >= 4.8
        assert cell == pytest.approx(BOOK1_USABLE_WIDTH_MM / 39, abs=1e-9)
        assert round(cell, 2) == 4.97


class TestBookCell_TwelveDeepBandFallsBelowFloor:
    """AC-239 (layout half): a 30 wide x 25 tall, 12-deep row gutter prints 4.61 mm.

    AC-182's fixture: the column gutter is 8 deep, and the width binds. The
    below-floor flag is FR-031's (CARD-121/CARD-123).
    """

    def test_twelve_deep_row_gutter_is_four_point_six_one(self) -> None:
        cell = _book_cell_mm(30, 25, row_depth=12, column_depth=8)

        assert cell < 4.8
        assert cell == pytest.approx(BOOK1_USABLE_WIDTH_MM / 42, abs=1e-9)
        assert round(cell, 2) == 4.61


class TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden:
    """EC(ADR-0036/R1), the explicit-default half: passing DEFAULT_PAGE_SPEC changes nothing.

    CARD-113's class of the same name pins ``compute_layout`` with no spec.
    This one pins the same golden with the default spec *passed*, and pins that
    both renderers draw the same bytes either way. G-6: the default spec has no
    parity, and ``Layout.page`` stays ``None``.
    """

    _CASES = golden.load(golden.LAYOUT_GOLDEN)["cases"]

    @pytest.mark.parametrize("case_id", sorted(_CASES))
    def test_explicit_default_spec_matches_the_a4_golden(self, case_id: str) -> None:
        case = self._CASES[case_id]
        rows = tuple(tuple(clue) for clue in case["row_clues"])
        columns = tuple(tuple(clue) for clue in case["column_clues"])

        explicit = compute_layout(rows, columns, DEFAULT_PAGE_SPEC)

        assert not golden.layout_differences(case["layout"], golden.serialize_layout(explicit))
        assert explicit == compute_layout(rows, columns)
        assert explicit.page is None

    def test_the_default_spec_is_todays_constants(self) -> None:
        spec = DEFAULT_PAGE_SPEC
        assert (spec.width_mm, spec.height_mm) == (210.0, 297.0) == (PAGE_WIDTH_MM, PAGE_HEIGHT_MM)
        assert spec.top_mm == spec.bottom_mm == spec.gutter_mm == spec.outside_mm == 12.0
        assert PAGE_MARGIN_MM == 12.0
        assert spec.band_mm == HEADER_BAND_MM == 12.0
        assert spec.orientation is OrientationPolicy.LARGER_CELL_WINS
        assert spec.cell_cap is CellCapPolicy.COMFORT_CURVE
        assert spec.min_thin_rule_mm is None
        assert spec.parity is None

    def test_renderers_draw_the_same_bytes_with_the_default_spec_passed(self) -> None:
        payload = _payload(_checkerboard(12, 17))

        assert (
            png.render_image(payload, page_spec=DEFAULT_PAGE_SPEC).tobytes()
            == png.render_image(payload).tobytes()
        )
        for passed, implicit in zip(
            pdf.render_pages(payload, page_spec=DEFAULT_PAGE_SPEC),
            pdf.render_pages(payload),
            strict=True,
        ):
            assert passed.size == implicit.size
            assert passed.tobytes() == implicit.tobytes()


def _valid_fields(**overrides: object) -> dict[str, object]:
    fields = {
        field.name: getattr(BOOK1_ODD, field.name) for field in dataclasses.fields(PageSpec)
    }
    fields.update(overrides)
    return fields


class TestPageSpec_RefusesPoisonSpecs:
    """Failure matrix, the constructor rows: an invalid PageSpec cannot exist."""

    @pytest.mark.parametrize(
        "overrides",
        [
            {"width_mm": 0.0},
            {"height_mm": -1.0},
            {"width_mm": math.nan},
            {"height_mm": math.inf},
            {"top_mm": -0.1},
            {"band_mm": -12.0},
            {"gutter_mm": True},
            {"outside_mm": "9.525"},
            {"bottom_mm": None},
        ],
    )
    def test_non_finite_non_positive_or_non_numeric_measurements(self, overrides) -> None:
        with pytest.raises(ValueError, match="PageSpec"):
            PageSpec(**_valid_fields(**overrides))

    @pytest.mark.parametrize(
        "overrides",
        [
            {"gutter_mm": 110.0, "outside_mm": 110.0},  # margins exceed the trim
            {"gutter_mm": 106.2, "outside_mm": 109.7},  # usable width exactly 0
            {"top_mm": 140.0, "bottom_mm": 139.4},  # usable height 0 before the band
            {"band_mm": 260.35},  # the band eats the rest: usable height exactly 0
        ],
    )
    def test_non_positive_usable_area(self, overrides) -> None:
        with pytest.raises(ValueError, match="usable area is non-positive"):
            PageSpec(**_valid_fields(**overrides))

    @pytest.mark.parametrize("parity", ["odd", 1, True, "EVEN"])
    def test_invalid_parity(self, parity) -> None:
        with pytest.raises(ValueError, match="invalid parity"):
            PageSpec(**_valid_fields(parity=parity))

    @pytest.mark.parametrize("cap", [0.0, -7.5, math.nan, math.inf, "comfort_curve", True])
    def test_invalid_cell_cap(self, cap) -> None:
        with pytest.raises(ValueError, match="cell_cap"):
            PageSpec(**_valid_fields(cell_cap=cap))

    @pytest.mark.parametrize("minimum", [0.0, -0.25, math.nan, "0.25"])
    def test_invalid_stroke_minimum(self, minimum) -> None:
        with pytest.raises(ValueError, match="min_thin_rule_mm"):
            PageSpec(**_valid_fields(min_thin_rule_mm=minimum))

    def test_invalid_orientation_policy(self) -> None:
        with pytest.raises(ValueError, match="orientation"):
            PageSpec(**_valid_fields(orientation="portrait_only"))

    def test_a_placed_page_may_not_turn(self) -> None:
        with pytest.raises(ValueError, match="never turned"):
            PageSpec(**_valid_fields(orientation=OrientationPolicy.LARGER_CELL_WINS))

    def test_no_parity_needs_one_uniform_margin(self) -> None:
        with pytest.raises(ValueError, match="four margins must be equal"):
            PageSpec(**_valid_fields(parity=None))

    def test_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            BOOK1_ODD.width_mm = 100.0  # type: ignore[misc]

    def test_compute_layout_refuses_a_spec_that_is_not_a_page_spec(self) -> None:
        with pytest.raises(TypeError, match="PageSpec"):
            compute_layout(_clues_of_depth(10, 1), _clues_of_depth(10, 1), {"parity": "odd"})  # type: ignore[arg-type]


class TestPageSpec_ParityMovesTheUsableAreaNeverItsSize:
    """The Book 1 usable area on both parities (AC-272/AC-273's numbers, at layout level)."""

    def test_book1_margins_by_parity(self) -> None:
        assert (BOOK1_ODD.left_margin_mm, BOOK1_ODD.right_margin_mm) == (12.7, 9.525)
        assert (BOOK1_EVEN.left_margin_mm, BOOK1_EVEN.right_margin_mm) == (9.525, 12.7)
        assert BOOK1_ODD.usable_width_mm == BOOK1_EVEN.usable_width_mm
        assert BOOK1_ODD.usable_width_mm == pytest.approx(BOOK1_USABLE_WIDTH_MM)

    def test_placed_usable_area_in_pixels(self) -> None:
        clues = _clues_of_depth(15, 7)
        odd = compute_layout(clues, clues, BOOK1_ODD).page
        even = compute_layout(clues, clues, BOOK1_EVEN).page
        assert odd is not None and even is not None
        # 12.7 mm = 150 px; 9.525 mm = 112.5 px, rounded half up; 206.375 mm = 2437.5 px.
        assert (odd.usable_left, odd.usable_right) == (150, 2438)
        assert (even.usable_left, even.usable_right) == (113, 2400)
        assert _px_to_mm(odd.usable_left) == pytest.approx(12.7)
        assert _px_to_mm(even.usable_right) == pytest.approx(203.2)

    def test_fifteen_by_fifteen_left_edges_on_facing_pages(self) -> None:
        """Handoff increment 13: 27.04 mm (odd) and 23.86 mm (even), the same top row."""
        clues = _clues_of_depth(15, 7)
        odd = compute_layout(clues, clues, BOOK1_ODD).page
        even = compute_layout(clues, clues, BOOK1_EVEN).page
        assert odd is not None and even is not None
        drawing_mm = 22 * 7.5
        expected_odd = 12.7 + (BOOK1_USABLE_WIDTH_MM - drawing_mm) / 2
        expected_even = 9.525 + (BOOK1_USABLE_WIDTH_MM - drawing_mm) / 2
        half_pixel_mm = _px_to_mm(0.5)
        assert abs(_px_to_mm(odd.drawing_left) - expected_odd) <= half_pixel_mm
        assert abs(_px_to_mm(even.drawing_left) - expected_even) <= half_pixel_mm
        assert odd.drawing_top == even.drawing_top


def _checkerboard(columns: int, rows: int) -> list[list[bool]]:
    return [[(row + column) % 2 == 0 for column in range(columns)] for row in range(rows)]


def _payload(grid: list[list[bool]], *, name: str | None = "cat") -> export.ExportPayload:
    clues = compute_clues(grid)
    return export.ExportPayload(
        grid=grid,
        row_clues=clues.rows,
        column_clues=clues.columns,
        seed=7,
        mode="random",
        name=name,
        difficulty="Medium",
    )


class TestRenderers_ThreadTheBookSpec:
    """``render_image``/``render_pages`` take the spec and return trim-sized pages."""

    def test_render_image_returns_the_trim_with_the_drawing_placed(self) -> None:
        payload = _payload(_checkerboard(30, 30))
        image = png.render_image(payload, page_spec=BOOK1_ODD)
        layout = compute_layout(payload.row_clues, payload.column_clues, BOOK1_ODD)
        assert layout.page is not None

        # 8.5 x 11 in at 300 DPI (AC-177's letter page).
        assert image.size == (2550, 3300)
        # Ink only inside the drawing, give or take half a heavy rule, and none in the band.
        ink = image.convert("L").point(lambda value: 255 if value < 250 else 0).getbbox()
        assert ink is not None
        half = layout.thick_rule // 2 + 1
        assert ink[0] >= layout.page.drawing_left - half
        assert ink[1] >= layout.page.drawing_top - half
        assert ink[2] <= layout.page.drawing_right + half
        assert ink[3] <= layout.page.drawing_bottom + half

    def test_render_pages_sets_the_header_inside_the_band_and_fills_the_answer(self) -> None:
        grid = _checkerboard(15, 15)
        payload = _payload(grid)
        puzzle_page, answer_page = pdf.render_pages(payload, page_spec=BOOK1_EVEN)
        layout = compute_layout(payload.row_clues, payload.column_clues, BOOK1_EVEN)
        placement = layout.page
        assert placement is not None

        assert puzzle_page.size == answer_page.size == (2550, 3300)

        band = puzzle_page.convert("L").crop(
            (placement.usable_left, placement.usable_top, placement.usable_right, placement.drawing_top)
        )
        assert band.getextrema()[0] < 128, "the header is set inside the band"
        above = puzzle_page.convert("L").crop((0, 0, 2550, placement.usable_top))
        assert above.getextrema() == (255, 255), "nothing is printed in the top margin"

        xs = [line.position for line in layout.vertical_lines]
        ys = [line.position for line in layout.horizontal_lines]
        for row in range(15):
            for column in range(15):
                centre = ((xs[column] + xs[column + 1]) // 2, (ys[row] + ys[row + 1]) // 2)
                expected = (0, 0, 0) if grid[row][column] else (255, 255, 255)
                assert answer_page.getpixel(centre) == expected
                assert puzzle_page.getpixel(centre) == (255, 255, 255)

    def test_an_untitled_placed_page_has_an_empty_band(self) -> None:
        payload = _payload(_checkerboard(10, 10), name=None)
        payload = dataclasses.replace(payload, difficulty=None)
        puzzle_page, _ = pdf.render_pages(payload, page_spec=BOOK1_ODD)
        layout = compute_layout(payload.row_clues, payload.column_clues, BOOK1_ODD)
        assert layout.page is not None
        band = puzzle_page.convert("L").crop((0, 0, 2550, layout.page.drawing_top - layout.thick_rule))
        assert band.getextrema() == (255, 255)
