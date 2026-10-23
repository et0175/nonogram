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

import re

import pytest

from tests.test_puzzle_solver_brush_menu import _touch_drag_row_1_cols_2_to_6
# CARD-271: the "is it in view?" reading, and CARD-212's own doubled board.
from tests.test_puzzle_solver_clues import GRID_30x25 as _GRID_30x25
from tests.test_puzzle_solver_clues import STICK_MAX_SHARE, GUTTER_PAINTS
from tests.test_puzzle_solver_clues import _in_view, _room, _to_corner
from tests.test_puzzle_solver_marking import (
    E,
    GRID,
    F,
    _cell,
    _centre,
    _drag,
    _marked,
    _region,
    _states,
    _tool,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _STATIC,
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_phone import BIG
from tests.test_puzzle_solver_progress import _set

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
            _region(page)  # CARD-211: Region is its own toggle now
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
            _region(page)  # CARD-211: Region is its own toggle now
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


# ==========================================================================
# CARD-212 AC-8 — a doubled board redrawn across the breakpoint, zoomed
# ==========================================================================

#: CARD-212's own fixtures: a board big on the row axis only (30 wide, 12
#: tall) at a viewport measured to afford both row gutters (28 px cells), and
#: a board big on both axes at a laptop window, where doubling would leave
#: 19.75 px cells and so does not happen.
_GRID_30x12 = _unique_grid(30, 12, seed=2121)
_GRID_30x25 = _unique_grid(30, 25, seed=212)
_WIDE = {"width": 1920, "height": 1080}
#: Room for all four gutters on a 30 x 25 (28 px cells), and a window with
#: room for none of them that is still nowhere near the 820 px breakpoint.
_ROOMY = {"width": 1920, "height": 1500}
_NARROW = {"width": 1100, "height": 900}
_LAPTOP = {"width": 1440, "height": 900}
_PHONE = {"width": 390, "height": 844}

#: How long a resize-driven redraw is allowed to take before the test calls
#: it broken. This bound guards against the board NOT settling at all — the
#: listener never firing, the debounce never resolving — and deliberately
#: not against slowness: what these tests assert is that the board settles
#: into the layout a reload would give, never how fast it gets there. The
#: redraw it has to cover is the most expensive one this card can ask for (a
#: doubled 30 x 25 rebuilt from scratch) on a machine that may be running
#: another worktree's browser suite at the same time; at 600 ms it lost
#: exactly that race at a merge gate, with the whole test taking 2.8-5.2 s
#: when run alone. Ten seconds is far above any redraw observed and still
#: finishes long before Playwright's own 30 s default.
#:
#: The DEBOUNCE's value is pinned where it belongs, by reading the constant
#: (test_the_resize_debounce_is_short_enough_to_be_a_debounce below), not by
#: racing it here — a bound doing both jobs is a stopwatch pretending to be
#: an assertion (CARD-212 review cycles 2-3, G-001).
_SETTLE_BOUND = 10_000

#: How long the burst test waits after the board has settled, to catch a
#: SECOND redraw that a lost clearTimeout would schedule. A few times
#: solver.js's RESIZE_SETTLE: the stray timers a per-event listener leaves
#: are all due within one debounce of the last event, so this is slack, not
#: a race — the draw count is what decides that test.
_BURST_QUIET = 800

#: The duplicates are gone (or, with the count swapped, back).
_NO_DUPLICATES = ("[...document.querySelectorAll('th.player-clue')]"
                  ".filter((box) => box.getAttribute('aria-hidden')).length === 0")

#: How many boards solver.js has built on this page (its draw mark).
_DRAWN_BOARDS = "performance.getEntriesByName('nonogram-player-board-draw').length"

#: What the board settled into at this window, independent of how it got
#: here (CARD-212 F-001: a resize must land where a reload would).
_FIT_SHAPE = """() => {
  const stage = document.querySelector('.player-stage');
  return {
    duplicates: [...document.querySelectorAll('th.player-clue')]
      .filter((box) => box.getAttribute('aria-hidden')).length,
    feet: document.querySelectorAll('.player-board tfoot tr').length,
    cell: document.querySelector('td.player-cell').getBoundingClientRect().width,
    overflowX: stage.scrollWidth - stage.clientWidth,
    overflowY: stage.scrollHeight - stage.clientHeight,
  };
}"""

_GUTTER_SHAPE = """() => {
  const table = document.querySelector('.player-board');
  return {
    rowBoxes: table.querySelectorAll('th.player-clue.is-row').length,
    colBoxes: table.querySelectorAll('th.player-clue.is-col').length,
    duplicates: table.querySelectorAll('th.player-clue[aria-hidden="true"]').length,
    mirrored: table.classList.contains('is-mirrored'),
    zoomProperty: table.style.getPropertyValue('--player-zoom'),
    circled: [...table.querySelectorAll('.player-clue-num.is-circled')].length,
    circledRow0: [...table.querySelectorAll('th.player-clue.is-row[data-line="0"]')].map(
      (box) => [...box.querySelectorAll('.player-clue-num')].map((n) => n.classList.contains('is-circled'))),
  };
}"""


@pytest.mark.browser
class TestSolverZoom_SurvivesADoubledRedraw:
    """CARD-212 AC-8 — a board whose clues are repeated on both sides is
    redrawn by the same ``redraw()`` CARD-193's mirror uses, so crossing the
    820 px breakpoint re-chooses the gutter layout. The marks, the zoom and
    the circles survive that, in both directions: nothing recorded and
    nothing of the view is lost when the duplicate gutters go away at phone
    width, or when they come back.

    And the layout the redraw lands on does not depend on the zoom: zoom
    multiplies the drawn cell, so solver.js divides it out again before
    comparing against DOUBLE_MIN_CELL. Without that, a 30 x 25 at 1440 x 900
    — 16 px cells doubled, which is why it is NOT doubled — would double on
    the next redraw at 150%, where those same cells measure 24 px.
    """

    def test_marks_zoom_and_circles_survive_crossing_both_ways(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(_WIDE)
        puzzle_id = live.store(_GRID_30x12)
        _open(page, live, puzzle_id)
        doubled = page.evaluate(_GUTTER_SHAPE)
        assert (doubled["rowBoxes"], doubled["colBoxes"], doubled["duplicates"]) == (24, 30, 12)

        # Row 0 fully marked: its clue numbers settle, so they circle — in
        # both gutters (CARD-188 + CARD-212 AC-4).
        width = len(_GRID_30x12[0])
        cells = ["unknown"] * (width * len(_GRID_30x12))
        for col, on in enumerate(_GRID_30x12[0]):
            cells[col] = "filled" if on else "empty"
        _set(page, cells)
        _zoom_to(page, 150)

        before = _board_snapshot(page, puzzle_id)
        shaped = page.evaluate(_GUTTER_SHAPE)
        numbers = len(shaped["circledRow0"][0])
        assert numbers > 1  # a 30-wide tight row: several numbers to circle
        assert shaped["circledRow0"] == [[True] * numbers] * 2  # both gutters
        assert shaped["circled"] == 2 * numbers  # only row 0's, in both gutters
        assert shaped["zoomProperty"] == "1.5"

        # Crossing to phone width: the duplicates cannot be afforded there,
        # so the board falls back to CARD-193's single mirrored gutter.
        page.set_viewport_size(_PHONE)
        page.wait_for_function("document.querySelector('.player-board').classList.contains('is-mirrored')")
        phone = page.evaluate(_GUTTER_SHAPE)

        assert (phone["rowBoxes"], phone["colBoxes"], phone["duplicates"]) == (12, 30, 0)
        assert _board_snapshot(page, puzzle_id) == before
        assert _zoom_readout(page) == "150%" and phone["zoomProperty"] == "1.5"
        assert phone["circledRow0"] == [[True] * numbers]  # the one gutter, still circled
        assert phone["circled"] == numbers

        # And back: the duplicates return, with the marks, the zoom and the
        # circles unchanged.
        page.set_viewport_size(_WIDE)
        page.wait_for_function(
            "[...document.querySelectorAll('th.player-clue')]"
            ".filter((box) => box.getAttribute('aria-hidden')).length === 12")
        again = page.evaluate(_GUTTER_SHAPE)

        assert _board_snapshot(page, puzzle_id) == before
        assert _zoom_readout(page) == "150%" and again["zoomProperty"] == "1.5"
        assert again == shaped

    def test_zooming_in_does_not_make_a_redraw_double_the_gutters(self, browser_page, live) -> None:
        page = browser_page
        page.set_viewport_size(_LAPTOP)
        _open(page, live, live.store(_GRID_30x25))
        plain = page.evaluate(_GUTTER_SHAPE)
        assert (plain["rowBoxes"], plain["colBoxes"], plain["duplicates"]) == (25, 30, 0)
        assert _cell_widths(page)[0] == pytest.approx(19.75, abs=0.05)

        _zoom_to(page, 150)
        # 150% of the doubled layout's 16 px cells is exactly the 24 px the
        # duplicate is conditional on — the number this test exists to keep
        # out of the decision.
        assert _cell_widths(page)[0] == pytest.approx(19.75 * 1.5, abs=0.05)

        # Force the redraw the breakpoint listener performs (out to phone
        # width and back), where a zoom-blind decision would double.
        page.set_viewport_size(_PHONE)
        page.wait_for_function("document.querySelector('.player-board').classList.contains('is-mirrored')")
        page.set_viewport_size(_LAPTOP)
        page.wait_for_function("!document.querySelector('.player-board').classList.contains('is-mirrored')")

        after = page.evaluate(_GUTTER_SHAPE)
        assert (after["rowBoxes"], after["colBoxes"], after["duplicates"]) == (25, 30, 0)
        assert _zoom_readout(page) == "150%" and after["zoomProperty"] == "1.5"

    def test_a_resize_that_never_crosses_the_breakpoint_rechooses_the_layout(
        self, browser_page, live
    ) -> None:
        """CARD-212 (review cycle 1, F-001) — the duplicate's condition is a
        measurement of the drawn board, not a media query, so it has to
        follow the WINDOW and not only the 820 px breakpoint. Before the
        resize listener, a 30 x 25 loaded at 1920 x 1500 and resized to
        1100 x 900 — never crossing 820 px — kept all 55 duplicates at
        14.39 px cells, 9.6 px under the bar they are conditional on, with
        sideways scroll inside the stage that the same board reloaded at
        that size does not have.

        Now the board settles into the layout a reload would have given it
        (measured: 17.63 px cells, no duplicates, the same 1 px of rounding
        overflow a reload shows), and crossing back brings them back — with
        the marks, the zoom and the circles carried through both redraws,
        exactly as the breakpoint crossing carries them.
        """
        page = browser_page
        page.set_viewport_size(_ROOMY)
        puzzle_id = live.store(_GRID_30x25)
        _open(page, live, puzzle_id)
        assert page.evaluate(_GUTTER_SHAPE)["duplicates"] == 55

        width = len(_GRID_30x25[0])
        cells = ["unknown"] * (width * len(_GRID_30x25))
        for col, on in enumerate(_GRID_30x25[0]):
            cells[col] = F if on else E
        _set(page, cells)
        _zoom_to(page, 150)
        before = _board_snapshot(page, puzzle_id)
        doubled = page.evaluate(_GUTTER_SHAPE)
        numbers = len(doubled["circledRow0"][0])
        assert doubled["circledRow0"] == [[True] * numbers] * 2 and numbers > 1

        page.set_viewport_size(_NARROW)
        page.wait_for_function(_NO_DUPLICATES, timeout=_SETTLE_BOUND)
        narrow = page.evaluate(_GUTTER_SHAPE)
        cell = page.evaluate("document.querySelector('td.player-cell').getBoundingClientRect().width")

        assert narrow["mirrored"] is False  # 1100 px: the 820 px query never fired
        assert (narrow["rowBoxes"], narrow["colBoxes"]) == (25, 30)
        # 17.63 px is what this board measures at this window (the next test
        # takes that from a reload rather than from this number); the zoom
        # multiplies it and does not survive as anything else.
        assert cell == pytest.approx(17.63 * 1.5, abs=0.08), cell
        assert _board_snapshot(page, puzzle_id) == before
        assert _zoom_readout(page) == "150%" and narrow["zoomProperty"] == "1.5"
        assert narrow["circledRow0"] == [[True] * numbers]

        page.set_viewport_size(_ROOMY)
        page.wait_for_function(_NO_DUPLICATES.replace("=== 0", "=== 55"), timeout=_SETTLE_BOUND)
        again = page.evaluate(_GUTTER_SHAPE)

        assert again == doubled
        assert _board_snapshot(page, puzzle_id) == before
        assert _zoom_readout(page) == "150%"

    def test_a_resize_settles_on_the_layout_a_reload_would_have_given(self, browser_page, live) -> None:
        """The same thing stated as the property rather than as numbers: after
        the window changes, the board is the board that window would have
        produced from scratch. Before the listener, the resized board had 55
        duplicates and 14.39 px cells where the reloaded one has none and
        17.63 px — and the duplicates were buying hundreds of pixels of
        sideways scroll instead of saving them."""
        page = browser_page
        page.set_viewport_size(_ROOMY)
        puzzle_id = live.store(_GRID_30x25)
        _open(page, live, puzzle_id)
        assert page.evaluate(_GUTTER_SHAPE)["duplicates"] == 55

        page.set_viewport_size(_NARROW)
        page.wait_for_function(_NO_DUPLICATES, timeout=_SETTLE_BOUND)
        resized = page.evaluate(_FIT_SHAPE)

        _open(page, live, puzzle_id)  # the same window, from scratch
        reloaded = page.evaluate(_FIT_SHAPE)

        assert resized == reloaded, (resized, reloaded)
        assert resized["duplicates"] == 0 and resized["cell"] == pytest.approx(17.63, abs=0.05)
        assert resized["overflowX"] <= 1, resized

    def test_the_resize_debounce_is_short_enough_to_be_a_debounce(self) -> None:
        """What a debounce is worth is its length, so that is asserted as a
        length and not as a race (CARD-212 review cycle 3). solver.js's
        RESIZE_SETTLE is read from the file: a listener that waits about a
        seventh of a second (150 ms) after the last event coalesces a window
        drag into one redraw, which is the point; one that waits seconds
        stops being a debounce and becomes a board that visibly trails its
        window, and one that waits a few milliseconds stops coalescing at
        all.

        This is the test that kills a stretched debounce. The settle waits
        above no longer do — their bound is deliberately generous now, for
        the reason given at _SETTLE_BOUND — and the burst test below is
        about the clearTimeout, not the delay. A later reader changing
        RESIZE_SETTLE should expect to meet this test and no other.
        """
        source = (_STATIC / "solver.js").read_text()
        declared = re.search(r"^const RESIZE_SETTLE = (\d+);$", source, re.M)
        assert declared, "solver.js no longer declares RESIZE_SETTLE"
        settle = int(declared.group(1))
        assert 50 <= settle <= 400, (
            f"RESIZE_SETTLE is {settle} ms: under ~50 ms it stops coalescing a drag, "
            f"over ~400 ms the board visibly trails the window")
        # And the tests above are written against that length: the quiet
        # period the burst test waits out has to clear it comfortably.
        assert _BURST_QUIET >= 4 * settle, (settle, _BURST_QUIET)

    def test_a_burst_of_resize_events_redraws_once(self, browser_page, live) -> None:
        """The listener is debounced, not throttled and not per-event: a drag
        across a window edge fires `resize` continuously, and each redraw is
        a board build. Eight events inside the debounce must cost one redraw
        — two if the timer happens to fire mid-burst — never eight, which is
        what the draw marks are counted for here (CARD-212 review cycle 2,
        G-001: without the clearTimeout this test is the one that notices).
        """
        page = browser_page
        page.set_viewport_size(_NARROW)
        _open(page, live, live.store(_GRID_30x25))
        before = page.evaluate(_DRAWN_BOARDS)
        assert before == 1  # one board at this window: nothing is afforded

        for step in range(8):  # eight events, each a pixel apart
            page.set_viewport_size({"width": _NARROW["width"] - step - 1, "height": _NARROW["height"]})
        page.wait_for_function(f"{_DRAWN_BOARDS} > {before}", timeout=_SETTLE_BOUND)
        page.wait_for_timeout(_BURST_QUIET)  # let any further timers fire

        after = page.evaluate(_DRAWN_BOARDS)
        assert 1 <= after - before <= 2, after - before

    def test_a_board_too_small_to_double_is_not_redrawn_by_a_resize(self, browser_page, live) -> None:
        """The listener's guard: a board past neither side's 15 can have no
        mirror and no duplicate, so no window size changes what it draws and
        it is never redrawn. Counted with the draw mark rather than inferred
        from the DOM, which would look the same either way."""
        page = browser_page
        page.set_viewport_size({"width": 1440, "height": 900})
        _open(page, live, live.store(_unique_grid(15, 15, seed=21215)))
        draws = "() => performance.getEntriesByName('nonogram-player-board-draw').length"
        assert page.evaluate(draws) == 1

        page.set_viewport_size({"width": 1000, "height": 700})
        page.wait_for_timeout(500)  # four times RESIZE_SETTLE

        assert page.evaluate(draws) == 1
        assert page.evaluate(_GUTTER_SHAPE)["duplicates"] == 0


# ==========================================================================
# CARD-271 — the clues stay in view while zoomed, up to where the band fits
#
# Zoom is where every big board loses its clues, doubled or not: the stage
# overflows in both directions and both bands scroll clean out of it, and a
# doubled board's duplicates — the whole point of which was the far edge —
# end up thousands of pixels from wherever the player is working. Since
# CARD-271 each axis keeps its labelled gutter stuck to the scrollport while
# it has the room, so panning to any corner leaves that cell's row clue and
# column clue in view.
#
# "While it has the room" is the whole story at high zoom, and it is this
# card's second unfixed case. --player-zoom multiplies the cell, and the clue
# numerals are 0.6 x the cell, so the BAND is magnified about as much as the
# cells are: its share of the stage barely falls, and past STICK_MAX_SHARE of
# the stage it would hide more board than it is worth. Measured on this host,
# Chromium, stepping the zoom buttons (keepCluesInView runs after each):
#
#   30 x 30 at 1280 x 720, stage 980 x 492 (plain, one gutter per axis)
#     zoom       100    125    150    175    200    225    250    275    300
#     rows        y      y      y      y      y      n      n      n      n
#     cols        y      y      n      n      n      n      n      n      n
#     col band  135.4  168.6  201.7  234.7  267.9  301.0  334.2  367.3  400.3
#
#   30 x 25 at 1920 x 1500, stage 1620 x 1272 (doubled, all four gutters)
#     zoom       100    125    150    175    200    225    250    275    300
#     rows        y      y      y      n      n      n      n      n      n
#     cols        y      y      y      y      y      n      n      n      n
#
# So the card's "any big board at 300 % zoom" is NOT delivered, and the reason
# is the band's magnification rather than stickiness: at 300 % the plain
# board's column band is 400.3 px of a 492 px stage — about nine cells of an
# eleven-cell-tall view. Not magnifying the clue band with the cells would
# turn every column of both tables above into a "y"; that is a CARD-195
# decision about what zoom means, recorded as an owner decision on CARD-271.
#
# The two cases asserted below are the ones where the mechanism works hardest
# — both axes keeping their clues while both axes really do scroll:
#
#   plain     30 x 30 at 900 x 700, 125 %: stage 600 x 472, overflow
#             (212, 253) against bands (272.2, 168.6)
#   doubled   30 x 25 at 1920 x 1500, 150 %: stage 1620 x 1272, overflow
#             (778, 487) — past BOTH bands (567.9, 347.4), so without the
#             stick every one of this board's four gutters leaves the view
# ==========================================================================

#: The 30 x 30 the plain cases use (the board CARD-271's desktop cases use
#: too, over in tests/test_puzzle_solver_clues.py).
_GRID_30x30 = _unique_grid(30, 30, seed=19330)


@pytest.mark.browser
class TestSolverZoom_CluesStayInViewWhileZoomed:
    """AC-3 — zoomed in, panned to each corner of the stage, the clue boxes
    of the row and the column under that corner are in view.

    Four corners per board, and the corner the pan lands on decides which
    cell is asked about: at the top-left the board's first row and column, at
    the bottom-right its last. The two boards cover the two layouts a big
    board can be in — plain (one gutter per axis, the commonest) and doubled
    (CARD-212's four gutters, where the stuck gutter is the labelled one and
    the duplicate deliberately scrolls) — each at the highest zoom that keeps
    both axes, which is where the mechanism is working hardest.
    """

    @pytest.mark.parametrize(
        "name, grid, viewport, feet, zoom, expected",
        [
            ("plain 30x30 at 900x700", _GRID_30x30, {"width": 900, "height": 700}, 0, 125,
             [212, 253]),
            ("doubled 30x25 at 1920x1500", _GRID_30x25, _ROOMY, 1, 150, [778, 487]),
        ],
        ids=lambda value: value if isinstance(value, str) else "",
    )
    def test_every_corner_keeps_that_cells_clues_in_view(
        self, browser_page, live, name, grid, viewport, feet, zoom, expected
    ) -> None:
        page = browser_page
        page.set_viewport_size(viewport)
        _open(page, live, live.store(grid))
        # Which layout this is, asserted rather than assumed — the case is
        # the layout, and the ladder measures.
        assert page.evaluate("document.querySelectorAll('.player-board tfoot tr').length") == feet

        _zoom_to(page, zoom)
        height = len(grid)
        width = len(grid[0])
        room = _room(page)
        assert room["keeping"] == [True, True], (name, room)
        # Both axes really do scroll, so neither band could stay in view by
        # accident: without the stick each one leaves the stage, wholly on
        # the doubled board (whose overflow is past both of its bands) and in
        # part on the plain one.
        assert room["overflow"][0] > 0 and room["overflow"][1] > 0, (name, room)
        assert room["overflow"] == expected, (name, room)

        for corner, (row, col) in (
            ("top-left", (0, 0)), ("top-right", (0, width - 1)),
            ("bottom-left", (height - 1, 0)), ("bottom-right", (height - 1, width - 1)),
        ):
            _to_corner(page, col, row)
            seen = _in_view(page, row, col)

            assert seen["row"]["inside"], (name, corner, seen["row"])
            assert seen["col"]["inside"], (name, corner, seen["col"])
            assert seen["row"]["hit"] in GUTTER_PAINTS, (name, corner, seen["row"])
            assert seen["col"]["hit"] in GUTTER_PAINTS, (name, corner, seen["col"])
            # Pinned to the scrollport's own edge, whichever corner this is:
            # the row band to the left (the mirror never holds at these
            # widths) and the column band to the top.
            assert seen["row"]["dLeft"] == 0, (name, corner, seen["row"])
            assert seen["col"]["dTop"] == 0, (name, corner, seen["col"])

    #: The table in this section's comment, as the assertion that keeps it
    #: true: for the plain 30 x 30 at 1280 x 720, the zoom at which each axis
    #: stops keeping its clues. ``None`` would mean "keeps all the way to
    #: 300 %", which neither axis does on this board.
    GIVES_UP_AT = {"rows": 225, "cols": 150}

    def test_each_axis_keeps_its_clues_up_to_the_zoom_its_band_outgrows(
        self, browser_page, live
    ) -> None:
        """The boundary of this card's fix, pinned so that it is a recorded
        limitation and not a surprise: stepping 100 % to 300 %, each axis
        keeps its gutter until its band would hide more than
        ``STICK_MAX_SHARE`` of the stage, and from there on the board renders
        exactly as it did before this card. A band that stopped being
        magnified by zoom would move both numbers below to "never", which is
        the owner decision this records.

        The share is NAMED here rather than quantified, which is how CARD-271's
        pre-gate finding PG-1 is fixed in a form that cannot drift again: this
        sentence said "half" while solver.js declared two fifths, and the loop
        below re-derives the decision from the imported constant — so the
        figure in the prose was a stale copy and never a second opinion. The
        number has one home, solver.js, and nothing restates it.
        """
        page = browser_page
        page.set_viewport_size({"width": 1280, "height": 720})
        _open(page, live, live.store(_GRID_30x30))

        ladder = {}
        for percent in range(100, 325, 25):
            _zoom_to(page, percent)
            room = _room(page)
            ladder[percent] = room["keeping"]
            # The rule, re-derived from this zoom's own measurements rather
            # than read off the classes — off the RAW cover, the number
            # solver.js actually compares, not the rounded one the report
            # quotes (CARD-271 review cycle 2, F-101; see _ROOM). This is one
            # of the two controls holding an owner decision, so a ±0.05 px
            # window here is a window in the decision.
            assert room["keeping"] == [
                room["coverRaw"][axis] <= room["port"][axis] * STICK_MAX_SHARE
                for axis in (0, 1)], (percent, room)

        kept = {
            "rows": [p for p, (rows, _cols) in ladder.items() if rows],
            "cols": [p for p, (_rows, cols) in ladder.items() if cols],
        }
        for axis, gives_up in self.GIVES_UP_AT.items():
            # Kept from 100 % up to the step before it gives up, and never
            # again after — one contiguous run, so "it gives up at N" is a
            # real boundary and not a hole in the middle.
            assert kept[axis] == list(range(100, gives_up, 25)), (axis, kept)

    def test_zooming_and_panning_record_and_save_nothing(self, browser_page, live) -> None:
        """G-4 / CON-021 — a scroll, and the sticky repaint it causes, are not
        state: the marks, the counters, undo/redo and the localStorage save
        are byte-identical across zooming in, panning to every corner, and
        coming back. (TestSolverZoom_IsNotSavedAndSendsNothing above says that
        of the zoom itself; this adds the panning, which is what CARD-271
        made the gutters respond to, and the re-measurement that each zoom
        step now runs.)

        The stickiness PRECONDITION is read where it has to be read and
        JUDGED after the recording assertion, which is the point (CARD-271
        review cycle 1, F-004). Asserted inside the pan loop it reddened this
        test before ``_board_snapshot`` was ever compared, so a stickiness
        regression — which is not a recording regression — was reported as a
        CON-021 failure with CON-021's own property unevaluated: on exactly
        the cycles where stickiness broke, panning's recording property went
        unverified while the report said a CON-021 test red. The review's own
        suggestion was to hoist it above the loop, which fixes the
        attribution but still aborts before the snapshot; keeping the readings
        and judging them last fixes both, and loses nothing the in-loop
        assertion covered.
        """
        page = browser_page
        page.set_viewport_size({"width": 900, "height": 700})
        puzzle = live.store(_GRID_30x30)
        _open(page, live, puzzle)
        _set(page, [F if on else E for on in _GRID_30x30[0]] + ["unknown"] * (30 * 29))
        before = _board_snapshot(page, puzzle)

        _zoom_to(page, 125)
        # Read, not yet judged: that both bands ARE stuck at this board,
        # viewport and zoom is what makes the pans below drag the board under
        # a kept gutter, rather than this being a test of a board where
        # sticking never happened.
        panned = [_room(page)["keeping"]]
        for x, y in ((0, 0), (1, 0), (0, 1), (1, 1), (0, 0)):
            _to_corner(page, x, y)
            panned.append(_room(page)["keeping"])
        _zoom_to(page, 100)

        # The control's own subject, first and unconditionally.
        assert _board_snapshot(page, puzzle) == before
        # ...and then the precondition, at the zoom and through every pan — a
        # scroll position is not one of the room condition's terms, so it
        # cannot change the answer.
        assert panned == [[True, True]] * 6, panned
