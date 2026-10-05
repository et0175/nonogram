"""CARD-188 — the puzzle player circles a clue number once the marks settle it.

The rule (``static/solver_state.js`` ``circledNumbers`` / ``circledClues``)
reads only the player's marks and the payload's clues. In a line a cell is
dark (FILLED), white (EMPTY) or undecided; a closed run is a maximal dark run
with a white cell or the edge on each side. Rule A walks in from each edge,
circling a closed run whose length is the next clue number from that edge
and stopping at anything else; rule B circles every number when the closed
runs are exactly the clue. A "0" clue is circled only when every cell is
white.

What each tier shows:

* **Pure module, in the browser** (``await import('/static/solver_state.js')``):
  the card's examples table (AC-2); the safety property against a brute force
  built here on ``tests/helpers/brute_force_oracle.py`` ``line_candidates``
  (AC-1); fully marked lines (AC-3); a board is its lines, and transposes
  (AC-4). Corpora are seeded ``random.Random`` (no ``hypothesis``), each
  asserting its own minimum counts.
* **Player page** (real clicks and drags, CARD-160's loopback panel over a
  temp SQLite store): circles follow every commit and not a drag's preview
  (AC-5, AC-7), the owner's "2 2" case stays uncircled (AC-6), circling moves
  nothing (AC-8), and the circle is a visible round outline (AC-9).
"""

from __future__ import annotations

import random

import pytest

from tests.helpers.brute_force_oracle import line_candidates
from tests.test_puzzle_solver_marking import E, F, U, _button, _cell, _centre, _drag, _states
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _tight_row,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_progress import _set, _watch_problems

# --------------------------------------------------------------------------
# The brute force (AC-1), written apart from solver_state.js
# --------------------------------------------------------------------------

_MARK = {"D": True, "W": False}


def _runs(pattern):
    """(start, end) of each run of True, left to right."""
    runs, start = [], None
    for index, value in enumerate([*pattern, False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            runs.append((start, index))
            start = None
    return runs


def _brute_circles(clue, marks):
    """The brute force of "What to implement" 6, or None when no placement
    of ``clue`` agrees with the dark (D) and white (W) marks.

    Number i is circled iff run i covers the same cells in every agreeing
    placement and those cells are a closed run of the marks. A "0" clue is
    circled iff every cell is white.
    """
    clue = tuple(clue)
    placements = [
        p for p in line_candidates(clue, len(marks))
        if all(m not in _MARK or _MARK[m] == v for m, v in zip(marks, p))
    ]
    if not placements:
        return None
    if clue == (0,):
        return [all(m == "W" for m in marks)]
    spans = [set() for _ in clue]
    for p in placements:
        for i, run in enumerate(_runs(p)):
            spans[i].add(run)
    circled = []
    for (only, *rest) in (list(s) for s in spans):
        start, end = only
        closed = (
            not rest
            and all(m == "D" for m in marks[start:end])
            and (start == 0 or marks[start - 1] == "W")
            and (end == len(marks) or marks[end] == "W")
        )
        circled.append(closed)
    return circled


# --------------------------------------------------------------------------
# Calling the pure module
# --------------------------------------------------------------------------

#: D dark, W white, anything else undecided ("." in the card's table).
_NUMBERS = """async (lines) => {
  const S = await import('/static/solver_state.js');
  const codes = { D: S.FILLED, W: S.EMPTY, '.': S.UNKNOWN };
  return lines.map(([clue, marks]) => {
    const got = S.circledNumbers(clue, Object.freeze([...marks].map((ch) => codes[ch])));
    if (!Object.isFrozen(got)) throw new Error('not frozen');
    return [...got];
  });
}"""


def _numbers(page, lines):
    got = page.evaluate(_NUMBERS, [[list(clue), marks] for clue, marks in lines])
    assert len(got) == len(lines)
    return got


def _blank_page(page, live):
    """Any player page: only its /static/solver_state.js is used."""
    _open(page, live, live.store(_player_grid()))


# ==========================================================================
# AC-2 — the examples table
# ==========================================================================


@pytest.mark.browser
class TestSolverClues_RuleExamples:
    """circledNumbers on the card's examples table, row by row."""

    ROWS = [
        # (clue, marks, circled) — "What to implement" 4
        ((2, 2), "...WDDW...", [False, False]),  # the owner's example
        ((2, 2), "DDW.......", [True, False]),
        ((2, 2), "WDDWWDDW..", [True, True]),
        ((2, 2), "DD.DD.....", [False, False]),  # no white dots, no circle
        ((1, 1), ".WDW.WDW.", [True, True]),  # rule B
        ((1, 1, 1), "WDWD......", [True, False, False]),
        ((3, 1), "DDW....WDW", [False, True]),  # one walk stops, not the other
        ((3, 1), ".WDDDW....", [False, False]),  # no length-only matching
        ((0,), "WWWWW", [True]),
        ((0,), "WW.WW", [False]),
    ]

    def test_each_row_circles_what_the_table_says(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        got = _numbers(browser_page, [(clue, marks) for clue, marks, _ in self.ROWS])
        assert got == [circled for _, _, circled in self.ROWS]


# ==========================================================================
# AC-1 — never circles what the brute force does not
# ==========================================================================


def _safety_corpus(rng, size):
    """Lines of length 1..12: the clue from a random solution line (some
    empty), marks revealing each cell with a per-line probability, a few
    revealed marks flipped, some lines all white, and some decided except
    for their two edge cells."""
    lines = []
    for k in range(size):
        length = rng.randint(1, 12)
        density = 0.0 if k % 12 == 0 else rng.choice((0.25, 0.45, 0.6, 0.8))
        solution = [rng.random() < density for _ in range(length)]
        clue = tuple(_encode(solution))
        if k % 12 == 6:
            marks = "W" * length
        elif k % 12 == 3:  # decided but for its edge cells: rule A cannot start
            marks = "." + "".join("D" if filled else "W" for filled in solution[1:-1]) + "." * (length > 1)
        else:
            reveal = rng.choice((0.3, 0.6, 0.85, 1.0))
            flip = rng.choice((0.0, 0.0, 0.03, 0.1))
            marks = ""
            for filled in solution:
                if rng.random() >= reveal:
                    marks += "."
                else:
                    marks += "D" if filled != (rng.random() < flip) else "W"
        lines.append((clue, marks))
    return lines


@pytest.mark.browser
def test_PropertyTest_SolverClues_NeverCirclesWhatBruteForceDoesNot(browser_page, live) -> None:
    """AC-1 — on every line whose marks fit at least one placement of its
    clue, each number circledNumbers circles is circled by the brute force."""
    _blank_page(browser_page, live)
    lines = _safety_corpus(random.Random(188), 6000)
    got = []
    for chunk in range(0, len(lines), 2000):
        got += _numbers(browser_page, lines[chunk:chunk + 2000])

    fitting = with_circle = zero_or_white = brute_only = 0
    violations = []
    for (clue, marks), rule in zip(lines, got):
        assert len(rule) == len(clue)
        brute = _brute_circles(clue, marks)
        if brute is None:
            continue
        fitting += 1
        with_circle += any(rule)
        zero_or_white += clue == (0,) or set(marks) == {"W"}
        brute_only += any(b and not r for r, b in zip(rule, brute))
        if any(r and not b for r, b in zip(rule, brute)):
            violations.append((clue, marks, rule, brute))
    assert violations == []
    assert fitting >= 3000, fitting
    assert with_circle >= 1000, with_circle
    assert zero_or_white >= 300, zero_or_white
    assert brute_only >= 100, brute_only


# ==========================================================================
# AC-3 — a fully marked line circles everything
# ==========================================================================


@pytest.mark.browser
def test_PropertyTest_SolverClues_AFullyMarkedLineCirclesEverything(browser_page, live) -> None:
    """AC-3 — marks equal to the solution line, every other cell white."""
    _blank_page(browser_page, live)
    rng = random.Random(1883)
    lines = []
    for k in range(600):
        length = rng.randint(1, 30)
        density = 0.0 if k % 20 == 0 else rng.random()
        solution = [rng.random() < density for _ in range(length)]
        lines.append((tuple(_encode(solution)), "".join("D" if s else "W" for s in solution)))
    assert len(lines) >= 500
    assert sum(len(clue) >= 3 for clue, _ in lines) >= 100
    got = _numbers(browser_page, lines)
    assert [i for i, circled in enumerate(got) if not all(circled)] == []


# ==========================================================================
# AC-4 — a board is its lines
# ==========================================================================

_BOARD = """async ({ width, height, rows, columns, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { D: S.FILLED, W: S.EMPTY, '.': S.UNKNOWN };
  const board = (w, h, cells) => Object.freeze({ width: w, height: h, cells: Object.freeze(cells) });
  const plain = (c) => ({ rows: c.rows.map((l) => [...l]), columns: c.columns.map((l) => [...l]) });
  return boards.map((text) => {
    const cells = [...text].map((ch) => codes[ch]);
    const b = board(width, height, cells);
    if (!S.isBoard(b)) throw new Error('not a board');
    const whole = S.circledClues(b, rows, columns);
    if (!Object.isFrozen(whole) || !Object.isFrozen(whole.rows) || !Object.isFrozen(whole.columns)) {
      throw new Error('not frozen');
    }
    const line = (r0, c0, dr, dc, n) => Array.from({ length: n }, (_, k) => cells[(r0 + k * dr) * width + c0 + k * dc]);
    const byLine = {
      rows: rows.map((clue, r) => [...S.circledNumbers(clue, line(r, 0, 0, 1, width))]),
      columns: columns.map((clue, c) => [...S.circledNumbers(clue, line(0, c, 1, 0, height))]),
    };
    const flipped = Array.from({ length: width * height }, (_, i) => cells[(i % height) * width + Math.floor(i / height)]);
    const transposed = S.circledClues(board(height, width, flipped), columns, rows);
    return { whole: plain(whole), byLine, transposed: plain(transposed) };
  });
}"""

_SHAPES = [(10, 10), (15, 10), (10, 25)]


@pytest.mark.browser
def test_PropertyTest_SolverClues_BoardIsLineByLine(browser_page, live) -> None:
    """AC-4 — each row and column entry of circledClues is circledNumbers of
    that line; the transposed board with rows and columns swapped gives the
    transposed result."""
    _blank_page(browser_page, live)
    rng = random.Random(1884)
    circled_lines = 0
    for width, height in _SHAPES:
        solution = [[rng.random() < 0.55 for _ in range(width)] for _ in range(height)]
        rows = [_encode(row) for row in solution]
        columns = [_encode(col) for col in zip(*solution)]
        boards = []
        for _ in range(120):
            reveal = rng.choice((0.5, 0.8, 0.95, 1.0))
            boards.append("".join(
                ("D" if cell else "W") if rng.random() < reveal else rng.choice("DW.")
                for row in solution for cell in row))
        got = browser_page.evaluate(_BOARD, {
            "width": width, "height": height, "rows": rows, "columns": columns, "boards": boards})
        assert len(got) == len(boards) >= 100
        for result in got:
            assert result["whole"] == result["byLine"]
            assert result["transposed"] == {"rows": result["whole"]["columns"],
                                            "columns": result["whole"]["rows"]}
            assert [len(line) for line in result["whole"]["rows"]] == [len(c) for c in rows]
            assert [len(line) for line in result["whole"]["columns"]] == [len(c) for c in columns]
            circled_lines += sum(any(line) for axis in ("rows", "columns") for line in result["whole"][axis])
    assert circled_lines >= 1000, circled_lines


# ==========================================================================
# The player page
# ==========================================================================

SIDE = 15
#: The owner's "2 2" row and a row whose first clue number has two digits.
OWNER_ROW = 7
TWO_DIGIT_ROW = 3


def _player_grid():
    """15 x 15, every row tight (its clue alone fixes it) except OWNER_ROW,
    so the column clues fix that row and the storage boundary's solver
    accepts the grid. TWO_DIGIT_ROW is "12 2"; OWNER_ROW is "2 2"."""
    rng = random.Random(188)
    rows = [_tight_row(SIDE, rng) for _ in range(SIDE)]
    rows[TWO_DIGIT_ROW] = [True] * 12 + [False] + [True] * 2
    rows[OWNER_ROW] = [False] * 3 + [True] * 2 + [False] * 4 + [True] * 2 + [False] * 4
    return rows


GRID = _player_grid()
ROW_CLUES = [_encode(row) for row in GRID]
COLUMN_CLUES = [_encode(col) for col in zip(*GRID)]

_CIRCLES = """() => {
  const read = (kind) => [...document.querySelectorAll(`th.player-clue.is-${kind}`)]
    .map((box) => [...box.querySelectorAll('.player-clue-num')].map((n) => n.classList.contains('is-circled')));
  return { rows: read('row'), columns: read('col') };
}"""


def _circles(page):
    return page.evaluate(_CIRCLES)


def _circled_set(page):
    seen = _circles(page)
    return {(axis, line, k) for axis in ("rows", "columns")
            for line, numbers in enumerate(seen[axis]) for k, on in enumerate(numbers) if on}


def _none(page):
    return _circled_set(page) == set()


def _open_player(page, live):
    _open(page, live, live.store(GRID))
    assert page.evaluate("window.puzzlePlayer.payload.rows") == ROW_CLUES


def _cells(marks_by_row):
    """A board's cells: {row: "DW.…"} for the given rows, undecided elsewhere."""
    codes = {"D": F, "W": E, ".": U}
    cells = [U] * (SIDE * SIDE)
    for r, marks in marks_by_row.items():
        for c, ch in enumerate(marks):
            cells[r * SIDE + c] = codes[ch]
    return cells


#: Two tight rows (not the special ones) whose first run is >= 2 cells.
_ROWS = [r for r in range(SIDE) if r not in (OWNER_ROW, TWO_DIGIT_ROW) and ROW_CLUES[r][0] >= 2][:2]


@pytest.mark.browser
class TestSolverClues_CirclesFollowEveryCommit:
    """AC-5 — real input circles exactly the settled number; undo, redo and
    reset carry the circles with the board."""

    def test_drag_click_undo_redo_reset(self, browser_page, live) -> None:
        page = browser_page
        problems = _watch_problems(page, live)
        _open_player(page, live)
        assert len(_ROWS) == 2
        first, second = _ROWS
        assert _none(page)

        # Row `first`: the white dot after its first run (two clicks), then a
        # drag over the run closes it — the drag's commit circles it.
        n = ROW_CLUES[first][0]
        _cell(page, first, n).click()
        _cell(page, first, n).click()
        assert _states(page)[first * SIDE + n] == E
        assert _none(page)
        _drag(page, [(first, 0), (first, n - 1)])
        assert _circled_set(page) == {("rows", first, 0)}

        _button(page, "Undo").click()
        assert _none(page)
        _button(page, "Redo").click()
        assert _circled_set(page) == {("rows", first, 0)}

        # Row `second`: the run first, then the white dot by clicks — the
        # second click (filled -> white) is the commit that circles it.
        m = ROW_CLUES[second][0]
        _drag(page, [(second, 0), (second, m - 1)])
        _cell(page, second, m).click()
        assert _circled_set(page) == {("rows", first, 0)}  # filled: the run is 1 too long
        _cell(page, second, m).click()
        assert _circled_set(page) == {("rows", first, 0), ("rows", second, 0)}

        page.keyboard.press("Control+z")
        assert _circled_set(page) == {("rows", first, 0)}
        page.keyboard.press("Control+Shift+z")
        assert _circled_set(page) == {("rows", first, 0), ("rows", second, 0)}

        _button(page, "Reset").click()
        _button(page, "Clear board").click()
        assert _none(page)
        assert problems == []


@pytest.mark.browser
class TestSolverClues_AmbiguousRunStaysUncircled:
    """AC-6 — the owner's case: clue "2 2", one closed run of 2 in the
    middle, undecided cells around it."""

    def test_the_owner_case(self, browser_page, live) -> None:
        _open_player(browser_page, live)
        assert ROW_CLUES[OWNER_ROW] == [2, 2]
        _set(browser_page, _cells({OWNER_ROW: "....WDDW......."}))
        assert _circles(browser_page)["rows"][OWNER_ROW] == [False, False]
        assert _none(browser_page)
        # The same row with its left edge decided circles the first "2" —
        # so the page does circle this row once its marks settle a number.
        _set(browser_page, _cells({OWNER_ROW: "WWWWWDDW......."}))
        assert _circles(browser_page)["rows"][OWNER_ROW] == [True, False]


@pytest.mark.browser
class TestSolverClues_DragPreviewDoesNotCircle:
    """AC-7 — circles follow the recorded board, not a drag's preview."""

    def test_no_circle_until_release(self, browser_page, live) -> None:
        page = browser_page
        _open_player(page, live)
        r = _ROWS[0]
        n = ROW_CLUES[r][0]
        _set(page, _cells({r: "." * n + "W"}))
        assert _none(page)
        page.mouse.move(*_centre(page, r, 0))
        page.mouse.down()
        page.mouse.move(*_centre(page, r, n - 1), steps=6)
        # The preview shows the closed run, yet nothing is circled.
        drawn = page.evaluate(
            "(r) => [...document.querySelectorAll(`td.player-cell[data-row='${r}']`)].map((td) => td.dataset.state)", r)
        assert drawn[:n + 1] == [F] * n + [E]
        assert _none(page)
        page.mouse.up()
        assert _circled_set(page) == {("rows", r, 0)}


_GEOMETRY = """() => {
  const box = (el) => { const b = el.getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; };
  const all = (sel) => [...document.querySelectorAll(sel)];
  return {
    cells: all('td.player-cell').map(box),
    clues: all('th.player-clue').map(box),
    numbers: all('.player-clue-num').map(box),
    texts: all('.player-clue-num').map((n) => n.textContent),
    labels: all('th.player-clue').map((b) => b.getAttribute('aria-label')),
  };
}"""


def _solution_marks(row_indices):
    return {r: "".join("D" if cell else "W" for cell in GRID[r]) for r in row_indices}


@pytest.mark.browser
class TestSolverClues_CirclingMovesNothing:
    """AC-8 — circling numbers changes no box, text or label."""

    def test_geometry_and_text_are_unchanged(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size({"width": 1440, "height": 900})
        _open_player(page, live)
        before = page.evaluate(_GEOMETRY)
        # Every row as the solution except the last, left undecided (so the
        # board is not solved): every number of those rows is circled.
        _set(page, _cells(_solution_marks(range(SIDE - 1))))
        circled = _circled_set(page)
        assert len(circled) >= 30, len(circled)
        assert {("rows", TWO_DIGIT_ROW, 0), ("rows", TWO_DIGIT_ROW, 1)} <= circled
        assert page.evaluate(_GEOMETRY) == before


_LOOK = """(span) => {
  const s = getComputedStyle(span);
  const box = span.getBoundingClientRect();
  const range = document.createRange();
  range.selectNodeContents(span);
  const text = range.getBoundingClientRect();
  return {
    border: parseFloat(s.borderTopWidth), radius: parseFloat(s.borderTopLeftRadius),
    style: s.borderTopStyle, colour: s.borderTopColor, ink: s.color,
    width: box.width, height: box.height, textWidth: text.width,
    background: getComputedStyle(span.closest('th')).backgroundColor,
    animation: s.animationName, transition: s.transitionDuration,
  };
}"""


@pytest.mark.browser
class TestSolverClues_TheCircleIsVisible:
    """AC-9 — a circled number has a round outline in a colour other than the
    clue box background; a two-digit one's outline is as wide as its text."""

    def test_the_outline(self, browser_page, live) -> None:
        page = browser_page
        _open_player(page, live)
        assert ROW_CLUES[TWO_DIGIT_ROW] == [12, 2]
        _set(page, _cells(_solution_marks([TWO_DIGIT_ROW, OWNER_ROW])))
        row = page.locator("th.player-clue.is-row").nth(TWO_DIGIT_ROW).locator(".player-clue-num")
        owner = page.locator("th.player-clue.is-row").nth(OWNER_ROW).locator(".player-clue-num")
        bare = page.locator("th.player-clue.is-row").nth(0).locator(".player-clue-num").first
        assert _circles(page)["rows"][TWO_DIGIT_ROW] == [True, True]

        ink = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--grid-ink')")
        for span in (row.nth(0), row.nth(1), owner.nth(0)):
            look = span.evaluate(_LOOK)
            assert look["border"] > 0 and look["style"] == "solid", look
            assert look["radius"] >= min(look["width"], look["height"]) / 2 - 0.5, look
            assert look["colour"] != look["background"], look
            assert look["colour"] == look["ink"], look  # grid-ink, as the digit
            assert look["width"] >= look["textWidth"], look
            assert look["animation"] == "none" and look["transition"] == "0s", look
        assert ink.strip()

        two_digit = row.nth(0).evaluate(_LOOK)
        assert two_digit["textWidth"] > row.nth(1).evaluate(_LOOK)["textWidth"]  # really two digits
        assert two_digit["width"] >= two_digit["textWidth"] + 2 * two_digit["border"]

        # An uncircled number keeps the same border width, in a transparent colour.
        plain = bare.evaluate(_LOOK)
        assert _circles(page)["rows"][0] == [False] * len(ROW_CLUES[0])
        assert plain["border"] == look["border"]
        assert plain["colour"] == "rgba(0, 0, 0, 0)", plain
