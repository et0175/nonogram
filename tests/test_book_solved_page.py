"""CARD-197 — the full-page solved layout: clues top+left, light-gray
gridlines between filled cells (owner's Google Doc "Nonograms - Print
layout1", 2026-10-07).

    AC-1  TestBookSolvedPage_CluesMatchTheGridAndTheUnsolvedPlacement
    AC-2  TestBookSolvedPage_GrayGridlinesBetweenFilledCells
    AC-3  TestBookSolvedPage_GrayOnlyBetweenFilledCells
    AC-4  TestBookSolvedPage_TitleBandMatchesBandIdentity
    AC-5  TestBookSolvedPage_CaptionReadsThePictureName
    AC-6  TestBookSolvedPage_CaptionOmittedWhenNoSlack
    AC-7  TestBookSolvedPage_TextHoldsTheTenPointFloor
    AC-8  TestBookSolvedPage_NoColour
    AC-9  TestBookSolvedPage_SameGeometryAsTheUnsolvedPage

CARD-203 — the caption right-aligns with the grid and sits a fixed gap above
its old centred-in-the-slack position (owner's Google Doc "Nonograms - Print
layout1", 2026-10-08, item 5). Its own AC numbering is independent of the
table above (CARD-197's own ACs, unrenumbered):

    AC-1  TestBookSolvedPage_CaptionRightAlignedWithTheGrid
    AC-2  TestBookSolvedPage_CaptionMovedCloserToTheDrawing
    AC-3  TestBookSolvedPage_CaptionMovedCloserToTheDrawing (same class)
    AC-4  TestBookSolvedPage_CaptionOmittedWhenNoSlack::test_the_narrow_gap_only_boundary_is_also_omitted
    AC-5  TestBookSolvedPage_CaptionOmittedWhenNoSlack (existing, unedited)
    AC-6  TestBookSolvedPage_SameGeometryAsTheUnsolvedPage,
          TestBookSolvedPage_GrayGridlinesBetweenFilledCells,
          TestBookSolvedPage_TitleBandMatchesBandIdentity (existing, unedited)

``BookPDFGenerator.solved_puzzle_page`` is a rendering primitive only — no
caller exists yet (CARD-198's job). Every test below builds a
``BookPDFGenerator()`` with no stored book, which is CON-018's Book 1 profile
(the default), and calls the new method directly.

**Grids, chosen deterministically, not generated.**

``_RUN_GRID`` (4x4) is built by hand to carry, in one small grid, every
boundary kind AC-2/AC-3 need: two within-row adjacent-filled pairs (gray), a
filled-then-empty pair (black), an empty-then-empty pair (black), two
vertical (row-to-row) adjacent-filled pairs (gray) and every outer border
(always black). Worked out once here and cross-checked by the probe script
kept in this module's history, not re-derived by a second run of the method
under test.

``_checkerboard`` (``grid[r][c] = (r + c) % 2 == 0``) never puts two
grid-adjacent cells both filled — every neighbour differs in parity — so it
carries no gray mark at all. That makes it the right grid for AC-9 (geometry
only, nothing about the new ink) and, at a shape that empties the cell's
slack (23 rows x 10 columns on Book 1 — found by sweeping every 10..30 shape
and keeping the one with the least headroom; recorded here as a constant
rather than re-swept on every run), for AC-6.

Pixel comparisons are exact (``np.array_equal``): Pillow's rendering is
deterministic for the same font, size and coordinates, and every expected
difference here is driven by a one-character text change or a filled/empty
flip, not a tolerance question.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram import clues
from nonogram.admin.book_pdf_generator import (
    ANSWER_TEXT_FONT_MM,
    POINTS_PER_INCH,
    BookPDFGenerator,
    _band_font,
    _SOLVED_GRID_GRAY,
    band_identity,
    type_px,
)
from nonogram.export import ExportPayload
from nonogram.export.layout import ANSWER_TILE_GAP_MM, compute_layout
from nonogram.export.pdf import render_pages
from nonogram.export.png import BACKGROUND, INK

from tests.helpers.page_ink import drawing_of

# --------------------------------------------------------------------------
# Grids and payload building
# --------------------------------------------------------------------------

#: AC-2/AC-3's grid, worked out by hand (see module docstring).
#:
#: Row 0: True,  True,  True,  False
#: Row 1: True,  False, True,  False
#: Row 2: False, False, True,  True
#: Row 3: False, False, False, False
_RUN_GRID = [
    [True, True, True, False],
    [True, False, True, False],
    [False, False, True, True],
    [False, False, False, False],
]

#: The 23x10 checkerboard's shape: the least vertical slack found sweeping
#: every 10..30 row/column combination of a checkerboard grid against the
#: Book 1 profile (AC-6) — ``0`` px, i.e. page-fit-bound.
_NO_SLACK_SHAPE = (23, 10)

#: A cap-bound checkerboard, used by AC-5 and AC-9 (plenty of slack below the
#: drawing on Book 1, and — being a checkerboard — no gray mark to confound
#: either comparison).
_CAP_BOUND_SHAPE = (10, 10)

#: CARD-203 AC-4's boundary shape: the one 29x23 checkerboard found sweeping
#: every 10..30 row/column combination of a checkerboard grid against the
#: Book 1 profile whose slack (58 px) sits inside
#: ``[line_height, gap_px + line_height)`` = ``[49, 73)`` at this page's own
#: DPI — enough room for the caption's own line under the OLD guard
#: (``slack >= line_height``), not enough once the new gap is added
#: (``slack >= gap_px + line_height``). The same kind of hand-recorded sweep
#: result as ``_NO_SLACK_SHAPE`` above, not re-swept on every run.
_NARROW_GAP_SHAPE = (29, 23)


def _checkerboard(rows: int, columns: int) -> list[list[bool]]:
    """A grid where no two grid-adjacent cells are ever both filled."""
    return [[(r + c) % 2 == 0 for c in range(columns)] for r in range(rows)]


def _clue_sets(grid: list[list[bool]]) -> Tuple[tuple, tuple]:
    """``grid``'s row and column clues, by ``clues.encode_line`` (AC-1's own
    ground truth), not by any helper this module or the code under test
    shares."""
    row_clues = tuple(clues.encode_line(row) for row in grid)
    column_clues = tuple(clues.encode_line(column) for column in zip(*grid))
    return row_clues, column_clues


def _payload(
    grid: list[list[bool]],
    *,
    name: Optional[str] = None,
    difficulty: object = None,
) -> ExportPayload:
    row_clues, column_clues = _clue_sets(grid)
    return ExportPayload(
        grid=grid,
        row_clues=row_clues,
        column_clues=column_clues,
        seed=0,
        mode="random",
        width=len(grid[0]),
        height=len(grid),
        name=name,
        difficulty=difficulty,
    )


def _array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB"))


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestBookSolvedPage_CluesMatchTheGridAndTheUnsolvedPlacement:
    """AC-1 — the clues are the grid's own RLE, placed where an unsolved page
    would place them.

    (A prior version of this class also asserted
    ``payload.row_clues == tuple(clues.encode_line(r) for r in _RUN_GRID)``
    directly — that assertion re-derived ``_payload()``'s own
    ``_clue_sets`` formula against itself without ever calling
    ``solved_puzzle_page``, so it passed regardless of the method's
    behaviour. Removed as tautological (forge:review F-001); the test below
    is the substantive AC-1 check — it renders the page and compares the
    rendered clue gutters pixel-for-pixel against an independently rendered
    unsolved page built from the same grid-derived clues.)
    """

    def test_clue_gutters_match_the_unsolved_pages_pixel_for_pixel(self):
        payload = _payload(_RUN_GRID, name="Picture", difficulty="Hard")
        generator = BookPDFGenerator()
        page_number = 2
        puzzle_number = 5

        solved = generator.solved_puzzle_page(payload, puzzle_number, page_number)

        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        unsolved_payload = ExportPayload(
            grid=payload.grid,
            row_clues=payload.row_clues,
            column_clues=payload.column_clues,
            seed=0,
            mode="random",
            width=payload.width,
            height=payload.height,
            name=None,
            difficulty=band_identity(puzzle_number, payload.difficulty),
        )
        blank, _ = render_pages(
            unsolved_payload, page_spec=generator.page_spec(page_number)
        )

        solved_arr, blank_arr = _array(solved), _array(blank)
        placement = layout.page
        assert placement is not None

        row_gutter_box = (
            placement.drawing_left,
            layout.grid_top,
            layout.grid_left,
            layout.grid_bottom,
        )
        column_gutter_box = (
            layout.grid_left,
            placement.drawing_top,
            layout.grid_right,
            layout.grid_top,
        )
        for box in (row_gutter_box, column_gutter_box):
            left, top, right, bottom = box
            np.testing.assert_array_equal(
                solved_arr[top:bottom, left:right],
                blank_arr[top:bottom, left:right],
            )


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestBookSolvedPage_GrayGridlinesBetweenFilledCells:
    """AC-2 — a run of 2+ adjacent filled cells: black fill, gray boundary."""

    @staticmethod
    def _render():
        payload = _payload(_RUN_GRID, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        solved = generator.solved_puzzle_page(payload, 1, page_number)
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        xs = [line.position for line in layout.vertical_lines]
        ys = [line.position for line in layout.horizontal_lines]
        return _array(solved), xs, ys

    def test_filled_cell_interiors_are_pure_black(self):
        arr, xs, ys = self._render()
        # (0, 0), (0, 1) and (0, 2) are filled in _RUN_GRID.
        for row, col in ((0, 0), (0, 1), (0, 2)):
            cx = (xs[col] + xs[col + 1]) // 2
            cy = (ys[row] + ys[row + 1]) // 2
            assert tuple(arr[cy, cx]) == INK

    def test_the_boundary_between_two_filled_cells_is_the_gray_tone(self):
        arr, xs, ys = self._render()
        # Within-row: row 0, columns 0-1 and 1-2 are both filled.
        for col_boundary in (1, 2):
            mid_y = (ys[0] + ys[1]) // 2
            assert tuple(arr[mid_y, xs[col_boundary]]) == _SOLVED_GRID_GRAY
        # Row-to-row: row 0-1 at column 0, and row 0-1 at column 2.
        for col in (0, 2):
            mid_x = (xs[col] + xs[col + 1]) // 2
            assert tuple(arr[ys[1], mid_x]) == _SOLVED_GRID_GRAY

    def test_the_gray_tone_is_distinguishable_from_black_and_white(self):
        assert _SOLVED_GRID_GRAY != INK
        assert _SOLVED_GRID_GRAY != BACKGROUND
        v = _SOLVED_GRID_GRAY[0]
        assert abs(v - 0) != abs(v - 255)  # not a coincidental midpoint match
        assert v not in (0, 255)


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookSolvedPage_GrayOnlyBetweenFilledCells:
    """AC-3 — gray appears on no other line: not filled-empty, not
    empty-empty, not an outer border."""

    @staticmethod
    def _render():
        payload = _payload(_RUN_GRID, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        solved = generator.solved_puzzle_page(payload, 1, page_number)
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        xs = [line.position for line in layout.vertical_lines]
        ys = [line.position for line in layout.horizontal_lines]
        return _array(solved), xs, ys, layout

    def test_a_filled_to_empty_boundary_is_black(self):
        arr, xs, ys, _ = self._render()
        # Row 0, columns 2-3: filled, then empty.
        mid_y = (ys[0] + ys[1]) // 2
        assert tuple(arr[mid_y, xs[3]]) == INK

    def test_an_empty_to_empty_boundary_is_black(self):
        arr, xs, ys, _ = self._render()
        # Row 2, columns 0-1: both empty.
        mid_y = (ys[2] + ys[3]) // 2
        assert tuple(arr[mid_y, xs[1]]) == INK

    def test_the_outer_border_is_black(self):
        arr, xs, ys, _ = self._render()
        mid_y = (ys[0] + ys[1]) // 2
        assert tuple(arr[mid_y, xs[0]]) == INK  # left border
        mid_x = (xs[0] + xs[1]) // 2
        assert tuple(arr[ys[0], mid_x]) == INK  # top border

    def test_every_interior_boundary_matches_its_both_filled_verdict(self):
        """Every interior boundary of _RUN_GRID, checked against the one rule
        AC-2/AC-3 together state: gray iff both of its two cells are filled,
        black otherwise."""
        arr, xs, ys, layout = self._render()
        grid = _RUN_GRID
        mismatches = []
        for c in range(1, layout.columns):
            for r in range(layout.rows):
                mid_y = (ys[r] + ys[r + 1]) // 2
                expected = _SOLVED_GRID_GRAY if (grid[r][c - 1] and grid[r][c]) else INK
                actual = tuple(arr[mid_y, xs[c]])
                if actual != expected:
                    mismatches.append(("vertical", r, c, expected, actual))
        for r in range(1, layout.rows):
            for c in range(layout.columns):
                mid_x = (xs[c] + xs[c + 1]) // 2
                expected = _SOLVED_GRID_GRAY if (grid[r - 1][c] and grid[r][c]) else INK
                actual = tuple(arr[ys[r], mid_x])
                if actual != expected:
                    mismatches.append(("horizontal", r, c, expected, actual))
        assert mismatches == []


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestBookSolvedPage_TitleBandMatchesBandIdentity:
    """AC-4 — the band reads exactly what band_identity(number, tier) says."""

    @staticmethod
    def _band_box(layout):
        placement = layout.page
        assert placement is not None
        return (0, placement.usable_top, layout.width, placement.drawing_top)

    @pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard", None])
    def test_the_band_matches_a_reference_band_identity_render(self, difficulty):
        payload = _payload(_RUN_GRID, name="Should Never Print", difficulty=difficulty)
        generator = BookPDFGenerator()
        page_number = 2
        puzzle_number = 12

        solved = generator.solved_puzzle_page(payload, puzzle_number, page_number)
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        expected_text = band_identity(puzzle_number, difficulty)

        reference_payload = ExportPayload(
            grid=payload.grid,
            row_clues=payload.row_clues,
            column_clues=payload.column_clues,
            seed=0,
            mode="random",
            width=payload.width,
            height=payload.height,
            name=None,
            difficulty=expected_text,
        )
        reference, _ = render_pages(
            reference_payload, page_spec=generator.page_spec(page_number)
        )

        box = self._band_box(layout)
        left, top, right, bottom = box
        np.testing.assert_array_equal(
            _array(solved)[top:bottom, left:right],
            _array(reference)[top:bottom, left:right],
        )

    def test_a_different_tier_changes_the_band_ink(self):
        easy = _payload(_RUN_GRID, difficulty="Easy")
        hard = _payload(_RUN_GRID, difficulty="Hard")
        generator = BookPDFGenerator()
        page_number = 2
        layout = compute_layout(
            easy.row_clues, easy.column_clues, generator.page_spec(page_number)
        )
        box = self._band_box(layout)
        left, top, right, bottom = box

        page_easy = generator.solved_puzzle_page(easy, 1, page_number)
        page_hard = generator.solved_puzzle_page(hard, 1, page_number)
        assert not np.array_equal(
            _array(page_easy)[top:bottom, left:right],
            _array(page_hard)[top:bottom, left:right],
        )


# --------------------------------------------------------------------------
# AC-5
# --------------------------------------------------------------------------


class TestBookSolvedPage_CaptionReadsThePictureName:
    """AC-5 — a cap-bound puzzle gets a caption, centred in the slack,
    inside the usable area."""

    @staticmethod
    def _render(title):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        page = generator.solved_puzzle_page(payload, 3, page_number, title=title)
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        return _array(page), layout

    def test_there_really_is_slack_below_the_drawing_on_this_shape(self):
        _, layout = self._render("Snowflake")
        placement = layout.page
        assert placement.usable_bottom - placement.drawing_bottom > 0

    def test_changing_the_title_changes_only_the_caption_area(self):
        arr_a, layout = self._render("Snowflake")
        arr_b, _ = self._render("A Completely Different Title")
        placement = layout.page

        # Everything from the page's top down to the drawing's bottom edge
        # is untouched by a caption, whatever its text.
        np.testing.assert_array_equal(
            arr_a[: placement.drawing_bottom, :],
            arr_b[: placement.drawing_bottom, :],
        )
        # The slack band itself does change.
        assert not np.array_equal(
            arr_a[placement.drawing_bottom : placement.usable_bottom, :],
            arr_b[placement.drawing_bottom : placement.usable_bottom, :],
        )

    def test_the_caption_is_drawn_inside_the_usable_area_only(self):
        arr, layout = self._render("Snowflake")
        placement = layout.page

        # Below the usable area (the trim's bottom margin) carries no ink.
        margin = arr[placement.usable_bottom :, :]
        assert np.array_equal(margin, np.full_like(margin, BACKGROUND[0]))

        # The slack band itself carries some ink (the caption was drawn).
        slack = arr[placement.drawing_bottom : placement.usable_bottom, :]
        assert not np.array_equal(slack, np.full_like(slack, BACKGROUND[0]))

        # That ink sits horizontally inside the usable area — never in the
        # trim margin outside it (a pixel or two of antialiasing bleed past
        # the drawing's own edges is not "inside the trim margin").
        dark_columns = np.flatnonzero((slack < 128).any(axis=(0, 2)))
        assert dark_columns.size > 0
        assert dark_columns.min() >= placement.usable_left
        assert dark_columns.max() <= placement.usable_right


# --------------------------------------------------------------------------
# CARD-203 AC-1
# --------------------------------------------------------------------------


class TestBookSolvedPage_CaptionRightAlignedWithTheGrid:
    """CARD-203 AC-1 — the caption's right edge lines up with
    ``placement.drawing_right`` (the grid's own right edge), not the page's
    horizontal centre under the grid (owner's Google Doc "Nonograms - Print
    layout1", 2026-10-08, item 5)."""

    @staticmethod
    def _render(title="Snowflake"):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        page = generator.solved_puzzle_page(payload, 3, page_number, title=title)
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        return _array(page), layout

    def test_the_captions_rightmost_ink_sits_at_drawing_right(self):
        arr, layout = self._render()
        placement = layout.page

        # Isolated to the right half of the drawing's own horizontal span,
        # so CARD-200's folio (drawn at the bottom-OUTER corner — the LEFT
        # side on this even page number, never under the right half of the
        # grid) cannot be mistaken for the caption's own ink.
        midpoint = (placement.drawing_left + placement.drawing_right) // 2
        slack = arr[
            placement.drawing_bottom : placement.usable_bottom,
            midpoint : placement.usable_right,
        ]
        dark_columns = np.flatnonzero((slack < 128).any(axis=(0, 2)))
        assert dark_columns.size > 0, "expected the caption's ink in the drawing's right half"
        rightmost = int(dark_columns.max()) + midpoint

        # Within normal antialiasing tolerance (a handful of device px — a
        # glyph's own rightmost ink can overshoot its advance width slightly
        # under hinting/antialiasing) of the grid's own right edge, and
        # never meaningfully past it.
        assert rightmost <= placement.drawing_right + 4
        assert rightmost >= placement.drawing_right - 6

    def test_the_right_edge_stays_fixed_regardless_of_title_length(self):
        """Right-alignment, not centring, is the thing being tested: a
        centred caption's rightmost pixel moves with the text's own width
        (half the width shift either way); a right-aligned one's rightmost
        pixel does not move at all, whatever the title reads."""

        def rightmost_ink(title):
            arr, layout = self._render(title)
            placement = layout.page
            midpoint = (placement.drawing_left + placement.drawing_right) // 2
            slack = arr[
                placement.drawing_bottom : placement.usable_bottom,
                midpoint : placement.usable_right,
            ]
            dark_columns = np.flatnonzero((slack < 128).any(axis=(0, 2)))
            assert dark_columns.size > 0
            return int(dark_columns.max()) + midpoint

        short = rightmost_ink("A")
        long = rightmost_ink("A Very Different, Much Longer Picture Name")
        assert abs(short - long) <= 2


# --------------------------------------------------------------------------
# CARD-203 AC-2 / AC-3
# --------------------------------------------------------------------------


class TestBookSolvedPage_CaptionMovedCloserToTheDrawing:
    """CARD-203 AC-2 — the caption sits a small fixed gap
    (``ANSWER_TILE_GAP_MM`` converted to this page's device pixels) below
    ``placement.drawing_bottom``, not centred across the whole slack to
    ``placement.usable_bottom``. AC-3 — at that new position, every caption
    pixel still sits strictly inside the usable area."""

    @staticmethod
    def _render(title="Snowflake"):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        page = generator.solved_puzzle_page(payload, 3, page_number, title=title)
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        return _array(page), layout, generator

    @staticmethod
    def _gap_px(generator):
        return round(ANSWER_TILE_GAP_MM / 25.4 * generator.dpi)

    @staticmethod
    def _line_height(generator):
        caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        caption_font_size = type_px(caption_font_points, generator.dpi)
        caption_font = _band_font(caption_font_size)
        ascent, descent = caption_font.getmetrics()
        return ascent + descent

    def test_there_really_is_slack_much_bigger_than_the_gap_plus_one_line(self):
        _, layout, generator = self._render()
        placement = layout.page
        slack = placement.usable_bottom - placement.drawing_bottom
        assert slack > 3 * (self._gap_px(generator) + self._line_height(generator)), (
            "this shape should have plenty of slack beyond one line plus the gap"
        )

    def test_the_captions_ink_sits_near_the_gap_not_centred_in_the_slack(self):
        arr, layout, generator = self._render()
        placement = layout.page
        gap_px = self._gap_px(generator)
        line_height = self._line_height(generator)

        # The grid's own outer-border rule overhangs `drawing_bottom` by a
        # pixel or two (pre-existing `_stroke_drawing` behaviour, nothing to
        # do with the caption) — skip a handful of rows past it before
        # looking for the caption's own ink.
        overhang = 5
        start = placement.drawing_bottom + overhang
        slack_band = arr[start : placement.usable_bottom, :, :]
        dark_rows = np.flatnonzero((slack_band < 128).any(axis=(1, 2)))
        assert dark_rows.size > 0, "expected the caption's ink somewhere in the slack"
        ink_top = int(dark_rows.min()) + start

        # Near the fixed gap above the caption's own text band (a few
        # pixels of headroom for a capital letter's cap-height sitting below
        # the font's full ascent line) — not anywhere close to the slack's
        # own middle, which is where the OLD centred-in-the-slack formula
        # would have put it on a shape with this much slack.
        expected_top = placement.drawing_bottom + gap_px
        assert expected_top <= ink_top <= expected_top + line_height // 2

        slack_total = placement.usable_bottom - placement.drawing_bottom
        old_centred_top = placement.drawing_bottom + (slack_total - line_height) // 2
        assert ink_top < old_centred_top - line_height, (
            "the caption should sit well above where the old centred-in-the-"
            "slack formula would have put it on this much-slack shape"
        )

    def test_the_caption_is_still_strictly_inside_the_usable_area(self):
        """AC-3 — re-verifies the existing AC-5 invariant at the new
        position (same check as
        TestBookSolvedPage_CaptionReadsThePictureName.test_the_caption_is_drawn_inside_the_usable_area_only)."""
        arr, layout, _ = self._render()
        placement = layout.page

        margin = arr[placement.usable_bottom :, :]
        assert np.array_equal(margin, np.full_like(margin, BACKGROUND[0]))

        slack = arr[placement.drawing_bottom : placement.usable_bottom, :]
        assert not np.array_equal(slack, np.full_like(slack, BACKGROUND[0]))

        dark_columns = np.flatnonzero((slack < 128).any(axis=(0, 2)))
        assert dark_columns.size > 0
        assert dark_columns.min() >= placement.usable_left
        assert dark_columns.max() <= placement.usable_right


# --------------------------------------------------------------------------
# AC-6
# --------------------------------------------------------------------------


class TestBookSolvedPage_CaptionOmittedWhenNoSlack:
    """AC-6 — a page-fit-bound puzzle (no slack below the drawing) prints no
    caption at all, rather than an overlapping or clipped one."""

    @staticmethod
    def _layout_and_generator():
        grid = _checkerboard(*_NO_SLACK_SHAPE)
        payload = _payload(grid, difficulty="Medium")
        generator = BookPDFGenerator()
        page_number = 2
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        return payload, generator, page_number, layout

    def test_this_shape_really_has_no_slack(self):
        _, _, _, layout = self._layout_and_generator()
        placement = layout.page
        assert placement.usable_bottom - placement.drawing_bottom <= 0

    def test_no_caption_pixel_is_drawn_outside_the_usable_area_or_over_the_grid(self):
        payload, generator, page_number, layout = self._layout_and_generator()
        placement = layout.page
        page = generator.solved_puzzle_page(payload, 7, page_number, title="Snowflake")
        arr = _array(page)

        # The grid's own outer border rule is centred on usable_bottom here
        # (drawing_bottom == usable_bottom, zero slack) and so, like every
        # other rule in this drawing, hangs half its own width outside —
        # a few pixels, pre-existing behaviour of `_stroke_drawing`, nothing
        # to do with a caption. Well beyond that overhang, nothing is drawn.
        far_margin = arr[placement.usable_bottom + 20 :, :]
        assert np.array_equal(far_margin, np.full_like(far_margin, BACKGROUND[0]))

        # Beside the grid's own horizontal span, even the frame/border's own
        # overhang is absent (a further 10 px of headroom past it, well
        # short of the drawing's own edge): nothing a caption could have
        # spilled sideways into the margin.
        overhang = 10
        side_margin = np.concatenate(
            [
                arr[placement.usable_bottom :, : placement.drawing_left - overhang],
                arr[placement.usable_bottom :, placement.drawing_right + overhang :],
            ],
            axis=1,
        )
        assert np.array_equal(side_margin, np.full_like(side_margin, BACKGROUND[0]))

    def test_the_rendered_page_is_identical_whatever_the_title(self):
        payload, generator, page_number, _ = self._layout_and_generator()
        page_a = generator.solved_puzzle_page(payload, 7, page_number, title="A")
        page_b = generator.solved_puzzle_page(
            payload, 7, page_number, title="A Very Different Picture Name"
        )
        np.testing.assert_array_equal(_array(page_a), _array(page_b))

    def test_the_narrow_gap_only_boundary_is_also_omitted(self):
        """CARD-203 AC-4 — a shape whose slack was enough for the line alone
        (the OLD guard, ``slack >= line_height``) but not enough once the
        new gap is added (``slack >= gap_px + line_height``) must also omit
        the caption, not draw it overlapping the gap or past
        ``usable_bottom``.

        ``_NARROW_GAP_SHAPE`` (29x23) sits at slack 58 px, inside
        ``[line_height, gap_px + line_height)`` = ``[49, 73)`` at this
        page's own DPI (asserted below, not assumed) — too little room for
        the new gap plus the line, though enough for the line alone under
        the old guard.
        """
        grid = _checkerboard(*_NARROW_GAP_SHAPE)
        payload = _payload(grid, difficulty="Medium")
        generator = BookPDFGenerator()
        page_number = 2
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        placement = layout.page
        slack = placement.usable_bottom - placement.drawing_bottom

        caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        caption_font_size = type_px(caption_font_points, generator.dpi)
        caption_font = _band_font(caption_font_size)
        ascent, descent = caption_font.getmetrics()
        line_height = ascent + descent
        gap_px = round(ANSWER_TILE_GAP_MM / 25.4 * generator.dpi)

        assert slack >= line_height, "the OLD guard would have drawn a caption here"
        assert slack < gap_px + line_height, "the NEW guard must omit it here"

        page = generator.solved_puzzle_page(payload, 7, page_number, title="Snowflake")
        arr = _array(page)

        # Isolated to the right half of the drawing's own span — where the
        # caption would sit were it drawn — so CARD-200's folio (the
        # bottom-OUTER corner mark, the LEFT side on this even page number,
        # which this shape's own slack is big enough to still carry) is not
        # mistaken for a caption that must not be there.
        overhang = 5
        midpoint = (placement.drawing_left + placement.drawing_right) // 2
        region = arr[placement.drawing_bottom + overhang :, midpoint : placement.usable_right]
        dark_columns = np.flatnonzero((region < 128).any(axis=(0, 2)))
        assert dark_columns.size == 0, "no caption ink should be drawn at this boundary"


# --------------------------------------------------------------------------
# AC-7
# --------------------------------------------------------------------------


class TestBookSolvedPage_TextHoldsTheTenPointFloor:
    """AC-7 — every drawn face except the clue digits holds CON-020's 10 pt
    floor at the page's own DPI."""

    FLOOR_PT = 10.0
    POINTS_PER_INCH = 72.0

    def _record(self, monkeypatch, generator, payload, puzzle_number, page_number, title):
        calls = []
        original = ImageDraw.ImageDraw.text

        def spy(self_draw, xy, text, fill=None, font=None, *args, **kwargs):
            import sys

            frame = sys._getframe(1)
            caller = frame.f_code.co_name if frame is not None else ""
            size = font.size if isinstance(font, ImageFont.FreeTypeFont) else None
            calls.append((caller, str(text), size))
            return original(self_draw, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        try:
            generator.solved_puzzle_page(payload, puzzle_number, page_number, title=title)
        finally:
            monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
        return calls

    def test_every_non_clue_face_is_at_least_ten_points(self, monkeypatch):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        calls = self._record(monkeypatch, generator, payload, 4, 2, "Snowflake")

        non_clue = [c for c in calls if c[0] != "_write_clues"]
        assert non_clue, "expected at least the band and the caption to be drawn"
        for caller, text, size in non_clue:
            assert size is not None, f"{caller}({text!r}) drew an unsized face"
            points = size * self.POINTS_PER_INCH / generator.dpi
            assert points >= self.FLOOR_PT, f"{caller}({text!r}) drew at {points:.2f} pt"

    def test_the_recording_covers_both_the_band_and_the_caption(self, monkeypatch):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        calls = self._record(monkeypatch, generator, payload, 4, 2, "Snowflake")
        callers = {c[0] for c in calls}
        assert "_set_band" in callers
        # CARD-202 (SCOPE+): the caption's own draw.text call moved from
        # solved_puzzle_page's body into a new shared helper,
        # BookPDFGenerator._draw_solved_slot, reused by a packed slot too
        # (see that method's own docstring) — the caption is still drawn
        # in-line, just one frame further down the call stack now.
        assert "_draw_solved_slot" in callers

    def test_clue_digits_are_exempt_and_are_exercised(self, monkeypatch):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        calls = self._record(monkeypatch, generator, payload, 4, 2, "Snowflake")
        clue_calls = [c for c in calls if c[0] == "_write_clues"]
        assert clue_calls, "expected clue digits to be drawn"


# --------------------------------------------------------------------------
# AC-8
# --------------------------------------------------------------------------


class TestBookSolvedPage_NoColour:
    """AC-8 — every pixel's R, G and B channels are equal."""

    def test_every_channel_is_equal_everywhere(self):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        # Flip one neighbour pair to also exercise the gray ink on this page.
        grid[0][0] = True
        grid[0][1] = True
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page = generator.solved_puzzle_page(payload, 9, 2, title="Snowflake")
        arr = _array(page)
        assert np.array_equal(arr[:, :, 0], arr[:, :, 1])
        assert np.array_equal(arr[:, :, 1], arr[:, :, 2])

    def test_both_the_black_ink_and_the_gray_tone_are_present(self):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        grid[0][0] = True
        grid[0][1] = True
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page = generator.solved_puzzle_page(payload, 9, 2, title="Snowflake")
        arr = _array(page)
        present = {tuple(c) for c in arr.reshape(-1, 3)[::31]}
        assert INK in present or any(c == (0, 0, 0) for c in present)
        assert _SOLVED_GRID_GRAY in present or any(
            c == _SOLVED_GRID_GRAY for c in present
        )


# --------------------------------------------------------------------------
# AC-9
# --------------------------------------------------------------------------


class TestBookSolvedPage_SameGeometryAsTheUnsolvedPage:
    """AC-9 — cell size, gutter depth, every grid-line position and the
    frame are identical to an unsolved page's."""

    def test_the_rendered_drawings_measure_identically(self):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)  # no gray marks on this grid
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        puzzle_number = 3

        solved = generator.solved_puzzle_page(payload, puzzle_number, page_number)

        unsolved_payload = ExportPayload(
            grid=payload.grid,
            row_clues=payload.row_clues,
            column_clues=payload.column_clues,
            seed=0,
            mode="random",
            width=payload.width,
            height=payload.height,
            name=None,
            difficulty=band_identity(puzzle_number, payload.difficulty),
        )
        blank, _ = render_pages(
            unsolved_payload, page_spec=generator.page_spec(page_number)
        )

        solved_drawing = drawing_of(solved)
        blank_drawing = drawing_of(blank)

        assert solved_drawing.left == blank_drawing.left
        assert solved_drawing.top == blank_drawing.top
        assert solved_drawing.grid_left == blank_drawing.grid_left
        assert solved_drawing.grid_right == blank_drawing.grid_right
        assert solved_drawing.grid_top == blank_drawing.grid_top
        assert solved_drawing.grid_bottom == blank_drawing.grid_bottom
        assert solved_drawing.columns == blank_drawing.columns
        assert solved_drawing.rows == blank_drawing.rows
        assert solved_drawing.cell == pytest.approx(blank_drawing.cell)
        assert solved_drawing.framed == blank_drawing.framed

    def test_pages_are_the_same_overall_size(self):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        solved = generator.solved_puzzle_page(payload, 3, page_number)
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        assert solved.size == (layout.width, layout.height)
