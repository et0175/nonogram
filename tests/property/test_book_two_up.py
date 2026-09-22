"""CARD-125: the two-up page's standing properties, over seeded corpora (FR-040).

    EC-028      PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea
        -> test_PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea
    ADR-0037/R2 PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin
                (CARD-114's property, two-up cases added here as a sibling so
                ``tests/property/test_book_layout.py`` stays untouched)
        -> test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up
    PairLayout's own invariant (the None-vs-pair verdict is exactly the rule)
        -> test_PropertyTest_BookTwoUp_PairsExactlyWhenTheRuleSaysSo

How the expectations are independent
------------------------------------
The expected shared cell is FR-040's definition written out again here in
floating-point millimetres: min(cap, (trim height − top − bottom − 2 × band) /
(both drawings' rows), usable width / each drawing's columns), with each
drawing's rows and columns counted from the clues' own lengths. It shares no
helper, no exact-fraction arithmetic and no pixel rounding with ``layout``.
Cases within a millionth of a millimetre of the 7.0 mm threshold are skipped
for the verdict comparison (float against exact), and counted, so the skip
cannot silently swallow the corpus.

No ``hypothesis`` (CLAUDE.md): stdlib ``random.Random`` at fixed seeds, each
test asserting its own minimum case counts for both verdicts.
"""

from __future__ import annotations

import dataclasses
import random

from nonogram.clues import compute_clues
from nonogram.export.layout import (
    Layout,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_pair_layout,
    header_band,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE

DPI = 300
PX_PER_MM = DPI / 25.4
HALF_PIXEL_MM = 0.5 / PX_PER_MM
STANDARD_CELL_MM = 7.5
TWO_UP_MINIMUM_MM = 7.0
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
type Puzzle = tuple[ClueSet, ClueSet]


def _puzzle(rng: random.Random) -> Puzzle:
    """A real clue set, 10..30 a side, biased toward the small sides that can pair."""
    def side() -> int:
        return rng.randint(MIN_SIZE, 16) if rng.random() < 0.7 else rng.randint(MIN_SIZE, MAX_SIZE)

    columns, rows = side(), side()
    if rng.random() < 0.2:
        grid = [[(row + column) % 2 == 0 for column in range(columns)] for row in range(rows)]
    else:
        density = rng.uniform(0.2, 0.9)
        grid = [[rng.random() < density for _ in range(columns)] for _ in range(rows)]
    clues = compute_clues(grid)
    return clues.rows, clues.columns


def _random_spec(rng: random.Random) -> PageSpec:
    """Any stored trim and margins a book could hold, Book 1 among them, with a 12 mm band."""
    if rng.random() < 0.3:
        return dataclasses.replace(BOOK1, parity=rng.choice([PageParity.ODD, PageParity.EVEN]))
    while True:
        width = round(rng.uniform(150.0, 330.0), 3)
        height = round(rng.uniform(200.0, 430.0), 3)
        top, bottom = round(rng.uniform(0.0, 25.4), 3), round(rng.uniform(0.0, 25.4), 3)
        gutter, outside = round(rng.uniform(3.0, 30.0), 3), round(rng.uniform(3.0, 25.4), 3)
        if width - gutter - outside > 0 and height - top - bottom - 12.0 > 0:
            return PageSpec(
                width_mm=width,
                height_mm=height,
                top_mm=top,
                bottom_mm=bottom,
                gutter_mm=gutter,
                outside_mm=outside,
                band_mm=12.0,
                orientation=OrientationPolicy.PORTRAIT_ONLY,
                cell_cap=STANDARD_CELL_MM,
                min_thin_rule_mm=BOOK_MIN_THIN_RULE_MM,
                parity=rng.choice([PageParity.ODD, PageParity.EVEN]),
            )


def _depth(clue_set: ClueSet) -> int:
    return max(len(clue) for clue in clue_set)


def _expected_shared_cell_mm(spec: PageSpec, first: Puzzle, second: Puzzle) -> float:
    """FR-040 in mm: the largest cell, capped, at which both fit with one band each."""
    down = sum(_depth(columns) + len(rows) for rows, columns in (first, second))
    widest = max(_depth(rows) + len(columns) for rows, columns in (first, second))
    height_for_drawings = spec.height_mm - spec.top_mm - spec.bottom_mm - 2 * spec.band_mm
    usable_width = spec.width_mm - spec.gutter_mm - spec.outside_mm
    return min(float(spec.cell_cap), height_for_drawings / down, usable_width / widest)


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _every_x(layout: Layout) -> list[int]:
    return (
        [line.position for line in layout.vertical_lines]
        + [line.start for line in layout.horizontal_lines]
        + [line.end for line in layout.horizontal_lines]
        + [entry.center_x for entry in layout.clue_entries]
    )


def _every_y(layout: Layout) -> list[int]:
    return (
        [line.position for line in layout.horizontal_lines]
        + [line.start for line in layout.vertical_lines]
        + [line.end for line in layout.vertical_lines]
        + [entry.center_y for entry in layout.clue_entries]
    )


def test_PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea() -> None:
    """EC-028: for any two puzzles of 10..30 a side, any clue depths and any stored
    trim and margins, a two-up page's shared cell is in [7.0, 7.5] mm, both slots
    print at it, both drawings with their bands lie inside the usable area without
    overlapping, and a pair whose largest fitting cell is below 7.0 mm is None."""
    rng = random.Random(20260922125)
    paired = declined = near_threshold = at_cap = 0
    for _ in range(3000):
        spec = _random_spec(rng)
        first, second = _puzzle(rng), _puzzle(rng)
        expected = _expected_shared_cell_mm(spec, first, second)
        pair = compute_pair_layout(first, second, spec)

        if abs(expected - TWO_UP_MINIMUM_MM) < 1e-6:
            near_threshold += 1
            continue
        if expected < TWO_UP_MINIMUM_MM:
            assert pair is None, (spec, expected)
            declined += 1
            continue
        assert pair is not None, (spec, expected)
        paired += 1

        upper, lower = pair.upper.page, pair.lower.page
        assert upper is not None and lower is not None

        # One shared cell, in [7.0, 7.5], and it is FR-040's number.
        assert TWO_UP_MINIMUM_MM <= pair.cell_mm <= STANDARD_CELL_MM
        assert upper.cell_mm == lower.cell_mm == pair.cell_mm
        assert abs(pair.cell_mm - expected) < 1e-6, (spec, pair.cell_mm, expected)
        assert pair.upper.thin_rule == pair.lower.thin_rule
        at_cap += pair.cell_mm == STANDARD_CELL_MM

        # The earlier puzzle is on top, in the order given.
        assert (pair.upper.rows, pair.upper.columns) == (len(first[0]), len(first[1]))
        assert (pair.lower.rows, pair.lower.columns) == (len(second[0]), len(second[1]))

        # Both on the page's trim and parity.
        for slot in (pair.upper, pair.lower):
            assert slot.page is not None and slot.page.parity is spec.parity
            assert abs(slot.width - spec.width_mm * PX_PER_MM) <= 0.5
            assert abs(slot.height - spec.height_mm * PX_PER_MM) <= 0.5

        # The usable area: the upper slot starts at the top margin, the lower one
        # ends at the bottom margin, both span the page's usable width.
        left_mm = spec.gutter_mm if spec.parity is PageParity.ODD else spec.outside_mm
        right_mm = left_mm + spec.width_mm - spec.gutter_mm - spec.outside_mm
        for slot_page in (upper, lower):
            assert abs(_mm(slot_page.usable_left) - left_mm) <= HALF_PIXEL_MM + 1e-9
            assert abs(_mm(slot_page.usable_right) - right_mm) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(upper.usable_top) - spec.top_mm) <= HALF_PIXEL_MM + 1e-9
        assert abs(_mm(lower.usable_bottom) - (spec.height_mm - spec.bottom_mm)) <= HALF_PIXEL_MM + 1e-9

        # The upper drawing's top is the single page's fixed row (FR-032).
        assert abs(_mm(upper.drawing_top) - (spec.top_mm + spec.band_mm)) <= HALF_PIXEL_MM + 1e-9

        # Each band is 12 mm and sits above its own drawing; the slots touch, never overlap.
        for slot in (pair.upper, pair.lower):
            band = header_band(slot)
            assert slot.page is not None
            assert band.height == slot.page.drawing_top - slot.page.usable_top
            assert abs(_mm(band.height) - spec.band_mm) <= 2 * HALF_PIXEL_MM + 1e-9
        assert upper.usable_bottom == lower.usable_top
        assert upper.drawing_bottom <= lower.usable_top < lower.drawing_top

        # Every drawn coordinate of each slot lies inside that slot, in whole pixels.
        for slot in (pair.upper, pair.lower):
            assert slot.page is not None and slot.page.fits
            xs, ys = _every_x(slot), _every_y(slot)
            assert slot.page.usable_left <= min(xs) and max(xs) <= slot.page.usable_right
            assert slot.page.drawing_top <= min(ys) and max(ys) <= slot.page.usable_bottom
            # Centred across the usable width (FR-032), within a pixel.
            spare_left = slot.page.drawing_left - slot.page.usable_left
            spare_right = slot.page.usable_right - slot.page.drawing_right
            assert abs(spare_left - spare_right) <= 2
    assert paired >= 500, paired
    assert declined >= 500, declined
    assert at_cap >= 100, at_cap
    assert near_threshold <= 5, near_threshold


def test_PropertyTest_BookTwoUp_PairsExactlyWhenTheRuleSaysSo() -> None:
    """The verdict is the rule, in either order: a pair is formed iff its cell >= 7.0
    mm, and swapping the two puzzles changes the slots, never the cell or the verdict."""
    rng = random.Random(125)
    checked = paired = 0
    for _ in range(1500):
        spec = _random_spec(rng)
        first, second = _puzzle(rng), _puzzle(rng)
        forward = compute_pair_layout(first, second, spec)
        backward = compute_pair_layout(second, first, spec)
        assert (forward is None) == (backward is None)
        if forward is not None and backward is not None:
            assert forward.cell_mm == backward.cell_mm
            for a, b in ((forward.upper, backward.lower), (forward.lower, backward.upper)):
                assert (a.rows, a.columns) == (b.rows, b.columns)
                # Same puzzle, same cell: the same drawing, only moved down or up.
                assert (a.page is not None) and (b.page is not None)
                assert a.page.drawing_left == b.page.drawing_left
                assert a.page.drawing_right == b.page.drawing_right
                assert abs(
                    (a.page.drawing_bottom - a.page.drawing_top)
                    - (b.page.drawing_bottom - b.page.drawing_top)
                ) <= 1
            paired += 1
        checked += 1
    assert checked == 1500
    assert paired >= 250, paired


def test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up() -> None:
    """ADR-0037/R2 on two-up pages: for every shared cell in 7.0..7.5 mm, both slots'
    thin rules are >= 0.25 mm (>= 3 px), heavy == 2 x thin, on every line, with the
    every-5th and outer-border rules heavy."""
    ten: Puzzle = (tuple((1,) for _ in range(10)), tuple((1,) for _ in range(10)))
    checked = 0
    for hundredths in range(700, 751):
        cap = hundredths / 100
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = dataclasses.replace(BOOK1, cell_cap=cap, parity=parity)
            pair = compute_pair_layout(ten, ten, spec)
            assert pair is not None and pair.cell_mm == cap  # the cap binds

            for slot in (pair.upper, pair.lower):
                assert slot.thin_rule >= 3
                assert _mm(slot.thin_rule) >= BOOK_MIN_THIN_RULE_MM
                assert slot.thick_rule == 2 * slot.thin_rule
                for line in slot.grid_lines:
                    last = slot.columns if line in slot.vertical_lines else slot.rows
                    assert line.major == (line.index % 5 == 0 or line.index == last)
                    assert line.width == (slot.thick_rule if line.major else slot.thin_rule)
            checked += 1
    assert checked == 102
