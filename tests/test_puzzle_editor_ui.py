"""CARD-246 — the manual puzzle editor's UI (the client half of CARD-245).

The *editor* is the page at ``GET /puzzle/<id>/editor``: the owner paints a
stored puzzle's grid by hand, presses Save, reads the recomputed difficulty,
and Approves or goes back to editing. The two routes it posts to are CARD-245's and are
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
  the stored grid, real clicks, the message, Approve, the two exits, what the store
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

**THE TWO-PHASE FLOW'S INVARIANT** (review cycle 1, F-001..F-005):
``TestPuzzleEditor_TheOfferAndTheWordsAgree`` is the class that holds the
page to it — never an Approve for a grid other than the one whose grade is on
screen, and never a claim about the store that the store has not made. Each of
the four mechanisms ``static/puzzle_edit.js`` names in THE INVARIANT is pinned
there by a test that fails when that mechanism alone is taken out, including
the two the reviewer's surviving mutants went through (Approve re-reading the
board, and the offer surviving the start of a new check).

One exception, measured rather than reasoned (review cycle 3, MU-I3): of the
two sites mechanism 3 occupies, only ``onSave``'s is sole protection.
Removing ``onApprove``'s one-request guard alone leaves 98 tests passing,
because ``tell`` has already withdrawn the offer by then, so there is nothing
for a second Approve to send. It is a DECLARED REDUNDANCY and
``test_a_second_approve_pressed_in_flight_is_not_sent_either``'s own docstring
says so; this paragraph used to claim the stronger thing for all four, which
the mutant falsified.

**Page isolation** is declared in :data:`PAGE_ISOLATION_DECLARATION` below and
checked by this file's own test, because CARD-235's registry globs
``tests/test_puzzle_solver_*.py`` and cannot see a file outside that name
(review cycle 1, F-014).

Property corpora are hand-built with ``random.Random`` and a fixed seed, each
asserting its own minimum count (no ``hypothesis``: not in the baseline).
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from urllib.parse import quote

import pytest

from tests.helpers.db import make_book
# CARD-291's two 9x9 fixtures, each with its premise asserted against the
# solver in the module that owns it: one whose verifying solve branches and
# one of the same extent that line logic finishes.
from tests.test_approval_guess_gate import GUESS_GRID, LINE_GRID
from tests.test_puzzle_edit_store import (
    MINUS_CORNER_SCORE,
    MINUS_CORNER_TIER,
    solid,
    solid_minus_corner,
    two_cell_diagonal,
)
# CARD-271 (review cycle 1, F-008): the editor reuses .player-stage and the
# same solver.js, so it inherits the clue-gutter room condition — read here
# with that card's own helpers rather than with a second copy of them.
from tests.test_puzzle_solver_clues import _room, _settled, _verdict, _zoom
from tests.test_puzzle_solver_marking import _button, _cell, _menu_item, _tool, _trigger
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures are used by name
    _encode,
    _store,
    _unique_grid,
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

#: What makes a file a grid renderer, whatever it calls its cells and
#: whatever nodes it builds them out of: it puts cells into the page. Every
#: route to that counts — ``createElement`` of ANY element, the DOM table
#: API, table markup, markup of any kind handed to ``innerHTML`` /
#: ``insertAdjacentHTML``, or a cloned node — because G-2 is "one renderer in
#: this panel" and a second one is still a second one under new class names
#: (review cycle 1, F-007) and in other tags (review cycle 2, G-004: a
#: ``<div class="shadow-cell">`` grid built from a string walked past the
#: table-shaped predicate). ``player-cell`` stays as the panel's own cell
#: class, which is what a FORK of solver.js would carry.
#:
#: **What this does NOT check**, stated because a completeness guard that
#: overstates itself is worse than none (review cycle 2, G-004): it is a text
#: predicate over one file, so a builder that creates no node and writes no
#: markup is outside it — one that only re-styles or re-labels cells
#: ``solver.js`` already drew, or one that reaches the DOM through a name
#: this pattern cannot see. The STRUCTURAL half of the guard covers the
#: likelier case on its own: the editor page's script set is asserted
#: exactly, so a renderer in a NEW file is caught by its file whatever it
#: draws with.
_BUILDS_A_GRID = re.compile(
    r"""createElement\(|createElementNS\(|cloneNode\("""
    r"""|insertRow|insertCell|insertAdjacentHTML"""
    r"""|innerHTML\s*=|outerHTML\s*=|<t(?:able|body|head|r|d|h)\b|player-cell""",
    re.I,
)

#: The markers that bound app.py's manual-edit POST surface — its helpers and
#: CARD-245's two routes. Every refusal those routes emit is read off that
#: slice, rather than from the reasons a test already knows (review cycle 2,
#: G-007).
#:
#: The start marker moved from ``_edit_refusal`` to the first of the helpers
#: when CARD-251 added them (``_submitted_confirmation``, ``_book_holding``,
#: ``_page_count_effect``, ``_book_answer``, ``_refused``): they sit in front
#: of ``_edit_refusal`` and are part of the same surface, so the slice is the
#: whole of it.
#:
#: **No reason is emitted from inside those helpers today** (review cycle 1,
#: F-003, which recomputed both regexes with the old marker and got the same
#: seven reasons): ``_refused`` takes its ``reason`` as a parameter and all
#: three call sites are BELOW ``_edit_refusal``, inside the two POST routes.
#: The widening is forward cover — strictly more of the surface scanned, so a
#: refusal a later card emits from one of these helpers is in scope the day it
#: is written — and not a fix for a reason this slice was missing. It cannot
#: loosen the guard in the other direction: ``emitted ==
#: set(EDIT_REFUSAL_REASONS)`` is an equality, so a vocabulary entry nothing
#: emits still fails. The convention for the next card is: the slice is the
#: whole POST surface, from its first helper, and it is widened when the
#: surface grows rather than when a reason goes missing.
_EDIT_ROUTES = (
    "    def _submitted_confirmation():",
    '@app.route("/puzzle/<puzzle_id>/editor"',
)

EDITOR = "/puzzle/{}/editor"
SAVE = "/puzzle/{}/edit"
VERIFY = "/puzzle/{}/edit/verify"

#: This file's page isolation, in CARD-235's own vocabulary and checked by
#: ``TestPuzzleEditor_Guardrails.test_this_files_page_isolation_is_declared``.
#: CARD-235 keeps the declaration for its twelve files in
#: ``tests/test_puzzle_solver_page.py``'s ``PAGE_ISOLATION``, whose guard globs
#: ``tests/test_puzzle_solver_*.py`` — a glob this file's name is outside, so
#: the discipline could not see it (review cycle 1, F-014). The glob is left
#: alone deliberately: widening it would re-key CARD-235's collection
#: baseline, its allowlist of added node ids and its recorded 422-test order
#: runs, which is a change to that card's machinery and not to this one's. The
#: declaration is made here instead, with the same two categories and the same
#: check that the fixtures this file imports really are per-test.
PAGE_ISOLATION_DECLARATION = (
    "own-page",
    "installs page.route interceptors (an aborted verify, an aborted save, a "
    "stubbed grade, a 204 that holds the exit's navigation back), request and "
    "pageerror listeners and a MutationObserver on the save bar, seeds and "
    "reads localStorage, and suppresses a document event listener — none of "
    "which navigating undoes; and since CARD-250 its tests navigate AWAY from "
    "the editor on purpose, so a page left on the puzzle list is a page the "
    "next test would have to put back — as is a page deliberately left on the "
    "editor holding an unstored stroke (review cycle 1, F-001), and since "
    "CARD-251 one left holding an OPEN book question, whose two answers are "
    "the only way past it",
)


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


@pytest.fixture
def books(admin_app):
    """The panel's book manager, emptied before and after.

    In memory mode ``get_book_manager`` hands back a module-level singleton
    (``book_manager._book_manager``), so books outlive the ``admin_app``
    fixture and would leak between tests. The same fixture
    ``tests/test_puzzle_edit_routes.py`` uses, and for the same reason
    (review cycle 1, F-010: this file's own helper cleared on entry only).
    """
    manager = admin_app.book_manager
    manager.books.clear()
    yield manager
    manager.books.clear()


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


def legacy_in_book(live, puzzle_id: str) -> None:
    """Record membership the pre-CARD-100 way: the ``in_book`` status, no id.

    The spelling of "a book this panel cannot name" that a real database can
    hold — the other one, an empty-string ``book_id``, does not go into a
    ``uuid`` column, which is why the in-memory tests use that one and the
    live ones use this (``tests/test_puzzle_edit_store.py`` says the same).
    """
    import uuid as uuid_module

    from nonogram.db.models import Puzzle

    with live.scope() as db:
        row = (
            db.query(Puzzle)
            .filter(Puzzle.id == uuid_module.UUID(puzzle_id))
            .first()
        )
        assert row is not None, f"no puzzles row for {puzzle_id}"
        row.status = "in_book"
    stored = live.app.puzzle_review_service.get_puzzle(puzzle_id)
    assert stored["status"] == "in_book"
    assert stored.get("book_id") is None, "this arm is the status alone"


def seed_with_real_clues(app, grid=None, **overrides) -> str:
    """A stored puzzle whose ``clues_*`` columns match its grid (CARD-251).

    ``seed`` above stores empty clue columns, which the book's 4.75 mm floor
    reads as "this puzzle's cell cannot be measured" and refuses — so a test
    that wants a REAL book to hold a puzzle has to store its clues. The floor
    is INV-006's and is not this card's to work around.
    """
    from nonogram.clues import compute_clues

    grid = solid() if grid is None else grid
    rows, columns = compute_clues(grid)
    payload = {
        "clues_rows": [list(clue) for clue in rows],
        "clues_cols": [list(clue) for clue in columns],
        "difficulty_tier": "easy",
        "difficulty_score": 33,
        "strategies_used": ["simple_overlap"],
    }
    payload.update(overrides)
    return seed(app, grid=grid, **payload)


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
    """AC-7, as CARD-251 narrowed it: the book this panel cannot NAME.

    Both halves of the old claim still hold for that case — the control is
    absent AND the route refuses, because a missing button is not a guard and
    the URL can be typed.

    **G-10, the retirements and their survivors.** CARD-246 asserted this for
    every booked puzzle, in three tests
    (``test_the_list_row_offers_no_edit_control``,
    ``test_the_editor_page_itself_refuses_and_says_why``,
    ``test_the_save_routes_refuse_it_too``). The owner reversed that
    behaviour, and the survivors are
    :class:`TestBookedEdit_TheEditorOpensForABookedPuzzle` (the page is served
    and names the book), ``tests/test_puzzle_edit_routes.py``'s
    ``TestBookedEditRoutes_TheConfirmationIsTheServers`` (the save still
    writes nothing without the confirmation) and that file's
    ``TestBookedEdit_OnlyEditingWasOpened`` (approve, reject, restore and
    delete still refuse). The two tests kept below are the same two
    assertions, for the membership that still has no book to name.
    """

    def test_the_list_row_offers_no_edit_control_for_a_book_it_cannot_name(
        self, admin_app
    ) -> None:
        puzzle_id = seed(admin_app)
        admin_app.puzzle_review_service.assign_to_book([puzzle_id], "")

        html = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert f'href="/puzzle/{puzzle_id}/editor"' not in html

    def test_the_editor_page_itself_refuses_and_says_why(self, admin_app) -> None:
        puzzle_id = seed(admin_app)
        admin_app.puzzle_review_service.assign_to_book([puzzle_id], "")

        response = admin_app.test_client().get(EDITOR.format(puzzle_id))

        assert response.status_code == 409
        assert "in a book" in response.get_data(as_text=True)

    def test_a_falsy_but_present_book_id_is_refused_by_control_and_route_alike(
        self, admin_app
    ) -> None:
        """AC-7 / F-010: one spelling of "may this grid be edited".

        The rule is the store's ``_holds_a_book`` — a ``book_id`` that is not
        ``None`` — and all three surfaces now read one answer
        (``puzzle_is_editable``). The list row used to ask it as truthiness and
        the card's script a third time, so a row whose book_id is ``""`` (a
        migration's empty string) was offered an Edit control that the route
        then refused with a 409: the control and the guard disagreeing about
        the same puzzle.
        """
        puzzle_id = seed(admin_app)
        admin_app.puzzle_review_service.assign_to_book([puzzle_id], "")
        client = admin_app.test_client()

        page = client.get("/puzzles").get_data(as_text=True)
        details = client.get(f"/api/puzzle/{puzzle_id}/details").get_json()

        assert f"/puzzle/{puzzle_id}/editor" not in page
        assert details["editable"] is False
        assert client.get(EDITOR.format(puzzle_id)).status_code == 409

    def test_an_unbooked_puzzle_of_the_same_page_is_still_editable(self, admin_app) -> None:
        """The control that can fail: if the row never offered an Edit link at
        all, the absence above would be vacuous."""
        unnameable = seed(admin_app)
        free = seed(admin_app)
        admin_app.puzzle_review_service.assign_to_book([unnameable], "")

        html = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert f'href="/puzzle/{unnameable}/editor"' not in html
        assert f'href="/puzzle/{free}/editor"' in html

    def test_a_puzzle_in_a_NAMEABLE_book_is_offered_the_control_again(
        self, admin_app
    ) -> None:
        """CARD-251, the other side of the narrowing: a booked puzzle is
        editable behind the confirmation, so the Edit control comes back — on
        the list row and in the answer the puzzle's own card reads."""
        puzzle_id = seed(admin_app)
        book_a_puzzle(admin_app, puzzle_id)
        client = admin_app.test_client()

        html = client.get("/puzzles").get_data(as_text=True)
        details = client.get(f"/api/puzzle/{puzzle_id}/details").get_json()

        assert f'href="/puzzle/{puzzle_id}/editor"' in html
        assert details["editable"] is True


# --------------------------------------------------------------------------
# CARD-251 AC-1 — the editor opens for a booked puzzle, and names the book
# --------------------------------------------------------------------------


class TestBookedEdit_TheEditorOpensForABookedPuzzle:
    """AC-1: served, not refused, and it says which book holds the puzzle.

    The page is where the owner meets the fact before they paint anything —
    the confirmation they will be asked for is about *that* book, and a page
    that did not name it would leave the question to arrive as a surprise
    after Save.
    """

    @staticmethod
    def _book(books, puzzle_ids, *, title="Winter Pictures", published=False):
        """A real draft book holding ``puzzle_ids``, through the panel's path.

        Takes the ``books`` fixture rather than the app so that the singleton
        is emptied on the way OUT as well as in (review cycle 1, F-010): it
        cleared only on entry, so every test after one of these four ran
        against a panel still holding "Winter Pictures".
        """
        book_id = books.create_book(
            title=title, description="Winter pictures", theme="christmas",
            target_audience="adults",
        )
        assert books.add_puzzles_to_book(book_id, list(puzzle_ids)) is True
        # Asserted rather than assumed: `add_puzzles_to_book` answers True for
        # "the add was processed", which includes a submission the 4.75 mm
        # floor refused entirely (INV-006).
        assert books.get_book(book_id).puzzle_ids == list(puzzle_ids)
        if published:
            books.books[book_id].status = "published"
        return book_id

    def test_the_page_is_served_and_carries_the_stored_grid(
        self, admin_app, books
    ) -> None:
        puzzle_id = seed_with_real_clues(admin_app)
        self._book(books, [puzzle_id])

        page = admin_app.test_client().get(EDITOR.format(puzzle_id))

        assert page.status_code == 200
        assert payload_of(page.get_data(as_text=True))["solution"] == solid()

    def test_the_page_names_the_book_that_holds_it(
        self, admin_app, books
    ) -> None:
        puzzle_id = seed_with_real_clues(admin_app)
        self._book(books, [puzzle_id], title="Winter Pictures")

        html = admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True)

        note = re.search(r'<p class="editor-book"[^>]*>(.*?)</p>', re.sub(r"\s+", " ", html))
        assert note is not None, "the editor page says nothing about the book"
        assert "Winter Pictures" in note.group(1)

    def test_a_published_books_page_says_it_is_published(
        self, admin_app, books
    ) -> None:
        """AC-6's half of the page: the question names the book AND its status,
        because a published book's confirmation is INV-008's own."""
        puzzle_id = seed_with_real_clues(admin_app)
        self._book(books, [puzzle_id], title="Winter Nights", published=True)

        html = admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True)
        flat = re.sub(r"\s+", " ", html)

        note = re.search(r'<p class="editor-book"[^>]*>(.*?)</p>', flat)
        assert note is not None
        assert "Winter Nights" in note.group(1)
        assert "published" in note.group(1)

    def test_a_book_whose_title_cannot_be_read_is_named_as_an_id(
        self, admin_app, books
    ) -> None:
        """Failure matrix F-4, on the first surface the owner meets (review
        cycle 1, F-002). A ``book_id`` that resolves to no book leaves the
        title ``None``, and the paragraph used to print the bare uuid where
        the title goes — so the owner read a uuid AS a title. It now says the
        title could not be read and calls the uuid an id.

        The membership is an identity, so the page is still SERVED: that is
        the branch ``_an_edit_may_touch`` sends here, and it is the one
        ``in_a_book`` does not (``test_a_puzzle_in_an_unnameable_book...``).
        """
        puzzle_id = seed_with_real_clues(admin_app)
        gone = "11111111-2222-3333-4444-555555555555"
        admin_app.puzzle_review_service.assign_to_book([puzzle_id], gone)

        page = admin_app.test_client().get(EDITOR.format(puzzle_id))
        flat = re.sub(r"\s+", " ", page.get_data(as_text=True))

        assert page.status_code == 200
        note = re.search(r'<p class="editor-book"[^>]*>(.*?)</p>', flat)
        assert note is not None, "the editor page says nothing about the book"
        assert "title could not be read" in note.group(1)
        assert gone in note.group(1)
        # And the uuid is not standing in for a title: it is called an id.
        assert f"id <strong>{gone}</strong>" in note.group(1)
        assert f"the book <strong>{gone}</strong>" not in note.group(1)

    def test_an_unbooked_puzzles_page_says_nothing_about_a_book(
        self, admin_app
    ) -> None:
        """The control that can fail: the note is absent for a puzzle with no
        book, so the three assertions above are about the membership and not
        about a paragraph the page always carries."""
        puzzle_id = seed_with_real_clues(admin_app)

        html = admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True)

        assert 'class="editor-book"' not in html


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

    #: A write to the save bar's message line, by either route this file could
    #: take: the binding ``tell`` holds, or a fresh lookup of the element.
    #: RESIDUAL, stated rather than left as a claim of completeness: a writer
    #: that aliases the element to a third name first
    #: (``const m = message; m.textContent = ...``) is not matched. The guard
    #: reads the two spellings the file actually uses; a third would be a new
    #: shape, and the coupling tests in
    #: ``TestPuzzleEditor_TheOfferAndTheWordsAgree`` are what stand behind it.
    _WRITES_THE_MESSAGE = re.compile(
        r"""(?:\bmessage\b|getElementById\(\s*['"]puzzle-editor-message['"]\s*\))"""
        r"""\s*\.\s*(?:textContent|innerText|innerHTML|replaceChildren|replaceWith"""
        r"""|append|appendChild|insertAdjacentHTML|insertAdjacentText)"""
    )
    _WRITES_THE_OFFER = re.compile(r"\bdecide\s*\.\s*hidden\s*=")

    def test_tell_is_the_only_writer_of_the_message_and_the_offer(self) -> None:
        """G-2, LITERALLY -- the clause, not only its consequence.

        The suite pinned the *coupling* (every sentence carries its own offer,
        so a refusal never stands beside a live Approve) and that is well
        pinned. It did not pin the clause G-2 actually states. Measured by the
        AC/EC/G gate on 2026-10-19: replacing ``tell(inFlightText(inFlight))``
        in ``onLeave`` with ``message.textContent = inFlightText(inFlight)``
        -- a literal second writer -- left 98 tests passing. A second writer
        that happens not to decouple the message from the offer was invisible,
        which is a claim stated wider than its mechanism (the family that
        produced a finding on every review cycle of this card).

        So: exactly one write of each, and both inside ``tell``. The point is
        not tidiness. It is that "a refusal standing beside a live Approve is
        not a state this file can be in" is only true while one function
        decides both, and a reviewer should be able to check that by counting
        rather than by reading every path.
        """
        script = (_STATIC / "puzzle_edit.js").read_text()
        code = "\n".join(
            line for line in script.splitlines() if not line.lstrip().startswith("//"))

        messages = self._WRITES_THE_MESSAGE.findall(code)
        offers = self._WRITES_THE_OFFER.findall(code)
        assert len(messages) == 1, messages
        assert len(offers) == 1, offers

        # ...and both of them are tell's own. Sliced from its declaration to
        # the next function's, so a write that moved out of tell but stayed
        # the only one still fails.
        start = code.index("function tell(")
        body = code[start:]
        end = body.index("\n  function ", 1)
        tell_body = body[:end]
        assert self._WRITES_THE_MESSAGE.search(tell_body), tell_body[-400:]
        assert self._WRITES_THE_OFFER.search(tell_body), tell_body[-400:]

    def test_the_editor_ships_no_second_grid_renderer(self, admin_app) -> None:
        """G-2. One renderer in the panel, asserted over what the editor's
        page actually LOADS rather than over one class name (review cycle 1,
        F-007).

        The old form globbed the static modules for the literal
        ``player-cell``, so a renderer added under any other name — a
        ``static/editor_grid.js`` building ``<td class="editor-cell">`` and
        loaded by this page — passed it. What makes a file a renderer is that
        it puts cells into the page, by whichever route (``createElement`` of
        any element, the DOM table API, markup handed to ``innerHTML``, a
        cloned node), and of every script this page serves itself exactly one
        may do that. The predicate's own residual — a builder that creates no
        node and writes no markup — is written out beside
        :data:`_BUILDS_A_GRID` rather than left as a claim of completeness
        the guard does not have (review cycle 2, G-004).
        """
        puzzle_id = seed(admin_app)
        html = admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True)

        loaded = sorted(set(re.findall(r'<script[^>]*src="[^"]*/static/([^"?]+)"', html)))
        assert loaded == ["puzzle_edit.js", "solver.js"], loaded
        builders = [name for name in loaded if _BUILDS_A_GRID.search((_STATIC / name).read_text())]
        assert builders == ["solver.js"], builders
        # The page loads the renderer itself, so "only one builds a grid" is
        # not satisfied by a page that draws no board at all.
        assert _BUILDS_A_GRID.search((_STATIC / "solver.js").read_text()) is not None
        # And the editor's own script builds nothing at all — asked of the
        # whole predicate rather than of ``createElement`` alone, which a
        # div/``innerHTML`` grid inside this very file walked straight past
        # (review cycle 2, G-004).
        assert _BUILDS_A_GRID.search((_STATIC / "puzzle_edit.js").read_text()) is None

    def test_the_editor_decides_no_uniqueness_and_no_difficulty(self) -> None:
        """Documentation of G-3, and only that (review cycle 1, F-013).

        It greps for two identifiers no hand-rolled client-side grader would
        have been named, so it cannot carry the guardrail. **The test that
        does** is
        ``TestPuzzleEditor_WhatTheServerSays.test_the_difficulty_shown_is_the_servers_number_and_not_a_derived_one``,
        which stubs the route with a grade no local arithmetic could produce
        and watches the page show it; its 422 sibling is the other half. This
        stays beside them as the statement that the file reads the response's
        own fields, which is the shape those two prove.
        """
        editor_js = (_STATIC / "puzzle_edit.js").read_text()
        code = "\n".join(
            line for line in editor_js.splitlines() if not line.strip().startswith("//"))

        assert "score_difficulty" not in code
        assert "classify" not in code
        # Everything shown about the grade is read out of the response.
        assert "grade.difficulty_tier" in code and "grade.difficulty_score" in code

    def test_this_files_page_isolation_is_declared_and_true(self) -> None:
        """F-014. CARD-235's rule is that a browser-test file's page isolation
        is a declaration somebody changes on purpose; its registry's guard
        globs ``tests/test_puzzle_solver_*.py``, which this file's name is
        outside, so the declaration is made here and checked here — in that
        card's own vocabulary, against that card's own reading of the fixture
        scopes, and with the reason grepped for the mechanisms it claims, as
        ``PAGE_ISOLATION``'s three tests do for the files inside it. (The
        ordinal that used to stand there — "the twelve" — was stale by two by
        the time CARD-267 added the fourteenth, so it is gone rather than
        re-counted: a number nothing checks is a number that goes wrong.)"""
        from tests.test_browser_fixture_scope import _fixture_scope
        from tests.test_puzzle_solver_page import PAGE_ISOLATION, PAGE_ISOLATION_CATEGORIES

        category, reason = PAGE_ISOLATION_DECLARATION
        source = Path(__file__).read_text()

        assert category in PAGE_ISOLATION_CATEGORIES
        assert len(reason.split()) >= 8, reason
        # Why this file declares its own: it is not in the family's glob, so
        # adding a key to PAGE_ISOLATION would fail that registry's own
        # "they agree with the files on disk" test.
        assert Path(__file__).name not in PAGE_ISOLATION
        # own-page means a page per test AND a server per test.
        for fixture in (browser_page, live):
            assert _fixture_scope(fixture) == "function", fixture
        for mechanism in (r"\.route\(", r"\.on\(", r"localStorage", r"MutationObserver"):
            assert re.search(mechanism, source), mechanism

    def test_the_edit_mode_contract_counts_its_own_branches(self) -> None:
        """F-009: solver.js's EDIT MODE contract says how many things the one
        flag changes, and the count is checked against the code rather than
        believed. It said three while the flag was read four times (the
        fourth, ``nextHint``, unreachable behind ``actions.hint?.``), and a
        contract nobody counts is how the fifth read — this cycle's
        BOARD_CHANGE — would have gone unlisted too."""
        solver = (_STATIC / "solver.js").read_text()
        code = "\n".join(
            line for line in solver.splitlines() if not line.strip().startswith("//"))

        # Every mention but the `const editing = ...` that declares it.
        reads = len(re.findall(r"\bediting\b", code)) - 1

        assert "FIVE reads of `editing`" in solver
        assert reads == 5, reads

    def test_one_word_does_not_name_a_brush_on_one_page_and_a_wipe_on_the_other(
        self, admin_app
    ) -> None:
        """Owner decision, 2026-10-19: keep "Clear" for the player's fourth
        brush and rename the editor's board-wipe.

        CARD-247 renamed the player's fourth brush from "Undecided" to
        "Clear". The editor's reset button was already called "Clear", and the
        two pages share one renderer — so the same word named a brush that
        paints ONE cell undecided and a button that wipes the WHOLE board. The
        owner settled it by renaming this button rather than the brush.

        The button is pinned here because nothing pinned it before: at the time
        of the rename no test in the suite drove the editor's reset control by
        its label, so the old name could have come back and the suite would
        have stayed green. A naming decision with no mechanism is a decision
        that lasts until the next edit.

        The confirmation moves with the button, which is CARD-250's rule: a
        page that renames a control and leaves the sentence naming the old one
        lies about its own controls.
        """
        puzzle_id = seed(admin_app)
        html = admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True)

        labels = [re.sub(r"<[^>]+>", "", m).strip()
                  for m in re.findall(r"<button\b[^>]*>(.*?)</button>", html, re.S)]
        # A control is named by its text OR by an attribute, and the first
        # draft of this guard swept only the text (review cycle 2) — so an
        # aria-label, a title or an input value could have carried the word
        # while the assertion stayed green. Not reachable today, and that is
        # exactly when a guard is cheapest to widen. Deliberately NOT a
        # whole-page sweep: the page embeds the puzzle's own name, so a
        # puzzle called "Clear…" would red a guard that is about controls.
        named = labels + re.findall(r'(?:aria-label|title|value)="([^"]*)"', html)

        assert "Reset" in labels, labels
        # The owner's decision, as a guard rather than as a sentence: no
        # control on THIS page carries the word the brush now owns.
        assert not [n for n in named if "Clear" in n], named
        # And the question the button opens names the button (CARD-250).
        title = re.search(
            r'id="puzzle-player-confirm-title"[^>]*>([^<]*)<', html).group(1)
        assert "Reset" in title and "Clear" not in title, title

    def test_the_editor_page_claims_no_difficulty_of_its_own(self, admin_app) -> None:
        """F-008. The player's header badge is a fact about a stored grid; on
        the editor's page the stored grid is what is being rewritten, so the
        badge went stale on the first stroke — and the success message used to
        point the owner at it ("the difficulty shown above") after Approve had
        stored another tier. The difficulty is said in the save bar instead,
        twice: the grade one solve produced, then the row that was stored."""
        puzzle_id = seed(admin_app, difficulty_tier="hard", difficulty_score=91)
        client = admin_app.test_client()

        editor = client.get(EDITOR.format(puzzle_id)).get_data(as_text=True)
        player = client.get(f"/puzzle/{puzzle_id}/solve").get_data(as_text=True)

        assert "player-tier" not in editor
        assert "HARD" not in editor
        assert "difficulty shown above" not in (_STATIC / "puzzle_edit.js").read_text()
        # G-1: the player's header is untouched.
        assert "player-tier" in player and "HARD" in player

    def test_every_refusal_carries_a_reason_the_editor_branches_on(self, admin_app) -> None:
        """F-005, both halves so neither is true alone: CARD-245's refusals
        carry a machine-readable ``reason`` from the declared vocabulary, and
        the editor's script branches on those words.

        The two 409s need opposite advice — a forgotten verification costs one
        re-verify ("press Save again"), a book built on the puzzle means the
        edit cannot be stored at all — and a client that told them apart by
        matching the server's prose would break the moment the wording
        improved."""
        from nonogram.admin.app import EDIT_REFUSAL_REASONS

        client = admin_app.test_client()
        unique = seed(admin_app)
        unnameable = seed(admin_app)
        admin_app.puzzle_review_service.assign_to_book([unnameable], "")
        # CARD-251's three. `regrade_in_a_book` needs a booked puzzle whose
        # stored tier the replacement changes (the seed's is "hard" and
        # `solid_minus_corner` grades easy); `needs_confirmation` needs one
        # whose tier it does NOT change, so the save gets as far as the
        # question; `extent_changed` needs a verified grid of another size.
        regrading = seed_with_real_clues(admin_app, difficulty_tier="hard")
        book_a_puzzle(admin_app, regrading)
        booked = seed_with_real_clues(admin_app)
        book_a_puzzle(admin_app, booked)
        client.post(VERIFY.format(booked), json={"grid": solid_minus_corner()})
        resized = seed(admin_app)
        client.post(VERIFY.format(resized), json={"grid": solid(12, 15)})
        # CARD-291's: an APPROVED puzzle, and a verified replacement of the
        # same extent whose solve branches. The grids come from that card's
        # own test module, which pins both of their premises against the
        # solver — a local fourth copy of a 9x9 whose verifying solve has to
        # search would be a fixture with nothing checking it.
        guessing = seed_with_real_clues(
            admin_app, grid=LINE_GRID, strategies_used=["simple_overlap"]
        )
        assert admin_app.puzzle_review_service.approve_puzzle(guessing) is True
        client.post(VERIFY.format(guessing), json={"grid": GUESS_GRID})

        seen = {
            "not_unique": client.post(
                VERIFY.format(unique), json={"grid": two_cell_diagonal()}),
            "not_verified": client.post(
                SAVE.format(unique), json={"grid": solid_minus_corner()}),
            "in_a_book": client.post(
                VERIFY.format(unnameable), json={"grid": solid_minus_corner()}),
            "not_found": client.post(
                SAVE.format("11111111-2222-3333-4444-555555555555"),
                json={"grid": solid_minus_corner()}),
            "needs_confirmation": client.post(
                SAVE.format(booked), json={"grid": solid_minus_corner()}),
            "regrade_in_a_book": client.post(
                VERIFY.format(regrading), json={"grid": solid_minus_corner()}),
            "extent_changed": client.post(
                SAVE.format(resized), json={"grid": solid(12, 15)}),
            "needs_guessing": client.post(
                SAVE.format(guessing), json={"grid": GUESS_GRID}),
        }
        # Every declared reason is driven, not a subset of them: a reason the
        # routes gained without joining this map would leave the editor's
        # branch for it untested.
        from nonogram.admin.app import EDIT_REFUSAL_REASONS as _declared
        assert set(seen) == set(_declared), set(_declared) - set(seen)

        editor_js = (_STATIC / "puzzle_edit.js").read_text()
        for reason, response in seen.items():
            body = response.get_json()
            assert body["reason"] == reason, (reason, response.status_code, body)
            assert reason in EDIT_REFUSAL_REASONS
            # The words are still the server's; the reason only chooses what
            # the page adds to them.
            assert body["message"]
            assert f'"{reason}"' in editor_js, reason

    def test_the_refusal_vocabulary_is_load_bearing_on_both_sides(self) -> None:
        """G-007, and the source half of G-001's allow-list.

        ``EDIT_REFUSAL_REASONS`` was a declared vocabulary nothing read: the
        routes wrote their reasons as literals, the client branched on
        literals of its own, and the test above iterates the four reasons it
        already knows — so a fifth refusal could join the routes without
        joining either. That became load-bearing the moment "nothing was
        stored" turned into an ALLOW-LIST of the refusals CARD-245 answers
        WITHOUT writing (review cycle 2, G-001): a reason missing from one
        side of that seam is a page that cannot say what the store did, and
        a reason wrongly *present* on it is a page that says what it does
        not know. So both sides are read off the source and held to the
        tuple.

        If a refusal that DOES write ever has to exist, this is the test
        that stops it being added quietly: the tuple and the client's list
        would have to be split, on purpose, with the reason written down.
        """
        from nonogram.admin.app import EDIT_REFUSAL_REASONS

        start, stop = _EDIT_ROUTES
        source = (_ADMIN / "app.py").read_text()
        head = source.index(start)
        edit_routes = source[head:source.index(stop, head)]
        allow_list = re.search(
            r"const REFUSALS_THAT_NEVER_WRITE = \[(.*?)\];",
            (_STATIC / "puzzle_edit.js").read_text(),
            re.S,
        )

        # Every reason the two POST routes emit is in the vocabulary, and the
        # vocabulary has nothing the routes do not emit. TWO spellings are
        # read, because the routes use two: the inline body CARD-245 wrote,
        # and CARD-251's `_refused(reason, message, code, puzzle)` — one
        # refusal body, so every edit refusal carries the same fields.
        # RESIDUAL, stated rather than left as a claim of completeness: a
        # refusal emitted in some third shape (a reason held in a variable, a
        # dict built elsewhere and returned) is not matched. What catches that
        # is the OTHER direction, which is checked here too — a vocabulary
        # entry nothing in the slice emits fails this test — plus
        # ``test_every_refusal_carries_a_reason_the_editor_branches_on``,
        # which drives each reason through the real routes.
        emitted = set(re.findall(r'"reason":\s*"([a-z_]+)"', edit_routes))
        emitted |= set(re.findall(r'_refused\(\s*\n?\s*"([a-z_]+)"', edit_routes))
        assert emitted == set(EDIT_REFUSAL_REASONS), emitted
        # And the client's allow-list is that same set, so "nothing was
        # stored" is said for exactly the refusals that never write.
        assert allow_list is not None, "the client's allow-list was renamed"
        assert set(re.findall(r'"([a-z_]+)"', allow_list.group(1))) == set(
            EDIT_REFUSAL_REASONS)

    def test_the_stale_clue_disclosure_stands_above_the_board(self, admin_app) -> None:
        """F-012's relocation, pinned (review cycle 2, G-006).

        The clue numbers beside the editor's board are the STORED puzzle's
        and do not follow what the owner paints; Save recomputes them from
        the grid it stores. That sentence spent cycle 1 in the last clause of
        an eight-sentence usage hint BELOW the save bar, where an owner
        reading the gutters would never meet it — and nothing but the diff
        held it in its new place above the board, which is how it got into
        the old one.
        """
        puzzle_id = seed(admin_app)
        html = admin_app.test_client().get(EDITOR.format(puzzle_id)).get_data(as_text=True)
        flat = re.sub(r"\s+", " ", html)

        note = re.search(r'<p class="editor-note">(.*?)</p>', flat)
        assert note is not None, "the disclosure's own paragraph is gone"
        assert (
            "<strong>The clue numbers beside the board are still the stored "
            "puzzle's</strong>" in note.group(1)
        ), note.group(1)
        assert "do not follow what you paint" in note.group(1)
        # Above the board it is about, and above the save bar it warns the
        # owner before they reach.
        assert flat.index('class="editor-note"') < flat.index('id="puzzle-player"')
        assert flat.index('class="editor-note"') < flat.index('id="puzzle-editor"')

    def test_the_editor_adds_no_dependency_and_no_vendored_script(self) -> None:
        """G-5 / ADR-0038/R1. The baseline itself is pinned by
        ``TestDependencyBaseline_IsExactlyPillowAndNumpy`` (the named
        survivor); this is the page's own half of it."""
        editor_html = (_TEMPLATES / "puzzle_edit.html").read_text()

        assert "http://" not in editor_html
        assert "https://" not in editor_html
        assert "<style" not in editor_html

    def test_the_bars_refusals_never_reach_for_disabled(self) -> None:
        """CARD-250 G-3, CARD-211's pattern. ``disabled`` drops the focus to
        the document mid-flow, so this panel says "busy" with
        ``aria-disabled`` and leaves the button focusable. A one-word slip
        here is invisible to the flow tests — both spellings refuse the press
        — so it is read off the editor's own two files.

        **What this does not cover:** a third file doing it, and an
        ``aria-disabled`` left stale. The flow tests read the bar's
        ``aria-disabled`` at each step, which is what covers the second.
        """
        editor_html = (_TEMPLATES / "puzzle_edit.html").read_text()
        editor_js = (_STATIC / "puzzle_edit.js").read_text()

        assert "aria-disabled" in editor_js
        assert not re.search(r'(?<!aria-)disabled\s*=\s*"', editor_html), editor_html
        assert not re.search(r"(?<!aria-)disabled\s*=", editor_js)
        assert not re.search(r'setAttribute\(\s*"disabled"', editor_js)


# --------------------------------------------------------------------------
# AC-6 — the list the exits land on shows the picture that is stored now
# --------------------------------------------------------------------------


def _thumbnail_of(html: str, puzzle_id: str) -> str:
    """The ``src`` the list row draws this puzzle's grid from."""
    match = re.search(
        rf'<img src="(/api/puzzle/{re.escape(puzzle_id)}/grid[^"]*)"', html)
    assert match is not None, f"no thumbnail for {puzzle_id} on this page"
    return match.group(1)


def _approve_an_edit(app, puzzle_id: str, grid) -> None:
    """The two POSTs the editor makes, through the panel's own routes."""
    client = app.test_client()
    verified = client.post(VERIFY.format(puzzle_id), json={"grid": grid})
    assert verified.status_code == 200, verified.get_data(as_text=True)
    saved = client.post(SAVE.format(puzzle_id), json={"grid": grid})
    assert saved.status_code == 200, saved.get_data(as_text=True)


class TestPuzzleEditor_TheListShowsTheEditedPicture:
    """CARD-250 AC-6, **the card's failing-first one.**

    The list's thumbnail is ``/api/puzzle/<id>/grid`` — a STABLE url whose
    response carries a ``Content-Type`` and nothing else: no ``Cache-Control``
    and no validator. A browser that already holds that url's SVG is
    therefore entitled to redraw the row from it, and the owner who has just
    replaced the grid is shown the grid they replaced.

    The fix versions the url by ``manually_edited_at`` — CARD-245's own stamp
    (migration 016), which moves when and only when the grid moves. So an
    unedited puzzle's thumbnail still caches normally (the reason this was
    chosen over ``Cache-Control: no-cache`` on the route, which would make
    every thumbnail on every page re-fetch forever to fix a case that arises
    once per edit), and an edited one cannot be answered out of the cache of
    the picture it replaced.

    **What these tests assert, and what they do not.** They assert the two
    SVGs really differ and that the url the list hands the browser differs
    with them — which is what makes a cache hit impossible. They do not drive
    a real browser cache: that would be an assertion about Chromium's
    heuristic freshness, which is not this panel's to guarantee and not
    stable enough to test. The first test below fails on the pre-card tree,
    where the two urls were one string over two different pictures.
    """

    def test_the_rows_picture_is_not_the_url_of_the_picture_it_replaced(
        self, admin_app
    ) -> None:
        puzzle_id = seed(admin_app, grid=solid())
        client = admin_app.test_client()
        before = _thumbnail_of(client.get("/puzzles").get_data(as_text=True), puzzle_id)
        drawn_before = client.get(f"/api/puzzle/{puzzle_id}/grid").get_data(as_text=True)

        _approve_an_edit(admin_app, puzzle_id, solid_minus_corner())

        drawn_after = client.get(f"/api/puzzle/{puzzle_id}/grid").get_data(as_text=True)
        after = _thumbnail_of(client.get("/puzzles").get_data(as_text=True), puzzle_id)

        # Two different pictures — which is the whole reason one url for both
        # of them is the defect and not a cosmetic point.
        assert drawn_before != drawn_after
        assert after != before, after

    def test_a_second_edit_moves_it_again(self, admin_app) -> None:
        """A version key that moved once and then stopped would fix only the
        first edit. The stamp is rewritten by every save, so the url is."""
        puzzle_id = seed(admin_app, grid=solid())
        client = admin_app.test_client()

        _approve_an_edit(admin_app, puzzle_id, solid_minus_corner())
        once = _thumbnail_of(client.get("/puzzles").get_data(as_text=True), puzzle_id)
        _approve_an_edit(admin_app, puzzle_id, solid())
        twice = _thumbnail_of(client.get("/puzzles").get_data(as_text=True), puzzle_id)

        assert once != twice, (once, twice)

    def test_an_unedited_puzzles_thumbnail_is_left_cacheable(self, admin_app) -> None:
        """Why the url is versioned rather than the route told not to cache:
        a puzzle nobody has edited keeps the plain, cacheable url, so the fix
        costs the other thumbnails nothing."""
        untouched = seed(admin_app, grid=solid())
        edited = seed(admin_app, grid=solid())
        _approve_an_edit(admin_app, edited, solid_minus_corner())

        html = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert _thumbnail_of(html, untouched) == f"/api/puzzle/{untouched}/grid"
        assert "?" in _thumbnail_of(html, edited)

    def test_the_stamp_is_the_only_thing_the_version_carries(self, admin_app) -> None:
        """The version key is the row's own ``manually_edited_at`` and not a
        clock read at render time: a url that changed on every page load
        would re-fetch every thumbnail forever, which is the cost this option
        was chosen to avoid. Two renderings with no edit between them give
        the same url."""
        puzzle_id = seed(admin_app, grid=solid())
        _approve_an_edit(admin_app, puzzle_id, solid_minus_corner())
        client = admin_app.test_client()

        first = _thumbnail_of(client.get("/puzzles").get_data(as_text=True), puzzle_id)
        second = _thumbnail_of(client.get("/puzzles").get_data(as_text=True), puzzle_id)

        stamp = admin_app.puzzle_review_service.get_puzzle(puzzle_id)["manually_edited_at"]
        assert first == second
        assert quote(str(stamp), safe="") in first, (first, stamp)


# --------------------------------------------------------------------------
# The browser tier
# --------------------------------------------------------------------------


SIDE = 10
#: The stored puzzle every browser test starts from, and the edit of it the
#: owner makes by clearing cell (0, 0) with the White brush. CARD-245
#: measured what one solve says about that edit: easy, score 33.
STORED = solid(SIDE, SIDE)
EDITED = solid_minus_corner(SIDE, SIDE)

#: ``EDITED`` with a second cell cleared — the stroke an owner can land while
#: the store is writing (review cycle 1, F-001). Distinct from both STORED and
#: EDITED, so "which board is on screen afterwards" has an answer, and
#: distinct from the grid Approve sent, so "what was stored" has one too.
PAINTED_WHILE_STORING = [list(row) for row in EDITED]
PAINTED_WHILE_STORING[1][1] = False

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


def _wait_for_the_list(page) -> None:
    """CARD-250 AC-5: a stored edit LEAVES the editor for ``/puzzles``.

    So "the store said yes" is observed here as the list page, not as a
    sentence on a bar the browser has navigated away from. The sentence is
    still written before the exit — the store's answer is told whatever
    happens, because it is the only report of what the store did — and the
    test that reads the LEAVING one keeps the page by answering the
    navigation with a 204 (``..._a_second_approve_pressed_in_flight...``).
    The other sentence, the one the page says when a stroke landed while the
    store was writing, is read where it is genuinely on screen, because that
    branch does not navigate at all (review cycle 1, F-001:
    ``..._a_stroke_made_while_the_store_was_writing_keeps_the_page``).
    """
    page.wait_for_url("**/puzzles", timeout=20_000)


def _stay_on_the_editor(page) -> None:
    """Answer the exit's navigation with 204, so the editor's document stays.

    A test that reads the bar's LAST sentence needs the page that sentence is
    on, and that sentence's next act is to leave. ``route.abort()`` is no use
    — Chromium commits an error document for an aborted main-frame navigation
    — but a 204 has no content to commit, so the browser keeps the document it
    already has. It is a ``page.route`` interceptor, which is part of this
    file's declared page isolation.
    """
    page.route("**/puzzles", lambda route: route.fulfill(status=204, body=""))


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


_LOCAL_STORAGE = """() => Object.fromEntries(
  Object.keys(window.localStorage).map((key) => [key, window.localStorage.getItem(key)]))"""

#: Every state the save bar passes through, so "a refusal never stands beside
#: an Approve" is checked over the whole sequence and not only where it ends
#: up. ``tell()`` writes the message, the offer and the buttons' aria-disabled
#: in one task, so the observer records finished states and never a
#: half-written one.
_WATCH_BAR = """() => {
  window.__barStates = [];
  const message = document.getElementById('puzzle-editor-message');
  const decide = document.getElementById('puzzle-editor-decide');
  const save = document.getElementById('puzzle-editor-save');
  const record = () => window.__barStates.push({
    text: message.textContent,
    offered: !decide.hidden,
    busy: save.getAttribute('aria-disabled'),
  });
  record();
  new MutationObserver(record).observe(document.getElementById('puzzle-editor'), {
    subtree: true, childList: true, characterData: true, attributes: true,
  });
}"""
_BAR_STATES = "() => window.__barStates"

#: Press Save and paint, in ONE task: the stroke therefore lands while the
#: verify is still unanswered, with no timing to get wrong and no sleep.
_SAVE_THEN_PAINT = """([grid]) => {
  document.getElementById('puzzle-editor-save').click();
  const height = grid.length, width = grid[0].length;
  const cells = Object.freeze(grid.flat().map((filled) => (filled ? 'filled' : 'empty')));
  window.puzzlePlayer.setBoard(Object.freeze({ width, height, cells }));
}"""

#: Press Approve and paint, in ONE task: the stroke therefore lands while the
#: store's write is still unanswered — the window F-001 is about. Written out
#: rather than reusing ``_SAVE_THEN_PAINT`` with another id, because the two
#: races end differently and a test should not have to read which button a
#: shared helper pressed.
_APPROVE_THEN_PAINT = """([grid]) => {
  document.getElementById('puzzle-editor-approve').click();
  const height = grid.length, width = grid[0].length;
  const cells = Object.freeze(grid.flat().map((filled) => (filled ? 'filled' : 'empty')));
  window.puzzlePlayer.setBoard(Object.freeze({ width, height, cells }));
}"""

#: Press Approve and then Back to edit, in ONE task: the press therefore
#: lands while the store's write is unanswered. The state an owner cannot
#: reach (the Approve / Back to edit pair is ``hidden``), and the one a script
#: reaches at once -- the same forcing ``_SAVE_THEN_BACK`` does for the verify
#: case. Written out rather than parameterising that helper, because what the
#: two presses race ends differently and a test should not have to read which
#: request a shared helper was timed against (review cycle 2, F-002).
_STATE_AFTER = """{
    path: window.location.pathname,
    said: document.getElementById('puzzle-editor-message').textContent,
    busy: document.getElementById('puzzle-editor-leave').getAttribute('aria-disabled'),
    confirming: !document.getElementById('puzzle-editor-leave-confirm').hidden,
  }"""

_APPROVE_THEN_BACK = """() => {
  document.getElementById('puzzle-editor-approve').click();
  document.getElementById('puzzle-editor-back').click();
  return %s;
}""" % _STATE_AFTER

#: The store's write SUCCEEDED and the page has acted on it: either the
#: success is on the bar, or the bar is gone because the page left for the
#: list. Both of the two branches a success has are covered, so a test that
#: expects one of them reports which one happened instead of timing out on
#: the other -- and the test's own next assertions discriminate them
#: (``_asked_for_the_list(asked) == []`` and the url).
#:
#: A REFUSED write resolves neither disjunct -- no refusal sentence contains
#: "Saved" -- so that outcome still runs the wait out and fails on the clock.
#: Deliberate, and the reason this says "succeeded" rather than "whichever way
#: it went" (review cycle 2, F-003): the two branches this wait exists to
#: distinguish are both successes, a refusal on this path would be a defect
#: rather than a case, and a predicate widened to catch it would be three
#: sentences of coupling for a failure that is already loud, just slow.
_STORED_OR_LEFT = """() => {
  const message = document.getElementById('puzzle-editor-message');
  return message === null || message.textContent.includes('Saved');
}"""

#: Press Save and then Back to edit, in ONE task: the press therefore lands
#: while the verify is still unanswered — the state an owner cannot reach,
#: because the Approve / Back to edit pair is ``hidden``, and the state a
#: script reaches at once (review cycle 2, G-008). CARD-250 renamed the button
#: (it was Cancel) and left its behaviour alone, which is why this reads the
#: same as it did.
_SAVE_THEN_BACK = """() => {
  document.getElementById('puzzle-editor-save').click();
  document.getElementById('puzzle-editor-back').click();
}"""

#: Take the board's change announcement away from the editor, leaving the
#: other mechanism (Approve sends the grid it captured) to answer alone. A
#: capture-phase listener on ``window`` runs before the editor's own listener
#: on ``document`` can see the event. The name is read from solver.js, which
#: is where it is spelled.
_SUPPRESS_BOARD_CHANGE = """async () => {
  const { BOARD_CHANGE } = await import('/static/solver.js');
  window.addEventListener(BOARD_CHANGE, (event) => event.stopImmediatePropagation(), true);
  return BOARD_CHANGE;
}"""

#: Two presses in one task — the double click an owner can actually make.
_PRESS_TWICE = """([id]) => {
  const button = document.getElementById(id);
  button.click();
  button.click();
}"""


def _watch(page):
    """``(errors, asked)``: uncaught page errors and every request made.

    The error list is AC-5's standard read directly — "words the owner can act
    on, not an exception" — and no test of this file installed it before
    review cycle 1 (F-003), which is why an uncaught rejection on this page
    was invisible to the suite.
    """
    errors: list[str] = []
    asked: list[tuple] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: asked.append((request.url, request.post_data)))
    return errors, asked


def _posted(asked, end: str):
    """The grids posted to the route whose path ends with ``end``."""
    return [json.loads(data)["grid"] for url, data in asked if url.endswith(end) and data]


def _settle(page) -> None:
    """Wait until the answer in flight has been acted on, not merely received.

    Save's ``aria-disabled`` goes back to "false" in the handler's ``finally``,
    in the same continuation that then decides whether the answer still
    belongs to this turn — so this is the page's own signal that it has
    finished with the response. A sleep would be a guess; this is an
    observation, and it is why the assertions after it cannot pass by being
    read too early.
    """
    page.wait_for_function(
        "() => document.getElementById('puzzle-editor-save')"
        ".getAttribute('aria-disabled') === 'false'",
        timeout=20_000,
    )
    page.evaluate("() => new Promise((resolve) => setTimeout(resolve, 0))")


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

    def test_a_card_whose_book_cannot_be_named_offers_none(
        self, browser_page, live
    ) -> None:
        """AC-7 on the card, beside the list row and the route — for the
        membership CARD-251 left refused.

        **G-10, the retirement and its survivor.** This was
        ``test_a_booked_puzzles_card_offers_none`` and booked the puzzle with
        a real book, which the owner has since made editable behind a
        confirmation; the survivor is
        ``test_a_card_in_a_nameable_book_does_offer_one`` below, which asserts
        the control is there for that case. What the card still refuses is a
        book it cannot name — the one spelling of the rule,
        ``puzzle_is_editable`` over the store's ``_an_edit_may_touch``, which
        the card reads off ``/details`` rather than working out again.
        """
        puzzle_id = _seed_live(live, name="Booked")
        legacy_in_book(live, puzzle_id)
        browser_page.goto(f"{live.url}/puzzles")
        browser_page.locator(f'a.name[onclick*="{puzzle_id}"]').click()
        browser_page.get_by_role("link", name="Solve", exact=True).wait_for()

        assert browser_page.get_by_role("link", name=re.compile("^Edit")).count() == 0

    def test_a_card_in_a_nameable_book_does_offer_one(
        self, browser_page, live
    ) -> None:
        """CARD-251: the control the test above needs in order to mean
        anything — a booked puzzle's card offers Edit again."""
        puzzle_id = _seed_live(live, name="Booked")
        live.app.puzzle_review_service.assign_to_book([puzzle_id], make_book(live.scope))
        browser_page.goto(f"{live.url}/puzzles")
        browser_page.locator(f'a.name[onclick*="{puzzle_id}"]').click()
        browser_page.get_by_role("link", name="Solve", exact=True).wait_for()

        # Inside the card, not anywhere on the page: the list row carries one
        # of its own for this puzzle now, and counting both would not say
        # which surface answered.
        card = browser_page.locator("#puzzleDetailModal")
        assert card.get_by_role("link", name=re.compile("^Edit")).count() == 1


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
    """AC-3: Save shows the recomputed difficulty with Approve and Back to
    edit, and nothing is stored until Approve. (CARD-250 renamed that second
    button from Cancel, and gave Approve its exit to the list.)"""

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
        assert _button(browser_page, "Back to edit").is_visible()
        _assert_stored(live, puzzle_id, STORED)

    def test_approve_commits_the_grid_that_was_graded(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        _button(browser_page, "Approve").click()
        _wait_for_the_list(browser_page)

        row = live.app.puzzle_review_service.get_puzzle(puzzle_id)
        assert row["grid"] == EDITED
        assert row["difficulty_tier"] == MINUS_CORNER_TIER
        assert row["difficulty_score"] == MINUS_CORNER_SCORE
        assert row["manually_edited_at"] is not None
        # "The two-phase flow is over: there is nothing left to approve" used
        # to be read here, after ``_wait_for_the_list`` — i.e. on the list,
        # where ``#puzzle-editor-decide`` matches nothing and ``is_visible()``
        # is False whatever the editor did (review cycle 1, F-003). Its named
        # survivor is
        # ``..._a_second_approve_pressed_in_flight_is_not_sent_either``, which
        # keeps the document with a 204 and reads the offer out of the bar's
        # recorded states for the stored sentence as well as the storing one.

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
        _wait_for_the_list(browser_page)

        with pytest.raises(AssertionError):
            _assert_stored(live, puzzle_id, STORED)


@pytest.mark.browser
class TestPuzzleEditor_BackToEditKeepsTheEditAndStoresNothing:
    """CARD-246 AC-4 under CARD-250's name for it (AC-3).

    This button was labelled Cancel; CARD-250 renamed it to what it does and
    freed the name for the exit beside Save. **The behaviour is unchanged**,
    which is why this class needed a rename and nothing else — if it had
    needed more, something the owner did not ask to change had changed
    (CARD-250 G-1).
    """

    def test_back_to_edit_leaves_the_store_and_the_board_as_they_were(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        _button(browser_page, "Back to edit").click()
        said = _wait_for_message(browser_page, "Not saved")

        _assert_stored(live, puzzle_id, STORED)
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)
        assert not _approve_offered(browser_page)
        assert "still there" in said

    def test_the_edit_can_be_carried_on_and_saved_after_going_back(
        self, browser_page, live
    ) -> None:
        """The edit being "intact" means usable, not merely visible."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Back to edit").click()
        _wait_for_message(browser_page, "Not saved")

        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_the_list(browser_page)

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
        _wait_for_the_list(browser_page)

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
        """The narrowing: Maybe and Clear paint states a boolean grid
        cannot express, so the editor does not offer them."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _trigger(browser_page).click()

        assert browser_page.get_by_role("menuitemradio").count() == 2
        assert _menu_item(browser_page, "Black").is_visible()
        assert _menu_item(browser_page, "White").is_visible()
        assert _menu_item(browser_page, "Maybe").count() == 0
        # CARD-247 renamed the player's fourth brush to "Clear". Asserting the
        # OLD label here would be a control that cannot fail: no page in the
        # panel offers an item named "Undecided" any more, so the absence would
        # hold for every possible editor. The name asserted is the one the
        # player really shows (test_the_player_still_offers_all_four below sees
        # all four).
        assert _menu_item(browser_page, "Clear").count() == 0

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
        # The other half of G-001's allow-list: this refusal is one CARD-245
        # answers WITHOUT writing, so the page is entitled to the DEFINITE
        # sentence and must not hedge. A fix that said "not known" everywhere
        # would close G-001 by making the page useless, and this fails on it.
        assert "not known" not in said
        assert not _approve_offered(browser_page)
        _assert_stored(live, puzzle_id, STORED)
        # G-3 / CARD-211: focus is never dropped mid-flow. This is onApprove's
        # REFUSAL branch and it owns the ``save.focus()`` on that branch — one
        # of the handler's two, the other belonging to the success that KEEPS
        # the bar because a stroke landed mid-write (pinned by
        # ``test_a_stroke_made_while_the_store_was_writing_keeps_the_page``;
        # this comment said that branch did not exist, which fix cycle 1 made
        # false — review cycle 2, F-001). The one success with nowhere to
        # stand is the one that LEAVES (CARD-250 AC-5), which is why the
        # assertion retired from ``test_approving_from_the_keyboard_commits``
        # is pinned here (review cycle 1, F-002). Delete that one line of the
        # script and this fails.
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-save"

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
        _wait_for_the_list(browser_page)

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
        # message and not "Approve Back to edit" after it.
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
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-back"

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
        _wait_for_the_list(browser_page)

        assert _stored_grid(live, puzzle_id) == EDITED
        # Where focus went is no longer a question THIS path answers: the
        # approve asked about here leaves the editor (CARD-250 AC-5), so there
        # is no save bar left to stand on. It is the only outcome of which
        # that is true. The flow has THREE focus hops, each pinned on the
        # branch that owns it, and every one of them is a page the editor
        # keeps:
        #   * Back to edit — ``test_the_whole_flow_runs_from_the_keyboard``;
        #   * onApprove's refusal — ``..._asks_to_verify_again``;
        #   * onApprove's branch that STORED and stayed because a stroke
        #     landed mid-write —
        #     ``test_a_stroke_made_while_the_store_was_writing_keeps_the_page``
        #     (added in fix cycle 1, given its hop and its pin in fix
        #     cycle 2, review cycle 2 F-001).
        assert browser_page.url.endswith("/puzzles")

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
        the very puzzle being edited.

        **The entry is seeded first, and by the player itself** (review cycle
        1, F-006). Asserting an EMPTY localStorage passed with edit mode's
        ``NO_SAVE`` removed entirely — ``serializeState`` returns null unless
        the history starts all-UNKNOWN, and an edit-mode history starts
        FILLED/EMPTY, so the write only ever forgot — which made this control
        unable to fail for the claim it is named after. Against a real entry
        it fails for exactly that claim: with the save on, the editor reads
        it, opens on the player's half-solved board and overwrites it on its
        first stroke.
        """
        puzzle_id = _seed_live(live)
        browser_page.goto(f"{live.url}/puzzle/{puzzle_id}/solve")
        browser_page.wait_for_function("window.puzzlePlayer !== undefined")
        _cell(browser_page, 2, 3).click()
        before = browser_page.evaluate(_LOCAL_STORAGE)
        assert len(before) == 1, before

        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _cell(browser_page, 1, 1).click()

        assert browser_page.evaluate(_LOCAL_STORAGE) == before

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


# --------------------------------------------------------------------------
# AC-3 / AC-5 at the edges — the two-phase flow's invariant
# (review cycle 1, F-001..F-005)
# --------------------------------------------------------------------------


@pytest.mark.browser
class TestPuzzleEditor_TheOfferAndTheWordsAgree:
    """The page never offers Approve for a grid other than the one whose grade
    is on screen, and never states a store state it has not been told.

    One test per mechanism named in ``static/puzzle_edit.js``'s THE INVARIANT,
    each written so that it fails when that mechanism alone is taken out:

    1. ``tell()`` is the only writer of the message and of the offer, so a
       refusal cannot stand beside a live Approve (F-001).
    2. ``turn``: an answer about a grid that is no longer on the board is
       dropped instead of shown.
    3. one request at a time (F-001's root cause, and F-011's double click).
    4. the board announces its own changes, so a stroke made while a grade is
       on screen takes the offer away instead of being left out of a store the
       page then calls saved (F-002) — and Approve sends the grid it captured,
       which is pinned on its own below (F-004).

    And one allow-list, which is how the second half of the invariant is
    kept (review cycle 2, G-001): on a save the page says "nothing was
    stored" for the refusals CARD-245 answers WITHOUT writing and for nothing
    else. Three tests below give it an answer it cannot read — a 200 that
    parses as nothing after the store has committed, a gateway's 502, a
    reason this page has never been taught — and each asserts the page claims
    nothing; the two refusals that DO license the definite sentence assert
    that it is still said (``..._asks_to_verify_again``,
    ``..._says_this_edit_cannot_be_stored``), so neither half can be closed
    by abandoning the other.

    None of these defects could corrupt the store: CARD-245's gate held behind
    every one of them. What they did was tell the owner something that was not
    so, which is why the assertions here are about the words AND the control
    AND the store together.
    """

    def test_a_grid_being_checked_is_never_shown_beside_an_approve(
        self, browser_page, live
    ) -> None:
        """Mechanisms 1 and 3. A second Save on the SAME board — so nothing
        here can come from the board-change announcement — must take the
        offer away as the check starts: while the page says "Checking this
        grid...", an Approve beside it belongs to the grade that message has
        just replaced. Checked over every state the bar passed through, and
        the state is announced too (G-4: aria-disabled while in flight).
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        assert _approve_offered(browser_page)

        browser_page.evaluate(_WATCH_BAR)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        states = browser_page.evaluate(_BAR_STATES)
        checking = [state for state in states if "Checking this grid" in state["text"]]
        assert checking, states
        assert not any(state["offered"] for state in checking), states
        assert all(state["busy"] == "true" for state in checking), states
        # The flow ends where it should: a grade, and an Approve for it.
        assert _approve_offered(browser_page)
        assert _button(browser_page, "Save").get_attribute("aria-disabled") == "false"

    def test_a_refusal_never_stands_beside_an_approve(self, browser_page, live) -> None:
        """F-001 as the reviewer reached it. A refusal arriving while an
        Approve was already on offer left the two side by side — "This grid
        cannot be saved and nothing was stored" with a button that stored it.
        The board does not move between the two Saves here, so the offer can
        only be taken away by the sentence that replaces it.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        assert _approve_offered(browser_page)

        browser_page.route(
            re.compile(r"/edit/verify$"),
            lambda route: route.fulfill(
                status=422,
                content_type="application/json",
                body=json.dumps({
                    "ok": False,
                    "reason": "not_unique",
                    "message": "the clue set has 2 or more solutions",
                }),
            ),
        )
        browser_page.evaluate(_WATCH_BAR)
        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "cannot be saved")

        refusals = [
            state for state in browser_page.evaluate(_BAR_STATES)
            if "cannot be saved" in state["text"]
        ]
        assert refusals
        assert not any(state["offered"] for state in refusals), refusals
        assert not _approve_offered(browser_page)
        assert _button(browser_page, "Approve").count() == 0
        assert "2 or more solutions" in said
        _assert_stored(live, puzzle_id, STORED)

    def test_a_second_save_pressed_in_flight_is_not_sent(
        self, browser_page, live
    ) -> None:
        """Mechanism 3. Two verifies in flight at once is what let a refusal
        land after a grade; two presses in one task are now one request."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        errors, asked = _watch(browser_page)

        browser_page.evaluate(_PRESS_TWICE, ["puzzle-editor-save"])
        _wait_for_message(browser_page, "Difficulty")

        assert len(_posted(asked, "/edit/verify")) == 1, asked
        assert _approve_offered(browser_page)
        assert errors == []

    def test_a_second_approve_pressed_in_flight_is_not_sent_either(
        self, browser_page, live
    ) -> None:
        """Mechanism 3, and F-011: this page's own guarantee now.

        A double Approve used to send two POSTs, and both only succeeded
        because CARD-245 deliberately does not consume a verification ("A
        verification is not consumed by a save" —
        ``save_edited_grid``'s docstring). That made the safety a property of
        the other card, recorded nowhere here; it is one request now, and the
        two responses can no longer race to write the message.

        TWO mechanisms make that true, and both are taken on every Approve:
        the sentence that announces the store WITHDRAWS the offer (``tell``'s
        one writer, so ``verified`` is null and the second press has nothing
        to send), and the single-flight guard refuses the second press
        outright. Review cycle 2 removed each alone and the file still passed,
        so only the pair was pinned. The offer half is asserted here — no
        state of the bar that says "Storing this grid" has an Approve beside
        it — which leaves the guard as the one unpinned half, and that is the
        honest state for a redundancy kept so a reader of ``onApprove`` need
        not reason about ``tell``'s side effect to see that one request is
        sent.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, asked = _watch(browser_page)
        browser_page.evaluate(_WATCH_BAR)
        # The sentence this test reads is the last thing the editor says
        # before it leaves for the list (CARD-250 AC-5), so the navigation is
        # aborted and the document stays. What is asserted below is unchanged:
        # the store's answer is told, with no Approve beside it, and one POST
        # was sent.
        _stay_on_the_editor(browser_page)

        browser_page.evaluate(_PRESS_TWICE, ["puzzle-editor-approve"])
        said = _wait_for_message(browser_page, "Saved")

        assert _posted(asked, "/edit") == [EDITED], asked
        assert _stored_grid(live, puzzle_id) == EDITED
        assert "the grid you verified" in said
        # The LEAVING tail, which is the one that belongs to this path: the
        # store's two sentences share a head and differ in what the page says
        # it does next (review cycle 1, F-001), so reading the head alone
        # would not notice the staying sentence standing here.
        assert "Showing the puzzle list" in said
        # And the staying tail is NOT standing here beside it. This is the
        # mirror of the guard the staying test carries, and the pair completes
        # the 2x2: each tail pinned present on its own branch and absent from
        # the other. Without it a sentence of head + BOTH tails passed the
        # whole file -- the page claiming in one breath to stay and to show
        # the list, and then navigating (review cycle 2, F-004; measured, not
        # argued: that mutant survived 108 tests and dies on this line).
        assert "the editor stays open" not in said, said
        assert errors == []
        # The offer really is down for the whole of the store's write, which
        # is the mechanism and not a by-product of the guard.
        states = browser_page.evaluate(_BAR_STATES)
        storing = [state for state in states if "Storing this grid" in state["text"]]
        assert storing, states
        assert not any(state["offered"] for state in storing), storing
        # And down for the STORED state too — "the two-phase flow is over,
        # there is nothing left to approve". That used to be read after the
        # exit, on a page where ``#puzzle-editor-decide`` does not exist and
        # so was true of every implementation (review cycle 1, F-003); here
        # the 204 keeps the document, the observer has the state, and the
        # assertion can fail.
        saved = [state for state in states if "Saved" in state["text"]]
        assert saved, states
        assert not any(state["offered"] for state in saved), saved

    def test_a_stroke_while_the_grid_is_being_checked_is_not_graded(
        self, browser_page, live
    ) -> None:
        """Mechanism 2. The stroke lands in the same task as the Save, so the
        server's answer comes back about a grid that is no longer on the
        board. It is dropped: a grade — and an Approve — for the grid the
        owner has just painted over is the one thing this page must not show.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)

        with browser_page.expect_response(
            lambda response: response.url.endswith("/edit/verify")
        ) as answer:
            browser_page.evaluate(_SAVE_THEN_PAINT, [EDITED])
        # It really was a grade that got dropped, not a refusal.
        assert answer.value.status == 200
        _settle(browser_page)

        said = _message(browser_page)
        assert "The board has changed" in said
        assert "Difficulty" not in said
        assert not _approve_offered(browser_page)
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)
        _assert_stored(live, puzzle_id, STORED)
        # And the flow is not stuck: the grid on the board is one Save away.
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        assert _approve_offered(browser_page)

    def test_a_stroke_after_the_grade_takes_the_approval_away_and_says_so(
        self, browser_page, live
    ) -> None:
        """F-002, the card's most user-visible defect. A stroke made while
        the confirmation was up was left out of the store without a word,
        and the page said "Saved. This grid is the stored puzzle now" over a
        board that was not the stored grid. The offer goes the moment the
        board stops being the grid that was graded, so the stroke cannot be
        the thing nobody mentions.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        assert _approve_offered(browser_page)

        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()

        said = _message(browser_page)
        assert "The board has changed" in said
        assert "nothing was stored" in said
        assert "Saved" not in said
        assert not _approve_offered(browser_page)
        assert _button(browser_page, "Approve").count() == 0
        _assert_stored(live, puzzle_id, STORED)

    def test_and_that_stroke_is_what_the_next_save_stores(
        self, browser_page, live
    ) -> None:
        """The correction costs one re-verify and no work: the grid the owner
        can see is the grid the next Save grades and Approve stores — so the
        stroke is not merely reported, it is keepable."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _wait_for_message(browser_page, "The board has changed")

        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_the_list(browser_page)

        assert _stored_grid(live, puzzle_id) == EDITED

    def test_approve_sends_the_graded_grid_and_never_re_reads_the_board(
        self, browser_page, live
    ) -> None:
        """Mechanism 4's other half, F-004, and the mutant that survived
        review cycle 1: Approve reading the board again instead of sending
        the grid it captured passed all 49 tests.

        It is tested with mechanism 4's *announcement* suppressed, because
        with both in place the two implementations are indistinguishable
        through the UI — a board that has moved never reaches Approve at all.
        Suppressed, the capture is left to answer alone: the POST carries the
        grid that was graded, and that is what the store holds. **This test
        fails if Approve starts reading the board again**, whichever way the
        store then answers.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        browser_page.evaluate(_SET_GRID, [EDITED])
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, asked = _watch(browser_page)

        assert browser_page.evaluate(_SUPPRESS_BOARD_CHANGE) == "puzzle-board-change"
        _tool(browser_page, "Black")
        _cell(browser_page, 0, 0).click()
        # The board is now the stored grid again, and no verification of it
        # exists — so a re-read would be visible both in the POST and in the
        # store's answer to it.
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(STORED)
        assert _approve_offered(browser_page), "the suppression did not take"

        _button(browser_page, "Approve").click()
        _wait_for_the_list(browser_page)

        assert _posted(asked, "/edit") == [EDITED], asked
        assert _stored_grid(live, puzzle_id) == EDITED
        assert errors == []

    def test_a_dropped_connection_on_save_is_told_in_words(
        self, browser_page, live
    ) -> None:
        """F-003. ``fetch`` was unwrapped, so a network failure rejected out
        of the handler: the message stayed on "Checking this grid...", an
        uncaught "Failed to fetch" reached the console and the owner was told
        nothing — while ``refusalText``'s own "could not be reached" branch
        sat unreachable, which is the evidence the case was meant to be
        handled. AC-5's standard is words, not an exception.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        errors, _asked = _watch(browser_page)
        browser_page.route(re.compile(r"/edit/verify$"), lambda route: route.abort())
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "could not be reached")

        assert "Checking this grid" not in said
        assert "nothing was stored" in said
        assert not _approve_offered(browser_page)
        assert errors == [], errors
        _assert_stored(live, puzzle_id, STORED)
        # Still usable: the refusal is a step, not the end of the flow.
        browser_page.unroute(re.compile(r"/edit/verify$"))
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

    def test_a_dropped_connection_on_approve_claims_nothing_about_the_store(
        self, browser_page, live
    ) -> None:
        """F-003 where it is worse: on Approve the request may or may not have
        committed, and the page is the only thing that can say so. It says
        that it does not know and what to do about it — never "Saved", and
        never nothing.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, _asked = _watch(browser_page)
        browser_page.route(re.compile(r"/edit$"), lambda route: route.abort())

        _button(browser_page, "Approve").click()
        said = _wait_for_message(browser_page, "not known")

        assert "Saved" not in said
        assert "Reload the page" in said
        assert not _approve_offered(browser_page)
        assert errors == [], errors
        # The request never reached the panel, so in fact nothing was stored —
        # which the page is right not to claim either way.
        _assert_stored(live, puzzle_id, STORED)

    def test_a_save_whose_answer_cannot_be_read_claims_nothing_about_the_store(
        self, browser_page, live
    ) -> None:
        """G-001, and the one case where the page could be read as lying
        about a write that really happened.

        The save REACHES the panel and commits; only the ANSWER is replaced,
        with a 200 carrying markup instead of JSON — a reverse proxy's error
        page, a login wall, a panel mid-deploy. ``post()`` hands back that
        code with ``body: null``, and the page used to narrate it as "Nothing
        was stored. The panel answered with 200, which this page does not
        know how to act on" while the stored grid was the edited one. The
        owner's act on that sentence is a second Save: a second solve and a
        second ``manually_edited_at`` stamp for a grid that was already in.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, _asked = _watch(browser_page)

        def answered_with_markup(route):
            route.fetch()  # the panel really does get the save, and writes
            route.fulfill(
                status=200, content_type="text/html", body="<html>not json</html>")

        browser_page.route(re.compile(r"/edit$"), answered_with_markup)
        _button(browser_page, "Approve").click()
        said = _wait_for_message(browser_page, "not known")

        # The store DID write, which is exactly why the page may not say it
        # did not — and may not say it did either.
        assert _stored_grid(live, puzzle_id) == EDITED
        assert "nothing was stored" not in said.lower(), said
        assert "Saved" not in said
        assert "Reload the page" in said
        assert not _approve_offered(browser_page)
        assert errors == [], errors

    def test_a_gateway_error_on_a_save_claims_nothing_about_the_store(
        self, browser_page, live
    ) -> None:
        """G-001 in the shape production actually runs: the panel is behind a
        proxy, and a gateway that gives up AFTER the app committed answers
        502 with no body the page can read. "Nothing was stored" is a claim
        about a store this page has not been told about, whichever way the
        timing fell, and the catch-all branch made it for every code outside
        200/404/409/422.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, _asked = _watch(browser_page)
        browser_page.route(
            re.compile(r"/edit$"),
            lambda route: route.fulfill(
                status=502, content_type="text/html", body="<html>Bad Gateway</html>"),
        )

        _button(browser_page, "Approve").click()
        said = _wait_for_message(browser_page, "not known")

        assert "502" in said
        assert "nothing was stored" not in said.lower(), said
        assert "Saved" not in said
        assert "Reload the page" in said
        assert not _approve_offered(browser_page)
        assert errors == [], errors
        # This save never reached the panel, so in fact nothing was stored —
        # which the page is right not to claim either way.
        _assert_stored(live, puzzle_id, STORED)

    def test_a_refusal_reason_this_page_was_never_taught_claims_nothing(
        self, browser_page, live
    ) -> None:
        """G-001's allow-list from the other end: the fifth reason.

        "Nothing was stored" is said for the four refusals CARD-245 answers
        without writing, named in ``puzzle_edit.js``'s
        ``REFUSALS_THAT_NEVER_WRITE`` and tied to the server's
        ``EDIT_REFUSAL_REASONS`` by
        ``test_the_refusal_vocabulary_is_load_bearing_on_both_sides``. A
        reason outside that list is one this page knows nothing about, so it
        fails safe — it hedges, and still relays the server's own words —
        rather than making the claim the invariant forbids. Patching each
        branch with ``storing`` instead would have left this case claiming.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, _asked = _watch(browser_page)
        browser_page.route(
            re.compile(r"/edit$"),
            lambda route: route.fulfill(
                status=422,
                content_type="application/json",
                body=json.dumps({
                    "ok": False,
                    "reason": "too_large",
                    "message": "a grid this big is not stored here",
                }),
            ),
        )

        _button(browser_page, "Approve").click()
        said = _wait_for_message(browser_page, "not known")

        assert "a grid this big is not stored here" in said  # still the server's words
        assert "nothing was stored" not in said.lower(), said
        assert "Saved" not in said
        assert not _approve_offered(browser_page)
        assert errors == [], errors

    def test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer(
        self, browser_page, live
    ) -> None:
        """G-008. ``onBackToEdit`` is a writer-caller like the others and
        spends the turn.

        An owner cannot reach Back to edit while a request is in flight — the
        pair it sits in is ``hidden``, and this panel's CSS makes that
        ``display: none`` — so the guarantee rested on another element's
        visibility, which is not a guarantee. Forced with a scripted click
        during the verify, the press used to be silently undone by the grade
        that landed after it: the message went back to a difficulty and the
        Approve came back up, for a flow the owner had just abandoned.

        A SAVE's answer is still never dropped, whatever turn it lands in,
        because it is the only report of what the store did — so this spends
        the turn without giving the press the power to silence the store.

        **CARD-250 changed nothing here, on purpose** (G-1), and this is the
        test that says so: the button was renamed from Cancel and its
        mid-flight behaviour is the one asserted above. The exit that CARD-250
        *did* add — Cancel, beside Save — is refused mid-flight instead, which
        is ``TestPuzzleEditor_NoExitWhileTheStoreIsDeciding``; the asymmetry is
        that Back to edit never leaves the page, so it has nothing to outrun.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        errors, _asked = _watch(browser_page)

        with browser_page.expect_response(
            lambda response: response.url.endswith("/edit/verify")
        ) as answer:
            browser_page.evaluate(_SAVE_THEN_BACK)
        # It really was a grade that got dropped, not a refusal.
        assert answer.value.status == 200
        _settle(browser_page)

        said = _message(browser_page)
        assert "your edit is still there" in said, said
        assert "Difficulty" not in said
        assert not _approve_offered(browser_page)
        assert errors == [], errors
        _assert_stored(live, puzzle_id, STORED)
        # And the flow is still usable: it abandoned a check, not the page.
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

    def test_a_puzzle_that_entered_a_book_says_this_edit_cannot_be_stored(
        self, browser_page, live
    ) -> None:
        """F-005, and AC-7's fourth half: the editor's own words for the 409
        a book causes.

        Both 409s used to get the not-verified one's advice — "Press Save to
        check this grid again", an instruction that can never succeed, handed
        to an owner holding an edit they cannot store. CARD-245 tells them
        apart on the wire (``reason``), so this page tells them apart in
        words.

        **CARD-251 changed which 409 that is.** A puzzle in a book the panel
        can name is editable now, so the refusal an owner meets by painting a
        booked puzzle is the REGRADE one — this board's stroke takes the
        stored ``medium`` row to an Easy grid, and a book's order is grouped
        by level (INV-009). The words are the same shape and the same
        promise: the edit cannot be stored, nothing was stored, and the advice
        is one that can succeed. The other case, where the tier does not move
        and the page asks its question instead, is
        :class:`TestBookedEdit_TheQuestionNamesTheBook`.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _tool(browser_page, "White")
        _cell(browser_page, 0, 0).click()
        errors, _asked = _watch(browser_page)
        live.app.puzzle_review_service.assign_to_book([puzzle_id], make_book(live.scope))

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "cannot be stored")

        assert "grouped by difficulty level" in said
        assert "take the puzzle out of the book" in said.lower()
        assert "Nothing was stored" in said
        assert "not known" not in said  # a refusal that never writes is known
        # The advice that can never succeed is gone.
        assert "Press Save" not in said
        assert not _approve_offered(browser_page)
        assert "Error" not in said and "Traceback" not in said
        assert errors == [], errors
        _assert_stored(live, puzzle_id, STORED)


# --------------------------------------------------------------------------
# CARD-250 — the two bars say what they do, and both exits land on the list
# (AC-1, AC-2, AC-3's rename proved by use, AC-4, AC-5, AC-7, AC-8)
# --------------------------------------------------------------------------


#: Every button the save bar carries, by the label it shows — read off the
#: rendered page, which is what AC-4 asks for: the words a message uses are
#: held against the bar the owner is actually looking at, never against a
#: list written down in a test. Hidden buttons count: the Approve pair and
#: the leave confirmation are on the bar, they are just not on screen yet.
_BAR_LABELS = """() => [...document.querySelectorAll('#puzzle-editor button')]
  .map((button) => button.textContent.trim())"""

#: The labels of the pair the grade's sentence offers.
_DECIDE_LABELS = """() => [...document.querySelectorAll('#puzzle-editor-decide button')]
  .map((button) => button.textContent.trim())"""

#: The tier word in the message, and the colour it actually wears.
_TIER_WORD = """() => {
  const span = document.getElementById('puzzle-editor-grade');
  const message = document.getElementById('puzzle-editor-message');
  return {
    text: span.textContent,
    tier: span.dataset.tier,
    colour: getComputedStyle(span).color,
    prose: getComputedStyle(message).color,
  };
}"""

#: The same reading from the list's tier chip, row by row, so "the same
#: colour" is measured on both surfaces inside one test.
_BADGE_COLOURS = """([ids]) => Object.fromEntries(Object.entries(ids).map(([tier, id]) => {
  const link = document.querySelector(`a[onclick*="${id}"]`);
  const badge = link.closest('tr').querySelector('.badge.tier');
  return [tier, { text: badge.textContent.trim(), colour: getComputedStyle(badge).color }];
}))"""

#: What the bar says and does in the SAME TASK as a press made while a
#: request is unanswered. Read there rather than after, because the honest
#: question is what the press did at the moment it was made: a fetch cannot
#: resolve inside the task that started it, so nothing has answered yet.

_APPROVE_THEN_LEAVE = """() => {
  document.getElementById('puzzle-editor-approve').click();
  document.getElementById('puzzle-editor-leave').click();
  return %s;
}""" % _STATE_AFTER

_SAVE_THEN_LEAVE = """() => {
  document.getElementById('puzzle-editor-save').click();
  document.getElementById('puzzle-editor-leave').click();
  return %s;
}""" % _STATE_AFTER

_SAVE_THEN_LEAVE_ANYWAY = """() => {
  document.getElementById('puzzle-editor-save').click();
  document.getElementById('puzzle-editor-leave-accept').click();
  return %s;
}""" % _STATE_AFTER

_SAVE_THEN_BACK_WITH_STATE = """() => {
  document.getElementById('puzzle-editor-save').click();
  document.getElementById('puzzle-editor-back').click();
  return %s;
}""" % _STATE_AFTER


def _confirm_open(page) -> bool:
    return page.locator("#puzzle-editor-leave-confirm").is_visible()


def _asked_for_the_list(asked) -> list[str]:
    return [url for url, _data in asked if url.endswith("/puzzles")]


def _paint_a_cell(page) -> None:
    """One recorded stroke — the board change this page hears about."""
    _tool(page, "White")
    _cell(page, 0, 0).click()


@pytest.mark.browser
class TestPuzzleEditor_CancelLeavesTheEditor:
    """CARD-250 AC-1. The exit that did not exist: beside Save, Cancel leaves
    the editor and stores nothing.

    The name was freed by renaming the old Cancel to Back to edit — the two
    items have to be read together, because two buttons both called Cancel
    meaning different things on one bar is not a design anyone asked for.
    """

    def test_cancel_goes_to_the_list_and_stores_nothing(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live, name="Owl")
        _open_editor(browser_page, live, puzzle_id)
        errors, asked = _watch(browser_page)

        _button(browser_page, "Cancel").click()
        _wait_for_the_list(browser_page)

        assert browser_page.url.endswith("/puzzles")
        # The list it lands on is the one this puzzle is on.
        assert browser_page.locator(f'a[onclick*="{puzzle_id}"]').count() >= 1
        _assert_stored(live, puzzle_id, STORED)
        # Nothing was even asked of the store: this exit is not a save.
        assert _posted(asked, "/edit") == [], asked
        assert _posted(asked, "/edit/verify") == [], asked
        assert errors == [], errors

    def test_it_leaves_from_the_keyboard_too(self, browser_page, live) -> None:
        """CARD-211's standard on the new control: reachable, and it does the
        same thing from Enter as from a click."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)

        _button(browser_page, "Save").focus()
        browser_page.keyboard.press("Tab")
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-leave"

        browser_page.keyboard.press("Enter")
        _wait_for_the_list(browser_page)

        assert browser_page.url.endswith("/puzzles")
        _assert_stored(live, puzzle_id, STORED)


@pytest.mark.browser
class TestPuzzleEditor_CancelAsksOnlyWhenThereIsSomethingToLose:
    """CARD-250 AC-2. A confirm on every exit trains the owner to dismiss it;
    no confirm at all loses work to a mis-click. So it asks exactly when the
    board has changed since it was opened — the fact this page is already
    told, by the one place a change is recorded (``BOARD_CHANGE``).

    It asks in the page (``role="alertdialog"``), which is the rule Clear's
    confirmation already follows, and never ``window.confirm``.
    """

    def test_an_unchanged_board_is_not_asked_about(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        assert not _confirm_open(browser_page)

        _button(browser_page, "Cancel").click()
        _wait_for_the_list(browser_page)

        assert browser_page.url.endswith("/puzzles")

    def test_a_changed_board_is_asked_about_and_declining_keeps_the_edit(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, asked = _watch(browser_page)

        _button(browser_page, "Cancel").click()

        assert _confirm_open(browser_page)
        assert browser_page.url.endswith("/editor")
        assert _asked_for_the_list(asked) == [], asked
        # Asked in the page, and the keyboard is put on the safe answer.
        dialog = browser_page.locator("#puzzle-editor-leave-confirm")
        assert dialog.get_attribute("role") == "alertdialog"
        assert browser_page.evaluate(
            "() => document.activeElement.id") == "puzzle-editor-leave-keep"
        assert "not stored" in dialog.text_content()
        assert _button(browser_page, "Cancel").get_attribute("aria-expanded") == "true"

        _button(browser_page, "Keep editing").click()

        assert not _confirm_open(browser_page)
        assert browser_page.url.endswith("/editor")
        assert _asked_for_the_list(asked) == [], asked
        # The edit is intact and USABLE, not merely still drawn.
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)
        _assert_stored(live, puzzle_id, STORED)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        assert errors == [], errors

    def test_confirming_leaves_and_still_stores_nothing(self, browser_page, live) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)

        _button(browser_page, "Cancel").click()
        _button(browser_page, "Leave editor").click()
        _wait_for_the_list(browser_page)

        assert browser_page.url.endswith("/puzzles")
        _assert_stored(live, puzzle_id, STORED)

    def test_escape_answers_it_the_way_keep_editing_does(self, browser_page, live) -> None:
        """Clear's confirmation closes on Escape; a second dialog on the same
        page that did not would be two behaviours for one gesture."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Cancel").click()
        assert _confirm_open(browser_page)

        browser_page.keyboard.press("Escape")

        assert not _confirm_open(browser_page)
        assert browser_page.url.endswith("/editor")
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-leave"

    def test_it_asks_about_a_board_that_was_painted_and_then_undone(
        self, browser_page, live
    ) -> None:
        """The fact this page holds is "the board has CHANGED since it was
        opened", which is what it is told. It is deliberately not "the board
        differs from the stored grid now", which would need a comparison this
        file does not make — a second notion of a changed board beside the one
        invariant 4 already rests on, and the kind of duplicate that drifts.

        Undo is itself a recorded change, so a painted-then-undone board still
        asks. That is the conservative direction: it costs one extra question
        and it never loses a stroke.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Undo").click()
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(STORED)

        _button(browser_page, "Cancel").click()

        assert _confirm_open(browser_page)
        assert browser_page.url.endswith("/editor")

    def test_the_question_is_asked_in_the_page_and_never_by_the_browser(self) -> None:
        """``window.confirm`` blocks the page, cannot be styled and cannot be
        read by the live region; ``solver.js``'s PROGRESS contract says
        "never window.confirm" for Clear, and this is the same rule for the
        second dialog on the same page."""
        editor_js = (_STATIC / "puzzle_edit.js").read_text()
        code = "\n".join(
            line for line in editor_js.splitlines() if not line.strip().startswith("//"))

        assert "window.confirm" not in code
        assert "confirm(" not in code
        assert 'role="alertdialog"' in (_TEMPLATES / "puzzle_edit.html").read_text()


@pytest.mark.browser
class TestPuzzleEditor_TheWordsNameTheButtonsThatExist:
    """CARD-250 AC-4. No message this page can show tells the owner to press
    something that is not on the bar.

    The bar's labels are read off the rendered page; the messages are got by
    importing the module and calling every one of them, over a seeded corpus
    for the refusals (no ``hypothesis``: not in the dependency baseline).

    **What this checks:** every place a message says "press X" or "or X" with
    a capitalised X, X is a label the bar carries. That is the defect the
    rename could have left behind — ``gradeText`` ended "or Cancel to go on
    editing" while the bar's Cancel became an exit from the page.

    **What it does not check,** stated rather than implied: a message could
    refer to a control without naming it ("the green button") and this would
    not see it; and a label that IS on the bar but means something else is a
    question about meaning, which no text predicate can answer. Both
    "Cancel" and "Back to edit" are labels now, so naming the wrong one of
    the two would pass here. What catches THAT is
    ``test_the_button_the_grade_names_is_the_one_that_goes_back`` below,
    which reads the name out of the message and presses it.
    """

    #: Where this file's prose names a control: "press X", "Press X", "or X".
    _NAMES_A_CONTROL = re.compile(r"\b(?:[Pp]ress|or)\s+(?=[A-Z])")

    def _every_message(self, page) -> list[str]:
        rng = random.Random(250)
        reasons = [None, "not_unique", "not_verified", "in_a_book", "not_found",
                   "needs_confirmation", "regrade_in_a_book", "extent_changed",
                   "too_large"]
        codes = [0, 200, 404, 409, 422, 500, 502, 504]
        # The server's own prose, relayed: lower-case sentences, as CARD-245's
        # messages are. What the server says is the server's claim, not this
        # page's claim about its own controls.
        said_by_the_server = [
            "the clue set has 2 or more solutions",
            "this grid is not the one you verified",
            "a puzzle in a book keeps its grid",
            "no such puzzle",
            "",
        ]
        refusals = [
            [
                rng.choice(codes),
                rng.choice(said_by_the_server),
                rng.choice(reasons),
                rng.choice([True, False]),
            ]
            for _ in range(120)
        ]
        grades = [
            {"difficulty_tier": tier, "difficulty_score": rng.randrange(0, 101)}
            for tier in ("easy", "medium", "hard", "guess", "fiendish")
        ]
        cells = [
            [[rng.randrange(0, 10), rng.randrange(0, 10)] for _ in range(count)]
            for count in (1, 2, 6, 7, 40)
        ]
        # Every shape of the book clause CARD-251 added, so the sentences it
        # can produce are held to the same rule as every other message.
        books = [
            {"id": "b1", "title": "Winter Pictures", "published": False,
             "pages": {"known": True, "changes": False, "added": 0,
                       "partner": "snowflake.png"}},
            {"id": "b2", "title": "Winter Nights", "published": True,
             "pages": {"known": True, "changes": True, "added": 1,
                       "partner": "Robin"}},
            {"id": "b3", "title": None, "published": False,
             "pages": {"known": False, "changes": None, "added": None,
                       "partner": None}},
            {"id": "b4", "title": "Alone", "published": False,
             "pages": {"known": True, "changes": True, "added": 1,
                       "partner": None}},
            # Review cycle 1, F-001/F-004: `added` is a signed count and the
            # sentence is built from it, so both directions and a magnitude
            # above one are shapes the message rule has to hold for too.
            {"id": "b5", "title": "Shorter", "published": False,
             "pages": {"known": True, "changes": True, "added": -1,
                       "partner": None}},
            {"id": "b6", "title": "Longer still", "published": True,
             "pages": {"known": True, "changes": True, "added": 2,
                       "partner": "Robin"}},
        ]
        said = page.evaluate(_MESSAGE_CORPUS, [refusals, grades, cells, books])
        # The two sentences written inline by the handlers rather than
        # exported, read off the source so the corpus is the whole vocabulary
        # and not only the exported half.
        said += re.findall(r'tell\("([^"]+)"\)', (_STATIC / "puzzle_edit.js").read_text())
        return said

    def test_no_message_names_a_button_the_bar_does_not_carry(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        labels = browser_page.evaluate(_BAR_LABELS)
        said = self._every_message(browser_page)

        assert len(labels) >= 4, labels
        assert len(said) >= 130, len(said)
        offences = [
            (message[match.end():match.end() + 24], message)
            for message in said
            for match in self._NAMES_A_CONTROL.finditer(message)
            if not any(message.startswith(label, match.end()) for label in labels)
        ]

        assert offences == [], offences

    def test_the_guard_fails_on_a_message_that_names_a_departed_button(
        self, browser_page, live
    ) -> None:
        """The control for the test above, which is worth nothing if it
        cannot fail: the same predicate over the sentence the rename would
        have left behind."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        labels = browser_page.evaluate(_BAR_LABELS)
        stale = "This grid is a puzzle. Approve to store it, or Dismiss to go on editing."

        found = [
            match for match in self._NAMES_A_CONTROL.finditer(stale)
            if not any(stale.startswith(label, match.end()) for label in labels)
        ]

        assert len(found) == 1, found
        assert stale[found[0].end():].startswith("Dismiss")

    def test_the_grade_names_both_buttons_it_offers(self, browser_page, live) -> None:
        """The positive half: the sentence that comes with the Approve pair
        names that pair, by the labels the pair is wearing. Rename either
        button and leave the sentence, and this fails — which is the half a
        "no dangling name" guard cannot do on its own.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)

        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "Difficulty")

        offered = browser_page.evaluate(_DECIDE_LABELS)
        assert len(offered) == 2, offered
        for label in offered:
            assert label in said, (label, said)

    def test_the_button_the_grade_names_is_the_one_that_goes_back(
        self, browser_page, live
    ) -> None:
        """AC-3's rename, proved by USE rather than by reading a label.

        The name is taken out of the message and pressed. A ``gradeText``
        still ending "or Cancel to go on editing" would press the EXIT: the
        board would be gone and the browser would be on the list, which is
        what the two assertions after the press rule out.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Save").click()
        said = _wait_for_message(browser_page, "Difficulty")

        labels = browser_page.evaluate(_BAR_LABELS)
        named = [label for label in labels if f"or {label} to go on editing" in said]
        assert len(named) == 1, (named, said, labels)
        _button(browser_page, named[0]).click()
        _wait_for_message(browser_page, "Not saved")

        assert browser_page.url.endswith("/editor")
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)
        assert not _approve_offered(browser_page)
        _assert_stored(live, puzzle_id, STORED)


#: Every message ``static/puzzle_edit.js`` can produce, from the module
#: itself. The parts of a sentence (CARD-250's coloured tier word) are
#: flattened the way ``tell`` flattens them into the line, so what is checked
#: is the sentence the owner reads.
_MESSAGE_CORPUS = """async ([refusals, grades, cells, books]) => {
  const module = await import('/static/puzzle_edit.js');
  const flat = (text) => (Array.isArray(text) ? text : [text])
    .map((part) => (typeof part === 'string' ? part : String(part.tier))).join('');
  const said = [module.BACK_TO_EDIT, module.BOARD_MOVED,
                flat(module.inFlightText('verify')), flat(module.inFlightText('approve')),
                flat(module.storedText(null)), flat(module.storedAndStayingText(null))];
  for (const grade of grades) {
    said.push(flat(module.gradeText(grade)));
    said.push(flat(module.storedText(grade)));
    // The store's other tail, the one the page says when it stays (F-001).
    said.push(flat(module.storedAndStayingText(grade)));
  }
  for (const undecided of cells) said.push(flat(module.undecidedText(undecided)));
  // CARD-251's own sentences: the grade's book clause in each of its three
  // shapes (no change, a split page, a book that could not be measured), the
  // question, and the answer to "no".
  said.push(module.BOOK_KEPT);
  for (const book of books) {
    said.push(flat(module.needsConfirmationText(book)));
    for (const grade of grades) said.push(flat(module.gradeText(grade, book)));
  }
  for (const [code, message, reason, storing] of refusals) {
    said.push(flat(module.refusalText(code, message, reason, { storing })));
  }
  return said;
}"""


@pytest.mark.browser
class TestPuzzleEditor_ApproveCommitsThenReturnsToTheList:
    """CARD-250 AC-5. An approved edit is stored AND the owner is put back on
    the list, where the row's picture is the grid that was just stored.

    The store's answer is still told before the exit — it is the only report
    of what the store did, and the page never trades it for the navigation
    (``test_a_second_approve_pressed_in_flight_is_not_sent_either`` reads that
    sentence, holding the page with a 204).

    **The exit's one exception, and what AC-5 therefore means** (review cycle
    1, F-001; the orchestrator's decision is recorded on the card). AC-5's
    "and the browser is on ``/puzzles``" is the settled case: the owner
    approved and let the store answer. A stroke that lands while the store is
    writing is unstored work that exists only on this board, so the page
    keeps it and says so instead of leaving — AC-2's own rule ("only when
    there is nothing to lose") applied to the exit AC-5 adds.
    ``test_a_stroke_made_while_the_store_was_writing_keeps_the_page`` is that
    branch; the two tests below are AC-5's own.
    """

    def test_the_store_holds_the_new_grid_and_the_browser_is_on_the_list(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live, name="Owl")
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, _asked = _watch(browser_page)

        _button(browser_page, "Approve").click()
        _wait_for_the_list(browser_page)

        assert browser_page.url.endswith("/puzzles")
        assert _stored_grid(live, puzzle_id) == EDITED
        assert errors == [], errors

    def test_the_row_it_lands_on_draws_the_grid_that_was_stored(
        self, browser_page, live
    ) -> None:
        """AC-6 in the browser, as far as a browser test honestly reaches:
        the url the row hands the browser carries this edit's stamp — so the
        cache of the replaced picture cannot answer it — and the picture it
        asks for really loads. That the two pictures DIFFER, and that the url
        moved with them, is ``TestPuzzleEditor_TheListShowsTheEditedPicture``.

        **Both pictures of this puzzle, not just the row's** (review cycle 3,
        F-003). Item 2 versioned two urls: the list row and the detail
        modal's large thumbnail. The modal's was read by nothing — every
        other AC-6 test goes through ``_thumbnail_of``, which matches the
        first row ``<img>`` on the page — so deleting its ``?v=`` failed no
        test while leaving the modal as the one place the replaced grid could
        survive in a cache. It is only reachable here: the modal is built by
        a template literal in ``_puzzle_table.html``'s own script from
        ``/api/puzzle/<id>/details``, so no Flask-client test can read the
        url it produces.
        """
        puzzle_id = _seed_live(live, name="Owl")
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        _button(browser_page, "Approve").click()
        _wait_for_the_list(browser_page)

        thumbnail = browser_page.locator(f'a.thumb[onclick*="{puzzle_id}"] img').first
        stamp = live.app.puzzle_review_service.get_puzzle(puzzle_id)["manually_edited_at"]
        assert stamp is not None
        assert quote(str(stamp), safe="") in thumbnail.get_attribute("src")
        # And it is a picture, not a broken image: the versioned url is one
        # the panel really serves.
        assert thumbnail.evaluate("(img) => img.complete && img.naturalWidth > 0")

        # The detail modal's own copy of that picture, in the same shape: the
        # stamp has to move with the edit there too, or the card that opens
        # over this row is where the grid the owner replaced is still shown.
        browser_page.evaluate("([id]) => openPuzzleDetail(id)", arg=[puzzle_id])
        card_picture = browser_page.locator("#puzzleDetailContent .thumb-lg img")
        card_picture.wait_for()
        assert quote(str(stamp), safe="") in card_picture.get_attribute("src"), (
            card_picture.get_attribute("src"))
        assert card_picture.evaluate("(img) => img.complete && img.naturalWidth > 0")

    def test_a_stroke_made_while_the_store_was_writing_keeps_the_page(
        self, browser_page, live
    ) -> None:
        """F-001: the exit is not taken when taking it would destroy work.

        Approve and paint in ONE task, so the stroke lands while the store's
        write is unanswered and there is no timing to get wrong. The stroke
        is unstored work that lives only on this document — the editor keeps
        nothing of its own in localStorage — so the store's answer is told
        and the page STAYS, and the sentence the owner reads is the one that
        is true of staying rather than the one promising a list the browser
        is not going to.

        What this is NOT: a confirmation. The store has just spoken and its
        answer is the only report of what it did, so a question in front of
        it would bury it (the card's ``[Decision] F-001``).
        """
        puzzle_id = _seed_live(live, name="Owl")
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, asked = _watch(browser_page)

        browser_page.evaluate(_APPROVE_THEN_PAINT, [PAINTED_WHILE_STORING])
        browser_page.wait_for_function(_STORED_OR_LEFT, timeout=20_000)

        # It did not leave: the list was never even asked for. (That read
        # first, because it is the deterministic one — a url read can be
        # taken before a navigation this page did start has committed.)
        assert _asked_for_the_list(asked) == [], asked
        assert browser_page.url.endswith("/editor")
        # The stroke is still on the board, which is the whole point.
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(PAINTED_WHILE_STORING)
        # And the store still did exactly what it was told, with the grid
        # that was graded — the board is never re-read (invariant 4).
        assert _posted(asked, "/edit") == [EDITED], asked
        assert _stored_grid(live, puzzle_id) == EDITED
        # The sentence is the staying one: it reports the store AND says the
        # strokes made since are still here and unstored.
        said = _message(browser_page)
        assert "the grid you verified is the stored puzzle now" in said
        assert "the editor stays open" in said
        assert "are not stored" in said
        assert "Showing the puzzle list" not in said, said
        assert errors == [], errors
        # The bar is still here, so focus is still a question this page has to
        # answer -- and "Press Save" is only an instruction if Save is what
        # the owner is standing on. ``tell("Storing this grid...")`` hid the
        # Approve's own ancestor, so without the handler's ``save.focus()``
        # this reads ``''``: focus had been dropped to the document, which is
        # the one thing G-3 / CARD-211 exists to prevent (review cycle 2,
        # F-001). Delete that line of the script and this fails.
        assert browser_page.evaluate("() => document.activeElement.id") == "puzzle-editor-save"

    def test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit(
        self, browser_page, live
    ) -> None:
        """F-002: the exit predicate means "the board moved", and only that.

        ``turn`` carries three jobs -- the staleness token for a verify
        answer, the request counter, and (since fix cycle 1) the predicate for
        whether a successful Approve LEAVES. Three of the four sites that
        advance it cannot disagree with that reading; ``onBackToEdit`` was the
        fourth, and unguarded. Forced during the store's write it spent the
        turn, which suppressed the exit AND put a sentence on the bar stating
        a fact about the board that nothing had told the page -- on a page
        whose whole discipline is to never say what it was not told.

        An owner cannot reach this press (the pair is ``hidden``, which is
        ``display: none`` here), but safety resting on another element's
        visibility is not safety -- the file refuses that argument on this
        very line, and ``_SAVE_THEN_BACK`` already forces the same press for
        the verify case. So the guard is narrow, ``inFlight === "approve"``
        and not ``inFlight !== null``: the verify-case turn spend G-008 added
        is deliberate and
        ``test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer``
        still pins it.

        What this asserts is the guard's whole effect: the board did NOT move,
        so the store's success still leaves for the list, exactly as it does
        with no press at all. Remove the guard and the page stays instead.
        """
        puzzle_id = _seed_live(live, name="Owl")
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        errors, asked = _watch(browser_page)

        state = browser_page.evaluate(_APPROVE_THEN_BACK)
        # THE SILENCE, read in the press's own task (AC/EC/G gate, 2026-10-19).
        # The amended AC-7 says this press is "ignored in silence" and names
        # THIS test as carrying that clause -- and it did not: with the guard
        # changed to `tell(BACK_TO_EDIT); return;` the whole suite still
        # passed, so the page could have announced "your edit is still there"
        # over a live store write, which is the alternative AC-7's own
        # justification records as REJECTED for brushing THE INVARIANT.
        # Ignored means ignored: the sentence on the bar is still the store's.
        assert "Storing this grid" in state["said"], state
        assert "your edit is still there" not in state["said"], state
        _wait_for_the_list(browser_page)

        assert _posted(asked, "/edit") == [EDITED], asked
        assert _stored_grid(live, puzzle_id) == EDITED
        assert errors == [], errors


@pytest.mark.browser
class TestPuzzleEditor_NoExitWhileTheStoreIsDeciding:
    """CARD-250 AC-7. An exit may not outrun the store.

    Leaving the page is a new way for a request to be in flight with nobody
    left to hear its answer, and a save's answer is the only report of what
    the store actually did — so Cancel is refused while a request is
    unanswered, in words and with ``aria-disabled`` (never ``disabled``:
    CARD-211), exactly as a second Save is refused.

    **The asymmetry, and why it is not a gap.** Back to edit is not an exit
    from the page, so it has nothing to outrun — but it is not refused by
    nothing either. AC-7 (amended per button, review cycle 3) asks a
    different thing of it in each in-flight window, and the two are pinned
    separately:

    * During a **verify** it spends the turn and says the edit is still
      there — CARD-246's behaviour, unchanged, and this is now the only
      window in which that behaviour exists. Pinned by
      ``test_a_back_to_edit_taken_mid_flight_is_not_undone_by_the_answer``
      (CARD-250 G-1: renamed, not changed) and by
      ``test_back_to_edit_pressed_mid_flight_does_not_navigate_either``
      below.
    * During an **approve** it is **ignored in silence**, so the exit
      predicate keeps one meaning. Pinned by
      ``test_a_back_to_edit_forced_while_the_store_writes_does_not_stop_the_exit``
      (review cycle 2, F-002). Silence rather than a sentence because the
      button carries no ``aria-disabled`` and sits in a ``display: none``
      container for the whole write — an attribute there reaches nobody —
      and because a press that cannot stop the store does not get to speak
      over the store's answer.

    Neither window is owner-reachable: the pair is ``hidden``, so only a
    script presses the button there.

    Each press below is made in the SAME TASK as the request it races, and
    the bar is read there: a fetch cannot resolve inside the task that
    started it, so what these read is the state the press itself produced.
    """

    def _graded(self, page, live):
        puzzle_id = _seed_live(live)
        _open_editor(page, live, puzzle_id)
        _paint_a_cell(page)
        _button(page, "Save").click()
        _wait_for_message(page, "Difficulty")
        return puzzle_id

    def test_cancel_pressed_while_the_store_is_deciding_does_not_leave(
        self, browser_page, live
    ) -> None:
        puzzle_id = self._graded(browser_page, live)
        errors, asked = _watch(browser_page)

        with browser_page.expect_response(lambda r: r.url.endswith("/edit")) as answer:
            state = browser_page.evaluate(_APPROVE_THEN_LEAVE)

        assert answer.value.status == 200
        assert state["path"].endswith("/editor")
        assert state["busy"] == "true"
        assert state["confirming"] is False
        assert "Still storing" in state["said"], state["said"]
        # And only that one: the pair is one ternary, so a function that
        # answered with both sentences at once would pass the line above
        # while telling the owner two store states in one breath
        # (review cycle 3, F-002 — the mirror cycle 2's F-004 added for
        # the stored pair, measured there as MU-J).
        assert "Still checking" not in state["said"], state["said"]
        assert _asked_for_the_list(asked) == [], asked
        # The refusal cost the owner nothing: the store's word is still heard,
        # and the exit happens on its own once it has been.
        _wait_for_the_list(browser_page)
        assert _stored_grid(live, puzzle_id) == EDITED
        assert errors == [], errors

    def test_cancel_pressed_while_the_grid_is_being_checked_does_not_leave_either(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, asked = _watch(browser_page)

        with browser_page.expect_response(lambda r: r.url.endswith("/edit/verify")) as answer:
            state = browser_page.evaluate(_SAVE_THEN_LEAVE)

        assert answer.value.status == 200
        assert state["path"].endswith("/editor")
        assert state["busy"] == "true"
        assert "Still checking" in state["said"], state["said"]
        # The other half of the same mirror (review cycle 3, F-002).
        assert "Still storing" not in state["said"], state["said"]
        assert _asked_for_the_list(asked) == [], asked
        # And the flow is not stuck: the grade lands and the page is usable.
        _wait_for_message(browser_page, "Difficulty")
        assert _approve_offered(browser_page)
        assert _button(browser_page, "Cancel").get_attribute("aria-disabled") == "false"
        _assert_stored(live, puzzle_id, STORED)
        assert errors == [], errors

    def test_leave_editor_pressed_after_the_question_was_asked_is_refused_too(
        self, browser_page, live
    ) -> None:
        """The confirmation may be open when a request starts, so the refusal
        is re-read at the moment of LEAVING and not only at the moment of
        asking — safety that rested on when the dialog was opened would be
        safety resting on a race.
        """
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        _button(browser_page, "Cancel").click()
        assert _confirm_open(browser_page)
        errors, asked = _watch(browser_page)

        with browser_page.expect_response(lambda r: r.url.endswith("/edit/verify")) as answer:
            state = browser_page.evaluate(_SAVE_THEN_LEAVE_ANYWAY)

        assert answer.value.status == 200
        assert state["path"].endswith("/editor")
        assert state["confirming"] is False  # the question is answered, not left open
        assert "Still checking" in state["said"], state["said"]
        # The mirror again, on the branch reached with the question open.
        assert "Still storing" not in state["said"], state["said"]
        assert _asked_for_the_list(asked) == [], asked
        _assert_stored(live, puzzle_id, STORED)
        assert errors == [], errors

    def test_back_to_edit_pressed_mid_flight_does_not_navigate_either(
        self, browser_page, live
    ) -> None:
        """AC-7's other half. Back to edit cannot leave the page at all, so
        the page does not navigate; and it says what it did, which is that
        nothing was saved and the edit is still there."""
        puzzle_id = _seed_live(live)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, asked = _watch(browser_page)

        with browser_page.expect_response(lambda r: r.url.endswith("/edit/verify")) as answer:
            state = browser_page.evaluate(_SAVE_THEN_BACK_WITH_STATE)

        assert answer.value.status == 200
        assert state["path"].endswith("/editor")
        assert "your edit is still there" in state["said"], state["said"]
        assert _asked_for_the_list(asked) == [], asked
        _settle(browser_page)
        assert browser_page.url.endswith("/editor")
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)
        _assert_stored(live, puzzle_id, STORED)
        assert errors == [], errors


@pytest.mark.browser
class TestPuzzleEditor_TheGradeWearsItsTierColour:
    """CARD-250 AC-8. The recomputed tier's word carries that tier's colour,
    and it is the SAME computed colour the list's chip uses for that tier —
    read off both pages inside one test, which is the only form in which
    "the same colour" is a claim and not a hope.

    The tier reaches the DOM as the server's own string on a data attribute;
    the hue is ``admin.css``'s, from ``--color-tier-*``. There is no
    tier-to-colour map in JavaScript and no literal anywhere but
    ``tokens.css``/``_tier.html`` — the other half of that is AC-9, in
    ``tests/test_admin_design_tokens.py``.
    """

    def test_each_tiers_word_is_that_tiers_colour_and_the_lists_too(
        self, browser_page, live
    ) -> None:
        tiers = ("easy", "medium", "hard")
        edited = _seed_live(live)
        rows = {tier: _seed_live(live, tier=tier, name=f"{tier} row") for tier in tiers}
        _open_editor(browser_page, live, edited)
        # The grade is the SERVER'S, so it is stubbed to walk the three tiers
        # — the page shows what it is told and decides nothing (G-3).
        grade = {"tier": tiers[0], "score": 11}
        browser_page.route(
            "**/edit/verify",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"ok": True, "grade": {
                    "difficulty_tier": grade["tier"],
                    "difficulty_score": grade["score"],
                }}),
            ),
        )
        browser_page.evaluate(_SET_GRID, [EDITED])

        word = {}
        for tier in tiers:
            grade["tier"] = tier
            _button(browser_page, "Save").click()
            _wait_for_message(browser_page, f"Difficulty: {tier}")
            word[tier] = browser_page.evaluate(_TIER_WORD)

        browser_page.goto(f"{live.url}/puzzles")
        badge = browser_page.evaluate(_BADGE_COLOURS, [rows])

        for tier in tiers:
            assert word[tier]["text"] == tier, word[tier]
            assert word[tier]["tier"] == tier, word[tier]
            # It really wears a colour, rather than inheriting the prose's.
            assert word[tier]["colour"] != word[tier]["prose"], word[tier]
            # And it is the list's colour for the same tier.
            assert badge[tier]["text"].lower() == tier, badge[tier]
            assert word[tier]["colour"] == badge[tier]["colour"], (tier, word[tier], badge[tier])
        # Three tiers, three colours: "the same colour" is not satisfied by
        # everything being one colour.
        assert len({word[tier]["colour"] for tier in tiers}) == 3, word

    def test_the_page_still_shows_no_difficulty_of_its_own(self, browser_page, live) -> None:
        """G-6. The coloured word is in the save bar's message and nowhere
        else: no tier badge came back to the header, and the span the colour
        lives on is empty until a grade has been told."""
        puzzle_id = _seed_live(live, tier="hard")
        _open_editor(browser_page, live, puzzle_id)

        served = browser_page.content()
        assert browser_page.locator("#puzzle-editor-grade").text_content() == ""
        assert browser_page.locator(".player-head .badge").count() == 0
        assert browser_page.locator("#puzzle-editor .badge").count() == 0
        assert "player-tier" not in served


# --------------------------------------------------------------------------
# CARD-251 — the question in the page, and the sentences that word the book
# --------------------------------------------------------------------------


def _book_question_open(page) -> bool:
    return page.locator("#puzzle-editor-book-question").is_visible()


def _live_book(live, puzzle_id, *, title="Winter Pictures", published=False) -> str:
    """A real ``books`` row holding ``puzzle_id`` through the store's own path.

    ``make_book`` writes the book and ``assign_to_book`` the row's side, which
    is the pair CARD-100 keeps together; the book's own ``puzzle_ids`` list is
    not needed here — the question is about the puzzle's ``book_id`` and the
    book's title.
    """
    from nonogram.db.models import Book
    import uuid as uuid_module

    book_id = make_book(live.scope, title=title)
    if published:
        with live.scope() as db:
            row = db.query(Book).filter(Book.id == uuid_module.UUID(book_id)).first()
            row.status = "published"
    assert live.app.puzzle_review_service.assign_to_book([puzzle_id], book_id) == 1
    return book_id


#: ``needsConfirmationText`` over the book shapes the server can send, read in
#: the page that ships it. Failure matrix F-4's own row lands here, because the
#: question is what F-4 declares behaviour for.
_QUESTION_TEXTS = """async ([books]) => {
  const module = await import('/static/puzzle_edit.js');
  return books.map((book) => module.needsConfirmationText(book));
}"""


@pytest.mark.browser
class TestBookedEdit_TheQuestionNamesTheBook:
    """AC-2 / AC-6 / G-1 / G-7 in the browser: the guard became a question.

    The flow, and every step of it is load-bearing:

    * **Save** grades the grid, and the grade's own sentence already names the
      book — the owner's principle for the tier was "learn it at verify, with
      the grade", and the book is the other thing there is to learn.
    * **Approve** posts the grid WITHOUT the confirmation. That request is the
      one the server refuses, so the question is the server's and not this
      page's: ``needs_confirmation`` comes back, nothing was written, and the
      page turns the answer into its own in-page ``alertdialog``.
    * **Edit it anyway** posts the same grid again WITH ``confirmed: true``.
      Two requests, and the second one is what stores — a dialog that posted
      an identical request would be no implementation of this card.

    The puzzle is seeded **easy**, the tier ``solid_minus_corner`` grades
    into, so the flow reaches the question rather than the regrade refusal
    (which is ``test_a_puzzle_that_entered_a_book_says_this_edit_cannot_be_stored``).
    """

    def test_the_question_names_the_book_and_the_answer_stores(
        self, browser_page, live
    ) -> None:
        puzzle_id = _seed_live(live, tier="easy")
        _live_book(live, puzzle_id, title="Winter Pictures")
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, asked = _watch(browser_page)

        _button(browser_page, "Save").click()
        graded = _wait_for_message(browser_page, "Difficulty")
        assert "Winter Pictures" in graded, graded
        assert _approve_offered(browser_page)

        _button(browser_page, "Approve").click()
        asking = _wait_for_message(browser_page, "Nothing is stored yet")

        # The question: it names the book, and it is in the page.
        assert "Winter Pictures" in asking, asking
        assert _book_question_open(browser_page)
        # No Approve stands beside an open question.
        assert not _approve_offered(browser_page)
        # And the server was asked, without the flag, and wrote nothing.
        unconfirmed = [data for url, data in asked if url.endswith("/edit") and data]
        assert unconfirmed, "the approve never reached the save route"
        assert json.loads(unconfirmed[-1]).get("confirmed") is None
        _assert_stored(live, puzzle_id, STORED)

        _button(browser_page, "Edit it anyway").click()
        _wait_for_the_list(browser_page)

        # The second request carried the flag, and the grid is stored.
        confirmed = [
            json.loads(data) for url, data in asked
            if url.endswith("/edit") and data
        ]
        assert confirmed[-1]["confirmed"] is True, confirmed[-1]
        assert len(confirmed) == 2, confirmed
        _assert_stored(live, puzzle_id, EDITED)
        assert errors == [], errors

    def test_the_question_calls_an_unreadable_books_id_an_id(
        self, browser_page, live
    ) -> None:
        """**Failure matrix F-4's second half** (review cycle 1, F-002). F-4
        declares that the question names the book's ID *and says its title
        could not be read*. Only the first half was built: the owner read
        "This puzzle is in the book 3f2a1b0c-…", a bare uuid standing where a
        title goes, with nothing to tell a missing title from a book literally
        called that.

        The load-bearing half was never in doubt and is driven end to end at
        the route by ``tests/test_puzzle_edit_routes.py``'s
        ``test_a_book_whose_title_cannot_be_read_still_needs_the_flag`` (the
        server sends ``title: null``, refuses the unconfirmed save, and stores
        the confirmed one). This is the sentence that answer reaches the owner
        as.
        """
        puzzle_id = _seed_live(live, tier="easy")
        _open_editor(browser_page, live, puzzle_id)
        gone = "3f2a1b0c-0000-0000-0000-000000000000"

        named, unnamed, published = browser_page.evaluate(_QUESTION_TEXTS, [[
            {"id": gone, "title": "Winter Pictures", "published": False},
            {"id": gone, "title": None, "published": False},
            {"id": gone, "title": None, "published": True},
        ]])

        # A readable title is still named, and the id is not quoted beside it.
        assert "the book Winter Pictures" in named
        assert gone not in named

        assert "title could not be read" in unnamed
        assert f"id {gone}" in unnamed
        assert f"the book {gone}" not in unnamed

        # AC-6's half is untouched by the clause: a published book is still
        # said to be published, with or without a readable title.
        assert "title could not be read" in published
        assert "that book is published" in published

    def test_keeping_the_stored_grid_stores_nothing_and_keeps_the_board(
        self, browser_page, live
    ) -> None:
        """The other answer. Nothing is stored, nothing on the board is lost,
        and the page is still usable — the promise Back to edit makes."""
        puzzle_id = _seed_live(live, tier="easy")
        _live_book(live, puzzle_id)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, _asked = _watch(browser_page)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Nothing is stored yet")

        _button(browser_page, "Keep the stored grid").click()
        said = _wait_for_message(browser_page, "the book keeps the grid it had")

        assert not _book_question_open(browser_page)
        assert "your edit is still there" in said or "still on the board" in said
        assert browser_page.url.endswith("/editor")
        assert browser_page.evaluate(_BOARD_STATES) == _states_of(EDITED)
        _assert_stored(live, puzzle_id, STORED)
        assert errors == [], errors
        # Still usable: a question was abandoned, not the page.
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

    def test_a_stroke_withdraws_the_question(self, browser_page, live) -> None:
        """The question is about ONE grid, so a stroke makes it a question
        about a grid that is not on the board. Clear's confirmation follows
        the same rule; "leave the editor?" deliberately does not, because that
        one is as true after a stroke as before it."""
        puzzle_id = _seed_live(live, tier="easy")
        _live_book(live, puzzle_id)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, _asked = _watch(browser_page)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_message(browser_page, "Nothing is stored yet")
        assert _book_question_open(browser_page)

        _cell(browser_page, 2, 2).click()
        said = _wait_for_message(browser_page, "The board has changed")

        assert not _book_question_open(browser_page)
        assert "nothing was stored" in said.lower()
        assert not _approve_offered(browser_page)
        _assert_stored(live, puzzle_id, STORED)
        assert errors == [], errors

    def test_a_published_books_question_says_it_is_published(
        self, browser_page, live
    ) -> None:
        """AC-6 in the page: the flag is the same one, and the question says
        which case the owner is in — a published book's confirmation is
        INV-008's own, which ``in_a_book()`` cannot tell apart (Trap 1)."""
        puzzle_id = _seed_live(live, tier="easy")
        _live_book(live, puzzle_id, title="Winter Nights", published=True)
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, _asked = _watch(browser_page)
        _button(browser_page, "Save").click()
        _wait_for_message(browser_page, "Difficulty")

        _button(browser_page, "Approve").click()
        asking = _wait_for_message(browser_page, "Nothing is stored yet")

        assert "Winter Nights" in asking
        assert "published" in asking
        assert errors == [], errors

    def test_an_unbooked_puzzle_is_never_asked(self, browser_page, live) -> None:
        """The control the four tests above need: without a book there is no
        question, the grade's sentence says nothing about books, and Approve
        stores on the first press."""
        puzzle_id = _seed_live(live, tier="easy")
        _open_editor(browser_page, live, puzzle_id)
        _paint_a_cell(browser_page)
        errors, asked = _watch(browser_page)

        _button(browser_page, "Save").click()
        graded = _wait_for_message(browser_page, "Difficulty")
        _button(browser_page, "Approve").click()
        _wait_for_the_list(browser_page)

        assert "book" not in graded.lower(), graded
        posted = [data for url, data in asked if url.endswith("/edit") and data]
        assert len(posted) == 1, posted
        assert json.loads(posted[0]).get("confirmed") is None
        _assert_stored(live, puzzle_id, EDITED)
        assert errors == [], errors


#: ``bookNote`` over the four shapes its argument can take, read in the page
#: that ships it. AC-9's own words are here because the facts behind them are
#: asserted at the route (``tests/test_puzzle_edit_routes.py``
#: ``TestBookedEdit_ASplitPairIsAnnouncedBeforeApprove``) and the sentence is
#: the client's half of the same criterion.
_BOOK_NOTES = """async ([books]) => {
  const module = await import('/static/puzzle_edit.js');
  return books.map((book) => module.bookNote(book));
}"""


@pytest.mark.browser
class TestBookedEdit_TheSplitPairIsWordedAsAWarning:
    """AC-9's words, and G-3: a warning, never a refusal.

    The verify's answer carries the page-count effect as facts; this is the
    sentence the page makes of them. The route's own test asserts the facts
    and that an approved edit stores; this asserts that what the owner READS
    says the book would gain a page and names the puzzle whose page it shares.
    """

    _PAGES = [
        {"id": "b", "title": "Winter Pictures", "published": False,
         "pages": {"known": True, "changes": True, "added": 1,
                   "partner": "snowflake.png"}},
        {"id": "b", "title": "Winter Pictures", "published": False,
         "pages": {"known": True, "changes": False, "added": 0,
                   "partner": "snowflake.png"}},
        {"id": "3f2a1b0c-0000-0000-0000-000000000000", "title": None,
         "published": False,
         "pages": {"known": False, "changes": None, "added": None,
                   "partner": None}},
        # Review cycle 1, F-004: the delta is signed and is not constrained
        # to one, so the two wordings nothing pinned are pinned here. Both are
        # reachable and both are measured at the route — a shallower
        # replacement letting a pair fit that does not fit today is
        # `test_a_replacement_that_lets_a_pair_fit_makes_the_book_shorter`.
        {"id": "b", "title": "Winter Pictures", "published": False,
         "pages": {"known": True, "changes": True, "added": -1,
                   "partner": None}},
        {"id": "b", "title": "Winter Pictures", "published": False,
         "pages": {"known": True, "changes": True, "added": 2,
                   "partner": "snowflake.png"}},
    ]

    def test_the_five_shapes_say_five_different_things(
        self, browser_page, live
    ) -> None:
        """Renamed from ``test_the_three_shapes_say_three_different_things``
        (review cycle 1, F-001/F-004): the three it covered are the first
        three assertions below, unchanged in substance, and two more shapes
        joined them."""
        puzzle_id = _seed_live(live, tier="easy")
        _open_editor(browser_page, live, puzzle_id)

        split, kept, unknown, shorter, two = browser_page.evaluate(
            _BOOK_NOTES, [self._PAGES]
        )

        # The split page: how much longer, the partner, and that the book
        # stays valid.
        assert "Winter Pictures" in split
        assert "snowflake.png" in split
        assert "one page longer" in split
        # And NO absolute page count (review cycle 1, F-001): the two walks
        # measure a delta, and the figure this page used to quote was the
        # book's PUZZLE pages under the name of its page count.
        assert not re.search(r"\d+", split.replace("snowflake.png", "")), split
        # And it is a warning: nothing in it says the edit cannot be stored.
        assert "cannot" not in split.lower()
        assert "refused" not in split.lower()

        # The pair that survives: the book is named, and no page count is
        # claimed to move.
        assert "Winter Pictures" in kept
        assert "page count" not in kept
        assert "longer" not in kept and "shorter" not in kept

        # Unmeasurable: it says so rather than claiming either way — and the
        # book whose title could not be read is named by its id and SAID to
        # be (review cycle 1, F-002; failure matrix F-4).
        assert "could not be measured" in unknown
        assert "page count" in unknown
        assert "title could not be read" in unknown
        assert "id 3f2a1b0c-0000-0000-0000-000000000000" in unknown

        # The other direction, and a magnitude above one: the words follow
        # the number instead of being written beside it.
        assert "one page shorter" in shorter
        assert "longer" not in shorter
        assert "2 pages longer" in two

    def test_a_book_with_no_note_adds_nothing_to_the_grade(
        self, browser_page, live
    ) -> None:
        """The control: ``bookNote`` of nothing is the empty string, which is
        why an unbooked puzzle's grade sentence is CARD-246's unchanged."""
        puzzle_id = _seed_live(live, tier="easy")
        _open_editor(browser_page, live, puzzle_id)

        notes = browser_page.evaluate(_BOOK_NOTES, [[None]])

        assert notes == [""]


# ==========================================================================
# CARD-271 (review cycle 1, F-008) — the editor's board keeps its clues by
# the same rule the player's does
#
# The card's Design context asks for a confirmation that the editor does not
# regress, and the implementation round did not produce one: the editor reuses
# ``.player-stage`` (puzzle_edit.html, the ``#puzzle-player`` div) and the same
# ``static/solver.js``, so ``drawBoard`` marks its gutters ``is-stuck-*`` and
# ``keepCluesInView`` runs on the editor board too — and no editor test read a
# gutter box.
#
# One honest check rather than a suite: the room condition is the whole
# mechanism, and what has to be true of the editor is that it obeys the same
# one — on load, and after a viewport change, which the editor can reach
# because its toolbar DOES ship the zoom control
# (``[data-player-zoom-action]`` in puzzle_edit.html, beside the brush). That
# last clause is measured here rather than taken from review cycle 1, which
# bounded F-008's risk on the grounds that the editor ships no zoom.
#
# The two halves run on two different boards, and that is the correction PG-3
# forced rather than a convenience: the room condition applies to every board,
# but F-001's defect was in the branch a board small on BOTH sides takes, so a
# 30 x 30 cannot exercise it. The marker census and the load-time equality
# stay on the 30 x 30 (the reported case); the resize goes to a 15 x 15.
# ==========================================================================


@pytest.mark.browser
class TestPuzzleEditor_TheBoardKeepsItsCluesByTheSameRule:

    #: The same board as the player's own case: a 30 x 30 drawn plain at
    #: 1280 x 720, cells under CARD-212's doubling bar.
    GRID = _unique_grid(30, 30, seed=27130)
    WIDE = {"width": 1280, "height": 720}

    #: And, for F-001's path only, a board small on BOTH sides — the branch
    #: the defect was in. Measured on this host, Chromium, on the EDITOR page:
    #: at 1920 x 1500 and 200 % it does not overflow, so both axes keep; at
    #: 1024 x 768 the same board has a 359.4 px row band and a 307.3 px column
    #: band over a 724 x 540 scrollport and overflows past both, so neither
    #: axis may. Every assertion re-derives that from the page's own numbers.
    SMALL = _unique_grid(15, 15, seed=27115)
    ZOOMED_WIDE = {"width": 1920, "height": 1500}
    ZOOMED_NARROW = {"width": 1024, "height": 768}
    ZOOM = 200

    def test_the_editors_gutters_obey_the_room_condition(
        self, browser_page, live
    ) -> None:
        page = browser_page
        page.set_viewport_size(self.WIDE)
        _open_editor(page, live, _seed_live(live, self.GRID))

        # The mechanism is present on this page at all: the editor's stage is
        # the scroll container, and solver.js marked the kept gutter of each
        # axis — one box per line of that axis, which on this plain board is
        # the whole band and no duplicate.
        marked = page.evaluate(
            """() => {
              const stage = document.querySelector('.player-stage');
              const table = document.querySelector('.player-board');
              return {
                stageId: stage.id,
                overflowY: getComputedStyle(stage).overflowY,
                rows: table.querySelectorAll('th.player-clue.is-row.is-stuck-row').length,
                cols: table.querySelectorAll('th.player-clue.is-col.is-stuck-col').length,
              };
            }"""
        )
        side = len(self.GRID)
        assert marked == {"stageId": "puzzle-player", "overflowY": "auto",
                          "rows": side, "cols": side}, marked

        # And it obeys the same rule, re-derived from the editor page's own
        # measurements and solver.js's constant — not compared against the
        # player's numbers, which would only say the two pages agree.
        at_load = _room(page)
        assert at_load["keeping"] == _verdict(at_load), at_load

    def test_a_resize_after_a_zoom_re_measures_the_editors_room(
        self, browser_page, live
    ) -> None:
        """F-001's own path, on the editor, on the board it can reach it with.

        This clause used to run on the 30 x 30 above and could not fail
        (CARD-271 fix round 1 pre-gate, PG-3): ``isBig`` is
        ``width > BIG_SIDE || height > BIG_SIDE`` with ``BIG_SIDE`` 15, so a
        30 x 30 is big on both sides and its resize always reached
        ``redraw()`` — the one branch F-001 never touched. Measured: the whole
        class, run with solver.js at the pre-fix revision, was 2 passed. A
        claim whose control cannot fail is exactly what F-002 was raised about,
        so it is replaced here rather than reworded.

        The board is small on BOTH sides, so its resize reaches the branch the
        defect was in, and it is zoomed until it scrolls, between two viewports
        measured to decide differently — 1920 x 1500 affords both axes (a
        15 x 15 at 200 % does not overflow there, and a band that covers
        nothing is free), 1024 x 768 affords neither (359.4 px and 307.3 px of
        band over a 724 x 540 scrollport). The same viewport and zoom reached
        by LOADING is the control: the rule is right everywhere it is reached,
        and it was the reaching that was missing.
        """
        page = browser_page
        puzzle = _seed_live(live, self.SMALL)

        page.set_viewport_size(self.ZOOMED_WIDE)
        _open_editor(page, live, puzzle)
        _zoom(page, self.ZOOM)
        at_load = _room(page)
        page.set_viewport_size(self.ZOOMED_NARROW)
        _settled(page)
        resized = _room(page)

        page.set_viewport_size(self.ZOOMED_NARROW)
        _open_editor(page, live, puzzle)
        _zoom(page, self.ZOOM)
        loaded = _room(page)

        report = {"at_load": at_load, "resized": resized, "loaded": loaded}
        # One board at one viewport, read twice: if the inputs differed the two
        # readings would not be comparable.
        assert resized["port"] == loaded["port"], report
        assert resized["band"] == loaded["band"], report
        assert resized["overflow"] == loaded["overflow"], report
        # Not vacuous: the viewport really does change the answer here, so a
        # page that never re-measured is caught rather than merely unexercised.
        assert at_load["keeping"] != _verdict(loaded), report
        # The rule where it is reached...
        assert loaded["keeping"] == _verdict(loaded), report
        # ...and where only a resize can reach it.
        assert resized["keeping"] == _verdict(resized), report
        assert resized["keeping"] == loaded["keeping"], report

    def test_the_editor_ships_the_zoom_control(self, browser_page, live) -> None:
        """The measurement behind the sentence above, because review cycle 1
        bounded F-008's risk on the opposite reading of this page: the editor
        DOES ship the zoom buttons, so every path that re-measures on the
        player — zoom, and a resize after one — exists here as well."""
        page = browser_page
        page.set_viewport_size(self.WIDE)
        _open_editor(page, live, _seed_live(live, self.GRID))

        assert page.locator('[data-player-zoom-action="in"]').count() == 1
        assert page.locator('[data-player-zoom-action="out"]').count() == 1
        assert page.locator("[data-player-zoom-readout]").text_content() == "100%"
