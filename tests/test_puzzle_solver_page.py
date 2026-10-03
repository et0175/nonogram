"""CARD-160 — the admin panel's puzzle player page (FR-044, ADR-0038).

The *puzzle player* (TERM-037) is the page a person solves a stored puzzle on,
at ``/puzzle/<id>/solve``. It is not the uniqueness solver (COMP-005); nothing
here touches ``src/nonogram/solver/``.

Two tiers, as ADR-0038 decides:

* **Server tests** (Flask test client, in-memory and SQLite stores): the route,
  the 404, and the embedded JSON payload — the page's contract with
  ``static/solver.js``. Clues are checked against an *independent* run-length
  encoder written here (``_encode``), never against ``compute_clues`` itself.
* **Browser tests** (``@pytest.mark.browser``, pytest-playwright + Chromium,
  ADR-0038/R7): everything only a browser can see — the drawn board, the clue
  boxes, the heavier fifth lines by computed style, the page's JS state, the
  pure state module, and that playing writes nothing. The real Flask app is
  served on 127.0.0.1 with an ephemeral port (loopback only, CON-015).

  CI step (ADR-0038/R8): ``pip install -e '.[dev]' && playwright install
  chromium`` before the suite. Without pytest-playwright or Chromium these
  tests FAIL with that instruction — deliberately not a skip, because pytest's
  default summary hides skip reasons and a silent green skip is this repo's
  known failure mode (the DB-mode tests without ``nonogram_test``).

Property corpora are hand-built with ``random.Random`` and a fixed seed, each
asserting its own minimum case count (no ``hypothesis``: not in the baseline).
"""

from __future__ import annotations

import json
import random
import re
import threading
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from itertools import groupby
from pathlib import Path

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.db import make_batch, make_book, sqlite_session_scope

_REPO = Path(__file__).resolve().parent.parent
_ADMIN = _REPO / "src" / "nonogram" / "admin"
_STATIC = _ADMIN / "static"

STORES = ("memory", "sqlite")
MAJOR_EVERY = 5


# --------------------------------------------------------------------------
# Grids: uniquely solvable by construction
# --------------------------------------------------------------------------


def _tight_row(width: int, rng: random.Random) -> list[bool]:
    """A row its clue alone determines: runs separated by exactly one gap,
    starting at the first cell and ending at the last."""
    runs = rng.randint(1, (width + 1) // 2)
    filled = width - (runs - 1)
    cuts = sorted(rng.sample(range(1, filled), runs - 1))
    row: list[bool] = []
    for index, (start, end) in enumerate(zip([0] + cuts, cuts + [filled])):
        if index:
            row.append(False)
        row.extend([True] * (end - start))
    assert len(row) == width
    return row


def _unique_grid(width: int, height: int, seed: int, empty_rows=()) -> list[list[bool]]:
    """Every row is tight or empty, so the clues admit exactly one grid and
    the storage boundary's solver accepts it (ADR-0032/R1)."""
    rng = random.Random(seed)
    return [[False] * width if r in empty_rows else _tight_row(width, rng) for r in range(height)]


def _transposed(grid):
    return [list(column) for column in zip(*grid)]


def _encode(line) -> list[int]:
    """Run-length encoding written independently of ``nonogram.clues``."""
    runs = [len(list(group)) for value, group in groupby(line) if value]
    return runs or [0]


def _expected_clues(grid):
    return [_encode(row) for row in grid], [_encode(column) for column in zip(*grid)]


#: AC-296/297/298: 25 wide, 15 high, row 3 (the third row, index 2) empty.
AC_GRID = _unique_grid(25, 15, seed=296, empty_rows={2})
#: AC-301: 20 x 20.
AC301_GRID = _unique_grid(20, 20, seed=301)


def _store(service, grid, *, tier="medium", name=None, source="owl.png", batch_id=None) -> str:
    puzzle_id = service.add_puzzle(
        grid=grid,
        clues_rows=[],
        clues_cols=[],
        width=len(grid[0]),
        height=len(grid),
        theme="test",
        difficulty_score=40,
        difficulty_tier=tier,
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=batch_id,
        source_image=source,
    )
    if name:
        service.rename_puzzle(puzzle_id, name)
    return puzzle_id


# --------------------------------------------------------------------------
# The panel, over an in-memory or a SQLite store (never a live database)
# --------------------------------------------------------------------------


def _build_app(store, scope, monkeypatch):
    from nonogram.admin.app import create_app

    monkeypatch.setenv("TESTING", "true")
    if store == "memory":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))
    else:
        import nonogram.db

        monkeypatch.setenv("DATABASE_URL", "sqlite:///card-160-test-only")
        monkeypatch.setattr(nonogram.db, "session_scope", scope)
    app = create_app()
    app.config["TESTING"] = True
    # The tests must exercise the store they name, not silently fall back.
    assert (app.puzzle_review_service._session_factory is None) == (store == "memory")
    return app


@pytest.fixture(params=STORES)
def store(request):
    return request.param


@pytest.fixture
def scope(store, tmp_path):
    return sqlite_session_scope(tmp_path, "card-160.db") if store == "sqlite" else None


@pytest.fixture
def panel(store, scope, monkeypatch):
    return _build_app(store, scope, monkeypatch)


_PAYLOAD = re.compile(
    r'<script type="application/json" id="puzzle-player-data">(.*?)</script>', re.S
)


def _page(panel, puzzle_id) -> str:
    response = panel.test_client().get(f"/puzzle/{puzzle_id}/solve")
    assert response.status_code == 200, response.status_code
    return response.get_data(as_text=True)


def _payload(html: str) -> dict:
    match = _PAYLOAD.search(html)
    assert match, "the player page embeds no puzzle payload"
    return json.loads(match.group(1))


# ==========================================================================
# Server tests
# ==========================================================================


class TestSolverPage_UnknownPuzzleIs404:
    """AC-299 — an unknown id is the panel's 404 page, status 404."""

    def test_no_such_puzzle_is_the_panels_404(self, panel) -> None:
        response = panel.test_client().get("/puzzle/no-such-puzzle/solve")

        assert response.status_code == 404
        body = response.get_data(as_text=True)
        assert "Page not found" in body and 'class="error-page"' in body
        assert "puzzle-player-data" not in body

    def test_a_well_formed_id_that_names_nothing_is_404_too(self, panel) -> None:
        _store(panel.puzzle_review_service, AC_GRID)
        unknown = "00000000-0000-4000-8000-000000000000" if panel.puzzle_review_service._session_factory else "puzzle_999999"

        response = panel.test_client().get(f"/puzzle/{unknown}/solve")

        assert response.status_code == 404
        assert "Page not found" in response.get_data(as_text=True)


class TestSolverPage_ShowsTheClues:
    """AC-296 / AC-297 — the board's size and its 40 clue boxes.

    The server half: the payload carries the grid's real size and
    compute_clues of the stored grid (ADR-0038/R3). The browser half, further
    down, reads what is drawn.
    """

    def test_the_payload_is_the_25x15_grid_with_its_clues(self, panel) -> None:
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID)

        payload = _payload(_page(panel, puzzle_id))

        rows, columns = _expected_clues(AC_GRID)
        assert (payload["width"], payload["height"]) == (25, 15)
        assert payload["rows"] == rows and len(rows) == 15
        assert payload["columns"] == columns and len(columns) == 25
        assert payload["rows"][2] == [0]
        assert payload["solution"] == AC_GRID

    def test_the_payload_has_exactly_the_documented_shape(self, panel) -> None:
        """The contract in solver.js's header — no more, no fewer keys."""
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID)

        payload = _payload(_page(panel, puzzle_id))

        assert set(payload) == {"id", "width", "height", "rows", "columns", "solution"}
        assert payload["id"] == puzzle_id
        assert all(isinstance(cell, bool) for row in payload["solution"] for cell in row)

    def test_the_contract_is_documented_in_the_renderer(self) -> None:
        header = (_STATIC / "solver.js").read_text(encoding="utf-8")
        for key in ("id", "width", "height", "rows", "columns", "solution"):
            assert f'"{key}"' in header, key


def _corpus_sizes(rng: random.Random) -> list[tuple[int, int]]:
    """Every corner of the supported range, then random non-square sizes."""
    sizes = [(MIN_SIZE, MIN_SIZE), (MAX_SIZE, MAX_SIZE), (MIN_SIZE, MAX_SIZE), (MAX_SIZE, MIN_SIZE)]
    while len(sizes) < 40:
        width, height = rng.randint(MIN_SIZE, MAX_SIZE), rng.randint(MIN_SIZE, MAX_SIZE)
        if width != height:
            sizes.append((width, height))
    return sizes


def test_PropertyTest_SolverPage_EmbeddedCluesAreTheGridsEncoding(monkeypatch) -> None:
    """For every stored grid in a seeded corpus (sizes MIN_SIZE..MAX_SIZE,
    non-square included, some lines empty), the payload's clues equal an
    independent encoding of the grid, its size is the grid's, and its solution
    is the grid."""
    panel = _build_app("memory", None, monkeypatch)
    rng = random.Random(160)
    cases = 0
    for width, height in _corpus_sizes(rng):
        empty = set(rng.sample(range(height), rng.randint(0, 2)))
        grid = _unique_grid(width, height, seed=rng.randrange(10**9), empty_rows=empty)
        if rng.random() < 0.5:
            grid = _transposed(grid)  # tight columns instead: deep column clues
        puzzle_id = _store(panel.puzzle_review_service, grid)

        payload = _payload(_page(panel, puzzle_id))

        rows, columns = _expected_clues(grid)
        assert (payload["width"], payload["height"]) == (len(grid[0]), len(grid))
        assert payload["rows"] == rows
        assert payload["columns"] == columns
        assert payload["solution"] == grid
        cases += 1
    assert cases >= 40


class TestSolverPageHeader:
    """Item 3 — "Puzzle <title>" and the tier, as the printed header reads."""

    def test_header_reads_puzzle_title_and_the_tier(self, panel) -> None:
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID, tier="medium", name="Snowy owl")

        html = _page(panel, puzzle_id)

        assert re.search(r"<h1>\s*Puzzle Snowy owl\s*</h1>", html)
        assert re.search(r'<span class="player-tier"><span class="badge tier"[^>]*>MEDIUM</span>', html)

    def test_header_reads_a_display_label_tier_too(self, panel) -> None:
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID, tier="Hard")

        assert ">HARD</span>" in _page(panel, puzzle_id)

    def test_header_without_a_tier_shows_no_chip(self, panel) -> None:
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID, tier="")

        assert "player-tier" not in _page(panel, puzzle_id)

    def test_header_falls_back_to_source_then_id(self, panel) -> None:
        service = panel.puzzle_review_service
        from_source = _store(service, AC_GRID, source="heron.png")
        from_id = _store(service, AC_GRID, source=None)

        assert re.search(r"<h1>\s*Puzzle heron.png\s*</h1>", _page(panel, from_source))
        assert re.search(rf"<h1>\s*Puzzle {re.escape(from_id[:8])}\s*</h1>", _page(panel, from_id))


class TestSolverPageStoredRows:
    """Failure matrix F3..F6 — what a stored row can be, and what the page does."""

    def _raw(self, monkeypatch, grid, **fields):
        """A legacy in-memory row written around the storage guard."""
        panel = _build_app("memory", None, monkeypatch)
        service = panel.puzzle_review_service
        puzzle_id = _store(service, AC_GRID)
        service.puzzles[puzzle_id] = {**service.puzzles[puzzle_id], "grid": grid, **fields}
        return panel, puzzle_id

    def test_stale_stored_clues_and_sizes_are_never_shown(self, monkeypatch) -> None:
        panel, puzzle_id = self._raw(
            monkeypatch, AC_GRID, clues_rows=[[9]] * 15, clues_cols=[[9]] * 25, width=10, height=10
        )

        payload = _payload(_page(panel, puzzle_id))

        assert (payload["rows"], payload["columns"]) == _expected_clues(AC_GRID)
        assert (payload["width"], payload["height"]) == (25, 15)

    def test_a_legacy_zero_one_grid_is_read_as_booleans(self, monkeypatch) -> None:
        legacy = [[int(cell) for cell in row] for row in AC_GRID]
        panel, puzzle_id = self._raw(monkeypatch, legacy)

        payload = _payload(_page(panel, puzzle_id))

        assert payload["solution"] == AC_GRID
        assert (payload["rows"], payload["columns"]) == _expected_clues(AC_GRID)

    @pytest.mark.parametrize(
        "grid",
        [None, "not a grid", [], [[]], [[True, False], [True]]],
        ids=["none", "string", "empty", "empty-row", "ragged"],
    )
    def test_an_unreadable_stored_grid_is_a_500_not_a_board(self, monkeypatch, grid) -> None:
        panel, puzzle_id = self._raw(monkeypatch, grid)

        response = panel.test_client().get(f"/puzzle/{puzzle_id}/solve")

        assert response.status_code == 500
        body = response.get_data(as_text=True)
        assert "no readable grid" in body
        assert "puzzle-player-data" not in body

    def test_a_database_error_is_not_reported_as_a_missing_puzzle(self, tmp_path, monkeypatch) -> None:
        from sqlalchemy.exc import OperationalError

        panel = _build_app("sqlite", sqlite_session_scope(tmp_path), monkeypatch)
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID)

        def down(_puzzle_id):
            raise OperationalError("SELECT puzzles", {}, Exception("database is down"))

        monkeypatch.setattr(panel.puzzle_review_service, "get_puzzle", down)
        panel.config["TESTING"] = False
        panel.config["PROPAGATE_EXCEPTIONS"] = False

        response = panel.test_client().get(f"/puzzle/{puzzle_id}/solve")

        assert response.status_code == 500
        assert "Page not found" not in response.get_data(as_text=True)


class TestPlayerAssets:
    """ADR-0038/R1, R4, R5, R7 — what ships, and how."""

    def test_every_admin_asset_ships_in_the_wheel(self) -> None:
        """R5: every file under admin/static and admin/templates matches a
        package-data glob, so no built wheel serves a page without its script."""
        manifest = tomllib.loads((_REPO / "pyproject.toml").read_text(encoding="utf-8"))
        globs = manifest["tool"]["setuptools"]["package-data"]["nonogram.admin"]
        files = [
            path.relative_to(_ADMIN).as_posix()
            for folder in ("static", "templates")
            for path in (_ADMIN / folder).iterdir()
            if path.is_file()
        ]
        assert "static/solver.js" in files and "static/solver_state.js" in files
        unshipped = [name for name in files if not any(fnmatch(name, glob) for glob in globs)]
        assert unshipped == []

    def test_pytest_playwright_is_a_dev_only_dependency(self) -> None:
        """R7: declared in the dev extra, never in the runtime set or the admin extra."""
        manifest = tomllib.loads((_REPO / "pyproject.toml").read_text(encoding="utf-8"))

        def names(requirements):
            return {re.split(r"[<>=!~\[ ]", line)[0].lower() for line in requirements}

        extras = manifest["project"]["optional-dependencies"]
        assert "pytest-playwright" in names(extras["dev"])
        assert "pytest-playwright" not in names(manifest["project"]["dependencies"])
        assert "pytest-playwright" not in names(extras["admin"])

    def test_the_scripts_are_served_as_javascript(self, monkeypatch) -> None:
        client = _build_app("memory", None, monkeypatch).test_client()
        for name in ("solver.js", "solver_state.js"):
            response = client.get(f"/static/{name}")
            assert response.status_code == 200, name
            assert response.mimetype == "text/javascript", (name, response.mimetype)

    def test_the_state_module_touches_no_dom(self) -> None:
        """R4: the pure module reaches nothing outside its arguments."""
        code = re.sub(r"//[^\n]*", "", (_STATIC / "solver_state.js").read_text(encoding="utf-8"))
        for name in ("document", "window", "globalThis", "fetch", "localStorage", "import "):
            assert name not in code, name

    def test_the_scripts_carry_no_colour_literals(self) -> None:
        """Colours belong to tokens.css; the scripts only set classes and data."""
        for name in ("solver.js", "solver_state.js"):
            assert not re.search(r"#[0-9a-fA-F]{3,8}\b", (_STATIC / name).read_text(encoding="utf-8")), name


# ==========================================================================
# Browser tests (pytest-playwright + Chromium)
# ==========================================================================

_PLAYWRIGHT_MISSING = (
    "pytest-playwright is not installed, so the puzzle player's browser tests "
    "cannot run. Fix: pip install -e '.[dev]' && playwright install chromium (ADR-0038/R8)"
)


@pytest.fixture(scope="session")
def browser_type(playwright, browser_name):
    """pytest-playwright's fixture, refusing loudly when the browser is absent."""
    browser = getattr(playwright, browser_name)
    if not Path(browser.executable_path).exists():
        pytest.fail(
            f"{browser_name} for Playwright is not installed ({browser.executable_path} "
            f"is missing), so the puzzle player's browser tests cannot run. "
            f"Fix: playwright install {browser_name} (ADR-0038/R8)",
            pytrace=False,
        )
    return browser


@pytest.fixture
def browser_page(request):
    try:
        import pytest_playwright  # noqa: F401
    except ImportError:
        pytest.fail(_PLAYWRIGHT_MISSING, pytrace=False)
    return request.getfixturevalue("page")


@dataclass
class Live:
    url: str
    app: object
    scope: object

    def store(self, grid, **kwargs) -> str:
        return _store(self.app.puzzle_review_service, grid, **kwargs)


@pytest.fixture
def live(tmp_path, monkeypatch):
    """The real panel over SQLite, served on loopback with an ephemeral port."""
    from werkzeug.serving import make_server

    scope = sqlite_session_scope(tmp_path, "card-160-live.db")
    app = _build_app("sqlite", scope, monkeypatch)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield Live(f"http://127.0.0.1:{server.server_port}", app, scope)
    finally:
        server.shutdown()
        thread.join()


def _open(page, live, puzzle_id):
    page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
    page.wait_for_function("window.puzzlePlayer !== undefined")


_DRAWN = """() => {
  const cellsOf = (tr) => [...tr.querySelectorAll('td.player-cell')];
  const rows = [...document.querySelectorAll('.player-board tbody tr')];
  const text = (box) => [...box.querySelectorAll('.player-clue-num')].map((n) => n.textContent);
  return {
    rowLengths: rows.map((tr) => cellsOf(tr).length),
    rowClues: [...document.querySelectorAll('th.player-clue.is-row')].map(text),
    columnClues: [...document.querySelectorAll('th.player-clue.is-col')].map(text),
  };
}"""

_RULES = """() => {
  const px = (el, side) => parseFloat(getComputedStyle(el)[`border${side}Width`]);
  const rows = [...document.querySelectorAll('.player-board tbody tr')];
  const grid = rows.map((tr) => [...tr.querySelectorAll('td.player-cell')]);
  const width = grid[0].length, height = grid.length;
  const colRule = [], rowRule = [];
  for (let c = 0; c < width; c++) colRule.push([...new Set(grid.map((row) => px(row[c], 'Right')))]);
  for (let r = 0; r < height; r++) rowRule.push([...new Set(grid[r].map((cell) => px(cell, 'Bottom')))]);
  return {
    colRule, rowRule,
    colClueRule: [...document.querySelectorAll('th.player-clue.is-col')].map((b) => px(b, 'Right')),
    rowClueRule: [...document.querySelectorAll('th.player-clue.is-row')].map((b) => px(b, 'Bottom')),
    lastCellMajor: grid[height - 1][width - 1].classList.contains('major-right')
                   || grid[height - 1][width - 1].classList.contains('major-below'),
  };
}"""


def _assert_every_fifth_line_heavier(rules, width, height) -> None:
    """Interior line after column c (row r) is heavy iff c+1 (r+1) is a
    multiple of five; heavy is strictly wider than thin; never on the last."""
    for lines, count in ((rules["colRule"], width), (rules["rowRule"], height)):
        assert all(len(widths) == 1 for widths in lines), "a line changes weight along its length"
        interior = [widths[0] for widths in lines[:-1]]
        heavy = {i for i in range(count - 1) if (i + 1) % MAJOR_EVERY == 0}
        thin = set(range(count - 1)) - heavy
        assert {i for i, w in enumerate(interior) if w > min(interior)} == heavy
        assert len({interior[i] for i in thin}) == 1
        if heavy:
            assert min(interior[i] for i in heavy) > max(interior[i] for i in thin)
    # The clue boxes carry the same rules on, into the clue area.
    assert [w > min(rules["colClueRule"]) for w in rules["colClueRule"][:-1]] == [
        (i + 1) % MAJOR_EVERY == 0 for i in range(width - 1)
    ]
    assert [w > min(rules["rowClueRule"]) for w in rules["rowClueRule"][:-1]] == [
        (i + 1) % MAJOR_EVERY == 0 for i in range(height - 1)
    ]
    assert rules["lastCellMajor"] is False


@pytest.mark.browser
class TestSolverPage_ShowsTheCluesInTheBrowser:
    """AC-296 / AC-297 as drawn — TestSolverPage_ShowsTheClues, browser half."""

    def test_TestSolverPage_ShowsTheClues_board_is_15_rows_of_25_cells(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(AC_GRID))

        drawn = browser_page.evaluate(_DRAWN)

        assert drawn["rowLengths"] == [25] * 15

    def test_TestSolverPage_ShowsTheClues_each_of_40_boxes_shows_its_clue(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(AC_GRID))

        drawn = browser_page.evaluate(_DRAWN)

        rows, columns = _expected_clues(AC_GRID)
        assert len(drawn["rowClues"]) + len(drawn["columnClues"]) == 40
        assert drawn["rowClues"] == [[str(n) for n in clue] for clue in rows]
        assert drawn["columnClues"] == [[str(n) for n in clue] for clue in columns]
        assert drawn["rowClues"][2] == ["0"]


@pytest.mark.browser
class TestSolverPage_EmphasisesEveryFifthLine:
    """AC-298 — heavier after columns 5, 10, 15, 20 and rows 5, 10, by computed style."""

    def test_the_25x15_board(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(AC_GRID))

        rules = browser_page.evaluate(_RULES)

        _assert_every_fifth_line_heavier(rules, 25, 15)
        heavy_cols = [c + 1 for c, w in enumerate(rules["colRule"][:-1]) if w[0] > rules["colRule"][0][0]]
        heavy_rows = [r + 1 for r, w in enumerate(rules["rowRule"][:-1]) if w[0] > rules["rowRule"][0][0]]
        assert (heavy_cols, heavy_rows) == ([5, 10, 15, 20], [5, 10])

    def test_PropertyTest_every_size_has_height_rows_of_width_cells_and_fifth_lines_heavier(
        self, browser_page, live
    ) -> None:
        rng = random.Random(298)
        sizes = [(MIN_SIZE, MIN_SIZE), (MAX_SIZE, MAX_SIZE), (MIN_SIZE, MAX_SIZE), (MAX_SIZE, MIN_SIZE),
                 (11, 14), (16, 21), (19, 26)]
        while len(sizes) < 12:
            sizes.append((rng.randint(MIN_SIZE, MAX_SIZE), rng.randint(MIN_SIZE, MAX_SIZE)))
        cases = 0
        for width, height in sizes:
            grid = _unique_grid(width, height, seed=rng.randrange(10**9))
            _open(browser_page, live, live.store(grid))

            assert browser_page.evaluate(_DRAWN)["rowLengths"] == [width] * height
            _assert_every_fifth_line_heavier(browser_page.evaluate(_RULES), width, height)
            cases += 1
        assert cases >= 12


_CELL_LOOK = """() => [...document.querySelectorAll('td.player-cell')].map((cell) => ({
  state: cell.dataset.state,
  background: getComputedStyle(cell).backgroundColor,
  mark: getComputedStyle(cell, '::after').content,
}))"""

_TOKEN_RGB = """(name) => {
  const probe = document.createElement('div');
  probe.style.color = `var(${name})`;
  document.body.append(probe);
  const rgb = getComputedStyle(probe).color;
  probe.remove();
  return rgb;
}"""


@pytest.mark.browser
class TestSolverPage_AllCellsStartUndecided:
    """AC-301 — a fresh 20x20 page: 400 undecided cells in state and on screen."""

    def test_all_400_cells_start_undecided(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(AC301_GRID))

        board = browser_page.evaluate("window.puzzlePlayer.getBoard()")
        look = browser_page.evaluate(_CELL_LOOK)
        paper = browser_page.evaluate(_TOKEN_RGB, "--grid-paper")

        assert (board["width"], board["height"]) == (20, 20)
        assert board["cells"] == ["unknown"] * 400
        assert len(look) == 400
        assert {cell["state"] for cell in look} == {"unknown"}
        assert {cell["background"] for cell in look} == {paper}
        assert {cell["mark"] for cell in look} == {"none"}

    def test_the_board_is_painted_from_state(self, browser_page, live) -> None:
        """The renderer draws whatever the state says — filled as ink, empty
        as a mark, undecided as bare paper — and nothing else changes."""
        _open(browser_page, live, live.store(AC301_GRID))
        ink = browser_page.evaluate(_TOKEN_RGB, "--grid-ink")
        paper = browser_page.evaluate(_TOKEN_RGB, "--grid-paper")

        look = browser_page.evaluate(
            """async (look) => {
              const S = await import('/static/solver_state.js');
              const player = window.puzzlePlayer;
              let board = S.withCell(player.getBoard(), 0, 0, S.FILLED);
              board = S.withCell(board, 19, 19, S.EMPTY);
              player.setBoard(board);
              const marked = eval(look)();
              player.setBoard(S.withCell(board, 0, 0, S.UNKNOWN));
              return { marked, after: eval(look)() };
            }""",
            _CELL_LOOK,
        )

        marked, after = look["marked"], look["after"]
        assert (marked[0]["state"], marked[0]["background"], marked[0]["mark"]) == ("filled", ink, "none")
        assert marked[399]["state"] == "empty" and marked[399]["mark"] != "none"
        assert marked[399]["background"] == paper
        assert {c["state"] for c in marked[1:399]} == {"unknown"}
        assert (after[0]["state"], after[0]["background"]) == ("unknown", paper)
        assert after[399]["state"] == "empty"

    def test_set_board_refuses_a_board_of_another_size(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(AC301_GRID))

        outcome = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const before = window.puzzlePlayer.getBoard();
              let error = null;
              try { window.puzzlePlayer.setBoard(S.withCell(S.createBoard(10, 20), 0, 0, S.FILLED)); }
              catch (e) { error = e.name; }
              return { error, kept: window.puzzlePlayer.getBoard() === before,
                       drawn: document.querySelector('td.player-cell').dataset.state };
            }"""
        )

        assert outcome == {"error": "RangeError", "kept": True, "drawn": "unknown"}


@pytest.mark.browser
class TestSolverStateModule:
    """The pure state module (ADR-0038/R4), driven in the browser it ships to."""

    def test_the_state_module_refuses_bad_input(self, browser_page, live) -> None:
        _open(browser_page, live, live.store(AC_GRID))

        errors = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const board = S.createBoard(3, 2);
              const attempt = (f) => { try { f(); return null; } catch (e) { return e.name; } };
              return {
                zeroWide: attempt(() => S.createBoard(0, 5)),
                fractional: attempt(() => S.createBoard(2.5, 5)),
                notANumber: attempt(() => S.createBoard('3', 5)),
                rowOut: attempt(() => S.cellAt(board, 2, 0)),
                colOut: attempt(() => S.cellAt(board, 0, 3)),
                negative: attempt(() => S.withCell(board, -1, 0, S.FILLED)),
                badState: attempt(() => S.withCell(board, 0, 0, 'crossed')),
                untouched: board.cells.every((c) => c === S.UNKNOWN),
                frozen: Object.isFrozen(board) && Object.isFrozen(board.cells),
                states: S.CELL_STATES,
              };
            }"""
        )

        assert errors == {
            "zeroWide": "RangeError", "fractional": "RangeError", "notANumber": "RangeError",
            "rowOut": "RangeError", "colOut": "RangeError", "negative": "RangeError",
            "badState": "RangeError", "untouched": True, "frozen": True,
            "states": ["unknown", "filled", "empty"],
        }

    def test_PropertyTest_StateModule_WithCellChangesExactlyOneCell(self, browser_page, live) -> None:
        """Over a seeded corpus of boards and edit sequences, every withCell
        yields exactly the Python reference model's board and leaves its input
        board unchanged."""
        _open(browser_page, live, live.store(AC_GRID))
        rng = random.Random(4)
        states = ["unknown", "filled", "empty"]
        cases = []
        for _ in range(60):
            width, height = rng.randint(1, MAX_SIZE), rng.randint(1, MAX_SIZE)
            edits = [(rng.randrange(height), rng.randrange(width), rng.choice(states)) for _ in range(rng.randint(1, 12))]
            cases.append({"width": width, "height": height, "edits": edits})

        results = browser_page.evaluate(
            """async (cases) => {
              const S = await import('/static/solver_state.js');
              return cases.map(({ width, height, edits }) => {
                let board = S.createBoard(width, height);
                const steps = [];
                for (const [row, col, state] of edits) {
                  const before = board.cells.slice();
                  const next = S.withCell(board, row, col, state);
                  steps.push({ inputKept: board.cells.every((c, i) => c === before[i]),
                               cells: next.cells.slice(), read: S.cellAt(next, row, col) });
                  board = next;
                }
                return steps;
              });
            }""",
            cases,
        )

        checked = 0
        for case, steps in zip(cases, results):
            model = ["unknown"] * (case["width"] * case["height"])
            for (row, col, state), step in zip(case["edits"], steps):
                model[row * case["width"] + col] = state
                assert step["inputKept"]
                assert step["cells"] == model
                assert step["read"] == state
                checked += 1
        assert len(cases) >= 60 and checked >= 300


_COUNT_TABLES = ("puzzles", "books", "batches", "generation_history")


def _snapshot(scope):
    from sqlalchemy import text

    with scope() as db:
        counts = {t: db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one() for t in _COUNT_TABLES}
        rows = [tuple(row) for row in db.execute(text("SELECT * FROM puzzles ORDER BY id")).all()]
    return counts, rows


@pytest.mark.browser
class TestSolverPage_WritesNothing:
    """AC-302 — open, 10 strokes, solve: no table's count and no puzzle row changes.

    CARD-160 has no input handling (marking is CARD-161), so the strokes are
    driven through the page's own seam: each stroke is one
    ``puzzlePlayer.setBoard(withCell(...))`` on the live page, and "solves it"
    sets every cell to the payload's solution the same way. CARD-161 replaces
    this with real clicks and drags against the same assertions.
    """

    def test_ten_strokes_and_a_solve_write_nothing(self, browser_page, live) -> None:
        batch_id = make_batch(live.scope)
        make_book(live.scope)
        other = live.store(AC301_GRID)
        puzzle_id = live.store(AC_GRID, batch_id=batch_id)
        before = _snapshot(live.scope)
        assert before[0]["puzzles"] == 2 and before[0]["books"] == 1 and before[0]["batches"] == 1

        _open(browser_page, live, puzzle_id)
        browser_page.wait_for_load_state("networkidle")
        requests = []
        browser_page.on("request", lambda request: requests.append(request.url))

        final = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const player = window.puzzlePlayer;
              const { width, height, solution } = player.payload;
              let strokes = 0;
              for (let k = 0; k < 10; k++) {
                const state = k % 2 ? S.EMPTY : S.FILLED;
                player.setBoard(S.withCell(player.getBoard(), k % height, (3 * k) % width, state));
                strokes++;
              }
              for (let r = 0; r < height; r++)
                for (let c = 0; c < width; c++)
                  player.setBoard(S.withCell(player.getBoard(), r, c, solution[r][c] ? S.FILLED : S.EMPTY));
              return { strokes, cells: player.getBoard().cells,
                       drawn: [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state) };
            }"""
        )

        solved = ["filled" if cell else "empty" for row in AC_GRID for cell in row]
        assert final["strokes"] == 10
        assert final["cells"] == solved and final["drawn"] == solved
        assert requests == []
        assert _snapshot(live.scope) == before
        assert other != puzzle_id


@pytest.mark.browser
class TestPuzzleDetail_OffersSolve:
    """AC-300 — the detail modal holds a "Solve" action to the player."""

    def test_the_modal_links_to_the_player(self, browser_page, live) -> None:
        puzzle_id = live.store(AC_GRID, name="Snowy owl")
        browser_page.goto(f"{live.url}/puzzles")
        browser_page.get_by_role("link", name="Snowy owl", exact=True).first.click()

        solve = browser_page.locator("#puzzleDetailModal").get_by_role("link", name="Solve", exact=True)
        solve.wait_for()

        assert solve.get_attribute("href") == f"/puzzle/{puzzle_id}/solve"
        solve.click()
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        assert browser_page.url == f"{live.url}/puzzle/{puzzle_id}/solve"


_BOX = """() => {
  const r = document.querySelector('.player-board').getBoundingClientRect();
  const stage = document.querySelector('.player-stage');
  return { left: r.left, top: r.top, right: r.right, bottom: r.bottom,
           cell: document.querySelector('td.player-cell').getBoundingClientRect().width,
           pageWidth: document.scrollingElement.scrollWidth, viewport: innerWidth,
           stageScrolls: stage.scrollWidth > stage.clientWidth };
}"""


@pytest.mark.browser
class TestSolverPageFits:
    """Item 3 / failure matrix F12-F13 — the largest board on a laptop and a phone."""

    @pytest.mark.parametrize("deep", ["row-clues", "column-clues"])
    def test_the_largest_board_fits_a_laptop_screen(self, browser_page, live, deep) -> None:
        grid = _unique_grid(MAX_SIZE, MAX_SIZE, seed=30)
        if deep == "column-clues":
            grid = _transposed(grid)
        browser_page.set_viewport_size({"width": 1440, "height": 900})
        _open(browser_page, live, live.store(grid))

        box = browser_page.evaluate(_BOX)

        assert box["left"] >= 0 and box["top"] >= 0
        assert box["right"] <= 1440 and box["bottom"] <= 900, box
        assert box["cell"] >= 14

    def test_a_phone_width_page_never_scrolls_sideways(self, browser_page, live) -> None:
        browser_page.set_viewport_size({"width": 390, "height": 844})
        _open(browser_page, live, live.store(_unique_grid(MAX_SIZE, MAX_SIZE, seed=31)))

        box = browser_page.evaluate(_BOX)

        assert box["pageWidth"] <= box["viewport"], box
        assert box["stageScrolls"] is True


def _embed(text: str):
    """A replacement for _PAYLOAD.sub that embeds ``text`` verbatim."""
    return lambda _match: f'<script type="application/json" id="puzzle-player-data">{text}</script>'


def _rewrite(change):
    """A page corruption: apply ``change`` to the parsed payload, re-embed it."""

    def corrupt(html: str) -> str:
        payload = _payload(html)
        change(payload)
        return _PAYLOAD.sub(_embed(json.dumps(payload)), html)

    return corrupt


@pytest.mark.browser
class TestSolverPageFailures:
    """Failure matrix F8/F9 and the clean-console check."""

    def test_the_player_page_loads_with_a_clean_console(self, browser_page, live) -> None:
        problems = []
        browser_page.on("console", lambda m: m.type in ("error", "warning") and problems.append(m.text))
        browser_page.on("pageerror", lambda e: problems.append(str(e)))
        browser_page.on("requestfailed", lambda r: problems.append(f"failed: {r.url}"))
        browser_page.on(
            "response",
            lambda r: r.url.startswith(live.url) and r.status >= 400 and problems.append(f"{r.status}: {r.url}"),
        )

        _open(browser_page, live, live.store(AC_GRID))
        browser_page.wait_for_load_state("networkidle")

        assert problems == []

    def test_without_the_script_the_fallback_says_so(self, browser_page, live) -> None:
        browser_page.route("**/static/solver.js", lambda route: route.abort())
        browser_page.goto(f"{live.url}/puzzle/{live.store(AC_GRID)}/solve")
        browser_page.wait_for_load_state("networkidle")

        fallback = browser_page.locator("[data-player-fallback]")
        assert fallback.is_visible()
        assert "did not load" in fallback.inner_text()
        assert browser_page.locator(".player-board").count() == 0

    @pytest.mark.parametrize(
        "corrupt, reason",
        [
            (lambda html: _PAYLOAD.sub(_embed('{"width": 25,'), html), "not JSON"),
            (lambda html: _PAYLOAD.sub("", html), "no puzzle data"),
            (lambda html: _PAYLOAD.sub(_embed("null"), html), "does not describe"),
            (_rewrite(lambda p: p.update(height=14)), "does not describe"),
            (_rewrite(lambda p: p.update(width="25")), "does not describe"),
            (_rewrite(lambda p: p.update(width=0, columns=[], solution=[[] for _ in range(15)])), "does not describe"),
            (_rewrite(lambda p: p["rows"].__setitem__(0, [-1])), "does not describe"),
            (_rewrite(lambda p: p["columns"].__setitem__(0, [])), "does not describe"),
            (_rewrite(lambda p: p["rows"].__setitem__(1, [1.5])), "does not describe"),
            (_rewrite(lambda p: p["solution"][0].__setitem__(0, 1)), "does not describe"),
            (_rewrite(lambda p: p["solution"][0].pop()), "does not describe"),
        ],
        ids=["not-json", "absent", "null", "height-off", "width-text", "width-zero",
             "negative-clue", "empty-clue", "fractional-clue", "solution-not-bool", "solution-short-row"],
    )
    def test_an_unreadable_payload_shows_an_alert_not_a_board(self, browser_page, live, corrupt, reason) -> None:
        puzzle_id = live.store(AC_GRID)

        def serve_corrupted(route):
            response = route.fetch()
            route.fulfill(response=response, body=corrupt(response.text()))

        browser_page.route(f"**/puzzle/{puzzle_id}/solve", serve_corrupted)
        errors = []
        browser_page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        alert = browser_page.get_by_role("alert")
        alert.wait_for()

        assert reason in alert.inner_text()
        assert browser_page.locator(".player-board").count() == 0
        assert browser_page.evaluate("window.puzzlePlayer === undefined")
        assert len(errors) == 1 and reason in errors[0]
