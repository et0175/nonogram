"""CARD-121 — the 4.8 mm floor at the book store (FR-031, NFR-008, INV-006).

    AC-183  a 4.61 mm puzzle submitted from the selection step with no
            override is not added, and the response names 4.61 mm against
            the 4.8 mm floor
    AC-184  the same puzzle, submitted with an override for its id, becomes a
            member and the override is stored for that id
    AC-185  the same puzzle pasted into the detail page's add-puzzles form is
            not added either — the floor holds on that route too
    AC-186  a 4.84 mm puzzle is added with no flag: at or above the floor

and the postures the invariant needs to be worth anything — what happens to a
puzzle whose cell cannot be computed, to a book whose trim cannot be read, to
an id no row matches, and to a manager wired without a store.

The evidence class is the Flask test client. AC-183..185 are user-facing
criteria on a server-rendered screen and this project has no browser harness,
so each drives the real POST route with real form fields and reads the real
HTML that came back — the same reading CARD-122's tests make.

The expected cell figures (4.61 mm, 4.84 mm) are the *card's*, stated in
FR-031's acceptance criteria, and the grids here are built by hand to hit
them. They are not re-derived from ``book_cell_mm``: that would only prove the
code agrees with itself. What must come from ``book_cell_mm`` is the cell the
product uses (G-1, EC-021), and
:class:`TestBookFloor_TheCellIsTheOneComputation` holds it to exactly that.
"""

from __future__ import annotations

import ast
import html as html_module
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_page_spec import FLOOR_MM, book_cell_mm, book_page_spec
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.db import sqlite_session_scope

#: The two fixtures FR-031 names, as (width, height, row-clue gutter depth,
#: column-clue gutter depth, the cell the card says they get on the Book 1
#: profile). AC-182/183/184/185 are all about the first; AC-186 is the second.
BELOW_FLOOR = (30, 25, 12, 8, 4.61)
ABOVE_FLOOR = (30, 20, 10, 8, 4.84)


# --------------------------------------------------------------------------
# hand-built puzzles that land on the cells the ACs name
# --------------------------------------------------------------------------


def dotted_grid(width: int, height: int, row_gutter: int, column_gutter: int):
    """A lattice of isolated cells: ``row_gutter`` deep rows, ``column_gutter`` deep columns.

    Cell ``(r, c)`` is filled when both indices are even and inside the
    ``column_gutter`` x ``row_gutter`` block at the top left, so every filled
    row holds ``row_gutter`` runs of one and every filled column
    ``column_gutter`` — which is exactly the clue-gutter depth the layout
    reserves, and therefore the number of cells across the sheet must fit.

    The grid is uniquely solvable, which the store insists on (ADR-0032/R1),
    and trivially so: every odd line and every line past the block is empty,
    which pins each filled line's runs to the even positions that are left.
    """
    assert 2 * row_gutter - 1 <= width and 2 * column_gutter - 1 <= height
    return [
        [
            r % 2 == 0 and r < 2 * column_gutter and c % 2 == 0 and c < 2 * row_gutter
            for c in range(width)
        ]
        for r in range(height)
    ]


def runs(line) -> list[int]:
    """The run-length encoding of one line, spelled out here on purpose.

    An independent second implementation rather than an import of
    ``nonogram.clues``: these fixtures must stand on their own, so that a
    change to the encoder cannot quietly move the puzzles this file measures.
    A line with no filled cell encodes to ``[0]``, as the project's boundary
    type requires.
    """
    encoded, run = [], 0
    for cell in line:
        if cell:
            run += 1
        elif run:
            encoded.append(run)
            run = 0
    if run:
        encoded.append(run)
    return encoded or [0]


def clues_of(grid):
    """``(clues_rows, clues_cols)`` for ``grid``, as the store keeps them."""
    return (
        [runs(row) for row in grid],
        [runs([row[c] for row in grid]) for c in range(len(grid[0]))],
    )


# --------------------------------------------------------------------------
# the shelf: a store, a book manager, and one storage mode
# --------------------------------------------------------------------------


class Shelf:
    """A book manager and the store behind it, in one storage mode.

    Item 2 of the card is "both storage modes", and the floor is a rule of the
    aggregate rather than of a backend, so every store-level assertion below
    runs against each.
    """

    def __init__(self, mode, tmp_path):
        self.mode = mode
        self.factory = None if mode == "memory" else sqlite_session_scope(tmp_path, "floor.db")
        self.store = PuzzleReviewService(session_factory=self.factory)
        self.books = BookManager(session_factory=self.factory, puzzle_store=self.store)

    def puzzle(self, width, height, row_gutter, column_gutter, *, tier="easy") -> str:
        grid = dotted_grid(width, height, row_gutter, column_gutter)
        clues_rows, clues_cols = clues_of(grid)
        puzzle_id = self.store.add_puzzle(
            grid=grid,
            clues_rows=clues_rows,
            clues_cols=clues_cols,
            width=width,
            height=height,
            theme="generic",
            difficulty_score=10,
            difficulty_tier=tier,
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            batch_id=None,
            source_image=f"{width}x{height}-{row_gutter}x{column_gutter}.png",
        )
        self.store.approve_puzzle(puzzle_id)
        return puzzle_id

    def book(self, title="Winter") -> str:
        return self.books.create_book(title, "a book", "christmas", "adults")


@pytest.fixture(params=["memory", "db"])
def shelf(request, tmp_path):
    return Shelf(request.param, tmp_path)


# --------------------------------------------------------------------------
# the panel: the real routes, driven through the test client
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    """The panel in in-memory mode, with a book manager of its own."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    book_manager_module._book_manager = BookManager(session_factory=None)
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    # Both module singletons emptied again, so the books and pictures made
    # here cannot be inherited by the next test's panel. Leaving the book
    # manager behind was enough to make an unrelated delete test fail: its
    # fresh in-memory store reuses the id `puzzle_000001`, which one of these
    # books still claimed, and the delete route refuses a puzzle in a book.
    # (A *fresh* manager, not None: `get_book_manager` wires the singleton's
    # store on first use and never rebuilds it.)
    image_manager_module._image_manager = None
    book_manager_module._book_manager = BookManager(session_factory=None)


class Panel:
    """The app, its store and its books, plus the two add routes as one-liners."""

    def __init__(self, app):
        self.app = app
        self.store = app.puzzle_review_service
        self.books = app.book_manager
        self.client = app.test_client()
        self._shelf = SimpleNamespace(store=self.store)

    puzzle = Shelf.puzzle
    book = Shelf.book

    def select(self, book_id, puzzle_ids, overrides=()):
        """POST the selection step, as the step's own form submits it (AC-183/184).

        ``shown_ids`` is every tile the page offered and ``puzzle_ids`` the
        ticked ones, which is what ``_fold_tab_into_selection`` reads; an
        override travels as ``override_<puzzle_id>``, the field CARD-121 fixed
        and CARD-123's tile will render.
        """
        form = {
            "bucket": "26-30",
            "shown_ids": list(puzzle_ids),
            "puzzle_ids": list(puzzle_ids),
        }
        for puzzle_id in overrides:
            form[f"override_{puzzle_id}"] = "on"
        return self.client.post(
            f"/book/{book_id}/select-puzzles", data=form, follow_redirects=True
        )

    def paste(self, book_id, puzzle_ids, **extra):
        """POST the detail page's paste-IDs form (AC-185)."""
        return self.client.post(
            f"/book/{book_id}/add-puzzles",
            data={"puzzle_ids": ",".join(puzzle_ids), **extra},
            follow_redirects=True,
        )

    def ids_of(self, book_id):
        return list(self.books.get_book(book_id).puzzle_ids)


@pytest.fixture
def panel(admin_app):
    return Panel(admin_app)


def text_of(html: str) -> str:
    """The rendered page as readable text: no tags, no entities, one space."""
    without_scripts = re.sub(r"(?s)<script.*?</script>", " ", html)
    return re.sub(
        r"\s+", " ", html_module.unescape(re.sub(r"<[^>]+>", " ", without_scripts))
    ).strip()


def body(response) -> str:
    assert response.status_code == 200
    return text_of(response.get_data(as_text=True))


# --------------------------------------------------------------------------
# AC-183 — refused from the selection step, with both figures named
# --------------------------------------------------------------------------


class TestBookAddPuzzles_RefusesBelowFloorWithoutOverride:
    """A 4.61 mm puzzle with no override does not join, and the owner is told why."""

    def test_the_selection_step_does_not_add_it_and_names_both_figures(self, panel) -> None:
        width, height, row_gutter, column_gutter, cell = BELOW_FLOOR
        puzzle_id = panel.puzzle(width, height, row_gutter, column_gutter)
        book_id = panel.book()

        shown = body(panel.select(book_id, [puzzle_id]))

        assert panel.ids_of(book_id) == [], (
            "a puzzle below the floor joined the book with no override: INV-006 "
            "says membership and a stored override come together"
        )
        assert f"{cell:.2f} mm" in shown, (
            f"the refusal must name the puzzle's own cell ({cell:.2f} mm); it said: {shown}"
        )
        assert f"{FLOOR_MM:g} mm floor" in shown, (
            f"the refusal must name the floor it missed; it said: {shown}"
        )

    def test_the_other_puzzles_in_the_same_submission_still_go_in(self, panel) -> None:
        """Refusal is per puzzle, not per batch (FR-031)."""
        small = panel.puzzle(*BELOW_FLOOR[:4])
        big = panel.puzzle(*ABOVE_FLOOR[:4])
        book_id = panel.book()

        panel.select(book_id, [small, big])

        assert panel.ids_of(book_id) == [big]

    def test_the_refused_tile_stays_ticked_so_it_can_be_overridden(self, panel) -> None:
        """The owner is left one tick from the remedy, not back at the start."""
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        panel.select(book_id, [puzzle_id])
        kept = panel.client.get(f"/book/{book_id}/select-puzzles?bucket=26-30")

        assert puzzle_id in kept.get_data(as_text=True)

    @pytest.mark.parametrize("stage", ["store", "route"])
    def test_the_store_is_the_gate_not_the_route(self, panel, stage) -> None:
        """The route may be bypassed; the floor may not (EC-021)."""
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        if stage == "route":
            panel.select(book_id, [puzzle_id])
        else:
            assert panel.books.add_puzzles_to_book(book_id, [puzzle_id]) is True

        assert panel.ids_of(book_id) == []

    def test_refused_in_either_storage_mode(self, shelf) -> None:
        puzzle_id = shelf.puzzle(*BELOW_FLOOR[:4])
        book_id = shelf.book()

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id])

        assert shelf.books.get_book(book_id).puzzle_ids == []
        assert shelf.books.floor_overrides(book_id) == []


# --------------------------------------------------------------------------
# AC-184 — admitted with an override, and the override is stored
# --------------------------------------------------------------------------


class TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt:
    """With an explicit override the puzzle joins — and the override is kept."""

    def test_the_selection_step_adds_it_and_stores_the_override(self, panel) -> None:
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        panel.select(book_id, [puzzle_id], overrides=[puzzle_id])

        assert panel.ids_of(book_id) == [puzzle_id]
        assert panel.books.floor_overrides(book_id) == [puzzle_id]

    def test_the_override_survives_a_reload_in_either_storage_mode(self, shelf) -> None:
        """It is *stored with the book*, not held for the request that gave it."""
        puzzle_id = shelf.puzzle(*BELOW_FLOOR[:4])
        book_id = shelf.book()

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=[puzzle_id])

        reread = BookManager(session_factory=shelf.factory, puzzle_store=shelf.store)
        if shelf.mode == "memory":
            reread = shelf.books  # the in-memory books live on the manager itself
        assert reread.get_book(book_id).puzzle_ids == [puzzle_id]
        assert reread.floor_overrides(book_id) == [puzzle_id]

    def test_a_stored_override_still_covers_the_puzzle_on_a_later_add(self, shelf) -> None:
        """INV-006 asks for a *stored* override; one stored earlier is stored."""
        puzzle_id = shelf.puzzle(*BELOW_FLOOR[:4])
        book_id = shelf.book()
        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=[puzzle_id])
        shelf.books.remove_puzzle_from_book(book_id, puzzle_id)
        # ... but removal takes the override with it (card item 4), so this
        # add is asked for the override again and refuses without one.
        shelf.books.add_puzzles_to_book(book_id, [puzzle_id])
        assert shelf.books.get_book(book_id).puzzle_ids == []

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=[puzzle_id])
        second = shelf.puzzle(*ABOVE_FLOOR[:4])
        shelf.books.add_puzzles_to_book(book_id, [puzzle_id, second])

        assert shelf.books.get_book(book_id).puzzle_ids == [puzzle_id, second]
        assert shelf.books.floor_overrides(book_id) == [puzzle_id]

    def test_removing_the_puzzle_removes_its_override(self, shelf) -> None:
        """Card item 4: no orphan override for a non-member."""
        puzzle_id = shelf.puzzle(*BELOW_FLOOR[:4])
        book_id = shelf.book()
        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=[puzzle_id])

        assert shelf.books.remove_puzzle_from_book(book_id, puzzle_id) is True

        assert shelf.books.floor_overrides(book_id) == []

    def test_an_override_for_a_puzzle_that_clears_the_floor_stores_nothing(self, shelf) -> None:
        """An override no rule needed is the same orphan, arriving from the front."""
        puzzle_id = shelf.puzzle(*ABOVE_FLOOR[:4])
        book_id = shelf.book()

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=[puzzle_id])

        assert shelf.books.get_book(book_id).puzzle_ids == [puzzle_id]
        assert shelf.books.floor_overrides(book_id) == []

    def test_an_override_does_not_leak_to_the_other_puzzles(self, shelf) -> None:
        first = shelf.puzzle(*BELOW_FLOOR[:4])
        second = shelf.puzzle(30, 25, 12, 8, tier="medium")
        book_id = shelf.book()

        shelf.books.add_puzzles_to_book(book_id, [first, second], overrides=[first])

        assert shelf.books.get_book(book_id).puzzle_ids == [first]
        assert shelf.books.floor_overrides(book_id) == [first]


# --------------------------------------------------------------------------
# AC-185 — the paste-IDs route holds the floor too
# --------------------------------------------------------------------------


class TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride:
    """POST /book/<id>/add-puzzles carries no override control, so it refuses."""

    def test_the_paste_ids_form_does_not_add_it_and_names_the_figures(self, panel) -> None:
        width, height, row_gutter, column_gutter, cell = BELOW_FLOOR
        puzzle_id = panel.puzzle(width, height, row_gutter, column_gutter)
        book_id = panel.book()

        shown = body(panel.paste(book_id, [puzzle_id]))

        assert panel.ids_of(book_id) == []
        assert f"{cell:.2f} mm" in shown and f"{FLOOR_MM:g} mm floor" in shown, shown

    def test_the_puzzle_review_modal_posts_to_the_same_route_and_is_covered(self, panel) -> None:
        """``_puzzle_table.html``'s modal sends ``return_to``; same route, same floor."""
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        panel.paste(book_id, [puzzle_id], return_to="/puzzles")

        assert panel.ids_of(book_id) == []

    def test_the_rest_of_a_pasted_list_still_goes_in(self, panel) -> None:
        small = panel.puzzle(*BELOW_FLOOR[:4])
        big = panel.puzzle(*ABOVE_FLOOR[:4])
        book_id = panel.book()

        panel.paste(book_id, [small, big])

        assert panel.ids_of(book_id) == [big]

    def test_refused_in_either_storage_mode(self, shelf) -> None:
        """The route passes no overrides; this is the call it makes."""
        puzzle_id = shelf.puzzle(*BELOW_FLOOR[:4])
        book_id = shelf.book()

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=())

        assert shelf.books.get_book(book_id).puzzle_ids == []


# --------------------------------------------------------------------------
# AC-186 — 4.84 mm is at or above the floor
# --------------------------------------------------------------------------


class TestBookAddPuzzles_AcceptsCellJustAboveFloor:
    """A 40-cells-across puzzle gets 4.84 mm and joins with nothing flagged."""

    def test_it_joins_from_the_selection_step_with_no_override(self, panel) -> None:
        puzzle_id = panel.puzzle(*ABOVE_FLOOR[:4])
        book_id = panel.book()

        shown = body(panel.select(book_id, [puzzle_id]))

        assert panel.ids_of(book_id) == [puzzle_id]
        assert panel.books.floor_overrides(book_id) == []
        assert f"{FLOOR_MM:g} mm floor" not in shown, (
            "an above-floor puzzle must not be mentioned by the floor at all"
        )

    def test_it_joins_from_the_paste_ids_route_too(self, panel) -> None:
        puzzle_id = panel.puzzle(*ABOVE_FLOOR[:4])
        book_id = panel.book()

        panel.paste(book_id, [puzzle_id])

        assert panel.ids_of(book_id) == [puzzle_id]

    def test_it_joins_in_either_storage_mode(self, shelf) -> None:
        puzzle_id = shelf.puzzle(*ABOVE_FLOOR[:4])
        book_id = shelf.book()

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id])

        assert shelf.books.get_book(book_id).puzzle_ids == [puzzle_id]
        assert shelf.books.floor_overrides(book_id) == []

    def test_the_two_fixtures_sit_either_side_of_the_floor(self, shelf) -> None:
        """The boundary is real: the same book, 0.23 mm apart, two verdicts."""
        below = shelf.puzzle(*BELOW_FLOOR[:4])
        above = shelf.puzzle(*ABOVE_FLOOR[:4])
        book_id = shelf.book()
        book = shelf.books.get_book(book_id)

        cells = {
            puzzle_id: book_cell_mm(
                book_page_spec(book),
                shelf.store.get_puzzle(puzzle_id)["clues_rows"],
                shelf.store.get_puzzle(puzzle_id)["clues_cols"],
            )
            for puzzle_id in (below, above)
        }

        assert cells[below] < FLOOR_MM <= cells[above]
        assert cells[below] == pytest.approx(BELOW_FLOOR[4], abs=0.005)
        assert cells[above] == pytest.approx(ABOVE_FLOOR[4], abs=0.005)


# --------------------------------------------------------------------------
# G-1 / EC-021 — the cell is book_cell_mm's, and nothing else
# --------------------------------------------------------------------------


class TestBookFloor_TheCellIsTheOneComputation:
    """The admin panel fits no cells itself (ADR-0036/R2)."""

    def test_the_refusal_carries_compute_layouts_own_millimetres(self, shelf) -> None:
        puzzle_id = shelf.puzzle(*BELOW_FLOOR[:4])
        book_id = shelf.book()
        record = shelf.store.get_puzzle(puzzle_id)

        refusal, = shelf.books.floor_refusals(book_id, [puzzle_id])

        assert refusal.cell_mm == book_cell_mm(
            book_page_spec(shelf.books.get_book(book_id)),
            record["clues_rows"],
            record["clues_cols"],
        )

    def test_the_floor_is_one_named_constant_and_not_a_literal(self) -> None:
        """No second statement of 4.8 anywhere the floor is applied (card item 5).

        Numeric literals only, read off the syntax tree: prose that names the
        figure is documentation and is meant to, but a second *value* would be
        a second floor waiting to disagree with the first.
        """
        root = Path(__file__).resolve().parent.parent / "src" / "nonogram" / "admin"
        for name in ("book_manager.py", "app.py"):
            spelled_out = [
                node.lineno
                for node in ast.walk(ast.parse((root / name).read_text()))
                if isinstance(node, ast.Constant)
                and isinstance(node.value, float)
                and abs(node.value - FLOOR_MM) < 1e-9
            ]
            assert spelled_out == [], (
                f"{name} spells the floor out at line(s) {spelled_out}; it must "
                f"read book_page_spec.FLOOR_MM"
            )

    def test_the_puzzle_is_untouched_by_being_measured(self, shelf) -> None:
        """G-3/ADR-0033/R1: assembly writes book_id and nothing else of a puzzle."""
        puzzle_id = shelf.puzzle(*BELOW_FLOOR[:4])
        book_id = shelf.book()
        before = dict(shelf.store.get_puzzle(puzzle_id))

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=[puzzle_id])

        after = dict(shelf.store.get_puzzle(puzzle_id))
        assert {k: v for k, v in after.items() if k != "book_id"} == {
            k: v for k, v in before.items() if k != "book_id"
        }


# --------------------------------------------------------------------------
# EC-021's "any future route ending in the book store"
# --------------------------------------------------------------------------


class TestBookFloor_EveryAddRouteEndsInTheGuardedStore:
    """The enumeration this card covered, checked against the code on disk."""

    #: The two views FR-031 names. A third would be a route this card's tests
    #: never drove, and the floor's reach would have to be argued again.
    COVERED = {"select_puzzles_for_book", "add_puzzles_to_book"}

    def test_no_third_caller_has_appeared(self) -> None:
        app_py = Path(__file__).resolve().parent.parent / "src" / "nonogram" / "admin" / "app.py"
        callers: set[str] = set()
        enclosing: list[str] = []

        class InnermostFunction(ast.NodeVisitor):
            """Every route in ``app.py`` is nested inside ``create_app``, so the
            caller is the *innermost* function around the call, not every one."""

            def visit_FunctionDef(self, node):
                enclosing.append(node.name)
                self.generic_visit(node)
                enclosing.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, node):
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "add_puzzles_to_book"
                    and enclosing
                ):
                    callers.add(enclosing[-1])
                self.generic_visit(node)

        InnermostFunction().visit(ast.parse(app_py.read_text()))

        assert callers == self.COVERED, (
            "a route reaches the book store that CARD-121 did not cover; the "
            f"floor holds anyway (it is enforced in the store), but {callers - self.COVERED} "
            "has no test naming its refusal"
        )


# --------------------------------------------------------------------------
# The postures: what an unmeasurable cell does
# --------------------------------------------------------------------------


class TestBookFloor_FailsClosedOnWhatItCannotMeasure:
    """A cell nobody can compute is not a cell known to clear the floor."""

    def test_a_stored_puzzle_with_unreadable_clues_is_refused(self, panel) -> None:
        puzzle_id = panel.puzzle(*ABOVE_FLOOR[:4])
        panel.store.puzzles[puzzle_id]["clues_rows"] = "not a clue set"
        book_id = panel.book()

        shown = body(panel.paste(book_id, [puzzle_id]))

        assert panel.ids_of(book_id) == []
        assert "clues_rows" in shown, shown

    def test_a_book_whose_trim_cannot_be_read_takes_nothing_and_names_the_column(
        self, panel
    ) -> None:
        puzzle_id = panel.puzzle(*ABOVE_FLOOR[:4])
        book_id = panel.book()
        panel.books.get_book(book_id).trim_width_cm = "wide-ish"

        shown = body(panel.paste(book_id, [puzzle_id]))

        assert panel.ids_of(book_id) == []
        assert "trim_width_cm" in shown, shown

    def test_an_unmeasurable_puzzle_can_still_be_overridden_in(self, shelf) -> None:
        """The refusal is the floor's, so the floor's own remedy answers it."""
        puzzle_id = shelf.puzzle(*ABOVE_FLOOR[:4])
        book_id = shelf.book()
        if shelf.mode == "memory":
            shelf.store.puzzles[puzzle_id]["clues_cols"] = []
        else:
            from nonogram.db.models import Puzzle

            with shelf.factory() as db:
                db.query(Puzzle).filter(
                    Puzzle.id == uuid.UUID(puzzle_id)
                ).first().clues_cols = []

        shelf.books.add_puzzles_to_book(book_id, [puzzle_id], overrides=[puzzle_id])

        assert shelf.books.get_book(book_id).puzzle_ids == [puzzle_id]
        assert shelf.books.floor_overrides(book_id) == [puzzle_id]


class TestBookFloor_PostureOnIdsThatAreNotPuzzles:
    """An id no row matches, and a manager with no store — decided, not drifted into."""

    def test_an_id_no_row_matches_is_not_the_floors_business(self, panel, caplog) -> None:
        """It has no grid, no clues and nothing to print; referential integrity
        (CARD-103's constraint, CARD-100's repair) owns it, and the readiness
        gate still refuses the book it sits in."""
        book_id = panel.book()
        phantom = str(uuid.uuid4())

        with caplog.at_level("WARNING"):
            panel.books.add_puzzles_to_book(book_id, [phantom])

        assert panel.ids_of(book_id) == [phantom]
        assert phantom in caplog.text
        assert panel.books.floor_overrides(book_id) == []

    def test_a_manager_with_no_store_says_so_rather_than_pretending(self, caplog) -> None:
        """CARD-100 kept this arrangement working; create_app never builds one."""
        lonely = BookManager(session_factory=None)
        book_id = lonely.create_book("Winter", "a book", "christmas", "adults")

        with caplog.at_level("ERROR"):
            lonely.add_puzzles_to_book(book_id, ["p1"])

        assert lonely.get_book(book_id).puzzle_ids == ["p1"]
        assert f"{FLOOR_MM:g} mm floor" in caplog.text


# --------------------------------------------------------------------------
# The guardrails this card must not move
# --------------------------------------------------------------------------


class TestBookFloor_GuardrailsIntact:
    def test_a_published_book_still_refuses_in_the_same_words(self, shelf) -> None:
        """G-4: turning this into a confirmation is CARD-131, not this card."""
        puzzle_id = shelf.puzzle(*ABOVE_FLOOR[:4])
        book_id = shelf.book()
        shelf.books.add_puzzles_to_book(book_id, [puzzle_id])
        book = shelf.books.get_book(book_id)
        if shelf.mode == "memory":
            book.status = "published"
        else:
            from nonogram.db.models import Book as DBBook

            with shelf.factory() as db:
                db.query(DBBook).filter(
                    DBBook.id == uuid.UUID(book_id)
                ).first().status = "published"

        with pytest.raises(ValueError, match="Cannot add puzzles to published book"):
            shelf.books.add_puzzles_to_book(book_id, [shelf.puzzle(*BELOW_FLOOR[:4])])

    def test_an_empty_submission_still_refuses_first(self, shelf) -> None:
        with pytest.raises(ValueError, match="at least one puzzle"):
            shelf.books.add_puzzles_to_book(shelf.book(), [])

    def test_an_unknown_book_is_still_not_found(self, shelf) -> None:
        unknown = str(uuid.uuid4()) if shelf.mode == "db" else "book_999999"
        assert shelf.books.add_puzzles_to_book(unknown, ["p1"]) is False
        assert shelf.books.floor_overrides(unknown) == []

    def test_the_grid_sizes_these_fixtures_use_are_supported_ones(self) -> None:
        """CON-011 via limits.py, rather than two literals repeated here."""
        for width, height, *_ in (BELOW_FLOOR, ABOVE_FLOOR):
            assert MIN_SIZE <= width <= MAX_SIZE and MIN_SIZE <= height <= MAX_SIZE
