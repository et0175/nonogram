"""CARD-143 — a puzzle's position in the arrange step can be typed (FR-036, INV-009).

    AC-1  typing 1 against the last puzzle of a level moves it to the front of
          that level and leaves every other level untouched
          (TestArrangePosition_TypedPositionMovesWithinTheLevel)
    AC-2  a position above the level's count, below 1, or not a number is
          refused with the valid range named, and the stored order is unchanged
          (TestArrangePosition_OutOfRangeIsRefusedNotClamped)
    AC-3  typing a puzzle's current position succeeds and changes nothing
          (TestArrangePosition_NoOpPositionIsAccepted)
    AC-4  for any book and any legal position, the result is a permutation of
          the same ids, still grouped by tier
          (PropertyTest_ArrangePosition_AlwaysAPermutationGroupedByTier)

What the feature is, and what it deliberately is not
----------------------------------------------------
A typed position is the **existing** move with its offset worked out:
``offset = target - current`` inside the level, handed to
:func:`~nonogram.admin.book_plan.moved_within_level` through
:meth:`~nonogram.admin.book_manager.BookManager.move_puzzle_within_level`. So
there is one ordering rule in the system, not two, and INV-009 is enforced by
the same function that enforces it for the up/down buttons. That function
**inserts**: the puzzle is lifted out and put back ``offset`` places away and
the puzzles between shift one place to close the gap, so a typed position does
exactly what clicking the button that many times does (the owner's ruling of
2026-09-30, CARD-143 fix 1 — it used to exchange the two positions, which
coincides with insertion only at the buttons' ±1). The expected orders in this
file are written out by hand accordingly — never re-derived by calling
``moved_within_level`` on the same input, which would prove only that it agrees
with itself.

Two numbers live on each row and they are not the same number: ``order`` is the
puzzle's place in the whole book (unchanged, CARD-126) and the position box is
its place in its own **level**. The owner sorts inside a difficulty group, and a
book-wide ordinal typed into that box would ask for precisely the cross-level
move INV-009 forbids, so AC-1 checks the box carries the level's numbering and
AC-2 checks that a position another level would have is refused rather than
honoured.

The evidence class is the Flask test client, as it is for CARD-126's own ACs in
``tests/test_book_level_order.py``: these are user-facing criteria on a
server-rendered screen and this project has no browser harness, so each test
drives the real POST route with real form fields and reads the real HTML that
came back. The shelf, the panel and the readable-text helpers are that file's —
imported rather than copied, so the two cards' tests cannot drift into
describing two different screens. The store-level method is asserted in both
storage modes beside the route, because the rule is the aggregate's and not a
backend's.

AC-4's corpus is built by hand from a seeded ``random.Random`` (no
``hypothesis``, per CLAUDE.md) and asserts its own size and coverage: how many
books it really checked, and that it really exercised moves in both directions
and the no-op. The tier ranking it grades "still grouped by tier" with is a
three-entry dict written out in this file, and the tiers it grades are the ones
the test itself asked for when it made each puzzle — so nothing in the property
is measured with the code it is measuring.
"""

from __future__ import annotations

import random
import re

import pytest

from nonogram.admin.book_plan import CROSS_LEVEL_REFUSAL, LevelBoundary
from tests.test_book_level_order import (  # noqa: F401  (fixtures used by name)
    MODES,
    Shelf,
    a_book_of,
    admin_app,
    body,
    panel,
    text_of,
)

#: The levels in book order, ranked here by hand. The property test grades
#: "still grouped by tier" with this and nothing else: importing
#: ``book_plan.level_rank`` would grade the grouping with the module that makes
#: it.
RANK = {"easy": 0, "medium": 1, "hard": 2}


def type_position(panel, book_id, puzzle_id, position):
    """POST one row's position box, exactly as the page submits it."""
    return panel.client.post(
        f"/book/{book_id}/arrange-puzzles",
        data={
            "action": "set_position",
            "puzzle_id": puzzle_id,
            "position": str(position),
        },
        follow_redirects=True,
    )


def box_of(markup: str, puzzle_id: str) -> str:
    """The value the position box carries for ``puzzle_id`` on the rendered page."""
    found = re.search(rf'id="position_{puzzle_id}"[^>]*value="([^"]*)"', markup)
    assert found, f"no position box for {puzzle_id} on the page: {markup}"
    return found.group(1)


def boxes_of(markup: str) -> list[tuple[str, str]]:
    """Every position box on the page, in document order: ``(puzzle_id, value)``."""
    return [
        (found.group(1), found.group(2))
        for found in re.finditer(
            r'id="position_([^"]+)"[^>]*value="([^"]*)"', markup
        )
    ]


# --------------------------------------------------------------------------
# AC-1 — a typed position is a move inside the level, and it sticks
# --------------------------------------------------------------------------


class TestArrangePosition_TypedPositionMovesWithinTheLevel:
    """E1, E2, E3, M1, M2: typing 1 against E3 puts it first among the easy ones."""

    def test_typing_one_against_the_last_of_a_level_moves_it_to_the_front(
        self, panel
    ) -> None:
        book_id, (e1, e2, e3, m1, m2) = a_book_of(
            panel, "easy", "easy", "easy", "medium", "medium"
        )
        assert panel.ids_of(book_id) == [e1, e2, e3, m1, m2]

        shown = body(type_position(panel, book_id, e3, 1))

        # The insertion `moved_within_level` makes, written out rather than
        # re-derived: E3 takes the front and E1, E2 each shift down one.
        assert panel.ids_of(book_id) == [e3, e1, e2, m1, m2], (
            "the typed position must put E3 first among the easy puzzles and "
            "shift the others down, not exchange it with E1"
        )
        assert "Moved puzzle to 1 of 3 in the Easy level" in shown, shown

    def test_the_other_levels_are_left_exactly_as_they_were(self, panel) -> None:
        """The medium level is not renumbered, reordered or otherwise touched."""
        book_id, (e1, e2, e3, m1, m2, m3) = a_book_of(
            panel, "easy", "easy", "easy", "medium", "medium", "medium"
        )

        type_position(panel, book_id, e3, 1)

        assert panel.ids_of(book_id)[3:] == [m1, m2, m3], (
            "a move inside the easy level must not disturb the medium one"
        )
        markup = panel.arrange(book_id).get_data(as_text=True)
        assert [box_of(markup, pid) for pid in (m1, m2, m3)] == ["1", "2", "3"]

    def test_a_typed_position_inside_a_level_moves_to_that_position(
        self, panel
    ) -> None:
        """Not only the ends: 2 against the fifth easy puzzle inserts it second.

        E5 goes to position 2 and E2, E3, E4 each shift down one place; E2 is
        not sent to the back in exchange for the place E5 took.
        """
        book_id, ids = a_book_of(panel, *(["easy"] * 5))
        e1, e2, e3, e4, e5 = ids

        type_position(panel, book_id, e5, 2)

        assert panel.ids_of(book_id) == [e1, e5, e2, e3, e4]
        markup = panel.arrange(book_id).get_data(as_text=True)
        assert box_of(markup, e5) == "2"

    def test_the_box_numbers_the_level_and_not_the_book(self, panel) -> None:
        """The card's item 2, on screen: M1 is 4th in the book and 1st in its level."""
        book_id, (_e1, _e2, _e3, m1, m2) = a_book_of(
            panel, "easy", "easy", "easy", "medium", "medium"
        )

        markup = panel.arrange(book_id).get_data(as_text=True)

        assert [value for _pid, value in boxes_of(markup)] == ["1", "2", "3", "1", "2"], (
            "each level is numbered from 1; the book-wide ordinal stays in "
            "`item-order` where CARD-126 put it"
        )
        assert box_of(markup, m1) == "1"
        assert box_of(markup, m2) == "2"
        assert '<div class="item-order">4</div>' in markup, (
            "the book-wide number is still shown, and is still 4 for M1"
        )
        assert "Position in Medium" in markup, (
            "the label must say which level the position counts within"
        )

    def test_the_typed_position_is_offered_on_every_row(self, panel) -> None:
        """Every puzzle has a box, including the ones whose buttons are disabled."""
        book_id, ids = a_book_of(panel, "easy", "easy", "medium", "hard")

        markup = panel.arrange(book_id).get_data(as_text=True)

        assert [pid for pid, _value in boxes_of(markup)] == list(ids)
        assert markup.count('name="action" value="set_position"') == 4
        assert markup.count("disabled") == 6, (
            "G-2: the up/down controls are untouched — one disabled control at "
            "each end of each level, so a level of one puzzle has two"
        )

    @pytest.mark.parametrize("mode", MODES)
    def test_the_store_moves_it_by_the_offset_in_either_storage_mode(
        self, mode, tmp_path
    ) -> None:
        """The offset move is the store's, so the page can be bypassed."""
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, e3, m1) = a_book_of(shelf, "easy", "easy", "easy", "medium")

        assert shelf.books.move_puzzle_within_level(book_id, e3, -2) is True

        assert shelf.ids_of(book_id) == [e3, e1, e2, m1]

    @pytest.mark.parametrize("mode", MODES)
    def test_the_store_still_refuses_an_offset_that_leaves_the_level(
        self, mode, tmp_path
    ) -> None:
        """G-1: INV-009 is enforced where it always was, for any offset.

        The route never sends one of these — it works its offset out inside the
        level — but the store is the gate, and an offset that crosses a level
        boundary is refused there rather than trusted to the caller.
        """
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, m1, m2) = a_book_of(shelf, "easy", "easy", "medium", "medium")

        with pytest.raises(LevelBoundary) as refusal:
            shelf.books.move_puzzle_within_level(book_id, m1, -2)

        assert str(refusal.value) == CROSS_LEVEL_REFUSAL
        assert shelf.ids_of(book_id) == [e1, e2, m1, m2], "nothing is written"


# --------------------------------------------------------------------------
# The rule itself: a typed position INSERTS, it does not exchange
# (the owner's ruling of 2026-09-30 — CARD-143 fix 1)
# --------------------------------------------------------------------------


class TestArrangePosition_ATypedPositionInsertsRatherThanExchanges:
    """Typing a position does what clicking the button that many times does.

    Why the card's own ACs could not catch this, and why every test here uses
    an offset of more than one place
    ---------------------------------------------------------------------
    Two different rules answer "move this puzzle ``offset`` places": exchange
    the puzzle with whatever sits ``offset`` places away, or lift the puzzle out
    and insert it there, shifting the puzzles in between one place to close the
    gap. **At ±1 the two are the same operation** — there is exactly one puzzle
    between the two positions, and it is the one being exchanged with — which is
    why the up/down buttons and all of CARD-126's tests read identically under
    either rule and cannot discriminate them.

    They diverge from ±2 on, and they diverge in the direction that matters:
    composing ``n`` one-step moves *is* an insertion, while one ``n``-step
    exchange is not. AC-1 ("typing 1 against the last puzzle of a level moves it
    to the front of that level") is satisfied by both, because under either rule
    the moved puzzle lands where it was told to — the difference is what happens
    to everything else. Under exchange, typing 1 against the last puzzle of a
    50-puzzle level flings the puzzle that was **first** to position 50, and
    nothing in the card's ACs looks there. So each test below asserts the whole
    level, at an offset beyond ±1, and the first one asserts the equivalence
    with the buttons directly rather than a hand-written order.
    """

    def test_a_typed_position_agrees_with_clicking_up_that_many_times(
        self, panel
    ) -> None:
        """Four one-step ups and one typed 1 must leave the same five puzzles.

        The two controls are one operation asked for two ways (G-2, the card's
        G-1 in spirit); an exchange makes them disagree from the second step on.
        """
        clicked_id, clicked = a_book_of(panel, *(["easy"] * 5))
        for _ in range(4):
            panel.move(clicked_id, clicked[4], "up")
        by_button = panel.ids_of(clicked_id)

        typed_id, typed = a_book_of(panel, *(["easy"] * 5))
        type_position(panel, typed_id, typed[4], 1)
        by_box = panel.ids_of(typed_id)

        # Compared by place in the original order, so the two books' different
        # ids line up. Both are written out, so a rule that changed *both*
        # controls together could not pass this by agreeing with itself.
        assert [clicked.index(pid) for pid in by_button] == [4, 0, 1, 2, 3], (
            f"the buttons themselves shift E1..E4 down: {by_button}"
        )
        assert [typed.index(pid) for pid in by_box] == [4, 0, 1, 2, 3], (
            "typing 1 must do what clicking up four times does; an exchange "
            f"would have given [4, 1, 2, 3, 0]: {by_box}"
        )

    def test_typing_one_against_the_last_shifts_the_level_and_flings_nobody(
        self, panel
    ) -> None:
        """The owner's case, spelled out: E1..E5, type 1 on E5 -> E5, E1..E4.

        Written by hand, and the order an exchange would have produced is named
        so the two rules cannot be confused by a later reader.
        """
        book_id, (e1, e2, e3, e4, e5) = a_book_of(panel, *(["easy"] * 5))

        type_position(panel, book_id, e5, 1)

        assert panel.ids_of(book_id) == [e5, e1, e2, e3, e4], (
            "an insertion shifts E1..E4 down one place; an exchange would have "
            "stored E5, E2, E3, E4, E1 and flung E1 to the back of the level"
        )
        assert panel.ids_of(book_id) != [e5, e2, e3, e4, e1], (
            "the puzzle that was first must not be flung to the end"
        )

    def test_a_typed_position_agrees_with_clicking_down_that_many_times(
        self, panel
    ) -> None:
        """The other direction, past a level boundary it must not cross.

        E1..E4 then M1: typing 4 against E1 inserts it last among the easy
        puzzles — E2, E3, E4 shift up one — and the medium level is untouched.
        An exchange would have stored E4, E2, E3, E1, M1.
        """
        book_id, (e1, e2, e3, e4, m1) = a_book_of(
            panel, "easy", "easy", "easy", "easy", "medium"
        )

        type_position(panel, book_id, e1, 4)

        assert panel.ids_of(book_id) == [e2, e3, e4, e1, m1], (
            "an insertion down shifts E2..E4 up one place, and M1 stays put"
        )

    @pytest.mark.parametrize("mode", MODES)
    def test_the_store_inserts_for_any_offset_in_either_storage_mode(
        self, mode, tmp_path
    ) -> None:
        """One ordering rule: the store inserts however the move was asked for.

        The page can be bypassed, so the rule is asserted at the aggregate too
        — at an offset of three, where exchange and insertion differ.
        """
        shelf = Shelf(mode, tmp_path)
        book_id, (e1, e2, e3, e4, m1) = a_book_of(
            shelf, "easy", "easy", "easy", "easy", "medium"
        )

        assert shelf.books.move_puzzle_within_level(book_id, e4, -3) is True

        assert shelf.ids_of(book_id) == [e4, e1, e2, e3, m1], (
            "an exchange would have stored E4, E2, E3, E1, M1"
        )

    @pytest.mark.parametrize("mode", MODES)
    def test_inserting_over_three_places_still_cannot_leave_the_level(
        self, mode, tmp_path
    ) -> None:
        """INV-009 is enforced by the same function, and by the same guard.

        A level is a contiguous block of the grouped order, so testing the id
        now sitting at the **destination** is exactly "the insertion stays
        inside my level" — the guard the exchange used, unchanged. E1, E2 then
        M1, M2, M3: an offset of +3 from E1 lands on M2, and is refused with
        nothing written.
        """
        shelf = Shelf(mode, tmp_path)
        book_id, ids = a_book_of(shelf, "easy", "easy", "medium", "medium", "medium")

        with pytest.raises(LevelBoundary) as refusal:
            shelf.books.move_puzzle_within_level(book_id, ids[0], +3)

        assert str(refusal.value) == CROSS_LEVEL_REFUSAL
        assert shelf.ids_of(book_id) == list(ids), "nothing is written"


# --------------------------------------------------------------------------
# AC-2 — an impossible position is refused, with the range, and nothing moves
# --------------------------------------------------------------------------


class TestArrangePosition_OutOfRangeIsRefusedNotClamped:
    """A position the level does not have is refused; it is never rounded into range."""

    @pytest.mark.parametrize(
        "typed",
        ["4", "9", "0", "-1", "abc", "", "2.5", "one", "1e1", " "],
    )
    def test_it_is_refused_with_the_range_named_and_nothing_moves(
        self, panel, typed
    ) -> None:
        book_id, (e1, e2, e3, m1) = a_book_of(panel, "easy", "easy", "easy", "medium")

        shown = body(type_position(panel, book_id, e1, typed))

        assert panel.ids_of(book_id) == [e1, e2, e3, m1], (
            f"the order must be untouched after {typed!r}"
        )
        assert "Position not changed" in shown, shown
        assert "from 1 to 3" in shown, (
            f"the refusal must name the valid range; the page said: {shown}"
        )
        assert "Moved puzzle to" not in shown, (
            "a move that did not happen must not be reported as one"
        )

    def test_a_position_past_the_end_is_not_clamped_to_the_last_one(
        self, panel
    ) -> None:
        """The whole point of item 3: 4 in a level of 3 is a refusal, not a 3."""
        book_id, (e1, e2, e3) = a_book_of(panel, "easy", "easy", "easy")

        body(type_position(panel, book_id, e1, 4))

        assert panel.ids_of(book_id) == [e1, e2, e3], (
            "clamping 4 to 3 would have moved E1 to the end of its level"
        )

    def test_a_position_below_one_is_not_clamped_to_the_first_one(
        self, panel
    ) -> None:
        book_id, (e1, e2, e3) = a_book_of(panel, "easy", "easy", "easy")

        body(type_position(panel, book_id, e3, 0))

        assert panel.ids_of(book_id) == [e1, e2, e3], (
            "clamping 0 to 1 would have moved E3 to the front of its level"
        )

    def test_a_position_another_level_has_is_refused_by_this_levels_count(
        self, panel
    ) -> None:
        """INV-009 is never reached, because the range is the level's own.

        E1, E2 then M1..M4: position 4 exists in the book and in the medium
        level, and is not a position the easy level has. Typing it against E1 is
        refused by the easy level's count — the route never works out an offset
        that would carry E1 into the medium level (G-1).
        """
        book_id, (e1, e2, m1, m2, m3, m4) = a_book_of(
            panel, "easy", "easy", "medium", "medium", "medium", "medium"
        )

        shown = body(type_position(panel, book_id, e1, 4))

        assert panel.ids_of(book_id) == [e1, e2, m1, m2, m3, m4]
        assert "no position 4 in the Easy level" in shown, shown
        assert "from 1 to 2" in shown, shown

    def test_the_refusal_marks_the_box_it_came_from_and_reads_as_text(
        self, panel
    ) -> None:
        """FormField: the control the refusal named, and only that one, is marked.

        The message is prose in a page-local alert the box points at, so the
        refusal does not rest on a red border alone.
        """
        book_id, (e1, _e2, _e3) = a_book_of(panel, "easy", "easy", "easy")

        markup = type_position(panel, book_id, e1, 7).get_data(as_text=True)

        assert markup.count("is-invalid") == 1, (
            "only the box the refusal named is marked invalid"
        )
        assert re.search(
            rf'id="position_{e1}"[^>]*is-invalid|is-invalid[^>]*id="position_{e1}"',
            markup,
        ), f"the mark is on another row's box: {markup}"
        assert markup.count('aria-invalid="true"') == 1
        assert markup.count('aria-describedby="position-error"') == 1
        assert 'id="position-error"' in markup, (
            "the description the box points at must exist on the page"
        )
        assert "There is no position 7 in the Easy level" in text_of(markup)

    def test_the_refused_box_keeps_what_was_typed_for_correcting(
        self, panel
    ) -> None:
        """FormField: a refusal re-renders the owner's entry, not the stored one.

        Only that one box: every other row still shows where its puzzle is.
        """
        book_id, (e1, e2, e3) = a_book_of(panel, "easy", "easy", "easy")

        markup = type_position(panel, book_id, e2, 77).get_data(as_text=True)

        assert box_of(markup, e2) == "77", (
            "the typo must still be in the box, to correct rather than retype"
        )
        assert [box_of(markup, pid) for pid in (e1, e3)] == ["1", "3"], (
            "the other rows still show where their puzzles are"
        )

    def test_a_clean_page_carries_no_refusal(self, panel) -> None:
        book_id, _ids = a_book_of(panel, "easy", "easy")

        markup = panel.arrange(book_id).get_data(as_text=True)

        assert "is-invalid" not in markup
        assert 'id="position-error"' not in markup

    def test_a_puzzle_this_book_does_not_hold_is_reported_not_moved(
        self, panel
    ) -> None:
        book_id, (e1, e2) = a_book_of(panel, "easy", "easy")
        stranger = panel.puzzle("easy")

        shown = body(type_position(panel, book_id, stranger, 1))

        assert panel.ids_of(book_id) == [e1, e2]
        assert "Book or puzzle not found" in shown, shown

    @pytest.mark.parametrize("mode", MODES)
    def test_a_zero_offset_is_a_no_op_the_route_never_sends(
        self, mode, tmp_path
    ) -> None:
        """The route answers a no-op itself rather than asking for a move of 0."""
        shelf = Shelf(mode, tmp_path)
        book_id, ids = a_book_of(shelf, "easy", "easy", "easy")

        before = shelf.ids_of(book_id)
        assert shelf.books.move_puzzle_within_level(book_id, ids[0], 0) is True, (
            "a zero offset is a legal no-op at the store, and the route does "
            "not even send it"
        )
        assert shelf.ids_of(book_id) == before


# --------------------------------------------------------------------------
# AC-3 — the position it already has is an answer, not a mistake
# --------------------------------------------------------------------------


class TestArrangePosition_NoOpPositionIsAccepted:
    """Typing a puzzle's current position succeeds and leaves the order alone."""

    def test_the_current_position_is_accepted_and_changes_nothing(
        self, panel
    ) -> None:
        book_id, (e1, e2, e3, m1) = a_book_of(panel, "easy", "easy", "easy", "medium")

        shown = body(type_position(panel, book_id, e2, 2))

        assert panel.ids_of(book_id) == [e1, e2, e3, m1], "nothing moved"
        assert "already 2 of 3 in the Easy level" in shown, shown
        assert "Position not changed" not in shown, (
            f"the position it already has is not a refusal: {shown}"
        )
        assert "is-invalid" not in type_position(
            panel, book_id, e2, 2
        ).get_data(as_text=True)

    def test_the_first_position_of_a_level_is_a_no_op_for_its_first_puzzle(
        self, panel
    ) -> None:
        """The level's own 1, not the book's: M1 typing 1 is a no-op."""
        book_id, (e1, e2, m1, m2) = a_book_of(panel, "easy", "easy", "medium", "medium")

        shown = body(type_position(panel, book_id, m1, 1))

        assert panel.ids_of(book_id) == [e1, e2, m1, m2]
        assert "already 1 of 2 in the Medium level" in shown, shown

    def test_the_only_puzzle_of_a_level_can_only_be_where_it_is(self, panel) -> None:
        book_id, (e1, h1) = a_book_of(panel, "easy", "hard")

        assert "already 1 of 1 in the Hard level" in body(
            type_position(panel, book_id, h1, 1)
        )
        assert "from 1 to 1" in body(type_position(panel, book_id, h1, 2))
        assert panel.ids_of(book_id) == [e1, h1]


# --------------------------------------------------------------------------
# AC-4 — the property: whatever is typed, the book is still the same book
# --------------------------------------------------------------------------

#: The corpus draws :data:`CORPUS_ATTEMPTS` books and **checks** the ones that
#: have a position to type at all: a book whose every level holds one puzzle has
#: no position but the one it is in, so it is drawn, skipped and not counted.
#: Every floor below is a measured figure with a margin, not a wish — the seeded
#: draw really checks 45 books of the 48 it makes, so a floor of 40 is a floor
#: that fires if the corpus ever shrinks toward it rather than one no corpus
#: could miss (the defect CARD-149 shipped: a corpus grown by
#: ``while len(cases) < CONST`` cannot fail its own size assertion).
CORPUS_BOOKS = 40
CORPUS_ATTEMPTS = 48

#: Moves up, moves down and no-ops must each appear this often, or the corpus
#: has stopped exercising the offset the route works out. Measured: 11 up,
#: 11 down, 23 no-ops.
CORPUS_MIN_OF_EACH_MOVE = 8

#: Books whose move had another level to leave alone — the half of the property
#: INV-009 is about. Measured: 43.
CORPUS_MIN_MULTI_LEVEL = 30


def corpus_books(seed: int = 143) -> list[list[str]]:
    """Seeded tier mixes: one list of tier names per book, in submission order."""
    rng = random.Random(seed)
    tiers = ("easy", "medium", "hard")
    books = []
    for _ in range(CORPUS_ATTEMPTS):
        size = rng.randint(2, 7)
        books.append([rng.choice(tiers) for _ in range(size)])
    return books


def levels_of(ids, tier_by_id) -> list[tuple[str, list[str]]]:
    """``ids`` cut into levels, by this file's own ranking, in book order."""
    groups: list[tuple[str, list[str]]] = []
    for puzzle_id in ids:
        tier = tier_by_id[puzzle_id]
        if not groups or groups[-1][0] != tier:
            groups.append((tier, []))
        groups[-1][1].append(puzzle_id)
    return groups


def test_PropertyTest_ArrangePosition_AlwaysAPermutationGroupedByTier(panel) -> None:
    """Over a seeded corpus, a typed position never breaks the book's order.

    Whatever legal position is typed against whichever puzzle, the stored order
    afterwards is (a) the same ids, no more and no fewer, (b) still grouped
    easy, then medium, then hard, (c) holding the moved puzzle at the position
    that was typed — counted within its level — and (d) unchanged in every
    other level. The rendered page is read too, so the numbering on screen is
    the numbering that was stored.

    Nothing here asks ``book_plan`` what the answer is: the tiers are the ones
    this test asked for when it made each puzzle, the grouping is graded with
    :data:`RANK`, and the position is counted off the result.
    """
    checked = 0
    moved_up = 0
    moved_down = 0
    no_ops = 0
    multi_level = 0
    rng = random.Random(1430)

    for mix in corpus_books():
        ids = [panel.puzzle(tier) for tier in mix]
        tier_by_id = dict(zip(ids, mix))
        book_id = panel.book()
        assert panel.books.add_puzzles_to_book(book_id, ids)

        before = panel.ids_of(book_id)
        groups_before = levels_of(before, tier_by_id)
        movable = [(tier, members) for tier, members in groups_before if len(members) > 1]
        if not movable:
            # No level of this book has a position other than the one its single
            # puzzle already occupies; there is nothing to type.
            continue

        tier, members = movable[rng.randrange(len(movable))]
        puzzle_id = members[rng.randrange(len(members))]
        current = members.index(puzzle_id) + 1
        target = rng.randint(1, len(members))

        markup = type_position(panel, book_id, puzzle_id, target).get_data(as_text=True)
        after = panel.ids_of(book_id)

        assert "Position not changed" not in text_of(markup), (
            f"a legal position was refused: {target} of {len(members)} in {tier}"
        )
        assert sorted(after) == sorted(before), (
            f"the book's membership changed: {before} -> {after}"
        )
        ranks = [RANK[tier_by_id[puzzle]] for puzzle in after]
        assert ranks == sorted(ranks), (
            f"the order is no longer grouped by tier: {ranks} for {mix}"
        )

        groups_after = dict(levels_of(after, tier_by_id))
        assert [name for name, _members in levels_of(after, tier_by_id)] == [
            name for name, _members in groups_before
        ], "the levels themselves must keep their order and their membership"
        assert groups_after[tier].index(puzzle_id) + 1 == target, (
            f"the puzzle is not at the typed position {target}: "
            f"{groups_after[tier]}"
        )
        #: CARD-143 fix 2: the moved level's OTHER members keep their relative
        #: order. That is the owner's insertion rule stated as a property — an
        #: exchange would reorder them (typing 1 against the last of E1..E5
        #: would give E5, E2, E3, E4, E1) while leaving membership, grouping,
        #: the landing position and every other level intact, so without this
        #: clause the whole corpus cannot tell the two rules apart.
        assert [p for p in groups_after[tier] if p != puzzle_id] == [
            p for p in members if p != puzzle_id
        ], (
            f"the rest of the {tier} level was reordered by inserting "
            f"{puzzle_id} at {target}: {members} -> {groups_after[tier]}"
        )
        for name, members_before in groups_before:
            if name != tier:
                assert groups_after[name] == members_before, (
                    f"the {name} level was disturbed by a move in {tier}"
                )

        shown = dict(boxes_of(markup))
        for _name, members_after in levels_of(after, tier_by_id):
            for index, member in enumerate(members_after, start=1):
                assert shown[member] == str(index), (
                    f"the page numbers {member} {shown[member]} where the "
                    f"stored order puts it {index}"
                )

        checked += 1
        if len(groups_before) > 1:
            multi_level += 1
        if target < current:
            moved_up += 1
        elif target > current:
            moved_down += 1
        else:
            no_ops += 1

    assert checked >= CORPUS_BOOKS >= 24, f"the corpus shrank to {checked} books"
    assert multi_level >= CORPUS_MIN_MULTI_LEVEL >= 12, (
        f"only {multi_level} books had another level to leave alone"
    )
    assert moved_up >= CORPUS_MIN_OF_EACH_MOVE >= 5, f"only {moved_up} moves up"
    assert moved_down >= CORPUS_MIN_OF_EACH_MOVE >= 5, f"only {moved_down} moves down"
    assert no_ops >= CORPUS_MIN_OF_EACH_MOVE >= 5, f"only {no_ops} no-ops"
