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
from nonogram.admin.book_plan import BUCKETS, TIERS, InvalidPlan
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

#: AC_PLAN with one easy puzzle moved from <=15 to 21-25: a real plan *edit*,
#: and still agreeing with its split (the column totals are untouched), so the
#: edit is the only thing the route reacts to.
EDITED_PLAN_CELLS = (
    (14, 10, 0),
    (20, 10, 5),
    (11, 15, 5),
    (0, 5, 5),
)
EDITED_PLAN = DistributionPlan(count=100, split=Split(45, 40, 15), cells=EDITED_PLAN_CELLS)

#: Every cell of the 4 x 3 matrix.
EVERY_CELL = frozenset((bucket, tier) for bucket in BUCKETS for tier in TIERS)

#: AC_PLAN and EDITED_PLAN as Print setup would have stored them: the same
#: numbers, all 12 cells marked hand-edited. That mark is what makes them
#: **fixed points of the form** — ``revise_plan`` keeps an edited cell's value
#: and re-derives every other one from count and split — so the submission the
#: plan-edit test makes lands exactly as written, and the *only* difference
#: between the two is the edit the test performs. (The no-op re-save test used
#: to start from AC_PLAN_AS_STORED too; cycle 2's F-002 pointed out that an
#: all-edited plan does not discriminate the edit-mark round trip, so it now
#: settles the route's own fixed point instead — see ``_settle_print_setup``.)
AC_PLAN_AS_STORED = DistributionPlan(
    count=100, split=Split(45, 40, 15), cells=AC_PLAN_CELLS, edited=EVERY_CELL
)
EDITED_PLAN_AS_STORED = DistributionPlan(
    count=100, split=Split(45, 40, 15), cells=EDITED_PLAN_CELLS, edited=EVERY_CELL
)

#: The degenerate plan an *empty* selection satisfies: one puzzle planned, no
#: cell claiming it, so every cell is within the tolerance of zero. F-004's own
#: configuration — the one a gate that mistook "unread" for "empty" approves.
NOTHING_PLANNED = DistributionPlan(
    count=1, split=Split(100, 0, 0), cells=((0, 0, 0),) * 4
)


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

    def damage_plan(self, book_id) -> None:
        """Storage holding a plan document the aggregate refuses to decode.

        DB mode only, and that is the point: the in-memory branch holds
        ``DistributionPlan`` objects, which ``__post_init__`` has already
        accepted, so it cannot reach this state at all. ``count: 0`` is the
        smallest damage INV-005 rejects, so the document is otherwise the real
        one the book stored.
        """
        assert self.factory is not None, "only DB mode can hold a damaged document"
        from nonogram.db.models import Book as DBBook

        with self.factory() as db:
            row = db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).first()
            document = dict(row.distribution_plan)
            document["count"] = 0
            row.distribution_plan = document
        with pytest.raises(InvalidPlan):
            self.books.get_plan(book_id)

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


def forget_flashes(client) -> None:
    """Drop what earlier requests flashed, so the next assertion is about one."""
    with client.session_transaction() as session:
        session.pop("_flashes", None)


def _setup_print_form(cells, *, count=100, split=(45, 40, 15)):
    """A complete Print setup submission carrying the plan ``cells`` describe."""
    form = {
        "unit": "cm",
        "width": "21.59",
        "height": "27.94",
        "plan_count": str(count),
    }
    for tier, share in zip(TIERS, split):
        form[f"split_{tier.value}"] = str(share)
    for b, row in enumerate(cells):
        for tier, value in zip(TIERS, row):
            form[f"cell_{b}_{tier.value}"] = str(value)
    return form


def _settle_print_setup(client, shelf, book_id, form, *, limit=6):
    """Submit ``form`` to Print setup until the stored plan stops moving.

    An arbitrary matrix is **not** a fixed point of the form on first
    submission: ``revise_plan`` marks a cell hand-edited only when its value
    differs from the one the page *showed*, and re-derives every unedited cell
    from the count and split — so the first POST can store something other
    than what was typed, and the next POST of the identical form is the one
    that sees those values on the page and keeps them. Repeating the identical
    submission converges (three POSTs, from a plan-less book or from a stored
    plan carrying no edit marks); this asserts that it converges instead of
    assuming how many it takes, and returns the settled plan.
    """
    previous = None
    for _ in range(limit):
        assert client.post(f"/book/{book_id}/setup-print", data=form).status_code == 302
        stored = shelf.books.get_plan(book_id)
        if stored == previous:
            return stored
        previous = stored
    raise AssertionError(
        f"Print setup did not settle within {limit} identical submissions"
    )


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

    def test_the_finalize_route_flashes_it(self, panel) -> None:
        """Review cycle 2, F-003: the *other* user-facing exit from draft.

        ``POST /book/<id>/finalize`` with ``action=save_and_finish`` is the
        second way the owner leaves draft, and the card's route audit claims
        it "flashes the refusal and the page re-renders with the status
        unchanged". Nothing pinned that: what turns the refusal into a flash
        there is a bare ``except Exception``, so a future change to the handler
        could swallow it silently. The route renders (200) rather than
        redirecting, so the flash is read out of the rendered page — the
        template consumes it — rather than out of the session.
        """
        app, shelf = panel
        book_id = shelf.book(cells_of(AC220_SELECTION))
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/finalize", data={"action": "save_and_finish"}
        )

        assert response.status_code == 200
        shown = response.get_data(as_text=True)
        assert OFFENDING_CELL_TEXT in shown, [
            line for line in shown.splitlines() if "Error" in line
        ]
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

    def test_the_guarantee_is_the_matrix_not_the_count(self) -> None:
        """CK-1 holds because AC_PLAN's matrix sums to its count — F-004.

        What refuses the half-book is that every *cell* is short of its own
        planned cell, and that is only equivalent to "half the planned book"
        while the matrix and the count agree. The claim is pinned here so that
        CK-1 is read as the per-cell rule it is; the plan for which the two
        part company is in
        ``TestBookReady_DisagreeingMatrixIsMeasuredAgainstTheStatedTotal``.
        """
        assert sum(sum(row) for row in AC_PLAN.cells) == AC_PLAN.count == 100
        assert not AC_PLAN.disagrees_with_split


# --------------------------------------------------------------------------
# F-004 — how far "ready means the planned book" actually reaches
# --------------------------------------------------------------------------


class TestBookReady_DisagreeingMatrixIsMeasuredAgainstTheStatedTotal:
    """Review cycle 2, F-004 — a declaration correction, not a behaviour change.

    ``off_plan_cells`` claimed that "ready" means the planned book rather than
    merely the planned mix, so "an under-filled selection fails even when its
    proportions are right". That holds **exactly when the matrix sums to the
    plan's count**. FR-034 deliberately lets a hand edit leave the matrix
    disagreeing with its split (``DistributionPlan.disagrees_with_split`` —
    warned about on Print setup, never refused), and the gate then measures
    each cell against the *stated* total anyway: a plan of 100 whose cells sum
    to 5 is satisfied by a selection of 5, every cell 0 points out.

    That is not an INV-007 hole — INV-007 is a per-cell rule and every cell is
    on its plan — and the behaviour is correct as designed: the matrix is what
    the owner planned cell by cell, and the count is what the shares are taken
    over. Only the sentence was wrong. These cases pin what is actually true,
    including that such a plan is reachable through the Print setup form and
    not only by constructing a ``DistributionPlan`` by hand.
    """

    #: 100 planned, but the matrix asks for five puzzles and no more.
    DISAGREEING_CELLS = ((5, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0))
    ONLY_FIVE_PLANNED = DistributionPlan(
        count=100, split=Split(45, 40, 15), cells=DISAGREEING_CELLS
    )

    def test_the_plan_really_does_disagree_with_its_split(self) -> None:
        assert self.ONLY_FIVE_PLANNED.count == 100
        assert sum(sum(row) for row in self.ONLY_FIVE_PLANNED.cells) == 5
        assert self.ONLY_FIVE_PLANNED.disagrees_with_split

    def test_such_a_plan_is_reachable_through_the_print_setup_form(self) -> None:
        """Through ``revise_plan``, which is all ``_plan_from_form`` calls.

        The form validates whole numbers, a split summing to 100 and a count
        of at least 1 — nothing compares the matrix with the count — so an
        owner who types these 12 values into Print setup stores this plan.
        """
        submitted = book_manager_module.revise_plan(
            None, 100, Split(45, 40, 15), self.DISAGREEING_CELLS
        )

        assert submitted.count == 100
        assert submitted.cells == self.DISAGREEING_CELLS
        assert submitted.disagrees_with_split

    def test_five_puzzles_satisfy_a_plan_of_a_hundred_that_asks_for_five(
        self, shelf
    ) -> None:
        """The honest limit of the guarantee, driven through the real gate."""
        book_id = shelf.book(
            cells_of(self.DISAGREEING_CELLS), plan=self.ONLY_FIVE_PLANNED
        )

        assert shelf.books.set_book_status(book_id, READY_FOR_PDF) is True
        assert shelf.status(book_id) == READY_FOR_PDF

    def test_the_cells_are_still_measured_against_the_stated_total(
        self, shelf
    ) -> None:
        """And the denominator really is 100, not the matrix's 5.

        Eight held against five planned is 3 points of the stated 100, which
        is inside the tolerance; nine is 4 points, which is not. Measured
        against the matrix's own sum, eight would be 60 points out.
        """
        inside = shelf.book(
            cells_of(((8, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0))),
            plan=self.ONLY_FIVE_PLANNED,
            title="Eight",
        )
        outside = shelf.book(
            cells_of(((9, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0))),
            plan=self.ONLY_FIVE_PLANNED,
            title="Nine",
        )

        assert shelf.books.set_book_status(inside, READY_FOR_PDF) is True
        assert "<=15 x easy: 9% against 5%" in shelf.refusal(outside)
        assert shelf.status(outside) == DRAFT


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

    def test_a_damaged_stored_plan_is_refused_with_the_same_remedy(self, scope) -> None:
        """Review cycle 2, F-001: a document that will not decode is no plan.

        The gate used to let ``InvalidPlan`` out of ``get_plan``, so the owner
        of a book with a damaged ``distribution_plan`` was shown a decode
        message ("the puzzle count must be a whole number of at least 1, got
        0") instead of ADR-0035 (c)'s remedy. It was still fail-closed — the
        status never moved — but the one screen that can repair the document
        was never named.

        DB mode only, and deliberately so: the in-memory branch stores plan
        objects the aggregate has already accepted and can never hold a
        document like this, which is the storage-mode asymmetry F-001 also
        reported. ``shelf.damage_plan`` asserts the document really is
        undecodable, so the case cannot quietly stop testing anything.
        """
        shelf = Shelf("db", scope)
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.damage_plan(book_id)

        refusal = shelf.refusal(book_id)

        assert "no stored plan" in refusal
        assert "Print setup" in refusal
        assert shelf.status(book_id) == DRAFT

    def test_a_damaged_plan_is_overwritten_by_the_remedy(self, scope) -> None:
        """And the remedy works on it: storing a plan is still the whole fix."""
        shelf = Shelf("db", scope)
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.damage_plan(book_id)
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
# Review cycle 1, F-004 — a selection the gate cannot read is not an empty one
# --------------------------------------------------------------------------


class TestBookReady_UnreadableSelectionIsRefused:
    """The gate concludes nothing from a selection it could not read.

    Driven in the finding's own configuration: a manager wired without a
    puzzle store, a book holding one id, and :data:`NOTHING_PLANNED` — the
    plan an empty selection matches. Reading the unread selection as an empty
    one (what ``_selection_records`` did until this fix) approves that book,
    which is why "fail-closed" was a false claim rather than a true one.

    The discriminator is *"there are ids to resolve and nothing to resolve
    them with"*, not *"there is no store"*: a book holding no ids is genuinely
    empty, needs no store to be judged, and is refused a step earlier by the
    "Must have puzzles" rule. The two tests below pin both sides of that.
    """

    @staticmethod
    def _manager(mode, scope):
        return BookManager(
            session_factory=None if mode == "memory" else scope, puzzle_store=None
        )

    @pytest.mark.parametrize("mode", MODES)
    @pytest.mark.parametrize("target", OUT_OF_DRAFT)
    def test_a_store_less_manager_refuses_every_exit_from_draft(
        self, mode, scope, target
    ) -> None:
        books = self._manager(mode, scope)
        book_id = books.create_book("Unreadable", "a book", "christmas", "adults")
        books.add_puzzles_to_book(book_id, [str(uuid.uuid4())])
        books.save_plan(book_id, NOTHING_PLANNED)

        with pytest.raises(ValueError, match="cannot be read"):
            books.set_book_status(book_id, target)

        assert books.get_book(book_id).status == DRAFT

    @pytest.mark.parametrize("mode", MODES)
    def test_an_empty_book_is_still_refused_for_being_empty(self, mode, scope) -> None:
        """Not conflated: "nothing to read" is not "nothing could be read"."""
        books = self._manager(mode, scope)
        book_id = books.create_book("Empty", "a book", "christmas", "adults")
        books.save_plan(book_id, NOTHING_PLANNED)

        with pytest.raises(ValueError, match="Must have puzzles"):
            books.set_book_status(book_id, READY_FOR_PDF)

    def test_with_a_store_an_unresolvable_id_still_counts_towards_no_cell(self) -> None:
        """The refusal is about the missing store, not about the missing row.

        A store that holds no row for the id is a store that answered: the id
        contributes to no cell, exactly as a record with an unrecognisable
        tier does. That is the behaviour this card inherited and did not
        change; only the store-less case moved.
        """
        books = BookManager(
            session_factory=None, puzzle_store=PuzzleReviewService(session_factory=None)
        )
        book_id = books.create_book("Placeholders", "a book", "christmas", "adults")
        books.add_puzzles_to_book(book_id, ["puzzle_000001"])
        books.save_plan(book_id, NOTHING_PLANNED)

        assert books.set_book_status(book_id, READY_FOR_PDF) is True


# --------------------------------------------------------------------------
# The owner's decision: a plan edit on a non-draft book returns it to draft
# --------------------------------------------------------------------------


class TestBookPlanEdit_OnANonDraftBookReturnsItToDraft:
    """CARD-124 owner decision (ADR-0035 "Membership change after draft").

    The plan is what the gate measures the selection against, so editing it
    unmakes the verdict that let the book out. The book goes back to draft and
    through the same gate, rather than the edit being refused.
    """

    @pytest.mark.parametrize("target", OUT_OF_DRAFT)
    def test_save_plan_returns_the_book_to_draft(self, shelf, target) -> None:
        """Every non-draft status, ``published`` included.

        ``published`` is the one status the other two domain writers treat
        differently (``set_book_status`` and ``add_puzzles_to_book`` both
        refuse to touch a published book), so the plan-edit rule is pinned
        there explicitly rather than left to ``ready_for_kdp`` to stand for.
        The owner's decision (see the class docstring) is deliberately uniform
        across statuses: INV-008 scopes its confirmation to a published book's
        *puzzle membership*, which ``save_plan`` never writes.
        """
        book_id = shelf.book(cells_of(AC218_SELECTION), title=f"From {target}")
        shelf.books.set_book_status(book_id, target)

        assert shelf.books.save_plan(book_id, EDITED_PLAN) is True

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
        book_id = shelf.book(cells_of(AC218_SELECTION), plan=AC_PLAN_AS_STORED)
        shelf.books.set_book_status(book_id, READY_FOR_PDF)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/setup-print", data=_setup_print_form(EDITED_PLAN_CELLS)
        )

        assert response.status_code == 302
        assert shelf.books.get_plan(book_id) == EDITED_PLAN_AS_STORED
        assert shelf.status(book_id) == DRAFT
        assert any("back in draft" in message for message in flashes(client)), flashes(client)

    def test_print_setup_leaves_a_book_alone_when_the_plan_did_not_change(
        self, panel
    ) -> None:
        """Review cycle 1, F-003: an idempotent re-save is not a plan edit.

        Re-opening Print setup on a non-draft book and pressing Save with
        nothing altered used to return the book to draft and flash that "the
        plan changed" — an assertion that was simply false. Nothing is stored
        and nothing is said about the plan now; the trim half still saves and
        the step still moves on.

        Review cycle 2, F-002: the starting plan is now the one **the route
        itself** produces, reached by submitting the form until the stored
        plan settles, rather than a hand-built constant with all 12 cells
        marked edited. With every cell marked, ``revise_plan``'s edit-mark
        round trip is preserved trivially and the ``edited`` half of the
        frozen-dataclass ``==`` is not discriminated at all. The settled plan
        carries a *partial* edit set (asserted below), so a mark lost or
        gained in the round trip makes the submission unequal to the stored
        plan — which stores it, returns the book to draft and flashes, all
        three of which this test then fails on.
        """
        app, shelf = panel
        book_id = shelf.book(cells_of(AC218_SELECTION))
        client = app.test_client()
        form = _setup_print_form(AC_PLAN_CELLS)

        settled = _settle_print_setup(client, shelf, book_id, form)
        assert frozenset() < settled.edited < EVERY_CELL, (
            "the fixed point must mark some cells and not others, or the "
            f"edit-mark round trip is not discriminated: {settled.edited}"
        )
        shelf.books.set_book_status(book_id, READY_FOR_PDF)
        forget_flashes(client)

        response = client.post(f"/book/{book_id}/setup-print", data=form)

        assert response.status_code == 302
        assert shelf.books.get_plan(book_id) == settled
        assert shelf.status(book_id) == READY_FOR_PDF
        assert not any("back in draft" in message for message in flashes(client)), flashes(
            client
        )

    def test_print_setup_still_stores_the_first_plan_of_a_plan_less_book(
        self, panel
    ) -> None:
        """The "unchanged" shortcut must not swallow the very first save.

        A plan-less book shows DEFAULT_PLAN, so the owner can submit it
        untouched — and there is no stored plan for it to be equal to, which
        is exactly what makes the book unable to leave draft (CK-2).
        """
        app, shelf = panel
        book_id = shelf.book(cells_of(AC218_SELECTION))
        shelf.drop_plan(book_id)
        client = app.test_client()

        response = client.post(
            f"/book/{book_id}/setup-print", data=_setup_print_form(AC_PLAN_CELLS)
        )

        assert response.status_code == 302
        stored = shelf.books.get_plan(book_id)
        assert stored is not None
        assert stored.count == 100
