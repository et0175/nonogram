"""CARD-191 — "Sort by size" on the Arrangement step (FR-041, INV-009, INV-012).

    AC-1  each level sorted ascending by (longest side, shortest side), easy
          still before medium, in both storage modes
          (TestArrangeSortBySize_SortsEachLevelByLongestThenShortest)
    AC-2  equal keys keep their current relative order
          (TestArrangeSortBySize_EqualSizesKeepTheirCurrentOrder)
    AC-3  a second sort writes nothing: order and ``updated_at`` unchanged, and
          the page says the order is unchanged
          (TestArrangeSortBySize_SecondPostChangesNothing)
    AC-4  the status is unchanged, as a move leaves it
          (TestArrangeSortBySize_KeepsTheStatusAsAMoveDoes)
    AC-5  a move after a sort acts on the sorted order
          (TestArrangeSortBySize_MovesStillWorkAfterASort)
    AC-6  the re-rendered page's ``data-page`` labels are the generator's plan
          for the new order (TestArrangeSortBySize_PageBreaksFollowTheSortedOrder)
    AC-7  a legacy mixed order comes back grouped and sorted, an unsized puzzle
          last in its level
          (TestArrangeSortBySize_GroupsALegacyOrderAndPutsUnsizedLast)
    AC-8  property over a seeded corpus: permutation, grouped, non-decreasing,
          stable, idempotent
          (PropertyTest_ArrangeSortBySize_GroupedStableAndIdempotent)
    AC-9  the page carries one confirmed "Sort by size" form; an empty book
          does not (TestArrangeSortBySize_ButtonIsOnThePage)

The shelf, the panel and the readable-text helpers are
``tests/test_book_level_order.py``'s, imported rather than copied. Every
expected order is written out by hand, or — in the property test — graded with
keys and level ranks the test computes from the sizes and tiers it chose
itself; nothing is re-derived by calling the function under test.
"""

from __future__ import annotations

import random
import re
import uuid

import pytest

from nonogram.admin.book_plan import (
    BUCKETS,
    TIERS,
    DistributionPlan,
    Split,
    bucket_of,
    sorted_by_size_within_level,
)
from nonogram.difficulty import Tier
from tests.test_book_level_order import (  # noqa: F401  (fixtures used by name)
    MODES,
    Shelf,
    _write_raw_order,
    admin_app,
    body,
    panel,
)

SORTED_FLASH = "Sorted each level by size: longest side, then shortest side."
UNCHANGED_FLASH = "Each level is already in size order; the order is unchanged."
NO_UNDO_PROMPT = (
    "Sort every level by size? Your own order inside each level is replaced. "
    "There is no undo."
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def sized(source, width: int, height: int, tier) -> str:
    """One stored, approved ``width`` x ``height`` puzzle carrying ``tier``.

    A fully filled rectangle is uniquely solvable, which the store insists
    on. ``source`` is a :class:`Shelf` or a :class:`Panel` — both carry a
    ``store`` and a ``_made`` counter.
    """
    source._made += 1
    puzzle_id = source.store.add_puzzle(
        grid=[[True] * width for _ in range(height)],
        clues_rows=[[width]] * height,
        clues_cols=[[height]] * width,
        width=width,
        height=height,
        theme="generic",
        difficulty_score=10,
        difficulty_tier=tier,
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=None,
        source_image=f"sized-{source._made}.png",
    )
    source.store.approve_puzzle(puzzle_id)
    return puzzle_id


def book_of(source, *specs):
    """A book holding one puzzle per ``(width, height, tier)``, stored in that order.

    The order is written verbatim after the add, so a test states the stored
    order it starts from rather than relying on where an add places a puzzle.
    """
    ids = [sized(source, w, h, tier) for w, h, tier in specs]
    book_id = source.book()
    source.books.add_puzzles_to_book(book_id, ids)
    assert source.books.reorder_puzzles(book_id, ids) is True
    return book_id, ids


def post_sort(panel, book_id):
    return panel.client.post(
        f"/book/{book_id}/arrange-puzzles", data={"action": "sort_by_size"}
    )


def row_pages(markup: str):
    """``[(puzzle_id, data-page or None), ...]`` for every row, in document order."""
    rows = []
    for chunk in markup.split('class="puzzle-list-item"')[1:]:
        page = re.match(r'(?: data-page="(\d+)")?', chunk).group(1)
        puzzle_id = re.search(r'id="position_([^"]+)"', chunk).group(1)
        rows.append((puzzle_id, None if page is None else int(page)))
    return rows


def sort_forms(markup: str):
    """Every ``<form>`` on the page that posts ``action=sort_by_size``."""
    return [
        form
        for form in re.findall(r"(?s)<form\b.*?</form>", markup)
        if re.search(r'name="action" value="sort_by_size"', form)
    ]


@pytest.fixture(params=MODES)
def shelf(request, tmp_path):
    return Shelf(request.param, tmp_path)


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestArrangeSortBySize_SortsEachLevelByLongestThenShortest:
    def _book(self, source):
        return book_of(
            source,
            (25, 25, "easy"),
            (15, 15, "easy"),
            (20, 15, "easy"),
            (30, 20, "easy"),
            (20, 20, "medium"),
            (10, 10, "medium"),
        )

    def test_the_store_sorts_each_level_in_both_modes(self, shelf) -> None:
        book_id, (e25, e15, e2015, e3020, m20, m10) = self._book(shelf)

        assert shelf.books.sort_puzzles_by_size(book_id) is True

        assert shelf.ids_of(book_id) == [e15, e2015, e25, e3020, m10, m20]

    def test_tiers_and_sizes_are_each_one_bulk_read(self, shelf, monkeypatch) -> None:
        book_id, _ = self._book(shelf)
        calls = []
        real = shelf.store.get_puzzles
        monkeypatch.setattr(
            shelf.store, "get_puzzles", lambda ids: calls.append(list(ids)) or real(ids)
        )

        assert shelf.books.sort_puzzles_by_size(book_id) is True

        assert len(calls) == 2, calls
        assert all(len(ids) == 6 for ids in calls)

    def test_the_route_sorts_and_says_so(self, panel) -> None:
        book_id, (e25, e15, e2015, e3020, m20, m10) = self._book(panel)

        shown = body(post_sort(panel, book_id))

        assert panel.ids_of(book_id) == [e15, e2015, e25, e3020, m10, m20]
        assert SORTED_FLASH in shown
        assert UNCHANGED_FLASH not in shown

    def test_the_pure_function_on_the_same_book(self) -> None:
        tiers = {"a": Tier.EASY, "b": Tier.EASY, "c": Tier.EASY, "d": Tier.EASY,
                 "m1": Tier.MEDIUM, "m2": Tier.MEDIUM}
        sizes = {"a": (25, 25), "b": (15, 15), "c": (20, 15), "d": (30, 20),
                 "m1": (20, 20), "m2": (10, 10)}
        result = sorted_by_size_within_level(
            ["a", "b", "c", "d", "m1", "m2"], tiers.get, sizes.get
        )
        assert result == ["b", "c", "a", "d", "m2", "m1"]

    def test_the_shortest_side_breaks_a_longest_side_tie(self) -> None:
        """25x25 against 25x10: same longest side, the narrower comes first."""
        tiers = {"wide": Tier.EASY, "narrow": Tier.EASY}
        sizes = {"wide": (25, 25), "narrow": (10, 25)}
        assert sorted_by_size_within_level(["wide", "narrow"], tiers.get, sizes.get) == [
            "narrow",
            "wide",
        ]


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestArrangeSortBySize_EqualSizesKeepTheirCurrentOrder:
    def test_equal_keys_keep_their_order_in_the_store(self, shelf) -> None:
        book_id, (a, b, c, d) = book_of(
            shelf,
            (20, 15, "easy"),
            (15, 20, "easy"),
            (20, 20, "easy"),
            (20, 15, "easy"),
        )

        assert shelf.books.sort_puzzles_by_size(book_id) is True

        assert shelf.ids_of(book_id) == [a, b, d, c]

    def test_equal_keys_keep_their_order_whatever_the_ids(self) -> None:
        """Ids chosen so that an order by id would read the other way round."""
        tiers = dict.fromkeys(["z", "y", "x", "w"], Tier.EASY)
        sizes = {"z": (20, 15), "y": (15, 20), "x": (20, 20), "w": (20, 15)}
        assert sorted_by_size_within_level(["z", "y", "x", "w"], tiers.get, sizes.get) == [
            "z",
            "y",
            "w",
            "x",
        ]


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestArrangeSortBySize_SecondPostChangesNothing:
    def test_a_second_sort_writes_nothing_in_both_modes(self, shelf) -> None:
        book_id, _ = book_of(shelf, (25, 25, "easy"), (10, 10, "easy"), (20, 20, "hard"))
        assert shelf.books.sort_puzzles_by_size(book_id) is True
        order = shelf.ids_of(book_id)
        stamp = shelf.books.get_book(book_id).updated_at

        assert shelf.books.sort_puzzles_by_size(book_id) is False

        assert shelf.ids_of(book_id) == order
        assert shelf.books.get_book(book_id).updated_at == stamp

    def test_the_second_post_says_the_order_is_unchanged(self, panel) -> None:
        book_id, (e25, e10, h20) = book_of(
            panel, (25, 25, "easy"), (10, 10, "easy"), (20, 20, "hard")
        )
        post_sort(panel, book_id)
        stamp = panel.books.get_book(book_id).updated_at

        shown = body(post_sort(panel, book_id))

        assert panel.ids_of(book_id) == [e10, e25, h20]
        assert panel.books.get_book(book_id).updated_at == stamp
        assert UNCHANGED_FLASH in shown
        assert SORTED_FLASH not in shown

    def test_an_unknown_book_is_refused(self, shelf) -> None:
        with pytest.raises(ValueError, match="Book not found"):
            shelf.books.sort_puzzles_by_size(str(uuid.uuid4()))


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------

#: The four easy puzzles, one per longest-side bucket, so a plan of one per
#: easy cell matches the selection exactly and the gate lets the book out.
STATUS_BOOK = ((25, 25, "easy"), (15, 15, "easy"), (20, 15, "easy"), (30, 20, "easy"))


def _matching_plan():
    cells = [[0, 0, 0] for _ in BUCKETS]
    for w, h, _tier in STATUS_BOOK:
        cells[BUCKETS.index(bucket_of(w, h))][TIERS.index(Tier.EASY)] += 1
    return DistributionPlan(count=len(STATUS_BOOK), split=Split(100, 0, 0), cells=cells)


class TestArrangeSortBySize_KeepsTheStatusAsAMoveDoes:
    @pytest.mark.parametrize("status", ["ready_for_pdf", "pdf_generated"])
    def test_the_sort_keeps_the_status(self, shelf, status) -> None:
        book_id, ids = book_of(shelf, *STATUS_BOOK)
        shelf.books.save_plan(book_id, _matching_plan())
        ladder = ["ready_for_pdf", "pdf_generated"]
        for step in ladder[: ladder.index(status) + 1]:
            assert shelf.books.set_book_status(book_id, step) is True

        assert shelf.books.sort_puzzles_by_size(book_id) is True

        assert shelf.ids_of(book_id) == [ids[1], ids[2], ids[0], ids[3]]
        assert shelf.books.get_book(book_id).status == status
        # The same verdict a move gets.
        assert shelf.books.move_puzzle_up(book_id, ids[0]) is True
        assert shelf.books.get_book(book_id).status == status


# --------------------------------------------------------------------------
# AC-5
# --------------------------------------------------------------------------


class TestArrangeSortBySize_MovesStillWorkAfterASort:
    def test_a_move_after_a_sort_acts_on_the_sorted_order(self, panel) -> None:
        book_id, (e25, e10, e15, m20) = book_of(
            panel, (25, 25, "easy"), (10, 10, "easy"), (15, 15, "easy"), (20, 20, "medium")
        )
        post_sort(panel, book_id)
        assert panel.ids_of(book_id) == [e10, e15, e25, m20]

        panel.move(book_id, e25, "up")

        assert panel.ids_of(book_id) == [e10, e25, e15, m20]


# --------------------------------------------------------------------------
# AC-6
# --------------------------------------------------------------------------


def _planned_pages(panel, book_id):
    """``{puzzle_id: interior page}`` asked of the generator for the stored order."""
    from nonogram.admin.book_pdf_generator import BookPDFGenerator, DividerPagePlan

    ids = panel.ids_of(book_id)
    records = panel.store.get_puzzles(ids)
    rows = [records[i] for i in ids]
    plan = BookPDFGenerator(panel.books.get_book(book_id)).section_plan(rows)
    pages, shared = {}, set()
    for entry in plan.pages:
        if isinstance(entry, DividerPagePlan):
            continue
        for number in entry.numbers:
            pages[plan.printed[number - 1]["id"]] = entry.page_number
        if len(entry.numbers) > 1:
            shared.update(plan.printed[n - 1]["id"] for n in entry.numbers)
    return pages, shared


class TestArrangeSortBySize_PageBreaksFollowTheSortedOrder:
    def test_every_row_shows_the_page_the_new_order_prints_it_on(self, panel) -> None:
        # Stored 25x25, 10x10, 30x20, 10x10: no two 10x10s are neighbours.
        # Sorted, they are, and the generator pairs them (asked below, not
        # assumed).
        book_id, (e25, e10a, e30, e10b) = book_of(
            panel, (25, 25, "easy"), (10, 10, "easy"), (30, 20, "easy"), (10, 10, "easy")
        )
        before, shared_before = _planned_pages(panel, book_id)
        assert not shared_before, "precondition: nothing pairs in the stored order"

        markup = post_sort(panel, book_id).get_data(as_text=True)

        after, shared_after = _planned_pages(panel, book_id)
        assert shared_after == {e10a, e10b}, "precondition: the sort makes a pair"
        assert after != before
        shown = row_pages(markup)
        assert [pid for pid, _ in shown] == [e10a, e10b, e25, e30]
        assert shown == [(pid, after[pid]) for pid in panel.ids_of(book_id)]
        assert "two puzzles" in markup


# --------------------------------------------------------------------------
# AC-7
# --------------------------------------------------------------------------


class TestArrangeSortBySize_GroupsALegacyOrderAndPutsUnsizedLast:
    def test_a_legacy_order_is_grouped_sorted_and_the_unsized_id_is_last(
        self, shelf
    ) -> None:
        m25 = sized(shelf, 25, 25, "medium")
        e20 = sized(shelf, 20, 20, "easy")
        h15 = sized(shelf, 15, 15, "hard")
        e10 = sized(shelf, 10, 10, "easy")
        m10 = sized(shelf, 10, 10, "medium")
        u25 = sized(shelf, 25, 25, None)
        u10 = sized(shelf, 10, 10, None)
        ghost = str(uuid.uuid4())  # no row: no size, no tier
        book_id = shelf.book()
        shelf.books.add_puzzles_to_book(book_id, [m25, e20, h15, e10, m10, u25, u10])
        _write_raw_order(shelf, book_id, [m25, e20, h15, u25, ghost, e10, m10, u10])

        assert shelf.books.sort_puzzles_by_size(book_id) is True

        assert shelf.ids_of(book_id) == [e10, e20, m10, m25, h15, u10, u25, ghost]

    def test_an_unsized_puzzle_goes_last_in_a_graded_level(self) -> None:
        tiers = {"a": Tier.EASY, "x": Tier.EASY, "b": Tier.EASY, "y": Tier.EASY,
                 "m": Tier.MEDIUM}
        sizes = {"a": (25, 25), "b": (10, 10), "m": (30, 30)}  # x, y unsized
        result = sorted_by_size_within_level(["x", "a", "y", "m", "b"], tiers.get, sizes.get)
        assert result == ["b", "a", "x", "y", "m"]

    def test_a_graded_record_without_a_size_goes_last_in_its_level(self, tmp_path) -> None:
        """Memory mode only: the DB schema makes width/height NOT NULL."""
        shelf = Shelf("memory", tmp_path)
        book_id, (e25, e_blank, e10) = book_of(
            shelf, (25, 25, "easy"), (15, 15, "easy"), (10, 10, "easy")
        )
        shelf.store.puzzles[e_blank]["width"] = None

        assert shelf.books.sort_puzzles_by_size(book_id) is True

        assert shelf.ids_of(book_id) == [e10, e25, e_blank]


# --------------------------------------------------------------------------
# AC-8
# --------------------------------------------------------------------------

#: Level ranks written out here, so the grouping is not graded with
#: ``book_plan.level_rank``.
RANK = {Tier.EASY: 0, Tier.MEDIUM: 1, Tier.HARD: 2, None: 3}
MIN_BOOKS = 400


def test_PropertyTest_ArrangeSortBySize_GroupedStableAndIdempotent() -> None:
    """Named as the AC refs it; a function, as CARD-143's property test is."""
    rng = random.Random(191)
    books = ties = unsized = ungraded = non_square = 0
    for _ in range(MIN_BOOKS):
        n = rng.randint(0, 14)
        ids = [f"p{i}" for i in range(n)]
        tiers = {pid: rng.choice([Tier.EASY, Tier.MEDIUM, Tier.HARD, None]) for pid in ids}
        sizes = {}
        for pid in ids:
            if rng.random() < 0.1:
                sizes[pid] = None
                continue
            # A narrow side range on some books, so equal keys really occur.
            low, high = (10, 30) if rng.random() < 0.5 else (14, 16)
            sizes[pid] = (rng.randint(low, high), rng.randint(low, high))
        rng.shuffle(ids)

        result = sorted_by_size_within_level(ids, tiers.get, sizes.get)
        books += 1

        def key(pid):
            # (unsized flag, longest, shortest), from the test's own sizes.
            size = sizes[pid]
            return (1, 0, 0) if size is None else (0, max(size), min(size))

        assert sorted(result) == sorted(ids), "not a permutation"
        ranks = [RANK[tiers[pid]] for pid in result]
        assert ranks == sorted(ranks), "levels mixed"
        position = {pid: i for i, pid in enumerate(ids)}
        for a, b in zip(result, result[1:]):
            if RANK[tiers[a]] != RANK[tiers[b]]:
                continue
            assert key(a) <= key(b), "not non-decreasing inside a level"
            if key(a) == key(b):
                ties += 1
                assert position[a] < position[b], "equal keys reordered"
        assert sorted_by_size_within_level(result, tiers.get, sizes.get) == result

        unsized += sum(1 for pid in ids if sizes[pid] is None)
        ungraded += sum(1 for pid in ids if tiers[pid] is None)
        non_square += sum(1 for pid in ids if sizes[pid] and sizes[pid][0] != sizes[pid][1])

    assert books >= MIN_BOOKS
    assert ties >= 50 and unsized >= 50 and ungraded >= 50 and non_square >= 500, (
        books, ties, unsized, ungraded, non_square,
    )


# --------------------------------------------------------------------------
# AC-9
# --------------------------------------------------------------------------


class TestArrangeSortBySize_ButtonIsOnThePage:
    def test_a_book_with_puzzles_carries_one_confirmed_sort_form(self, panel) -> None:
        book_id, _ = book_of(panel, (25, 25, "easy"), (10, 10, "easy"))

        markup = panel.arrange(book_id).get_data(as_text=True)

        forms = sort_forms(markup)
        assert len(forms) == 1
        form = forms[0]
        assert 'method="POST"' in form
        assert f"return confirm('{NO_UNDO_PROMPT}')" in form
        assert ">Sort by size</button>" in form
        assert 'title="Sort each level by longest side, then shortest side"' in form
        assert 'class="btn btn-sm btn-outline-secondary"' in form
        header = re.search(r'(?s)<div class="card-header[^"]*">(.*?)</div>', markup).group(1)
        assert form in header, "the button sits in the 'Puzzles in book' card header"
        assert "Puzzles in book" in header

    def test_an_empty_book_has_no_sort_button(self, panel) -> None:
        book_id = panel.book()

        markup = panel.arrange(book_id).get_data(as_text=True)

        assert sort_forms(markup) == []
        assert "Sort by size" not in markup
