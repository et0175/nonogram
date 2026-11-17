"""CARD-439 — the line focus view: a big board on a phone solved one row or
column at a time, in big cells (owner request and ruling, 2026-11-12).

The view is a dialog over the player (``#puzzle-player-line``) that draws ONE
line of the board, split into at most two strips, with a mini board to choose
the line by. It holds no state of its own: every mark made in it is a stroke
recorded into the player's own history, so these tests read the result off the
BOARD (``td.player-cell`` and ``window.puzzlePlayer.getBoard()``) and the save,
never only off the view.

Browser tests only (pytest-playwright + Chromium, ADR-0038/R7), through
CARD-160's fixtures. Touch input is real: CDP ``Input.dispatchTouchEvent``.
A synthetic drag is sent as small steps with a pause at the end, as a finger
moves: Chromium reads an instantaneous swipe as a fling, and the tap after a
fling is spent stopping it — true of the board's own Region drag too, and not
something this view does.
"""

from __future__ import annotations

import io
import re

import pytest
from PIL import Image

from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)
from tests.test_player_public_mode import public_payload, serve  # noqa: F401 — serve is a fixture

U, F, E, M = "unknown", "filled", "empty", "maybe"

#: The three boards: a 30 x 30 (two strips of 15 both ways), a 25 wide x 20
#: high (rows 15 + 10, columns 10 + 10) and a 15 x 15 (no view offered).
BIG = _unique_grid(30, 30, seed=439)
WIDE = _unique_grid(25, 20, seed=4391)
SMALL = _unique_grid(15, 15, seed=4392)

PHONE = {"width": 390, "height": 844}
LANDSCAPE = {"width": 844, "height": 390}
DESKTOP = {"width": 1440, "height": 900}

#: solver.js's LONG_PRESS_MS, with room to spare.
LONG_PRESS_S = 0.6

#: CARD-445 AC-3 — ``.player-line-strips``' own border box (width x height),
#: MEASURED on ``main`` at each viewport with ``BIG`` open in the view, before
#: this card put an ask control in the view's tool row. Keyed on the
#: viewport's width. The figure is a measurement and not a prediction: the
#: brief's own numbers were taken on production's 30 x 25 puzzle, where the
#: landscape strip is 559 px wide and not 598 — the mini board beside it is a
#: different shape, so the column it leaves is a different width.
MAIN_STRIPS = {390: (358.0, 132.0), 844: (598.0, 132.0)}


def _context(browser, viewport):
    return browser.new_context(has_touch=True, viewport=viewport)


def _open_phone(browser, live, grid, viewport=PHONE):
    context = _context(browser, viewport)
    page = context.new_page()
    _open(page, live, live.store(grid), keep_opening_zoom=True)
    return context, page


def _line_button(page):
    return page.locator("[data-player-line-open]")


def _dialog(page):
    return page.locator("#puzzle-player-line")


def _open_line(page):
    _line_button(page).tap()
    page.wait_for_function("!document.getElementById('puzzle-player-line').hidden")


def _title(page) -> str:
    return page.locator("[data-player-line-title]").text_content()


def _strip_states(page) -> list[str]:
    return page.eval_on_selector_all(".player-line-cell", "els => els.map((e) => e.dataset.state)")


def _board_line(page, axis, index) -> list[str]:
    return page.evaluate(
        """([axis, index]) => {
          const b = window.puzzlePlayer.getBoard();
          const n = axis === 'row' ? b.width : b.height;
          return Array.from({length: n}, (_, k) => axis === 'row'
            ? b.cells[index * b.width + k] : b.cells[k * b.width + index]);
        }""",
        [axis, index],
    )


def _centre(page, selector):
    box = page.locator(selector).bounding_box()
    return {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}


def _strips_box(page) -> tuple[float, float]:
    """``.player-line-strips``' border box, (width, height), to 1/100 px.

    Its control, recorded here and not only in a review (ADR-0039/R4): the
    assertions below are ``>=`` against ``MAIN_STRIPS``, so what has to be
    shown is that the box can FALL when something beside or above the strips
    takes room from them. It can, and in the direction the ``>=`` guards —
    widening the landscape block's ``column-gap`` from ``--space-5`` to
    200 px gives the map column 180 px more and the box reads ``(418, 132)``
    against the ``(598.0, 132.0)`` asked for, which reds AC-3's cell at
    844 x 390. The height is content-fixed (two 48 px strips, a 2 px rule
    each side, one ``--space-3 + 1rem`` gap = 132), so a fall shows in the
    width; the companion ``_tool_rows`` is what catches a wrap, which is the
    other way the strips lose room.
    """
    return tuple(page.eval_on_selector(
        ".player-line-strips",
        "e => { const r = e.getBoundingClientRect();"
        " return [Math.round(r.width * 100) / 100, Math.round(r.height * 100) / 100]; }"))


def _tool_rows(page) -> list[float]:
    """The distinct ``y`` of the view's drawn tool buttons, ascending.

    One distinct ``y`` is one row — ``tests/test_puzzle_solver_phone.py``'s own
    idiom for the board's toolbar, and the measurement CARD-445 AC-3 actually
    needs: a control that WRAPS the tool block onto another row is what would
    take room from the strips, and a free-space sum does not predict a wrap.
    ``getClientRects()`` and not ``offsetParent``: the view is
    ``position: fixed``, whose ``offsetParent`` is null however visible it is.
    """
    return sorted(set(page.eval_on_selector_all(
        ".player-line-tools button",
        "els => els.filter((b) => b.getClientRects().length > 0)"
        "  .map((b) => Math.round(b.getBoundingClientRect().y * 100) / 100)")))


def _jump_targets(page) -> list[str]:
    """CARD-445: the ask's other broken lines, as the view offers them."""
    return page.eval_on_selector_all("[data-player-line-jump]",
                                     "els => els.map((b) => b.textContent.trim())")


def _answer_and_tip(page) -> tuple[float, float]:
    """The BOTTOM of the ask's targets box and the TOP of the view's tip.

    CARD-445: the owner's ruling of 2026-11-16 put the lines the ask found
    broken where "it reads as the answer and not as a footnote to it" — above
    the tip — while the markup has them LAST, so that an empty answer is
    ``display: none`` and costs the strips nothing (AC-3). ``admin.css``'s
    ``order`` on ``.player-line-tip`` is what puts them back, in the portrait
    flex column and in the landscape grid alike. Two border-box edges and not
    a frozen ``y``: the arrangement is the claim, the pixel is not.
    """
    answer = page.locator("[data-player-line-broken]").bounding_box()
    tip = page.locator("[data-player-line-tip]").bounding_box()
    return answer["y"] + answer["height"], tip["y"]


def _view_scroll(page) -> tuple[float, float]:
    """The view's own (``scrollHeight``, ``clientHeight``).

    ``admin.css``'s ``.player-line`` rule is ``overflow-y: auto``, so this is
    the instrument behind its landscape block's "13 px of scroll": what the
    answered state costs in landscape is overflow inside the view, not room
    out of the strips. Falls to a zero difference whenever the content fits,
    which is what it reads in portrait.
    """
    return tuple(page.evaluate(
        "() => { const e = document.getElementById('puzzle-player-line');"
        " return [e.scrollHeight, e.clientHeight]; }"))


def _explain_pixel(page) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The pixel the answer line actually PAINTS, and the colour it asks for.

    CARD-445: ``#puzzle-player-explain`` is a ``position: fixed`` box and so is
    the view (``z-index: 1050``), so borrowing the board's answer line over an
    open view needs the stacking to work out — ``admin.css``'s
    ``.is-line-open .player-explain { z-index: 1060 }``. A hit test cannot
    measure it (the box is ``pointer-events: none``, so
    ``elementFromPoint`` returns whatever is beneath it whichever one paints on
    top), so this reads one screenshot pixel inside the box's padding and
    compares it with the box's own computed background colour.

    Its controls, recorded here because a control run once in a review is a
    control the next reader cannot find (ADR-0039/R4). Both run against the
    committed bytes, each reverted immediately:
      * POSITIVE — ``.is-line-open .player-explain``'s ``z-index: 1060`` ->
        ``1040``, i.e. BELOW the view's own 1050: the probe reads
        ``(245, 240, 230)``, the view's paper, against the box's own
        ``(230, 239, 236)``, and the assertion reds.
      * NEGATIVE — the same declaration ``1060`` -> ``1051``, one above the
        view instead of ten: stays green. So the instrument discriminates
        "above the view" from "far above it", and will not red on a
        near-miss stacking change that still paints correctly.
    Comparing the painted pixel with the box's OWN computed
    ``backgroundColor`` is what makes it survive a colour-token, theme or
    dark-mode change: both sides move together. Its one drift anchor is the
    literal ``8`` in the clip's ``x`` — it is 6 px clear of anything but
    background only because ``--space-4: 1rem`` (tokens.css) plus a 2 px
    border leaves it so, which a padding-token change could undo.
    """
    box = page.locator("#puzzle-player-explain").bounding_box()
    shot = page.screenshot(clip={"x": box["x"] + 8, "y": box["y"] + box["height"] / 2,
                                 "width": 1, "height": 1})
    painted = Image.open(io.BytesIO(shot)).convert("RGB").getpixel((0, 0))
    asked = page.eval_on_selector("#puzzle-player-explain",
                                  "e => getComputedStyle(e).backgroundColor")
    return painted, tuple(int(v) for v in re.findall(r"\d+", asked)[:3])


def _cell(k: int) -> str:
    return f'.player-line-cell[data-index="{k}"]'


def _touch(cdp, kind, points=()):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": list(points)})


def _strip_drag(context, page, first: int, last: int) -> None:
    cdp = context.new_cdp_session(page)
    a, z = _centre(page, _cell(first)), _centre(page, _cell(last))
    _touch(cdp, "touchStart", [a])
    for step in range(1, 13):
        _touch(cdp, "touchMove", [{"x": a["x"] + (z["x"] - a["x"]) * step / 12,
                                   "y": a["y"] + (z["y"] - a["y"]) * step / 12}])
        page.wait_for_timeout(30)
    page.wait_for_timeout(150)
    _touch(cdp, "touchEnd")


def _long_press(context, page, k: int) -> None:
    cdp = context.new_cdp_session(page)
    _touch(cdp, "touchStart", [_centre(page, _cell(k))])
    page.wait_for_timeout(LONG_PRESS_S * 1000)
    _touch(cdp, "touchEnd")


def _saved_strokes(page) -> int:
    return page.evaluate(
        """() => {
          const key = Object.keys(localStorage).find((k) => k.startsWith('nonogram-player:'));
          return key ? JSON.parse(localStorage.getItem(key)).done.length : 0;
        }""")


@pytest.mark.browser
class TestSolverLine_ThePureHelpers:
    """lineStrips, crossingLine and lineOf, from the page's own module."""

    def test_the_split_and_the_pivot(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(SMALL))
        result = browser_page.evaluate(
            """async () => {
              const m = await import('/static/solver_state.js');
              const board = m.withCell(m.createBoard(3, 2), 1, 2, m.FILLED);
              let refused = 0;
              for (const bad of [0, 1.5, -3]) { try { m.lineStrips(bad); } catch { refused += 1; } }
              return {
                strips: [10, 15, 16, 20, 22, 25, 30].map((n) => [...m.lineStrips(n)]),
                // 2026-11-17 (owner's pass-2 review, item 9): an upright
                // phone asks for strips of ten.
                tall: [10, 22, 25, 30].map((n) => [...m.lineStrips(n, m.LINE_STRIP_TALL)]),
                refused,
                row: [...m.lineOf(board, 'row', 1)],
                column: [...m.lineOf(board, 'column', 2)],
                crossRow: m.crossingLine('row', 13, 17),
                crossColumn: m.crossingLine('column', 17, 13),
                position: [m.linePosition('row', 4, 9), m.linePosition('column', 4, 9)],
              };
            }""")
        assert result["strips"] == [[10], [15], [10, 6], [10, 10], [10, 12], [15, 10], [15, 15]]
        assert result["tall"] == [[10], [10, 10, 2], [10, 10, 5], [10, 10, 10]]
        assert result["refused"] == 3
        assert result["row"] == [U, U, F] and result["column"] == [U, F]
        assert result["crossRow"] == {"axis": "column", "index": 17, "at": 13}
        assert result["crossColumn"] == {"axis": "row", "index": 13, "at": 17}
        assert result["position"] == [[4, 9], [9, 4]]


@pytest.mark.browser
class TestSolverLine_IsOfferedOnlyForABigBoardOnAPhone:
    """AC-1 — and, since CARD-445, AC-3's geometry: what the view's own ask
    control costs the strips at each of the two viewports the card names.

    The RESTING and PROBING states only: the ANSWERED one needs a probe that
    has actually broken two lines, so it is measured where that probe already
    exists, at both viewports, in
    ``TestSolverLine_ProbesInTheView::test_a_wrong_guess_in_the_view_undoes_it_and_offers_the_other_colour``.
    """

    @pytest.mark.parametrize("viewport", [PHONE, LANDSCAPE], ids=["390x844", "844x390"])
    def test_a_big_board_on_a_phone_offers_it(self, browser, live, viewport) -> None:
        context, page = _open_phone(browser, live, BIG, viewport)
        try:
            assert _line_button(page).is_visible()
            # CARD-445 AC-3: "the strips keep their room". The ask control is
            # drawn only while a probe is open (it answers about a probe and
            # has nothing to say outside one), so the state to measure is the
            # PROBING one: there the view's Probe button is replaced by Keep
            # and Wrong guess and joined by the ask, which is the tool block's
            # widest state and the one that could wrap.
            _open_line(page)
            before, rows = _strips_box(page), _tool_rows(page)
            # "No smaller" in BOTH dimensions, element-wise and not as a tuple
            # comparison: tuples compare lexicographically, so a box one pixel
            # wider and a hundred shorter would pass `>=` on the pair.
            was = MAIN_STRIPS[viewport["width"]]
            assert all(a >= b for a, b in zip(before, was, strict=True)), (before, was)
            page.locator('[data-player-line-probe="open"]').tap()
            assert page.locator("[data-player-line-ask]").is_visible()
            assert _strips_box(page) == before, (before, _strips_box(page))
            assert _tool_rows(page) == rows, (rows, _tool_rows(page))
        finally:
            context.close()

    @pytest.mark.parametrize(("grid", "viewport"), [(BIG, DESKTOP), (SMALL, PHONE)],
                             ids=["30x30-desktop", "15x15-phone"])
    def test_elsewhere_it_is_not_drawn(self, browser, live, grid, viewport) -> None:
        context, page = _open_phone(browser, live, grid, viewport)
        try:
            assert not _line_button(page).is_visible()
            assert _dialog(page).is_hidden()
            if grid is SMALL:
                # Never offered, so never built: the page is the one it was.
                assert _dialog(page).count() == 0 and _line_button(page).count() == 0
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_OpensAtTheLastCellTouched:
    """AC-2 — and before any touch, row 1; Escape and Board both close it."""

    def test_row_one_then_the_touched_row(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            assert _title(page) == "Row 1 of 30"
            assert page.evaluate("document.activeElement.dataset.playerLineAction") == "close"
            page.keyboard.press("Escape")
            assert _dialog(page).is_hidden()

            page.locator(".player-board tbody tr").nth(13).locator("td.player-cell").nth(10).tap()
            _open_line(page)
            assert _title(page) == "Row 14 of 30"
            assert len(_strip_states(page)) == 30
            page.locator('[data-player-line-action="close"]').tap()
            assert _dialog(page).is_hidden()
            assert page.evaluate("document.activeElement.hasAttribute('data-player-line-open')")
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_MarksAreTheBoardsMarks:
    """AC-3."""

    def test_tap_repeat_tap_drag_and_undo(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            page.locator(_cell(3)).tap()                      # black
            assert _board_line(page, "row", 0)[3] == F
            page.locator(_cell(3)).tap()                      # repeat: white
            assert _board_line(page, "row", 0)[3] == E
            page.locator('[data-player-line-tool="maybe"]').tap()
            assert page.locator("#puzzle-player-tool-trigger").get_attribute("aria-label") == "Brush: Maybe"
            _strip_drag(context, page, 20, 24)                # across nothing but strip 2
            row = _board_line(page, "row", 0)
            assert row[20:25] == [M] * 5 and row[19] == U and row[25] == U
            assert _strip_states(page) == row
            assert _saved_strokes(page) == 3
            cells = page.locator(".player-board tbody tr").first.locator("td.player-cell")
            assert cells.nth(22).get_attribute("data-state") == M

            page.locator('[data-player-line-action="undo"]').tap()
            assert _board_line(page, "row", 0)[20:25] == [U] * 5
            assert _saved_strokes(page) == 2
        finally:
            context.close()

    def test_a_drag_crosses_from_one_strip_to_the_other(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            _strip_drag(context, page, 12, 17)
            assert _board_line(page, "row", 0)[12:18] == [F] * 6
            assert _saved_strokes(page) == 1
        finally:
            context.close()

    def test_the_arrows_and_the_mini_board_choose_the_line(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            assert page.locator('[data-player-line-action="prev"]').get_attribute("aria-disabled") == "true"
            page.locator('[data-player-line-action="next"]').tap()
            assert _title(page) == "Row 2 of 30"
            box = page.locator("[data-player-line-mini]").bounding_box()
            # The centre of row 21, column 6 of the map.
            page.touchscreen.tap(box["x"] + box["width"] * 5.5 / 30, box["y"] + box["height"] * 20.5 / 30)
            assert _title(page) == "Row 21 of 30"
            page.locator('[data-player-line-axis="column"]').tap()
            assert _title(page) == "Column 6 of 30"
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_TheLineIsSplitInTwo:
    """AC-4 — split, not scrolled, at a phone's width."""

    @pytest.mark.parametrize(("grid", "axis", "split"), [
        # 2026-11-17 (owner's pass-2 review, item 9): upright, strips of ten
        # (they were 15 + 15 and 15 + 10, 23 px cells over half a free screen).
        (BIG, "row", [10, 10, 10]), (WIDE, "row", [10, 10, 5]), (WIDE, "column", [10, 10]),
    ], ids=["30-row", "25-row", "20-column"])
    def test_the_strips_fit_the_phone(self, browser, live, grid, axis, split) -> None:
        context, page = _open_phone(browser, live, grid)
        try:
            _open_line(page)
            if axis == "column":
                page.locator('[data-player-line-axis="column"]').tap()
            strips = page.eval_on_selector_all(
                ".player-line-strip",
                "els => els.map((s) => ({n: s.children.length, right: s.getBoundingClientRect().right,"
                " cell: s.firstElementChild.getBoundingClientRect().width}))")
            assert [s["n"] for s in strips] == split
            assert all(s["right"] <= PHONE["width"] for s in strips)
            assert min(s["cell"] for s in strips) >= 30  # was 22 with strips of fifteen
            # One cell size for both strips.
            assert max(s["cell"] for s in strips) - min(s["cell"] for s in strips) < 1
            assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
            # CARD-471 (UX review L4): upright, the map is at most a quarter
            # of the screen's height (it was a third), so the strips sit higher.
            mini = page.locator(".player-line-mini").bounding_box()
            assert mini["height"] <= 0.25 * PHONE["height"] + 1, mini
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_ReadsLikeTheBoard:
    """CARD-441 — a settled number is ringed, not struck; two black cells
    either side of the heavy fifth rule stay two cells."""

    def test_ring_and_divider(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            row, k = next((r, k) for r, line in enumerate(BIG) for k in (5, 10, 20, 25)
                          if line[k - 1] and line[k])
            other = next(r for r in range(30) if r != row and any(BIG[r]))
            page.evaluate(
                """async ([grid, other, col]) => {
                  const m = await import('/static/solver_state.js');
                  window.puzzlePlayer.setBoard(m.withCell(m.boardOfGrid(grid), other, col, m.UNKNOWN));
                }""",
                [BIG, other, BIG[other].index(True)],
            )
            free = BIG[row].index(False)
            page.locator(".player-board tbody tr").nth(row).locator("td.player-cell").nth(free).tap()
            page.locator('[data-player-action="undo"]').tap()
            _open_line(page)
            assert _title(page) == f"Row {row + 1} of 30"
            nums = page.eval_on_selector_all(".player-line-num", """els => els.map((e) => {
              const s = getComputedStyle(e);
              return {circled: e.classList.contains('is-circled'), line: s.textDecorationLine,
                      ring: s.borderTopColor, radius: parseFloat(s.borderTopLeftRadius), h: e.offsetHeight};
            })""")
            ink = page.evaluate("getComputedStyle(document.querySelector('.player-line-cell[data-state=filled]')).backgroundColor")
            assert nums and all(n["circled"] for n in nums)
            assert all(n["line"] == "none" and n["ring"] == ink and n["radius"] >= n["h"] / 2 for n in nums)
            cell = page.eval_on_selector(_cell(k), """e => ({major: e.classList.contains('is-major'),
              state: e.dataset.state, bg: getComputedStyle(e).backgroundColor, shadow: getComputedStyle(e).boxShadow})""")
            assert cell["major"] and cell["state"] == F
            before = page.eval_on_selector(_cell(k - 1), "e => getComputedStyle(e).boxShadow")
            # A paper gap inside each black cell, either side of the ink rule.
            for shadow in (cell["shadow"], before):
                assert shadow != "none" and cell["bg"] not in shadow
        finally:
            context.close()


def _probe_state(page) -> dict:
    return page.evaluate("""() => ({
      buttons: Object.fromEntries([...document.querySelectorAll('[data-player-line-probe]')]
        .map((b) => [b.dataset.playerLineProbe, !b.hidden])),
      strip: [...document.querySelectorAll('.player-line-cell[data-probe]')].map((c) => Number(c.dataset.index)),
      board: [...document.querySelectorAll('.player-board tbody tr:first-child td.player-cell')]
        .flatMap((c, k) => c.hasAttribute('data-probe') ? [k] : []),
      mini: document.querySelectorAll('.player-line-mini-probe').length,
    })""")


def _flags(page) -> dict:
    """CARD-435: the two things the quiet rule governs in THIS view — the
    focused line's clue and the Wrong guess button — read as the board's own
    pair is read (``tests/test_puzzle_solver_probe.py``'s ``_BROKEN``)."""
    return page.evaluate("""() => ({
      clue: document.querySelector('[data-player-line-clue]').classList.contains('is-broken'),
      abandon: document.querySelector('[data-player-line-probe="abandon"]').classList.contains('is-flagged'),
    })""")


def _over_long_run(row) -> int:
    """One more than the row's longest clue number.

    A black run that long cannot be placed whatever the clue says, so marking
    that many consecutive cells breaks the line FOR CERTAIN — which is the
    premise CARD-435's arms below need and the reason they do not guess at a
    wrong mark that may or may not kill a 30-wide row.
    """
    runs = [len(run) for run in "".join("#" if v else "." for v in row).split(".") if run]
    return max(runs) + 1


@pytest.mark.browser
class TestSolverLine_ProbesInTheView:
    """CARD-442 — the probe (CARD-268) inside the line view: a probe already
    open shows when the view opens, and one is started, kept and abandoned
    from it with the probe bar's own transitions.

    CARD-435 (owner ruling 2, 2026-11-14) added the quiet rule to this
    surface: the clue a probe has broken and the Wrong guess button wait for
    Hint here exactly as the board's clue boxes and Contradiction do, because
    one probe cannot answer one way on the board and another in the view. The
    asking itself was the BOARD's Hint, the view shipping no ask of its own
    (buildLineView), so a reader asked by going back to the board — which is
    still what the first cell below drives, unchanged, because that path must
    keep working.

    CARD-445 (owner rulings 2026-11-16) gives the view its own ask, because
    the two CARD-435 rulings together left the flags unreachable from inside:
    once a reader marks anything here the quiet rule hides them and there is
    no control in the view to lift it. The second cell below drives that ask,
    and the three things the owner asked it to answer — the visible line's own
    clue flagged, the OTHER broken rows and columns named in the sentence, and
    those others offered as targets that pivot the view onto them. It also
    carries AC-3 for the ANSWERED state, at BOTH orientations the ruling
    names: that state needs a probe that has broken two lines, which is what
    this cell has already built by then, so the viewport turns under the open
    answered view rather than a second cell being added for it. Its name is
    narrower than its body by exactly that act: the node id is registered in
    ``tests/test_browser_fixture_scope.py``, so renaming it would read as a
    test removed plus a test added rather than as the cell this card changed.
    """

    def test_an_open_probe_shows_and_keep_keeps_it(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            page.locator("#puzzle-player-probe").tap()
            page.locator(".player-board tbody tr").first.locator("td.player-cell").nth(3).tap()
            _open_line(page)
            state = _probe_state(page)
            assert state["buttons"] == {"open": False, "keep": True, "abandon": True}
            assert state["strip"] == [3] and state["board"] == [3] and state["mini"] == 1
            page.locator(_cell(7)).tap()
            state = _probe_state(page)
            assert state["strip"] == [3, 7] and state["board"] == [3, 7] and state["mini"] == 2
            # CARD-435 ruling 2 — the quiet rule on this surface. A black run
            # one longer than the row's longest clue number kills row 1 for
            # certain, and the view says nothing about it until Hint is
            # pressed; that the red arrives on the very same marks is what
            # makes the quiet arm's premise ("there was something to say")
            # measured rather than assumed.
            over = _over_long_run(BIG[0])
            assert over + 8 <= len(BIG[0]), over   # the run clears cells 3 and 7
            for k in range(len(BIG[0]) - over, len(BIG[0])):
                page.locator(_cell(k)).tap()
            assert _flags(page) == {"clue": False, "abandon": False}
            page.locator('[data-player-line-action="close"]').tap()
            page.locator('[data-player-action="hint"]').tap()   # the board's Hint: the ask
            _open_line(page)
            assert _title(page) == f"Row 1 of {len(BIG)}"       # it reopens on the row asked about
            assert _flags(page) == {"clue": True, "abandon": True}
            page.locator('[data-player-line-probe="keep"]').tap()
            assert _flags(page) == {"clue": False, "abandon": False}  # nothing stale
            state = _probe_state(page)
            assert state["buttons"] == {"open": True, "keep": False, "abandon": False}
            assert state["strip"] == [] and state["board"] == []
            assert _board_line(page, "row", 0)[3] == F and _board_line(page, "row", 0)[7] == F
            assert page.locator("#puzzle-player-probe").is_visible()   # the bar closed with it
        finally:
            context.close()

    def test_a_wrong_guess_in_the_view_undoes_it_and_offers_the_other_colour(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            _open_line(page)
            page.locator('[data-player-line-probe="open"]').tap()
            assert page.locator("#puzzle-player-probe").is_hidden()    # the bar opened with it
            page.locator(_cell(20)).tap()
            assert _probe_state(page)["strip"] == [20]

            # ---------- CARD-445: the view can be ASKED (AC-1, AC-4) --------
            # Two broken lines, one on each axis, so the ask has something to
            # flag ON SCREEN and something else to NAME and jump to.
            # Row 1 first: a black run one longer than its longest clue number
            # cannot be placed whatever the clue says. Its first cell IS the
            # probe's single-cell first stroke above, so the Wrong-guess offer
            # at the end of this cell still reads that stroke (probeVerdict
            # looks at the probe's FIRST stroke, not at its only one).
            over = _over_long_run(BIG[0])
            assert len(BIG[0]) - over == 20, over      # the run starts at cell 20
            for k in range(21, len(BIG[0])):
                page.locator(_cell(k)).tap()
            # Then a column, through the view's own pivot: Cols switches axis
            # through the cell last touched (cell 29 -> column 30), one step
            # back is column 29, whose longest clue number is three.
            page.locator('[data-player-line-axis="column"]').tap()
            page.locator('[data-player-line-action="prev"]').tap()
            assert _title(page) == "Column 29 of 30"
            column = [BIG[r][28] for r in range(len(BIG))]
            kill = _over_long_run(column)
            assert kill == 4, kill
            for k in range(10, 10 + kill):
                page.locator(_cell(k)).tap()

            # AC-2's property, on this surface and at this moment too: a
            # recorded change un-asks the question, so everything marked above
            # is silent until the ask.
            assert _flags(page) == {"clue": False, "abandon": False}
            assert _jump_targets(page) == []
            resting, rows = _strips_box(page), _tool_rows(page)
            page.locator("[data-player-line-ask]").tap()
            # 1. the visible line's own clue numbers, flagged.
            assert _flags(page) == {"clue": True, "abandon": True}
            # 2. the sentence — the BOARD's, written to the board's own answer
            #    line and its live region by the one shared handler (AC-4), so
            #    it names every broken line and not only the visible one.
            said = page.locator("#puzzle-player-explain").text_content()
            assert said.startswith("Hint: this guess breaks "), said
            named = set(re.findall(r"(?:row|column) \d+", said))
            assert {"row 1", "column 29"} <= named, said
            assert page.locator("#puzzle-player-announce").text_content() == said
            # and it PAINTS over the view, which is what borrowing it needs.
            painted, asked = _explain_pixel(page)
            assert painted == asked, (painted, asked)
            # 3. the others, as targets that pivot the view onto them.
            titled = {n.capitalize() for n in named}
            assert set(_jump_targets(page)) == titled - {"Column 29"}, said
            # 4. and the shape of the ANSWERED view — the one state in which
            #    the targets box is a layout participant at all, and so the
            #    only state this card adds to the view's geometry (AC-3). The
            #    strips keep the box they had one press ago, the tool block
            #    keeps its rows, and the answer sits ABOVE the tip, where the
            #    owner's ruling put it.
            assert _strips_box(page) == resting, (resting, _strips_box(page))
            assert _tool_rows(page) == rows, (rows, _tool_rows(page))
            answer_low, tip_top = _answer_and_tip(page)
            assert answer_low <= tip_top, (answer_low, tip_top)
            # Portrait has the room for all of it: no scroll at all.
            tall, visible = _view_scroll(page)
            assert tall == visible, (tall, visible)
            page.locator('[data-player-line-jump="row:0"]').tap()
            assert _title(page) == "Row 1 of 30"
            # The pivot's only screen-reader channel: the live region takes
            # the name of the line jumped to, exactly as the long press's
            # pivot announces the crossing line. The sentence itself is not
            # re-said — the answer has not changed, only what is on screen.
            assert page.locator("#puzzle-player-announce").text_content() == "Row 1"
            assert _flags(page) == {"clue": True, "abandon": True}   # still asked
            assert set(_jump_targets(page)) == titled - {"Row 1"}

            # ---- the same answered view in LANDSCAPE (AC-3's other half) ---
            # The owner's ruling and AC-3 name both orientations, and
            # landscape is where the one-row tool block and the view's own
            # scroll live. The viewport TURNS under the open, answered view
            # rather than this becoming a second cell: the owner's test budget
            # (2026-11-07) is "change existing tests, do not add", and a
            # parameter here would cost a node id plus an entry in
            # tests/test_browser_fixture_scope.py's registry for a state this
            # same press has already reached.
            page.set_viewport_size(LANDSCAPE)
            page.wait_for_function(
                "() => matchMedia('(max-height: 500px) and (orientation: landscape)').matches")
            was = MAIN_STRIPS[LANDSCAPE["width"]]
            landscape = _strips_box(page)
            assert all(a >= b for a, b in zip(landscape, was, strict=True)), (landscape, was)
            assert len(_tool_rows(page)) == 1, _tool_rows(page)
            answer_low, tip_top = _answer_and_tip(page)
            assert answer_low <= tip_top, (answer_low, tip_top)
            # admin.css's landscape block: "what the answer costs is 13 px of
            # scroll inside the view, nothing in the strips". Measured as the
            # overflow the view carries, and bounded rather than frozen: the
            # claim is that the cost is a little scroll and not a row of the
            # strips (132 px), so the bound is well under one strip.
            tall, visible = _view_scroll(page)
            assert 0 < tall - visible <= 40, (tall, visible)
            page.set_viewport_size(PHONE)
            page.wait_for_function(
                "() => !matchMedia('(max-height: 500px) and (orientation: landscape)').matches")

            page.locator('[data-player-line-probe="abandon"]').tap()
            assert _board_line(page, "row", 0)[20] == U
            assert _probe_state(page)["strip"] == []
            # The probe is gone, so the ask's answer goes with it.
            # RETIRED CLAIM, 2026-11-17 (owner's pass-2 review, item 9: "There
            # is no Hint in Line view"): the ask itself was hidden outside a
            # probe; it now stays, as the board's own Hint, under that name.
            assert _flags(page) == {"clue": False, "abandon": False}
            assert _jump_targets(page) == []
            assert page.locator("[data-player-line-ask]").get_attribute("aria-label") == "Hint"
            offer = page.locator("#puzzle-player-offer")
            assert offer.is_visible()
            assert "row 1, column 21 must be white" in offer.text_content()
            box = offer.bounding_box()
            assert page.evaluate("([x, y]) => !!document.elementFromPoint(x, y)?.closest('#puzzle-player-offer')",
                                 [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
            assert page.locator(f"{_cell(20)}.is-offered").count() == 1
            page.locator('[data-player-offer="mark"]').tap()
            assert _board_line(page, "row", 0)[20] == E
            assert offer.is_hidden() and _dialog(page).is_visible()
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_ALongPressOpensTheCrossingLine:
    """AC-5."""

    def test_row_to_column_marks_nothing(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            page.locator(".player-board tbody tr").nth(13).locator("td.player-cell").nth(0).tap()
            page.locator('[data-player-action="undo"]').tap()
            _open_line(page)
            assert _title(page) == "Row 14 of 30"
            _long_press(context, page, 17)
            assert _title(page) == "Column 18 of 30"
            pivot = page.eval_on_selector_all(".player-line-cell.is-pivot", "els => els.map((e) => e.dataset.index)")
            assert pivot == ["13"]
            assert all(state == U for state in page.evaluate("window.puzzlePlayer.getBoard().cells"))
            _long_press(context, page, 13)
            assert _title(page) == "Row 14 of 30"
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_SolvingClosesTheView:
    """AC-6 — the solving stroke closes the view, and the button goes."""

    def test_the_last_cell(self, browser, live) -> None:
        context, page = _open_phone(browser, live, BIG)
        try:
            row = next(r for r, line in enumerate(BIG) if any(line))
            col = BIG[row].index(True)
            page.evaluate(
                """async ([grid, row, col]) => {
                  const m = await import('/static/solver_state.js');
                  let board = m.boardOfGrid(grid);
                  board = m.withCell(board, row, col, m.UNKNOWN);
                  window.puzzlePlayer.setBoard(board);
                }""",
                [BIG, row, col],
            )
            # A wrong tap elsewhere on that row, undone: Line then opens there.
            other = BIG[row].index(False)
            page.locator(".player-board tbody tr").nth(row).locator("td.player-cell").nth(other).tap()
            page.locator('[data-player-action="undo"]').tap()
            _open_line(page)
            assert _title(page) == f"Row {row + 1} of 30"
            page.locator('[data-player-line-tool="filled"]').tap()
            page.locator(_cell(col)).tap()
            page.wait_for_function("document.getElementById('puzzle-player-line').hidden")
            assert not _line_button(page).is_visible()
            assert page.locator("#puzzle-player-solved").is_visible()
        finally:
            context.close()


@pytest.mark.browser
class TestSolverLine_ThePublicPlayerOffersItToo:
    """AC-7 — the public site runs this same player in public mode (no
    solution): the view is offered, marks the board and the mark is saved."""

    def test_a_mark_in_the_public_player(self, browser, serve) -> None:
        served = serve(public_payload(BIG))
        context = _context(browser, PHONE)
        page = context.new_page()
        try:
            page.goto(f"{served.url}/index.html")
            page.wait_for_function("window.puzzlePlayer !== undefined")
            _open_line(page)
            page.locator(_cell(29)).tap()
            assert _board_line(page, "row", 0)[29] == F
            assert _saved_strokes(page) == 1
            _long_press(context, page, 29)
            assert _title(page) == "Column 30 of 30"
        finally:
            context.close()
