"""CARD-142 — the batch's bulk buttons keep up with per-puzzle approve/reject.

    AC-1  rejecting one puzzle by fetch enables Delete rejected, naming 1
    AC-2  approve and reject report fresh counts to a JSON caller only
    AC-3  the counts a JSON caller receives are the batch's counts
    AC-4  a refused action (a puzzle a book holds) leaves the counts alone

The screen posts the per-puzzle Approve and Reject by ``fetch`` and never
reloads, so the three bulk buttons kept whatever ``batch_action_counts`` said
when the page was rendered. The fix is one number travelling: the endpoints
report the batch's counts to the caller that asks for JSON, and the script
applies them.

Nothing here executes the page's JavaScript — there is no engine in the
dependency baseline. So the two halves are pinned separately and deliberately:
:func:`_assert_wiring` pins that the script does read ``data.action_counts``
and drives *both* halves of the display rule off it — the ``disabled`` state
and the sentence the confirmation names — and :func:`_apply_counts` is an
independent second implementation of that display rule (disabled below one,
which sentence gets the number) written from the data attributes the page
renders. The counting rule itself is never reimplemented here — the tests
compare against the store, which is the one place it lives.

The wiring pins read the script's source, so they are written to survive a
reformat: they name the function that must do the applying and the attributes
it must read, and match the one expression they cannot avoid by shape rather
than by spelling.
"""

from __future__ import annotations

import re
import uuid
from html.parser import HTMLParser

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module


JSON = {"Accept": "application/json"}
#: What a browser actually sends for a form post / a document request.
BROWSER = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}


# --------------------------------------------------------------------------
# fixtures and helpers
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    book_manager_module._book_manager = book_manager_module.BookManager(
        session_factory=None
    )
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


@pytest.fixture
def batch_id(admin_app):
    """A batch the generator has recorded — the review screen renders no other.

    ``source="images"`` with no images uploaded records the job and generates
    nothing, so the batch holds exactly the puzzles a test puts in it.
    """
    return admin_app.batch_generator.create_batch(
        count=1, sizes=[10], theme="image", source="images", quality_filter=0
    )


def _add(app, batch_id, status="draft", name="p.png"):
    store = app.puzzle_review_service
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


def _book(app, puzzle_id):
    """Put a puzzle in a book, the way the panel does (CARD-100)."""
    book_id = app.book_manager.create_book("Winter", "a book", "christmas", "adults")
    app.book_manager.add_puzzles_to_book(book_id, [puzzle_id])
    return book_id


def _page(app, batch_id):
    return (
        app.test_client()
        .get(f"/batch/{batch_id}/generated-puzzles")
        .get_data(as_text=True)
    )


class _BulkButtons(HTMLParser):
    """The three bulk buttons as the browser would see them.

    Keyed by ``data-bulk-action`` — the same keys ``batch_action_counts``
    returns, which is what lets the script pair a count with a button without
    knowing anything about either.
    """

    def __init__(self):
        super().__init__()
        self.buttons = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-bulk-action" in attrs:
            self.buttons[attrs["data-bulk-action"]] = dict(
                attrs, disabled="disabled" in attrs
            )


def _bulk_buttons(body):
    parser = _BulkButtons()
    parser.feed(body)
    assert set(parser.buttons) == {"approve", "reject", "delete_rejected"}, (
        "the page must offer all three bulk buttons, keyed by the count they use"
    )
    return parser.buttons


def _apply_counts(buttons, counts):
    """What the page will show once the script applies ``counts``.

    An independent reading of the display rule, from the attributes the page
    renders rather than from the script: a button with nothing to do is
    disabled, and the confirmation names the number in the sentence that
    matches its plurality.
    """
    shown = {}
    for action, count in counts.items():
        button = buttons[action]
        sentence = button["data-confirm-one" if count == 1 else "data-confirm-many"]
        shown[action] = (count == 0, sentence.replace("{n}", str(count)))
    return shown


#: The one function the fetch handler hands the server's counts to. Pinning a
#: name the page chose on purpose, rather than an expression's spelling, is
#: what keeps these assertions about intent.
APPLIER = "applyActionCounts"

#: ``button.disabled = count === 0`` by shape: something's ``disabled`` is
#: assigned the result of a strict comparison against zero. Parentheses, a
#: trailing semicolon or a renamed loop variable all still match; ``!==``, a
#: different threshold, or the assignment going away do not.
_DISABLED_BELOW_ONE = re.compile(r"\.disabled\s*=\s*\(?\s*\w+\s*===\s*0\s*\)?")

#: The ``{n}`` in the rendered sentence is where the fresh number goes.
_FILLS_IN_THE_NUMBER = re.compile(r"\.replace\(\s*['\"]\{n\}['\"]")

#: The confirmation the browser will actually ask is the form's own handler,
#: so re-filling the sentence means replacing that handler.
_REPLACES_THE_HANDLER = re.compile(r"\.onsubmit\s*=")


def _applier_source(script):
    """The body of the function the counts are handed to.

    Sliced by brace depth from its declaration so that the assertions below
    are about the function that does the applying, not about the script as a
    whole — a page that merely mentioned the attributes somewhere else would
    not satisfy them.
    """
    start = script.index("function " + APPLIER)
    depth = 0
    for index in range(script.index("{", start), len(script)):
        depth += {"{": 1, "}": -1}.get(script[index], 0)
        if depth == 0:
            return script[start : index + 1]
    raise AssertionError(f"{APPLIER} must be a complete function")


def _assert_wiring(body):
    """The script really does drive the buttons off what the server sent.

    Without this, :func:`_apply_counts` would happily describe a page whose
    handler ignores the response — or one that applies only the half of the
    rule that greys a button out and leaves the confirmation naming the digit
    the page was rendered with, which is half the bug this card exists to fix.
    """
    script = body[body.index("<script>") :]
    assert "'Accept': 'application/json'" in script, "the fetch must ask for JSON"

    # The counts applied are the ones the action just taken reported, not the
    # ones the page loaded with.
    after_fetch = script[script.index("fetch(") :]
    assert re.search(rf"{APPLIER}\([^)]*action_counts", after_fetch), (
        f"the fetch handler must hand the server's own counts to {APPLIER}()"
    )
    # A refusal says why (CARD-100's wording), instead of a bare "Error".
    assert "data.message" in after_fetch, "the server's reason must reach the owner"
    # Applying the counts is bookkeeping for the bulk buttons: it may not
    # repaint a per-puzzle action the server actually performed.
    assert re.search(rf"try\s*\{{[^}}]*{APPLIER}\(", after_fetch), (
        f"a throw inside {APPLIER}() must not reach the shared catch"
    )

    applier = _applier_source(script)
    assert "[data-bulk-action]" in applier, "every bulk button must be updated"
    # Half one: a button with nothing to do is disabled.
    assert _DISABLED_BELOW_ONE.search(applier), "a count of zero must disable"
    # Half two: …and the confirmation of a button that is *not* disabled names
    # the fresh number, in the sentence that matches its plurality.
    assert "dataset.confirmOne" in applier, "the singular sentence must be read"
    assert "dataset.confirmMany" in applier, "the plural sentence must be read"
    assert _FILLS_IN_THE_NUMBER.search(applier), "{n} must be filled in"
    assert _REPLACES_THE_HANDLER.search(applier), (
        "the rendered onsubmit still names the old number until it is replaced"
    )
    assert "confirm(" in applier, "the refilled sentence must be what is asked"
    # G-2: the rules are the store's. The page may not count cards of its own.
    assert ".result-card" not in script


def _counts_from_the_store(app, puzzle_ids):
    """The three counts, reimplemented from the rows rather than asked for.

    The rule (CARD-068): a puzzle a book holds is out of reach of every bulk
    action; of the rest, Approve touches what is not approved, Reject what is
    not rejected, and Delete rejected what is rejected.
    """
    store = app.puzzle_review_service
    counts = {"approve": 0, "reject": 0, "delete_rejected": 0}
    for puzzle_id in puzzle_ids:
        puzzle = store.get_puzzle(puzzle_id)
        if puzzle is None:
            continue
        status = puzzle["status"]
        if puzzle.get("book_id") or status == "in_book":
            continue
        counts["approve"] += status != "approved"
        counts["reject"] += status != "rejected"
        counts["delete_rejected"] += status == "rejected"
    return counts


# --------------------------------------------------------------------------
# AC-1 — the symptom the owner reported
# --------------------------------------------------------------------------


class TestBulkButtons_SingleRejectEnablesDeleteRejected:
    def test_the_page_starts_with_delete_rejected_disabled(self, admin_app, batch_id):
        """The state the bug left behind for good — the before half."""
        _add(admin_app, batch_id)
        _add(admin_app, batch_id)

        buttons = _bulk_buttons(_page(admin_app, batch_id))

        assert buttons["delete_rejected"]["disabled"] is True

    def test_rejecting_one_puzzle_enables_delete_rejected_naming_one(
        self, admin_app, batch_id
    ):
        first = _add(admin_app, batch_id)
        _add(admin_app, batch_id)
        body = _page(admin_app, batch_id)
        _assert_wiring(body)
        forms = _bulk_buttons(body)

        response = admin_app.test_client().post(
            f"/puzzle/{first}/reject?batch_id={batch_id}", headers=JSON
        )

        counts = response.get_json()["action_counts"]
        assert counts["delete_rejected"] == 1
        disabled, sentence = _apply_counts(forms, counts)["delete_rejected"]
        assert disabled is False
        assert sentence == (
            "Delete the 1 rejected puzzle in this batch? This cannot be undone."
        )

    def test_approve_all_and_reject_all_follow_the_same_action(
        self, admin_app, batch_id
    ):
        """The owner named one button; all three go stale by one mechanism."""
        first = _add(admin_app, batch_id)
        forms = _bulk_buttons(_page(admin_app, batch_id))

        counts = (
            admin_app.test_client()
            .post(f"/puzzle/{first}/approve?batch_id={batch_id}", headers=JSON)
            .get_json()["action_counts"]
        )

        shown = _apply_counts(forms, counts)
        # The batch's only puzzle is approved now: nothing left to approve,
        # one thing left to reject, nothing to delete.
        assert shown["approve"] == (True, "Approve all 0 puzzles in this batch?")
        assert shown["reject"] == (False, "Reject 1 puzzle in this batch?")
        assert shown["delete_rejected"][0] is True

    def test_the_rendered_sentence_and_the_refilled_one_agree(
        self, admin_app, batch_id
    ):
        """One wording, two readings: what the page shipped with is what the
        script would rebuild for the same count."""
        _add(admin_app, batch_id, "rejected")
        _add(admin_app, batch_id, "rejected")
        body = _page(admin_app, batch_id)
        forms = _bulk_buttons(body)

        counts = admin_app.puzzle_review_service.batch_action_counts(batch_id)

        for action, (_, sentence) in _apply_counts(forms, counts).items():
            assert sentence in body, f"{action}: the page and the script disagree"


# --------------------------------------------------------------------------
# AC-2 — the endpoints answer a JSON caller, and only a JSON caller
# --------------------------------------------------------------------------


class TestBulkButtons_ActionsReportCountsToJsonCallersOnly:
    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_a_json_caller_gets_the_counts(self, admin_app, batch_id, action):
        puzzle_id = _add(admin_app, batch_id)

        response = admin_app.test_client().post(
            f"/puzzle/{puzzle_id}/{action}?batch_id={batch_id}", headers=JSON
        )

        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert set(response.get_json()["action_counts"]) == {
            "approve",
            "reject",
            "delete_rejected",
        }

    @pytest.mark.parametrize("action", ["approve", "reject"])
    @pytest.mark.parametrize("headers", [{}, BROWSER], ids=["bare", "browser"])
    def test_a_form_post_still_gets_todays_redirect(
        self, admin_app, batch_id, action, headers
    ):
        """G-1: the no-JavaScript path is the default, not the fallback."""
        puzzle_id = _add(admin_app, batch_id)

        response = admin_app.test_client().post(
            f"/puzzle/{puzzle_id}/{action}?batch_id={batch_id}", headers=headers
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith(
            f"/batch/{batch_id}/generated-puzzles"
        )

    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_a_json_caller_without_a_batch_still_acts(self, admin_app, action):
        """The library's own rows post the same routes with no batch, so the
        counts are simply absent rather than the request being refused."""
        puzzle_id = _add(admin_app, None)

        response = admin_app.test_client().post(
            f"/puzzle/{puzzle_id}/{action}", headers=JSON
        )

        assert response.status_code == 200
        assert "action_counts" not in response.get_json()
        expected = "approved" if action == "approve" else "rejected"
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id)["status"] == expected


# --------------------------------------------------------------------------
# AC-3 — the number travelling is the batch's number
# --------------------------------------------------------------------------


class TestBulkButtons_ReportedCountsMatchTheBatch:
    def test_every_reported_count_is_the_batchs_own(self, admin_app, batch_id):
        ids = [
            _add(admin_app, batch_id),
            _add(admin_app, batch_id, "approved"),
            _add(admin_app, batch_id, "rejected"),
            _add(admin_app, batch_id),
        ]
        _book(admin_app, _add(admin_app, batch_id))
        elsewhere = _add(admin_app, str(uuid.uuid4()), "rejected")
        client = admin_app.test_client()

        for puzzle_id, action in zip(ids, ["reject", "reject", "approve", "approve"]):
            reported = client.post(
                f"/puzzle/{puzzle_id}/{action}?batch_id={batch_id}", headers=JSON
            ).get_json()["action_counts"]

            assert reported == admin_app.puzzle_review_service.batch_action_counts(
                batch_id
            )
            # …and the store's own answer is the rule, independently applied.
            assert reported == _counts_from_the_store(admin_app, ids)

        assert admin_app.puzzle_review_service.get_puzzle(elsewhere)["status"] == (
            "rejected"
        ), "another batch's puzzle was touched"

    def test_the_counts_are_the_batchs_not_the_rendered_rows(
        self, admin_app, batch_id
    ):
        """The page renders at most 100 rows; the batch is what counts.

        Counting cards in the DOM would have looked right on every batch this
        suite builds and wrong on the first one that overflows a page.
        """
        rendered_limit = 100
        ids = [_add(admin_app, batch_id, name=f"p{i}.png") for i in range(120)]
        assert len(ids) > rendered_limit

        body = _page(admin_app, batch_id)
        assert body.count('class="result-card"') == rendered_limit

        reported = (
            admin_app.test_client()
            .post(f"/puzzle/{ids[0]}/reject?batch_id={batch_id}", headers=JSON)
            .get_json()["action_counts"]
        )

        assert reported == {"approve": 120, "reject": 119, "delete_rejected": 1}


# --------------------------------------------------------------------------
# AC-4 — a refusal changes nothing
# --------------------------------------------------------------------------


class TestBulkButtons_RefusedActionDoesNotChangeCounts:
    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_a_puzzle_in_a_book_is_refused_and_reports_no_counts(
        self, admin_app, batch_id, action
    ):
        held = _add(admin_app, batch_id)
        _book(admin_app, held)
        _add(admin_app, batch_id)
        store = admin_app.puzzle_review_service
        before = store.batch_action_counts(batch_id)

        response = admin_app.test_client().post(
            f"/puzzle/{held}/{action}?batch_id={batch_id}", headers=JSON
        )

        assert response.status_code == 409
        body = response.get_json()
        assert body["ok"] is False
        assert body["message"] == f"Cannot {action} a puzzle that is in a book"
        # Nothing for the handler to apply, so the buttons stay as they were.
        assert "action_counts" not in body
        assert store.batch_action_counts(batch_id) == before
        assert store.get_puzzle(held)["status"] != action + "d"

    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_a_puzzle_that_is_not_there_reports_no_counts(
        self, admin_app, batch_id, action
    ):
        _add(admin_app, batch_id)
        store = admin_app.puzzle_review_service
        before = store.batch_action_counts(batch_id)

        response = admin_app.test_client().post(
            f"/puzzle/puzzle_999999/{action}?batch_id={batch_id}", headers=JSON
        )

        assert response.status_code == 404
        assert "action_counts" not in response.get_json()
        assert store.batch_action_counts(batch_id) == before

    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_the_browser_path_still_says_why_it_refused(
        self, admin_app, batch_id, action
    ):
        """CARD-100's message survives the JSON branch."""
        held = _add(admin_app, batch_id)
        _book(admin_app, held)

        body = admin_app.test_client().post(
            f"/puzzle/{held}/{action}?batch_id={batch_id}", follow_redirects=True
        ).get_data(as_text=True)

        assert f"Cannot {action} a puzzle that is in a book" in body
        assert "Puzzle not found" not in body
