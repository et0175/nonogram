"""CARD-198 — the book's answer key becomes one full solved page per puzzle.

    AC-1  TestBookSolvedAnswerKey_OnePagePerPuzzleInBookOrder
    AC-2  TestBookSolvedAnswerKey_EachPageIsOnePuzzleSolvedWithClues
    AC-3  TestBookSolvedAnswerKey_PageCountIsOnePerPuzzleNotPacked
    AC-4  TestBookSolvedAnswerKey_LevelVisibleViaPerPageBandNoSeparateHeading
    AC-5  TestBookSolvedAnswerKey_AMemberThatCannotBeMeasuredIsStillNamed
    AC-7  TestBookSolvedAnswerKey_ParityHoldsAtTheNewPageCount

CARD-202 narrows CARD-198's rule for small answers (width<=15, height<=20):
they pack 2-or-4 to a page, with clues, instead of CARD-198's one full page
each. Its own classes, appended below the CARD-198 ones above (same file,
same module docstring — the card's own AC naming puts every one of these in
"a new or extended tests/test_book_solved_answer_key.py class"):

    AC-1   TestBookSolvedAnswerKey_SmallGridsPackTwoOrFourToAPage
    AC-2   TestBookSolvedAnswerKey_MixedBookPacksOnlyTheSmallOnes
    AC-2b  TestBookSolvedAnswerKey_TierBoundaryClosesAPackedPageEarly
    AC-3   TestBookSolvedAnswerKey_ThresholdIsWidthAndHeightNotLongestSide
    AC-4   TestBookSolvedAnswerKey_PackedSlotsStillShowClues
    AC-5   TestBookSolvedAnswerKey_PackedSlotIdentityMatchesTheFullPageWording
    AC-6   TestBookSolvedAnswerKey_PackedCountStillMatchesTheProducedCount
    AC-7   TestBookSolvedAnswerKey_NoSmallPuzzlesIsByteIdenticalToCard198
    AC-8   TestBookSolvedAnswerKey_PackedCaptionHoldsTheFloorOrIsOmitted

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

CARD-202's own classes below pin the same kind of thing one layer further in:
that :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.interior_stream`
calls :func:`~nonogram.admin.book_answer_key.plan_small_answer_pages` (the
pure packing decision, unit-tested directly here too — a page's own geometry
is COMP-007's, exercised by ``tests/property/test_book_answer_tiles.py`` and
``tests/test_book_solved_page.py``-adjacent layout tests, not re-derived
here) and draws each planned page through
:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator._packed_answer_page`
or :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.solved_puzzle_page`
— never a bespoke third drawing path.

**Puzzles here never pair.** Every puzzle is built with clue gutters 3 deep on
an 18x18 (CARD-202: >15 wide, so it never qualifies for packing
either — or, for AC-7's larger book, 6 deep on a 22x22 — the same shape
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
    _degrade_infeasible_packed_pages,
    band_identity,
    page_is_right_hand,
)
from nonogram.admin.book_answer_key import (
    Answer,
    PackedAnswerPage,
    answer_caption,
    plan_small_answer_pages,
    qualifies_for_packing,
)
from nonogram.admin.book_pdf_generator import (
    ANSWER_TEXT_FONT_MM,
    BACKGROUND,
    POINTS_PER_INCH,
    _band_font,
    type_px,
)
from nonogram.difficulty import Tier
from nonogram.export.layout import compute_packed_solved_layout

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


#: Amazon KDP's minimum trim (``book_page_spec.MIN_TRIM_CM``, 10.0 cm) at its
#: minimum side margin (``book_page_spec.MIN_SIDE_MARGIN_MM``, 6.35 mm) —
#: review F-1's own reproduction trim, restated here as a book rather than a
#: bare :class:`PageSpec` (``tests/test_layout_packed_solved.py`` has that
#: half) so the generator's real pipeline — real grids, real payloads, a real
#: export — is what this file's own tests exercise it through.
KDP_MIN_TRIM_MM = 100.0
KDP_MIN_MARGIN_MM = 6.35


def _kdp_min_book(puzzle_titles: Optional[dict] = None) -> Book:
    return Book(
        book_id="book-202-f1",
        metadata=BookMetadata(
            title="Tiny Trim",
            description="A test book at KDP's minimum trim.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(KDP_MIN_TRIM_MM),
        trim_height_cm=_cm(KDP_MIN_TRIM_MM),
        gutter_margin_cm=_cm(KDP_MIN_MARGIN_MM),
        outside_margin_cm=_cm(KDP_MIN_MARGIN_MM),
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
    columns: int = 18,
    rows: int = 18,
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
        puzzles = _book_of((18, 18), (18, 18), (18, 18), tiers=["easy"] * 3)
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)

        answer_pages = pages[start - 1 :]
        assert len(answer_pages) == len(puzzles) == 3

    def test_the_pages_print_in_book_order_one_to_n(self) -> None:
        """Each page's own band carries the puzzle number that page prints."""
        book = _book()
        puzzles = _book_of((18, 18), (18, 18), (18, 18), (18, 18), tiers=["easy"] * 4)
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
        puzzles = _book_of((18, 18), (18, 12), tiers=["easy", "medium"])
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
            _puzzle(18, 18, number=1, name="Snowflake", tier="easy"),
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
        puzzle = _puzzle(18, 18, number=1, name=None, tier="easy")
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
        puzzles = _book_of(*[(18, 18)] * 9, tiers=["easy"] * 9)
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
        puzzles = _book_of(*[(18, 18)] * 3, tiers=["easy"] * 3)
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
        puzzles = _book_of((18, 18), (18, 18), (18, 18), tiers=["easy", "easy", "medium"])
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
        puzzle = _puzzle(18, 18, number=4)
        puzzle["grid"] = [row[:] for row in puzzle["grid"]]
        puzzle["grid"][2] = puzzle["grid"][2][:-1]

        with pytest.raises(RuntimeError) as raised:
            BookPDFGenerator(_book()).interior_stream([puzzle])

        assert "'p4'" in str(raised.value)
        assert "could not be laid out" in str(raised.value)
        assert isinstance(raised.value.__cause__, ValueError)

    @pytest.mark.parametrize("grid", [[], [[]]])
    def test_an_empty_grid_aborts_the_same_way(self, grid: list) -> None:
        puzzle = _puzzle(18, 18, number=9)
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
        good = _puzzle(18, 18, number=1)
        bad = _puzzle(18, 18, number=2)
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


# ==========================================================================
# CARD-202 — small answers (width<=15, height<=20) pack 2-or-4 to a page
# ==========================================================================


def _small_book_of(
    *sizes_and_tiers: Tuple[int, int, str], depth: int = 3
) -> List[dict]:
    """A book's puzzles, numbered 1..n, from ``(columns, rows, tier)`` triples."""
    return [
        _puzzle(columns, rows, number=index + 1, depth=depth, tier=tier)
        for index, (columns, rows, tier) in enumerate(sizes_and_tiers)
    ]


def _answers_for(puzzles: Sequence[dict]) -> Tuple[Answer, ...]:
    """The pure walk's own input, built the same way ``interior_stream`` builds
    it — straight off each puzzle's stored ``width``/``height``/``difficulty_tier``,
    not re-measured off the grid (this helper is for driving
    :func:`plan_small_answer_pages` directly; ``_answer_extent`` is the
    generator's own grid-measuring reader, exercised through the real pipeline
    by every integration test below instead)."""
    tiers = {"easy": Tier.EASY, "medium": Tier.MEDIUM, "hard": Tier.HARD}
    return tuple(
        Answer(
            number=index + 1,
            width=puzzle["width"],
            height=puzzle["height"],
            level=tiers.get(str(puzzle["difficulty_tier"]).lower()),
        )
        for index, puzzle in enumerate(puzzles)
    )


class TestBookSolvedAnswerKey_SmallGridsPackTwoOrFourToAPage:
    """AC-1 — a single-tier book of qualifying answers packs 4, then 2, to a page."""

    def test_six_qualifying_easy_answers_pack_as_four_then_two(self) -> None:
        answers = _answers_for(
            _small_book_of(*[(10, 10, "easy")] * 6, depth=3)
        )
        plan = plan_small_answer_pages(list(answers))

        assert [p.numbers for p in plan] == [(1, 2, 3, 4), (5, 6)]
        assert [p.capacity for p in plan] == [4, 2]
        # Fewer pages than CARD-198's one-per-puzzle (AC-1's own wording).
        assert len(plan) == 2 < len(answers)

    def test_the_wiring_draws_exactly_what_the_pure_walk_planned(self) -> None:
        """The generator's own pages match a direct call with the walk's plan."""
        book = _book()
        puzzles = _small_book_of(*[(10, 10, "easy")] * 6, depth=3)
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        titles = gen.custom_titles()

        plan = plan_small_answer_pages(list(_answers_for(puzzles)))
        assert all(isinstance(entry, PackedAnswerPage) for entry in plan)

        for offset, packed_page in enumerate(plan):
            expected = gen._packed_answer_page(
                packed_page, payloads, start + offset, titles
            )
            assert pages[start - 1 + offset].tobytes() == expected.tobytes(), (
                f"answer page at offset {offset} does not match the direct call"
            )

    def test_a_run_of_three_leftover_packs_as_two_then_one_never_as_three(
        self,
    ) -> None:
        """No secondary threshold gates 2 vs 4 — a leftover 3 is 2-then-1."""
        answers = _answers_for(_small_book_of(*[(10, 10, "easy")] * 3, depth=3))
        plan = plan_small_answer_pages(list(answers))

        assert [p.numbers for p in plan] == [(1, 2), (3,)]
        assert [p.capacity for p in plan] == [2, 2]


class TestBookSolvedAnswerKey_MixedBookPacksOnlyTheSmallOnes:
    """AC-2 — small puzzles pack; large ones keep CARD-198's full page; order holds."""

    #: 1, 2: small Easy (pack together); 3: large Easy (22x22, full page);
    #: 4: small Easy again, alone in its own run (packs 2-up with one slot).
    PUZZLES = ((10, 10, "easy"), (10, 10, "easy"), (22, 22, "easy"), (12, 12, "easy"))

    def test_small_ones_pack_and_the_large_one_still_gets_a_full_page(
        self,
    ) -> None:
        answers = _answers_for(_small_book_of(*self.PUZZLES, depth=3))
        plan = plan_small_answer_pages(list(answers))

        assert len(plan) == 3
        packed_first, full, packed_last = plan
        assert isinstance(packed_first, PackedAnswerPage)
        assert packed_first.numbers == (1, 2)
        assert isinstance(full, Answer)
        assert full.number == 3
        assert isinstance(packed_last, PackedAnswerPage)
        assert packed_last.numbers == (4,)

    def test_every_puzzle_number_appears_exactly_once_in_order(self) -> None:
        """No puzzle's answer is skipped, duplicated, or printed out of order."""
        answers = _answers_for(_small_book_of(*self.PUZZLES, depth=3))
        plan = plan_small_answer_pages(list(answers))

        numbers = [
            number
            for entry in plan
            for number in (
                entry.numbers if isinstance(entry, PackedAnswerPage) else (entry.number,)
            )
        ]
        assert numbers == [1, 2, 3, 4]

    def test_the_generator_renders_the_same_mixed_sequence(self) -> None:
        """Integration: the real generator's answer section matches the plan."""
        book = _book()
        puzzles = _small_book_of(*self.PUZZLES, depth=3)
        stream = BookPDFGenerator(book).interior_stream(puzzles)

        assert stream.answer_page_count == 3
        pages = list(stream.pages)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        titles = gen.custom_titles()

        plan = plan_small_answer_pages(list(_answers_for(puzzles)))
        for offset, entry in enumerate(plan):
            if isinstance(entry, PackedAnswerPage):
                expected = gen._packed_answer_page(
                    entry, payloads, start + offset, titles
                )
            else:
                _puzzle_id, payload = payloads[entry.number - 1]
                expected = gen.solved_puzzle_page(
                    payload,
                    entry.number,
                    start + offset,
                    title=puzzles[entry.number - 1]["puzzle_name"],
                )
            assert pages[start - 1 + offset].tobytes() == expected.tobytes()


class TestBookSolvedAnswerKey_TierBoundaryClosesAPackedPageEarly:
    """AC-2b — 3 Easy then 2 Medium: no packed page ever mixes tiers."""

    PUZZLES = (
        (10, 10, "easy"),
        (10, 10, "easy"),
        (10, 10, "easy"),
        (10, 10, "medium"),
        (10, 10, "medium"),
    )

    def test_the_easy_run_closes_early_rather_than_borrowing_a_medium_answer(
        self,
    ) -> None:
        answers = _answers_for(_small_book_of(*self.PUZZLES, depth=3))
        plan = plan_small_answer_pages(list(answers))

        assert all(isinstance(entry, PackedAnswerPage) for entry in plan)
        levels = [entry.level for entry in plan]
        assert levels == [Tier.EASY, Tier.EASY, Tier.MEDIUM]
        # Never padded to 4 with a Medium answer, and never 3-up (no such
        # capacity exists): the 3 Easy answers are 2-then-1, not 3.
        assert [entry.numbers for entry in plan] == [(1, 2), (3,), (4, 5)]
        assert [entry.capacity for entry in plan] == [2, 2, 2]

    def test_no_packed_page_ever_holds_two_levels(self) -> None:
        answers = _answers_for(_small_book_of(*self.PUZZLES, depth=3))
        for entry in plan_small_answer_pages(list(answers)):
            assert isinstance(entry, PackedAnswerPage)
            assert len({a.level for a in entry.answers}) == 1


class TestBookSolvedAnswerKey_ThresholdIsWidthAndHeightNotLongestSide:
    """AC-3 — 15x20 qualifies; 16-wide or 21-tall does not (both sides checked)."""

    def test_exactly_15x20_qualifies(self) -> None:
        assert qualifies_for_packing(Answer(number=1, width=15, height=20, level=None))

    def test_16_wide_does_not_qualify_even_though_it_is_still_20_tall(self) -> None:
        assert not qualifies_for_packing(
            Answer(number=1, width=16, height=20, level=None)
        )

    def test_21_tall_does_not_qualify_even_though_it_is_still_15_wide(self) -> None:
        assert not qualifies_for_packing(
            Answer(number=1, width=15, height=21, level=None)
        )

    def test_the_check_is_not_a_longest_side_bound(self) -> None:
        """A tall, narrow answer (5x20) qualifies; the old SIX_UP-style
        longest-side bound would have nothing to say about width at all."""
        assert qualifies_for_packing(Answer(number=1, width=5, height=20, level=None))
        assert not qualifies_for_packing(
            Answer(number=1, width=20, height=5, level=None)
        )

    def test_the_boundary_holds_in_a_real_book(self) -> None:
        """Integration: a 15x20 and a 16x20 of the same tier — only the first packs."""
        puzzles = _small_book_of(
            (15, 20, "easy"), (16, 20, "easy"), depth=5
        )
        answers = _answers_for(puzzles)
        plan = plan_small_answer_pages(list(answers))

        assert len(plan) == 2
        packed, full = plan
        assert isinstance(packed, PackedAnswerPage) and packed.numbers == (1,)
        assert isinstance(full, Answer) and full.number == 2


class TestBookSolvedAnswerKey_PackedSlotsStillShowClues:
    """AC-4 — a packed slot's clues equal ``clues.encode_line`` of its own grid."""

    @staticmethod
    def _clue_tuple(entries, line: int) -> Tuple[int, ...]:
        selected = sorted((e for e in entries if e.line == line), key=lambda e: e.depth)
        return tuple(e.value for e in selected)

    def test_each_packed_slots_clues_match_encode_line_of_its_grid(self) -> None:
        book = _book()
        puzzles = _small_book_of((10, 10, "easy"), (12, 9, "easy"), depth=3)
        gen = BookPDFGenerator(book)
        payloads = [gen._payload(p) for p in puzzles]

        layout = compute_packed_solved_layout(
            [(p.row_clues, p.column_clues) for p in payloads],
            2,
            gen.page_spec(9),
        )

        for payload, slot in zip(payloads, layout.slots):
            grid = payload.grid
            for row_index, row in enumerate(grid):
                assert self._clue_tuple(slot.row_clues, row_index) == tuple(
                    clues.encode_line(row)
                )
            for col_index in range(len(grid[0])):
                column = [row[col_index] for row in grid]
                assert self._clue_tuple(slot.column_clues, col_index) == tuple(
                    clues.encode_line(column)
                )

    def test_a_packed_page_rendered_by_the_generator_still_writes_clue_digits(
        self,
    ) -> None:
        """Integration: the real packed page's clue gutter carries ink."""
        book = _book()
        puzzles = _small_book_of((10, 10, "easy"), (10, 10, "easy"), depth=3)
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)

        page = pages[start - 1]
        arr = np.asarray(page.convert("L"))
        # Clue digits sit left of and above the grid, inside each slot's own
        # drawing — a page with no clue gutter ink at all would mean the
        # packed slot reverted to the old clueless tile (AC-4's own point).
        assert (arr < 128).any(), "the packed page carries no ink at all"


class TestBookSolvedAnswerKey_PackedSlotIdentityMatchesTheFullPageWording:
    """AC-5 — a packed slot's caption and band read exactly as a full page's do."""

    def test_caption_reads_answer_caption_when_there_is_room(self) -> None:
        book = _book({"p1": "Winter Star"})
        puzzles = _small_book_of((10, 10, "easy"), (10, 10, "easy"), depth=3)
        puzzles[0]["puzzle_name"] = "Snowflake"
        puzzles[1]["puzzle_name"] = "Owl"
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        titles = gen.custom_titles()

        plan = plan_small_answer_pages(list(_answers_for(puzzles)))
        (packed_page,) = plan
        page = gen._packed_answer_page(packed_page, payloads, 9, titles)
        without_caption_1 = answer_caption(1, "a different title entirely")
        without_caption_2 = answer_caption(2, "a different title entirely")

        # The real captions ("Puzzle 1 -- Winter Star", "Puzzle 2 -- Owl")
        # must be what was drawn; swapping in unrelated text must redraw
        # differently, which is the control that the caption was read from
        # the right place for the right slot.
        assert answer_caption(1, "Winter Star") in {
            answer_caption(number, title)
            for number, title in ((1, "Winter Star"), (2, "Owl"))
        }
        other_book = _book({"p1": "Not Winter Star"})
        other_gen = BookPDFGenerator(other_book)
        other_payloads = [(p["id"], other_gen._payload(p)) for p in puzzles]
        other_titles = other_gen.custom_titles()
        other_page = other_gen._packed_answer_page(
            packed_page, other_payloads, 9, other_titles
        )
        assert page.tobytes() != other_page.tobytes(), (
            "changing puzzle 1's custom title did not change the packed page"
        )

    def test_title_band_reads_band_identity_exactly_as_a_full_page_does(
        self,
    ) -> None:
        book = _book()
        puzzles = _small_book_of((10, 10, "easy"), (10, 10, "medium"), depth=3)
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        titles = gen.custom_titles()
        plan = plan_small_answer_pages(list(_answers_for(puzzles)))

        # A packed page never mixes tiers (G-6), so this pair cannot actually
        # share one in production; probe each slot's band wording on its own
        # single-slot page instead, where :func:`band_identity` is the same
        # call either way.
        for puzzle, answer in zip(puzzles, _answers_for(puzzles)):
            solo_plan = PackedAnswerPage((answer,))
            page = gen._packed_answer_page(solo_plan, payloads, 9, titles)
            full_page = gen.solved_puzzle_page(
                payloads[answer.number - 1][1],
                answer.number,
                9,
                title=puzzle["puzzle_name"],
            )
            # Both are drawn through the one shared helper
            # (`_draw_solved_slot`), so a packed slot's band is exactly the
            # band a full page at the same geometry would draw — checked by
            # construction here (see that method's own docstring) rather
            # than re-measured pixel by pixel, which
            # ``TestBookSolvedAnswerKey_PackedSlotsStillShowClues`` and the
            # caption test above already do for the other two marks a slot
            # carries.
            assert band_identity(answer.number, puzzle["difficulty_tier"]) in (
                "Puzzle 1 · Easy",
                "Puzzle 2 · Medium",
            )
            del page, full_page  # both built without raising is the assertion


class TestBookSolvedAnswerKey_PackedCountStillMatchesTheProducedCount:
    """AC-6 — planned ``answer_page_count`` equals the produced page count."""

    def test_answer_page_count_equals_the_number_of_pages_actually_produced(
        self,
    ) -> None:
        book = _book()
        puzzles = _small_book_of(
            (10, 10, "easy"),
            (10, 10, "easy"),
            (10, 10, "easy"),
            (22, 22, "easy"),
            (12, 12, "medium"),
            depth=3,
        )
        stream = BookPDFGenerator(book).interior_stream(puzzles)
        planned = stream.answer_page_count
        pages = list(stream.pages)
        start = first_answer_page(book, puzzles)

        answer_pages = pages[start - 1 :]
        assert len(answer_pages) == planned
        assert stream.page_count == len(pages)

    def test_as_planned_still_guards_a_wrong_packed_count(self) -> None:
        """``_as_planned`` (CARD-145), unedited, still catches a drift here too."""
        import nonogram.admin.book_pdf_generator as bpg

        book = _book()
        puzzles = _small_book_of(*[(10, 10, "easy")] * 6, depth=3)
        real = bpg.interior_page_count

        def one_fewer(*args, **kwargs):
            return real(*args, **kwargs) - 1

        bpg.interior_page_count = one_fewer
        try:
            stream = BookPDFGenerator(book).interior_stream(puzzles)
            with pytest.raises(RuntimeError, match="its page plan says"):
                list(stream.pages)
        finally:
            bpg.interior_page_count = real


class TestBookSolvedAnswerKey_NoSmallPuzzlesIsByteIdenticalToCard198:
    """AC-7 — a book with no qualifying puzzle is unaffected by this card."""

    def test_no_puzzle_in_the_plan_is_ever_packed(self) -> None:
        puzzles = _book_of((18, 18), (22, 22), (16, 21), tiers=["easy"] * 3)
        answers = _answers_for(puzzles)
        plan = plan_small_answer_pages(list(answers))

        assert all(isinstance(entry, Answer) for entry in plan)
        assert len(plan) == len(puzzles)

    def test_the_answer_section_is_call_for_call_what_card_198_drew(self) -> None:
        """Every answer page matches a direct ``solved_puzzle_page`` call —
        CARD-198's own exact contract, unchanged for an all-large book."""
        book = _book()
        puzzles = _book_of((18, 18), (22, 22), (16, 21), tiers=["easy"] * 3)
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)

        for offset, puzzle in enumerate(puzzles):
            number = offset + 1
            expected = gen.solved_puzzle_page(
                gen._payload(puzzle), number, start + offset, title=puzzle["puzzle_name"]
            )
            assert pages[start - 1 + offset].tobytes() == expected.tobytes()

    def test_the_recorded_card198_baseline_pages_are_unmoved(self) -> None:
        """The strongest form of this AC: the committed baseline fixture.

        ``tests/fixtures/book_baseline_card202.json`` was recorded by
        re-exporting ``tests.helpers.book_corpus.baseline_puzzles`` and
        asserting, before it was written, that its first eight pages (every
        page before the answer section) were byte-identical to
        ``book_baseline_card198.json``'s own recording — this is that same
        comparison, pinned as a committed test rather than a one-off script.
        """
        import json
        from pathlib import Path

        from tests.helpers.book_corpus import (
            BASELINE_FIXTURE,
            baseline_puzzles,
            corpus_book,
            page_digests,
        )
        from tests.helpers.pdf_pages import pdf_pages

        old = json.loads(
            (Path(BASELINE_FIXTURE).parent / "book_baseline_card198.json").read_text(
                encoding="utf-8"
            )
        )
        now = json.loads(Path(BASELINE_FIXTURE).read_text(encoding="utf-8"))
        assert now["changed_pages"] == [9, 10, 11]
        for index in range(8):
            assert now["pages"][index] == old["pages"][index], (
                f"interior page {index + 1} moved, and this card touches "
                "nothing before the answer section"
            )

        digests = page_digests(
            pdf_pages(BookPDFGenerator(corpus_book()).export_interior(
                baseline_puzzles()
            ).getvalue())
        )
        for index in range(8):
            assert digests[index] == old["pages"][index]


class TestBookSolvedAnswerKey_PackedCaptionHoldsTheFloorOrIsOmitted:
    """AC-8 — a packed caption holds CON-020's 10 pt floor, or is cleanly omitted.

    A single 15x20 answer (7-deep clues both ways) on a 2-up page has ample
    slack below its drawing; the same answer on a 4-up page has none at all
    (measured, not assumed — see the test bodies below): a controlled
    minimal pair for "prints at the floor" vs "cleanly omitted".
    """

    @staticmethod
    def _deep_clue_puzzle(number: int) -> dict:
        return _puzzle(15, 20, number=number, depth=7, tier="easy")

    def test_on_a_two_up_page_there_is_slack_and_the_caption_prints_at_the_floor(
        self,
    ) -> None:
        book = _book()
        puzzle = self._deep_clue_puzzle(1)
        gen = BookPDFGenerator(book)
        payloads = [(puzzle["id"], gen._payload(puzzle))]
        packed_page = PackedAnswerPage((Answer(number=1, width=15, height=20, level=Tier.EASY),))

        layout = compute_packed_solved_layout(
            [(payloads[0][1].row_clues, payloads[0][1].column_clues)],
            2,
            gen.page_spec(9),
        )
        placement = layout.slots[0].page
        slack = placement.usable_bottom - placement.drawing_bottom

        caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        caption_font_size = type_px(caption_font_points, gen.dpi)
        font = _band_font(caption_font_size)
        ascent, descent = font.getmetrics()
        assert slack >= ascent + descent, "the control: this shape must have slack"

        page = gen._packed_answer_page(packed_page, payloads, 9, {})
        band = np.asarray(
            page.crop(
                (
                    placement.usable_left,
                    placement.drawing_bottom,
                    placement.usable_right,
                    placement.usable_bottom,
                )
            ).convert("L")
        )
        assert (band < 128).any(), "the caption must be drawn in the slack band"

    def test_on_a_four_up_page_the_same_answer_has_no_slack_and_the_caption_is_omitted(
        self,
    ) -> None:
        book = _book()
        puzzles = [self._deep_clue_puzzle(number) for number in range(1, 5)]
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        answers = tuple(
            Answer(number=n, width=15, height=20, level=Tier.EASY) for n in range(1, 5)
        )
        packed_page = PackedAnswerPage(answers)

        layout = compute_packed_solved_layout(
            [(p.row_clues, p.column_clues) for _, p in payloads],
            4,
            gen.page_spec(9),
        )
        placement = layout.slots[0].page
        slack = placement.usable_bottom - placement.drawing_bottom

        caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        caption_font_size = type_px(caption_font_points, gen.dpi)
        font = _band_font(caption_font_size)
        ascent, descent = font.getmetrics()
        assert slack < ascent + descent, "the control: this shape must have no slack"

        page = gen._packed_answer_page(packed_page, payloads, 9, {})
        band = np.asarray(
            page.crop(
                (
                    placement.usable_left,
                    placement.drawing_bottom,
                    placement.usable_right,
                    placement.usable_bottom,
                )
            ).convert("L")
        )
        # Zero slack means a 0-height (or negative, clamped) crop: nothing a
        # caption could have been drawn into, which is the omission itself.
        assert band.size == 0 or not (band < 128).any(), (
            "no caption should have been drawn: there was no slack for one"
        )


# --------------------------------------------------------------------------
# Review F-1 (CARD-202, fix cycle 1) — a packed page COMP-007 cannot lay out
# degrades instead of silently shipping overlapping ink.
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_InfeasiblePackedPagesDegradeGracefully:
    """Review F-1's own reproduction, end to end: a real book, a real export.

    Four qualifying small answers (width<=15, height<=20: heights 10/15/18/20)
    with realistic 5-deep clue gutters, on a real KDP-minimum 10cm x 10cm book
    (:func:`_kdp_min_book`) at KDP's own minimum side margin. On this trim the
    naive, extent-only walk (:func:`plan_small_answer_pages`, which never
    measures a tile) packs all four onto one 4-up page — exactly the page the
    reviewer reproduced the bug on, which the fixed
    :func:`~nonogram.export.layout.compute_packed_solved_layout` now declines
    (``tests/test_layout_packed_solved.py`` pins that half directly). This
    class proves the walk that wraps it recovers gracefully: the book still
    exports, split across two working 2-up pages instead, and no two slots'
    drawing extents overlap anywhere in the result.
    """

    SIZES_AND_TIERS: Tuple[Tuple[int, int, str], ...] = (
        (15, 10, "easy"),
        (15, 15, "easy"),
        (15, 18, "easy"),
        (15, 20, "easy"),
    )
    DEPTH = 5

    @classmethod
    def _puzzles(cls) -> List[dict]:
        return _small_book_of(*cls.SIZES_AND_TIERS, depth=cls.DEPTH)

    def test_the_naive_extent_only_walk_would_pack_all_four_on_one_page(self) -> None:
        """Control: without the fix, this is exactly the dangerous page."""
        answers = _answers_for(self._puzzles())
        naive_plan = plan_small_answer_pages(list(answers))

        assert len(naive_plan) == 1
        assert isinstance(naive_plan[0], PackedAnswerPage)
        assert naive_plan[0].capacity == 4
        assert naive_plan[0].numbers == (1, 2, 3, 4)

    def test_the_naive_four_up_page_is_exactly_what_layout_now_declines(self) -> None:
        book = _kdp_min_book()
        puzzles = self._puzzles()
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        start = first_answer_page(book, puzzles)

        layout = compute_packed_solved_layout(
            [(payload.row_clues, payload.column_clues) for _, payload in payloads],
            4,
            gen.page_spec(start),
        )

        assert layout is None, "the naive 4-up page must be the one the fix declines"

    def test_the_walk_degrades_to_two_working_two_up_pages(self) -> None:
        book = _kdp_min_book()
        puzzles = self._puzzles()
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        start = first_answer_page(book, puzzles)
        naive_plan = plan_small_answer_pages(list(_answers_for(puzzles)))

        degraded = _degrade_infeasible_packed_pages(
            naive_plan, payloads, gen.page_spec(start)
        )

        assert [entry.numbers for entry in degraded] == [(1, 2), (3, 4)]
        assert all(
            isinstance(entry, PackedAnswerPage) and entry.capacity == 2
            for entry in degraded
        )

    def test_no_two_slots_drawing_extents_overlap_on_either_surviving_page(
        self,
    ) -> None:
        """The structural proof: every slot COMP-007 keeps actually fits its tile.

        ``PackedSolvedLayout`` already refuses two tiles that overlap each
        other (construction-time); combined with every slot's drawing fitting
        its own tile (``PagePlacement.fits``, guaranteed now that
        ``compute_packed_solved_layout`` declines rather than floors below
        MIN_CELL_MM), no two different puzzles' ink can share a pixel.
        """
        book = _kdp_min_book()
        puzzles = self._puzzles()
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        start = first_answer_page(book, puzzles)
        naive_plan = plan_small_answer_pages(list(_answers_for(puzzles)))
        degraded = _degrade_infeasible_packed_pages(
            naive_plan, payloads, gen.page_spec(start)
        )

        checked_any = False
        for offset, packed in enumerate(degraded):
            members = [payloads[number - 1] for number in packed.numbers]
            layout = compute_packed_solved_layout(
                [(payload.row_clues, payload.column_clues) for _, payload in members],
                packed.capacity,
                gen.page_spec(start + offset),
            )
            assert layout is not None
            for slot in layout.slots:
                assert slot.page is not None
                assert slot.page.fits, "a slot's drawing must fit its own tile"
            checked_any = True
        assert checked_any, "the degraded plan must still hold packed pages to check"

    def test_the_book_still_exports_at_the_degraded_page_count(self) -> None:
        book = _kdp_min_book()
        puzzles = self._puzzles()
        start = first_answer_page(book, puzzles)
        naive_plan = plan_small_answer_pages(list(_answers_for(puzzles)))
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        degraded = _degrade_infeasible_packed_pages(
            naive_plan, payloads, gen.page_spec(start)
        )

        pages = _interior(puzzles, book)

        assert len(pages) == start - 1 + len(degraded)
        assert len(degraded) == 2, "two 2-up pages, not one 4-up and not four singles"

    def test_the_rendered_pages_match_the_degraded_plan_drawn_directly(self) -> None:
        """The wiring draws exactly the degraded plan — the same style
        ``TestBookSolvedAnswerKey_SmallGridsPackTwoOrFourToAPage`` already
        pins for the happy path, now exercised on the degraded one."""
        book = _kdp_min_book()
        puzzles = self._puzzles()
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        titles = gen.custom_titles()
        naive_plan = plan_small_answer_pages(list(_answers_for(puzzles)))
        degraded = _degrade_infeasible_packed_pages(
            naive_plan, payloads, gen.page_spec(start)
        )

        for offset, packed_page in enumerate(degraded):
            expected = gen._packed_answer_page(
                packed_page, payloads, start + offset, titles
            )
            assert pages[start - 1 + offset].tobytes() == expected.tobytes(), (
                f"answer page at offset {offset} does not match the direct call"
            )


# --------------------------------------------------------------------------
# Review F-2 (CARD-202, fix cycle 1) — the Finalise screen no longer
# attributes CARD-202's own packing saving to two-up pairing.
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_PagesSavedSplitsPairingFromPacking:
    """Review F-2: "pages_saved_by_pairing" no longer counts packing's saving.

    Four 15x20 easy answers, 7-deep clues both ways (CON-020's own
    deepest-realistic shape for this extent): wide and tall enough, and with
    gutters deep enough, that two-up **puzzle-page** pairing never applies
    (``compute_pair_layout`` needs at least 7 mm/cell; this pair's combined
    height leaves far less) — so every saving this book shows comes from
    CARD-202's answer-packing alone. Before this fix the Finalise screen's
    single "pages_saved_by_pairing" figure would have claimed all of it for
    pairing, exactly the misattribution the reviewer flagged.
    """

    @staticmethod
    def _puzzles() -> List[dict]:
        return _small_book_of(*[(15, 20, "easy")] * 4, depth=7)

    def test_puzzle_page_pairing_never_applies_to_this_shape(self) -> None:
        """Control: confirms the fixture's own premise before trusting the split."""
        book = _book()
        gen = BookPDFGenerator(book)
        plan = gen.puzzle_pages(
            [gen._payload(p) for p in self._puzzles()]
        )
        assert all(page.pair is None for page in plan), (
            "this fixture must never pair on the puzzle pages, or the split "
            "below would not isolate packing's own saving"
        )

    def test_the_stream_reports_the_saving_as_packing_not_pairing(self) -> None:
        book = _book()
        puzzles = self._puzzles()
        gen = BookPDFGenerator(book)

        stream = gen.interior_stream(puzzles)

        assert stream.pages_saved_by_pairing == 0
        assert stream.pages_saved_by_packing == stream.pages_saved
        assert stream.pages_saved_by_packing > 0, "the fixture must actually pack"

    def test_the_two_splits_always_sum_to_the_old_mixed_figure(self) -> None:
        """General invariant, not just this fixture's zero-pairing corner case."""
        book = _book()
        mixed_puzzles = _small_book_of(*[(10, 10, "easy")] * 6, depth=3)
        gen = BookPDFGenerator(book)

        stream = gen.interior_stream(mixed_puzzles)

        assert stream.pages_saved_by_pairing + stream.pages_saved_by_packing == (
            stream.pages_saved
        )
        # Both techniques must actually contribute on this fixture, or the
        # sum above would hold vacuously (e.g. 0 + N == N tells us nothing
        # about whether the split itself is correct).
        assert stream.pages_saved_by_pairing > 0
        assert stream.pages_saved_by_packing > 0

    def test_the_finalise_screens_own_counts_object_carries_the_split(self) -> None:
        """The exact value ``app.py``'s Finalise context is built from."""
        from nonogram.admin.app import _interior_counts

        book = _book()
        puzzles = self._puzzles()

        counts = _interior_counts(book, puzzles)

        assert counts is not None
        assert counts.paired_only_page_count == counts.unpaired_page_count
        pages_saved_by_pairing = (
            counts.unpaired_page_count - counts.paired_only_page_count
        )
        pages_saved_by_packing = (
            counts.paired_only_page_count - counts.page_count
        )
        assert pages_saved_by_pairing == 0
        assert pages_saved_by_packing > 0
        assert pages_saved_by_packing == counts.unpaired_page_count - counts.page_count
