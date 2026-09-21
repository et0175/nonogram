"""CARD-068 — the per-puzzle Delete, and bulk actions that say what they did.

    AC-1  Delete removes a rejected puzzle and returns to the same batch
    AC-3  every bulk action reports what it changed AND what it passed over
    AC-4  nothing in a book is touched, nothing in another batch is touched
    AC-5  the store's bulk operations work in both modes
    AC-6  each bulk confirmation names the count it is about
    AC-7  Delete is offered only where the rule allows it (option (a))

Option (a), the owner's pick: a puzzle must be rejected before it can be
deleted. The card's alternative was Delete from any status but in-a-book; this
page is a grid of near-identical thumbnails judged quickly, which is the worst
place for a one-click irreversible delete.

AC-6 is pinned twice. Naming a count is easy; naming the *right* count is the
part that rots, because the number on the button is computed from the page's
rows and the number in the flash from the store's own filter. The drift guard
is ``test_the_promised_count_is_what_the_action_reports``: it clicks the button
and compares.
"""

from __future__ import annotations

import re
import uuid
from contextlib import contextmanager

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.puzzle_review import PuzzleReviewService, PuzzleStatus
from tests.helpers.db import make_batch, sqlite_session_scope


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    # The in-memory book manager is a module singleton and in-memory puzzle ids
    # restart at puzzle_000001 with every app, so a book left behind by an
    # earlier test lists ids this one is about to mint. Reset it with the rest.
    book_manager_module._book_manager = book_manager_module.BookManager(
        session_factory=None
    )
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


@pytest.fixture(params=["memory", "db"])
def store(request, tmp_path):
    """AC-5: the two branches of every bulk operation, run side by side.

    In DB mode the store carries the session factory its batches live in, so
    a test can make one: ``puzzles.batch_id`` is a foreign key (CARD-102).
    """
    if request.param == "memory":
        store = PuzzleReviewService()
        store.session_factory_for_tests = None
        return store
    scope = sqlite_session_scope(tmp_path)
    store = PuzzleReviewService(session_factory=scope)
    store.session_factory_for_tests = scope
    return store


def _add(store, status="draft", batch_id=None, name="p.png"):
    puzzle_id = store.add_puzzle(
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
        store.approve_puzzle(puzzle_id)
    elif status == "rejected":
        store.reject_puzzle(puzzle_id)
    return puzzle_id


def _in_book(store, puzzle_id, book_id="0f5b9a2c-1d3e-4f5a-8b7c-9d0e1f2a3b4c"):
    """Mark a puzzle as belonging to a book, the only way the store allows.

    ``mark_in_book`` sets the status to ``in_book`` as well as the column, so a
    *rejected* puzzle that a book holds is reached by rejecting it afterwards —
    ``reject_puzzle`` rewrites the status and leaves ``book_id`` alone, which is
    its own defect (CARD-100).
    """
    store.mark_in_book(puzzle_id, uuid.UUID(book_id))
    return puzzle_id


def _rejected_in_book(store, puzzle_id):
    """A rejected puzzle that a book also holds.

    Reject first, then book it through ``assign_to_book`` — the writer
    :class:`BookManager` uses, which records membership and leaves the curation
    status alone. The legacy ``mark_in_book`` would overwrite "rejected" with
    the ``in_book`` status and there would be nothing for
    ``delete_rejected_in_batch`` to consider. Booking first is impossible now:
    CARD-100 refuses to reject a puzzle a book already holds, which is the
    stronger guarantee.
    """
    store.reject_puzzle(puzzle_id)
    store.assign_to_book([puzzle_id], "0f5b9a2c-1d3e-4f5a-8b7c-9d0e1f2a3b4c")
    return puzzle_id


def _batch_id(store=None):
    """A batch id, backed by a real row whenever there is a database.

    In-memory mode has no ``batches`` table and needs none. In DB mode the row
    has to exist, because ``puzzles.batch_id`` is a foreign key — the suite
    only ever got away without it while SQLite had enforcement off (CARD-102).
    """
    scope = getattr(store, "session_factory_for_tests", None)
    if scope is None:
        return str(uuid.uuid4())
    return make_batch(scope)


def _real_batch(app):
    """A batch the batch generator has actually recorded.

    The bulk routes check the batch exists before acting, so a bare uuid would
    be answered with "Batch not found" and never reach the store.
    """
    return app.batch_generator.create_batch(
        count=1, sizes=[10], theme="image", source="images", quality_filter=0
    )


def _page(app, batch_id):
    return app.test_client().get(f"/batch/{batch_id}/generated-puzzles").get_data(
        as_text=True
    )


def _flashes(app, response_path, **post):
    """POST and read the flash messages off the page it lands on."""
    client = app.test_client()
    body = client.post(response_path, follow_redirects=True, **post).get_data(
        as_text=True
    )
    return re.findall(r'<div class="alert alert-\w+[^"]*"[^>]*>\s*(.*?)\s*<button', body, re.S)


# --------------------------------------------------------------------------
# AC-1 / AC-7 — the per-puzzle Delete
# --------------------------------------------------------------------------


def test_deleting_a_rejected_puzzle_returns_to_the_same_batch(admin_app):
    batch_id = _batch_id()
    puzzle_id = _add(admin_app.puzzle_review_service, "rejected", batch_id)

    response = admin_app.test_client().post(
        f"/puzzle/{puzzle_id}/delete?batch_id={batch_id}"
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/batch/{batch_id}/generated-puzzles")
    assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) is None


def test_a_delete_without_a_batch_still_goes_to_the_library(admin_app):
    """G-2: the existing caller of this route keeps its behaviour."""
    puzzle_id = _add(admin_app.puzzle_review_service, "rejected")

    response = admin_app.test_client().post(f"/puzzle/{puzzle_id}/delete")

    assert response.status_code == 302
    assert "/generated-puzzles" not in response.headers["Location"]


@pytest.mark.parametrize("status", ["draft", "approved"])
def test_delete_refuses_a_puzzle_that_is_not_rejected(admin_app, status):
    """Option (a): rejection is the gesture that makes deletion possible."""
    batch_id = _batch_id()
    puzzle_id = _add(admin_app.puzzle_review_service, status, batch_id)

    response = admin_app.test_client().post(
        f"/puzzle/{puzzle_id}/delete?batch_id={batch_id}"
    )

    assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) is not None
    assert response.headers["Location"].endswith(f"/batch/{batch_id}/generated-puzzles")


def test_delete_refuses_a_rejected_puzzle_that_is_in_a_book(admin_app):
    batch_id = _batch_id()
    puzzle_id = _add(admin_app.puzzle_review_service, "rejected", batch_id)
    _in_book(admin_app.puzzle_review_service, puzzle_id)

    admin_app.test_client().post(f"/puzzle/{puzzle_id}/delete?batch_id={batch_id}")

    assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) is not None


def test_delete_refuses_a_puzzle_a_book_lists(admin_app):
    """The guard that matters, and the one production can trigger.

    Written when a puzzle added to a book kept ``book_id = None`` — membership
    lived in ``Book.puzzle_ids`` alone, so a Delete that trusted the puzzle row
    would destroy a puzzle a book was built on. CARD-100 made the two halves
    agree, so the row now knows as well, and this test pins both answers: the
    route still asks the book side, and the column no longer lies.
    """
    batch_id = _real_batch(admin_app)
    puzzle_id = _add(admin_app.puzzle_review_service, "rejected", batch_id)
    book_id = admin_app.book_manager.create_book(
        "Winter", "a winter book", "christmas", "adults"
    )
    admin_app.book_manager.add_puzzles_to_book(book_id, [puzzle_id])

    # Both halves of membership now agree (CARD-100); before it, the column
    # was None here and the route's second question was the only guard.
    assert admin_app.puzzle_review_service.get_puzzle(puzzle_id).get("book_id") == book_id
    assert admin_app.book_manager.book_listing(puzzle_id) == book_id

    admin_app.test_client().post(f"/puzzle/{puzzle_id}/delete?batch_id={batch_id}")

    assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) is not None
    assert puzzle_id in admin_app.book_manager.get_book(book_id).puzzle_ids


def test_book_listing_names_the_book_that_holds_a_puzzle(admin_app):
    books = admin_app.book_manager
    loose = _add(admin_app.puzzle_review_service, "rejected", _real_batch(admin_app))
    held = _add(admin_app.puzzle_review_service, "rejected", _real_batch(admin_app))
    book_id = books.create_book("Winter", "a winter book", "christmas", "adults")
    books.add_puzzles_to_book(book_id, [held])

    assert books.book_listing(held) == book_id
    assert books.book_listing(loose) is None


def test_the_page_offers_delete_on_a_rejected_card_only(admin_app):
    """AC-7: the button is not shown where the route would refuse it."""
    batch_id = _real_batch(admin_app)
    rejected = _add(admin_app.puzzle_review_service, "rejected", batch_id, "r.png")
    draft = _add(admin_app.puzzle_review_service, "draft", batch_id, "d.png")

    body = _page(admin_app, batch_id)

    assert f'action="/puzzle/{rejected}/delete?batch_id={batch_id}"' in body
    assert f'action="/puzzle/{draft}/delete?batch_id={batch_id}"' in body
    # Both forms exist so rejecting can reveal one without a reload; only the
    # draft's is hidden.
    assert "hidden" in _delete_form(body, draft)
    assert "hidden" not in _delete_form(body, rejected)


def _delete_form(body: str, puzzle_id: str) -> str:
    """The opening tag of that puzzle's delete form."""
    start = body.rindex("<form", 0, body.index(f'action="/puzzle/{puzzle_id}/delete'))
    return body[start : body.index(">", start)]


def test_every_puzzle_keeps_its_own_delete_control(admin_app):
    """G-5: grouping must not make one control stand for several puzzles."""
    batch_id = _real_batch(admin_app)
    for _ in range(3):
        _add(admin_app.puzzle_review_service, "rejected", batch_id, "same.png")

    body = _page(admin_app, batch_id)

    assert body.count('data-action="delete"') == 3


# --------------------------------------------------------------------------
# AC-6 — the confirmations name their count
# --------------------------------------------------------------------------


def test_each_bulk_confirmation_names_its_count(admin_app):
    batch_id = _real_batch(admin_app)
    _add(admin_app.puzzle_review_service, "draft", batch_id)
    _add(admin_app.puzzle_review_service, "draft", batch_id)
    _add(admin_app.puzzle_review_service, "rejected", batch_id)

    body = _page(admin_app, batch_id)

    assert "Approve all 3 puzzles in this batch?" in body
    assert "Reject all 2 puzzles in this batch?" in body
    assert "Delete the 1 rejected puzzle in this batch?" in body


def test_a_bulk_button_with_nothing_to_do_is_disabled(admin_app):
    batch_id = _real_batch(admin_app)
    _add(admin_app.puzzle_review_service, "approved", batch_id)

    body = _page(admin_app, batch_id)
    approve = body[body.index("/approve-all") : body.index("/approve-all") + 400]
    delete = body[body.index("/delete-rejected") : body.index("/delete-rejected") + 400]

    assert "disabled" in approve
    assert "disabled" in delete


def test_the_counts_ignore_puzzles_in_a_book_and_other_batches(admin_app):
    batch_id = _real_batch(admin_app)
    _add(admin_app.puzzle_review_service, "draft", batch_id)
    _in_book(
        admin_app.puzzle_review_service,
        _add(admin_app.puzzle_review_service, "draft", batch_id),
    )
    _add(admin_app.puzzle_review_service, "draft", _batch_id())

    assert "Approve 1 puzzle in this batch?" in _page(admin_app, batch_id)


@pytest.mark.parametrize(
    "action,past,route",
    [("Approve", "Approved", "approve-all"), ("Reject", "Rejected", "reject-all")],
)
def test_the_promised_count_is_what_the_action_reports(admin_app, action, past, route):
    """The drift guard: the button's number and the store's number are two
    computations of one fact, and nothing else in this suite compares them."""
    batch_id = _real_batch(admin_app)
    _add(admin_app.puzzle_review_service, "draft", batch_id)
    _add(admin_app.puzzle_review_service, "approved", batch_id)
    _add(admin_app.puzzle_review_service, "rejected", batch_id)
    _in_book(
        admin_app.puzzle_review_service,
        _add(admin_app.puzzle_review_service, "draft", batch_id),
    )

    body = _page(admin_app, batch_id)
    promised = int(re.search(rf"{action} (?:all )?(\d+) puzzles? in this batch\?", body).group(1))

    (message, *_) = _flashes(admin_app, f"/batch/{batch_id}/{route}")

    assert message.startswith(f"{past} {promised} puzzle")


# --------------------------------------------------------------------------
# AC-3 — the bulk actions say what they passed over
# --------------------------------------------------------------------------


def test_the_page_makes_no_claim_about_puzzles_a_book_holds(admin_app):
    """CARD-100: the in-book number is zero however many a book really lists.

    Membership is written to ``Book.puzzle_ids`` and every guard here reads
    ``Puzzle.book_id``, which nothing in production sets. So this card reports
    what it changed and says nothing about what a book held back — a confident
    "0 left alone: in a book" would be worse than silence. The store counts it
    either way (see the store tests below), so the clause is a sentence away
    once CARD-100 makes the number true.
    """
    batch_id = _real_batch(admin_app)
    _add(admin_app.puzzle_review_service, "rejected", batch_id)
    _add(admin_app.puzzle_review_service, "rejected", batch_id)

    (message, *_) = _flashes(admin_app, f"/batch/{batch_id}/delete-rejected")

    assert message.strip() == "Deleted 2 rejected puzzles."
    assert "in a book" not in message


def test_approve_all_reports_the_ones_already_approved(admin_app):
    batch_id = _real_batch(admin_app)
    _add(admin_app.puzzle_review_service, "draft", batch_id)
    _add(admin_app.puzzle_review_service, "approved", batch_id)
    _add(admin_app.puzzle_review_service, "approved", batch_id)

    (message, *_) = _flashes(admin_app, f"/batch/{batch_id}/approve-all")

    assert "Approved 1 puzzle" in message
    assert "2 were already approved" in message


def test_a_clean_bulk_action_says_only_what_it_did(admin_app):
    batch_id = _real_batch(admin_app)
    _add(admin_app.puzzle_review_service, "draft", batch_id)
    _add(admin_app.puzzle_review_service, "draft", batch_id)

    (message, *_) = _flashes(admin_app, f"/batch/{batch_id}/approve-all")

    assert message.strip() == "Approved 2 puzzles."


# --------------------------------------------------------------------------
# AC-4 / AC-5 — the store, in both modes
# --------------------------------------------------------------------------


def test_set_batch_status_counts_changed_unchanged_and_held_back(store):
    batch_id = _batch_id(store)
    _add(store, "draft", batch_id)
    _add(store, "approved", batch_id)
    _in_book(store, _add(store, "draft", batch_id))
    _add(store, "draft", _batch_id(store))

    outcome = store.set_batch_status(batch_id, PuzzleStatus.APPROVED)

    assert (outcome.changed, outcome.unchanged, outcome.in_book) == (1, 1, 1)


def test_delete_rejected_counts_deleted_and_held_back(store):
    batch_id = _batch_id(store)
    _add(store, "rejected", batch_id)
    _rejected_in_book(store, _add(store, "draft", batch_id))
    _add(store, "draft", batch_id)
    other = _add(store, "rejected", _batch_id(store))

    outcome = store.delete_rejected_in_batch(batch_id)

    assert (outcome.changed, outcome.in_book) == (1, 1)
    assert store.get_puzzle(other) is not None


def test_batch_action_counts_predict_each_action(store):
    batch_id = _batch_id(store)
    _add(store, "draft", batch_id)
    _add(store, "draft", batch_id)
    _add(store, "approved", batch_id)
    _add(store, "rejected", batch_id)
    _in_book(store, _add(store, "draft", batch_id))

    counts = store.batch_action_counts(batch_id)

    assert counts == {"approve": 3, "reject": 3, "delete_rejected": 1}
    assert store.set_batch_status(batch_id, PuzzleStatus.APPROVED).changed == 3


def test_batch_action_counts_of_an_unknown_batch_are_zero(store):
    assert store.batch_action_counts(_batch_id()) == {
        "approve": 0,
        "reject": 0,
        "delete_rejected": 0,
    }
