"""CARD-187 — the puzzle player shows "Progress: N%" (FR-044 AC-351..AC-354,
EC-045; owner's solver test doc 2026-10-05, item 3).

The percent is ``solver_state.js`` ``solvedPercent(board, solution)``: 100
when the board is solved, otherwise floor(100 x correct cells / all cells),
a correct cell being FILLED on a solution-filled cell or EMPTY on a
solution-empty one (undecided, a wrong mark and "?" never count). The page
shows it in ``#puzzle-player-progress``, which is not a live region.

Expected values always come from the Python oracle written here
(``_percent_of``), never from the JavaScript under test. The pure function
is run with ``await import('/static/solver_state.js')`` over a seeded
``random.Random`` corpus (no ``hypothesis``), with the minimum counts
asserted inside the test. User-facing criteria drive real input in Chromium;
``puzzlePlayer.setBoard`` only sets a board up (or is itself the step under
test, AC-4).
"""

from __future__ import annotations

import random

import pytest

from tests.test_puzzle_solver_marking import (
    GRID,
    SIDE,
    E,
    F,
    U,
    _button,
    _cell,
    _centre,
    _drag,
    _states,
    _tool,
    _twenty_strokes,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_progress import (
    _EMPTY,
    _FILLED,
    LONG_RUN,
    _is_solved_shown,
    _set,
    _watch_problems,
)

M = "maybe"  # CARD-186's "?"


# --------------------------------------------------------------------------
# The definition, written independently of solver_state.js
# --------------------------------------------------------------------------


def _solved(cells, solution):
    """Solved, cell by cell: no "?" anywhere, every solution-filled cell
    filled, no solution-empty cell filled (white marks optional)."""
    width = len(solution[0])
    for index, state in enumerate(cells):
        filled = solution[index // width][index % width]
        if state == M or (state == F) != filled:
            return False
    return True


def _correct(cells, solution):
    width = len(solution[0])
    return sum(
        1 for index, state in enumerate(cells)
        if state == (F if solution[index // width][index % width] else E)
    )


def _percent_of(cells, solution):
    """100 if solved, else 100 * correct // (width * height)."""
    if _solved(cells, solution):
        return 100
    return 100 * _correct(cells, solution) // (len(solution) * len(solution[0]))


# --------------------------------------------------------------------------
# Reading the page
# --------------------------------------------------------------------------


def _shown(page):
    """The counter as read: "Progress: N%" -> N (the whole text is checked)."""
    text = " ".join(page.locator("#puzzle-player-progress").text_content().split())
    assert text.startswith("Progress: ") and text.endswith("%"), text
    return int(text[len("Progress: "):-1])


_CODE = {U: "u", F: "f", E: "e", M: "m"}

_EVAL = """async ({ width, height, solutions, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY, m: S.MAYBE };
  return boards.map(([si, text]) => {
    const board = Object.freeze({ width, height, cells: Object.freeze([...text].map((ch) => codes[ch])) });
    if (!S.isBoard(board)) throw new Error('not a board');
    return S.solvedPercent(board, solutions[si]);
  });
}"""


def _evaluate(page, width, height, solutions, boards):
    got = page.evaluate(_EVAL, {
        "width": width, "height": height, "solutions": solutions,
        "boards": [[si, "".join(_CODE[s] for s in cells)] for si, cells in boards],
    })
    assert len(got) == len(boards)
    return got


# ==========================================================================
# EC-045 / AC-1 — the property corpus
# ==========================================================================

_SHAPES = [(10, 10), (15, 10), (10, 25), (30, 30)]
_PER_SHAPE = 300
_MIN_PER_SHAPE = 200
_KINDS = ("random", "solved", "solved_blank_whites", "near", "maybe", "missing")


def _corpus(width, height, rng):
    """Boards against a few solutions of one shape. Kinds: uniform random over
    all four states; solved (whites white or undecided at random); solved with
    every white undecided; near misses (a solved board with one cell wrong,
    undecided or "?"); "?" sprinkled over a solved board (never solved); and
    a solved board with one to five blacks left undecided."""
    solutions = [[[rng.random() < density for _ in range(width)] for _ in range(height)]
                 for density in (0.5, 0.3, 0.7, 0.55)]
    solutions.append([[False] * width for _ in range(height)])  # all empty
    solutions.append([[True] * width for _ in range(height)])  # all filled
    boards = []  # (solution index, cells, kind)
    for k in range(_PER_SHAPE):
        si = k % len(solutions)
        flat = [cell for row in solutions[si] for cell in row]
        kind = _KINDS[k % len(_KINDS)]
        if kind == "random":
            cells = [rng.choice((U, F, E, M)) for _ in flat]
        elif kind == "solved_blank_whites":
            cells = [F if cell else U for cell in flat]
        else:
            cells = [F if cell else rng.choice((E, U)) for cell in flat]
            if kind == "near":
                index = rng.randrange(len(flat))
                cells[index] = rng.choice((E, U, M)) if flat[index] else rng.choice((F, M))
            elif kind == "maybe":
                for index in rng.sample(range(len(flat)), rng.randint(1, 6)):
                    cells[index] = M
            elif kind == "missing":
                blacks = [index for index, cell in enumerate(flat) if cell]
                for index in rng.sample(blacks, min(len(blacks), rng.randint(1, 5))):
                    cells[index] = U
        boards.append((si, cells, kind))
    return solutions, boards


def _run_corpus(page, seed):
    rng = random.Random(seed)
    for width, height in _SHAPES:
        solutions, boards = _corpus(width, height, rng)
        got = _evaluate(page, width, height, solutions, [(si, cells) for si, cells, _ in boards])
        yield (width, height), solutions, boards, got


@pytest.mark.browser
def test_PropertyTest_SolverPercent_MatchesTheDefinition(browser_page, live) -> None:
    """EC-045 / AC-1 — solvedPercent equals the oracle on every board of the
    corpus, over four shapes, with the minimum counts asserted."""
    _open(browser_page, live, live.store(GRID))
    for shape, solutions, boards, got in _run_corpus(browser_page, seed=187):
        solved = [_solved(cells, solutions[si]) for si, cells, _ in boards]
        undecided_white = [
            ok and any(c == U and not s for c, s in zip(cells, (x for r in solutions[si] for x in r)))
            for (si, cells, _), ok in zip(boards, solved)
        ]
        assert len(boards) >= _MIN_PER_SHAPE, shape
        assert sum(solved) >= 50, (shape, sum(solved))
        assert sum(undecided_white) >= 30, (shape, sum(undecided_white))
        assert sum(M in cells for _, cells, _ in boards) >= 50, shape
        # Unsolved boards whose floor is 99 (a near miss on 900 cells): the
        # rounding rule, not only the solved override, is exercised.
        if shape == (30, 30):
            assert sum(not ok and _percent_of(cells, solutions[si]) == 99
                       for (si, cells, _), ok in zip(boards, solved)) >= 10, shape
        # Solved boards whose correct-cell floor is below 100 (undecided
        # whites): the override is exercised.
        assert sum(ok and 100 * _correct(cells, solutions[si]) // (shape[0] * shape[1]) < 100
                   for (si, cells, _), ok in zip(boards, solved)) >= 30, shape
        for index, ((si, cells, kind), percent) in enumerate(zip(boards, got)):
            assert percent == _percent_of(cells, solutions[si]), (shape, index, kind)


# ==========================================================================
# AC-2 — floor, and 100 only when solved
# ==========================================================================


@pytest.mark.browser
class TestSolverPercent_FloorsAndReaches100OnlyWhenSolved:
    """AC-2 / AC-352 — explicit 30 x 30 boards, and every unsolved board of
    the corpus reads at most 99."""

    def test_explicit_boards(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        rng = random.Random(352)
        sol = [[rng.random() < 0.5 for _ in range(30)] for _ in range(30)]
        flat = [cell for row in sol for cell in row]
        miss = next(i for i, cell in enumerate(flat) if cell)
        all_right = [F if cell else E for cell in flat]
        one_undecided = list(all_right)
        one_undecided[miss] = U
        one_wrong = list(all_right)
        one_wrong[miss] = E
        blank_whites = [F if cell else U for cell in flat]
        boards = [[U] * 900, one_undecided, one_wrong, blank_whites]
        assert [_correct(b, sol) for b in boards] == [0, 899, 899, sum(flat)]
        got = _evaluate(browser_page, 30, 30, [sol], [(0, b) for b in boards])
        assert got == [0, 99, 99, 100]

    def test_no_unsolved_board_reads_100(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        unsolved = 0
        for _, solutions, boards, got in _run_corpus(browser_page, seed=187):
            for (si, cells, _), percent in zip(boards, got):
                if not _solved(cells, solutions[si]):
                    unsolved += 1
                    assert percent <= 99
        assert unsolved >= 600


# ==========================================================================
# AC-3 — "?" never counts
# ==========================================================================


@pytest.mark.browser
class TestSolverPercent_QuestionMarksNeverCount:
    """AC-3 / AC-353 — on the live page."""

    def test_an_undecided_cell_marked_maybe_leaves_the_percent(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        # A board with some correct marks of both kinds, so the percent is not 0.
        cells = [F if cell else U for row in GRID for cell in row]
        for r, c in _EMPTY[:20]:
            cells[r * SIDE + c] = E
        for r, c in _FILLED[:5]:
            cells[r * SIDE + c] = U
        _set(browser_page, cells)
        before = _shown(browser_page)
        assert before == _percent_of(cells, GRID) > 0
        for target in (_FILLED[0], _EMPTY[-1]):  # undecided on both kinds of cell
            _tool(browser_page, "Maybe")
            _cell(browser_page, *target).click()
            after = _states(browser_page)
            assert after[target[0] * SIDE + target[1]] == M
            assert _shown(browser_page) == before == _percent_of(after, GRID)

    def test_one_maybe_on_a_white_blocks_100(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cells = [F if cell else E for row in GRID for cell in row]
        r, c = _EMPTY[0]
        cells[r * SIDE + c] = M
        _set(browser_page, cells)
        assert _shown(browser_page) == _percent_of(cells, GRID) == 99
        assert not _is_solved_shown(browser_page)


# ==========================================================================
# AC-4 — follows every recorded change, not the drag preview
# ==========================================================================

_WATCH = """() => {
  const el = document.querySelector('[data-player-progress]');
  window.__card187Writes = 0;
  new MutationObserver((records) => { window.__card187Writes += records.length; })
    .observe(el, { childList: true, characterData: true, subtree: true });
}"""


@pytest.mark.browser
class TestSolverPercent_FollowsEveryRecordedChange:
    """AC-4 / AC-351 — click, drag, Undo, Redo, Hint, confirmed Reset, Undo of
    it and setBoard, each read against the oracle; unchanged mid-drag."""

    def test_every_step(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        page = browser_page
        seen = [_shown(page)]
        assert seen == [0]

        def check():
            seen.append(_shown(page))
            assert seen[-1] == _percent_of(_states(page), GRID), seen

        _cell(page, *_FILLED[0]).click()  # Black brush, a correct first click
        check()
        # Row 2 is all filled in the solution: a 15-cell correct drag.
        assert all(GRID[2])
        page.mouse.move(*_centre(page, 2, 0))
        page.mouse.down()
        page.mouse.move(*_centre(page, 2, SIDE - 1), steps=6)
        preview = _states(page)
        assert preview[2 * SIDE + SIDE - 1] == F  # the preview is drawn ...
        assert _shown(page) == seen[-1]  # ... but not counted
        page.mouse.up()
        check()
        _button(page, "Undo").click()
        check()
        _button(page, "Redo").click()
        check()
        _button(page, "Hint").click()
        check()
        _button(page, "Reset").click()
        _button(page, "Clear board").click()
        check()
        _button(page, "Undo").click()
        check()
        cells = [F if cell else E for row in GRID for cell in row]
        cells[_FILLED[-1][0] * SIDE + _FILLED[-1][1]] = U
        _set(page, cells)
        check()
        assert seen == [0, seen[1], seen[2], seen[1], seen[2], seen[5], 0, seen[5], 99]
        # One cell of 225 floors to 0; the drag's 15 more to 7; the hint's
        # one more cell may or may not move the floor.
        assert seen[1] == 0 and 0 < seen[2] <= seen[5] < 99
        assert problems == []

    def test_an_unchanged_percent_is_not_rewritten(self, browser_page, live) -> None:
        """showProgress writes the count only when its text changes: a stroke
        that leaves the percent (a "?" on an undecided cell) writes nothing;
        one that changes it writes."""
        _open(browser_page, live, live.store(GRID))
        browser_page.evaluate(_WATCH)
        _tool(browser_page, "Maybe")
        _cell(browser_page, *_FILLED[0]).click()
        assert _states(browser_page)[_FILLED[0][0] * SIDE + _FILLED[0][1]] == M
        assert browser_page.evaluate("window.__card187Writes") == 0
        _tool(browser_page, "Black")
        _drag(browser_page, [(2, 0), (2, SIDE - 1)])  # 15 correct cells: 6%
        assert _shown(browser_page) > 0
        assert browser_page.evaluate("window.__card187Writes") > 0


# ==========================================================================
# AC-5 — where it sits (layout accepted as built, owner decision 2026-10-06)
# ==========================================================================

_LAYOUT = """() => {
  const q = (s) => document.querySelector(s);
  const box = (el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  const errors = q('#puzzle-player-errors'), hints = q('#puzzle-player-hints'), progress = q('#puzzle-player-progress');
  const after = (a, b) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
  const count = q('[data-player-progress]'), errCount = q('[data-player-errors]');
  return {
    order: after(errors, hints) && after(hints, progress),
    text: progress.textContent.replace(/\\s+/g, ' ').trim(),
    toolbar: box(q('.player-toolbar')),
    errors: box(errors), hints: box(hints), progress: box(progress),
    buttons: [...document.querySelectorAll('.player-tools > button, .player-history > button')].map(box),
    numeric: getComputedStyle(count).fontVariantNumeric,
    sameFont: getComputedStyle(count).fontFamily === getComputedStyle(errCount).fontFamily
      && getComputedStyle(count).fontSize === getComputedStyle(errCount).fontSize
      && getComputedStyle(count).color === getComputedStyle(errCount).color,
    pageWidth: document.scrollingElement.scrollWidth, viewport: innerWidth,
  };
}"""


def _layout(browser, live, width, height=900):
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        _open(page, live, live.store(GRID))
        return page.evaluate(_LAYOUT)
    finally:
        context.close()


@pytest.mark.browser
class TestSolverPercent_SitsNextToTheCounters:
    """AC-5 / AC-354 — DOM order Errors, Hints, Progress; "Progress: 0%";
    at 1440 on the error counter's row, left of it; at 1280 below the
    errors / hints pair, at the toolbar's right end, with the pair on the
    buttons' row and the buttons at the toolbar's top; no horizontal scroll
    at 390. The count looks like the error count (tabular numerals)."""

    @pytest.mark.parametrize("width", [1440, 1280, 390])
    def test_order_text_and_style(self, browser, live, width) -> None:
        got = _layout(browser, live, width)
        assert got["order"]
        assert got["text"] == "Progress: 0%"
        assert got["numeric"] == "tabular-nums"
        assert got["sameFont"]

    def test_same_row_left_of_errors_at_1440(self, browser, live) -> None:
        got = _layout(browser, live, 1440)
        pl, pt, pr, pb = got["progress"]
        el, et, er, eb = got["errors"]
        assert pt < eb and et < pb  # same row band
        assert pr <= el  # drawn left of "Errors: N"

    def test_below_the_pair_at_the_right_at_1280(self, browser, live) -> None:
        got = _layout(browser, live, 1280, 720)
        pl, pt, pr, pb = got["progress"]
        _, et, _, eb = got["errors"]
        _, ht, _, hb = got["hints"]
        assert pt >= max(eb, hb)  # below the pair
        assert abs(pr - got["toolbar"][2]) <= 1  # at the toolbar's right end
        tops = {round(b[1]) for b in got["buttons"]}
        assert tops == {round(got["toolbar"][1])}  # the buttons keep the row's top
        bt, bb = got["buttons"][0][1], got["buttons"][0][3]
        assert round((et + eb) / 2) == round((bt + bb) / 2)  # pair centred on the buttons' row

    def test_no_horizontal_scroll_at_390(self, browser, live) -> None:
        got = _layout(browser, live, 390, 844)
        assert got["pageWidth"] <= got["viewport"]


# ==========================================================================
# AC-6 — not a live region
# ==========================================================================

_LIVENESS = """() => {
  const bad = [];
  for (let el = document.getElementById('puzzle-player-progress'); el; el = el.parentElement) {
    const role = el.getAttribute('role');
    const live = el.getAttribute('aria-live');
    if (['status', 'alert', 'log'].includes(role) || (live !== null && live !== 'off')) bad.push(el.id || el.className || el.tagName);
  }
  return bad;
}"""


@pytest.mark.browser
class TestSolverPercent_DoesNotFloodScreenReaders:
    """AC-6 — neither the counter nor any ancestor is a live region, and five
    ordinary marks that change the percent put nothing into the announcer."""

    def test_silent(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        assert browser_page.evaluate(_LIVENESS) == []
        announce = browser_page.locator("#puzzle-player-announce")
        values = [_shown(browser_page)]
        for r, c in _FILLED[:5]:
            _cell(browser_page, r, c).click()
            values.append(_shown(browser_page))
            assert announce.text_content() == ""
        assert len(set(values)) >= 3  # the percent did change along the way
        assert browser_page.evaluate(_LIVENESS) == []


# ==========================================================================
# AC-7 — no request per mark
# ==========================================================================


@pytest.mark.browser
class TestSolverPercent_NoRequestPerMark:
    """AC-7 — 20 strokes, the percent changing, and no network request."""

    def test_twenty_strokes(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.context.on("request", lambda request: requests.append(request.url))
        before = _shown(browser_page)
        _twenty_strokes(browser_page)
        after = _shown(browser_page)
        assert after == _percent_of(_states(browser_page), GRID)
        assert after != before
        assert requests == []


# ==========================================================================
# CARD-185 — right after a reload restores the board
# ==========================================================================


@pytest.mark.browser
class TestSolverPercent_IsRightAfterAReloadRestoresTheBoard:
    """Marks, a reload (CARD-185 restores the board from this browser), and
    the percent read at once equals the oracle on the restored board."""

    def test_reload(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        r, c, e = LONG_RUN
        _drag(browser_page, [(r, c), (r, e)])
        _tool(browser_page, "White")
        for rr, cc in _EMPTY[:6]:
            _cell(browser_page, rr, cc).click()
        _cell(browser_page, *_FILLED[-1]).click()  # one wrong mark
        before = _states(browser_page)
        shown = _shown(browser_page)
        assert shown == _percent_of(before, GRID) > 0

        browser_page.reload()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        restored = _states(browser_page)
        assert restored == before
        assert _shown(browser_page) == _percent_of(restored, GRID) == shown
        assert problems == []
