"""CARD-134's packed answer key — what survives CARD-198 (ADR-0036/R2, G-5).

CARD-198 replaced the book's packed 6-up/4-up answer key with one full solved
page per puzzle (:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.solved_puzzle_page`),
so every test here that exercised the packed key *through the book generator*
— ``BookPDFGenerator.answer_key``/``_answer_page``, and the whole-interior
walk that used to produce packed tiles behind the SOLUTIONS divider — pinned
a production behaviour that no longer exists and was retired. The one-page-
per-puzzle behaviour it replaced them with is pinned instead by
``tests/test_book_solved_answer_key.py`` (AC-1..AC-5, AC-7) and by CARD-197's
own ``tests/test_book_solved_page.py`` (G-1: ``solved_puzzle_page`` itself is
reused verbatim, unedited by this card).

What is left below is every test that was **never a test of the book
generator's packed-key production path in the first place** — each one
exercises ``book_answer_key``'s pure capacity rule or COMP-007's
``render_answer_page``/``compute_answer_page_layout`` directly, neither of
which this card touches (G-5: ``book_answer_key.py`` is left in the module,
unedited, even though no production code calls ``pack_answer_pages``/
``AnswerPage``/``Answer`` after this card — deleting them is a decision for
later, not this card's). These tests make no claim about what the book
generator currently *does* with a packed key; they are evergreen guards on
code that still exists and could still be reused.

    EC-031  TestBookAnswerKey_SixUpRuleKeepsTheAnswerCellAboveTheFloor
            (the link only — the floor itself is CARD-133's
            tests/property/test_book_answer_tiles.py)
    G-1a    TestBookAnswerKey_CaptionSeparatorIsADrawnGlyph
    AC-6    TestBookKdp_UnpairedCountStillRejectsAMalformedGrid (CARD-198)

    TestBookAnswerKey_TheExtentReaderAgreesWithTheRenderer pins that
    ``book_pdf_generator._answer_extent`` (kept by CARD-198 for validation
    only — see that card) and ``png._answer_extent`` still agree, since both
    functions are still in the codebase and nothing but this test keeps them
    from drifting into two different answers about one grid.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pytest
from PIL import Image

from nonogram.admin.book_kdp import unpaired_interior_page_count
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin import book_pdf_generator
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.export import pdf, png
from nonogram.export.layout import compute_answer_page_layout
from nonogram.export.png import render_answer_page
from nonogram.limits import MAX_SIZE

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out rather than imported.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4

#: FR-042's caption rule, restated here: the number, an em dash (U+2014) with
#: a space either side, and the title.
CAPTION = "Puzzle {number} — {title}"

#: FR-042's two tilings — still ``book_answer_key``'s own constants, written
#: out here rather than imported (the module docstring's own rule).
SIX_UP = 6
FOUR_UP = 4

#: INV-011's threshold: an answer longer than this on its longest side takes
#: its page down to :data:`FOUR_UP`.
SIX_UP_LONGEST_SIDE = 20


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book() -> Book:
    """A book on the Book 1 profile, as a ``books`` row carries it."""
    return Book(
        book_id="book-134",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="A test book.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(BOOK1_WIDTH_MM),
        trim_height_cm=_cm(BOOK1_HEIGHT_MM),
        gutter_margin_cm=_cm(GUTTER_MM),
        outside_margin_cm=_cm(OUTSIDE_MM),
    )


def _grid(columns: int, rows: int, depth: int = 3, mark: int = 0) -> list:
    """A solved grid whose clues are ``depth`` entries deep, and that is its own.

    ``mark`` fills one extra cell in the bottom-right corner, at a position
    that varies with it, so two answers of the same extent are different
    pictures.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    grid = [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]
    grid[rows - 1][(columns - 1) - (mark % (columns - limit))] = True
    return grid


def _ink(page: Image.Image) -> np.ndarray:
    #: A pixel darker than this (0..255 grey) is ink.
    return np.asarray(page.convert("L")) < 128


# --------------------------------------------------------------------------
# EC-031's floor, and the rule that keeps it (book_answer_key + COMP-007 only)
# --------------------------------------------------------------------------

#: EC-031's floor on a printed answer cell, in millimetres — written out as
#: CARD-133's ``tests/property/test_book_answer_tiles.py`` writes it, because
#: nothing in ``nonogram.export.layout`` holds a cell up to it.
ANSWER_FLOOR_MM = 3.19

#: The first square answer whose six-up cell falls under that floor on the
#: Book 1 profile. INV-011 refuses it a six-up page.
FIRST_SIX_UP_BREACH = 25


class TestBookAnswerKey_SixUpRuleKeepsTheAnswerCellAboveTheFloor:
    """Why :data:`SIX_UP_LONGEST_SIDE` is a rule and not a preference (EC-031).

    ``book_answer_key``'s own docstring rests the 3.19 mm answer-cell floor on
    this module's capacity rule, because
    :func:`~nonogram.export.layout.compute_answer_page_layout` enforces no
    floor of its own — a 25x25 laid out six-up comes back undersized and no
    error is raised. Neither ``book_answer_key.py`` nor
    ``compute_answer_page_layout`` is touched by CARD-198 (G-5), so this link
    still holds exactly as CARD-133 and CARD-134 left it; nothing here is a
    claim about the book generator's current production path.
    """

    @staticmethod
    def _cell_mm(side: int, capacity: int, heading: Optional[str]) -> float:
        """The printed cell of one ``side`` x ``side`` answer on such a page."""
        layout = compute_answer_page_layout(
            [(side, side)], capacity, book_page_spec(_book(), 4), heading
        )
        return layout.tiles[0].cell_mm

    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_the_largest_answer_left_six_up_clears_the_floor(
        self, heading: Optional[str]
    ) -> None:
        """20 on the longest side, six-up: 3.97 mm bare, 3.84 mm under a heading."""
        assert self._cell_mm(SIX_UP_LONGEST_SIDE, SIX_UP, heading) >= ANSWER_FLOOR_MM

    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_an_answer_the_rule_refuses_six_up_would_have_broken_the_floor(
        self, heading: Optional[str]
    ) -> None:
        """25x25 six-up: 3.18 mm bare, 3.07 mm headed — and nothing raises."""
        assert self._cell_mm(FIRST_SIX_UP_BREACH, SIX_UP, heading) < ANSWER_FLOOR_MM

    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_the_four_up_page_the_rule_gives_it_instead_clears_the_floor(
        self, heading: Optional[str]
    ) -> None:
        """And the page INV-011 does give that answer is above the floor."""
        assert self._cell_mm(FIRST_SIX_UP_BREACH, FOUR_UP, heading) >= ANSWER_FLOOR_MM

    def test_the_threshold_is_conservative_and_this_is_by_how_much(self) -> None:
        """20 is not the tight bound, and the rationale must not read as one."""
        breaches = [
            side
            for side in range(SIX_UP_LONGEST_SIDE, MAX_SIZE + 1)
            if self._cell_mm(side, SIX_UP, "Easy") < ANSWER_FLOOR_MM
        ]
        assert breaches, "no square answer in range breaks the floor six-up"
        assert breaches[0] == FIRST_SIX_UP_BREACH
        assert SIX_UP_LONGEST_SIDE < breaches[0]


# --------------------------------------------------------------------------
# The caption separator's ink, drawn directly through COMP-007 (G-1a)
# --------------------------------------------------------------------------

#: A codepoint no typeface carries: the last of the BMP, permanently unassigned
#: by Unicode. Whatever face is in force rasterizes it to that face's
#: ``.notdef`` glyph, so it is the control every "is this character really
#: drawn?" question here is asked against.
UNMAPPED = "￿"


class TestBookAnswerKey_CaptionSeparatorIsADrawnGlyph:
    """AC-268's em dash is a *dash* on paper, not a ``.notdef`` box (G-1a).

    Drawn straight through :func:`~nonogram.export.png.render_answer_page`,
    never through the book generator — CARD-198 did not touch that function,
    and this test makes no claim about which production path still calls it.
    """

    #: Where the separator's ink must be wider than tall for a dash, and is
    #: not for a box. The packaged face measures roughly 11:1 for U+2014 and
    #: 0.6:1 for its ``.notdef``, so the threshold is nowhere near either.
    DASH_ASPECT = 3.0

    NAME = "Snowflake"
    NUMBER = 7

    @staticmethod
    def _page(caption: str) -> Image.Image:
        return render_answer_page(
            [(_grid(15, 15), caption)],
            SIX_UP,
            book_page_spec(_book(), 4),
        )

    @classmethod
    def _separator_ink(cls, separator: str) -> Tuple[int, int]:
        """The ``(width, height)`` in pixels of the ink ``separator`` adds."""
        drawn = _ink(cls._page(separator))
        blank = _ink(cls._page(""))
        mark = drawn != blank
        rows = np.flatnonzero(mark.any(axis=1))
        columns = np.flatnonzero(mark.any(axis=0))
        assert rows.size and columns.size, f"{separator!r} drew nothing at all"
        return (
            int(columns[-1] - columns[0] + 1),
            int(rows[-1] - rows[0] + 1),
        )

    def test_the_em_dash_is_ink_an_unmapped_codepoint_would_not_have_made(
        self,
    ) -> None:
        caption = CAPTION.format(number=self.NUMBER, title=self.NAME)
        tofu = caption.replace("—", UNMAPPED)
        assert tofu != caption, "the caption under test carries no em dash"

        assert self._page(caption).tobytes() != self._page(tofu).tobytes()

    def test_the_separator_prints_as_a_bar_and_the_unmapped_one_does_not(
        self,
    ) -> None:
        dash_width, dash_height = self._separator_ink("—")
        box_width, box_height = self._separator_ink(UNMAPPED)

        assert dash_width >= self.DASH_ASPECT * dash_height, (
            f"U+2014 drew {dash_width}x{dash_height} px — not a dash's flat bar"
        )
        assert box_width < self.DASH_ASPECT * box_height, (
            f"U+FFFF drew {box_width}x{box_height} px — the control is not a box"
        )

    def test_the_face_is_the_packaged_one_the_pdf_header_already_uses(self) -> None:
        assert (png.FONT_PACKAGE, png.FONT_RESOURCE) == (
            pdf.FONT_PACKAGE,
            pdf.FONT_RESOURCE,
        )


# --------------------------------------------------------------------------
# The two answer-extent readers, cross-checked
# --------------------------------------------------------------------------


class TestBookAnswerKey_TheExtentReaderAgreesWithTheRenderer:
    """The two grid measurements the answer path depends on, compared.

    ``book_pdf_generator._answer_extent`` is kept by CARD-198 for validation
    only (nothing packs by it any longer) and ``png._answer_extent`` decides
    how :func:`~nonogram.export.png.render_answer_page` measures a page it is
    handed. They remain two implementations on purpose — ``export/`` exposes
    no public call that measures a grid, and the project reimplements rather
    than imports across a capability boundary — so nothing but this test
    keeps them from drifting into two different answers about one grid.
    """

    @staticmethod
    def _payload(grid: object):
        """A payload carrying ``grid``, exactly as the generator builds one."""
        return BookPDFGenerator._payload({"grid": grid})

    @pytest.mark.parametrize("columns,rows", [(10, 10), (20, 15), (15, 20), (30, 30)])
    def test_both_readers_measure_a_well_formed_grid_the_same_way(
        self, columns: int, rows: int
    ) -> None:
        grid = _grid(columns, rows, mark=1)

        assert book_pdf_generator._answer_extent(self._payload(grid), 1) == (
            columns,
            rows,
        )
        assert png._answer_extent(grid, 0) == (columns, rows)

    @pytest.mark.parametrize(
        "grid",
        [
            pytest.param([[True] * 15, [True] * 14], id="ragged"),
            pytest.param([], id="no-rows"),
            pytest.param([[]], id="one-empty-row"),
        ],
    )
    def test_a_grid_the_generator_refuses_is_refused_by_the_renderer_too(
        self, grid: list
    ) -> None:
        with pytest.raises(ValueError):
            book_pdf_generator._answer_extent(self._payload(grid), 4)

        with pytest.raises(ValueError):
            render_answer_page([(grid, "")], SIX_UP, book_page_spec(_book(), 4))


# --------------------------------------------------------------------------
# AC-6 (CARD-198) — the sheet-free count still rejects a malformed grid
# --------------------------------------------------------------------------


class TestBookKdp_UnpairedCountStillRejectsAMalformedGrid:
    """AC-6 — ``unpaired_interior_page_count`` still raises on a bad grid.

    CARD-198 dropped this function's ``Answer``/``pack_answer_pages`` import
    (the packing walk it no longer needs) but kept its per-row rectangle
    check (``_grid_extent``, book_kdp.py), because ``app.py``'s
    ``_is_an_unpackable_row`` depends on this function refusing exactly the
    rows the generator's own eager validation refuses (G-6). This is the
    one case this function exists for: a book whose stored print
    specification cannot be laid out at all has no sheet to measure
    pairing on, so Finalise falls back to this sheet-free upper bound — and
    that fallback must still name a malformed row rather than silently
    returning a plausible-looking count.
    """

    @staticmethod
    def _row(grid: object, number: int) -> dict:
        return {
            "id": f"p{number}",
            "grid": grid,
            "difficulty_tier": "easy",
        }

    def test_a_ragged_grid_among_well_formed_ones_is_refused(self) -> None:
        good = _grid(10, 10, mark=1)
        ragged = [row[:] for row in _grid(10, 10, mark=2)]
        ragged[3] = ragged[3][:-1]

        rows = [self._row(good, 1), self._row(ragged, 2)]

        with pytest.raises(ValueError, match="2's answer"):
            unpaired_interior_page_count(rows)

    @pytest.mark.parametrize("grid", [[], [[]]], ids=["no-rows", "one-empty-row"])
    def test_an_empty_grid_is_refused(self, grid: object) -> None:
        rows = [self._row(grid, 1)]

        with pytest.raises(ValueError):
            unpaired_interior_page_count(rows)

    def test_the_same_book_well_formed_is_not_refused(self) -> None:
        """The control: nothing about this corpus is refused on its own."""
        rows = [self._row(_grid(10, 10, mark=index), index) for index in range(1, 3)]

        assert unpaired_interior_page_count(rows) > 0
