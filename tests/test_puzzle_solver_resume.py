"""CARD-185 — the puzzle player reopens a puzzle in the state it was left in,
in this browser only (FR-044 AC-360..AC-365, EC-046, EC-047; CON-021 as
amended 2026-10-06).

The player keeps one ``localStorage`` entry per puzzle, under
``"nonogram-player:" + id``, written after every recorded change, read at
load, removed by a confirmed reset. Nothing goes to the server.

The pure functions (``saveKey``, ``gridFingerprint``, ``serializeState``,
``deserializeState`` in ``solver_state.js``) are run with
``await import('/static/solver_state.js')`` over corpora built with
``random.Random`` and fixed seeds (no ``hypothesis``); minimum counts are
asserted inside the tests. Expected values come from Python written here
(the key, the FNV-1a fingerprint, a stroke replay) or from CARD-162's
error / solved definitions — or from the ORIGINAL history, which was built
without the save. User-facing criteria drive real input in Chromium.
"""

from __future__ import annotations

import json
import random

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
    _marked,
    _states,
    _tool,
)
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _open,
    _unique_grid,
    browser_page,
    browser_type,
    live,
)
from tests.test_puzzle_solver_progress import (
    NAME,
    _error_count,
    _errors_of,
    _is_solved_shown,
    _set,
    _solve,
    _solved_of,
    _watch_problems,
)

M = "maybe"
_TOOL_CODE = {F: "f", E: "e", U: "u", M: "m"}


def _key(puzzle_id):
    """The storage key, written out (not saveKey)."""
    return f"nonogram-player:{puzzle_id}"


def _fnv1a(grid):
    """32-bit FNV-1a of the grid read row-major as "1"/"0", as 8 hex digits."""
    value = 0x811C9DC5
    for row in grid:
        for filled in row:
            value ^= ord("1" if filled else "0")
            value = (value * 0x01000193) & 0xFFFFFFFF
    return f"{value:08x}"


def _payload(puzzle_id, grid):
    return {
        "id": puzzle_id,
        "width": len(grid[0]),
        "height": len(grid),
        "rows": [_encode(row) for row in grid],
        "columns": [_encode(col) for col in zip(*grid)],
        "solution": grid,
    }


def _replay(width, height, strokes):
    """The board the strokes give from a blank board — written apart from replay."""
    cells = [U] * (width * height)
    for stroke in strokes:
        for r, c in stroke["cells"]:
            cells[r * width + c] = stroke["state"]
    return cells


def _is_solved(cells, grid):
    return M not in cells and _solved_of(cells, grid)


# ==========================================================================
# The pure functions
# ==========================================================================

_HISTORIES = """async ({ cases }) => {
  const S = await import('/static/solver_state.js');
  const tools = { f: S.FILLED, e: S.EMPTY, u: S.UNKNOWN, m: S.MAYBE };
  const strokes = (list) => list.map((s) => ({ cells: s.cells.map((c) => [...c]), state: s.state, hint: s.hint === true }));
  const view = (h, payload) => ({
    board: [...h.board.cells],
    done: strokes(h.done.map((entry) => entry.stroke)),
    undone: strokes(h.undone),
    errors: S.errorCount(h.board, payload.solution),
    hints: S.hintCount(h),
    solved: S.isSolved(h.board, payload.solution),
  });
  return cases.map(({ payload, ops }) => {
    let h = S.createHistory(S.createBoard(payload.width, payload.height));
    for (const op of ops) {
      if (op[0] === 'click') h = S.record(h, S.clickStroke(h.board, op[1], op[2], op[3] === null ? undefined : tools[op[3]]));
      else if (op[0] === 'drag') h = S.record(h, S.dragStroke(op[2], op[3], tools[op[1]]));
      else if (op[0] === 'reset') h = S.record(h, S.resetStroke(h.board));
      else if (op[0] === 'hint') {
        const hint = S.hintCell(h.board, payload.rows, payload.columns, payload.solution);
        if (hint !== null) h = S.record(h, S.hintStroke(hint.row, hint.col, hint.state));
      } else if (op[0] === 'undo') h = S.undo(h);
      else if (op[0] === 'redo') h = S.redo(h);
      else throw new Error(`unknown op ${op[0]}`);
    }
    const text = S.serializeState(h, payload);
    const back = S.deserializeState(text, payload);
    return { text, original: view(h, payload), restored: back === null ? null : view(back, payload) };
  });
}"""

_ROUND_TRIP_SHAPES = [(10, 10), (15, 10), (10, 25), (30, 30)]
_ROUND_TRIP_PER_SHAPE = 80


def _random_grid(width, height, rng):
    density = rng.uniform(0.3, 0.7)
    return [[rng.random() < density for _ in range(width)] for _ in range(height)]


def _solving_ops(grid):
    """Real-input-like strokes that leave exactly the solution filled."""
    ops = []
    width = len(grid[0])
    for r, row in enumerate(grid):
        ops.append(["drag", "u", [r, 0], [[r, width - 1]]])
        c = 0
        while c < width:
            if row[c]:
                end = c
                while end + 1 < width and row[end + 1]:
                    end += 1
                ops.append(["drag", "f", [r, c], [[r, end]] if end > c else []])
                c = end
            c += 1
    return ops


def _history_ops(width, height, grid, rng):
    ops = []
    for _ in range(rng.randint(8, 40)):
        roll = rng.random()
        if roll < 0.3:
            ops.append(["click", rng.randrange(height), rng.randrange(width), rng.choice(["f", "e", "u", "m", None])])
        elif roll < 0.6:
            start = [rng.randrange(height), rng.randrange(width)]
            end = [start[0], rng.randrange(width)] if rng.random() < 0.5 else [rng.randrange(height), start[1]]
            ops.append(["drag", rng.choice(["f", "e", "u", "m", "m"]), start, [end]])
        elif roll < 0.63:
            ops.append(["reset"])
        elif roll < 0.75:
            ops.append(["hint"])
        else:
            ops.extend([[rng.choice(["undo", "redo"])]] * rng.randint(1, 3))
    ending = rng.random()
    if ending < 0.2:
        ops.extend(_solving_ops(grid))
    elif ending < 0.6:
        ops.extend([["undo"]] * rng.randint(1, 3))
    return ops


def _round_trip_cases(width, height, rng):
    cases = []
    for _ in range(_ROUND_TRIP_PER_SHAPE):
        grid = _random_grid(width, height, rng)
        cases.append({"payload": _payload(f"{rng.getrandbits(64):016x}", grid),
                      "ops": _history_ops(width, height, grid, rng)})
    return cases


@pytest.mark.browser
def test_PropertyTest_SolverResume_SaveAndRestoreRoundTrip(browser_page, live) -> None:
    """AC-1 / EC-046 — serializeState then deserializeState gives back the
    board, the done strokes (cells, state, hint flag), the undone stack, the
    error count and the hint count of the original history; the original
    itself agrees with Python's replay, error count and hint count."""
    rng = random.Random(185)
    _open(browser_page, live, live.store(GRID))
    total = with_redo = with_hint = with_maybe = solved = 0
    for width, height in _ROUND_TRIP_SHAPES:
        cases = _round_trip_cases(width, height, rng)
        results = browser_page.evaluate(_HISTORIES, {"cases": cases})
        assert len(results) == len(cases)
        for case, result in zip(cases, results):
            payload, original, restored = case["payload"], result["original"], result["restored"]
            assert restored == original, (width, height, case["ops"])
            # The original, checked without the module's own functions.
            assert original["board"] == _replay(width, height, original["done"])
            assert original["errors"] == _errors_of(original["board"], payload["solution"])
            assert original["hints"] == sum(stroke["hint"] for stroke in original["done"])
            assert original["solved"] == _is_solved(original["board"], payload["solution"])
            # The text: exactly the documented fields; no solution in it.
            saved = json.loads(result["text"])
            assert set(saved) == {"v", "id", "width", "height", "rows", "columns", "grid", "done", "undone"}
            assert (saved["v"], saved["id"], saved["width"], saved["height"]) == (1, payload["id"], width, height)
            assert (saved["rows"], saved["columns"]) == (payload["rows"], payload["columns"])
            assert saved["grid"] == _fnv1a(payload["solution"])
            for kept, stroke in zip(saved["done"] + saved["undone"], original["done"] + original["undone"]):
                assert kept == ({"cells": stroke["cells"], "state": stroke["state"], "hint": True} if stroke["hint"]
                                else {"cells": stroke["cells"], "state": stroke["state"]})
            total += 1
            with_redo += bool(original["undone"])
            with_hint += original["hints"] > 0
            with_maybe += M in original["board"]
            solved += original["solved"]
    assert total >= 300, total
    assert with_redo >= 50, with_redo
    assert with_hint >= 50, with_hint
    assert with_maybe >= 50, with_maybe
    assert solved >= 30, solved


_REJECT = """async ({ payload, texts }) => {
  const S = await import('/static/solver_state.js');
  return texts.map((text) => {
    try {
      return S.deserializeState(text, payload) === null ? 'null' : 'history';
    } catch (error) {
      return `threw ${error.name}: ${error.message}`;
    }
  });
}"""

_VALID_SAVES = """async ({ payload, ops }) => {
  const S = await import('/static/solver_state.js');
  const tools = { f: S.FILLED, e: S.EMPTY, u: S.UNKNOWN, m: S.MAYBE };
  let h = S.createHistory(S.createBoard(payload.width, payload.height));
  const saves = [];
  for (const op of ops) {
    if (op[0] === 'drag') h = S.record(h, S.dragStroke(op[2], op[3], tools[op[1]]));
    else if (op[0] === 'hint') {
      const hint = S.hintCell(h.board, payload.rows, payload.columns, payload.solution);
      if (hint !== null) h = S.record(h, S.hintStroke(hint.row, hint.col, hint.state));
    } else if (op[0] === 'undo') h = S.undo(h);
    saves.push(S.serializeState(h, payload));
  }
  return saves;
}"""


def _corrupt(kind, text, payload, rng):
    """One corruption of a valid save text, of the named kind."""
    save = json.loads(text)
    width, height = payload["width"], payload["height"]
    strokes = save["done"] + save["undone"]
    if kind == "truncated":
        return text[: rng.randrange(len(text))]
    if kind == "non-object":
        return rng.choice(["[]", "null", "1", '"text"', "true", json.dumps([save]), json.dumps(text)])
    if kind == "version":
        save["v"] = rng.choice([0, 2, "1", None, 1.5, True, [1]])
    elif kind == "id":
        save["id"] = rng.choice([payload["id"] + "x", "", None, payload["id"].upper() + "Z", 7])
    elif kind == "size":
        field = rng.choice(["width", "height"])
        save[field] = rng.choice([save[field] + 1, save[field] - 1, str(save[field])])
    elif kind == "clue":
        axis = rng.choice(["rows", "columns"])
        line = rng.randrange(len(save[axis]))
        k = rng.randrange(len(save[axis][line]))
        save[axis][line][k] += rng.choice([1, -1]) if save[axis][line][k] > 0 else 1
    elif kind == "grid":
        flipped = "0" if save["grid"][0] != "0" else "1"
        save["grid"] = rng.choice([flipped + save["grid"][1:], save["grid"].upper() + "0", None, ""])
    elif kind == "cell":
        stroke = rng.choice(strokes)
        k = rng.randrange(len(stroke["cells"]))
        stroke["cells"][k] = rng.choice([[height, 0], [0, width], [-1, 0], [0, -1], [0.5, 0], ["0", 0], [0], [0, 0, 0]])
    elif kind == "state":
        rng.choice(strokes)["state"] = rng.choice(["Filled", "x", None, 1, "?", ""])
    elif kind == "hint":
        rng.choice(strokes)["hint"] = rng.choice([False, 1, "true", None, 0, [True]])
    elif kind == "no-op":
        k = rng.randrange(len(save["done"]))
        save["done"].insert(k + 1, json.loads(json.dumps(save["done"][k])))
    return json.dumps(save)


_CORRUPTIONS = ["truncated", "version", "id", "size", "clue", "grid", "cell", "state", "hint", "no-op", "non-object"]
_PER_CORRUPTION = 50


@pytest.mark.browser
def test_PropertyTest_SolverResume_RejectsAnyUntrustedSave(browser_page, live) -> None:
    """AC-2 / EC-047 — deserializeState returns null, and never throws, for
    every corrupted save; the saves they were made from all restore."""
    rng = random.Random(1850)
    _open(browser_page, live, live.store(GRID))
    sources = []
    for width, height in [(10, 10), (15, 10), (10, 25), (30, 30)]:
        grid = _random_grid(width, height, rng)
        payload = _payload(f"{rng.getrandbits(64):016x}", grid)
        ops = []
        for _ in range(30):
            roll = rng.random()
            if roll < 0.7:
                start = [rng.randrange(height), rng.randrange(width)]
                end = [start[0], rng.randrange(width)] if rng.random() < 0.5 else [rng.randrange(height), start[1]]
                ops.append(["drag", rng.choice(["f", "e", "u", "m"]), start, [end]])
            elif roll < 0.85:
                ops.append(["hint"])
            else:
                ops.append(["undo"])
        saves = browser_page.evaluate(_VALID_SAVES, {"payload": payload, "ops": ops})
        # Saves with something to corrupt: a done stroke, and a hint somewhere.
        usable = [text for text in saves if json.loads(text)["done"]
                  and any(s.get("hint") for s in json.loads(text)["done"] + json.loads(text)["undone"])]
        assert len(usable) >= 5, (width, height)
        assert browser_page.evaluate(_REJECT, {"payload": payload, "texts": usable}) == ["history"] * len(usable)
        sources.append((payload, usable))

    counts = dict.fromkeys(_CORRUPTIONS, 0)
    total = 0
    for kind in _CORRUPTIONS:
        by_payload = {}
        for _ in range(_PER_CORRUPTION):
            payload, usable = rng.choice(sources)
            by_payload.setdefault(payload["id"], (payload, []))[1].append(_corrupt(kind, rng.choice(usable), payload, rng))
        for payload, texts in by_payload.values():
            verdicts = browser_page.evaluate(_REJECT, {"payload": payload, "texts": texts})
            for text, verdict in zip(texts, verdicts):
                assert verdict == "null", (kind, verdict, text[:300])
            counts[kind] += len(texts)
            total += len(texts)
    assert total >= 500, total
    assert min(counts.values()) >= 20, counts


_KEY_AND_FINGERPRINT = """async ({ ids, grids }) => {
  const S = await import('/static/solver_state.js');
  return { version: S.SAVE_VERSION, keys: ids.map(S.saveKey), prints: grids.map(S.gridFingerprint) };
}"""


@pytest.mark.browser
class TestSolverResumeModule_KeyAndFingerprint:
    """saveKey is "nonogram-player:" + id; gridFingerprint is FNV-1a of the
    grid read row-major as "1"/"0" — both against Python written here."""

    def test_key_and_fingerprint(self, browser_page, live) -> None:
        rng = random.Random(18501)
        _open(browser_page, live, live.store(GRID))
        ids = ["abc", "", "0123456789abcdef", "with:colon"]
        grids = [GRID, [[False]], [[True]]] + [_random_grid(rng.randint(1, 30), rng.randint(1, 30), rng) for _ in range(60)]
        seen = browser_page.evaluate(_KEY_AND_FINGERPRINT, {"ids": ids, "grids": grids})
        assert seen["version"] == 1
        assert seen["keys"] == [_key(i) for i in ids]
        assert seen["prints"] == [_fnv1a(g) for g in grids]
        assert len(set(seen["prints"])) == len(grids)  # no collision in this corpus


_START_NOT_BLANK = """async ({ payload }) => {
  const S = await import('/static/solver_state.js');
  const blank = S.createBoard(payload.width, payload.height);
  const marked = S.withCell(blank, 0, 0, S.FILLED);
  const fromMarked = S.record(S.createHistory(marked), S.clickStroke(marked, 1, 1));
  const fromBlank = S.record(S.createHistory(blank), S.clickStroke(blank, 1, 1));
  return [
    S.serializeState(S.createHistory(marked), payload),
    S.serializeState(fromMarked, payload),
    S.serializeState(S.undo(fromMarked), payload),
    S.serializeState(S.createHistory(blank), payload) !== null,
    S.serializeState(S.undo(fromBlank), payload) !== null,
  ];
}"""


@pytest.mark.browser
class TestSolverResumeModule_OnlyABlankStartIsSaved:
    """serializeState gives null for a history that does not start from a
    blank board (what setBoard makes), with or without strokes after it."""

    def test_only_a_blank_start(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(GRID))
        payload = _payload("p", GRID)
        assert browser_page.evaluate(_START_NOT_BLANK, {"payload": payload}) == [None, None, None, True, True]


# ==========================================================================
# The page
# ==========================================================================


def _saved(page, puzzle_id):
    return page.evaluate("(key) => localStorage.getItem(key)", _key(puzzle_id))


def _hints_shown(page):
    return int(page.locator("[data-player-hints]").text_content())


def _reload(page):
    page.reload()
    page.wait_for_function("window.puzzlePlayer !== undefined")


@pytest.mark.browser
class TestSolverResume_ReloadRestoresBoardCountsAndHistory:
    """AC-3 / AC-360 — five strokes, a hint, a "?" mark and an undo survive a
    reload: board, both counts, then Redo and Undo through the same steps."""

    def test_reload_restores(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        puzzle_id = live.store(GRID)
        _open(browser_page, live, puzzle_id)
        boards = [_states(browser_page)]

        def step(action):
            action()
            boards.append(_states(browser_page))
            assert boards[-1] != boards[-2]

        step(lambda: _drag(browser_page, [(0, 0), (0, 6)]))
        step(lambda: _cell(browser_page, 2, 2).click())
        step(lambda: (_tool(browser_page, "White"), _drag(browser_page, [(4, 1), (4, 9)])))
        step(lambda: (_tool(browser_page, "Maybe"), _cell(browser_page, 6, 6).click()))
        step(lambda: _button(browser_page, "Hint").click())
        step(lambda: (_tool(browser_page, "Black"), _cell(browser_page, 8, 8).click()))
        step(lambda: _cell(browser_page, 10, 3).click())
        _button(browser_page, "Undo").click()
        before = _states(browser_page)
        assert before == boards[-2]
        assert M in before
        errors, hints = _error_count(browser_page), _hints_shown(browser_page)
        assert hints == 1 and errors == _errors_of(before, GRID)

        _reload(browser_page)
        assert _states(browser_page) == before
        assert (_error_count(browser_page), _hints_shown(browser_page)) == (errors, hints)
        assert _button(browser_page, "Black").get_attribute("aria-pressed") == "true"  # default (c)
        _button(browser_page, "Redo").click()
        assert _states(browser_page) == boards[-1]
        for expected in reversed(boards[:-1]):
            _button(browser_page, "Undo").click()
            assert _states(browser_page) == expected
        assert _is_disabled(browser_page, "Undo")
        assert _hints_shown(browser_page) == 0
        assert problems == []


def _solve_by_hand(page, grid=GRID):
    """Solve ``grid`` with real input only: each row dragged Black, then its
    solution-empty cells clicked once (Black -> White)."""
    width = len(grid[0])
    for r, row in enumerate(grid):
        _drag(page, [(r, 0), (r, width - 1)])
        for c, filled in enumerate(row):
            if not filled:
                _cell(page, r, c).click()


@pytest.mark.browser
class TestSolverResume_SolvedPuzzleReopensSolved:
    """AC-4 / AC-361 — a solved board reopens solved and locked; Reset works."""

    def test_solved_reopens_solved(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        puzzle_id = live.store(GRID, name=NAME)
        _open(browser_page, live, puzzle_id)
        _solve_by_hand(browser_page)
        assert _is_solved_shown(browser_page)
        solved = _states(browser_page)

        _reload(browser_page)
        assert _states(browser_page) == solved
        assert _is_solved_shown(browser_page)
        assert NAME in browser_page.locator("#puzzle-player-announce").text_content()
        assert browser_page.evaluate("document.querySelector('.player-board').classList.contains('is-solved')")
        _cell(browser_page, 0, 0).click()
        assert _states(browser_page) == solved  # locked
        assert _is_disabled(browser_page, "Undo") and _is_disabled(browser_page, "Redo")
        assert not _is_disabled(browser_page, "Reset")
        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()
        assert set(_states(browser_page)) == {U}
        assert not _is_solved_shown(browser_page)
        assert problems == []


@pytest.mark.browser
class TestSolverResume_ResetClearsTheSave:
    """AC-5 / AC-362 — a confirmed reset removes the entry; its in-page Undo
    writes it again; after reset and reload the board is blank."""

    def test_reset_clears(self, browser_page, live) -> None:
        puzzle_id = live.store(GRID)
        _open(browser_page, live, puzzle_id)
        _drag(browser_page, [(1, 0), (1, 8)])
        _button(browser_page, "Hint").click()
        _cell(browser_page, 5, 5).click()
        marks = _states(browser_page)
        assert _saved(browser_page, puzzle_id) is not None

        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()
        assert _saved(browser_page, puzzle_id) is None
        _button(browser_page, "Undo").click()  # default (a): undo still works before a reload
        assert _states(browser_page) == marks
        assert _saved(browser_page, puzzle_id) is not None
        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()
        assert _saved(browser_page, puzzle_id) is None

        _reload(browser_page)
        assert set(_states(browser_page)) == {U}
        assert (_error_count(browser_page), _hints_shown(browser_page)) == (0, 0)
        assert _is_disabled(browser_page, "Undo") and _is_disabled(browser_page, "Redo")


#: A second 15 x 15 puzzle: same size as GRID, another grid.
GRID_B = _unique_grid(15, 15, seed=1852)


@pytest.mark.browser
class TestSolverResume_UntrustedSaveStartsFresh:
    """AC-6 / AC-363 — another puzzle's save, corrupt JSON and a v=2 save are
    each removed at load; the board starts blank, the console stays clean,
    and the next mark writes a save that restores."""

    @pytest.mark.parametrize("kind", ["other-puzzle", "corrupt-json", "version-2"])
    def test_untrusted_starts_fresh(self, browser_page, live, kind) -> None:
        assert GRID_B != GRID
        problems = _watch_problems(browser_page, live)
        a, b = live.store(GRID), live.store(GRID_B)
        _open(browser_page, live, a)
        _drag(browser_page, [(3, 0), (3, 7)])
        _cell(browser_page, 9, 9).click()
        save = json.loads(_saved(browser_page, a))
        save["id"] = b
        if kind == "other-puzzle":
            text = json.dumps(save)
        elif kind == "corrupt-json":
            text = json.dumps(save)[:-7] + "}{"
        else:
            save["v"] = 2
            text = json.dumps(save)
        browser_page.evaluate("([key, text]) => localStorage.setItem(key, text)", [_key(b), text])

        _open(browser_page, live, b)
        assert set(_states(browser_page)) == {U}
        assert _saved(browser_page, b) is None  # the untrusted entry is removed
        _cell(browser_page, 0, 0).click()
        written = json.loads(_saved(browser_page, b))
        assert (written["v"], written["id"], written["grid"]) == (1, b, _fnv1a(GRID_B))
        mark = _states(browser_page)
        _reload(browser_page)
        assert _states(browser_page) == mark
        assert problems == []


#: Init scripts that break storage: setItem throws, or reading
#: window.localStorage throws.
_QUOTA = """Storage.prototype.setItem = function () {
  throw new DOMException('the quota is exceeded', 'QuotaExceededError');
};"""
_SECURITY = """Object.defineProperty(window, 'localStorage', {
  configurable: true,
  get() { throw new DOMException('storage is denied', 'SecurityError'); },
});"""


def _use_the_player(page):
    """Marks, undo, reset (confirmed), then a solve — every action checked."""
    _drag(page, [(2, 0), (2, 9)])
    _cell(page, 7, 7).click()
    marks = _states(page)
    assert len(_marked(marks)) == 11
    _button(page, "Undo").click()
    assert len(_marked(_states(page))) == 10
    _button(page, "Redo").click()
    assert _states(page) == marks
    _button(page, "Reset").click()
    _button(page, "Clear board").click()
    assert set(_states(page)) == {U}
    _button(page, "Undo").click()
    assert _states(page) == marks
    _solve(page)
    assert _is_solved_shown(page)


@pytest.mark.browser
class TestSolverResume_BrokenStorageDegradesSilently:
    """AC-7 / AC-364 — with setItem throwing QuotaExceededError, or reading
    window.localStorage throwing SecurityError, the player works and logs
    nothing; a failed write removes the entry, so a reload is blank."""

    def test_quota_exceeded(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        puzzle_id = live.store(GRID, name=NAME)
        _open(browser_page, live, puzzle_id)
        _cell(browser_page, 0, 0).click()
        assert _saved(browser_page, puzzle_id) is not None
        browser_page.add_init_script(_QUOTA)
        _reload(browser_page)
        assert _marked(_states(browser_page)) == {(0, 0): F}  # reading still works
        _cell(browser_page, 1, 1).click()  # the write fails ...
        assert _saved(browser_page, puzzle_id) is None  # ... so the entry is removed
        assert browser_page.evaluate("(() => { try { localStorage.setItem('x', '1'); return 'wrote'; } catch (e) { return e.name; } })()") == "QuotaExceededError"
        _reload(browser_page)
        assert set(_states(browser_page)) == {U}
        _use_the_player(browser_page)
        assert problems == []

    def test_security_error(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        browser_page.add_init_script(_SECURITY)
        _open(browser_page, live, live.store(GRID, name=NAME))
        assert browser_page.evaluate("(() => { try { return typeof window.localStorage; } catch (e) { return e.name; } })()") == "SecurityError"
        _use_the_player(browser_page)
        _button(browser_page, "Reset").click()
        _button(browser_page, "Clear board").click()
        _reload(browser_page)
        assert set(_states(browser_page)) == {U}
        assert problems == []


@pytest.mark.browser
class TestSolverResume_SavesEveryChangeWithoutARequest:
    """AC-8 / AC-365 — twenty strokes, two undos, a hint and a reload: no
    request for any mark, and the entry changes after each recorded change."""

    def test_saves_every_change(self, browser_page, live) -> None:
        problems = _watch_problems(browser_page, live)
        puzzle_id = live.store(GRID)
        _open(browser_page, live, puzzle_id)
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.context.on("request", lambda request: requests.append(request.url))
        entries = [_saved(browser_page, puzzle_id)]
        assert entries == [None]

        def changed(action):
            action()
            entries.append(_saved(browser_page, puzzle_id))
            assert entries[-1] is not None and entries[-1] != entries[-2], len(entries)

        for k in range(20):
            changed(lambda k=k: _cell(browser_page, k % SIDE, (k * 4) % SIDE).click())
        changed(lambda: _button(browser_page, "Undo").click())
        changed(lambda: _button(browser_page, "Undo").click())
        changed(lambda: _button(browser_page, "Hint").click())
        assert requests == []
        board = _states(browser_page)

        _reload(browser_page)
        browser_page.wait_for_load_state("networkidle")
        assert _states(browser_page) == board
        assert _saved(browser_page, puzzle_id) == entries[-1]
        requests.clear()
        changed(lambda: _cell(browser_page, 14, 14).click())
        assert requests == []
        assert problems == []

    def test_a_drag_preview_writes_nothing(self, browser_page, live) -> None:
        from tests.test_puzzle_solver_marking import _centre

        puzzle_id = live.store(GRID)
        _open(browser_page, live, puzzle_id)
        _cell(browser_page, 0, 0).click()
        entry = _saved(browser_page, puzzle_id)
        browser_page.mouse.move(*_centre(browser_page, 5, 0))
        browser_page.mouse.down()
        for c in range(1, 8):
            browser_page.mouse.move(*_centre(browser_page, 5, c), steps=3)
        assert _states(browser_page)[5 * SIDE + 7] == F  # previewed ...
        assert _saved(browser_page, puzzle_id) == entry  # ... not written
        browser_page.mouse.up()
        assert _saved(browser_page, puzzle_id) != entry


@pytest.mark.browser
class TestSolverResume_SetBoardStartIsNotSaved:
    """setBoard (the CARD-160 seam) to a non-blank board starts a history
    serializeState cannot save: the entry is removed, stays absent while that
    history lasts, and a reload starts blank rather than from a wrong board."""

    def test_set_board(self, browser_page, live) -> None:
        puzzle_id = live.store(GRID)
        _open(browser_page, live, puzzle_id)
        _cell(browser_page, 0, 0).click()
        assert _saved(browser_page, puzzle_id) is not None
        cells = [U] * (SIDE * SIDE)
        cells[3 * SIDE + 3] = E
        _set(browser_page, cells)
        assert _saved(browser_page, puzzle_id) is None
        _cell(browser_page, 4, 4).click()
        assert _saved(browser_page, puzzle_id) is None
        _reload(browser_page)
        assert set(_states(browser_page)) == {U}
        _set(browser_page, [U] * (SIDE * SIDE))  # a blank start is saved
        _cell(browser_page, 6, 6).click()
        assert _saved(browser_page, puzzle_id) is not None
