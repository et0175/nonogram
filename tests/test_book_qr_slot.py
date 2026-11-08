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
from pathlib import Path
from typing import List, Optional, Tuple

import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    PuzzlePagePlan,
    _draw_page_frame,
    _folio_reserve_px,
)
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    INTERIOR_FOOTER_MM,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_pair_layout,
    interior_frame,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.book_corpus import corpus_book

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

#: The unequal sheet's two side margins, in millimetres: neither is a Book 1
#: figure and the two differ by 12 mm, so "which side" claims made on it cannot
#: pass by reading the wrong margin.
UNEQUAL_GUTTER_MM = 19.0
UNEQUAL_OUTSIDE_MM = 7.0

DOMAIN = "https://nonogram.adverax.io"

#: FR-040's two-up minimum, in millimetres -- written out rather than
#: imported, so a claim about the boundary is not the same constant on both
#: sides.
TWO_UP_MINIMUM_MM = 7.0

#: The footer strip's depth in device pixels, stated from CON-020's own three
#: rows rather than read off :data:`INTERIOR_FOOTER_MM`: the 20 mm row the QR
#: icon used to fill (still reserved, CARD-392 shrinks it), one 10 pt line and
#: 9 pt of white twice. 29.878 mm.
FOOTER_STRIP_PX = 353

#: How many cells of combined drawing height a Book 1 pair may have, with and
#: without the strip reserved, before its shared cell falls under 7.0 mm. Both
#: stated from the usable height by hand (253.492 mm less two 12 mm bands, less
#: the strip for the second), never from ``compute_pair_layout``:
#:
#:     unreserved  229.492 / 7.0 = 32.78  ->  32 cells
#:     reserved    199.605 / 7.0 = 28.51  ->  28 cells
#:
#: so the pairs the strip refuses are **exactly** those whose combined drawing
#: height is 29, 30, 31 or 32 cells.
MAX_PAIR_CELLS_UNRESERVED = 32
MAX_PAIR_CELLS_RESERVED = 28
NEWLY_REFUSED_PAIR_CELLS = frozenset({29, 30, 31, 32})


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


def _page_text_calls(generator, plan, payloads, monkeypatch) -> List[dict]:
    """Every ``draw.text`` call **one page's** own drawing makes.

    The per-page form of :func:`_text_calls`, for a page composed directly by
    ``_two_up_page`` rather than reached through a whole interior export —
    the same spy ``tests/test_book_page_numbers.py`` uses for the folio.
    """
    original = ImageDraw.ImageDraw.text
    calls: List[dict] = []

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        calls.append(
            {
                "text": str(text),
                "anchor": kwargs.get("anchor"),
                "size": getattr(font, "size", None),
                "xy": xy,
            }
        )
        return original(self, xy, text, fill, font, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    try:
        generator._two_up_page(plan, payloads)
    finally:
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
    return calls


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


def _two_up_render(
    spec_parity: PageParity,
    page_number: int,
    pair,
    numbers=(1, 2),
    *,
    book=None,
):
    """A real two-up page image, drawn by the production method.

    ``book`` names the stored print specification the renderer reads its own
    frame from; the default is Book 1's. Pass one when the pair was fitted on
    some other profile, because the two have to be the same sheet
    (:func:`_ink_render`).
    """
    generator = BookPDFGenerator(
        book or corpus_book(f"card248-{spec_parity.name}-{page_number}")
    )
    payloads = [_payload(10, 10, 3, 3), _payload(10, 10, 3, 3)]
    plan = PuzzlePagePlan(page_number, numbers, pair)
    return generator, plan, payloads


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
    cost is the 13-row band, measured below: 7.5000 -> 7.1287 mm, **4.95 %**.
    """

    def test_the_strip_is_free_wherever_the_gap_between_the_slots_already_holds_it(
        self,
    ) -> None:
        """The card's own "the room already exists" claim, re-derived: a pair
        whose slots sit at least one strip apart commits the identical cell
        with the strip reserved — the strip is taken out of that gap, not out
        of the cell."""
        spec = _spec()
        checked = 0
        for rows in (10, 11, 12):
            bare = _two_up(spec, (10, rows, 1, 1), reserve_footer=False)
            reserved = _two_up(spec, (10, rows, 1, 1))
            assert bare is not None and reserved is not None, rows
            gap = bare.lower.page.usable_top - bare.upper.page.drawing_bottom
            assert gap >= FOOTER_STRIP_PX, (rows, gap)
            assert reserved.cell_mm == bare.cell_mm, (rows, bare.cell_mm, reserved.cell_mm)
            # And the gap really did pay for it.
            assert (
                reserved.lower.page.usable_top - reserved.upper.page.drawing_bottom
                == gap - FOOTER_STRIP_PX
            )
            checked += 1
        assert checked == 3

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

    def test_the_worst_surviving_cost_is_the_thirteen_row_band_at_4_95_percent(
        self,
    ) -> None:
        """The figure the card asked for, measured and pinned.

        13-row depth-1 pairs are the deepest that still pair with the strip
        reserved: 28 cells of drawing height, which 199.605 mm fits at
        7.1287 mm. Unreserved they print at the 7.5 mm cap, so the strip
        costs them 0.3713 mm — **4.95 %**, not the card's guessed 2 %.
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
        assert worst_case[1] == 13, worst_case
        assert abs(worst_case[2] - STANDARD_CELL_MM) < 1e-9
        assert abs(worst_case[3] - 7.1287) < 1e-3, worst_case
        assert abs(worst - 4.95) < 0.01, (worst, worst_case)

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
    One 353 px strip leaves 199.605 mm, which admits at most 28. So the pairs
    this card stops pairing are **exactly** those whose combined drawing
    height is 29, 30, 31 or 32 cells — and no others, at any width.

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

    def test_the_refused_set_is_exactly_the_29_to_32_cell_pairs(self) -> None:
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
        """The control for the set above (ADR-0039/R1): 28 cells is accepted
        and 29 refused, and the two figures come from the sheet by hand, not
        from the function under test."""
        pair_height_mm = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM
        assert abs(pair_height_mm - 229.492) < 1e-9
        reserved_mm = pair_height_mm - FOOTER_STRIP_PX / PX_PER_MM
        assert abs(reserved_mm - 199.6047) < 1e-3, reserved_mm
        assert int(pair_height_mm / TWO_UP_MINIMUM_MM) == MAX_PAIR_CELLS_UNRESERVED
        assert int(reserved_mm / TWO_UP_MINIMUM_MM) == MAX_PAIR_CELLS_RESERVED
        spec = _spec()
        # 14 drawing rows a slot (a depth-1 13-row puzzle) is 28 cells: paired.
        assert _two_up(spec, (10, 13, 1, 1)) is not None
        # 15 a slot (a depth-1 14-row puzzle) is 30: refused.
        assert _two_up(spec, (10, 14, 1, 1)) is None
        # 29, the odd member of the band, needs an unequal pair.
        assert _two_up(spec, (10, 13, 1, 1), (10, 14, 1, 1)) is None

    def test_such_a_pair_prints_as_two_single_pages_each_with_its_own_footer(self) -> None:
        """Through the production walk: two puzzles in the refused band become
        two plans of one puzzle each, two pages, never one page."""
        generator = BookPDFGenerator(corpus_book("card248-split"))
        payloads = [_payload(10, 14, 1, 1), _payload(10, 14, 1, 1)]
        plans = generator.puzzle_pages(payloads)
        assert [plan.numbers for plan in plans] == [(1,), (2,)], plans
        assert all(plan.pair is None for plan in plans)
        assert len({plan.page_number for plan in plans}) == 2

    def test_the_same_pair_one_cell_shallower_does_share_a_page(self) -> None:
        """The control the claim above needs: one cell of clue gutter less and
        the identical two puzzles pair, on one page. If the refusal ever became
        a blanket rule this reds."""
        generator = BookPDFGenerator(corpus_book("card248-nosplit"))
        payloads = [_payload(10, 13, 1, 1), _payload(10, 13, 1, 1)]
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
    rule and the centred folio like every other puzzle page.

    Survivor of ``tests/test_book_page_frame.py``'s
    ``TestBookPageFrame_TwoUpKeepsItsOuterFolio`` (G-7), which asserted the
    opposite and is retargeted there to the exemption that is left.
    """

    @pytest.mark.parametrize("parity,page_number", [(PageParity.ODD, 5), (PageParity.EVEN, 6)])
    def test_the_footer_group_is_drawn_and_the_folio_is_on_its_line(
        self, parity: PageParity, page_number: int, monkeypatch
    ) -> None:
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        frame = interior_frame(spec)
        # The precondition, confirmed rather than assumed: the lower slot's
        # drawing now stops exactly on the footer rule.
        assert pair.lower.page.drawing_bottom == frame.footer_rule.y

        generator, plan, payloads = _two_up_render(parity, page_number, pair)
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        folios = [call for call in calls if call["text"] == str(page_number)]
        assert len(folios) == 1, calls
        assert folios[0]["xy"] == (frame.folio_x, frame.baseline), folios
        assert folios[0]["anchor"] == "mb", folios

    def test_the_frames_own_verdict_says_the_strip_was_drawn(self) -> None:
        """Not read off the ink: ``_draw_page_frame`` returns whether it drew
        the footer group, and on a reserved two-up page it returns ``True``
        where it returned ``False`` before this card."""
        spec = _spec()
        frame = interior_frame(spec)
        for reserve, expected in ((True, True), (False, False)):
            pair = _two_up(spec, reserve_footer=reserve)
            assert pair is not None, reserve
            canvas = Image.new("RGB", (pair.lower.width, pair.lower.height), (255, 255, 255))
            drawn = _draw_page_frame(
                ImageDraw.Draw(canvas),
                frame,
                5,
                DPI,
                size_label=None,
                content_bottom=pair.lower.page.drawing_bottom,
                content_right=pair.lower.page.drawing_right,
                content_left=pair.lower.page.drawing_left,
            )
            assert drawn is expected, (reserve, drawn)

    def test_the_folio_is_not_also_in_the_corner(self, monkeypatch) -> None:
        """One page number, not two: the corner fallback and the footer line
        are alternatives, and gaining the second must not leave the first."""
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec)
        assert pair is not None
        frame = interior_frame(spec)
        generator, plan, payloads = _two_up_render(PageParity.ODD, 5, pair)
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        folios = [call for call in calls if call["text"] == "5"]
        assert len(folios) == 1, folios
        assert folios[0]["xy"][1] == frame.baseline
        assert folios[0]["xy"][1] != frame.page_bottom


# --------------------------------------------------------------------------
# One definition of a footer
# --------------------------------------------------------------------------


class TestTwoUpFooter_UsesTheSameFooterGeometryAsASinglePage:
    """G-1/AC-8 of CARD-248: a two-up page's footer is **the** footer, not a
    second definition of one for pairs."""

    def test_the_strip_the_pair_reserves_is_the_strip_the_frame_draws(self) -> None:
        """One figure, read by both: the reserve handed to
        ``compute_pair_layout`` is ``InteriorFrame.footer_depth``, and the
        lower slot's resulting slack is exactly that -- so the drawing stops
        on the rule the frame strokes, by construction."""
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            frame = interior_frame(spec)
            assert frame.footer_depth == FOOTER_STRIP_PX
            assert frame.footer_depth == round(INTERIOR_FOOTER_MM * PX_PER_MM)
            pair = _two_up(spec)
            assert pair is not None
            placement = pair.lower.page
            assert placement.usable_bottom - placement.drawing_bottom == frame.footer_depth
            assert placement.drawing_bottom == frame.footer_rule.y

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
