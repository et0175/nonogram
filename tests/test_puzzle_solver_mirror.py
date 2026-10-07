"""CARD-193 — boards wider than 15 columns mirror their row clues to the right,
on phones only (FR-044, owner decision 2026-10-06).

A board whose width (W, columns) exceeds 15 draws its row-clue gutter on the
RIGHT instead of the left, at viewports <= 820 px only — desktop sizing and
layout are unchanged (G-1). ``solver.js`` adds ``is-mirrored`` to
``table.player-board`` and reorders each body row's children (the row-clue
box moves after the cells) and the head row's children (the corner moves
after the last column clue); the ``cells`` array solver.js returns from
``drawBoard`` stays row-major regardless (the marking code depends on it —
only DOM placement changes). The mirror follows the viewport via a
``matchMedia("(max-width: 820px)")`` listener that redraws the board from the
CURRENT recorded history, so marks, undo/redo and the save survive crossing
the breakpoint.

Browser tests only (pytest-playwright + Chromium, ADR-0038/R7), using
CARD-160's fixtures.
"""

from __future__ import annotations

import pytest

from tests.test_puzzle_solver_marking import _button, _centre
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)

U, F, E = "unknown", "filled", "empty"

PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1440, "height": 900}

#: AC-5 / AC-7 / AC-8: a 25-wide (> 15), 15-tall board.
GRID_25x15 = _unique_grid(25, 15, seed=193)
ROW_CLUES_25x15 = [_encode(row) for row in GRID_25x15]

#: AC-6: a 15-wide board (never mirrors) and a 16-wide one (always mirrors,
#: on phones) — the W > 15 boundary, exactly at and just past it.
GRID_15_WIDE = _unique_grid(15, 25, seed=1930)
GRID_16_WIDE = _unique_grid(16, 15, seed=1931)


_STRUCTURE = """() => {
  const table = document.querySelector('.player-board');
  const head = table.querySelector('thead tr');
  const rows = [...table.querySelectorAll('tbody tr')];
  const tag = (el) => ({ tag: el.tagName, cls: el.className });
  return {
    isMirrored: table.classList.contains('is-mirrored'),
    headFirst: tag(head.firstElementChild),
    headLast: tag(head.lastElementChild),
    rowFirst: rows.map((tr) => tag(tr.firstElementChild)),
    rowLast: rows.map((tr) => tag(tr.lastElementChild)),
    rowClueTexts: [...document.querySelectorAll('th.player-clue.is-row')].map(
      (th) => [...th.querySelectorAll('.player-clue-num')].map((n) => n.textContent)),
  };
}"""


def _structure(page):
    return page.evaluate(_STRUCTURE)


def _is_cell(tag) -> bool:
    return tag["tag"] == "TD" and "player-cell" in tag["cls"].split()


def _is_row_clue(tag) -> bool:
    return tag["tag"] == "TH" and "player-clue" in tag["cls"].split() and "is-row" in tag["cls"].split()


def _is_corner(tag) -> bool:
    return tag["tag"] == "TD" and tag["cls"].split() == ["player-corner"]


def _is_col_clue(tag) -> bool:
    return tag["tag"] == "TH" and "player-clue" in tag["cls"].split() and "is-col" in tag["cls"].split()


# ==========================================================================
# AC-5 — mirrored DOM placement at phone width; unmirrored (desktop
# unchanged, G-1) at 1440
# ==========================================================================


@pytest.mark.browser
class TestSolverMirror_RowCluesOnTheRightAboveFifteen:
    """AC-5 / AC-6."""

    def test_a_25_wide_board_mirrors_at_phone_and_not_at_desktop(self, browser_page, live) -> None:
        page = browser_page
        puzzle_id = live.store(GRID_25x15)

        page.set_viewport_size(PHONE)
        _open(page, live, puzzle_id)
        phone = _structure(page)

        assert phone["isMirrored"] is True
        assert _is_corner(phone["headFirst"]) is False
        assert _is_col_clue(phone["headFirst"]) is True
        assert _is_corner(phone["headLast"]) is True
        for first, last in zip(phone["rowFirst"], phone["rowLast"]):
            assert _is_cell(first), first
            assert _is_row_clue(last), last
        # The row clues still read top to bottom in payload order (AC-5).
        assert phone["rowClueTexts"] == [[str(n) for n in clue] for clue in ROW_CLUES_25x15]

        # Desktop sizing and layout are unchanged (G-1, the final owner
        # ruling: mirroring is phones-only) — re-open at 1440 and confirm
        # the SAME board draws unmirrored, corner and row clue first.
        page.set_viewport_size(DESKTOP)
        _open(page, live, puzzle_id)
        desktop = _structure(page)

        assert desktop["isMirrored"] is False
        assert _is_corner(desktop["headFirst"]) is True
        for first, last in zip(desktop["rowFirst"], desktop["rowLast"]):
            assert _is_row_clue(first), first
            assert _is_cell(last), last
        assert desktop["rowClueTexts"] == [[str(n) for n in clue] for clue in ROW_CLUES_25x15]

    def test_fifteen_wide_never_mirrors_and_sixteen_wide_mirrors_at_phone(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(PHONE)

        _open(page, live, live.store(GRID_15_WIDE))
        fifteen = _structure(page)
        assert fifteen["isMirrored"] is False
        assert _is_row_clue(fifteen["rowFirst"][0])
        assert _is_cell(fifteen["rowLast"][0])

        _open(page, live, live.store(GRID_16_WIDE))
        sixteen = _structure(page)
        assert sixteen["isMirrored"] is True
        assert _is_cell(sixteen["rowFirst"][0])
        assert _is_row_clue(sixteen["rowLast"][0])


# ==========================================================================
# AC-7 — the mirrored heavy lines are the mirror image of the left layout's
# ==========================================================================

_BORDERS = """() => {
  const px = (el, side) => parseFloat(getComputedStyle(el)[`border${side}Width`]);
  const rowClue = document.querySelector('th.player-clue.is-row');
  const corner = document.querySelector('.player-corner');
  const rows = [...document.querySelectorAll('.player-board tbody tr')];
  const grid = rows.map((tr) => [...tr.querySelectorAll('td.player-cell')]);
  const width = grid[0].length;
  const colRight = [];
  for (let c = 0; c < width; c++) colRight.push(px(grid[0][c], 'Right'));
  return {
    rowClueLeft: px(rowClue, 'Left'), rowClueRight: px(rowClue, 'Right'),
    cornerLeft: px(corner, 'Left'), cornerRight: px(corner, 'Right'), cornerBottom: px(corner, 'Bottom'),
    colRight,
  };
}"""


@pytest.mark.browser
class TestSolverMirror_HeavyLinesMatchTheLeftLayout:
    """AC-7 — at phone width (where the mirror actually applies), the heavy
    vertical lines are after every fifth column and on the line between the
    last column and the row clues (now on the right); every other vertical
    line is thin. That is exactly the un-mirrored layout's own pattern,
    reflected left-to-right: the heavy/thin weights move sides, none change
    weight. At 1440 px (desktop, G-1) the board is not mirrored at all, so
    its pattern is the plain, un-reflected one — checked here as the
    sanity case the mirrored one is a reflection of."""

    def test_mirrored_at_phone_and_plain_at_desktop(self, browser_page, live) -> None:
        page = browser_page
        puzzle_id = live.store(GRID_25x15)
        width = len(GRID_25x15[0])

        page.set_viewport_size(PHONE)
        _open(page, live, puzzle_id)
        mirrored = page.evaluate(_BORDERS)

        thin = min(mirrored["colRight"])
        heavy = max(mirrored["colRight"])
        assert heavy > thin
        # Every fifth real column stays heavy on its own right border
        # (solver.js's .major-right class is unaffected by the mirror).
        assert [c for c in range(width - 1) if mirrored["colRight"][c] > thin] == [4, 9, 14, 19]
        # The last real column's OWN right border is no longer the heavy
        # frame edge (that responsibility moves to the row-clue box's left
        # border in mirrored mode — see admin.css .player-board.is-mirrored).
        assert mirrored["colRight"][width - 1] == thin
        # The heavy line between the last column and the row clues: on the
        # row-clue box's LEFT (mirrored) rather than its right.
        assert mirrored["rowClueLeft"] == heavy
        assert mirrored["rowClueRight"] == thin
        # The corner's heavy line to the last column clue is on its LEFT
        # now, and it no longer draws a border on its new outer-right edge.
        assert mirrored["cornerLeft"] == heavy
        assert mirrored["cornerRight"] == 0
        assert mirrored["cornerBottom"] == heavy  # unaffected by the mirror (vertical)

        page.set_viewport_size(DESKTOP)
        _open(page, live, puzzle_id)
        plain = page.evaluate(_BORDERS)

        assert plain["colRight"][width - 1] == max(plain["colRight"])  # the un-mirrored frame edge
        assert plain["rowClueRight"] == max(plain["colRight"])  # heavy, on the LEFT-side gutter
        assert plain["rowClueLeft"] == min(plain["colRight"])
        assert plain["cornerRight"] == max(plain["colRight"])
        assert plain["cornerLeft"] == 0


# ==========================================================================
# AC-8 — marking a mirrored board's rightmost column
# ==========================================================================


@pytest.mark.browser
class TestSolverMirror_MarkingWorksOnAMirroredBoard:
    """AC-8 — marking, clue circles, hints, progress and the solved state
    find their elements by class/data-attribute, never by DOM position, so
    they keep working on a mirrored board exactly as on an un-mirrored one."""

    def test_tapping_the_rightmost_column_fills_only_that_cell(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(PHONE)
        _open(page, live, live.store(GRID_25x15))
        assert page.evaluate("document.querySelector('.player-board').classList.contains('is-mirrored')")

        _button(page, "Black").click()
        width = len(GRID_25x15[0])
        row, col = 6, width - 1
        page.mouse.click(*_centre(page, row, col))

        states = page.evaluate(
            "() => [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state)"
        )
        changed = {(i // width, i % width): s for i, s in enumerate(states) if s != U}
        assert changed == {(row, col): F}


# ==========================================================================
# The matchMedia redraw: crossing 820 px preserves marks, undo/redo and the
# save (not a lettered AC — "What to implement" item 2's own requirement)
# ==========================================================================


@pytest.mark.browser
class TestSolverMirror_CrossingTheBreakpointKeepsTheBoard:
    """Crossing 820 px toggles the mirror (via the matchMedia listener
    start() registers) without losing anything solver_state.js tracks:
    the recorded board (marks), the undo/redo history or the localStorage
    save. A live-region announcement or a stray network request would also
    signal a full reload, so both are watched too."""

    def test_marks_undo_redo_and_the_save_survive_the_breakpoint(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(DESKTOP)
        puzzle_id = live.store(GRID_25x15)
        _open(page, live, puzzle_id)
        assert not page.evaluate("document.querySelector('.player-board').classList.contains('is-mirrored')")

        _button(page, "Black").click()
        page.mouse.click(*_centre(page, 0, 0))  # one recorded stroke, one undo step
        before = page.evaluate("[...window.puzzlePlayer.getBoard().cells]")
        saved_before = page.evaluate(
            "async () => { const S = await import('/static/solver_state.js'); "
            "return window.localStorage.getItem(S.saveKey(window.puzzlePlayer.payload.id)); }"
        )

        requests = []
        page.on("request", lambda request: requests.append(request.url))
        page.set_viewport_size(PHONE)  # crosses 820 px: matchMedia fires "change"
        page.wait_for_function("document.querySelector('.player-board').classList.contains('is-mirrored')")

        after_mirror = page.evaluate("[...window.puzzlePlayer.getBoard().cells]")
        assert after_mirror == before
        assert requests == []  # a redraw, not a reload or a request (ADR-0038/R2)

        # Undo still works on the redrawn (mirrored) board, from the SAME
        # history — the stroke recorded before the crossing is still there.
        page.keyboard.press("Control+z")
        undone = page.evaluate("[...window.puzzlePlayer.getBoard().cells]")
        assert undone != after_mirror
        assert all(c == U for c in undone)

        page.keyboard.press("Control+Shift+z")
        redone = page.evaluate("[...window.puzzlePlayer.getBoard().cells]")
        assert redone == before

        # The save survives the crossing too (it is keyed by puzzle id, not
        # by layout, and nothing here clears or rewrites it except a mark).
        saved_after = page.evaluate(
            "async () => { const S = await import('/static/solver_state.js'); "
            "return window.localStorage.getItem(S.saveKey(window.puzzlePlayer.payload.id)); }"
        )
        assert saved_after == saved_before

        # Crossing back to desktop keeps the (redone) board and un-mirrors.
        page.set_viewport_size(DESKTOP)
        page.wait_for_function("!document.querySelector('.player-board').classList.contains('is-mirrored')")
        back = page.evaluate("[...window.puzzlePlayer.getBoard().cells]")
        assert back == before
