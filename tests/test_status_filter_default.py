"""CARD-166 AC-3 / G-2 and CARD-180 — puzzle selection's status filter
(FR-036, IDEA-013, IDEA-088).

Step 2 of a book offers approved puzzles only, unless the URL names another
status. Before CARD-166 the default applied only when the ``status`` key was
ABSENT, so a hand-typed ``?status=`` switched the filter off and offered draft
and rejected puzzles too.

The fixture holds puzzles of all three review statuses on the default tab
(longest side <=15), so "approved only" is a real cut, not a vacuous one.
Expected ids come from the fixture's own bookkeeping — which ids it approved,
rejected or left as draft — never from the route or the store's filter.

CARD-180: the exact value ``?status=all`` offers every status (still only
puzzles in no book); any other unknown value still offers nothing.

Both stores: in-memory and SQLite (never a live database).
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

import pytest

from nonogram.clues import compute_clues
from tests.helpers.db import sqlite_session_scope
from tests.test_puzzle_solver_page import _build_app, _unique_grid

STORES = ("memory", "sqlite")

#: A tile the page offers carries its id in a hidden ``shown_ids`` field.
_SHOWN = re.compile(r'name="shown_ids" value="([^"]+)"')


@pytest.fixture(params=STORES)
def panel(request, tmp_path, monkeypatch):
    scope = sqlite_session_scope(tmp_path, "card-166.db") if request.param == "sqlite" else None
    return _build_app(request.param, scope, monkeypatch)


@pytest.fixture
def stocked(panel):
    """A book and two puzzles of each status, all on the <=15 tab.

    Returns ``(client, book_id, {status: {ids}})``.
    """
    return _stock(panel, measurable=False)


@pytest.fixture
def measurable(panel):
    """CARD-180: :func:`stocked`'s stock, but each puzzle stores its real
    clues, so its printed cell can be measured and the floor admits it —
    the add tests need puzzles that can actually join a book. Same shape
    otherwise: six puzzles, two per status, all on the <=15 tab."""
    return _stock(panel, measurable=True)


def _stock(panel, *, measurable):
    store = panel.puzzle_review_service
    by_status: dict[str, set[str]] = {"approved": set(), "draft": set(), "rejected": set()}
    for index, status in enumerate(["approved", "draft", "rejected"] * 2):
        grid = _unique_grid(10 + index, 10, seed=166 + index)
        rows, cols = compute_clues(grid) if measurable else ([], [])
        puzzle_id = store.add_puzzle(
            grid=grid,
            clues_rows=[list(clue) for clue in rows],
            clues_cols=[list(clue) for clue in cols],
            width=len(grid[0]),
            height=len(grid),
            theme="test",
            difficulty_score=10,
            difficulty_tier="easy",
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            batch_id=None,
            source_image=f"pic-{index}.png",
        )
        if status == "approved":
            assert store.approve_puzzle(puzzle_id)
        elif status == "rejected":
            assert store.reject_puzzle(puzzle_id)
        by_status[status].add(puzzle_id)
    book_id = panel.book_manager.create_book("Winter", "a book", "generic", "adults")
    return panel.test_client(), book_id, by_status


def _offered(client, url) -> set[str]:
    response = client.get(url)
    assert response.status_code == 200, response.status_code
    return set(_SHOWN.findall(response.get_data(as_text=True)))


class TestStatusFilter_EmptyValueKeepsTheApprovedDefault:
    """AC-3: ``?status=`` (empty) offers what the URL without the key offers —
    the approved puzzles, and only those."""

    def test_an_empty_status_offers_the_same_puzzles_as_no_status(self, stocked) -> None:
        client, book_id, by_status = stocked
        base = f"/book/{book_id}/select-puzzles"

        absent = _offered(client, base)
        empty = _offered(client, f"{base}?status=")

        assert absent == by_status["approved"]  # the default, and not vacuous:
        assert by_status["draft"] and by_status["rejected"]  # others exist
        assert empty == absent

    def test_an_empty_status_beside_another_query_key_is_the_default_too(self, stocked) -> None:
        client, book_id, by_status = stocked

        offered = _offered(client, f"/book/{book_id}/select-puzzles?bucket=%3C%3D15&status=")

        assert offered == by_status["approved"]


class TestStatusFilter_ExplicitValuesFilterAsBefore:
    """G-2: an explicit status still filters exactly as before CARD-166 — by
    equality with the puzzle's stored status."""

    @pytest.mark.parametrize("status", ["approved", "draft", "rejected"])
    def test_an_explicit_status_offers_exactly_its_puzzles(self, stocked, status) -> None:
        client, book_id, by_status = stocked

        offered = _offered(client, f"/book/{book_id}/select-puzzles?status={status}")

        assert offered == by_status[status]
        assert offered  # each status has puzzles, so equality is not vacuous


# --- CARD-180: ``?status=all`` lists every status --------------------------

_ALL = "status=all"

#: One tile's markup, from its opening tag up to the next tile (or the end).
_TILE = re.compile(r'(?s)<div class="puzzle-tile" data-puzzle-id="([^"]+)"(.*?)(?=<div class="puzzle-tile" |\Z)')
#: The "Status" info row inside one tile.
_STATUS_ROW = re.compile(
    r'(?s)<span class="info-label">Status</span>\s*<span class="info-value">([^<]*)</span>'
)


def _every(by_status) -> set[str]:
    return set().union(*by_status.values())


def _status_rows(client, url) -> dict[str, list[str]]:
    """Each rendered tile's id -> the values of its "Status" rows."""
    response = client.get(url)
    assert response.status_code == 200, response.status_code
    body = response.get_data(as_text=True)
    return {pid: _STATUS_ROW.findall(markup) for pid, markup in _TILE.findall(body)}


def _leave_in_book_without_a_book(store, puzzle_id) -> None:
    """Set a puzzle's status to ``in_book`` while leaving its ``book_id``
    empty — the pre-CARD-100 leftover the card's owner default is about. No
    public method produces that shape (``mark_in_book`` also sets a book), so
    the row is written directly, in whichever store the test runs on."""
    if store._session_factory is None:
        store.puzzles[puzzle_id]["status"] = "in_book"
        return
    import uuid

    from nonogram.db.models import Puzzle

    with store._session_factory() as db:
        row = db.query(Puzzle).filter(Puzzle.id == uuid.UUID(puzzle_id)).one()
        row.status = "in_book"


class TestStatusFilter_AllOffersEveryStatus:
    """AC-1: ``?status=all`` offers the draft, approved and rejected puzzles."""

    def test_all_offers_exactly_the_six_puzzles(self, measurable) -> None:
        client, book_id, by_status = measurable

        offered = _offered(client, f"/book/{book_id}/select-puzzles?{_ALL}")

        assert all(len(ids) == 2 for ids in by_status.values())  # not vacuous
        assert offered == _every(by_status)


class TestStatusFilter_AllStillHidesPuzzlesInABook:
    """AC-2: ``all`` widens the status, not the book filter."""

    def test_a_puzzle_already_in_the_book_is_not_offered(self, measurable) -> None:
        client, book_id, by_status = measurable
        in_book = sorted(by_status["approved"])[0]
        assert client.application.book_manager.add_puzzles_to_book(book_id, [in_book])

        url = f"/book/{book_id}/select-puzzles?{_ALL}"
        offered = _offered(client, url)

        assert offered == _every(by_status) - {in_book}
        assert len(offered) == 5
        # The tab's count comes from the store's own query, not from the
        # rendered tiles, so it shows the store itself left the book's
        # puzzle out — not only the route's per-row cross-check.
        assert "(5 available)" in client.get(url).get_data(as_text=True)


class TestStatusFilter_AllSurvivesTabSwitchAndApply:
    """AC-3: a tab switch, a page move and Apply land on a URL carrying
    ``status=all``, and that page offers every status."""

    _HIDDEN_STATUS = re.compile(r'<input type="hidden" name="status" value="([^"]*)">')

    @pytest.mark.parametrize(
        "control", [{"go_bucket": "<=15"}, {"go_offset": "0"}, {"go_filter": "1"}],
        ids=["tab-switch", "page-move", "apply"],
    )
    def test_the_redirect_carries_all(self, measurable, control) -> None:
        client, book_id, by_status = measurable
        page = client.get(f"/book/{book_id}/select-puzzles?{_ALL}").get_data(as_text=True)
        # The form posts back whatever the page's hidden field holds.
        (carried,) = self._HIDDEN_STATUS.findall(page)

        response = client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "<=15", "status": carried, "limit": "50", "offset": "0", **control},
        )

        assert response.status_code == 302, response.status_code
        location = response.headers["Location"]
        assert parse_qs(urlsplit(location).query).get("status") == ["all"]
        assert _offered(client, location) == _every(by_status)


class TestStatusFilter_AllTilesCanBeAddedAndKeepTheirStatus:
    """AC-4: a draft and a rejected tile ticked under ``all`` join the book,
    and each keeps its own curation status (ADR-0033/R1)."""

    def test_draft_and_rejected_join_and_keep_their_status(self, measurable) -> None:
        client, book_id, by_status = measurable
        draft = sorted(by_status["draft"])[0]
        rejected = sorted(by_status["rejected"])[0]
        shown = sorted(_offered(client, f"/book/{book_id}/select-puzzles?{_ALL}"))
        assert {draft, rejected} <= set(shown)

        response = client.post(
            f"/book/{book_id}/select-puzzles",
            data={
                "bucket": "<=15",
                "status": "all",
                "limit": "50",
                "offset": "0",
                "shown_ids": shown,
                "puzzle_ids": [draft, rejected],
            },
        )

        assert response.status_code == 302, response.status_code
        app = client.application
        assert set(app.book_manager.get_book(book_id).puzzle_ids) == {draft, rejected}
        store = app.puzzle_review_service
        assert store.get_puzzle(draft)["status"] == "draft"
        assert store.get_puzzle(rejected)["status"] == "rejected"


class TestStatusFilter_NonApprovedTilesNameTheirStatus:
    """AC-5: under ``all`` every draft or rejected tile has one "Status" row
    naming its status and no approved tile has one; the default page shows
    no "Status" row at all."""

    def test_rows_under_all(self, measurable) -> None:
        client, book_id, by_status = measurable

        rows = _status_rows(client, f"/book/{book_id}/select-puzzles?{_ALL}")

        assert set(rows) == _every(by_status)
        for status, ids in by_status.items():
            for pid in ids:
                assert rows[pid] == ([] if status == "approved" else [status]), (status, pid)

    def test_no_row_on_the_default_page(self, measurable) -> None:
        client, book_id, by_status = measurable

        rows = _status_rows(client, f"/book/{book_id}/select-puzzles")

        assert set(rows) == by_status["approved"]
        assert all(found == [] for found in rows.values())

    def test_in_book_reads_as_two_words(self, measurable) -> None:
        """Owner default: a leftover ``in_book`` status with no book id is
        shown like any status, as "in book"."""
        client, book_id, by_status = measurable
        store = client.application.puzzle_review_service
        draft = sorted(by_status["draft"])[0]
        _leave_in_book_without_a_book(store, draft)
        assert store.get_puzzle(draft)["status"] == "in_book"
        assert store.get_puzzle(draft).get("book_id") is None

        rows = _status_rows(client, f"/book/{book_id}/select-puzzles?{_ALL}")

        assert rows[draft] == ["in book"]


class TestStatusFilter_AllEmptyTabDoesNotSayApproved:
    """AC-6: an empty tab under ``all`` does not say "approved"; at the
    default it still does."""

    _EMPTY = re.compile(r'(?s)<p class="empty">(.*?)</p>')

    def _empty_text(self, client, url) -> str:
        response = client.get(url)
        assert response.status_code == 200, response.status_code
        found = self._EMPTY.findall(response.get_data(as_text=True))
        assert len(found) == 1, found
        return found[0]

    def test_all_copy_is_neutral_and_default_copy_is_kept(self, measurable) -> None:
        client, book_id, _ = measurable
        base = f"/book/{book_id}/select-puzzles?bucket=26-30"  # the stock has none there

        under_all = self._empty_text(client, f"{base}&{_ALL}")
        default = self._empty_text(client, base)

        assert "approved" not in under_all
        assert under_all == "No puzzles with a longest side of 26-30 match these filters. Try another tab."
        assert "No approved puzzles with a longest side of 26-30" in default


class TestStatusFilter_UnknownValueStillMatchesNothing:
    """AC-7 (was CARD-166's pinned ``all`` test): only the exact value ``all``
    is special. Any other value is matched literally and offers nothing, so
    an unknown status never quietly widens into the default or into all."""

    @pytest.mark.parametrize("value", ["bogus", "ALL", "All", "all-of-them", "%20all"])
    def test_an_unknown_value_offers_nothing(self, measurable, value) -> None:
        client, book_id, by_status = measurable
        assert _every(by_status)  # puzzles exist, so the empty set is a real cut

        assert _offered(client, f"/book/{book_id}/select-puzzles?status={value}") == set()
