"""CARD-128 — the printed book's levels (FR-041, INV-009, TERM-031, ADR-0037).

    AC-253  TestBookPdf_DifficultyOrderWithDividerPerLevel
    AC-254  TestBookPdf_DividerPageCarriesLevelNameOnly
    AC-255  TestBookPdf_DividerPagesDoNotConsumePuzzleNumbers
    AC-256  TestBookPdf_EmptyLevelHasNoDivider
    AC-260  TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel
    AC-293  TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages

AC-287 belongs to the interior's parity and lives with the rest of it, in
``tests/test_book_pdf.py`` (``TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1``).

How a page is identified without an OCR this project does not have
------------------------------------------------------------------
Every claim here is about **which page is where**, so every page is named by
measuring or by re-rendering it, never by trusting the generator's own plan.

*A puzzle page* is identified whole: the page COMP-007 draws for that puzzle's
payload, with the picture's name cleared and a band line this module writes out
from ADR-0037's wording, is compared with the page the interior holds. Two
pages differing by one clue, one band character or one page's parity differ in
their pixels, so the comparison names the puzzle **and** its print number at
once — the technique ``tests/test_book_pdf_band.py`` reads a band with
(CARD-117).

*A divider page* is identified in two independent steps, because the two halves
of AC-254 are different claims:

* **"and nothing else"** is measured off the page's own ink
  (:func:`is_divider`): one band of inked rows, no block wide and tall enough
  to be a drawing, and under a thousandth of the page inked. A page carrying a
  band, a page number, a grid or a second line fails it, and nothing in that
  measurement knows what a divider is supposed to look like.
* **"its level's name"** is a comparison against the divider pages of the four
  words the interior can print — "Easy", "Medium", "Hard" and "SOLUTIONS" —
  built by :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.create_divider_page`
  itself. Exactly one of the four must match, which is a statement about the
  word this card **chooses** for the page rather than about the ink a word
  makes; that the four are four different pages is asserted in
  :class:`TestBookPdf_DividerPageCarriesLevelNameOnly` before any of them is
  used to name a page, so the comparison is shown to discriminate rather than
  assumed to.

The book is CON-018's Book 1 profile throughout, written out in millimetres
rather than imported. Its puzzles are 20x20 with 3-deep clue gutters, so no two
of them ever share a page (FR-040, CARD-127) and the interior's make-up is one
page per puzzle — which is what lets these tests count pages. Each puzzle's
grid carries a different extra cell, so two puzzles of the same extent are
different pictures with different clues and a page holding the wrong one is
visible.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.export import ExportPayload
from nonogram.export.pdf import render_pages

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out rather than imported.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4

#: A pixel darker than this (0..255 grey) is ink.
INK_LEVEL = 128

#: ADR-0037's band, restated: "Puzzle 12 · Easy", the dot U+00B7 with a space
#: either side. Written out rather than imported from ``band_identity``, so the
#: expected line is a second implementation of the rule (CLAUDE.md).
BAND_TEMPLATE = "Puzzle {number} · {tier}"

#: The three level names a divider can carry (ADR-0031's three tiers, as
#: AC-020 displays them), and the fourth word the interior's other divider
#: carries (AC-292).
LEVEL_NAMES = ("Easy", "Medium", "Hard")
SOLUTIONS = "SOLUTIONS"


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book() -> Book:
    """A book on CON-018's Book 1 profile, as a ``books`` row carries it."""
    return Book(
        book_id="book-128",
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
    )


def _grid(columns: int, rows: int, depth: int = 3, mark: int = 0) -> List[List[bool]]:
    """A grid with ``depth``-deep clues and one extra cell chosen by ``mark``.

    The extra cell is what makes two puzzles of one extent two different
    pictures, with different clues, so a page holding the wrong one of them
    fails a comparison.
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
    name: str,
    tier: object,
    columns: int = 20,
    rows: int = 20,
    mark: int = 0,
) -> dict:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _grid(columns, rows, mark=mark)
    found = clues.compute_clues(grid)
    return {
        "id": name,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": tier,
    }


def _book_of(*members: Tuple[str, str]) -> List[dict]:
    """A book's rows from ``(name, stored tier)`` pairs, each a different picture."""
    return [
        _puzzle(name, tier, mark=index) for index, (name, tier) in enumerate(members)
    ]


def _interior(puzzles: Sequence[dict]) -> List[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``."""
    return BookPDFGenerator(_book()).interior_pages(list(puzzles))


# --------------------------------------------------------------------------
# Naming a page
# --------------------------------------------------------------------------


def expected_puzzle_page(puzzle: dict, page_number: int, number: int, tier: str):
    """The page COMP-007 draws for ``puzzle``, banded as this module says.

    The payload the generator builds from the row, with the picture's name
    cleared (ADR-0037/R1) and the band line written out here, laid out on the
    sheet of interior page ``page_number`` — so comparing it with the interior's
    page asserts the puzzle, its print number, its tier label and its parity
    together.
    """
    payload = ExportPayload(
        grid=puzzle["grid"],
        row_clues=tuple(tuple(clue) for clue in puzzle["clues_rows"]),
        column_clues=tuple(tuple(clue) for clue in puzzle["clues_cols"]),
        seed=0,
        mode="random",
        width=puzzle["width"],
        height=puzzle["height"],
        name=None,
        difficulty=BAND_TEMPLATE.format(number=number, tier=tier),
    )
    blank, _ = render_pages(payload, page_spec=book_page_spec(_book(), page_number))
    return blank


def divider_page(page_number: int, text: str) -> Image.Image:
    """A divider page carrying ``text``, on the sheet of interior ``page_number``."""
    return BookPDFGenerator(_book()).create_divider_page(page_number, text)


def _ink(page: Image.Image) -> np.ndarray:
    return np.asarray(page.convert("L")) < INK_LEVEL


def _row_bands(present: Sequence[bool]) -> List[Tuple[int, int]]:
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


#: How large a block of ink must be, in both axes, to be a puzzle's drawing
#: rather than a line of type — a share of the page. The smallest drawing a
#: book page carries is far above it and a line of type far below.
_DRAWING_SHARE = 0.1


def _carries_a_drawing(page: Image.Image) -> bool:
    """Whether ``page`` holds a block of ink large enough to be a drawing."""
    mask = _ink(page)
    least_wide = page.width * _DRAWING_SHARE
    least_tall = page.height * _DRAWING_SHARE
    for top, bottom in _row_bands(mask.any(axis=1)):
        if bottom - top + 1 < least_tall:
            continue
        strip = mask[top : bottom + 1]
        if any(
            right - left + 1 >= least_wide
            for left, right in _row_bands(strip.any(axis=0))
        ):
            return True
    return False


def is_divider(page: Image.Image) -> bool:
    """Whether ``page`` is a divider: one short line of type, and nothing else.

    Measured off the page and nothing else: one band of inked rows, no block of
    ink large enough to be a drawing, and under a thousandth of the page inked.
    A puzzle page fails on all three (its band is a second line, its grid is a
    block, and its ink is orders of magnitude more), and so does an answer page.
    """
    mask = _ink(page)
    return (
        len(_row_bands(mask.any(axis=1))) == 1
        and not _carries_a_drawing(page)
        and mask.sum() < page.width * page.height / 1000
    )


def divider_word(page: Image.Image, page_number: int) -> Optional[str]:
    """Which of the interior's four divider words ``page`` carries, if any.

    ``None`` when the page matches none of them — which is a failure worth
    reporting as "no word this interior prints", rather than one the caller has
    to spell out four times.
    """
    for word in (*LEVEL_NAMES, SOLUTIONS):
        if page.tobytes() == divider_page(page_number, word).tobytes():
            return word
    return None


def interior_shape(pages: Sequence[Image.Image]) -> List[str]:
    """Each interior page as ``"divider Easy"`` or ``"puzzle"``, in print order.

    The guide page (interior page 1) is left out: it is not part of the puzzle
    section and carries lines of its own text. Every other page is named by
    measurement — :func:`is_divider` first, then the word it carries.
    """
    shape: List[str] = []
    for number, page in enumerate(pages[1:], start=2):
        if is_divider(page):
            shape.append(f"divider {divider_word(page, number)}")
        else:
            shape.append("puzzle")
    return shape


# --------------------------------------------------------------------------
# AC-253 — the order, and the divider that opens each level
# --------------------------------------------------------------------------

#: AC-253's book: two easy, two medium and one hard 20x20, arranged in that
#: order already, so what is under test is the make-up of the pages and not the
#: grouping (that is AC-260's book).
AC253_MEMBERS = (
    ("E1", "easy"),
    ("E2", "easy"),
    ("M1", "medium"),
    ("M2", "medium"),
    ("H1", "hard"),
)

#: Where each of them prints, and under which band: interior page 1 is the
#: guide page, page 2 the "Easy" divider, and a divider costs a page and no
#: number. Written out here rather than computed, because it is the claim.
AC253_PAGES = (
    (3, 1, "Easy"),
    (4, 2, "Easy"),
    (6, 3, "Medium"),
    (7, 4, "Medium"),
    (9, 5, "Hard"),
)


class TestBookPdf_DifficultyOrderWithDividerPerLevel:
    """AC-253 (INV-009) — divider "Easy", E1, E2, divider "Medium", M1, M2, divider "Hard", H1."""

    @staticmethod
    def _pages() -> Tuple[List[dict], List[Image.Image]]:
        puzzles = _book_of(*AC253_MEMBERS)
        return puzzles, _interior(puzzles)

    def test_the_puzzle_section_runs_divider_then_that_levels_puzzles(self) -> None:
        _, pages = self._pages()

        assert interior_shape(pages[:9]) == [
            "divider Easy",
            "puzzle",
            "puzzle",
            "divider Medium",
            "puzzle",
            "puzzle",
            "divider Hard",
            "puzzle",
        ]

    def test_each_puzzle_page_is_the_puzzle_and_the_band_it_should_be(self) -> None:
        puzzles, pages = self._pages()

        for puzzle, (page_number, number, tier) in zip(puzzles, AC253_PAGES):
            expected = expected_puzzle_page(puzzle, page_number, number, tier)
            assert pages[page_number - 1].tobytes() == expected.tobytes(), (
                f"interior page {page_number} is not {puzzle['id']} banded "
                f"'Puzzle {number} · {tier}'"
            )

    def test_the_interior_is_that_section_between_the_guide_and_the_key(self) -> None:
        """The whole file: guide, the eight pages above, SOLUTIONS, the key.

        Five answers of 20x20 fit one six-up page per level, so the key is
        three pages — which is what makes 13 the interior's page count, and
        what the generator must have reported before it drew anything.
        """
        puzzles, pages = self._pages()
        stream = BookPDFGenerator(_book()).interior_stream(puzzles)

        assert len(pages) == 13
        assert stream.page_count == 13
        assert is_divider(pages[9]), "interior page 10 is the SOLUTIONS divider"
        assert divider_word(pages[9], 10) == SOLUTIONS
        assert stream.answer_page_count == 3
        assert not any(is_divider(page) for page in pages[10:])


# --------------------------------------------------------------------------
# AC-254 — what a divider page carries
# --------------------------------------------------------------------------


class TestBookPdf_DividerPageCarriesLevelNameOnly:
    """AC-254 — each divider page's only content is its level's name."""

    #: The three divider pages of AC-253's book, by interior position.
    DIVIDERS = ((2, "Easy"), (5, "Medium"), (8, "Hard"))

    def test_the_four_divider_words_are_four_different_pages(self) -> None:
        """The premise of every comparison below: the words discriminate.

        Four pages built the same way from four different words must be four
        different images, or "the page carries this word and not the others"
        would be a statement about nothing.
        """
        pages = {
            word: divider_page(2, word).tobytes()
            for word in (*LEVEL_NAMES, SOLUTIONS)
        }

        assert len(set(pages.values())) == 4, "two divider words draw one page"

    def test_each_divider_carries_its_own_level_name(self) -> None:
        pages = _interior(_book_of(*AC253_MEMBERS))

        for page_number, name in self.DIVIDERS:
            assert divider_word(pages[page_number - 1], page_number) == name

    def test_a_divider_carries_one_line_of_type_and_nothing_else(self) -> None:
        """No band, no number, no drawing — measured off the page (G-3)."""
        pages = _interior(_book_of(*AC253_MEMBERS))

        for page_number, name in self.DIVIDERS:
            page = pages[page_number - 1]
            mask = _ink(page)
            assert mask.any(), f"the {name} divider is blank"
            assert len(_row_bands(mask.any(axis=1))) == 1, (
                f"the {name} divider carries more than one line of type"
            )
            assert not _carries_a_drawing(page), f"the {name} divider carries a drawing"

    def test_a_puzzle_page_fails_the_same_measurement(self) -> None:
        """The control: the measurement above says "no" when there is more ink."""
        pages = _interior(_book_of(*AC253_MEMBERS))

        assert not is_divider(pages[2]), "a puzzle page reads as a divider"
        assert _carries_a_drawing(pages[2])


# --------------------------------------------------------------------------
# AC-255 — a divider consumes no puzzle number
# --------------------------------------------------------------------------


class TestBookPdf_DividerPagesDoNotConsumePuzzleNumbers:
    """AC-255 — 2 easy and 1 medium: the medium puzzle is "Puzzle 3 · Medium".

    Its page is interior page 6 — guide, Easy divider, two puzzles, Medium
    divider — so by the time it prints, three divider-and-guide pages have gone
    past and the number is still 3.
    """

    MEMBERS = (("E1", "easy"), ("E2", "easy"), ("M1", "medium"))

    def test_the_medium_puzzles_band_reads_puzzle_three_medium(self) -> None:
        puzzles = _book_of(*self.MEMBERS)
        pages = _interior(puzzles)

        expected = expected_puzzle_page(puzzles[2], 6, 3, "Medium")

        assert pages[5].tobytes() == expected.tobytes()

    def test_it_is_not_numbered_by_its_page(self) -> None:
        """The two ways of getting it wrong: numbering by page, or per level.

        Interior page 6 would be "Puzzle 6" if a divider consumed a number,
        and "Puzzle 1 · Medium" if numbering restarted inside a level.
        """
        puzzles = _book_of(*self.MEMBERS)
        page = _interior(puzzles)[5]

        for number in (6, 4, 1):
            assert page.tobytes() != expected_puzzle_page(
                puzzles[2], 6, number, "Medium"
            ).tobytes(), f"the medium puzzle prints as Puzzle {number}"

    def test_the_numbers_run_one_to_n_over_the_puzzles(self) -> None:
        puzzles = _book_of(*self.MEMBERS)
        pages = _interior(puzzles)

        for puzzle, page_number, number, tier in (
            (puzzles[0], 3, 1, "Easy"),
            (puzzles[1], 4, 2, "Easy"),
            (puzzles[2], 6, 3, "Medium"),
        ):
            expected = expected_puzzle_page(puzzle, page_number, number, tier)
            assert pages[page_number - 1].tobytes() == expected.tobytes()


# --------------------------------------------------------------------------
# AC-256 — an empty level has no divider
# --------------------------------------------------------------------------


class TestBookPdf_EmptyLevelHasNoDivider:
    """AC-256 — 3 easy and 2 medium, no hard: the PDF holds no "Hard" divider."""

    MEMBERS = (
        ("E1", "easy"),
        ("E2", "easy"),
        ("E3", "easy"),
        ("M1", "medium"),
        ("M2", "medium"),
    )

    def test_no_page_of_the_interior_is_a_hard_divider(self) -> None:
        pages = _interior(_book_of(*self.MEMBERS))

        words = [
            divider_word(page, number)
            for number, page in enumerate(pages, start=1)
            if is_divider(page)
        ]

        assert words == ["Easy", "Medium", SOLUTIONS]

    def test_the_interior_is_one_page_shorter_than_three_levels_would_make_it(
        self,
    ) -> None:
        """Guide, Easy, 3 puzzles, Medium, 2 puzzles, SOLUTIONS, 2 answer pages.

        Eleven pages, and a third level would have made it twelve. The key is
        two pages because each level starts one of its own (CARD-134), not
        because five answers overflow a six-up page.
        """
        pages = _interior(_book_of(*self.MEMBERS))

        assert len(pages) == 11
        assert interior_shape(pages[:8]) == [
            "divider Easy",
            "puzzle",
            "puzzle",
            "puzzle",
            "divider Medium",
            "puzzle",
            "puzzle",
        ]


# --------------------------------------------------------------------------
# AC-260 — a legacy mixed arrangement prints grouped
# --------------------------------------------------------------------------


class TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel:
    """AC-260 (INV-009) — stored M1, E1, H1, E2 prints E1, E2, M1, H1.

    The arrangement was saved before INV-009, so the list handed to the
    generator is mixed. Nothing about it is rewritten (G-1): what is asserted
    is the *pages*, and the stored list is checked afterwards to be the mixed
    one it was.
    """

    MEMBERS = (("M1", "medium"), ("E1", "easy"), ("H1", "hard"), ("E2", "easy"))

    #: The expected print order: which member of ``MEMBERS`` prints where, on
    #: which page and under which band.
    PRINTED = (
        (1, 3, 1, "Easy"),  # E1
        (3, 4, 2, "Easy"),  # E2
        (0, 6, 3, "Medium"),  # M1
        (2, 8, 4, "Hard"),  # H1
    )

    def test_the_puzzles_print_grouped_by_level(self) -> None:
        puzzles = _book_of(*self.MEMBERS)
        pages = _interior(puzzles)

        for index, page_number, number, tier in self.PRINTED:
            expected = expected_puzzle_page(
                puzzles[index], page_number, number, tier
            )
            assert pages[page_number - 1].tobytes() == expected.tobytes(), (
                f"{puzzles[index]['id']} does not print on interior page "
                f"{page_number} as Puzzle {number}"
            )

    def test_each_level_still_opens_with_its_own_divider(self) -> None:
        pages = _interior(_book_of(*self.MEMBERS))

        assert interior_shape(pages[:8]) == [
            "divider Easy",
            "puzzle",
            "puzzle",
            "divider Medium",
            "puzzle",
            "divider Hard",
            "puzzle",
        ]

    def test_the_stored_arrangement_is_left_as_it_was(self) -> None:
        """G-1: the grouping is a print-time decision and writes nothing back."""
        puzzles = _book_of(*self.MEMBERS)
        before = [puzzle["id"] for puzzle in puzzles]

        _interior(puzzles)

        assert [puzzle["id"] for puzzle in puzzles] == before
        assert before == ["M1", "E1", "H1", "E2"]


# --------------------------------------------------------------------------
# AC-293 — the default plan's answer key across three levels
# --------------------------------------------------------------------------


class TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages:
    """AC-293 (FR-042, INV-011) — 150 puzzles at 40/40/20 take 31 answer pages.

    ADR-0034's default plan with AC-198's prefill, level by level: easy 50
    answers at most 20 cells on the longest side and then 10 longer, medium 34
    then 26, hard 6 then 24. Because every level starts a page of its own
    (CARD-134), the key is easy 11 + medium 13 + hard 7 = **31** answer pages,
    after the one SOLUTIONS divider — 32 pages in all, where the same 150
    answers packed without level-first pages take 30 (AC-270).

    Counted, not rendered: 150 puzzle pages and 31 answer pages of ink would
    make this the slowest test in the suite. What is exercised is the answer
    walk the export itself makes over the same 150 payloads, plus — for the
    "after 1 SOLUTIONS page" half — the interior's own page plan, which knows
    all of its counts before a pixel exists.
    """

    #: (stored tier, small answers, large answers) per level, in book order.
    PLAN = (("easy", 50, 10), ("medium", 34, 26), ("hard", 6, 24))

    #: Each level's share of the key, and the total.
    PER_LEVEL = (11, 13, 7)
    PAGES = 31

    @staticmethod
    def _rows() -> List[dict]:
        """The 150 rows, in plan order: each level's small answers, then its large."""
        rows: List[dict] = []
        for tier, small, large in (
            TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages.PLAN
        ):
            for index in range(small):
                rows.append(
                    _puzzle(f"{tier}-s{index}", tier, 20, 20, mark=index)
                )
            for index in range(large):
                rows.append(
                    _puzzle(f"{tier}-l{index}", tier, 25, 25, mark=index)
                )
        return rows

    def test_the_book_is_the_default_plan(self) -> None:
        """The premise: 150 puzzles split 40 / 40 / 20 (ADR-0034, AC-198)."""
        rows = self._rows()
        counts = [small + large for _, small, large in self.PLAN]

        assert len(rows) == 150
        assert counts == [60, 60, 30]

    def test_the_key_is_thirty_one_pages_eleven_thirteen_and_seven(self) -> None:
        key = BookPDFGenerator(_book()).answer_key(
            [BookPDFGenerator._payload(row) for row in self._rows()]
        )
        per_level: List[int] = []
        for page in key:
            if page.heading is not None:
                per_level.append(0)
            per_level[-1] += 1

        assert len(key) == self.PAGES
        assert per_level == list(self.PER_LEVEL)
        assert [page.heading for page in key if page.heading] == list(LEVEL_NAMES)

    def test_every_one_of_the_hundred_and_fifty_answers_appears_once_in_order(
        self,
    ) -> None:
        key = BookPDFGenerator(_book()).answer_key(
            [BookPDFGenerator._payload(row) for row in self._rows()]
        )
        printed = [number for page in key for number in page.numbers]

        assert printed == list(range(1, 151))

    def test_the_key_follows_one_solutions_page_in_the_interiors_plan(self) -> None:
        """31 answer pages after 1 divider — and the whole interior's count.

        Guide + 3 level dividers + 150 puzzle pages + SOLUTIONS + 31 answers.
        """
        stream = BookPDFGenerator(_book()).interior_stream(self._rows())

        assert stream.answer_page_count == self.PAGES
        assert stream.page_count == 1 + 3 + 150 + 1 + self.PAGES
