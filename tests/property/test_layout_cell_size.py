"""Two standing properties of the printed page:

* EC-008 — PropertyTest_Layout_CellSizeNeverExceedsComfortCap (NFR-005);
* EC-010 — PropertyTest_PageOrientation_LargerCellWinsTiesToPortrait
  (NFR-006).

They share a file because they share a corpus and a subject: EC-010 chooses the
sheet, EC-008 bounds the cell that is then fitted to it, and neither statement
is checkable on square grids alone.

NFR-005 sizes a printed cell as ``min(comfort_cap(max(width, height)),
page_fit)``. The standing property that rule has to keep true is deliberately
*not* "cell size declines as the grid grows": page fit depends on the clue
gutter, which is a property of a puzzle's clues rather than of its dimensions,
so a 25x25 with one filled cell genuinely prints a larger cell than a 20x20
checkerboard. It is not "the same larger dimension gives the same cell" either
— a 40x20 and a 20x40 print at 5.00mm and 4.91mm even after NFR-006 has turned
the first one's sheet. Stating it over the cap instead keeps it true and still
pins the thing that was decided:

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
   sheet of A4 *held the way EC-010 turned it*. A cap raised without this is a
   cap that prints off the paper, which is exactly what happened first time
   round: sized on the drawing alone, 50 shapes in this corpus overran A4 once
   the band was added, none of which had under the flat 6.5mm cap the new rule
   replaced. Halves 1 and 2 were green throughout — a ceiling is only half of
   ``min()``, and the other half needs asserting too or the first one is
   licence to grow.
4. **The sheet is whichever way up prints the larger cell.** EC-010: over the
   same 441 extents at the same four clue patterns, the orientation chosen is
   the one of portrait and landscape whose fitted cell is larger, and portrait
   when the two are equal. Checked by laying each puzzle out on *both* sheets
   with :func:`_independent_cell_px` — NFR-005's whole formula, written out
   here from A4's own numbers and the chosen cap values — and comparing, never
   by asking ``layout`` which sheet it picked or by reading ``width > height``
   off the grid, which is the superseded rule and disagrees with this one on
   398 of the 1764 cases below.

Halves 1-3 are checked against an *independent* reading of NFR-005's five
chosen values, spelled out below as literals, and half 4 against an independent
reading of the whole ``min(cap, page_fit)`` formula built from them. A test
that derived its expectation from ``layout.CELL_COMFORT_MM`` would follow that
table wherever it went and assert nothing about where the decided values are;
the module's constants are pinned against these literals once, in the first
test, and everything else is built from the literals.

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

#: A4's two edges in millimetres (ISO 216), as literals for the same reason the
#: chosen cell sizes are literals: a test that read ``layout.PAGE_WIDTH_MM``
#: would follow the module onto A5 without noticing. Which edge is the width
#: depends on how the sheet is turned — see :func:`_expected_orientation` and
#: :func:`_assert_the_page_fits_a4`.
A4_SHORT_EDGE_MM = 210.0
A4_LONG_EDGE_MM = 297.0

#: The blank border kept on all four sides, the strip a titled page reserves
#: above the drawing, and the cell-size floor — all in millimetres, and all
#: literals for the same reason as A4's edges: :func:`_independent_cell_px`
#: below is NFR-005's formula written out, and a formula that read the module's
#: constants would follow the module rather than check it.
PAGE_MARGIN_MM = 12.0
HEADER_BAND_MM = 12.0
FLOOR_MM = 2.0

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
    (``_random_grid``, ``_checkerboard``, ``_sparse``) and **235** cases still
    fail — 151 checkerboard, 74 random and 10 sparse — the first at 10x25
    checkerboard. This pattern strengthens the corpus; it is not what makes the
    assertion capable of catching the regression.

    (Counting how often the band reservation changes the cell, per pattern over
    441 extents: checkerboard 151, alternating-rows 118, random 74, sparse 10 —
    353 of 1764 cases, by at most 0.508mm. That is a different quantity from
    *how often page fit's height term binds*, which is larger; earlier
    revisions of this docstring conflated the two. All four counts moved at
    CARD-034 and ``_sparse``'s rose from zero: a landscape sheet has only 174mm
    of printable height once the band is reserved, so the band's claim bites on
    far more of the corpus than it did when every page was portrait.)

    The distinction is load-bearing. The false version invited a maintainer to
    scope :func:`_assert_the_page_fits_a4` to this pattern alone and delete 235
    real witnesses, restoring exactly the blindness that let the regression
    ship. Assert the page fit on every case the corpus generates.

    (The crossover, per orientation: a portrait sheet prints 186mm across
    against 273mm down, less the 12mm reserved for the band — 261mm — so a
    drawing must be about **1.40x** taller than wide before height is the
    smaller quotient. A landscape sheet prints 273mm across against 174mm
    down, so there the crossover is about **0.64x** and the height term binds
    on most drawings, not on a tall minority.)
    """
    return [[row % 2 == 0 for _ in range(width)] for row in range(height)]


def _gutters(grid: list[list[bool]]) -> tuple[int, int]:
    """How deep this grid's two clue gutters are, in clue boxes."""
    row_clues, column_clues = compute_clues(grid)
    return (
        max(len(clue) for clue in row_clues),
        max(len(clue) for clue in column_clues),
    )


def _independent_cell_px(
    grid: list[list[bool]], orientation: str, *, reserved_mm: float = HEADER_BAND_MM
) -> int:
    """NFR-005's printed cell for ``grid`` on a sheet held that way up.

    The whole formula, written out from the requirement and the literals above
    rather than called: A4 is 210 x 297 mm, 12 mm of margin comes off each of
    the four edges, 12 mm more of height is reserved for the header band, the
    drawing that has to fit is the grid plus each gutter, and the result is
    held under the comfort cap for the grid's larger dimension and over the
    2 mm floor. Turning the sheet swaps which edge is which and nothing else.

    This is the oracle EC-010 is checked against, so it must not consult the
    thing under test. It takes the orientation as an argument and has no
    opinion about which one a puzzle gets — that is exactly what makes it usable
    twice per puzzle, once per sheet, to say which sheet *should* have won.
    """
    row_gutter, column_gutter = _gutters(grid)
    height, width = len(grid), len(grid[0])
    across_mm, down_mm = (
        (A4_LONG_EDGE_MM, A4_SHORT_EDGE_MM)
        if orientation == "landscape"
        else (A4_SHORT_EDGE_MM, A4_LONG_EDGE_MM)
    )
    printable_across = round((across_mm - 2 * PAGE_MARGIN_MM) / 25.4 * layout.DPI)
    printable_down = round((down_mm - 2 * PAGE_MARGIN_MM) / 25.4 * layout.DPI) - round(
        reserved_mm / 25.4 * layout.DPI
    )
    page_fit = min(
        printable_across // (row_gutter + width),
        printable_down // (column_gutter + height),
    )
    cap = int(_expected_cap_mm()[max(width, height)] / 25.4 * layout.DPI)
    return max(round(FLOOR_MM / 25.4 * layout.DPI), min(cap, page_fit))


def _expected_orientation(grid: list[list[bool]]) -> str:
    """EC-010's rule, read independently of the module under test.

    Lay the puzzle out on both sheets and keep the one with the larger cell;
    portrait when they are equal. Deliberately *not* ``layout._orientation_for``
    and deliberately not ``width > height`` either — the first would agree with
    the implementation however it was written, and the second is the superseded
    shape rule, which disagrees with this one on 398 of the 1764 cases the
    sweeps below generate.
    """
    upright = _independent_cell_px(grid, "portrait")
    turned = _independent_cell_px(grid, "landscape")
    return "landscape" if turned > upright else "portrait"


def _sheet_px(orientation: str) -> tuple[int, int]:
    """A4's width and height in device pixels, held that way up."""
    if orientation == "landscape":
        long_edge, short_edge = A4_LONG_EDGE_MM, A4_SHORT_EDGE_MM
        return round(long_edge / 25.4 * layout.DPI), round(short_edge / 25.4 * layout.DPI)
    return (
        round(A4_SHORT_EDGE_MM / 25.4 * layout.DPI),
        round(A4_LONG_EDGE_MM / 25.4 * layout.DPI),
    )


def _assert_the_page_fits_a4(geometry: Layout, *, owed: str, label: str) -> None:
    """The whole printed page — drawing plus header band — lands on A4.

    The band is measured with :func:`layout.header_band`, the same call the PDF
    exporter makes, rather than re-derived from :data:`layout.HEADER_BAND_MM`:
    what has to fit is the page a renderer actually produces, so the band that
    is asserted must be the band that is drawn.

    Since NFR-006 the sheet is not always the same way up, so the two bounds
    are not always 210mm and 297mm. They are still *exactly two numbers per
    case*, taken from the sheet ``owed`` — which the caller reads off
    :func:`_expected_orientation`, never off ``geometry.orientation``, and
    never as the larger of the two edges either way, which would pass on a page
    turned the wrong way round.
    """
    band = layout.header_band(geometry)
    orientation = owed
    page_width_px, page_height_px = _sheet_px(orientation)

    assert geometry.width <= page_width_px, (
        f"{label}: {geometry.width}px wide overruns {orientation} A4's {page_width_px}px"
    )
    assert geometry.height + band.height <= page_height_px, (
        f"{label}: {geometry.height}px of drawing plus a {band.height}px band "
        f"overruns {orientation} A4's {page_height_px}px"
    )


def test_the_module_encodes_the_chosen_values_and_nothing_else() -> None:
    """The one place the literals above and the module's constants are tied
    together. Everything else in this file reads the literals."""
    assert layout.CELL_COMFORT_MM == CHOSEN
    assert layout.MAX_CELL_MM == 6.5
    assert layout.MIN_CELL_MM == FLOOR_MM
    # The three page numbers :func:`_independent_cell_px` re-derives NFR-005
    # from. Tied down here for the same reason as the cap curve: the oracle has
    # to be measuring the same sheet as the module, or it is measuring nothing.
    assert (layout.PAGE_WIDTH_MM, layout.PAGE_HEIGHT_MM) == (
        A4_SHORT_EDGE_MM,
        A4_LONG_EDGE_MM,
    )
    assert layout.PAGE_MARGIN_MM == PAGE_MARGIN_MM
    assert layout.HEADER_BAND_MM == HEADER_BAND_MM


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
                _assert_the_page_fits_a4(
                    geometry,
                    owed=_expected_orientation(grid),
                    label=f"{width}x{height}",
                )
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


def test_the_sheet_is_whichever_way_up_prints_the_larger_cell() -> None:
    """EC-010 — PropertyTest_PageOrientation_LargerCellWinsTiesToPortrait.

    The sweep runs every one of CON-011's 441 extents at all four clue
    patterns, rather than the handful of measured examples the acceptance
    criteria name, because EC-010 is a statement about every supported puzzle
    and because those examples were chosen to be legible, not extreme.

    How this avoids asserting the implementation against itself
    -----------------------------------------------------------
    The property is not "the orientation equals X" for some X this test knows
    in advance — under this rule there is no such X, since the answer depends
    on the clue gutters as much as on the extent. It is "the chosen sheet is
    the one that prints the larger cell". So the expectation is computed by
    laying the *same* puzzle out on *both* sheets and comparing the two cells:
    :func:`_independent_cell_px` is NFR-005's formula written out from A4's own
    numbers and the chosen cap values, so what the assertion compares is the
    orientation CHOICE against a second implementation of CELL SIZE — two
    different functions, which is what keeps it a real check rather than a
    tautology.

    The four patterns are the point of the test rather than padding. Every one
    of these puzzles has the same grid extent as its three siblings with a
    wildly different *drawing* extent — ``_sparse`` draws barely wider than its
    grid, ``_checkerboard`` about half as wide again, ``_alternating_rows`` far
    taller than its grid is — and the last assertions below use that: they
    require the corpus to keep containing the cases that tell this rule apart
    from the shape rule it replaced (``landscape iff width > height``), and the
    extents whose four puzzles do not all land on the same sheet, which is the
    half of EC-010 that says orientation is not a function of ``(width,
    height)`` at all.
    """
    rng = random.Random(SEED)
    landscape = portrait = 0
    ties = tie_on_a_wide_grid = 0
    shape_rule_disagrees = 0
    sheets_by_extent: dict[tuple[int, int], set[str]] = {}

    for width in range(MIN_SUPPORTED, MAX_SUPPORTED + 1):
        for height in range(MIN_SUPPORTED, MAX_SUPPORTED + 1):
            for grid in (
                _random_grid(width, height, rng),
                _checkerboard(width, height),
                _sparse(width, height),
                _alternating_rows(width, height),
            ):
                geometry = compute_layout(*compute_clues(grid))
                upright = _independent_cell_px(grid, "portrait")
                turned = _independent_cell_px(grid, "landscape")
                expected = "landscape" if turned > upright else "portrait"

                assert geometry.orientation == expected, (
                    f"{width}x{height} printed {geometry.orientation} at "
                    f"{geometry.cell}px, but portrait fits {upright}px and "
                    f"landscape {turned}px, so it is owed {expected}"
                )
                assert geometry.cell == max(upright, turned), (
                    f"{width}x{height} printed {geometry.cell}px, not the "
                    f"{max(upright, turned)}px the better of the two sheets takes"
                )
                if geometry.orientation == "landscape":
                    landscape += 1
                else:
                    portrait += 1
                if upright == turned:
                    ties += 1
                    if width > height:
                        tie_on_a_wide_grid += 1
                if (width > height) != (geometry.orientation == "landscape"):
                    shape_rule_disagrees += 1
                sheets_by_extent.setdefault((width, height), set()).add(geometry.orientation)

    assert landscape + portrait == 4 * 21 * 21
    # Both outcomes have to be observed, or "the larger cell wins" would be
    # satisfied by a constant. Measured: 446 landscape, 1318 portrait.
    assert landscape >= 300, "nothing turned — the corpus cannot see the rule work"
    assert portrait >= 1000, "everything turned"
    # The tie clause is not a corner case: wherever the comfort cap binds on
    # both sheets the two cells are equal by construction. Measured: 443 ties,
    # 279 of them on grids the superseded shape rule would have turned — which
    # is what makes "ties go to portrait" an assertion with witnesses rather
    # than a sentence.
    assert ties >= 200, "no puzzle ever tied — the tie-break is untested"
    assert tie_on_a_wide_grid >= 100, (
        "every tie was on a tall or square grid, so nothing here distinguishes "
        "'ties go to portrait' from 'ties go to the grid's shape'"
    )
    # The superseded rule and this one disagree on 398 of these 1764 cases.
    # Those are the only witnesses that tell the two apart, so the corpus must
    # not silently stop containing them.
    assert shape_rule_disagrees >= 300, (
        "the shape rule 'landscape iff width > height' agreed with this one "
        "everywhere — the corpus can no longer tell the two apart"
    )
    # EC-010's second half: two grids of identical extent can print on
    # differently turned sheets when their gutters differ. Measured: 152 of the
    # 441 extents split across their four puzzles.
    split_extents = sum(1 for sheets in sheets_by_extent.values() if len(sheets) > 1)
    assert split_extents >= 100, (
        "every extent put all four of its puzzles on the same sheet — the "
        "corpus cannot show that orientation is not a function of (width, height)"
    )


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
