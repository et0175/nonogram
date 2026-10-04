"""CARD-166 AC-3 / G-2 — puzzle selection's status filter (FR-036, IDEA-013).

Step 2 of a book offers approved puzzles only, unless the URL names another
status. Before CARD-166 the default applied only when the ``status`` key was
ABSENT, so a hand-typed ``?status=`` switched the filter off and offered draft
and rejected puzzles too.

The fixture holds puzzles of all three review statuses on the default tab
(longest side <=15), so "approved only" is a real cut, not a vacuous one.
Expected ids come from the fixture's own bookkeeping — which ids it approved,
rejected or left as draft — never from the route or the store's filter.

Both stores: in-memory and SQLite (never a live database).
"""

from __future__ import annotations

import re

import pytest

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
    store = panel.puzzle_review_service
    by_status: dict[str, set[str]] = {"approved": set(), "draft": set(), "rejected": set()}
    for index, status in enumerate(["approved", "draft", "rejected"] * 2):
        grid = _unique_grid(10 + index, 10, seed=166 + index)
        puzzle_id = store.add_puzzle(
            grid=grid,
            clues_rows=[],
            clues_cols=[],
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

    def test_all_is_matched_literally_as_before(self, stocked) -> None:
        """``all`` is not a puzzle status and the route never special-cased
        it, so — as before this card — it matches no puzzle. Pinned so the
        empty-value rule cannot quietly widen into "unknown means default"."""
        client, book_id, _ = stocked

        assert _offered(client, f"/book/{book_id}/select-puzzles?status=all") == set()
