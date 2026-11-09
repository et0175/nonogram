"""The grey cell rule on an answer tile's grid (CARD-197, re-expressed on the
vector page by CARD-322).

``_RUN_GRID`` (4x4) is built by hand to carry every boundary kind: two
within-row adjacent-filled pairs, a filled-then-empty pair, an
empty-then-empty pair and two row-to-row adjacent-filled pairs.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from nonogram import clues
from nonogram.admin.book_answer_key import Answer, PackedAnswerPage
from nonogram.admin.book_answer_vector import packed_answer_page
from nonogram.admin.book_pdf_generator import BookPDFGenerator, answer_section_spec
from nonogram.difficulty import Tier
from nonogram.export import ExportPayload
from nonogram.export.layout import compute_packed_solved_layout

from tests.helpers.pdf_pages import page_image

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


def _payload(
    grid: list[list[bool]],
    *,
    name: Optional[str] = None,
    difficulty: object = None,
) -> ExportPayload:
    row_clues = tuple(clues.encode_line(row) for row in grid)
    column_clues = tuple(clues.encode_line(column) for column in zip(*grid))
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


def _array(image) -> np.ndarray:
    return np.asarray(image.convert("RGB"))


#: The vector answer page's two greys (measured on the baseline run grid,
#: poppler at 300 DPI): the owner's 0.3 pt cell line is 89 on white, and the
#: same rule inside the solid black mass between two filled cells is the
#: lighter 160, so it stays visible. Written out here, not imported.
VECTOR_THIN_GREY_ON_WHITE = (89, 89, 89)
VECTOR_THIN_GREY_ON_BLACK = (160, 160, 160)


def _window(arr, fixed, centre, vertical: bool) -> set:
    """The set of RGB triples within 2 px either side of ``centre``."""
    if vertical:
        return {tuple(int(v) for v in arr[fixed, x]) for x in range(centre - 2, centre + 3)}
    return {tuple(int(v) for v in arr[y, fixed]) for y in range(centre - 2, centre + 3)}


def thin_grey_rule_findings(arr, xs, ys, layout, grid) -> list:
    """Every interior boundary of ``grid`` whose thin grey rule is missing or the wrong tone.

    The owner's three-weight design (ADR-0037/R2 as amended 2026-10-17: 0.3 pt
    grey cell lines) draws that rule on EVERY interior boundary of the vector
    answer page: 160 where both neighbours are filled, 89 anywhere else
    (filled-to-empty, empty-to-empty). The rule is 2 px wide and poppler
    centres it, so it is read in a 2 px window either side of the layout
    coordinate.
    """
    found = []
    for c in range(1, layout.columns):
        for r in range(layout.rows):
            want = VECTOR_THIN_GREY_ON_BLACK if (grid[r][c - 1] and grid[r][c]) else VECTOR_THIN_GREY_ON_WHITE
            window = _window(arr, (ys[r] + ys[r + 1]) // 2, xs[c], vertical=True)
            if want not in window:
                found.append(("vertical", r, c, want, sorted(window)))
    for r in range(1, layout.rows):
        for c in range(layout.columns):
            want = VECTOR_THIN_GREY_ON_BLACK if (grid[r - 1][c] and grid[r][c]) else VECTOR_THIN_GREY_ON_WHITE
            window = _window(arr, (xs[c] + xs[c + 1]) // 2, ys[r], vertical=False)
            if want not in window:
                found.append(("horizontal", r, c, want, sorted(window)))
    return found


class TestBookSolvedPage_TheVectorBoundariesAreTheThinGreyRule:
    """The grey 0.3 pt cell rule is on every interior boundary of an answer
    tile (owner ruling 2026-11-07: grey on a filled/empty boundary is
    correct), lighter where both neighbours are filled.

    Read off a packed answer page holding the run grid alone, at the tile
    coordinates COMP-007 reports for it.
    """

    @staticmethod
    def _render():
        payload = _payload(_RUN_GRID, difficulty="Easy")
        generator = BookPDFGenerator()
        page_number = 2
        page = page_image(
            packed_answer_page(
                generator.page_spec(page_number),
                generator.dpi,
                PackedAnswerPage((Answer(number=1, width=4, height=4, level=Tier.EASY),)),
                [("p1", payload)],
                page_number,
                {},
            )
        )
        packed = compute_packed_solved_layout(
            [(payload.row_clues, payload.column_clues)],
            4,
            answer_section_spec(generator.page_spec(page_number)),
        )
        layout = packed.slots[0]
        xs = [line.position for line in layout.vertical_lines]
        ys = [line.position for line in layout.horizontal_lines]
        return _array(page.convert("RGB")), xs, ys, layout

    def test_a_filled_to_empty_boundary_is_the_thin_grey_rule(self):
        arr, xs, ys, _ = self._render()
        mid_y = (ys[0] + ys[1]) // 2  # row 0, columns 2-3: filled, then empty
        assert VECTOR_THIN_GREY_ON_WHITE in _window(arr, mid_y, xs[3], vertical=True)

    def test_an_empty_to_empty_boundary_is_the_thin_grey_rule(self):
        arr, xs, ys, _ = self._render()
        mid_y = (ys[2] + ys[3]) // 2  # row 2, columns 0-1: both empty
        assert VECTOR_THIN_GREY_ON_WHITE in _window(arr, mid_y, xs[1], vertical=True)

    def test_every_interior_boundary_carries_the_thin_grey_rule(self):
        arr, xs, ys, layout = self._render()
        assert thin_grey_rule_findings(arr, xs, ys, layout, _RUN_GRID) == []

    def test_a_boundary_drawn_black_or_missing_is_found(self):
        """Plants: one filled/empty boundary painted black, one painted white,
        and a rule in the wrong tone; each must red the reading, and the
        clean page must not."""
        arr, xs, ys, layout = self._render()
        assert thin_grey_rule_findings(arr, xs, ys, layout, _RUN_GRID) == []
        mid_y = (ys[0] + ys[1]) // 2
        for label, value in (("black", 0), ("white", 255), ("wrong tone", 140)):
            planted = arr.copy()
            planted[mid_y, xs[3] - 2 : xs[3] + 3] = value  # row 0: filled | empty
            assert thin_grey_rule_findings(planted, xs, ys, layout, _RUN_GRID), label
        mid_y2 = (ys[2] + ys[3]) // 2
        planted = arr.copy()
        planted[mid_y2, xs[1] - 2 : xs[1] + 3] = 255  # row 2: empty | empty
        assert thin_grey_rule_findings(planted, xs, ys, layout, _RUN_GRID)
