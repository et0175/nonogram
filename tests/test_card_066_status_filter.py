"""CARD-066: the puzzle review page filters by status.

AC-1 — ?status=draft|approved|rejected|in_book lists only those puzzles; no
       status lists every status, as before.
AC-2 — the rendered form marks the current status, and nothing when unset.
AC-3 — the pagination links keep the status filter.
AC-4 — an unknown status does not 500: it is reported and ignored.
AC-5 — status combines with the other filters.
"""

import re

import pytest

import nonogram.admin.image_manager as image_manager_module

STATUSES = ("draft", "approved", "rejected", "in_book")


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _add(app, status="draft", width=10, height=10):
    """Store one puzzle and move it to ``status``."""
    store = app.puzzle_review_service
    grid = [[True] * width for _ in range(height)]
    clues_rows = [[width] for _ in range(height)]
    clues_cols = [[height] for _ in range(width)]
    puzzle_id = store.add_puzzle(
        grid=grid,
        clues_rows=clues_rows,
        clues_cols=clues_cols,
        width=width,
        height=height,
        theme="test",
        difficulty_score=10,
        difficulty_tier="Easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        source_image=f"{status}_{width}x{height}.png",
    )
    if status == "approved":
        assert store.approve_puzzle(puzzle_id)
    elif status == "rejected":
        assert store.reject_puzzle(puzzle_id)
    return puzzle_id


def _statuses(body: str) -> list:
    """The status badges rendered in the table, in order."""
    return re.findall(r'class="badge"[^>]*>\s*(draft|approved|rejected|in_book)\s*<', body)


def _status_select(body: str) -> str:
    match = re.search(r'<select[^>]*id="status".*?</select>', body, re.DOTALL)
    assert match, "no status <select> in the filter form"
    return match.group(0)


@pytest.mark.parametrize("wanted", ["draft", "approved", "rejected"])
def test_ac1_only_the_wanted_status_is_listed(admin_app, wanted):
    for status in ("draft", "approved", "rejected"):
        _add(admin_app, status)

    body = admin_app.test_client().get(f"/puzzles?status={wanted}").get_data(as_text=True)

    assert _statuses(body) == [wanted]
    assert "Puzzles (1 total)" in body


def test_ac1_without_a_status_every_puzzle_is_listed(admin_app):
    for status in ("draft", "approved", "rejected"):
        _add(admin_app, status)

    body = admin_app.test_client().get("/puzzles").get_data(as_text=True)

    assert sorted(_statuses(body)) == ["approved", "draft", "rejected"]
    assert "Puzzles (3 total)" in body


def test_ac1_in_book_puzzles_can_be_listed(admin_app):
    """The fourth status: reachable only through `mark_in_book`, and easy to
    leave untested because nothing in this page sets it."""
    store = admin_app.puzzle_review_service
    puzzle_id = _add(admin_app, "approved")
    assert store.mark_in_book(puzzle_id, "book-1")
    _add(admin_app, "draft")

    body = admin_app.test_client().get("/puzzles?status=in_book").get_data(as_text=True)

    assert _statuses(body) == ["in_book"]
    assert "Puzzles (1 total)" in body


def test_ac2_the_options_come_from_the_status_enum(admin_app, monkeypatch):
    """Hardcoding today's four statuses in the template passes every other
    test here. This one fails, because the list is the enum's: a status added
    to `PuzzleStatus` has to appear without touching the page."""
    import nonogram.admin.app as app_module

    monkeypatch.setattr(app_module, "_PUZZLE_STATUSES", tuple(STATUSES) + ("archived",))

    select = _status_select(admin_app.test_client().get("/puzzles").get_data(as_text=True))

    assert '<option value="archived"' in select
    assert select.count("<option") == len(STATUSES) + 2  # Any, the four, archived


def test_ac2_the_route_takes_its_statuses_from_the_enum():
    """The test above pins template ← route. This pins route ← enum.

    It compares values, so replacing the derivation with a literal tuple of
    today's four statuses still passes — but that is behaviour-identical
    today. The failure this guards is the one that matters: a status added
    to `PuzzleStatus` while the page keeps the old list makes this fail.
    """
    from nonogram.admin.app import _PUZZLE_STATUSES
    from nonogram.admin.puzzle_review import PuzzleStatus

    assert _PUZZLE_STATUSES == tuple(status.value for status in PuzzleStatus)
    assert set(STATUSES) == set(_PUZZLE_STATUSES), "this file's own list is stale"


def test_ac2_the_form_offers_every_status_and_marks_the_current_one(admin_app):
    _add(admin_app, "approved")
    client = admin_app.test_client()

    chosen = _status_select(client.get("/puzzles?status=approved").get_data(as_text=True))
    assert '<option value="approved" selected>' in chosen
    for status in STATUSES:
        assert f'value="{status}"' in chosen

    unset = _status_select(client.get("/puzzles").get_data(as_text=True))
    assert "selected" not in unset


def test_ac3_pagination_keeps_the_status(admin_app):
    for _ in range(3):
        _add(admin_app, "approved")
    _add(admin_app, "draft")

    body = admin_app.test_client().get("/puzzles?status=approved&limit=1").get_data(as_text=True)

    assert "Page 1 of 3" in body  # the draft one is filtered out
    nav = body[body.index('aria-label="Pagination"') :]
    hrefs = re.findall(r'href="\?([^"]*)"', nav)
    assert hrefs, "no pagination links rendered"
    assert all("status=approved" in href for href in hrefs), hrefs


def test_ac4_an_unknown_status_is_reported_and_ignored(admin_app):
    _add(admin_app, "draft")
    _add(admin_app, "approved")

    response = admin_app.test_client().get("/puzzles?status=nonsense")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Unknown status" in body
    assert sorted(_statuses(body)) == ["approved", "draft"]
    assert "selected" not in _status_select(body)


def test_ac4_the_filter_error_page_still_offers_every_status(admin_app):
    """The route's `except ValueError` branch re-renders this page. Without
    `statuses` there, the select degrades silently to "Any" only — a page
    that still returns 200 and quietly loses the filter."""
    _add(admin_app, "approved")

    response = admin_app.test_client().get("/puzzles?size=999")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Filter error" in body
    select = _status_select(body)
    for status in STATUSES:
        assert f'value="{status}"' in select


def test_ac5_status_combines_with_the_size_filter(admin_app):
    _add(admin_app, "approved", width=10, height=10)
    _add(admin_app, "approved", width=20, height=20)
    _add(admin_app, "draft", width=20, height=20)

    body = admin_app.test_client().get("/puzzles?status=approved&size=20").get_data(as_text=True)

    assert _statuses(body) == ["approved"]
    assert "Puzzles (1 total)" in body
    assert "20×20" in body
