"""EC-008 — PropertyTest_Layout_CellSizeNeverExceedsComfortCap (NFR-005).

NFR-005 sizes a printed cell as ``min(comfort_cap(max(width, height)),
page_fit)``. The standing property that rule has to keep true is deliberately
*not* "cell size declines as the grid grows": page fit depends on the clue
gutter, which is a property of a puzzle's clues rather than of its dimensions,
so a 25x25 with one filled cell genuinely prints a larger cell than a 20x20
checkerboard. Stating it over the cap instead keeps it true and still pins the
thing that was decided:

1. **The ceiling holds.** For every supported grid — every shape in
   CON-011's 10..30 band, not only the square ones — the printed cell is at
   most the comfort cap for that grid's *larger* dimension.
2. **The cap itself declines.** Independently of any puzzle, the cap is a
   non-increasing function of the larger dimension across the whole range.
   Half 1 alone would pass trivially on a cap that jumped around, or on one
   that returned a metre for everything.
3. **The page still holds the page.** The other half of the ``min()`` — the
   one AC-080 and AC-081 both state in their ``then`` and neither of their
   examples measured — over the *same* corpus as half 1: grid, plus both clue
   gutters, plus the header band a titled sheet carries above them, inside a
   sheet of A4. A cap raised without this is a cap that prints off the paper,
   which is exactly what happened first time round: sized on the drawing
   alone, 50 shapes in this corpus overran A4 once the band was added, none of
   which had under the flat 6.5mm cap the new rule replaced. Halves 1 and 2
   were green throughout — a ceiling is only half of ``min()``, and the other
   half needs asserting too or the first one is licence to grow.

Both halves are checked against an *independent* reading of NFR-005's five
chosen values, spelled out below as literals. A test that derived its
expectation from ``layout.CELL_COMFORT_MM`` would follow that table wherever it
went and assert nothing about where the decided values are; the module's
constants are pinned against these literals once, in the first test, and
everything else is built from the literals.

No ``hypothesis`` (CLAUDE.md's test policy): the corpus is built with stdlib
``random.Random`` from a fixed seed, and every test asserts a minimum case
count so it cannot silently shrink.
"""

from __future__ import annotations

import random

import pytest

from nonogram.clues import compute_clues
from nonogram.export import layout
from nonogram.export.layout import Layout, compute_layout

SEED = 20260831

#: NFR-005's chosen values, as literals: the cell edge in millimetres decided
#: for a grid whose larger dimension is that many cells.
CHOSEN: tuple[tuple[int, float], ...] = (
    (10, 9.0),
    (15, 8.0),
    (20, 7.5),
    (25, 7.0),
    (30, 6.5),
)

#: CON-011's supported band, named here for the same reason as the values.
MIN_SUPPORTED = 10
MAX_SUPPORTED = 30

#: A4 portrait in millimetres (ISO 216), as literals for the same reason the
#: chosen cell sizes are literals: a test that read ``layout.PAGE_WIDTH_MM``
#: would follow the module onto A5 without noticing.
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0

#: How close two millimetre measurements have to be to count as the same
#: number. One device pixel at 300 DPI is ~0.085mm; the layout truncates the
#: cap to whole pixels, so a printed cell can sit up to one pixel *below* its
#: cap and never above it.
_ONE_PIXEL_MM = 25.4 / layout.DPI


def _expected_cap_mm() -> dict[int, float]:
    """NFR-005's curve, read independently of the module under test.

    Built by *accumulation* — walk each segment cell by cell, adding the
    per-cell step — rather than by the parametric "fraction of the way along"
    form :func:`layout.comfort_cap_mm` uses, so the two implementations can
    disagree about an endpoint or an off-by-one instead of sharing the mistake.
    """
    table = {CHOSEN[0][0]: CHOSEN[0][1]}
    for (left_cells, left_mm), (right_cells, right_mm) in zip(CHOSEN, CHOSEN[1:], strict=False):
        step = (right_mm - left_mm) / (right_cells - left_cells)
        for offset in range(1, right_cells - left_cells + 1):
            table[left_cells + offset] = left_mm + offset * step
    return table


def _cell_mm(cell_px: int) -> float:
    """A cell size in device pixels as the physical measurement NFR-005 is about."""
    return cell_px / layout.DPI * 25.4


def _random_grid(width: int, height: int, rng: random.Random) -> list[list[bool]]:
    """A grid at a random density — an ordinary puzzle's clue depth."""
    density = rng.uniform(0.2, 0.6)
    return [[rng.random() < density for _ in range(width)] for _ in range(height)]


def _checkerboard(width: int, height: int) -> list[list[bool]]:
    """The deepest gutter a grid of this shape can have: every clue is all 1s,
    so the drawing is about half as wide again as the grid and page fit is as
    hostile to the cap as the format allows."""
    return [[(row + column) % 2 == 0 for column in range(width)] for row in range(height)]


def _sparse(width: int, height: int) -> list[list[bool]]:
    """The shallowest gutter: one filled cell, so every clue is one number and
    page fit is as generous as it ever gets. This is where the cap binds."""
    grid = [[False] * width for _ in range(height)]
    grid[0][0] = True
    return grid


def _alternating_rows(width: int, height: int) -> list[list[bool]]:
    """Rows alternately full and empty: the *tallest* drawing a shape allows.

    Every row clue is one number and every column clue is ``ceil(height / 2)``
    of them, so the row gutter is 1 cell and the column gutter is half the
    height — a drawing that grows down while staying as narrow as the grid.
    This is the regime in which page fit's *height* term binds most often, and
    the shape that broke first was a 10x25 of exactly this form.

    It is **not** the only such regime, and this docstring claimed it was until
    cycle 2 measured it. Decisively: remove the band reservation and run
    :func:`_assert_the_page_fits_a4` over only the three *pre-existing* patterns
    (``_random_grid``, ``_checkerboard``, ``_sparse``) and **61** cases still
    fail — 58 checkerboard plus 3 random — the first at 10x25 checkerboard. This
    pattern strengthens the corpus; it is not what makes the assertion capable
    of catching the regression.

    (Counting how often the band reservation changes the cell, per pattern over
    441 extents: alternating-rows 111, checkerboard 58, random 3, sparse 0. That
    is a different quantity from *how often page fit's height term binds*, which
    is larger; earlier revisions of this docstring conflated the two.)

    The distinction is load-bearing. The false version invited a maintainer to
    scope :func:`_assert_the_page_fits_a4` to this pattern alone and delete 61
    real witnesses, restoring exactly the blindness that let the regression
    ship. Assert the page fit on every case the corpus generates.

    (The crossover, corrected: A4 prints 186mm across against 273mm down, less
    the 12mm now reserved for the band — 261mm — so a drawing must be about
    **1.40x** taller than wide before height is the smaller quotient. The 1.5x
    previously stated was computed from the pre-reservation height.)
    """
    return [[row % 2 == 0 for _ in range(width)] for row in range(height)]


def _assert_the_page_fits_a4(geometry: Layout, *, label: str) -> None:
    """The whole printed page — drawing plus header band — lands on A4.

    The band is measured with :func:`layout.header_band`, the same call the PDF
    exporter makes, rather than re-derived from :data:`layout.HEADER_BAND_MM`:
    what has to fit is the page a renderer actually produces, so the band that
    is asserted must be the band that is drawn.
    """
    band = layout.header_band(geometry)
    page_width_px = round(A4_WIDTH_MM / 25.4 * layout.DPI)
    page_height_px = round(A4_HEIGHT_MM / 25.4 * layout.DPI)

    assert geometry.width <= page_width_px, (
        f"{label}: {geometry.width}px wide overruns A4's {page_width_px}px"
    )
    assert geometry.height + band.height <= page_height_px, (
        f"{label}: {geometry.height}px of drawing plus a {band.height}px band "
        f"overruns A4's {page_height_px}px"
    )


def test_the_module_encodes_the_chosen_values_and_nothing_else() -> None:
    """The one place the literals above and the module's constants are tied
    together. Everything else in this file reads the literals."""
    assert layout.CELL_COMFORT_MM == CHOSEN
    assert layout.MAX_CELL_MM == 6.5
    assert layout.MIN_CELL_MM == 2.0


def test_the_cap_is_non_increasing_across_the_whole_supported_range() -> None:
    """EC-008's second half, checked without a puzzle in sight.

    Every integer from 10 to 30 inclusive, plus the flat runs on either side:
    below the first decided size and above the last there is nothing to
    interpolate between, so the curve holds its end value rather than
    extrapolating a number nobody decided.
    """
    expected = _expected_cap_mm()
    cells = list(range(1, 61))

    caps = [layout.comfort_cap_mm(count) for count in cells]

    assert len(cells) >= 60
    for count, cap in zip(cells, caps, strict=True):
        if count < MIN_SUPPORTED:
            assert cap == pytest.approx(CHOSEN[0][1]), f"below the range at {count}"
        elif count > MAX_SUPPORTED:
            assert cap == pytest.approx(CHOSEN[-1][1]), f"above the range at {count}"
        else:
            assert cap == pytest.approx(expected[count]), f"off the curve at {count}"
    for smaller, larger in zip(caps, caps[1:], strict=False):
        assert larger <= smaller + 1e-12, "the cap grew with the grid"


def test_the_five_chosen_sizes_are_on_the_curve_exactly() -> None:
    """Interpolation is for the sizes in between; the decided points are the
    decided points, and a curve that missed them would still be monotone."""
    for cells, millimetres in CHOSEN:
        assert layout.comfort_cap_mm(cells) == pytest.approx(millimetres)


def test_no_supported_puzzle_prints_a_cell_larger_than_its_cap() -> None:
    """EC-008's first and third halves, over every shape CON-011 supports.

    Four puzzles per shape — a random-density one, the deepest gutter the shape
    allows, the shallowest, and the *tallest* — so the corpus spans both terms
    of the ``min()`` at every one of the 441 supported extents, square and not,
    and both axes of the page-fit term.

    Every case carries two assertions, not one. ``printed <= cap`` is EC-008 as
    written; ``page fits A4`` is the clause AC-080 and AC-081 both end on, and
    the one that was going unmeasured while the cap was being raised. They fail
    in opposite directions — a cell too large for the paper passes the first
    and fails the second — which is the whole reason both belong on the same
    corpus rather than on two corpora chosen to suit each.
    """
    rng = random.Random(SEED)
    expected = _expected_cap_mm()
    cases = 0
    at_the_cap = 0
    under_the_cap = 0

    for width in range(MIN_SUPPORTED, MAX_SUPPORTED + 1):
        for height in range(MIN_SUPPORTED, MAX_SUPPORTED + 1):
            for grid in (
                _random_grid(width, height, rng),
                _checkerboard(width, height),
                _sparse(width, height),
                _alternating_rows(width, height),
            ):
                geometry = compute_layout(*compute_clues(grid))
                cap = expected[max(width, height)]
                printed = _cell_mm(geometry.cell)

                assert printed <= cap, f"{width}x{height} printed {printed}mm over a {cap}mm cap"
                _assert_the_page_fits_a4(geometry, label=f"{width}x{height}")
                cases += 1
                if printed > cap - _ONE_PIXEL_MM:
                    at_the_cap += 1
                else:
                    under_the_cap += 1

    assert cases >= 4 * 21 * 21
    # A ceiling nothing ever reaches would satisfy the assertion above just as
    # well as the real rule, and so would one nothing ever falls below. Both
    # sides of the ``min()`` must actually be observed to bind.
    assert at_the_cap >= 100, "the cap never bound — the property would be vacuous"
    assert under_the_cap >= 100, "page fit never bound — the cap is acting as a target"


def test_the_cap_ignores_the_gutter_that_page_fit_is_made_of() -> None:
    """The two terms read different things off the same puzzle, and this is the
    difference that makes ``_fit_cell`` take both.

    Two 20x20 puzzles: one whose clues are a single number per line, one whose
    clues are ten. They share a comfort cap, because the cap is a function of
    the grid; they do not share a printed cell, because the gutter is part of
    the drawing page fit has to hold.
    """
    shallow = compute_layout(*compute_clues(_sparse(20, 20)))
    deep = compute_layout(*compute_clues(_checkerboard(20, 20)))

    assert shallow.row_gutter_cells < deep.row_gutter_cells
    assert _cell_mm(deep.cell) < _cell_mm(shallow.cell)
    for geometry in (shallow, deep):
        assert _cell_mm(geometry.cell) <= _expected_cap_mm()[20]
