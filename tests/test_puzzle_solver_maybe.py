"""CARD-186 — the puzzle player's "?" mark and "?" brush (FR-044 extension,
card-local AC-1..AC-15).

A fourth cell state, MAYBE ("maybe", drawn as "?"): neither dark nor white,
never an error, and no board holding one is solved. A fourth tool, Maybe,
paints "?" along a drag like any tool; its click marks a cell "?" and clears a
"?" back to undecided. Since CARD-189 a click follows the selected brush: a
first click on a "?" with Black, White or Undecided gives that brush's state
(CARD-186's interim "a "?" goes to black" is gone), and every click needs a
tool. The hint (CARD-183) and the clue circles (CARD-188) read "?" as
undecided.

The pure state module is exercised with ``await import('/static/solver_state.js')``
against oracles written here or imported from the other player test files
(CARD-161's board model, CARD-162's error / solved definitions, CARD-183's
hint oracle). Corpora are built with ``random.Random`` and fixed seeds (no
``hypothesis``), their minimum counts asserted inside the tests. User-facing
criteria drive real input in Chromium; ``puzzlePlayer.setBoard`` only sets up
a board.
"""

from __future__ import annotations

import io
import random

import pytest

from tests.test_puzzle_solver_hint import _fixpoint, _grid_hint, _oracle_hint
from tests.test_puzzle_solver_marking import (
    _FOCUSED,
    GRID,
    SIDE,
    E,
    F,
    U,
    _button,
    _cell,
    _drag,
    _Model,
    _states,
    _tool,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_phone import BIG
from tests.test_puzzle_solver_progress import (
    _ONLY_THIS_SAVE,
    LAST,
    NAME,
    _error_count,
    _errors_of,
    _is_solved_shown,
    _near_solved,
    _set,
    _solved_of,
    _watch_problems,
)

M = "maybe"
_CODE = {U: "u", F: "f", E: "e", M: "m"}
_STATE = {code: state for state, code in _CODE.items()}

#: What one FIRST click does (CARD-189), written out: state -> the state after
#: a first click with (Black, White, Undecided, Maybe). Repeat clicks are
#: tested in test_puzzle_solver_marking.py (TestSolverClickFollowsTheBrush).
_CLICK_TABLE = {
    U: (F, E, F, M),
    F: (E, E, U, M),
    E: (F, U, U, M),
    M: (F, E, U, U),
}
_TOOL_COLUMN = {F: 0, E: 1, U: 2, M: 3}


def _clicked(state, tool):
    return _CLICK_TABLE[state][_TOOL_COLUMN[tool]]


def _text(cells):
    return "".join(_CODE[s] for s in cells)


def _clues(grid):
    return [_encode(row) for row in grid], [_encode(col) for col in zip(*grid)]


def _truth(solution, index):
    width = len(solution[0])
    return F if solution[index // width][index % width] else E


def _without_maybe(cells, instead=U):
    return [instead if s == M else s for s in cells]


def _pressed(page):
    return {name: _button(page, name).get_attribute("aria-pressed")
            for name in ("Black", "White", "Undecided", "Maybe")}


def _marked(states, width=SIDE):
    return {(i // width, i % width): s for i, s in enumerate(states) if s != U}


#: GRID's solution-filled and solution-empty cells, row-major.
_FILLED = [(r, c) for r in range(SIDE) for c in range(SIDE) if GRID[r][c]]
_EMPTY = [(r, c) for r in range(SIDE) for c in range(SIDE) if not GRID[r][c]]


# ==========================================================================
# The pure module
# ==========================================================================


_FOURTH_STATE = """async () => {
  const S = await import('/static/solver_state.js');
  const cells = Object.freeze([S.MAYBE, S.UNKNOWN, S.FILLED, S.MAYBE, S.EMPTY, S.MAYBE]);
  const board = Object.freeze({ width: 3, height: 2, cells });
  const blank = S.createBoard(3, 2);
  const set = S.withCell(blank, 1, 2, S.MAYBE);
  return {
    states: S.CELL_STATES,
    frozen: Object.isFrozen(S.CELL_STATES),
    maybe: S.MAYBE,
    isBoard: S.isBoard(board),
    capitalised: S.isBoard(Object.freeze({ width: 1, height: 1, cells: Object.freeze(['Maybe']) })),
    set: [...set.cells],
    setIsBoard: S.isBoard(set),
    blankAfter: [...blank.cells],
  };
}"""


@pytest.mark.browser
class TestSolverMaybeModule_IsAFourthState:
    """AC-1 — CELL_STATES gains "maybe"; boards and withCell take it."""

    def test_fourth_state(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        got = browser_page.evaluate(_FOURTH_STATE)
        assert got["states"] == ["unknown", "filled", "empty", "maybe"]
        assert got["frozen"] is True
        assert got["maybe"] == M
        assert got["isBoard"] is True
        assert got["capitalised"] is False
        assert got["set"] == [U, U, U, U, U, M]
        assert got["setIsBoard"] is True
        assert got["blankAfter"] == [U] * 6


_CLICKS = """async () => {
  const S = await import('/static/solver_state.js');
  const tools = { filled: S.FILLED, empty: S.EMPTY, unknown: S.UNKNOWN, maybe: S.MAYBE };
  const out = [];
  for (const state of S.CELL_STATES) {
    const board = S.withCell(S.createBoard(4, 3), 1, 2, state);
    for (const name of Object.keys(tools)) {
      const stroke = S.clickStroke(board, 1, 2, tools[name]);
      out.push({ state, tool: name,
                 clicked: S.clickedState(state, tools[name]),
                 stroke: { cells: stroke.cells, state: stroke.state } });
    }
  }
  const error = (f) => { try { f(); return null; } catch (e) { return e.name; } };
  return { out, badWithMaybe: error(() => S.clickedState('crossed', S.MAYBE)),
           badWithBlack: error(() => S.clickedState('crossed', S.FILLED)),
           noTool: error(() => S.clickStroke(S.createBoard(4, 3), 1, 2)) };
}"""


@pytest.mark.browser
class TestSolverMaybeModule_ClickedStateTable:
    """AC-2 — clickedState and clickStroke over every (state, tool), as a first
    click, equal _CLICK_TABLE; since CARD-189 an omitted tool is refused."""

    def test_table(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        got = browser_page.evaluate(_CLICKS)
        assert len(got["out"]) == 4 * 4
        for row in got["out"]:
            want = _clicked(row["state"], row["tool"])
            assert row["clicked"] == want, row
            assert row["stroke"] == {"cells": [[1, 2]], "state": want}, row
        assert got["badWithMaybe"] == "RangeError"
        assert got["badWithBlack"] == "RangeError"
        assert got["noTool"] == "RangeError"


# --------------------------------------------------------------------------
# AC-5 / AC-6 — error count and solved state over a corpus with "?"
# --------------------------------------------------------------------------

_PROGRESS_SHAPES = [(10, 10), (15, 10), (10, 25)]
_PER_SHAPE = 240
_MIN_PER_SHAPE = 200
_ONE_MAYBE = 60

_PROGRESS = """async ({ width, height, solutions, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY, m: S.MAYBE };
  return boards.map(([si, text]) => {
    const board = Object.freeze({ width, height, cells: Object.freeze([...text].map((ch) => codes[ch])) });
    if (!S.isBoard(board)) throw new Error('not a board');
    return [S.errorCount(board, solutions[si]), S.isSolved(board, solutions[si])];
  });
}"""


def _four_state_corpus(width, height, rng):
    """Boards with every cell drawn from all four states and at least 20% "?":
    uniform random, and mostly-right boards (the solution's marks, some cells
    wrong or undecided, at least 20% turned "?")."""
    solutions = [[[rng.random() < d for _ in range(width)] for _ in range(height)] for d in (0.5, 0.3, 0.7)]
    boards = []
    while len(boards) < _PER_SHAPE:
        si = len(boards) % len(solutions)
        flat = [cell for row in solutions[si] for cell in row]
        if len(boards) % 2:
            kind = "uniform"
            weights = (1, 1, 1, rng.uniform(0.4, 2))
            cells = rng.choices((U, F, E, M), weights=weights, k=len(flat))
        else:
            kind = "mostly-right"
            cells = [rng.choice((U, F, E)) if rng.random() < 0.1 else (F if cell else E) for cell in flat]
            for index in rng.sample(range(len(flat)), int(len(flat) * rng.uniform(0.2, 0.5)) + 1):
                cells[index] = M
        if cells.count(M) >= 0.2 * len(cells):
            boards.append((si, cells, kind))
    return solutions, boards


def _one_maybe_boards(solutions, rng):
    """Solved boards (the solution's blacks; every other cell white or
    undecided) with exactly one solution-empty cell turned "?"."""
    boards = []
    for k in range(_ONE_MAYBE):
        si = k % len(solutions)
        flat = [cell for row in solutions[si] for cell in row]
        cells = [F if cell else rng.choice((E, U)) for cell in flat]
        cells[rng.choice([i for i, cell in enumerate(flat) if not cell])] = M
        boards.append((si, cells, "one-maybe"))
    return boards


def _solved_boards(solutions, rng, count):
    """Solved boards with no "?" — the oracle and the module must say true."""
    boards = []
    for k in range(count):
        si = k % len(solutions)
        flat = [cell for row in solutions[si] for cell in row]
        boards.append((si, [F if cell else rng.choice((E, U)) for cell in flat], "solved"))
    return boards


def _run_progress(page, seed):
    rng = random.Random(seed)
    results = []
    for width, height in _PROGRESS_SHAPES:
        solutions, corpus = _four_state_corpus(width, height, rng)
        extra = _one_maybe_boards(solutions, rng) + _solved_boards(solutions, rng, 30)
        boards = corpus + extra
        got = page.evaluate(_PROGRESS, {
            "width": width, "height": height, "solutions": solutions,
            "boards": [[si, _text(cells)] for si, cells, _ in boards],
        })
        assert len(got) == len(boards)
        results.append(((width, height), solutions, corpus, boards, got))
    return results


@pytest.mark.browser
def test_PropertyTest_SolverMaybe_ErrorCountNeverCountsMaybe(browser_page, live) -> None:
    """AC-5 — errorCount equals the oracle that counts only FILLED on
    solution-empty and EMPTY on solution-filled, on boards with >= 20% "?"
    on both kinds of solution cell."""
    _open(browser_page, live, live.store(GRID))
    for shape, solutions, corpus, boards, got in _run_progress(browser_page, seed=1865):
        assert len(corpus) >= _MIN_PER_SHAPE, shape
        assert all(cells.count(M) >= 0.2 * len(cells) for _, cells, _ in corpus), shape
        assert all(set(cells) == {U, F, E, M} for _, cells, kind in corpus if kind == "uniform"), shape
        assert sum(kind == "uniform" for _, _, kind in corpus) >= 100, shape

        def maybe_on(want, si, cells):
            flat = [x for row in solutions[si] for x in row]
            return any(s == M and cell is want for s, cell in zip(cells, flat))

        # "?" on solution-filled and on solution-empty cells: counting a "?"
        # as either kind of wrong mark would show.
        assert sum(maybe_on(True, si, cells) for si, cells, _ in corpus) >= 150, shape
        assert sum(maybe_on(False, si, cells) for si, cells, _ in corpus) >= 150, shape
        assert sum(_errors_of(cells, solutions[si]) > 0 for si, cells, _ in corpus) >= 100, shape
        for index, ((si, cells, kind), (count, _)) in enumerate(zip(boards, got)):
            assert count == _errors_of(cells, solutions[si]), (shape, index, kind)


@pytest.mark.browser
def test_PropertyTest_SolverMaybe_NotSolvedWhileAnyMaybe(browser_page, live) -> None:
    """AC-6 — isSolved equals EC-036's oracle and "no cell is MAYBE", over the
    AC-5 corpus, solved boards with no "?" (true), and boards solved but for
    one "?" on a solution-empty cell (false, every one)."""
    _open(browser_page, live, live.store(GRID))
    for shape, solutions, _, boards, got in _run_progress(browser_page, seed=1865):
        one_maybe = [(b, g) for b, g in zip(boards, got) if b[2] == "one-maybe"]
        assert len(one_maybe) >= 50, shape
        # Without the "?" clause these boards are solved: the clause decides.
        assert all(_solved_of(cells, solutions[si]) for (si, cells, _), _ in one_maybe), shape
        assert all(verdict is False for _, (_, verdict) in one_maybe), shape
        assert sum(kind == "solved" for _, _, kind in boards) >= 30, shape
        for index, ((si, cells, kind), (_, verdict)) in enumerate(zip(boards, got)):
            want = _solved_of(cells, solutions[si]) and M not in cells
            assert verdict is want, (shape, index, kind)
        assert sum(verdict for _, verdict in got) >= 30, shape


# --------------------------------------------------------------------------
# AC-8 — replay reproduces the board with "?" strokes
# --------------------------------------------------------------------------

_EC_WIDTH, _EC_HEIGHT = 12, 10
_EC_OPS = 1300

_RUN_HISTORY = """async ({ width, height, ops }) => {
  const S = await import('/static/solver_state.js');
  const blank = S.createBoard(width, height);
  let h = S.createHistory(blank);
  const steps = [];
  for (const op of ops) {
    if (op[0] === 'click') {
      const stroke = S.clickStroke(h.board, op[1], op[2], op[3]);  // a first click (CARD-189)
      h = S.record(h, stroke);
    } else if (op[0] === 'drag') h = S.record(h, S.dragStroke(op[2], op[3], op[1]));
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


class _MaybeModel(_Model):
    """CARD-161's board model with a click that follows _CLICK_TABLE (a first click)."""

    def click(self, r, c, tool=F):
        self._apply({(r, c)}, _clicked(self.board[(r, c)], tool))


def _ops(rng):
    ops = []
    while len(ops) < _EC_OPS:
        roll = rng.random()
        if roll < 0.34:
            ops.append(["click", rng.randrange(_EC_HEIGHT), rng.randrange(_EC_WIDTH), rng.choice([F, E, U, M])])
        elif roll < 0.66:
            start = [rng.randrange(_EC_HEIGHT), rng.randrange(_EC_WIDTH)]
            path, here = [], list(start)
            for _ in range(rng.randint(0, 6)):
                here = [here[0], rng.randrange(_EC_WIDTH)] if rng.random() < 0.5 else [rng.randrange(_EC_HEIGHT), here[1]]
                path.append(here)
            ops.append(["drag", rng.choice([F, E, U, M]), start, path])
        elif roll < 0.68:
            ops.append(["reset"])
        else:
            ops.extend([[rng.choice(["undo", "redo"])]] * rng.randint(1, 4))
    return ops[:_EC_OPS]


@pytest.mark.browser
def test_PropertyTest_SolverMaybe_ReplayReproducesTheBoard(browser_page, live) -> None:
    """AC-8 — after every step of a seeded mix of clicks and drags with each of
    the four tools (first clicks — CARD-189 refuses a click with no tool), resets, undos and redos,
    replaying the undo stack from a blank board gives the current board, which
    equals the Python model's."""
    ops = _ops(random.Random(186))
    _open(browser_page, live, live.store(GRID))
    steps = browser_page.evaluate(_RUN_HISTORY, {"width": _EC_WIDTH, "height": _EC_HEIGHT, "ops": ops})
    assert len(steps) == len(ops)

    model = _MaybeModel(_EC_WIDTH, _EC_HEIGHT)
    strokes = sets_maybe = 0
    clicks = {tool: 0 for tool in (F, E, U, M)}
    drags = {tool: 0 for tool in (F, E, U, M)}
    for index, (op, step) in enumerate(zip(ops, steps)):
        if op[0] == "click":
            strokes += 1
            clicks[op[3]] += 1
            sets_maybe += _clicked(model.board[(op[1], op[2])], op[3]) == M
            model.click(op[1], op[2], op[3])
        elif op[0] == "drag":
            strokes += 1
            drags[op[1]] += 1
            sets_maybe += op[1] == M
            model.drag(op[1], tuple(op[2]), [tuple(p) for p in op[3]])
        elif op[0] == "reset":
            strokes += 1
            model.reset()
        else:
            getattr(model, op[0])()
        assert step["replayed"] == step["board"], (index, op)
        assert step["board"] == "".join(s[0] for s in model.cells()), (index, op)
        assert (step["done"], step["undone"]) == (len(model.past), len(model.future)), (index, op)

    assert strokes >= 500, strokes
    assert sets_maybe >= 100, sets_maybe
    assert min(clicks.values()) >= 40 and min(drags.values()) >= 40, (clicks, drags)
    assert sum(op[0] == "reset" for op in ops) >= 5
    assert sum(op[0] == "undo" for op in ops) >= 100 and sum(op[0] == "redo" for op in ops) >= 100


# --------------------------------------------------------------------------
# AC-11 — the hint reads "?" as undecided
# --------------------------------------------------------------------------

_HINT_SHAPES = [(10, 10), (15, 10), (30, 30)]
_HINT_PER_SHAPE = 220

_HINT_PAIRS = """async ({ width, height, rows, columns, solution, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY, m: S.MAYBE };
  const hint = (text) => {
    const board = Object.freeze({ width, height, cells: Object.freeze([...text].map((ch) => codes[ch])) });
    if (!S.isBoard(board)) throw new Error('not a board');
    const h = S.hintCell(board, rows, columns, solution);
    return h === null ? null : [h.row, h.col, h.state, h.deduced];
  };
  return boards.map(([withMaybe, without]) => [hint(withMaybe), hint(without)]);
}"""


def _hint_corpus(width, height, rng):
    """Kinds: random (correct, wrong, undecided and "?"), fixpoint (line
    logic's fixed point, some cells turned "?"), only-maybe (every cell
    correct but some "?"), and full (no undecided cell; wrong marks and "?")."""
    solution = [[rng.random() < 0.55 for _ in range(width)] for _ in range(height)]
    rows, columns = _clues(solution)
    truth = [F if cell else E for row in solution for cell in row]
    wrong = {F: E, E: F}
    fixed = _fixpoint(rows, columns)
    boards = []
    for k in range(_HINT_PER_SHAPE):
        kind = ("random", "fixpoint", "only-maybe", "full")[k % 4]
        if kind == "random":
            p_mark, p_wrong, p_maybe = rng.random(), rng.random() * 0.4, rng.random() * 0.5
            cells = []
            for t in truth:
                roll = rng.random()
                cells.append(M if roll < p_maybe else
                             ((wrong[t] if rng.random() < p_wrong else t) if rng.random() < p_mark else U))
            if M not in cells:
                cells[rng.randrange(len(cells))] = M
        elif kind == "fixpoint":
            cells = list(fixed)
            for index in rng.sample(range(len(cells)), rng.randint(1, max(1, len(cells) // 10))):
                cells[index] = M
        elif kind == "only-maybe":
            cells = list(truth)
            for index in rng.sample(range(len(cells)), rng.randint(1, max(1, len(cells) // 4))):
                cells[index] = M
        else:
            cells = [wrong[t] if rng.random() < 0.05 else t for t in truth]
            for index in rng.sample(range(len(cells)), rng.randint(1, 6)):
                cells[index] = M
        boards.append((cells, kind))
    return solution, rows, columns, boards


@pytest.mark.browser
def test_PropertyTest_SolverMaybe_HintReadsMaybeAsUndecided(browser_page, live) -> None:
    """AC-11 — hintCell on a board equals hintCell on the same board with every
    "?" turned undecided (same cell, state and deduced), and both equal
    CARD-183's oracle on the turned board."""
    _open(browser_page, live, live.store(GRID))
    rng = random.Random(1861)
    returned_maybe = only_maybe = 0
    for width, height in _HINT_SHAPES:
        solution, rows, columns, boards = _hint_corpus(width, height, rng)
        got = browser_page.evaluate(_HINT_PAIRS, {
            "width": width, "height": height, "rows": rows, "columns": columns, "solution": solution,
            "boards": [[_text(cells), _text(_without_maybe(cells))] for cells, _ in boards],
        })
        assert len(boards) >= 200 and len(got) == len(boards)
        for index, ((cells, kind), (with_maybe, without)) in enumerate(zip(boards, got)):
            where = ((width, height), index, kind)
            assert M in cells, where
            assert with_maybe == without, where
            want = _oracle_hint(_without_maybe(cells), rows, columns, solution)
            assert (None if without is None else tuple(without)) == want, where
            if with_maybe is not None and cells[with_maybe[0] * width + with_maybe[1]] == M:
                returned_maybe += 1
            not_correct = [s for i, s in enumerate(cells) if s != _truth(solution, i)]
            only_maybe += bool(not_correct) and set(not_correct) == {M}
    assert returned_maybe >= 30, returned_maybe
    assert only_maybe >= 10, only_maybe


# --------------------------------------------------------------------------
# The clue circles (CARD-188) read "?" as undecided
# --------------------------------------------------------------------------

_CIRCLE_SHAPES = [(10, 10), (15, 10), (10, 25)]
_CIRCLE_PER_SHAPE = 100

_CIRCLE_TRIPLES = """async ({ width, height, rows, columns, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY, m: S.MAYBE };
  const circles = (text) => {
    const board = Object.freeze({ width, height, cells: Object.freeze([...text].map((ch) => codes[ch])) });
    if (!S.isBoard(board)) throw new Error('not a board');
    const got = S.circledClues(board, rows, columns);
    return JSON.stringify([got.rows, got.columns]);
  };
  return boards.map((texts) => texts.map(circles));
}"""


def _lines(cells, width, height):
    rows = [cells[r * width:(r + 1) * width] for r in range(height)]
    return rows + [cells[c::width] for c in range(width)]


def _maybe_matters(cells, width, height):
    """A "?" sits next to a dark run, or is the only non-white cell of a line."""
    for line in _lines(cells, width, height):
        for i, s in enumerate(line):
            if s != M:
                continue
            if (i > 0 and line[i - 1] == F) or (i + 1 < len(line) and line[i + 1] == F):
                return True
            if all(x == E for j, x in enumerate(line) if j != i):
                return True
    return False


def _circle_corpus(width, height, rng):
    """Boards over one solution (with an all-empty row and column, so [0]
    clues occur): mostly correct marks, some undecided, and "?" placed on
    cells next to the solution's runs and at random."""
    solution = [[rng.random() < 0.5 for _ in range(width)] for _ in range(height)]
    solution[rng.randrange(height)] = [False] * width
    empty_col = rng.randrange(width)
    for row in solution:
        row[empty_col] = False
    rows, columns = _clues(solution)
    truth = [F if cell else E for row in solution for cell in row]
    edges = [i for i, t in enumerate(truth) if t == E and any(
        0 <= j < len(truth) and truth[j] == F and (j // width == i // width or j % width == i % width)
        for j in (i - 1, i + 1, i - width, i + width))]
    boards = []
    for k in range(_CIRCLE_PER_SHAPE):
        cells = [U if rng.random() < 0.1 * (k % 3) else t for t in truth]
        for index in rng.sample(edges, rng.randint(1, 4)):
            cells[index] = M
        for index in rng.sample(range(len(cells)), rng.randint(0, 3)):
            cells[index] = M
        boards.append(cells)
    return rows, columns, boards


@pytest.mark.browser
def test_PropertyTest_SolverMaybe_CirclesReadMaybeAsUndecided(browser_page, live) -> None:
    """circledClues of a board with "?" equals circledClues of the same board
    with every "?" turned undecided. The corpus is one where reading "?" as
    white would change the circles on many boards."""
    _open(browser_page, live, live.store(GRID))
    rng = random.Random(1868)
    total = matters = differs_as_white = 0
    for width, height in _CIRCLE_SHAPES:
        rows, columns, boards = _circle_corpus(width, height, rng)
        got = browser_page.evaluate(_CIRCLE_TRIPLES, {
            "width": width, "height": height, "rows": rows, "columns": columns,
            "boards": [[_text(cells), _text(_without_maybe(cells)), _text(_without_maybe(cells, E))]
                       for cells in boards],
        })
        assert len(got) == len(boards)
        for index, (cells, (with_maybe, as_unknown, as_white)) in enumerate(zip(boards, got)):
            assert M in cells, ((width, height), index)
            assert with_maybe == as_unknown, ((width, height), index)
            total += 1
            matters += _maybe_matters(cells, width, height)
            differs_as_white += as_white != as_unknown
    assert total >= 200, total
    assert matters >= 150, matters
    assert differs_as_white >= 100, differs_as_white


# ==========================================================================
# The page
# ==========================================================================


@pytest.mark.browser
class TestSolverMaybe_ClickWithTheMaybeTool:
    """AC-3 — real mouse clicks with Maybe, and on a "?" with another tool."""

    def test_two_clicks_mark_then_clear(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Maybe")
        _cell(browser_page, 4, 6).click()
        assert _marked(_states(browser_page)) == {(4, 6): M}
        _cell(browser_page, 4, 6).click()
        assert _marked(_states(browser_page)) == {}

    def test_a_black_cell_clicked_with_maybe_reads_maybe(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 2, 2).click()  # Black is pressed at load
        assert _marked(_states(browser_page)) == {(2, 2): F}
        _tool(browser_page, "Maybe")
        _cell(browser_page, 2, 2).click()
        assert _marked(_states(browser_page)) == {(2, 2): M}

    # CARD-189: a "?" clicked with a colour brush takes that brush's state
    # (CARD-186's interim rule sent it to black whatever the brush).
    @pytest.mark.parametrize("tool, after", [("Black", F), ("White", E), ("Undecided", U)])
    def test_a_maybe_cell_clicked_with_another_tool_takes_its_state(self, browser_page, live, tool, after) -> None:
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Maybe")
        _cell(browser_page, 7, 3).click()
        assert _marked(_states(browser_page)) == {(7, 3): M}
        _tool(browser_page, tool)
        _cell(browser_page, 7, 3).click()
        assert _marked(_states(browser_page)) == ({(7, 3): after} if after != U else {})


@pytest.mark.browser
class TestSolverMaybe_DragPaintsMaybe:
    """AC-4 — a Maybe drag paints "?" over whatever the cells held; a White
    drag over "?" cells makes them white."""

    def test_drag(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 2, 3).click()  # black
        _cell(browser_page, 2, 4).click()
        _cell(browser_page, 2, 4).click()  # white
        _tool(browser_page, "White")
        _drag(browser_page, [(2, 6), (2, 9)])
        _cell(browser_page, 5, 5).click()  # off the line; White selected: white (CARD-189)
        before = _marked(_states(browser_page))
        assert before == {(2, 3): F, (2, 4): E, (2, 6): E, (2, 7): E, (2, 8): E, (2, 9): E, (5, 5): E}

        _tool(browser_page, "Maybe")
        _drag(browser_page, [(2, 3), (2, 7)])
        after = _marked(_states(browser_page))
        assert after == {**before, **{(2, c): M for c in range(3, 8)}}

        _tool(browser_page, "White")
        _drag(browser_page, [(2, 5), (2, 6)])
        assert _marked(_states(browser_page)) == {**after, (2, 5): E, (2, 6): E}


@pytest.mark.browser
class TestSolverMaybe_BlocksTheSolvedState:
    """AC-7 — blacks right, one "?" on a solution-empty cell: not solved, not
    locked, 0 errors; clearing the "?" with Maybe solves and locks."""

    def test_one_maybe_left(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        r, c = _EMPTY[len(_EMPTY) // 2]
        cells = [F if cell else U for row in GRID for cell in row]
        cells[r * SIDE + c] = M
        _set(browser_page, cells)

        assert not _is_solved_shown(browser_page)
        assert _error_count(browser_page) == 0
        assert browser_page.locator("table.player-board.is-solved").count() == 0
        assert browser_page.locator(".player-tools").is_visible()

        _tool(browser_page, "Maybe")
        _cell(browser_page, r, c).click()

        assert _is_solved_shown(browser_page)
        assert browser_page.locator("table.player-board.is-solved").count() == 1
        solved = _states(browser_page)
        assert solved[r * SIDE + c] == U
        _cell(browser_page, *_EMPTY[0]).click()  # locked: a click changes nothing
        assert _states(browser_page) == solved


@pytest.mark.browser
class TestSolverMaybe_UndoRedo:
    """AC-9 — a "?" click and a "?" drag are one undo step each (buttons,
    then Ctrl/Cmd+Z)."""

    @pytest.mark.parametrize("modifier", ["Control", "Meta"])
    def test_undo_redo(self, browser_page, live, modifier) -> None:
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Maybe")
        _cell(browser_page, 3, 3).click()
        _drag(browser_page, [(6, 2), (6, 6)])
        click = {(3, 3): M}
        both = {**click, **{(6, c): M for c in range(2, 7)}}
        assert _marked(_states(browser_page)) == both

        seen = []
        for name in ("Undo", "Undo", "Redo", "Redo"):
            _button(browser_page, name).click()
            seen.append(_marked(_states(browser_page)))
        assert seen == [click, {}, click, both]

        browser_page.locator("h1").click()
        seen = []
        for keys in (f"{modifier}+z", f"{modifier}+z", f"Shift+{modifier}+z", f"Shift+{modifier}+z"):
            browser_page.keyboard.press(keys)
            seen.append(_marked(_states(browser_page)))
        assert seen == [click, {}, click, both]


@pytest.mark.browser
class TestSolverMaybe_ResetClearsMaybe:
    """AC-10 — a board of only "?" marks can be reset; Clear board clears them."""

    def test_reset(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cells = [U] * (SIDE * SIDE)
        for r, c in ((0, 0), (4, 9), (14, 14)):
            cells[r * SIDE + c] = M
        _set(browser_page, cells)
        assert _button(browser_page, "Reset").get_attribute("aria-disabled") == "false"

        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()

        assert set(_states(browser_page)) == {U}


@pytest.mark.browser
class TestSolverMaybe_HintMayOverwriteMaybe:
    """AC-12 — every cell correct but some "?": Hint reveals one "?" cell and
    Undo brings it back."""

    def test_hint(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cells = [F if cell else E for row in GRID for cell in row]
        maybes = [_FILLED[3], _EMPTY[5], _FILLED[-2]]
        for r, c in maybes:
            cells[r * SIDE + c] = M
        _set(browser_page, cells)
        want = _grid_hint(_without_maybe(cells))
        assert want is not None and (want[0], want[1]) in maybes
        assert _button(browser_page, "Hint").get_attribute("aria-disabled") == "false"
        hints = browser_page.locator("[data-player-hints]")
        assert hints.text_content() == "0"

        _button(browser_page, "Hint").click()

        after = _states(browser_page)
        changed = {(i // SIDE, i % SIDE): s for i, (b, s) in enumerate(zip(cells, after)) if b != s}
        assert changed == {(want[0], want[1]): want[2]}
        assert hints.text_content() == "1"

        _button(browser_page, "Undo").click()
        assert _states(browser_page) == cells
        assert hints.text_content() == "0"


_GLYPH = """(td) => {
  const after = getComputedStyle(td, '::after');
  const r = td.getBoundingClientRect();
  return { content: after.content, fontSize: parseFloat(after.fontSize), color: after.color,
           background: getComputedStyle(td).backgroundColor,
           rect: [r.left, r.top, r.right, r.bottom], dpr: devicePixelRatio,
           viewport: [innerWidth, innerHeight] };
}"""


def _rgb(text):
    parts = text[text.index("(") + 1:text.index(")")].replace(",", " ").split()
    return tuple(float(p) for p in parts[:3])


def _contrast(a, b):
    def luminance(rgb):
        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b_ = (channel(v) for v in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _glyph_box(page, cells, r, c, width):
    """The bounding box, in viewport px, of the pixels that change when cell
    (r, c) goes from undecided to "?" — the rendered glyph."""
    from PIL import Image, ImageChops

    cell = page.locator(f'td.player-cell[data-row="{r}"][data-col="{c}"]')
    cell.evaluate("(td) => td.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' })")
    blank = list(cells)
    blank[r * width + c] = U
    marked = list(cells)
    marked[r * width + c] = M
    _set(page, blank)
    before = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    _set(page, marked)
    after = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    diff = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v > 24 else 0)
    return diff.getbbox(), cell


@pytest.mark.browser
class TestSolverMaybe_GlyphIsLegibleAtTheMinimumCell:
    """AC-13 — the "?" cell's ::after is "?", at least 12 px and 0.5 x the cell
    side, drawn inside the cell (both axes), with >= 4.5:1 contrast on the
    cell's background."""

    @pytest.mark.parametrize("case", ["30x30@390", "15x15@1440"])
    def test_glyph(self, browser_page, live, case) -> None:
        grid, viewport, (r, c) = {
            "30x30@390": (BIG, {"width": 390, "height": 844}, (12, 20)),
            "15x15@1440": (GRID, {"width": 1440, "height": 900}, (7, 7)),
        }[case]
        width = len(grid[0])
        browser_page.set_viewport_size(viewport)
        _open(browser_page, live, live.store(grid))
        cells = [U] * (width * len(grid))
        cells[0] = F  # Reset stays enabled in both screenshots, so only the cell differs
        box, cell = _glyph_box(browser_page, cells, r, c, width)
        seen = cell.evaluate(_GLYPH)
        left, top, right, bottom = seen["rect"]
        side = right - left
        assert 0 <= left and right <= seen["viewport"][0] and 0 <= top and bottom <= seen["viewport"][1], seen
        if case.endswith("@390"):
            # CARD-193 removed the CARD-182 24 px phone floor; this grid's
            # two-digit column numbers still bind CARD-196's 14.4 px
            # column-numeral floor instead (measured, not the old literal).
            assert side == pytest.approx(14.39, abs=0.05), side

        assert seen["content"] == '"?"'
        assert seen["fontSize"] >= 12 and seen["fontSize"] >= 0.5 * side, (seen["fontSize"], side)
        assert box is not None, "the glyph drew nothing"
        dpr = seen["dpr"]
        g_left, g_top, g_right, g_bottom = (v / dpr for v in box)
        assert left <= g_left and g_right <= right, (box, seen["rect"])
        assert top <= g_top and g_bottom <= bottom, (box, seen["rect"])
        ratio = _contrast(_rgb(seen["color"]), _rgb(seen["background"]))
        assert ratio >= 4.5, ratio


@pytest.mark.browser
class TestSolverMaybe_ToolKeyboardAndLabel:
    """AC-14 — the Maybe tool: name, Tab place, Enter / Space, hidden swatch."""

    def test_name_and_swatch(self, browser_page, live) -> None:
        from playwright.sync_api import expect

        _open(browser_page, live, live.store(GRID))
        button = _button(browser_page, "Maybe")
        assert button.count() == 1
        expect(button).to_have_accessible_name("Maybe")
        assert button.get_attribute("data-player-tool") == M
        swatch = button.locator(".player-swatch")
        assert swatch.get_attribute("aria-hidden") == "true"
        assert swatch.get_attribute("data-state") == M
        assert swatch.evaluate("(s) => getComputedStyle(s, '::after').content") == '"?"'

    def test_tab_reaches_it_between_undecided_and_undo(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        browser_page.evaluate("document.activeElement && document.activeElement.blur()")
        reached = []
        for _ in range(80):
            browser_page.keyboard.press("Tab")
            focused = browser_page.evaluate(_FOCUSED)
            if focused and focused not in reached:
                reached.append(focused)
            if "Undo" in reached:
                break
        assert reached[-3:] == ["Undecided", "Maybe", "Undo"], reached

    @pytest.mark.parametrize("key", ["Enter", "Space"])
    def test_enter_and_space_select_it(self, browser_page, live, key) -> None:
        _open(browser_page, live, live.store(GRID))
        assert _pressed(browser_page)["Black"] == "true"
        _button(browser_page, "Maybe").focus()
        browser_page.keyboard.press(key)
        assert _pressed(browser_page) == {"Black": "false", "White": "false", "Undecided": "false", "Maybe": "true"}
        _cell(browser_page, 9, 9).click()  # the selected tool governs the click
        assert _marked(_states(browser_page)) == {(9, 9): M}


@pytest.mark.browser
class TestSolverMaybe_NoRequestPerMark:
    """AC-15 — ten "?" strokes: no request, nothing stored, a clean console."""

    def test_no_request(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.context.on("request", lambda request: requests.append(request.url))

        _tool(browser_page, "Maybe")
        for k in range(5):
            _cell(browser_page, k, (2 * k) % SIDE).click()
            _drag(browser_page, [(10 + k % 5, 1), (10 + k % 5, 4 + k)])
        marks = _marked(_states(browser_page))
        assert len(marks) >= 10 and set(marks.values()) == {M}

        stored = browser_page.evaluate(_ONLY_THIS_SAVE)
        assert requests == []
        assert stored
        assert problems == []


# ==========================================================================
# Review F-001 (cycle 1) — the solved banner never moves the board
# ==========================================================================

#: Viewport widths swept (height 900): 960..1480 step 20, plus the phone.
_SWEEP = [(w, 900) for w in range(960, 1481, 20)] + [(390, 844)]

_TOOLBAR_BOXES = """() => {
  const box = (el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  const q = (s) => document.querySelector(s);
  return {
    tools: box(q('.player-tools')),
    banner: box(q('#puzzle-player-solved')),
    others: [...document.querySelectorAll(
      '.player-history > button, .player-errors, .player-hints, .player-board')].map(box),
  };
}"""


def _overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _solve_and_measure(page):
    """Near-solved GRID, then the real solving click; the board's box before
    and after, the toolbar boxes after, and the tools' box before."""
    _set(page, _near_solved(U))
    assert not _is_solved_shown(page)
    # Scroll first, so the click itself scrolls nothing (on the phone the
    # stage and the page would otherwise scroll to reach the cell).
    _cell(page, *LAST).scroll_into_view_if_needed()
    before = page.locator(".player-board").bounding_box()
    tools_before = page.evaluate(_TOOLBAR_BOXES)["tools"]
    _cell(page, *LAST).click()
    assert _is_solved_shown(page)
    after = page.locator(".player-board").bounding_box()
    # The banner settles in from a small translateY; measure it settled.
    page.evaluate("Promise.all(document.getAnimations().map((a) => a.finished))")
    boxes = page.evaluate(_TOOLBAR_BOXES)
    boxes["tools_before"] = tools_before
    return before, after, boxes


@pytest.mark.browser
class TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth:
    """With four tools the toolbar wraps differently across widths; the
    solved banner takes the tools' box (the tools stay in layout, hidden), so
    the board's box is the same before and after the solving click at every
    swept width (960..1480 step 20 at height 900, and 390 x 844), on both
    axes. The banner (here "Lighthouse") lies inside the tools' box,
    centred down it (within 1 px), and overlaps none of the other controls
    or the board."""

    def test_sweep(self, browser, live) -> None:
        puzzle = live.store(GRID, name=NAME)
        moved, misplaced, checked = [], [], 0
        for width, height in _SWEEP:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            try:
                _open(page, live, puzzle)
                before, after, boxes = _solve_and_measure(page)
                tools_hidden = not page.locator(".player-tools").is_visible()
            finally:
                context.close()
            checked += 1
            if (before["x"], before["y"]) != (after["x"], after["y"]):
                moved.append((width, after["x"] - before["x"], after["y"] - before["y"]))
            tl, tt, tr, tb = boxes["tools"]
            bl, bt, br, bb = boxes["banner"]
            inside = tl - 0.5 <= bl and br <= tr + 0.5 and tt - 0.5 <= bt and bb <= tb + 0.5
            inside = inside and abs((bt + bb) / 2 - (tt + tb) / 2) <= 1  # centred down the tools' box
            if not (tools_hidden and inside) or any(_overlaps(boxes["banner"], o) for o in boxes["others"]):
                misplaced.append((width, boxes))
        assert checked == len(_SWEEP) == 28
        assert moved == [], " ".join(f"{w}:{dx:+g},{dy:+g}" for w, dx, dy in moved)
        assert misplaced == []


#: The longest name the panel accepts (MAX_PUZZLE_NAME_LENGTH, 120 characters),
#: as words and as one unbroken token (a name falls back to the source file name).
_LONG_NAMES = [
    ("The lighthouse keeper's cottage on the northern cliffs, "
     "seen at dawn from the harbour wall, with gulls and fishing boats")[:120],
    ("lighthouse_keepers_cottage_on_the_northern_cliffs_seen_at_dawn_"
     "from_the_harbour_wall_with_gulls_and_fishing_boats_v2.png")[:120],
]


@pytest.mark.browser
class TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth:
    """A 120-character picture name, as words or as one unbroken token, wraps
    inside the tools' width: the tools'
    box is the same before and after solving (the banner does not widen it),
    the banner lies within its width, and it runs into none of the history
    controls, the counters or the board; the whole name stays shown and the
    check icon keeps its 1em square. Only
    width and overlap are claimed: a name too long for the tools' box makes
    the toolbar row taller (and so moves the board)."""

    @pytest.mark.parametrize("long_name", _LONG_NAMES, ids=["words", "one-token"])
    @pytest.mark.parametrize("width,height", [(1440, 900), (1200, 900), (390, 844)])
    def test_wraps(self, browser, live, width, height, long_name) -> None:
        assert len(long_name) == 120
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID, name=long_name))
            _, _, boxes = _solve_and_measure(page)
            name = page.locator("[data-player-solved-name]").inner_text()
            icon = page.locator("#puzzle-player-solved .icon").bounding_box()
            text_px = page.locator("#puzzle-player-solved").evaluate("(el) => parseFloat(getComputedStyle(el).fontSize)")
        finally:
            context.close()
        assert name == long_name
        assert icon["width"] == icon["height"] == text_px  # the check icon is not squeezed (1em square)
        # The banner does not widen the tools' box (its height may grow).
        assert boxes["tools"][0::2] == boxes["tools_before"][0::2]
        tl, _, tr, _ = boxes["tools"]
        bl, _, br, _ = boxes["banner"]
        assert tl - 0.5 <= bl and br <= tr + 0.5, boxes
        assert not any(_overlaps(boxes["banner"], other) for other in boxes["others"]), boxes


_TOOLBAR_ROWS = """() => {
  const centres = [...document.querySelectorAll(
    '.player-tools > button, .player-history > button, .player-errors, .player-hints')]
    .map((el) => { const r = el.getBoundingClientRect(); return Math.round((r.top + r.bottom) / 2); });
  return new Set(centres).size;
}"""


@pytest.mark.browser
class TestSolverMaybe_FourToolsKeepOneToolbarRowAt1280:
    """At 1280 x 720 (the default viewport) the four tools, Undo / Redo /
    Reset / Hint and both counters share one toolbar row, as the three tools
    did before CARD-186."""

    def test_one_row(self, browser_page, live) -> None:
        assert browser_page.viewport_size == {"width": 1280, "height": 720}
        _open(browser_page, live, live.store(GRID))
        assert browser_page.evaluate(_TOOLBAR_ROWS) == 1


@pytest.mark.browser
class TestSolverMaybe_HiddenToolsAreOutOfReachWhenSolved:
    """Solved, the tools keep their box but are hidden: no tool is a button
    by role, focus() does not take, and Tab from the top of the page reaches
    Reset without passing any tool."""

    def test_out_of_reach(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID, name=NAME))
        _solve_and_measure(browser_page)
        tools = ("Black", "White", "Undecided", "Maybe")
        assert [browser_page.get_by_role("button", name=t, exact=True).count() for t in tools] == [0, 0, 0, 0]
        focused = browser_page.evaluate("""() => [...document.querySelectorAll('[data-player-tool]')]
          .map((b) => { b.focus(); return document.activeElement === b; })""")
        assert focused == [False] * 4
        browser_page.evaluate("document.activeElement && document.activeElement.blur()")
        seen = []
        for _ in range(60):
            browser_page.keyboard.press("Tab")
            here = browser_page.evaluate(
                "(() => { const a = document.activeElement; return a.dataset.playerTool || a.dataset.playerAction || ''; })()")
            seen.append(here)
            if here == "reset":
                break
        assert "reset" in seen
        assert not set(seen) & {"filled", "empty", "unknown", "maybe"}
