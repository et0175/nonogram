"""CARD-386 / CARD-399 - the public site's ``/play/<key>``: the admin's own player
files on the public data, no override layer.

CARD-385 made ``solver.js`` / ``solver_state.js`` run with no solution grid.
CARD-386 assembled a site that uses them; since CARD-399 that is the ONLY
assembly (``assemble()`` and ``scripts/assemble_player_site.py`` with no
flag) and the separate ``player/play.js`` is gone. The cells below were the
preview's; they now describe the default tree.
The acceptance criteria and where each is held:

* AC-1 - ``TestSharedUi_ThePageRuns``: a real puzzle plays to the Solved banner
  with zero page errors and zero non-GET requests, the page links no stylesheet
  beyond the project's base sheet / tokens / ``admin.css``; and
  ``TestSharedUi_TheCard385SweepOnThisTree`` runs CARD-385's whole gesture sweep
  (every control, the solve, the reload) against THIS assembled tree.
* AC-2 - ``TestSharedUi_ByteIdentity``: the table covers the four admin files,
  the tree's copies equal the sources, an edited copy reds, and the
  assembly-time equality check fires on a copy that is not identical.
* AC-3 - ``TestSharedUi_TheServedTreeCarriesNoAnswer``: no solution string in
  any served file, the puzzle JSON key set is exactly ``clues, height, key,
  tier, width``, a plant that adds a solution key or string reds, the copied JS
  has no network call, and AC-392's own scan of the tree is empty.
* AC-4 - ``TestSharedUi_TheDefaultIsUnchanged``: two default runs are byte
  identical, the driver's command line and its end-to-end tree equal the
  in-process assembly, and the retired flags are refused.
* AC-5 - ``TestSharedUi_TheDoorsKeepTheirShapes``: ``/library`` and ``/b/<slug>``
  are the ``player/`` sources' bytes and work in Chromium; the preview
  server serves all three URL shapes.

Beside them: the F-2 usage line (no sentence about Check), F-3 (Hint stays on
and says why where no line decides), the banner's neutral name, the fresh start
(old ``nonogram-public:`` saves are not read), and the refusals of the shell
and of the two CLIs.

Bootstrap is NOT in the repository (G-3). Since CARD-394 the page needs none:
it links the project's own ``player/shared-ui-base.css``, held to the real
Bootstrap's measured computed styles and rectangles by
``tests/test_player_base_css.py``. CARD-399 retired the ``--bootstrap``
override with the preview (``tests/test_player_base_css.py``'s optional
real-file arm swaps the published ``base.css`` instead).
"""

from __future__ import annotations

import http.server
import importlib.util
import json
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import tests.test_player_public_mode as sweep_module
from tests.test_player_public_mode import (  # noqa: F401 - fixtures are used by name
    Watch,
    action,
    browser_page,
    browser_type,
    cell,
    clues_of,
    disabled,
    flat,
    network_calls,
    public_exhausted_sentence,
    solution_leaks,
    CONTROL_STEPS,
    _random_grid,
    _unique,
    solve_to_the_end,
    states,
    sweep_problems,
    touch_page,
)
from tests.test_public_player import REPO_ROOT, _bundle_payload, _leaky_title, assembler
from tests.test_public_player_pages import (
    BOOK_ORDER,
    BOOK_TITLE_SERVED,
    COPIED_JS_RESIDUE,
    PAGE_GRIDS,
    PAGES_SETTLE_MS,
    _open_pages,
    _serve,
    _tiles,
    driver,
    scan_site,
    write_pages_bundle,
)

#: CARD-385's sweep boards (10 x 8 and 7 x 6) are below the supported extent
#: (``limits.MIN_SIZE``), and the assembler rightly refuses to serve them, so
#: this tree's two boards are the smallest SUPPORTED equivalents, found by
#: seeded search and held to the same two properties by the first test below.
SWEEP_GRID = _random_grid(10, 10, seed=1, density=0.6)
STALL_GRID = _random_grid(10, 10, seed=3095, density=0.4)

STATIC = REPO_ROOT / "src" / "nonogram" / "admin" / "static"

#: The four files the card names; the table under test must be exactly these.
FOUR_FILES = {
    "src/nonogram/admin/static/solver.js": "solver.js",
    "src/nonogram/admin/static/admin.css": "admin.css",
    "src/nonogram/admin/static/solver_state.js": "solver_state.js",
    "src/nonogram/admin/static/tokens.css": "tokens.css",
}

# --------------------------------------------------------------------------
# The fixtures: a bundle and the assembled tree
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fragment() -> str:
    """The admin template, rendered by the assembler (the one source of markup)."""
    return assembler.render_shared_ui_fragment()


def write_extra_puzzle(root: Path, grid, tier: str) -> str:
    payload = _bundle_payload(grid, tier=tier, title=_leaky_title(grid))
    path = root / "puzzle" / f"{payload['key']}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload["key"]


@pytest.fixture
def bundle(tmp_path):
    """The pages corpus (one book, leaky puzzle titles) plus the sweep's two boards."""
    root = tmp_path / "bundle"
    keys, slug = write_pages_bundle(root, order=BOOK_ORDER)
    keys["sweep"] = write_extra_puzzle(root, SWEEP_GRID, "medium")
    keys["stall"] = write_extra_puzzle(root, STALL_GRID, "easy")
    return root, keys, slug


def preview_of(bundle_root: Path, out: Path, fragment: str, tmp_path: Path, **kwargs):
    """The assembled tree, built from ``fragment`` (the rendered admin markup)."""
    return assembler.assemble(bundle_root, out, fragment=fragment, **kwargs)


@pytest.fixture
def preview(bundle, fragment, tmp_path):
    root, keys, slug = bundle
    report = preview_of(root, tmp_path / "preview", fragment, tmp_path)
    return report, keys, slug


@pytest.fixture
def preview_host(preview):
    report, keys, slug = preview
    url, stop = _serve(report.site_dir)
    try:
        yield url, report, keys, slug
    finally:
        stop()


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def open_play(page, url: str, key: str) -> None:
    page.goto(f"{url}/play/{key}", timeout=PAGES_SETTLE_MS)
    page.wait_for_function("() => window.puzzlePlayer !== undefined", timeout=PAGES_SETTLE_MS)


def open_play_at(page, url: str, address: str) -> None:
    """CARD-436: ``open_play`` for an address that carries a query string."""
    page.goto(f"{url}{address}", timeout=PAGES_SETTLE_MS)
    page.wait_for_function("() => window.puzzlePlayer !== undefined", timeout=PAGES_SETTLE_MS)


#: CARD-436 requirement 5: what the board would lose if anything above it
#: grew. The stage's own height is what the board is drawn into, and its top
#: is what solver.js's measureStageTop writes to --player-stage-top, so the
#: two together say whether a row above the board cost it anything. Rounded
#: to 1/100 px: the layout engine's own rounding is 1/64.
_ROOM = """() => {
  const box = (selector) => document.querySelector(selector).getBoundingClientRect();
  const round = (n) => Math.round(n * 100) / 100;
  const stage = box('.player-stage');
  return {
    stage: round(stage.height),
    top: round(stage.top + window.scrollY),
    head: round(box('.player-head').height),
    toolbar: round(box('.player-toolbar').height),
  };
}"""

#: CARD-436: what the reader actually sees of the way back, so "promoted" is
#: a measurement and not an attribute that claims it. The look is read off the
#: inner span, which is where the pill is; the three BOXES are read beside it,
#: because cycle 1 of this card's review found two things no attribute and no
#: ``inner_text()`` can see:
#:
#: * ``link`` vs ``words`` — the <a>'s own rectangle against its span's. The
#:   first implementation put the row's ``flex: 1 1 0`` on the <a> itself, so
#:   the anchor was as wide as the row's free space (875 px for 221 px of
#:   words at 1280 x 720) and ~654 px of apparently empty header navigated
#:   away from the board. The geometry is on a non-clickable slot <span> now,
#:   and ``slot`` is that box, so the slack and the hit area are separable;
#: * ``whole`` vs ``painted`` — ``scrollWidth`` against ``clientWidth``.
#:   ``inner_text()`` returns the string whether or not it is painted, so it
#:   passes identically against ``text-overflow: ellipsis``; these two say
#:   how much of the book's name the reader actually sees.
_LOOK = """() => {
  const link = document.querySelector('[data-player-book]');
  const name = link.querySelector('span');
  const style = getComputedStyle(name);
  const round = (n) => Math.round(n * 100) / 100;
  return {
    weight: style.fontWeight,
    background: style.backgroundColor,
    border: style.borderTopColor + ' ' + style.borderTopWidth,
    link: round(link.getBoundingClientRect().width),
    words: round(name.getBoundingClientRect().width),
    slot: round(link.parentElement.getBoundingClientRect().width),
    painted: name.clientWidth,
    whole: name.scrollWidth,
  };
}"""


class Opened:
    """The two attributes CARD-385's sweep reads off its server object."""

    def __init__(self, url: str, root: Path) -> None:
        self.url, self.root = url, root


def step_hint_on_a_bigger_board(page, ctx):
    """CARD-385's ``step_hint`` with its press bound scaled to this board.

    That step presses at most ``3 * 90`` times, enough for its own 10 x 8
    board; the smallest SUPPORTED board has 100 cells and needs more
    (measured: "the ladder ran out of presses"). Everything else it asserts is
    the same, so the other steps are used as they are.
    """
    if not disabled(action(page, "reset")):
        action(page, "reset").click()
        page.locator('[data-player-confirm="accept"]').click()
    hint = action(page, "hint")
    assert not disabled(hint)
    before = states(page)
    hint.click()
    assert states(page) == before, "rung 1 changes no cell"
    assert page.locator("#puzzle-player-explain").inner_text() != ""
    hint.click()
    assert states(page) == before, "rung 2 changes no cell"
    hint.click()
    assert states(page) != before, "rung 3 reveals a cell"
    assert page.locator("[data-player-hints]").inner_text() == "1"

    def finished() -> bool:
        return (disabled(hint) or page.locator("#puzzle-player-solved").is_visible()
                or page.locator("#puzzle-player-explain").inner_text() == public_exhausted_sentence())

    for _ in range(3 * len(SWEEP_GRID) * len(SWEEP_GRID[0])):
        if finished():
            break
        hint.click()
    assert finished(), "the ladder ran out of presses"
    hint.click(force=True)  # beyond: a locked Hint is inert, an exhausted one repeats its sentence


STEPS = {**CONTROL_STEPS, "data-player-action=hint": step_hint_on_a_bigger_board}


#: CARD-413 (owner finding 2026-11-07, item 9): each control the "How to play"
#: text names, by the bold word that starts its bullet, and where it is.
HOWTO_CONTROLS = {
    "Tap": "td.player-cell",
    "Brush": ".player-tool-trigger",
    "Region": "[data-player-region]",
    "Hint": '[data-player-action="hint"]',
    "Check": '[data-player-action="check"]',
    "Probe": "[data-player-probe]",
    # "− / + or Fit": all three (review cycle 1, F-602). Fit is the readout,
    # a control only while there is a Fit to go to, so it is the readout.
    "Zoom": ('[data-player-zoom-action="out"]', '[data-player-zoom-action="in"]', "[data-player-zoom-readout]"),
}


def howto_problems(page) -> list[str]:
    """CARD-413 AC-3 (it replaces CARD-386 F-2's usage-line check): every
    sentence of the "How to play" text is true on this page — each control
    its bullets name (the bold word) is on the page and visible, and the text
    names no control the page lacks. Read from the DOM, opened first."""
    page.evaluate("document.getElementById('puzzle-player-hint').open = true")
    names = page.evaluate(
        "[...document.querySelectorAll('#puzzle-player-hint li > strong:first-child')].map((s) => s.textContent.trim())")
    problems = []
    if not names:
        problems.append("the text names no control")
    for name in names:
        selectors = HOWTO_CONTROLS.get(name)
        if selectors is None:
            problems.append(f"names {name!r}, which no control here is")
            continue
        for selector in (selectors,) if isinstance(selectors, str) else selectors:
            if not page.locator(selector).first.is_visible():
                problems.append(f"names {name}, but the page has no visible {selector}")
    return problems


def test_the_two_boards_are_what_the_sweep_needs() -> None:
    """The same properties as CARD-385's ``test_the_sweep_puzzles_are_what_the_sweep_needs``."""

    def forces(clue, length):
        runs = [n for n in clue if n > 0]
        return not runs or length - (sum(runs) + len(runs) - 1) < max(runs)

    assert _unique(SWEEP_GRID) and _unique(STALL_GRID)
    rows, columns = clues_of(SWEEP_GRID)
    assert any(forces(c, 10) for c in rows + columns), "Hint must have a deduction from the blank board"
    rows, columns = clues_of(STALL_GRID)
    assert not any(forces(c, 10) for c in rows + columns), "no line may decide a cell from the blank board"
    assert not any(c == [0] for c in rows + columns)


# ==========================================================================
# AC-1 - the page runs the admin's solver.js with the admin's admin.css
# ==========================================================================


@pytest.mark.browser
class TestSharedUi_ThePageRuns:
    # AC-383: the model's verifying ref, tests/test_player_shared_ui_site.py::test_a_real_puzzle_plays_to_the_solved_banner (CARD-399: moved here from play.js's twin).
    def test_a_real_puzzle_plays_to_the_solved_banner(self, browser_page, preview_host) -> None:
        """AC-1."""
        url, report, keys, _ = preview_host
        key = keys["sweep"]
        watch = Watch(browser_page)
        open_play(browser_page, url, key)
        assert browser_page.locator("td.player-cell").count() == len(SWEEP_GRID) * len(SWEEP_GRID[0])
        solve_to_the_end(browser_page, SWEEP_GRID)
        assert browser_page.locator("#puzzle-player-solved").is_visible()
        assert watch.problems() == []
        assert watch.non_get == []
        # Only the tree's own files, and every one of them a GET.
        requested = {u.removeprefix(url) for u in watch.urls}
        assert requested == {
            f"/play/{key}", "/base.css", "/tokens.css", "/admin.css", "/solver.js",
            "/solver_state.js", f"/puzzle/{key}.json",
        }, sorted(requested)

    def test_the_page_links_no_stylesheet_beyond_the_admins_and_has_no_style_element(
        self, browser_page, preview_host
    ) -> None:
        """G-1 and CARD-394 AC-1: three sheets (the project's, tokens, admin.css), no override layer,
        no third-party file in the tree, and no licence header or URL in the project's sheet."""
        url, report, keys, _ = preview_host
        open_play(browser_page, url, keys["sweep"])
        sheets = browser_page.evaluate("[...document.styleSheets].map(s => new URL(s.href).pathname)")
        assert sheets == ["/base.css", "/tokens.css", "/admin.css"], sheets
        assert browser_page.evaluate("document.querySelectorAll('style').length") == 0
        html = (report.site_dir / "play" / "index.html").read_text(encoding="utf-8")
        assert re.findall(r'rel="stylesheet" href="([^"]+)"', html) == [
            "/base.css", "/tokens.css", "/admin.css"]
        assert [p for p in tree_bytes(report.site_dir) if "bootstrap" in p.lower()] == []
        base = (report.site_dir / "base.css").read_text(encoding="utf-8")
        assert not re.search(r"https?:|//[a-z]|/\*!|@import|url\(", base), "no URL, import or licence header"

    def test_the_header_the_tab_and_the_banner_name_come_from_the_puzzle_file(
        self, browser_page, preview_host
    ) -> None:
        url, report, keys, _ = preview_host
        key = keys["sweep"]
        open_play(browser_page, url, key)
        assert browser_page.locator(".player-head h1").inner_text() == "Puzzle 10×10"
        assert browser_page.locator(".player-tier .badge").inner_text() == "MEDIUM"
        assert browser_page.title() == "Puzzle 10×10 · MEDIUM - Nonogram"
        # The hue is the design token's, not a second copy of the hex.
        assert "--color-tier-medium" in browser_page.locator(".player-tier .badge").get_attribute("style")
        # The banner's name: never a picture name (a title is in no served
        # file). RETIRED CLAIM, 2026-11-10 (CARD-280, owner ruling: a festive
        # solve): it read "Puzzle <key>"; now there is no name element at all
        # and the banner says "Solved!" (the count is spoken and shown over
        # the board on the solve).
        assert browser_page.locator("[data-player-solved-name]").count() == 0
        solve_to_the_end(browser_page, SWEEP_GRID)
        said = " ".join(browser_page.locator("#puzzle-player-solved").inner_text().split())
        assert said == "Solved!" and key not in said, said
        for name, grid in PAGE_GRIDS.items():
            assert _leaky_title(grid) not in browser_page.content()

    def test_a_puzzle_opened_from_a_book_offers_the_way_back_and_no_other_page_does(
        self, browser_page, preview_host
    ) -> None:
        """CARD-436 AC-1/AC-2/AC-3 — the way back to the book, and the cost.

        The card measured the live page at zero anchors (``document
        .querySelectorAll('a').length === 0``), and its AC-1 asked only for
        the solved state. **The owner's ruling of 2026-11-13 widened it**: a
        quiet link from the moment the puzzle opens, PLUS a prominent one in
        the solved state. Both are held here.

        The three negatives are the point of the cell, not its tail: no
        ``?book=``, a malformed slug, and a valid slug for a book that does
        NOT hold this key. An implementation that linked to whatever slug the
        URL carried would pass the positive arm alone, and the third negative
        is the one only the membership test catches — the same validity test
        CARD-420 applies for the theme. Each is measured as the card's own
        instrument, ``a`` count zero, which is stronger than "no link of
        mine": a page that grew some other anchor would red here too.

        The cost (requirement 5) is measured, not argued, at the 390 x 844 the
        card names: the stage's height, its top (what ``measureStageTop``
        writes to ``--player-stage-top``) and the two rows above it are read
        from the same puzzle with the book and without, and must be equal.
        The link's SLOT is the third item of ``.page-head.player-head``, where
        ``admin.css``'s own comment measured that a line of text is free, and
        the solve promotes the link inside it rather than drawing a second one
        — see ``assemble.py``'s comment for the render that decided that.

        Two more things are measured rather than asserted off an attribute or
        off ``inner_text()``, both from cycle 1's findings (see ``_LOOK``):
        the <a>'s own rectangle against its words' at 1280 x 720, where the
        row has slack — an anchor wider than its words is blank clickable
        header above the board — and the name's ``scrollWidth`` against its
        ``clientWidth``, which is the only instrument that can see
        ``text-overflow: ellipsis``. The second one holds a DECLARATION, not
        a repair: the name is clipped at 390 x 844 and whole at 1280 x 720,
        and both states are asserted so neither can change in silence.
        """
        url, report, keys, slug = preview_host
        page = browser_page
        watch = Watch(page)
        page.set_viewport_size({"width": 390, "height": 844})
        key = keys["e10"]  # in the fixture book, and its smallest board
        outside = keys["sweep"]  # published, and in no book

        # Without a book: the page as it is today — no link at all.
        open_play(page, url, key)
        assert page.evaluate("() => document.querySelectorAll('a').length") == 0
        bare = page.evaluate(_ROOM)
        # What the page FETCHED, the document itself left out (its own address
        # is the one thing the two arms cannot share).
        def fetched(seen: list[str]) -> set[str]:
            paths = {u.removeprefix(url) for u in seen}
            return {path for path in paths if not path.startswith("/play/")}

        asked, no_book = len(watch.urls), fetched(watch.urls)

        # From the book: the quiet link, from the moment the puzzle opens.
        open_play_at(page, url, f"/play/{key}?book={slug}")
        # AC-3's request count: the book page fetches the puzzle file and the
        # book file, and nothing the bookless page did not fetch. The way back
        # is drawn from what CARD-420 already fetched for the theme.
        assert fetched(watch.urls[asked:]) == no_book | {f"/book/{slug}.json"}, sorted(
            fetched(watch.urls[asked:])
        )
        back = page.locator("[data-player-book]")
        assert back.is_visible()
        assert back.get_attribute("href") == f"/b/{slug}", "a real href, openable in a new tab"
        assert BOOK_TITLE_SERVED in back.inner_text()
        assert back.get_attribute("data-player-book") == "quiet"
        quiet = page.evaluate(_LOOK)
        # F-002: ``inner_text()`` is the string, not the painted glyphs, so the
        # line above passes identically whether the reader sees the book's name
        # or "← Winter Pictu…". The RENDERED extent is asserted beside it, and
        # at THIS viewport the declaration is that the name does NOT fit: about
        # 41% of it is ellipsised (251 px of name in 148 px of row). That is
        # declared and held rather than styled away — the header's width is a
        # product decision about what this row shows, not a defect of this
        # card — so a later change that makes the name fit reds here and has to
        # re-state the declaration instead of silently retiring it.
        assert quiet["whole"] > quiet["painted"], quiet
        # And the board lost nothing to it (requirement 5).
        assert page.evaluate(_ROOM) == bare, (page.evaluate(_ROOM), bare)

        # Solved: the same element, promoted — and promoted in FACT, not by an
        # attribute that says so. The attribute is read, and so is what the
        # reader sees: the solved banner's own success edge and tint, and a
        # heavier weight, none of which the quiet state has.
        solve_to_the_end(page, PAGE_GRIDS["e10"])
        assert page.locator("#puzzle-player-solved").is_visible()
        assert back.is_visible()
        assert back.get_attribute("href") == f"/b/{slug}"
        assert BOOK_TITLE_SERVED in back.inner_text()
        assert back.get_attribute("data-player-book") == "solved"
        loud = page.evaluate(_LOOK)
        assert loud["weight"] != quiet["weight"], (loud, quiet)
        assert loud["background"] != quiet["background"] and loud["border"] != quiet["border"]
        assert quiet["background"] == "rgba(0, 0, 0, 0)", quiet
        solved = page.evaluate(_ROOM)

        # The SOLVED state's cost, measured against the same solved board with
        # no book — the player's own save resumes it, and no link is drawn.
        # This arm is not ceremony: the FIRST implementation put the solved
        # way back inside the banner, where this comparison measured the board
        # pushed down 2 px here and 12.8 px at 1280 x 720 (and a render showed
        # the banner overflowing its box onto the History buttons).
        open_play(page, url, key)
        assert page.locator("#puzzle-player-solved").is_visible(), "the save resumed a solved board"
        assert page.evaluate("() => document.querySelectorAll('a').length") == 0
        assert page.evaluate(_ROOM) == solved, (page.evaluate(_ROOM), solved)

        # A malformed slug and a real book that does not hold this key: no
        # link at all either, exactly as today (AC-2; the no-book arm is the
        # two ``a``-count zeros above).
        for address in (f"/play/{key}?book=nope", f"/play/{outside}?book={slug}"):
            open_play_at(page, url, address)
            assert page.evaluate("() => document.querySelectorAll('a').length") == 0, address

        # F-001: the way back's HIT AREA is its words, not the row's free
        # space. At 390 x 844 the two are one box — the name fills the slot —
        # so the only viewport that can tell them apart is one with slack, and
        # this is the viewport the defect was measured at. The first
        # implementation put the row's ``flex: 1 1 0`` on the <a> itself: 875
        # px of anchor for 221 px of words, i.e. ~654 px of apparently empty
        # header, directly above the board, that left the puzzle when tapped,
        # on a page that had no anchor at all before this card. Both lines
        # below are red against that construction.
        page.set_viewport_size({"width": 1280, "height": 720})
        open_play_at(page, url, f"/play/{key}?book={slug}")
        page.wait_for_selector('[data-player-book="solved"]', timeout=PAGES_SETTLE_MS)
        wide = page.evaluate(_LOOK)
        assert wide["slot"] - wide["link"] > 100, wide  # the row really has slack here
        assert wide["link"] - wide["words"] <= 1, wide  # and the anchor is only its words
        # The other half of F-002, at the viewport where the row is wide
        # enough: given the space, the whole name IS painted. So "clipped at
        # 390 x 844" above is a statement about the row, not about the string.
        assert wide["whole"] <= wide["painted"], wide

        # Nothing threw along any of it — the observer included.
        assert watch.problems() == []

    def test_the_usage_line_is_true_for_the_public_player(self, browser_page, preview_host) -> None:
        """F-2: the admin's text describes Check, which does not exist here.
        Since CARD-413 (owner item 9) the text is "How to play" and its Check
        bullet is removed here with the button (no assembly-time edit any
        more): every control it names is on this page (AC-3)."""
        url, report, keys, _ = preview_host
        open_play(browser_page, url, keys["sweep"])
        hint = browser_page.locator("#puzzle-player-hint")
        assert hint.is_visible()
        assert howto_problems(browser_page) == []
        text = hint.inner_text()
        assert "Check" not in text and "wrong mark" not in text, text
        assert browser_page.locator('[data-player-action="check"]').count() == 0
        # And the admin-only counters are gone from the toolbar.
        assert not browser_page.locator("#puzzle-player-errors").is_visible()
        assert not browser_page.locator("#puzzle-player-progress").is_visible()

    @pytest.mark.parametrize("width, height", [(390, 844), (1280, 900)])
    def test_the_line_the_usage_text_names_is_where_it_says_at_both_widths(
        self, browser_page, preview_host, width, height
    ) -> None:
        """RETIRED CLAIM, 2026-11-07 (CARD-413, owner item 9): F-1's "the line
        the usage text names is where it says". The "How to play" text names
        no place; what it must be at both widths is one closed line
        (AC-1) whose bullets, opened, name only controls this page shows
        (AC-3). The name is kept (a rename moves a recorded node id)."""
        url, report, keys, _ = preview_host
        browser_page.set_viewport_size({"width": width, "height": height})
        open_play(browser_page, url, keys["sweep"])
        hint = browser_page.locator("#puzzle-player-hint")
        assert hint.get_attribute("open") is None and " ".join(hint.inner_text().split()) == "How to play"
        assert howto_problems(browser_page) == []

    def test_the_old_wording_is_false_on_a_phone_and_the_check_sees_it(self, browser_page, preview_host) -> None:
        """The plant (CARD-413 AC-3's control; the retired claim was CARD-386
        F-1's old sentence): put the Check bullet back on the public page and
        the text check must red, at both widths. The name is kept (a rename
        moves a recorded node id)."""
        url, report, keys, _ = preview_host
        problems = {}
        for width, height in ((390, 844), (1280, 900)):
            browser_page.set_viewport_size({"width": width, "height": height})
            open_play(browser_page, url, keys["sweep"])
            browser_page.evaluate(
                "() => { const li = document.createElement('li'); li.innerHTML = '<strong>Check</strong>: highlights the row.';"
                " document.querySelector('#puzzle-player-hint ul').append(li); }")
            problems[width] = howto_problems(browser_page)
        assert problems[390] != [] and problems[1280] != [], problems

    def test_a_bad_address_shows_no_placeholder_header_chip_or_false_fallback(
        self, browser_page, preview_host
    ) -> None:
        """F-2: not 'Puzzle x', no template tier chip, and a fallback sentence that is true here."""
        url, *_ = preview_host
        browser_page.goto(f"{url}/play/0000000000", timeout=PAGES_SETTLE_MS)
        browser_page.wait_for_function(
            "() => !document.querySelector('[data-player-fallback]').textContent.startsWith('Drawing')",
            timeout=PAGES_SETTLE_MS,
        )
        assert browser_page.locator(".player-head h1").inner_text() == "Puzzle"
        assert not browser_page.locator(".player-tier").is_visible()
        html = (preview_host[1].site_dir / "play" / "index.html").read_text(encoding="utf-8")
        assert "static/solver.js" not in html and "\u00d7</h1>" not in html
        assert "(solver.js) did not load, or JavaScript is off." in html

    def test_hint_stays_on_and_says_why_where_no_line_decides(self, browser_page, preview_host) -> None:
        """F-3, verified on the assembled page (the stall board of CARD-385's sweep)."""
        url, report, keys, _ = preview_host
        open_play(browser_page, url, keys["stall"])
        assert not disabled(action(browser_page, "hint"))
        before = states(browser_page)
        action(browser_page, "hint").click()
        assert states(browser_page) == before
        assert browser_page.locator("#puzzle-player-explain").inner_text() == public_exhausted_sentence()

    def test_old_public_saves_are_not_read_and_the_visitor_starts_fresh(
        self, browser_page, preview_host
    ) -> None:
        """The owner decides at deploy whether a migration is worth it; the preview starts fresh."""
        url, report, keys, _ = preview_host
        key = keys["sweep"]
        old = json.dumps({"board": "filled" * 3})
        browser_page.add_init_script(f"localStorage.setItem('nonogram-public:{key}', {json.dumps(old)})")
        open_play(browser_page, url, key)
        assert set(states(browser_page)) == {"unknown"}
        assert browser_page.evaluate(f"localStorage.getItem('nonogram-public:{key}')") == old
        cell(browser_page, 0, 0).click()
        assert browser_page.evaluate("Object.keys(localStorage).sort()") == sorted(
            [f"nonogram-public:{key}", f"nonogram-player:{key}"])

    @pytest.mark.parametrize("path, message", [
        ("/play/not-a-key", "This address names no puzzle"),
        ("/play/0000000000", "This puzzle is not on the site"),
    ])
    def test_an_address_that_is_no_puzzle_says_so_and_draws_no_board(
        self, browser_page, preview_host, path, message
    ) -> None:
        url, *_ = preview_host
        browser_page.goto(f"{url}{path}", timeout=PAGES_SETTLE_MS)
        browser_page.wait_for_function(
            "() => !document.querySelector('[data-player-fallback]').textContent.startsWith('Drawing')",
            timeout=PAGES_SETTLE_MS,
        )
        assert message in browser_page.locator("[data-player-fallback]").inner_text()
        assert browser_page.locator("td.player-cell").count() == 0


@pytest.mark.browser
class TestSharedUi_TheCard385SweepOnThisTree:
    # EC-050 and ADR-0041/R4: the model's verifying ref, tests/test_player_shared_ui_site.py::test_every_control_every_gesture_the_solve_and_the_reload_are_clean (CARD-399: moved here from play.js's twin).
    def test_every_control_every_gesture_the_solve_and_the_reload_are_clean(
        self, touch_page, preview, monkeypatch
    ) -> None:
        """AC-1 / the card's item 3: CARD-385's own sweep, against THIS tree."""
        report, keys, _ = preview
        key = keys["sweep"]
        # The sweep asserts the save key it expects; the tree's key is the puzzle's.
        monkeypatch.setattr(sweep_module, "SWEEP_ID", key)
        monkeypatch.setattr(sweep_module, "SWEEP_GRID", SWEEP_GRID)
        url, stop = _serve(report.site_dir)
        try:
            problems = sweep_problems(touch_page, Opened(f"{url}/play/{key}", report.site_dir), SWEEP_GRID, steps=STEPS)
        finally:
            stop()
        assert problems == []

    def test_the_sweep_is_not_vacuous_a_gutted_control_reds_it(
        self, touch_page, bundle, fragment, tmp_path, monkeypatch
    ) -> None:
        """The control: remove the Undo button from the markup and the same sweep must red (solver.js
        wires the control it finds absent and throws, so the page errors and the sweep aborts)."""
        root, keys, _ = bundle
        key = keys["sweep"]
        mutant = re.sub(r'<button[^>]*data-player-action="undo".*?</button>', "", fragment, flags=re.S)
        assert mutant != fragment
        report = preview_of(root, tmp_path / "mutant", mutant, tmp_path)
        monkeypatch.setattr(sweep_module, "SWEEP_ID", key)
        monkeypatch.setattr(sweep_module, "SWEEP_GRID", SWEEP_GRID)
        url, stop = _serve(report.site_dir)
        try:
            problems = sweep_problems(
                touch_page, Opened(f"{url}/play/{key}", report.site_dir), SWEEP_GRID, steps=STEPS, timeout=2000
            )
        finally:
            stop()
        assert problems != []


# ==========================================================================
# AC-2 - byte identity of the four admin files
# ==========================================================================


class TestSharedUi_ByteIdentity:
    def test_the_table_covers_exactly_the_four_files(self) -> None:
        assert assembler.COPIED_FROM_ADMIN == FOUR_FILES

    @staticmethod
    def identity_problems(site: Path) -> list[str]:
        """The test tree's own equality check, written apart from the assembler's."""
        problems = []
        for source, published in FOUR_FILES.items():
            if (site / published).read_bytes() != (REPO_ROOT / source).read_bytes():
                problems.append(f"{published} differs from {source}")
        return problems

    def test_the_trees_copies_are_the_sources_byte_for_byte(self, preview) -> None:
        report, *_ = preview
        assert self.identity_problems(report.site_dir) == []
        # Real bytes, not an empty equality: the files are the big ones.
        assert (report.site_dir / "solver.js").stat().st_size > 100_000
        assert (report.site_dir / "admin.css").stat().st_size > 100_000

    @pytest.mark.parametrize("name", sorted(FOUR_FILES.values()))
    def test_a_plant_that_edits_a_copy_reds(self, preview, name) -> None:
        report, *_ = preview
        target = report.site_dir / name
        original = target.read_bytes()
        target.write_bytes(original + b"\n/* planted */\n")
        assert self.identity_problems(report.site_dir) == [f"{name} differs from " + next(
            s for s, p in FOUR_FILES.items() if p == name)]
        target.write_bytes(original)
        assert self.identity_problems(report.site_dir) == []

    @pytest.mark.parametrize("name", ["solver.js", "admin.css"])
    def test_the_assembly_time_check_refuses_a_copy_that_is_not_identical(
        self, bundle, fragment, tmp_path, monkeypatch, name
    ) -> None:
        root, *_ = bundle
        real = Path.write_bytes

        def corrupt(self, data):
            return real(self, data + b"x" if self.name == name else data)

        # Control first: the same call, unpatched, assembles.
        preview_of(root, tmp_path / "ok", fragment, tmp_path)
        monkeypatch.setattr(Path, "write_bytes", corrupt)
        with pytest.raises(RuntimeError, match="not byte-identical"):
            preview_of(root, tmp_path / "bad", fragment, tmp_path)


# ==========================================================================
# AC-3 - the served tree carries no answer
# ==========================================================================


class TestSharedUi_TheServedTreeCarriesNoAnswer:
    EXACT = {"clues", "height", "key", "tier", "width"}

    def leaks(self, site: Path, keys: dict[str, str]) -> list[str]:
        """Every served file carrying a bundle grid in any encoding, or its leaky title."""
        found = []
        grids = {**{k: PAGE_GRIDS[k] for k in PAGE_GRIDS}, "sweep": SWEEP_GRID, "stall": STALL_GRID}
        for name, grid in grids.items():
            found += [f"{name}: {f}" for f in solution_leaks(site, grid)]
            title = _leaky_title(grid)
            found += [
                f"{name}: title in {p.relative_to(site)}"
                for p in sorted(site.rglob("*"))
                if p.is_file() and title in p.read_text(errors="ignore")
            ]
        return found

    @staticmethod
    def key_set_problems(site: Path) -> list[str]:
        problems = []
        files = sorted((site / "puzzle").glob("*.json"))
        for path in files:
            if set(json.loads(path.read_text(encoding="utf-8"))) != TestSharedUi_TheServedTreeCarriesNoAnswer.EXACT:
                problems.append(path.name)
        return problems if files else ["no puzzle file"]

    def test_no_served_file_contains_a_solution_string(self, preview) -> None:
        report, keys, _ = preview
        assert self.leaks(report.site_dir, keys) == []

    def test_the_scan_finds_a_planted_solution_in_every_encoding(self, preview) -> None:
        report, keys, _ = preview
        site = report.site_dir
        for index, plant in enumerate((flat(SWEEP_GRID), json.dumps(SWEEP_GRID), _leaky_title(STALL_GRID))):
            target = site / "planted.txt"
            target.write_text(plant)
            assert self.leaks(site, keys) != [], plant[:20]
            target.unlink()
        assert self.leaks(site, keys) == []

    def test_every_puzzle_file_carries_exactly_the_served_key_set(self, preview) -> None:
        report, keys, _ = preview
        assert self.key_set_problems(report.site_dir) == []
        assert len(list((report.site_dir / "puzzle").glob("*.json"))) == len(keys)

    def test_a_bundle_whose_puzzle_carries_a_solution_key_is_served_without_it(
        self, bundle, fragment, tmp_path
    ) -> None:
        root, keys, _ = bundle
        path = root / "puzzle" / f"{keys['sweep']}.json"
        payload = json.loads(path.read_text())
        payload["solution"] = [[int(c) for c in row] for row in SWEEP_GRID]
        path.write_text(json.dumps(payload))
        report = preview_of(root, tmp_path / "planted-bundle", fragment, tmp_path)
        assert ("solution" in {name for _, name in report.dropped}) and self.key_set_problems(report.site_dir) == []

    def test_a_plant_that_adds_a_solution_key_to_a_served_file_reds_the_key_check(self, preview) -> None:
        report, keys, _ = preview
        path = report.site_dir / "puzzle" / f"{keys['sweep']}.json"
        served = json.loads(path.read_text())
        assert self.key_set_problems(report.site_dir) == []
        served["solution"] = [[0]]
        path.write_text(json.dumps(served))
        assert self.key_set_problems(report.site_dir) == [path.name]

    @pytest.mark.parametrize("name", ["solver.js", "solver_state.js"])
    def test_the_copied_javascript_has_no_network_call(self, preview, name) -> None:
        report, *_ = preview
        text = (report.site_dir / name).read_text()
        assert network_calls(text) == []
        # The control: the scan sees a call that is planted.
        for call in ('fetch("/x")', "new XMLHttpRequest()", "navigator.sendBeacon('/x')"):
            assert network_calls(text + f"\n{call};\n") != [], call

    def test_ac392s_own_scan_of_the_tree_is_empty_and_finds_a_plant(self, preview) -> None:
        """No external http(s) reference, none excepted, and no tracking identifier."""
        report, *_ = preview
        runtime, static = driver.allow_list()
        # The scan is default-deny and reads solver.js's import of its byte-identical
        # sibling (`./solver_state.js`) as a reference it cannot place: a relative,
        # same-origin module import. That one line is the whole of the residue, and the
        # test names it so that a SECOND unplaceable reference reds.
        assert scan_site(report.site_dir, runtime, static) == {
            "foreign": [], "identifiers": [], "unclassifiable": COPIED_JS_RESIDUE}
        page = report.site_dir / "play" / "index.html"
        original = page.read_text(encoding="utf-8")
        page.write_text(original.replace("</head>", '<script src="https://evil.example/x.js"></script></head>'))
        assert scan_site(report.site_dir, runtime, static)["foreign"] != []
        page.write_text(original.replace("</head>", '<link rel="stylesheet" href="x.css"></head>'))
        assert len(scan_site(report.site_dir, runtime, static)["unclassifiable"]) == 2
        page.write_text(original)
        # AC-1's plant: a reference appended to the project's own stylesheet reds the scan too.
        base = report.site_dir / "base.css"
        text = base.read_text(encoding="utf-8")
        base.write_text(text + "\n.x { background: url(https://evil.example/x.png); }\n")
        assert scan_site(report.site_dir, runtime, static)["foreign"] != []
        base.write_text(text)

    def test_the_site_marker_is_there(self, preview) -> None:
        report, *_ = preview
        assert (report.site_dir / assembler.SITE_MARKER_FILE).is_file()


# ==========================================================================
# AC-4 - the default is unchanged; the preview differs in a named set only
# ==========================================================================


class TestSharedUi_TheDefaultIsUnchanged:
    def test_two_default_runs_are_byte_identical(self, bundle, tmp_path) -> None:
        root, *_ = bundle
        a = tree_bytes(assembler.assemble(root, tmp_path / "a").site_dir)
        b = tree_bytes(assembler.assemble(root, tmp_path / "b").site_dir)
        assert a == b

    def test_the_drivers_default_command_line_is_unchanged(self) -> None:
        assert driver.delegated_argv(bundle="b", out="o", force=False, analytics=None) == [
            "--out", "o", "--bundle", "b"]

    def test_the_driver_still_writes_no_file_and_names_no_published_path(self) -> None:
        """The existing guard, extended to the preview's table (the guard itself is unchanged)."""
        import ast

        tree = ast.parse((REPO_ROOT / "scripts" / "assemble_player_site.py").read_text(encoding="utf-8"))
        calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        assert not calls & {"write_text", "write_bytes", "copy", "copytree", "rmtree", "mkdir"}
        literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        published = {*assembler.PLAYER_FILES, *assembler.PLAYER_FILES.values(),
                     *assembler.COPIED_FROM_ADMIN, *assembler.COPIED_FROM_ADMIN.values(),
                     assembler.PLAY_PAGE, assembler.SHARED_UI_BASE, assembler.SHARED_UI_BASE_SOURCE}
        assert sorted(p for p in published if any(p in text for text in literals if len(text) < 80)) == []

    def test_the_driver_end_to_end_equals_the_in_process_assembly(self, bundle, fragment, tmp_path) -> None:
        """The driven tree (no flag: there is one assembly) equals the in-process one."""
        root, *_ = bundle
        out = tmp_path / "driven"
        run = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "assemble_player_site.py"),
             "--bundle", str(root), "--out", str(out)],
            capture_output=True, text=True, cwd=REPO_ROOT, check=False,
            env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        )
        assert run.returncode == 0, run.stderr
        in_process = preview_of(root, tmp_path / "inproc", fragment, tmp_path).site_dir
        assert tree_bytes(out) == tree_bytes(in_process)
        page = (out / "play" / "index.html").read_text(encoding="utf-8")
        assert 'href="/base.css"' in page and (out / "base.css").is_file()
        assert not (out / "play.js").exists() and not (out / "bootstrap.min.css").exists()

    def test_the_retired_flags_are_refused_and_print_only_renders_nothing(self, bundle, tmp_path) -> None:
        """``--shared-ui`` and ``--bootstrap`` no longer exist on either command line."""
        root, *_ = bundle
        script = str(REPO_ROOT / "scripts" / "assemble_player_site.py")
        for flags in (["--shared-ui"], ["--bootstrap", str(tmp_path / "x.css")]):
            run = subprocess.run(
                [sys.executable, script, "--bundle", str(root), "--out", str(tmp_path / "o"), *flags],
                capture_output=True, text=True, cwd=REPO_ROOT, check=False)
            assert run.returncode == 2 and "unrecognized arguments" in run.stderr, (flags, run.stderr)
        run = subprocess.run(
            [sys.executable, script, "--bundle", str(root), "--out", str(tmp_path / "o"), "--print-only"],
            capture_output=True, text=True, cwd=REPO_ROOT, check=False)
        assert run.returncode == 0, run.stderr
        assert not (tmp_path / "o").exists()
        with pytest.raises(SystemExit):
            assembler.main(["--out", str(tmp_path / "o"), "--shared-ui-fragment", str(tmp_path / "f.html")])


# ==========================================================================
# The shell's refusals
# ==========================================================================


class TestSharedUi_TheShellRefusesAFragmentItCannotTrust:
    def test_the_real_fragment_builds_a_page(self, fragment) -> None:
        page = assembler.shared_ui_play_page(fragment)
        # The admin's payload element (it carries the admin's solution) is gone; the loader builds its own.
        assert '<script type="application/json"' not in page and "puzzle-player-data" in page
        # CARD-413: no assembly-time text edit any more — the Check bullet is in
        # the shell and removed when the page runs (the live check is
        # test_the_usage_line_is_true_for_the_public_player).
        assert page.count("data-player-howto-check") == 1

    @pytest.mark.parametrize("damage, why", [
        (lambda f: f.replace('id="puzzle-player-data"', 'id="other"'), "no payload element"),
        (lambda f: f.replace("data-player-solved-name", "data-x"), "no banner name hook"),
        (lambda f: f.replace('id="puzzle-player-solved"', 'id="x"'), "no solved banner (CARD-436)"),
        (lambda f: f.replace('class="player-tier"', 'class="x"'), "no tier hook"),
        (lambda f: f.replace('id="puzzle-player"', 'id="x"'), "no stage"),
    ])
    def test_a_fragment_missing_a_hook_is_refused(self, fragment, damage, why) -> None:
        with pytest.raises(ValueError):
            assembler.shared_ui_play_page(damage(fragment))

    def test_a_refused_fragment_leaves_the_previous_tree_alone(self, bundle, fragment, tmp_path) -> None:
        root, *_ = bundle
        out = tmp_path / "keep"
        preview_of(root, out, fragment, tmp_path)
        before = tree_bytes(out)
        with pytest.raises(ValueError):
            preview_of(root, out, fragment.replace('id="puzzle-player"', 'id="x"'), tmp_path)  # the clause damage until CARD-413 retired the clause
        assert tree_bytes(out) == before

# ==========================================================================
# AC-5 - the QR landing, the library and the URL shapes
# ==========================================================================


def load_preview_server():
    path = REPO_ROOT / "scripts" / "preview_player_site.py"
    spec = importlib.util.spec_from_file_location("preview_player_site_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSharedUi_TheDoorsKeepTheirShapes:
    def test_the_two_listing_pages_and_their_assets_are_the_sources_bytes(self, preview) -> None:
        tree = tree_bytes(preview[0].site_dir)
        for source, published in assembler.PLAYER_FILES.items():
            assert tree[published] == (REPO_ROOT / "player" / source).read_bytes(), published

    def test_the_preview_server_serves_the_three_url_shapes(self, preview) -> None:
        report, keys, slug = preview
        server_module = load_preview_server()
        server_module.RewritingHandler.rules = server_module.rewrites(report.site_dir)
        handler = lambda *a: server_module.RewritingHandler(*a, directory=str(report.site_dir))  # noqa: E731
        httpd = http.server.HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            def get(path: str) -> tuple[int, str]:
                try:
                    with urllib.request.urlopen(base + path, timeout=5) as response:
                        return response.status, response.read().decode("utf-8")
                except urllib.error.HTTPError as error:
                    return error.code, ""

            status, body = get(f"/play/{keys['sweep']}")
            assert status == 200 and 'import("/solver.js")' in body
            status, body = get(f"/b/{slug}")
            assert status == 200 and "/pages.js" in body
            status, body = get("/library")
            assert status == 200 and "/pages.js" in body
            # The control: a path that is no door is not rewritten into one.
            assert get("/nowhere/at/all")[0] == 404
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()

    @pytest.mark.browser
    def test_the_qr_landing_lists_the_book_and_a_tile_opens_the_admin_player(
        self, browser_page, preview_host
    ) -> None:
        url, report, keys, slug = preview_host
        watch = Watch(browser_page)
        expected = [keys[name] for name in BOOK_ORDER]
        _open_pages(browser_page, url, f"/b/{slug}")
        assert _tiles(browser_page) == expected
        browser_page.locator(".tile").nth(1).click()
        browser_page.wait_for_function("() => window.puzzlePlayer !== undefined", timeout=PAGES_SETTLE_MS)
        assert browser_page.url.endswith(f"/play/{expected[1]}?book={slug}")  # CARD-420
        assert browser_page.locator("td.player-cell").count() > 0
        assert watch.problems() == []

    @pytest.mark.browser
    def test_the_library_lists_every_puzzle_and_a_tile_opens_the_admin_player(
        self, browser_page, preview_host
    ) -> None:
        url, report, keys, _ = preview_host
        watch = Watch(browser_page)
        _open_pages(browser_page, url, "/library")
        assert sorted(_tiles(browser_page)) == sorted(keys.values())
        browser_page.locator(f'.tile[data-key="{keys["stall"]}"]').click()
        browser_page.wait_for_function("() => window.puzzlePlayer !== undefined", timeout=PAGES_SETTLE_MS)
        assert browser_page.url.endswith(f"/play/{keys['stall']}")
        assert watch.problems() == []
