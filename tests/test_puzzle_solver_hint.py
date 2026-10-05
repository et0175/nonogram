"""CARD-183 — the puzzle player's Hint button (IDEA-074; FR-044 extension,
card-local AC-1..AC-11).

A hint reveals one undecided cell, set to its solution state, as one undoable
stroke: the first cell, row-major, that one pass of line logic over its row
or its column forces from the player's correct marks (wrong marks count as
undecided); when no cell is forced that way, the first undecided cell, from
the solution, and the announcement says so.

The line solver (``solver_state.js`` ``lineForced``) is cross-checked against
two independent implementations: the uniqueness solver's
``nonogram.solver.propagate.line_intersection`` (imported here, from the test
tree, as an oracle only — COMP-005 is not touched) and the brute-force
``line_candidates`` of ``tests/helpers/brute_force_oracle.py``. ``hintCell`` is
checked against an oracle written below on top of ``line_intersection``. The
corpora are built with ``random.Random`` and fixed seeds (no ``hypothesis``),
their minimum counts asserted inside the tests.

User-facing criteria drive real input in Chromium (``locator.click``,
``page.keyboard``, ``page.mouse``); ``puzzlePlayer.setBoard`` only sets up the
board before the hint. Fixtures are CARD-160's, page helpers CARD-161/162's.
"""

from __future__ import annotations

import random

import pytest

from nonogram.solver import solve
from nonogram.solver.propagate import canonical_clue, line_intersection
from tests.helpers.brute_force_oracle import line_candidates
from tests.test_puzzle_solver_marking import (
    _FOCUSED,
    GRID,
    SIDE,
    E,
    F,
    U,
    _button,
    _cell,
    _centre,
    _is_disabled,
    _marked,
    _states,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_progress import (
    _MOTION,
    LAST,
    NAME,
    _error_count,
    _is_solved_shown,
    _near_solved,
    _open_named,
    _set,
    _watch_problems,
)

_CODE = {U: "u", F: "f", E: "e"}
_STATE = {"u": U, "f": F, "e": E}


# --------------------------------------------------------------------------
# The oracles, on top of the uniqueness solver's line logic
# --------------------------------------------------------------------------


def _forced(clue, cells):
    """line_intersection on one line of cell states: the line with every
    agreed cell set, or None when no placement fits."""
    length = len(cells)
    known_filled = sum(1 << i for i, s in enumerate(cells) if s == F)
    known_empty = sum(1 << i for i, s in enumerate(cells) if s == E)
    result = line_intersection(canonical_clue(tuple(clue)), length, known_filled, known_empty)
    if result is None:
        return None
    filled, empty, _ = result
    return [F if filled >> i & 1 else E if empty >> i & 1 else U for i in range(length)]


def _by_brute_force(clue, cells):
    """The intersection of every line with this clue that agrees with the
    knowns, by enumeration; None when none agrees."""
    fits = [
        line for line in line_candidates(tuple(clue), len(cells))
        if all(s == U or (s == F) == cell for s, cell in zip(cells, line))
    ]
    if not fits:
        return None
    return [F if all(line[i] for line in fits) else E if not any(line[i] for line in fits) else U
            for i in range(len(cells))]


def _truth(solution, r, c):
    return F if solution[r][c] else E


def _first_deducible(cells, knowns, rows, columns, solution):
    """The first UNKNOWN cell of ``cells``, row-major, that one
    line_intersection pass over its row or its column forces from
    ``knowns`` (a line with no placement deduces nothing); else None."""
    height, width = len(rows), len(columns)
    by_row = [_forced(rows[r], [knowns[r * width + c] for c in range(width)]) for r in range(height)]
    by_col = [_forced(columns[c], [knowns[r * width + c] for r in range(height)]) for c in range(width)]
    for r in range(height):
        for c in range(width):
            if cells[r * width + c] != U:
                continue
            if (by_row[r] and by_row[r][c] != U) or (by_col[c] and by_col[c][r] != U):
                return (r, c, _truth(solution, r, c), True)
    return None


def _correct_only(cells, solution):
    width = len(solution[0])
    return [s if s == _truth(solution, i // width, i % width) else U for i, s in enumerate(cells)]


def _oracle_hint(cells, rows, columns, solution):
    """The criterion: (row, col, state, deduced) or None."""
    width = len(columns)
    found = _first_deducible(cells, _correct_only(cells, solution), rows, columns, solution)
    if found:
        return found
    first = next((i for i, s in enumerate(cells) if s == U), None)
    if first is None:
        return None
    return (first // width, first % width, _truth(solution, first // width, first % width), False)


def _face_value_hint(cells, rows, columns, solution):
    """What a hint would be if every mark were taken at face value (wrong
    marks included) — used only to count boards where ignoring wrong marks
    makes a difference."""
    return _first_deducible(cells, list(cells), rows, columns, solution)


def _face_value_forces(cells, rows, columns, r, c):
    """Whether one pass over row ``r`` or column ``c``, every mark taken at
    face value (wrong marks included), forces cell (r, c); a line with no
    placement forces nothing."""
    width, height = len(columns), len(rows)
    by_row = _forced(rows[r], [cells[r * width + j] for j in range(width)])
    by_col = _forced(columns[c], [cells[i * width + c] for i in range(height)])
    return bool((by_row and by_row[c] != U) or (by_col and by_col[r] != U))


def _fixpoint(rows, columns):
    """Line logic to a fixed point from a blank board (correct knowns only)."""
    height, width = len(rows), len(columns)
    board = [U] * (width * height)
    changed = True
    while changed:
        changed = False
        for r in range(height):
            line = _forced(rows[r], board[r * width:(r + 1) * width])
            for c in range(width):
                if board[r * width + c] != line[c]:
                    board[r * width + c] = line[c]
                    changed = True
        for c in range(width):
            line = _forced(columns[c], board[c::width])
            for r in range(height):
                if board[r * width + c] != line[r]:
                    board[r * width + c] = line[r]
                    changed = True
    return board


def _clues(grid):
    return [_encode(row) for row in grid], [_encode(col) for col in zip(*grid)]


def _fallback_grid():
    """A 10 x 10 grid with exactly one solution that line logic alone does not
    solve: at its line-logic fixed point no undecided cell is forced by one
    line, which is the fallback's board (AC-6)."""
    rng = random.Random(183)
    for _ in range(2000):
        grid = [[rng.random() < 0.55 for _ in range(10)] for _ in range(10)]
        rows, columns = _clues(grid)
        if not solve(tuple(map(tuple, rows)), tuple(map(tuple, columns))).is_unique:
            continue
        board = _fixpoint(rows, columns)
        if U in board:
            return grid, board
    raise AssertionError("no unique, not line-solvable 10 x 10 grid in 2000 draws")


# ==========================================================================
# The pure module, in the browser
# ==========================================================================

_LINES = """async (lines) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY };
  const back = { [S.UNKNOWN]: 'u', [S.FILLED]: 'f', [S.EMPTY]: 'e' };
  return lines.map(([clue, text]) => {
    const got = S.lineForced(clue, [...text].map((ch) => codes[ch]));
    return got === null ? null : got.map((s) => back[s]).join('');
  });
}"""

_HINTS = """async ({ width, height, rows, columns, solution, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY };
  return boards.map((text) => {
    const board = Object.freeze({ width, height, cells: Object.freeze([...text].map((ch) => codes[ch])) });
    if (!S.isBoard(board)) throw new Error('not a board');
    const hint = S.hintCell(board, rows, columns, solution);
    return hint === null ? null : [hint.row, hint.col, hint.state, hint.deduced];
  });
}"""


def _text(cells):
    return "".join(_CODE[s] for s in cells)


def _line_corpus(rng, count, max_length):
    """Lines with clues from random solution lines and knowns a random subset
    of that line (a solution always fits)."""
    lines = []
    for k in range(count):
        length = rng.randint(1, max_length) if k >= max_length else k + 1  # every length once first
        density = rng.choice((0.2, 0.5, 0.8, rng.random()))
        line = [rng.random() < density for _ in range(length)]
        known = rng.choice((0.0, 0.2, 0.5, 0.8, 1.0))
        cells = [(F if cell else E) if rng.random() < known else U for cell in line]
        lines.append((_encode(line), cells))
    return lines


def _contradicting_corpus(rng, count, max_length, oracle):
    """Lines whose knowns contradict their clue (``oracle`` says None)."""
    lines = []
    while len(lines) < count:
        length = rng.randint(1, max_length)
        clue = _encode([rng.random() < 0.5 for _ in range(length)])
        cells = [rng.choice((U, U, F, E)) for _ in range(length)]
        if oracle(clue, cells) is None:
            lines.append((clue, cells))
    return lines


def _run_lines(page, lines):
    got = page.evaluate(_LINES, [[clue, _text(cells)] for clue, cells in lines])
    assert len(got) == len(lines)
    return [None if g is None else [_STATE[ch] for ch in g] for g in got]


@pytest.mark.browser
def test_PropertyTest_SolverHint_LineForcedMatchesThePythonLineSolver(browser_page, live) -> None:
    """AC-1 — lineForced's forced cells and null verdicts equal
    line_intersection's on every line of a seeded corpus."""
    _open(browser_page, live, live.store(GRID))
    rng = random.Random(1831)
    lines = _line_corpus(rng, 2400, 30) + _contradicting_corpus(rng, 300, 30, _forced)
    expected = [_forced(clue, cells) for clue, cells in lines]

    assert len(lines) >= 2000
    assert {len(cells) for _, cells in lines} == set(range(1, 31))
    assert sum(e is None for e in expected) >= 200
    # Lines where the solver deduces something new, and lines where it
    # leaves cells undecided: neither "copy the knowns" nor "decide all" passes.
    assert sum(e is not None and e != cells for e, (_, cells) in zip(expected, lines)) >= 500
    assert sum(e is not None and U in e for e in expected) >= 500
    assert sum(clue == [0] for clue, _ in lines) >= 20
    for index, (got, want) in enumerate(zip(_run_lines(browser_page, lines), expected)):
        assert got == want, (index, lines[index])


@pytest.mark.browser
def test_PropertyTest_SolverHint_LineForcedMatchesBruteForce(browser_page, live) -> None:
    """AC-2 — on lines of at most 12 cells, lineForced equals the intersection
    of the brute-force candidates that agree with the knowns."""
    _open(browser_page, live, live.store(GRID))
    rng = random.Random(1832)
    lines = _line_corpus(rng, 600, 12) + _contradicting_corpus(rng, 100, 12, _by_brute_force)
    expected = [_by_brute_force(clue, cells) for clue, cells in lines]

    assert len(lines) >= 500
    assert max(len(cells) for _, cells in lines) <= 12
    assert sum(e is None for e in expected) >= 50
    assert sum(e is not None and e != cells for e, (_, cells) in zip(expected, lines)) >= 100
    assert sum(e is not None and U in e for e in expected) >= 100
    for index, (got, want) in enumerate(zip(_run_lines(browser_page, lines), expected)):
        assert got == want, (index, lines[index])


#: (width, height): square and non-square, smallest to largest.
_SHAPES = [(10, 10), (15, 10), (10, 25), (30, 30)]
_PER_SHAPE = 240
_MIN_PER_SHAPE = 200


def _board_corpus(width, height, rng):
    """One solution per shape and boards of five kinds: random (correct,
    wrong and undecided marks), fixpoint (the line-logic fixed point — often
    no cell left to deduce), fixpoint with wrong marks over known cells,
    full (no undecided cell, some wrong), and sparse (a few marks, many of
    them wrong)."""
    solution = [[rng.random() < 0.55 for _ in range(width)] for _ in range(height)]
    rows, columns = _clues(solution)
    truth = [F if cell else E for row in solution for cell in row]
    wrong = {F: E, E: F}
    fixed = _fixpoint(rows, columns)
    boards = []
    for k in range(_PER_SHAPE):
        kind = ("random", "fixpoint", "fixpoint-wrong", "full", "sparse")[k % 5]
        if kind == "random":
            p_mark, p_wrong = rng.random(), rng.random() * 0.4
            cells = [(wrong[t] if rng.random() < p_wrong else t) if rng.random() < p_mark else U for t in truth]
        elif kind == "fixpoint":
            cells = list(fixed)
            for index in rng.sample(range(len(cells)), rng.randint(0, 3)):
                cells[index] = U  # a few more undecided, so boards differ
        elif kind == "fixpoint-wrong":
            cells = list(fixed)
            known = [i for i, s in enumerate(cells) if s != U] or list(range(len(cells)))
            for index in rng.sample(known, min(len(known), rng.randint(1, 4))):
                cells[index] = wrong[truth[index]]
        elif kind == "full":
            cells = [wrong[t] if rng.random() < 0.05 * (k % 3) else t for t in truth]
        else:
            cells = [U] * len(truth)
            for index in rng.sample(range(len(cells)), rng.randint(1, 2 * width)):
                cells[index] = wrong[truth[index]] if rng.random() < 0.6 else truth[index]
        boards.append((cells, kind))
    return solution, rows, columns, boards


@pytest.mark.browser
def test_PropertyTest_SolverHint_RevealsTheFirstDeducibleCell(browser_page, live) -> None:
    """AC-3 — hintCell: null iff nothing is undecided; otherwise an undecided
    cell with its solution state, the first one-pass deducible cell (correct
    marks only) when there is one, else the first undecided cell. At least 20
    boards have a wrong mark that hides the deduction: taken at face value,
    neither the revealed cell's row nor its column forces it."""
    _open(browser_page, live, live.store(GRID))
    rng = random.Random(1833)
    fallbacks = with_wrong = changed = hidden = nulls = deduced = 0
    for width, height in _SHAPES:
        solution, rows, columns, boards = _board_corpus(width, height, rng)
        got = browser_page.evaluate(_HINTS, {
            "width": width, "height": height, "rows": rows, "columns": columns,
            "solution": solution, "boards": [_text(cells) for cells, _ in boards],
        })
        assert len(boards) >= _MIN_PER_SHAPE
        assert len(got) == len(boards)
        for index, ((cells, kind), hint) in enumerate(zip(boards, got)):
            where = ((width, height), index, kind)
            want = _oracle_hint(cells, rows, columns, solution)
            if U not in cells:  # (i)
                assert hint is None, where
                nulls += 1
                continue
            assert hint is not None, where
            r, c, state, is_deduced = hint
            assert cells[r * width + c] == U, where  # (ii)
            assert state == _truth(solution, r, c), where
            assert (r, c, state, is_deduced) == want, where  # (iii) and (iv)
            fallbacks += not is_deduced
            deduced += is_deduced
            has_wrong = _correct_only(cells, solution) != cells
            with_wrong += has_wrong
            # Taken at face value, the wrong marks change the hint ...
            changed += bool(has_wrong and is_deduced
                            and _face_value_hint(cells, rows, columns, solution) != want)
            # ... and, the stricter case AC-3 counts, they hide this very
            # deduction: neither the cell's row nor its column forces it.
            hidden += bool(has_wrong and is_deduced
                           and not _face_value_forces(cells, rows, columns, r, c))
    assert fallbacks >= 30
    assert with_wrong >= 50
    assert hidden >= 20  # a wrong mark taken at face value would hide this deduction
    # Every hidden board also changes the hint; the corpus also holds boards
    # where a wrong mark only adds an earlier, spurious deduction while this
    # cell stays forced — the strict count must leave those out.
    assert changed > hidden
    assert nulls >= 30 and deduced >= 200


_PURE = """async () => {
  const S = await import('/static/solver_state.js');
  const board = (width, height, text) => Object.freeze({ width, height,
    cells: Object.freeze([...text].map((ch) => ({ u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY })[ch])) });
  const hint = (h) => (h === null ? null : [h.row, h.col, h.state, h.deduced]);
  const stroke = S.hintStroke(1, 0, S.FILLED);
  let history = S.createHistory(S.createBoard(2, 2));
  history = S.record(history, S.clickStroke(history.board, 0, 0));
  const counts = [S.hintCount(history)];
  history = S.record(history, stroke);
  counts.push(S.hintCount(history));
  history = S.record(history, S.hintStroke(1, 1, S.EMPTY));
  counts.push(S.hintCount(history));
  history = S.undo(history);
  counts.push(S.hintCount(history));
  history = S.redo(history);
  counts.push(S.hintCount(history));
  history = S.record(history, S.resetStroke(history.board));
  counts.push(S.hintCount(history));
  return {
    stroke: { frozen: Object.isFrozen(stroke) && Object.isFrozen(stroke.cells) && Object.isFrozen(stroke.cells[0]),
              cells: stroke.cells, state: stroke.state, hint: stroke.hint },
    counts,
    replayed: [...S.replay(S.createBoard(2, 2), history.done.map((e) => e.stroke)).cells],
    board: [...history.board.cells],
    // 1 x 1, clue [1], solution empty: the line forces FILLED, the hint
    // still carries the solution's state.
    fromSolution: hint(S.hintCell(board(1, 1, 'u'), [[1]], [[1]], [[false]])),
    // 2 x 1: the row clue [0] contradicts the correct black at (0, 0) — no
    // deduction from that row; column 1's [0] still forces (0, 1).
    nullRow: hint(S.hintCell(board(2, 1, 'fu'), [[0]], [[1], [0]], [[true, false]])),
    // ... and when column 1 has no placement either, the fallback.
    nullRowFallback: hint(S.hintCell(board(2, 1, 'fu'), [[0]], [[1], [2]], [[true, false]])),
    lines: [
      S.lineForced([0], [S.UNKNOWN, S.UNKNOWN]),
      S.lineForced([1], [S.UNKNOWN]),
      S.lineForced([1], [S.EMPTY]),
      S.lineForced([0], [S.FILLED]),
      S.lineForced([2], [S.UNKNOWN, S.UNKNOWN, S.UNKNOWN]),
      S.lineForced([1, 1], [S.UNKNOWN, S.UNKNOWN, S.UNKNOWN]),
      S.lineForced([1, 1], [S.UNKNOWN, S.UNKNOWN]),
    ],
  };
}"""


@pytest.mark.browser
class TestSolverHintModule:
    """hintStroke, hintCount, and hintCell / lineForced on hand-picked cases."""

    def test_cases(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        got = browser_page.evaluate(_PURE)
        assert got["stroke"] == {"frozen": True, "cells": [[1, 0]], "state": F, "hint": True}
        # click, +hint, +hint, undo, redo, reset (a reset keeps the count)
        assert got["counts"] == [0, 1, 2, 1, 2, 2]
        assert got["replayed"] == got["board"] == [U, U, U, U]
        assert got["fromSolution"] == [0, 0, E, True]
        assert got["nullRow"] == [0, 1, E, True]
        assert got["nullRowFallback"] == [0, 1, E, False]
        assert got["lines"] == [
            [E, E], [F], None, None, [U, F, U], [F, E, F], None,
        ]


# ==========================================================================
# The page
# ==========================================================================


def _hint(page):
    return _button(page, "Hint")


def _hints_shown(page):
    counter = page.locator("[data-player-hints]")
    assert counter.is_visible()
    return int(counter.text_content())


def _announced(page):
    return " ".join(page.locator("#puzzle-player-announce").text_content().split())


def _hinted(page):
    return page.evaluate(
        "[...document.querySelectorAll('td.player-cell.is-hinted')].map((td) => [+td.dataset.row, +td.dataset.col])")


def _changed(before, after, width=SIDE):
    return {(i // width, i % width): a for i, (b, a) in enumerate(zip(before, after)) if a != b}


_GRID_CLUES = _clues(GRID)


def _grid_hint(cells):
    return _oracle_hint(cells, *_GRID_CLUES, GRID)


def _color(state):
    return "black" if state == F else "white"


#: The hinted cell's computed outline and ring, after its animations end,
#: next to the tokens they should resolve to (read from a probe in the stage,
#: where --player-rule-major is defined).
_OUTLINE = """async (td) => {
  await Promise.all(td.getAnimations().map((a) => a.finished));
  const probe = document.createElement('div');
  probe.style.cssText = 'color: var(--color-accent); background-color: var(--grid-paper);'
    + ' width: var(--player-rule-major); height: 0; position: absolute;';
  document.querySelector('.player-stage').append(probe);
  const p = getComputedStyle(probe);
  const tokens = { accent: p.color, paper: p.backgroundColor, rule: parseFloat(p.width) };
  probe.remove();
  const s = getComputedStyle(td);
  return { ...tokens, style: s.outlineStyle, color: s.outlineColor, width: parseFloat(s.outlineWidth),
           offset: parseFloat(s.outlineOffset), shadow: s.boxShadow };
}"""


@pytest.mark.browser
class TestSolverHint_RevealsOneCell:
    """AC-4 — a blank 15 x 15 board: one real click on Hint reveals the
    oracle's cell, "Hints: 1", errors unchanged."""

    def test_one_click_reveals_the_oracles_cell(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        before = _states(browser_page)
        assert _hints_shown(browser_page) == 0 and _error_count(browser_page) == 0
        want = _grid_hint(before)
        assert want is not None and want[3]

        _hint(browser_page).click()

        r, c, state, _ = want
        assert _changed(before, _states(browser_page)) == {(r, c): state}
        assert _hints_shown(browser_page) == 1
        assert _error_count(browser_page) == 0
        assert _hinted(browser_page) == [[r, c]]
        assert _announced(browser_page) == f"Hint: row {r + 1}, column {c + 1} is {_color(state)}."
        assert browser_page.locator("[data-player-hints]").locator("xpath=..").get_attribute("role") == "status"

    def test_the_outline_moves_on_with_the_next_commit(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _hint(browser_page).click()
        first = _hinted(browser_page)
        _hint(browser_page).click()
        second = _hinted(browser_page)
        assert len(first) == len(second) == 1 and first != second
        _cell(browser_page, 14, 14).click()
        assert _hinted(browser_page) == []
        assert _hints_shown(browser_page) == 2

    def test_the_hinted_cell_carries_an_accent_outline(self, browser_page, live) -> None:
        """The hinted cell's outline is --color-accent, as wide as the major
        rule and inset by that width (drawn just inside the cell), with an
        inset --grid-paper ring of twice that width inside it; every other
        td.player-cell has outline-style none. Read after the hinted cell's
        animation has finished."""
        _open(browser_page, live, live.store(GRID))
        _hint(browser_page).click()
        r, c = _hinted(browser_page)[0]
        look = _cell(browser_page, r, c).evaluate(_OUTLINE)
        others = browser_page.evaluate(
            "[...document.querySelectorAll('td.player-cell:not(.is-hinted)')]"
            ".filter((td) => getComputedStyle(td).outlineStyle !== 'none').map((td) => [+td.dataset.row, +td.dataset.col])")
        assert browser_page.locator("td.player-cell:not(.is-hinted)").count() == SIDE * SIDE - 1
        rule = look["rule"]
        assert rule > 0
        assert look["style"] == "solid"
        assert look["color"] == look["accent"]
        assert look["width"] == rule
        assert look["offset"] == -rule
        assert look["shadow"] == f"{look['paper']} 0px 0px 0px {2 * rule:g}px inset"
        assert others == []


_BOXES = """() => {
  const box = (el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  const q = (s) => document.querySelector(s);
  const errors = q('.player-errors');
  return {
    group: [...q('.player-history').querySelectorAll('button[data-player-action]')].map((b) => b.dataset.playerAction),
    hintIsLastChild: q('.player-history').lastElementChild === q('[data-player-action="hint"]'),
    hintsFollowErrors: errors.nextElementSibling === q('.player-hints'),
    toolbar: box(q('.player-toolbar')),
    reset: box(q('[data-player-action="reset"]')),
    hint: box(q('[data-player-action="hint"]')),
    errors: box(errors),
    hints: box(q('.player-hints')),
  };
}"""


@pytest.mark.browser
class TestSolverHint_PlacesTheButtonAndTheCounter:
    """The Hint button closes the History group (its last child, after
    Reset); "Hints: N" is the element right after "Errors: N" and sits to its
    right in the same row, at the right end of the toolbar, at desktop width
    and at 390 px. Hint is on Reset's row at desktop width and wraps onto a
    row of its own at 390 px."""

    @pytest.mark.parametrize("width", [1440, 390])
    def test_dom_order_and_boxes(self, browser, live, width) -> None:
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            got = page.evaluate(_BOXES)
        finally:
            context.close()
        assert got["group"] == ["undo", "redo", "reset", "hint"]
        assert got["hintIsLastChild"]
        assert got["hintsFollowErrors"]
        el, et, er, eb = got["errors"]
        hl, ht, hr, hb = got["hints"]
        assert ht < eb and et < hb  # same row band
        assert hl >= er  # to the right of the error counter
        assert abs(hr - got["toolbar"][2]) <= 1  # at the right end of the toolbar
        rl, rt, rr, rb = got["reset"]
        bl, bt, br, bb = got["hint"]
        if width == 1440:
            assert bt < rb and rt < bb and bl >= rr  # Reset's row, to its right
        else:
            assert bt >= rb  # below Undo / Redo / Reset
            assert bb <= et  # and above the counters: a row of its own


@pytest.mark.browser
class TestSolverHint_IgnoresWrongMarks:
    """AC-5 — two wrong marks stay, errors stay 2, and the revealed cell is the
    oracle's with the wrong marks ignored."""

    def test_wrong_marks_are_ignored_and_kept(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        # Two wrong marks for which taking them at face value would give a
        # different hint, so the test tells "ignored" from "believed".
        blank = [U] * (SIDE * SIDE)
        wrong = {F: E, E: F}
        board = None
        for r1 in range(SIDE):
            for c1 in range(SIDE - 1):
                cells = list(blank)
                cells[r1 * SIDE + c1] = wrong[_truth(GRID, r1, c1)]
                cells[r1 * SIDE + c1 + 1] = wrong[_truth(GRID, r1, c1 + 1)]
                if _face_value_hint(cells, *_GRID_CLUES, GRID) != _grid_hint(cells):
                    board = cells
                    break
            if board:
                break
        assert board is not None
        _set(browser_page, board)
        assert _error_count(browser_page) == 2
        before = _states(browser_page)

        _hint(browser_page).click()

        r, c, state, _ = _grid_hint(before)
        after = _states(browser_page)
        assert _changed(before, after) == {(r, c): state}
        assert {k: v for k, v in _marked(after).items() if (k, v) != ((r, c), state)} == _marked(before)
        assert _error_count(browser_page) == 2
        assert _hints_shown(browser_page) == 1


@pytest.mark.browser
class TestSolverHint_FallsBackToTheSolution:
    """AC-6 — no undecided cell is line-deducible: the first undecided cell
    gets its solution state and the announcement says so."""

    def test_fallback_reveals_the_first_undecided_cell(self, browser_page, live) -> None:
        grid, board = _fallback_grid()
        rows, columns = _clues(grid)
        assert _first_deducible(board, board, rows, columns, grid) is None
        _open(browser_page, live, live.store(grid))
        _set(browser_page, board)
        before = _states(browser_page)

        _hint(browser_page).click()

        first = before.index(U)
        r, c = divmod(first, 10)
        state = _truth(grid, r, c)
        assert _changed(before, _states(browser_page), width=10) == {(r, c): state}
        assert _announced(browser_page) == (
            f"Hint: no cell follows from a single line yet; row {r + 1}, column {c + 1} "
            f"is {_color(state)} (from the solution).")
        assert _hints_shown(browser_page) == 1
        assert _hinted(browser_page) == [[r, c]]


@pytest.mark.browser
class TestSolverHint_IsOneUndoableStroke:
    """AC-7 — a hint after two strokes: one undo takes it (and the count)
    back, one redo restores both; buttons and Ctrl/Cmd+Z alike."""

    def _two_strokes_and_a_hint(self, page):
        _cell(page, 5, 5).click()
        _cell(page, 9, 0).click()
        two = _states(page)
        want = _grid_hint(two)
        _hint(page).click()
        assert _changed(two, _states(page)) == {want[:2]: want[2]}
        assert _hints_shown(page) == 1
        return two, _states(page)

    def test_undo_and_redo_buttons(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        two, hinted = self._two_strokes_and_a_hint(browser_page)

        _button(browser_page, "Undo").click()
        assert _states(browser_page) == two
        assert _hints_shown(browser_page) == 0
        assert _hinted(browser_page) == []
        _button(browser_page, "Redo").click()
        assert _states(browser_page) == hinted
        assert _hints_shown(browser_page) == 1

    @pytest.mark.parametrize("modifier", ["Control", "Meta"])
    def test_ctrl_z_and_shift_ctrl_z(self, browser_page, live, modifier) -> None:
        _open(browser_page, live, live.store(GRID))
        two, hinted = self._two_strokes_and_a_hint(browser_page)
        browser_page.locator("h1").click()

        browser_page.keyboard.press(f"{modifier}+z")
        assert _states(browser_page) == two
        assert _hints_shown(browser_page) == 0
        browser_page.keyboard.press(f"Shift+{modifier}+z")
        assert _states(browser_page) == hinted
        assert _hints_shown(browser_page) == 1

    def test_reset_keeps_the_count_and_set_board_clears_it(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _hint(browser_page).click()
        _hint(browser_page).click()
        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()
        assert _marked(_states(browser_page)) == {}
        assert _hints_shown(browser_page) == 2
        _set(browser_page, [U] * (SIDE * SIDE))
        assert _hints_shown(browser_page) == 0


@pytest.mark.browser
class TestSolverHint_CanSolveAndThenLocks:
    """AC-8 — the hint that fills the last solution cell solves and locks;
    Hint is then aria-disabled and changes nothing."""

    def test_the_last_hint_solves(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _set(browser_page, _near_solved(E))
        before = _states(browser_page)
        assert _grid_hint(before)[:3] == (*LAST, F)
        assert not _is_disabled(browser_page, "Hint")

        _hint(browser_page).click()

        assert _changed(before, _states(browser_page)) == {LAST: F}
        assert _is_solved_shown(browser_page)
        assert _announced(browser_page) == f"Solved: {NAME}"
        assert _is_disabled(browser_page, "Hint")
        solved = _states(browser_page)
        _hint(browser_page).click(force=True)  # a real click on the disabled control
        assert _states(browser_page) == solved
        assert _hints_shown(browser_page) == 1

    def test_locked_with_cells_still_undecided(self, browser_page, live) -> None:
        """Solved with white cells left undecided: hintCell has a cell, the
        lock alone disables Hint."""
        _open_named(browser_page, live)
        _set(browser_page, _near_solved(U))
        _cell(browser_page, *LAST).click()
        assert _is_solved_shown(browser_page)
        solved = _states(browser_page)
        assert U in solved
        assert _is_disabled(browser_page, "Hint")
        _hint(browser_page).click(force=True)
        assert _states(browser_page) == solved
        assert _hints_shown(browser_page) == 0


@pytest.mark.browser
class TestSolverHint_DisabledWithNothingToReveal:
    """AC-9 — every cell marked, some wrong, not solved: Hint is disabled and
    changes nothing."""

    def test_no_undecided_cell(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cells = [F if cell else E for row in GRID for cell in row]
        cells[0] = E if cells[0] == F else F
        cells[17] = E if cells[17] == F else F
        _set(browser_page, cells)
        assert not _is_solved_shown(browser_page)
        assert _is_disabled(browser_page, "Hint")
        _hint(browser_page).click(force=True)
        assert _states(browser_page) == cells
        assert _hints_shown(browser_page) == 0

    def test_enabled_again_once_a_cell_is_undecided(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cells = [F if cell else E for row in GRID for cell in row]
        cells[0] = E if cells[0] == F else F
        _set(browser_page, cells)
        assert _is_disabled(browser_page, "Hint")
        _cell(browser_page, 0, 0).click()  # empty -> undecided, or filled -> empty
        if _states(browser_page)[0] != U:
            _cell(browser_page, 0, 0).click()
        assert not _is_disabled(browser_page, "Hint")

    def test_disabled_during_a_drag(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        assert not _is_disabled(browser_page, "Hint")
        browser_page.mouse.move(*_centre(browser_page, 3, 0))
        browser_page.mouse.down()
        browser_page.mouse.move(*_centre(browser_page, 3, 4), steps=4)
        assert _is_disabled(browser_page, "Hint")
        browser_page.evaluate("document.querySelector('[data-player-action=\"hint\"]').click()")
        browser_page.mouse.up()
        assert _marked(_states(browser_page)) == {(3, c): F for c in range(5)}
        assert _hints_shown(browser_page) == 0
        assert not _is_disabled(browser_page, "Hint")

    def test_enabled_again_after_a_cancelled_drag(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        browser_page.mouse.move(*_centre(browser_page, 3, 0))
        browser_page.mouse.down()
        browser_page.mouse.move(*_centre(browser_page, 3, 4), steps=4)
        assert _is_disabled(browser_page, "Hint")
        # Chromium's mouse is pointerId 1; the dropped preview below shows the
        # cancel reached the drag.
        browser_page.evaluate(
            "document.querySelector('.player-board').dispatchEvent("
            "new PointerEvent('pointercancel', { pointerId: 1, bubbles: true }))")
        assert _marked(_states(browser_page)) == {}
        assert not _is_disabled(browser_page, "Hint")
        browser_page.mouse.up()
        assert _marked(_states(browser_page)) == {}


@pytest.mark.browser
class TestSolverHint_KeyboardAndNoRequest:
    """AC-10 — Tab reaches Hint; Enter and Space each reveal one cell; its
    accessible name is "Hint"; three hints issue no request."""

    @staticmethod
    def _tab_to(page, name):
        page.evaluate("document.activeElement && document.activeElement.blur()")
        for _ in range(80):
            page.keyboard.press("Tab")
            if page.evaluate(_FOCUSED) == name:
                return
        raise AssertionError(f"Tab never reached {name}")

    def test_keyboard_and_no_request(self, browser_page, live) -> None:
        from playwright.sync_api import expect

        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.context.on("request", lambda request: requests.append(request.url))
        expect(_hint(browser_page)).to_have_accessible_name("Hint")
        assert _hint(browser_page).count() == 1

        revealed = []
        for key in ("Enter", "Space"):
            before = _states(browser_page)
            self._tab_to(browser_page, "Hint")
            browser_page.keyboard.press(key)
            changed = _changed(before, _states(browser_page))
            assert len(changed) == 1, key
            revealed.append(changed)
        _hint(browser_page).click()

        assert _hints_shown(browser_page) == 3
        assert len(_marked(_states(browser_page))) == 3
        assert requests == []
        assert browser_page.evaluate("localStorage.length + sessionStorage.length") == 0
        assert problems == []


#: The hinted cell's one animation: its name and its first keyframe.
_FADE = """(td) => {
  const [a] = td.getAnimations();
  return [a.animationName, a.effect.getKeyframes()[0]];
}"""


@pytest.mark.browser
class TestSolverHint_ReducedMotion:
    """AC-11 — under reduced motion no animation or transition runs on the
    hinted cell or the toolbar; without it the hinted cell does animate."""

    def test_reduced_motion(self, browser, live) -> None:
        context = browser.new_context(reduced_motion="reduce")
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _hint(page).click()
            assert len(_hinted(page)) == 1
            motion = page.evaluate(_MOTION)
            assert motion["checked"] > SIDE * SIDE
            assert motion == {**motion, "animations": 0, "named": 0, "timed": 0}
            assert page.locator("td.player-cell.is-hinted").evaluate("(td) => td.getAnimations().length") == 0
        finally:
            context.close()

    def test_without_reduced_motion_the_hinted_cell_animates(self, browser, live) -> None:
        """The control: the same hint does animate, so AC-11's zero is real.
        The one animation is player-hinted-in, whose first keyframe (offset 0)
        sets the outline colour to transparent: the outline fades in."""
        context = browser.new_context(reduced_motion="no-preference")
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _hint(page).click()
            assert page.locator("td.player-cell.is-hinted").evaluate("(td) => td.getAnimations().length") == 1
            name, first = page.locator("td.player-cell.is-hinted").evaluate(_FADE)
            assert name == "player-hinted-in"
            assert first["offset"] == 0
            assert first.get("outlineColor") in ("transparent", "rgba(0, 0, 0, 0)")
        finally:
            context.close()
