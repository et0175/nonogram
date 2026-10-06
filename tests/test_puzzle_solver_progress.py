"""CARD-162 — the error count, the solved state and a confirmed reset
(FR-044 AC-312..AC-321, EC-036, EC-037).

The player page (``/puzzle/<id>/solve``, CARD-160/161) gains a live error
counter, a solved state that names the picture, plays a short animation (none
under prefers-reduced-motion) and locks the board until reset, and an in-page
confirmation in front of Reset.

Every user-facing criterion is checked in real Chromium. The stroke that the
criterion is about is always REAL input (``page.mouse``, ``locator.click``,
``page.keyboard``); ``puzzlePlayer.setBoard`` only sets up the board before it
(the CARD-161 seam: it replaces the board and starts a new history). Expected
counts and verdicts come from Python written here (``_errors_of``,
``_solved_of``), never from the JavaScript under test. EC-036/EC-037 evaluate
``solver_state.js`` ``errorCount`` / ``isSolved`` over a seeded corpus built
with ``random.Random`` (no ``hypothesis``), with the minimum counts asserted
inside the tests.

Fixtures (real Chromium refusing loudly when absent, ADR-0038/R8; a loopback
Flask panel over a temp SQLite store) are CARD-160's; page helpers are
CARD-161's.
"""

from __future__ import annotations

import random

import pytest

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
    _drag,
    _is_disabled,
    _marked,
    _states,
    _tool,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    _tight_row,
    browser_page,
    browser_type,
    live,
)

#: The picture name the solved state must show (stored as the puzzle's name).
NAME = "Lighthouse"


# --------------------------------------------------------------------------
# The definitions, written independently of solver_state.js
# --------------------------------------------------------------------------


def _errors_of(cells, solution):
    """FR-044: cells marked filled whose solution is empty, plus cells marked
    empty whose solution is filled — cell by cell. Undecided never counts."""
    width = len(solution[0])
    errors = 0
    for index, state in enumerate(cells):
        filled = solution[index // width][index % width]
        if state == F and not filled:
            errors += 1
        elif state == E and filled:
            errors += 1
    return errors


def _solved_of(cells, solution):
    """FR-044: every solution-filled cell marked filled and no solution-empty
    cell marked filled — cell by cell. Empty marks are optional."""
    width = len(solution[0])
    for index, state in enumerate(cells):
        filled = solution[index // width][index % width]
        if filled and state != F:
            return False
        if not filled and state == F:
            return False
    return True


def _solution_cells(grid, empty_state=U):
    """The board with exactly the solution's filled cells filled."""
    return [F if cell else empty_state for row in grid for cell in row]


def _grid_with_filled(width, counts, seed):
    """Tight rows (uniquely solvable) with exactly ``counts[r]`` filled cells."""
    rng = random.Random(seed)
    grid = []
    for filled in counts:
        runs = width - filled + 1
        cuts = sorted(rng.sample(range(1, filled), runs - 1))
        row = []
        for index, (start, end) in enumerate(zip([0] + cuts, cuts + [filled])):
            if index:
                row.append(False)
            row.extend([True] * (end - start))
        assert len(row) == width and sum(row) == filled
        grid.append(row)
    return grid


#: AC-315: 20 wide, 10 high, exactly 120 filled cells.
GRID_120 = _grid_with_filled(20, [11, 13, 12, 12, 11, 13, 12, 12, 11, 13], seed=315)

#: GRID's cells in row-major order: the last solution-filled cell, a
#: solution-empty cell, and a run boundary (filled, then empty, on one row).
_FILLED = [(r, c) for r in range(SIDE) for c in range(SIDE) if GRID[r][c]]
_EMPTY = [(r, c) for r in range(SIDE) for c in range(SIDE) if not GRID[r][c]]
LAST = _FILLED[-1]
BOUNDARY = next((r, c) for r, c in _FILLED if c + 1 < SIDE and not GRID[r][c + 1])
#: A run of at least two filled cells: (row, first column, last column).
LONG_RUN = next((r, c, e) for r in range(SIDE) for c in range(SIDE) for e in range(c + 1, SIDE)
                if all(GRID[r][c:e + 1]) and (c == 0 or not GRID[r][c - 1]) and (e + 1 == SIDE or not GRID[r][e + 1]))


# --------------------------------------------------------------------------
# Driving and reading the page
# --------------------------------------------------------------------------

_SET_BOARD = """(cells) => {
  const { width, height } = window.puzzlePlayer.payload;
  window.puzzlePlayer.setBoard(Object.freeze({ width, height, cells: Object.freeze(cells) }));
}"""


def _set(page, cells):
    """Set up the board (setBoard: new board, new history)."""
    page.evaluate(_SET_BOARD, list(cells))


def _error_count(page):
    counter = page.locator("[data-player-errors]")
    assert counter.is_visible()
    return int(counter.text_content())


def _banner(page):
    return page.locator("#puzzle-player-solved")


def _is_solved_shown(page):
    return _banner(page).is_visible()


def _near_solved(empty_state=U, extra=()):
    """GRID's solution with LAST still undecided, plus ``extra`` (cell, state)."""
    cells = _solution_cells(GRID, empty_state)
    cells[LAST[0] * SIDE + LAST[1]] = U
    for (r, c), state in extra:
        cells[r * SIDE + c] = state
    return cells


def _open_named(page, live, grid=GRID):
    _open(page, live, live.store(grid, name=NAME))


def _solve(page):
    """From a fresh page: set up GRID one cell short, then click it (real)."""
    _set(page, _near_solved(E))
    assert not _is_solved_shown(page)
    _cell(page, *LAST).click()
    assert _is_solved_shown(page)


def _thirty_marks(page):
    """30 marks by real drags: three rows, ten cells each, Black / White / Black."""
    _drag(page, [(2, 1), (2, 10)])
    _tool(page, "White")
    _drag(page, [(6, 3), (6, 12)])
    _tool(page, "Black")
    _drag(page, [(11, 4), (11, 13)])
    marks = _marked(_states(page))
    assert len(marks) == 30
    return marks


#: G-1 exception (CARD-185): sessionStorage is empty and localStorage holds at
#: most one key, this puzzle's save ("nonogram-player:" + its id).
_ONLY_THIS_SAVE = """() => sessionStorage.length === 0 && (localStorage.length === 0
  || (localStorage.length === 1 && localStorage.key(0) === 'nonogram-player:' + window.puzzlePlayer.payload.id))"""


def _watch_problems(page, live):
    problems = []
    page.on("console", lambda m: m.type in ("error", "warning") and problems.append(m.text))
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.on("requestfailed", lambda r: problems.append(f"failed: {r.url}"))
    page.on("response", lambda r: r.url.startswith(live.url) and r.status >= 400 and problems.append(f"{r.status}: {r.url}"))
    return problems


# ==========================================================================
# AC-312..AC-315 — the live error count
# ==========================================================================


@pytest.mark.browser
class TestSolverProgress_LiveErrorCount:
    """AC-312..AC-315 — the count is the current number of wrong marks."""

    def test_ac312_marking_a_solution_empty_cell_filled_reads_one(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        assert _error_count(browser_page) == 0
        _cell(browser_page, *_EMPTY[0]).click()
        assert _states(browser_page)[_EMPTY[0][0] * SIDE + _EMPTY[0][1]] == F
        assert _error_count(browser_page) == 1

    def test_ac313_a_white_drag_over_a_solution_filled_cell_reads_one(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        assert _error_count(browser_page) == 0
        r, c = BOUNDARY  # (r, c) is filled in the solution, (r, c + 1) is not
        _tool(browser_page, "White")
        _drag(browser_page, [(r, c), (r, c + 1)])
        assert _marked(_states(browser_page)) == {(r, c): E, (r, c + 1): E}
        assert _error_count(browser_page) == 1

    def test_ac314_undoing_the_wrong_stroke_reads_zero(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _cell(browser_page, *_EMPTY[0]).click()
        assert _error_count(browser_page) == 1
        _button(browser_page, "Undo").click()
        assert _marked(_states(browser_page)) == {}
        assert _error_count(browser_page) == 0

    def test_ac315_a_fresh_board_of_a_120_cell_solution_reads_zero(self, browser_page, live) -> None:
        _open_named(browser_page, live, GRID_120)
        solution = browser_page.evaluate("window.puzzlePlayer.payload.solution")
        assert sum(cell for row in solution for cell in row) == 120
        assert set(_states(browser_page)) == {U}
        assert _error_count(browser_page) == 0

    def test_the_count_follows_marks_and_corrections_not_a_running_total(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        row = next(r for r in range(SIDE) if not all(GRID[r]))
        _drag(browser_page, [(row, 0), (row, SIDE - 1)])  # the whole row black
        wrong = sum(not cell for cell in GRID[row])
        assert _error_count(browser_page) == wrong == _errors_of(_states(browser_page), GRID)
        _tool(browser_page, "White")
        _drag(browser_page, [(row, 0), (row, SIDE - 1)])  # the whole row white
        assert _error_count(browser_page) == SIDE - wrong == _errors_of(_states(browser_page), GRID)
        _tool(browser_page, "Undecided")
        _drag(browser_page, [(row, 0), (row, SIDE - 1)])  # undecided never counts
        assert _error_count(browser_page) == 0
        browser_page.keyboard.press("Control+z")
        assert _error_count(browser_page) == SIDE - wrong
        browser_page.keyboard.press("Shift+Control+z")
        assert _error_count(browser_page) == 0

    def test_a_click_that_cycles_a_wrong_black_to_white_corrects_it(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _cell(browser_page, *_EMPTY[0]).click()
        assert _error_count(browser_page) == 1
        _cell(browser_page, *_EMPTY[0]).click()  # filled -> marked empty: right
        assert _error_count(browser_page) == 0

    def test_the_count_is_a_live_region(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        region = browser_page.locator("#puzzle-player-errors")
        assert region.get_attribute("role") == "status"
        assert region.inner_text().split() == ["Errors:", "0"]

    def test_set_board_rederives_the_count(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        cells = [U] * (SIDE * SIDE)
        for r, c in _EMPTY[:3]:
            cells[r * SIDE + c] = F
        for r, c in _FILLED[:2]:
            cells[r * SIDE + c] = E
        _set(browser_page, cells)
        assert _error_count(browser_page) == 5 == _errors_of(cells, GRID)
        _set(browser_page, [U] * (SIDE * SIDE))
        assert _error_count(browser_page) == 0


# ==========================================================================
# AC-316 / AC-317 — the solved state
# ==========================================================================


@pytest.mark.browser
class TestSolverProgress_SolvedWhenBlacksMatch:
    """AC-316 / AC-317 — solved iff the blacks match; white marks optional."""

    @pytest.mark.parametrize("whites", ["none", "some", "all"])
    def test_ac316_the_completing_click_shows_the_picture_name(self, browser_page, live, whites) -> None:
        _open_named(browser_page, live)
        cells = _near_solved(U)
        chosen = {"none": [], "some": _EMPTY[::3], "all": _EMPTY}[whites]
        for r, c in chosen:
            cells[r * SIDE + c] = E
        _set(browser_page, cells)
        assert not _is_solved_shown(browser_page)
        assert browser_page.locator("#puzzle-player-announce").text_content() == ""

        _cell(browser_page, *LAST).click()

        assert _solved_of(_states(browser_page), GRID)
        banner = _banner(browser_page)
        assert banner.is_visible()
        assert banner.locator("[data-player-solved-name]").inner_text() == NAME
        assert " ".join(banner.inner_text().split()) == f"Solved: {NAME}"
        announce = browser_page.locator("#puzzle-player-announce")
        assert announce.get_attribute("role") == "status"
        assert " ".join(announce.text_content().split()) == f"Solved: {NAME}"
        assert _error_count(browser_page) == 0

    def test_ac316_the_completing_drag_solves_too(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        r, start, end = LONG_RUN  # undecide a whole run, then drag it back in
        cells = _solution_cells(GRID, U)
        for k in range(start, end + 1):
            cells[r * SIDE + k] = U
        _set(browser_page, cells)
        assert not _is_solved_shown(browser_page)
        _drag(browser_page, [(r, start), (r, end)])
        assert _is_solved_shown(browser_page)

    def test_ac317_a_stray_black_on_a_solution_empty_cell_is_not_solved(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        stray = _EMPTY[len(_EMPTY) // 2]
        _set(browser_page, _near_solved(U, extra=[(stray, F)]))
        _cell(browser_page, *LAST).click()  # every solution-filled cell now filled

        states = _states(browser_page)
        assert all(states[r * SIDE + c] == F for r, c in _FILLED)
        assert not _is_solved_shown(browser_page)
        assert _error_count(browser_page) == 1
        # Not locked: correcting the stray (filled -> marked empty) solves it.
        _cell(browser_page, *stray).click()
        assert _is_solved_shown(browser_page)

    def test_a_missing_black_with_no_errors_is_not_solved(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _set(browser_page, _near_solved(E))
        assert _error_count(browser_page) == 0
        assert not _is_solved_shown(browser_page)

    def test_the_banner_takes_the_tools_place_and_the_board_does_not_move(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _set(browser_page, _near_solved(U))
        before = browser_page.locator(".player-board").bounding_box()
        assert browser_page.locator(".player-tools").is_visible()
        _cell(browser_page, *LAST).click()
        assert not browser_page.locator(".player-tools").is_visible()
        assert browser_page.locator(".player-board").bounding_box() == before

    def test_the_success_frame_is_not_clipped_by_the_stage(self, browser_page, live) -> None:
        """The frame's outer edge, on every side, lies inside .player-stage,
        which scrolls and so clips whatever is drawn beyond its padding box."""
        _open_named(browser_page, live)
        _solve(browser_page)
        sides = browser_page.evaluate("""() => {
          const board = document.querySelector('.player-board');
          const stage = board.closest('.player-stage');
          const style = getComputedStyle(board);
          const out = parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth);
          const b = board.getBoundingClientRect();
          const s = stage.getBoundingClientRect();
          const clip = { left: s.left + stage.clientLeft, top: s.top + stage.clientTop };
          clip.right = clip.left + stage.clientWidth;
          clip.bottom = clip.top + stage.clientHeight;
          return {
            width: parseFloat(style.outlineWidth),
            left: b.left - out >= clip.left, top: b.top - out >= clip.top,
            right: b.right + out <= clip.right, bottom: b.bottom + out <= clip.bottom,
          };
        }""")
        assert sides == {"width": sides["width"], "left": True, "top": True, "right": True, "bottom": True}
        assert sides["width"] > 0

    def test_set_board_to_a_solved_board_shows_it_and_to_another_hides_it(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _set(browser_page, _solution_cells(GRID, E))
        assert _is_solved_shown(browser_page)
        _set(browser_page, _near_solved(E))
        assert not _is_solved_shown(browser_page)
        assert browser_page.locator("#puzzle-player-announce").text_content() == ""


# ==========================================================================
# AC-318 — locked until reset
# ==========================================================================


@pytest.mark.browser
class TestSolverProgress_LockedUntilReset:
    """AC-318 — in the solved state clicks, drags, undo and redo change no cell."""

    def test_ac318_click_drag_undo_redo_change_nothing(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _solve(browser_page)
        solved = _states(browser_page)
        assert _is_disabled(browser_page, "Undo") and _is_disabled(browser_page, "Redo")

        _cell(browser_page, *_FILLED[0]).click()
        _cell(browser_page, *_EMPTY[0]).click()
        _drag(browser_page, [(0, 0), (0, SIDE - 1)])
        _button(browser_page, "Undo").click(force=True)
        browser_page.keyboard.press("Control+z")
        _button(browser_page, "Redo").click(force=True)
        browser_page.keyboard.press("Shift+Control+z")

        assert _states(browser_page) == solved
        assert _is_solved_shown(browser_page)

    def test_a_click_changes_nothing(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _solve(browser_page)
        solved = _states(browser_page)
        for cell in (_FILLED[0], _EMPTY[0], LAST):
            _cell(browser_page, *cell).click()
        assert _states(browser_page) == solved

    def test_a_drag_changes_nothing_not_even_as_a_preview(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _solve(browser_page)
        solved = _states(browser_page)
        page = browser_page
        page.mouse.move(*_centre(page, 0, 0))
        page.mouse.down()
        page.mouse.move(*_centre(page, 0, SIDE - 1), steps=6)
        assert _states(page) == solved  # no preview either
        page.mouse.up()
        assert _states(page) == solved

    def test_undo_changes_nothing(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _solve(browser_page)  # the completing click is on the undo stack
        solved = _states(browser_page)
        _button(browser_page, "Undo").click(force=True)
        assert _states(browser_page) == solved
        browser_page.keyboard.press("Control+z")
        assert _states(browser_page) == solved

    def test_redo_changes_nothing(self, browser_page, live) -> None:
        """Undo of a reset made from the solved state brings the solved board
        back, and the lock with it — with the reset on the redo stack, which
        redo must not re-apply while locked (the documented reset decision)."""
        _open_named(browser_page, live)
        _solve(browser_page)
        solved = _states(browser_page)
        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()
        assert set(_states(browser_page)) == {U}
        assert not _is_solved_shown(browser_page)

        _button(browser_page, "Undo").click()  # unlocked board: undo acts
        assert _states(browser_page) == solved
        assert _is_solved_shown(browser_page)  # locked again
        assert _is_disabled(browser_page, "Redo") and _is_disabled(browser_page, "Undo")

        _button(browser_page, "Redo").click(force=True)
        assert _states(browser_page) == solved
        browser_page.keyboard.press("Shift+Control+z")
        assert _states(browser_page) == solved

    def test_reset_stays_available_while_locked(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _solve(browser_page)
        assert not _is_disabled(browser_page, "Reset")


# ==========================================================================
# AC-319 — prefers-reduced-motion
# ==========================================================================

_MOTION = """() => {
  const scope = [...document.querySelectorAll(
    '.player-toolbar, .player-toolbar *, .player-stage, .player-stage *')];
  return {
    animations: document.getAnimations().length,
    named: scope.filter((el) => getComputedStyle(el).animationName !== 'none').length,
    timed: scope.filter((el) => getComputedStyle(el).transitionDuration.split(',')
      .some((d) => parseFloat(d) !== 0)).length,
    checked: scope.length,
  };
}"""


def _solve_in(page, live):
    _open_named(page, live)
    _set(page, _near_solved(U))
    _cell(page, *LAST).click()


@pytest.mark.browser
class TestSolverProgress_ReducedMotion:
    """AC-319 — reduced motion: the same reveal, nothing animated."""

    def test_ac319_solved_with_no_animation_or_transition(self, browser, live) -> None:
        context = browser.new_context(reduced_motion="reduce")
        page = context.new_page()
        try:
            _solve_in(page, live)
            motion = page.evaluate(_MOTION)
            assert _is_solved_shown(page)
            assert page.locator("[data-player-solved-name]").inner_text() == NAME
            assert motion["checked"] > SIDE * SIDE
            assert motion == {**motion, "animations": 0, "named": 0, "timed": 0}
            page.wait_for_timeout(100)
            assert page.evaluate("document.getAnimations().length") == 0
        finally:
            context.close()

    def test_without_reduced_motion_the_solve_is_animated(self, browser, live) -> None:
        """The control: the same solve does animate (so AC-319's zero is real)."""
        context = browser.new_context(reduced_motion="no-preference")
        page = context.new_page()
        try:
            _solve_in(page, live)
            motion = page.evaluate(_MOTION)
            assert motion["animations"] > 0 and motion["named"] > 0
            # The board itself animates (the filled cells' sweep), not only the banner.
            animated_cells = page.evaluate(
                "[...document.querySelectorAll('td.player-cell')].filter((td) => td.getAnimations().length > 0).length")
            assert animated_cells == sum(cell for row in GRID for cell in row)
            assert page.locator("#puzzle-player-solved").evaluate("(el) => el.getAnimations().length") == 1
            # Short: everything has finished within two seconds.
            page.wait_for_function("document.getAnimations().every((a) => a.playState === 'finished')", timeout=2000)
        finally:
            context.close()


# ==========================================================================
# AC-320 / AC-321 — reset after an in-page confirmation
# ==========================================================================


@pytest.mark.browser
class TestSolverProgress_ResetAfterConfirm:
    """AC-320 / AC-321 — Reset asks in the page; accept clears, cancel keeps."""

    @staticmethod
    def _dialogs(page):
        seen = []
        page.on("dialog", lambda dialog: (seen.append(dialog.type), dialog.dismiss()))
        return seen

    def test_ac320_thirty_marks_cleared_after_accepting(self, browser_page, live) -> None:
        dialogs = self._dialogs(browser_page)
        _open_named(browser_page, live)
        _thirty_marks(browser_page)
        assert _error_count(browser_page) == _errors_of(_states(browser_page), GRID) > 0

        _button(browser_page, "Reset").click()
        confirm = browser_page.get_by_role("alertdialog", name="Clear the board?")
        assert confirm.is_visible()
        assert len(_marked(_states(browser_page))) == 30  # nothing cleared yet
        _button(browser_page, "Clear board").click()

        assert not confirm.is_visible()
        assert set(_states(browser_page)) == {U}
        assert _error_count(browser_page) == 0
        _cell(browser_page, 4, 4).click()  # marks accepted again
        assert _marked(_states(browser_page)) == {(4, 4): F}
        assert dialogs == []

    def test_ac320_the_solved_board_cleared_after_accepting(self, browser_page, live) -> None:
        dialogs = self._dialogs(browser_page)
        _open_named(browser_page, live)
        _solve(browser_page)

        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()

        assert set(_states(browser_page)) == {U}
        assert _error_count(browser_page) == 0
        assert not _is_solved_shown(browser_page)
        assert browser_page.locator(".player-tools").is_visible()
        _cell(browser_page, 4, 4).click()  # a click is accepted again
        _drag(browser_page, [(7, 2), (7, 5)])  # and a drag
        assert _marked(_states(browser_page)) == {(4, 4): F, **{(7, c): F for c in range(2, 6)}}
        assert not _is_disabled(browser_page, "Undo")
        assert dialogs == []

    def test_ac321_cancelling_keeps_all_thirty_marks(self, browser_page, live) -> None:
        dialogs = self._dialogs(browser_page)
        _open_named(browser_page, live)
        marks = _thirty_marks(browser_page)
        errors = _error_count(browser_page)

        _button(browser_page, "Reset").click()
        _button(browser_page, "Keep marks").click()

        assert not browser_page.locator("#puzzle-player-confirm").is_visible()
        assert _marked(_states(browser_page)) == marks
        assert _error_count(browser_page) == errors
        assert dialogs == []

    def test_escape_cancels_and_focus_returns_to_reset(self, browser_page, live) -> None:
        dialogs = self._dialogs(browser_page)
        _open_named(browser_page, live)
        marks = _thirty_marks(browser_page)

        _button(browser_page, "Reset").click()
        assert browser_page.evaluate(_FOCUSED) == "Keep marks"  # focus moved in
        browser_page.keyboard.press("Escape")

        assert not browser_page.locator("#puzzle-player-confirm").is_visible()
        assert browser_page.evaluate(_FOCUSED) == "Reset"  # and back
        assert _marked(_states(browser_page)) == marks
        assert dialogs == []

    def test_the_confirmation_is_keyboard_operable(self, browser_page, live) -> None:
        dialogs = self._dialogs(browser_page)
        _open_named(browser_page, live)
        marks = _thirty_marks(browser_page)
        reset = _button(browser_page, "Reset")
        assert reset.get_attribute("aria-expanded") == "false"

        reset.focus()
        browser_page.keyboard.press("Enter")
        assert reset.get_attribute("aria-expanded") == "true"
        assert browser_page.evaluate(_FOCUSED) == "Keep marks"
        browser_page.keyboard.press("Enter")  # Keep marks
        assert _marked(_states(browser_page)) == marks
        assert browser_page.evaluate(_FOCUSED) == "Reset"

        browser_page.keyboard.press("Space")
        browser_page.keyboard.press("Shift+Tab")
        assert browser_page.evaluate(_FOCUSED) == "Clear board"
        browser_page.keyboard.press("Space")
        assert set(_states(browser_page)) == {U}
        assert browser_page.evaluate(_FOCUSED) == "Reset"
        assert dialogs == []

    # A change to the board while the confirmation is open closes it, as
    # "Keep marks" does (focus back to Reset), after recording the change.
    # "redo-key-noop" is a redo with an empty redo stack (the precondition
    # click below drops it): the history does not change, and the
    # confirmation still closes (PROGRESS "reset": "even one that changes
    # nothing"). "redo-button-noop" is the same no-op from the Redo button,
    # clicked while it says aria-disabled="true" (force: Playwright treats
    # aria-disabled as not clickable) — the header promises "button or key"
    # (CARD-162 F-010).
    _CHANGES = {
        "undo-key": lambda page: page.keyboard.press("Control+z"),
        "undo-button": lambda page: _button(page, "Undo").click(),
        "stroke": lambda page: _cell(page, SIDE - 1, SIDE - 1).click(),
        "set-board": lambda page: _set(page, [U] * (SIDE * SIDE)),
        "redo-key-noop": lambda page: page.keyboard.press("Control+Shift+z"),
        "redo-button-noop": lambda page: _button(page, "Redo").click(force=True),
    }

    @pytest.mark.parametrize("change", list(_CHANGES))
    def test_a_board_change_while_asking_closes_the_confirmation(self, browser_page, live, change) -> None:
        _open_named(browser_page, live)
        _cell(browser_page, SIDE - 1, 0).click()
        reset = _button(browser_page, "Reset")
        reset.click()
        assert browser_page.locator("#puzzle-player-confirm").is_visible()
        before = _states(browser_page)

        self._CHANGES[change](browser_page)

        assert not browser_page.locator("#puzzle-player-confirm").is_visible()
        assert reset.get_attribute("aria-expanded") == "false"
        assert browser_page.evaluate(_FOCUSED) == "Reset"
        if change in ("redo-key-noop", "redo-button-noop"):
            assert _states(browser_page) == before  # really a no-op
            assert _is_disabled(browser_page, "Redo")
            assert not _is_disabled(browser_page, "Reset")
            return
        expected = {(SIDE - 1, 0): F, (SIDE - 1, SIDE - 1): F} if change == "stroke" else {}
        assert _marked(_states(browser_page)) == expected
        assert _is_disabled(browser_page, "Reset") is (change != "stroke")

    def test_a_board_change_with_the_confirmation_closed_leaves_focus_alone(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        _cell(browser_page, SIDE - 1, 0).click()
        _button(browser_page, "Undo").click()
        assert browser_page.evaluate(_FOCUSED) == "Undo"
        _cell(browser_page, SIDE - 1, 0).click()
        assert browser_page.evaluate(_FOCUSED) == "Undo"

    def test_a_disabled_reset_opens_no_confirmation(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        assert _is_disabled(browser_page, "Reset")
        _button(browser_page, "Reset").click(force=True)
        assert not browser_page.locator("#puzzle-player-confirm").is_visible()

    def test_the_reset_from_solved_is_one_undoable_step(self, browser_page, live) -> None:
        """The decision: reset stays an undoable step from the solved state;
        undoing it returns the solved board AND its lock."""
        _open_named(browser_page, live)
        _solve(browser_page)
        solved = _states(browser_page)
        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()
        _button(browser_page, "Undo").click()
        assert _states(browser_page) == solved
        assert _is_solved_shown(browser_page)
        _cell(browser_page, *_EMPTY[0]).click()  # locked again
        assert _states(browser_page) == solved


# ==========================================================================
# ADR-0038/R2, G-3 — client-side only, nothing persisted, console clean
# ==========================================================================


@pytest.mark.browser
class TestSolverProgress_StaysInThePage:
    """The solve and reset flows issue no request, store nothing and log nothing."""

    def test_solve_and_reset_issue_no_request_store_nothing_and_log_nothing(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        _open_named(browser_page, live)
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.context.on("request", lambda request: requests.append(request.url))

        _cell(browser_page, *_EMPTY[0]).click()
        _button(browser_page, "Undo").click()
        _solve(browser_page)
        for name in ("Reset", "Keep marks", "Reset", "Clear board", "Undo"):
            _button(browser_page, name).click()
        browser_page.keyboard.press("Escape")

        assert _is_solved_shown(browser_page)
        assert requests == []
        assert browser_page.evaluate(_ONLY_THIS_SAVE)
        assert problems == []


# ==========================================================================
# The pure functions, case by case
# ==========================================================================

_PURE = """async (cases) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY };
  return cases.map(({ width, height, cells, solution }) => {
    const board = Object.freeze({ width, height, cells: Object.freeze([...cells].map((ch) => codes[ch])) });
    if (!S.isBoard(board)) throw new Error('not a board');
    return [S.errorCount(board, solution), S.isSolved(board, solution)];
  });
}"""


@pytest.mark.browser
class TestSolverProgressModule:
    """solver_state.js errorCount / isSolved on hand-picked boards."""

    CASES = [
        # (cells, solution rows, expected errors, expected solved)
        ("uu", [[True, False]], 0, False),  # undecided never counts
        ("fu", [[True, False]], 0, True),  # white marks optional
        ("fe", [[True, False]], 0, True),
        ("ff", [[True, False]], 1, False),  # black on a solution-empty cell
        ("eu", [[True, False]], 1, False),  # white on a solution-filled cell
        ("ef", [[True, False]], 2, False),
        ("uu", [[False, False]], 0, True),  # an all-empty solution: blank solves
        ("eeee", [[False, False], [False, False]], 0, True),
        ("fuuf", [[True, False], [False, True]], 0, True),  # 2 x 2, row-major
        ("ufuf", [[True, False], [False, True]], 1, False),
        ("fffe", [[False, True, True, True]], 2, False),  # 1 x 4 vs 4 x 1
        ("feef", [[True], [False], [False], [True]], 0, True),
    ]

    def test_cases(self, browser_page, live) -> None:
        _open_named(browser_page, live)
        cases = [
            {"width": len(sol[0]), "height": len(sol), "cells": cells, "solution": sol}
            for cells, sol, _, _ in self.CASES
        ]
        got = browser_page.evaluate(_PURE, cases)
        assert got == [[errors, solved] for _, _, errors, solved in self.CASES]


# ==========================================================================
# EC-036 / EC-037 — the property corpus
# ==========================================================================

#: (width, height): square and non-square, smallest to largest.
_SHAPES = [(10, 10), (15, 10), (10, 25), (30, 30)]
_PER_SHAPE = 300
_MIN_PER_SHAPE = 200
_CODE = {U: "u", F: "f", E: "e"}


def _corpus(width, height, rng):
    """Boards against a few solutions of one shape. Kinds: uniform random
    (almost never solved), solved (the solution's blacks, each white cell
    randomly white or undecided), near misses (a solved board with exactly
    one wrong or missing cell), missing (a solved board with one to five
    blacks left undecided — no error, not solved) and noisy (mostly right)."""
    solutions = [[[rng.random() < density for _ in range(width)] for _ in range(height)]
                 for density in (0.5, 0.3, 0.7, 0.55)]
    solutions.append([[False] * width for _ in range(height)])  # all empty
    solutions.append([[True] * width for _ in range(height)])  # all filled
    boards = []  # (solution index, cells, kind)
    for k in range(_PER_SHAPE):
        si = k % len(solutions)
        sol = solutions[si]
        flat = [cell for row in sol for cell in row]
        kind = ("random", "solved", "near", "missing", "noisy")[k % 5]
        if kind == "random":
            cells = [rng.choice((U, F, E)) for _ in flat]
        else:
            cells = [F if cell else rng.choice((E, U)) for cell in flat]
            if kind == "near":
                index = rng.randrange(len(flat))
                cells[index] = rng.choice((E, U)) if flat[index] else F
            elif kind == "missing":
                blacks = [index for index, cell in enumerate(flat) if cell]
                for index in rng.sample(blacks, min(len(blacks), rng.randint(1, 5))):
                    cells[index] = U
            elif kind == "noisy":
                for index in range(len(flat)):
                    if rng.random() < 0.02:
                        cells[index] = rng.choice((U, F, E))
        boards.append((si, cells, kind))
    return solutions, boards


_EVAL = """async ({ width, height, solutions, boards }) => {
  const S = await import('/static/solver_state.js');
  const codes = { u: S.UNKNOWN, f: S.FILLED, e: S.EMPTY };
  return boards.map(([si, text]) => {
    const board = Object.freeze({ width, height, cells: Object.freeze([...text].map((ch) => codes[ch])) });
    if (!S.isBoard(board)) throw new Error('not a board');
    return [S.errorCount(board, solutions[si]), S.isSolved(board, solutions[si])];
  });
}"""


def _run_corpus(page, seed):
    """Per shape: the corpus, the module's answers and the oracle's."""
    rng = random.Random(seed)
    results = []
    for width, height in _SHAPES:
        solutions, boards = _corpus(width, height, rng)
        got = page.evaluate(_EVAL, {
            "width": width, "height": height, "solutions": solutions,
            "boards": [[si, "".join(_CODE[s] for s in cells)] for si, cells, _ in boards],
        })
        assert len(got) == len(boards)
        results.append(((width, height), solutions, boards, got))
    return results


@pytest.mark.browser
def test_PropertyTest_SolverProgress_SolvedMatchesTheSolution(browser_page, live) -> None:
    """EC-036 — isSolved is true iff a cell-by-cell comparison finds every
    solution-filled cell filled and no solution-empty cell filled."""
    _open_named(browser_page, live)
    for shape, solutions, boards, got in _run_corpus(browser_page, seed=36):
        expected = [_solved_of(cells, solutions[si]) for si, cells, _ in boards]
        solved = sum(expected)
        near_misses = sum(kind == "near" for _, _, kind in boards)
        assert len(boards) >= _MIN_PER_SHAPE, shape
        assert solved >= 50 and len(boards) - solved >= 150, (shape, solved)
        assert near_misses >= 50, shape
        # Unsolved with no error at all (a black still missing): the solved
        # check is not "error count == 0".
        assert sum(not ok and _errors_of(cells, solutions[si]) == 0
                   for (si, cells, _), ok in zip(boards, expected)) >= 20, shape
        for index, ((si, cells, kind), (_, verdict)) in enumerate(zip(boards, got)):
            assert verdict is expected[index], (shape, index, kind)


@pytest.mark.browser
def test_PropertyTest_SolverProgress_ErrorCountMatchesTheDefinition(browser_page, live) -> None:
    """EC-037 — errorCount equals the cells marked filled whose solution is
    empty plus those marked empty whose solution is filled, over EC-036's
    corpus."""
    _open_named(browser_page, live)
    for shape, solutions, boards, got in _run_corpus(browser_page, seed=36):
        expected = [_errors_of(cells, solutions[si]) for si, cells, _ in boards]
        assert len(boards) >= _MIN_PER_SHAPE, shape
        assert sum(e > 0 for e in expected) >= 100, shape
        assert sum(e == 1 for e in expected) >= 20, shape  # near misses with one wrong mark
        # Boards with undecided cells on both kinds of solution cell, so an
        # undecided cell counted as an error would show.
        def undecided_on(want, si, cells):
            flat = (x for r in solutions[si] for x in r)
            return any(c == U for c, s in zip(cells, flat) if s is want)
        assert sum(undecided_on(True, si, cells) for si, cells, _ in boards) >= 100, shape
        assert sum(undecided_on(False, si, cells) for si, cells, _ in boards) >= 100, shape
        for index, ((si, cells, kind), (count, _)) in enumerate(zip(boards, got)):
            assert count == expected[index], (shape, index, kind)


@pytest.mark.browser
def test_PropertyTest_SolverProgress_PageShowsWhatTheDefinitionSays(browser_page, live) -> None:
    """The page wiring: for seeded boards set on the live 15 x 15 page, the
    counter and the banner show the oracle's count and verdict."""
    _open_named(browser_page, live)
    rng = random.Random(162)
    flat = [cell for row in GRID for cell in row]
    shown_solved = 0
    for k in range(40):
        if k % 3 == 0:
            cells = [F if cell else rng.choice((E, U)) for cell in flat]
        else:
            cells = [rng.choice((U, F, E)) if rng.random() < 0.1 else (F if cell else U) for cell in flat]
        _set(browser_page, cells)
        assert _error_count(browser_page) == _errors_of(cells, GRID), k
        assert _is_solved_shown(browser_page) is _solved_of(cells, GRID), k
        shown_solved += _solved_of(cells, GRID)
    assert 10 <= shown_solved <= 30, shown_solved
