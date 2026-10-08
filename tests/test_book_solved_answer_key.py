"""CARD-198 — the book's answer key becomes one full solved page per puzzle.

    AC-1  TestBookSolvedAnswerKey_OnePagePerPuzzleInBookOrder
    AC-2  TestBookSolvedAnswerKey_EachPageIsOnePuzzleSolvedWithClues
    AC-3  TestBookSolvedAnswerKey_PageCountIsOnePerPuzzleNotPacked
    AC-4  TestBookSolvedAnswerKey_LevelVisibleViaPerPageBandNoSeparateHeading
    AC-5  TestBookSolvedAnswerKey_AMemberThatCannotBeMeasuredIsStillNamed
    AC-7  TestBookSolvedAnswerKey_ParityHoldsAtTheNewPageCount

CARD-198 replaced the packed 6-up/4-up answer key (``book_answer_key``,
CARD-134) with one call to :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.solved_puzzle_page`
(CARD-197, reused verbatim — G-1) per drawable puzzle, in book order, behind
the unchanged SOLUTIONS divider. This module pins the generator's wiring —
that :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.interior_stream`
calls that primitive once per puzzle with the right arguments, in the right
place, the right number of times, and preserves the malformed-grid abort
contract — never CARD-197's own pixel-level drawing (that is
``tests/test_book_solved_page.py``'s job, and it is G-1's that this card does
not edit it).

**Puzzles here never pair.** Every puzzle is built with clue gutters 3 deep on
a 15x15 (or, for AC-7's larger book, 6 deep on a 22x22 — the same shape
``tests/test_book_finalise_gutter.py``'s own ``alone`` uses, chosen there for
exactly this reason), so FR-040's two-up pairing never shortens the puzzle
section and the interior's make-up is arithmetic, not a verdict of the pairing
walk. That is what lets :func:`first_answer_page` below predict exactly where
the answer section starts from the puzzle count and the level count alone.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import pytest
from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _as_planned,
    band_identity,
    page_is_right_hand,
)
from nonogram.admin.book_answer_key import answer_caption

from tests.helpers.page_ink import drawing_of

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out rather than imported.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4


def _cm(millimetres: float) -> str:
    return f"{millimetres / 10:.2f}"


def _book(puzzle_titles: Optional[dict] = None) -> Book:
    return Book(
        book_id="book-198",
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
    """A non-pairing solved grid, ``depth`` clue-entries deep (see module docstring)."""
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
    depth: int = 3,
    name: Optional[str] = None,
    tier: object = "easy",
) -> dict:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _grid(columns, rows, depth=depth, mark=number)
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


def _book_of(*sizes: Tuple[int, int], tiers: Sequence[object] = (), depth: int = 3) -> List[dict]:
    """A book's puzzles, numbered 1..n, from ``(columns, rows)`` pairs."""
    levels = list(tiers) or ["easy"] * len(sizes)
    return [
        _puzzle(columns, rows, number=index + 1, depth=depth, tier=levels[index])
        for index, (columns, rows) in enumerate(sizes)
    ]


def first_answer_page(book: Book, puzzles: Sequence[dict]) -> int:
    """Where the answer section's first page sits in the interior.

    Measured off the generator's own :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.section_plan`
    (the one seam CARD-140 built for exactly this question) rather than
    re-derived by counting levels and puzzles by hand, so this helper cannot
    silently disagree with the walk it is predicting.
    """
    section = BookPDFGenerator(book).section_plan(list(puzzles)).pages
    return 3 + len(section)


def _interior(puzzles: Sequence[dict], book: Optional[Book] = None) -> List[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``."""
    return BookPDFGenerator(book if book is not None else _book()).interior(
        list(puzzles)
    ).pages


# --------------------------------------------------------------------------
# AC-1 — one answer page per puzzle, in book order, behind the SOLUTIONS page
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_OnePagePerPuzzleInBookOrder:
    """AC-1 — N drawable puzzles make exactly N answer pages, numbered 1..N."""

    def test_the_answer_section_holds_exactly_one_page_per_puzzle(self) -> None:
        book = _book()
        puzzles = _book_of((15, 15), (15, 15), (15, 15), tiers=["easy"] * 3)
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)

        answer_pages = pages[start - 1 :]
        assert len(answer_pages) == len(puzzles) == 3

    def test_the_pages_print_in_book_order_one_to_n(self) -> None:
        """Each page's own band carries the puzzle number that page prints."""
        book = _book()
        puzzles = _book_of((15, 15), (15, 15), (15, 15), (15, 15), tiers=["easy"] * 4)
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)

        for offset, puzzle in enumerate(puzzles):
            page = pages[start - 1 + offset]
            expected = gen.solved_puzzle_page(
                gen._payload(puzzle), offset + 1, start + offset, title=puzzle["puzzle_name"]
            )
            assert page.tobytes() == expected.tobytes(), (
                f"answer page at offset {offset} is not puzzle {offset + 1}'s"
            )

    def test_a_book_with_no_puzzles_has_no_answer_section_at_all(self) -> None:
        pages = _interior([])
        assert len(pages) == 1, "the guide page alone"


# --------------------------------------------------------------------------
# AC-2 — each page matches a direct call to solved_puzzle_page
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_EachPageIsOnePuzzleSolvedWithClues:
    """AC-2 — interior_stream calls CARD-197's primitive correctly per puzzle.

    This pins the *wiring*: the band's number and tier, the caption's number
    and title (custom book title winning over the picture's own name,
    FR-041), the clues and the fill — all exactly what calling
    :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.solved_puzzle_page`
    directly with the same ``(payload, puzzle_number, page_number, title)``
    would draw. Not CARD-197's own pixel-level drawing — that is
    ``tests/test_book_solved_page.py``'s job (G-1).
    """

    def test_a_puzzle_with_its_own_name_matches_a_direct_call(self) -> None:
        book = _book()
        puzzles = _book_of((15, 15), (18, 12), tiers=["easy", "medium"])
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)

        for offset, puzzle in enumerate(puzzles):
            number = offset + 1
            expected = gen.solved_puzzle_page(
                gen._payload(puzzle), number, start + offset, title=puzzle["puzzle_name"]
            )
            assert pages[start - 1 + offset].tobytes() == expected.tobytes()

    def test_a_custom_book_title_wins_over_the_pictures_own_name(self) -> None:
        """FR-041: ``books.puzzle_titles`` beats ``puzzle_name`` in the caption."""
        puzzles = [
            _puzzle(15, 15, number=1, name="Snowflake", tier="easy"),
        ]
        book = _book({"p1": "Winter Star"})
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)

        expected = gen.solved_puzzle_page(
            gen._payload(puzzles[0]), 1, start, title="Winter Star"
        )
        assert pages[start - 1].tobytes() == expected.tobytes()

        # The control: captioned with the picture's own name, it must not match.
        uncustomised = gen.solved_puzzle_page(
            gen._payload(puzzles[0]), 1, start, title="Snowflake"
        )
        assert pages[start - 1].tobytes() != uncustomised.tobytes()

    def test_a_puzzle_with_no_name_at_all_is_still_captioned_by_number_alone(
        self,
    ) -> None:
        puzzle = _puzzle(15, 15, number=1, name=None, tier="easy")
        puzzle["puzzle_name"] = None
        book = _book()
        pages = _interior([puzzle], book)
        start = first_answer_page(book, [puzzle])
        gen = BookPDFGenerator(book)

        expected = gen.solved_puzzle_page(gen._payload(puzzle), 1, start, title=None)
        assert pages[start - 1].tobytes() == expected.tobytes()
        assert answer_caption(1, None) == "Puzzle 1"


# --------------------------------------------------------------------------
# AC-3 — the reported count is one per puzzle, and the guard still holds
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_PageCountIsOnePerPuzzleNotPacked:
    """AC-3 — ``answer_page_count`` is the drawable-puzzle count, unpacked."""

    def test_answer_page_count_equals_the_drawable_puzzle_count(self) -> None:
        book = _book()
        puzzles = _book_of(*[(15, 15)] * 9, tiers=["easy"] * 9)
        stream = BookPDFGenerator(book).interior_stream(puzzles)

        assert stream.answer_page_count == 9
        # The control this AC asks for explicitly: packed six-up would have
        # reported 2 for nine small same-tier answers (INV-011's old rule).
        assert stream.answer_page_count != 2

    def test_a_producer_short_of_its_planned_count_still_raises(self) -> None:
        """``_as_planned`` (CARD-145), unedited, still guards the real call.

        ``interior_page_count`` is monkeypatched to report one page more
        than the walk actually produces — the same shape a change to the
        answer term's arithmetic that forgot to update the plan would take —
        so the mismatch is caught by the unedited ``_as_planned`` guard
        exactly as it already does for the puzzle section
        (``tests/test_book_pdf_memory.py``).
        """
        import nonogram.admin.book_pdf_generator as bpg

        book = _book()
        puzzles = _book_of(*[(15, 15)] * 3, tiers=["easy"] * 3)
        real = bpg.interior_page_count

        def one_more(*args, **kwargs):
            return real(*args, **kwargs) + 1

        bpg.interior_page_count = one_more
        try:
            stream = BookPDFGenerator(book).interior_stream(puzzles)
            with pytest.raises(RuntimeError, match="its page plan says"):
                list(stream.pages)
        finally:
            bpg.interior_page_count = real

    def test_as_planned_itself_still_raises_on_an_undercount(self) -> None:
        """The guard's own unit shape, pinned directly (CARD-145, unedited)."""

        def two_pages():
            yield Image.new("RGB", (10, 10), "white")
            yield Image.new("RGB", (10, 10), "white")

        with pytest.raises(RuntimeError, match="interior has 2 pages"):
            list(_as_planned(two_pages(), 3))


# --------------------------------------------------------------------------
# AC-4 — the level is visible per page; no separate heading or divider
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_LevelVisibleViaPerPageBandNoSeparateHeading:
    """AC-4 — 2 easy then 1 medium: bands show it, no extra page or line does."""

    @staticmethod
    def _book_and_pages() -> Tuple[Book, List[dict], List[Image.Image]]:
        book = _book()
        puzzles = _book_of((15, 15), (15, 15), (15, 15), tiers=["easy", "easy", "medium"])
        return book, puzzles, _interior(puzzles, book)

    def test_pages_one_and_two_band_easy_and_page_three_bands_medium(self) -> None:
        book, puzzles, pages = self._book_and_pages()
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)

        for offset, tier in enumerate(("easy", "easy", "medium")):
            puzzle = puzzles[offset]
            expected = gen.solved_puzzle_page(
                gen._payload(puzzle), offset + 1, start + offset, title=puzzle["puzzle_name"]
            )
            assert pages[start - 1 + offset].tobytes() == expected.tobytes()
            # band_identity is what the page was asked to draw; confirm the
            # tier fed to it is the one this offset's puzzle actually carries.
            assert band_identity(offset + 1, puzzles[offset]["difficulty_tier"]).endswith(
                tier.capitalize()
            )

    def test_the_answer_section_opens_with_exactly_one_divider_the_solutions_one(
        self,
    ) -> None:
        """No per-level heading page inside the answer section (CARD-198)."""
        book, puzzles, pages = self._book_and_pages()
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)

        # The page immediately before the answer section is the SOLUTIONS
        # divider, built the same way every divider page is.
        assert pages[start - 2].tobytes() == gen.create_divider_page(start - 1).tobytes()

        # And every page from the first answer page on is a *puzzle* page —
        # built by solved_puzzle_page, never create_divider_page — so there
        # is no second divider hiding inside the answer run.
        for offset, puzzle in enumerate(puzzles):
            page = pages[start - 1 + offset]
            not_a_divider = gen.create_divider_page(start + offset, "Easy")
            assert page.tobytes() != not_a_divider.tobytes()

    def test_the_total_page_count_has_no_room_for_a_heading_page(self) -> None:
        """1 guide + 2 dividers + 3 puzzles + SOLUTIONS + 3 answers = 10.

        A per-level heading page inside the answer section (the alternative
        CARD-198's own "What to implement" considered and rejected) would
        make this 11 or 12 instead.
        """
        book, puzzles, pages = self._book_and_pages()
        assert len(pages) == 1 + 2 + 3 + 1 + 3 == 10


# --------------------------------------------------------------------------
# AC-5 — a malformed answer still aborts, before any page is drawn
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_AMemberThatCannotBeMeasuredIsStillNamed:
    """AC-5 — the "could not be laid out" abort contract survives CARD-198."""

    def test_a_ragged_grid_aborts_naming_the_puzzle_with_a_value_error_cause(
        self,
    ) -> None:
        puzzle = _puzzle(15, 15, number=4)
        puzzle["grid"] = [row[:] for row in puzzle["grid"]]
        puzzle["grid"][2] = puzzle["grid"][2][:-1]

        with pytest.raises(RuntimeError) as raised:
            BookPDFGenerator(_book()).interior_stream([puzzle])

        assert "'p4'" in str(raised.value)
        assert "could not be laid out" in str(raised.value)
        assert isinstance(raised.value.__cause__, ValueError)

    @pytest.mark.parametrize("grid", [[], [[]]])
    def test_an_empty_grid_aborts_the_same_way(self, grid: list) -> None:
        puzzle = _puzzle(15, 15, number=9)
        puzzle["grid"] = grid

        with pytest.raises(RuntimeError) as raised:
            BookPDFGenerator(_book()).interior_stream([puzzle])

        assert "'p9'" in str(raised.value)
        assert isinstance(raised.value.__cause__, ValueError)

    def test_the_abort_happens_before_interior_stream_even_returns(self) -> None:
        """Eager: the raise comes from the call itself, not from walking pages.

        A caller that never touches ``.pages`` still gets the abort — the
        same "refused before the file has a first byte" contract the plan
        tripwires keep (:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.interior_stream`'s
        own docstring).
        """
        good = _puzzle(15, 15, number=1)
        bad = _puzzle(15, 15, number=2)
        bad["grid"] = []

        with pytest.raises(RuntimeError, match="could not be laid out"):
            # No `.pages` ever consumed: if this raised lazily instead, the
            # call below would return an InteriorStream with no exception.
            BookPDFGenerator(_book()).interior_stream([good, bad])


# --------------------------------------------------------------------------
# AC-7 — parity still holds at the larger, one-per-puzzle page count
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_ParityHoldsAtTheNewPageCount:
    """AC-7 — page 1 is right-hand; every later page's parity is its position.

    The book is 12 puzzles of one tier, 22x22 with 6-deep clues (the same
    non-pairing shape ``tests/test_book_finalise_gutter.py``'s ``alone``
    uses), so the answer section alone is 12 pages — several more than the
    packed key would ever have made for 12 small same-tier answers (two,
    six-up) — which is the "beyond the old packed count" AC-7 asks for.
    """

    PUZZLES = 12

    def test_the_answer_section_is_longer_than_the_old_packed_count_would_be(
        self,
    ) -> None:
        book = _book()
        puzzles = _book_of(*[(22, 22)] * self.PUZZLES, depth=6, tiers=["easy"] * self.PUZZLES)
        start = first_answer_page(book, puzzles)
        pages = _interior(puzzles, book)

        answer_pages = pages[start - 1 :]
        assert len(answer_pages) == self.PUZZLES == 12
        # The old packed key would have put 12 same-tier, <=20-longest-side
        # answers on ceil(12 / 6) = 2 six-up pages.
        assert len(answer_pages) > 2

    def test_every_interior_pages_measured_side_matches_its_declared_parity(
        self,
    ) -> None:
        """Puzzle and answer pages via :func:`drawing_of`; page 1 off its own ink.

        Page 1 (the guide) and the SOLUTIONS/level divider pages carry no
        ruled grid for :func:`drawing_of` to measure, so each divider is
        skipped (``drawing_of`` itself raises on it — a page with no grid at
        all, never a silently wrong measurement) and the guide page's parity
        is read the same independent way
        ``tests/test_book_pdf_memory.py``'s own parity test reads it: the
        leftmost ink column, which sits at the gutter margin on a right-hand
        page and at the (narrower) outside margin on a left-hand one.
        """
        book = _book()
        puzzles = _book_of(*[(22, 22)] * self.PUZZLES, depth=6, tiers=["easy"] * self.PUZZLES)
        pages = _interior(puzzles, book)
        middle = pages[0].width / 2
        checked = 0

        for number, page in enumerate(pages, start=1):
            right_hand = page_is_right_hand(number)
            if number == 1:
                ink = np.asarray(page.convert("L")) < 128
                leftmost = int(np.where(ink.any(axis=0))[0].min())
                # Book 1: gutter 0.5in (150 px), outside 0.375in (112.5 px).
                assert (leftmost > 130) == right_hand, (
                    f"interior page 1's leftmost ink is at {leftmost}px"
                )
                checked += 1
                continue
            try:
                drawing = drawing_of(page)
            except ValueError:
                continue  # a divider page: no grid to measure parity from.
            offset = (drawing.left + drawing.grid_right) / 2 - middle
            assert (offset > 0) == right_hand, (
                f"interior page {number} measured {offset:+.1f} px from the "
                f"middle, but page_is_right_hand({number}) says "
                f"{'right' if right_hand else 'left'}-hand"
            )
            checked += 1

        # The guide page, the two-up-free puzzle pages and the answer pages:
        # everything but the two divider pages (Easy, SOLUTIONS).
        assert checked == len(pages) - 2

    def test_page_is_right_hand_itself_alternates_from_page_one(self) -> None:
        """The control: the declared parity is alternating, not constant."""
        assert page_is_right_hand(1) is True
        assert page_is_right_hand(2) is False
        assert [page_is_right_hand(n) for n in range(1, 7)] == [
            True,
            False,
            True,
            False,
            True,
            False,
        ]
