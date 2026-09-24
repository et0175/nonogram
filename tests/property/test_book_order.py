"""EC-029 — the book order stays grouped by tier under any edit sequence (INV-009).

    For any book and any sequence of adds, removes and moves, the book order
    stays grouped by tier (easy, then medium, then hard); and the relative
    order of two puzzles of one level changes only through an explicit move
    within that level.

This file holds **both halves** of EC-029: the edit sequence, and — since
CARD-128 — the printed book that comes out of every state it passes through.
After each step the book's rows are put through the export's own two decisions
(``print_order`` then ``puzzle_section``, which is the pair
``interior_stream`` makes before it draws anything) and the page plan that
comes back is required to be **one divider page per non-empty level,
immediately before that level's first puzzle page, with puzzle numbers 1..n
unbroken across the levels**. The expected plan is built here, from this
file's own rank table, and never by asking the code under test what it thinks.

Nothing is rendered inside the sweep — the plan is decided without a pixel,
which is what makes it affordable per step — but the last book of each mode
**is** exported, so the plan this property sweeps is tied to a file whose
pages were really drawn.

What is moved
-------------
* **any book** — a fresh book per trial, grown from empty by the sequence
  itself, so no trial starts from a state a previous one arranged;
* **any sequence** — adds of a random handful, removes of a random member and
  moves up and down of a random member, drawn in a random order, over a pool
  whose stored tiers cover all three levels plus ADR-0031/R3's retired
  ``guess`` word (a row written before the fourth tier was retired, which must
  print with the hard level);
* **both storage modes** — the grouping is a rule of the aggregate, not of a
  backend, so the in-memory manager and the database-backed one each run the
  whole corpus.

No ``hypothesis`` (it is not in the dependency baseline): the corpus is built
by hand with stdlib :class:`random.Random` on a fixed seed, and the case count
is asserted *inside* each test so it cannot silently shrink. The counts are
asserted per **kind** of step as well as in total: a run that never refused a
boundary-crossing move, or never removed anything, would satisfy the property
vacuously, and that is exactly the green that means nothing.

The oracle is independent
-------------------------
The expected order is never re-derived by calling ``book_level_order`` on the
same input — that would prove only that the code agrees with itself. The rank
table below is written out here from the *stored word* on the row, the
grouping is checked as "the ranks are non-decreasing", and the within-level
relative order is checked by cutting both the before and the after order into
levels with this file's own code and comparing them element by element.
"""

from __future__ import annotations

import random

import pytest

from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    DividerPagePlan,
    PuzzlePagePlan,
    print_order,
)
from nonogram.admin.book_plan import LevelBoundary
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import sqlite_session_scope

#: The seed. Fixed, so a failure is reproducible and a corpus is a corpus.
SEED = 20260923 + 126

MODES = ["memory", "db"]

#: The pool's stored tier words, repeated so every level holds several
#: puzzles — a level of one can never show a within-level reordering.
POOL_TIERS = (
    "easy",
    "easy",
    "easy",
    "medium",
    "medium",
    "medium",
    "hard",
    "hard",
    "guess",  # ADR-0031/R3: a pre-CARD-098 row. It ranks with hard, unrewritten.
)

#: Which level each stored word belongs to, written out here rather than
#: imported: this is the oracle, and an oracle that asks the code under test
#: what the answer is is not one.
RANK = {"easy": 0, "medium": 1, "hard": 2, "guess": 2}

#: What a divider page for each rank says — the level's name, and nothing else
#: (AC-254). Written out here for the same reason :data:`RANK` is.
LEVEL_NAME = {0: "Easy", 1: "Medium", 2: "Hard"}

#: How much sequence each mode runs, and the floor under it.
TRIALS = 25
STEPS = 14
MIN_STEPS = 300
#: The smallest number of steps of each kind a run must contain.
MIN_OF_EACH_KIND = 15


# --------------------------------------------------------------------------
# the shelf and the oracle
# --------------------------------------------------------------------------


class Shelf:
    """A book manager, the store behind it, and a pool of graded puzzles."""

    def __init__(self, mode, tmp_path):
        self.mode = mode
        factory = None if mode == "memory" else sqlite_session_scope(tmp_path, "order.db")
        self.store = PuzzleReviewService(session_factory=factory)
        self.books = BookManager(session_factory=factory, puzzle_store=self.store)
        self.pool = [self._puzzle(tier, n) for n, tier in enumerate(POOL_TIERS)]
        #: id -> the word actually stored on the row, read back from the store.
        self.word = {
            puzzle_id: self.store.get_puzzle(puzzle_id)["difficulty_tier"]
            for puzzle_id in self.pool
        }

    def _puzzle(self, tier, n, size=10) -> str:
        return self.store.add_puzzle(
            grid=[[True] * size for _ in range(size)],
            clues_rows=[[size]] * size,
            clues_cols=[[size]] * size,
            width=size,
            height=size,
            theme="generic",
            difficulty_score=10,
            difficulty_tier=tier,
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            batch_id=None,
            source_image=f"{tier}-{n}.png",
        )

    def rank(self, puzzle_id) -> int:
        return RANK[self.word[puzzle_id]]

    def order(self, book_id) -> list:
        return list(self.books.get_book(book_id).puzzle_ids)


def levels_of(shelf, order) -> dict:
    """``order`` cut into ``{rank: [ids in the order they appear]}``.

    This file's own code, kept deliberately naive: it walks the list once and
    files each id under its rank, so the list it builds for a rank is that
    rank's subsequence of ``order`` — which is precisely "the relative order
    of two puzzles of one level".
    """
    cut: dict = {rank: [] for rank in (0, 1, 2)}
    for puzzle_id in order:
        cut[shelf.rank(puzzle_id)].append(puzzle_id)
    return cut


def assert_grouped(shelf, order, context) -> None:
    """INV-009's grouping: every easy before every medium before every hard."""
    ranks = [shelf.rank(puzzle_id) for puzzle_id in order]
    assert ranks == sorted(ranks), (
        f"the order is not grouped easy, then medium, then hard after {context}: "
        f"ranks {ranks}"
    )


def assert_levels_unchanged(shelf, before, after, context, *, except_rank=None) -> None:
    """Every level's relative order is what it was, for the ids both lists hold."""
    kept = set(before) & set(after)
    for rank, sequence in levels_of(shelf, before).items():
        if rank == except_rank:
            continue
        was = [puzzle_id for puzzle_id in sequence if puzzle_id in kept]
        now = [
            puzzle_id
            for puzzle_id in levels_of(shelf, after)[rank]
            if puzzle_id in kept
        ]
        assert was == now, (
            f"level {rank}'s relative order changed without an explicit move "
            f"inside it, after {context}: {was} -> {now}"
        )


# --------------------------------------------------------------------------
# the printed book (CARD-128)
# --------------------------------------------------------------------------


def _rows(shelf, order) -> list:
    """The book's rows, in the stored order, as the export is handed them."""
    return [shelf.store.get_puzzle(puzzle_id) for puzzle_id in order]


def _expected_section(shelf, order) -> list:
    """The puzzle section this file says the interior must hold.

    ``[("divider", name) | ("puzzle", puzzle id, number), ...]`` in print
    order: the ids grouped by :data:`RANK` with a stable sort, one divider
    before each run of a **named** level, and the numbers running 1..n over
    the puzzles alone. Nothing here calls the generator; it is the expectation
    the generator's plan is compared against.

    None of this corpus's puzzles ever shares a page: they are 10x10s with
    single-run clues, which two-up pairing could pair — so the comparison
    below allows a page to hold two puzzles and this expectation is written
    per **puzzle**, not per page, with the pages' contents concatenated on the
    other side.
    """
    printed = sorted(order, key=shelf.rank)
    section: list = []
    opened = None
    for number, puzzle_id in enumerate(printed, start=1):
        rank = shelf.rank(puzzle_id)
        if rank != opened:
            opened = rank
            if rank in LEVEL_NAME:
                section.append(("divider", LEVEL_NAME[rank]))
        section.append(("puzzle", puzzle_id, number))
    return section


def _planned_section(shelf, order) -> list:
    """The same list, read off the export's own page plan.

    ``print_order`` and ``puzzle_section`` are the two decisions
    :meth:`BookPDFGenerator.interior_stream` makes before it draws anything,
    made here in the same order and over the same rows, so what is compared is
    the plan the export would print. A two-up page contributes both of its
    puzzles, in print order, which is what lets a paired book be compared
    against the per-puzzle expectation above.
    """
    rows = print_order(_rows(shelf, order))
    payloads = [BookPDFGenerator._payload(row) for row in rows]
    ids = [row["id"] for row in rows]
    section: list = []
    for entry in BookPDFGenerator(None).puzzle_section(payloads, ids=ids):
        if isinstance(entry, DividerPagePlan):
            section.append(("divider", entry.text))
            continue
        for number in entry.numbers:
            section.append(("puzzle", ids[number - 1], number))
    return section


def assert_prints_grouped_with_dividers(shelf, order, context) -> int:
    """EC-029's printed half, over one state of one book.

    One divider per non-empty named level, immediately before that level's
    first puzzle, and puzzle numbers 1..n unbroken across the levels — checked
    as a single comparison of the whole section, because each of those three
    claims is a claim about *where* something is and the section is where they
    all live.

    Returns how many levels this state prints, so the sweep can require that
    books of one, two and three levels all occurred rather than assuming a
    random walk produced them.
    """
    planned = _planned_section(shelf, order)
    assert planned == _expected_section(shelf, order), (
        f"the printed section is not the one this order prints, after {context}"
    )

    # And the three claims again, each on its own, so a failure says which of
    # them broke rather than only that the lists differ.
    numbers = [entry[2] for entry in planned if entry[0] == "puzzle"]
    assert numbers == list(range(1, len(order) + 1)), (
        f"puzzle numbers are not 1..{len(order)} after {context}: {numbers}"
    )
    names = [entry[1] for entry in planned if entry[0] == "divider"]
    levels = [
        LEVEL_NAME[rank]
        for rank in sorted({shelf.rank(p) for p in order} & set(LEVEL_NAME))
    ]
    assert names == levels, (
        f"the dividers are {names}, not one per non-empty level ({levels}) "
        f"after {context}"
    )
    for index, entry in enumerate(planned):
        if entry[0] != "divider":
            continue
        follower = planned[index + 1]
        assert follower[0] == "puzzle", f"{entry[1]} opens no puzzle after {context}"
        assert LEVEL_NAME[shelf.rank(follower[1])] == entry[1], (
            f"the {entry[1]} divider opens a {follower[1]} page after {context}"
        )
    return len(names)


def assert_the_interior_really_prints_that(shelf, order, context) -> None:
    """The same book, exported: the page plan's own count, and a real file.

    The sweep decides a plan per step without drawing; this draws one book, so
    the plan the property is stated over is tied to pages that exist. The page
    count is checked against this file's own arithmetic — guide page, the
    section's pages, the SOLUTIONS divider and the packed key's pages — and
    the pages are really built, which is where a plan that cannot be drawn
    would fail.
    """
    rows = print_order(_rows(shelf, order))
    payloads = [BookPDFGenerator._payload(row) for row in rows]
    plan = BookPDFGenerator(None).puzzle_section(payloads)
    dividers = sum(1 for entry in plan if isinstance(entry, DividerPagePlan))
    puzzle_pages = sum(1 for entry in plan if isinstance(entry, PuzzlePagePlan))

    stream = BookPDFGenerator(None).interior_stream(_rows(shelf, order))
    pages = list(stream.pages)

    # Guide page, the section's pages, the SOLUTIONS divider, the packed key.
    expected = 1 + dividers + puzzle_pages + 1 + stream.answer_page_count
    assert stream.page_count == expected, context
    assert len(pages) == expected, context
    assert {page.size for page in pages} == {pages[0].size}, context


# --------------------------------------------------------------------------
# the property
# --------------------------------------------------------------------------


def _draw(rng, members, shelf) -> str:
    """One step's kind, constrained only by what is possible right now."""
    possible = ["add"] if len(members) < len(shelf.pool) else []
    if members:
        possible += ["remove", "up", "down", "up", "down"]
    return rng.choice(possible)


def _move(shelf, book_id, puzzle_id, offset):
    """The move, as an outcome: True, False or the refusal it raised."""
    try:
        if offset < 0:
            return shelf.books.move_puzzle_up(book_id, puzzle_id)
        return shelf.books.move_puzzle_down(book_id, puzzle_id)
    except LevelBoundary as refusal:
        return refusal


def _assert_at_the_end_of_its_level(shelf, after, joining, context) -> None:
    """The new ids are the tail of their level, in the order they were submitted."""
    for rank, sequence in levels_of(shelf, after).items():
        new_here = [p for p in joining if shelf.rank(p) == rank]
        if not new_here:
            continue
        assert sequence[len(sequence) - len(new_here) :] == new_here, (
            f"a new puzzle did not land at the end of its own level ({context}): "
            f"level {rank} is {sequence}, the new ones were {new_here}"
        )


def _check_move(shelf, before, after, moving, offset, outcome, context) -> str:
    """Which kind of move this was, having checked it did the right thing."""
    sequence = levels_of(shelf, before)[shelf.rank(moving)]
    index = sequence.index(moving)
    target = index + offset

    if 0 <= target < len(sequence):
        assert outcome is True, f"a move inside a level must happen ({context}): {outcome!r}"
        expected = list(sequence)
        expected[index], expected[target] = expected[target], expected[index]
        assert levels_of(shelf, after)[shelf.rank(moving)] == expected, context
        assert_levels_unchanged(shelf, before, after, context, except_rank=shelf.rank(moving))
        return "moved"

    # No neighbour inside the level. Either the book has none at all...
    at_the_book_end = before.index(moving) == (0 if offset < 0 else len(before) - 1)
    assert after == before, f"a move that did not happen changed the order ({context})"
    if at_the_book_end:
        assert outcome is False, (
            f"the very top or bottom of the book reports nothing happened "
            f"({context}): {outcome!r}"
        )
        return "book_end"
    # ...or the neighbour belongs to another level, which is refused.
    assert isinstance(outcome, LevelBoundary), (
        f"a move across a level boundary must be refused ({context}): {outcome!r}"
    )
    return "refused"


@pytest.mark.parametrize("mode", MODES)
def test_PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence(mode, tmp_path) -> None:
    """EC-029 — PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence.

    Both halves: for any book and any sequence of adds, removes and moves, the
    order stays grouped easy/medium/hard, a level's internal order changes only
    through a move inside that level, and the book that order **prints** holds
    exactly one divider per non-empty level, immediately before that level's
    first puzzle, with puzzle numbers 1..n unbroken (CARD-128).
    """
    shelf = Shelf(mode, tmp_path)
    rng = random.Random(SEED)
    counts = {"add": 0, "remove": 0, "moved": 0, "refused": 0, "book_end": 0}
    #: The printed half runs on every step of every trial, so it is counted
    #: separately from the edit kinds and has a floor of its own.
    counts["printed"] = 0
    #: How many levels the printed books held, so a sweep that only ever saw
    #: one-level books cannot pass for a sweep of the divider rule.
    levels_seen: set = set()

    for trial in range(TRIALS):
        book_id = shelf.books.create_book(f"Book {trial}", "a book", "christmas", "adults")
        members: list = []

        for step in range(STEPS):
            before = shelf.order(book_id)
            assert before == members, (
                "the store and this test disagree about the membership before "
                f"trial {trial} step {step}: {before} vs {members}"
            )
            kind = _draw(rng, members, shelf)
            context = f"trial {trial} step {step} ({kind})"

            if kind == "add":
                free = [p for p in shelf.pool if p not in members]
                joining = rng.sample(free, rng.randint(1, min(3, len(free))))
                shelf.books.add_puzzles_to_book(book_id, joining)
                after = shelf.order(book_id)
                assert set(after) == set(before) | set(joining), context
                assert_levels_unchanged(shelf, before, after, context)
                _assert_at_the_end_of_its_level(shelf, after, joining, context)
                counts["add"] += 1

            elif kind == "remove":
                leaving = rng.choice(members)
                assert shelf.books.remove_puzzle_from_book(book_id, leaving) is True
                after = shelf.order(book_id)
                assert set(after) == set(before) - {leaving}, context
                assert_levels_unchanged(shelf, before, after, context)
                counts["remove"] += 1

            else:
                offset = -1 if kind == "up" else +1
                moving = rng.choice(members)
                outcome = _move(shelf, book_id, moving, offset)
                after = shelf.order(book_id)
                assert set(after) == set(before), context
                counts[_check_move(shelf, before, after, moving, offset, outcome, context)] += 1

            assert_grouped(shelf, after, context)
            # ...and the book this state prints (CARD-128). Decided, not
            # drawn: the plan is what the claim is about, and a rendered page
            # per step would make this corpus unaffordable.
            levels_seen.add(assert_prints_grouped_with_dividers(shelf, after, context))
            counts["printed"] += 1
            members = after

        # One book of each trial's final state is really exported, so the
        # plans swept above are tied to pages that were drawn. The last trial
        # of each mode is enough: the work is one 13-page interior, not 350.
        if trial == TRIALS - 1 and members:
            assert_the_interior_really_prints_that(
                shelf, members, f"trial {trial} (exported)"
            )
        shelf.books.delete_book(book_id)

    printed = counts.pop("printed")
    steps = sum(counts.values())
    assert printed == steps, (printed, steps)
    # Books of one, two and three levels were all printed, so "one divider per
    # non-empty level" was checked where it has something to say.
    assert {1, 2, 3} <= levels_seen, levels_seen
    assert steps >= MIN_STEPS, f"the corpus shrank to {steps} steps: {counts}"
    for kind, seen in counts.items():
        assert seen >= MIN_OF_EACH_KIND, (
            f"only {seen} {kind!r} steps in {steps}; the property would be vacuous "
            f"for that kind: {counts}"
        )
