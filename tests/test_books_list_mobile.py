"""CARD-175 AC-3/AC-4 — /books folds a row's off-plan hints on a phone.

At 390 px a book with ten off-plan cells stacked ten chips in the narrow
"Against plan" column and every row grew to about 650 px (CARD-158's
renders). The hints now sit in a native ``<details class="plan-hints">``:
closed at phone width, so the row shows the tier split and one summary line;
forced open with the summary hidden above 820 px.

Open or closed is a layout fact, so this is a real browser test
(pytest-playwright + Chromium, ADR-0038/R7). Only Chromium is exercised. The
fixtures that refuse loudly when Playwright or Chromium is missing
(ADR-0038/R8) are imported from ``tests/test_puzzle_solver_page.py``, as
``tests/test_book_setup_print_mobile.py`` does, rather than copied.

"Visible" is Playwright's own ``is_visible()`` (a non-empty box and not
``visibility: hidden``); a chip inside a closed disclosure has no box.
"""

from __future__ import annotations

import threading

import pytest

from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_plan import DistributionPlan, Split
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import sqlite_session_scope
from tests.test_puzzle_solver_page import (  # noqa: F401
    _build_app,
    _expected_clues,
    _unique_grid,
    browser_page,
    browser_type,
)

PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1440, "height": 900}

#: The closed row's height bound at 390 px (AC-3). Measured in Chromium on
#: this card's build with this fixture: the closed row is about 176 px tall
#: (the actions column alone is 148 px); the same row was about 667 px before.
ROW_HEIGHT_MAX = 220

#: A plan of 150 at 40/40/20 — the one tests/test_books_list_plan_stats.py
#: calls PLAN_150. Ten of its twelve cells are non-zero.
PLAN_150 = DistributionPlan(
    count=150,
    split=Split(40, 40, 20),
    cells=((20, 7, 0), (30, 27, 6), (10, 20, 12), (0, 6, 12)),
)

#: Four easy 15 x 15 members leave every non-zero cell short: ten hints.
MEMBERS = 4
HINTS = 10

_PAGE_WIDTH = """() => ({
  scrollWidth: document.documentElement.scrollWidth,
  innerWidth: window.innerWidth,
})"""


def _member(store, grid) -> str:
    """One stored easy puzzle whose clues are filled in: the 4.8 mm floor
    measures a member's cell from its clues, and refuses a puzzle without."""
    rows, cols = _expected_clues(grid)
    return store.add_puzzle(
        grid=grid,
        clues_rows=rows,
        clues_cols=cols,
        width=len(grid[0]),
        height=len(grid),
        theme="christmas",
        difficulty_score=20,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=None,
        source_image="tree.png",
    )


@pytest.fixture
def live_books(tmp_path, monkeypatch):
    """The real panel over SQLite on loopback, holding one ten-hint book."""
    from werkzeug.serving import make_server

    scope = sqlite_session_scope(tmp_path, "card-175-live.db")
    app = _build_app("sqlite", scope, monkeypatch)
    store = PuzzleReviewService(session_factory=scope)
    books = BookManager(session_factory=scope, puzzle_store=store)
    book_id = books.create_book(
        "Christmas Nonograms for Adults", "A winter book.", "christmas", "adults"
    )
    ids = [_member(store, _unique_grid(15, 15, seed=175 + n)) for n in range(MEMBERS)]
    assert books.add_puzzles_to_book(book_id, ids)
    assert len(books.get_book(book_id).puzzle_ids) == MEMBERS
    assert books.save_plan(book_id, PLAN_150)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/books"
    finally:
        server.shutdown()
        thread.join()


def _open_at(page, url, viewport):
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.set_viewport_size(viewport)
    page.goto(url)
    return errors


def _chips(page):
    chips = page.locator("tbody tr .plan-hints [data-off-plan='true']")
    assert chips.count() == HINTS, chips.count()
    return chips


def _visible_chips(page) -> int:
    chips = _chips(page)
    return sum(1 for index in range(HINTS) if chips.nth(index).is_visible())


@pytest.mark.browser
class TestBooksListMobile_RowIsCompactAtPhoneWidth:
    """AC-3: at 390 x 844 the row is the split plus one summary line; a click
    on the summary shows every chip."""

    @pytest.fixture
    def phone_page(self, browser_page, live_books):  # noqa: F811
        errors = _open_at(browser_page, live_books, PHONE)
        yield browser_page
        assert errors == [], errors  # the page renders with a clean console

    def test_the_summary_shows_and_no_chip_does(self, phone_page) -> None:
        summary = phone_page.locator("tbody tr .plan-hints > summary")
        assert summary.is_visible()
        assert summary.inner_text().strip() == f"{HINTS} cells off plan"
        assert _visible_chips(phone_page) == 0

    def test_the_closed_summary_is_one_line(self, phone_page) -> None:
        # The closed summary does not wrap ("10 cells off / plan" was F-003):
        # a Range over its text yields one rect per line the text occupies,
        # the technique the chip check below uses.
        lines = phone_page.evaluate(
            """() => {
                 const summary = document.querySelector('tbody tr .plan-hints > summary');
                 const range = document.createRange();
                 range.selectNodeContents(summary);
                 return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
               }"""
        )
        assert lines == 1, lines

    def test_the_closed_row_is_short(self, phone_page) -> None:
        height = phone_page.locator("tbody tr").first.bounding_box()["height"]
        assert height <= ROW_HEIGHT_MAX, height

    def test_the_page_does_not_scroll_sideways(self, phone_page) -> None:
        width = phone_page.evaluate(_PAGE_WIDTH)
        assert width["innerWidth"] == PHONE["width"]
        assert width["scrollWidth"] <= width["innerWidth"], width

    def test_a_click_on_the_summary_shows_every_chip(self, phone_page) -> None:
        phone_page.locator("tbody tr .plan-hints > summary").click()

        assert _visible_chips(phone_page) == HINTS
        # No chip breaks mid-text (white-space: nowrap): its text lays out as
        # one line box. A chip is a flex item, so the count comes from a Range
        # over its text, which yields one rect per line the text occupies.
        lines = phone_page.evaluate(
            """() => [...document.querySelectorAll('.plan-hints [data-off-plan="true"]')]
                 .map((chip) => {
                   const range = document.createRange();
                   range.selectNodeContents(chip);
                   return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
                 })"""
        )
        assert lines == [1] * HINTS, lines


@pytest.mark.browser
class TestBooksListMobile_DesktopShowsEveryHint:
    """AC-4: at 1440 x 900 the summary is hidden and all ten chips show
    without a click — the desktop row as it was before CARD-175."""

    @pytest.fixture
    def desktop_page(self, browser_page, live_books):  # noqa: F811
        errors = _open_at(browser_page, live_books, DESKTOP)
        yield browser_page
        assert errors == [], errors

    def test_the_summary_is_hidden(self, desktop_page) -> None:
        assert not desktop_page.locator("tbody tr .plan-hints > summary").is_visible()

    def test_every_chip_shows_without_a_click(self, desktop_page) -> None:
        assert _visible_chips(desktop_page) == HINTS
