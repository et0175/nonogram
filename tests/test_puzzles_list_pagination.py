"""Admin puzzle list pagination: First, Previous, a window of up to 5 page
numbers around the current page, Next and Last, with the list's filters kept
on every link."""

import re

import pytest

from nonogram.admin.app import _page_window


def _numbers(window):
    return [n for n, _ in window["numbers"]]


class TestPageWindow:
    def test_the_window_is_centred_on_the_current_page(self):
        window = _page_window(total_count=30, limit=2, offset=14)  # page 8 of 15
        assert (window["current"], window["pages"]) == (8, 15)
        assert _numbers(window) == [6, 7, 8, 9, 10]
        assert window["numbers"][0] == (6, 10)

    def test_it_is_clamped_at_the_start(self):
        window = _page_window(30, 2, 0)
        assert window["current"] == 1
        assert _numbers(window) == [1, 2, 3, 4, 5]

    def test_it_is_clamped_at_the_end(self):
        window = _page_window(30, 2, 28)
        assert window["current"] == 15
        assert _numbers(window) == [11, 12, 13, 14, 15]

    def test_fewer_pages_than_the_window(self):
        assert _numbers(_page_window(5, 2, 2)) == [1, 2, 3]

    def test_first_previous_next_last_offsets(self):
        window = _page_window(30, 2, 14)
        assert (
            window["first_offset"],
            window["prev_offset"],
            window["next_offset"],
            window["last_offset"],
        ) == (0, 12, 16, 28)

    def test_a_partial_last_page_counts(self):
        assert _page_window(31, 2, 0)["pages"] == 16

    def test_an_empty_list_is_one_page(self):
        window = _page_window(0, 25, 0)
        assert (window["pages"], _numbers(window)) == (1, [1])

    def test_an_unaligned_offset_lands_on_its_page(self):
        assert _page_window(30, 2, 15)["current"] == 8

    def test_an_offset_past_the_end_clamps_to_the_last_page(self):
        assert _page_window(30, 2, 100)["current"] == 15


# --- the rendered /puzzles page ----------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app


def _seed(app, count):
    store = app.batch_generator.puzzle_review_service
    grid = [[True] * 10 for _ in range(10)]
    clues = [[10] for _ in range(10)]
    for i in range(count):
        store.add_puzzle(
            grid=grid,
            clues_rows=clues,
            clues_cols=clues,
            width=10,
            height=10,
            theme="test",
            difficulty_score=10,
            difficulty_tier="Easy",
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            source_image=f"p{i}.png",
        )


def _link_offset(body, aria_label):
    """The offset an enabled link with ``aria_label`` points at, or None if
    that link is rendered disabled (no href)."""
    match = re.search(
        rf'<a class="page-link" href="\?[^"]*offset=(\d+)" aria-label="{aria_label}"', body
    )
    return int(match.group(1)) if match else None


def _page_numbers(body):
    nav = body[body.index('aria-label="Pagination"'):]
    return [int(n) for n in re.findall(r'class="page-link"[^>]*>(\d+)<', nav)]


def test_a_middle_page_shows_five_numbers_and_all_four_jumps(admin_app):
    _seed(admin_app, 30)
    body = admin_app.test_client().get("/puzzles?limit=2&offset=14").get_data(as_text=True)

    assert _page_numbers(body) == [6, 7, 8, 9, 10]
    assert '<li class="page-item active" aria-current="page"><span class="page-link">8</span>' in body
    assert "Page 8 of 15" in body
    assert _link_offset(body, "First page") == 0
    assert _link_offset(body, "Previous page") == 12
    assert _link_offset(body, "Next page") == 16
    assert _link_offset(body, "Last page") == 28
    assert _link_offset(body, "Page 6") == 10
    # The list's own filters survive the jump.
    assert re.search(r'href="\?[^"]*limit=2[^"]*offset=28" aria-label="Last page"', body)


def test_the_first_page_disables_first_and_previous(admin_app):
    _seed(admin_app, 30)
    body = admin_app.test_client().get("/puzzles?limit=2").get_data(as_text=True)

    assert _page_numbers(body) == [1, 2, 3, 4, 5]
    assert _link_offset(body, "First page") is None
    assert _link_offset(body, "Previous page") is None
    assert _link_offset(body, "Last page") == 28


def test_the_last_page_disables_next_and_last(admin_app):
    _seed(admin_app, 30)
    body = admin_app.test_client().get("/puzzles?limit=2&offset=28").get_data(as_text=True)

    assert _page_numbers(body) == [11, 12, 13, 14, 15]
    assert _link_offset(body, "Next page") is None
    assert _link_offset(body, "Last page") is None
    assert _link_offset(body, "First page") == 0


def test_a_single_page_shows_no_pagination(admin_app):
    _seed(admin_app, 3)
    body = admin_app.test_client().get("/puzzles").get_data(as_text=True)

    assert 'aria-label="Pagination"' not in body
