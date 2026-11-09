"""CARD-248's footer claims that outlived the QR code (CARD-391).

This file was ``tests/test_book_qr_slot.py`` (CARD-223/CARD-248): 70 tests about
the placeholder QR icon, its caption, its typed link and the two groups a
two-up footer carried. The owner removed the per-puzzle QR on 2026-11-07
(ADR-0041/R8) and CARD-391 retired every test whose claim was about it (the
closing table is in that card's Worktree notes). What is left is the part of
the footer that does not depend on the QR, and it keeps the file's name
because ``meta/profiling/rank_durations.py`` freezes the render-heavy set by
path against recorded artefacts: a rename would move recorded shares for a
file that has not changed what it costs. The claims about the new pointer line
are in ``tests/test_book_footer_pointer.py``.

    TestTwoUpFooter_TheCellCostIsMeasuredAndBounded
    TestTwoUpFooter_APairThatCannotFitSplitsIntoSinglePages
    TestTwoUpFooter_TwoUpPagesNowCarryTheirFolio
    TestTwoUpFooter_UsesTheSameFooterGeometryAsASinglePage
"""

from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from nonogram import clues
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    FOLIO_PT,
    PuzzlePagePlan,
    _folio_reserve_px,
    type_px,
)
from nonogram.admin.book_vector import interior_face_metrics
from nonogram.admin.book_vector_draw import advance_px
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    INTERIOR_FOOTER_MM,
    TWO_UP_RULE_GAP_MM,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_pair_layout,
    interior_frame,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.book_corpus import corpus_book
from tests.helpers.pdf_vector import frame_rules, placed_text

DPI = 300
PX_PER_MM = DPI / 25.4

#: CON-018's Book 1 profile, in millimetres -- the same stated-from-the-spec
#: construction every other footer/frame test file uses, written out here
#: rather than imported.
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
MIN_THIN_RULE_MM = 0.25

#: FR-040's two-up minimum, in millimetres -- written out rather than
#: imported, so a claim about the boundary is not the same constant on both
#: sides.
TWO_UP_MINIMUM_MM = 7.0

#: The footer strip's depth in device pixels, stated from the one-line footer's own
#: two rows rather than read off :data:`INTERIOR_FOOTER_MM`: one 10 pt line and
#: 9 pt of white twice, 28 pt = 9.878 mm (CARD-392; 29.878 mm with the 20 mm
#: QR row before it).
FOOTER_STRIP_PX = 117

#: How many cells of combined drawing height a Book 1 pair may have, with and
#: without the strip reserved, before its shared cell falls under 7.0 mm. Both
#: stated from the usable height by hand (253.492 mm less two 12 mm bands, less
#: the strip for the second), never from ``compute_pair_layout``:
#:
#:     unreserved  229.492 / 7.0 = 32.78  ->  32 cells
#:     reserved    219.586 / 7.0 = 31.37  ->  31 cells
#:
#: so the pairs the strip refuses are **exactly** those whose combined drawing
#: height is 32 cells (CARD-392; 29, 30, 31 and 32 under the 29.878 mm strip
#: of CARD-248, when 28 cells was the largest that paired).
MAX_PAIR_CELLS_UNRESERVED = 32
MAX_PAIR_CELLS_RESERVED = 31
NEWLY_REFUSED_PAIR_CELLS = frozenset({32})


def _spec(
    *,
    parity: PageParity = PageParity.ODD,
    width_mm: float = BOOK1_WIDTH_MM,
    height_mm: float = BOOK1_HEIGHT_MM,
    gutter_mm: float = GUTTER_MM,
    outside_mm: float = OUTSIDE_MM,
    **overrides: object,
) -> PageSpec:
    return PageSpec(
        width_mm=width_mm,
        height_mm=height_mm,
        top_mm=TOP_MM,
        bottom_mm=BOTTOM_MM,
        gutter_mm=gutter_mm,
        outside_mm=outside_mm,
        band_mm=BAND_MM,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=MIN_THIN_RULE_MM,
        parity=parity,
        **overrides,
    )


#: A gutter and an outside margin that **differ**, so mirroring is visible
#: (imported by ``tests/test_book_puzzle_frame.py``).
UNEQUAL_GUTTER_MM = 19.0
UNEQUAL_OUTSIDE_MM = 7.0


def _unequal_spec(parity: PageParity) -> PageSpec:
    """Book 1's trim with a gutter and an outside margin that **differ**."""
    return _spec(parity=parity, gutter_mm=UNEQUAL_GUTTER_MM, outside_mm=UNEQUAL_OUTSIDE_MM)


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> List[List[bool]]:
    """A grid whose row clues are ``row_depth`` deep and columns ``column_depth``."""
    if 2 * row_depth - 1 > columns or 2 * column_depth - 1 > rows:
        raise ValueError(
            f"a {columns}x{rows} grid cannot carry {row_depth}-deep row clues "
            f"and {column_depth}-deep column clues"
        )
    grid = [[False] * columns for _ in range(rows)]
    for step in range(row_depth):
        grid[0][2 * step] = True
    for step in range(column_depth):
        grid[2 * step][0] = True
    return grid


def _clue_sets(columns: int, rows: int, row_depth: int, column_depth: int):
    found = clues.compute_clues(_grid(columns, rows, row_depth, column_depth))
    return found.rows, found.columns


def _payload(columns: int, rows: int, row_depth: int, column_depth: int) -> ExportPayload:
    grid = _grid(columns, rows, row_depth, column_depth)
    found = clues.compute_clues(grid)
    return ExportPayload(
        grid=grid,
        row_clues=found.rows,
        column_clues=found.columns,
        seed=223,
        mode="random",
        name="footer-pointer-test",
        difficulty="Easy",
    )


# ==========================================================================
# Survivors of CARD-223/CARD-248's footer claims (moved here from the QR file)
# ==========================================================================


def _footer_reserve_px(spec: PageSpec) -> int:
    """The strip ``compute_pair_layout`` is told to keep, as production tells it."""
    return interior_frame(spec).footer_depth


def _two_up(
    spec: PageSpec,
    upper: Tuple[int, int, int, int] = (10, 10, 3, 3),
    lower: Optional[Tuple[int, int, int, int]] = None,
    *,
    reserve_footer: bool = True,
):
    """A production two-up pair on ``spec``: both reserves, as ``puzzle_pages`` passes them."""
    return compute_pair_layout(
        _clue_sets(*upper),
        _clue_sets(*(lower if lower is not None else upper)),
        spec,
        folio_reserve_px=_folio_reserve_px(DPI),
        footer_reserve_px=_footer_reserve_px(spec) if reserve_footer else 0,
    )


def _two_up_rule_gap_px(pair, *, footer_px: int) -> int:
    """The rule gap a two-up page leaves between each rule and each drawing.

    Read off the lower slot (its drawing's top less its band's real foot) and
    checked against the gap re-derived from the pair's own placements:
    ``TWO_UP_RULE_GAP_MM``, capped at a quarter of the vertical slack the fit
    left -- the content height (``footer_px`` above the bottom margin) less
    both bands and both drawings -- floored to a whole device pixel, within the
    pixel the placements' own rounding can cost. The same gap stands below the
    upper band's foot and between the lower drawing and the content's bottom.
    """
    upper, lower = pair.upper.page, pair.lower.page
    gap = lower.drawing_top - lower.band_bottom
    assert upper.drawing_top - upper.band_bottom == gap
    slack = (lower.usable_bottom - footer_px) - upper.usable_top - sum(
        (page.band_bottom - page.usable_top) + (page.drawing_bottom - page.drawing_top)
        for page in (upper, lower)
    )
    expected = math.floor(min(TWO_UP_RULE_GAP_MM * PX_PER_MM, max(slack, 0) / 4))
    assert abs(gap - expected) <= 1, (gap, expected, slack)
    assert lower.usable_bottom - footer_px - lower.drawing_bottom == gap
    return gap


def _two_up_stream(page_number: int, pair):
    """The vector two-up page production writes for ``pair``, on Book 1's sheet."""
    generator = BookPDFGenerator(corpus_book(f"card248-{page_number}"))
    payloads = [_payload(10, 10, 3, 3), _payload(10, 10, 3, 3)]
    return generator.vector_two_up_page(PuzzlePagePlan(page_number, (1, 2), pair), payloads)


def _folios_set(stream, page_number: int) -> List[Tuple[float, float]]:
    """Every ``(x, y)`` in points where the stream set ``page_number``'s own digits."""
    placed = placed_text("\n".join(stream.operators))
    return [(x, y) for x, y, _, text in placed if text == str(page_number)]


# --------------------------------------------------------------------------
# The cell cost of the reserved strip, measured and bounded (CARD-248 AC-5)
# --------------------------------------------------------------------------


def _expected_pair_cell_mm(
    across: int, lower_across: int, total_down: int, *, strip: bool
) -> float:
    """FR-040's shared cell on Book 1, written out from the sheet's own
    millimetres — **both** reserves included, as production passes them.

    An independent second implementation, not a call into
    ``compute_pair_layout``: ``min(cap, usable width / the wider drawing's
    columns, (usable height - two bands - the strip) / both drawings' rows)``,
    re-fitted against a usable width one folio reserve narrower when the lower
    drawing's own spare at the first answer falls short of that reserve
    (CARD-204 Fix 4's documented rule, restated here rather than imported).
    The strip is stated as :data:`FOOTER_STRIP_PX` pixels converted back to
    millimetres, which is how the production call converts the reserve it is
    handed.
    """
    usable_width = BOOK1_WIDTH_MM - GUTTER_MM - OUTSIDE_MM
    usable_height = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM
    if strip:
        usable_height -= FOOTER_STRIP_PX / PX_PER_MM
    cell = min(STANDARD_CELL_MM, usable_width / across, usable_height / total_down)
    folio_px = _folio_reserve_px(DPI)
    if usable_width * PX_PER_MM - lower_across * cell * PX_PER_MM < folio_px:
        cell = min(
            STANDARD_CELL_MM,
            (usable_width - folio_px / PX_PER_MM) / across,
            usable_height / total_down,
        )
    return cell


class TestTwoUpFooter_TheCellCostIsMeasuredAndBounded:
    """What the strip costs the pairs that keep pairing, per pair, against an
    independently written formula — and the figure CARD-248's own card guessed
    at, measured.

    **The card's "roughly 0.15 mm off the cell, about 2 %" for the tall 15-row
    pairs is wrong, and the direction matters.** That arithmetic counted the
    two 12 mm bands as spare the strip could take; they are not spare. A
    Book 1 pair's whole free vertical slack is the gap *between* its slots,
    and a 15-row depth-1 pair's is **zero** — the pair is already height-bound
    — so the strip cannot be found anywhere and the pair is **refused**
    outright rather than printed 2 % smaller (AC-6). The real worst surviving
    cost is the 14-row band, measured below: 7.5000 -> 7.3195 mm, **2.41 %**
    (CARD-392's one-line footer; 4.95 % at 13 rows under the old strip).
    """

    def test_the_strip_is_free_wherever_the_gap_between_the_slots_already_holds_it(
        self,
    ) -> None:
        """The card's own "the room already exists" claim, re-derived: a pair
        whose slots sit at least one strip apart commits the identical cell
        with the strip reserved — the strip is taken out of that gap, not out
        of the cell. "That gap" is the pair's whole vertical slack: the room
        between the slots plus the three two-up rule gaps
        (``TWO_UP_RULE_GAP_MM``) spent out of it, which is what the bare and
        reserved pairs are compared on, since the rule gap itself shrinks
        once a quarter of a tighter slack is less than its 3 mm."""
        spec = _spec()
        checked = 0
        for rows in (10, 11, 12, 13):
            bare = _two_up(spec, (10, rows, 1, 1), reserve_footer=False)
            reserved = _two_up(spec, (10, rows, 1, 1))
            assert bare is not None and reserved is not None, rows
            bare_rule_gap = _two_up_rule_gap_px(bare, footer_px=0)
            reserved_rule_gap = _two_up_rule_gap_px(reserved, footer_px=FOOTER_STRIP_PX)
            gap = (
                bare.lower.page.usable_top - bare.upper.page.drawing_bottom
            ) + 3 * bare_rule_gap
            assert gap >= FOOTER_STRIP_PX, (rows, gap)
            assert reserved.cell_mm == bare.cell_mm, (rows, bare.cell_mm, reserved.cell_mm)
            # And the gap really did pay for it.
            assert (
                reserved.lower.page.usable_top - reserved.upper.page.drawing_bottom
            ) + 3 * reserved_rule_gap == gap - FOOTER_STRIP_PX
            checked += 1
        assert checked == 4

    def test_the_committed_cell_is_the_independently_written_fit(self) -> None:
        """Every pair that still pairs commits exactly
        ``min(cap, width fit, (height - two bands - strip) / rows)`` — so no
        pair loses more than the strip forces it to."""
        spec = _spec()
        checked = 0
        for columns in range(MIN_SIZE, 25):
            for rows in range(MIN_SIZE, 16):
                pair = _two_up(spec, (columns, rows, 1, 1))
                if pair is None:
                    continue
                across = 1 + columns
                total_down = 2 * (1 + rows)
                expected = _expected_pair_cell_mm(across, across, total_down, strip=True)
                assert abs(pair.cell_mm - expected) < 1e-6, (
                    columns, rows, pair.cell_mm, expected
                )
                checked += 1
        assert checked >= 45, checked

    def test_the_worst_surviving_cost_is_the_fourteen_row_band_at_2_41_percent(
        self,
    ) -> None:
        """The figure the card asked for, measured and pinned.

        14-row depth-1 pairs are the worst that still pair with the strip
        reserved: 30 cells of drawing height, which 219.586 mm fits at
        7.3195 mm. Unreserved they print at the 7.5 mm cap, so the strip
        costs them 0.1805 mm — **2.41 %** (4.95 % at 13 rows under the
        29.878 mm strip, before CARD-392 shrank it).
        """
        spec = _spec()
        worst = 0.0
        worst_case = None
        for columns in range(MIN_SIZE, 25):
            for rows in range(MIN_SIZE, 16):
                bare = _two_up(spec, (columns, rows, 1, 1), reserve_footer=False)
                reserved = _two_up(spec, (columns, rows, 1, 1))
                if bare is None or reserved is None:
                    continue
                drop = 100 * (bare.cell_mm - reserved.cell_mm) / bare.cell_mm
                if drop > worst:
                    worst, worst_case = drop, (columns, rows, bare.cell_mm, reserved.cell_mm)
        assert worst_case is not None
        assert worst_case[1] == 14, worst_case
        assert abs(worst_case[2] - STANDARD_CELL_MM) < 1e-9
        assert abs(worst_case[3] - 7.3195) < 1e-3, worst_case
        assert abs(worst - 2.41) < 0.01, (worst, worst_case)

    def test_both_slots_keep_one_shared_cell_with_the_strip_reserved(self) -> None:
        """G-4, which CARD-226 builds its aligned bottoms on: the reserve is
        taken from the page, never from one slot, so the two slots print at the
        same cell as each other."""
        spec = _spec()
        checked = 0
        for columns, rows in ((10, 10), (12, 11), (20, 13), (24, 12)):
            pair = _two_up(spec, (columns, rows, 1, 1), (columns, rows, 2, 1))
            if pair is None:
                continue
            assert pair.upper.page.cell_mm == pair.lower.page.cell_mm == pair.cell_mm
            checked += 1
        assert checked >= 3, checked


# --------------------------------------------------------------------------
# A pair that no longer fits prints as two single pages (CARD-248 AC-6)
# --------------------------------------------------------------------------


class TestTwoUpFooter_APairThatCannotFitSplitsIntoSinglePages:
    """The exemption this card grants, as an **exact** set rather than a range
    (ADR-0039/R1, R3), with what happens to its members asserted through the
    production walk.

    **The exact set, on Book 1, and why it is exact rather than a corpus
    sample.** ``compute_pair_layout``'s verdict is a function of two numbers
    only — the wider drawing's columns and the two drawings' combined rows —
    so the set can be stated over the second of them and be complete. The
    usable height is 253.492 mm; two 12 mm bands leave 229.492 mm, and
    FR-040's 7.0 mm floor therefore admits at most 32 cells of drawing height.
    One 117 px strip (CARD-392's one-line footer; 353 px before it) leaves
    219.586 mm, which admits at most 31. So the pairs the strip stops pairing
    are **exactly** those whose combined drawing height is 32 cells — and no
    others, at any width.

    **What they do instead**: two single pages, each with its own footer.
    That is option 1 of the four the owner was shown, and it costs one
    interior page per refused pair. (CARD-248's other refusal, a footer too
    narrow for two QR groups, went with the groups: CARD-391.)

    **It is not a small set.** On the depth-1 equal-size sweep below, 30 of
    the 90 pairs that paired before this card stop pairing; on a seeded
    corpus with real clue depths the share is higher still, because a pair
    deep enough to pair at all is usually already height-bound. The measured
    figures are in the card's report; they are far above the ~2 % the card's
    own prose estimated, and the cost is a longer interior.
    """

    def test_the_refused_set_is_exactly_the_32_cell_pairs(self) -> None:
        """Over every width and height a book puzzle can have, the verdict
        changes for exactly the combined-height band named above — compared
        against the independently written fit, not against the function."""
        spec = _spec()
        changed_heights = set()
        kept_heights = set()
        checked = 0
        # Unequal heights as well as equal ones, so the band's **odd** members
        # (29 and 31 cells) are reachable at all — an equal pair's combined
        # height is always even, and a sweep of those alone would report a
        # smaller set and look like agreement.
        for columns in (MIN_SIZE, 15, 20, 24):
            for upper_rows in range(MIN_SIZE, MAX_SIZE + 1):
                for lower_rows in range(MIN_SIZE, MAX_SIZE + 1):
                    upper = (columns, upper_rows, 1, 1)
                    lower = (columns, lower_rows, 1, 1)
                    bare = _two_up(spec, upper, lower, reserve_footer=False)
                    reserved = _two_up(spec, upper, lower)
                    checked += 1
                    if bare is None:
                        assert reserved is None, (columns, upper_rows, lower_rows)
                        continue
                    total_down = (1 + upper_rows) + (1 + lower_rows)
                    if reserved is None:
                        changed_heights.add(total_down)
                    else:
                        kept_heights.add(total_down)
        assert checked == 4 * 441
        assert changed_heights == NEWLY_REFUSED_PAIR_CELLS, changed_heights
        assert not (kept_heights & NEWLY_REFUSED_PAIR_CELLS), kept_heights
        assert max(kept_heights) == MAX_PAIR_CELLS_RESERVED, kept_heights

    def test_the_boundary_is_where_the_hand_arithmetic_puts_it(self) -> None:
        """The control for the set above (ADR-0039/R1): 31 cells is accepted
        and 32 refused, and the two figures come from the sheet by hand, not
        from the function under test."""
        pair_height_mm = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM
        assert abs(pair_height_mm - 229.492) < 1e-9
        reserved_mm = pair_height_mm - FOOTER_STRIP_PX / PX_PER_MM
        assert abs(reserved_mm - 219.5860) < 1e-3, reserved_mm
        assert int(pair_height_mm / TWO_UP_MINIMUM_MM) == MAX_PAIR_CELLS_UNRESERVED
        assert int(reserved_mm / TWO_UP_MINIMUM_MM) == MAX_PAIR_CELLS_RESERVED
        spec = _spec()
        # 15 drawing rows a slot (a depth-1 14-row puzzle) is 30 cells: paired.
        assert _two_up(spec, (10, 14, 1, 1)) is not None
        # 16 a slot (a depth-1 15-row puzzle) is 32: refused.
        assert _two_up(spec, (10, 15, 1, 1)) is None
        # 31, the odd top of the paired range, needs an unequal pair.
        assert _two_up(spec, (10, 14, 1, 1), (10, 15, 1, 1)) is not None

    def test_such_a_pair_prints_as_two_single_pages_each_with_its_own_footer(self) -> None:
        """Through the production walk: two puzzles in the refused band become
        two plans of one puzzle each, two pages, never one page."""
        generator = BookPDFGenerator(corpus_book("card248-split"))
        payloads = [_payload(10, 15, 1, 1), _payload(10, 15, 1, 1)]
        plans = generator.puzzle_pages(payloads)
        assert [plan.numbers for plan in plans] == [(1,), (2,)], plans
        assert all(plan.pair is None for plan in plans)
        assert len({plan.page_number for plan in plans}) == 2

    def test_the_same_pair_one_cell_shallower_does_share_a_page(self) -> None:
        """The control the claim above needs: one cell of clue gutter less and
        the identical two puzzles pair, on one page. If the refusal ever became
        a blanket rule this reds."""
        generator = BookPDFGenerator(corpus_book("card248-nosplit"))
        payloads = [_payload(10, 14, 1, 1), _payload(10, 14, 1, 1)]
        plans = generator.puzzle_pages(payloads)
        assert [plan.numbers for plan in plans] == [(1, 2)], plans
        assert plans[0].pair is not None


# --------------------------------------------------------------------------
# The folio arrives on a two-up page (CARD-248 AC-7)
# --------------------------------------------------------------------------


class TestTwoUpFooter_TwoUpPagesNowCarryTheirFolio:
    """A gain to claim deliberately: a two-up page had **no** footer, so
    CARD-222's frame refused the strip and the page kept CARD-200's
    bottom-outer-corner folio. With the strip reserved it carries the footer
    rule and the centred folio like every other puzzle page. Read off the
    vector page ``vector_two_up_page`` writes.
    """

    @pytest.mark.parametrize("parity,page_number", [(PageParity.ODD, 5), (PageParity.EVEN, 6)])
    def test_the_footer_group_is_drawn_and_the_folio_is_on_its_line(
        self, parity: PageParity, page_number: int
    ) -> None:
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        frame = interior_frame(spec)
        # The precondition, confirmed rather than assumed: the lower slot's
        # drawing stops one two-up rule gap above the footer rule, clear of
        # its stroke.
        rule_gap = _two_up_rule_gap_px(pair, footer_px=frame.footer_depth)
        assert rule_gap > frame.footer_rule.width
        assert pair.lower.page.drawing_bottom == frame.footer_rule.y - rule_gap

        stream = _two_up_stream(page_number, pair)
        scale = stream.to_points(1.0)
        folios = _folios_set(stream, page_number)
        assert len(folios) == 1, folios
        ((x, y),) = folios
        width = advance_px(str(page_number), type_px(FOLIO_PT, DPI), interior_face_metrics())
        assert x / scale + width / 2 == pytest.approx(frame.folio_x, abs=0.5)
        assert stream.height_px - y / scale == pytest.approx(frame.baseline, abs=0.5)
        # The footer rule is stroked: the page's lowest full-measure rule.
        _, footer = frame_rules("\n".join(stream.operators))
        assert stream.height_px - footer[2] / scale == pytest.approx(frame.footer_rule.y, abs=1.0)

    def test_the_folio_is_not_also_in_the_corner(self) -> None:
        """One page number, not two: the corner fallback and the footer line
        are alternatives, and gaining the second must not leave the first."""
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec)
        assert pair is not None
        frame = interior_frame(spec)
        stream = _two_up_stream(5, pair)
        folios = _folios_set(stream, 5)
        assert len(folios) == 1, folios
        ((_, y),) = folios
        baseline = stream.height_px - y / stream.to_points(1.0)
        assert baseline == pytest.approx(frame.baseline, abs=0.5)
        assert abs(baseline - frame.page_bottom) > 1


# --------------------------------------------------------------------------
# One definition of a footer
# --------------------------------------------------------------------------


class TestTwoUpFooter_UsesTheSameFooterGeometryAsASinglePage:
    """G-1/AC-8 of CARD-248: a two-up page's footer is **the** footer, not a
    second definition of one for pairs."""

    def test_the_strip_the_pair_reserves_is_the_strip_the_frame_draws(self) -> None:
        """One figure, read by both: the reserve handed to
        ``compute_pair_layout`` is ``InteriorFrame.footer_depth``, and the
        lower slot's resulting slack is exactly that plus the two-up rule gap
        (``TWO_UP_RULE_GAP_MM``) -- so the drawing stops that gap above the
        rule the frame strokes, by construction."""
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            frame = interior_frame(spec)
            assert frame.footer_depth == FOOTER_STRIP_PX
            assert frame.footer_depth == round(INTERIOR_FOOTER_MM * PX_PER_MM)
            pair = _two_up(spec)
            assert pair is not None
            placement = pair.lower.page
            rule_gap = _two_up_rule_gap_px(pair, footer_px=frame.footer_depth)
            assert rule_gap > 0
            assert placement.usable_bottom - placement.drawing_bottom == (
                frame.footer_depth + rule_gap
            )
            assert placement.drawing_bottom == frame.footer_rule.y - rule_gap

    def test_there_is_one_footer_depth_constant_and_one_pointer_placer(self) -> None:
        """Read off the source: nothing in the package states a second footer
        depth, and the only thing that places the pointer line is
        ``footer_pointer``."""
        package = Path(__file__).resolve().parent.parent / "src" / "nonogram"
        placers = []
        for module in sorted(package.rglob("*.py")):
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "footer_pointer":
                    placers.append(module.name)
        assert placers == ["layout.py"], placers
        source = (package / "export" / "layout.py").read_text(encoding="utf-8")
        assert source.count("INTERIOR_FOOTER_MM = ") == 1
