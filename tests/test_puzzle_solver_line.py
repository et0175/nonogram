"""CARD-439 — the line focus view: a big board on a phone solved one row or
column at a time, in big cells (owner request and ruling, 2026-11-12).

The view is a dialog over the player (``#puzzle-player-line``) that draws ONE
line of the board, split into at most two strips, with a mini board to choose
the line by. It holds no state of its own: every mark made in it is a stroke
recorded into the player's own history, so these tests read the result off the
BOARD (``td.player-cell`` and ``window.puzzlePlayer.getBoard()``) and the save,
never only off the view.

Browser tests only (pytest-playwright + Chromium, ADR-0038/R7), through
CARD-160's fixtures. Touch input is real: CDP ``Input.dispatchTouchEvent``.
A synthetic drag is sent as small steps with a pause at the end, as a finger
moves: Chromium reads an instantaneous swipe as a fling, and the tap after a
fling is spent stopping it — true of the board's own Region drag too, and not
something this view does.
"""

from __future__ import annotations

import pytest

from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)
from tests.test_player_public_mode import public_payload, serve  # noqa: F401 — serve is a fixture

U, F, E, M = "unknown", "filled", "empty", "maybe"

#: The three boards: a 30 x 30 (two strips of 15 both ways), a 25 wide x 20
#: high (rows 15 + 10, columns 10 + 10) and a 15 x 15 (no view offered).
BIG = _unique_grid(30, 30, seed=439)
WIDE = _unique_grid(25, 20, seed=4391)
SMALL = _unique_grid(15, 15, seed=4392)

PHONE = {"width": 390, "height": 844}
LANDSCAPE = {"width": 844, "height": 390}
DESKTOP = {"width": 1440, "height": 900}

#: solver.js's LONG_PRESS_MS, with room to spare.
LONG_PRESS_S = 0.6


def _context(browser, viewport):
    return browser.new_context(has_touch=True, viewport=viewport)


def _open_phone(browser, live, grid, viewport=PHONE):
    context = _context(browser, viewport)
    page = context.new_page()
    _open(page, live, live.store(grid), keep_opening_zoom=True)
    return context, page


def _line_button(page):
    return page.locator("[data-player-line-open]")


def _dialog(page):
    return page.locator("#puzzle-player-line")


def _open_line(page):
    _line_button(page).tap()
    page.wait_for_function("!document.getElementById('puzzle-player-line').hidden")


def _title(page) -> str:
    return page.locator("[data-player-line-title]").text_content()


def _strip_states(page) -> list[str]:
    return page.eval_on_selector_all(".player-line-cell", "els => els.map((e) => e.dataset.state)")


def _board_line(page, axis, index) -> list[str]:
    return page.evaluate(
        """([axis, index]) => {
          const b = window.puzzlePlayer.getBoard();
          const n = axis === 'row' ? b.width : b.height;
          return Array.from({length: n}, (_, k) => axis === 'row'
            ? b.cells[index * b.width + k] : b.cells[k * b.width + index]);
        }""",
        [axis, index],
    )


def _centre(page, selector):
    box = page.locator(selector).bounding_box()
    return {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}


def _cell(k: int) -> str:
    return f'.player-line-cell[data-index="{k}"]'


def _touch(cdp, kind, points=()):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": list(points)})


def _strip_drag(context, page, first: int, last: int) -> None:
    cdp = context.new_cdp_session(page)
    a, z = _centre(page, _cell(first)), _centre(page, _cell(last))
    _touch(cdp, "touchStart", [a])
    for step in range(1, 13):
        _touch(cdp, "touchMove", [{"x": a["x"] + (z["x"] - a["x"]) * step / 12,
                                   "y": a["y"] + (z["y"] - a["y"]) * step / 12}])
        page.wait_for_timeout(30)
    page.wait_for_timeout(150)
    _touch(cdp, "touchEnd")


def _long_press(context, page, k: int) -> None:
    cdp = context.new_cdp_session(page)
    _touch(cdp, "touchStart", [_centre(page, _cell(k))])
    page.wait_for_timeout(LONG_PRESS_S * 1000)
    _touch(cdp, "touchEnd")


def _saved_strokes(page) -> int:
    return page.evaluate(
        """() => {
          const key = Object.keys(localStorage).find((k) => k.startsWith('nonogram-player:'));
          return key ? JSON.parse(localStorage.getItem(key)).done.length : 0;
        }""")


@pytest.mark.browser
class TestSolverLine_ThePureHelpers:
    """lineStrips, crossingLine and lineOf, from the page's own module."""

    def test_the_split_and_the_pivot(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(SMALL))
        result = browser_page.evaluate(
            """async () => {
              const m = await import('/static/solver_state.js');
              const board = m.withCell(m.createBoard(3, 2), 1, 2, m.FILLED);
              let refused = 0;
              for (const bad of [0, 1.5, -3]) { try { m.lineStrips(bad); } catch { refused += 1; } }
              return {
                strips: [10, 15, 16, 20, 22, 25, 30].map((n) => [...m.lineStrips(n)]),
                refused,
                row: [...m.lineOf(board, 'row', 1)],
                column: [...m.lineOf(board, 'column', 2)],
                crossRow: m.crossingLine('row', 13, 17),
                crossColumn: m.crossingLine('column', 17, 13),
                position: [m.linePosition('row', 4, 9), m.linePosition('column', 4, 9)],
              };
            }""")
        assert result["strips"] == [[10], [15], [10, 6], [10, 10], [10, 12], [15, 10], [15, 15]]
        assert result["refused"] == 3
        assert result["row"] == [U, U, F] and result["column"] == [U, F]
        assert result["crossRow"] == {"axis": "column", "index": 17, "at": 13}
        assert result["crossColumn"] == {"axis": "row", "index": 13, "at": 17}
        assert result["position"] == [[4, 9], [9, 4]]


@pytest.mark.browser
class TestSolverLine_IsOfferedOnlyForABigBoardOnAPhone:
    """AC-1."""

    @pytest.mark.parametrize("viewport", [PHONE, LANDSCAPE], ids=["390x844", "844x390"])
    def test_a_big_board_on_a_phone_offers_it(self, browser, live, viewport) -> None:
        context, page = _open_phone(browser, live, BIG, viewport)
        try:
            assert _line_button(page).is_visible()
        finally:
            context.close()

    @pytest.mark.parametrize(("grid", "viewport"), [(BIG, DESKTOP), (SMALL, PHONE)],
                             ids=["30x30-desktop", "15x15-phone"])
    def test_elsewhere_it_is_not_drawn(self, browser, live, grid, viewport) -> None:
        context, page = _open_phone(browser, live, grid, viewport)
        try:
            assert not _line_button(page).is_visible()
            assert _dialog(page).is_hidden()
            if grid is SMALL:
                # Never offered, so never built: the page is the one it was.
                assert _dialog(page).count() == 0 and _line_button(page).count() == 0
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_OpensAtTheLastCellTouched:
    """AC-2 — and before any touch, row 1; Escape and Board both close it."""

    def test_row_one_then_the_touched_row(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            assert _title(page) == "Row 1 of 30"
            assert page.evaluate("document.activeElement.dataset.playerLineAction") == "close"
            page.keyboard.press("Escape")
            assert _dialog(page).is_hidden()

            page.locator(".player-board tbody tr").nth(13).locator("td.player-cell").nth(10).tap()
            _open_line(page)
            assert _title(page) == "Row 14 of 30"
            assert len(_strip_states(page)) == 30
            page.locator('[data-player-line-action="close"]').tap()
            assert _dialog(page).is_hidden()
            assert page.evaluate("document.activeElement.hasAttribute('data-player-line-open')")
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_MarksAreTheBoardsMarks:
    """AC-3."""

    def test_tap_repeat_tap_drag_and_undo(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            page.locator(_cell(3)).tap()                      # black
            assert _board_line(page, "row", 0)[3] == F
            page.locator(_cell(3)).tap()                      # repeat: white
            assert _board_line(page, "row", 0)[3] == E
            page.locator('[data-player-line-tool="maybe"]').tap()
            assert page.locator("#puzzle-player-tool-trigger").get_attribute("aria-label") == "Brush: Maybe"
            _strip_drag(context, page, 20, 24)                # across nothing but strip 2
            row = _board_line(page, "row", 0)
            assert row[20:25] == [M] * 5 and row[19] == U and row[25] == U
            assert _strip_states(page) == row
            assert _saved_strokes(page) == 3
            cells = page.locator(".player-board tbody tr").first.locator("td.player-cell")
            assert cells.nth(22).get_attribute("data-state") == M

            page.locator('[data-player-line-action="undo"]').tap()
            assert _board_line(page, "row", 0)[20:25] == [U] * 5
            assert _saved_strokes(page) == 2
        finally:
            context.close()

    def test_a_drag_crosses_from_one_strip_to_the_other(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            _strip_drag(context, page, 12, 17)
            assert _board_line(page, "row", 0)[12:18] == [F] * 6
            assert _saved_strokes(page) == 1
        finally:
            context.close()

    def test_the_arrows_and_the_mini_board_choose_the_line(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            assert page.locator('[data-player-line-action="prev"]').get_attribute("aria-disabled") == "true"
            page.locator('[data-player-line-action="next"]').tap()
            assert _title(page) == "Row 2 of 30"
            box = page.locator("[data-player-line-mini]").bounding_box()
            # The centre of row 21, column 6 of the map.
            page.touchscreen.tap(box["x"] + box["width"] * 5.5 / 30, box["y"] + box["height"] * 20.5 / 30)
            assert _title(page) == "Row 21 of 30"
            page.locator('[data-player-line-axis="column"]').tap()
            assert _title(page) == "Column 6 of 30"
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_TheLineIsSplitInTwo:
    """AC-4 — split, not scrolled, at a phone's width."""

    @pytest.mark.parametrize(("grid", "axis", "split"), [
        (BIG, "row", [15, 15]), (WIDE, "row", [15, 10]), (WIDE, "column", [10, 10]),
    ], ids=["30-row", "25-row", "20-column"])
    def test_the_strips_fit_the_phone(self, browser, live, grid, axis, split) -> None:
        context, page = _open_phone(browser, live, grid)
        try:
            _open_line(page)
            if axis == "column":
                page.locator('[data-player-line-axis="column"]').tap()
            strips = page.eval_on_selector_all(
                ".player-line-strip",
                "els => els.map((s) => ({n: s.children.length, right: s.getBoundingClientRect().right,"
                " cell: s.firstElementChild.getBoundingClientRect().width}))")
            assert [s["n"] for s in strips] == split
            assert all(s["right"] <= PHONE["width"] for s in strips)
            assert min(s["cell"] for s in strips) >= 22
            # One cell size for both strips.
            assert max(s["cell"] for s in strips) - min(s["cell"] for s in strips) < 1
            assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_ReadsLikeTheBoard:
    """CARD-441 — a settled number is ringed, not struck; two black cells
    either side of the heavy fifth rule stay two cells."""

    def test_ring_and_divider(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            row, k = next((r, k) for r, line in enumerate(BIG) for k in (5, 10, 20, 25)
                          if line[k - 1] and line[k])
            other = next(r for r in range(30) if r != row and any(BIG[r]))
            page.evaluate(
                """async ([grid, other, col]) => {
                  const m = await import('/static/solver_state.js');
                  window.puzzlePlayer.setBoard(m.withCell(m.boardOfGrid(grid), other, col, m.UNKNOWN));
                }""",
                [BIG, other, BIG[other].index(True)],
            )
            free = BIG[row].index(False)
            page.locator(".player-board tbody tr").nth(row).locator("td.player-cell").nth(free).tap()
            page.locator('[data-player-action="undo"]').tap()
            _open_line(page)
            assert _title(page) == f"Row {row + 1} of 30"
            nums = page.eval_on_selector_all(".player-line-num", """els => els.map((e) => {
              const s = getComputedStyle(e);
              return {circled: e.classList.contains('is-circled'), line: s.textDecorationLine,
                      ring: s.borderTopColor, radius: parseFloat(s.borderTopLeftRadius), h: e.offsetHeight};
            })""")
            ink = page.evaluate("getComputedStyle(document.querySelector('.player-line-cell[data-state=filled]')).backgroundColor")
            assert nums and all(n["circled"] for n in nums)
            assert all(n["line"] == "none" and n["ring"] == ink and n["radius"] >= n["h"] / 2 for n in nums)
            cell = page.eval_on_selector(_cell(k), """e => ({major: e.classList.contains('is-major'),
              state: e.dataset.state, bg: getComputedStyle(e).backgroundColor, shadow: getComputedStyle(e).boxShadow})""")
            assert cell["major"] and cell["state"] == F
            before = page.eval_on_selector(_cell(k - 1), "e => getComputedStyle(e).boxShadow")
            # A paper gap inside each black cell, either side of the ink rule.
            for shadow in (cell["shadow"], before):
                assert shadow != "none" and cell["bg"] not in shadow
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_ALongPressOpensTheCrossingLine:
    """AC-5."""

    def test_row_to_column_marks_nothing(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            page.locator(".player-board tbody tr").nth(13).locator("td.player-cell").nth(0).tap()
            page.locator('[data-player-action="undo"]').tap()
            _open_line(page)
            assert _title(page) == "Row 14 of 30"
            _long_press(context, page, 17)
            assert _title(page) == "Column 18 of 30"
            pivot = page.eval_on_selector_all(".player-line-cell.is-pivot", "els => els.map((e) => e.dataset.index)")
            assert pivot == ["13"]
            assert all(state == U for state in page.evaluate("window.puzzlePlayer.getBoard().cells"))
            _long_press(context, page, 13)
            assert _title(page) == "Row 14 of 30"
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_SolvingClosesTheView:
    """AC-6 — the solving stroke closes the view, and the button goes."""

    def test_the_last_cell(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            row = next(r for r, line in enumerate(BIG) if any(line))
            col = BIG[row].index(True)
            page.evaluate(
                """async ([grid, row, col]) => {
                  const m = await import('/static/solver_state.js');
                  let board = m.boardOfGrid(grid);
                  board = m.withCell(board, row, col, m.UNKNOWN);
                  window.puzzlePlayer.setBoard(board);
                }""",
                [BIG, row, col],
            )
            # A wrong tap elsewhere on that row, undone: Line then opens there.
            other = BIG[row].index(False)
            page.locator(".player-board tbody tr").nth(row).locator("td.player-cell").nth(other).tap()
            page.locator('[data-player-action="undo"]').tap()
            _open_line(page)
            assert _title(page) == f"Row {row + 1} of 30"
            page.locator('[data-player-line-tool="filled"]').tap()
            page.locator(_cell(col)).tap()
            page.wait_for_function("document.getElementById('puzzle-player-line').hidden")
            assert not _line_button(page).is_visible()
            assert page.locator("#puzzle-player-solved").is_visible()
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_ThePublicPlayerOffersItToo:
    """AC-7 — the public site runs this same player in public mode (no
    solution): the view is offered, marks the board and the mark is saved."""

    def test_a_mark_in_the_public_player(self, browser, serve) -> None:
        served = serve(public_payload(BIG))
        context = _context(browser, PHONE)
        page = context.new_page()
        try:
            page.goto(f"{served.url}/index.html")
            page.wait_for_function("window.puzzlePlayer !== undefined")
            _open_line(page)
            page.locator(_cell(29)).tap()
            assert _board_line(page, "row", 0)[29] == F
            assert _saved_strokes(page) == 1
            _long_press(context, page, 29)
            assert _title(page) == "Column 30 of 30"
        finally:
            context.close()
