"""CARD-132 — /books against the plan: actual vs planned, per tier, exact hints.

    AC-230  TestBooksList_ShowsActualVsPlannedCount
    AC-231  TestBooksList_ShowsPerTierActualVsPlan
    AC-232  TestBooksList_HintsShortBucket
    AC-233  TestBooksList_NoHintWhenOnPlan
    AC-234  TestBooksList_SortsByCompleteness
    AC-235  TestBooksList_BookWithoutPlanShowsCountOnly

and the cross-checks the card's two open questions and its guardrails need:

    CK-1    TestBooksList_HintsOverBucket            (one hint list, both ways)
    CK-2    TestBooksList_PlanlessBookSortsLast      (the recorded decision)
    CK-3    TestBooksList_SortsBackToNewestFirst     (the order this list had)
    CK-4    PropertyTest_BooksList_HintsAreEveryOffPlanCellExactly  (G-2, G-3)
    CK-5    TestBooksList_OverPlanBookTiesWithOnPlanBook  (the clamped ratio)
    CK-6    TestBooksList_SortableHeadsAnnounceTheirOrder  (the aria-sort pair)
    CK-7    TestBooksList_PlanBarSaysWhichFillItIs        (partial vs complete)

The evidence class is the Flask test client: these are user-facing criteria on
a server-rendered page and this project has no browser harness, so every test
GETs the real ``/books`` route and reads the real HTML it rendered.

Every scenario is a **literal matrix** — the numbers the criteria name are in
this file, never re-derived through ``prefill`` or ``planned_cells``. CK-4 goes
further and buckets its puzzles by its own copy of the longest-side bounds, so
the hints it checks are not the ones ``bucket_of`` would agree with by
construction: the two implementations have to meet.

Storage mode: in memory. The route reads a stored plan and a stored record per
member, and both storage modes answer those reads through the same
``BookManager``/``PuzzleReviewService`` API (``test_book_ready_gate`` pins that
equivalence for the plan and the selection in both modes). Nothing here needs a
database, so nothing here can skip for want of one.
"""

from __future__ import annotations

import html as html_module
import random
import re
import uuid

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_plan import BUCKETS, TIERS, DistributionPlan, Split

E, M, H = TIERS

#: The longest-side buckets as this test spells them — label and inclusive
#: bounds — written out rather than read from ``book_plan``. CK-4 buckets its
#: puzzles with these, so a disagreement between them and ``bucket_of`` shows
#: up as a hint the page does not carry (G-2: there is one bucketing function,
#: and this is the second opinion that proves the page uses it).
BUCKET_BOUNDS = (
    ("<=15", 10, 15),
    ("16-20", 16, 20),
    ("21-25", 21, 25),
    ("26-30", 26, 30),
)


def bucket_label_of(width: int, height: int) -> str:
    """The bucket of a ``width`` x ``height`` puzzle, by longest side alone."""
    longest = max(width, height)
    for label, low, high in BUCKET_BOUNDS:
        if low <= longest <= high:
            return label
    raise AssertionError(f"{width}x{height} is in no bucket")


# --------------------------------------------------------------------------
# The plans and selections the criteria are stated against
# --------------------------------------------------------------------------

#: A plan of 150 at 40/40/20, whose per-tier columns are 60 / 60 / 30 — the
#: plan AC-230 and AC-231 name. Rows in BUCKETS order, columns in TIERS order.
PLAN_150_CELLS = (
    (20, 7, 0),    # <=15
    (30, 27, 6),   # 16-20
    (10, 20, 12),  # 21-25
    (0, 6, 12),    # 26-30
)
PLAN_150 = DistributionPlan(count=150, split=Split(40, 40, 20), cells=PLAN_150_CELLS)

#: AC-230 / AC-231: 132 puzzles, 50 easy, 60 medium and 22 hard.
SELECTION_132 = (
    (20, 5, 0),
    (20, 25, 5),
    (10, 20, 12),
    (0, 10, 5),
)

#: AC-232: PLAN_150 met everywhere but 26-30 x hard, which holds 5 of its 12.
SELECTION_SHORT_BY_7 = (
    (20, 7, 0),
    (30, 27, 6),
    (10, 20, 12),
    (0, 6, 5),
)

#: CK-1: the same plan with one puzzle too many in that cell.
SELECTION_OVER_BY_1 = (
    (20, 7, 0),
    (30, 27, 6),
    (10, 20, 12),
    (0, 6, 13),
)

#: CK-5 (review cycle 1, F-005): the same plan with ten puzzles too many in
#: that cell — 160 puzzles against a plan of 150.
SELECTION_OVER_BY_10 = (
    (20, 7, 0),
    (30, 27, 6),
    (10, 20, 12),
    (0, 6, 22),
)

#: AC-234's first book: a plan of 100, and 20 puzzles against it.
PLAN_100 = DistributionPlan(
    count=100,
    split=Split(45, 40, 15),
    cells=((15, 10, 0), (20, 10, 5), (10, 15, 5), (0, 5, 5)),
)
SELECTION_20 = (
    (5, 3, 0),
    (5, 3, 1),
    (2, 1, 0),
    (0, 0, 0),
)

#: AC-235: a book made before distribution plans existed, holding 40 puzzles.
SELECTION_40 = (
    (10, 5, 0),
    (10, 5, 2),
    (3, 3, 1),
    (0, 1, 0),
)


def cells_of(matrix) -> dict:
    """``{(bucket, tier): count}`` from a 4 x 3 matrix in BUCKETS order."""
    return {
        (bucket, tier): matrix[b][t]
        for b, bucket in enumerate(BUCKETS)
        for t, tier in enumerate(TIERS)
    }


def total_of(matrix) -> int:
    return sum(sum(row) for row in matrix)


# --------------------------------------------------------------------------
# The panel, its store, and the books list read back out of it
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


class Shelf:
    """The panel, the store behind it, and the books on it.

    Puzzle records are written straight into the store rather than through
    ``add_puzzle``, exactly as ``test_book_ready_gate``'s shelf does: this page
    reads a record's width, height and stored tier and nothing else, and a
    three-book scenario of 302 puzzles would otherwise cost 302 uniqueness
    proofs. The one-cell clue pair keeps every puzzle far above the 4.8 mm
    floor, so membership is never refused (INV-006).
    """

    def __init__(self, app):
        self.app = app
        self.store = app.puzzle_review_service
        self.books = app.book_manager
        self.client = app.test_client()

    def record(self, width, height, tier) -> str:
        puzzle_id = str(uuid.uuid4())
        self.store.puzzles[puzzle_id] = {
            "id": puzzle_id,
            "width": width,
            "height": height,
            "clues_rows": [[1]],
            "clues_cols": [[1]],
            "difficulty_tier": tier.value if hasattr(tier, "value") else tier,
            "status": "approved",
            "book_id": None,
        }
        return puzzle_id

    def puzzles(self, matrix) -> list:
        """One puzzle per puzzle the 4 x 3 ``matrix`` asks for.

        Each one is square at the top of its bucket's range, so which bucket it
        lands in follows from the bounds and not from a size picked here.
        """
        return [
            self.record(bucket.high, bucket.high, tier)
            for (bucket, tier), count in cells_of(matrix).items()
            for _ in range(count)
        ]

    def book(self, matrix, *, plan=PLAN_150, title="Winter") -> str:
        """A draft book holding the selection ``matrix`` describes."""
        book_id = self.books.create_book(title, "a book", "christmas", "adults")
        ids = self.puzzles(matrix)
        if ids:
            assert self.books.add_puzzles_to_book(book_id, ids)
        held = self.books.get_book(book_id).puzzle_ids
        assert len(held) == len(ids), f"the book holds {len(held)} of {len(ids)} puzzles"
        if plan is None:
            self.books._plans.pop(book_id, None)
            assert self.books.get_plan(book_id) is None
        else:
            assert self.books.save_plan(book_id, plan)
        return book_id

    def listing(self, **query) -> str:
        args = "&".join(f"{key}={value}" for key, value in query.items())
        response = self.client.get("/books" + (f"?{args}" if args else ""))
        assert response.status_code == 200
        return response.get_data(as_text=True)


@pytest.fixture
def shelf(admin_app):
    return Shelf(admin_app)


def text_of(fragment: str) -> str:
    """A rendered fragment as readable text: no tags, no entities, one space."""
    without_scripts = re.sub(r"(?s)<script.*?</script>", " ", fragment)
    stripped = re.sub(r"<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", html_module.unescape(stripped)).strip()


def rows_of(html: str) -> list:
    """Every row of the books table, in the order the page rendered them."""
    body = re.search(r"(?s)<tbody>(.*?)</tbody>", html)
    assert body, "the books list rendered no table body"
    return re.findall(r"(?s)<tr>(.*?)</tr>", body.group(1))


def row_of(html: str, book_id: str) -> str:
    """The one row of the books table that is about ``book_id``."""
    matching = [row for row in rows_of(html) if book_id in row]
    assert len(matching) == 1, f"{len(matching)} rows of /books are about book {book_id}"
    return matching[0]


def order_of(html: str, book_ids) -> list:
    """The position of each of ``book_ids`` in the rendered order."""
    rendered = rows_of(html)
    places = {}
    for book_id in book_ids:
        found = [index for index, row in enumerate(rendered) if book_id in row]
        assert len(found) == 1, f"book {book_id} appears in {len(found)} rows"
        places[book_id] = found[0]
    return [book_id for book_id in sorted(places, key=places.get)]


def hints_of(row: str) -> list:
    """The exact-count hints one row carries, in the order it carries them."""
    return [text_of(hint) for hint in re.findall(r'data-off-plan="true"[^>]*>(.*?)</span>', row)]


def figures_of(row: str) -> list:
    """The planned-vs-actual figures one row carries, in rendered order.

    The count first, then the per-tier split. A hint is not one of these: it
    carries ``data-off-plan`` and :func:`hints_of` reads it.
    """
    return [
        text_of(figure)
        for figure in re.findall(r'<span class="stat-cell">(.*?)</span>', row)
    ]


def head_of(html: str, label: str) -> str:
    """The one ``<th>`` of the books table whose column is ``label``.

    Returned as raw markup, not as text: the ``aria-sort`` these tests read is
    an attribute, and whether it is an attribute at all is the thing at stake.
    """
    head = re.search(r"(?s)<thead>(.*?)</thead>", html)
    assert head, "the books list rendered no table head"
    cells = re.findall(r"(?s)<th\b.*?</th>", head.group(1))
    assert cells, "the books list rendered no column heads"
    matching = [cell for cell in cells if text_of(cell).startswith(label)]
    assert len(matching) == 1, f"{len(matching)} heads of /books are the {label} column"
    return matching[0]


def heads_of(html: str) -> list:
    """Every ``<th>`` of the books table, as raw markup, in rendered order."""
    head = re.search(r"(?s)<thead>(.*?)</thead>", html)
    assert head, "the books list rendered no table head"
    return re.findall(r"(?s)<th\b.*?</th>", head.group(1))


def plan_bar_of(row: str) -> str:
    """The opening tag of the one plan bar a row draws, as raw markup."""
    bars = re.findall(r'<div class="progress-bar"[^>]*>', row)
    assert len(bars) == 1, f"the row draws {len(bars)} plan bars"
    return bars[0]


# --------------------------------------------------------------------------
# AC-230 — the actual count against the planned count
# --------------------------------------------------------------------------


class TestBooksList_ShowsActualVsPlannedCount:
    """AC-230: a plan of 150 holding 132 puzzles shows 132 / 150."""

    def test_the_row_shows_actual_against_planned(self, shelf):
        assert total_of(SELECTION_132) == 132
        book_id = shelf.book(SELECTION_132, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert "132 / 150" in text_of(row), text_of(row)
        assert figures_of(row)[0] == "132 / 150", figures_of(row)

    def test_the_bar_beside_it_carries_the_same_figure(self, shelf):
        """The ProgressBar is a second reading of the count, not a third one.

        88% of 150 is 132, and the bar's own accessible name repeats the two
        numbers in words — the figure is never conveyed by a bar length alone.
        """
        book_id = shelf.book(SELECTION_132, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert 'aria-valuenow="88"' in row, row
        assert "132 of 150 planned puzzles" in row, row


# --------------------------------------------------------------------------
# AC-231 — the per-tier split, actual against planned
# --------------------------------------------------------------------------


class TestBooksList_ShowsPerTierActualVsPlan:
    """AC-231: 50 easy, 60 medium, 22 hard against 60 / 60 / 30."""

    def test_the_row_shows_the_split(self, shelf):
        planned = cells_of(PLAN_150_CELLS)
        assert [
            sum(planned[(bucket, tier)] for bucket in BUCKETS) for tier in TIERS
        ] == [60, 60, 30]
        selected = cells_of(SELECTION_132)
        assert [
            sum(selected[(bucket, tier)] for bucket in BUCKETS) for tier in TIERS
        ] == [50, 60, 22]

        book_id = shelf.book(SELECTION_132, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert "easy 50 / 60 · medium 60 / 60 · hard 22 / 30" in text_of(row), text_of(row)
        assert figures_of(row) == ["132 / 150", "50 / 60", "60 / 60", "22 / 30"], figures_of(row)


# --------------------------------------------------------------------------
# AC-232 / CK-1 — the exact-count hint, both ways
# --------------------------------------------------------------------------


class TestBooksList_HintsShortBucket:
    """AC-232: 26-30 x hard holding 5 against a plan of 12 is hinted."""

    def test_the_row_names_the_cell_and_the_exact_shortfall(self, shelf):
        assert cells_of(PLAN_150_CELLS)[(BUCKETS[3], H)] == 12
        assert cells_of(SELECTION_SHORT_BY_7)[(BUCKETS[3], H)] == 5

        book_id = shelf.book(SELECTION_SHORT_BY_7, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert hints_of(row) == ["26-30 × hard: short 7"], text_of(row)

    def test_the_shortfall_is_exact_and_not_the_gates_tolerance(self, shelf):
        """G-3: one puzzle short of a 150-puzzle plan is 0.67 points out.

        The readiness gate forgives that (ADR-0035/R1's +/-3 pp) and this list
        must not: it answers "what is still missing", and the answer is one.
        """
        selection = tuple(
            tuple(value - 1 if (b, t) == (3, 2) else value for t, value in enumerate(row))
            for b, row in enumerate(PLAN_150_CELLS)
        )
        book_id = shelf.book(selection, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert hints_of(row) == ["26-30 × hard: short 1"], text_of(row)


class TestBooksList_HintsOverBucket:
    """CK-1: an over-plan cell is hinted by the same list, worded "over".

    The card leaves it open whether short and over are one hint or two. They
    are **one list**: a cell is off its plan in exactly one direction, both
    directions are work the owner has to do, and one list keeps a table row
    readable. The direction is a word, so the hint reads without its tint.
    """

    def test_the_row_names_the_cell_and_the_exact_excess(self, shelf):
        book_id = shelf.book(SELECTION_OVER_BY_1, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert hints_of(row) == ["26-30 × hard: over 1"], text_of(row)

    def test_a_short_cell_and_an_over_cell_are_hinted_together(self, shelf):
        """Both directions at once, in bucket-then-tier order."""
        selection = (
            (20, 7, 0),
            (30, 27, 8),   # 16-20 x hard: 2 over its 6
            (10, 20, 12),
            (0, 6, 5),     # 26-30 x hard: 7 short of its 12
        )
        book_id = shelf.book(selection, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert hints_of(row) == [
            "16-20 × hard: over 2",
            "26-30 × hard: short 7",
        ], text_of(row)


# --------------------------------------------------------------------------
# AC-233 — no hint for a book on its plan
# --------------------------------------------------------------------------


class TestBooksList_NoHintWhenOnPlan:
    """AC-233: every cell exactly on its plan carries no hint."""

    def test_the_row_carries_no_hint(self, shelf):
        book_id = shelf.book(PLAN_150_CELLS, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert hints_of(row) == [], text_of(row)
        # Whole words: the row's "Cover" download (CARD-158) is not a hint.
        assert not re.search(r"\bshort\b", text_of(row))
        assert not re.search(r"\bover\b", text_of(row))

    def test_the_row_says_so_in_words(self, shelf):
        """"On plan" is stated, not left to the absence of a hint."""
        book_id = shelf.book(PLAN_150_CELLS, plan=PLAN_150)

        row = text_of(row_of(shelf.listing(), book_id))

        assert "150 / 150" in row, row
        assert "On plan" in row, row


# --------------------------------------------------------------------------
# AC-234 / CK-2 / CK-3 — the order
# --------------------------------------------------------------------------


class TestBooksList_SortsByCompleteness:
    """AC-234: 150 / 150, then 132 / 150, then 20 / 100."""

    def test_most_complete_first(self, shelf):
        assert total_of(SELECTION_20) == 20
        assert total_of(SELECTION_132) == 132
        assert total_of(PLAN_150_CELLS) == 150

        fifth = shelf.book(SELECTION_20, plan=PLAN_100, title="Twenty of a hundred")
        full = shelf.book(PLAN_150_CELLS, plan=PLAN_150, title="All hundred and fifty")
        most = shelf.book(SELECTION_132, plan=PLAN_150, title="A hundred and thirty-two")

        body = shelf.listing()

        assert order_of(body, (fifth, full, most)) == [full, most, fifth]
        assert [
            figure
            for figure in ("150 / 150", "132 / 150", "20 / 100")
            if figure in text_of(body)
        ] == ["150 / 150", "132 / 150", "20 / 100"]

    def test_completeness_is_the_ratio_not_the_count(self, shelf):
        """A smaller book further along outranks a bigger one behind it.

        20 / 100 is ahead of 25 / 150, so counting puzzles instead of dividing
        them would put them the other way round.
        """
        fifth = shelf.book(SELECTION_20, plan=PLAN_100, title="Twenty of a hundred")
        twenty_five = shelf.book(
            ((10, 5, 0), (5, 5, 0), (0, 0, 0), (0, 0, 0)), plan=PLAN_150, title="Twenty-five of 150"
        )

        assert order_of(shelf.listing(), (fifth, twenty_five)) == [fifth, twenty_five]


class TestBooksList_PlanlessBookSortsLast:
    """CK-2 — the recorded decision: a plan-less book sorts last.

    FR-039 does not say where a book with no stored plan goes. It has no
    completeness at all, so it cannot be placed among the books that have one,
    and it goes after every one of them — including a planned book at 0 / 150,
    because a book with no plan yet is not further along than a book that has
    one and has not started filling it.
    """

    def test_it_comes_after_every_planned_book_including_an_empty_one(self, shelf):
        plan_less = shelf.book(SELECTION_40, plan=None, title="No plan")
        empty = shelf.book(((0, 0, 0),) * 4, plan=PLAN_150, title="Nothing chosen yet")
        full = shelf.book(PLAN_150_CELLS, plan=PLAN_150, title="Done")

        assert order_of(shelf.listing(), (plan_less, empty, full)) == [full, empty, plan_less]


class TestBooksList_OverPlanBookTiesWithOnPlanBook:
    """CK-5 — the recorded decision: the sort ratio is clamped at 1.

    AC-234 pins 150 / 150 > 132 / 150 > 20 / 100 and says nothing about a book
    over its plan. Uncapped, 160 / 150 is a ratio of 16/15 and would sort ahead
    of everything, including a book that is exactly right. ``/books`` is a
    to-do list, and a book ten over its plan still has work to do — decide
    which ten to drop — so it must not outrank one that needs nothing. Clamped
    at 1 the two are **one tie**, broken by ``get_all_books``' newest-first
    order, which is what the two orderings below show.

    The clamp is for the order only: the row still reads its real figures.
    """

    def test_an_over_plan_book_does_not_outrank_an_on_plan_one(self, shelf):
        assert total_of(SELECTION_OVER_BY_10) == 160
        assert total_of(PLAN_150_CELLS) == 150

        over = shelf.book(SELECTION_OVER_BY_10, plan=PLAN_150, title="Ten too many")
        exact = shelf.book(PLAN_150_CELLS, plan=PLAN_150, title="Exactly right")
        behind = shelf.book(SELECTION_132, plan=PLAN_150, title="Still filling")

        order = order_of(shelf.listing(), (over, exact, behind))

        # `exact` is the newer of the two tied books, so it leads them; the
        # uncapped ratio would have put `over` first instead.
        assert order == [exact, over, behind], order

    def test_the_tie_is_broken_by_creation_order_not_by_the_excess(self, shelf):
        """The mirror image: the over-plan book made *later* leads the tie.

        Which of the two comes first is ``get_all_books``' newest-first order
        over a stable sort, not the excess — so this is a tie and not a
        reversal of the ranking.
        """
        exact = shelf.book(PLAN_150_CELLS, plan=PLAN_150, title="Exactly right")
        over = shelf.book(SELECTION_OVER_BY_10, plan=PLAN_150, title="Ten too many")

        assert order_of(shelf.listing(), (exact, over)) == [over, exact]

    def test_the_row_still_reads_its_real_figures(self, shelf):
        """The clamp is in the sort key alone: 160 / 150, and "over 10"."""
        book_id = shelf.book(SELECTION_OVER_BY_10, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert figures_of(row)[0] == "160 / 150", figures_of(row)
        assert hints_of(row) == ["26-30 × hard: over 10"], text_of(row)


class TestBooksList_SortsBackToNewestFirst:
    """CK-3: the order this list had before CARD-132 is still reachable."""

    def test_sort_created_is_newest_first(self, shelf):
        first = shelf.book(PLAN_150_CELLS, plan=PLAN_150, title="Made first")
        second = shelf.book(SELECTION_20, plan=PLAN_100, title="Made second")

        assert order_of(shelf.listing(sort="created"), (first, second)) == [second, first]

    def test_an_unknown_sort_is_the_default_order(self, shelf):
        fifth = shelf.book(SELECTION_20, plan=PLAN_100, title="Twenty of a hundred")
        full = shelf.book(PLAN_150_CELLS, plan=PLAN_150, title="Done")

        assert order_of(shelf.listing(sort="sideways"), (fifth, full)) == [full, fifth]


# --------------------------------------------------------------------------
# AC-235 — the plan-less book
# --------------------------------------------------------------------------


class TestBooksList_BookWithoutPlanShowsCountOnly:
    """AC-235: 40 puzzles, no stored plan, no planned figure."""

    def test_the_row_shows_the_count_alone(self, shelf):
        assert total_of(SELECTION_40) == 40
        book_id = shelf.book(SELECTION_40, plan=None)

        row = row_of(shelf.listing(), book_id)

        assert figures_of(row) == ["40"], figures_of(row)
        assert hints_of(row) == [], text_of(row)
        assert "aria-valuenow" not in row, "a book with no plan has no progress to draw"

    def test_the_row_points_at_the_remedy(self, shelf):
        """ADR-0035 (c)'s remedy: a plan-less book is told where to get one."""
        book_id = shelf.book(SELECTION_40, plan=None)

        row = row_of(shelf.listing(), book_id)

        assert "No plan yet" in text_of(row), text_of(row)
        assert f"/book/{book_id}/setup-print" in row, row


# --------------------------------------------------------------------------
# CK-6 — the sortable heads say which one is sorted, and which way
# --------------------------------------------------------------------------


class TestBooksList_SortableHeadsAnnounceTheirOrder:
    """CK-6 (review cycle 1, F-004): the `aria-sort` pair on the two heads.

    The list offers descending order only, so the head the page is sorted by
    says ``descending`` and the other sortable head says ``none`` — sortable,
    not sorted. Two things are pinned here, both of which a later edit can
    break in silence:

      * the two values are not interchangeable, and they follow the `sort` the
        request asked for — so the pair has to **swap** under ``?sort=created``;
      * the attribute reaches the page as markup. It renders raw only because
        a Jinja macro returns ``Markup``; a ``|forceescape``, or moving the
        attribute into a Python-side string the route passes in, would emit
        ``aria-sort=&#34;descending&#34;`` and drop the attribute altogether,
        with the page looking untouched. So the raw attribute text is what is
        asserted, never the readable text of the head. (``|e`` and ``|string``
        are *not* that failure mode — both are no-ops on ``Markup``, which was
        checked by mutation rather than assumed.)
    """

    def test_the_sorted_head_is_descending_and_the_other_is_none(self, shelf):
        shelf.book(SELECTION_132, plan=PLAN_150)

        body = shelf.listing()

        assert 'aria-sort="descending"' in head_of(body, "Puzzles"), head_of(body, "Puzzles")
        assert 'aria-sort="none"' in head_of(body, "Created"), head_of(body, "Created")

    def test_the_pair_swaps_when_the_other_column_is_sorted(self, shelf):
        """``?sort=created`` moves ``descending`` to the Created head."""
        shelf.book(SELECTION_132, plan=PLAN_150)

        body = shelf.listing(sort="created")

        assert 'aria-sort="descending"' in head_of(body, "Created"), head_of(body, "Created")
        assert 'aria-sort="none"' in head_of(body, "Puzzles"), head_of(body, "Puzzles")

    def test_only_the_two_sortable_heads_carry_the_attribute(self, shelf):
        """A head that is not a link claims no sort state at all."""
        shelf.book(SELECTION_132, plan=PLAN_150)

        body = shelf.listing()

        carrying = [head for head in heads_of(body) if "aria-sort" in head]
        assert len(carrying) == 2, [text_of(head) for head in carrying]
        assert sorted(text_of(head).split(" ")[0] for head in carrying) == [
            "Created",
            "Puzzles",
        ], [text_of(head) for head in carrying]

    def test_the_attribute_is_markup_and_not_escaped_text(self, shelf):
        """The fragile mechanism, asserted directly: nothing is entity-escaped.

        ``aria-sort=&#34;…&#34;`` is what an escaped macro emits, and it is not
        an attribute — it is visible text inside the tag.
        """
        shelf.book(SELECTION_132, plan=PLAN_150)

        body = shelf.listing()

        assert "aria-sort=&" not in body, "the aria-sort attribute rendered escaped"
        assert body.count('aria-sort="') == 2, body.count('aria-sort="')


# --------------------------------------------------------------------------
# CK-7 — the plan bar's own state word
# --------------------------------------------------------------------------


class TestBooksList_PlanBarSaysWhichFillItIs:
    """CK-7 (review cycle 1, F-003): the bar's states are `partial` and
    `complete`, and never the batch lifecycle's `generating`.

    This bar shows a fill level, not a job in flight. The word matters because
    it is the selector a future CSS or JS rule would be written against: one
    written for real batch behaviour must not reach a book that is merely
    half chosen.
    """

    def test_a_partly_filled_book_is_partial(self, shelf):
        book_id = shelf.book(SELECTION_132, plan=PLAN_150)

        bar = plan_bar_of(row_of(shelf.listing(), book_id))

        assert 'data-status="partial"' in bar, bar
        assert "generating" not in bar, bar

    def test_a_book_on_its_plan_is_complete(self, shelf):
        book_id = shelf.book(PLAN_150_CELLS, plan=PLAN_150)

        bar = plan_bar_of(row_of(shelf.listing(), book_id))

        assert 'data-status="complete"' in bar, bar

    def test_a_book_over_its_plan_is_complete_too(self, shelf):
        """160 of 150 is not "partial": there is nothing left to add."""
        book_id = shelf.book(SELECTION_OVER_BY_10, plan=PLAN_150)

        bar = plan_bar_of(row_of(shelf.listing(), book_id))

        assert 'data-status="complete"' in bar, bar


# --------------------------------------------------------------------------
# CK-4 — the hints are exactly the off-plan cells, over a seeded corpus
# --------------------------------------------------------------------------


#: How many books CK-4's corpus holds. Asserted inside the test, so the corpus
#: cannot silently shrink to one lucky case.
CORPUS_CASES = 24


def test_PropertyTest_BooksList_HintsAreEveryOffPlanCellExactly(shelf) -> None:
    """CK-4: for any book, the hints are exactly its off-plan cells (G-2, G-3).

    No ``hypothesis`` (it is not in the dependency baseline): the corpus is
    built by hand with a seeded ``random.Random`` and the case count is
    asserted inside the test, so it cannot silently shrink.

    The expected hints are derived from the puzzles' own extents through
    :func:`bucket_label_of` — this file's own copy of the longest-side bounds —
    and the sizes are drawn from anywhere inside each bucket's range rather
    than pinned to its top, so agreeing with the page means agreeing with
    ``bucket_of`` about where a 17 x 12 goes and not merely about where a
    20 x 20 does.
    """

    rng = random.Random(20260930)
    checked = seen_short = seen_over = 0

    for case in range(CORPUS_CASES):
        plan_cells = tuple(tuple(rng.randint(0, 3) for _ in TIERS) for _ in BUCKETS)
        plan = DistributionPlan(
            count=max(1, total_of(plan_cells)), split=Split(40, 40, 20), cells=plan_cells
        )
        book_id = shelf.books.create_book(f"Corpus {case}", "a book", "christmas", "adults")

        # The selection, as puzzles of any size inside their own bucket.
        counted = {}
        ids = []
        for label, low, high in BUCKET_BOUNDS:
            for tier in TIERS:
                for _ in range(rng.randint(0, 3)):
                    longest = rng.randint(low, high)
                    shorter = rng.randint(10, longest)
                    width, height = (
                        (longest, shorter) if rng.random() < 0.5 else (shorter, longest)
                    )
                    assert bucket_label_of(width, height) == label
                    counted[(label, tier.value)] = counted.get((label, tier.value), 0) + 1
                    ids.append(shelf.record(width, height, tier))
        if ids:
            assert shelf.books.add_puzzles_to_book(book_id, ids)
        assert shelf.books.save_plan(book_id, plan)

        expected = []
        for b, (label, _low, _high) in enumerate(BUCKET_BOUNDS):
            for t, tier in enumerate(TIERS):
                delta = counted.get((label, tier.value), 0) - plan_cells[b][t]
                if delta > 0:
                    expected.append(f"{label} × {tier.value}: over {delta}")
                elif delta < 0:
                    expected.append(f"{label} × {tier.value}: short {-delta}")

        row = row_of(shelf.listing(), book_id)
        assert hints_of(row) == expected, text_of(row)

        checked += 1
        seen_short += sum(1 for hint in expected if "short" in hint)
        seen_over += sum(1 for hint in expected if "over" in hint)

    assert checked >= CORPUS_CASES >= 24, f"the corpus shrank to {checked} books"
    assert seen_short >= 20, f"the corpus holds only {seen_short} short cells"
    assert seen_over >= 20, f"the corpus holds only {seen_over} over cells"


# --------------------------------------------------------------------------
# CARD-175 — on a phone the hints fold behind one summary line
# --------------------------------------------------------------------------
#
# Presentation evidence, not new FR-039 criteria: the hint data is the same
# list the tests above pin (G-1); these read where the page puts it. Whether a
# disclosure is open or closed at a given width is a browser's call, so that
# half lives in ``tests/test_books_list_mobile.py``.

#: CARD-175 AC-1: four easy <=15 puzzles against PLAN_150. Every one of the
#: plan's ten non-zero cells is then short, and its two zero cells are on plan.
SELECTION_4 = (
    (4, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0),
)

#: The ten hints SELECTION_4 earns, written out in bucket-then-tier order.
HINTS_OF_SELECTION_4 = [
    "<=15 × easy: short 16",
    "<=15 × medium: short 7",
    "16-20 × easy: short 30",
    "16-20 × medium: short 27",
    "16-20 × hard: short 6",
    "21-25 × easy: short 10",
    "21-25 × medium: short 20",
    "21-25 × hard: short 12",
    "26-30 × medium: short 6",
    "26-30 × hard: short 12",
]


def disclosures_of(row: str) -> list:
    """Every ``<details …>…</details>`` one row carries, as raw markup."""
    return re.findall(r"(?s)<details\b.*?</details>", row)


def summary_of(disclosure: str) -> str:
    """The text of a disclosure's one ``<summary>``."""
    summaries = re.findall(r"(?s)<summary\b[^>]*>(.*?)</summary>", disclosure)
    assert len(summaries) == 1, f"the disclosure has {len(summaries)} summaries"
    return text_of(summaries[0])


class TestBooksList_HintsFoldBehindASummary:
    """CARD-175 AC-1: ten off-plan cells sit inside one disclosure whose
    summary counts them."""

    def test_the_row_holds_exactly_one_plan_hints_disclosure(self, shelf):
        book_id = shelf.book(SELECTION_4, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        found = disclosures_of(row)
        assert len(found) == 1, found
        assert found[0].startswith('<details class="plan-hints">'), found[0]

    def test_the_summary_counts_the_cells_in_words(self, shelf):
        book_id = shelf.book(SELECTION_4, plan=PLAN_150)

        (disclosure,) = disclosures_of(row_of(shelf.listing(), book_id))

        assert summary_of(disclosure) == "10 cells off plan"

    def test_every_chip_is_inside_the_disclosure_in_order(self, shelf):
        book_id = shelf.book(SELECTION_4, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)
        (disclosure,) = disclosures_of(row)

        assert hints_of(disclosure) == HINTS_OF_SELECTION_4, text_of(disclosure)
        # ...and none outside it: the whole row carries the same ten.
        assert hints_of(row) == HINTS_OF_SELECTION_4, text_of(row)

    def test_the_summary_is_not_itself_a_hint(self, shelf):
        """The summary carries no `data-off-plan` and neither direction word."""
        book_id = shelf.book(SELECTION_4, plan=PLAN_150)

        (disclosure,) = disclosures_of(row_of(shelf.listing(), book_id))
        summary = re.search(r"(?s)<summary\b.*?</summary>", disclosure).group(0)

        assert "data-off-plan" not in summary, summary
        assert not re.search(r"\b(short|over)\b", text_of(summary)), summary


class TestBooksList_HintSummaryCountsAndAbsence:
    """CARD-175 AC-2: one cell is singular; no hints, no disclosure."""

    def test_one_off_plan_cell_reads_singular(self, shelf):
        book_id = shelf.book(SELECTION_SHORT_BY_7, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)
        (disclosure,) = disclosures_of(row)

        assert summary_of(disclosure) == "1 cell off plan"
        assert hints_of(disclosure) == ["26-30 × hard: short 7"]

    def test_two_off_plan_cells_read_plural(self, shelf):
        selection = (
            (20, 7, 0),
            (30, 27, 8),   # 16-20 x hard: 2 over its 6
            (10, 20, 12),
            (0, 6, 5),     # 26-30 x hard: 7 short of its 12
        )
        book_id = shelf.book(selection, plan=PLAN_150)

        (disclosure,) = disclosures_of(row_of(shelf.listing(), book_id))

        assert summary_of(disclosure) == "2 cells off plan"

    def test_an_on_plan_row_has_no_disclosure(self, shelf):
        book_id = shelf.book(PLAN_150_CELLS, plan=PLAN_150)

        row = row_of(shelf.listing(), book_id)

        assert disclosures_of(row) == [], row
        assert "<summary" not in row, row
        assert "On plan" in text_of(row), text_of(row)

    def test_a_planless_row_has_no_disclosure(self, shelf):
        book_id = shelf.book(SELECTION_40, plan=None)

        row = row_of(shelf.listing(), book_id)

        assert disclosures_of(row) == [], row
        assert "<summary" not in row, row
        assert "No plan yet" in text_of(row), text_of(row)
