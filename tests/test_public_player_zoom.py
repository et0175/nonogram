"""CARD-324 — the public player's zoom: four shared functions it already served.

The public page at ``/play/<key>`` **served** the zoom arithmetic and called
none of it. ``solver_state.js`` — the module ADR-0041/R3 makes the two players
share byte-for-byte — exports ``ZOOM_MIN``, ``ZOOM_MAX``, ``ZOOM_STEP``,
``clampZoom``, ``stepZoom``, ``pinchZoom`` and ``anchoredScroll``; the copy
``player/assemble.py`` writes into the site carries all seven, and before this
card ``player/play.js`` imported not one of them and ``player/player.css`` had
no zoom rule at all. So this is duplication-shaped debt rather than a new
feature: the behaviour was already there, and only the glue was missing.

The case that makes it matter is a board at :data:`nonogram.limits.MAX_SIZE` on
a 390 px screen. Thirty cells do not fit a phone at a tappable size — that is
``player.css``'s own accepted trade-off — so a 30-cell puzzle is **read by
zooming**, and every browser test below is taken at 390x844 for that reason.

Where each claim is answered, and why there
-------------------------------------------
Two tiers, following ``tests/test_public_player.py``'s own split:

* **tree tests** read ``player/`` and ``src/nonogram/admin/static/`` off disk.
  "no bound, step or clamp is re-implemented in ``play.js``" is a statement
  about *source text*, and a browser adds nothing to it;
* **browser tests** (``@pytest.mark.browser``) own everything a real engine
  has to answer: the readout, the rendered cell size, the stage's scroll
  position, a two-finger pinch and what leaves the page. They refuse
  **LOUDLY** when Chromium is absent (ADR-0038/R8) because they take
  CARD-160's own ``browser_page`` / ``browser_type`` fixtures, imported below
  rather than rewritten — those call ``pytest.fail``, never ``skip``.

The harness is imported, not rebuilt
------------------------------------
``bundle`` / ``site`` / ``host`` and the ``_open`` / ``_tap`` / ``_state`` /
``_cell_centre`` helpers come from ``tests/test_public_player.py`` by name.
That is the pattern ``tests/test_public_player_maybe.py`` set for this family
of cards and states in its own header: one module per card, importing the
assembled-site harness rather than standing up a second server, so the site
under test is the site every other public-player test measures.

**Not one expected zoom figure is written down here.** Every percent, every
bound, every step and every anchored scroll position is read from the served
``/solver_state.js`` inside the page under test and compared to what the page
did. That is the whole point of the card: a test carrying ``125`` would pass
just as well against a second copy of the arithmetic in ``play.js``, which is
the defect this card exists to remove. The one number this file does write is
the floor on its own corpus size (:data:`SWEEP_CASES`), which is a statement
about the test and not about the feature.

No ``hypothesis`` (not in the dependency baseline): the EC's sweep is a seeded
``random.Random`` corpus over the whole range, and it asserts its own minimum
case count so it cannot silently shrink to nothing.

The pinch/drag collision, which is the card's real interaction work
-------------------------------------------------------------------
Two pointers on the stage is a pinch — and by the time the second lands, the
first has **already** begun a single-pointer gesture, because ``play.js`` sets
``gesture`` at ``pointerdown``. What happens to that stroke is a decision, and
``play.js``'s ``beginPinch`` records it: the stroke is **abandoned**. Its
preview reverts to the recorded board, ``gesture`` is cleared so the first
finger's own later ``pointerup`` commits nothing — not the drag, and not even
the single-cell **click** it would otherwise have been — and ``pinch`` then
swallows the ``pointerup``/``pointercancel`` of both its pointers.

That last clause is the sharp one, and
:class:`TestPublicZoom_APinchZoomsAndPaintsNothing` has an arm for it with
Region **off**, where a touch gesture paints nothing anyway and so the only
thing a pinch could leave behind is a tap on the cell the first finger went
down on. That is the cell AC-5 names by word.

ADR-0041/R2 — what this module establishes, derived rather than quoted
----------------------------------------------------------------------
No public asset may carry a solution grid or any data from which a solution
cell is recoverable. This card is unusually safe on that axis **by signature**:
every function it consumes takes numbers only — ``stepZoom(current,
direction)``, ``pinchZoom(startZoom, startDistance, currentDistance)``,
``anchoredScroll(scroll, anchor, oldZoom, newZoom)`` — so none can carry a
board, a payload or a solution cell, and that is asserted here rather than
asserted in prose: :class:`TestPublicZoom_TheArithmeticIsTheModules` reads each
one's parameter list out of ``solver_state.js`` and holds it to a closed set of
scalar names.

The glue is where a leak would enter, so the glue is measured too: the zoom
writes **one** attribute pair on the page (the two buttons' ``aria-disabled``)
and one text node (the readout), it is the only thing that writes
``--player-zoom``, and it writes no cell's ``data-state`` at all. The *whole*
of R2 over the served tree stays where it already is —
``tests/test_public_player.py::test_served_tree_is_clean_of_answers`` and
``::test_the_page_carries_no_answer_and_no_third_party_asset`` — which run over
this card's tree unchanged; a second copy of that sweep here would be a second
copy of a guard, not a second guard.

Tests, by node id (FR-045, CARD-324's ACs)
------------------------------------------
Written out in full, path and name on one line each, for the reason
``tests/test_public_player.py``'s own table gives: the architecture validator
resolves a check ref by a TEXT search for the whole ``path::name`` string, so a
ref wrapped across two lines reads as dead however green the test is.

* AC-1 — ``tests/test_public_player_zoom.py::TestPublicZoom_TheControlsChangeTheZoom``
* AC-2 — ``tests/test_public_player_zoom.py::TestPublicZoom_TheBoundsComeFromTheModule``
* AC-3 — ``tests/test_public_player_zoom.py::TestPublicZoom_ZoomRecordsNoStroke``
* AC-4 — ``tests/test_public_player_zoom.py::TestPublicZoom_TheAnchoredScrollIsTheModules``
* AC-5 — ``tests/test_public_player_zoom.py::TestPublicZoom_APinchZoomsAndPaintsNothing``
* AC-6 — ``tests/test_public_player_zoom.py::TestPublicZoom_NoRequestPerZoom``
* EC(ADR-0041/R3) — ``tests/test_public_player_zoom.py::TestPublicZoom_TheArithmeticIsTheModules``

One class answers no AC, and the reason it exists is worth reading
-------------------------------------------------------------------
:class:`TestPublicZoom_AZoomedGutterNeverCoversTheBoard` was written after the
feature was, because **the renders caught what the tests did not**. Every
assertion above was green on a build in which, at 390 px and 300%, the sticky
row clue gutter was wider than the whole stage: the percent was right, the
cells really were three times bigger, the scroll was anchored, nothing
painted — and a player who zoomed in on the 30-cell board could reach no cell
at all, because the pinned gutter covered every column. That is the exact case
the card exists for, and it was invisible to six ACs.

``play.js``'s ``keepCluesInView`` is the fix: a gutter is pinned only while
the stage still has room beside it for TWO whole cells. The threshold is
derived from the board, not chosen: a window of width ``w`` over cells of pitch
``c`` holds a whole cell at every scroll offset exactly when ``w >= 2c``. What is deliberately **not** taken is
``solver.js``'s own richer rule (``keepCluesInView`` there,
``STICK_MAX_SHARE = 0.4``): applied at 390 px it would unpin this page's row
gutter at 100% as well, contradicting ``player.css``'s stated promise and the
reading
``tests/test_public_player.py::test_phone_viewport_is_playable`` makes of it.
Which rule the public page should take is an **owner decision**, routed rather
than made here; the narrow rule changes nothing below the zoom at which the
board stops being reachable. The bound's measured residue (ADR-0039/R3), on
this module's own harness and ``GRIDS["max"]`` (a stage client width of 358 px
at 390 px; row gutter 173/215/257/299/341 px and cell 29/36/43/50/57 px at
100/125/150/175/200%): at 390x844 the row gutter is pinned through 150% and
lets go at **175%**, the column gutter never lets go; at 844x390 the column
gutter is pinned at 100% and lets go from **125%**; at 1440 px nothing lets go
at any of nine rungs.

**The rule's first spelling asked for one cell and the 175% rung is why it asks
for two.** With one cell, at 175% on a 390 px phone the rule was met by 60 px
of band beside a 299 px gutter with a 50 px cell: one column, and at the
scroll the zoom itself lands on, zero whole cells in view (cycle 1's renders
08 and 09). That was a defect and not a residue, because the owner meets that
rung by thumb on exactly that phone, and the fix is one derived factor. What
stays declared after it: when a gutter is *unpinned* the board is reachable
only by scrolling it back into view (at 390 px from 175%, the row clues scroll
off the left edge), which is the trade the rule makes against a board nobody
can reach; and ``play.js`` reads the stage's height as the part visible with
the page at its top (the toolbar wraps on a phone, so the stage is 708 px tall
with its bottom at 943 against an 844 px fold), which understates the band
once the page itself is scrolled down.

The rule is re-run on ``resize``, because the geometry it reads is the
viewport's. Before that, zooming to 250% at 390x844 and rotating left both
classes holding the portrait answer (rows False / columns True where the
landscape geometry wants True / False) with no whole cell reachable until a
zoom button was pressed; ``test_rotating_a_zoomed_phone_re_asks_the_rule`` holds
it.

Two divergences from the admin player, both deliberate and both recorded
------------------------------------------------------------------------
#. **the keyboard**: the admin's zoom buttons carry no ``aria-keyshortcuts``
   and ``solver.js`` binds no key for zoom. This page matches that, and
   :meth:`TestPublicZoom_TheArithmeticIsTheModules.test_neither_page_invents_a_zoom_key_binding`
   holds **both** pages to it, so the match cannot rot into a divergence from
   either side;
#. **``touch-action``**: ``admin.css`` gives its cells ``pan-x pan-y``
   specifically so the compositor cannot claim a two-finger touch as the
   browser's own page pinch-zoom before any JS runs. This page's cells are
   ``touch-action: auto``, pinned there by
   ``tests/test_public_player.py::test_the_brush_region_and_touch_bindings_are_the_modules``
   and consistent with ``play.html``'s recorded decision to leave the
   browser's own pinch on ("the board's own two-finger pinch is not a
   substitute for the browser's"). The consequence is real and is a **routed
   finding, not a silence**: on a real phone the native pinch may preempt the
   board's. It is asserted as the current state rather than left unsaid, by
   :meth:`TestPublicZoom_TheArithmeticIsTheModules.test_the_cells_touch_action_diverges_from_the_admins_and_is_a_routed_finding`,
   so the day an owner decision changes it, that test is where the change is
   declared. What does **not** depend on it is the half AC-5 is about: a pinch
   not painting is pure JS bookkeeping and holds whatever the compositor does
   with the gesture.
"""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

import pytest

from nonogram.limits import MAX_SIZE
from tests.test_public_player import (  # noqa: F401 — fixtures used by name
    GRIDS,
    PLAYER_DIR,
    REPO_ROOT,
    _cell_centre,
    _open,
    _state,
    _tap,
    browser_page,
    browser_type,
    bundle,
    host,
    site,
)

ADMIN_STATIC = REPO_ROOT / "src" / "nonogram" / "admin" / "static"
STATE_MODULE = ADMIN_STATIC / "solver_state.js"
ADMIN_SCRIPT = ADMIN_STATIC / "solver.js"
ADMIN_CSS = ADMIN_STATIC / "admin.css"
ADMIN_TEMPLATE = REPO_ROOT / "src" / "nonogram" / "admin" / "templates" / "puzzle_solve.html"
PUBLIC_SCRIPT = PLAYER_DIR / "play.js"
PUBLIC_PAGE = PLAYER_DIR / "play.html"
PUBLIC_CSS = PLAYER_DIR / "player.css"

#: The phone this feature exists for. ``player.css``'s own header names it.
PHONE = {"width": 390, "height": 844}

#: The same phone turned on its side. It is in the gutter sweep because the
#: column gutter never lets go at :data:`PHONE` (cycle 1 of this card's review:
#: with ``keepsCols`` True at every rung, "the class equals the geometry" was
#: ``True == True`` on that axis, and a column predicate reading the wrong
#: dimension survived), and it is the viewport a rotation lands in.
LANDSCAPE = {"width": 844, "height": 390}

#: How long a dispatched touch stream is given to be DELIVERED before the
#: zoom it asked for is read, in ms.
#:
#: Not a guess and not politeness: Chromium coalesces touchmove delivery to
#: its own rendering rate, so a reading taken the instant after the dispatch
#: returns the PREVIOUS move's value. Measured on this page — a two-finger
#: spread read immediately after its own touchMove still answered ZOOM_MIN,
#: and answered correctly one event later. ``tests/test_puzzle_solver_zoom.py``
#: waits for the same reason on the admin side and says so.
SETTLE_MS = 300

#: The floor on the EC sweep's corpus, asserted inside the test so the corpus
#: cannot silently shrink. It is a statement about the test, not the feature —
#: the only written-down number in this file.
SWEEP_CASES = 60


# --------------------------------------------------------------------------
# Reading the module, in the page that serves it
# --------------------------------------------------------------------------


def _module(page, expression: str, argument=None):
    """``expression`` evaluated with the served ``/solver_state.js`` bound to ``S``.

    Every expected value in this file goes through here. The import is the
    page's own asset over the same loopback host the page was loaded from, so
    what answers is the module the page itself calls — not a second copy and
    not a Python transcription of one.
    """
    return page.evaluate(
        f"async (arg) => {{ const S = await import('/solver_state.js'); return ({expression}); }}",
        argument,
    )


def _bounds(page) -> dict[str, float]:
    return _module(page, "{ min: S.ZOOM_MIN, max: S.ZOOM_MAX, step: S.ZOOM_STEP }")


def _readout(page) -> str:
    return page.inner_text("[data-player-zoom-readout]").strip()


def _percent(page) -> float:
    return float(_readout(page).rstrip("%"))


def _zoom_disabled(page, direction: str) -> str:
    return page.get_attribute(f'[data-player-zoom-action="{direction}"]', "aria-disabled")


def _press(page, direction: str) -> None:
    # force=True: at a bound the button is aria-disabled, and pressing it
    # there is one of the interactions AC-2 is about, so Playwright's
    # actionability check must not refuse it.
    page.click(f'[data-player-zoom-action="{direction}"]', force=True)


def _cell_widths(page):
    """Every cell's used CONTENT width, in px.

    The computed width rather than the bounding box, because the box carries
    the border: every fifth cell and the last in each line draw the heavier
    rule, so a bounding-box reading is not one number but three, and a ratio
    asserted over it needs a tolerance wide enough to hide a real error. The
    content width is exactly ``--player-cell``, which is what the zoom
    multiplies. :func:`_cell_boxes` is the border-box reading, used where the
    claim is "the drawn cell really got bigger".
    """
    return page.evaluate(
        "() => [...document.querySelectorAll('td.player-cell')]"
        ".map((td) => parseFloat(getComputedStyle(td).width))"
    )


def _cell_boxes(page):
    return page.evaluate(
        "() => [...document.querySelectorAll('td.player-cell')]"
        ".map((td) => td.getBoundingClientRect().width)"
    )


def _board_zoom_property(page):
    """``--player-zoom`` as the board element carries it, or ``""``."""
    return page.evaluate(
        "() => document.querySelector('.player-board').style.getPropertyValue('--player-zoom')"
    )


def _solve_state(page, key: str):
    """Every piece of solve state AC-3 claims a zoom never touches."""
    return page.evaluate(
        """(saveKey) => ({
          states: [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state),
          done: window.publicPlayer.getHistory().done.length,
          undone: window.publicPlayer.getHistory().undone.length,
          solved: window.publicPlayer.isSolved(),
          bodySolved: document.body.dataset.solved,
          tool: window.publicPlayer.getTool(),
          region: window.publicPlayer.isRegion(),
          undo: document.querySelector('[data-player-action="undo"]').getAttribute('aria-disabled'),
          redo: document.querySelector('[data-player-action="redo"]').getAttribute('aria-disabled'),
          reset: document.querySelector('[data-player-action="reset"]').getAttribute('aria-disabled'),
          save: localStorage.getItem(saveKey),
        })""",
        key,
    )


def _touch(page_session, kind: str, points) -> None:
    """One ``Input.dispatchTouchEvent`` with ``points`` as ``(x, y)`` pairs.

    A real two-pointer stream is the only way to reach ``play.js``'s pinch
    path: Playwright's own input API has no two-finger gesture, and
    ``page.touchscreen.tap`` is a tap. ``tests/test_public_player.py``'s
    ``_touch_drag`` reaches the one-finger half through the same device and
    documents why it is Chromium-only (ADR-0038/R7 declares the one browser).
    """
    page_session.send(
        "Input.dispatchTouchEvent",
        {
            "type": kind,
            "touchPoints": [{"x": x, "y": y, "id": index + 1} for index, (x, y) in enumerate(points)],
        },
    )


def _open_max(page, host):
    """The 30-cell board on the phone this feature exists for."""
    page.set_viewport_size(PHONE)
    _open(page, host, host[2]["max"])
    assert len(_cell_widths(page)) == MAX_SIZE * MAX_SIZE
    return host[2]["max"]


# ==========================================================================
# AC-1 — the controls zoom, and the percent is the module's
# ==========================================================================


@pytest.mark.browser
class TestPublicZoom_TheControlsChangeTheZoom:
    """AC-1."""

    def test_zoom_in_reads_the_modules_next_step_and_grows_every_cell(self, browser_page, host) -> None:
        """AC-1 — ``ZOOM_MIN + ZOOM_STEP``, never a literal 125.

        The expected percent is ``stepZoom(ZOOM_MIN, "in")`` asked of the
        served module, and the expected cell side is the one before times the
        ratio of the two percents. So the assertion follows the module if the
        module's step ever changes, and fails if ``play.js`` grows a step of
        its own — which is the whole claim of the card.
        """
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)

        # The page opens at the module's floor, not at a number this page chose.
        assert _percent(page) == bounds["min"]
        assert _zoom_disabled(page, "out") == "true"
        assert _zoom_disabled(page, "in") == "false"

        before = _cell_widths(page)
        before_boxes = _cell_boxes(page)
        assert before and min(before) > 0, "no cell was drawn, so the reading below is vacuous"

        _press(page, "in")

        stepped = _module(page, 'S.stepZoom(S.ZOOM_MIN, "in")')
        assert stepped == bounds["min"] + bounds["step"], (stepped, bounds)
        assert _readout(page) == f"{round(stepped)}%"
        assert float(_board_zoom_property(page)) == stepped / 100

        after = _cell_widths(page)
        ratio = stepped / bounds["min"]
        assert len(after) == len(before)
        for index, (was, now) in enumerate(zip(before, after)):
            assert now == pytest.approx(was * ratio, abs=0.5), (index, was, now, ratio)
        # And the DRAWN box grew too, every one of them past the largest
        # before: the content width above is what the zoom multiplies, this is
        # what the player sees. Asserted as a strict inequality over the whole
        # board rather than a ratio, because the box carries a border that is
        # heavier on every fifth cell and does not scale with the zoom.
        assert min(_cell_boxes(page)) > max(before_boxes), (
            min(_cell_boxes(page)),
            max(before_boxes),
        )

    def test_zoom_out_from_a_stepped_in_board_returns_to_the_modules_floor(
        self, browser_page, host
    ) -> None:
        """AC-1's other direction, so "in" is not the only wired button."""
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)
        floor = _cell_widths(page)

        _press(page, "in")
        _press(page, "in")
        assert _percent(page) == _module(page, 'S.stepZoom(S.stepZoom(S.ZOOM_MIN, "in"), "in")')

        _press(page, "out")
        _press(page, "out")
        assert _percent(page) == bounds["min"]
        assert _cell_widths(page) == pytest.approx(floor, abs=0.5)


# ==========================================================================
# AC-2 — both bounds are read from the module
# ==========================================================================


@pytest.mark.browser
class TestPublicZoom_TheBoundsComeFromTheModule:
    """AC-2."""

    def test_both_ends_disable_their_button_and_a_press_there_changes_nothing(
        self, browser_page, host
    ) -> None:
        """AC-2 — the ends of the range, and the number of steps to reach them,
        are the module's.

        The step count is ``(ZOOM_MAX - ZOOM_MIN) / ZOOM_STEP`` computed from
        the module's own three constants, so a changed range moves this test
        with it instead of leaving it asserting a stale rung.
        """
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)
        rungs = (bounds["max"] - bounds["min"]) / bounds["step"]
        assert rungs == int(rungs) and rungs >= 2, bounds
        rungs = int(rungs)

        # The low end, which is where the page opens.
        assert _percent(page) == bounds["min"]
        assert _zoom_disabled(page, "out") == "true"
        at_floor = _cell_widths(page)
        _press(page, "out")
        assert _percent(page) == bounds["min"]
        assert _cell_widths(page) == pytest.approx(at_floor, abs=0.5)
        assert _zoom_disabled(page, "out") == "true"

        # Every rung up to the high end, each one the module's own next step.
        for _ in range(rungs):
            expected = _module(page, 'S.stepZoom(arg, "in")', _percent(page))
            _press(page, "in")
            assert _percent(page) == expected

        assert _percent(page) == bounds["max"]
        assert _zoom_disabled(page, "in") == "true"
        assert _zoom_disabled(page, "out") == "false"
        at_ceiling = _cell_widths(page)
        _press(page, "in")
        assert _percent(page) == bounds["max"]
        assert _cell_widths(page) == pytest.approx(at_ceiling, abs=0.5)

    def test_no_sequence_of_presses_leaves_the_modules_range(self, browser_page, host) -> None:
        """AC-2's completeness half: a seeded walk over the two buttons, with
        every reading held inside ``[ZOOM_MIN, ZOOM_MAX]``.

        The walk deliberately presses past both ends — that is what makes the
        clamp load-bearing rather than incidental — and its length is well
        over the number of rungs in either direction.
        """
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)
        rng = random.Random(3241)
        seen = []
        for _ in range(SWEEP_CASES):
            direction = "in" if rng.random() < 0.5 else "out"
            expected = _module(page, 'S.stepZoom(arg[0], arg[1])', [_percent(page), direction])
            _press(page, direction)
            percent = _percent(page)
            assert percent == expected, (direction, percent, expected)
            assert bounds["min"] <= percent <= bounds["max"], (percent, bounds)
            seen.append(percent)
        assert len(seen) == SWEEP_CASES
        # Not a vacuous walk: both ends were actually reached.
        assert min(seen) == bounds["min"] and max(seen) == bounds["max"], sorted(set(seen))


# ==========================================================================
# AC-3 — a zoom is a view, never a stroke
# ==========================================================================


@pytest.mark.browser
class TestPublicZoom_ZoomRecordsNoStroke:
    """AC-3."""

    def test_every_zoom_interaction_leaves_the_board_history_and_save_identical(
        self, browser_page, host
    ) -> None:
        """AC-3 — and the snapshot is taken on a board with marks on it.

        A snapshot of an empty board would be equal to itself for the wrong
        reason: every cell is ``unknown`` and every history is empty, so a
        zoom that silently cleared the board would pass. The board is marked
        first, and the snapshot's own non-emptiness is asserted.
        """
        page = browser_page
        key = _open_max(page, host)
        save_key = page.evaluate("() => window.publicPlayer.saveKey")

        _tap(page, 0, 0)
        _tap(page, 3, 4)
        page.click('[data-player-tool="maybe"]')
        _tap(page, 7, 7)

        floor = _bounds(page)["min"]
        before = _solve_state(page, save_key)
        assert before["done"] >= 3, before
        assert before["states"].count("unknown") < len(before["states"]), before
        assert before["save"], "nothing was saved, so the save comparison is vacuous"
        assert _percent(page) == floor

        _press(page, "in")
        _press(page, "in")
        _press(page, "out")
        session = page.context.new_cdp_session(page)
        try:
            # The first finger stays put — see _pinch below for why a moving
            # one is cancelled by the compositor before the second lands.
            x, y = _cell_centre(page, 5, 0)
            assert x + 160 < PHONE["width"], x
            _touch(session, "touchStart", [(x, y)])
            _touch(session, "touchStart", [(x, y), (x + 80, y)])
            _touch(session, "touchMove", [(x, y), (x + 160, y)])
            _touch(session, "touchEnd", [])
        finally:
            session.detach()
        page.wait_for_timeout(SETTLE_MS)  # see SETTLE_MS

        after = _solve_state(page, save_key)
        assert after == before, {k: (before[k], after[k]) for k in before if before[k] != after[k]}
        # The zoom really did move, so "nothing changed" is not "nothing
        # happened": three button presses net one step up, and the pinch then
        # doubled that. A page where no zoom reached the board at all would
        # satisfy every equality above and fails here.
        assert _percent(page) > floor, (_readout(page), floor)
        assert float(_board_zoom_property(page)) == _percent(page) / 100
        assert key in save_key


# ==========================================================================
# AC-4 — the anchored scroll is the module's own return value
# ==========================================================================


@pytest.mark.browser
class TestPublicZoom_TheAnchoredScrollIsTheModules:
    """AC-4."""

    def test_the_stage_lands_where_anchored_scroll_says_on_both_axes(
        self, browser_page, host
    ) -> None:
        """AC-4 — asserted against ``anchoredScroll``'s return, not a pixel figure.

        Three things make this a control that can fail rather than a reading
        of whatever happened:

        #. the stage is scrolled away from the origin on both axes first, and
           having room to scroll on both is asserted — on a stage pinned at 0
           the formula and "do nothing" are indistinguishable;
        #. the expected value is ``anchoredScroll(scroll, anchor, old, new)``
           from the served module, and it is asserted to **differ** from the
           scroll position before the zoom, so a page that simply left the
           scroll alone fails here;
        #. the browser's own clamp to ``scrollWidth - clientWidth`` is applied
           to the expectation rather than assumed away, and the horizontal
           axis is additionally asserted to be *inside* that range, so at
           least one axis is compared to an unclamped module value.
        """
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)

        room = page.evaluate(
            """() => {
              const stage = document.querySelector('[data-player-stage]');
              stage.scrollLeft = Math.round((stage.scrollWidth - stage.clientWidth) / 3);
              stage.scrollTop = Math.round((stage.scrollHeight - stage.clientHeight) / 3);
              return {
                x: stage.scrollWidth - stage.clientWidth,
                y: stage.scrollHeight - stage.clientHeight,
                scrollLeft: stage.scrollLeft,
                scrollTop: stage.scrollTop,
                anchorX: stage.clientWidth / 2,
                anchorY: stage.clientHeight / 2,
              };
            }"""
        )
        assert room["x"] > 0, "the stage cannot scroll sideways, so the x axis is vacuous"
        assert room["y"] > 0, "the stage cannot scroll vertically, so the y axis is vacuous"
        assert room["scrollLeft"] > 0 and room["scrollTop"] > 0, room

        old = _percent(page)
        _press(page, "in")
        new = _percent(page)
        assert new == old + bounds["step"], (old, new, bounds)

        landed = page.evaluate(
            """() => {
              const stage = document.querySelector('[data-player-stage]');
              return {
                scrollLeft: stage.scrollLeft,
                scrollTop: stage.scrollTop,
                maxX: stage.scrollWidth - stage.clientWidth,
                maxY: stage.scrollHeight - stage.clientHeight,
              };
            }"""
        )
        wanted = _module(
            page,
            "[S.anchoredScroll(arg[0], arg[1], arg[2], arg[3]),"
            " S.anchoredScroll(arg[4], arg[5], arg[2], arg[3])]",
            [room["scrollLeft"], room["anchorX"], old, new, room["scrollTop"], room["anchorY"]],
        )
        wanted_x, wanted_y = wanted

        # (2) the formula asks for a different place than "leave it alone".
        assert wanted_x != room["scrollLeft"], (wanted_x, room)
        assert wanted_y != room["scrollTop"], (wanted_y, room)
        # (3) the x axis is compared to the module's value with no clamp in play.
        assert 0 < wanted_x < landed["maxX"], (wanted_x, landed)
        assert landed["scrollLeft"] == pytest.approx(wanted_x, abs=1.5), (landed, wanted_x)
        assert landed["scrollTop"] == pytest.approx(
            min(max(wanted_y, 0), landed["maxY"]), abs=1.5
        ), (landed, wanted_y)


# ==========================================================================
# The gutters, which the zoom grows with everything else
# ==========================================================================


@pytest.mark.browser
class TestPublicZoom_AZoomedGutterNeverCoversTheBoard:
    """The one thing the zoom needed beyond the transform, found by rendering it.

    ``player.css`` promises the clue gutters stay in view while the board is
    panned, and they are sized from ``--player-cell`` — so the zoom grows them
    too. On a 390 px phone at 300% the ROW gutter alone is then wider than the
    whole stage: pinned, it covers every column, and a player who zoomed in to
    read a 30-cell board can reach no cell at all. That is the opposite of what
    the zoom is for, and no assertion in this module caught it — the renders
    did, which is why the owner looks at them.

    ``play.js``'s ``keepCluesInView`` is the answer, and the rule it applies is
    **derived**: a gutter is pinned only while the stage still has room beside
    it for a whole cell. No share and no constant, so this test recomputes the
    same predicate from the page's own boxes rather than comparing against a
    threshold written here.
    """

    _READING = """() => {
      const board = document.querySelector('.player-board');
      const stage = document.querySelector('[data-player-stage]');
      const row = document.querySelector('th.player-clue.is-row').getBoundingClientRect();
      const col = document.querySelector('th.player-clue.is-col').getBoundingClientRect();
      const cell = document.querySelector('td.player-cell').getBoundingClientRect();
      const style = (el) => getComputedStyle(document.querySelector(el));
      // The part of the stage on screen with the page at its top: the stage's
      // bottom edge can sit below the fold (the toolbar wraps on a phone).
      const innerTop = stage.getBoundingClientRect().top + stage.clientTop;
      const visible = Math.min(innerTop + stage.clientHeight, innerHeight) - innerTop;
      return {
        keepsRows: board.classList.contains('keeps-rows'),
        keepsCols: board.classList.contains('keeps-cols'),
        roomBesideRows: stage.clientWidth - row.width >= 2 * cell.width,
        roomBesideCols: visible - col.height >= 2 * cell.height,
        rowLeft: style('th.player-clue.is-row').left,
        colTop: style('th.player-clue.is-col').top,
        rowPosition: style('th.player-clue.is-row').position,
      };
    }"""

    def test_a_gutter_is_pinned_exactly_while_a_cell_still_fits_beside_it(
        self, browser_page, host
    ) -> None:
        page = browser_page
        bounds = None
        seen = []  # (viewport name, percent, keepsRows, keepsCols)
        for name, viewport in (("phone", PHONE), ("landscape", LANDSCAPE)):
            page.set_viewport_size(viewport)
            _open(page, host, host[2]["max"])
            bounds = _bounds(page)
            rungs = int((bounds["max"] - bounds["min"]) / bounds["step"])
            for step in range(rungs + 1):
                if step:
                    _press(page, "in")
                reading = page.evaluate(self._READING)
                # The class is the measurement, on both axes and at every rung.
                assert reading["keepsRows"] is reading["roomBesideRows"], (name, step, reading)
                assert reading["keepsCols"] is reading["roomBesideCols"], (name, step, reading)
                # And the class is what actually moves the offset: `position`
                # stays sticky throughout (CARD-283's declaration, which
                # test_public_player.py reads), so what a pinned axis has is an
                # offset of 0 and an unpinned one the `auto` default.
                assert reading["rowPosition"] == "sticky", reading
                assert reading["rowLeft"] == ("0px" if reading["keepsRows"] else "auto"), reading
                assert reading["colTop"] == ("0px" if reading["keepsCols"] else "auto"), reading
                seen.append((name, _percent(page), reading["keepsRows"], reading["keepsCols"]))

            # It lets go monotonically, per axis and per viewport — once there
            # is no room, zooming further in cannot give it back.
            mine = [row for row in seen if row[0] == name]
            for axis in (2, 3):
                kept = [row[axis] for row in mine]
                assert kept == sorted(kept, reverse=True), (name, axis, mine)
            # At the module's floor the promise CARD-283 made is intact on BOTH
            # axes at BOTH viewports. Cycle 2 narrowed the column half to the
            # phone, honestly: with the toolbar wrapped to two rows, the 844x390
            # stage was 193 px tall, the 30-clue band took 134 of it, and a
            # pinned band would have left under two cells of board, so the rule
            # unpinned it. Cycle 3 gives the row back (landscape drops the
            # readout and tightens the gap, the toolbar is one 44 px row, the
            # stage is 249 px, MEASURED): 249 - 134 leaves two 33 px cells
            # under the band, and the band re-pins. Nothing was forced: the
            # equality `keepsCols is roomBesideCols` above is the rule, and
            # this line records what the geometry now gives.
            assert mine[0][1:3] == (bounds["min"], True), mine
            assert mine[0][3] is True, mine

        # Not a vacuous rule, on EITHER axis: each has a rung somewhere in the
        # sweep where it holds and a rung where it lets go, so neither
        # `keepsRows is roomBesideRows` nor `keepsCols is roomBesideCols` can be
        # `True == True` throughout. (Cycle 1: this read the row list alone,
        # and a column predicate reading `.width` for `.height` survived.)
        for axis, label in ((2, "rows"), (3, "cols")):
            held = [row for row in seen if row[axis]]
            let_go = [row for row in seen if not row[axis]]
            assert held and let_go, (label, seen)

    #: Per axis, the number of whole cells the player can see in the part of the
    #: stage that is not under a pinned gutter and not below the fold, swept over
    #: every scroll offset in steps of a quarter cell. ``min`` is the worst
    #: scroll position, ``max`` the best — a measurement of the CONSEQUENCE the
    #: rule exists for, taken without calling the rule's own predicate.
    _REACH = """() => {
      const stage = document.querySelector('[data-player-stage]');
      const W = window.publicPlayer.payload.width;
      const cells = [...document.querySelectorAll('td.player-cell')];
      const firstRow = cells.slice(0, W);
      const firstCol = cells.filter((_td, i) => i % W === 0);
      const rowGutter = document.querySelector('th.player-clue.is-row');
      const colGutter = document.querySelector('th.player-clue.is-col');
      const box = stage.getBoundingClientRect();
      const left = box.left + stage.clientLeft;
      const top = box.top + stage.clientTop;
      const right = left + stage.clientWidth;
      const bottom = Math.min(top + stage.clientHeight, innerHeight);
      const saved = [stage.scrollLeft, stage.scrollTop];
      const quarter = firstRow[0].getBoundingClientRect().width / 4;
      const sweep = (prop, max, count) => {
        const counts = [];
        for (let at = 0; at < max + quarter; at += quarter) {
          stage[prop] = Math.min(at, max);
          counts.push(count());
        }
        return { min: Math.min(...counts), max: Math.max(...counts) };
      };
      const cols = sweep('scrollLeft', stage.scrollWidth - stage.clientWidth, () => {
        const edge = Math.max(left, rowGutter.getBoundingClientRect().right);
        return firstRow.filter((td) => {
          const r = td.getBoundingClientRect();
          return r.left >= edge - 0.5 && r.right <= right + 0.5;
        }).length;
      });
      stage.scrollLeft = saved[0];
      const rows = sweep('scrollTop', stage.scrollHeight - stage.clientHeight, () => {
        const edge = Math.max(top, colGutter.getBoundingClientRect().bottom);
        return firstCol.filter((td) => {
          const r = td.getBoundingClientRect();
          return r.top >= edge - 0.5 && r.bottom <= bottom + 0.5;
        }).length;
      });
      stage.scrollLeft = saved[0];
      stage.scrollTop = saved[1];
      return { cols, rows };
    }"""

    def _assert_reachable(self, page, label) -> None:
        reading = page.evaluate(self._READING)
        reach = page.evaluate(self._REACH)
        # A board nobody can reach is the defect this class exists for.
        assert reach["cols"]["max"] >= 1 and reach["rows"]["max"] >= 1, (label, reach)
        # A PINNED gutter must leave a whole cell at EVERY scroll offset, which
        # is what the two-cell rule is derived to guarantee; an unpinned one
        # only has to be scrollable into view (asserted above).
        if reading["keepsRows"]:
            assert reach["cols"]["min"] >= 1, (label, reach, reading)
        if reading["keepsCols"]:
            assert reach["rows"]["min"] >= 1, (label, reach, reading)

    def test_a_pinned_gutter_always_leaves_a_whole_cell_in_view(
        self, browser_page, host
    ) -> None:
        """F-3's 175% rung, and F-4's fold, measured by their consequence.

        The sweep above asks whether the class equals the rule; this asks
        whether the rule is *enough* — at every rung and every scroll offset,
        on both viewports, a pinned axis leaves at least one whole cell visible.
        Cycle 1 measured the one-cell rule failing exactly this at 175%.
        """
        page = browser_page
        for name, viewport in (("phone", PHONE), ("landscape", LANDSCAPE)):
            page.set_viewport_size(viewport)
            _open(page, host, host[2]["max"])
            bounds = _bounds(page)
            for step in range(int((bounds["max"] - bounds["min"]) / bounds["step"]) + 1):
                if step:
                    _press(page, "in")
                self._assert_reachable(page, (name, _percent(page)))

    def test_one_cell_of_room_is_not_enough_at_the_rung_the_owner_will_meet(
        self, browser_page, host
    ) -> None:
        """The control for the reach measurement: it can fail.

        At 175% on the phone the row gutter is put back by hand, as the
        one-cell rule left it. The measurement must then find a scroll offset
        with no whole column in view; unpinned, it must not.
        """
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)
        for _ in range(3):
            _press(page, "in")
        assert _percent(page) == bounds["min"] + 3 * bounds["step"]
        pinned = """(on) => document.querySelector('.player-board').classList.toggle('keeps-rows', on)"""
        page.evaluate(pinned, True)
        assert page.evaluate(self._REACH)["cols"]["min"] == 0, "a straddled offset exists and was not seen"
        page.evaluate(pinned, False)
        assert page.evaluate(self._REACH)["cols"]["max"] >= 1

    def test_rotating_a_zoomed_phone_re_asks_the_rule(self, browser_page, host) -> None:
        """F-1: zoom, then rotate, with no further interaction.

        ``keepCluesInView`` reads the viewport's geometry, so a rotation is an
        input to it exactly as a zoom press is. Left to the presses, a phone
        zoomed to 250% and turned on its side kept the portrait answer on both
        axes and showed no whole cell until a zoom button was pressed.
        """
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)
        for _ in range(5):
            _press(page, "in")
        assert _percent(page) == bounds["min"] + 5 * bounds["step"]
        before = page.evaluate(self._READING)
        # The rotation must change the answer, or this test proves nothing.
        page.set_viewport_size(LANDSCAPE)
        for _ in range(2):
            page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
        after = page.evaluate(self._READING)
        assert (before["roomBesideRows"], before["roomBesideCols"]) != (
            after["roomBesideRows"], after["roomBesideCols"],
        ), "rotating did not change what the geometry asks for"
        assert after["keepsRows"] is after["roomBesideRows"], (before, after)
        assert after["keepsCols"] is after["roomBesideCols"], (before, after)
        self._assert_reachable(page, "landscape, after rotating")
        # And back.
        page.set_viewport_size(PHONE)
        for _ in range(2):
            page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
        back = page.evaluate(self._READING)
        assert back["keepsRows"] is back["roomBesideRows"], back
        assert back["keepsCols"] is back["roomBesideCols"], back
        self._assert_reachable(page, "phone, after rotating back")

    def test_pinning_the_gutter_anyway_is_what_hides_the_board(
        self, browser_page, host
    ) -> None:
        """The control: the unpinning is load-bearing, not decoration.

        At the top of the range the rule's class is put back by hand, and the
        board is measured with it — no cell's left edge is inside the part of
        the stage the pinned gutter does not cover. That is the state the
        renders showed before ``keepCluesInView`` existed.
        """
        page = browser_page
        _open_max(page, host)
        bounds = _bounds(page)
        for _ in range(int((bounds["max"] - bounds["min"]) / bounds["step"])):
            _press(page, "in")
        assert _percent(page) == bounds["max"]
        assert page.evaluate(self._READING)["keepsRows"] is False, "the rule did not fire"

        visible = """(pinned) => {
          const board = document.querySelector('.player-board');
          board.classList.toggle('keeps-rows', pinned);
          const stage = document.querySelector('[data-player-stage]');
          const box = stage.getBoundingClientRect();
          const gutter = document.querySelector('th.player-clue.is-row').getBoundingClientRect();
          const edge = pinned ? Math.max(box.left, gutter.right) : box.left;
          return [...document.querySelectorAll('td.player-cell')].filter((td) => {
            const r = td.getBoundingClientRect();
            return r.left >= edge && r.right <= box.right && r.bottom > box.top && r.top < box.bottom;
          }).length;
        }"""
        pinned = page.evaluate(visible, True)
        unpinned = page.evaluate(visible, False)
        assert pinned == 0, f"the pinned gutter left {pinned} cells reachable, so it is not the cause"
        assert unpinned > 0, "unpinned, the board is still unreachable — the fix does not work"


# ==========================================================================
# CARD-324 review cycle 2 — the gutter rule held over its OPERANDS, and the
# stage's height held to the real toolbar
# ==========================================================================

#: The narrowest phone the sweeps start from. Not derived: it is the smallest
#: width ``player.css``'s own header names a phone for, and the only written
#: starting point; everything ABOVE it is derived from the page's geometry.
NARROWEST = 320

#: The viewport heights the sweeps span (a landscape phone to a tall desktop
#: window) and the widest width. Bounds of the sweep, not of the feature.
SHORTEST, TALLEST, WIDEST = 390, 900, 1440

#: What the gutter test reads, with the page scrolled to its top first (and
#: put back after), so the viewport-relative numbers are measured at the
#: scroll the rule claims to be conservative for — without calling the rule.
_GEOMETRY = """() => {
  const stage = document.querySelector('[data-player-stage]');
  const board = document.querySelector('.player-board');
  const y = window.scrollY;
  window.scrollTo(0, 0);
  const box = stage.getBoundingClientRect();
  const row = document.querySelector('th.player-clue.is-row').getBoundingClientRect();
  const col = document.querySelector('th.player-clue.is-col').getBoundingClientRect();
  const cell = document.querySelector('td.player-cell').getBoundingClientRect();
  const innerTop = box.top + stage.clientTop;
  const visible = Math.min(innerTop + stage.clientHeight, innerHeight) - innerTop;
  const reading = {
    innerWidth, innerHeight,
    clientWidth: stage.clientWidth, clientHeight: stage.clientHeight,
    rowWidth: row.width, colHeight: col.height,
    cellWidth: cell.width, cellHeight: cell.height,
    innerTop, visible,
    docBottom: box.bottom,
    docHeight: document.documentElement.scrollHeight,
    keepsRows: board.classList.contains('keeps-rows'),
    keepsCols: board.classList.contains('keeps-cols'),
  };
  window.scrollTo(0, y);
  return reading;
}"""


def _settle(page, frames: int = 2) -> None:
    for _ in range(frames):
        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")


def _rung_count(page) -> int:
    bounds = _bounds(page)
    return int(round((bounds["max"] - bounds["min"]) / bounds["step"]))


def _to_rung(page, rung: int) -> None:
    bounds = _bounds(page)
    target = bounds["min"] + rung * bounds["step"]
    while _percent(page) < target:
        _press(page, "in")
    while _percent(page) > target:
        _press(page, "out")
    assert _percent(page) == bounds["min"] + rung * bounds["step"]


def _rows_say(reading) -> bool:
    return reading["clientWidth"] - reading["rowWidth"] >= 2 * reading["cellWidth"]


def _cols_say(reading) -> bool:
    return reading["visible"] - reading["colHeight"] >= 2 * reading["cellHeight"]


@pytest.mark.browser
class TestPublicZoom_TheGutterRuleHoldsOverItsOperands:
    """Cycle 2 (C2-2, C2-3): the rule's tests held two viewports and nine rungs.

    A factor of 1.5 on the row axis, ``innerWidth`` for ``stage.clientWidth``,
    ``>`` for ``>=``, a dropped ``window.scrollY`` or ``stage.clientTop``: each
    left every test green, because the sweep sampled two viewports and nothing
    scrolled the page. So here the viewport is the variable.

    **How the sweep is placed, and why it is not a copy of the reviewer's.**
    The rule flips on an axis at one viewport size per zoom rung. That size is
    not chosen: it is *predicted from the page's own geometry* (the stage's
    width less its viewport, the gutter, two cell pitches) and then *verified*
    — a flip must really occur within a few pixels of it, so a wrong prediction
    fails rather than silently sampling elsewhere. Around each prediction the
    sweep covers one cell pitch below it (the most any factor between 1 and 2
    can move the flip) plus the viewport-to-stage offset (what ``innerWidth``
    for ``clientWidth`` moves it by), at a 3 px step, and 1 px steps right at
    it (where ``offsetWidth`` and a dropped ``clientTop`` live). Above the
    largest prediction every rung is pinned, so the range ends there.

    **The operand table (cycle 2's remit: classify the whole population).**
    Every operand of ``keepCluesInView``'s two predicates, of ``visibleHeight``
    and of the stage-cap write, with the plant (by text, count ``== 1``) that
    reds, or the declaration. "rows"/"cols"/"cap"/"census" name the test below
    or above that holds it.

    * rows: ``stage.clientWidth`` -> ``innerWidth`` / ``offsetWidth`` /
      ``scrollWidth`` (rows sweep); ``rowClue`` width -> ``.height`` or the
      column gutter (rows); ``-`` -> ``+`` (rows); ``>=`` -> ``>`` (boundary);
      ``CELLS_BESIDE`` -> 1.5 on this axis alone (rows); ``* width`` ->
      ``* height`` (rows: the cell is 29 x 33 at 100%, NOT square, so this is
      not an equivalent mutant); the class name swapped, or ``add`` / ``remove``
      for ``toggle(name, force)`` (rows).
    * cols: ``visibleHeight`` -> ``clientHeight`` / ``innerHeight`` (cols
      sweep, scrolled/unbounded); band ``.height`` -> ``.width``, ``-`` -> ``+``,
      1.5, ``* height`` -> ``* width``, class swapped, ``add`` / ``remove``
      (cols); ``>=`` -> ``>`` (boundary).
    * the constant ``CELLS_BESIDE``: 1, 3 and 1.5 on both axes (rows).
    * ``visibleHeight``: min -> max (cols); ``innerHeight`` -> ``innerWidth``
      (cols); ``rect.top`` -> ``rect.bottom`` (cols); ``+ clientTop`` dropped,
      ``+ scrollY`` dropped or sign-flipped, ``-`` -> ``+`` (scrolled and
      unbounded: it needs a page that is both scrolled and taller than the
      viewport); ``clientHeight`` -> ``offsetHeight`` / ``scrollHeight`` (cols);
      the measured cell -> a major-rule cell (rows, cols: the pitch residue
      cycle 2 called C2-4 is real, 0.5 px, and the first cell is pinned).
    * the guard ``if (!board || !rowClue || !colClue || !cell) return``: the
      last three operands and the whole guard (missing element). **Declared:**
      ``!board`` is subsumed by the other three (the gutters and cells are
      built inside the one board, so a stage without it has none of them).
    * the stage-cap write: ``rect.top`` -> ``rect.bottom``, ``scrollY``
      dropped or flipped, the property renamed, the unit changed (fold, with
      the page scrolled), and the CSS side: the air dropped, the border
      dropped, the fallback renamed (fold).
    * listeners: ``resize`` removed, ``orientationchange`` instead, an empty
      handler (cols sweep); ``ResizeObserver`` removed or on the content box
      (toolbar); a second inline-arrow ``resize`` listener (census total).
    * **Declared, equivalent:** ``onScreen < clientHeight`` -> ``<=`` -- both
      branches yield the same number at equality, so no input distinguishes
      them. ``innerHeight`` -> ``document.documentElement.clientHeight`` --
      they differ only by a classic horizontal scrollbar; measured equal at
      2610 of 2610 viewport / rung samples in the one declared browser
      (headless Chromium, overlay scrollbars), so a plant survives and is
      NOT a gap in this environment.
    * **Declared, boundary:** ``>=`` is exact. A natural gutter is fractional
      and the stage an integer, so equality does not occur at a phone width
      except by coincidence (the real 125% gutter is 215 px and the equality
      sits at a 319 px viewport, below the narrowest phone); it is therefore
      manufactured in ``test_the_boundary_itself_pins_on_both_axes`` rather
      than waited for.
    """

    def _expect(self, page, axis: str, label) -> dict:
        reading = page.evaluate(_GEOMETRY)
        if axis == "rows":
            assert reading["keepsRows"] is _rows_say(reading), (label, reading)
        else:
            assert reading["keepsCols"] is _cols_say(reading), (label, reading)
        return reading

    def _flip(self, page, axis, widths_or_heights, set_size, label) -> bool:
        """Walk the sizes; the class must equal the geometry at each; True if it flipped."""
        classes = []
        for size in widths_or_heights:
            set_size(size)
            _settle(page)
            reading = self._expect(page, axis, (label, size))
            classes.append(reading["keepsRows" if axis == "rows" else "keepsCols"])
        return len(set(classes)) == 2

    def test_the_row_rule_equals_the_geometry_across_the_phone_widths_at_every_rung(
        self, browser_page, host
    ) -> None:
        page = browser_page
        _open_max(page, host)
        plan = {}
        for rung in range(_rung_count(page) + 1):
            if rung:
                _press(page, "in")
            g = page.evaluate(_GEOMETRY)
            offset = g["innerWidth"] - g["clientWidth"]
            plan[rung] = (
                math.ceil(g["rowWidth"] + 2 * g["cellWidth"] + offset),
                math.ceil(g["cellWidth"] + offset) + 2,
            )
        upper = max(edge for edge, _ in plan.values()) + 8
        assert upper < 1000, "the cell grew past its fitted floor; the prediction does not apply"
        checked = 0
        for rung, (edge, reach) in plan.items():
            _to_rung(page, rung)
            near = list(range(edge - 3, edge + 4))
            windowed = list(range(edge - reach, edge + 5, 3))
            sparse = list(range(NARROWEST, upper, 40))
            widths = sorted({w for w in near + windowed + sparse if NARROWEST <= w <= upper}, reverse=True)
            flipped = self._flip(
                page, "rows", widths,
                lambda w: page.set_viewport_size({"width": w, "height": PHONE["height"]}),
                ("rows", _percent(page)),
            )
            checked += len(widths)
            # The prediction is verified, not trusted: the rule really flips
            # inside the window it was derived to flip in. (At the lowest rungs
            # the board is reachable at every phone width and there is nothing
            # to flip; the prediction then lies below the narrowest phone.)
            if edge - 3 >= NARROWEST:
                assert flipped, ("no flip near the predicted width", rung, edge)
            # The consequence, at the flip itself: a pinned row gutter leaves a
            # whole cell at every scroll offset (cycle 2's 0-vs-11 count,
            # taken at the widths where it could go wrong).
            for w in near:
                if NARROWEST <= w:
                    page.set_viewport_size({"width": w, "height": PHONE["height"]})
                    _settle(page)
                    if page.evaluate(_GEOMETRY)["keepsRows"]:
                        assert page.evaluate(self._REACH)["min"] >= 1, ("rows", _percent(page), w)
        assert checked >= 100, checked

    #: Whole cells in the first board row that are visible at the WORST scroll
    #: offset of the stage, with the row gutter's pin taken into account — the
    #: consequence the row rule exists for, measured without calling it.
    _REACH = """() => {
      const stage = document.querySelector('[data-player-stage]');
      const W = window.publicPlayer.payload.width;
      const first = [...document.querySelectorAll('td.player-cell')].slice(0, W);
      const gutter = document.querySelector('th.player-clue.is-row');
      const box = stage.getBoundingClientRect();
      const left = box.left + stage.clientLeft;
      const right = left + stage.clientWidth;
      const quarter = first[0].getBoundingClientRect().width / 4;
      const saved = stage.scrollLeft;
      const max = stage.scrollWidth - stage.clientWidth;
      let min = Infinity;
      for (let at = 0; at < max + quarter; at += quarter) {
        stage.scrollLeft = Math.min(at, max);
        const edge = Math.max(left, gutter.getBoundingClientRect().right);
        const n = first.filter((td) => {
          const r = td.getBoundingClientRect();
          return r.left >= edge - 0.5 && r.right <= right + 0.5;
        }).length;
        min = Math.min(min, n);
      }
      stage.scrollLeft = saved;
      return { min };
    }"""

    def test_the_column_rule_equals_the_geometry_across_the_viewport_heights_at_every_rung(
        self, browser_page, host
    ) -> None:
        page = browser_page
        checked = 0
        flips = 0
        for name, viewport in (("phone", PHONE), ("landscape", LANDSCAPE)):
            # The prediction is read in the regime the flip happens in. A 844 px
            # wide window taller than 844 is PORTRAIT, where the readout is
            # shown and the toolbar wraps (cycle 3), and a prediction taken
            # there is 56 px off for the landscape heights it is applied to.
            # So the landscape phone is opened at the tallest height that is
            # still landscape, and the phone at TALLEST as before.
            tall = min(TALLEST, viewport["width"] - 1) if viewport["width"] > viewport["height"] else TALLEST
            page.set_viewport_size({**viewport, "height": tall})
            _open(page, host, host[2]["max"])
            for rung in range(_rung_count(page) + 1):
                _to_rung(page, rung)
                g = page.evaluate(_GEOMETRY)
                # visible = clientHeight tracks the viewport's height 1:1 while
                # the cap is what bounds the stage, so the flip is where the
                # visible height less the band reaches two pitches.
                edge = math.ceil(g["innerHeight"] + 2 * g["cellHeight"] + g["colHeight"] - g["visible"])
                reach = math.ceil(g["cellHeight"]) + 20
                near = list(range(edge - 3, edge + 4))
                windowed = list(range(edge - reach, edge + 5, 3))
                heights = sorted(
                    {h for h in near + windowed + list(range(SHORTEST, TALLEST + 1, 53))
                     if SHORTEST <= h <= TALLEST},
                    reverse=True,
                )
                flipped = self._flip(
                    page, "cols", heights,
                    lambda h: page.set_viewport_size({"width": viewport["width"], "height": h}),
                    (name, _percent(page)),
                )
                checked += len(heights)
                if SHORTEST <= edge - 3 and edge + 3 <= TALLEST:
                    assert flipped, ("no flip near the predicted height", name, rung, edge)
                    flips += 1
        assert checked >= 200 and flips >= 9, (checked, flips)

    def test_the_boundary_itself_pins_on_both_axes(self, browser_page, host) -> None:
        """``>=`` and not ``>``: a viewport CAN land on ``room == 2 pitches`` exactly.

        A natural gutter is a fraction of a pixel wide and the stage's width an
        integer, so the equality is manufactured: the gutters are given a
        whole-pixel size by the sheet below, and the stage a size that makes
        the room exactly two cell pitches. At one pixel less the axis must let
        go and at one more it must hold — the three together are what a ``>``
        cannot satisfy. (Not contrived out of nothing: at 125% the real row
        gutter measures 215 px, and the equality is real at a 319 px viewport.)
        """
        page = browser_page
        page.set_viewport_size({"width": 600, "height": 1300})
        _open(page, host, host[2]["max"])
        _to_rung(page, 1)
        page.add_style_tag(
            content="th.player-clue.is-row { min-width: 300px !important }"
            " th.player-clue.is-col { height: 200px !important }"
        )
        _press(page, "in")
        _press(page, "out")
        g = page.evaluate(_GEOMETRY)
        assert g["rowWidth"] == int(g["rowWidth"]) and g["colHeight"] == int(g["colHeight"]), g
        # Rows: the stage is as wide as the viewport less its offset.
        offset = g["innerWidth"] - g["clientWidth"]
        need = g["rowWidth"] + 2 * g["cellWidth"]
        results = {}
        for delta in (-1, 0, 1):
            page.set_viewport_size({"width": int(need + offset) + delta, "height": 1300})
            _settle(page)
            r = page.evaluate(_GEOMETRY)
            assert r["clientWidth"] - r["rowWidth"] - 2 * r["cellWidth"] == delta, r
            results[delta] = r["keepsRows"]
        assert results == {-1: False, 0: True, 1: True}, results
        # Columns: the stage's own height is given, and the viewport is tall
        # enough that it, not the fold, is what bounds the visible height.
        page.set_viewport_size({"width": 600, "height": 1300})
        results = {}
        for delta in (-1, 0, 1):
            height = int(g["colHeight"] + 2 * g["cellHeight"]) + delta
            page.evaluate(
                "(h) => { document.querySelector('[data-player-stage]').style.maxHeight = h + 'px';"
                " window.dispatchEvent(new Event('resize')); }",
                height,
            )
            _settle(page)
            r = page.evaluate(_GEOMETRY)
            assert r["visible"] - r["colHeight"] - 2 * r["cellHeight"] == delta, r
            results[delta] = r["keepsCols"]
        assert results == {-1: False, 0: True, 1: True}, results

    def test_a_scrolled_page_and_an_unbounded_stage_hold_the_visible_height_operands(
        self, browser_page, host
    ) -> None:
        """C2-2: nothing scrolled the page, so ``scrollY`` was unread.

        The stage is left uncapped here (``max-height: none``) so that the
        part of it on screen — ``innerHeight`` less its top, in page
        coordinates — is what bounds the visible height, and so the page is
        tall enough to scroll at any viewport. The page is scrolled before the
        rule is re-asked; the expectation is read with the page back at its
        top. A dropped ``scrollY`` over-states the visible height by the
        scroll, a flipped sign by twice it, a dropped ``clientTop`` by a
        pixel, the wrong edge of the stage by its height.
        """
        page = browser_page
        page.set_viewport_size({"width": PHONE["width"], "height": TALLEST})
        _open(page, host, host[2]["max"])
        page.evaluate("() => { document.querySelector('[data-player-stage]').style.maxHeight = 'none'; }")
        checked = 0
        for rung in range(_rung_count(page) + 1):
            _to_rung(page, rung)
            g = page.evaluate(_GEOMETRY)
            # Uncapped, the visible height is innerHeight less the stage's
            # top, so the flip is where that reaches the band plus two pitches.
            edge = math.ceil(g["innerTop"] + g["colHeight"] + 2 * g["cellHeight"])
            for scroll in (0, 90):
                for height in sorted({edge + k for k in range(-3, 4)} | {edge - scroll, edge - 2 * scroll}, reverse=True):
                    if not SHORTEST <= height <= TALLEST + 400:
                        continue
                    page.set_viewport_size({"width": PHONE["width"], "height": height})
                    _settle(page)
                    page.evaluate(
                        "(y) => { window.scrollTo(0, y); window.dispatchEvent(new Event('resize')); }", scroll
                    )
                    assert page.evaluate("() => window.scrollY") == scroll, "the page did not scroll"
                    r = page.evaluate(_GEOMETRY)
                    assert r["visible"] == r["innerHeight"] - r["innerTop"], r  # uncapped: the fold bounds it
                    assert r["keepsCols"] is _cols_say(r), (_percent(page), scroll, height, r)
                    checked += 1
        assert checked >= 100, checked

    def test_a_stage_missing_a_measured_element_is_left_alone_and_never_thrown_at(
        self, browser_page, host
    ) -> None:
        """The guard's operands: the rule cannot measure what is not there.

        ``keepCluesInView`` opens with ``if (!board || !rowClue || !colClue ||
        !cell) return``. Nothing in the shipped page reaches it (the board is
        drawn before the first call), so each operand is dead code until a
        stage is emptied of exactly one of them: this removes the row gutter,
        the column gutter and the cells in turn and re-asks the rule through a
        real ``resize`` handler. An unguarded read is a ``TypeError`` out of
        the handler, which Chromium reports as a ``pageerror``. (``!board`` is
        NOT separately testable and is declared in the operand table instead:
        the gutters and cells are built inside the one ``.player-board``, so
        a stage without the board has none of them and the other three
        operands answer first.)
        """
        page = browser_page
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for selector in ("th.player-clue.is-row", "th.player-clue.is-col", "td.player-cell"):
            _open_max(page, host)
            page.evaluate(
                "(sel) => { document.querySelectorAll(sel).forEach((el) => el.remove());"
                " window.dispatchEvent(new Event('resize')); }",
                selector,
            )
            _settle(page)
            assert errors == [], (selector, errors)

    def test_scrolling_the_page_only_ever_adds_reach_because_the_space_below_is_smaller_than_the_top(
        self, browser_page, host
    ) -> None:
        """C2-2's premise, asserted instead of observed once.

        ``keepCluesInView`` reads the stage as it is with the page at its top
        and calls that conservative: scrolling the page further shows MORE of
        the stage. That is true only while the space below the stage is
        smaller than the stage's own offset from the top; were it larger, a
        scrolled page could push the stage off the top of the screen and the
        reading taken at the top would over-state what is visible. So the
        inequality is measured over the whole viewport grid, with the page at
        its tallest, rather than left as a thing that happened to hold.
        """
        page = browser_page
        _open_max(page, host)
        worst = None
        count = 0
        for height in range(SHORTEST, TALLEST + 1, 70):
            for width in range(NARROWEST, WIDEST + 1, 40):
                page.set_viewport_size({"width": width, "height": height})
                _settle(page)
                r = page.evaluate(_GEOMETRY)
                below = r["docHeight"] - r["docBottom"]
                margin = r["innerTop"] - below
                count += 1
                worst = margin if worst is None else min(worst, margin)
                assert below < r["innerTop"], (width, height, below, r["innerTop"])
        assert count >= 150 and worst > 0, (count, worst)


@pytest.mark.browser
class TestPublicZoom_TheStageEndsAboveTheFold:
    """Cycle 2 (C2-1's second half): the stage's cap follows the real toolbar.

    ``--player-chrome-h`` once allowed ONE toolbar row, and the toolbar wraps:
    at 844x390 the stage's bottom sat 47 px below the fold and the page
    scrolled as well as the stage. The cap is now the stage's measured
    distance from the top of the page, so it follows whatever the chrome above
    it is — however many rows, whatever the heading does.
    """

    _FOLD = """() => {
      const stage = document.querySelector('[data-player-stage]');
      const probe = document.createElement('div');
      probe.style.paddingTop = 'var(--space-4)';
      document.body.append(probe);
      const air = parseFloat(getComputedStyle(probe).paddingTop);
      probe.remove();
      const y = window.scrollY;
      window.scrollTo(0, 0);
      const bottom = stage.getBoundingClientRect().bottom;
      window.scrollTo(0, y);
      return { bottom, innerHeight, air, clientHeight: stage.clientHeight, y };
    }"""

    def test_the_stage_bottom_is_inside_the_fold_at_every_viewport(self, browser_page, host) -> None:
        page = browser_page
        _open_max(page, host)
        rows = {}
        count = 0
        for height in range(SHORTEST, TALLEST + 1, 30):
            for width in range(NARROWEST, WIDEST + 1, 20):
                page.set_viewport_size({"width": width, "height": height})
                _settle(page)
                r = page.evaluate(self._FOLD)
                count += 1
                # Inside the fold, with the page's own air below it.
                assert r["bottom"] <= r["innerHeight"] - r["air"] + 0.01, (width, height, r)
                assert r["clientHeight"] > 0, (width, height, r)
                rows[(width, height)] = r
        assert count >= 600, count
        # The three landscape phones the owner named, by name.
        for width, height in ((844, 390), (852, 393), (874, 402)):
            page.set_viewport_size({"width": width, "height": height})
            _settle(page)
            r = page.evaluate(self._FOLD)
            assert r["bottom"] <= r["innerHeight"] - r["air"] + 0.01, (width, height, r)

    def test_the_sweep_can_fail_the_old_allowance_is_what_it_would_have_left(
        self, browser_page, host
    ) -> None:
        """The control: with the cap put back to one toolbar row, 844x390 is out."""
        page = browser_page
        _open_max(page, host)
        # Not 844x390 any more: the toolbar fits one row there since cycle 3, so
        # the old one-row allowance is RIGHT at that width. The control needs a
        # landscape width where the toolbar still wraps, and 812x375 (iPhone X,
        # XS, 11 Pro, 12 mini, 13 mini) is the declared residue: 2 rows, 96 px.
        page.set_viewport_size({"width": 812, "height": 375})
        _settle(page)
        page.evaluate(
            "() => document.querySelector('[data-player-stage]').style.setProperty("
            "'--player-above-h', 'calc(var(--space-4) + var(--text-xl) * 1.2 + var(--space-3)"
            " + 44px + var(--space-3))')"
        )
        r = page.evaluate(self._FOLD)
        assert r["bottom"] > r["innerHeight"], r

    def test_it_holds_with_the_page_scrolled_when_the_rule_is_re_asked(self, browser_page, host) -> None:
        """The cap is a position in PAGE coordinates, so a scrolled page must not move it."""
        page = browser_page
        _open_max(page, host)
        page.set_viewport_size(LANDSCAPE)
        page.evaluate("() => { document.body.style.paddingBottom = '600px'; }")
        _settle(page)
        page.evaluate("() => { window.scrollTo(0, 120); window.dispatchEvent(new Event('resize')); }")
        r = page.evaluate(self._FOLD)
        assert r["y"] == 120, r
        assert r["bottom"] <= r["innerHeight"] - r["air"] + 0.01, r

    def test_it_follows_a_toolbar_that_changes_height_with_no_resize(self, browser_page, host) -> None:
        """The ResizeObserver's reason: the Solved banner, a late font, a wrap."""
        page = browser_page
        _open_max(page, host)
        page.set_viewport_size(LANDSCAPE)
        _settle(page)
        before = page.evaluate(self._FOLD)
        page.add_style_tag(content=".player-toolbar { padding-bottom: 40px }")
        _settle(page, 4)
        after = page.evaluate(self._FOLD)
        assert after["clientHeight"] == before["clientHeight"] - 40, (before, after)
        assert after["bottom"] <= after["innerHeight"] - after["air"] + 0.01, after


# ==========================================================================
# Cycle 3 — the landscape toolbar is ONE row at the iPhone widths
# ==========================================================================


def _landscape_rule(css: str) -> tuple[int, str]:
    """``(breakpoint in px, body)`` of the one landscape media rule in ``css``."""
    rules = re.findall(
        r"@media \(orientation: landscape\) and \(max-width: (\d+)px\) \{(.*?)\n\}", css, re.S
    )
    assert len(rules) == 1, rules
    return int(rules[0][0]), rules[0][1]


@pytest.mark.browser
class TestPublicZoom_TheLandscapeToolbarIsOneRow:
    """The toolbar wrapped at 844x390 (cycle 2): the zoom group did not fit the
    first row, the toolbar took two, and the board lost two thirds of its rows.

    The owner chose to hide the percent in landscape. Measured alone it left the
    row 2.4 px short at 844, so the toolbar's gap drops from ``--space-3`` to
    ``--space-2`` as well; the 44 px targets are untouched. The media query
    needs a constant, so the constant is HELD to a measurement: the width at
    which the groups wrap with the readout shown is found in the page, and the
    breakpoint must cover it.
    """

    PHONES = ((844, 390), (852, 393), (874, 402))

    #: Rows the toolbar's three groups occupy, the toolbar's height, and the
    #: slack: the toolbar's content width less the groups and the gaps between.
    _TOOLBAR = """() => {
      const bar = document.querySelector('.player-toolbar');
      const groups = [...bar.querySelectorAll(':scope > .player-tools, :scope > .player-history, :scope > .player-zoom')];
      const boxes = groups.map((g) => g.getBoundingClientRect());
      const gap = parseFloat(getComputedStyle(bar).columnGap);
      const need = boxes.reduce((a, b) => a + b.width, 0) + gap * (groups.length - 1);
      const readout = document.querySelector('[data-player-zoom-readout]');
      const rb = readout.getBoundingClientRect();
      return {
        groups: groups.length,
        rows: new Set(boxes.map((b) => Math.round(b.top))).size,
        height: bar.getBoundingClientRect().height,
        gap, slack: bar.clientWidth - need,
        readoutBox: Math.max(rb.width, rb.height),
        readoutText: readout.textContent,
        readoutDisplay: getComputedStyle(readout).display,
        readoutVisibility: getComputedStyle(readout).visibility,
        readoutAriaHidden: readout.closest('[aria-hidden="true"]') !== null,
      };
    }"""

    #: Whole board rows inside the visible stage with the page and the stage at
    #: their tops: rows entirely below the column band and above the lower of
    #: the stage's bottom edge and the fold.
    _WHOLE_ROWS = """() => {
      const stage = document.querySelector('[data-player-stage]');
      const band = document.querySelector('th.player-clue.is-col').getBoundingClientRect().bottom;
      const edge = Math.min(stage.getBoundingClientRect().bottom, innerHeight);
      return [...document.querySelectorAll('.player-board tr')]
        .filter((tr) => tr.querySelector('td.player-cell'))
        .filter((tr) => { const r = tr.getBoundingClientRect(); return r.top >= band - 0.5 && r.bottom <= edge + 0.5; })
        .length;
    }"""

    def _read(self, page, width, height):
        page.set_viewport_size({"width": width, "height": height})
        _settle(page, 3)
        return page.evaluate(self._TOOLBAR)

    def test_the_three_iphone_widths_get_one_44px_row_with_room_to_spare(self, browser_page, host) -> None:
        page = browser_page
        _open_max(page, host)
        for width, height in self.PHONES:
            r = self._read(page, width, height)
            assert r["groups"] == 3, r
            assert r["rows"] == 1 and r["height"] == 44, (width, height, r)
            assert r["slack"] > 0, (width, height, r)
            # The targets were not shrunk to buy the room.
            for action in ("out", "in"):
                box = page.eval_on_selector(
                    f'[data-player-zoom-action="{action}"]',
                    "(el) => { const b = el.getBoundingClientRect(); return [b.width, b.height]; }",
                )
                assert box[0] >= 44 and box[1] >= 44, (width, height, action, box)

    def test_every_landscape_width_from_the_headline_phone_up_stays_one_row(self, browser_page, host) -> None:
        """The residue's edge: from 844 up there is no wrap to find."""
        page = browser_page
        _open_max(page, host)
        count = 0
        for width in range(844, 1000, 3):
            r = self._read(page, width, 390)
            count += 1
            assert r["rows"] == 1 and r["height"] == 44, (width, r)
        assert count >= 50, count

    def test_the_stage_regained_the_rows_the_wrap_took(self, browser_page, host) -> None:
        """Whole rows counted inside the visible stage: 1, 1, 2 wrapped; 3, 3, 3 now."""
        page = browser_page
        _open_max(page, host)
        for width, height in self.PHONES:
            self._read(page, width, height)
            assert page.evaluate(self._WHOLE_ROWS) >= 3, (width, height)

    def test_the_column_band_pins_again_at_the_headline_phone_at_100_percent(self, browser_page, host) -> None:
        page = browser_page
        _open_max(page, host)
        self._read(page, 844, 390)
        assert page.evaluate("() => document.querySelector('.player-board').classList.contains('keeps-cols')")

    def test_the_gap_is_the_second_spacing_step_in_landscape_and_the_third_otherwise(
        self, browser_page, host
    ) -> None:
        page = browser_page
        _open_max(page, host)
        probe = """(token) => {
          const p = document.createElement('div');
          p.style.paddingTop = `var(${token})`;
          document.body.append(p);
          const v = parseFloat(getComputedStyle(p).paddingTop);
          p.remove();
          return v;
        }"""
        landscape = self._read(page, 844, 390)
        assert landscape["gap"] == page.evaluate(probe, "--space-2"), landscape
        portrait = self._read(page, 390, 844)
        assert portrait["gap"] == page.evaluate(probe, "--space-3"), portrait

    def test_the_readout_is_hidden_visually_in_landscape_and_its_text_is_still_in_the_dom(
        self, browser_page, host
    ) -> None:
        page = browser_page
        _open_max(page, host)
        r = self._read(page, 844, 390)
        assert r["readoutBox"] <= 1, r
        # Not display:none, not visibility:hidden, not removed, not aria-hidden:
        # getZoom(), the tests and a screen reader still get the percent.
        assert r["readoutDisplay"] != "none" and r["readoutVisibility"] == "visible", r
        assert not r["readoutAriaHidden"], r
        bounds = _bounds(page)
        assert r["readoutText"].strip() == f"{bounds['min']:g}%", r
        _press(page, "in")
        after = page.evaluate(self._TOOLBAR)
        assert after["readoutText"].strip() == f"{bounds['min'] + bounds['step']:g}%", after
        assert page.evaluate("() => window.publicPlayer.getZoom()") == bounds["min"] + bounds["step"]

    def test_a_portrait_phone_keeps_its_readout(self, browser_page, host) -> None:
        page = browser_page
        _open_max(page, host)
        r = self._read(page, 390, 844)
        assert r["readoutBox"] > 1, r
        assert r["readoutText"].strip().endswith("%"), r
        # A portrait window narrower than the breakpoint is the case a bare
        # max-width query would have hidden it in.
        css = PUBLIC_CSS.read_text(encoding="utf-8")
        breakpoint, _ = _landscape_rule(css)
        assert 390 < breakpoint

    def test_the_breakpoint_covers_the_width_the_groups_wrap_at_with_the_readout_shown(
        self, browser_page, host
    ) -> None:
        """Measured, not copied: the landscape rule is taken out of the live
        sheet, then the page is narrowed from 1000 px until the toolbar wraps.
        The breakpoint must be at least that width, so adding a toolbar button
        (or widening anything in it) reds this until the constant is raised."""
        page = browser_page
        _open_max(page, host)
        css = PUBLIC_CSS.read_text(encoding="utf-8")
        breakpoint, body = _landscape_rule(css)
        removed = page.evaluate(
            """() => {
              let n = 0;
              for (const sheet of document.styleSheets) {
                for (let i = sheet.cssRules.length - 1; i >= 0; i--) {
                  const rule = sheet.cssRules[i];
                  if (rule.type === CSSRule.MEDIA_RULE && rule.conditionText.includes('orientation: landscape')) {
                    sheet.deleteRule(i);
                    n += 1;
                  }
                }
              }
              return n;
            }"""
        )
        assert removed == 1, removed
        r = self._read(page, 1000, 390)
        assert r["rows"] == 1 and r["readoutBox"] > 1 and r["gap"] == 12, r
        threshold = None
        for width in range(1000, 500, -1):
            r = self._read(page, width, 390)
            if r["rows"] > 1:
                threshold = width + 1  # the narrowest width that still held one row
                break
        assert threshold is not None
        # Covered: the rule is in force at every width the groups would wrap at.
        assert breakpoint >= threshold - 1, (breakpoint, threshold)
        # Not tuned upward either: no more than a few px of margin over the
        # measurement, so the readout is not hidden where it would have fit.
        assert breakpoint - threshold <= 16, (breakpoint, threshold)
        # And it is what the CSS says it is: the gap and the hidden pattern.
        assert "gap: var(--space-2)" in body and "clip-path: inset(50%)" in body, body
        assert "display: none" not in body, body


# ==========================================================================
# AC-5 — a pinch zooms and paints nothing, including the first finger's cell
# ==========================================================================


@pytest.mark.browser
class TestPublicZoom_APinchZoomsAndPaintsNothing:
    """AC-5."""

    #: The pinch's two separations, in px: it begins ``START`` apart and ends
    #: ``END`` apart, so the zoom it asks for is
    #: ``pinchZoom(ZOOM_MIN, START, END)`` — read from the module, never
    #: computed here.
    START, END = 80, 160

    def _pinch(self, page, row, col):
        """Two fingers, the first on cell ``(row, col)``, spreading :data:`START`
        to :data:`END` apart.

        **The first finger never moves**, and that is deliberate rather than
        incidental: with Region off the cells are ``touch-action: auto``, so
        Chromium's own gesture recognizer takes a moving touch over and fires
        ``pointercancel`` after the first ``pointermove``
        (``tests/test_public_player.py``'s ``_touch_drag`` measured exactly
        that and documents it). A cancelled first pointer would be dropped
        from ``play.js``'s pointer map before the second finger landed, and
        there would be no pinch to measure. So the spread is produced by the
        second finger alone.

        One deliberate jump rather than many small steps: Chromium coalesces
        touchmove delivery to its own rendering rate, so a long run of tiny
        synthetic steps sent back-to-back has it drop most of them —
        ``pinchZoom`` only ever reads the CURRENT distance, so one jump
        exercises the identical formula. ``tests/test_puzzle_solver_zoom.py``
        measured this on the admin side and says the same.
        """
        session = page.context.new_cdp_session(page)
        try:
            x, y = _cell_centre(page, row, col)
            # Every point of the gesture has to be inside the 390 px viewport
            # or the browser delivers it to nothing and the whole test passes
            # vacuously. Only six columns of a 30-cell board are visible
            # beside the row clue band at this width, which is why the cell
            # the pinch starts on is in the FIRST column and the second finger
            # spreads to its right.
            assert 0 < x and x + self.END < PHONE["width"], (x, self.END)
            _touch(session, "touchStart", [(x, y)])
            _touch(session, "touchStart", [(x, y), (x + self.START, y)])
            _touch(session, "touchMove", [(x, y), (x + self.END, y)])
            _touch(session, "touchEnd", [])
        finally:
            session.detach()
        page.wait_for_timeout(SETTLE_MS)  # see SETTLE_MS

    def test_with_region_off_the_pinch_zooms_and_the_first_fingers_cell_is_unmarked(
        self, browser_page, host
    ) -> None:
        """AC-5's sharp arm.

        With Region off a touch gesture paints nothing (``gesturePaints``), so
        the only mark a pinch could leave is the **tap** the first finger's
        own ``pointerup`` would otherwise have committed on the cell it went
        down on. The cell is named, and asserted still ``unknown``.
        """
        page = browser_page
        key = _open_max(page, host)
        save_key = page.evaluate("() => window.publicPlayer.saveKey")
        assert page.evaluate("() => window.publicPlayer.isRegion()") is False
        before = _solve_state(page, save_key)

        self._pinch(page, 6, 0)

        wanted = _module(page, "S.pinchZoom(S.ZOOM_MIN, arg[0], arg[1])", [self.START, self.END])
        assert _percent(page) == pytest.approx(wanted, abs=1), (_readout(page), wanted)
        assert wanted > _bounds(page)["min"], "the pinch asked for no change at all"
        assert _state(page, 6, 0) == "unknown", "the first finger's own cell was marked"
        after = _solve_state(page, save_key)
        assert after == before, {k: (before[k], after[k]) for k in before if before[k] != after[k]}
        assert after["save"] is None and key in save_key

        # And the page is still PLAYABLE afterwards, which is the other half
        # of what `beginPinch`'s `gesture = null` protects and the half that
        # nothing above sees. A stale `gesture` does not leak a mark — the
        # pinch's own pointerup path swallows both its pointers by a different
        # route — it blocks every LATER pointerdown, because the first line of
        # that handler is `if (gesture) return`. So the cost of dropping that
        # line is not a wrong mark but a board that cannot be marked again
        # until the page is reloaded.
        #
        # Measured rather than reasoned: mutation M7 removed exactly that line
        # and every assertion above this one stayed green.
        while _zoom_disabled(page, "out") != "true":
            _press(page, "out")
        _tap(page, 8, 2)
        assert _state(page, 8, 2) == "filled", "a tap after the pinch marked nothing"
        assert _solve_state(page, save_key)["done"] == before["done"] + 1

    def test_with_region_armed_the_second_finger_reverts_the_drag_and_commits_nothing(
        self, browser_page, host
    ) -> None:
        """AC-5's other arm: Region on, so the first finger really is painting.

        This is the one that measures ``beginPinch``'s revert rather than just
        its ``gesture = null``: the preview is asserted to have painted before
        the second finger lands, and to be gone after it.
        """
        page = browser_page
        _open_max(page, host)
        save_key = page.evaluate("() => window.publicPlayer.saveKey")
        page.click("[data-player-region]")
        assert page.evaluate("() => window.publicPlayer.isRegion()") is True
        before = _solve_state(page, save_key)

        session = page.context.new_cdp_session(page)
        try:
            x0, y0 = _cell_centre(page, 2, 1)
            _touch(session, "touchStart", [(x0, y0)])
            last = (x0, y0)
            for col in (2, 3, 4):
                last = _cell_centre(page, 2, col)
                _touch(session, "touchMove", [last])
            painting = _solve_state(page, save_key)
            assert painting["states"] != before["states"], "the drag's preview never painted"

            # The second finger is a POINT 60 px to the LEFT of the first, not
            # a far cell: at 390 px only six columns are visible, so a cell
            # chosen deep into the board lands outside the viewport and the
            # browser delivers the touch to nothing. It need not be on a cell
            # at all — the board's pinch rule reads the FIRST pointer's cell.
            # The spread then runs leftwards, into the clue band, so every
            # point of the gesture stays on screen; and the first finger does
            # not move again, so nothing re-enters the drag path.
            second = (last[0] - 60, last[1])
            assert second[0] - 60 > 0, second
            _touch(session, "touchStart", [last, second])
            reverted = _solve_state(page, save_key)
            assert reverted["states"] == before["states"], "the preview was not reverted"

            _touch(session, "touchMove", [last, (second[0] - 60, second[1])])
            _touch(session, "touchEnd", [])
        finally:
            session.detach()
        page.wait_for_timeout(SETTLE_MS)  # see SETTLE_MS

        # The spread doubled the pointers' separation, so the zoom the module
        # asks for is pinchZoom(ZOOM_MIN, 60, 120) — read from it, as every
        # other expectation in this file is.
        wanted = _module(page, "S.pinchZoom(S.ZOOM_MIN, 60, 120)")
        assert _percent(page) == pytest.approx(wanted, abs=1), (_readout(page), wanted)
        assert wanted > _bounds(page)["min"], "the pinch did not zoom, so AC-5's first half is vacuous"
        after = _solve_state(page, save_key)
        assert after["states"] == before["states"]
        assert (after["done"], after["undone"]) == (before["done"], before["undone"])
        assert after["save"] == before["save"]
        assert after["undo"] == "true", "something was recorded to undo"

        # Playable afterwards, for the reason arm one states at length: the
        # abandoned gesture has to be cleared or it blocks the next
        # pointerdown, and that is invisible to every assertion above.
        while _zoom_disabled(page, "out") != "true":
            _press(page, "out")
        _tap(page, 8, 2)
        assert _state(page, 8, 2) == "filled", "a tap after the pinch marked nothing"
        assert _solve_state(page, save_key)["done"] == before["done"] + 1


# ==========================================================================
# AC-6 — no request per zoom
# ==========================================================================


@pytest.mark.browser
class TestPublicZoom_NoRequestPerZoom:
    """AC-6 / ADR-0038/R2."""

    def test_every_zoom_interaction_issues_nothing_beyond_the_initial_get(
        self, browser_page, host
    ) -> None:
        """AC-6 — the recorder is installed before the page is opened, so the
        initial GET of the puzzle file is counted and named rather than
        excluded by timing. Every request after it is a failure.
        """
        page = browser_page
        url, _report, keys = host
        requests: list[tuple[str, str]] = []
        page.context.on("request", lambda request: requests.append((request.method, request.url)))

        _open_max(page, host)
        # The one request this page makes at all, so the recorder is proved live.
        assert any(
            method == "GET" and target.endswith(f"/puzzle/{keys['max']}.json")
            for method, target in requests
        ), requests
        assert all(method == "GET" for method, _ in requests), requests

        # The bounds are read BEFORE the watched slice begins, on purpose:
        # ``_module`` reaches them with a dynamic ``import('/solver_state.js')``,
        # which is itself a request. Taking the baseline after it is what keeps
        # the slice compared below the one the zoom could have caused.
        bounds = _bounds(page)
        rungs = int((bounds["max"] - bounds["min"]) / bounds["step"])
        after_load = len(requests)

        # Both buttons to both ends and two presses past each, so the clamped
        # no-op presses are in the walk too.
        for _ in range(rungs + 2):
            _press(page, "in")
        for _ in range(rungs + 2):
            _press(page, "out")
        assert _percent(page) == bounds["min"], "the button walk did not end where it claims"

        session = page.context.new_cdp_session(page)
        try:
            x, y = _cell_centre(page, 4, 0)
            assert x + 160 < PHONE["width"], x
            _touch(session, "touchStart", [(x, y)])
            _touch(session, "touchStart", [(x, y), (x + 80, y)])
            _touch(session, "touchMove", [(x, y), (x + 160, y)])
            _touch(session, "touchEnd", [])
        finally:
            session.detach()
        page.wait_for_timeout(SETTLE_MS)  # see SETTLE_MS

        assert _percent(page) > bounds["min"], "the pinch did not zoom, so its arm is vacuous"
        assert requests[after_load:] == [], requests[after_load:]


# ==========================================================================
# EC(ADR-0041/R3) — the arithmetic is the module's, in the source and in the page
# ==========================================================================

#: One ``import { … } from "…solver_state.js"`` statement's braces.
_IMPORT = re.compile(r"import\s*\{([^}]*)\}\s*from\s*\"[^\"]*solver_state\.js\"")

#: An ``export const NAME`` / ``export function NAME(params)`` in the module.
_EXPORTED_CONST = re.compile(r"^export const ([A-Z_]+) =", re.M)
_EXPORTED_FUNCTION = re.compile(r"^export function ([A-Za-z]+)\(([^)]*)\)", re.M)

#: The seven names the card is about, as the module spells them.
ZOOM_NAMES = ("ZOOM_MIN", "ZOOM_MAX", "ZOOM_STEP", "clampZoom", "stepZoom", "pinchZoom", "anchoredScroll")


def _markup(path: Path) -> str:
    """``path``'s markup with every HTML comment removed.

    Both pages carry long comments naming the very attributes asserted
    against below — ``play.html``'s own zoom block says why its readout has no
    percent in it — so a count over the raw file counts the prose too. Reading
    the markup alone is what makes "no percent literal in the markup" a claim
    about what the browser gets rather than about what a reader is told.
    """
    return re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)


def _rule_bodies(css: str, selector: str) -> list[str]:
    """Every declaration block in ``css`` opened by exactly ``selector``.

    A sheet may spell one selector more than once — ``admin.css`` declares
    ``.player-cell`` twice, once for its size and once for its input — so a
    reading that takes the first match reads whichever happens to come first.
    """
    return [
        match.group(1)
        for match in re.finditer(rf"^{re.escape(selector)} \{{(.*?)\}}", css, re.M | re.S)
    ]


def _imported(path: Path) -> set[str]:
    """Every name ``path`` imports from ``solver_state.js``, over all its
    import statements.

    ``solver.js`` splits its imports into nine statements, one per feature,
    and the zoom's is one of them — so a reading that took the first match
    would read the board transitions instead.
    """
    text = path.read_text(encoding="utf-8")
    found = _IMPORT.findall(text)
    assert found, f"{path.name} imports nothing from solver_state.js"
    return {
        name.strip()
        for clause in found
        for name in clause.replace("\n", " ").split(",")
        if name.strip()
    }


def _code(path: Path) -> str:
    """``path``'s source below its ``solver_state.js`` import, comments gone.

    Every assertion about "``play.js`` does not spell this" is made over this
    rather than the file: the header above the import explains at length why
    the arithmetic is not here, naming the very functions and constants being
    looked for, so a search over the raw text finds the explanation.
    """
    text = path.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))
    halves = code.split('} from "/solver_state.js";')
    assert len(halves) == 2, f"{path.name} does not import from /solver_state.js exactly once"
    return halves[1]


def _exports(text: str) -> dict[str, tuple[str, ...] | None]:
    """``{exported name: parameter names, or None for a constant}``."""
    found: dict[str, tuple[str, ...] | None] = {
        name: None for name in _EXPORTED_CONST.findall(text)
    }
    for name, params in _EXPORTED_FUNCTION.findall(text):
        found[name] = tuple(p.strip() for p in params.split(",") if p.strip())
    return found


class TestPublicZoom_TheArithmeticIsTheModules:
    """EC(ADR-0041/R3) — no bound, step or clamp is re-implemented in ``play.js``.

    This is the claim the card exists to make true, so it is held from two
    sides that fail for different reasons: the SOURCE (``play.js`` names none
    of the arithmetic itself and consumes exactly the surface the admin's own
    glue consumes) and the PAGE (every value the running page produces equals
    the module's answer for the same input, over a seeded sweep of the whole
    range).
    """

    def test_the_module_still_exports_all_seven_names_and_only_over_numbers(self) -> None:
        """The card's load-bearing premise, re-derived rather than carried —
        and ADR-0041/R2 established by SIGNATURE in the same reading.

        The four functions' parameter lists are read out of the module and
        held to a closed set of scalar names. None of them takes a board, a
        payload or a solution, so none *can* carry a solution cell; that is a
        stronger statement than any scan of what the page happens to pass.
        """
        text = STATE_MODULE.read_text(encoding="utf-8")
        exported = _exports(text)
        missing = [name for name in ZOOM_NAMES if name not in exported]
        assert missing == [], missing

        #: Every parameter any of the four zoom functions may take. Scalars,
        #: all of them — a name outside this set is a new kind of argument and
        #: reds here rather than being noticed later.
        scalars = {
            "value",
            "current",
            "direction",
            "startZoom",
            "startDistance",
            "currentDistance",
            "scroll",
            "anchor",
            "oldZoom",
            "newZoom",
        }
        for name in ("clampZoom", "stepZoom", "pinchZoom", "anchoredScroll"):
            params = exported[name]
            assert params is not None, name
            assert set(params) <= scalars, (name, params)
        for name in ("ZOOM_MIN", "ZOOM_MAX", "ZOOM_STEP"):
            assert exported[name] is None, name

        # And the control: the same reader over the same text with a board
        # parameter planted reports it, so "no board reaches these" is a
        # measurement and not a property of the regex.
        planted = text.replace(
            "export function clampZoom(value) {",
            "export function clampZoom(value, board) {",
        )
        assert planted != text
        assert set(_exports(planted)["clampZoom"]) - scalars == {"board"}

    def test_play_js_consumes_the_admins_own_zoom_surface_and_declares_none_of_it(self) -> None:
        """EC(ADR-0041/R3)'s source half.

        Two readings, and the second is the one that catches the mutant this
        card is about. A locally re-implemented ``clampZoom`` with the module's
        own bounds behaves identically, so no behavioural test can see it:
        what sees it is that ``play.js`` would then **declare** one of the
        module's seven names, which the second assertion refuses.

        The consumed set is derived from ``solver.js``'s own import rather
        than listed here: the admin's glue is the authority for which of the
        seven a *page* needs, and it needs five — ``ZOOM_STEP`` and
        ``clampZoom`` are used only inside the module (``stepZoom`` and
        ``pinchZoom`` clamp their own returns), so importing them here would
        be an unused name, which is a second place to look for a rule that
        lives in one.
        """
        admin_zoom = {name for name in _imported(ADMIN_SCRIPT) if name in ZOOM_NAMES}
        public = _imported(PUBLIC_SCRIPT)
        public_zoom = {name for name in public if name in ZOOM_NAMES}
        assert admin_zoom, "solver.js imports no zoom name, so this comparison is vacuous"
        assert public_zoom == admin_zoom, sorted(public_zoom ^ admin_zoom)

        body = _code(PUBLIC_SCRIPT)
        declared = [
            name
            for name in ZOOM_NAMES
            if re.search(rf"\b(?:function|const|let|var|class)\s+{name}\b", body)
        ]
        assert declared == [], declared

        # The control: the same reading over the same text with the card's own
        # defect planted — a local clampZoom carrying the module's bounds.
        mutant = body.replace(
            "  function syncZoom() {",
            "  function clampZoom(value) { return Math.min(300, Math.max(100, value)); }\n"
            "  function syncZoom() {",
            1,
        )
        assert mutant != body, "the plant did not apply, so the control measures nothing"
        assert [
            name
            for name in ZOOM_NAMES
            if re.search(rf"\b(?:function|const|let|var|class)\s+{name}\b", mutant)
        ] == ["clampZoom"]

    def test_play_js_spells_no_bound_step_or_clamp_of_its_own(self) -> None:
        """The same claim from the other direction: the three constants' VALUES
        do not appear in ``play.js``, and neither does a clamping expression.

        The values are read from the module rather than written here, so a
        changed range changes what this test looks for. Two exemptions, both
        named so neither can widen:

        * ``zoom / 100`` — the percent-to-multiplier conversion the CSS
          custom property needs. A unit, not a bound;
        * one ``Math.max(distanceBetween(…), 1)`` — ``pinchZoom``'s own
          documented precondition (it refuses a non-positive starting
          distance), guarded at the call site so two synthetic pointers at one
          point do not throw out of a listener. ``solver.js``'s own
          ``beginPinch`` carries the identical guard for the identical reason.
          ``Math.min`` has no such exemption and must not appear at all.
        """
        module = STATE_MODULE.read_text(encoding="utf-8")
        values = {}
        for name in ("ZOOM_MIN", "ZOOM_MAX", "ZOOM_STEP"):
            match = re.search(rf"^export const {name} = (\d+);", module, re.M)
            assert match is not None, name
            values[name] = match.group(1)
        assert len(set(values.values())) == 3, values

        body = _code(PUBLIC_SCRIPT)
        exempt = {values["ZOOM_MIN"]: "String(zoom / 100)"}
        for name, value in values.items():
            hits = re.findall(rf"[^0-9A-Za-z_.]{value}[^0-9]", body)
            allowed = body.count(exempt[value]) if value in exempt else 0
            assert len(hits) == allowed, (name, value, hits, allowed)

        assert "Math.min(" not in body
        assert body.count("Math.max(") == 1, body.count("Math.max(")
        assert "Math.max(distanceBetween(" in body
        for forbidden in ("clampZoom", "ZOOM_STEP"):
            assert forbidden not in body, forbidden

        # The control: the same reading with an unclamped step planted.
        mutant = body.replace('stepZoom(zoom, "in")', "zoom + 25", 1)
        assert mutant != body, "the plant did not apply"
        assert re.findall(rf"[^0-9A-Za-z_.]{values['ZOOM_STEP']}[^0-9]", mutant) != []

    def test_the_only_values_the_zoom_ever_takes_come_from_the_module(self) -> None:
        """EC(ADR-0041/R3)'s structural half: every value ``zoom`` is ever
        assigned arrived from ``stepZoom`` or ``pinchZoom``.

        The two readings together close the shape a value test cannot see. The
        variable is written in exactly two places — once from ``ZOOM_MIN`` at
        load, once from ``applyZoom``'s parameter — and every ``applyZoom``
        call passes the return of one of the module's two functions. So there
        is no path by which a percent this file computed itself can reach the
        page, which is a stronger statement than "the numbers happen to
        agree".

        The page half of the EC is carried by the browser classes above and is
        deliberately not repeated here: a third copy of the sweep would be a
        third copy of a guard. Their node ids are asserted present so the
        sentence cannot go stale in a rename.
        """
        body = _code(PUBLIC_SCRIPT)
        assignments = re.findall(r"(?<![=!<>])\bzoom = ([^;]+);", body)
        assert assignments == ["ZOOM_MIN", "nextPercent"], assignments

        calls = re.findall(r"applyZoom\(\s*([A-Za-z]+)\(", body)
        assert sorted(calls) == ["pinchZoom", "stepZoom", "stepZoom"], calls

        # The control: a percent computed here instead of asked for.
        mutant = body.replace('applyZoom(stepZoom(zoom, "in")', "applyZoom(zoom + 25", 1)
        assert mutant != body, "the plant did not apply"
        assert sorted(re.findall(r"applyZoom\(\s*([A-Za-z]+)\(", mutant)) == [
            "pinchZoom",
            "stepZoom",
        ]

        # The three that carry the page half, RESOLVED rather than counted in
        # this file's own text: a text count reads the sentence above as a
        # second definition of what it names.
        for owner, name in (
            (
                TestPublicZoom_TheBoundsComeFromTheModule,
                "test_no_sequence_of_presses_leaves_the_modules_range",
            ),
            (
                TestPublicZoom_TheAnchoredScrollIsTheModules,
                "test_the_stage_lands_where_anchored_scroll_says_on_both_axes",
            ),
            (
                TestPublicZoom_TheControlsChangeTheZoom,
                "test_zoom_in_reads_the_modules_next_step_and_grows_every_cell",
            ),
        ):
            assert callable(getattr(owner, name, None)), (owner.__name__, name)
        assert SWEEP_CASES >= 40, SWEEP_CASES

    def test_neither_page_invents_a_zoom_key_binding(self) -> None:
        """The card's item 5, held to BOTH pages so the match cannot rot.

        The admin's zoom buttons carry no ``aria-keyshortcuts`` and
        ``solver.js`` binds no key for zoom. This page matches that rather
        than inventing one. Asserted on both sides: the day the admin gains a
        zoom shortcut, this test reds and the public page's divergence becomes
        a decision somebody makes instead of a silence.
        """
        for path in (ADMIN_TEMPLATE, PUBLIC_PAGE):
            page_text = _markup(path)
            groups = re.findall(
                r"<button[^>]*data-player-zoom-action=\"(?:in|out)\"[^>]*>", page_text
            )
            assert len(groups) == 2, (path.name, groups)
            for button in groups:
                assert "aria-keyshortcuts" not in button, (path.name, button)
                assert "aria-label=" in button, (path.name, button)
        # The public page's own control group, with the hooks the admin uses.
        public = _markup(PUBLIC_PAGE)
        assert 'class="player-zoom"' in public and 'aria-label="Zoom"' in public
        assert public.count("data-player-zoom-readout") == 1
        # And no percent literal in the markup: the readout's only source is
        # the module's ZOOM_MIN, written by play.js before the toolbar is
        # revealed. A number here would be a second source (AC-1).
        assert "data-player-zoom-readout></span>" in public
        assert not re.search(r"\d+%", public), re.findall(r"\d+%", public)

    def test_the_cells_touch_action_diverges_from_the_admins_and_is_a_routed_finding(
        self,
    ) -> None:
        """The divergence this card found and did NOT decide, asserted rather
        than left in prose.

        ``admin.css`` gives its cells ``pan-x pan-y`` so the compositor cannot
        claim a two-finger touch as the browser's own page pinch-zoom before
        any JS runs — it reads ``touch-action`` ahead of every script, so no
        ``preventDefault`` can take a native pinch back. This page's cells are
        ``touch-action: auto``, and that is **pinned** by
        ``tests/test_public_player.py::test_the_brush_region_and_touch_bindings_are_the_modules``
        and consistent with ``play.html``'s own recorded decision to leave the
        browser's pinch on. Changing it is therefore an owner decision, not a
        worktree call, and this test is the place it gets declared.

        What does not depend on it: a pinch not PAINTING is pure JS
        bookkeeping (``beginPinch``), so AC-5 holds whatever the compositor
        does with the gesture.
        """
        admin = ADMIN_CSS.read_text(encoding="utf-8")
        public = PUBLIC_CSS.read_text(encoding="utf-8")
        admin_cell = _rule_bodies(admin, ".player-cell")
        public_cell = _rule_bodies(public, ".player-cell")
        assert admin_cell and public_cell, (len(admin_cell), len(public_cell))
        assert any("touch-action: pan-x pan-y" in body for body in admin_cell), admin_cell
        assert any("touch-action: auto" in body for body in public_cell), public_cell
        assert not any("touch-action: pan-x pan-y" in body for body in public_cell), public_cell
        # Both sheets agree on the Region-armed half, which is the one that
        # matters for marking, so the divergence is narrow and named.
        for text in (admin, public):
            assert ".player-board.is-region .player-cell { touch-action: none; }" in text

    def test_the_public_sheet_took_the_admins_zoom_rules_and_declares_the_multiplier(
        self,
    ) -> None:
        """The CSS half: the stage is the scrollport, the board carries the
        multiplier, and the group has the admin's three selectors.

        ``--player-zoom`` is asserted to be declared **once**, with the
        module's own neutral value, and to be read inside the cell's fitted
        clamp — so the multiplier cannot be declared and then never applied,
        which is the shape a reviewer would plant.
        """
        public = PUBLIC_CSS.read_text(encoding="utf-8")
        # Top-level rules only (a line-start match): the landscape media rule
        # restates the readout's selector indented, inside its own block.
        for selector in (".player-zoom {", ".player-zoom .btn {", ".player-zoom-readout {"):
            assert len(re.findall(rf"^{re.escape(selector)}", public, re.M)) == 1, selector
        assert public.count("--player-zoom: 1;") == 1
        board = re.search(r"^\.player-board \{(.*?)^\}", public, re.M | re.S)
        assert board is not None
        assert "var(--player-zoom)" in board.group(1), board.group(1)
        assert re.search(r"--player-cell:\s*calc\(clamp\(", board.group(1)), board.group(1)
        stage = re.search(r"^\.player-stage \{(.*?)^\}", public, re.M | re.S)
        assert stage is not None
        assert "overflow: auto" in stage.group(1)
        assert "max-height: calc(100svh - var(--player-chrome-h))" in stage.group(1)

        # The control: the multiplier declared but dropped from the clamp.
        mutant = board.group(1).replace(" * var(--player-zoom)", "")
        assert mutant != board.group(1)
        assert "var(--player-zoom)" not in mutant
