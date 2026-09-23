"""EC-021 — below the floor only with a stored override, whatever the route (INV-006).

    For any puzzle, any stored trim and margins and every add route, a puzzle
    whose book cell is below 4.8 mm becomes a member only together with a
    stored override for its id.

The property has three moving parts and this corpus moves all three:

* **any puzzle** — 24 hand-built grids whose cell-count across and down is
  varied deliberately (both sides, both clue gutters), so the cells they draw
  spread across and either side of the floor rather than clustering;
* **any stored trim and margins** — 16 print specifications built from KDP's
  own range, including the Book 1 profile and trims small enough to push a
  comfortable puzzle under the floor;
* **every add route** — the book store itself in *both* storage modes, the
  selection step (which can carry an override) and the detail page's
  paste-IDs form (which cannot), each driven as the product drives it.

No ``hypothesis`` (it is not in the dependency baseline): the corpus is built
by hand with stdlib :class:`random.Random` on a fixed seed, and the case count
is asserted *inside* each test so the corpus cannot silently shrink. The
counts are asserted per verdict as well as in total — a run in which nothing
ever fell below the floor would satisfy "no below-floor member without an
override" vacuously, and is exactly the green that means nothing.

The expected verdict comes from ``book_cell_mm(book_page_spec(book), ...)``.
That is deliberate and is the *other* half of EC-021: the tile, the refusal
and the finalise count must all be that one computation, so a property test
that measured the cell its own way would be asserting the opposite of the
constraint. The independent check is elsewhere —
``tests/test_book_floor.py`` pins the two cells the ACs state (4.61 mm and
4.84 mm) to hand-built grids and figures the card arrived at without this
code.
"""

from __future__ import annotations

import random
import uuid

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_page_spec import FLOOR_MM, book_cell_mm, book_page_spec
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.db import sqlite_session_scope
from tests.test_book_floor import clues_of, dotted_grid

#: The seed. Fixed, so a failure is reproducible and a corpus is a corpus.
SEED = 20260923 + 121

#: How many distinct puzzles the corpus holds, and the smallest number of
#: per-puzzle decisions each test must make. Asserted inside the tests.
PUZZLES = 24
SPECS = 16
MIN_DECISIONS = 300
#: The smallest number of decisions of each *kind* a run must contain. An
#: all-above-floor corpus would pass the property without testing it.
MIN_OF_EACH_VERDICT = 40


# --------------------------------------------------------------------------
# the corpus
# --------------------------------------------------------------------------


def puzzle_shapes() -> list[tuple[int, int, int, int]]:
    """``(width, height, row gutter, column gutter)`` for every corpus puzzle.

    The clue gutters are what make one grid's cell differ from another of the
    same extent — the sheet fits ``width + row_gutter`` cells across — so they
    are drawn independently of the extent rather than derived from it. Both
    extremes of CON-011 are included explicitly, and the rest are drawn.
    """
    rng = random.Random(SEED)
    shapes = [
        (MAX_SIZE, MAX_SIZE, MAX_SIZE // 2, MAX_SIZE // 2),  # the worst case there is
        (MAX_SIZE, MIN_SIZE, MAX_SIZE // 2, MIN_SIZE // 2),
        (MIN_SIZE, MIN_SIZE, 1, 1),  # the kindest
        (MIN_SIZE, MAX_SIZE, 1, MAX_SIZE // 2),
    ]
    while len(shapes) < PUZZLES:
        width = rng.randint(MIN_SIZE, MAX_SIZE)
        height = rng.randint(MIN_SIZE, MAX_SIZE)
        shape = (
            width,
            height,
            rng.randint(1, (width + 1) // 2),
            rng.randint(1, (height + 1) // 2),
        )
        if shape not in shapes:
            shapes.append(shape)
    return shapes


def print_specs() -> list[dict[str, str]]:
    """The stored print columns of every corpus book, as centimetre strings.

    Inside KDP's range (``book_page_spec`` refuses a stored trim outside it,
    and a margin under its minimum), and including the Book 1 profile itself
    so the ACs' own sheet is one of the cases.
    """
    rng = random.Random(SEED + 1)
    widths = ["12.70", "15.24", "17.78", "19.05", "20.32", "21.59", "25.40"]
    heights = ["20.32", "22.86", "25.40", "27.94", "30.48"]
    gutters = ["0.95", "1.27", "1.59", "1.91"]
    outsides = ["0.64", "0.95", "1.27"]
    specs = [
        {
            "trim_width_cm": "21.59",
            "trim_height_cm": "27.94",
            "gutter_margin_cm": "1.27",
            "outside_margin_cm": "0.95",
        },
        # A book from before migration 011: empty margins, read as the profile.
        {
            "trim_width_cm": "21.59",
            "trim_height_cm": "27.94",
            "gutter_margin_cm": None,
            "outside_margin_cm": None,
        },
    ]
    while len(specs) < SPECS:
        spec = {
            "trim_width_cm": rng.choice(widths),
            "trim_height_cm": rng.choice(heights),
            "gutter_margin_cm": rng.choice(gutters),
            "outside_margin_cm": rng.choice(outsides),
        }
        if spec not in specs:
            specs.append(spec)
    return specs


class Corpus:
    """Every corpus puzzle stored once, in one storage mode, with its clues."""

    def __init__(self, factory, *, store=None, books=None):
        self.factory = factory
        self.store = store if store is not None else PuzzleReviewService(session_factory=factory)
        self.books = (
            books
            if books is not None
            else BookManager(session_factory=factory, puzzle_store=self.store)
        )
        self.ids: list[str] = []
        self.clues: dict[str, tuple] = {}
        for width, height, row_gutter, column_gutter in puzzle_shapes():
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
                difficulty_tier="easy",
                quality_score=50,
                recognizability="medium",
                strategies_used=[],
                batch_id=None,
                source_image=f"{width}x{height}.png",
            )
            self.store.approve_puzzle(puzzle_id)
            self.ids.append(puzzle_id)
            self.clues[puzzle_id] = (clues_rows, clues_cols)

    def book_on(self, spec: dict, title: str) -> str:
        """A draft book whose stored print columns are ``spec``."""
        book_id = self.books.create_book(title, "a book", "christmas", "adults")
        if self.factory is None:
            for column, value in spec.items():
                setattr(self.books.books[book_id], column, value)
            return book_id

        from nonogram.db.models import Book as DBBook

        with self.factory() as db:
            row = db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).first()
            for column, value in spec.items():
                setattr(row, column, value)
        return book_id

    def release(self, book_id: str) -> None:
        """Give every member back, so the next book starts from free puzzles.

        One puzzle belongs to at most one book (ADR-0033, G-2), and
        ``_mirror_onto_puzzles`` writes ``puzzles.book_id``. Putting the same
        24 puzzles into 16 successive books without releasing them left the
        corpus in exactly the multi-book state the ADR forbids, so a regression
        in the assigned-puzzle exclusion could not have shown up here (review
        cycle 1, F-007). Called *after* each book's verdicts are checked, so
        nothing the property asserts is affected and the corpus does not shrink.
        """
        for puzzle_id in list(self.books.get_book(book_id).puzzle_ids):
            self.books.remove_puzzle_from_book(book_id, puzzle_id)

    def below_floor(self, book_id: str) -> dict[str, bool]:
        """Whether each corpus puzzle is below this book's floor.

        ``book_cell_mm(book_page_spec(book), ...)`` — the one computation
        (EC-021), which is what the property is about.
        """
        spec = book_page_spec(self.books.get_book(book_id))
        return {
            puzzle_id: book_cell_mm(spec, *self.clues[puzzle_id]) < FLOOR_MM
            for puzzle_id in self.ids
        }


def chosen_overrides(rng: random.Random, puzzle_ids) -> list[str]:
    """A pseudo-random subset of the ids, as the tiles the owner ticked."""
    return [puzzle_id for puzzle_id in puzzle_ids if rng.random() < 0.5]


# --------------------------------------------------------------------------
# the property, stated once and checked against each route's outcome
# --------------------------------------------------------------------------


class Tally:
    """The per-puzzle verdicts one route produced, counted by kind."""

    def __init__(self):
        self.admitted_above = 0
        self.admitted_below_with_override = 0
        self.refused_below = 0

    @property
    def total(self) -> int:
        return self.admitted_above + self.admitted_below_with_override + self.refused_below

    def check(
        self, route: str, book_id: str, below: dict[str, bool], members, stored_overrides
    ) -> None:
        """INV-006 over one book, after one submission through ``route``."""
        members = set(members)
        stored_overrides = set(stored_overrides)
        for puzzle_id, is_below in below.items():
            if puzzle_id not in members:
                # The other direction, so that a floor which refused
                # *everything* could not pass this property: only a below-floor
                # cell is the floor's to refuse.
                assert is_below, (
                    f"[{route}] puzzle {puzzle_id} prints at or above the "
                    f"{FLOOR_MM:g} mm floor on book {book_id} and was submitted, "
                    f"but is not a member — the floor refused a puzzle it clears"
                )
                self.refused_below += 1
                continue
            if is_below:
                assert puzzle_id in stored_overrides, (
                    f"[{route}] puzzle {puzzle_id} prints below the "
                    f"{FLOOR_MM:g} mm floor on book {book_id} and became a member "
                    f"with no override stored for it — INV-006 says the two come "
                    f"together"
                )
                self.admitted_below_with_override += 1
            else:
                self.admitted_above += 1

        assert stored_overrides <= members, (
            f"[{route}] book {book_id} stores an override for a puzzle that is not "
            f"a member: {sorted(stored_overrides - members)}"
        )
        assert all(below[p] for p in stored_overrides if p in below), (
            f"[{route}] book {book_id} stores an override no rule needed: "
            f"{sorted(p for p in stored_overrides if p in below and not below[p])}"
        )

    def assert_covered(self, route: str) -> None:
        assert self.total >= MIN_DECISIONS, (
            f"[{route}] the corpus shrank to {self.total} per-puzzle decisions; "
            f"EC-021 is checked over at least {MIN_DECISIONS}"
        )
        for kind, count in (
            ("admitted above the floor", self.admitted_above),
            ("admitted below it with an override", self.admitted_below_with_override),
            ("refused below it", self.refused_below),
        ):
            assert count >= MIN_OF_EACH_VERDICT, (
                f"[{route}] only {count} decision(s) {kind}: below "
                f"{MIN_OF_EACH_VERDICT}, the property would hold vacuously"
            )


# --------------------------------------------------------------------------
# PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    """The panel in in-memory mode, so the two routes can be driven for real."""
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


# EC-021's membership half: every route, every trim, every puzzle. The
# named test is spelled the way this suite spells a property test —
# `test_PropertyTest_<name>` as module-level functions, one per route
# (tests/property/test_book_export_interior.py is the precedent).


@pytest.mark.parametrize("mode", ["memory", "db"])
def test_PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride(
    mode, tmp_path
) -> None:
    """The gate itself — where membership is written, so no route can pass it."""
    factory = None if mode == "memory" else sqlite_session_scope(tmp_path, "floor.db")
    corpus = Corpus(factory)
    rng = random.Random(SEED + 2)
    tally = Tally()

    for index, spec in enumerate(print_specs()):
        book_id = corpus.book_on(spec, f"Book {index}")
        below = corpus.below_floor(book_id)
        overrides = chosen_overrides(rng, corpus.ids)

        corpus.books.add_puzzles_to_book(book_id, list(corpus.ids), overrides)

        tally.check(
            f"store/{mode}",
            book_id,
            below,
            corpus.books.get_book(book_id).puzzle_ids,
            corpus.books.floor_overrides(book_id),
        )
        corpus.release(book_id)

    tally.assert_covered(f"store/{mode}")


def test_PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride_selection_step(
    admin_app,
) -> None:
    """POST /book/<id>/select-puzzles — the route that can carry an override."""
    # The panel's own store and manager, so the route writes where the
    # assertions read.
    corpus = Corpus(
        None,
        store=admin_app.puzzle_review_service,
        books=admin_app.book_manager,
    )
    rng = random.Random(SEED + 3)
    tally = Tally()
    client = admin_app.test_client()

    for index, spec in enumerate(print_specs()):
        book_id = corpus.book_on(spec, f"Selected {index}")
        below = corpus.below_floor(book_id)
        overrides = chosen_overrides(rng, corpus.ids)
        form = {
            "bucket": "26-30",
            "shown_ids": list(corpus.ids),
            "puzzle_ids": list(corpus.ids),
        }
        for puzzle_id in overrides:
            form[f"override_{puzzle_id}"] = "on"

        response = client.post(
            f"/book/{book_id}/select-puzzles", data=form, follow_redirects=True
        )
        assert response.status_code == 200

        tally.check(
            "select-puzzles",
            book_id,
            below,
            corpus.books.get_book(book_id).puzzle_ids,
            corpus.books.floor_overrides(book_id),
        )
        corpus.release(book_id)

    tally.assert_covered("select-puzzles")


def test_PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride_paste_ids_route(
    admin_app,
) -> None:
    """POST /book/<id>/add-puzzles carries no override control (FR-031).

    Two submissions per book: the paste alone, which may admit only what
    clears the floor, and then the same paste after the selection step has
    stored overrides for some of the refused ids — because INV-006 asks for
    a *stored* override, and one stored by another route is stored.
    """
    corpus = Corpus(
        None,
        store=admin_app.puzzle_review_service,
        books=admin_app.book_manager,
    )
    rng = random.Random(SEED + 4)
    client = admin_app.test_client()
    alone, after_override = Tally(), Tally()

    for index, spec in enumerate(print_specs()):
        book_id = corpus.book_on(spec, f"Pasted {index}")
        below = corpus.below_floor(book_id)

        pasted = client.post(
            f"/book/{book_id}/add-puzzles",
            data={"puzzle_ids": ",".join(corpus.ids)},
            follow_redirects=True,
        )
        assert pasted.status_code == 200
        alone.check(
            "add-puzzles",
            book_id,
            below,
            corpus.books.get_book(book_id).puzzle_ids,
            corpus.books.floor_overrides(book_id),
        )
        assert corpus.books.floor_overrides(book_id) == [], (
            "the paste-IDs route admits no override, so it may store none"
        )

        refused = [p for p in corpus.ids if below[p]]
        granted = chosen_overrides(rng, refused)
        form = {
            "bucket": "26-30",
            "shown_ids": refused,
            "puzzle_ids": refused,
            **{f"override_{p}": "on" for p in granted},
        }
        client.post(
            f"/book/{book_id}/select-puzzles", data=form, follow_redirects=True
        )
        client.post(
            f"/book/{book_id}/add-puzzles",
            data={"puzzle_ids": ",".join(corpus.ids)},
            follow_redirects=True,
        )
        after_override.check(
            "add-puzzles after a stored override",
            book_id,
            below,
            corpus.books.get_book(book_id).puzzle_ids,
            corpus.books.floor_overrides(book_id),
        )
        corpus.release(book_id)

    assert alone.admitted_below_with_override == 0, (
        "the paste-IDs route let a below-floor puzzle in on its own"
    )
    assert alone.total >= MIN_DECISIONS and alone.refused_below >= MIN_OF_EACH_VERDICT
    assert alone.admitted_above >= MIN_OF_EACH_VERDICT
    after_override.assert_covered("add-puzzles after a stored override")


def test_PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride_a_removed_puzzle_keeps_no_override(
    tmp_path,
) -> None:
    """Card item 4, over the whole corpus: no orphan override, either mode."""
    checked = 0
    for mode in ("memory", "db"):
        factory = None if mode == "memory" else sqlite_session_scope(tmp_path, f"{mode}.db")
        corpus = Corpus(factory)
        for index, spec in enumerate(print_specs()):
            book_id = corpus.book_on(spec, f"Emptied {index}")
            below = corpus.below_floor(book_id)
            corpus.books.add_puzzles_to_book(book_id, list(corpus.ids), corpus.ids)
            assert set(corpus.books.floor_overrides(book_id)) == {
                p for p in corpus.ids if below[p]
            }

            for puzzle_id in corpus.ids:
                corpus.books.remove_puzzle_from_book(book_id, puzzle_id)
                checked += 1
                assert puzzle_id not in corpus.books.floor_overrides(book_id), (
                    f"[{mode}] book {book_id} kept an override for {puzzle_id}, "
                    f"which is no longer a member"
                )

            assert corpus.books.floor_overrides(book_id) == []

    assert checked >= MIN_DECISIONS, (
        f"only {checked} removal(s) checked; the corpus shrank"
    )
