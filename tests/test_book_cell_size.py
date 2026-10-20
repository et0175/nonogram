"""CARD-225 — one cell size per grid size across the whole book (NFR-008 amended).

    AC-1  TestBookCellSize_SameGridSizeSameCell
    AC-2  TestBookCellSize_FitsTheDeepestMember                 (= NFR-008's AC-369)
    AC-3  TestBookCellSize_HoldsTheSevenAndAHalfMillimetreCap
    AC-4  TestBookCellSize_SharedPageTakesTheSmaller
    AC-5  TestBookCellSize_SoleMemberOfItsSize
    AC-6  TestBookCellSize_BelowFloorFlagFollowsTheSharedSize    (= NFR-008's AC-371)
    AC-7  TestBookCellSize_IsOrderIndependent
    AC-370  TestBookCell_ThirtyByThirtyDepthTenHoldsTheAmendedFloor
            — the pin NFR-008's 2026-10-17 amendment newly owed this card, named on
              no other card, and the control CARD-222's review cycle 2 measured as a
              0.22 mm straddle rather than a boundary
    the cost  TestBookCellSize_TheCostOfABookWideCell

NFR-008 as amended 2026-10-17 (commit ``91609aa``): the printed cell is chosen
**per grid size per book**, fitted to the deepest-clued member of that grid
size, inside a 4.75..7.5 mm band. So every 20x20 in one book prints at one
cell however its clue columns differ — the owner's issue 4.

What the evidence is
--------------------
Every cell AC-1..AC-5 assert is read off the **rendered interior**, through
CARD-116's ``tests/helpers/page_ink`` (and ``two_up_ink`` for the shared page),
never asked of the code that produced it. The expected millimetres are
NFR-008's and FR-030's definitions written out again here in floating point
over CON-018's profile stated in inches (:func:`_own_fit_mm`) — a second
implementation, so this file never re-derives a figure with the function it is
testing. Nothing here imports ``compute_layout``, ``book_cell_mm`` or
``book_cell_sizes`` for an *expected* value; the two places that do import
them (the order-independence guard and the cost corpus) say why at the import.

What "the same cell" means in ink, and the bound on it
------------------------------------------------------
Two members of one grid size are laid out with the *identical* cap, so
``Layout.page.cell_mm`` is the same float for both. Their grids' **edges** are
each rounded to a whole device pixel independently, and a book page's drawing
is centred across the usable width, so a measured grid can be one pixel wider
than its neighbour's at the same cell. The tolerance below is therefore exactly
that: one device pixel spread over the grid's own columns
(:func:`_one_pixel_mm`) — 0.004 mm on a 20-wide grid — rather than the 0.05 mm
``tests/test_book_pdf.py`` uses for a single page's absolute figure. **It is
two orders of magnitude tighter than the spread this card removes**: the three
20x20s of AC-1 print at 7.50, 7.06 and 6.35 mm without it.
"""

from __future__ import annotations

import functools
import random
import re
import statistics
from typing import Any, Dict, List, Tuple

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import Book, BookManager, BookMetadata
from nonogram.admin.book_page_spec import FLOOR_MM
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.page_ink import drawing_of
from tests.helpers.two_up_ink import drawings_of
from tests.test_book_floor import Panel, clues_of, dotted_grid

# --------------------------------------------------------------------------
# CON-018's Book 1 profile in millimetres, written out rather than imported —
# the same figures tests/test_book_pdf.py and tests/test_book_pdf_two_up.py
# write out. CON-018 as amended 2026-10-17 (CARD-222): outside 0.5 in, top
# 0.55 in, bottom 0.47 in, the gutter deliberately still KDP's 0.5 in.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4

#: The title band above each puzzle (TERM-028), and NFR-008's standard cell.
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5

#: NFR-008's floor, written out — the one figure this file states twice,
#: because AC-370 is about ``FLOOR_MM``'s own value and a test that read the
#: constant for both sides of the comparison could not pin it.
AMENDED_FLOOR_MM = 4.75

#: The floor NFR-008 retired on 2026-10-17, kept only so AC-370 can say what
#: it says: "where the retired 4.8 mm floor would have refused it".
RETIRED_FLOOR_MM = 4.8

#: FR-040's two-up minimum: two puzzles share a page only at this cell or more.
TWO_UP_MINIMUM_MM = 7.0

#: The page's usable width — 190.5 mm on Book 1 since the margin amendment.
USABLE_WIDTH_MM = BOOK1_WIDTH_MM - GUTTER_MM - OUTSIDE_MM
USABLE_HEIGHT_MM = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - BAND_MM

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = 300 / 25.4

#: Interior page 1 of the **puzzle** section on a one-level book: 1-2 the
#: guide (CARD-201), 3 the table of contents (CARD-200), 4 the level divider
#: (CARD-128). Spelled out here as ``tests/test_book_pdf.py`` spells it out.
FIRST_PUZZLE_PAGE = 5


def _own_fit_mm(columns: int, rows: int, row_gutter: int, column_gutter: int) -> float:
    """What **one** puzzle alone would print at: FR-030's fit, written out.

    ``min(standard cell, usable width / drawing columns, usable height /
    drawing rows)`` — the figure that was the book cell before this card, and
    which is now only one term of it. A second implementation: no layout
    function is consulted.
    """
    return min(
        STANDARD_CELL_MM,
        USABLE_WIDTH_MM / (row_gutter + columns),
        USABLE_HEIGHT_MM / (column_gutter + rows),
    )


def _book_cell_mm(members: List[Tuple[int, int, int, int]], of: int = 0) -> float:
    """NFR-008 as amended, written out: the minimum own fit within a grid size.

    ``members`` is ``(columns, rows, row gutter, column gutter)`` per member of
    the book; ``of`` indexes the member whose printed cell is wanted. The
    minimum is taken over the members **of that member's grid size** only.
    """
    columns, rows = members[of][0], members[of][1]
    return min(
        _own_fit_mm(*member)
        for member in members
        if (member[0], member[1]) == (columns, rows)
    )


def _one_pixel_mm(columns: int) -> float:
    """One device pixel of grid width, in mm of cell — this file's tolerance.

    A measured cell is ``grid width / columns`` and each of the grid's two
    edges rounds to a whole pixel, so two members of one grid size can read one
    pixel apart however exactly their cells agree. Anything larger than this is
    a real difference in cell size.
    """
    return 1 / PX_PER_MM / columns


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _book(book_id: str = "card-225") -> Book:
    """A book on CON-018's Book 1 profile, with no custom puzzle titles."""
    return Book(
        book_id=book_id,
        metadata=BookMetadata(
            title="One Cell Per Size",
            description="The book CARD-225's cells are measured on.",
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


def _puzzle(
    columns: int,
    rows: int,
    row_gutter: int,
    column_gutter: int,
    *,
    name: str,
    tier: str = "easy",
) -> Dict[str, Any]:
    """One book puzzle whose two clue gutters are exactly that deep.

    ``dotted_grid`` (``tests/test_book_floor.py``) rather than
    ``book_corpus.puzzle``: the gutters have to be settable **independently**,
    because the row gutter is what decides a wide grid's cell and the column
    gutter is what decides a tall one's, and a fixture forced to make them
    equal cannot build the shallow 20x10 this card's own AC-4 needs.
    """
    grid = dotted_grid(columns, rows, row_gutter, column_gutter)
    clue_rows, clue_columns = clues_of(grid)
    assert max(len(line) for line in clue_rows) == row_gutter
    assert max(len(line) for line in clue_columns) == column_gutter
    return {
        "id": name,
        "grid": grid,
        "clues_rows": clue_rows,
        "clues_cols": clue_columns,
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": tier,
    }


def _interior(puzzles: List[Dict[str, Any]], book: Book | None = None) -> List[Any]:
    """The book's interior pages; ``pages[n - 1]`` is interior page ``n``."""
    return BookPDFGenerator(book if book is not None else _book()).interior_pages(puzzles)


def _drawn_cells_mm(pages: List[Any], count: int) -> List[float]:
    """The cell each of the first ``count`` puzzle pages draws, off the ink."""
    return [
        _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1 + index]).cell)
        for index in range(count)
    ]


# --------------------------------------------------------------------------
# AC-1 — one grid size, one cell, measured off the ink
# --------------------------------------------------------------------------


class TestBookCellSize_SameGridSizeSameCell:
    """AC-1: three 20x20s with 3-, 7- and 10-deep row gutters print one cell.

    The owner's issue 4 exactly: before this card the three drew 7.50, 7.06 and
    6.35 mm, so grids of the same size did not match across pages.
    """

    #: ``(columns, rows, row gutter, column gutter)``. The column gutter is
    #: held at 2 so the *width* term binds for all three and the only thing
    #: separating them is the row gutter — 23, 27 and 30 cells across.
    MEMBERS = [(20, 20, 3, 2), (20, 20, 7, 2), (20, 20, 10, 2)]

    def _puzzles(self) -> List[Dict[str, Any]]:
        return [
            _puzzle(*member, name=f"Twenty-{index}")
            for index, member in enumerate(self.MEMBERS)
        ]

    def test_the_premise_is_that_they_would_not_have_matched(self) -> None:
        """Without the rule these three print three different cells.

        The control this class rests on: if the three own fits were already
        equal, every assertion below would hold whatever the code did.
        """
        own = [_own_fit_mm(*member) for member in self.MEMBERS]

        assert own == pytest.approx([7.5, 190.5 / 27, 190.5 / 30], abs=1e-9)
        assert max(own) - min(own) > 1.1, own

    def test_every_twenty_by_twenty_is_drawn_at_the_same_cell(self) -> None:
        pages = _interior(self._puzzles())

        drawn = _drawn_cells_mm(pages, len(self.MEMBERS))

        spread = max(drawn) - min(drawn)
        assert spread <= _one_pixel_mm(20), drawn

    def test_that_cell_is_the_deepest_members_own_fit(self) -> None:
        pages = _interior(self._puzzles())

        drawn = _drawn_cells_mm(pages, len(self.MEMBERS))

        expected = USABLE_WIDTH_MM / 30  # the 10-deep member's own fit
        assert expected == pytest.approx(6.35, abs=5e-4)
        for cell in drawn:
            assert cell == pytest.approx(expected, abs=_one_pixel_mm(20)), drawn

    def test_the_size_is_the_books_and_not_one_levels(self) -> None:
        """The deep member in **another level** still decides for all of them.

        A grid size can straddle FR-041's levels, and the puzzle section plans
        each level's pages in its own walk (``puzzle_section``) — so this is
        the claim's substance on the single-page path: three 20x20s, two
        graded Easy and one Hard, all printed at the Hard one's cell.

        **What it does not do is discriminate the per-level mutant, and the
        committed docstring used to say it did** (review cycle 1, F-005).
        Re-measured: with ``puzzle_section``'s walk handed
        ``self.cell_sizes(payloads[start:end])`` instead of the book's map,
        this test still **passes** — 1 failed, 42 passed over this file, and
        the one failure is
        :meth:`TestBookCellSize_SharedPageTakesTheSmaller.test_the_pair_is_capped_by_a_member_in_another_level`.
        The reason is mechanical: a book's **single** pages are drawn from
        ``SectionPlan.cell_sizes`` in ``interior_stream`` and never see the
        slice at all, so only the **pairing** path can observe a per-level
        map. The two tests are a pair — this one pins what the rule means for
        the reader, that one is the only guard that can see it broken — and
        naming the second here is what makes them legible as one.
        """
        puzzles = [
            _puzzle(20, 20, 3, 2, name="Easy-shallow", tier="easy"),
            _puzzle(20, 20, 4, 2, name="Easy-shallower", tier="easy"),
            _puzzle(20, 20, 10, 2, name="Hard-deep", tier="hard"),
        ]

        pages = _interior(puzzles)
        # Two levels, so two dividers: easy's divider at 4, its two pages at
        # 5-6, hard's divider at 7, its page at 8.
        easy = [_mm(drawing_of(pages[index]).cell) for index in (4, 5)]
        hard = _mm(drawing_of(pages[7]).cell)

        assert max(easy + [hard]) - min(easy + [hard]) <= _one_pixel_mm(20), (
            easy,
            hard,
        )
        assert hard == pytest.approx(USABLE_WIDTH_MM / 30, abs=_one_pixel_mm(20))

    def test_each_page_still_draws_its_own_grid_unrotated(self) -> None:
        """G-3/ADR-0033/R1: a drawing size changed, not a puzzle."""
        pages = _interior(self._puzzles())

        for index in range(len(self.MEMBERS)):
            drawing = drawing_of(pages[FIRST_PUZZLE_PAGE - 1 + index])
            assert (drawing.columns, drawing.rows) == (20, 20)


# --------------------------------------------------------------------------
# AC-2 / NFR-008's AC-369 — the deepest clue stack decides
# --------------------------------------------------------------------------


class TestBookCellSize_FitsTheDeepestMember:
    """AC-2 (NFR-008's AC-369): two 30x30s, 5- and 9-deep, both print 4.885 mm.

    The registry states it as a criterion of NFR-008 itself: "both puzzles
    print at 4.885 mm — the cell the 9-deep member fits at". So the shared
    figure is neither larger (the 9-deep member would overflow) nor smaller
    (nothing is shrunk further than it has to be).
    """

    SHALLOW = (30, 30, 5, 5)
    DEEP = (30, 30, 9, 9)

    def _puzzles(self) -> List[Dict[str, Any]]:
        return [
            _puzzle(*self.SHALLOW, name="Five-deep"),
            _puzzle(*self.DEEP, name="Nine-deep"),
        ]

    def test_both_print_at_the_nine_deep_members_cell(self) -> None:
        pages = _interior(self._puzzles())

        drawn = _drawn_cells_mm(pages, 2)

        expected = USABLE_WIDTH_MM / 39
        assert expected == pytest.approx(4.885, abs=5e-4)  # the registry's figure
        for cell in drawn:
            assert cell == pytest.approx(expected, abs=_one_pixel_mm(30)), drawn

    def test_it_is_the_deepest_members_own_fit_and_not_smaller(self) -> None:
        """Nothing is shrunk further than the deepest member needs."""
        pages = _interior(self._puzzles())

        drawn = _drawn_cells_mm(pages, 2)

        alone = _own_fit_mm(*self.DEEP)
        for cell in drawn:
            assert cell == pytest.approx(alone, abs=_one_pixel_mm(30)), (drawn, alone)

    def test_the_shallow_member_gave_up_the_difference(self) -> None:
        """The cost, stated: the 5-deep member printed 5.443 mm alone."""
        pages = _interior(self._puzzles())

        shallow_drawn = _drawn_cells_mm(pages, 1)[0]

        alone = _own_fit_mm(*self.SHALLOW)
        assert alone == pytest.approx(USABLE_WIDTH_MM / 35, abs=1e-9)
        assert alone == pytest.approx(5.443, abs=5e-4)
        assert alone - shallow_drawn == pytest.approx(0.558, abs=0.005)


# --------------------------------------------------------------------------
# AC-3 — the flat 7.5 mm cap stands (G-1)
# --------------------------------------------------------------------------


class TestBookCellSize_HoldsTheSevenAndAHalfMillimetreCap:
    """AC-3: a book of small grids with shallow clues prints 7.5 mm, not more.

    This card changes how the figure is *chosen*, never what NFR-008 allows:
    the per-grid-size figure is a **minimum** over members, so it can only move
    a cell down, and the cap is still the ceiling every one of them meets.
    """

    MEMBERS = [(15, 15, 1, 1), (15, 15, 7, 7), (10, 10, 1, 1)]

    def _puzzles(self) -> List[Dict[str, Any]]:
        return [
            _puzzle(*member, name=f"Small-{index}")
            for index, member in enumerate(self.MEMBERS)
        ]

    def test_every_page_prints_the_standard_cell(self) -> None:
        pages = _interior(self._puzzles())

        drawn = _drawn_cells_mm(pages, len(self.MEMBERS))

        for cell in drawn:
            assert cell == pytest.approx(STANDARD_CELL_MM, abs=0.01), drawn

    def test_the_deepest_member_of_the_size_also_fits_above_the_cap(self) -> None:
        """The premise: the cap, not the page, is what holds all three.

        The 7-deep 15x15 fits 8.66 mm on this sheet, so if this card's minimum
        were taken over page fits *before* the cap it would still read 7.5 —
        which is why the assertion above cannot pass by the cap being bypassed.
        """
        assert USABLE_WIDTH_MM / 22 > STANDARD_CELL_MM
        assert _own_fit_mm(15, 15, 7, 7) == STANDARD_CELL_MM

    def test_no_page_prints_larger_than_the_cap(self) -> None:
        pages = _interior(self._puzzles())

        drawn = _drawn_cells_mm(pages, len(self.MEMBERS))

        for cell in drawn:
            assert cell <= STANDARD_CELL_MM + 0.01, drawn


# --------------------------------------------------------------------------
# AC-4 — a shared page takes the smaller of the two book sizes
# --------------------------------------------------------------------------


class TestBookCellSize_SharedPageTakesTheSmaller:
    """AC-4: two puzzles of different grid sizes on one page, both at the smaller.

    The owner's rule for a two-up page, and what makes the two grids line up
    (CARD-226 then aligns the slots around it). The pair here is a 20x10 and a
    15x10: the 20x10 grid size also holds a 6-deep member, so its book cell is
    7.327 mm, while the 15x10 is held at the 7.5 mm cap. Both slots print
    7.327 mm; before this card the pair shared 7.5 mm, fitted from the pair
    alone.
    """

    #: The pair, in print order, then the deep member that decides the 20x10's
    #: book cell. All one tier, so the walk offers the first two to each other
    #: (INV-010) and the third prints alone.
    PAIR_UPPER = (20, 10, 2, 2)
    PAIR_LOWER = (15, 10, 2, 2)
    DEEP = (20, 10, 6, 2)

    def _puzzles(self) -> List[Dict[str, Any]]:
        return [
            _puzzle(*self.PAIR_UPPER, name="Upper"),
            _puzzle(*self.PAIR_LOWER, name="Lower"),
            _puzzle(*self.DEEP, name="Deep"),
        ]

    #: The 20x10's book cell: 26 cells across the sheet (the 6-deep member).
    SHARED_MM = USABLE_WIDTH_MM / 26

    def test_the_premise_is_a_pair_that_would_have_shared_the_cap(self) -> None:
        """Without the rule the pair fits 7.5 mm, so the cap has to bind."""
        assert _own_fit_mm(*self.PAIR_UPPER) == STANDARD_CELL_MM
        assert _own_fit_mm(*self.PAIR_LOWER) == STANDARD_CELL_MM
        assert self.SHARED_MM == pytest.approx(7.327, abs=5e-4)
        assert TWO_UP_MINIMUM_MM < self.SHARED_MM < STANDARD_CELL_MM

    def test_the_two_puzzles_really_do_share_a_page(self) -> None:
        pages = _interior(self._puzzles())

        drawings = drawings_of(pages[FIRST_PUZZLE_PAGE - 1])

        assert len(drawings) == 2
        assert [(d.columns, d.rows) for d in drawings] == [(20, 10), (15, 10)]

    def test_both_slots_are_drawn_at_the_smaller_of_the_two_book_sizes(self) -> None:
        pages = _interior(self._puzzles())

        drawings = drawings_of(pages[FIRST_PUZZLE_PAGE - 1])

        for drawing in drawings:
            assert _mm(drawing.cell) == pytest.approx(
                self.SHARED_MM, abs=_one_pixel_mm(drawing.columns)
            ), [_mm(d.cell) for d in drawings]

    def test_the_two_slots_agree_with_each_other(self) -> None:
        """The point of the rule: the grids line up because the cells match."""
        pages = _interior(self._puzzles())

        upper, lower = drawings_of(pages[FIRST_PUZZLE_PAGE - 1])

        assert abs(_mm(upper.cell) - _mm(lower.cell)) <= _one_pixel_mm(15)

    def test_the_pair_is_capped_by_a_member_in_another_level(self) -> None:
        """The deep member moved to another level still caps the pair.

        FR-041 cuts the pairing walk level by level (``puzzle_section``), so a
        pair is offered by a walk that can only see its own level's puzzles.
        The cap it is offered must still be the **book's**: with the 6-deep
        20x10 graded Hard, a per-level map would read the Easy level's only
        20x10 as shallow and share the 7.5 mm cap again — the two grids would
        line up with each other and with nothing else in the book. Added
        because the per-level mutant (M6) survived every other case here: the
        single pages are drawn from ``SectionPlan.cell_sizes`` and never see
        the slice, so the pairing path is the only place this is observable.

        **This is the only test in the repository that kills M6** (re-measured
        in review cycle 1, F-005: 1 failed, 42 passed over this file, the
        failure being this one). Its pair is
        :meth:`TestBookCellSize_SameGridSizeSameCell.test_the_size_is_the_books_and_not_one_levels`,
        which states the same rule on the single-page path, where it is the
        claim's substance and cannot be a guard.
        """
        puzzles = [
            _puzzle(*self.PAIR_UPPER, name="Upper", tier="easy"),
            _puzzle(*self.PAIR_LOWER, name="Lower", tier="easy"),
            _puzzle(*self.DEEP, name="Deep", tier="hard"),
        ]

        pages = _interior(puzzles)
        drawings = drawings_of(pages[FIRST_PUZZLE_PAGE - 1])

        assert len(drawings) == 2, "the pair must still share a page"
        for drawing in drawings:
            assert _mm(drawing.cell) == pytest.approx(
                self.SHARED_MM, abs=_one_pixel_mm(drawing.columns)
            ), [_mm(d.cell) for d in drawings]

    def test_a_pair_whose_book_cell_falls_under_the_two_up_minimum_is_refused(
        self,
    ) -> None:
        """FR-040's 7.0 mm minimum is applied to the **book's** cell (F-8).

        The declared behaviour change this card's failure matrix records: the
        same pair that shares a page above shares none once the 20x10 grid
        size holds a 10-deep member, because its book cell is then 6.35 mm and
        FR-040 admits no two-up page below 7.0 mm. The two puzzles print on
        two pages instead — which costs a page and is the honest consequence
        of "both members print at the same cell as every other puzzle of their
        size". Nothing here is a *new* rule: TWO_UP_MIN_CELL_MM is unchanged
        and is still what refuses it.
        """
        deepest = (20, 10, 10, 2)
        assert _own_fit_mm(*deepest) == pytest.approx(USABLE_WIDTH_MM / 30, abs=1e-9)
        assert _own_fit_mm(*deepest) < TWO_UP_MINIMUM_MM
        puzzles = [
            _puzzle(*self.PAIR_UPPER, name="Upper"),
            _puzzle(*self.PAIR_LOWER, name="Lower"),
            _puzzle(*deepest, name="Deepest"),
        ]

        # The control, in this same test: the identical two puzzles in a book
        # without the deep member DO share a page, so the refusal below is the
        # deep member's doing and not something about this pair.
        assert len(drawings_of(_interior(puzzles[:2])[FIRST_PUZZLE_PAGE - 1])) == 2

        pages = _interior(puzzles)

        # Three single pages, not a pair and a single: every one of them
        # measures as one drawing.
        for index in range(3):
            drawing = drawing_of(pages[FIRST_PUZZLE_PAGE - 1 + index])
            assert (drawing.columns, drawing.rows) in {(20, 10), (15, 10)}
        twenties = [
            _mm(drawing_of(pages[FIRST_PUZZLE_PAGE - 1 + index]).cell)
            for index in (0, 2)
        ]
        for cell in twenties:
            assert cell == pytest.approx(USABLE_WIDTH_MM / 30, abs=_one_pixel_mm(20))

    def test_the_member_that_decided_it_prints_at_that_cell_alone(self) -> None:
        pages = _interior(self._puzzles())

        deep = drawing_of(pages[FIRST_PUZZLE_PAGE])

        assert (deep.columns, deep.rows) == (20, 10)
        assert _mm(deep.cell) == pytest.approx(self.SHARED_MM, abs=_one_pixel_mm(20))


# --------------------------------------------------------------------------
# AC-5 — a grid size with one member degenerates to today's fit
# --------------------------------------------------------------------------


class TestBookCellSize_SoleMemberOfItsSize:
    """AC-5: the only 30x30 in a book prints exactly what it printed before.

    Not a special case in the code: a minimum over one member *is* that
    member, so the rule degenerates by construction rather than by a branch.
    """

    SOLE = (30, 30, 9, 9)
    #: Other grid sizes, including a deeply-clued one, so the book is not
    #: trivially one puzzle and a neighbouring size cannot reach across.
    OTHERS = [(20, 20, 10, 2), (20, 20, 3, 2), (25, 25, 12, 4)]

    def _puzzles(self) -> List[Dict[str, Any]]:
        members = [self.SOLE, *self.OTHERS]
        return [
            _puzzle(*member, name=f"Member-{index}")
            for index, member in enumerate(members)
        ]

    def test_it_prints_its_own_page_fit(self) -> None:
        pages = _interior(self._puzzles())

        drawn = _drawn_cells_mm(pages, 1)[0]

        assert drawn == pytest.approx(_own_fit_mm(*self.SOLE), abs=_one_pixel_mm(30))
        assert drawn == pytest.approx(USABLE_WIDTH_MM / 39, abs=_one_pixel_mm(30))

    def test_a_deeper_puzzle_of_a_different_size_does_not_reach_it(self) -> None:
        """A 25x25 at 12 deep prints 5.149 mm and the 30x30 keeps 4.885.

        The grid size is the key: a deeper member of *another* size shares no
        cell with this one, and a rule that keyed on the longest side alone —
        or on nothing — would have dragged this page down with it.
        """
        pages = _interior(self._puzzles())

        thirty = _drawn_cells_mm(pages, 1)[0]

        assert _own_fit_mm(*self.OTHERS[-1]) == pytest.approx(5.149, abs=5e-4)
        assert thirty == pytest.approx(USABLE_WIDTH_MM / 39, abs=_one_pixel_mm(30))
        assert thirty < _own_fit_mm(*self.OTHERS[-1])


# --------------------------------------------------------------------------
# AC-6 / NFR-008's AC-371 — the below-floor flag follows the shared size
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    """The panel in in-memory mode, with a book manager of its own.

    The fixture ``tests/test_book_floor.py`` and
    ``tests/test_book_select_floor_tiles.py`` both use, spelled out here as
    the second of those spells it out, so this file's tests stand on their
    own; the module singletons are emptied on both sides so no book made here
    can be inherited by the next test's panel.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    book_manager_module._book_manager = BookManager(session_factory=None)
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None
    book_manager_module._book_manager = BookManager(session_factory=None)


@pytest.fixture
def panel(admin_app):
    return Panel(admin_app)


def _below_floor_count(panel, book_id) -> int:
    """The finalise summary's below-the-floor figure, read off the page.

    The same attribute ``tests/test_book_select_floor_tiles.py`` reads it
    from, re-stated here rather than imported, as this file re-states every
    other figure it uses.
    """
    response = panel.client.get(f"/book/{book_id}/finalize")
    assert response.status_code == 200
    counted = re.search(
        r'data-below-floor-count="(\d+)"', response.get_data(as_text=True)
    )
    assert counted is not None, "the finalise summary reports no below-floor figure"
    return int(counted.group(1))


class TestBookCellSize_BelowFloorFlagFollowsTheSharedSize:
    """AC-6 (NFR-008's AC-371): the flag describes what is **printed**.

    A 30x30 at clue depth 13 prints 4.430 mm — the depth random 30x30 grids at
    density 0.5 reach — which is below NFR-008's 4.75 mm floor, so FR-031's
    stored override is the only way it joins a book (AC-371). Once it has,
    **every** 30x30 in that book prints at 4.430 mm, and the flag is raised for
    all of them and not only for the one that forced it: a shallow 30x30 that
    clears the floor comfortably on its own is refused without an override of
    its own, and the finalise screen counts it.
    """

    #: 43 cells across the sheet: 4.4302 mm, the figure NFR-008's amendment
    #: note measures for clue depth 13.
    DEEP = (30, 30, 13, 5)
    #: 35 cells across: 5.4429 mm, comfortably above the floor alone.
    SHALLOW = (30, 30, 5, 5)

    def test_the_premise_is_one_puzzle_either_side_of_the_floor_alone(self) -> None:
        assert _own_fit_mm(*self.DEEP) == pytest.approx(USABLE_WIDTH_MM / 43, abs=1e-9)
        assert _own_fit_mm(*self.DEEP) == pytest.approx(4.430, abs=5e-4)
        assert _own_fit_mm(*self.DEEP) < AMENDED_FLOOR_MM
        assert _own_fit_mm(*self.SHALLOW) == pytest.approx(5.443, abs=5e-4)
        assert _own_fit_mm(*self.SHALLOW) > AMENDED_FLOOR_MM

    def _stored(self, panel) -> Tuple[str, str, str]:
        deep = panel.puzzle(*self.DEEP)
        shallow = panel.puzzle(*self.SHALLOW)
        return panel.book(), deep, shallow

    def test_the_deep_puzzle_needs_fr031s_stored_override_to_join(self, panel) -> None:
        """AC-371 itself: submitted with no override, it is not added."""
        book_id, deep, _ = self._stored(panel)

        assert panel.books.add_puzzles_to_book(book_id, [deep]) is True
        assert panel.ids_of(book_id) == []

        refusal, = panel.books.below_floor(book_id, [deep])
        assert refusal.cell_mm == pytest.approx(4.430, abs=5e-4)

    def test_the_shallow_puzzle_is_refused_once_the_deep_one_is_a_member(
        self, panel
    ) -> None:
        """AC-6's own clause: the flag is raised for the one that did not force it."""
        book_id, deep, shallow = self._stored(panel)
        panel.books.add_puzzles_to_book(book_id, [deep], [deep])
        assert panel.ids_of(book_id) == [deep]

        refusals = panel.books.below_floor(book_id, [shallow])

        assert [r.puzzle_id for r in refusals] == [shallow]
        assert refusals[0].cell_mm == pytest.approx(4.430, abs=5e-4), (
            "the flag must carry the cell the page really prints, not the "
            "5.443 mm this puzzle would have had to itself"
        )

    def test_it_is_not_refused_in_a_book_without_the_deep_member(self, panel) -> None:
        """The control: the refusal above is the deep member's doing.

        Without this, "the shallow puzzle is refused" would be satisfied by a
        floor that refuses every 30x30.
        """
        book_id, _, shallow = self._stored(panel)

        assert panel.books.below_floor(book_id, [shallow]) == []
        assert panel.books.add_puzzles_to_book(book_id, [shallow]) is True
        assert panel.ids_of(book_id) == [shallow]

    def test_both_members_are_counted_below_the_floor_on_the_finalise_screen(
        self, panel
    ) -> None:
        """The flag the owner actually sees (AC-187/AC-188), for **both**."""
        book_id, deep, shallow = self._stored(panel)
        panel.books.add_puzzles_to_book(book_id, [deep, shallow], [deep, shallow])
        assert sorted(panel.ids_of(book_id)) == sorted([deep, shallow])

        assert _below_floor_count(panel, book_id) == 2, (
            "the deep member and the shallow one both print at 4.430 mm, so "
            "both are below the floor"
        )

    def test_a_book_holding_only_the_shallow_member_counts_none(self, panel) -> None:
        """The same control at the screen: the count is not "every 30x30"."""
        book_id, _, shallow = self._stored(panel)
        panel.books.add_puzzles_to_book(book_id, [shallow])

        assert _below_floor_count(panel, book_id) == 0

    def test_the_printed_page_really_carries_the_flagged_cell(self) -> None:
        """The flag describes what is printed — so the ink is checked too."""
        pages = _interior(
            [
                _puzzle(*self.SHALLOW, name="Five-deep"),
                _puzzle(*self.DEEP, name="Thirteen-deep"),
            ]
        )

        drawn = _drawn_cells_mm(pages, 2)

        for cell in drawn:
            assert cell == pytest.approx(
                USABLE_WIDTH_MM / 43, abs=_one_pixel_mm(30)
            ), drawn
            assert cell < AMENDED_FLOOR_MM


# --------------------------------------------------------------------------
# AC-7 — the sizes are deterministic and order-independent
# --------------------------------------------------------------------------


class TestBookCellSize_IsOrderIndependent:
    """AC-7: the same book, computed twice, gives identical sizes.

    The one class that imports the computation itself: what is asserted here is
    a property *of* it (two calls, one answer), which cannot be stated about a
    second implementation — and the figures it compares are each other's, never
    an expected constant.
    """

    MEMBERS = [
        (20, 20, 3, 2),
        (30, 30, 9, 9),
        (20, 20, 10, 2),
        (15, 15, 1, 1),
        (30, 30, 5, 5),
        (25, 25, 12, 4),
    ]

    def _payloads(self, order: List[int]):
        generator = BookPDFGenerator(_book())
        puzzles = [
            _puzzle(*self.MEMBERS[index], name=f"Member-{index}") for index in order
        ]
        return generator, [generator._payload(puzzle) for puzzle in puzzles]

    def test_two_computations_of_one_book_are_identical(self) -> None:
        order = list(range(len(self.MEMBERS)))
        generator, payloads = self._payloads(order)

        first = generator.cell_sizes(payloads)
        second = generator.cell_sizes(payloads)

        assert first == second
        assert len(first) == 4, first  # 20x20, 30x30, 15x15, 25x25

    def test_the_order_the_puzzles_were_added_in_does_not_change_them(self) -> None:
        reference = None
        shuffler = random.Random(225)
        orders = [list(range(len(self.MEMBERS)))]
        while len(orders) < 12:
            order = list(range(len(self.MEMBERS)))
            shuffler.shuffle(order)
            if order not in orders:
                orders.append(order)

        for order in orders:
            generator, payloads = self._payloads(order)
            sizes = generator.cell_sizes(payloads)
            if reference is None:
                reference = sizes
            assert sizes == reference, order

        assert len(orders) == 12, "the corpus of orders must not shrink"

    def test_a_member_handed_over_twice_is_one_member(self) -> None:
        generator, payloads = self._payloads(list(range(len(self.MEMBERS))))

        once = generator.cell_sizes(payloads)
        twice = generator.cell_sizes(payloads + payloads)

        assert once == twice

    def test_the_rendered_pages_are_identical_across_two_exports(self) -> None:
        """Determinism where it is paid for: the same ink, twice."""
        puzzles = [
            _puzzle(*member, name=f"Member-{index}")
            for index, member in enumerate(self.MEMBERS)
        ]

        first = _interior(puzzles)
        second = _interior(puzzles)

        assert [page.tobytes() for page in first] == [
            page.tobytes() for page in second
        ]


# --------------------------------------------------------------------------
# AC-370 — the amended floor's missing lower pin (the inherited obligation)
# --------------------------------------------------------------------------


class TestBookCell_ThirtyByThirtyDepthTenHoldsTheAmendedFloor:
    """AC-370: a 30x30 at clue depth 10 prints 4.7625 mm and is **admitted**.

    NFR-008's amendment of 2026-10-17 lowered the floor from 4.8 mm to
    4.75 mm for one measured reason: the CON-018 margin change must cost no
    grid a clue-depth step. On the old margins a 30-wide grid first fell under
    4.8 mm at clue depth 11; on the new margins it first falls under 4.75 mm at
    that same depth 11. **The depth-10 case is what pays for the number**, and
    it is the test the amendment newly owed this card — named on no other.

    What this closes, and how far
    -----------------------------
    CARD-222's review cycle 2 measured ``FLOOR_MM`` as pinned tightly above and
    loosely below: the suite stayed fully green for any value in (4.54, 4.76],
    a **0.22 mm straddle**, so ``FLOOR_MM = 4.60`` shipped green while admitting
    cells NFR-008's own note calls "too small". The pair of cases below —
    depth 10 admitted, depth 11 refused — closes that interval to
    **(4.6463, 4.7625]**, which is 0.116 mm.

    **It is not closed further, and this docstring does not claim it is.**
    That interval is exactly what NFR-008's justification determines: the floor
    must admit depth 10 (4.7625 mm) and refuse depth 11 (4.6463 mm) on the
    amended margins, and no behaviour of this system distinguishes 4.70 from
    4.75. 4.75 is the owner's round choice inside the bracket, and a test that
    reported a tighter pin would be asserting something the requirement does
    not say.
    """

    #: ``(columns, rows, row gutter, column gutter)`` and the cell each prints.
    #: 40 and 41 cells across the sheet.
    DEPTH_TEN = (30, 30, 10, 10)
    DEPTH_ELEVEN = (30, 30, 11, 5)

    def test_depth_ten_prints_the_registrys_figure(self) -> None:
        pages = _interior([_puzzle(*self.DEPTH_TEN, name="Ten-deep")])

        drawn = _drawn_cells_mm(pages, 1)[0]

        assert USABLE_WIDTH_MM / 40 == pytest.approx(4.7625, abs=1e-9)
        assert drawn == pytest.approx(4.7625, abs=_one_pixel_mm(30)), drawn

    def test_depth_ten_is_at_or_above_the_amended_floor(self) -> None:
        """``FLOOR_MM <= 4.7625``: the side CARD-222's mutation already bounded."""
        assert _own_fit_mm(*self.DEPTH_TEN) >= FLOOR_MM
        assert FLOOR_MM <= 4.7625

    def test_the_retired_four_point_eight_floor_would_have_refused_it(self) -> None:
        """The whole of what the amendment bought: one clue-depth step."""
        assert _own_fit_mm(*self.DEPTH_TEN) < RETIRED_FLOOR_MM
        assert RETIRED_FLOOR_MM - _own_fit_mm(*self.DEPTH_TEN) == pytest.approx(
            0.0375, abs=1e-4
        )

    def test_depth_eleven_is_below_the_amended_floor(self) -> None:
        """``FLOOR_MM > 4.6463``: the lower pin that did not exist.

        This is the half the 0.22 mm straddle was missing. Without it
        ``FLOOR_MM = 4.64`` is a fully green suite.
        """
        assert USABLE_WIDTH_MM / 41 == pytest.approx(4.6463, abs=5e-5)
        assert _own_fit_mm(*self.DEPTH_ELEVEN) < FLOOR_MM
        assert FLOOR_MM > 4.6463

    def test_the_breach_point_on_the_amended_margins_is_exactly_depth_eleven(
        self,
    ) -> None:
        """Stated as a sweep, so it says *where* the floor sits, not just that it does.

        Depths 1..15 are the whole admissible range for a 30-wide grid
        (``2 * depth - 1 <= 30``); the first depth whose cell falls under
        ``FLOOR_MM`` must be 11, which is the amendment's own claim.
        """
        breaches = [
            depth
            for depth in range(1, 16)
            if USABLE_WIDTH_MM / (30 + depth) < FLOOR_MM
        ]

        assert breaches == list(range(11, 16)), breaches

    def test_the_gate_admits_depth_ten_and_refuses_depth_eleven(self, panel) -> None:
        """The pin where it is enforced: FR-031's own store gate, not arithmetic."""
        ten = panel.puzzle(*self.DEPTH_TEN)
        eleven = panel.puzzle(*self.DEPTH_ELEVEN)
        book_id = panel.book()

        assert panel.books.below_floor(book_id, [ten]) == []
        refusal, = panel.books.below_floor(book_id, [eleven])

        assert refusal.cell_mm == pytest.approx(4.6463, abs=5e-4)


# --------------------------------------------------------------------------
# The cost, measured on a seeded corpus (card item 5)
# --------------------------------------------------------------------------

#: The corpus the cost is measured on. Seeded ``random.Random``, no
#: ``hypothesis`` (it is not in the dependency baseline), and the case count is
#: asserted inside the test so the corpus cannot silently shrink.
COST_SEED = 225
COST_BOOKS = 60
MIN_COST_CASES = 1200

#: The grid sizes the corpus draws from — the shapes a book admits (CON-011's
#: 10..30 a side), including the two the card's own decompose-station table
#: names (30x30 and 30x12).
COST_SIZES = [
    (10, 10), (15, 15), (15, 20), (20, 15), (20, 20), (20, 25),
    (25, 20), (25, 25), (30, 20), (30, 25), (30, 30), (30, 12),
]


def _cost_corpus(seed: int) -> List[List[Dict[str, Any]]]:
    """``COST_BOOKS`` books of random grids at density 0.5, as clue sets.

    Density 0.5 is the population NFR-008's own amendment note sweeps ("random
    30x30 grids at density 0.5 reach depth 13"), so the distribution below is
    measured on the same kind of grid the registry reasons about rather than on
    the lattice fixtures the ACs above use.
    """
    from nonogram import clues as clue_module

    rng = random.Random(seed)
    books: List[List[Dict[str, Any]]] = []
    for _ in range(COST_BOOKS):
        members = []
        for _ in range(rng.randint(8, 40)):
            columns, rows = rng.choice(COST_SIZES)
            grid = [[rng.random() < 0.5 for _ in range(columns)] for _ in range(rows)]
            found = clue_module.compute_clues(grid)
            members.append(
                {
                    "row_clues": tuple(found.rows),
                    "column_clues": tuple(found.columns),
                    "size": (columns, rows),
                }
            )
        books.append(members)
    return books


@functools.lru_cache(maxsize=None)
def _measured_cost(seed: int) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
    """Every corpus puzzle's cell before and after the rule, in one pass.

    ``(before, after)``, parallel: ``before[i]`` is puzzle *i*'s own page fit
    and ``after[i]`` the cell its grid size prints at in its own book.

    Cached on the seed, which is its only input (review cycle 1, F-007). The
    six assertions of :class:`TestBookCellSize_TheCostOfABookWideCell` each
    read the whole measurement, and as a plain method it rebuilt the corpus —
    ``COST_BOOKS`` books, about 1388 random grids through ``compute_clues`` —
    and re-measured every member twice, once per test: six constructions and
    roughly 16.6k ``compute_layout`` calls where one construction and 2.8k
    do. The six keep their independence, because what they share is an
    immutable pair of tuples that none of them writes to, and the corpus still
    cannot silently shrink: ``test_the_corpus_is_the_size_it_says_it_is``
    asserts :data:`MIN_COST_CASES` against this same object.

    This function imports ``book_cell_mm``/``book_cell_sizes`` deliberately —
    see the class docstring below: the quantity being measured *is* the
    difference between those two answers.
    """
    from nonogram.admin.book_page_spec import (
        book_cell_mm,
        book_cell_sizes,
        book_page_spec,
    )

    spec = book_page_spec(_book())
    before: List[float] = []
    after: List[float] = []
    for members in _cost_corpus(seed):
        sizes = book_cell_sizes(
            spec, [(m["row_clues"], m["column_clues"]) for m in members]
        )
        for member in members:
            before.append(
                book_cell_mm(spec, member["row_clues"], member["column_clues"])
            )
            after.append(
                sizes[(len(member["column_clues"]), len(member["row_clues"]))]
            )
    return tuple(before), tuple(after)


class TestBookCellSize_TheCostOfABookWideCell:
    """What the rule costs, measured rather than estimated (card item 5).

    A book-wide size is by construction **<=** the per-puzzle size, so some
    puzzles print smaller than they did. This class imports
    ``book_cell_mm``/``book_cell_sizes`` deliberately: the quantity being
    measured *is* the difference between those two answers, and a second
    implementation of both would measure a model of the change.

    The figures the assertions pin are the ones recorded in CARD-225's own
    "Measured cost" section. They are a **corpus** measurement: a different
    seed moves them, which is why the seed is fixed and stated.
    """

    def _measure(self):
        """The one measurement, built once for the whole class (F-007)."""
        return _measured_cost(COST_SEED)

    def test_the_corpus_is_the_size_it_says_it_is(self) -> None:
        before, after = self._measure()

        assert len(before) == len(after)
        assert len(before) >= MIN_COST_CASES, (
            f"the cost corpus shrank to {len(before)} puzzles; it is measured "
            f"over at least {MIN_COST_CASES}"
        )

    def test_no_puzzle_ever_prints_larger_than_it_did(self) -> None:
        """The direction of the change, over the whole corpus."""
        before, after = self._measure()

        assert all(a <= b + 1e-12 for a, b in zip(after, before))

    def test_some_puzzles_really_do_print_smaller(self) -> None:
        """The control: a corpus in which nothing changed would prove nothing."""
        before, after = self._measure()

        changed = sum(1 for a, b in zip(after, before) if b - a > 1e-9)
        assert changed >= 300, changed

    def test_the_measured_distribution_is_the_one_the_card_records(self) -> None:
        before, after = self._measure()
        losses = sorted((b - a) / b * 100 for a, b in zip(after, before))

        unchanged = sum(1 for loss in losses if loss < 1e-9)
        assert unchanged / len(losses) == pytest.approx(0.715, abs=0.02)
        assert statistics.mean(losses) == pytest.approx(1.02, abs=0.05)
        assert statistics.median(losses) == pytest.approx(0.0, abs=1e-9)
        assert losses[-1] == pytest.approx(9.30, abs=0.1)
        assert max(b - a for a, b in zip(after, before)) == pytest.approx(
            0.523, abs=0.01
        )

    def test_the_cap_and_the_smallest_cell_are_both_untouched(self) -> None:
        """NFR-008's two ends: nothing gains, and the floor's worst case is the same.

        A grid size already at the 7.5 mm cap stays there — every member of it
        is capped, so the minimum is the cap (G-1). And the **smallest** cell
        in the book does not move either: it belongs to the deepest-clued
        member, which is the one the shared figure is fitted to.
        """
        before, after = self._measure()

        assert sum(1 for b in before if b == STANDARD_CELL_MM) == sum(
            1 for a in after if a == STANDARD_CELL_MM
        )
        assert min(after) == pytest.approx(min(before), abs=1e-12)

    def test_how_many_more_puzzles_land_below_the_floor(self) -> None:
        """The cost that matters most: FR-031's flag fires for more puzzles."""
        before, after = self._measure()

        was = sum(1 for b in before if b < FLOOR_MM)
        now = sum(1 for a in after if a < FLOOR_MM)

        assert was == pytest.approx(186, abs=10)
        assert now == pytest.approx(325, abs=15)
        assert now > was
