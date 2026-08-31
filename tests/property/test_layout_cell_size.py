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
from nonogram.export.layout import compute_layout

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
    """EC-008's first half, over every shape CON-011 supports.

    Three puzzles per shape — a random-density one, the deepest gutter the
    shape allows and the shallowest — so the corpus spans both terms of the
    ``min()`` at every one of the 441 supported extents, square and not.
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
            ):
                geometry = compute_layout(*compute_clues(grid))
                cap = expected[max(width, height)]
                printed = _cell_mm(geometry.cell)

                assert printed <= cap, f"{width}x{height} printed {printed}mm over a {cap}mm cap"
                cases += 1
                if printed > cap - _ONE_PIXEL_MM:
                    at_the_cap += 1
                else:
                    under_the_cap += 1

    assert cases >= 3 * 21 * 21
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
