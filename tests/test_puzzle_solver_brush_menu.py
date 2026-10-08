"""CARD-194 — the puzzle player's brushes become one dropdown with a Region
option; a drag scrolls the page unless Region is picked (owner decision,
2026-10-06).

Before this card ``#puzzle-player-controls .player-tools`` held four toggle
buttons (``[data-player-tool]``: filled/empty/unknown/maybe — Black, White,
Undecided, Maybe), exactly one ``aria-pressed="true"``, and every touch drag
on a cell marked (``.player-cell { touch-action: none }``, admin.css). This
card collapses the four buttons into one trigger (``#puzzle-player-tool-trigger``,
named ``Brush: <brush>``) opening a ``role="menu"`` of five
``role="menuitemradio"`` items in the owner's order — Black, White, Maybe,
Undecided, Region — and adds Region, a modifier (never a cell state) that a
touch or pen drag now needs to mark at all; a mouse drag keeps marking
without it (G-1, the desktop default). ``solver_state.js`` is untouched
(G-2): Region is UI state in ``solver.js``, exactly like ``lastClick`` —
never a brush, never in the history, never saved.

Most of this card's acceptance criteria live beside the code they extend,
per the card's guardrails: AC-5 (a brush's click sequence) in
``test_puzzle_solver_marking.py``'s ``TestSolverClickFollowsTheBrush``, AC-10
(a touch tap still clicks with Region on) in the same file's
``TestSolverClickFollowsTheBrush``, AC-11 (the solved board) in
``test_puzzle_solver_maybe.py``'s ``TestSolverMaybe_HiddenToolsAreOutOfReachWhenSolved``,
AC-13 (touch-action follows Region) in ``test_puzzle_solver_phone.py``'s
``TestSolverPhone_SwipingTheCluesPansTheBoard``, and AC-14 (no request per
mark) in ``test_puzzle_solver_maybe.py``'s ``TestSolverMaybe_NoRequestPerMark``.
What stays here is the menu itself: its shape, its keyboard, and the
Region/touch mechanics that are new in this card (AC-1..AC-4, AC-6..AC-9,
AC-12).

Fixtures (real Chromium refusing loudly when absent, ADR-0038/R8; a loopback
Flask panel over a temp SQLite store) are CARD-160's, imported below, same as
every other puzzle-player test file.
"""

from __future__ import annotations

import pytest

from tests.test_puzzle_solver_marking import (
    _FOCUSED,
    GRID,
    MENU_ORDER,
    E,
    F,
    M,
    _button,
    _cell,
    _centre,
    _drag,
    _marked,
    _menu_item,
    _states,
    _tool,
    _trigger,
    _trigger_text,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    browser_page,
    browser_type,
    live,
)


def _touch_drag_row_1_cols_2_to_6(context, page):
    """Row 2, columns 3 to 7 (1-based) = row index 1, column indexes 2..6 —
    the card's own example, driven by real CDP touch events (never
    page.touchscreen, which Playwright may satisfy as a tap-only gesture)."""
    cdp = context.new_cdp_session(page)
    (x0, y0), (x1, _) = _centre(page, 1, 2), _centre(page, 1, 6)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for k in range(1, 9):
        x = x0 + (x1 - x0) * k / 8
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


# ==========================================================================
# AC-1 / AC-2 — one trigger, a five-item menu
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_OneButtonWithAMenu:
    """AC-1 / AC-2 — the tool group holds one button naming the brush, and
    its menu lists the owner's five items in the owner's order."""

    def test_one_button_with_a_menu(self, browser_page, live) -> None:
        """AC-1."""
        _open(browser_page, live, live.store(GRID))
        group = browser_page.get_by_role("group", name="Marking tool", exact=True)
        trigger = group.get_by_role("button", name="Brush: Black", exact=True)
        assert trigger.count() == 1
        assert trigger.get_attribute("aria-haspopup") == "menu"
        assert trigger.get_attribute("aria-expanded") == "false"
        for name in ("White", "Undecided", "Maybe"):
            assert browser_page.get_by_role("button", name=name, exact=True).count() == 0

    def test_menu_lists_five_items_in_order(self, browser_page, live) -> None:
        """AC-2."""
        _open(browser_page, live, live.store(GRID))
        _trigger(browser_page).click()

        items = browser_page.get_by_role("menuitemradio")
        names = [items.nth(i).text_content().strip() for i in range(items.count())]

        assert names == MENU_ORDER == ["Black", "White", "Maybe", "Undecided", "Region"]
        assert _menu_item(browser_page, "Black").get_attribute("aria-checked") == "true"
        assert all(
            _menu_item(browser_page, name).get_attribute("aria-checked") == "false"
            for name in ("White", "Maybe", "Undecided", "Region")
        )
        assert _trigger(browser_page).get_attribute("aria-expanded") == "true"


# ==========================================================================
# AC-3 / AC-4 — the menu's own keyboard
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_Keyboard:
    """AC-3 / AC-4 — opening from the trigger, moving inside the menu, and
    leaving it by picking an item, Escape or Tab."""

    def test_arrow_and_enter_pick_a_brush(self, browser_page, live) -> None:
        """AC-3."""
        _open(browser_page, live, live.store(GRID))
        _trigger(browser_page).focus()
        browser_page.keyboard.press("Enter")  # opens, focus on the checked item (Black)
        assert browser_page.evaluate("document.activeElement.textContent.trim()") == "Black"
        browser_page.keyboard.press("ArrowDown")  # White, the next item in MENU_ORDER
        assert browser_page.evaluate("document.activeElement.textContent.trim()") == "White"
        browser_page.keyboard.press("Enter")  # picks White

        assert browser_page.locator("#puzzle-player-tool-menu").is_hidden()
        assert browser_page.evaluate("document.activeElement.id") == "puzzle-player-tool-trigger"
        assert _trigger_text(browser_page) == "White"

        _drag(browser_page, [(0, 0), (0, 3)])
        assert _marked(_states(browser_page)) == {(0, c): E for c in range(4)}

    def test_escape_closes_and_tab_leaves(self, browser_page, live) -> None:
        """AC-4."""
        _open(browser_page, live, live.store(GRID))
        before = _states(browser_page)

        _trigger(browser_page).click()
        browser_page.keyboard.press("Escape")

        assert browser_page.locator("#puzzle-player-tool-menu").is_hidden()
        assert browser_page.evaluate("document.activeElement.id") == "puzzle-player-tool-trigger"
        assert _states(browser_page) == before
        assert _trigger_text(browser_page) == "Black"

        _trigger(browser_page).click()
        browser_page.keyboard.press("Tab")

        assert browser_page.locator("#puzzle-player-tool-menu").is_hidden()
        assert browser_page.evaluate(_FOCUSED) == "Undo"


# ==========================================================================
# AC-6 / AC-7 — touch needs Region to mark; off, it scrolls instead
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_Touch:
    """AC-6 / AC-7 — the same real touch drag (CDP touch events, row 2
    columns 3 to 7), with Region off and then on."""

    def test_touch_drag_without_region_scrolls_and_marks_nothing(self, browser, live) -> None:
        """AC-6. Region is off (the default). No cell changes, and nothing
        here stops the browser from scrolling instead of marking: no
        pointer event this drag fires is ``defaultPrevented``, and the
        browser still recognises it as a pan (``pointercancel`` fires,
        exactly as it already does for a cancelled gesture elsewhere —
        TestSolverClickFollowsTheBrush::test_a_cancelled_gesture_makes_the_next_tap_a_first_click
        in test_puzzle_solver_marking.py)."""
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            page.evaluate(
                "window.__events = []; "
                "for (const t of ['pointerdown', 'pointercancel']) "
                "document.addEventListener(t, (e) => window.__events.push([t, e.defaultPrevented]));"
            )

            _touch_drag_row_1_cols_2_to_6(context, page)

            assert _marked(_states(page)) == {}
            assert page.evaluate("window.__events") == [["pointerdown", False], ["pointercancel", False]]
            assert _trigger_text(page) == "Black"  # Region was never picked
        finally:
            context.close()

    def test_touch_drag_with_region_marks_and_region_turns_off(self, browser, live) -> None:
        """AC-7. White is picked, then Region; the same drag marks the five
        cells white, and afterwards the trigger reads "Brush: White" again
        (Region has turned itself off)."""
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _tool(page, "White")
            _tool(page, "Region")

            _touch_drag_row_1_cols_2_to_6(context, page)

            assert _marked(_states(page)) == {(1, c): E for c in range(2, 7)}
            assert _trigger_text(page) == "White"
            _trigger(page).click()
            assert _menu_item(page, "Region").get_attribute("aria-checked") == "false"
            assert _menu_item(page, "White").get_attribute("aria-checked") == "true"
            page.keyboard.press("Escape")
        finally:
            context.close()


# ==========================================================================
# AC-8 / AC-9 — Region with a mouse drag, and a tap with Region on
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_Region:
    """AC-8 / AC-9 / AC-12 — Region's own mechanics beyond touch: a mouse
    drag while it is on, a tap while it is on, and what a reload starts
    with."""

    def test_mouse_region_drag_marks_then_region_turns_off(self, browser_page, live) -> None:
        """AC-8 — Maybe picked, Region on, a mouse drag along row 4
        (index 3) columns 2 to 6 (indexes 1..5): the five cells read "?",
        and afterwards Region is unchecked and Maybe is checked."""
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Maybe")
        _tool(browser_page, "Region")
        _trigger(browser_page).click()  # while Region is on: Region (not Maybe) is checked
        assert _menu_item(browser_page, "Region").get_attribute("aria-checked") == "true"
        assert _menu_item(browser_page, "Maybe").get_attribute("aria-checked") == "false"
        browser_page.keyboard.press("Escape")

        _drag(browser_page, [(3, 1), (3, 5)])

        assert _marked(_states(browser_page)) == {(3, c): M for c in range(1, 6)}
        _trigger(browser_page).click()
        assert _menu_item(browser_page, "Region").get_attribute("aria-checked") == "false"
        assert _menu_item(browser_page, "Maybe").get_attribute("aria-checked") == "true"
        browser_page.keyboard.press("Escape")

    def test_picking_a_brush_turns_region_off(self, browser_page, live) -> None:
        """Target behaviour #3 — Region on, then a different brush is
        picked from the menu with no drag involved: Region turns off
        immediately (distinct from #7's turn-off-after-a-drag, exercised by
        test_mouse_region_drag_marks_then_region_turns_off above)."""
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Region")
        assert _trigger_text(browser_page) == "Region · Black"

        _tool(browser_page, "White")

        assert _trigger_text(browser_page) == "White"
        _trigger(browser_page).click()
        assert _menu_item(browser_page, "Region").get_attribute("aria-checked") == "false"
        browser_page.keyboard.press("Escape")

    def test_a_tap_with_region_clicks_and_region_stays_on(self, browser_page, live) -> None:
        """AC-9 — Black (the default brush), Region on, a blank cell
        clicked once (a mouse click stands for a tap here — AC-7's real
        touch drag already exercises CDP touch input; this is Region's own
        "a non-drag input is a click" rule, independent of pointer type):
        the cell reads black and Region is still on."""
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Region")

        _cell(browser_page, 9, 9).click()

        assert _marked(_states(browser_page)) == {(9, 9): F}
        assert _trigger_text(browser_page) == "Region · Black"

    def test_reload_starts_with_black_and_region_off(self, browser_page, live) -> None:
        """AC-12 — a brush and Region were chosen, and a region drag was
        recorded (so there is history to reload too); after a reload the
        trigger reads "Brush: Black" and Region is off, regardless of what
        was picked before (brush and Region are UI state, never saved —
        G-3)."""
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "White")
        _tool(browser_page, "Region")
        _drag(browser_page, [(2, 0), (2, 3)])
        assert _trigger_text(browser_page) == "White"  # Region turned off; White stayed

        browser_page.reload()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert _trigger_text(browser_page) == "Black"
        assert _button(browser_page, "Brush: Black").count() == 1


# ==========================================================================
# Pen counts as touch (owner decision, Worktree notes — a pen drag needs
# Region exactly like a touch drag does)
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_Pen:
    """A pen behaves like touch (pointerType "pen"), driven through CDP's
    Input.dispatchMouseEvent with pointerType "pen" (Playwright has no pen
    helper; CDP is the same mechanism the touch tests already use for real
    input). Unlike a real touch gesture, a real pen gesture does not
    reliably get pointercancel from Chromium's own pan recognition even
    after real movement — this is exactly the gap a drag that moves but
    never paints must still not fall back to "click the start cell" for
    (solver.js pointerup's `done.paints` branch)."""

    @staticmethod
    def _pen_drag(context, page, start, end, steps=8):
        cdp = context.new_cdp_session(page)
        (x0, y0), (x1, y1) = _centre(page, *start), _centre(page, *end)
        cdp.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x0, "y": y0, "button": "left", "clickCount": 1, "pointerType": "pen"})
        for k in range(1, steps + 1):
            x = x0 + (x1 - x0) * k / steps
            cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": x, "y": y0, "button": "left", "pointerType": "pen"})
        cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x1, "y": y0, "button": "left", "clickCount": 1, "pointerType": "pen"})

    def test_pen_drag_without_region_marks_nothing_not_even_the_start_cell(self, browser, live) -> None:
        """Region off (the default): a pen drag across row 2, columns 3 to 7
        marks nothing at all — not the five cells a region drag would give,
        and not even the start cell alone (the bug this test guards: a drag
        that never paints must not be read as a click on release just
        because the browser happened not to cancel it)."""
        context = browser.new_context(viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            page.evaluate(
                "window.__types = []; document.addEventListener('pointerdown', (e) => window.__types.push(e.pointerType));"
            )

            self._pen_drag(context, page, (1, 2), (1, 6))

            assert page.evaluate("window.__types") == ["pen"]
            assert _marked(_states(page)) == {}
            assert _trigger_text(page) == "Black"
        finally:
            context.close()

    def test_pen_drag_with_region_marks_like_touch(self, browser, live) -> None:
        """Region on: a pen drag marks exactly like the touch case (AC-7),
        and turns Region off afterwards."""
        context = browser.new_context(viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _tool(page, "White")
            _tool(page, "Region")

            self._pen_drag(context, page, (1, 2), (1, 6))

            assert _marked(_states(page)) == {(1, c): E for c in range(2, 7)}
            assert _trigger_text(page) == "White"
        finally:
            context.close()
