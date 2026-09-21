"""CARD-100 — book membership is one fact, written where it is read.

    AC-1  a puzzle a book holds survives every bulk action
    AC-2  removing it from the book releases it again
    AC-3  a book never lists an id that is not in the store
    AC-4  the backfill fills in rows written before this card
    AC-5  per-puzzle Reject and Restore obey the same rule
    AC-6  mark_in_book works in DB mode
    AC-7  the bulk messages gain the clause CARD-068 left out
    AC-8  the book builder stops offering puzzles another book holds
    AC-9  get_approved_puzzles answers for a book

The reproduction this card exists for is `test_the_reproduction_from_the_card`
— written first, from the card, and failing on `main` at `8d81d17`.

Membership is `Puzzle.book_id`, a nullable column written by BookManager as it
edits `Book.puzzle_ids`. The `in_book` *status* is no longer written by
anything: it would destroy the row's real curation state (a puzzle is approved
AND in a book) and removal would have to guess what to restore. Rows that
already carry it keep being treated as in-a-book on the read side, the way
`difficulty.tier_of_record` still answers for the retired guess tier.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.puzzle_review import PuzzleFilter, PuzzleReviewService, PuzzleStatus
from tests.helpers.db import make_batch, sqlite_session_scope


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


class Panel:
    """A store and a book manager wired together the way ``create_app`` does."""

    #: The batch every puzzle here belongs to. In DB mode it is a row that
    #: really exists: ``puzzles.batch_id`` is a foreign key, and a fabricated
    #: id was accepted only while SQLite had foreign keys switched off
    #: (CARD-102).
    BATCH = "7c9e6679-7425-40de-944b-e07fc1f90ae7"

    def __init__(self, session_factory=None):
        self.store = PuzzleReviewService(session_factory=session_factory)
        self.books = BookManager(session_factory=session_factory, puzzle_store=self.store)
        if session_factory is not None:
            make_batch(session_factory, self.BATCH, source="random", total_count=0)

    def add(self, status="approved", batch_id=BATCH, name="p.png"):
        puzzle_id = self.store.add_puzzle(
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
            batch_id=batch_id,
            source_image=name,
        )
        if status == "approved":
            self.store.approve_puzzle(puzzle_id)
        elif status == "rejected":
            self.store.reject_puzzle(puzzle_id)
        return puzzle_id

    def book(self, *puzzle_ids, title="Winter"):
        book_id = self.books.create_book(title, "a book", "christmas", "adults")
        if puzzle_ids:
            self.books.add_puzzles_to_book(book_id, list(puzzle_ids))
        return book_id

    def book_id_of(self, puzzle_id):
        return self.store.get_puzzle(puzzle_id).get("book_id")


@pytest.fixture(params=["memory", "db"])
def panel(request, tmp_path):
    """AC-1/AC-5: both storage modes, side by side, for every rule."""
    if request.param == "memory":
        return Panel()
    return Panel(session_factory=sqlite_session_scope(tmp_path))


@pytest.fixture
def admin_app(monkeypatch):
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


# --------------------------------------------------------------------------
# AC-1 — the reproduction
# --------------------------------------------------------------------------


def test_the_reproduction_from_the_card(panel):
    """The exact sequence the card was opened with, which must now end well.

    The protection lands a step earlier than the card imagined: the puzzle can
    no longer be *rejected* while a book holds it, so "Delete rejected" never
    sees a candidate. Both guards are pinned — the refusal here, and the bulk
    path's own in `test_a_book_is_not_stripped_by_delete_rejected`.
    """
    puzzle_id = panel.add("approved")
    book_id = panel.book(puzzle_id)

    assert panel.store.reject_puzzle(puzzle_id) is False, "a booked puzzle was rejected"
    panel.store.delete_rejected_in_batch(Panel.BATCH)

    assert panel.store.get_puzzle(puzzle_id) is not None, "the puzzle was deleted"
    assert puzzle_id in panel.books.get_book(book_id).puzzle_ids


def test_a_book_is_not_stripped_by_delete_rejected(panel):
    """The bulk guard itself, reached by booking a puzzle already rejected."""
    puzzle_id = panel.add("rejected")
    panel.book(puzzle_id)

    outcome = panel.store.delete_rejected_in_batch(Panel.BATCH)

    assert (outcome.changed, outcome.in_book) == (0, 1)
    assert panel.store.get_puzzle(puzzle_id) is not None


def test_adding_a_puzzle_to_a_book_writes_it_on_the_puzzle(panel):
    puzzle_id = panel.add()

    book_id = panel.book(puzzle_id)

    assert panel.book_id_of(puzzle_id) == book_id


def test_adding_to_a_book_leaves_the_curation_status_alone(panel):
    """Decision 2: membership is a column, not a status.

    A puzzle is approved *and* in a book. Overwriting the status would lose
    the first fact and leave removal guessing what to restore.
    """
    puzzle_id = panel.add("approved")

    panel.book(puzzle_id)

    assert panel.store.get_puzzle(puzzle_id)["status"] == PuzzleStatus.APPROVED.value


def test_a_bulk_status_change_passes_over_a_booked_puzzle(panel):
    booked = panel.add("draft")
    loose = panel.add("draft")
    panel.book(booked)

    outcome = panel.store.set_batch_status(Panel.BATCH, PuzzleStatus.APPROVED)

    assert (outcome.changed, outcome.in_book) == (1, 1)
    assert panel.store.get_puzzle(booked)["status"] == PuzzleStatus.DRAFT.value
    assert panel.store.get_puzzle(loose)["status"] == PuzzleStatus.APPROVED.value


def test_a_row_carrying_only_the_legacy_status_is_still_in_a_book(panel):
    """Decision 2's read side: rows written before this card are not orphaned.

    ``mark_in_book`` wrote both the status and the column; a row that carries
    the ``in_book`` status without the column is what an older write left
    behind, and it is still a puzzle a book is built on. Nothing writes that
    status any more, and everything keeps reading it — the arrangement
    ``difficulty.tier_of_record`` uses for the retired guess tier.
    """
    puzzle_id = panel.add("draft")
    panel.store.mark_in_book(puzzle_id, "0f5b9a2c-1d3e-4f5a-8b7c-9d0e1f2a3b4c")
    panel.store.release_from_book([puzzle_id])  # the legacy shape: status only

    assert panel.store.get_puzzle(puzzle_id)["status"] == PuzzleStatus.IN_BOOK.value
    assert panel.store.get_puzzle(puzzle_id).get("book_id") is None
    assert panel.store.in_a_book(puzzle_id) is True
    assert panel.store.reject_puzzle(puzzle_id) is False
    assert panel.store.set_batch_status(Panel.BATCH, PuzzleStatus.APPROVED).in_book == 1


# --------------------------------------------------------------------------
# AC-2 / AC-3
# --------------------------------------------------------------------------


def test_removing_a_puzzle_from_a_book_releases_it(panel):
    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)

    assert panel.books.remove_puzzle_from_book(book_id, puzzle_id)

    assert panel.book_id_of(puzzle_id) is None
    assert panel.books.book_listing(puzzle_id) is None


def test_a_released_puzzle_can_then_be_rejected_and_deleted(panel):
    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)
    panel.books.remove_puzzle_from_book(book_id, puzzle_id)

    assert panel.store.reject_puzzle(puzzle_id)
    assert panel.store.delete_rejected_in_batch(Panel.BATCH).changed == 1
    assert panel.store.get_puzzle(puzzle_id) is None


def test_no_bulk_action_leaves_a_book_pointing_at_a_ghost(panel):
    """AC-3, stated as the invariant rather than as one sequence."""
    booked = [panel.add("rejected") for _ in range(2)]
    panel.add("rejected")
    book_id = panel.book(*booked)

    panel.store.set_batch_status(Panel.BATCH, PuzzleStatus.REJECTED)
    panel.store.delete_rejected_in_batch(Panel.BATCH)

    listed = panel.books.get_book(book_id).puzzle_ids
    assert listed
    assert all(panel.store.get_puzzle(pid) is not None for pid in listed)


# --------------------------------------------------------------------------
# AC-5 — the per-puzzle bypass
# --------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["reject_puzzle", "restore_puzzle", "approve_puzzle"])
def test_a_per_puzzle_status_change_refuses_a_booked_puzzle(panel, action):
    puzzle_id = panel.add("approved")
    panel.book(puzzle_id)

    assert getattr(panel.store, action)(puzzle_id) is False
    assert panel.store.get_puzzle(puzzle_id)["status"] == PuzzleStatus.APPROVED.value


def test_the_route_says_why_it_refused(admin_app):
    panel_store = admin_app.puzzle_review_service
    puzzle_id = panel_store.add_puzzle(
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
        batch_id=Panel.BATCH,
        source_image="p.png",
    )
    book_id = admin_app.book_manager.create_book("Winter", "a book", "christmas", "adults")
    admin_app.book_manager.add_puzzles_to_book(book_id, [puzzle_id])

    body = admin_app.test_client().post(
        f"/puzzle/{puzzle_id}/reject", follow_redirects=True
    ).get_data(as_text=True)

    # The exact flash, not a loose substring: "in a book" also appears in the
    # puzzles list's own lede, so a looser assertion passed while the route
    # still said "Puzzle not found".
    assert "Cannot reject a puzzle that is in a book" in body
    assert "Puzzle not found" not in body
    assert panel_store.get_puzzle(puzzle_id)["status"] != PuzzleStatus.REJECTED.value


# --------------------------------------------------------------------------
# AC-6 / AC-8 / AC-9 — the sites that read the column
# --------------------------------------------------------------------------


def test_mark_in_book_accepts_a_string_book_id(panel):
    """AC-6: the in-memory branch always did; the DB branch raised."""
    puzzle_id = panel.add()

    assert panel.store.mark_in_book(puzzle_id, "0f5b9a2c-1d3e-4f5a-8b7c-9d0e1f2a3b4c")

    assert panel.book_id_of(puzzle_id) == "0f5b9a2c-1d3e-4f5a-8b7c-9d0e1f2a3b4c"


def test_unassigned_means_not_in_any_book(panel):
    """AC-8: the filter the book builder uses to avoid offering a puzzle twice."""
    booked = panel.add()
    loose = panel.add()
    panel.book(booked)

    found = panel.store.filter_puzzles(PuzzleFilter(book_id="unassigned", limit=50))

    ids = {p["id"] for p in found.puzzles}
    assert loose in ids
    assert booked not in ids


def test_filtering_by_a_book_returns_its_puzzles(panel):
    mine = panel.add()
    theirs = panel.add()
    book_id = panel.book(mine, title="Mine")
    panel.book(theirs, title="Theirs")

    found = panel.store.filter_puzzles(PuzzleFilter(book_id=book_id, limit=50))

    assert {p["id"] for p in found.puzzles} == {mine}


def test_get_approved_puzzles_answers_for_a_book(panel):
    """AC-9: it filtered on two columns nothing wrote, so it was always empty."""
    mine = panel.add("approved")
    panel.add("approved")
    book_id = panel.book(mine)

    assert [p["id"] for p in panel.store.get_approved_puzzles(book_id)] == [mine]


# --------------------------------------------------------------------------
# AC-7 — the clause CARD-068 left out
# --------------------------------------------------------------------------


def test_the_bulk_report_names_what_a_book_held_back(admin_app):
    import re

    store = admin_app.puzzle_review_service
    batch_id = admin_app.batch_generator.create_batch(
        count=1, sizes=[10], theme="image", source="images", quality_filter=0
    )

    def add():
        pid = store.add_puzzle(
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
            batch_id=batch_id,
            source_image="p.png",
        )
        store.reject_puzzle(pid)
        return pid

    add()
    booked = add()
    book_id = admin_app.book_manager.create_book("Winter", "a book", "christmas", "adults")
    admin_app.book_manager.add_puzzles_to_book(book_id, [booked])

    body = admin_app.test_client().post(
        f"/batch/{batch_id}/delete-rejected", follow_redirects=True
    ).get_data(as_text=True)
    (message, *_) = re.findall(
        r'<div class="alert alert-\w+[^"]*"[^>]*>\s*(.*?)\s*<button', body, re.S
    )

    assert "Deleted 1 rejected puzzle" in message
    assert "1 left alone: in a book" in message


# --------------------------------------------------------------------------
# AC-4 — the backfill
# --------------------------------------------------------------------------


def _orphan_the_column(panel, *puzzle_ids):
    """Put a puzzle back into the state this card is repairing.

    A book that lists a puzzle whose row says nothing — which is every book
    made before this card.
    """
    for puzzle_id in puzzle_ids:
        panel.store.release_from_book([puzzle_id])


def test_the_backfill_reports_before_it_writes(panel):
    from nonogram.admin.book_membership import backfill

    puzzle_id = panel.add()
    book_id = panel.book(puzzle_id)
    _orphan_the_column(panel, puzzle_id)

    outcome = backfill(panel.books, panel.store, dry_run=True)

    assert outcome.dry_run is True
    assert outcome.repaired == 1
    assert outcome.books_seen == 1
    assert panel.book_id_of(puzzle_id) is None, "a dry run wrote something"
    assert book_id  # the book is untouched either way


def test_the_backfill_writes_what_it_reported(panel):
    from nonogram.admin.book_membership import backfill

    puzzle_id = panel.add()
    panel.book(puzzle_id)
    _orphan_the_column(panel, puzzle_id)

    planned = backfill(panel.books, panel.store, dry_run=True)
    done = backfill(panel.books, panel.store, dry_run=False)

    assert (done.repaired, done.books_seen) == (planned.repaired, planned.books_seen)
    assert panel.book_id_of(puzzle_id) is not None


def test_the_backfill_is_idempotent(panel):
    from nonogram.admin.book_membership import backfill

    puzzle_id = panel.add()
    panel.book(puzzle_id)
    _orphan_the_column(panel, puzzle_id)
    backfill(panel.books, panel.store, dry_run=False)

    again = backfill(panel.books, panel.store, dry_run=False)

    assert again.repaired == 0
    assert again.already == 1


def test_the_backfill_reports_a_book_listing_a_missing_puzzle(panel):
    """The ghosts this card's absence already created are named, not fixed."""
    from nonogram.admin.book_membership import backfill

    puzzle_id = panel.add()
    panel.book(puzzle_id)
    _orphan_the_column(panel, puzzle_id)
    panel.store.delete_puzzle(puzzle_id)

    outcome = backfill(panel.books, panel.store, dry_run=True)

    assert outcome.repaired == 0
    assert outcome.missing == (puzzle_id,)


def test_the_backfill_touches_nothing_but_the_column(panel):
    from nonogram.admin.book_membership import backfill

    puzzle_id = panel.add("approved")
    panel.book(puzzle_id)
    _orphan_the_column(panel, puzzle_id)
    before = dict(panel.store.get_puzzle(puzzle_id))

    backfill(panel.books, panel.store, dry_run=False)

    after = panel.store.get_puzzle(puzzle_id)
    changed = {k for k in before if before[k] != after.get(k)}
    assert changed == {"book_id"}


def test_a_puzzle_in_two_books_is_reported_not_guessed(panel):
    """Only possible because the bug allowed it; the backfill must not pick."""
    from nonogram.admin.book_membership import backfill

    puzzle_id = panel.add()
    panel.book(puzzle_id, title="First")
    _orphan_the_column(panel, puzzle_id)
    panel.book(puzzle_id, title="Second")
    _orphan_the_column(panel, puzzle_id)

    outcome = backfill(panel.books, panel.store, dry_run=True)

    assert outcome.repaired == 0
    assert puzzle_id in dict(outcome.contested)


# --------------------------------------------------------------------------
# the wiring this all depends on
# --------------------------------------------------------------------------


def test_the_app_wires_the_book_manager_to_the_store(admin_app):
    """Without this, membership silently stops being mirrored."""
    assert admin_app.book_manager.puzzle_store is admin_app.puzzle_review_service


def test_a_book_manager_with_no_store_says_so_rather_than_pretending(panel, caplog):
    lonely = BookManager(session_factory=None)
    book_id = lonely.create_book("Winter", "a book", "christmas", "adults")

    with caplog.at_level("WARNING"):
        lonely.add_puzzles_to_book(book_id, ["p1"])

    assert "membership" in caplog.text.lower()


# --------------------------------------------------------------------------
# the operator entry point
# --------------------------------------------------------------------------


def test_the_command_refuses_when_there_is_no_database(monkeypatch):
    """An in-memory panel has nothing durable to repair, and says so."""
    from nonogram.admin import book_membership

    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit) as exit_info:
        book_membership.main([])

    assert "DATABASE_URL" in str(exit_info.value)


def test_the_command_reports_without_writing_by_default(panel, monkeypatch, capsys):
    from nonogram.admin import book_membership

    puzzle_id = panel.add()
    panel.book(puzzle_id)
    panel.store.release_from_book([puzzle_id])
    monkeypatch.setattr(book_membership, "_services", lambda: (panel.books, panel.store))

    assert book_membership.main([]) == 0

    printed = capsys.readouterr().out
    assert "would repair 1" in printed
    assert "Re-run with --write" in printed
    assert panel.book_id_of(puzzle_id) is None


def test_the_command_writes_when_told_to(panel, monkeypatch, capsys):
    from nonogram.admin import book_membership

    puzzle_id = panel.add()
    panel.book(puzzle_id)
    panel.store.release_from_book([puzzle_id])
    monkeypatch.setattr(book_membership, "_services", lambda: (panel.books, panel.store))

    assert book_membership.main(["--write"]) == 0

    printed = capsys.readouterr().out
    assert "repaired 1" in printed and "would repair" not in printed
    assert panel.book_id_of(puzzle_id) is not None


def test_the_command_names_what_it_will_not_decide(panel, monkeypatch, capsys):
    from nonogram.admin import book_membership

    puzzle_id = panel.add()
    panel.book(puzzle_id, title="First")
    panel.store.release_from_book([puzzle_id])
    panel.book(puzzle_id, title="Second")
    panel.store.release_from_book([puzzle_id])
    monkeypatch.setattr(book_membership, "_services", lambda: (panel.books, panel.store))

    book_membership.main([])

    printed = capsys.readouterr().out
    assert "claimed by two books" in printed
    assert puzzle_id in printed
    assert "need a decision this command will not make" in printed
