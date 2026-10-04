"""CARD-166 AC-2 — Print setup's plan inputs on a phone (FR-030, IDEA-051).

At a 390 px viewport the plan's number inputs clipped "20" to "2(" (seen in
CARD-159's renders). Only a browser lays the page out, so this is a real
Chromium test (pytest-playwright, ADR-0038/R7), reusing the player's loud
refusal when Playwright or Chromium is missing (ADR-0038/R8): those fixtures
are imported from ``tests/test_puzzle_solver_page.py`` rather than copied.

The measurement is the browser's own: an input whose text is wider than its
box has ``scrollWidth > clientWidth``; a page that scrolls sideways has
``document.documentElement.scrollWidth > window.innerWidth``.
"""

from __future__ import annotations

import threading

import pytest

from nonogram.admin.book_manager import BookManager
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import sqlite_session_scope
from tests.test_puzzle_solver_page import _build_app, browser_page, browser_type  # noqa: F401

PHONE = {"width": 390, "height": 844}
THREE_DIGITS = "100"

#: Every plan number input: the count, the three shares and the matrix cells.
_PLAN_INPUTS = "#plan_count, input[id^='split_'], table input[id^='cell_']"

_MEASURE = """(selector) => [...document.querySelectorAll(selector)].map((input) => ({
  id: input.id,
  value: input.value,
  scrollWidth: input.scrollWidth,
  clientWidth: input.clientWidth,
}))"""

_PAGE_WIDTH = """() => ({
  scrollWidth: document.documentElement.scrollWidth,
  innerWidth: window.innerWidth,
})"""


@pytest.fixture
def live_book(tmp_path, monkeypatch):
    """The real panel over SQLite on loopback, holding one book (default plan)."""
    from werkzeug.serving import make_server

    scope = sqlite_session_scope(tmp_path, "card-166-live.db")
    app = _build_app("sqlite", scope, monkeypatch)
    books = BookManager(session_factory=scope, puzzle_store=PuzzleReviewService(session_factory=scope))
    book_id = books.create_book("Winter", "Twenty winter pictures.", "generic", "adults")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/book/{book_id}/setup-print"
    finally:
        server.shutdown()
        thread.join()


@pytest.mark.browser
class TestPrintSetupMobile_PlanInputsShowThreeDigits:
    """AC-2: at 390 px every plan number input shows "100" in full, and the
    page does not scroll sideways."""

    @pytest.fixture
    def phone_page(self, browser_page, live_book):  # noqa: F811
        errors: list[str] = []
        browser_page.on("pageerror", lambda exc: errors.append(str(exc)))
        browser_page.on(
            "console", lambda msg: errors.append(msg.text) if msg.type == "error" else None
        )
        browser_page.set_viewport_size(PHONE)
        browser_page.goto(live_book)
        yield browser_page
        assert errors == [], errors  # the screen renders with a clean console

    def _fill_three_digits(self, page) -> list[dict]:
        inputs = page.locator(_PLAN_INPUTS)
        count = inputs.count()
        # 1 count + 3 shares + 4 buckets x 3 tiers: the selector found them all.
        assert count == 16, count
        for index in range(count):
            inputs.nth(index).fill(THREE_DIGITS)
        return page.evaluate(_MEASURE, _PLAN_INPUTS)

    def test_every_plan_input_shows_a_three_digit_value_in_full(self, phone_page) -> None:
        measured = self._fill_three_digits(phone_page)

        assert all(m["value"] == THREE_DIGITS for m in measured)
        clipped = [m for m in measured if m["scrollWidth"] > m["clientWidth"]]
        assert clipped == [], clipped

    def test_the_page_does_not_scroll_sideways(self, phone_page) -> None:
        self._fill_three_digits(phone_page)

        width = phone_page.evaluate(_PAGE_WIDTH)
        assert width["innerWidth"] == PHONE["width"]
        assert width["scrollWidth"] <= width["innerWidth"], width
