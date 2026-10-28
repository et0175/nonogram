"""CARD-267 — the player's crosshair (FR-044; ADR-0038/R1..R4).

The row and the column of the cell the pointer is on are tinted, and their
clue boxes with them, so the gaze does not slide onto a neighbouring line.
It is *rendering*: one class, ``.is-crossed``, on cells and clue boxes that
are already on the page (``static/solver.js`` ``wireCrosshair``, coloured by
``static/admin.css``). No board state, no ARIA, no request, no edit to
``static/solver_state.js``.

Everything a browser can see is driven by REAL input in Chromium — ``page.mouse``
for hover, CDP ``Input.dispatchTouchEvent`` for touch — never by
``puzzlePlayer.setBoard`` and never by dispatching a synthetic ``PointerEvent``
from the page: the card is about what a pointer does, so a hand-made event
would test the handler and not the behaviour. The expected crosshair is
derived in PYTHON from a full enumeration of the board's cells and clue boxes
(:func:`_expected`), never from the selector ``crossedParts`` uses — a check
that asked the production selector which boxes it would mark would agree with
it whatever it marked.

Fixtures (real Chromium refusing loudly when absent, ADR-0038/R8; a loopback
Flask panel over a temp SQLite store) are CARD-160's, imported below. This
file's page isolation is declared in ``tests/test_puzzle_solver_page.py``'s
``PAGE_ISOLATION``, like every other file of the family.
"""

from __future__ import annotations

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

#: The last line of ``wireCrosshair``, which bounds the slice of ``solver.js``
#: the G-5 structural check reads (see that test).
_FORGET = "return { forget: () => { crossed = null; } };"

U, F, E, M = "unknown", "filled", "empty", "maybe"

#: 15 x 15: one row gutter and one column gutter (``BIG_SIDE`` is 15, and
#: "big" is *past* it), so this is the plain board every test that is not
#: about doubling or redrawing uses.
GRID = _unique_grid(15, 15, seed=267)

#: AC-3's board. 16 on BOTH sides is past ``BIG_SIDE``, so both axes are
#: eligible for CARD-212's duplicate gutter; :data:`DOUBLED_VIEWPORT` is a
#: viewport roomy enough that both are actually afforded. The test asserts
#: that premise off the drawn board rather than trusting this comment.
DOUBLED_GRID = _unique_grid(16, 16, seed=2673)
DOUBLED_VIEWPORT = {"width": 1600, "height": 1200}

#: AC-7's board: 20 columns is past ``BIG_SIDE``, which is what makes
#: ``start()``'s ``isBig`` true and so makes a window resize REDRAW the board
#: rather than only re-measure it. A board big on neither side never redraws
#: at all, so it could not show the staleness this AC is about.
REDRAW_GRID = _unique_grid(20, 12, seed=2677)


# --------------------------------------------------------------------------
# Reading the board, and deriving what the crosshair should be
# --------------------------------------------------------------------------


#: The WHOLE board, with each cell's and each clue box's crosshair flag — not
#: the crossed ones only. Every assertion below is an equality against this
#: full enumeration, so "and no other cell or clue box does" (AC-1) is part of
#: the same comparison rather than a second, weaker check.
_BOARD = """() => {
  const table = document.querySelector('.player-board');
  const number = (name) => Number(table.style.getPropertyValue(name));
  return {
    size: [number('--player-cols'), number('--player-rows')],
    gutters: [number('--player-row-gutters'), number('--player-col-gutters')],
    cells: [...table.querySelectorAll('td.player-cell')].map((td) => [
      Number(td.dataset.row), Number(td.dataset.col),
      td.classList.contains('is-crossed')]),
    clues: [...table.querySelectorAll('th.player-clue')].map((th) => [
      th.classList.contains('is-row') ? 'row' : 'col', Number(th.dataset.line),
      th.classList.contains('is-crossed')]),
  };
}"""


def _board(page) -> dict:
    board = page.evaluate(_BOARD)
    width, height = board["size"]
    assert len(board["cells"]) == width * height, board["size"]
    return board


def _crossed(board) -> tuple[list, list]:
    """What carries the crosshair: the cells as (row, col), the clue boxes as
    (axis, line) — a LIST and not a set for the clue boxes, because a doubled
    axis must light both twins and a set would hide one of them."""
    return (
        sorted((r, c) for r, c, on in board["cells"] if on),
        sorted((axis, line) for axis, line, on in board["clues"] if on),
    )


def _expected(board, row, col) -> tuple[list, list]:
    """The crosshair for (row, col), derived here.

    The cells come from the board's SIZE — every column of ``row`` and every
    row of ``col`` — and not from any class or selector. The clue boxes come
    from the full box enumeration filtered on the card's own rule (this axis,
    this line), so a doubled axis yields both of its twins by arithmetic.
    """
    width, height = board["size"]
    cells = sorted({(row, k) for k in range(width)} | {(k, col) for k in range(height)})
    assert len(cells) == width + height - 1  # the two lines share their crossing
    clues = sorted(
        (axis, line)
        for axis, line, _on in board["clues"]
        if (axis, line) in (("row", row), ("col", col))
    )
    row_gutters, col_gutters = board["gutters"]
    assert len(clues) == row_gutters + col_gutters, (clues, board["gutters"])
    return cells, clues


#: Chromium spells a computed background two ways, and a crossed board shows
#: both: ``rgb(241, 235, 221)`` for a plain token and ``color(srgb 0.24 0.26
#: 0.31)`` for a ``color-mix()``. Both are read here, into one 0..1 scale, so
#: a brightness comparison is not quietly comparing 0.24 against 241.
_RGB = re.compile(r"^rgba?\(([^)]*)\)$")
_SRGB = re.compile(r"^color\(srgb ([^)/]*)\)$")


def _luma(value: str) -> float:
    """The mean of a computed colour's three sRGB channels, on 0..1."""
    srgb = _SRGB.match(value)
    if srgb:
        channels = [float(n) for n in srgb.group(1).split()[:3]]
    else:
        plain = _RGB.match(value)
        assert plain, f"unrecognised computed colour: {value!r}"
        channels = [float(n) / 255 for n in plain.group(1).replace("/", " ").split(",")[:3]]
    assert all(0.0 <= channel <= 1.0 for channel in channels), (value, channels)
    return sum(channels) / 3


def _cell(page, row, col):
    return page.locator(f'td.player-cell[data-row="{row}"][data-col="{col}"]')


def _centre(page, row, col):
    box = _cell(page, row, col).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _hover(page, row, col):
    page.mouse.move(*_centre(page, row, col))


def _states(page) -> list[str]:
    seen = page.evaluate(
        """() => ({ drawn: [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state),
                    board: [...window.puzzlePlayer.getBoard().cells] })"""
    )
    assert seen["drawn"] == seen["board"]
    return seen["drawn"]


def _button(page, name):
    return page.get_by_role("button", name=name, exact=True)


def _tool(page, name):
    """Pick a brush through the menu (CARD-194), by mouse."""
    page.locator("#puzzle-player-tool-trigger").click()
    page.get_by_role("menuitemradio", name=name, exact=True).click()


def _touch(cdp, kind, x=None, y=None):
    points = [] if x is None else [{"x": x, "y": y}]
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})


# ==========================================================================
# AC-1 — the hovered cell's row, column and clue boxes light, and nothing else
# ==========================================================================


@pytest.mark.browser
class TestSolverCrosshair_RowColumnAndCluesLight:
    """AC-1 — hovering (r, c) marks row r, column c and their clue boxes.

    The equality is against the whole board (:data:`_BOARD`), so the "and no
    other cell or clue box does" half is the same assertion and cannot drift
    out of it.
    """

    def test_the_hovered_rows_column_and_clues_carry_the_marker(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        assert _crossed(_board(browser_page)) == ([], []), "a fresh load shows a crosshair"

        _hover(browser_page, 4, 11)

        board = _board(browser_page)
        assert _crossed(board) == _expected(board, 4, 11)

    def test_the_four_cell_states_stay_apart_under_the_tint(self, browser_page, live) -> None:
        """Card item 5 — the tint must keep all four ``data-state`` looks
        plainly distinguishable, and must not be confusable with CARD-188's
        clue circles.

        Three cells of ONE row are painted by real clicks, one per brush
        (Black, White, Maybe), a fourth is left Clear, and then that row is
        hovered: so all four looks are read under the crosshair, in the same
        board, in the same row.

        What "plainly apart" is, measured rather than asserted by eye, and
        narrowed to what the shipped CSS actually does: the tint is ONE
        background, so three of the four states share a ground and are told
        apart by their ``::after`` mark (nothing, the white dot, the "?"),
        while ``filled`` is told apart by its ground. So the claim is two
        measurements, not one — three distinct marks on the light states, and
        a filled ground darker than all three of them by much more than a
        rounding error. A tint that flattened the dot or the "?" away, or that
        lightened the filled cell toward the paper, fails one of them.

        Not confusable with a circle is structural rather than perceptual:
        a circle is a border on the numeral's ``::before`` and the crosshair
        is a cell/box BACKGROUND, so the set of circled numbers is asserted
        unchanged by the hover (``TestSolverCrosshair_IsPureView`` asserts the
        same thing over a long sequence of hovers).
        """
        _open(browser_page, live, live.store(GRID))
        row, painted = 6, {}
        for col, (brush, state) in enumerate({"Black": F, "White": E, "Maybe": M}.items()):
            _tool(browser_page, brush)
            _cell(browser_page, row, col).click()
            painted[state] = col
        painted[U] = 3  # never clicked
        assert {s: _states(browser_page)[row * 15 + c] for s, c in painted.items()} == {
            F: F, E: E, M: M, U: U
        }

        _hover(browser_page, row, 9)

        look = browser_page.evaluate(
            """([row, cols]) => Object.fromEntries(Object.entries(cols).map(([state, col]) => {
              const cell = document.querySelector(
                `td.player-cell[data-row="${row}"][data-col="${col}"]`);
              const style = getComputedStyle(cell);
              return [state, { crossed: cell.classList.contains('is-crossed'),
                               background: style.backgroundColor,
                               mark: getComputedStyle(cell, '::after').content }];
            }))""",
            [row, painted],
        )

        assert all(seen["crossed"] for seen in look.values()), look
        # The three light states: told apart by their mark, under the tint.
        marks = {state: look[state]["mark"] for state in (U, E, M)}
        assert len(set(marks.values())) == 3, marks
        # And `filled` by its ground, by a margin and not a rounding error.
        luma = {state: _luma(look[state]["background"]) for state in look}
        assert max(luma.values()) == max(luma[s] for s in (U, E, M)), luma
        assert min(luma[s] for s in (U, E, M)) - luma[F] > 0.4, luma

    def test_the_tint_changes_the_ground_of_both_a_cell_and_a_clue_box(
        self, browser_page, live
    ) -> None:
        """AC-1's class has to be WORTH something: three CSS rules turn it into
        a tint, and a class nothing paints is a crosshair nobody sees.

        So this reads the computed background of one cell and one clue box of
        the hovered lines, before and after the hover, and of a cell and a clue
        box OFF them in the same reading. The crossed pair must change and
        gain a ground distinct from the uncrossed pair's; the uncrossed pair
        must not move at all. Without it, every other assertion in this file
        would still hold with ``admin.css`` carrying no crosshair rule — the
        classes would be in all the right places and the board would look
        exactly as it did before.
        """
        _open(browser_page, live, live.store(GRID))
        grounds = """([row, col]) => {
          const ground = (selector) =>
            getComputedStyle(document.querySelector(selector)).backgroundColor;
          return {
            cell: ground(`td.player-cell[data-row="${row}"][data-col="${col}"]`),
            clue: ground(`th.player-clue.is-row[data-line="${row}"]`),
            otherCell: ground(`td.player-cell[data-row="${row + 2}"][data-col="${col + 2}"]`),
            otherClue: ground(`th.player-clue.is-row[data-line="${row + 2}"]`),
          };
        }"""
        before = browser_page.evaluate(grounds, [3, 5])

        _hover(browser_page, 3, 5)

        after = browser_page.evaluate(grounds, [3, 5])

        assert after["cell"] != before["cell"], (before, after)
        assert after["clue"] != before["clue"], (before, after)
        assert after["otherCell"] == before["otherCell"], (before, after)
        assert after["otherClue"] == before["otherClue"], (before, after)
        # And the tint is one ground shared by the cell and the clue box of
        # the crossed lines, which is what makes the cross read as one shape.
        assert after["cell"] == after["clue"], after


# ==========================================================================
# AC-2 — the crosshair follows the pointer, and costs nothing inside one cell
# ==========================================================================


#: Counts class-attribute mutations anywhere in the board, so "a move within
#: the same cell does nothing" is a measurement of DOM WRITES and not of what
#: the board happens to look like afterwards (which is identical either way).
_WATCH = """() => {
  window.__crossWrites = 0;
  window.__crossWatcher = new MutationObserver((records) => {
    window.__crossWrites += records.length;
  });
  window.__crossWatcher.observe(document.querySelector('.player-board'),
    { attributes: true, subtree: true, attributeFilter: ['class'] });
}"""


@pytest.mark.browser
class TestSolverCrosshair_FollowsThePointer:
    """AC-2 — moving to (r2, c2) clears the old lines and marks exactly the new."""

    def test_a_move_clears_the_old_lines_and_marks_the_new(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))

        _hover(browser_page, 2, 3)
        first = _board(browser_page)
        _hover(browser_page, 11, 8)
        second = _board(browser_page)

        # Two equalities against two independently derived crosshairs, and
        # that is the whole claim: (2, 3) and (11, 8) share neither a row nor
        # a column, so the second equality holding is already "the old lines
        # are cleared". A third assert that the two differ would be derived
        # from these two and could not fail on its own.
        assert _crossed(first) == _expected(first, 2, 3)
        assert _crossed(second) == _expected(second, 11, 8)

    def test_a_move_inside_one_cell_writes_nothing(self, browser_page, live) -> None:
        """Card item 4 — a move within the same cell does nothing.

        The observer is its own positive control: the last move crosses into a
        neighbouring cell and MUST be seen. A reading of "0 writes" from an
        observer that could not see a write at all would say nothing.
        """
        _open(browser_page, live, live.store(GRID))
        _hover(browser_page, 7, 7)
        box = _cell(browser_page, 7, 7).bounding_box()
        assert box["width"] >= 8, box  # room inside the cell for three distinct points
        browser_page.evaluate(_WATCH)

        for dx, dy in ((-2, -2), (2, 2), (0, 1)):
            browser_page.mouse.move(
                box["x"] + box["width"] / 2 + dx, box["y"] + box["height"] / 2 + dy)
        inside = browser_page.evaluate("window.__crossWrites")
        _hover(browser_page, 7, 8)
        after_leaving = browser_page.evaluate("window.__crossWrites")

        assert inside == 0
        assert after_leaving > 0, "the observer sees no write even for a real move"


# ==========================================================================
# AC-3 — both twins of a doubled gutter light
# ==========================================================================


@pytest.mark.browser
class TestSolverCrosshair_LightsBothTwinsOnADoubledBoard:
    """AC-3 — on CARD-212's doubled gutters, BOTH twins of the row clue and
    BOTH twins of the column clue carry the marker.

    ``crossedParts`` selects clue boxes by axis + ``data-line``, which is
    exactly why: a duplicate carries its twin's line number, so a selector
    keyed on it cannot reach one and miss the other (the same construction
    ``clueNumbersOf`` relies on for the circles).
    """

    def test_a_doubled_board_lights_two_row_boxes_and_two_column_boxes(
        self, browser_page, live
    ) -> None:
        browser_page.set_viewport_size(DOUBLED_VIEWPORT)
        _open(browser_page, live, live.store(DOUBLED_GRID))
        premise = _board(browser_page)
        assert premise["gutters"] == [2, 2], (
            f"this board drew {premise['gutters']} gutters at "
            f"{DOUBLED_VIEWPORT}, so it is not the doubled board AC-3 needs"
        )

        _hover(browser_page, 5, 9)

        board = _board(browser_page)
        cells, clues = _crossed(board)
        assert (cells, clues) == _expected(board, 5, 9)
        assert clues == [("col", 9), ("col", 9), ("row", 5), ("row", 5)], clues


# ==========================================================================
# AC-4 — touch: it follows the finger and stays after pointerup
# ==========================================================================


@pytest.mark.browser
class TestSolverCrosshair_TouchKeepsTheLastCell:
    """AC-4 — a touch drag crosses the cell under the finger, still marks
    exactly as today, and leaves the crosshair on the last touched cell.

    A phone has no hover, so a crosshair that left with the finger would never
    be seen between taps. The mechanism is one exemption in the ``pointerleave``
    handler: a released touch pointer leaves the stage at once.
    """

    def test_a_touch_drag_crosses_the_finger_and_the_crosshair_stays(self, browser, live) -> None:
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            # Region on: a touch drag marks only while it is armed (CARD-194
            # target behaviour #8/#10), and AC-4 asks for the marking to be
            # exactly today's as well as for the crosshair.
            page.get_by_role("button", name="Region", exact=True).tap()
            (x0, y0) = _centre(page, 1, 2)
            (x1, _y1) = _centre(page, 1, 6)

            _touch(cdp := context.new_cdp_session(page), "touchStart", x0, y0)
            seen = []
            for k in range(1, 9):
                _touch(cdp, "touchMove", x0 + (x1 - x0) * k / 8, y0)
                seen.append(_crossed(_board(page)))
            during = _board(page)
            _touch(cdp, "touchEnd")
            after = _board(page)

            assert _crossed(during) == _expected(during, 1, 6), "the finger's cell is not crossed"
            assert _crossed(after) == _crossed(during), "pointerup cleared the touch crosshair"
            # It FOLLOWED the finger rather than being painted once or only at
            # the ends. The drag runs from the centre of column 2 to the
            # centre of column 6 in eight equal steps, so the cell under the
            # finger changes four times after the first step (measured: the
            # column lines seen across the eight moves are 3, 4, 5 and 6 —
            # column 2 is crossed by the touchStart, before the first move).
            # Asserted as "at least four, ending on the finger's last cell"
            # rather than as that exact set: how an interpolated half-cell
            # step rounds at a cell boundary is Chromium's business, and a
            # bound is what this AC needs.
            columns = [line for _cells, clues in seen for axis, line in clues if axis == "col"]
            assert len(set(columns)) >= 4, columns
            assert columns == sorted(columns) and columns[-1] == 6, columns
            # And the drag marked exactly as today.
            assert {
                (i // 15, i % 15): s for i, s in enumerate(_states(page)) if s != U
            } == {(1, c): F for c in range(2, 7)}
        finally:
            context.close()

    def test_a_single_tap_leaves_the_crosshair_on_the_tapped_cell(self, browser, live) -> None:
        """A tap can reach ``pointerup`` without one ``pointermove``, which is
        why the crosshair follows ``pointerdown`` as well."""
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            page.touchscreen.tap(*_centre(page, 9, 4))

            board = _board(page)

            assert _crossed(board) == _expected(board, 9, 4)
        finally:
            context.close()


# ==========================================================================
# AC-5 — the hover crosshair clears when the pointer leaves the board
# ==========================================================================


@pytest.mark.browser
class TestSolverCrosshair_ClearsWhenThePointerLeaves:
    """AC-5 — the mouse leaving the board clears the crosshair.

    "Leaving" is leaving ``.player-stage``: a pointer still over the board but
    not over a cell — a clue box, the stage's own padding — keeps the
    crosshair where it was, on purpose (the card's whole point is that looking
    from a cell to its clue must not put the line out). Both halves are
    asserted here, because the second is what makes the first a boundary and
    not a blanket.
    """

    def test_leaving_the_stage_clears_it_and_a_clue_box_does_not(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _hover(browser_page, 8, 8)
        assert _crossed(_board(browser_page))[0], "nothing to clear"

        clue = browser_page.locator('th.player-clue.is-row[data-line="8"]').bounding_box()
        browser_page.mouse.move(clue["x"] + clue["width"] / 2, clue["y"] + clue["height"] / 2)
        over_the_clue = _board(browser_page)
        stage = browser_page.locator(".player-stage").bounding_box()
        browser_page.mouse.move(stage["x"] + stage["width"] / 2, max(stage["y"] - 20, 1))
        left = _board(browser_page)

        assert _crossed(over_the_clue) == _expected(over_the_clue, 8, 8)
        assert _crossed(left) == ([], [])

    def test_entering_and_leaving_without_ever_touching_a_cell_is_quiet(
        self, browser_page, live
    ) -> None:
        """The leave with nothing to clear, which is reachable from a fresh
        load: the pointer crosses a clue gutter and goes out again, so
        ``pointerleave`` arrives with no crosshair ever made.

        It is not a no-op path — unpainting a crosshair that is ``null`` is a
        ``TypeError`` in a pointer handler, i.e. a thrown error on an ordinary
        mouse movement over a freshly loaded board. So the page is watched for
        one rather than only the class list being checked.
        """
        problems: list[str] = []
        browser_page.on("pageerror", lambda error: problems.append(str(error)))
        browser_page.on(
            "console",
            lambda message: message.type == "error" and problems.append(message.text))
        _open(browser_page, live, live.store(GRID))

        clue = browser_page.locator('th.player-clue.is-col[data-line="4"]').bounding_box()
        browser_page.mouse.move(clue["x"] + clue["width"] / 2, clue["y"] + clue["height"] / 2)
        stage = browser_page.locator(".player-stage").bounding_box()
        browser_page.mouse.move(stage["x"] + stage["width"] / 2, max(stage["y"] - 20, 1))
        browser_page.wait_for_timeout(100)

        assert _crossed(_board(browser_page)) == ([], [])
        assert problems == []


# ==========================================================================
# AC-6 — a view and nothing else
# ==========================================================================


@pytest.mark.browser
class TestSolverCrosshair_IsPureView:
    """AC-6 — hovering changes no board state, records nothing and saves
    nothing; and G-3: it issues no request either."""

    def test_a_long_hover_sequence_changes_no_state_no_history_and_no_save(
        self, browser_page, live
    ) -> None:
        puzzle = live.store(GRID)
        _open(browser_page, live, puzzle)
        before = {
            "states": _states(browser_page),
            "undo": _button(browser_page, "Undo").get_attribute("aria-disabled"),
            "redo": _button(browser_page, "Redo").get_attribute("aria-disabled"),
            "counters": browser_page.locator("#puzzle-player-controls").inner_text(),
            "circled": browser_page.evaluate(
                "[...document.querySelectorAll('.player-clue-num')]"
                ".map((n) => n.classList.contains('is-circled'))"),
            "save": browser_page.evaluate("Object.entries(localStorage)"),
            "serialized": browser_page.evaluate("window.puzzlePlayer.getBoard()"),
        }

        for row in range(0, 15, 2):
            for col in range(0, 15, 3):
                _hover(browser_page, row, col)
        crossed = _crossed(_board(browser_page))

        assert crossed != ([], []), "no crosshair was made, so nothing was proved"
        assert before["states"] == [U] * 225
        assert {
            "states": _states(browser_page),
            "undo": _button(browser_page, "Undo").get_attribute("aria-disabled"),
            "redo": _button(browser_page, "Redo").get_attribute("aria-disabled"),
            "counters": browser_page.locator("#puzzle-player-controls").inner_text(),
            "circled": browser_page.evaluate(
                "[...document.querySelectorAll('.player-clue-num')]"
                ".map((n) => n.classList.contains('is-circled'))"),
            "save": browser_page.evaluate("Object.entries(localStorage)"),
            "serialized": browser_page.evaluate("window.puzzlePlayer.getBoard()"),
        } == before

    def test_hovering_issues_no_request(self, browser_page, live) -> None:
        """G-3 / ADR-0038/R2 — none per mark, and none per hover either.

        There is no *mechanism* that suppresses a request: the crosshair
        simply never asks for anything, which is a property of the code and
        not a guard in it. So the reading needs its instrument proved: the
        listener is installed before the page is opened and must see the
        page's own requests, and only then is it trusted to report zero over
        the hovers.
        """
        requests: list[str] = []
        browser_page.context.on("request", lambda request: requests.append(request.url))
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        loading = len(requests)

        for row in range(0, 15, 2):
            for col in range(0, 15, 2):
                _hover(browser_page, row, col)
        browser_page.wait_for_timeout(250)

        assert loading > 0, "the request listener saw not even the page it loaded"
        assert _crossed(_board(browser_page)) != ([], [])
        assert requests[loading:] == []

    def test_the_state_module_knows_nothing_of_the_crosshair(self) -> None:
        """G-5, structural — ``solver_state.js`` is not edited by this card.

        A crosshair that needed the state module would have been designed
        wrong (ADR-0038/R4), so the claim is checked rather than narrated: the
        module mentions nothing of it, and the renderer's crosshair code
        imports nothing (it is handed the stage and reads the live DOM).
        """
        state = (_STATIC / "solver_state.js").read_text(encoding="utf-8")
        # The crosshair's own names, and not a bare "crossed": that word turns
        # up honestly in prose about crossing a breakpoint, and a tripwire
        # that fires on a future card's comment is a tripwire somebody
        # disables.
        for word in ("crosshair", "Crosshair", "is-crossed", "crossedParts"):
            assert word not in state, word

        renderer = (_STATIC / "solver.js").read_text(encoding="utf-8")
        # The crosshair's own code, from the first of its two functions to the
        # last line of the second — bounded by what this card wrote, so the
        # slice cannot quietly grow into the marking code's comments (which do
        # name solver_state.js, legitimately, and once did fail this).
        start = renderer.index("function crossedParts")
        crosshair = renderer[start:renderer.index(_FORGET, start) + len(_FORGET)]
        assert "function wireCrosshair" in crosshair
        assert crosshair.count("function ") >= 2, crosshair
        for word in ("import", "solver_state", "serializeState", "record(", "fetch"):
            assert word not in crosshair, word


# ==========================================================================
# AC-7 — no stale marker after a redraw
# ==========================================================================


@pytest.mark.browser
class TestSolverCrosshair_NoStaleMarkerAfterRedraw:
    """AC-7 — a redraw leaves no half-painted crosshair behind.

    Both halves matter and the second is the sharper one. A redraw replaces
    every cell and clue box, so nothing painted can survive it on its own;
    what CAN survive is the renderer's MEMORY of where the crosshair was, and
    a remembered position with nothing painted means the next move onto that
    same cell reads "already there" and paints nothing at all. So this
    re-hovers the same cell after the redraw and asserts the full crosshair
    comes back.
    """

    def test_a_redraw_clears_the_marker_and_the_same_cell_crosses_again(
        self, browser_page, live
    ) -> None:
        browser_page.set_viewport_size({"width": 1280, "height": 720})
        _open(browser_page, live, live.store(REDRAW_GRID))
        drawn = browser_page.evaluate(
            "performance.getEntriesByName('nonogram-player-board-draw').length")
        _hover(browser_page, 5, 7)
        assert _crossed(_board(browser_page))[0], "nothing to go stale"

        browser_page.set_viewport_size({"width": 880, "height": 700})
        browser_page.wait_for_function(
            "(was) => performance.getEntriesByName('nonogram-player-board-draw').length > was",
            arg=drawn)
        redrawn = _board(browser_page)
        _hover(browser_page, 5, 7)
        again = _board(browser_page)

        assert _crossed(redrawn) == ([], []), "a marker survived the redraw"
        assert _crossed(again) == _expected(again, 5, 7)


# ==========================================================================
# AC-8 — no ARIA, anywhere
# ==========================================================================


#: Every ARIA attribute and role in the player, element by element, in
#: document order. Not "the attributes of the crossed cells": the claim is
#: that hovering adds no ARIA ANYWHERE, so the whole player is read.
#:
#: tagName and id, and deliberately NOT className: the crosshair IS a class,
#: so a probe that read the class list would report its own subject as an
#: ARIA change and this test would pass on nothing but that. Position in the
#: document-ordered list is what identifies an element here.
_ARIA = """() => [...document.querySelectorAll('#puzzle-player, #puzzle-player *, '
  + '#puzzle-player-controls, #puzzle-player-controls *')].map((el) => [
    el.tagName, el.id,
    el.getAttributeNames().filter((n) => n === 'role' || n.startsWith('aria-'))
      .sort().map((n) => `${n}=${el.getAttribute(n)}`),
  ])"""


@pytest.mark.browser
class TestSolverCrosshair_AddsNoAria:
    """AC-8, a11y half — the crosshair is decorative and redundant by nature
    (it repeats where the pointer already is), so it announces nothing and
    changes nothing a screen reader reads per cell or per clue."""

    def test_hovering_adds_no_aria_attribute_and_announces_nothing(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        before = browser_page.evaluate(_ARIA)
        assert before, "the ARIA probe found no elements at all"

        for row, col in ((0, 0), (7, 7), (14, 14), (3, 12)):
            _hover(browser_page, row, col)

        assert _crossed(_board(browser_page)) != ([], [])
        assert browser_page.evaluate(_ARIA) == before
        assert browser_page.locator("#puzzle-player-announce").inner_text() == ""
