"""The player at three screens: one walk of every option per screen (owner's
review request of 2026-11-17).

The feature files beside this one pin each option where it was built, and most
of them at one screen: marking and the crosshair only on a desktop, the line
view only on phones. This file is the other axis and deliberately thin. It
drives the ASSEMBLED PUBLIC SITE (the admin's own player files, byte-identical
copies — ADR-0041/R3) at a desktop, a phone held upright and the same phone
turned, and asks of each the same short list: the brush menu, Region, panning
a zoomed board, zoom, the hint ladder, the probe, and the single-line view;
then the library, a book's landing and the lesson. Each walk also holds the
two properties no feature file can state for a page as a whole: nothing was
thrown, and the page itself never scrolls sideways.

It is a smoke walk, not a second specification: a claim about HOW an option
behaves belongs in that option's own file (owner's ruling of 2026-11-07,
fewer tests, verified once). Seven node ids: the two walks at three screens
one cell for two interrupted gestures, and one for a page whose
furniture above the board moves after the board is drawn.
"""

from __future__ import annotations

import pytest

from tests.test_player_shared_ui_site import (  # noqa: F401 - fixtures are used by name
    browser_page,
    browser_type,
    bundle,
    fragment,
    open_play,
    preview,
    preview_host,
)
from tests.test_public_player_pages import PAGE_GRIDS, PAGES_SETTLE_MS, _open_pages, driver  # noqa: F401

#: The three screens. The two phone shapes are the suite's own
#: (test_puzzle_solver_line.py PHONE / LANDSCAPE); ``touch`` decides both the
#: context and which input the walk uses.
SCREENS = {
    "desktop": ({"width": 1280, "height": 800}, False),
    "portrait": ({"width": 390, "height": 844}, True),
    "landscape": ({"width": 844, "height": 390}, True),
}

#: The fixture bundle's 24 x 24: big enough that a phone opens it at Fit, that
#: four zoom steps overflow the stage on every screen, and that the line view
#: is offered (solver.js LINE_MIN_SIDE).
BOARD = "h24"

#: Longer than solver.js REGION_HOLD_MS, the hold that sets Region's anchor.
HOLD_MS = 700

_PAGE_OVERFLOW = "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
_MARKED = "() => [...window.puzzlePlayer.getBoard().cells].filter((s) => s !== 'unknown').length"
_STAGE = """() => {
  const s = document.querySelector('.player-stage');
  return { x: s.scrollLeft, y: s.scrollTop,
           roomX: s.scrollWidth - s.clientWidth, roomY: s.scrollHeight - s.clientHeight };
}"""
#: Two points 60 px apart on a diagonal through the middle of the part of the
#: board the stage shows, so a drag between them starts and ends on cells.
#: The cell under the middle of the stage's visible box, as [row, col].
_CENTRE_CELL = """() => {
  const s = document.querySelector('.player-stage').getBoundingClientRect();
  const cell = document.elementFromPoint(s.left + s.width / 2, s.top + s.height / 2)?.closest('td.player-cell');
  return cell ? [Number(cell.dataset.row), Number(cell.dataset.col)] : null;
}"""
_DRAWN = "() => [...document.querySelectorAll('td.player-cell')].filter((c) => c.dataset.state !== 'unknown').length"
_PAN_POINTS = """() => {
  const s = document.querySelector('.player-stage').getBoundingClientRect();
  const cells = [...document.querySelectorAll('td.player-cell')].map((c) => c.getBoundingClientRect());
  const left = Math.max(s.left, Math.min(...cells.map((c) => c.left)));
  const top = Math.max(s.top, Math.min(...cells.map((c) => c.top)));
  const right = Math.min(s.right, innerWidth, Math.max(...cells.map((c) => c.right)));
  const bottom = Math.min(s.bottom, innerHeight, Math.max(...cells.map((c) => c.bottom)));
  const x = (left + right) / 2, y = (top + bottom) / 2;
  return [{ x: x + 30, y: y + 30 }, { x: x - 30, y: y - 30 }];
}"""


def _cell(page, row, col):
    return page.locator(f'td.player-cell[data-row="{row}"][data-col="{col}"]')


def _centre(locator):
    box = locator.bounding_box()
    return {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}


def _touch_drag(context, page, start, end, hold_ms: int = 0) -> None:
    cdp = context.new_cdp_session(page)

    def send(kind, points=()):
        cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": list(points)})

    send("touchStart", [start])
    page.wait_for_timeout(hold_ms)
    for step in range(1, 13):
        send("touchMove", [{"x": start["x"] + (end["x"] - start["x"]) * step / 12,
                            "y": start["y"] + (end["y"] - start["y"]) * step / 12}])
        # Short: an unheld drag has to leave its first cell well inside
        # solver.js's hold (REGION_HOLD_MS), or a loaded runner turns it into
        # the anchor-setting press it is being told apart from.
        page.wait_for_timeout(10)
    page.wait_for_timeout(100)
    send("touchEnd")


@pytest.fixture(params=list(SCREENS))
def screen(request, browser_page):  # noqa: F811
    """A page at one of the three screens, with everything it throws kept."""
    viewport, touch = SCREENS[request.param]
    context = browser_page.context.browser.new_context(
        viewport=viewport, has_touch=touch, is_mobile=touch)
    page = context.new_page()
    page.set_default_timeout(PAGES_SETTLE_MS)
    thrown: list[str] = []
    page.on("pageerror", lambda error: thrown.append(str(error)))
    page.on("console", lambda m: thrown.append(m.text) if m.type == "error" else None)
    yield request.param, context, page, touch, thrown
    context.close()


@pytest.mark.browser
def test_every_option_of_the_player_works_at_this_screen(screen, preview_host) -> None:
    name, context, page, touch, thrown = screen
    url, _report, keys, _slug = preview_host
    open_play(page, url, keys[BOARD])
    press = (lambda locator: locator.tap()) if touch else (lambda locator: locator.click())
    region = page.locator("[data-player-region]")
    readout = page.locator("[data-player-zoom-readout]")
    opened_at = readout.text_content()
    assert page.evaluate(_PAGE_OVERFLOW) <= 0

    # ---- the brush menu: a pick is what the next press paints -------------
    press(page.locator("#puzzle-player-tool-trigger"))
    press(page.get_by_role("menuitemradio", name="White", exact=True))
    press(_cell(page, 0, 0))
    assert _cell(page, 0, 0).get_attribute("data-state") == "empty"
    press(page.locator("#puzzle-player-tool-trigger"))
    press(page.get_by_role("menuitemradio", name="Black", exact=True))

    # ---- Region: one drag paints the run (a finger needs it armed) --------
    if region.get_attribute("aria-pressed") != "true":
        press(region)
    start, end = _centre(_cell(page, 2, 1)), _centre(_cell(page, 2, 5))

    def drag(hold_ms=0):
        if touch:
            _touch_drag(context, page, start, end, hold_ms)
        else:
            page.mouse.move(start["x"], start["y"])
            page.mouse.down()
            page.wait_for_timeout(hold_ms)
            page.mouse.move(end["x"], end["y"], steps=8)
            page.mouse.up()

    # A press HELD first sets Region's anchor and marks nothing — and draws
    # nothing either (review of 2026-11-17: the drag after the hold left a
    # painted run on the board that no undo could reach).
    drawn = page.evaluate(_DRAWN)
    drag(hold_ms=HOLD_MS)
    assert page.evaluate(_DRAWN) == drawn == page.evaluate(_MARKED)
    page.keyboard.press("Escape")  # drops the anchor
    drag()
    assert [_cell(page, 2, c).get_attribute("data-state") for c in range(1, 6)] == ["filled"] * 5

    # ---- zoom: the cells grow, the stage scrolls, the page does not -------
    before = _cell(page, 0, 0).bounding_box()["width"]
    for _ in range(4):
        press(page.locator('[data-player-zoom-action="in"]'))
    assert readout.text_content() != opened_at
    assert _cell(page, 0, 0).bounding_box()["width"] > before * 1.5
    stage = page.evaluate(_STAGE)
    assert stage["roomX"] > 0 or stage["roomY"] > 0, stage
    assert page.evaluate(_PAGE_OVERFLOW) <= 0
    # a board that left view disarms Region, so a finger can pan again
    assert region.get_attribute("aria-pressed") == "false"
    # ... and a zoom keeps the cell at the middle of the view where it was
    # (review of 2026-11-17: the clue band does not scale with the cells, and
    # scaling the whole scroll by the zoom ratio slid the board a cell a step).
    page.evaluate("""() => {
      const s = document.querySelector('.player-stage');
      s.scrollLeft = (s.scrollWidth - s.clientWidth) * 0.6;
      s.scrollTop = (s.scrollHeight - s.clientHeight) * 0.6;
    }""")
    middle = page.evaluate(_CENTRE_CELL)
    assert middle is not None
    for _ in range(2):
        press(page.locator('[data-player-zoom-action="in"]'))
        assert page.evaluate(_CENTRE_CELL) == middle
    stage = page.evaluate(_STAGE)

    # ---- scroll: a finger (or the wheel) pans the board and marks nothing -
    marked = page.evaluate(_MARKED)
    if touch:
        a, z = page.evaluate(_PAN_POINTS)
        _touch_drag(context, page, a, z)
        page.wait_for_timeout(300)
    else:
        page.locator(".player-stage").hover()
        page.mouse.wheel(120, 120)
        page.wait_for_timeout(300)
    panned = page.evaluate(_STAGE)
    assert (panned["x"], panned["y"]) != (stage["x"], stage["y"]), (stage, panned)
    assert page.evaluate(_MARKED) == marked

    for _ in range(8):
        out = page.locator('[data-player-zoom-action="out"]')
        if out.get_attribute("aria-disabled") == "true":
            break
        press(out)
    assert readout.text_content() == opened_at

    # ---- the hint ladder: line, reason, then one revealed cell ------------
    hint = page.locator('[data-player-action="hint"]')
    said = []
    for _ in range(3):
        press(hint)
        said.append(page.locator("#puzzle-player-explain").text_content().strip())
    assert len(set(said)) == 3 and all(said), said
    assert page.locator("[data-player-hints]").text_content().strip() == "1"
    assert page.evaluate(_MARKED) == marked + 1
    assert page.locator(".player-stage .is-hinted").count() == 1
    # ... and the answer box does not sit on the cell it names (review of
    # 2026-11-17: the reveal kept the edge the rung before it had chosen).
    assert not page.evaluate("""() => {
      const a = document.querySelector('.is-hinted').getBoundingClientRect();
      const b = document.getElementById('puzzle-player-explain').getBoundingClientRect();
      return !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
    }""")
    page.keyboard.press("Escape")

    # ---- the probe: a guess that is taken back leaves no mark -------------
    probe = page.locator("[data-player-probe]")
    press(probe)
    assert probe.get_attribute("aria-pressed") == "true"
    marked = page.evaluate(_MARKED)
    press(_cell(page, 23, 23))
    assert page.evaluate(_MARKED) == marked + 1
    press(page.locator('[data-player-probe-action="abandon"]'))
    assert page.evaluate(_MARKED) == marked
    assert probe.get_attribute("aria-pressed") == "false"

    # ---- the single-line view: a phone's, and it marks the real board -----
    line_open = page.locator("[data-player-line-open]")
    if touch:
        press(line_open)
        page.wait_for_function("!document.getElementById('puzzle-player-line').hidden")
        assert page.locator("[data-player-line-title]").text_content().startswith("Row ")
        press(page.locator('.player-line-cell[data-index="9"]'))
        assert page.evaluate(_MARKED) == marked + 1
        assert page.evaluate(_PAGE_OVERFLOW) <= 0
        # The view is modal: Tab never reaches the toolbar it covers, and
        # Escape closes it even with the focus on nothing (review of
        # 2026-11-17: Tab reached Reset under the view; a tap on the mini
        # board left Escape dead).
        for key in ["Tab"] * 20 + ["Shift+Tab"] * 3:
            page.keyboard.press(key)
            assert page.evaluate("() => document.activeElement.closest('#puzzle-player-line') !== null")
        press(page.locator("[data-player-line-mini]"))
        page.keyboard.press("Escape")
        assert page.locator("#puzzle-player-line").is_hidden()
        assert page.evaluate("() => document.activeElement.matches('[data-player-line-open]')")
    else:
        assert not line_open.is_visible()

    # ---- Reset asks first, and its two answers are readable --------------
    # (review of 2026-11-17: the landscape strip's square-button rule drew
    # "Reset board" / "Keep marks" as 44 px squares with the words outside.)
    press(page.locator('[data-player-action="reset"]'))
    answers = page.locator("#puzzle-player-confirm [data-player-confirm]")
    assert answers.count() == 2
    clipped = answers.evaluate_all(
        "(buttons) => buttons.filter((b) => b.scrollWidth > b.clientWidth"
        " || b.scrollHeight > b.clientHeight).map((b) => b.textContent.trim())")
    assert clipped == [], f"{name}: the words do not fit their buttons: {clipped}"
    # Escape answers "keep" wherever the focus has gone (it used to need the
    # focus inside the question) — one layer per press: with the brush menu
    # opened over the question, the first Escape closes only the menu.
    page.locator("#puzzle-player-tool-trigger").focus()
    page.keyboard.press("Enter")
    assert page.locator("#puzzle-player-tool-menu").is_visible()
    page.keyboard.press("Escape")
    assert page.locator("#puzzle-player-tool-menu").is_hidden()
    assert page.locator("#puzzle-player-confirm").is_visible()
    page.keyboard.press("Escape")
    assert page.locator("#puzzle-player-confirm").is_hidden()
    assert page.evaluate(_MARKED) > 0

    assert page.evaluate(_PAGE_OVERFLOW) <= 0
    assert thrown == [], f"{name}: {thrown}"


@pytest.mark.browser
def test_the_library_a_book_and_the_lesson_work_at_this_screen(screen, preview_host) -> None:
    name, _context, page, touch, thrown = screen
    url, _report, keys, slug = preview_host
    press = (lambda locator: locator.tap()) if touch else (lambda locator: locator.click())

    # ---- the library lists every puzzle and fits the screen ---------------
    _open_pages(page, url, "/library")
    assert page.locator(".tile").count() == len(keys)
    assert page.evaluate(_PAGE_OVERFLOW) <= 0
    # A filter, a puzzle, and Back: the list is still the filtered one
    # (review of 2026-11-17: the browser restored the select over an
    # unfiltered list).
    page.select_option('[data-pages-filter="tier"]', "hard")
    hard = page.locator(".tile").count()
    assert 0 < hard < len(keys)
    press(page.locator(".tile").first)
    page.wait_for_function("() => window.puzzlePlayer !== undefined")
    page.go_back()
    page.wait_for_function("() => window.playerPages !== undefined")
    assert page.input_value('[data-pages-filter="tier"]') == page.evaluate("window.playerPages.getFilters().tier")
    assert page.locator(".tile").count() == (hard if page.input_value('[data-pages-filter="tier"]') == "hard" else len(keys))

    # ---- the book: its squares, one opens its puzzle, the way back works --
    _open_pages(page, url, f"/b/{slug}")
    squares = page.locator(".tile.square")
    assert squares.count() > 0
    assert page.evaluate(_PAGE_OVERFLOW) <= 0
    press(squares.first)
    page.wait_for_function("() => window.puzzlePlayer !== undefined")
    assert page.evaluate(_PAGE_OVERFLOW) <= 0
    press(page.locator("[data-player-book]"))
    page.wait_for_url(f"**/b/{slug}")

    # ---- the lesson, opened from one of the book's puzzles: every step is
    # reachable and fits, and the way back is the BOOK (review of
    # 2026-11-17: it was the library, and the book's look was lost) ---------
    press(page.locator(".tile.square").first)
    page.wait_for_function("() => window.puzzlePlayer !== undefined")
    press(page.locator(".player-howto summary"))
    press(page.locator("[data-player-lesson]"))
    page.wait_for_function("() => window.howToSolve !== undefined")
    assert page.evaluate("window.howToSolve.home") == f"/b/{slug}"
    steps = page.locator("[data-hts-goto]").count()
    assert steps == page.locator("[data-hts-step]").count() > 1
    for n in range(1, steps + 1):
        if n > 1:
            press(page.locator("[data-hts-next]"))
        page.wait_for_function(f"() => window.howToSolve.getStep() === {n}")
        shown = page.evaluate(
            "() => [...document.querySelectorAll('[data-hts-step]')]"
            ".filter((s) => !s.hidden).map((s) => Number(s.dataset.htsStep))")
        assert shown == [n]
        assert page.evaluate(_PAGE_OVERFLOW) <= 0, f"{name}: step {n} scrolls the page sideways"
    assert page.locator("[data-hts-next]").is_hidden()

    # A square pressed from the keyboard keeps the focus (the redraw used to
    # drop it to the top of the page).
    page.evaluate("() => { window.location.hash = String("
                  "document.querySelector('[data-hts-try-board]').closest('[data-hts-step]').dataset.htsStep); }")
    square = page.locator('[data-hts-try-board] .hts-cell[data-row="2"][data-column="0"]')
    square.focus()
    page.keyboard.press("Enter")
    assert page.evaluate("() => document.activeElement.matches("
                         "'[data-hts-try-board] .hts-cell[data-row=\"2\"][data-column=\"0\"]')")
    assert square.get_attribute("data-state") == "filled"

    # ---- a library that cannot load shows its message and no dead filters -
    assert thrown == [], f"{name}: {thrown}"
    page.route("**/index.json", lambda route: route.fulfill(status=500, body="no"))
    page.goto(f"{url}/library")
    page.wait_for_function("() => !document.querySelector('[data-pages-notfound]').hidden")
    assert page.locator("[data-pages-filters]").is_hidden()


@pytest.mark.browser
def test_an_interrupted_gesture_leaves_the_board_usable(browser_page, preview_host) -> None:  # noqa: F811
    """Two interruptions the review of 2026-11-17 measured losing the
    reader's work, each driven the way it happened.

    * The phone is TURNED with a finger resting on the board and Region off.
      The redraw replaces the table, the finger's release lands outside the
      stage, and the stale touch made every later tap a pinch's second
      finger: no tap marked anything until a reload.
    * Ctrl+Z in the middle of a drag along a line-view strip took back an
      EARLIER stroke, and the drag's own record then dropped the redo stack,
      so that stroke was gone for good. The board's own drag always ignored
      the key; the strip's now does too.
    """
    url, _report, keys, _slug = preview_host
    browser = browser_page.context.browser

    phone = browser.new_context(viewport=SCREENS["portrait"][0], has_touch=True, is_mobile=True)
    try:
        page = phone.new_page()
        page.set_default_timeout(PAGES_SETTLE_MS)
        open_play(page, url, keys[BOARD])
        region = page.locator("[data-player-region]")
        if region.get_attribute("aria-pressed") == "true":
            region.tap()
        cdp = phone.new_cdp_session(page)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [_centre(_cell(page, 3, 3))]})
        page.wait_for_timeout(100)
        page.set_viewport_size(SCREENS["landscape"][0])
        page.wait_for_timeout(500)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(200)
        marked = page.evaluate(_MARKED)
        for row, col in ((1, 1), (2, 2), (5, 5)):
            _cell(page, row, col).tap()
        assert page.evaluate(_MARKED) == marked + 3
    finally:
        phone.close()

    narrow = browser.new_context(viewport={"width": 560, "height": 800})
    try:
        page = narrow.new_page()
        page.set_default_timeout(PAGES_SETTLE_MS)
        open_play(page, url, keys[BOARD])
        _cell(page, 4, 7).click()
        _cell(page, 9, 9).click()
        page.locator("[data-player-line-open]").click()
        page.wait_for_function("!document.getElementById('puzzle-player-line').hidden")
        start = _centre(page.locator('.player-line-cell[data-index="1"]'))
        end = _centre(page.locator('.player-line-cell[data-index="4"]'))
        page.mouse.move(start["x"], start["y"])
        page.mouse.down()
        page.mouse.move(end["x"], end["y"], steps=5)
        page.keyboard.press("Control+z")
        page.mouse.up()
        assert _cell(page, 9, 9).get_attribute("data-state") == "filled"
        assert _cell(page, 4, 7).get_attribute("data-state") == "filled"
        assert page.evaluate(_MARKED) == 2 + 4
    finally:
        narrow.close()


_FIT = """() => {
  const stage = document.querySelector('.player-stage');
  return { said: getComputedStyle(stage).getPropertyValue('--player-stage-top').trim(),
           top: Math.round(stage.getBoundingClientRect().top + window.scrollY) + 'px',
           cell: document.querySelector('td.player-cell').getBoundingClientRect().width };
}"""


@pytest.mark.browser
def test_the_board_is_fitted_again_when_what_stands_above_it_moves(browser_page, preview_host) -> None:  # noqa: F811
    """Review of 2026-11-17. The stage's top is measured when the toolbar or
    the header changes size — but something above the stage can move it
    without resizing either. Measured on the public site with a themed
    book's decoration sheet arriving after the first draw: the recorded top
    stayed thousands of pixels out, the board was drawn into the stage's
    5rem floor, and only a window resize put it right.

    Driven here with no theme at all, so the cell does not depend on which
    books decorate: a tall block is put above the header before the board is
    drawn and taken away after. The board must end exactly as it is on a
    page that never had the block."""
    url, _report, keys, _slug = preview_host
    context = browser_page.context.browser.new_context(
        viewport=SCREENS["portrait"][0], has_touch=True, is_mobile=True)
    try:
        page = context.new_page()
        page.set_default_timeout(PAGES_SETTLE_MS)
        open_play(page, url, keys["n30"])
        page.wait_for_timeout(300)
        plain = page.evaluate(_FIT)
        assert plain["said"] == plain["top"]

        page.add_init_script("""document.addEventListener('DOMContentLoaded', () => {
          const block = document.createElement('div');
          block.id = 'late-furniture';
          block.style.height = '6000px';
          document.body.prepend(block);
        });""")
        open_play(page, url, keys["n30"])
        page.wait_for_timeout(300)
        squeezed = page.evaluate(_FIT)
        assert squeezed["cell"] < plain["cell"] / 2, (squeezed, plain)  # the block really cost the board its room
        page.evaluate("() => document.getElementById('late-furniture').remove()")
        page.wait_for_timeout(500)
        after = page.evaluate(_FIT)
        assert after["said"] == after["top"] == plain["top"], (after, plain)
        assert abs(after["cell"] - plain["cell"]) < 0.01, (after, plain)

        # The other thing a redraw must not lose (same review): "Show grid" on
        # a solved board. The class sat on the table a redraw replaces, so a
        # turned phone took the grid away while the button still said pressed.
        page.evaluate("""async (grid) => {
          const state = await import('/solver_state.js');
          window.puzzlePlayer.setBoard(state.boardOfGrid(grid));
        }""", PAGE_GRIDS["n30"])
        show = page.locator("[data-player-show-grid]")
        show.tap()
        shown = "() => document.querySelector('.player-board').classList.contains('is-showing-grid')"
        assert page.evaluate(shown) and show.get_attribute("aria-pressed") == "true"
        # Wait for the redraw itself (a new table), not for a time: a late
        # redraw would otherwise let this pass on the table that was never
        # replaced.
        page.evaluate("() => { document.querySelector('.player-board').dataset.before = 'turn'; }")
        page.set_viewport_size(SCREENS["landscape"][0])
        page.wait_for_function("() => document.querySelector('.player-board').dataset.before === undefined")
        assert page.evaluate(shown) and show.get_attribute("aria-pressed") == "true"
    finally:
        context.close()
