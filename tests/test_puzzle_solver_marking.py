"""CARD-161 — marking cells in the puzzle player (FR-044 AC-303..AC-311, EC-035).

The player page (``/puzzle/<id>/solve``, CARD-160) gains a tool picker
(black / white / undecided), clicks that follow the selected brush (CARD-189),
line-constrained drags, stroke-level undo and redo (buttons and Ctrl/Cmd+Z,
Shift+Ctrl/Cmd+Z) and a reset.

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
    _PAYLOAD,
    _embed,
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)

_STATIC = Path(__file__).resolve().parent.parent / "src" / "nonogram" / "admin" / "static"

U, F, E = "unknown", "filled", "empty"
M = "maybe"  # CARD-186's "?"
TOOLS = {"Black": F, "White": E, "Undecided": U}
#: Every brush (CARD-189): the tool button's name -> the state it paints.
BRUSHES = {**TOOLS, "Maybe": M}

#: What one click does (CARD-189), written out by hand from the card's two
#: tables — never computed from solver_state.js: brush -> {cell before: after}.
#: A first click: the brush's state, or the next step of the brush's sequence
#: when the cell already holds it.
FIRST_CLICK = {
    F: {U: F, F: E, E: F, M: F},
    E: {U: E, F: E, E: U, M: E},
    U: {U: F, F: U, E: U, M: U},
    M: {U: M, F: M, E: M, M: U},
}
#: A repeat click (same cell, same brush, nothing in between): one step along
#: the brush's sequence; a cell outside it takes the brush's state.
REPEAT_CLICK = {
    F: {U: F, F: E, E: U, M: F},
    E: {U: F, F: E, E: U, M: E},
    U: {U: F, F: E, E: U, M: U},
    M: {U: M, F: M, E: M, M: U},
}

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

    def click(self, r, c, tool=F, repeat=False):
        table = REPEAT_CLICK if repeat else FIRST_CLICK
        self._apply({(r, c)}, table[tool][self.board[(r, c)]])

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
# AC-303 / AC-304 — the click cycle (superseded for clicks by CARD-189's
# brush sequences, FR-044 AC-355..AC-359: see TestSolverClickFollowsTheBrush)
# ==========================================================================


@pytest.mark.browser
class TestSolverMarking_ClickCycles:
    """AC-303 — three clicks with Black: filled, marked empty, undecided; drawn
    black, dot, blank. Since CARD-189 the second and third are repeat clicks
    going along Black's sequence (AC-355's Black row)."""

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
        last = None
        for r, c in [(0, 0), (14, 14), (7, 3), (7, 3), (0, 14)]:
            _cell(browser_page, r, c).click()
            model.click(r, c, F, repeat=(r, c) == last)
            last = (r, c)
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
    """AC-304 ("a click cycles whatever tool is selected") is superseded by
    CARD-189 (a click follows the selected brush, FR-044 AC-355..AC-359,
    TestSolverClickFollowsTheBrush); its two click tests were removed with it.
    What stays is the tool picker's own check: exactly one tool is pressed."""

    def test_exactly_one_tool_is_pressed(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        for name in ("White", "White", "Undecided", "Black"):
            _tool(browser_page, name)
            pressed = {n: _button(browser_page, n).get_attribute("aria-pressed") for n in TOOLS}
            assert pressed == {n: str(n == name).lower() for n in TOOLS}


# ==========================================================================
# CARD-189 — a click follows the selected brush (FR-044 AC-355..AC-359,
# card-local AC-1..AC-11)
# ==========================================================================

_CLICK_TABLE_JS = """async () => {
  const S = await import('/static/solver_state.js');
  const out = [];
  for (const brush of S.CELL_STATES) {
    for (const state of S.CELL_STATES) {
      for (const repeat of [false, true]) {
        const board = S.withCell(S.createBoard(4, 3), 1, 2, state);
        const stroke = S.clickStroke(board, 1, 2, brush, repeat);
        out.push({ brush, state, repeat, cells: stroke.cells, after: stroke.state });
      }
    }
  }
  // `repeat` counts only when it is exactly true: Black on a white cell is
  // black on a first click and blank on a repeat click.
  const white = S.withCell(S.createBoard(4, 3), 0, 0, S.EMPTY);
  const coerced = [1, 'true', {}, undefined].map((flag) => S.clickStroke(white, 0, 0, S.FILLED, flag).state);
  return { states: [...S.CELL_STATES], out, coerced };
}"""

_REFUSED_TOOLS_JS = """async () => {
  const S = await import('/static/solver_state.js');
  const board = S.createBoard(4, 3);
  const refused = (f) => { try { f(); return null; } catch (e) { return e.name; } };
  return {
    omitted: refused(() => S.clickStroke(board, 0, 0)),
    omittedRepeat: refused(() => S.clickStroke(board, 0, 0, undefined, true)),
    others: ['black', 'Filled', 'FILLED', '', null, 1, 'crossed'].map(
      (tool) => [String(tool), refused(() => S.clickStroke(board, 0, 0, tool)),
                 refused(() => S.clickStroke(board, 0, 0, tool, true))]),
  };
}"""

#: The cells a brush's four clicks go through from blank (AC-3).
_SEQUENCES = {
    "Black": [F, E, U, F],
    "White": [E, U, F, E],
    "Undecided": [F, E, U, F],
    "Maybe": [M, U, M, U],
}


@pytest.mark.browser
class TestSolverClickFollowsTheBrush:
    """CARD-189 — a first click gives a cell the brush's state (or the next step
    when it already holds it); a repeat click on the same cell with the same
    brush, nothing in between, goes one step along the brush's sequence."""

    def test_every_brush_state_and_repeat_gives_the_table(self, browser_page, live) -> None:
        """AC-1 — all 32 (brush, state, repeat) cases against the literal tables."""
        _open(browser_page, live, live.store(GRID))
        got = browser_page.evaluate(_CLICK_TABLE_JS)
        # A state the literals do not cover fails here, before any lookup.
        assert set(got["states"]) <= set(FIRST_CLICK) and set(got["states"]) <= set(REPEAT_CLICK)
        for table in (FIRST_CLICK, REPEAT_CLICK):
            assert all(set(row) >= set(got["states"]) for row in table.values())
        assert len(got["out"]) == 32
        for row in got["out"]:
            table = REPEAT_CLICK if row["repeat"] else FIRST_CLICK
            want = table[row["brush"]][row["state"]]
            assert want != row["state"]  # every click changes the cell
            assert (row["cells"], row["after"]) == ([[1, 2]], want), row
        assert got["coerced"] == [F, F, F, F]

    def test_a_click_without_a_valid_tool_is_refused(self, browser_page, live) -> None:
        """AC-2 — no tool, or one that is not a cell state: RangeError."""
        _open(browser_page, live, live.store(GRID))
        got = browser_page.evaluate(_REFUSED_TOOLS_JS)
        assert got["omitted"] == "RangeError" and got["omittedRepeat"] == "RangeError"
        assert all(first == again == "RangeError" for _, first, again in got["others"]), got["others"]

    def test_repeat_clicks_follow_each_brush_sequence(self, browser_page, live) -> None:
        """AC-3 — four real clicks on one fresh blank cell per brush."""
        _open(browser_page, live, live.store(GRID))
        seen = {}
        for k, name in enumerate(_SEQUENCES):
            _tool(browser_page, name)
            cell = _cell(browser_page, 2 + 3 * k, 4 + k)
            seen[name] = []
            for _ in range(4):
                cell.click()
                seen[name].append(_at(_states(browser_page), 2 + 3 * k, 4 + k))
        assert seen == _SEQUENCES

    def test_a_first_click_on_each_state_with_each_brush(self, browser_page, live) -> None:
        """AC-4 — dark, white and "?" cells (set by drags), each clicked once by
        each brush: the first-click table."""
        _open(browser_page, live, live.store(GRID))
        rows = {F: 3, E: 6, M: 9}
        for state, row in rows.items():
            _tool(browser_page, next(name for name, s in BRUSHES.items() if s == state))
            _drag(browser_page, [(row, 0), (row, 3)])
        before = _states(browser_page)
        assert {(r, c): _at(before, r, c) for r in rows.values() for c in range(4)} == {
            (row, c): state for state, row in rows.items() for c in range(4)}

        for k, (name, brush) in enumerate(BRUSHES.items()):
            _tool(browser_page, name)
            for row in rows.values():
                _cell(browser_page, row, k).click()
        after = _states(browser_page)
        got = {(name, state): _at(after, row, k)
               for k, name in enumerate(BRUSHES) for state, row in rows.items()}
        assert got == {(name, state): FIRST_CLICK[brush][state]
                       for name, brush in BRUSHES.items() for state in rows}
        # The "?" column, as the card spells it out.
        assert [got[(name, M)] for name in BRUSHES] == [F, E, U, U]

    def test_anything_between_two_clicks_makes_the_next_a_first_click(self, browser_page, live) -> None:
        """AC-5 — Black, a cell clicked twice (dark, white); then (a) a click on
        another cell, (b) Black pressed again, (c) a drag elsewhere, (d) undo
        then redo — and also a drag that changes nothing, Black picked by the
        keyboard, Ctrl+Z then Shift+Ctrl+Z, a hint, setBoard, a click on another
        cell in the same row, one in the same column, Reset opened and then
        cancelled with Keep marks: the next click is a first click
        (white -> dark). With nothing between it gives blank.
        A confirmed reset is checked with White (after a reset the cell is
        blank, where only White's first and repeat clicks differ)."""
        page = browser_page
        _open(page, live, live.store(GRID))

        def black_pressed_by_key():
            _button(page, "Black").focus()
            page.keyboard.press("Enter")

        def keyboard_undo_redo():
            page.locator("h1").click()
            page.keyboard.press("Control+z")
            page.keyboard.press("Shift+Control+z")

        def set_board():
            page.evaluate("window.puzzlePlayer.setBoard(window.puzzlePlayer.getBoard())")

        def reset_opened_and_cancelled():
            _button(page, "Reset").click()
            _button(page, "Keep marks").click()

        between = {
            "nothing": lambda: None,
            "(a) another cell": lambda: _cell(page, 14, 14).click(),
            "(b) Black again": lambda: _tool(page, "Black"),
            "(c) a drag elsewhere": lambda: _drag(page, [(13, 0), (13, 3)]),
            "(d) undo then redo": lambda: (_button(page, "Undo").click(), _button(page, "Redo").click()),
            "a drag that changes nothing": lambda: _drag(page, [(13, 0), (13, 3)]),
            "Black by keyboard": black_pressed_by_key,
            "Ctrl+Z, Shift+Ctrl+Z": keyboard_undo_redo,
            "a hint": lambda: _button(page, "Hint").click(),
            "setBoard": set_board,
            # The cell compare is on both axes: a click in the same row, and
            # one in the same column, each end the run (rows 10 and 11 below).
            "another cell in the same row": lambda: _cell(page, 10, 13).click(),
            "another cell in the same column": lambda: _cell(page, 14, 10).click(),
            "reset opened and cancelled (Keep marks)": reset_opened_and_cancelled,
        }
        third = {}
        for row, (name, step) in enumerate(between.items()):
            cell = _cell(page, row, 10)
            cell.click()
            cell.click()
            assert _at(_states(page), row, 10) == E, name
            step()
            cell.click()
            third[name] = _at(_states(page), row, 10)
        assert third == {name: (U if name == "nothing" else F) for name in between}

        # A confirmed reset (White: white, then Clear board, then White again).
        _tool(page, "White")
        _cell(page, 0, 12).click()
        assert _at(_states(page), 0, 12) == E
        _button(page, "Reset").click()
        _button(page, "Clear board").click()
        _cell(page, 0, 12).click()
        assert _marked(_states(page)) == {(0, 12): E}  # a repeat would give black

    def test_a_brush_change_restarts_the_sequence(self, browser_page, live) -> None:
        """AC-6 — Black on a blank cell, then White on it: white."""
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 5, 5).click()
        assert _marked(_states(browser_page)) == {(5, 5): F}
        _tool(browser_page, "White")
        _cell(browser_page, 5, 5).click()
        assert _marked(_states(browser_page)) == {(5, 5): E}

    def test_touch_taps_follow_the_brush(self, browser, live) -> None:
        """AC-7 — White, three real touch taps on a blank cell: white, blank, dark."""
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            page.evaluate("window.__types = []; document.addEventListener('pointerdown', (e) => window.__types.push(e.pointerType))")
            _button(page, "White").tap()
            seen = []
            for _ in range(3):
                page.touchscreen.tap(*_centre(page, 2, 2))
                seen.append(_at(_states(page), 2, 2))
            assert seen == [E, U, F]
            assert set(page.evaluate("window.__types")) == {"touch"}
        finally:
            context.close()

    def test_a_cancelled_gesture_makes_the_next_tap_a_first_click(self, browser, live) -> None:
        """The card's "a cancelled gesture" between two clicks: Black, two taps
        (dark, white), a touch that Chromium cancels (pointercancel), a tap:
        dark (a repeat would give blank). Without the cancel, blank."""
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            page.evaluate("window.__cancels = 0; document.addEventListener('pointercancel', () => { window.__cancels += 1; })")
            cdp = context.new_cdp_session(page)
            third = {}
            for cell, cancel in (((4, 4), True), ((6, 6), False)):
                x, y = _centre(page, *cell)
                page.touchscreen.tap(x, y)
                page.touchscreen.tap(x, y)
                assert _at(_states(page), *cell) == E
                if cancel:
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
                page.touchscreen.tap(x, y)
                third[cancel] = _at(_states(page), *cell)
            assert page.evaluate("window.__cancels") == 1
            assert third == {True: F, False: U}
        finally:
            context.close()

    def test_each_click_is_one_undo_step(self, browser_page, live) -> None:
        """AC-8 — Black, three clicks (dark, white, blank); three undos (white,
        dark, blank), three redos (dark, white, blank); then a first click: dark."""
        _open(browser_page, live, live.store(GRID))
        cell = _cell(browser_page, 7, 7)
        clicks, undos, redos = [], [], []
        for _ in range(3):
            cell.click()
            clicks.append(_at(_states(browser_page), 7, 7))
        for _ in range(3):
            _button(browser_page, "Undo").click()
            undos.append(_at(_states(browser_page), 7, 7))
        assert _is_disabled(browser_page, "Undo")
        for _ in range(3):
            _button(browser_page, "Redo").click()
            redos.append(_at(_states(browser_page), 7, 7))
        assert _is_disabled(browser_page, "Redo")
        assert (clicks, undos, redos) == ([F, E, U], [E, F, U], [F, E, U])
        cell.click()
        assert _marked(_states(browser_page)) == {(7, 7): F}

    def test_a_reload_starts_with_no_last_click(self, browser_page, live) -> None:
        """G-7 / CARD-185 — the last click is not saved: Black, two clicks
        (dark, white), reload (the board comes back from this browser's save),
        then a click: a first click, dark (a repeat would give blank)."""
        _open(browser_page, live, live.store(GRID))
        cell = _cell(browser_page, 3, 8)
        cell.click()
        cell.click()
        assert _marked(_states(browser_page)) == {(3, 8): E}
        browser_page.reload()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        assert _marked(_states(browser_page)) == {(3, 8): E}
        _cell(browser_page, 3, 8).click()
        assert _marked(_states(browser_page)) == {(3, 8): F}

    def test_the_page_copy_describes_the_new_click(self, browser_page, live) -> None:
        """AC-11 — the tool group is "Marking tool"; the hint names each colour
        brush's sequence and keeps the drag and Maybe sentences."""
        from playwright.sync_api import expect

        _open(browser_page, live, live.store(GRID))
        group = browser_page.get_by_role("group", name="Marking tool", exact=True)
        assert group.count() == 1
        expect(group).to_have_accessible_name("Marking tool")
        assert group.locator("[data-player-tool]").count() == 4
        hint = browser_page.locator("p.player-hint#puzzle-player-hint")
        assert hint.is_visible()
        text = " ".join(hint.text_content().split())
        assert "Click a cell to cycle" not in text and "for drags" not in text
        assert text == (
            "Click a cell to give it the selected tool's mark; click it again to go on "
            "(Black: black, white, blank; White: white, blank, black; Undecided: blank, black, white). "
            "Drag along a row or column to apply the selected tool. "
            "With Maybe, a click marks ? and a second click clears it."
        )


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
        _button(browser_page, "Clear board").click()  # CARD-162's in-page confirmation
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
        _cell(browser_page, 2, 2).click()  # CARD-189: a first click with Black makes white black
        assert _marked(_states(browser_page)) == {(0, 0): F, (2, 2): F}
        _button(browser_page, "Undo").click()
        assert _marked(_states(browser_page)) == {(0, 0): F, (2, 2): E}


# ==========================================================================
# AC-309 / AC-310 — keyboard and labels
# ==========================================================================

CONTROLS = ["Black", "White", "Undecided", "Maybe", "Undo", "Redo", "Reset"]

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
        browser_page.keyboard.press("Shift+Tab")  # CARD-162's confirmation: focus is on
        browser_page.keyboard.press("Enter")  # "Keep marks"; "Clear board" is before it
        assert _marked(_states(browser_page)) == {}
        press("Undo", "Enter")
        press("Reset", "Space")
        browser_page.keyboard.press("Shift+Tab")
        browser_page.keyboard.press("Space")
        assert _marked(_states(browser_page)) == {}

    @staticmethod
    def _tab_to(page, name):
        """Move keyboard focus to the control by Tab presses alone."""
        page.evaluate("document.activeElement && document.activeElement.blur()")
        for _ in range(80):
            page.keyboard.press("Tab")
            if page.evaluate(_FOCUSED) == name:
                return
        raise AssertionError(f"Tab never reached {name}")

    #: The tool selected (by mouse) before the key press — one whose drag
    #: would leave a different state, so a key that does nothing is visible.
    _PRIOR_TOOL = {"Black": "White", "White": "Undecided", "Undecided": "White"}

    @pytest.mark.parametrize("key", ["Enter", "Space"])
    @pytest.mark.parametrize("name", ["Black", "White", "Undecided"])
    def test_each_tool_acts_on_a_single_key_press(self, browser_page, live, name, key) -> None:
        """AC-310 — one Enter or one Space on a Tab-focused tool selects it, and
        the next drag uses it."""
        _open(browser_page, live, live.store(GRID))
        _drag(browser_page, [(0, 0), (0, 3)])  # Black: row 0 filled, so Undecided shows
        _tool(browser_page, self._PRIOR_TOOL[name])

        self._tab_to(browser_page, name)
        browser_page.keyboard.press(key)

        pressed = {t: _button(browser_page, t).get_attribute("aria-pressed") for t in TOOLS}
        assert pressed == {t: "true" if t == name else "false" for t in TOOLS}
        _drag(browser_page, [(0, 0), (0, 3)])
        expected = {(0, c): TOOLS[name] for c in range(4)} if TOOLS[name] != U else {}
        assert _marked(_states(browser_page)) == expected

    @pytest.mark.parametrize("key", ["Enter", "Space"])
    @pytest.mark.parametrize("name", ["Undo", "Redo", "Reset"])
    def test_each_history_control_acts_on_a_single_key_press(self, browser_page, live, name, key) -> None:
        """AC-310 — one Enter or one Space on a Tab-focused Undo / Redo / Reset
        acts, asserted after that single press."""
        _open(browser_page, live, live.store(GRID))
        _drag(browser_page, [(1, 2), (1, 6)])
        _cell(browser_page, 8, 8).click()
        drag = {(1, c): F for c in range(2, 7)}
        two = {**drag, (8, 8): F}
        assert _marked(_states(browser_page)) == two
        if name == "Redo":
            _button(browser_page, "Undo").click()
            assert _marked(_states(browser_page)) == drag

        self._tab_to(browser_page, name)
        browser_page.keyboard.press(key)

        after = _marked(_states(browser_page))
        if name == "Undo":
            assert after == drag  # the board minus the last stroke
        elif name == "Redo":
            assert after == two  # the undone stroke is back
        else:
            # CARD-162: Reset opens the in-page confirmation with focus on
            # "Keep marks"; one more press of the same key on "Clear board".
            assert after == two
            assert browser_page.evaluate(_FOCUSED) == "Keep marks"
            browser_page.keyboard.press("Shift+Tab")
            browser_page.keyboard.press(key)
            assert _marked(_states(browser_page)) == {}
            _button(browser_page, "Undo").click()  # the reset is one undoable step
            assert _marked(_states(browser_page)) == two

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

    @staticmethod
    def _press_layout_key(page, key, code, modifiers):
        """A real key press through CDP with an explicit key and code — what a
        non-US layout sends (Playwright's keyboard derives code from key)."""
        cdp = page.context.new_cdp_session(page)
        for kind in ("rawKeyDown", "keyUp"):
            cdp.send("Input.dispatchKeyEvent", {
                "type": kind, "key": key, "code": code,
                "windowsVirtualKeyCode": 90 if code == "KeyZ" else 89, "modifiers": modifiers,
            })

    def test_ctrl_z_works_when_the_layout_puts_a_non_latin_letter_on_z(self, browser_page, live) -> None:
        """F-002 — a Russian layout: the Z key reports key "я", code "KeyZ"."""
        ctrl, shift = 2, 8
        _open(browser_page, live, live.store(GRID))
        _drag(browser_page, [(1, 2), (1, 6)])
        _cell(browser_page, 8, 8).click()
        two = _marked(_states(browser_page))
        browser_page.locator("h1").click()

        self._press_layout_key(browser_page, "я", "KeyZ", ctrl)
        after_undo = _marked(_states(browser_page))
        self._press_layout_key(browser_page, "Я", "KeyZ", ctrl | shift)
        after_redo = _marked(_states(browser_page))

        assert after_undo == {(1, c): F for c in range(2, 7)}
        assert after_redo == two

    def test_a_latin_letter_on_the_z_position_is_that_letter_not_z(self, browser_page, live) -> None:
        """F-002 — a German layout: the KeyZ position reports "y"; Ctrl+Y must not undo."""
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 8, 8).click()
        browser_page.locator("h1").click()

        self._press_layout_key(browser_page, "y", "KeyZ", 2)

        assert _marked(_states(browser_page)) == {(8, 8): F}
        assert not _is_disabled(browser_page, "Undo")

    def test_a_tool_picked_mid_drag_applies_to_the_next_drag(self, browser_page, live) -> None:
        """F-003 — the drag keeps the tool it started with, in its preview and
        in the stroke recorded on release; the new tool governs the next drag."""
        _open(browser_page, live, live.store(GRID))
        browser_page.mouse.move(*_centre(browser_page, 0, 0))
        browser_page.mouse.down()
        browser_page.mouse.move(*_centre(browser_page, 0, 3), steps=4)

        _button(browser_page, "White").focus()
        browser_page.keyboard.press("Enter")
        assert _button(browser_page, "White").get_attribute("aria-pressed") == "true"

        browser_page.mouse.move(*_centre(browser_page, 0, 6), steps=4)
        preview = _marked(_states(browser_page))
        browser_page.mouse.up()
        recorded = _marked(_states(browser_page))
        _drag(browser_page, [(4, 0), (4, 2)])
        after_next = _marked(_states(browser_page))

        line = {(0, c): F for c in range(7)}
        assert preview == line
        assert recorded == line
        assert after_next == line | {(4, c): E for c in range(3)}


@pytest.mark.browser
class TestSolverMarking_ControlsStayHiddenWithoutABoard:
    """F-004 — the template's claim: the controls and the usage hint are shown
    only once the board is drawn, so no dead buttons appear without one."""

    def _assert_hidden(self, page):
        assert page.locator("#puzzle-player-controls").is_hidden()
        assert page.locator("#puzzle-player-hint").is_hidden()
        assert page.get_by_role("button", name="Undo", exact=True).count() == 0

    def test_a_refused_payload_shows_no_controls(self, browser_page, live) -> None:
        puzzle_id = live.store(GRID)

        def serve_corrupted(route):
            response = route.fetch()
            route.fulfill(response=response, body=_PAYLOAD.sub(_embed("null"), response.text()))

        browser_page.route(f"**/puzzle/{puzzle_id}/solve", serve_corrupted)
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        browser_page.get_by_role("alert").wait_for()

        self._assert_hidden(browser_page)

    def test_a_page_whose_script_never_ran_shows_no_controls(self, browser_page, live) -> None:
        browser_page.route("**/static/solver.js", lambda route: route.abort())
        browser_page.goto(f"{live.url}/puzzle/{live.store(GRID)}/solve")
        browser_page.wait_for_load_state("networkidle")

        assert browser_page.locator("[data-player-fallback]").is_visible()
        self._assert_hidden(browser_page)


# ==========================================================================
# AC-311 / ADR-0038/R2 — no request per mark; G-2 — no correctness shown
# ==========================================================================


def _twenty_strokes(page):
    """10 clicks and 10 drags (with tool changes between), mirrored in a model.
    Each click is a first click (CARD-189) with the tool picked before it."""
    model = _Model(SIDE, SIDE)
    tools = ["Black", "White", "Undecided"]
    tool = "Black"
    for k in range(10):
        r, c = k, (3 * k) % SIDE
        _cell(page, r, c).click()
        model.click(r, c, TOOLS[tool])
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
        _button(browser_page, "Clear board").click()  # CARD-162's in-page confirmation
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
  .replace(/ aria-(pressed|disabled)="(true|false)"/g, '')
  .replace(/ is-circled(?=[" ])/g, '')
  .replace(/(data-player-progress="?"?>)\\d+%</, '$1<')"""


@pytest.mark.browser
class TestSolverMarking_RevealsNoCorrectness:
    """G-2 — marking shows nothing but the marks. Narrowed by CARD-162, which
    adds the error count and the solved state (FR-044 AC-312..AC-317, tested in
    test_puzzle_solver_progress.py): correct marks that do not yet solve the
    puzzle still change nothing on the page but the cells. Narrowed again by
    CARD-188: a clue number's ``is-circled`` class is stripped too — clue
    circles are a read-only view of the marks, not of correctness.
    Narrowed again by CARD-187: the progress % reveals progress by the owner's
    choice, like the error count (only the count inside
    ``[data-player-progress]`` is stripped)."""

    def test_marking_all_but_the_last_solution_cell_changes_nothing_but_cell_states(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        before = browser_page.evaluate(_STRIPPED)

        expected = [F if cell else U for row in GRID for cell in row]
        last_r = max(r for r, row in enumerate(GRID) if any(row))
        last_c = max(c for c, cell in enumerate(GRID[last_r]) if cell)
        expected[last_r * SIDE + last_c] = U
        for r, row in enumerate(GRID):  # every filled run, by drag or click
            c = 0
            while c < SIDE:
                if row[c]:
                    end = c
                    while end + 1 < SIDE and row[end + 1]:
                        end += 1
                    if r == last_r and end == last_c:
                        end -= 1  # leave the very last solution cell undecided
                    if end > c:
                        _drag(browser_page, [(r, c), (r, end)])
                    elif end == c:
                        _cell(browser_page, r, c).click()
                    c = end + 1 if end >= c else c
                c += 1

        assert _states(browser_page) == expected
        assert browser_page.evaluate(_STRIPPED) == before

    def test_the_marking_code_reads_no_solution(self) -> None:
        """The input code and everything in solver_state.js before its
        Progress section (the board and the stroke/history functions) never
        read the solution; only CARD-162's progress code does (solver.js
        start(), solver_state.js errorCount / isSolved)."""
        code = re.sub(r"//[^\n]*", "", (_STATIC / "solver.js").read_text(encoding="utf-8"))
        marking = code[code.index("function wireMarking"):]
        assert "solution" not in marking
        text = (_STATIC / "solver_state.js").read_text(encoding="utf-8")
        before_progress = text[:text.index("// Progress against the solution")]
        assert "// Strokes and history" in before_progress
        assert "solution" not in re.sub(r"//[^\n]*", "", before_progress)


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
              const click = S.clickStroke(board, 1, 2, S.UNKNOWN);  // CARD-189: Undecided on white
              const reset = S.resetStroke(board);
              return {
                cycledGone: S.cycled === undefined,  // CARD-189: no tool-blind click cycle any more
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
                replayTwo: S.replay(S.createBoard(3, 2), [click, S.clickStroke(board, 0, 0, S.FILLED)]).cells,
              };
            }"""
        )
        assert out["cycledGone"]
        assert out["badTool"] == "RangeError"
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
              const h2 = S.record(h1, S.clickStroke(h1.board, 2, 2, S.FILLED));
              const u1 = S.undo(h2);
              const r1 = S.redo(u1);
              const fresh = S.record(u1, S.clickStroke(u1.board, 1, 1, S.FILLED));
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
    if (op[0] === 'click') h = S.record(h, S.clickStroke(h.board, op[1], op[2], op[3], op[4]));
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
    """A random mix: clicks with each brush, drags with each tool, resets, undo
    and redo runs. A click op is ["click", row, col, brush, repeat]: the driver
    keeps its own last-click memory (CARD-189) — the last click's (row, col,
    brush), cleared by every op that is not a click — and `repeat` says the
    click matches it. Seven in ten clicks that follow a click go back to that
    cell with that brush, so repeat clicks are common."""
    ops = []
    last = None
    while len(ops) < _EC_OPS:
        roll = rng.random()
        if roll < 0.30:
            if last is not None and rng.random() < 0.7:
                r, c, brush = last
            else:
                r, c, brush = rng.randrange(_EC_HEIGHT), rng.randrange(_EC_WIDTH), rng.choice([F, E, U, M])
            ops.append(["click", r, c, brush, (r, c, brush) == last])
            last = (r, c, brush)
            continue
        last = None
        if roll < 0.64:
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
    the board matches the independent Python model at every step. Since
    CARD-189 (AC-10) each click carries a brush and a repeat flag, and the
    model clicks by its own hand-written tables (FIRST_CLICK, REPEAT_CLICK)."""
    ops = _ec_ops(random.Random(35))
    kinds = [op[0] for op in ops]
    strokes = sum(kind in ("click", "drag", "reset") for kind in kinds)
    per_tool = {tool: sum(op[0] == "drag" and op[1] == tool for op in ops) for tool in (F, E, U)}
    per_brush = {brush: sum(op[0] == "click" and op[3] == brush for op in ops) for brush in (F, E, U, M)}
    repeats = sum(op[0] == "click" and op[4] for op in ops)
    assert strokes >= _EC_MIN_STROKES, strokes
    assert min(per_tool.values()) >= 80, per_tool
    assert min(per_brush.values()) >= 50 and repeats >= 50, (per_brush, repeats)
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
            model.click(op[1], op[2], op[3], op[4])
            assert model.board is not board_before, (index, op)  # CARD-189: every click is a step
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
