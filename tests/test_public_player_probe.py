"""CARD-380 - probe mode (the hypothesis transaction) on the PUBLIC player.

The admin player has had probe mode since CARD-268: a group of marks made under
one hypothesis, later KEPT as a group or ABANDONED as a group. The transaction
is ``solver_state.js``'s (``nextProbe``, ``probeCells``, ``abandonProbe``,
``checkpointHistory``), takes a history and a probe and NO solution, and is a
byte-identical build-time copy on this site (ADR-0041/R3). ``play.js`` is the
wiring: it says which event happened and paints what the module returns.

Test names follow the card (AC-1 .. AC-13); AC-13 is in
``tests/test_public_player_agreement.py`` (``TestPlayerLooksAgree_TheProbeIsTheSameLook``).
The sections, in file order:

* the scenarios, one per rule the card declares, each a function that drives
  the SERVED page in headless Chromium and returns its problems (``[]`` = green);
  the ACs' tests assert the scenarios green AND the specific facts the AC names;
* the plants: edge mutants of ``play.js``, each served through a Playwright ROUTE
  with a served CANARY (``window.__served``), each run beside its matched control
  in the same test, each pinned to the EXACT set of scenarios that fire;
* AC-9 (the module's transitions and four states, tokens only), AC-10 (the
  controls are outside the toolbar, 44 px, reachable at the zoom maximum and a
  scrolled offset, and the zoom module's premise holds with them), AC-11 (the
  marks coexist, by pixels), AC-12 (no answer, no request).

How the expected values are made. A test of the transaction must not derive its
expectation from the thing under test, so the expectations here are one of
three kinds: a SNAPSHOT of the page before the probe (abandon must restore it
cell for cell), the SERVED module's own function asked over the board the page
holds (``circledClues``), or a count the scenario constructs (a probe of N
strokes holds exactly the cells those N strokes touched). The module's
``probeCells`` is never asked to judge ``paintProbe``: membership is checked
against the strokes the scenario made.
"""

from __future__ import annotations

import itertools
import json
import math
import re
from pathlib import Path

import pytest

from tests.test_public_player import (  # noqa: F401 - fixtures used by name
    GRIDS,
    PLAYER_DIR,
    _cell_centre,
    _open,
    _tap,
    browser_type,
    host,
    site,
    write_bundle,
)
from tests.test_public_player_circles import (  # noqa: F401
    CIRCLES_GRID,
    _board,
    _dom,
    _marked,
    _mismatch,
    _pixels,
    _total,
    _want,
)
from tests.test_public_player_crosshair import _centre_in_stage, _move, _scan, browser_page  # noqa: F401
from tests.test_public_player_hint import (  # noqa: F401
    FIXTURES,
    HINT,
    PUZZLE_FIELDS,
    TOOLBAR_BUTTONS,
    _TOOLBAR_FACTS,
    _nearly_solved,
    bundle,
    expected,
    plant_page,
    press,
    serve_planted,
    served_puzzles,
    walk_globals,
)
import tests.test_public_player_zoom as zoom_module
from tests.test_public_player_zoom import (  # noqa: F401
    NARROWEST,
    PHONE,
    SHORTEST,
    TALLEST,
    WIDEST,
    _GEOMETRY,
    _bounds,
    _open_max,
    _percent,
    _press,
    _settle,
)

PLAY_JS = PLAYER_DIR / "play.js"
PLAY_HTML = PLAYER_DIR / "play.html"
PLAYER_CSS = PLAYER_DIR / "player.css"
ADMIN_STATIC = Path(__file__).resolve().parent.parent / "src" / "nonogram" / "admin" / "static"

PROBE = "[data-player-probe]"
KEEP = '[data-player-probe-action="keep"]'
ABANDON = '[data-player-probe-action="abandon"]'
UNDO = '[data-player-action="undo"]'
REDO = '[data-player-action="redo"]'
RESET = '[data-player-action="reset"]'


def brush(name: str) -> str:
    return f'[data-player-tool="{name}"]'


# --------------------------------------------------------------------------
# Reading the page
# --------------------------------------------------------------------------

_STATE = """() => {
  const p = window.publicPlayer;
  const h = p.getHistory();
  const probe = document.querySelector('[data-player-probe]');
  const keep = document.querySelector('[data-player-probe-action="keep"]');
  const abandon = document.querySelector('[data-player-probe-action="abandon"]');
  const note = document.querySelector('[data-player-probe-note]');
  const usage = document.querySelector('[data-player-hint]');
  const width = p.payload.width;
  return {
    cells: [...h.board.cells],
    dom: [...document.querySelectorAll('td.player-cell')].map((c) => c.dataset.state),
    marked: [...document.querySelectorAll('td.player-cell[data-probe]')]
      .map((c) => Number(c.dataset.row) * width + Number(c.dataset.col)).sort((a, b) => a - b),
    markedValues: [...new Set([...document.querySelectorAll('[data-probe]')].map((c) => c.getAttribute('data-probe')))],
    markedElsewhere: document.querySelectorAll('[data-probe]:not(td.player-cell)').length,
    open: probe.getAttribute('aria-pressed'),
    disabled: probe.getAttribute('aria-disabled'),
    keepHidden: keep.hidden, abandonHidden: abandon.hidden, noteHidden: note.hidden, usageHidden: usage.hidden,
    noteShown: note.getBoundingClientRect().height > 0,
    done: h.done.length, undone: h.undone.length,
    hints: Number(document.querySelector('[data-player-hints]').textContent),
    save: localStorage.getItem(p.saveKey),
    keys: Object.keys(localStorage).sort(),
    solved: !document.querySelector('[data-player-solved]').hidden,
    bodySolved: document.body.dataset.solved,
    hinted: [...document.querySelectorAll('td.is-hinted')].map((c) => Number(c.dataset.row) * width + Number(c.dataset.col)),
  };
}"""


def st(page) -> dict:
    return page.evaluate(_STATE)


def at(row: int, col: int, width: int = 10) -> int:
    return row * width + col


def mark(page, tool: str, row: int, col: int) -> None:
    page.click(brush(tool), force=True)
    _tap(page, row, col)


def save_strokes(state: dict) -> dict:
    return json.loads(state["save"])


def fresh(page, host, name: str = "mixed", strokes=()) -> None:
    """The page on ``name`` with a save holding ``strokes`` (an empty list is a blank board)."""
    _board(page, host, host[2][name], FIXTURES[name], list(strokes))


def reload(page) -> None:
    page.reload()
    page.wait_for_function("window.publicPlayer !== undefined")


def closed_problems(s: dict, label: str) -> list[str]:
    """What a page with NO probe open looks like: the control offers Probe only, and nothing is marked."""
    found = []
    if s["open"] != "false" or not s["keepHidden"] or not s["abandonHidden"] or not s["noteHidden"]:
        found.append(f"{label}: a probe looks open ({s['open']}, keep hidden {s['keepHidden']}, abandon hidden {s['abandonHidden']}, note hidden {s['noteHidden']})")
    if s["marked"]:
        found.append(f"{label}: cells still carry the probe marker: {s['marked']}")
    if s["usageHidden"]:
        found.append(f"{label}: the usage paragraph is hidden with no probe and no sentence")
    return found


def open_problems(s: dict, label: str) -> list[str]:
    found = []
    if s["open"] != "true" or s["disabled"] != "true" or s["keepHidden"] or s["abandonHidden"] or s["noteHidden"]:
        found.append(f"{label}: no probe looks open ({s['open']}, disabled {s['disabled']}, keep hidden {s['keepHidden']}, abandon hidden {s['abandonHidden']}, note hidden {s['noteHidden']})")
    if not s["usageHidden"]:
        found.append(f"{label}: the usage paragraph still shows beside the probe's note")
    if not s["noteShown"]:
        found.append(f"{label}: the note has no box")
    return found


def _move_away(page) -> None:
    """The pointer off the board (the crosshair tints the cell under it) and every animation finished."""
    page.mouse.move(2, 2)
    page.wait_for_function("document.getAnimations().every((a) => a.playState !== 'running')")


def check(problems: list[str], condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


# --------------------------------------------------------------------------
# The scenarios: one per rule the card declares. Each returns its problems.
# --------------------------------------------------------------------------


def sc_marks(page, host) -> list[str]:
    """Rules 2 and 3 (AC-1): marks made while a probe is open carry the marker, with every state, hint strokes included."""
    p: list[str] = []
    fresh(page, host)
    mark(page, "filled", 0, 0)  # made BEFORE the probe
    page.click(PROBE, force=True)
    p.extend(open_problems(st(page), "just opened"))
    check(p, st(page)["marked"] == [], "opening a probe marked a cell")
    mark(page, "filled", 1, 1)
    mark(page, "empty", 2, 2)
    mark(page, "maybe", 3, 3)
    mark(page, "filled", 4, 4)
    for _ in range(2):  # the same brush again on the same cell goes on: white, then blank. A cell put back is still a mark made
        _tap(page, 4, 4)
    p.extend(open_problems(st(page), "with marks, before any hint"))
    want_hint = expected(page)
    check(p, want_hint is not None, "the fixture has no hint to reveal")
    for _ in range(3):
        press(page)
    s = st(page)
    members = {at(1, 1), at(2, 2), at(3, 3), at(4, 4)}
    if want_hint is not None:
        members.add(at(want_hint["row"], want_hint["col"]))
    check(p, s["marked"] == sorted(members), f"the marker is on {s['marked']}, not on exactly the {sorted(members)} the probe's strokes touched")
    check(p, at(0, 0) not in s["marked"], "a cell marked BEFORE the probe carries the marker")
    check(p, s["markedValues"] == ["true"] and s["markedElsewhere"] == 0, f"the marker is {s['markedValues']} on {s['markedElsewhere']} non-cells")
    check(p, s["cells"] == s["dom"], "a cell's data-state is not the recorded board's (the marker is a fifth state)")
    check(p, {s["dom"][i] for i in (at(1, 1), at(2, 2), at(3, 3))} == {"filled", "empty", "maybe"}, f"the marked states are {s['dom']}")
    check(p, s["dom"][at(4, 4)] == "unknown" and s["dom"][at(0, 0)] == "filled", "a state under the marker is not its own")
    if want_hint is not None and (want_hint["row"], want_hint["col"]) not in {(1, 1), (2, 2), (3, 3), (4, 4), (0, 0)}:
        check(p, s["dom"][at(want_hint["row"], want_hint["col"])] == want_hint["state"], "the hint cell does not show the derived state")
    check(p, s["hints"] == 1, f"the hint counter reads {s['hints']}")
    # a hint sentence takes the slot beside the bars: the note yields to it, and the usage paragraph stays out
    check(p, s["open"] == "true" and s["usageHidden"] and s["noteHidden"], "the slot has two occupants while a hint sentence shows with a probe open")
    mark(page, "filled", 6, 6)  # the next recorded change clears the sentence and the note comes back
    p.extend(open_problems(st(page), "after the sentence is cleared"))
    # the matched control, same page: the same strokes with NO probe leave no marker
    fresh(page, host)
    mark(page, "filled", 0, 0)
    mark(page, "filled", 1, 1)
    mark(page, "empty", 2, 2)
    s = st(page)
    check(p, s["marked"] == [] and s["open"] == "false", f"marks with no probe carry the marker: {s['marked']}")
    p.extend(closed_problems(s, "with no probe"))
    return p


def sc_abandon(page, host) -> list[str]:
    """Rule 4 (AC-2): one press undoes back to the checkpoint, the board is as at the start, and redo follows the history rules."""
    p: list[str] = []
    fresh(page, host)
    mark(page, "filled", 0, 0)
    mark(page, "empty", 0, 1)
    before = st(page)
    page.click(PROBE, force=True)
    mark(page, "filled", 1, 1)
    mark(page, "maybe", 3, 3)
    mark(page, "empty", 0, 0)  # a PRE-probe cell touched inside the probe
    inside = st(page)
    check(p, inside["done"] == before["done"] + 3, "the scenario did not make three probe strokes")
    page.click(ABANDON, force=True)
    after = st(page)
    check(p, after["cells"] == before["cells"], f"the board is not the checkpoint board: {[i for i, (a, b) in enumerate(zip(after['cells'], before['cells'])) if a != b]}")
    check(p, after["dom"] == before["dom"], "the DOM is not the checkpoint board")
    p.extend(closed_problems(after, "after abandon"))
    check(p, after["done"] == before["done"] and after["undone"] == 3, f"the history is {after['done']}/{after['undone']}, not {before['done']}/3")
    saved = save_strokes(after)
    check(p, len(saved["done"]) == before["done"] and len(saved["undone"]) == 3, "the save does not follow the abandon (a run of undos)")
    page.click(REDO, force=True)  # redo after an abandon: the ordinary rules
    redone = st(page)
    check(p, redone["done"] == before["done"] + 1 and redone["cells"][at(1, 1)] == "filled", "redo after an abandon does not bring back the first probe stroke")
    p.extend(closed_problems(redone, "after redo"))
    return p


def sc_commit(page, host) -> list[str]:
    """Rule 5 (AC-3): Keep drops the look, touches no cell, closes the probe, and the whole history is savable."""
    p: list[str] = []
    fresh(page, host)
    mark(page, "filled", 0, 0)
    page.click(PROBE, force=True)
    mark(page, "filled", 1, 1)
    mark(page, "empty", 2, 2)
    mark(page, "maybe", 3, 3)
    before = st(page)
    check(p, before["marked"] == sorted([at(1, 1), at(2, 2), at(3, 3)]), "the probe does not hold its three cells before Keep")
    check(p, len(save_strokes(before)["done"]) == 1, "the save holds probe strokes before Keep")
    page.click(KEEP, force=True)
    after = st(page)
    check(p, after["cells"] == before["cells"] and after["dom"] == before["dom"], "Keep changed a cell")
    p.extend(closed_problems(after, "after keep"))
    check(p, (after["done"], after["undone"]) == (before["done"], before["undone"]), "Keep recorded or dropped a stroke")
    check(p, len(save_strokes(after)["done"]) == 4, "the kept strokes are not in the save")
    page.click(UNDO, force=True)  # an ordinary history again: one undo pops the last kept stroke
    undone = st(page)
    check(p, undone["cells"][at(3, 3)] == "unknown" and undone["cells"][at(2, 2)] == "empty" and undone["marked"] == [], "undo after Keep is not the ordinary undo")
    reload(page)
    reloaded = st(page)
    check(p, reloaded["cells"][at(1, 1)] == "filled" and reloaded["cells"][at(2, 2)] == "empty" and reloaded["marked"] == [], "a kept probe does not survive a reload")
    return p


def sc_undo(page, host) -> list[str]:
    """Rule 6 (AC-4): undo pops probe strokes first, past the checkpoint it clamps and the probe stays open and empty,
    and a stroke made BEFORE the probe does not come back inside it after a redo (CARD-268's review finding)."""
    p: list[str] = []
    fresh(page, host)
    mark(page, "filled", 0, 0)  # A, before the probe
    page.click(PROBE, force=True)
    mark(page, "filled", 1, 1)
    mark(page, "filled", 2, 2)
    mark(page, "filled", 3, 3)
    page.click(UNDO, force=True)
    s = st(page)
    check(p, s["marked"] == sorted([at(1, 1), at(2, 2)]), f"undo did not take the popped stroke's marker with it: {s['marked']}")
    page.click(UNDO, force=True)
    page.click(UNDO, force=True)
    s = st(page)
    check(p, s["marked"] == [] and s["open"] == "true", f"a probe that shrank to empty did not stay open: marked {s['marked']}, open {s['open']}")
    page.click(UNDO, force=True)  # past the checkpoint: A itself
    s = st(page)
    check(p, s["done"] == 0 and s["cells"][at(0, 0)] == "unknown", "the scenario did not undo past the checkpoint")
    check(p, s["open"] == "true" and s["marked"] == [], f"undoing past the checkpoint closed or filled the probe: {s['open']} {s['marked']}")
    mark(page, "filled", 5, 5)
    s = st(page)
    check(p, s["marked"] == [at(5, 5)] and s["open"] == "true", f"the next mark did not belong to the clamped probe: {s['marked']}")
    page.click(ABANDON, force=True)
    s = st(page)
    check(p, all(c == "unknown" for c in s["cells"]), "abandon after a clamp did not return to the clamped checkpoint")
    p.extend(closed_problems(s, "after the clamped abandon"))
    # the F-002 case: A, B made; B undone; probe opened; B redone INSIDE it must not be the probe's
    fresh(page, host)
    mark(page, "filled", 0, 0)
    mark(page, "filled", 1, 1)
    page.click(UNDO, force=True)
    page.click(PROBE, force=True)
    page.click(REDO, force=True)
    s = st(page)
    check(p, s["cells"][at(1, 1)] == "filled", "the scenario did not redo B")
    check(p, s["marked"] == [], f"a stroke made BEFORE the probe came back inside it: {s['marked']}")
    mark(page, "filled", 2, 2)
    check(p, st(page)["marked"] == [at(2, 2)], "the stroke made after the redo is not alone in the probe")
    page.click(ABANDON, force=True)
    s = st(page)
    check(p, s["cells"][at(0, 0)] == "filled" and s["cells"][at(1, 1)] == "filled" and s["cells"][at(2, 2)] == "unknown",
          "Contradiction took away a stroke the player made before the probe")
    return p


def sc_depth(page, host) -> list[str]:
    """Rule 1 (AC-5): depth 1. The chosen behaviour: Probe is aria-disabled while a probe is open and pressing it is a no-op."""
    p: list[str] = []
    fresh(page, host)
    check(p, st(page)["disabled"] == "false", "Probe is disabled with nothing open")
    page.click(PROBE, force=True)
    mark(page, "filled", 1, 1)
    page.click(PROBE, force=True)  # a second press, force: aria-disabled does not stop a click, the page must
    s = st(page)
    check(p, s["disabled"] == "true" and s["open"] == "true", "the open probe's control is not disabled and pressed")
    mark(page, "filled", 2, 2)
    check(p, st(page)["marked"] == sorted([at(1, 1), at(2, 2)]), "a second press opened a second probe (the first stroke left the transaction)")
    page.click(ABANDON, force=True)
    s = st(page)
    check(p, all(c == "unknown" for c in s["cells"]), "Contradiction left a stroke behind: the first probe was replaced by a second")
    check(p, s["disabled"] == "false" and s["open"] == "false", "Probe is not offered again after a close")
    page.click(PROBE, force=True)
    check(p, st(page)["open"] == "true", "Probe does not open a second transaction after the first closed")
    return p


def sc_middrag(page, host) -> list[str]:
    """A drag is one input: the three controls are ignored while a stroke is being drawn."""
    p: list[str] = []
    fresh(page, host)
    page.click(PROBE, force=True)
    mark(page, "filled", 0, 0)
    x, y = zoom_module._cell_centre(page, 3, 3)
    page.mouse.move(x, y)
    page.mouse.down()
    page.evaluate("document.querySelector('[data-player-probe-action=\"keep\"]').click()")
    page.evaluate("document.querySelector('[data-player-probe-action=\"abandon\"]').click()")
    page.mouse.up()
    s = st(page)
    check(p, s["open"] == "true" and s["cells"][at(0, 0)] == "filled", "a control pressed mid-gesture closed the probe or changed the board")
    check(p, s["marked"] == sorted([at(0, 0), at(3, 3)]), f"the probe lost or gained a cell around a mid-gesture press: {s['marked']}")
    fresh(page, host)
    x, y = zoom_module._cell_centre(page, 3, 3)
    page.mouse.move(x, y)
    page.mouse.down()
    page.evaluate("document.querySelector('[data-player-probe]').click()")
    page.mouse.up()
    check(p, st(page)["open"] == "false", "Probe opened a transaction in the middle of a stroke")
    return p


def sc_save(page, host) -> list[str]:
    """Rule 9 (AC-6): the page's OWN save is the save as of the checkpoint; a reload resumes there with no probe open."""
    p: list[str] = []
    fresh(page, host)
    mark(page, "filled", 0, 0)
    mark(page, "empty", 0, 1)
    save0 = st(page)["save"]
    keys0 = st(page)["keys"]
    page.click(PROBE, force=True)
    mark(page, "filled", 1, 1)
    mark(page, "maybe", 2, 2)
    mark(page, "filled", 0, 0)  # a PRE-probe cell touched in the probe
    s = st(page)
    check(p, s["save"] == save0, f"the save changed while the probe was open: {len(save_strokes(s)['done'])} strokes, not {len(json.loads(save0)['done'])}")
    check(p, s["keys"] == keys0, f"the page wrote another key: {sorted(set(s['keys']) ^ set(keys0))}")
    undone_cells = s["cells"]
    page.click(UNDO, force=True)  # an undo inside the probe does not put a probe stroke in the save either
    check(p, json.loads(st(page)["save"])["done"] == json.loads(save0)["done"], "an undo inside the probe wrote a probe stroke")
    reload(page)
    r = st(page)
    check(p, r["cells"][at(0, 0)] == "filled" and r["cells"][at(0, 1)] == "empty", "a reload did not resume at the probe's start")
    check(p, r["cells"][at(1, 1)] == "unknown" and r["cells"][at(2, 2)] == "unknown", "a reload brought back probe strokes")
    p.extend(closed_problems(r, "after the reload"))
    check(p, r["done"] == 2 and r["undone"] == 0, f"the pre-probe undo history is {r['done']}/{r['undone']}, not 2/0")
    check(p, undone_cells != r["cells"], "the scenario's probe held nothing")
    # Keep makes the whole history savable again; Contradiction saves the history with the probe's strokes on the redo stack
    page.click(PROBE, force=True)
    mark(page, "filled", 3, 3)
    page.click(KEEP, force=True)
    check(p, len(save_strokes(st(page))["done"]) == 3, "Keep did not save the kept stroke")
    reload(page)
    check(p, st(page)["cells"][at(3, 3)] == "filled", "a kept probe is lost on reload")
    return p


def sc_hint(page, host) -> list[str]:
    """Rule 3 with CARD-327's hint: a rung-3 hint inside a probe is the probe's, and is not saved until the probe is kept."""
    p: list[str] = []
    fresh(page, host)
    page.click(PROBE, force=True)
    want = expected(page)
    check(p, want is not None, "the fixture has no hint")
    for _ in range(3):
        press(page)
    s = st(page)
    cell = at(want["row"], want["col"]) if want else -1
    check(p, s["marked"] == [cell] and s["hinted"] == [cell], f"the hinted cell is not the probe's alone: marked {s['marked']}, hinted {s['hinted']}")
    check(p, s["hints"] == 1, f"hints reads {s['hints']}")
    check(p, save_strokes(s)["done"] == [], "a hint made inside the probe is in the save")
    page.click(KEEP, force=True)
    s = st(page)
    saved = save_strokes(s)["done"]
    check(p, len(saved) == 1 and saved[0].get("hint") is True, f"a kept hint is saved as {saved}")
    check(p, s["marked"] == [] and s["hints"] == 1, "a kept hint lost its count or kept its marker")
    # abandoning takes the hint away with the probe, and its count with it
    fresh(page, host)
    page.click(PROBE, force=True)
    for _ in range(3):
        press(page)
    page.click(ABANDON, force=True)
    s = st(page)
    check(p, s["hints"] == 0 and all(c == "unknown" for c in s["cells"]) and s["hinted"] == [], f"an abandoned hint left {s['hints']} hints, hinted {s['hinted']}")
    p.extend(closed_problems(s, "after abandoning a hint"))
    return p


def sc_reset(page, host) -> list[str]:
    """Rule 10: Reset clears the board and any open probe (the board can be brought back by undo, as ever, but no probe returns)."""
    p: list[str] = []
    fresh(page, host)
    mark(page, "filled", 0, 0)
    page.click(PROBE, force=True)
    mark(page, "filled", 1, 1)
    page.click(RESET, force=True)
    s = st(page)
    check(p, all(c == "unknown" for c in s["cells"]), "Reset did not clear the board")
    p.extend(closed_problems(s, "after reset"))
    page.click(UNDO, force=True)
    s = st(page)
    check(p, s["cells"][at(1, 1)] == "filled" and s["marked"] == [] and s["open"] == "false", "undoing a reset brought a probe back")
    # a Reset that does nothing (a blank board) closes nothing
    fresh(page, host)
    page.click(PROBE, force=True)
    page.click(RESET, force=True)
    check(p, st(page)["open"] == "true", "a Reset on a blank board closed the probe")
    return p


def constructed_solve(grid, hold_back: int):
    """A board of the grid's correct black cells but the last ``hold_back``, and those cells in order."""
    black = [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v]
    return ([("filled", black[:-hold_back])] if black[:-hold_back] else []), black[-hold_back:]


def sc_solve(page, host) -> list[str]:
    """Rule 7 (AC-7): marks that reach the clue-solved state COMMIT the probe; the banner behaves as today;
    marks that satisfy only some lines do not."""
    p: list[str] = []
    grid = FIXTURES["min"]
    strokes, rest = constructed_solve(grid, 3)
    # a partly solved board: three correct marks outstanding. Two of them in a probe leave the puzzle unsolved.
    fresh(page, host, "min", strokes)
    check(p, st(page)["solved"] is False, "the constructed board is already solved")
    page.click(PROBE, force=True)
    for row, col in rest[:2]:
        mark(page, "filled", row, col)
    s = st(page)
    check(p, s["open"] == "true" and s["solved"] is False and len(s["marked"]) == 2,
          f"a probe on a board that is not solved committed (open {s['open']}, solved {s['solved']}, marked {s['marked']})")
    row, col = rest[2]
    mark(page, "filled", row, col)  # the last cell: the whole puzzle is solved
    s = st(page)
    check(p, s["solved"] is True and s["bodySolved"] == "true", "the board did not reach the solved state")
    p.extend(closed_problems(s, "solved inside a probe"))
    check(p, s["disabled"] == "true", "Probe is offered on a solved board")
    saved = save_strokes(s)["done"]
    check(p, sum(len(x["cells"]) for x in saved) == sum(len(x[1]) for x in strokes) + 3, "the finishing marks are not in the save")
    page.click(PROBE, force=True)
    check(p, st(page)["open"] == "false", "a probe opened on a solved board")
    reload(page)
    r = st(page)
    check(p, r["solved"] is True and r["cells"] == s["cells"], "the finished picture is lost on reload")
    # the matched control: the same marks with no probe
    fresh(page, host, "min", strokes)
    for row, col in rest:
        mark(page, "filled", row, col)
    c = st(page)
    check(p, c["solved"] is True and c["cells"] == s["cells"] and c["bodySolved"] == "true", "the same marks outside a probe do not give the same solved board")
    return p


def sc_circles(page, host) -> list[str]:
    """Rule 8 (AC-8): the circles read the board as it is, probe marks included, exactly as for the same marks without a probe."""
    p: list[str] = []
    grid = FIXTURES["mixed"]
    taps = [("filled" if grid[r][c] else "empty", r, c) for r in (0, 1) for c in range(10)]
    fresh(page, host)
    page.click(PROBE, force=True)
    for tool, row, col in taps:
        mark(page, tool, row, col)
    probing = _dom(page)
    p.extend(_mismatch(page, "inside a probe"))
    check(p, any(any(line) for line in probing["rows"]) or any(any(line) for line in probing["columns"]), "the constructed marks circle nothing")
    check(p, st(page)["marked"] == sorted(at(r, c) for _, r, c in taps), "the probe does not hold the constructed marks")
    fresh(page, host)
    for tool, row, col in taps:
        mark(page, tool, row, col)
    check(p, _dom(page) == probing, "the circles differ between the same marks in and out of a probe")
    # and after an abandon the circles are those of the checkpoint board
    fresh(page, host)
    page.click(PROBE, force=True)
    for tool, row, col in taps:
        mark(page, tool, row, col)
    page.click(ABANDON, force=True)
    p.extend(_mismatch(page, "after an abandon"))
    check(p, _total(_dom(page)) == _total(probing) and not any(any(line) for line in _dom(page)["rows"]), "an abandoned probe left circled numbers")
    return p


def sc_pinch(page, host) -> list[str]:
    """A two-finger pinch neither opens a probe nor changes an open one (it zooms, which is a view)."""
    p: list[str] = []
    key = _open_max(page, host)
    pinch = zoom_module.TestPublicZoom_APinchZoomsAndPaintsNothing()._pinch
    page.evaluate("([k]) => localStorage.removeItem('nonogram-public:' + k)", [key])
    reload(page)
    before = st(page)
    pinch(page, 6, 0)
    s = st(page)
    check(p, s["open"] == "false" and s["cells"] == before["cells"] and s["marked"] == [], f"a pinch opened a probe or marked a cell (open {s['open']}, marked {s['marked']})")
    zoomed = _percent(page)
    page.click(PROBE, force=True)
    page.click(brush("filled"), force=True)
    page.click("td.player-cell[data-row=\"6\"][data-col=\"2\"]", force=True)
    open_state = st(page)
    check(p, open_state["marked"] == [at(6, 2, 30)] and open_state["open"] == "true", "the scenario's one probe mark is not there")
    pinch(page, 6, 0)
    s = st(page)
    check(p, s["open"] == "true" and s["marked"] == open_state["marked"] and s["cells"] == open_state["cells"],
          f"a pinch changed an open probe (open {s['open']}, marked {s['marked']})")
    check(p, s["save"] == before["save"] or s["save"] is None or save_strokes(s)["done"] == [], "a pinch wrote probe strokes to the save")
    check(p, _percent(page) != zoomed, "the pinch did not zoom: the scenario is vacuous")
    page.set_viewport_size({"width": 1280, "height": 720})
    return p


SCENARIOS = {
    "marks": sc_marks,
    "abandon": sc_abandon,
    "commit": sc_commit,
    "undo": sc_undo,
    "depth": sc_depth,
    "middrag": sc_middrag,
    "save": sc_save,
    "hint": sc_hint,
    "reset": sc_reset,
    "solve": sc_solve,
    "circles": sc_circles,
    "pinch": sc_pinch,
}


def run_scenarios(page, errors, host, names=None, canary=None) -> dict[str, list[str]]:
    """Every scenario (or ``names``) as {name: problems}; an uncaught page exception is a problem of the
    scenario that provoked it, and a canary that is not the served one is a problem of every scenario."""
    results: dict[str, list[str]] = {}
    for name in names or SCENARIOS:
        errors.clear()
        try:
            problems = list(SCENARIOS[name](page, host))
        except Exception as exc:  # noqa: BLE001 - a plant that breaks the page is a plant that fired
            problems = [f"the scenario could not finish: {type(exc).__name__}: {str(exc).splitlines()[0][:120]}"]
        if errors:
            problems.append(f"the page threw: {errors[0][:120]}")
        if canary is not None and page.evaluate("window.__served") != canary:
            problems.append("THE PLANT WAS NOT SERVED")
        results[name] = problems
    return results


def fired(results: dict[str, list[str]]) -> set[str]:
    return {name for name, problems in results.items() if problems}


@pytest.mark.browser
class TestPublicProbe_TheScenariosAreGreenOnTheRealPage:
    def test_every_scenario_passes_and_none_is_skipped(self, plant_page, host) -> None:
        page, errors = plant_page
        results = run_scenarios(page, errors, host)
        assert set(results) == set(SCENARIOS) and len(results) >= 12
        assert {k: v for k, v in results.items() if v} == {}

    @pytest.mark.parametrize("name", list(SCENARIOS))
    def test_each_scenario_is_green_on_its_own_node(self, plant_page, host, name) -> None:
        """The umbrella above names no scenario when it reds; these do, one node each."""
        page, errors = plant_page
        assert run_scenarios(page, errors, host, names=[name])[name] == []

    def test_the_served_canary_mechanism_serves_an_unchanged_file(self, plant_page, host) -> None:
        page, errors = plant_page
        serve_planted(page, host, "play.js", [], "control")
        results = run_scenarios(page, errors, host, names=["marks", "abandon"], canary="control")
        assert {k: v for k, v in results.items() if v} == {}


# --------------------------------------------------------------------------
# The plants: edge mutants of play.js, served through a ROUTE with a canary
# --------------------------------------------------------------------------


class Plant:
    def __init__(self, ident: str, edits: list[tuple[str, str]], fires: set[str], why: str) -> None:
        self.ident, self.edits, self.fires, self.why = ident, edits, set(fires), why


_MEMBERS = "probeCells(history, probe).map(([row, col]) => row * payload.width + col)"
_EVENT = 'isClueSolved(next.board, payload.rows, payload.columns) ? "keep" : event'
_OPEN = '    if (gesture || probeOpen.getAttribute("aria-disabled") === "true") return;\n    lastClick = null;\n    probe = nextProbe(probe, history, "open");'
_KEEP_SAVE = '    probe = nextProbe(probe, history, "keep");\n    writeSave(payload.key, serialize(history, payload));\n    refresh();'
_ABANDON = '    probe = nextProbe(probe, back, "abandon");\n    commit(back);'
_SAVE = "serialize(checkpointHistory(history, probe), payload)"
_RESET = 'commit(cleared, cleared === history ? "change" : "keep");'
_PINCH = "  function beginPinch(firstId, secondId) {\n    if (gesture) {"
_CIRCLES = "circledClues(history.board, payload.rows, payload.columns)"

#: Every plant is an EDGE mutant of the probe wiring (what the card's review lenses ask for: an abandon that leaves
#: one cell, a commit that touches a cell, a save that holds probe strokes, an undo past the checkpoint that does not
#: clamp, a rule 7 that fires on a partly solved board, a probe opened by a pinch, and the failure of every `===`
#: comparison this card added). The fired set is MEASURED: the scenarios that red, and no others.
PLANTS = [
    Plant("the-marker-is-on-every-stroke-not-the-probes", [(_MEMBERS, "history.done.flatMap((entry) => entry.stroke.cells).map(([row, col]) => row * payload.width + col)")],
          {"abandon", "commit", "hint", "marks", "reset", "save", "solve", "undo"}, "membership read off all strokes, pre-probe ones included"),
    Plant("the-marker-is-by-position-not-by-set", [(_MEMBERS, "history.done.slice(1).flatMap((entry) => entry.stroke.cells).map(([row, col]) => row * payload.width + col)")],
          {"abandon", "circles", "commit", "depth", "hint", "marks", "middrag", "pinch", "reset", "save", "solve", "undo"}, "the single-number checkpoint CARD-268's review replaced: a redone pre-probe stroke joins the probe"),
    Plant("the-marker-is-a-fifth-state", [('cells[index].dataset.probe = "true";', 'cells[index].dataset.probe = "true", cells[index].dataset.state = "probe";')],
          {"commit", "marks"}, "the probe written into data-state"),
    Plant("a-hint-is-not-a-member", [(_MEMBERS, _MEMBERS.replace("probeCells(history, probe)", "probeCells({ ...history, done: history.done.filter((entry) => entry.stroke.hint !== true) }, probe)"))],
          {"hint", "marks"}, "a rung-3 stroke inside the probe left out of it"),
    Plant("abandon-leaves-one-cell", [(_ABANDON, '    probe = nextProbe(probe, back, "abandon");\n    commit(redo(back));')],
          {"abandon", "depth", "hint", "undo"}, "the first probe stroke survives Contradiction"),
    Plant("abandon-does-not-write-the-save", [(_ABANDON, '    probe = nextProbe(probe, back, "abandon");\n    history = back;\n    shown = back.board;\n    refresh();')],
          {"abandon", "hint"}, "the abandon is not saved"),
    Plant("commit-touches-a-cell", [(_KEEP_SAVE, '    probe = nextProbe(probe, history, "keep");\n    history = undo(history);\n    shown = history.board;\n    writeSave(payload.key, serialize(history, payload));\n    refresh();')],
          {"commit", "hint", "save"}, "Keep that undoes a stroke"),
    Plant("keep-does-not-write-the-save", [(_KEEP_SAVE, '    probe = nextProbe(probe, history, "keep");\n    refresh();')],
          {"commit", "hint", "save"}, "the kept strokes are not savable"),
    Plant("the-save-holds-probe-strokes", [(_SAVE, "serialize(history, payload)")],
          {"commit", "hint", "pinch", "save"}, "no checkpointHistory"),
    Plant("undo-past-the-checkpoint-closes-the-probe", [(_EVENT, 'isClueSolved(next.board, payload.rows, payload.columns) || (probe !== null && next.done.length === 0) ? "keep" : event')],
          {"reset", "undo"}, "the probe does not clamp: it ends when everything is undone"),
    Plant("a-second-press-opens-a-second-probe", [(_OPEN, '    if (gesture) return;\n    lastClick = null;\n    probe = nextProbe(null, history, "open");')],
          {"depth", "solve"}, "depth 2: the checkpoint moves"),
    Plant("rule-seven-fires-on-any-filled-cell", [(_EVENT, 'history.board.cells.includes(FILLED) ? "keep" : event')],
          {"abandon", "circles", "commit", "depth", "marks", "middrag", "save", "solve", "undo"}, "rule 7 on a partly solved board"),
    Plant("rule-seven-never-fires", [(_EVENT, "event")],
          {"solve"}, "no auto-commit"),
    Plant("a-solved-board-still-offers-probe", [('probeOpen.setAttribute("aria-disabled", probe === null && !done ? "false" : "true");', 'probeOpen.setAttribute("aria-disabled", probe === null ? "false" : "true");')],
          {"solve"}, "the toggle on a solved board"),
    Plant("reset-leaves-the-probe-open", [(_RESET, "commit(cleared);")],
          {"reset"}, "rule 10"),
    Plant("a-blank-reset-closes-the-probe", [(_RESET, 'commit(cleared, cleared !== history ? "change" : "keep");')],
          {"reset"}, "=== failed"),
    Plant("the-event-is-ignored", [(_EVENT, 'isClueSolved(next.board, payload.rows, payload.columns) ? "keep" : "change"')],
          {"reset"}, "the reset's own event"),
    Plant("a-pinch-opens-a-probe", [(_PINCH, '  function beginPinch(firstId, secondId) {\n    probe = nextProbe(probe, history, "open");\n    if (gesture) {')],
          {"pinch"}, "a pinch that opens a probe"),
    Plant("a-control-works-mid-drag", [('    if (gesture || probe === null) return;\n    lastClick = null;\n    probe = nextProbe(probe, history, "keep");', '    if (probe === null) return;\n    lastClick = null;\n    probe = nextProbe(probe, history, "keep");'),
                                       ('    if (gesture || probeOpen.getAttribute("aria-disabled") === "true") return;', '    if (probeOpen.getAttribute("aria-disabled") === "true") return;')],
          {"middrag"}, "the gesture guard of Keep and Probe"),
    Plant("the-note-never-shows", [("probeNote.hidden = probe === null || saying;", "probeNote.hidden = true;")],
          {"marks"}, "no warning that a reload abandons the probe"),
    Plant("the-actions-show-with-no-probe", [("    probeKeep.hidden = probe === null;", "    probeKeep.hidden = false;")],
          {"abandon", "commit", "hint", "marks", "reset", "save", "solve", "undo"}, "Keep offered with nothing to keep"),
    Plant("the-usage-paragraph-stays-beside-the-note", [("hint.hidden = saying || !(probe === null);", "hint.hidden = saying;")],
          {"marks"}, "two occupants of the slot"),
    Plant("the-note-stays-under-a-sentence", [("probeNote.hidden = probe === null || saying;", "probeNote.hidden = probe === null;")],
          {"marks"}, "two occupants of the slot, the other pair"),
    Plant("the-circles-read-the-checkpoint-board", [(_CIRCLES, "circledClues(abandonProbe(history, probe).board, payload.rows, payload.columns)")],
          {"circles"}, "the circles blind to probe marks"),
    Plant("the-marker-is-never-removed", [("      else delete cells[index].dataset.probe;", "")],
          {"abandon", "commit", "hint", "reset", "solve", "undo"}, "a stale marker"),
]


@pytest.mark.browser
class TestPublicProbe_EachPlantFiresTheScenarioItIsAbout:
    @pytest.mark.parametrize("plant", PLANTS, ids=[p.ident for p in PLANTS])
    def test_a_plant_is_served_fires_exactly_its_scenarios_and_its_control_is_green(self, plant_page, host, plant) -> None:
        page, errors = plant_page
        about = sorted(plant.fires)
        control = run_scenarios(page, errors, host, names=about)  # the matched control, in this very run
        assert {k: v for k, v in control.items() if v} == {}, ("the matched control", plant.ident)
        assert len(control) == len(about)
        serve_planted(page, host, "play.js", plant.edits, plant.ident)
        results = run_scenarios(page, errors, host, canary=plant.ident)
        assert all("THE PLANT WAS NOT SERVED" not in p for ps in results.values() for p in ps), "the plant was not served"
        assert len(results) == len(SCENARIOS), "a scenario was skipped"
        assert fired(results) == plant.fires, f"FIRED {plant.ident} {json.dumps(sorted(fired(results)))}"


# ==========================================================================
# AC-1 .. AC-8 - the transaction, on the served page
# ==========================================================================


def scenario_green(page, errors, host, name: str) -> None:
    result = run_scenarios(page, errors, host, names=[name])[name]
    assert result == [], result


def random_marks(rng, count: int) -> list[tuple[str, int, int]]:
    return [(rng.choice(["filled", "empty", "maybe", "unknown"]), rng.randrange(10), rng.randrange(10)) for _ in range(count)]


CORPUS_CASES = 12


def corpus_cases(seed: int) -> list[tuple[list, list]]:
    import random

    rng = random.Random(seed)
    return [(random_marks(rng, rng.randrange(0, 5)), random_marks(rng, rng.randrange(1, 7))) for _ in range(CORPUS_CASES)]


@pytest.mark.browser
class TestPublicProbe_MarksCarryTheLook:
    def test_every_mark_made_in_a_probe_carries_the_marker_and_the_cells_before_it_do_not(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "marks")

    def test_a_rung_three_hint_inside_a_probe_is_a_member_of_it(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "hint")

    def test_the_marker_is_a_dashed_outline_and_the_four_states_keep_their_own_look_under_it(self, browser_page, host) -> None:
        page = browser_page
        fresh(page, host)
        # unprobed twins of each state first, then the probe's own cells
        for tool, row, col in (("filled", 6, 6), ("empty", 7, 7), ("maybe", 8, 8)):
            mark(page, tool, row, col)
        page.click(PROBE, force=True)
        for tool, row, col in (("filled", 1, 1), ("empty", 2, 2), ("maybe", 3, 3)):
            mark(page, tool, row, col)
        _move_away(page)
        look = page.evaluate(
            """() => {
              const cell = (r, c) => document.querySelector(`td.player-cell[data-row="${r}"][data-col="${c}"]`);
              const read = (el) => {
                const s = getComputedStyle(el), a = getComputedStyle(el, '::after');
                return { state: el.dataset.state, ground: s.backgroundColor, glyph: a.content, glyphColour: a.color,
                         outlineStyle: s.outlineStyle, outlineWidth: s.outlineWidth, outlineColour: s.outlineColor, shadow: s.boxShadow };
              };
              const probe = document.createElement('i'); probe.style.color = 'var(--player-probe)';
              const ink = document.createElement('i'); ink.style.color = 'var(--player-probe-ink)';
              document.querySelector('.player-stage').append(probe, ink);
              const colours = { probe: getComputedStyle(probe).color, ink: getComputedStyle(ink).color };
              probe.remove(); ink.remove();
              return { colours,
                twins: { filled: read(cell(6, 6)), empty: read(cell(7, 7)), maybe: read(cell(8, 8)), unknown: read(cell(9, 9)) },
                probed: { filled: read(cell(1, 1)), empty: read(cell(2, 2)), maybe: read(cell(3, 3)) } };
            }"""
        )
        for state, probed in look["probed"].items():
            twin = look["twins"][state]
            assert (probed["outlineStyle"], probed["outlineWidth"]) == ("dashed", "2px"), (state, probed)
            assert twin["outlineStyle"] == "none", (state, twin)
            # the marker changes the OUTLINE and nothing else the state paints: ground, glyph and glyph colour are the twin's
            for same in ("state", "ground", "glyph", "glyphColour", "shadow"):
                assert probed[same] == twin[same], (state, same, probed[same], twin[same])
            assert probed["outlineColour"] == (look["colours"]["ink"] if state == "filled" else look["colours"]["probe"]), (state, probed["outlineColour"], look["colours"])
        # and the four states are still four: distinct (ground, glyph) pairs among the probed cells and the untouched blank
        looks = {(v["ground"], v["glyph"]) for v in [*look["probed"].values(), look["twins"]["unknown"]]}
        assert len(looks) == 4, looks


@pytest.mark.browser
class TestPublicProbe_AbandonRestoresTheCheckpointBoard:
    def test_the_scenario_is_green(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "abandon")

    def test_over_a_seeded_corpus_the_board_is_the_checkpoint_board_cell_for_cell(self, browser_page, host) -> None:
        page = browser_page
        cases = corpus_cases(380)
        assert len(cases) >= CORPUS_CASES >= 12, "the corpus may not shrink"
        probe_strokes = 0
        for before, inside in cases:
            fresh(page, host)
            for tool, row, col in before:
                mark(page, tool, row, col)
            snapshot = st(page)
            page.click(PROBE, force=True)
            for tool, row, col in inside:
                mark(page, tool, row, col)
            probe_strokes += st(page)["done"] - snapshot["done"]
            page.click(ABANDON, force=True)
            after = st(page)
            assert after["cells"] == snapshot["cells"] and after["dom"] == snapshot["dom"], (before, inside)
            assert after["marked"] == [] and after["open"] == "false", (before, inside)
        assert probe_strokes >= 20, "the corpus made too few probe strokes to mean anything"


@pytest.mark.browser
class TestPublicProbe_CommitKeepsCellsAndDropsTheLook:
    def test_the_scenario_is_green(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "commit")

    def test_over_a_seeded_corpus_no_cell_changes_and_no_marker_remains(self, browser_page, host) -> None:
        page = browser_page
        cases = corpus_cases(381)
        assert len(cases) >= CORPUS_CASES >= 12, "the corpus may not shrink"
        marked_cells = 0
        for before, inside in cases:
            fresh(page, host)
            for tool, row, col in before:
                mark(page, tool, row, col)
            page.click(PROBE, force=True)
            for tool, row, col in inside:
                mark(page, tool, row, col)
            held = st(page)
            marked_cells += len(held["marked"])
            page.click(KEEP, force=True)
            after = st(page)
            assert after["cells"] == held["cells"] and after["dom"] == held["dom"], (before, inside)
            assert after["marked"] == [] and after["open"] == "false" and (after["done"], after["undone"]) == (held["done"], held["undone"])
        assert marked_cells >= 15, "the corpus held too few probe cells to mean anything"


@pytest.mark.browser
class TestPublicProbe_UndoClampsTheCheckpoint:
    def test_the_scenario_is_green(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "undo")

    def test_the_keyboard_undo_and_redo_move_the_probe_like_the_buttons(self, browser_page, host) -> None:
        page = browser_page
        fresh(page, host)
        page.click(PROBE, force=True)
        mark(page, "filled", 1, 1)
        mark(page, "filled", 2, 2)
        page.keyboard.press("Control+z")
        assert st(page)["marked"] == [at(1, 1)]
        page.keyboard.press("Control+Shift+z")
        assert st(page)["marked"] == sorted([at(1, 1), at(2, 2)])
        page.keyboard.press("Control+z")
        page.keyboard.press("Control+z")
        s = st(page)
        assert s["marked"] == [] and s["open"] == "true"


@pytest.mark.browser
class TestPublicProbe_OnlyOneProbeAtATime:
    def test_the_probe_control_is_disabled_while_one_is_open_and_a_press_is_a_no_op(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "depth")

    def test_the_controls_are_ignored_while_a_stroke_is_being_drawn(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "middrag")


@pytest.mark.browser
class TestPublicProbe_AReloadAbandonsTheOpenProbe:
    def test_the_save_is_the_save_as_of_the_checkpoint(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "save")

    def test_the_page_says_so_in_one_line_where_the_controls_are(self, browser_page, host) -> None:
        page = browser_page
        fresh(page, host)
        assert st(page)["noteShown"] is False
        page.click(PROBE, force=True)
        facts = page.evaluate(
            """() => {
              const note = document.querySelector('[data-player-probe-note]');
              const bar = document.querySelector('[data-player-probe-bar]');
              const n = note.getBoundingClientRect(), b = bar.getBoundingClientRect();
              return { text: note.textContent.trim(), lines: (() => { const r = document.createRange(); r.selectNodeContents(note); return r.getClientRects().length; })(),
                       below: n.top >= b.top, visible: n.width > 0 && n.height > 0 };
            }"""
        )
        assert facts["visible"] and facts["text"] == "Leaving this page abandons the open probe — press Keep or Contradiction first.", facts
        assert facts["lines"] <= 2, facts  # one short line at desktop width; it may wrap once in the slot

    def test_the_save_never_holds_a_probe_stroke_over_a_seeded_corpus(self, browser_page, host) -> None:
        page = browser_page
        for before, inside in corpus_cases(382):
            fresh(page, host)
            for tool, row, col in before:
                mark(page, tool, row, col)
            held = st(page)["save"]
            page.click(PROBE, force=True)
            for tool, row, col in inside:
                mark(page, tool, row, col)
            assert json.loads(st(page)["save"]) == json.loads(held), (before, inside)


@pytest.mark.browser
class TestPublicProbe_SolvingCommitsTheProbe:
    def test_marks_that_reach_the_clue_solved_state_commit_the_probe_and_the_banner_is_todays(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "solve")

    def test_reset_closes_an_open_probe(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "reset")

    def test_the_constructed_board_is_one_mark_from_solved_and_the_fixture_is_what_the_card_needs(self) -> None:
        grid = FIXTURES["min"]
        strokes, rest = constructed_solve(grid, 3)
        assert len(rest) == 3 and strokes and all(grid[r][c] for r, c in rest)
        black = sum(sum(row) for row in grid)
        assert sum(len(cells) for _, cells in strokes) == black - 3


@pytest.mark.browser
class TestPublicProbe_CirclesSeeProbeMarksAsMarks:
    def test_the_circle_set_is_circledclues_of_the_recorded_board_probe_strokes_included(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "circles")


@pytest.mark.browser
class TestPublicProbe_APinchNeitherOpensNorChangesAProbe:
    def test_a_two_finger_pinch_leaves_the_probe_alone(self, plant_page, host) -> None:
        page, errors = plant_page
        scenario_green(page, errors, host, "pinch")


# ==========================================================================
# AC-9 - the transitions are the module's, the cell has four states, colours are tokens
# ==========================================================================

from tests.test_public_player import assembler  # noqa: E402
from tests.test_public_player_hint import declaration_census  # noqa: E402

STATES = {"unknown", "filled", "empty", "maybe"}
EVENT_LITERAL = re.compile(r'(?<![=\w-])"(?:open|keep|abandon|change)"')


def probe_code_violations(js_source: str) -> list[str]:
    """Every way ``play.js`` decides a probe transition itself instead of asking the module."""
    code, _ = _scan(js_source)
    problems: list[str] = []
    # 1. every value `probe` is ever given is the module's answer (or its initial null)
    given = [m.group(1) for m in re.finditer(r"(?<![\w.$])probe\s*=(?!=)\s*([A-Za-z_$][\w$]*)", code)]
    if sorted(given) != ["nextProbe"] * 4 + ["null"]:
        problems.append(f"`probe` is given {sorted(given)}: only `null` once and nextProbe(...) four times (commit, open, keep, abandon)")
    if len(re.findall(r"(?<![\w.$])probe\s*=(?!=)", code)) != len(given):
        problems.append("`probe` is assigned something that is not a name")
    # 2. nothing named for the probe is declared but the five handles, the value and the one painter
    names = {word for word in declaration_census(code) if "robe" in word}
    allowed = {"const:probeBar", "const:probeOpen", "const:probeKeep", "const:probeAbandon", "const:probeNote", "let:probe", "function:paintProbe"}
    if names != allowed:
        problems.append(f"probe declarations are {sorted(names)}, not {sorted(allowed)}")
    # 3. the module's four functions are imported and called; no export or class of the page's own
    imported = re.search(r'import\s*\{([^}]*)\}\s*from\s*"/solver_state\.js"', js_source)
    for name in ("nextProbe", "probeCells", "abandonProbe", "checkpointHistory"):
        if imported is None or name not in imported.group(1):
            problems.append(f"{name} is not imported from the module")
        if not re.search(rf"\b{name}\(", code):
            problems.append(f"{name} is never called")
    # 4. an event name appears only on a line that hands it to the module (or to commit, which does)
    for number, line in enumerate(js_source.splitlines(), 1):
        if line.strip().startswith("//") or not EVENT_LITERAL.search(line):
            continue
        if not re.search(r"nextProbe\(|commit\(|function commit|nextRung\(", line):
            problems.append(f"line {number} names a probe event outside nextProbe/commit: {line.strip()}")
    # 5. the cell's state is only ever assigned from the board (paint) or at draw time
    if re.search(r"dataset\.state\s*=\s*[\"'`]", js_source.split("const paint =")[1].split("\n};")[0]):
        problems.append("paint writes a literal state")
    return problems


def test_the_public_probe_look_comes_from_tokens() -> None:
    """AC-9 (colours): every value in the probe's rules is a token, a token-only color-mix(), or the one keyword `dashed`."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tests.test_public_player_agreement import _probe_rules  # the same extractor AC-13 compares with

    css = PLAYER_CSS.read_text(encoding="utf-8")
    tokens = (ADMIN_STATIC / "tokens.css").read_text(encoding="utf-8")
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", tokens)) | set(re.findall(r"^\s*(--player-[a-z-]+):", css, re.M))

    def problems(text: str) -> list[str]:
        found: list[str] = []
        rules = _probe_rules(text)
        assert len(rules) >= 8, sorted(rules)
        for selector, declared in rules.items():
            for prop, value in declared.items():
                bare = re.sub(r"var\((--[a-z0-9-]+)\)", "", value)
                if re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(|\bcolor\((?!-)", value) or re.search(r"\b(?:red|blue|green|black|white|orange|yellow|gray|grey)\b", bare):
                    found.append(f"{selector} {prop}: a colour literal: {value}")
                for name in re.findall(r"var\((--[a-z0-9-]+)\)", value):
                    if name not in defined:
                        found.append(f"{selector} {prop}: {name} is not defined")
                if "color-mix(" in value and not re.fullmatch(r"color-mix\(in srgb, var\(--[a-z0-9-]+\) \d+%, var\(--[a-z0-9-]+\)\)", value):
                    found.append(f"{selector} {prop}: a color-mix that is not tokens only: {value}")
                if prop.startswith("outline") and prop == "outline" and not re.fullmatch(r"var\(--[a-z0-9-]+\) dashed var\(--[a-z0-9-]+\)", value):
                    found.append(f"{selector} {prop}: the outline is not a token width, `dashed`, a token colour: {value}")
        return found

    assert problems(css) == []
    # the controls, each of which fails just past the bound
    assert problems(css.replace("dashed var(--player-probe);", "dashed #8a5a00;")) != []
    assert problems(css.replace("var(--color-warning) 86%", "var(--color-warnin) 86%")) != []
    assert problems(css.replace("var(--color-warning) 42%, var(--grid-paper)", "rgb(204, 186, 144) 42%, var(--grid-paper)")) != []
    assert problems(css.replace("outline-color: var(--color-accent); }", "outline-color: red; }")) != []


@pytest.mark.browser
class TestPublicProbe_StateIsThePureModulesAndStatesAreFour:
    def test_play_js_asks_the_module_for_every_transition_and_defines_none_of_its_own(self) -> None:
        assert probe_code_violations(PLAY_JS.read_text(encoding="utf-8")) == []

    @pytest.mark.parametrize(
        ("label", "old", "new", "expect"),
        [
            ("the-page-closes-the-probe-itself", '    probe = nextProbe(probe, history, "keep");', "    probe = null;", "`probe` is given"),
            ("the-page-opens-a-probe-itself", '    probe = nextProbe(probe, history, "open");', "    probe = history.done.map((entry) => entry.stroke);", "`probe` is given"),
            ("a-second-copy-of-the-open-rule", "  const probeNote =", "  const probeStart = (h) => h.done.length;\n  const probeNote =", "probe declarations"),
            ("a-probe-flag", "  let probe = null;", "  let probe = null;\n  let probing = false;", ""),
            ("the-membership-function-is-not-called", "probeCells(history, probe)", "[]", "probeCells is never called"),
            ("the-checkpoint-save-is-not-called", "checkpointHistory(history, probe)", "history", "checkpointHistory is never called"),
            ("an-import-is-dropped", "  nextProbe, probeCells, abandonProbe, checkpointHistory,", "  probeCells, abandonProbe, checkpointHistory,", "nextProbe is not imported"),
            ("an-event-named-in-the-page", "  function paintProbe() {", '  const opened = "open";\n  function paintProbe() {', "names a probe event"),
        ],
    )
    def test_a_page_that_decides_a_transition_is_refused_beside_its_clean_control(self, label, old, new, expect) -> None:
        source = PLAY_JS.read_text(encoding="utf-8")
        assert probe_code_violations(source) == [], "the matched control"
        assert source.count(old) == 1, f"the plant must apply exactly once: {old!r} ({source.count(old)})"
        found = probe_code_violations(source.replace(old, new))
        if expect:
            assert any(expect in problem for problem in found), (label, found)
        else:  # a new page variable is refused by the hint module's closed census; here it must not be a probe transition
            assert not any("`probe` is given" in problem for problem in found), (label, found)

    def test_the_cell_has_exactly_the_four_states_and_a_probe_session_writes_no_other(self, browser_page, host) -> None:
        page = browser_page
        from tests.test_public_player_zoom import _module

        states = _module(page.context.new_page() if False else page, "[...S.CELL_STATES]") if page.url != "about:blank" else None
        fresh(page, host)
        states = _module(page, "[...S.CELL_STATES]")
        assert len(states) == 4 and set(states) == STATES, states
        assert _module(page, "[...S.PROBE_EVENTS]") == ["open", "keep", "abandon", "change"]
        for fn in ("nextProbe", "probeCells", "abandonProbe", "checkpointHistory", "probeStart"):
            assert _module(page, f"typeof S.{fn}") == "function", fn
        seen: set[str] = set()
        for before, inside in corpus_cases(383):
            fresh(page, host)
            for tool, row, col in before:
                mark(page, tool, row, col)
            page.click(PROBE, force=True)
            for tool, row, col in inside:
                mark(page, tool, row, col)
            seen |= set(st(page)["dom"])
            page.click(ABANDON if len(inside) % 2 else KEEP, force=True)
            seen |= set(st(page)["dom"])
        assert seen <= STATES and len(seen) >= 3, seen
        assert page.evaluate("[...new Set([...document.querySelectorAll('[data-state]')].map((e) => e.dataset.state))].every((s) => ['unknown','filled','empty','maybe'].includes(s))")

    def test_the_served_module_and_tokens_are_the_admins_byte_for_byte(self, host) -> None:
        site_dir = host[1].site_dir
        for source, served in assembler.COPIED_FROM_ADMIN.items():
            assert (site_dir / served).read_bytes() == (Path(__file__).resolve().parent.parent / source).read_bytes(), served
        assert {"solver_state.js", "tokens.css"} <= set(assembler.COPIED_FROM_ADMIN.values())
        assert (site_dir / "solver_state.js").read_bytes() == (ADMIN_STATIC / "solver_state.js").read_bytes()


# ==========================================================================
# AC-10 - the controls are OUTSIDE the toolbar
# ==========================================================================

_PROBE_FACTS = """() => {
  const toolbar = document.querySelector('.player-toolbar');
  const stage = document.querySelector('[data-player-stage]');
  const usage = document.querySelector('[data-player-hint]');
  const out = {};
  for (const [name, selector] of [['probe', '[data-player-probe]'], ['keep', '[data-player-probe-action="keep"]'], ['abandon', '[data-player-probe-action="abandon"]']]) {
    const el = document.querySelector(selector);
    const r = el.getBoundingClientRect();
    out[name] = { inToolbar: toolbar.contains(el), width: r.width, height: r.height, fontSize: parseFloat(getComputedStyle(el).fontSize),
                  underStage: !!(stage.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING),
                  beforeUsage: !!(el.compareDocumentPosition(usage) & Node.DOCUMENT_POSITION_FOLLOWING),
                  visible: r.width > 0 && r.height > 0 };
  }
  const bar = document.querySelector('[data-player-probe-bar]');
  out.barInToolbar = toolbar.contains(bar);
  out.barHidden = bar.hidden;
  return out;
}"""


def probe_toolbar_problems(page, *, open_probe: bool) -> list[str]:
    facts = page.evaluate(_PROBE_FACTS)
    hint_facts = page.evaluate(_TOOLBAR_FACTS)
    found: list[str] = []
    for name in ("probe", "keep", "abandon"):
        f = facts[name]
        if f["inToolbar"]:
            found.append(f"{name} is inside .player-toolbar")
        if not (f["underStage"] and f["beforeUsage"]):
            found.append(f"{name} is not under the board and before the usage paragraph")
        if f["visible"] and (f["height"] < 44 or f["width"] < 44):
            found.append(f"{name} is {f['width']:.0f} x {f['height']:.0f} px, under the 44 px touch floor")
        if (name == "probe" or open_probe) and not f["visible"]:
            found.append(f"{name} is not visible")
    if facts["barInToolbar"] or facts["barHidden"]:
        found.append("the probe bar is in the toolbar or hidden after the board is drawn")
    if hint_facts["buttons"] != TOOLBAR_BUTTONS:
        found.append(f"the toolbar's button set changed: {hint_facts['buttons']}")
    return found


@pytest.mark.browser
class TestPublicProbe_TheControlsAreOutsideTheToolbar:
    def test_the_controls_are_under_the_board_44px_and_the_toolbar_is_what_it_was(self, browser_page, host) -> None:
        page = browser_page
        fresh(page, host)
        assert probe_toolbar_problems(page, open_probe=False) == []
        page.click(PROBE)  # a real click, with Playwright's actionability checks
        assert probe_toolbar_problems(page, open_probe=True) == []

    def test_the_markup_agrees_before_a_script_runs(self) -> None:
        html = PLAY_HTML.read_text(encoding="utf-8")
        toolbar = html[html.index('<div class="player-toolbar"') : html.index('</div>\n\n  <div class="player-stage"')]
        assert "data-player-probe" not in toolbar and "player-probe" not in toolbar
        assert html.index("data-player-stage") < html.index("data-player-probe-bar") < html.index('<p class="player-hint"')
        assert re.search(r'<div class="player-probe"[^>]*\bhidden\b', html), "the bar is hidden until the board is drawn"
        for action in ("keep", "abandon"):
            assert re.search(rf'<button[^>]*data-player-probe-action="{action}"[^>]*\bhidden\b', html), action
        assert re.search(r"<p class=\"player-probe-note\"[^>]*\bhidden\b", html)

    def test_a_probe_control_moved_into_the_toolbar_is_refused(self, plant_page, host) -> None:
        page, _ = plant_page
        fresh(page, host)
        assert probe_toolbar_problems(page, open_probe=False) == [], "the matched control"
        page.evaluate("() => document.querySelector('.player-toolbar').append(document.querySelector('[data-player-probe]'))")
        found = probe_toolbar_problems(page, open_probe=False)
        assert any("probe is inside .player-toolbar" in p for p in found) and any("button set changed" in p for p in found), found

    def test_a_control_under_the_touch_floor_is_refused(self, plant_page, host) -> None:
        page, _ = plant_page
        fresh(page, host)
        assert probe_toolbar_problems(page, open_probe=False) == [], "the matched control"
        page.add_style_tag(content=".player-probe .btn { min-height: 43px !important; min-width: 0 !important; height: 43px; }")
        assert any("under the 44 px touch floor" in p for p in probe_toolbar_problems(page, open_probe=False))

    @pytest.mark.parametrize("scroll", [0, 120, 100000], ids=["top", "scrolled", "bottom"])
    def test_the_controls_are_reachable_and_legible_at_the_zoom_maximum_and_a_scrolled_offset(self, browser_page, host, scroll) -> None:
        page = browser_page
        page.set_viewport_size(PHONE)
        _board(page, host, host[2]["max"], FIXTURES["max"], [])
        bounds = _bounds(page)
        while _percent(page) < bounds["max"]:
            _press(page, "in")
        assert _percent(page) == bounds["max"]
        _settle(page)
        page.evaluate("(y) => window.scrollTo(0, y)", scroll)
        _settle(page)
        def reachable(name: str, selector: str) -> None:
            page.locator(selector).scroll_into_view_if_needed()
            _settle(page)
            facts = page.evaluate(_PROBE_FACTS)[name]
            assert facts["fontSize"] >= 14 and facts["width"] >= 44 and facts["height"] >= 44, (name, facts)
            spot = page.evaluate(
                """(sel) => {
                  const b = document.querySelector(sel);
                  const r = b.getBoundingClientRect();
                  const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  const note = document.querySelector('[data-player-probe-note]');
                  const n = note.hidden ? r : note.getBoundingClientRect();
                  return { onIt: at === b || b.contains(at), right: Math.max(r.right, n.right), width: innerWidth };
                }""",
                selector,
            )
            assert spot["onIt"] and spot["right"] <= spot["width"], (name, scroll, spot)

        reachable("probe", PROBE)
        page.click(PROBE)  # a real click: visible, stable, enabled and receiving the event
        page.evaluate("window.scrollTo(0, 0)")  # the stage is in view at the top of the page: mark a cell there
        where = page.evaluate(
            """() => {
              for (const td of document.querySelectorAll('td.player-cell')) {
                const r = td.getBoundingClientRect();
                const x = r.left + r.width / 2, y = r.top + r.height / 2;
                if (x > 0 && y > 0 && x < innerWidth && y < innerHeight && document.elementFromPoint(x, y) === td) {
                  return { row: Number(td.dataset.row), col: Number(td.dataset.col), x, y };
                }
              }
              return null;
            }"""
        )
        assert where is not None, "no cell of the zoomed board is reachable at the top of the page"
        page.mouse.click(where["x"], where["y"])
        page.evaluate("(y) => window.scrollTo(0, y)", scroll)
        _settle(page)
        reachable("keep", KEEP)
        reachable("abandon", ABANDON)
        # the marker is on the cell at the zoom maximum, still a dashed 2 px outline in the cell's place
        assert st(page)["marked"] == [at(where["row"], where["col"], 30)], st(page)["marked"]
        outline = page.evaluate("(() => { const s = getComputedStyle(document.querySelector('td.player-cell[data-probe]')); return [s.outlineStyle, s.outlineWidth]; })()")
        assert outline == ["dashed", "2px"], outline
        page.click(ABANDON)
        assert st(page)["open"] == "false" and st(page)["marked"] == []


#: The zoom module pins that the space BELOW the stage is smaller than the stage's offset from the top
#: (tests/test_public_zoom.py, over a grid of viewports, with the page at rest). The Probe bar sits in the
#: row of the Hint bar and the usage paragraph, and while a probe is open the NOTE takes the paragraph's slot.
#: DECLARED BOUNDS (ADR-0039/R3), each the least margin (stage offset minus space below, px) over the zoom
#: module's grid, MEASURED this card on the 30 x 30 board, 2026-11-06:
#:   * at rest (the Probe button beside the Hint bar): 1 px at the 840 px column, where the usage paragraph
#:     gains one 20 px line because the bars are 77 px wider than the cut's (the cut's least margin was 21 px
#:     at the same viewports); positive, which is the premise, and one line from failing;
#:   * with a probe open (Keep, Contradiction and the note shown, the paragraph hidden): 50 px;
#:   * with a probe open AND a rung-2 hint sentence showing (the note yields to the sentence): 2 px, at the
#:     840-960 px columns, where the bars take the row and the sentence wraps to two lines beside them.
#: Past each bound there is a control that fails: one more 20 px line under the paragraph at rest, both
#: occupants of the slot at once (the note AND the paragraph) while open, and a sentence far longer than any
#: the page says while open.
CLOSED_WORST_MARGIN_PX = 1
OPEN_WORST_MARGIN_PX = 50
OPEN_SENTENCE_WORST_MARGIN_PX = 2
VIOLATIONS_WITH_BOTH_OCCUPANTS = 191  # MEASURED 2026-11-06, of 232 viewports: the note AND the usage paragraph showing
VIOLATIONS_WITH_A_LINE_MORE_AT_REST = 15  # MEASURED 2026-11-06, of 232 viewports: 20 px more under the paragraph at rest


def bar_margins(page, host, *, mode: str, extra: str = "") -> dict[tuple[int, int], int]:
    """(width, height) -> stage-top-offset minus space-below, for ``mode`` in closed / open / sentence."""
    page.set_viewport_size(PHONE)
    _board(page, host, host[2]["max"], FIXTURES["max"], [])
    if mode in ("open", "sentence"):
        page.click(PROBE, force=True)
    if mode == "sentence":
        press(page)
        press(page)
    if extra:
        page.evaluate(extra)
    out: dict[tuple[int, int], int] = {}
    for height in range(SHORTEST, TALLEST + 1, 70):
        for width in range(NARROWEST, WIDEST + 1, 40):
            page.set_viewport_size({"width": width, "height": height})
            _settle(page)
            r = page.evaluate(_GEOMETRY)
            out[(width, height)] = r["innerTop"] - (r["docHeight"] - r["docBottom"])
    return out


@pytest.mark.browser
class TestPublicProbe_TheBarsKeepTheZoomModulesPremise:
    def test_at_rest_the_space_below_stays_smaller_than_the_top(self, browser_page, host) -> None:
        margins = bar_margins(browser_page, host, mode="closed")
        assert len(margins) >= 150
        assert min(margins.values()) == CLOSED_WORST_MARGIN_PX > 0, (min(margins.values()), sorted(k for k, v in margins.items() if v <= 0))

    def test_with_a_probe_open_the_note_takes_the_paragraphs_slot_and_the_premise_holds(self, browser_page, host) -> None:
        margins = bar_margins(browser_page, host, mode="open")
        assert min(margins.values()) == OPEN_WORST_MARGIN_PX > 0, (min(margins.values()), sorted(k for k, v in margins.items() if v <= 0))

    def test_with_a_probe_open_and_a_hint_sentence_showing_the_premise_holds(self, browser_page, host) -> None:
        margins = bar_margins(browser_page, host, mode="sentence")
        assert min(margins.values()) == OPEN_SENTENCE_WORST_MARGIN_PX > 0, (min(margins.values()), sorted(k for k, v in margins.items() if v <= 0))

    def test_a_line_more_under_the_paragraph_at_rest_goes_past_the_bound(self, browser_page, host) -> None:
        """The control that fails just past the rest bound: one 20 px line is the whole margin and then some."""
        margins = bar_margins(browser_page, host, mode="closed", extra="document.querySelector('[data-player-hint]').style.paddingBottom = '20px'")
        assert sum(1 for v in margins.values() if v <= 0) == VIOLATIONS_WITH_A_LINE_MORE_AT_REST > 0

    def test_both_occupants_of_the_slot_at_once_break_the_premise_while_open(self, browser_page, host) -> None:
        margins = bar_margins(browser_page, host, mode="open", extra="document.querySelector('[data-player-hint]').hidden = false")
        assert sum(1 for v in margins.values() if v <= 0) == VIOLATIONS_WITH_BOTH_OCCUPANTS > 0

    def test_a_sentence_far_longer_than_any_the_page_says_goes_past_the_open_bound(self, browser_page, host) -> None:
        margins = bar_margins(browser_page, host, mode="sentence", extra="document.querySelector('[data-player-hint-say]').textContent += ' x'.repeat(200)")
        assert min(margins.values()) < OPEN_SENTENCE_WORST_MARGIN_PX and any(v <= 0 for v in margins.values())


# ==========================================================================
# AC-11 - the marks coexist, by pixels
# ==========================================================================
#
# The probe's DASHED OUTLINE (the panel's look, decided by the owner 2026-11-06 and NOT altered here) is one
# of four marks that can share a cell or a clue box on this board: the crosshair's tint (``is-crossed``), the
# hint line's tint (``is-hint-line``), the hinted cell's solid ring (``is-hinted``) and a circled clue number's
# ring (a border on the number's ::before). The probe is an OUTLINE and the two tints are BACKGROUNDS, so the
# channels differ; what is held here is the PIXELS: on every ground a probed cell can have, the dashed ring
# stays far enough from the ground to read, and the ring really is drawn in the cell's edge pixels.
#
# DECLARED BOUND (ADR-0039/R3): the least CIE76 distance between the ring colour and the ground under it,
# MEASURED this card in headless Chromium on the 10 x 10 mixed fixture, is RING_DISTANCES_MEASURED below (52.4, a
# filled cell on a lit hint line); the floor is 20, the panel's own (admin.css measured 51.2 .. 71.5 for the same six grounds, "8.7x the JND of 2.3").
# The control that fails just past it is a ring painted in the ground's own colour.

RING_FLOOR = 20
#: ground -> dE76 between the ring and the ground under it, rounded to 0.1: the figures the floor was set from
RING_DISTANCES_MEASURED = {
    "maybe": 58.4,
    "maybe_crossed": 61.9,
    "maybe_lit": 60.3,
    "maybe_lit_crossed": 61.1,
    "filled": 71.5,
    "filled_crossed": 57.6,
    "filled_lit": 52.4,
    "filled_lit_crossed": 54.9,
}


def _linear(channel: float) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (_linear(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116  # noqa: E731
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e76(one: tuple[int, int, int], other: tuple[int, int, int]) -> float:
    return math.dist(lab(one), lab(other))


def _rgb_of(text: str) -> tuple[int, int, int]:
    from tests.test_public_player_circles import _rgb

    return _rgb(text)


_CELL_LOOK = """([row, col]) => {
  const td = document.querySelector(`td.player-cell[data-row="${row}"][data-col="${col}"]`);
  const s = getComputedStyle(td);
  const r = td.getBoundingClientRect();
  return { row, col, ground: s.backgroundColor, ring: s.outlineColor, style: s.outlineStyle, width: s.outlineWidth, shadow: s.boxShadow,
           classes: [...td.classList], marked: td.hasAttribute('data-probe'), state: td.dataset.state,
           box: { x: r.left, y: r.top, w: r.width, h: r.height } };
}"""


def cell_look(page, row: int, col: int) -> dict:
    page.wait_for_function("document.getAnimations().every((a) => a.playState !== 'running')")
    return page.evaluate(_CELL_LOOK, [row, col])


def ring_in_pixels(page, look: dict, *, gaps: bool = True) -> bool:
    """Whether the cell's top edge, as drawn NOW, holds pixels of the ring's colour and, with ``gaps``, of the
    ground too (the dashes and the gaps between them). ``look`` must have been read just before."""
    box, ring, ground = look["box"], _rgb_of(look["ring"]), _rgb_of(look["ground"])
    strip = _pixels(page, box["x"], box["y"], box["w"], 2)
    colours = [strip.getpixel((x, y)) for x in range(strip.width) for y in range(strip.height)]
    seen = any(max(abs(a - b) for a, b in zip(c, ring)) <= 6 for c in colours)
    return seen and (not gaps or any(max(abs(a - b) for a, b in zip(c, ground)) <= 6 for c in colours))


def probe_grounds(page, host, *, probing: bool = True, style: str = "") -> dict[str, dict]:
    """The probed cell on each ground, by REAL events: a maybe cell and a filled cell, each plain, crossed by the
    pointer, on a lit hint line, and both. Returns {name: cell_look}, each with ``ring_seen`` read at once.
    Finds its own cells from the module's hint. ``probing=False`` makes the same marks with NO probe open (the
    control for "the probe changes no ground"); ``style`` is CSS added to the page first (a plant)."""
    out: dict[str, dict] = {}
    grid = FIXTURES["mixed"]
    for state, cells in (("maybe", None), ("filled", [(r, c) for r in range(10) for c in range(10) if grid[r][c]])):
        found = False
        for candidate in cells or [None]:
            fresh(page, host)
            if style:
                page.add_style_tag(content=style)
            if probing:
                page.click(PROBE, force=True)
            want = expected(page)
            if want is None:
                continue
            if candidate is None:  # a maybe mark does not change the deduction: put one ON the hint's line
                axis, index = want["axis"], want["index"]
                spots = [(index, c) for c in range(10)] if axis == "row" else [(r, index) for r in range(10)]
                spot = next(((r, c) for r, c in spots if (r, c) != (want["row"], want["col"])), None)
                tool = "maybe"
            else:
                spot, tool = candidate, "filled"
                mark(page, "filled", *spot)
                want = expected(page)
                if want is None:
                    continue
                on_line = (want["axis"] == "row" and want["index"] == spot[0]) or (want["axis"] == "column" and want["index"] == spot[1])
                if not on_line:
                    continue
            if spot is None:
                continue
            if tool == "maybe":
                mark(page, "maybe", *spot)
                if expected(page) != want:
                    continue
            row, col = spot

            def look(name: str) -> None:
                out[name] = cell_look(page, row, col)
                out[name]["ring_seen"] = ring_in_pixels(page, out[name], gaps=probing)

            _move_away(page)
            look(f"{state}")
            _move(page, row, (col + 1) % 10)
            look(f"{state}_crossed")
            _move_away(page)
            press(page)
            _move_away(page)
            look(f"{state}_lit")
            _move(page, row, (col + 1) % 10)
            look(f"{state}_lit_crossed")
            found = True
            break
        assert found, f"no {state} cell of the fixture can be probed on a lit hint line"
    return out


def ring_distances(grounds: dict[str, dict]) -> dict[str, float]:
    return {name: round(delta_e76(_rgb_of(look["ring"]), _rgb_of(look["ground"])), 1) for name, look in grounds.items()}


@pytest.mark.browser
class TestPublicProbe_TheMarksCoexistByPixels:
    def test_a_probed_cell_keeps_its_dashed_ring_on_every_ground_it_can_have(self, browser_page, host) -> None:
        page = browser_page
        grounds = probe_grounds(page, host)
        assert set(grounds) == set(RING_DISTANCES_MEASURED), sorted(grounds)
        for name, look in grounds.items():
            assert look["marked"] and (look["style"], look["width"]) == ("dashed", "2px"), (name, look)
            if "crossed" in name:
                assert "is-crossed" in look["classes"], (name, look["classes"])
            if "lit" in name:
                assert "is-hint-line" in look["classes"], (name, look["classes"])
            assert look["ring_seen"], f"{name}: the ring is not in the cell's edge pixels"
        distances = ring_distances(grounds)
        assert min(distances.values()) >= RING_FLOOR, distances
        assert distances == RING_DISTANCES_MEASURED, "MEASURED " + json.dumps(distances)

    def test_the_probe_changes_no_ground_so_every_tint_still_shows(self, browser_page, host) -> None:
        """The same real events with NO probe open: every cell's ground is the one it has with the probe open, on each
        of the eight grounds. (The tints' own pairwise distances are CARD-325's and CARD-327's, not held here.)"""
        page = browser_page
        with_probe = probe_grounds(page, host)
        without = probe_grounds(page, host, probing=False)
        assert set(with_probe) == set(without)
        for name in with_probe:
            assert _rgb_of(with_probe[name]["ground"]) == _rgb_of(without[name]["ground"]), name
            assert without[name]["style"] == "none" and not without[name]["marked"], name

    def test_a_ring_painted_in_the_grounds_own_colour_is_caught(self, plant_page, host) -> None:
        page, _ = plant_page
        grounds = probe_grounds(page, host)
        assert min(ring_distances(grounds).values()) >= RING_FLOOR and all(g["ring_seen"] for g in grounds.values()), "the matched control"
        planted = probe_grounds(page, host, style=".player-cell[data-probe], .player-cell[data-probe][data-state] { outline-color: var(--grid-paper) !important; }")
        assert min(ring_distances(planted).values()) < RING_FLOOR
        assert not any(g["ring_seen"] for g in planted.values() if _rgb_of(g["ground"]) == _rgb_of(g["ring"]))

    def test_a_hinted_probed_cell_shows_the_accent_and_the_dash(self, browser_page, host) -> None:
        page = browser_page
        fresh(page, host)
        page.click(PROBE, force=True)
        for _ in range(3):
            press(page)
        _move_away(page)
        s = st(page)
        assert len(s["hinted"]) == 1 and s["marked"] == s["hinted"]
        row, col = divmod(s["hinted"][0], 10)
        look = cell_look(page, row, col)
        accent = page.evaluate("(() => { const i = document.createElement('i'); i.style.color = 'var(--color-accent)'; document.body.append(i); const c = getComputedStyle(i).color; i.remove(); return c; })()")
        assert look["style"] == "dashed" and look["ring"] == accent, look
        assert look["shadow"] != "none", "the hint's paper ring is gone"
        assert ring_in_pixels(page, look, gaps=False), "the hinted cell's ring is not in its edge pixels"

    def test_a_circled_clue_number_keeps_its_ring_while_the_board_is_probed(self, browser_page, host) -> None:
        from tests.test_public_player_circles import _RING, _ring_edge_distances

        page = browser_page
        grid = FIXTURES["mixed"]
        _board(page, host, host[2]["mixed"], grid, _marked(grid, rows=range(3)))
        page.mouse.move(2, 2)
        plain = page.evaluate(_RING, "th.player-clue.is-row[data-line='0']")
        assert plain["found"], "the constructed board has no circled number on row 0"
        without = _ring_edge_distances(page, plain)  # the ring's own anti-aliasing, with no probe: the control
        page.click(PROBE, force=True)
        mark(page, "maybe", 6, 6)
        mark(page, "maybe", 7, 2)
        _move(page, 6, 2)  # the crosshair over the probed board as well
        ring = page.evaluate(_RING, "th.player-clue.is-row[data-line='0']")
        assert ring["found"]
        assert _ring_edge_distances(page, ring) == without, (_ring_edge_distances(page, ring), without)
        assert all(distance <= 45 for distance in without.values()), without
        s = st(page)
        assert s["marked"] == sorted([at(6, 6), at(7, 2)]) and s["markedElsewhere"] == 0, "the marker reached a clue box"
        assert page.evaluate("document.querySelectorAll('th.player-clue.is-crossed').length") == 2


# --------------------------------------------------------------------------
# AC-12 - no answer, and no request
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestPublicProbe_NoAnswerAndNoRequest:
    def test_every_served_puzzle_file_still_carries_exactly_the_five_fields(self, host) -> None:
        puzzles = served_puzzles(host[1].site_dir)
        assert len(puzzles) == len(FIXTURES) and len(puzzles) >= 6
        for key, payload in puzzles.items():
            assert sorted(payload) == PUZZLE_FIELDS, (key, sorted(payload))

    def test_the_only_request_is_the_get_of_its_own_puzzle_file_through_every_interaction(self, browser_page, host) -> None:
        page = browser_page
        seen: list[tuple[str, str]] = []
        page.context.on("request", lambda request: seen.append((request.method, request.url)))
        url, _, keys = host
        key = keys["mixed"]
        _open(page, host, key)
        page.wait_for_timeout(300)
        after_load = len(seen)
        assert any(u.endswith(f"/puzzle/{key}.json") and m == "GET" for m, u in seen), seen
        page.click(PROBE, force=True)
        mark(page, "filled", 1, 1)
        for _ in range(3):
            press(page)
        page.click(UNDO, force=True)
        page.click(REDO, force=True)
        page.click(KEEP, force=True)
        page.click(PROBE, force=True)
        mark(page, "empty", 3, 3)
        page.click(ABANDON, force=True)
        page.click(RESET, force=True)
        reload(page)
        page.wait_for_timeout(300)
        after = seen[after_load:]
        assert [m for m, _ in seen] and all(m == "GET" for m, _ in seen), seen
        served = {p.relative_to(host[1].site_dir).as_posix() for p in host[1].site_dir.rglob("*") if p.is_file()}
        for method, request_url in after:
            path = request_url[len(url) + 1 :]
            assert path in served or request_url == f"{url}/play/{key}", (method, request_url)
        assert page.context.cookies() == []

    def test_no_page_variable_or_stored_value_is_a_solution_grid_after_a_probe(self, browser_page, host) -> None:
        page = browser_page
        for name in ("min", "mixed"):
            grid = FIXTURES[name]
            _board(page, host, host[2][name], grid, _marked(grid, rows=range(2)))
            page.click(PROBE, force=True)
            for _ in range(3):
                press(page)
            for tool, row, col in [("filled", 5, 5), ("maybe", 6, 6)]:
                mark(page, tool, row, col)
            walked = walk_globals(page, grid)
            assert walked["custom"] == ["publicPlayer"], walked["custom"]
            assert walked["hits"] == [], walked["hits"]
            page.click(KEEP, force=True)
            walked = walk_globals(page, grid)
            assert walked["custom"] == ["publicPlayer"] and walked["hits"] == []
            assert page.evaluate("window.publicPlayer.saveKey") in walked["stored"] and all(k.startswith("nonogram-public:") for k in walked["stored"]), walked["stored"]

    def test_the_probe_adds_no_field_to_the_page_object_and_no_word_solution_to_the_script(self) -> None:
        source = PLAY_JS.read_text(encoding="utf-8")
        code, _ = _scan(source)
        assert not re.search(r"\bsolution\b", code)
        assert re.findall(r"\bfetch\(", code) == ["fetch("]
        for forbidden in ("XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "localStorage.setItem"):
            assert forbidden not in code, forbidden
        exposed = re.search(r"window\.publicPlayer = Object\.freeze\(\{(.*?)\n  \}\);", source, re.S)
        assert exposed is not None
        assert sorted(re.findall(r"^\s{4}(\w+)[:,]", exposed.group(1), re.M)) == sorted(
            ["payload", "getBoard", "getHistory", "isSolved", "getTool", "isRegion", "getZoom", "saveKey"]
        ), "the probe exposed something on the page object"
