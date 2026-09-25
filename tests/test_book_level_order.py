"""CARD-126 — the book runs easy, then medium, then hard (FR-041, INV-009, TERM-032).

    AC-257  a book arranged E1, E2, M1: moving E2 up gives E2, E1, M1
    AC-258  a book arranged E1, E2, M1, M2: moving M1 up changes nothing —
            the move would cross the easy/medium boundary — and the owner is
            told why
    AC-259  a book arranged E1, E2, M1, H1: adding an easy E3 puts it before
            M1, at the end of the easy level

plus the postures the invariant needs to be worth anything: what the page
offers at a level's ends, what a legacy mixed arrangement reads as and when it
gets normalised, what happens to a puzzle with no readable tier, and that the
tier is *read* and never re-graded (ADR-0033/R1, ADR-0031).

The evidence class for the three ACs is the Flask test client — they are
user-facing criteria on a server-rendered screen and this project has no
browser harness, so each drives the real POST route with real form fields and
reads the real HTML that came back, exactly as CARD-121's and CARD-122's tests
do. The store-level rule is asserted in **both** storage modes beside it,
because the grouping is a rule of the aggregate and not of a backend.

The expected orders here are written out by hand, never re-derived by calling
``book_level_order`` on the same input: a test that asks the function under
test what the answer is proves only that it agrees with itself.
"""

from __future__ import annotations

import html as html_module
import re
import uuid

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_plan import (
    CROSS_LEVEL_REFUSAL,
    UNGRADED_RANK,
    LevelBoundary,
    book_level_order,
    book_levels,
    is_level_order,
    level_rank,
    moved_within_level,
    place_in_level,
)
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.difficulty import Tier
from tests.helpers.db import sqlite_session_scope

MODES = ["memory", "db"]


# --------------------------------------------------------------------------
# the shelf: a store, a book manager, and one storage mode
# --------------------------------------------------------------------------


def solid_grid(size: int = 10):
    """A fully filled square — uniquely solvable, which the store insists on."""
    return [[True] * size for _ in range(size)]


class Shelf:
    """A book manager and the store behind it, in one storage mode."""

    def __init__(self, mode, tmp_path):
        self.mode = mode
        self.factory = None if mode == "memory" else sqlite_session_scope(tmp_path, "order.db")
        self.store = PuzzleReviewService(session_factory=self.factory)
        self.books = BookManager(session_factory=self.factory, puzzle_store=self.store)
        self._made = 0

    def puzzle(self, tier: str, size: int = 10) -> str:
        """One stored puzzle carrying ``tier`` as its stored grade."""
        self._made += 1
        grid = solid_grid(size)
        puzzle_id = self.store.add_puzzle(
            grid=grid,
            clues_rows=[[size]] * size,
            clues_cols=[[size]] * size,
            width=size,
            height=size,
            theme="generic",
            difficulty_score=10,
            difficulty_tier=tier,
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            batch_id=None,
            source_image=f"{tier}-{self._made}.png",
        )
        self.store.approve_puzzle(puzzle_id)
        return puzzle_id

    def book(self, title="Winter") -> str:
        return self.books.create_book(title, "a book", "christmas", "adults")

    def ids_of(self, book_id):
        return list(self.books.get_book(book_id).puzzle_ids)


@pytest.fixture(params=MODES)
def shelf(request, tmp_path):
    return Shelf(request.param, tmp_path)


# --------------------------------------------------------------------------
# the panel: the real arrange route, driven through the test client
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
    image_manager_module._image_manager = None
    book_manager_module._book_manager = BookManager(session_factory=None)


class Panel:
    """The app, its store and its books, plus the arrange route as one-liners."""

    def __init__(self, app):
        self.app = app
        self.store = app.puzzle_review_service
        self.books = app.book_manager
        self.client = app.test_client()
        self._made = 0

    puzzle = Shelf.puzzle
    book = Shelf.book
    ids_of = Shelf.ids_of

    def arrange(self, book_id):
        """GET the arrangement screen."""
        return self.client.get(f"/book/{book_id}/arrange-puzzles")

    def move(self, book_id, puzzle_id, direction):
        """POST one of the arrange screen's move buttons, as the page submits it."""
        return self.client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": f"move_{direction}", "puzzle_id": puzzle_id},
            follow_redirects=True,
        )

    def paste(self, book_id, puzzle_ids):
        """POST the detail page's paste-IDs add form."""
        return self.client.post(
            f"/book/{book_id}/add-puzzles",
            data={"puzzle_ids": ",".join(puzzle_ids)},
            follow_redirects=True,
        )


@pytest.fixture
def panel(admin_app):
    return Panel(admin_app)


def text_of(markup: str) -> str:
    """The rendered page as readable text: no tags, no entities, one space."""
    without_scripts = re.sub(r"(?s)<script.*?</script>", " ", markup)
    return re.sub(
        r"\s+", " ", html_module.unescape(re.sub(r"<[^>]+>", " ", without_scripts))
    ).strip()


def body(response) -> str:
    assert response.status_code == 200
    return text_of(response.get_data(as_text=True))


def a_book_of(source, *tiers):
    """A book holding one puzzle per tier named, added in that order."""
    ids = [source.puzzle(tier) for tier in tiers]
    book_id = source.book()
    source.books.add_puzzles_to_book(book_id, ids)
    return book_id, ids


# --------------------------------------------------------------------------
# AC-257 — a move inside a level is the owner's arrangement, and it sticks
# --------------------------------------------------------------------------


class TestBookArrange_MoveWithinLevelKeepsOwnerOrder:
    """E1, E2, M1 with E2 moved up is E2, E1, M1."""

    def test_the_arrange_screen_moves_it_and_stores_the_new_order(self, panel) -> None:
        book_id, (e1, e2, m1) = a_book_of(panel, "easy", "easy", "medium")
        assert panel.ids_of(book_id) == [e1, e2, m1]

        shown = body(panel.move(book_id, e2, "up"))

        assert panel.ids_of(book_id) == [e2, e1, m1], (
            "a move inside the easy level is the owner's arrangement and must be kept"
        )
        assert "Moved puzzle up" in shown, shown

    @pytest.mark.parametrize("mode", MODES)
    def test_the_store_moves_it_in_either_storage_mode(self, mode, tmp_path) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1) = a_book_of(shelf, "easy", "easy", "medium")

        assert shelf.books.move_puzzle_up(book_id, e2) is True

        assert shelf.ids_of(book_id) == [e2, e1, m1]

    @pytest.mark.parametrize("mode", MODES)
    def test_a_move_down_inside_a_level_is_the_same_rule(self, mode, tmp_path) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, m2) = a_book_of(shelf, "easy", "easy", "medium", "medium")

        assert shelf.books.move_puzzle_down(book_id, m1) is True

        assert shelf.ids_of(book_id) == [e1, e2, m2, m1]

    @pytest.mark.parametrize("mode", MODES)
    def test_the_book_ends_still_report_nothing_happened(self, mode, tmp_path) -> None:
        """The very top and the very bottom keep their old answer: False, not a refusal."""
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, _e2, h1) = a_book_of(shelf, "easy", "easy", "hard")

        assert shelf.books.move_puzzle_up(book_id, e1) is False
        assert shelf.books.move_puzzle_down(book_id, h1) is False
        assert shelf.ids_of(book_id) == [e1, _e2, h1]

    def test_the_page_disables_the_controls_at_each_levels_own_ends(self, panel) -> None:
        """The move the store would refuse is not offered at all (the card's item 4).

        E1, E2, M1, M2: each level's first row has no working "up" and each
        level's last row no working "down" — four disabled controls, not the
        two a single flat list would have had.
        """
        book_id, _ids = a_book_of(panel, "easy", "easy", "medium", "medium")

        markup = panel.arrange(book_id).get_data(as_text=True)

        for label in (
            "First in the Easy level",
            "Last in the Easy level",
            "First in the Medium level",
            "Last in the Medium level",
        ):
            assert f'aria-label="{label}"' in markup, f"{label} is not disabled: {markup}"
        assert markup.count("disabled") == 4, (
            "exactly one disabled control at each end of each level"
        )
        assert "Hard level" not in markup, "no level this book does not have"


# --------------------------------------------------------------------------
# AC-258 — a move across a level boundary is refused and changes nothing
# --------------------------------------------------------------------------


class TestBookArrange_MoveAcrossLevelBoundaryRefused:
    """E1, E2, M1, M2 with M1 moved up stays E1, E2, M1, M2."""

    def test_the_arrange_screen_refuses_it_and_says_why(self, panel) -> None:
        book_id, (e1, e2, m1, m2) = a_book_of(panel, "easy", "easy", "medium", "medium")

        shown = body(panel.move(book_id, m1, "up"))

        assert panel.ids_of(book_id) == [e1, e2, m1, m2], (
            "the move would carry a medium puzzle above an easy one; INV-009 "
            "leaves the order exactly as it was"
        )
        assert "easy, then medium, then hard" in shown, (
            f"the refusal must name the rule it enforced; the page said: {shown}"
        )
        assert "Moved puzzle up" not in shown, (
            f"a move that did not happen must not be reported as one: {shown}"
        )

    def test_the_last_of_a_level_cannot_be_moved_down_either(self, panel) -> None:
        book_id, (e1, e2, m1, m2) = a_book_of(panel, "easy", "easy", "medium", "medium")

        shown = body(panel.move(book_id, e2, "down"))

        assert panel.ids_of(book_id) == [e1, e2, m1, m2]
        assert "easy, then medium, then hard" in shown, shown

    @pytest.mark.parametrize("mode", MODES)
    def test_the_store_refuses_it_in_either_storage_mode(self, mode, tmp_path) -> None:
        """The store is the gate, not the route: the page may be bypassed."""
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, m2) = a_book_of(shelf, "easy", "easy", "medium", "medium")

        with pytest.raises(LevelBoundary):
            shelf.books.move_puzzle_up(book_id, m1)

        assert shelf.ids_of(book_id) == [e1, e2, m1, m2]

    @pytest.mark.parametrize("mode", MODES)
    def test_a_submitted_order_that_is_not_grouped_is_refused_whole(
        self, mode, tmp_path
    ) -> None:
        """``reorder_puzzles`` is the third door into the order, and it holds too."""
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, m2) = a_book_of(shelf, "easy", "easy", "medium", "medium")

        with pytest.raises(LevelBoundary):
            shelf.books.reorder_puzzles(book_id, [e1, m1, e2, m2])

        assert shelf.ids_of(book_id) == [e1, e2, m1, m2]

    @pytest.mark.parametrize("mode", MODES)
    def test_a_grouped_reorder_is_still_accepted(self, mode, tmp_path) -> None:
        """The refusal is about the grouping, not about reordering (no false refusal)."""
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, m2) = a_book_of(shelf, "easy", "easy", "medium", "medium")

        assert shelf.books.reorder_puzzles(book_id, [e2, e1, m2, m1]) is True

        assert shelf.ids_of(book_id) == [e2, e1, m2, m1]

    def test_the_refusal_is_a_value_error_for_callers_that_only_know_those(self) -> None:
        assert issubclass(LevelBoundary, ValueError)


# --------------------------------------------------------------------------
# AC-259 — a new puzzle lands at the end of its own level
# --------------------------------------------------------------------------


class TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel:
    """E1, E2, M1, H1 plus an easy E3 is E1, E2, E3, M1, H1."""

    @pytest.mark.parametrize("mode", MODES)
    def test_an_easy_addition_sits_before_the_medium_one(self, mode, tmp_path) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, h1) = a_book_of(shelf, "easy", "easy", "medium", "hard")
        e3 = shelf.puzzle("easy")

        shelf.books.add_puzzles_to_book(book_id, [e3])

        order = shelf.ids_of(book_id)
        assert order == [e1, e2, e3, m1, h1]
        assert order.index(e3) < order.index(m1), "AC-259: E3 sits before M1"

    @pytest.mark.parametrize("mode", MODES)
    def test_each_level_takes_its_own_addition(self, mode, tmp_path) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, m1, h1) = a_book_of(shelf, "easy", "medium", "hard")
        e2, m2, h2 = shelf.puzzle("easy"), shelf.puzzle("medium"), shelf.puzzle("hard")

        shelf.books.add_puzzles_to_book(book_id, [h2, m2, e2])

        assert shelf.ids_of(book_id) == [e1, e2, m1, m2, h1, h2]

    @pytest.mark.parametrize("mode", MODES)
    def test_two_additions_to_one_level_keep_the_order_they_were_submitted_in(
        self, mode, tmp_path
    ) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, m1) = a_book_of(shelf, "easy", "medium")
        first, second = shelf.puzzle("easy"), shelf.puzzle("easy")

        shelf.books.add_puzzles_to_book(book_id, [first, second])

        assert shelf.ids_of(book_id) == [e1, first, second, m1]

    def test_the_paste_ids_route_places_it_in_its_level_too(self, panel) -> None:
        """The second add route, driven as the detail page submits it."""
        book_id, (e1, e2, m1, h1) = a_book_of(panel, "easy", "easy", "medium", "hard")
        e3 = panel.puzzle("easy")

        panel.paste(book_id, [e3])

        assert panel.ids_of(book_id) == [e1, e2, e3, m1, h1]

    @pytest.mark.parametrize("mode", MODES)
    def test_a_first_puzzle_of_a_new_level_lands_between_the_levels_it_belongs(
        self, mode, tmp_path
    ) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, h1) = a_book_of(shelf, "easy", "hard")
        m1 = shelf.puzzle("medium")

        shelf.books.add_puzzles_to_book(book_id, [m1])

        assert shelf.ids_of(book_id) == [e1, m1, h1]


# --------------------------------------------------------------------------
# G-4, the titles half — a removal is one member's, not the book's titles
# --------------------------------------------------------------------------


class TestBookRemovePuzzle_LeavesTheOtherTitlesAlone:
    """Taking one titled puzzle out leaves every other title exactly as set.

    G-4's *arrangement* half is pinned elsewhere — EC-029's property asserts the
    surviving order after repeated removes in both storage modes. Its *titles*
    half was pinned nowhere: ``remove_puzzle_from_book`` drops the removed id
    from ``puzzle_titles`` by rebuilding the dict, and a rebuild that dropped
    the wrong key, or every key, would have passed the whole suite.

    (What this does *not* assert is that the removed puzzle's own entry is gone:
    only the DB branch drops it — the in-memory branch never touches
    ``puzzle_titles`` at all — so that is a divergence to settle, not a rule to
    pin here.)
    """

    @pytest.mark.parametrize("mode", MODES)
    def test_removing_one_titled_puzzle_keeps_the_rest_and_their_titles(
        self, mode, tmp_path
    ) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, h1) = a_book_of(shelf, "easy", "easy", "medium", "hard")
        titles = {e1: "First light", e2: "Snowfall", m1: "The Rain Deer", h1: "Thaw"}
        for puzzle_id, title in titles.items():
            assert shelf.books.set_puzzle_title(book_id, puzzle_id, title) is True

        assert shelf.books.remove_puzzle_from_book(book_id, e2) is True

        assert shelf.ids_of(book_id) == [e1, m1, h1], (
            "G-4: the rest of the arrangement, in its own order, minus the removed one"
        )
        assert [shelf.books.get_puzzle_title(book_id, p) for p in (e1, m1, h1)] == [
            titles[e1],
            titles[m1],
            titles[h1],
        ], "G-4: ... and every surviving title still exactly what the owner set"


# --------------------------------------------------------------------------
# The tier is read, never re-graded (G-2, ADR-0033/R1, ADR-0031)
# --------------------------------------------------------------------------


class TestBookLevelOrder_ReadsTheStoredTier:
    """What decides a puzzle's level is the row's own word, and only that."""

    @pytest.mark.parametrize("mode", MODES)
    def test_the_row_is_never_rewritten_by_an_order_change(self, mode, tmp_path) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1) = a_book_of(shelf, "easy", "easy", "medium")
        before = {pid: shelf.store.get_puzzle(pid)["difficulty_tier"] for pid in (e1, e2, m1)}

        shelf.books.move_puzzle_up(book_id, e2)

        after = {pid: shelf.store.get_puzzle(pid)["difficulty_tier"] for pid in (e1, e2, m1)}
        assert after == before, "book assembly reads a tier; it never writes one"

    @pytest.mark.parametrize("mode", MODES)
    def test_size_does_not_decide_the_level(self, mode, tmp_path) -> None:
        """A big easy puzzle is still easy: no level is derived from a grid (ADR-0031)."""
        shelf = Shelf(mode, tmp_path)
        big_easy = shelf.puzzle("easy", size=30)
        small_hard = shelf.puzzle("hard", size=10)
        book_id = shelf.book()

        shelf.books.add_puzzles_to_book(book_id, [small_hard, big_easy])

        assert shelf.ids_of(book_id) == [big_easy, small_hard]

    @pytest.mark.parametrize("mode", MODES)
    def test_a_legacy_guess_row_prints_with_the_hard_level(self, mode, tmp_path) -> None:
        """ADR-0031/R3: the retired fourth tier reads back as hard, unrewritten."""
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, m1) = a_book_of(shelf, "easy", "medium")
        guess = shelf.puzzle("guess")

        shelf.books.add_puzzles_to_book(book_id, [guess])

        assert shelf.ids_of(book_id) == [e1, m1, guess]
        assert shelf.store.get_puzzle(guess)["difficulty_tier"] == "guess"


# --------------------------------------------------------------------------
# A legacy mixed arrangement: read grouped, normalised only by a move
# --------------------------------------------------------------------------


class TestBookLevelOrder_LegacyMixedArrangement:
    """A book arranged before this rule keeps its stored list until it is moved."""

    def _mixed(self, shelf):
        """A book whose *stored* order interleaves the levels, as an old one may."""
        book_id, (e1, m1, h1) = a_book_of(shelf, "easy", "medium", "hard")
        e2 = shelf.puzzle("easy")
        # Written straight past the aggregate, which is the only way such an
        # order can exist now: it is what a book stored before CARD-126 holds.
        _write_raw_order(shelf, book_id, [m1, e1, h1, e2])
        return book_id, (e1, e2, m1, h1)

    @pytest.mark.parametrize("mode", MODES)
    def test_the_stored_list_is_read_grouped_without_being_rewritten(
        self, mode, tmp_path
    ) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, h1) = self._mixed(shelf)

        levels = shelf.books.puzzle_levels(book_id)

        assert levels == [(Tier.EASY, [e1, e2]), (Tier.MEDIUM, [m1]), (Tier.HARD, [h1])]
        assert shelf.ids_of(book_id) == [m1, e1, h1, e2], (
            "reading a legacy order grouped must not rewrite it"
        )

    @pytest.mark.parametrize("mode", MODES)
    def test_the_first_move_writes_the_grouped_order_back(self, mode, tmp_path) -> None:
        """The card's item 2: the move is the one point of normalisation."""
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, h1) = self._mixed(shelf)

        assert shelf.books.move_puzzle_down(book_id, e1) is True

        assert shelf.ids_of(book_id) == [e2, e1, m1, h1]

    @pytest.mark.parametrize("mode", MODES)
    def test_an_add_to_a_legacy_book_leaves_the_rest_of_the_list_alone(
        self, mode, tmp_path
    ) -> None:
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, h1) = self._mixed(shelf)
        e3 = shelf.puzzle("easy")

        shelf.books.add_puzzles_to_book(book_id, [e3])

        assert shelf.ids_of(book_id) == [m1, e1, h1, e2, e3], (
            "the new easy puzzle goes after the last easy one there is; no other "
            "stored position moves, because an add is not a normalisation"
        )
        assert shelf.books.puzzle_levels(book_id)[0] == (Tier.EASY, [e1, e2, e3]), (
            "and read grouped it is the end of the easy level, which is the rule"
        )


def _write_raw_order(shelf, book_id, order):
    """Store ``order`` verbatim, past the aggregate — a pre-CARD-126 row."""
    if shelf.mode == "memory":
        shelf.books.books[book_id].puzzle_ids = list(order)
        return
    from nonogram.db.models import Book as DBBook

    with shelf.factory() as db:
        row = db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).first()
        row.puzzle_ids = list(order)
        db.commit()


# --------------------------------------------------------------------------
# The pure helper on its own (the one grouping, item 1)
# --------------------------------------------------------------------------


EASY, MEDIUM, HARD = Tier.EASY, Tier.MEDIUM, Tier.HARD


def lookup(**tiers):
    """A ``tier_of`` over a hand-written map; anything unnamed has no tier."""
    return lambda puzzle_id: tiers.get(puzzle_id)


class TestBookLevelOrder_ThePureGrouping:
    """``book_plan.book_level_order`` and the functions beside it."""

    def test_it_groups_easy_then_medium_then_hard(self) -> None:
        tier_of = lookup(a=HARD, b=EASY, c=MEDIUM, d=EASY)

        assert book_level_order(["a", "b", "c", "d"], tier_of) == ["b", "d", "c", "a"]

    def test_it_keeps_the_relative_order_inside_a_level(self) -> None:
        tier_of = lookup(a=EASY, b=EASY, c=EASY)

        assert book_level_order(["c", "a", "b"], tier_of) == ["c", "a", "b"]

    def test_it_is_idempotent(self) -> None:
        tier_of = lookup(a=HARD, b=EASY, c=MEDIUM)
        once = book_level_order(["a", "b", "c"], tier_of)

        assert book_level_order(once, tier_of) == once

    @pytest.mark.parametrize("unreadable", [None, "", "extreme", 7, "  "])
    def test_a_puzzle_with_no_readable_tier_sorts_after_the_graded_ones(
        self, unreadable
    ) -> None:
        """Never silently inside easy, and never dropped.

        The unreadable value goes through to ``tier_of`` as it stands — a
        blank, a word that is not a tier, a number — so each case exercises
        ``level_rank``'s non-``Tier`` branch instead of collapsing to ``None``
        five times over (review cycle 1, F-003).
        """
        tier_of = lookup(a=EASY, b=HARD, x=unreadable)

        assert book_level_order(["x", "b", "a"], tier_of) == ["a", "b", "x"]
        assert level_rank(unreadable) == UNGRADED_RANK

    def test_the_order_is_always_a_permutation_of_the_membership(self) -> None:
        tier_of = lookup(a=EASY, c=MEDIUM)

        grouped = book_level_order(["a", "b", "c", "b"], tier_of)

        assert sorted(grouped) == ["a", "b", "b", "c"]

    def test_levels_hold_one_entry_per_non_empty_level(self) -> None:
        tier_of = lookup(a=EASY, b=HARD, c=HARD)

        assert book_levels(["b", "a", "c"], tier_of) == [(EASY, ["a"]), (HARD, ["b", "c"])]

    def test_an_ungraded_tail_is_its_own_last_entry(self) -> None:
        tier_of = lookup(a=EASY)

        assert book_levels(["x", "a"], tier_of) == [(EASY, ["a"]), (None, ["x"])]

    def test_is_level_order_is_the_predicate_for_the_same_rule(self) -> None:
        tier_of = lookup(a=EASY, b=MEDIUM)

        assert is_level_order(["a", "b"], tier_of) is True
        assert is_level_order(["b", "a"], tier_of) is False

    def test_place_in_level_appends_inside_the_level(self) -> None:
        tier_of = lookup(e1=EASY, e2=EASY, m1=MEDIUM, h1=HARD, e3=EASY)

        placed = place_in_level(["e1", "e2", "m1", "h1"], ["e3"], tier_of)

        assert placed == ["e1", "e2", "e3", "m1", "h1"]

    def test_place_in_level_leaves_a_mixed_list_otherwise_untouched(self) -> None:
        tier_of = lookup(m1=MEDIUM, e1=EASY, h1=HARD, e2=EASY)

        placed = place_in_level(["m1", "e1", "h1"], ["e2"], tier_of)

        assert placed == ["m1", "e1", "e2", "h1"]

    def test_moved_within_level_reports_the_ends_of_the_book_as_nothing_happened(
        self,
    ) -> None:
        tier_of = lookup(a=EASY, b=EASY)

        assert moved_within_level(["a", "b"], "a", -1, tier_of) is None
        assert moved_within_level(["a", "b"], "b", +1, tier_of) is None

    def test_moved_within_level_refuses_a_boundary_crossing(self) -> None:
        tier_of = lookup(a=EASY, b=MEDIUM)

        with pytest.raises(LevelBoundary) as raised:
            moved_within_level(["a", "b"], "b", -1, tier_of)

        assert str(raised.value) == CROSS_LEVEL_REFUSAL

    def test_moved_within_level_returns_the_grouped_order(self) -> None:
        """A move on a legacy mixed list normalises it — the one such point."""
        tier_of = lookup(m1=MEDIUM, e1=EASY, e2=EASY)

        assert moved_within_level(["m1", "e1", "e2"], "e2", -1, tier_of) == [
            "e2",
            "e1",
            "m1",
        ]


# --------------------------------------------------------------------------
# The arrange screen shows the grouping it stores (item 4)
# --------------------------------------------------------------------------


class TestBookArrangeScreen_ShowsTheLevels:
    """One heading per non-empty level, in book order, with the numbering unbroken."""

    def test_the_page_carries_a_heading_for_each_level_present(self, panel) -> None:
        book_id, _ids = a_book_of(panel, "easy", "medium", "hard")

        shown = body(panel.arrange(book_id))

        assert "Easy level" in shown and "Medium level" in shown and "Hard level" in shown
        assert shown.index("Easy level") < shown.index("Medium level") < shown.index(
            "Hard level"
        ), shown

    def test_an_empty_level_gets_no_heading(self, panel) -> None:
        book_id, _ids = a_book_of(panel, "easy", "hard")

        shown = body(panel.arrange(book_id))

        assert "Medium level" not in shown, shown

    def test_the_rows_are_numbered_one_to_n_across_the_levels(self, panel) -> None:
        book_id, (e1, m1, h1) = a_book_of(panel, "easy", "medium", "hard")

        markup = panel.arrange(book_id).get_data(as_text=True)

        positions = [markup.index(pid) for pid in (e1, m1, h1)]
        assert positions == sorted(positions), "the page lists the book in level order"
        numbers = re.findall(r'item-order">(\d+)<', markup)
        assert numbers == ["1", "2", "3"], numbers

    def test_the_page_break_indicator_counts_the_whole_book_not_each_level(
        self, panel
    ) -> None:
        """Review cycle 1, F-001: the page numbers run on across the levels.

        The divider used to count off the loop variable, which this card's
        nesting restarted at every level heading — so this book showed "page 2"
        twice and never "page 3". The numbers now come from the printed book's
        page plan (CARD-140) rather than from any arithmetic on this page, and
        they are still the **book's**: four easy 10x10s pair into interior pages
        3 and 4, the medium level's divider takes 5, its first two rows pair on
        6 and its last row has 7 to itself. Nothing restarts, and no number
        appears twice.

        What each of those numbers means is
        ``tests/test_book_arrange_page_breaks.py``'s subject; what this test
        keeps is the nesting posture the review found: the labels are read in
        the order the page renders them, across the level headings.
        """
        book_id, _ids = a_book_of(
            panel, "easy", "easy", "easy", "easy", "medium", "medium", "medium"
        )

        markup = panel.arrange(book_id).get_data(as_text=True)

        assert re.findall(r'item-order">(\d+)<', markup) == list("1234567")
        numbers = re.findall(r'page-break-divider" data-page="(\d+)"', markup)
        assert numbers == ["2", "3", "4", "5", "6", "7"], numbers
        # ... and the medium level's own pages are numbered on from the easy
        # level's, inside the medium level: the number is the book's, not the
        # level's.
        medium = markup.index("Medium level")
        assert markup.index('data-page="6"') > medium, "page 6 sits inside the medium level"
        assert markup.index('data-page="4"') < medium, "page 4 is still the easy level's"

    def test_the_last_page_of_the_book_is_labelled_like_any_other(
        self, panel
    ) -> None:
        """A book of exactly three: every row sits under the page it prints on.

        The screen used to rule off every third puzzle and therefore showed this
        book no break at all. Since CARD-140 a break opens every page of the
        printed interior — the two easy 10x10s share page 3 behind the easy
        level's divider page, and the medium row has page 5 to itself behind its
        own — so the last row is labelled like the rest, and there is still no
        rule left dangling after it.
        """
        book_id, _ids = a_book_of(panel, "easy", "easy", "medium")

        markup = panel.arrange(book_id).get_data(as_text=True)

        assert re.findall(r'page-break-divider" data-page="(\d+)"', markup) == [
            "2",
            "3",
            "4",
            "5",
        ]
        last_row = markup.rindex('class="item-order"')
        assert "page-break-divider" not in markup[last_row:], markup[last_row:]
