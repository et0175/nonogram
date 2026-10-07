"""CARD-182 — the puzzle player's cells are a usable tap target on a phone (FR-044).

Below the shell's 820 px breakpoint ``admin.css`` raises the player's cell
floor (``--player-cell-min``) from 14 px to 24 px; the clamp, its 28 px cap and
everything above 820 px are unchanged. A board wider than the stage scrolls
inside ``.player-stage``; the page never scrolls sideways. Cells keep
``touch-action: none`` (a touch drag marks); every clue box (column, row,
corner) keeps the default ``auto``, and a swipe that starts on the column-clue
band (a column clue or the corner) pans the board.

Browser tests only (pytest-playwright + Chromium, ADR-0038/R7), refusing loudly
when Chromium is absent (ADR-0038/R8) through CARD-160's fixtures, imported
below. Touch input is real: CDP ``Input.dispatchTouchEvent`` drags and taps,
and Chromium's own touch scroll gesture for the clue swipe.
"""

from __future__ import annotations

import pytest

from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)

U, F, E = "unknown", "filled", "empty"

#: The 24 px phone floor and the unchanged 28 px cap.
FLOOR, CAP = 24, 28


def _deep_row_clues(width, height, seed):
    """A uniquely solvable grid whose first row has the deepest clue a tight
    row of ``width`` can have: (width + 1) // 2 runs (15 for 30 wide)."""
    grid = _unique_grid(width, height, seed=seed)
    runs = (width + 1) // 2
    row = [True] * (width - 2 * (runs - 1)) + [False, True] * (runs - 1)
    assert len(row) == width and row[0] and row[-1]
    grid[0] = row
    return grid


#: The three boards of AC-1: a 15 x 15, a 25 x 15 (25 wide, 15 high) and a
#: 30 x 30 with a 15-number row clue.
GRIDS = {
    "15x15": _unique_grid(15, 15, seed=182),
    "25x15": _unique_grid(25, 15, seed=1825),
    "30x30": _deep_row_clues(30, 30, seed=1830),
}
BIG = GRIDS["30x30"]
BIG_SIDE = 30

#: AC-4: td.player-cell width at 1440 x 900 for each board, measured on main
#: (admin.css unchanged, commit 2e40c96) before this card's rule was added,
#: rounded to 0.001 px (the 30 x 30 measured 16.796875).
DESKTOP_CELL = {"15x15": 28.0, "25x15": 28.0, "30x30": 16.797}


_CELLS = """() => [...document.querySelectorAll('td.player-cell')].map((td) => {
  const r = td.getBoundingClientRect();
  return [r.width, r.height];
})"""

_FIT = """() => {
  const stage = document.querySelector('.player-stage');
  return { pageWidth: document.scrollingElement.scrollWidth, viewport: innerWidth,
           stageScrollWidth: stage.scrollWidth, stageClientWidth: stage.clientWidth };
}"""


def _states(page):
    return page.evaluate("() => [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state)")


def _changed(states, width=BIG_SIDE):
    return {(i // width, i % width): s for i, s in enumerate(states) if s != U}


def _cell(page, r, c):
    return page.locator(f'td.player-cell[data-row="{r}"][data-col="{c}"]')


def _stage_scroll_left(page):
    return page.evaluate("document.querySelector('.player-stage').scrollLeft")


def _phone(browser):
    return browser.new_context(has_touch=True, viewport={"width": 390, "height": 844})


def _bring_row_to_middle(page, row):
    """Scroll the page vertically (never the stage) so ``row`` sits mid-screen.
    Instant: Bootstrap's reboot makes the root scroll smooth."""
    page.evaluate(
        """(row) => {
          const top = document.querySelector(`td.player-cell[data-row="${row}"]`).getBoundingClientRect().top;
          window.scrollBy({ top: top - innerHeight / 2, behavior: 'instant' });
        }""",
        row,
    )


def _visible_centre(page, r, c):
    """The cell's centre, asserting the whole cell is inside the stage's
    visible box and the viewport (so a touch there lands on it, not beside)."""
    seen = page.evaluate(
        """([r, c]) => {
          const cell = document.querySelector(`td.player-cell[data-row="${r}"][data-col="${c}"]`).getBoundingClientRect();
          const stage = document.querySelector('.player-stage').getBoundingClientRect();
          return { cell: [cell.left, cell.top, cell.right, cell.bottom],
                   stage: [stage.left, stage.top, stage.right, stage.bottom],
                   viewport: [innerWidth, innerHeight] };
        }""",
        [r, c],
    )
    left, top, right, bottom = seen["cell"]
    s_left, _, s_right, _ = seen["stage"]
    vw, vh = seen["viewport"]
    assert s_left <= left and right <= s_right, seen
    assert 0 <= left and right <= vw and 0 <= top and bottom <= vh, seen
    return (left + right) / 2, (top + bottom) / 2


def _touch(cdp, kind, x=None, y=None):
    points = [] if x is None else [{"x": x, "y": y}]
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})


# ==========================================================================
# AC-1 / AC-2 — every cell is a 24..28 px target at 390 x 844; the board
# scrolls inside the stage, never the page
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_CellsAreATapTarget:
    """AC-1 / AC-2."""

    @pytest.mark.parametrize("name", list(GRIDS))
    def test_every_cell_is_between_24_and_28_px(self, browser_page, live, name) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(GRIDS[name]))

        cells = browser_page.evaluate(_CELLS)

        assert len(cells) == len(GRIDS[name]) * len(GRIDS[name][0])
        sides = [side for cell in cells for side in cell]
        assert FLOOR <= min(sides) and max(sides) <= CAP, (min(sides), max(sides))

    @pytest.mark.parametrize("name", list(GRIDS))
    def test_the_board_scrolls_in_its_stage_and_the_page_does_not(self, browser_page, live, name) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(GRIDS[name]))

        fit = browser_page.evaluate(_FIT)

        assert fit["pageWidth"] <= fit["viewport"], fit
        assert fit["stageScrollWidth"] > fit["stageClientWidth"], fit


# ==========================================================================
# AC-3 — the floor applies at 820 px and not at 821 px
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_FloorAppliesOnlyBelowTheShellBreakpoint:
    """AC-3."""

    def test_820_gets_the_floor_and_821_the_desktop_clamp(self, browser_page, live) -> None:
        puzzle_id = live.store(BIG)
        sides = {}
        for width in (820, 821):
            browser_page.set_viewport_size({"width": width, "height": 900})
            _open(browser_page, live, puzzle_id)
            cells = browser_page.evaluate(_CELLS)
            sides[width] = (min(s for cell in cells for s in cell), max(s for cell in cells for s in cell))

        assert sides[820][0] >= FLOOR, sides
        assert sides[821][1] < FLOOR, sides


# ==========================================================================
# AC-4 — desktop sizing is the value measured on main
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_DesktopSizingUnchanged:
    """AC-4."""

    @pytest.mark.parametrize("name", list(GRIDS))
    def test_the_1440_cell_width_is_mains(self, browser_page, live, name) -> None:
        browser_page.set_viewport_size({"width": 1440, "height": 900})
        _open(browser_page, live, live.store(GRIDS[name]))

        widths = {round(w, 3) for w, _ in browser_page.evaluate(_CELLS)}

        assert widths == {DESKTOP_CELL[name]}, widths


# ==========================================================================
# AC-5 / AC-6 — touch marks the cells under the finger on a scrolled board
# ==========================================================================

ROW = 12
RIGHT_FIVE = [(ROW, c) for c in range(BIG_SIDE - 5, BIG_SIDE)]


def _scrolled_phone_page(browser, live, tool=None):
    """The 30 x 30 at 390 x 844 in a touch context, ``tool`` picked first (a
    click scrolls its button into view), the stage scrolled to its right end
    and the page scrolled down to ROW."""
    context = _phone(browser)
    page = context.new_page()
    _open(page, live, live.store(BIG))
    if tool:
        page.get_by_role("button", name=tool, exact=True).click()
    page.evaluate("const s = document.querySelector('.player-stage'); s.scrollLeft = s.scrollWidth;")
    left = _stage_scroll_left(page)
    assert left > 0 and left == page.evaluate(
        "const s = document.querySelector('.player-stage'); s.scrollWidth - s.clientWidth"
    )
    _bring_row_to_middle(page, ROW)
    assert _stage_scroll_left(page) == left
    return context, page, left


@pytest.mark.browser
class TestSolverPhone_TouchDragMarksOnAScrolledBoard:
    """AC-5 / AC-6."""

    def test_a_touch_drag_marks_exactly_the_five_cells_under_the_finger(self, browser, live) -> None:
        context, page, left = _scrolled_phone_page(browser, live, tool="White")
        try:
            (x0, y0), (x1, _) = _visible_centre(page, *RIGHT_FIVE[0]), _visible_centre(page, *RIGHT_FIVE[-1])
            for cell in RIGHT_FIVE[1:-1]:
                _visible_centre(page, *cell)
            cdp = context.new_cdp_session(page)
            _touch(cdp, "touchStart", x0, y0)
            for k in range(1, 9):
                _touch(cdp, "touchMove", x0 + (x1 - x0) * k / 8, y0)
            _touch(cdp, "touchEnd")

            assert _changed(_states(page)) == {cell: E for cell in RIGHT_FIVE}
            assert _stage_scroll_left(page) == left
        finally:
            context.close()

    def test_a_tap_fills_exactly_that_cell(self, browser, live) -> None:
        context, page, left = _scrolled_phone_page(browser, live)
        try:
            x, y = _visible_centre(page, ROW, BIG_SIDE - 3)
            cdp = context.new_cdp_session(page)
            _touch(cdp, "touchStart", x, y)
            _touch(cdp, "touchEnd")

            assert _changed(_states(page)) == {(ROW, BIG_SIDE - 3): F}
            assert _stage_scroll_left(page) == left
        finally:
            context.close()


# ==========================================================================
# AC-7 — a swipe that starts on the column clues pans the board
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_SwipingTheCluesPansTheBoard:
    """AC-7."""

    # The swipe starts in the column-clue band (the board's header row), at the
    # rightmost point of it the stage shows. On the deep-row-clue 30 x 30 at
    # scrollLeft 0 the row-clue gutter (15 numbers) is wider than the 358 px
    # stage, so the only part of that band in view is the corner box; the
    # 25 x 15 shows real column-clue boxes there. Both are asserted by class.
    @pytest.mark.parametrize(("name", "start_on"), [("30x30", "player-corner"), ("25x15", "player-clue is-col")])
    def test_a_swipe_on_the_column_clue_band_scrolls_the_stage_and_marks_nothing(
        self, browser, live, name, start_on
    ) -> None:
        context = _phone(browser)
        page = context.new_page()
        try:
            _open(page, live, live.store(GRIDS[name]))
            assert _stage_scroll_left(page) == 0
            # CARD-196 (owner-approved G-8 exception): on the 30 x 30 the corner
            # box is the visible part of the band, so the start point is taken
            # inside the corner box rather than at the stage's right edge.
            x, y, under = page.evaluate(
                """(onCorner) => {
                  const stage = document.querySelector('.player-stage').getBoundingClientRect();
                  const band = document.querySelector('.player-board thead tr').getBoundingClientRect();
                  const corner = document.querySelector('.player-corner').getBoundingClientRect();
                  const reach = onCorner ? Math.min(stage.right, corner.right) : Math.min(stage.right, band.right);
                  const x = reach - 12, y = band.top + band.height / 2;
                  return [x, y, document.elementFromPoint(x, y).closest('th, td').className];
                }""",
                start_on == "player-corner",
            )
            assert under == start_on
            cdp = context.new_cdp_session(page)
            _touch(cdp, "touchStart", x, y)
            for k in range(1, 11):
                _touch(cdp, "touchMove", x - 20 * k, y)
            _touch(cdp, "touchEnd")

            page.wait_for_function("document.querySelector('.player-stage').scrollLeft > 0", timeout=2000)
            assert _changed(_states(page), len(GRIDS[name][0])) == {}
        finally:
            context.close()

    def test_cells_take_no_touch_action_and_clue_boxes_keep_the_default(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(BIG))

        actions = browser_page.evaluate(
            """() => {
              const of = (sel) => new Set([...document.querySelectorAll(sel)].map((el) => getComputedStyle(el).touchAction));
              return { cells: [...of('td.player-cell')], colClues: [...of('.player-clue.is-col')],
                       rowClues: [...of('.player-clue.is-row')], corner: [...of('.player-corner')] };
            }"""
        )

        assert actions["cells"] == ["none"]
        for kind in ("colClues", "rowClues", "corner"):
            assert actions[kind] == ["auto"], actions
