"""CARD-246 — the manual puzzle editor's UI (the client half of CARD-245).

The *editor* is the page at ``GET /puzzle/<id>/editor``: the owner paints a
stored puzzle's grid by hand, presses Save, reads the recomputed difficulty,
and Approves or Cancels. The two routes it posts to are CARD-245's and are
tested in ``tests/test_puzzle_edit_routes.py`` /
``tests/test_puzzle_edit_store.py``; what is new here is the page, the Edit
controls that reach it, and the save flow in ``static/puzzle_edit.js``.

Two tiers, as ADR-0038 decides and the player's own files already do:

* **Server tests** (Flask test client, in-memory store): the route, its 404
  and its 409, the embedded payload — the page's contract with
  ``static/solver.js`` — and the Edit control on a server-rendered list row.
  Fast, and they cannot skip.
* **Browser tests** (``@pytest.mark.browser``, pytest-playwright + Chromium,
  ADR-0038/R7/R8): everything only a browser can see — the board drawn from
  the stored grid, real clicks, the message, Approve, Cancel, what the store
  holds at each step, and the editor's own card-level entry point, which the
  detail modal builds in JavaScript. Without Chromium these FAIL loudly
  rather than skipping (the fixtures are the player's own, which already
  refuse that way).

**AC-6's rule, stated as the AC requires.** The rule implemented and asserted
here is **"the save is refused and names the undecided cells"**, not "those
brushes are unavailable in edit mode". The editor's menu does leave Maybe and
Undecided out — ``TestPuzzleEditor_NoUndecidedCellReachesTheStore`` asserts
that too — but hiding them is a narrowing of the tools and could not be the
guarantee: ``solver_state.js clickedState`` makes a repeat click's third step
"blank" for Black and for White, and a confirmed Clear blanks every cell, so
an undecided cell stays reachable with two brushes on offer. That
reachability is asserted here as the *reason* the refusal is the rule
(``test_a_repeat_click_still_reaches_a_blank_cell_which_is_why_save_refuses``);
without it the refusal would look like dead code.

Property corpora are hand-built with ``random.Random`` and a fixed seed, each
asserting its own minimum count (no ``hypothesis``: not in the baseline).
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest

from tests.helpers.db import make_book
from tests.test_puzzle_edit_store import (
    MINUS_CORNER_SCORE,
    MINUS_CORNER_TIER,
    solid,
    solid_minus_corner,
    two_cell_diagonal,
)
from tests.test_puzzle_solver_marking import _button, _cell, _menu_item, _tool, _trigger
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _store,
    browser_page,
    browser_type,
    live,
)

_REPO = Path(__file__).resolve().parent.parent
_ADMIN = _REPO / "src" / "nonogram" / "admin"
_STATIC = _ADMIN / "static"
_TEMPLATES = _ADMIN / "templates"

#: The payload script both the player page and the editor page embed.
_PAYLOAD = re.compile(
    r'<script type="application/json" id="puzzle-player-data">(.*?)</script>', re.S
)

EDITOR = "/puzzle/{}/editor"
SAVE = "/puzzle/{}/edit"
VERIFY = "/puzzle/{}/edit/verify"


# --------------------------------------------------------------------------
# The panel over the in-memory store (these cannot skip)
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ADMIN_ALLOWED_HOST", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def seed(app, grid=None, **overrides) -> str:
    grid = solid() if grid is None else grid
    payload = {
        "grid": grid,
        "clues_rows": [],
        "clues_cols": [],
        "width": len(grid[0]),
        "height": len(grid),
        "theme": "winter",
        "difficulty_score": 99,
        "difficulty_tier": "hard",
        "quality_score": 71,
        "recognizability": "high",
        "strategies_used": ["guess"],
        "source_image": "snowflake.png",
    }
    payload.update(overrides)
    return app.puzzle_review_service.add_puzzle(**payload)


def payload_of(html: str) -> dict:
    match = _PAYLOAD.search(html)
    assert match is not None, "the page carries no puzzle data"
    return json.loads(match.group(1))


def book_a_puzzle(app, puzzle_id: str) -> None:
    """Make a book hold ``puzzle_id`` — the in-memory store's own route in."""
    app.puzzle_review_service.assign_to_book([puzzle_id], "11111111-1111-1111-1111-111111111111")


# --------------------------------------------------------------------------
# AC-1 — an Edit control from both entry points
# --------------------------------------------------------------------------


class TestPuzzleEditor_ReachableFromListAndCard:
    """AC-1. The server-rendered list row here; the puzzle's own card (the
    detail modal, built in JavaScript) in the browser class below."""

    def test_the_list_row_offers_an_edit_control_for_that_puzzle(self, admin_app) -> None:
        puzzle_id = seed(admin_app)
        html = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert f'href="/puzzle/{puzzle_id}/editor"' in html

    def test_the_edit_control_says_which_puzzle_it_edits(self, admin_app) -> None:
        """G-4. "Edit", repeated down a column of rows, names nothing — and a
        control whose visible text is not part of its accessible name is a
        defect of its own (WCAG 2.5.3), so "Edit" has to be inside it."""
        puzzle_id = seed(admin_app, source_image="snowflake.png")
        html = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        row = html[html.index(f'href="/puzzle/{puzzle_id}/editor"'):]
        anchor = row[: row.index("</a>")]
        assert 'aria-label="Edit the grid of snowflake.png"' in anchor
        assert ">Edit" in anchor

    def test_the_control_reaches_the_editor_of_that_very_puzzle(self, admin_app) -> None:
        first = seed(admin_app, source_image="first.png")
        second = seed(admin_app, grid=solid(8, 8), source_image="second.png")

        page = admin_app.test_client().get(EDITOR.format(second))

        assert page.status_code == 200
        assert payload_of(page.get_data(as_text=True))["id"] == second
        assert first != second

    def test_an_unknown_puzzle_has_no_editor(self, admin_app) -> None:
        assert admin_app.test_client().get(EDITOR.format("nope")).status_code == 404


# --------------------------------------------------------------------------
# AC-2 — the editor opens on the stored grid
# --------------------------------------------------------------------------


class TestPuzzleEditor_OpensOnTheStoredGrid:
    """AC-2, the server half: the payload the board is drawn from. The drawn
    cells themselves are asserted in the browser class below."""

    def test_the_payload_carries_the_stored_grid_at_its_stored_extent(self, admin_app) -> None:
        grid = solid_minus_corner(7, 9)
        puzzle_id = seed(admin_app, grid=grid)

        payload = payload_of(admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True))

        assert payload["solution"] == grid
        assert (payload["width"], payload["height"]) == (9, 7)

    def test_the_payload_asks_for_edit_mode(self, admin_app) -> None:
        """The one flag CARD-246 adds. Without it solver.js is the player and
        the board opens blank, which is the defect AC-2 names."""
        puzzle_id = seed(admin_app)

        payload = payload_of(admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True))

        assert payload["mode"] == "edit"

    def test_the_clues_beside_the_board_are_the_stored_grids_clues(self, admin_app) -> None:
        """Through the one encoder (ADR-0038/R3), checked against an encoder
        written independently of ``nonogram.clues`` (``_encode``)."""
        grid = solid_minus_corner(6, 8)
        puzzle_id = seed(admin_app, grid=grid, clues_rows=[[1]], clues_cols=[[1]])

        payload = payload_of(admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True))

        assert payload["rows"] == [_encode(row) for row in grid]
        assert payload["columns"] == [_encode(column) for column in zip(*grid)]

    def test_every_size_of_stored_grid_opens_on_itself(self, admin_app) -> None:
        """A seeded corpus rather than one example: the extent is read off the
        grid, not off the row's own width/height columns, so a row whose
        columns disagree with its grid must still open on the grid."""
        rng = random.Random(246)
        cases = 0
        for _ in range(12):
            height, width = rng.randint(5, 12), rng.randint(5, 12)
            grid = solid_minus_corner(height, width)
            # Deliberately wrong width/height columns beside a right grid.
            puzzle_id = seed(admin_app, grid=grid, width=3, height=3)
            payload = payload_of(
                admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True))
            assert payload["solution"] == grid
            assert (payload["width"], payload["height"]) == (width, height)
            cases += 1
        assert cases >= 12


# --------------------------------------------------------------------------
# AC-7 — a booked puzzle offers no Edit, and the route refuses it
# --------------------------------------------------------------------------


class TestPuzzleEditor_BookedPuzzleIsNotEditable:
    """AC-7. Both halves: the control is absent AND the route refuses. A
    disabled button is not a guard — the URL can be typed."""

    def test_the_list_row_offers_no_edit_control(self, admin_app) -> None:
        puzzle_id = seed(admin_app)
        book_a_puzzle(admin_app, puzzle_id)

        html = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert f'href="/puzzle/{puzzle_id}/editor"' not in html

    def test_the_editor_page_itself_refuses_and_says_why(self, admin_app) -> None:
        puzzle_id = seed(admin_app)
        book_a_puzzle(admin_app, puzzle_id)

        response = admin_app.test_client().get(EDITOR.format(puzzle_id))

        assert response.status_code == 409
        assert "in a book" in response.get_data(as_text=True)

    def test_the_save_routes_refuse_it_too(self, admin_app) -> None:
        """CARD-245's own guard, asserted from this card as well: AC-7 is the
        claim that BOTH hold, and a card that only tested its own half would
        pass while the pair came apart."""
        puzzle_id = seed(admin_app)
        book_a_puzzle(admin_app, puzzle_id)
        client = admin_app.test_client()
        grid = solid_minus_corner()

        verify = client.post(VERIFY.format(puzzle_id), json={"grid": grid})
        save = client.post(SAVE.format(puzzle_id), json={"grid": grid})

        assert (verify.status_code, save.status_code) == (409, 409)
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id)["grid"] == solid()

    def test_an_unbooked_puzzle_of_the_same_page_is_still_editable(self, admin_app) -> None:
        """The control that can fail: if the row never offered an Edit link at
        all, the absence above would be vacuous."""
        booked = seed(admin_app)
        free = seed(admin_app)
        book_a_puzzle(admin_app, booked)

        html = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert f'href="/puzzle/{booked}/editor"' not in html
        assert f'href="/puzzle/{free}/editor"' in html


# --------------------------------------------------------------------------
# G-1 / G-2 / G-3 / G-5 — the guardrails that can be read off the files
# --------------------------------------------------------------------------


class TestPuzzleEditor_Guardrails:
    def test_the_players_payload_is_untouched(self, admin_app) -> None:
        """G-1. The editor adds a key to ITS payload; the player's keeps
        exactly the six CARD-160 documented, "mode" not among them."""
        puzzle_id = seed(admin_app)

        payload = payload_of(
            admin_app.test_client().get(f"/puzzle/{puzzle_id}/solve").get_data(as_text=True))

        assert set(payload) == {"id", "width", "height", "rows", "columns", "solution"}

    def test_the_player_page_keeps_its_four_brushes_its_hint_and_its_counters(self) -> None:
        """G-1. The editor leaves elements out of ITS OWN page; taking any of
        them out of the player's would be the regression."""
        player = (_TEMPLATES / "puzzle_solve.html").read_text()

        # The attribute pair, not the role alone: the template's own header
        # comment names the role too.
        assert player.count('role="menuitemradio" data-player-tool=') == 4
        assert 'data-player-action="hint"' in player
        assert "data-player-errors" in player
        assert "data-player-progress" in player
        assert 'id="puzzle-player-solved"' in player

    def test_the_editor_ships_no_second_grid_renderer(self) -> None:
        """G-2. One renderer in the panel. The editor's own script never
        creates an element, and the editor's page loads the player's
        renderer — the same file, not a copy of it."""
        editor_js = (_STATIC / "puzzle_edit.js").read_text()
        editor_html = (_TEMPLATES / "puzzle_edit.html").read_text()

        assert "createElement" not in editor_js
        assert "player-cell" not in editor_js
        assert "solver.js" in editor_html
        drawing = [path.name for path in sorted(_STATIC.glob("*.js")) if "player-cell" in path.read_text()]
        assert drawing == ["solver.js"]

    def test_the_editor_decides_no_uniqueness_and_no_difficulty(self) -> None:
        """G-3, read off the file; the browser test below proves it by making
        the server lie and watching the page repeat the lie."""
        editor_js = (_STATIC / "puzzle_edit.js").read_text()
        code = "\n".join(
            line for line in editor_js.splitlines() if not line.strip().startswith("//"))

        assert "score_difficulty" not in code
        assert "classify" not in code
        # Everything shown about the grade is read out of the response.
        assert "grade.difficulty_tier" in code and "grade.difficulty_score" in code

    def test_the_editor_adds_no_dependency_and_no_vendored_script(self) -> None:
        """G-5 / ADR-0038/R1. The baseline itself is pinned by
        ``TestDependencyBaseline_IsExactlyPillowAndNumpy`` (the named
        survivor); this is the page's own half of it."""
        editor_html = (_TEMPLATES / "puzzle_edit.html").read_text()

        assert "http://" not in editor_html
        assert "https://" not in editor_html
        assert "<style" not in editor_html


# --------------------------------------------------------------------------
# The browser tier
# --------------------------------------------------------------------------


SIDE = 10
#: The stored puzzle every browser test starts from, and the edit of it the
#: owner makes by clearing cell (0, 0) with the White brush. CARD-245
#: measured what one solve says about that edit: easy, score 33.
STORED = solid(SIDE, SIDE)
EDITED = solid_minus_corner(SIDE, SIDE)

#: Put an arbitrary board on the editor's board without clicking 100 cells.
#: The cell states are built here, from a literal map, rather than through
#: ``solver_state.js boardOfGrid`` — the function AC-2 is about — so a test
#: that sets up a board is never testing the setup against itself.
_SET_GRID = """([grid]) => {
  const height = grid.length, width = grid[0].length;
  const cells = Object.freeze(grid.flat().map((filled) => (filled ? 'filled' : 'empty')));
  window.puzzlePlayer.setBoard(Object.freeze({ width, height, cells }));
}"""

#: The same, for a board that holds states a grid cannot express (AC-6).
_SET_STATES = """([states, width]) => {
  const cells = Object.freeze([...states]);
  window.puzzlePlayer.setBoard(
    Object.freeze({ width, height: states.length / width, cells }));
}"""

_BOARD_STATES = """() => [...document.querySelectorAll('td.player-cell')].map((td) => td.dataset.state)"""


def _states_of(grid) -> list[str]:
    return ["filled" if cell else "empty" for row in grid for cell in row]


def _open_editor(page, live, puzzle_id):
    page.goto(f"{live.url}/puzzle/{puzzle_id}/editor")
    page.wait_for_function("window.puzzlePlayer !== undefined")
    page.wait_for_selector("#puzzle-editor:not([hidden])")


def _message(page) -> str:
    return page.locator("#puzzle-editor-message").text_content()


def _wait_for_message(page, needle: str) -> str:
    page.wait_for_function(
        "([needle]) => document.getElementById('puzzle-editor-message')"
        ".textContent.includes(needle)",
        arg=[needle],
        timeout=20_000,
    )
    return _message(page)


def _approve_offered(page) -> bool:
    return page.locator("#puzzle-editor-decide").is_visible()


def _stored_grid(live, puzzle_id):
    return live.app.puzzle_review_service.get_puzzle(puzzle_id)["grid"]


def _assert_stored(live, puzzle_id, grid) -> None:
    """The store holds exactly ``grid`` and nothing of an edit it was not
    told to make. Used as both the assertion and — through
    ``test_the_unchanged_assertion_can_fail`` — its own control."""
    row = live.app.puzzle_review_service.get_puzzle(puzzle_id)
    assert row["grid"] == grid
    if grid == STORED:
        assert row["manually_edited_at"] is None


def _seed_live(live, grid=None, **kwargs) -> str:
    return _store(live.app.puzzle_review_service, grid if grid is not None else STORED, **kwargs)


@pytest.mark.browser
class TestPuzzleEditor_ReachableFromTheCard:
    """AC-1's second entry point: a puzzle's own card. The detail modal is
    built in JavaScript from ``/api/puzzle/<id>/details``, so only a browser
    sees it."""

    def test_the_card_offers_an_edit_control_that_opens_the_editor(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live, name="Snowflake")
        browser_page.goto(f"{live.url}/puzzles")
        browser_page.locator(f'a.name[onclick*="{puzzle_id}"]').click()

        edit = browser_page.get_by_role("link", name="Edit grid of Snowflake", exact=True)
        edit.wait_for()
        edit.click()

        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        assert browser_page.url.endswith(f"/puzzle/{puzzle_id}/editor")

    def test_a_booked_puzzles_card_offers_none(self, browser_page, live) -> None:
        """AC-7 on the card, beside the list row and the route."""
        puzzle_id = _seed_live(live, name="Booked")
        live.app.puzzle_review_service.assign_to_book([puzzle_id], make_book(live.scope))
        browser_page.goto(f"{live.url}/puzzles")
        browser_page.locator(f'a.name[onclick*="{puzzle_id}"]').click()
        browser_page.get_by_role("link", name="Solve", exact=True).wait_for()

        assert browser_page.get_by_role("link", name=re.compile("^Edit")).count() == 0


@pytest.mark.browser
class TestPuzzleEditor_OpensOnTheStoredGridInTheBrowser:
    """AC-2 in the browser: the cells as drawn."""

    def test_the_board_opens_showing_the_stored_grid(self, browser_page, live) -> None:
        grid = solid_minus_corner(6, 8)
        puzzle_id = _seed_live(live, grid)
        _open_editor(browser_page, live, puzzle_id)

        drawn = browser_page.evaluate(_BOARD_STATES)

        assert drawn == _states_of(grid)
        assert len(drawn) == 48
        assert "unknown" not in drawn

    def test_the_player_of_the_same_puzzle_still_opens_blank(self, browser_page, live) -> None:
        """G-1. The editor starts on the grid; the player must not — the two
        read the same flag and only one of them sets it."""
        puzzle_id = _seed_live(live, solid_minus_corner(6, 8))
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert set(browser_page.evaluate(_BOARD_STATES)) == {"unknown"}


@pytest.mark.browser
class TestPuzzleEditor_SaveShowsDifficultyThenApproveCommits:
    """AC-3: Save shows the recomputed difficulty with Cancel and Approve,
    and nothing is stored until Approve."""

    def test_save_shows_the_recomputed_difficulty_and_stores_nothing(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "Difficulty")

        assert MINUS_CORNER_TIER in said
        assert str(MINUS_CORNER_SCORE) in said
        assert _approve_offered(browser_page)
        assert _button(browser_page, "Approve").is_visible()
        assert _button(browser_page, "Cancel").is_visible()
        _assert_stored(live, puzzle_id, STORED)

    def test_approve_commits_the_grid_that_was_graded(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Saved")

        row = live.app.puzzle_review_service.get_puzzle(puzzle_id)
        assert row["grid"] == EDITED
        assert row["difficulty_tier"] == MINUS_CORNER_TIER
        assert row["difficulty_score"] == MINUS_CORNER_SCORE
        assert row["manually_edited_at"] is not None
        # The two-phase flow is over: there is nothing left to approve.
        assert not _approve_offered(browser_page)

    def test_the_unchanged_assertion_can_fail(self, browser_page, live) -> None:
        """ADR-0039/R1: the control for "nothing is stored until Approve".
        The claim is only worth something if the same assertion FAILS once
        something has been stored, so that is asserted here directly."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _assert_stored(live, puzzle_id, STORED)  # still true

        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Saved")

        with pytest.raises(AssertionError):
            _assert_stored(live, puzzle_id, STORED)


@pytest.mark.browser
class TestPuzzleEditor_CancelKeepsTheEditAndStoresNothing:
    """AC-4: Cancel stores nothing and does not discard the work either."""

    def test_cancel_leaves_the_store_and_the_board_as_they_were(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        _button(browser_page, "Cancel").click()
        said = _wait_for_message(browser_page, "Not saved")

        _assert_stored(live, puzzle_id, STORED)
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)
        assert not _approve_offered(browser_page)
        assert "still there" in said

    def test_the_edit_can_be_carried_on_and_saved_after_a_cancel(
        self, browser_page, live
    ) -> None:
        """The edit being "intact" means usable, not merely visible."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Cancel").click()
        _wait_for_message(browser_page, "Not saved")

        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Saved")

        assert _stored_grid(live, puzzle_id) == EDITED


@pytest.mark.browser
class TestPuzzleEditor_NonUniqueEditCannotBeApproved:
    """AC-5: an edit with zero or several solutions is refused in words, with
    no Approve, and the stored puzzle is unchanged."""

    def test_a_grid_with_two_solutions_is_refused_in_words(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.evaluate(_SET_GRID, [two_cell_diagonal(SIDE, SIDE)])

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "cannot be saved")

        assert not _approve_offered(browser_page)
        # Offered means reachable: a hidden button has no role at all, so the
        # two reads say different things — the element is in the page, and
        # nothing can get at it.
        assert browser_page.locator("#puzzle-editor-approve").count() == 1
        assert _button(browser_page, "Approve").count() == 0
        assert "exactly one solution" in said
        assert "Error" not in said and "Traceback" not in said
        _assert_stored(live, puzzle_id, STORED)

    def test_the_refusal_does_not_stop_the_owner_editing(self, browser_page, live) -> None:
        """A refusal is a step in the flow, not the end of it: the same page
        goes on to a grid that IS a puzzle."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.evaluate(_SET_GRID, [two_cell_diagonal(SIDE, SIDE)])
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "cannot be saved")

        browser_page.evaluate(_SET_GRID, [EDITED])
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Saved")

        assert _stored_grid(live, puzzle_id) == EDITED


@pytest.mark.browser
class TestPuzzleEditor_NoUndecidedCellReachesTheStore:
    """AC-6. **The rule implemented here is "the save is refused and names
    the undecided cells".** The two brushes that paint those states are also
    left out of the editor's menu, but that is a narrowing and not the
    guarantee — the third test below is why."""

    def test_save_refuses_and_names_the_undecided_cells(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        states = _states_of(STORED)
        states[0 * SIDE + 2] = "unknown"
        states[3 * SIDE + 4] = "maybe"
        browser_page.evaluate(_SET_STATES, [states, SIDE])

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "undecided")

        assert "row 1, column 3" in said
        assert "row 4, column 5" in said
        assert "2 cells are" in said
        assert not _approve_offered(browser_page)
        _assert_stored(live, puzzle_id, STORED)

    def test_nothing_is_even_sent_for_a_board_that_is_not_an_answer(
        self, browser_page, live
    ) -> None:
        """The cells cannot be coerced to ``false`` on the way out if the way
        out is never taken: no request is made at all."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        asked: list[str] = []
        browser_page.on("request", lambda request: asked.append(request.url))
        states = _states_of(STORED)
        states[5 * SIDE + 5] = "unknown"
        browser_page.evaluate(_SET_STATES, [states, SIDE])

        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "undecided")

        assert [url for url in asked if "/edit" in url] == []
        _assert_stored(live, puzzle_id, STORED)

    def test_a_repeat_click_still_reaches_a_blank_cell_which_is_why_save_refuses(
        self, browser_page, live
    ) -> None:
        """Why the refusal is the rule and hiding the brushes is not. With
        Black and White the only brushes on offer, a repeat click's third
        step is still "blank" (solver_state.js clickedState), so an undecided
        cell is reachable with the tools the editor DOES offer — and a rule
        that only removed brushes would leave it storable."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")

        _cell(browser_page, 0, 0).click()  # filled -> empty
        _cell(browser_page, 0, 0).click()  # repeat: empty -> blank

        assert browser_page.evaluate(_BOARD_STATES)[0] == "unknown"
        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "undecided")
        assert "row 1, column 1" in said
        _assert_stored(live, puzzle_id, STORED)

    def test_the_editor_offers_only_the_two_brushes_an_answer_can_hold(
        self, browser_page, live
    ) -> None:
        """The narrowing: Maybe and Undecided paint states a boolean grid
        cannot express, so the editor does not offer them."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _trigger(browser_page).click()

        assert browser_page.get_by_role("menuitemradio").count() == 2
        assert _menu_item(browser_page, "Black").is_visible()
        assert _menu_item(browser_page, "White").is_visible()
        assert _menu_item(browser_page, "Maybe").count() == 0
        assert _menu_item(browser_page, "Undecided").count() == 0

    def test_the_player_still_offers_all_four(self, browser_page, live) -> None:
        """G-1's half of the same claim: the brushes were left out of the
        editor's page, not taken off the shared board."""
        puzzle_id = _seed_live(live)
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        _trigger(browser_page).click()

        assert browser_page.get_by_role("menuitemradio").count() == 4

    def test_a_board_that_is_not_an_answer_yields_no_grid_at_all(
        self, browser_page, live
    ) -> None:
        """``answerOfBoard`` itself (solver_state.js), the pure function the
        refusal rests on: it hands back ``grid: null``, so there is no
        coerced grid for any caller to send, and it names every cell."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)

        answered = browser_page.evaluate(
            """async ([states, width]) => {
              const m = await import('/static/solver_state.js');
              const cells = Object.freeze([...states]);
              const board = Object.freeze({ width, height: states.length / width, cells });
              const answer = m.answerOfBoard(board);
              return { grid: answer.grid, undecided: answer.undecided };
            }""",
            [["filled", "unknown", "empty", "maybe"], 2],
        )

        assert answered["grid"] is None
        assert answered["undecided"] == [[0, 1], [1, 1]]

    def test_an_answer_board_round_trips_through_both_pure_functions(
        self, browser_page, live
    ) -> None:
        """The corpus: ``answerOfBoard(boardOfGrid(g)).grid`` is ``g`` for
        every grid, so the editor opening on a stored grid and saving it
        untouched stores the same grid. Seeded ``random.Random``, minimum
        count asserted here (no ``hypothesis``)."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        rng = random.Random(2460)
        grids = []
        for _ in range(40):
            height, width = rng.randint(1, 9), rng.randint(1, 9)
            grids.append([[rng.random() < 0.5 for _ in range(width)] for _ in range(height)])
        assert len(grids) >= 40
        # The corpus has to contain both values, or the round trip could hold
        # for a constant function.
        flat = [cell for grid in grids for row in grid for cell in row]
        assert flat.count(True) >= 100 and flat.count(False) >= 100

        round_tripped = browser_page.evaluate(
            """async ([grids]) => {
              const m = await import('/static/solver_state.js');
              return grids.map((grid) => m.answerOfBoard(m.boardOfGrid(grid)).grid);
            }""",
            [grids],
        )

        assert round_tripped == grids


@pytest.mark.browser
class TestPuzzleEditor_WhatTheServerSays:
    """G-3 and CARD-245's ``EditNotVerified``: the page relays the server and
    decides nothing itself."""

    def test_the_difficulty_shown_is_the_servers_number_and_not_a_derived_one(
        self, browser_page, live
    ) -> None:
        """G-3, proved rather than read: the verify route is stubbed with a
        grade no local arithmetic would produce, and the page shows it. A
        page that computed the difficulty itself would show 33/easy."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.route(
            "**/edit/verify",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "ok": True,
                    "grade": {"difficulty_score": 7, "difficulty_tier": "fiendish"},
                }),
            ),
        )
        browser_page.evaluate(_SET_GRID, [EDITED])

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "Difficulty")

        assert "fiendish" in said
        assert "7 of 100" in said
        assert MINUS_CORNER_TIER not in said

    def test_a_refusal_from_the_server_is_what_the_owner_reads(
        self, browser_page, live
    ) -> None:
        """G-3 the other way: a 422 the page could not have decided on."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.route(
            "**/edit/verify",
            lambda route: route.fulfill(
                status=422,
                content_type="application/json",
                body=json.dumps({"ok": False, "message": "this grid has 4 solutions"}),
            ),
        )
        browser_page.evaluate(_SET_GRID, [EDITED])

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "cannot be saved")

        assert "this grid has 4 solutions" in said
        assert not _approve_offered(browser_page)

    def test_an_approval_of_a_grid_the_store_no_longer_remembers_asks_to_verify_again(
        self, browser_page, live
    ) -> None:
        """CARD-245 memoises the proof on the service instance, LRU-bounded:
        an eviction (or a restart) makes Approve a 409. That is an ordinary
        outcome of this flow, so the owner is asked to press Save again and
        told nothing was stored — never shown an error."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.evaluate(_SET_GRID, [EDITED])
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        # What an eviction leaves behind: a page holding a grade whose proof
        # the store has forgotten.
        live.app.puzzle_review_service._verifications.clear()

        _button(browser_page, "Approve").click()
        said = _wait_for_message(browser_page, "Press Save to check this grid again")

        assert "Nothing was stored" in said
        assert "verify it again" in said  # the store's own words, relayed
        assert not _approve_offered(browser_page)
        _assert_stored(live, puzzle_id, STORED)

    def test_the_same_save_can_then_be_made_again(self, browser_page, live) -> None:
        """The refusal above costs one re-verify and no work."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.evaluate(_SET_GRID, [EDITED])
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        live.app.puzzle_review_service._verifications.clear()
        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Press Save to check this grid again")

        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Saved")

        assert _stored_grid(live, puzzle_id) == EDITED


@pytest.mark.browser
class TestPuzzleEditor_Accessibility:
    """G-4, following CARD-211's pattern: reachable from the keyboard, and
    the state said out loud rather than shown only."""

    def test_the_message_is_a_live_region_that_is_always_present(
        self, browser_page, live
    ) -> None:
        """A region that only appears is not reliably read, so the line is in
        the DOM from the start and only its text changes; the two buttons
        sit outside it, so the announcement is the message and not the
        labels."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        message = browser_page.locator("#puzzle-editor-message")

        assert message.get_attribute("role") == "status"
        assert message.get_attribute("aria-atomic") == "true"
        # In the DOM and not hidden from the start — an empty <p> simply has
        # no box to be "visible" in, which is not the same as being absent or
        # display:none (what a reader's live region would not survive).
        assert message.count() == 1
        assert message.get_attribute("hidden") is None
        assert browser_page.evaluate(
            "() => getComputedStyle(document.getElementById('puzzle-editor-message')).display"
        ) != "none"
        assert message.text_content().strip() == ""
        # The buttons are OUTSIDE the region, so what is announced is the
        # message and not "Approve Cancel" after it.
        assert browser_page.locator("#puzzle-editor-message #puzzle-editor-approve").count() == 0

        browser_page.evaluate(_SET_GRID, [EDITED])
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        assert message.is_visible()

    def test_the_whole_flow_runs_from_the_keyboard(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.evaluate(_SET_GRID, [EDITED])

        _button(browser_page, "Save").focus()
        browser_page.keyboard.press("Enter")
        _wait_for_message(browser_page, "Difficulty")
        # Focus follows the flow: the next thing to decide is Approve.
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-approve"
        browser_page.keyboard.press("Tab")
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-cancel"

        browser_page.keyboard.press("Enter")
        _wait_for_message(browser_page, "Not saved")
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-save"
        _assert_stored(live, puzzle_id, STORED)

    def test_approving_from_the_keyboard_commits(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.evaluate(_SET_GRID, [EDITED])

        _button(browser_page, "Save").focus()
        browser_page.keyboard.press("Enter")
        _wait_for_message(browser_page, "Difficulty")
        browser_page.keyboard.press("Enter")
        _wait_for_message(browser_page, "Saved")

        assert _stored_grid(live, puzzle_id) == EDITED
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-save"

    def test_the_edit_link_on_the_list_is_in_the_tab_order(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live, name="Owl")
        browser_page.goto(f"{live.url}/puzzles")
        link = browser_page.get_by_role("link", name="Edit the grid of Owl", exact=True)

        link.focus()
        browser_page.keyboard.press("Enter")

        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        assert browser_page.url.endswith(f"/puzzle/{puzzle_id}/editor")

    def test_region_keeps_its_announced_toggle_state(self, browser_page, live) -> None:
        """CARD-211's control, on the editor's page too — the editor reuses
        the player's markup, so it must keep the player's accessibility."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        toggle = browser_page.locator("[data-player-region]")
        assert toggle.get_attribute("aria-pressed") == "false"

        toggle.click()

        assert toggle.get_attribute("aria-pressed") == "true"
        assert "Region on" in browser_page.locator("#puzzle-player-announce").text_content()


@pytest.mark.browser
class TestPuzzleEditor_ThePlayerIsNotRegressed:
    """G-1, the seam the editor could most easily have broken."""

    def test_the_editor_writes_nothing_into_the_players_save(
        self, browser_page, live
    ) -> None:
        """The player's save is keyed by the puzzle's id (CARD-185), so an
        editor that kept the save would overwrite the solve-in-progress of
        the very puzzle being edited."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _cell(browser_page, 1, 1).click()

        keys = browser_page.evaluate("() => Object.keys(window.localStorage)")

        assert keys == []

    def test_a_solve_in_progress_survives_a_visit_to_the_editor(
        self, browser_page, live
    ) -> None:
        """The same claim end to end, and the one the owner would notice."""
        puzzle_id = _seed_live(live)
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        _cell(browser_page, 2, 3).click()
        marked = browser_page.evaluate(_BOARD_STATES)
        saved = browser_page.evaluate("() => Object.keys(window.localStorage).length")
        assert saved == 1

        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert browser_page.evaluate(_BOARD_STATES) == marked

    def test_the_editor_page_has_no_hint_and_no_counters(self, browser_page, live) -> None:
        """What edit mode leaves out, asserted as absent rather than assumed:
        all four are statements about a solution, and in the editor the
        solution is what is being written."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)

        assert _button(browser_page, "Hint").count() == 0
        assert browser_page.locator("[data-player-errors]").count() == 0
        assert browser_page.locator("[data-player-progress]").count() == 0
        assert browser_page.locator("#puzzle-player-solved").count() == 0

    def test_the_board_is_never_locked_as_solved_in_the_editor(
        self, browser_page, live
    ) -> None:
        """The board opens equal to the stored grid, which in the player means
        solved — and a locked board cannot be edited."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")

        _cell(browser_page, 4, 4).click()

        assert browser_page.evaluate(_BOARD_STATES)[4 * SIDE + 4] == "empty"
        assert browser_page.locator(".player-board.is-solved").count() == 0
        assert _button(browser_page, "Undo").get_attribute("aria-disabled") == "false"

    def test_the_player_keeps_its_hint_and_its_counters(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")

        assert _button(browser_page, "Hint").count() == 1
        assert browser_page.locator("[data-player-errors]").count() == 1
        assert browser_page.locator("[data-player-progress]").count() == 1
