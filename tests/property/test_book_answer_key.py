"""CARD-134: the packed answer key's standing property (EC-030, INV-011, FR-042).

    EC-030  PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook
        -> test_PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook
           (the seeded corpus: any length, any mix of sizes 10..30 and tiers)
        -> test_PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook_exhaustive
           (every short book over a small alphabet, enumerated rather than drawn)

What EC-030 says, and how it is checked here
--------------------------------------------
For **any** book order of any length and any mix of puzzle sizes
:data:`~nonogram.limits.MIN_SIZE`..``MAX_SIZE`` and tiers:

1. the key holds every member puzzle's answer **exactly once, in
   puzzle-number order**;
2. no page holds more than 6 answers, nor more than 4 when any answer on it is
   longer than 20 on its longest side;
3. no page holds answers of two levels;
4. a page is **closed only when** the next answer would push it past its
   capacity or belongs to the next level — the "no early close" half, which is
   what stops a walk from satisfying every other clause by putting one answer
   on each page;
5. the page count lies between ``ceil(n / 6)`` and ``ceil(n / 4) + (L - 1)``
   for ``n`` answers over ``L`` non-empty levels.

Clauses 2, 4 and 5 are re-derived here from FR-042's wording rather than from
the module under test: the capacity of a group is recomputed in this file, the
"would it have fitted?" question is asked by replaying each page boundary by
hand, and the bounds are computed from ``n`` and ``L`` with :func:`math.ceil`.
:mod:`nonogram.admin.book_answer_key`'s own constants are not imported — 6, 4
and 20 are written out below as FR-042 writes them — so a retuning on that side
cannot quietly retune the expectation too.

``L`` is the number of level **runs**, and why that is EC-030's ``L``
----------------------------------------------------------------------
A book's order is grouped by tier: every easy puzzle before every medium one,
every medium before every hard (INV-009, and CARD-128 prints the section in
that order). So a level occupies **one** contiguous run of the order, and its
number of runs is its number of non-empty levels — EC-030's ``L`` exactly.

Stated over an order that is *not* grouped, the bound is not merely wrong but
unreachable by any walk that keeps clause 3: easy, medium, easy is three
answers over two levels and cannot be printed in fewer than three pages,
while ``ceil(3 / 4) + (2 - 1)`` is two. Each level change costs a page, so the
quantity the bound is about is the number of changes, which is the number of
runs. Both are asserted: the corpus builds grouped orders in the majority,
where the two counts coincide and the bound is EC-030's literal one (the
:data:`GROUPED_BOOKS` floor below requires that case to be well represented),
and un-grouped orders besides, where it is checked against the runs. A walk
that split a grouped book's level across two runs would break the first.

No ``hypothesis`` (CLAUDE.md): stdlib ``random.Random`` at a fixed seed, with
the corpus's own minimum size and shape coverage asserted inside each test.
"""

from __future__ import annotations

import itertools
import random
from math import ceil
from typing import List, Optional, Sequence, Tuple

import pytest

from nonogram.admin.book_answer_key import Answer, AnswerPage, pack_answer_pages
from nonogram.difficulty import Tier
from nonogram.limits import MAX_SIZE, MIN_SIZE

# --------------------------------------------------------------------------
# FR-042's rule, restated — the independent half of every assertion below
# --------------------------------------------------------------------------

#: A page holds six answers while every answer on it is at most 20 cells on its
#: longest side, and four once one of them is longer.
SIX_UP = 6
FOUR_UP = 4
LONGEST_SIDE_FOR_SIX_UP = 20

#: The levels a book's puzzles can carry. ``None`` is a row whose tier nobody
#: can read (ADR-0031/R3 and worse), which is a level of its own.
LEVELS: Tuple[Optional[Tier], ...] = (Tier.EASY, Tier.MEDIUM, Tier.HARD, None)


def capacity_of(answers: Sequence[Answer]) -> int:
    """FR-042's capacity for a group of answers, written out again here."""
    if any(max(a.width, a.height) > LONGEST_SIDE_FOR_SIX_UP for a in answers):
        return FOUR_UP
    return SIX_UP


def page_bounds(count: int, runs: int) -> Tuple[int, int]:
    """EC-030's bounds on the page count: ``ceil(n / 6)`` .. ``ceil(n / 4) + (L - 1)``.

    ``runs`` is EC-030's ``L`` — see the module docstring on why the quantity
    is the number of level runs, and why it equals the number of non-empty
    levels for every order a book can actually be in (INV-009).
    """
    if count == 0:
        return 0, 0
    return ceil(count / SIX_UP), ceil(count / FOUR_UP) + max(runs - 1, 0)


def non_empty_levels(answers: Sequence[Answer]) -> int:
    """How many distinct levels the book's answers fall into."""
    return len({answer.level for answer in answers})


def level_runs(answers: Sequence[Answer]) -> int:
    """How many maximal stretches of one level the book's order falls into."""
    return sum(
        1
        for position, answer in enumerate(answers)
        if position == 0 or answers[position - 1].level != answer.level
    )


def is_grouped(answers: Sequence[Answer]) -> bool:
    """Whether the order is grouped by level, as INV-009 requires a book to be."""
    return level_runs(answers) == non_empty_levels(answers)


# --------------------------------------------------------------------------
# The property itself
# --------------------------------------------------------------------------


def check_the_key(answers: Sequence[Answer], pages: Sequence[AnswerPage], label: str) -> None:
    """Assert every clause of EC-030 for one book's answers and its key."""
    # (1) every answer exactly once, in puzzle-number order.
    walked = [answer for page in pages for answer in page.answers]
    assert walked == list(answers), f"{label}: the key is not the book order"

    for position, page in enumerate(pages):
        on_page = page.answers
        # (2) the capacity rule, re-derived.
        capacity = capacity_of(on_page)
        assert len(on_page) <= capacity, (
            f"{label}: page {position + 1} holds {len(on_page)} answers at a "
            f"capacity of {capacity}"
        )
        assert page.capacity == capacity, (
            f"{label}: page {position + 1} reports a capacity of {page.capacity}, "
            f"not {capacity}"
        )
        # (3) one level per page.
        assert len({answer.level for answer in on_page}) == 1, (
            f"{label}: page {position + 1} holds two levels"
        )

    # (4) no page was closed early: the first answer of every page but the
    # first either belongs to another level or would not have fitted on the
    # page before it.
    for position in range(1, len(pages)):
        previous = pages[position - 1].answers
        opener = pages[position].answers[0]
        if opener.level == previous[0].level:
            joined = list(previous) + [opener]
            assert len(joined) > capacity_of(joined), (
                f"{label}: page {position} closed with {len(previous)} answers "
                f"although answer {opener.number} would have fitted"
            )

    # (5) the page count's bounds. On a grouped order — the only order a book
    # is ever in (INV-009) — the run count *is* the level count, so this is
    # EC-030's bound as written; see the module docstring.
    least, most = page_bounds(len(answers), level_runs(answers))
    assert least <= len(pages) <= most, (
        f"{label}: {len(answers)} answers over {level_runs(answers)} level run(s) "
        f"took {len(pages)} pages, not {least}..{most}"
    )
    if is_grouped(answers):
        assert len(pages) <= ceil(len(answers) / FOUR_UP) + max(
            non_empty_levels(answers) - 1, 0
        ), f"{label}: a grouped book must meet EC-030's bound on its level count"

    # The headings: the first page of a level's run carries that level's name,
    # every later page of the run carries none.
    for position, page in enumerate(pages):
        opens_a_run = position == 0 or pages[position - 1].level != page.level
        expected = (page.level.label if page.level is not None else None) if opens_a_run else None
        assert page.heading == expected, (
            f"{label}: page {position + 1} carries the heading {page.heading!r}, "
            f"not {expected!r}"
        )


# --------------------------------------------------------------------------
# The seeded corpus
# --------------------------------------------------------------------------

#: The corpus cannot silently shrink: the floors are asserted inside the test.
MIN_BOOKS = 400
MIN_ANSWERS = 8000
MIN_PAGES = 2000

#: How many books of the corpus must be in the grouped order INV-009 puts a
#: real book in — the case where EC-030's bound is its literal self.
GROUPED_BOOKS = 150


def _levels(source: random.Random, count: int) -> List[Optional[Tier]]:
    """One book's levels, in order, in one of three shapes.

    **Grouped** (the majority, and the only shape a real book is in): a subset
    of the levels, each occupying one contiguous block, as INV-009 requires.
    **Run-shaped**: contiguous blocks that may return to a level already left —
    a legacy arrangement, which the walk must still print sensibly.
    **Scattered**: a fresh draw per answer, so that almost every page is closed
    by a level change. Without the first two, a corpus of scattered orders
    would never fill a page and the capacity clause would never bite.
    """
    if count == 0:
        return []
    roll = source.random()
    if roll < 0.55:  # grouped
        chosen = source.sample(LEVELS, source.randint(1, len(LEVELS)))
        levels: List[Optional[Tier]] = []
        cuts = sorted(source.randint(0, count) for _ in range(len(chosen) - 1))
        for level, start, end in zip(chosen, [0] + cuts, cuts + [count]):
            levels.extend([level] * (end - start))
        return levels
    if roll < 0.85:  # run-shaped, levels may return
        levels = []
        while len(levels) < count:
            run = min(count - len(levels), source.randint(1, 14))
            levels.extend([source.choice(LEVELS)] * run)
        return levels
    return [source.choice(LEVELS) for _ in range(count)]


def _book(source: random.Random, count: int) -> List[Answer]:
    """One book's answers: ``count`` puzzles, numbered 1..count.

    The extents are drawn across CON-011's whole range, with the two sides
    drawn independently so that a wide-and-short answer (20 x 15, longest side
    20) and a tall-and-narrow one (15 x 25, longest side 25) both occur — the
    two halves of the "longest side" the capacity rule is stated in. The levels
    are :func:`_levels`'.

    Each book draws its own **share of small answers** rather than sizing every
    answer uniformly over 10..30. A uniform draw makes a large answer on a page
    almost certain, so four-up pages would swamp the corpus and a *full* six-up
    page — six consecutive answers all at most 20 — would turn up about twice
    in ten thousand. BK-8's own default plan is 90 small to 60 large, so the
    shares swept here run from all-large to all-small with that among them.
    """
    levels = _levels(source, count)
    small_share = source.choice((0.0, 0.2, 0.5, 0.6, 0.85, 1.0))

    def side(small: bool) -> int:
        return (
            source.randint(MIN_SIZE, LONGEST_SIDE_FOR_SIX_UP)
            if small
            else source.randint(LONGEST_SIDE_FOR_SIX_UP + 1, MAX_SIZE)
        )

    answers: List[Answer] = []
    for number in range(1, count + 1):
        small = source.random() < small_share
        width, height = side(small), side(small)
        if not small:
            # One side above 20 is enough to make an answer large; which one
            # varies, so a tall-and-narrow answer is as common as a squat one.
            width, height = (
                (width, source.randint(MIN_SIZE, MAX_SIZE))
                if source.random() < 0.5
                else (source.randint(MIN_SIZE, MAX_SIZE), height)
            )
        answers.append(
            Answer(
                number=number, width=width, height=height, level=levels[number - 1]
            )
        )
    return answers


def test_PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook() -> None:
    """EC-030 — every clause, over a seeded corpus of whole books.

    Book lengths run from the empty book to rather more than the default
    plan's 150, so the bound in clause 5 is exercised where ``L - 1`` is a
    rounding error and where it is the whole difference.
    """
    source = random.Random(20260923)
    books = 0
    answers_seen = 0
    pages_seen = 0
    seen: dict = {
        "six-up page": 0,
        "four-up page": 0,
        "page closed by capacity": 0,
        "page closed by level": 0,
        "full four-up page": 0,
        "full six-up page": 0,
        "unnamed level": 0,
        "at the upper bound": 0,
        "at the lower bound": 0,
        "grouped book": 0,
        "ungrouped book": 0,
        "multi-level book": 0,
    }

    for index in range(MIN_BOOKS + 40):
        count = source.choice(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 24, 25, 49, 90, 150, 151, 163]
        )
        answers = _book(source, count)
        pages = pack_answer_pages(answers)
        check_the_key(answers, pages, f"book {index} of {count}")

        books += 1
        answers_seen += count
        pages_seen += len(pages)
        for position, page in enumerate(pages):
            seen["six-up page" if page.capacity == SIX_UP else "four-up page"] += 1
            if len(page.answers) == page.capacity:
                seen[f"full {'six' if page.capacity == SIX_UP else 'four'}-up page"] += 1
            if page.level is None:
                seen["unnamed level"] += 1
            if position:
                closed_by = (
                    "level" if pages[position - 1].level != page.level else "capacity"
                )
                seen[f"page closed by {closed_by}"] += 1
        if count:
            seen["grouped book" if is_grouped(answers) else "ungrouped book"] += 1
            if non_empty_levels(answers) > 1:
                seen["multi-level book"] += 1
            least, most = page_bounds(count, level_runs(answers))
            if len(pages) == most:
                seen["at the upper bound"] += 1
            if len(pages) == least:
                seen["at the lower bound"] += 1

    assert books >= MIN_BOOKS, books
    assert answers_seen >= MIN_ANSWERS, answers_seen
    assert pages_seen >= MIN_PAGES, pages_seen
    # The corpus really met every shape the property is about.
    for shape, floor in (
        ("six-up page", 200),
        ("four-up page", 200),
        ("page closed by capacity", 200),
        ("page closed by level", 100),
        ("full six-up page", 100),
        ("full four-up page", 100),
        ("unnamed level", 50),
        ("at the lower bound", 20),
        ("at the upper bound", 20),
        ("grouped book", GROUPED_BOOKS),
        ("ungrouped book", 50),
        ("multi-level book", 150),
    ):
        assert seen[shape] >= floor, (shape, seen)


# --------------------------------------------------------------------------
# The exhaustive half: every short book over a small alphabet
# --------------------------------------------------------------------------

#: One small answer, one exactly at the six-up boundary, and one above it —
#: the three cases the capacity rule distinguishes, at both orientations of
#: the "longest side".
ALPHABET: Tuple[Tuple[int, int], ...] = (
    (MIN_SIZE, MIN_SIZE),
    (LONGEST_SIDE_FOR_SIX_UP, MIN_SIZE),
    (MIN_SIZE, LONGEST_SIDE_FOR_SIX_UP),
    (LONGEST_SIDE_FOR_SIX_UP + 1, MIN_SIZE),
    (MIN_SIZE, MAX_SIZE),
)

#: The two levels it takes to make a level change, plus the unnamed one.
SHORT_LEVELS: Tuple[Optional[Tier], ...] = (Tier.EASY, Tier.MEDIUM, None)


@pytest.mark.parametrize("length", [1, 2, 3])
def test_PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook_exhaustive(
    length: int,
) -> None:
    """EC-030 over **every** book of up to three puzzles from a small alphabet.

    The seeded corpus above samples; this enumerates. Every arrangement of
    sizes and levels of that length is built and checked, so the boundary cases
    the sampler might miss — a 20 followed by a 21, a level change on the first
    answer, an unnamed level between two named ones — are all present by
    construction rather than by luck.
    """
    checked = 0
    for sizes in itertools.product(ALPHABET, repeat=length):
        for levels in itertools.product(SHORT_LEVELS, repeat=length):
            answers = [
                Answer(number=number, width=width, height=height, level=level)
                for number, ((width, height), level) in enumerate(
                    zip(sizes, levels), start=1
                )
            ]
            check_the_key(
                answers, pack_answer_pages(answers), f"{sizes} at {levels}"
            )
            checked += 1

    assert checked == (len(ALPHABET) * len(SHORT_LEVELS)) ** length, checked


# --------------------------------------------------------------------------
# The walk's own refusals
# --------------------------------------------------------------------------


class TestPackAnswerPages_RefusesWhatItCannotPrint:
    """INV-011 is an order as much as a capacity, and the walk says so."""

    @pytest.mark.parametrize(
        "numbers", [(2, 1), (1, 1), (1, 3, 2), (3, 2, 1), (1, 2, 2)]
    )
    def test_answers_out_of_puzzle_number_order_are_refused(
        self, numbers: Tuple[int, ...]
    ) -> None:
        answers = [
            Answer(number=number, width=15, height=15, level=Tier.EASY)
            for number in numbers
        ]
        with pytest.raises(ValueError):
            pack_answer_pages(answers)

    def test_an_empty_book_has_no_answer_pages(self) -> None:
        assert pack_answer_pages([]) == []

    @pytest.mark.parametrize("number", [0, -1])
    def test_an_answer_that_is_not_a_print_position_is_refused(
        self, number: int
    ) -> None:
        with pytest.raises(ValueError):
            Answer(number=number, width=15, height=15, level=Tier.EASY)

    @pytest.mark.parametrize("side", [0, -1, 1.5, True, "15"])
    def test_an_extent_that_is_not_a_cell_count_is_refused(self, side: object) -> None:
        with pytest.raises(ValueError):
            Answer(number=1, width=side, height=15, level=Tier.EASY)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            Answer(number=1, width=15, height=side, level=Tier.EASY)  # type: ignore[arg-type]

    def test_a_level_that_is_not_a_tier_is_refused(self) -> None:
        """The walk groups by level; a raw ``"easy"`` beside a ``Tier.EASY``
        would be two levels that print as one heading."""
        with pytest.raises(ValueError):
            Answer(number=1, width=15, height=15, level="easy")  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "answers",
        [
            # Two levels on one page.
            (
                Answer(number=1, width=15, height=15, level=Tier.EASY),
                Answer(number=2, width=15, height=15, level=Tier.MEDIUM),
            ),
            # Seven answers, which no tiling holds.
            tuple(
                Answer(number=n, width=15, height=15, level=Tier.EASY)
                for n in range(1, 8)
            ),
            # Five answers on a page one of them makes four-up.
            tuple(
                Answer(number=n, width=25 if n == 1 else 15, height=15, level=Tier.EASY)
                for n in range(1, 6)
            ),
            (),
        ],
    )
    def test_a_page_that_could_not_print_cannot_be_built(
        self, answers: Tuple[Answer, ...]
    ) -> None:
        """INV-011 is a property of the type, not only of the walk."""
        with pytest.raises(ValueError):
            AnswerPage(answers=answers)
