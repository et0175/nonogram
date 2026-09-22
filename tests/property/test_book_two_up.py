"""CARD-125: the two-up page's standing properties, over seeded corpora (FR-040).

    EC-028      PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea
        -> test_PropertyTest_BookTwoUp_SharedCellInRangeAndDrawingsFitUsableArea
    ADR-0037/R2 PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin
                (CARD-114's property, two-up cases added here as a sibling so
                ``tests/property/test_book_layout.py`` stays untouched)
        -> test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up
           (the cap binds: one 10x10 pair over every cap in 7.00..7.50)
        -> test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up_fitted
           (the *height fit* binds: cells strictly below the cap, varied shapes,
           both parities, over a seeded corpus)
        -> test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up_pixels
           ("black", measured off rendered pixels the way CARD-114's ``_pixels``
           test measures it, for both slots of a pair)
    PairLayout's own invariant (the None-vs-pair verdict is exactly the rule)
        -> test_PropertyTest_BookTwoUp_PairsExactlyWhenTheRuleSaysSo
    Each slot is compute_layout's placed page at the shared cell (no second assembly)
        -> test_PropertyTest_BookTwoUp_UpperSlotIsTheSinglePageAtTheSharedCell

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

The stroke tests need pairs whose shared cell comes from the *height fit*
rather than from the cap, at a known value. ``_spec_fitting_cell`` inverts the
same formula: given the two puzzles and a wanted cell, it returns a trim whose
usable height is exactly ``2 x band + (both drawings' rows) x cell`` and whose
usable width is wide enough that the width term cannot bind. So a wanted cell
under the cap is the height fit, one over the cap leaves the cap binding, and
which of the three terms decides is chosen by the test rather than hoped for.

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
    compute_layout,
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
# The lower slot's last heavy rule straddles the bottom-margin line; see
# ``_spec_fitting_cell``. Well above any heavy rule at a 7.0..7.5 mm cell.
_FITTED_BOTTOM_FLOOR_MM = 2.0

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


def _spec_fitting_cell(
    rng: random.Random,
    first: Puzzle,
    second: Puzzle,
    *,
    cell_mm: float,
    parity: PageParity,
) -> PageSpec:
    """A trim whose *height fit* for this pair is exactly ``cell_mm``.

    FR-040's formula inverted, in millimetres, with no help from ``layout``:
    the usable height is set to ``2 x band + (both drawings' rows) x cell_mm``,
    so ``height_for_drawings / down`` is ``cell_mm`` exactly, and the trim is
    made wide enough (a random 1.0..1.4 of what the widest drawing needs at
    that cell) that the width term is never the smallest of the three. The
    margins and the band are random within a book's range. Hand it a cell below
    the cap and the height fit decides the shared cell; hand it one above the
    cap and the cap decides.

    The bottom margin is floored at ``_FITTED_BOTTOM_FLOOR_MM``. The lower
    slot's last heavy rule is centred on the bottom-margin line, so a margin
    thinner than half a heavy rule (~0.25 mm) would leave that rule clipped by
    the canvas edge: a pixel probe reading it back would measure a short run,
    or index off the image, and report a stroke-width failure that is the
    trim's fault rather than the layout's. Two millimetres is ~23 px at 300
    DPI, far more than any heavy rule at a 7.0..7.5 mm cell, so every rule both
    slots draw has whole paper under it. Trims with a near-zero bottom margin
    are still exercised — ``_random_spec`` draws one from 0.0 mm up, and the
    geometry properties that do not read pixels run over that corpus.
    """
    down = sum(_depth(columns) + len(rows) for rows, columns in (first, second))
    widest = max(_depth(rows) + len(columns) for rows, columns in (first, second))
    top = round(rng.uniform(0.0, 20.0), 3)
    bottom = round(rng.uniform(_FITTED_BOTTOM_FLOOR_MM, 20.0), 3)
    gutter, outside = round(rng.uniform(6.0, 25.0), 3), round(rng.uniform(3.0, 20.0), 3)
    band = round(rng.choice([12.0, 12.0, rng.uniform(4.0, 18.0)]), 3)
    return PageSpec(
        width_mm=round(gutter + outside + widest * cell_mm * rng.uniform(1.0, 1.4), 6),
        height_mm=round(top + bottom + 2 * band + down * cell_mm, 6),
        top_mm=top,
        bottom_mm=bottom,
        gutter_mm=gutter,
        outside_mm=outside,
        band_mm=band,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=BOOK_MIN_THIN_RULE_MM,
        parity=parity,
    )


def _assert_book_strokes(slot: Layout) -> None:
    """ADR-0037/R2 on one slot: thin >= 0.25 mm (>= 3 px at 300 DPI), heavy == 2 x thin,
    and every line drawn at the width its own major/minor role asks for."""
    assert slot.thin_rule >= 3
    assert _mm(slot.thin_rule) >= BOOK_MIN_THIN_RULE_MM
    assert slot.thick_rule == 2 * slot.thin_rule
    for line in slot.grid_lines:
        last = slot.columns if line in slot.vertical_lines else slot.rows
        assert line.major == (line.index % 5 == 0 or line.index == last)
        assert line.width == (slot.thick_rule if line.major else slot.thin_rule)


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


def test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up_fitted() -> None:
    """ADR-0037/R2 where the *height fit* sets the shared cell, not the cap.

    The sibling above holds one 10x10 pair against every cap in 7.00..7.50, so
    every cell it sees is the cap's. Here the cell is whatever fitting two
    drawings into a trim's usable height leaves — a cell strictly below the cap
    (7.39, 7.16, ... mm) — over varied puzzle shapes, varied margins and bands,
    and both page parities: the 0.25 mm floor and heavy == 2 x thin hold there
    too, and the cell stays inside FR-040's [7.0, 7.5] band.
    """
    rng = random.Random(1250037)
    fitted = at_cap = 0
    by_parity = {PageParity.ODD: 0, PageParity.EVEN: 0}
    cells: set[float] = set()
    for _ in range(600):
        first, second = _puzzle(rng), _puzzle(rng)
        parity = rng.choice([PageParity.ODD, PageParity.EVEN])
        # Under the cap -> the height fit decides; over it -> the cap decides.
        wanted = (
            round(rng.uniform(7.0 + 1e-3, STANDARD_CELL_MM - 1e-3), 4)
            if rng.random() < 0.75
            else round(rng.uniform(7.6, 12.0), 4)
        )
        spec = _spec_fitting_cell(rng, first, second, cell_mm=wanted, parity=parity)
        expected = _expected_shared_cell_mm(spec, first, second)
        pair = compute_pair_layout(first, second, spec)
        assert pair is not None, (spec, wanted, expected)

        # The cell is the one this trim was built for, and the term that set it
        # is the one the case intended.
        assert abs(pair.cell_mm - expected) < 1e-6, (spec, pair.cell_mm, expected)
        assert TWO_UP_MINIMUM_MM <= pair.cell_mm <= STANDARD_CELL_MM
        if wanted < STANDARD_CELL_MM:
            assert abs(pair.cell_mm - wanted) < 1e-6, (spec, pair.cell_mm, wanted)
            assert pair.cell_mm < STANDARD_CELL_MM - 1e-9, "the height fit binds, not the cap"
            fitted += 1
            cells.add(round(pair.cell_mm, 4))
        else:
            assert abs(pair.cell_mm - STANDARD_CELL_MM) < 1e-9, "the cap binds"
            at_cap += 1
        by_parity[parity] += 1

        assert pair.upper.thin_rule == pair.lower.thin_rule
        assert pair.upper.thick_rule == pair.lower.thick_rule
        for slot in (pair.upper, pair.lower):
            assert slot.page is not None and slot.page.parity is parity
            _assert_book_strokes(slot)
    assert fitted >= 350, fitted
    assert at_cap >= 100, at_cap
    assert min(by_parity.values()) >= 200, by_parity
    assert len(cells) >= 300, len(cells)  # the fitted cells really do vary


def test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_two_up_pixels() -> None:
    """ADR-0037/R2's "black" clause for a pair, measured off the rendered pixels.

    CARD-114's ``..._pixels`` test renders a single puzzle page and counts the
    runs of ink a column of pixels meets crossing the horizontal rules. The
    same technique, the same renderer and the same probe, applied to both slots
    of a two-up page: the page is a blank trim-sized canvas with
    ``png._draw_grid``/``png._draw_clues`` — the body of ``png.render_image``,
    which cannot be called here because it fits its own layout from the clues
    and a spec, and a slot's layout is the pair's — run once per slot, exactly
    as CARD-125's proof renders do.

    Both regimes are covered: the cap's 7.5 mm cell and cells the height fit
    leaves below it, on both parities.
    """
    from PIL import Image, ImageDraw

    from nonogram.export import png

    rng = random.Random(370125)
    checked = fitted = 0
    for wanted in (STANDARD_CELL_MM, 7.39, 7.16, 7.02):
        for parity in (PageParity.ODD, PageParity.EVEN):
            first, second = _puzzle(rng), _puzzle(rng)
            spec = _spec_fitting_cell(rng, first, second, cell_mm=wanted, parity=parity)
            pair = compute_pair_layout(first, second, spec)
            assert pair is not None
            assert abs(pair.cell_mm - wanted) < 1e-6, (pair.cell_mm, wanted)
            fitted += wanted < STANDARD_CELL_MM

            page = Image.new(
                "RGB", (pair.upper.width, pair.upper.height), png.BACKGROUND
            )
            draw = ImageDraw.Draw(page)
            for slot in (pair.upper, pair.lower):
                png._draw_grid(draw, slot)
                png._draw_clues(draw, slot)

            for slot in (pair.upper, pair.lower):
                # Every rule both slots draw has whole paper under it, so the
                # probe below reads each one in full rather than running off
                # the canvas (``_spec_fitting_cell``'s bottom-margin floor).
                assert slot.grid_top - slot.thick_rule >= 0
                assert slot.grid_bottom + slot.thick_rule <= page.height
                # Middle of the last grid column: no clue digit, no vertical line.
                xs = [line.position for line in slot.vertical_lines]
                probe_x = (xs[-2] + xs[-1]) // 2
                runs: list[tuple[int, tuple[int, int, int]]] = []
                run_colour: set[tuple[int, int, int]] = set()
                length = 0
                for y in range(
                    slot.grid_top - slot.thick_rule, slot.grid_bottom + slot.thick_rule
                ):
                    pixel = page.getpixel((probe_x, y))
                    # Literal white and literal black, not ``png.BACKGROUND`` /
                    # ``png.INK`` read back: the clause is "black on the paper".
                    if pixel != (255, 255, 255):
                        length += 1
                        run_colour.add(pixel)
                    elif length:
                        runs.append(
                            (length, run_colour.pop() if len(run_colour) == 1 else (1, 1, 1))
                        )
                        run_colour, length = set(), 0
                assert runs, "the probe crossed no rule at all"
                assert all(colour == (0, 0, 0) for _, colour in runs), "every rule is pure black"
                assert len(runs) == slot.rows + 1
                widths = [width for width, _ in runs]
                majors = [line.major for line in slot.horizontal_lines]
                for width, major in zip(widths, majors, strict=True):
                    assert width == (slot.thick_rule if major else slot.thin_rule)
                    assert _mm(width) >= BOOK_MIN_THIN_RULE_MM
                checked += 1
    assert checked == 16
    assert fitted == 6


def test_PropertyTest_BookTwoUp_UpperSlotIsTheSinglePageAtTheSharedCell() -> None:
    """A slot is ``compute_layout``'s placed page, not a second assembly of one.

    The upper slot's band starts at the top margin, so it is the single-page
    layout of the same puzzle on the same trim with the cap lowered to the
    shared cell — every ruled line (its index, major/minor role, width, and its
    position and extent), every clue entry, both stroke widths, the clue font
    size, the drawing's left and top edges, and the cell itself. Any drift
    between ``_slot_layout`` and ``compute_layout``'s placed-page assembly
    shows up here rather than in one example.

    The one licensed difference is a pixel. ``compute_layout`` is re-fitted from
    the cap handed to it, a ``float``; the pair's own pitch is the exact
    fraction that ``float`` was rounded from. When the shared cell *is* the cap
    (the cell round-trips through ``float`` unchanged) the two agree exactly,
    and that is asserted exactly; when the height fit set it, each boundary is
    rounded from a pitch that differs in its last bits, so a boundary may land
    one pixel apart. Widths, majors, indices, clue values and the clue font
    size are compared exactly in both regimes.
    """
    rng = random.Random(1251)
    checked = fitted = exact = 0
    for index in range(900):
        first, second = _puzzle(rng), _puzzle(rng)
        if index % 2:
            spec = _random_spec(rng)
        else:
            parity = rng.choice([PageParity.ODD, PageParity.EVEN])
            spec = _spec_fitting_cell(
                rng,
                first,
                second,
                cell_mm=round(rng.uniform(7.0 + 1e-3, 9.0), 4),
                parity=parity,
            )
        pair = compute_pair_layout(first, second, spec)
        if pair is None:
            continue
        single = compute_layout(*first, dataclasses.replace(spec, cell_cap=pair.cell_mm))
        assert single.page is not None and pair.upper.page is not None
        assert single.page.cell_mm == pair.upper.page.cell_mm == pair.cell_mm

        # The cap's own cell round-trips through float; a fitted one need not.
        at_cap = pair.cell_mm == float(spec.cell_cap)
        tolerance = 0 if at_cap else 1
        exact += at_cap
        fitted += not at_cap

        slot_lines, single_lines = pair.upper.grid_lines, single.grid_lines
        assert len(slot_lines) == len(single_lines)
        for mine, theirs in zip(slot_lines, single_lines, strict=True):
            assert (mine.index, mine.major, mine.width) == (
                theirs.index,
                theirs.major,
                theirs.width,
            )
            assert abs(mine.position - theirs.position) <= tolerance
            assert abs(mine.start - theirs.start) <= tolerance
            assert abs(mine.end - theirs.end) <= tolerance
        slot_clues, single_clues = pair.upper.clue_entries, single.clue_entries
        assert len(slot_clues) == len(single_clues)
        for mine_clue, theirs_clue in zip(slot_clues, single_clues, strict=True):
            assert mine_clue.value == theirs_clue.value
            assert abs(mine_clue.center_x - theirs_clue.center_x) <= tolerance
            assert abs(mine_clue.center_y - theirs_clue.center_y) <= tolerance
        assert (pair.upper.thin_rule, pair.upper.thick_rule) == (
            single.thin_rule,
            single.thick_rule,
        )
        # The size the clue digits are drawn at (``png._clue_font``) is a
        # function of the pitch alone, so it matches exactly in both regimes.
        assert pair.upper.clue_font_size == single.clue_font_size
        assert abs(pair.upper.page.drawing_left - single.page.drawing_left) <= tolerance
        assert abs(pair.upper.page.drawing_top - single.page.drawing_top) <= tolerance
        checked += 1
    assert checked >= 400, checked
    assert exact >= 100, exact
    assert fitted >= 100, fitted
