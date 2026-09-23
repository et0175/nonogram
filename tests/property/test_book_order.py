"""EC-029 — the book order stays grouped by tier under any edit sequence (INV-009).

    For any book and any sequence of adds, removes and moves, the book order
    stays grouped by tier (easy, then medium, then hard); and the relative
    order of two puzzles of one level changes only through an explicit move
    within that level.

This file holds the **edit-sequence half** of EC-029. The other half — one
divider per non-empty level immediately before that level's first puzzle, and
puzzle numbers 1..n unbroken — belongs to the printed book and is CARD-128's
to add here; nothing in this file asserts anything about a PDF.

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

    The edit-sequence half: for any book and any sequence of adds, removes and
    moves, the order stays grouped easy/medium/hard, and a level's internal
    order changes only through a move inside that level. CARD-128 extends this
    with the divider and numbering half.
    """
    shelf = Shelf(mode, tmp_path)
    rng = random.Random(SEED)
    counts = {"add": 0, "remove": 0, "moved": 0, "refused": 0, "book_end": 0}

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
            members = after

        shelf.books.delete_book(book_id)

    steps = sum(counts.values())
    assert steps >= MIN_STEPS, f"the corpus shrank to {steps} steps: {counts}"
    for kind, seen in counts.items():
        assert seen >= MIN_OF_EACH_KIND, (
            f"only {seen} {kind!r} steps in {steps}; the property would be vacuous "
            f"for that kind: {counts}"
        )
