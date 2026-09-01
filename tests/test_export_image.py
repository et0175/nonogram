"""COMP-007 tests: the print-ready renderers and the geometry behind them.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-028  TestExport_WritesPNG               -> test_export_writes_png*
    AC-029  TestExport_WritesSVG               -> test_export_writes_svg*
    AC-030  TestExport_RejectsUnverifiedPuzzle -> test_export_rejects_an_unverified_puzzle*
    AC-080  TestLayout_SmallGridTakesTheComfortCap
            -> test_a_small_grid_takes_the_comfort_cap
    AC-081  TestLayout_LargeGridIsPageFitBoundNotCapBound
            -> test_a_large_grid_is_page_fit_bound_not_cap_bound
    AC-082  TestLayout_CapComesFromLargerDimensionRegardlessOfOrientation
            -> test_the_cap_comes_from_the_larger_dimension_regardless_of_orientation
    AC-083  TestLayout_InterpolatesBetweenChosenCellSizes
            -> test_the_cap_interpolates_between_the_chosen_cell_sizes
    AC-099  TestPageOrientation_WideGridTurnsLandscapeAt660mm
            -> test_a_wide_grid_turns_the_page_to_landscape
    AC-100  TestPageOrientation_40x20GainsFortySevenPercentFromLandscape
            -> test_a_forty_by_twenty_gains_forty_seven_percent_from_landscape
    AC-101  TestPageOrientation_45x25GainsFortyFourPercentFromLandscape
            -> test_a_forty_five_by_twenty_five_gains_forty_four_percent_from_landscape
    AC-102  TestPageOrientation_TallGridKeepsPortraitAt491mm
            -> test_a_tall_grid_keeps_the_page_portrait
    AC-103  TestPageOrientation_SquareGridDefaultsPortraitBySmallMargin
            -> test_a_square_grid_defaults_to_portrait_by_a_small_margin
    AC-104  TestLayout_SameLargerDimensionDoesNotGuaranteeSameCellSize
            -> test_the_same_larger_dimension_does_not_guarantee_the_same_cell_size

AC-030 is INV-002's gate seen from the image formats. The gate itself is one
check in COMP-002 that all five renderers inherit (ADR-0007, guardrail G-5), and
``tests/test_export_json.py`` already pins it for JSON; what is added here is the
per-format instance the acceptance criterion actually names — export of an
unverified puzzle as PNG or SVG is refused, and the destination is left empty,
with no truncated image behind it.

The other thing these tests exist to hold down is the *negative* half of FR-011:
what a person prints is the **blank** grid. The solution belongs to FR-012's
JSON/CSV and to CARD-014's answer key, so several tests below assert not on what
was drawn but on what was not — every cell interior white, no filled rectangle
in the markup, and the same bytes out whether the payload carries the solution
grid or nothing at all.

Nothing here writes outside ``tmp_path``.
"""

from __future__ import annotations

import ast
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image

from nonogram import cli, export, orchestrator
from nonogram.clues import compute_clues
from nonogram.errors import ExportRejected
from nonogram.export import layout as layout_module
from nonogram.export import png, svg
from nonogram.export.layout import Layout, compute_layout
from nonogram.orchestrator import GenerationRequest, Puzzle, export_puzzle, generate
from nonogram.solver import MANY

# --------------------------------------------------------------------------
# Helpers — same notation as tests/test_orchestrator.py: ``█`` filled, ``·`` empty.
# --------------------------------------------------------------------------

_FILLED = "█"

_SVG_NS = "{http://www.w3.org/2000/svg}"

_WHITE = (255, 255, 255)


def _grid(*patterns: str) -> list[list[bool]]:
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


#: Exactly one solution (the same 2x2 the orchestrator and JSON tests pin on).
#:
#:     ██
#:     █·
UNIQUE = _grid("██", "█·")


def _puzzle(
    out: Path | None,
    *,
    grid: list[list[bool]] | None = None,
    solution_count: int | None = 1,
    formats: tuple[str, ...] = (export.PNG,),
    **request_fields: object,
) -> Puzzle:
    """A puzzle at the point the pipeline would hand it to the export step.

    Built by driving the aggregate the way :func:`generate` does — record a
    candidate, then report a verdict — so ``ready_for_export`` is only ever
    reached through INV-002's own transition, never written by hand.
    ``solution_count=None`` leaves the candidate unjudged, which is the "not
    ready" case AC-030 is about.
    """
    fields: dict[str, object] = {
        "mode": "random",
        "size": 2,
        "density": 50,
        "seed": 7,
        "export_formats": formats,
        "out": out,
    }
    fields.update(request_fields)
    request = GenerationRequest(**fields)  # type: ignore[arg-type]
    puzzle = Puzzle(request=request, seed=request.seed or 0)
    puzzle.record_candidate(grid if grid is not None else UNIQUE)
    if solution_count is not None:
        puzzle.confirm_uniqueness(solution_count)
    return puzzle


def _payload(grid: list[list[bool]]) -> export.ExportPayload:
    """The payload COMP-002 would build for ``grid`` (INV-001 clues included)."""
    puzzle_clues = compute_clues(grid)
    return export.ExportPayload(
        grid=grid,
        row_clues=puzzle_clues.rows,
        column_clues=puzzle_clues.columns,
        seed=7,
        mode="random",
    )


def _written(directory: Path) -> list[Path]:
    return sorted(directory.iterdir()) if directory.exists() else []


def _cell_centres(geometry: Layout) -> list[tuple[int, int]]:
    """The centre pixel of every *grid* cell — never a gutter box."""
    half = geometry.cell // 2
    return [
        (
            geometry.grid_left + column * geometry.cell + half,
            geometry.grid_top + row * geometry.cell + half,
        )
        for row in range(geometry.rows)
        for column in range(geometry.columns)
    ]


def _layout_for(grid: list[list[bool]]) -> Layout:
    """The geometry COMP-007 computes for ``grid``'s clues."""
    return compute_layout(*compute_clues(grid))


def _patterned(width: int, height: int) -> list[list[bool]]:
    """A ``width`` x ``height`` grid with a realistic clue depth.

    The every-third-cell diagonal: a fixed, readable pattern whose gutters are
    close to what a real puzzle at a middling density produces (four cells deep
    at 10x10, ten at 30x30), so NFR-005's tests measure the page a person would
    actually print rather than a degenerate one.
    """
    return [[(row + column) % 3 == 0 for column in range(width)] for row in range(height)]


def _cell_mm(geometry: Layout) -> float:
    """``geometry``'s cell edge as the physical measurement NFR-005 is about."""
    return geometry.cell / geometry.dpi * 25.4


def _assert_fits_printable_area(geometry: Layout) -> None:
    """The whole printed page sits inside A4's printable area (AC-080, AC-081).

    "The whole page" means the drawing *plus* the header band a titled sheet
    carries above it, which is what NFR-005 defines page fit over. Measuring the
    drawing alone is the measurement that let a cap raised to 7.0mm at 25 cells
    push 50 supported shapes off A4 with the suite green: those pages overran
    the sheet only once the band was added, so a check that stopped at
    ``geometry.height`` could not see it. The band is added for every format,
    not only the PDF, because all three renderers size their cell from one
    :func:`compute_layout` — see ``_fit_cell``.

    Since NFR-006 the sheet has two ways up, so the printable area is measured
    against the one this grid's shape is owed — landscape when the grid is
    wider than it is tall, portrait otherwise — derived here from the grid
    rather than read off ``geometry.orientation``, so that a page turned the
    wrong way is measured against the sheet it should have been printed on.

    The fit bound alone only catches HALF of "turned the wrong way", which is
    why the orientation itself is asserted below (cycle-1 F-002). A wrongly
    *landscape* page overruns the portrait sheet it was owed and is caught by
    the bound. A wrongly *portrait* page does not: ``_fit_cell`` shrinks the
    cell until the drawing fits the narrower sheet, so the drawing comes out
    SMALLER and sits comfortably inside the landscape bound it is measured
    against. Measured on 40x20, 45x25 and 30x10 with orientation forced
    portrait: every one passed the bound.
    """
    expected_orientation = (
        "landscape" if geometry.columns > geometry.rows else "portrait"
    )
    assert geometry.orientation == expected_orientation, (
        f"{geometry.columns}x{geometry.rows} printed {geometry.orientation}, "
        f"not the {expected_orientation} sheet NFR-006 owes it"
    )
    short_edge, long_edge = layout_module.PAGE_WIDTH_MM, layout_module.PAGE_HEIGHT_MM
    across, down = (
        (long_edge, short_edge) if geometry.columns > geometry.rows else (short_edge, long_edge)
    )
    printable_width = round(
        (across - 2 * layout_module.PAGE_MARGIN_MM) / 25.4 * layout_module.DPI
    )
    printable_height = round(
        (down - 2 * layout_module.PAGE_MARGIN_MM) / 25.4 * layout_module.DPI
    )
    band = layout_module.header_band(geometry)

    assert geometry.width - 2 * geometry.margin <= printable_width
    assert geometry.height - 2 * geometry.margin + band.height <= printable_height


#: A grid dense enough that a renderer leaking the solution would be obvious:
#: three quarters of its cells are filled.
DENSE = _grid("████", "███·", "██·█", "█·██")


# ==========================================================================
# export/layout.py — the shared geometry
# ==========================================================================


def test_the_layout_is_a_pure_function_of_the_clues() -> None:
    """Same clues in, same numbers out — the property that lets PNG, SVG and
    CARD-014's PDF draw one picture instead of three that drift."""
    clues = compute_clues(DENSE)

    first = compute_layout(clues.rows, clues.columns)
    second = compute_layout(clues.rows, clues.columns)

    assert first == second


def test_the_layout_never_sees_the_solution() -> None:
    """The structural reason a rendered page cannot reveal the answer.

    ``compute_layout`` takes clue sets and nothing else, so no filled-cell
    coordinate exists anywhere downstream of it for a renderer to draw. If a
    grid argument is ever added here, this is what fails.
    """
    clues = compute_clues(DENSE)

    from_clues_only = compute_layout(clues.rows, clues.columns)

    assert from_clues_only.rows == 4
    assert from_clues_only.columns == 4


def test_the_layout_takes_its_dimensions_from_the_clue_sets() -> None:
    rows = tuple((1,) for _ in range(7))
    columns = tuple((1,) for _ in range(12))

    geometry = compute_layout(rows, columns)

    assert (geometry.rows, geometry.columns) == (7, 12)
    assert len(geometry.horizontal_lines) == 8
    assert len(geometry.vertical_lines) == 13


def test_mismatched_clue_sets_are_a_pipeline_bug() -> None:
    with pytest.raises(ValueError, match="clue sets disagree"):
        compute_layout(((1,), (1,)), ())


def test_the_gutters_are_as_deep_as_the_longest_clue() -> None:
    """The whole point of deriving the gutter rather than fixing it: a puzzle
    whose rows never need more than two numbers does not carry a gutter sized
    for the worst case."""
    rows = ((1,), (1, 1), (1, 1, 1, 1))
    columns = ((3,), (3,), (3,))

    geometry = compute_layout(rows, columns)

    assert geometry.row_gutter_cells == 4
    assert geometry.column_gutter_cells == 1
    assert geometry.grid_left == geometry.margin + 4 * geometry.cell
    assert geometry.grid_top == geometry.margin + 1 * geometry.cell


def test_an_all_empty_line_still_gets_a_gutter_box() -> None:
    """``clues.encode_line`` marks an empty line ``(0,)`` (AC-013), so every
    clue occupies at least one box and the gutter is never zero-deep."""
    geometry = compute_layout(((0,),), ((0,),))

    assert geometry.row_gutter_cells == 1
    assert geometry.column_gutter_cells == 1
    assert [entry.value for entry in geometry.row_clues] == [0]


def test_every_fifth_grid_line_is_heavier() -> None:
    """The standard nonogram counting aid: heavy rules at 0, 5, 10 ... plus the
    far edge, so the frame closes even when the width is not a multiple of
    five."""
    geometry = compute_layout(
        tuple((1,) for _ in range(12)), tuple((1,) for _ in range(12))
    )

    heavy = [line.index for line in geometry.vertical_lines if line.major]

    assert heavy == [0, 5, 10, 12]
    assert all(line.width == geometry.thick_rule for line in geometry.vertical_lines if line.major)
    assert all(
        line.width == geometry.thin_rule
        for line in geometry.vertical_lines
        if not line.major
    )
    assert geometry.thick_rule > geometry.thin_rule


def test_the_heavy_rule_applies_to_both_axes() -> None:
    geometry = compute_layout(
        tuple((1,) for _ in range(10)), tuple((1,) for _ in range(10))
    )

    assert [line.index for line in geometry.horizontal_lines if line.major] == [0, 5, 10]


def test_grid_lines_span_the_gutters_too() -> None:
    """A vertical line continues up through the column-clue gutter, which is
    what makes a clue readable as belonging to its column."""
    geometry = compute_layout(((1, 1),), ((1,), (1,)))

    for line in geometry.vertical_lines:
        assert line.start == geometry.margin
        assert line.end == geometry.grid_bottom
    for line in geometry.horizontal_lines:
        assert line.start == geometry.margin
        assert line.end == geometry.grid_right


def test_row_clues_are_right_aligned_against_the_grid() -> None:
    """The last number of every row clue lands in the same gutter column — the
    one abutting the grid — which is how a printed nonogram is read."""
    geometry = compute_layout(((3,), (1, 1, 1)), ((1,), (1,), (1,)))

    last_of_each_row = [
        entry for entry in geometry.row_clues if entry.depth == geometry.row_gutter_cells - 1
    ]

    assert len(last_of_each_row) == 2
    assert {entry.center_x for entry in last_of_each_row} == {
        geometry.grid_left - geometry.cell + geometry.cell // 2
    }


def test_column_clues_are_bottom_aligned_against_the_grid() -> None:
    geometry = compute_layout(((1,), (1,), (1,)), ((3,), (1, 1, 1)))

    last_of_each_column = [
        entry
        for entry in geometry.column_clues
        if entry.depth == geometry.column_gutter_cells - 1
    ]

    assert len(last_of_each_column) == 2
    assert {entry.center_y for entry in last_of_each_column} == {
        geometry.grid_top - geometry.cell + geometry.cell // 2
    }


def test_every_clue_number_is_placed_exactly_once() -> None:
    clues = compute_clues(DENSE)

    geometry = compute_layout(clues.rows, clues.columns)

    assert len(geometry.row_clues) == sum(len(clue) for clue in clues.rows)
    assert len(geometry.column_clues) == sum(len(clue) for clue in clues.columns)
    assert len({(entry.center_x, entry.center_y) for entry in geometry.clue_entries}) == (
        len(geometry.clue_entries)
    )


def test_clue_boxes_sit_inside_the_page_margins() -> None:
    clues = compute_clues(DENSE)

    geometry = compute_layout(clues.rows, clues.columns)

    for entry in geometry.clue_entries:
        assert geometry.margin <= entry.center_x <= geometry.width - geometry.margin
        assert geometry.margin <= entry.center_y <= geometry.height - geometry.margin


# --------------------------------------------------------------------------
# The A4 / 300 DPI target and the cell clamp
# --------------------------------------------------------------------------


def test_a_typical_puzzle_fits_an_a4_sheet() -> None:
    """15x15 at the default clue depth: the size a user actually prints."""
    clues = compute_clues([[(row + column) % 3 == 0 for column in range(15)] for row in range(15)])

    geometry = compute_layout(clues.rows, clues.columns)

    assert geometry.width <= round(layout_module.PAGE_WIDTH_MM / 25.4 * layout_module.DPI)
    assert geometry.height <= round(layout_module.PAGE_HEIGHT_MM / 25.4 * layout_module.DPI)


def test_a_small_puzzle_is_not_blown_up_into_a_poster() -> None:
    """The cap: a cell stops getting easier to mark past a point and then just
    wastes paper, so a tiny grid gets a comfortable cell, not a quarter of the
    page. Below NFR-005's smallest decided size the curve is flat, so a 5x5 is
    capped at the 10-cell value rather than at an extrapolated one."""
    geometry = compute_layout(tuple((1,) for _ in range(5)), tuple((1,) for _ in range(5)))

    assert _cell_mm(geometry) <= 9.0
    assert _cell_mm(geometry) == pytest.approx(9.0, abs=0.2)


def test_the_largest_drawing_keeps_a_markable_cell() -> None:
    """The floor, and the one clamp still allowed to beat page fit (G-3).

    No supported puzzle reaches it — CON-011 stops at 30 cells a side, and the
    worst 30x30 still prints at about 4mm — so this pins it on the deliberately
    out-of-range drawing that does: 180 cells across is well past the ~92 at
    which page fit falls below 2mm. The layout holds the cell at the minimum
    rather than shrinking past the point where a pencil mark means anything, and
    lets the image outgrow A4 instead.
    """
    worst = tuple(tuple(1 for _ in range(60)) for _ in range(120))

    geometry = compute_layout(worst, worst)

    assert geometry.cell == round(layout_module.MIN_CELL_MM / 25.4 * layout_module.DPI)
    assert geometry.width > round(layout_module.PAGE_WIDTH_MM / 25.4 * layout_module.DPI)
    assert geometry.clue_font_size >= 8


# --------------------------------------------------------------------------
# NFR-005 — cell = min(comfort cap, page fit)
#
# The four criteria are split by WHICH TERM BINDS: AC-080/082/083 are the sizes
# where the cap is observable at all, AC-081 is where the page overrules it.
# Each names its expected millimetre value as a literal, deliberately — deriving
# it from ``layout.CELL_COMFORT_MM`` would follow that table wherever it went
# and assert nothing about where the decided values actually are.
# --------------------------------------------------------------------------


def test_a_small_grid_takes_the_comfort_cap() -> None:
    """AC-080. A 10x10's four-deep gutter still leaves the page room to spare,
    so the cap is what the printed cell measures: 9.0mm, not the 6.52mm a single
    flat cap used to hand every grid from 10x10 to 25x25 alike."""
    geometry = _layout_for(_patterned(10, 10))

    assert _cell_mm(geometry) == pytest.approx(9.0, abs=0.2)
    _assert_fits_printable_area(geometry)


def test_a_large_grid_is_page_fit_bound_not_cap_bound() -> None:
    """AC-081, and guardrail G-3's ceiling-not-floor rule where it bites.

    A 30x30 draws forty cells across once its clue gutter is counted, which is
    260mm of paper at the 6.5mm the cap allows, against the 186mm A4 prints. The
    cap is not a promise the format can keep at that size, so page fit overrules
    it — and the page still holds the whole drawing, which is the point.
    """
    geometry = _layout_for(_patterned(30, 30))

    assert _cell_mm(geometry) < 6.5
    _assert_fits_printable_area(geometry)


@pytest.mark.parametrize(
    ("width", "height"),
    [pytest.param(12, 10, id="landscape"), pytest.param(10, 12, id="portrait")],
)
def test_the_cap_comes_from_the_larger_dimension_regardless_of_orientation(
    width: int, height: int
) -> None:
    """AC-082. The cap is a function of ``max(width, height)``, so a 12x10 and a
    10x12 print the same cell — 12's 8.6mm, never 10's 9.0mm. Both reach
    ``compute_layout`` as clue sets and nothing else (G-4): the extent is
    derived from the clues, which is what keeps this independent of any
    rectangular ``(width, height)`` request.
    """
    geometry = _layout_for(_patterned(width, height))

    assert (geometry.columns, geometry.rows) == (width, height)
    assert _cell_mm(geometry) == pytest.approx(8.6, abs=0.2)
    _assert_fits_printable_area(geometry)


def test_the_cap_interpolates_between_the_chosen_cell_sizes() -> None:
    """AC-083. 13 is not one of the five decided sizes: it sits three fifths of
    the way from 10 (9.0mm) to 15 (8.0mm), so it prints at 8.4mm. The points
    were decided, the line between them is interpolation."""
    geometry = _layout_for(_patterned(13, 11))

    assert _cell_mm(geometry) == pytest.approx(9.0 - (13 - 10) / (15 - 10) * (9.0 - 8.0), abs=0.2)


# --------------------------------------------------------------------------
# NFR-006 — the sheet turns to match the grid
#
# Every figure below is a *page fit* measurement: the largest cell the sheet
# can take, with NFR-005's comfort cap out of the picture. That is the quantity
# turning the page actually moves, and the quantity the criteria were measured
# in. ``_page_fit_mm`` recomputes it here from NFR-005's own words and A4's own
# numbers rather than calling ``layout._fit_cell``, so a change to the module's
# page arithmetic has to disagree with a second implementation before these
# tests will follow it.
#
# Page fit depends on the clue gutter as well as the grid, so "a 40x20" is not
# by itself a page: each case names the gutter depths it was measured at, and
# ``_with_gutters`` builds a real grid that has exactly those. The depths are
# the ones an ordinary puzzle of that shape produces at about half density.
# --------------------------------------------------------------------------


def _with_gutters(
    width: int, height: int, row_runs: int, column_runs: int
) -> list[list[bool]]:
    """A ``width`` x ``height`` grid whose deepest clues are exactly that deep.

    A comb along the top row — every other cell filled, ``row_runs`` of them —
    gives row 0 exactly ``row_runs`` numbers and every column it touches
    exactly one. A second comb down column 0 does the same to that column
    without adding a run to any row it lands on, since each of those rows is
    otherwise empty. So the row gutter is ``row_runs`` deep, the column gutter
    ``column_runs``, and no other line is deeper than one.

    Needs ``2 * runs - 1`` cells to lay a comb in, which every case below has.
    """
    grid = [[False] * width for _ in range(height)]
    for run in range(row_runs):
        grid[0][2 * run] = True
    for run in range(column_runs):
        grid[2 * run][0] = True
    return grid


def _page_fit_mm(grid: list[list[bool]], *, orientation: str) -> float:
    """The largest cell A4 can take for ``grid``, that way up, cap ignored.

    NFR-005's page-fit term, written out from the requirement rather than
    called: A4 is 210 x 297 mm, 12 mm of margin comes off each of the four
    edges, 12 mm more of height is reserved for the header band, and the
    drawing that has to fit is the grid plus each gutter. Turning the sheet
    swaps which edge is which and nothing else (G-1).
    """
    row_clues, column_clues = compute_clues(grid)
    row_gutter = max(len(clue) for clue in row_clues)
    column_gutter = max(len(clue) for clue in column_clues)
    across_mm, down_mm = (297.0, 210.0) if orientation == "landscape" else (210.0, 297.0)
    printable_across = round((across_mm - 2 * 12.0) / 25.4 * 300)
    printable_down = round((down_mm - 2 * 12.0) / 25.4 * 300) - round(12.0 / 25.4 * 300)
    cell_px = min(
        printable_across // (row_gutter + len(column_clues)),
        printable_down // (column_gutter + len(row_clues)),
    )
    return cell_px / 300 * 25.4


def test_a_wide_grid_turns_the_page_to_landscape() -> None:
    """AC-099, and the shape FR-023's derivation makes routine.

    A 30x10 at an ordinary gutter depth fits 6.60mm of cell on a turned sheet
    against 4.49mm on a fixed portrait one — the page-fit measurement the
    criterion quotes.

    Two corrections to the criterion's own numbers, both recorded here rather
    than smoothed over, because they are the sort of thing a later reader will
    otherwise re-derive from scratch:

    * **6.60mm is the page fit, not what this grid prints.** 30x10's larger
      dimension is 30, so NFR-005 caps it at 6.5mm and the cell comes out at
      6.43mm (6.5mm truncated to a whole device pixel). This is the ceiling of
      EC-008 doing exactly its job — page fit stopped being the binding term —
      and asserting the criterion's 6.60mm on ``geometry.cell`` would mean
      lifting that ceiling. Both numbers are pinned below.
    * **2.29mm is not this grid's portrait figure**, it is the 60x10's, from
      the same measured set (NFR-006's rationale lists both shapes). A 30x10
      prints 4.49mm on a fixed portrait sheet. The 60x10 pair is asserted too,
      so the criterion's number stays covered by a test even though it belongs
      to the neighbouring shape.
    """
    grid = _with_gutters(30, 10, row_runs=11, column_runs=4)

    geometry = _layout_for(grid)

    assert geometry.orientation == "landscape"
    assert _page_fit_mm(grid, orientation="landscape") == pytest.approx(6.60, abs=0.01)
    assert _page_fit_mm(grid, orientation="portrait") == pytest.approx(4.49, abs=0.01)
    # The cap, not page fit, is what this particular shape ends up printing.
    assert _cell_mm(geometry) == pytest.approx(6.43, abs=0.01)
    assert _cell_mm(geometry) <= 6.5
    _assert_fits_printable_area(geometry)

    # Where the criterion's 2.29mm comes from: the 60x10 of the same measured
    # set, whose page fit the cap never touches.
    sixty = _with_gutters(60, 10, row_runs=19, column_runs=5)
    assert _page_fit_mm(sixty, orientation="portrait") == pytest.approx(2.29, abs=0.01)
    assert _page_fit_mm(sixty, orientation="landscape") == pytest.approx(3.39, abs=0.01)
    assert _cell_mm(_layout_for(sixty)) == pytest.approx(3.39, abs=0.01)


def test_a_forty_by_twenty_gains_forty_seven_percent_from_landscape() -> None:
    """AC-100. 3.39mm on a fixed portrait sheet, 5.00mm turned: the cell is not
    a little bigger, it is half again as big, and 40 is far enough past the
    comfort curve's last decided point that the cap never comes into it."""
    grid = _with_gutters(40, 20, row_runs=14, column_runs=8)

    geometry = _layout_for(grid)
    portrait = _page_fit_mm(grid, orientation="portrait")

    assert geometry.orientation == "landscape"
    assert portrait == pytest.approx(3.39, abs=0.01)
    assert _cell_mm(geometry) == pytest.approx(5.00, abs=0.01)
    assert _cell_mm(geometry) / portrait == pytest.approx(1.47, abs=0.01)
    _assert_fits_printable_area(geometry)


def test_a_forty_five_by_twenty_five_gains_forty_four_percent_from_landscape() -> None:
    """AC-101. The same win at a shape half again as large, so the gain is a
    property of turning the page and not of one lucky extent."""
    grid = _with_gutters(45, 25, row_runs=16, column_runs=9)

    geometry = _layout_for(grid)
    portrait = _page_fit_mm(grid, orientation="portrait")

    assert geometry.orientation == "landscape"
    assert portrait == pytest.approx(3.05, abs=0.01)
    assert _cell_mm(geometry) == pytest.approx(4.40, abs=0.01)
    assert _cell_mm(geometry) / portrait == pytest.approx(1.44, abs=0.01)
    _assert_fits_printable_area(geometry)


def test_a_tall_grid_keeps_the_page_portrait() -> None:
    """AC-102. The other half of "if and only if": a 20x40 is already on the
    sheet that suits it, and turning it would cost a third of the cell (4.91mm
    down to 3.22mm). A rule that turned every rectangle would pass AC-100 and
    fail here."""
    grid = _with_gutters(20, 40, row_runs=7, column_runs=13)

    geometry = _layout_for(grid)

    assert geometry.orientation == "portrait"
    assert _cell_mm(geometry) == pytest.approx(4.91, abs=0.01)
    assert _page_fit_mm(grid, orientation="landscape") == pytest.approx(3.22, abs=0.01)
    _assert_fits_printable_area(geometry)


def test_a_square_grid_defaults_to_portrait_by_a_small_margin() -> None:
    """AC-103, and guardrail G-3. A square grid has no longer side to lay along
    the sheet's longer axis, so the tie has to be broken by fiat — portrait,
    which is what every earlier version of this module did. It is not a free
    choice made to preserve behaviour: the drawing is the grid *plus* its row
    gutter, so a 30x30 draws wider than it is tall and portrait genuinely wins,
    4.40mm against 4.06mm. The margin is small, which is why it is asserted
    rather than assumed."""
    grid = _with_gutters(30, 30, row_runs=12, column_runs=12)

    geometry = _layout_for(grid)

    assert geometry.orientation == "portrait"
    assert _cell_mm(geometry) == pytest.approx(4.40, abs=0.01)
    assert _page_fit_mm(grid, orientation="landscape") == pytest.approx(4.06, abs=0.01)
    assert _page_fit_mm(grid, orientation="landscape") < _cell_mm(geometry)
    _assert_fits_printable_area(geometry)


def test_the_same_larger_dimension_does_not_guarantee_the_same_cell_size() -> None:
    """AC-104, and the reason NFR-005 and EC-008 had to be amended.

    A 40x20 and a 20x40 share ``max(width, height) = 40``. On a fixed portrait
    sheet they printed 3.39mm and 4.91mm — a 45% gap for the same max() — which
    is why "cell size is a function of max(width, height)" was ill-posed rather
    than merely imprecise. Turning the page narrows the gap to 5.00mm against
    4.91mm but does not close it, because page fit still depends on the clue
    gutter, and the gutter is a property of the puzzle's clues. So what EC-008
    guarantees is the ceiling both of them obey, not the equality neither does.
    """
    wide = _with_gutters(40, 20, row_runs=14, column_runs=8)
    tall = _with_gutters(20, 40, row_runs=7, column_runs=13)

    turned = _layout_for(wide)
    upright = _layout_for(tall)

    assert max(turned.columns, turned.rows) == max(upright.columns, upright.rows) == 40
    assert (turned.orientation, upright.orientation) == ("landscape", "portrait")
    assert _cell_mm(turned) == pytest.approx(5.00, abs=0.01)
    assert _cell_mm(upright) == pytest.approx(4.91, abs=0.01)
    assert turned.cell != upright.cell
    # Both still under the one thing EC-008 does promise: the cap for 40.
    for geometry in (turned, upright):
        assert _cell_mm(geometry) <= layout_module.comfort_cap_mm(40)
        # Inside the loop deliberately: at module scope this ran once on the
        # leaked loop variable, so `turned` — the whole point of the case —
        # was never checked against the printable area (cycle-1 F-004).
        _assert_fits_printable_area(geometry)


def test_the_layout_reports_its_physical_size() -> None:
    """Device pixels are meaningless without the resolution they are at; both
    renderers stamp this onto their output so a printer reproduces A4 sizing."""
    geometry = compute_layout(((1,),), ((1,),))

    assert geometry.dpi == layout_module.DPI
    assert geometry.width_inches == pytest.approx(geometry.width / layout_module.DPI)
    assert geometry.height_inches == pytest.approx(geometry.height / layout_module.DPI)


# ==========================================================================
# The registry — two more rows, and the CLI picking them up unedited
# ==========================================================================


def test_the_registry_knows_the_print_ready_formats() -> None:
    assert export.PNG in export.FORMATS
    assert export.SVG in export.FORMATS


@pytest.mark.parametrize(
    ("name", "extension", "renderer"),
    [
        pytest.param(export.PNG, ".png", png.render, id="png"),
        pytest.param(export.SVG, ".svg", svg.render, id="svg"),
    ],
)
def test_a_print_format_row_carries_its_extension_and_its_renderer(
    name: str, extension: str, renderer: object
) -> None:
    row = export.for_format(name)

    assert row.name == name
    assert row.extension == extension
    assert row.render is renderer


@pytest.mark.parametrize("name", [export.PNG, export.SVG])
def test_the_cli_accepts_the_new_formats_without_being_edited(name: str) -> None:
    """CARD-007's design claim, cashed in: ``--export``'s choices come from the
    registry, so registering PNG and SVG is the whole of the CLI change
    (guardrail G-2 — ``cli.py`` is not this card's to touch)."""
    args = cli.build_parser().parse_args(["generate", "--export", name])

    assert args.export_formats == [name]


# ==========================================================================
# AC-028 — TestExport_WritesPNG
# ==========================================================================


def test_export_writes_png(tmp_path: Path) -> None:
    """AC-028, end to end and unmocked.

    Pinned seed: at 10x10 / 50% density, seed 0's first candidate is already
    unique — the same pin the orchestrator and JSON tests document. Running the
    real pipeline is what makes "finalized, uniqueness-confirmed" the solver's
    word rather than the test's.
    """
    puzzle = generate(
        GenerationRequest(
            mode="random",
            size=10,
            density=50,
            seed=0,
            export_formats=(export.PNG,),
            out=tmp_path,
        )
    )
    assert puzzle.ready_for_export is True

    paths = export_puzzle(puzzle)

    assert len(paths) == 1
    written = paths[0]
    assert written.suffix == ".png"
    assert _written(tmp_path) == [written]

    with Image.open(written) as image:
        assert image.format == "PNG"
        geometry = _layout_for(puzzle.grid)
        assert image.size == (geometry.width, geometry.height)


def test_the_png_contains_the_clues(tmp_path: Path) -> None:
    """AC-028's "containing ... clues", as ink on the page: both gutters carry
    marks, and the corner block where they meet stays blank."""
    puzzle = _puzzle(tmp_path, grid=DENSE)
    geometry = _layout_for(DENSE)

    with Image.open(export_puzzle(puzzle)[0]) as image:
        pixels = image.convert("RGB")
        row_gutter = pixels.crop(
            (geometry.margin, geometry.grid_top, geometry.grid_left, geometry.grid_bottom)
        )
        column_gutter = pixels.crop(
            (geometry.grid_left, geometry.margin, geometry.grid_right, geometry.grid_top)
        )

    assert row_gutter.getbbox() is not None, "the row-clue gutter is blank"
    assert column_gutter.getbbox() is not None, "the column-clue gutter is blank"


def test_the_png_grid_is_blank(tmp_path: Path) -> None:
    """FR-011's negative half: what is printed is the puzzle, not the answer.

    ``DENSE`` is three-quarters filled, so a renderer that drew the solution
    would blacken most of these sample points.
    """
    puzzle = _puzzle(tmp_path, grid=DENSE)
    geometry = _layout_for(DENSE)

    with Image.open(export_puzzle(puzzle)[0]) as image:
        pixels = image.convert("RGB")
        centres = [pixels.getpixel(point) for point in _cell_centres(geometry)]

    assert centres == [_WHITE] * (geometry.rows * geometry.columns)


def test_the_png_records_its_print_resolution(tmp_path: Path) -> None:
    """Without the ``pHYs`` tag a viewer assumes 72 DPI and prints the page at
    four times its intended size."""
    with Image.open(export_puzzle(_puzzle(tmp_path))[0]) as image:
        horizontal, vertical = image.info["dpi"]

    assert (round(horizontal), round(vertical)) == (layout_module.DPI, layout_module.DPI)


# --------------------------------------------------------------------------
# CON-006 — the raster is exposed as an object, not only as a file
# --------------------------------------------------------------------------


def test_the_raster_is_available_without_a_filesystem() -> None:
    """CON-006, structurally.

    FR-016's PDF is *this* buffer saved a second time (``save_all`` /
    ``append_images``), which is what keeps PDF a renderer rather than a
    dependency decision. A module that only exposed "write a PNG here" would
    force CARD-014 to write a throwaway file and read it back, or to redraw the
    page against a second geometry that could drift from this one.
    """
    image = png.render_image(_payload(DENSE))

    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"
    geometry = _layout_for(DENSE)
    assert image.size == (geometry.width, geometry.height)


def test_the_written_png_is_the_exposed_raster(tmp_path: Path) -> None:
    """The file sink adds the resolution tag and nothing else — so what
    CARD-014 saves as a PDF page is the same picture the user's PNG shows."""
    payload = _payload(DENSE)
    path = png.write_png(payload, tmp_path / "puzzle.png")

    with Image.open(path) as saved:
        assert saved.convert("RGB").tobytes() == png.render_image(payload).tobytes()


def test_write_png_reports_where_it_wrote(tmp_path: Path) -> None:
    """A convenience for CARD-014's second sink, not for the registry — which
    dispatches through ``render`` and discards the return value."""
    destination = tmp_path / "puzzle.png"

    assert png.write_png(_payload(UNIQUE), destination) == destination
    assert png.render(_payload(UNIQUE), tmp_path / "again.png") is None


# ==========================================================================
# AC-029 — TestExport_WritesSVG
# ==========================================================================


def test_export_writes_svg(tmp_path: Path) -> None:
    """AC-029, end to end and unmocked, at the same pinned seed as AC-028."""
    puzzle = generate(
        GenerationRequest(
            mode="random",
            size=10,
            density=50,
            seed=0,
            export_formats=(export.SVG,),
            out=tmp_path,
        )
    )
    assert puzzle.ready_for_export is True

    paths = export_puzzle(puzzle)

    assert len(paths) == 1
    written = paths[0]
    assert written.suffix == ".svg"
    assert _written(tmp_path) == [written]

    root = ElementTree.fromstring(written.read_text(encoding="utf-8"))
    assert root.tag == f"{_SVG_NS}svg"


def test_the_svg_draws_the_grid_and_the_clues(tmp_path: Path) -> None:
    """AC-029's "containing the blank grid and clues", element by element."""
    puzzle = _puzzle(tmp_path, grid=DENSE, formats=(export.SVG,))
    geometry = _layout_for(DENSE)

    root = ElementTree.fromstring(
        export_puzzle(puzzle)[0].read_text(encoding="utf-8")
    )

    lines = root.iter(f"{_SVG_NS}line")
    texts = [element.text for element in root.iter(f"{_SVG_NS}text")]

    assert len(list(lines)) == len(geometry.grid_lines)
    assert texts == [str(entry.value) for entry in geometry.clue_entries]


def test_the_svg_grid_is_blank(tmp_path: Path) -> None:
    """FR-011's negative half again, in the vector output: the only filled
    shape in the document is the white sheet itself."""
    puzzle = _puzzle(tmp_path, grid=DENSE, formats=(export.SVG,))

    markup = export_puzzle(puzzle)[0].read_text(encoding="utf-8")
    root = ElementTree.fromstring(markup)

    rectangles = list(root.iter(f"{_SVG_NS}rect"))
    assert len(rectangles) == 1
    assert rectangles[0].get("fill") == svg.BACKGROUND
    assert svg.INK not in {rectangle.get("fill") for rectangle in rectangles}


def test_the_svg_heavy_rules_are_marked_as_such(tmp_path: Path) -> None:
    """The every-5th rule survives into the markup as both a stroke width and
    a name, so an SVG opened in an editor can be restyled by intent."""
    puzzle = _puzzle(tmp_path, grid=DENSE, formats=(export.SVG,))
    geometry = _layout_for(DENSE)

    root = ElementTree.fromstring(export_puzzle(puzzle)[0].read_text(encoding="utf-8"))
    major = [line for line in root.iter(f"{_SVG_NS}line") if line.get("class") == "major"]

    assert len(major) == sum(1 for line in geometry.grid_lines if line.major)
    assert {line.get("stroke-width") for line in major} == {str(geometry.thick_rule)}


def test_the_svg_declares_a_physical_size_over_a_pixel_viewbox() -> None:
    """A pixel ``width`` would be re-read at the consumer's own idea of a pixel
    (96/in, usually) and print at a third of the intended size."""
    geometry = _layout_for(DENSE)

    root = ElementTree.fromstring(svg.document(_payload(DENSE)))

    assert root.get("width", "").endswith("in")
    assert root.get("height", "").endswith("in")
    assert float(root.get("width", "0in").removesuffix("in")) == pytest.approx(
        geometry.width_inches, abs=1e-3
    )
    assert root.get("viewBox") == f"0 0 {geometry.width} {geometry.height}"


def test_the_svg_is_stdlib_generated_markup() -> None:
    """Guardrail G-4 / ADR-0006: SVG is XML text this package writes itself.

    Asserted against the module's *imports* rather than its text, so the
    docstring is free to explain which libraries were declined and why without
    tripping its own check. The allowed set is the stdlib plus this package —
    ADR-0006's baseline is closed, and Pillow and NumPy are the only two names
    on it, neither of which the vector renderer has any use for.
    """
    tree = ast.parse(Path(svg.__file__ or "").read_text(encoding="utf-8"))

    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert imported <= {"__future__", "pathlib", "typing", "xml", "nonogram"}


def test_the_svg_document_is_built_without_touching_the_filesystem() -> None:
    """``document`` is separable from ``render``, the same split
    ``json_export`` makes: the markup is assertable on its own."""
    markup = svg.document(_payload(UNIQUE))

    assert markup.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert markup.rstrip().endswith("</svg>")


# ==========================================================================
# Neither renderer reads the solution
# ==========================================================================


@pytest.mark.parametrize(
    "render_output",
    [
        pytest.param(lambda payload: png.render_image(payload).tobytes(), id="png"),
        pytest.param(svg.document, id="svg"),
    ],
)
def test_the_output_does_not_depend_on_the_solution_grid(
    render_output: Callable[[export.ExportPayload], object],
) -> None:
    """The strongest form of "the page is blank": byte-identical output for a
    payload whose grid is the real solution and one whose grid is empty.

    Both renderers reach only ``row_clues``/``column_clues``, so the solution
    is not merely omitted from the drawing — it is never read.
    """
    clues = compute_clues(DENSE)
    with_solution = export.ExportPayload(
        grid=DENSE,
        row_clues=clues.rows,
        column_clues=clues.columns,
        seed=7,
        mode="random",
    )
    without_solution = export.ExportPayload(
        grid=[],
        row_clues=clues.rows,
        column_clues=clues.columns,
        seed=7,
        mode="random",
    )

    assert render_output(with_solution) == render_output(without_solution)


# ==========================================================================
# AC-030 — TestExport_RejectsUnverifiedPuzzle, for the image formats
# ==========================================================================


@pytest.mark.parametrize("name", [export.PNG, export.SVG])
def test_export_rejects_an_unverified_puzzle(name: str, tmp_path: Path) -> None:
    """AC-030 / INV-002. A candidate the solver has not judged is not
    exportable as an image either, and nothing is written on the way to finding
    that out — no zero-byte file, no truncated image, nothing to clean up."""
    destination = tmp_path / "out"
    puzzle = _puzzle(destination, solution_count=None, formats=(name,))

    with pytest.raises(ExportRejected, match="not ready for export"):
        export_puzzle(puzzle)

    assert _written(destination) == []


@pytest.mark.parametrize("name", [export.PNG, export.SVG])
@pytest.mark.parametrize(
    "solution_count",
    [pytest.param(0, id="no-solutions"), pytest.param(MANY, id="many-solutions")],
)
def test_export_rejects_an_image_the_solver_did_not_call_unique(
    name: str, solution_count: int, tmp_path: Path
) -> None:
    """INV-002 is about *exactly* one solution: a candidate with none and one
    with many are both refused, on the solver's number alone."""
    destination = tmp_path / "out"
    puzzle = _puzzle(destination, solution_count=solution_count, formats=(name,))

    with pytest.raises(ExportRejected):
        export_puzzle(puzzle)

    assert _written(destination) == []


def test_a_rejected_multi_format_export_writes_none_of_the_formats(
    tmp_path: Path,
) -> None:
    """The gate is consulted once, before the first renderer runs, so a refused
    export cannot leave a partial set of files behind."""
    destination = tmp_path / "out"
    puzzle = _puzzle(
        destination,
        solution_count=None,
        formats=(export.PNG, export.SVG, export.JSON),
    )

    with pytest.raises(ExportRejected):
        export_puzzle(puzzle)

    assert _written(destination) == []


@pytest.mark.parametrize("name", [export.PNG, export.SVG])
def test_a_rejected_image_export_reaches_the_user_as_exit_code_five(
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-030 as the user meets it: a documented refusal and an exit code, not
    a traceback and not a half-written image."""
    unready = _puzzle(tmp_path, solution_count=None, formats=(name,))
    monkeypatch.setattr(orchestrator, "generate", lambda request: unready)

    exit_code = cli.main(
        [
            "generate",
            "--size",
            "10",
            "--density",
            "50",
            "--export",
            name,
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.EXPORT_REJECTED
    assert "not ready for export" in capsys.readouterr().err
    assert _written(tmp_path) == []


def test_the_image_renderers_are_not_a_second_gate() -> None:
    """Guardrail G-5, as source.

    INV-002 has one enforcement point (COMP-002, ADR-0007). A renderer that
    re-checked readiness would be the second one that rule exists to prevent —
    and the payload it is handed carries no readiness flag at all, which is
    what makes that structural rather than a convention.
    """
    for module in (png, svg, layout_module):
        source = Path(module.__file__ or "").read_text(encoding="utf-8")
        for forbidden in ("ready_for_export", "ExportRejected"):
            assert f"{forbidden}(" not in source and f".{forbidden}" not in source


# ==========================================================================
# Both formats through the shared write-to---out plumbing (CARD-007)
# ==========================================================================


def test_one_puzzle_in_both_print_formats_shares_a_filename_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--export png --export svg`` is one puzzle in two formats, not two
    differently-named files."""
    monkeypatch.setattr(export, "default_stem", lambda mode, **kwargs: "puzzle")

    paths = export_puzzle(_puzzle(tmp_path, formats=(export.PNG, export.SVG)))

    assert [path.suffix for path in paths] == [".png", ".svg"]
    assert len({path.stem for path in paths}) == 1
    assert _written(tmp_path) == sorted(paths)


def test_the_cli_writes_an_image_and_reports_the_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """COMP-001 -> COMP-002 -> COMP-007, as a user runs it."""
    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "random",
            "--size",
            "10",
            "--density",
            "50",
            "--seed",
            "42",
            "--export",
            "png",
            "--export",
            "svg",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.OK
    written = _written(tmp_path)
    assert [path.suffix for path in written] == [".png", ".svg"]
    out = capsys.readouterr().out
    assert all(str(path) in out for path in written)
