"""CARD-194 — the puzzle player's brushes become one dropdown with a Region
option; a drag scrolls the page unless Region is picked (owner decision,
2026-10-06). CARD-211 — Region leaves that dropdown and becomes a toggle
control of its own beside it (owner's doc, 2026-10-13).

Before CARD-194 ``#puzzle-player-controls .player-tools`` held four toggle
buttons (``[data-player-tool]``: filled/empty/unknown/maybe — Black, White,
Undecided, Maybe), exactly one ``aria-pressed="true"``, and every touch drag
on a cell marked (``.player-cell { touch-action: none }``, admin.css). That
card collapsed the four buttons into one trigger
(``#puzzle-player-tool-trigger``, named ``Brush: <brush>``) opening a
``role="menu"`` of five ``role="menuitemradio"`` items in the owner's order —
Black, White, Maybe, Undecided, Region — and added Region, a modifier (never
a cell state) that a touch or pen drag now needs to mark at all; a mouse drag
keeps marking without it (G-1, the desktop default).

CARD-211 changes WHERE that modifier lives and HOW it is exposed, and nothing
about what it does. The menu holds the four brushes only; Region is
``[data-player-region]`` (``#puzzle-player-region``), the brush trigger's
sibling inside ``.player-tools``, a toggle carrying ``aria-pressed`` rather
than a radio carrying ``aria-checked`` — it is a mode, not one option among
several, and that is what a screen reader should announce. CARD-194's
composite ``Region · <brush>`` trigger text is gone with the menu item: the
trigger reads the brush alone and its ``aria-label`` stays
``Brush: <brush>``, while every flip of the toggle is announced through the
player's existing ``#puzzle-player-announce`` live region. The flag itself is
still UI state in ``solver.js`` — never a brush, never in the history, never
saved — but its transition table and the "does this drag paint?" rule are now
pure functions in ``solver_state.js`` (``nextRegion``, ``gesturePaints``;
ADR-0038/R4), exercised here through the page they drive.

Most of CARD-194's acceptance criteria live beside the code they extend, per
that card's guardrails: AC-5 (a brush's click sequence) in
``test_puzzle_solver_marking.py``'s ``TestSolverClickFollowsTheBrush``, AC-10
(a touch tap still clicks with Region on) in the same file's
``TestSolverClickFollowsTheBrush``, AC-11 (the solved board) in
``test_puzzle_solver_maybe.py``'s
``TestSolverMaybe_HiddenToolsAreOutOfReachWhenSolved`` (which since CARD-211
also covers the Region toggle going out of reach with the rest of the tools),
AC-13 (touch-action follows Region) in ``test_puzzle_solver_phone.py``'s
``TestSolverPhone_SwipingTheCluesPansTheBoard``, and AC-14 (no request per
mark) in ``test_puzzle_solver_maybe.py``'s ``TestSolverMaybe_NoRequestPerMark``.
What stays here is the menu itself — its shape and its keyboard — and Region:
its control, its mechanics and its announcements.

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
    SIDE,
    E,
    F,
    M,
    U,
    _button,
    _cell,
    _centre,
    _drag,
    _marked,
    _menu_item,
    _region,
    _region_pressed,
    _region_toggle,
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
from tests.test_puzzle_solver_progress import (
    LONG_RUN,
    _is_solved_shown,
    _set,
    _solution_cells,
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


def _announced(page):
    """What the player's one live region currently says
    (#puzzle-player-announce — shared with the solved banner and the hints;
    see solver.js)."""
    return page.locator("#puzzle-player-announce").text_content().strip()


def _tab_until(page, name, limit=40):
    """Tab from wherever focus is until the named player control has it;
    returns the player controls reached, in order."""
    reached = []
    for _ in range(limit):
        page.keyboard.press("Tab")
        focused = page.evaluate(_FOCUSED)
        if focused:
            reached.append(focused)
            if focused == name:
                break
    return reached


# ==========================================================================
# CARD-194 AC-1 — one trigger standing in for the four brushes
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_OneButtonWithAMenu:
    """CARD-194 AC-1 — the tool group holds one button naming the brush, and
    no standalone button per brush."""

    def test_one_button_with_a_menu(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        group = browser_page.get_by_role("group", name="Marking tool", exact=True)
        trigger = group.get_by_role("button", name="Brush: Black", exact=True)
        assert trigger.count() == 1
        assert trigger.get_attribute("aria-haspopup") == "menu"
        assert trigger.get_attribute("aria-expanded") == "false"
        for name in ("White", "Undecided", "Maybe"):
            assert browser_page.get_by_role("button", name=name, exact=True).count() == 0


# ==========================================================================
# AC-1 — the menu holds exactly the four brushes, and no Region item
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_HoldsFourBrushesOnly:
    """CARD-211 AC-1 (and what is left of CARD-194 AC-2) — opened, the menu
    lists the owner's four brushes in the owner's order with exactly one
    checked, and Region is not among them in any form: not by name, not by
    the ``data-player-tool="region"`` value CARD-194 gave it, and not as a
    fifth ``menuitemradio``.

    Mutant: leaving CARD-194's Region ``<button role="menuitemradio">`` in
    ``puzzle_solve.html`` fails every assertion of the second test here and
    the item count of the first."""

    def test_menu_lists_the_four_brushes_in_order(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _trigger(browser_page).click()

        items = browser_page.get_by_role("menuitemradio")
        names = [items.nth(i).text_content().strip() for i in range(items.count())]

        assert names == MENU_ORDER == ["Black", "White", "Maybe", "Undecided"]
        assert _menu_item(browser_page, "Black").get_attribute("aria-checked") == "true"
        assert all(
            _menu_item(browser_page, name).get_attribute("aria-checked") == "false"
            for name in ("White", "Maybe", "Undecided")
        )
        assert _trigger(browser_page).get_attribute("aria-expanded") == "true"
        browser_page.keyboard.press("Escape")

    def test_no_region_item_is_left_in_the_menu(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _trigger(browser_page).click()

        menu = browser_page.locator("#puzzle-player-tool-menu")
        assert menu.get_by_role("menuitemradio", name="Region", exact=True).count() == 0
        assert menu.locator('[data-player-tool="region"]').count() == 0
        assert menu.locator("[data-player-region]").count() == 0
        # The Region control is outside the menu, in the tool group (AC-2).
        assert browser_page.locator(".player-tools > [data-player-region]").count() == 1
        browser_page.keyboard.press("Escape")


# ==========================================================================
# AC-2 — Region is its own toggle, outside the menu
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_RegionIsItsOwnToggle:
    """CARD-211 AC-2 — at load the Region control is a <button> of its own,
    beside the brush trigger and outside the menu, carrying its state in
    ``aria-pressed`` (a mode, not a radio: no ``aria-checked``, no menu
    role), reachable by Tab in the toolbar's order right after the trigger
    and before Undo, and wearing the toolbar's own button pattern
    (``.btn.btn-outline-secondary``, like the history buttons) so it keeps a
    tap target on a 390 px phone."""

    def test_it_is_a_pressed_state_button_outside_the_menu(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))

        toggle = browser_page.get_by_role("button", name="Region", exact=True)
        assert toggle.count() == 1
        assert _region_pressed(browser_page) == "false"
        assert toggle.get_attribute("aria-checked") is None
        assert toggle.get_attribute("role") is None  # a plain button, not a menuitem
        assert browser_page.get_by_role("menuitemradio", name="Region", exact=True).count() == 0
        # Outside the menu, inside the tool group, after the brush trigger.
        assert browser_page.evaluate(
            """() => {
              const tools = document.querySelector('.player-tools');
              const toggle = document.querySelector('[data-player-region]');
              const trigger = document.getElementById('puzzle-player-tool-trigger');
              const menu = document.getElementById('puzzle-player-tool-menu');
              return {
                inTools: toggle.parentElement === tools,
                inMenu: menu.contains(toggle),
                afterTrigger: Boolean(trigger.compareDocumentPosition(toggle)
                  & Node.DOCUMENT_POSITION_FOLLOWING),
                toolsButtons: [...tools.children].filter((el) => el.tagName === 'BUTTON').length,
              };
            }"""
        ) == {"inTools": True, "inMenu": False, "afterTrigger": True, "toolsButtons": 2}

    def test_tab_reaches_it_between_the_trigger_and_undo(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        browser_page.evaluate("document.activeElement && document.activeElement.blur()")

        reached = _tab_until(browser_page, "Undo")

        assert reached[-3:] == ["Brush: Black", "Region", "Undo"]

    def test_space_and_enter_press_it(self, browser_page, live) -> None:
        """A native <button>, so both keys arrive as a click, and focus stays
        on the toggle — a mode control does not move focus when pressed (the
        brush trigger, which opens a menu, is the one that does)."""
        _open(browser_page, live, live.store(GRID))
        _region_toggle(browser_page).focus()

        browser_page.keyboard.press("Space")
        assert _region_pressed(browser_page) == "true"
        assert browser_page.evaluate("document.activeElement.id") == "puzzle-player-region"

        browser_page.keyboard.press("Enter")
        assert _region_pressed(browser_page) == "false"
        assert browser_page.evaluate("document.activeElement.id") == "puzzle-player-region"

    def test_it_keeps_a_tap_target_and_the_toolbars_button_pattern_on_a_phone(self, browser, live) -> None:
        """CARD-182's tap-target rule as the rest of the player states it
        (>= 24 px square — TestSolverZoom_TapTargetsAreAtLeast24px; the
        panel's --control-h is 36 px, so no toolbar button reaches 44) and
        the card's "reuse .btn.btn-outline-secondary": the toggle is exactly
        as tall as Undo, so it cannot drift from the toolbar's own height."""
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            classes = _region_toggle(page).get_attribute("class").split()
            box = _region_toggle(page).bounding_box()
            undo = _button(page, "Undo").bounding_box()
        finally:
            context.close()
        assert {"btn", "btn-outline-secondary"} <= set(classes)
        assert box["width"] >= 24 and box["height"] >= 24, box
        assert round(box["height"]) == round(undo["height"])

    @pytest.mark.parametrize("width,height", [(1280, 720), (1440, 900), (390, 844)])
    @pytest.mark.parametrize("brush", ["Black", "Undecided"])
    def test_adding_it_leaves_the_tools_slot_at_its_old_width(self, browser, live, width, height, brush) -> None:
        """The toolbar's one measured constraint this card had to not break:
        ``.player-slot`` (the tools' box, which the solved banner takes over)
        is still exactly 13rem = 208 px wide — the width CARD-194 gave it —
        at every pinned viewport and for the narrowest and widest brush
        label alike.

        That is why admin.css moved the 13rem minimum off
        ``.player-tool-trigger`` onto ``.player-tools`` and gave the toggle
        the trigger's narrower side padding: leaving the minimum on the
        trigger made the group 13rem PLUS the toggle (~296 px measured),
        which pushed "Progress: N%" off the counters' row at 1280 px
        (TestSolverPercent_SitsNextToTheCounters::test_shares_the_buttons_row_at_1280,
        observed red), and sizing the toggle with the default button padding
        let the group grow past 13rem for the wider brush labels, nudging
        the board sideways when the brush changed. Mutant: restoring
        ``min-width: 13rem`` on .player-tool-trigger fails here at every
        width."""
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            if brush != "Black":
                _tool(page, brush)
            boxes = page.evaluate(
                """() => {
                  const w = (s) => document.querySelector(s).getBoundingClientRect().width;
                  return { slot: w('.player-slot'), tools: w('.player-tools') };
                }"""
            )
        finally:
            context.close()
        assert round(boxes["slot"]) == round(boxes["tools"]) == 208, (brush, width, boxes)


# ==========================================================================
# AC-3 / AC-4 — an armed drag marks and disarms; unarmed, touch scrolls
# ==========================================================================


@pytest.mark.browser
class TestSolverRegion_ArmedDragMarksThenDisarms:
    """CARD-211 AC-3 (and CARD-194 AC-7/AC-8, now driven from the toggle) —
    Region pressed, a drag along a row marks every cell of the drag with the
    current brush, and the toggle reads ``aria-pressed="false"`` again
    afterwards: Region is one-shot, exactly as CARD-194 shipped it.

    Mutant: dropping the ``setRegion(nextRegion(region, "drag"))`` call from
    solver.js's pointerup leaves ``aria-pressed="true"`` in all three tests
    here (and makes the mode sticky, which is a separate owner decision)."""

    def test_mouse_drag_with_black_marks_the_row_then_disarms(self, browser_page, live) -> None:
        """AC-3's own scenario: the default Black brush, Region pressed, a
        mouse drag along row 4 (index 3), columns 2 to 6 (indexes 1..5)."""
        _open(browser_page, live, live.store(GRID))
        _region(browser_page)
        assert _region_pressed(browser_page) == "true"

        _drag(browser_page, [(3, 1), (3, 5)])

        assert _marked(_states(browser_page)) == {(3, c): F for c in range(1, 6)}
        assert _region_pressed(browser_page) == "false"
        assert _trigger_text(browser_page) == "Black"  # the brush is untouched

    def test_touch_drag_with_region_marks_and_region_turns_off(self, browser, live) -> None:
        """CARD-194 AC-7 — White is picked, then Region pressed; the same
        real touch drag (CDP touch events) marks the five cells white, and
        afterwards the toggle is unpressed while White stays chosen."""
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            _tool(page, "White")
            _region(page)

            _touch_drag_row_1_cols_2_to_6(context, page)

            assert _marked(_states(page)) == {(1, c): E for c in range(2, 7)}
            assert _region_pressed(page) == "false"
            assert _trigger_text(page) == "White"
            _trigger(page).click()
            assert _menu_item(page, "White").get_attribute("aria-checked") == "true"
            page.keyboard.press("Escape")
        finally:
            context.close()

    def test_a_drag_that_changes_no_cell_still_disarms(self, browser_page, live) -> None:
        """CARD-194 target behaviour #7 — "a drag ended", not "a cell
        changed": Undecided dragged over already-undecided cells records a
        stroke that marks nothing, and Region still turns itself off."""
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Undecided")
        _region(browser_page)

        _drag(browser_page, [(6, 1), (6, 5)])

        assert _marked(_states(browser_page)) == {}
        assert _region_pressed(browser_page) == "false"


@pytest.mark.browser
class TestSolverRegion_UnarmedTouchDragStillScrolls:
    """CARD-211 AC-4 (CARD-194 AC-6, unchanged by this card) — Region not
    pressed is the default, and the same real touch drag marks nothing while
    leaving the browser free to scroll: no pointer event it fires is
    ``defaultPrevented``, and Chromium still recognises the gesture as a pan
    (``pointercancel`` fires, exactly as it already does for a cancelled
    gesture elsewhere —
    TestSolverClickFollowsTheBrush::test_a_cancelled_gesture_makes_the_next_tap_a_first_click
    in test_puzzle_solver_marking.py). The cells' ``touch-action`` is what
    makes that possible, and it is keyed to ``.player-board.is-region``,
    which since this card only the toggle sets (the computed values
    themselves are measured in test_puzzle_solver_phone.py)."""

    def test_touch_drag_without_region_scrolls_and_marks_nothing(self, browser, live) -> None:
        context = browser.new_context(has_touch=True, viewport={"width": 1024, "height": 768})
        page = context.new_page()
        try:
            _open(page, live, live.store(GRID))
            assert _region_pressed(page) == "false"
            assert page.evaluate("document.querySelectorAll('.player-board.is-region').length") == 0
            page.evaluate(
                "window.__events = []; "
                "for (const t of ['pointerdown', 'pointercancel']) "
                "document.addEventListener(t, (e) => window.__events.push([t, e.defaultPrevented]));"
            )

            _touch_drag_row_1_cols_2_to_6(context, page)

            assert _marked(_states(page)) == {}
            assert page.evaluate("window.__events") == [["pointerdown", False], ["pointercancel", False]]
            assert _region_pressed(page) == "false"  # nothing armed it
            assert _trigger_text(page) == "Black"
        finally:
            context.close()


# ==========================================================================
# AC-5 — the brush and Region do not overwrite each other
# ==========================================================================


@pytest.mark.browser
class TestSolverRegion_DoesNotChangeTheBrush:
    """CARD-211 AC-5 — the two controls are independent in the direction this
    card creates: pressing Region (and pressing it again) leaves the chosen
    brush exactly as it was, for every brush — in the trigger's visible text,
    in its ``aria-label`` and in which menu item is checked.

    The other direction is deliberately NOT independent: picking a brush
    still turns Region off, which is CARD-194 target behaviour #3 and is kept
    as shipped (TestSolverBrushMenu_Region::test_picking_a_brush_turns_region_off
    below). Making the two fully independent would change what the control
    does, which is an owner decision rather than this card's.

    Mutant: having the Region handler write ``tool`` — or having ``pick``
    still treat "region" as a name it may receive, as CARD-194's menu did —
    fails here."""

    @pytest.mark.parametrize("brush", ["Black", "White", "Maybe", "Undecided"])
    def test_pressing_and_releasing_region_keeps_the_brush(self, browser_page, live, brush) -> None:
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, brush)

        _region(browser_page)
        assert _region_pressed(browser_page) == "true"
        assert _trigger_text(browser_page) == brush
        assert _trigger(browser_page).get_attribute("aria-label") == f"Brush: {brush}"

        _region(browser_page)
        assert _region_pressed(browser_page) == "false"
        assert _trigger_text(browser_page) == brush
        assert _trigger(browser_page).get_attribute("aria-label") == f"Brush: {brush}"

        _trigger(browser_page).click()
        assert _menu_item(browser_page, brush).get_attribute("aria-checked") == "true"
        browser_page.keyboard.press("Escape")

    def test_the_armed_brush_is_the_one_a_region_drag_paints(self, browser_page, live) -> None:
        """The flip side of the label claim: arming Region does not quietly
        reset the brush to Black either — a region drag after picking Maybe
        paints "?"."""
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "Maybe")
        _region(browser_page)

        _drag(browser_page, [(3, 1), (3, 5)])

        assert _marked(_states(browser_page)) == {(3, c): M for c in range(1, 6)}


# ==========================================================================
# AC-6 — the toggle's state is announced, not re-labelled
# ==========================================================================


@pytest.mark.browser
class TestSolverRegion_AnnouncesItsState:
    """CARD-211 AC-6 — a screen reader learns Region's state from the
    player's existing live region (#puzzle-player-announce, role=status,
    aria-atomic), not from a label the user must go back and re-read: the
    brush trigger's accessible name never mentions Region, and CARD-194's
    ``Region · <brush>`` visible text is gone. The automatic disarm after a
    region drag is announced too — otherwise a user who cannot see the
    toggle would be left believing the mode is still armed.

    Mutant: dropping the ``announce.textContent`` write from solver.js's
    setRegion leaves the live region empty through all of this."""

    def test_pressing_and_unpressing_are_announced(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        assert _announced(browser_page) == ""

        _region(browser_page)
        assert _announced(browser_page) == "Region on: the next drag marks with the brush."

        _region(browser_page)
        assert _announced(browser_page) == "Region off."

    def test_the_live_region_is_the_players_existing_one(self, browser_page, live) -> None:
        """Not a second live region of its own: the announcement lands in
        #puzzle-player-announce, which is already role=status and present
        from the first paint (a region that only appears is not reliably
        read — see the template's comment block)."""
        _open(browser_page, live, live.store(GRID))
        _region(browser_page)

        assert browser_page.evaluate(
            """() => {
              const a = document.getElementById('puzzle-player-announce');
              const live = [...document.querySelectorAll(
                '#puzzle-player-controls [role=status], #puzzle-player-controls [aria-live]')];
              return { role: a.getAttribute('role'), atomic: a.getAttribute('aria-atomic'),
                       says: a.textContent.trim(), unnamed: live.filter((el) => el.id === '').length };
            }"""
        ) == {"role": "status", "atomic": "true",
              "says": "Region on: the next drag marks with the brush.", "unnamed": 0}

    def test_the_brush_label_never_mentions_region(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _region(browser_page)

        assert _trigger(browser_page).get_attribute("aria-label") == "Brush: Black"
        assert _trigger_text(browser_page) == "Black"
        assert "Region" not in _trigger(browser_page).text_content()

    def test_the_automatic_disarm_is_announced(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _region(browser_page)

        _drag(browser_page, [(3, 1), (3, 5)])

        assert _region_pressed(browser_page) == "false"
        assert _announced(browser_page) == "Region off."

    def test_a_drag_that_solves_the_board_announces_the_banner_instead(self, browser_page, live) -> None:
        """The two writers of the one live region, ordered: solver.js
        announces the disarm BEFORE committing the stroke, so when that
        stroke solves the board the solved banner — the more important of the
        two messages — is what the user is left hearing. (LONG_RUN is a run
        of two or more solution-filled cells on one row, so the two cells
        this drag fills both want Black.)"""
        row, first, _last_col = LONG_RUN
        _open(browser_page, live, live.store(GRID))
        cells = _solution_cells(GRID, E)
        cells[row * SIDE + first] = U
        cells[row * SIDE + first + 1] = U
        _set(browser_page, cells)
        assert not _is_solved_shown(browser_page)
        assert _announced(browser_page) == ""
        _region(browser_page)

        _drag(browser_page, [(row, first), (row, first + 1)])

        assert _is_solved_shown(browser_page)
        assert _region_pressed(browser_page) == "false"
        assert "Solved" in _announced(browser_page)
        assert _announced(browser_page) != "Region off."


# ==========================================================================
# CARD-194 AC-3 / AC-4 — the menu's own keyboard
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_Keyboard:
    """CARD-194 AC-3 / AC-4 — opening from the trigger, moving inside the
    menu, and leaving it by picking an item, Escape or Tab. CARD-211: the
    menu's last item is Undecided now, and Tab out of the menu lands on the
    Region toggle, the control that sits between the trigger and Undo."""

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

    def test_arrow_up_and_end_reach_undecided_the_last_item(self, browser_page, live) -> None:
        """CARD-211: with Region out of the menu, its last item is Undecided,
        so ArrowUp wrapping from the first item — and End — land there."""
        _open(browser_page, live, live.store(GRID))
        _trigger(browser_page).focus()
        browser_page.keyboard.press("ArrowDown")  # opens on Black, the checked item

        browser_page.keyboard.press("ArrowUp")  # wraps past the end
        assert browser_page.evaluate("document.activeElement.textContent.trim()") == "Undecided"
        browser_page.keyboard.press("Home")
        assert browser_page.evaluate("document.activeElement.textContent.trim()") == "Black"
        browser_page.keyboard.press("End")
        assert browser_page.evaluate("document.activeElement.textContent.trim()") == "Undecided"
        browser_page.keyboard.press("Escape")

    def test_escape_closes_and_tab_leaves(self, browser_page, live) -> None:
        """AC-4. CARD-211: Tab out of the menu reaches Region, and one more
        Tab reaches Undo — the order the toolbar's own Tab test pins
        (test_puzzle_solver_marking.py CONTROLS)."""
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
        assert browser_page.evaluate(_FOCUSED) == "Region"
        browser_page.keyboard.press("Tab")
        assert browser_page.evaluate(_FOCUSED) == "Undo"


# ==========================================================================
# CARD-194 AC-9 / AC-12 and target behaviour #3 — Region's other mechanics
# ==========================================================================


@pytest.mark.browser
class TestSolverBrushMenu_Region:
    """CARD-194 AC-9 / AC-12 and target behaviour #3, all still holding with
    the toggle in place of the menu item: a tap while Region is on, what a
    reload starts with, and a brush pick turning Region off."""

    def test_picking_a_brush_turns_region_off(self, browser_page, live) -> None:
        """Target behaviour #3 — Region on, then a brush picked from the menu
        with no drag involved: Region turns off immediately (distinct from
        #7's turn-off-after-a-drag, exercised by
        TestSolverRegion_ArmedDragMarksThenDisarms above). CARD-211 keeps
        this deliberately: before it, the menu's radio exclusivity forced it;
        now the "brush" transition of solver_state.js nextRegion does, and
        changing it would be an owner decision rather than this card's."""
        _open(browser_page, live, live.store(GRID))
        _region(browser_page)
        assert _region_pressed(browser_page) == "true"
        assert _trigger_text(browser_page) == "Black"  # no composite label any more

        _tool(browser_page, "White")

        assert _trigger_text(browser_page) == "White"
        assert _region_pressed(browser_page) == "false"
        assert _announced(browser_page) == "Region off."

    def test_re_picking_the_same_brush_also_turns_region_off(self, browser_page, live) -> None:
        """"Picking a brush" means any pick, including the brush already
        chosen — the same reading CARD-194's `lastClick` reset follows."""
        _open(browser_page, live, live.store(GRID))
        _region(browser_page)

        _tool(browser_page, "Black")

        assert _region_pressed(browser_page) == "false"
        assert _trigger_text(browser_page) == "Black"

    def test_a_tap_with_region_clicks_and_region_stays_on(self, browser_page, live) -> None:
        """AC-9 — Black (the default brush), Region on, a blank cell
        clicked once (a mouse click stands for a tap here — AC-7's real
        touch drag already exercises CDP touch input; this is Region's own
        "a non-drag input is a click" rule, independent of pointer type):
        the cell reads black and Region is still on, because only a *drag*
        is what disarms it."""
        _open(browser_page, live, live.store(GRID))
        _region(browser_page)

        _cell(browser_page, 9, 9).click()

        assert _marked(_states(browser_page)) == {(9, 9): F}
        assert _region_pressed(browser_page) == "true"
        assert _trigger_text(browser_page) == "Black"

    def test_reload_starts_with_black_and_region_off(self, browser_page, live) -> None:
        """AC-12 — a brush and Region were chosen, and a region drag was
        recorded (so there is history to reload too); after a reload the
        trigger reads "Brush: Black" and the toggle is unpressed, regardless
        of what was picked before (brush and Region are UI state, never
        saved — G-3)."""
        _open(browser_page, live, live.store(GRID))
        _tool(browser_page, "White")
        _region(browser_page)
        _drag(browser_page, [(2, 0), (2, 3)])
        assert _trigger_text(browser_page) == "White"  # Region turned off; White stayed
        _region(browser_page)  # armed again, so the reload has something to drop

        browser_page.reload()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert _trigger_text(browser_page) == "Black"
        assert _button(browser_page, "Brush: Black").count() == 1
        assert _region_pressed(browser_page) == "false"


# ==========================================================================
# The pure rules (ADR-0038/R4) — plain values, no DOM
# ==========================================================================


@pytest.mark.browser
class TestRegionRules_PureFunctions:
    """``solver_state.js``'s Region exports, exercised directly — the same
    module solver.js calls, with no page state involved. CARD-211 moved the
    flag's transition table and the "does this drag paint?" rule here from
    ``solver.js``, where CARD-194 had kept them inline; this is the same
    split the zoom arithmetic already follows
    (TestZoomArithmetic_PureFunctions in test_puzzle_solver_zoom.py). The
    truth table is written out by hand, never derived from the module."""

    def test_next_region_covers_every_event_from_both_states(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))

        result = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const attempt = (f) => { try { return { value: f() }; } catch (e) { return { error: e.name }; } };
              return {
                armFromOff: S.nextRegion(false, 'toggle'),
                disarmFromOn: S.nextRegion(true, 'toggle'),
                dragFromOn: S.nextRegion(true, 'drag'),
                dragFromOff: S.nextRegion(false, 'drag'),
                brushFromOn: S.nextRegion(true, 'brush'),
                brushFromOff: S.nextRegion(false, 'brush'),
                events: [...S.REGION_EVENTS],
                frozen: Object.isFrozen(S.REGION_EVENTS),
                badEvent: attempt(() => S.nextRegion(false, 'press')),
                emptyEvent: attempt(() => S.nextRegion(true, '')),
              };
            }"""
        )

        assert (result["armFromOff"], result["disarmFromOn"]) == (True, False)
        assert (result["dragFromOn"], result["dragFromOff"]) == (False, False)
        assert (result["brushFromOn"], result["brushFromOff"]) == (False, False)
        assert result["events"] == ["toggle", "drag", "brush"]
        assert result["frozen"] is True
        assert result["badEvent"] == {"error": "RangeError"}
        assert result["emptyEvent"] == {"error": "RangeError"}

    def test_gesture_paints_is_mouse_always_and_the_rest_only_when_armed(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))

        result = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const rows = {};
              for (const type of ['mouse', 'touch', 'pen', '']) {
                for (const armed of [false, true]) rows[type + ':' + armed] = S.gesturePaints(type, armed);
              }
              return rows;
            }"""
        )

        assert result == {
            "mouse:false": True, "mouse:true": True,
            "touch:false": False, "touch:true": True,
            "pen:false": False, "pen:true": True,
            ":false": False, ":true": True,
        }


# ==========================================================================
# Pen counts as touch (owner decision, CARD-194's Worktree notes — a pen drag
# needs Region exactly like a touch drag does)
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
    (solver.js pointerup's `done.paints` branch, whose rule is
    solver_state.js gesturePaints since CARD-211)."""

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
            _region(page)

            self._pen_drag(context, page, (1, 2), (1, 6))

            assert _marked(_states(page)) == {(1, c): E for c in range(2, 7)}
            assert _region_pressed(page) == "false"
            assert _trigger_text(page) == "White"
        finally:
            context.close()
