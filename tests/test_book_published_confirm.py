"""CARD-131 — a published book confirms, and leaving draft is paid for again.

    AC-226  TestBookPublished_PuzzleChangeRequiresConfirmation      (INV-008)
    AC-227  TestBookPublished_ConfirmedPuzzleChangeApplied          (INV-008)
    AC-228  TestBookPlanChange_KeepsSelection                       (EC-026)
    AC-229  TestBookRemovePuzzle_KeepsRestOfArrangement             (EC-026)
    AC-277  TestBookMembership_AddOnNonDraftReturnsToDraft          (INV-012)
    AC-278  TestBookMembership_RemoveOnNonDraftReturnsToDraft       (INV-012)
    AC-279  TestBookPublished_ConfirmedChangeReturnsToDraft         (INV-012)
    AC-280  TestBookPublished_UnconfirmedChangeKeepsStatus          (INV-008)
    AC-281  TestBookAddPuzzlesByIds_NonDraftReturnsToDraft          (INV-012)
    AC-282  TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership (FR-037)

EC-026 and EC-033 — the two standing properties — are in
``tests/property/test_book_workflow.py``. The fourth membership route, the
arrangement step's Delete, has its three answers (removed · asked · found
nothing) in ``TestBookArrangeStep_DeleteReportsWhatTheStoreDid`` here.

Every store-level assertion runs in **both** storage modes: INV-008 and INV-012
are rules of the aggregate, not of a backend, and the two modes have twice
already disagreed about what a membership write does (CARD-100's list identity,
CARD-126's title pruning). The user-facing half is driven through the Flask
test client against the real routes, because this project has no browser
harness at any tier — which is also why the confirmation is a **server-rendered
page** and not a browser ``confirm()``: the page the route returns is re-posted
here field for field, exactly as a browser would, by
:func:`resubmit_confirmation`.

The books are built from the fixtures ``tests/test_book_ready_gate.py``
already owns (its ``Shelf`` writes puzzle records straight into the store, so a
120-puzzle book does not cost 120 uniqueness proofs). Nothing is imported from
the code under test to *derive* an expectation: the selections and the plans
below are literal matrices, and the counts the criteria name — 120, 121, 14
against 10 — are written out here.
"""

from __future__ import annotations

import html as html_module
import re

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import (
    AddOutcome,
    BookManager,
    BookStatus,
    DistributionPlan,
    RemoveOutcome,
    Split,
)
from nonogram.admin.book_plan import BUCKETS, TIERS
from tests.helpers.db import sqlite_session_scope
from tests.test_book_ready_gate import (
    AC_PLAN,
    AC_PLAN_CELLS,
    OFFENDING_CELL_TEXT,
    Shelf,
    _setup_print_form,
    cells_of,
)

B15, B20, B25, B30 = BUCKETS
E, M, H = TIERS

DRAFT = BookStatus.DRAFT.value
READY_FOR_PDF = BookStatus.READY_FOR_PDF.value
PDF_GENERATED = BookStatus.PDF_GENERATED.value
READY_FOR_KDP = BookStatus.READY_FOR_KDP.value
PUBLISHED = BookStatus.PUBLISHED.value

MODES = ("memory", "db")

#: The 120-puzzle book AC-226..AC-227 and AC-277..AC-281 are stated about, as a
#: 4 x 3 matrix in BUCKETS x TIERS order. Its column totals are 48 / 48 / 24 of
#: 120 — exactly 40 / 40 / 20 percent — so the plan below agrees with its split
#: and a selection matching it cell for cell is 0 points out of plan. That is
#: what lets these books really pass ADR-0035's gate on the way to published
#: rather than having a status written behind the gate's back.
BOOK_OF_120 = (
    (24, 12, 0),  # <=15
    (24, 24, 12),  # 16-20
    (0, 12, 12),  # 21-25
    (0, 0, 0),  # 26-30
)
PLAN_OF_120 = DistributionPlan(count=120, split=Split(40, 40, 20), cells=BOOK_OF_120)

#: AC-226/AC-227's number, written out rather than summed by the test helper.
HOLDS = 120
HOLDS_AFTER_ADD = 121
#: The selection step's normal use is a handful of ticks at once, not one: the
#: confirmation has to carry the whole submission, so one scenario below ticks
#: three puzzles and counts them off the book afterwards.
A_FEW = 3
HOLDS_AFTER_A_FEW = 123


def test_the_scenario_book_really_holds_a_hundred_and_twenty() -> None:
    """The criteria's 120 is the fixture's 120, checked against the matrix."""
    assert sum(sum(row) for row in BOOK_OF_120) == PLAN_OF_120.count == HOLDS
    assert HOLDS + 1 == HOLDS_AFTER_ADD
    assert HOLDS + A_FEW == HOLDS_AFTER_A_FEW
    assert not PLAN_OF_120.disagrees_with_split


# --------------------------------------------------------------------------
# The shelf, the panel, and the two things this card's tests always do
# --------------------------------------------------------------------------


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "published-confirm.db")


@pytest.fixture(params=MODES)
def shelf(request, scope) -> Shelf:
    return Shelf(request.param, None if request.param == "memory" else scope)


@pytest.fixture
def panel(monkeypatch):
    """The admin panel in memory mode, and a shelf over its own store and books."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))

    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    shelf = Shelf("memory", None, store=app.puzzle_review_service, books=app.book_manager)
    return app, shelf


def stocked(shelf, cells, plan, *, status=DRAFT, title="Winter"):
    """A book holding ``cells``, on ``plan``, brought to ``status`` through the gate.

    Returns ``(book_id, groups)`` where ``groups`` maps each ``(bucket, tier)``
    cell to the ids that fill it, so a test can name the four easy puzzles it
    means to remove instead of guessing at positions in the stored order.

    The status is reached by :meth:`BookManager.set_book_status`, never written
    behind it: a book these tests call "published" is one ADR-0035's gate let
    out, which is the only kind the product can produce.
    """
    book_id = shelf.books.create_book(title, "a book", "christmas", "adults")
    groups = {
        cell: shelf.puzzles({cell: count})
        for cell, count in cells_of(cells).items()
        if count
    }
    every_id = [puzzle_id for ids in groups.values() for puzzle_id in ids]
    if every_id:
        shelf.books.add_puzzles_to_book(book_id, every_id)
    shelf.books.save_plan(book_id, plan)
    for step in _path_to(status):
        assert shelf.books.set_book_status(book_id, step) is True, (
            f"the fixture could not reach {status}: {step} was refused"
        )
    assert shelf.books.get_book(book_id).status == status
    return book_id, groups


def _path_to(status):
    """The statuses walked to reach ``status`` from draft, in order."""
    ladder = [READY_FOR_PDF, PDF_GENERATED, READY_FOR_KDP, PUBLISHED]
    return [] if status == DRAFT else ladder[: ladder.index(status) + 1]


def one_more(shelf, cell=(B20, M)) -> str:
    """One further stored puzzle, in a cell of the plan, not in any book."""
    return shelf.puzzles({cell: 1})[0]


def below_the_floor(shelf) -> str:
    """One stored, approved puzzle whose printed cell misses the 4.8 mm floor.

    A 30x25 grid with 12-deep row clues — ``tests/test_book_floor.py``'s
    ``BELOW_FLOOR`` fixture, whose 4.61 mm is measured there rather than
    re-derived here. It is written through the store's own ``add_puzzle`` (not
    the shelf's stub records) because the floor reads the clues, and it is the
    puzzle INV-006 refuses unless the submission carries an override for it.
    """
    from tests.test_book_floor import BELOW_FLOOR, clues_of, dotted_grid

    width, height, row_gutter, column_gutter, _cell = BELOW_FLOOR
    grid = dotted_grid(width, height, row_gutter, column_gutter)
    rows, cols = clues_of(grid)
    puzzle_id = shelf.store.add_puzzle(
        grid=grid,
        clues_rows=rows,
        clues_cols=cols,
        width=width,
        height=height,
        theme="generic",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=None,
        source_image="below-floor.png",
    )
    shelf.store.approve_puzzle(puzzle_id)
    return puzzle_id


def ids_of(shelf, book_id):
    return list(shelf.books.get_book(book_id).puzzle_ids)


def status_of(shelf, book_id) -> str:
    return shelf.books.get_book(book_id).status


# --------------------------------------------------------------------------
# Reading the confirmation the route rendered, and posting it back
# --------------------------------------------------------------------------

_FORM = re.compile(r"(?s)<form\b[^>]*\baction=\"([^\"]*)\"[^>]*>(.*?)</form>")
_HIDDEN = re.compile(
    r"<input\b[^>]*\btype=\"hidden\"[^>]*\bname=\"([^\"]*)\"[^>]*\bvalue=\"([^\"]*)\"[^>]*>"
)


def text_of(html: str) -> str:
    """The rendered page as readable text: no tags, no entities, one space."""
    without_scripts = re.sub(r"(?s)<script.*?</script>", " ", html)
    return re.sub(
        r"\s+", " ", html_module.unescape(re.sub(r"<[^>]+>", " ", without_scripts))
    ).strip()


def confirmation_form(response):
    """``(action, [(name, value), ...])`` of the confirmation page's one form.

    The page is *asking*, so it has exactly one form on it — asserted here,
    because a second one would mean this helper is picking a form at random and
    every test that re-posts through it would be testing the wrong control.
    """
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    forms = _FORM.findall(body)
    assert len(forms) == 1, f"expected one form on the confirmation page, found {len(forms)}"
    action, inner = forms[0]
    fields = [
        (html_module.unescape(name), html_module.unescape(value))
        for name, value in _HIDDEN.findall(inner)
    ]
    return html_module.unescape(action), fields


def resubmit_confirmation(client, response):
    """Press "Confirm change" on the page the route rendered.

    The submission is the page's own hidden fields, re-posted to the page's own
    action — nothing this test reconstructed. A confirmation screen whose form
    carried the wrong fields, or posted to the wrong route, fails here rather
    than passing because the test knew what to send.
    """
    action, fields = confirmation_form(response)
    form = {}
    for name, value in fields:
        form.setdefault(name, []).append(value)
    return client.post(action, data=form, follow_redirects=True)


def asks_to_confirm(response, book, *, change_mentions=()) -> str:
    """Assert the response is the confirmation screen, and return its text."""
    raw = response.get_data(as_text=True)
    shown = text_of(raw)
    assert response.status_code == 200
    assert "Confirm change" in shown, f"no confirmation was offered: {shown}"
    assert book.metadata.title in shown, f"the confirmation does not name the book: {shown}"
    # The status, twice over: as a word the owner reads, and as the status
    # badge's own attribute. The first alone was satisfied by the template's
    # prose — a page that stopped reading the status off the book still said
    # "published", because the sentence around it did.
    assert book.status.replace("_", " ") in shown, (
        f"the confirmation does not name the book's status: {shown}"
    )
    assert f'data-status="{book.status}"' in raw, (
        "the confirmation does not carry the book's own status badge"
    )
    for fragment in change_mentions:
        assert fragment in shown, f"the confirmation does not name the change: {shown}"
    return shown


# --------------------------------------------------------------------------
# AC-226 (INV-008) — unconfirmed, the 120 stay 120 and the response asks
# --------------------------------------------------------------------------


class TestBookPublished_PuzzleChangeRequiresConfirmation:
    """A published book's membership does not move until the owner says so."""

    def test_the_store_changes_nothing_and_says_it_needs_confirmation(self, shelf) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = one_more(shelf)

        outcome = shelf.books.add_puzzles_reporting_refusals(book_id, [joining])

        assert isinstance(outcome, AddOutcome) and outcome.needs_confirmation
        assert (outcome.admitted, outcome.refusals) == ([], [])
        assert len(ids_of(shelf, book_id)) == HOLDS
        assert joining not in ids_of(shelf, book_id)

    def test_the_yes_no_door_answers_no_rather_than_pretending(self, shelf) -> None:
        """``add_puzzles_to_book`` must not read "asked" as "added"."""
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)

        assert shelf.books.add_puzzles_to_book(book_id, [one_more(shelf)]) is False
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_removing_asks_too(self, shelf) -> None:
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        leaving = groups[(B15, E)][0]

        outcome = shelf.books.remove_puzzle_reporting_confirmation(book_id, leaving)

        assert outcome == RemoveOutcome(False, needs_confirmation=True)
        assert leaving in ids_of(shelf, book_id)
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_a_removal_of_a_puzzle_the_book_never_held_is_not_a_question(
        self, shelf
    ) -> None:
        """Nothing would change, so there is nothing to confirm."""
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)

        outcome = shelf.books.remove_puzzle_reporting_confirmation(
            book_id, one_more(shelf)
        )

        assert outcome == RemoveOutcome(False)

    def test_the_paste_ids_route_renders_the_confirmation(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = one_more(shelf)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/add-puzzles", data={"puzzle_ids": joining}
        )

        asks_to_confirm(
            response, shelf.books.get_book(book_id), change_mentions=("Add 1 puzzle",)
        )
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_the_selection_step_renders_the_confirmation(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = one_more(shelf)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "16-20", "shown_ids": [joining], "puzzle_ids": [joining]},
        )

        asks_to_confirm(response, shelf.books.get_book(book_id))
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_the_question_carries_every_ticked_puzzle_not_just_the_first(
        self, panel
    ) -> None:
        """The step is asked about the whole submission it was given.

        A confirmation page that carried the first tick only would still read
        as a question and still apply *something* on confirm, so the count is
        pinned here on the page's own fields and in the plural wording the
        owner reads — the singular is the only shape the other tests take.
        """
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = [one_more(shelf) for _ in range(A_FEW)]
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "16-20", "shown_ids": joining, "puzzle_ids": joining},
        )

        asks_to_confirm(
            response,
            shelf.books.get_book(book_id),
            change_mentions=(f"Add {A_FEW} selected puzzles",),
        )
        _, fields = confirmation_form(response)
        assert [value for name, value in fields if name == "puzzle_ids"] == joining, (
            "the confirmation does not carry back the submission it was given"
        )
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_the_remove_route_renders_the_confirmation(self, panel) -> None:
        app, shelf = panel
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        leaving = groups[(B15, E)][0]
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/remove-puzzle", data={"puzzle_id": leaving}
        )

        asks_to_confirm(response, shelf.books.get_book(book_id), change_mentions=("Remove",))
        assert leaving in ids_of(shelf, book_id)

    def test_the_arrange_steps_delete_renders_the_confirmation(self, panel) -> None:
        """EC-033's "any route ending in the book store" — this one too."""
        app, shelf = panel
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        leaving = groups[(B15, E)][0]
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": "delete", "puzzle_id": leaving},
        )

        asks_to_confirm(response, shelf.books.get_book(book_id), change_mentions=("Remove",))
        assert leaving in ids_of(shelf, book_id)
        assert status_of(shelf, book_id) == PUBLISHED

    def test_pressing_confirm_on_the_arrange_step_removes_the_puzzle(self, panel) -> None:
        app, shelf = panel
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        leaving = groups[(B15, E)][0]
        client = app.test_client()

        asked = client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": "delete", "puzzle_id": leaving},
        )
        resubmit_confirmation(client, asked)

        assert leaving not in ids_of(shelf, book_id)
        assert status_of(shelf, book_id) == DRAFT

    def test_a_draft_book_is_never_asked(self, panel) -> None:
        """INV-008 is about published books only; nothing else grew a question."""
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/add-puzzles",
            data={"puzzle_ids": one_more(shelf)},
            follow_redirects=True,
        )

        assert "Confirm change" not in text_of(response.get_data(as_text=True))
        assert len(ids_of(shelf, book_id)) == HOLDS_AFTER_ADD


# --------------------------------------------------------------------------
# AC-227 (INV-008) — confirmed, the book holds 121
# --------------------------------------------------------------------------


class TestBookPublished_ConfirmedPuzzleChangeApplied:
    """With the confirmation the change lands — floor, level placement and all."""

    def test_the_store_applies_a_confirmed_add(self, shelf) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = one_more(shelf)

        outcome = shelf.books.add_puzzles_reporting_refusals(
            book_id, [joining], confirmed=True
        )

        assert outcome.needs_confirmation is False
        assert outcome.admitted == [joining]
        assert len(ids_of(shelf, book_id)) == HOLDS_AFTER_ADD
        assert joining in ids_of(shelf, book_id)

    def test_the_store_applies_a_confirmed_removal(self, shelf) -> None:
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        leaving = groups[(B15, E)][0]

        assert shelf.books.remove_puzzle_from_book(book_id, leaving, confirmed=True) is True

        assert leaving not in ids_of(shelf, book_id)
        assert len(ids_of(shelf, book_id)) == HOLDS - 1

    def test_pressing_the_rendered_confirm_button_adds_the_puzzle(self, panel) -> None:
        """The screen is driven, not imitated: its own form is posted back."""
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = one_more(shelf)
        client = app.test_client()

        asked = client.post(f"/book/{book_id}/add-puzzles", data={"puzzle_ids": joining})
        applied = resubmit_confirmation(client, asked)

        assert applied.status_code == 200
        assert len(ids_of(shelf, book_id)) == HOLDS_AFTER_ADD
        assert joining in ids_of(shelf, book_id)

    def test_pressing_confirm_on_the_selection_step_adds_the_puzzle(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = one_more(shelf)
        client = app.test_client()

        asked = client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "16-20", "shown_ids": [joining], "puzzle_ids": [joining]},
        )
        resubmit_confirmation(client, asked)

        assert len(ids_of(shelf, book_id)) == HOLDS_AFTER_ADD
        assert joining in ids_of(shelf, book_id)

    def test_pressing_confirm_adds_every_puzzle_the_question_named(self, panel) -> None:
        """All three join, and the owner is told about three.

        The card's own checkpoint is a published 120-puzzle book, where the
        selection step is used a tabful of ticks at a time. A confirmation that
        carried only part of the submission would add part of it and report
        that part as the whole, with the rest left in the kept selection where
        a floor refusal also leaves things — indistinguishable to the owner.
        """
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = [one_more(shelf) for _ in range(A_FEW)]
        client = app.test_client()

        asked = client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "16-20", "shown_ids": joining, "puzzle_ids": joining},
        )
        applied = resubmit_confirmation(client, asked)

        held = ids_of(shelf, book_id)
        assert [pid for pid in joining if pid in held] == joining, (
            f"the confirmation applied {[pid for pid in joining if pid in held]} "
            f"of the {A_FEW} puzzles it was given"
        )
        assert len(held) == HOLDS_AFTER_A_FEW
        assert f"Added {A_FEW} puzzle(s) to book" in text_of(
            applied.get_data(as_text=True)
        ), "the owner is told a number the book does not hold"

    def test_pressing_confirm_carries_the_floor_override_with_it(self, panel) -> None:
        """INV-006 x INV-008: the screen must not eat the owner's override.

        A below-floor tile is admitted only with an override on the submission
        being committed (``_submitted_overrides`` reads the *current* form), so
        the confirmation page is the only thing that can carry the owner's
        override across the question. If it did not, the store would refuse the
        puzzle by name and the owner would be told their explicitly overridden
        puzzle is below the floor, with nothing pointing at the screen that
        dropped the decision.
        """
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        tiny = below_the_floor(shelf)
        client = app.test_client()

        asked = client.post(
            f"/book/{book_id}/select-puzzles",
            data={
                "bucket": "26-30",
                "shown_ids": [tiny],
                "puzzle_ids": [tiny],
                f"override_{tiny}": "on",
            },
        )
        _, fields = confirmation_form(asked)
        assert (f"override_{tiny}", "on") in fields, (
            f"the confirmation page dropped the override for {tiny}: {fields}"
        )

        applied = resubmit_confirmation(client, asked)

        shown = text_of(applied.get_data(as_text=True))
        assert tiny in ids_of(shelf, book_id), (
            "the overridden puzzle did not join through the confirmation (INV-006 "
            f"was applied to a submission with no override): {shown}"
        )
        assert shelf.books.floor_overrides(book_id) == [tiny]
        assert "mm floor" not in shown, (
            f"the owner is told their overridden puzzle is below the floor: {shown}"
        )

    def test_the_store_carries_an_override_through_a_confirmed_add(self, shelf) -> None:
        """The store half of the same interaction, in both storage modes."""
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        tiny = below_the_floor(shelf)

        outcome = shelf.books.add_puzzles_reporting_refusals(
            book_id, [tiny], [tiny], confirmed=True
        )

        assert outcome.refusals == []
        assert tiny in ids_of(shelf, book_id)
        assert shelf.books.floor_overrides(book_id) == [tiny]

    def test_pressing_confirm_on_the_remove_route_removes_the_puzzle(self, panel) -> None:
        app, shelf = panel
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        leaving = groups[(B15, E)][0]
        client = app.test_client()

        asked = client.post(f"/book/{book_id}/remove-puzzle", data={"puzzle_id": leaving})
        resubmit_confirmation(client, asked)

        assert leaving not in ids_of(shelf, book_id)
        assert len(ids_of(shelf, book_id)) == HOLDS - 1

    def test_an_arbitrary_truthy_confirm_field_is_not_a_confirmation(self, panel) -> None:
        """Only the confirmation screen's own button confirms (INV-008)."""
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/add-puzzles",
            data={"puzzle_ids": one_more(shelf), "confirm": "maybe"},
        )

        asks_to_confirm(response, shelf.books.get_book(book_id))
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_the_confirmed_add_still_holds_the_floor_and_the_level_order(
        self, shelf
    ) -> None:
        """G-4: confirming waives INV-008, not INV-006 or INV-009."""
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        joining = one_more(shelf, cell=(B15, E))

        shelf.books.add_puzzles_to_book(book_id, [joining], confirmed=True)

        stored = ids_of(shelf, book_id)
        tiers = [shelf.store.get_puzzle(pid)["difficulty_tier"] for pid in stored]
        rank = {"easy": 0, "medium": 1, "hard": 2}
        assert [rank[t] for t in tiers] == sorted(rank[t] for t in tiers), (
            "a confirmed add broke INV-009's easy/medium/hard grouping"
        )
        assert stored.index(joining) == max(
            i for i, t in enumerate(tiers) if t == "easy"
        ), "a confirmed add did not join the end of its own level (INV-009)"


# --------------------------------------------------------------------------
# EC-033 — the arrange step reports the store's verdict, not its intention
# --------------------------------------------------------------------------


class TestBookArrangeStep_DeleteReportsWhatTheStoreDid:
    """The fourth route was brought into scope over exactly this flash.

    Before CARD-131 the step announced "Removed puzzle from book" whatever the
    store answered — including the published book's "not without a
    confirmation", which is the lie that argued the route into the card. The
    announcement now follows ``RemoveOutcome.removed``, and the not-found arm
    is worded like the sibling route ``POST /book/<id>/remove-puzzle``: the
    same delete, reached from two screens, answers the owner the same way.
    """

    def test_a_removal_the_store_made_is_announced(self, panel) -> None:
        app, shelf = panel
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120)
        leaving = groups[(B15, E)][0]
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": "delete", "puzzle_id": leaving},
        )

        assert "Removed puzzle from book" in text_of(response.get_data(as_text=True))
        assert leaving not in ids_of(shelf, book_id)
        assert len(ids_of(shelf, book_id)) == HOLDS - 1

    def test_a_delete_that_found_nothing_announces_no_removal(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120)
        stranger = one_more(shelf)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": "delete", "puzzle_id": stranger},
        )

        shown = text_of(response.get_data(as_text=True))
        assert "Removed puzzle from book" not in shown, (
            f"the step announced a removal the store did not make: {shown}"
        )
        assert "Book or puzzle not found" in shown, (
            f"the step said nothing at all about a delete that found nothing: {shown}"
        )
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_the_question_a_published_book_asks_is_not_an_announcement(
        self, panel
    ) -> None:
        """The scenario the flash lied about: asked, so nothing was removed."""
        app, shelf = panel
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        leaving = groups[(B15, E)][0]
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": "delete", "puzzle_id": leaving},
        )

        shown = text_of(response.get_data(as_text=True))
        assert "Removed puzzle from book" not in shown, (
            f"the step announced a removal it was only asking about: {shown}"
        )
        assert leaving in ids_of(shelf, book_id)


# --------------------------------------------------------------------------
# AC-228 (EC-026) — a plan edit keeps the selection
# --------------------------------------------------------------------------

#: AC-228's book: a plan of 150 and 40 puzzles selected against it. The cells
#: are deliberately nothing like the plan — the point is that the plan edit
#: leaves them alone, not that they match.
FORTY_SELECTED = (
    (10, 5, 0),
    (10, 5, 0),
    (5, 3, 2),
    (0, 0, 0),
)
PLAN_OF_150 = DistributionPlan(
    count=150,
    split=Split(40, 40, 20),
    cells=((20, 15, 0), (20, 25, 10), (15, 15, 10), (5, 5, 10)),
)


def test_ac228_fixture_is_forty_puzzles_against_a_plan_of_150() -> None:
    assert sum(sum(row) for row in FORTY_SELECTED) == 40
    assert PLAN_OF_150.count == 150


class TestBookPlanChange_KeepsSelection:
    """Changing the plan's count from 150 to 120 discards nothing (EC-026)."""

    def test_the_forty_selected_puzzles_are_still_selected(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, FORTY_SELECTED, PLAN_OF_150)
        before = ids_of(shelf, book_id)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_setup_print_form(PLAN_OF_150.cells, count=120),
        )

        assert response.status_code == 302
        assert shelf.books.get_plan(book_id).count == 120, "the plan edit did not land"
        assert ids_of(shelf, book_id) == before
        assert len(before) == 40

    def test_the_ticks_not_yet_added_survive_the_plan_edit(self, panel) -> None:
        """The other reading of "selected": the step's pending set (AC-211)."""
        app, shelf = panel
        book_id, _ = stocked(shelf, FORTY_SELECTED, PLAN_OF_150)
        ticked = [one_more(shelf) for _ in range(3)]
        client = app.test_client()
        # Tick three tiles and switch tabs: kept server-side, added to nothing.
        client.post(
            f"/book/{book_id}/select-puzzles",
            data={
                "bucket": "16-20",
                "shown_ids": ticked,
                "puzzle_ids": ticked,
                "go_bucket": "21-25",
            },
        )

        client.post(
            f"/book/{book_id}/setup-print",
            data=_setup_print_form(PLAN_OF_150.cells, count=120),
        )

        shown = client.get(f"/book/{book_id}/select-puzzles?bucket=16-20").get_data(
            as_text=True
        )
        for puzzle_id in ticked:
            assert puzzle_id in shown, "a plan edit dropped a tick the owner made"

    def test_the_plan_edit_writes_no_membership_at_all(self, panel) -> None:
        """Not even a reorder: the stored order is the same list, same order."""
        app, shelf = panel
        book_id, _ = stocked(shelf, FORTY_SELECTED, PLAN_OF_150)
        shelf.books.set_puzzle_title(book_id, ids_of(shelf, book_id)[0], "Snowy owl")
        before = ids_of(shelf, book_id)
        client = app.test_client()

        client.post(
            f"/book/{book_id}/setup-print",
            data=_setup_print_form(PLAN_OF_150.cells, count=120),
        )

        assert ids_of(shelf, book_id) == before
        assert shelf.books.get_puzzle_title(book_id, before[0]) == "Snowy owl"


# --------------------------------------------------------------------------
# AC-229 (EC-026) — removing B keeps A, C, D and their titles
# --------------------------------------------------------------------------


class TestBookRemovePuzzle_KeepsRestOfArrangement:
    """A, B, C, D each with a custom title; B leaves and takes only its own."""

    def _arranged(self, shelf):
        book_id, groups = stocked(shelf, ((4, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)), AC_PLAN)
        ordered = ids_of(shelf, book_id)
        assert len(ordered) == 4
        titles = dict(zip(ordered, ("Alpha", "Bravo", "Charlie", "Delta")))
        for puzzle_id, title in titles.items():
            shelf.books.set_puzzle_title(book_id, puzzle_id, title)
        return book_id, ordered, titles

    def test_the_arrangement_is_a_c_d_with_their_titles(self, shelf) -> None:
        book_id, (a, b, c, d), titles = self._arranged(shelf)

        assert shelf.books.remove_puzzle_from_book(book_id, b) is True

        assert ids_of(shelf, book_id) == [a, c, d]
        assert [shelf.books.get_puzzle_title(book_id, pid) for pid in (a, c, d)] == [
            titles[a],
            titles[c],
            titles[d],
        ]

    def test_the_removed_puzzles_own_title_entry_is_dropped(self, shelf) -> None:
        """Both storage modes: in memory it was kept, so a re-add wore it again."""
        book_id, (a, b, c, d), _ = self._arranged(shelf)

        shelf.books.remove_puzzle_from_book(book_id, b)

        assert shelf.books.get_puzzle_title(book_id, b) is None
        assert b not in (shelf.books.get_book(book_id).puzzle_titles or {})

    def test_a_re_added_puzzle_does_not_wear_its_old_title(self, shelf) -> None:
        book_id, (a, b, c, d), _ = self._arranged(shelf)

        shelf.books.remove_puzzle_from_book(book_id, b)
        shelf.books.add_puzzles_to_book(book_id, [b])

        assert shelf.books.get_puzzle_title(book_id, b) is None

    def test_the_arrange_step_removes_through_the_same_rule(self, panel) -> None:
        app, shelf = panel
        book_id, (a, b, c, d), titles = self._arranged(shelf)
        client = app.test_client()

        client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": "delete", "puzzle_id": b},
        )

        assert ids_of(shelf, book_id) == [a, c, d]
        assert shelf.books.get_puzzle_title(book_id, c) == titles[c]


# --------------------------------------------------------------------------
# AC-277..AC-281 (INV-012) — a membership change returns the book to draft
# --------------------------------------------------------------------------


class TestBookMembership_AddOnNonDraftReturnsToDraft:
    """AC-277 — pdf_generated, one puzzle added, and the book is draft again."""

    def test_adding_to_a_pdf_generated_book_returns_it_to_draft(self, shelf) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PDF_GENERATED)

        shelf.books.add_puzzles_to_book(book_id, [one_more(shelf)])

        assert status_of(shelf, book_id) == DRAFT
        assert len(ids_of(shelf, book_id)) == HOLDS_AFTER_ADD

    @pytest.mark.parametrize("status", [READY_FOR_PDF, PDF_GENERATED, READY_FOR_KDP])
    def test_every_status_outside_draft_goes_back(self, shelf, status) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=status)

        shelf.books.add_puzzles_to_book(book_id, [one_more(shelf)])

        assert status_of(shelf, book_id) == DRAFT

    def test_the_selection_step_returns_it_to_draft_too(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PDF_GENERATED)
        joining = one_more(shelf)
        client = app.test_client()

        client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "16-20", "shown_ids": [joining], "puzzle_ids": [joining]},
        )

        assert status_of(shelf, book_id) == DRAFT
        assert joining in ids_of(shelf, book_id)

    def test_a_draft_book_stays_in_draft(self, shelf) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120)

        shelf.books.add_puzzles_to_book(book_id, [one_more(shelf)])

        assert status_of(shelf, book_id) == DRAFT

    def test_an_add_that_changes_no_membership_demotes_nothing(self, shelf) -> None:
        """Re-adding a member is not a membership change (INV-012)."""
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PDF_GENERATED)
        already_in = groups[(B15, E)][0]

        shelf.books.add_puzzles_to_book(book_id, [already_in])

        assert status_of(shelf, book_id) == PDF_GENERATED
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_a_submission_the_floor_refused_entirely_demotes_nothing(self, panel) -> None:
        """Handover from CARD-121: the return-to-draft write is *after* the filter."""
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PDF_GENERATED)
        tiny = below_the_floor(shelf)

        outcome = shelf.books.add_puzzles_reporting_refusals(book_id, [tiny])

        assert [r.puzzle_id for r in outcome.refusals] == [tiny]
        assert status_of(shelf, book_id) == PDF_GENERATED, (
            "a submission that changed no membership demoted the book"
        )

    @pytest.mark.parametrize("action", ["reorder", "retitle"])
    def test_reorder_and_retitle_keep_the_status(self, shelf, action) -> None:
        """The owner named add and remove only (decision 2026-09-22 (c))."""
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PDF_GENERATED)
        member = groups[(B15, E)][1]

        if action == "reorder":
            assert shelf.books.move_puzzle_up(book_id, member) is True
        else:
            assert shelf.books.set_puzzle_title(book_id, member, "Snowy owl") is True

        assert status_of(shelf, book_id) == PDF_GENERATED


class TestBookMembership_RemoveOnNonDraftReturnsToDraft:
    """AC-278 — ready_for_pdf, one puzzle removed, and the book is draft again."""

    def test_removing_from_a_ready_for_pdf_book_returns_it_to_draft(self, shelf) -> None:
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=READY_FOR_PDF)

        assert shelf.books.remove_puzzle_from_book(book_id, groups[(B15, E)][0]) is True

        assert status_of(shelf, book_id) == DRAFT
        assert len(ids_of(shelf, book_id)) == HOLDS - 1

    def test_the_remove_route_returns_it_to_draft(self, panel) -> None:
        app, shelf = panel
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=READY_FOR_PDF)
        client = app.test_client()

        client.post(
            f"/book/{book_id}/remove-puzzle", data={"puzzle_id": groups[(B15, E)][0]}
        )

        assert status_of(shelf, book_id) == DRAFT

    def test_a_removal_that_found_nothing_demotes_nothing(self, shelf) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=READY_FOR_PDF)

        assert shelf.books.remove_puzzle_from_book(book_id, one_more(shelf)) is False

        assert status_of(shelf, book_id) == READY_FOR_PDF


class TestBookPublished_ConfirmedChangeReturnsToDraft:
    """AC-279 — the confirmed change to a published book lands it in draft."""

    def test_the_store_confirmed_add_returns_it_to_draft(self, shelf) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)

        shelf.books.add_puzzles_to_book(book_id, [one_more(shelf)], confirmed=True)

        assert status_of(shelf, book_id) == DRAFT
        assert len(ids_of(shelf, book_id)) == HOLDS_AFTER_ADD

    def test_pressing_confirm_returns_it_to_draft(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        client = app.test_client()

        asked = client.post(
            f"/book/{book_id}/add-puzzles", data={"puzzle_ids": one_more(shelf)}
        )
        resubmit_confirmation(client, asked)

        assert status_of(shelf, book_id) == DRAFT

    def test_a_confirmed_removal_returns_it_to_draft(self, shelf) -> None:
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)

        shelf.books.remove_puzzle_from_book(
            book_id, groups[(B15, E)][0], confirmed=True
        )

        assert status_of(shelf, book_id) == DRAFT


class TestBookPublished_UnconfirmedChangeKeepsStatus:
    """AC-280 — the unconfirmed change moves nothing, the status included."""

    def test_the_book_is_still_published(self, shelf) -> None:
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)

        shelf.books.add_puzzles_to_book(book_id, [one_more(shelf)])

        assert status_of(shelf, book_id) == PUBLISHED
        assert len(ids_of(shelf, book_id)) == HOLDS

    def test_an_unconfirmed_removal_keeps_the_status_too(self, shelf) -> None:
        book_id, groups = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)

        shelf.books.remove_puzzle_from_book(book_id, groups[(B15, E)][0])

        assert status_of(shelf, book_id) == PUBLISHED

    def test_the_route_that_asked_changed_no_status(self, panel) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=PUBLISHED)
        client = app.test_client()

        client.post(f"/book/{book_id}/add-puzzles", data={"puzzle_ids": one_more(shelf)})

        assert status_of(shelf, book_id) == PUBLISHED


class TestBookAddPuzzlesByIds_NonDraftReturnsToDraft:
    """AC-281 — the paste-IDs route returns a ready_for_kdp book to draft too."""

    def test_pasting_an_id_into_the_detail_form_returns_the_book_to_draft(
        self, panel
    ) -> None:
        app, shelf = panel
        book_id, _ = stocked(shelf, BOOK_OF_120, PLAN_OF_120, status=READY_FOR_KDP)
        joining = one_more(shelf)
        client = app.test_client()

        client.post(
            f"/book/{book_id}/add-puzzles",
            data={"puzzle_ids": joining},
            follow_redirects=True,
        )

        assert status_of(shelf, book_id) == DRAFT
        assert joining in ids_of(shelf, book_id)
        assert len(ids_of(shelf, book_id)) == HOLDS_AFTER_ADD


# --------------------------------------------------------------------------
# AC-282 (FR-037, INV-012) — the returned book is checked against the plan again
# --------------------------------------------------------------------------


class TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership:
    """A book that passed the check once does not keep the pass over new puzzles."""

    def _returned_to_draft(self, shelf):
        """AC-282's book: 100 on plan, pdf_generated, then +4 medium / -4 easy."""
        book_id, groups = stocked(shelf, AC_PLAN_CELLS, AC_PLAN, status=PDF_GENERATED)
        joining = shelf.puzzles({(B20, M): 4})
        shelf.books.add_puzzles_to_book(book_id, joining)
        for leaving in groups[(B15, E)][:4]:
            shelf.books.remove_puzzle_from_book(book_id, leaving)
        return book_id

    def test_marking_it_ready_is_rejected_and_it_stays_draft(self, shelf) -> None:
        book_id = self._returned_to_draft(shelf)
        assert status_of(shelf, book_id) == DRAFT

        with pytest.raises(ValueError) as refused:
            shelf.books.set_book_status(book_id, READY_FOR_PDF)

        assert OFFENDING_CELL_TEXT in str(refused.value)
        assert status_of(shelf, book_id) == DRAFT

    def test_the_book_really_is_a_hundred_puzzles_with_fourteen_in_that_cell(
        self, shelf
    ) -> None:
        """The scenario's arithmetic, counted off the store rather than assumed."""
        book_id = self._returned_to_draft(shelf)

        held = [shelf.store.get_puzzle(pid) for pid in ids_of(shelf, book_id)]
        in_the_cell = [
            record
            for record in held
            if record["difficulty_tier"] == "medium"
            and B20.low <= max(record["width"], record["height"]) <= B20.high
        ]

        assert len(held) == 100
        assert len(in_the_cell) == 14
        assert cells_of(AC_PLAN_CELLS)[(B20, M)] == 10

    def test_the_changed_membership_cannot_ship_behind_the_pass_it_no_longer_has(
        self, shelf
    ) -> None:
        """What AC-282 is worth, stated as the shipping step rather than the next rung.

        The selection that bought the pdf_generated pass is not the selection
        the book now holds, and the gate runs at the **exit from draft only**
        (``_refuse_unless_the_planned_book``) — so a changed membership left at
        pdf_generated would never be measured again on its way to KDP. What
        INV-012 buys is that the road back out of draft is the gate, and the
        gate refuses this membership for every target, the ship-ward jump
        straight to published included (ADR-0035 (a)'s status-jump bypass).
        """
        book_id, groups = stocked(shelf, AC_PLAN_CELLS, AC_PLAN, status=PDF_GENERATED)
        passed_the_gate_with = ids_of(shelf, book_id)
        joining = shelf.puzzles({(B20, M): 4})
        shelf.books.add_puzzles_to_book(book_id, joining)
        for leaving in groups[(B15, E)][:4]:
            shelf.books.remove_puzzle_from_book(book_id, leaving)

        held = ids_of(shelf, book_id)
        assert sorted(set(held) - set(passed_the_gate_with)) == sorted(joining), (
            "the book still holds the selection its pdf_generated pass was for"
        )

        with pytest.raises(ValueError) as refused:
            shelf.books.set_book_status(book_id, PUBLISHED)

        assert OFFENDING_CELL_TEXT in str(refused.value)
        assert status_of(shelf, book_id) == DRAFT, (
            "the membership changed under a non-draft status: INV-012 (EC-033)"
        )
