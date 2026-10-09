"""CARD-202 review F-1 (fix cycle 1): the packing walk degrades an infeasible
packed page instead of shipping it (white-box, over
``book_pdf_generator._degrade_infeasible_packed_pages``/``_packed_page_is_feasible``).

``tests/test_layout_packed_solved.py`` pins the geometry half of the fix —
``compute_packed_solved_layout`` declining rather than flooring. This file
pins the **walk** half: given a plan ``plan_small_answer_pages`` produced from
extents alone (it cannot see real clue depth — its own module docstring), the
degrade pass must turn any packed page COMP-007 cannot actually lay out into
one it can, in book order, without dropping, duplicating or reordering an
answer — first retrying at the next lower density (4-up -> two 2-ups), then
falling all the way back to one full page per answer.

``tests/test_book_solved_answer_key.py``'s
``TestBookSolvedAnswerKey_InfeasiblePackedPagesDegradeGracefully`` is this
fix's end-to-end proof, over a real book and real grids; this file reaches
the branches a real KDP-minimum trim's own numbers cannot (a 2-up pair that
still cannot pack) with synthetic clue depths instead, the same style
``tests/test_layout_two_up.py``'s own ``_puzzle`` helper uses.

    TestDegradeInfeasiblePackedPages_AFeasiblePageIsReturnedUnchanged
    TestDegradeInfeasiblePackedPages_FourUpSplitsIntoTwoWorkingTwoUps
    TestDegradeInfeasiblePackedPages_AHalfThatStillFailsFallsBackToSingles
    TestDegradeInfeasiblePackedPages_ATwoUpThatFailsFallsBackToSingles
    TestDegradeInfeasiblePackedPages_ALoneLeftoverThatFailsBecomesAPlainAnswer
    TestDegradeInfeasiblePackedPages_NeverDropsDuplicatesOrReordersAnAnswer
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, Sequence, Tuple, Union

from nonogram.admin.book_answer_key import Answer, PackedAnswerPage
from nonogram.admin.book_pdf_generator import (
    _degrade_infeasible_packed_pages,
    _packed_page_is_feasible,
)
from nonogram.difficulty import Tier
from nonogram.export.layout import OrientationPolicy, PageParity, PageSpec

#: The same KDP-minimum trim ``tests/test_layout_packed_solved.py`` reproduces
#: review F-1's reported scenario on (100mm x 100mm, KDP's minimum side
#: margin, the Book 1 profile's fixed top/bottom and title band) — restated
#: here rather than imported, the way every layout-literal test in this
#: project states its own spec.
KDP_MIN_ODD = PageSpec(
    width_mm=100.0,
    height_mm=100.0,
    top_mm=9.525,
    bottom_mm=9.525,
    gutter_mm=6.35,
    outside_mm=6.35,
    band_mm=12.0,
    orientation=OrientationPolicy.PORTRAIT_ONLY,
    cell_cap=7.5,
    min_thin_rule_mm=0.25,
    parity=PageParity.ODD,
)


def _clue_pair(
    *, row_depth: int, column_depth: int, rows: int, columns: int
) -> Tuple[Tuple[Tuple[int, ...], ...], Tuple[Tuple[int, ...], ...]]:
    """A synthetic ``(row_clues, column_clues)`` pair of exactly the depths asked.

    Not a real grid's encoding — a literal, the same way
    ``tests/test_layout_two_up.py``'s own ``_puzzle`` builds one — so the
    depth is exact rather than whatever a grid at this size happens to
    produce, and a depth no real 15-wide grid could carry (as deep as 25) is
    still usable to drive the geometry formula directly.
    """
    return (
        tuple((1,) * row_depth for _ in range(rows)),
        tuple((1,) * column_depth for _ in range(columns)),
    )


def _answer(number: int, width: int, height: int) -> Answer:
    return Answer(number=number, width=width, height=height, level=Tier.EASY)


def _payload(row_depth: int, column_depth: int, *, width: int, height: int) -> Any:
    """A minimal stand-in for ``ExportPayload``: only the two attributes
    ``_packed_page_is_feasible`` actually reads."""
    row_clues, column_clues = _clue_pair(
        row_depth=row_depth, column_depth=column_depth, rows=height, columns=width
    )
    return SimpleNamespace(row_clues=row_clues, column_clues=column_clues)


def _payloads(
    specs: Sequence[Tuple[int, int, int, int]]
) -> List[Tuple[Any, Any]]:
    """``[(id, payload), ...]`` from ``(width, height, row_depth, column_depth)``
    tuples, indexed 1-based print number minus one, the shape
    ``interior_stream`` already holds."""
    return [
        (f"p{index + 1}", _payload(row_depth, column_depth, width=width, height=height))
        for index, (width, height, row_depth, column_depth) in enumerate(specs)
    ]


def _numbers(plan: Sequence[Union[Answer, PackedAnswerPage]]) -> List[int]:
    result: List[int] = []
    for entry in plan:
        if isinstance(entry, PackedAnswerPage):
            result.extend(entry.numbers)
        else:
            result.append(entry.number)
    return result


class TestDegradeInfeasiblePackedPages_AFeasiblePageIsReturnedUnchanged:
    """A page COMP-007 can already lay out passes through untouched."""

    def test_identity_is_preserved_not_just_equality(self) -> None:
        answers = (_answer(1, 15, 8), _answer(2, 15, 9))
        page = PackedAnswerPage(answers)
        payloads = _payloads([(15, 8, 1, 1), (15, 9, 1, 1)])
        assert _packed_page_is_feasible(page, payloads, KDP_MIN_ODD)

        result = _degrade_infeasible_packed_pages([page], payloads, KDP_MIN_ODD)

        assert result == [page]
        assert result[0] is page


class TestDegradeInfeasiblePackedPages_FourUpSplitsIntoTwoWorkingTwoUps:
    """Review F-1's own reproduction: 4-up declines, both 2-up halves work."""

    #: Matches ``test_layout_packed_solved.py``'s own ``_ANSWERS``: width 15,
    #: heights 10/15/18/20, 5-deep gutters both axes — the 4-up tile's
    #: drawing height cannot clear MIN_CELL_MM for any of the four, but a
    #: 2-up tile's (double the height) can for both halves.
    SPECS = [(15, 10, 5, 5), (15, 15, 5, 5), (15, 18, 5, 5), (15, 20, 5, 5)]

    def test_the_four_up_page_is_not_feasible(self) -> None:
        answers = tuple(_answer(i + 1, w, h) for i, (w, h, _, _) in enumerate(self.SPECS))
        page = PackedAnswerPage(answers)
        payloads = _payloads(self.SPECS)
        assert not _packed_page_is_feasible(page, payloads, KDP_MIN_ODD)

    def test_it_degrades_to_two_packed_two_up_pages_not_four_singles(self) -> None:
        answers = tuple(_answer(i + 1, w, h) for i, (w, h, _, _) in enumerate(self.SPECS))
        page = PackedAnswerPage(answers)
        payloads = _payloads(self.SPECS)

        result = _degrade_infeasible_packed_pages([page], payloads, KDP_MIN_ODD)

        assert [type(entry) for entry in result] == [PackedAnswerPage, PackedAnswerPage]
        assert [entry.numbers for entry in result] == [(1, 2), (3, 4)]
        assert [entry.capacity for entry in result] == [2, 2]
        assert _numbers(result) == [1, 2, 3, 4]


class TestDegradeInfeasiblePackedPages_AHalfThatStillFailsFallsBackToSingles:
    """One 2-up half packs; the other cannot even at 2-up and falls to singles."""

    #: Members 1-2 (heights 10/15) carry a shallow gutter and pack fine at
    #: 2-up. Members 3-4 (heights 18/20) carry a 17-deep column gutter: at
    #: the 2-up tile's drawing height (68.95 mm on this trim), 68.95 /
    #: (17 + 18) = 1.97 mm and 68.95 / (17 + 20) = 1.86 mm, both under
    #: MIN_CELL_MM — so that half cannot pack at any capacity this walk
    #: tries and must fall back to two full pages.
    SPECS = [(15, 10, 1, 1), (15, 15, 1, 1), (15, 18, 1, 17), (15, 20, 1, 17)]

    def test_the_second_half_alone_is_infeasible(self) -> None:
        payloads = _payloads(self.SPECS)
        second_half = PackedAnswerPage((_answer(3, 15, 18), _answer(4, 15, 20)))
        assert not _packed_page_is_feasible(second_half, payloads, KDP_MIN_ODD)

    def test_the_first_half_alone_is_feasible(self) -> None:
        payloads = _payloads(self.SPECS)
        first_half = PackedAnswerPage((_answer(1, 15, 10), _answer(2, 15, 15)))
        assert _packed_page_is_feasible(first_half, payloads, KDP_MIN_ODD)

    def test_the_degraded_plan_keeps_the_pair_and_splits_the_rest_to_singles(
        self,
    ) -> None:
        answers = tuple(_answer(i + 1, w, h) for i, (w, h, _, _) in enumerate(self.SPECS))
        page = PackedAnswerPage(answers)
        payloads = _payloads(self.SPECS)

        result = _degrade_infeasible_packed_pages([page], payloads, KDP_MIN_ODD)

        assert len(result) == 3
        first, second, third = result
        assert isinstance(first, PackedAnswerPage) and first.numbers == (1, 2)
        assert isinstance(second, Answer) and second.number == 3
        assert isinstance(third, Answer) and third.number == 4
        assert _numbers(result) == [1, 2, 3, 4]


class TestDegradeInfeasiblePackedPages_ATwoUpThatFailsFallsBackToSingles:
    """A page already at 2-up (no lower packed density) degrades straight to singles."""

    #: 25-deep column gutter: 68.95 / (25 + 10) = 1.97 mm, under the floor,
    #: for the shallower of the two (so both members fail).
    SPECS = [(15, 10, 1, 25), (15, 12, 1, 25)]

    def test_the_pair_is_infeasible_at_its_own_capacity(self) -> None:
        answers = (_answer(1, 15, 10), _answer(2, 15, 12))
        page = PackedAnswerPage(answers)
        payloads = _payloads(self.SPECS)
        assert page.capacity == 2
        assert not _packed_page_is_feasible(page, payloads, KDP_MIN_ODD)

    def test_it_degrades_to_two_plain_answers(self) -> None:
        answers = (_answer(1, 15, 10), _answer(2, 15, 12))
        page = PackedAnswerPage(answers)
        payloads = _payloads(self.SPECS)

        result = _degrade_infeasible_packed_pages([page], payloads, KDP_MIN_ODD)

        assert result == [answers[0], answers[1]]
        assert all(isinstance(entry, Answer) for entry in result)


class TestDegradeInfeasiblePackedPages_ALoneLeftoverThatFailsBecomesAPlainAnswer:
    """A packed page of exactly one answer (a run's leftover) degrades to itself."""

    def test_a_single_member_packed_page_that_fails_becomes_a_plain_answer(
        self,
    ) -> None:
        answer = _answer(1, 15, 10)
        page = PackedAnswerPage((answer,))
        payloads = _payloads([(15, 10, 1, 25)])
        assert page.capacity == 2  # a lone member still measures at the 2-up tile
        assert not _packed_page_is_feasible(page, payloads, KDP_MIN_ODD)

        result = _degrade_infeasible_packed_pages([page], payloads, KDP_MIN_ODD)

        assert result == [answer]
        assert isinstance(result[0], Answer)


class TestDegradeInfeasiblePackedPages_NeverDropsDuplicatesOrReordersAnAnswer:
    """Across a mixed plan, every answer reaches the result exactly once, in order."""

    def test_a_plan_mixing_feasible_and_infeasible_pages_keeps_every_number_once(
        self,
    ) -> None:
        # Page A (1,2): feasible 2-up. Page B (3,4,5,6): infeasible 4-up whose
        # second half (5,6) is also infeasible at 2-up. Puzzle 7: already a
        # plain (large) answer, untouched by the walk.
        specs = [
            (15, 10, 1, 1),
            (15, 11, 1, 1),
            (15, 10, 5, 5),
            (15, 15, 5, 5),
            (15, 18, 1, 17),
            (15, 20, 1, 17),
        ]
        payloads = _payloads(specs) + [("p7", SimpleNamespace(row_clues=(), column_clues=()))]
        page_a = PackedAnswerPage((_answer(1, 15, 10), _answer(2, 15, 11)))
        page_b = PackedAnswerPage(
            (
                _answer(3, 15, 10),
                _answer(4, 15, 15),
                _answer(5, 15, 18),
                _answer(6, 15, 20),
            )
        )
        plain_seven = _answer(7, 22, 22)
        plan: List[Union[Answer, PackedAnswerPage]] = [page_a, page_b, plain_seven]

        result = _degrade_infeasible_packed_pages(plan, payloads, KDP_MIN_ODD)

        assert _numbers(result) == [1, 2, 3, 4, 5, 6, 7]
        # page_a was already feasible and must survive untouched.
        assert result[0] is page_a
        # plain_seven was never a PackedAnswerPage and must survive untouched.
        assert result[-1] is plain_seven
