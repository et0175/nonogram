"""CARD-270 — a filled cell carries its own division, across every ink rule.

The defect (owner, 2026-10-22: *"Regions around wider lines (5x cell number)
don't have gray cell divisions around black cells"*). A filled cell's fill is
``--grid-ink`` and so is every MAJOR rule: the every-fifth
``.major-right``/``.major-below`` the player counts by, the board's outer
frame, and the clue gutters' edges. Ink on ink — a run of filled cells
crossing any of those merged into one blob. The thin dividers are
``--player-thin``, so the same run read fine across an ordinary border; the
defect class is *any ink rule between two ink fills*.

The fix is one declaration in ``admin.css``: ``.player-cell[data-state=
"filled"]`` draws an inset ``--player-thin`` hairline ``--player-rule`` wide
just inside its own box. It is neighbour-independent, so the division reads
the same across a thin rule, a major rule, the frame and a gutter edge.

**What is asserted here, and in which domain.** Two kinds of check, and they
are not interchangeable:

* the **mechanism** assertions (computed ``box-shadow``, computed border
  widths/colours, bounding boxes) are the regression net — they hold for any
  rendering of this stylesheet;
* the **pixel** assertions are one sample each, in a *declared* domain:
  Chromium, ``device_scale_factor`` 1 (asserted), page zoom 100 % and
  ``--player-zoom`` 1 (never set by this file), the viewport named by the test
  (1440x900 desktop, 390x844 phone), a 20x20 board whose cells are all marked
  filled, sampled along one named scanline. They claim nothing about other
  viewports, zoom levels or device pixel ratios, and they exist for exactly
  one reason: a computed style can agree with the mechanism while no visible
  band is produced.

Each pixel test carries its own control — the same scanline read with the
hairline suppressed (an injected ``box-shadow: none``), which must find **no**
light band across a major rule. That is the defect reproduced in-test, so a
green band reading is attributable to the shipped declaration and not to
something else on the board.

Browser tests (``@pytest.mark.browser``, pytest-playwright + Chromium,
ADR-0038/R7) refuse LOUDLY when the browser is absent — the ``browser_type``
and ``browser_page`` fixtures of ``tests/test_puzzle_solver_page.py``
``pytest.fail`` with the install instruction rather than skipping, because a
silent green skip is this repo's known failure mode.
"""

from __future__ import annotations

import io

import pytest

from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)
# CARD-271 review cycle 1 (F-002): solver.js's own resize debounce, derived
# from the file that declares it. An element screenshot makes the page fire
# `resize`, so the length of that debounce is how long a capture's wake lasts
# — see _quiet.
from tests.test_puzzle_solver_clues import RESIZE_SETTLE as _RESIZE_SETTLE

#: The board every pixel test marks up: 20 x 20, uniquely solvable, and it
#: has at least one empty cell — so marking EVERY cell filled is never the
#: solution, which keeps the solved flash (it animates ``background``) and the
#: success frame out of every screenshot. Asserted, not assumed.
SIDE = 20
GRID = _unique_grid(SIDE, SIDE, seed=270)
assert any(not cell for row in GRID for cell in row), (
    "GRID has no empty cell, so an all-filled board would be SOLVED and the "
    "solved flash would animate the pixels these tests sample"
)

DESKTOP = (1440, 900)
PHONE = (390, 844)

#: The two viewports every pixel figure in this file is measured at, as one
#: list so a test cannot be parametrized on a subset of them by accident.
#: Desktop cells are 24.88 CSS px, phone cells 14.39 — the phone number the
#: card's Standards section asks about by name.
_VIEWPORTS = [(DESKTOP, "desktop"), (PHONE, "phone")]

#: How far two colours may differ per channel and still count as the same
#: one. The board renders these rules without antialiasing (every sampled
#: pixel measured so far is exact), so this is slack, not a fudge factor.
_TOLERANCE = 8


# --------------------------------------------------------------------------
# Driving the page
# --------------------------------------------------------------------------

_FILL_ALL = """() => {
  const { width, height } = window.puzzlePlayer.payload;
  const cells = new Array(width * height).fill('filled');
  window.puzzlePlayer.setBoard(Object.freeze({ width, height, cells: Object.freeze(cells) }));
}"""

_SET_BOARD = """(cells) => {
  const { width, height } = window.puzzlePlayer.payload;
  window.puzzlePlayer.setBoard(Object.freeze({ width, height, cells: Object.freeze(cells) }));
}"""

#: Two 8 x 8 swatches pinned to the viewport's top-left corner, painted with
#: the two tokens this card is about. The reference colours are read back out
#: of a screenshot rather than parsed from a computed style, so a colour-space
#: serialisation (``color-mix()`` computes to ``color(srgb ...)``) can never
#: silently become the thing under test.
_SWATCHES = """() => {
  // The VALUE is read off .player-stage, which is where --player-rule and
  // --player-thin are declared: `background: var(--player-thin)` on a body
  // child resolves to nothing at all (the property is not in scope there),
  // and the swatch would then show whatever is behind it. _tokens() asserts
  // the four come back distinct, so that failure can never pass as a colour.
  const stage = getComputedStyle(document.querySelector('.player-stage'));
  for (const [prop, x] of [['--grid-ink', 0], ['--player-thin', 8],
                           ['--grid-paper', 16]]) {
    const d = document.createElement('div');
    d.setAttribute('data-card270-swatch', prop);
    d.style.cssText = 'position: fixed; left: ' + x + 'px; top: 0; width: 8px;'
      + ' height: 8px; z-index: 2147483647;';
    d.style.background = stage.getPropertyValue(prop).trim();
    document.body.append(d);
  }
}"""

#: The two rule widths, in px, read off probes inside ``.player-stage`` (the
#: element the two custom properties are declared on), plus the two facts the
#: pixel domain rests on.
_RULE_WIDTHS = """() => {
  const stage = document.querySelector('.player-stage');
  const probe = (prop) => {
    const d = document.createElement('div');
    d.style.cssText = 'position: absolute; height: 0; width: var(' + prop + ');';
    stage.append(d);
    const px = parseFloat(getComputedStyle(d).width);
    d.remove();
    return px;
  };
  return {
    rule: probe('--player-rule'),
    major: probe('--player-rule-major'),
    dpr: window.devicePixelRatio,
    zoom: parseFloat(getComputedStyle(
      document.querySelector('.player-board')).getPropertyValue('--player-zoom')),
  };
}"""

#: Every cell's box, in coordinates relative to the TABLE's own box — which is
#: what an element screenshot of ``.player-board`` is in. Read after the
#: screenshot, in one evaluate, so a scroll between the two cannot shift them.
_GEOMETRY = """() => {
  const table = document.querySelector('.player-board');
  const t = table.getBoundingClientRect();
  const cells = {};
  for (const td of document.querySelectorAll('td.player-cell')) {
    const r = td.getBoundingClientRect();
    cells[td.dataset.row + ',' + td.dataset.col] = {
      x: r.left - t.left, y: r.top - t.top, w: r.width, h: r.height,
      majorRight: td.classList.contains('major-right'),
      majorBelow: td.classList.contains('major-below'),
    };
  }
  return { w: t.width, h: t.height, cells };
}"""

#: Suppresses *any* cell hairline without editing the stylesheet: the control
#: every pixel reading is compared against.
#:
#: The selector is deliberately **wider** than the shipped rule's
#: (``.player-cell``, not ``.player-cell[data-state="filled"]``), and that is
#: load-bearing rather than tidiness. Scoped to the filled state it could not
#: suppress a hairline that had broadened onto some *other* state, so a
#: comparison of "shipped" against "suppressed" on a board with no filled cell
#: was equal by construction — the mutation sat in both readings and the
#: blank-board arm of :func:`test_the_rules_against_paper_are_untouched` could
#: not fail in the direction its own message named (CARD-270 review 1, F-001,
#: proved with the REACHES-BLANK and BROADEN-UNKNOWN mutants). Unscoped, the
#: control subtracts every ``box-shadow`` any cell has, whatever put it there,
#: so the comparison reds on a hairline that reaches a cell this card's rule
#: does not select. Under the shipped stylesheet it is exactly as strong as
#: the narrow form on every board the file samples: the three other callers
#: mark every cell filled, so the two selectors match the same 400 cells.
_SHADOW_OFF = """() => {
  const style = document.createElement('style');
  style.id = 'card270-shadow-off';
  style.textContent =
    '.player-cell { box-shadow: none !important; }';
  document.head.append(style);
}"""

_BOXES = """() => {
  const out = [];
  for (const el of document.querySelectorAll(
      '.player-board, td.player-cell, th.player-clue, th.player-corner')) {
    const r = el.getBoundingClientRect();
    out.push([el.className, el.dataset.row ?? '', el.dataset.col ?? '',
              el.dataset.line ?? '', Math.round(r.left * 100), Math.round(r.top * 100),
              Math.round(r.width * 100), Math.round(r.height * 100)]);
  }
  return out;
}"""


def _image(png: bytes):
    from PIL import Image

    return Image.open(io.BytesIO(png)).convert("RGB")


def _open_filled(page, live, viewport):
    """A 20 x 20 board at ``viewport`` with every cell marked filled."""
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    _open(page, live, live.store(GRID))
    page.evaluate(_FILL_ALL)
    page.evaluate(_SWATCHES)
    assert page.locator(".player-board.is-solved").count() == 0, (
        "the all-filled board reads as SOLVED, so the solved flash is "
        "animating the pixels this test samples"
    )
    return _tokens(page)


def _tokens(page) -> dict:
    """The reference colours (out of a screenshot) and the two rule widths."""
    shot = _image(page.screenshot(scale="css"))
    widths = page.evaluate(_RULE_WIDTHS)
    colours = {
        "ink": shot.getpixel((4, 4)),
        "thin": shot.getpixel((12, 4)),
        "paper": shot.getpixel((20, 4)),
    }
    # A swatch that failed to paint shows what is behind it, and two reference
    # colours that are secretly the same turn every reading below into a
    # tautology. This is the control for that: the four tokens are visibly
    # different colours, so they must come back visibly different.
    assert len(set(colours.values())) == 3, colours
    for name, colour in colours.items():
        others = [c for n, c in colours.items() if n != name]
        assert not any(_is(colour, other) for other in others), colours
    return {**colours, **widths}


#: Take the clue gutters off the scrollport for the duration of a capture
#: (CARD-271), and put them back.
#:
#: A kept gutter is ``position: sticky`` against ``.player-stage``, so unless
#: the stage happens to be at the far end of that axis the gutter is PAINTED
#: away from its flow position — and an element screenshot of the table
#: ignores the stage's own overflow clip, so the band then lands in the
#: capture over cells the player cannot see at that scroll at all (measured
#: at 390 px on this file's 20 x 20: 113 px of cells, columns 12 to 19,
#: reading --color-surface instead of the fill). Every reading in this file
#: is about the table's own RULES, so it is taken of the table alone.
#:
#: Sticking is layout-neutral, so this changes what is PAINTED and nothing
#: else — and :func:`_board` now carries its own control for that instead of
#: citing one (CARD-271 review cycle 1, F-002). The citation here was
#: tests/test_puzzle_solver_clues.py
#: ``TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted``, whose
#: ``test_sticking_changes_neither_the_band_nor_the_overflow`` asserts the
#: band, the overflow and the port — three terms ``_GEOMETRY`` does not read.
#: ``_GEOMETRY`` reads the table's own width and height and every cell's
#: offset from the table's rect, so had sticking ever moved a cell relative to
#: the table, that control could not have reddened and the citation would have
#: gone on licensing a capture taken in one class state against geometry read
#: in another. ADR-0039/R1: a claim whose control cannot fail is narrative,
#: not coverage.
#:
#: The classes go straight back, and so does the dataset the restore needs:
#: ``keptClasses`` is deleted on the way out, so no later assertion in the
#: same test sees an attribute this file invented either.
#: The stash it leaves is read back on the way out, and a MISSING stash is a
#: signal rather than a crash: ``redraw()`` replaces the whole table, so a
#: stash that is gone means the table it was written on is gone. See
#: :func:`_quiet` for the measurement of how that happens and :func:`_board`
#: for what is done about it. (The implementation round's version of this
#: helper met the same condition as ``TypeError: Cannot read properties of
#: undefined (reading 'split')``, with nothing to say which table it had
#: been handed.)
_UNSTICK = """(on) => {
  const table = document.querySelector('.player-board');
  if (!on) {
    const kept = [...table.classList].filter((c) => c.startsWith('is-keeping-'));
    table.dataset.keptClasses = kept.join(' ');
    table.classList.remove(...kept);
    return true;
  }
  const stashed = table.dataset.keptClasses;
  if (stashed === undefined) return false;
  table.classList.add(...stashed.split(' ').filter(Boolean));
  delete table.dataset.keptClasses;
  return true;
}"""


#: The draw mark solver.js leaves behind, one per board built — the only
#: observable that says whether the table under a reading is still the table
#: that reading was taken of.
_DRAWS = "() => performance.getEntriesByName('nonogram-player-board-draw').length"


def _quiet(page):
    """Wait out any debounced redraw already pending, and answer the draw count.

    Needed because of a measured interaction between this file's captures and
    CARD-212's resize listener, and it is a property of the two, not of
    CARD-271: **a Playwright element screenshot makes the page fire
    ``resize``**. Measured on this file's own 20 x 20 at 390 x 844 —
    ``innerWidth``/``innerHeight`` never change (390 x 844 before and after),
    one ``resize`` event is recorded, the draw count is 1 immediately after
    the capture and 2 once ``RESIZE_SETTLE`` has passed. So every capture
    leaves a redraw landing a moment later, and a redraw replaces the whole
    table.

    Left alone that makes the pair of readings in :func:`_board` unsound
    rather than merely flaky: ``png`` describes the table the screenshot was
    taken of and the geometry afterwards can describe its replacement. Waiting
    here, before anything is read, is what keeps a capture window clean; the
    draw-count comparison in :func:`_board` is what proves it was.
    """
    page.wait_for_timeout(4 * _RESIZE_SETTLE)
    return page.evaluate(_DRAWS)


def _board(page):
    """An element screenshot of the table, and the cell boxes inside it.

    The geometry is read TWICE — once inside the unstuck window the capture is
    taken in, once after the classes are back — and the two readings are
    asserted equal. That assertion IS this helper's licence to mix the two
    states, held here rather than cited elsewhere (F-002). Measured on this
    file's own board and viewport the two agree exactly (20 x 20 at 390 x 844,
    the stage scrolled to mid-axis: table 471.453125 x 380.03125 both ways, 0
    of 400 cells differing). If sticking ever did move a cell relative to the
    table, every pixel reading in this file would be comparing a capture
    against geometry that does not describe it — the one way this helper can
    be wrong, and now the one thing it checks.

    Everything is read inside ONE board generation, and that is asserted
    rather than hoped: :func:`_quiet` waits out the redraw the previous
    capture left pending, and the draw count is compared across the window
    afterwards. Without it the pair of readings straddles a redraw — not a
    flake to retry past but a reading of two different tables, which is the
    very thing the geometry comparison below exists to rule out.
    """
    drew = _quiet(page)
    page.evaluate(_UNSTICK, False)
    try:
        loose = page.evaluate(_GEOMETRY)
        png = page.locator(".player-board").screenshot(scale="css")
    finally:
        restored = page.evaluate(_UNSTICK, True)
    assert restored and page.evaluate(_DRAWS) == drew, (
        f"the board was redrawn inside the capture window "
        f"(draws {drew} -> {page.evaluate(_DRAWS)}, stash restored: "
        f"{restored}), so this capture does not describe the table the "
        f"geometry below is read off")
    geometry = page.evaluate(_GEOMETRY)
    assert loose == geometry, (
        "sticking moved the table's own geometry, so the capture taken with "
        "the gutters off and the geometry returned with them on do not "
        "describe the same board")
    # The other half of the same claim, and the one the docstring above used
    # to make without checking: this helper leaves nothing of its own on the
    # page for a later assertion in the same test to read.
    assert page.evaluate(
        "document.querySelector('.player-board').dataset.keptClasses") is None, (
        "_UNSTICK left data-kept-classes on the table")
    return _image(png), geometry


def _is(pixel, reference) -> bool:
    return max(abs(a - b) for a, b in zip(pixel, reference)) <= _TOLERANCE


def _differing(one, other) -> int:
    """How many pixels of two same-sized images are **visibly** different.

    Byte identity is the right test for "nothing moved" (one changed pixel is
    a change), but it is the wrong test for "something moved": two renderings
    of the *same* computed style can differ by a pixel or two of ±1 at the
    board's outer edge, and a control that only asks "did the bytes differ"
    is bought by that noise. Measured, on a blank board under this card's
    REACHES-BLANK mutant: 32 pixels at the board's left and right extremes,
    each differing by at most 1 per channel, between two renderings whose
    computed ``box-shadow`` is the same string on all 400 cells. So a
    difference is counted only past :data:`_TOLERANCE`, the same window every
    colour reading in this file uses.
    """
    from PIL import ImageChops

    assert one.size == other.size, (one.size, other.size)
    # ``tobytes`` rather than ``getdata``: both images are RGB, so this is
    # three bytes per pixel, and it is not on Pillow's deprecation list.
    channels = ImageChops.difference(one, other).tobytes()
    assert len(channels) == 3 * one.size[0] * one.size[1], len(channels)
    return sum(
        1 for at in range(0, len(channels), 3)
        if max(channels[at:at + 3]) > _TOLERANCE
    )


def _centre(cell):
    return cell["x"] + cell["w"] / 2, cell["y"] + cell["h"] / 2


def _scan(image, start, end) -> list[tuple[int, int, int]]:
    """The pixels along a horizontal or vertical segment, both ends included."""
    x0, y0 = round(start[0]), round(start[1])
    x1, y1 = round(end[0]), round(end[1])
    assert x0 == x1 or y0 == y1, "a scan is horizontal or vertical"
    width, height = image.size
    if y0 == y1:
        step = 1 if x1 >= x0 else -1
        points = [(x, y0) for x in range(x0, x1 + step, step)]
    else:
        step = 1 if y1 >= y0 else -1
        points = [(x0, y) for y in range(y0, y1 + step, step)]
    return [image.getpixel(p) for p in points if 0 <= p[0] < width and 0 <= p[1] < height]


def _runs(pixels, reference) -> list[int]:
    """The lengths of the maximal runs of ``reference``-coloured pixels."""
    lengths, current = [], 0
    for pixel in pixels:
        if _is(pixel, reference):
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    return lengths


def _first_unlike(pixels, reference):
    """The first pixel of ``pixels`` that is not ``reference``, or None."""
    return next((p for p in pixels if not _is(p, reference)), None)


def _pair_across(geometry, axis):
    """Two adjacent cells either side of a fifth-line major rule on ``axis``.

    Read off the DOM (``.major-right`` / ``.major-below``, which ``solver.js``
    assigns) rather than from a hard-coded column index, so the sample follows
    the board the renderer actually drew.
    """
    key = "majorRight" if axis == "x" else "majorBelow"
    for name, cell in geometry["cells"].items():
        row, col = (int(n) for n in name.split(","))
        if not cell[key]:
            continue
        nxt = (f"{row},{col + 1}" if axis == "x" else f"{row + 1},{col}")
        if nxt in geometry["cells"] and 5 <= row < SIDE - 5 and 5 <= col < SIDE - 5:
            return cell, geometry["cells"][nxt]
    raise AssertionError(f"no .{key} cell with a neighbour on the {axis} axis")


def _pair_plain(geometry, axis):
    """Two adjacent cells either side of an ORDINARY (thin) rule."""
    key = "majorRight" if axis == "x" else "majorBelow"
    for name, cell in geometry["cells"].items():
        row, col = (int(n) for n in name.split(","))
        if cell[key]:
            continue
        nxt = (f"{row},{col + 1}" if axis == "x" else f"{row + 1},{col}")
        if nxt in geometry["cells"] and 5 <= row < SIDE - 5 and 5 <= col < SIDE - 5:
            return cell, geometry["cells"][nxt]
    raise AssertionError(f"no ordinary rule on the {axis} axis")


def _between(image, first, second, axis):
    """The scanline from the first cell's centre to the second's."""
    a, b = _centre(first), _centre(second)
    return _scan(image, a, (b[0], a[1]) if axis == "x" else (a[0], b[1]))


# ==========================================================================
# AC-1 — filled cells divide across the every-fifth major rules
# ==========================================================================


@pytest.mark.browser
class TestSolverFifthRule_FilledCellsDivideAcrossMajorRules:
    """AC-1. Two adjacent filled cells either side of a fifth-line major rule,
    on both axes, are visually separated.

    The mechanism assertion is the regression net; the pixel sample is the one
    check that the mechanism actually produces a visible band, and it states
    its domain in the method's own docstring.
    """

    def test_every_filled_cell_carries_the_inset_hairline(self, browser_page, live) -> None:
        """The mechanism, on every filled cell of the board: one inset
        ``box-shadow``, ``--player-thin``-coloured, ``--player-rule`` wide, no
        offset and no blur. Read as a computed style, so it holds for any
        rendering of this stylesheet and not only for the sampled viewport."""
        tokens = _open_filled(browser_page, live, DESKTOP)
        look = browser_page.evaluate(
            """() => {
              const stage = document.querySelector('.player-stage');
              const probe = document.createElement('div');
              probe.style.cssText = 'position: absolute; height: 0;'
                + ' width: var(--player-rule); background-color: var(--player-thin);';
              stage.append(probe);
              const s = getComputedStyle(probe);
              const want = s.backgroundColor + ' 0px 0px 0px ' + s.width + ' inset';
              probe.remove();
              const got = new Set([...document.querySelectorAll(
                'td.player-cell[data-state="filled"]')].map(
                  (td) => getComputedStyle(td).boxShadow));
              return { want, got: [...got],
                       count: document.querySelectorAll(
                         'td.player-cell[data-state="filled"]').length };
            }"""
        )
        assert look["count"] == SIDE * SIDE, look["count"]
        assert look["got"] == [look["want"]], look
        assert tokens["rule"] > 0 and tokens["major"] == 2 * tokens["rule"], tokens

    @pytest.mark.parametrize("axis", ["x", "y"])
    @pytest.mark.parametrize("viewport,name", _VIEWPORTS, ids=["desktop", "phone"])
    def test_a_light_band_reads_across_the_fifth_rule(
        self, browser_page, live, viewport, name, axis
    ) -> None:
        """DOMAIN of every figure below: Chromium, the **named** viewport
        (1440x900 desktop or 390x844 phone), device pixel ratio 1 (asserted),
        page zoom 100 % and ``--player-zoom`` 1 (asserted), a 20 x 20 board
        with every cell marked filled, sampled along the single scanline
        joining the centres of the two cells either side of one fifth-line
        major rule. No claim is made about any other viewport, zoom level or
        device pixel ratio.

        Both viewports are sampled because the card's Standards section names
        the phone cell explicitly ("state what it measures at 14 px"), and the
        figures are the only thing that can say a hairline did not round away
        there: 24.88 px cells at desktop, 14.39 px at phone, and the band
        widths below are read off the tokens at the viewport under test rather
        than hard-coded, so this arm reds on a hairline that collapses at one
        size and not the other (CARD-270 review 1, F-002).

        Shipped: leaving either fill, the first pixel that is not ink is
        ``--player-thin``; the rule's own ink core between the two hairlines is
        still ``--player-rule-major`` wide.

        Control: the same scanline with ``box-shadow: none`` forced on every
        cell finds NO ``--player-thin`` pixel at all — the defect, reproduced,
        which is what makes the reading above attributable to the hairline.
        """
        tokens = _open_filled(browser_page, live, viewport)
        assert tokens["dpr"] == 1, tokens["dpr"]
        assert tokens["zoom"] == 1, tokens["zoom"]
        image, geometry = _board(browser_page)
        first, second = _pair_across(geometry, axis)
        pixels = _between(image, first, second, axis)

        assert _is(pixels[0], tokens["ink"]), pixels[:4]
        assert _is(pixels[-1], tokens["ink"]), pixels[-4:]
        assert _runs(pixels, tokens["thin"]) == [tokens["rule"], tokens["rule"]], (
            f"{name}/{axis}: the two fills are not separated by two "
            f"{tokens['rule']}px --player-thin hairlines: {pixels}"
        )
        # The major rule's ink core, between the two hairlines, is untouched.
        light = [i for i, p in enumerate(pixels) if _is(p, tokens["thin"])]
        assert light[-1] - light[0] - 1 == tokens["major"], (
            f"{name}/{axis}: the ink between the hairlines is "
            f"{light[-1] - light[0] - 1}px, not --player-rule-major: {pixels}"
        )

        browser_page.evaluate(_SHADOW_OFF)
        without, geometry = _board(browser_page)
        first, second = _pair_across(geometry, axis)
        assert _runs(_between(without, first, second, axis), tokens["thin"]) == [], (
            f"{name}/{axis}: a --player-thin band reads across the major rule "
            f"with the hairline suppressed, so the band above is not the "
            f"hairline's"
        )

    @pytest.mark.parametrize("axis", ["x", "y"])
    @pytest.mark.parametrize("viewport,name", _VIEWPORTS, ids=["desktop", "phone"])
    def test_an_ordinary_rule_reads_the_same_way(
        self, browser_page, live, viewport, name, axis
    ) -> None:
        """Same domain as above, at both viewports for the same reason. The
        card's claim is that the division reads *uniformly* — across a thin
        rule as well as a major one — so the thin rule is sampled too: between
        two filled cells it is one contiguous light band of hairline + rule +
        hairline, and leaving either fill the first non-ink pixel is
        ``--player-thin``."""
        tokens = _open_filled(browser_page, live, viewport)
        assert tokens["dpr"] == 1, tokens["dpr"]
        image, geometry = _board(browser_page)
        first, second = _pair_plain(geometry, axis)
        pixels = _between(image, first, second, axis)

        assert _is(pixels[0], tokens["ink"]) and _is(pixels[-1], tokens["ink"]), pixels
        assert _first_unlike(pixels, tokens["ink"]) is not None, pixels
        assert _is(_first_unlike(pixels, tokens["ink"]), tokens["thin"]), pixels
        assert _runs(pixels, tokens["thin"]) == [3 * tokens["rule"]], (
            f"{name}/{axis}: an ordinary rule between two filled cells is not "
            f"hairline + rule + hairline: {pixels}"
        )


# ==========================================================================
# AC-2 — the frame and the clue gutters too
# ==========================================================================


@pytest.mark.browser
class TestSolverFifthRule_EdgesAndGuttersToo:
    """AC-2. The same division reads where a filled cell meets the board's
    outer frame and the clue gutters' edges — the other two places the rule is
    ``--grid-ink`` and so was ink on ink."""

    @pytest.mark.parametrize("viewport,name", _VIEWPORTS, ids=["desktop", "phone"])
    def test_leaving_a_filled_cell_at_the_boards_edge_the_first_pixel_is_the_hairline(
        self, browser_page, live, viewport, name
    ) -> None:
        """DOMAIN: Chromium, the named viewport, device pixel ratio 1
        (asserted), zoom 100 %, a 20 x 20 all-filled board. Sampled: from each
        edge cell's centre outward, perpendicular to that edge, as far as the
        cell's own border box plus the major rule beyond it.

        Shipped: for every cell on the board's outer ring, on all four sides,
        the first pixel that is not ink is ``--player-thin``. That covers the
        clue-gutter edges (the gutter draws a ``--grid-ink`` major rule against
        the cell) and the outer frame, whichever the layout put on that side.

        Control: with the hairline suppressed, at least one of those edges
        reports a first-non-ink pixel that is NOT ``--player-thin`` — the
        defect, reproduced.
        """
        tokens = _open_filled(browser_page, live, viewport)
        assert tokens["dpr"] == 1, tokens["dpr"]
        image, geometry = _board(browser_page)

        #: The board's outer ring: every cell that has at least one side on
        #: the frame, with the side(s) that are on it.
        ring = [(0, col, "top") for col in range(SIDE)]
        ring += [(SIDE - 1, col, "bottom") for col in range(SIDE)]
        ring += [(row, 0, "left") for row in range(SIDE)]
        ring += [(row, SIDE - 1, "right") for row in range(SIDE)]

        def _edges(img, geo):
            out = {}
            for row, col, side in ring:
                cell = geo["cells"][f"{row},{col}"]
                cx, cy = _centre(cell)
                reach = cell["w"] / 2 + tokens["major"] + 1
                end = {
                    "left": (cx - reach, cy), "right": (cx + reach, cy),
                    "top": (cx, cy - reach), "bottom": (cx, cy + reach),
                }[side]
                pixels = _scan(img, (cx, cy), end)
                out[(row, col, side)] = (pixels[0], _first_unlike(pixels, tokens["ink"]))
            return out

        edges = _edges(image, geometry)
        assert len(edges) == 4 * SIDE, len(edges)
        wrong = [
            f"{where}: starts {start}, first non-ink {found}"
            for where, (start, found) in sorted(edges.items())
            if not _is(start, tokens["ink"]) or found is None or not _is(found, tokens["thin"])
        ]
        assert wrong == [], f"{name}: {wrong[:6]}"

        browser_page.evaluate(_SHADOW_OFF)
        without, geometry = _board(browser_page)
        broken = [
            where
            for where, (_start, found) in _edges(without, geometry).items()
            if found is None or not _is(found, tokens["thin"])
        ]
        assert broken != [], (
            f"{name}: every board edge still reads a --player-thin division with "
            f"the hairline suppressed, so this test is not measuring the hairline"
        )

    def test_the_sampled_edges_really_include_a_clue_gutter(self, browser_page, live) -> None:
        """The edge sweep above is only AC-2 if a clue gutter really sits
        against one of the edges it walks. A row gutter has to be flush
        against the first or last cell COLUMN and a column gutter against the
        first or last cell ROW, measured off the live boxes — so a layout that
        stopped drawing a gutter beside the grid fails here instead of quietly
        narrowing the sweep to the frame alone."""
        _open_filled(browser_page, live, DESKTOP)
        flush = browser_page.evaluate(
            """() => {
              const cell = (r, c) => document.querySelector(
                'td.player-cell[data-row="' + r + '"][data-col="' + c + '"]'
                ).getBoundingClientRect();
              const near = (a, b) => Math.abs(a - b) <= 3;
              const first = cell(0, 0), last = cell(19, 19);
              const out = { row: false, col: false };
              for (const box of document.querySelectorAll('th.player-clue')) {
                const r = box.getBoundingClientRect();
                if (box.classList.contains('is-row')) {
                  if (near(r.right, first.left) || near(r.left, last.right)) out.row = true;
                } else if (near(r.bottom, first.top) || near(r.top, last.bottom)) {
                  out.col = true;
                }
              }
              return out;
            }"""
        )
        assert flush["row"], "no row-clue gutter is flush against the grid's side"
        assert flush["col"], "no column-clue gutter is flush against the grid's top or bottom"


# ==========================================================================
# AC-3 — nothing else moves
# ==========================================================================


@pytest.mark.browser
class TestSolverFifthRule_GeometryAndOtherMarksUnchanged:
    """AC-3. The cell geometry, the rules against paper, the empty dot, the
    "?" mark and the hint's own ring are what they were."""

    @pytest.mark.parametrize("viewport,name", _VIEWPORTS, ids=["desktop", "phone"])
    def test_the_hairline_takes_no_part_in_layout(
        self, browser_page, live, viewport, name
    ) -> None:
        """Two arms, and the first is the one that can see a mechanism that
        *does* move layout.

        1. Every cell on a board whose cells are all FILLED is still exactly
           ``--player-cell`` wide and tall — the size a probe inside the board
           resolves that token to — and all 400 agree. Measured against the
           token rather than against the board's other state, so a mechanism
           that widened filled cells (a padding, a min-width, a border) is
           caught whether or not it is a ``box-shadow``.
        2. Every box on the board — the table, every cell, every clue box and
           corner — is identical with the hairline shipped and with it forced
           off, to a hundredth of a px.

        Arm 2 alone would be narrative: forcing ``box-shadow: none`` can only
        undo a ``box-shadow``, so a layout-moving replacement sits in BOTH
        readings and the comparison reports no difference (measured: the
        MOVES-LAYOUT mutant survives arm 2 and is killed by arm 1).
        """
        _open_filled(browser_page, live, viewport)
        measured = browser_page.evaluate(
            """() => {
              const table = document.querySelector('.player-board');
              const probe = document.createElement('div');
              probe.style.cssText =
                'position: absolute; height: 0; width: var(--player-cell);';
              table.querySelector('td.player-cell').append(probe);
              const token = parseFloat(getComputedStyle(probe).width);
              probe.remove();
              const sizes = new Set();
              for (const td of document.querySelectorAll('td.player-cell')) {
                const r = td.getBoundingClientRect();
                sizes.add(r.width.toFixed(2) + 'x' + r.height.toFixed(2));
              }
              return { token, sizes: [...sizes],
                       cells: document.querySelectorAll('td.player-cell').length };
            }"""
        )
        assert measured["cells"] == SIDE * SIDE, measured
        assert measured["token"] > 0, measured
        want = f"{measured['token']:.2f}x{measured['token']:.2f}"
        assert measured["sizes"] == [want], (
            f"{name}: a filled board's cells are {measured['sizes']}, not the "
            f"{want} --player-cell resolves to — something moved the geometry"
        )

        shipped = browser_page.evaluate(_BOXES)
        browser_page.evaluate(_SHADOW_OFF)
        without = browser_page.evaluate(_BOXES)

        assert len(shipped) > SIDE * SIDE, len(shipped)
        assert shipped == without, f"{name}: the hairline moved the board's layout"

    def test_the_rules_against_paper_are_untouched(self, browser_page, live) -> None:
        """DOMAIN: Chromium, 1440x900, device pixel ratio 1 (asserted), zoom
        100 %, a 20 x 20 board left BLANK (every cell undecided), compared as
        whole ``.player-board`` element screenshots.

        A blank board must be pixel-for-pixel what it was, and it must stay
        that way under a control that can actually subtract something: the
        comparison is against ``_SHADOW_OFF``, which suppresses ``box-shadow``
        on **every** ``.player-cell`` and not only on the filled ones. So the
        two readings differ the moment any cell on a board with no filled cell
        carries a hairline — whichever rule put it there. The ink core of a
        fifth-line major rule is still ``--player-rule-major`` px wide against
        paper.

        *Why the control is wider than the shipped rule.* Scoped to
        ``[data-state="filled"]`` this arm could not fail: a hairline that had
        broadened onto a non-filled state is by definition not the rule such a
        control turns off, so the mutation sat in both readings and the
        comparison was equal by construction. Measured, with the hairline
        moved onto ``.player-cell`` (REACHES-BLANK) and with a second rule
        added for ``[data-state="unknown"]`` (BROADEN-UNKNOWN): with the narrow
        control both mutants left this arm PASS; with the wide one both red it
        (CARD-270 review 1, F-001).

        The premise is asserted over the whole board, not sampled: all 400
        cells read ``data-state="unknown"``. Were a future change to open the
        board with cells already decided, this arm would stop being the
        blank-board claim it is named for, and it fails rather than drifting.

        Note what this does NOT assert, because the pixels will not carry it:
        a rule at a fractional offset is antialiased, and ``--player-thin`` is
        28 % ink over paper — which is *exactly* the colour a 28 %-covered ink
        edge blends to. "No ``--player-thin`` pixel on a blank board" is
        therefore not a statement the sampler can make, and it is not made.

        Control: forcing the hairline onto EVERY cell instead must change at
        least one pixel **per cell** by more than ``_TOLERANCE`` — otherwise
        this is comparing nothing. Byte inequality is deliberately not the
        test here, although it is the right test for the arm above: under
        REACHES-BLANK the board already carries the hairline everywhere, and
        forcing it on again still changed 32 pixels by ±1 at the board's left
        and right extremes (measured; the computed ``box-shadow`` is the same
        string on all 400 cells in both renderings). A control a rounding
        artefact can satisfy is not a control, so this one counts visibly
        changed pixels and reds under both mutants as well.
        """
        browser_page.set_viewport_size({"width": DESKTOP[0], "height": DESKTOP[1]})
        _open(browser_page, live, live.store(GRID))
        browser_page.evaluate(_SWATCHES)
        tokens = _tokens(browser_page)
        assert tokens["dpr"] == 1, tokens["dpr"]

        #: The arm's premise, over the board rather than spot-checked: every
        #: cell is undecided, so "blank" is measured and not assumed.
        states = browser_page.evaluate(
            """() => {
              const tally = {};
              for (const td of document.querySelectorAll('td.player-cell')) {
                tally[td.dataset.state] = (tally[td.dataset.state] ?? 0) + 1;
              }
              return tally;
            }"""
        )
        assert states == {"unknown": SIDE * SIDE}, (
            f"the board this arm calls BLANK carries {states}, so the "
            f"comparison below is not the blank-board claim"
        )

        shipped, geometry = _board(browser_page)

        for axis in ("x", "y"):
            first, second = _pair_across(geometry, axis)
            pixels = _between(shipped, first, second, axis)
            assert _is(pixels[0], tokens["paper"]), (axis, pixels[:4])
            assert _runs(pixels, tokens["ink"]) == [tokens["major"]], (axis, pixels)

        browser_page.evaluate(_SHADOW_OFF)
        without, _ = _board(browser_page)
        assert shipped.tobytes() == without.tobytes(), (
            "a blank board is not what it was with EVERY cell's box-shadow "
            "forced off, so a hairline is reaching cells that are not filled"
        )

        browser_page.evaluate(
            """() => {
              document.getElementById('card270-shadow-off').remove();
              const style = document.createElement('style');
              style.textContent = '.player-cell { box-shadow: inset 0 0 0'
                + ' var(--player-rule) var(--player-thin) !important; }';
              document.head.append(style);
            }"""
        )
        everywhere, _ = _board(browser_page)
        #: One pixel per cell is the floor a hairline on 400 cells cannot miss,
        #: and it is two orders of magnitude above the ±1 edge noise two
        #: renderings of the SAME computed style were measured to produce.
        changed = _differing(shipped, everywhere)
        assert changed >= SIDE * SIDE, (
            f"a hairline forced onto every cell changes only {changed} pixels "
            f"of a blank board by more than {_TOLERANCE} per channel, so the "
            f"comparison above would not have seen one either"
        )

    def test_no_other_cell_state_gains_a_shadow(self, browser_page, live) -> None:
        """A board carrying all four cell states: only the filled one has a
        ``box-shadow``. The empty dot and the "?" glyph still take their
        colours from their own tokens and their size from the cell."""
        browser_page.set_viewport_size({"width": DESKTOP[0], "height": DESKTOP[1]})
        _open(browser_page, live, live.store(GRID))
        #: Four cells away from every fifth line (the major lines are after
        #: columns/rows 4, 9 and 14), so each one's content box is the cell
        #: minus one --player-rule on each of two sides and the percentage
        #: geometry below has one denominator.
        where = {"unknown": (6, 6), "filled": (6, 7), "empty": (7, 6), "maybe": (7, 7)}
        cells = ["unknown"] * (SIDE * SIDE)
        for state, (row, col) in where.items():
            cells[row * SIDE + col] = state
        browser_page.evaluate(_SET_BOARD, cells)
        look = browser_page.evaluate(
            """(where) => {
              const stage = document.querySelector('.player-stage');
              const probe = document.createElement('div');
              probe.style.cssText = 'position: absolute; height: 0; width: 0;'
                + ' color: var(--color-accent); background-color: var(--color-text-secondary);';
              stage.append(probe);
              const p = getComputedStyle(probe);
              const tokens = { accent: p.color, secondary: p.backgroundColor };
              probe.remove();
              const out = { tokens, shadow: {}, state: {}, dot: null, glyph: null };
              for (const [state, [row, col]] of Object.entries(where)) {
                const td = document.querySelector(
                  'td.player-cell[data-row="' + row + '"][data-col="' + col + '"]');
                out.state[state] = td.dataset.state;
                out.shadow[state] = getComputedStyle(td).boxShadow;
                const after = getComputedStyle(td, '::after');
                const inner = td.clientWidth;
                if (state === 'empty') {
                  out.dot = { w: after.width, h: after.height,
                              colour: after.backgroundColor,
                              radius: after.borderRadius, inner };
                }
                if (state === 'maybe') {
                  out.glyph = { colour: after.color, size: after.fontSize,
                                weight: after.fontWeight,
                                cell: td.getBoundingClientRect().width };
                }
              }
              return out;
            }""",
            where,
        )
        assert look["state"] == {state: state for state in where}, look["state"]
        assert [state for state, shadow in look["shadow"].items() if shadow == "none"] == [
            "unknown", "empty", "maybe",
        ], look["shadow"]
        assert look["shadow"]["filled"] != "none"
        assert look["dot"]["colour"] == look["tokens"]["secondary"], look["dot"]
        assert look["dot"]["radius"] == "50%", look["dot"]
        for side in ("w", "h"):
            assert abs(float(look["dot"][side].rstrip("px"))
                       - 0.28 * look["dot"]["inner"]) < 0.5, look["dot"]
        assert look["glyph"]["colour"] == look["tokens"]["accent"], look["glyph"]
        assert look["glyph"]["weight"] == "600", look["glyph"]
        assert abs(float(look["glyph"]["size"].rstrip("px"))
                   - max(12.0, 0.6 * look["glyph"]["cell"])) < 0.5, look["glyph"]

    def test_a_hinted_filled_cell_still_wears_the_hints_own_ring(
        self, browser_page, live
    ) -> None:
        """The edge of this card's claim. ``.is-hinted`` sets a ``box-shadow``
        of its own and has the same specificity as the filled rule, so the one
        that comes LATER in ``admin.css`` wins outright — a ``box-shadow`` is
        replaced, never merged. This drives Hint until a cell that is both
        filled and hinted exists and asserts that cell shows CARD-183's paper
        ring, not this card's hairline: the hint's look is unchanged, and a
        filled cell is the only case where the two rules can collide."""
        browser_page.set_viewport_size({"width": DESKTOP[0], "height": DESKTOP[1]})
        _open(browser_page, live, live.store(GRID))
        hint = browser_page.locator('[data-player-action="hint"]')
        for _ in range(12):
            hint.click()
            hinted = browser_page.locator('td.player-cell.is-hinted[data-state="filled"]')
            if hinted.count():
                break
        else:
            pytest.fail("12 hints revealed no FILLED cell, so the collision is untested")

        look = hinted.first.evaluate(
            """async (td) => {
              await Promise.all(td.getAnimations().map((a) => a.finished));
              const stage = document.querySelector('.player-stage');
              const probe = document.createElement('div');
              probe.style.cssText = 'position: absolute; height: 0;'
                + ' width: var(--player-rule-major);'
                + ' background-color: var(--grid-paper); color: var(--player-thin);';
              stage.append(probe);
              const p = getComputedStyle(probe);
              const paper = p.backgroundColor, thin = p.color;
              const major = parseFloat(p.width);
              probe.remove();
              return { shadow: getComputedStyle(td).boxShadow,
                       want: paper + ' 0px 0px 0px ' + (2 * major) + 'px inset',
                       thin };
            }"""
        )
        assert look["shadow"] == look["want"], look
        assert look["thin"] not in look["shadow"], look
