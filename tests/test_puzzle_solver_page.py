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
    """Item 3 (CARD-160), as CARD-163 changed it: "Puzzle <width>×<height>" and
    the tier — the picture name is the answer, so only the solved banner says it."""

    def test_header_reads_puzzle_size_and_the_tier(self, panel) -> None:
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID, tier="medium", name="Snowy owl")

        html = _page(panel, puzzle_id)

        assert re.search(r"<h1>\s*Puzzle 25×15\s*</h1>", html)
        assert re.search(r'<span class="player-tier"><span class="badge tier"[^>]*>MEDIUM</span>', html)

    def test_header_reads_a_display_label_tier_too(self, panel) -> None:
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID, tier="Hard")

        assert ">HARD</span>" in _page(panel, puzzle_id)

    def test_header_without_a_tier_shows_no_chip(self, panel) -> None:
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID, tier="")

        html = _page(panel, puzzle_id)

        assert "player-tier" not in html
        assert _tab_title(html) == "Puzzle 25×15 - Nonogram admin"

    def test_the_banner_falls_back_to_source_then_id_and_the_header_never_shows_either(self, panel) -> None:
        service = panel.puzzle_review_service
        from_source = _store(service, AC_GRID, source="heron.png")
        from_id = _store(service, AC_GRID, source=None)

        for puzzle_id, shown in ((from_source, "heron.png"), (from_id, from_id[:8])):
            html = _page(panel, puzzle_id)
            assert _banner_name(html) == shown
            assert shown not in _header_text(html)
            assert shown not in _tab_title(html)


_HEADER = re.compile(r'<div class="page-head player-head">(.*?)</div>', re.S)
_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
_BANNER_NAME = re.compile(r"<strong[^>]*data-player-solved-name[^>]*>(.*?)</strong>", re.S)


def _text(fragment: str) -> str:
    """What a reader sees of an HTML fragment: tags dropped, spaces collapsed."""
    return " ".join(re.sub(r"<[^>]+>", " ", fragment).split())


def _header_text(html: str) -> str:
    match = _HEADER.search(html)
    assert match, "the player page has no header"
    return _text(match.group(1))


def _tab_title(html: str) -> str:
    match = _TITLE.search(html)
    assert match, "the player page has no <title>"
    return _text(match.group(1))


def _banner_name(html: str) -> str:
    match = _BANNER_NAME.search(html)
    assert match, "the player page has no solved banner name"
    return _text(match.group(1))


#: A picture name no size, tier, fixture or page text can contain by accident.
SECRET_NAME = "Quokka lantern"
SECRET_SOURCE = "quokka-lantern.png"


class TestSolverPage_HidesThePictureNameUntilSolved:
    """FR-044 AC-322 / AC-323 (CARD-163): the name is the answer.

    Before the puzzle is solved the header and the tab title show the size and
    the tier; the solved banner (hidden until solved, CARD-162) is the only
    place the page shows the name. Each negative check is paired with a
    positive one on the same page — the name *is* in the banner — so an
    absence cannot pass because the fixture never had a name.
    """

    def test_ac322_neither_the_header_nor_the_tab_title_contains_the_name(self, panel) -> None:
        puzzle_id = _store(
            panel.puzzle_review_service, AC_GRID, tier="medium", name=SECRET_NAME, source=SECRET_SOURCE
        )

        html = _page(panel, puzzle_id)

        assert _banner_name(html) == SECRET_NAME  # the fixture's name is real
        assert re.search(r'id="puzzle-player-solved" hidden', html)  # and unshown until solved
        for shown in (_header_text(html), _tab_title(html)):
            assert SECRET_NAME.lower() not in shown.lower()
            assert "quokka" not in shown.lower()  # nor the file it came from

    def test_ac323_the_header_shows_25x15_and_medium_in_place_of_the_name(self, panel) -> None:
        """The size is "25×15" with the multiplication sign U+00D7, never the
        letter "x" (width first, ADR-0022/R1; AC-323 as amended 2026-10-04,
        CARD-166). The tier badge renders the stored tier upper-cased
        ("MEDIUM", the admin badge's spelling), so the tier is compared
        case-insensitively — and pinned exactly as rendered."""
        puzzle_id = _store(panel.puzzle_review_service, AC_GRID, tier="medium", name=SECRET_NAME)

        html = _page(panel, puzzle_id)

        header = _header_text(html)
        assert "25\u00d715" in header  # U+00D7 MULTIPLICATION SIGN
        for shown in (header, _tab_title(html)):
            assert "25x15" not in shown.lower()
        assert "medium" in header.lower().split()
        assert header == "Puzzle 25×15 MEDIUM"
        assert _tab_title(html) == "Puzzle 25×15 · MEDIUM - Nonogram admin"

    @pytest.mark.browser
    def test_the_drawn_page_keeps_the_name_out_of_the_header_until_the_banner_reveals_it(
        self, browser_page, live
    ) -> None:
        """solver.js rewrites neither the header nor the tab title: they read
        the same after the board is drawn and after it is solved, while the
        banner appears with the name."""
        _open(browser_page, live, live.store(AC_GRID, tier="medium", name=SECRET_NAME))
        head = browser_page.locator(".player-head")
        banner = browser_page.locator("#puzzle-player-solved")

        assert not banner.is_visible()
        assert " ".join(head.inner_text().split()) == "Puzzle 25×15 MEDIUM"
        assert browser_page.title() == "Puzzle 25×15 · MEDIUM - Nonogram admin"

        browser_page.evaluate(
            """async (solution) => {
              const S = await import('/static/solver_state.js');
              const { width, height } = window.puzzlePlayer.payload;
              const cells = solution.flat().map((filled) => (filled ? S.FILLED : S.EMPTY));
              window.puzzlePlayer.setBoard(Object.freeze({ width, height, cells: Object.freeze(cells) }));
            }""",
            AC_GRID,
        )

        assert banner.is_visible()
        assert SECRET_NAME in banner.inner_text()
        assert " ".join(head.inner_text().split()) == "Puzzle 25×15 MEDIUM"
        assert browser_page.title() == "Puzzle 25×15 · MEDIUM - Nonogram admin"


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

        # `1 == True` in Python, so equality alone would pass on ints too; the
        # renderer's isSolution refuses anything but JSON booleans.
        assert payload["solution"] == AC_GRID
        assert all(type(cell) is bool for row in payload["solution"] for cell in row)
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


#: CARD-235, AC-4. Which page-isolation category each of the
#: ``tests/test_puzzle_solver_*.py`` files is in, and why — stated here, beside
#: the fixture that implements it, so that a file's isolation is a declaration
#: somebody has to change on purpose rather than a side effect of whichever
#: fixture happened to be in scope.
#:
#: Two categories:
#:
#: * ``own-page`` — the file's tests get a fresh Chromium page each
#:   (``browser_page`` below is function-scoped, as is ``live``).
#: * ``shared-page`` — the file's tests share one page, reset between tests.
#:
#: **Every file is ``own-page``, and that was chosen on measurement.** CARD-217
#: read the family's 0.33 s per-test teardown as the price of Chromium's page
#: lifecycle. It is not. One ``new_context`` + ``new_page`` + close costs 57 ms
#: on this host (20 iterations against a launched Chromium), so collapsing the
#: page lifecycle for all 422 tests is worth ~24 s — 2.6 % of the suite. The
#: teardown was the ``live`` server's stop (see :data:`_SERVE_POLL_INTERVAL_S`):
#: 118 s of teardown, and free of any isolation risk. Sharing a page would buy
#: a fifth of the saving for the whole of the order-dependence risk, so no file
#: was converted.
#:
#: The reasons below are what each file would have to undo to become
#: convertible, and they are not hypothetical: ``page.on("console")`` /
#: ``page.on("pageerror")`` handlers and ``page.route`` interceptors accumulate
#: on a page and are not undone by navigating, so on a shared page a later
#: test's console output lands in an earlier test's list — cross-talk that
#: reports as green.
PAGE_ISOLATION: dict[str, tuple[str, str]] = {
    "test_puzzle_solver_brush_menu.py": (
        "own-page",
        "reloads the page mid-test to assert the chosen brush survives a "
        "reload, so it depends on the page's own navigation history",
    ),
    "test_puzzle_solver_clues.py": (
        "own-page",
        "sets the viewport 29 times across its cases; a viewport left behind "
        "silently changes which layout the next test's board chooses",
    ),
    "test_puzzle_solver_crosshair.py": (
        "own-page",
        "sets the viewport for its doubled-gutter and redraw boards, installs "
        "a context request listener to prove no hover asks for anything, and "
        "reads localStorage to prove no hover saves anything",
    ),
    "test_puzzle_solver_fifth_rule.py": (
        "own-page",
        "sets the viewport for its desktop and phone samples, and injects "
        "<style> elements that force the filled cell's hairline off (and onto "
        "every cell) which stay in the document for anything sharing the page",
    ),
    "test_puzzle_solver_hint.py": (
        "own-page",
        "sets the viewport and installs a page listener to watch for console "
        "problems, which would accumulate across tests on a shared page",
    ),
    "test_puzzle_solver_marking.py": (
        "own-page",
        "installs page.route interceptors (a corrupted payload, an aborted "
        "solver.js), a context request listener and four page listeners, and "
        "reloads; none of that is undone by navigating",
    ),
    "test_puzzle_solver_maybe.py": (
        "own-page",
        "sets the viewport and installs a page listener, and carries the "
        "family's longest test (30.9 s of call) whose state no reset describes",
    ),
    "test_puzzle_solver_mirror.py": (
        "own-page",
        "crosses the phone/desktop breakpoint by viewport and asserts marks, "
        "undo/redo and the localStorage save survive the crossing — that save "
        "is exactly the state a reset would have to erase",
    ),
    "test_puzzle_solver_page.py": (
        "own-page",
        "defines these fixtures; installs page.route interceptors and request, "
        "console, pageerror and requestfailed listeners, and sets the viewport "
        "to both 1440x900 and 390x844",
    ),
    "test_puzzle_solver_percent.py": (
        "own-page",
        "reloads to assert the percentage is restored, and installs a console "
        "listener",
    ),
    "test_puzzle_solver_phone.py": (
        "own-page",
        "is entirely about the 390x844 phone viewport: it sets it eight times "
        "and its assertions are computed-style readings of that viewport",
    ),
    "test_puzzle_solver_probe.py": (
        "own-page",
        "installs a context request listener to prove the probe's controls ask "
        "for nothing, and a page listener for console problems; neither is "
        "undone by navigating",
    ),
    "test_puzzle_solver_progress.py": (
        "own-page",
        "reads and writes the localStorage save six times and installs six "
        "page listeners",
    ),
    "test_puzzle_solver_resume.py": (
        "own-page",
        "is the resume feature's test: it writes, corrupts and restores the "
        "localStorage save eight times and reloads to prove it restores",
    ),
    "test_puzzle_solver_zoom.py": (
        "own-page",
        "sets the viewport 20 times, persists the zoom level to localStorage "
        "and reloads to prove the zoom is restored",
    ),
}

#: The only two categories :data:`PAGE_ISOLATION` may name.
PAGE_ISOLATION_CATEGORIES = ("own-page", "shared-page")


@pytest.fixture
def browser_page(request):
    """A fresh Chromium page per test (``own-page``; see :data:`PAGE_ISOLATION`)."""
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


#: How often this fixture's serve loop checks whether it has been asked to
#: stop. Same reason as ``tests/test_web_server.py``'s ``_POLL_INTERVAL_S``:
#: ``socketserver.serve_forever``'s stdlib default is 0.5 s, and ``shutdown()``
#: cannot return until the loop next wakes up, so the default is a uniform
#: 0–0.5 s wait paid on *every* test's teardown. The server here is never asked
#: to be responsive, only to stop promptly. Nothing any test of this family can
#: observe changes either way: ``shutdown()`` + ``join()`` mean the server is
#: stopped before the fixture returns, whatever the interval — which is why
#: ``tests/test_browser_fixture_scope.py``'s
#: ``TestBrowserFixtures_ThePollIntervalIsStillApplied`` exists. It drives this
#: fixture by hand and fails if the ``poll_interval`` kwarg below stops being
#: passed, or stops being well under the stdlib 0.5 s, because nothing else in
#: the suite would notice.
#:
#: CARD-235. That wait is the 0.33 s per test — 137.97 s, 96 % of the whole
#: suite's teardown — which CARD-217's profile attributed to Chromium's page
#: lifecycle. The profile's own evidence says so in hindsight: teardown was
#: bimodal with the mass at 0.3–0.5 s and "no tail at all, stopping dead at
#: 0.520 s", which is the signature of a bounded poll wait and not of a browser
#: teardown. The near-zero cluster is the family's non-browser tests, which
#: never ask for ``live``.
#:
#: **0.05 s, not the 0.01 s this fixture's neighbour uses, and the difference
#: was measured rather than assumed.** A solo back-to-back A/B over all twelve
#: files (``meta/profiling/card-235-poll-interval-ab.txt``) says:
#:
#: == ===========  ========  =========  ==========
#:    poll            total       call    teardown
#: == ===========  ========  =========  ==========
#:    0.5 (stdlib)  507.80 s   345.20 s    129.93 s
#:    **0.05**      283.37 s   246.11 s     11.88 s
#:    0.01          372.34 s   339.08 s      3.69 s
#: == ===========  ========  =========  ==========
#:
#: 0.01 s buys 8 s more teardown and costs **93 s of call**: a thread waking
#: 100 times a second takes the GIL from a main thread that is driving Chromium
#: through synchronous RPC, and every handoff lands in the middle of a round
#: trip. At 20 Hz that cost is gone and 91 % of the teardown saving remains.
#: ``test_web_server.py`` can afford 0.01 s because nothing there runs a browser
#: on the other side of the GIL — which is why this is a constant per file and
#: not one shared between them.
_SERVE_POLL_INTERVAL_S = 0.05


@pytest.fixture
def live(tmp_path, monkeypatch):
    """The real panel over SQLite, served on loopback with an ephemeral port."""
    from werkzeug.serving import make_server

    scope = sqlite_session_scope(tmp_path, "card-160-live.db")
    app = _build_app("sqlite", scope, monkeypatch)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": _SERVE_POLL_INTERVAL_S},
        daemon=True,
    )
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
  // One entry per clue GUTTER (CARD-212: a big board can draw two per axis,
  // left+right or top+bottom), each a list of that gutter's boxes in line
  // order, read from the box's own data-line rather than from DOM order.
  // Flattening them instead would compare 2 * height boxes against the
  // height - 1 pattern below and fail on a doubled board.
  const gutters = (selector, side) => {
    const found = [], seen = new Map();
    for (const box of document.querySelectorAll(selector)) {
      const line = Number(box.dataset.line);
      const gutter = seen.get(line) ?? 0;
      seen.set(line, gutter + 1);
      (found[gutter] ??= [])[line] = px(box, side);
    }
    return found;
  };
  return {
    colRule, rowRule,
    colClueRule: gutters('th.player-clue.is-col', 'Right'),
    rowClueRule: gutters('th.player-clue.is-row', 'Bottom'),
    lastCellMajor: grid[height - 1][width - 1].classList.contains('major-right')
                   || grid[height - 1][width - 1].classList.contains('major-below'),
  };
}"""


def _assert_every_fifth_line_heavier(rules, width, height) -> None:
    """Interior line after column c (row r) is heavy iff c+1 (r+1) is a
    multiple of five; heavy is strictly wider than thin; never on the last.

    The clue rules are checked per gutter (CARD-212): a big board repeats its
    clues on the far side of an axis, and the pattern must read the same in
    every gutter it draws — one is the old behaviour, so this stays the same
    check on boards that draw one.
    """
    for lines, count in ((rules["colRule"], width), (rules["rowRule"], height)):
        assert all(len(widths) == 1 for widths in lines), "a line changes weight along its length"
        interior = [widths[0] for widths in lines[:-1]]
        heavy = {i for i in range(count - 1) if (i + 1) % MAJOR_EVERY == 0}
        thin = set(range(count - 1)) - heavy
        assert {i for i, w in enumerate(interior) if w > min(interior)} == heavy
        assert len({interior[i] for i in thin}) == 1
        if heavy:
            assert min(interior[i] for i in heavy) > max(interior[i] for i in thin)
    # The clue boxes carry the same rules on, into the clue area — in every
    # gutter the board draws (1, or 2 on a doubled axis).
    for gutters, count in ((rules["colClueRule"], width), (rules["rowClueRule"], height)):
        assert 1 <= len(gutters) <= 2, gutters
        for gutter in gutters:
            assert len(gutter) == count, gutter
            assert [w > min(gutter) for w in gutter[:-1]] == [
                (i + 1) % MAJOR_EVERY == 0 for i in range(count - 1)
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
        # (20, 12) is CARD-212's: at this file's default 1280 x 720 viewport
        # it is one of the sizes whose row clues are DOUBLED, so the corpus
        # covers a board with two gutters per axis instead of missing that
        # band — the twelve sizes it joins all draw a single gutter here
        # (CARD-212's review cycle 1 replayed the whole corpus to check).
        # The five random SIZES are the five they always were (the tail is
        # drawn from the same rng state); the GRIDS after this insertion are
        # not, since each case draws its own seed in the loop below and
        # there is now one more case to draw for. The `doubled` count keeps
        # the one property that matters honest if a size ever moves.
        sizes = [(MIN_SIZE, MIN_SIZE), (MAX_SIZE, MAX_SIZE), (MIN_SIZE, MAX_SIZE), (MAX_SIZE, MIN_SIZE),
                 (11, 14), (16, 21), (19, 26), (20, 12)]
        while len(sizes) < 13:
            sizes.append((rng.randint(MIN_SIZE, MAX_SIZE), rng.randint(MIN_SIZE, MAX_SIZE)))
        cases, doubled = 0, 0
        for width, height in sizes:
            grid = _unique_grid(width, height, seed=rng.randrange(10**9))
            _open(browser_page, live, live.store(grid))

            assert browser_page.evaluate(_DRAWN)["rowLengths"] == [width] * height
            rules = browser_page.evaluate(_RULES)
            _assert_every_fifth_line_heavier(rules, width, height)
            doubled += len(rules["rowClueRule"]) == 2 or len(rules["colClueRule"]) == 2
            cases += 1
        assert cases >= 13
        assert doubled >= 1, "no size in the corpus draws a second gutter, so that path is unchecked"


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

    def test_set_board_refuses_a_value_that_is_not_a_board(self, browser_page, live) -> None:
        """F17: right dimensions or not, a value outside isBoard's declared
        definition is refused before it is painted — so the page never shows a
        ``data-state="undefined"`` cell (F-009: a frozen cells array with holes
        used to pass ``cells.every`` and paint exactly that). One row per
        clause of the definition; each must also be refused by isBoard itself
        (F-010: the side clause is masked through setBoard by the payload
        dimension check, so it is asserted on isBoard directly)."""
        _open(browser_page, live, live.store(AC301_GRID))

        outcome = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const player = window.puzzlePlayer;
              const before = player.getBoard();
              const good = S.withCell(before, 0, 0, S.FILLED);
              const F = Object.freeze;
              const filled = (n, state) => F(new Array(n).fill(state));
              const board = (cells, extra = {}) => F({ width: 20, height: 20, cells, ...extra });
              const holeAt = (i) => { const c = good.cells.slice(); delete c[i]; return F(c); };
              const stateAt = (i, v) => { const c = good.cells.slice(); c[i] = v; return F(c); };
              const getterCell = () => {
                const c = good.cells.slice();
                Object.defineProperty(c, 5, { get: () => S.FILLED, enumerable: true });
                return F(c);
              };
              const sides = (width, height, n) => F({ width, height, cells: filled(n, S.UNKNOWN) });
              const bad = {
                allHoles: board(F(new Array(400))),
                holeAtStart: board(holeAt(0)),
                holeInMiddle: board(holeAt(200)),
                holeAtEnd: board(holeAt(399)),
                arrayLikeCells: board(F(Object.assign({ length: 400 }, good.cells))),
                unfrozenCells: board(good.cells.slice()),
                unfrozenBoard: { ...good },
                widthZero: sides(0, 20, 0),
                sidesNegative: sides(-20, -20, 400),
                widthFractional: sides(2.5, 160, 400),
                heightFractional: sides(160, 2.5, 400),
                widthNaN: sides(NaN, 20, 400),
                widthInfinity: sides(Infinity, 20, 400),
                widthString: sides('20', 20, 400),
                heightString: sides(20, '20', 400),
                widthMissing: F({ height: 20, cells: good.cells }),
                heightMissing: F({ width: 20, cells: good.cells }),
                cellsMissing: F({ width: 20, height: 20 }),
                widthGetter: F({ get width() { return 20; }, height: 20, cells: good.cells }),
                inheritedBoard: F(Object.create(good)),
                cellGetter: board(getterCell()),
                lengthShort: board(filled(399, S.FILLED)),
                lengthLong: board(filled(401, S.FILLED)),
                sidesDoNotMultiply: F({ width: 20, height: 21, cells: good.cells }),
                stateCapitalised: board(stateAt(7, 'Filled')),
                stateNull: board(stateAt(7, null)),
                stateUndefined: board(stateAt(7, undefined)),
                stateNumber: board(stateAt(7, 1)),
                stateUnknownWord: board(filled(400, 'crossed')),
                aFunction: F(Object.assign(function () {}, { width: 20, height: 20, cells: good.cells })),
                isNull: null,
                isUndefined: undefined,
                isNumber: 400,
              };
              const drawn = () => [...new Set(
                [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state))];
              const attempt = (value) => {
                let error = null;
                try { player.setBoard(value); } catch (e) { error = e.name; }
                return error;
              };
              const refused = {};
              for (const [name, value] of Object.entries(bad)) {
                const error = attempt(value);
                refused[name] = { error, isBoard: S.isBoard(value),
                                  kept: player.getBoard() === before, drawn: drawn() };
              }
              // Other own properties are not checked: such a value is a board,
              // and the player keeps a copy without them.
              const withExtra = F({ ...good, note: 'ignored' });
              const extraError = attempt(withExtra);
              const kept = player.getBoard();
              const accepted = {
                madeBoards: S.isBoard(before) && S.isBoard(good),
                extra: [S.isBoard(withExtra), extraError, kept !== withExtra,
                        S.isBoard(kept), 'note' in kept,
                        JSON.stringify(kept.cells) === JSON.stringify(good.cells), drawn().sort()],
              };
              return { refused, accepted };
            }"""
        )

        expected = {"error": "RangeError", "isBoard": False, "kept": True, "drawn": ["unknown"]}
        refused = outcome["refused"]
        assert len(refused) >= 33
        assert {name: row for name, row in refused.items() if row != expected} == {}
        assert outcome["accepted"] == {
            "madeBoards": True,
            "extra": [True, None, True, True, False, True, ["filled", "unknown"]],
        }

    def test_set_board_keeps_and_paints_its_own_copy(self, browser_page, live) -> None:
        """F17 / F-011: setBoard stores and paints a fresh frozen copy of the
        board it accepted — getBoard() is never the caller's object, yet equals
        it cell for cell, side for side, and is itself a board."""
        _open(browser_page, live, live.store(AC301_GRID))

        outcome = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const player = window.puzzlePlayer;
              let given = S.withCell(player.getBoard(), 0, 0, S.FILLED);
              given = S.withCell(given, 19, 19, S.EMPTY);
              given = S.withCell(given, 7, 3, S.FILLED);
              player.setBoard(given);
              const kept = player.getBoard();
              return {
                same: kept === given,
                sameCells: kept.cells === given.cells,
                sides: [kept.width, kept.height],
                cells: kept.cells.slice(),
                given: given.cells.slice(),
                frozen: Object.isFrozen(kept) && Object.isFrozen(kept.cells),
                isBoard: S.isBoard(kept),
                drawn: [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state),
              };
            }"""
        )

        assert outcome["same"] is False, "getBoard() returned the object passed to setBoard"
        assert outcome["sameCells"] is False
        assert outcome["sides"] == [20, 20]
        assert outcome["cells"] == outcome["given"]
        assert len(outcome["cells"]) == 400
        assert outcome["frozen"] is True
        assert outcome["isBoard"] is True
        assert outcome["drawn"] == outcome["given"]


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
            "states": ["unknown", "filled", "empty", "maybe"],
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
                               frozen: Object.isFrozen(next) && Object.isFrozen(next.cells),
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
                assert step["frozen"], "withCell returned a board that is not frozen"
                assert step["cells"] == model
                assert step["read"] == state
                checked += 1
        assert len(cases) >= 60 and checked >= 300


    def test_with_cell_builds_its_cells_by_index_not_by_slice(self, browser_page, live) -> None:
        """F-011: withCell builds the new cells Array index by index. A board
        whose frozen cells Array carries an own ``constructor`` with a
        ``Symbol.species`` (which ``slice()`` would consult) or an own ``slice``
        that throws is still a board, and withCell on it returns a board with
        exactly the expected cells."""
        _open(browser_page, live, live.store(AC_GRID))

        outcome = browser_page.evaluate(
            """async () => {
              const S = await import('/static/solver_state.js');
              const base = S.withCell(S.createBoard(3, 2), 1, 2, S.FILLED);
              const cellsWith = (props) => Object.freeze(Object.assign(base.cells.slice(), props));
              class NotAnArray { constructor() { return {}; } }
              const variants = {
                species: cellsWith({ constructor: { [Symbol.species]: NotAnArray } }),
                throwingSlice: cellsWith({ slice() { throw new Error('slice was called'); } }),
              };
              const out = {};
              for (const [name, cells] of Object.entries(variants)) {
                const board = Object.freeze({ width: 3, height: 2, cells });
                let next = null, error = null;
                try { next = S.withCell(board, 0, 1, S.EMPTY); } catch (e) { error = e.message; }
                out[name] = {
                  inputIsBoard: S.isBoard(board), error,
                  resultIsBoard: next !== null && S.isBoard(next),
                  cells: next && Array.isArray(next.cells) ? Array.from(next.cells) : null,
                };
              }
              return out;
            }"""
        )

        expected_cells = ["unknown", "empty", "unknown", "unknown", "unknown", "filled"]
        for name in ("species", "throwingSlice"):
            assert outcome[name] == {"inputIsBoard": True, "error": None, "resultIsBoard": True,
                                     "cells": expected_cells}, name

    def test_PropertyTest_StateModule_IsBoardIsExactlyTheDeclaration(self, browser_page, live) -> None:
        """F17 / F-009: over a seeded corpus, every board built by createBoard
        and any sequence of withCell is accepted by isBoard, and every single
        corruption of one of those boards — one per clause of isBoard's
        declared definition — is refused."""
        _open(browser_page, live, live.store(AC_GRID))
        rng = random.Random(160)
        states = ["unknown", "filled", "empty"]
        kinds = ["hole", "badState", "short", "long", "unfrozenBoard", "unfrozenCells",
                 "arrayLike", "widthOff", "cellGetter", "inherited"]
        cases = []
        for n in range(240):
            width, height = rng.randint(1, MAX_SIZE), rng.randint(1, MAX_SIZE)
            edits = [(rng.randrange(height), rng.randrange(width), rng.choice(states))
                     for _ in range(rng.randint(0, 15))]
            cases.append({"width": width, "height": height, "edits": edits,
                          "kind": kinds[n % len(kinds)], "index": rng.randrange(width * height),
                          "badState": rng.randrange(7), "extra": rng.choice(states)})

        results = browser_page.evaluate(
            """async (cases) => {
              const S = await import('/static/solver_state.js');
              const F = Object.freeze;
              const badStates = ['Filled', null, undefined, 1, '', 'crossed', 'UNKNOWN'];
              const corrupt = (b, { kind, index, badState, extra }) => {
                const c = b.cells.slice();
                const at = (cells) => F({ width: b.width, height: b.height, cells });
                switch (kind) {
                  case 'hole': delete c[index]; return at(F(c));
                  case 'badState': c[index] = badStates[badState]; return at(F(c));
                  case 'short': c.pop(); return at(F(c));
                  case 'long': c.push(extra); return at(F(c));
                  case 'unfrozenBoard': return { width: b.width, height: b.height, cells: b.cells };
                  case 'unfrozenCells': return at(c);
                  case 'arrayLike': return at(F(Object.assign({ length: c.length }, c)));
                  case 'widthOff': return F({ width: b.width + 1, height: b.height, cells: b.cells });
                  case 'cellGetter': {
                    const v = c[index];
                    Object.defineProperty(c, index, { get: () => v, enumerable: true });
                    return at(F(c));
                  }
                  case 'inherited': return F(Object.create(b));
                }
                throw new Error(`no corruption ${kind}`);
              };
              return cases.map((one) => {
                let board = S.createBoard(one.width, one.height);
                let allBoards = S.isBoard(board);
                let boards = 1;
                for (const [row, col, state] of one.edits) {
                  board = S.withCell(board, row, col, state);
                  allBoards = allBoards && S.isBoard(board);
                  boards += 1;
                }
                return { allBoards, boards, corruptIsBoard: S.isBoard(corrupt(board, one)) };
              });
            }""",
            cases,
        )

        accepted = refused = 0
        per_kind = {kind: 0 for kind in kinds}
        for case, result in zip(cases, results, strict=True):
            assert result["allBoards"], f"a made board was refused: {case}"
            assert result["corruptIsBoard"] is False, f"a corrupted board was accepted: {case}"
            accepted += result["boards"]
            refused += 1
            per_kind[case["kind"]] += 1
        assert len(cases) >= 200 and accepted >= 1000 and refused >= 200
        assert min(per_kind.values()) >= 20, per_kind


_WATCHED_TABLES = ("puzzles", "books", "batches", "generation_history")


def _snapshot(scope):
    """Every row of every watched table, so an INSERT, a DELETE and an UPDATE
    all show up as a difference (each table is seeded with at least one row)."""
    from sqlalchemy import text

    with scope() as db:
        return {
            table: [tuple(row) for row in db.execute(text(f"SELECT * FROM {table} ORDER BY id")).all()]
            for table in _WATCHED_TABLES
        }


def _seed_history(scope, puzzle_id: str) -> None:
    import uuid

    from nonogram.db.models import GenerationHistory

    with scope() as db:
        db.add(GenerationHistory(puzzle_id=uuid.UUID(puzzle_id), image_url="owl.png"))


@pytest.mark.browser
class TestSolverPage_WritesNothing:
    """AC-302 — open, 10 strokes, solve: no row of puzzles, books, batches or generation_history changes.

    CARD-160 has no input handling (marking is CARD-161), so the strokes are
    driven through the page's own seam: each stroke is one
    ``puzzlePlayer.setBoard(withCell(...))`` on the live page, and "solves it"
    sets every cell to the payload's solution the same way. CARD-161 replaces
    this with real clicks and drags against the same assertions.
    """

    def test_ten_strokes_and_a_solve_write_nothing(self, browser_page, live) -> None:
        batch_id = make_batch(live.scope)
        make_book(live.scope)
        live.store(AC301_GRID)  # a second puzzle row, so a write to the wrong row shows too
        puzzle_id = live.store(AC_GRID, batch_id=batch_id)
        _seed_history(live.scope, puzzle_id)
        before = _snapshot(live.scope)
        assert {table: len(rows) for table, rows in before.items()} == {
            "puzzles": 2, "books": 1, "batches": 1, "generation_history": 1,
        }

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
        """AC-11 (CARD-193, rewritten 2026-10-07). The name is the hard,
        unconditional guarantee: the PAGE never scrolls sideways, whatever
        ``.player-stage`` does. ``stageScrolls`` stays ``True`` here
        unedited — not the earlier draft's anticipated flip to ``False`` —
        because this seeded MAX_SIZE grid meets AC-1's named condition for a
        stage-level scroll (its row-clue band width plus its columns at
        CARD-196's numeral floor exceeds the 358 px stage, here via a
        two-digit column number rather than a deep row clue; either route
        trips the same named condition), which the rewritten AC-11 scopes
        its stage-level claim to, carrying forward the owner's final ruling
        ("where a board cannot fit at 12 px, it scrolls sideways").
        tests/test_puzzle_solver_phone.py TestSolverPhone_BoardFitsThePhoneWidth
        measures this mechanism directly, against an independent formula,
        rather than one fixed grid's coincidence, and
        TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit
        demonstrates AC-1's unconditional counterpart for a board that stays
        inside the named condition."""
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
