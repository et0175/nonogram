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
  nothing (AC-8), and the circle is a visible round ring that clears its
  digits (AC-9).
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

    #: "What to implement" 2, rule A: a closed run whose length is not its
    #: anchored clue number STOPS the walk from that edge. These marks fit no
    #: placement (the by-design wrong-marks case), so AC-1 cannot see them.
    STOPS = [
        ((1, 1), "DDW.......", [False, False]),  # longer than c1: no circle
        ((1, 2), "DDWDW.....", [False, False]),  # stop, not skip to the next run
        ((2, 1), ".....WDWDD", [False, False]),  # the same from the right edge
        ((1, 2), "WWWWWWWWWD", [True, False]),  # a closed run may end at the far edge
        ((2, 1), "DWWWWWWWWW", [False, True]),  # the same, walking from the right
    ]

    def test_a_mismatched_closed_run_stops_its_walk(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        got = _numbers(browser_page, [(clue, marks) for clue, marks, _ in self.STOPS])
        assert got == [circled for _, _, circled in self.STOPS]


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


#: Desktop, and a phone (390 px: the <= 820 px 24 px cell floor, CARD-182).
_VIEWPORTS = [{"width": 1440, "height": 900}, {"width": 390, "height": 844}]

_GEOMETRY = """() => {
  const box = (el) => { const b = el.getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; };
  const all = (sel) => [...document.querySelectorAll(sel)];
  return {
    cells: all('td.player-cell').map(box),
    clues: all('th.player-clue').map(box),
    numbers: all('.player-clue-num').map(box),
    digits: all('.player-clue-num').map((n) => { const r = document.createRange(); r.selectNodeContents(n); return box(r); }),
    texts: all('.player-clue-num').map((n) => n.textContent),
    labels: all('th.player-clue').map((b) => b.getAttribute('aria-label')),
  };
}"""


def _solution_marks(row_indices):
    return {r: "".join("D" if cell else "W" for cell in GRID[r]) for r in row_indices}


@pytest.mark.browser
class TestSolverClues_CirclingMovesNothing:
    """AC-8 — circling numbers changes no box (cell, clue box, number, or the
    digits' own text box), text or label, at 1440 px and at 390 px."""

    @pytest.mark.parametrize("viewport", _VIEWPORTS, ids=["desktop", "phone"])
    def test_geometry_and_text_are_unchanged(self, browser_page, live, viewport) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open_player(page, live)
        before = page.evaluate(_GEOMETRY)
        # Every row as the solution except the last, left undecided (so the
        # board is not solved): every number of those rows is circled.
        _set(page, _cells(_solution_marks(range(SIDE - 1))))
        circled = _circled_set(page)
        assert len(circled) >= 30, len(circled)
        assert {("rows", TWO_DIGIT_ROW, 0), ("rows", TWO_DIGIT_ROW, 1)} <= circled
        assert page.evaluate(_GEOMETRY) == before


_SLOTS = """() => {
  const px = (v) => parseFloat(v);
  const cell = document.querySelector('td.player-cell').getBoundingClientRect();
  const row = (n) => {
    const s = getComputedStyle(n), b = n.getBoundingClientRect();
    return { text: n.textContent, width: b.width, gap: px(s.marginRight), font: px(s.fontSize) };
  };
  const col = (n) => ({ text: n.textContent, height: n.getBoundingClientRect().height });
  return {
    cell: [cell.width, cell.height],
    rows: [...document.querySelectorAll('th.player-clue.is-row .player-clue-num')].map(row),
    columns: [...document.querySelectorAll('th.player-clue.is-col .player-clue-num')].map(col),
  };
}"""


@pytest.mark.browser
class TestSolverClues_EveryNumberKeepsAOneCellSlot:
    """AC-3 (CARD-196) — a row number's box is as wide as its digits (0.6 em
    each at the numeral size), with a 1.45 ch gap after it, not one cell
    wide; a column number's box is still one cell tall. One- and two-digit
    numbers, at 1440 px and at 390 px."""

    @pytest.mark.parametrize("viewport", _VIEWPORTS, ids=["desktop", "phone"])
    def test_slots(self, browser_page, live, viewport) -> None:
        browser_page.set_viewport_size(viewport)
        _open_player(browser_page, live)
        seen = browser_page.evaluate(_SLOTS)
        width, height = seen["cell"]
        assert any(len(r["text"]) == 2 for r in seen["rows"])
        for r in seen["rows"]:
            ch = 0.6 * r["font"]
            assert abs(r["width"] - len(r["text"]) * ch) < 0.1, r  # glyph advances round to 1/64 px
            assert abs(r["gap"] - 1.45 * ch) < 0.1, r
        assert [c for c in seen["columns"] if abs(c["height"] - height) > 0.001] == [], seen["columns"]
        assert all(r["width"] < width for r in seen["rows"] if len(r["text"]) == 1), seen["rows"]


#: A number's ring is its ::before (admin.css): read the ring's computed style.
_LOOK = """(span) => {
  const s = getComputedStyle(span), ring = getComputedStyle(span, '::before');
  const box = span.getBoundingClientRect();
  const range = document.createRange();
  range.selectNodeContents(span);
  const text = range.getBoundingClientRect();
  return {
    border: parseFloat(ring.borderTopWidth), radius: parseFloat(ring.borderTopLeftRadius),
    style: ring.borderTopStyle, colour: ring.borderTopColor, ink: s.color,
    width: parseFloat(ring.width), height: parseFloat(ring.height), sizing: ring.boxSizing,
    textWidth: text.width, numberWidth: box.width,
    background: getComputedStyle(span.closest('th')).backgroundColor,
    animation: ring.animationName, transition: ring.transitionDuration,
  };
}"""

#: The --grid-ink token, resolved to a colour inside the board.
_GRID_INK = """() => {
  const probe = document.createElement('i');
  probe.style.color = 'var(--grid-ink)';
  document.querySelector('.player-board').append(probe);
  const colour = getComputedStyle(probe).color;
  probe.remove();
  return colour;
}"""

#: Every number's ring as a viewport rectangle (from the ::before's computed
#: box and offsets against the number's box), and its digits' text box.
_RINGS = """() => [...document.querySelectorAll('.player-clue-num')].map((n) => {
  const b = n.getBoundingClientRect(), ring = getComputedStyle(n, '::before'), s = getComputedStyle(n);
  const range = document.createRange(); range.selectNodeContents(n); const t = range.getBoundingClientRect();
  const bw = parseFloat(ring.borderTopWidth);
  const extra = ring.boxSizing === 'border-box' ? 0 : 2 * bw;
  const left = b.left + parseFloat(s.borderLeftWidth) + parseFloat(ring.left);
  const top = b.top + parseFloat(s.borderTopWidth) + parseFloat(ring.top);
  return {
    axis: n.closest('th').classList.contains('is-row') ? 'row' : 'col', text: n.textContent,
    circled: n.classList.contains('is-circled'), position: ring.position, border: bw,
    left, top, right: left + parseFloat(ring.width) + extra, bottom: top + parseFloat(ring.height) + extra,
    textLeft: t.left, textRight: t.right, textTop: t.top, textBottom: t.bottom,
  };
})"""


#: admin.css --player-ring-gap: the least distance between any two rings.
_RING_GAP = 0.25

#: The 30 x 30 ring check's windows: the desktop cell floor, 1440, 390.
_RING_VIEWPORTS = [{"width": 1100, "height": 700}, *_VIEWPORTS]


def _two_run_row(first, second, side=30):
    return [True] * first + [False] + [True] * second + [False] * (side - first - second - 1)


def _two_digit_grid():
    """30 x 30 whose row clues are pairs of two-digit numbers ("12 17", ...)
    and whose first ten columns read "30"/two-digit numbers side by side."""
    rng = random.Random(7)
    rows = [_two_run_row(a, 29 - a) for a in (rng.randint(10, 19) for _ in range(30))]
    rows[0] = [True] * 30
    return rows


@pytest.mark.browser
class TestSolverClues_TheCircleIsVisible:
    """AC-9 — a circled number has a round ring (its ::before) in the
    --grid-ink colour, other than the clue box background; a two-digit row
    number's ring is a pill (wider than tall) at least as wide as its text
    plus both border widths. Checked at 1440 px and at 390 px on the 15 x 15,
    and on a 30 x 30 at the 14 px cell floor (a 1100 x 700 window), at
    1440 px (about 17 px) and at 390 px (24 px), where every row clue box
    is one cell tall and every number's ring has its horizontal and
    vertical centre within half a pixel of its digits' text-box centre (the
    Range box of the number's text). Every circled row number's ring, one
    digit or two, and every circled single-digit column number's ring
    clears its digits' text box by at least half a pixel on the left and on
    the right — CARD-196 AC-8 (redo 3, owner option a) narrows this one
    clearance claim for a two-digit COLUMN number only: its ring is not
    required to fully clear its own digits (see
    test_two_digit_rings_clear_their_digits_on_a_30x30 for the measured
    bound and the no-clipping check), though it is still capped at
    _RING_GAP from the next column's ring, so it never reaches a
    neighbour. That test's clearance assertion covers every row ring
    regardless of digit count and every single-digit column ring (not just
    the two-digit rows its fixture happens to produce); see the comment at
    the assertion for why a dedicated single-digit-row fixture is not
    needed for THIS clearance question.

    Separately, any two rings are at least _RING_GAP (admin.css
    --player-ring-gap) apart — EXCEPT two adjacent SINGLE-DIGIT ROW rings
    (CARD-196 AC-8, F-006 narrowing, owner option b, 2026-10-07): the
    shared 1.45ch row gap leaves them only about 0.125-0.141 px apart,
    across all three viewports above (never an actual overlap — the gap
    stays positive), while every other pair — two-digit row, two-digit
    column, single-digit column, and any row/column mix — keeps the full
    _RING_GAP floor, pinned by the `_RING_GAP` close-pairs check in
    test_two_digit_rings_clear_their_digits_on_a_30x30 (whose fixture has
    no adjacent single-digit row pair, so it does not exercise this one
    exception). This gap exception does NOT touch a single-digit row
    ring's OWN digit clearance, which stays the unqualified >= 0.5 px bar
    above: TestSolverClues_SingleDigitRowRingsMayTouch exercises a
    dedicated adjacent-single-digit-row fixture (the 15 x 15
    _player_grid's OWNER_ROW, "2 2") to prove both the narrowed gap and
    the still-unqualified own-clearance, rather than extend this class's
    30 x 30 two-digit fixture (which has no single-digit row pair)."""

    @pytest.mark.parametrize("viewport", _VIEWPORTS, ids=["desktop", "phone"])
    def test_the_outline(self, browser_page, live, viewport) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open_player(page, live)
        assert ROW_CLUES[TWO_DIGIT_ROW] == [12, 2]
        _set(page, _cells(_solution_marks([TWO_DIGIT_ROW, OWNER_ROW])))
        row = page.locator("th.player-clue.is-row").nth(TWO_DIGIT_ROW).locator(".player-clue-num")
        owner = page.locator("th.player-clue.is-row").nth(OWNER_ROW).locator(".player-clue-num")
        bare = page.locator("th.player-clue.is-row").nth(0).locator(".player-clue-num").first
        assert _circles(page)["rows"][TWO_DIGIT_ROW] == [True, True]

        ink = page.evaluate(_GRID_INK)
        assert ink.startswith("rgb"), ink
        for span in (row.nth(0), row.nth(1), owner.nth(0)):
            look = span.evaluate(_LOOK)
            assert look["border"] > 0 and look["style"] == "solid", look
            assert look["radius"] >= min(look["width"], look["height"]) / 2 - 0.5, look
            assert look["colour"] != look["background"], look
            assert look["colour"] == ink, look  # the --grid-ink token
            assert look["colour"] == look["ink"], look  # as the digit
            assert look["width"] >= look["textWidth"], look
            assert look["animation"] == "none" and look["transition"] == "0s", look

        two_digit = row.nth(0).evaluate(_LOOK)
        assert two_digit["sizing"] == "border-box", two_digit
        assert two_digit["textWidth"] > row.nth(1).evaluate(_LOOK)["textWidth"]  # really two digits
        assert two_digit["width"] >= two_digit["textWidth"] + 2 * two_digit["border"]
        assert two_digit["width"] > two_digit["height"]  # a pill, not the one-digit circle

        # An uncircled number keeps the same ring, in a transparent colour.
        plain = bare.evaluate(_LOOK)
        assert _circles(page)["rows"][0] == [False] * len(ROW_CLUES[0])
        assert plain["border"] == look["border"]
        assert plain["colour"] == "rgba(0, 0, 0, 0)", plain

    @pytest.mark.parametrize("viewport", _RING_VIEWPORTS, ids=["floor", "desktop", "phone"])
    def test_two_digit_rings_clear_their_digits_on_a_30x30(self, browser_page, live, viewport) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        grid = _two_digit_grid()
        _open(page, live, live.store(grid))
        cell = page.evaluate("document.querySelector('td.player-cell').getBoundingClientRect().width")
        assert cell == pytest.approx({1100: 14.4, 1440: 17.67, 390: 24}[viewport["width"]], abs=0.05), cell
        # The row numbers' height, line-height and negative margins (admin.css)
        # leave every row clue box, so every row, one cell tall, also the rows
        # that end in a heavy rule.
        rows = page.evaluate("[...document.querySelectorAll('th.player-clue.is-row')].map((th) => th.getBoundingClientRect().height)")
        assert len(rows) == 30 and [h for h in rows if abs(h - cell) > 0.001] == [], rows
        # The whole solution: every line fully marked, so every number is
        # circled (a solved board is not special-cased).
        _set(page, [F if on else E for line in grid for on in line])
        rings = page.evaluate(_RINGS)
        assert {ring["position"] for ring in rings} == {"absolute"}  # out of layout
        circled = [ring for ring in rings if ring["circled"] and len(ring["text"]) == 2]
        for axis in ("row", "col"):
            assert sum(ring["axis"] == axis for ring in circled) >= 20, axis

        # Every ring (one and two digits, rows and columns) is centred on its
        # digits' text box, horizontally and vertically, within half a pixel.
        for axis in ("row", "col"):
            assert sum(ring["axis"] == axis for ring in rings) >= 30, axis
        offsets = [
            (ring["axis"], ring["text"],
             round((ring["left"] + ring["right"] - ring["textLeft"] - ring["textRight"]) / 2, 3),
             round((ring["top"] + ring["bottom"] - ring["textTop"] - ring["textBottom"]) / 2, 3))
            for ring in rings
        ]
        off_centre = [o for o in offsets if abs(o[2]) > 0.5 or abs(o[3]) > 0.5]
        assert off_centre == [], off_centre[:5]

        for ring in circled:
            inner_left, inner_right = ring["left"] + ring["border"], ring["right"] - ring["border"]
            assert ring["right"] - ring["left"] > ring["bottom"] - ring["top"], ring  # a pill, every axis
            if ring["axis"] == "row":
                assert ring["textLeft"] - inner_left >= 0.5, ring
                assert inner_right - ring["textRight"] >= 0.5, ring
            # CARD-196 AC-8 (redo 3, owner option a, narrowed): a two-digit
            # COLUMN ring keeps the --player-ring cap (admin.css) that holds
            # it _RING_GAP away from the next column's ring — measured below,
            # it never gets there — but that same cap means it is not
            # required to clear its own digits. Measured at this test's two
            # smallest cells: -1.42 px short (1100x700, the 14.4 px floor)
            # and +0.22 to +0.25 px (1440x900, under the 0.5 px bar used for
            # rows and single-digit columns above). No clearance assertion
            # for the col axis here; the no-clipping check below (not a
            # clearance number) is what AC-8 actually requires of it.
        # Every circled row ring (one digit or two) AND every circled
        # single-digit column ring clears its own digits (CARD-196 AC-8: the
        # row's 1.45 ch gap and the column's uncapped-by-digit-count ring
        # formula both leave room; only a two-digit COLUMN ring is narrowed,
        # in the `circled` loop above). This fixture (_two_digit_grid) has
        # no single-digit ROW number -- every row run is built two digits
        # wide -- so the row half of this assertion is exercised only by
        # two-digit rows here; that is still the harder case for the row
        # axis: a row ring is never capped to its neighbour (only a column
        # ring is, admin.css), and the single-digit COLUMN ring this loop
        # does check is comfortably clear at every viewport (>= 1.7 px,
        # measured) versus the two-digit row's tightest measured margin
        # (0.703 px) -- so a single-digit row ring, using the same
        # uncapped max(circle, digits * 1ch + clearance) formula as the row
        # rings already checked here, cannot be tighter than either of
        # those two already-proven cases. The `> 0` check below keeps the
        # single-digit-column half of this assertion from going vacuous if
        # the fixture ever changes to have none.
        single_digit_col_rings = [
            ring for ring in rings
            if ring["circled"] and ring["axis"] == "col" and len(ring["text"]) == 1
        ]
        assert len(single_digit_col_rings) > 0, "fixture has no single-digit column ring to check"
        for ring in rings:
            if ring["circled"] and (ring["axis"] == "row" or len(ring["text"]) == 1):
                inner_left, inner_right = ring["left"] + ring["border"], ring["right"] - ring["border"]
                assert ring["textLeft"] - inner_left >= 0.5 and inner_right - ring["textRight"] >= 0.5, ring

        # Any two rings are at least _RING_GAP apart on one axis, less one
        # 1/64 px layout unit (layout rounds to 1/64 px, hence the tolerance).
        # CARD-196 AC-8 (redo 3): the owner's narrowing allows a two-digit
        # COLUMN ring to come within, or overlap, _RING_GAP of its neighbour
        # by about 3 px. Measured here it does not: the --player-ring cap
        # (admin.css) already subtracts _RING_GAP from the distance between
        # two columns' rings, so the closest two-digit column pair measures
        # exactly that floor (0.25 px, at both 1100x700 and 1440x900) and no
        # pair ever goes negative. The check below is therefore left as the
        # one hard floor for every pair, including two-digit column ones —
        # narrowing it to a looser, measured bound would assert an overlap
        # that this CSS does not actually produce.
        close = [
            (a["text"], b["text"], a["axis"], b["axis"], round(gap, 3))
            for i, a in enumerate(rings) for b in rings[i + 1:]
            if (gap := max(b["left"] - a["right"], a["left"] - b["right"], b["top"] - a["bottom"], a["top"] - b["bottom"]))
            < _RING_GAP - 1 / 64
        ]
        assert close == [], close[:5]

        # AC-8: a two-digit column ring may fall short of clearing its own
        # digits, but it must never clip them. The ring is a decorative
        # ::before with no size effect on layout (asserted absolute above);
        # nothing in admin.css sets overflow: hidden (or a clip-path) on a
        # .player-clue-num or on its ancestor th.player-clue, so the digits'
        # own glyphs are always fully painted regardless of the ring's size.
        not_clipped = page.evaluate(
            "() => [...document.querySelectorAll('.player-clue-num')].every((n) => {"
            "  const style = getComputedStyle(n), th = getComputedStyle(n.closest('th'));"
            "  return style.overflow === 'visible' && th.overflow === 'visible'"
            "    && style.clipPath === 'none' && th.clipPath === 'none';"
            "})"
        )
        assert not_clipped


@pytest.mark.browser
class TestSolverClues_SingleDigitRowRingsMayTouch:
    """CARD-196 AC-8, F-006 narrowing (owner decision, option b,
    2026-10-07): two adjacent SINGLE-DIGIT row rings are not required to
    keep the full _RING_GAP (admin.css --player-ring-gap) apart. Uses the
    15 x 15 _player_grid's OWNER_ROW (clue "2 2", the owner's own AC-6
    example row) — already the only adjacent single-digit row ring pair in
    this file — rather than a new board, at the same three viewports
    (_RING_VIEWPORTS) TestSolverClues_TheCircleIsVisible checks the 30 x 30
    ring floor at. Fully marking OWNER_ROW circles both its "2"s (AC-3: a
    fully marked line circles everything), so both rings are live. The gap
    between them is always positive (the rings touch, never overlap) but
    measures well under _RING_GAP (about 0.125-0.141 px); each ring's OWN
    digit clearance (the >= 0.5 px bar from the cycle-1 F-001 fix) is
    unaffected by this narrowing and is asserted here too."""

    @pytest.mark.parametrize("viewport", _RING_VIEWPORTS, ids=["floor", "desktop", "phone"])
    def test_adjacent_single_digit_row_rings_touch_but_never_overlap(self, browser_page, live, viewport) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open_player(page, live)
        assert ROW_CLUES[OWNER_ROW] == [2, 2]
        _set(page, _cells(_solution_marks([OWNER_ROW])))
        assert _circles(page)["rows"][OWNER_ROW] == [True, True]

        rings = page.evaluate(_RINGS)
        owner_rings = [ring for ring in rings if ring["axis"] == "row" and ring["circled"]]
        # OWNER_ROW is the only row marked, so these are exactly its two
        # rings, and both are single-digit ("2 2").
        assert len(owner_rings) == 2, owner_rings
        assert all(len(ring["text"]) == 1 for ring in owner_rings), owner_rings
        first, second = sorted(owner_rings, key=lambda ring: ring["left"])

        gap = second["left"] - first["right"]
        # Never an actual overlap (always positive, less one 1/64 px layout
        # unit, as the existing close-pairs check below tolerates)...
        assert gap > -1 / 64, gap
        # ...but F-006 narrows the full _RING_GAP floor away for this one
        # pair: it must measure strictly under it (the owner's measured
        # ~0.125-0.141 px), or a future CSS change that widens the row gap
        # back to clearing every pair would make this fixture pointless.
        assert gap < _RING_GAP - 1 / 64, gap

        # Unaffected by the narrowing: each ring still fully clears its own
        # digits (the >= 0.5 px bar, unchanged since the cycle-1 F-001 fix).
        for ring in owner_rings:
            inner_left, inner_right = ring["left"] + ring["border"], ring["right"] - ring["border"]
            assert ring["textLeft"] - inner_left >= 0.5, ring
            assert inner_right - ring["textRight"] >= 0.5, ring


#: The numerals' computed font sizes, in document order.
_NUMERALS = """() => [...document.querySelectorAll('.player-clue-num')].map((n) => parseFloat(getComputedStyle(n).fontSize))"""

#: The stage's scroll and client widths, and the page's scroll width.
_SCROLL = """() => {
  const stage = document.querySelector('.player-stage');
  return {
    stage: [stage.scrollWidth, stage.clientWidth],
    page: document.documentElement.scrollWidth,
    cell: document.querySelector('td.player-cell').getBoundingClientRect().width,
  };
}"""


def _fit_binding_columns_grid():
    """30 x 30: every row has two runs (one white cell, not at the ends), rows
    9, 19 and 28 are empty, so every column number has one digit and every
    row clue is short: the fit, not the column floor, sets the cell at 390 px."""
    rng = random.Random(4040)
    grid = []
    for r in range(30):
        if r in (9, 19, 28):
            grid.append([False] * 30)
        else:
            z = rng.randint(1, 28)
            grid.append([c != z for c in range(30)])
    return grid


def _no_phone_floor(page):
    page.evaluate("document.querySelector('.player-stage').style.setProperty('--player-cell-min', '0px')")


@pytest.mark.browser
class TestPlayerNumerals_TwelvePixelFloor:
    """AC-1 and AC-2 (CARD-196) — a numeral is 0.6 x the cell, never below
    12 px. A 15 x 15 keeps its 0.6 x cell numerals on desktop (16.8 px) and
    at the phone floor (14.4 px); a 30 x 30 with a two-digit column number
    sits at the 12 px floor at 1440 px and at 1100 px (its cell is 17.67 px
    and 14.4 px, so 0.6 x cell is 10.6 px and 8.6 px and the floor binds)."""

    def test_15x15_desktop_numerals_are_0_6_of_the_28_px_cell(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 1440, "height": 900})
        _open_player(browser_page, live)
        fonts = browser_page.evaluate(_NUMERALS)
        assert fonts and all(abs(f - 16.8) < 0.01 for f in fonts), sorted(set(fonts))

    def test_15x15_phone_numerals_are_0_6_of_the_24_px_cell(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open_player(browser_page, live)
        fonts = browser_page.evaluate(_NUMERALS)
        assert fonts and all(abs(f - 14.4) < 0.01 for f in fonts), sorted(set(fonts))

    @pytest.mark.parametrize("viewport", [{"width": 1440, "height": 900}, {"width": 1100, "height": 700}],
                             ids=["desktop", "floor"])
    def test_30x30_numerals_never_fall_below_12_px(self, browser_page, live, viewport) -> None:
        browser_page.set_viewport_size(viewport)
        _open(browser_page, live, live.store(_two_digit_grid()))
        fonts = browser_page.evaluate(_NUMERALS)
        assert fonts and min(fonts) >= 12 - 0.001, sorted(set(fonts))
        assert all(abs(f - 12) < 0.01 for f in fonts), sorted(set(fonts))


@pytest.mark.browser
class TestPlayerNumerals_ColumnFloorIsTheWidestColumnNumeral:
    """AC-4 and AC-5 (CARD-196) — the cell is at least the widest column
    numeral's width (its digits at 12 px, 7.2 px per digit). With one-digit
    column numbers only, the cell is the fit (10.05 px for this grid at 390
    px, not raised to the 14.4 px two-digit floor). With a two-digit column
    number the cell is 14.4 px at 1100 px and at 390 px."""

    def test_one_digit_column_numbers_keep_the_fit(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(_fit_binding_columns_grid()))
        _no_phone_floor(browser_page)
        seen = browser_page.evaluate(_SCROLL)
        assert all(len(t) == 1 for t in browser_page.evaluate(
            "[...document.querySelectorAll('th.player-clue.is-col .player-clue-num')].map((n) => n.textContent)")), "one digit"
        assert abs(seen["cell"] - 10.05) < 0.05, seen

    def test_a_two_digit_column_number_sets_the_floor_at_1100(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 1100, "height": 700})
        _open(browser_page, live, live.store(_two_digit_grid()))
        assert abs(browser_page.evaluate(_SCROLL)["cell"] - 14.4) < 0.05

    def test_a_two_digit_column_number_sets_the_floor_at_390_without_the_phone_floor(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(_two_digit_grid()))
        _no_phone_floor(browser_page)
        assert abs(browser_page.evaluate(_SCROLL)["cell"] - 14.4) < 0.05


@pytest.mark.browser
class TestPlayerNumerals_ColumnNumbersDecideTheStageScroll:
    """AC-6 (CARD-196) — a 30-column board with two-digit column numbers
    cannot fit a 390 px stage at 14.4 px a cell (30 x 14.4 = 432 px). The
    board scrolls sideways inside .player-stage; the page never scrolls."""

    def test_the_stage_scrolls_and_the_page_does_not(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(_two_digit_grid()))
        _no_phone_floor(browser_page)
        seen = browser_page.evaluate(_SCROLL)
        assert abs(seen["cell"] - 14.4) < 0.05, seen
        stage_scroll, stage_client = seen["stage"]
        assert stage_scroll > stage_client, seen
        assert seen["page"] <= 390, seen
