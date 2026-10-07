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

import random

import pytest

from nonogram.solver import solve
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    MAJOR_EVERY,
    _encode,
    _open,
    _tight_row,
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


def _single_digit_col_grid(width, height, seed, run_cap=9):
    """A uniquely solvable grid every one of whose COLUMN clues is a single
    digit (no run of 10+ consecutive filled cells) — unlike ``GRIDS``/``BIG``
    above, which each happen to carry at least one two-digit column clue (see
    ``TestSolverPhone_BoardFitsThePhoneWidth``'s docstring) and so cannot
    demonstrate AC-1's *unconditional* half.

    Built the same way ``_unique_grid`` builds tight ROWS (CARD-182/CARD-160:
    a run-length encoding with zero slack — the runs plus their minimum
    one-cell gaps already sum to the line's own length — forces that line's
    one and only placement from its clue alone), but transposed to tight
    COLUMNS instead, each re-rolled until its longest run is at most
    ``run_cap``. A tight column's clue alone forces its own content
    regardless of any row, so the grid this produces is uniquely solvable
    from the column clues alone, independent of what the rows turn out to
    be — re-verified directly against the real solver below (not merely
    trusted from the construction), because this is a different
    construction from ``_unique_grid``'s and the solver is the one
    authority ADR-0032/R1 actually asks for.
    """
    rng = random.Random(seed)
    columns = []
    for _ in range(width):
        for _attempt in range(200):
            column = _tight_row(height, rng)
            if max(_encode(column)) <= run_cap:
                columns.append(column)
                break
        else:  # pragma: no cover — not hit by the seeds used below
            raise AssertionError(f"could not build a single-digit column (seed={seed})")
    return [[columns[c][r] for c in range(width)] for r in range(height)]


#: AC-1's unconditional half: a 15 x 15 board whose every column clue is a
#: single digit, so CARD-196's column-numeral floor (7.2 px for one digit)
#: never exceeds the fit-to-width term and the stage genuinely never needs
#: to scroll — the literal claim ``GRIDS`` cannot demonstrate (see above).
#: Measured at 390 x 844: cell 16.359375 px, matching _predict_cell's
#: 16.370667 px within Chromium's own sub-pixel layout rounding (its
#: LayoutUnit is fixed-point at 1/64 px = 0.015625 px; the deeper calc()/
#: clamp()/cqi chain the fit terms go through accumulates a few of those
#: ticks, unlike the column-floor branch's one-step multiply, which is why
#: the cross-check below needs a slightly wider tolerance than the existing
#: floor-bound tests' abs=0.01).
#:
#: 25 x 15 (25 wide, 15 high) is deliberately NOT included here, after a
#: genuine, measured effort across three different constructions (CARD-193
#: redo, 2026-10-07):
#:   1. A tight-COLUMN single-digit grid (this function, seed 19325):
#:      predicted/measured cell ~9.1 px, floor_dominates False (the column
#:      floor is comfortably cleared) — but TR heights measured {13, 14} px
#:      against a uniform 9.109375 px column width: not square.
#:   2. The *shallowest possible* row-clue construction for a 25-wide board
#:      (every row a single run, or empty — row_ch at its absolute floor of
#:      2.95, the minimum any row's clue can need): term1 = (358 - 1 - 2 -
#:      2.95 * 0.6 * 12) / 25 = 13.3504 px. This is width 25's own ceiling
#:      under the current formula — term1's denominator is the board's
#:      width, so no choice of clues raises it further for a 25-wide board.
#:      Measured in the browser: 13.34375 px on most rows, but 14 px (a
#:      whole pixel higher) on rows 5, 10 and 15 — the three rows CARD-193's
#:      MAJOR_EVERY gives a heavier (2 px) bottom border. Column width
#:      stayed uniform (13.34375 px throughout); only row TR height snapped.
#:   3. Re-ran (1) at a second independent seed: the same {13, 14} px split
#:      reproduced.
#: All three show the same mechanism: at any cell size a 25-wide board can
#:  reach (<= 13.3504 px, the mathematical ceiling above), Chromium's table
#:  row-height layout rounds the three heavier-bordered rows up a whole
#:  pixel relative to the rest, so "every cell has the same side" is
#:  literally false — independent of which grid is stored, the column
#:  digit count, or the column floor. This is a width=25 structural
#:  ceiling colliding with a Chromium table-layout rounding behaviour, not
#:  a fixture-choice gap of the kind the 15 x 15 case turned out to be, and
#:  not something fixable by picking yet another grid (the ceiling was
#:  already measured at its best achievable value in construction 2). Per
#:  the same evidence standard as AC-2's 30 x 30 case, 25 x 15 is treated as
#:  unreached for AC-1's UNCONDITIONAL literal claim and is not added to
#:  ``GRIDS_SINGLE_DIGIT_COLS`` (doing so would make
#:  ``TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit``'s
#:  existing 15 x 15 test fail when parametrized over it too, since this
#:  board's cells are not all the same side). AC-1 clause (b)'s mechanism
#:  itself — not the unconditional claim — IS now covered directly: see
#:  ``GRID_25X15_SINGLE_DIGIT_COLS`` and
#:  ``TestSolverPhone_Width25FitCeilingBreaksRowHeightUniformity`` below
#:  (RF-001, CARD-193 redo cycle 1 review), construction 1's own grid and
#:  seed made into an executable, running check instead of only this
#:  comment.
GRIDS_SINGLE_DIGIT_COLS = {
    "15x15": _single_digit_col_grid(15, 15, seed=19315),
}

#: RF-001 fix (CARD-193 redo, cycle 1 review): AC-1 clause (b) claimed the
#: width=25 fit-ceiling / MAJOR_EVERY row-height rounding mechanism as
#: "confirmed" from three manual measurements (see the comment above) but
#: shipped no executable test exercising it. This is that construction
#: (measurement attempt 1's grid, same seed) made real and asserted on,
#: below, by TestSolverPhone_Width25FitCeilingBreaksRowHeightUniformity. It
#: is a SIBLING of GRIDS_SINGLE_DIGIT_COLS, not a member of it: unlike the
#: 15 x 15 case, this board does NOT satisfy AC-1's unconditional half (its
#: cells are not all the same side — that is the whole point), so adding it
#: to GRIDS_SINGLE_DIGIT_COLS would make
#: TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit's
#: existing, unchanged 15 x 15 test fail when parametrized over it too.
GRID_25X15_SINGLE_DIGIT_COLS = _single_digit_col_grid(25, 15, seed=19325)

#: Re-verify each fixture above against the real solver (nonogram.solver),
#: not just trust the tight-column construction's own reasoning — this is a
#: new construction (CARD-193's redo), unlike GRIDS, which reuses
#: _unique_grid's long-proven tight-ROW one (ADR-0032/R1: a stored puzzle
#: must actually be uniquely solvable). Extended (not duplicated) to also
#: cover GRID_25X15_SINGLE_DIGIT_COLS, the RF-001 sibling fixture above.
for _name, _grid in {**GRIDS_SINGLE_DIGIT_COLS, "25x15": GRID_25X15_SINGLE_DIGIT_COLS}.items():
    _rows_clues = tuple(tuple(_encode(row)) for row in _grid)
    _cols_clues = tuple(tuple(_encode(col)) for col in zip(*_grid))
    assert max(len(str(n)) for clue in _cols_clues for n in clue) == 1, _name
    assert solve(_rows_clues, _cols_clues).is_unique, _name
del _name, _grid, _rows_clues, _cols_clues


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
    of them. This is the two-tier behaviour the rewritten AC-1/AC-2/AC-11
    actually describe, not a single blanket claim: a board whose row-clue
    band width plus its columns at the numeral floor fits inside the 358 px
    stage fits with no stage scroll at all (demonstrated for a different,
    single-digit-column fixture by
    ``TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit``
    below); a board that exceeds that named condition — the 30 x 30 with a
    15-number row clue is the one confirmed instance, and the three boards
    here all happen to need the column-numeral floor too — scrolls inside
    ``.player-stage`` instead, while the page itself never scrolls either
    way. Rather than hard-code either coincidence (or silently swap in
    different fixtures and lose the boards these tests were defined
    against — G-1 pins their 1440 px cell sizes, so they are not changed
    here), this test cross-checks the measured cell against an independent
    re-derivation of admin.css's clamp (_predict_cell), which stays correct
    whichever term binds. Whatever the stage does internally, the page
    itself never scrolls sideways (AC-1's unconditional page-level claim).
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
# AC-1's unconditional half — a board whose columns stay single-digit
# genuinely never scrolls its stage, literally, not just "the page doesn't"
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit:
    """AC-1's unconditional half, demonstrated literally rather than only as
    the conditional property above. ``GRIDS``/``BIG`` (CARD-182's original
    fixtures, kept byte-for-byte for G-1) each happen to carry at least one
    two-digit column clue, so all three measure the SAME column-floor-bound
    ~14.39 px and all three scroll inside ``.player-stage`` — none of them
    can show AC-1's "fits with no stage scroll at all" half, only its
    conditional half (the class above). ``GRIDS_SINGLE_DIGIT_COLS`` is built
    so every column clue is a single digit instead: CARD-196's
    column-numeral floor (7.2 px for one digit) then never exceeds the
    fit-to-width term, so the clamp is fit-bound, not floor-bound, and the
    stage's ``scrollWidth`` comes out at or below its ``clientWidth`` —
    genuinely no stage scroll, not merely an unscrolled page. This is the
    board choice the AC's own "named condition" (row-clue band width +
    columns at the numeral floor <= the 358 px stage) predicts will fit;
    confirmed here by direct measurement, not assumed."""

    @pytest.mark.parametrize("name", list(GRIDS_SINGLE_DIGIT_COLS))
    def test_the_stage_does_not_scroll_and_every_cell_shares_one_side(self, browser_page, live, name) -> None:
        grid = GRIDS_SINGLE_DIGIT_COLS[name]
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(grid))

        cells = browser_page.evaluate(_CELLS)
        fit = browser_page.evaluate(_FIT)

        assert len(cells) == len(grid) * len(grid[0])
        sides = {side for cell in cells for side in cell}
        assert len(sides) == 1, sides  # every cell shares one side, literally
        side = sides.pop()
        assert side <= CAP, side

        predicted, floor_dominates = _predict_cell(grid, fit["stageClientWidth"], 844, cell_min=0)
        assert not floor_dominates, (name, predicted)  # the fit term binds here, not the numeral floor
        # abs=0.02, not the existing floor-bound tests' 0.01: Chromium's
        # LayoutUnit is fixed-point at 1/64 px (0.015625 px), and the
        # fit-to-width term's calc()/clamp()/cqi chain accumulates a few of
        # those ticks across more arithmetic steps than the column floor's
        # one-step multiply does (see GRIDS_SINGLE_DIGIT_COLS's comment).
        assert side == pytest.approx(predicted, abs=0.02), (side, predicted)

        # AC-1's unconditional half, literally: the stage itself never scrolls.
        assert fit["stageScrollWidth"] <= fit["stageClientWidth"], fit
        # And the page, as always, never scrolls either.
        assert fit["pageWidth"] <= fit["viewport"], fit


# ==========================================================================
# AC-1 clause (b) — RF-001 (CARD-193 redo, cycle 1 review): the width=25
# fit-term ceiling / MAJOR_EVERY row-height rounding mechanism, made real
# ==========================================================================


@pytest.mark.browser
class TestSolverPhone_Width25FitCeilingBreaksRowHeightUniformity:
    """AC-1 clause (b), confirmed by direct measurement rather than asserted
    only in a code comment (see ``GRID_25X15_SINGLE_DIGIT_COLS`` above for
    the three manual measurement attempts this test turns into an
    executable check — this is measurement attempt 1's own grid and seed).

    Proves the finding's own distinction: column WIDTH stays uniform (every
    ``td.player-cell`` has the same width, matching ``_predict_cell``'s
    fit-term prediction, and the column-numeral floor is comfortably
    cleared — ``floor_dominates`` is False, so this is NOT column-floor
    dominance), but row/cell HEIGHT is not uniform: every row shares one
    height with every other row EXCEPT the three ``MAJOR_EVERY``-bordered
    rows (5, 10 and 15, 1-indexed), which are exactly one pixel taller.
    This is a distinct table-layout rounding effect, not a repeat of the
    column-floor-bound boards in ``TestSolverPhone_BoardFitsThePhoneWidth``
    above."""

    def test_columns_stay_uniform_but_major_every_rows_are_one_pixel_taller(self, browser_page, live) -> None:
        grid = GRID_25X15_SINGLE_DIGIT_COLS
        width, height = len(grid[0]), len(grid)
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(grid))

        cells = browser_page.evaluate(_CELLS)
        fit = browser_page.evaluate(_FIT)
        assert len(cells) == width * height

        # Column width IS uniform — every cell shares the same width, and it
        # matches the fit-term prediction (the arithmetic ceiling term1
        # folds into, not a column-floor dominance).
        widths = {round(w, 6) for w, _h in cells}
        assert len(widths) == 1, widths
        measured_width = widths.pop()

        predicted, floor_dominates = _predict_cell(grid, fit["stageClientWidth"], 844, cell_min=0)
        assert not floor_dominates, predicted  # the fit term binds, not CARD-196's numeral floor
        assert measured_width == pytest.approx(predicted, abs=0.02), (measured_width, predicted)

        # Row HEIGHT is not uniform. Every cell within one row still shares
        # that row's own height (table rows are internally consistent)...
        rows = [cells[r * width:(r + 1) * width] for r in range(height)]
        row_heights = []
        for r, row in enumerate(rows):
            heights_in_row = {round(h, 6) for _w, h in row}
            assert len(heights_in_row) == 1, (r, heights_in_row)
            row_heights.append(heights_in_row.pop())

        # ...but not every row shares the SAME height as every other row:
        # this is the literal "cell-uniformity itself breaks" claim.
        assert len(set(row_heights)) > 1, row_heights

        # Specifically: the three MAJOR_EVERY rows (5, 10, 15 1-indexed —
        # the heavier-bordered rows) are one pixel taller than every other
        # row, and every other row shares one common height.
        major_rows = {r for r in range(height) if (r + 1) % MAJOR_EVERY == 0}
        plain_rows = set(range(height)) - major_rows
        assert major_rows, "no MAJOR_EVERY row in a 15-row board"
        plain_heights = {row_heights[r] for r in plain_rows}
        major_heights = {row_heights[r] for r in major_rows}
        assert len(plain_heights) == 1, plain_heights
        assert len(major_heights) == 1, major_heights
        plain_height, major_height = plain_heights.pop(), major_heights.pop()
        assert major_height == pytest.approx(plain_height + 1, abs=0.01), (plain_height, major_height)

        # This is not horizontal scrolling (mechanism (a)): the stage still
        # fits the board's width exactly, and the page itself never scrolls.
        assert fit["stageScrollWidth"] <= fit["stageClientWidth"], fit
        assert fit["pageWidth"] <= fit["viewport"], fit


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


