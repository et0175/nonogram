"""CARD-182 / CARD-193 — the puzzle player fits a board to the phone width (FR-044).

CARD-182 raised the player's cell floor (``--player-cell-min``) to 24 px below
the shell's 820 px breakpoint, so a board wider than the stage scrolled inside
``.player-stage``. CARD-193 (owner decision, 2026-10-06) removes that floor
below 820 px (down to 0 px, which never binds on its own): the cell comes from
the fit-to-width/height clamp, or CARD-196's column-numeral floor
(``--player-col-floor``, keeping a column number no narrower than a 12 px
numeral needs) when that is larger — capped at 28 px as before, and the
14 px floor is back above 820 px. The owner's final ruling is explicit that
the numeral floor can still force a sideways scroll ("where a board cannot
fit at 12 px, it scrolls sideways") — that is a deliberate, accepted trade-off
for legibility, not a defect, and several tests below measure it rather than
assume it away. Cells keep ``touch-action: none`` (a touch drag marks); every
clue box (column, row, corner) keeps the default ``auto``, and nothing pans
the board on a swipe any more (AC-10).

Browser tests only (pytest-playwright + Chromium, ADR-0038/R7), refusing loudly
when Chromium is absent (ADR-0038/R8) through CARD-160's fixtures, imported
below. Touch input is real: CDP ``Input.dispatchTouchEvent`` drags and taps.
"""

from __future__ import annotations

import pytest

from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)

U, F, E = "unknown", "filled", "empty"

#: The old (CARD-182) 24 px phone floor — now gone below 820 px — and the
#: unchanged 28 px cap. DESKTOP_FLOOR is the 14 px floor that still applies
#: above 820 px (and that the clamp's lower bound falls back to there).
FLOOR, CAP, DESKTOP_FLOOR = 24, 28, 14

#: admin.css's own constants (CARD-193/CARD-196), reimplemented independently
#: below rather than read from the DOM — see _predict_cell.
RULE, RULE_MAJOR, NUMERAL_MIN, CHROME_H = 1, 2, 12, 228


def _deep_row_clues(width, height, seed):
    """A uniquely solvable grid whose first row has the deepest clue a tight
    row of ``width`` can have: (width + 1) // 2 runs (15 for 30 wide)."""
    grid = _unique_grid(width, height, seed=seed)
    runs = (width + 1) // 2
    row = [True] * (width - 2 * (runs - 1)) + [False, True] * (runs - 1)
    assert len(row) == width and row[0] and row[-1]
    grid[0] = row
    return grid


#: The three boards of AC-1: a 15 x 15, a 25 x 15 (25 wide, 15 high) and a
#: 30 x 30 with a 15-number row clue. Unchanged since CARD-182 (G-1): their
#: 1440 px cell sizes are pinned (DESKTOP_CELL below) and must not move.
GRIDS = {
    "15x15": _unique_grid(15, 15, seed=182),
    "25x15": _unique_grid(25, 15, seed=1825),
    "30x30": _deep_row_clues(30, 30, seed=1830),
}
BIG = GRIDS["30x30"]
BIG_SIDE = 30

#: AC-4: td.player-cell width at 1440 x 900 for each board, measured on main
#: (admin.css unchanged, commit 2e40c96) before this card's rule was added,
#: rounded to 0.001 px (the 30 x 30 measured 16.796875).
DESKTOP_CELL = {"15x15": 28.0, "25x15": 28.0, "30x30": 16.797}


def _predict_cell(grid, stage_width, viewport_height, cell_min):
    """An independent re-derivation of admin.css's ``--player-cell`` clamp
    (CARD-193/CARD-196), from the grid's own clues (re-encoded here, not
    read from solver.js's custom properties) and the *measured* stage width
    and viewport height — not a value assumed from .main's padding, which
    is not this formula's concern. Returns ``(cell, floor_dominates)``:
    ``floor_dominates`` says whether CARD-196's column-numeral floor (not
    the fit) is what set the cell, which is exactly the condition under
    which the owner's ruling allows the stage to need a sideways scroll.
    """
    rows_clues = [_encode(row) for row in grid]
    columns_clues = [_encode(col) for col in zip(*grid)]
    width, height = len(grid[0]), len(grid)
    row_ch = max(sum(len(str(n)) + 1.45 for n in clue) + 0.5 for clue in rows_clues)
    col_depth = max(len(clue) for clue in columns_clues)
    col_digits = max(len(str(n)) for clue in columns_clues for n in clue)
    col_floor = col_digits * 0.6 * NUMERAL_MIN
    lower = max(cell_min, col_floor)
    term1 = (stage_width - RULE - RULE_MAJOR - row_ch * 0.6 * NUMERAL_MIN) / width
    term2 = (stage_width - RULE - RULE_MAJOR) / (width + row_ch * 0.36)
    term3 = (viewport_height - CHROME_H) / (height + col_depth + 1)
    fit = min(term1, term2, term3)
    cell = max(lower, min(fit, CAP))
    return cell, col_floor > fit


_CELLS = """() => [...document.querySelectorAll('td.player-cell')].map((td) => {
  const r = td.getBoundingClientRect();
  return [r.width, r.height];
})"""

_FIT = """() => {
  const stage = document.querySelector('.player-stage');
  return { pageWidth: document.scrollingElement.scrollWidth, viewport: innerWidth,
           stageScrollWidth: stage.scrollWidth, stageClientWidth: stage.clientWidth };
}"""


def _states(page):
    return page.evaluate("() => [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state)")


def _changed(states, width=BIG_SIDE):
    return {(i // width, i % width): s for i, s in enumerate(states) if s != U}


def _cell(page, r, c):
    return page.locator(f'td.player-cell[data-row="{r}"][data-col="{c}"]')


def _stage_scroll_left(page):
    return page.evaluate("document.querySelector('.player-stage').scrollLeft")


def _phone(browser):
    return browser.new_context(has_touch=True, viewport={"width": 390, "height": 844})


def _bring_row_to_middle(page, row):
    """Scroll the page vertically (never the stage) so ``row`` sits mid-screen.
    Instant: Bootstrap's reboot makes the root scroll smooth."""
    page.evaluate(
        """(row) => {
          const top = document.querySelector(`td.player-cell[data-row="${row}"]`).getBoundingClientRect().top;
          window.scrollBy({ top: top - innerHeight / 2, behavior: 'instant' });
        }""",
        row,
    )


def _scroll_cell_into_view(page, r, c):
    """Scrolls .player-stage (never the page) so this cell is reachable,
    whether or not the board needs that scroll — CARD-193: a board whose
    column numerals don't fit at the 12 px floor still scrolls internally
    (AC-9 must work either way), while most boards no longer need to."""
    page.evaluate(
        """([r, c]) => {
          document.querySelector(`td.player-cell[data-row="${r}"][data-col="${c}"]`)
            .scrollIntoView({ inline: 'end', block: 'nearest' });
        }""",
        [r, c],
    )


def _visible_centre(page, r, c):
    """The cell's centre, asserting the whole cell is inside the stage's
    visible box and the viewport (so a touch there lands on it, not beside)."""
    seen = page.evaluate(
        """([r, c]) => {
          const cell = document.querySelector(`td.player-cell[data-row="${r}"][data-col="${c}"]`).getBoundingClientRect();
          const stage = document.querySelector('.player-stage').getBoundingClientRect();
          return { cell: [cell.left, cell.top, cell.right, cell.bottom],
                   stage: [stage.left, stage.top, stage.right, stage.bottom],
                   viewport: [innerWidth, innerHeight] };
        }""",
        [r, c],
    )
    left, top, right, bottom = seen["cell"]
    s_left, _, s_right, _ = seen["stage"]
    vw, vh = seen["viewport"]
    assert s_left <= left and right <= s_right, seen
    assert 0 <= left and right <= vw and 0 <= top and bottom <= vh, seen
    return (left + right) / 2, (top + bottom) / 2


def _touch(cdp, kind, x=None, y=None):
    points = [] if x is None else [{"x": x, "y": y}]
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})


# ==========================================================================
# AC-1 / AC-2 — the cell matches the fit-or-numeral-floor formula at
# 390 x 844, the old 24 px floor is gone, and the page never scrolls
# sideways, whether or not .player-stage must scroll internally
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_BoardFitsThePhoneWidth:
    """AC-1 / AC-2 — below 820 px the cell floor is removed: every cell
    shares one side, at most 28 px (the cap, unchanged) and no longer
    pinned at the old 24 px floor. All three boards here measure the SAME
    ~14.39 px at 390 px, because each has at least one two-digit column
    number and CARD-196's column-numeral floor (14.4 px for two digits)
    exceeds what the fit-to-width/height terms alone would give every one
    of them — so AC-2's "narrower than 14 px" is not a blanket guarantee:
    it holds only for a board whose column clues need no more than a
    single-digit numeral. Rather than hard-code that coincidence (or
    silently swap in different fixtures and lose the boards these tests
    were defined against — G-1 pins their 1440 px cell sizes, so they are
    not changed here), this test cross-checks the measured cell against an
    independent re-derivation of admin.css's clamp (_predict_cell), which
    stays correct whichever term binds. Whatever the stage does internally,
    the page itself never scrolls sideways (AC-1's "the board fits the
    phone").
    """

    @pytest.mark.parametrize("name", list(GRIDS))
    def test_the_cell_matches_the_formula_and_clears_the_old_floor(self, browser_page, live, name) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(GRIDS[name]))

        cells = browser_page.evaluate(_CELLS)
        fit = browser_page.evaluate(_FIT)

        assert len(cells) == len(GRIDS[name]) * len(GRIDS[name][0])
        sides = {side for cell in cells for side in cell}
        assert len(sides) == 1, sides  # every cell shares one side
        side = sides.pop()
        assert side <= CAP, side
        assert side < FLOOR, side  # the old 24 px floor no longer binds

        predicted, _floor_dominates = _predict_cell(GRIDS[name], fit["stageClientWidth"], 844, cell_min=0)
        assert side == pytest.approx(predicted, abs=0.01), (side, predicted)
        assert fit["pageWidth"] <= fit["viewport"], fit  # the page never scrolls sideways

    @pytest.mark.parametrize("name", list(GRIDS))
    def test_the_stage_scrolls_exactly_when_the_column_floor_exceeds_the_fit(self, browser_page, live, name) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(GRIDS[name]))

        fit = browser_page.evaluate(_FIT)
        _predicted, floor_dominates = _predict_cell(GRIDS[name], fit["stageClientWidth"], 844, cell_min=0)

        stage_scrolls = fit["stageScrollWidth"] > fit["stageClientWidth"]
        assert stage_scrolls == floor_dominates, (name, fit, floor_dominates)
        assert fit["pageWidth"] <= fit["viewport"], fit  # never the page, regardless


# ==========================================================================
# AC-3 — at 820 px the board fits its stage with no internal scroll; at
# 821 px the 14 px desktop floor is back
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_FitAppliesOnlyAtOrBelowTheShellBreakpoint:
    """AC-3."""

    def test_820_fits_and_821_keeps_the_desktop_floor(self, browser_page, live) -> None:
        puzzle_id = live.store(BIG)
        sides, fits = {}, {}
        for width in (820, 821):
            browser_page.set_viewport_size({"width": width, "height": 900})
            _open(browser_page, live, puzzle_id)
            cells = browser_page.evaluate(_CELLS)
            sides[width] = (min(s for cell in cells for s in cell), max(s for cell in cells for s in cell))
            fits[width] = browser_page.evaluate(_FIT)

        assert fits[820]["stageScrollWidth"] <= fits[820]["stageClientWidth"], fits[820]
        assert sides[821][0] >= DESKTOP_FLOOR, sides


# ==========================================================================
# AC-4 — desktop sizing is the value measured on main
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_DesktopSizingUnchanged:
    """AC-4."""

    @pytest.mark.parametrize("name", list(GRIDS))
    def test_the_1440_cell_width_is_mains(self, browser_page, live, name) -> None:
        browser_page.set_viewport_size({"width": 1440, "height": 900})
        _open(browser_page, live, live.store(GRIDS[name]))

        widths = {round(w, 3) for w, _ in browser_page.evaluate(_CELLS)}

        assert widths == {DESKTOP_CELL[name]}, widths


# ==========================================================================
# AC-9 — touch marks the cells under the finger on a fitted board
# ==========================================================================

ROW = 12
RIGHT_FIVE = [(ROW, c) for c in range(BIG_SIDE - 5, BIG_SIDE)]


def _fitted_phone_page(browser, live, tool=None):
    """The 30 x 30 at 390 x 844 in a touch context, ``tool`` picked first (a
    click scrolls its button into view), and the page scrolled down to ROW.
    CARD-193: below 820 px the cell floor is removed, so most boards no
    longer scroll inside .player-stage — but this grid's two-digit column
    numbers still bind CARD-196's column floor, so it does. Either way the
    test only needs the target cells reachable, so it brings them into view
    (_scroll_cell_into_view) rather than asserting a scroll position; what
    IS asserted is that the drag itself does not change .player-stage's
    scroll (whatever it is) — touch-action: none keeps the gesture from
    panning the board."""
    context = _phone(browser)
    page = context.new_page()
    _open(page, live, live.store(BIG))
    if tool:
        page.get_by_role("button", name=tool, exact=True).click()
    _scroll_cell_into_view(page, *RIGHT_FIVE[-1])
    left = _stage_scroll_left(page)
    _bring_row_to_middle(page, ROW)
    assert _stage_scroll_left(page) == left
    return context, page, left


@pytest.mark.browser
class TestSolverPhone_TouchDragMarksOnAFittedBoard:
    """AC-9 (renamed from TestSolverPhone_TouchDragMarksOnAScrolledBoard:
    a fitted board no longer guarantees a scrolled stage, so the old
    ``scrollLeft > 0`` precondition is gone — see _fitted_phone_page)."""

    def test_a_touch_drag_marks_exactly_the_five_cells_under_the_finger(self, browser, live) -> None:
        context, page, left = _fitted_phone_page(browser, live, tool="White")
        try:
            (x0, y0), (x1, _) = _visible_centre(page, *RIGHT_FIVE[0]), _visible_centre(page, *RIGHT_FIVE[-1])
            for cell in RIGHT_FIVE[1:-1]:
                _visible_centre(page, *cell)
            cdp = context.new_cdp_session(page)
            _touch(cdp, "touchStart", x0, y0)
            for k in range(1, 9):
                _touch(cdp, "touchMove", x0 + (x1 - x0) * k / 8, y0)
            _touch(cdp, "touchEnd")

            assert _changed(_states(page)) == {cell: E for cell in RIGHT_FIVE}
            assert _stage_scroll_left(page) == left
        finally:
            context.close()

    def test_a_tap_fills_exactly_that_cell(self, browser, live) -> None:
        context, page, left = _fitted_phone_page(browser, live)
        try:
            x, y = _visible_centre(page, ROW, BIG_SIDE - 3)
            cdp = context.new_cdp_session(page)
            _touch(cdp, "touchStart", x, y)
            _touch(cdp, "touchEnd")

            assert _changed(_states(page)) == {(ROW, BIG_SIDE - 3): F}
            assert _stage_scroll_left(page) == left
        finally:
            context.close()


# ==========================================================================
# AC-10 — cells keep touch-action: none, clue boxes keep the default
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_SwipingTheCluesPansTheBoard:
    """AC-10. (CARD-193: nothing pans the board on a phone any more, so the
    old swipe-pans-the-stage test — which also assumed the column-clue band
    was reachable at a fixed scroll position — is gone; this touch-action
    check is what AC-10 actually asks for.)"""

    def test_cells_take_no_touch_action_and_clue_boxes_keep_the_default(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(BIG))

        actions = browser_page.evaluate(
            """() => {
              const of = (sel) => new Set([...document.querySelectorAll(sel)].map((el) => getComputedStyle(el).touchAction));
              return { cells: [...of('td.player-cell')], colClues: [...of('.player-clue.is-col')],
                       rowClues: [...of('.player-clue.is-row')], corner: [...of('.player-corner')] };
            }"""
        )

        assert actions["cells"] == ["none"]
        for kind in ("colClues", "rowClues", "corner"):
            assert actions[kind] == ["auto"], actions
