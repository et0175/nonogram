"""CARD-326 - circled clue numbers on the public player: the clue readout that needs no answer.

CARD-188 gave the admin player circled clue numbers: a clue number is circled
once the player's marks account for it. ``solver_state.js`` exports
``circledNumbers(clue, cells)`` and ``circledClues(board, rows, columns)``;
neither takes a solution, the served copy is byte-identical to the admin's
(ADR-0041/R3), and until this card ``play.js`` imported neither. This card is
wiring, not porting: the page recomputes the circle set from the RECORDED board
every time ``refresh()`` runs (the repaint every stroke, undo, redo and reset
already goes through) and toggles ``.is-circled`` on the clue numbers.

The trap, and where it is held (AC-4)
-------------------------------------
Circling a number and satisfying a clue are DIFFERENT predicates.
``play.js``'s header says so and is right: ``circledNumbers`` circles under
three rules, two of which fire on marks that satisfy no clue. So the page's
solved check stays ``isClueSolved``, untouched, and AC-4 holds it with a board
this card CONSTRUCTED because no existing fixture has one (measured by
:meth:`TestPublicCircles_CirclesAreNotTheSolvedCheck.test_no_existing_fixture_has_the_extra_cell_board`):
a solution fully marked plus ONE extra black cell. Every clue number of it is
circled, the board is not solved, and a solved check built from the circle set
would declare victory on it.

Where each claim is answered
----------------------------
Browser tests (``@pytest.mark.browser``) drive the real page and compare what it
paints with ``circledClues``'s own return value, evaluated in the page from the
page's own served ``/solver_state.js`` (never a Python transcription, never a
list spelled into a test). Tree tests read ``player/`` off disk. Behavioural
plants rewrite the SERVED copy of ``play.js`` / ``player.css`` inside the
test's own temporary site (never the source tree), each beside its matched
control in the same test.

The four gaps the card's premise note named, and the test that closes each
-------------------------------------------------------------------------
#. a crossed AND circled clue box shows both:
   ``TestPublicCircles_ACrossedClueStillShowsItsCircle``;
#. the circles' look is held to the admin's:
   ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCirclesAreTheSameLook``
   (SCOPE+: that file is not in the card's Touches);
#. the listener census: this card adds NO listener, so
   ``tests/test_public_player.py::test_every_player_control_is_in_the_ec_050_walk``
   runs unedited (and ``TestPublicCircles_ThePredicateIsTheModules`` refuses a
   listener inside the circle code);
#. zoom: ``TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled``.

Tests, by node id (FR-045, CARD-326's ACs)
------------------------------------------
Written out in full, one per line, because the architecture validator resolves a
check ref by a TEXT search for the whole ``path::name`` string.

* AC-1 - ``tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers``
* AC-2 - ``tests/test_public_player_circles.py::TestPublicCircles_TheyFollowUndoRedoAndReset``
* AC-3 - ``tests/test_public_player_circles.py::TestPublicCircles_ThePredicateIsTheModules``
* AC-4 - ``tests/test_public_player_circles.py::TestPublicCircles_CirclesAreNotTheSolvedCheck``
* AC-5 - ``tests/test_public_player_circles.py::TestPublicCircles_NoAnswerAndNoRequest``
"""

from __future__ import annotations

import io
import random
import re
from pathlib import Path

import pytest

from nonogram.solver import solve
from tests.test_public_player import (  # noqa: F401 - fixtures used by name
    GRIDS,
    PLAYER_DIR,
    _drag,
    _cell_centre,
    _filled_cells,
    _open,
    _prefill,
    _save,
    _state,
    _tap,
    browser_type,
    host,
    site,
    write_bundle,
)
from tests.test_public_player_crosshair import (  # noqa: F401
    _matching,
    _raw_definition,
    _scan,
    browser_page,
    definition,
    free_references,
    _move,
    _assert_crossed_at,
)
from tests.test_public_player_zoom import (  # noqa: F401
    LANDSCAPE,
    PHONE,
    _bounds,
    _module,
    _percent,
    _press,
)
from tests.test_puzzle_solver_page import _encode, _unique_grid

PLAY_JS = PLAYER_DIR / "play.js"
PLAYER_CSS = PLAYER_DIR / "player.css"

# --------------------------------------------------------------------------
# This card's own fixtures
# --------------------------------------------------------------------------

#: A 10 x 10 puzzle of this card's own, found by seeded search (seed 3 of a
#: density sweep) because AC-4 needs a board where EVERY clue number is
#: circled and the board is not solved, and none of the four ``GRIDS``
#: fixtures has one (measured by
#: ``test_no_existing_fixture_has_the_extra_cell_board``). Uniquely solvable,
#: re-checked against the real solver by ``test_the_fixtures_are_uniquely_solvable``.
CIRCLES_ROWS = (
    ".#.......#",
    "...#.##.##",
    ".#.#..#..#",
    ".#...###.#",
    "...#...###",
    ".##...#..#",
    "...##...##",
    ".####..#..",
    ".#####...#",
    "#..###.#.#",
)
CIRCLES_GRID = [[ch == "#" for ch in row] for row in CIRCLES_ROWS]

#: Cells of ``CIRCLES_GRID`` that are white in the solution and which, once
#: marked black ON TOP OF the fully marked solution, leave every clue number
#: circled (found with the module, listed so the test can assert the module
#: still agrees: ``test_the_constructed_board_is_what_the_card_says``).
EXTRA_CELLS = ((0, 4), (0, 7), (1, 0), (4, 0), (6, 0))

#: A 10 x 10 whose first and last rows are EMPTY: a ``[0]`` clue on the first
#: and on the last line, which ``circledNumbers`` circles only when every cell
#: of the line is white.
BLANK_EDGES = _unique_grid(10, 10, seed=326, empty_rows={0, 9})


@pytest.fixture
def bundle(tmp_path):
    """Shadows the shared ``bundle``: the shared four puzzles plus this card's two.

    A module-level fixture of the same name overrides an imported one for this
    module only; every key the shared fixtures serve is still served.
    """
    root = tmp_path / "bundle"
    return root, write_bundle(root, {**GRIDS, "circles": CIRCLES_GRID, "blank-edges": BLANK_EDGES})


# --------------------------------------------------------------------------
# Reading the page and the module
# --------------------------------------------------------------------------

_READ_CIRCLES = """() => {
  const read = (kind) => {
    const lines = [];
    for (const box of document.querySelectorAll(`th.player-clue.is-${kind}`)) {
      lines[Number(box.dataset.line)] =
        [...box.querySelectorAll('.player-clue-num')].map((n) => n.classList.contains('is-circled'));
    }
    return lines;
  };
  return { rows: read('row'), columns: read('col') };
}"""

# circledClues of the RECORDED board, from the page's own served module.
_MODULE_CIRCLES = """async () => {
  const S = await import('/solver_state.js');
  const p = window.publicPlayer;
  const c = S.circledClues(p.getHistory().board, p.payload.rows, p.payload.columns);
  return { rows: c.rows.map((l) => [...l]), columns: c.columns.map((l) => [...l]) };
}"""

# circledClues of the DISPLAYED board (mid-drag preview included).
_MODULE_CIRCLES_SHOWN = _MODULE_CIRCLES.replace("p.getHistory().board", "p.getBoard()")


def _dom(page) -> dict:
    return page.evaluate(_READ_CIRCLES)


def _want(page) -> dict:
    return page.evaluate(_MODULE_CIRCLES)


def _count(circles: dict) -> int:
    return sum(sum(line) for axis in ("rows", "columns") for line in circles[axis])


def _total(circles: dict) -> int:
    return sum(len(line) for axis in ("rows", "columns") for line in circles[axis])


def _differences(dom: dict, want: dict) -> list[tuple[str, int, int]]:
    return [
        (axis, line, k)
        for axis in ("rows", "columns")
        for line, flags in enumerate(want[axis])
        for k, flag in enumerate(flags)
        if dom[axis][line][k] != flag
    ]


def _mismatch(page, label: str) -> list[str]:
    """``[]`` when the page paints exactly ``circledClues(recorded board)``."""
    dom, want = _dom(page), _want(page)
    assert _total(dom) == _total(want), "the page and the module disagree on how many numbers there are"
    wrong = _differences(dom, want)
    return [f"{label}: {len(wrong)} numbers differ from circledClues, first {wrong[:3]}"] if wrong else []


def _save_strokes(key: str, grid, strokes) -> str:
    """The page's own resume format with several strokes (``tests.test_public_player._save``'s shape)."""
    import json

    return json.dumps(
        {
            "v": 1,
            "key": key,
            "width": len(grid[0]),
            "height": len(grid),
            "rows": [_encode(row) for row in grid],
            "columns": [_encode(column) for column in zip(*grid)],
            "done": [{"cells": [[r, c] for r, c in cells], "state": state} for state, cells in strokes],
            "undone": [],
        }
    )


def _marked(grid, rows=None, extra=()):
    """Strokes marking ``rows`` of ``grid`` fully (black where the solution is, white elsewhere),
    plus ``extra`` cells black on top."""
    rows = range(len(grid)) if rows is None else rows
    black = [(r, c) for r in rows for c in range(len(grid[0])) if grid[r][c]]
    white = [(r, c) for r in rows for c in range(len(grid[0])) if not grid[r][c]]
    strokes = [("empty", white), ("filled", black + [tuple(cell) for cell in extra])]
    return [stroke for stroke in strokes if stroke[1]]


def _board(page, host, key, grid, strokes) -> None:
    _prefill(page, host, key, _save_strokes(key, grid, strokes))


def _site_file(host, name: str) -> Path:
    return host[1].site_dir / name


def _plant(page, host, name: str, old: str, new: str) -> None:
    """Serve ``name`` with ``old`` replaced by ``new`` to ``page``, from now on.

    By ROUTE, not by rewriting the file: a route fulfils every request for the
    name itself (and Playwright switches the HTTP cache off while a route is
    active), so a file the control run already fetched cannot be served stale
    to the plant's run. Measured the hard way: rewriting the served file and
    switching the cache off through a CDP session both let plants go unserved
    at random, and an unserved plant reads as "not caught" for the wrong
    reason. The source tree and the temporary site are never touched.
    """
    served = _site_file(host, name)
    text = served.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"the plant must apply exactly once to {name}: {old!r} ({text.count(old)})"
    planted = text.replace(old, new)
    kind = "text/javascript" if name.endswith(".js") else "text/css"
    page.route(f"**/{name}", lambda route: route.fulfill(status=200, body=planted, content_type=kind))


def _click(page, selector: str) -> None:
    page.click(selector, force=True)


UNDO = '[data-player-action="undo"]'
REDO = '[data-player-action="redo"]'
RESET = '[data-player-action="reset"]'
FILLED_BRUSH = '[data-player-tool="filled"]'
EMPTY_BRUSH = '[data-player-tool="empty"]'


# --------------------------------------------------------------------------
# The scenarios: each returns the list of ways the page disagreed with the module
# --------------------------------------------------------------------------


def walk_problems(page, host, keys) -> list[str]:
    """Load, mark a row by clicks, undo, redo, key-undo, reset, undo the reset."""
    key, grid = keys["circles"], CIRCLES_GRID
    problems: list[str] = []
    _board(page, host, key, grid, _marked(grid, rows=range(5)))
    problems += _mismatch(page, "load")
    if _count(_dom(page)) == 0:
        problems.append("vacuous: the loaded board circles nothing")
    # Complete row 5 by clicks, white cells first so the LAST click (black) is
    # the one that closes the row and changes the circle set.
    _click(page, EMPTY_BRUSH)
    for col in (0, 3, 4, 5, 7, 8):
        _tap(page, 5, col)
    _click(page, FILLED_BRUSH)
    for col in (1, 2, 6):
        _tap(page, 5, col)
    problems += _mismatch(page, "row 5 one cell short")
    before = _count(_dom(page))
    _tap(page, 5, 9)
    problems += _mismatch(page, "row 5 complete")
    after = _count(_dom(page))
    if after <= before:
        problems.append(f"vacuous: closing row 5 circled nothing new ({before} -> {after})")
    _click(page, UNDO)
    problems += _mismatch(page, "undo")
    if _count(_dom(page)) != before:
        problems.append("undo did not take the closing click's circles back")
    _click(page, REDO)
    problems += _mismatch(page, "redo")
    page.keyboard.press("Control+z")
    problems += _mismatch(page, "ctrl-z")
    page.keyboard.press("Control+Shift+z")
    problems += _mismatch(page, "ctrl-shift-z")
    _click(page, RESET)
    problems += _mismatch(page, "reset")
    if _count(_dom(page)) != 0:
        problems.append(f"reset left {_count(_dom(page))} numbers circled")
    _click(page, UNDO)
    problems += _mismatch(page, "undo of the reset")
    if _count(_dom(page)) == 0:
        problems.append("undoing the reset brought no circle back")
    return problems


def mid_drag_problems(page, host, keys) -> list[str]:
    """The circles come from the RECORDED board, never from a drag's preview."""
    key, grid = keys["circles"], CIRCLES_GRID
    problems: list[str] = []
    # Every row marked except row 7, whose white cells are marked and whose
    # black cells are left undecided.
    strokes = _marked(grid, rows=[r for r in range(10) if r != 7])
    strokes.append(("empty", [(7, c) for c in range(10) if not grid[7][c]]))
    _board(page, host, key, grid, strokes)
    problems += _mismatch(page, "before the drag")
    recorded = _dom(page)
    _click(page, FILLED_BRUSH)
    cells = [(7, 1), (7, 2), (7, 3), (7, 4)]
    page.mouse.move(*_cell_centre(page, *cells[0]))
    page.mouse.down()
    for cell in cells[1:]:
        page.mouse.move(*_cell_centre(page, *cell))
    shown = page.evaluate(_MODULE_CIRCLES_SHOWN)
    if _differences(recorded, shown) == []:
        problems.append("vacuous: the preview circles exactly what the record does")
    problems += _mismatch(page, "mid-drag")
    page.mouse.up()
    problems += _mismatch(page, "after the drag")
    if _count(_dom(page)) <= _count(recorded):
        problems.append("the committed drag circled nothing new")
    return problems


def edge_problems(page, host, keys) -> list[str]:
    """First and last lines, a repeated number circled one at a time, a [0] clue."""
    key, grid = keys["circles"], CIRCLES_GRID
    problems: list[str] = []
    # The whole solution: every number, including row 0 / the last row and
    # column 0 / the last column, is circled.
    _board(page, host, key, grid, _marked(grid))
    problems += _mismatch(page, "solution")
    dom = _dom(page)
    if _count(dom) != _total(dom):
        problems.append("the fully marked solution did not circle every number")
    # Row 0 is clued [1, 1]. Marking only its first 1 (black, closed by white
    # cells) circles that number and not its twin of the same value.
    _board(page, host, key, grid, [("filled", [(0, 1)]), ("empty", [(0, 0), (0, 2)])])
    problems += _mismatch(page, "a repeated number")
    if _dom(page)["rows"][0] != [True, False]:
        problems.append(f"vacuous: row 0 was meant to circle [1st, not 2nd], got {_dom(page)['rows'][0]}")
    # The last row's first number alone: right edge.
    _board(page, host, key, grid, [("filled", [(9, 9)]), ("empty", [(9, 8)])])
    problems += _mismatch(page, "the last number of the last row")
    if _dom(page)["rows"][9][-1] is not True:
        problems.append("vacuous: the last number of the last row was meant to be circled")
    # [0] clues on the first and the last line.
    blank = keys["blank-edges"]
    both = [(0, c) for c in range(10)] + [(9, c) for c in range(10)]
    _board(page, host, blank, BLANK_EDGES, [("empty", both)])
    problems += _mismatch(page, "blank edges")
    dom = _dom(page)
    if not (dom["rows"][0] == [True] and dom["rows"][9] == [True]):
        problems.append(f"vacuous: [0] clues were meant to circle: {dom['rows'][0]} {dom['rows'][9]}")
    return problems


def circle_problems(page, host, keys) -> list[str]:
    return walk_problems(page, host, keys) + mid_drag_problems(page, host, keys) + edge_problems(page, host, keys)


# ==========================================================================
# AC-1 - the marks circle the numbers
# ==========================================================================


@pytest.mark.browser
class TestPublicCircles_TheMarksCircleTheNumbers:
    """AC-1. The expected set is ``circledClues``'s return value, evaluated in the page."""

    def test_a_blank_board_circles_nothing(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["circles"])
        assert _count(_dom(page)) == 0
        assert _mismatch(page, "blank") == []

    @pytest.mark.parametrize("name", ["min", "cycle2-144", "oblong", "max", "circles"])
    def test_a_fully_marked_solution_circles_every_number(self, browser_page, host, name) -> None:
        page = browser_page
        grids = {**GRIDS, "circles": CIRCLES_GRID}
        _board(page, host, host[2][name], grids[name], _marked(grids[name]))
        dom = _dom(page)
        assert _mismatch(page, name) == []
        assert _total(dom) > 0 and _count(dom) == _total(dom)

    def test_the_numbers_the_marks_account_for_are_circled_and_the_rest_are_not(self, browser_page, host) -> None:
        """Five rows marked: some numbers circle, some do not, and the page
        agrees with the module on each of them (both counts are asserted
        non-zero, so an all-or-nothing page cannot satisfy this)."""
        page = browser_page
        key = host[2]["circles"]
        _board(page, host, key, CIRCLES_GRID, _marked(CIRCLES_GRID, rows=range(5)))
        dom, want = _dom(page), _want(page)
        assert _differences(dom, want) == []
        assert 0 < _count(dom) < _total(dom), (_count(dom), _total(dom))
        circled_rows = [flags for flags in dom["rows"][:5]]
        assert all(all(flags) for flags in circled_rows), "a fully marked row circles all its numbers"
        assert not any(any(flags) for flags in dom["rows"][5:]), "a row with no mark circles nothing"

    def test_a_number_repeated_in_a_clue_circles_one_at_a_time(self, browser_page, host) -> None:
        page = browser_page
        key = host[2]["circles"]
        _board(page, host, key, CIRCLES_GRID, [("filled", [(0, 1)]), ("empty", [(0, 0), (0, 2)])])
        assert _dom(page)["rows"][0] == [True, False]
        assert _mismatch(page, "repeat") == []

    def test_the_blank_line_clue_is_circled_only_when_every_cell_is_white(self, browser_page, host) -> None:
        page = browser_page
        key = host[2]["blank-edges"]
        _board(page, host, key, BLANK_EDGES, [("empty", [(0, c) for c in range(9)])])
        assert _dom(page)["rows"][0] == [False]
        _board(page, host, key, BLANK_EDGES, [("empty", [(0, c) for c in range(10)])])
        assert _dom(page)["rows"][0] == [True]
        assert page.evaluate("() => document.querySelector('th.is-row[data-line=\"0\"] .player-clue-num').textContent") == "0"
        assert _mismatch(page, "blank row") == []

    def test_the_fixtures_are_uniquely_solvable(self) -> None:
        """CON-005 / INV-002, for the two fixtures this card adds."""
        for grid in (CIRCLES_GRID, BLANK_EDGES):
            rows = tuple(tuple(_encode(row)) for row in grid)
            columns = tuple(tuple(_encode(column)) for column in zip(*grid))
            assert solve(rows, columns).solution_count == 1


# ==========================================================================
# AC-2 - the circles follow the history
# ==========================================================================

#: The hook line in ``refresh()`` and the toggle line in ``paintCircles``: the
#: two places every behavioural plant below rewrites, copied from ``play.js``
#: verbatim and asserted to occur exactly once by ``_plant``.
HOOK = "    paintCircles(clueNumbers, circledClues(history.board, payload.rows, payload.columns));"
TOGGLE = '        span.classList.toggle("is-circled", circled[axis][line][k]);'

#: ``(id, old, new)``: each plant breaks ONE way the circles can stop following
#: the record. The edge cases are the card's: a circle that survives undo, a
#: circle left after reset, the preview read in place of the record, the circle
#: drawn on the wrong axis's clue, the first line skipped, the last line
#: skipped, a repeated number circled by its VALUE rather than its place, and a
#: toggle with no force (which flips instead of setting).
#: Each plant's fourth field is the text the FIRST scenario that must notice it
#: puts in its problem: the plant test asserts a problem containing it, not just
#: "some problem" (a plant caught by the wrong scenario would be a vacuous scenario).
CIRCLE_PLANTS = [
    (
        "survives-undo",
        HOOK,
        "    if (history.undone.length === 0) paintCircles(clueNumbers, circledClues(history.board, payload.rows, payload.columns));",
        "undo",
    ),
    (
        "left-after-reset",
        HOOK,
        "    if (history.board.cells.some((state) => state !== UNKNOWN)) paintCircles(clueNumbers, circledClues(history.board, payload.rows, payload.columns));",
        "reset",
    ),
    (
        "preview-not-record",
        HOOK,
        "    paintCircles(clueNumbers, circledClues(shown, payload.rows, payload.columns));",
        "mid-drag",
    ),
    (
        "wrong-axis",
        TOGGLE,
        '        span.classList.toggle("is-circled", circled[axis === "rows" ? "columns" : "rows"][line][k]);',
        "differ from circledClues",
    ),
    (
        "first-line-skipped",
        TOGGLE,
        '        if (line > 0) span.classList.toggle("is-circled", circled[axis][line][k]);',
        "differ from circledClues",
    ),
    (
        "last-line-skipped",
        TOGGLE,
        '        if (line < clueNumbers[axis].length - 1) span.classList.toggle("is-circled", circled[axis][line][k]);',
        "differ from circledClues",
    ),
    (
        "repeat-by-value",
        TOGGLE,
        '        span.classList.toggle("is-circled", circled[axis][line][spans.findIndex((s) => s.textContent === span.textContent)]);',
        "differ from circledClues",
    ),
    (
        "toggle-without-force",
        TOGGLE,
        '        if (circled[axis][line][k]) span.classList.toggle("is-circled");',
        "differ from circledClues",
    ),
]


@pytest.mark.browser
class TestPublicCircles_TheyFollowUndoRedoAndReset:
    """AC-2. At every step the page's set is ``circledClues`` of the recorded board."""

    def test_every_step_of_a_stroke_undo_redo_reset_walk_equals_the_module(self, browser_page, host) -> None:
        assert walk_problems(browser_page, host, host[2]) == []

    def test_a_drag_in_progress_leaves_the_circles_on_the_record(self, browser_page, host) -> None:
        assert mid_drag_problems(browser_page, host, host[2]) == []

    def test_the_edges_a_repeat_and_a_blank_clue_equal_the_module(self, browser_page, host) -> None:
        assert edge_problems(browser_page, host, host[2]) == []

    @pytest.mark.parametrize(("name", "old", "new", "expect"), CIRCLE_PLANTS, ids=[p[0] for p in CIRCLE_PLANTS])
    def test_a_planted_defect_is_caught_and_the_unplanted_page_is_clean(self, browser_page, host, name, old, new, expect) -> None:
        """The matched control first (the shipped page, this same test, no
        problem), then ONE plant into the served ``play.js``; the same scenarios
        must now report a disagreement with the module."""
        page = browser_page
        assert circle_problems(page, host, host[2]) == [], "the matched control"
        _plant(page, host, "play.js", old, new)
        planted = circle_problems(page, host, host[2])
        assert planted != [], f"plant {name} was not caught"
        assert any(expect in problem for problem in planted), f"plant {name} was caught, but not by the scenario that owns it ({expect!r}): {planted}"


# ==========================================================================
# AC-3 - the predicate is the module's
# ==========================================================================
#
# A claim that play.js "contains no second rule" is a claim about SOURCE TEXT,
# so it is answered by reading it, DEFAULT-DENY (ADR-0039/R2) on identifiers,
# on PROPERTY reads and on computed member access, which is the lesson of
# CARD-325's first scanner (it denied by identifier only, and its reviewer
# planted seven bypasses). The circle code is two small functions, so the
# allowlist is the whole vocabulary they may use: any token outside it is
# refused, including every operator, so there is no comparison, no condition
# and no arithmetic in which a second rule could live.

_TOKEN = re.compile(
    r'"[^"\n]*"|\'[^\'\n]*\'|`[^`]*`|[A-Za-z_$][\w$]*|\d+(?:\.\d+)?|=>|===|!==|==|!=|<=|>=|&&|\|\||\?\?|\.\.\.|[^\s\w]'
)
_IDENT = re.compile(r"^[A-Za-z_$][\w$]*$")


class _Vocabulary:
    """What one function may say: identifiers, properties, strings, punctuation,
    and the exact index expressions a computed member may hold."""

    def __init__(self, identifiers, properties, strings, punctuation, indexes, chains=None) -> None:
        self.identifiers = frozenset(identifiers)
        self.properties = frozenset(properties)
        self.strings = frozenset(strings)
        self.punctuation = frozenset(punctuation)
        self.indexes = tuple(indexes)
        #: ``{base identifier: the ORDERED index chain it may be read through}``.
        self.chains = dict(chains or {})


PAINT_VOCABULARY = _Vocabulary(
    identifiers={"function", "paintCircles", "clueNumbers", "circled", "for", "const", "of", "axis", "line", "k", "spans", "span"},
    properties={"forEach", "classList", "toggle"},
    strings={'"rows"', '"columns"', '"is-circled"'},
    punctuation={"(", ")", "{", "}", "[", "]", ",", ";", ".", "=>"},
    indexes=[("axis",), ("line",), ("k",)],
    chains={"circled": ["axis", "line", "k"], "clueNumbers": ["axis"]},
)

COLLECT_VOCABULARY = _Vocabulary(
    identifiers={"function", "clueNumbersOf", "table", "axis", "kind", "lines", "box", "const", "for", "of", "return",
                 "rows", "columns", "Number"},
    properties={"querySelectorAll", "dataset", "line"},
    strings={'"row"', '"col"', '".player-clue-num"', "`th.player-clue.is-${kind}`"},
    punctuation={"(", ")", "{", "}", "[", "]", ",", ";", ".", "=>", "=", ":", "..."},
    indexes=[("Number", "(", "box", ".", "dataset", ".", "line", ")")],
)


def vocabulary_violations(name: str, body: str, vocabulary: _Vocabulary) -> list[str]:
    tokens = _TOKEN.findall(body)
    problems: list[str] = []
    for position, token in enumerate(tokens):
        previous = tokens[position - 1] if position else ""
        if token[0] in "\"'`":
            if token not in vocabulary.strings:
                problems.append(f"{name}: string {token}")
        elif _IDENT.match(token):
            if previous == ".":
                if token not in vocabulary.properties:
                    problems.append(f"{name}: property .{token}")
            elif token not in vocabulary.identifiers:
                problems.append(f"{name}: identifier {token}")
        elif token[0].isdigit():
            problems.append(f"{name}: number {token}")
        elif token not in vocabulary.punctuation:
            problems.append(f"{name}: token {token!r}")
        if token == "[":
            member = bool(previous) and (_IDENT.match(previous) is not None and previous not in {"of"} or previous in {"]", ")"})
            if member:
                inside = []
                depth = 0
                for follower in tokens[position + 1 :]:
                    if follower == "[":
                        depth += 1
                    if follower == "]":
                        if depth == 0:
                            break
                        depth -= 1
                    inside.append(follower)
                if tuple(inside) not in vocabulary.indexes:
                    problems.append(f"{name}: computed member [{' '.join(inside)}]")
    problems += _comma_and_chain_violations(name, tokens, vocabulary)
    return problems


def _comma_and_chain_violations(name: str, tokens: list[str], vocabulary: _Vocabulary) -> list[str]:
    """A comma is a separator (call arguments, parameters, the one array
    literal) or it is the comma OPERATOR, which evaluates its left side and
    discards it: a second rule that ``(a, b)`` hides. And an index chain is read
    in its ORDER: ``circled[axis][line][k]`` and no permutation of it."""
    problems: list[str] = []
    stack: list[int] = []
    for position, token in enumerate(tokens):
        if token in "([{":
            stack.append(position)
        elif token in ")]}":
            opened = stack.pop()
            if token == ")" and tokens[opened] == "(":
                # Remember whether this paren group is an arrow's parameter list.
                if position + 1 < len(tokens) and tokens[position + 1] == "=>":
                    tokens[opened] = "(=>"
    stack = []
    for position, token in enumerate(tokens):
        if token in ("(", "(=>", "[", "{"):
            stack.append(position)
        elif token in (")", "]", "}"):
            stack.pop()
        elif token == "," and stack:
            opened = stack[-1]
            before = tokens[opened - 1] if opened else ""
            call = tokens[opened] == "(" and (_IDENT.match(before) is not None and before not in {"of", "return"} or before in {")", "]"})
            parameters = tokens[opened] == "(=>"
            literal = (tokens[opened] == "[" and before == "of") or (tokens[opened] == "{" and before == "return")
            if not (call or parameters or literal):
                problems.append(f"{name}: comma operator")
    for base, expected in vocabulary.chains.items():
        for position, token in enumerate(tokens):
            if token != base or (position and tokens[position - 1] == "."):
                continue
            chain: list[str] = []
            at = position + 1
            while at < len(tokens) and tokens[at] == "[":
                chain.append(tokens[at + 1])
                at += 3
            if position + 1 < len(tokens) and tokens[position + 1] == "[" and chain != expected:
                problems.append(f"{name}: {base} read through chain {chain}, expected {expected}")
    return problems


def circle_code_violations(js_source: str) -> list[str]:
    """Every way the circle code (painter, collector, hook) says what it must not."""
    problems: list[str] = []
    for name, vocabulary in (("paintCircles", PAINT_VOCABULARY), ("clueNumbersOf", COLLECT_VOCABULARY)):
        raw = _raw_definition(js_source, name)
        if raw is None:
            problems.append(f"{name}: not defined")
        else:
            problems += vocabulary_violations(name, raw, vocabulary)
    comment_free, _ = _scan(js_source)
    if len(re.findall(r"\bcircledClues\b", comment_free)) != 2:
        problems.append("circledClues: must be named exactly twice in code (the import and the one call)")
    if re.search(r"\bcircledNumbers\b", comment_free):
        problems.append("circledNumbers: the per-line form is not used")
    if not re.search(r'import\s*\{[^}]*\bcircledClues\b[^}]*\}\s*from\s*"/solver_state\.js"', js_source):
        problems.append("circledClues: not imported from /solver_state.js")
    refresh = _nested_definition(js_source, "refresh") or ""
    if "paintCircles(clueNumbers, circledClues(history.board, payload.rows, payload.columns));" not in refresh:
        problems.append("refresh: does not paint circledClues of the recorded board")
    painters = re.findall(r"(?m)^(?:export\s+)?(?:function|const)\s+(\w*[Cc]ircle\w*)", comment_free)
    if painters != ["paintCircles"]:
        problems.append(f"a second circle definition: {painters}")
    if _without_comments(js_source).count("is-circled") != 1:
        problems.append("is-circled: must be named exactly once in code (any quote kind, any function), as the painter's string")
    return problems


def _without_comments(js_source: str) -> str:
    """``js_source`` with its comments removed and every string KEPT (a rule in
    a single-quoted or template string is still a rule)."""
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


def _nested_definition(js_source: str, name: str) -> str | None:
    """``function name(...) { ... }`` declared at any indent (``refresh`` lives inside ``start``)."""
    code, _ = _scan(js_source)
    head = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", code)
    if head is None:
        return None
    # The same brace count over the comment-free text that still has its strings.
    stripped = re.sub(r"(?m)//[^\n]*$", "", js_source)
    start = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", stripped)
    assert start is not None
    open_at = stripped.index("{", stripped.index(")", start.end()))
    return stripped[start.start() : _matching(stripped, open_at, "{", "}") + 1]


#: What ``isClueSolved`` may use that it did not declare itself: its own two
#: helpers, ``Array``, and the destructured / property names it reads off the
#: board. ``circledClues``, ``paintCircles`` and anything else is refused.
SOLVED_ALLOWED = frozenset({"sameNumbers", "runsOf", "Array", "export", "width", "height", "cells", "length"})


def solved_check_violations(js_source: str) -> list[str]:
    code, _ = _scan(js_source)
    body = definition(code, "isClueSolved")
    if body is None:
        return ["isClueSolved: not defined"]
    problems = [f"isClueSolved: free reference {ref!r}" for ref in sorted(free_references(body) - SOLVED_ALLOWED)]
    if re.search(r"circle", body, re.I):
        problems.append("isClueSolved: names a circle")
    return problems


def _warning_text(js_source: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*//\s?", "", js_source))


class TestPublicCircles_ThePredicateIsTheModules:
    """AC-3, and the EC (ADR-0041/R3): the page's set equals ``circledClues``'s."""

    def test_the_circle_code_says_nothing_but_the_modules_return_value(self) -> None:
        assert circle_code_violations(PLAY_JS.read_text(encoding="utf-8")) == []

    def test_the_circle_code_is_not_vacuously_clean(self) -> None:
        """A scanner that found nothing to scan would also report nothing."""
        source = PLAY_JS.read_text(encoding="utf-8")
        for name in ("paintCircles", "clueNumbersOf"):
            raw = _raw_definition(source, name)
            assert raw is not None and len(_TOKEN.findall(raw)) > 20, name

    @pytest.mark.parametrize(
        ("old", "new", "expect"),
        [
            (TOGGLE, '        if (line > 0) span.classList.toggle("is-circled", circled[axis][line][k]);', "token"),
            (TOGGLE, '        span.classList.toggle("is-circled", circled[axis][line][k] && spans.length > 1);', "property .length"),
            (TOGGLE, '        span.getAttribute("data-state");\n' + TOGGLE, "property .getAttribute"),
            (TOGGLE, '        span["dataset"];\n' + TOGGLE, "computed member"),
            (TOGGLE, "        history.board.cells;\n" + TOGGLE, "identifier history"),
            (TOGGLE, "        Math.max(1, 2);\n" + TOGGLE, "identifier Math"),
            (TOGGLE, '        span.classList.toggle("is-circled", circled[axis][line][k] || "data-state");', "string"),
            (TOGGLE, '        span.addEventListener("click", () => {});\n' + TOGGLE, "property .addEventListener"),
            (TOGGLE, "        circled = null;\n" + TOGGLE, "token '='"),
            (TOGGLE, '        span.classList.toggle("is-circled", circled[axis]["0"][k]);', "computed member"),
            (TOGGLE, '        span.classList.toggle("is-circled", circled[axis][line][k + 1]);', "computed member"),
            (TOGGLE, '        span.classList.toggle("is-circled", (circled[axis][line][k], k));', "comma operator"),
            (TOGGLE, '        span.classList.toggle("is-circled", circled[axis][k][line]);', "chain"),
            (TOGGLE, '        span.classList.toggle("is-circled", circled[axis][line][line]);', "chain"),
            (TOGGLE, '        span.classList.toggle("is-circled", circled[line][axis][k]);', "chain"),
            ("function paintCircles(", "function decide(spans) { spans[0].classList.toggle('is-circled', true); }\nfunction paintCircles(", "is-circled"),
            ("function paintCircles(", "function decide(spans) { spans[0].classList.toggle(`is-circled`, true); }\nfunction paintCircles(", "is-circled"),
            ("function paintCircles(", "function decide(spans) { spans[0].className = \"player-clue-num is-circled\"; }\nfunction paintCircles(", "is-circled"),
            ("      lines[Number(box.dataset.line)] = [...box.querySelectorAll(\".player-clue-num\")];",
             "      lines[Number(box.dataset.line)] = [...box.querySelectorAll(\".player-clue-num\")].map((n) => n.textContent);",
             "property .map"),
            ("      lines[Number(box.dataset.line)] = [...box.querySelectorAll(\".player-clue-num\")];",
             "      lines[box.dataset.line] = [...box.querySelectorAll(\".player-clue-num\")];",
             "computed member"),
        ],
        ids=[
            "an-operator-and-a-condition", "a-length-property", "a-getAttribute-read", "a-computed-member-by-string",
            "a-reference-to-the-history", "a-global-helper", "a-string-naming-state", "a-listener", "an-assignment",
            "a-computed-index-by-literal", "an-offset-index",
            "the-comma-operator", "indexes-k-then-line", "indexes-line-twice", "indexes-axis-after-line",
            "a-second-toggler-in-single-quotes", "a-second-toggler-in-a-template", "a-second-circled-rule-in-another-function",
            "collector-reads-the-text", "collector-indexes-by-a-string",
        ],
    )
    def test_a_second_rule_or_a_read_the_painter_may_not_make_is_refused(self, old, new, expect) -> None:
        """The matched control (the shipped source is clean) and one plant each.

        ``!=`` and ``not in`` are not used in the scanner; its refusals are the
        membership tests above, each planted here, so a bypass of the allowlist
        is a plant that comes back clean and is therefore a failing case."""
        source = PLAY_JS.read_text(encoding="utf-8")
        assert circle_code_violations(source) == [], "the matched control"
        assert source.count(old) == 1, f"the plant must apply exactly once: {old!r}"
        found = circle_code_violations(source.replace(old, new))
        assert found != [], "a plant that the scanner cannot see"
        assert any(expect in problem for problem in found), (expect, found)

    @pytest.mark.parametrize(
        ("old", "new"),
        [
            ("  circledClues,\n} from", "} from"),
            (HOOK, "    paintCircles(clueNumbers, circledClues(shown, payload.rows, payload.columns));"),
            (HOOK, ""),
            ("function paintCircles(", "function paintCirclesToo(clueNumbers, circled) {}\nfunction paintCircles("),
        ],
        ids=["the-import-is-gone", "the-hook-reads-the-preview", "the-hook-is-gone", "a-second-painter-is-defined"],
    )
    def test_the_import_and_the_hook_are_held_too(self, old, new) -> None:
        source = PLAY_JS.read_text(encoding="utf-8")
        assert circle_code_violations(source) == [], "the matched control"
        assert source.count(old) == 1, old
        problems = circle_code_violations(source.replace(old, new))
        assert problems != []

    def test_the_solved_check_is_still_the_clue_rule_and_its_warning_stands(self) -> None:
        source = PLAY_JS.read_text(encoding="utf-8")
        assert solved_check_violations(source) == []
        assert "NOT built out of solver_state.js's circledNumbers" in _warning_text(source)
        assert "two of which fire on marks that satisfy no clue" in _warning_text(source)
        assert source.count("    const done = isClueSolved(history.board, payload.rows, payload.columns);") == 1
        assert source.count("    isSolved: () => isClueSolved(history.board, payload.rows, payload.columns),") == 1

    @pytest.mark.parametrize(
        "insertion",
        [
            "  const c = circledClues(board, rows, columns);",
            "  const c = window.circled;",
            "  return paintCircles;",
        ],
        ids=["the-module-call", "a-circle-global", "a-reference-to-the-painter"],
    )
    def test_a_solved_check_that_reaches_for_the_circles_is_refused(self, insertion) -> None:
        source = PLAY_JS.read_text(encoding="utf-8")
        assert solved_check_violations(source) == [], "the matched control"
        anchor = "export function isClueSolved(board, rows, columns) {\n"
        assert source.count(anchor) == 1
        assert solved_check_violations(source.replace(anchor, anchor + insertion + "\n")) != []

    def test_the_circle_code_registers_no_listener_and_the_file_adds_none(self) -> None:
        """GAP 3: the census of listener types in ``tests/test_public_player.py``
        runs unedited because this card adds none. This test covers the TWO circle
        bodies only; what holds the rest of the file is that census (it counts
        every ``addEventListener`` type in ``play.js`` and reds on a new one)."""
        source = PLAY_JS.read_text(encoding="utf-8")
        for name in ("paintCircles", "clueNumbersOf"):
            assert "addEventListener" not in (_raw_definition(source, name) or "addEventListener")

    @pytest.mark.browser
    def test_the_page_set_equals_the_modules_across_a_seeded_corpus(self, browser_page, host) -> None:
        """EC (ADR-0041/R3): boards spanning extents and mark patterns, the page's
        circle set equals ``circledClues``'s return value for the same board,
        with the corpus size asserted inside the test."""
        page = browser_page
        rng = random.Random(326)
        puzzles = {**GRIDS, "circles": CIRCLES_GRID}
        cases = mismatches = circled = uncircled = mixed_repeats = 0
        extents = set()
        for name, grid in puzzles.items():
            height, width = len(grid), len(grid[0])
            cells = [(r, c) for r in range(height) for c in range(width)]
            black = [x for x in cells if grid[x[0]][x[1]]]
            white = [x for x in cells if not grid[x[0]][x[1]]]
            for _ in range(2):
                chosen = [x for x in cells if rng.random() < 0.6]
                patterns = [
                    _marked(grid, rows=sorted(rng.sample(range(height), rng.randint(1, height - 1)))),
                    [("filled", [x for x in black if rng.random() < 0.7])],
                    [("empty", [x for x in chosen if not grid[x[0]][x[1]]]), ("filled", [x for x in chosen if grid[x[0]][x[1]]])],
                    [(state, [x for x in cells if rng.random() < 0.15]) for state in ("filled", "empty", "maybe")],
                    _marked(grid, extra=rng.sample(white, min(3, len(white)))),
                    _marked(grid, rows=[r for r in range(height) if rng.random() < 0.5] or [0]),
                ]
                for strokes in patterns:
                    _board(page, host, host[2][name], grid, [s for s in strokes if s[1]])
                    dom, want = _dom(page), _want(page)
                    cases += 1
                    extents.add((width, height))
                    mismatches += len(_differences(dom, want))
                    # a DOM with MORE numbers (or more circled ones) than the module's
                    # would pass the per-number comparison above: totals are compared too
                    mismatches += abs(_total(dom) - _total(want)) + abs(_count(dom) - _count(want))
                    circled += _count(want)
                    uncircled += _total(want) - _count(want)
                    clues = page.evaluate("() => window.publicPlayer.payload")
                    for axis, key in (("rows", "rows"), ("columns", "columns")):
                        for line, clue in enumerate(clues[key]):
                            flags = want[axis][line]
                            mixed_repeats += any(
                                clue[i] == clue[j] and flags[i] != flags[j]
                                for i in range(len(clue))
                                for j in range(i + 1, len(clue))
                            )
        assert mismatches == 0
        assert cases >= 60, cases
        assert len(extents) >= 4, extents
        assert circled > 0 and uncircled > 0, (circled, uncircled)
        assert mixed_repeats > 0, "the corpus never circled one of two equal numbers and not the other"


# ==========================================================================
# AC-4 - circles are not the solved check
# ==========================================================================

_ALL_CIRCLED_ELSEWHERE = """async ({ grid, rows, cols }) => {
  const S = await import('/solver_state.js');
  const h = grid.length, w = grid[0].length;
  const base = grid.flat().map((v) => (v ? 'filled' : 'empty'));
  const hits = [];
  for (let r = 0; r < h; r++) for (let c = 0; c < w; c++) {
    if (grid[r][c]) continue;
    const cells = [...base];
    cells[r * w + c] = 'filled';
    const out = S.circledClues({ width: w, height: h, cells }, rows, cols);
    if ([...out.rows, ...out.columns].every((line) => line.every(Boolean))) hits.push([r, c]);
  }
  return hits;
}"""

#: Replaces the banner's predicate with "every number circled".
BANNER_FROM_CIRCLES = (
    "    const done = isClueSolved(history.board, payload.rows, payload.columns);",
    "    const done = (() => { const c = circledClues(history.board, payload.rows, payload.columns); "
    "return [...c.rows, ...c.columns].every((line) => line.every((flag) => flag === true)); })();",
)
#: Replaces the clue rule itself with "every number circled".
RULE_FROM_CIRCLES = (
    "export function isClueSolved(board, rows, columns) {\n",
    "export function isClueSolved(board, rows, columns) {\n"
    "  const c = circledClues(board, rows, columns);\n"
    "  if (c) return [...c.rows, ...c.columns].every((line) => line.every((flag) => flag === true));\n",
)


def _solved_reading(page) -> dict:
    return page.evaluate(
        """() => ({
          isSolved: window.publicPlayer.isSolved(),
          bannerHidden: document.querySelector('[data-player-solved]').hidden,
          body: document.body.dataset.solved,
        })"""
    )


def _wrong_board_reading(page, host, extra) -> tuple[dict, dict]:
    """``(the wrong board's reading, the solution's reading)`` on this card's fixture."""
    key = host[2]["circles"]
    _board(page, host, key, CIRCLES_GRID, _marked(CIRCLES_GRID, extra=[extra]))
    wrong = {**_solved_reading(page), "all_circled": _count(_dom(page)) == _total(_dom(page)), "same_as_module": _mismatch(page, "wrong") == []}
    _board(page, host, key, CIRCLES_GRID, _marked(CIRCLES_GRID))
    right = {**_solved_reading(page), "all_circled": _count(_dom(page)) == _total(_dom(page))}
    return wrong, right


@pytest.mark.browser
class TestPublicCircles_CirclesAreNotTheSolvedCheck:
    """AC-4. A board where every number is circled and the board is not solved."""

    @pytest.mark.parametrize("extra", EXTRA_CELLS, ids=[f"extra-cell-{r}-{c}" for r, c in EXTRA_CELLS])
    def test_every_number_circled_and_the_board_is_not_solved(self, browser_page, host, extra) -> None:
        wrong, right = _wrong_board_reading(browser_page, host, extra)
        assert wrong["all_circled"] and wrong["same_as_module"], wrong
        assert wrong["isSolved"] is False
        assert wrong["bannerHidden"] is True
        assert wrong["body"] == "false"
        # the matched control, in this same run: the solution circles everything
        # too, and there the check DOES fire, so the page can tell them apart.
        assert right["all_circled"] and right["isSolved"] is True
        assert right["bannerHidden"] is False and right["body"] == "true"

    def test_the_constructed_board_is_what_the_card_says(self, browser_page, host) -> None:
        """The extra-cell list is the module's own finding on this fixture, not a
        number written here: the set of white cells that, marked black on the
        marked solution, leave every number circled, equals :data:`EXTRA_CELLS`."""
        page = browser_page
        _open(page, host, host[2]["circles"])
        hits = page.evaluate(
            _ALL_CIRCLED_ELSEWHERE,
            {"grid": [[int(v) for v in row] for row in CIRCLES_GRID],
             "rows": [_encode(row) for row in CIRCLES_GRID],
             "cols": [_encode(column) for column in zip(*CIRCLES_GRID)]},
        )
        assert sorted(map(tuple, hits)) == sorted(EXTRA_CELLS)

    @pytest.mark.parametrize("name", list(GRIDS))
    def test_no_existing_fixture_has_the_extra_cell_board(self, browser_page, host, name) -> None:
        """Why this card builds a fixture of its own (the card's AC-4 asks to say
        so). Bounded claim: of the boards that are a fully marked solution plus
        ONE extra black cell, none leaves every number circled, for each of the
        four shared fixtures. Other wrong boards were not searched."""
        page = browser_page
        grid = GRIDS[name]
        _open(page, host, host[2][name])
        hits = page.evaluate(
            _ALL_CIRCLED_ELSEWHERE,
            {"grid": [[int(v) for v in row] for row in grid],
             "rows": [_encode(row) for row in grid],
             "cols": [_encode(column) for column in zip(*grid)]},
        )
        assert hits == []

    @pytest.mark.parametrize(
        ("name", "plant"), [("banner-from-circles", BANNER_FROM_CIRCLES), ("rule-from-circles", RULE_FROM_CIRCLES)]
    )
    def test_a_solved_check_made_from_the_circle_set_declares_victory_on_the_wrong_board(
        self, browser_page, host, name, plant
    ) -> None:
        """The plant the card asks for. Control first: the shipped page reads the
        wrong board as unsolved. Then the served ``play.js`` is rewritten so the
        solved check is "every number circled"; the same board must now read as
        solved (banner shown and/or ``isSolved()`` true)."""
        page = browser_page
        wrong, _ = _wrong_board_reading(page, host, EXTRA_CELLS[0])
        assert wrong["isSolved"] is False and wrong["bannerHidden"] is True, "the matched control"
        _plant(page, host, "play.js", *plant)
        planted, _ = _wrong_board_reading(page, host, EXTRA_CELLS[0])
        assert planted["isSolved"] is True or planted["bannerHidden"] is False, (name, planted)


# ==========================================================================
# AC-5 - no answer, no request
# ==========================================================================

#: The files one load of ``/play/<key>`` fetches. Written out because "no
#: request beyond the puzzle's own GET" is asserted against this list AND against
#: the list the same page had after it finished loading.
LOAD_PATHS = {"/tokens.css", "/player.css", "/play.js", "/solver_state.js"}


@pytest.mark.browser
class TestPublicCircles_NoAnswerAndNoRequest:
    def test_every_interaction_issues_nothing_beyond_the_load(self, browser_page, host) -> None:
        page = browser_page
        url, _, keys = host
        key = keys["circles"]
        seen: list[tuple[str, str]] = []
        page.context.on("request", lambda request: seen.append((request.method, request.url)))
        _open(page, host, key)
        page.wait_for_timeout(300)
        after_load = list(seen)
        assert all(method == "GET" and address.startswith(url + "/") for method, address in after_load), after_load
        paths = {address[len(url):] for _, address in after_load}
        assert paths >= LOAD_PATHS | {f"/puzzle/{key}.json"}, paths
        assert sum(1 for _, address in after_load if address.endswith(".json")) == 1
        # every interaction that moves the circles
        _click(page, EMPTY_BRUSH)
        for col in (0, 3, 4, 5, 7, 8):
            _tap(page, 5, col)
        _click(page, FILLED_BRUSH)
        for col in (1, 2, 6, 9):
            _tap(page, 5, col)
        _drag(page, [(7, 1), (7, 2), (7, 3), (7, 4)])
        _click(page, UNDO)
        _click(page, REDO)
        page.keyboard.press("Control+z")
        page.keyboard.press("Control+Shift+z")
        _click(page, RESET)
        _click(page, UNDO)
        _click(page, '[data-player-region]')
        _click(page, '[data-player-zoom-action="in"]')
        page.wait_for_timeout(300)
        assert _count(_dom(page)) >= 0 and _mismatch(page, "after the walk") == []
        assert seen == after_load, [item for item in seen if item not in after_load]

    def test_the_page_holds_no_solution_field_and_the_circles_add_no_attribute(self, browser_page, host) -> None:
        page = browser_page
        key = host[2]["circles"]
        _board(page, host, key, CIRCLES_GRID, _marked(CIRCLES_GRID))
        assert page.evaluate("() => Object.keys(window.publicPlayer.payload).sort()") == [
            "columns", "height", "key", "rows", "tier", "width",
        ]
        assert page.evaluate("() => Object.keys(window.publicPlayer).sort()") == [
            "getBoard", "getHistory", "getTool", "getZoom", "isRegion", "isSolved", "payload", "saveKey",
        ]
        spans = page.evaluate(
            """() => [...document.querySelectorAll('.player-clue-num')].map((n) => ({
              attributes: n.getAttributeNames().sort(), classes: [...n.classList].sort() }))"""
        )
        assert len(spans) > 40
        assert {tuple(s["attributes"]) for s in spans} == {("class",)}, "a circle is a class and nothing else"
        assert {tuple(s["classes"]) for s in spans} == {("is-circled", "player-clue-num")}, "every number circled on the solved board"
        html = page.content()
        assert "solution" not in html.lower()

    def test_the_circle_code_adds_no_external_reference(self) -> None:
        for name in ("play.js", "player.css", "play.html"):
            text = (PLAYER_DIR / name).read_text(encoding="utf-8")
            code = _scan(text)[0] if name == "play.js" else re.sub(r"/\*.*?\*/|<!--.*?-->", "", text, flags=re.S)
            for forbidden in ("http://", "https://", "url(", "@import", "<script src", "<link rel=\"preconnect"):
                assert forbidden not in code, (name, forbidden)


# ==========================================================================
# GAP 1 - a crossed AND circled clue shows both
# ==========================================================================
#
# The crosshair (CARD-325) tints the clue BOXES of the hovered row and column
# with a BACKGROUND; the circle is a BORDER on the number's ::before. The
# decision: they are different channels, so neither can hide the other, and the
# circle needs no rule of its own for a crossed box. What is held here is the
# PIXELS, not the rule: a screenshot of a crossed box shows the tint at its
# corner and the ink ring at the number.

_RING = """(selector) => {
  const box = document.querySelector(selector);
  const span = box.querySelector('.player-clue-num.is-circled');
  const probe = document.createElement('i');
  probe.style.background = 'var(--grid-ink)';
  document.body.append(probe);
  const ink = getComputedStyle(probe).backgroundColor;
  probe.remove();
  if (!span) return { found: false };
  const cs = getComputedStyle(span, '::before');
  const r = span.getBoundingClientRect();
  const b = box.getBoundingClientRect();
  return {
    found: true, crossed: box.classList.contains('is-crossed'), ink,
    boxBackground: getComputedStyle(box).backgroundColor,
    left: r.left + parseFloat(cs.left), top: r.top + parseFloat(cs.top),
    w: parseFloat(cs.width), h: parseFloat(cs.height), bw: parseFloat(cs.borderTopWidth),
    corner: { x: b.left + 2, y: b.top + 2 },
  };
}"""


def _rgb(text: str) -> tuple[int, int, int]:
    """``rgb(r, g, b)`` or the ``color(srgb r g b)`` form a ``color-mix`` computes to."""
    numbers = [float(n) for n in re.findall(r"[\d.]+", text)[:3]]
    scale = 255 if text.startswith("color(srgb") else 1
    return tuple(round(n * scale) for n in numbers)  # type: ignore[return-value]


def _pixels(page, x: float, y: float, width: float, height: float):
    from PIL import Image

    png = page.screenshot(clip={"x": x, "y": y, "width": max(width, 1), "height": max(height, 1)})
    return Image.open(io.BytesIO(png)).convert("RGB")


def _distance(one, other) -> int:
    return max(abs(a - b) for a, b in zip(one, other))


def _ring_edge_distances(page, ring: dict) -> dict[str, int]:
    """How far the darkest pixel on EACH of the ring's four edges, at its middle,
    is from the ink (review F-4a: the left edge alone let a plant that clipped
    the right half of the ring pass)."""
    ink = _rgb(ring["ink"])
    bw, mid_x, mid_y = ring["bw"], ring["left"] + ring["w"] / 2, ring["top"] + ring["h"] / 2
    clips = {
        "left": (int(ring["left"]) - 1, mid_y - 1, bw + 3, 2),
        "right": (int(ring["left"] + ring["w"] - bw) - 1, mid_y - 1, bw + 3, 2),
        "top": (mid_x - 1, int(ring["top"]) - 1, 2, bw + 3),
        "bottom": (mid_x - 1, int(ring["top"] + ring["h"] - bw) - 1, 2, bw + 3),
    }
    out: dict[str, int] = {}
    for edge, clip in clips.items():
        picture = _pixels(page, *clip)
        out[edge] = min(_distance(picture.getpixel((x, y)), ink) for x in range(picture.width) for y in range(picture.height))
    return out


def crossed_problems(page, host, keys) -> list[str]:
    """Row 2 and column 1 of the card's fixture are crossed; each crossed clue
    box has a circled number; the box shows its tint AND the number its ring."""
    key = keys["circles"]
    problems: list[str] = []
    _board(page, host, key, CIRCLES_GRID, _marked(CIRCLES_GRID, rows=range(5)))
    page.mouse.move(2, 2)
    before = {kind: page.evaluate(_RING, f"th.player-clue.is-{kind}[data-line='{line}']") for kind, line in (("row", 2), ("col", 1))}
    _move(page, 2, 1)
    _assert_crossed_at(page, 2, 1)
    for kind, line in (("row", 2), ("col", 1)):
        ring = page.evaluate(_RING, f"th.player-clue.is-{kind}.is-crossed")
        if not ring["found"]:
            problems.append(f"{kind}: no circled number in the crossed box (the scenario is vacuous)")
            continue
        for edge, distance in _ring_edge_distances(page, ring).items():
            if distance > 40:
                problems.append(f"{kind}: the crossed box's ring is not ink at its {edge} edge")
        corner = _pixels(page, ring["corner"]["x"], ring["corner"]["y"], 1, 1).getpixel((0, 0))
        if _distance(corner, _rgb(ring["boxBackground"])) > 6:
            problems.append(f"{kind}: the crossed box does not show its own background at its corner")
        if ring["boxBackground"] == before[kind]["boxBackground"]:
            problems.append(f"{kind}: crossing did not tint the box (the scenario is vacuous)")
        if (ring["w"], ring["h"]) != (before[kind]["w"], before[kind]["h"]):
            problems.append(f"{kind}: crossing changed the ring's size")
    return problems


@pytest.mark.browser
class TestPublicCircles_ACrossedClueStillShowsItsCircle:
    """GAP 1."""

    def test_a_crossed_and_circled_clue_box_shows_its_tint_and_its_ring(self, browser_page, host) -> None:
        assert crossed_problems(browser_page, host, host[2]) == []

    @pytest.mark.parametrize(
        "plant",
        [
            "\n.player-clue.is-crossed .player-clue-num::before { border-color: transparent; }",
            '\n.player-clue.is-crossed::after { content: ""; position: absolute; inset: 0; background: var(--player-cross); }',
            "\n.player-clue.is-crossed .player-clue-num { visibility: hidden; }",
            "\n.player-clue.is-crossed .player-clue-num::before { clip-path: inset(0 50% 0 0); }",
            "\n.player-clue.is-crossed .player-clue-num::before { clip-path: inset(0 0 50% 0); }",
            "\n.player-clue.is-crossed .player-clue-num::before { clip-path: inset(50% 0 0 0); }",
        ],
        ids=["tint-clears-the-ring", "tint-is-an-overlay-above-the-ring", "tint-hides-the-number",
             "right-half-clipped", "lower-half-clipped", "upper-half-clipped"],
    )
    def test_a_tint_that_can_hide_the_ring_is_caught(self, browser_page, host, plant) -> None:
        page = browser_page
        assert crossed_problems(page, host, host[2]) == [], "the matched control"
        anchor = ".player-board .player-clue-num.is-circled::before { border-color: var(--grid-ink); }"
        _plant(page, host, "player.css", anchor, anchor + plant)
        assert crossed_problems(page, host, host[2]) != []


# ==========================================================================
# GAP 4 - the circles at the zoom maximum and at a scrolled offset
# ==========================================================================

_RINGS_IN_VIEW = """() => {
  const stage = document.querySelector('[data-player-stage]');
  const view = stage.getBoundingClientRect();
  const out = [];
  for (const span of document.querySelectorAll('.player-clue-num.is-circled')) {
    const cs = getComputedStyle(span, '::before');
    const r = span.getBoundingClientRect();
    const ring = { left: r.left + parseFloat(cs.left), top: r.top + parseFloat(cs.top), w: parseFloat(cs.width), h: parseFloat(cs.height) };
    const inside = ring.left >= view.left + 1 && ring.top >= view.top + 1
      && ring.left + ring.w <= view.right - 1 && ring.top + ring.h <= view.bottom - 1
      && ring.left >= 0 && ring.top >= 0 && ring.left + ring.w <= window.innerWidth && ring.top + ring.h <= window.innerHeight;
    const box = span.closest('th.player-clue');
    // Uncovered: the hit test at the ring's centre and at the middle of each
    // of its four edges lands in the number's own clue box (a pinned gutter
    // that covers the ring's edge puts another box there).
    const probes = [[ring.left + ring.w / 2, ring.top + ring.h / 2], [ring.left + 1.5, ring.top + ring.h / 2],
      [ring.left + ring.w - 1.5, ring.top + ring.h / 2], [ring.left + ring.w / 2, ring.top + 1.5],
      [ring.left + ring.w / 2, ring.top + ring.h - 1.5]];
    const uncovered = probes.every(([x, y]) => document.elementFromPoint(x, y)?.closest('th.player-clue') === box);
    if (inside && uncovered) {
      out.push({ ...ring, kind: box.classList.contains('is-row') ? 'row' : 'col', line: Number(box.dataset.line) });
    }
  }
  return out;
}"""

_GAPS = """() => {
  const rect = (span) => {
    const cs = getComputedStyle(span, '::before');
    const r = span.getBoundingClientRect();
    return { l: r.left + parseFloat(cs.left), t: r.top + parseFloat(cs.top), w: parseFloat(cs.width), h: parseFloat(cs.height) };
  };
  let row = Infinity, col = Infinity, pairs = 0;
  for (const box of document.querySelectorAll('th.player-clue.is-row')) {
    const rs = [...box.querySelectorAll('.player-clue-num')].map(rect);
    for (let i = 1; i < rs.length; i++) { row = Math.min(row, rs[i].l - (rs[i - 1].l + rs[i - 1].w)); pairs++; }
  }
  for (const box of document.querySelectorAll('th.player-clue.is-col')) {
    const rs = [...box.querySelectorAll('.player-clue-num')].map(rect);
    for (let i = 1; i < rs.length; i++) { col = Math.min(col, rs[i].t - (rs[i - 1].t + rs[i - 1].h)); pairs++; }
  }
  const first = document.querySelector('.player-clue-num');
  return { row, col, pairs, ringHeight: parseFloat(getComputedStyle(first, '::before').height) };
}"""

#: DECLARED BOUND (ADR-0039/R3). Two neighbouring rings in one clue box must
#: keep at least this many px apart, so a stack of rings reads as separate
#: circles and not as one chain. REASON: 0.25 px is admin.css's own
#: ``--player-ring-gap`` (CARD-196), the number the panel's rings are held to.
#: MEASURED RESIDUE (this round, the 30 x 30 and 25 x 26 fixtures of the real
#: bundle fully marked): at 100% the smallest gap was 1.00 px between row rings
#: and 0.59 px between column rings on a 390 px phone; at the 300% maximum it
#: was 3.11 px and 1.77 px (rings and gaps both scale with the cell). The
#: control that fails just past the bound is ``--player-circle: 1.09em``, a ring
#: 0.04em taller than the shipped 1.05em, which leaves 0.01em (about 0.12 px at
#: the phone's 100%) between stacked rings.
RING_GAP_FLOOR_PX = 0.25

#: DECLARED BOUND. The ring's height at the zoom maximum, divided by its height
#: at 100%, must equal the zoom ratio to within this fraction: a ring that does
#: not scale with the board is not "in place" next to its number. REASON: the
#: ring is sized in the numeral's em and the numeral in cells, and zoom
#: multiplies the cell, so the ratio should be exact up to layout rounding.
#: MEASURED RESIDUE: 0.0003 on the 390 px phone (37.03 / 12.34 against 3.0) and
#: 0.0007 on the 1440 px desktop (44.97 / 14.98); the bound is 0.01, an order
#: above the residue. The control that fails past it is a ring declared in px
#: (``--player-circle: 15px``), which does not scale at all (ratio 1.0).
RING_SCALE_TOLERANCE = 0.01


def _zoom_to_max(page) -> None:
    for _ in range(64):
        if _percent(page) >= _bounds(page)["max"]:
            break
        _press(page, "in")
    assert _percent(page) == _bounds(page)["max"]


def _scroll_stage(page, fraction: float) -> tuple[float, float]:
    return page.evaluate(
        """(f) => {
          const s = document.querySelector('[data-player-stage]');
          s.scrollLeft = (s.scrollWidth - s.clientWidth) * f;
          s.scrollTop = (s.scrollHeight - s.clientHeight) * f;
          return [s.scrollLeft, s.scrollTop];
        }""",
        fraction,
    )


def _scroll_into_the_gutters(page, fraction: float) -> tuple[float, float]:
    return page.evaluate(
        """(f) => {
          const s = document.querySelector('[data-player-stage]');
          const rowGutter = document.querySelector('th.player-clue.is-row').getBoundingClientRect().width;
          const colBand = document.querySelector('th.player-clue.is-col').getBoundingClientRect().height;
          s.scrollLeft = rowGutter * f;
          s.scrollTop = colBand * f;
          return [s.scrollLeft, s.scrollTop];
        }""",
        fraction,
    )


def _spread(items: list[dict], count: int) -> list[dict]:
    ordered = sorted(items, key=lambda ring: (ring["kind"], ring["line"], ring["left"], ring["top"]))
    picks = sorted({round(i * (len(ordered) - 1) / (count - 1)) for i in range(count)}) if len(ordered) > count else range(len(ordered))
    return [ordered[i] for i in picks]


#: DECLARED BOUND AND ITS RESIDUE (ADR-0039/R3). The in-place check asks for ink
#: within this many px of each of a ring's four edges. REASON: edge pixels are
#: anti-aliased and the clip is rounded to whole pixels, so an exact edge is not
#: a stable thing to read. RESIDUE, measured this round at the 300% maximum on
#: the 30 x 30 fixture (3 px ring line, 8 sampled rings on a 1440 px desktop): a
#: ring drawn shifted by 1 px is NOT seen (0 of 8 report), one shifted by 1.5 px
#: is (7 of 8 report); so a displacement under about 1.5 px is invisible to this
#: check, and at 100% (1 px line) the same band is proportionally coarser. The
#: control just past it is the 1.5 px shift in
#: ``test_the_in_place_residue_is_declared_and_a_shift_just_past_it_is_caught``.
IN_PLACE_BAND_PX = 2
SHIFT_THE_CHECK_CANNOT_SEE_PX = 1
SHIFT_THE_CHECK_CATCHES_PX = 1.5

#: COVERAGE OF THE ZOOM SAMPLE, measured this round (the 30 x 30 fixture fully
#: marked, 423 circled numbers, at the 300% maximum; "in view" = the ring lies
#: wholly inside the stage and the window and a hit test at its centre and four
#: edge midpoints lands in its own clue box). Desktop unscrolled: 61 in view
#: (45 column, 16 row), 8 sampled (6 column, 2 row). Phone a quarter into the
#: gutters: 16 in view, ALL row rings, 8 sampled. Phone three quarters in: 15 in
#: view (10 row, 5 column), 8 sampled (5 row, 3 column). So at the phone's 300%
#: only 15-16 of 423 circled rings are in view and uncovered (about 3.6%), and
#: at the first offset no column ring is sampled; the claim is "the rings that
#: can be seen are in place", not "every ring is". The reviewer reported 6-7 of
#: 195 for the same question; I could not reproduce those figures (a different
#: fixture or marking, not asked): the numbers above are mine, from this round.


def ring_in_place_problems(page, rings: list[dict]) -> list[str]:
    """Each sampled ring is drawn where the page says, at the size it says:
    ink on all four of the clip's edges (the ring), within 2 px of its box."""
    import numpy as np

    problems: list[str] = []
    ink = _rgb(page.evaluate("() => { const p = document.createElement('i'); p.style.background = 'var(--grid-ink)'; document.body.append(p); const c = getComputedStyle(p).backgroundColor; p.remove(); return c; }"))
    for ring in rings:
        picture = np.asarray(_pixels(page, ring["left"], ring["top"], ring["w"], ring["h"]), dtype=int)
        near = np.abs(picture - np.array(ink)).max(axis=2) <= 40
        band = IN_PLACE_BAND_PX
        for side, edge in (("left", near[:, :band]), ("right", near[:, -band:]), ("top", near[:band, :]), ("bottom", near[-band:, :])):
            if not edge.any():
                problems.append(f"{ring['kind']} {ring['line']}: no ink on the ring's {side} edge")
    return problems


def _ring_state(page) -> dict:
    return {"gaps": page.evaluate(_GAPS), "percent": _percent(page)}


@pytest.mark.browser
class TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled:
    """GAP 4."""

    @pytest.mark.parametrize(
        ("viewport", "fraction"),
        [("desktop", 0.0), ("phone", 0.25), ("phone", 0.75)],
        ids=["desktop-unscrolled", "phone-a-quarter-into-the-gutters", "phone-three-quarters-into-the-gutters"],
    )
    def test_the_rings_are_in_place_and_clear_of_each_other_at_the_maximum(self, browser_page, host, viewport, fraction) -> None:
        """``fraction`` is how far into the clue GUTTERS the stage is scrolled
        (of the row gutter's width and the column band's height), because the
        gutters are what carry the numbers: a scroll to the middle of a 30 x 30
        at 300% leaves no clue number in view at all."""
        page = browser_page
        key, grid = host[2]["max"], GRIDS["max"]
        page.set_viewport_size({"width": 390, "height": 844} if viewport == "phone" else {"width": 1440, "height": 900})
        _board(page, host, key, grid, _marked(grid))
        at_100 = _ring_state(page)
        _zoom_to_max(page)
        at_max = _ring_state(page)
        if fraction:
            left, top = _scroll_into_the_gutters(page, fraction)
            assert left > 0 and top > 0, "the stage did not scroll: the offset arm would be vacuous"
        rings = _rings_for_test(page)
        assert len(rings) >= 6, f"too few rings in view to say anything: {len(rings)}"
        assert {ring["kind"] for ring in rings} >= {"row", "col"} or viewport == "phone"
        assert ring_in_place_problems(page, _spread(rings, 8)) == []
        # scale: the ring grows with the zoom, to the declared tolerance
        ratio = at_max["gaps"]["ringHeight"] / at_100["gaps"]["ringHeight"]
        zoom = at_max["percent"] / at_100["percent"]
        assert abs(ratio / zoom - 1) <= RING_SCALE_TOLERANCE, (ratio, zoom)
        # clearance: the declared floor, at 100% and at the maximum
        for state in (at_100, at_max):
            assert state["gaps"]["pairs"] > 100
            assert state["gaps"]["row"] >= RING_GAP_FLOOR_PX and state["gaps"]["col"] >= RING_GAP_FLOOR_PX, state["gaps"]

    @pytest.mark.parametrize(
        ("name", "old", "new", "what"),
        [
            ("ring-too-tall", "  --player-circle: 1.05em;", "  --player-circle: 1.09em;", "gap"),
            ("ring-in-px", "  --player-circle: 1.05em;", "  --player-circle: 15px;", "scale"),
        ],
    )
    def test_a_ring_past_a_declared_bound_is_caught(self, browser_page, host, name, old, new, what) -> None:
        """The matched control (shipped CSS passes both bounds) and the plant
        that fails just past each: 1.09em leaves 0.12 px between stacked rings
        at the phone's 100% (floor 0.25 px); a px ring does not scale."""
        page = browser_page
        key, grid = host[2]["max"], GRIDS["max"]
        page.set_viewport_size({"width": 390, "height": 844})

        def readings():
            _board(page, host, key, grid, _marked(grid))
            at_100 = _ring_state(page)
            _zoom_to_max(page)
            return at_100, _ring_state(page)

        def breaches(at_100, at_max) -> list[str]:
            found = []
            ratio = (at_max["gaps"]["ringHeight"] / at_100["gaps"]["ringHeight"]) / (at_max["percent"] / at_100["percent"])
            if abs(ratio - 1) > RING_SCALE_TOLERANCE:
                found.append("scale")
            if min(at_100["gaps"]["row"], at_100["gaps"]["col"]) < RING_GAP_FLOOR_PX:
                found.append("gap")
            return found

        assert breaches(*readings()) == [], "the matched control"
        _plant(page, host, "player.css", old, new)
        assert what in breaches(*readings())


def _rings_for_test(page) -> list[dict]:
    return page.evaluate(_RINGS_IN_VIEW)


@pytest.mark.browser
class TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed:
    """The in-place check reads PIXELS against the geometry the page reports, so
    a ring drawn somewhere else than where it says is caught."""

    @pytest.mark.parametrize(
        "plant",
        [
            "\n.player-board .player-clue-num::before { transform: translateX(9px); }",
            "\n.player-board .player-clue-num::before { transform: translateY(9px); }",
            "\n.player-board .player-clue-num.is-circled::before { border-style: none; }",
            "\n.player-board .player-clue-num.is-circled::before { border-color: var(--color-text-secondary); opacity: 0.1; }",
        ],
        ids=["ring-shifted-right", "ring-shifted-down", "ring-not-drawn", "ring-faded-to-nothing"],
    )
    def test_a_ring_not_drawn_where_it_says_is_caught(self, browser_page, host, plant) -> None:
        page = browser_page
        key, grid = host[2]["max"], GRIDS["max"]
        page.set_viewport_size({"width": 1440, "height": 900})

        def problems() -> list[str]:
            _board(page, host, key, grid, _marked(grid))
            _zoom_to_max(page)
            rings = _spread(_rings_for_test(page), 8)
            assert len(rings) >= 6
            return ring_in_place_problems(page, rings)

        assert problems() == [], "the matched control"
        anchor = ".player-board .player-clue-num.is-circled::before { border-color: var(--grid-ink); }"
        _plant(page, host, "player.css", anchor, anchor + plant)
        assert problems() != []


@pytest.mark.browser
class TestPublicCircles_TheInPlaceBandHasADeclaredResidue:
    @pytest.mark.parametrize(
        ("shift", "caught"),
        [(SHIFT_THE_CHECK_CANNOT_SEE_PX, False), (SHIFT_THE_CHECK_CATCHES_PX, True)],
        ids=["a-1px-shift-is-the-declared-residue", "a-1_5px-shift-just-past-it-is-caught"],
    )
    def test_the_in_place_residue_is_declared_and_a_shift_just_past_it_is_caught(self, browser_page, host, shift, caught) -> None:
        page = browser_page
        key, grid = host[2]["max"], GRIDS["max"]
        page.set_viewport_size({"width": 1440, "height": 900})

        def problems() -> list[str]:
            _board(page, host, key, grid, _marked(grid))
            _zoom_to_max(page)
            rings = _spread(_rings_for_test(page), 8)
            assert len(rings) >= 6
            return ring_in_place_problems(page, rings)

        assert problems() == [], "the matched control"
        anchor = ".player-board .player-clue-num.is-circled::before { border-color: var(--grid-ink); }"
        _plant(page, host, "player.css", anchor, anchor + f"\n.player-board .player-clue-num::before {{ transform: translateX({shift}px); }}")
        assert (problems() != []) is caught
