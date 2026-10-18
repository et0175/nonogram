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

CARD-203 review cycle 1 fixes:

    F-001  TestBookSolvedPage_CaptionDoesNotCollideWithTheFolio (new class) —
           the caption/folio pixel collision on a right-hand page, and its
           fix (the folio yields the corner to the caption, never the other
           way round — see ``_draw_folio``'s and
           ``BookPDFGenerator.solved_puzzle_page``'s own docstrings).
    F-003  TestBookSolvedPage_CaptionRightAlignedWithTheGrid and
           TestBookSolvedPage_CaptionMovedCloserToTheDrawing each gained a
           right-hand (odd) page_number test alongside their original
           left-hand (even) ones, so right-alignment and the closer gap are
           both verified on a right-hand page too.

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
from nonogram.admin.book_answer_key import answer_caption
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

#: CARD-203 AC-4's boundary shape: a 24x19 checkerboard found sweeping every
#: 10..30 row/column combination of a checkerboard grid against the Book 1
#: profile, whose slack (59 px) sits inside
#: ``[line_height, gap_px + line_height)`` = ``[49, 73)`` at this page's own
#: DPI — enough room for the caption's own line under the OLD guard
#: (``slack >= line_height``), not enough once the new gap is added
#: (``slack >= gap_px + line_height``). The same kind of hand-recorded sweep
#: result as ``_NO_SLACK_SHAPE`` above, not re-swept on every run.
#:
#: **Re-swept for CARD-222**: the shape that sat in this window on CON-018's
#: retired margins (29x23, 58 px) has 24 px of slack on the amended ones, so
#: it no longer demonstrates anything. Only two shapes of the 441 land in the
#: window now — 24x19 at 59 px and 27x22 at 57 — and the nearer of the two to
#: the retired figure is taken.
_NARROW_GAP_SHAPE = (24, 19)

#: CARD-203 review cycle 1, F-003: a right-hand (odd) page number, used
#: alongside the right-alignment/closer-gap tests that previously only ever
#: rendered ``page_number=2`` (even, left-hand) — see
#: ``page_is_right_hand`` (``book_pdf_generator.py``).
_RIGHT_HAND_PAGE_NUMBER = 3

#: CARD-203 review cycle 1, F-001's own reproduction shape: a 26x21
#: checkerboard on ``_RIGHT_HAND_PAGE_NUMBER`` yields zero horizontal margin
#: (``drawing_right == usable_right``) and 110 px of vertical slack — inside
#: the window where the caption's own omission guard
#: (``slack >= gap_px + line_height``, 73 px) and the pre-fix folio's "is
#: there room" bar (``line_height`` alone, 49 px) were BOTH satisfied, so
#: before the fix both marks drew into the same bottom-outer corner on a
#: right-hand page. Found by the same kind of hand-recorded sweep as
#: ``_NO_SLACK_SHAPE``/``_NARROW_GAP_SHAPE`` above, not re-swept on every run
#: (swept against every 10..30 row/column checkerboard for margin <= 5 px and
#: slack inside the window; 26x21 is the shape with the greatest margin-0
#: slack in it).
#:
#: **Re-swept for CARD-222**: the review's own shape (30x24) had 74 px of
#: slack on CON-018's retired margins and has 40 px on the amended ones,
#: which is under the caption's own guard — the window moved, not the defect.
_RIGHT_HAND_COLLISION_SHAPE = (26, 21)


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


def _caption_geometry(generator: BookPDFGenerator) -> Tuple[int, int]:
    """``(gap_px, line_height)`` for the caption, exactly as
    ``_draw_solved_slot`` computes them — used by the CARD-203 review cycle 1
    tests below to isolate the caption's own row band from the folio's
    (which, on a right-hand page, sits in the same column range near
    ``usable_right`` but always at the bottom-most rows, never near the
    caption's own, closer-to-the-grid position)."""
    caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
    caption_font_size = type_px(caption_font_points, generator.dpi)
    caption_font = _band_font(caption_font_size)
    ascent, descent = caption_font.getmetrics()
    line_height = ascent + descent
    gap_px = round(ANSWER_TILE_GAP_MM / 25.4 * generator.dpi)
    return gap_px, line_height


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
        # the drawing's own edges is not "inside the trim margin" — CARD-204
        # makes this bleed actually reachable on this shape: the drawing is
        # now flush with this left-hand page's outer margin, with no slack
        # of its own on that side, where centring always left some).
        dark_columns = np.flatnonzero((slack < 128).any(axis=(0, 2)))
        bleed = 2
        assert dark_columns.size > 0
        assert dark_columns.min() >= placement.usable_left - bleed
        assert dark_columns.max() <= placement.usable_right + bleed


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

    def test_right_alignment_also_holds_on_a_right_hand_page(self):
        """CARD-203 review cycle 1, F-003 — the three prior tests in this
        class all rendered ``page_number=2`` (even, left-hand); this repeats
        the first test's own assertion on an odd (right-hand) page, where
        the folio shares the caption's own side of the page (CARD-200,
        F-001) — the row band is narrowed to just below the drawing so the
        folio's own ink, further down near ``usable_bottom``, is never
        mistaken for the caption's."""
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = _RIGHT_HAND_PAGE_NUMBER
        page = generator.solved_puzzle_page(payload, 3, page_number, title="Snowflake")
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        placement = layout.page
        arr = _array(page)
        gap_px, line_height = _caption_geometry(generator)
        headroom = 10

        midpoint = (placement.drawing_left + placement.drawing_right) // 2
        caption_band = arr[
            placement.drawing_bottom : placement.drawing_bottom
            + gap_px
            + line_height
            + headroom,
            midpoint : placement.usable_right,
        ]
        dark_columns = np.flatnonzero((caption_band < 128).any(axis=(0, 2)))
        assert dark_columns.size > 0, "expected the caption's ink on this right-hand page too"
        rightmost = int(dark_columns.max()) + midpoint

        assert rightmost <= placement.drawing_right + 4
        assert rightmost >= placement.drawing_right - 6


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
        TestBookSolvedPage_CaptionReadsThePictureName.test_the_caption_is_drawn_inside_the_usable_area_only).

        **CARD-204 Fix 7 (merge gate) — two bands, not one.** This test used
        to scan the whole slack band for ink and require every dark column of
        it to be inside ``[usable_left, usable_right]``. On the merged tree it
        failed at column 111 against ``usable_left`` 113 — and the ink at 111
        is **not the caption's**: it is the *drawing's own* bottom border
        rule, which ``_stroke_drawing`` strokes centred on the grid's
        boundary and which therefore overhangs the drawing's own edges by
        about half a rule (measured: 2 px, and only on the band's first
        rows; the caption's own ink on this shape runs from column 986 to
        1438, well inside — 873 px clear of ``usable_left``; re-measured
        under CARD-204 Fix 8, review cycle 5's F-3, which found the figure
        first written here was wrong). While CARD-203's caption sat under a
        *centred* drawing that overhang had the page's own horizontal spare
        to spend;
        under CARD-204 the drawing is flush with an even page's outer margin,
        so it reaches 2 px past it — which is exactly the bleed AC-5's own
        twin test above already documents and tolerates (``bleed = 2``), and
        a property of the drawing's border rather than of the caption this
        class is about.

        So the band is split rather than given a blanket tolerance: the rows
        the drawing's own border reaches into keep AC-5's documented 2 px
        bleed, and the caption's own rows — everything below that overhang,
        which is where ``_draw_solved_slot`` puts the caption and
        ``_draw_folio`` the folio — keep the strict claim with no tolerance
        at all. Narrowing the row band is the same trick this class's own
        ``test_the_captions_ink_sits_near_the_gap_not_centred_in_the_slack``
        already uses (``overhang = 5``) for the same reason. What the caption
        does when it is *itself* too wide for the margin is a separate
        question, pinned on both parities by
        ``TestBookSolvedPage_CaptionWiderThanItsGridStaysInsideTheMargin``.
        """
        arr, layout, _ = self._render()
        placement = layout.page

        margin = arr[placement.usable_bottom :, :]
        assert np.array_equal(margin, np.full_like(margin, BACKGROUND[0]))

        slack = arr[placement.drawing_bottom : placement.usable_bottom, :]
        assert not np.array_equal(slack, np.full_like(slack, BACKGROUND[0]))

        # The drawing's own border rows: AC-5's documented bleed, no more.
        overhang = 5
        bleed = 2
        border = arr[placement.drawing_bottom : placement.drawing_bottom + overhang, :]
        border_columns = np.flatnonzero((border < 128).any(axis=(0, 2)))
        assert border_columns.size > 0, "expected the drawing's own bottom rule here"
        assert border_columns.min() >= placement.usable_left - bleed
        assert border_columns.max() <= placement.usable_right + bleed

        # The caption's own rows (and the folio's): strictly inside, no bleed.
        below = arr[placement.drawing_bottom + overhang : placement.usable_bottom, :]
        dark_columns = np.flatnonzero((below < 128).any(axis=(0, 2)))
        assert dark_columns.size > 0, "expected the caption's ink below the border"
        assert dark_columns.min() >= placement.usable_left
        assert dark_columns.max() <= placement.usable_right

    def test_the_closer_gap_also_holds_on_a_right_hand_page(self):
        """CARD-203 review cycle 1, F-003 — the three prior tests in this
        class all rendered ``page_number=2`` (even, left-hand); this repeats
        ``test_the_captions_ink_sits_near_the_gap_not_centred_in_the_slack``'s
        own assertion on an odd (right-hand) page. The row-wise topmost-ink
        search is unaffected by which side the folio sits on (the folio's
        own ink always starts near ``usable_bottom``, well below the
        caption's, on either page parity), so this mirrors that test
        directly rather than needing the right-alignment tests' own
        column-narrowing trick."""
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = _RIGHT_HAND_PAGE_NUMBER
        page = generator.solved_puzzle_page(payload, 3, page_number, title="Snowflake")
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        placement = layout.page
        arr = _array(page)
        gap_px, line_height = _caption_geometry(generator)

        overhang = 5
        start = placement.drawing_bottom + overhang
        slack_band = arr[start : placement.usable_bottom, :, :]
        dark_rows = np.flatnonzero((slack_band < 128).any(axis=(1, 2)))
        assert dark_rows.size > 0, "expected the caption's ink somewhere in the slack"
        ink_top = int(dark_rows.min()) + start

        expected_top = placement.drawing_bottom + gap_px
        assert expected_top <= ink_top <= expected_top + line_height // 2

        slack_total = placement.usable_bottom - placement.drawing_bottom
        old_centred_top = placement.drawing_bottom + (slack_total - line_height) // 2
        assert ink_top < old_centred_top - line_height, (
            "the caption should sit well above where the old centred-in-the-"
            "slack formula would have put it on this much-slack shape, on "
            "a right-hand page too"
        )


# --------------------------------------------------------------------------
# CARD-204 Fix 7 (merge gate) — CARD-203's right-aligned caption meets
# CARD-204's flush drawing
# --------------------------------------------------------------------------


class TestBookSolvedPage_CaptionWiderThanItsGridStaysInsideTheMargin:
    """CARD-204 Fix 7 — no caption ink leaves ``[usable_left, usable_right]``,
    on either parity, for any caption the book can produce.

    **The defect.** CARD-203 right-aligns the caption at
    ``placement.drawing_right``; a caption *wider than its own grid* therefore
    extends left past ``placement.drawing_left``. A caption is as wide as the
    picture's name, which nothing bounds (``books.puzzle_titles`` is free
    text from the Arrangement step), while a grid is as wide as the puzzle —
    so the two are not ordered. Under CARD-204 an EVEN page's drawing was
    flush with the outer margin (``drawing_left == usable_left``), so any
    overhang at all crossed it. Measured before the fix on this shape: the
    caption's leftmost ink at column **0** against ``usable_left`` 113 —
    9.6 mm of a reader-facing name printed into the trim margin and running
    off the page.

    **CARD-224 (AC-5, G-3): the clamp is kept, it still fires, and the width
    at which it fires has moved.** Centring the drawing again gives it half
    the page's spare on its left — 461 px on this shape — so a caption has to
    overhang its own grid by more than that before it reaches the margin.
    ``_OVER_GRID_TITLE`` (1705 px against a 1328 px drawing) no longer does:
    it is now the *control* that shows the restored spare absorbing an
    overhang, exactly as this module's docstring says it did before CARD-204.
    ``_OVER_SPARE_TITLE`` (2190 px) is the caption that spends the whole
    spare and lands on ``usable_left``, so the clamp-only regime stays
    exercised rather than quietly becoming vacuous; ``_OVER_PAGE_TITLE``
    (3032 px) still exercises the clip. All three widths are asserted below
    against the page's own measurements, so none of them can drift into
    another regime unnoticed.

    **The fix** is :func:`~nonogram.export.layout.caption_slot`: the
    caption's right edge is pushed right by exactly the overhang and no more,
    so right-alignment holds wherever it fits (every caption this corpus
    prints — a corpus caption measures 460 px against a 1328 px grid) and the
    usable area's left edge is the hard stop where it does not. A caption too
    wide for the usable area at *any* x is clipped to an ellipsis first
    (``_clipped_to``, the TOC's own loop): its type cannot shrink to fit
    instead, because ``ANSWER_TEXT_FONT_MM`` already *is* CON-020's 10 pt
    floor.

    Both regimes, both parities, and the premises are asserted rather than
    assumed — a title that stopped being wider than its grid would make every
    assertion below vacuous.
    """

    #: A picture name whose caption is wider than its own 10x10 grid
    #: (measured: 1705 px against a 1328 px drawing) but still narrower than
    #: Book 1's own usable width (2287 px) — the regime the clamp alone
    #: answers, with the caption's text untouched.
    _OVER_GRID_TITLE = "A Snowflake Over The Frozen Pine Woods At Midnight In Deep Winter"

    #: A name whose caption (measured: 2190 px) is wider than the drawing's
    #: right edge is from the usable area's left one (1789 px on this shape)
    #: but still narrower than the usable width (2250 px): the caption that
    #: reaches the margin under CARD-224's centring, and so the one the clamp
    #: alone has to answer.
    _OVER_SPARE_TITLE = (
        "A Snowflake Over The Frozen Pine Woods At Midnight In Deep Winter "
        "While The Owls Watch"
    )

    #: A name whose caption is wider than the whole usable area (measured:
    #: 3032 px against 2287/2288 px) — the regime no x can answer, where the
    #: text itself must be clipped.
    _OVER_PAGE_TITLE = (
        "A Snowflake Over The Frozen Pine Woods At Midnight In Deep Winter "
        "While The Owls Keep Watch From The Tallest Branches Above"
    )

    _PUZZLE_NUMBER = 3

    @classmethod
    def _render(cls, page_number: int, title: str):
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page = generator.solved_puzzle_page(
            payload, cls._PUZZLE_NUMBER, page_number, title=title
        )
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        return _array(page), layout, generator

    @classmethod
    def _caption_ink_columns(cls, arr, placement, generator):
        """The dark columns of the caption's **own** row band.

        Narrowed to the one line the caption occupies — the fixed gap below
        the drawing, one line tall — so neither the drawing's own border rule
        (which overhangs ``drawing_bottom`` by ~2 px: see
        ``TestBookSolvedPage_CaptionMovedCloserToTheDrawing``'s own AC-3 test)
        nor the folio further down near ``usable_bottom`` can be mistaken for
        the caption's ink.
        """
        gap_px, line_height = _caption_geometry(generator)
        top = placement.drawing_bottom + gap_px
        band = arr[top : top + line_height, :]
        return np.flatnonzero((band < 128).any(axis=(0, 2)))

    @classmethod
    def _caption_width(cls, generator, title) -> float:
        """What the caption measures in the face ``_draw_solved_slot`` letters
        it in — derived here from the same three constants that method reads,
        never asked of the production code."""
        font = _band_font(type_px(ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4, generator.dpi))
        return font.getlength(answer_caption(cls._PUZZLE_NUMBER, title))

    @pytest.mark.parametrize("page_number", [2, _RIGHT_HAND_PAGE_NUMBER])
    def test_the_three_titles_really_are_in_the_three_regimes(self, page_number):
        """The premise, on both parities, in the three widths CARD-224 leaves:
        one caption wider than its own grid but still inside the spare, one
        that spends the spare and reaches the margin, one wider than the whole
        usable area."""
        _, layout, generator = self._render(page_number, self._OVER_GRID_TITLE)
        placement = layout.page
        drawing_width = placement.drawing_right - placement.drawing_left
        usable_width = placement.usable_right - placement.usable_left
        #: How wide a right-aligned caption can be before its left edge
        #: crosses ``usable_left``: the drawing's right edge measured from
        #: that margin.
        room = placement.drawing_right - placement.usable_left

        over_grid = self._caption_width(generator, self._OVER_GRID_TITLE)
        over_spare = self._caption_width(generator, self._OVER_SPARE_TITLE)
        over_page = self._caption_width(generator, self._OVER_PAGE_TITLE)
        assert drawing_width < over_grid < room, (
            "_OVER_GRID_TITLE must overhang its grid and still clear the "
            "margin: it is the control for the spare centring restores"
        )
        assert room < over_spare < usable_width, (
            "_OVER_SPARE_TITLE must exercise the clamp and not the clip"
        )
        assert over_page > usable_width, "_OVER_PAGE_TITLE must exercise the clip"

    @pytest.mark.parametrize("page_number", [2, _RIGHT_HAND_PAGE_NUMBER])
    @pytest.mark.parametrize(
        "title_name", ["_OVER_GRID_TITLE", "_OVER_SPARE_TITLE", "_OVER_PAGE_TITLE"]
    )
    def test_no_caption_ink_leaves_the_usable_area(self, page_number, title_name):
        title = getattr(self, title_name)
        arr, layout, generator = self._render(page_number, title)
        placement = layout.page
        columns = self._caption_ink_columns(arr, placement, generator)

        assert columns.size > 0, "expected the caption's own ink in its own band"
        assert columns.min() >= placement.usable_left, (
            f"the caption's leftmost ink is {placement.usable_left - columns.min()} px "
            f"outside the usable area on a {placement.parity} page"
        )
        assert columns.max() <= placement.usable_right

    @pytest.mark.parametrize(
        "page_number, title_name",
        [
            # CARD-224: the drawing is centred on both parities, and on
            # CON-018 as amended the two side margins are equal, so the two
            # parities are the same geometry and the clamp fires at the same
            # caption width on each. Both are swept rather than one, so a
            # future card that makes them differ again shows up here.
            (2, "_OVER_SPARE_TITLE"),
            (2, "_OVER_PAGE_TITLE"),
            (_RIGHT_HAND_PAGE_NUMBER, "_OVER_SPARE_TITLE"),
            (_RIGHT_HAND_PAGE_NUMBER, "_OVER_PAGE_TITLE"),
        ],
    )
    def test_the_clamp_moves_the_caption_by_the_overhang_and_no_more(
        self, page_number, title_name
    ):
        """Not "shove it anywhere inside": the caption keeps as much of
        CARD-203's right-alignment as the margin allows, so an over-wide
        caption's left edge lands *on* ``usable_left``, not past it and not
        well inside it either."""
        arr, layout, generator = self._render(page_number, getattr(self, title_name))
        placement = layout.page
        columns = self._caption_ink_columns(arr, placement, generator)
        # Two things keep the leftmost ink a little inside ``usable_left``: a
        # glyph's own left side bearing, and — for the clipped title — the
        # clip's own granularity, which is a whole character. The clipped
        # caption stops at the last character that still fits the measure, so
        # its ink can fall short of the margin by up to one character's
        # advance. Measured on CON-018's amended margins (CARD-222): 36 px for
        # the clipped title on this page, where the retired margins happened
        # to put the clip within 8 px. 48 px is one em of this face at 10 pt
        # plus the bearing, which is the real bound on both regimes.
        bearing = 48
        assert placement.usable_left <= columns.min() <= placement.usable_left + bearing

    @pytest.mark.parametrize("page_number", [2, _RIGHT_HAND_PAGE_NUMBER])
    def test_a_page_absorbs_an_overhang_inside_its_own_spare_without_a_clamp(
        self, page_number
    ):
        """The clamp is not a blanket "captions are left-aligned now": a
        caption that overhangs its own grid but stays inside the page's spare
        keeps CARD-203's right-alignment exactly, on either parity.

        **CARD-224 restated this from a parity asymmetry.** Until this card
        the same ``_OVER_GRID_TITLE`` had to be clamped on a left-hand page
        and not on a right-hand one, because CARD-204's flush anchor gave an
        EVEN page's drawing no left-hand spare and an ODD page's all of it.
        Centring splits the spare evenly, and on CON-018 as amended the two
        side margins are equal, so the two parities are now the same geometry
        — the identity the registry's note on EC-032 warns a reviewer not to
        read as evidence of mirroring. Both are therefore asserted to behave
        the same way, which is a claim about the alignment rather than about
        the parity."""
        arr, layout, generator = self._render(page_number, self._OVER_GRID_TITLE)
        placement = layout.page
        columns = self._caption_ink_columns(arr, placement, generator)
        assert columns.max() <= placement.drawing_right + 4
        assert columns.max() >= placement.drawing_right - 6
        # Right-aligned at the drawing's own edge, so the left edge is that
        # edge less the caption's measured width — inside the margin, with
        # the spare it did not spend (84 px here) to go. A clamped caption
        # would start at ``usable_left`` instead, 84 px further left.
        width = self._caption_width(generator, self._OVER_GRID_TITLE)
        unclamped_left = placement.drawing_right - width
        assert unclamped_left > placement.usable_left, (
            "this page's own spare should absorb the overhang entirely"
        )
        assert abs(columns.min() - unclamped_left) <= 48, (columns.min(), unclamped_left)

    @pytest.mark.parametrize("page_number", [2, _RIGHT_HAND_PAGE_NUMBER])
    def test_a_caption_too_wide_for_the_page_is_clipped_and_still_names_the_puzzle(
        self, monkeypatch, page_number
    ):
        """The clip is on the *text*, and it keeps the part that identifies
        the answer: a reader finds an answer by its number (the caption's own
        "Puzzle N", the same number the band shows), so the number survives
        and the name is what loses its tail. Recorded off the ``draw.text``
        call itself rather than read back off pixels, since what is asserted
        here is the string."""
        grid = _checkerboard(*_CAP_BOUND_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        drawn: list[tuple[str, str]] = []
        original = ImageDraw.ImageDraw.text

        def spy(self_draw, xy, text, fill=None, font=None, *args, **kwargs):
            import sys

            frame = sys._getframe(1)
            drawn.append((frame.f_code.co_name if frame is not None else "", str(text)))
            return original(self_draw, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        try:
            generator.solved_puzzle_page(
                payload, self._PUZZLE_NUMBER, page_number, title=self._OVER_PAGE_TITLE
            )
        finally:
            monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        captions = [text for caller, text in drawn if caller == "_draw_solved_slot"]
        assert len(captions) == 1, captions
        caption = captions[0]
        assert caption.startswith(f"Puzzle {self._PUZZLE_NUMBER}")
        assert caption.endswith("…"), caption
        assert caption != answer_caption(self._PUZZLE_NUMBER, self._OVER_PAGE_TITLE)
        assert len(caption) < len(answer_caption(self._PUZZLE_NUMBER, self._OVER_PAGE_TITLE))

    def test_a_caption_that_fits_is_not_clipped_or_moved(self):
        """The negative control: the clamp and the clip are both *inactive*
        for a caption of the length a book actually prints, so CARD-203's
        own right-alignment tests above still describe every real page."""
        arr, layout, generator = self._render(2, "Snowflake")
        placement = layout.page
        assert self._caption_width(generator, "Snowflake") < (
            placement.drawing_right - placement.drawing_left
        )
        columns = self._caption_ink_columns(arr, placement, generator)
        assert columns.max() <= placement.drawing_right + 4
        assert columns.max() >= placement.drawing_right - 6
        assert columns.min() > placement.usable_left, (
            "a caption this short should sit nowhere near the margin"
        )


# --------------------------------------------------------------------------
# CARD-203 review cycle 1, F-001
# --------------------------------------------------------------------------


class TestBookSolvedPage_CaptionDoesNotCollideWithTheFolio:
    """CARD-203 review cycle 1, F-001 (gating) — the right-aligned caption
    and CARD-200's pre-existing folio (``_draw_folio``) can target the same
    bottom-outer corner on a right-hand page. Before the fix, a shape whose
    slack fell inside the window where the caption's own omission guard
    (``slack >= gap_px + line_height``) and the folio's own "is there room"
    bar (``line_height`` alone — narrower, since it did not yet know about
    the caption) were BOTH satisfied drew the two marks overlapping.

    ``_RIGHT_HAND_COLLISION_SHAPE`` (26x21 since CARD-222 re-swept it) is
    that reproduction: margin 0 (``drawing_right == usable_right``) and 110 px
    of slack, squarely inside that window at this page's DPI.
    """

    _PUZZLE_NUMBER = 7
    _TITLE = "Snowflake"

    @classmethod
    def _render(cls, page_number: int):
        grid = _checkerboard(*_RIGHT_HAND_COLLISION_SHAPE)
        payload = _payload(grid, difficulty="Easy")
        generator = BookPDFGenerator()
        page = generator.solved_puzzle_page(
            payload, cls._PUZZLE_NUMBER, page_number, title=cls._TITLE
        )
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(page_number)
        )
        return _array(page), layout, generator

    @classmethod
    def _caption_only_reference(cls, layout, generator) -> np.ndarray:
        """An independently rendered reference: a blank page of the same
        size with *only* the caption drawn, by the exact same formula
        :meth:`BookPDFGenerator._draw_solved_slot` uses (ground-truth
        reuse, the same technique AC-1's clue-gutter test already applies to
        a whole page). Diffing the real page against this isolates any ink
        the caption itself does not account for — i.e. the folio, if drawn
        — without guessing at row/column windows that the caption's and
        folio's own geometry can otherwise make nearly indistinguishable at
        this shape's small slack."""
        placement = layout.page
        assert placement is not None
        canvas = Image.new("RGB", (layout.width, layout.height), BACKGROUND)
        draw = ImageDraw.Draw(canvas)
        gap_px, line_height = _caption_geometry(generator)
        caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        caption_font_size = type_px(caption_font_points, generator.dpi)
        caption_font = _band_font(caption_font_size)
        from nonogram.admin.book_answer_key import answer_caption

        caption = answer_caption(cls._PUZZLE_NUMBER, cls._TITLE)
        draw.text(
            (
                placement.drawing_right,
                placement.drawing_bottom + gap_px + line_height / 2,
            ),
            caption,
            font=caption_font,
            fill=INK,
            anchor="rm",
        )
        return _array(canvas)

    def test_this_shape_really_sits_in_the_danger_window_on_a_right_hand_page(self):
        _, layout, generator = self._render(_RIGHT_HAND_PAGE_NUMBER)
        placement = layout.page
        slack = placement.usable_bottom - placement.drawing_bottom
        gap_px, line_height = _caption_geometry(generator)

        assert placement.drawing_right == placement.usable_right, (
            "the review's own repro shape has zero horizontal margin"
        )
        assert slack >= gap_px + line_height, "the caption must actually draw here"
        # The pre-fix folio bar (line_height alone, 49 px at this DPI) is
        # narrower than the caption's own (gap_px + line_height, 73 px): a
        # slack value clearing the caption's bar by only a little still
        # clears the folio's bar by a wide margin, which is exactly the
        # danger window this shape was swept to land inside.
        assert slack - (gap_px + line_height) < line_height, (
            "this shape should sit close enough to the caption's own bar "
            "that the pre-fix folio bar was already well cleared too"
        )

    def test_the_folio_yields_rather_than_overlap_the_caption(self):
        """The actual regression check: diff the real right-hand page
        against an independently rendered reference carrying *only* the
        caption's own ink (ground-truth reuse — see
        ``_caption_only_reference``'s own docstring). Any dark pixel the
        real page has that the caption-only reference does not is ink this
        card's own caption drawing cannot account for — i.e. the folio.

        At this shape's geometry (margin 0: ``drawing_right ==
        usable_right``) the folio's own horizontal-clearance check in
        ``_draw_folio`` can never pass once it knows about the caption's
        box (CARD-203 review cycle 1 fix), so the correct, deterministic
        outcome here is the folio omitted outright — not "drawn elsewhere
        with daylight between them" (that outcome is only geometrically
        possible on a shape with horizontal margin to spare, not this
        one). Whichever outcome a future shape produces, "no extra ink
        touching/overlapping the caption's own" is what this asserts.
        """
        arr, layout, generator = self._render(_RIGHT_HAND_PAGE_NUMBER)
        reference = self._caption_only_reference(layout, generator)
        placement = layout.page

        # Skip the grid's own outer-border overhang (a pre-existing couple
        # of pixels past `drawing_bottom`, nothing to do with the caption or
        # folio) before comparing, the same `overhang` skip every other test
        # in this module uses.
        overhang = 5
        start = placement.drawing_bottom + overhang
        real_slack = arr[start : placement.usable_bottom, :, :]
        reference_slack = reference[start : placement.usable_bottom, :, :]

        real_dark = (real_slack < 128).any(axis=2)
        caption_dark = (reference_slack < 128).any(axis=2)
        assert caption_dark.any(), "expected the caption to draw on this shape"

        extra_ink = real_dark & ~caption_dark
        assert not extra_ink.any(), (
            "found ink below the drawing that the caption alone does not "
            "account for — the folio drew into the caption's own corner, "
            "the exact collision F-001 reported"
        )

    def test_a_left_hand_page_with_the_same_shape_still_draws_both_marks(self):
        """The fix is scoped to the right-hand page's corner (where the
        caption and folio can actually coincide) — the same shape on a
        left-hand page, where the folio sits at the opposite (left) outer
        corner, must still draw both marks, unaffected by this fix."""
        arr, layout, generator = self._render(2)
        reference = self._caption_only_reference(layout, generator)
        placement = layout.page

        overhang = 5
        start = placement.drawing_bottom + overhang
        real_slack = arr[start : placement.usable_bottom, :, :]
        reference_slack = reference[start : placement.usable_bottom, :, :]

        real_dark = (real_slack < 128).any(axis=2)
        caption_dark = (reference_slack < 128).any(axis=2)
        assert caption_dark.any(), "expected the caption to draw on this shape"

        # On a left-hand page the caption's own fix never engages (the
        # folio sits at the opposite corner) — the folio's own ink is still
        # there, as "extra" ink the caption-only reference does not predict.
        extra_ink = real_dark & ~caption_dark
        assert extra_ink.any(), (
            "expected the folio to still draw, unaffected, on a left-hand page"
        )

        # And it sits well clear of the caption: every "extra" (folio) dark
        # column lies to the left of every caption dark column.
        extra_cols = np.flatnonzero(extra_ink.any(axis=0))
        caption_cols = np.flatnonzero(caption_dark.any(axis=0))
        assert extra_cols.max() < caption_cols.min()


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
