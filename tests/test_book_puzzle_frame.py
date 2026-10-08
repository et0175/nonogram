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
the drawing is centred across the usable width and hangs one band below the top
margin. Nothing in :func:`_expected_box` reads ``compute_layout``, so a frame
in the right place is two answers agreeing rather than one answer restated.

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
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import BookPDFGenerator, _stroke_drawing
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    DEFAULT_PAGE_SPEC,
    DPI,
    CellCapPolicy,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_layout,
    compute_pair_layout,
)
from nonogram.export.png import BACKGROUND, render_image
from tests.helpers.page_ink import drawing_of
from tests.helpers.two_up_ink import drawings_of

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in inches, written out rather than imported
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = TOP_MM = BOTTOM_MM = 0.375 * 25.4

#: A 6 x 9 in trim, the other one the owner prints — CARD-144 asks the frame to
#: sit correctly on any stored trim, not only on Book 1's.
SIX_BY_NINE_MM = (6 * 25.4, 9 * 25.4)

#: The title band above each puzzle (TERM-028), NFR-008's standard cell and
#: ADR-0037/R2's thinnest thin rule.
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
MIN_THIN_RULE_MM = 0.25

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = DPI / 25.4

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
    **overrides: object,
) -> PageSpec:
    """A book page, stated from CON-018 rather than built by the panel."""
    return PageSpec(
        width_mm=width_mm,
        height_mm=height_mm,
        top_mm=TOP_MM,
        bottom_mm=BOTTOM_MM,
        gutter_mm=GUTTER_MM,
        outside_mm=OUTSIDE_MM,
        band_mm=BAND_MM,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=MIN_THIN_RULE_MM,
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

    Worked out from the sheet in millimetres: the drawing is centred across the
    usable width (FR-032) and its top edge is the top margin plus the band, on
    every page and parity. That rectangle **is** the frame: its left and top
    are the outer edges of the two clue gutters, its right and bottom the
    grid's own outer border.
    """
    drawing_columns = row_depth + columns
    drawing_rows = column_depth + rows
    cell = _expected_cell_mm(spec, drawing_columns, drawing_rows)
    usable_width = spec.width_mm - spec.gutter_mm - spec.outside_mm
    left_margin = spec.outside_mm if spec.parity is PageParity.EVEN else spec.gutter_mm
    left = left_margin + (usable_width - drawing_columns * cell) / 2
    top = spec.top_mm + spec.band_mm
    return (
        left * PX_PER_MM,
        top * PX_PER_MM,
        (left + drawing_columns * cell) * PX_PER_MM,
        (top + drawing_rows * cell) * PX_PER_MM,
    )


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
        for page_number in (1, 2, 7, 8):
            spec = book_page_spec(None, page_number)
            assert spec.frame is None, "the panel states nothing about the frame"
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

    def test_the_thirty_by_thirty_with_nine_deep_clues_still_prints_at_4_97_mm(self) -> None:
        spec = _spec()
        layout = compute_layout(*_clue_sets(30, 30, 9, 9), spec)

        assert layout.frame is not None
        assert layout.page.cell_mm == pytest.approx(4.97, abs=0.005)

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
        assert pair.upper.frame.top == single.frame.top, "the fixed top row (FR-032)"
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
PAIR_HEIGHT_MM = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM

#: The pair these criteria are read on, and the puzzle that prints alone after
#: it so that a two-up slot and a single page can be compared **on one book**.
#: All three are Easy, so the interior is one level: guide, the "Easy" divider,
#: the two-up page, the single page, SOLUTIONS, three answer pages (CARD-198:
#: one per puzzle, where this book took one packed page before that card).
UPPER_PUZZLE = dict(columns=10, rows=10, row_depth=2, column_depth=2)
LOWER_PUZZLE = dict(columns=12, rows=12, row_depth=3, column_depth=3)
SINGLE_PUZZLE = dict(columns=20, rows=20, row_depth=8, column_depth=8)

#: Which interior page is which, once the walk above has run. Asserted rather
#: than trusted by :func:`_book_pages`.
TWO_UP_PAGE = 3
SINGLE_PAGE = 4
INTERIOR_PAGES = 8


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
    pages = BookPDFGenerator(_book()).interior_pages(
        [
            _book_puzzle(**UPPER_PUZZLE, puzzle_id="one"),
            _book_puzzle(**LOWER_PUZZLE, puzzle_id="two"),
            _book_puzzle(**SINGLE_PUZZLE, puzzle_id="three"),
        ]
    )
    assert len(pages) == INTERIOR_PAGES, f"the book printed {len(pages)} pages"
    assert len(drawings_of(pages[TWO_UP_PAGE - 1])) == 2, "the pair really shares a page"
    assert len(drawings_of(pages[SINGLE_PAGE - 1])) == 1, "and the 20x20 prints alone"
    return pages


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
    """FR-040's shared cell for one pair on one Book 1 page, in millimetres."""
    return min(
        STANDARD_CELL_MM,
        USABLE_WIDTH_MM / max(_across(upper), _across(lower)),
        PAIR_HEIGHT_MM / (_down(upper) + _down(lower)),
    )


def _expected_pair_boxes(
    upper: dict, lower: dict, parity: PageParity = PageParity.ODD
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

    Each drawing is centred across the usable width on the **shared** cell; the
    upper one's top edge is the fixed row every single puzzle page uses (top
    margin plus band, FR-032/EC-022) and the lower one's bottom edge is the
    bottom margin, its own band in the 12 mm above it — which is the placement
    ``tests/test_book_pdf_two_up.py`` states AC-251's lower band from.

    That rectangle **is** the frame: its left and top are the outer edges of
    the two clue gutters and its right and bottom the grid's own outer border.
    """
    cell = _shared_cell_mm(upper, lower)
    left_margin = OUTSIDE_MM if parity is PageParity.EVEN else GUTTER_MM

    def box(puzzle: dict, top_mm: float) -> tuple[float, float, float, float]:
        left_mm = left_margin + (USABLE_WIDTH_MM - _across(puzzle) * cell) / 2
        return (
            left_mm * PX_PER_MM,
            top_mm * PX_PER_MM,
            (left_mm + _across(puzzle) * cell) * PX_PER_MM,
            (top_mm + _down(puzzle) * cell) * PX_PER_MM,
        )

    return (
        box(upper, TOP_MM + BAND_MM),
        box(lower, BOOK1_HEIGHT_MM - BOTTOM_MM - _down(lower) * cell),
    )


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
_RULE_WINDOW_PX = 20

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

    @pytest.fixture(scope="class")
    @classmethod
    def pages(cls) -> list[Image.Image]:
        return _book_pages()

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

    @pytest.fixture(scope="class")
    @classmethod
    def pages(cls) -> list[Image.Image]:
        return _book_pages()

    @staticmethod
    def _weights(dark: np.ndarray, drawing) -> tuple[int, int]:
        """``(thin, thick)`` as this page actually strokes them, off its own ink.

        Measured on a pixel row half a cell below the grid's top border and
        **bounded to the grid itself**, where the only ink is the grid's
        verticals: every fifth of them and the two borders are heavy, the rest
        thin. The bound matters — a row half a cell into the grid crosses that
        row's clue digits out in the gutter, and a digit's stem is its own
        number of pixels wide. Nothing here is imported from the layout; the
        two weights are counted.
        """
        row = drawing.grid_top + round(drawing.cell / 2)
        runs = _runs_across(
            dark, row, drawing.grid_left, drawing.grid_right + _RULE_WINDOW_PX
        )
        widths = {len(run) for run in runs}
        assert len(widths) == 2, f"a row through the grid shows weights {sorted(widths)}"
        return min(widths), max(widths)

    def test_the_two_up_page_strokes_exactly_two_weights(self, pages) -> None:
        dark = _dark(pages[TWO_UP_PAGE - 1])

        for drawing in drawings_of(pages[TWO_UP_PAGE - 1]):
            thin, thick = self._weights(dark, drawing)
            assert thick == 2 * thin, f"the heavy rule is {thick} to the thin's {thin}"
            assert thin / PX_PER_MM >= MIN_THIN_RULE_MM

    def test_every_frame_side_is_the_heavy_rule_and_no_new_weight(self, pages) -> None:
        page = pages[TWO_UP_PAGE - 1]
        dark = _dark(page)
        drawings = drawings_of(page)
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for drawing, box in zip(drawings, boxes):
            left, top, right, bottom = _pixel_box(box)
            _thin, thick = self._weights(dark, drawing)
            assert bottom - top > 4 * thick, "these crops really are inside the drawing"
            # A row inside the column-clue band, clear of the frame's own top
            # side: the first and last runs of ink across the slot's span are
            # the frame's two vertical sides.
            columns = _runs_across(
                dark, top + 2 * thick, left - _RULE_WINDOW_PX, right + _RULE_WINDOW_PX
            )
            assert len(columns) >= 3
            assert abs(columns[0][0] - left) <= thick, (
                "the leftmost rule in this band is not on the drawing's own left "
                f"edge ({columns[0][0]} against {left}) — there is no frame here, "
                "only the grid's border a whole clue gutter further in"
            )
            assert len(columns[0]) == thick, "the frame's left side is not the heavy rule"
            assert len(columns[-1]) == thick, "nor is its right side"
            # A column inside the row-clue band, clear of the frame's left side
            # and bounded to this slot's own rows — the other slot's frame is
            # in the same pixel columns further down the sheet.
            rows = _runs_down(
                dark, left + 2 * thick, top - _RULE_WINDOW_PX, bottom + _RULE_WINDOW_PX
            )
            assert len(rows) >= 2
            assert abs(rows[0][0] - top) <= thick, (
                "the topmost rule in this gutter is not on the drawing's own top "
                f"edge ({rows[0][0]} against {top})"
            )
            assert len(rows[0]) == thick, "the frame's top side is not the heavy rule"
            assert len(rows[-1]) == thick, "nor is its bottom side"

    def test_the_two_up_page_introduces_no_weight_the_single_page_lacks(
        self, pages
    ) -> None:
        """The pair and the single page of the same book stroke the same two rules.

        Not the same *pixel counts* — the two pages print different cells, and
        ADR-0037/R2's rules scale with the cell — but the same shape of answer:
        two weights, the heavy exactly twice the thin. A third weight invented
        for the pair shows up as a third run length.
        """
        two_up, single = pages[TWO_UP_PAGE - 1], pages[SINGLE_PAGE - 1]
        single_dark, two_up_dark = _dark(single), _dark(two_up)
        thin, thick = self._weights(single_dark, drawing_of(single))
        assert thick == 2 * thin, "the single page itself strokes two weights"

        for drawing in drawings_of(two_up):
            paired_thin, paired_thick = self._weights(two_up_dark, drawing)
            assert paired_thick == 2 * paired_thin, (
                f"a slot strokes {paired_thick} to the thin's {paired_thin}"
            )
        # The negative control: the two pages print different cells, so this
        # comparison is of the *rule*, not of two pages that happen to agree.
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

    @pytest.fixture(scope="class")
    @classmethod
    def pages(cls) -> list[Image.Image]:
        return _book_pages()

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

    @pytest.fixture(scope="class")
    @classmethod
    def pages(cls) -> list[Image.Image]:
        return _book_pages()

    def test_the_pair_still_prints_at_the_shared_cell_fr_040_measures(
        self, pages
    ) -> None:
        """CARD-127's figure: both slots on one cell, and it is FR-040's own."""
        expected = _shared_cell_mm(UPPER_PUZZLE, LOWER_PUZZLE)
        assert expected == pytest.approx(STANDARD_CELL_MM), "this pair fits the cap"

        for drawing in drawings_of(pages[TWO_UP_PAGE - 1]):
            assert drawing.cell / PX_PER_MM == pytest.approx(expected, abs=0.05)

    def test_the_upper_slot_still_starts_on_the_fixed_top_row(self, pages) -> None:
        """CARD-118's EC-022: top margin plus band, on a pair as on a single page."""
        upper, lower = drawings_of(pages[TWO_UP_PAGE - 1])
        alone = drawing_of(pages[SINGLE_PAGE - 1])

        assert upper.top == alone.top, "the framed pair moved its upper drawing"
        assert abs(upper.top / PX_PER_MM - (TOP_MM + BAND_MM)) <= 0.5
        assert lower.top > upper.top, "the lower slot is a second drawing below it"

    def test_both_slots_sit_where_con_018s_millimetres_put_them(self, pages) -> None:
        """Origin and extent, against the arithmetic — not against the layout."""
        drawings = drawings_of(pages[TWO_UP_PAGE - 1])
        boxes = _expected_pair_boxes(UPPER_PUZZLE, LOWER_PUZZLE)

        for drawing, puzzle, (left, top, right, bottom) in zip(
            drawings, (UPPER_PUZZLE, LOWER_PUZZLE), boxes
        ):
            assert abs(drawing.left - left) <= EDGE_TOLERANCE_PX
            assert abs(drawing.top - top) <= EDGE_TOLERANCE_PX
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
    cases = 0
    for width_mm, height_mm in trims:
        for parity in PageParity:
            for _ in range(40):
                columns = rng.randint(10, 30)
                rows = rng.randint(10, 30)
                row_depth = rng.randint(1, (columns + 1) // 2)
                column_depth = rng.randint(1, (rows + 1) // 2)
                spec = _spec(width_mm=width_mm, height_mm=height_mm, parity=parity)
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
    for field in dataclasses.fields(PageSpec):
        ours, theirs = getattr(mine, field.name), getattr(panels, field.name)
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
