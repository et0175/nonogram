"""CARD-108 — deleting a book lets go of its puzzles, in both storage modes.

    AC-1  after delete_book, its puzzles have no book_id, in either mode
    AC-2  those puzzles can be rejected and deleted again
    AC-3  deleting one book does not release another's puzzles
    AC-4  the puzzles are released, not deleted

Measured before the fix, in-memory mode::

    booked                  : True
    after delete_book       : STILL POINTS AT book_000001
    puzzle still rejectable : False

The second line is the damage. CARD-100 made every in-book guard read
``book_id``, so a puzzle left pointing at a deleted book could no longer be
rejected, restored, approved or deleted by anything, ever.

DB mode has been fine since CARD-103, because ``ON DELETE SET NULL`` does the
work. That is why this is parametrised over both modes rather than tested in
one: the bug is precisely that they disagreed, and a test in DB mode alone
would have passed throughout.
"""

from __future__ import annotations

import pytest

from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_plan import DistributionPlan, Split
from nonogram.admin.puzzle_review import PuzzleReviewService, PuzzleStatus
from tests.helpers.db import make_batch, sqlite_session_scope

#: CARD-124: since ADR-0035 a book leaves draft only when every longest-side x
#: tier cell is within 3 points of its plan, so a test that publishes a book
#: plans it first. Every puzzle here is 10 x 10 and easy — the <=15 x easy
#: cell — so a one-puzzle book is planned by a one-puzzle plan.
ONE_SMALL_EASY_PUZZLE = DistributionPlan(
    count=1, split=Split(100, 0, 0), cells=((1, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0))
)


class Panel:
    """A store and a book manager, wired as ``create_app`` wires them."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory
        self.store = PuzzleReviewService(session_factory=session_factory)
        self.books = BookManager(session_factory=session_factory, puzzle_store=self.store)
        self.batch = (
            make_batch(session_factory) if session_factory is not None else "b-1"
        )

    def add(self, name="p.png"):
        return self.store.add_puzzle(
            grid=[[True] * 10 for _ in range(10)],
            clues_rows=[[10]] * 10,
            clues_cols=[[10]] * 10,
            width=10,
            height=10,
            theme="test",
            difficulty_score=10,
            difficulty_tier="easy",
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            batch_id=self.batch,
            source_image=name,
        )

    def book(self, *puzzle_ids, title="Winter", theme="christmas"):
        book_id = self.books.create_book(title, "a book", theme, "adults")
        if puzzle_ids:
            self.books.add_puzzles_to_book(book_id, list(puzzle_ids))
        return book_id

    def book_id_of(self, puzzle_id):
        return self.store.get_puzzle(puzzle_id).get("book_id")


@pytest.fixture(params=["memory", "db"])
def panel(request, tmp_path):
    """Both modes. The bug was that they disagreed."""
    if request.param == "memory":
        return Panel()
    return Panel(session_factory=sqlite_session_scope(tmp_path))


# --------------------------------------------------------------------------
# AC-1 / AC-4
# --------------------------------------------------------------------------


def test_deleting_a_book_releases_its_puzzles(panel):
    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)
    assert panel.book_id_of(puzzle_id) == book_id

    assert panel.books.delete_book(book_id)

    assert panel.book_id_of(puzzle_id) is None
    assert panel.store.get_puzzle(puzzle_id) is not None, "the puzzle went too"


def test_every_puzzle_of_the_book_is_released(panel):
    ids = [panel.add(f"{n}.png") for n in range(3)]
    book_id = panel.book(*ids)

    panel.books.delete_book(book_id)

    assert [panel.book_id_of(p) for p in ids] == [None, None, None]


# --------------------------------------------------------------------------
# AC-2 — the guard must not outlive the book
# --------------------------------------------------------------------------


def test_a_released_puzzle_is_curatable_again(panel):
    """The damage this card repairs, stated as the thing that must work.

    Before the fix this puzzle could not be rejected, restored, approved or
    deleted by anything — CARD-100's guard saw a `book_id` and refused, and no
    book existed to remove it from.
    """
    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)
    assert panel.store.reject_puzzle(puzzle_id) is False, "guarded while booked"

    panel.books.delete_book(book_id)

    assert panel.store.reject_puzzle(puzzle_id) is True
    assert panel.store.delete_rejected_in_batch(panel.batch).changed == 1
    assert panel.store.get_puzzle(puzzle_id) is None


def test_the_released_puzzle_counts_as_unassigned_again(panel):
    """It should come back to the book builder, which filters on this."""
    from nonogram.admin.puzzle_review import PuzzleFilter

    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)

    panel.books.delete_book(book_id)

    found = panel.store.filter_puzzles(PuzzleFilter(book_id="unassigned", limit=50))
    assert puzzle_id in {p["id"] for p in found.puzzles}


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


def test_deleting_one_book_leaves_anothers_puzzles_alone(panel):
    mine, theirs = panel.add("a.png"), panel.add("b.png")
    doomed = panel.book(mine, title="Doomed")
    kept = panel.book(theirs, title="Kept", theme="easter")

    panel.books.delete_book(doomed)

    assert panel.book_id_of(mine) is None
    assert panel.book_id_of(theirs) == kept


def test_a_published_book_is_still_refused(panel):
    """G-2-adjacent: the existing rule is not loosened by the release."""
    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)
    panel.books.save_plan(book_id, ONE_SMALL_EASY_PUZZLE)
    panel.books.set_book_status(book_id, "published")

    with pytest.raises(ValueError):
        panel.books.delete_book(book_id)

    assert panel.book_id_of(puzzle_id) == book_id, "released despite refusing"


def test_deleting_a_book_that_is_not_there_changes_nothing(panel):
    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)

    assert panel.books.delete_book("0f5b9a2c-1d3e-4f5a-8b7c-9d0e1f2a3b4c") is False

    assert panel.book_id_of(puzzle_id) == book_id


def test_a_manager_with_no_store_still_deletes_the_book(caplog):
    """The `_mirror_onto_puzzles` arrangement, for the delete path too."""
    lonely = BookManager(session_factory=None)
    book_id = lonely.create_book("Winter", "a book", "christmas", "adults")
    lonely.add_puzzles_to_book(book_id, ["p1"])

    with caplog.at_level("WARNING"):
        assert lonely.delete_book(book_id) is True

    assert lonely.get_book(book_id) is None
    assert "membership" in caplog.text.lower()
