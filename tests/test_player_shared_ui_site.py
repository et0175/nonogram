"""CARD-386 - the shared-UI PREVIEW site: the admin's own player files on the
public data, no override layer, never deployed.

CARD-385 made ``solver.js`` / ``solver_state.js`` run with no solution grid.
This card assembles a site that uses them (``assemble(shared_ui=...)``;
``scripts/assemble_player_site.py --shared-ui``) so that the owner can open
``/play/<key>`` and judge the admin's look and behaviour on the public pages.
The acceptance criteria and where each is held:

* AC-1 - ``TestSharedUi_ThePageRuns``: a real puzzle plays to the Solved banner
  with zero page errors and zero non-GET requests, the page links no stylesheet
  beyond tokens / Bootstrap / ``admin.css``; and
  ``TestSharedUi_TheCard385SweepOnThisTree`` runs CARD-385's whole gesture sweep
  (every control, the solve, the reload) against THIS assembled tree.
* AC-2 - ``TestSharedUi_ByteIdentity``: the table covers the four admin files,
  the tree's copies equal the sources, an edited copy reds, and the
  assembly-time equality check fires on a copy that is not identical.
* AC-3 - ``TestSharedUi_TheServedTreeCarriesNoAnswer``: no solution string in
  any served file, the puzzle JSON key set is exactly ``clues, height, key,
  tier, width``, a plant that adds a solution key or string reds, the copied JS
  has no network call, and AC-392's own scan of the tree is empty.
* AC-4 - ``TestSharedUi_TheDefaultIsUnchanged``: without the flag the tree is
  the default tree and the preview differs from it in a named set of paths only.
  (The existing assembler and public-player modules are re-run by node id; see
  the card's notes.)
* AC-5 - ``TestSharedUi_TheDoorsKeepTheirShapes``: ``/library`` and ``/b/<slug>``
  are byte-identical to the default tree's and work in Chromium; the preview
  server serves all three URL shapes.

Beside them: the F-2 usage line (no sentence about Check), F-3 (Hint stays on
and says why where no line decides), the banner's neutral name, the fresh start
(old ``nonogram-public:`` saves are not read), and the refusals of the shell
and of the two CLIs.

Bootstrap is NOT in the repository (G-3), so the tests assemble with a tiny
stand-in stylesheet that holds the one Bootstrap rule the player needs
(``[hidden]``). The real file was run through the same sweep by hand; the
card's notes carry that measurement.
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
    play_exhausted_sentence,
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

#: What stands in for Bootstrap in the tests (G-3: the real file is not in the
#: repository). ``admin.css`` leans on Bootstrap's reboot for ``[hidden]``.
BOOTSTRAP_STAND_IN = "/* stand-in for Bootstrap 5.3 (tests only) */\n[hidden] { display: none !important; }\n"

#: The files the preview's tree differs from the default tree in.
PREVIEW_ONLY = {"admin.css", "bootstrap.min.css", "solver.js"}
PREVIEW_REPLACED = {"play/index.html"}
PREVIEW_DROPPED = {"play.js"}


# --------------------------------------------------------------------------
# The fixtures: a bundle, a default tree, a preview tree
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fragment() -> str:
    """The admin template, rendered by the driver (the one source of markup)."""
    return driver.render_shared_ui_fragment()


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
    stand_in = tmp_path / "bootstrap.min.css"
    stand_in.write_text(BOOTSTRAP_STAND_IN, encoding="utf-8")
    return assembler.assemble(
        bundle_root, out, shared_ui=assembler.SharedUi(fragment=fragment, bootstrap=stand_in), **kwargs
    )


@pytest.fixture
def preview(bundle, fragment, tmp_path):
    root, keys, slug = bundle
    report = preview_of(root, tmp_path / "preview", fragment, tmp_path)
    return report, keys, slug


@pytest.fixture
def default_tree(bundle, tmp_path):
    root, _, _ = bundle
    return assembler.assemble(root, tmp_path / "default").site_dir


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
                or page.locator("#puzzle-player-explain").inner_text() == play_exhausted_sentence())

    for _ in range(3 * len(SWEEP_GRID) * len(SWEEP_GRID[0])):
        if finished():
            break
        hint.click()
    assert finished(), "the ladder ran out of presses"
    hint.click(force=True)  # beyond: a locked Hint is inert, an exhausted one repeats its sentence


STEPS = {**CONTROL_STEPS, "data-player-action=hint": step_hint_on_a_bigger_board}


def usage_line_problems(page) -> list[str]:
    """Where the usage paragraph says the answer line is, against where it is.

    Read from the DOM: the paragraph's claim is parsed from its own text, and
    each claim is held to the rectangles of the header, the answer line and the
    toolbar. A paragraph that makes neither claim is a problem too.
    """
    text = page.locator("#puzzle-player-hint").inner_text()
    box = page.evaluate(
        """() => { const r = (s) => { const b = document.querySelector(s).getBoundingClientRect();
          return {top: b.top, bottom: b.bottom, width: b.width}; };
          return {h1: r('.player-head h1'), line: r('#puzzle-player-explain'), tools: r('#puzzle-player-controls')}; }"""
    )
    line, h1, tools = box["line"], box["h1"], box["tools"]
    problems = []
    if line["width"] <= 0:
        problems.append("the answer line is not on the page")
    claimed = False
    if "beside the puzzle's title" in text:
        claimed = True
        middle = (line["top"] + line["bottom"]) / 2
        if not h1["top"] <= middle <= h1["bottom"]:
            problems.append("says beside the title, but the line is not on the title's row")
    if "at the top of the page" in text:
        claimed = True
        if line["bottom"] > tools["top"] + 1:
            problems.append("says at the top of the page, but the line is below the toolbar")
    if not claimed:
        problems.append("the paragraph does not say where the answer line is")
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
            f"/play/{key}", "/tokens.css", "/bootstrap.min.css", "/admin.css", "/solver.js",
            "/solver_state.js", f"/puzzle/{key}.json",
        }, sorted(requested)

    def test_the_page_links_no_stylesheet_beyond_the_admins_and_has_no_style_element(
        self, browser_page, preview_host
    ) -> None:
        """G-1: no override layer. The page's sheets are tokens, Bootstrap, admin.css."""
        url, report, keys, _ = preview_host
        open_play(browser_page, url, keys["sweep"])
        sheets = browser_page.evaluate("[...document.styleSheets].map(s => new URL(s.href).pathname)")
        assert sheets == ["/bootstrap.min.css", "/tokens.css", "/admin.css"], sheets
        assert browser_page.evaluate("document.querySelectorAll('style').length") == 0
        html = (report.site_dir / "play" / "index.html").read_text(encoding="utf-8")
        assert re.findall(r'rel="stylesheet" href="([^"]+)"', html) == [
            "/bootstrap.min.css", "/tokens.css", "/admin.css"]

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
        # The banner's name: neutral, never a picture name (a title is in no served file).
        assert browser_page.locator("[data-player-solved-name]").text_content() == f"Puzzle {key}"
        solve_to_the_end(browser_page, SWEEP_GRID)
        assert f"Puzzle {key}" in browser_page.locator("#puzzle-player-solved").inner_text()
        for name, grid in PAGE_GRIDS.items():
            assert _leaky_title(grid) not in browser_page.content()

    def test_the_usage_line_is_true_for_the_public_player(self, browser_page, preview_host) -> None:
        """F-2: the admin's paragraph ends with a sentence about Check, which does not exist here."""
        url, report, keys, _ = preview_host
        open_play(browser_page, url, keys["sweep"])
        hint = browser_page.locator("#puzzle-player-hint")
        assert hint.is_visible()
        text = hint.inner_text()
        assert "Check" not in text and "wrong mark" not in text, text
        assert text.endswith("the third reveals it, and each press writes its answer in the line at the top of the page."), text
        assert "beside the puzzle" not in text, text
        assert browser_page.locator('[data-player-action="check"]').count() == 0
        # And the admin-only counters are gone from the toolbar.
        assert not browser_page.locator("#puzzle-player-errors").is_visible()
        assert not browser_page.locator("#puzzle-player-progress").is_visible()

    @pytest.mark.parametrize("width, height", [(390, 844), (1280, 900)])
    def test_the_line_the_usage_text_names_is_where_it_says_at_both_widths(
        self, browser_page, preview_host, width, height
    ) -> None:
        """F-1, measured from the DOM: after a Hint press the answer line is above the toolbar."""
        url, report, keys, _ = preview_host
        browser_page.set_viewport_size({"width": width, "height": height})
        open_play(browser_page, url, keys["sweep"])
        action(browser_page, "hint").click()
        assert browser_page.locator("#puzzle-player-explain").is_visible()
        assert usage_line_problems(browser_page) == []

    def test_the_old_wording_is_false_on_a_phone_and_the_check_sees_it(self, browser_page, preview_host) -> None:
        """The plant: the admin's own sentence, put back, must red at 390 px (and only there)."""
        url, report, keys, _ = preview_host
        old = "its answer in the line beside the puzzle's title."
        problems = {}
        for width, height in ((390, 844), (1280, 900)):
            browser_page.set_viewport_size({"width": width, "height": height})
            open_play(browser_page, url, keys["sweep"])
            action(browser_page, "hint").click()
            browser_page.evaluate(
                "(old) => { const p = document.querySelector('#puzzle-player-hint');"
                " p.textContent = p.textContent.replace(/its answer in the line at the top of the page\\./, old); }",
                old,
            )
            assert old in browser_page.locator("#puzzle-player-hint").inner_text()
            problems[width] = usage_line_problems(browser_page)
        assert problems[390] != [], "the old wording must red at 390 px"
        assert problems[1280] == [], "and it is true on a desktop, which is why it survived"

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
        assert browser_page.locator("#puzzle-player-explain").inner_text() == play_exhausted_sentence()

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
        assert assembler.SHARED_UI_COPIED_FROM_ADMIN == FOUR_FILES
        # The default table is untouched (AC-4).
        assert assembler.COPIED_FROM_ADMIN == {
            k: v for k, v in FOUR_FILES.items() if v in ("solver_state.js", "tokens.css")}

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
            "foreign": [], "identifiers": [],
            "unclassifiable": ["solver.js: './solver_state.js' is neither absolute nor rooted at the site"]}
        page = report.site_dir / "play" / "index.html"
        original = page.read_text(encoding="utf-8")
        page.write_text(original.replace("</head>", '<script src="https://evil.example/x.js"></script></head>'))
        assert scan_site(report.site_dir, runtime, static)["foreign"] != []
        page.write_text(original.replace("</head>", '<link rel="stylesheet" href="x.css"></head>'))
        assert len(scan_site(report.site_dir, runtime, static)["unclassifiable"]) == 2
        page.write_text(original)

    def test_the_site_marker_is_there(self, preview) -> None:
        report, *_ = preview
        assert (report.site_dir / assembler.SITE_MARKER_FILE).is_file()


# ==========================================================================
# AC-4 - the default is unchanged; the preview differs in a named set only
# ==========================================================================


class TestSharedUi_TheDefaultIsUnchanged:
    def test_without_the_flag_the_tree_is_the_default_tree(self, default_tree) -> None:
        tree = tree_bytes(default_tree)
        for absent in PREVIEW_ONLY:
            assert absent not in tree, absent
        assert tree["play/index.html"] == (REPO_ROOT / "player" / "play.html").read_bytes()
        assert tree["play.js"] == (REPO_ROOT / "player" / "play.js").read_bytes()
        assert assembler.PLAYER_FILES.keys() == {
            "play.html", "play.js", "library.html", "book.html", "pages.js", "player.css", "vercel.json"}

    def test_two_default_runs_are_byte_identical(self, bundle, tmp_path) -> None:
        root, *_ = bundle
        a = tree_bytes(assembler.assemble(root, tmp_path / "a").site_dir)
        b = tree_bytes(assembler.assemble(root, tmp_path / "b", shared_ui=None).site_dir)
        assert a == b

    def test_the_preview_differs_from_the_default_in_the_named_paths_only(
        self, preview, default_tree
    ) -> None:
        shared, plain = tree_bytes(preview[0].site_dir), tree_bytes(default_tree)
        assert set(shared) - set(plain) == PREVIEW_ONLY
        assert set(plain) - set(shared) == PREVIEW_DROPPED
        changed = {name for name in set(shared) & set(plain) if shared[name] != plain[name]}
        assert changed == PREVIEW_REPLACED, sorted(changed)

    def test_the_cli_flags_are_all_or_nothing(self, tmp_path) -> None:
        with pytest.raises(SystemExit):
            assembler.main(["--out", str(tmp_path / "o"), "--bootstrap", str(tmp_path / "b.css")])
        with pytest.raises(SystemExit):
            assembler.main(["--out", str(tmp_path / "o"), "--shared-ui-fragment", str(tmp_path / "f.html")])

    def test_the_drivers_default_command_line_is_unchanged(self) -> None:
        assert driver.delegated_argv(bundle="b", out="o", force=False, analytics=None) == [
            "--out", "o", "--bundle", "b"]
        assert driver.delegated_argv(bundle="b", out="o", force=False, analytics=None, bootstrap="x.css") == [
            "--out", "o", "--bundle", "b", "--bootstrap", "x.css"]

    def test_the_driver_still_writes_no_file_and_names_no_published_path(self) -> None:
        """The existing guard, extended to the preview's table (the guard itself is unchanged)."""
        import ast

        tree = ast.parse((REPO_ROOT / "scripts" / "assemble_player_site.py").read_text(encoding="utf-8"))
        calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        assert not calls & {"write_text", "write_bytes", "copy", "copytree", "rmtree", "mkdir"}
        literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        published = {*assembler.SHARED_UI_PLAYER_FILES, *assembler.SHARED_UI_PLAYER_FILES.values(),
                     *assembler.SHARED_UI_COPIED_FROM_ADMIN, *assembler.SHARED_UI_COPIED_FROM_ADMIN.values(),
                     assembler.SHARED_UI_BOOTSTRAP}
        assert sorted(p for p in published if any(p in text for text in literals if len(text) < 80)) == []

    def test_the_driver_end_to_end_equals_the_in_process_assembly(self, bundle, fragment, tmp_path) -> None:
        root, *_ = bundle
        css = tmp_path / "bootstrap.min.css"
        css.write_text(BOOTSTRAP_STAND_IN, encoding="utf-8")
        out = tmp_path / "driven"
        run = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "assemble_player_site.py"),
             "--bundle", str(root), "--out", str(out), "--shared-ui", "--bootstrap", str(css)],
            capture_output=True, text=True, cwd=REPO_ROOT, check=False,
            env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        )
        assert run.returncode == 0, run.stderr
        assert "PREVIEW" in run.stdout
        in_process = preview_of(root, tmp_path / "inproc", fragment, tmp_path).site_dir
        assert tree_bytes(out) == tree_bytes(in_process)

    def test_the_driver_refuses_one_of_the_two_flags_and_print_only_renders_nothing(
        self, bundle, tmp_path
    ) -> None:
        root, *_ = bundle
        script = str(REPO_ROOT / "scripts" / "assemble_player_site.py")
        for flags in (["--shared-ui"], ["--bootstrap", str(tmp_path / "x.css")]):
            run = subprocess.run(
                [sys.executable, script, "--bundle", str(root), "--out", str(tmp_path / "o"), *flags],
                capture_output=True, text=True, cwd=REPO_ROOT, check=False)
            assert run.returncode == 2 and "go together" in run.stderr, run.stderr
        run = subprocess.run(
            [sys.executable, script, "--bundle", str(root), "--out", str(tmp_path / "o"), "--shared-ui",
             "--bootstrap", str(tmp_path / "x.css"), "--print-only"],
            capture_output=True, text=True, cwd=REPO_ROOT, check=False)
        assert run.returncode == 0, run.stderr
        assert "--bootstrap" in run.stdout and not (tmp_path / "o").exists()


# ==========================================================================
# The shell's refusals
# ==========================================================================


class TestSharedUi_TheShellRefusesAFragmentItCannotTrust:
    def test_the_real_fragment_builds_a_page(self, fragment) -> None:
        page = assembler.shared_ui_play_page(fragment)
        # The admin's payload element (it carries the admin's solution) is gone; the loader builds its own.
        assert '<script type="application/json"' not in page and "puzzle-player-data" in page
        assert "Check highlights" not in page

    @pytest.mark.parametrize("damage, why", [
        (lambda f: f.replace(assembler.SHARED_UI_HINT_CLAUSE, "."), "the usage clause is gone"),
        (lambda f: f + assembler.SHARED_UI_HINT_CLAUSE, "the usage clause twice"),
        (lambda f: f.replace('id="puzzle-player-data"', 'id="other"'), "no payload element"),
        (lambda f: f.replace("data-player-solved-name", "data-x"), "no banner name hook"),
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
            preview_of(root, out, fragment.replace(assembler.SHARED_UI_HINT_CLAUSE, "."), tmp_path)
        assert tree_bytes(out) == before

    def test_a_missing_bootstrap_file_is_an_error_before_the_tree_is_touched(
        self, bundle, fragment, tmp_path
    ) -> None:
        root, *_ = bundle
        out = tmp_path / "keep"
        preview_of(root, out, fragment, tmp_path)
        before = tree_bytes(out)
        with pytest.raises(FileNotFoundError):
            assembler.assemble(root, out, shared_ui=assembler.SharedUi(fragment, tmp_path / "none.css"))
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
    def test_the_two_listing_pages_and_their_assets_are_the_default_trees_bytes(
        self, preview, default_tree
    ) -> None:
        shared, plain = tree_bytes(preview[0].site_dir), tree_bytes(default_tree)
        for name in ("library/index.html", "b/index.html", "pages.js", "player.css", "vercel.json",
                     "index.json", *(n for n in plain if n.startswith(("book/", "puzzle/")))):
            assert shared[name] == plain[name], name

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
        assert browser_page.url.endswith(f"/play/{expected[1]}")
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
