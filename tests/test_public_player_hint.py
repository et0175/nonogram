"""CARD-327 - the public player's hint DERIVES the next cell from the clues.

``play.js`` used to say, in its header, that the page could have "no hints"
because "adding any of them publicly needs the answer". That sentence was true
of the error count, the progress percent and Check, and FALSE of the hint:
``solver_state.js``'s ``hintCell`` touches the solution for exactly two things
(spelling the state it returns, and reading the player's wrong marks as
undecided), and the deduction between them, ``lineForced``, takes no solution
at all. This module holds the correction and the feature that makes it true.

Test names follow the card (AC-1 .. AC-10); AC-10 is
``TestPublicHint_ThreeMarksCoexist``. The sections, in file order:

* the page's hint ladder: rung 3 derives the cell (AC-1), rungs 1-2 point and
  explain (AC-2), the ladder is the module's (AC-3), the exhausted state reveals
  nothing (AC-4), a hint is one undo step and survives a reload (AC-5), the
  contradicting-line decision;
* the answer: the asset gains nothing and no page variable is a solution grid
  (AC-6, EC), the hint code's structural scanner with its bypass plants, the
  header claim (AC-8);
* the deduction against the module (AC-7), and the plants that move it;
* the control outside the toolbar (AC-9), the three marks that share a line
  (AC-10), zoom and scroll, and the listener census.

How the expected values are made. A test of a derived hint must not derive its
expectation from the thing under test, and must not read a fixture's solution
for it either (AC-1). So an expectation comes from one of two places: the
served ``/solver_state.js``'s own ``lineForced`` (``_EXPECTED``), asked over the
board the page holds; or ``oracle_line`` below, a brute-force enumeration of
every placement written in Python for this module, which shares no code with
either JavaScript implementation. A run that needs the module's ``hintCell``
(AC-7) hands it the fixture's solution, which is legal in the TEST tree: it is
the only place the solution is allowed to exist.

How a plant is served. Every behavioural plant rewrites the SERVED ``play.js``
through a Playwright ROUTE and adds a canary the page reports
(``window.__served``), and the runner asserts the canary before it believes a
plant did or did not fire: rewriting the file and switching the cache off
through CDP both let plants go unserved at random (CARD-326's measurement).
"""

from __future__ import annotations

import itertools
from collections import Counter
import json
import random
import re
from pathlib import Path

import pytest

from nonogram.solver import solve
from tests.test_public_player import (  # noqa: F401 - fixtures used by name
    GRIDS,
    PLAYER_DIR,
    _cell_centre,
    _drag,
    _open,
    _prefill,
    _state,
    _tap,
    browser_type,
    host,
    site,
    write_bundle,
)
from tests.test_public_player_circles import (  # noqa: F401
    CIRCLES_GRID,
    _RING,
    _board,
    _distance,
    _marked,
    _pixels,
    _ring_edge_distances,
    _rgb,
    _save_strokes,
)
from tests.test_public_player_crosshair import (  # noqa: F401
    _move,
    _raw_definition,
    _scan,
    browser_page,
)
from tests.test_public_player_zoom import (  # noqa: F401
    NARROWEST,
    PHONE,
    SHORTEST,
    TALLEST,
    WIDEST,
    _GEOMETRY,
    _bounds,
    _module,
    _percent,
    _press,
    _settle,
)
from tests.test_puzzle_solver_page import _encode

PLAY_JS = PLAYER_DIR / "play.js"
PLAY_HTML = PLAYER_DIR / "play.html"
PLAYER_CSS = PLAYER_DIR / "player.css"
SOLVER_STATE = Path(__file__).resolve().parent.parent / "src" / "nonogram" / "admin" / "static" / "solver_state.js"

HINT = '[data-player-action="hint"]'
UNDO = '[data-player-action="undo"]'
REDO = '[data-player-action="redo"]'
RESET = '[data-player-action="reset"]'
FILLED_BRUSH = '[data-player-tool="filled"]'
EMPTY_BRUSH = '[data-player-tool="empty"]'

# --------------------------------------------------------------------------
# This card's own fixtures
# --------------------------------------------------------------------------

#: A 10 x 10 puzzle on whose BLANK board no row and no column clue forces any
#: cell, and which is nonetheless uniquely solvable (a line-logic-only solver
#: stops at the first move; the real solver finishes by search). Found by a
#: seeded search (seed 16185 of 20000 random half-dense grids) because AC-4
#: needs the exhausted state at the first press and none of the four ``GRIDS``
#: fixtures has it: their rows are all tight, so every row forces everything.
#: Both properties are RE-DERIVED below, not trusted
#: (``test_the_exhausted_fixture_is_what_the_card_needs``).
EXHAUSTED_ROWS = (
    "##..#...##",
    "###..#...#",
    ".##..#.#.#",
    "#...##....",
    ".#...#..##",
    ".........#",
    "....####.#",
    "#...#.###.",
    "#.##....#.",
    "..##..#...",
)
EXHAUSTED_GRID = [[ch == "#" for ch in row] for row in EXHAUSTED_ROWS]

FIXTURES = {**GRIDS, "mixed": CIRCLES_GRID, "exhausted": EXHAUSTED_GRID}


@pytest.fixture
def bundle(tmp_path):
    """Shadows the shared ``bundle``: the four shared puzzles plus this card's two."""
    root = tmp_path / "bundle"
    return root, write_bundle(root, FIXTURES)


@pytest.fixture
def plant_page(request):
    """``browser_page`` without its teardown assertion, yielding ``(page, errors)``.

    A plant that makes the page throw is a plant working: the exception is the
    evidence, so the scenarios read ``errors`` and report it instead of the
    fixture failing the test at teardown. Chromium's absence still refuses
    LOUDLY (ADR-0038/R8), by the same route ``browser_page`` takes.
    """
    from tests import test_puzzle_solver_page as _solver_page

    try:
        import pytest_playwright  # noqa: F401
    except ImportError:
        pytest.fail(_solver_page._PLAYWRIGHT_MISSING, pytrace=False)
    page = request.getfixturevalue("page")
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page, errors


# --------------------------------------------------------------------------
# The brute-force oracle: every placement, no deduction
# --------------------------------------------------------------------------


def _placements(runs: list[int], length: int):
    """Every way to lay ``runs`` in ``length`` cells, as a list of booleans."""

    def go(index: int, start: int):
        if index == len(runs):
            yield []
            return
        reserved = sum(runs[index + 1 :]) + len(runs) - index - 1
        for at in range(start, length - runs[index] - reserved + 1):
            for rest in go(index + 1, at + runs[index] + 1):
                yield [(at, runs[index])] + rest

    for layout in go(0, 0):
        line = [False] * length
        for at, run in layout:
            for cell in range(at, at + run):
                line[cell] = True
        yield line


def oracle_line(clue: list[int], cells: list[str]) -> list[str] | None:
    """What every placement consistent with the FILLED/EMPTY cells agrees on.

    ``None`` when no placement fits. Written by enumeration so it shares no
    reasoning with ``lineForced`` (reachability) or ``forcedLine`` (the same).
    """
    runs = [n for n in clue if n > 0]
    fits = [
        line
        for line in _placements(runs, len(cells))
        if all((c != "filled" or on) and (c != "empty" or not on) for c, on in zip(cells, line, strict=True))
    ]
    if not fits:
        return None
    out = []
    for i in range(len(cells)):
        column = {line[i] for line in fits}
        out.append("filled" if column == {True} else "empty" if column == {False} else "unknown")
    return out


def _known(state: str) -> str:
    return state if state in ("filled", "empty") else "unknown"


def oracle_hint(cells: list[str], width: int, height: int, rows, columns) -> dict | None:
    """The first undecided cell some line forces (row-major, ROW first), or None."""
    row_cells = [[_known(cells[r * width + c]) for c in range(width)] for r in range(height)]
    col_cells = [[_known(cells[r * width + c]) for r in range(height)] for c in range(width)]
    row_forced = [oracle_line(clue, row_cells[r]) for r, clue in enumerate(rows)]
    col_forced = [oracle_line(clue, col_cells[c]) for c, clue in enumerate(columns)]
    for r in range(height):
        for c in range(width):
            if cells[r * width + c] not in ("unknown", "maybe"):
                continue
            if row_forced[r] is not None and row_forced[r][c] != "unknown":
                return {"row": r, "col": c, "state": row_forced[r][c], "axis": "row", "index": r}
            if col_forced[c] is not None and col_forced[c][r] != "unknown":
                return {"row": r, "col": c, "state": col_forced[c][r], "axis": "column", "index": c}
    return None


def clues_of(grid) -> tuple[list[list[int]], list[list[int]]]:
    return [_encode(row) for row in grid], [_encode(column) for column in zip(*grid)]


def cells_after(grid, strokes, extra=()) -> list[str]:
    """The board a list of ``(state, cells)`` strokes leaves on ``grid``'s extent."""
    height, width = len(grid), len(grid[0])
    cells = ["unknown"] * (height * width)
    for state, where in [*strokes, *extra]:
        for r, c in where:
            cells[r * width + c] = state
    return cells


# --------------------------------------------------------------------------
# Reading the page and the module
# --------------------------------------------------------------------------

_READ = """() => {
  const p = window.publicPlayer;
  const button = document.querySelector('[data-player-action="hint"]');
  const lit = [...document.querySelectorAll('.is-hint-line')].map((el) =>
    el.matches('td') ? 'cell:' + el.dataset.row + ',' + el.dataset.col
      : (el.classList.contains('is-row') ? 'row-clue:' : 'col-clue:') + el.dataset.line);
  const history = p.getHistory();
  return {
    rung: Number(button.getAttribute('data-player-rung')),
    disabled: button.getAttribute('aria-disabled'),
    say: document.querySelector('[data-player-hint-say]').textContent,
    counter: document.querySelector('[data-player-hints]').textContent,
    cells: [...p.getBoard().cells], recorded: [...history.board.cells],
    hinted: [...document.querySelectorAll('td.is-hinted')].map((el) => [Number(el.dataset.row), Number(el.dataset.col)]),
    lit, done: history.done.length, undone: history.undone.length,
    hintStrokes: history.done.filter((entry) => entry.stroke.hint === true).length,
    last: history.done.length ? history.done[history.done.length - 1].stroke : null,
  };
}"""

#: The expected hint, asked of the SERVED module's ``lineForced`` over a board as
#: the player has it (a "?" is read by ``lineForced`` as undecided). Row first,
#: row-major: the rule the module's ``hintLine`` states.
_EXPECT_FN = """const expectOf = (b, rows, columns) => {
  const { width, height } = b;
  const row = (r) => Array.from({ length: width }, (_, c) => b.cells[r * width + c]);
  const col = (c) => Array.from({ length: height }, (_, r) => b.cells[r * width + c]);
  const rf = rows.map((clue, r) => S.lineForced(clue, row(r)));
  const cf = columns.map((clue, c) => S.lineForced(clue, col(c)));
  const known = (s) => (s === S.FILLED || s === S.EMPTY ? s : S.UNKNOWN);
  for (let r = 0; r < height; r += 1) {
    for (let c = 0; c < width; c += 1) {
      const here = b.cells[r * width + c];
      if (here !== S.UNKNOWN && here !== S.MAYBE) continue;
      if (rf[r] !== null && rf[r][c] !== S.UNKNOWN) {
        return { row: r, col: c, state: rf[r][c], axis: 'row', index: r, at: c, clue: rows[r], cells: row(r).map(known) };
      }
      if (cf[c] !== null && cf[c][r] !== S.UNKNOWN) {
        return { row: r, col: c, state: cf[c][r], axis: 'column', index: c, at: r, clue: columns[c], cells: col(c).map(known) };
      }
    }
  }
  return null;
};"""


def _module_js(page, body: str, argument=None):
    """``body`` (a function body using ``S`` = the served ``/solver_state.js``)."""
    return page.evaluate(
        "async (arg) => { const S = await import('/solver_state.js'); " + body + " }",
        argument,
    )


def read(page) -> dict:
    return page.evaluate(_READ)


def expected(page) -> dict | None:
    return _module_js(
        page,
        _EXPECT_FN + " const p = window.publicPlayer; return expectOf(p.getHistory().board, p.payload.rows, p.payload.columns);",
    )


def press(page) -> None:
    page.click(HINT, force=True)


def press_to_reveal(page) -> None:
    for _ in range(3):
        press(page)


def line_parts(page, axis: str, index: int) -> list[str]:
    """What carrying ``.is-hint-line`` means for one line: its cells and its clue box."""
    width, height = page.evaluate("() => [window.publicPlayer.payload.width, window.publicPlayer.payload.height]")
    if axis == "row":
        return sorted([*[f"cell:{index},{c}" for c in range(width)], f"row-clue:{index}"])
    return sorted([*[f"cell:{r},{index}" for r in range(height)], f"col-clue:{index}"])


def single_undecided(grid, where) -> list:
    """Strokes marking every cell of ``grid`` as the solution has it EXCEPT ``where``."""
    height, width = len(grid), len(grid[0])
    black = [(r, c) for r in range(height) for c in range(width) if grid[r][c] and (r, c) != where]
    white = [(r, c) for r in range(height) for c in range(width) if not grid[r][c] and (r, c) != where]
    return [s for s in (("empty", white), ("filled", black)) if s[1]]


def _site_text(host, name: str) -> str:
    return (host[1].site_dir / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Fixture sanity: derived, not assumed
# --------------------------------------------------------------------------


def test_the_exhausted_fixture_is_what_the_card_needs() -> None:
    rows, columns = clues_of(EXHAUSTED_GRID)
    blank = ["unknown"] * 100
    assert oracle_hint(blank, 10, 10, rows, columns) is None, "a line forces a cell on the blank board"
    assert solve(tuple(tuple(r) for r in rows), tuple(tuple(c) for c in columns)).solution_count == 1


def test_the_mixed_fixture_is_uniquely_solvable_and_has_a_forced_first_cell() -> None:
    rows, columns = clues_of(CIRCLES_GRID)
    assert solve(tuple(tuple(r) for r in rows), tuple(tuple(c) for c in columns)).solution_count == 1
    assert oracle_hint(["unknown"] * 100, 10, 10, rows, columns) is not None


# ==========================================================================
# AC-1 - rung 3 derives the cell
# ==========================================================================

#: Boards (name -> strokes over the mixed fixture) the ladder is driven on. The
#: strokes are the CORRECT marks of some rows, or a "?" laid over cells: what
#: the hint sees is the board as the player has it.
LADDER_BOARDS = {
    "blank": lambda: [],
    "four-rows-marked": lambda: _marked(CIRCLES_GRID, rows=range(4)),
    "maybe-cells": lambda: [("maybe", [(0, 0), (0, 1), (3, 3), (6, 6)])],
}


def ladder_to_reveal(page, host, board: str) -> tuple[dict, dict, dict]:
    """Open ``board`` on the mixed puzzle and press to rung 3; return (expected, before, after)."""
    _board(page, host, host[2]["mixed"], CIRCLES_GRID, LADDER_BOARDS[board]())
    want = expected(page)
    assert want is not None, "the scenario is vacuous: no line forces a cell"
    before = read(page)
    press_to_reveal(page)
    return want, before, read(page)


@pytest.mark.browser
class TestPublicHint_RungThreeDerivesTheCell:
    @pytest.mark.parametrize("board", list(LADDER_BOARDS))
    def test_rung_three_marks_the_cell_lineforced_gives_it_as_one_hint_stroke(self, browser_page, host, board) -> None:
        want, before_page, after = ladder_to_reveal(browser_page, host, board)
        index = want["row"] * 10 + want["col"]
        assert after["recorded"][index] == want["state"], (want, after["recorded"][index])
        assert after["hintStrokes"] == 1 and after["done"] == before_page["done"] + 1
        assert after["last"]["hint"] is True
        assert after["last"]["cells"] == [[want["row"], want["col"]]] and after["last"]["state"] == want["state"]
        # the count is the module's, read off the history the page holds
        assert _module_js(browser_page, "return S.hintCount(window.publicPlayer.getHistory());") == 1
        assert after["counter"] == "1"
        # and exactly that one cell changed
        before = ["unknown"] * 100
        for state, where in LADDER_BOARDS[board]():
            for r, c in where:
                before[r * 10 + c] = state
        changed = [i for i in range(100) if before[i] != after["recorded"][i]]
        assert changed == [index], changed

    @pytest.mark.parametrize("board", list(LADDER_BOARDS))
    def test_the_derived_cell_is_what_an_independent_enumeration_finds(self, browser_page, host, board) -> None:
        """The expectation above is the module's; this one shares no code with it."""
        page = browser_page
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, LADDER_BOARDS[board]())
        rows, columns = clues_of(CIRCLES_GRID)
        brute = oracle_hint(cells_after(CIRCLES_GRID, LADDER_BOARDS[board]()), 10, 10, rows, columns)
        press_to_reveal(page)
        after = read(page)
        assert brute is not None
        assert after["last"]["cells"] == [[brute["row"], brute["col"]]] and after["last"]["state"] == brute["state"]


# ==========================================================================
# AC-2 - rungs 1 and 2 point and explain
# ==========================================================================

#: Boards on which each of the module's three reasons is the one given. Which
#: board earns which reason is read off the module (``hintReason``), and the
#: three are asserted to cover ``HINT_REASONS`` exactly.
REASON_BOARDS = {
    "blank": LADDER_BOARDS["blank"],
    "four-rows-marked": LADDER_BOARDS["four-rows-marked"],
    "maybe-cells": LADDER_BOARDS["maybe-cells"],
    "row-complete": lambda: [("filled", [(r, c) for r in range(1) for c in range(10) if CIRCLES_GRID[r][c]])],
}

#: The sentence each reason is said with. Keyed by the module's reason names;
#: ``test_the_reason_sentences_are_exactly_the_modules_reasons`` holds the keys
#: to ``HINT_REASONS`` in both directions. The wording is the admin's
#: (``solver.js``'s ``LADDER_REASON``), held to it by the agreement module.
REASON_SAYS = {
    "runs-complete": "every run in this {axis} is placed; the rest is white.",
    "overlap": "the {run}-run must overlap in the middle whatever its position.",
    "generic": "every placement of this {axis}'s clues agrees on at least one cell.",
}


def rungs_one_and_two(page, host, board: str) -> tuple[dict, dict, dict, dict]:
    _board(page, host, host[2]["mixed"], CIRCLES_GRID, REASON_BOARDS[board]())
    want = expected(page)
    assert want is not None, "vacuous: nothing to point at"
    before = read(page)
    press(page)
    one = read(page)
    press(page)
    two = read(page)
    return want, before, one, two


@pytest.mark.browser
class TestPublicHint_RungsOneAndTwoPointAndExplain:
    @pytest.mark.parametrize("board", list(REASON_BOARDS))
    def test_rung_one_lights_the_line_the_deduction_comes_from_and_says_so(self, browser_page, host, board) -> None:
        page = browser_page
        want, before, one, _ = rungs_one_and_two(page, host, board)
        assert sorted(one["lit"]) == line_parts(page, want["axis"], want["index"]), (want["axis"], want["index"], one["lit"])
        assert one["say"] == f"Hint: look at {want['axis']} {want['index'] + 1}."
        assert (one["recorded"], one["done"], one["counter"]) == (before["recorded"], before["done"], before["counter"])
        assert one["hinted"] == []

    @pytest.mark.parametrize("board", list(REASON_BOARDS))
    def test_rung_two_adds_the_reason_hintreason_gives_and_changes_nothing_on_the_board(self, browser_page, host, board) -> None:
        page = browser_page
        want, before, one, two = rungs_one_and_two(page, host, board)
        reason = _module_js(page, "return S.hintReason(arg.clue, arg.cells, arg.at);", want)
        assert reason["reason"] in _module_js(page, "return [...S.HINT_REASONS];")
        sentence = REASON_SAYS[reason["reason"]].format(axis=want["axis"], run=reason["run"])
        assert two["say"] == f"Hint: look at {want['axis']} {want['index'] + 1} — {sentence}"
        assert two["lit"] == one["lit"], "rung 2 lights the same line as rung 1"
        assert two["recorded"] == before["recorded"] and two["done"] == before["done"] and two["counter"] == "0"

    def test_the_three_boards_between_them_give_every_reason_the_module_has(self, browser_page, host) -> None:
        page = browser_page
        seen = set()
        for board in REASON_BOARDS:
            want, *_ = rungs_one_and_two(page, host, board)
            seen.add(_module_js(page, "return S.hintReason(arg.clue, arg.cells, arg.at).reason;", want))
        assert seen == set(_module_js(page, "return [...S.HINT_REASONS];")), seen

    def test_the_reason_sentences_are_exactly_the_modules_reasons(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["mixed"])
        reasons = _module_js(page, "return [...S.HINT_REASONS];")
        assert sorted(REASON_SAYS) == sorted(reasons)
        in_page = page.evaluate("async () => Object.keys((await import('/play.js')).HINT_REASON_SAY)")
        assert sorted(in_page) == sorted(reasons), "the page says a reason the module does not have, or lacks one"

    def test_only_one_line_is_lit_after_a_change_and_a_second_press(self, browser_page, host) -> None:
        page = browser_page
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, [])
        press(page)
        first = read(page)["lit"]
        _tap(page, 9, 9)  # a recorded change: the highlight goes
        assert read(page)["lit"] == []
        press(page)
        second = read(page)["lit"]
        want = expected(page)
        assert sorted(second) == line_parts(page, want["axis"], want["index"]) and first != [], (first, second)


# ==========================================================================
# AC-3 - the ladder climbs and resets as the module says
# ==========================================================================


def next_rung(page, rung: int, event: str) -> int:
    return _module_js(page, "return S.nextRung(arg[0], arg[1]);", [rung, event])


@pytest.mark.browser
class TestPublicHint_TheLadderIsTheModules:
    def test_the_rung_after_every_step_is_what_nextrung_returns_for_the_event_that_occurred(self, browser_page, host) -> None:
        page = browser_page
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, [])
        rungs = _module_js(page, "return [...S.HINT_RUNGS];")
        assert read(page)["rung"] == rungs[0], "a load starts on the first rung"
        steps = [
            "hint", "hint", "tap", "hint", "undo", "hint", "hint", "hint", "redo", "hint", "key-undo", "hint", "hint", "hint",
            "reset", "hint", "tap",
        ]
        events: list[str] = []
        rung = read(page)["rung"]
        for step in steps:
            before = read(page)
            if step == "hint":
                press(page)
            elif step == "tap":
                _tap(page, 9, 0)
            elif step == "undo":
                page.click(UNDO, force=True)
            elif step == "redo":
                page.click(REDO, force=True)
            elif step == "key-undo":
                page.keyboard.press("Control+z")
            elif step == "reset":
                page.click('[data-player-action="reset"]', force=True)
            after = read(page)
            recorded = (after["done"], after["undone"], after["recorded"]) != (before["done"], before["undone"], before["recorded"])
            if recorded:
                event = "change"
            elif step == "hint":
                event = "press"
            else:
                # an undo, redo or key with nothing to undo or redo records nothing,
                # so it is no event at all: the ladder is where it was
                assert after["rung"] == before["rung"] and after["lit"] == before["lit"], (step, before, after)
                continue
            events.append(event)
            rung = next_rung(page, rung, event)
            assert after["rung"] == rung, (step, event, before["rung"], after["rung"], rung)
        # every event the module knows occurred, derived from the module
        assert set(events) == set(_module_js(page, "return [...S.RUNG_EVENTS];")), events

    def test_rung_three_is_the_reveal_and_the_others_record_nothing(self, browser_page, host) -> None:
        page = browser_page
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, [])
        rungs = _module_js(page, "return [S.RUNG_POINT, S.RUNG_EXPLAIN, S.RUNG_REVEAL];")
        assert rungs == _module_js(page, "return [...S.HINT_RUNGS];")
        done = []
        for _ in rungs:
            done.append(read(page)["done"])
            press(page)
        assert done == [0, 0, 0] and read(page)["done"] == 1, "only the last rung records a stroke"

    def test_a_hint_that_is_pressed_mid_gesture_does_nothing(self, browser_page, host) -> None:
        page = browser_page
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, [])
        before = read(page)
        page.mouse.move(*_cell_centre(page, 5, 0))
        page.mouse.down()
        page.mouse.move(*_cell_centre(page, 5, 1))
        page.mouse.move(*_cell_centre(page, 5, 2))
        page.evaluate("() => document.querySelector('[data-player-action=\"hint\"]').click()")
        mid = read(page)
        page.mouse.up()
        assert (mid["rung"], mid["say"], mid["lit"], mid["done"]) == (before["rung"], "", [], 0), mid


# ==========================================================================
# AC-4 - the exhausted state says so and reveals nothing
# ==========================================================================

EXHAUSTED_SENTENCE = "the clues decide nothing more by themselves"


def exhausted_problems(page, host, keys) -> list[str]:
    problems: list[str] = []
    _board(page, host, keys["exhausted"], EXHAUSTED_GRID, [])
    start = read(page)
    if expected(page) is not None:
        problems.append("vacuous: a line forces a cell on the exhausted fixture")
    if start["disabled"] != "false":
        problems.append("the control is disabled on a board with undecided cells: it cannot say it is exhausted")
    for number in range(1, 5):  # one more press than there are rungs: every rung, and the wrap
        press(page)
        now = read(page)
        if EXHAUSTED_SENTENCE not in now["say"]:
            problems.append(f"press {number}: no exhausted sentence: {now['say']!r}")
        if now["recorded"] != start["recorded"] or now["done"] != 0 or now["hintStrokes"] != 0:
            problems.append(f"press {number}: a cell was revealed or a stroke recorded")
        if now["lit"] or now["hinted"]:
            problems.append(f"press {number}: something is lit although no line decides a cell")
        if now["counter"] != "0":
            problems.append(f"press {number}: the hint count moved")
    return problems


@pytest.mark.browser
class TestPublicHint_ExhaustedRevealsNothing:
    def test_a_board_no_line_decides_says_so_at_every_rung_and_reveals_no_cell(self, browser_page, host) -> None:
        assert exhausted_problems(browser_page, host, host[2]) == []

    def test_the_page_never_holds_back_a_cell_to_reveal_later(self, browser_page, host) -> None:
        page = browser_page
        _board(page, host, host[2]["exhausted"], EXHAUSTED_GRID, [])
        for _ in range(12):
            press(page)
        after = read(page)
        assert after["recorded"] == ["unknown"] * 100 and after["done"] == 0 and after["undone"] == 0


# ==========================================================================
# AC-5 - a hint is one undo step
# ==========================================================================


@pytest.mark.browser
class TestPublicHint_AHintIsOneUndoStep:
    def test_undo_returns_the_cell_to_undecided_and_the_count_falls_and_redo_restores_both(self, browser_page, host) -> None:
        page = browser_page
        want, _, revealed = ladder_to_reveal(page, host, "four-rows-marked")
        index = want["row"] * 10 + want["col"]
        page.click(UNDO, force=True)
        undone = read(page)
        assert undone["recorded"][index] == "unknown" and undone["counter"] == "0" and undone["done"] == revealed["done"] - 1
        assert _module_js(page, "return S.hintCount(window.publicPlayer.getHistory());") == 0
        page.click(REDO, force=True)
        redone = read(page)
        assert redone["recorded"][index] == want["state"] and redone["counter"] == "1"
        assert _module_js(page, "return S.hintCount(window.publicPlayer.getHistory());") == 1
        assert redone["recorded"] == revealed["recorded"]

    def test_the_hint_survives_a_reload_as_a_hint(self, browser_page, host) -> None:
        """The page's own save used to keep only cells and state, so a reload turned a
        derived cell into a plain mark and the count fell to zero."""
        page = browser_page
        want, _, revealed = ladder_to_reveal(page, host, "blank")
        page.reload()
        page.wait_for_function("window.publicPlayer !== undefined")
        after = read(page)
        assert after["recorded"] == revealed["recorded"]
        assert (after["hintStrokes"], after["counter"]) == (1, "1")
        assert _module_js(page, "return S.hintCount(window.publicPlayer.getHistory());") == 1
        page.click(UNDO, force=True)
        assert read(page)["counter"] == "0"

    @pytest.mark.parametrize(
        "bad",
        ["yes", 1, False, None],
        ids=["string", "number", "false", "null"],
    )
    def test_a_save_whose_hint_flag_is_not_true_is_refused(self, browser_page, host, bad) -> None:
        page = browser_page
        key = host[2]["mixed"]
        _open(page, host, key)
        save = json.loads(_save_strokes(key, CIRCLES_GRID, [("filled", [(0, 1)])]))
        control = json.loads(json.dumps(save))
        control["done"][0]["hint"] = True
        _prefill(page, host, key, json.dumps(control))
        assert read(page)["hintStrokes"] == 1, "the matched control: a true flag is read"
        save["done"][0]["hint"] = bad
        _prefill(page, host, key, json.dumps(save))
        assert read(page)["recorded"] == ["unknown"] * 100, "a save that cannot be trusted is dropped whole"

    def test_a_hint_moves_the_circles_like_any_mark_and_leaves_no_crosshair_behind(self, browser_page, host) -> None:
        """GAP 5. The row's last clue number circles once the hint completes it; the
        crosshair is DOM-only and is not caused by a stroke."""
        page = browser_page
        key = host[2]["mixed"]
        # Everything of row 0 correct but its last black cell: the hint is that cell.
        last = max(c for c in range(10) if CIRCLES_GRID[0][c])
        strokes = single_undecided(CIRCLES_GRID, (0, last))
        _board(page, host, key, CIRCLES_GRID, strokes)
        page.mouse.move(2, 2)
        want = expected(page)
        assert (want["row"], want["col"]) == (0, last), want
        circled = "() => JSON.stringify(window.publicPlayer && [...document.querySelectorAll('.player-clue-num')].map((n) => n.classList.contains('is-circled')))"
        module = (
            "const p = window.publicPlayer; const c = S.circledClues(p.getHistory().board, p.payload.rows, p.payload.columns);"
            " return JSON.stringify([...c.rows.flat(), ...c.columns.flat()].length ? [...document.querySelectorAll('th.player-clue.is-col .player-clue-num')].length : 0);"
        )
        assert _module_js(page, module) != "0"
        dom_before = page.evaluate(circled)
        press_to_reveal(page)
        # the page's circles are the module's for the board the hint produced
        mismatch = _module_js(
            page,
            """const p = window.publicPlayer;
            const c = S.circledClues(p.getHistory().board, p.payload.rows, p.payload.columns);
            const want = [...c.rows.flat(), ...c.columns.flat()];
            const spans = [...document.querySelectorAll('th.player-clue.is-row .player-clue-num'), ...document.querySelectorAll('th.player-clue.is-col .player-clue-num')];
            const rowsFirst = [...document.querySelectorAll('th.player-clue.is-row')].sort((a, b) => a.dataset.line - b.dataset.line)
              .flatMap((th) => [...th.querySelectorAll('.player-clue-num')]);
            const colsNext = [...document.querySelectorAll('th.player-clue.is-col')].sort((a, b) => a.dataset.line - b.dataset.line)
              .flatMap((th) => [...th.querySelectorAll('.player-clue-num')]);
            const got = [...rowsFirst, ...colsNext].map((n) => n.classList.contains('is-circled'));
            return JSON.stringify(got) === JSON.stringify(want) ? '' : 'differs';""",
        )
        assert mismatch == ""
        assert page.evaluate(circled) != dom_before, "the hint moved no circle: the scenario is vacuous"
        assert page.evaluate("() => document.querySelectorAll('.is-crossed').length") == 0, "a hint left a crosshair behind"
        # undo puts the circles back, exactly
        page.click(UNDO, force=True)
        assert page.evaluate(circled) == dom_before
        assert page.evaluate("() => document.querySelectorAll('.is-crossed').length") == 0


# ==========================================================================
# The contradicting-line decision: SKIP
# ==========================================================================
#
# ``lineForced`` answers ``null`` for a line whose clue the player's own marks
# contradict. The page SKIPS that line and deduces from the others. Surfacing it
# ("this line cannot be right") is solution-free and is the nearest honest thing
# to the error count the owner declined, but it is a feature (and a reversal of
# that decision shaped as a bug fix), so it would need its own AC and is not
# shipped. These tests hold the decision both ways: a contradicted line never
# supplies the hint, and the others still do.


def contradiction_board() -> tuple[list, tuple[int, int], int]:
    """A board on the mixed fixture whose ROW 0 is contradicted by the player's marks.

    Row 0's clue is ``[1, 1]``; filling three adjacent cells there fits no
    placement. The rest of the board is the correct marks of rows 3-9, so other
    lines still decide cells. Returns (strokes, the forced cell the oracle finds, 0).
    """
    strokes = [("filled", [(0, 0), (0, 1), (0, 2)]), *_marked(CIRCLES_GRID, rows=range(3, 10))]
    return strokes, (0, 0), 0


def _contradicted(grid, strokes) -> list[int]:
    rows, columns = clues_of(grid)
    cells = cells_after(grid, strokes)
    return [r for r in range(len(rows)) if oracle_line(rows[r], [_known(cells[r * 10 + c]) for c in range(10)]) is None]


def test_the_contradiction_fixture_contradicts_a_line_and_another_still_decides() -> None:
    strokes, _, _ = contradiction_board()
    assert _contradicted(CIRCLES_GRID, strokes) == [0]
    rows, columns = clues_of(CIRCLES_GRID)
    found = oracle_hint(cells_after(CIRCLES_GRID, strokes), 10, 10, rows, columns)
    assert found is not None and not (found["axis"] == "row" and found["index"] == 0), found


def contradiction_problems(page, host, keys) -> list[str]:
    strokes, _, _ = contradiction_board()
    problems: list[str] = []
    _board(page, host, keys["mixed"], CIRCLES_GRID, strokes)
    rows, columns = clues_of(CIRCLES_GRID)
    brute = oracle_hint(cells_after(CIRCLES_GRID, strokes), 10, 10, rows, columns)
    press(page)
    one = read(page)
    if brute is None:
        return ["vacuous: no other line decides a cell"]
    want_lit = line_parts(page, brute["axis"], brute["index"])
    if sorted(one["lit"]) != want_lit:
        problems.append(f"the hint did not come from the line the enumeration finds: {one['lit'][:3]} vs {want_lit[:3]}")
    if one["say"] != f"Hint: look at {brute['axis']} {brute['index'] + 1}.":
        problems.append(f"rung 1 said {one['say']!r}")
    press(page)
    press(page)
    after = read(page)
    index = brute["row"] * 10 + brute["col"]
    if after["recorded"][index] != brute["state"] or after["hintStrokes"] != 1:
        problems.append("rung 3 did not mark the cell the other lines decide")
    return problems


@pytest.mark.browser
class TestPublicHint_AContradictingLineIsSkipped:
    def test_a_line_the_marks_contradict_supplies_no_hint_and_the_others_still_do(self, browser_page, host) -> None:
        assert contradiction_problems(browser_page, host, host[2]) == []

    def test_a_board_where_the_only_deciding_line_is_contradicted_is_the_exhausted_state(self, browser_page, host) -> None:
        """Skipping is not surfacing: with nothing else deciding, the page says the
        same sentence as any exhausted board and reveals nothing (G-3). The board
        is found by the search in the module's notes: row 3's clue ``1 2`` has no
        placement once three adjacent cells are black, and no other line decides
        anything."""
        page = browser_page
        strokes = [("filled", [(3, 5), (3, 6), (3, 7)])]
        rows, columns = clues_of(EXHAUSTED_GRID)
        assert _contradicted(EXHAUSTED_GRID, strokes) == [3], "the fixture's premise"
        assert oracle_hint(cells_after(EXHAUSTED_GRID, strokes), 10, 10, rows, columns) is None, "the fixture's premise"
        _board(page, host, host[2]["exhausted"], EXHAUSTED_GRID, strokes)
        before = read(page)
        for _ in range(4):
            press(page)
            now = read(page)
            assert EXHAUSTED_SENTENCE in now["say"] and now["lit"] == [] and now["hinted"] == []
            assert now["recorded"] == before["recorded"] and now["done"] == before["done"] and now["counter"] == "0"


# ==========================================================================
# The structural scanner: the hint code reads no solution, has no second rule
# ==========================================================================
#
# A claim that play.js's hint "reads no solution" is a claim about SOURCE
# TEXT, so it is answered by reading it, DEFAULT-DENY (ADR-0039/R2) on
# identifiers, on PROPERTY reads, on strings, on punctuation and on computed
# member access, and with the comma operator and optional chaining refused
# outright. Two grades, because the code is of two kinds:
#
#   * the DEDUCTION (``forcedLine``, ``derivedHint`` and their three one-line
#     helpers) is real computation, so it may use operators and comparisons;
#     what it may not do is REACH anything it was not handed. Its vocabulary is
#     the locals it declares, the four cell-state constants and a handful of
#     array methods; any other identifier, any other property, any string but
#     the two axis words and any computed member whose index is not plain
#     arithmetic over its locals is refused;
#   * the GLUE that carries the answer to the DOM (``paintHintLine``,
#     ``markHinted``, ``HINT_PARTS``) claims "no second rule", so it is held to
#     a closed vocabulary with NO operator at all.
#
# Over the file as a whole: the import list, the number and shape of the calls
# to the deduction, the page's `let` variables (a page variable holding a grid
# is a new `let` or a new global) and the `window` properties it touches are
# each a closed set.

_TOKEN = re.compile(
    r'"[^"\n]*"|\'[^\'\n]*\'|`[^`]*`|[A-Za-z_$][\w$]*|\d+(?:\.\d+)?|=>|===|!==|==|!=|<=|>=|&&|\|\||\?\?|\.\.\.|[^\s\w]'
)
_IDENT = re.compile(r"^[A-Za-z_$][\w$]*$")
_NOT_A_MEMBER_BASE = {"return", "of", "in", "typeof", "case", "const", "let", "else", "new"}


class Vocabulary:
    def __init__(self, identifiers, properties, strings, numbers, punctuation, *, index_tokens=None, exact_indexes=None) -> None:
        self.identifiers = frozenset(identifiers)
        self.properties = frozenset(properties)
        self.strings = frozenset(strings)
        self.numbers = frozenset(numbers)
        self.punctuation = frozenset(punctuation)
        self.index_tokens = None if index_tokens is None else frozenset(index_tokens)
        self.exact_indexes = None if exact_indexes is None else tuple(exact_indexes)


_DEDUCTION_PUNCTUATION = {"(", ")", "{", "}", "[", "]", ",", ";", ".", "=>", "=", "===", "!==", "<", ">", "<=", ">=", "+", "-", "*", "&&", "||", "!", ":", "?"}
DEDUCTION = Vocabulary(
    identifiers={
        "export", "function", "const", "let", "for", "if", "return", "continue", "new", "null", "true", "false",
        "Array", "Object", "FILLED", "EMPTY", "UNKNOWN", "MAYBE",
        "known", "state", "isUndecided", "forcedLine", "clue", "cells", "runs", "n", "k", "fits", "at", "run", "x",
        "after", "rest", "i", "j", "blank", "placed", "reached", "canFill", "canEmpty", "_", "length",
        "derivedHint", "board", "rows", "columns", "width", "height", "rowCells", "colCells", "rowForced", "colForced",
        "decides", "forced", "row", "col", "line", "axis", "index", "canHint",
    },
    properties={"length", "filter", "map", "fill", "from", "freeze", "cells", "some"},
    strings={'"row"', '"column"'},
    numbers={"0", "1"},
    punctuation=_DEDUCTION_PUNCTUATION,
    index_tokens={"x", "i", "j", "at", "run", "row", "col", "width", "k", "n", "0", "1", "+", "-", "*", "(", ")", ",", "runs", "after", "[", "]"},
)

PAINT = Vocabulary(
    identifiers={"function", "paintHintLine", "table", "line", "on", "for", "const", "of", "selector", "part", "HINT_PARTS"},
    properties={"axis", "index", "querySelectorAll", "classList", "toggle"},
    strings={'"is-hint-line"'},
    numbers=set(),
    punctuation={"(", ")", "{", "}", "[", "]", ",", ";", ".", "=>"},
    exact_indexes=[("line", ".", "axis")],
)
MARK = Vocabulary(
    identifiers={"function", "markHinted", "cell", "on"},
    properties={"classList", "toggle"},
    strings={'"is-hinted"'},
    numbers=set(),
    punctuation={"(", ")", "{", "}", ",", ";", "."},
)
PARTS = Vocabulary(
    identifiers={"const", "HINT_PARTS", "row", "column", "index"},
    properties=set(),
    strings={
        '`td.player-cell[data-row="${index}"]`', '`th.player-clue.is-row[data-line="${index}"]`',
        '`td.player-cell[data-col="${index}"]`', '`th.player-clue.is-col[data-line="${index}"]`',
    },
    numbers=set(),
    punctuation={"=", "{", "}", ":", "(", ")", "=>", "[", "]", ",", ";"},
)


def _matching_close(tokens: list[str], at: int) -> int:
    depth = 0
    for position in range(at, len(tokens)):
        if tokens[position] in "([{":
            depth += 1
        elif tokens[position] in ")]}":
            depth -= 1
            if depth == 0:
                return position
    return len(tokens) - 1


def comma_violations(name: str, tokens: list[str]) -> list[str]:
    """A comma is a separator (call arguments, parameters, an array or object
    literal, a destructuring pattern) or it is the comma OPERATOR, which
    evaluates its left side and discards it - a place a second rule can hide."""
    problems: list[str] = []
    stack: list[str] = []
    for position, token in enumerate(tokens):
        before = tokens[position - 1] if position else ""
        if token == "(":
            close = _matching_close(tokens, position)
            after = tokens[close + 1] if close + 1 < len(tokens) else ""
            if after == "=>":
                stack.append("params")
            elif before in {"for", "if", "while", "switch", "catch"}:
                stack.append("group")
            elif (_IDENT.match(before) is not None and before not in _NOT_A_MEMBER_BASE) or before in {")", "]"}:
                stack.append("call")
            else:
                stack.append("group")
        elif token == "[":
            member = (_IDENT.match(before) is not None and before not in _NOT_A_MEMBER_BASE) or before in {")", "]"}
            stack.append("member" if member else "array")
        elif token == "{":
            stack.append("literal" if before in {"(", ",", "=", ":", "return", "[", "const", "let", "?"} else "block")
        elif token in (")", "]", "}"):
            stack.pop()
        elif token == "," and (not stack or stack[-1] not in {"call", "params", "array", "literal"}):
            problems.append(f"{name}: comma operator")
    return problems


def vocabulary_violations(name: str, body: str, vocabulary: Vocabulary) -> list[str]:
    tokens = _TOKEN.findall(body)
    problems: list[str] = []
    for position, token in enumerate(tokens):
        before = tokens[position - 1] if position else ""
        after = tokens[position + 1] if position + 1 < len(tokens) else ""
        if token[0] in "\"'`":
            if token not in vocabulary.strings:
                problems.append(f"{name}: string {token}")
        elif _IDENT.match(token):
            if before == ".":
                if token not in vocabulary.properties:
                    problems.append(f"{name}: property .{token}")
            elif token not in vocabulary.identifiers:
                problems.append(f"{name}: identifier {token}")
        elif token[0].isdigit():
            if token not in vocabulary.numbers:
                problems.append(f"{name}: number {token}")
        elif token not in vocabulary.punctuation:
            problems.append(f"{name}: token {token!r}")
        if token == "?" and after == ".":
            problems.append(f"{name}: optional chaining")
        if token == "[" and ((_IDENT.match(before) is not None and before not in _NOT_A_MEMBER_BASE) or before in {")", "]"}):
            inside, depth = [], 0
            for follower in tokens[position + 1 :]:
                if follower == "[":
                    depth += 1
                if follower == "]":
                    if depth == 0:
                        break
                    depth -= 1
                inside.append(follower)
            if vocabulary.exact_indexes is not None and tuple(inside) not in vocabulary.exact_indexes:
                problems.append(f"{name}: computed member [{' '.join(inside)}]")
            if vocabulary.index_tokens is not None and not set(inside) <= vocabulary.index_tokens:
                problems.append(f"{name}: computed member [{' '.join(inside)}]")
            if vocabulary.exact_indexes is None and vocabulary.index_tokens is None:
                problems.append(f"{name}: computed member [{' '.join(inside)}]")
    problems += comma_violations(name, list(tokens))
    return problems


def _const_object(js_source: str, name: str) -> str | None:
    text = _raw_definition_text(js_source)
    head = re.search(rf"(?m)^const\s+{re.escape(name)}\s*=\s*\{{", text)
    if head is None:
        return None
    open_at = text.index("{", head.start())
    depth = 0
    for index in range(open_at, len(text)):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        if depth == 0:
            return text[head.start() : text.index(";", index) + 1]
    return None


def _raw_definition_text(js_source: str) -> str:
    """The source with comments removed and every string KEPT."""
    out: list[str] = []
    i, n = 0, len(js_source)
    while i < n:
        ch = js_source[i]
        if js_source.startswith("//", i):
            while i < n and js_source[i] != "\n":
                i += 1
        elif js_source.startswith("/*", i):
            i = js_source.index("*/", i) + 2
        elif ch in "'\"`":
            j = i + 1
            while js_source[j] != ch:
                j += 2 if js_source[j] == "\\" else 1
            out.append(js_source[i : j + 1])
            i = j + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


_KEYWORDS_BEFORE_A_REGEX = frozenset("return typeof case of in delete void throw new else do instanceof yield await".split())


def _regex_literals(src: str, at: int = 0, nested: bool = False) -> tuple[list[str], int]:
    """The regular-expression literals of ``src`` and where the lexing stopped.

    The comment and string scanners this file leans on read a quote inside a regex
    literal as the start of a string and run on, past code they then never see; so
    the literals are found first, by a lexer that knows comments, strings, templates
    (and their ``${}``) and which ``/`` starts a regex (not after a value)."""
    found: list[str] = []
    i, n, depth, value = at, len(src), 0, False
    while i < n:
        ch = src[i]
        if src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
        elif src.startswith("/*", i):
            i = src.index("*/", i) + 2
        elif ch in "'\"":
            i += 1
            while src[i] != ch:
                i += 2 if src[i] == "\\" else 1
            i, value = i + 1, True
        elif ch == "`":
            i += 1
            while src[i] != "`":
                if src[i] == "\\":
                    i += 2
                elif src.startswith("${", i):
                    inner, i = _regex_literals(src, i + 2, True)
                    found += inner
                else:
                    i += 1
            i, value = i + 1, True
        elif ch == "/" and not value:
            j, in_class = i + 1, False
            while src[j] != "/" or in_class:
                if src[j] == "\\":
                    j += 1
                elif src[j] == "[":
                    in_class = True
                elif src[j] == "]":
                    in_class = False
                j += 1
            found.append(src[i : j + 1])
            i, value = j + 1, True
        elif ch == "{":
            depth, i, value = depth + 1, i + 1, False
        elif ch == "}":
            if nested and depth == 0:
                return found, i + 1
            depth, i, value = depth - 1, i + 1, True
        elif _WORD.match(src, i):
            word = _WORD.match(src, i).group()
            i, value = i + len(word), word not in _KEYWORDS_BEFORE_A_REGEX
        elif ch.isdigit() or ch in ")]":
            i, value = i + 1, True
        else:
            i, value = i + 1, False if not ch.isspace() else value
    return found, i


_WORD = re.compile(r"[A-Za-z_$][\w$]*")


def declaration_census(code: str) -> Counter:
    """Every ``const`` / ``let`` / ``var`` name (destructuring and comma lists too),
    every ``function`` and every ``class``, anywhere in ``code`` (comments gone, string
    bodies emptied), as ``kind:name`` -> how many times it is declared."""
    found: Counter = Counter()
    for m in re.finditer(r"\b(const|let|var)\b", code):
        j, depth, start, segs = m.end(), 0, m.end(), []
        while j < len(code):
            c = code[j]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and c == ";":
                break
            elif depth == 0 and c == ",":
                segs.append(code[start:j])
                start = j + 1
            elif depth == 0 and c.isspace() and re.match(r"\s(?:of|in)\s", code[j:]) and "=" not in code[start:j]:
                break
            j += 1
        segs.append(code[start:j])
        for seg in segs:
            for name in _WORD.findall(seg.split("=")[0]):
                found[f"{m.group(1)}:{name}"] += 1
    for m in re.finditer(r"\bfunction\b\s*\*?\s*([A-Za-z_$][\w$]*)?", code):
        found[f"function:{m.group(1) or '<anonymous>'}"] += 1
    for m in re.finditer(r"\bclass\b\s*([A-Za-z_$][\w$]*)?", code):
        found[f"class:{m.group(1) or '<anonymous>'}"] += 1
    return found


#: Every declaration in ALL of play.js (not only the hint section), as `kind:name` or
#: `kind:name*count`: 229 declarations of 186 names, DERIVED from the file at this card's tip
#: by ``declaration_census`` (not carried). A new `const stash`, a closure `const memo`, an
#: alias `const knownAlias = known`, a helper `function`/arrow-const a click handler calls,
#: or a second declaration of an old name (shadowing) changes it, and the scanner refuses.
#: RESIDUE (R3), the declared bound of "no page variable holds a grid": the census names
#: DECLARATIONS. It does not see a parameter, a property assigned onto an object the page
#: already has (`payload.x = ...`, `element.textContent = ...`), an object-literal method,
#: or an anonymous callback; of those, assignments to a member are the only ones that could
#: park a value, and play.js has 45 of them (MEMBER_ASSIGNMENTS, measured at this card's tip; each is a DOM property
#: write or a `window.publicPlayer` field). Nothing on the page carries a solution to park
#: (ADR-0041/R2, held by the asset test), so the claim is "no new NAMED variable or helper".
MEMBER_ASSIGNMENTS = 45
DECLARATION_CENSUS = Counter(
    {
        (word.split("*")[0]): (int(word.split("*")[1]) if "*" in word else 1)
        for word in """
    const:CELLS_BESIDE const:HINT_EXHAUSTED const:HINT_PARTS const:HINT_REASON_SAY const:HINT_SAY
    const:KEY const:MAJOR_EVERY const:SAVE_VERSION const:TOOLS const:actions const:after const:announce
    const:at const:axis*2 const:blank const:board*2 const:body const:box*3 const:button*3 const:canEmpty
    const:canFill const:canHint const:cell*4 const:cells*3 const:chosen const:clueNumbers const:clues
    const:col const:colCells const:colClue const:colForced const:columns*2 const:controls const:corner
    const:decides const:distanceBetween const:done*3 const:down const:first*2 const:firstId const:fits
    const:follow const:from const:head const:headRow const:height*5 const:hint*2 const:hintBar
    const:hintPointText const:hintRevealText const:hintSay const:hintsOut const:id const:inPinch
    const:isAt const:isFinger const:isUndecided const:k const:key const:known const:last const:lift
    const:line*4 const:lines const:majorAfter const:n const:next const:number const:old const:onBoard
    const:onScreen const:paint const:paints const:paragraph const:part*2 const:payload const:placed
    const:position const:previous const:reached const:reason const:regionToggle const:repeat
    const:response const:rest const:row const:rowCells const:rowClue const:rowForced const:rows*2
    const:run const:runs*2 const:sameNumbers const:saveKey const:savedStroke const:sayFor const:second
    const:segments const:selector const:sentence const:setDisabled const:showing const:solved const:span
    const:stage*2 const:state const:store const:stroke const:swatch const:table*3 const:tierChip
    const:touchPoints const:touchStartCell const:tr const:type const:undone const:visibleHeight
    const:width*5 const:zoomIn const:zoomOut const:zoomReadout function:applyZoom function:beginPinch
    function:cellUnder function:clear function:clueBox function:clueNumbersOf function:commit
    function:crossedParts function:derivedHint function:deserialize function:drawBoard function:fail
    function:forcedLine function:hintExplainText function:isClue function:isClueSolved
    function:isPainted function:keepCluesInView function:keyOf function:load function:markHinted
    function:moveTo function:paint function:paintCircles function:paintHintLine function:pinchMove
    function:readPayload function:readSave function:refresh function:releaseTouch function:runsOf
    function:say function:serialize function:setRegion function:setRung function:showHintLine
    function:showHinted function:start function:storage function:strokeOf function:syncZoom
    function:wireCrosshair function:writeSave let:col*4 let:crossed let:data*2 let:gesture let:hintLine
    let:hinted let:history*2 let:i*2 let:index let:j*2 let:k let:lastClick let:pinch let:pinching
    let:region let:row*3 let:run let:rung let:shown let:tool let:x*2 let:zoom
    """.split()
    }
)


DEDUCTION_FUNCTIONS = ("known", "isUndecided", "forcedLine", "derivedHint", "canHint")
#: The names ``start``'s `let`s and the module-level ones may have. A page
#: variable that could hold a grid is a new `let`, so the set is closed.
LET_ALLOWED = frozenset(
    "run data history crossed pinching shown tool region lastClick gesture rung hintLine hinted zoom pinch".split()
)
WINDOW_ALLOWED = frozenset({"addEventListener", "innerHeight", "localStorage", "location", "publicPlayer", "scrollY"})
IMPORT_ALLOWED = frozenset(
    "UNKNOWN FILLED EMPTY MAYBE CELL_STATES createBoard createHistory record undo redo applyStroke clickStroke dragStroke "
    "resetStroke gesturePaints nextRegion ZOOM_MIN ZOOM_MAX stepZoom pinchZoom anchoredScroll "
    "RUNG_POINT RUNG_EXPLAIN RUNG_REVEAL HINT_REASONS nextRung hintReason hintStroke hintCount circledClues".split()
)
#: What takes `solution`, or is the half of the module that would hand this
#: page a revealed cell: none may be imported.
NEVER_IMPORTED = frozenset(
    "hintCell knownLine lineForced hintLine errorCount isSolved solvedPercent firstWrongRow serializeState deserializeState".split()
)


def hint_code_violations(js_source: str) -> list[str]:
    """Every way the hint code reads what it was not handed, or says a second rule."""
    problems: list[str] = []
    literals, _ = _regex_literals(js_source)
    unreadable = [r for r in literals if re.search(r"""['"`]|//|/\*""", r)]
    if unreadable:
        # the comment/string scanners below would desynchronise on it: nothing after is trustworthy
        return [f"a regex literal the comment and string scanners misread: {unreadable[0]}"]
    for name in DEDUCTION_FUNCTIONS:
        body = _raw_definition(js_source, name)
        if body is None:
            problems.append(f"{name}: not defined")
        else:
            problems += vocabulary_violations(name, body, DEDUCTION)
    for name, vocabulary in (("paintHintLine", PAINT), ("markHinted", MARK)):
        body = _raw_definition(js_source, name)
        if body is None:
            problems.append(f"{name}: not defined")
        else:
            problems += vocabulary_violations(name, body, vocabulary)
    parts = _const_object(js_source, "HINT_PARTS")
    if parts is None:
        problems.append("HINT_PARTS: not defined")
    else:
        problems += vocabulary_violations("HINT_PARTS", parts, PARTS)
    code, strings = _scan(js_source)
    kept = _raw_definition_text(js_source)
    imported = re.search(r'import\s*\{([^}]*)\}\s*from\s*"/solver_state\.js"', kept)
    if imported is None:
        problems.append("no import from /solver_state.js")
    else:
        names = set(re.findall(r"[A-Za-z_$][\w$]*", imported.group(1)))
        if names - IMPORT_ALLOWED:
            problems.append(f"imports outside the closed set: {sorted(names - IMPORT_ALLOWED)}")
        if names & NEVER_IMPORTED:
            problems.append(f"imports a function that takes the solution: {sorted(names & NEVER_IMPORTED)}")
        if IMPORT_ALLOWED - names:
            problems.append(f"the closed import set names what is not imported: {sorted(IMPORT_ALLOWED - names)}")
    calls = re.findall(r"\bderivedHint\(([^)]*)\)", kept)
    if sorted(calls) != ["board, rows, columns", "history.board, payload.rows, payload.columns"]:
        problems.append(f"derivedHint is called as {calls}: it is defined once and asked once, of the RECORDED board")
    if len(re.findall(r"\bforcedLine\(", kept)) != 3:
        problems.append("forcedLine: must be named in code exactly three times (the definition and the two lines)")
    if re.search(r"\bsolution\b", kept):
        problems.append("the word `solution` appears in code or in a string")
    census = declaration_census(code)
    for word in sorted(census - DECLARATION_CENSUS):
        problems.append(f"a new declaration (closed census of play.js): {word}")
    for name in sorted(set(re.findall(r"(?m)^\s*let\s+([A-Za-z_$][\w$]*)", code)) - LET_ALLOWED):
        problems.append(f"a new page variable: let {name}")
    for prop in sorted(set(re.findall(r"\bwindow\.([A-Za-z_$][\w$]*)", code)) - WINDOW_ALLOWED):
        problems.append(f"window.{prop} is touched")
    if re.search(r"\b(?:globalThis|self|parent|top|eval|Function|fetch)\b(?!\()|\beval\(|\bFunction\(", code) and len(re.findall(r"\bfetch\(", code)) != 1:
        problems.append("a global escape hatch is named")
    return problems


def test_the_scanner_finds_the_hint_code_and_passes_the_real_file() -> None:
    source = PLAY_JS.read_text(encoding="utf-8")
    assert hint_code_violations(source) == []
    for name in (*DEDUCTION_FUNCTIONS, "paintHintLine", "markHinted"):
        assert _raw_definition(source, name) is not None, name
    assert _const_object(source, "HINT_PARTS") is not None


#: Bypasses of the scanner, each planted into a COPY of the real file and each
#: required to be refused, beside the unplanted copy that must pass. Eight
#: kinds the earlier scanners were walked through (CARD-325's seven, CARD-326's
#: comma operator) and the ones this vocabulary adds.
BYPASSES = [
    ("a-global-by-identifier", "  const n = cells.length;\n  const k = runs.length;",
     "  const n = cells.length;\n  const k = runs.length + window.publicPlayer.payload.height * 0;", "identifier window"),
    ("a-property-read", "  const k = runs.length;", "  const k = runs.length + cells.solution;", "property .solution"),
    ("a-computed-member-from-strings", "  const k = runs.length;", '  const k = cells["len" + "gth"];', "string"),
    ("optional-chaining", "  const k = runs.length;", "  const k = cells?.length;", "optional chaining"),
    ("the-comma-operator", "  const k = runs.length;", "  const k = (0, runs.length);", "comma operator"),
    ("the-comma-operator-in-an-index", "        canEmpty[i] = true;\n      }\n      if (j < k",
     "        canEmpty[(i, i)] = true;\n      }\n      if (j < k", "comma operator"),
    ("a-number-in-an-index", "        reached[i + 1][j] = true;", "        reached[i + 1][2] = true;", "number 2"),
    ("a-template-index", "  const k = runs.length;", "  const k = cells[`length`];", "string"),
    ("this", "  const k = runs.length;", "  const k = this.length;", "identifier this"),
    ("the-function-constructor", "  const k = runs.length;", '  const k = Function("return 1")();', "identifier Function"),
    ("an-operator-the-vocabulary-lacks", "  const k = runs.length;", "  const k = runs.length % 1;", "token '%'"),
    ("loose-inequality", "  if (!rest[0][0]) return null;", "  if (rest[0][0] != true) return null;", "token '!='"),
    ("a-dynamic-import", "  const k = runs.length;", '  const k = import("/x.js");', "identifier import"),
    ("a-second-rule-in-the-painter", '    for (const part of table.querySelectorAll(selector)) part.classList.toggle("is-hint-line", on);',
     '    for (const part of table.querySelectorAll(selector)) part.classList.toggle("is-hint-line", on && selector.length);',
     "token '&&'"),
    ("a-condition-in-the-painter", '    for (const part of table.querySelectorAll(selector)) part.classList.toggle("is-hint-line", on);',
     '    for (const part of table.querySelectorAll(selector)) if (on) part.classList.toggle("is-hint-line", on);', "identifier if"),
    ("a-comma-operator-in-the-painter", '    for (const part of table.querySelectorAll(selector)) part.classList.toggle("is-hint-line", on);',
     '    for (const part of table.querySelectorAll(selector)) part.classList.toggle("is-hint-line", (on, on));', "comma operator"),
    ("the-painter-reads-another-index", "HINT_PARTS[line.axis](line.index)", 'HINT_PARTS["row"](line.index)', "string"),
    ("the-painter-indexes-by-the-wrong-property", "HINT_PARTS[line.axis](line.index)", "HINT_PARTS[line.index](line.index)", "computed member"),
    ("the-marker-is-given-a-constant", 'cell.classList.toggle("is-hinted", on);', 'cell.classList.toggle("is-hinted", true);', "identifier true"),
    ("a-fetch-by-name", "  const k = runs.length;", '  const k = fetch("/puzzle/x.json");', "identifier fetch"),
    ("an-import-that-reads-the-solution", "  nextRung, hintReason, hintStroke, hintCount,", "  nextRung, hintReason, hintStroke, hintCount, hintCell,", "imports"),
    ("a-second-ask-of-the-deduction", "    const hint = derivedHint(history.board, payload.rows, payload.columns);",
     "    const hint = derivedHint(history.board, payload.rows, payload.columns);\n    derivedHint(shown, payload.rows, payload.columns);", "derivedHint is called"),
    ("a-new-page-variable", "  let rung = RUNG_POINT;", "  let rung = RUNG_POINT;\n  let stash = null;", "a new page variable: let stash"),
    ("a-new-global", "  controls.hidden = false;", "  window.stash = [];\n  controls.hidden = false;", "window.stash"),
    # CARD-327 review 1, F-2: the five bypasses the `let`/`window` default-deny let through.
    ("a-module-level-const-stash", "const HINT_EXHAUSTED =", "const stash = [];\nconst HINT_EXHAUSTED =", "const:stash"),
    ("a-closure-const-memo", "  let rung = RUNG_POINT;", "  const memo = {};\n  let rung = RUNG_POINT;", "const:memo"),
    ("an-alias-const", "const known = (state) => (state === FILLED || state === EMPTY ? state : UNKNOWN);",
     "const known = (state) => (state === FILLED || state === EMPTY ? state : UNKNOWN);\nconst knownAlias = known;", "const:knownAlias"),
    ("an-unscanned-function-called-from-the-click-handler", '    setRung(nextRung(rung, "press"));',
     '    function fallback() { return history.board.cells.findIndex(isUndecided); }\n    fallback();\n    setRung(nextRung(rung, "press"));', "function:fallback"),
    ("an-unscanned-arrow-const-called-from-the-click-handler", '    setRung(nextRung(rung, "press"));',
     '    const fallback = () => history.board.cells.findIndex(isUndecided);\n    fallback();\n    setRung(nextRung(rung, "press"));', "const:fallback"),
    ("an-old-name-declared-again-in-a-closure", "  let rung = RUNG_POINT;", "  const history = [];\n  let rung = RUNG_POINT;", "const:history"),
    ("a-regex-literal-holding-a-quote", "const known = (state)", "const quoteDesync = /'/;\nconst known = (state)", "regex literal"),
    ("a-regex-literal-holding-a-backtick", "const known = (state)", "const tickDesync = /`/;\nconst known = (state)", "regex literal"),
    ("the-word-in-a-string", "const HINT_EXHAUSTED =", 'const SOLUTION_TAG = "solution";\nconst HINT_EXHAUSTED =', "`solution`"),
]


@pytest.mark.parametrize(("label", "old", "new", "expect"), BYPASSES, ids=[b[0] for b in BYPASSES])
def test_a_bypass_is_refused_beside_its_clean_control(label, old, new, expect) -> None:
    source = PLAY_JS.read_text(encoding="utf-8")
    assert hint_code_violations(source) == [], "the matched control"
    assert source.count(old) == 1, f"the plant must apply exactly once: {old!r} ({source.count(old)})"
    found = hint_code_violations(source.replace(old, new))
    assert any(expect in problem for problem in found), (label, found)


def test_the_declaration_census_is_the_whole_file_and_is_not_vacuous() -> None:
    """The control for the census: it reads play.js as a WHOLE (not the hint section), equals the
    closed set exactly (a stale entry fails as a new one does), and a planted declaration moves it."""
    source = PLAY_JS.read_text(encoding="utf-8")
    code, _ = _scan(source)
    census = declaration_census(code)
    assert census == DECLARATION_CENSUS
    assert (len(census), sum(census.values())) == (186, 229)
    assert {"function:start", "const:HINT_PARTS", "function:wireCrosshair", "const:KEY", "function:storage"} <= set(census)
    planted, _ = _scan(source.replace("const known = (state)", "const stash = [];\nconst known = (state)", 1))
    assert declaration_census(planted) - DECLARATION_CENSUS == Counter({"const:stash": 1})
    # R3: the residue the census does not see, measured: member assignments (a value parked on an object)
    assert len(re.findall(r"\.[A-Za-z_$][\w$]*\s*(?:=|\+=|-=)(?!=)|\]\s*(?:=|\+=)(?!=)", code)) == MEMBER_ASSIGNMENTS


def test_the_regex_lexer_finds_the_one_literal_and_nothing_in_strings() -> None:
    literals, _ = _regex_literals(PLAY_JS.read_text(encoding="utf-8"))
    assert literals == ["/^[0-9a-f]{10}$/"]
    assert _regex_literals("const a = x / 2; const b = 'it/s'; const c = `${y / 3}/`; // /q/\n")[0] == []


def test_there_are_at_least_eight_bypasses_and_every_vocabulary_has_one() -> None:
    assert len(BYPASSES) >= 8
    kinds = {expect for *_, expect in BYPASSES}
    for needed in ("identifier", "property", "string", "optional chaining", "comma operator", "number", "token", "computed member"):
        assert any(needed in k for k in kinds), needed


# ==========================================================================
# AC-6 - no answer anywhere, and the asset is unchanged
# ==========================================================================

PUZZLE_FIELDS = ["clues", "height", "key", "tier", "width"]  # carried: measured 2026-10-30 (the card), re-derived below


def served_puzzles(site_dir: Path) -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((site_dir / "puzzle").glob("*.json"))}


def _stage_walk_arg(grid) -> dict:
    height, width = len(grid), len(grid[0])
    return {"w": width, "h": height, "solution": ["filled" if grid[r][c] else "empty" for r in range(height) for c in range(width)]}


#: Walks the page's data: every window property that is not a browser built-in,
#: and every localStorage value, looking for a structure that IS a solution
#: grid (a flat or nested array of w*h decided cells all agreeing with it).
_GLOBALS_WALK = """(arg) => {
  const frame = document.createElement('iframe');
  document.body.append(frame);
  const builtin = new Set(Object.getOwnPropertyNames(frame.contentWindow));
  frame.remove();
  const custom = Object.getOwnPropertyNames(window).filter((name) => !builtin.has(name) && name !== '__served');
  const decided = (v) => (v === true || v === 'filled' || v === 1 ? 'filled' : (v === false || v === 'empty' || v === 0 ? 'empty' : null));
  const isGrid = (flat) => flat.length === arg.w * arg.h && flat.every((v, i) => decided(v) === arg.solution[i]);
  const seen = new Set();
  const hits = [];
  const walk = (value, path, depth) => {
    if (value === null || typeof value !== 'object' || seen.has(value) || depth > 7) return;
    seen.add(value);
    if (Array.isArray(value)) {
      if (isGrid(value)) hits.push(path);
      if (value.length === arg.h && value.every((row) => Array.isArray(row) && row.length === arg.w) && isGrid(value.flat())) hits.push(path);
    }
    for (const key of Object.getOwnPropertyNames(value)) {
      let child;
      try { child = value[key]; } catch (e) { continue; }
      walk(child, path + '.' + key, depth + 1);
    }
  };
  for (const name of custom) walk(window[name], name, 0);
  const stored = [];
  for (let i = 0; i < localStorage.length; i += 1) {
    const text = localStorage.getItem(localStorage.key(i));
    try { walk(JSON.parse(text), 'localStorage', 0); } catch (e) { /* not JSON */ }
    stored.push(localStorage.key(i));
  }
  return { custom, hits, stored };
}"""


def walk_globals(page, grid) -> dict:
    return page.evaluate(_GLOBALS_WALK, _stage_walk_arg(grid))


def _nearly_solved(grid, hold_back: int) -> list:
    """The correct marks of every cell but the last ``hold_back`` black ones."""
    black = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v]
    return [("filled", black[:-hold_back] if hold_back else black)]


def stash_problems(page, errors, host, keys) -> list[str]:
    """After hints on a partly marked board, the page has one global, and no walkable
    data in it, in localStorage or in the DOM's data attributes is a solution grid."""
    problems: list[str] = []
    for name in ("min", "mixed"):
        grid = FIXTURES[name]
        _board(page, host, keys[name], grid, _marked(grid, rows=range(2)))
        for _ in range(7):
            press(page)
        walked = walk_globals(page, grid)
        if walked["custom"] != ["publicPlayer"]:
            problems.append(f"{name}: the page defines globals {walked['custom']}")
        if walked["hits"]:
            problems.append(f"{name}: a solution grid is reachable at {walked['hits']}")
    return problems


@pytest.mark.browser
class TestPublicHint_TheAssetGainsNothing:
    def test_every_served_puzzle_file_carries_exactly_the_five_fields(self, host) -> None:
        puzzles = served_puzzles(host[1].site_dir)
        assert len(puzzles) == len(FIXTURES) and len(puzzles) >= 6
        for key, payload in puzzles.items():
            assert sorted(payload) == PUZZLE_FIELDS, (key, sorted(payload))

    def test_the_hint_adds_no_request_and_the_only_one_is_the_get_of_its_own_puzzle(self, browser_page, host) -> None:
        page = browser_page
        url, _, keys = host
        seen: list[tuple[str, str]] = []
        page.context.on("request", lambda request: seen.append((request.method, request.url)))
        key = keys["mixed"]
        _open(page, host, key)
        page.wait_for_timeout(300)
        after_load = list(seen)
        for _ in range(9):  # three full ladders: points, explains, reveals
            press(page)
        page.click(UNDO, force=True)
        page.click(REDO, force=True)
        page.reload()
        page.wait_for_function("window.publicPlayer !== undefined")
        page.wait_for_timeout(300)
        assert all(method == "GET" for method, _ in seen), [s for s in seen if s[0] != "GET"]
        later = [address for _, address in seen[len(after_load) :]]
        assert all(address.startswith(url + "/") for address in later)
        puzzle_gets = [address for _, address in seen if address.endswith(".json")]
        assert set(puzzle_gets) == {f"{url}/puzzle/{key}.json"}, puzzle_gets
        assert len(puzzle_gets) == 2, "one GET per load (two loads), and nothing per hint"
        assert not [m for m, _ in after_load if m != "GET"]

    def test_the_page_holds_one_global_and_no_solution_grid_before_and_after_hints(self, browser_page, host) -> None:
        page = browser_page
        assert stash_problems(page, [], host, host[2]) == []

    def test_across_a_seeded_corpus_no_hint_leaves_a_grid_behind(self, browser_page, host) -> None:
        """EC (ADR-0041/R2): extents, tiers and mark patterns; minimum case count asserted."""
        page = browser_page
        rng = random.Random(327)
        cases = 0
        for name, grid in FIXTURES.items():
            height, width = len(grid), len(grid[0])
            for pattern in ("blank", "correct-30", "with-maybe", "with-a-wrong-mark"):
                cells = [(r, c) for r in range(height) for c in range(width)]
                chosen = rng.sample(cells, len(cells) * 3 // 10) if pattern != "blank" else []
                strokes = [("filled" if grid[r][c] else "empty", [(r, c)]) for r, c in chosen]
                if pattern == "with-maybe":
                    strokes += [("maybe", [cells[rng.randrange(len(cells))]]) for _ in range(5)]
                if pattern == "with-a-wrong-mark" and chosen:
                    r, c = chosen[0]
                    strokes.append(("empty" if grid[r][c] else "filled", [(r, c)]))
                _board(page, host, host[2][name], grid, strokes)
                for _ in range(rng.randrange(1, 10)):
                    press(page)
                walked = walk_globals(page, grid)
                assert walked["custom"] == ["publicPlayer"] and walked["hits"] == [], (name, pattern, walked)
                cases += 1
        assert cases >= 24, cases

    def test_a_page_that_stashes_the_solution_is_caught(self, plant_page, host) -> None:
        """The control for the walk: the page, re-served with code that iterates its own
        deduction to a fixed point and keeps the result in a global, is refused by the
        two things that would catch it (the global census and the grid walk)."""
        page, errors = plant_page
        keys = host[2]
        assert stash_problems(page, errors, host, keys) == [], "the matched control, on the same page"
        stash = (
            "  { let work = createBoard(payload.width, payload.height);\n"
            "    for (let hint = derivedHint(work, payload.rows, payload.columns); hint !== null;"
            " hint = derivedHint(work, payload.rows, payload.columns)) {\n"
            "      work = applyStroke(work, hintStroke(hint.row, hint.col, hint.state)); }\n"
            "    window.__stash = work.cells; }\n"
        )
        serve_planted(page, host, "play.js", [("  controls.hidden = false;\n", stash + "  controls.hidden = false;\n")], "stash")
        found = stash_problems(page, errors, host, keys)
        assert page.evaluate("window.__served") == "stash", "the plant was not served"
        assert any("globals" in p for p in found) and any("solution grid is reachable" in p for p in found), found

    def test_the_scanner_also_refuses_the_stash_in_source(self) -> None:
        source = PLAY_JS.read_text(encoding="utf-8")
        planted = source.replace("  controls.hidden = false;\n", "  window.__stash = createBoard(payload.width, payload.height).cells;\n  controls.hidden = false;\n")
        assert any("window.__stash" in p for p in hint_code_violations(planted))


def serve_planted(page, host, name: str, edits: list[tuple[str, str]], canary: str) -> None:
    """Serve ``name`` with ``edits`` applied, by ROUTE, plus a canary the page reports.

    A route fulfils every request for the name itself, and Playwright switches
    the HTTP cache off while one is active, so a file the control run already
    fetched cannot be served stale to the plant's run (CARD-326's measurement:
    rewriting the served file and switching the cache off through CDP both let
    plants go unserved at random). The canary is the proof of service: the
    caller asserts ``window.__served`` before believing a plant fired or did not.
    """
    text = (host[1].site_dir / name).read_text(encoding="utf-8")
    for old, new in edits:
        assert text.count(old) == 1, f"the plant must apply exactly once to {name}: {old!r} ({text.count(old)})"
        text = text.replace(old, new)
    body = text + (f'\nwindow.__served = "{canary}";\n' if name.endswith(".js") else "")
    kind = "text/javascript" if name.endswith(".js") else "text/css"
    page.route(f"**/{name}", lambda route: route.fulfill(status=200, body=body, content_type=kind))


# ==========================================================================
# AC-8 - the comment is true
# ==========================================================================

def header_of(js_source: str) -> str:
    lines = []
    for line in js_source.splitlines():
        if not line.startswith("//"):
            break
        lines.append(line[2:].strip())
    return " ".join(part for part in lines if part)


def header_claim_violations(js_source: str) -> list[str]:
    return claim_text_violations(" ".join(header_of(js_source).split()))


#: The four things the header must say, each as the text that says it and the
#: problem its absence is reported as. Every one is individually load-bearing:
#: ``test_each_part_of_the_claim_is_individually_load_bearing`` removes each in turn.
CLAIMS = (
    ("the error count, the progress percent and Check need the answer", "named as needing the answer"),
    ("THE HINT DOES NOT NEED IT", "not named as not needing the answer"),
    ("hint below DERIVES the next cell from the clues", "not named as deriving"),
    ("no fallback that reveals a cell", "missing fallback is not stated"),
)
RETRACTED_PHRASES = (
    "No error count, no progress percent, no hints",
    "Adding any of them publicly needs the answer",
    "and hintCell all take `solution`",
)


def claim_text_violations(header: str) -> list[str]:
    """The header's account of what the page can and cannot do, held to what it names."""
    problems = [f"the retracted claim is still written: {phrase!r}" for phrase in RETRACTED_PHRASES if phrase in header]
    problems += [f"{message}" for text, message in CLAIMS if text not in header]
    return problems


def behaviour_problems(page, host, keys) -> list[str]:
    """What the header says, observed: a hint that derives, and no error count, progress or Check."""
    problems: list[str] = []
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    want = expected(page)
    press_to_reveal(page)
    after = read(page)
    if want is None or after["hintStrokes"] != 1:
        problems.append("the hint does not derive a cell")
    if page.evaluate("() => document.querySelectorAll('[data-player-action=\"check\"], [data-player-errors], [data-player-progress]').length") != 0:
        problems.append("the page has a Check, error-count or progress control")
    text = page.evaluate("() => document.body.innerText")
    for word in ("Errors", "Progress", "Check"):
        if re.search(rf"\b{word}\b", text):
            problems.append(f"the page says {word!r}")
    return problems


class TestPublicHint_TheHeaderClaimIsTrue:
    def test_the_header_states_what_holds_and_not_what_was_false(self) -> None:
        assert header_claim_violations(PLAY_JS.read_text(encoding="utf-8")) == []

    def test_the_old_header_is_refused(self) -> None:
        """The control: the retracted sentence, restored, reds the claim check."""
        source = PLAY_JS.read_text(encoding="utf-8")
        start = source.index("//   * solver_state.js's isSolved")
        end = source.index("//   * the save below")
        old = (
            "//   * solver_state.js's isSolved, errorCount, solvedPercent and hintCell all\n"
            "//     take `solution` and are therefore unreachable from this page. No error\n"
            "//     count, no progress percent, no hints (CARD-283 G-4). Adding any of them\n"
            "//     publicly needs the answer, which is a new architecture question;\n"
        )
        found = header_claim_violations(source[:start] + old + source[end:])
        assert len(found) >= 4 and any("retracted" in p for p in found), found

    @pytest.mark.parametrize(("text", "message"), CLAIMS, ids=[m for _, m in CLAIMS])
    def test_each_part_of_the_claim_is_individually_load_bearing(self, text, message) -> None:
        flat = " ".join(header_of(PLAY_JS.read_text(encoding="utf-8")).split())
        assert claim_text_violations(flat) == [], "the matched control"
        assert flat.count(text) == 1, text
        assert claim_text_violations(flat.replace(text, "XX")) == [message]

    @pytest.mark.parametrize("phrase", RETRACTED_PHRASES, ids=["no-hints", "needs-the-answer", "hintcell-takes-solution"])
    def test_each_retracted_phrase_is_individually_refused(self, phrase) -> None:
        flat = " ".join(header_of(PLAY_JS.read_text(encoding="utf-8")).split())
        assert claim_text_violations(flat + " " + phrase) == [f"the retracted claim is still written: {phrase!r}"]

    @pytest.mark.browser
    def test_the_behaviour_the_header_names_is_the_behaviour(self, browser_page, host) -> None:
        assert behaviour_problems(browser_page, host, host[2]) == []

    @pytest.mark.browser
    def test_a_page_with_a_check_button_makes_the_claim_false(self, plant_page, host) -> None:
        page, errors = plant_page
        assert behaviour_problems(page, host, host[2]) == [], "the matched control"
        page.route(
            "**/play/*",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body=(host[1].site_dir / "play" / "index.html").read_text(encoding="utf-8").replace(
                    '<div class="player-hint-bar" data-player-hint-bar hidden>',
                    '<div class="player-hint-bar" data-player-hint-bar hidden><button data-player-action="check">Check</button>',
                ),
            ),
        )
        found = behaviour_problems(page, host, host[2])
        assert any("Check" in p for p in found), found


# ==========================================================================
# AC-7 - the two deductions agree
# ==========================================================================
#
# The public player's native ``derivedHint`` against ``solver_state.js``'s own
# ``hintCell``. The two are comparable only where ``knownLine`` is the identity,
# i.e. on boards with no WRONG mark (a "?" is read as undecided by both). On a
# board with a wrong mark they legitimately differ - ``hintCell`` reads the wrong
# mark as undecided, the page cannot - and what the test holds there is exactly
# what the page promises instead: ``derivedHint`` equals the module's
# ``lineForced`` run over the board as the player has it.

#: (width, height) of the corpus's boards. The first four are small enough for
#: the brute-force oracle; the last two are the extremes of the supported range.
EXTENTS = [(10, 10), (11, 12), (12, 12), (15, 10), (20, 20), (30, 30)]
ORACLE_MAX_CELLS = 15 * 12


def make_corpus(seed: int = 3270, count: int = 360) -> list[dict]:
    rng = random.Random(seed)
    cases = []
    for n in range(count):
        width, height = EXTENTS[n % len(EXTENTS)] if n % 3 else EXTENTS[rng.randrange(4)]
        density = rng.choice([0.3, 0.5, 0.7])
        grid = [[rng.random() < density for _ in range(width)] for _ in range(height)]
        rows, columns = clues_of(grid)
        marked = rng.choice([0.2, 0.5, 0.8])
        cells = ["unknown"] * (width * height)
        for i in range(width * height):
            if rng.random() < marked:
                cells[i] = "filled" if grid[i // width][i % width] else "empty"
            elif rng.random() < 0.05:
                cells[i] = "maybe"
        if n % 3 == 2:  # a third carry wrong marks, enough that some of them matter to the first hint
            decided = [i for i, s in enumerate(cells) if s in ("filled", "empty")]
            for i in rng.sample(decided, min(len(decided), rng.randrange(4, 11))):
                cells[i] = "empty" if cells[i] == "filled" else "filled"
        cases.append({"w": width, "h": height, "grid": grid, "rows": rows, "cols": columns, "cells": cells})
    return cases


def has_wrong_mark(case: dict) -> bool:
    return any(
        state in ("filled", "empty") and state != ("filled" if case["grid"][i // case["w"]][i % case["w"]] else "empty")
        for i, state in enumerate(case["cells"])
    )


_CORPUS_JS = """async (cases) => {
  const S = await import('/solver_state.js');
  const P = await import('/play.js');
  const expectOf = (b, rows, columns) => {
    const { width, height } = b;
    const row = (r) => Array.from({ length: width }, (_, c) => b.cells[r * width + c]);
    const col = (c) => Array.from({ length: height }, (_, r) => b.cells[r * width + c]);
    const rf = rows.map((clue, r) => S.lineForced(clue, row(r)));
    const cf = columns.map((clue, c) => S.lineForced(clue, col(c)));
    for (let r = 0; r < height; r += 1) {
      for (let c = 0; c < width; c += 1) {
        const here = b.cells[r * width + c];
        if (here !== S.UNKNOWN && here !== S.MAYBE) continue;
        if (rf[r] !== null && rf[r][c] !== S.UNKNOWN) return { row: r, col: c, state: rf[r][c], axis: 'row', index: r };
        if (cf[c] !== null && cf[c][r] !== S.UNKNOWN) return { row: r, col: c, state: cf[c][r], axis: 'column', index: c };
      }
    }
    return null;
  };
  return cases.map((c) => {
    const board = { width: c.w, height: c.h, cells: c.cells };
    const mine = P.derivedHint(board, c.rows, c.cols);
    const theirs = S.hintCell(board, c.rows, c.cols, c.grid);
    return {
      mine: mine && { row: mine.row, col: mine.col, state: mine.state, axis: mine.line.axis, index: mine.line.index },
      theirs: theirs && { row: theirs.row, col: theirs.col, state: theirs.state, deduced: theirs.deduced },
      raw: expectOf(board, c.rows, c.cols),
    };
  });
}"""


def run_corpus(page, cases: list[dict]) -> list[dict]:
    return page.evaluate(_CORPUS_JS, cases)


def _cell(h: dict | None) -> tuple | None:
    return None if h is None else (h["row"], h["col"], h["state"])


def corpus_problems(page, cases: list[dict]) -> list[str]:
    """Every way the page's deduction disagrees with the module's ``lineForced`` (all
    boards), with ``hintCell`` (boards with no wrong mark) and with the enumeration."""
    problems: list[str] = []
    results = run_corpus(page, cases)
    for number, (case, got) in enumerate(zip(cases, results, strict=True)):
        mine = got["mine"]
        if (_cell(mine), None if mine is None else (mine["axis"], mine["index"])) != (
            _cell(got["raw"]), None if got["raw"] is None else (got["raw"]["axis"], got["raw"]["index"])
        ):
            problems.append(f"case {number}: derivedHint {mine} != lineForced over the player's board {got['raw']}")
        if not has_wrong_mark(case):
            theirs = got["theirs"]
            want = _cell(theirs) if theirs is not None and theirs["deduced"] else None
            if _cell(mine) != want:
                problems.append(f"case {number}: clean board, derivedHint {_cell(mine)} != hintCell {want}")
        if case["w"] * case["h"] <= ORACLE_MAX_CELLS:
            brute = oracle_hint(case["cells"], case["w"], case["h"], case["rows"], case["cols"])
            if _cell(mine) != _cell(brute):
                problems.append(f"case {number}: derivedHint {_cell(mine)} != enumeration {_cell(brute)}")
        if len(problems) > 8:
            break
    return problems


@pytest.mark.browser
class TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards:
    @pytest.fixture
    def corpus(self):
        return make_corpus()

    def test_the_corpus_is_big_and_has_every_kind_of_board(self, corpus) -> None:
        wrong = [c for c in corpus if has_wrong_mark(c)]
        clean = [c for c in corpus if not has_wrong_mark(c)]
        assert len(corpus) >= 300 and len(clean) >= 200 and len(wrong) >= 60, (len(corpus), len(clean), len(wrong))
        assert {(c["w"], c["h"]) for c in corpus} == set(EXTENTS)
        assert sum(1 for c in corpus if "maybe" in c["cells"]) >= 100
        assert sum(1 for c in corpus if c["w"] * c["h"] <= ORACLE_MAX_CELLS) >= 200

    def test_the_page_agrees_with_the_module_and_the_enumeration(self, browser_page, host, corpus) -> None:
        page = browser_page
        _open(page, host, host[2]["mixed"])
        assert corpus_problems(page, corpus) == []

    def test_where_a_mark_is_wrong_the_two_differ_and_only_there(self, browser_page, host, corpus) -> None:
        page = browser_page
        _open(page, host, host[2]["mixed"])
        results = run_corpus(page, corpus)
        differ = []
        for case, got in zip(corpus, results, strict=True):
            theirs = got["theirs"]
            want = _cell(theirs) if theirs is not None and theirs["deduced"] else None
            if _cell(got["mine"]) != want:
                differ.append(case)
        assert differ, "no board shows the legitimate difference: the claim is untested"
        assert all(has_wrong_mark(c) for c in differ), "the two differ on a board with no wrong mark"
        assert len(differ) >= 8, len(differ)
        # and the consequence the card declares: a hint taken over a wrong mark can itself be wrong
        wrong_hints = 0
        for case, got in zip(corpus, results, strict=True):
            mine = got["mine"]
            if mine is not None and mine["state"] != ("filled" if case["grid"][mine["row"]][mine["col"]] else "empty"):
                wrong_hints += 1
                assert has_wrong_mark(case), "a hint disagreed with the solution on a board with no wrong mark"
        assert wrong_hints >= 1, "the declared consequence never occurs in the corpus"

    def test_a_clean_board_never_gets_a_hint_that_disagrees_with_the_solution(self, browser_page, host, corpus) -> None:
        page = browser_page
        _open(page, host, host[2]["mixed"])
        checked = 0
        for case, got in zip(corpus, run_corpus(page, corpus), strict=True):
            if has_wrong_mark(case) or got["mine"] is None:
                continue
            checked += 1
            truth = "filled" if case["grid"][got["mine"]["row"]][got["mine"]["col"]] else "empty"
            assert got["mine"]["state"] == truth
        assert checked >= 150, checked


# ==========================================================================
# Scenarios and plants
# ==========================================================================
#
# A scenario drives the page one way and returns the ways it disagreed with
# what it must do. A PLANT rewrites the served play.js; each one is run beside
# its matched control in the same test, and the set of scenarios that fired is
# pinned, so "some problem" is never enough: the plant has to fire the
# scenario that is about the thing it broke.


def sc_ladder(page, host, keys) -> list[str]:
    problems: list[str] = []
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    rungs = _module_js(page, "return [...S.HINT_RUNGS];")
    want = expected(page)
    if want is None:
        return ["vacuous: nothing to hint"]
    before = read(page)
    press(page)
    one = read(page)
    if sorted(one["lit"]) != line_parts(page, want["axis"], want["index"]):
        problems.append("rung 1 did not light the line the deduction comes from")
    if one["say"] != f"Hint: look at {want['axis']} {want['index'] + 1}.":
        problems.append(f"rung 1 said {one['say']!r}")
    if one["rung"] != rungs[1]:
        problems.append(f"after one press the rung is {one['rung']}")
    press(page)
    two = read(page)
    if " — " not in two["say"] or two["rung"] != rungs[2] or two["done"] != 0:
        problems.append(f"rung 2 said {two['say']!r} at rung {two['rung']}")
    press(page)
    three = read(page)
    index = want["row"] * 10 + want["col"]
    if three["recorded"][index] != want["state"]:
        problems.append(f"rung 3 marked {three['recorded'][index]!r}, lineForced says {want['state']!r}")
    if [i for i in range(100) if three["recorded"][i] != before["recorded"][i]] != [index]:
        problems.append("rung 3 changed a cell other than the derived one")
    if (three["hintStrokes"], three["counter"], three["done"]) != (1, "1", 1):
        problems.append(f"rung 3 recorded {three['hintStrokes']} hint strokes, counter {three['counter']!r}")
    if three["rung"] != rungs[0] or three["lit"] != []:
        problems.append(f"after the reveal the ladder is at {three['rung']} with {len(three['lit'])} lit")
    if three["hinted"] != [[want["row"], want["col"]]]:
        problems.append(f"the hinted cell is {three['hinted']}")
    return problems


def _single(page, host, keys, where) -> dict:
    _board(page, host, keys["mixed"], CIRCLES_GRID, single_undecided(CIRCLES_GRID, where))
    return read(page)


def sc_edges(page, host, keys) -> list[str]:
    """The first and the last line, the last row and the last column, a tie, a column alone."""
    problems: list[str] = []
    rows, columns = clues_of(CIRCLES_GRID)
    for where, label in (((0, 0), "first line"), ((9, 9), "last line"), ((4, 9), "last column"), ((9, 4), "last row")):
        _single(page, host, keys, where)
        brute = oracle_hint(cells_after(CIRCLES_GRID, single_undecided(CIRCLES_GRID, where)), 10, 10, rows, columns)
        press(page)
        one = read(page)
        # both its row and its column decide it, so a tie: the ROW is named
        if brute is None or one["say"] != f"Hint: look at row {where[0] + 1}.":
            problems.append(f"{label}: rung 1 said {one['say']!r} (a tie goes to the row)")
        press(page)
        press(page)
        three = read(page)
        if three["recorded"][where[0] * 10 + where[1]] != (brute or {}).get("state"):
            problems.append(f"{label}: the cell {where} was not derived")
    # a column alone: the row has two places left for one of its black cells
    black = [(a, b) for a in range(10) for b in range(10) if CIRCLES_GRID[a][b] and (a, b) not in ((0, 0), (0, 1))]
    white = [(a, b) for a in range(10) for b in range(10) if not CIRCLES_GRID[a][b] and (a, b) not in ((0, 0), (0, 1))]
    strokes = [("empty", white), ("filled", black)]
    _board(page, host, keys["mixed"], CIRCLES_GRID, strokes)
    brute = oracle_hint(cells_after(CIRCLES_GRID, strokes), 10, 10, rows, columns)
    press(page)
    one = read(page)
    if brute is None or brute["axis"] != "column" or one["say"] != "Hint: look at column 1.":
        problems.append(f"a cell only its column decides: rung 1 said {one['say']!r}")
    if sorted(one["lit"]) != line_parts(page, "column", 0):
        problems.append("a cell only its column decides: the column was not lit")
    return problems


def sc_contradiction(page, host, keys) -> list[str]:
    return contradiction_problems(page, host, keys)


def sc_exhausted(page, host, keys) -> list[str]:
    return exhausted_problems(page, host, keys)


def sc_reset(page, host, keys) -> list[str]:
    problems: list[str] = []
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    press(page)
    lit = read(page)
    if lit["rung"] == 1 or not lit["lit"]:
        return ["vacuous: one press did not climb"]
    _tap(page, 9, 9)
    after = read(page)
    if after["rung"] != _module_js(page, "return S.nextRung(arg, 'change');", lit["rung"]) or after["lit"] or after["say"] != "":
        problems.append(f"a board change left the ladder at rung {after['rung']} with {len(after['lit'])} lit and {after['say']!r}")
    return problems


def sc_undo(page, host, keys) -> list[str]:
    problems: list[str] = []
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    want = expected(page)
    press_to_reveal(page)
    revealed = read(page)
    index = want["row"] * 10 + want["col"]
    page.click(UNDO, force=True)
    undone = read(page)
    if undone["recorded"][index] != "unknown" or undone["counter"] != "0" or undone["hintStrokes"] != 0:
        problems.append(f"undo left the hint: cell {undone['recorded'][index]!r}, counter {undone['counter']!r}")
    page.click(REDO, force=True)
    redone = read(page)
    if redone["recorded"] != revealed["recorded"] or redone["counter"] != "1":
        problems.append(f"redo did not restore the hint: counter {redone['counter']!r}")
    if _module_js(page, "return S.hintCount(window.publicPlayer.getHistory());") != int(redone["counter"] or -1):
        problems.append("the counter is not the module's hintCount of the history")
    # Reset is a RECORDED stroke (play.js: record(history, resetStroke(...))), so the hint
    # stays on the undo stack and hintCount - which the admin's counter reads the same way -
    # still says 1 over the cleared board; undoing the Reset brings the board and the count back.
    page.click(RESET, force=True)
    cleared = read(page)
    module_count = _module_js(page, "return S.hintCount(window.publicPlayer.getHistory());")
    if cleared["recorded"] != ["unknown"] * 100 or module_count != 1 or cleared["counter"] != str(module_count):
        problems.append(f"after Reset the counter is {cleared['counter']!r} but the module's hintCount is {module_count}")
    page.click(UNDO, force=True)
    back = read(page)
    if back["recorded"] != revealed["recorded"] or back["counter"] != "1":
        problems.append(f"undoing Reset left counter {back['counter']!r} over a changed board")
    return problems


def sc_noop_undo(page, host, keys) -> list[str]:
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    press(page)
    before = read(page)
    page.click(REDO, force=True)
    page.click(UNDO, force=True)
    page.keyboard.press("Control+Shift+z")
    after = read(page)
    if (after["rung"], after["lit"], after["say"]) != (before["rung"], before["lit"], before["say"]):
        return ["a redo or undo with nothing to redo or undo reset the ladder"]
    return []


def sc_mid_drag(page, host, keys) -> list[str]:
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    before = read(page)
    page.mouse.move(*_cell_centre(page, 5, 0))
    page.mouse.down()
    page.mouse.move(*_cell_centre(page, 5, 1))
    page.mouse.move(*_cell_centre(page, 5, 2))
    page.evaluate("() => document.querySelector('[data-player-action=\"hint\"]').click()")
    mid = read(page)
    page.mouse.up()
    problems = []
    if (mid["rung"], mid["say"], mid["lit"]) != (before["rung"], "", []):
        problems.append(f"a press mid-drag did something: rung {mid['rung']}, {mid['say']!r}")
    end = read(page)
    if end["recorded"][50:53] != ["filled"] * 3:
        problems.append("the drag was not recorded")
    return problems


def sc_lit(page, host, keys) -> list[str]:
    problems: list[str] = []
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    press(page)
    first = read(page)["lit"]
    _tap(page, 9, 9)
    press(page)
    want = expected(page)
    second = read(page)["lit"]
    if not first or sorted(second) != line_parts(page, want["axis"], want["index"]):
        problems.append(f"after a change and a press {len(second)} parts are lit, not exactly the one line")
    return problems


def sc_hinted(page, host, keys) -> list[str]:
    problems: list[str] = []
    _board(page, host, keys["mixed"], CIRCLES_GRID, [])
    press_to_reveal(page)
    first = read(page)["hinted"]
    press_to_reveal(page)
    second = read(page)["hinted"]
    if len(first) != 1 or len(second) != 1 or first == second:
        problems.append(f"the hinted cell is {first} then {second}")
    _tap(page, 9, 9)
    if read(page)["hinted"] != []:
        problems.append("a change left the hinted cell outlined")
    return problems


def _other_storage(page, save_key: str) -> dict:
    """Every localStorage entry but the page's own save key."""
    return page.evaluate(
        "(own) => Object.fromEntries(Object.keys(localStorage).filter((k) => k !== own).map((k) => [k, localStorage.getItem(k)]))",
        save_key,
    )


def sc_save(page, host, keys) -> list[str]:
    problems: list[str] = []
    key = keys["mixed"]
    _board(page, host, key, CIRCLES_GRID, [])
    save_key = page.evaluate("() => window.publicPlayer.saveKey")
    others_before = _other_storage(page, save_key)
    press_to_reveal(page)
    # ADR-0041/R4: a hint writes the page's ONE save key and nothing else. The key
    # is asked of the page (publicPlayer.saveKey), and every other entry must be
    # exactly as it was, so a second key holding the board is a new or changed entry.
    if _other_storage(page, save_key) != others_before:
        problems.append(f"a hint wrote a localStorage entry other than {save_key!r}")
    page.reload()
    page.wait_for_function("window.publicPlayer !== undefined")
    after = read(page)
    if (after["hintStrokes"], after["counter"]) != (1, "1"):
        problems.append(f"a reload lost the hint: {after['hintStrokes']} hint strokes, counter {after['counter']!r}")
    save = json.loads(_save_strokes(key, CIRCLES_GRID, [("filled", [(0, 1)])]))
    save["done"][0]["hint"] = "yes"
    _prefill(page, host, key, json.dumps(save))
    if read(page)["recorded"] != ["unknown"] * 100:
        problems.append("a save whose hint flag is not true was accepted")
    return problems


def sc_full(page, host, keys) -> list[str]:
    grid = CIRCLES_GRID
    _board(page, host, keys["mixed"], grid, _marked(grid))
    before = read(page)
    press(page)
    after = read(page)
    problems = []
    if before["disabled"] != "true":
        problems.append("the control is enabled with no undecided cell left")
    if (after["say"], after["done"], after["rung"]) != ("", before["done"], before["rung"]):
        problems.append("a press with nothing to hint did something")
    return problems


def sc_corpus(page, host, keys) -> list[str]:
    _open(page, host, keys["mixed"])
    return corpus_problems(page, make_corpus(seed=7, count=48))


SCENARIOS = {
    "ladder": sc_ladder,
    "edges": sc_edges,
    "contradiction": sc_contradiction,
    "exhausted": sc_exhausted,
    "reset": sc_reset,
    "undo": sc_undo,
    "noop-undo": sc_noop_undo,
    "mid-drag": sc_mid_drag,
    "lit": sc_lit,
    "hinted": sc_hinted,
    "save": sc_save,
    "full": sc_full,
    "corpus": sc_corpus,
}


def run_scenarios(page, errors, host, keys, names=None, canary=None) -> dict[str, list[str]]:
    """Every scenario (or ``names``), each as {name: problems}; the page's uncaught
    exceptions are a problem of the scenario that provoked them."""
    results: dict[str, list[str]] = {}
    for name in names or SCENARIOS:
        errors.clear()
        try:
            problems = list(SCENARIOS[name](page, host, keys))
        except Exception as exc:  # noqa: BLE001 - a plant that breaks the page is a plant that fired
            problems = [f"the scenario could not finish: {type(exc).__name__}: {str(exc).splitlines()[0][:120]}"]
        if errors:
            problems.append(f"the page threw: {errors[0][:120]}")
        if canary is not None and page.evaluate("window.__served") != canary:
            problems.append("THE PLANT WAS NOT SERVED")
        results[name] = problems
    return results


def fired(results: dict[str, list[str]]) -> set[str]:
    return {name for name, problems in results.items() if problems}


@pytest.mark.browser
class TestPublicHint_TheScenariosAreGreenOnTheRealPage:
    def test_every_scenario_passes_and_none_is_skipped(self, plant_page, host) -> None:
        page, errors = plant_page
        results = run_scenarios(page, errors, host, host[2])
        assert set(results) == set(SCENARIOS) and len(results) >= 13
        assert {k: v for k, v in results.items() if v} == {}

    @pytest.mark.parametrize("name", list(SCENARIOS))
    def test_each_scenario_is_green_on_its_own_node(self, plant_page, host, name) -> None:
        """The umbrella above names no scenario when it reds; these do, one node each, so a
        plant that breaks exactly one thing moves exactly that thing's node id."""
        page, errors = plant_page
        assert run_scenarios(page, errors, host, host[2], names=[name])[name] == []

    def test_the_served_canary_mechanism_serves_an_unchanged_file(self, plant_page, host) -> None:
        page, errors = plant_page
        serve_planted(page, host, "play.js", [], "control")
        results = run_scenarios(page, errors, host, host[2], names=["ladder", "exhausted"], canary="control")
        assert {k: v for k, v in results.items() if v} == {}


class Plant:
    def __init__(self, ident: str, edits: list[tuple[str, str]], fires: set[str], why: str) -> None:
        self.ident, self.edits, self.fires, self.why = ident, edits, set(fires), why


_LOOPS = "  for (let row = 0; row < height; row += 1) {\n    for (let col = 0; col < width; col += 1) {\n      if (!isUndecided"
_REVEAL = "      commit(record(history, hintStroke(hint.row, hint.col, hint.state)));"
_EXHAUSTED_BRANCH = "      showHintLine(null);\n      say(HINT_EXHAUSTED);\n      return;\n    }"
_GUARD = "    if (gesture) return;\n    if (!canHint(history.board)) return;"
_DECIDES = "const decides = (forced, at) => forced !== null && forced[at] !== UNKNOWN;"

#: Every plant is an EDGE mutant of the hint code (the first or last line, a tie,
#: a wrong mark, the exhausted state, the ladder's reset, undo, the count, the
#: board the deduction reads) or the failure of one `!==` this card added. The
#: fired set is MEASURED: the scenarios that red, and no others.
PLANTS = [
    Plant("first-line-skipped", [(_LOOPS, _LOOPS.replace("let row = 0", "let row = 1"))], {"contradiction", "corpus", "edges", "ladder", "lit"}, "a hint on the first line"),
    Plant("last-line-skipped", [(_LOOPS, _LOOPS.replace("row < height", "row < height - 1"))], {"edges"}, "a hint on the last line"),
    Plant("last-column-skipped", [(_LOOPS, _LOOPS.replace("col < width", "col < width - 1"))], {"corpus", "edges", "ladder", "lit"}, "a hint in the last column"),
    Plant("first-column-skipped", [(_LOOPS, _LOOPS.replace("let col = 0", "let col = 1"))], {"edges", "corpus"}, "a hint in the first column"),
    Plant("a-column-wins-a-tie", [("      if (decides(rowForced[row], col)) {", "      if (decides(rowForced[row], col) && !decides(colForced[col], row)) {")], {"edges", "corpus"}, "a column line forcing a cell a row line also forces"),
    Plant("a-contradicted-line-forces-a-cell", [(_DECIDES, "const decides = (forced, at) => forced === null || forced[at] !== UNKNOWN;")], {"contradiction", "corpus"}, "a wrong mark that makes lineForced answer null"),
    Plant("a-null-line-decides-nothing-else-does-either", [("forced !== null && forced[at]", "forced === null && forced[at]")], {"contradiction", "corpus", "edges", "hinted", "ladder", "lit", "reset", "save", "undo"}, "!== null failed"),
    Plant("a-forced-cell-reads-as-undecided", [("forced[at] !== UNKNOWN;", "forced[at] === UNKNOWN;")], {"contradiction", "corpus", "edges", "exhausted", "hinted", "ladder", "lit", "save", "undo"}, "!== UNKNOWN failed"),
    Plant("the-exhausted-state-reveals-a-cell", [(_EXHAUSTED_BRANCH, "      showHintLine(null);\n      const first = history.board.cells.findIndex(isUndecided);\n      commit(record(history, hintStroke(Math.floor(first / payload.width), first % payload.width, FILLED)));\n      say(HINT_EXHAUSTED);\n      return;\n    }")], {"exhausted"}, "a fallback rung"),
    Plant("the-rung-does-not-reset-on-a-change", [("      setRung(nextRung(rung, \"change\"));\n      showHintLine(null);", "      showHintLine(null);")], {"ladder", "reset"}, "the rung survives a board change"),
    Plant("a-noop-undo-resets-the-ladder", [("    if (next !== history) {", "    if (next === history) {")], {"hinted", "ladder", "noop-undo", "reset"}, "next !== history failed"),
    Plant("undo-does-not-remove-a-hint", [("  actions.undo?.addEventListener(\"click\", () => commit(undo(history)));", "  actions.undo?.addEventListener(\"click\", () => commit(history.done.at(-1)?.stroke.hint === true ? history : undo(history)));")], {"undo"}, "undo leaves the hint"),
    Plant("the-count-is-a-variable-not-the-history", [("    hintsOut.textContent = String(hintCount(history));", "    hintsOut.textContent = String(globalThis.__n ?? 0);"), (_REVEAL, _REVEAL + "\n      globalThis.__n = (globalThis.__n ?? 0) + 1;")], {"ladder", "save", "undo"}, "the count read from a variable"),
    Plant("a-press-mid-drag-is-honoured", [(_GUARD, "    if (!canHint(history.board)) return;")], {"mid-drag"}, "no gesture guard"),
    Plant("the-deduction-reads-the-displayed-board", [(_GUARD, "    if (!canHint(history.board)) return;"), ("derivedHint(history.board, payload.rows, payload.columns);", "derivedHint(shown, payload.rows, payload.columns);")], {"mid-drag"}, "mid-drag, the displayed board"),
    Plant("rung-three-records-a-plain-stroke", [(_REVEAL, "      commit(record(history, { cells: [[hint.row, hint.col]], state: hint.state }));")], {"contradiction", "ladder", "save", "undo"}, "a hint that is not a hint stroke"),
    Plant("rung-three-ignores-the-derived-state", [("hintStroke(hint.row, hint.col, hint.state)", "hintStroke(hint.row, hint.col, FILLED)")], {"contradiction", "edges"}, "the state read from somewhere else"),
    Plant("rung-one-names-the-wrong-axis", [("`Hint: look at ${line.axis} ${line.index + 1}.`", "`Hint: look at row ${line.index + 1}.`")], {"ladder", "edges", "contradiction"}, "an axis that is not the line's"),
    Plant("a-press-does-not-climb", [("    setRung(nextRung(rung, \"press\"));", "    setRung(rung);")], {"contradiction", "edges", "hinted", "ladder", "reset", "save", "undo"}, "the ladder does not follow nextRung"),
    Plant("the-line-is-never-lit", [("    if (hintLine !== null) paintHintLine(table, hintLine, true);", "    if (hintLine === null) paintHintLine(table, hintLine, true);")], {"contradiction", "edges", "exhausted", "hinted", "ladder", "lit", "mid-drag", "reset", "save", "undo"}, "!== null failed (light)"),
    Plant("the-old-line-is-never-unlit", [("    if (hintLine !== null) paintHintLine(table, hintLine, false);\n", "")], {"ladder", "reset"}, "!== null failed (unlight)"),
    Plant("the-hinted-cell-is-never-outlined", [("    if (hinted !== null) markHinted(cells[hinted[0] * payload.width + hinted[1]], true);", "    if (hinted === null) markHinted(cells[hinted[0] * payload.width + hinted[1]], true);")], {"contradiction", "edges", "hinted", "ladder", "lit", "mid-drag", "reset", "save", "undo"}, "!== null failed (outline)"),
    Plant("the-old-outline-is-never-removed", [("    if (hinted !== null) markHinted(cells[hinted[0] * payload.width + hinted[1]], false);\n", "")], {"hinted"}, "!== null failed (remove)"),
    Plant("a-save-with-any-flag-is-accepted", [("if (Object.hasOwn(saved, \"hint\") && saved.hint !== true) return null;", "if (false) return null;")], {"save"}, "saved.hint !== true failed"),
    Plant("a-save-forgets-the-hint-flag", [("  ...(stroke.hint === true ? { hint: true } : {}),\n", "")], {"save"}, "the flag is not saved"),
    Plant("a-full-board-can-be-hinted", [("    if (!canHint(history.board)) return;\n    lastClick = null;", "    lastClick = null;")], {"full"}, "nothing to hint, pressed anyway"),
    Plant("the-control-is-never-disabled", [("    setDisabled(actions.hint, !canHint(history.board));", "    setDisabled(actions.hint, false);")], {"full"}, "aria-disabled"),
    Plant("a-run-may-touch-the-next-black-cell", [("return at + run === n || cells[at + run] !== FILLED;", "return at + run === n || cells[at + run] === FILLED;")], {"corpus", "edges", "exhausted", "ladder", "lit"}, "!== FILLED failed (separator)"),
    Plant("a-black-cell-may-be-left-blank-backward", [("const blank = cells[i] !== FILLED && rest[i + 1][j];", "const blank = cells[i] === FILLED && rest[i + 1][j];")], {"contradiction", "corpus", "edges"}, "!== FILLED failed (backward)"),
    Plant("a-black-cell-may-be-left-blank-forward", [("if (cells[i] !== FILLED && rest[i + 1][j]) {", "if (cells[i] === FILLED && rest[i + 1][j]) {")], {"contradiction", "corpus", "edges", "exhausted", "ladder", "lit"}, "!== FILLED failed (forward)"),
    Plant("the-reveal-never-happens", [("    if (hint !== null && rung === RUNG_REVEAL) {", "    if (hint === null && rung === RUNG_REVEAL) {")], {"contradiction", "edges", "exhausted", "hinted", "ladder", "save", "undo"}, "hint !== null failed"),
    Plant("a-hint-also-writes-a-second-storage-key", [(_REVEAL, _REVEAL + "\n      localStorage.setItem('leak', JSON.stringify(history.board.cells));")], {"save"}, "a second key holding the board (ADR-0041/R4)"),
    Plant("the-counter-reads-zero-after-reset", [("    hintsOut.textContent = String(hintCount(history));", "    hintsOut.textContent = String(history.board.cells.every((s) => s === UNKNOWN) ? 0 : hintCount(history));")], {"undo"}, "the counter is not the undo stack's hintCount over a cleared board"),
    Plant("the-counter-is-never-written", [("    hintsOut.textContent = String(hintCount(history));", "")], {"ladder", "undo", "save"}, "no count"),
]


#: The lines of play.js at the cut (9ef90933) that carry a `!==`. CARRIED, not derived: they
#: are the cut's own and every one is in a function this card did not write; a line that is
#: not here is one the card added, and must be the subject of a plant above.
CARRIED_NEQ_LINES = frozenset({
    'const majorAfter = (index, count) => (index + 1) % MAJOR_EVERY === 0 && index + 1 !== count;',
    'const repeat = lastClick !== null && lastClick.row === row',
    'const segments = String(path).split("/").filter((segment) => segment !== "");',
    'if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z") return;',
    'if (!Array.isArray(columns) || columns.length !== width) return null;',
    'if (!Array.isArray(rows) || rows.length !== height) return null;',
    'if (!gesture || event.pointerId !== gesture.pointerId) return;',
    'if (JSON.stringify(data.columns) !== JSON.stringify(payload.columns)) return null;',
    'if (JSON.stringify(data.rows) !== JSON.stringify(payload.rows)) return null;',
    'if (clues === null || typeof clues !== "object") return null;',
    'if (crossed !== null && isAt(position, crossed) && isPainted(crossed)) return;',
    'if (crossed !== null) paint(crossed, false);',
    'if (data === null || typeof data !== "object" || Array.isArray(data)) return null;',
    'if (data.key !== key || !Number.isInteger(width) || !Number.isInteger(height)) return null;',
    'if (data.v !== SAVE_VERSION || data.key !== payload.key) return null;',
    'if (data.width !== payload.width || data.height !== payload.height) return null;',
    'if (gesture || (event.pointerType === "mouse" && event.button !== 0)) return;',
    'if (payload.tier !== "") {',
    'if (position !== null) moveTo(position);',
    'if (saved === null || typeof saved !== "object" || Array.isArray(saved)) return null;',
    'if (touchStartCell.get(firstId) !== null) {',
    'if (typeof document !== "undefined") load();',
    'if (width < 1 || height < 1 || typeof data.tier !== "string") return null;',
    'if (zoom !== old) {',
    'pinch !== null && (event.pointerId === pinch.firstId || event.pointerId === pinch.secondId);',
    'return last !== undefined && KEY.test(last) ? last : null;',
    'return stage.querySelector(`td.player-cell.is-crossed[data-row="${row}"][data-col="${col}"]`) !== null;',
})


def test_every_neq_this_card_added_has_a_plant_that_fails_it() -> None:
    """Every `!==` / `!=` on a line the card added to play.js is the subject of a plant."""
    source = PLAY_JS.read_text(encoding="utf-8")
    lines = [line.strip() for line in source.splitlines() if ("!==" in line or "!=" in line) and not line.lstrip().startswith("//")]
    added = [line for line in lines if line not in CARRIED_NEQ_LINES]
    olds = " ".join(old for plant in PLANTS for old, _ in plant.edits)
    comparisons = [c for line in added for c in re.findall(r"[\w.\[\]]+ (?:!==|!=) [\w.]+", line)]
    assert len(comparisons) >= 12, comparisons
    uncovered = [c for c in comparisons if c not in olds]
    assert uncovered == [], uncovered
    assert len(lines) - len(added) >= 20, "the carried lines are no longer in the file: the census reads nothing"


def test_the_neq_census_notices_a_comparison_with_no_plant() -> None:
    """The control for the census: a new `!==` with no plant is uncovered."""
    olds = " ".join(old for plant in PLANTS for old, _ in plant.edits)
    assert "run] !== FILLED" in olds and "zzz !== null" not in olds


@pytest.mark.browser
class TestPublicHint_EachPlantFiresTheScenarioItIsAbout:
    @pytest.mark.parametrize("plant", PLANTS, ids=[p.ident for p in PLANTS])
    def test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green(self, plant_page, host, plant) -> None:
        page, errors = plant_page
        # the matched control, in this very run: the scenarios the plant is
        # about, on the unplanted page
        about = sorted(plant.fires)
        control = run_scenarios(page, errors, host, host[2], names=about)
        assert {k: v for k, v in control.items() if v} == {}, ("the matched control", plant.ident)
        assert len(control) == len(about) >= 1
        serve_planted(page, host, "play.js", plant.edits, plant.ident)
        results = run_scenarios(page, errors, host, host[2], canary=plant.ident)
        assert all("THE PLANT WAS NOT SERVED" not in p for ps in results.values() for p in ps), "the plant was not served"
        assert len(results) == len(SCENARIOS), "a scenario was skipped"
        assert fired(results) == plant.fires, f"FIRED {plant.ident} {json.dumps(sorted(fired(results)))}"

    def test_there_are_plants_for_every_edge_the_card_names(self) -> None:
        ids = {p.ident for p in PLANTS}
        for needed in (
            "first-line-skipped", "last-line-skipped", "a-column-wins-a-tie", "a-contradicted-line-forces-a-cell",
            "the-exhausted-state-reveals-a-cell", "the-rung-does-not-reset-on-a-change", "undo-does-not-remove-a-hint",
            "the-count-is-a-variable-not-the-history", "the-deduction-reads-the-displayed-board",
        ):
            assert needed in ids, needed
        assert len(PLANTS) >= 25


# ==========================================================================
# AC-9 - the control is OUTSIDE the toolbar
# ==========================================================================

#: The toolbar's buttons as the cut (9ef90933) had them, by the attribute that names each.
#: CARRIED, not derived: "exactly what it was before this card" is a statement about the
#: cut, and the cut's toolbar is this list (4 brushes, Region, 3 history, 2 zoom).
TOOLBAR_BUTTONS = sorted(
    [f'data-player-tool="{t}"' for t in ("filled", "empty", "maybe", "unknown")]
    + ["data-player-region", 'data-player-action="undo"', 'data-player-action="redo"', 'data-player-action="reset"']
    + ['data-player-zoom-action="out"', 'data-player-zoom-action="in"']
)

_TOOLBAR_FACTS = """() => {
  const bar = document.querySelector('.player-toolbar');
  const hint = document.querySelector('[data-player-action="hint"]');
  const stage = document.querySelector('[data-player-stage]');
  const usage = document.querySelector('[data-player-hint]');
  const hintBar = document.querySelector('[data-player-hint-bar]');
  const buttons = [...bar.querySelectorAll('button')].map((b) =>
    b.getAttributeNames().filter((n) => n.startsWith('data-player-') && n !== 'data-player-rung')
      .map((n) => (b.getAttribute(n) === '' ? n : n + '="' + b.getAttribute(n) + '"')).sort()[0]);
  const box = hint.getBoundingClientRect();
  const before = (a, b) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
  return {
    inToolbar: bar.contains(hint), closestToolbar: hint.closest('.player-toolbar') !== null,
    barInToolbar: bar.contains(hintBar), buttons: buttons.sort(), toolbarChildren: bar.querySelectorAll('button').length,
    width: box.width, height: box.height, fontSize: parseFloat(getComputedStyle(hint).fontSize),
    afterStage: before(stage, hintBar), beforeUsage: before(hintBar, usage),
    hintBarHidden: hintBar.hidden,
  };
}"""


def toolbar_problems(page) -> list[str]:
    facts = page.evaluate(_TOOLBAR_FACTS)
    problems: list[str] = []
    if facts["inToolbar"] or facts["closestToolbar"] or facts["barInToolbar"]:
        problems.append("the Hint control is inside .player-toolbar")
    if facts["buttons"] != TOOLBAR_BUTTONS:
        problems.append(f"the toolbar's button set changed: {facts['buttons']}")
    if facts["height"] < 44 or facts["width"] < 44:
        problems.append(f"the control is {facts['width']} x {facts['height']} px, under the 44 px touch floor")
    if not (facts["afterStage"] and facts["beforeUsage"]):
        problems.append("the control is not under the board and beside the usage paragraph")
    if facts["hintBarHidden"]:
        problems.append("the control is hidden after the board is drawn")
    return problems


@pytest.mark.browser
class TestPublicHint_TheControlIsOutsideTheToolbar:
    def test_the_control_is_under_the_board_44px_and_the_toolbar_is_what_it_was(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["mixed"])
        assert toolbar_problems(page) == []

    def test_the_markup_agrees_before_a_script_runs(self) -> None:
        html = PLAY_HTML.read_text(encoding="utf-8")
        toolbar = html[html.index('<div class="player-toolbar"') : html.index("</div>\n\n  <div class=\"player-stage\"")]
        assert 'data-player-action="hint"' not in toolbar and "player-hint-bar" not in toolbar
        assert html.index("data-player-stage") < html.index("data-player-hint-bar") < html.index('<p class="player-hint"')
        assert len(re.findall(r"<button", toolbar)) == len(TOOLBAR_BUTTONS)
        # the control is hidden until the board is drawn, like the toolbar, and says so in its own markup
        assert re.search(r"<div class=\"player-hint-bar\"[^>]*\bhidden\b", html)

    def test_a_toolbar_button_added_or_the_control_moved_into_it_is_refused(self, plant_page, host) -> None:
        page, _ = plant_page
        _open(page, host, host[2]["mixed"])
        assert toolbar_problems(page) == [], "the matched control"
        page.evaluate(
            """() => {
              const hint = document.querySelector('[data-player-action="hint"]');
              document.querySelector('.player-toolbar').append(hint);
            }"""
        )
        found = toolbar_problems(page)
        assert any("inside .player-toolbar" in p for p in found) and any("button set changed" in p for p in found), found

    def test_the_control_is_reachable_and_legible_at_the_zoom_maximum_and_a_scrolled_offset(self, browser_page, host) -> None:
        page = browser_page
        page.set_viewport_size(PHONE)
        _board(page, host, host[2]["max"], FIXTURES["max"], [])
        bounds = _bounds(page)
        while _percent(page) < bounds["max"]:
            _press(page, "in")
        assert _percent(page) == bounds["max"]
        _settle(page)
        for scroll in (0, 120, 100000):
            page.evaluate("(y) => window.scrollTo(0, y)", scroll)
            _settle(page)
            facts = page.evaluate(_TOOLBAR_FACTS)
            assert facts["fontSize"] >= 14 and facts["width"] >= 44 and facts["height"] >= 44, facts
            # a real click, with Playwright's own actionability checks: visible, stable, and
            # receiving the event (not covered by a sticky gutter or the toolbar)
            before = read(page)["rung"]
            page.click(HINT)
            after = read(page)
            assert after["rung"] != before or after["done"] == 1, (scroll, before, after["rung"])
            assert after["say"] != ""
            spot = page.evaluate(
                """() => {
                  const b = document.querySelector('[data-player-action="hint"]');
                  const r = b.getBoundingClientRect();
                  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  const say = document.querySelector('[data-player-hint-say]');
                  const s = say.getBoundingClientRect();
                  return { onIt: at === b || b.contains(at), right: Math.max(r.right, s.right), width: innerWidth,
                           clipped: say.scrollWidth > say.clientWidth || say.scrollHeight > say.clientHeight };
                }"""
            )
            assert spot["onIt"] and spot["right"] <= spot["width"] and not spot["clipped"], (scroll, spot)
            page.click(UNDO, force=True)  # whatever the press did, leave the board as it was

    @pytest.mark.parametrize("viewport", [{"width": 320, "height": 568}, PHONE, {"width": 844, "height": 390}, {"width": 1440, "height": 900}],
                             ids=["320", "phone", "landscape", "desktop"])
    def test_a_rung_two_sentence_is_whole_and_in_the_viewport_at_every_width(self, browser_page, host, viewport) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _board(page, host, host[2]["max"], FIXTURES["max"], [])
        press(page)
        press(page)
        _settle(page)
        say = page.evaluate(
            """() => { const s = document.querySelector('[data-player-hint-say]'); const r = s.getBoundingClientRect();
              return { text: s.textContent, left: r.left, right: r.right, width: innerWidth, h: r.height, scrollH: s.scrollHeight, clientH: s.clientHeight }; }"""
        )
        assert " — " in say["text"] and say["left"] >= 0 and say["right"] <= say["width"], say
        assert say["scrollH"] <= say["clientH"] + 1, say


#: The zoom module pins that the space BELOW the stage is smaller than the stage's offset
#: from the top (tests/test_public_player_zoom.py, over a grid of viewports, with the page
#: at rest), because a page that scrolls further than that carries the stage's top off the
#: screen and makes ``keepCluesInView``'s reading over-state what is visible. The hint bar
#: adds a 44 px row and one --space-3 below the stage, and the sentence a press says wraps on
#: a phone. So while a sentence shows, play.js HIDES the usage paragraph (the longer of the
#: two at every width), and this holds the premise over the zoom module's own grid with the
#: sentence showing. DECLARED BOUND (ADR-0039/R3): the least margin (stage offset minus space
#: below, px) over that grid, MEASURED this card on the 30 x 30 board, 2026-11-06, with the
#: sentence showing, is WORST_MARGIN_PX; it is positive, which is the premise. Past the bound:
#: the control that leaves the usage paragraph showing under the sentence (what the page
#: would do without the swap) violates the premise on VIOLATIONS_WITHOUT_THE_SWAP viewports.
WORST_MARGIN_PX = 54  # MEASURED 2026-11-06
VIOLATIONS_WITHOUT_THE_SWAP = 84  # MEASURED 2026-11-06, of 170 viewports


def sentence_margins(page, host, *, keep_usage: bool = False, pad: int = 0) -> dict[tuple[int, int], int]:
    """(width, height) -> stage-top-offset minus space-below, with a rung-2 sentence showing.

    ``keep_usage`` shows the usage paragraph again under the sentence (the control);
    ``pad`` appends that many characters to the sentence so it wraps further.
    """
    page.set_viewport_size(PHONE)
    _board(page, host, host[2]["max"], FIXTURES["max"], [])
    press(page)
    press(page)
    page.evaluate(
        "([keep, pad]) => { const s = document.querySelector('[data-player-hint-say]'); s.textContent += ' x'.repeat(pad);"
        " if (keep) document.querySelector('[data-player-hint]').hidden = false; }",
        [keep_usage, pad],
    )
    out: dict[tuple[int, int], int] = {}
    for height in range(SHORTEST, TALLEST + 1, 70):
        for width in range(NARROWEST, WIDEST + 1, 40):
            page.set_viewport_size({"width": width, "height": height})
            _settle(page)
            r = page.evaluate(_GEOMETRY)
            out[(width, height)] = r["innerTop"] - (r["docHeight"] - r["docBottom"])
    return out


@pytest.mark.browser
class TestPublicHint_TheSentenceBelowTheBoardKeepsTheZoomModulesPremise:
    def test_with_a_sentence_showing_the_space_below_stays_smaller_than_the_top(self, browser_page, host) -> None:
        margins = sentence_margins(browser_page, host)
        assert len(margins) >= 150
        assert min(margins.values()) == WORST_MARGIN_PX > 0, (min(margins.values()), sorted(k for k, v in margins.items() if v <= 0))

    def test_without_the_swap_the_premise_fails_on_a_measured_number_of_viewports(self, browser_page, host) -> None:
        """The control: the same sentence with the usage paragraph left showing."""
        margins = sentence_margins(browser_page, host, keep_usage=True)
        assert sum(1 for v in margins.values() if v <= 0) == VIOLATIONS_WITHOUT_THE_SWAP > 0

    def test_a_sentence_far_longer_than_any_the_page_says_goes_past_the_bound(self, browser_page, host) -> None:
        margins = sentence_margins(browser_page, host, pad=200)
        assert min(margins.values()) < WORST_MARGIN_PX and any(v <= 0 for v in margins.values())

    def test_the_usage_paragraph_comes_back_with_the_next_change(self, browser_page, host) -> None:
        page = browser_page
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, [])
        assert page.is_visible("[data-player-hint]")
        press(page)
        assert not page.is_visible("[data-player-hint]") and page.is_visible("[data-player-hint-say]")
        _tap(page, 9, 9)
        assert page.is_visible("[data-player-hint]") and not page.is_visible("[data-player-hint-say]")


# ==========================================================================
# AC-10 - the hint highlight is distinct from the crosshair and from a circle
# ==========================================================================
#
# Three marks share the clue boxes and the board: the crosshair's tint
# (``is-crossed``, CARD-325), a circled number's ring (``is-circled``, CARD-326,
# a BORDER on the number's ::before) and this card's hint line
# (``is-hint-line``). They must coexist: a line that is hinted, crossed AND
# circled shows all three. The panel lets the hint win outright where the two
# tints meet (the crosshair vanishes on the lit line); this page shows a 50/50
# mix of the two tints instead, a declared difference
# (tests/test_public_player_agreement.py, DECLARED_HINT_DIVERGENCES) whose
# measured distances are held HERE, in pixels.

#: The least distance (max channel difference, 0-255) between the clue box's ground
#: in any two of the four states (plain, crossed, hinted, hinted AND crossed) that
#: this card treats as "distinguishable". MEASURED, 2026-11-06, in headless Chromium
#: on the 10 x 10 mixed fixture: TINT_DISTANCES_MEASURED below, the smallest being 10
#: (the crosshair's own tint against the plain box, CARD-325's figure, and the blend
#: against each pure tint, which is half the distance between them by construction).
#: The floor is 8 BECAUSE the panel's own hint tint (--color-accent-tint) measures 6
#: from this page's crosshair on the same box: the plant below that restores it is
#: the control that fails just past the bound, and the agreement module declares the
#: stronger tint as a divergence with this reason.
TINT_FLOOR = 8
#: pair -> distance, the figures the floor was set from
TINT_DISTANCES_MEASURED = {
    ("plain", "crossed"): 10,
    ("plain", "hinted"): 24,
    ("plain", "both"): 14,
    ("crossed", "hinted"): 20,
    ("crossed", "both"): 10,
    ("hinted", "both"): 10,
}


def three_mark_board(page, host) -> tuple[int, list]:
    """A board on the mixed fixture whose hinted line is row R (R >= 1), whose clue box has a
    CIRCLED number, found by search over R with the module as the judge of both facts."""
    for r in range(1, 10):
        unique_closed = [
            ("empty", [(a, b) for a in range(r) for b in range(10) if not CIRCLES_GRID[a][b]]),
            ("filled", [(a, b) for a in range(r) for b in range(10) if CIRCLES_GRID[a][b]]),
        ]
        run_cells = [(r, b) for b in range(10) if CIRCLES_GRID[r][b]]
        closers = [(r, b) for b in range(10) if not CIRCLES_GRID[r][b] and any(abs(b - c) == 1 for _, c in run_cells)]
        strokes = [s for s in unique_closed if s[1]] + [("filled", run_cells[:1]), ("empty", closers[:2])]
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, strokes)
        want = expected(page)
        circled = page.evaluate(
            f"() => document.querySelectorAll('th.player-clue.is-row[data-line=\"{r}\"] .player-clue-num.is-circled').length"
        )
        if want is not None and (want["axis"], want["index"]) == ("row", r) and circled:
            return r, strokes
    raise AssertionError("no row of the fixture is hinted and has a circled number")


def ground(page, selector: str) -> tuple[int, int, int]:
    """The pixel an element shows at its top-left corner, inset past the rule."""
    page.wait_for_function("document.getAnimations().every((a) => a.playState !== 'running')")
    box = page.query_selector(selector).bounding_box()
    return _pixels(page, box["x"] + 3, box["y"] + 3, 1, 1).getpixel((0, 0))


def four_grounds(page, host) -> dict[str, tuple[int, int, int]]:
    r, _ = three_mark_board(page, host)
    box = f"th.player-clue.is-row[data-line='{r}']"
    out = {}
    page.mouse.move(2, 2)
    out["plain"] = ground(page, box)
    _move(page, r, 5)
    out["crossed"] = ground(page, box)
    page.mouse.move(2, 2)
    press(page)
    out["hinted"] = ground(page, box)
    _move(page, r, 5)
    out["both"] = ground(page, box)
    return out


def tint_problems(page, host, floor: int = TINT_FLOOR) -> list[str]:
    grounds = four_grounds(page, host)
    problems = []
    for one, other in itertools.combinations(grounds, 2):
        if _distance(grounds[one], grounds[other]) < floor:
            problems.append(f"{one} and {other} are {_distance(grounds[one], grounds[other])} apart (floor {floor})")
    return problems


def ring_problems(page, host) -> list[str]:
    r, _ = three_mark_board(page, host)
    press(page)
    _move(page, r, 5)
    ring = page.evaluate(_RING, f"th.player-clue.is-row.is-crossed.is-hint-line")
    if not ring["found"]:
        return ["vacuous: the hinted, crossed box has no circled number"]
    problems = [
        f"the ring is not ink at its {edge} edge ({distance} away)"
        for edge, distance in _ring_edge_distances(page, ring).items()
        if distance > 40
    ]
    classes = page.evaluate(f"() => [...document.querySelector(\"th.player-clue.is-row[data-line='{r}']\").classList]")
    if not {"is-crossed", "is-hint-line"} <= set(classes):
        problems.append(f"the box does not carry both marks: {classes}")
    return problems


@pytest.mark.browser
class TestPublicHint_ThreeMarksCoexist:
    def test_the_four_states_of_a_clue_box_are_pairwise_distinguishable(self, browser_page, host) -> None:
        assert tint_problems(browser_page, host) == []

    def test_the_measured_distances_are_the_ones_the_floor_was_set_from(self, browser_page, host) -> None:
        grounds = four_grounds(browser_page, host)
        measured = {pair: _distance(grounds[pair[0]], grounds[pair[1]]) for pair in TINT_DISTANCES_MEASURED}
        assert measured == TINT_DISTANCES_MEASURED, "MEASURED " + json.dumps({"|".join(k): v for k, v in measured.items()})
        assert min(measured.values()) >= TINT_FLOOR

    def test_a_hinted_crossed_and_circled_box_shows_all_three(self, browser_page, host) -> None:
        page = browser_page
        assert ring_problems(page, host) == []
        grounds = four_grounds(page, host)
        assert _distance(grounds["both"], grounds["hinted"]) >= TINT_FLOOR and _distance(grounds["both"], grounds["crossed"]) >= TINT_FLOOR

    def test_a_hinted_line_keeps_a_filled_a_white_and_a_blank_cell_apart(self, browser_page, host) -> None:
        """The tint is a background, so the marks on a lit line are still told apart: the
        centre pixel of a black cell, of a white one (its dot) and of a blank one (the tint)."""
        page = browser_page
        r, _ = three_mark_board(page, host)
        press(page)
        assert sorted(read(page)["lit"]) == line_parts(page, "row", r)
        states = page.evaluate(
            f"() => [...document.querySelectorAll('td.player-cell[data-row=\"{r}\"]')].map((c) => c.dataset.state)"
        )
        assert {"filled", "empty", "unknown"} <= set(states), states
        corner, centre = {}, {}
        page.wait_for_function("document.getAnimations().every((a) => a.playState !== 'running')")
        for state in ("filled", "empty", "unknown"):
            box = page.query_selector(f"td.player-cell[data-row='{r}'][data-col='{states.index(state)}']").bounding_box()
            corner[state] = _pixels(page, box["x"] + 4, box["y"] + 4, 1, 1).getpixel((0, 0))
            centre[state] = _pixels(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, 1, 1).getpixel((0, 0))
        assert _distance(corner["filled"], corner["unknown"]) > 100, corner
        assert corner["empty"] == corner["unknown"], "a lit white and a lit blank cell share the tint"
        assert _distance(centre["empty"], corner["empty"]) > 40, "the white mark's dot is not visible on a lit line"
        assert centre["unknown"] == corner["unknown"], "a blank cell on a lit line has a mark"

    def test_a_maybe_cell_on_a_lit_line_keeps_its_glyph_and_the_tint_is_not_the_maybe_ground(self, browser_page, host) -> None:
        """G-9: the hint highlight stays distinct from CARD-323's Maybe cell. On a lit line the
        tint replaces the Maybe cell's ground (the later rule wins), so what keeps it a Maybe
        cell is its ``?`` glyph: the cell holds pixels that are not the tint, and a blank cell
        beside it holds none. The tint is also nowhere near the Maybe ground itself."""
        page = browser_page
        r, strokes = three_mark_board(page, host)
        blank = [c for c in range(10) if cells_after(CIRCLES_GRID, strokes)[r * 10 + c] == "unknown"]
        assert blank, "the scenario is vacuous: no blank cell on the row"
        _board(page, host, host[2]["mixed"], CIRCLES_GRID, [*strokes, ("maybe", [(r, blank[0])])])
        press(page)
        assert sorted(read(page)["lit"]) == line_parts(page, "row", r)
        page.wait_for_function("document.getAnimations().every((a) => a.playState !== 'running')")
        distinct = {}
        for name, col in (("maybe", blank[0]), ("blank", blank[1])):
            box = page.query_selector(f"td.player-cell[data-row='{r}'][data-col='{col}']").bounding_box()
            distinct[name] = len(_pixels(page, box["x"] + 3, box["y"] + 3, box["width"] - 6, box["height"] - 6).getcolors(100000) or [])
        assert distinct["blank"] == 1, distinct
        assert distinct["maybe"] > 1, distinct
        maybe_ground = page.evaluate(
            "() => { const p = document.createElement('i'); p.style.background = 'var(--color-surface-hover)'; document.body.append(p);"
            " const c = getComputedStyle(p).backgroundColor; p.remove(); return c; }"
        )
        tint = _pixels(page, *[v for v in (lambda b: (b["x"] + 3, b["y"] + 3))(page.query_selector(f"td.player-cell[data-row='{r}'][data-col='{blank[1]}']").bounding_box())], 1, 1).getpixel((0, 0))
        assert _distance(tint, _rgb(maybe_ground)) >= TINT_FLOOR, (tint, maybe_ground)

    @pytest.mark.parametrize(
        ("label", "css"),
        [
            ("the-hint-tint-is-the-crosshairs", ".player-stage { --player-hint-line: var(--player-cross); }"),
            ("the-hint-tint-is-nearly-the-crosshairs", ".player-stage { --player-hint-line: color-mix(in srgb, var(--player-cross) 97%, var(--color-accent-tint)); }"),
            ("the-hint-tint-is-the-panels-own-and-6-levels-from-the-crosshair", ".player-stage { --player-hint-line: var(--color-accent-tint); }"),
            ("the-blend-is-the-crosshairs", ".player-clue.is-hint-line.is-crossed { background: var(--player-cross); }"),
            ("the-blend-is-the-hint", ".player-clue.is-hint-line.is-crossed { background: var(--player-hint-line); }"),
        ],
    )
    def test_a_tint_that_is_not_distinct_is_caught(self, plant_page, host, label, css) -> None:
        page, _ = plant_page
        assert tint_problems(page, host) == [], "the matched control"
        text = (host[1].site_dir / "player.css").read_text(encoding="utf-8")
        page.route("**/player.css", lambda route: route.fulfill(status=200, body=text + "\n" + css, content_type="text/css"))
        found = tint_problems(page, host)
        assert found, label

    @pytest.mark.parametrize(
        "css",
        [
            ".player-clue.is-hint-line .player-clue-num::before { border-color: transparent; }",
            ".player-clue.is-hint-line.is-crossed .player-clue-num::before { clip-path: inset(0 50% 0 0); }",
            ".player-clue.is-hint-line.is-crossed .player-clue-num { visibility: hidden; }",
            '.player-clue.is-hint-line::after { content: ""; position: absolute; inset: 0; background: var(--player-hint-line); }',
        ],
        ids=["ring-cleared", "right-half-clipped", "number-hidden", "tint-is-an-overlay-above-the-ring"],
    )
    def test_a_highlight_that_can_hide_the_ring_is_caught(self, plant_page, host, css) -> None:
        page, _ = plant_page
        assert ring_problems(page, host) == [], "the matched control"
        text = (host[1].site_dir / "player.css").read_text(encoding="utf-8")
        page.route("**/player.css", lambda route: route.fulfill(status=200, body=text + "\n" + css, content_type="text/css"))
        assert ring_problems(page, host) != []

    def test_every_value_of_the_hint_rules_is_a_token_or_a_token_only_expression(self) -> None:
        css = PLAYER_CSS.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        rules = [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", code) if re.search(r"is-hint-line|is-hinted|--player-hint-line", sel + body)]
        assert len(rules) >= 8, [sel for sel, _ in rules]
        tokens = set(re.findall(r"(--[a-z0-9-]+)\s*:", (SOLVER_STATE.parent / "tokens.css").read_text(encoding="utf-8")))
        own = set(re.findall(r"(--player-[a-z-]+)\s*:", code))
        for selector, body in rules:
            for value in re.findall(r":\s*([^;]+);?", body):
                assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(|\b(?:red|green|blue|white|black|grey|gray)\b(?!-)", value), (selector, value)
                for name in re.findall(r"var\((--[a-z0-9-]+)\)", value):
                    assert name in tokens | own, (selector, name)
                assert not re.search(r"\d+(?:\.\d+)?(?:px|rem|em)\b", value.replace("calc(", "(")) or "calc(" in value or "var(" in value, (selector, value)
        # and a literal planted into the hint block is refused by the same reading
        planted = code + "\n.player-clue.is-hint-line.is-crossed { background: #e6efec; }"
        assert re.search(r"#[0-9a-fA-F]{3,8}\b", planted)


# ==========================================================================
# GAP 4 - the highlight and the control at the zoom maximum and at a scrolled offset
# ==========================================================================


def bring_lit_cell_into_view(page) -> None:
    """Scroll the stage to its top and centre a middle lit cell horizontally: the lit line of
    the blank 30 x 30 board is its first row, which sits just under the pinned column band, so
    ``scrollIntoView`` (which ignores sticky offsets) would put it behind that band."""
    page.evaluate(
        """() => {
          const stage = document.querySelector('[data-player-stage]');
          const lit = [...document.querySelectorAll('td.player-cell.is-hint-line')];
          const r = lit[Math.floor(lit.length / 2)].getBoundingClientRect();
          const box = stage.getBoundingClientRect();
          stage.scrollTop = 0;
          stage.scrollLeft += (r.left + r.width / 2) - (box.left + box.width / 2);
        }"""
    )
    _settle(page)


def lit_visible_ground(page) -> tuple[int, int, int] | None:
    """The ground of a lit cell that is really on screen, in the stage's view and
    not behind a sticky gutter; None when no lit cell is in view."""
    found = page.evaluate(
        """() => {
          const stage = document.querySelector('[data-player-stage]').getBoundingClientRect();
          for (const el of document.querySelectorAll('td.player-cell.is-hint-line')) {
            const r = el.getBoundingClientRect();
            const x = r.left + r.width * 0.8, y = r.top + r.height * 0.8;
            if (x > stage.left && x < stage.right && y > stage.top && y < stage.bottom && document.elementFromPoint(x, y) === el) {
              return [x, y];
            }
          }
          return null;
        }"""
    )
    if found is None:
        return None
    page.wait_for_function("document.getAnimations().every((a) => a.playState !== 'running')")
    return _pixels(page, found[0], found[1], 1, 1).getpixel((0, 0))


@pytest.mark.browser
class TestPublicHint_StayLegibleAndInPlaceWhenZoomedAndScrolled:
    def test_the_lit_line_and_the_outlined_cell_survive_zoom_and_scroll(self, browser_page, host) -> None:
        page = browser_page
        page.set_viewport_size(PHONE)
        _board(page, host, host[2]["max"], FIXTURES["max"], [])
        press(page)
        lit = read(page)["lit"]
        want = expected(page)
        assert sorted(lit) == line_parts(page, want["axis"], want["index"]) and len(lit) == 31
        bounds = _bounds(page)
        # the panel's own tint, read from a lit cell at 100%: what every later reading must equal
        bring_lit_cell_into_view(page)
        reference = lit_visible_ground(page)
        assert reference is not None, "no lit cell is visible at 100%"
        seen = 0
        while _percent(page) < bounds["max"]:
            _press(page, "in")
            assert sorted(read(page)["lit"]) == sorted(lit), "zoom changed what is lit"
            assert read(page)["rung"] == 2, "zoom is a view change, not a recorded one: the ladder stays"
            bring_lit_cell_into_view(page)
            _settle(page)
            tint = lit_visible_ground(page)
            assert tint is not None, f"no lit cell can be brought into view at {_percent(page)}%"
            assert _distance(tint, reference) <= 4, (_percent(page), tint, reference)
            seen += 1
            for fraction in (0.0, 0.5, 1.0):
                page.evaluate(
                    "(f) => { const s = document.querySelector('[data-player-stage]');"
                    " s.scrollLeft = (s.scrollWidth - s.clientWidth) * f; s.scrollTop = (s.scrollHeight - s.clientHeight) * f; }",
                    fraction,
                )
                _settle(page)
                tint = lit_visible_ground(page)
                if tint is not None:
                    seen += 1
                    assert _distance(tint, reference) <= 4, (_percent(page), fraction, tint, reference)
        assert seen >= 8, f"only {seen} readings had a lit cell in view: the check is vacuous"
        # rung 3 at the maximum: the hinted cell keeps its outline when only the zoom moves
        press(page)
        press(page)
        outlined = read(page)["hinted"]
        assert len(outlined) == 1
        _press(page, "out")
        assert read(page)["hinted"] == outlined
        page.evaluate("() => window.scrollTo(0, 100000)")
        assert read(page)["hinted"] == outlined and read(page)["say"] != ""


# ==========================================================================
# GAP 3 - the listener census
# ==========================================================================
#
# tests/test_public_player.py::test_every_player_control_is_in_the_ec_050_walk
# censuses every ``addEventListener`` type play.js registers and reds on any
# addition. The Hint control is one more ``click`` handler on one more
# ``data-player-action`` button, so that census needed a SCOPE+ edit (the
# action set and the walk's table gain "hint"; the click count was already
# derived from the markup and moves by itself). The census is re-derived
# below as a function so the claim is a test: it reds without the edit
# (against the markup it would have counted), and still reds on a sixth listener.


def listener_census(script: str, html: str) -> tuple[list[str], list[str]]:
    """(registered listener types in play.js, the types the markup says it should have)."""
    actions = set(re.findall(r'data-player-action="([a-z]+)"', html))
    zoom = set(re.findall(r'data-player-zoom-action="([a-z]+)"', html))
    registered = sorted(re.findall(r'addEventListener\("([a-z]+)"', script))
    crosshair = re.search(r"\nfunction wireCrosshair\(stage\) \{.*?\n\}\n", script, re.S)
    assert crosshair is not None
    crosshair_events = sorted(re.findall(r'addEventListener\("([a-z]+)"', crosshair.group(0)))
    viewport = re.findall(r'window\.addEventListener\("([a-z]+)", (\w+)\)', script)
    want = sorted(
        ["pointerdown", "pointermove", "pointerup", "pointercancel", "keydown"]
        + crosshair_events
        + [kind for kind, _ in viewport]
        + ["click"] * (2 + len(actions) + len(zoom))
    )
    return registered, want


class TestPublicHint_TheListenerCensus:
    def test_the_hint_is_one_click_listener_and_the_census_balances(self) -> None:
        registered, want = listener_census(PLAY_JS.read_text(encoding="utf-8"), PLAY_HTML.read_text(encoding="utf-8"))
        assert registered == want
        assert registered.count("click") == 2 + 4 + 2, "the tools, Region, four action buttons (undo, redo, reset, hint), two zoom buttons"

    def test_a_sixth_listener_reds_it(self) -> None:
        script, html = PLAY_JS.read_text(encoding="utf-8"), PLAY_HTML.read_text(encoding="utf-8")
        registered, want = listener_census(script, html)
        assert registered == want, "the matched control"
        for planted in (
            script.replace("  controls.hidden = false;\n", '  document.addEventListener("click", () => {});\n  controls.hidden = false;\n', 1),
            script.replace("  controls.hidden = false;\n", '  hintBar.addEventListener("click", () => {});\n  controls.hidden = false;\n', 1),
            script.replace("  controls.hidden = false;\n", '  document.addEventListener("focusin", () => {});\n  controls.hidden = false;\n', 1),
        ):
            assert planted != script
            planted_registered, planted_want = listener_census(planted, html)
            assert planted_registered != planted_want

    def test_a_hint_button_without_its_listener_or_a_listener_without_its_button_reds_it(self) -> None:
        script, html = PLAY_JS.read_text(encoding="utf-8"), PLAY_HTML.read_text(encoding="utf-8")
        no_button = html.replace('data-player-action="hint"', 'data-player-hint-button')
        registered, want = listener_census(script, no_button)
        assert registered != want, "the markup lost the button and the census did not notice"
        no_listener = script.replace('  actions.hint?.addEventListener("click", () => {', '  const unused = (() => {', 1)
        registered, want = listener_census(no_listener, html)
        assert registered != want
