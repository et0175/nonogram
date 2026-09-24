"""CARD-134 — the packed answer key (FR-042, INV-011, ADR-0036/R2, ADR-0037/R1).

    AC-261  TestBookAnswerKey_SixUpInPuzzleNumberOrder
    AC-263  TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage
    AC-264  TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20
    AC-266  TestBookAnswerKey_LongestSideTwentyStaysSixUp
    AC-268  TestBookAnswerKey_CaptionPuzzleNumberAndTitle
            TestBookAnswerKey_CaptionSeparatorIsADrawnGlyph (G-1a)
    AC-269  TestBookAnswerKey_CaptionUsesCustomBookTitle
    AC-270  TestBookAnswerKey_DefaultPlanTakesThirtyPages
    AC-290  TestBookAnswerKey_EachLevelStartsNewAnswerPage
    AC-291  TestBookAnswerKey_HeadingOnlyOnLevelFirstPage
    AC-292  TestBookAnswerKey_SolutionsDividerPrecedesAnswerKey
    EC-031  TestBookAnswerKey_SixUpRuleKeepsTheAnswerCellAboveTheFloor
            (the link only — the floor itself is CARD-133's
            tests/property/test_book_answer_tiles.py)

How an answer page is read back
-------------------------------
Two independent measurements, and every AC uses both.

**The page, pixel for pixel.** An answer page is asserted by building the page
this test says should be there — through COMP-007's own
:func:`~nonogram.export.png.render_answer_page`, handed the grids and captions
*this module* names, in the order it names them, at the capacity and under the
heading it names — and comparing it with the page the generator produced. Two
pages differing by one answer, one caption character, one heading or one
tiling differ in their pixels, so the comparison fails a key that packs the
wrong answers, packs them in the wrong order, captions them wrongly, or lays
the page out four-up where it should be six-up. It is the same technique
``tests/test_book_pdf_band.py`` reads a band with, and for the same reason:
nothing in the dependency baseline turns ink back into letters.

Nothing here imports :mod:`nonogram.admin.book_answer_key`. The grouping every
expectation is built from is written out by hand, case by case, so what is
compared is FR-042's rule as this module reads it against the walk under test,
not the walk against itself.

**The page's shape, off its own ink.** A byte comparison is exact but says
nothing about *where* anything is, and two blank pages are equal. So each page
is also measured structurally by :func:`answer_grids` — the grids found as the
wide blocks of ink on the page, with no help from any layout call — which
gives the answers' tile boxes in reading order. That is what "2 columns x 3
rows, read left to right, top to bottom" is asserted against, and it is what
shows the captions and headings carry ink at all.

The book, and why its puzzles never pair
----------------------------------------
Every book here is CON-018's Book 1 profile, written out in millimetres rather
than imported. Its puzzles are drawn with 3-deep clue gutters, so no two
neighbours ever share a page (FR-040, CARD-127) and the interior's make-up is
exactly one page per puzzle followed by the divider and the key — which is
what lets :func:`answer_key_of` find the answer pages by position. Pairing has
its own corpora (``tests/test_book_pdf_two_up.py``); what is under test here
is the answer section.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pytest
from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin import book_pdf_generator
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.export import pdf, png
from nonogram.export.layout import compute_answer_page_layout
from nonogram.export.png import render_answer_page
from nonogram.limits import MAX_SIZE, MIN_SIZE

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out rather than imported.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4

#: A pixel darker than this (0..255 grey) is ink.
INK_LEVEL = 128

#: FR-042's caption rule, restated here: the number, an em dash (U+2014) with
#: a space either side, and the title.
CAPTION = "Puzzle {number} — {title}"

#: The caption of a puzzle with neither a custom book title nor a name — this
#: card's documented decision (``book_answer_key.answer_caption``).
UNTITLED_CAPTION = "Puzzle {number}"

#: FR-042's two tilings.
SIX_UP = 6
FOUR_UP = 4

#: INV-011's threshold: an answer longer than this on its longest side takes
#: its page down to :data:`FOUR_UP`.
SIX_UP_LONGEST_SIDE = 20


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book(puzzle_titles: Optional[dict] = None) -> Book:
    """A book on the Book 1 profile, as a ``books`` row carries it.

    ``puzzle_titles`` is the ``{puzzle_id: title}`` column the Arrangement step
    writes (FR-041); an empty one is a book whose puzzles print under their own
    names.
    """
    return Book(
        book_id="book-134",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="A test book.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(BOOK1_WIDTH_MM),
        trim_height_cm=_cm(BOOK1_HEIGHT_MM),
        gutter_margin_cm=_cm(GUTTER_MM),
        outside_margin_cm=_cm(OUTSIDE_MM),
        puzzle_titles=dict(puzzle_titles or {}),
    )


def _grid(columns: int, rows: int, depth: int = 3, mark: int = 0) -> List[List[bool]]:
    """A solved grid whose clues are ``depth`` entries deep, and that is its own.

    The clue depth decides how wide and tall the *drawing* is on a puzzle page,
    and 3 is shallow enough that no two of these ever pair (see the module
    docstring). ``mark`` fills one extra cell in the bottom-right corner, at a
    position that varies with it, so two answers of the same extent are
    different pictures — otherwise a key that drew answer 4 in answer 2's tile
    would be invisible to a comparison of pages.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    grid = [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]
    grid[rows - 1][(columns - 1) - (mark % (columns - limit))] = True
    return grid


def _puzzle(
    columns: int = 15,
    rows: int = 15,
    *,
    number: int = 1,
    name: Optional[str] = None,
    tier: object = "easy",
) -> dict:
    """One book puzzle, in the shape the review service hands the generator.

    Its id is ``"p<number>"`` and its name defaults to ``"Picture <number>"``,
    so every puzzle of a book is distinguishable by both.
    """
    grid = _grid(columns, rows, mark=number)
    found = clues.compute_clues(grid)
    return {
        "id": f"p{number}",
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": f"Picture {number}" if name is None else name,
        "difficulty_tier": tier,
    }


def _book_of(*sizes: Tuple[int, int], tiers: Sequence[object] = ()) -> List[dict]:
    """A book's puzzles, numbered 1..n, from ``(columns, rows)`` pairs."""
    levels = list(tiers) or ["easy"] * len(sizes)
    return [
        _puzzle(columns, rows, number=index + 1, tier=levels[index])
        for index, (columns, rows) in enumerate(sizes)
    ]


def _interior(puzzles: Sequence[dict], book: Optional[Book] = None) -> List[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``."""
    return BookPDFGenerator(book if book is not None else _book()).interior_pages(
        list(puzzles)
    )


# --------------------------------------------------------------------------
# Reading a page back off its ink
# --------------------------------------------------------------------------


def _ink(page: Image.Image) -> np.ndarray:
    return np.asarray(page.convert("L")) < INK_LEVEL


def _bands(present: Iterable[bool]) -> List[Tuple[int, int]]:
    """The maximal runs of ``True``, as ``(first, last)`` index pairs."""
    bands: List[List[int]] = []
    previous = False
    for index, here in enumerate(present):
        if here and not previous:
            bands.append([index, index])
        elif here:
            bands[-1][1] = index
        previous = here
    return [(first, last) for first, last in bands]


#: How large a block of ink must be, as a share of the page, to be an answer's
#: grid rather than a line of type — in **both** axes. The smallest grid the
#: key can print is a 10x10 at the 5 mm answer cap, which is 50 x 50 mm: about
#: a fifth of a Book 1 page across and down. A caption or a heading is a line
#: of about 3.5 mm type, so it fails the height test by an order of magnitude
#: however long its text is, which is what keeps a title from being mistaken
#: for a picture.
_GRID_SHARE = 0.1


def answer_grids(page: Image.Image) -> List[Tuple[int, int, int, int]]:
    """The answers' grids on ``page``, as ``(top, bottom, left, right)`` boxes.

    Found off the page's own ink and nothing else: the rows carrying ink are
    grouped into bands, each band's inked columns are grouped in turn, and a
    block at least :data:`_GRID_SHARE` of the page in both axes is a grid. A
    caption, a level heading and the divider's word are all one short line of
    type, so they are excluded by the same measurement that finds the grids.

    The boxes come back in reading order — top to bottom, then left to right —
    which is what "read left to right, top to bottom" (AC-261) is asserted
    against.
    """
    mask = _ink(page)
    least_wide = page.width * _GRID_SHARE
    least_tall = page.height * _GRID_SHARE
    boxes: List[Tuple[int, int, int, int]] = []
    for top, bottom in _bands(mask.any(axis=1)):
        if bottom - top + 1 < least_tall:
            continue
        strip = mask[top : bottom + 1]
        for left, right in _bands(strip.any(axis=0)):
            if right - left + 1 >= least_wide:
                boxes.append((top, bottom, left, right))
    return boxes


#: How far apart two grids' centres (or tops) may be and still count as the
#: same tile column (or row), in device pixels. A tile's grid is centred across
#: it and hangs from its caption line, so two answers in one column agree to
#: within a rounded pixel or two; the two columns of a Book 1 answer page are
#: about 1150 px apart.
_SAME_TILE_PX = 4


def _clusters(values: Iterable[float]) -> int:
    """How many groups ``values`` fall into, two within :data:`_SAME_TILE_PX`
    counting as one."""
    groups: List[float] = []
    for value in sorted(values):
        if not groups or value - groups[-1] > _SAME_TILE_PX:
            groups.append(value)
    return len(groups)


def grid_columns_and_rows(page: Image.Image) -> Tuple[int, int]:
    """How many tile columns and tile rows of answers ``page`` carries.

    Counted off :func:`answer_grids`: two grids share a tile **column** when
    their horizontal centres agree (each grid is centred across its own tile,
    so a 25x25 and a 15x15 in one column have very different edges and the same
    centre), and a tile **row** when their top edges agree (every grid hangs
    from its caption line).
    """
    boxes = answer_grids(page)
    return (
        _clusters((left + right) / 2 for _, _, left, right in boxes),
        _clusters(top for top, _, _, _ in boxes),
    )


def text_lines_above_the_first_grid(page: Image.Image) -> int:
    """How many lines of type sit above the page's first answer grid.

    One on a page whose first tile carries only its caption; two on a page that
    carries a level heading above it. Counted as the bands of inked rows that
    hold no wide block and begin above the first grid, so nothing here knows
    what a heading line is worth in millimetres.
    """
    grids = answer_grids(page)
    assert grids, "the page carries no answer"
    first_grid_top = min(top for top, _, _, _ in grids)
    wide = {box[0] for box in grids}
    mask = _ink(page)
    return sum(
        1
        for top, _ in _bands(mask.any(axis=1))
        if top < first_grid_top and top not in wide
    )


def is_divider(page: Image.Image) -> bool:
    """Whether ``page`` is a divider: one short line of type, and nothing else.

    Measured, not compared: one band of inked rows, no wide block in it, and
    under a thousandth of the page inked — which no answer page and no puzzle
    page can satisfy.
    """
    mask = _ink(page)
    rows = _bands(mask.any(axis=1))
    return (
        len(rows) == 1
        and not answer_grids(page)
        and mask.sum() < page.width * page.height / 1000
    )


def answer_key_of(
    pages: Sequence[Image.Image], puzzle_count: Optional[int] = None
) -> List[Image.Image]:
    """The interior's answer pages: everything after the SOLUTIONS divider.

    The divider is found by **measuring** the pages rather than by counting to
    it (:func:`is_divider`), so a book whose puzzles happened to pair two-up
    (FR-040) is read just as correctly as one whose puzzles did not. Exactly
    one page of the interior may be a divider, and every page after it must
    carry an answer — so every test in this module carries AC-292's check as
    well as its own.

    ``puzzle_count``, when given, is asserted against where the divider was
    found — which is how a test that expects no pairing finds out that its
    puzzles paired, and what makes ``3 + puzzle_count`` a safe interior
    position for the first answer page. It is left out only where the pairing
    is beside the point.
    """
    dividers = [number for number, page in enumerate(pages, start=1) if is_divider(page)]
    assert len(dividers) == 1, f"the interior holds {len(dividers)} divider page(s)"
    (divider,) = dividers
    if puzzle_count is not None:
        assert divider == 2 + puzzle_count, (
            f"the divider is interior page {divider}, not {2 + puzzle_count} — "
            "these puzzles were expected to take a page each"
        )
    key = list(pages[divider:])
    assert key, "the book has no answer pages"
    for offset, page in enumerate(key):
        assert answer_grids(page), f"answer page {offset + 1} carries no answer"
    return key


def expected_answer_page(
    entries: Sequence[Tuple[dict, str]],
    capacity: int,
    page_number: int,
    heading: Optional[str] = None,
    book: Optional[Book] = None,
) -> Image.Image:
    """The answer page this module says the interior should hold at ``page_number``.

    Drawn through COMP-007's own renderer from the grids and captions named
    here, on the sheet of that interior position — so a comparison against the
    generator's page is about which answers, in which order, at which tiling,
    under which heading, with which captions, and nothing else.
    """
    return render_answer_page(
        [(puzzle["grid"], caption) for puzzle, caption in entries],
        capacity,
        book_page_spec(book if book is not None else _book(), page_number),
        heading,
    )


def captioned(puzzles: Sequence[dict], numbers: Sequence[int]) -> List[Tuple[dict, str]]:
    """``(puzzle, caption)`` for each of ``numbers``, captioned by this module's rule."""
    return [
        (
            puzzles[number - 1],
            CAPTION.format(number=number, title=puzzles[number - 1]["puzzle_name"]),
        )
        for number in numbers
    ]


# --------------------------------------------------------------------------
# AC-261 — six answers to a page, in puzzle-number order
# --------------------------------------------------------------------------


class TestBookAnswerKey_SixUpInPuzzleNumberOrder:
    """AC-261 (INV-011) — 12 easy 15x15 puzzles make two six-up answer pages.

    Answers 1-6 on the first and 7-12 on the second, each page 2 columns x 3
    rows read left to right, top to bottom. Where one answer page per puzzle
    would have taken 12.
    """

    PUZZLES = 12

    @staticmethod
    def _key() -> Tuple[List[dict], List[Image.Image]]:
        puzzles = _book_of(*[(15, 15)] * TestBookAnswerKey_SixUpInPuzzleNumberOrder.PUZZLES)
        return puzzles, answer_key_of(_interior(puzzles), len(puzzles))

    def test_twelve_answers_take_two_pages(self) -> None:
        _, key = self._key()
        assert len(key) == 2

    @pytest.mark.parametrize(
        "offset,numbers,heading",
        [
            (0, (1, 2, 3, 4, 5, 6), "Easy"),
            (1, (7, 8, 9, 10, 11, 12), None),
        ],
    )
    def test_each_page_holds_its_six_answers_in_number_order(
        self, offset: int, numbers: Tuple[int, ...], heading: Optional[str]
    ) -> None:
        """The page is, pixel for pixel, the page of exactly those six answers.

        Its interior position is ``3 + puzzles + offset`` — after the guide
        page, the puzzle pages and the divider — which is also what makes the
        comparison a check on the page's *parity*: a key laid out on the wrong
        side of the spread would sit a few millimetres across from this.
        """
        puzzles, key = self._key()
        page_number = 3 + self.PUZZLES + offset
        expected = expected_answer_page(
            captioned(puzzles, numbers), SIX_UP, page_number, heading
        )
        assert key[offset].tobytes() == expected.tobytes()

    @pytest.mark.parametrize("offset", [0, 1])
    def test_each_page_is_two_columns_by_three_rows(self, offset: int) -> None:
        """Measured off the page's own ink, with no layout call involved."""
        _, key = self._key()
        assert grid_columns_and_rows(key[offset]) == (2, 3)
        assert len(answer_grids(key[offset])) == SIX_UP


# --------------------------------------------------------------------------
# AC-263 — a large answer that would overfill a six-up page starts a new one
# --------------------------------------------------------------------------


class TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage:
    """AC-263 (INV-011) — five 15x15s then a 25x25.

    The sixth answer would take the page down to four-up, and six answers do
    not fit a four-up page, so the first page closes holding five and the
    25x25 opens the next one. The page is still *tiled* six-up: it was
    measured for six and drew five (CARD-133).
    """

    SIZES = ((15, 15), (15, 15), (15, 15), (15, 15), (15, 15), (25, 25))

    def test_the_first_page_holds_five_and_the_large_answer_starts_the_next(self) -> None:
        puzzles = _book_of(*self.SIZES)
        key = answer_key_of(_interior(puzzles), len(puzzles))
        first_page = 3 + len(puzzles)

        assert len(key) == 2
        assert key[0].tobytes() == expected_answer_page(
            captioned(puzzles, (1, 2, 3, 4, 5)), SIX_UP, first_page, "Easy"
        ).tobytes()
        assert key[1].tobytes() == expected_answer_page(
            captioned(puzzles, (6,)), FOUR_UP, first_page + 1, None
        ).tobytes()

    def test_the_first_page_shows_five_answers_and_the_second_one(self) -> None:
        """The counts, read off the ink rather than off the comparison above."""
        puzzles = _book_of(*self.SIZES)
        key = answer_key_of(_interior(puzzles), len(puzzles))

        assert len(answer_grids(key[0])) == 5
        assert len(answer_grids(key[1])) == 1


# --------------------------------------------------------------------------
# AC-264 — a page becomes four-up once it holds an answer above 20
# --------------------------------------------------------------------------


class TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20:
    """AC-264 (INV-011) — three 15x15s, a 25x25, then a 15x15.

    The 25x25 is the page's fourth answer, which a four-up page holds, so it
    joins; the fifth answer does not, so it starts a new page. This is the
    other side of AC-263: a page is closed *late*, when the next answer would
    push it past the capacity it would then have, never as soon as a large
    answer is seen.
    """

    SIZES = ((15, 15), (15, 15), (15, 15), (25, 25), (15, 15))

    def test_the_first_page_is_a_four_up_of_four_and_answer_five_starts_the_next(
        self,
    ) -> None:
        puzzles = _book_of(*self.SIZES)
        key = answer_key_of(_interior(puzzles), len(puzzles))
        first_page = 3 + len(puzzles)

        assert len(key) == 2
        assert key[0].tobytes() == expected_answer_page(
            captioned(puzzles, (1, 2, 3, 4)), FOUR_UP, first_page, "Easy"
        ).tobytes()
        assert key[1].tobytes() == expected_answer_page(
            captioned(puzzles, (5,)), SIX_UP, first_page + 1, None
        ).tobytes()

    def test_the_first_page_is_two_columns_by_two_rows(self) -> None:
        puzzles = _book_of(*self.SIZES)
        key = answer_key_of(_interior(puzzles), len(puzzles))

        assert grid_columns_and_rows(key[0]) == (2, 2)
        assert len(answer_grids(key[0])) == FOUR_UP


# --------------------------------------------------------------------------
# AC-266 — a longest side of exactly 20 keeps the page six-up
# --------------------------------------------------------------------------


class TestBookAnswerKey_LongestSideTwentyStaysSixUp:
    """AC-266 (INV-011) — a 20 x 15 and five 15x15s make one six-up page.

    The boundary INV-011 states: *at most* 20 on the longest side keeps six-up,
    so 20 is six-up and 21 is not. Both sides are measured.
    """

    def test_twenty_on_the_longest_side_leaves_one_six_up_page(self) -> None:
        puzzles = _book_of((SIX_UP_LONGEST_SIDE, 15), *[(15, 15)] * 5)
        key = answer_key_of(_interior(puzzles), len(puzzles))

        assert len(key) == 1
        assert key[0].tobytes() == expected_answer_page(
            captioned(puzzles, (1, 2, 3, 4, 5, 6)),
            SIX_UP,
            3 + len(puzzles),
            "Easy",
        ).tobytes()
        assert grid_columns_and_rows(key[0]) == (2, 3)

    def test_one_cell_longer_takes_the_page_to_four_up(self) -> None:
        """The control: 21 wide, and the same six puzzles need two pages."""
        puzzles = _book_of((SIX_UP_LONGEST_SIDE + 1, 15), *[(15, 15)] * 5)
        key = answer_key_of(_interior(puzzles), len(puzzles))

        assert len(key) == 2
        assert len(answer_grids(key[0])) == FOUR_UP
        assert len(answer_grids(key[1])) == 2


# --------------------------------------------------------------------------
# EC-031's floor, and the rule that keeps it
# --------------------------------------------------------------------------

#: EC-031's floor on a printed answer cell, in millimetres — written out as
#: CARD-133's ``tests/property/test_book_answer_tiles.py`` writes it, because
#: nothing in ``nonogram.export.layout`` holds a cell up to it.
ANSWER_FLOOR_MM = 3.19

#: The first square answer whose six-up cell falls under that floor on the
#: Book 1 profile. INV-011 refuses it a six-up page.
FIRST_SIX_UP_BREACH = 25


class TestBookAnswerKey_SixUpRuleKeepsTheAnswerCellAboveTheFloor:
    """Why :data:`SIX_UP_LONGEST_SIDE` is a rule and not a preference (EC-031).

    ``book_answer_key``'s own docstring rests the 3.19 mm answer-cell floor on
    this module's capacity rule, because
    :func:`~nonogram.export.layout.compute_answer_page_layout` enforces no
    floor of its own — a 25x25 laid out six-up comes back undersized and no
    error is raised. That rationale was otherwise unmeasured on this card: the
    floor itself is swept, over every extent INV-011 admits, by CARD-133's
    ``tests/property/test_book_answer_tiles.py``, and nothing else here
    measures a millimetre.

    So this pins the *link* — the rule's threshold against the geometry it is
    chosen for — on the Book 1 page the rule produces. The layout is read, not
    reimplemented: what is asserted is which side of the floor each case lands
    on, which is the rule's claim. The arithmetic that puts it there is
    CARD-133's property test's business, re-derived there from the profile's
    own literals.
    """

    @staticmethod
    def _cell_mm(side: int, capacity: int, heading: Optional[str]) -> float:
        """The printed cell of one ``side`` x ``side`` answer on such a page."""
        layout = compute_answer_page_layout(
            [(side, side)], capacity, book_page_spec(_book(), 4), heading
        )
        return layout.tiles[0].cell_mm

    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_the_largest_answer_left_six_up_clears_the_floor(
        self, heading: Optional[str]
    ) -> None:
        """20 on the longest side, six-up: 3.97 mm bare, 3.84 mm under a heading.

        The worst case the rule admits to a six-up page, on both kinds of page
        it can be — a level's first page carries a heading and gives up 6 mm.
        """
        assert self._cell_mm(SIX_UP_LONGEST_SIDE, SIX_UP, heading) >= ANSWER_FLOOR_MM

    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_an_answer_the_rule_refuses_six_up_would_have_broken_the_floor(
        self, heading: Optional[str]
    ) -> None:
        """25x25 six-up: 3.18 mm bare, 3.07 mm headed — and nothing raises.

        The other half of the link. Were the capacity rule a preference, this
        is the page the key would print, and the layout would not object.
        """
        assert self._cell_mm(FIRST_SIX_UP_BREACH, SIX_UP, heading) < ANSWER_FLOOR_MM

    @pytest.mark.parametrize("heading", [None, "Easy"])
    def test_the_four_up_page_the_rule_gives_it_instead_clears_the_floor(
        self, heading: Optional[str]
    ) -> None:
        """And the page INV-011 does give that answer is above the floor."""
        assert self._cell_mm(FIRST_SIX_UP_BREACH, FOUR_UP, heading) >= ANSWER_FLOOR_MM

    def test_the_threshold_is_conservative_and_this_is_by_how_much(self) -> None:
        """20 is not the tight bound, and the rationale must not read as one.

        Sides 21..24 still clear the floor six-up; the first that does not is
        :data:`FIRST_SIX_UP_BREACH`, so the rule stands four cells clear of the
        edge. The tightest admitted case is a headed 24x24 at 3.1993 mm — a
        0.009 mm margin — which is why the threshold is not put there. A
        profile change that eats the headroom moves this number and is caught.
        """
        breaches = [
            side
            for side in range(SIX_UP_LONGEST_SIDE, MAX_SIZE + 1)
            if self._cell_mm(side, SIX_UP, "Easy") < ANSWER_FLOOR_MM
        ]
        assert breaches, "no square answer in range breaks the floor six-up"
        assert breaches[0] == FIRST_SIX_UP_BREACH
        assert SIX_UP_LONGEST_SIDE < breaches[0]


# --------------------------------------------------------------------------
# AC-268 / AC-269 — the caption
# --------------------------------------------------------------------------

#: AC-268's book: seven puzzles, the seventh named "Snowflake".
_SNOWFLAKE = 7


def _snowflake_book(titles: Optional[dict] = None) -> Tuple[List[dict], Book]:
    """Seven easy 15x15s, puzzle 7 named "Snowflake"; ``titles`` is the column."""
    puzzles = [
        _puzzle(15, 15, number=number, name="Snowflake" if number == _SNOWFLAKE else None)
        for number in range(1, _SNOWFLAKE + 1)
    ]
    return puzzles, _book(titles)


class TestBookAnswerKey_CaptionPuzzleNumberAndTitle:
    """AC-268 — puzzle 7 is named "Snowflake" and has no custom book title.

    Its caption reads "Puzzle 7 — Snowflake", with an em dash.
    """

    def test_answer_seven_is_captioned_with_its_number_and_its_name(self) -> None:
        puzzles, book = _snowflake_book()
        key = answer_key_of(_interior(puzzles, book), len(puzzles))

        # Answer 7 is the only answer on the second page of a seven-answer key.
        assert len(key) == 2
        assert key[1].tobytes() == expected_answer_page(
            [(puzzles[_SNOWFLAKE - 1], "Puzzle 7 — Snowflake")],
            SIX_UP,
            3 + len(puzzles) + 1,
            None,
            book,
        ).tobytes()

    def test_the_caption_is_ink_the_page_would_not_have_without_it(self) -> None:
        """The control: drop the caption and the page stops matching.

        Without it the comparison above would pass just as well against a page
        whose tiles were captioned with empty strings.
        """
        puzzles, book = _snowflake_book()
        page = answer_key_of(_interior(puzzles, book), len(puzzles))[1]
        uncaptioned = expected_answer_page(
            [(puzzles[_SNOWFLAKE - 1], "")], SIX_UP, 3 + len(puzzles) + 1, None, book
        )

        assert page.tobytes() != uncaptioned.tobytes()

    def test_a_puzzle_with_no_name_at_all_is_captioned_by_its_number(self) -> None:
        """This card's documented decision: no title, no em dash, no crash.

        A dash with nothing after it reads as a broken caption rather than as
        one that says less, and the number alone is the whole of what the key
        is looked up by.
        """
        puzzles = [
            _puzzle(15, 15, number=1, name=None),
            _puzzle(15, 15, number=2, name=""),
            _puzzle(15, 15, number=3, name="   "),
        ]
        for puzzle in puzzles[:1]:
            puzzle["puzzle_name"] = None
        key = answer_key_of(_interior(puzzles), len(puzzles))

        expected = expected_answer_page(
            [
                (puzzle, UNTITLED_CAPTION.format(number=number))
                for number, puzzle in enumerate(puzzles, start=1)
            ],
            SIX_UP,
            3 + len(puzzles),
            "Easy",
        )
        assert key[0].tobytes() == expected.tobytes()


class TestBookAnswerKey_CaptionUsesCustomBookTitle:
    """AC-269 — puzzle 7 is named "Snowflake" but titled "Winter Star" in the book.

    The per-book title set on the Arrangement step wins (FR-041,
    ``books.puzzle_titles``); the puzzle's own name is not printed at all.
    """

    def test_the_custom_book_title_is_what_the_caption_prints(self) -> None:
        puzzles, book = _snowflake_book({f"p{_SNOWFLAKE}": "Winter Star"})
        key = answer_key_of(_interior(puzzles, book), len(puzzles))

        assert key[1].tobytes() == expected_answer_page(
            [(puzzles[_SNOWFLAKE - 1], "Puzzle 7 — Winter Star")],
            SIX_UP,
            3 + len(puzzles) + 1,
            None,
            book,
        ).tobytes()

    def test_the_puzzles_own_name_is_not_what_is_printed(self) -> None:
        """The control: the same page captioned with the name does not match."""
        puzzles, book = _snowflake_book({f"p{_SNOWFLAKE}": "Winter Star"})
        page = answer_key_of(_interior(puzzles, book), len(puzzles))[1]

        assert page.tobytes() != expected_answer_page(
            [(puzzles[_SNOWFLAKE - 1], "Puzzle 7 — Snowflake")],
            SIX_UP,
            3 + len(puzzles) + 1,
            None,
            book,
        ).tobytes()

    def test_a_title_set_for_another_puzzle_leaves_this_one_alone(self) -> None:
        """A column keyed by puzzle id, not by position."""
        puzzles, book = _snowflake_book({"p1": "Winter Star"})
        key = answer_key_of(_interior(puzzles, book), len(puzzles))

        assert key[1].tobytes() == expected_answer_page(
            [(puzzles[_SNOWFLAKE - 1], "Puzzle 7 — Snowflake")],
            SIX_UP,
            3 + len(puzzles) + 1,
            None,
            book,
        ).tobytes()


# --------------------------------------------------------------------------
# AC-268, the half a page comparison cannot see — G-1a
# --------------------------------------------------------------------------

#: A codepoint no typeface carries: the last of the BMP, permanently unassigned
#: by Unicode. Whatever face is in force rasterizes it to that face's
#: ``.notdef`` glyph, so it is the control every "is this character really
#: drawn?" question here is asked against.
UNMAPPED = "￿"


class TestBookAnswerKey_CaptionSeparatorIsADrawnGlyph:
    """AC-268's em dash is a *dash* on paper, not a ``.notdef`` box (G-1a).

    Why this is a test of its own, and not covered by the caption ACs above
    -------------------------------------------------------------------------
    Every other caption assertion in this module compares the generator's page
    with a page drawn by the same renderer through
    :func:`~nonogram.export.png.render_answer_page`. If the face those two
    share has no glyph for U+2014, **both** sides print the same box in the
    same place and agree — which is exactly how the defect G-1a rules on
    shipped: the key was captioned "Puzzle 7 ▯ Snowflake" on paper with the
    whole suite green. The question that comparison cannot ask is whether the
    separator's ink is the separator's, so it is asked here instead, against
    :data:`UNMAPPED`.

    Both measurements are taken off the rendered page and neither knows which
    face drew it: one is a page comparison against the same caption carrying
    :data:`UNMAPPED` in the dash's place, the other is the shape of the ink
    the separator itself contributes — an em dash is a flat horizontal bar,
    far wider than it is tall, and a ``.notdef`` is an upright hollow box.
    """

    #: Where the separator's ink must be wider than tall for a dash, and is
    #: not for a box. The packaged face measures roughly 11:1 for U+2014 and
    #: 0.6:1 for its ``.notdef``, so the threshold is nowhere near either.
    DASH_ASPECT = 3.0

    NAME = "Snowflake"
    NUMBER = 7

    @staticmethod
    def _page(caption: str) -> Image.Image:
        """One six-up answer page carrying a single answer under ``caption``.

        Drawn straight through COMP-007 rather than through the generator: the
        caption *text* is what this class varies, and the generator composes
        that text itself.
        """
        return render_answer_page(
            [(_grid(15, 15), caption)],
            SIX_UP,
            book_page_spec(_book(), 4),
        )

    @classmethod
    def _separator_ink(cls, separator: str) -> Tuple[int, int]:
        """The ``(width, height)`` in pixels of the ink ``separator`` adds.

        Isolated by difference rather than by cropping: the same page is drawn
        with the caption and with an empty caption — which prints nothing and
        still occupies its line, so the geometry is identical — and what
        differs is the caption's ink and nothing else. Narrowing the caption to
        the separator alone then leaves the separator's own ink.
        """
        drawn = _ink(cls._page(separator))
        blank = _ink(cls._page(""))
        mark = drawn != blank
        rows = np.flatnonzero(mark.any(axis=1))
        columns = np.flatnonzero(mark.any(axis=0))
        assert rows.size and columns.size, f"{separator!r} drew nothing at all"
        return (
            int(columns[-1] - columns[0] + 1),
            int(rows[-1] - rows[0] + 1),
        )

    def test_the_em_dash_is_ink_an_unmapped_codepoint_would_not_have_made(
        self,
    ) -> None:
        """The whole caption, against the same caption with U+FFFF in its place.

        The one assertion the rest of the module structurally cannot make. A
        face without U+2014 draws these two pages identically, because it draws
        the same ``.notdef`` box for both characters; a face that carries it
        cannot.
        """
        caption = CAPTION.format(number=self.NUMBER, title=self.NAME)
        tofu = caption.replace("—", UNMAPPED)
        assert tofu != caption, "the caption under test carries no em dash"

        assert self._page(caption).tobytes() != self._page(tofu).tobytes()

    def test_the_separator_prints_as_a_bar_and_the_unmapped_one_does_not(
        self,
    ) -> None:
        """The positive half: the drawn shape is a dash's, not a box's.

        Page inequality alone would be satisfied by *any* second glyph. An em
        dash is a rule — one flat horizontal stroke about one em long — so its
        ink is several times wider than it is tall, while a ``.notdef`` box is
        an upright rectangle that is not.
        """
        dash_width, dash_height = self._separator_ink("—")
        box_width, box_height = self._separator_ink(UNMAPPED)

        assert dash_width >= self.DASH_ASPECT * dash_height, (
            f"U+2014 drew {dash_width}x{dash_height} px — not a dash's flat bar"
        )
        assert box_width < self.DASH_ASPECT * box_height, (
            f"U+FFFF drew {box_width}x{box_height} px — the control is not a box"
        )

    def test_the_face_is_the_packaged_one_the_pdf_header_already_uses(self) -> None:
        """ADR-0006/R1's static asset, addressed once for the whole project.

        ``png`` spells the resource out again instead of importing it, because
        ``pdf`` imports ``png`` and the edge only runs one way. This pins the
        two spellings equal so they cannot drift to two different files.
        """
        assert (png.FONT_PACKAGE, png.FONT_RESOURCE) == (
            pdf.FONT_PACKAGE,
            pdf.FONT_RESOURCE,
        )


# --------------------------------------------------------------------------
# AC-270 — the default plan's 150 puzzles take 30 answer pages
# --------------------------------------------------------------------------


class TestBookAnswerKey_DefaultPlanTakesThirtyPages:
    """AC-270 (INV-011) — 150 puzzles, BK-8's 90 / 60 split, all of one tier.

    Puzzles 1-90 are at most 20 on the longest side and 91-150 longer, so the
    key is 15 six-up pages and then 15 four-up pages: **30**, where one page
    per answer would take 150. The SOLUTIONS divider is not counted.

    The interior is not rendered: 150 puzzle pages and 30 answer pages of ink
    would make this the slowest test in the suite and would measure CARD-127's
    pairing walk rather than this card's. What is exercised is the generator's
    own answer walk over the same 150 payloads — the call
    :meth:`BookPDFGenerator.interior` itself makes — and the counts are
    checked against a rendered book of the same shape at a size that can be
    drawn (:meth:`test_the_same_shape_scaled_down_really_prints_that_many`).
    """

    SMALL = 90
    LARGE = 60
    PAGES = 30

    @staticmethod
    def _payloads(small: int, large: int) -> list:
        puzzles = _book_of(
            *([(15, 15)] * small + [(25, 25)] * large),
        )
        return [BookPDFGenerator._payload(puzzle) for puzzle in puzzles]

    def test_the_default_plan_packs_into_thirty_answer_pages(self) -> None:
        key = BookPDFGenerator(_book()).answer_key(self._payloads(self.SMALL, self.LARGE))

        assert len(key) == self.PAGES
        assert [page.capacity for page in key] == [SIX_UP] * 15 + [FOUR_UP] * 15
        assert [len(page.answers) for page in key] == [SIX_UP] * 15 + [FOUR_UP] * 15

    def test_every_one_of_the_hundred_and_fifty_answers_appears_once_in_order(
        self,
    ) -> None:
        key = BookPDFGenerator(_book()).answer_key(self._payloads(self.SMALL, self.LARGE))
        printed = [number for page in key for number in page.numbers]

        assert printed == list(range(1, self.SMALL + self.LARGE + 1))

    def test_the_same_shape_scaled_down_really_prints_that_many(self) -> None:
        """Six small answers then four large ones: a six-up page and a four-up one.

        The rendered half of this AC — the same 90 / 60 shape at a tenth of the
        size, so the interior can be drawn and counted as pages rather than as
        the walk's verdict.
        """
        puzzles = _book_of(*([(15, 15)] * 6 + [(25, 25)] * 4))
        key = answer_key_of(_interior(puzzles), len(puzzles))

        assert len(key) == 2
        assert len(answer_grids(key[0])) == SIX_UP
        assert len(answer_grids(key[1])) == FOUR_UP


# --------------------------------------------------------------------------
# AC-290 / AC-291 — levels
# --------------------------------------------------------------------------


class TestBookAnswerKey_EachLevelStartsNewAnswerPage:
    """AC-290 (INV-011) — 4 easy then 3 medium 15x15s make two answer pages.

    The medium level opens a page of its own although the first page had room
    for two more answers. No answer page holds two levels.
    """

    TIERS = ["easy"] * 4 + ["medium"] * 3

    def test_the_medium_level_starts_a_new_page_although_the_first_had_room(
        self,
    ) -> None:
        puzzles = _book_of(*[(15, 15)] * len(self.TIERS), tiers=self.TIERS)
        key = answer_key_of(_interior(puzzles), len(puzzles))
        first_page = 3 + len(puzzles)

        assert len(key) == 2
        assert key[0].tobytes() == expected_answer_page(
            captioned(puzzles, (1, 2, 3, 4)), SIX_UP, first_page, "Easy"
        ).tobytes()
        assert key[1].tobytes() == expected_answer_page(
            captioned(puzzles, (5, 6, 7)), SIX_UP, first_page + 1, "Medium"
        ).tobytes()

    def test_the_first_page_really_had_room(self) -> None:
        """The premise: the same seven answers, all one level, take one page.

        Without this, "the first had room for 2 more" would be an assertion
        about arithmetic nobody ran.
        """
        one_level = _book_of(*[(15, 15)] * len(self.TIERS))
        key = answer_key_of(_interior(one_level), len(one_level))

        assert len(key) == 2
        assert len(answer_grids(key[0])) == SIX_UP

    def test_neither_page_shows_more_answers_than_its_level_has(self) -> None:
        puzzles = _book_of(*[(15, 15)] * len(self.TIERS), tiers=self.TIERS)
        key = answer_key_of(_interior(puzzles), len(puzzles))

        assert [len(answer_grids(page)) for page in key] == [4, 3]


class TestBookAnswerKey_HeadingOnlyOnLevelFirstPage:
    """AC-291 — 8 easy then 1 medium: "Easy", nothing, "Medium".

    The heading marks where a level begins, so it is on the first page of the
    level's run and on no other.
    """

    TIERS = ["easy"] * 8 + ["medium"]

    @staticmethod
    def _key() -> Tuple[List[dict], List[Image.Image]]:
        tiers = TestBookAnswerKey_HeadingOnlyOnLevelFirstPage.TIERS
        puzzles = _book_of(*[(15, 15)] * len(tiers), tiers=tiers)
        return puzzles, answer_key_of(_interior(puzzles), len(puzzles))

    @pytest.mark.parametrize(
        "offset,numbers,heading",
        [
            (0, (1, 2, 3, 4, 5, 6), "Easy"),
            (1, (7, 8), None),
            (2, (9,), "Medium"),
        ],
    )
    def test_each_page_carries_its_own_heading_and_no_other(
        self, offset: int, numbers: Tuple[int, ...], heading: Optional[str]
    ) -> None:
        puzzles, key = self._key()
        expected = expected_answer_page(
            captioned(puzzles, numbers), SIX_UP, 3 + len(puzzles) + offset, heading
        )
        assert len(key) == 3
        assert key[offset].tobytes() == expected.tobytes()

    def test_a_headed_page_carries_a_line_of_type_an_unheaded_one_does_not(
        self,
    ) -> None:
        """The heading is ink, and it costs a line: measured off the pages.

        Above its first answer a headed page carries **two** lines of type —
        the heading and the first tile's caption — and an unheaded page one.
        Its tiles start lower for the same reason. That is the structural half
        of the byte comparisons above: it shows each heading is drawn, not
        merely reserved, without knowing what a heading is worth in
        millimetres.
        """
        _, key = self._key()

        assert [text_lines_above_the_first_grid(page) for page in key] == [2, 1, 2]
        assert answer_grids(key[0])[0][0] > answer_grids(key[1])[0][0], (
            "a heading costs the page a line"
        )
        assert answer_grids(key[2])[0][0] == answer_grids(key[0])[0][0]


# --------------------------------------------------------------------------
# AC-292 — the SOLUTIONS divider
# --------------------------------------------------------------------------


class TestBookAnswerKey_SolutionsDividerPrecedesAnswerKey:
    """AC-292 — a book of 3 easy 15x15s: guide, 3 puzzles, SOLUTIONS, the key.

    The divider carries only that word: no band, no number, no heading and no
    answer. It is one trim-size page, immediately after the last puzzle page
    and immediately before the first answer page.
    """

    PUZZLES = 3

    def test_the_page_between_the_puzzles_and_the_key_is_the_solutions_page(
        self,
    ) -> None:
        puzzles = _book_of(*[(15, 15)] * self.PUZZLES)
        book = _book()
        pages = _interior(puzzles, book)
        divider = 2 + self.PUZZLES

        assert len(pages) == divider + 1, "guide, 3 puzzles, divider, one answer page"
        assert pages[divider - 1].tobytes() == BookPDFGenerator(
            book
        ).create_divider_page(divider).tobytes()

    def test_the_divider_carries_that_word_and_nothing_else(self) -> None:
        """Measured, not compared: one short line of type, centred, no grid.

        The comparison above would be satisfied by a divider that had grown a
        band or a heading, since it would have grown one on both sides.
        """
        puzzles = _book_of(*[(15, 15)] * self.PUZZLES)
        pages = _interior(puzzles)
        divider = pages[2 + self.PUZZLES - 1]

        assert is_divider(divider)
        assert not answer_grids(divider)
        blank = Image.new("RGB", divider.size, "white")
        assert divider.tobytes() != blank.tobytes(), "the divider is blank"

    def test_the_page_before_is_a_puzzle_page_and_the_page_after_is_the_key(
        self,
    ) -> None:
        puzzles = _book_of(*[(15, 15)] * self.PUZZLES)
        pages = _interior(puzzles)
        divider = 2 + self.PUZZLES

        assert not is_divider(pages[divider - 2]), "the page before is a divider too"
        assert answer_grids(pages[divider]), "the page after carries no answer"

    def test_a_book_with_no_puzzles_has_no_divider_and_no_key(self) -> None:
        pages = _interior([])
        assert len(pages) == 1, "the guide page alone"


# --------------------------------------------------------------------------
# The counts the Increment 15 checkpoint reads
# --------------------------------------------------------------------------


class TestBookAnswerKey_ReportsItsAnswerPageCount:
    """FR-042 §4 — the answer-key page count, the divider not counted.

    Reported beside the interior's page count so the checkpoint can state the
    saving without reopening the file, and cross-checked here against the
    pages the export really wrote.
    """

    def test_the_reported_count_is_the_pages_after_the_divider(self) -> None:
        puzzles = _book_of(*[(15, 15)] * 12)
        interior = BookPDFGenerator(_book()).interior(puzzles)

        assert interior.answer_page_count == len(
            answer_key_of(interior.pages, len(puzzles))
        )
        assert interior.answer_page_count == 2

    def test_pairing_is_the_only_thing_the_saving_measures(self) -> None:
        """``pages_saved`` counts two-up pages, never the packed key.

        These puzzles never pair, so nothing is saved — although the key is
        ten pages shorter than one page per answer would have been. A
        ``unpaired_page_count`` that counted the un-packed key would report 10.
        """
        puzzles = _book_of(*[(15, 15)] * 12)
        interior = BookPDFGenerator(_book()).interior(puzzles)

        assert interior.pages_saved == 0
        assert interior.unpaired_page_count == interior.page_count

    def test_the_export_carries_the_same_count(self) -> None:
        puzzles = _book_of(*[(15, 15)] * 12)
        export = BookPDFGenerator(_book()).export_book(puzzles, "Winter Pictures")

        assert export.answer_page_count == 2
        assert export.interior_page_count == 1 + 12 + 1 + 2


# --------------------------------------------------------------------------
# What a malformed member does to the key
# --------------------------------------------------------------------------


class TestBookAnswerKey_AMemberThatCannotBeMeasuredIsNamed:
    """An answer that cannot be laid out aborts the export, naming the puzzle.

    The same failure contract the pairing walk keeps (CARD-127): a book that is
    quietly one answer short is worse than an export that says which row it
    could not print. The id is what the message carries, because it is the only
    handle a 120-puzzle book can be searched by.
    """

    def test_a_ragged_grid_aborts_the_export_naming_the_puzzle(self) -> None:
        puzzle = _puzzle(15, 15, number=4)
        puzzle["grid"] = [row[:] for row in puzzle["grid"]]
        puzzle["grid"][2] = puzzle["grid"][2][:-1]

        with pytest.raises(RuntimeError) as raised:
            _interior([puzzle])

        assert "'p4'" in str(raised.value)

    @pytest.mark.parametrize("grid", [[], [[]]])
    def test_an_empty_grid_aborts_the_export_naming_the_puzzle(self, grid) -> None:
        puzzle = _puzzle(15, 15, number=9)
        puzzle["grid"] = grid

        with pytest.raises(RuntimeError) as raised:
            _interior([puzzle])

        assert "'p9'" in str(raised.value)


class TestBookAnswerKey_TheExtentReaderAgreesWithTheRenderer:
    """The two grid measurements the key depends on, compared to each other.

    ``book_pdf_generator._answer_extent`` decides which tiling a page gets
    (INV-011) and ``png._answer_extent`` decides how the page is drawn. They
    are two implementations on purpose — ``export/`` exposes no public call
    that measures a grid, and the project reimplements rather than imports
    across a capability boundary — so nothing but a test keeps them from
    drifting into two different answers about one grid. That is what this
    class is: both readers, the same grids, in both directions.

    The generator's *type* check has no counterpart and is not compared here:
    a payload's grid arrives off a database row, and a row that is not rows of
    cells must be named and refused before any renderer sees it.
    """

    @staticmethod
    def _payload(grid: object):
        """A payload carrying ``grid``, exactly as the generator builds one."""
        return BookPDFGenerator._payload({"grid": grid})

    @pytest.mark.parametrize("columns,rows", [(10, 10), (20, 15), (15, 20), (30, 30)])
    def test_both_readers_measure_a_well_formed_grid_the_same_way(
        self, columns: int, rows: int
    ) -> None:
        grid = _grid(columns, rows, mark=1)

        assert book_pdf_generator._answer_extent(self._payload(grid), 1) == (
            columns,
            rows,
        )
        assert png._answer_extent(grid, 0) == (columns, rows)

    @pytest.mark.parametrize(
        "grid",
        [
            pytest.param([[True] * 15, [True] * 14], id="ragged"),
            pytest.param([], id="no-rows"),
            pytest.param([[]], id="one-empty-row"),
        ],
    )
    def test_a_grid_the_generator_refuses_is_refused_by_the_renderer_too(
        self, grid: list
    ) -> None:
        with pytest.raises(ValueError):
            book_pdf_generator._answer_extent(self._payload(grid), 4)

        with pytest.raises(ValueError):
            render_answer_page([(grid, "")], SIX_UP, book_page_spec(_book(), 4))


# --------------------------------------------------------------------------
# The supported grid range, end to end
# --------------------------------------------------------------------------


class TestBookAnswerKey_EverySupportedSizePrints:
    """CON-011's range, at both ends, through the whole export.

    :data:`~nonogram.limits.MIN_SIZE` is six-up and
    :data:`~nonogram.limits.MAX_SIZE` is four-up, and both draw.
    """

    @pytest.mark.parametrize(
        "side,capacity", [(MIN_SIZE, SIX_UP), (MAX_SIZE, FOUR_UP)]
    )
    def test_a_book_of_one_size_packs_at_its_capacity(
        self, side: int, capacity: int
    ) -> None:
        puzzles = _book_of(*[(side, side)] * capacity)
        # No ``puzzle_count``: a book of 10x10s pairs two-up (FR-040), so where
        # the divider lands is CARD-127's business and not this test's.
        key = answer_key_of(_interior(puzzles))

        assert len(key) == 1
        assert len(answer_grids(key[0])) == capacity
