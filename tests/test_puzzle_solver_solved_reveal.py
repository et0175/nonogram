"""CARD-280 — the solved board stops being a worksheet and becomes the picture.

Owner request 2026-10-23 ("make an animation after the user solves the puzzle
more festive") and ruling 2026-11-10 ("do as you propose": "Solved!" with the
solve's own count instead of the public key; the picture without its worksheet;
the sweep through the picture). Two cells, the owner's test budget:

* the sweep's values are a pure function of the board (AC-7), held to a
  breadth-first search written here;
* one browser cell walks a real solve through every state the card names
  (AC-1 .. AC-6): the chrome goes and the frame stays, no cell moves, a redraw
  and a reload keep the picture without replaying the celebration, an undo
  brings the worksheet back, "Show grid" toggles it, and under reduced motion
  the picture is the same with nothing animating.
The banner's words (AC-8) are held where the solve already is: the no-hint
solve in tests/test_puzzle_solver_progress.py and the hinted one in
tests/test_puzzle_solver_hint.py.
"""

from __future__ import annotations

import random
from collections import deque

import pytest

from tests.test_puzzle_solver_marking import GRID, _button, _drag, _states, _tool
from tests.test_puzzle_solver_page import _open, browser_page, browser_type, live  # noqa: F401

#: A 5 x 5 the cell solves with real, saved strokes (so a reload restores it):
#: columns 0-3 dark and column 4
#: white. Its clues admit only this grid.
SMALL = [[True, True, True, True, False] for _ in range(5)]
NAME = "Stripes"


def _bfs_wave(width, height, filled):
    """Independent of solver_state.js: per cell, its distance through filled
    edge-neighbours from the first filled cell (reading order) of its part."""
    wave = [0] * (width * height)
    seen = set()
    for start in range(width * height):
        if start not in filled or start in seen:
            continue
        seen.add(start)
        queue = deque([(start, 0)])
        while queue:
            at, dist = queue.popleft()
            wave[at] = dist
            r, c = divmod(at, width)
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                near = rr * width + cc
                if 0 <= rr < height and 0 <= cc < width and near in filled and near not in seen:
                    seen.add(near)
                    queue.append((near, dist + 1))
    return wave


@pytest.mark.browser
class TestSolvedReveal_TheWaveIsAPureFunctionOfTheFilledRegion:
    """AC-7: pictureWave over a seeded corpus of boards equals the BFS above,
    every value a finite integer, and a board in two disconnected parts gives
    each part its own run starting at 0. Plant: seed every part from the
    first part's start -> red."""

    def test_the_wave_runs_through_the_picture(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        rng = random.Random(280)
        boards = []
        for _ in range(300):
            width, height = rng.randint(1, 12), rng.randint(1, 12)
            density = rng.choice((0.2, 0.45, 0.7))
            boards.append((width, height, [rng.random() < density for _ in range(width * height)]))
        boards.append((5, 1, [True, True, False, True, True]))  # two parts in one row
        got = browser_page.evaluate("""async (boards) => {
          const S = await import('/static/solver_state.js');
          return boards.map(([w, h, cells]) => [...S.pictureWave({ width: w, height: h,
            cells: cells.map((on) => (on ? S.FILLED : S.EMPTY)) })]);
        }""", boards)
        wrong = [(w, h, g) for (w, h, cells), g in zip(boards, got)
                 if g != _bfs_wave(w, h, {i for i, on in enumerate(cells) if on})]
        assert wrong == [], wrong[:2]
        assert all(isinstance(v, int) and v >= 0 for g in got for v in g)
        assert got[-1] == [0, 1, 0, 0, 1]  # each part from its own start
        assert sum(1 for g in got if max(g, default=0) >= 5) >= 50  # long runs exist


_BOARD = """() => {
  const table = document.querySelector('.player-board');
  const cell = (r, c) => document.querySelector(`td.player-cell[data-row="${r}"][data-col="${c}"]`);
  const look = (el) => getComputedStyle(el);
  const empty = document.querySelector('td.player-cell[data-state="empty"]');
  return {
    solved: table.classList.contains('is-solved'),
    celebrating: table.classList.contains('is-celebrating'),
    hairline: look(cell(0, 0)).borderRightColor,
    dot: empty ? getComputedStyle(empty, '::after').visibility : null,
    clue: look(document.querySelector('th.player-clue')).opacity,
    frame: look(table).outlineStyle,
    boxes: [...document.querySelectorAll('td.player-cell')].map((td) => {
      const b = td.getBoundingClientRect(); return [td.dataset.state, Math.round(b.left), Math.round(b.top)]; }),
  };
}"""


def _settle(page):
    page.evaluate("Promise.all(document.getAnimations().map((a) => a.finished.catch(() => null)))")


@pytest.mark.browser
class TestSolvedReveal_ThePictureStaysAndTheCelebrationRunsOnce:
    """AC-1 .. AC-6 on one real solve (the last cell clicked):

    * AC-1/AC-2: solved -> the hairlines are transparent, the white dots and
      the clues hidden, the success frame drawn; every cell keeps its state
      and its box;
    * the celebration class is on after the genuine solve, and off again;
    * AC-3: a redraw (a resize across the phone breakpoint and back) keeps the
      picture and does not put the celebration back;
    * AC-4: a reload of the saved solved board shows the picture, no
      celebration;
    * "Show grid" puts the worksheet back, and again takes it away;
    * AC-5: a solved board is LOCKED (undo and redo do nothing on it), so a
      confirmed Reset is what un-solves it, and the worksheet returns (the
      card's undo/redo arm cannot occur; declared here);
    * AC-6: under prefers-reduced-motion the same picture state, and nothing
      running on the board.
    Plant: the picture rules keyed on .is-celebrating (gone after the beat)
    instead of .is-solved -> the reload arm red.
    """

    def test_a_real_solve_reveals_the_picture(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size({"width": 1280, "height": 900})
        _open(page, live, live.store(SMALL, name=NAME))
        _tool(page, "White")
        _drag(page, [(0, 4), (4, 4)])  # the white column, before the board locks
        _tool(page, "Black")
        for col in range(3):
            _drag(page, [(0, col), (4, col)])
        before = page.evaluate(_BOARD)
        assert not before["solved"] and before["clue"] == "1" and before["dot"] == "visible", before

        _drag(page, [(0, 3), (4, 3)])  # the solving stroke
        solving = page.evaluate(_BOARD)
        assert solving["solved"] and solving["celebrating"], solving
        _settle(page)
        page.wait_for_function("!document.querySelector('.player-board').classList.contains('is-celebrating')", timeout=6000)
        solved = page.evaluate(_BOARD)
        assert solved["hairline"] == "rgba(0, 0, 0, 0)" and solved["dot"] == "hidden" and solved["clue"] == "0", solved
        assert solved["frame"] == "solid"
        changed = [(a, b) for a, b in zip(before["boxes"], solved["boxes"]) if a[1:] != b[1:]]
        assert changed == [], changed[:3]  # no cell moved
        assert [b[0] for b in solved["boxes"]] == _states(page)

        page.set_viewport_size({"width": 700, "height": 900})  # a redraw across the breakpoint
        page.wait_for_timeout(200)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(200)
        redrawn = page.evaluate(_BOARD)
        assert redrawn["solved"] and not redrawn["celebrating"] and redrawn["clue"] == "0", redrawn

        page.reload()
        page.wait_for_function("window.puzzlePlayer !== undefined")
        reloaded = page.evaluate(_BOARD)
        assert reloaded["solved"] and not reloaded["celebrating"] and reloaded["dot"] == "hidden", reloaded

        page.get_by_role("button", name="Show grid").click()
        _settle(page)
        grid = page.evaluate(_BOARD)
        assert grid["clue"] == "1" and grid["dot"] == "visible", grid
        assert page.get_by_role("button", name="Show grid").get_attribute("aria-pressed") == "true"
        page.get_by_role("button", name="Show grid").click()
        _settle(page)
        assert page.evaluate(_BOARD)["clue"] == "0"

        # AC-6: the same picture under reduced motion, nothing running.
        page.emulate_media(reduced_motion="reduce")
        page.reload()
        page.wait_for_function("window.puzzlePlayer !== undefined")
        calm = page.evaluate(_BOARD)
        assert calm["solved"] and calm["clue"] == "0" and calm["dot"] == "hidden", calm
        assert page.evaluate("document.querySelector('.player-stage').getAnimations({ subtree: true }).length") == 0
        page.emulate_media(reduced_motion="no-preference")

        # AC-5: a solved board is LOCKED (Undo and Redo do nothing on it), so
        # what un-solves it is a confirmed Reset — and the worksheet returns.
        _button(page, "Reset").click()
        page.locator('[data-player-confirm="accept"]').click()
        _settle(page)
        reset = page.evaluate(_BOARD)
        assert not reset["solved"] and reset["clue"] == "1" and not reset["celebrating"], reset
        assert page.get_by_role("button", name="Show grid").count() == 0  # gone with the solve
