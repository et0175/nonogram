"""CARD-195 — the puzzle player can zoom the board in and out (FR-044).

A zoom level multiplies the fitted cell size (admin.css --player-zoom on
table.player-board, solver.js drawBoard/wireMarking). It is a view setting
only: it changes no board state, is never recorded, serialized or saved, and
starts at 100% on every page load. 100% to 300%, in 25-point steps on the
toolbar's zoom buttons ("Zoom out" / "Zoom in", #puzzle-player-controls
.player-zoom) and continuously on a two-finger pinch that starts on a board
cell; a pinch starting on a clue box or off the board is left to the
browser's own page pinch. A button zoom keeps the stage's own visible-box
centre on the same board point; a pinch keeps the two fingers' midpoint on
the same board point (solver_state.js anchoredScroll, the "keep the view"
formula). The stage (.player-stage) scrolls in both directions once the
board outgrows it, which it never did vertically before this card.

The pure arithmetic (clamping, a button's next step, a pinch's ratio, the
anchor formula) lives in solver_state.js (ADR-0038/R4) and is exercised
directly below, with plain values, the same way test_puzzle_solver_page.py's
TestSolverStateModule exercises the rest of that module.

Fixtures (real Chromium refusing loudly when absent, ADR-0038/R8; a loopback
Flask panel over a temp SQLite store) are CARD-160's, imported below, same as
every other puzzle-player test file. Pinch input is real: CDP
``Input.dispatchTouchEvent`` with two touch points (precedent:
test_puzzle_solver_brush_menu.py's dual-pointer-free single touch drags, and
test_puzzle_solver_phone.py's touch drags).
"""

from __future__ import annotations

import pytest

from tests.test_puzzle_solver_brush_menu import _touch_drag_row_1_cols_2_to_6
from tests.test_puzzle_solver_marking import (
    GRID,
    F,
    _cell,
    _centre,
    _drag,
    _marked,
    _states,
    _tool,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_phone import BIG

# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _zoom_button(page, direction):
    return page.locator(f'[data-player-zoom-action="{direction}"]')


def _zoom_readout(page):
    return page.locator("[data-player-zoom-readout]").text_content()


def _zoom_percent(page):
    return int(_zoom_readout(page).rstrip("%"))


def _cell_sizes(page):
    return page.evaluate(
        "() => [...document.querySelectorAll('td.player-cell')].map((td) => {"
        "  const r = td.getBoundingClientRect(); return [r.width, r.height]; })"
    )


def _cell_widths(page):
    return [w for w, _h in _cell_sizes(page)]


def _save_entry(page, puzzle_id):
    return page.evaluate("(id) => localStorage.getItem('nonogram-player:' + id)", puzzle_id)


def _board_snapshot(page, puzzle_id):
    """Every piece of solve-state AC-3 claims zoom never touches."""
    return page.evaluate(
        """(id) => ({
          states: [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state),
          errors: document.querySelector('[data-player-errors]').textContent,
          progress: document.querySelector('[data-player-progress]').textContent,
          hints: document.querySelector('[data-player-hints]').textContent,
          undo: document.querySelector('[data-player-action="undo"]').getAttribute('aria-disabled'),
          redo: document.querySelector('[data-player-action="redo"]').getAttribute('aria-disabled'),
          save: localStorage.getItem('nonogram-player:' + id),
        })""",
        puzzle_id,
    )


_STAGE_FIT = """() => {
  const stage = document.querySelector('.player-stage');
  return { stageScrollWidth: stage.scrollWidth, stageClientWidth: stage.clientWidth,
           stageScrollHeight: stage.scrollHeight, stageClientHeight: stage.clientHeight,
           pageWidth: document.scrollingElement.scrollWidth };
}"""

_CENTRE_CELL = """() => {
  const stage = document.querySelector('.player-stage');
  const r = stage.getBoundingClientRect();
  const cell = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)?.closest('td.player-cell');
  return cell ? [Number(cell.dataset.row), Number(cell.dataset.col)] : null;
}"""


def _zoom_to(page, percent):
    """Click the zoom button that moves toward `percent`, the number of
    25-point steps needed from wherever the readout currently is, asserting
    it lands exactly there."""
    assert 100 <= percent <= 300 and percent % 25 == 0
    current = _zoom_percent(page)
    direction = "in" if percent > current else "out"
    for _ in range(abs(percent - current) // 25):
        _zoom_button(page, direction).click(force=True)
    assert _zoom_readout(page) == f"{percent}%"


def _dispatch_touch(cdp, kind, points):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y} for x, y in points]})


def _undo_disabled(page) -> bool:
    return page.locator('[data-player-action="undo"]').get_attribute("aria-disabled") == "true"


# ==========================================================================
# AC-1 / AC-2 — the buttons step by 25 points and clamp at both ends
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_ButtonsStepAndClamp:
    """AC-1 / AC-2."""

    def test_zoom_in_once_reads_125_percent_and_scales_every_cell(self, browser_page, live) -> None:
        """AC-1."""
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19511)))
        before = _cell_widths(browser_page)

        _zoom_button(browser_page, "in").click(force=True)

        assert _zoom_readout(browser_page) == "125%"
        after = _cell_widths(browser_page)
        assert len(before) == len(after) and len(after) == 225
        for b, a in zip(before, after):
            assert a == pytest.approx(b * 1.25, abs=0.5), (b, a)

    def test_zoom_out_at_100_percent_is_a_no_op_and_stays_disabled(self, browser_page, live) -> None:
        """AC-2, the 100% end."""
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19512)))
        before = _cell_widths(browser_page)
        assert _zoom_readout(browser_page) == "100%"
        assert _zoom_button(browser_page, "out").get_attribute("aria-disabled") == "true"

        _zoom_button(browser_page, "out").click(force=True)

        assert _zoom_readout(browser_page) == "100%"
        assert _cell_widths(browser_page) == before

    def test_zoom_in_at_300_percent_is_a_no_op_and_stays_disabled(self, browser_page, live) -> None:
        """AC-2, the 300% end."""
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19513)))
        _zoom_to(browser_page, 300)
        before = _cell_widths(browser_page)
        assert _zoom_button(browser_page, "in").get_attribute("aria-disabled") == "true"

        _zoom_button(browser_page, "in").click(force=True)

        assert _zoom_readout(browser_page) == "300%"
        assert _cell_widths(browser_page) == before

    def test_the_full_25_point_staircase_up_and_down(self, browser_page, live) -> None:
        """Every intermediate step, not just the two endpoints — and the
        buttons' own aria-disabled only at the matching end."""
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19514)))
        up = [_zoom_readout(browser_page)]
        for _ in range(9):
            _zoom_button(browser_page, "in").click(force=True)
            up.append(_zoom_readout(browser_page))
        assert up == [f"{p}%" for p in (100, 125, 150, 175, 200, 225, 250, 275, 300, 300)]

        down = []
        for _ in range(9):
            _zoom_button(browser_page, "out").click(force=True)
            down.append(_zoom_readout(browser_page))
        assert down == [f"{p}%" for p in (275, 250, 225, 200, 175, 150, 125, 100, 100)]

        _zoom_to(browser_page, 150)
        assert _zoom_button(browser_page, "out").get_attribute("aria-disabled") == "false"
        assert _zoom_button(browser_page, "in").get_attribute("aria-disabled") == "false"


# ==========================================================================
# AC-3 — zoom changes no solve state
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_ChangingZoomChangesNoSolveState:
    """AC-3 (G-1)."""

    def test_a_100_to_300_to_100_round_trip_changes_nothing_recorded(self, browser_page, live) -> None:
        puzzle_id = live.store(_unique_grid(15, 15, seed=19515))
        _open(browser_page, live, puzzle_id)
        for row, col in ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)):
            _cell(browser_page, row, col).click()
        assert browser_page.locator('[data-player-action="undo"]').get_attribute("aria-disabled") == "false"
        before = _board_snapshot(browser_page, puzzle_id)

        _zoom_to(browser_page, 300)
        _zoom_to(browser_page, 100)

        after = _board_snapshot(browser_page, puzzle_id)
        assert after == before


# ==========================================================================
# AC-4 — the stage scrolls both ways at 300%, the page never does
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_TheBoardScrollsInsideItsStage:
    """AC-4."""

    def test_300_percent_scrolls_the_stage_both_ways_never_the_page(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(BIG))

        _zoom_to(browser_page, 300)
        fit = browser_page.evaluate(_STAGE_FIT)

        assert fit["stageScrollWidth"] > fit["stageClientWidth"], fit
        assert fit["stageScrollHeight"] > fit["stageClientHeight"], fit
        assert fit["pageWidth"] <= 390, fit
        assert fit["stageClientHeight"] <= 844, fit


# ==========================================================================
# AC-5 — a button zoom keeps the stage's visible centre on the same cell
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_ZoomKeepsTheViewCentre:
    """AC-5."""

    def test_zoom_out_keeps_the_same_cell_near_the_stages_centre(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(BIG))
        _zoom_to(browser_page, 300)
        browser_page.evaluate(
            """() => {
              const stage = document.querySelector('.player-stage');
              stage.scrollLeft = (stage.scrollWidth - stage.clientWidth) / 2;
              stage.scrollTop = (stage.scrollHeight - stage.clientHeight) / 2;
            }"""
        )
        before = browser_page.evaluate(_CENTRE_CELL)
        assert before is not None

        _zoom_button(browser_page, "out").click(force=True)

        after = browser_page.evaluate(_CENTRE_CELL)
        assert after is not None
        assert max(abs(before[0] - after[0]), abs(before[1] - after[1])) <= 1, (before, after)


# ==========================================================================
# AC-6 / AC-7 / AC-8 — pinch: zooms on a cell, cancels a stroke, leaves a
# clue-box pinch to the browser
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_PinchOnTheBoardZooms:
    """AC-6."""

    def test_spreading_100_to_200px_on_a_cell_reads_200_percent_and_marks_nothing(self, browser, live) -> None:
        context = browser.new_context(has_touch=True, viewport={"width": 390, "height": 844})
        page = context.new_page()
        try:
            _open(page, live, live.store(_unique_grid(15, 15, seed=19516)))
            before_states = _states(page)
            cx, cy = _centre(page, 7, 7)

            # One deliberate jump, not many small steps: Chromium coalesces
            # touchmove delivery to its own rendering rate, so a long run of
            # tiny synthetic steps sent back-to-back (no yield in between)
            # has it silently drop most of them — pinchZoom only ever reads
            # the CURRENT distance, so one jump exercises the same formula.
            cdp = context.new_cdp_session(page)
            _dispatch_touch(cdp, "touchStart", [(cx - 50, cy), (cx + 50, cy)])
            _dispatch_touch(cdp, "touchMove", [(cx - 100, cy), (cx + 100, cy)])
            _dispatch_touch(cdp, "touchEnd", [])
            # The browser's own native pinch-zoom (distinct from
            # --player-zoom) commits asynchronously — it is not yet visible
            # in window.visualViewport.scale immediately after touchEnd,
            # only after the browser has had a moment to settle. Waiting
            # here is what makes the assertion below a real regression
            # guard rather than one that reads too early and always
            # passes: this is exactly how a real instance of the native
            # zoom escaped detection during this card's own development —
            # .player-cell's touch-action was still "auto" with Region off,
            # letting the compositor commit to the browser's native
            # pinch-zoom before any of this card's own JS ran; fixed by
            # pan-x pan-y (admin.css, test_puzzle_solver_phone.py).
            page.wait_for_timeout(300)

            assert abs(_zoom_percent(page) - 200) <= 1
            assert _states(page) == before_states
            assert page.evaluate("[window.scrollX, window.scrollY]") == [0, 0]
            assert page.evaluate("window.visualViewport.scale") == 1
        finally:
            context.close()


@pytest.mark.browser
class TestSolverZoom_PinchCancelsTheStrokeInProgress:
    """AC-7."""

    def test_a_second_finger_reverts_the_drag_and_commits_nothing(self, browser, live) -> None:
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _tool(page, "Region")
            before = _states(page)

            cdp = context.new_cdp_session(page)
            x0, y0 = _centre(page, 1, 2)
            _dispatch_touch(cdp, "touchStart", [(x0, y0)])
            last = (x0, y0)
            for col in (3, 4, 5):
                last = _centre(page, 1, col)
                _dispatch_touch(cdp, "touchMove", [last])
            mid = _states(page)
            assert mid != before, "the drag's preview never painted anything"

            second = _centre(page, 10, 10)
            _dispatch_touch(cdp, "touchStart", [last, second])
            reverted = _states(page)
            assert reverted == before, "the preview was not reverted when the second finger landed"

            _dispatch_touch(cdp, "touchEnd", [])

            assert _states(page) == before
            assert _undo_disabled(page), "nothing should have been recorded to undo"
        finally:
            context.close()


@pytest.mark.browser
class TestSolverZoom_PinchOnAClueBoxIsNotTheBoardsZoom:
    """AC-8."""

    def test_a_pinch_starting_on_a_column_clue_box_is_left_to_the_browser(self, browser, live) -> None:
        context = browser.new_context(has_touch=True, viewport={"width": 390, "height": 844})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            clue_box = page.locator("th.player-clue.is-col").first
            box = clue_box.bounding_box()
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

            cdp = context.new_cdp_session(page)
            _dispatch_touch(cdp, "touchStart", [(x, y), (x + 40, y)])
            _dispatch_touch(cdp, "touchMove", [(x - 40, y), (x + 80, y)])
            _dispatch_touch(cdp, "touchEnd", [])

            assert _zoom_readout(page) == "100%"
            assert page.evaluate("(el) => getComputedStyle(el).touchAction", clue_box.element_handle()) != "none"
        finally:
            context.close()


# ==========================================================================
# AC-9 — a one-finger drag marks exactly as before, zoomed or not
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_OneFingerDragIsUnchangedByZoom:
    """AC-9."""

    def test_a_region_touch_drag_at_200_percent_marks_exactly_five_cells(self, browser, live) -> None:
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _tool(page, "Region")
            _zoom_to(page, 200)

            _touch_drag_row_1_cols_2_to_6(context, page)

            assert _marked(_states(page)) == {(1, c): F for c in range(2, 7)}
        finally:
            context.close()

    def test_a_mouse_drag_at_200_percent_still_marks_along_the_dragged_line(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _zoom_to(browser_page, 200)

        _drag(browser_page, [(0, 0), (0, 4)])

        assert _marked(_states(browser_page)) == {(0, c): F for c in range(5)}


# ==========================================================================
# AC-10 — 100% is exactly the fitted size (G-2)
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_HundredPercentIsTheFittedSize:
    """AC-10 (G-2)."""

    def test_28px_at_100_percent_then_56px_at_200_percent(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 1440, "height": 900})
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19517)))

        widths_100 = {round(w, 3) for w in _cell_widths(browser_page)}
        assert widths_100 == {28.0}, widths_100

        _zoom_to(browser_page, 200)

        widths_200 = {round(w, 3) for w in _cell_widths(browser_page)}
        assert widths_200 == {56.0}, widths_200


# ==========================================================================
# AC-11 — tap targets: the zoom buttons, and cells at 300%
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_TapTargetsAreAtLeast24px:
    """AC-11."""

    def test_zoom_buttons_and_300_percent_cells_are_at_least_24px(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19518)))

        for direction in ("out", "in"):
            box = _zoom_button(browser_page, direction).bounding_box()
            assert box["width"] >= 24 and box["height"] >= 24, (direction, box)

        _zoom_to(browser_page, 300)

        for width, height in _cell_sizes(browser_page):
            assert width >= 24 and height >= 24, (width, height)


# ==========================================================================
# AC-12 — zoom is not saved and sends nothing
# ==========================================================================


@pytest.mark.browser
class TestSolverZoom_IsNotSavedAndSendsNothing:
    """AC-12 (G-5)."""

    def test_zoom_sends_no_request_leaves_the_save_untouched_and_resets_on_reload(
        self, browser_page, live
    ) -> None:
        puzzle_id = live.store(_unique_grid(15, 15, seed=19519))
        _open(browser_page, live, puzzle_id)
        _cell(browser_page, 0, 0).click()  # one stroke, so there is a save entry to compare
        before_save = _save_entry(browser_page, puzzle_id)
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.context.on("request", lambda request: requests.append(request.url))

        _zoom_to(browser_page, 150)

        # The zoom change itself sends nothing — checked before the reload
        # below, which is an ordinary navigation and naturally requests the
        # page and its assets; that is not what this AC's "sends nothing"
        # claims.
        assert requests == []
        assert _save_entry(browser_page, puzzle_id) == before_save

        browser_page.reload()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert _zoom_readout(browser_page) == "100%"


# ==========================================================================
# The pure arithmetic (ADR-0038/R4) — plain values, no DOM
# ==========================================================================


@pytest.mark.browser
class TestZoomArithmetic_PureFunctions:
    """solver_state.js's zoom exports, exercised directly — the same module
    solver.js calls, with no page state involved."""

    def test_clamp_and_step_cover_the_range_its_edges_and_a_non_multiple(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19520)))

        result = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const attempt = (f) => { try { return { value: f() }; } catch (e) { return { error: e.name }; } };
              return {
                clampLow: S.clampZoom(50), clampHigh: S.clampZoom(400), clampInside: S.clampZoom(180),
                stepInFromExact: S.stepZoom(100, 'in'),
                stepOutFromExact: S.stepZoom(300, 'out'),
                stepInAtMax: S.stepZoom(300, 'in'),
                stepOutAtMin: S.stepZoom(100, 'out'),
                stepInFromMid: S.stepZoom(137.5, 'in'),
                stepOutFromMid: S.stepZoom(137.5, 'out'),
                badDirection: attempt(() => S.stepZoom(150, 'sideways')),
                range: [S.ZOOM_MIN, S.ZOOM_MAX, S.ZOOM_STEP],
              };
            }"""
        )

        assert (result["clampLow"], result["clampHigh"], result["clampInside"]) == (100, 300, 180)
        assert (result["stepInFromExact"], result["stepOutFromExact"]) == (125, 275)
        assert (result["stepInAtMax"], result["stepOutAtMin"]) == (300, 100)
        assert (result["stepInFromMid"], result["stepOutFromMid"]) == (150, 125)
        assert result["badDirection"] == {"error": "RangeError"}
        assert result["range"] == [100, 300, 25]

    def test_pinch_zoom_scales_clamps_and_refuses_a_non_positive_distance(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19521)))

        result = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const attempt = (f) => { try { return { value: f() }; } catch (e) { return { error: e.name }; } };
              return {
                doubled: S.pinchZoom(100, 100, 200),
                halved: S.pinchZoom(200, 100, 50),
                clampedHigh: S.pinchZoom(200, 100, 1000),
                clampedLow: S.pinchZoom(200, 1000, 10),
                zeroDistance: attempt(() => S.pinchZoom(100, 0, 50)),
                negativeDistance: attempt(() => S.pinchZoom(100, -5, 50)),
              };
            }"""
        )

        assert (result["doubled"], result["halved"]) == (200, 100)
        assert (result["clampedHigh"], result["clampedLow"]) == (300, 100)
        assert result["zeroDistance"] == {"error": "RangeError"}
        assert result["negativeDistance"] == {"error": "RangeError"}

    def test_anchored_scroll_matches_the_cards_own_formula_by_hand(self, browser_page, live) -> None:
        """scroll' = (scroll + a) x (new / old) - a (target behaviour #5),
        checked against values worked out independently of the function."""
        _open(browser_page, live, live.store(_unique_grid(15, 15, seed=19522)))

        result = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              return {
                zoomingIn: S.anchoredScroll(40, 100, 100, 200),
                zoomingOut: S.anchoredScroll(140, 100, 200, 100),
                noChange: S.anchoredScroll(40, 100, 100, 100),
                zeroAnchor: S.anchoredScroll(40, 0, 100, 200),
              };
            }"""
        )

        assert result["zoomingIn"] == pytest.approx(180)  # (40+100)*2 - 100
        assert result["zoomingOut"] == pytest.approx(20)  # (140+100)*0.5 - 100
        assert result["noChange"] == pytest.approx(40)
        assert result["zeroAnchor"] == pytest.approx(80)  # (40+0)*2 - 0
