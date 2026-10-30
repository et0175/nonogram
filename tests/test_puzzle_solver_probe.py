"""CARD-268 — probe mode: hypothesis marks in their own tint, abandoned or
committed as one transaction (FR-044; ADR-0038/R1..R4, R6; CON-021).

What a solver does when probing is make a *group* of marks under one
hypothesis and then either revert them all (a contradiction) or keep them all
(the hypothesis held). So a probe is a TRANSACTION and not a fifth colour:
during one the player marks filled, empty and "?" cells, and the painful part
is the revert. The card's declared semantics make a probe a **checkpoint in
the stroke history** — ``solver_state.js``'s ``{board, done, undone}`` — so
membership is derived from the history and never stored per cell, undo and
redo move it for free, and ``CELL_STATES`` keeps exactly its four members
(G-4: every selector, save and test on this page is keyed on those values).

The pure half (the checkpoint arithmetic, membership, the clamp, the two
transitions and the checkpoint prefix a save is written from) is driven
through ``await import('/static/solver_state.js')`` against a Python oracle
written here from the card's numbered rules — never against the production
function (:func:`_oracle`). Corpora are hand-built with ``random.Random`` and
a fixed seed, with the case count asserted inside the test (no ``hypothesis``:
not in the dependency baseline).

Everything a player can see is driven by REAL input in Chromium — mouse
clicks and drags on cells, clicks on the real buttons — never by dispatching
a synthetic event, and the probe marker is read off the DOM as
``td.player-cell[data-probe]``.

Fixtures (real Chromium refusing loudly when absent, ADR-0038/R8; a loopback
Flask panel over a temp SQLite store) are CARD-160's, imported below. This
file's page isolation is declared in ``tests/test_puzzle_solver_page.py``'s
``PAGE_ISOLATION``, like every other file of the family.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import pytest

from tests.test_puzzle_solver_marking import (
    GRID,
    SIDE,
    E,
    F,
    U,
    _button,
    _cell,
    _drag,
    _is_disabled,
    _states,
    _tool,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _open,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_progress import (
    NAME,
    _error_count,
    _errors_of,
    _solution_cells,
    _is_solved_shown,
    _set,
    _watch_problems,
)

M = "maybe"

_STATIC = Path(__file__).resolve().parent.parent / "src" / "nonogram" / "admin" / "static"


# ==========================================================================
# Driving and reading the probe on the page
# ==========================================================================


def _probe_toggle(page):
    return page.locator("[data-player-probe]")


def _probe(page):
    """Press the Probe toggle once (a real click on a real button)."""
    _probe_toggle(page).click()


def _probe_pressed(page):
    return _probe_toggle(page).get_attribute("aria-pressed")


def _probe_disabled(page):
    return _probe_toggle(page).get_attribute("aria-disabled")


def _keep(page):
    page.locator('[data-player-probe-action="keep"]').click()


def _contradiction(page):
    page.locator('[data-player-probe-action="abandon"]').click()


def _members(page):
    """Every cell carrying the probe marker, as a sorted list of (row, col) —
    read from the DOM, never from the board or from the history."""
    return sorted(
        tuple(cell)
        for cell in page.evaluate(
            """() => [...document.querySelectorAll('td.player-cell[data-probe]')]
                 .map((td) => [Number(td.dataset.row), Number(td.dataset.col)])"""
        )
    )


def _watch_requests(page, live):
    """Every request the page makes to the panel from now on — G-2's other
    half, and the reason this file installs a listener of its own.

    ``TestSolverMarking_NoRequestPerMark`` is the card's NAMED check of
    ADR-0038/R2 and it is not edited (G-7), so it drives the controls that
    existed when it was written and cannot drive the probe's. G-2 says the
    probe is included — "open, mark, commit, abandon make no network
    request" — so each of those four is measured here, in the AC test that
    already performs it, rather than left as a guardrail inherited by
    assertion.
    """
    seen = []
    page.context.on("request", lambda request: seen.append(request.url))
    return seen


def _actions_shown(page):
    return (
        page.locator('[data-player-probe-action="keep"]').is_visible(),
        page.locator('[data-player-probe-action="abandon"]').is_visible(),
        page.locator("#puzzle-player-probe-note").is_visible(),
    )


# ==========================================================================
# AC-9 (first half) — the pure module: the probe is a checkpoint, and the
# four cell states are still four
# ==========================================================================

#: Chromium spells a computed background two ways, and a probed board shows
#: both: ``rgb(...)`` for a plain token and ``color(srgb ...)`` for a
#: ``color-mix()``. Both are read into one 0..1 scale (CARD-267's instrument,
#: reimplemented here rather than imported: this file must not depend on the
#: crosshair's own test module for a measurement of its own tint).
_RGB = re.compile(r"^rgba?\(([^)]*)\)$")
_SRGB = re.compile(r"^color\(srgb ([^)/]*)\)$")


def _luma(value: str) -> float:
    """The mean of a computed colour's three sRGB channels, on 0..1."""
    srgb = _SRGB.match(value)
    if srgb:
        channels = [float(n) for n in srgb.group(1).split()[:3]]
    else:
        plain = _RGB.match(value)
        assert plain, f"unrecognised computed colour: {value!r}"
        channels = [float(n) / 255 for n in plain.group(1).replace("/", " ").split(",")[:3]]
    assert all(0.0 <= channel <= 1.0 for channel in channels), (value, channels)
    return sum(channels) / 3


#: The ops the pure-module driver and :func:`_oracle` both understand. A
#: ``mark`` is one click's stroke (``clickStroke`` always changes its cell, so
#: every mark is one history step); ``undo``/``redo`` are the history's own
#: moves; ``open``/``keep``/``abandon`` are the probe's three controls.
#:
#: Production applies the ``"change"`` event to the probe after EVERY recorded
#: change and nowhere else (``solver.js``'s ``commit``), so the driver does
#: exactly that after a mark, an undo and a redo — the clamp of rule 6 is
#: reached the way the player reaches it, not by calling it directly.
_PROBE_MODULE = """async ({ cases, side }) => {
  const S = await import('/static/solver_state.js');
  const tools = { f: S.FILLED, e: S.EMPTY, u: S.UNKNOWN, m: S.MAYBE };
  const pairs = (cells) => cells.map(([row, col]) => [row, col]);
  const out = [];
  for (const ops of cases) {
    let h = S.createHistory(S.createBoard(side, side));
    let probe = null;
    for (const op of ops) {
      if (op[0] === 'mark') {
        h = S.record(h, S.clickStroke(h.board, op[1], op[2], tools[op[3]], false));
      } else if (op[0] === 'undo') {
        h = S.undo(h);
      } else if (op[0] === 'redo') {
        h = S.redo(h);
      } else if (op[0] === 'open') {
        probe = S.nextProbe(probe, h, 'open');
        continue;
      } else if (op[0] === 'keep') {
        probe = S.nextProbe(probe, h, 'keep');
        continue;
      } else if (op[0] === 'abandon') {
        h = S.abandonProbe(h, probe);
        probe = S.nextProbe(probe, h, 'abandon');
        continue;
      } else {
        throw new Error(`unknown op ${op[0]}`);
      }
      probe = S.nextProbe(probe, h, 'change');
    }
    const prefix = S.checkpointHistory(h, probe);
    const first = prefix.done.length > 0 ? prefix.done[0].before : prefix.board;
    out.push({
      probe,
      members: pairs(S.probeCells(h, probe)),
      done: h.done.length,
      undone: h.undone.length,
      prefixDone: prefix.done.length,
      prefixUndone: prefix.undone.length,
      prefixBlankStart: first.cells.every((state) => state === S.UNKNOWN),
      prefixBoard: [...prefix.board.cells],
      board: [...h.board.cells],
      frozen: Object.isFrozen(S.probeCells(h, probe)),
    });
  }
  return out;
}"""

_PROBE_REFUSALS = """async () => {
  const S = await import('/static/solver_state.js');
  const h = S.createHistory(S.createBoard(3, 3));
  const refused = (event) => {
    try {
      S.nextProbe(null, h, event);
      return 'accepted';
    } catch (error) {
      return error.constructor.name;
    }
  };
  return {
    states: [...S.CELL_STATES],
    events: [...S.PROBE_EVENTS],
    refusals: ['', 'OPEN', 'commit', 'reset', 'solved', 'drag', null, undefined].map(refused),
  };
}"""


def _oracle(ops):
    """The card's numbered rules, implemented here from the card and not from
    ``solver_state.js``: the probe after each op, which cells belong to it,
    and the shape of the history and of the checkpoint prefix a save is
    written from.

    A probe is the number of undo-stack entries at the moment it opened
    (rule 2). Opening while one is open changes nothing (rule 1, depth 1).
    Keep and Abandon close it (rules 5 and 4); Abandon first undoes back to
    the checkpoint, which puts its strokes onto the redo stack like any other
    undos. Any recorded change clamps the checkpoint to the undo stack it
    still has (rule 6), so a probe can shrink to empty, stay open, and own
    the next mark. Members are the cells of the strokes recorded since the
    checkpoint, each once, in the order first marked (rule 3).
    """
    done: list[tuple[int, int]] = []   # one cell per mark — a click's stroke
    undone: list[tuple[int, int]] = []
    probe: int | None = None
    for op in ops:
        if op[0] == "mark":
            done.append((op[1], op[2]))
            undone = []
        elif op[0] == "undo":
            if done:
                undone.append(done.pop())
        elif op[0] == "redo":
            if undone:
                done.append(undone.pop())
        elif op[0] == "open":
            if probe is None:
                probe = len(done)
            continue
        elif op[0] == "keep":
            probe = None
            continue
        elif op[0] == "abandon":
            if probe is not None:
                while len(done) > probe:
                    undone.append(done.pop())
                probe = None
            continue
        else:
            raise AssertionError(f"unknown op {op[0]}")
        if probe is not None:
            probe = min(probe, len(done))
    members: list[tuple[int, int]] = []
    for cell in (done[probe:] if probe is not None else []):
        if cell not in members:
            members.append(cell)
    prefix_done = len(done) if probe is None else min(probe, len(done))
    prefix_undone = len(undone) if probe is None else 0
    return {
        "probe": probe,
        "members": members,
        "done": len(done),
        "undone": len(undone),
        "prefixDone": prefix_done,
        "prefixUndone": prefix_undone,
    }


#: The explicit cases: one per numbered rule the pure half carries, so a
#: failure names the rule rather than a seed.
_RULE_CASES = {
    "2 — a probe opens at the current position": [
        ("mark", 0, 0, "f"), ("mark", 0, 1, "f"), ("open",), ("mark", 1, 1, "f"),
    ],
    "1 — a second open changes nothing (depth 1)": [
        ("mark", 0, 0, "f"), ("open",), ("mark", 1, 0, "f"), ("open",), ("mark", 1, 1, "f"),
    ],
    "3 — every brush's mark belongs to the probe": [
        ("open",), ("mark", 0, 0, "f"), ("mark", 0, 1, "e"), ("mark", 0, 2, "m"),
        ("mark", 0, 3, "u"),
    ],
    "3 — a cell marked twice is one member": [
        ("open",), ("mark", 0, 0, "f"), ("mark", 0, 0, "e"), ("mark", 1, 1, "f"),
    ],
    "4 — abandon undoes back to the checkpoint": [
        ("mark", 0, 0, "f"), ("mark", 0, 1, "f"), ("open",),
        ("mark", 2, 2, "f"), ("mark", 2, 3, "e"), ("abandon",),
    ],
    "4 — a stroke redone after an abandon is a normal stroke": [
        ("mark", 0, 0, "f"), ("open",), ("mark", 2, 2, "f"), ("abandon",), ("redo",),
    ],
    "5 — keep closes the probe and touches no cell": [
        ("open",), ("mark", 0, 0, "f"), ("mark", 1, 1, "e"), ("keep",),
    ],
    "6 — undo pops probe strokes first": [
        ("mark", 0, 0, "f"), ("open",), ("mark", 1, 1, "f"), ("mark", 2, 2, "f"), ("undo",),
    ],
    "6 — undoing past the checkpoint clamps it and stays open": [
        ("mark", 0, 0, "f"), ("mark", 0, 1, "f"), ("open",), ("mark", 1, 1, "f"),
        ("undo",), ("undo",), ("undo",),
    ],
    "6 — the next mark after a clamp belongs to the probe": [
        ("mark", 0, 0, "f"), ("open",), ("undo",), ("mark", 3, 3, "f"),
    ],
    "6 — a probe can shrink to empty and still be open": [
        ("open",), ("mark", 0, 0, "f"), ("undo",),
    ],
    "9 — an open probe's save is the checkpoint prefix": [
        ("mark", 0, 0, "f"), ("mark", 0, 1, "f"), ("open",),
        ("mark", 2, 2, "f"), ("mark", 2, 3, "f"),
    ],
    "9 — a closed probe saves the whole history, redo stack and all": [
        ("mark", 0, 0, "f"), ("mark", 0, 1, "f"), ("undo",),
    ],
}

_SIDE = 4
_TOOLS = ("f", "e", "m", "u")
_CORPUS_CASES = 300


def _corpus(rng):
    """Random op sequences over a 4 x 4 board: marks with every brush,
    undo/redo, and the probe's three controls, in any order."""
    cases = []
    for _ in range(_CORPUS_CASES):
        ops = []
        for _ in range(rng.randint(1, 14)):
            kind = rng.choices(
                ["mark", "undo", "redo", "open", "keep", "abandon"],
                weights=[8, 3, 2, 3, 1, 1],
            )[0]
            if kind == "mark":
                ops.append(("mark", rng.randrange(_SIDE), rng.randrange(_SIDE),
                            rng.choice(_TOOLS)))
            else:
                ops.append((kind,))
        cases.append(ops)
    return cases


@pytest.mark.browser
class TestSolverProbe_StateIsPureAndStatesAreFour:
    """AC-9 (first half) / rule 11 — the probe's whole value is one number in
    the pure module, and ``CELL_STATES`` is untouched.

    Five arms, measured one at a time because a test short-circuits at its
    first failing assert:

    1. every numbered rule the pure half carries, as a named case, against
       :func:`_oracle`;
    2. a seeded corpus of 300 random op sequences against the same oracle —
       the probe value, the member cells, the history's two stack sizes and
       the checkpoint prefix's;
    3. the prefix a save is written from always starts blank (``serializeState``
       refuses a history that does not) and never holds a stroke made after
       the checkpoint;
    4. ``CELL_STATES`` is exactly today's four members, in today's order, and
       an unknown probe event is a ``RangeError`` rather than a quiet "leave
       it as it was" (``nextRegion``'s and ``stepZoom``'s discipline);
    5. the module reaches no DOM: the probe's names are exported from
       ``solver_state.js`` and the marker attribute is written only in
       ``solver.js``.
    """

    def test_the_named_rule_cases_match_the_oracle(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        names = list(_RULE_CASES)
        got = browser_page.evaluate(
            _PROBE_MODULE,
            {"cases": [[list(op) for op in _RULE_CASES[name]] for name in names],
             "side": _SIDE},
        )
        assert len(got) == len(names) == 13
        wrong = []
        for name, seen in zip(names, got):
            want = _oracle(_RULE_CASES[name])
            reading = {key: seen[key] for key in want}
            reading["members"] = [tuple(cell) for cell in reading["members"]]
            if reading != want:
                wrong.append((name, want, reading))
        assert wrong == [], wrong

    def test_a_seeded_corpus_matches_the_oracle(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cases = _corpus(random.Random(268))
        got = browser_page.evaluate(
            _PROBE_MODULE,
            {"cases": [[list(op) for op in ops] for ops in cases], "side": _SIDE},
        )
        assert len(got) == len(cases) == _CORPUS_CASES >= 300
        wrong = []
        for ops, seen in zip(cases, got):
            want = _oracle(ops)
            reading = {key: seen[key] for key in want}
            reading["members"] = [tuple(cell) for cell in reading["members"]]
            if reading != want:
                wrong.append((ops, want, reading))
        assert wrong == [], wrong[:3]
        # The corpus really does reach every state worth reaching, or the
        # equality above is an agreement about nothing.
        opened = [seen for seen in got if seen["probe"] is not None]
        assert len([seen for seen in opened if seen["members"]]) >= 60, len(opened)
        assert len([seen for seen in opened if not seen["members"]]) >= 10
        assert len([seen for seen in got if seen["probe"] is None]) >= 60
        assert all(seen["frozen"] for seen in got)

    def test_the_checkpoint_prefix_is_a_savable_history(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        cases = _corpus(random.Random(2680))
        got = browser_page.evaluate(
            _PROBE_MODULE,
            {"cases": [[list(op) for op in ops] for ops in cases], "side": _SIDE},
        )
        assert len(got) == _CORPUS_CASES
        # serializeState refuses a history that does not start from a blank
        # board, so a prefix that did would silently stop saving (CARD-185).
        assert [seen["prefixBlankStart"] for seen in got] == [True] * _CORPUS_CASES
        # And the prefix board is the board as of the checkpoint: no cell a
        # probe stroke touched can differ from it, because those strokes are
        # not in the prefix. Read as "the prefix equals the current board
        # exactly where the probe owns nothing".
        for ops, seen in zip(cases, got):
            want = _oracle(ops)
            if want["probe"] is None:
                assert seen["prefixBoard"] == seen["board"], ops
            else:
                members = {row * _SIDE + col for row, col in want["members"]}
                differ = {index for index, state in enumerate(seen["board"])
                          if state != seen["prefixBoard"][index]}
                assert differ <= members, (ops, sorted(differ), sorted(members))

    def test_the_cell_states_are_four_and_an_unknown_event_is_refused(
        self, browser_page, live
    ) -> None:
        _open(browser_page, live, live.store(GRID))
        seen = browser_page.evaluate(_PROBE_REFUSALS)
        assert seen["states"] == [U, F, E, M]
        assert seen["events"] == ["open", "keep", "abandon", "change"]
        assert seen["refusals"] == ["RangeError"] * 8, seen["refusals"]

    def test_the_probe_is_pure_and_only_the_renderer_knows_the_attribute(self) -> None:
        state = (_STATIC / "solver_state.js").read_text(encoding="utf-8")
        renderer = (_STATIC / "solver.js").read_text(encoding="utf-8")

        for name in ("nextProbe", "probeCells", "abandonProbe", "checkpointHistory",
                     "PROBE_EVENTS"):
            assert f"export function {name}" in state or f"export const {name}" in state, name

        # ADR-0038/R4: the pure module reaches nothing outside its arguments.
        # Read over the CODE lines only — the file explains at length why the
        # DOM is not in it, and a sweep of its prose would fire on the
        # sentences that state the rule.
        code = re.sub(r"//[^\n]*", "", state)
        for name in ("document", "window", "dataset", "classList", "querySelector"):
            assert name not in code, name

        # The marker is rendering, so only the renderer writes it.
        assert "dataset.probe" in renderer
        assert "data-probe" not in state and "dataset.probe" not in state


# ==========================================================================
# AC-1 — a mark made while a probe is open keeps its state and wears the
# probe marker; a mark made before the probe wears none
# ==========================================================================

#: One cell's whole look, as the shipped CSS actually draws it: the ground,
#: the ``::after`` mark's content and the two paints a mark can use.
_LOOK = """(cells) => Object.fromEntries(Object.entries(cells).map(([name, [row, col]]) => {
  const cell = document.querySelector(
    `td.player-cell[data-row="${row}"][data-col="${col}"]`);
  const after = getComputedStyle(cell, '::after');
  return [name, { state: cell.dataset.state,
                  probe: cell.getAttribute('data-probe'),
                  crossed: cell.classList.contains('is-crossed'),
                  lined: cell.classList.contains('is-hint-line'),
                  background: getComputedStyle(cell).backgroundColor,
                  mark: after.content,
                  markGround: after.backgroundColor,
                  markInk: after.color }];
}))"""


def _hover(page, row, col):
    box = _cell(page, row, col).bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def _look(page, cells):
    return page.evaluate(_LOOK, cells)


def _click_times(page, row, col, times):
    for _ in range(times):
        _cell(page, row, col).click()


@pytest.mark.browser
class TestSolverProbe_MarksCarryTheTint:
    """AC-1 / rules 2, 3 — the marker rides a separate attribute, the four
    looks stay apart under the tint, and the tint beats the two tints it can
    share a cell with.

    Four arms, measured one at a time (a test short-circuits at its first
    failing assert, so one FAILED line would say nothing about the arms that
    never ran):

    1. a cell marked BEFORE the probe carries no marker, and the probe's own
       cells carry one — the member set read off the DOM is exactly the cells
       marked since the probe opened, whichever brush made them, and every
       one of them keeps the ``data-state`` it would have had anyway (G-4);
    2. all four ``data-state`` looks stay plainly apart under the tint, in
       pixels and not by eye: the three light states share the tinted ground
       and are told apart by their own ``::after`` channel (nothing, the white
       dot's background, the "?"'s colour), and ``filled`` by its ground's
       luma — CARD-267's instrument for the same claim about its own tint;
    3. the crosshair (CARD-267) does not repaint a probe cell: a cell that is
       both probed and crossed reads exactly as a probed cell that is not
       crossed, and not as a crossed cell that is not probed;
    4. nor does the hint ladder's line (CARD-269). That arm is a claim about
       the STYLESHEET's order and not about input, so the competing class is
       put on by script and only computed styles are read; arm 3's crosshair
       is driven by a real pointer, because there it is the pointer that
       decides.
    """

    def test_the_probes_marks_carry_the_marker_and_earlier_marks_do_not(
        self, browser_page, live
    ) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        requests = _watch_requests(browser_page, live)

        # Before the probe: two strokes, one click and one drag.
        _cell(browser_page, 0, 0).click()
        _drag(browser_page, [(1, 0), (1, 3)])
        before = _states(browser_page)
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"
        assert _actions_shown(browser_page) == (False, False, False)

        _probe(browser_page)
        assert _probe_pressed(browser_page) == "true"
        assert _actions_shown(browser_page) == (True, True, True)

        # Every brush, plus a drag, while the probe is open.
        _cell(browser_page, 6, 0).click()                     # Black
        _tool(browser_page, "White")
        _cell(browser_page, 6, 1).click()                     # White
        _tool(browser_page, "Maybe")
        _cell(browser_page, 6, 2).click()
        _tool(browser_page, "Black")
        _click_times(browser_page, 6, 3, 3)                   # black, white, blank
        _drag(browser_page, [(7, 4), (7, 6)])

        marked = _states(browser_page)
        assert _members(browser_page) == sorted(
            [(6, 0), (6, 1), (6, 2), (6, 3), (7, 4), (7, 5), (7, 6)]
        )
        # G-4: the states are the ones those same marks give without a probe.
        assert {(6, c): marked[6 * SIDE + c] for c in range(4)} == {
            (6, 0): F, (6, 1): E, (6, 2): M, (6, 3): U,
        }
        assert [marked[7 * SIDE + c] for c in (4, 5, 6)] == [F, F, F]
        # And the pre-probe marks are untouched, state and marker both.
        assert marked[0:2 * SIDE] == before[0:2 * SIDE]
        # G-2 for two of its four: opening a probe and marking inside one.
        assert requests == []
        assert problems == []

    def test_the_four_states_stay_apart_under_the_tint(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _probe(browser_page)
        _cell(browser_page, 6, 0).click()                     # filled
        _tool(browser_page, "White")
        _cell(browser_page, 6, 1).click()                     # empty
        _tool(browser_page, "Maybe")
        _cell(browser_page, 6, 2).click()                     # maybe
        _tool(browser_page, "Black")
        _click_times(browser_page, 6, 3, 3)                   # undecided, still a member

        look = _look(browser_page, {F: [6, 0], E: [6, 1], M: [6, 2], U: [6, 3]})
        assert [look[state]["state"] for state in (F, E, M, U)] == [F, E, M, U]
        assert all(look[state]["probe"] is not None for state in look), look
        # The three light states: told apart by their mark, under one ground.
        marks = {state: look[state]["mark"] for state in (U, E, M)}
        assert len(set(marks.values())) == 3, marks
        luma = {state: _luma(look[state]["background"]) for state in look}
        assert len({round(luma[state], 4) for state in (U, E, M)}) == 1, luma
        # Each mark that has a paint of its own is apart from the tint it sits
        # on, in pixels and through the channel that paints it.
        for state, colour in {E: look[E]["markGround"], M: look[M]["markInk"]}.items():
            assert abs(_luma(colour) - luma[state]) > 0.2, (state, colour, luma[state])
        # And filled by its ground, by a margin and not a rounding error.
        assert min(luma[s] for s in (U, E, M)) - luma[F] > 0.4, luma

    def test_the_crosshair_does_not_repaint_a_probe_cell(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        _probe(browser_page)
        _cell(browser_page, 6, 0).click()                     # filled, will be crossed
        _cell(browser_page, 8, 8).click()                     # filled, not crossed
        _click_times(browser_page, 6, 3, 3)                   # undecided, will be crossed
        _click_times(browser_page, 8, 9, 3)                   # undecided, not crossed

        _hover(browser_page, 6, 11)
        look = _look(browser_page, {
            "crossed_filled": [6, 0], "probe_filled": [8, 8],
            "crossed_blank": [6, 3], "probe_blank": [8, 9],
            "crossed_only": [6, 12],
        })
        assert look["crossed_filled"]["crossed"] and look["crossed_blank"]["crossed"]
        assert not look["probe_filled"]["crossed"] and not look["probe_blank"]["crossed"]
        assert look["crossed_only"]["crossed"]
        assert look["crossed_only"]["probe"] is None
        # The probe tint wins: a probed cell reads the same crossed or not.
        assert look["crossed_filled"]["background"] == look["probe_filled"]["background"]
        assert look["crossed_blank"]["background"] == look["probe_blank"]["background"]
        # And it is not the crosshair's own ground that it reads.
        assert look["crossed_blank"]["background"] != look["crossed_only"]["background"]

    def test_the_hint_lines_tint_does_not_repaint_a_probe_cell(
        self, browser_page, live
    ) -> None:
        _open(browser_page, live, live.store(GRID))
        _probe(browser_page)
        _cell(browser_page, 6, 0).click()
        _cell(browser_page, 8, 8).click()
        _click_times(browser_page, 6, 3, 3)
        _click_times(browser_page, 8, 9, 3)
        # A stylesheet-order claim, so the class is put on by script: which of
        # two rules of equal specificity wins is decided by this file's order
        # and by nothing a pointer or a button does.
        browser_page.evaluate(
            """() => document.querySelectorAll('td.player-cell[data-row="6"]')
                 .forEach((td) => td.classList.add('is-hint-line'))"""
        )
        browser_page.evaluate("Promise.all(document.getAnimations().map((a) => a.finished))")

        look = _look(browser_page, {
            "lined_filled": [6, 0], "probe_filled": [8, 8],
            "lined_blank": [6, 3], "probe_blank": [8, 9],
            "lined_only": [6, 12],
        })
        assert look["lined_filled"]["lined"] and look["lined_blank"]["lined"]
        assert look["lined_only"]["lined"] and look["lined_only"]["probe"] is None
        assert look["lined_filled"]["background"] == look["probe_filled"]["background"]
        assert look["lined_blank"]["background"] == look["probe_blank"]["background"]
        assert look["lined_blank"]["background"] != look["lined_only"]["background"]


# ==========================================================================
# AC-2 — Abandon restores the board the probe opened on, exactly
# ==========================================================================


@pytest.mark.browser
class TestSolverProbe_AbandonRestoresTheCheckpointBoard:
    """AC-2 / rule 4 — one action undoes the whole hypothesis.

    Two arms. The first is the card's own: a board B, a probe of four strokes
    made with three brushes and two drags over it, and one press of
    Contradiction — after which the board is B cell for cell, the probe is
    closed, no marker remains and the toggle can open a probe again.

    The second is the edge rule 4's parenthetical decides by reference to the
    existing history rules, and it is NOT ambiguous once membership is read
    off the open probe alone: an abandon is a run of undos, so the probe's
    strokes sit on the redo stack like any other undos, and redoing one past
    a CLOSED probe's old checkpoint brings back a normal stroke with no
    marker. Closing a probe forgets it, which is what makes that true by
    construction rather than by a rule of its own.
    """

    def test_abandon_restores_the_board_and_closes_the_probe(
        self, browser_page, live
    ) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        requests = _watch_requests(browser_page, live)
        _cell(browser_page, 0, 0).click()
        _drag(browser_page, [(1, 0), (1, 3)])
        _tool(browser_page, "White")
        _cell(browser_page, 2, 2).click()
        checkpoint = _states(browser_page)

        _probe(browser_page)
        _tool(browser_page, "Black")
        _drag(browser_page, [(5, 0), (5, 4)])
        _tool(browser_page, "Maybe")
        _cell(browser_page, 6, 6).click()
        _tool(browser_page, "White")
        _cell(browser_page, 7, 7).click()
        _tool(browser_page, "Black")
        _drag(browser_page, [(8, 0), (8, 2)])
        assert _members(browser_page) == sorted(
            [(5, c) for c in range(5)] + [(6, 6), (7, 7)] + [(8, c) for c in range(3)]
        )
        assert _states(browser_page) != checkpoint

        _contradiction(browser_page)

        assert _states(browser_page) == checkpoint
        assert _probe_pressed(browser_page) == "false"
        assert _probe_disabled(browser_page) == "false"
        assert _members(browser_page) == []
        assert _actions_shown(browser_page) == (False, False, False)
        assert requests == []  # G-2: abandoning a probe asks for nothing
        assert problems == []

    def test_a_stroke_redone_after_an_abandon_is_a_normal_stroke(
        self, browser_page, live
    ) -> None:
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 0, 0).click()
        checkpoint = _states(browser_page)
        _probe(browser_page)
        _cell(browser_page, 5, 5).click()
        first = _states(browser_page)
        _cell(browser_page, 6, 6).click()
        second = _states(browser_page)

        _contradiction(browser_page)
        assert _states(browser_page) == checkpoint
        assert not _is_disabled(browser_page, "Redo")

        _button(browser_page, "Redo").click()
        assert _states(browser_page) == first
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"
        _button(browser_page, "Redo").click()
        assert _states(browser_page) == second
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"


# ==========================================================================
# AC-3 — Keep drops the tint and touches no cell
# ==========================================================================


@pytest.mark.browser
class TestSolverProbe_CommitKeepsCellsAndDropsTheTint:
    """AC-3 / rule 5 — commit is a change of STATUS, not of cells.

    Four claims, each measured: every cell's ``data-state`` is what it was
    before the press, every marker is gone, the probe is closed (and the
    toggle can open another), and the history is untouched — the undo stack
    still holds each probe stroke as its own step, so one Undo after a Keep
    takes back the last kept mark and nothing else.
    """

    def test_keep_keeps_every_cell_and_drops_every_marker(
        self, browser_page, live
    ) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        browser_page.wait_for_load_state("networkidle")
        requests = _watch_requests(browser_page, live)
        _cell(browser_page, 0, 0).click()

        _probe(browser_page)
        _drag(browser_page, [(5, 0), (5, 4)])
        _tool(browser_page, "Maybe")
        _cell(browser_page, 6, 6).click()
        _tool(browser_page, "Black")
        before_last = _states(browser_page)
        _cell(browser_page, 7, 7).click()
        kept = _states(browser_page)
        assert _members(browser_page) == sorted(
            [(5, c) for c in range(5)] + [(6, 6), (7, 7)]
        )

        _keep(browser_page)

        assert _states(browser_page) == kept
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"
        assert _probe_disabled(browser_page) == "false"
        assert _actions_shown(browser_page) == (False, False, False)
        # The history is intact: the last kept mark is still one undo step.
        _button(browser_page, "Undo").click()
        assert _states(browser_page) == before_last
        assert _members(browser_page) == []
        assert requests == []  # G-2: committing a probe asks for nothing
        assert problems == []

    def test_keep_makes_the_probes_marks_savable_again(self, browser_page, live) -> None:
        """Rule 9's other end, and the arm a mutant found missing: while a
        probe is open the save is the CHECKPOINT prefix, so the moment it
        closes the whole history has to be written again or the kept marks
        would not survive a reload.

        Driven through a real reload rather than by reading the entry, because
        "the save is right" is only interesting as "the board comes back".
        (Measured: the mutant that stops ``probed()`` writing leaves every
        other test of this card green and reds this one.)
        """
        puzzle_id = live.store(GRID)
        _open(browser_page, live, puzzle_id)
        _cell(browser_page, 0, 0).click()

        _probe(browser_page)
        _drag(browser_page, [(5, 0), (5, 4)])
        _cell(browser_page, 7, 7).click()
        kept = _states(browser_page)
        _keep(browser_page)
        assert _states(browser_page) == kept

        browser_page.reload()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert _states(browser_page) == kept
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"

    def test_a_reset_clears_the_open_probe(self, browser_page, live) -> None:
        """Rule 10, and the second arm a mutant found missing: a reset clears
        any open probe.

        The board the hypothesis was about is gone, so the probe has nothing
        left to be about — and a reset stroke left INSIDE the probe would make
        Contradiction un-reset the board, which is the one thing a player who
        has just confirmed a reset cannot have asked for. The history is
        exactly today's: the reset is one undoable step (the confirmation says
        "Undo brings them back"), and undoing it does not reopen the probe.
        (Measured: the mutant that drops the close leaves the probe pressed
        and makes every cell of the board a member.)
        """
        _open(browser_page, live, live.store(GRID))
        _probe(browser_page)
        _drag(browser_page, [(5, 0), (5, 4)])
        before_reset = _states(browser_page)
        assert _members(browser_page) != []

        _button(browser_page, "Reset").click()
        _button(browser_page, "Reset board").click()

        assert set(_states(browser_page)) == {U}
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"
        assert _actions_shown(browser_page) == (False, False, False)
        # Today's history: the reset is one undo step, and undoing it brings
        # the marks back as ordinary marks, not as a reopened probe.
        _button(browser_page, "Undo").click()
        assert _states(browser_page) == before_reset
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"


# ==========================================================================
# AC-4 — undo during a probe: probe strokes pop first, then the clamp
# ==========================================================================


@pytest.mark.browser
class TestSolverProbe_UndoClampsTheCheckpoint:
    """AC-4 / rule 6 — undo/redo work exactly as today, and the checkpoint
    clamps rather than adopting strokes made before the probe.

    Three arms in one walk, in the order the rule states them: probe strokes
    pop first and their markers clear with them; a probe undone to nothing
    stays OPEN (its toggle still pressed, its two actions still offered); and
    an undo PAST the checkpoint takes back a pre-probe stroke without making
    it a member — after which the next mark belongs to the probe again.
    """

    def test_undo_pops_probe_strokes_first_then_clamps(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 0, 0).click()
        _cell(browser_page, 1, 1).click()
        checkpoint = _states(browser_page)

        _probe(browser_page)
        _cell(browser_page, 5, 5).click()
        _cell(browser_page, 6, 6).click()
        _cell(browser_page, 7, 7).click()
        assert _members(browser_page) == [(5, 5), (6, 6), (7, 7)]

        _button(browser_page, "Undo").click()
        assert _members(browser_page) == [(5, 5), (6, 6)]
        assert _states(browser_page)[7 * SIDE + 7] == U
        _button(browser_page, "Undo").click()
        assert _members(browser_page) == [(5, 5)]
        _button(browser_page, "Undo").click()
        # Empty and still open — the probe never closes itself (rule 6).
        assert _members(browser_page) == []
        assert _states(browser_page) == checkpoint
        assert _probe_pressed(browser_page) == "true"
        assert _actions_shown(browser_page) == (True, True, True)

        # Past the checkpoint: a pre-probe stroke comes back, and it is NOT
        # adopted by the probe — the checkpoint clamps instead.
        _button(browser_page, "Undo").click()
        assert _states(browser_page)[1 * SIDE + 1] == U
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "true"

        # And the next mark belongs to the clamped probe.
        _cell(browser_page, 9, 9).click()
        assert _members(browser_page) == [(9, 9)]
        assert _states(browser_page)[0] == F  # the first pre-probe mark, a member of nothing
        assert problems == []


# ==========================================================================
# AC-5 — depth 1: the control cannot open a second probe
# ==========================================================================


@pytest.mark.browser
class TestSolverProbe_OnlyOneProbeAtATime:
    """AC-5 / rule 1 — at most one probe is open, and the toggle SAYS so.

    Of the two answers the card offers, this is the "disabled" one: while a
    probe is open the toggle carries ``aria-disabled="true"`` (the discipline
    every other control on this page already follows — Undo, Redo, Reset,
    Hint and Check all stay focusable and say they have nothing to do) while
    keeping ``aria-pressed="true"``, which is what carries the probe's state
    to a screen reader.

    Three arms, because "nothing happened" is the easiest thing to assert
    vacuously: the attribute says disabled, the pressed state does not move,
    and — the one that actually proves depth 1 — the CHECKPOINT did not move,
    read by abandoning afterwards and finding the board the FIRST probe opened
    on rather than the board the second press would have checkpointed.
    """

    def test_a_second_press_opens_nothing(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))
        _cell(browser_page, 0, 0).click()
        checkpoint = _states(browser_page)

        _probe(browser_page)
        _cell(browser_page, 5, 5).click()
        _cell(browser_page, 6, 6).click()
        members = _members(browser_page)
        assert members == [(5, 5), (6, 6)]
        assert _probe_disabled(browser_page) == "true"
        assert _probe_pressed(browser_page) == "true"

        # A REAL press that the page refuses, not a press the test skipped.
        # Playwright reads aria-disabled as "not enabled" and would wait for
        # the attribute to go away, so the click is forced — it still goes to
        # the element's centre as a browser click, which is exactly what a
        # player clicking the control gets (aria-disabled, unlike `disabled`,
        # does not stop the browser dispatching one). The same `force=True`
        # tests/test_puzzle_solver_zoom.py uses on a clamped zoom button.
        _probe_toggle(browser_page).click(force=True)

        assert _probe_pressed(browser_page) == "true"
        assert _probe_disabled(browser_page) == "true"
        assert _members(browser_page) == members
        assert _actions_shown(browser_page) == (True, True, True)

        # The checkpoint is still the FIRST one: abandoning reaches the board
        # before (5, 5), not the board the second press would have kept.
        _contradiction(browser_page)
        assert _states(browser_page) == checkpoint
        assert problems == []


# ==========================================================================
# AC-7 — a probe that solves the puzzle commits itself
# ==========================================================================


def _two_short(grid):
    """The solution with its last two filled cells left undecided."""
    cells = _solution_cells(grid, E)
    missing = [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c]][-2:]
    for row, col in missing:
        cells[row * len(grid[0]) + col] = U
    return cells, missing


@pytest.mark.browser
class TestSolverProbe_SolvingCommitsTheProbe:
    """AC-7 / rule 7 — ``isSolved`` compares against the solution, so a probe
    that reached the solved state was a correct hypothesis: it commits, and
    the banner and the lock behave exactly as today.

    The board is set two cells short of the solution, so the probe's FIRST
    mark is visibly a member (otherwise "no marker remains" would be a claim
    about a probe that never showed one) and its second solves the puzzle.
    """

    def test_the_solving_mark_commits_the_probe(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID, name=NAME))
        cells, missing = _two_short(GRID)
        _set(browser_page, cells)
        assert not _is_solved_shown(browser_page)

        _probe(browser_page)
        assert _probe_pressed(browser_page) == "true"
        _cell(browser_page, *missing[0]).click()
        assert _members(browser_page) == [missing[0]]
        assert not _is_solved_shown(browser_page)

        _cell(browser_page, *missing[1]).click()

        assert _is_solved_shown(browser_page)
        assert _members(browser_page) == []
        assert _probe_pressed(browser_page) == "false"
        assert _actions_shown(browser_page) == (False, False, False)
        # Exactly today's solved state, lock included; and the toggle says it
        # has nothing to offer on a locked board.
        assert _is_disabled(browser_page, "Undo") and _is_disabled(browser_page, "Redo")
        assert _probe_disabled(browser_page) == "true"
        assert NAME in browser_page.locator("#puzzle-player-announce").text_content()
        assert browser_page.evaluate(
            "document.querySelector('.player-board').classList.contains('is-solved')")
        assert problems == []


# ==========================================================================
# AC-8 — the counters read a probe mark as a mark
# ==========================================================================


def _progress(page):
    return page.locator("[data-player-progress]").text_content()


_CIRCLED = """() => [...document.querySelectorAll('th.player-clue')].flatMap((box) => {
  const kind = box.classList.contains('is-row') ? 'row' : 'col';
  return [...box.querySelectorAll('.player-clue-num')]
    .map((num, index) => [kind, box.dataset.line, index, num.classList.contains('is-circled')])
    .filter(([, , , circled]) => circled)
    .map(([k, line, index]) => `${k}:${line}:${index}`);
}).sort()"""


def _counters(page):
    return (_error_count(page), _progress(page), page.evaluate(_CIRCLED))


#: The one row of GRID that is filled end to end, so dragging the whole of it
#: Black leaves ONE closed run as long as the line and the clue is circled.
#: Found here rather than written down, so the marks below cannot quietly stop
#: circling anything if the grid's seed ever changes.
_A_FULL_ROW = next(r for r in range(SIDE) if all(GRID[r]))


def _the_same_marks(page):
    """One fixed run of real input, chosen so all three readings move: the
    whole of :data:`_A_FULL_ROW` dragged Black (which CIRCLES that row's
    clue), a wrong Black click on a solution-empty cell and a wrong White
    click on a solution-filled one (two errors), and a "?" (never an error,
    never a circle)."""
    _tool(page, "Black")
    _drag(page, [(_A_FULL_ROW, 0), (_A_FULL_ROW, SIDE - 1)])
    _cell(page, *_A_SOLUTION_EMPTY).click()
    _tool(page, "White")
    _cell(page, *_A_SOLUTION_FILLED).click()
    _tool(page, "Maybe")
    _cell(page, 11, 11).click()


_A_SOLUTION_EMPTY = next((r, c) for r in range(SIDE) for c in range(SIDE) if not GRID[r][c])
_A_SOLUTION_FILLED = next((r, c) for r in range(SIDE) for c in range(SIDE) if GRID[r][c])


@pytest.mark.browser
class TestSolverProbe_CountersSeeProbeMarksAsMarks:
    """AC-8 / rule 8 — the error count, Progress % and the clue circles read
    the board as it IS, probe marks included, so no shipped AC-3xx is amended.

    The same run of real input is made twice on the same page — once with no
    probe open, once inside a probe — and the three readings are compared
    against each other. The error count is also compared against
    :func:`_errors_of`, the independent Python definition CARD-162's own tests
    use, so the equality is not two runs agreeing about a wrong number.
    """

    def test_the_same_marks_read_the_same_inside_a_probe(
        self, browser_page, live
    ) -> None:
        problems = _watch_problems(browser_page, live)
        _open(browser_page, live, live.store(GRID))

        _the_same_marks(browser_page)
        plain = _counters(browser_page)
        plain_board = _states(browser_page)
        assert _members(browser_page) == []
        # The count is the independent Python definition's, and it is not
        # zero — an equality between two readings of nothing would be vacuous.
        assert plain[0] == _errors_of(plain_board, GRID)
        assert plain[0] >= 2, plain
        assert plain[2], "these marks circle no clue number, so the third arm is vacuous"

        _button(browser_page, "Reset").click()
        _button(browser_page, "Reset board").click()
        assert set(_states(browser_page)) == {U}

        _probe(browser_page)
        _the_same_marks(browser_page)
        probed = _counters(browser_page)
        probed_board = _states(browser_page)
        assert _members(browser_page) != []

        assert probed_board == plain_board
        assert probed == plain
        assert probed[0] == _errors_of(probed_board, GRID)
        assert problems == []


# ==========================================================================
# The probe bar's own geometry — the fix round's control
# ==========================================================================


#: Where the bar sits against the board, in viewport px, plus the one
#: derived number the claim below is about.
#:
#: ``capture`` is the first whole pixel row a Playwright ELEMENT screenshot of
#: ``.player-board`` is taken from: such a capture clips the page raster to
#: the ENCLOSING whole-pixel rect, ``[floor(top), ceil(bottom))``, so a board
#: whose top is at ``y.797`` is captured from ``y.0`` and its first row holds
#: 0.797 px of whatever is directly above the board.
#:
#: ``barBottom`` is the bar's own border-box bottom rather than its children's
#: — it encloses them (no child carries a negative margin), so it is the
#: stricter of the two and it does not change when the bar wraps.
_BAR_AGAINST_BOARD = """() => {
  const bar = document.querySelector('.player-probe');
  const board = document.querySelector('.player-board');
  const tools = document.querySelector('.player-tools');
  const boardTop = board.getBoundingClientRect().top;
  return {
    hidden: bar.hidden,
    barTop: bar.getBoundingClientRect().top,
    barBottom: bar.getBoundingClientRect().bottom,
    barHeight: bar.getBoundingClientRect().height,
    toolsBottom: tools.getBoundingClientRect().bottom,
    boardTop,
    capture: Math.floor(boardTop),
  };
}"""


@pytest.mark.browser
class TestSolverProbe_TheBarStaysOutOfTheBoardsCapture:
    """The probe bar's 1 px of air above the board, in the mechanism domain.

    This is the fix round's control, and the defect it pins is not a tint or
    a transition: shipped with ``margin-bottom: calc(-1 * var(--space-4))``
    the bar ate the WHOLE 16 px between the toolbar and the board, so its
    bottom edge and ``.player-board``'s top edge were the same number to the
    1/64 px at every viewport the suite samples (246.796875 at 1280 x 720,
    210.796875 at 1440 x 900, 502.0625 at 390 x 844). A Playwright element
    screenshot clips the page raster to the enclosing whole-pixel rect, so
    row 0 of every ``.player-board`` capture then held the bottom 0.797 px of
    the Probe button — and
    ``tests/test_puzzle_solver_fifth_rule.py``
    ``TestSolverFifthRule_GeometryAndOtherMarksUnchanged::``
    ``test_the_rules_against_paper_are_untouched``, which compares two such
    captures of a BLANK board byte for byte, reported a difference on 4
    pixels of that row (the button's antialiased corners, by 1 per channel).
    Its message said a hairline was reaching unfilled cells; no cell had a
    ``box-shadow`` at all. That sibling is this claim's PIXEL control and is
    not edited (G-7); what is asserted here is the two edges themselves.

    The claim is stated as ``barBottom <= floor(boardTop)`` and not as "1 px
    of air", because ``floor(t) > t - 1`` for every ``t``: one whole CSS
    pixel of air keeps the bar out of the capture's first row at every
    viewport, zoom and device pixel ratio rather than at the ones measured,
    and half a pixel does not — both measured, as the fix round's A1/A2
    mutants.

    Two assertions, and the first is not decoration. A bar that is hidden,
    or that has been folded back onto the toolbar's first row, satisfies the
    second one for a reason that has nothing to do with the air; the premise
    says the bar is visible and is a line of its OWN below ``.player-tools``,
    which is the layout the air is arithmetic about.

    Both probe states are swept because the bar's height is not constant —
    Keep, Contradiction and the leaving note appear while a probe is open,
    and at 390 px they wrap the bar onto further lines (measured: 24 px
    closed, taller open). The air is a function of the bar's MARGIN and not
    of its height, and that is the half of the arithmetic a reader is most
    likely to doubt.
    """

    @pytest.mark.parametrize(
        "viewport,open_probe",
        [
            ((1440, 900), False),
            ((1440, 900), True),
            ((390, 844), False),
            ((390, 844), True),
        ],
        ids=["desktop-closed", "desktop-open", "phone-closed", "phone-open"],
    )
    def test_the_bar_ends_above_the_boards_first_capture_row(
        self, browser_page, live, viewport, open_probe
    ) -> None:
        browser_page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        _open(browser_page, live, live.store(GRID))
        if open_probe:
            _probe(browser_page)
            assert _probe_pressed(browser_page) == "true"
        seen = browser_page.evaluate(_BAR_AGAINST_BOARD)

        assert (
            not seen["hidden"]
            and seen["barHeight"] > 0
            and seen["barTop"] >= seen["toolsBottom"]
        ), (
            f"the probe bar is not a visible line of its own below "
            f".player-tools, so the air below it is not what keeps it out of "
            f"the board's capture: {seen}"
        )
        assert seen["barBottom"] <= seen["capture"], (
            f"the probe bar's bottom edge ({seen['barBottom']}) is inside the "
            f"first whole pixel row an element screenshot of .player-board is "
            f"taken from (the board's top is {seen['boardTop']}, so the "
            f"capture starts at {seen['capture']}), which puts the bar's own "
            f"paint into every pixel reading taken of the board"
        )


#: Takes the probe LINE out of the page without taking the probe's element out
#: of the DOM: the bar stops being laid out, and the toolbar's own pull-up
#: stops applying. Together those are exactly the two rules CARD-268 adds to
#: the page's vertical geometry, so what is left is the layout the solve page
#: had before this card — which is the thing the board's position is compared
#: against. (``display: none`` alone would not do it: ``:has(.player-probe)``
#: matches on the element's PRESENCE, so the toolbar would keep the pull-up
#: and the board would sit 9 px too high.)
_WITHOUT_THE_PROBE_LINE = """() => {
  const style = document.createElement('style');
  style.id = 'card268-no-probe-line';
  style.textContent =
    '.player-probe { display: none !important; }'
    + '.player-toolbar { margin-top: 0 !important; }';
  document.head.append(style);
}"""

_BOARD_TOP = """() => document.querySelector('.player-board').getBoundingClientRect().top"""

_TOOLBAR_PULL = """() => parseFloat(
  getComputedStyle(document.querySelector('.player-toolbar')).marginTop)"""


@pytest.mark.browser
class TestSolverProbe_TheBarCostsTheBoardNoGround:
    """The probe bar's line is paid for ABOVE the toolbar, so the board sits
    exactly where it sat before this card.

    The card's own first constraint is that the board may not move down —
    ``#puzzle-player`` is a scroll container, Chromium puts it in the Tab
    order and smooth-scrolls it into view, and a board lower down means a
    longer scroll still in flight when a test drags across it. The
    implementation round read that constraint as a budget with 8 px of slack
    and shipped the bar's line out of the toolbar's bottom margin alone; the
    fix round measured the slack and there is none. Eight px lower took the
    focus scroll from 11 px to 19 px, past the half-cell the constraint is
    about, and reddened 3 of the 8 cases of
    ``tests/test_puzzle_solver_marking.py``
    ``TestSolverMarking_KeyboardAndLabels::test_each_tool_acts_on_a_single_key_press``
    plus — by a second route nobody had looked for — ``test_the_banner_takes
    _the_tools_place_and_the_board_does_not_move`` in
    ``tests/test_puzzle_solver_progress.py``, whose last filled cell went
    under the fold so that Playwright scrolled the PAGE 5 px to click it.
    Both of those are unedited siblings (G-7) and both are behavioural
    controls for this claim: they were red at the implementation round's
    commit and are green with the pull-up.

    What is asserted HERE is the arithmetic itself, because those two go red
    at 8 px and not at 1 px, and 1 px is exactly the error a reader of this
    rule would make: the board's top is compared with the board's top in a
    page whose two CARD-268 geometry rules have both been switched off, and
    the two must be the same number. That is sharp at one pixel.

    Probe CLOSED at all three viewports, which is the standing layout every
    sibling test sees. An OPEN probe deliberately makes the bar taller (Keep,
    Contradiction and the leaving note appear) and at 390 px wraps it onto
    further lines, so the board does move down while a probe is open — the
    player asked for it, it lasts as long as the probe does, and no test in
    the family opens one. The companion class above is what holds the air in
    that state.
    """

    @pytest.mark.parametrize(
        "viewport",
        [(1280, 720), (1440, 900), (390, 844)],
        ids=["1280x720", "1440x900", "390x844"],
    )
    def test_the_probe_line_leaves_the_boards_top_where_it_was(
        self, browser_page, live, viewport
    ) -> None:
        browser_page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        _open(browser_page, live, live.store(GRID))

        pull = browser_page.evaluate(_TOOLBAR_PULL)
        assert pull < 0 and browser_page.locator(".player-probe").is_visible(), (
            f"the toolbar's margin-top is {pull} and the probe bar's "
            f"visibility is "
            f"{browser_page.locator('.player-probe').is_visible()}: there is "
            f"no line to pay for, or nothing paying for it, so the "
            f"comparison below is between a page and itself"
        )

        with_bar = browser_page.evaluate(_BOARD_TOP)
        browser_page.evaluate(_WITHOUT_THE_PROBE_LINE)
        without = browser_page.evaluate(_BOARD_TOP)
        assert with_bar == without, (
            f"the board's top is {with_bar} with the probe line and "
            f"{without} without it, so the line this card adds to the "
            f"toolbar moves the board by {with_bar - without} px"
        )
