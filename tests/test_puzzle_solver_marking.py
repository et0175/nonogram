"""CARD-161 — marking cells in the puzzle player (FR-044 AC-303..AC-311, EC-035).

The player page (``/puzzle/<id>/solve``, CARD-160) gains a tool picker
(black / white / undecided), a click cycle, line-constrained drags, stroke-level
undo and redo (buttons and Ctrl/Cmd+Z, Shift+Ctrl/Cmd+Z) and a reset.

Every user-facing criterion is driven by REAL input in Chromium — ``page.mouse``,
``locator.click``, ``page.keyboard``, ``page.touchscreen`` and CDP touch events —
never by ``puzzlePlayer.setBoard``. Expected boards come from a small Python
model written here (``_Model``, ``_line_cells``), not from the JavaScript under
test. The pure state module (``static/solver_state.js``, ADR-0038/R4) is also
exercised directly with ``await import('/static/solver_state.js')``, including
the EC-035 property corpus: built in Python with ``random.Random`` and a fixed
seed (no ``hypothesis``), its minimum counts asserted inside the test.

Fixtures (real Chromium refusing loudly when absent, ADR-0038/R8; a loopback
Flask panel over a temp SQLite store) are CARD-160's, imported below.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import pytest

from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)

_STATIC = Path(__file__).resolve().parent.parent / "src" / "nonogram" / "admin" / "static"

U, F, E = "unknown", "filled", "empty"
TOOLS = {"Black": F, "White": E, "Undecided": U}
CYCLE = {U: F, F: E, E: U}

#: 15 x 15, uniquely solvable (every row tight): the board most tests mark on.
GRID = _unique_grid(15, 15, seed=161)
SIDE = 15


# --------------------------------------------------------------------------
# An independent model of the board, strokes and history
# --------------------------------------------------------------------------


def _line_cells(start, path):
    """The cells a drag covers, as a set — written apart from dragLine.

    The axis is the first path cell's, other than ``start``: the row when its
    column distance is at least its row distance. The covered cells are the
    union of the spans between consecutive on-line positions, ``start`` first.
    """
    sr, sc = start
    moved = [p for p in path if tuple(p) != (sr, sc)]
    if not moved:
        return {(sr, sc)}
    fr, fc = moved[0]
    along_row = abs(fc - sc) >= abs(fr - sr)
    if along_row:
        stops = [sc] + [c for r, c in path if r == sr]
        return {(sr, k) for a, b in zip(stops, stops[1:]) for k in range(min(a, b), max(a, b) + 1)} | {(sr, sc)}
    stops = [sr] + [r for r, c in path if c == sc]
    return {(k, sc) for a, b in zip(stops, stops[1:]) for k in range(min(a, b), max(a, b) + 1)} | {(sr, sc)}


class _Model:
    """Boards as dicts; undo keeps whole snapshots, so it shares nothing with
    the module's {stroke, before} entries."""

    def __init__(self, width, height):
        self.width, self.height = width, height
        self.board = {(r, c): U for r in range(height) for c in range(width)}
        self.past = []  # snapshots before each recorded stroke
        self.future = []  # snapshots after each undone stroke, next redo last

    def _apply(self, cells, state):
        after = dict(self.board)
        for cell in cells:
            after[cell] = state
        if after != self.board:  # a stroke that changes nothing is not a step
            self.past.append(self.board)
            self.future = []
            self.board = after

    def click(self, r, c):
        self._apply({(r, c)}, CYCLE[self.board[(r, c)]])

    def drag(self, tool, start, path):
        self._apply(_line_cells(start, path), tool)

    def reset(self):
        self._apply(set(self.board), U)

    def undo(self):
        if self.past:
            self.future.append(self.board)
            self.board = self.past.pop()

    def redo(self):
        if self.future:
            self.past.append(self.board)
            self.board = self.future.pop()

    def cells(self):
        return [self.board[(r, c)] for r in range(self.height) for c in range(self.width)]


# --------------------------------------------------------------------------
# Driving the page
# --------------------------------------------------------------------------


def _cell(page, r, c):
    return page.locator(f'td.player-cell[data-row="{r}"][data-col="{c}"]')


def _centre(page, r, c):
    box = _cell(page, r, c).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _drag(page, cells, steps=4):
    """Press on cells[0], move through each next cell's centre, release."""
    page.mouse.move(*_centre(page, *cells[0]))
    page.mouse.down()
    for cell in cells[1:]:
        page.mouse.move(*_centre(page, *cell), steps=steps)
    page.mouse.up()


def _states(page):
    """The board as drawn (data-state per cell) — asserted equal to getBoard()."""
    seen = page.evaluate(
        """() => ({ drawn: [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state),
                    board: [...window.puzzlePlayer.getBoard().cells] })"""
    )
    assert seen["drawn"] == seen["board"]
    return seen["drawn"]


def _at(states, r, c, width=SIDE):
    return states[r * width + c]


def _marked(states, width=SIDE):
    return {(i // width, i % width): s for i, s in enumerate(states) if s != U}


def _button(page, name):
    return page.get_by_role("button", name=name, exact=True)


def _tool(page, name):
    _button(page, name).click()


def _is_disabled(page, name):
    return _button(page, name).get_attribute("aria-disabled") == "true"


_LOOK = """(td) => {
  const after = getComputedStyle(td, '::after');
  return { background: getComputedStyle(td).backgroundColor,
           mark: after.content !== 'none' && parseFloat(after.width) > 0 };
}"""

_TOKEN_RGB = """(name) => {
  const probe = document.createElement('div');
  probe.style.backgroundColor = `var(${name})`;
  document.body.append(probe);
  const rgb = getComputedStyle(probe).backgroundColor;
  probe.remove();
  return rgb;
}"""


# ==========================================================================
# AC-303 / AC-304 — the click cycle
# ==========================================================================


@pytest.mark.browser
class TestSolverMarking_ClickCycles:
    """AC-303 — three clicks: filled, marked empty, undecided; drawn black, dot, blank."""

    def test_three_clicks_go_filled_empty_undecided_and_are_drawn_so(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        assert _button(browser_page, "Black").get_attribute("aria-pressed") == "true"
        ink = browser_page.evaluate(_TOKEN_RGB, "--grid-ink")
        paper = browser_page.evaluate(_TOKEN_RGB, "--grid-paper")
        cell = _cell(browser_page, 4, 6)

        seen = []
        for _ in range(3):
            cell.click()
            seen.append((_at(_states(browser_page), 4, 6), cell.evaluate(_LOOK)))

        assert [state for state, _ in seen] == [F, E, U]
        assert seen[0][1] == {"background": ink, "mark": False}  # black
        assert seen[1][1] == {"background": paper, "mark": True}  # the dot
        assert seen[2][1] == {"background": paper, "mark": False}  # blank
        assert _marked(_states(browser_page)) == {}

    def test_a_click_changes_only_its_cell(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        model = _Model(SIDE, SIDE)
        for r, c in [(0, 0), (14, 14), (7, 3), (7, 3), (0, 14)]:
            _cell(browser_page, r, c).click()
            model.click(r, c)
            assert _states(browser_page) == model.cells()

    def test_a_touch_tap_cycles_too(self, browser, live) -> None:
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            page.evaluate("window.__types = []; document.addEventListener('pointerdown', (e) => window.__types.push(e.pointerType))")
            seen = []
            for _ in range(3):
                page.touchscreen.tap(*_centre(page, 2, 2))
                seen.append(_at(_states(page), 2, 2))
            assert seen == [F, E, U]
            assert set(page.evaluate("window.__types")) == {"touch"}
        finally:
            context.close()

    def test_other_mouse_buttons_mark_nothing(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 3, 3).click(button="right")
        _cell(browser_page, 3, 3).click(button="middle")
        assert _marked(_states(browser_page)) == {}


@pytest.mark.browser
class TestSolverMarking_ClickIgnoresTheSelectedTool:
    """AC-304 — a click cycles whatever tool is selected."""

    @pytest.mark.parametrize("tool", ["White", "Undecided", "Black"])
    def test_a_click_on_an_undecided_cell_fills_it_whatever_the_tool(self, browser_page, live, tool) -> None:
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, tool)
        assert _button(browser_page, tool).get_attribute("aria-pressed") == "true"

        _cell(browser_page, 5, 5).click()

        assert _marked(_states(browser_page)) == {(5, 5): F}

    def test_the_whole_cycle_ignores_the_tool(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        seen = []
        for tool in ("White", "Undecided", "White"):
            _tool(browser_page, tool)
            _cell(browser_page, 1, 1).click()
            seen.append(_at(_states(browser_page), 1, 1))
        assert seen == [F, E, U]

    def test_exactly_one_tool_is_pressed(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        for name in ("White", "White", "Undecided", "Black"):
            _tool(browser_page, name)
            pressed = {n: _button(browser_page, n).get_attribute("aria-pressed") for n in TOOLS}
            assert pressed == {n: str(n == name).lower() for n in TOOLS}


# ==========================================================================
# AC-305 / AC-306 — drags keep to one line
# ==========================================================================


@pytest.mark.browser
class TestSolverMarking_DragMarksOneLine:
    """AC-305 / AC-306 — a drag marks the cells passed along the row or column it started on."""

    def test_row_2_columns_3_to_7(self, browser_page, live) -> None:
        """AC-305 (1-based row 2, columns 3..7 = row index 1, column indexes 2..6)."""
        _open(browser_page, live, live.store(GRID))

        _drag(browser_page, [(1, 2), (1, 6)])

        assert _marked(_states(browser_page)) == {(1, c): F for c in range(2, 7)}

    def test_a_drag_that_wanders_off_marks_only_its_row(self, browser_page, live) -> None:
        """AC-306 — start row 2 column 3, wander through row 3 column 5 to row 4 column 7."""
        _open(browser_page, live, live.store(GRID))

        _drag(browser_page, [(1, 2), (2, 4), (3, 6)])

        marked = _marked(_states(browser_page))
        assert (1, 2) in marked and set(marked.values()) == {F}
        assert {r for r, _ in marked} == {1}, marked  # nothing in rows 3 or 4 (indexes 2, 3)

    def test_a_drag_that_jumps_off_its_row_marks_only_the_start(self, browser_page, live) -> None:
        """AC-306, cell by cell with no intermediate pointer positions."""
        _open(browser_page, live, live.store(GRID))

        _drag(browser_page, [(1, 2), (2, 4), (3, 6)], steps=1)

        assert _marked(_states(browser_page)) == {(1, 2): F}

    def test_coming_back_to_the_row_marks_the_span_passed(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))

        _drag(browser_page, [(1, 2), (1, 4), (3, 6), (1, 9)], steps=1)

        assert _marked(_states(browser_page)) == {(1, c): F for c in range(2, 10)}

    def test_a_fast_drag_covers_every_cell_it_passed(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))

        _drag(browser_page, [(6, 0), (6, 14)], steps=1)

        assert _marked(_states(browser_page)) == {(6, c): F for c in range(15)}

    def test_a_drag_down_a_column(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))

        _drag(browser_page, [(2, 8), (4, 8), (5, 10), (7, 8)])

        assert _marked(_states(browser_page)) == {(r, 8): F for r in range(2, 8)}

    @pytest.mark.parametrize("tool", ["White", "Undecided"])
    def test_each_tool_sets_its_state_along_the_line(self, browser_page, live, tool) -> None:
        _open(browser_page, live, live.store(GRID))
        _drag(browser_page, [(4, 0), (4, 9)])  # Black first
        _tool(browser_page, tool)

        _drag(browser_page, [(4, 3), (4, 6)])

        expected = {(4, c): F for c in range(10)}
        expected.update({(4, c): TOOLS[tool] for c in range(3, 7)})
        assert _marked(_states(browser_page)) == {k: v for k, v in expected.items() if v != U}

    def test_a_drag_is_previewed_and_recorded_on_release(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        browser_page.mouse.move(*_centre(browser_page, 6, 2))
        browser_page.mouse.down()
        browser_page.mouse.move(*_centre(browser_page, 6, 5), steps=4)

        during = _marked(_states(browser_page))
        undo_during = _is_disabled(browser_page, "Undo")
        browser_page.mouse.up()

        assert during == {(6, c): F for c in range(2, 6)}
        assert undo_during  # not a step until the pointer is released
        assert _marked(_states(browser_page)) == during and not _is_disabled(browser_page, "Undo")

    def test_a_drag_released_outside_the_board_still_counts(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        x, y = _centre(browser_page, 0, 10)
        browser_page.mouse.move(*_centre(browser_page, 0, 12))
        browser_page.mouse.down()
        browser_page.mouse.move(x, y, steps=4)
        browser_page.mouse.move(x, 5, steps=4)  # up over the page header
        browser_page.mouse.up()

        assert _marked(_states(browser_page)) == {(0, 10): F, (0, 11): F, (0, 12): F}
        _cell(browser_page, 9, 9).click()  # the next stroke starts from the recorded drag
        _button(browser_page, "Undo").click()
        _button(browser_page, "Undo").click()
        assert _marked(_states(browser_page)) == {}

    def test_a_touch_drag_marks_one_line(self, browser, live) -> None:
        """Real touch input through Chromium's input pipeline (CDP touch events)."""
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            page.evaluate("window.__types = []; document.addEventListener('pointermove', (e) => window.__types.push(e.pointerType))")
            cdp = context.new_cdp_session(page)
            (x0, y0), (x1, y1) = _centre(page, 1, 2), _centre(page, 1, 6)
            (xo, yo) = _centre(page, 3, 6)
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
            for k in range(1, 9):
                x = x0 + (x1 - x0) * k / 8
                cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0}]})
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": xo, "y": yo}]})
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

            assert _marked(_states(page)) == {(1, c): F for c in range(2, 7)}
            assert set(page.evaluate("window.__types")) == {"touch"}
            assert page.evaluate("scrollX === 0 && scrollY === 0")
        finally:
            context.close()


# ==========================================================================
# AC-307 / AC-308 — undo and redo by stroke
# ==========================================================================


def _seven_marks(page):
    """AC-307's board: one five-cell drag, then two single clicks."""
    _drag(page, [(1, 2), (1, 6)])
    _cell(page, 5, 5).click()
    _cell(page, 9, 0).click()


@pytest.mark.browser
class TestSolverMarking_UndoRedoByStroke:
    """AC-307 / AC-308 — undo and redo move a whole stroke; a new stroke drops redo."""

    def test_three_undos_then_three_redos(self, browser_page, live) -> None:
        """AC-307."""
        _open(browser_page, live, live.store(GRID))
        _seven_marks(browser_page)
        drag = {(1, c): F for c in range(2, 7)}
        all_seven = {**drag, (5, 5): F, (9, 0): F}
        assert _marked(_states(browser_page)) == all_seven

        after_undos = []
        for _ in range(3):
            _button(browser_page, "Undo").click()
            after_undos.append(_marked(_states(browser_page)))
        assert after_undos == [{**drag, (5, 5): F}, drag, {}]
        assert _is_disabled(browser_page, "Undo")

        after_redos = []
        for _ in range(3):
            _button(browser_page, "Redo").click()
            after_redos.append(_marked(_states(browser_page)))
        assert after_redos == [drag, {**drag, (5, 5): F}, all_seven]
        assert _is_disabled(browser_page, "Redo")

    def test_a_new_stroke_after_undo_drops_redo(self, browser_page, live) -> None:
        """AC-308."""
        _open(browser_page, live, live.store(GRID))
        _seven_marks(browser_page)
        _button(browser_page, "Undo").click()
        assert not _is_disabled(browser_page, "Redo")

        _cell(browser_page, 12, 12).click()
        before = _states(browser_page)
        redo = browser_page.get_by_role("button", name="Redo", exact=True, disabled=True)
        assert redo.count() == 1
        redo.click(force=True)  # a real click on the disabled control
        browser_page.keyboard.press("Shift+Control+z")

        assert _states(browser_page) == before
        assert _marked(before) == {**{(1, c): F for c in range(2, 7)}, (5, 5): F, (12, 12): F}

    def test_nothing_to_undo_or_redo_at_load(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        assert _is_disabled(browser_page, "Undo") and _is_disabled(browser_page, "Redo")
        assert _is_disabled(browser_page, "Reset")
        for name in ("Undo", "Redo", "Reset"):
            _button(browser_page, name).click(force=True)  # disabled: Playwright would wait
        browser_page.keyboard.press("Control+z")
        assert _marked(_states(browser_page)) == {}

    def test_a_drag_that_changes_nothing_is_not_a_step(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _drag(browser_page, [(3, 0), (3, 4)])
        _drag(browser_page, [(5, 0), (5, 4)])
        _button(browser_page, "Undo").click()  # redo now holds the row-5 drag
        _drag(browser_page, [(3, 1), (3, 3)])  # Black over black cells: no change
        _tool(browser_page, "Undecided")
        _drag(browser_page, [(10, 0), (10, 4)])  # Undecided over blank cells: no change

        assert not _is_disabled(browser_page, "Redo")  # the redo stack was kept
        _button(browser_page, "Redo").click()
        assert _marked(_states(browser_page)) == {(r, c): F for r in (3, 5) for c in range(5)}
        _button(browser_page, "Undo").click()
        _button(browser_page, "Undo").click()  # one undo per real stroke: two reach blank
        assert _marked(_states(browser_page)) == {}
        assert _is_disabled(browser_page, "Undo")

    def test_reset_clears_the_board_as_one_undoable_step(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _seven_marks(browser_page)
        _tool(browser_page, "White")
        _drag(browser_page, [(12, 1), (12, 4)])
        marks = _marked(_states(browser_page))
        assert len(marks) == 11

        _button(browser_page, "Reset").click()
        assert _marked(_states(browser_page)) == {}
        assert _is_disabled(browser_page, "Reset")

        _button(browser_page, "Undo").click()
        assert _marked(_states(browser_page)) == marks
        _button(browser_page, "Redo").click()
        assert _marked(_states(browser_page)) == {}

    def test_set_board_starts_a_new_history(self, browser_page, live) -> None:
        """The CARD-160 seam: an outside setBoard is the new starting point."""
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 0, 0).click()
        browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              window.puzzlePlayer.setBoard(S.withCell(window.puzzlePlayer.getBoard(), 2, 2, S.EMPTY));
            }"""
        )
        assert _is_disabled(browser_page, "Undo") and _is_disabled(browser_page, "Redo")
        _cell(browser_page, 2, 2).click()  # cycles from the set state
        assert _marked(_states(browser_page)) == {(0, 0): F}
        _button(browser_page, "Undo").click()
        assert _marked(_states(browser_page)) == {(0, 0): F, (2, 2): E}


# ==========================================================================
# AC-309 / AC-310 — keyboard and labels
# ==========================================================================

CONTROLS = ["Black", "White", "Undecided", "Undo", "Redo", "Reset"]

_FOCUSED = """() => {
  const el = document.activeElement;
  return el && el.closest('#puzzle-player-controls') ? el.textContent.trim() : null;
}"""


@pytest.mark.browser
class TestSolverMarking_KeyboardAndLabels:
    """AC-309 / AC-310 — the shortcuts, and every control by keyboard alone."""

    @pytest.mark.parametrize("modifier", ["Control", "Meta"])
    def test_ctrl_z_undoes_and_shift_ctrl_z_redoes(self, browser_page, live, modifier) -> None:
        """AC-309 (Cmd is Meta)."""
        _open(browser_page, live, live.store(GRID))
        _drag(browser_page, [(1, 2), (1, 6)])
        _cell(browser_page, 8, 8).click()
        two = _marked(_states(browser_page))
        browser_page.locator("h1").click()  # keyboard focus on the page, not on a control

        browser_page.keyboard.press(f"{modifier}+z")
        after_undo = _marked(_states(browser_page))
        browser_page.keyboard.press(f"Shift+{modifier}+z")
        after_redo = _marked(_states(browser_page))

        assert after_undo == {(1, c): F for c in range(2, 7)}
        assert after_redo == two

    def test_each_control_has_a_name_and_is_reachable_by_tab(self, browser_page, live) -> None:
        """AC-310 — names and Tab order."""
        from playwright.sync_api import expect

        _open(browser_page, live, live.store(GRID))
        for name in CONTROLS:
            button = _button(browser_page, name)
            assert button.count() == 1, name
            expect(button).to_have_accessible_name(re.compile(r"\S"))

        browser_page.evaluate("document.activeElement && document.activeElement.blur()")
        reached = []
        for _ in range(80):
            browser_page.keyboard.press("Tab")
            focused = browser_page.evaluate(_FOCUSED)
            if focused and focused not in reached:
                reached.append(focused)
            if len(reached) == len(CONTROLS):
                break
        assert reached == CONTROLS

    def test_each_control_acts_on_enter_or_space(self, browser_page, live) -> None:
        """AC-310 — operate every control with the keyboard alone (strokes need a pointer)."""
        _open(browser_page, live, live.store(GRID))
        _drag(browser_page, [(1, 2), (1, 6)])
        _cell(browser_page, 8, 8).click()
        two = _marked(_states(browser_page))

        def press(name, key):
            _button(browser_page, name).focus()
            browser_page.keyboard.press(key)

        press("White", "Space")
        assert _button(browser_page, "White").get_attribute("aria-pressed") == "true"
        press("Undecided", "Enter")
        assert _button(browser_page, "Undecided").get_attribute("aria-pressed") == "true"
        press("Black", "Space")
        assert _button(browser_page, "Black").get_attribute("aria-pressed") == "true"

        press("Undo", "Enter")
        assert _marked(_states(browser_page)) == {(1, c): F for c in range(2, 7)}
        press("Redo", "Space")
        assert _marked(_states(browser_page)) == two
        press("Undo", "Space")
        press("Redo", "Enter")
        assert _marked(_states(browser_page)) == two
        press("Reset", "Enter")
        assert _marked(_states(browser_page)) == {}
        press("Undo", "Enter")
        press("Reset", "Space")
        assert _marked(_states(browser_page)) == {}

    def test_the_tool_picked_by_keyboard_governs_the_next_drag(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _button(browser_page, "White").focus()
        browser_page.keyboard.press("Enter")

        _drag(browser_page, [(0, 0), (0, 3)])

        assert _marked(_states(browser_page)) == {(0, c): E for c in range(4)}

    def test_shortcuts_are_announced(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        assert "Control+Z" in _button(browser_page, "Undo").get_attribute("aria-keyshortcuts")
        assert "Shift+Meta+Z" in _button(browser_page, "Redo").get_attribute("aria-keyshortcuts")


# ==========================================================================
# AC-311 / ADR-0038/R2 — no request per mark; G-2 — no correctness shown
# ==========================================================================


def _twenty_strokes(page):
    """10 clicks and 10 drags (with tool changes between), mirrored in a model."""
    model = _Model(SIDE, SIDE)
    tools = ["Black", "White", "Undecided"]
    for k in range(10):
        r, c = k, (3 * k) % SIDE
        _cell(page, r, c).click()
        model.click(r, c)
        tool = tools[k % 3]
        _tool(page, tool)
        start, end = (14 - k, 1), (14 - k, 1 + k)
        if k % 2:
            start, end = (2, 14 - k), (2 + k, 14 - k)
        _drag(page, [start, end])
        model.drag(TOOLS[tool], start, [end])
    return model


@pytest.mark.browser
class TestSolverMarking_NoRequestPerMark:
    """AC-311, and the named check of ADR-0038/R2 — marking is entirely client-side."""

    def test_twenty_strokes_issue_no_request(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.context.on("request", lambda request: requests.append(request.url))

        model = _twenty_strokes(browser_page)
        _button(browser_page, "Undo").click()
        model.undo()
        browser_page.keyboard.press("Control+z")
        model.undo()
        _button(browser_page, "Redo").click()
        model.redo()
        _button(browser_page, "Reset").click()
        model.reset()

        assert _states(browser_page) == model.cells()
        assert requests == []

    def test_strokes_leave_the_console_clean(self, browser_page, live) -> None:
        problems = []
        browser_page.on("console", lambda m: m.type in ("error", "warning") and problems.append(m.text))
        browser_page.on("pageerror", lambda e: problems.append(str(e)))
        browser_page.on("requestfailed", lambda r: problems.append(f"failed: {r.url}"))
        browser_page.on(
            "response",
            lambda r: r.url.startswith(live.url) and r.status >= 400 and problems.append(f"{r.status}: {r.url}"),
        )
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")

        model = _twenty_strokes(browser_page)
        for name in ("Undo", "Redo", "Reset", "Undo"):
            _button(browser_page, name).click()

        assert len(model.past) >= 15
        assert problems == []


_STRIPPED = """() => document.body.outerHTML
  .replace(/ data-state="[a-z]+"/g, '')
  .replace(/ aria-(pressed|disabled)="(true|false)"/g, '')"""


@pytest.mark.browser
class TestSolverMarking_RevealsNoCorrectness:
    """G-2 — marking, even marking the whole solution, shows nothing but the marks."""

    def test_marking_the_solution_changes_nothing_but_cell_states(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        before = browser_page.evaluate(_STRIPPED)

        for r, row in enumerate(GRID):  # every filled run, by drag or click
            c = 0
            while c < SIDE:
                if row[c]:
                    end = c
                    while end + 1 < SIDE and row[end + 1]:
                        end += 1
                    if end > c:
                        _drag(browser_page, [(r, c), (r, end)])
                    else:
                        _cell(browser_page, r, c).click()
                    c = end
                c += 1

        assert _states(browser_page) == [F if cell else U for row in GRID for cell in row]
        assert browser_page.evaluate(_STRIPPED) == before

    def test_the_marking_code_reads_no_solution(self) -> None:
        code = re.sub(r"//[^\n]*", "", (_STATIC / "solver.js").read_text(encoding="utf-8"))
        marking = code[code.index("function wireMarking"):]
        assert "solution" not in marking
        state = re.sub(r"//[^\n]*", "", (_STATIC / "solver_state.js").read_text(encoding="utf-8"))
        assert "solution" not in state


# ==========================================================================
# The pure module — strokes and history, branch by branch
# ==========================================================================


@pytest.mark.browser
class TestSolverHistoryModule:
    """solver_state.js stroke and history functions, imported in the page they ship to."""

    def test_cycle_and_strokes(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        out = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const refused = (f) => { try { f(); return null; } catch (e) { return e.name; } };
              const board = S.withCell(S.createBoard(3, 2), 1, 2, S.EMPTY);
              const click = S.clickStroke(board, 1, 2);
              const reset = S.resetStroke(board);
              return {
                cycle: [S.UNKNOWN, S.FILLED, S.EMPTY].map(S.cycled),
                badCycle: refused(() => S.cycled('black')),
                click: [click.cells, click.state],
                clickFrozen: Object.isFrozen(click) && Object.isFrozen(click.cells) && Object.isFrozen(click.cells[0]),
                drag: S.dragStroke([0, 0], [[0, 2]], S.EMPTY),
                badTool: refused(() => S.dragStroke([0, 0], [], 'black')),
                reset: [reset.cells, reset.state],
                applied: S.applyStroke(board, S.dragStroke([0, 0], [[0, 2]], S.FILLED)).cells,
                appliedIsBoard: S.isBoard(S.applyStroke(board, click)),
                untouched: board.cells,
                outside: refused(() => S.applyStroke(board, { cells: [[2, 0]], state: S.FILLED })),
                badState: refused(() => S.applyStroke(board, { cells: [[0, 0]], state: 'black' })),
                replayNone: S.replay(board, []) === board,
                replayTwo: S.replay(S.createBoard(3, 2), [click, S.clickStroke(board, 0, 0)]).cells,
              };
            }"""
        )
        assert out["cycle"] == [F, E, U]
        assert out["badCycle"] == "RangeError" and out["badTool"] == "RangeError"
        assert out["click"] == [[[1, 2]], U] and out["clickFrozen"]
        assert out["drag"] == {"cells": [[0, 0], [0, 1], [0, 2]], "state": E}
        assert out["reset"] == [[[r, c] for r in range(2) for c in range(3)], U]
        assert out["applied"] == [F, F, F, U, U, E] and out["appliedIsBoard"]
        assert out["untouched"] == [U, U, U, U, U, E]
        assert out["outside"] == "RangeError" and out["badState"] == "RangeError"
        assert out["replayNone"] and out["replayTwo"] == [F, U, U, U, U, U]

    @pytest.mark.parametrize(
        "start, path, expected",
        [
            ((2, 3), [], [(2, 3)]),
            ((2, 3), [(2, 3), (2, 3)], [(2, 3)]),
            ((2, 3), [(2, 4), (2, 7)], [(2, 3), (2, 4), (2, 5), (2, 6), (2, 7)]),
            ((2, 3), [(5, 3)], [(2, 3), (3, 3), (4, 3), (5, 3)]),
            ((2, 3), [(3, 4), (2, 1)], [(2, 3), (2, 2), (2, 1)]),  # tie: the row; off-row ignored
            ((2, 3), [(4, 4), (5, 3)], [(2, 3), (3, 3), (4, 3), (5, 3)]),  # further in rows: the column
            ((2, 3), [(2, 5), (2, 1)], [(2, 3), (2, 4), (2, 5), (2, 2), (2, 1)]),
            ((2, 3), [(2, 5), (3, 9), (2, 8)], [(2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8)]),
            ((2, 3), [(3, 5), (4, 7)], [(2, 3)]),  # AC-306's wander, cell by cell
        ],
        ids=["no-path", "only-start", "row-skips", "column", "tie-is-row", "column-wins",
             "back-and-forth", "returns-to-row", "ac306-wander"],
    )
    def test_drag_line(self, browser_page, live, start, path, expected) -> None:
        _open(browser_page, live, live.store(GRID))
        got = browser_page.evaluate(
            "async ([start, path]) => (await import('/static/solver_state.js')).dragLine(start, path)",
            [list(start), [list(p) for p in path]],
        )
        assert [tuple(cell) for cell in got] == expected
        assert set(expected) == _line_cells(start, path)  # the oracle agrees

    def test_history_branches(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        out = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const blank = S.createBoard(4, 3);
              const h0 = S.createHistory(blank);
              const fill = S.dragStroke([0, 0], [[0, 3]], S.FILLED);
              const h1 = S.record(h0, fill);
              const h2 = S.record(h1, S.clickStroke(h1.board, 2, 2));
              const u1 = S.undo(h2);
              const r1 = S.redo(u1);
              const fresh = S.record(u1, S.clickStroke(u1.board, 1, 1));
              const frozen = (h) => Object.isFrozen(h) && Object.isFrozen(h.done) && Object.isFrozen(h.undone)
                && h.done.every(Object.isFrozen) && Object.isFrozen(h.board);
              return {
                h0: [h0.board === blank, h0.done.length, h0.undone.length],
                noOpRecord: S.record(h1, fill) === h1,
                noOpKeepsRedo: S.record(u1, S.dragStroke([0, 0], [[0, 1]], S.FILLED)) === u1,
                undoEmpty: S.undo(h0) === h0,
                redoEmpty: S.redo(h2) === h2,
                h2: [h2.done.length, h2.board.cells],
                h2Before: h2.done[1].before === h1.board,
                u1: [u1.board === h1.board, u1.done.length, u1.undone.length],
                r1: [r1.board.cells, r1.done.length, r1.undone.length],
                fresh: [fresh.undone.length, fresh.done.length, fresh.board.cells],
                h1Untouched: [h1.done.length, h1.undone.length, h1.board.cells],
                frozen: [h0, h1, h2, u1, r1, fresh].every(frozen),
              };
            }"""
        )
        row0 = [F, F, F, F]
        assert out["h0"] == [True, 0, 0]
        assert out["noOpRecord"] and out["noOpKeepsRedo"]
        assert out["undoEmpty"] and out["redoEmpty"]
        assert out["h2"] == [2, row0 + [U] * 4 + [U, U, F, U]] and out["h2Before"]
        assert out["u1"] == [True, 1, 1]
        assert out["r1"] == [row0 + [U] * 4 + [U, U, F, U], 2, 0]
        assert out["fresh"] == [0, 2, row0 + [U, F, U, U] + [U] * 4]
        assert out["h1Untouched"] == [1, 0, row0 + [U] * 8]
        assert out["frozen"]


# ==========================================================================
# EC-035 — replaying the undo history reproduces the board
# ==========================================================================

_EC_WIDTH, _EC_HEIGHT = 12, 10
_EC_OPS = 1300
_EC_MIN_STROKES = 500

_RUN_HISTORY = """async ({ width, height, ops }) => {
  const S = await import('/static/solver_state.js');
  const blank = S.createBoard(width, height);
  let h = S.createHistory(blank);
  const steps = [];
  for (const op of ops) {
    if (op[0] === 'click') h = S.record(h, S.clickStroke(h.board, op[1], op[2]));
    else if (op[0] === 'drag') h = S.record(h, S.dragStroke(op[2], op[3], op[1]));
    else if (op[0] === 'reset') h = S.record(h, S.resetStroke(h.board));
    else if (op[0] === 'undo') h = S.undo(h);
    else if (op[0] === 'redo') h = S.redo(h);
    else throw new Error(`unknown op ${op[0]}`);
    const replayed = S.replay(blank, h.done.map((entry) => entry.stroke));
    steps.push({
      board: h.board.cells.map((s) => s[0]).join(''),
      replayed: replayed.cells.map((s) => s[0]).join(''),
      done: h.done.length,
      undone: h.undone.length,
    });
  }
  return steps;
}"""


def _ec_ops(rng: random.Random):
    """A random mix: clicks, drags with each tool, resets, undo and redo runs."""
    ops = []
    while len(ops) < _EC_OPS:
        roll = rng.random()
        if roll < 0.30:
            ops.append(["click", rng.randrange(_EC_HEIGHT), rng.randrange(_EC_WIDTH)])
        elif roll < 0.64:
            start = [rng.randrange(_EC_HEIGHT), rng.randrange(_EC_WIDTH)]
            path, here = [], list(start)
            for _ in range(rng.randint(0, 6)):
                kind = rng.random()
                if kind < 0.45:
                    here = [here[0], rng.randrange(_EC_WIDTH)]
                elif kind < 0.8:
                    here = [rng.randrange(_EC_HEIGHT), here[1]]
                else:
                    here = [rng.randrange(_EC_HEIGHT), rng.randrange(_EC_WIDTH)]
                path.append(here)
            ops.append(["drag", rng.choice([F, E, U]), start, path])
        elif roll < 0.66:
            ops.append(["reset"])
        else:
            ops.extend([[rng.choice(["undo", "redo"])]] * rng.randint(1, 4))
    return ops[:_EC_OPS]


@pytest.mark.browser
def test_PropertyTest_SolverHistory_ReplayReproducesTheBoard(browser_page, live) -> None:
    """EC-035 — after every stroke, undo and redo of a seeded corpus, replaying
    the undo stack's strokes from a blank board gives the current board; and
    the board matches the independent Python model at every step."""
    ops = _ec_ops(random.Random(35))
    kinds = [op[0] for op in ops]
    strokes = sum(kind in ("click", "drag", "reset") for kind in kinds)
    per_tool = {tool: sum(op[0] == "drag" and op[1] == tool for op in ops) for tool in (F, E, U)}
    assert strokes >= _EC_MIN_STROKES, strokes
    assert min(per_tool.values()) >= 80, per_tool
    assert kinds.count("click") >= 200 and kinds.count("reset") >= 5
    assert kinds.count("undo") >= 100 and kinds.count("redo") >= 100

    _open(browser_page, live, live.store(GRID))
    steps = browser_page.evaluate(_RUN_HISTORY, {"width": _EC_WIDTH, "height": _EC_HEIGHT, "ops": ops})
    assert len(steps) == len(ops)

    model = _Model(_EC_WIDTH, _EC_HEIGHT)
    effective_redos = dropped_redo_stacks = 0
    for index, (op, step) in enumerate(zip(ops, steps)):
        had_future = len(model.future)
        board_before = model.board
        if op[0] == "click":
            model.click(op[1], op[2])
        elif op[0] == "drag":
            model.drag(op[1], tuple(op[2]), [tuple(p) for p in op[3]])
        elif op[0] == "reset":
            model.reset()
        else:
            getattr(model, op[0])()
        if op[0] == "redo" and model.board is not board_before:
            effective_redos += 1
        if had_future and not model.future and op[0] not in ("undo", "redo"):
            dropped_redo_stacks += 1

        assert step["replayed"] == step["board"], (index, op)
        assert step["board"] == "".join(s[0] for s in model.cells()), (index, op)
        assert (step["done"], step["undone"]) == (len(model.past), len(model.future)), (index, op)

    # The corpus really exercised what it claims to.
    assert effective_redos >= 50 and dropped_redo_stacks >= 20, (effective_redos, dropped_redo_stacks)
