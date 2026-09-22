"""CARD-124 — the readiness gate: a book leaves draft only as the planned book.

    AC-218  TestBookReady_AcceptsWhenEveryCellWithinTolerance      (INV-007)
    AC-219  TestBookReady_ExactlyThreePointsAccepted               (INV-007)
    AC-220  TestBookReady_RefusedBeyondThreePoints                 (INV-007)
    AC-221  TestBookReady_RefusalNamesOffendingCell
    CK-1    TestBookReady_UnderFilledBookRefusedAgainstPlannedTotal
    CK-2    TestBookReady_PlanlessBookRefusedWithRemedy
    R1      TestBookStatus_EveryExitFromDraftIsGatedOnThePlan      (ADR-0035/R1)
    owner   TestBookPlanEdit_OnANonDraftBookReturnsItToDraft

EC-025's iff — the gate accepts a selection *exactly* when every cell is within
the tolerance, over a seeded corpus — is in tests/property/test_book_ready_gate.py.

Every storage-level test runs in **both** storage modes: in memory, and DB mode
against a real SQLite file. The user-facing half (the status route refusing and
flashing what the domain refused, and a plan edit returning a book to draft) is
driven through the Flask test client against the real routes, because this
project has no browser harness.

The scenarios are stated as literal matrices (``AC_PLAN_CELLS`` and the
selections below), not re-derived through ``prefill``, so the numbers the
criteria name — 13 against 10, 14 against 10 — are in the test rather than in
the code under test.
"""

from __future__ import annotations

import uuid

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import (
    READY_TOLERANCE_POINTS,
    BookManager,
    BookStatus,
    DistributionPlan,
    Split,
)
from nonogram.admin.book_plan import BUCKETS, TIERS
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import make_batch, sqlite_session_scope

MODES = ("memory", "db")

B15, B20, B25, B30 = BUCKETS
E, M, H = TIERS

DRAFT = BookStatus.DRAFT.value
READY_FOR_PDF = BookStatus.READY_FOR_PDF.value

#: Every status that is not draft — every way out of draft ADR-0035 (a) gates.
OUT_OF_DRAFT = tuple(s.value for s in BookStatus if s is not BookStatus.DRAFT)

#: The plan the acceptance criteria are stated against: 100 puzzles, with 10 of
#: them in the 16-20 x medium cell AC-219 to AC-221 name. Rows in BUCKETS order,
#: columns in TIERS order. Its column totals are 45 / 40 / 15, which is its
#: split, so the matrix agrees with the general plan.
AC_PLAN_CELLS = (
    (15, 10, 0),  # <=15
    (20, 10, 5),  # 16-20
    (10, 15, 5),  # 21-25
    (0, 5, 5),  # 26-30
)
AC_PLAN = DistributionPlan(count=100, split=Split(45, 40, 15), cells=AC_PLAN_CELLS)

#: AC-218: 100 selected, three moved from <=15 x easy to 21-25 x easy. Every
#: cell is within 3 points of its plan and none of them is exactly on it.
AC218_SELECTION = (
    (12, 10, 0),
    (20, 10, 5),
    (13, 15, 5),
    (0, 5, 5),
)

#: AC-219: the 16-20 x medium cell holds 13 against a plan of 10 — 13% against
#: 10% of the planned 100, exactly 3.0 points out, which is inside.
AC219_SELECTION = (
    (15, 10, 0),
    (20, 13, 5),
    (10, 15, 5),
    (0, 5, 5),
)

#: AC-220 / AC-221: the same cell holds 14 — 14% against 10%, 4 points out.
AC220_SELECTION = (
    (15, 10, 0),
    (20, 14, 5),
    (10, 15, 5),
    (0, 5, 5),
)

#: CK-1: the right mix at half the size — 50 selected against a plan of 100.
HALF_SELECTION = (
    (8, 5, 0),
    (10, 5, 2),
    (5, 8, 2),
    (0, 3, 2),
)

#: The refusal AC-221 asks to see, spelled out rather than built from the code.
OFFENDING_CELL_TEXT = "16-20 x medium: 14% against 10%"


def cells_of(matrix) -> dict:
    """A ``{(bucket, tier): count}`` map from a 4 x 3 matrix in BUCKETS order."""
    return {
        (bucket, tier): matrix[b][t]
        for b, bucket in enumerate(BUCKETS)
        for t, tier in enumerate(TIERS)
    }


# --------------------------------------------------------------------------
# The shelf: a book manager, the store that holds its puzzles, and one mode
# --------------------------------------------------------------------------


class Shelf:
    """A book manager in one storage mode, with the store behind it.

    Puzzle records are written straight into the store rather than through
    ``add_puzzle``: the gate reads a record's width, height and difficulty
    tier and nothing else, and a hundred-puzzle book would otherwise cost a
    hundred uniqueness proofs. In DB mode they are real ``puzzles`` rows, read
    back through the store's own query.
    """

    def __init__(self, mode, factory, *, store=None, books=None):
        self.mode = mode
        self.factory = factory
        self.store = store if store is not None else PuzzleReviewService(session_factory=factory)
        self.books = (
            books
            if books is not None
            else BookManager(session_factory=factory, puzzle_store=self.store)
        )
        self.batch = make_batch(factory, source="random") if factory is not None else None

    def puzzles(self, cells) -> list:
        """One puzzle per puzzle the ``{(bucket, tier): count}`` map asks for.

        A cell's puzzles are square at the top of their bucket's own range, so
        the bucket each one lands in comes from ``book_plan``'s bounds rather
        than from a size this test picked.
        """
        wanted = [
            (bucket, tier)
            for (bucket, tier), count in cells.items()
            for _ in range(count)
        ]
        ids = [str(uuid.uuid4()) for _ in wanted]

        if self.factory is None:
            for puzzle_id, (bucket, tier) in zip(ids, wanted):
                self.store.puzzles[puzzle_id] = {
                    "id": puzzle_id,
                    "width": bucket.high,
                    "height": bucket.high,
                    "difficulty_tier": tier.value,
                    "status": "approved",
                    "book_id": None,
                }
            return ids

        from nonogram.db.models import Puzzle

        with self.factory() as db:
            db.add_all(
                Puzzle(
                    id=uuid.UUID(puzzle_id),
                    batch_id=uuid.UUID(self.batch),
                    grid=[[True]],
                    clues_rows=[[1]],
                    clues_cols=[[1]],
                    width=bucket.high,
                    height=bucket.high,
                    difficulty_tier=tier.value,
                    status="approved",
                )
                for puzzle_id, (bucket, tier) in zip(ids, wanted)
            )
        return ids

    def book(self, cells, *, plan=AC_PLAN, title="Winter") -> str:
        """A draft book holding the selection ``cells`` describes."""
        book_id = self.books.create_book(title, "a book", "christmas", "adults")
        ids = self.puzzles(cells)
        if ids:
            self.books.add_puzzles_to_book(book_id, ids)
        if plan is not None:
            self.books.save_plan(book_id, plan)
        return book_id

    def drop_plan(self, book_id) -> None:
        """Storage as a row from before migration 010 has it: no plan at all."""
        if self.factory is None:
            self.books._plans.pop(book_id, None)
        else:
            from nonogram.db.models import Book as DBBook

            with self.factory() as db:
                db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).first(
                ).distribution_plan = None
        assert self.books.get_plan(book_id) is None

    def status(self, book_id) -> str:
        return self.books.get_book(book_id).status

    def refusal(self, book_id, status=READY_FOR_PDF) -> str:
        """The refusal the gate raises for that transition (it must raise one)."""
        with pytest.raises(ValueError) as refused:
            self.books.set_book_status(book_id, status)
        return str(refused.value)


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "ready-gate.db")


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
    shelf = Shelf(
        "memory", None, store=app.puzzle_review_service, books=app.book_manager
    )
    return app, shelf


def flashes(client):
    """Every message flashed into this client's session, newest last."""
    with client.session_transaction() as session:
        return [message for _, message in session.get("_flashes", [])]


# --------------------------------------------------------------------------
# AC-218 — a selection within the tolerance leaves draft
# --------------------------------------------------------------------------


class TestBookReady_AcceptsWhenEveryCellWithinTolerance:
    """AC-218 (INV-007) — 100 planned, 100 selected, every cell within 3 points."""

    def test_the_book_reaches_the_ready_status(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC218_SELECTION))

        assert shelf.books.set_book_status(book_id, READY_FOR_PDF) is True
        assert shelf.status(book_id) == READY_FOR_PDF

    def test_the_scenario_really_is_inside_the_tolerance(self) -> None:
        """The data, checked against the criterion rather than against the gate."""
        planned, selected = cells_of(AC_PLAN_CELLS), cells_of(AC218_SELECTION)

        assert sum(selected.values()) == sum(planned.values()) == AC_PLAN.count == 100
        assert max(abs(selected[c] - planned[c]) for c in planned) == 3


# --------------------------------------------------------------------------
# AC-219 — exactly 3.0 points is inside
# --------------------------------------------------------------------------


class TestBookReady_ExactlyThreePointsAccepted:
    """AC-219 (INV-007) — 13 against a plan of 10 in a book of 100 passes."""

    def test_thirteen_against_ten_of_a_hundred_passes(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC219_SELECTION))

        assert shelf.books.set_book_status(book_id, READY_FOR_PDF) is True
        assert shelf.status(book_id) == READY_FOR_PDF

    def test_that_cell_is_exactly_the_tolerance_out(self) -> None:
        planned, selected = cells_of(AC_PLAN_CELLS), cells_of(AC219_SELECTION)

        assert (selected[(B20, M)], planned[(B20, M)]) == (13, 10)
        assert (selected[(B20, M)] - planned[(B20, M)]) * 100 == (
            READY_TOLERANCE_POINTS * AC_PLAN.count
        ), "the criterion's cell is not on the boundary any more"
        assert all(abs(selected[c] - planned[c]) <= 3 for c in planned)


# --------------------------------------------------------------------------
# AC-220 — one point further is refused
# --------------------------------------------------------------------------


class TestBookReady_RefusedBeyondThreePoints:
    """AC-220 (INV-007) — 14 against a plan of 10 is refused, status unchanged."""

    def test_the_transition_is_rejected_and_the_book_stays_draft(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC220_SELECTION))

        shelf.refusal(book_id)

        assert shelf.status(book_id) == DRAFT

    def test_only_that_cell_is_out(self) -> None:
        planned, selected = cells_of(AC_PLAN_CELLS), cells_of(AC220_SELECTION)

        assert (selected[(B20, M)], planned[(B20, M)]) == (14, 10)
        assert [c for c in planned if abs(selected[c] - planned[c]) > 3] == [(B20, M)]


# --------------------------------------------------------------------------
# AC-221 — the refusal names the offending cell
# --------------------------------------------------------------------------


class TestBookReady_RefusalNamesOffendingCell:
    """AC-221 — "16-20 x medium: 14% against 10%", and the owner sees it."""

    def test_the_refusal_names_the_cell_with_both_shares(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC220_SELECTION))

        refusal = shelf.refusal(book_id)

        assert OFFENDING_CELL_TEXT in refusal
        assert refusal.count(" against ") == 1, f"named a cell that is within: {refusal}"

    def test_every_offending_cell_is_named_not_only_the_first(self, shelf) -> None:
        """A refusal is the whole to-do list, not the first thing that is wrong."""
        selection = ((15, 10, 0), (20, 14, 5), (10, 15, 0), (0, 5, 5))
        book_id = shelf.book(cells_of(selection))

        refusal = shelf.refusal(book_id)

        assert OFFENDING_CELL_TEXT in refusal
        assert "21-25 x hard: 0% against 5%" in refusal
        assert refusal.count(" against ") == 2

    def test_the_status_route_flashes_it(self, panel) -> None:
        """The user-facing half: the route flashes what the domain refused."""
        app, shelf = panel
        book_id = shelf.book(cells_of(AC220_SELECTION))
        client = app.test_client()

        response = client.post(f"/book/{book_id}/status", data={"status": READY_FOR_PDF})

        assert response.status_code == 302
        assert any(OFFENDING_CELL_TEXT in message for message in flashes(client)), flashes(
            client
        )
        assert shelf.status(book_id) == DRAFT


# --------------------------------------------------------------------------
# CK-1 — the denominator is the planned total, so an under-filled book fails
# --------------------------------------------------------------------------


class TestBookReady_UnderFilledBookRefusedAgainstPlannedTotal:
    """CK-1 (ADR-0035 (b)) — the right mix at half the planned size is refused."""

    def test_half_a_book_is_refused(self, shelf) -> None:
        book_id = shelf.book(cells_of(HALF_SELECTION))

        refusal = shelf.refusal(book_id)

        assert shelf.status(book_id) == DRAFT
        # The biggest cells are the ones that are short: 20 planned, 10 held.
        assert "16-20 x easy: 10% against 20%" in refusal

    def test_the_selection_really_is_about_half_at_the_planned_mix(self) -> None:
        planned, selected = cells_of(AC_PLAN_CELLS), cells_of(HALF_SELECTION)

        assert sum(selected.values()) == 50 == sum(planned.values()) // 2
        assert all(abs(selected[c] - planned[c] / 2) <= 0.5 for c in planned)


# --------------------------------------------------------------------------
# CK-2 — a plan-less book is refused with its remedy
# --------------------------------------------------------------------------


class TestBookReady_PlanlessBookRefusedWithRemedy:
    """CK-2 (ADR-0035 (c)) — no stored plan, so no exit from draft."""

    def test_refused_and_pointed_at_print_setup(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.drop_plan(book_id)

        refusal = shelf.refusal(book_id)

        assert "no stored plan" in refusal
        assert "Print setup" in refusal
        assert shelf.status(book_id) == DRAFT

    def test_storing_a_plan_is_the_whole_remedy(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.drop_plan(book_id)
        shelf.refusal(book_id)

        assert shelf.books.save_plan(book_id, AC_PLAN) is True

        assert shelf.books.set_book_status(book_id, READY_FOR_PDF) is True


# --------------------------------------------------------------------------
# ADR-0035/R1 — every exit from draft is gated, and only the exit
# --------------------------------------------------------------------------


class TestBookStatus_EveryExitFromDraftIsGatedOnThePlan:
    """ADR-0035/R1 — including a direct draft -> ready_for_kdp or -> published."""

    @pytest.mark.parametrize("target", OUT_OF_DRAFT)
    def test_no_target_status_lets_an_off_plan_book_out(self, shelf, target) -> None:
        book_id = shelf.book(cells_of(AC220_SELECTION))

        refusal = shelf.refusal(book_id, target)

        assert OFFENDING_CELL_TEXT in refusal
        assert shelf.status(book_id) == DRAFT

    @pytest.mark.parametrize("target", OUT_OF_DRAFT)
    def test_no_target_status_lets_a_plan_less_book_out(self, shelf, target) -> None:
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.drop_plan(book_id)

        assert "no stored plan" in shelf.refusal(book_id, target)
        assert shelf.status(book_id) == DRAFT

    @pytest.mark.parametrize("target", OUT_OF_DRAFT)
    def test_a_matching_book_reaches_every_target_directly(self, shelf, target) -> None:
        """G-1: no status order is added — draft goes straight to any status."""
        book_id = shelf.book(cells_of(AC218_SELECTION), title=f"To {target}")

        assert shelf.books.set_book_status(book_id, target) is True
        assert shelf.status(book_id) == target

    def test_draft_to_draft_is_not_an_exit_and_is_not_gated(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC220_SELECTION))
        shelf.drop_plan(book_id)

        assert shelf.books.set_book_status(book_id, DRAFT) is True
        assert shelf.status(book_id) == DRAFT

    def test_the_gate_runs_at_the_exit_only(self, shelf) -> None:
        """A book past the gate moves on without being judged again.

        Stated with the strongest off-plan condition there is — no plan at
        all — so it cannot pass by accident. This is the half INV-012 covers
        instead: a membership or plan change on a non-draft book returns it to
        draft (CARD-131 for membership), and it is judged again on the way out.
        """
        book_id = shelf.book(cells_of(AC218_SELECTION))
        assert shelf.books.set_book_status(book_id, READY_FOR_PDF) is True
        shelf.drop_plan(book_id)

        assert shelf.books.set_book_status(book_id, BookStatus.PDF_GENERATED.value) is True
        assert shelf.status(book_id) == BookStatus.PDF_GENERATED.value

    def test_the_rules_the_gate_joins_still_hold(self, shelf) -> None:
        """The empty-book and published-book rules are not replaced by it."""
        empty = shelf.books.create_book("Empty", "a book", "christmas", "adults")
        with pytest.raises(ValueError, match="Must have puzzles"):
            shelf.books.set_book_status(empty, READY_FOR_PDF)

        book_id = shelf.book(cells_of(AC218_SELECTION), title="Out")
        shelf.books.set_book_status(book_id, BookStatus.PUBLISHED.value)
        with pytest.raises(ValueError, match="published book"):
            shelf.books.set_book_status(book_id, DRAFT)


# --------------------------------------------------------------------------
# The owner's decision: a plan edit on a non-draft book returns it to draft
# --------------------------------------------------------------------------


class TestBookPlanEdit_OnANonDraftBookReturnsItToDraft:
    """CARD-124 owner decision (ADR-0035 "Membership change after draft").

    The plan is what the gate measures the selection against, so editing it
    unmakes the verdict that let the book out. The book goes back to draft and
    through the same gate, rather than the edit being refused.
    """

    def test_save_plan_returns_the_book_to_draft(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.books.set_book_status(book_id, BookStatus.READY_FOR_KDP.value)

        assert shelf.books.save_plan(book_id, AC_PLAN) is True

        assert shelf.status(book_id) == DRAFT

    def test_a_draft_book_is_left_where_it_is(self, shelf) -> None:
        book_id = shelf.book(cells_of(AC218_SELECTION))

        shelf.books.save_plan(book_id, AC_PLAN)

        assert shelf.status(book_id) == DRAFT

    def test_the_book_must_pass_the_gate_again(self, shelf) -> None:
        """No bypass: a book back in draft leaves it only through the gate."""
        book_id = shelf.book(cells_of(AC219_SELECTION))
        shelf.books.set_book_status(book_id, READY_FOR_PDF)

        # A plan that the same selection no longer matches: one puzzle planned
        # where it holds thirteen.
        tightened = DistributionPlan(
            count=100,
            split=Split(45, 40, 15),
            cells=((15, 10, 0), (20, 1, 5), (10, 15, 5), (0, 5, 5)),
        )
        shelf.books.save_plan(book_id, tightened)

        assert "16-20 x medium: 13% against 1%" in shelf.refusal(book_id)
        assert shelf.status(book_id) == DRAFT

    def test_print_setup_returns_the_book_to_draft_and_says_so(self, panel) -> None:
        """The user-facing half, through the route that edits the plan."""
        app, shelf = panel
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.books.set_book_status(book_id, READY_FOR_PDF)
        client = app.test_client()

        form = {"unit": "cm", "width": "21.59", "height": "27.94", "plan_count": "100"}
        for tier, share in zip(TIERS, (45, 40, 15)):
            form[f"split_{tier.value}"] = str(share)
        for b, row in enumerate(AC_PLAN_CELLS):
            for tier, value in zip(TIERS, row):
                form[f"cell_{b}_{tier.value}"] = str(value)
        response = client.post(f"/book/{book_id}/setup-print", data=form)

        assert response.status_code == 302
        assert shelf.status(book_id) == DRAFT
        assert any("back in draft" in message for message in flashes(client)), flashes(client)
