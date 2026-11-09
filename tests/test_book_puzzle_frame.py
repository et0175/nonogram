"""CARD-144/CARD-146 — a frame around the puzzle on book pages (ADR-0036/R1, CON-019).

    CARD-144 AC (new)  TestPuzzleFrame_BookPageCarriesTheFrame
    CARD-144 AC (new)  TestPuzzleFrame_DefaultPageSpecIsUnchanged
    CARD-144 AC (new)  TestPuzzleFrame_GeometryIsUnmovedByTheFrame
    CARD-144 AC (new)  TestPuzzleFrame_UsesTheHeavyRuleOnly
    CARD-144 AC (new)  TestPuzzleFrame_PairIsFramedPerPuzzle
    CARD-146 AC-1      TestPuzzleFrame_PairIsFramedOnThePrintedPage
    CARD-146 AC-2      TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly
    CARD-146 AC-3      TestPuzzleFrame_TwoUpStraddlesItsBoundaryLikeASinglePage
    CARD-146 AC-4      TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame
    CARD-224 AC-378    TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame
                       ::test_the_upper_slot_still_starts_on_the_bands_own_foot
                       (the ink half: this module's own rendered pages. The
                       PDF-level statement is
                       ``tests/test_book_pdf_two_up.py``'s
                       ``TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow``,
                       and the layout-level one
                       ``tests/test_layout_two_up.py``'s
                       ``TestPairLayout_UpperSlotSitsAtItsOwnBandFoot``.
                       AC-379 — the two slots sharing the page's own puzzle
                       area — is owed to CARD-226 and has no test here.)

**CARD-144 measured the pair; CARD-146 prints it.** ``compute_pair_layout``
computed a ``PuzzleFrame`` for both slots of a two-up page from the day
CARD-144 landed — ``TestPuzzleFrame_PairIsFramedPerPuzzle`` below is that
evidence, and it was green the whole time — but the *page* is composed by
``book_pdf_generator._stroke_drawing``, which reimplements grid stroking from
the slot's own line tuples (the native-reimplementation convention) and simply
never stroked ``slot.frame``. Interior page 3 of the baseline book, the two-up
page, was byte-identical to its pre-frame recording while the single-puzzle
pages moved. The four CARD-146 classes are therefore all stated on the
**printed page**, never on the layout object: a criterion that reads
``slot.frame`` would have passed before the gap was closed.

The owner asked for the classic printed look: one rectangle around clues and
grid, the two clue bands boxed off from the grid, an empty corner. It is **ink
and not geometry** — every side of it lands on a boundary ``compute_layout``
had already placed — and it is confined to **book pages**, because CON-019
holds the CLI's and the web's A4 output byte-identical and the owner chose to
keep that intact rather than amend it.

**No FR is named above, deliberately.** The frame is the owner's decision of
2026-09-23, recorded as intake at
``meta/architecture/inputs/raw-requirements.md:265`` and not yet formalised
into a requirement with acceptance criteria — so the "AC (new)" rows above are
this module's own names for the properties it pins, not ids from
``requirements.yml``. This card first cited FR-041, which is the **level
order and divider** requirement (CARD-128's), and that was wrong in a way a
missing citation would not have been: it made untraced scope look traced.

What is measured, and against what
----------------------------------
Where the frame is expected to be is worked out here from CON-018's profile in
**inches**, the way ``tests/test_book_pdf.py`` and
``tests/test_book_pdf_two_up.py`` state a book page's arithmetic: the cell is
``min(7.5 mm, usable width / drawing columns, usable height / drawing rows)``,
the drawing is centred across the usable width, and its top edge **floats** at
42% of CARD-222's puzzle-area spare height (FR-032 as amended 2026-10-17,
CARD-224) — degrading to the band's foot, one band below the top margin, on a
sheet whose area cannot hold the drawing clear of both of its rules. It hung at
the band's foot unconditionally until CARD-224, and that fixed row survives
here only as :func:`_fixed_top_mm`, the control the placement ACs need. A
two-up slot starts one two-up rule gap (``TWO_UP_RULE_GAP_MM``) below its own
slot's band foot and a packed answer tile at its own; only a *single* page's
drawing floats. Nothing in :func:`_expected_box` reads
``compute_layout``, so a frame in the right place is two answers agreeing
rather than one answer restated.

What the frame looks like on paper is then read off the **rendered raster**
(:func:`~nonogram.export.png.render_image`), not off the ``PuzzleFrame`` that
placed it: the four sides are checked for unbroken ink, the corner box for the
absence of it, and the stroke's own pixels for their width, their colour and
which side of the boundary they fall on.

Where the stroke sits
---------------------
Pillow centres a stroke on its coordinate, so half of a rule drawn on a box's
edge falls outside the box. The frame is drawn **on** its four boundaries, not
inside them, because that is what the grid's own outer border already does —
:class:`~nonogram.export.layout.PuzzleFrame` states the reasoning.
:meth:`TestPuzzleFrame_UsesTheHeavyRuleOnly.test_the_frame_straddles_its_boundary_exactly_as_the_grids_border_does`
is what pins it: it compares the frame's left rule's pixel offsets about the
drawing's left edge with the grid's right border's offsets about the grid's
right edge, and requires them equal and straddling zero. An inset frame, or one
drawn half a rule out of step with the border it continues, fails there.
"""

from __future__ import annotations

import ast
import dataclasses
import random
import warnings
from fractions import Fraction
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _folio_reserve_px,
    _stroke_drawing,
)
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    DEFAULT_PAGE_SPEC,
    DPI,
    CellCapPolicy,
    GridRule,
    GridRules,
    OrientationPolicy,
    PageParity,
    TWO_UP_RULE_GAP_MM,
    PageSpec,
    compute_layout,
    compute_pair_layout,
    interior_frame,
)
# The one private this module reads: the boundary
# ``test_a_gap_of_exactly_one_clearance_floats`` pins is not reachable through
# ``compute_layout`` at any trim (see that test), so it is stated on the
# placement itself. The same convention as this file's ``_folio_reserve_px``
# and ``_stroke_drawing`` imports above.
from nonogram.export.layout import _placed_drawing_top
from nonogram.export.png import BACKGROUND, render_image
from tests.helpers.page_ink import Drawing, FrameCentre, drawing_of, frame_centre_of
from tests.helpers.pdf_pages import interior_images
from tests.helpers.two_up_ink import drawings_of
# CARD-219: the readers the shared-render controls at the end of this file are
# built on, which CARD-218 had to write out here and again in
# ``tests/test_book_pdf_band.py``. Aliased to the names those controls already
# call, so this file's call sites are unchanged.
from tests.helpers.shared_fixture_controls import (
    bitmap_bytes as _bitmap_bytes,
    lru_cache_names as _lru_cache_names,
    page_digest as _page_digest,
    refuse_unless_every_consumer_is_collected as _refuse_unless_every_consumer_is_collected,
    refuse_unless_nothing_takes_it_later as _refuse_unless_nothing_takes_it_later,
    retained_bitmap_bytes as _retained_bitmap_bytes,
)
# The project's own figure for one book page — 2550 x 3300 RGB, 25,245,000 B.
# Imported rather than restated so the retention bound at the end of this file
# is the unit this repo already reasons in, and cross-checked against the
# pages this module actually draws by
# ``TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind.test_the_page_bitmap_unit_is_this_modules_own_page``,
# so it cannot quietly come to mean something else.
from tests.test_book_pdf_memory import PAGE_BITMAP_BYTES
from tests.test_book_qr_slot import (
    UNEQUAL_GUTTER_MM,
    UNEQUAL_OUTSIDE_MM,
    _unequal_spec,
)

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in inches, written out rather than imported
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
# CON-018's margins as amended 2026-10-17 (CARD-222): the outside margin
# moved 0.375 -> 0.5 in, the top to 0.55 in and the bottom to 0.47 in, and the
# gutter deliberately stayed at KDP's 0.5 in. Written out here, as this file
# writes every other figure out, rather than imported.
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4

#: A 6 x 9 in trim, the other one the owner prints — CARD-144 asks the frame to
#: sit correctly on any stored trim, not only on Book 1's.
SIX_BY_NINE_MM = (6 * 25.4, 9 * 25.4)

#: The title band above each puzzle (TERM-028), NFR-008's standard cell and
#: the book's thinnest thin rule **on a raster surface** — which is all
#: ``min_thin_rule_mm`` has meant since ADR-0037/R2's 2026-10-25 amendment
#: moved the interior's weights to physical points with no millimetre floor.
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
MIN_THIN_RULE_MM = 0.25

#: ADR-0037/R2's three grid-rule weights and their tones, exactly as the
#: owner's artifact "Puzzle page layout" states them — 0.3 pt cell lines in
#: grey, 1.1 pt every fifth (0.8 pt until the owner raised it on 2026-11-08),
#: 1.3 pt border — and **written out here rather
#: than imported**, for the reason every other CON-018 figure in this file is
#: written out: :func:`_spec` is the profile stated independently of the
#: panel, so a spec that borrowed the panel's own ``GRID_RULES`` object would
#: make ``test_the_profile_is_the_panels_sheet`` compare a value with itself.
GRID_RULES = GridRules(
    cell=GridRule(width_pt=0.3, grey=0.35),
    fifth=GridRule(width_pt=1.1, grey=0.0),
    border=GridRule(width_pt=1.3, grey=0.0),
)

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = DPI / 25.4

#: CARD-222's puzzle area and CARD-224's split, written out as this file
#: writes every other figure out. The header rule sits an eighth of the band's
#: depth above its foot; the footer rule one footer strip
#: (:data:`FOOTER_STRIP_MM`, declared below with the two-up figures) above the
#: bottom margin; and the drawing floats with 42% of the area's spare height
#: above it (FR-032 as amended 2026-10-17, AC-366/AC-367 — the owner's own
#: optical figure, "which looks centred once the header sits above it").
HEADER_RULE_LIFT_SHARE = 1 / 8
SPARE_ABOVE = 0.42

#: A drawing whose spare is positive but under this many millimetres sits in the
#: clearance window the boundary test owns (the threshold is 1.21 mm at Book 1's
#: cell); 2.0 mm is the tolerance ``tests/property/test_book_pdf_geometry`` uses
#: for the same window.
CLEARANCE_WINDOW_MM = 2.0

#: CARD-204 Fix 4's fixed, universal folio reserve, in millimetres —
#: ``_folio_reserve_px`` is a font-measurement helper (not FR-040's own
#: geometry), so it is imported directly rather than reimplemented a third
#: time; the pairing/placement arithmetic that uses it below is this
#: module's own independent check.
RESERVE_MM = _folio_reserve_px(DPI) / PX_PER_MM

#: How far a measured edge may sit from the millimetres worked out here. Every
#: boundary is rounded to a whole device pixel once, and the drawing's left
#: edge carries the half-pixel of a centred drawing as well.
EDGE_TOLERANCE_PX = 1.5

#: A pixel darker than this (0..255 grey) is ink, the level ``page_ink`` uses.
INK_LEVEL = 128


# --------------------------------------------------------------------------
# The sheets and the puzzles
# --------------------------------------------------------------------------


def _spec(
    *,
    width_mm: float = BOOK1_WIDTH_MM,
    height_mm: float = BOOK1_HEIGHT_MM,
    parity: PageParity = PageParity.ODD,
    band_mm: float = BAND_MM,
    **overrides: object,
) -> PageSpec:
    """A book page, stated from CON-018 rather than built by the panel.

    ``band_mm`` is named rather than left to ``**overrides`` because the
    degraded placement's safety is a function of it (CARD-224 review cycle 2,
    F2-001) and two tests below vary it.
    """
    return PageSpec(
        width_mm=width_mm,
        height_mm=height_mm,
        top_mm=TOP_MM,
        bottom_mm=BOTTOM_MM,
        gutter_mm=GUTTER_MM,
        outside_mm=OUTSIDE_MM,
        band_mm=band_mm,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=MIN_THIN_RULE_MM,
        grid_rules=GRID_RULES,
        parity=parity,
        **overrides,
    )


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> list[list[bool]]:
    """A grid whose row clues are ``row_depth`` deep and columns ``column_depth``.

    Row 0 carries ``row_depth`` single cells with a gap between each, so it
    encodes to that many runs and no row is deeper; column 0 does the same down
    the page. They share the corner cell, which is one run of each, so neither
    count is disturbed. (The same construction ``tests/test_book_pdf_two_up.py``
    uses, restated here rather than imported across test modules.)
    """
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


def _clue_sets(
    columns: int, rows: int, row_depth: int, column_depth: int
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    found = clues.compute_clues(_grid(columns, rows, row_depth, column_depth))
    return found.rows, found.columns


def _payload(columns: int, rows: int, row_depth: int, column_depth: int) -> ExportPayload:
    grid = _grid(columns, rows, row_depth, column_depth)
    found = clues.compute_clues(grid)
    return ExportPayload(
        grid=grid,
        row_clues=found.rows,
        column_clues=found.columns,
        seed=144,
        mode="random",
        width=columns,
        height=rows,
    )


# --------------------------------------------------------------------------
# The independent second implementation: where a framed drawing must sit
# --------------------------------------------------------------------------


def _expected_cell_mm(spec: PageSpec, drawing_columns: int, drawing_rows: int) -> float:
    """FR-030's cell, in millimetres, restated from the trim."""
    usable_width = spec.width_mm - spec.gutter_mm - spec.outside_mm
    usable_height = spec.height_mm - spec.top_mm - spec.bottom_mm - spec.band_mm
    return min(
        STANDARD_CELL_MM, usable_width / drawing_columns, usable_height / drawing_rows
    )


def _expected_box(
    spec: PageSpec, columns: int, rows: int, row_depth: int, column_depth: int
) -> tuple[float, float, float, float]:
    """``(left, top, right, bottom)`` of the drawing, in device pixels.

    Worked out from the sheet in millimetres (CARD-224, FR-032): the drawing is
    **centred** across the usable width — on both parities, so parity moves the
    usable area and not the alignment — and its top edge **floats** at
    :data:`SPARE_ABOVE` of CARD-222's puzzle-area spare height, or sits at the
    band's foot where the drawing is too deep for that area to hold it (the
    regime a page-fit-bound drawing is always in, since the cell is fitted
    against the usable height less the band, which is up to one footer strip
    deeper than the area). Between CARD-204 and CARD-224 the drawing was flush
    with the outer margin and its top edge was the band's foot on every page.

    That rectangle **is** the frame: its left and top are the outer edges of
    the two clue gutters, its right and bottom the grid's own outer border.
    """
    drawing_columns = row_depth + columns
    drawing_rows = column_depth + rows
    cell = _expected_cell_mm(spec, drawing_columns, drawing_rows)
    usable_width = spec.width_mm - spec.gutter_mm - spec.outside_mm
    left_margin = spec.outside_mm if spec.parity is PageParity.EVEN else spec.gutter_mm
    spare = usable_width - drawing_columns * cell
    left = left_margin + max(spare, 0.0) / 2
    top = _expected_top_mm(spec, drawing_rows * cell)
    return (
        left * PX_PER_MM,
        top * PX_PER_MM,
        (left + drawing_columns * cell) * PX_PER_MM,
        (top + drawing_rows * cell) * PX_PER_MM,
    )


def _footer_group_omitted(layout, spec) -> bool:
    """Whether the page's footer group is omitted: the drawing reaches past the rule.

    The condition ``_draw_page_frame`` applies (``content_bottom`` against the
    footer rule's own row), read off ``interior_frame``. Until CARD-391 these
    tests proxied it through the QR icon's room check, which answered the same
    question on the same figure.
    """
    return layout.page.drawing_bottom > interior_frame(spec).footer_rule.y


def _puzzle_area_mm(spec: PageSpec) -> tuple[float, float]:
    """CARD-222's puzzle area on ``spec``: ``(header rule, footer rule)``, in mm."""
    return (
        spec.top_mm + spec.band_mm * (1 - HEADER_RULE_LIFT_SHARE),
        spec.height_mm - spec.bottom_mm - FOOTER_STRIP_MM,
    )


def _expected_top_mm(spec: PageSpec, drawing_height_mm: float) -> float:
    """Where a drawing that deep starts on ``spec``, in millimetres (CARD-224).

    The 42% float, or the band's foot when the puzzle area cannot hold the
    drawing clear of both of its rules. The implementation abandons the ratio a
    little before the spare reaches zero: each of the two gaps the split would
    leave has to pay the drawing's own half-heavy-rule clearance, and since the
    split is 42/58 the binding one is the gap *above* — the ratio is refused
    below ``clearance / 0.42`` of spare, which is 14.29 px (1.21 mm) at Book 1's
    cell (CARD-224 review cycle 1, F-001).

    **This helper deliberately does not model that threshold**, and the
    simplification is ``spare <= 0``. Every box this file checks with it is on
    a trim with tens of millimetres of spare, so the two rules cannot disagree
    where it is used. It also does not model the degraded row's own lower
    bound — the placement stops at the band's foot *or* one pixel of drawing
    past the footer rule, whichever is lower (review cycle 2, F2-001) — which
    bites only on bands shallower than about 10.4 mm, and every sheet this
    helper is used on carries the 12 mm band.
    **Nothing that reads this helper can therefore pin the
    boundary, and no module that measures only in millimetres can**: the
    threshold is a function of the heavy rule in device pixels.
    :mod:`tests.property.test_book_pdf_geometry`'s ``CLEARANCE_WINDOW_MM`` is a
    2.0 mm *tolerance* that accepts both candidate rows — it is wider than the
    threshold itself and was never an oracle for it — and
    :mod:`tests.property.test_book_layout` sweeps the degraded regime without
    reaching its edge. The boundary's one oracle is
    :meth:`TestBookPuzzleFrame_GridClearsBothRules.test_the_clearance_threshold_is_the_gap_above_and_not_half_the_spare`,
    which walks one sheet's trim height across it in 0.05 mm steps and asserts
    both gaps against a clearance derived from the three rule weights.
    """
    area_top, area_bottom = _puzzle_area_mm(spec)
    spare = (area_bottom - area_top) - drawing_height_mm
    if spare <= 0:
        return spec.top_mm + spec.band_mm
    return area_top + SPARE_ABOVE * spare


# --------------------------------------------------------------------------
# Reading ink off a rendered page
# --------------------------------------------------------------------------


def _dark(page: Image.Image) -> np.ndarray:
    return np.asarray(page.convert("L")) < INK_LEVEL


def _groups(indices: np.ndarray) -> list[list[int]]:
    """Consecutive runs of ``indices`` — one group per stroked rule."""
    groups: list[list[int]] = []
    for index in indices.tolist():
        if groups and index == groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def _ink_columns(dark: np.ndarray, row: int) -> list[list[int]]:
    """The groups of ink columns on one pixel row."""
    return _groups(np.flatnonzero(dark[row]))


def _ink_rows(dark: np.ndarray, column: int) -> list[list[int]]:
    """The groups of ink rows down one pixel column."""
    return _groups(np.flatnonzero(dark[:, column]))


# --------------------------------------------------------------------------
# AC: a book page carries the frame
# --------------------------------------------------------------------------


class TestPuzzleFrame_BookPageCarriesTheFrame:
    """A closed rectangle around clues and grid, the bands boxed, corner empty."""

    CASE = dict(columns=20, rows=20, row_depth=4, column_depth=5)

    @pytest.fixture(scope="class")
    @classmethod
    def spec(cls) -> PageSpec:
        return _spec()

    @pytest.fixture(scope="class")
    @classmethod
    def page(cls, spec) -> Image.Image:
        return render_image(_payload(**cls.CASE), page_spec=spec)

    def test_the_frame_is_the_drawings_own_box(self, spec) -> None:
        layout = compute_layout(*_clue_sets(**self.CASE), spec)
        frame = layout.frame

        assert frame is not None, "a book page's layout carries a frame"
        expected = _expected_box(spec, **self.CASE)
        measured = (frame.left, frame.top, frame.right, frame.bottom)
        assert all(
            abs(was - is_) <= EDGE_TOLERANCE_PX
            for was, is_ in zip(expected, measured, strict=True)
        ), f"the frame is at {measured}, and CON-018 puts the drawing at {expected}"
        # The two sides that are not new ink: they are the grid's own border.
        assert (frame.right, frame.bottom) == (layout.grid_right, layout.grid_bottom)

    def test_the_four_sides_are_unbroken_ink(self, spec, page) -> None:
        frame = compute_layout(*_clue_sets(**self.CASE), spec).frame
        dark = _dark(page)

        for side, ink in (
            ("top", dark[frame.top, frame.left : frame.right + 1]),
            ("bottom", dark[frame.bottom, frame.left : frame.right + 1]),
            ("left", dark[frame.top : frame.bottom + 1, frame.left]),
            ("right", dark[frame.top : frame.bottom + 1, frame.right]),
        ):
            assert ink.all(), f"the frame's {side} side is broken"

    def test_the_corner_box_is_empty(self, spec, page) -> None:
        layout = compute_layout(*_clue_sets(**self.CASE), spec)
        frame = layout.frame
        dark = _dark(page)
        rule = layout.thick_rule

        corner = dark[
            frame.top + rule : layout.grid_top - rule,
            frame.left + rule : layout.grid_left - rule,
        ]
        assert corner.size, "the corner box has an inside to be empty"
        assert not corner.any(), "the corner box where the two gutters meet is blank"

    def test_each_clue_band_is_boxed_off_from_the_grid(self, spec, page) -> None:
        """Both bands are closed on all four sides — the band/grid divider included."""
        layout = compute_layout(*_clue_sets(**self.CASE), spec)
        frame = layout.frame
        dark = _dark(page)

        # The column-clue band: frame top above it, the grid's top border below,
        # the grid's left border to its left, the frame's right side beyond it.
        assert dark[frame.top, layout.grid_left : frame.right + 1].all()
        assert dark[layout.grid_top, layout.grid_left : frame.right + 1].all()
        assert dark[frame.top : layout.grid_top + 1, layout.grid_left].all()
        assert dark[frame.top : layout.grid_top + 1, frame.right].all()
        # The row-clue band, the same four sides transposed.
        assert dark[layout.grid_top : frame.bottom + 1, frame.left].all()
        assert dark[layout.grid_top : frame.bottom + 1, layout.grid_left].all()
        assert dark[layout.grid_top, frame.left : layout.grid_left + 1].all()
        assert dark[frame.bottom, frame.left : layout.grid_left + 1].all()

    def test_the_panels_own_book_page_spec_is_framed(self) -> None:
        """The sheet the book really prints on is a framed one (ADR-0036/R2).

        The frame is decided by COMP-007, from the fact that a book page is a
        *placed* page, so the panel that builds the spec goes on deciding no
        geometry and still gets the frame.
        """
        # Owner decision 2026-11-09: no frame around the clues. The panel's
        # spec now states the frame (``BOOK_PUZZLE_FRAME``), off by default;
        # this module turns it back on (tests/helpers/legacy_book_layout.py),
        # and what it measures is the frame COMP-007 draws when it is on.
        from nonogram.admin import book_page_spec as module

        for page_number in (1, 2, 7, 8):
            spec = book_page_spec(None, page_number)
            assert spec.frame is module.BOOK_PUZZLE_FRAME, "the panel states the book's frame"
            assert spec.framed, f"interior page {page_number} is a framed page"
            assert compute_layout(*_clue_sets(15, 15, 3, 3), spec).frame is not None


# --------------------------------------------------------------------------
# AC: the default page spec is unchanged (CON-019, G-1)
# --------------------------------------------------------------------------


class TestPuzzleFrame_DefaultPageSpecIsUnchanged:
    """No sheet the CLI or the web lays out is framed, and none gains ink.

    The byte-level tripwire is ``tests/test_export_a4_golden.py`` and
    ``tests/property/test_cli_exports_byte_identity.py``; what this adds is the
    reason those stay green — the default sheet is not a framed sheet, and its
    raster puts no rule on the drawing's own edge.
    """

    CORPUS = (
        (10, 10, 1, 1),
        (10, 25, 3, 2),
        (15, 15, 4, 4),
        (20, 20, 5, 5),
        (25, 10, 2, 5),
        (30, 30, 9, 9),
    )

    def test_the_default_sheet_is_not_a_framed_sheet(self) -> None:
        assert DEFAULT_PAGE_SPEC.frame is None
        assert not DEFAULT_PAGE_SPEC.framed

    @pytest.mark.parametrize("case", CORPUS)
    def test_the_default_layout_carries_no_frame(self, case) -> None:
        row_clues, column_clues = _clue_sets(*case)

        without_spec = compute_layout(row_clues, column_clues)
        with_default = compute_layout(row_clues, column_clues, DEFAULT_PAGE_SPEC)

        assert without_spec.frame is None
        assert without_spec == with_default, "no spec and the default spec are one call"

    @pytest.mark.parametrize("case", CORPUS)
    def test_the_default_raster_leaves_the_drawings_edge_unruled(self, case) -> None:
        """The corner box's left edge carries no rule — which is the frame's.

        An A4 page's corner box (where the two gutters meet) is blank on all
        four of its own sides today. A frame would rule two of them, so ink
        anywhere down the drawing's left edge, inside the column gutter, is the
        one pixel-level signature this card could have leaked onto A4.
        """
        row_clues, column_clues = _clue_sets(*case)
        layout = compute_layout(row_clues, column_clues)
        page = render_image(_payload(*case))
        dark = _dark(page)
        rule = layout.thick_rule

        assert layout.grid_left > layout.margin, "this case really has a row gutter"
        assert layout.grid_top > layout.margin, "and a column gutter"
        corner = dark[
            layout.margin + rule : layout.grid_top - rule,
            layout.margin + rule : layout.grid_left - rule,
        ]
        assert corner.size
        assert not corner.any(), "an A4 page's corner box is blank, frame or no frame"
        edge = dark[layout.margin + rule : layout.grid_top - rule, layout.margin]
        assert not edge.any(), "no rule runs down an A4 drawing's left edge"

    def test_a_sheet_can_still_be_framed_or_not_on_purpose(self) -> None:
        """``frame=`` states it outright, whichever way the sheet would default."""
        row_clues, column_clues = _clue_sets(15, 15, 3, 3)

        framed_a4 = replace(DEFAULT_PAGE_SPEC, frame=True)
        unframed_book = _spec(frame=False)

        assert framed_a4.framed
        assert compute_layout(row_clues, column_clues, framed_a4).frame is not None
        assert not unframed_book.framed
        assert compute_layout(row_clues, column_clues, unframed_book).frame is None

    @pytest.mark.parametrize("bad", [0, 1, "yes", "true"])
    def test_a_spec_refuses_a_frame_that_is_not_a_verdict(self, bad) -> None:
        with pytest.raises(ValueError, match="frame"):
            _spec(frame=bad)


# --------------------------------------------------------------------------
# AC: geometry is unmoved by the frame (G-3)
# --------------------------------------------------------------------------


class TestPuzzleFrame_GeometryIsUnmovedByTheFrame:
    """The frame adds ink and moves nothing — CARD-116's figures stay put."""

    def test_the_thirty_by_thirty_with_nine_deep_clues_still_prints_at_4_885_mm(self) -> None:
        spec = _spec()
        layout = compute_layout(*_clue_sets(30, 30, 9, 9), spec)

        assert layout.frame is not None
        # 4.97 mm until CON-018's margins were amended on 2026-10-17
        # (CARD-222): 190.5 mm of usable width over 39 cells.
        assert layout.page.cell_mm == pytest.approx(4.8846, abs=0.005)

    def test_the_fifteen_by_fifteen_still_prints_at_the_standard_cell(self) -> None:
        spec = _spec()
        layout = compute_layout(*_clue_sets(15, 15, 4, 4), spec)

        assert layout.frame is not None
        assert layout.page.cell_mm == pytest.approx(STANDARD_CELL_MM, abs=0.005)

    @pytest.mark.parametrize(
        "case", [(30, 30, 9, 9), (15, 15, 4, 4), (10, 10, 1, 1), (25, 12, 7, 3)]
    )
    @pytest.mark.parametrize("parity", list(PageParity))
    def test_every_field_but_the_frame_is_what_it_was_unframed(self, case, parity) -> None:
        row_clues, column_clues = _clue_sets(*case)
        framed = compute_layout(row_clues, column_clues, _spec(parity=parity))
        plain = compute_layout(row_clues, column_clues, _spec(parity=parity, frame=False))

        assert plain.frame is None
        assert framed.frame is not None
        assert replace(framed, frame=None) == plain, (
            "a framed page and an unframed one differ in the frame and nowhere else"
        )

    def test_the_rendered_page_is_the_unframed_one_plus_the_frames_own_ink(self) -> None:
        """Ink is only ever *added*: no pixel the unframed page inked is now white."""
        spec = _spec()
        case = dict(columns=20, rows=20, row_depth=4, column_depth=5)
        framed = _dark(render_image(_payload(**case), page_spec=spec))
        plain = _dark(render_image(_payload(**case), page_spec=replace(spec, frame=False)))

        assert not (plain & ~framed).any(), "the frame erased ink the page already had"
        assert (framed & ~plain).any(), "the frame drew nothing at all"


# --------------------------------------------------------------------------
# AC: the heavy rule and no other (ADR-0037/R2, G-2)
# --------------------------------------------------------------------------


class TestPuzzleFrame_UsesTheHeavyRuleOnly:
    """Every side is the heavy rule: twice the thin one, pure black, no third weight."""

    CASE = dict(columns=20, rows=20, row_depth=4, column_depth=5)

    @pytest.fixture(scope="class")
    @classmethod
    def spec(cls) -> PageSpec:
        return _spec()

    @pytest.fixture(scope="class")
    @classmethod
    def page(cls, spec) -> Image.Image:
        return render_image(_payload(**cls.CASE), page_spec=spec)

    def test_the_frame_carries_the_layouts_heavy_rule_and_no_new_weight(self, spec) -> None:
        layout = compute_layout(*_clue_sets(**self.CASE), spec)

        weights = {line.width for line in layout.grid_lines} | {layout.frame.width}
        assert weights == {layout.thin_rule, layout.thick_rule}, (
            "the frame introduced a third stroke weight"
        )
        assert layout.thick_rule == 2 * layout.thin_rule
        assert layout.thin_rule / PX_PER_MM >= MIN_THIN_RULE_MM

    def test_every_side_is_exactly_the_heavy_rule_thick_on_the_page(self, spec, page) -> None:
        layout = compute_layout(*_clue_sets(**self.CASE), spec)
        frame = layout.frame
        dark = _dark(page)
        # A row inside the column-clue band, clear of the frame's own top side:
        # the ink groups there are the frame's left side, the grid's verticals
        # and the frame's right side.
        row = frame.top + 2 * layout.thick_rule
        columns = _ink_columns(dark, row)
        assert len(columns) >= 3
        assert len(columns[0]) == frame.width, "the frame's left side is the heavy rule"
        assert len(columns[-1]) == frame.width, "and so is its right side"

        # A column inside the row-clue band, clear of the frame's left side.
        column = frame.left + 2 * layout.thick_rule
        rows = _ink_rows(dark, column)
        assert len(rows) >= 2
        assert len(rows[0]) == frame.width, "the frame's top side is the heavy rule"
        assert len(rows[-1]) == frame.width, "and so is its bottom side"

    def test_the_frames_pixels_are_pure_black(self, spec, page) -> None:
        frame = compute_layout(*_clue_sets(**self.CASE), spec).frame
        pixels = np.asarray(page.convert("RGB"))

        strips = (
            pixels[frame.top, frame.left : frame.right + 1],
            pixels[frame.bottom, frame.left : frame.right + 1],
            pixels[frame.top : frame.bottom + 1, frame.left],
            pixels[frame.top : frame.bottom + 1, frame.right],
        )
        for strip in strips:
            assert np.array_equal(strip, np.zeros_like(strip)), (
                "a frame rule is pure black, never an anti-aliased grey"
            )

    def test_the_frame_straddles_its_boundary_exactly_as_the_grids_border_does(
        self, spec, page
    ) -> None:
        """The card's rendering trap, pinned.

        Pillow centres a stroke on its coordinate. The frame is drawn **on**
        the drawing's edges, not inset from them, so its left side straddles
        the drawing's left edge exactly as the grid's right border straddles
        the grid's right edge. Equal offsets, both sides of zero — an inset
        frame would sit entirely at offsets >= 0 and fail here.
        """
        layout = compute_layout(*_clue_sets(**self.CASE), spec)
        frame = layout.frame
        dark = _dark(page)

        row = frame.top + 2 * layout.thick_rule
        columns = _ink_columns(dark, row)
        left_offsets = [column - frame.left for column in columns[0]]
        border_offsets = [column - layout.grid_right for column in columns[-1]]

        assert left_offsets == border_offsets, (
            "the frame's left side and the grid's right border are drawn to "
            f"different rules: {left_offsets} against {border_offsets}"
        )
        assert min(left_offsets) < 0 < max(left_offsets), (
            f"the frame is not centred on its boundary: offsets {left_offsets}"
        )


# --------------------------------------------------------------------------
# AC: a two-up page frames each puzzle separately (FR-040)
# --------------------------------------------------------------------------


class TestPuzzleFrame_PairIsFramedPerPuzzle:
    """Two puzzles to a page are two frames, not one around the pair."""

    @pytest.fixture(scope="class")
    @classmethod
    def pair(cls):
        found = compute_pair_layout(
            _clue_sets(10, 10, 2, 2), _clue_sets(12, 12, 3, 3), _spec()
        )
        assert found is not None, "this pair really does fit two-up"
        return found

    def test_each_slot_carries_its_own_frame_on_its_own_drawing(self, pair) -> None:
        for slot in (pair.upper, pair.lower):
            frame, placement = slot.frame, slot.page
            assert frame is not None
            assert (frame.left, frame.top, frame.right, frame.bottom) == (
                placement.drawing_left,
                placement.drawing_top,
                placement.drawing_right,
                placement.drawing_bottom,
            )
            assert frame.width == slot.thick_rule == 2 * slot.thin_rule

    def test_the_two_frames_are_separate_and_neither_encloses_the_pair(self, pair) -> None:
        upper, lower = pair.upper.frame, pair.lower.frame

        assert upper.bottom < lower.top, "the upper frame closes above the lower's"
        assert lower.top > pair.upper.page.usable_bottom - 1, (
            "the lower frame belongs to the lower slot"
        )
        assert upper != lower

    def test_a_slot_is_framed_exactly_as_the_single_page_it_would_have_been(self) -> None:
        """The pair's frame is the single page's, so there is one frame rule.

        The two clue sets differ, so what is compared is the *shape* of the
        answer — the frame's box is the slot's own drawing box, at the slot's
        own heavy rule — rather than two identical rectangles.
        """
        spec = _spec()
        single = compute_layout(*_clue_sets(10, 10, 2, 2), spec)
        pair = compute_pair_layout(
            _clue_sets(10, 10, 2, 2), _clue_sets(10, 10, 2, 2), spec
        )
        assert pair is not None

        assert pair.upper.frame.left == single.frame.left, "both are centred alike"
        # CARD-224: the single page's drawing floats at 42% of its puzzle
        # area's spare while the slot's sits one rule gap
        # (TWO_UP_RULE_GAP_MM) below its slot's band foot, so the two tops
        # are a known distance apart instead of equal — the slot's is the
        # band's foot plus that gap, and the single page's is lower.
        assert pair.upper.frame.top == pair.upper.page.drawing_top
        assert abs(
            (pair.upper.frame.top - pair.upper.page.band_bottom) * 25.4 / DPI
            - TWO_UP_RULE_GAP_MM
        ) <= 25.4 / DPI
        assert single.frame.top > pair.upper.frame.top
        assert pair.upper.frame.width == single.frame.width


# ==========================================================================
# CARD-146 — the frame reaches the printed two-up page
# ==========================================================================
#
# Everything below is stated on the **rendered interior** of a real book, the
# way ``tests/test_book_pdf_two_up.py`` states FR-040: the pages come out of
# ``BookPDFGenerator.interior_pages``, and where they are expected to put ink
# is worked out here from CON-018's profile in inches. ``compute_pair_layout``
# is not consulted for a single expected coordinate — it was *already* right
# before this card, which is exactly why a criterion phrased over it would
# have been green on a page with no frame on it.


#: The page's usable width, and the height left once a page reserves a band for
#: each of **two** puzzles: 193.675 mm and 236.35 mm on Book 1. The same two
#: figures ``tests/test_book_pdf_two_up.py`` states FR-040's shared cell from.
USABLE_WIDTH_MM = BOOK1_WIDTH_MM - GUTTER_MM - OUTSIDE_MM

#: The footer strip a two-up page reserves since CARD-248 (``INTERIOR_FOOTER_MM``
#: as this page's own pixels: 117 px, 9.878 mm; 353 px, 29.878 mm before CARD-392), and the height its two
#: drawings are left with. The strip carries both puzzles' QR groups and the
#: page's folio, so it comes out of the pair's height before anything is
#: fitted — and the lower slot's drawing now stops one two-up rule gap above
#: the footer rule rather than on the bottom margin. Written out here, as this file writes every
#: other figure out.
FOOTER_STRIP_PX = 117
FOOTER_STRIP_MM = FOOTER_STRIP_PX / PX_PER_MM
PAIR_HEIGHT_MM = (
    BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM - FOOTER_STRIP_MM
)

#: The pair these criteria are read on, and the puzzle that prints alone after
#: it so that a two-up slot and a single page can be compared **on one book**.
#: All three are Easy, so the interior is one level: the 2-page guide
#: (CARD-201), the "Easy" divider, the two-up page, the single page,
#: SOLUTIONS, then the answer section. UPPER and LOWER both qualify for
#: CARD-202's packing rule (width<=15 and height<=20, same tier, adjacent in
#: book order), so they share one packed answer page; SINGLE_PUZZLE (20x20)
#: doesn't qualify and still gets its own full answer page — two answer
#: pages total, not three.
#: **LOWER's gutters are 2 cells deep, not 3, since CARD-248.** The footer
#: strip that card reserves leaves a pair 199.605 mm rather than 229.492 mm,
#: and 27 cells of combined drawing height no longer clear NFR-008's standard
#: cell in it (7.39 mm): these criteria are read on a pair the **cap** binds,
#: so that the boxes below are exact 7.5 mm arithmetic and not a fit. One cell
#: shallower is 26 cells, 7.68 mm, capped at 7.5 — the same pair, measured
#: the same way.
UPPER_PUZZLE = dict(columns=10, rows=10, row_depth=2, column_depth=2)
LOWER_PUZZLE = dict(columns=12, rows=12, row_depth=2, column_depth=2)
SINGLE_PUZZLE = dict(columns=20, rows=20, row_depth=8, column_depth=8)

#: Which interior page is which, once the walk above has run. Asserted rather
#: than trusted by :func:`_book_pages`. CARD-200 (SCOPE+): a 1-page table of
#: contents now sits between the guide and the puzzle section (this book's
#: three puzzles fit Book 1's own TOC capacity on one page), so every page
#: number here is one more than before. CARD-206 (SCOPE+): the blank title /
#: copyright page is reserved as interior page 1, so every page number here
#: is one more again.
TWO_UP_PAGE = 6
SINGLE_PAGE = 7
INTERIOR_PAGES = 10


def _book() -> Book:
    """A book on CON-018's Book 1 profile, as a ``books`` row carries it."""
    return Book(
        book_id="book-146",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-146's frame criteria are read off.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{BOOK1_WIDTH_MM / 10:.2f}",
        trim_height_cm=f"{BOOK1_HEIGHT_MM / 10:.2f}",
        gutter_margin_cm=f"{GUTTER_MM / 10:.2f}",
        outside_margin_cm=f"{OUTSIDE_MM / 10:.2f}",
    )


def _book_puzzle(
    *, columns: int, rows: int, row_depth: int, column_depth: int, puzzle_id: str
) -> dict:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _grid(columns, rows, row_depth, column_depth)
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": "Snowflake",
        "difficulty_tier": "easy",
    }


def _book_pages() -> list[Image.Image]:
    """The interior of the book above; ``pages[n - 1]`` is interior page ``n``.

    The two page numbers the criteria below index by are checked here, by what
    is drawn on them, so a walk that stopped pairing would fail as a wrong page
    count rather than as a frame mysteriously missing from a single page.
    """
    # CARD-329: the one page-source seam of this module. The puzzle pages
    # arrive as content-stream operators under ADR-0042/R1 and the kinds that
    # stay raster arrive as bitmaps (ADR-0042/R2); every criterion below is
    # stated on *device pixels*, so `interior_images` puts both media in that
    # one domain -- a raster page unchanged, an operators page rasterised by
    # poppler at the page's own DPI (CARD-330: an instrument has to say which
    # domain it is in). No criterion was weakened and no tolerance widened.
    pages = interior_images(
        BookPDFGenerator(_book()).interior_pages(
            [
                _book_puzzle(**UPPER_PUZZLE, puzzle_id="one"),
                _book_puzzle(**LOWER_PUZZLE, puzzle_id="two"),
                _book_puzzle(**SINGLE_PUZZLE, puzzle_id="three"),
            ]
        )
    )
    assert len(pages) == INTERIOR_PAGES, f"the book printed {len(pages)} pages"
    assert len(drawings_of(pages[TWO_UP_PAGE - 1])) == 2, "the pair really shares a page"
    assert len(drawings_of(pages[SINGLE_PAGE - 1])) == 1, "and the 20x20 prints alone"
    return pages


@pytest.fixture(scope="module")
def pages() -> list[Image.Image]:
    """This module's one book, drawn once for the whole module (CARD-218).

    Five places used to ask for this interior — four class-scoped ``pages``
    fixtures and one inline call — so the same three puzzles were laid out and
    drawn five times to be measured five ways. The measurement that moved it
    here: the four class renders plus the inline one cost 0.418 s of repeated
    work, every byte of it identical, which was the largest single
    identical-input render duplication anywhere in CARD-218's nine files.

    **Module, not session** (the card's rule 2): a session fixture would hold
    this book's page bitmaps alive for the rest of the run, and
    ``test_book_pdf_memory.py`` exists because a page alive while the next is
    built was a real defect (CARD-145).

    **Read-only.** Every consumer measures ink through ``np.asarray`` /
    ``drawings_of`` / ``drawing_of``, all of which read the image and return
    something new; none draws on it. A test that needs to draw must take
    ``page.copy()``, and
    :meth:`TestPuzzleFrame_TheSharedInteriorIsNotMutated.test_the_shared_pages_are_handed_out_as_they_were_drawn`
    is the control that fails if one forgets: it digests every page after the
    module's measuring tests have run and compares it with the digest taken
    when the book was drawn.
    """
    drawn = _book_pages()
    _SHARED_DIGEST.extend(_page_digest(page) for page in drawn)
    return drawn


#: A sha256 per page of :func:`pages` as it was drawn, filled by the fixture
#: and read back by its mutation control. A list rather than a module-level
#: rebinding so the control cannot pass by reading a name the fixture never
#: set — and a *digest* rather than the bytes, because this list outlives the
#: fixture (see :func:`_page_digest`, and the retention control at the end of
#: this file, which holds every module-level accumulator of this file to
#: exactly 32 B per page of the book it signed).
_SHARED_DIGEST: list[bytes] = []


# --------------------------------------------------------------------------
# FR-040's pair arithmetic, in millimetres, written out here
# --------------------------------------------------------------------------


def _across(puzzle: dict) -> int:
    """The drawing's width in cells: the row-clue gutter plus the grid."""
    return puzzle["row_depth"] + puzzle["columns"]


def _down(puzzle: dict) -> int:
    """The drawing's height in cells: the column-clue gutter plus the grid."""
    return puzzle["column_depth"] + puzzle["rows"]


def _shared_cell_mm(upper: dict, lower: dict) -> float:
    """FR-040's shared cell for one pair on one Book 1 page, in millimetres.

    **CARD-204 Fix 4 (owner decision, 2026-10-12, "fixed universal
    reserve").** Re-derives ``compute_pair_layout``'s own "only widen the
    fit when the lower slot's own natural spare can't already hold the
    fixed reserve" rule independently, in millimetres.
    """
    natural = min(
        STANDARD_CELL_MM,
        USABLE_WIDTH_MM / max(_across(upper), _across(lower)),
        PAIR_HEIGHT_MM / (_down(upper) + _down(lower)),
    )
    natural_spare_mm = USABLE_WIDTH_MM - _across(lower) * natural
    if natural_spare_mm >= RESERVE_MM:
        return natural
    return min(
        STANDARD_CELL_MM,
        (USABLE_WIDTH_MM - RESERVE_MM) / max(_across(upper), _across(lower)),
        PAIR_HEIGHT_MM / (_down(upper) + _down(lower)),
    )


def _two_up_rule_gap_mm(upper: dict, lower: dict) -> float:
    """The room a two-up page leaves between each drawing and the rule above it.

    Each two-up drawing sits ``TWO_UP_RULE_GAP_MM`` below its own band's foot,
    and the lower one ends the same gap above the footer reserve, so neither
    touches the header, band or footer rule — capped at a quarter of the
    vertical slack the fit left (three gaps spent, at least one more left
    between the slots), so the gap never changes the cell or the pairing.
    Written out from the page's millimetres rather than read from
    ``compute_pair_layout``.
    """
    slack_mm = PAIR_HEIGHT_MM - (_down(upper) + _down(lower)) * _shared_cell_mm(upper, lower)
    return min(TWO_UP_RULE_GAP_MM, max(slack_mm, 0.0) / 4)


def _expected_pair_boxes(
    upper: dict,
    lower: dict,
    parity: PageParity = PageParity.ODD,
    *,
    page_number: int = TWO_UP_PAGE,
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    """Where the two drawings sit on a two-up page: ``(left, top, right, bottom)``.

    Both boxes in device pixels — **fractional**, deliberately, exactly as
    :func:`_expected_box` leaves a single page's. A boundary lands on a whole
    pixel only by luck, and the two questions asked of these numbers want
    different things of the fraction: "is there ink on this rule" wants a whole
    pixel inside a six-pixel stroke (:func:`_pixel_box`), and "which side of the
    boundary do the stroke's pixels fall on" wants the boundary itself, because
    a boundary rounded to a whole pixel first is a boundary that has already
    moved up to half a pixel in the direction the answer is about.

    Each drawing is **centred** across the usable width (CARD-224, FR-032) on
    the **shared** cell; the upper one's top edge is one two-up rule gap
    (``TWO_UP_RULE_GAP_MM``, capped at a quarter of the pair's vertical slack)
    below its own slot's band foot (top margin plus band — the row every placed
    drawing used before CARD-224: the 42% float is the single page's, and
    splitting a page's puzzle area between two slots is CARD-226's) and the
    lower one's bottom edge is that gap above the **footer rule** — one
    :data:`FOOTER_STRIP_MM` above the bottom margin since CARD-248, where it
    was the margin itself before — with its own band in the 12 mm above its
    drawing's top less that gap,
    which is the placement ``tests/test_book_pdf_two_up.py`` states AC-251's
    lower band from.

    That rectangle **is** the frame: its left and top are the outer edges of
    the two clue gutters and its right and bottom the grid's own outer border.

    **History (CARD-204 Fix 1/Fix 2, reverted by Fix 3, restored as a fixed
    constant by Fix 4 — owner decision, 2026-10-12, "fixed universal
    reserve").** Fix 1/Fix 2 pulled the lower box alone back toward the
    gutter by a page/book-specific folio reserve (INV-010, cycle-1 F-1,
    cycle-2 F-5). Fix 3 removed the reserve mechanism entirely. Fix 4
    restored it as a *fixed* amount (:data:`RESERVE_MM`, never derived from
    ``page_number`` or any book content). **CARD-224 drops the shift with the
    anchor**: centring leaves each slot half its own spare on *both* sides, so
    the lower box is placed exactly like the upper one and
    :data:`RESERVE_MM` no longer enters this helper. The reserve is still
    taken out of the shared cell's own fit, which is why the cell below is
    unchanged (G-1). This helper still does not take or need a
    ``page_number``, kept only so every call site below (which names one for
    its own documentation value) does not need editing.
    """
    cell = _shared_cell_mm(upper, lower)
    left_margin = OUTSIDE_MM if parity is PageParity.EVEN else GUTTER_MM

    def box(
        puzzle: dict, top_mm: float, *, is_lower: bool = False
    ) -> tuple[float, float, float, float]:
        spare_mm = USABLE_WIDTH_MM - _across(puzzle) * cell
        left_mm = left_margin + max(spare_mm, 0.0) / 2
        return (
            left_mm * PX_PER_MM,
            top_mm * PX_PER_MM,
            (left_mm + _across(puzzle) * cell) * PX_PER_MM,
            (top_mm + _down(puzzle) * cell) * PX_PER_MM,
        )

    gap_mm = _two_up_rule_gap_mm(upper, lower)

    return (
        box(upper, TOP_MM + BAND_MM + gap_mm),
        box(
            lower,
            # CARD-248: the lower drawing's bottom edge sits above the
            # **footer rule** — one footer strip above the bottom margin —
            # not on the margin itself, because the page now reserves a
            # footer carrying both puzzles' QR groups and its own folio; and
            # one rule gap above that rule, so the two do not touch.
            BOOK1_HEIGHT_MM - BOTTOM_MM - FOOTER_STRIP_MM - gap_mm - _down(lower) * cell,
            is_lower=True,
        ),
    )


# CARD-200 (SCOPE+): the default `parity` of each box helper below used to
# match `TWO_UP_PAGE`/`SINGLE_PAGE`'s own, un-shifted parity (4 = even,
# 5 = odd); the 1-page table of contents moves both pages by one, flipping
# each one's parity, so the defaults flip too — no caller in this file
# passes `parity` explicitly, so this is the one place that needs it.
def _expected_single_box(puzzle: dict, parity: PageParity = PageParity.EVEN):
    """The same rectangle for the puzzle that prints alone, on its own page."""
    return _expected_box(
        _spec(parity=parity),
        puzzle["columns"],
        puzzle["rows"],
        puzzle["row_depth"],
        puzzle["column_depth"],
    )


def _pixel_box(box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    """One expected box at whole-pixel precision, for asking a page about ink.

    Safe to round because every side of the frame is the heavy rule — six
    device pixels at the cell a book prints, and never under
    ``2 * MIN_THIN_RULE_MM`` — so a whole pixel within half a pixel of the
    boundary is a pixel the stroke covers whichever way the boundary fell.
    """
    return tuple(round(edge) for edge in box)  # type: ignore[return-value]


def _runs_across(dark: np.ndarray, row: int, lo: int, hi: int) -> list[list[int]]:
    """Runs of ink along ``row`` between ``lo`` and ``hi``, in page coordinates.

    A two-up page carries two drawings side by side down the sheet and clue
    digits inside each one's gutters, so "the groups of ink on this pixel row"
    is only a measurement of *one* slot's rules when it is bounded to that
    slot's own span. Both bounds are always stated by the caller.
    """
    return [[lo + index for index in run] for run in _groups(np.flatnonzero(dark[row, lo:hi]))]


def _runs_down(dark: np.ndarray, column: int, lo: int, hi: int) -> list[list[int]]:
    """The same down one pixel column, bounded to one slot's rows."""
    return [
        [lo + index for index in run] for run in _groups(np.flatnonzero(dark[lo:hi, column]))
    ]


#: How far either side of a boundary a rule's own pixels can possibly fall: a
#: heavy rule is well under this at any cell a book prints, and a window this
#: wide cannot reach the next rule (the smallest cell FR-040 will pair at is
#: 7.0 mm, which is 82 px).
#:
#: **12 since CARD-222**, down from 20. The frame's header rule is drawn
#: inside the title band, an eighth of its depth above the band's foot — 18 px
#: on Book 1's 12 mm band at 300 DPI — and the band's foot is where a puzzle
#: page's drawing begins when the puzzle area cannot hold it clear of both
#: rules, as it is where *every* placed drawing began until CARD-224 retired
#: FR-032's fixed-top-edge clause (AC-378/AC-379). A 20 px window above the
#: drawing's top edge therefore reached that rule and read it as the frame's
#: own top side; the drawings this constant is used on are measured at their
#: own slot's band foot (plus the two-up rule gap, which only moves them
#: further from that rule), so the float does not move the figure.
#: Measured, not guessed: the heaviest rule the book strokes is 6 px, so 12 px
#: is twice the widest a rule can be and still 6 px clear of the header rule.
_RULE_WINDOW_PX = 12

#: How lopsided a stroke centred on its boundary may still measure, in device
#: pixels, once two unavoidable whole-pixel steps are spent:
#:
#: * the boundary itself is a fraction of a pixel, and the layout puts the rule
#:   on the whole pixel nearest it — up to 1 px of the difference;
#: * Pillow centres an **even**-width stroke with one more pixel on one side
#:   than the other — the remaining 1 px.
#:
#: So the two halves of a heavy rule read as far apart as 3 px while the rule is
#: exactly where CARD-144 put it. That still leaves the property teeth: a frame
#: drawn even **one** pixel in from its boundary measures 5 px apart, and one
#: inset by the half rule that a "draw it inside the box" reading would give
#: has no ink outside the boundary at all.
_STRADDLE_SLACK_PX = 3.0


# --------------------------------------------------------------------------
# AC-1: a printed pair is two framed puzzles
# --------------------------------------------------------------------------


class TestPuzzleFrame_PairIsFramedOnThePrintedPage:
    """Each of a two-up page's two drawings carries its own closed frame.

    Read off the interior's page 3 with the project's own ink measurer
    (``tests/helpers/two_up_ink.drawings_of``, which splits the page and then
    measures each half exactly as a single puzzle page is measured). That
    helper decides ``framed`` by asking the page two questions — is the
    outermost full-length rule *on* the drawing's own edge, and is the rule
    immediately inside it stroked just as heavily — so nothing here is told
    where a frame is; it is found or it is not.
    """

    def test_both_slots_read_back_as_framed_drawings(self, pages) -> None:
        """The gap, stated: before this card both slots read ``framed=False``."""
        upper, lower = drawings_of(pages[TWO_UP_PAGE - 1])

        assert upper.framed is True, "the upper slot printed without its frame"
        assert lower.framed is True, "the lower slot printed without its frame"

    def test_the_single_page_of_the_same_book_is_framed_too(self, pages) -> None:
        """The positive control: the measurer can see a frame it is shown one.

        Page 4 was already framed before this card, so a run where page 3 is
        bare and page 4 is not is the gap; a run where *both* are bare is a
        broken measurer, and this tells the two apart.
        """
        assert drawing_of(pages[SINGLE_PAGE - 1]).framed is True

    def test_each_slots_frame_is_that_slots_own_drawing_box(self, pages) -> None:
        """Four sides of unbroken ink on the rectangle CON-018's millimetres put there."""
        dark = _dark(pages[TWO_UP_PAGE - 1])
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for slot, box in zip(("upper", "lower"), boxes):
            left, top, right, bottom = _pixel_box(box)
            for side, ink in (
                ("top", dark[top, left : right + 1]),
                ("bottom", dark[bottom, left : right + 1]),
                ("left", dark[top : bottom + 1, left]),
                ("right", dark[top : bottom + 1, right]),
            ):
                assert ink.all(), f"the {slot} slot's frame is broken on its {side} side"

    def test_each_slot_reads_back_its_own_gutters_from_behind_the_frame(
        self, pages
    ) -> None:
        """The frame is a *whole clue gutter* out from the grid, on both axes.

        The two sides a frame actually adds are its left and its top; its right
        and bottom land on the grid's border, which was inked before this card.
        So the evidence that the new ink is a frame and not a re-stroke of what
        was already there is that the outermost rule stands the clues' own depth
        away from the grid's — which is what makes the corner box exist.
        """
        drawings = drawings_of(pages[TWO_UP_PAGE - 1])

        for drawing, puzzle in zip(drawings, (UPPER_PUZZLE, LOWER_PUZZLE)):
            assert (drawing.columns, drawing.rows) == (
                puzzle["columns"],
                puzzle["rows"],
            ), "the slot does not read back its own grid from behind the frame"
            assert (
                _gutter_cells(drawing.left, drawing.grid_left, drawing.cell)
                == puzzle["row_depth"]
            )
            assert (
                _gutter_cells(drawing.top, drawing.grid_top, drawing.cell)
                == puzzle["column_depth"]
            )

    def test_the_corner_box_of_each_slot_is_closed_and_empty(self, pages) -> None:
        """Where the two clue gutters meet: ruled on all four sides, blank inside."""
        page = pages[TWO_UP_PAGE - 1]
        dark = _dark(page)
        drawings = drawings_of(page)
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for drawing, box in zip(drawings, boxes):
            left, top, _right, _bottom = _pixel_box(box)
            rule = round(drawing.cell / 20) + 2  # clear of every stroke's own pixels
            corner = dark[
                top + rule : drawing.grid_top - rule,
                left + rule : drawing.grid_left - rule,
            ]
            assert corner.size, "the corner box has an inside to be empty"
            assert not corner.any(), "the corner box where the two gutters meet is blank"

    def test_each_clue_band_of_each_slot_is_boxed_off_from_the_grid(self, pages) -> None:
        """Both bands closed on all four sides — the band/grid divider included."""
        page = pages[TWO_UP_PAGE - 1]
        dark = _dark(page)
        drawings = drawings_of(page)
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for drawing, box in zip(drawings, boxes):
            left, top, right, bottom = _pixel_box(box)
            grid_left, grid_top = drawing.grid_left, drawing.grid_top
            # The column-clue band: the frame's top above it, the grid's own top
            # border below, the grid's left border beside it, the frame's right
            # side beyond.
            assert dark[top, grid_left : right + 1].all()
            assert dark[grid_top, grid_left : right + 1].all()
            assert dark[top : grid_top + 1, grid_left].all()
            assert dark[top : grid_top + 1, right].all()
            # The row-clue band, the same four sides transposed.
            assert dark[grid_top : bottom + 1, left].all()
            assert dark[grid_top : bottom + 1, grid_left].all()
            assert dark[grid_top, left : grid_left + 1].all()
            assert dark[bottom, left : grid_left + 1].all()

    def test_the_pair_is_two_rectangles_and_not_one_around_both(self, pages) -> None:
        """Nothing is ruled across the strip between the slots."""
        dark = _dark(pages[TWO_UP_PAGE - 1])
        upper_box, lower_box = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)
        upper_bottom, lower_top = _pixel_box(upper_box)[3], _pixel_box(lower_box)[1]

        assert upper_bottom < lower_top, "the upper frame closes above the lower's"
        between = dark[upper_bottom + 10 : lower_top - 10]
        assert between.size, "there is a strip between the two slots to inspect"
        # The lower slot's band is lettered in this strip, so there IS ink here
        # — but no *rule*: no pixel column is unbroken ink right through it,
        # which is what a side of one rectangle enclosing both pairs would be.
        assert not between.all(axis=0).any(), (
            "a rule runs down the strip between the two slots"
        )


# --------------------------------------------------------------------------
# AC-2: the heavy rule and no other, on a two-up page (ADR-0037/R2, G-2)
# --------------------------------------------------------------------------


class TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly:
    """Every frame rule on a printed pair is the heavy weight, and pure black."""

    #: The owner's three declared grid weights in points (ADR-0037/R2 as
    #: amended 2026-10-17, CARD-227: 0.3 pt grey cell lines, 1.1 pt every fifth
    #: line — 0.8 pt until the owner raised it on 2026-11-08 — 1.3 pt outer
    #: border). Written out, not imported from the writer.
    DECLARED_PT = (0.3, 1.1, 1.3)
    #: What poppler inks them as at 300 DPI, MEASURED on this page (CARD-322,
    #: CARD-342's finding): 2 / 4 / 6 pixel runs, grey 89 for the first and
    #: pure black for the other two, no blend pixels. For the thin and border
    #: weights that is ceil(pt*300/72) = ceil(1.25), ceil(5.42); the 1.1 pt
    #: fifth (4.58 px nominal) still inks as a 4 px run, as the 0.8 pt fifth
    #: (3.33 px) did — re-measured on 2026-11-08 across every grid rule of
    #: this book's pages, so the raster tells the fifth from its neighbours by
    #: run width but not the new figure from the old: the STREAM tests below
    #: are what pin 1.1 pt.
    MEASURED_PX = (2, 4, 6)

    @staticmethod
    def weight_findings(widths_pt, runs_px=None) -> list[str]:
        """Every way a page's stroke widths (and a grid row's runs) break the
        owner's three-weight claim. Pure, so the plants can drive it."""
        found: list[str] = []
        declared = TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly.DECLARED_PT
        used = {round(w, 4) for w in widths_pt}
        for name, weight in zip(("thin", "fifth", "border"), declared):
            if weight not in used:
                found.append(f"the {name} weight {weight} pt is not stroked")
        if not declared[0] < declared[1] < declared[2]:
            found.append("the declared weights are not thin < fifth < border")
        if runs_px is not None:
            distinct = sorted({len(run) for run in runs_px})
            expected = list(TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly.MEASURED_PX)
            if distinct != expected:
                found.append(f"a grid row shows run widths {distinct}, not {expected}")
            else:
                widths = [len(run) for run in runs_px]
                for index, width in enumerate(widths):
                    border = index in (0, len(widths) - 1)
                    fifth = index % 5 == 0 and not border
                    want = expected[2] if border else expected[1] if fifth else expected[0]
                    if width != want:
                        found.append(f"rule {index} is {width} px, not {want}")
        return found

    @staticmethod
    def _weights(dark: np.ndarray, drawing) -> tuple[int, int, int]:
        """``(thin, fifth, border)`` run widths on a row through the grid.

        Measured on a pixel row half a cell below the grid's top border and
        bounded to the grid itself (see the history of this helper: the bound
        keeps clue digits out). Returns the three DISTINCT widths, smallest
        first, and refuses anything but three.
        """
        row = drawing.grid_top + round(drawing.cell / 2)
        runs = _runs_across(
            dark, row, drawing.grid_left, drawing.grid_right + _RULE_WINDOW_PX
        )
        widths = sorted({len(run) for run in runs})
        assert len(widths) == 3, f"a row through the grid shows weights {widths}"
        return widths[0], widths[1], widths[2]

    @staticmethod
    def _two_up_stream_widths() -> list[float]:
        """Every stroke width the two-up page's own content stream sets, in points."""
        from tests.helpers import pdf_vector

        raw = BookPDFGenerator(_book()).interior_pages(
            [
                _book_puzzle(**UPPER_PUZZLE, puzzle_id="one"),
                _book_puzzle(**LOWER_PUZZLE, puzzle_id="two"),
                _book_puzzle(**SINGLE_PUZZLE, puzzle_id="three"),
            ]
        )
        return pdf_vector.stroke_widths("\n".join(raw[TWO_UP_PAGE - 1].operators))

    def test_the_two_up_stream_strokes_the_three_declared_weights(self) -> None:
        """Exact widths from the STREAM: 0.3, 1.1 and 1.3 pt, thin < fifth < border."""
        widths = self._two_up_stream_widths()
        assert self.weight_findings(widths) == []
        assert self.DECLARED_PT[0] < self.DECLARED_PT[1] < self.DECLARED_PT[2]

    def test_a_missing_or_merged_weight_is_found(self) -> None:
        """Plants: one per weight, and two weights merged into one."""
        widths = self._two_up_stream_widths()
        assert self.weight_findings(widths) == []
        for weight in self.DECLARED_PT:
            planted = [w for w in widths if round(w, 4) != weight]
            assert self.weight_findings(planted), weight
        merged = [0.3 if round(w, 4) == 1.1 else w for w in widths]
        assert self.weight_findings(merged), "fifth merged into thin"
        merged = [1.3 if round(w, 4) == 1.1 else w for w in widths]
        assert self.weight_findings(merged), "fifth merged into border"

    def test_a_grid_row_shows_exactly_the_three_weights_at_their_positions(self, pages) -> None:
        """2 / 4 / 6 px, the 4 px runs at every fifth rule, the 6 px runs the borders."""
        dark = _dark(pages[TWO_UP_PAGE - 1])
        for drawing in drawings_of(pages[TWO_UP_PAGE - 1]):
            row = drawing.grid_top + round(drawing.cell / 2)
            runs = _runs_across(dark, row, drawing.grid_left, drawing.grid_right + _RULE_WINDOW_PX)
            assert self.weight_findings(list(self.DECLARED_PT), runs) == []
            assert self._weights(dark, drawing) == self.MEASURED_PX
            # Plants on the row itself: an extra genuine run width, and two
            # weights merged (every fifth rule drawn as a thin one).
            extra = [list(run) for run in runs]
            extra[1] = extra[1] + [extra[1][-1] + 1]
            assert self.weight_findings(list(self.DECLARED_PT), extra)
            flat = [list(run)[:2] if len(run) == 4 else list(run) for run in runs]
            assert self.weight_findings(list(self.DECLARED_PT), flat)

    def test_every_frame_side_is_the_border_weight_and_no_new_weight(self, pages) -> None:
        page = pages[TWO_UP_PAGE - 1]
        dark = _dark(page)
        drawings = drawings_of(page)
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for drawing, box in zip(drawings, boxes):
            left, top, right, bottom = _pixel_box(box)
            _thin, _fifth, thick = self._weights(dark, drawing)
            assert bottom - top > 4 * thick, "these crops really are inside the drawing"
            columns = _runs_across(
                dark, top + 2 * thick, left - _RULE_WINDOW_PX, right + _RULE_WINDOW_PX
            )
            assert len(columns) >= 3
            assert abs(columns[0][0] - left) <= thick, (
                "the leftmost rule in this band is not on the drawing's own left "
                f"edge ({columns[0][0]} against {left}) -- there is no frame here, "
                "only the grid's border a whole clue gutter further in"
            )
            assert len(columns[0]) == thick, "the frame's left side is not the border weight"
            assert len(columns[-1]) == thick, "nor is its right side"
            rows = _runs_down(
                dark, left + 2 * thick, top - _RULE_WINDOW_PX, bottom + _RULE_WINDOW_PX
            )
            assert len(rows) >= 2
            assert abs(rows[0][0] - top) <= thick, (
                "the topmost rule in this gutter is not on the drawing's own top "
                f"edge ({rows[0][0]} against {top})"
            )
            assert len(rows[0]) == thick, "the frame's top side is not the border weight"
            assert len(rows[-1]) == thick, "nor is its bottom side"

    def test_the_pair_and_the_single_page_stroke_the_same_three_weights(self, pages) -> None:
        """Not the same pixel counts' cells (the pages print different cells) but
        the same three widths, so a fourth weight invented for the pair shows."""
        two_up, single = pages[TWO_UP_PAGE - 1], pages[SINGLE_PAGE - 1]
        reference = self._weights(_dark(single), drawing_of(single))
        assert reference == self.MEASURED_PX
        for drawing in drawings_of(two_up):
            assert self._weights(_dark(two_up), drawing) == reference
        assert drawing_of(single).cell != drawings_of(two_up)[0].cell

    def test_the_frames_pixels_are_pure_black(self, pages) -> None:
        pixels = np.asarray(pages[TWO_UP_PAGE - 1].convert("RGB"))

        for box in _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE):
            left, top, right, bottom = _pixel_box(box)
            for strip in (
                pixels[top, left : right + 1],
                pixels[bottom, left : right + 1],
                pixels[top : bottom + 1, left],
                pixels[top : bottom + 1, right],
            ):
                assert np.array_equal(strip, np.zeros_like(strip)), (
                    "a frame rule on a two-up page is pure black, never a grey"
                )


# --------------------------------------------------------------------------
# AC-3: placement on a pair straddles its boundary as a single page's does
# --------------------------------------------------------------------------


class TestPuzzleFrame_TwoUpStraddlesItsBoundaryLikeASinglePage:
    """The two presentations agree: both frames sit **on** their boundary.

    Pillow centres a stroke on its coordinate, so half a rule drawn on a box's
    edge falls outside the box. CARD-144 chose that for a single page because
    it is what the grid's own outer border already does. A pair drawn with an
    *inset* frame — a whole rule in from the edge the horizontal rules start
    at — would still look framed in a thumbnail and would still pass every
    "is there ink here" question; what tells the two apart is which side of the
    boundary the stroke's pixels fall on, and that is what is measured here,
    against boundaries worked out in millimetres.
    """

    @staticmethod
    def _straddle(dark: np.ndarray, row: int, boundary: float) -> tuple[float, float]:
        """How far a rule's ink reaches either side of ``boundary``, in pixels.

        The stroke is read in a window narrow enough to hold one rule and no
        other (:data:`_RULE_WINDOW_PX`); ``(outside, inside)`` is how far its
        ink extends below ``boundary`` and how far above it, counting a pixel
        as the unit interval it covers. A stroke centred on the boundary gives
        two roughly equal halves, both positive. A stroke drawn *inside* its
        box gives ``outside <= 0``.
        """
        window = round(boundary)
        runs = _runs_across(
            dark, row, window - _RULE_WINDOW_PX, window + _RULE_WINDOW_PX
        )
        assert len(runs) == 1, f"the window about {boundary:.2f} holds {len(runs)} rules"
        return boundary - runs[0][0], (runs[0][-1] + 1) - boundary

    def _assert_centred(self, dark, row: int, boundary: float, what: str) -> float:
        """``boundary`` falls inside the stroke, with equal ink either side."""
        outside, inside = self._straddle(dark, row, boundary)

        assert outside > 0, (
            f"{what} is drawn inside its boundary, not on it: its ink starts "
            f"{-outside:.2f} px past {boundary:.2f}"
        )
        assert inside > 0, f"{what} is drawn outside its boundary altogether"
        assert abs(outside - inside) <= _STRADDLE_SLACK_PX, (
            f"{what} is out of step with its boundary: {outside:.2f} px of ink "
            f"outside it against {inside:.2f} px inside"
        )
        return outside + inside

    def test_each_slots_left_side_straddles_the_drawings_left_edge(self, pages) -> None:
        """And the grid's right border, which the frame continues, agrees."""
        dark = _dark(pages[TWO_UP_PAGE - 1])
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for slot, (left, top, right, _bottom) in zip(("upper", "lower"), boxes):
            row = round(top) + 30  # inside the column-clue band
            frame = self._assert_centred(dark, row, left, f"the {slot} slot's frame")
            border = self._assert_centred(dark, row, right, f"the {slot} slot's border")
            assert frame == border, (
                f"the {slot} slot's frame is {frame} px of ink where the grid's "
                f"own border beside it is {border}"
            )

    def test_a_two_up_slot_and_a_single_page_place_the_stroke_alike(self, pages) -> None:
        """The card's whole claim, in one comparison, on one book.

        The two pages print different cells and their drawings start at
        different fractions of a pixel, so what must agree is not a coordinate
        and not a list of offsets: it is that both presentations answer the
        *same* question the same way — the boundary falls inside the stroke,
        with equal ink either side of it. A pair framed a rule inside its box
        fails here and nowhere else in this module.
        """
        two_up, single = pages[TWO_UP_PAGE - 1], pages[SINGLE_PAGE - 1]
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)
        single_left, single_top, _right, _bottom = _expected_single_box(SINGLE_PUZZLE)

        alone = self._straddle(_dark(single), round(single_top) + 30, single_left)
        assert min(alone) > 0, f"the single page's frame is not on its edge: {alone}"

        for slot, (left, top, _r, _b) in zip(("upper", "lower"), boxes):
            paired = self._straddle(_dark(two_up), round(top) + 30, left)
            assert min(paired) > 0, (
                f"the {slot} slot's frame is not on its edge: {paired}"
            )
            assert sum(paired) == sum(alone), (
                f"the {slot} slot strokes {sum(paired)} px where a single page "
                f"of the same book strokes {sum(alone)}"
            )
            assert abs(
                (paired[0] - paired[1]) - (alone[0] - alone[1])
            ) <= _STRADDLE_SLACK_PX, (
                f"the {slot} slot places its frame at {paired} about its own "
                f"boundary where a single page places it at {alone}"
            )


# --------------------------------------------------------------------------
# AC-4: ink only — no cell, origin or page geometry moved (G-3)
# --------------------------------------------------------------------------


class TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame:
    """CARD-127's and CARD-118's measured figures, on the framed pair."""

    def test_the_pair_still_prints_at_the_shared_cell_fr_040_measures(
        self, pages
    ) -> None:
        """CARD-127's figure: both slots on one cell, and it is FR-040's own."""
        expected = _shared_cell_mm(UPPER_PUZZLE, LOWER_PUZZLE)
        assert expected == pytest.approx(STANDARD_CELL_MM), "this pair fits the cap"

        for drawing in drawings_of(pages[TWO_UP_PAGE - 1]):
            assert drawing.cell / PX_PER_MM == pytest.approx(expected, abs=0.05)

    def test_the_upper_slot_still_starts_on_the_bands_own_foot(self, pages) -> None:
        """CARD-118's EC-022, as CARD-224 leaves it: top margin plus band (plus
        the two-up rule gap, ``TWO_UP_RULE_GAP_MM``) on a pair, where a single
        page's drawing now floats below that row.

        The equality this test asserted until CARD-224 (``upper.top ==
        alone.top``, AC-252's own claim) is false by that card's design: the
        single page floats at 42% of its puzzle area's spare, the slot does
        not. Both rows are still measured, and their *inequality* is asserted
        — so a build that moved either one onto the other fails here.

        **AC-252 is retired** (2026-10-17/18, with AC-190). **AC-378** states
        the two rows differ and is pinned at the PDF level by
        ``tests/test_book_pdf_two_up.py::TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow``
        (a positive test, not an ``xfail``); **AC-379** — a two-up page's two
        slots sharing the page's own puzzle area — is owed to CARD-226 and is
        out of this card's scope. Nothing is owed at the architect station.
        """
        upper, lower = drawings_of(pages[TWO_UP_PAGE - 1])
        alone = drawing_of(pages[SINGLE_PAGE - 1])

        # The row is the band's foot plus the two-up rule gap since the slots
        # stopped sitting flush against the rules above them.
        gap_mm = _two_up_rule_gap_mm(UPPER_PUZZLE, LOWER_PUZZLE)
        assert abs(upper.top / PX_PER_MM - (TOP_MM + BAND_MM + gap_mm)) <= 0.5
        assert alone.top > upper.top, "the single page's drawing floats below it"
        assert lower.top > upper.top, "the lower slot is a second drawing below it"

    def test_both_slots_sit_where_con_018s_millimetres_put_them(self, pages) -> None:
        """Origin and extent, against the arithmetic — not against the layout.

        **The origin is a boundary, so CARD-336 reads it as one.** ``left``
        and ``top`` below are the millimetres CON-018 puts the slot's own box
        at; ``Drawing.left``/``.top`` are the frame rule's *leading inked
        line*, which sits outside that box by half a rule and — measured —
        by a different amount in each medium: 0 px where Pillow butt-caps
        four lines, 2.5 px where a PDF rasteriser strokes one mitred ``re``.
        Against this page's own arithmetic that reads as 0.4961 px in raster
        and **2.5039 px in vector**, past the 1.5 px
        :data:`EDGE_TOLERANCE_PX` — a renderer that moved nothing.
        :func:`~tests.helpers.page_ink.frame_centre_of` reports the rule's
        centre instead, read off the rule's own measured width, and the same
        page then reads **0.0039 px in vector and 0.9961 px in raster** —
        inside the bound in both media, where the ink reading is inside it in
        only one. No tolerance moved (G-1).
        """
        page = pages[TWO_UP_PAGE - 1]
        drawings = drawings_of(page)
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for drawing, puzzle, (left, top, right, bottom) in zip(
            drawings, (UPPER_PUZZLE, LOWER_PUZZLE), boxes
        ):
            centre = frame_centre_of(page, drawing)
            assert abs(centre.frame_left - left) <= EDGE_TOLERANCE_PX
            assert abs(centre.frame_top - top) <= EDGE_TOLERANCE_PX
            # ``grid_left``/``grid_right`` are their rule group's first pixel and
            # both rules are heavy, so the half stroke cancels in the difference:
            # the grid's own *extent* is compared, and it is the drawing's box
            # less the two clue gutters — unmoved by the frame around it.
            assert abs(
                (drawing.grid_right - drawing.grid_left)
                - (right - left - puzzle["row_depth"] * drawing.cell)
            ) <= EDGE_TOLERANCE_PX
            assert abs(
                (drawing.grid_bottom - drawing.grid_top)
                - (bottom - top - puzzle["column_depth"] * drawing.cell)
            ) <= EDGE_TOLERANCE_PX

    def test_the_stroked_slot_is_the_unframed_one_plus_the_frames_own_ink(self) -> None:
        """``_stroke_drawing`` only ever *adds*: no pixel it inked is now white.

        The function this card changed, driven directly, with the frame present
        and with it dropped — which is the one comparison that can be made at
        all, because the panel's own sheet is always a framed one (a placed page
        is framed, ADR-0036/R2) and there is no unframed two-up page to render.
        """
        pair = compute_pair_layout(
            _clue_sets(**UPPER_PUZZLE), _clue_sets(**LOWER_PUZZLE), _spec()
        )
        assert pair is not None

        for slot in (pair.upper, pair.lower):
            assert slot.frame is not None, "COMP-007 measured a frame for this slot"
            framed = _stroked(slot)
            plain = _stroked(replace(slot, frame=None))

            assert not (plain & ~framed).any(), "stroking the frame erased grid ink"
            assert (framed & ~plain).any(), "the frame put no ink on the page at all"
            # And what it added is only the two sides a frame adds — the left
            # and top edges of the drawing — never anything inside the grid.
            added = np.argwhere(framed & ~plain)
            assert added[:, 0].min() < slot.frame.top + slot.thick_rule
            assert added[:, 1].min() < slot.frame.left + slot.thick_rule

    def test_the_page_size_is_the_books_own_trim(self, pages) -> None:
        """G-3's outermost figure: the frame moved no page geometry at all."""
        for page in pages:
            assert page.size == (
                round(BOOK1_WIDTH_MM * PX_PER_MM),
                round(BOOK1_HEIGHT_MM * PX_PER_MM),
            )


def _stroked(slot) -> np.ndarray:
    """``_stroke_drawing``'s ink for one slot, on a page of the slot's own size."""
    image = Image.new("RGB", (slot.width, slot.height), BACKGROUND)
    _stroke_drawing(ImageDraw.Draw(image), slot)
    return _dark(image)


# --------------------------------------------------------------------------
# Property: every pair the walk can make prints as two framed puzzles
# --------------------------------------------------------------------------

#: How many pairs the corpus below must hold. Stated as a constant *and* as a
#: literal in the assertion, so the floor can fail: a corpus that shrank to
#: half its size fails on the constant, and a constant quietly lowered to match
#: a shrunken corpus fails on the literal (the idiom
#: ``tests/test_books_list_plan_stats.py`` uses).
TWO_UP_CORPUS_PAIRS = 24


def test_PropertyTest_TwoUpFrame_EveryPrintedPairIsTwoFramedPuzzles() -> None:
    """Over a seeded corpus of pairs, trims and parities (no ``hypothesis``).

    Each case is stroked through the function this card changed and then
    measured off the ink, so what is asserted is what a printer would see:

    * both slots read back as **framed** drawings;
    * each reads back its own grid and its own clue gutters from behind the
      frame, so the frame is a whole gutter out from the grid's border and not
      a re-stroke of it;
    * the frame's weight is the heavy rule and no third weight appears.

    Only pairs ``compute_pair_layout`` accepts are counted — FR-040 declines a
    pair that would print under 7.0 mm — and the count is floored so the corpus
    cannot silently stop exercising the page kind this card exists for.
    """
    rng = random.Random(146)
    trims = ((BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM), SIX_BY_NINE_MM)
    pairs = 0
    for width_mm, height_mm in trims:
        for parity in PageParity:
            for _ in range(16):
                columns = rng.randint(10, 14)
                rows = rng.randint(10, 14)
                row_depth = rng.randint(1, (columns + 1) // 2)
                column_depth = rng.randint(1, (rows + 1) // 2)
                spec = _spec(width_mm=width_mm, height_mm=height_mm, parity=parity)
                same = _clue_sets(columns, rows, row_depth, column_depth)
                found = compute_pair_layout(same, same, spec)
                if found is None:
                    continue

                page = Image.new(
                    "RGB", (found.upper.width, found.upper.height), BACKGROUND
                )
                draw = ImageDraw.Draw(page)
                for slot in (found.upper, found.lower):
                    _stroke_drawing(draw, slot)

                drawings = drawings_of(page)
                assert len(drawings) == 2, (
                    f"{columns}x{rows} twice on {width_mm:g}x{height_mm:g} {parity} "
                    f"reads as {len(drawings)} drawings"
                )
                for drawing, slot in zip(drawings, (found.upper, found.lower)):
                    assert drawing.framed is True, (
                        f"{columns}x{rows} on {width_mm:g}x{height_mm:g} {parity}: "
                        "a slot printed without its frame"
                    )
                    assert (drawing.columns, drawing.rows) == (columns, rows)
                    assert (
                        _gutter_cells(drawing.left, drawing.grid_left, drawing.cell)
                        == row_depth
                    )
                    assert (
                        _gutter_cells(drawing.top, drawing.grid_top, drawing.cell)
                        == column_depth
                    )
                    assert slot.frame.width == slot.thick_rule == 2 * slot.thin_rule
                pairs += 1

    assert pairs >= TWO_UP_CORPUS_PAIRS >= 24, f"the corpus shrank to {pairs} pairs"


# --------------------------------------------------------------------------
# Property: every trim, every parity, every gutter — the frame is the drawing
# --------------------------------------------------------------------------


def test_PropertyTest_PuzzleFrame_IsTheDrawingsBoxOnEveryTrimAndParity() -> None:
    """Over a seeded corpus of trims, parities and gutters (no ``hypothesis``).

    Three standing properties, on every case:

    * the frame is exactly the drawing's box — the two clue gutters' outer
      edges and the grid's own far border, so it can move nothing;
    * dropping it leaves a layout identical to the one the same sheet produces
      with ``frame=False``, field for field;
    * its weight is the heavy rule, twice the thin one, and no third weight
      appears on the page (ADR-0037/R2).

    The expected box is :func:`_expected_box`'s millimetre arithmetic, not
    ``compute_layout``'s own.
    """
    rng = random.Random(144)
    trims = (
        (BOOK1_WIDTH_MM, BOOK1_HEIGHT_MM),
        SIX_BY_NINE_MM,
        (7 * 25.4, 10 * 25.4),
    )
    cases = skipped = 0
    for width_mm, height_mm in trims:
        for parity in PageParity:
            for _ in range(40):
                columns = rng.randint(10, 30)
                rows = rng.randint(10, 30)
                row_depth = rng.randint(1, (columns + 1) // 2)
                column_depth = rng.randint(1, (rows + 1) // 2)
                spec = _spec(width_mm=width_mm, height_mm=height_mm, parity=parity)
                # The boundary window is the clearance test's subject, not this
                # property's: :func:`_expected_top_mm` does not model the
                # threshold (see its docstring), so a drawing whose spare is
                # positive but under CLEARANCE_WINDOW_MM is left to
                # ``test_the_clearance_threshold_is_the_gap_above_and_not_half_the_spare``.
                # Measured (CARD-392): 2 of this corpus's 240 drawings are in
                # the window with the one-line footer, 1 was with the old band.
                area_top_mm, area_bottom_mm = _puzzle_area_mm(spec)
                drawing_mm = (column_depth + rows) * _expected_cell_mm(
                    spec, row_depth + columns, column_depth + rows
                )
                if 0 < (area_bottom_mm - area_top_mm) - drawing_mm < CLEARANCE_WINDOW_MM:
                    skipped += 1
                    continue
                row_clues, column_clues = _clue_sets(columns, rows, row_depth, column_depth)

                layout = compute_layout(row_clues, column_clues, spec)
                plain = compute_layout(row_clues, column_clues, replace(spec, frame=False))
                frame = layout.frame

                assert frame is not None
                expected = _expected_box(spec, columns, rows, row_depth, column_depth)
                measured = (frame.left, frame.top, frame.right, frame.bottom)
                assert all(
                    abs(was - is_) <= EDGE_TOLERANCE_PX
                    for was, is_ in zip(expected, measured, strict=True)
                ), (
                    f"{columns}x{rows} ({row_depth}/{column_depth} deep) on "
                    f"{width_mm:g}x{height_mm:g} {parity}: frame {measured}, "
                    f"drawing {expected}"
                )
                assert replace(layout, frame=None) == plain
                assert frame.width == layout.thick_rule == 2 * layout.thin_rule
                assert {line.width for line in layout.grid_lines} | {frame.width} == {
                    layout.thin_rule,
                    layout.thick_rule,
                }
                cases += 1

    assert cases >= 200, f"the corpus cannot silently shrink: {cases} cases"
    assert skipped <= 5, f"the boundary window is a rare exemption, not a hole: {skipped}"


def test_the_frame_is_a_field_of_the_layout_and_not_a_line_of_the_grid() -> None:
    """``vertical_lines``/``horizontal_lines`` stay the grid's own boundaries.

    ``pdf._reveal`` reads a cell's extent off consecutive entries of those two
    tuples, so a gutter-edge rule folded in among them would put every filled
    cell of every answer page one column out. The frame is carried beside them
    instead, and this says so where a later reader will meet it.
    """
    spec = _spec()
    columns, rows, row_depth, column_depth = 20, 20, 4, 5
    layout = compute_layout(*_clue_sets(columns, rows, row_depth, column_depth), spec)

    assert len(layout.vertical_lines) == columns + 1
    assert len(layout.horizontal_lines) == rows + 1
    assert layout.frame.left < layout.vertical_lines[0].position
    assert layout.frame.top < layout.horizontal_lines[0].position
    assert "frame" in {field.name for field in dataclasses.fields(layout)}


def _gutter_cells(edge: int, border: int, cell: float) -> int:
    """How many whole cells of clue gutter stand between ``edge`` and ``border``.

    ``edge`` is the drawing's outer edge as ``page_ink`` reads it — where the
    rules of the *other* axis start, which is half a heavy stroke inside the
    rule group's own first pixel that ``border`` reports. Rounding to whole
    cells is what makes the two comparable: a gutter is a whole number of
    cells deep by construction, and half a rule is not a fraction of one.
    """
    return round(abs(border - edge) / cell)


def test_the_frame_never_reaches_an_answer_tile() -> None:
    """FR-042's packed answer key is out of scope and carries no frame **on paper**.

    Read off the rendered key, not off the layout object. The structural
    reading — ``AnswerTile`` has no ``frame`` field — is true of every tree
    this card could have produced, under every mutation of the frame code, so
    on its own it proves nothing. What the card claims is that a *printed*
    answer page carries no rectangle around its tiles, and the only way to say
    that is to render one and measure it.

    Measured with the project's own ink measurer, against a framed puzzle page
    on the **same sheet** as a positive control, so the test fails from either
    side: a frame that leaked onto the key reads ``framed=True`` there, and a
    measurer that cannot see a frame at all reads ``framed=False`` on the
    puzzle page. The first is how CARD-144's first cycle shipped — the
    measurer asked only "does the leftmost rule sit on the drawing's own
    edge?", which an answer tile satisfies trivially because it carries no
    clue gutter, so the key's pages reported a frame they do not have and read
    one column and one row short of their true extent, with every test green.
    Both halves are asserted here.
    """
    from nonogram.export.layout import compute_answer_page_layout
    from nonogram.export.png import render_answer_page

    from tests.helpers.page_ink import drawing_of

    spec = _spec()
    columns, rows, row_depth, column_depth = 16, 12, 4, 3

    # One answer on the page, so the rules the measurer counts are that one
    # tile's grid and nothing else. ``_grid`` fills only row 0 and column 0 and
    # never the last cell of either, so the grid's outer ring stays blank and
    # no revealed run is ever as long as the rule beside it — which is what
    # makes counting rules safe on this particular answer page.
    key = render_answer_page(
        [(_grid(columns, rows, row_depth, column_depth), "1")], 4, spec
    )
    on_the_key = drawing_of(key)

    assert on_the_key.framed is False, "the frame reached FR-042's answer key"
    assert (on_the_key.columns, on_the_key.rows) == (columns, rows), (
        "the answer tile's grid does not read back its own extent"
    )
    # A tile has no clue gutter and no rule outside its grid's border, so the
    # drawing's own left and top edges ARE that border, to within the half of
    # its stroke that falls outside it: **zero** cells stand between them,
    # where a framed drawing always has the clues' own depth.
    assert _gutter_cells(on_the_key.left, on_the_key.grid_left, on_the_key.cell) == 0
    assert _gutter_cells(on_the_key.top, on_the_key.grid_top, on_the_key.cell) == 0

    # The positive control on the same sheet: a puzzle page of this book IS
    # framed, and reads its own extent from behind the frame.
    puzzle = render_image(
        _payload(columns, rows, row_depth, column_depth), page_spec=spec
    )
    on_the_puzzle = drawing_of(puzzle)

    assert on_the_puzzle.framed is True, "the measurer cannot see the frame it looks for"
    assert (on_the_puzzle.columns, on_the_puzzle.rows) == (columns, rows)
    # There the gutters are real: as many whole cells deep as the clues run.
    assert (
        _gutter_cells(on_the_puzzle.left, on_the_puzzle.grid_left, on_the_puzzle.cell)
        == row_depth
    )
    assert (
        _gutter_cells(on_the_puzzle.top, on_the_puzzle.grid_top, on_the_puzzle.cell)
        == column_depth
    )

    # The cheap structural companion, kept: no tile carries a frame field either.
    page = compute_answer_page_layout([(10, 10)] * 4, 4, spec)
    for tile in page.tiles:
        assert not hasattr(tile, "frame")


def test_the_book_spec_is_the_sheet_these_tests_state_by_hand() -> None:
    """CON-018's profile written out here is the sheet the panel builds (AC-178).

    Compared field by field and to within a float's last bit, not for exact
    equality: the panel converts CON-018's inches through :class:`Decimal` and
    lands on 215.9 mm where ``8.5 * 25.4`` lands on 215.89999999999998. That
    is the two statements agreeing, which is the point of stating it twice.
    """
    mine, panels = _spec(), book_page_spec(None, 1)

    assert mine.cell_cap == panels.cell_cap
    assert mine.cell_cap is not CellCapPolicy.COMFORT_CURVE
    from nonogram.admin import book_page_spec as panel

    for field in dataclasses.fields(PageSpec):
        ours, theirs = getattr(mine, field.name), getattr(panels, field.name)
        if field.name == "frame":
            # The one field the panel now states (owner, 2026-11-09): the
            # book's frame switch, which this module turns back on.
            assert theirs is panel.BOOK_PUZZLE_FRAME, field.name
            continue
        if isinstance(ours, float) and isinstance(theirs, float):
            assert ours == pytest.approx(theirs), field.name
        else:
            assert ours == theirs, field.name


# --------------------------------------------------------------------------
# "A placed page is framed" is only safe while "placed" and "book" name the
# same pages — so that equivalence is walked on disk, not asserted in prose
# --------------------------------------------------------------------------

#: The package on disk, walked the way ``tests/test_cli.py``'s import guard
#: walks it, so a module a later card adds is covered from the moment it lands.
_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "nonogram"

#: The one module allowed to build a page spec that carries a parity.
_THE_PLACED_PAGE_PRODUCER = "nonogram.admin.book_page_spec"


def _module_name(path: Path) -> str:
    parts = path.relative_to(_PACKAGE_DIR).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(("nonogram", *parts))


def _is_page_spec_call(node: ast.Call) -> bool:
    """A call that can hand back a placed :class:`PageSpec`.

    Two shapes, because a spec is born two ways in this codebase:

    * ``PageSpec(...)`` or ``layout.PageSpec(...)``, however it was imported;
    * ``replace(...)`` or ``dataclasses.replace(...)`` — the idiom
      ``layout.py`` itself already uses on this very type, and the one a
      second producer is most likely to reach for, since it starts from a
      spec that already exists.

    ``replace`` is matched by name alone, without checking what is being
    replaced: the walk cannot know a local's type, and a guard that only
    fires on calls it can prove are ``PageSpec`` is a guard that misses the
    interesting case. A ``replace`` of something else carrying ``parity=``
    would be a false positive, and a loud one is the right failure here —
    the same reason ``_carries_a_parity`` treats ``**kwargs`` as placed.
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr in {"PageSpec", "replace"}
    return isinstance(func, ast.Name) and func.id in {"PageSpec", "replace"}


def _carries_a_parity(node: ast.Call) -> bool:
    """Whether this call can produce a spec whose ``parity`` is not ``None``.

    A ``parity=`` keyword written as the literal ``None`` is the unplaced case
    and does not count; anything else does, **including ``**kwargs``**, whose
    contents this walk cannot see. Unknown is treated as placed on purpose: the
    guard's job is to make a second producer impossible to add quietly, and an
    unreadable call is exactly the shape that would.
    """
    for keyword in node.keywords:
        if keyword.arg is None:
            return True
        if keyword.arg == "parity":
            value = keyword.value
            return not (isinstance(value, ast.Constant) and value.value is None)
    return False


def _placed_page_producers() -> tuple[dict[str, list[int]], int]:
    """``({module: [line, ...]}, how many PageSpec calls were seen at all)``."""
    producers: dict[str, list[int]] = {}
    seen = 0
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        with warnings.catch_warnings():
            # ``sourcing/templates/dog_in_house.py`` carries a stray escape in
            # a docstring and warns on every parse. It is not this guard's
            # business, and letting it through would put the same line in the
            # suite's output on every run.
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_page_spec_call(node)):
                continue
            seen += 1
            if _carries_a_parity(node):
                producers.setdefault(_module_name(path), []).append(node.lineno)
    return producers, seen


def test_the_book_is_the_only_thing_in_src_that_places_a_page() -> None:
    """``PageSpec.framed`` reads "a placed page is framed" — pin what "placed" means.

    ``PageSpec.framed`` returns ``self.parity is not None`` when ``frame`` is
    left at its default, so the *stated* rule is about parity. The rule the
    owner gave is about the **book** ("BOOK PAGES ONLY", intake at
    ``meta/architecture/inputs/raw-requirements.md:265``), and the two agree
    only because nothing but the book lays a puzzle on a trim. That is a fact
    about today's source tree, not a property of ``PageSpec`` — and until this
    test it lived in a docstring, so the first non-book placed page (a
    single-sheet trim preview, a poster export, a marketing render) would have
    acquired a frame in silence and CON-019's reasoning would have quietly
    stopped holding.

    Walked on disk with ``ast`` rather than by import, in the spirit of
    ``tests/test_cli.py``'s import guard, so a module a later card adds is
    covered the moment it lands. The day a second producer appears this fails,
    and the reading to take from it is *not* "add the module to the allowlist"
    — it is that ``framed`` must then say what it means and be given an
    explicit ``frame=``, which the field already supports.
    """
    producers, seen = _placed_page_producers()

    assert seen >= 2, (
        f"the walk saw {seen} PageSpec constructions in {_PACKAGE_DIR} — it is "
        "empty or misrooted, and would pass whatever the source said"
    )
    assert set(producers) == {_THE_PLACED_PAGE_PRODUCER}, (
        "a second module now builds a page spec with a parity, so "
        "'a placed page is framed' no longer means 'a book page is framed': "
        f"{producers}"
    )


def test_the_placed_page_walk_reads_a_parity_where_there_is_one() -> None:
    """Guard the guard: the two shapes it must tell apart, told apart.

    ``DEFAULT_PAGE_SPEC`` writes ``parity=None`` and the panel's spec passes a
    variable, and those are the two readings the whole guard turns on. Asserted
    against parsed source rather than against the real files, so this stays true
    when the real ones are reformatted.
    """
    unplaced, placed, splatted, silent = (
        ast.parse(source).body[0].value
        for source in (
            "PageSpec(width_mm=1, parity=None)",
            "PageSpec(width_mm=1, parity=parity)",
            "PageSpec(**fields)",
            "PageSpec(width_mm=1)",
        )
    )

    assert not _carries_a_parity(unplaced)
    assert not _carries_a_parity(silent)
    assert _carries_a_parity(placed)
    assert _carries_a_parity(splatted), "an unreadable call must count as placed"
    assert _is_page_spec_call(placed)
    assert _is_page_spec_call(ast.parse("layout.PageSpec(parity=p)").body[0].value)
    assert not _is_page_spec_call(ast.parse("Layout(parity=p)").body[0].value)


# ==========================================================================
# CARD-224 — the grid goes back to centred, at 42% of the puzzle area's spare
# ==========================================================================
#
#     AC-1  TestBookPuzzleFrame_GridIsCentredOnBothParities
#     AC-2  TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare  (AC-366/AC-367)
#     AC-3  TestBookPuzzleFrame_GridClearsBothRules                  (EC-022)
#     AC-4  TestBookPuzzleFrame_TallestGridYieldsToTheFooter
#     AC-6  TestBookPuzzleFrame_NoEmptyLowerThird
#
# AC-378 (added 2026-10-18 with AC-252's and AC-190's retirement) is the
# *negative* of the retired claim — the upper slot's drawing does NOT start on
# the single page's row — and this module states its ink half in
# ``TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame``
# ``::test_the_upper_slot_still_starts_on_the_bands_own_foot``, above. AC-379
# (each slot floating in its own slot's spare) is owed to CARD-226 by this
# card's G-4 and is not tested here.
#
# AC-5 is the existing caption-slot classes in ``tests/test_book_solved_page.py``
# and ``tests/test_layout_page_spec.py``, which this card leaves in force (G-3)
# and which it had to re-aim: centring restores the horizontal spare CARD-204's
# flush anchor had spent, so the caption width at which the clamp fires moved,
# and those files now carry a title in each of the three regimes rather than
# one that has quietly stopped reaching the margin.
#
# **Where the numbers come from.** The puzzle area is restated here in
# millimetres from CARD-222's own two figures (:data:`HEADER_RULE_LIFT_SHARE`,
# :data:`FOOTER_STRIP_MM`) and the split from :data:`SPARE_ABOVE` — never read
# back from ``interior_frame``, so a drawing in the right place is two
# independent answers agreeing. What the page *did* is read off its ink.
#
# **The controls.** Every claim below is paired with the same check applied to
# the **pre-CARD-224 geometry** — the flush-by-parity anchor and the fixed top
# edge, each computed here in millimetres — which must fail it (ADR-0039/R1: a
# coverage claim needs a control that can fail). That is the strongest control
# available: it is exactly the placement this card replaces, so a test that
# passed under both would be measuring nothing.


def _area_ink_box(page: Image.Image, spec: PageSpec) -> tuple[int, int, int, int]:
    """``(left, top, right, bottom)`` of every dark pixel **inside the puzzle
    area**, in device pixels.

    The drawing is the only thing a :func:`render_image` page puts there (the
    payload names no picture and no tier, so the band is blank; the frame's two
    rules are the *generator's* ink and are not on this page at all), so these
    four numbers are the drawing's own outermost ink — stroke overhang
    included, on all four sides alike, which is what "measured off the drawn
    ink" has to mean and is one step closer to the paper than any boundary the
    layout reports.

    **Why the area and not the page.** A placed page carries more ink than its
    drawing: since CARD-223 the footer's outer corner holds a 2 cm QR
    placeholder whose box reaches the usable area's own edges — precisely the
    fragility ``page_ink``'s own docstring records. It sits *below* the footer
    rule, so cropping to the puzzle area removes it without needing to know
    where it is.

    **Why not** :func:`~tests.helpers.page_ink.drawing_of`: its ``left``/
    ``top`` are a rule's first ink row and its ``grid_right``/``grid_bottom``
    the *same* edge of the far rule, which is deliberate there (it makes the
    printed cell a rule-to-rule pitch) and asymmetric here — it would
    understate the ink by half a heavy rule at two of the four sides, which on
    a 22 mm spare is 2% of the ratio AC-2 and AC-6 state to 0.5%.
    """
    area_top, area_bottom = _puzzle_area_mm(spec)
    top_px, bottom_px = round(area_top * PX_PER_MM), round(area_bottom * PX_PER_MM)
    dark = _dark(page)[top_px : bottom_px + 1]
    rows = np.flatnonzero(dark.any(axis=1))
    columns = np.flatnonzero(dark.any(axis=0))
    assert rows.size and columns.size, "the puzzle area carries no ink at all"
    return (
        int(columns.min()),
        top_px + int(rows.min()),
        int(columns.max()),
        top_px + int(rows.max()),
    )


def _flush_left_mm(spec: PageSpec, drawing_columns: int, cell_mm: float) -> float:
    """CARD-204's anchor, in millimetres: the control AC-1 needs.

    Flush with the usable area's *outer* margin, mirrored by parity — the
    placement this card reverses. Written out here, not read from any
    surviving code, because none survives.
    """
    left_margin = spec.outside_mm if spec.parity is PageParity.EVEN else spec.gutter_mm
    spare = (spec.width_mm - spec.gutter_mm - spec.outside_mm) - drawing_columns * cell_mm
    return left_margin if spec.parity is PageParity.EVEN else left_margin + spare


def _fixed_top_mm(spec: PageSpec) -> float:
    """FR-032's retired fixed top edge (AC-190), in millimetres: the control
    AC-2, AC-4 and AC-6 need. The band's foot, on every page and parity."""
    return spec.top_mm + spec.band_mm


class TestBookPuzzleFrame_GridIsCentredOnBothParities:
    """AC-1 — the same puzzle on a left-hand and a right-hand page: equal side
    margins within the puzzle area, and parity no longer moves the drawing.

    **Stated on two books on purpose.** On Book 1 as amended 2026-10-17 the
    gutter and the outside margin are both 12.700 mm, so the two pages place
    the drawing at the *same absolute x* and "parity no longer moves it" is
    literally measurable there. But that equality also makes any parity claim
    on that profile an identity (the carried note on this card's system
    contract, and the registry's own note on EC-032), so the second half of
    the claim — that what parity still moves is the *usable area*, and the
    drawing simply sits in the middle of whatever that is — is stated on
    CARD-223's ``_unequal_spec``, whose two margins differ by 12 mm. That
    helper is imported rather than reimplemented: it exists for exactly this.
    """

    CASE = dict(columns=20, rows=20, row_depth=4, column_depth=5)

    def _pages(self, spec_of) -> dict:
        return {
            parity: render_image(_payload(**self.CASE), page_spec=spec_of(parity))
            for parity in (PageParity.ODD, PageParity.EVEN)
        }

    def test_the_two_side_margins_are_equal_on_both_parities(self) -> None:
        """Measured off the ink, inside the puzzle area's own usable width."""
        for name, spec_of in (
            ("book 1", lambda parity: _spec(parity=parity)),
            ("unequal margins", _unequal_spec),
        ):
            for parity, page in self._pages(spec_of).items():
                spec = spec_of(parity)
                left, _, right, _ = _area_ink_box(page, spec)
                usable_left = (
                    spec.outside_mm if parity is PageParity.EVEN else spec.gutter_mm
                ) * PX_PER_MM
                usable_right = (
                    spec.width_mm
                    - (spec.gutter_mm if parity is PageParity.EVEN else spec.outside_mm)
                ) * PX_PER_MM
                gaps = (left - usable_left, usable_right - right)
                assert abs(gaps[0] - gaps[1]) <= 2 * EDGE_TOLERANCE_PX, (
                    name, parity, gaps
                )

    def test_book_1_places_it_on_the_same_pixel_at_both_parities(self) -> None:
        """Parity no longer moves it: on equal margins, the same x and the
        same y, to the pixel."""
        pages = self._pages(lambda parity: _spec(parity=parity))
        odd, even = (
            _area_ink_box(pages[parity], _spec(parity=parity))
            for parity in (PageParity.ODD, PageParity.EVEN)
        )

        assert odd == even, (odd, even)

    def test_on_unequal_margins_the_area_moves_and_the_alignment_does_not(self) -> None:
        """What parity still does: it moves the usable area by gutter − outside,
        and the drawing goes with it while staying centred in it (EC-032)."""
        pages = self._pages(_unequal_spec)
        odd, even = (
            _area_ink_box(pages[parity], _unequal_spec(parity))
            for parity in (PageParity.ODD, PageParity.EVEN)
        )
        expected_shift = (UNEQUAL_GUTTER_MM - UNEQUAL_OUTSIDE_MM) * PX_PER_MM

        assert abs(expected_shift) > 100, "this sheet must really move the area"
        assert abs((odd[0] - even[0]) - expected_shift) <= 2 * EDGE_TOLERANCE_PX
        assert odd[1] == even[1], "parity never moves it vertically (AC-276)"

    def test_the_control_card_204s_anchor_fails_both_claims(self) -> None:
        """The control that can fail (ADR-0039/R1): the placement this card
        reverses, computed in millimetres, is not centred and *is* moved by
        parity — on Book 1's own equal margins, where the two assertions above
        would otherwise be the weakest."""
        drawing_columns = self.CASE["row_depth"] + self.CASE["columns"]
        drawing_rows = self.CASE["column_depth"] + self.CASE["rows"]
        flush = {}
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            cell = _expected_cell_mm(spec, drawing_columns, drawing_rows)
            flush[parity] = _flush_left_mm(spec, drawing_columns, cell)
            usable_left = spec.outside_mm if parity is PageParity.EVEN else spec.gutter_mm
            usable_right = spec.width_mm - (
                spec.gutter_mm if parity is PageParity.EVEN else spec.outside_mm
            )
            gaps = (
                flush[parity] - usable_left,
                usable_right - (flush[parity] + drawing_columns * cell),
            )
            # The very assertion the first test makes, on the old anchor.
            assert abs(gaps[0] - gaps[1]) > 2 * EDGE_TOLERANCE_PX / PX_PER_MM, (
                parity, gaps, "CARD-204's anchor would pass a centring check"
            )
        assert flush[PageParity.ODD] != flush[PageParity.EVEN], (
            "CARD-204's anchor moved the drawing by parity even on equal margins"
        )


class TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare:
    """AC-2, and the registry's AC-366/AC-367 — the gap above the drawing is
    0.42 of the puzzle area's spare height and the gap below it 0.58, measured
    off the drawn ink.

    42% is the owner's optical figure, not an arithmetic one ("which looks
    centred once the header sits above it", artifact of 2026-10-14), and it is
    declared once in the code as
    :data:`~nonogram.export.layout.GRID_SPARE_ABOVE` with that sentence as its
    docstring. This class reads the ratio back off two real pages rather than
    importing it, so a build that "improved" it to 0.5 fails here.
    """

    #: AC-367's own two puzzles: a 15x15 whose 22-cell drawing prints at the
    #: 7.5 mm cap (165.0 mm deep) and a 30x30 whose 39-cell drawing is page-fit
    #: bound (190.5 mm deep, 4.885 mm a cell).
    SHALLOW = dict(columns=15, rows=15, row_depth=7, column_depth=7)
    DEEP = dict(columns=30, rows=30, row_depth=9, column_depth=9)

    @staticmethod
    def _bands(case: dict, spec: PageSpec) -> tuple[float, float]:
        """``(above, below)`` in millimetres, off the ink of a rendered page."""
        page = render_image(_payload(**case), page_spec=spec)
        _, top, _, bottom = _area_ink_box(page, spec)
        area_top, area_bottom = _puzzle_area_mm(spec)
        return (top / PX_PER_MM - area_top, area_bottom - bottom / PX_PER_MM)

    @pytest.mark.parametrize("parity", [PageParity.ODD, PageParity.EVEN])
    @pytest.mark.parametrize("case", ["SHALLOW", "DEEP"])
    def test_the_spare_is_split_42_to_58(self, case: str, parity: PageParity) -> None:
        spec = _spec(parity=parity)
        above, below = self._bands(getattr(self, case), spec)
        spare = above + below

        assert spare > 20.0, (case, spare, "this page must have real spare")
        assert above / spare == pytest.approx(SPARE_ABOVE, abs=0.005), (case, above, below)
        assert below / spare == pytest.approx(1 - SPARE_ABOVE, abs=0.005)

    def test_ac_367s_own_figure_the_shallow_drawing_sits_10_71_mm_lower(self) -> None:
        """The two pages' top edges, 0.42 x 25.5 mm apart (AC-367)."""
        spec = _spec()
        shallow_above, _ = self._bands(self.SHALLOW, spec)
        deep_above, _ = self._bands(self.DEEP, spec)

        assert shallow_above - deep_above == pytest.approx(10.71, abs=0.1)

    def test_ac_366s_own_figure_a_60_mm_spare_splits_25_2_to_34_8(self) -> None:
        """AC-366 states the split on a 60 mm spare. No stored trim gives a
        60.0 mm spare exactly, so the trim is *made* to: the page is lengthened
        until the 15x15's spare is 60 mm, which is a sheet CON-018 would admit
        (a taller trim at Book 1's own margins) and keeps the figure the
        registry states rather than quoting a different one.
        """
        drawing_rows = self.SHALLOW["column_depth"] + self.SHALLOW["rows"]
        depth_mm = drawing_rows * STANDARD_CELL_MM
        # area height = spare + drawing, and area height is
        # trim − top − bottom − 7/8 band − footer strip.
        height_mm = (
            60.0
            + depth_mm
            + TOP_MM
            + BOTTOM_MM
            + BAND_MM * (1 - HEADER_RULE_LIFT_SHARE)
            + FOOTER_STRIP_MM
        )
        spec = _spec(height_mm=height_mm)

        above, below = self._bands(self.SHALLOW, spec)

        # 0.3 mm, not 0.2: the ink is read at the stroke's own outermost
        # pixel, so each band is a heavy rule's half (0.25 mm) shorter than
        # the boundary-to-boundary figure the registry states.
        assert above + below == pytest.approx(60.0, abs=0.6)
        assert above == pytest.approx(25.2, abs=0.3)
        assert below == pytest.approx(34.8, abs=0.3)

    def test_the_control_the_retired_fixed_top_edge_fails_this_ratio(self) -> None:
        """The control that can fail (ADR-0039/R1): AC-190's own placement —
        the band's foot, where every drawing sat until this card — puts about
        0.07 of the spare above the drawing on the deep page and 0.93 below it,
        not 0.42/0.58. The same arithmetic this class applies to the ink,
        applied to the geometry this card replaced."""
        spec = _spec()
        for case in (self.SHALLOW, self.DEEP):
            drawing_rows = case["column_depth"] + case["rows"]
            drawing_columns = case["row_depth"] + case["columns"]
            cell = _expected_cell_mm(spec, drawing_columns, drawing_rows)
            area_top, area_bottom = _puzzle_area_mm(spec)
            above = _fixed_top_mm(spec) - area_top
            below = area_bottom - (_fixed_top_mm(spec) + drawing_rows * cell)
            spare = above + below
            assert spare > 20.0, (case, spare)
            assert abs(above / spare - SPARE_ABOVE) > 0.1, (
                case, above, below, "the retired fixed top edge would pass AC-2"
            )


class TestBookPuzzleFrame_GridClearsBothRules:
    """AC-3 (and EC-022's own last clause) — no grid or clue ink touches the
    header rule or the footer rule.

    **What is actually swept, which is narrower than AC-3's own wording.** The
    card says "every grid size the book admits and every trim"; the sweep below
    covers **extents 10..30 in steps of 2 on both axes** at two clue-depth
    patterns on **five** sheets — 5 x 121 extents x 2 depths, 1,210 cases —
    and not the admissible space. The count is derived in the loop's own guard
    (``len(self.SHEETS) * 11 * 11 * 2``) rather than restated here, because
    cycle 2 caught this sentence quoting three different wrong figures for its
    own corpus. CON-011 admits 5..40, the odd extents are not swept, and no stored
    trim outside these four is. The gap is recorded here rather than closed:
    growing the corpus is cost this card cannot justify, and the one thing the
    unswept corner contains that the swept one does not is a *tighter* clearance
    margin — the worst case found by this card's review cycle 1 is a 39x35 at
    maximal clue depths, outside the range above. That corner is now covered by
    arithmetic instead of by enumeration:
    :meth:`test_the_clearance_threshold_is_the_gap_above_and_not_half_the_spare`
    pins the threshold that makes the conclusion hold for *every* extent,
    every trim and every rule weight, so the sweep is evidence over the stored
    sheets and the threshold test is the reason it generalises.

    **Two layers, because one of them cannot be afforded 1,210 times.** The
    sweep below is on the layout and on the rules' own rows computed here in
    millimetres: every extent from 10 to 30 on both axes, at two clue-depth
    patterns, on five sheets — the amended Book 1 at both parities, the 6 x 9
    in trim the owner also prints, KDP's smallest storable trim (10.00 cm),
    whose puzzle area is 33.7 mm deep and therefore cannot hold any drawing at
    all (AC-4's regime), and a **shallow-band** sheet (9 mm instead of 12 mm on
    a 160 mm trim), which is the one band depth at which the degraded
    placement's own safety stops being a gift of the band's lift — see
    :meth:`test_a_shallow_band_cannot_leave_ink_on_a_drawn_footer_rule`.
    The drawing's ink, not its boundary, is what clears: every rule in it is
    stroked centred on its boundary, so the box grows by half a heavy rule at
    each end. **The furniture rules' own spread is the one thing this sweep
    does not model** — :meth:`_clears` compares against the rules' *rows*, so
    it cannot see a violation within half a furniture rule of either. That
    blind spot is about 1 px wide and is covered by arithmetic instead:
    :meth:`test_the_clearance_threshold_is_the_gap_above_and_not_half_the_spare`
    asserts the ink against each rule's own outermost ink row, and the
    clearance the placement pays makes the ink-vs-ink margin at least 1 px
    (worst measured over this corpus: 3.984 px against the rows, 3 px against
    the ink).

    Then one real book's rendered pages are measured off their **ink**, with
    the frame's two rules really drawn on them, so the sweep's own model of
    where those rules are cannot be the only evidence.

    **The exception once declared here is retired.** A two-up page's *lower*
    slot used to have its drawing's bottom edge exactly on the footer rule
    (CARD-248 reserved one footer strip out of the pair's height, so that
    boundary and the hairline were the same row), and the ink test below
    asserted the coincidence so it would fail if it ever became a gap. It
    has: the lower drawing now ends ``TWO_UP_RULE_GAP_MM`` (capped at a quarter
    of the pair's slack) above the footer rule, so the ink test holds that
    slot to the same clearance as every other drawing and measures the gap.
    """

    SHEETS = {
        "book1 odd": _spec(parity=PageParity.ODD),
        "book1 even": _spec(parity=PageParity.EVEN),
        "six by nine": _spec(width_mm=SIX_BY_NINE_MM[0], height_mm=SIX_BY_NINE_MM[1]),
        "smallest trim": _spec(width_mm=100.0, height_mm=100.0),
        # The shallow band (review cycle 2, F2-001). Nothing else in the suite
        # varies ``band_mm`` on a footer-branch assertion, and the degraded
        # placement's safety used to depend on it: at 9 mm the band's lift is
        # 13.30 px against a 14.29 px clearance threshold, so the band's foot
        # no longer carries the drawing past the footer rule on its own. A
        # 30x12 at 6-deep gutters on this sheet is the case that reds both
        # footer-branch assertions below if the placement stops clamping.
        "shallow band": _spec(height_mm=160.0, band_mm=9.0),
    }

    @staticmethod
    def _depths(extent: int) -> tuple[int, ...]:
        """Two clue-depth patterns per extent: the shallowest a line can have
        and the deepest (alternating cells), so the gutter's own share of the
        drawing is swept and not fixed."""
        return (1, (extent + 1) // 2)

    @staticmethod
    def _clears(ink_top_mm: float, ink_bottom_mm: float, area: tuple[float, float]) -> bool:
        """Whether a drawing whose ink runs ``ink_top_mm..ink_bottom_mm``
        clears both of the puzzle area's **rule rows**.

        The one predicate the sweep and its control both use, so the control
        is a control *of this check* and not of a paraphrase of it.

        **The declared blind spot** (review cycle 2, F2-003). ``area`` holds
        the two rows the furniture rules are *centred on*, not the rows their
        ink reaches: the header rule is 3 px, so its ink reaches one row below
        ``area_top``, and a drawing whose ink sits on that pixel still passes
        ``area_top < ink_top_mm``. This predicate therefore cannot see a
        violation within about 1 px of either rule — which is precisely the
        0.555/0.659 px margins review cycle 1 found and this sweep did not.
        It is left as it is rather than tightened, because the margin is now
        guaranteed by arithmetic instead of by enumeration: the placement pays
        ``ceil(thick/2) + ceil(furniture/2) + 1`` at each end, which exceeds
        ``ceil(thick/2) + furniture // 2`` — the ink's actual need — by at
        least a pixel, and
        :meth:`test_the_clearance_threshold_is_the_gap_above_and_not_half_the_spare`
        pins that arithmetic against each rule's own outermost ink row.
        Measured over this sweep's corpus: worst ink-vs-row margin 3.984 px,
        worst ink-vs-ink margin 3.000 px.
        """
        area_top, area_bottom = area
        return area_top < ink_top_mm and ink_bottom_mm < area_bottom

    def test_every_extent_on_every_trim_clears_both_rules(self) -> None:
        checked = floated = held = 0
        for name, spec in self.SHEETS.items():
            area_top, area_bottom = _puzzle_area_mm(spec)
            for columns in range(10, 31, 2):
                for rows in range(10, 31, 2):
                    for depth in self._depths(min(columns, rows)):
                        layout = compute_layout(
                            *_clue_sets(columns, rows, depth, depth), spec
                        )
                        placement = layout.page
                        overhang = -(-layout.thick_rule // 2)
                        ink_top = (placement.drawing_top - overhang) / PX_PER_MM
                        ink_bottom = (placement.drawing_bottom + overhang) / PX_PER_MM
                        # The header rule is cleared in both regimes.
                        assert ink_top > area_top, (name, columns, rows, depth, ink_top)
                        if placement.vertical_bound == "ratio":
                            assert self._clears(
                                ink_top, ink_bottom, (area_top, area_bottom)
                            ), (name, columns, rows, depth, ink_top, ink_bottom)
                            floated += 1
                        else:
                            # AC-4's regime: the area cannot hold this drawing,
                            # the 42% rule yields, and the page's footer group
                            # is omitted by the renderer rather than crossed —
                            # which is what makes "no ink touches the footer
                            # rule" true: there is no footer rule on it.
                            assert placement.vertical_bound == "footer"
                            assert ink_bottom > area_bottom
                            assert _footer_group_omitted(layout, spec), (
                                "the footer group's own all-or-nothing "
                                "condition must refuse this page"
                            )
                            held += 1
                        checked += 1
        # Derived from the corpus, not restated: every sheet, every extent in
        # ``range(10, 31, 2)`` on both axes, both depth patterns.
        assert checked == len(self.SHEETS) * 11 * 11 * 2, checked
        # Neither regime may silently empty out of this sweep.
        assert floated >= 300, floated
        assert held >= 200, held

    #: CARD-222's two furniture rules in points, written out here as this
    #: file writes every other figure out, and the one rule the layout applies
    #: to a weight in points: the fewest whole device pixels that measure at
    #: least it. Neither is near a whole pixel (0.6 pt is 2.50 px, 0.4 pt is
    #: 1.67 px), so the rounding needs no tolerance here.
    HEADER_RULE_PT = 0.6
    FOOTER_RULE_PT = 0.4

    @staticmethod
    def _rule_px(points: float) -> int:
        """A rule weight in points as whole device pixels, rounded **up**."""
        return int(-(-(points * 25.4 / 72 * PX_PER_MM) // 1))

    @classmethod
    def _clearance_px(cls, thick_rule: int) -> int:
        """The clearance each of the two gaps has to pay, in device pixels.

        Half the drawing's own heavy rule (its ink is stroked centred on the
        boundary, so it overhangs by that much), plus half of the heavier
        furniture rule (which spreads about its own row the same way), plus
        the pixel that makes "clear" strict rather than "touching".

        Derived here from the three rule weights — the drawing's heavy rule as
        the layout committed it, the two furniture weights as points written
        out above — and **not** imported from the implementation, so a build
        that redefined its own clearance would not redefine this one.
        """
        furniture = max(cls._rule_px(cls.HEADER_RULE_PT), cls._rule_px(cls.FOOTER_RULE_PT))
        return -(-thick_rule // 2) + -(-furniture // 2) + 1

    #: The drawing the threshold test walks across the boundary: a 20x20
    #: behind 8-deep gutters, 28 cells each way, on Book 1's own width.
    STRADDLE = dict(columns=20, rows=20, row_depth=8, column_depth=8)
    #: The trim heights it is walked on. 0.05 mm a step is 0.6 px of trim, and
    #: the spare moves about 11.8 px per millimetre of height, so the scan
    #: brackets the one place the verdict changes to within a pixel of spare.
    #: The range is chosen to hold the boundary with both regimes either side
    #: of it, which the test asserts rather than assumes.
    STRADDLE_HEIGHTS_MM = tuple(round(237.0 + 0.05 * step, 3) for step in range(41))

    def test_the_clearance_threshold_is_the_gap_above_and_not_half_the_spare(self) -> None:
        """The boundary itself (CARD-224 review cycle 1, F-001).

        AC-3's conclusion is supposed to be arithmetic rather than a property
        of the trims stored today, and the arithmetic is a clearance term: the
        ratio is abandoned when the spare cannot pay the drawing's own
        half-heavy-rule clearance at **both** ends. Nothing pinned that term
        until this test, and the implementation's first form of it
        (``spare < 2 * clearance``) did not deliver what it claimed: the split
        is 42/58, so a spare that pays two clearances leaves only ``0.42 x 2 =
        0.84`` of one *above* the drawing. It survived on the stored profiles
        because the clearance is a pixel more generous than the ink needs.

        So the claim under test is **the gap, not the spare**: wherever the
        page reports ``"ratio"``, each of the two gaps is at least one whole
        clearance, and the drawing's outermost ink clears each rule's
        outermost ink. The trim height is walked in 0.05 mm steps across the
        one place the verdict changes, so both regimes are exercised and the
        case immediately below the boundary — which still has a **positive**
        spare, and is refused for the clearance's sake alone — is asserted
        too. That last assertion is what a ``spare <= 0`` oracle cannot make,
        and halving the threshold reds the loop below.
        """
        verdicts: list[tuple[float, str]] = []
        straddle: list[tuple[float, str, int, int]] = []
        for height_mm in self.STRADDLE_HEIGHTS_MM:
            spec = _spec(height_mm=height_mm)
            layout = compute_layout(*_clue_sets(**self.STRADDLE), spec)
            placement = layout.page
            area_top_mm, area_bottom_mm = _puzzle_area_mm(spec)
            area_top = round(area_top_mm * PX_PER_MM)
            area_bottom = round(area_bottom_mm * PX_PER_MM)
            spare = (area_bottom - area_top) - (placement.drawing_bottom - placement.drawing_top)
            gap_above = placement.drawing_top - area_top
            gap_below = area_bottom - placement.drawing_bottom
            clearance = self._clearance_px(layout.thick_rule)
            where = (height_mm, placement.vertical_bound, spare, gap_above)
            verdicts.append((height_mm, placement.vertical_bound))
            straddle.append(where)
            if placement.vertical_bound != "ratio":
                # The degraded regime: held at the band's foot, and the
                # renderer prints no footer group for the ink to cross.
                assert placement.drawing_top == placement.band_bottom, where
                assert _footer_group_omitted(layout, spec), where
                continue
            assert gap_above >= clearance, (
                "the gap ABOVE the drawing must pay a whole clearance; "
                "`spare < 2 * clearance` only buys 0.84 of one",
                where,
                clearance,
            )
            assert gap_below >= clearance, (
                "the gap BELOW the drawing must pay a whole clearance too",
                where,
                gap_below,
                clearance,
            )
            # And the ink itself, against each rule's own outermost ink row
            # rather than against the row the rule is centred on.
            overhang = -(-layout.thick_rule // 2)
            header_ink_bottom = area_top + self._rule_px(self.HEADER_RULE_PT) // 2
            footer_ink_top = area_bottom - (self._rule_px(self.FOOTER_RULE_PT) - 1) // 2
            assert placement.drawing_top - overhang > header_ink_bottom, where
            assert placement.drawing_bottom + overhang < footer_ink_top, where

        kinds = {verdict for _, verdict in verdicts}
        assert kinds == {"ratio", "footer"}, (
            "the scan must hold the boundary, with both regimes either side",
            sorted(kinds),
        )
        assert sum(1 for _, v in verdicts if v == "ratio") >= 15
        assert sum(1 for _, v in verdicts if v == "footer") >= 15
        flips = [
            (straddle[n - 1], straddle[n])
            for n in range(1, len(straddle))
            if straddle[n - 1][1] != straddle[n][1]
        ]
        assert len(flips) == 1, ("the verdict must change exactly once", flips)
        refused, floated = flips[0]
        # The refused case is the point of the whole test: its puzzle area DOES
        # hold the drawing (the spare is positive), and the ratio is abandoned
        # anyway because 42% of that spare would not clear the header rule.
        assert refused[1] == "footer" and floated[1] == "ratio", flips
        assert refused[2] > 0, (
            "the case below the boundary must have a positive spare, or this "
            "test is pinning `spare <= 0` and not the clearance",
            refused,
        )
        assert floated[3] == self._clearance_px(
            compute_layout(
                *_clue_sets(**self.STRADDLE), _spec(height_mm=floated[0])
            ).thick_rule
        ), (
            "the first case that floats must sit exactly one clearance below "
            "the header rule — the threshold is clearance / 0.42 of spare",
            floated,
        )

    def test_a_real_books_pages_keep_their_ink_off_both_drawn_rules(
        self, pages
    ) -> None:
        """The ink-level half: a real interior, with the frame's rules drawn.

        The rules' rows are measured off the page too — each is the one run of
        dark pixels that spans the whole text width, which no drawing narrower
        than the text block reaches — so neither side of this comparison is
        ``interior_frame``'s own answer.
        """
        spec = _spec()
        text_width = round((spec.width_mm - spec.gutter_mm - spec.outside_mm) * PX_PER_MM)
        area_top_mm, area_bottom_mm = _puzzle_area_mm(spec)
        header_row = round(area_top_mm * PX_PER_MM)
        footer_row = round(area_bottom_mm * PX_PER_MM)
        measured = 0
        for index in (TWO_UP_PAGE - 1, SINGLE_PAGE - 1):
            page = pages[index]
            dark = _dark(page)
            # Each rule really is drawn on the row this module's own
            # millimetres put it on — a run of ink across the whole text
            # width, which the rule is the only mark on a page to make. Both
            # sides of the clearance check below are therefore the page's own
            # ink against this file's own arithmetic, with
            # ``interior_frame`` on neither side.
            for name, row in (("header", header_row), ("footer", footer_row)):
                near = [
                    candidate
                    for candidate in range(row - 3, row + 4)
                    if dark[candidate].sum() >= text_width - 4
                ]
                assert near, (
                    f"interior page {index + 1} draws no {name} rule within "
                    f"3 px of row {row}"
                )
            drawings = (
                drawings_of(page) if index == TWO_UP_PAGE - 1 else [drawing_of(page)]
            )
            for position, drawing in enumerate(drawings):
                assert drawing.top > header_row + 3, (index, drawing.top, header_row)
                if len(drawings) == 2 and position == 1:
                    # **The exception this branch used to declare is gone.**
                    # Until the two-up rule gap, CARD-248's footer strip left
                    # a two-up page's lower drawing sitting ON the footer
                    # rule — its heavy border and the hairline stroked on the
                    # same pixel — and this branch pinned that coincidence so
                    # it would fail the day it became a gap. It has: the lower
                    # drawing now ends TWO_UP_RULE_GAP_MM (capped at a quarter
                    # of the pair's slack) above the footer reserve. So the
                    # lower slot clears the footer rule like every other
                    # drawing, and the clearance is that gap, measured: the
                    # border's leading ink sits up to half its 6 px rule
                    # inside the box's edge, hence 3 px more than the rows'
                    # own 3 px of slack.
                    gap_px = _two_up_rule_gap_mm(UPPER_PUZZLE, LOWER_PUZZLE) * PX_PER_MM
                    assert drawing.grid_bottom < footer_row - 3, (
                        index, drawing.grid_bottom, footer_row
                    )
                    assert abs((footer_row - drawing.grid_bottom) - gap_px) <= 3 + 3, (
                        index, drawing.grid_bottom, footer_row
                    )
                else:
                    assert drawing.grid_bottom < footer_row - 3, (
                        index, drawing.grid_bottom, footer_row
                    )
                measured += 1
        assert measured >= 3, measured

    def test_the_control_a_drawing_on_either_rule_fails_this_check(self) -> None:
        """The control that can fail (ADR-0039/R1): :meth:`_clears` — the very
        predicate the sweep above applies to every case — rejects a drawing
        whose ink reaches either rule's **row**. (Not its ink: that is the
        predicate's declared blind spot, recorded on :meth:`_clears`, and the
        last two assertions below are a tenth of a millimetre past each row
        rather than onto each rule's outermost ink.)

        The two placements fed to it are the two the 42% float exists to
        avoid: one whose top ink lands on the header rule (the ratio applied
        to a spare it cannot pay the clearance out of) and one whose bottom
        ink lands on the footer rule (the ratio run the other way, 0.42 of the
        spare *below* instead of above). Both are real page geometries —
        Book 1's own area and a real drawing's depth — with only the placement
        changed, so what is shown is that the sweep's green is this card's
        placement and not the check's indifference.
        """
        spec = self.SHEETS["book1 odd"]
        area = _puzzle_area_mm(spec)
        layout = compute_layout(*_clue_sets(20, 20, 5, 5), spec)
        depth_mm = (
            layout.page.drawing_bottom - layout.page.drawing_top
        ) / PX_PER_MM
        spare = (area[1] - area[0]) - depth_mm
        assert spare > 20.0, spare

        # This card's own placement clears both rules.
        floated_top = area[0] + SPARE_ABOVE * spare
        assert self._clears(floated_top, floated_top + depth_mm, area)
        # On the header rule, and on the footer rule: both rejected.
        assert not self._clears(area[0], area[0] + depth_mm, area)
        assert not self._clears(area[1] - depth_mm, area[1], area)
        # And a hair past either of them, which is the regime AC-4 degrades.
        assert not self._clears(area[0] - 0.1, area[0] - 0.1 + depth_mm, area)
        assert not self._clears(area[1] - depth_mm + 0.1, area[1] + 0.1, area)


class TestBookPuzzleFrame_TallestGridYieldsToTheFooter:
    """AC-4 — the tallest grid that fits at all: the 42% rule degrades to "as
    low as it fits" rather than pushing ink further past the footer rule, and
    the page says which rule bound it.

    The deepest drawing the book admits is a 30-row grid behind a 15-deep
    column gutter: 45 cells down. The cell is fitted against the usable height
    **less the band** (FR-030), which is up to one whole footer strip deeper
    than the puzzle area, so a height-bound drawing is deeper than the area it
    is placed in by construction — the degenerate case this AC is about, and
    one every trim reaches by being short rather than by being unusual.

    "The page says which rule bound it" is
    :attr:`~nonogram.export.layout.PagePlacement.vertical_bound`: ``"ratio"``
    when the split placed the drawing, ``"footer"`` when the area could not
    hold it and the drawing was held at the band's foot instead. The renderer
    reads the same verdict through its own all-or-nothing footer condition and
    prints no footer group on such a page, which is the only reason "no ink on
    the footer rule" can still be true of it.
    """

    #: Book 1's own width on a **short** trim (16.0 cm, well inside KDP's
    #: 10 cm minimum): the deepest admissible drawing cannot fit its 93.7 mm
    #: puzzle area, while still fitting the usable *width* — so the page's ink
    #: is measurable by the drawing's own rules, which it would not be on a
    #: trim so small that the drawing runs off the sheet sideways too.
    SHORT = _spec(height_mm=160.0)
    #: The deepest drawing the book admits: 30 rows behind a 15-deep column
    #: gutter, 45 cells down.
    TALLEST = dict(columns=30, rows=30, row_depth=15, column_depth=15)

    def test_the_tallest_grid_is_held_at_the_bands_foot_and_says_so(self) -> None:
        layout = compute_layout(*_clue_sets(**self.TALLEST), self.SHORT)
        placement = layout.page

        assert placement.vertical_bound == "footer", "the page must name the rule"
        assert abs(placement.drawing_top / PX_PER_MM - _fixed_top_mm(self.SHORT)) <= 0.5
        assert placement.drawing_top == placement.band_bottom

    def test_it_is_not_pushed_further_down_than_the_old_placement(self) -> None:
        """"Rather than pushing ink past the footer rule": the degraded page's
        ink stops exactly where it stopped before this card — the 42% rule does
        not spend a spare it has not got."""
        layout = compute_layout(*_clue_sets(**self.TALLEST), self.SHORT)
        page = render_image(_payload(**self.TALLEST), page_spec=self.SHORT)
        _, ink_top, _, ink_bottom = _area_ink_box(page, self.SHORT)
        _, area_bottom = _puzzle_area_mm(self.SHORT)
        overhang = -(-layout.thick_rule // 2)

        assert layout.page.drawing_top - overhang <= ink_top <= layout.page.drawing_top
        # The premise, read off the layout and NOT off ``ink_bottom``:
        # :func:`_area_ink_box` crops the page at ``round(area_bottom *
        # PX_PER_MM)``, so ``ink_bottom`` saturates on that row and would read
        # as "deeper than the area" for a drawing that stopped exactly on the
        # footer rule. Measured on this fixture: the crop row is 1632 while the
        # drawing's own bottom edge is 1749 px, 9.9 mm below the rule (30 mm
        # before CARD-392 shrank the footer band) -- which is the number that
        # makes the claim (CARD-224 review cycle 1, F-003).
        assert ink_bottom == round(area_bottom * PX_PER_MM), (
            "the crop saturates here, which is why the premise below is taken "
            "from the layout and not from this number"
        )
        assert (layout.page.drawing_bottom + overhang) / PX_PER_MM > area_bottom + 8.0, (
            "this page's drawing really is deeper than its puzzle area, by "
            "millimetres and not by the crop's own rounding"
        )
        # The ratio, had it been applied to a negative spare, would have
        # lifted the drawing *above* the header rule; "as low as it fits"
        # means it is not moved at all.
        assert ink_top / PX_PER_MM > _puzzle_area_mm(self.SHORT)[0]

    def test_such_a_page_prints_no_footer_group_to_cross(self) -> None:
        """The renderer's half, on a real page: a book on this trim gets
        CARD-200's corner folio and no footer rule, so there is no rule on the
        page for the drawing to touch."""
        layout = compute_layout(*_clue_sets(**self.TALLEST), self.SHORT)

        assert _footer_group_omitted(layout, self.SHORT)
        assert layout.page.drawing_bottom / PX_PER_MM > _puzzle_area_mm(self.SHORT)[1]

    #: Book 1's own trim and an 18x22 behind 9- and 11-deep gutters (a 23x27
    #: behind 11-deep ones until CARD-392 gave the area its 236 px back): the **third**
    #: case, which neither of the two names ``vertical_bound`` carries
    #: describes on its face. Its puzzle area *does* hold the drawing — the
    #: spare is a positive 3 px — and the page still reports ``"footer"``,
    #: because 42% of 3 px would not clear the header rule. Measured, not
    #: contrived: 107 distinct placements of a 21 x 21 extent sweep at depths 2 to 15
    #: (mine, CARD-392) land in ``vertical_bound == "footer"`` with a
    #: positive spare on this sheet alone.
    THIRD_CASE = dict(columns=18, rows=22, row_depth=9, column_depth=11)

    def test_a_positive_spare_too_small_to_clear_the_rule_also_reports_footer(self) -> None:
        """The third case, named (CARD-224 review cycle 1, F-008).

        ``"footer"`` is documented as "the drawing is as deep as the area or
        deeper, or this sheet has no puzzle area at all". There is a third way
        to reach it: a spare that is positive but smaller than
        ``clearance / 0.42``, where the area holds the drawing and the ratio is
        abandoned for the clearance's sake. AC-4's "the page says which rule
        bound it" names the footer rule on such a page, and what actually bound
        it is the **header** rule's clearance.

        **Why that is safe.** The degraded placement stops at the band's foot
        or one pixel of drawing past the footer rule, whichever is lower, so
        the renderer's all-or-nothing footer condition omits the whole footer
        group and there is no rule on the page for the ink to cross. That is
        true at every band depth since review cycle 2 (F2-001) and is pinned
        on a 9 mm band by
        :meth:`test_a_shallow_band_cannot_leave_ink_on_a_drawn_footer_rule`.

        **What this test pins is the Book 1 arithmetic that makes the clamp
        inert here**, not the invariant itself. The band's own lift
        (``band_mm / 8`` = 17.72 px on a 12 mm band) exceeds the clearance
        threshold (14.29 px), so the band's foot is already the lower of the
        two rows and the drawing sits exactly where every placed drawing sat
        before this card. Below about 10.4 mm of band that stops being true
        and the clamp starts to move the row — which is a different page, not
        a broken one, and is the sibling test's subject. The lift assertion
        below is the tripwire on the inertness: it reds if ``band_mm`` or
        :data:`HEADER_RULE_LIFT_SHARE` moves far enough that this sheet's
        degraded pages are no longer byte-identical to their predecessors.
        """
        spec = _spec()
        layout = compute_layout(*_clue_sets(**self.THIRD_CASE), spec)
        placement = layout.page
        area_top_mm, area_bottom_mm = _puzzle_area_mm(spec)
        area_top = round(area_top_mm * PX_PER_MM)
        area_bottom = round(area_bottom_mm * PX_PER_MM)
        spare = (area_bottom - area_top) - (placement.drawing_bottom - placement.drawing_top)

        assert 0 < spare, ("the area does hold this drawing", spare)
        assert placement.vertical_bound == "footer"
        assert placement.drawing_top == placement.band_bottom
        # What the verdict's own name would predict is false here.
        assert placement.drawing_bottom - placement.drawing_top < area_bottom - area_top

        # The coupling, in the sheet's own pixels: the band's lift has to be
        # the larger of the two, or the degraded page keeps a footer rule that
        # its drawing then crosses.
        clearance = TestBookPuzzleFrame_GridClearsBothRules._clearance_px(layout.thick_rule)
        threshold = clearance / SPARE_ABOVE
        lift = HEADER_RULE_LIFT_SHARE * spec.band_mm * PX_PER_MM
        assert lift > threshold, (
            "band_mm is deep enough that the band's foot is already below the "
            "footer rule, so the degraded page is the pre-CARD-224 one",
            lift,
            threshold,
        )
        # The invariant, which holds at every band depth: the drawing's bottom
        # edge is past the footer rule, so the renderer omits the whole group.
        assert placement.drawing_bottom > area_bottom, (lift, threshold, spare)
        assert _footer_group_omitted(layout, spec)

    def test_the_control_a_trim_that_can_hold_it_floats_instead(self) -> None:
        """The control that can fail (ADR-0039/R1): the same 45-cell drawing on
        Book 1's own trim, which *can* hold it, reports ``"ratio"`` and floats
        — so ``"footer"`` above is a verdict about the sheet and not a constant
        this card returns everywhere."""
        layout = compute_layout(*_clue_sets(**self.TALLEST), _spec())
        placement = layout.page

        assert placement.vertical_bound == "ratio"
        assert placement.drawing_top > placement.band_bottom
        assert not _footer_group_omitted(layout, _spec())

    #: The shallow-band sheet and the drawing that lands in the window the
    #: band's lift no longer covers (review cycle 2, F2-001). A 29x17 behind
    #: 14- and 9-deep gutters on a 9 mm band and a 160 mm trim: 43 drawing
    #: columns by 26 rows, a spare of 14 px against a 14.29 px threshold (a 23x9
    #: behind 5-deep gutters with a spare of 13 px until CARD-392 gave the area
    #: its 236 px back; the window is 13..14 px wide, which is why it is a
    #: search result and not a round figure), so the ratio is
    #: refused — and the band's lift is only 13.30 px, so the band's foot
    #: alone would leave the drawing's bottom edge **on** the footer rule.
    SHALLOW_BAND_MM = 9.0
    SHALLOW_TRIM_MM = 160.0
    SHALLOW_CASE = dict(columns=29, rows=17, row_depth=14, column_depth=9)

    def test_a_shallow_band_cannot_leave_ink_on_a_drawn_footer_rule(self) -> None:
        """EC-022 on a band the stored profiles do not store (review cycle 2,
        F2-001).

        The degraded regime's whole bargain is *either the drawing clears the
        footer rule, or the footer group is not drawn*. Until this cycle the
        second half was delivered by the title band's own lift outrunning the
        clearance threshold — 17.72 px against 14.29 px on Book 1's 12 mm
        band — which is a ``PrintProfile`` field and not an argument. Shallow
        the band to 9 mm, an ordinary typographic decision on a small trim,
        and the lift becomes 13.30 px: the band's foot then leaves the drawing
        **above** the footer rule, the renderer strokes the whole footer group,
        and the grid's 6 px border is stroked three rows past the hairline.

        So this test states the bargain directly, and it states the defect it
        guards against in the test's own arithmetic rather than trusting the
        placement: the row the band's foot *would* have given is computed here
        from the sheet's millimetres, and it is asserted to be the unsafe one.
        What the placement must then do is stop lower.
        """
        spec = _spec(height_mm=self.SHALLOW_TRIM_MM, band_mm=self.SHALLOW_BAND_MM)
        layout = compute_layout(*_clue_sets(**self.SHALLOW_CASE), spec)
        placement = layout.page
        area_top_mm, area_bottom_mm = _puzzle_area_mm(spec)
        area_bottom = round(area_bottom_mm * PX_PER_MM)
        overhang = -(-layout.thick_rule // 2)
        depth = placement.drawing_bottom - placement.drawing_top

        # The premise: this sheet's band really is too shallow to carry the
        # degraded placement past the footer rule on its own.
        clearance = TestBookPuzzleFrame_GridClearsBothRules._clearance_px(layout.thick_rule)
        lift = HEADER_RULE_LIFT_SHARE * spec.band_mm * PX_PER_MM
        assert lift < clearance / SPARE_ABOVE, (lift, clearance / SPARE_ABOVE)
        assert placement.vertical_bound == "footer"
        spare = (area_bottom - round(area_top_mm * PX_PER_MM)) - depth
        assert spare > 0, ("case (iii): the area does hold this drawing", spare)

        # The defect, worked out here: had the drawing been held at the band's
        # foot, its bottom edge would have stopped at or above the footer rule
        # (so the renderer strokes the whole footer group) while its ink ran
        # past it. Both halves are asserted, so this test cannot pass by the
        # case having quietly stopped being the unsafe one.
        at_band_foot = round((TOP_MM + spec.band_mm) * PX_PER_MM) + depth
        assert at_band_foot <= area_bottom, (
            "the band's foot would keep the footer group on this page",
            at_band_foot,
            area_bottom,
        )
        assert at_band_foot + overhang > area_bottom, (
            "and the drawing's ink would run past the hairline it strokes",
            at_band_foot + overhang,
            area_bottom,
        )

        # The bargain: the placement stops lower, so the group is omitted and
        # there is no rule on the page for the ink to cross.
        assert placement.drawing_top > placement.band_bottom, (
            "the placement must refuse the band's foot on this sheet",
            placement.drawing_top,
            placement.band_bottom,
        )
        assert placement.drawing_bottom > area_bottom
        assert _footer_group_omitted(layout, spec), (
            "the footer group's own all-or-nothing condition must refuse "
            "this page"
        )

    def test_the_control_a_deep_drawing_on_that_sheet_keeps_the_bands_foot(
        self,
    ) -> None:
        """The control that can fail (ADR-0039/R1): the clamp above is a
        ``max`` and not a new fixed row.

        The same shallow sheet with a drawing deeper than its puzzle area —
        case (i), not case (iii) — is held at the band's foot exactly as
        before, because the band's foot is already the lower of the two rows
        there. A clamp that had replaced the band's foot rather than bounded
        it would move this drawing too, and the first assertion would fail.
        """
        spec = _spec(height_mm=self.SHALLOW_TRIM_MM, band_mm=self.SHALLOW_BAND_MM)
        layout = compute_layout(*_clue_sets(**self.TALLEST), spec)
        placement = layout.page
        _, area_bottom_mm = _puzzle_area_mm(spec)
        area_bottom = round(area_bottom_mm * PX_PER_MM)

        assert placement.vertical_bound == "footer"
        assert placement.drawing_top == placement.band_bottom
        # And it is in the other regime: the area cannot hold it at all.
        area_top = round(_puzzle_area_mm(spec)[0] * PX_PER_MM)
        assert (
            placement.drawing_bottom - placement.drawing_top > area_bottom - area_top
        ), "the control must be case (i): deeper than the area, not case (iii)"
        assert _footer_group_omitted(layout, spec)

    def test_a_gap_of_exactly_one_clearance_floats(self) -> None:
        """Which side of the strict comparison the boundary falls on (review
        cycle 2, F2-006).

        The placement refuses the ratio while ``gap_above < clearance``, so a
        gap of **exactly** one clearance floats. No sweep of trim heights can
        show that: ``spare`` would have to be exactly ``50 x clearance / 21``
        of a pixel and a scan steps over it, which is why cycle 2 found the
        ``<=`` mutant surviving :meth:`
        test_the_clearance_threshold_is_the_gap_above_and_not_half_the_spare`.
        It is therefore stated on the placement itself, with the spare handed
        in exactly: at the boundary the drawing floats and sits one clearance
        below the header rule, and a hair under it is refused.

        The clearance is :meth:`_clearance_px`'s — derived from the three rule
        weights written out in this module, not imported — and the share is
        this file's own ``42/100``.
        """
        spec = _spec()
        area_top = round(_puzzle_area_mm(spec)[0] * PX_PER_MM)
        area_bottom = round(_puzzle_area_mm(spec)[1] * PX_PER_MM)
        band_bottom = (
            (Fraction(repr(TOP_MM)) + Fraction(repr(BAND_MM)))
            * DPI
            / Fraction(254, 10)
        )
        thick_rule = 6
        clearance = TestBookPuzzleFrame_GridClearsBothRules._clearance_px(thick_rule)
        share = Fraction(42, 100)

        at_boundary = Fraction(clearance) / share
        for spare, expected in (
            (at_boundary, "ratio"),
            (at_boundary - Fraction(1, 10**6), "footer"),
        ):
            top, bound = _placed_drawing_top(
                spec,
                band_bottom=band_bottom,
                drawing_height=Fraction(area_bottom - area_top) - spare,
                thick_rule=thick_rule,
            )
            assert bound == expected, (spare, bound, expected)
            if expected == "ratio":
                # Exactly one clearance below the header rule — which is what
                # makes the floated case's gap the boundary and not a value
                # that merely rounds to it.
                assert top - area_top == clearance, (top, area_top, clearance)
            else:
                assert top == band_bottom, (top, band_bottom)


class TestBookPuzzleFrame_NoEmptyLowerThird:
    """AC-6 — the owner's "the lower third of the page is empty" (pp. 28, 75,
    125 of the corpus), measured.

    **Corrected 2026-10-17, and this class states the corrected form.** The
    criterion first read "the empty band below the grid is no larger than the
    band above it", which contradicts AC-2: the split is deliberately 42/58,
    so the band below *is* the larger one. The corrected criterion is the
    ratio itself plus a bound — the band below is at most **1.4x** the band
    above — and the defect it replaces is that today the lower band is the
    *whole* spare, which is what the three named pages show.

    The three pages are reached as the owner reaches them: the three deepest
    page kinds a corpus book prints at Book 1's own trim, at the three clue
    depths that give a 15x15, a 20x20 and a 30x30 their real gutters. What is
    asserted is the ratio and the 1.4x bound, and the control is the retired
    placement, whose lower band is 13 to 19 times its upper one.
    """

    #: The three pages, at the three clue depths that give them their real
    #: gutters. Each has at least 20 mm of spare, so a ratio read back off the
    #: ink (0.085 mm a pixel) is a measurement and not a rounding: the
    #: 20x20's own depth is 5 and not 8 for that reason — at depth 8 its
    #: drawing is 210 mm of a 213.1 mm area and the whole claim would rest on
    #: three millimetres.
    CASES = (
        dict(columns=15, rows=15, row_depth=7, column_depth=7),
        dict(columns=20, rows=20, row_depth=5, column_depth=5),
        dict(columns=30, rows=30, row_depth=9, column_depth=9),
    )

    @staticmethod
    def _bands_mm(case: dict, spec: PageSpec) -> tuple[float, float]:
        page = render_image(_payload(**case), page_spec=spec)
        _, top, _, bottom = _area_ink_box(page, spec)
        area_top, area_bottom = _puzzle_area_mm(spec)
        return (top / PX_PER_MM - area_top, area_bottom - bottom / PX_PER_MM)

    @pytest.mark.parametrize("index", range(3))
    def test_the_spare_is_split_and_the_lower_band_is_at_most_1_4x_the_upper(
        self, index: int
    ) -> None:
        spec = _spec()
        above, below = self._bands_mm(self.CASES[index], spec)
        spare = above + below

        assert above > 0 and below > 0, (above, below)
        assert spare > 20.0, (spare, "this page must have real spare to split")
        assert above / spare == pytest.approx(SPARE_ABOVE, abs=0.005)
        assert below / spare == pytest.approx(1 - SPARE_ABOVE, abs=0.005)
        assert below <= 1.4 * above + 1e-9, (above, below)

    @pytest.mark.parametrize("index", range(3))
    def test_the_control_the_retired_placement_leaves_the_whole_spare_below(
        self, index: int
    ) -> None:
        """The control that can fail (ADR-0039/R1), and the defect's own
        measurement: under the fixed top edge the band above is the band's own
        lift (1.5 mm) and the band below is everything else, 13x to 19x it —
        which is the owner's "the lower third of the page is empty", and fails
        both assertions above."""
        spec = _spec()
        case = self.CASES[index]
        drawing_columns = case["row_depth"] + case["columns"]
        drawing_rows = case["column_depth"] + case["rows"]
        cell = _expected_cell_mm(spec, drawing_columns, drawing_rows)
        area_top, area_bottom = _puzzle_area_mm(spec)
        above = _fixed_top_mm(spec) - area_top
        below = area_bottom - (_fixed_top_mm(spec) + drawing_rows * cell)
        spare = above + below

        assert above == pytest.approx(BAND_MM * HEADER_RULE_LIFT_SHARE, abs=0.01)
        assert below > 1.4 * above, (above, below)
        assert abs(above / spare - SPARE_ABOVE) > 0.1


# --------------------------------------------------------------------------
# CARD-336 — the frame-centre oracle: AC-1 (the reading IS a boundary, in
# both media, against a coordinate) and AC-3 (the placed-edge population of
# this module and of `tests/property/test_book_pdf_geometry.py`, derived)
# --------------------------------------------------------------------------


#: How far a frame-centre reading may sit from the boundary ``compute_layout``
#: itself states, in device pixels. **Half a pixel**, and it is arithmetic
#: rather than a tolerance: the frame rule inks an even number of pixel lines
#: (six, measured, in both media), so the centre of its run is a half-integer
#: while the boundary it is stroked on is a whole pixel. Measured at exactly
#: +0.5 px in raster and −0.5 px in vector, Pillow inking ``c-2..c+3`` and
#: poppler ``c-3..c+2`` for one boundary ``c``.
FRAME_CENTRE_TOLERANCE_PX = 0.5


#: And how far the two media's readings of the **same** page may sit from each
#: other: one pixel — the two half pixels above, and CARD-330's own measured
#: figure for a content stream's operand against the boundary (0.0847 mm at
#: 300 DPI). The *ink* reading of the same page disagrees across the media by
#: **three** pixels, which is the control below.
FRAME_CENTRE_CROSS_MEDIUM_PX = 1.0


#: The vector medium's declared frame stroke, in device pixels: ADR-0037/R2's
#: heavy rule is 1.3 pt and a point is 1/72 in, so 5.4167 px at 300 DPI. It is
#: here only to be shown **different from the width the page inks** (six), so
#: that a reading keyed on the declared figure is visibly not a reading of the
#: page.
DECLARED_VECTOR_RULE_PX = 1.3 * DPI / 72


@dataclasses.dataclass(frozen=True)
class _BothMedia:
    """One book puzzle page drawn both ways, and the boundary it was laid at.

    Attributes:
        coordinate: ``compute_layout``'s own :class:`PuzzleFrame` for this
            page — the drawing's two outer boundaries, as the geometry states
            them and before any ink exists. Every assertion below is made
            against this and never against the other medium's ink.
        raster: The page as ``BookPDFGenerator._blank_page`` draws it, which
            is Pillow stroking four butt-capped lines.
        vector: The same page as ``.vector_puzzle_page`` writes it, read back
            through ``interior_images`` — poppler's raster of one mitred
            ``re`` — at the page's own DPI, so both sides are device pixels
            in one domain (CARD-330).
    """

    coordinate: object
    raster: Image.Image
    vector: Image.Image


@pytest.fixture(scope="module")
def both_media() -> _BothMedia:
    """The same page in each medium, drawn once for this file (CARD-218's rule).

    Deliberately **not** the module's shared ``pages`` fixture: that one is a
    whole interior in whichever medium the registry declares, and what AC-1
    needs is one page in *each*, with no registry touched (G-2). The two
    writers take the same arguments, so the page is the same page and the
    medium is the only difference between the two sides.
    """
    case = dict(columns=20, rows=20, row_depth=4, column_depth=5)
    page_number = SINGLE_PAGE
    generator = BookPDFGenerator(_book())
    payload = BookPDFGenerator._payload(
        _book_puzzle(**case, puzzle_id="card336-ac1")
    )
    cells = generator.cell_sizes([payload])
    spec = generator._puzzle_page_spec(
        page_number, cells.get(BookPDFGenerator._grid_size(payload))
    )
    layout = compute_layout(payload.row_clues, payload.column_clues, spec)
    assert layout.frame is not None, "this page must be a framed book page"
    stream = generator.vector_puzzle_page(payload, 1, page_number, cells)
    return _BothMedia(
        coordinate=layout.frame,
        raster=generator._blank_page(payload, 1, page_number, cells),
        vector=interior_images([stream])[0],
    )


class TestFrameCentre_TheReadingIsABoundaryInBothMedia:
    """CARD-336 AC-1: ``frame_centre_of`` reports where the drawing **is**.

    ADR-0042/R6's own note asked for "an oracle that reads the frame rule's
    CENTRE rather than its first inked line". This is the judgement of that
    oracle, and it is complete with no page converted: the two writers are
    both on `main` today, the coordinate both are laid against is
    ``compute_layout``'s, and nothing here reads ``_RASTER_DECLARATIONS``.

    Every assertion is against the **coordinate**. The cross-medium cell
    compares two *boundary* readings, neither of which is an ink extent, so
    no claim here is one medium's ink measured against the other's.
    """

    def test_each_mediums_reading_is_the_boundary_the_layout_states(
        self, both_media
    ) -> None:
        """Both sides, each against ``layout.frame``, to within half a pixel."""
        frame = both_media.coordinate
        for medium, page in (
            ("raster", both_media.raster),
            ("vector", both_media.vector),
        ):
            boundary = frame_centre_of(page, drawing_of(page))
            assert abs(boundary.frame_left - frame.left) <= (
                FRAME_CENTRE_TOLERANCE_PX + 1e-9
            ), (medium, boundary.frame_left, frame.left)
            assert abs(boundary.frame_top - frame.top) <= (
                FRAME_CENTRE_TOLERANCE_PX + 1e-9
            ), (medium, boundary.frame_top, frame.top)

    def test_the_two_media_read_the_same_page_as_the_same_boundary(
        self, both_media
    ) -> None:
        """And they agree with each other, within one pixel."""
        here = frame_centre_of(both_media.raster, drawing_of(both_media.raster))
        there = frame_centre_of(both_media.vector, drawing_of(both_media.vector))

        assert abs(here.frame_left - there.frame_left) <= (
            FRAME_CENTRE_CROSS_MEDIUM_PX + 1e-9
        ), (here, there)
        assert abs(here.frame_top - there.frame_top) <= (
            FRAME_CENTRE_CROSS_MEDIUM_PX + 1e-9
        ), (here, there)

    def test_the_control_the_ink_reading_cannot_make_either_claim(
        self, both_media
    ) -> None:
        """The control that CAN fail (ADR-0039/R1), and the defect's measure.

        The same two claims on :class:`~tests.helpers.page_ink.Drawing`'s own
        extents: the vector page's ink sits **3 px** from the boundary and
        the two media's ink readings sit 3 px from each other — so neither
        bound above is met by the reading this card replaces, and both bounds
        are therefore load-bearing rather than generous.
        """
        frame = both_media.coordinate
        here = drawing_of(both_media.raster)
        there = drawing_of(both_media.vector)

        assert abs(there.left - frame.left) > FRAME_CENTRE_TOLERANCE_PX, there.left
        assert abs(there.top - frame.top) > FRAME_CENTRE_TOLERANCE_PX, there.top
        assert abs(here.left - there.left) > FRAME_CENTRE_CROSS_MEDIUM_PX, (
            here.left,
            there.left,
        )
        assert abs(here.top - there.top) > FRAME_CENTRE_CROSS_MEDIUM_PX, (
            here.top,
            there.top,
        )

    def test_the_rule_width_is_the_pages_and_not_the_declared_figure(
        self, both_media
    ) -> None:
        """Item 1's requirement, asserted: the width comes off the page.

        The reading reports the width it used, and it is the number of pixel
        lines the rule really inks — counted here a second time, off the
        page, without the helper. In the vector medium that is **six** lines
        where the stroke is *declared* at 5.4167 px (ADR-0037/R2's 1.3 pt),
        so a reading keyed on the declared figure would be reading the
        writer's constant and not the page: the two are asserted unequal.
        """
        for medium, page in (
            ("raster", both_media.raster),
            ("vector", both_media.vector),
        ):
            drawing = drawing_of(page)
            boundary = frame_centre_of(page, drawing)
            dark = _dark(page)
            # Recounted here, independently of the helper: the inked run that
            # holds the drawing's own left edge, taken on a row through the
            # MIDDLE of the grid's first cell — never the drawing's midpoint,
            # which lands on a grid rule and reads the whole drawing as one
            # run (measured, and the first draft of this cell did exactly
            # that). The same down the page for the top side.
            row = drawing.grid_top + round(drawing.cell / 2)
            column = drawing.grid_left + round(drawing.cell / 2)
            across = [
                run
                for run in _groups(np.flatnonzero(dark[row]))
                if run[0] <= drawing.left <= run[-1]
            ]
            down = [
                run
                for run in _groups(np.flatnonzero(dark[:, column]))
                if run[0] <= drawing.top <= run[-1]
            ]
            assert [len(run) for run in across] == [boundary.left_rule_px], (
                medium, boundary, [len(run) for run in across]
            )
            assert [len(run) for run in down] == [boundary.top_rule_px], (
                medium, boundary, [len(run) for run in down]
            )
            assert boundary.left_rule_px == boundary.top_rule_px, (medium, boundary)

        vector = frame_centre_of(both_media.vector, drawing_of(both_media.vector))
        assert vector.left_rule_px != pytest.approx(DECLARED_VECTOR_RULE_PX), (
            "the page inks the declared stroke width exactly, so this cell can "
            "no longer tell a reading of the page from a reading of the constant"
        )
        assert vector.left_rule_px == 6, vector.left_rule_px

    def test_a_drawing_whose_outer_rule_is_not_a_frames_is_refused(self) -> None:
        """ADR-0039/R2, in the reading itself: it refuses rather than guessing.

        An unframed drawing's leftmost full-height rule is the grid's own
        left border, a whole clue gutter inside the drawing's left edge, so
        the reading cannot be a frame's centre and says so — rather than
        reporting the grid's border as the drawing's boundary.
        """
        case = dict(columns=20, rows=20, row_depth=4, column_depth=5)
        page = render_image(
            _payload(**case), page_spec=replace(_spec(), frame=False)
        )
        drawing = drawing_of(page)
        assert drawing.framed is False, "this control needs an unframed drawing"
        with pytest.raises(ValueError, match="does not hold the drawing's own"):
            frame_centre_of(page, drawing)


class TestFrameCentre_EveryPlacedEdgeSiteIsClassified:
    """CARD-336 AC-3 and its EC(ADR-0039/R2): the population is **derived**.

    The two modules in this card's ``Touches`` each declare their own
    placed-edge bound — ``HALF_PIXEL_MM`` there, :data:`EDGE_TOLERANCE_PX`
    here — and an assertion read against that bound is a placed-edge site.
    That is the same derivation shape ``tests/test_book_pdf.py``'s
    ``TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium`` uses over
    ``EDGE_TOLERANCE_MM``, and it is a derivation rather than a list: a site
    added tomorrow is in the population the day it is written, and a site
    this walk cannot place is a **FAILURE** (ADR-0039/R2) rather than a pass.

    Every site lands in exactly one of four classes:

    ``boundary``
        it reads a :class:`~tests.helpers.page_ink.FrameCentre` field — this
        card's re-expression.
    ``cancelling``
        every ink extent it reads is paired with another inside one
        expression, so the half rule cancels out of the difference. The
        reading the ``Drawing`` comment calls "ink with ink".
    ``no_extent``
        it reads no ink extent at all: a coordinate against a coordinate, or
        a reading from some other helper.
    :data:`PLACED_EDGE_ON_THE_INK_BY_DECLARATION`
        it differences an ink extent against a coordinate **and says why**,
        with its measurement. One site qualifies, and that is the finding
        this card raises rather than a tolerance it widened (G-1).

    **Which fields are which is read off the two dataclasses**, not written
    out: the ink extents are :class:`~tests.helpers.page_ink.Drawing`'s own
    fields less the three that are not edges, and the boundaries are
    ``FrameCentre``'s. A field renamed on either moves this walk with it, and
    the two names are asserted disjoint so that no attribute can be both.
    """

    _MODULE_BOUNDS = {
        "tests/property/test_book_pdf_geometry.py": "HALF_PIXEL_MM",
        "tests/test_book_puzzle_frame.py": "EDGE_TOLERANCE_PX",
    }
    _INK_READERS = frozenset({"drawing_of", "drawings_of"})
    _BOUNDARY_READERS = frozenset({"frame_centre_of"})

    #: The floor, anchored to the two modules' own site counts as measured on
    #: 2026-11-04. Not a target: a walk that finds fewer sites than this has
    #: narrowed, which is the permissive direction, and a bound renamed out of
    #: existence is the quietest way for that to happen.
    _SITE_FLOOR = {
        "tests/property/test_book_pdf_geometry.py": 9,
        "tests/test_book_puzzle_frame.py": 9,
    }

    @staticmethod
    def _ink_edges() -> frozenset[str]:
        """``Drawing``'s ink extents: its fields, less the three that are not."""
        fields = set(Drawing.__dataclass_fields__)
        not_an_edge = {"columns", "rows", "framed"}
        assert not_an_edge <= fields, sorted(not_an_edge - fields)
        return frozenset(fields - not_an_edge)

    @staticmethod
    def _boundary_fields() -> frozenset[str]:
        """``FrameCentre``'s boundaries: its fields, less the measured widths."""
        fields = set(FrameCentre.__dataclass_fields__)
        widths = {name for name in fields if name.endswith("_rule_px")}
        assert widths, sorted(fields)
        return frozenset(fields - widths)

    @classmethod
    def _tree(cls, path: str) -> ast.Module:
        root = Path(__file__).resolve().parent.parent
        return ast.parse((root / path).read_text(encoding="utf-8"), filename=path)

    @staticmethod
    def _functions(tree: ast.Module) -> dict[ast.AST, str]:
        """Every function of ``tree``, by its class-qualified name."""
        found: dict[ast.AST, str] = {}

        def walk(node: ast.AST, prefix: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    walk(child, f"{prefix}{child.name}::")
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found[child] = prefix + child.name
                    walk(child, f"{prefix}{child.name}.")
                else:
                    walk(child, prefix)

        walk(tree, "")
        return found

    @staticmethod
    def _bindings(function: ast.AST, module: ast.Module) -> dict[str, list[ast.AST]]:
        """``name -> [the expressions it was bound from]``.

        The function's own statements and the module's **top level** — never
        another function's, which would make one file's every local name
        resolvable from every other site in it.
        """
        table: dict[str, list[ast.AST]] = {}

        def bind(target: ast.AST, value: ast.AST) -> None:
            if isinstance(target, ast.Name):
                table.setdefault(target.id, []).append(value)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    bind(element, value)
            elif isinstance(target, ast.Starred):
                bind(target.value, value)

        for node in list(module.body) + list(ast.walk(function)):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    bind(target, node.value)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value:
                bind(node.target, node.value)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                bind(node.target, node.iter)
            elif isinstance(
                node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
            ):
                for generator in node.generators:
                    bind(generator.target, generator.iter)
            elif isinstance(node, ast.withitem) and node.optional_vars:
                bind(node.optional_vars, node.context_expr)
        return table

    @classmethod
    def _readers_behind(
        cls, name: str, table: dict[str, list[ast.AST]], seen: set[str] | None = None
    ) -> set[str]:
        """Which oracle ``name`` came from — to a fixed point through locals.

        The closure is what makes a house-style binding resolvable: the
        geometry module writes ``by_number = {n: drawing_of(...)}`` and then
        ``drawing = by_number[n]``, so a depth-1 reading would place the
        second name nowhere at all.
        """
        seen = set() if seen is None else seen
        if name in seen:
            return set()
        seen.add(name)
        found: set[str] = set()
        for value in table.get(name, ()):
            for node in ast.walk(value):
                if isinstance(node, ast.Call):
                    called = (
                        node.func.id
                        if isinstance(node.func, ast.Name)
                        else getattr(node.func, "attr", "")
                    )
                    if called in cls._INK_READERS:
                        found.add("ink")
                    if called in cls._BOUNDARY_READERS:
                        found.add("boundary")
                elif isinstance(node, ast.Name) and node.id != name:
                    found |= cls._readers_behind(node.id, table, seen)
        return found

    @staticmethod
    def _root(node: ast.AST) -> str | None:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    @classmethod
    def _contributing(
        cls,
        expression: ast.AST,
        table: dict[str, list[ast.AST]],
        seen: set[str] | None = None,
    ) -> list[ast.AST]:
        """``expression`` and every expression its local names were bound from.

        Without this the walk reads only what is written inside the ``assert``,
        and this tree's house style puts the measurement one line above it
        (``left_spare = ...`` then ``assert abs(left_spare - right_spare)``).
        """
        seen = set() if seen is None else seen
        trees = [expression]
        for node in ast.walk(expression):
            if isinstance(node, ast.Name) and node.id not in seen:
                seen.add(node.id)
                for value in table.get(node.id, ()):
                    trees += cls._contributing(value, table, seen)
        return trees

    @staticmethod
    def _multiple(site: ast.AST, bound: str) -> float:
        """The constant ``site`` multiplies ``bound`` by, or 1 for a bare read."""
        for node in ast.walk(site):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                for one, other in ((node.left, node.right), (node.right, node.left)):
                    if (
                        isinstance(one, ast.Name)
                        and one.id == bound
                        and isinstance(other, ast.Constant)
                    ):
                        return other.value
        return 1

    @classmethod
    def _partition(cls, path: str, tree: ast.Module | None = None) -> list:
        """``[((path, qualified name, multiple), class)]`` for ``path``'s sites.

        A **list**, and that is this walk's own measured lesson rather than a
        style choice: keyed on that triple, a dict loses one site of
        ``tests/property/test_book_pdf_geometry.py``, whose
        ``..._MirroredMarginsCentreDrawingForEveryParity_pdf_pages`` carries
        **two** sites at four half pixels — one re-expressed and one
        cancelling. Nine sites became eight keys and the lost one was never
        classified. The same shape ``tests/test_book_pdf.py``'s
        ``_COLLIDING_SITES`` records, met again here;
        :meth:`test_one_key_really_does_hold_two_sites` is what keeps the
        regression red rather than quiet.
        """
        bound = cls._MODULE_BOUNDS[path]
        tree = cls._tree(path) if tree is None else tree
        ink_edges, boundaries = cls._ink_edges(), cls._boundary_fields()
        out: list[tuple[tuple[str, str, float], str]] = []
        for function, qualified in cls._functions(tree).items():
            table = cls._bindings(function, tree)
            for site in ast.walk(function):
                if not isinstance(site, ast.Assert):
                    continue
                if not any(
                    isinstance(node, ast.Name) and node.id == bound
                    for node in ast.walk(site)
                ):
                    continue
                trees = cls._contributing(site, table)
                ink: list[ast.AST] = []
                boundary: list[ast.AST] = []
                unresolved: list[str] = []
                for sub in trees:
                    for attr in ast.walk(sub):
                        if not isinstance(attr, ast.Attribute):
                            continue
                        base = cls._root(attr.value)
                        readers = cls._readers_behind(base, table) if base else set()
                        if attr.attr in boundaries and "boundary" in readers:
                            boundary.append(attr)
                        elif attr.attr in ink_edges and "ink" in readers:
                            ink.append(attr)
                        elif attr.attr in ink_edges and base is None:
                            unresolved.append(ast.unparse(attr))
                parents: dict[int, ast.AST] = {}
                for sub in trees:
                    for node in ast.walk(sub):
                        for child in ast.iter_child_nodes(node):
                            parents[id(child)] = node
                marked = {id(node) for node in ink}
                unpaired = []
                for attr in ink:
                    current, paired = attr, False
                    while (current := parents.get(id(current))) is not None:
                        if isinstance(current, (ast.BinOp, ast.Compare, ast.Call)):
                            inside = sum(
                                1 for node in ast.walk(current) if id(node) in marked
                            )
                            if inside >= 2:
                                paired = True
                                break
                    if not paired:
                        unpaired.append(attr)
                key = (path, qualified, cls._multiple(site, bound))
                if unresolved:
                    verdict = f"UNCLASSIFIED {sorted(unresolved)}"
                elif boundary and not unpaired:
                    verdict = "boundary"
                elif ink and not unpaired:
                    verdict = "cancelling"
                elif not ink and not boundary:
                    verdict = "no_extent"
                else:
                    verdict = "ink_against_a_coordinate"
                out.append((key, verdict))
        return sorted(out, key=lambda entry: (entry[0][1], entry[0][2], entry[1]))

    def test_the_two_readings_cannot_name_the_same_attribute(self) -> None:
        """The walk tells them apart by field name, so the names are disjoint."""
        assert not self._ink_edges() & self._boundary_fields(), sorted(
            self._ink_edges() & self._boundary_fields()
        )

    @pytest.mark.parametrize("path", sorted(_MODULE_BOUNDS))
    def test_the_bound_this_walk_derives_from_still_exists(self, path: str) -> None:
        """A renamed bound empties the population silently — so it is asserted.

        The name has to be a module-level assignment of the module it is
        claimed for, and the walk has to find at least as many sites as were
        measured there.
        """
        bound = self._MODULE_BOUNDS[path]
        tree = self._tree(path)
        assigned = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        assert bound in assigned, (path, bound, "no module-level assignment")
        found = self._partition(path, tree)
        assert len(found) >= self._SITE_FLOOR[path], (path, len(found), found)

    @pytest.mark.parametrize("path", sorted(_MODULE_BOUNDS))
    def test_every_placed_edge_site_lands_in_exactly_one_class(
        self, path: str
    ) -> None:
        """The partition is total: nothing unclassified, nothing on the ink
        against a coordinate that has not declared itself."""
        found = self._partition(path)
        unclassified = [
            entry for entry in found if entry[1].startswith("UNCLASSIFIED")
        ]
        assert not unclassified, unclassified
        on_the_ink = {
            key for key, verdict in found if verdict == "ink_against_a_coordinate"
        }
        assert on_the_ink <= set(PLACED_EDGE_ON_THE_INK_BY_DECLARATION), sorted(
            on_the_ink - set(PLACED_EDGE_ON_THE_INK_BY_DECLARATION)
        )

    def test_every_declaration_is_a_site_that_is_really_on_the_ink(self) -> None:
        """ADR-0039/R3: the exemption is a claim and carries its own control.

        A declaration for a site that has been re-expressed, renamed or
        deleted is a dead exemption, and a dead exemption is how a real one
        gets added later without anyone reading it. Every entry has to name a
        site the walk still finds **and** still places on the ink.
        """
        found: list = []
        for path in self._MODULE_BOUNDS:
            found += self._partition(path)
        for key, reason in PLACED_EDGE_ON_THE_INK_BY_DECLARATION.items():
            verdicts = [verdict for site, verdict in found if site == key]
            assert verdicts, (key, "no such placed-edge site")
            assert set(verdicts) == {"ink_against_a_coordinate"}, (key, verdicts)
            assert "CARD-" in reason, (key, "a declaration names the card that owns it")

    def test_the_control_a_site_put_back_on_the_ink_is_caught(self) -> None:
        """The control that CAN fail (ADR-0039/R1), for the claim as stated.

        A module shaped exactly like the re-expressed sites, except that one
        of them reads the ink extent again: the walk must place it on the ink
        against a coordinate, and must place the boundary twin beside it in
        the ``boundary`` class. Caught with the mutation, missed without.
        """
        shape = """
EDGE_TOLERANCE_PX = 1.5

def test_re_expressed(page):
    drawing = drawing_of(page)
    boundary = frame_centre_of(page, drawing)
    assert abs(boundary.frame_left - 10) <= EDGE_TOLERANCE_PX

def test_put_back_on_the_ink(page):
    drawing = drawing_of(page)
    assert abs(drawing.left - 10) <= 2 * EDGE_TOLERANCE_PX
"""
        path = "tests/test_book_puzzle_frame.py"
        found = dict(self._partition(path, ast.parse(shape)))
        assert found[(path, "test_re_expressed", 1)] == "boundary", found
        assert (
            found[(path, "test_put_back_on_the_ink", 2)]
            == "ink_against_a_coordinate"
        ), found

    def test_one_key_really_does_hold_two_sites(self) -> None:
        """The collision is measured, so a dict-keyed regression cannot be quiet.

        If this ever reports one site per key, the walk may be keyed on a dict
        again without losing anything today — and would lose the next
        collision silently. See :meth:`_partition`.
        """
        found = self._partition("tests/property/test_book_pdf_geometry.py")
        keys = [key for key, _verdict in found]
        assert len(keys) > len(set(keys)), keys

    def test_no_bound_was_widened(self) -> None:
        """AC-4 / G-1, asserted rather than claimed.

        :data:`EDGE_TOLERANCE_PX` is unmoved, and the geometry module's
        ``HALF_PIXEL_MM`` carries the same **multiset** of site multiples it
        carried before this card: ``{2: x2, 3: x4, 4: x2}`` across eight
        constant-multiple sites, plus the definition and one bare read. There
        is no ``1 x`` multiple in that file and never was — an earlier
        wording of this card's AC-4 said "four site multiples unchanged at
        3/3/2/1", which was the multiple each of the four FAILING assertions
        carried and not the file's site count; re-derived with ``ast`` here so
        that the figure is the file's rather than a card's memory of it.
        """
        assert EDGE_TOLERANCE_PX == 1.5, EDGE_TOLERANCE_PX

        path = "tests/property/test_book_pdf_geometry.py"
        tree = self._tree(path)
        parents = {
            id(child): node
            for node in ast.walk(tree)
            for child in ast.iter_child_nodes(node)
        }
        multiples: dict[float, int] = {}
        bare = 0
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Name) and node.id == "HALF_PIXEL_MM"):
                continue
            parent = parents.get(id(node))
            if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Mult):
                other = parent.right if parent.left is node else parent.left
                if isinstance(other, ast.Constant):
                    multiples[other.value] = multiples.get(other.value, 0) + 1
                    continue
            bare += 1
        assert multiples == {2: 2, 3: 4, 4: 2}, multiples
        assert sum(multiples.values()) == 8, multiples
        assert bare == 2, bare
        assert 1 not in multiples, multiples


#: CARD-336 AC-3: the placed-edge sites of the two ``Touches`` modules that
#: stay on the **ink** extent against a coordinate, each with the measurement
#: that says why reading the boundary does not close it. Keyed on
#: ``(module, class-qualified test name, the multiple of the module's own
#: bound that site reads)`` — never a line number, which rots.
#:
#: Held to naming only real, still-on-the-ink sites by
#: :meth:`TestFrameCentre_EveryPlacedEdgeSiteIsClassified.test_every_declaration_is_a_site_that_is_really_on_the_ink`,
#: so this cannot rot into a blanket exemption (ADR-0039/R3).
#:
#: **The other declared residue: two re-expressed sites that CLEAR their bound
#: with 0.4 % of margin.** These two are deliberately **not** keys of the
#: mapping below — that mapping is held to sites still on the ink, and these
#: are closed and green. They are declared here anyway, for the same reason the
#: entry below is declared: a residue this card cannot improve is written down
#: with its figures, so that a corpus change, a poppler version or one
#: differently-landing trim reds them against an explanation instead of against
#: nothing. CARD-336's F-7, re-derived at the merge gate over the same 136
#: cases of
#: ``test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages``:
#:
#: ======================================  =======  ==========  =======
#: site, in that module and that node id   bound    vector      raster
#: ======================================  =======  ==========  =======
#: ``frame_left`` vs ``drawing_left_mm``   2 x      **1.992x**  1.983x
#: ``left_spare`` vs ``right_spare``       4 x      **3.984x**  3.965x
#: ======================================  =======  ==========  =======
#:
#: **Why the bound is the exact worst case — arithmetic, not luck.** The
#: reading is a rule's centre, and a rule of even inked width centres on a
#: half-integer, so it carries +/-0.5 px against the boundary. The millimetre
#: figure it is compared with is itself rounded to a device coordinate,
#: carrying a further +/-0.5 px. One device pixel is 2 x ``HALF_PIXEL_MM`` —
#: so 2 x **is** the derived worst case of a single-edge comparison, and 4 x is
#: twice it because the spare-margin site differences two such edges. 1.992x
#: is therefore *at* the derived bound, not inside it by accident.
#:
#: **And the bound was not widened to admit it** (G-1). What the INK reads on
#: the same corpus, for contrast: **6.992x** and 7.333x on the two single-edge
#: sites and **13.984x** on the spare site, all three RED in vector. The margin
#: is 0.4 %; the alternative was 3.5x the bound. Widening is what G-1 forbids,
#: and these figures are what make that refusal checkable rather than a claim.
PLACED_EDGE_ON_THE_INK_BY_DECLARATION: dict = {}
#: **EMPTIED by CARD-322 (owner ruling 2026-11-06, the placed-edge cells).** The
#: one entry this mapping held, the geometry module's
#: ``..._PortraitWithFixedTopEdgeForEveryExtent_two_up_pages`` site at its ONE
#: half-pixel bound, was declared on the ink because no single reading met the
#: bound in both media. The interior is one medium now, and that site reads the
#: frame BOUNDARY (``frame_centre_of``), measured at or under 0.46x the same
#: bound, with a 1 px control; it is no longer on the ink and so no longer a
#: declaration. The mapping stays (empty) because the guard tests below are
#: written against it and ``test_every_declaration_is_a_site_that_is_really_on_the_ink``
#: is what will refuse a future entry that names a site not on the ink.


# --------------------------------------------------------------------------
# CARD-218 fix round 1 — what the controls below are allowed to conclude
#
# The nine readers these controls are built on used to be written out here and
# again in ``tests/test_book_pdf_band.py``, on the house precedent for two
# places needing the same small check (CLAUDE.md, ``solver/propagate.py``'s
# ``mask_runs``). That precedent is for a check a module can cross-check
# natively; these nine read pytest's collection data, which neither file can
# check the other's reading of, and the comment that used to stand here said so
# as "the honest cost of that choice". CARD-219 paid the cost instead: they live
# in ``tests/helpers/shared_fixture_controls.py``, with the agreement guard the
# two copies lacked in ``tests/test_shared_fixture_controls.py``, and with both
# of the holes CARD-218's review left open closed there.
# --------------------------------------------------------------------------


#: The module fixture the controls at the end of this file are controls *on*.
SHARED_RENDER = "pages"


# --------------------------------------------------------------------------
# RETIRED by CARD-220 — `test_no_test_in_this_module_takes_a_fixture_through_
# getfixturevalue` stood here.
#
# SURVIVOR: tests/test_shared_fixture_controls.py
#   ::TestSharedControls_TheCopiesCannotComeBack
#   ::test_no_importer_reaches_for_a_fixture_at_run_time
#
# It calls the same bound, `shared_fixture_controls.
# refuse_unless_nothing_is_taken_dynamically`, over **every** importer of the
# shared home rather than once per file — "applied here rather than once per
# consumer file so that a module which starts importing the shared home is
# covered the day it does", as its own docstring puts it. This file is one of
# the three importers (measured: test_book_pdf_band.py,
# test_book_puzzle_frame.py, test_book_puzzle_page_vector.py), and the third
# never had a per-file copy — so the shared version already covered strictly
# more than the two copies did.
#
# MUTATION PROOF (CARD-220, out of tree, one file at a time so the survivor
# cannot be credited for the other's mutant):
#   * planted in THIS file only: this module's retired guard FAILED and the
#     survivor FAILED naming `test_book_pdf_band.py` line 1974; the other
#     file's per-file guard PASSED.
#   * planted in test_book_puzzle_frame.py only: the survivor FAILED naming
#     `test_book_puzzle_frame.py` line 3445.
#   * near-miss control: the word in a docstring/string only, planted in both
#     files, left all three GREEN — while a grep instrument would have fired
#     7 times on the MUTATED file. CARD-220 fix round 1 re-derived that figure
#     and states its domain, which the line above did not: the BASELINE is 5
#     occurrences per file at the fork point 4d164f62 (`grep -c` and
#     `grep -o | wc -l` agree, so the domain ambiguity does not explain it),
#     plus the 2 planted mentions. It is 2 per file today. The bound is an
#     `ast` reading of Attribute nodes, not a text match.
#
# Anyone adding a `request.getfixturevalue(...)` consumer to this file still
# reds immediately — in the shared home's test rather than here. Take the
# fixture as a parameter.
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# CARD-218's AC-5 — the control it was missing (cycle 1, F-001)
# --------------------------------------------------------------------------


class TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind:
    """AC-5, with a verifier that can fail on this module's **accumulators**.

    AC-5 says the fixture "must not keep more pages alive at once than the
    single-test path did", and named ``test_book_pdf_memory.py``'s peak
    assertions as its verifier. Those assertions instrument that module's own
    ``_live`` dict, so they cannot fail on bytes retained by this one: the
    conversion shipped **10 page bitmaps (252,450,000 B) held to the end of
    every session that collected this file**, and no guard on the board could
    see it: no module under ``tests/`` *asserts a shape* on this process's own
    memory (``tests/helpers/book_corpus.py``'s ``resident_bytes`` reads
    ``ru_maxrss``, but only as the quantity a child's cap is enforced
    against), and the one module that instruments page memory at all measures
    its own live-page dict (deliberately — it says so at its line 84). That
    sentence is held to a grep over every token it claims about —
    ``ru_maxrss|getrusage|RLIMIT_AS|peak_rss|max_rss|tracemalloc|resident_bytes``
    — which returns exactly ``tests/test_book_pdf_memory.py`` and
    ``tests/helpers/book_corpus.py``, **plus the two files this card converts,
    because this very paragraph names the tokens**. Re-run it with
    ``--include='*.py' tests/ | grep -vE 'puzzle_frame|pdf_band'`` to see the
    two that matter, or read the four and note that two of them are this
    sentence talking about itself. (Cycle 2, F-004: the sentence this replaces
    said "at all", and one grep refuted it. The orchestrator's pre-gate then
    found that recording the grep had changed what the grep returns — four
    files, not two — which is why the count is written out here rather than
    left to be rediscovered.)

    pytest keeps a test module in ``sys.modules``, so a module-level
    accumulator outlives the module-scoped fixture that filled it, which is
    exactly what :func:`pages` chose module over session scope to avoid.

    **Scope, stated as the measurement rather than as a universal.** This
    control's subject is the module-level accumulators
    :func:`_retained_bitmap_bytes` walks, along the edges that walk follows —
    **not everything this module leaves behind**, and CARD-219's fix round
    withdrew the sentence that said the two "happen to coincide" here. Two
    instruments agree, which is a smaller statement and the true one: an
    independent deep walk to depth 8 over this module at session end on
    2026-10-24 returns **320 B**, all of it :data:`_SHARED_DIGEST`, equal to
    what this instrument reports, and this file has **no** ``@lru_cache`` at
    all. Both walks have a blind side —
    ``shared_fixture_controls._step`` lists the edges this one declines, among
    them a class attribute of an imported class and a numpy view's uncropped
    base — so "equal to 320 B" means equal as far as two readings can see, not
    "nothing else is retained". Its twin
    ``tests/test_book_pdf_band.py`` is the file where the two figures diverge
    — 256 B of accumulator against 25,192,439 B found by the walk, the
    difference being two pre-existing ``@lru_cache(maxsize=None)`` stores that
    predate CARD-218 (25,192,183 B at the fork point ``c7cca514``) and are
    backlogged. The equality below is stated so that if this file ever grows
    such a channel, the claim does not silently widen to cover it.

    This control is **selection-independent** — unlike the render-count
    controls below it, it needs no denominator: whatever ran, an accumulator
    holding more than its digests is holding more than its digests. One node
    id of it is enough to red the regression.

    It is placed immediately *before* the module's mutation control rather
    than after it, because that control must be the last thing in the file
    that takes :func:`pages` (its own ordering guard says so), and nothing
    after this point can add to an accumulator: every fixture that fills one
    has run.
    """

    def test_the_page_bitmap_unit_is_this_modules_own_page(self, pages) -> None:
        """The unit the bound below is stated in is this book's real page.

        ``PAGE_BITMAP_BYTES`` is ``test_book_pdf_memory.py``'s definition of a
        page — 2550 x 3300 RGB, 25,245,000 B — and the unit cycle 1 reported
        the retention in. The pages this module draws are measured against it
        here instead of being assumed to match, so a change of trim or
        resolution fails this rather than quietly making the bound mean
        something else. Two instruments, one figure: the project's constant
        and the geometry of a page as drawn.
        """
        measured = {_bitmap_bytes(page) for page in pages}
        assert measured == {PAGE_BITMAP_BYTES}, (
            "this module's pages are no longer the page the retention bound "
            f"is stated in: measured {sorted(measured)} B against "
            f"test_book_pdf_memory.PAGE_BITMAP_BYTES = {PAGE_BITMAP_BYTES} B. "
            "Re-derive the bound below from the page this module now draws."
        )

    def test_no_module_level_accumulator_retains_a_page_bitmap(self, pages) -> None:
        """The accumulators hold one 32-byte digest per page they signed — exactly.

        The node id is unchanged on purpose: the card's mutant tables (M7, M8)
        and three sets of review notes are keyed to it, and the name is still
        true — it is now the weaker half of what is asserted.

        An **equality**, not a bound, and that is the correction cycle 2 asked
        for (F-001). ``total < one page bitmap`` was a threshold its twin in
        ``tests/test_book_pdf_band.py`` sat 0.21 % under once everything that
        module retains is counted, and it invited a comparison against a
        quantity the instrument above cannot see. The equality invites none:
        the accumulators hold ``32 B x pages`` or they are wrong, and they go
        red the instant any byte comes back — a digest store turned into
        ``page.tobytes()``, a second accumulator holding a page, a fixture
        that never signed, a book of a different length.

        Both sides are derived. ``32`` is sha256's digest size written out by
        hand here rather than read back off :func:`_page_digest`, so this is a
        second statement of the digest's width and not that function run
        twice; the page count is the book the fixture actually handed out. The
        page-bitmap unit still appears, in the message and in the test above,
        because the figure a reader needs when this reds is how many pages the
        accumulator is now worth.

        **CARD-219 widened the walk under it.** :func:`_retained_bitmap_bytes`
        asks the garbage collector what every value refers to, fenced off from
        modules, functions and methods, so the three channels this module's old
        instrument could only declare — numpy arrays, ``Test`` class
        attributes, deep nesting — and the three CARD-219's cycle 1 found still
        open — a deque, an instance's own attributes, a cache nothing named —
        are inside the equality above rather than beside it. It
        is a **bounded** reading all the same: ``_step``'s own docstring is the
        authority on which edges it follows and which it declines, and a page
        parked behind a declined edge does not red this. The second assertion
        is the exemption's control from the other side: this file declares
        **no** ``@lru_cache`` at all, so its allowance is empty, and the day it
        grows one the allowance has to be granted deliberately instead of
        appearing.
        """
        digest_bytes = 32
        unit = _bitmap_bytes(pages[0])
        retained = _retained_bitmap_bytes(globals())
        total = sum(retained.by_name.values())
        expected = digest_bytes * len(pages)
        detail = (
            ", ".join(
                f"{name} {held:,} B ({held / unit:.4f} pages)"
                for name, held in sorted(
                    retained.by_name.items(), key=lambda row: -row[1]
                )
            )
            or "no module-level name holds any measurable bytes"
        )
        assert total == expected, (
            f"this module's module-level accumulators will leave {total:,} B "
            f"({total / unit:.4f} page bitmaps) alive after its fixtures are "
            f"finalised, rather than the {expected:,} B of one "
            f"{digest_bytes}-byte digest per page of the {len(pages)}-page "
            f"book they signed: {detail}. pytest keeps a test module in "
            "sys.modules for the rest of the session, so a module-level "
            "accumulator outlives the module-scoped fixture that filled it — "
            "the retention module scope was chosen to avoid (CARD-218 AC-5, "
            "F-001). Store a 32-byte `_page_digest(page)`, not "
            "`page.tobytes()`. The walk now follows numpy arrays, deep "
            "containers, Test-class attributes and `@lru_cache` stores, so "
            "this no longer excuses any of them."
        )
        # One conjunct, because the other could not fail: `by_cache` is built
        # from `_caches_of` on this namespace, so an empty `_lru_cache_names`
        # makes `retained.by_cache == {}` true by construction. The name set
        # is the failable half (CARD-219 cycle 1, F-005 — the same shape
        # CARD-218's cycle 2 deleted, shipped again beside its twin).
        assert _lru_cache_names(globals()) == set(), (
            "this module has grown an `@lru_cache`, and a cache store is the "
            "one channel the equality above exempts: "
            f"{sorted(_lru_cache_names(globals()))} declared, "
            f"{retained.by_cache} holding measurable bytes. Its twin "
            "`tests/test_book_pdf_band.py` has two such caches holding "
            "25,192,183 B and names them as a deliberate allowance; this file "
            "had none, so the allowance here is empty and a new cache must be "
            "admitted on purpose rather than by arriving."
        )


# --------------------------------------------------------------------------
# CARD-218 — the control on the shared render
# --------------------------------------------------------------------------


class TestPuzzleFrame_TheSharedInteriorIsNotMutated:
    """CARD-218's AC-4, for the one book this module now draws once.

    Sharing a render is only sound while every reader is a reader. Pillow
    images are mutable and this file compares pages by their ink, so a test
    that drew on a shared page — a debug marker, a crop written back, a
    ``paste`` — would silently change what every later test measures, and the
    failure would land on the later test rather than on the one that caused
    it. This class is where it lands instead.

    It runs last on purpose, and since cycle 1's F-006 it *says so to pytest*
    rather than to the reader: both tests below open by asserting, off this
    run's own collected order, that no other test takes :func:`pages` after
    them.
    """

    def test_the_shared_pages_are_handed_out_as_they_were_drawn(
        self, request, pages
    ) -> None:
        """Every page is byte for byte what the fixture drew.

        The digest is taken *inside* the fixture, before any test sees the
        pages, and this compares the pages as they stand now against it — so
        the comparison is the drawn book against the handed-out book, not the
        handed-out book against itself.

        The two guards first: this control's verdict covers exactly the tests
        that ran, so it refuses a selection that leaves a consumer out, and
        refuses an order that puts one after it (F-002, F-006).
        """
        _refuse_unless_every_consumer_is_collected(request, globals(), SHARED_RENDER)
        _refuse_unless_nothing_takes_it_later(
            request, SHARED_RENDER, siblings_excepted=True
        )
        assert len(_SHARED_DIGEST) == INTERIOR_PAGES, (
            "the shared-render digest was not taken: "
            f"{len(_SHARED_DIGEST)} pages recorded, {INTERIOR_PAGES} drawn"
        )
        moved = [
            number
            for number, (page, drawn) in enumerate(zip(pages, _SHARED_DIGEST), start=1)
            if _page_digest(page) != drawn
        ]
        assert not moved, (
            "a test in this module drew on the shared interior rather than on "
            f"a copy of it: interior page(s) {moved} no longer match the bytes "
            "the module fixture drew. Take `page.copy()` in the test that "
            "needs to draw, or give that test a render of its own."
        )

    def test_one_render_served_the_whole_module(self, request, pages) -> None:
        """The saving itself, asserted rather than assumed.

        ``_SHARED_DIGEST`` is appended to once per execution of the module
        fixture, so a digest holding exactly one book's pages is the statement
        that the book was drawn once for the module. Widen the fixture's scope
        back to ``function``, or narrow it to a class, **and run this whole
        file**, and this holds more than one book's worth of digests and goes
        red.

        The scope of that claim, corrected in fix round 1 (F-002): it is a
        statement about a run that collected every consumer, and only about
        such a run. The counter cannot distinguish one render from one render
        per test when one test took the fixture, so the first guard refuses
        that selection rather than returning the silent green cycle 1 measured
        under ``-k one_render``. The second guard is why "one book's worth" can
        be read as "the last word on the module": nothing takes the pages
        after this.

        The assertion below carried a third conjunct, ``== INTERIOR_PAGES``,
        until fix round 2 dropped it (cycle 2, F-005). It was unfailable:
        :func:`_book_pages` already asserts ``len(pages) == INTERIOR_PAGES``
        before the fixture returns, so nothing could red it — and had anything
        been able to, this message would have diagnosed a wrong page count as
        a scope regression. :meth:`test_the_shared_pages_are_handed_out_as_they_were_drawn`
        holds the digest length to ``INTERIOR_PAGES`` in its own right, so
        nothing is given up. Three live assertions remain in this control —
        the two guard calls and this equality — and none is unfailable.
        """
        _refuse_unless_every_consumer_is_collected(request, globals(), SHARED_RENDER)
        _refuse_unless_nothing_takes_it_later(
            request, SHARED_RENDER, siblings_excepted=True
        )
        assert len(_SHARED_DIGEST) == len(pages), (
            f"{len(_SHARED_DIGEST)} page digests were recorded for a book of "
            f"{len(pages)} pages, across a run that collected every consumer "
            "of the module fixture: the book was drawn more than once, so the "
            "fixture is no longer module-scoped"
        )


# The owner's 2026-11-09 polish took the frame off and lets every answer pack;
# this module measures what it measured before (tests/helpers/legacy_book_layout.py).
from tests.helpers.legacy_book_layout import module_fixture as _legacy_module_fixture  # noqa: E402

_legacy_book_layout = _legacy_module_fixture()
