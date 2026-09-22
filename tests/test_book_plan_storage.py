"""CARD-120 — the distribution plan stored with the book.

    AC-196  TestBookPlan_StoredWithBookSurvivesReopen
    AC-197  TestBookPlan_RejectsSplitNotSummingTo100            (INV-005)
    AC-203  TestBookPlan_WarnsWhenHandEditedMatrixDisagreesWithSplit
    AC-204  TestBookCreate_StoresDefaultPlanThatSumsTo100        (INV-005)
    AC-205  TestBookCreate_DefaultPlanIs150At40_40_20
    EC-023  PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan — the store/reload
            round-trip half (the prefill half is CARD-119's, in
            tests/property/test_book_plan.py)
    G-2     saving a plan never touches the selection, order or titles
    G-3     a plan-less (pre-migration) book stays readable and editable
    010     the migration adds the column without backfill and downgrades

Every storage-level test runs in **both** storage modes: in memory, and DB mode
against a real SQLite file (not a mock) read back through fresh sessions. The
user-facing ACs (196, 197, 203) are driven through the Flask test client
against ``/book/<id>/setup-print``, in both modes too.

Expected values are stated independently of the code under test where it
matters: AC-198's literal matrix for the default plan, and the EC-023 oracle
(Fraction-based sequential apportionment, shares no code with ``book_plan``)
for the round-trip property.
"""

from __future__ import annotations

import random
import re
import uuid
from pathlib import Path

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager, plan_from_json, plan_to_json, revise_plan
from nonogram.admin.book_plan import (
    BOOK1_MATRIX,
    BUCKETS,
    DEFAULT_PLAN,
    TIERS,
    DistributionPlan,
    InvalidPlan,
    LongestSideBucket,
    Split,
    prefill,
    with_edited_cell,
    with_split,
)
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.difficulty import Tier
from tests.helpers.db import make_batch, make_book, sqlite_session_scope
from tests.property.test_book_plan import _oracle_apportion

B15, B20, B25, B30 = BUCKETS
E, M, H = TIERS

MODES = ("memory", "db")

#: AC-198's worked table for 150 at 40/40/20 — the literal numbers, not a
#: re-derivation through ``prefill``.
AC198_MATRIX = ((20, 7, 0), (30, 27, 6), (10, 20, 12), (0, 6, 12))


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "plans.db")


def _manager(mode, scope) -> BookManager:
    if mode == "memory":
        return BookManager(session_factory=None)
    return BookManager(session_factory=scope, puzzle_store=PuzzleReviewService(session_factory=scope))


@pytest.fixture(params=MODES)
def books(request, scope) -> BookManager:
    return _manager(request.param, scope)


def _new_book(books: BookManager, audience: str = "adults") -> str:
    return books.create_book("Winter", "Twenty winter pictures.", "generic", audience)


def _build_app(mode, scope, monkeypatch):
    """An admin app in ``mode`` — DB mode wired to the test's SQLite file."""
    from nonogram.admin.app import create_app

    monkeypatch.setenv("TESTING", "true")
    if mode == "memory":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # A fresh in-memory store: the module singleton would otherwise carry
        # this test's books into every later in-memory app.
        monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))
    else:
        import nonogram.db

        monkeypatch.setenv("DATABASE_URL", "sqlite:///card-120-test-only")
        monkeypatch.setattr(nonogram.db, "session_scope", scope)
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(params=MODES)
def mode(request):
    return request.param


@pytest.fixture
def app(mode, scope, monkeypatch):
    return _build_app(mode, scope, monkeypatch)


# --------------------------------------------------------------------------
# Page helpers
# --------------------------------------------------------------------------


def _input_value(html: str, input_id: str) -> str:
    """The ``value`` of the ``<input id="input_id">`` on the page."""
    match = re.search(r'<input\b[^>]*\bid="' + re.escape(input_id) + r'"[^>]*>', html, re.S)
    assert match, f"no input #{input_id} on the page"
    value = re.search(r'\bvalue="([^"]*)"', match.group(0))
    assert value, f"input #{input_id} has no value"
    return value.group(1)


def _page(client, book_id) -> str:
    response = client.get(f"/book/{book_id}/setup-print")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _shown_plan(html: str) -> tuple[int, tuple[int, int, int], tuple[tuple[int, ...], ...]]:
    count = int(_input_value(html, "plan_count"))
    split = tuple(int(_input_value(html, f"split_{t.value}")) for t in TIERS)
    cells = tuple(
        tuple(int(_input_value(html, f"cell_{b}_{t.value}")) for t in TIERS) for b in range(len(BUCKETS))
    )
    return count, split, cells


def _form(count, split, cells, *, width="21.59", height="27.94") -> dict:
    form = {"unit": "cm", "width": width, "height": height, "plan_count": str(count)}
    for tier, share in zip(TIERS, split):
        form[f"split_{tier.value}"] = str(share)
    for b, row in enumerate(cells):
        for tier, value in zip(TIERS, row):
            form[f"cell_{b}_{tier.value}"] = str(value)
    return form


def _columns(cells) -> tuple[int, ...]:
    return tuple(sum(row[t] for row in cells) for t in range(3))


# --------------------------------------------------------------------------
# AC-205 / AC-204 — the default plan stored on creation
# --------------------------------------------------------------------------


class TestBookCreate_DefaultPlanIs150At40_40_20:
    """AC-205 — a new book's stored plan is 150 at 40/40/20 (60/60/30)."""

    def test_stored_plan_is_the_default(self, books) -> None:
        plan = books.get_plan(_new_book(books))

        assert plan is not None
        assert plan.count == 150
        assert (plan.split.easy, plan.split.medium, plan.split.hard) == (40, 40, 20)
        assert _columns(plan.cells) == (60, 60, 30)
        assert plan.cells == AC198_MATRIX
        assert plan.edited == frozenset()

    def test_through_the_create_form(self, app) -> None:
        client = app.test_client()
        response = client.post(
            "/book/create",
            data={"title": "Winter", "description": "d", "theme": "generic", "target_audience": "seniors"},
        )
        assert response.status_code == 302
        book_id = response.headers["Location"].rstrip("/").split("/")[-2]

        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN
        assert _shown_plan(_page(client, book_id)) == (150, (40, 40, 20), AC198_MATRIX)

    def test_the_default_does_not_depend_on_the_audience(self, books) -> None:
        """G-1: target_audience is free text and is not read by plan code."""
        plans = {books.get_plan(_new_book(books, audience)) for audience in ("seniors", "kids", "adults")}
        assert plans == {DEFAULT_PLAN}


class TestBookCreate_StoresDefaultPlanThatSumsTo100:
    """AC-204 (INV-005) — split sums to 100, matrix equals that split's prefill."""

    def test_split_sums_to_100_and_matrix_is_its_prefill(self, books) -> None:
        plan = books.get_plan(_new_book(books))

        assert plan.split.easy + plan.split.medium + plan.split.hard == 100
        assert plan.cells == prefill(plan.count, plan.split).cells
        assert all(isinstance(v, int) and v >= 0 for row in plan.cells for v in row)
        assert sum(v for row in plan.cells for v in row) == plan.count
        assert not plan.disagrees_with_split


# --------------------------------------------------------------------------
# AC-196 — stored with the book, survives reopening
# --------------------------------------------------------------------------


class TestBookPlan_StoredWithBookSurvivesReopen:
    """AC-196 — Print setup saved with 150 at 40/40/20 reads back from the book."""

    def test_saved_plan_is_shown_on_reopen(self, mode, scope, monkeypatch) -> None:
        app = _build_app(mode, scope, monkeypatch)
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        # First store something else, so reading 150 at 40/40/20 back below
        # proves a write and a read rather than an untouched default.
        # The matrix is submitted as the page showed it (the default's), so
        # POL-007 re-derives it: no cell is hand-edited. (Posting other.cells
        # here would be typing 12 new values — hand edits that, since F-001,
        # rightly survive the next split change.)
        other = prefill(120, Split(30, 45, 25))
        response = client.post(f"/book/{book_id}/setup-print", data=_form(120, (30, 45, 25), AC198_MATRIX))
        assert response.status_code == 302
        assert _shown_plan(_page(client, book_id)) == (120, (30, 45, 25), other.cells)

        response = client.post(
            f"/book/{book_id}/setup-print", data=_form(150, (40, 40, 20), other.cells)
        )
        assert response.status_code == 302
        assert "/select-puzzles" in response.headers["Location"]

        # Leave the workflow: a new client (no session). In DB mode a new app
        # too, so nothing but the stored row can carry the plan.
        if mode == "db":
            app = _build_app(mode, scope, monkeypatch)
        count, split, cells = _shown_plan(_page(app.test_client(), book_id))

        assert (count, split) == (150, (40, 40, 20))
        # The matrix was never hand-edited, so the split change re-derived it.
        assert cells == AC198_MATRIX

    def test_trim_only_submission_keeps_the_plan(self, app) -> None:
        """A form without the plan fields still works exactly as before."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        app.book_manager.save_plan(book_id, prefill(99, Split(50, 30, 20)))

        response = client.post(
            f"/book/{book_id}/setup-print", data={"unit": "cm", "width": "21.59", "height": "27.94"}
        )

        assert response.status_code == 302
        assert "/select-puzzles" in response.headers["Location"]
        assert app.book_manager.get_plan(book_id) == prefill(99, Split(50, 30, 20))

    def test_trim_fields_still_refuse_an_out_of_range_size(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(150, (30, 45, 25), AC198_MATRIX, width="5"),
        )

        assert response.status_code == 200
        assert "alert-danger" in response.get_data(as_text=True)
        # A refused submission stores nothing, the plan included.
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN


# --------------------------------------------------------------------------
# AC-197 — a split not summing to 100 is refused, stored plan unchanged
# --------------------------------------------------------------------------


class TestBookPlan_RejectsSplitNotSummingTo100:
    """AC-197 (INV-005)."""

    def test_route_refuses_110_percent_and_keeps_the_stored_plan(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert app.book_manager.get_plan(book_id) == prefill(150, Split(40, 40, 20))
        size_before = app.book_manager.get_book(book_id).metadata.size

        # A valid, non-default trim alongside the refused split: the refusal
        # must store nothing, the trim included (review F-005).
        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(150, (40, 40, 30), AC198_MATRIX, width="15.24", height="22.86"),
        )

        assert response.status_code == 200  # re-rendered, not redirected on
        html = response.get_data(as_text=True)
        assert 'class="alert alert-danger"' in html
        assert "Plan not saved" in html
        assert "110%" in html
        # The refused values stay in the fields, marked invalid, for correcting.
        assert _input_value(html, "split_hard") == "30"
        assert "is-invalid" in html

        assert app.book_manager.get_book(book_id).metadata.size == size_before
        assert "15.24" not in (size_before or "")

        stored = app.book_manager.get_plan(book_id)
        assert stored.count == 150
        assert (stored.split.easy, stored.split.medium, stored.split.hard) == (40, 40, 20)
        assert stored == DEFAULT_PLAN
        assert _shown_plan(_page(client, book_id)) == (150, (40, 40, 20), AC198_MATRIX)

    @pytest.mark.parametrize(
        "field, value",
        [("split_easy", "39"), ("split_easy", "forty"), ("plan_count", "0"), ("cell_2_hard", "-1"),
         ("cell_0_easy", "2.5")],
    )
    def test_route_refuses_other_values_inv005_does_not_allow(self, app, field, value) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX)
        form[field] = value

        response = client.post(f"/book/{book_id}/setup-print", data=form)

        assert response.status_code == 200
        assert "Plan not saved" in response.get_data(as_text=True)
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN

    def test_the_refusal_is_the_aggregates_own(self) -> None:
        """DDD: the split rule lives in Split, and save_plan takes only a plan."""
        with pytest.raises(InvalidPlan):
            Split(40, 40, 30)

    def test_save_plan_accepts_nothing_but_a_plan(self, books) -> None:
        book_id = _new_book(books)
        with pytest.raises(InvalidPlan):
            books.save_plan(book_id, {"count": 150, "split": {"easy": 40, "medium": 40, "hard": 30}})
        assert books.get_plan(book_id) == DEFAULT_PLAN

    def test_a_malformed_stored_document_is_refused_on_the_way_out(self) -> None:
        document = plan_to_json(DEFAULT_PLAN)
        document["split"] = {"easy": 40, "medium": 40, "hard": 30}
        with pytest.raises(InvalidPlan):
            plan_from_json(document)
        with pytest.raises(InvalidPlan):
            plan_from_json({"count": 150})


# --------------------------------------------------------------------------
# AC-203 — the warning
# --------------------------------------------------------------------------


class TestBookPlan_WarnsWhenHandEditedMatrixDisagreesWithSplit:
    """AC-203.

    AC-203 is worded "the same hand-edited plan" as AC-202 (21-25 x hard hand
    edited 12 -> 15, then split 30/45/25). Measured: 15 is exactly the 30/45/25
    prefill of that cell (hard 38 over 0/5/10/10 -> 0/8/15/15), so that plan
    does NOT disagree and no warning is due — asserted below as the literal
    case. The warning is driven with the same steps and an edit that does
    break the column (12 -> 20).
    """

    def _edit_then_change_split(self, client, book_id, edited_value):
        cells = [list(row) for row in AC198_MATRIX]
        cells[2][2] = edited_value  # 21-25 x hard
        response = client.post(f"/book/{book_id}/setup-print", data=_form(150, (40, 40, 20), cells))
        assert response.status_code == 302

        # Change only the split; the matrix is submitted exactly as the page shows it.
        _, _, shown = _shown_plan(_page(client, book_id))
        response = client.post(f"/book/{book_id}/setup-print", data=_form(150, (30, 45, 25), shown))
        assert response.status_code == 302
        return _page(client, book_id)

    def test_warning_shown_when_the_kept_edit_breaks_the_column(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        html = self._edit_then_change_split(client, book_id, 20)

        assert 'class="alert alert-warning"' in html
        assert "disagrees with the general split" in html
        plan = app.book_manager.get_plan(book_id)
        assert plan.split == Split(30, 45, 25)
        assert plan.cell(B25, H) == 20
        assert plan.edited == {(B25, H)}
        assert plan.disagrees_with_split
        # Every unedited cell followed the split (POL-007).
        fresh = prefill(150, Split(30, 45, 25))
        for bucket in BUCKETS:
            for tier in TIERS:
                if (bucket, tier) != (B25, H):
                    assert plan.cell(bucket, tier) == fresh.cell(bucket, tier)
        # The edited cell is marked for sighted and screen-reader users alike.
        assert 'data-edited="true"' in html
        assert "Longest side 21-25, hard (hand-edited)" in html

    def test_ac202s_literal_edit_keeps_15_and_agrees(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        html = self._edit_then_change_split(client, book_id, 15)

        plan = app.book_manager.get_plan(book_id)
        assert plan.cell(B25, H) == 15
        assert plan.edited == {(B25, H)}
        assert "alert-warning" not in html

    def test_no_warning_for_a_prefilled_plan(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert "alert-warning" not in _page(client, book_id)


# --------------------------------------------------------------------------
# revise_plan — which cells a submission hand-edits (POL-007)
# --------------------------------------------------------------------------


class TestRevisePlan:
    def test_unedited_matrix_rederived_on_split_change(self) -> None:
        revised = revise_plan(DEFAULT_PLAN, 150, Split(30, 45, 25), DEFAULT_PLAN.cells)
        assert revised == prefill(150, Split(30, 45, 25))

    def test_count_change_rederives_an_unedited_matrix(self) -> None:
        revised = revise_plan(DEFAULT_PLAN, 90, Split(40, 40, 20), DEFAULT_PLAN.cells)
        assert revised == prefill(90, Split(40, 40, 20))

    def test_a_typed_cell_is_edited_and_kept(self) -> None:
        cells = [list(r) for r in DEFAULT_PLAN.cells]
        cells[0][0] = 3
        revised = revise_plan(DEFAULT_PLAN, 150, Split(30, 45, 25), cells)
        assert revised.cell(B15, E) == 3
        assert revised.edited == {(B15, E)}

    def test_typing_a_cell_back_to_its_prefill_un_edits_it(self) -> None:
        stored = with_edited_cell(DEFAULT_PLAN, B30, M, 11)
        revised = revise_plan(stored, 150, Split(40, 40, 20), DEFAULT_PLAN.cells)
        assert revised == DEFAULT_PLAN

    def test_a_plan_less_book_is_revised_from_the_default_it_was_shown(self) -> None:
        assert revise_plan(None, 150, Split(40, 40, 20), DEFAULT_PLAN.cells) == DEFAULT_PLAN

    def test_changing_an_edit_that_equals_the_prefill_keeps_it_edited(self) -> None:
        """An edited 15 that coincides with the 30/45/25 prefill, retyped to 17: still edited."""
        stored = with_split(with_edited_cell(DEFAULT_PLAN, B25, H, 15), Split(30, 45, 25))
        assert stored.cell(B25, H) == prefill(150, Split(30, 45, 25)).cell(B25, H) == 15
        cells = [list(r) for r in stored.cells]
        cells[2][2] = 17
        revised = revise_plan(stored, 150, Split(30, 45, 25), cells)
        assert revised.cell(B25, H) == 17
        assert revised.edited == {(B25, H)}


# --------------------------------------------------------------------------
# Review F-001 — a stored hand edit survives an unchanged resubmission
# --------------------------------------------------------------------------


class TestRevisePlan_StoredEditSurvivesUnchangedResubmit:
    """F-001: "hand-edited" is carried forward from the stored plan.

    The review's own scenario: at 40/40/20 edit 21-25 x hard 12 -> 15 (edited);
    change the split to 30/45/25 (15 kept — and 15 is now that split's prefill);
    resubmit the page unchanged (every Print setup visit is a submit); change
    the split back to 40/40/20. The old revise_plan dropped the mark at step 3
    (15 == new prefill) and step 4 re-derived the cell to 12.
    """

    def _steps(self, submit):
        """Drive steps 1-4 through ``submit(count, split, cells)`` -> stored plan."""
        cells = [list(r) for r in DEFAULT_PLAN.cells]
        cells[2][2] = 15
        submit(150, (40, 40, 20), cells)                     # 1. edit
        plan = submit(150, (30, 45, 25), cells)              # 2. split change, matrix as shown
        plan = submit(150, (30, 45, 25), plan.cells)         # 3. unchanged resubmit
        return submit(150, (40, 40, 20), plan.cells)         # 4. split back, matrix as shown

    def test_storage_level(self, books) -> None:
        book_id = _new_book(books)

        def submit(count, split, cells):
            books.save_plan(book_id, revise_plan(books.get_plan(book_id), count, Split(*split), cells))
            return books.get_plan(book_id)

        plan = self._steps(submit)

        assert plan.cell(B25, H) == 15
        assert plan.edited == {(B25, H)}
        fresh = prefill(150, Split(40, 40, 20))
        for bucket in BUCKETS:
            for tier in TIERS:
                if (bucket, tier) != (B25, H):
                    assert plan.cell(bucket, tier) == fresh.cell(bucket, tier)

    def test_through_the_route(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        def submit(count, split, cells):
            response = client.post(f"/book/{book_id}/setup-print", data=_form(count, split, cells))
            assert response.status_code == 302
            plan = app.book_manager.get_plan(book_id)
            # What the owner sees is what the next submit carries.
            assert _shown_plan(_page(client, book_id)) == (
                plan.count, (plan.split.easy, plan.split.medium, plan.split.hard), plan.cells
            )
            return plan

        plan = self._steps(submit)

        assert plan.cell(B25, H) == 15
        assert plan.edited == {(B25, H)}
        assert "Longest side 21-25, hard (hand-edited)" in _page(client, book_id)


# --------------------------------------------------------------------------
# Review F-002 / F-003 / F-004 — Print setup feedback
# --------------------------------------------------------------------------


def _flashes(client):
    with client.session_transaction() as sess:
        return list(sess.get("_flashes", []))


def _input_tag(html: str, input_id: str) -> str:
    match = re.search(r'<input\b[^>]*\bid="' + re.escape(input_id) + r'"[^>]*>', html, re.S)
    assert match, f"no input #{input_id} on the page"
    return match.group(0)


class TestPrintSetup_WarnsWhenADisagreeingPlanIsSaved:
    """F-002: the FR-034 warning at the moment the disagreeing plan is saved."""

    def test_warning_flash_on_save(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        cells = [list(r) for r in AC198_MATRIX]
        cells[2][2] = 20

        response = client.post(f"/book/{book_id}/setup-print", data=_form(150, (40, 40, 20), cells))

        assert response.status_code == 302
        assert app.book_manager.get_plan(book_id).disagrees_with_split
        warnings = [m for c, m in _flashes(client) if c == "warning"]
        assert len(warnings) == 1
        assert "disagrees with the general split" in warnings[0]
        assert "60 / 60 / 38" in warnings[0] and "60 / 60 / 30" in warnings[0]

    def test_no_warning_flash_for_an_agreeing_plan(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        client.post(f"/book/{book_id}/setup-print", data=_form(150, (40, 40, 20), AC198_MATRIX))

        assert [c for c, _ in _flashes(client)] == ["success"]


class TestPrintSetup_RefusalKeepsInputAndMarksOnlyTheFailingField:
    """F-003: a refused submission comes back whole, with only its failing field(s) invalid."""

    def test_refused_split_keeps_the_typed_matrix(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        cells = [list(r) for r in AC198_MATRIX]
        cells[0][0] = 3  # an unrelated matrix edit that must not be lost

        html = client.post(
            f"/book/{book_id}/setup-print", data=_form(150, (40, 40, 30), cells)
        ).get_data(as_text=True)

        assert _input_value(html, "cell_0_easy") == "3"
        for tier in TIERS:
            assert "is-invalid" in _input_tag(html, f"split_{tier.value}")
        assert "is-invalid" not in _input_tag(html, "plan_count")
        assert "is-invalid" not in _input_tag(html, "cell_0_easy")
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN

    @pytest.mark.parametrize(
        "field, value", [("plan_count", "0"), ("cell_2_hard", "-1"), ("cell_0_easy", "2.5")]
    )
    def test_only_the_failing_field_is_marked(self, app, field, value) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX)
        form[field] = value

        html = client.post(f"/book/{book_id}/setup-print", data=form).get_data(as_text=True)

        assert "Plan not saved" in html
        assert _input_value(html, field) == value
        tag = _input_tag(html, field)
        assert "is-invalid" in tag and 'aria-describedby="plan-error"' in tag
        assert html.count("is-invalid") == 1
        for tier in TIERS:
            assert "is-invalid" not in _input_tag(html, f"split_{tier.value}")

    def test_trim_refusal_carries_the_plan_input_back(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        cells = [list(r) for r in prefill(120, Split(30, 45, 25)).cells]
        cells[1][1] = 33

        html = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(120, (30, 45, 25), cells, width="5"),
        ).get_data(as_text=True)

        assert _shown_plan(html) == (120, (30, 45, 25), tuple(tuple(r) for r in cells))
        assert _input_value(html, "width") == "5"
        assert "is-invalid" not in html  # the plan was fine
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN


class TestPrintSetup_UnreadableStoredPlanCanBeOverwritten:
    """F-004: a stored document the aggregate refuses does not break Print setup."""

    def test_damaged_plan_shows_default_and_a_submit_repairs_it(self, scope, monkeypatch) -> None:
        from nonogram.db.models import Book as DBBook

        app = _build_app("db", scope, monkeypatch)
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        broken = plan_to_json(DEFAULT_PLAN)
        broken["split"] = {"easy": 40, "medium": 40, "hard": 30}
        with scope() as db:
            row = db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).one()
            row.distribution_plan = broken
        with pytest.raises(InvalidPlan):
            app.book_manager.get_plan(book_id)

        html = _page(client, book_id)
        assert 'id="plan-damaged"' in html
        assert "no stored plan yet" not in html
        assert _shown_plan(html) == (150, (40, 40, 20), AC198_MATRIX)

        response = client.post(
            f"/book/{book_id}/setup-print", data=_form(120, (30, 45, 25), AC198_MATRIX)
        )
        assert response.status_code == 302
        assert app.book_manager.get_plan(book_id) == prefill(120, Split(30, 45, 25))
        assert 'id="plan-damaged"' not in _page(client, book_id)


# --------------------------------------------------------------------------
# G-2 — save_plan writes plan columns only
# --------------------------------------------------------------------------


def _add_puzzle(store, batch_id, name):
    return store.add_puzzle(
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
        source_image=f"{name}.png",
    )


class TestSavePlan_NeverTouchesTheSelection:
    """G-2 / FR-038: selection, order and custom titles are unchanged by save_plan."""

    @pytest.mark.parametrize("mode", MODES)
    def test_selection_order_titles_and_status_unchanged(self, mode, scope) -> None:
        books = _manager(mode, scope)
        book_id = _new_book(books)
        if mode == "db":
            batch_id = make_batch(scope, source="random", total_count=3)
            ids = [_add_puzzle(books.puzzle_store, batch_id, n) for n in ("a", "b", "c")]
        else:
            ids = [str(uuid.uuid4()) for _ in range(3)]
        books.add_puzzles_to_book(book_id, ids)
        books.reorder_puzzles(book_id, [ids[2], ids[0], ids[1]])
        books.set_puzzle_title(book_id, ids[0], "First light")
        before = books.get_book(book_id)
        before_ids, before_titles = list(before.puzzle_ids), dict(before.puzzle_titles)

        new_plan = with_edited_cell(prefill(77, Split(20, 50, 30)), B20, M, 9)
        assert books.save_plan(book_id, new_plan) is True

        after = books.get_book(book_id)
        assert after.puzzle_ids == before_ids == [ids[2], ids[0], ids[1]]
        assert after.puzzle_titles == before_titles == {ids[0]: "First light"}
        assert after.status == before.status == "draft"
        assert books.get_plan(book_id) == new_plan
        if mode == "db":
            for pid in ids:
                assert books.puzzle_store.get_puzzle(pid)["book_id"] == book_id

    def test_unknown_book(self, books) -> None:
        missing = str(uuid.uuid4()) if books._session_factory else "book_999999"
        assert books.save_plan(missing, DEFAULT_PLAN) is False
        assert books.get_plan(missing) is None


# --------------------------------------------------------------------------
# G-3 — a plan-less book stays readable and editable
# --------------------------------------------------------------------------


class TestPlanLessBook_StaysReadableAndEditable:
    def test_db_book_without_a_plan(self, scope, monkeypatch) -> None:
        app = _build_app("db", scope, monkeypatch)
        book_id = make_book(scope, title="Legacy")  # as a pre-010 row: plan NULL
        client = app.test_client()

        assert app.book_manager.get_book(book_id).metadata.title == "Legacy"
        assert app.book_manager.get_plan(book_id) is None
        html = _page(client, book_id)
        assert "no stored plan yet" in html
        assert _shown_plan(html) == (150, (40, 40, 20), AC198_MATRIX)

        response = client.post(f"/book/{book_id}/setup-print", data=_form(150, (40, 40, 20), AC198_MATRIX))
        assert response.status_code == 302
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN

    def test_memory_book_without_a_plan(self, monkeypatch, scope) -> None:
        app = _build_app("memory", scope, monkeypatch)
        book_id = _new_book(app.book_manager)
        app.book_manager._plans.pop(book_id)  # a book from before plans existed

        assert "no stored plan yet" in _page(app.test_client(), book_id)
        assert app.book_manager.get_book(book_id) is not None


# --------------------------------------------------------------------------
# Migration 010
# --------------------------------------------------------------------------


def _alembic(database_url, monkeypatch):
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parent.parent
    # No ini file on purpose: with one, migrations/env.py calls
    # logging.config.fileConfig, which disables every logger already created
    # and silences later tests that assert on log output (caplog).
    config = Config()
    config.set_main_option("script_location", str(root / "migrations"))
    monkeypatch.setenv("DATABASE_URL", database_url)
    return command, config


class TestMigration010:
    def test_chain_and_revision(self) -> None:
        import importlib.util

        path = Path(__file__).resolve().parent.parent / "migrations" / "versions" / "010_book_distribution_plan.py"
        spec = importlib.util.spec_from_file_location("migration_010", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert (module.revision, module.down_revision) == ("010", "009")

    def test_upgrade_adds_a_null_column_without_backfill_and_downgrade_drops_it(
        self, tmp_path, monkeypatch
    ) -> None:
        import sqlalchemy as sa

        url = f"sqlite:///{tmp_path / 'migrate.db'}"
        command, config = _alembic(url, monkeypatch)
        command.upgrade(config, "009")
        engine = sa.create_engine(url)
        legacy = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO books (id, title, puzzle_ids, puzzle_titles, book_metadata, status)"
                    " VALUES (:id, 'Legacy', '[]', '{}', '{}', 'draft')"
                ),
                {"id": legacy.hex},
            )

        command.upgrade(config, "010")
        with engine.connect() as conn:
            columns = {c["name"] for c in sa.inspect(conn).get_columns("books")}
            assert "distribution_plan" in columns
            rows = conn.execute(sa.text("SELECT title, distribution_plan FROM books")).all()
        assert rows == [("Legacy", None)]  # no backfill

        # The ORM reads the migrated row: plan-less, still a book.
        from contextlib import contextmanager

        from sqlalchemy.orm import sessionmaker

        factory = sessionmaker(bind=engine)

        @contextmanager
        def migrated_scope():
            db = factory()
            try:
                yield db
                db.commit()
            finally:
                db.close()

        books = BookManager(session_factory=migrated_scope)
        assert books.get_book(str(legacy)).metadata.title == "Legacy"
        assert books.get_plan(str(legacy)) is None
        assert books.save_plan(str(legacy), DEFAULT_PLAN)
        assert books.get_plan(str(legacy)) == DEFAULT_PLAN

        command.downgrade(config, "009")
        with engine.connect() as conn:
            columns = {c["name"] for c in sa.inspect(conn).get_columns("books")}
            assert "distribution_plan" not in columns
            assert conn.execute(sa.text("SELECT title FROM books")).scalars().all() == ["Legacy"]
        engine.dispose()


# --------------------------------------------------------------------------
# EC-023 — the store/reload round-trip, both storage modes
# --------------------------------------------------------------------------


def _random_split(rng: random.Random) -> Split:
    e = rng.randint(0, 100)
    m = rng.randint(0, 100 - e)
    return Split(e, m, 100 - e - m)


def _corpus() -> list[tuple[DistributionPlan, bool]]:
    """Plans to store: prefilled ones (flag True) and hand-edited/split-changed ones."""
    rng = random.Random(20260922 + 120)
    cells = [(b, t) for b in BUCKETS for t in TIERS]
    corpus: list[tuple[DistributionPlan, bool]] = []
    # Boundaries: count 1, whole-book tiers, the default.
    for split in (Split(100, 0, 0), Split(0, 100, 0), Split(0, 0, 100), Split(34, 33, 33)):
        for count in (1, 2, 3, 150):
            corpus.append((prefill(count, split), True))
    for _ in range(150):
        corpus.append((prefill(rng.randint(1, 1000), _random_split(rng)), True))
    for _ in range(150):
        plan = prefill(rng.randint(1, 400), _random_split(rng))
        for bucket, tier in rng.sample(cells, rng.randint(1, 6)):
            plan = with_edited_cell(plan, bucket, tier, rng.randint(0, 90))
        if rng.random() < 0.5:
            plan = with_split(plan, _random_split(rng))
        corpus.append((plan, False))
    return corpus


@pytest.mark.parametrize("mode", MODES)
def test_PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan_StoreReloadRoundTrip(mode, scope) -> None:
    """EC-023 (INV-005) — PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, round-trip half.

    For every plan in the corpus, in this storage mode: the plan read back
    equals the plan saved — count, split, all 12 cells and the edited set —
    and a reloaded prefilled plan still satisfies EC-023 (12 non-negative int
    cells summing to the count, column totals equal to the general plan's tier
    counts as an independent oracle computes them, zero-share cells 0).
    """
    books = _manager(mode, scope)
    book_id = _new_book(books)
    corpus = _corpus()
    assert len(corpus) >= 300, "the corpus shrank"
    edited_seen = 0

    for plan, prefilled in corpus:
        assert books.save_plan(book_id, plan)
        reloaded = books.get_plan(book_id)

        assert reloaded == plan
        assert reloaded.edited == plan.edited
        edited_seen += bool(reloaded.edited)
        split = reloaded.split
        assert split.easy + split.medium + split.hard == 100
        flat = [v for row in reloaded.cells for v in row]
        assert len(flat) == 12 and all(isinstance(v, int) and v >= 0 for v in flat)
        if prefilled:
            expected = _oracle_apportion(reloaded.count, (split.easy, split.medium, split.hard), ties_to_later=True)
            assert sum(flat) == reloaded.count
            assert _columns(reloaded.cells) == expected
            for t in range(3):
                column = tuple(row[t] for row in reloaded.cells)
                assert column == _oracle_apportion(expected[t], tuple(r[t] for r in BOOK1_MATRIX))
            assert reloaded.cell(B15, H) == 0 and reloaded.cell(B30, E) == 0

    assert edited_seen >= 100, "hand-edited plans must be exercised"


def test_stored_document_names_cells_by_label_not_position() -> None:
    """Edited cells are stored as ("21-25", "hard"), so reordering BUCKETS/TIERS cannot move them."""
    document = plan_to_json(with_edited_cell(DEFAULT_PLAN, B25, H, 15))
    assert document["edited"] == [["21-25", "hard"]]
    assert LongestSideBucket("21-25") is B25 and Tier("hard") is H
