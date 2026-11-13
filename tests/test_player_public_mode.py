"""CARD-385 - the admin player's PUBLIC mode: ``solver.js`` and
``solver_state.js`` run with no solution grid at all (ADR-0041/R2).

The owner chose design A of the shared-player spike (2026-11-06): the public
page runs the admin's own player files instead of a second implementation. The
one thing that stopped ``solver.js`` running on the public site was that it
needs ``payload.solution``, which no public asset may carry. This file is the
R2 proof of the fix, in three parts:

* the PURE half - ``solver_state.js``'s solution-free twins (``isClueSolved``,
  ``hintCell`` / ``hintLine`` / ``knownLine`` with a ``null`` solution, a save
  with no fingerprint) against an independent brute-force oracle on a seeded
  corpus (CARD-399 dropped the comparison with ``player/play.js``'s
  ``derivedHint`` / ``isClueSolved`` / ``forcedLine``: the shared player is the
  one implementation, the oracle is the independent second one);
* the SWEEP - an assembled scratch tree built from the REAL admin files
  (``solver.js``, ``solver_state.js``, ``admin.css``, ``tokens.css`` and the
  real ``puzzle_solve.html`` rendered by Jinja behind a throwaway shell that
  stands in for the next card's assembler), served over loopback with a payload
  that has NO ``solution``, in headless Chromium, with EVERY control exercised.
  A page error, a console error, a non-GET request or the solution string in
  any served file fails it. In public mode ``payload.solution`` is a getter
  that THROWS, so a solution read left reachable is a page error, never a
  tolerated null;
* the CENSUS and the MUTANTS - every ``data-player-*`` control of the admin
  template must have a sweep step that really clicks it (or asserts it absent),
  and each way the property could be lost (an ungated solution read, a reveal
  fallback, a payload with a solution accepted, an unswept control, a network
  call, a fingerprint from a non-null solution, a changed admin mode) is built
  here as a mutant of a copy of the real files and must red the test that
  claims to catch it, beside a matched clean control.
"""

from __future__ import annotations

import functools
import http.server
import json
import random
import re
import shutil
import threading
from itertools import groupby
from pathlib import Path

import jinja2
import pytest

from nonogram.solver import solve
from tests.test_puzzle_solver_page import _unique_grid, browser_page, browser_type, live  # noqa: F401 - fixtures are used by name
from tests.test_puzzle_solver_page import _open as admin_open

_ROOT = Path(__file__).resolve().parent.parent
_ADMIN = _ROOT / "src" / "nonogram" / "admin"
_STATIC = _ADMIN / "static"
_TEMPLATES = _ADMIN / "templates"

#: The four files the admin page really serves, copied byte for byte.
ADMIN_FILES = ("solver.js", "solver_state.js", "admin.css", "tokens.css")

# --------------------------------------------------------------------------
# The puzzles
# --------------------------------------------------------------------------

UNKNOWN, FILLED, EMPTY, MAYBE = "unknown", "filled", "empty", "maybe"


def _encode(line) -> list[int]:
    """Run-length encoding written independently of ``nonogram.clues``."""
    runs = [len(list(group)) for value, group in groupby(line) if value]
    return runs or [0]


def clues_of(grid):
    return [_encode(row) for row in grid], [_encode(column) for column in zip(*grid)]


def _random_grid(width: int, height: int, seed: int, density: float) -> list[list[bool]]:
    rng = random.Random(seed)
    return [[rng.random() < density for _ in range(width)] for _ in range(height)]


def _unique(grid) -> bool:
    rows, columns = clues_of(grid)
    return solve([tuple(r) for r in rows], [tuple(c) for c in columns]).solution_count == 1


#: The sweep's puzzle: 10 x 8, uniquely solvable, and line logic decides cells
#: from the blank board, so Hint has something to say at once.
SWEEP_GRID = _random_grid(10, 8, seed=0, density=0.6)
#: A uniquely solvable 7 x 6 where NO line decides a cell from the blank board:
#: Hint has nothing to derive and nothing to reveal (the exhausted state).
STALL_GRID = _random_grid(7, 6, seed=155, density=0.45)
SWEEP_ID = "sweep-puzzle"


def flat(grid) -> str:
    return "".join("1" if cell else "0" for row in grid for cell in row)


def public_exhausted_sentence() -> str:
    """The exhausted-hint sentence of public mode, read from solver.js's own
    ``PUBLIC_EXHAUSTED`` (CARD-399: the shared player is the one implementation,
    so the sentence is read where it is defined, not from player/play.js)."""
    match = re.search(r'const PUBLIC_EXHAUSTED =\s*\n?\s*"([^"]+)";', (_STATIC / "solver.js").read_text())
    assert match, "solver.js no longer defines PUBLIC_EXHAUSTED"
    return match.group(1)


def public_payload(grid, *, puzzle_id: str = SWEEP_ID, **extra) -> dict:
    rows, columns = clues_of(grid)
    payload = {"id": puzzle_id, "mode": "public", "width": len(grid[0]), "height": len(grid),
               "rows": rows, "columns": columns}
    payload.update(extra)
    return payload


def test_the_sweep_puzzles_are_what_the_sweep_needs() -> None:
    assert _unique(SWEEP_GRID) and _unique(STALL_GRID)

    def forces(clue, length):
        runs = [n for n in clue if n > 0]
        return not runs or length - (sum(runs) + len(runs) - 1) < max(runs)

    rows, columns = clues_of(SWEEP_GRID)
    assert any(forces(c, 10) for c in rows), "the sweep board must give Hint a deduction from blank"
    rows, columns = clues_of(STALL_GRID)
    assert not any(forces(c, 7) for c in rows) and not any(forces(c, 6) for c in columns)
    assert not any(c == [0] for c in rows + columns)


# --------------------------------------------------------------------------
# The assembled scratch tree (a throwaway shell; the real assembler is CARD-386)
# --------------------------------------------------------------------------

_BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>{% block title %}{% endblock %}</title>
<link rel="stylesheet" href="/tokens.css"><link rel="stylesheet" href="/admin.css">
<style>[hidden] { display: none !important; }</style></head>
<body><main class="container">{% block content %}{% endblock %}</main>{% block extra_js %}{% endblock %}</body></html>"""


def render_shell(payload: dict, template_text: str | None = None) -> str:
    """The REAL ``puzzle_solve.html`` behind a nine-line base, with ``payload``
    as its data element. ``template_text`` replaces the template (the census
    plant); the include macros are the real ones."""
    templates = {"base.html": _BASE}
    if template_text is not None:
        templates["puzzle_solve.html"] = template_text
    env = jinja2.Environment(
        loader=jinja2.ChoiceLoader([jinja2.DictLoader(templates), jinja2.FileSystemLoader(str(_TEMPLATES))]),
        autoescape=True,
    )
    env.globals["url_for"] = lambda endpoint, filename: f"/{filename}"
    return env.get_template("puzzle_solve.html").render(
        title="",
        extent=(payload["width"], payload["height"]),
        tier_label="MEDIUM",
        payload=payload,
    )


def real_template() -> str:
    return (_TEMPLATES / "puzzle_solve.html").read_text()


def build_tree(root: Path, payload: dict, *, edits=(), template_text: str | None = None, extra_files=()) -> Path:
    """Copy the four admin files, apply ``edits`` ((file, old, new), each ``old``
    exactly once) and write the shell. Returns ``root``."""
    root.mkdir(parents=True, exist_ok=True)
    for name in ADMIN_FILES:
        shutil.copyfile(_STATIC / name, root / name)
    for name, old, new in edits:
        text = (root / name).read_text()
        assert text.count(old) == 1, (name, text.count(old), old[:70])
        (root / name).write_text(text.replace(old, new))
    (root / "index.html").write_text(render_shell(payload, template_text))
    for name, text in extra_files:
        (root / name).write_text(text)
    return root


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs) -> None:  # quiet
        pass


class Served:
    """A loopback static server (GET and HEAD only: SimpleHTTPRequestHandler
    answers anything else with 501, and the sweep fails on the attempt)."""

    def __init__(self, root: Path) -> None:
        handler = functools.partial(_Handler, directory=str(root))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.root = root
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


@pytest.fixture
def serve(tmp_path):
    started: list[Served] = []

    def start(payload: dict, **kwargs) -> Served:
        root = build_tree(tmp_path / f"tree{len(started)}", payload, **kwargs)
        served = Served(root)
        started.append(served)
        return served

    yield start
    for served in started:
        served.stop()


def solution_leaks(root: Path, grid) -> list[str]:
    """Every file under ``root`` that carries the grid: as the flat 0/1 string,
    as a JSON array of booleans (compact or spaced), or as a JSON array of 0/1."""
    needles = [
        flat(grid),
        json.dumps(grid, separators=(",", ":")),
        json.dumps(grid),
        json.dumps([[int(c) for c in row] for row in grid], separators=(",", ":")),
    ]
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            text = path.read_text(errors="ignore")
            if any(needle in text for needle in needles):
                found.append(str(path.relative_to(root)))
    return found


# --------------------------------------------------------------------------
# The controls of the admin template, and the census
# --------------------------------------------------------------------------

#: The attributes that name a CONTROL in puzzle_solve.html. Output elements
#: (counters, readouts, the picture name) are not controls and are not here.
_CONTROL_ATTRIBUTES = (
    "data-player-action", "data-player-confirm", "data-player-tool",
    "data-player-zoom-action", "data-player-probe-action", "data-player-offer",
)
#: Boolean-attribute controls: the attribute alone names the control.
_BARE_CONTROLS = ("data-player-region", "data-player-probe", "data-player-show-grid")


def template_controls(template_text: str) -> set[str]:
    """Every control the template offers, as ``attribute=value`` (or the bare
    attribute) - read from the template text, so a control added there and not
    here is a control the census does not know and the sweep must be taught."""
    found = set()
    for attribute in _CONTROL_ATTRIBUTES:
        for value in re.findall(rf'\b{attribute}="([^"]+)"', template_text):
            found.add(f"{attribute}={value}")
    for attribute in _BARE_CONTROLS:
        if re.search(rf"<button\b[^>]*\b{attribute}(?=[\s>=])(?!-)", template_text):
            found.add(attribute)
    return found


def _selector(control: str) -> str:
    if "=" in control:
        attribute, value = control.split("=", 1)
        return f'[{attribute}="{value}"]'
    return f"[{control}]"


#: Controls solver.js REMOVES in public mode (their statements are about the
#: solution), and so the sweep asserts ABSENT rather than clicks.
ABSENT_IN_PUBLIC = frozenset({"data-player-action=check"})


# --------------------------------------------------------------------------
# Driving the page
# --------------------------------------------------------------------------

_CLICK_RECORDER = """() => {
  // Kept in sessionStorage (not localStorage: the sweep asserts what the page
  // saves) so that a reload in the middle of the sweep does not forget a click.
  window.__clicked = new Set(JSON.parse(sessionStorage.getItem('__clicked') || '[]'));
  const selectors = %s;
  document.addEventListener('click', (event) => {
    for (const [control, selector] of Object.entries(selectors)) {
      if (event.target.closest(selector)) window.__clicked.add(control);
    }
    sessionStorage.setItem('__clicked', JSON.stringify([...window.__clicked]));
  }, true);
}"""


class Watch:
    """Everything that must stay empty: page errors, console errors, failed
    requests, non-GET requests; and every URL requested."""

    def __init__(self, page) -> None:
        self.errors: list[str] = []
        self.non_get: list[str] = []
        self.urls: list[str] = []
        page.on("pageerror", lambda error: self.errors.append(f"pageerror: {error}"))
        page.on("console", lambda m: self.errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("requestfailed", lambda r: self.errors.append(f"requestfailed: {r.url}"))
        page.on("request", self._request)

    def _request(self, request) -> None:
        self.urls.append(request.url)
        if request.method != "GET":
            self.non_get.append(f"{request.method} {request.url}")

    def problems(self) -> list[str]:
        return [*self.errors, *self.non_get]


def cell(page, r, c):
    return page.locator(f'td.player-cell[data-row="{r}"][data-col="{c}"]')


def centre(page, r, c):
    box = cell(page, r, c).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def drag(page, cells, steps=4):
    page.mouse.move(*centre(page, *cells[0]))
    page.mouse.down()
    for target in cells[1:]:
        page.mouse.move(*centre(page, *target), steps=steps)
    page.mouse.up()


def states(page) -> list[str]:
    seen = page.evaluate(
        """() => ({ drawn: [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state),
                    board: [...window.puzzlePlayer.getBoard().cells] })""")
    assert seen["drawn"] == seen["board"], "the drawn board and getBoard() disagree"
    return seen["drawn"]


def action(page, name):
    return page.locator(f'[data-player-action="{name}"]')


def disabled(locator) -> bool:
    return locator.get_attribute("aria-disabled") == "true"


def tool(page, name: str) -> None:
    page.locator("#puzzle-player-tool-trigger").click()
    page.get_by_role("menuitemradio", name=name, exact=True).click()


def open_page(page, served: Served) -> None:
    page.goto(served.url + "/")
    page.wait_for_function("window.puzzlePlayer !== undefined")


def touch(cdp, kind, points=()):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y} for x, y in points]})


@pytest.fixture
def touch_page(browser_type, browser_page):  # noqa: F811
    """A page in a touch-capable context (the sweep pinches), 1280 x 900."""
    context = browser_page.context.browser.new_context(has_touch=True, viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.context_for_test = context
    yield page
    context.close()


# ---- the steps: one function per control, each REALLY drives it ------------------------------


def step_brush_menu(page, ctx):
    """Every brush through the menu, and by keyboard; each paints its state."""
    for name, state in (("Black", FILLED), ("White", EMPTY), ("Maybe", MAYBE), ("Clear", UNKNOWN)):
        tool(page, name)
        for _ in range(3):  # a click follows the brush's sequence
            cell(page, 0, 1).click()
        assert states(page)[1] in (FILLED, EMPTY, MAYBE, UNKNOWN)
    tool(page, "Black")
    page.locator("#puzzle-player-tool-trigger").focus()
    page.keyboard.press("Enter")
    page.keyboard.press("Home")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    assert page.locator("#puzzle-player-tool-trigger").get_attribute("aria-label") == "Brush: White"
    tool(page, "Black")


def step_each_brush(value):
    names = {"filled": "Black", "empty": "White", "maybe": "Maybe", "unknown": "Clear"}

    def run(page, ctx):
        tool(page, names[value])
        cell(page, 2, 2).click()
        drag(page, [(3, 0), (3, 1), (3, 2), (3, 3)])
        tool(page, "Black")

    return run


def step_region(page, ctx):
    """CARD-433 (owner's ruling of 2026-11-12, "Sticky only at 100%/Fit").

    This sweep's board is a 10 x 8 and its stage has no scrollable overflow at
    the zoom the steps before this one leave behind — asserted, because it is
    the premise of everything below: with the whole board in view Region is
    armed from the load, a recorded drag leaves it armed (it is the *panning*
    gesture the one-shot disarm gives back, and there is nothing to pan), and
    only the reader's own press turns it off. The disarm-after-one-drag that
    this step used to drive is CARD-194's behaviour on a board that scrolls,
    which this one does not; it is pinned in
    test_puzzle_solver_brush_menu.py's TestSolverRegion_ArmedDragMarksThenDisarms.
    """
    toggle = page.locator("[data-player-region]")
    assert page.evaluate(
        """() => { const s = document.querySelector('.player-stage');
             return [s.scrollWidth - s.clientWidth, s.scrollHeight - s.clientHeight]; }"""
    ) == [0, 0], "this step is about a board wholly in view"
    assert toggle.get_attribute("aria-pressed") == "true", "armed at load, with the board in view"
    drag(page, [(5, 0), (5, 1), (5, 2), (5, 3), (5, 4)])
    assert toggle.get_attribute("aria-pressed") == "true", "sticky: the drag does not disarm it"
    toggle.click()
    assert toggle.get_attribute("aria-pressed") == "false", "the reader's own press wins"
    tool(page, "Black")
    assert toggle.get_attribute("aria-pressed") == "false", "and a brush pick does not undo it"
    toggle.click()
    assert toggle.get_attribute("aria-pressed") == "true"


def step_undo(page, ctx):
    cell(page, 6, 0).click()
    before = states(page)
    assert not disabled(action(page, "undo"))
    action(page, "undo").click()
    assert states(page) != before
    page.keyboard.press("Control+z")


def step_redo(page, ctx):
    cell(page, 6, 1).click()
    action(page, "undo").click()
    assert not disabled(action(page, "redo"))
    action(page, "redo").click()
    assert states(page)[6 * 10 + 1] == FILLED
    action(page, "undo").click()
    page.keyboard.press("Control+Shift+z")


def step_reset(page, ctx):
    cell(page, 7, 0).click()
    action(page, "reset").click()
    page.locator('[data-player-confirm="cancel"]').click()
    assert states(page)[7 * 10] == FILLED, "Keep marks must keep them"
    action(page, "reset").click()
    page.keyboard.press("Escape")
    action(page, "reset").click()
    page.locator('[data-player-confirm="accept"]').click()
    assert set(states(page)) == {UNKNOWN}


def step_zoom_out(page, ctx):
    page.locator('[data-player-zoom-action="in"]').click()
    page.locator('[data-player-zoom-action="out"]').click()
    assert page.locator("[data-player-zoom-readout]").inner_text() == "100%"


def _zoom_to(page, direction: str, limit: str) -> None:
    """Press a zoom button until it disables itself at its limit (100 or 300)."""
    button = page.locator(f'[data-player-zoom-action="{direction}"]')
    for _ in range(20):
        if disabled(button):
            break
        button.click()
    assert page.locator("[data-player-zoom-readout]").inner_text() == limit


def step_zoom_in(page, ctx):
    _zoom_to(page, "in", "300%")
    _zoom_to(page, "out", "100%")


def step_hint(page, ctx):
    """Rungs 1, 2 and 3 and BEYOND: press until the button is disabled or the
    board is solved, then once more on the disabled button."""
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
    for _ in range(3 * 90):
        if disabled(hint) or page.locator("#puzzle-player-solved").is_visible() or \
                page.locator("#puzzle-player-explain").inner_text() == public_exhausted_sentence():
            break
        hint.click()
    assert (disabled(hint) or page.locator("#puzzle-player-solved").is_visible()
            or page.locator("#puzzle-player-explain").inner_text() == public_exhausted_sentence()), \
        "the ladder ran out of presses"
    hint.click(force=True)  # beyond: a locked Hint is inert, an exhausted one repeats its sentence


def step_check_is_absent(page, ctx):
    assert action(page, "check").count() == 0, "Check is a statement about the solution: absent in public mode"
    assert page.locator("#puzzle-player-errors, #puzzle-player-progress").count() == 0


def step_probe(page, ctx):
    toggle = page.locator("[data-player-probe]")
    keep = page.locator('[data-player-probe-action="keep"]')
    abandon = page.locator('[data-player-probe-action="abandon"]')
    cell(page, 0, 9).click()
    toggle.click()
    assert toggle.get_attribute("aria-pressed") == "true"
    cell(page, 1, 9).click()
    keep.click()
    assert toggle.get_attribute("aria-pressed") == "false"
    toggle.click()
    cell(page, 2, 9).click()
    abandon.click()
    assert toggle.get_attribute("aria-pressed") == "false"


def step_offer(page, ctx):
    """CARD-412: the Wrong-guess offer in public mode — it reads the history
    only, so it is offered here too; No thanks changes nothing, Mark it
    records the other colour as one undoable stroke."""
    toggle = page.locator("[data-player-probe]")
    abandon = page.locator('[data-player-probe-action="abandon"]')
    offer = page.locator("#puzzle-player-offer")
    before = states(page)
    toggle.click()
    cell(page, 3, 9).click()
    abandon.click()
    assert offer.is_visible() and "must be white" in offer.inner_text()
    page.locator('[data-player-offer="dismiss"]').click()
    assert not offer.is_visible() and states(page) == before
    toggle.click()
    cell(page, 3, 9).click()
    abandon.click()
    page.locator('[data-player-offer="mark"]').click()
    assert not offer.is_visible() and states(page)[3 * 10 + 9] == EMPTY
    action(page, "undo").click()
    assert states(page) == before


def step_show_grid(page, ctx):
    """CARD-280: on a solved board the picture shows without its worksheet,
    and "Show grid" puts the worksheet back and takes it away again."""
    if not page.locator("#puzzle-player-solved").is_visible():
        solve_to_the_end(page, SWEEP_GRID)
    toggle = page.locator("[data-player-show-grid]")
    board = page.locator(".player-board")
    assert toggle.is_visible() and "is-showing-grid" not in board.get_attribute("class")
    toggle.click()
    assert "is-showing-grid" in board.get_attribute("class") and toggle.get_attribute("aria-pressed") == "true"
    toggle.click()
    assert "is-showing-grid" not in board.get_attribute("class")


def step_crosshair(page, ctx):
    page.mouse.move(*centre(page, 3, 4))
    assert page.locator(".is-crossed").count() > 0
    page.mouse.move(0, 0)


def step_same_count_wrong_board(page, ctx):
    """F-1: a board with as many filled cells as the solution has, in the wrong
    places, completed under an OPEN probe: it is not solved (no banner, no lock)
    and the probe does not commit. Solved means the clues are met, not that the
    number of black cells is right."""
    if not disabled(action(page, "reset")):
        action(page, "reset").click()
        page.locator('[data-player-confirm="accept"]').click()
    solution = [(r, c) for r, row in enumerate(SWEEP_GRID) for c, v in enumerate(row) if v]
    blank = next((r, c) for r, row in enumerate(SWEEP_GRID) for c, v in enumerate(row) if not v)
    wrong = solution[1:] + [blank]  # one solution cell moved: same count, wrong place
    assert len(wrong) == len(solution) and set(wrong) != set(solution)
    probe = page.locator("[data-player-probe]")
    probe.click()
    assert probe.get_attribute("aria-pressed") == "true"
    for r, c in wrong:
        cell(page, r, c).click()
    assert not page.locator("#puzzle-player-solved").is_visible(), "a same-count wrong board was called solved"
    assert not page.evaluate("document.querySelector('.player-board').classList.contains('is-solved')")
    assert probe.get_attribute("aria-pressed") == "true", "a same-count wrong board committed the probe"
    assert not disabled(action(page, "undo")), "the board is locked"
    page.locator('[data-player-probe-action="abandon"]').click()
    assert set(states(page)) == {UNKNOWN}, "Contradiction restores the board the probe opened on"


def step_pinch(page, ctx):
    cdp = page.context.new_cdp_session(page)
    cx, cy = centre(page, 4, 5)
    touch(cdp, "touchStart", [(cx - 50, cy), (cx + 50, cy)])
    touch(cdp, "touchMove", [(cx - 100, cy), (cx + 100, cy)])
    touch(cdp, "touchEnd")
    page.wait_for_timeout(250)
    assert int(page.locator("[data-player-zoom-readout]").inner_text().rstrip("%")) > 100
    _zoom_to(page, "out", "100%")


CONTROL_STEPS = {
    "data-player-tool=filled": step_each_brush("filled"),
    "data-player-tool=empty": step_each_brush("empty"),
    "data-player-tool=maybe": step_each_brush("maybe"),
    "data-player-tool=unknown": step_each_brush("unknown"),
    "data-player-region": step_region,
    "data-player-action=undo": step_undo,
    "data-player-action=redo": step_redo,
    "data-player-action=reset": step_reset,
    "data-player-confirm=accept": step_reset,
    "data-player-confirm=cancel": step_reset,
    "data-player-zoom-action=in": step_zoom_in,
    "data-player-zoom-action=out": step_zoom_out,
    "data-player-action=check": step_check_is_absent,
    "data-player-probe": step_probe,
    "data-player-probe-action=keep": step_probe,
    "data-player-probe-action=abandon": step_probe,
    "data-player-offer=mark": step_offer,
    "data-player-offer=dismiss": step_offer,
    # LAST: Hint taken to the end may solve this board, and a solved board is
    # locked. run_sweep wipes the save afterwards.
    "data-player-action=hint": step_hint,
    # After Hint: it needs the solved board Hint may have made (CARD-280).
    "data-player-show-grid": step_show_grid,
}

#: Gestures that are not one control: run by the sweep in addition.
GESTURE_STEPS = {
    "brush-menu": step_brush_menu,
    "crosshair": step_crosshair,
    "pinch": step_pinch,
    "same-count-wrong-board": step_same_count_wrong_board,
}


def census_problems(template_text: str, steps: dict) -> list[str]:
    """What the sweep does not know: a control with no step, and a step for a
    control the template does not have."""
    controls = template_controls(template_text)
    problems = [f"unswept control: {c}" for c in sorted(controls - set(steps))]
    problems += [f"step for a control the template lacks: {c}" for c in sorted(set(steps) - controls)]
    return problems


def solve_to_the_end(page, grid, ctx=None) -> None:
    """Reset, open a probe, click every solution cell: the LAST click solves the
    board while the probe is open (rule 7's auto-commit, decided from the clues)."""
    cells = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v]
    if not disabled(action(page, "reset")):
        action(page, "reset").click()
        page.locator('[data-player-confirm="accept"]').click()
    probe = page.locator("[data-player-probe]")
    for r, c in cells[:-1]:
        cell(page, r, c).click()
    probe.click()
    assert probe.get_attribute("aria-pressed") == "true"
    r, c = cells[-1]
    cell(page, r, c).click()
    assert page.locator("#puzzle-player-solved").is_visible(), "the Solved banner (from the clues alone)"
    assert probe.get_attribute("aria-pressed") == "false", "a probe that reached the solution commits (rule 7)"
    assert page.evaluate("document.querySelector('.player-board').classList.contains('is-solved')")


class SweepResult:
    def __init__(self, watch: Watch, clicked: set[str], steps_run: list[str], served: Served) -> None:
        self.watch, self.clicked, self.steps_run, self.served = watch, clicked, steps_run, served


def run_sweep(page, served: Served, watch: Watch, grid=SWEEP_GRID, steps=None) -> SweepResult:
    """Every control, every gesture, the solve, the reload: returns what was
    watched. ``steps`` replaces the control registry (the census plant)."""
    steps = CONTROL_STEPS if steps is None else steps
    page.add_init_script(
        "(" + _CLICK_RECORDER % json.dumps({c: _selector(c) for c in sorted(template_controls(real_template()))}) + ")()"
    )
    open_page(page, served)
    assert page.locator("td.player-cell").count() == len(grid) * len(grid[0])
    ran: list[str] = []
    for name, step in {**GESTURE_STEPS}.items():
        step(page, None)
        ran.append(name)
    done = set()
    for control, step in steps.items():
        if step in done:
            continue
        step(page, None)
        done.add(step)
        ran.append(control)
    # Hint taken to the end may have solved the board and locked it; start the
    # solve from a clean board with no save.
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.puzzlePlayer !== undefined")
    assert not page.locator("#puzzle-player-solved").is_visible()
    solve_to_the_end(page, grid)
    ran.append("solve")
    clicked = set(page.evaluate("[...window.__clicked]"))
    # Reload and resume: the save brings the solved board back, from the clues.
    keys = page.evaluate("Object.keys(localStorage)")
    page.reload()
    page.wait_for_function("window.puzzlePlayer !== undefined")
    assert page.locator("#puzzle-player-solved").is_visible(), "a reload resumes the solved board"
    assert keys == [f"nonogram-player:{SWEEP_ID}"], keys
    ran.append("reload")
    return SweepResult(watch, clicked, ran, served)


# ==========================================================================
# AC-1 - the board draws and the whole sweep completes clean
# ==========================================================================


@pytest.mark.browser
class TestPublicMode_TheSweep:
    def test_the_census_and_the_sweep_agree_on_the_real_template(self) -> None:
        assert census_problems(real_template(), CONTROL_STEPS) == []

    def test_every_control_is_driven_and_nothing_goes_wrong(self, touch_page, serve) -> None:
        """AC-1."""
        served = serve(public_payload(SWEEP_GRID))
        result = run_sweep(touch_page, served, Watch(touch_page))
        assert result.watch.problems() == []
        expected = template_controls(real_template()) - ABSENT_IN_PUBLIC
        assert expected <= result.clicked, sorted(expected - result.clicked)
        # And the requests: only the tree's own files, all GET.
        assert result.watch.non_get == []
        assert {u.split(served.url)[-1] for u in result.watch.urls} <= {
            "/", "/solver.js", "/solver_state.js", "/admin.css", "/tokens.css"}

    def test_the_stall_board_has_a_disabled_hint_and_reveals_nothing(self, browser_page, serve) -> None:
        watch = Watch(browser_page)
        served = serve(public_payload(STALL_GRID, puzzle_id="stall"))
        open_page(browser_page, served)
        # CARD-385 fix round (F-3): the id is kept (G-5) and the claim moved.
        # Hint used to be DISABLED here (a dead button with no reason); it now
        # stays enabled and says the public sentence. Nothing is revealed.
        assert not disabled(action(browser_page, "hint")), "undecided cells remain: Hint stays on"
        before = states(browser_page)
        action(browser_page, "hint").click()
        assert states(browser_page) == before
        assert browser_page.locator("#puzzle-player-explain").inner_text() == public_exhausted_sentence()
        assert watch.problems() == []


# ==========================================================================
# The checks: each returns the list of ways its property is lost, so that the
# same function is a test on the real files ([] expected) and the verdict on a
# mutant of them (non-empty expected) - a claim and its control in one run.
# ==========================================================================


def sweep_problems(page, served: Served, grid=SWEEP_GRID, steps=None, timeout=10000) -> list[str]:
    page.set_default_timeout(timeout)
    watch = Watch(page)
    problems: list[str] = []
    try:
        result = run_sweep(page, served, watch, grid, steps)
        expected = template_controls(real_template()) - ABSENT_IN_PUBLIC
        problems += [f"control never clicked: {c}" for c in sorted(expected - result.clicked)]
    except Exception as error:  # noqa: BLE001 - any way the sweep fails is a problem found
        problems.append(f"sweep aborted: {type(error).__name__}: {str(error).splitlines()[0][:160]}")
    problems += watch.problems()
    problems += [f"solution in served file: {f}" for f in solution_leaks(served.root, grid)]
    return problems


def stall_problems(page, served: Served, timeout=3000) -> list[str]:
    """On a board no line decides, Hint is still offered, says why nothing is
    offered in the public sentence (explain line AND announce region), reveals
    nothing, records nothing, counts nothing, and does not climb the ladder."""
    page.set_default_timeout(timeout)
    watch = Watch(page)
    problems: list[str] = []
    try:
        open_page(page, served)
        problems += exhausted_press_problems(page)
    except Exception as error:  # noqa: BLE001
        problems.append(f"aborted: {type(error).__name__}: {str(error).splitlines()[0][:160]}")
    return problems + watch.problems()


def exhausted_press_problems(page) -> list[str]:
    problems: list[str] = []
    hint = action(page, "hint")
    if disabled(hint):
        problems.append("Hint is disabled where cells are undecided and no line decides one (a dead button)")
    before = states(page)
    sentence = public_exhausted_sentence()
    for press in range(4):  # past three: the ladder must not reach a reveal
        hint.click(force=True)
        if page.locator("#puzzle-player-explain").inner_text() != sentence:
            problems.append(f"press {press + 1}: the explain line is {page.locator('#puzzle-player-explain').inner_text()!r}")
        if page.locator("#puzzle-player-announce").inner_text() != sentence:
            problems.append(f"press {press + 1}: the announce region is {page.locator('#puzzle-player-announce').inner_text()!r}")
    if states(page) != before:
        problems.append("Hint changed a cell on a board where no line decides one")
    if page.locator("[data-player-hints]").inner_text() != "0":
        problems.append("a hint was counted where none was derivable")
    if not disabled(action(page, "undo")):
        problems.append("a stroke was recorded by a press that has no cell")
    if page.locator(".is-hint-line, .is-hinted").count() != 0:
        problems.append("something was highlighted where no line decides a cell")
    return problems


def refusal_problems(page, served: Served, timeout=3000) -> list[str]:
    """A public payload that carries a solution is refused: no board, no
    window.puzzlePlayer, and the stage says why."""
    page.set_default_timeout(timeout)
    page.goto(served.url + "/")
    page.wait_for_timeout(400)
    problems = []
    if page.evaluate("window.puzzlePlayer !== undefined"):
        problems.append("window.puzzlePlayer was set for a public payload that carries a solution")
    if page.locator("td.player-cell").count() != 0:
        problems.append("a board was drawn from a public payload that carries a solution")
    if "solution" not in page.locator("#puzzle-player").inner_text():
        problems.append("the refusal does not say why: " + page.locator("#puzzle-player").inner_text()[:80])
    return problems


def save_problems(page, served: Served, timeout=5000) -> list[str]:
    """A public save: the admin's key, a constant stamp, no solution anywhere,
    resumed on reload, and a save stamped by an admin page's fingerprint is
    refused and forgotten."""
    page.set_default_timeout(timeout)
    watch = Watch(page)
    problems: list[str] = []
    try:
        open_page(page, served)
        cell(page, 0, 0).click()
        cell(page, 0, 1).click()
        cell(page, 1, 1).click()
        marked = states(page)
        key = f"nonogram-player:{SWEEP_ID}"
        keys = page.evaluate("Object.keys(localStorage)")
        if keys != [key]:
            problems.append(f"storage keys {keys}, not [{key!r}]")
        text = page.evaluate(f"localStorage.getItem({json.dumps(key)})")
        saved = json.loads(text)
        if saved.get("grid") != "public":
            problems.append(f"the save's stamp is {saved.get('grid')!r}, not the constant 'public'")
        if "solution" in text or flat(SWEEP_GRID) in text:
            problems.append("the save mentions the solution")
        page.reload()
        page.wait_for_function("window.puzzlePlayer !== undefined")
        if states(page) != marked:
            problems.append("a reload did not resume the marks")
        saved["grid"] = "0badf00d"  # an admin page's kind of stamp
        page.evaluate(f"localStorage.setItem({json.dumps(key)}, {json.dumps(json.dumps(saved))})")
        page.reload()
        page.wait_for_function("window.puzzlePlayer !== undefined")
        if set(states(page)) != {UNKNOWN}:
            problems.append("a save with another page's stamp was resumed")
        if page.evaluate(f"localStorage.getItem({json.dumps(key)})") is not None:
            problems.append("a save with another page's stamp was not forgotten")
    except Exception as error:  # noqa: BLE001
        problems.append(f"aborted: {type(error).__name__}: {str(error).splitlines()[0][:160]}")
    return problems + watch.problems()


def admin_payload(grid, **extra) -> dict:
    payload = public_payload(grid, **extra)
    del payload["mode"]
    payload["solution"] = grid
    return payload


def admin_mode_problems(page, served: Served, timeout=5000) -> list[str]:
    """The default mode is what it was: Errors, Progress and Check are there and
    count against the answer, Hint has its answer-reveal fallback, a "?"
    anywhere stops a board being solved, and a public-mode save is not read."""
    page.set_default_timeout(timeout)
    watch = Watch(page)
    problems: list[str] = []
    grid = STALL_GRID
    try:
        open_page(page, served)
        for selector in ("#puzzle-player-errors", "#puzzle-player-progress", '[data-player-action="check"]'):
            if page.locator(selector).count() != 1:
                problems.append(f"admin mode lost {selector}")
        if disabled(action(page, "hint")):
            problems.append("admin Hint is disabled where its fallback reveals a cell")
        wrong = next((r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if not v)
        cell(page, *wrong).click()  # Black on a white cell: one error
        if page.locator("[data-player-errors]").inner_text() != "1":
            problems.append("admin Errors did not count a wrong mark")
        cell(page, *wrong).click()
        cell(page, *wrong).click()  # back to blank
        mark = next((r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if not v and (r, c) != wrong)
        tool(page, "Maybe")
        cell(page, *mark).click()
        tool(page, "Black")
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                if v:
                    cell(page, r, c).click()
        if page.locator("#puzzle-player-solved").is_visible():
            problems.append("admin mode called a board with a '?' on it solved")
        tool(page, "Clear")
        cell(page, *mark).click()
        if not page.locator("#puzzle-player-solved").is_visible():
            problems.append("admin mode did not call the solution solved")
        if page.locator("[data-player-progress]").inner_text() != "100%":
            problems.append("admin Progress did not reach 100%")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_function("window.puzzlePlayer !== undefined")
        hint = action(page, "hint")
        for _ in range(3):
            hint.click()
        if "(from the solution)" not in page.locator("#puzzle-player-announce").inner_text() or \
                page.locator("[data-player-hints]").inner_text() != "1":
            problems.append("admin Hint's third press did not reveal from the solution")
        saved = json.loads(page.evaluate(f"localStorage.getItem('nonogram-player:{SWEEP_ID}')"))
        if saved["grid"] == "public" or not re.fullmatch(r"[0-9a-f]{8}", saved["grid"]):
            problems.append(f"an admin save is stamped {saved['grid']!r}, not a fingerprint")
        saved["grid"] = "public"  # a public page's stamp, on a save whose strokes would otherwise resume
        page.evaluate(f"localStorage.setItem('nonogram-player:{SWEEP_ID}', {json.dumps(json.dumps(saved))})")
        page.reload()
        page.wait_for_function("window.puzzlePlayer !== undefined")
        if set(states(page)) != {UNKNOWN}:
            problems.append("a save stamped by a public page was resumed in admin mode")
        if page.evaluate(f"localStorage.getItem('nonogram-player:{SWEEP_ID}')") is not None:
            problems.append("a save stamped by a public page was not forgotten in admin mode")
    except Exception as error:  # noqa: BLE001
        problems.append(f"aborted: {type(error).__name__}: {str(error).splitlines()[0][:160]}")
    return problems + watch.problems()


# --------------------------------------------------------------------------
# AC-2, the save, the admin's default, the stall board, on the real files
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestPublicMode_ThePayload:
    def test_a_public_payload_with_a_solution_is_refused(self, browser_page, serve) -> None:
        """AC-2 - and the matched control: the same page without it draws."""
        refused = serve(public_payload(SWEEP_GRID, solution=SWEEP_GRID))
        assert refusal_problems(browser_page, refused) == []
        page = browser_page.context.new_page()
        drawn = serve(public_payload(SWEEP_GRID))
        page.goto(drawn.url + "/")
        page.wait_for_function("window.puzzlePlayer !== undefined")
        assert page.locator("td.player-cell").count() == 80

    def test_even_a_null_or_empty_solution_key_is_refused(self, browser_page, serve) -> None:
        for value in (None, [], [[]], False):
            page = browser_page.context.new_page()
            served = serve(public_payload(SWEEP_GRID, solution=value))
            assert refusal_problems(page, served) == [], value
            page.close()

    def test_a_public_payload_is_still_checked_for_its_shape(self, browser_page, serve) -> None:
        broken = public_payload(SWEEP_GRID)
        broken["rows"] = broken["rows"][:-1]
        served = serve(broken)
        browser_page.goto(served.url + "/")
        browser_page.wait_for_timeout(300)
        assert browser_page.evaluate("window.puzzlePlayer === undefined")
        assert browser_page.locator("td.player-cell").count() == 0

    def test_the_default_mode_still_needs_its_solution(self, browser_page, serve) -> None:
        """Admin mode, unchanged: no solution, no board."""
        payload = admin_payload(SWEEP_GRID)
        del payload["solution"]
        served = serve(payload)
        browser_page.goto(served.url + "/")
        browser_page.wait_for_timeout(300)
        assert browser_page.evaluate("window.puzzlePlayer === undefined")
        assert browser_page.locator("td.player-cell").count() == 0

    def test_the_solution_getter_throws_in_public_mode_and_is_not_serialised(self, browser_page, serve) -> None:
        served = serve(public_payload(SWEEP_GRID))
        open_page(browser_page, served)
        seen = browser_page.evaluate(
            """() => {
              const p = window.puzzlePlayer.payload;
              let thrown = null;
              try { p.solution; } catch (e) { thrown = String(e.message); }
              return { thrown, listed: Object.keys(p), json: JSON.stringify(p), has: 'solution' in p };
            }""")
        assert seen["thrown"] and "public mode" in seen["thrown"]
        assert "solution" not in seen["listed"] and "solution" not in seen["json"]


@pytest.mark.browser
class TestPublicMode_TheSave:
    def test_the_save_carries_a_constant_stamp_and_resumes(self, browser_page, serve) -> None:
        assert save_problems(browser_page, serve(public_payload(SWEEP_GRID))) == []


@pytest.mark.browser
class TestPublicMode_TheStallBoard:
    def test_hint_offers_and_reveals_nothing_where_no_line_decides(self, browser_page, serve) -> None:
        """Id kept (G-5); since the F-3 fix Hint is offered AND says why."""
        assert stall_problems(browser_page, serve(public_payload(STALL_GRID, puzzle_id="stall"))) == []

    def test_the_oracle_s_stalled_boards_drive_it(self, browser_page, serve) -> None:
        """Boards the brute-force oracle says no line decides (half of them
        holding a '?'): Hint is enabled and says the sentence on each; and a
        fully decided board that is not solved has nothing to hint, so it is
        disabled (the same rule play.js's canHint had)."""
        stalled = [c for c in hint_corpus() if c["w"] <= ORACLE_MAX_SIDE and c["h"] <= ORACLE_MAX_SIDE
                   and oracle_hint(c["cells"], c["w"], c["h"], c["rows"], c["cols"]) is None
                   and any(s in (UNKNOWN, MAYBE) for s in c["cells"])]
        assert len(stalled) >= 30 and sum(MAYBE in c["cells"] for c in stalled) >= 10
        for n, case in enumerate(stalled[:24]):
            served = serve(public_payload(case["grid"], puzzle_id=f"stalled{n}"))
            page = browser_page.context.new_page()
            open_page(page, served)
            page.evaluate(
                """async (cells) => { const S = await import('/solver_state.js'); const b = window.puzzlePlayer.getBoard();
                   window.puzzlePlayer.setBoard(Object.freeze({ width: b.width, height: b.height, cells: Object.freeze(cells) })); }""",
                case["cells"])
            assert exhausted_press_problems(page) == [], (n, case["cells"])
            page.close()
        page = browser_page.context.new_page()
        open_page(page, serve(public_payload(STALL_GRID, puzzle_id="decided")))
        page.evaluate(
            """() => { const b = window.puzzlePlayer.getBoard();
               window.puzzlePlayer.setBoard(Object.freeze({ width: b.width, height: b.height,
                 cells: Object.freeze(b.cells.map(() => 'filled')) })); }""")
        assert disabled(action(page, "hint")), "no undecided cell: nothing to say, nothing to reveal"


@pytest.mark.browser
class TestPublicMode_TheAdminDefaultIsUnchanged:
    def test_errors_progress_check_the_fallback_and_the_fingerprint_are_all_there(self, browser_page, serve) -> None:
        served = serve(admin_payload(STALL_GRID, puzzle_id=SWEEP_ID))
        assert admin_mode_problems(browser_page, served) == []


# ==========================================================================
# AC-4 / G-3 - nothing served carries the answer, nothing reaches a network
# ==========================================================================


class TestPublicMode_NothingServedCarriesTheSolution:
    def test_the_assembled_tree_carries_no_solution_in_any_encoding(self, tmp_path) -> None:
        root = build_tree(tmp_path / "t", public_payload(SWEEP_GRID))
        assert sorted(p.name for p in root.iterdir()) == sorted([*ADMIN_FILES, "index.html"])
        assert solution_leaks(root, SWEEP_GRID) == []

    @pytest.mark.parametrize("encoding", ["flat", "json", "json-spaced", "zero-one"])
    def test_a_plant_that_serves_the_solution_reds_the_scan(self, tmp_path, encoding) -> None:
        text = {
            "flat": flat(SWEEP_GRID),
            "json": json.dumps(SWEEP_GRID, separators=(",", ":")),
            "json-spaced": json.dumps(SWEEP_GRID),
            "zero-one": json.dumps([[int(c) for c in row] for row in SWEEP_GRID], separators=(",", ":")),
        }[encoding]
        clean = build_tree(tmp_path / "clean", public_payload(SWEEP_GRID))
        planted = build_tree(tmp_path / "planted", public_payload(SWEEP_GRID),
                             extra_files=[("puzzle.json", "{" + f'"x": {text}' + "}")]
                             if encoding != "flat" else [("puzzle.txt", text)])
        assert solution_leaks(clean, SWEEP_GRID) == []
        assert solution_leaks(planted, SWEEP_GRID) != []

    def test_a_payload_that_ships_the_solution_is_what_the_scan_exists_to_find(self, tmp_path) -> None:
        root = build_tree(tmp_path / "t", public_payload(SWEEP_GRID, solution=SWEEP_GRID))
        assert solution_leaks(root, SWEEP_GRID) == ["index.html"]


_NETWORK = re.compile(r"\b(?:fetch|XMLHttpRequest|sendBeacon|WebSocket|EventSource|importScripts)\b|\bimport\s*\(")


def code_of(text: str) -> str:
    """The file with its ``//`` comment lines dropped."""
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))


def network_calls(text: str) -> list[str]:
    return _NETWORK.findall(code_of(text))


class TestPublicMode_NoNetworkInAnyMode:
    """G-3."""

    @pytest.mark.parametrize("name", ["solver.js", "solver_state.js"])
    def test_the_admin_player_files_contain_no_network_call(self, name) -> None:
        assert network_calls((_STATIC / name).read_text()) == []

    @pytest.mark.parametrize("call", [
        'fetch("/x")', "new XMLHttpRequest()", "navigator.sendBeacon('/x')", "new WebSocket('ws://x')",
        "import('/x.js')", "new EventSource('/x')",
    ])
    def test_a_plant_of_each_kind_reds_the_scan(self, call) -> None:
        text = (_STATIC / "solver.js").read_text()
        assert network_calls(text) == [] and network_calls(text + f"\n{call};\n") != []


# ==========================================================================
# AC-5 - the census: every control has a sweep step that really drives it
# ==========================================================================


class TestPublicMode_TheCensus:
    def test_the_template_has_the_controls_the_census_expects(self) -> None:
        assert template_controls(real_template()) == {
            "data-player-action=undo", "data-player-action=redo", "data-player-action=reset",
            "data-player-action=hint", "data-player-action=check",
            "data-player-confirm=accept", "data-player-confirm=cancel",
            "data-player-tool=filled", "data-player-tool=empty", "data-player-tool=maybe", "data-player-tool=unknown",
            "data-player-zoom-action=in", "data-player-zoom-action=out",
            "data-player-probe-action=keep", "data-player-probe-action=abandon",
            "data-player-offer=mark", "data-player-offer=dismiss",
            "data-player-region", "data-player-probe", "data-player-show-grid",
        }

    def test_the_real_template_is_fully_swept_and_a_plant_is_not(self) -> None:
        text = real_template()
        assert census_problems(text, CONTROL_STEPS) == []
        planted = text.replace(
            '<button type="button" class="btn btn-outline-secondary" data-player-action="hint"',
            '<button type="button" data-player-action="shuffle">Shuffle</button>\n'
            '        <button type="button" class="btn btn-outline-secondary" data-player-action="hint"')
        assert planted != text
        assert census_problems(planted, CONTROL_STEPS) == ["unswept control: data-player-action=shuffle"]
        assert census_problems(text, {k: v for k, v in CONTROL_STEPS.items() if k != "data-player-action=redo"}) == [
            "unswept control: data-player-action=redo"]
        assert census_problems(text, {**CONTROL_STEPS, "data-player-action=ghost": step_undo}) == [
            "step for a control the template lacks: data-player-action=ghost"]

    @pytest.mark.parametrize("attribute", [*_CONTROL_ATTRIBUTES])
    def test_every_control_family_is_read_by_the_census(self, attribute) -> None:
        text = real_template()
        assert any(c.startswith(attribute + "=") for c in template_controls(text))
        # The anchor is the toolbar's close; since CARD-409 the stage sits in a
        # .player-stage-wrap with the answer line, after a template comment —
        # whose card number CARD-427 changed when the owner's ruling of
        # 2026-11-11 centred that line in the viewport. The anchor is the
        # comment's opening, so it is re-pinned rather than re-claimed.
        planted = text.replace("</div>\n</div>\n\n{# CARD-427",
                               f'<button {attribute}="ghost">?</button></div>\n</div>\n\n{{# CARD-427')
        assert planted != text and f"{attribute}=ghost" in template_controls(planted)

    def test_an_unclicked_step_is_found_by_the_sweep_not_only_by_the_census(self, touch_page, serve) -> None:
        """A registry entry that does not drive its control (here: Redo's step
        replaced by one that looks at the page and clicks nothing) passes the
        census and is caught by the click recorder."""
        looked = lambda page, ctx: states(page)  # noqa: E731
        steps = {**CONTROL_STEPS, "data-player-action=redo": looked}
        assert census_problems(real_template(), steps) == []
        problems = sweep_problems(touch_page, serve(public_payload(SWEEP_GRID)), steps=steps, timeout=4000)
        assert "control never clicked: data-player-action=redo" in problems, problems


@pytest.mark.browser
class TestPublicMode_TheSweepOfTheRealFiles:
    def test_the_sweep_is_clean(self, touch_page, serve) -> None:
        """AC-1 + AC-4: every control, every gesture, the solve and the reload,
        with zero page errors, console errors and non-GET requests, and the
        solution in no served file."""
        served = serve(public_payload(SWEEP_GRID))
        problems = sweep_problems(touch_page, served)
        assert problems == []
        assert solution_leaks(served.root, SWEEP_GRID) == []

    def test_the_sweep_drives_what_it_says_it_drives(self, touch_page, serve) -> None:
        served = serve(public_payload(SWEEP_GRID))
        result = run_sweep(touch_page, served, Watch(touch_page))
        assert result.steps_run[: len(GESTURE_STEPS)] == list(GESTURE_STEPS)
        assert result.steps_run[-2:] == ["solve", "reload"]
        assert template_controls(real_template()) - ABSENT_IN_PUBLIC <= result.clicked
        assert result.clicked <= template_controls(real_template())
        assert result.watch.non_get == []
        assert {u.removeprefix(served.url) for u in result.watch.urls} <= {
            "/", "/solver.js", "/solver_state.js", "/admin.css", "/tokens.css"}


# ==========================================================================
# The solution-reading sites: every one listed, each with its gate
# ==========================================================================

#: (file, a regex the read's line matches, how it is gated). The sweep proves
#: the gates by behaviour (the sealed getter throws on any ungated read); THIS
#: table makes a tenth read an event: `payload.solution` in code appears on
#: exactly these lines and no others.
SOLUTION_SITES = [
    ("solver.js", r"isSolution\(payload\.solution", "readPayload: only when payload.mode !== PUBLIC_MODE"),
    ("solver.js", r"boardOfGrid\(payload\.solution", "edit mode's start board: `editing`, exclusive with public"),
    ("solver.js", r"errorCount\(history\.board, payload\.solution", "showProgress: inside `if (!publicMode)`"),
    ("solver.js", r"solvedPercent\(history\.board, payload\.solution", "showProgress: inside `if (!publicMode)`"),
    ("solver.js", r": isSolved\(history\.board, payload\.solution", "showProgress: the else arm of `publicMode ?`"),
    ("solver.js", r"hintCell\(.*publicMode \? null : payload\.solution", "nextHint: `publicMode ? null :`"),
    ("solver.js", r"publicMode \? null : payload\.solution, hint", "hintLine: `publicMode ? null :`"),
    ("solver.js", r"firstWrongRow\(history\.board, payload\.solution", "Check: UNREACHABLE, its button is removed in public mode"),
    ("solver.js", r": isSolved\(candidate, payload\.solution", "solves: the else arm of `publicMode ?`"),
    ("solver_state.js", r"gridFingerprint\(payload\.solution", "stampOf: the else arm of `payload.mode === PUBLIC_MODE ?`"),
]


def solution_read_lines(name: str) -> list[str]:
    return [line.strip() for line in code_of((_STATIC / name).read_text()).splitlines()
            if re.search(r"\bpayload\.solution\b", line)]


class TestPublicMode_EverySolutionReadIsListedAndGated:
    def test_the_reads_are_exactly_the_listed_sites(self) -> None:
        for name in ("solver.js", "solver_state.js"):
            lines = solution_read_lines(name)
            wanted = [(rx, gate) for f, rx, gate in SOLUTION_SITES if f == name]
            # every read line is covered by exactly one site pattern, every site by a line
            for line in lines:
                assert sum(bool(re.search(rx, line)) for rx, _ in wanted) == 1, (name, line)
            for rx, gate in wanted:
                assert sum(bool(re.search(rx, line)) for line in lines) == 1, (name, rx, gate)
        assert len(solution_read_lines("solver.js")) == 9
        assert len(solution_read_lines("solver_state.js")) == 1

    def test_a_tenth_read_is_found(self) -> None:
        text = (_STATIC / "solver.js").read_text()
        planted = text.replace("  if (publicMode) sealSolution(payload);\n",
                               "  if (publicMode) sealSolution(payload);\n  const leak = payload.solution;\n")
        assert planted != text
        assert len([ln for ln in code_of(planted).splitlines() if re.search(r"\bpayload\.solution\b", ln)]) == 10

    def test_the_gated_calls_are_exactly_the_ones_the_gates_name(self) -> None:
        """A read that is gated by NAME: each gate's text is present, in the
        place it guards (the behavioural proof is the sweep and the mutants)."""
        solver = code_of((_STATIC / "solver.js").read_text())
        assert solver.count("publicMode ? null : payload.solution") == 2
        assert "if (publicMode) sealSolution(payload);" in solver
        assert 'PUBLIC_ABSENT = \'#puzzle-player-errors, #puzzle-player-progress, [data-player-action="check"]\'' in solver
        state = code_of((_STATIC / "solver_state.js").read_text())
        for fn in ("errorCount", "isSolved", "firstWrongRow", "gridFingerprint"):
            assert re.search(rf'requireSolution\(solution, "{fn}"\)', state), fn


# ==========================================================================
# AC-6 / G-6 - the solution-free deduction, against a brute-force oracle and
# on seeded corpora (CARD-399: no longer compared with player/play.js)
# ==========================================================================


def _placements(runs: list[int], length: int):
    """Every 0/1 line of ``length`` whose runs are ``runs`` (enumeration: it
    shares no reasoning with lineForced's or forcedLine's reachability)."""
    if not runs:
        yield (False,) * length
        return
    first, rest = runs[0], runs[1:]
    need = sum(rest) + len(rest)  # the cells the remaining runs and their gaps take
    for start in range(0, length - first - need + 1):
        head = (False,) * start + (True,) * first
        if rest:
            for tail in _placements(rest, length - len(head) - 1):
                yield head + (False,) + tail
        else:
            yield head + (False,) * (length - len(head))


def oracle_line(clue, cells):
    runs = [n for n in clue if n > 0]
    fits = [line for line in _placements(runs, len(cells))
            if all((c != FILLED or on) and (c != EMPTY or not on) for c, on in zip(cells, line, strict=True))]
    if not fits:
        return None
    return [FILLED if {line[i] for line in fits} == {True} else EMPTY if {line[i] for line in fits} == {False}
            else UNKNOWN for i in range(len(cells))]


def oracle_hint(cells, width, height, rows, columns):
    """The first undecided cell some line forces from the marks as they stand
    (row-major, ROW first), as (row, col, state, axis, index), or None."""
    known = lambda s: s if s in (FILLED, EMPTY) else UNKNOWN  # noqa: E731
    row_forced = [oracle_line(rows[r], [known(cells[r * width + c]) for c in range(width)]) for r in range(height)]
    col_forced = [oracle_line(columns[c], [known(cells[r * width + c]) for r in range(height)]) for c in range(width)]
    for r in range(height):
        for c in range(width):
            if cells[r * width + c] not in (UNKNOWN, MAYBE):
                continue
            if row_forced[r] is not None and row_forced[r][c] != UNKNOWN:
                return (r, c, row_forced[r][c], "row", r)
            if col_forced[c] is not None and col_forced[c][r] != UNKNOWN:
                return (r, c, col_forced[c][r], "column", c)
    return None


#: Extents of the hint corpus. The first five are small enough for the oracle's
#: enumeration; the last two are the supported range's extremes (beyond the oracle: held by
#: the clean-board comparison with the admin's deduced hint, and since CARD-399
#: no longer also by a comparison with play.js).
HINT_EXTENTS = [(6, 5), (8, 8), (10, 8), (11, 10), (12, 12), (20, 20), (30, 30)]
ORACLE_MAX_SIDE = 12


def hint_corpus(seed: int = 3851, count: int = 420) -> list[dict]:
    rng = random.Random(seed)
    cases = []
    for n in range(count):
        width, height = HINT_EXTENTS[n % len(HINT_EXTENTS)]
        grid = [[rng.random() < rng.choice((0.35, 0.55, 0.75)) for _ in range(width)] for _ in range(height)]
        rows, columns = clues_of(grid)
        marked = rng.choice((0.0, 0.15, 0.4, 0.7, 0.95))
        cells = [UNKNOWN] * (width * height)
        for i in range(width * height):
            if rng.random() < marked:
                cells[i] = FILLED if grid[i // width][i % width] else EMPTY
            elif rng.random() < 0.06:
                cells[i] = MAYBE
        if n % 3 == 2:  # a third carry wrong marks
            decided = [i for i, s in enumerate(cells) if s in (FILLED, EMPTY)]
            for i in rng.sample(decided, min(len(decided), rng.randrange(1, 9))):
                cells[i] = EMPTY if cells[i] == FILLED else FILLED
        cases.append({"w": width, "h": height, "grid": grid, "rows": rows, "cols": columns, "cells": cells})
    return cases + stalled_boards(rng, 70)


def stalled_boards(rng: random.Random, want: int) -> list[dict]:
    """Boards line logic has run out on: start blank and apply the ORACLE's own
    hint until it has none (so these are exhausted by the oracle's reckoning, not
    the module's), keeping the ones that still have an undecided cell. Every other
    one gets a '?' on an undecided cell, which is undecided too."""
    found: list[dict] = []
    while len(found) < want:
        width, height = rng.randint(6, 8), rng.randint(6, 8)
        grid = [[rng.random() < rng.choice((0.3, 0.4, 0.5)) for _ in range(width)] for _ in range(height)]
        rows, columns = clues_of(grid)
        cells = [UNKNOWN] * (width * height)
        while (hint := oracle_hint(cells, width, height, rows, columns)) is not None:
            cells[hint[0] * width + hint[1]] = hint[2]
        undecided = [i for i, s in enumerate(cells) if s == UNKNOWN]
        if not undecided:
            continue
        if len(found) % 2:
            cells[rng.choice(undecided)] = MAYBE
        found.append({"w": width, "h": height, "grid": grid, "rows": rows, "cols": columns, "cells": cells})
    return found


def has_wrong_mark(case) -> bool:
    return any(s in (FILLED, EMPTY) and s != (FILLED if case["grid"][i // case["w"]][i % case["w"]] else EMPTY)
               for i, s in enumerate(case["cells"]))


_HINT_JS = """async (cases) => {
  document.body.insertAdjacentHTML('beforeend', '<div data-player-stage></div>');
  const S = await import('/solver_state.js');
  return cases.map((c) => {
    const board = { width: c.w, height: c.h, cells: c.cells };
    const pub = S.hintCell(board, c.rows, c.cols, null);
    const line = pub === null ? null : S.hintLine(board, c.rows, c.cols, null, pub);
    const admin = S.hintCell(board, c.rows, c.cols, c.grid);
    const adminLine = admin === null ? null : S.hintLine(board, c.rows, c.cols, c.grid, admin);
    return {
      pub: pub && [pub.row, pub.col, pub.state, pub.deduced], line: line && [line.axis, line.index],
      admin: admin && [admin.row, admin.col, admin.state, admin.deduced],
      adminLine: adminLine && [adminLine.axis, adminLine.index],
    };
  });
}"""


def pure_site(serve, tmp_path_factory_edits=()):
    """A tree for the pure checks: the real modules and nothing else (CARD-399:
    play.js is no longer copied in, the module is checked against the oracle)."""
    return serve(public_payload(SWEEP_GRID), edits=list(tmp_path_factory_edits))


def hint_problems(page, served: Served, cases) -> list[str]:
    page.goto(served.url + "/")
    got = page.evaluate(_HINT_JS, cases)
    assert len(got) == len(cases)
    problems: list[str] = []
    for n, (case, g) in enumerate(zip(cases, got, strict=True)):
        small = case["w"] <= ORACLE_MAX_SIDE and case["h"] <= ORACLE_MAX_SIDE
        pub = g["pub"]
        cell_of = lambda h: None if h is None else tuple(h[:3])  # noqa: E731
        if pub is not None and pub[3] is not True:
            problems.append(f"case {n}: a public hint that is not deduced: {pub}")
        if small:
            want = oracle_hint(case["cells"], case["w"], case["h"], case["rows"], case["cols"])
            if cell_of(pub) != (None if want is None else want[:3]):
                problems.append(f"case {n}: hintCell(null) {pub} != brute force {want}")
            if want is not None and g["line"] is not None and tuple(g["line"]) != tuple(want[3:]):
                problems.append(f"case {n}: line {g['line']} != brute force {want[3:]}")
        if not has_wrong_mark(case):
            # the same board with an answer to check against: when the admin hint
            # is DEDUCED it is the public one; the admin's extra is only its fallback
            adm = g["admin"]
            deduced = adm if adm is not None and adm[3] else None
            if cell_of(pub) != cell_of(deduced):
                problems.append(f"case {n}: clean board, hintCell(null) {pub} != admin deduction {adm}")
            if pub is not None:
                r, c, state = pub[:3]
                if state != (FILLED if case["grid"][r][c] else EMPTY):
                    problems.append(f"case {n}: clean board, the derived state {state} is not the answer's")
        if len(problems) > 8:
            break
    return problems


def hint_census(cases) -> dict:
    wrong = [c for c in cases if has_wrong_mark(c)]
    return {"cases": len(cases), "wrong": len(wrong), "maybes": sum(MAYBE in c["cells"] for c in cases),
            "small": sum(c["w"] <= ORACLE_MAX_SIDE and c["h"] <= ORACLE_MAX_SIDE for c in cases),
            "extents": {(c["w"], c["h"]) for c in cases}}


@pytest.mark.browser
class TestPublicMode_TheHintIsDerivedFromTheCluesAndTheMarks:
    @pytest.fixture
    def cases(self):
        return hint_corpus()

    def test_the_corpus_is_big_and_has_every_kind_of_board(self, cases) -> None:
        census = hint_census(cases)
        assert census["cases"] >= 480 and census["wrong"] >= 100 and census["maybes"] >= 150
        assert census["small"] >= 340 and set(HINT_EXTENTS) <= census["extents"]
        oracle = [oracle_hint(c["cells"], c["w"], c["h"], c["rows"], c["cols"])
                  for c in cases if c["w"] <= ORACLE_MAX_SIDE and c["h"] <= ORACLE_MAX_SIDE]
        # neither "always null" nor "always a cell" passes
        assert sum(o is None for o in oracle) >= 40 and sum(o is not None for o in oracle) >= 150
        assert sum(o is not None and o[3] == "column" for o in oracle) >= 20

    def test_it_agrees_with_the_brute_force_oracle(self, browser_page, serve, cases) -> None:
        """AC-6 and G-6: hintCell/hintLine with a null solution equal the
        enumeration (cell, state AND the line that decides it) on every case
        within the oracle's reach, wrong marks included; and on a board with no wrong mark they equal the admin's
        deduced cell, so the answer-free hint is the admin hint minus its
        fallback and nothing else."""
        assert hint_problems(browser_page, pure_site(serve), cases) == []

    def test_a_wrong_mark_misleads_it_as_adr_0041_r2_declares(self, browser_page, serve, cases) -> None:
        """AC-6's declared half (inherent to ADR-0041/R2): on a board with a
        wrong mark the derived cell is sometimes not the answer's, and the
        public hint then differs from the admin's. Measured on this corpus, not
        assumed. (CARD-399: the third arm, "play.js gives the same cell", went
        with the comparator; the claim that a wrong mark misleads is unchanged.)"""
        browser_page.goto(pure_site(serve).url + "/")
        got = browser_page.evaluate(_HINT_JS, cases)
        misled = [(n, g["pub"]) for n, (c, g) in enumerate(zip(cases, got, strict=True))
                  if has_wrong_mark(c) and g["pub"] is not None
                  and g["pub"][2] != (FILLED if c["grid"][g["pub"][0]][g["pub"][1]] else EMPTY)]
        differs_from_admin = [n for n, (c, g) in enumerate(zip(cases, got, strict=True))
                              if has_wrong_mark(c) and (g["pub"] and g["pub"][:3]) != (
                                  g["admin"] and g["admin"][3] and g["admin"][:3] or None)]
        assert len(misled) >= 3, "the corpus must contain boards a wrong mark misleads"
        assert len(differs_from_admin) >= 3, "and boards where the public hint differs from the admin's"

    def test_there_is_never_a_hint_where_no_line_decides(self, browser_page, serve, cases) -> None:
        browser_page.goto(pure_site(serve).url + "/")
        got = browser_page.evaluate(_HINT_JS, cases)
        exhausted = [n for n, c in enumerate(cases) if c["w"] <= ORACLE_MAX_SIDE and c["h"] <= ORACLE_MAX_SIDE
                     and oracle_hint(c["cells"], c["w"], c["h"], c["rows"], c["cols"]) is None
                     and any(s in (UNKNOWN, MAYBE) for s in c["cells"])]
        assert len(exhausted) >= 30
        assert all(got[n]["pub"] is None for n in exhausted), "a hint was invented where no line decides a cell"
        # and the admin hint on the same boards is exactly the fallback this one lacks
        assert sum(1 for n in exhausted if got[n]["admin"] is not None and got[n]["admin"][3] is False) >= 20


# ---- solved, from the clues ---------------------------------------------------------


def unique_grids(count: int = 40, seed: int = 4207) -> list[list[list[bool]]]:
    rng = random.Random(seed)
    grids = []
    while len(grids) < count:
        width, height = rng.randint(4, 9), rng.randint(4, 9)
        grid = [[rng.random() < rng.choice((0.4, 0.55, 0.7)) for _ in range(width)] for _ in range(height)]
        if _unique(grid):
            grids.append(grid)
    return grids


def solved_corpus() -> list[dict]:
    rng = random.Random(9917)
    cases = []
    for grid in unique_grids():
        height, width = len(grid), len(grid[0])
        rows, columns = clues_of(grid)

        def board(extra=UNKNOWN, maybe=0.0):
            cells = []
            for r in range(height):
                for c in range(width):
                    if grid[r][c]:
                        cells.append(FILLED)
                    else:
                        cells.append(MAYBE if rng.random() < maybe else rng.choice((UNKNOWN, EMPTY)))
            return cells

        exact = board()
        flipped = list(exact)
        i = rng.randrange(width * height)
        flipped[i] = UNKNOWN if flipped[i] == FILLED else FILLED
        twice = list(flipped)
        j = rng.randrange(width * height)
        twice[j] = UNKNOWN if twice[j] == FILLED else FILLED
        maybe_over = list(exact)
        filled_at = [k for k, s in enumerate(exact) if s == FILLED]
        if filled_at:
            maybe_over[rng.choice(filled_at)] = MAYBE
        extra_fill = [FILLED] * (width * height)
        noise = [rng.choice((UNKNOWN, FILLED, EMPTY, MAYBE)) for _ in range(width * height)]
        for cells in (exact, board(maybe=0.3), flipped, twice, maybe_over, extra_fill, noise, [UNKNOWN] * (width * height)):
            cases.append({"w": width, "h": height, "grid": grid, "rows": rows, "cols": columns, "cells": cells})
    return cases


def solved_truth(case) -> bool:
    """Solved iff the filled cells are the solution (the puzzle is unique)."""
    w = case["w"]
    return all((s == FILLED) == case["grid"][i // w][i % w] for i, s in enumerate(case["cells"]))


def clue_truth(case) -> bool:
    """The same verdict by the clue definition: the board's filled runs, line by
    line, are the clues (written with itertools, not with runsOf)."""
    w, h = case["w"], case["h"]
    cell = lambda r, c: case["cells"][r * w + c] == FILLED  # noqa: E731
    return (all(_encode([cell(r, c) for c in range(w)]) == case["rows"][r] for r in range(h))
            and all(_encode([cell(r, c) for r in range(h)]) == case["cols"][c] for c in range(w)))


_SOLVED_JS = """async (cases) => {
  document.body.insertAdjacentHTML('beforeend', '<div data-player-stage></div>');
  const S = await import('/solver_state.js');
  return cases.map((c) => {
    const board = { width: c.w, height: c.h, cells: c.cells };
    return { mine: S.isClueSolved(board, c.rows, c.cols),
             admin: S.isSolved(board, c.grid) };
  });
}"""


def solved_problems(page, served: Served, cases) -> list[str]:
    page.goto(served.url + "/")
    got = page.evaluate(_SOLVED_JS, cases)
    problems = []
    for n, (case, g) in enumerate(zip(cases, got, strict=True)):
        truth = solved_truth(case)
        if clue_truth(case) != truth:
            problems.append(f"case {n}: the two oracles disagree (a non-unique puzzle slipped in)")
        if g["mine"] != truth:
            problems.append(f"case {n}: isClueSolved {g['mine']} != oracle {truth}")
        if g["admin"] != (truth and MAYBE not in case["cells"]):
            problems.append(f"case {n}: admin isSolved {g['admin']} drifted")
        if len(problems) > 8:
            break
    return problems


@pytest.mark.browser
class TestPublicMode_SolvedComesFromTheClues:
    @pytest.fixture
    def cases(self):
        return solved_corpus()

    def test_the_corpus_is_big_unique_and_two_sided(self, cases) -> None:
        assert len(cases) >= 300
        assert len({json.dumps(c["grid"]) for c in cases}) >= 40
        truths = [solved_truth(c) for c in cases]
        assert sum(truths) >= 60 and sum(not t for t in truths) >= 200
        assert sum(t and MAYBE in c["cells"] for t, c in zip(truths, cases)) >= 20, "solved boards holding a '?'"
        assert all(clue_truth(c) == t for c, t in zip(cases, truths))

    # AC-384: the model's verifying ref, tests/test_player_public_mode.py::test_it_agrees_with_the_oracle (CARD-399: moved here from play.js's twin).
    def test_it_agrees_with_the_oracle(self, browser_page, serve, cases) -> None:
        """AC-6 / G-6. Declared: it differs from the admin's isSolved only
        where a '?' sits on an otherwise solved board (a '?' is no run)."""
        assert solved_problems(browser_page, pure_site(serve), cases) == []

    def test_the_one_difference_from_the_admin_is_a_maybe_on_a_solved_board(self, browser_page, serve, cases) -> None:
        browser_page.goto(pure_site(serve).url + "/")
        got = browser_page.evaluate(_SOLVED_JS, cases)
        differ = [c for c, g in zip(cases, got, strict=True) if g["mine"] != g["admin"]]
        assert len(differ) >= 20, "the corpus must exercise the difference"
        assert all(MAYBE in c["cells"] and solved_truth(c) for c in differ)


# ==========================================================================
# The mutants: every way the property can be lost, built from the REAL files
# ==========================================================================


def sealed_problems(page, served: Served, timeout=3000) -> list[str]:
    """In public mode payload.solution is a getter that throws, hidden from
    enumeration and JSON: reading it is an error, never a tolerated null."""
    page.set_default_timeout(timeout)
    open_page(page, served)
    seen = page.evaluate(
        """() => { const p = window.puzzlePlayer.payload; let thrown = false;
                   try { p.solution; } catch (e) { thrown = true; }
                   return { thrown, listed: Object.keys(p).includes('solution'), json: JSON.stringify(p).includes('solution') }; }""")
    problems = []
    if not seen["thrown"]:
        problems.append("reading payload.solution did not throw in public mode")
    if seen["listed"] or seen["json"]:
        problems.append("the sealed solution is enumerable or serialised")
    return problems


def _hint_check(page, served, timeout=3000):
    return hint_problems(page, served, hint_corpus())


def _solved_check(page, served, timeout=3000):
    return solved_problems(page, served, solved_corpus())


#: name -> (payload factory, the check, files the tree also needs)
CHECKS = {
    "sweep": (lambda: public_payload(SWEEP_GRID), sweep_problems, []),
    "stall": (lambda: public_payload(STALL_GRID, puzzle_id="stall"), stall_problems, []),
    "refusal": (lambda: public_payload(SWEEP_GRID, solution=SWEEP_GRID), refusal_problems, []),
    "save": (lambda: public_payload(SWEEP_GRID), save_problems, []),
    "admin": (lambda: admin_payload(STALL_GRID, puzzle_id=SWEEP_ID), admin_mode_problems, []),
    "sealed": (lambda: public_payload(SWEEP_GRID), sealed_problems, []),
    "hint": (lambda: public_payload(SWEEP_GRID), _hint_check, []),
    "solved": (lambda: public_payload(SWEEP_GRID), _solved_check, []),
}

_HINTLINE_READ = "      history.board, payload.rows, payload.columns, publicMode ? null : payload.solution, hint),"
_NEXTHINT_READ = "      : hintCell(history.board, payload.rows, payload.columns, publicMode ? null : payload.solution)),"
_NOW = """    const now = publicMode
      ? isClueSolved(history.board, payload.rows, payload.columns)
      : isSolved(history.board, payload.solution);"""
_SOLVES = """    solves: (candidate) => !editing && (publicMode
      ? isClueSolved(candidate, payload.rows, payload.columns)
      : isSolved(candidate, payload.solution)),"""
_FALLBACK = "      if (fallback === null && solution !== null) {\n        fallback = { row, col, state: truth(row, col), deduced: false };\n      }"
_COUNT = ('candidate.cells.filter((c) => c === "filled").length'
          ' === payload.rows.flat().reduce((a, b) => a + b, 0)')
_STAMP = "  return payload.mode === PUBLIC_MODE ? PUBLIC_GRID : gridFingerprint(payload.solution);"

#: (id, check that must red, [(file, old, new)]). Each edit's ``old`` is
#: asserted to occur exactly once in the copy, so a stale mutant is an error,
#: never a silent pass.
MUTANTS = [
    ("hintLine-reads-the-solution-ungated", "sweep", [("solver.js", _HINTLINE_READ, _HINTLINE_READ.replace("publicMode ? null : ", ""))]),
    ("nextHint-reads-the-solution-ungated", "sweep", [("solver.js", _NEXTHINT_READ, _NEXTHINT_READ.replace("publicMode ? null : ", ""))]),
    ("solved-reads-the-solution-ungated", "sweep", [("solver.js", _NOW, "    const now = isSolved(history.board, payload.solution);")]),
    ("probe-auto-commit-reads-the-solution-ungated", "sweep", [("solver.js", _SOLVES, "    solves: (candidate) => !editing && isSolved(candidate, payload.solution),")]),
    ("errors-counted-from-the-solution-in-public", "sweep", [("solver.js", "    if (!publicMode) {\n      const errors", "    if (true) {\n      const errors")]),
    ("progress-counted-from-the-solution-in-public", "sweep", [("solver.js", "    if (!publicMode) {\n      const percent", "    if (true) {\n      const percent")]),
    ("check-left-on-the-page", "sweep", [("solver.js", ", [data-player-action=\"check\"]';", "';")]),
    ("the-solution-is-not-sealed", "sealed", [("solver.js", "  if (publicMode) sealSolution(payload);\n", "")]),
    ("hint-falls-back-to-revealing-a-cell-stall", "stall", [("solver_state.js", _FALLBACK, "      if (fallback === null) {\n        fallback = { row, col, state: solution === null ? FILLED : truth(row, col), deduced: false };\n      }")]),
    ("hint-falls-back-to-revealing-a-cell-oracle", "hint", [("solver_state.js", _FALLBACK, "      if (fallback === null) {\n        fallback = { row, col, state: solution === null ? FILLED : truth(row, col), deduced: false };\n      }")]),
    ("a-public-payload-with-a-solution-is-accepted", "refusal", [("solver.js", "  if (payload && payload.mode === PUBLIC_MODE && Object.hasOwn(payload, \"solution\")) {", "  if (false) {")]),
    ("the-save-is-fingerprinted-from-a-solution", "save", [("solver_state.js", _STAMP, "  return payload.mode === PUBLIC_MODE ? gridFingerprint([[true]]) : gridFingerprint(payload.solution);")]),
    ("the-save-reads-the-solution-in-public", "sweep", [("solver_state.js", _STAMP, "  return gridFingerprint(payload.solution);")]),
    ("a-network-call-is-added", "sweep", [("solver.js", "const MAJOR_EVERY = 5;", "const MAJOR_EVERY = 5;\nfetch(\"/ping\", { method: \"POST\", body: \"x\" });")]),
    ("clue-solved-ignores-the-columns", "solved", [("solver_state.js", "  for (let col = 0; col < width; col += 1) {\n    const line = Array.from({ length: height }, (_, row) => cells[row * width + col]);\n    if (!sameRuns(runsOf(line), columns[col])) return false;\n  }\n  return true;", "  return true;")]),
    ("public-marks-ignore-the-empty-marks", "hint", [("solver_state.js", "if (solution === null) return state === FILLED || state === EMPTY ? state : UNKNOWN;", "if (solution === null) return state === FILLED ? state : UNKNOWN;")]),
    ("admin-solved-is-read-from-the-clues", "admin", [("solver.js", _NOW, "    const now = isClueSolved(history.board, payload.rows, payload.columns);")]),
    ("admin-loses-its-counters-and-check", "admin", [("solver.js", "  if (publicMode) {\n    for (const element of toolbar", "  if (true) {\n    for (const element of toolbar")]),
    ("admin-save-is-stamped-public", "admin", [("solver_state.js", _STAMP, "  return PUBLIC_GRID;")]),
    ("banner-decided-by-filled-count", "sweep", [("solver.js", _NOW, _NOW.replace("isClueSolved(history.board, payload.rows, payload.columns)", _COUNT.replace("candidate", "history.board")))]),
    ("probe-auto-commit-decided-by-filled-count", "sweep", [("solver.js", _SOLVES, _SOLVES.replace("isClueSolved(candidate, payload.rows, payload.columns)", _COUNT))]),
    ("hint-disabled-again-where-no-line-decides", "stall", [("solver.js", "(player.nextHint() === null && !player.speaks())", "player.nextHint() === null")]),
    ("hint-reveals-a-cell-where-no-line-decides", "stall", [("solver.js", "      say(PUBLIC_EXHAUSTED);\n      return;", "      commit(record(player.getHistory(), hintStroke(0, 0, \"filled\")), null);\n      return;")]),
    ("hint-is-silent-where-no-line-decides", "stall", [("solver.js", "      say(PUBLIC_EXHAUSTED);\n      return;", "      return;")]),
    ("hint-counts-where-no-line-decides", "stall", [("solver.js", "      say(PUBLIC_EXHAUSTED);\n      return;", "      say(PUBLIC_EXHAUSTED);\n      commit(record(player.getHistory(), hintStroke(0, 0, \"filled\")), null);\n      return;")]),
    ("admin-resumes-a-public-stamp", "admin", [("solver_state.js", "      || data.grid !== stampOf(payload)", "      || (data.grid !== stampOf(payload) && data.grid !== PUBLIC_GRID)")]),
    ("admin-hint-loses-its-fallback", "admin", [("solver_state.js", _FALLBACK, _FALLBACK.replace("solution !== null", "false"))]),
]


@pytest.fixture
def touch_pages(browser_page):
    """A factory of pages in touch-capable contexts, closed at teardown."""
    contexts = []

    def make():
        context = browser_page.context.browser.new_context(has_touch=True, viewport={"width": 1280, "height": 900})
        contexts.append(context)
        return context.new_page()

    yield make
    for context in contexts:
        context.close()


@pytest.mark.browser
class TestPublicMode_EveryWayOfLosingItIsCaught:
    @pytest.mark.parametrize("mutant", MUTANTS, ids=[m[0] for m in MUTANTS])
    def test_the_check_is_green_on_the_real_files_and_red_on_the_mutant(self, mutant, touch_pages, serve) -> None:
        name, check_name, edits = mutant
        payload, check, extra = CHECKS[check_name]
        clean = check(touch_pages(), serve(payload(), extra_files=extra))
        assert clean == [], f"the control ({check_name}) is not green on the real files: {clean}"
        broken = check(touch_pages(), serve(payload(), edits=edits, extra_files=extra))
        assert broken != [], f"{name}: the {check_name} check did not see the mutant"

    def test_there_is_a_mutant_for_every_way_the_card_names(self) -> None:
        ids = {m[0] for m in MUTANTS}
        assert len(ids) == len(MUTANTS) >= 20
        for family in ("ungated", "fallback", "accepted", "fingerprinted", "network", "admin", "sealed"):
            assert any(family in i for i in ids), family
        assert {m[1] for m in MUTANTS} == set(CHECKS), "every check has a mutant that reds it"

    @pytest.mark.parametrize("who", ["solver.js", "solver_state.js"])
    def test_a_network_plant_reds_the_scan_beside_a_clean_control(self, who) -> None:
        text = (_STATIC / who).read_text()
        assert network_calls(text) == []
        assert network_calls(text + '\nfetch("/ping", { method: "POST" });\n') == ["fetch"]


#: CARD-402: the strip's buttons that must be on screen, not the brush menu's
#: items or the reset dialog's (popovers), and not a hidden probe button;
#: "lowest" against the strip's own clip as well as the window.
_STRIP = """() => {
  const strip = document.getElementById('puzzle-player-controls');
  const shown = (b) => b.getClientRects().length && getComputedStyle(b).visibility !== 'hidden'
    && !b.closest('[role=menu]') && !b.closest('.player-confirm');
  const boxes = [...strip.querySelectorAll('button, [data-player-zoom-readout]')].filter(shown).map((b) => b.getBoundingClientRect());
  const s = strip.getBoundingClientRect(), board = document.querySelector('.player-board').getBoundingClientRect();
  return { left: s.left, right: s.right, width: s.width, clip: Math.min(s.bottom, innerHeight),
           overflowY: getComputedStyle(strip).overflowY,
           board: [board.left, board.top, board.width, board.height].map((v) => Math.round(v * 10) / 10),
           lowest: Math.max(...boxes.map((b) => b.bottom)), shortest: Math.min(...boxes.map((b) => b.height)),
           count: boxes.length, page: document.documentElement.scrollHeight - innerHeight };
}"""

#: Every brush in the open menu answers a tap where it is drawn — at its
#: centre AND near its right edge, which is what a clipping strip hides.
_MENU_TAPPABLE = """() => [...document.querySelectorAll('[data-player-tool]')].every((item) => {
  const b = item.getBoundingClientRect(), y = b.top + b.height / 2;
  return b.width > 0 && [b.left + b.width / 2, b.right - 4].every((x) =>
    document.elementFromPoint(x, y)?.closest('[data-player-tool]') === item); })"""


def _settled(page, read=_STRIP, tries=30):
    """Read ``read`` once two reads 100 ms apart agree (bounded)."""
    before = page.evaluate(read)
    for _ in range(tries):
        page.wait_for_timeout(100)
        now = page.evaluate(read)
        if now == before:
            return now
        before = now
    raise AssertionError(f"never settled: {before}")


class TestPublicMode_LandscapeToolStrip:
    """CARD-402 (owner finding 2026-11-07, item 5: "Toolbar as a vertical icon
    column at the side ... the board then gets nearly the full height"; owner
    ruling 2026-11-10, "B": two buttons wide). Measured on the public page —
    the phone's page; the admin page keeps its desktop sidebar and topbar at
    844 px and its strip scrolls there (Worktree notes). One cell:

    * AC-1: at 844 x 390, 852 x 393 and 874 x 402 the strip is LEFT of the
      board, at most two 44 px buttons and a gap wide, all ten controls
      inside the window and the strip's clip, each 44 px tall or more, and
      the brush menu's items tappable where they are drawn (not clipped);
    * AC-3: the board's box (place AND size) is the same idle, with a probe
      open, at hint rung 2, with the reset dialog open and solved;
    * AC-5: at 568 x 320 the strip scrolls ITSELF and its last button can be
      scrolled into the window;
    * review cycle 1, F-001: a 30 x 29 at Fit at 932 x 430 holds still (it
      re-fitted every frame when the strip's height fed the toolbar observer).
    Portrait and desktop (AC-4) are the existing layout cells, unchanged.
    """

    def test_the_tools_stand_in_a_strip_left_of_the_board(self, browser_page, serve, live) -> None:
        page = browser_page
        served = serve(public_payload(SWEEP_GRID))
        for width, height in ((844, 390), (852, 393), (874, 402)):
            page.set_viewport_size({"width": width, "height": height})
            open_page(page, served)
            idle = _settled(page)
            assert idle["right"] <= idle["board"][0] and idle["width"] <= 2 * 44 + 8 + 1, (width, idle)
            assert idle["lowest"] <= idle["clip"] and idle["page"] <= 0, (width, idle)
            assert idle["shortest"] >= 44 and idle["count"] == 10, (width, idle)
            page.locator(".player-tool-trigger").click()
            assert page.evaluate(_MENU_TAPPABLE), width
            page.keyboard.press("Escape")
            page.locator("[data-player-probe]").click()
            probing = _settled(page)
            assert probing["lowest"] <= probing["clip"], (width, probing)
            page.locator('[data-player-probe-action="keep"]').click()
            action(page, "hint").click()
            action(page, "hint").click()
            rung2 = _settled(page)
            page.keyboard.press("Escape")
            cell(page, 0, 0).click()
            action(page, "reset").click()
            confirming = _settled(page)
            assert page.locator("#puzzle-player-confirm").is_visible()
            page.locator('[data-player-confirm="cancel"]').click()
            assert idle["board"] == probing["board"] == rung2["board"] == confirming["board"], (width, idle, probing, rung2, confirming)
        solve_to_the_end(page, SWEEP_GRID)
        solved = _settled(page)
        assert page.locator("#puzzle-player-solved").is_visible() and solved["board"] == idle["board"], (solved, idle)

        page.set_viewport_size({"width": 568, "height": 320})
        open_page(page, served)
        small = _settled(page)
        assert small["overflowY"] == "auto" and small["page"] <= 0, small
        page.evaluate("() => { const s = document.getElementById('puzzle-player-controls'); s.scrollTop = s.scrollHeight; }")
        scrolled = page.evaluate(_STRIP)
        assert scrolled["lowest"] <= scrolled["clip"], scrolled
        # Review cycle 2, F-010: a board solved with the strip scrolled down
        # brings the banner (the strip's top) back into the strip's view.
        open_page(page, serve(public_payload(SWEEP_GRID, puzzle_id="strip-568")))
        _settled(page)
        page.evaluate("() => { const s = document.getElementById('puzzle-player-controls'); s.scrollTop = s.scrollHeight; }")
        solve_to_the_end(page, SWEEP_GRID)
        banner = page.evaluate("""() => { const s = document.getElementById('puzzle-player-controls').getBoundingClientRect();
          const b = document.getElementById("puzzle-player-solved").getBoundingClientRect(); return [b.top >= s.top - 1.5, b.bottom <= s.bottom + 1.5, b.height > 0]; }""")  # its 1 px border
        assert banner == [True, True, True], banner

        # Review cycle 2, F-009: the ADMIN page in a small landscape window
        # (its strip starts low, under the title) keeps every brush tappable
        # (667 x 375 until cycle 3; 740 x 360 overflows as well).
        # Review cycle 3, F-011: and on the SECOND open too (a lifted open
        # once left an inline margin that misplaced the next one) — at 740 x
        # 360, where that second open ran off the window.
        page.set_viewport_size({"width": 740, "height": 360})
        admin_open(page, live, live.store(SWEEP_GRID))
        for _ in range(2):
            page.locator(".player-tool-trigger").click()
            assert page.evaluate(_MENU_TAPPABLE)
            page.keyboard.press("Escape")

        page.set_viewport_size({"width": 932, "height": 430})
        open_page(page, serve(public_payload(_unique_grid(30, 29, seed=19330))))
        sizes = page.evaluate("""() => new Promise((done) => { const out = []; const tick = () => {
          out.push(document.querySelector('.player-board').getBoundingClientRect().width);
          if (out.length < 20) requestAnimationFrame(tick); else done(out); };
          setTimeout(() => requestAnimationFrame(tick), 500); })""")
        assert len(set(sizes)) == 1, sizes  # F-001: no re-fit loop
