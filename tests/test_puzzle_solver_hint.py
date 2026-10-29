"""CARD-183 — the puzzle player's Hint button (IDEA-074; FR-044 extension,
card-local AC-1..AC-11) — and CARD-269's hint LADDER over it (card-local
AC-1..AC-10, at the bottom of this file).

A hint reveals one undecided cell, set to its solution state, as one undoable
stroke: the first cell, row-major, that one pass of line logic over its row
or its column forces from the player's correct marks (wrong marks count as
undecided); when no cell is forced that way, the first undecided cell, from
the solution, and the announcement says so.

CARD-269 made that reveal the THIRD press rather than the first, and it is
the reason several classes below press Hint three times (``_reveal``) where
they used to press it once. One press now points at the line to look at, a
second adds a CHECKED reason, and only the third reveals — so a player who
needs a nudge no longer pays the full answer. Where no single line decides a
cell, the first two presses highlight NOTHING and say so, which is the
falsehood CARD-183's fallback taught: it revealed a cell while announcing "no
cell follows from a single line yet", and the player read that as "you missed
a line deduction" when none existed. A second control, Check, answers the
question Hint silently danced around — "is one of my marks wrong?" — with the
row of the first wrong mark and never the cell.

That supersedes three shipped clauses of FR-044 (AC-327's "exactly one cell
changes" per press, AC-329's fallback reveal on the FIRST press, AC-334's
"each press reveals one cell"); the card names the supersession in its
semantics rule 10, and the ACs CARD-269's own classes carry are the
card-local statement they are checked against.

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
import re

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
    M,
    U,
    _button,
    _cell,
    _centre,
    _drag,
    _is_disabled,
    _marked,
    _states,
    _tool,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _unique_grid,
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
    _ONLY_THIS_SAVE,
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
  history = S.record(history, S.clickStroke(history.board, 0, 0, S.FILLED));
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


def _check(page):
    return _button(page, "Check")


def _reveal(page):
    """Climb the whole ladder to a reveal (CARD-269): rung 1 points at the
    line, rung 2 explains why it decides a cell, rung 3 reveals.

    Three real presses where CARD-183 took one. That is exactly the
    supersession of AC-327 / AC-329 / AC-334, so every class below that wants
    a REVEALED cell goes through here, and the classes CARD-269's own ACs
    cover press the button one rung at a time instead.
    """
    for _ in range(3):
        _hint(page).click()


#: What carries the ladder's line highlight: the cells, and the clue boxes of
#: each axis by their data-line (so a CARD-212 doubled axis shows BOTH twins
#: rather than whichever one came first in the DOM).
_HINT_LINE = """() => ({
  cells: [...document.querySelectorAll('td.player-cell.is-hint-line')]
    .map((td) => [+td.dataset.row, +td.dataset.col]),
  rowClues: [...document.querySelectorAll('th.player-clue.is-row.is-hint-line')]
    .map((th) => +th.dataset.line),
  colClues: [...document.querySelectorAll('th.player-clue.is-col.is-hint-line')]
    .map((th) => +th.dataset.line),
})"""


def _lined(page):
    return page.evaluate(_HINT_LINE)


def _changed(before, after, width=SIDE):
    return {(i // width, i % width): a for i, (b, a) in enumerate(zip(before, after)) if a != b}


_GRID_CLUES = _clues(GRID)


def _grid_hint(cells):
    return _oracle_hint(cells, *_GRID_CLUES, GRID)


def _color(state):
    return "black" if state == F else "white"


# --------------------------------------------------------------------------
# CARD-269 — the ladder's own oracles, on the same Python line solver
# --------------------------------------------------------------------------


def _line_of(cells, rows, columns, solution, axis, index):
    """One line of a board as the player's CORRECT marks describe it (every
    wrong mark, and every "?", read as undecided) with its clue."""
    width, height = len(columns), len(rows)
    knowns = _correct_only(cells, solution)
    if axis == "row":
        return rows[index], [knowns[index * width + c] for c in range(width)]
    return columns[index], [knowns[r * width + index] for r in range(height)]


def _ladder_line(cells, hint, rows, columns, solution):
    """The line rungs 1 and 2 point at for the hintCell result ``hint``, by
    the card's rule 2: the axis whose own ``line_intersection`` pass forces
    that cell from the correct marks, ROW FIRST when both do; ``(None, None)``
    for the exhausted state (``hint`` is None or ``deduced`` is False).

    Written on ``line_intersection``, never on ``solver_state.js`` — the same
    discipline as ``_oracle_hint`` above.
    """
    if hint is None or not hint[3]:
        return (None, None)
    row, col = hint[0], hint[1]
    for axis, index, at in (("row", row, col), ("column", col, row)):
        clue, line = _line_of(cells, rows, columns, solution, axis, index)
        forced = _forced(clue, line)
        if forced is not None and forced[at] != U:
            return (axis, index)
    return (None, None)


def _overlap_run(clue, length, at):
    """Which run of ``clue`` covers index ``at`` in EVERY placement in a line
    of ``length`` cells, by ENUMERATING the placements; None when the cell is
    not always filled, or when different placements give it to different runs.

    Deliberately not the arithmetic ``solver_state.js`` uses (leftmost start
    plus slack): brute force over ``line_candidates`` is a second
    implementation rather than the same derivation retyped, which is this
    suite's rule for a figure the code also computes.
    """
    runs = [n for n in clue if n > 0]
    owners = set()
    for line in line_candidates(tuple(clue), length):
        if not line[at]:
            return None
        owner = -1
        for index, cell in enumerate(line):
            if cell and (index == 0 or not line[index - 1]):
                owner += 1
            if index == at:
                break
        owners.add(owner)
    return runs[owners.pop()] if len(owners) == 1 else None


def _reason(clue, cells, at):
    """The card's rule 3 classifier as the ACs state it: ``("runs-complete",
    None)``, ``("overlap", run)`` or ``("generic", None)`` for the cell at
    index ``at`` of the line (``clue``, ``cells`` — correct marks only).

    Both named cases carry their precondition HERE too, so AC-8 is checked
    against this and not against the module under test: runs-complete needs
    the filled marks to total the clue AND every other cell to be forced
    white; overlap needs the line to hold no known mark at all, the cell to
    be forced filled, and one run to own it in every placement (``
    _overlap_run``, by enumeration).
    """
    forced = _forced(clue, cells)
    if forced is None or forced[at] == U:
        return ("generic", None)
    if sum(1 for state in cells if state == F) == sum(clue) and all(
        state == F or forced[index] == E for index, state in enumerate(cells)
    ):
        return ("runs-complete", None)
    if all(state == U for state in cells) and forced[at] == F:
        run = _overlap_run(clue, len(cells), at)
        if run is not None:
            return ("overlap", run)
    return ("generic", None)


#: The sentence rung 2 adds for each reason, written out as a human reads it.
#: Keyed by the names ``solver_state.js`` exports as ``HINT_REASONS`` — the
#: enumerable authority — and the ladder tests below assert the set of reasons
#: they actually DROVE equals that export, so a reason added to the module
#: without a case here is a failure rather than an untested branch
#: (ADR-0039/R2).
_REASON_SENTENCE = {
    "runs-complete": lambda axis, run: f"every run in this {axis} is placed; the rest is white.",
    "overlap": lambda axis, run: f"the {run}-run must overlap in the middle whatever its position.",
    "generic": lambda axis, run: f"every placement of this {axis}'s clues agrees on at least one cell.",
}


def _rung_text(rung, axis, index, reason=None):
    """What #puzzle-player-announce says on rung 1 or rung 2 of a ladder
    pointing at (``axis``, ``index``), 0-based, announced 1-based."""
    point = f"Hint: look at {axis} {index + 1}"
    if rung == 1:
        return f"{point}."
    case, run = reason
    return f"{point} — {_REASON_SENTENCE[case](axis, run)}"


def _grid_ladder_line(cells):
    return _ladder_line(cells, _grid_hint(cells), *_GRID_CLUES, GRID)


def _grid_reason(cells, axis, index, hint):
    clue, line = _line_of(cells, *_GRID_CLUES, GRID, axis, index)
    at = hint[1] if axis == "row" else hint[0]
    return _reason(clue, line, at)


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
    """AC-4, as CARD-269 superseded it — a blank 15 x 15 board: a full climb
    of the ladder (three real clicks on Hint) reveals the oracle's cell,
    "Hints: 1", errors unchanged.

    The method names below still say "one click" and "the next commit"
    because a rename is a node-id change; what changed is the number of
    presses one reveal costs, and ``_reveal`` is where that number lives.
    """

    def test_one_click_reveals_the_oracles_cell(self, browser_page, live) -> None:
        """Three presses, one reveal (CARD-269 AC-3's reveal seen from
        CARD-183's side): the cell, the counter and the announcement are
        CARD-183's unchanged, the price is the climb."""
        _open(browser_page, live, live.store(GRID))
        before = _states(browser_page)
        assert _hints_shown(browser_page) == 0 and _error_count(browser_page) == 0
        want = _grid_hint(before)
        assert want is not None and want[3]

        _reveal(browser_page)

        r, c, state, _ = want
        assert _changed(before, _states(browser_page)) == {(r, c): state}
        assert _hints_shown(browser_page) == 1
        assert _error_count(browser_page) == 0
        assert _hinted(browser_page) == [[r, c]]
        assert _announced(browser_page) == f"Hint: row {r + 1}, column {c + 1} is {_color(state)}."
        assert browser_page.locator("[data-player-hints]").locator("xpath=..").get_attribute("role") == "status"

    def test_the_outline_moves_on_with_the_next_commit(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _reveal(browser_page)
        first = _hinted(browser_page)
        _reveal(browser_page)
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
        _reveal(browser_page)
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
    checkIsLastChild: q('.player-history').lastElementChild === q('[data-player-action="check"]'),
    checkFollowsHint: q('[data-player-action="hint"]').nextElementSibling === q('[data-player-action="check"]'),
    hintsFollowErrors: errors.nextElementSibling === q('.player-hints'),
    toolbar: box(q('.player-toolbar')),
    reset: box(q('[data-player-action="reset"]')),
    hint: box(q('[data-player-action="hint"]')),
    check: box(q('[data-player-action="check"]')),
    errors: box(errors),
    hints: box(q('.player-hints')),
  };
}"""


@pytest.mark.browser
class TestSolverHint_PlacesTheButtonAndTheCounter:
    """CARD-269 extends this with Check's placement. CHECK now closes the
    History group, right after Hint (which is where the card's Design
    context puts it, and the clause of AC-333 that called Hint the group's
    last control is part of what the ladder supersedes — surfaced in the
    report, not decided quietly here). "Hints: N" is the element right after
    "Errors: N" and sits to its right in the same row, at the right end of
    the toolbar, at desktop width and at 390 px. Hint and Check share Reset's
    row at desktop width and wrap onto a row of their own at 390 px, Check to
    Hint's right in both.
    """

    @pytest.mark.parametrize("width", [1440, 390])
    def test_dom_order_and_boxes(self, browser, live, width) -> None:
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            got = page.evaluate(_BOXES)
        finally:
            context.close()
        assert got["group"] == ["undo", "redo", "reset", "hint", "check"]
        assert got["checkIsLastChild"]
        assert got["checkFollowsHint"]
        assert got["hintsFollowErrors"]
        el, et, er, eb = got["errors"]
        hl, ht, hr, hb = got["hints"]
        assert ht < eb and et < hb  # same row band
        assert hl >= er  # to the right of the error counter
        assert abs(hr - got["toolbar"][2]) <= 1  # at the right end of the toolbar
        rl, rt, rr, rb = got["reset"]
        bl, bt, br, bb = got["hint"]
        kl, kt, kr, kb = got["check"]
        # Check is on Hint's row and to its right at BOTH widths: it is the
        # ladder's neighbour, not a control of its own somewhere else.
        assert kt < bb and bt < kb, (got["hint"], got["check"])
        assert kl >= br, (got["hint"], got["check"])
        if width == 1440:
            assert bt < rb and rt < bb and bl >= rr  # Reset's row, to its right
            assert kt < rb and rt < kb  # Check on that row too
        else:
            assert bt >= rb  # below Undo / Redo / Reset
            assert bb <= et  # and above the counters: a row of their own
            assert kb <= et


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

        _reveal(browser_page)

        r, c, state, _ = _grid_hint(before)
        after = _states(browser_page)
        assert _changed(before, after) == {(r, c): state}
        assert {k: v for k, v in _marked(after).items() if (k, v) != ((r, c), state)} == _marked(before)
        assert _error_count(browser_page) == 2
        assert _hints_shown(browser_page) == 1


@pytest.mark.browser
class TestSolverHint_FallsBackToTheSolution:
    """AC-6, as CARD-269 superseded it, and CARD-269 AC-5 — the EXHAUSTED
    ladder, walked rung by rung.

    This is the defect at the centre of CARD-269. No undecided cell is
    line-deducible here, and CARD-183 answered the first press by revealing a
    cell while announcing "no cell follows from a single line yet" — which a
    player reads as "you missed a line deduction". There was none to miss, so
    the hint taught a falsehood, which is worse than no hint.

    Now the two cheap rungs say what is actually the case and highlight
    NOTHING, and the reveal — with its shipped wording, byte for byte — is
    still there on the third press for a player who wants it. The two claims
    are measured separately: the exhausted announcement AND an empty
    highlight (the second is what makes the first more than a word change,
    because a highlighted line here would point at a deduction that does not
    exist), with the deducible board as the control that the same instrument
    DOES see a line and DOES say "look at" when there is one.
    """

    def test_the_first_two_presses_say_no_line_decides_and_point_at_nothing(
        self, browser_page, live
    ) -> None:
        grid, board = _fallback_grid()
        rows, columns = _clues(grid)
        assert _first_deducible(board, board, rows, columns, grid) is None
        _open(browser_page, live, live.store(grid))
        _set(browser_page, board)
        before = _states(browser_page)
        assert U in before  # undecided cells remain: this is exhaustion, not a solved board
        assert not _is_disabled(browser_page, "Hint")

        for press in (1, 2):
            _hint(browser_page).click()
            assert _states(browser_page) == before, press  # no cell changes
            assert _hints_shown(browser_page) == 0, press  # and nothing is counted
            assert _hinted(browser_page) == [], press
            assert _lined(browser_page) == {"cells": [], "rowClues": [], "colClues": []}, press
            assert _announced(browser_page) == (
                "Hint: no single row or column decides a cell right now."), press

    def test_fallback_reveals_the_first_undecided_cell(self, browser_page, live) -> None:
        """Rung 3 is CARD-183's fallback reveal, unchanged — the same cell,
        the same "(from the solution)" wording, the same counter."""
        grid, board = _fallback_grid()
        rows, columns = _clues(grid)
        assert _first_deducible(board, board, rows, columns, grid) is None
        _open(browser_page, live, live.store(grid))
        _set(browser_page, board)
        before = _states(browser_page)

        _reveal(browser_page)

        first = before.index(U)
        r, c = divmod(first, 10)
        state = _truth(grid, r, c)
        assert _changed(before, _states(browser_page), width=10) == {(r, c): state}
        assert _announced(browser_page) == (
            f"Hint: no cell follows from a single line yet; row {r + 1}, column {c + 1} "
            f"is {_color(state)} (from the solution).")
        assert _hints_shown(browser_page) == 1
        assert _hinted(browser_page) == [[r, c]]
        assert _lined(browser_page) == {"cells": [], "rowClues": [], "colClues": []}

    def test_the_control_a_deducible_board_does_get_a_line(self, browser_page, live) -> None:
        """The negative control for the two claims above (ADR-0039/R4): the
        same two instruments, on a board where a line DOES decide a cell,
        read a highlighted line and a "look at" sentence. Without this, "the
        highlight is empty" and "the sentence says no line decides" would
        both also pass on an instrument that can only ever read empty.
        """
        _open(browser_page, live, live.store(GRID))
        axis, index = _grid_ladder_line(_states(browser_page))
        assert axis is not None

        _hint(browser_page).click()

        assert _lined(browser_page)["cells"] != []
        assert _announced(browser_page) == _rung_text(1, axis, index)


@pytest.mark.browser
class TestSolverHint_IsOneUndoableStroke:
    """AC-7 — a hint after two strokes: one undo takes it (and the count)
    back, one redo restores both; buttons and Ctrl/Cmd+Z alike."""

    def _two_strokes_and_a_hint(self, page):
        _cell(page, 5, 5).click()
        _cell(page, 9, 0).click()
        two = _states(page)
        want = _grid_hint(two)
        _reveal(page)
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
        _reveal(browser_page)
        _reveal(browser_page)
        _button(browser_page, "Reset").click()
        _button(browser_page, "Reset board").click()
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

        _reveal(browser_page)

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
        _tool(browser_page, "Clear")  # CARD-189: its first click blanks a dark or white cell; CARD-194: via the menu
        _cell(browser_page, 0, 0).click()
        assert _states(browser_page)[0] == U
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
    """AC-10, as CARD-269 superseded it, and CARD-269 AC-10 — Tab reaches
    Hint and Check; Enter and Space each climb a rung, so three of either
    reveal one cell; the accessible names are "Hint" and "Check"; the whole
    ladder and Check issue no request.
    """

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

        expect(_check(browser_page)).to_have_accessible_name("Check")
        assert _check(browser_page).count() == 1

        revealed = []
        for key in ("Enter", "Space"):
            before = _states(browser_page)
            self._tab_to(browser_page, "Hint")
            # Three presses of the SAME key: the whole ladder by keyboard
            # (CARD-269). The first two must change nothing, which is checked
            # here and not only at the end — otherwise "one cell changed"
            # would also pass if a single press still revealed.
            for rung in (1, 2):
                browser_page.keyboard.press(key)
                assert _states(browser_page) == before, (key, rung)
                assert _lined(browser_page)["cells"] != [], (key, rung)
            browser_page.keyboard.press(key)
            changed = _changed(before, _states(browser_page))
            assert len(changed) == 1, key
            revealed.append(changed)
        _reveal(browser_page)

        assert _hints_shown(browser_page) == 3
        assert len(_marked(_states(browser_page))) == 3
        # Check by keyboard too, and it is free: no cell, no stroke, no count.
        board = _states(browser_page)
        self._tab_to(browser_page, "Check")
        browser_page.keyboard.press("Enter")
        assert _states(browser_page) == board
        assert _hints_shown(browser_page) == 3
        assert _announced(browser_page) == "Check: no wrong marks."
        assert requests == []
        assert browser_page.evaluate(_ONLY_THIS_SAVE)
        assert problems == []


#: The hinted cell's one animation: its name and its first keyframe.
_FADE = """(td) => {
  const [a] = td.getAnimations();
  return [a.animationName, a.effect.getKeyframes()[0]];
}"""


@pytest.mark.browser
class TestSolverHint_ReducedMotion:
    """AC-11, extended by CARD-269 AC-10 — under reduced motion no animation
    or transition runs on the hinted cell, the LADDER'S LINE HIGHLIGHT or the
    toolbar; without it both the hinted cell and the line do animate.

    The line highlight was given a fade of its own precisely so this zero is
    a measurement and not a vacuous truth: a highlight that never animates
    would pass the reduced-motion check on an instrument incapable of reading
    anything else (ADR-0039/R4). The two controls at the end are what prove
    each zero rises.
    """

    def test_reduced_motion(self, browser, live) -> None:
        context = browser.new_context(reduced_motion="reduce")
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _hint(page).click()  # rung 1: the line highlight, and nothing recorded
            assert _lined(page)["cells"] != []
            assert page.locator("td.player-cell.is-hint-line").first.evaluate(
                "(td) => td.getAnimations().length") == 0
            assert page.locator("th.player-clue.is-hint-line").first.evaluate(
                "(th) => th.getAnimations().length") == 0
            _hint(page).click()
            _hint(page).click()  # rung 3: the reveal
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
            _reveal(page)
            assert page.locator("td.player-cell.is-hinted").evaluate("(td) => td.getAnimations().length") == 1
            name, first = page.locator("td.player-cell.is-hinted").evaluate(_FADE)
            assert name == "player-hinted-in"
            assert first["offset"] == 0
            assert first.get("outlineColor") in ("transparent", "rgba(0, 0, 0, 0)")
        finally:
            context.close()

    def test_without_reduced_motion_the_line_highlight_animates(self, browser, live) -> None:
        """The second control (CARD-269): rung 1's line fades its tint in,
        on the cells AND on the clue box, so the zero above is a real
        suppression and not an instrument reading nothing."""
        context = browser.new_context(reduced_motion="no-preference")
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _hint(page).click()
            assert _lined(page)["cells"] != []
            for selector in ("td.player-cell.is-hint-line", "th.player-clue.is-hint-line"):
                element = page.locator(selector).first
                assert element.evaluate("(el) => el.getAnimations().length") == 1, selector
                name, first = element.evaluate(_FADE)
                assert name == "player-hint-line-in", selector
                assert first["offset"] == 0, selector
                assert first.get("backgroundColor") in ("transparent", "rgba(0, 0, 0, 0)"), selector
        finally:
            context.close()


# ==========================================================================
# CARD-269 — the hint ladder and Check (card-local AC-1..AC-10)
# ==========================================================================

#: CARD-269 — the pure half of the ladder, driven straight.
#:
#: Everything the rungs rest on: the three enumerable authorities
#: (HINT_RUNGS, RUNG_EVENTS, HINT_REASONS, HINT_AXES), the whole rung
#: transition table rather than a sample of it, the RangeErrors that make an
#: unknown rung or event a loud failure instead of "leave it as it was", the
#: axis choice (row first when both force, the column when only it does, null
#: for the exhausted state), the classifier on hand-picked lines including
#: both of each named case's near misses, and Check's scan.
_LADDER = """async () => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY, m: S.MAYBE };
  const back = { [S.UNKNOWN]: 'u', [S.FILLED]: 'f', [S.EMPTY]: 'e', [S.MAYBE]: 'm' };
  const board = (width, height, text) => Object.freeze({ width, height,
    cells: Object.freeze([...text].map((ch) => codes[ch])) });
  const cells = (text) => [...text].map((ch) => codes[ch]);
  const refused = (call) => {
    try { call(); return null; } catch (error) { return error.constructor.name; }
  };
  const line = (l) => (l === null ? null
    : [l.axis, l.index, l.at, l.clue, l.cells.map((s) => back[s]).join(''), Object.isFrozen(l)]);
  const reason = (clue, text, at) => {
    const got = S.hintReason(clue, cells(text), at);
    return [got.reason, got.run, Object.isFrozen(got)];
  };
  const hint = (b, rows, cols, solution) => {
    const h = S.hintCell(b, rows, cols, solution);
    return [h === null ? null : [h.row, h.col, h.state, h.deduced], line(S.hintLine(b, rows, cols, solution, h))];
  };
  return {
    authorities: {
      rungs: [...S.HINT_RUNGS],
      events: [...S.RUNG_EVENTS],
      reasons: [...S.HINT_REASONS],
      axes: [...S.HINT_AXES],
      frozen: [S.HINT_RUNGS, S.RUNG_EVENTS, S.HINT_REASONS, S.HINT_AXES].every(Object.isFrozen),
      named: [S.RUNG_POINT, S.RUNG_EXPLAIN, S.RUNG_REVEAL],
    },
    // The WHOLE table: every rung against every event.
    table: S.RUNG_EVENTS.map((event) => S.HINT_RUNGS.map((rung) => S.nextRung(rung, event))),
    refused: {
      event: refused(() => S.nextRung(S.RUNG_POINT, 'toggle')),
      rung: refused(() => S.nextRung(4, 'press')),
      zero: refused(() => S.nextRung(0, 'press')),
      axis: refused(() => S.knownLine(board(1, 1, 'u'), [[true]], 'col', 0)),
    },
    // A wrong mark and a "?" read as undecided; a correct mark is kept.
    // Board 3 x 1 'fme', solution [true, true, true]: (0,0) correct,
    // (0,1) a "?", (0,2) wrong.
    known: {
      row: S.knownLine(board(3, 1, 'fme'), [[true, true, true]], 'row', 0).map((s) => back[s]).join(''),
      column: S.knownLine(board(1, 3, 'fme'), [[true], [true], [true]], 'column', 0)
        .map((s) => back[s]).join(''),
    },
    // Rung 1/2's axis. (a) both the row and the column force (0, 0) -> the
    // ROW; (b) the row clue [0] contradicts the correct black at (0, 0), so
    // only column 1 forces (0, 1) -> the COLUMN; (c) the same board with no
    // placement in either line -> the fallback, so no line at all.
    both: hint(board(2, 1, 'uu'), [[2]], [[1], [1]], [[true, true]]),
    columnOnly: hint(board(2, 1, 'fu'), [[0]], [[1], [0]], [[true, false]]),
    exhausted: hint(board(2, 1, 'fu'), [[0]], [[1], [2]], [[true, false]]),
    noCell: hint(board(1, 1, 'f'), [[1]], [[1]], [[true]]),
    reasons: {
      // Claimed: every run placed (the marks total the clue, the rest is
      // forced white) and a [0] line, whose runs are all placed vacuously.
      complete: reason([2], 'ffuuu', 2),
      completeZero: reason([0], 'uuuuu', 2),
      completeTwo: reason([1, 1], 'fuufu', 1),
      // Refused: one run short of the clue, and two marks no single run can
      // cover (no placement at all) — generic, not "every run is placed".
      shortOfTheClue: reason([2], 'fuuuu', 1),
      noPlacement: reason([2], 'fuufu', 1),
      // Claimed: nothing known, and the 4-run must cover the middle three.
      overlap: reason([4], 'uuuuu', 2),
      overlapEdge: reason([4], 'uuuuu', 1),
      // Refused: the SAME arithmetic window, with one cell known — the
      // deduction is no longer the clue's alone, so the overlap sentence is
      // not claimed.
      overlapWithAMark: reason([4], 'ufuuu', 2),
      overlapWithAWhite: reason([4], 'uuuue', 2),
      // Refused: the cell is not forced at all, so nothing may be claimed.
      notForced: reason([1], 'uuuuu', 0),
    },
    // Check: "?" and undecided are never wrong; the first wrong ROW,
    // row-major, is what comes back.
    wrong: {
      clean: S.firstWrongRow(board(2, 2, 'ffmu'), [[true, true], [false, false]]),
      second: S.firstWrongRow(board(2, 2, 'ffuf'), [[true, true], [false, false]]),
      first: S.firstWrongRow(board(2, 2, 'efmu'), [[true, true], [false, false]]),
      bothRows: S.firstWrongRow(board(2, 2, 'efff'), [[true, true], [false, false]]),
    },
  };
}"""


@pytest.mark.browser
class TestSolverHintLadder_ThePureModule:
    """CARD-269 — nextRung, knownLine, hintLine, hintReason and firstWrongRow
    on the cases that decide the ladder's behaviour, driven straight through
    ``await import('/static/solver_state.js')``.

    Each named reason is checked in BOTH directions here (AC-8's floor): the
    claim where its precondition holds, and the generic answer on a line that
    differs from it in exactly one respect — one run short of the clue for
    runs-complete, one known mark for overlap, with the overlap window
    otherwise identical. A classifier that dropped either precondition would
    keep every "claimed" case green and red only these.
    """

    def test_the_ladder(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        got = browser_page.evaluate(_LADDER)

        authorities = got["authorities"]
        assert authorities["rungs"] == [1, 2, 3]
        assert authorities["named"] == [1, 2, 3]
        assert authorities["events"] == ["press", "change"]
        assert authorities["reasons"] == ["runs-complete", "overlap", "generic"]
        assert authorities["axes"] == ["row", "column"]
        assert authorities["frozen"]

        # The whole transition table, not a sample: a press climbs and wraps,
        # every change drops to rung 1.
        assert got["table"] == [[2, 3, 1], [1, 1, 1]]
        assert got["refused"] == {
            "event": "RangeError", "rung": "RangeError",
            "zero": "RangeError", "axis": "RangeError",
        }

        # Correct mark kept, "?" and wrong mark read as undecided — the same
        # knowns hintCell deduces from, on both axes.
        assert got["known"] == {"row": "fuu", "column": "fuu"}

        # The axis: row first when both force, the column when only it does,
        # and NOTHING for the exhausted state or for a board with no
        # undecided cell.
        assert got["both"] == [[0, 0, F, True], ["row", 0, 0, [2], "uu", True]]
        assert got["columnOnly"] == [[0, 1, E, True], ["column", 1, 0, [0], "u", True]]
        assert got["exhausted"] == [[0, 1, E, False], None]
        assert got["noCell"] == [None, None]

        assert got["reasons"] == {
            "complete": ["runs-complete", None, True],
            "completeZero": ["runs-complete", None, True],
            "completeTwo": ["runs-complete", None, True],
            "shortOfTheClue": ["generic", None, True],
            "noPlacement": ["generic", None, True],
            "overlap": ["overlap", 4, True],
            "overlapEdge": ["overlap", 4, True],
            "overlapWithAMark": ["generic", None, True],
            "overlapWithAWhite": ["generic", None, True],
            "notForced": ["generic", None, True],
        }

        assert got["wrong"] == {"clean": None, "second": 1, "first": 0, "bothRows": 0}


# ==========================================================================
# CARD-212 (review cycle 2, G-003) — the highlight survives a redraw
# ==========================================================================

#: A board big enough for CARD-212's layout choice to apply, so a window
#: resize redraws it (a 15 x 15 is past neither side's 15 and is never
#: redrawn). At 1280 x 720 this one draws both row gutters.
GRID_BIG = _unique_grid(20, 12, seed=2124)

#: How many boards solver.js has built on this page (CARD-212's draw mark),
#: as an expression rather than a function so it reads the same in
#: page.evaluate and in a wait_for_function predicate.
_DRAWN_BOARDS = "performance.getEntriesByName('nonogram-player-board-draw').length"


@pytest.mark.browser
class TestSolverHint_TheHighlightSurvivesARedraw:
    """CARD-212 made the board redraw on a window resize, not only when the
    820 px breakpoint flips (its layout choice is a measurement, so it has to
    follow the window). A redraw replaces every cell element, and the hinted
    cell's highlight used to be held as one of those elements — so a ONE
    PIXEL resize took the highlight off while "Hints: 1" kept counting it.
    That is a hint the reader paid for and cannot see, on a trigger that is
    now ordinary: a phone fires a resize when its URL bar collapses, which is
    mid-solve, on the device where a hint helps most.

    The hint is a CELL, not an element, so it is kept as one and put back
    after the redraw. Asserted on the highlight itself and not on the
    counter, which survived a redraw all along and would make this vacuous.
    """

    def test_a_one_pixel_resize_keeps_the_highlight_on_the_same_cell(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size({"width": 1280, "height": 720})
        _open(page, live, live.store(GRID_BIG))

        _reveal(page)
        _reveal(page)  # the first hint of this board is (0, 0); the
        before = _hinted(page)  # second is off the diagonal, where a
        assert len(before) == 1, before  # transposed lookup would show
        assert before[0][0] != before[0][1], before
        # The cell the live region NAMES, so "still highlighted" is checked
        # against the hint itself and not only against the element that was
        # highlighted a moment ago (which a wrong lookup would match too).
        said = re.search(r"row (\d+), column (\d+)", _announced(page))
        assert said, _announced(page)
        named = [int(said.group(1)) - 1, int(said.group(2)) - 1]
        assert before == [named], (before, named)
        drawn = page.evaluate(_DRAWN_BOARDS)

        page.set_viewport_size({"width": 1279, "height": 720})
        page.wait_for_function(f"{_DRAWN_BOARDS} > {drawn}", timeout=600)

        assert _hinted(page) == before == [named]  # the same cell, still highlighted
        assert _hints_shown(page) == 2
        # And it is still the highlight, not a leftover class: the next
        # commit moves it on, exactly as it does without a resize.
        _cell(page, 11, 19).click()
        assert _hinted(page) == []


#: Every reason name the pure module declares, read from the module itself
#: (the enumerable authority) rather than from a list written here.
_REASONS_EXPORT = """async () => [...(await import('/static/solver_state.js')).HINT_REASONS]"""

#: Nothing highlighted, as _lined reads it.
_NO_LINE = {"cells": [], "rowClues": [], "colClues": []}


def _row_marks(row, count):
    """A blank 15 x 15 board with the first ``count`` filled cells of GRID's
    row ``row`` marked correctly (every mark right, so AC-328's "wrong marks
    are ignored" is not what is being exercised here)."""
    cells = [U] * (SIDE * SIDE)
    for col in [c for c in range(SIDE) if GRID[row][c]][:count]:
        cells[row * SIDE + col] = F
    return cells


def _reason_boards():
    """One real 15 x 15 board per reason name, found by walking each row from
    "nothing marked" to "every run marked".

    That walk is what moves a row through all three reasons: with nothing
    known the deduction is the clue's own overlap, with some of the run marked
    it is neither named case, and with every run marked the rest of the row is
    white. Returns ``{reason: cells}``; the caller asserts the keys cover the
    module's own HINT_REASONS, so a reason with no board here is a failure.
    """
    found = {}
    for row in range(SIDE):
        for count in range(sum(GRID[row]) + 1):
            cells = _row_marks(row, count)
            hint = _grid_hint(cells)
            axis, index = _ladder_line(cells, hint, *_GRID_CLUES, GRID)
            if axis is None:
                continue
            case, _run = _grid_reason(cells, axis, index, hint)
            found.setdefault(case, cells)
    return found


@pytest.mark.browser
class TestSolverHintLadder_FirstPressPointsAtALine:
    """AC-1 — the gentlest rung. One press on a blank 15 x 15 board points at
    the line the next deduction lives on and does nothing else: no cell
    changes, "Hints: 0" stays, no stroke is recorded.

    The line is the one the card's rule 2 names, and which line that is comes
    from the Python line oracle here (``_ladder_line`` over
    ``line_intersection``), not from ``solver_state.js`` — so a ladder that
    highlighted the wrong line, or the right line's wrong axis, reds this.
    """

    def test_the_first_press_highlights_the_line_and_says_so(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        before = _states(browser_page)
        hint = _grid_hint(before)
        assert hint is not None and hint[3]
        axis, index = _grid_ladder_line(before)
        assert axis is not None
        assert _lined(browser_page) == _NO_LINE  # a fresh load points at nothing
        assert _announced(browser_page) == ""

        _hint(browser_page).click()

        assert _states(browser_page) == before  # not one cell changed
        assert _hints_shown(browser_page) == 0  # and nothing counted
        assert _error_count(browser_page) == 0
        assert _hinted(browser_page) == []  # no reveal highlight either
        assert _is_disabled(browser_page, "Undo") is True  # nothing recorded
        lined = _lined(browser_page)
        if axis == "row":
            assert lined["cells"] == [[index, col] for col in range(SIDE)]
            assert lined["rowClues"] == [index]
            assert lined["colClues"] == []
        else:
            assert lined["cells"] == [[row, index] for row in range(SIDE)]
            assert lined["colClues"] == [index]
            assert lined["rowClues"] == []
        assert _announced(browser_page) == _rung_text(1, axis, index)
        assert browser_page.evaluate(_ONLY_THIS_SAVE)

    def test_the_cell_the_third_press_will_reveal_is_on_that_line(self, browser_page, live) -> None:
        """Card rule 5 (coherence), checked at rung 1 rather than inferred
        from the reset rule: the line this press points at CONTAINS the cell
        the ladder will reveal."""
        _open(browser_page, live, live.store(GRID))
        hint = _grid_hint(_states(browser_page))

        _hint(browser_page).click()
        lined = _lined(browser_page)

        assert [hint[0], hint[1]] in lined["cells"]

    def test_the_highlight_survives_a_redraw(self, browser_page, live) -> None:
        """A redraw (CARD-212 made a one-pixel resize one) replaces every cell
        and every clue box, so a highlight held as those ELEMENTS would be
        gone while the player is still standing on the rung they pressed for
        — the same defect CARD-212's review cycle 2 found in the hinted
        cell's outline. The line is held as a value and painted back.

        On this board the row axis is doubled, so the assertion also covers
        the twin rule: both clue boxes of the line carry the highlight.
        """
        page = browser_page
        page.set_viewport_size({"width": 1280, "height": 720})
        _open(page, live, live.store(GRID_BIG))

        _hint(page).click()
        before = _lined(page)
        assert before["cells"] != []
        assert len(before["rowClues"]) + len(before["colClues"]) >= 2
        assert len(set(before["rowClues"]) | set(before["colClues"])) == 1
        drawn = page.evaluate(_DRAWN_BOARDS)

        page.set_viewport_size({"width": 1279, "height": 720})
        page.wait_for_function(f"{_DRAWN_BOARDS} > {drawn}", timeout=600)

        assert _lined(page) == before
        # And it is still the highlight, not a leftover class: a mark clears it.
        _cell(page, 11, 19).click()
        assert _lined(page) == _NO_LINE


@pytest.mark.browser
class TestSolverHintLadder_SecondPressExplains:
    """AC-2 — the second rung adds WHY, on the same line, and still records
    nothing.

    Driven once per reason the pure module declares, on a real board where
    that reason's precondition genuinely holds; the set of reasons driven is
    asserted to BE the module's HINT_REASONS, so a reason added there without
    a board (or a sentence) fails this rather than passing untested
    (ADR-0039/R2).
    """

    def test_each_reason_is_announced_on_a_board_where_it_holds(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        authority = browser_page.evaluate(_REASONS_EXPORT)
        boards = _reason_boards()
        assert set(boards) == set(authority), (sorted(boards), sorted(authority))

        for case, cells in boards.items():
            _set(browser_page, cells)
            before = _states(browser_page)
            hint = _grid_hint(before)
            axis, index = _ladder_line(before, hint, *_GRID_CLUES, GRID)
            reason = _grid_reason(before, axis, index, hint)
            assert reason[0] == case, (case, reason)

            _hint(browser_page).click()
            first = _announced(browser_page)
            lined = _lined(browser_page)
            assert first == _rung_text(1, axis, index), case

            _hint(browser_page).click()

            assert _states(browser_page) == before, case  # still no cell changes
            assert _hints_shown(browser_page) == 0, case
            assert _hinted(browser_page) == [], case
            assert _lined(browser_page) == lined, case  # the same line, same highlight
            said = _announced(browser_page)
            assert said == _rung_text(2, axis, index, reason), case
            assert said != first, case
            assert "undefined" not in said, case
            assert said.startswith(f"{first[:-1]} — "), (case, said, first)


@pytest.mark.browser
class TestSolverHintLadder_ThirdPressRevealsTheSameSituation:
    """AC-3 — the third rung is CARD-183's reveal, unchanged, of a cell ON
    the line rungs 1 and 2 pointed at (card rule 5), and the ladder is back
    on rung 1 afterwards."""

    def test_the_third_press_reveals_the_cell_of_that_line(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        before = _states(browser_page)
        hint = _grid_hint(before)
        axis, index = _grid_ladder_line(before)
        r, c, state, _ = hint

        _hint(browser_page).click()
        _hint(browser_page).click()
        lined = _lined(browser_page)
        assert lined["cells"] != []

        _hint(browser_page).click()

        assert _changed(before, _states(browser_page)) == {(r, c): state}
        assert _hints_shown(browser_page) == 1
        assert _hinted(browser_page) == [[r, c]]
        assert _announced(browser_page) == f"Hint: row {r + 1}, column {c + 1} is {_color(state)}."
        # The revealed cell is the one the ladder's own line contains.
        assert [r, c] in lined["cells"]
        assert (r if axis == "row" else c) == index
        # The line highlight is gone with the reveal, and the reveal is ONE
        # undo step: one undo takes the cell and the count back together.
        assert _lined(browser_page) == _NO_LINE
        _button(browser_page, "Undo").click()
        assert _states(browser_page) == before
        assert _hints_shown(browser_page) == 0

    def test_the_ladder_is_back_on_rung_one(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _reveal(browser_page)
        after = _states(browser_page)
        axis, index = _grid_ladder_line(after)
        assert axis is not None

        _hint(browser_page).click()

        assert _states(browser_page) == after  # a point, not a second reveal
        assert _hints_shown(browser_page) == 1
        assert _announced(browser_page) == _rung_text(1, axis, index)
        assert _lined(browser_page)["cells"] != []


@pytest.mark.browser
class TestSolverHintLadder_AnyChangeResetsTheLadder:
    """AC-4 — standing on rung 2, ANY change puts the next press back on rung
    1 and takes the old highlight off.

    One parametrised case per way the board can change, driven as real input:
    a click, a drag, Undo, Redo, a confirmed Reset, and Check. That reset is
    what makes a ladder coherent (card rule 5), so each route gets its own
    cell — a single "a mark resets it" case would leave undo, redo, reset and
    Check resting on the claim that they all go through one place, which is
    exactly the kind of claim this board asks to be measured.
    """

    def _to_rung_two(self, page):
        _hint(page).click()
        _hint(page).click()
        lined = _lined(page)
        assert lined["cells"] != []
        assert " — " in _announced(page)  # rung 2, not rung 1
        return lined

    @pytest.mark.parametrize("event", ["mark", "drag", "undo", "redo", "reset", "check"])
    def test_the_next_press_is_rung_one_again(self, browser_page, live, event) -> None:
        _open(browser_page, live, live.store(GRID))
        # What each route needs on the undo stack before the ladder is climbed.
        if event in ("undo", "redo", "reset"):
            _cell(browser_page, 14, 0).click()
        if event == "redo":
            _button(browser_page, "Undo").click()

        lined = self._to_rung_two(browser_page)

        if event == "mark":
            _cell(browser_page, 14, 14).click()
        elif event == "drag":
            _drag(browser_page, [(13, 2), (13, 6)])
        elif event == "undo":
            _button(browser_page, "Undo").click()
        elif event == "redo":
            _button(browser_page, "Redo").click()
        elif event == "reset":
            _button(browser_page, "Reset").click()
            _button(browser_page, "Reset board").click()
        else:
            _check(browser_page).click()

        # The old line is off the board. Check puts its OWN line up, so what
        # is asserted there is that it is not the ladder's old one.
        if event == "check":
            assert _lined(browser_page) != lined
        else:
            assert _lined(browser_page) == _NO_LINE

        after = _states(browser_page)
        axis, index = _grid_ladder_line(after)
        assert axis is not None, event

        _hint(browser_page).click()

        assert _states(browser_page) == after, event  # rung 1 reveals nothing
        assert _announced(browser_page) == _rung_text(1, axis, index), event
        assert _lined(browser_page)["cells"] != [], event

    def test_the_control_two_presses_with_no_change_between_them_do_climb(
        self, browser_page, live
    ) -> None:
        """The negative control for every case above (ADR-0039/R4): with
        nothing happening between the presses, the second press DOES climb to
        rung 2. Without this, a ladder stuck on rung 1 for ever would pass
        all six cases above.
        """
        _open(browser_page, live, live.store(GRID))

        _hint(browser_page).click()
        first = _announced(browser_page)
        _hint(browser_page).click()
        second = _announced(browser_page)

        assert first.endswith(".") and " — " not in first
        assert second.startswith(f"{first[:-1]} — ")
        assert _hints_shown(browser_page) == 0  # and still nothing recorded


# --------------------------------------------------------------------------
# AC-8 — the reason is never a lie
# --------------------------------------------------------------------------

_REASONS = """async (lines) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY, m: S.MAYBE };
  return lines.map(([clue, text, at]) => {
    const got = S.hintReason(clue, [...text].map((ch) => codes[ch]), at);
    return [got.reason, got.run];
  });
}"""


def _arithmetic_overlap(clue, length, at):
    """The run a classifier would name from the CLUE ALONE (leftmost start
    plus slack), ignoring what is known on the line.

    Not an oracle and never asserted against: it exists only to COUNT the
    corpus lines where the overlap precondition is the whole difference
    between a true sentence and a false one — a line whose window still
    covers ``at`` but which holds a known mark. Without that count, "overlap
    was refused here" could be refusing lines where no classifier would have
    claimed it, and AC-8's second direction would be vacuous.
    """
    runs = [n for n in clue if n > 0]
    if not runs:
        return None
    slack = length - (sum(runs) + len(runs) - 1)
    if slack < 0:
        return None
    start = 0
    for run in runs:
        if run > slack and start + slack <= at < start + run:
            return run
        start += run + 1
    return None


def _reason_corpus(rng, draws):
    """``(clue, cells, at, kind)`` lines of five kinds, built from random
    solution lines of 5..12 cells: ``no-knowns`` (the overlap case),
    ``runs-placed`` (the runs-complete case), ``one-mark`` (a no-knowns
    overlap line with ONE correct mark added — the overlap case's near miss),
    ``runs-short`` (every run but one marked — runs-complete's near miss) and
    ``mixed`` (random correct knowns). ``at`` is always a cell the line's own
    logic decides, which is the only kind of cell rung 2 ever talks about.

    12 cells is the ceiling because ``_overlap_run`` enumerates placements.
    """
    lines = []
    while len(lines) < draws:
        length = rng.randint(5, 12)
        truth = [rng.random() < 0.5 for _ in range(length)]
        clue = _encode(truth)
        blank = [U] * length
        blank_forced = _forced(clue, blank)
        decided = [i for i in range(length) if blank_forced[i] != U]
        if decided:
            lines.append((clue, list(blank), rng.choice(decided), "no-knowns"))
            window = [i for i in decided if _arithmetic_overlap(clue, length, i)]
            if window:
                at = rng.choice(window)
                cells = list(blank)
                elsewhere = rng.choice([i for i in range(length) if i != at])
                cells[elsewhere] = F if truth[elsewhere] else E
                lines.append((clue, cells, at, "one-mark"))
        placed = [F if cell else U for cell in truth]
        placed_forced = _forced(clue, placed)
        holes = [i for i in range(length) if placed[i] == U and placed_forced[i] != U]
        if holes:
            lines.append((clue, list(placed), rng.choice(holes), "runs-placed"))
        marks = [i for i in range(length) if truth[i]]
        if len(marks) > 1:
            cells = list(placed)
            cells[rng.choice(marks)] = U
            short_forced = _forced(clue, cells)
            open_cells = [i for i in range(length)
                          if cells[i] == U and short_forced is not None and short_forced[i] != U]
            if open_cells:
                lines.append((clue, cells, rng.choice(open_cells), "runs-short"))
        share = rng.choice((0.2, 0.5, 0.8))
        cells = [(F if cell else E) if rng.random() < share else U for cell in truth]
        mixed_forced = _forced(clue, cells)
        open_cells = [i for i in range(length)
                      if cells[i] == U and mixed_forced is not None and mixed_forced[i] != U]
        if open_cells:
            lines.append((clue, cells, rng.choice(open_cells), "mixed"))
    return lines


@pytest.mark.browser
class TestSolverHintLadder_TheReasonIsNeverALie:
    """AC-8 — a named reason is announced only where its own precondition
    holds, in both directions, over a seeded corpus of lines.

    This is the card's centre of gravity turned into a measurement. A hint
    that makes the player believe they missed something that was never there
    is worse than no hint, so the two named cases are not allowed to be
    announced on a line the code did not check:

      * "every run in this row is placed" needs the correct filled marks to
        total the clue (and, with that, every other cell forced white);
      * "the N-run must overlap in the middle" needs the line to hold NO
        known mark, so the deduction really is the clue's own arithmetic —
        and the run named has to be the one that owns the cell in every
        placement, which ``_overlap_run`` settles by enumeration rather than
        by the same arithmetic again.

    Both near misses are counted, not merely present: a corpus where the
    refused lines were lines nobody would have claimed anyway would make the
    second direction vacuous.
    """

    def test_every_named_reason_claimed_only_where_it_holds(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        rng = random.Random(2691)
        lines = _reason_corpus(rng, 1800)
        expected = [_reason(clue, cells, at) for clue, cells, at, _kind in lines]

        assert len(lines) >= 1700
        counts = {case: sum(1 for case_, _ in expected if case_ == case) for case, _ in expected}
        assert counts.get("runs-complete", 0) >= 450, counts
        assert counts.get("overlap", 0) >= 150, counts
        assert counts.get("generic", 0) >= 800, counts
        # The two near misses, counted: a line whose overlap WINDOW still
        # covers the cell but which holds a known mark, and a line one run
        # short of its clue — on both, the named sentence must not appear.
        refused_overlap = [
            (clue, cells, at) for (clue, cells, at, kind), (case, _run) in zip(lines, expected)
            if kind == "one-mark" and _arithmetic_overlap(clue, len(cells), at) and case != "overlap"
        ]
        refused_complete = [
            (clue, cells, at) for (clue, cells, at, kind), (case, _run) in zip(lines, expected)
            if kind == "runs-short" and case != "runs-complete"
        ]
        assert len(refused_overlap) >= 150, len(refused_overlap)
        assert len(refused_complete) >= 400, len(refused_complete)

        got = browser_page.evaluate(_REASONS, [[clue, _text(cells), at] for clue, cells, at, _ in lines])
        assert len(got) == len(lines)
        for index, (answer, want) in enumerate(zip(got, expected)):
            assert tuple(answer) == want, (index, lines[index])

        # And the claims the module DID make, re-checked against their own
        # preconditions rather than against the oracle that shares them.
        claims = 0
        for (clue, cells, at, _kind), (case, run) in zip(lines, got):
            if case == "runs-complete":
                forced = _forced(clue, cells)
                assert sum(1 for state in cells if state == F) == sum(clue), (clue, cells)
                assert all(state == F or forced[i] == E for i, state in enumerate(cells)), (clue, cells)
                claims += 1
            elif case == "overlap":
                assert all(state == U for state in cells), (clue, cells)
                assert run == _overlap_run(clue, len(cells), at), (clue, cells, at, run)
                claims += 1
        assert claims >= 600, claims

    def test_the_page_never_says_a_reason_it_did_not_check(self, browser_page, live) -> None:
        """The same rule where the player meets it: on each reason's own
        board, the sentence announced carries that reason's words and NEITHER
        of the other named case's words. Both directions, per board.
        """
        _open(browser_page, live, live.store(GRID))
        boards = _reason_boards()
        words = {"runs-complete": "is placed", "overlap": "must overlap"}
        said = {}
        for case, cells in boards.items():
            _set(browser_page, cells)
            _hint(browser_page).click()
            _hint(browser_page).click()
            said[case] = _announced(browser_page)

        assert set(said) == set(boards)
        for case, sentence in said.items():
            for other, phrase in words.items():
                if other == case:
                    assert phrase in sentence, (case, sentence)
                else:
                    assert phrase not in sentence, (case, other, sentence)
            if case == "generic":
                assert all(phrase not in sentence for phrase in words.values()), sentence
                assert "agrees on at least one cell" in sentence


_SAVE_TEXT = """() => localStorage.getItem('nonogram-player:' + window.puzzlePlayer.payload.id)"""


@pytest.mark.browser
class TestSolverHintLadder_NeitherRungNorCheckIsSaved:
    """AC-9 / G-7 — the rung and Check leave no trace. The save written with
    a ladder standing on rung 2 and a Check pressed is byte-for-byte the save
    of the same marks without either, and a reload starts on rung 1 with
    nothing highlighted (CON-021: play state is this browser's, and the rung
    is not even that — it is UI state of Region's kind).
    """

    def test_the_save_is_byte_identical_and_a_reload_starts_at_rung_one(
        self, browser_page, live
    ) -> None:
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 0, 0).click()
        _cell(browser_page, 7, 3).click()
        marks = _states(browser_page)
        plain = browser_page.evaluate(_SAVE_TEXT)
        assert plain is not None and plain != ""

        _hint(browser_page).click()  # rung 1
        _hint(browser_page).click()  # rung 2
        _check(browser_page).click()  # and Check, which resets the ladder
        _hint(browser_page).click()  # rung 1 again

        assert _states(browser_page) == marks
        assert browser_page.evaluate(_SAVE_TEXT) == plain
        assert browser_page.evaluate(_ONLY_THIS_SAVE)
        assert _hints_shown(browser_page) == 0

        browser_page.reload()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert _states(browser_page) == marks  # the marks came back
        assert _lined(browser_page) == _NO_LINE  # the rung did not
        assert _announced(browser_page) == ""
        before = _states(browser_page)
        axis, index = _grid_ladder_line(before)

        _hint(browser_page).click()

        # Rung 1, not rung 2 and not a reveal: the first press after a reload
        # points at the line.
        assert _states(browser_page) == before
        assert _announced(browser_page) == _rung_text(1, axis, index)
        assert _hints_shown(browser_page) == 0

    def test_the_control_rung_three_does_change_the_save(self, browser_page, live) -> None:
        """The control for the byte-identical claim (ADR-0039/R4): the SAME
        instrument, read around a rung-3 press, shows a different save. A
        comparison that could only ever read "equal" would prove nothing
        about rungs 1-2.
        """
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 0, 0).click()
        plain = browser_page.evaluate(_SAVE_TEXT)

        _reveal(browser_page)

        assert browser_page.evaluate(_SAVE_TEXT) != plain
        assert _hints_shown(browser_page) == 1


# --------------------------------------------------------------------------
# AC-6 / AC-7 — Check
# --------------------------------------------------------------------------


def _wrong(row, col):
    """A mark at (row, col) that the solution disagrees with."""
    return E if GRID[row][col] else F


def _right(row, col):
    return F if GRID[row][col] else E


@pytest.mark.browser
class TestSolverCheck_NamesTheFirstWrongRow:
    """AC-6 — Check names the ROW of the first wrong mark, row-major, and
    nothing else: no cell changes, no stroke is recorded, neither counter
    moves. Hint ignores wrong marks (AC-328) and never said so; this is the
    control that says it.
    """

    def test_check_highlights_and_names_the_row(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cells = [U] * (SIDE * SIDE)
        cells[0 * SIDE + 2] = _right(0, 2)  # a CORRECT mark, earlier row-major
        cells[1 * SIDE + 4] = M  # a "?", which is never wrong (CARD-186)
        cells[4 * SIDE + 6] = _wrong(4, 6)  # the first wrong mark
        cells[9 * SIDE + 1] = _wrong(9, 1)  # and a later one
        _set(browser_page, cells)
        assert _error_count(browser_page) == 2
        before = _states(browser_page)
        assert not _is_disabled(browser_page, "Check")

        _check(browser_page).click()

        assert _states(browser_page) == before  # no cell changes
        assert _error_count(browser_page) == 2  # no counter moves
        assert _hints_shown(browser_page) == 0  # Check is free
        assert _is_disabled(browser_page, "Undo") is True  # no stroke recorded
        assert _hinted(browser_page) == []
        assert _announced(browser_page) == "Check: a mark in row 5 is wrong."
        # The row, never the cell: the sentence names no column at all.
        assert "column" not in _announced(browser_page)
        lined = _lined(browser_page)
        assert lined["cells"] == [[4, col] for col in range(SIDE)]
        assert lined["rowClues"] == [4]
        assert lined["colClues"] == []

    def test_the_row_is_the_first_one_row_major(self, browser_page, live) -> None:
        """Not the row with the most wrong marks, and not the last one: three
        wrong marks in row 12 and one in row 3, and row 3 is named. The
        control for a scan that happened to run the other way, or to count.
        """
        _open(browser_page, live, live.store(GRID))
        cells = [U] * (SIDE * SIDE)
        for col in (2, 5, 9):
            cells[12 * SIDE + col] = _wrong(12, col)
        cells[3 * SIDE + 13] = _wrong(3, 13)
        _set(browser_page, cells)
        assert _error_count(browser_page) == 4

        _check(browser_page).click()

        assert _announced(browser_page) == "Check: a mark in row 4 is wrong."
        assert _lined(browser_page)["rowClues"] == [3]

    def test_check_does_not_move_the_hinted_cell(self, browser_page, live) -> None:
        """Check is a reader (ADR-0038/R6): it leaves the revealed cell's own
        highlight where it was, and does not record a thing over it."""
        _open(browser_page, live, live.store(GRID))
        _reveal(browser_page)
        hinted = _hinted(browser_page)
        assert len(hinted) == 1

        _check(browser_page).click()

        assert _hinted(browser_page) == hinted
        assert _hints_shown(browser_page) == 1
        assert _announced(browser_page) == "Check: no wrong marks."


@pytest.mark.browser
class TestSolverCheck_CleanLockedAndEditMode:
    """AC-7 — Check with nothing wrong, Check on a locked board, and Check in
    edit mode (where it must not exist at all, for the reason Hint does not:
    the solution there is the grid being rewritten)."""

    def test_a_clean_board_with_question_marks(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cells = [U] * (SIDE * SIDE)
        cells[2 * SIDE + 2] = _right(2, 2)
        cells[6 * SIDE + 8] = M
        cells[11 * SIDE + 0] = M
        _set(browser_page, cells)
        assert _error_count(browser_page) == 0
        before = _states(browser_page)

        _check(browser_page).click()

        assert _states(browser_page) == before
        assert _announced(browser_page) == "Check: no wrong marks."
        assert _lined(browser_page) == _NO_LINE
        assert _hints_shown(browser_page) == 0

    def test_a_question_mark_over_a_filled_cell_is_not_wrong(self, browser_page, live) -> None:
        """The sharper half of "? is never wrong": a "?" sitting on a cell the
        solution fills, which a scan comparing states would call an error."""
        _open(browser_page, live, live.store(GRID))
        filled = next((r, c) for r in range(SIDE) for c in range(SIDE) if GRID[r][c])
        empty = next((r, c) for r in range(SIDE) for c in range(SIDE) if not GRID[r][c])
        cells = [U] * (SIDE * SIDE)
        cells[filled[0] * SIDE + filled[1]] = M
        cells[empty[0] * SIDE + empty[1]] = M
        _set(browser_page, cells)

        _check(browser_page).click()

        assert _announced(browser_page) == "Check: no wrong marks."
        assert _lined(browser_page) == _NO_LINE

    def test_a_locked_board_disables_check(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _set(browser_page, _near_solved(E))
        assert not _is_disabled(browser_page, "Check")
        _cell(browser_page, *LAST).click()
        assert _is_solved_shown(browser_page)
        solved = _states(browser_page)

        assert _is_disabled(browser_page, "Check") is True
        _check(browser_page).click(force=True)  # a real click on the disabled control

        assert _states(browser_page) == solved
        assert _lined(browser_page) == _NO_LINE
        assert _announced(browser_page) == f"Solved: {NAME}"  # Check wrote nothing

    def test_the_editor_page_has_no_check(self, browser_page, live) -> None:
        """Edit mode ships neither control, asserted as ABSENT on the real
        editor page — with the player page as the control that the same
        locator does find them."""
        puzzle_id = live.store(GRID)
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/editor")
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert _check(browser_page).count() == 0
        assert _hint(browser_page).count() == 0
        assert browser_page.locator('[data-player-action="check"]').count() == 0

        _open(browser_page, live, puzzle_id)

        assert _check(browser_page).count() == 1
        assert _hint(browser_page).count() == 1
