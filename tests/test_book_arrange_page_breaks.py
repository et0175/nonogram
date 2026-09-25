"""CARD-140 — the arrange screen shows the book's real page breaks (FR-036, FR-041).

    AC-1  a book of 30x30 puzzles shows one puzzle per page, never three
          (TestArrangeBreaks_BigPuzzlesAreOnePerPage)
    AC-2  two adjacent same-tier puzzles that pair are shown sharing one page,
          with one page number
          (TestArrangeBreaks_PairedNeighboursShareAPage)
    AC-3  the page numbers shown are the interior numbers the PDF prints, for
          the same book
          (TestArrangeBreaks_NumbersMatchTheGeneratedInterior)
    AC-4  the screen's page plan and the PDF's page plan are the same for any
          book
          (PropertyTest_ArrangeBreaks_AgreeWithTheGeneratedBook)
    AC-5  a level's first puzzle starts a new page and the break names the
          level
          (TestArrangeBreaks_LevelStartsANewPage)

The screen used to rule off every third puzzle and label the rule
``order // 3 + 1``. Three per page was true of no book this project prints: the
interior puts **one** puzzle on a page, or two of equal tier whose shared cell
COMP-007 measures at 7.0 mm or more (FR-040, INV-010), and every level opens
behind a divider page of its own (CARD-128, TERM-031). This file is the
evidence that the screen now reports the pages the book really has.

What each side of the comparison is
-----------------------------------
The **screen's** plan is read out of the HTML the real route returned —
:func:`shown_plan` walks the markup in document order and asks "which page
label was the last one above this row?", so a page number rendered in the wrong
place is a mismatch and not just a different string. No test here reads the
route's template context.

The **book's** plan is taken two independent ways, and every example asserts
against both:

* :func:`planned_by_hand` — a second implementation of the walk, written here
  from the rules (INV-009's grouping, one divider per named non-empty level,
  greedy same-tier pairing offered to COMP-007's
  :func:`~nonogram.export.layout.compute_pair_layout`, one interior page each).
  It imports ``nonogram.export.layout`` and ``nonogram.admin.book_page_spec``
  — the authorities on geometry — and deliberately **not**
  ``book_pdf_generator``'s walk, so the comparison is two answers rather than
  one answer twice (CLAUDE.md, "prefer an independent second implementation").
* the **written PDF**, in AC-3: the pages of the file the download route served,
  measured off their own ink by ``tests/helpers`` (``drawings_of``), which is
  the only reading of "the interior numbers the PDF prints" that no page plan
  can fake.

AC-4's corpus is built by hand with stdlib ``random.Random`` (no
``hypothesis``, per CLAUDE.md), and asserts its own minimum size *and* that it
exercised both pairing verdicts — a corpus in which nothing ever paired would
agree about a plan neither side had to think about.

The grids
---------
:func:`comb_grid` is a uniquely-solvable family whose clue depth is a
parameter: one full line across the top (or down the side), and every other
line under it stopped short, so a puzzle's clue gutter is as deep as the test
asks for. Depth matters here and a corpus of solid squares would have hidden
the reason it does: a pair's shared cell is fitted from both puzzles' **real**
clue depths (TERM-021), so two puzzles' extents alone do not decide whether
they share a page, and a screen that guessed from ``width``/``height`` would
disagree with the book on exactly the rows this corpus varies.

How far it disagrees is measured rather than remembered, and the measurement is
:func:`test_extent_alone_would_disagree_with_the_book_on_this_corpus`, which
re-derives every figure below from :func:`corpus_books`, :func:`comb_grid` and
the greedy walk of :func:`planned_by_hand` each time the suite runs. Over that
corpus, each same-tier neighbour pair offered to COMP-007's
:func:`~nonogram.export.layout.compute_pair_layout` on the page the pair would
share:

* 24 books holding **164** puzzles between them;
* **99** same-tier neighbour pairs in print order, of which the greedy forward
  walk actually offers **93** (a pair that forms consumes its successor, so the
  pair starting on the second of two paired puzzles is never asked about);
* **10** of those verdicts come out differently when both puzzles' clues are
  replaced by one-run-deep clues of the same extent — 10 under a solid-grid
  flattening (every row ``(width,)``, every column ``(height,)``) and 10 under
  a filled-count-preserving one (every line ``(sum(runs),)``), so the figure
  does not depend on which way the depth is flattened away.

Ten is a small number and is the whole point: it is not zero, so this corpus
discriminates between the plan the book makes and a plan fitted from extents
alone instead of agreeing with both — an extent-only planner would have put ten
pairs of puzzles on pages the printed book does not print them on.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram import clues as clues_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.difficulty import Tier, tier_of_record
from nonogram.export.layout import compute_pair_layout
from tests.helpers.pdf_pages import pdf_pages
from tests.helpers.two_up_ink import drawings_of

#: The interior's first page is the guide page (INV-013), so the puzzle section
#: — the first level's divider page — starts at 2. Written out rather than
#: imported: it is the number the screen's labels are checked against.
FIRST_SECTION_PAGE = 2


# --------------------------------------------------------------------------
# The grids: uniquely solvable, with the clue depth as a parameter
# --------------------------------------------------------------------------


def comb_grid(width: int, height: int, teeth: int, across: bool = True) -> List[List[bool]]:
    """A filled grid with ``teeth`` notches cut out of it, uniquely solvable.

    ``across=True`` leaves row 0 filled and empties every other cell of the
    first ``2 * teeth - 1`` columns below it, so each of those rows reads
    ``teeth`` runs deep while every column reads ``(1,)`` or ``(height,)``.
    ``across=False`` is the transpose, which puts the depth on the columns
    instead — the axis a two-up page's height is fitted from.

    Unique by construction, which is what the store insists on: a column of one
    cell can only be the one row that is filled right across, and a full column
    is forced. The store is asked all the same — ``add_puzzle`` refuses a grid
    that is not uniquely solvable — so nothing here depends on that argument
    being right.
    """
    if 2 * teeth - 1 > (width if across else height):
        raise ValueError(f"a {width}x{height} grid cannot carry {teeth} teeth")
    if across:
        notched = {x for x in range(1, 2 * teeth - 1, 2)}
        return [[y == 0 or x not in notched for x in range(width)] for y in range(height)]
    notched = {y for y in range(1, 2 * teeth - 1, 2)}
    return [[x == 0 or y not in notched for x in range(width)] for y in range(height)]


# --------------------------------------------------------------------------
# The panel: the real arrange route and the real download route
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
    """The panel, its store and its books, plus the two routes as one-liners."""

    def __init__(self, app):
        self.app = app
        self.store = app.puzzle_review_service
        self.books = app.book_manager
        self.client = app.test_client()
        self._made = 0

    def puzzle(
        self,
        tier: str,
        size: int = 10,
        height: Optional[int] = None,
        teeth: int = 2,
        across: bool = True,
    ) -> str:
        """One approved puzzle of the given tier, extent and clue depth."""
        self._made += 1
        rows = height or size
        grid = comb_grid(size, rows, teeth, across)
        found = clues_module.compute_clues(grid)
        puzzle_id = self.store.add_puzzle(
            grid=grid,
            clues_rows=[list(clue) for clue in found.rows],
            clues_cols=[list(clue) for clue in found.columns],
            width=size,
            height=rows,
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

    def book_of(self, *puzzle_ids: str) -> str:
        """A book holding those puzzles, in that order."""
        book_id = self.books.create_book("Winter", "a book", "christmas", "adults")
        self.books.add_puzzles_to_book(book_id, list(puzzle_ids))
        return book_id

    def arrange(self, book_id: str) -> str:
        """The arrangement screen's markup."""
        response = self.client.get(f"/book/{book_id}/arrange-puzzles")
        assert response.status_code == 200
        return response.get_data(as_text=True)

    def interior_pdf(self, book_id: str) -> bytes:
        """The interior PDF the download route serves for this book."""
        response = self.client.post(f"/book/{book_id}/download-pdf?part=interior")
        assert response.status_code == 200, response.status_code
        assert response.mimetype == "application/pdf", response.mimetype
        return response.get_data()

    def rows_of(self, book_id: str) -> List[Dict[str, Any]]:
        """The book's rows in stored order, as the panel reads them."""
        book = self.books.get_book(book_id)
        return [self.store.get_puzzle(pid) for pid in book.puzzle_ids]

    def book(self, book_id: str):
        return self.books.get_book(book_id)


@pytest.fixture
def panel(admin_app):
    return Panel(admin_app)


# --------------------------------------------------------------------------
# What the screen says
# --------------------------------------------------------------------------

#: One page label or one puzzle row, in the order the markup holds them. A
#: row's own ``data-page`` is optional in the markup and so it is here: a row the
#: plan does not hold carries none.
_TOKEN = re.compile(
    r'class="page-break-divider" data-page="(?P<page>\d+)"'
    r'(?: data-divider-level="(?P<level>[a-z]+)")?'
    r'|class="puzzle-list-item"(?: data-page="(?P<row>\d+)")?'
)

#: The visible text of one page label: ``page 3``, ``page 3 · two puzzles``,
#: ``page 2 · Easy divider page``.
_LABEL = re.compile(r"<span>(?P<text>page [^<]+)</span>")

#: A row's ``item-order`` — the membership number the screen prints in its first
#: column. Read only where that number is the subject; it is **not** the plan's
#: puzzle number (see :func:`shown_plan`).
_ORDER = re.compile(r'class="item-order">(?P<order>\d+)<')


def shown_plan(markup: str) -> Tuple[Dict[int, Optional[int]], Dict[str, int]]:
    """What the screen says, read the way a reader reads it, top to bottom.

    Returns ``({puzzle number: interior page}, {level: divider page})``, keyed
    on the **plan's** puzzle number: the rows the plan holds, counted 1..n in
    document order. That is the plan's own coordinate — ``print_order`` gives
    the screen and the plan the same order, and a row the plan does not hold
    carries no ``data-page`` — so it is the key the two sides of every
    comparison in this file agree on.

    It is deliberately not the row's ``item-order``, which the route numbers
    over the book's whole **membership**: the two coincide only while nothing is
    dropped, and a book with one undrawable member would shift every later key
    by one and fail the property test with a confusing diff instead of reporting
    the real relationship (CARD-140 F-004,
    :func:`test_an_undrawable_member_shifts_no_other_rows_page`).

    A row the plan holds but which has no page label above it maps to ``None``,
    and a divider page's label ends the run it opens — so a break rendered
    *after* the row it belongs to, or a level whose rows are still counted
    against the previous level's last page, comes back wrong rather than
    unnoticed.
    """
    pages: Dict[int, Optional[int]] = {}
    dividers: Dict[str, int] = {}
    current: Optional[int] = None
    number = 0
    for token in _TOKEN.finditer(markup):
        if token.group(0).startswith('class="page-break-divider"'):
            if token.group("level"):
                dividers[token.group("level")] = int(token.group("page"))
                current = None
            else:
                current = int(token.group("page"))
            continue
        if token.group("row") is None:
            # A row the plan does not hold: listed, but not one of the plan's
            # numbered puzzles, and it neither opens nor closes a page's run.
            continue
        number += 1
        pages[number] = current
    return pages, dividers


def shown_rows(markup: str) -> List[Optional[int]]:
    """Each puzzle row's own ``data-page``, in document order.

    ``None`` for a row the plan does not hold — the page the screen prints
    beside the row itself, as against :func:`shown_plan`'s reading of the label
    *above* it. Its length is how many rows the screen listed at all.
    """
    return [
        None if token.group("row") is None else int(token.group("row"))
        for token in _TOKEN.finditer(markup)
        if not token.group(0).startswith('class="page-break-divider"')
    ]


def shown_orders(markup: str) -> List[int]:
    """The membership numbers the screen prints, in document order."""
    return [int(match.group("order")) for match in _ORDER.finditer(markup)]


def shown_labels(markup: str) -> List[str]:
    """Every page label's visible text, in the order the screen shows them."""
    return [match.group("text") for match in _LABEL.finditer(markup)]


# --------------------------------------------------------------------------
# What the book does — worked out here, from the rules
# --------------------------------------------------------------------------

#: The levels in print order (INV-009); anything else ranks after all three.
_RANK = {Tier.EASY: 0, Tier.MEDIUM: 1, Tier.HARD: 2}


def _clue_sets(row: Dict[str, Any]) -> Tuple[tuple, tuple]:
    return (
        tuple(tuple(clue) for clue in row["clues_rows"]),
        tuple(tuple(clue) for clue in row["clues_cols"]),
    )


def planned_by_hand(
    book,
    rows: List[Dict[str, Any]],
    offered: Optional[List[Tuple[Dict[str, Any], Dict[str, Any], int, bool]]] = None,
) -> Tuple[Dict[int, int], Dict[str, int]]:
    """Where this book prints each puzzle, worked out from the rules.

    The independent second implementation this file compares the screen
    against. It is the walk as FR-040/FR-041 and CARD-127/CARD-128 state it,
    and nothing else:

    * the rows are grouped easy, medium, hard by a stable sort, with anything
      ungraded after all three, and numbered 1..n in that order;
    * interior page 1 is the guide page, so the section starts at page 2;
    * a named level opens with a divider page that carries no puzzle;
    * inside a level the walk is greedy and forward: puzzle *i* and *i+1* are
      offered to COMP-007 on the spec of the page they would share, and a
      ``PairLayout`` back puts both on it. Otherwise *i* has the page to
      itself. A run with no readable tier never pairs.

    Args:
        book: The book, for its page specs.
        rows: Its rows, in stored order.
        offered: If given, every pair this walk offers COMP-007 is appended to
            it as ``(earlier row, later row, the shared page, the verdict)``.
            That is what makes the clue-depth measurement a reading of *this*
            walk rather than a fourth implementation of it
            (:func:`test_extent_alone_would_disagree_with_the_book_on_this_corpus`).

    Returns ``({puzzle number: interior page}, {level value: divider page})``.
    """
    ordered = sorted(rows, key=lambda row: _RANK.get(tier_of_record(row["difficulty_tier"]), 3))
    tiers = [tier_of_record(row["difficulty_tier"]) for row in ordered]

    pages: Dict[int, int] = {}
    dividers: Dict[str, int] = {}
    page = FIRST_SECTION_PAGE
    index = 0
    while index < len(ordered):
        level = tiers[index]
        end = index
        while end < len(ordered) and tiers[end] is level:
            end += 1
        if level is not None:
            dividers.setdefault(level.value, page)
            page += 1
        while index < end:
            paired = False
            if level is not None and index + 1 < end:
                paired = (
                    compute_pair_layout(
                        _clue_sets(ordered[index]),
                        _clue_sets(ordered[index + 1]),
                        book_page_spec(book, page),
                    )
                    is not None
                )
                if offered is not None:
                    offered.append((ordered[index], ordered[index + 1], page, paired))
            pages[index + 1] = page
            if paired:
                pages[index + 2] = page
                index += 2
            else:
                index += 1
            page += 1
    return pages, dividers


def generated_plan(book, rows: List[Dict[str, Any]]) -> Tuple[Dict[int, int], Dict[str, int]]:
    """The same question asked of the generator — the call the export walks.

    Imported inside the function so that the module-level imports of this file
    stay the independent ones.
    """
    from nonogram.admin.book_pdf_generator import BookPDFGenerator, DividerPagePlan

    plan = BookPDFGenerator(book).section_plan(rows)
    pages: Dict[int, int] = {}
    dividers: Dict[str, int] = {}
    for entry in plan.pages:
        if isinstance(entry, DividerPagePlan):
            dividers.setdefault(entry.level.value, entry.page_number)
            continue
        for number in entry.numbers:
            pages[number] = entry.page_number
    return pages, dividers


# --------------------------------------------------------------------------
# AC-1 — one puzzle per page, never three
# --------------------------------------------------------------------------


class TestArrangeBreaks_BigPuzzlesAreOnePerPage:
    """A 30x30 fills a book page on its own, and the screen says so."""

    def test_five_big_puzzles_take_five_pages_not_two(self, panel) -> None:
        """The reported bug: five 30x30s used to be shown on two pages."""
        ids = [panel.puzzle("easy", size=30, teeth=8) for _ in range(5)]
        book_id = panel.book_of(*ids)

        pages, dividers = shown_plan(panel.arrange(book_id))

        assert dividers == {"easy": 2}, dividers
        assert pages == {1: 3, 2: 4, 3: 5, 4: 6, 5: 7}, pages
        assert len(set(pages.values())) == 5, "a 30x30 has a page to itself"

    def test_the_screen_and_the_book_agree_that_nothing_pairs(self, panel) -> None:
        ids = [panel.puzzle("easy", size=30, teeth=8) for _ in range(5)]
        book_id = panel.book_of(*ids)
        book, rows = panel.book(book_id), panel.rows_of(book_id)

        shown = shown_plan(panel.arrange(book_id))

        assert shown == planned_by_hand(book, rows)
        assert shown == generated_plan(book, rows)

    def test_no_label_claims_two_puzzles_share_a_page(self, panel) -> None:
        ids = [panel.puzzle("hard", size=30, teeth=8) for _ in range(3)]
        book_id = panel.book_of(*ids)

        labels = shown_labels(panel.arrange(book_id))

        assert labels == [
            "page 2 · Hard divider page",
            "page 3",
            "page 4",
            "page 5",
        ], labels


# --------------------------------------------------------------------------
# AC-2 — a pair is shown sharing one page
# --------------------------------------------------------------------------


class TestArrangeBreaks_PairedNeighboursShareAPage:
    """Two small same-tier neighbours share a page, and one number covers both."""

    def test_the_pair_is_listed_under_one_page_number(self, panel) -> None:
        first = panel.puzzle("easy", size=10, teeth=3)
        second = panel.puzzle("easy", size=10, teeth=3)
        book_id = panel.book_of(first, second)
        book, rows = panel.book(book_id), panel.rows_of(book_id)

        markup = panel.arrange(book_id)
        pages, dividers = shown_plan(markup)

        assert dividers == {"easy": 2}
        assert pages == {1: 3, 2: 3}, "both puzzles print on interior page 3"
        assert shown_labels(markup) == [
            "page 2 · Easy divider page",
            "page 3 · two puzzles",
        ], "one label for the shared page, and it says the page is shared"
        assert (pages, dividers) == planned_by_hand(book, rows)
        assert (pages, dividers) == generated_plan(book, rows)

    def test_the_two_rows_are_not_separated_by_a_break(self, panel) -> None:
        """"Shown as sharing it" is the absence of a rule between them."""
        first = panel.puzzle("easy", size=10, teeth=3)
        second = panel.puzzle("easy", size=10, teeth=3)
        book_id = panel.book_of(first, second)

        markup = panel.arrange(book_id)

        rows = [match.start() for match in re.finditer(r'class="item-order">', markup)]
        breaks = [match.start() for match in re.finditer(r'class="page-break-divider"', markup)]
        assert len(rows) == 2 and len(breaks) == 2, markup
        assert all(position < rows[0] for position in breaks), (
            "both labels open the run; nothing is ruled off between the two rows"
        )

    def test_a_third_puzzle_of_the_same_tier_starts_the_next_page(self, panel) -> None:
        """The walk is greedy and forward: 1+2 share, 3 is alone (EC-027)."""
        ids = [panel.puzzle("easy", size=10, teeth=3) for _ in range(3)]
        book_id = panel.book_of(*ids)

        pages, _dividers = shown_plan(panel.arrange(book_id))

        assert pages == {1: 3, 2: 3, 3: 4}, pages

    def test_two_neighbours_of_different_tiers_do_not_share(self, panel) -> None:
        """INV-010 is untouched: equal tiers only, whatever the screen shows."""
        book_id = panel.book_of(
            panel.puzzle("easy", size=10, teeth=3),
            panel.puzzle("medium", size=10, teeth=3),
        )

        pages, dividers = shown_plan(panel.arrange(book_id))

        assert dividers == {"easy": 2, "medium": 4}
        assert pages == {1: 3, 2: 5}, pages


# --------------------------------------------------------------------------
# AC-3 — the numbers shown are the interior numbers the PDF prints
# --------------------------------------------------------------------------


class TestArrangeBreaks_NumbersMatchTheGeneratedInterior:
    """The pages the screen names are read back out of the written file."""

    def test_every_page_the_screen_names_carries_what_it_says(self, panel) -> None:
        """One book, two readings: the screen's labels, and the PDF's own ink.

        The book is three puzzles: two 10x10 Easies, which are the one
        arrangement the walk turns into a two-up page, and a 30x30 Hard, which
        fills a page on its own. So the screen's claims are all falsifiable on
        the file — a page it calls shared must carry two drawings, a page it
        gives to the 30x30 must carry a 30-column grid, and a page it calls a
        level's divider must carry no grid at all.
        """
        small = [panel.puzzle("easy", size=10, teeth=3) for _ in range(2)]
        big = panel.puzzle("hard", size=30, teeth=8)
        book_id = panel.book_of(small[0], small[1], big)

        pages, dividers = shown_plan(panel.arrange(book_id))
        printed = pdf_pages(panel.interior_pdf(book_id))

        assert pages == {1: 3, 2: 3, 3: 5}, pages
        assert dividers == {"easy": 2, "hard": 4}, dividers
        assert len(printed) >= max(pages.values()), (
            f"the screen names page {max(pages.values())} of a {len(printed)}-page interior"
        )

        shared = drawings_of(printed[pages[1] - 1])
        assert len(shared) == 2, "the page the screen calls shared holds two drawings"
        assert [drawing.columns for drawing in shared] == [10, 10]

        (alone,) = drawings_of(printed[pages[3] - 1])
        assert (alone.columns, alone.rows) == (30, 30), (
            "the page the screen gives the 30x30 is the page it prints on"
        )

        for level, page_number in dividers.items():
            with pytest.raises(ValueError):
                drawings_of(printed[page_number - 1])
            assert page_number + 1 in pages.values(), (
                f"the {level} level's divider page is followed by its first puzzle page"
            )

    def test_the_interior_is_as_long_as_the_plan_the_screen_showed(self, panel) -> None:
        """The last page the screen names is a page of the file, not past it."""
        book_id = panel.book_of(
            panel.puzzle("medium", size=15, teeth=4),
            panel.puzzle("medium", size=15, teeth=4),
        )

        pages, dividers = shown_plan(panel.arrange(book_id))
        printed = pdf_pages(panel.interior_pdf(book_id))

        last_puzzle_page = max(pages.values())
        assert min(dividers.values()) == FIRST_SECTION_PAGE
        assert len(printed) > last_puzzle_page, (
            "the SOLUTIONS divider and the answer key follow the puzzle pages"
        )
        for page_number in sorted(set(pages.values())):
            assert drawings_of(printed[page_number - 1]), (
                f"interior page {page_number} carries a puzzle, as the screen says"
            )


# --------------------------------------------------------------------------
# AC-4 — the two plans agree for any book
# --------------------------------------------------------------------------

#: How many books the corpus holds, asserted inside the test so it cannot
#: silently shrink (CLAUDE.md: no ``hypothesis``, a hand-built seeded corpus
#: that states its own size).
CORPUS_BOOKS = 24

#: The fewest puzzles those books must hold between them.
CORPUS_PUZZLES = 100

#: The fewest pages of each verdict the corpus must have produced. A corpus in
#: which nothing ever paired — or in which everything did — would agree about a
#: plan that was never in doubt.
CORPUS_MIN_OF_EACH_VERDICT = 5


def corpus_books(seed: int = 140) -> List[List[Tuple[str, int, int, int, bool]]]:
    """The books AC-4 compares, drawn once from a seeded ``random.Random``.

    Each book is 3 to 9 puzzles of ``(tier, width, height, teeth, across)``.
    Sizes run from 10 to 30 and the clue depth from 2 to 8 on either axis, so
    the corpus holds pairs that share a page, pairs that are too large to,
    neighbours whose tiers differ, and levels of one puzzle and of several.
    """
    rng = random.Random(seed)
    tiers = ("easy", "medium", "hard")
    books: List[List[Tuple[str, int, int, int, bool]]] = []
    for _ in range(CORPUS_BOOKS):
        book: List[Tuple[str, int, int, int, bool]] = []
        for _ in range(rng.randint(3, 9)):
            width = rng.choice((10, 12, 15, 18, 20, 25, 30))
            height = rng.choice((10, 12, 15, 18, 20, 25, 30))
            teeth = rng.randint(2, min(8, (min(width, height) + 1) // 2))
            book.append((rng.choice(tiers), width, height, teeth, rng.choice((True, False))))
        books.append(book)
    return books


#: Every figure the module docstring quotes about this corpus, re-derived by
#: :func:`test_extent_alone_would_disagree_with_the_book_on_this_corpus`. It is
#: pinned because it is the whole recorded justification for planning from the
#: rows' stored clues rather than from the ``(width, height)`` extent the card's
#: step 1 proposed, and a figure nobody re-measures is a figure that goes stale
#: (CARD-140 F-001: the first set of numbers did, and one of them — more
#: same-tier verdicts than the corpus has same-tier neighbours — was refutable
#: by arithmetic alone).
CORPUS_MEASURED = {
    "books": 24,
    "puzzles": 164,
    "same_tier_neighbours": 99,
    "verdicts_offered": 93,
    "flips_solid_grid": 10,
    "flips_filled_count": 10,
}


def corpus_rows(members: List[Tuple[str, int, int, int, bool]]) -> List[Dict[str, Any]]:
    """One corpus book's rows, as the store would hold them.

    The fields :func:`planned_by_hand` reads, built straight from
    :func:`comb_grid` and :func:`~nonogram.clues.compute_clues` — the same grids
    and therefore the same clues the panel's store keeps for them, without
    paying for 164 uniqueness solves to find that out.
    """
    rows: List[Dict[str, Any]] = []
    for tier, width, height, teeth, across in members:
        found = clues_module.compute_clues(comb_grid(width, height, teeth, across))
        rows.append(
            {
                "difficulty_tier": tier,
                "clues_rows": [list(clue) for clue in found.rows],
                "clues_cols": [list(clue) for clue in found.columns],
                "width": width,
                "height": height,
            }
        )
    return rows


def _solid_grid_clues(row: Dict[str, Any]) -> Tuple[tuple, tuple]:
    """The row's clues flattened to depth 1: a solid grid of the same extent."""
    width, height = row["width"], row["height"]
    return (
        tuple((width,) for _ in range(height)),
        tuple((height,) for _ in range(width)),
    )


def _filled_count_clues(row: Dict[str, Any]) -> Tuple[tuple, tuple]:
    """The row's clues flattened to depth 1, keeping each line's filled count."""
    rows, columns = _clue_sets(row)
    return (
        tuple((sum(clue),) if sum(clue) else (0,) for clue in rows),
        tuple((sum(clue),) if sum(clue) else (0,) for clue in columns),
    )


def test_extent_alone_would_disagree_with_the_book_on_this_corpus() -> None:
    """The measurement behind the deviation from the card's step 1 (CARD-140).

    Step 1 asked for a planner over "each puzzle's tier and ``(width, height)``
    extent". The implementation plans from the rows' **stored clues** instead,
    because a pair's shared cell is fitted from both puzzles' real clue depths
    (``layout._gutter_depth``, TERM-021) — and this is the evidence, re-derived
    every run rather than quoted from a note:

    * the corpus is :func:`corpus_books` at its default seed, its grids
      :func:`comb_grid`, its rows :func:`corpus_rows`;
    * the walk is :func:`planned_by_hand`'s, which reports each same-tier
      neighbour pair it offers COMP-007 and the page they would share. No book
      row is stored and no page is drawn, so this is cheap enough to keep;
    * the book is one with no stored print specification, which is CON-018's
      Book 1 profile — exactly what ``create_book`` leaves, so the page specs are
      AC-4's own;
    * the counterfactual is each pair's verdict re-asked with both puzzles'
      clues flattened to depth 1 at the same extent, which is all an extent-only
      planner could have known. Two flattenings, because the figure must not be
      an artefact of one: a solid grid of the same extent, and one run per line
      keeping that line's filled count.

    The conclusion is what the numbers are for and it does not depend on their
    exact size: the flips are not zero, so extent alone answers INV-010
    differently from the book, and the plan has to travel on the stored clues.
    """
    corpus = corpus_books()
    rows_per_book = [corpus_rows(members) for members in corpus]

    same_tier_neighbours = 0
    offered: List[Tuple[Dict[str, Any], Dict[str, Any], int, bool]] = []
    for rows in rows_per_book:
        ordered = sorted(
            rows, key=lambda row: _RANK.get(tier_of_record(row["difficulty_tier"]), 3)
        )
        tiers = [tier_of_record(row["difficulty_tier"]) for row in ordered]
        same_tier_neighbours += sum(
            1
            for index in range(len(ordered) - 1)
            if tiers[index] is not None and tiers[index] is tiers[index + 1]
        )
        planned_by_hand(None, rows, offered=offered)

    flips = {"flips_solid_grid": 0, "flips_filled_count": 0}
    for earlier, later, page, verdict in offered:
        spec = book_page_spec(None, page)
        for key, flatten in (
            ("flips_solid_grid", _solid_grid_clues),
            ("flips_filled_count", _filled_count_clues),
        ):
            flattened = (
                compute_pair_layout(flatten(earlier), flatten(later), spec) is not None
            )
            if flattened != verdict:
                flips[key] += 1

    measured = {
        "books": len(corpus),
        "puzzles": sum(len(members) for members in corpus),
        "same_tier_neighbours": same_tier_neighbours,
        "verdicts_offered": len(offered),
        **flips,
    }
    assert measured == CORPUS_MEASURED, (
        "the deviation's figures no longer reproduce — re-measure and correct "
        f"the module docstring and CARD-140's note: {measured}"
    )
    assert measured["verdicts_offered"] <= measured["same_tier_neighbours"], (
        "a walk cannot offer more pairs than the corpus has same-tier neighbours"
    )
    assert flips["flips_solid_grid"] > 0, (
        "no verdict flips: the corpus has stopped discriminating between the "
        "book's plan and one fitted from extents alone, which is the only "
        "reason the plan reads the stored clues"
    )


def test_PropertyTest_ArrangeBreaks_AgreeWithTheGeneratedBook(panel) -> None:
    """Over a seeded corpus of books, the screen's plan is the book's plan.

    Named as this project names a property (a ``test_PropertyTest_...``
    function, so the corpus is one case the suite cannot skip past) and built
    the way it builds one: by hand, from a seeded ``random.Random``, with the
    corpus's own size and coverage asserted inside the test.

    Three readings of every book, and all three must agree: the HTML the arrange
    route returned, the rules worked out by :func:`planned_by_hand`, and the
    plan the export path walks. The middle one is what gives the property teeth
    — the other two are the same call twice, which is the comparison this card
    exists to stop anyone being satisfied by.
    """
    corpus = corpus_books()
    assert len(corpus) >= CORPUS_BOOKS, "the corpus must not shrink"
    assert sum(len(book) for book in corpus) >= CORPUS_PUZZLES

    shared_pages = 0
    single_pages = 0
    checked = 0
    for members in corpus:
        ids = [
            panel.puzzle(tier, size=width, height=height, teeth=teeth, across=across)
            for tier, width, height, teeth, across in members
        ]
        book_id = panel.book_of(*ids)
        book, rows = panel.book(book_id), panel.rows_of(book_id)

        shown = shown_plan(panel.arrange(book_id))
        by_hand = planned_by_hand(book, rows)

        assert shown == by_hand, (
            f"the screen and the rules disagree about {members}: "
            f"{shown} against {by_hand}"
        )
        assert shown == generated_plan(book, rows), (
            f"the screen and the generator's own plan disagree about {members}"
        )
        checked += 1

        on_page: Dict[int, int] = {}
        for page in shown[0].values():
            on_page[page] = on_page.get(page, 0) + 1
        shared_pages += sum(1 for count in on_page.values() if count == 2)
        single_pages += sum(1 for count in on_page.values() if count == 1)
        assert max(on_page.values()) <= 2, "a book page never holds three puzzles"

    assert checked == CORPUS_BOOKS
    assert shared_pages >= CORPUS_MIN_OF_EACH_VERDICT, (
        f"only {shared_pages} shared pages: the corpus stopped exercising pairing"
    )
    assert single_pages >= CORPUS_MIN_OF_EACH_VERDICT, (
        f"only {single_pages} single pages: the corpus stopped exercising the refusal"
    )


# --------------------------------------------------------------------------
# AC-5 — a level starts a new page, and the break names the level
# --------------------------------------------------------------------------


class TestArrangeBreaks_LevelStartsANewPage:
    """Each level opens behind its own divider page (CARD-128, TERM-031)."""

    def test_each_level_opens_with_a_break_that_names_it(self, panel) -> None:
        book_id = panel.book_of(
            panel.puzzle("hard", size=30, teeth=8),
            panel.puzzle("easy", size=10, teeth=3),
            panel.puzzle("medium", size=15, teeth=4),
        )

        markup = panel.arrange(book_id)
        pages, dividers = shown_plan(markup)

        assert shown_labels(markup) == [
            "page 2 · Easy divider page",
            "page 3",
            "page 4 · Medium divider page",
            "page 5",
            "page 6 · Hard divider page",
            "page 7",
        ], "the book runs easy, medium, hard and each level opens a page of its own"
        assert dividers == {"easy": 2, "medium": 4, "hard": 6}
        assert pages == {1: 3, 2: 5, 3: 7}
        for level, divider_page in dividers.items():
            first = min(page for number, page in pages.items() if page > divider_page)
            assert first == divider_page + 1, (
                f"the {level} level's first puzzle follows its divider page"
            )

    def test_a_levels_first_puzzle_never_shares_with_the_level_before(self, panel) -> None:
        """Two 10x10s that would have paired are split by the level boundary."""
        book_id = panel.book_of(
            panel.puzzle("easy", size=10, teeth=3),
            panel.puzzle("medium", size=10, teeth=3),
        )

        pages, dividers = shown_plan(panel.arrange(book_id))

        assert pages[1] != pages[2], "a pair cannot straddle a divider (INV-010)"
        assert dividers["medium"] == pages[1] + 1
        assert pages[2] == dividers["medium"] + 1

    def test_an_empty_level_gets_no_break(self, panel) -> None:
        book_id = panel.book_of(
            panel.puzzle("easy", size=10, teeth=3),
            panel.puzzle("hard", size=10, teeth=3),
        )

        _pages, dividers = shown_plan(panel.arrange(book_id))

        assert set(dividers) == {"easy", "hard"}, dividers


# --------------------------------------------------------------------------
# When there is no plan to show (CARD-140 F-002, F-004)
# --------------------------------------------------------------------------


class TestArrangeBreaks_WhenThereIsNoPlanToShow:
    """The screen declines to answer rather than answering wrongly.

    The arrange step is three steps before Finalise, so a book the generator
    cannot plan must not fail on the owner here — but the fallback drops every
    page label and every level divider, which renders identically to a book that
    genuinely has no page structure. No book this project prints is one, so the
    screen has to *say* the labels are missing (F-002). And the one book the
    plan is smaller than its membership — a member that builds no export payload
    — must shift no other row's page (F-004).
    """

    @staticmethod
    def _cannot_be_laid_out(panel, book_id: str) -> None:
        """Store a trim outside KDP's bounds, so no sheet can be built.

        The failure ``section_plan`` documents, reached the way a real book
        reaches it: ``BookPDFGenerator``'s constructor asks
        ``book_page_spec`` for the book's trim and it raises ``ValueError``
        naming the column.
        """
        panel.books.books[book_id].trim_width_cm = "50.00"

    def test_the_step_still_answers_when_the_book_cannot_be_planned(self, panel) -> None:
        """200, every row listed, no page label — and the owner is told why."""
        ids = [panel.puzzle("easy", size=10, teeth=3) for _ in range(3)]
        book_id = panel.book_of(*ids)
        self._cannot_be_laid_out(panel, book_id)

        markup = panel.arrange(book_id)  # asserts the 200 itself

        assert shown_orders(markup) == [1, 2, 3], "every row is still listed"
        for puzzle_id in ids:
            assert puzzle_id in markup, f"row {puzzle_id} is missing from the screen"
        assert shown_labels(markup) == [], "there are no pages to label"
        assert shown_rows(markup) == [None, None, None]
        assert shown_plan(markup) == ({}, {})
        assert 'id="page-plan-unavailable"' in markup, (
            "a page-break-free list is what a book with no page structure looks "
            "like, so the screen must say the breaks are unavailable"
        )
        assert "could not be worked out" in markup

    def test_a_planned_book_shows_no_such_notice(self, panel) -> None:
        """The control: the notice is the failure's, not part of the furniture."""
        book_id = panel.book_of(panel.puzzle("easy", size=10, teeth=3))

        markup = panel.arrange(book_id)

        assert 'id="page-plan-unavailable"' not in markup
        assert shown_labels(markup) == ["page 2 · Easy divider page", "page 3"]

    def test_the_declared_failure_is_logged_as_a_warning(self, panel, caplog) -> None:
        """A stored trim that is not a sheet is the book's fault, not a bug."""
        book_id = panel.book_of(panel.puzzle("easy", size=10, teeth=3))
        self._cannot_be_laid_out(panel, book_id)

        with caplog.at_level(logging.DEBUG):
            panel.arrange(book_id)

        records = [record for record in caplog.records if "page plan" in record.message]
        assert records, caplog.text
        assert [record.levelno for record in records] == [logging.WARNING]
        assert all(record.exc_info is None for record in records), (
            "a declared failure needs no traceback"
        )
        assert "trim_width_cm" in caplog.text, "the log names the column at fault"

    def test_a_bug_in_the_seam_itself_is_logged_with_its_traceback(
        self, panel, monkeypatch, caplog
    ) -> None:
        """The regression class this card exists to make impossible.

        A renamed plan field or a changed ``numbers`` index breaks
        ``_printed_places`` itself, not the book — and a screen with no page
        labels looks the same either way, so the two must be distinguishable in
        the log. Simulated by a plan whose pages name puzzles it does not carry,
        which is what either mistake leaves behind.
        """
        from nonogram.admin import book_pdf_generator

        book_id = panel.book_of(panel.puzzle("easy", size=10, teeth=3))

        original = book_pdf_generator.BookPDFGenerator.section_plan

        def truncated(self, puzzles):
            plan = original(self, puzzles)
            return replace(plan, printed=[])

        monkeypatch.setattr(
            book_pdf_generator.BookPDFGenerator, "section_plan", truncated
        )

        with caplog.at_level(logging.DEBUG):
            markup = panel.arrange(book_id)  # asserts the 200 itself

        assert 'id="page-plan-unavailable"' in markup, "the owner is still told"
        assert shown_labels(markup) == []
        failures = [record for record in caplog.records if record.levelno >= logging.ERROR]
        assert failures, caplog.text
        assert any(record.exc_info is not None for record in failures), (
            "an unexpected failure is logged with its traceback, not as a "
            "one-line warning, so it can be told apart from a book whose "
            "stored specification is at fault"
        )

    def test_an_undrawable_member_shifts_no_other_rows_page(self, panel) -> None:
        """A row that builds no export payload takes no puzzle number with it.

        The one degenerate case in this card's review focus: the plan numbers
        only the rows that built an ``ExportPayload``, while the screen's
        ``item-order`` counts every member, so after a drop the two part company
        and only the plan's own numbering describes the book. The middle row's
        stored clues are replaced with a value ``_payload`` cannot read, which
        stands in for any record the export has to drop (it logs and drops it,
        exactly as the interior does).
        """
        ids = [panel.puzzle("easy", size=30, teeth=8) for _ in range(3)]
        book_id = panel.book_of(*ids)
        panel.store.puzzles[ids[1]]["clues_rows"] = 12
        book = panel.book(book_id)
        drawable = [
            row for row in panel.rows_of(book_id) if isinstance(row["clues_rows"], list)
        ]

        markup = panel.arrange(book_id)
        pages, dividers = shown_plan(markup)

        assert shown_orders(markup) == [1, 2, 3], "the dropped row is still listed"
        assert shown_rows(markup) == [3, None, 4], (
            "the row the book cannot print carries no page, and the row after it "
            "keeps the page the plan gives it"
        )
        assert dividers == {"easy": 2}
        assert pages == {1: 3, 2: 4}, pages
        assert (pages, dividers) == planned_by_hand(book, drawable)
        assert (pages, dividers) == generated_plan(book, panel.rows_of(book_id))
        assert shown_labels(markup) == [
            "page 2 · Easy divider page",
            "page 3",
            "page 4",
        ], "two printable puzzles, two pages, and no label for the third row"
