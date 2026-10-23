"""CARD-188 — the puzzle player circles a clue number once the marks settle it.

The rule (``static/solver_state.js`` ``circledNumbers`` / ``circledClues``)
reads only the player's marks and the payload's clues. In a line a cell is
dark (FILLED), white (EMPTY) or undecided; a closed run is a maximal dark run
with a white cell or the edge on each side. Rule A walks in from each edge,
circling a closed run whose length is the next clue number from that edge
and stopping at anything else; rule B circles every number when the closed
runs are exactly the clue; rule C (CARD-213) circles a number whose value
occurs exactly once in the line's clue when the line holds exactly one closed
run of that length, wherever in the line that run sits. A "0" clue is circled
only when every cell is white.

What each tier shows:

* **Pure module, in the browser** (``await import('/static/solver_state.js')``):
  the card's examples table (AC-2); the safety property against a brute force
  built here on ``tests/helpers/brute_force_oracle.py`` ``line_candidates``
  (AC-1); fully marked lines (AC-3); a board is its lines, and transposes
  (AC-4). Corpora are seeded ``random.Random`` (no ``hypothesis``), each
  asserting its own minimum counts.
* **Rule C** (CARD-213, the section after AC-4): the unique-value cases and
  their negatives, each negative paired with a positive control on the same
  marks so that "nothing is circled" cannot pass for a rule that never ran;
  the pre-card verdicts of the examples tables, kept as a frozen column
  (CARD-213 AC-5); and two properties against ``_rule_circles``, the rule
  block written again in Python from its prose (CARD-213 AC-7, G-4).
* **Player page** (real clicks and drags, CARD-160's loopback panel over a
  temp SQLite store): circles follow every commit and not a drag's preview
  (AC-5, AC-7), the owner's "2 2" case stays uncircled (AC-6), circling moves
  nothing (AC-8), and the circle is a visible round ring that clears its
  digits (AC-9).
"""

from __future__ import annotations

import random
import re

import pytest

from tests.helpers.brute_force_oracle import line_candidates
# CARD-271, G-2: the token predicate the design-system sweep is built on, so
# this card's one coloured value is judged by the same rule as every other.
from tests.test_admin_design_tokens import _STATIC as _TOKENS_STATIC
from tests.test_admin_design_tokens import _declared_values, _untokenised
from tests.test_puzzle_solver_marking import E, F, U, _button, _cell, _centre, _drag, _states
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _tight_row,
    _unique_grid,
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
        # CARD-213 rule C: "3" is unique in "3 1" and one closed run has that
        # length, so the length alone now settles it (this row read
        # [False, False] before that card).
        ((3, 1), ".WDDDW....", [True, False]),
        # The same marks under a clue in which no value is unique: there is
        # still no matching by length alone.
        ((3, 1, 3), ".WDDDW....", [False, False, False]),
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
    #: CARD-213: on two of these lines every clue value is unique and a closed
    #: run matches each, so rule C circles what rule A's walk refused (they
    #: read [False, False] before that card). Each keeps a twin whose clue
    #: repeats every value — rule C cannot fire there, so the walk's stop is
    #: still what the row shows.
    STOPS = [
        ((1, 1), "DDW.......", [False, False]),  # longer than c1: no circle
        ((1, 2), "DDWDW.....", [True, True]),  # rule A stops; rule C circles both
        ((1, 1, 2, 2), "DDWDW.....", [False, False, False, False]),  # the walk stops, and only the walk runs
        ((2, 1), ".....WDWDD", [True, True]),  # the same from the right edge
        ((2, 2, 1, 1), ".....WDWDD", [False, False, False, False]),
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
# CARD-213 — rule C: a value that occurs once in the line's clue
# ==========================================================================
#
# Rule C circles a clue number whose VALUE occurs exactly once in that line's
# clue as soon as the line holds exactly one closed run of that length: no
# other number can own that run, so the deduction needs no edge anchoring.
# Every negative below ("nothing is circled") is paired with a positive
# control over the SAME marks, so a rule that never ran at all cannot pass
# for a rule that correctly declined to fire.

#: "1 2 3 2 1" from the owner's note: the 3 (index 2) is the only value that
#: occurs once, so it is the only number rule C can ever circle here.
_OWNER_CLUE = (1, 2, 3, 2, 1)
#: Only the 3 of _OWNER_CLUE circled.
_ONLY_THE_THREE = [False, False, True, False, False]
_NOTHING = [False] * 5


def _closed_runs(marks):
    """(length, closed) of each dark run of `marks`, left to right. A run is
    closed when its neighbour on each side is a white cell or the line's
    edge."""
    runs, start = [], 0
    while start < len(marks):
        if marks[start] != "D":
            start += 1
            continue
        end = start
        while end < len(marks) and marks[end] == "D":
            end += 1
        closed = ((start == 0 or marks[start - 1] == "W")
                  and (end == len(marks) or marks[end] == "W"))
        runs.append((end - start, closed))
        start = end
    return runs


def _walk_in(clue, marks, numbers):
    """Rule A's walk over `marks` from its first cell, taking its clue
    numbers from `numbers` in order (the clue's indices in walk order): the
    left walk is called with the line and 0..n-1, the right walk with the
    reversed line and n-1..0. Returns the indices the walk circles."""
    circled, step = [], 0
    while step < len(marks) and len(circled) < len(clue):
        if marks[step] == "W":
            step += 1
            continue
        if marks[step] != "D":
            break  # undecided: the walk cannot see past it
        end = step
        while end < len(marks) and marks[end] == "D":
            end += 1
        if end < len(marks) and marks[end] != "W":
            break  # the run is not closed
        number = numbers[len(circled)]
        if end - step != clue[number]:
            break
        circled.append(number)
        step = end
    return circled


def _rule_circles(clue, marks, *, rule_c=True):
    """``solver_state.js``'s rule block written again here, from its prose
    rather than its code: rules A and B (CARD-188) and, unless `rule_c` is
    off, rule C (CARD-213). ``rule_c=False`` is the behaviour before this
    card — ``TestSolverClues_RuleCOnlyAddsToTheOldTable`` calibrates it
    against the committed pre-card verdicts of the two examples tables."""
    clue = list(clue)
    if clue == [0]:
        return [all(mark == "W" for mark in marks)]
    circled = [False] * len(clue)
    numbers = list(range(len(clue)))
    walked = _walk_in(clue, marks, numbers) + _walk_in(clue, marks[::-1], numbers[::-1])
    for number in walked:
        circled[number] = True
    runs = _closed_runs(marks)
    if all(closed for _, closed in runs) and [length for length, _ in runs] == clue:
        circled = [True] * len(clue)  # rule B
    if rule_c:
        closed = [length for length, is_closed in runs if is_closed]
        for number, value in enumerate(clue):
            if clue.count(value) == 1 and closed.count(value) == 1:
                circled[number] = True
    return circled


# --------------------------------------------------------------------------
# AC-1 — a unique length circles wherever its run is closed
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestSolverClues_UniqueLengthCirclesAnywhere:
    """CARD-213 AC-1 — "1 2 3 2 1" with one closed run of three and
    undecided cells on both sides of it: the 3 is circled and no other
    number is. Neither walk of rule A can reach that run (both stop at an
    undecided cell) and rule B needs the whole clue, so every circle in the
    table is rule C's — which the second test here is the control for."""

    LINES = [
        # (clue, marks, circled)
        (_OWNER_CLUE, "....WDDDW.........", _ONLY_THE_THREE),
        (_OWNER_CLUE, "........WDDDW.....", _ONLY_THE_THREE),
        # One cell in from the edge: the left walk still stops on the
        # undecided cell 0, so the circle is rule C's, not rule A's.
        (_OWNER_CLUE, ".WDDDW............", _ONLY_THE_THREE),
        # Another closed run, of a length that occurs twice: the 1s stay
        # uncircled and the 3 is unaffected by it.
        (_OWNER_CLUE, "...WDDDWWDW.......", _ONLY_THE_THREE),
        # Two unique values, each with one closed run: both are circled.
        ((1, 2, 3), "..WDW..WDDDW......", [True, False, True]),
    ]

    def test_the_unique_length_is_circled_where_its_run_is_closed(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        got = _numbers(browser_page, [(clue, marks) for clue, marks, _ in self.LINES])
        assert got == [circled for _, _, circled in self.LINES]

    def test_rules_a_and_b_circle_none_of_them(self, browser_page, live) -> None:
        """The control: without rule C the same lines circle nothing, so each
        row above is rule C's work and not a walk that happened to reach."""
        assert [_rule_circles(clue, marks, rule_c=False) for clue, marks, _ in self.LINES] \
            == [[False] * len(clue) for clue, _, _ in self.LINES]


# --------------------------------------------------------------------------
# AC-2 — a value that occurs twice never circles by length
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestSolverClues_RepeatedLengthDoesNotCircle:
    """CARD-213 AC-2 — the same clue with a closed run of TWO mid-line and
    undecided cells either side: "2" occurs twice in "1 2 3 2 1", so rule C
    cannot tell which of them the run is and circles nothing.

    The control is every one of those marks under "1 2 3", where 2 occurs
    once: there the 2 IS circled. Both assertions read the same marks, so
    "nothing is circled" cannot be a rule that never ran."""

    #: Each holds exactly one closed run of two and no closed run of three.
    MARKS = [
        "....WDDW..........",
        ".WDDW.............",
        "..WDDW...WDW......",
        "........WDDWWDDDDW",
    ]
    #: The clue that makes 2 unique, and what it circles on those marks.
    CONTROL = (1, 2, 3)
    CIRCLES_THE_TWO = [
        [False, True, False],
        [False, True, False],
        [True, True, False],  # the lone dark cell is a closed run of 1 too
        [False, True, False],
    ]

    def test_the_repeated_value_circles_nothing(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        got = _numbers(browser_page, [(_OWNER_CLUE, marks) for marks in self.MARKS])
        assert got == [_NOTHING] * len(self.MARKS)

    def test_the_same_marks_circle_a_two_that_occurs_once(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        got = _numbers(browser_page, [(self.CONTROL, marks) for marks in self.MARKS])
        assert got == self.CIRCLES_THE_TWO
        assert all(circled[1] for circled in got)  # the 2, in every row


# --------------------------------------------------------------------------
# AC-3 — two closed runs of the unique length circle nothing
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestSolverClues_AmbiguousUniqueLengthCirclesNothing:
    """CARD-213 AC-3 — "1 2 3 2 1" holding two (or three) closed runs of
    three: the marks are contradictory, and rule C circles neither — it must
    not take the first or the leftmost.

    Each is paired with a line of the same shape holding exactly ONE closed
    run of three, which does circle the 3: a rule that picked a run out of
    several would read the same on both halves of the pair, and a rule that
    never fired would read the same the other way."""

    PAIRS = [
        # (two or more closed runs of three, the same line with one)
        ("..WDDDW...WDDDW...", "..WDDDW..........."),
        ("WDDDWDDDWDDDW.....", "WDDDW............."),
        ("DDDW........WDDDW.", "DDDW.............."),
        ("WDDDW........WDDDW", ".........WWDDDW..."),
    ]

    def test_two_matching_runs_circle_nothing_and_one_circles_the_three(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        lines = [(_OWNER_CLUE, marks) for pair in self.PAIRS for marks in pair]
        got = _numbers(browser_page, lines)
        assert got[0::2] == [_NOTHING] * len(self.PAIRS)  # the ambiguous lines
        assert got[1::2] == [_ONLY_THE_THREE] * len(self.PAIRS)  # the controls


# --------------------------------------------------------------------------
# AC-4 — an open run is not a closed run
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestSolverClues_OpenRunDoesNotCircle:
    """CARD-213 AC-4 — a run of three dark cells with an undecided cell on
    one side is not closed, so rule C does not circle the 3; the run's own
    two neighbours are what "closed" means.

    Each row is paired with the same line whose open side is white instead:
    one cell apart, and that cell decides the circle."""

    PAIRS = [
        # (open, the same run closed)
        ("....WDDD..........", "....WDDDW........."),  # open on the right
        ("...DDDW...........", "..WDDDW..........."),  # open on the left
        ("....DDD...........", "...WDDDW.........."),  # open on both sides
        ("..........WDDD....", "..........WDDDW..."),
        # The far edge closes one side; the other is one undecided cell, and
        # however much of the line is decided elsewhere, open means open.
        ("WWWWWWWWWWWWWW.DDD", "WWWWWWWWWWWWWWWDDD"),
    ]

    def test_the_open_run_does_not_circle_and_closing_it_does(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        lines = [(_OWNER_CLUE, marks) for pair in self.PAIRS for marks in pair]
        got = _numbers(browser_page, lines)
        assert got[0::2] == [_NOTHING] * len(self.PAIRS)
        assert got[1::2] == [_ONLY_THE_THREE] * len(self.PAIRS)


# --------------------------------------------------------------------------
# AC-6 — the "0" clue keeps its own rule
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestSolverClues_ZeroClueRuleUnchanged:
    """CARD-213 AC-6 — a "0" clue is circled when every cell of the line is
    white and at no other time; rule C does not apply to it (its value, 0,
    is matched by no run of dark cells, and the line's dark runs are
    irrelevant to it).

    The all-white row is the control that can fail: drop the "0" branch in
    favour of rule C and it reads False. The last two rows are the same
    marks under "1", where rule C is the only rule that can fire — they show
    the rows above are a rule that declined, not a rule that is absent."""

    ZERO = [
        ((0,), "WWWWW", [True]),  # every cell white
        ((0,), "WW.WW", [False]),  # one undecided cell: not yet
        ((0,), ".....", [False]),
        ((0,), "WWDWW", [False]),  # a closed run of one, and still nothing
        ((0,), "..WDW.", [False]),
    ]
    CONTROL = [
        ((1,), "WWDWW", [True]),  # rule A reaches this one from both edges
        ((1,), "..WDW.", [True]),  # neither walk reaches it: rule C's circle
        ((1,), "WW.WW", [False]),  # no closed run at all
    ]

    def test_the_zero_clue_and_the_same_marks_under_a_one(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        rows = [*self.ZERO, *self.CONTROL]
        got = _numbers(browser_page, [(clue, marks) for clue, marks, _ in rows])
        assert got == [circled for _, _, circled in rows]


# --------------------------------------------------------------------------
# AC-5 / G-4 — the pre-card verdicts, and rule C only adds
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestSolverClues_RuleCOnlyAddsToTheOldTable:
    """CARD-213 AC-5 and G-4 — every line of the two examples tables above
    with the verdict the committed module gave it BEFORE this card, copied
    from that file. Rule C turns a False into a True on three of those lines
    and leaves the other twelve exactly as they were; it never takes a
    circle away.

    The snapshot is also what calibrates ``_rule_circles(..., rule_c=False)``,
    the rules-A-and-B reference the two properties below compare against."""

    #: (clue, marks) -> the circles before CARD-213.
    BEFORE = {
        ((2, 2), "...WDDW..."): [False, False],
        ((2, 2), "DDW......."): [True, False],
        ((2, 2), "WDDWWDDW.."): [True, True],
        ((2, 2), "DD.DD....."): [False, False],
        ((1, 1), ".WDW.WDW."): [True, True],
        ((1, 1, 1), "WDWD......"): [True, False, False],
        ((3, 1), "DDW....WDW"): [False, True],
        ((3, 1), ".WDDDW...."): [False, False],
        ((0,), "WWWWW"): [True],
        ((0,), "WW.WW"): [False],
        ((1, 1), "DDW......."): [False, False],
        ((1, 2), "DDWDW....."): [False, False],
        ((2, 1), ".....WDWDD"): [False, False],
        ((1, 2), "WWWWWWWWWD"): [True, False],
        ((2, 1), "DWWWWWWWWW"): [False, True],
    }
    #: The three lines rule C changes, and what it adds to each.
    ADDED = {
        ((3, 1), ".WDDDW...."): [True, False],
        ((1, 2), "DDWDW....."): [True, True],
        ((2, 1), ".....WDWDD"): [True, True],
    }

    def test_the_old_table_is_covered(self) -> None:
        """Every line of the snapshot is still a row of the two tables
        above, and the snapshot still holds all fifteen pre-card lines: it
        cannot drift away from the tables it is the history of. (The tables
        also carry rows added by this card, which have no pre-card verdict.)
        """
        rows = {(clue, marks) for clue, marks, _ in
                (*TestSolverClues_RuleExamples.ROWS, *TestSolverClues_RuleExamples.STOPS)}
        assert set(self.BEFORE) <= rows
        assert len(self.BEFORE) == 15
        assert set(self.ADDED) <= set(self.BEFORE)

    def test_rule_c_adds_three_circles_and_removes_none(self, browser_page, live) -> None:
        _blank_page(browser_page, live)
        rows = list(self.BEFORE)
        got = _numbers(browser_page, rows)
        changed = {}
        for (clue, marks), now in zip(rows, got):
            before = self.BEFORE[(clue, marks)]
            assert len(now) == len(before)
            assert all(b <= n for b, n in zip(before, now)), (clue, marks, before, now)
            if now != before:
                changed[(clue, marks)] = now
        assert changed == self.ADDED

    def test_the_reference_reproduces_the_pre_card_verdicts(self) -> None:
        """``_rule_circles(..., rule_c=False)`` was written from the rule
        block's prose; on all fifteen lines it agrees with what the module
        actually did before rule C existed, and with the module now once
        rule C is switched on."""
        assert {row: _rule_circles(*row, rule_c=False) for row in self.BEFORE} == self.BEFORE
        now = {row: _rule_circles(*row) for row in self.BEFORE}
        assert {row: verdict for row, verdict in now.items() if verdict != self.BEFORE[row]} == self.ADDED


# --------------------------------------------------------------------------
# G-4 (property) — rule C only adds, on a seeded corpus
# --------------------------------------------------------------------------


def _rule_c_lines(rng, size):
    """Lines built to put closed runs where rules A and B cannot reach them:
    a clue of 1..5 values drawn so that some lines have a unique value and
    some have none, marks that reveal a run and its two neighbours and leave
    the rest undecided, sometimes with a second matching run, sometimes with
    the run left open."""
    lines = []
    for k in range(size):
        length = rng.randint(6, 24)
        count = rng.randint(1, 5)
        if k % 5 == 0:  # every value repeated: rule C can never fire
            half = [rng.randint(1, 5) for _ in range(count)]
            clue = tuple(half + half)
        else:
            clue = tuple(rng.randint(1, 5) for _ in range(count))
        marks = ["."] * length
        for _ in range(rng.randint(1, 3)):
            run = rng.choice(clue)
            start = rng.randint(0, max(0, length - run))
            if start + run > length:
                continue
            for index in range(start, start + run):
                marks[index] = "D"
            for side in (start - 1, start + run):
                if 0 <= side < length:
                    marks[side] = "." if rng.random() < 0.25 else "W"
        if rng.random() < 0.25:  # some white noise elsewhere
            for index in range(length):
                if marks[index] == "." and rng.random() < 0.4:
                    marks[index] = "W"
        lines.append((clue, "".join(marks)))
    return lines


@pytest.mark.browser
def test_PropertyTest_SolverClues_RuleCOnlyAddsToRulesAAndB(browser_page, live) -> None:
    """CARD-213 G-4 — on a seeded corpus, circledNumbers equals the Python
    reference with rule C on, and every circle the reference gives with rule
    C OFF is still there: rule C only ever adds. The counts below keep the
    claim from being vacuous — the corpus has to contain lines rule C
    changes, lines it leaves alone, and lines whose clue repeats every value
    so that rule C cannot fire at all."""
    _blank_page(browser_page, live)
    lines = [*_rule_c_lines(random.Random(213), 2400), *_safety_corpus(random.Random(2131), 600)]
    got = []
    for chunk in range(0, len(lines), 2000):
        got += _numbers(browser_page, lines[chunk:chunk + 2000])

    added = untouched = no_unique_value = 0
    mismatched, removed = [], []
    for (clue, marks), now in zip(lines, got):
        before = _rule_circles(clue, marks, rule_c=False)
        after = _rule_circles(clue, marks)
        if now != after:
            mismatched.append((clue, marks, now, after))
        if any(b and not n for b, n in zip(before, now)):
            removed.append((clue, marks, before, now))
        added += now != before
        untouched += now == before
        no_unique_value += all(clue.count(value) > 1 for value in clue)
    assert mismatched == []
    assert removed == []
    assert len(lines) >= 3000, len(lines)
    assert added >= 500, added
    assert untouched >= 500, untouched
    assert no_unique_value >= 300, no_unique_value


# --------------------------------------------------------------------------
# AC-7 (property) — rule C is axis-independent
# --------------------------------------------------------------------------

_TRANSPOSE = """async ({ width, height, rows, columns, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { D: S.FILLED, W: S.EMPTY, '.': S.UNKNOWN };
  const board = (w, h, cells) => Object.freeze({ width: w, height: h, cells: Object.freeze(cells) });
  const plain = (c) => ({ rows: c.rows.map((l) => [...l]), columns: c.columns.map((l) => [...l]) });
  return boards.map((text) => {
    const cells = [...text].map((ch) => codes[ch]);
    const flipped = Array.from({ length: width * height },
      (_, i) => cells[(i % height) * width + Math.floor(i / height)]);
    return {
      upright: plain(S.circledClues(board(width, height, cells), rows, columns)),
      transposed: plain(S.circledClues(board(height, width, flipped), columns, rows)),
    };
  });
}"""


def _rule_c_boards(rng, width, height, count):
    """A random solution's clues, and boards that reveal each cell with a
    per-board probability — so closed runs turn up mid-line, with undecided
    cells between them and the edges, on both axes."""
    solution = [[rng.random() < 0.45 for _ in range(width)] for _ in range(height)]
    rows = [_encode(row) for row in solution]
    columns = [_encode(column) for column in zip(*solution)]
    boards = []
    for _ in range(count):
        reveal = rng.choice((0.5, 0.65, 0.8, 0.9))
        boards.append("".join(
            ("D" if cell else "W") if rng.random() < reveal else "."
            for row in solution for cell in row))
    return rows, columns, boards


@pytest.mark.browser
def test_PropertyTest_SolverClues_RuleCInvariantUnderTransposition(browser_page, live) -> None:
    """CARD-213 AC-7 — on a seeded corpus of boards and clue sets, the
    circles of the transposed board with its clue sets swapped are the
    circles of the upright board with its axes swapped: rule C reads a line,
    not a direction. Every line is also checked against the Python
    reference, and the corpus must contain enough lines that only rule C
    circles — otherwise the property would hold for a rule C that was never
    there."""
    _blank_page(browser_page, live)
    rng = random.Random(2132)
    lines = rule_c_only = rule_c_added = 0
    for width, height in [(12, 12), (18, 11), (9, 20)]:
        rows, columns, boards = _rule_c_boards(rng, width, height, 60)
        got = browser_page.evaluate(_TRANSPOSE, {
            "width": width, "height": height, "rows": rows, "columns": columns, "boards": boards})
        assert len(got) == len(boards) == 60
        for text, result in zip(boards, got):
            assert result["transposed"] == {"rows": result["upright"]["columns"],
                                            "columns": result["upright"]["rows"]}
            marks = {
                "rows": [text[r * width:(r + 1) * width] for r in range(height)],
                "columns": ["".join(text[r * width + c] for r in range(height)) for c in range(width)],
            }
            for axis, clues in (("rows", rows), ("columns", columns)):
                for clue, line, now in zip(clues, marks[axis], result["upright"][axis]):
                    before = _rule_circles(clue, line, rule_c=False)
                    assert now == _rule_circles(clue, line), (axis, clue, line, now)
                    lines += 1
                    rule_c_added += now != before
                    rule_c_only += any(now) and not any(before)
    # An equality, not a floor: the corpus is fully determined by its seed and
    # its shape list, so `>= 200` against a measured 4920 would let the corpus
    # shrink 24-fold in silence. Re-record this deliberately if the shapes move.
    assert lines == 4920, lines
    assert rule_c_added >= 150, rule_c_added
    assert rule_c_only >= 100, rule_c_only


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
        _button(page, "Reset board").click()
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


#: Desktop, and a phone (390 px: the <= 820 px cell floor is removed, so the
#: cell is whatever the fit (or the numeral floor) produces, CARD-193).
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
    1440 px (about 17 px) and at 390 px (about 14.4 px — CARD-193 removed the
    24 px phone floor below 820 px; this grid's two-digit column numbers
    still bind the 14.4 px numeral-driven column floor, CARD-196), where
    every row clue box is one cell tall and every number's ring has its
    horizontal and vertical centre within half a pixel of its digits' text-box centre (the
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
        # CARD-193: below 820 px the cell floor is removed, so at 390 the
        # measured value is this grid's 14.4 px numeral-driven column floor
        # (two-digit column numbers), not the old 24 px phone floor.
        assert cell == pytest.approx({1100: 14.4, 1440: 17.67, 390: 14.39}[viewport["width"]], abs=0.05), cell
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
    fully marked line circles everything), so both rings are live.

    At the floor and desktop viewports (cell 14.4 / 17.67 px, numeral above
    the 12 px floor) the gap between them is always positive (the rings
    touch, never overlap) but measures well under _RING_GAP (about
    0.125-0.141 px). At the phone viewport (CARD-193: the 24 px phone floor
    is gone, so this 15 x 15 board's cell is the fit, well under 20 px) the
    numeral sits at its 12 px floor (CARD-196) while the ring still scales
    with the now much smaller cell, so the two rings are no longer tight —
    the pair keeps the ordinary full _RING_GAP there instead, like every
    other pair; this is asserted below per viewport rather than as one
    shared bound. Each ring's OWN digit clearance (the >= 0.5 px bar from
    the cycle-1 F-001 fix) is unaffected either way and is asserted here
    too."""

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
        if viewport["width"] == 390:
            # CARD-193: below the 24 px phone floor this pair is no longer
            # tight — it keeps the ordinary full _RING_GAP, measured here at
            # about 5.4 px (well clear of the floor).
            assert gap >= _RING_GAP - 1 / 64, gap
        else:
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
    12 px. A 15 x 15 keeps its 0.6 x cell numerals on desktop (16.8 px); at
    the phone viewport (CARD-193 removed the 24 px phone floor, so this
    board's cell is now its fit, about 14 px — well under the 20 px a 12 px
    numeral needs) the 12 px floor itself binds instead of 0.6 x cell. A
    30 x 30 with a two-digit column number sits at the 12 px floor at
    1440 px and at 1100 px (its cell is 17.67 px and 14.4 px, so 0.6 x cell
    is 10.6 px and 8.6 px and the floor binds)."""

    def test_15x15_desktop_numerals_are_0_6_of_the_28_px_cell(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 1440, "height": 900})
        _open_player(browser_page, live)
        fonts = browser_page.evaluate(_NUMERALS)
        assert fonts and all(abs(f - 16.8) < 0.01 for f in fonts), sorted(set(fonts))

    def test_15x15_phone_numerals_sit_at_the_12px_floor(self, browser_page, live) -> None:
        """CARD-193 (renamed from ..._are_0_6_of_the_24_px_cell, which this
        board no longer measures: its phone cell is now the fit, not a 24 px
        floor, so 0.6 x cell would be under 12 px and the numeral floor binds
        instead — measured here, not assumed)."""
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open_player(browser_page, live)
        fonts = browser_page.evaluate(_NUMERALS)
        assert fonts and all(abs(f - 12) < 0.01 for f in fonts), sorted(set(fonts))

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


# ==========================================================================
# CARD-212 — a big board repeats its clues on BOTH sides of an axis
#
# Owner's doc "Nonograms - Print layout", 2026-10-13 (item 3). Row clues left
# AND right, column clues above AND below, so a player scrolled to the far
# edge of a big board still has clues in view. Each axis is decided on its
# own (W > 15 for the row clues, H > 15 for the column ones), and a duplicate
# is drawn only while the cells it leaves are at least 24 px on a side
# (solver.js DOUBLE_MIN_CELL — CARD-182's phone-fit minimum, read as a
# condition rather than the floor CARD-193 removed); otherwise the board keeps
# exactly today's rendering, CARD-193's mirror included (AC-6, over in
# tests/test_puzzle_solver_phone.py).
#
# The viewports below are MEASURED choices, not guesses: at 1920 x 1500 a
# 30 x 25 keeps 28 px cells with all four gutters drawn, at 1920 x 1080 a
# 30 x 12 keeps 28 px with both row gutters, and at 1440 x 900 the same
# 30 x 25 falls to 19.75 px doubled and so keeps its single gutters. Each
# number below is asserted where it matters, so a future change to the fit
# cannot quietly turn one of these cases into the other without a red test.
# ==========================================================================

#: AC-1 / AC-3 / AC-4 / AC-7: big on both axes (30 wide, 25 tall).
GRID_30x25 = _unique_grid(30, 25, seed=212)
#: AC-2: big on the row axis only (30 wide, 12 tall — 12 <= 15).
GRID_30x12 = _unique_grid(30, 12, seed=2121)

#: Room for all four gutters on a 30 x 25 (measured: 28 px cells), and room
#: for both row gutters on a 30 x 12 (measured: 28 px cells) while a 30 x 25
#: there can only afford the row pair (25.05 px).
ROOMY = {"width": 1920, "height": 1500}
WIDE = {"width": 1920, "height": 1080}
#: A laptop window, where doubling a 30 x 25 would leave 19.75 px cells: the
#: board keeps one gutter per axis (AC-1's "with room" clause, from the other
#: side).
LAPTOP = {"width": 1440, "height": 900}

#: Every clue box, in document order, with what this card gives it: the axis,
#: the line it belongs to (data-line), whether it is a duplicate (aria-hidden,
#: unlabelled), which side/end it draws on, and its numbers.
_GUTTERS = """() => {
  const table = document.querySelector('.player-board');
  const boxes = [...table.querySelectorAll('th.player-clue')].map((box) => ({
    axis: box.classList.contains('is-row') ? 'rows' : 'columns',
    line: Number(box.dataset.line),
    hidden: box.getAttribute('aria-hidden'),
    label: box.getAttribute('aria-label'),
    right: box.classList.contains('is-right'),
    below: box.closest('tfoot') !== null,
    numbers: [...box.querySelectorAll('.player-clue-num')].map((n) => n.textContent),
  }));
  return {
    boxes,
    mirrored: table.classList.contains('is-mirrored'),
    feet: table.querySelectorAll('tfoot tr').length,
    corners: [...table.querySelectorAll('.player-corner')].map((c) => ({
      right: c.classList.contains('is-right'), below: c.closest('tfoot') !== null })),
    cell: document.querySelector('td.player-cell').getBoundingClientRect().width,
  };
}"""


def _gutters(page):
    return page.evaluate(_GUTTERS)


def _lines(seen, axis, *, duplicate):
    """The numbers of each line's box in one gutter, in line order."""
    boxes = [b for b in seen["boxes"]
             if b["axis"] == axis and (b["hidden"] == "true") == duplicate]
    assert [b["line"] for b in boxes] == sorted(b["line"] for b in boxes), boxes
    return [b["numbers"] for b in boxes]


def _as_text(clues):
    return [[str(n) for n in clue] for clue in clues]


@pytest.mark.browser
class TestSolverClues_BigBoardRepeatsBothAxes:
    """AC-1 — a 30 x 25 on a viewport with room for both gutters: every row's
    clue appears left of AND right of the grid, every column's above AND
    below it, and the four corners that close the two bands are there."""

    def test_a_30x25_draws_both_gutters_on_both_axes(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(ROOMY)
        _open(page, live, live.store(GRID_30x25))

        seen = _gutters(page)

        rows, columns = _as_text([_encode(r) for r in GRID_30x25]), _as_text(
            [_encode(c) for c in zip(*GRID_30x25)])
        assert _lines(seen, "rows", duplicate=False) == rows
        assert _lines(seen, "rows", duplicate=True) == rows
        assert _lines(seen, "columns", duplicate=False) == columns
        assert _lines(seen, "columns", duplicate=True) == columns
        # Left and right, above and below — read off the boxes' own geometry
        # markers rather than from their count alone.
        assert [b["right"] for b in seen["boxes"] if b["axis"] == "rows"] == [False, True] * 25
        assert {b["below"] for b in seen["boxes"] if b["axis"] == "columns" and b["hidden"]} == {True}
        assert {b["below"] for b in seen["boxes"] if b["axis"] == "columns" and not b["hidden"]} == {False}
        assert seen["feet"] == 1
        assert sorted((c["right"], c["below"]) for c in seen["corners"]) == [
            (False, False), (False, True), (True, False), (True, True)]
        assert seen["mirrored"] is False
        # The room it takes: 28 px cells, the cap, well over the 24 px the
        # duplicate is conditional on — and all four gutters FIT: the fitted
        # cell is charged for both bands of each doubled axis (admin.css
        # --player-row-gutters / --player-col-gutters), so the stage does not
        # scroll in either direction on a board that was asked to grow two
        # extra bands.
        assert seen["cell"] == pytest.approx(28, abs=0.01), seen["cell"]
        fit = page.evaluate(
            """() => {
              const stage = document.querySelector('.player-stage');
              return { overflowX: stage.scrollWidth - stage.clientWidth,
                       overflowY: stage.scrollHeight - stage.clientHeight,
                       page: document.scrollingElement.scrollWidth, viewport: innerWidth };
            }"""
        )
        assert fit["overflowX"] <= 0 and fit["overflowY"] <= 0, fit
        assert fit["page"] <= fit["viewport"], fit

    def test_the_doubled_board_is_fitted_for_both_of_its_bands(self, browser_page, live) -> None:
        """The cell is charged for the bands that are actually drawn. At
        1700 x 1500 the same 30 x 25 doubles both axes and the FIT sets the
        cell (24.53 px, under the 28 px cap), which is where fitting the
        board as if it had one band of each would show: the two extra bands
        are about 330 px apiece, so the board would hang a third of the way
        out of the stage instead of ending within the pixel or two of
        per-box rounding that a single-gutter board already carries on
        main (measured there: 1 px at 1024 x 768 and at 1440 x 900).
        """
        page = browser_page
        page.set_viewport_size({"width": 1700, "height": 1500})
        _open(page, live, live.store(GRID_30x25))

        seen = _gutters(page)
        fit = page.evaluate(
            """() => {
              const stage = document.querySelector('.player-stage');
              return { overflowX: stage.scrollWidth - stage.clientWidth,
                       stage: stage.clientWidth,
                       table: document.querySelector('.player-board').getBoundingClientRect().width };
            }"""
        )

        assert len(_lines(seen, "rows", duplicate=True)) == 25
        assert len(_lines(seen, "columns", duplicate=True)) == 30
        assert 24 <= seen["cell"] < 28, seen["cell"]  # the fit, not the cap
        # Measured: a 1402.34 px table in a 1400 px stage, which Chromium
        # reports as 2 or 3 px of integer scroll overflow from run to run
        # (scrollWidth is whole pixels; the table's own box is the stable
        # number of the two). The bound is that rounding, not a budget:
        # fitted for one band instead of two, this board measures some
        # 190 px past the stage.
        assert fit["table"] <= fit["stage"] + 3, fit
        assert fit["overflowX"] <= 3, fit

    def test_the_doubled_board_is_fitted_for_both_of_its_column_bands(self, browser_page, live) -> None:
        """The same, down the other axis: a 25 x 20 at 1920 x 1080 doubles
        both axes with the HEIGHT setting the cell (24.33 px), so the board
        ends within a few pixels of the stage's own visible height instead of
        a whole second column band (14 rows of numbers, some 340 px) past it.
        Measured here: 5 px of stage overflow. That is the known residue of
        the column band against the stage's own height (this card's open
        item, and the same order as the 3-5 px a single-gutter board already
        has at this viewport), NOT a budget — so the bound below sits just
        above the measurement rather than at twice it, and doubling the
        residue reds it.
        """
        page = browser_page
        page.set_viewport_size(WIDE)
        _open(page, live, live.store(_unique_grid(25, 20, seed=2123)))

        seen = _gutters(page)
        fit = page.evaluate(
            """() => {
              const stage = document.querySelector('.player-stage');
              return { overflowY: stage.scrollHeight - stage.clientHeight,
                       stage: stage.clientHeight };
            }"""
        )

        assert len(_lines(seen, "rows", duplicate=True)) == 20
        assert len(_lines(seen, "columns", duplicate=True)) == 25
        assert 24 <= seen["cell"] < 28, seen["cell"]  # the fit, not the cap
        assert fit["overflowY"] <= 6, fit

    def test_the_same_board_keeps_one_gutter_per_axis_on_a_laptop(self, browser_page, live) -> None:
        """AC-1's "with room" clause from the other side: at 1440 x 900 the
        doubled layout would leave 19.75 px cells, so this board draws
        exactly today's single gutters instead — and keeps the 19.75 px."""
        page = browser_page
        page.set_viewport_size(LAPTOP)
        _open(page, live, live.store(GRID_30x25))

        seen = _gutters(page)

        assert len(_lines(seen, "rows", duplicate=False)) == 25
        assert _lines(seen, "rows", duplicate=True) == []
        assert _lines(seen, "columns", duplicate=True) == []
        assert seen["feet"] == 0
        assert seen["cell"] == pytest.approx(19.75, abs=0.05), seen["cell"]


@pytest.mark.browser
class TestSolverClues_AxesDoubleIndependently:
    """AC-2 — a 30 x 12: the row clues are doubled and the column clues are
    not, because 12 is not past the 15 the row axis is past. The same
    viewport doubles BOTH axes of a 25 x 20 (also 20 rows deep, but tall
    enough to be eligible), so the asymmetry is the board's, not the
    viewport's."""

    def test_a_30x12_doubles_its_rows_only(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(WIDE)
        _open(page, live, live.store(GRID_30x12))

        seen = _gutters(page)

        rows = _as_text([_encode(r) for r in GRID_30x12])
        assert _lines(seen, "rows", duplicate=False) == rows
        assert _lines(seen, "rows", duplicate=True) == rows
        assert len(_lines(seen, "columns", duplicate=False)) == 30
        assert _lines(seen, "columns", duplicate=True) == []
        assert seen["feet"] == 0
        assert [(c["right"], c["below"]) for c in seen["corners"]] == [(False, False), (True, False)]
        assert seen["cell"] == pytest.approx(28, abs=0.01), seen["cell"]

    def test_a_25x20_at_the_same_viewport_doubles_both(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(WIDE)
        _open(page, live, live.store(_unique_grid(25, 20, seed=2123)))

        seen = _gutters(page)

        assert len(_lines(seen, "rows", duplicate=True)) == 20
        assert len(_lines(seen, "columns", duplicate=True)) == 25
        assert seen["feet"] == 1


@pytest.mark.browser
class TestSolverClues_DuplicateReadsTheSameSequence:
    """AC-3 — a duplicate gutter is a repetition, never a mirror of the
    sequence: line by line, in line order, its numbers are its twin's, and a
    bottom column box reads top to bottom like the top one. Checked against
    the payload's own clues (the embedded compute_clues JSON, G-1), not only
    against the other gutter, so a pair that is equal and both wrong fails."""

    def test_both_gutters_read_the_payload_in_the_same_order(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(ROOMY)
        _open(page, live, live.store(GRID_30x25))

        seen = _gutters(page)
        payload = page.evaluate("[window.puzzlePlayer.payload.rows, window.puzzlePlayer.payload.columns]")

        for axis, clues in (("rows", payload[0]), ("columns", payload[1])):
            first = _lines(seen, axis, duplicate=False)
            second = _lines(seen, axis, duplicate=True)
            assert first == _as_text(clues)
            assert second == first
            # Not reversed — a line whose clue is not a palindrome would read
            # the same either way otherwise.
            assert any(line != line[::-1] for line in first), axis


@pytest.mark.browser
class TestSolverClues_DuplicateIsAriaHidden:
    """AC-7 — the duplicate is a visual repetition, so the accessibility tree
    exposes each clue exactly once: every box of the second gutter is
    aria-hidden and carries no aria-label, and the labelled boxes are exactly
    one per line per axis, with the labels CARD-160 defined."""

    def test_each_clue_is_exposed_once(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(ROOMY)
        _open(page, live, live.store(GRID_30x25))

        seen = _gutters(page)

        labelled = [b for b in seen["boxes"] if b["hidden"] is None]
        hidden = [b for b in seen["boxes"] if b["hidden"] == "true"]
        assert len(labelled) == 30 + 25 and len(hidden) == 30 + 25
        assert all(b["label"] is None for b in hidden), hidden[:3]
        assert [b["label"] for b in labelled if b["axis"] == "rows"] == [
            f"Row {line + 1}: {' '.join(str(n) for n in _encode(GRID_30x25[line]))}" for line in range(25)]
        assert [b["label"] for b in labelled if b["axis"] == "columns"] == [
            f"Column {line + 1}: {' '.join(str(n) for n in _encode(col))}"
            for line, col in enumerate(zip(*GRID_30x25))]
        # Read the same way a screen reader walks the table: nothing inside an
        # aria-hidden subtree counts, so every clue is named once.
        names = page.evaluate(
            """() => [...document.querySelectorAll('th.player-clue')]
                 .filter((box) => box.closest('[aria-hidden="true"]') === null)
                 .map((box) => box.getAttribute('aria-label'))"""
        )
        assert len(names) == 55 and all(name for name in names)


@pytest.mark.browser
class TestSolverClues_CirclesPaintBothGutters:
    """AC-4 — CARD-188's circle is a property of a clue NUMBER, so on a
    doubled board both of that number's spans carry .is-circled, and both
    lose it when the marks change. Checked on a 30 x 25 with all four
    gutters drawn, so the row axis and the column axis are both covered, and
    with the ring itself measured on the duplicate: a duplicate that does not
    circle is worse than no duplicate, and so is one whose ring is painted
    twice (the rules are keyed on the span's own class, so the duplicate's
    ring is one ring, the same width as its twin's)."""

    def test_both_spans_circle_and_uncircle_together(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(ROOMY)
        problems = _watch_problems(page, live)
        _open(page, live, live.store(GRID_30x25))
        assert _gutters(page)["feet"] == 1

        # Nothing is marked: no number in either gutter is circled.
        assert _twins(page) != []
        assert [t for t in _twins(page) if any(t["circled"])] == []

        # The whole solution: every line settles, so every number circles —
        # in both gutters, and never in only one of them.
        _set(page, [F if on else E for line in GRID_30x25 for on in line])
        twins = _twins(page)
        assert len(twins) == sum(len(_encode(r)) for r in GRID_30x25) + sum(
            len(_encode(c)) for c in zip(*GRID_30x25))
        assert [t for t in twins if t["circled"] != [True, True]] == []
        # The ring is drawn once per span, the same size in both gutters.
        assert [t for t in twins if t["rings"][0] != t["rings"][1]] == []
        ink = page.evaluate(_GRID_INK)
        assert ink.startswith("rgb"), ink
        assert [t for t in twins if t["rings"][0]["width"] <= 0
                or t["rings"][0]["colour"] != ink] == [], twins[0]

        # Rubbing the marks out again clears both spans, never one of them:
        # the circles follow the board, in both gutters (a blank board settles
        # nothing). setBoard, not undo — _set starts a fresh history, so
        # there is nothing to undo after one.
        _set(page, [U] * (30 * 25))
        assert [t for t in _twins(page) if t["circled"] != [False, False]] == []
        assert problems == []


#: Every clue number of a doubled board as the pair of spans that show it:
#: the two gutters' .is-circled flags and the ring their ::before draws.
_TWINS = """() => {
  const twins = [];
  for (const kind of ['row', 'col']) {
    const boxes = [...document.querySelectorAll(`th.player-clue.is-${kind}`)];
    const byLine = new Map();
    for (const box of boxes) {
      const line = Number(box.dataset.line);
      if (!byLine.has(line)) byLine.set(line, []);
      byLine.get(line).push([...box.querySelectorAll('.player-clue-num')]);
    }
    for (const [line, gutters] of byLine) {
      if (gutters.length !== 2) return [];  // not a doubled axis: refuse
      gutters[0].forEach((span, k) => {
        const ring = (s) => {
          const look = getComputedStyle(s, '::before');
          return { width: parseFloat(look.borderTopWidth), colour: look.borderTopColor,
                   size: `${look.width}x${look.height}` };
        };
        twins.push({
          kind, line, k,
          circled: gutters.map((spans) => spans[k].classList.contains('is-circled')),
          rings: gutters.map((spans) => ring(spans[k])),
        });
      });
    }
  }
  return twins;
}"""


def _twins(page):
    return page.evaluate(_TWINS)


@pytest.mark.browser
class TestSolverClues_SmallBoardUnchanged:
    """AC-5 — a 15 x 15 is past neither side's 15, so it draws exactly what it
    drew before this card: one top gutter, one left gutter, one corner, no
    duplicate, no aria-hidden box, and no <tfoot> — at a viewport with room to
    spare for duplicates, which is where a wrong threshold would show."""

    @pytest.mark.parametrize("viewport", [ROOMY, LAPTOP, {"width": 390, "height": 844}],
                             ids=["roomy", "laptop", "phone"])
    def test_a_15x15_draws_one_gutter_per_axis(self, browser_page, live, viewport) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open_player(page, live)

        seen = _gutters(page)

        assert _lines(seen, "rows", duplicate=False) == _as_text(ROW_CLUES)
        assert _lines(seen, "columns", duplicate=False) == _as_text(COLUMN_CLUES)
        assert [b for b in seen["boxes"] if b["hidden"] is not None] == []
        assert [b for b in seen["boxes"] if b["right"] or b["below"]] == []
        assert seen["feet"] == 0
        assert [(c["right"], c["below"]) for c in seen["corners"]] == [(False, False)]
        assert seen["mirrored"] is False


_FRAMES = """() => {
  const px = (el, side) => parseFloat(getComputedStyle(el)[`border${side}Width`]);
  const table = document.querySelector('.player-board');
  const box = (sel, i = 0) => [...table.querySelectorAll(sel)][i];
  const sides = (el) => ({ left: px(el, 'Left'), right: px(el, 'Right'),
                           top: px(el, 'Top'), bottom: px(el, 'Bottom') });
  const bodyRows = [...table.querySelectorAll('tbody tr')];
  const lastRow = [...bodyRows.at(-1).querySelectorAll('td.player-cell')];
  const firstRow = [...bodyRows[0].querySelectorAll('td.player-cell')];
  const rowClues = (tr) => [...tr.querySelectorAll('th.player-clue.is-row')];
  const numberBand = (sel) => {
    const clue = box(sel);
    const numbers = [...clue.querySelectorAll('.player-clue-num')];
    const b = clue.getBoundingClientRect();
    return { aboveFirst: numbers[0].getBoundingClientRect().top - b.top,
             belowLast: b.bottom - numbers.at(-1).getBoundingClientRect().bottom };
  };
  return {
    rowLeft: sides(rowClues(bodyRows[0])[0]),
    rowRight: sides(rowClues(bodyRows[0])[1]),
    colTop: sides(box('thead th.player-clue.is-col')),
    colBottom: sides(box('tfoot th.player-clue.is-col')),
    cornerTopLeft: sides(box('thead .player-corner', 0)),
    cornerTopRight: sides(box('thead .player-corner', 1)),
    cornerBottomLeft: sides(box('tfoot .player-corner', 0)),
    cornerBottomRight: sides(box('tfoot .player-corner', 1)),
    lastCellOfRow: sides(firstRow.at(-1)),
    lastRowOfCells: [...new Set(lastRow.map((td) => px(td, 'Bottom')))],
    colRight: firstRow.map((td) => px(td, 'Right')),
    rowBottom: bodyRows.map((tr) => px(rowClues(tr)[0], 'Bottom')),
    topBand: numberBand('thead th.player-clue.is-col'),
    bottomBand: numberBand('tfoot th.player-clue.is-col'),
  };
}"""


@pytest.mark.browser
class TestSolverClues_DoubledFramesReadOnAllFourSides:
    """"What to implement" item 6 — with a gutter on each side of each axis,
    the heavy/thin rule pattern still reads correctly on all four sides.
    Every heavy line of the single-gutter board has exactly one counterpart
    here, drawn by the box that is now on that side; no line is doubled (two
    adjacent heavy borders would read as one twice as thick) and none goes
    missing.

    The ":last-child" rules admin.css relies on for the grid's right frame and
    the top band's right frame stop matching once a duplicate follows the
    cells (CARD-193 met this first, for the mirror); here they are replaced by
    the .is-right boxes' own left borders. Below the grid, the opposite: the
    last cell row's heavy bottom border IS the boundary, so the <tfoot> boxes
    draw no top border at all.
    """

    def test_the_rules_around_a_30x25_with_four_gutters(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(ROOMY)
        _open(page, live, live.store(GRID_30x25))
        assert _gutters(page)["feet"] == 1

        seen = page.evaluate(_FRAMES)
        thin = min(seen["colRight"])
        heavy = max(seen["colRight"])
        assert heavy > thin > 0

        # Left/right row gutters: the heavy boundary faces the grid on each
        # side, the thin edge faces out.
        assert (seen["rowLeft"]["right"], seen["rowLeft"]["left"]) == (heavy, thin)
        assert (seen["rowRight"]["left"], seen["rowRight"]["right"]) == (heavy, thin)
        # Top/bottom column gutters: the same, turned ninety degrees — except
        # that below the grid the boundary is the cells' own heavy bottom
        # border, so the gutter adds none of its own.
        assert (seen["colTop"]["bottom"], seen["colTop"]["top"]) == (heavy, thin)
        assert (seen["colBottom"]["top"], seen["colBottom"]["bottom"]) == (0, thin)
        assert seen["lastRowOfCells"] == [heavy]

        # The grid's own right frame moved onto the right gutter's left
        # border, so the last column's cells keep the thin rule (CARD-193's
        # mirrored case, now on a board that has both gutters).
        assert seen["lastCellOfRow"]["right"] == thin
        assert [c for c in range(29) if seen["colRight"][c] > thin] == [4, 9, 14, 19, 24]
        assert [r for r in range(24) if seen["rowBottom"][r] > min(seen["rowBottom"])] == [4, 9, 14, 19]

        # The four corners: each closes its own band with one heavy line
        # toward the grid, and draws nothing on the table's outer edges.
        assert seen["cornerTopLeft"] == {"left": 0, "right": heavy, "top": 0, "bottom": heavy}
        assert seen["cornerTopRight"] == {"left": heavy, "right": 0, "top": 0, "bottom": heavy}
        assert seen["cornerBottomLeft"] == {"left": 0, "right": heavy, "top": 0, "bottom": 0}
        assert seen["cornerBottomRight"] == {"left": heavy, "right": 0, "top": 0, "bottom": 0}

        # The numbers of each column gutter sit against the grid, so a short
        # clue leaves its empty room on the OUTER side: the top band's last
        # number ends on its box's (heavy) bottom border, the bottom band's
        # first number starts on its box's top edge, which draws no border at
        # all. Both bands are deeper than the clue measured here, so the room
        # left over is really on the far side and not merely absent.
        assert seen["topBand"]["belowLast"] == pytest.approx(heavy, abs=0.5), seen["topBand"]
        assert seen["topBand"]["aboveFirst"] > 1, seen["topBand"]
        assert seen["bottomBand"]["aboveFirst"] == pytest.approx(0, abs=0.5), seen["bottomBand"]
        assert seen["bottomBand"]["belowLast"] > 1, seen["bottomBand"]


_BAND_RINGS = """() => {
  const rings = [];
  for (const box of document.querySelectorAll('th.player-clue.is-row')) {
    const b = box.getBoundingClientRect();
    const style = getComputedStyle(box);
    const inside = { left: b.left + parseFloat(style.borderLeftWidth),
                     right: b.right - parseFloat(style.borderRightWidth) };
    [...box.querySelectorAll('.player-clue-num')].forEach((span, k) => {
      const r = span.getBoundingClientRect(), ring = getComputedStyle(span, '::before');
      const left = r.left + parseFloat(ring.left);
      rings.push({
        right: box.classList.contains('is-right'), line: Number(box.dataset.line), k,
        clear: { left: left - inside.left,
                 right: inside.right - (left + parseFloat(ring.width) + 2 * parseFloat(ring.borderTopWidth)) },
      });
    });
  }
  return rings;
}"""


@pytest.mark.browser
class TestSolverClues_RowRingsStayInsideTheirOwnBand:
    """A row number's ring is wider than its digits, and the 1.45 ch gap each
    number keeps is where that width goes. In a gutter on the RIGHT of the
    grid the gap has to be on the other side of the number, or the first
    ring — the one against the grid — is drawn over the board's heavy frame
    and the cells behind it (seen on the duplicate gutter before admin.css
    mirrored the margin; CARD-193's phone mirror had it too).

    So: in a left-hand gutter no ring crosses the box's inner (right) edge,
    and in a right-hand gutter no ring crosses its inner (left) edge. The
    outer edge of either is the board's own outside, where a ring may still
    reach into the page's margin as it always has — that is not asserted
    here, only the edge that faces the grid.
    """

    def test_no_ring_reaches_across_the_edge_that_faces_the_grid(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(ROOMY)
        _open(page, live, live.store(GRID_30x25))
        assert len(_lines(_gutters(page), "rows", duplicate=True)) == 25

        rings = page.evaluate(_BAND_RINGS)

        left = [r for r in rings if not r["right"]]
        right = [r for r in rings if r["right"]]
        assert len(left) == len(right) == sum(len(_encode(row)) for row in GRID_30x25)
        assert [r for r in left if r["clear"]["right"] < 0] == []
        assert [r for r in right if r["clear"]["left"] < 0] == []

    def test_the_phone_mirrors_single_right_hand_gutter_too(self, browser_page, live) -> None:
        """CARD-193's mirror is the same geometry and had the same defect
        for a week before this card shared the rule with it: on a 390 px
        phone every row-clue box is a right-hand one, and before the margin
        was mirrored the first ring of each crossed into the cells (measured
        at review: -2.72 px worst case, +7.75 px at HEAD). Pinned here, on
        the mirror itself, so the fix cannot be lost on the board that has
        carried the bug the longest."""
        page = browser_page
        page.set_viewport_size({"width": 390, "height": 844})
        _open(page, live, live.store(_unique_grid(30, 30, seed=19330)))
        assert page.evaluate("document.querySelector('.player-board').classList.contains('is-mirrored')")

        rings = page.evaluate(_BAND_RINGS)

        assert rings and all(r["right"] for r in rings)  # mirrored: no left gutter
        assert [r for r in rings if r["clear"]["left"] < 0] == []


#: One entry per board solver.js built, and what it settled on (CARD-212:
#: drawBoard leaves a performance mark per board, DRAW_MARK).
_DRAWS = """() => ({
  draws: performance.getEntriesByName('nonogram-player-board-draw').length,
  duplicates: document.querySelectorAll('th.player-clue[aria-hidden="true"]').length,
  cell: document.querySelector('td.player-cell').getBoundingClientRect().width,
})"""

#: The laptop viewport every browser test that never calls set_viewport_size
#: runs at — Playwright's default, and the one most of this suite uses.
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}

#: Mid-size boards: big on the row axis, small enough that the row clues DO
#: double at DEFAULT_VIEWPORT (measured: 26.88 px and, for the 22-wide, a
#: plain board at 24.59 px whose doubled rung misses the bar). This is the
#: band the card's other tests leave out — see the class below.
GRID_20x12 = _unique_grid(20, 12, seed=2124)
GRID_22x14 = _unique_grid(22, 14, seed=2125)


@pytest.mark.browser
class TestSolverClues_TheLadderStopsAtTheFirstRungThatFits:
    """The layout is chosen by drawing a candidate and measuring it, so the
    question "how many boards did that cost?" is a real one: building a
    30 x 30 is ~900 cells and a forced layout. solver.js draws TODAY'S
    rendering first and stops there when it is already under the bar —
    doubling only ever takes room away, so no rung above a plain board that
    is too small can qualify — and when a doubled rung is tried and misses,
    the plain board already drawn is put back rather than built again.

    Measured before the early-out, a 30 x 30 at this viewport took four
    draws and ~810 ms to an interactive board; it now takes one and ~125 ms.
    The counts below are asserted exactly, because they are the property —
    a timing would be flaky and would not say what is meant.
    """

    @pytest.mark.parametrize(
        "name, grid, viewport, draws, duplicates",
        [
            # Nothing can be afforded: one draw, and it is the board that stays.
            ("30x30 on a laptop", _unique_grid(30, 30, seed=19330), DEFAULT_VIEWPORT, 1, 0),
            ("30x25 on a laptop", GRID_30x25, LAPTOP, 1, 0),
            # Never eligible on either axis: a ladder of one rung.
            ("15x15 on a laptop", _unique_grid(15, 15, seed=182), DEFAULT_VIEWPORT, 1, 0),
            # The plain board clears the bar, the doubled rung does not: the
            # plain one is re-inserted, not rebuilt, so this is 2 and not 3.
            ("22x14 on a laptop", GRID_22x14, DEFAULT_VIEWPORT, 2, 0),
            # Afforded on the first rung tried: the plain board plus it.
            ("20x12 on a laptop", GRID_20x12, DEFAULT_VIEWPORT, 2, 12),
            ("30x12 wide", GRID_30x12, WIDE, 2, 12),
            ("30x25 roomy", GRID_30x25, ROOMY, 2, 55),
        ],
        ids=lambda value: value if isinstance(value, str) else "",
    )
    def test_the_board_is_built_as_few_times_as_the_answer_needs(
        self, browser_page, live, name, grid, viewport, draws, duplicates
    ) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open(page, live, live.store(grid))

        seen = page.evaluate(_DRAWS)

        assert (seen["draws"], seen["duplicates"]) == (draws, duplicates), (name, seen)


@pytest.mark.browser
class TestSolverClues_MidSizeBoardsDoubleOnAnOrdinaryLaptop:
    """The band the 24 px bar actually switches on at the suite's default
    1280 x 720 — boards from 16 to about 22 columns — which the card's other
    cases (1920 x 1500, 1920 x 1080, 1700 x 1500, 1440 x 900, 390 x 844)
    step over. A 20 x 12 there draws both row gutters at 26.88 px cells; a
    22 x 14, whose doubled rung measures just under the bar, draws one. Both
    are asserted, so the boundary is covered from each side rather than
    assumed, and the duplicate's numbers and its fifth-line rules are checked
    where most players will actually meet them.
    """

    def test_a_20x12_draws_both_row_gutters_and_reads_the_same(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(DEFAULT_VIEWPORT)
        _open(page, live, live.store(GRID_20x12))

        seen = _gutters(page)

        rows = _as_text([_encode(row) for row in GRID_20x12])
        assert _lines(seen, "rows", duplicate=False) == rows
        assert _lines(seen, "rows", duplicate=True) == rows
        assert _lines(seen, "columns", duplicate=True) == []  # 12 rows: not eligible
        assert seen["feet"] == 0
        assert seen["cell"] == pytest.approx(26.88, abs=0.05), seen["cell"]
        # The heavy fifth-line rules read the same in both gutters (the
        # duplicate carries .major-below exactly as its twin does).
        heavy = page.evaluate(
            """() => {
              const px = (el) => parseFloat(getComputedStyle(el).borderBottomWidth);
              const gutters = [[], []];
              const seen = new Map();
              for (const box of document.querySelectorAll('th.player-clue.is-row')) {
                const line = Number(box.dataset.line);
                const index = seen.get(line) ?? 0;
                seen.set(line, index + 1);
                gutters[index][line] = px(box);
              }
              return gutters;
            }"""
        )
        thin = min(heavy[0])
        assert heavy[0] == heavy[1], heavy
        assert [r for r in range(11) if heavy[0][r] > thin] == [4, 9]

    def test_a_22x14_whose_doubled_rung_misses_the_bar_draws_one(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(DEFAULT_VIEWPORT)
        _open(page, live, live.store(GRID_22x14))

        seen = _gutters(page)
        # Why this board draws one gutter, measured rather than assumed: the
        # plain board clears the 24 px bar and the doubled rung does not.
        # Measured here the margins are thin — 24.59 plain (+0.59) and 23.31
        # doubled (-0.69) — and 0.59 px on 22 columns is about 13 px of
        # stage, so a platform with classic 15 px scrollbars would land on
        # the other side of the bar. This assertion is what says so: if it
        # fails, this window is narrower here than it is on the machine the
        # numbers were taken on, and the ladder is behaving correctly.
        bar = page.evaluate(
            """() => {
              const table = document.querySelector('.player-board');
              const cell = () => document.querySelector('td.player-cell').getBoundingClientRect().width;
              const plain = cell();
              table.style.setProperty('--player-row-gutters', 2);
              const doubled = cell();
              table.style.setProperty('--player-row-gutters', 1);
              return { plain, doubled };
            }"""
        )
        assert bar["doubled"] < 24 <= bar["plain"], bar

        assert _lines(seen, "rows", duplicate=True) == []
        assert seen["feet"] == 0
        assert seen["cell"] == pytest.approx(24.59, abs=0.05), seen["cell"]


# ==========================================================================
# CARD-271 — the clues stay in view whatever the fit ladder decides
#
# Owner's bug report, 2026-10-22: "clues sometimes are missed at the bottom
# and at the left for big puzzles". CARD-212's duplicates answer that only
# while they FIT, and the biggest boards are the ones they do not fit: at
# 1280 x 720 a 30 x 30 is drawn plain (one gutter per axis) and that one
# gutter scrolls out of .player-stage. So each axis now keeps ONE gutter in
# view — the labelled one, never the duplicate — by sticking it to the
# stage's scrollport (solver.js .is-stuck-col / .is-stuck-row, admin.css
# "Clue gutters that stay in view").
#
# .player-stage IS the scroll container these resolve against, measured
# rather than assumed: see TestSolverClues_TheStageIsTheScrollContainer
# below, which walks the table's ancestors and asserts the stage is the only
# one of them that scrolls.
#
# The viewports below are measured choices (30 x 30, seed 19330, the board
# the ladder draws plain at every one of them):
#
#   1280 x 720   stage overflow (0, 91) against a 135.39 px column band and
#                a 272.16 px row band: the column band is scrolled PARTLY
#                out, and nothing scrolls sideways at all
#   1280 x 600   overflow (0, 211): the whole column band goes, which is the
#                owner's "missed at the bottom" on a desktop
#   900 x 700    overflow (104, 111): the only desktop viewport measured
#                where a plain board scrolls SIDEWAYS too (above 820 px, so
#                CARD-193's mirror does not hold — the row band is on the
#                left, and 104 px of it is what scrolls away)
#   390 x 844    the mirror: see tests/test_puzzle_solver_phone.py
#   300 % zoom   overflow (900, 1220) on both axes: see
#                tests/test_puzzle_solver_zoom.py
# ==========================================================================

#: The board every CARD-271 case here uses: a 30 x 30, which the ladder draws
#: plain (one gutter per axis) at every viewport below — pinned by
#: TestSolverClues_TheLadderStopsAtTheFirstRungThatFits's first row.
GRID_30x30 = _unique_grid(30, 30, seed=19330)

#: Desktop, column band partly scrolled out; the card's AC-1 viewport.
LAPTOP_720 = DEFAULT_VIEWPORT
#: Desktop, the whole column band scrolled out.
SHORT_720 = {"width": 1280, "height": 600}
#: The narrowest desktop measured: a plain big board scrolls on BOTH axes and
#: is still not mirrored (900 > 820).
NARROW_DESKTOP = {"width": 900, "height": 700}

#: Where the clue boxes of one cell's row and column are, relative to
#: ``.player-stage``'s own visible box, and what paints at their centre.
#:
#: Only the boxes that CARD-271 sticks are looked up (``.is-stuck-row`` /
#: ``.is-stuck-col``): on a doubled board those are the labelled gutters and
#: the duplicate is deliberately not one of them, so a selector that matched
#: either would not say which box is being measured.
#:
#: ``inside`` is the card's "in view": the whole box is within the stage's
#: visible box, to half a pixel (every number measured here is tens of
#: pixels from the bound, so the tolerance is for sub-pixel rounding only).
#: ``hit`` is what ``document.elementFromPoint`` finds at the box's centre,
#: and it is how "the cells scrolled past are UNDER, not over, the gutters"
#: is read. It is a CLASSIFICATION and not an element, because what may
#: legitimately paint there is more than one thing:
#:
#: * ``"own box"`` — the measured box itself, the usual answer;
#: * ``"another gutter box"`` — a different clue box or corner. Two stuck
#:   bands cross at the corner, and at 300 % zoom a band is most of the
#:   scrollport wide (a 30 x 25's row band measures 1073 px of a 1560 px
#:   stage there), so a column box can sit behind the row band. Still a
#:   gutter over a cell, which is the property;
#: * ``"off-window"`` — the box is inside the STAGE but the stage itself is
#:   past the browser window (the page scrolls on a phone, under the board),
#:   so there is no point to hit-test. Reported rather than silently read as
#:   a miss, since ``elementFromPoint`` answers null for both;
#: * anything else is the tag and classes of what paints there — a cell over
#:   a gutter reports itself.
_IN_VIEW = """([row, col]) => {
  const stage = document.querySelector('.player-stage');
  const table = document.querySelector('.player-board');
  const sr = stage.getBoundingClientRect();
  const look = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const onWindow = cx >= 0 && cy >= 0 && cx <= innerWidth && cy <= innerHeight;
    const hit = onWindow ? document.elementFromPoint(cx, cy) : null;
    return {
      inside: r.left >= sr.left - 0.5 && r.right <= sr.right + 0.5
           && r.top >= sr.top - 0.5 && r.bottom <= sr.bottom + 0.5,
      dTop: +(r.top - sr.top).toFixed(2), dLeft: +(r.left - sr.left).toFixed(2),
      dBottom: +(sr.bottom - r.bottom).toFixed(2), dRight: +(sr.right - r.right).toFixed(2),
      position: getComputedStyle(el).position,
      zIndex: getComputedStyle(el).zIndex,
      hit: !onWindow ? 'off-window'
         : hit === null ? 'nothing'
         : el.contains(hit) ? 'own box'
         : hit.closest('th.player-clue, td.player-corner') !== null ? 'another gutter box'
         : hit.tagName + '.' + hit.className,
      numbers: [...el.querySelectorAll('.player-clue-num')].map((n) => n.textContent),
    };
  };
  return {
    scroll: [stage.scrollLeft, stage.scrollTop],
    overflow: [stage.scrollWidth - stage.clientWidth, stage.scrollHeight - stage.clientHeight],
    row: look(table.querySelector(`th.player-clue.is-row.is-stuck-row[data-line="${row}"]`)),
    col: look(table.querySelector(`th.player-clue.is-col.is-stuck-col[data-line="${col}"]`)),
    corner: look(table.querySelector('.player-corner.is-stuck-col.is-stuck-row')),
  };
}"""

#: "A gutter paints here, not a cell" — the two readings of :data:`_IN_VIEW`'s
#: ``hit`` that satisfy it.
GUTTER_PAINTS = ("own box", "another gutter box")

#: Scroll ``.player-stage`` to one of its four corners: ``x``/``y`` of 1 mean
#: the far end of that axis, and the browser clamps to the real maximum so no
#: number has to be computed here.
_TO_CORNER = """([x, y]) => {
  const stage = document.querySelector('.player-stage');
  stage.scrollLeft = x ? stage.scrollWidth : 0;
  stage.scrollTop = y ? stage.scrollHeight : 0;
}"""


def _in_view(page, row, col):
    return page.evaluate(_IN_VIEW, [row, col])


def _to_corner(page, x, y):
    """Scroll the stage to one of its corners, with the stage itself brought
    into the browser window first.

    The window part is Playwright's and not this page's JS, and that is
    measured rather than stylistic: in this headless Chromium the DOCUMENT
    does not scroll from script at all — at 390 x 844 the solve page is
    1256 px tall, ``document.scrollingElement.scrollTop = 300``,
    ``window.scrollBy``, ``scrollIntoView`` and a synthesized wheel each
    leave ``scrollY`` at 0, while Playwright's CDP-driven
    ``scroll_into_view_if_needed`` moves it to 400. So on a phone viewport
    the bottom of the stage is below the window, and
    ``document.elementFromPoint`` — which takes WINDOW coordinates — answers
    null for every box down there, which :data:`_IN_VIEW` would report as
    ``off-window``. Bringing the stage into the window is what makes the
    "cells scroll under the gutters" reading possible at all; it changes
    nothing about the stage's own scroll, which is what the card is about.
    """
    page.locator(".player-stage").scroll_into_view_if_needed()
    page.evaluate(_TO_CORNER, [1 if x else 0, 1 if y else 0])


def _to_bottom_right(page):
    _to_corner(page, 1, 1)


@pytest.mark.browser
class TestSolverClues_TheStageIsTheScrollContainer:
    """"What to implement" item 3 — the card asks for this to be VERIFIED and
    not assumed, because every sticky offset in admin.css resolves against
    whichever ancestor scrolls: if the overflow lived on ``.main`` or on the
    document, sticking against the stage would pin the gutters to the wrong
    box and the fix would be silently inert.

    Measured: of the table's seven ancestors, exactly one — ``.player-stage``
    — has a scrolling ``overflow``, and it is the one that actually has
    content past its visible box. The document scrolls vertically on this
    page (the toolbar and the usage hint below the stage), which is why the
    assertion is about the table's ANCESTOR CHAIN and not about the page.
    """

    def test_only_the_stage_scrolls_over_the_board(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(SHORT_720)
        _open(page, live, live.store(GRID_30x30))

        chain = page.evaluate(
            """() => {
              const out = [];
              for (let el = document.querySelector('.player-board'); el; el = el.parentElement) {
                const s = getComputedStyle(el);
                out.push({ name: el.tagName + (el.className ? '.' + el.className : ''),
                           scrolls: ['auto', 'scroll', 'overlay'].includes(s.overflowX)
                                 || ['auto', 'scroll', 'overlay'].includes(s.overflowY),
                           overflowX: el.scrollWidth - el.clientWidth,
                           overflowY: el.scrollHeight - el.clientHeight });
              }
              return out;
            }"""
        )

        assert len(chain) >= 6, chain  # table, stage, main, shell, body, html
        scrollers = [box for box in chain if box["scrolls"]]
        assert [box["name"] for box in scrollers] == ["DIV.player-stage"], chain
        # And it is the box the board really does outgrow, so the question the
        # card asked is answered by a measurement and not by a declaration.
        assert scrollers[0]["overflowY"] == 211, scrollers


@pytest.mark.browser
class TestSolverClues_StayInViewOnAPlainBigBoard:
    """AC-1 — the reported case, on the plain single-gutter board the ladder
    actually draws for a 30 x 30 on a desktop.

    Scrolled to the far bottom-right cell, that cell's row clue and column
    clue are both wholly inside ``.player-stage``'s visible box, and what
    paints at the centre of each is the gutter itself and not a cell: the
    cells scrolled past go UNDER the gutters.

    Each viewport states its own measured overflow, because that is what
    makes the case the case. At 1280 x 720 (the card's viewport) the stage
    scrolls 91 px down and NOT AT ALL sideways — the fit clamp is exactly
    what keeps a 100 % board inside its stage's width — so the column half
    of this AC is the live one there and the row half is asserted at
    900 x 700, the one desktop viewport measured where a plain board scrolls
    on both axes without CARD-193's mirror holding.
    """

    @pytest.mark.parametrize(
        "name, viewport, overflow",
        [
            ("the card's 1280x720", LAPTOP_720, [0, 91]),
            ("a short window, whole band gone", SHORT_720, [0, 211]),
            ("a narrow window, both axes", NARROW_DESKTOP, [104, 111]),
        ],
        ids=lambda value: value if isinstance(value, str) else "",
    )
    def test_the_bottom_right_cells_clues_are_in_view(
        self, browser_page, live, name, viewport, overflow
    ) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open(page, live, live.store(GRID_30x30))
        # The board really is the plain one — the case this AC is about.
        assert _gutters(page)["feet"] == 0
        assert page.evaluate(
            "document.querySelectorAll('th.player-clue[aria-hidden=\"true\"]').length") == 0

        _to_bottom_right(page)
        seen = _in_view(page, 29, 29)

        # The overflow is the case: if this window is not the one the numbers
        # were measured on, the rest of the test is measuring something else.
        assert seen["overflow"] == overflow, (name, seen["overflow"])
        assert seen["scroll"] == overflow, (name, seen)

        assert seen["row"]["inside"], (name, seen["row"])
        assert seen["col"]["inside"], (name, seen["col"])
        # Pinned to the scrollport's own edges, which is what "whatever the
        # player scrolled to" means: without the stick these would read
        # -{overflow} instead of 0.
        assert seen["row"]["dLeft"] == 0, (name, seen["row"])
        assert seen["col"]["dTop"] == 0, (name, seen["col"])
        # The cells that scrolled past are under the gutters, not over them.
        assert seen["row"]["hit"] == "own box", (name, seen["row"])
        assert seen["col"]["hit"] == "own box", (name, seen["col"])
        # And both carry the numbers they are supposed to be showing.
        assert seen["row"]["numbers"] == [str(n) for n in _encode(GRID_30x30[29])], seen["row"]
        assert seen["col"]["numbers"] == [
            str(n) for n in _encode([row[29] for row in GRID_30x30])], seen["col"]

    def test_the_corner_sticks_on_both_axes(self, browser_page, live) -> None:
        """"What to implement" item 1's last clause: the corner box is where
        the two bands cross, so it sticks on both axes and paints above both
        (z-index 3 against the bands' 2 and 1) — otherwise the crossing is a
        hole through which the cells show."""
        page = browser_page
        page.set_viewport_size(NARROW_DESKTOP)
        _open(page, live, live.store(GRID_30x30))

        _to_bottom_right(page)
        seen = _in_view(page, 29, 29)

        assert seen["corner"]["dTop"] == 0 and seen["corner"]["dLeft"] == 0, seen["corner"]
        assert seen["corner"]["hit"] == "own box", seen["corner"]
        assert [int(seen[k]["zIndex"]) for k in ("corner", "row", "col")] == [3, 2, 1], seen


@pytest.mark.browser
class TestSolverClues_SmallBoardsUnaffectedByStickiness:
    """AC-5 — a 15 x 15 is past neither side's BIG_SIDE and fits its stage, so
    stickiness has nothing to do: the stage does not scroll on either axis,
    and every gutter box sits exactly where the static layout puts it.

    "Exactly where" is read as the box's offset from the TABLE's own content
    box, independently of the stage: a sticky box that had shifted would
    move relative to the table, because sticky shifts a box out of its flow
    position and nothing else does.

    AC-5's clause is "nothing OBSERVABLE changes", and a 15 x 15 that fits at
    100 % is only the easy half of it. The second and third tests here are the
    half this card's review cycle 1 found missing (F-001): a small board that
    is zoomed DOES scroll, so the room condition has a real answer for it, and
    that answer is a property of the viewport. Before the fix the two viewport
    triggers in solver.js were both gated on ``isBig`` — correct while every
    viewport-dependent decision was a LAYOUT one, since a board big on neither
    side can have neither CARD-193's mirror nor CARD-212's duplicate — so the
    classes a small board was given at load survived any later resize, and a
    stale stick floated a band over cells the player could then not tap. Both
    directions are pinned below, each against the same board, viewport and
    zoom reached by LOADING there, because the mechanism is right everywhere it
    is reached and it is the reaching that was missing.
    """

    @pytest.mark.parametrize("viewport", [ROOMY, LAPTOP, {"width": 390, "height": 844}],
                             ids=["roomy", "laptop", "phone"])
    def test_a_15x15_moves_nothing(self, browser_page, live, viewport) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open_player(page, live)

        offsets = """() => {
          const table = document.querySelector('.player-board');
          const t = table.getBoundingClientRect();
          const stage = document.querySelector('.player-stage');
          return {
            overflow: [stage.scrollWidth - stage.clientWidth,
                       stage.scrollHeight - stage.clientHeight],
            boxes: [...table.querySelectorAll('th.player-clue, td.player-corner')].map((el) => {
              const r = el.getBoundingClientRect();
              return [el.className, +(r.left - t.left).toFixed(2), +(r.top - t.top).toFixed(2)];
            }),
          };
        }"""
        at_rest = page.evaluate(offsets)
        # Nothing to scroll: the board fits, which is what makes this the
        # edge case the AC names.
        assert at_rest["overflow"] == [0, 0], at_rest["overflow"]
        assert len(at_rest["boxes"]) == 15 + 15 + 1, at_rest["boxes"][:3]

        # Scrolling a stage with nothing to scroll is a no-op, and so is
        # every sticky box on it: the whole band is where it was.
        _to_bottom_right(page)
        assert page.evaluate(offsets) == at_rest

        # Each box's flow position, read off the table's own geometry rather
        # than off the box: the one corner at the origin, the column band
        # across the top of the row band, the row band down the left.
        band = [b for b in at_rest["boxes"] if "is-row" in b[0]]
        above = [b for b in at_rest["boxes"] if "is-col" in b[0]]
        corner = [b for b in at_rest["boxes"] if "player-corner" in b[0]]
        assert len(corner) == 1 and corner[0][1] == 0 and corner[0][2] == 0, corner
        assert {b[1] for b in band} == {0}, band
        assert {b[2] for b in above} == {0}, above
        assert sorted(b[2] for b in band) == [b[2] for b in band], band

    #: The viewport a zoomed 15 x 15 is dragged BETWEEN, and the zoom. Measured
    #: on this host, Chromium: at 1920 x 1500 nothing scrolls, so both axes
    #: keep; at 1024 x 768 the same board has a 376.3 px row band and a
    #: 270.4 px column band over a 724 x 540 scrollport and overflows past
    #: both, so what each band could hide is 0.520 and 0.501 of its axis —
    #: past STICK_MAX_SHARE, and neither axis may keep. Every assertion below
    #: re-derives that from the page's own numbers; these two viewports are
    #: chosen because the decision differs between them, which is what makes
    #: the test able to see a missing re-measurement at all.
    SHRINK_FROM = ROOMY
    SHRINK_TO = {"width": 1024, "height": 768}
    #: And the reverse: from a viewport that refuses both axes to one with the
    #: room for both.
    GROW_TO = {"width": 1600, "height": 1200}
    STALE_ZOOM = 200

    def test_a_resize_after_a_zoom_re_measures_the_room(
        self, browser_page, live
    ) -> None:
        """The stale STICK, and what it costs the player.

        A 15 x 15 zoomed to 200 % at 1920 x 1500 keeps both axes, because
        nothing scrolls there and a band that covers nothing is free. Dragged
        to 1024 x 768 the same board overflows on both axes and the bands are
        half the scrollport, which is the configuration STICK_MAX_SHARE was
        measured to refuse — solver.js:437-447 names this very board and
        viewport, "where a 359.4 px row band over a 724 px stage swallowed the
        cells a recorded touch drag was aimed at". Without a re-measurement
        the refusal does not reach the resized page: the classes stay on, the
        bands float, and most of the cells still visible do not take their own
        tap.

        The LOADED control is what makes this a missing call site rather than
        a broken measurement — the same board at the same viewport and zoom,
        reached by loading, decides correctly — and the hit count is read
        scrolled to the far corner, because at scroll 0 a sticky box sits at
        its flow position and covers nothing at all.
        """
        page = browser_page

        page.set_viewport_size(self.SHRINK_FROM)
        _open_player(page, live)
        _zoom(page, self.STALE_ZOOM)
        at_load = _room(page)
        page.set_viewport_size(self.SHRINK_TO)
        _settled(page)
        resized = _room(page)
        _to_bottom_right(page)
        resized_hits = _blocked(page)

        page.set_viewport_size(self.SHRINK_TO)
        _open_player(page, live)
        _zoom(page, self.STALE_ZOOM)
        loaded = _room(page)
        _to_bottom_right(page)
        loaded_hits = _blocked(page)

        report = {"at_load": at_load, "resized": resized, "loaded": loaded,
                  "resized_hits": resized_hits, "loaded_hits": loaded_hits}
        # One board at one viewport, measured twice: if the three inputs
        # differed, the two readings would not be comparable and this test
        # would be about two different pages.
        assert resized["port"] == loaded["port"], report
        assert resized["band"] == loaded["band"], report
        assert resized["overflow"] == loaded["overflow"], report
        # Not vacuous: the viewport really does change the answer, so a page
        # that never re-measured would be caught by the next two assertions
        # and not merely be unexercised.
        assert at_load["keeping"] != _verdict(loaded), report
        # The mechanism, where it is reached...
        assert loaded["keeping"] == _verdict(loaded), report
        # ...and where it has to be reached through a resize.
        assert resized["keeping"] == _verdict(resized), report
        assert resized["keeping"] == loaded["keeping"], report

        # The consequence, in cells: a stuck band over the bottom-right cells
        # takes their taps, and that is the whole reason the room condition
        # exists. Both readings see cells, so neither zero is an empty count.
        assert loaded_hits["visible"] > 0 and resized_hits["visible"] > 0, report
        assert loaded_hits["blocked"] == 0, report
        assert resized_hits["blocked"] == 0, report

    def test_a_grown_window_re_measures_the_room_too(
        self, browser_page, live
    ) -> None:
        """The same staleness in the other direction, which costs the clues
        rather than the board: a zoomed 15 x 15 that was refused both axes at
        1024 x 768 is given a window with the room for them, and without a
        re-measurement it goes on scrolling its clues away where the card's own
        rule says to keep them. One direction of a bar is not a control for
        it (CARD-264's lesson), so both are pinned."""
        page = browser_page

        page.set_viewport_size(self.SHRINK_TO)
        _open_player(page, live)
        _zoom(page, self.STALE_ZOOM)
        at_load = _room(page)
        page.set_viewport_size(self.GROW_TO)
        _settled(page)
        resized = _room(page)

        page.set_viewport_size(self.GROW_TO)
        _open_player(page, live)
        _zoom(page, self.STALE_ZOOM)
        loaded = _room(page)

        report = {"at_load": at_load, "resized": resized, "loaded": loaded}
        assert resized["port"] == loaded["port"], report
        assert resized["band"] == loaded["band"], report
        assert resized["overflow"] == loaded["overflow"], report
        assert at_load["keeping"] != _verdict(loaded), report
        assert loaded["keeping"] == _verdict(loaded), report
        assert resized["keeping"] == _verdict(resized), report
        assert resized["keeping"] == loaded["keeping"], report


#: --grid-ink as the browser resolves it, for the pixel sample below.
_INK_RGB = """() => {
  const probe = document.createElement('i');
  probe.style.color = 'var(--grid-ink)';
  document.querySelector('.player-board').append(probe);
  const colour = getComputedStyle(probe).color;
  probe.remove();
  return colour;
}"""


def _rgb(text):
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


@pytest.mark.browser
class TestSolverClues_StickyGutterRendersCleanly:
    """AC-6 — a stuck gutter with the board scrolled behind it renders as a
    static one does: opaque, with its heavy rule toward the grid, and with
    CARD-188's circles on its numbers.

    Opacity is the one of the three that a computed style alone cannot
    settle — a transparent box with an opaque ancestor also computes to
    alpha 1 nowhere, and an opaque box that paints BELOW the cells looks the
    same from the DOM — so it is sampled in pixels: all 900 cells filled
    (``--grid-ink``), the board scrolled to its far corner, and the colour
    at the centre of each stuck box read from a screenshot. The corner is
    the strongest sample of the three, being blank by construction, and it
    is also the box that had no background of its own before this card.
    """

    def test_a_stuck_gutter_is_opaque_over_the_cells(self, browser_page, live) -> None:
        import io

        from PIL import Image

        page = browser_page
        page.set_viewport_size(SHORT_720)
        _open(page, live, live.store(GRID_30x30))
        _set(page, [F] * (30 * 30))
        _to_bottom_right(page)

        ink = _rgb(page.evaluate(_INK_RGB))
        spots = page.evaluate(
            """() => {
              const table = document.querySelector('.player-board');
              const at = (el) => {
                const r = el.getBoundingClientRect();
                const look = getComputedStyle(el);
                return { x: r.left + r.width / 2, y: r.top + r.height / 2,
                         declared: look.backgroundColor };
              };
              return {
                corner: at(table.querySelector('.player-corner.is-stuck-col.is-stuck-row')),
                clue: at(table.querySelector('th.player-clue.is-col.is-stuck-col')),
                page: getComputedStyle(document.body).backgroundColor,
              };
            }"""
        )

        # Every cell behind the gutters is ink, so a transparent box would
        # read ink here.
        assert page.evaluate(
            "[...new Set([...document.querySelectorAll('td.player-cell')]"
            ".map((td) => td.dataset.state))]") == ["filled"]

        for name in ("corner", "clue"):
            spot = spots[name]
            shot = page.screenshot(
                clip={"x": spot["x"] - 1, "y": spot["y"] - 1, "width": 3, "height": 3})
            pixel = Image.open(io.BytesIO(shot)).convert("RGB").getpixel((1, 1))
            assert pixel != ink, (name, pixel, ink)
            assert pixel == _rgb(spot["declared"]), (name, pixel, spot)
        # The corner's own colour is the one it used to show THROUGH itself:
        # it was a blank td over the page, so making it opaque must not have
        # repainted it (cross-checked against the page's own background
        # rather than against the token's name).
        assert spots["corner"]["declared"] == spots["page"], spots

    def test_a_stuck_gutter_keeps_its_heavy_edge_and_its_circles(self, browser_page, live) -> None:
        """The rule toward the grid and CARD-188's ring, read on the stuck
        gutters while the board is scrolled behind them and compared with the
        same boards' own thin rule — so this is the heavy/thin pattern of
        TestSolverClues_DoubledFramesReadOnAllFourSides, re-read in the one
        state that card never had: a gutter away from its flow position."""
        page = browser_page
        page.set_viewport_size(NARROW_DESKTOP)
        _open(page, live, live.store(GRID_30x30))
        # The whole solution: every line settles, so every number circles.
        _set(page, [F if on else E for line in GRID_30x30 for on in line])
        _to_bottom_right(page)

        seen = page.evaluate(
            """() => {
              const px = (el, side) => parseFloat(getComputedStyle(el)[`border${side}Width`]);
              const table = document.querySelector('.player-board');
              const row = table.querySelector('th.player-clue.is-row.is-stuck-row[data-line="29"]');
              const col = table.querySelector('th.player-clue.is-col.is-stuck-col[data-line="29"]');
              const corner = table.querySelector('.player-corner.is-stuck-col.is-stuck-row');
              const cell = table.querySelector('td.player-cell');
              const rings = (box) => [...box.querySelectorAll('.player-clue-num')].map((span) => {
                const look = getComputedStyle(span, '::before');
                const r = span.getBoundingClientRect(), b = box.getBoundingClientRect();
                return { circled: span.classList.contains('is-circled'),
                         width: parseFloat(look.borderTopWidth), colour: look.borderTopColor,
                         insideLeft: +(r.left - b.left).toFixed(2),
                         insideRight: +(b.right - r.right).toFixed(2) };
              });
              return {
                thin: px(cell, 'Right'),
                rowToGrid: px(row, 'Right'), rowOuter: px(row, 'Left'),
                colToGrid: px(col, 'Bottom'), colOuter: px(col, 'Top'),
                cornerToGrid: [px(corner, 'Right'), px(corner, 'Bottom')],
                rowRings: rings(row), colRings: rings(col),
              };
            }"""
        )
        ink = page.evaluate(_INK_RGB)

        # The heavy rule, on the edge of each stuck box that faces the grid —
        # the edge the scrolled cells arrive at.
        heavy = seen["rowToGrid"]
        assert heavy == pytest.approx(2 * seen["thin"], abs=0.01), seen
        assert seen["colToGrid"] == heavy, seen
        assert seen["cornerToGrid"] == [heavy, heavy], seen
        # ...and the thin one on the outer edges, unchanged by sticking.
        assert (seen["rowOuter"], seen["colOuter"]) == (seen["thin"], seen["thin"]), seen

        # CARD-188's rings, on a stuck gutter: every number of the settled
        # board is circled, in both bands, with a real ring in --grid-ink.
        for name in ("rowRings", "colRings"):
            rings = seen[name]
            assert rings and all(r["circled"] for r in rings), (name, rings)
            assert all(r["width"] > 0 and r["colour"] == ink for r in rings), (name, rings[0])
        # And no ring crosses the edge that faces the grid — the property
        # TestSolverClues_RowRingsStayInsideTheirOwnBand pins on a static
        # band, re-read on a stuck one.
        assert [r for r in seen["rowRings"] if r["insideRight"] < 0] == [], seen["rowRings"]


@pytest.mark.browser
class TestSolverClues_DoubledGuttersAreNotStuck:
    """AC-4's other half, as a positive claim rather than only as the
    unedited ladder gate: a duplicate NEVER sticks.

    That is a measurement and not a preference. A 30 x 25 at 1920 x 1500 and
    150 % zoom has a 567.9 px row band in a 1620 px stage, so a gutter stuck
    at EACH end of that axis would spend 1136 px of it — and CARD-212's
    duplicates are already at the far ends, which is the same job. So on a
    doubled board the labelled gutter sticks and the duplicate, the <tfoot>
    band and the duplicate's corner stay exactly where CARD-212 put them.

    Asserted at 150 % zoom, where the stage overflows by (778, 487) — more
    than either band, so every gutter of this board would scroll clean out of
    view without the fix, and a stuck duplicate would be unmistakable. (At
    100 % this board fits its stage in both directions, which is CARD-212's
    own condition for drawing the duplicates at all, so nothing there could
    tell a stuck box from a static one.)
    """

    def test_the_duplicate_the_tfoot_and_its_corner_stay_put(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(ROOMY)
        _open(page, live, live.store(GRID_30x25))
        assert _gutters(page)["feet"] == 1  # all four gutters: the doubled board
        for _ in range(2):
            page.locator('[data-player-zoom-action="in"]').click(force=True)
        assert page.locator("[data-player-zoom-readout]").text_content() == "150%"

        seen = page.evaluate(
            """() => {
              const table = document.querySelector('.player-board');
              const stage = document.querySelector('.player-stage');
              const pos = (sel) => [...table.querySelectorAll(sel)].map(
                (el) => getComputedStyle(el).position);
              return {
                overflow: [stage.scrollWidth - stage.clientWidth,
                           stage.scrollHeight - stage.clientHeight],
                bands: [
                  table.querySelector('th.player-clue.is-row.is-stuck-row')
                    .getBoundingClientRect().width,
                  table.querySelector('th.player-clue.is-col.is-stuck-col')
                    .getBoundingClientRect().height,
                ],
                labelledRows: [...new Set(pos('tbody th.player-clue.is-row:not([aria-hidden])'))],
                duplicateRows: [...new Set(pos('tbody th.player-clue.is-row[aria-hidden="true"]'))],
                headColumns: [...new Set(pos('thead th.player-clue.is-col'))],
                footColumns: [...new Set(pos('tfoot th.player-clue.is-col'))],
                corners: [...table.querySelectorAll('.player-corner')].map((el) => {
                  const s = getComputedStyle(el);
                  return [el.className, s.position, s.top, s.left, s.right];
                }),
              };
            }"""
        )

        # Both bands would scroll clean out of view without the fix: the
        # overflow on each axis is past that axis's whole band (567.9 px and
        # 347.4 px here), so this is a case and not a formality.
        assert seen["overflow"] == [778, 487], seen["overflow"]
        assert seen["bands"] == [pytest.approx(567.9, abs=0.5),
                                 pytest.approx(347.4, abs=0.5)], seen["bands"]
        assert seen["labelledRows"] == ["sticky"], seen
        assert seen["duplicateRows"] == ["static"], seen
        assert seen["headColumns"] == ["sticky"], seen
        assert seen["footColumns"] == ["static"], seen
        # Four corners, each sticking on exactly the axes whose band it
        # closes — which is why a corner carries the two markers separately:
        #   head + left    both bands stick, so it does too
        #   head + right   its row band is the duplicate: the top only
        #   foot + left    its column band is the duplicate: the left only
        #                  (and it must, or the stuck row band would show a
        #                  notch at the bottom row where this box used to be)
        #   foot + right   both of its bands are duplicates: nothing
        assert sorted(seen["corners"]) == sorted([
            ["player-corner is-stuck-col is-stuck-row", "sticky", "0px", "0px", "auto"],
            ["player-corner is-right is-stuck-col", "sticky", "0px", "auto", "auto"],
            ["player-corner is-stuck-row", "sticky", "auto", "0px", "auto"],
            ["player-corner is-right", "static", "auto", "auto", "auto"],
        ]), seen["corners"]


#: solver.js's own STICK_MAX_SHARE, read out of the file that declares it.
#: The tests below re-derive the "does this axis keep its clues?" decision
#: from the measurements rather than from the classes, which needs the
#: number — and reading it here means the number has one home and a drift
#: cannot pass as agreement.
#:
#: The absence is NAMED rather than left to the regex (CARD-271 review cycle
#: 1, F-007): a value outside the ``([0-9.]+)`` domain makes ``re.search``
#: answer ``None`` at IMPORT time, which takes this file, phone.py and zoom.py
#: out of collection with ``AttributeError: 'NoneType' ... 'group'`` — loud
#: (exit 2, three ERROR lines) but unattributable, and this card's own
#: pre-gate paid for that exact shape twice, with two mutants that exited
#: non-zero having run nothing. The idiom is the one already beside the
#: row-gap derivation in tests/test_admin_design_tokens.py: derive the figure,
#: and say what its absence means.
_DECLARED_SHARE = re.search(
    r"\nconst STICK_MAX_SHARE = ([0-9.]+);",
    (_TOKENS_STATIC / "solver.js").read_text())
assert _DECLARED_SHARE, "solver.js no longer declares STICK_MAX_SHARE as a decimal"
STICK_MAX_SHARE = float(_DECLARED_SHARE.group(1))


#: What solver.js's keepCluesInView measured, and the inputs it measured it
#: from: ``cover`` is what a stuck band could actually hide, min(this axis's
#: overflow, the band's own size), against STICK_MAX_SHARE of the stage.
_ROOM = """() => {
  const stage = document.querySelector('.player-stage');
  const table = document.querySelector('.player-board');
  const size = (sel, side) => {
    const box = table.querySelector(sel);
    // Infinity, not 0, because solver.js's own fallback fails closed toward
    // NOT sticking (CARD-271 review cycle 1, F-003) and this expression is a
    // deliberate reimplementation of that one: it moves with it or it stops
    // being a cross-check. Unreachable on every board the suite draws.
    return box === null ? Infinity : box.getBoundingClientRect()[side];
  };
  const band = [size('th.player-clue.is-row.is-stuck-row', 'width'),
                size('th.player-clue.is-col.is-stuck-col', 'height')];
  const overflow = [stage.scrollWidth - stage.clientWidth,
                    stage.scrollHeight - stage.clientHeight];
  return {
    keeping: [table.classList.contains('is-keeping-rows'),
              table.classList.contains('is-keeping-cols')],
    band: band.map((n) => +n.toFixed(1)),
    overflow,
    port: [stage.clientWidth, stage.clientHeight],
    cover: [+Math.min(overflow[0], band[0]).toFixed(1),
            +Math.min(overflow[1], band[1]).toFixed(1)],
  };
}"""


def _room(page):
    return page.evaluate(_ROOM)


def _verdict(room):
    """The decision ``keepCluesInView``'s OWN terms give for this reading —
    re-derived from the measurements and solver.js's constant, never read off
    the classes it set. ``_room(page)["keeping"] == _verdict(_room(page))`` is
    the whole rule, and every test below that cares which axes keep its board
    checks the two against each other rather than trusting either."""
    return [room["cover"][axis] <= room["port"][axis] * STICK_MAX_SHARE
            for axis in (0, 1)]


#: solver.js's RESIZE_SETTLE, read out of the file that declares it so the
#: wait below cannot drift from the debounce it is waiting out. Named on
#: absence for the same reason STICK_MAX_SHARE is (F-007).
_DECLARED_SETTLE = re.search(
    r"\nconst RESIZE_SETTLE = (\d+);", (_TOKENS_STATIC / "solver.js").read_text())
assert _DECLARED_SETTLE, "solver.js no longer declares RESIZE_SETTLE as an integer"
RESIZE_SETTLE = int(_DECLARED_SETTLE.group(1))


def _settled(page):
    """Wait out the trailing debounce a viewport change is handled through.

    Four times the declared settle, which is the wait
    tests/test_puzzle_solver_zoom.py's resize tests already use: generous
    rather than tight on purpose, because what is being read afterwards is a
    settled state and a tight wait would turn a slow machine into a failure.
    """
    page.wait_for_timeout(4 * RESIZE_SETTLE)


#: Every cell whose own centre lies inside ``.player-stage``'s visible box,
#: and how many of them do not take their own tap: ``document.elementFromPoint``
#: at the centre answering something that is not the cell means a stuck band
#: is floating over it. This is the CONSEQUENCE reading of the room condition
#: — the reason STICK_MAX_SHARE exists at all — and it is in window
#: coordinates, so the stage has to be inside the window first (see
#: :func:`_to_corner`, and note that at scroll 0 a sticky box sits at its flow
#: position and covers nothing, so this must be read scrolled).
_BLOCKED = """() => {
  const stage = document.querySelector('.player-stage');
  const port = stage.getBoundingClientRect();
  let visible = 0, blocked = 0;
  for (const cell of document.querySelectorAll('.player-board td.player-cell')) {
    const box = cell.getBoundingClientRect();
    const x = box.left + box.width / 2, y = box.top + box.height / 2;
    if (x < port.left || x > port.right || y < port.top || y > port.bottom) continue;
    visible += 1;
    const hit = document.elementFromPoint(x, y);
    if (hit !== cell && !cell.contains(hit)) blocked += 1;
  }
  return { visible, blocked };
}"""


def _blocked(page):
    return page.evaluate(_BLOCKED)


def _zoom(page, percent):
    """Step the zoom buttons to ``percent``.

    tests/test_puzzle_solver_zoom.py has the same helper; it imports this
    module, so this one is written here rather than imported from there, in
    the same spirit as the rest of this suite's one-directional test imports.
    """
    assert 100 <= percent <= 300 and percent % 25 == 0, percent
    readout = page.locator("[data-player-zoom-readout]")
    current = int(readout.text_content().rstrip("%"))
    action = "in" if percent > current else "out"
    for _ in range(abs(percent - current) // 25):
        page.locator(f'[data-player-zoom-action="{action}"]').click(force=True)
    assert readout.text_content() == f"{percent}%", readout.text_content()


@pytest.mark.browser
class TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted:
    """A stuck band floats over the cells, so keeping the clues in view and
    keeping the BOARD in view are the same space spent twice. solver.js
    therefore sticks an axis only while the band could hide at most
    ``STICK_MAX_SHARE`` of the stage, measured per axis as min(that axis's
    overflow, the band) — so an axis that barely scrolls keeps its clues
    however deep its band is, and one whose band would swallow the board
    keeps today's rendering instead.

    Two things here that nothing else says:

    * the decision agrees with its own inputs at every viewport sampled, and
      the sample spans the threshold from both sides (the row axis crosses it
      between 390 px and 600 px of window, with CARD-193's mirror holding at
      both);
    * the measurement cannot oscillate. Sticking is layout-neutral, and in
      Chromium a stuck box adds nothing to the scrollable overflow either —
      so both of the terms it reads are the same before and after it is
      applied. Read off the live board by toggling the classes by hand: if
      sticking changed either term, this card's rule would feed back into
      its own input and the board could flicker between the two answers on
      every resize.
    """

    #: Measured on this host, Chromium, with GRID_30x30.
    ROOMS = [
        ("1280x720", {"width": 1280, "height": 720}, [True, True], [0, 91], [980, 492]),
        ("1280x600", {"width": 1280, "height": 600}, [True, True], [0, 211], [980, 372]),
        ("900x700", {"width": 900, "height": 700}, [True, True], [104, 111], [600, 472]),
        # The mirror, and the one case at 100 % zoom where an axis gives up:
        # 272.2 px of band over a 358 px stage is three quarters of it, so a
        # stuck band would leave six columns of thirty visible.
        ("390x844", {"width": 390, "height": 844}, [False, True], [346, 0], [358, 583]),
        # The same board and the same mirror, 210 px wider: the row axis now
        # scrolls by 136 px, so that is all the band can hide, and it keeps.
        ("600x844", {"width": 600, "height": 844}, [True, True], [136, 0], [568, 583]),
    ]

    @pytest.mark.parametrize("name, viewport, keeping, overflow, port", ROOMS,
                             ids=[case[0] for case in ROOMS])
    def test_each_axis_keeps_its_clues_exactly_when_it_has_the_room(
        self, browser_page, live, name, viewport, keeping, overflow, port
    ) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open(page, live, live.store(GRID_30x30))

        seen = _room(page)

        assert (seen["overflow"], seen["port"]) == (overflow, port), (name, seen)
        assert seen["keeping"] == keeping, (name, seen)
        # The decision re-derived from its own inputs, here, rather than
        # trusted from the class: each axis keeps exactly while what its band
        # could hide is at most STICK_MAX_SHARE of the stage — two fifths,
        # 0.4, as solver.js declares it and as the next line reads it out of
        # that file. (It said "half" until CARD-271's pre-gate, PG-1; the
        # assertion below was always derived from the constant, so the figure
        # was a stale copy and not a second opinion. Nothing here restates it:
        # the share is spelled once, in solver.js.)
        assert 0 < STICK_MAX_SHARE < 1, STICK_MAX_SHARE
        assert seen["keeping"] == [
            seen["cover"][axis] <= seen["port"][axis] * STICK_MAX_SHARE
            for axis in (0, 1)], (name, seen)

    def test_sticking_changes_neither_the_band_nor_the_overflow(
        self, browser_page, live
    ) -> None:
        page = browser_page
        page.set_viewport_size(SHORT_720)
        _open(page, live, live.store(GRID_30x30))
        _to_bottom_right(page)

        stuck = _room(page)
        assert stuck["keeping"] == [True, True], stuck
        loose = page.evaluate(
            """() => {
              const table = document.querySelector('.player-board');
              table.classList.remove('is-keeping-rows', 'is-keeping-cols');
              return null;
            }"""
        ) or _room(page)

        # The classes really did come off — otherwise the comparison below is
        # a tautology.
        assert loose["keeping"] == [False, False], loose
        assert page.evaluate(
            "getComputedStyle(document.querySelector("
            "'.player-board th.player-clue.is-row.is-stuck-row')).position") == "static"
        # ...and neither input moved.
        assert (loose["band"], loose["overflow"], loose["port"]) == (
            stuck["band"], stuck["overflow"], stuck["port"]), (stuck, loose)


def test_the_sticky_gutter_rules_declare_no_colour_but_the_one_token(
) -> None:
    """G-2 — CARD-271's one coloured value, pinned per rule.

    The card's fix is positioning, and positioning declares no colour: the
    four sticky rules must stay that way, because a background or a border
    written into one of them would be a literal the whole-file hex sweep in
    tests/test_admin_design_tokens.py cannot see when it is written as
    ``rgb(...)``, as a named colour or as a bare length. The ONE coloured
    value the card does add is ``.player-corner``'s background, and its value
    has to be a token or a token-only expression.

    Collected by selector, so a renamed, reformatted or deleted rule reds
    this test instead of shrinking it. The predicate is driven over the rule
    broken on purpose at the end (ADR-0039/R1), one break per way a literal
    can get into it.
    """
    css = (_TOKENS_STATIC / "admin.css").read_text()
    rules_only = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    sticky = re.findall(r"(?m)^(\.player-board\.is-keeping[^{]*?)\s*\{([^}]*)\}", rules_only)
    corner = re.findall(r"(?m)^(\.player-corner)\s*\{([^}]*)\}", rules_only)

    assert len(sticky) == 4, (
        f"admin.css declares {len(sticky)} .is-keeping-* rules, not 4: {sticky}")

    # The positioning rules say nothing about colour. (A property sweep, not
    # a value one: `position: sticky` and `top: 0` carry no token and so
    # cannot be judged by the token predicate at all.)
    paints = ("background", "border", "color", "box-shadow", "outline")
    for selector, body in sticky:
        named = [part.split(":", 1)[0].strip() for part in body.split(";") if ":" in part]
        assert [p for p in named if p.startswith(paints)] == [], (selector, named)
        assert [p for p in named if p in ("position", "top", "left", "right", "z-index")], (
            selector, named)

    # ...and the one rule that does paint, paints from a token. There are two
    # top-level `.player-corner` rules — the rule weights CARD-212 left, and
    # this card's background — so the one that paints is picked by what it
    # declares and not by where in the file it sits.
    assert len(corner) == 2, f"admin.css declares {len(corner)} .player-corner rules, not 2"
    painting = [body for _selector, body in corner if "background" in body]
    assert len(painting) == 1, f"{len(painting)} .player-corner rules set a background"
    values = _declared_values(f".player-corner {{{painting[0]}}}")
    assert values == ["var(--color-bg)"], values
    assert _untokenised(values) == [], values

    # The control: each of these is a colour reaching into that rule in a
    # form the whole-file hex sweep would NOT catch.
    for label, value in {
        "a colour function": "rgb(245, 240, 230)",
        "a named colour": "beige",
        "a literal inside the mix": "color-mix(in srgb, #f5f0e6 50%, var(--color-surface))",
        "transparent, which is what the bug was": "transparent",
    }.items():
        assert _untokenised([value]) != [], f"{label}: {value!r} passed the token predicate"
