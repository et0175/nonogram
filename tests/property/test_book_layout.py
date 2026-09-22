"""CARD-114: the book's standing layout properties, over seeded corpora of PageSpecs.

    EC-019 (layout half)  PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell
        -> test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell
        -> test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_floor_cases
    ADR-0037/R2           PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin
        -> test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin
        -> test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_pixels
    EC-022 (layout half)  PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent
        -> test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent
    EC-032 (layout half)  PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity
        -> test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity
    PageSpec's invariant  test_PropertyTest_PageSpec_ExistsExactlyWhenItsUsableAreaIsPositive

The PDF-level halves of EC-019 ("the PDF page is the trim size"), EC-022 and
EC-032 are CARD-116's.

How the expectations are independent
------------------------------------
Every expected number is worked out here, in millimetres, from FR-030's own
definition: usable width = trim − gutter − outside, usable height = trim − top
− bottom − band, cell = min(cap, usable width / drawing columns, usable height
/ drawing rows). That is a second implementation. It does not share
``layout``'s exact-fraction arithmetic, its pixel rounding or its helpers, so
the two are compared with a stated tolerance (a millionth of a millimetre for
the cell, half a device pixel for any placed edge, one pixel for a difference
of two independently rounded edges) instead of exact equality.
The clue sets are real encodings of random grids, from ``nonogram.clues``
(legal in the test tree), topped up with the deepest-gutter patterns
(alternating cells) so that every depth up to 15 appears.

No ``hypothesis`` (CLAUDE.md): stdlib ``random.Random`` at fixed seeds, and
each test asserts its own minimum case count so the corpus cannot shrink
silently.

How the MIN_CELL_MM floor interacts (EC-019)
--------------------------------------------
The floor (2.0 mm) still beats page fit on a placed page, as it does on A4.
So EC-019's fit is asserted over every spec whose page fit is at least 2 mm.
That includes every cell between 2 mm and NFR-008's 4.8 mm book floor: those
fit, and FR-031 flags them. A spec whose page fit is under 2 mm (only a
freakishly small stored trim reaches that) is its own declared case. The cell
is exactly 2 mm, the drawing anchors at the usable area's left edge with its
top at top + band, it overflows right and down, and ``page.fits`` is
``False``. That is pinned separately, so neither side of the floor is vacuous.
"""

from __future__ import annotations

import dataclasses
import math
import random

from nonogram.clues import compute_clues
from nonogram.export.layout import (
    MIN_CELL_MM,
    CellCapPolicy,
    Layout,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_layout,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE

DPI = 300
PX_PER_MM = DPI / 25.4
HALF_PIXEL_MM = 0.5 / PX_PER_MM
STANDARD_CELL_MM = 7.5
BOOK_MIN_THIN_RULE_MM = 0.25

BOOK1 = PageSpec(
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

type ClueSet = tuple[tuple[int, ...], ...]


def _alternating(columns: int, rows: int) -> list[list[bool]]:
    """Every other cell filled in every line: the deepest gutters an extent can have."""
    return [[(row + column) % 2 == 0 for column in range(columns)] for row in range(rows)]


def _puzzle(rng: random.Random) -> tuple[ClueSet, ClueSet]:
    """A real clue set of a random extent in CON-011's range and a random clue depth."""
    columns, rows = rng.randint(MIN_SIZE, MAX_SIZE), rng.randint(MIN_SIZE, MAX_SIZE)
    if rng.random() < 0.25:
        grid = _alternating(columns, rows)
    else:
        density = rng.uniform(0.15, 0.85)
        grid = [[rng.random() < density for _ in range(columns)] for _ in range(rows)]
    clues = compute_clues(grid)
    return clues.rows, clues.columns


def _random_spec(rng: random.Random, *, cap: float | None = None) -> PageSpec:
    """Any stored trim and margins a book could hold, and a band, with a valid usable area."""
    while True:
        width = round(rng.uniform(100.0, 330.0), 3)
        height = round(rng.uniform(140.0, 430.0), 3)
        top, bottom = round(rng.uniform(0.0, 25.4), 3), round(rng.uniform(0.0, 25.4), 3)
        gutter, outside = round(rng.uniform(3.0, 30.0), 3), round(rng.uniform(3.0, 25.4), 3)
        band = round(rng.choice([0.0, 12.0, rng.uniform(0.0, 20.0)]), 3)
        if width - gutter - outside > 0 and height - top - bottom - band > 0:
            return PageSpec(
                width_mm=width,
                height_mm=height,
                top_mm=top,
                bottom_mm=bottom,
                gutter_mm=gutter,
                outside_mm=outside,
                band_mm=band,
                orientation=OrientationPolicy.PORTRAIT_ONLY,
                cell_cap=STANDARD_CELL_MM if cap is None else cap,
                min_thin_rule_mm=BOOK_MIN_THIN_RULE_MM,
                parity=rng.choice([PageParity.ODD, PageParity.EVEN]),
            )


def _depth(clue_set: ClueSet) -> int:
    return max(len(clue) for clue in clue_set)


def _expected_cell_mm(spec: PageSpec, rows: ClueSet, columns: ClueSet) -> tuple[float, float]:
    """FR-030 in mm: ``(page fit, cell)`` with the flat cap and the MIN_CELL_MM floor."""
    across = _depth(rows) + len(columns)
    down = _depth(columns) + len(rows)
    usable_width = spec.width_mm - spec.gutter_mm - spec.outside_mm
    usable_height = spec.height_mm - spec.top_mm - spec.bottom_mm - spec.band_mm
    fit = min(usable_width / across, usable_height / down)
    return fit, max(2.0, min(float(spec.cell_cap), fit))


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _every_x(layout: Layout) -> list[int]:
    return [line.position for line in layout.vertical_lines] + [
        line.start for line in layout.horizontal_lines
    ] + [line.end for line in layout.horizontal_lines] + [
        entry.center_x for entry in layout.clue_entries
    ]


def _every_y(layout: Layout) -> list[int]:
    return [line.position for line in layout.horizontal_lines] + [
        line.start for line in layout.vertical_lines
    ] + [line.end for line in layout.vertical_lines] + [
        entry.center_y for entry in layout.clue_entries
    ]


def test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell() -> None:
    """EC-019: for any extent, clue depth and stored trim/margins whose page fit is
    at least the 2 mm floor, the drawing is inside the usable area below the band
    and the cell never exceeds the 7.5 mm standard cell."""
    rng = random.Random(20260922)
    checked = below_book_floor = at_cap = 0
    for _ in range(1500):
        spec = _random_spec(rng)
        rows, columns = _puzzle(rng)
        fit, expected_cell = _expected_cell_mm(spec, rows, columns)
        if fit < MIN_CELL_MM:
            continue
        layout = compute_layout(rows, columns, spec)
        page = layout.page
        assert page is not None

        # The cell: FR-030's number, never above the standard cell.
        assert page.cell_mm <= STANDARD_CELL_MM
        assert abs(page.cell_mm - expected_cell) < 1e-6, (spec, page.cell_mm, expected_cell)

        # The page is the trim, at 300 DPI.
        assert abs(layout.width - spec.width_mm * PX_PER_MM) <= 0.5
        assert abs(layout.height - spec.height_mm * PX_PER_MM) <= 0.5

        # The usable area it reports is the trim minus its margins, within half a pixel.
        left_mm = spec.gutter_mm if spec.parity is PageParity.ODD else spec.outside_mm
        right_mm = spec.width_mm - (spec.outside_mm if spec.parity is PageParity.ODD else spec.gutter_mm)
        assert abs(_mm(page.usable_left) - left_mm) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(page.usable_right) - right_mm) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(page.usable_top) - spec.top_mm) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(page.usable_bottom) - (spec.height_mm - spec.bottom_mm)) <= HALF_PIXEL_MM + 1e-9

        # The drawing (grid, both gutters, every clue) lies inside the usable
        # area below the band, in whole device pixels, with no tolerance.
        assert page.fits
        xs, ys = _every_x(layout), _every_y(layout)
        assert page.usable_left <= min(xs) and max(xs) <= page.usable_right
        assert page.drawing_top <= min(ys) and max(ys) <= page.usable_bottom
        assert page.usable_top < page.drawing_top or spec.band_mm * PX_PER_MM < 0.5

        # The drawing is exactly as wide as its cells: n cells within a pixel of n x cell.
        across = layout.row_gutter_cells + layout.columns
        assert abs((page.drawing_right - page.drawing_left) - across * page.cell_mm * PX_PER_MM) <= 1

        checked += 1
        below_book_floor += page.cell_mm < 4.8
        at_cap += page.cell_mm == STANDARD_CELL_MM
    assert checked >= 1000, checked
    # Both regimes are exercised: held at the cap, and fitted below NFR-008's floor.
    assert at_cap >= 100, at_cap
    assert below_book_floor >= 100, below_book_floor


def test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_floor_cases() -> None:
    """EC-019's boundary: page fit under MIN_CELL_MM overflows, is reported, and never raises."""
    rng = random.Random(114)
    checked = 0
    for _ in range(300):
        rows, columns = _puzzle(rng)
        across = _depth(rows) + len(columns)
        # A trim whose usable width holds the drawing only below 2 mm a cell.
        usable_width = round(rng.uniform(0.2, 1.95) * across, 3)
        spec = PageSpec(
            width_mm=round(usable_width + 20.0, 3),
            height_mm=600.0,
            top_mm=10.0,
            bottom_mm=10.0,
            gutter_mm=12.0,
            outside_mm=8.0,
            band_mm=12.0,
            orientation=OrientationPolicy.PORTRAIT_ONLY,
            cell_cap=STANDARD_CELL_MM,
            min_thin_rule_mm=BOOK_MIN_THIN_RULE_MM,
            parity=rng.choice([PageParity.ODD, PageParity.EVEN]),
        )
        fit, _ = _expected_cell_mm(spec, rows, columns)
        assert fit < MIN_CELL_MM

        layout = compute_layout(rows, columns, spec)
        page = layout.page
        assert page is not None
        assert page.cell_mm == MIN_CELL_MM
        assert not page.fits
        assert page.drawing_left == page.usable_left, "anchored at the usable left edge"
        assert page.drawing_right > page.usable_right, "overflows to the right"
        assert abs(_mm(page.drawing_top) - (spec.top_mm + spec.band_mm)) <= HALF_PIXEL_MM + 1e-9
        checked += 1
    assert checked >= 300


def test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin() -> None:
    """ADR-0037/R2: for every cell in 4.0..7.5 mm under a book spec, thin >= 0.25 mm
    (>= 3 px), heavy == 2 x thin, on every line; the default spec's rule is unchanged."""
    rows = columns = tuple((1,) for _ in range(12))
    checked = 0
    for hundredths in range(400, 751):
        cap = hundredths / 100
        spec = dataclasses.replace(BOOK1, cell_cap=cap)
        layout = compute_layout(rows, columns, spec)
        assert layout.page is not None and layout.page.cell_mm == cap  # the cap binds

        assert layout.thin_rule >= 3
        assert _mm(layout.thin_rule) >= BOOK_MIN_THIN_RULE_MM
        assert layout.thick_rule == 2 * layout.thin_rule
        for line in layout.grid_lines:
            assert line.width == (layout.thick_rule if line.major else layout.thin_rule)
        checked += 1
    assert checked == 351

    # The default spec keeps cell / 30 (a 2 px thin rule at a ~6 mm cell, not 3).
    default = compute_layout(tuple((1,) for _ in range(30)), tuple((1,) for _ in range(30)))
    assert default.thin_rule == max(1, round(default.cell / 30))
    assert default.thin_rule < 3


def test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_pixels() -> None:
    """The strokes as drawn: pure black, and exactly as wide as the layout says.

    Measured off the rendered pixels, not read back from ``Layout``. A column
    of pixels crosses every horizontal rule inside the grid (between clue
    columns, away from any vertical line), and the runs of ink it meets are
    counted and measured.
    """
    from nonogram import export
    from nonogram.export import png

    rng = random.Random(37)
    checked = 0
    for cap in (4.0, 4.8, 5.5, 6.4, 7.0, 7.5):
        for parity in (PageParity.ODD, PageParity.EVEN):
            columns, rows = rng.randint(MIN_SIZE, 15), rng.randint(MIN_SIZE, 15)
            grid = [[False] * columns for _ in range(rows)]
            grid[0][0] = True
            clues = compute_clues(grid)
            spec = dataclasses.replace(BOOK1, cell_cap=cap, parity=parity)
            payload = export.ExportPayload(
                grid=grid, row_clues=clues.rows, column_clues=clues.columns, seed=1, mode="random"
            )
            image = png.render_image(payload, page_spec=spec)
            layout = compute_layout(clues.rows, clues.columns, spec)

            # Middle of the last column: no clue digit, no vertical line.
            xs = [line.position for line in layout.vertical_lines]
            probe_x = (xs[-2] + xs[-1]) // 2
            runs: list[tuple[int, tuple[int, int, int]]] = []
            run_colour: set[tuple[int, int, int]] = set()
            length = 0
            for y in range(layout.grid_top - layout.thick_rule, layout.grid_bottom + layout.thick_rule):
                pixel = image.getpixel((probe_x, y))
                if pixel != (255, 255, 255):
                    length += 1
                    run_colour.add(pixel)
                elif length:
                    runs.append((length, run_colour.pop() if len(run_colour) == 1 else (1, 1, 1)))
                    run_colour, length = set(), 0
            widths = [width for width, _ in runs]
            assert all(colour == (0, 0, 0) for _, colour in runs), "every rule is pure black"
            assert len(runs) == rows + 1
            majors = [line.major for line in layout.horizontal_lines]
            for width, major in zip(widths, majors, strict=True):
                assert width == (layout.thick_rule if major else layout.thin_rule)
                assert _mm(width) >= BOOK_MIN_THIN_RULE_MM
            checked += 1
    assert checked == 12


def test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent() -> None:
    """EC-022 (layout half): portrait, unrotated, and the top offset is top + band,
    for every extent 10..30 x 10..30, including the wide grids NFR-006 would turn."""
    rng = random.Random(22)
    specs = [BOOK1, dataclasses.replace(BOOK1, parity=PageParity.EVEN)] + [
        _random_spec(rng) for _ in range(3)
    ]
    checked = 0
    for spec in specs:
        expected_top_mm = spec.top_mm + spec.band_mm
        tops: set[int] = set()
        for columns in range(MIN_SIZE, MAX_SIZE + 1):
            for rows in range(MIN_SIZE, MAX_SIZE + 1):
                grid = _alternating(columns, rows) if (columns + rows) % 3 else [
                    [column == row % columns for column in range(columns)] for row in range(rows)
                ]
                clues = compute_clues(grid)
                layout = compute_layout(clues.rows, clues.columns, spec)
                page = layout.page
                assert page is not None

                assert layout.orientation == "portrait"
                # Unrotated: columns run across the page, rows down it.
                assert (layout.columns, layout.rows) == (columns, rows)
                assert len(layout.vertical_lines) == columns + 1
                assert len(layout.horizontal_lines) == rows + 1
                assert all(line.start < line.end for line in layout.grid_lines)
                assert abs(layout.width - spec.width_mm * PX_PER_MM) <= 0.5
                assert abs(layout.height - spec.height_mm * PX_PER_MM) <= 0.5

                assert abs(_mm(page.drawing_top) - expected_top_mm) <= HALF_PIXEL_MM + 1e-9
                assert min(line.start for line in layout.vertical_lines) == page.drawing_top
                tops.add(page.drawing_top)
                checked += 1
        assert len(tops) == 1, "the top edge never varies between puzzle pages of a book"

    assert checked == len(specs) * 21 * 21

    # The book's opt-out is real: some of these extents turn on A4.
    wide = compute_clues(_alternating(30, 10))
    assert compute_layout(wide.rows, wide.columns).orientation == "landscape"
    assert compute_layout(wide.rows, wide.columns, BOOK1).orientation == "portrait"


def test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity() -> None:
    """EC-032 (layout half): gutter on the binding side, drawing centred across the
    usable width, odd-minus-even left edge == gutter - outside, top edge identical."""
    rng = random.Random(32)
    checked = 0
    for _ in range(800):
        base = _random_spec(rng, cap=rng.choice([STANDARD_CELL_MM, round(rng.uniform(3.0, 10.0), 2)]))
        rows, columns = _puzzle(rng)
        fit, _ = _expected_cell_mm(base, rows, columns)
        if fit < MIN_CELL_MM:
            continue
        odd = compute_layout(rows, columns, dataclasses.replace(base, parity=PageParity.ODD))
        even = compute_layout(rows, columns, dataclasses.replace(base, parity=PageParity.EVEN))
        o, e = odd.page, even.page
        assert o is not None and e is not None

        # The gutter margin is on the binding side.
        assert abs(_mm(o.usable_left) - base.gutter_mm) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(odd.width - o.usable_right) - base.outside_mm) <= HALF_PIXEL_MM * 2 + 1e-9
        assert abs(_mm(e.usable_left) - base.outside_mm) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(even.width - e.usable_right) - base.gutter_mm) <= HALF_PIXEL_MM * 2 + 1e-9

        for layout, page, left_margin in ((odd, o, base.gutter_mm), (even, e, base.outside_mm)):
            # Centred on this page's usable width (both computed here in mm).
            usable_centre_mm = left_margin + (base.width_mm - base.gutter_mm - base.outside_mm) / 2
            drawing_centre_mm = _mm((page.drawing_left + page.drawing_right) / 2)
            assert abs(drawing_centre_mm - usable_centre_mm) <= HALF_PIXEL_MM + 1e-9

        # Parity moves the drawing sideways by gutter - outside, and nothing else.
        # Each page's edge is rounded to the pixel on its own, so the shift
        # between them is within one pixel (two half-pixel roundings) of the
        # physical gutter - outside.
        shift_mm = _mm(o.drawing_left - e.drawing_left)
        assert abs(shift_mm - (base.gutter_mm - base.outside_mm)) < 2 * HALF_PIXEL_MM
        assert o.drawing_top == e.drawing_top
        assert o.drawing_bottom == e.drawing_bottom
        assert o.cell_mm == e.cell_mm
        drawing_widths = (o.drawing_right - o.drawing_left, e.drawing_right - e.drawing_left)
        assert abs(drawing_widths[0] - drawing_widths[1]) <= 1
        usable_widths = (o.usable_right - o.usable_left, e.usable_right - e.usable_left)
        assert abs(usable_widths[0] - usable_widths[1]) <= 1
        assert [line.position for line in odd.horizontal_lines] == [
            line.position for line in even.horizontal_lines
        ]
        checked += 1
    assert checked >= 600, checked


def _independent_spec_is_valid(fields: dict[str, object]) -> bool:
    """PageSpec's invariant, written out again: finite numbers, a positive trim,
    non-negative margins and band, and a positive usable area."""
    numbers = [fields[name] for name in (
        "width_mm", "height_mm", "top_mm", "bottom_mm", "gutter_mm", "outside_mm", "band_mm"
    )]
    if not all(isinstance(n, float) and math.isfinite(n) for n in numbers):
        return False
    width, height, top, bottom, gutter, outside, band = numbers  # type: ignore[misc]
    return (
        width > 0
        and height > 0
        and min(top, bottom, gutter, outside, band) >= 0
        and width - gutter - outside > 0
        and height - top - bottom - band > 0
    )


def test_PropertyTest_PageSpec_ExistsExactlyWhenItsUsableAreaIsPositive() -> None:
    """The value object's invariant, as a property: a PageSpec constructs iff it is valid."""
    rng = random.Random(1140)
    specials = [math.nan, math.inf, -math.inf, 0.0, -1.0]
    accepted = refused = 0
    for _ in range(3000):
        def measure(low: float, high: float) -> float:
            return rng.choice(specials) if rng.random() < 0.03 else round(rng.uniform(low, high), 3)

        fields: dict[str, object] = {
            "width_mm": measure(-10.0, 300.0),
            "height_mm": measure(-10.0, 400.0),
            "top_mm": measure(-5.0, 150.0),
            "bottom_mm": measure(-5.0, 150.0),
            "gutter_mm": measure(-5.0, 150.0),
            "outside_mm": measure(-5.0, 150.0),
            "band_mm": measure(-5.0, 100.0),
            "orientation": OrientationPolicy.PORTRAIT_ONLY,
            "cell_cap": rng.choice([CellCapPolicy.COMFORT_CURVE, STANDARD_CELL_MM]),
            "min_thin_rule_mm": rng.choice([None, BOOK_MIN_THIN_RULE_MM]),
            "parity": rng.choice([PageParity.ODD, PageParity.EVEN]),
        }
        expected = _independent_spec_is_valid(fields)
        try:
            spec = PageSpec(**fields)  # type: ignore[arg-type]
        except ValueError:
            assert not expected, fields
            refused += 1
            continue
        assert expected, fields
        # A spec that exists can always be laid out, at any extent, without raising.
        layout = compute_layout(*_puzzle(rng), spec)
        assert layout.page is not None and layout.page.cell_mm >= MIN_CELL_MM
        accepted += 1
    assert accepted >= 300 and refused >= 300, (accepted, refused)
