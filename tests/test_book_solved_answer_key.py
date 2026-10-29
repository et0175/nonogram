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

import nonogram.admin.book_pdf_generator as book_pdf_generator
from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _as_planned,
    _degrade_infeasible_packed_pages,
    band_identity,
    page_frame,
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
    FOLIO_PT,
    POINTS_PER_INCH,
    _band_font,
    type_px,
)
from nonogram.difficulty import Tier
from nonogram.export.layout import ANSWER_TILE_GAP_MM, compute_packed_solved_layout

from tests.helpers.book_corpus import GUIDE_INTERIOR_PAGES
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
    decided = BookPDFGenerator(book).section_plan(list(puzzles))
    # CARD-201: the guide grew from 1 page to 2, so the answer section (right
    # after the SOLUTIONS divider, which is right after the puzzle section)
    # moved one page later — 4 + len(section), not 3. CARD-200: the table of
    # contents (``decided.toc_page_count`` pages) sits between the guide and
    # the puzzle section, moving everything after it later again by that
    # many pages — read off ``section_plan``'s own answer rather than
    # re-derived, the same "ask the one seam, don't recompute" discipline
    # this helper's own docstring already states. CARD-206: the blank title /
    # copyright page is reserved as interior page 1, one page earlier still
    # than the guide — 5 + ..., not 4.
    return 5 + decided.toc_page_count + len(decided.pages)


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
        assert len(pages) == 1 + 2, (
            "the blank title page (CARD-206) and the 2-page guide (CARD-201) "
            "alone"
        )


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
        """1 title (CARD-206) + 2 guide (CARD-201) + 1 TOC (CARD-200) +
        2 dividers + 3 puzzles + SOLUTIONS + 3 answers = 13.

        A per-level heading page inside the answer section (the alternative
        CARD-198's own "What to implement" considered and rejected) would
        make this 14 or 15 instead.
        """
        book, puzzles, pages = self._book_and_pages()
        assert len(pages) == 1 + 2 + 1 + 2 + 3 + 1 + 3 == 13


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

        The blank title page (interior page 1, CARD-206), the guide's two
        pages and the SOLUTIONS/level divider pages carry no
        ruled grid for :func:`drawing_of` to measure, so each divider is
        skipped (``drawing_of`` itself raises on it — a page with no grid at
        all, never a silently wrong measurement), the title page carries no
        ink at all and cannot be measured either, and the guide's own two
        pages' parity (CARD-201) is read the same independent way
        ``tests/test_book_pdf_memory.py``'s own parity test reads it: the
        leftmost ink column, which sits at the gutter margin on a right-hand
        page and at the (narrower) outside margin on a left-hand one.

        CARD-200 (SCOPE+): the table of contents page(s) carry no ruled grid
        either — plain text, like a divider — so :func:`drawing_of` raises on
        them the same way and they fall into the same ``except`` skip below.
        """
        book = _book()
        puzzles = _book_of(*[(22, 22)] * self.PUZZLES, depth=6, tiers=["easy"] * self.PUZZLES)
        pages = _interior(puzzles, book)
        middle = pages[0].width / 2
        checked = 0
        decided = BookPDFGenerator(book).section_plan(list(puzzles))

        for number, page in enumerate(pages, start=1):
            right_hand = page_is_right_hand(number)
            if number == 1:
                # CARD-206's blank title page: no ink, so nothing to measure
                # a side from. Asserted to be blank, which is the only thing
                # it can say, and not counted as a parity measurement.
                ink = np.asarray(page.convert("L")) < 128
                assert not ink.any(), "interior page 1 is the blank title page"
                continue
            if number in GUIDE_INTERIOR_PAGES:
                ink = np.asarray(page.convert("L")) < 128
                leftmost = int(np.where(ink.any(axis=0))[0].min())
                # Book 1: gutter 0.5in (150 px), outside 0.375in (112.5 px).
                assert (leftmost > 130) == right_hand, (
                    f"interior page {number}'s leftmost ink is at {leftmost}px"
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

        # The guide's two pages, the two-up-free puzzle pages and the answer
        # pages: everything but the two divider pages (Easy, SOLUTIONS), the
        # table of contents page(s) (CARD-200) and the blank title page
        # (CARD-206), which has no ink to measure a side from.
        assert checked == len(pages) - 2 - decided.toc_page_count - 1

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
        """The strongest form of this AC, restated for CARD-201's merge.

        This used to compare the committed baseline fixture's first eight
        pages byte-for-byte against ``book_baseline_card198.json`` (CARD-198,
        pre-CARD-201). ``book_baseline_card198.json`` predates CARD-201's
        2-page guide, and every page from the first puzzle/divider page
        onward permanently changes parity (recto/verso) — and therefore its
        exact pixels — once the guide grows by a page (a documented,
        unavoidable consequence of pagination; see the "SCOPE+" notes in
        ``tests/test_book_pdf_memory.py`` and ``tests/test_book_pdf_ink_mode.py``
        for the same point made elsewhere in this merge), not a regression.
        A byte-for-byte comparison against that pre-CARD-201 file can never
        pass again, and was never what this AC is actually about.

        What AC-7 *is* about — that CARD-202's packing walk touches nothing
        before the SOLUTIONS divider — is proven directly instead, with no
        stale fixture involved: the same baseline book is exported twice,
        once with the real packing walk and once with it forced off
        (monkeypatched to CARD-198's own one-full-page-per-answer shape),
        and every page before the answer section must come out
        byte-identical either way.
        """
        import json
        from pathlib import Path

        import nonogram.admin.book_pdf_generator as bpg
        from tests.helpers.book_corpus import (
            BASELINE_FIXTURE,
            baseline_puzzles,
            corpus_book,
            page_digests,
        )
        from tests.helpers.pdf_pages import pdf_pages

        now = json.loads(Path(BASELINE_FIXTURE).read_text(encoding="utf-8"))
        # CARD-200 (SCOPE+): the fixture this reads is now
        # book_baseline_card200.json, whose own `changed_pages` means
        # "literally every page" (a new TOC page plus a new folio mark on
        # every other one, CARD-200's own doing) — a different *shape* of
        # claim from CARD-201's own `[10, 11, 12]`, not a narrower version
        # of it, so `changed_pages[0] - 1` is no longer "how many pages
        # precede the answer section". That count is read directly off a
        # real plan instead, which is what this test actually needs and
        # does not depend on any fixture's own bookkeeping.
        plan = BookPDFGenerator(corpus_book()).section_plan(baseline_puzzles())
        before_answers = (
            1
            + bpg.TITLE_PAGE_COUNT
            + bpg.GUIDE_PAGE_COUNT
            + plan.toc_page_count
            + len(plan.pages)
        )
        assert now["page_count"] >= before_answers + 1, (
            "the fixture's own book should still open an answer section "
            "after this many front-matter/puzzle-section pages"
        )

        puzzles = baseline_puzzles()
        packed_bytes = BookPDFGenerator(corpus_book()).export_interior(puzzles).getvalue()

        real_plan = bpg.plan_small_answer_pages
        bpg.plan_small_answer_pages = lambda answers: list(answers)
        try:
            unpacked_bytes = BookPDFGenerator(corpus_book()).export_interior(puzzles).getvalue()
        finally:
            bpg.plan_small_answer_pages = real_plan

        packed_pages = page_digests(pdf_pages(packed_bytes))
        unpacked_pages = page_digests(pdf_pages(unpacked_bytes))

        # Everything before the answer section (the guide, the TOC, the
        # level dividers, the puzzle pages and the SOLUTIONS divider) is
        # identical whether packing ran or not: CARD-202's own G-1/G-2.
        for index in range(before_answers):
            assert packed_pages[index] == unpacked_pages[index], (
                f"interior page {index + 1} moved when packing was turned "
                "off — this card touches nothing before the answer section"
            )

        # The control: packing really did do something, so this is not a
        # vacuous comparison of two identical runs.
        assert len(packed_pages) < len(unpacked_pages)


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
        # The control: this shape must have at least one line's worth of
        # slack. This is deliberately the OLD, weaker bound (pre-CARD-203's
        # `slack >= line_height`) — a sanity floor on the fixture, not a
        # restatement of the production guard, which is the wider
        # `slack >= gap_px + line_height` (CARD-203) that `_draw_solved_slot`
        # actually evaluates; this shape's own slack clears that wider bound
        # too (asserted indirectly below, by the caption actually drawing).
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
        # The control: this shape must have no slack at all — below even the
        # OLD, weaker `slack >= line_height` bound (pre-CARD-203), which is
        # also necessarily below the production guard's wider
        # `slack >= gap_px + line_height` (CARD-203), so the caption is
        # omitted under either threshold; not a restatement of the
        # production guard itself.
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


class TestBookSolvedAnswerKey_PackedCaptionRightAlignedWithItsOwnTile:
    """CARD-203 review cycle 1, F-004 — a direct geometric assertion for the
    packed path's own caption right-alignment, mirroring
    ``TestBookSolvedPage_CaptionRightAlignedWithTheGrid`` (full page) rather
    than resting on the whole-page byte-identity baseline alone.

    ``TestBookSolvedAnswerKey_PackedCaptionHoldsTheFloorOrIsOmitted`` (AC-8,
    above) only asserts ink is present somewhere in a tile's own slack band
    — it cannot tell a correctly right-aligned packed caption from one drawn
    anywhere else in that band. This class asserts the packed slot's own
    caption ink sits at *that tile's* ``placement.drawing_right`` specifically.
    """

    @staticmethod
    def _render(title: str = "Snowflake"):
        book = _book()
        puzzle = _puzzle(15, 20, number=1, depth=7, tier="easy")
        gen = BookPDFGenerator(book)
        payloads = [(puzzle["id"], gen._payload(puzzle))]
        packed_page = PackedAnswerPage((Answer(number=1, width=15, height=20, level=Tier.EASY),))
        page = gen._packed_answer_page(packed_page, payloads, 9, {"p1": title})
        layout = compute_packed_solved_layout(
            [(payloads[0][1].row_clues, payloads[0][1].column_clues)],
            2,
            gen.page_spec(9),
        )
        return np.asarray(page.convert("RGB")), layout

    def test_the_tiles_own_caption_ink_sits_at_the_tiles_own_drawing_right(self) -> None:
        arr, layout = self._render()
        placement = layout.slots[0].page
        assert placement is not None

        # Isolated to the right half of this tile's own drawing span (not
        # the whole page), the same technique
        # TestBookSolvedPage_CaptionRightAlignedWithTheGrid uses for a full
        # page — a packed page can carry more than one tile, so searching
        # past this tile's own usable_right would risk picking up a
        # neighbouring tile's own ink instead.
        midpoint = (placement.drawing_left + placement.drawing_right) // 2
        slack = arr[
            placement.drawing_bottom : placement.usable_bottom,
            midpoint : placement.usable_right,
        ]
        dark_columns = np.flatnonzero((slack < 128).any(axis=(0, 2)))
        assert dark_columns.size > 0, "expected this tile's caption ink in its own right half"
        rightmost = int(dark_columns.max()) + midpoint

        assert rightmost <= placement.drawing_right + 4
        assert rightmost >= placement.drawing_right - 6

    def test_the_tiles_own_right_edge_stays_fixed_regardless_of_title_length(self) -> None:
        """Same discriminator as the full-page test: right-alignment keeps
        the rightmost pixel fixed; centring would move it with the text's
        own width."""

        def rightmost_ink(title: str) -> int:
            arr, layout = self._render(title)
            placement = layout.slots[0].page
            assert placement is not None
            midpoint = (placement.drawing_left + placement.drawing_right) // 2
            slack = arr[
                placement.drawing_bottom : placement.usable_bottom,
                midpoint : placement.usable_right,
            ]
            dark_columns = np.flatnonzero((slack < 128).any(axis=(0, 2)))
            assert dark_columns.size > 0
            return int(dark_columns.max()) + midpoint

        short = rightmost_ink("A")
        long = rightmost_ink("A Very Different, Much Longer Picture Name")
        assert abs(short - long) <= 2


class TestBookSolvedAnswerKey_PackedCaptionDoesNotCollideWithTheFolio:
    """CARD-203 review cycle 2, F-101/F-102 — the packed path's own
    corner-tile caption/folio collision check, mirroring
    ``TestBookSolvedPage_CaptionDoesNotCollideWithTheFolio``
    (``tests/test_book_solved_page.py``) but against ``_packed_answer_page``'s
    corner tile instead of a full page.

    Review cycle 1 (F-001) fixed the full-page case (``solved_puzzle_page``)
    by gating the caption-box fold-in on ``page_is_right_hand(page_number)``,
    but the packed-page fix (``_packed_answer_page``) shipped with no such
    gate — it folded the corner tile's caption into ``content_bottom``
    unconditionally. Review cycle 2 (F-101) found and reproduced the
    resulting regression: on a LEFT-hand packed page, the corner tile is
    column 0 (``corner_column`` in the production code), whose own
    ``drawing_left`` reaches the folio's actual (left) corner — but whose
    CAPTION is still right-aligned toward *that tile's own* ``drawing_right``
    (nowhere near the left margin). Folding that caption's bottom edge into
    ``content_bottom`` regardless of side made the folio disappear from a
    left-hand packed page with genuine, ample slack.

    ``_COLLISION_WIDTH``/``_COLLISION_HEIGHT``/``_COLLISION_DEPTH`` (14x4,
    depth 1 since CARD-222 re-measured it — 14x6 until then) at capacity 4 on
    :func:`_kdp_min_book` is a shape/trim pair found by direct measurement
    (not swept): both the left-hand
    (``_LEFT_HAND_PAGE_NUMBER``, 8) and right-hand (``_RIGHT_HAND_PAGE_NUMBER``,
    9) corner tiles land with zero horizontal margin (``drawing_right ==
    usable_right`` on the right-hand side, ``drawing_left == usable_left`` on
    the left-hand one — :func:`_kdp_min_book`'s gutter and outside margins
    are equal, so the two page sides are geometrically mirror-symmetric) and
    108 px of vertical slack below the grid — comfortably above both the
    caption's own omission guard (``gap_px + line_height`` = 73 px) and the
    folio's plain "is there room" bar (``line_height`` alone, 49 px).

    **Re-measured for CARD-222.** CON-018's amended top and bottom margins
    (0.55 in and 0.47 in, where the retired profile had 0.375 in on every
    side) take 16 mm of height off this trim, and this book stores no top or
    bottom margin of its own, so it gets the amended ones: the 14x6 shape's
    slack fell from 84 px to 43 px — under the caption's own guard, where the
    class's premise needs it above. Two rows shallower restores a shape in
    the same window (108 px) at the same width and depth; the alternatives
    measured in the window are 15x4 (119 px) and 16x5 (99 px).

    Each test renders the real page and an independently rendered reference
    built by monkeypatching the module-level ``_draw_folio`` to a no-op for
    one render only (ground-truth reuse, the same "diff against a reference
    that cannot draw the mark under test" technique the full-page class
    uses, adapted here since ``_packed_answer_page`` calls the module-level
    function directly rather than through an overridable method) — any pixel
    difference between the two is the folio's own ink, nothing else.
    """

    _COLLISION_WIDTH = 14
    _COLLISION_HEIGHT = 4
    _COLLISION_DEPTH = 1
    _LEFT_HAND_PAGE_NUMBER = 8
    _RIGHT_HAND_PAGE_NUMBER = 9

    @classmethod
    def _members(cls, gen: BookPDFGenerator):
        puzzles = [
            _puzzle(
                cls._COLLISION_WIDTH,
                cls._COLLISION_HEIGHT,
                number=number,
                depth=cls._COLLISION_DEPTH,
                tier="easy",
            )
            for number in range(1, 5)
        ]
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        answers = tuple(
            Answer(
                number=number,
                width=cls._COLLISION_WIDTH,
                height=cls._COLLISION_HEIGHT,
                level=Tier.EASY,
            )
            for number in range(1, 5)
        )
        return payloads, PackedAnswerPage(answers)

    @classmethod
    def _render(cls, page_number: int, *, suppress_folio: bool = False):
        gen = BookPDFGenerator(_kdp_min_book())
        payloads, packed_page = cls._members(gen)
        original_draw_folio = book_pdf_generator._draw_folio
        if suppress_folio:
            book_pdf_generator._draw_folio = lambda *args, **kwargs: None
        try:
            page = gen._packed_answer_page(packed_page, payloads, page_number, {})
        finally:
            book_pdf_generator._draw_folio = original_draw_folio
        layout = compute_packed_solved_layout(
            [(payload.row_clues, payload.column_clues) for _, payload in payloads],
            packed_page.capacity,
            gen.page_spec(page_number),
        )
        return np.asarray(page.convert("RGB")), layout, gen

    @classmethod
    def _corner_placement(cls, layout, gen, page_number: int):
        right_hand = page_is_right_hand(page_number)
        corner_column = layout.tile_columns - 1 if right_hand else 0
        corner_index = (layout.tile_rows - 1) * layout.tile_columns + corner_column
        return layout.slots[corner_index].page, right_hand

    def test_this_shape_really_sits_in_the_danger_window_on_both_page_sides(
        self,
    ) -> None:
        for page_number in (self._LEFT_HAND_PAGE_NUMBER, self._RIGHT_HAND_PAGE_NUMBER):
            _, layout, gen = self._render(page_number)
            placement, right_hand = self._corner_placement(layout, gen, page_number)
            assert placement is not None
            slack = placement.usable_bottom - placement.drawing_bottom
            caption_font_points = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
            caption_font_size = type_px(caption_font_points, gen.dpi)
            font = _band_font(caption_font_size)
            ascent, descent = font.getmetrics()
            gap_px = round(ANSWER_TILE_GAP_MM / 25.4 * gen.dpi)

            if right_hand:
                margin = placement.usable_right - placement.drawing_right
            else:
                margin = placement.drawing_left - placement.usable_left
            assert margin == 0, (
                "the corner tile must reach the page's own outer margin "
                "with no horizontal room to spare"
            )
            assert slack >= gap_px + ascent + descent, (
                "the caption must actually draw here, not be omitted for "
                "lack of slack"
            )

    def test_the_folio_still_yields_on_the_right_hand_page(self) -> None:
        """The genuine collision case (a): the corner tile's caption really
        does reach the same corner as the folio on a right-hand page — the
        folio must still correctly omit itself there, unaffected by the
        F-101 fix (``right_hand`` is already true before and after it)."""
        page_number = self._RIGHT_HAND_PAGE_NUMBER
        with_folio, _, _ = self._render(page_number, suppress_folio=False)
        without_folio, _, _ = self._render(page_number, suppress_folio=True)

        assert np.array_equal(with_folio, without_folio), (
            "expected the folio to be omitted (no pixel difference from a "
            "render where _draw_folio is a no-op): the corner tile's "
            "right-aligned caption occupies the exact corner the folio "
            "would otherwise draw into"
        )

    # ----------------------------------------------------------------
    # CARD-204 Fix 8 (review cycle 5, F-1) — the CLAMPED corner caption.
    # ----------------------------------------------------------------
    #
    # The two cases above use default short picture names, so their captions
    # are never clamped and they could not see F-1: Fix 7 moved an over-wide
    # caption's right edge out past its own ``drawing_right`` (to the tile's
    # ``usable_right``, the only x that keeps it inside its tile), and
    # ``_packed_answer_page`` went on feeding ``_draw_folio`` the *tile's*
    # ``drawing_right``. On the corner column of a right-hand page that
    # under-reports the caption's real edge by the whole clamp, so the
    # clearance test passed on a figure that no longer described the ink and
    # the folio drew into glyphs the caption had already set.
    #
    # The trim/shape pair below was found by sweeping 6 trim widths x 5 trim
    # heights x capacities 2 and 4 x grid sides 10..30 for the configuration
    # where the predicate actually *splits*: the clamp active, the caption's
    # own lower edge leaving the folio no vertical room, the stale figure
    # reading "clear" and the real one reading "not clear". Measured there
    # before the fix: ``drawing_right`` 2383 against the caption's real right
    # edge 2462, the folio's own glyph box starting at 2447, the folio drawn,
    # 20 px of caption ink inside that box and 5 pixels of literally shared
    # ink. Each of those four conditions is asserted below rather than
    # assumed, so a future geometry change that moves this shape out of the
    # danger window fails loudly instead of passing vacuously.
    #
    # **CARD-222 is such a change, and the assertions did fail loudly.**
    # CON-018's amended top and bottom margins (0.55 in and 0.47 in, against
    # 0.375 in on every side before) take 6.86 mm of usable height off this
    # trim, which is enough that the corner tile's caption is omitted for
    # lack of slack and the window is empty. The trim height alone is moved,
    # 9.0 -> 9.4 in, which is the height that restores all four conditions
    # at the same width, side and capacity (re-swept over 8.6..10.0 in x
    # sides 10..13; 8.8/9.0 in at side 10 and 9.8/10.0 in at side 12 also
    # land in the window). ``drawing_right`` is 2383 again, the folio's box
    # starts at 2447 again, and the caption's real right edge is 2456 rather
    # than 2462 — 9 px inside the folio's box instead of 20. The pre-fix
    # shared-ink count is not re-measured: the fix it describes is shipped
    # and the behaviour it described cannot be produced any more.

    _CLAMPED_TRIM_WIDTH_MM = 8.5 * 25.4
    _CLAMPED_TRIM_HEIGHT_MM = 9.4 * 25.4
    _CLAMPED_SIDE = 11
    _CLAMPED_CAPACITY = 4
    _CLAMPED_TITLE = (
        "A Snowflake Over The Frozen Pine Woods At Midnight In Deep Winter"
    )

    @classmethod
    def _clamped_book(cls, titles: dict) -> Book:
        return Book(
            book_id="book-204-fix8",
            metadata=BookMetadata(
                title="Clamped Caption",
                description="A test book whose corner caption is clamped.",
                theme="generic",
                target_audience="adults",
                size="",
                page_count=0,
            ),
            trim_width_cm=_cm(cls._CLAMPED_TRIM_WIDTH_MM),
            trim_height_cm=_cm(cls._CLAMPED_TRIM_HEIGHT_MM),
            gutter_margin_cm=_cm(KDP_MIN_MARGIN_MM),
            outside_margin_cm=_cm(KDP_MIN_MARGIN_MM),
            puzzle_titles=dict(titles),
        )

    @classmethod
    def _render_clamped(cls, title: str, *, suppress_folio: bool = False):
        """The reproduction page, rendered the same way the two cases above
        are — the real ``_packed_answer_page``, with the module-level
        ``_draw_folio`` monkeypatched to a no-op for the reference render
        only, so folio ink and caption ink are separable."""
        page_number = cls._RIGHT_HAND_PAGE_NUMBER
        puzzles = [
            _puzzle(
                cls._CLAMPED_SIDE,
                cls._CLAMPED_SIDE,
                number=number,
                depth=3,
                tier="easy",
                name=title,
            )
            for number in range(1, cls._CLAMPED_CAPACITY + 1)
        ]
        titles = {puzzle["id"]: title for puzzle in puzzles}
        gen = BookPDFGenerator(cls._clamped_book(titles))
        payloads = [(puzzle["id"], gen._payload(puzzle)) for puzzle in puzzles]
        packed_page = PackedAnswerPage(
            tuple(
                Answer(
                    number=number,
                    width=cls._CLAMPED_SIDE,
                    height=cls._CLAMPED_SIDE,
                    level=Tier.EASY,
                )
                for number in range(1, cls._CLAMPED_CAPACITY + 1)
            )
        )
        original_draw_folio = book_pdf_generator._draw_folio
        if suppress_folio:
            book_pdf_generator._draw_folio = lambda *args, **kwargs: None
        try:
            page = gen._packed_answer_page(packed_page, payloads, page_number, titles)
        finally:
            book_pdf_generator._draw_folio = original_draw_folio
        layout = compute_packed_solved_layout(
            [(payload.row_clues, payload.column_clues) for _, payload in payloads],
            packed_page.capacity,
            gen.page_spec(page_number),
        )
        placement, _ = cls._corner_placement(layout, gen, page_number)
        return page, placement, gen

    @classmethod
    def _caption_band_ink(cls, page, placement, gen):
        """The caption's own one-line band, read across the whole page width:
        the columns that carry ink, and the band's own lower edge."""
        font = _band_font(type_px(ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4, gen.dpi))
        ascent, descent = font.getmetrics()
        gap_px = round(ANSWER_TILE_GAP_MM / 25.4 * gen.dpi)
        top = placement.drawing_bottom + gap_px
        bottom = top + ascent + descent
        band = np.asarray(page.crop((0, top, page.width, bottom)).convert("L"))
        return np.flatnonzero((band < 128).any(axis=0)), bottom

    @classmethod
    def _folio_glyph_left(cls, gen, page_number: int):
        """Where the folio's own glyph box starts, and how tall it is — the
        two figures ``_draw_folio``'s own clearance test is written in."""
        font = _band_font(type_px(FOLIO_PT, gen.dpi))
        ascent, descent = font.getmetrics()
        frame = page_frame(gen.page_spec(page_number))
        return frame.right - font.getlength(str(page_number)), ascent + descent, frame

    def test_this_shape_really_clamps_the_corner_caption_into_the_folios_corner(
        self,
    ) -> None:
        """All four conditions of the predicate split, measured — so the two
        tests below cannot pass for the wrong reason."""
        page_number = self._RIGHT_HAND_PAGE_NUMBER
        page, placement, gen = self._render_clamped(
            self._CLAMPED_TITLE, suppress_folio=True
        )
        assert placement is not None
        columns, band_bottom = self._caption_band_ink(page, placement, gen)
        folio_left, folio_line_height, frame = self._folio_glyph_left(gen, page_number)

        assert columns.size > 0, "expected the caption's own ink in its own band"
        assert columns.max() > placement.drawing_right, (
            f"this caption must be CLAMPED past its own grid: rightmost ink "
            f"{columns.max()} vs drawing_right {placement.drawing_right}"
        )
        assert columns.max() >= folio_left, (
            f"the clamped caption must actually reach the folio's own glyph "
            f"box: rightmost ink {columns.max()} vs folio box from {folio_left}"
        )
        assert frame.bottom - band_bottom < folio_line_height, (
            "the caption's lower edge must leave the folio no vertical room, "
            "or _draw_folio never reads a horizontal figure at all"
        )
        assert placement.drawing_right <= folio_left, (
            "the tile's own drawing_right — the stale figure this fix "
            "replaces — must read 'clear', or there is nothing to under-report"
        )

    def test_the_folio_yields_to_a_clamped_corner_caption(self) -> None:
        """F-1 itself: with the caption clamped into the folio's own corner,
        the folio must omit itself — "the folio yields, the content wins,"
        the same rule the unclamped right-hand case above already keeps.

        Before Fix 8 this failed: ``_packed_answer_page`` passed the tile's
        ``drawing_right`` (2383), which cleared the folio's glyph box (from
        2447), so the folio drew while the caption's real right edge was
        2462 — 20 px of caption ink inside the folio's box, 5 pixels of
        shared ink."""
        with_folio, _, _ = self._render_clamped(self._CLAMPED_TITLE)
        without_folio, _, _ = self._render_clamped(
            self._CLAMPED_TITLE, suppress_folio=True
        )

        assert np.array_equal(
            np.asarray(with_folio.convert("RGB")),
            np.asarray(without_folio.convert("RGB")),
        ), (
            "expected the folio to be omitted (no pixel difference from a "
            "render where _draw_folio is a no-op): the corner tile's caption "
            "is clamped out to that tile's usable_right, which on this page "
            "is the folio's own corner"
        )

    def test_the_same_page_still_prints_its_folio_for_an_unclamped_caption(
        self,
    ) -> None:
        """The negative control on the same trim and the same shape: a
        caption of the length a book actually prints is not clamped, cannot
        reach the folio's corner, and must not cost the page its folio."""
        page, placement, gen = self._render_clamped("Owl", suppress_folio=True)
        columns, _ = self._caption_band_ink(page, placement, gen)
        folio_left, _, _ = self._folio_glyph_left(gen, self._RIGHT_HAND_PAGE_NUMBER)
        assert columns.size > 0
        assert columns.max() <= placement.drawing_right + 4, (
            "the control's caption must be right-aligned with its own grid, "
            "not clamped"
        )
        assert columns.max() < folio_left

        with_folio, _, _ = self._render_clamped("Owl")
        without_folio, _, _ = self._render_clamped("Owl", suppress_folio=True)
        assert not np.array_equal(
            np.asarray(with_folio.convert("RGB")),
            np.asarray(without_folio.convert("RGB")),
        ), (
            "expected the folio to draw: nothing on this page reaches its "
            "corner, so Fix 8 must not have made the folio disappear"
        )

    def test_the_folio_now_draws_on_the_left_hand_page(self) -> None:
        """F-101's own regression case (b): the same shape on a left-hand
        page has genuine, ample slack (84 px, well above the folio's own
        49 px bar) — the corner tile's caption sits at *that tile's own*
        right edge, nowhere near the folio's actual (left) corner, so the
        folio must draw, not be silently omitted."""
        page_number = self._LEFT_HAND_PAGE_NUMBER
        with_folio, _, _ = self._render(page_number, suppress_folio=False)
        without_folio, _, _ = self._render(page_number, suppress_folio=True)

        assert not np.array_equal(with_folio, without_folio), (
            "expected the folio to draw (a pixel difference from a render "
            "where _draw_folio is a no-op) — this page's slack is ample and "
            "the corner tile's caption cannot actually reach this page's "
            "own left-outer corner"
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


# --------------------------------------------------------------------------
# CARD-204 Fix 7 — a packed caption is held inside its own TILE
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_PackedCaptionWiderThanItsTileStaysInside:
    """CARD-204 Fix 7 — an over-wide caption on a *packed* slot stays inside
    that slot's own tile, on both parities.

    The full-page half of this claim lives in
    ``tests/test_book_solved_page.py::TestBookSolvedPage_CaptionWiderThanItsGridStaysInsideTheMargin``;
    this is the packed half, and it is not a duplicate of it. A packed slot's
    :class:`~nonogram.export.layout.PagePlacement` carries its **tile's** box
    as the usable area (``_packed_tile_layout``), not the page's, and a tile
    is half a page wide — so an over-wide caption is both likelier here and
    bounded by a different rectangle. ``_draw_solved_slot`` must therefore
    ask ``caption_slot`` about the *slot* it was handed; a future edit that
    passed it the whole page's layout instead would leave this test's ink
    spilling across the gutter into the neighbouring tile while every
    full-page test stayed green.
    """

    #: Long enough that "Puzzle 1 — ..." is wider than a 2-up tile on Book 1
    #: (asserted below, not assumed).
    _LONG_TITLE = "A Snowflake Over The Frozen Pine Woods At Midnight In Deep Winter"

    @staticmethod
    def _render(page_number: int, title: str):
        """One 15x20 answer packed alone onto a 2-up page, captioned ``title``.

        The same shape and the same harness
        ``TestBookSolvedAnswerKey_PackedCaptionHoldsTheFloorOrIsOmitted``
        uses for its "there is slack" case, so the caption is actually drawn.
        """
        puzzle = _puzzle(15, 20, number=1, depth=7, tier="easy", name=title)
        gen = BookPDFGenerator(_book({puzzle["id"]: title}))
        payloads = [(puzzle["id"], gen._payload(puzzle))]
        packed_page = PackedAnswerPage(
            (Answer(number=1, width=15, height=20, level=Tier.EASY),)
        )
        layout = compute_packed_solved_layout(
            [(payloads[0][1].row_clues, payloads[0][1].column_clues)],
            2,
            gen.page_spec(page_number),
        )
        page = gen._packed_answer_page(
            packed_page, payloads, page_number, {puzzle["id"]: title}
        )
        return page, layout.slots[0].page, gen

    @classmethod
    def _caption_ink_columns(cls, page, placement, gen):
        """The dark columns of the caption's own one-line band, read across
        the **whole page width** — so ink that left the tile is seen, not
        cropped away by the measurement itself."""
        font = _band_font(type_px(ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4, gen.dpi))
        ascent, descent = font.getmetrics()
        gap_px = round(ANSWER_TILE_GAP_MM / 25.4 * gen.dpi)
        top = placement.drawing_bottom + gap_px
        band = np.asarray(
            page.crop((0, top, page.width, top + ascent + descent)).convert("L")
        )
        return np.flatnonzero((band < 128).any(axis=0))

    @pytest.mark.parametrize("page_number", [9, 10])
    def test_this_caption_really_is_wider_than_its_own_tile(self, page_number) -> None:
        _, placement, gen = self._render(page_number, self._LONG_TITLE)
        font = _band_font(type_px(ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4, gen.dpi))
        width = font.getlength(answer_caption(1, self._LONG_TITLE))
        assert width > placement.drawing_right - placement.drawing_left
        assert width > placement.usable_right - placement.usable_left, (
            "on a tile this caption is wider than the whole tile, so it "
            "exercises the clip as well as the clamp"
        )

    @pytest.mark.parametrize("page_number", [9, 10])
    def test_no_caption_ink_leaves_the_tile(self, page_number) -> None:
        page, placement, gen = self._render(page_number, self._LONG_TITLE)
        columns = self._caption_ink_columns(page, placement, gen)
        assert columns.size > 0, "expected the caption's own ink in its own band"
        assert columns.min() >= placement.usable_left, (
            f"the caption's leftmost ink is {placement.usable_left - columns.min()} px "
            f"outside its own tile on a {placement.parity} page"
        )
        assert columns.max() <= placement.usable_right

    @pytest.mark.parametrize("page_number", [9, 10])
    def test_a_short_caption_is_still_right_aligned_with_its_own_grid(
        self, page_number
    ) -> None:
        """The negative control: the clamp is inactive for a caption of the
        length a book actually prints, so CARD-203's right-alignment still
        describes a packed slot too."""
        page, placement, gen = self._render(page_number, "Owl")
        columns = self._caption_ink_columns(page, placement, gen)
        assert columns.size > 0
        assert columns.max() <= placement.drawing_right + 4
        assert columns.max() >= placement.drawing_right - 6
        assert columns.min() > placement.usable_left


# ==========================================================================
# CARD-297 — the answer pages as PDF operators (ADR-0042/R1)
#
#     AC-1  TestAnswerAndTocPages_CarryNoImageXObject
#     AC-2  TestAnswerKey_IsTheOnlyPlaceTheTitleIsPrinted
#     AC-3  TestAnswerTiles_ReuseTheGridRoutine
#     AC-5  TestAnswerTileHeader_DifficultyDotsAreRound
#     AC-6  TestAnswerPages_CaptionHoldsTheFloorInTheStream
#     EC    TestPropertyTest_AnswerAndToc_WriterDerivesNoGeometry
#     (AC-4 is the table of contents' own, in ``tests/test_book_toc.py``.)
#
# **Every claim about a vector page is made against the content stream of a
# written PDF, or against poppler — an engine that did not write it.** No
# claim about a vector page is made by counting dark pixels; the one place a
# raster page is read below is AC-1's *positive control*, where the raster
# twin of the same page really does reference an image XObject, which is what
# makes AC-1's reading capable of failing (ADR-0039/R1).
#
# **The pages come from one walk of the real interior** (:func:`recorded`).
# The three vector twins take the same arguments their raster twins take, so
# that walk is spied on once — what each TOC page, full answer page and packed
# answer page was asked to draw — and exactly that is handed to the twin. No
# page plan is re-derived here: a second walk would be a second opinion on the
# book, and the arguments are the production ones by construction.
#
# G-5: the pixel-reading sites above this line are **not** converted. They
# read the raster pages the book still ships (``_write_pdf`` chooses no medium
# per page until CARD-298), so converting them would drop the control on what
# ships in exchange for a control on what does not. This block is the
# stream-side half, beside the ink-side half rather than instead of it.
# ==========================================================================

import ast as _ast
import math as _math
import re as _re
import sys as _sys
from pathlib import Path as _Path
from random import Random as _Random

from PIL import Image as _Image, ImageDraw as _ImageDraw

from nonogram.admin import book_answer_vector, book_toc_vector, book_vector_draw
from nonogram.admin.book_pdf_generator import (
    DividerPagePlan,
    PageKind,
    PuzzlePagePlan,
    TocEntry,
    _SOLVED_GRID_GRAY,
    _draw_difficulty_dots,
    answer_title,
    structural_toc_entries,
)
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_plan import TIERS
from nonogram.admin.book_vector import ContentStream, interior_face_metrics, write_vector_pdf
from nonogram.difficulty import Tier as _Tier
from nonogram.export.layout import (
    PageParity,
    compute_answer_page_layout,
    compute_layout,
    difficulty_dots,
)
from tests.helpers import pdf_vector, round_ink

NO_POPPLER_PPM = "poppler (pdftoppm) is not installed: AC-5's independent engine is absent"
needs_pdftoppm = pytest.mark.skipif(pdf_vector.PDFTOPPM is None, reason=NO_POPPLER_PPM)
NO_POPPLER_TEXT = (
    "poppler (pdftotext) is not installed: the caption's own placement has no "
    "independent engine to read it back"
)
needs_poppler_text = pytest.mark.skipif(
    pdf_vector.PDFTOTEXT is None, reason=NO_POPPLER_TEXT
)

#: One shown string of a content stream: the ``Tf`` size it was set at and the
#: text itself. ``book_vector.ContentStream.text`` writes the whole show on
#: one line, so one pattern reads both — which is what lets AC-6 assert a
#: **named** face's size rather than "the smallest size on the page".
_SHOW = _re.compile(
    r"/\S+ (" + pdf_vector.NUMBER + r") Tf \S+ \S+ Td \((.*?)\) Tj"
)

#: One stroked straight line, as ``ContentStream.line`` writes it.
_LINE = _re.compile(
    r"("
    + pdf_vector.NUMBER
    + r") ("
    + pdf_vector.NUMBER
    + r") m ("
    + pdf_vector.NUMBER
    + r") ("
    + pdf_vector.NUMBER
    + r") l S"
)

#: One painted rectangle, as ``ContentStream.rectangle`` writes it.
_RECT = _re.compile(
    r"("
    + pdf_vector.NUMBER
    + r") ("
    + pdf_vector.NUMBER
    + r") ("
    + pdf_vector.NUMBER
    + r") ("
    + pdf_vector.NUMBER
    + r") re ([SfB])"
)


def _shows(stream_text: str) -> List[Tuple[float, str]]:
    """``(size in points, text)`` for every string the stream sets, in order."""
    return [(float(size), text) for size, text in _SHOW.findall(stream_text)]


def _strings(stream_text: str) -> List[str]:
    return [text for _, text in _shows(stream_text)]


def _written(streams: Sequence[ContentStream]) -> bytes:
    return write_vector_pdf(list(streams), len(streams)).getvalue()


class _Recorded:
    """What one walk of a book's real interior asked each page kind to draw."""

    def __init__(self, book: Book, puzzles: Sequence[dict]) -> None:
        self.generator = BookPDFGenerator(book)
        self.toc: List[Tuple[List[TocEntry], int]] = []
        self.answers: List[Tuple[object, int, int, Optional[str]]] = []
        self.packed: List[Tuple[PackedAnswerPage, list, int, dict]] = []
        #: Every ``ImageDraw.text`` the walk made, as ``(page, text, names)``
        #: where ``names`` is the ``nonogram`` functions on the stack above
        #: it. This is AC-2's **whole-interior** reading: a page kind that
        #: printed a title would print it through one of these calls.
        self.text: List[Tuple[int, str, frozenset]] = []
        self._walk(list(puzzles))

    def _walk(self, puzzles: List[dict]) -> None:
        self_recorded = self
        generator = self.generator
        klass = BookPDFGenerator
        original = {
            name: getattr(klass, name)
            for name in ("create_toc_page", "solved_puzzle_page", "_packed_answer_page")
        }
        original_text = _ImageDraw.ImageDraw.text
        current = {"page": 0}

        def spy_toc(self, entries, page_number):
            self_recorded.toc.append((list(entries), page_number))
            return original["create_toc_page"](self, entries, page_number)

        def spy_answer(self, payload, puzzle_number, page_number, title=None):
            self_recorded.answers.append((payload, puzzle_number, page_number, title))
            return original["solved_puzzle_page"](
                self, payload, puzzle_number, page_number, title
            )

        def spy_packed(self, plan, payloads, page_number, titles):
            self_recorded.packed.append((plan, list(payloads), page_number, dict(titles)))
            return original["_packed_answer_page"](self, plan, payloads, page_number, titles)

        def spy_text(self, xy, text, fill=None, font=None, *args, **kwargs):
            names = []
            frame = _sys._getframe(1)
            while frame is not None:
                if frame.f_globals.get("__name__", "").startswith("nonogram."):
                    names.append(frame.f_code.co_name)
                frame = frame.f_back
            self_recorded.text.append((current["page"], str(text), frozenset(names)))
            return original_text(self, xy, text, fill, font, *args, **kwargs)

        klass.create_toc_page = spy_toc
        klass.solved_puzzle_page = spy_answer
        klass._packed_answer_page = spy_packed
        _ImageDraw.ImageDraw.text = spy_text
        try:
            stream = generator.interior_stream(puzzles)
            pages = iter(stream.pages)
            drawn = 0
            while True:
                current["page"] = drawn + 1
                try:
                    next(pages)
                except StopIteration:
                    break
                drawn += 1
            self.page_count = drawn
            assert drawn == stream.page_count
        finally:
            for name, function in original.items():
                setattr(klass, name, function)
            _ImageDraw.ImageDraw.text = original_text

    def toc_streams(self) -> List[ContentStream]:
        generator = self.generator
        return [
            book_toc_vector.toc_page_stream(
                entries,
                page_frame(generator.page_spec(page_number)),
                generator.dpi,
                page_number,
            )
            for entries, page_number in self.toc
        ]

    def answer_streams(self) -> List[ContentStream]:
        """Every answer page of the book, full and packed, in print order."""
        generator = self.generator
        pages = [
            (
                page_number,
                book_answer_vector.answer_page(
                    generator.page_spec(page_number),
                    generator.dpi,
                    payload,
                    number,
                    page_number,
                    title,
                ),
            )
            for payload, number, page_number, title in self.answers
        ]
        pages += [
            (
                page_number,
                book_answer_vector.packed_answer_page(
                    generator.page_spec(page_number),
                    generator.dpi,
                    plan,
                    payloads,
                    page_number,
                    titles,
                ),
            )
            for plan, payloads, page_number, titles in self.packed
        ]
        return [stream for _, stream in sorted(pages, key=lambda pair: pair[0])]


#: The book this block reads, and the titles its answer key prints. Named
#: puzzles rather than ``_puzzle``'s default "Picture N", because AC-2 is
#: about a *title* and a book whose titles were all absent would pass it
#: vacuously — ``test_every_answer_page_prints_a_title`` is the control that
#: refuses that.
_TITLES = ("Snowflake", "Owl in a Pine", "Reindeer", "Tiny Bell")


def _titled_book_puzzles() -> List[dict]:
    """Four puzzles: two that pack two-up and two that take a page each."""
    return [
        _puzzle(12, 12, number=1, depth=3, name=_TITLES[0], tier="easy"),
        _puzzle(12, 12, number=2, depth=3, name=_TITLES[1], tier="easy"),
        _puzzle(18, 18, number=3, depth=3, name=_TITLES[2], tier="medium"),
        _puzzle(18, 18, number=4, depth=3, name=_TITLES[3], tier="hard"),
    ]


_RECORDINGS: dict = {}


def _recorded(profile: str) -> _Recorded:
    """One walk per profile, shared by every test below."""
    if profile not in _RECORDINGS:
        book = _book() if profile == "book1" else _kdp_min_book()
        _RECORDINGS[profile] = _Recorded(book, _titled_book_puzzles())
    return _RECORDINGS[profile]


@pytest.fixture(scope="module", params=["book1", "min-trim"])
def profile(request) -> str:
    """Book 1's trim, and the 10 x 10 cm minimum trim CON-018 also stocks."""
    return request.param


@pytest.fixture(scope="module")
def recorded(profile: str) -> _Recorded:
    return _recorded(profile)


# --------------------------------------------------------------------------
# AC-1 — neither page kind carries a bitmap
# --------------------------------------------------------------------------


class TestAnswerAndTocPages_CarryNoImageXObject:
    """AC-1 (ADR-0042/R1): no page of either kind references an image XObject.

    Read off the written file's own ``/Resources`` dictionaries, by
    :func:`~tests.helpers.pdf_vector.page_resource_keys` — which spells the
    keys out as strings rather than handing back Pillow's ``PdfDict``, because
    ``PdfDict`` indexes by ``bytes`` and *iterates* ``PdfName``, and a
    membership test that silently reads ``False`` is exactly how "this page
    carries no image XObject" would pass without being true.

    The positive control is :meth:`test_the_raster_twin_of_the_same_page_does_carry_one`:
    the raster answer page of the same book really does reference one, so this
    reading can fail (ADR-0039/R1).
    """

    def test_no_answer_page_of_the_book_names_an_xobject(self, recorded) -> None:
        streams = recorded.answer_streams()
        assert streams, "the book printed no answer page to read"
        for keys in pdf_vector.page_resource_keys(_written(streams)):
            assert "XObject" not in keys, keys

    def test_no_toc_page_of_the_book_names_an_xobject(self, recorded) -> None:
        streams = recorded.toc_streams()
        assert streams, "the book printed no table of contents to read"
        for keys in pdf_vector.page_resource_keys(_written(streams)):
            assert "XObject" not in keys, keys

    def test_every_page_of_both_kinds_draws_something(self, recorded) -> None:
        """A blank page carries no XObject either, so emptiness is ruled out."""
        for stream in recorded.toc_streams() + recorded.answer_streams():
            assert stream.render(), "an empty stream is a blank sheet, not a page"

    def test_the_operator_alphabet_is_closed_at_what_these_pages_draw(
        self, recorded
    ) -> None:
        """Default-DENY over the operators, not a search for ``Do``.

        ``Do`` is how an XObject is *painted*, and naming it is the obvious
        check; this asserts the whole alphabet instead, so an operator neither
        page kind should emit — a transformation, a clip, an inline image
        (``BI``) — fails here rather than being absent from a list nobody
        updated.

        **An equality, not a subset, since review cycle 2.** F-297-04 measured
        the allow-list at 16 members against 13 emitted, and the three surplus
        ones — ``B``, ``c`` and ``h`` — were exactly
        :meth:`ContentStream.round_mark`'s own vocabulary, so the cell carried
        slack precisely where
        :meth:`TestAnswerTileHeader_DifficultyDotsAreRound.test_no_answer_page_draws_a_round_mark_today`
        needs it tight, and the two cells disagreed about whether ``c`` was
        allowed. The reading is now the measured set itself, over both page
        kinds together, which closes the slack in both directions: a new
        operator reds, and an operator these pages *stop* emitting reds too.
        Measured identical on both profiles (13 members; the TOC alone emits 6
        of them and the answer pages all 13).
        """
        emitted = {
            "g", "G", "w", "m", "l", "S", "re", "f",
            "BT", "ET", "Tf", "Td", "Tj",
        }
        seen: set = set()
        for stream_text in pdf_vector.content_streams(
            _written(recorded.toc_streams() + recorded.answer_streams())
        ):
            tokens = set(pdf_vector.operator_tokens(stream_text))
            assert tokens <= emitted, sorted(tokens - emitted)
            seen |= tokens
        assert seen == emitted, (sorted(seen - emitted), sorted(emitted - seen))
        # The three members F-297-04 found surplus are a round mark's, and a
        # round shape on these pages is CARD-233's signal rather than this
        # card's licence. Stated here as well as in the limit cell so the two
        # cannot drift apart again.
        assert not ({"B", "c", "h"} & seen), sorted({"B", "c", "h"} & seen)

    def test_the_raster_twin_of_the_same_page_does_carry_one(self, recorded) -> None:
        """The control. The same answer page as a bitmap references an image."""
        payload, number, page_number, title = recorded.answers[0]
        page = recorded.generator.solved_puzzle_page(payload, number, page_number, title)
        data = recorded.generator._write_pdf(
            [page],
            1,
            mode=recorded.generator.interior_bitmap_mode,
            kinds=(PageKind.ANSWER,),
        ).getvalue()
        assert any("XObject" in keys for keys in pdf_vector.page_resource_keys(data))


# --------------------------------------------------------------------------
# AC-2 / EC(ADR-0037/R1) — the answer key is the only place the title prints
# --------------------------------------------------------------------------


class TestAnswerKey_IsTheOnlyPlaceTheTitleIsPrinted:
    """AC-2 (FR-033/AC-194, ADR-0037/R1), in both halves and both media.

    The half that **can** fail is the second one, and it is asserted over the
    **whole interior** rather than over the answer section: a claim read only
    off the answer pages cannot notice a puzzle page that started printing the
    picture's name. So the second half is taken two ways, and neither is a
    reading of the answer pages:

    * **over every mark the raster interior makes** — one walk's worth of
      ``ImageDraw.text`` calls, tagged with the ``nonogram`` functions above
      them, so a title drawn by *any* page kind is seen. That is every page
      the book ships today: the title page, both guide pages, the TOC, the
      puzzle pages, the dividers and the answer pages;
    * **over the vector streams** of the three page kinds that have a vector
      writer — this card's two and CARD-295's puzzle page — read as the
      strings they actually set.

    The corpus arm (:meth:`test_the_title_prints_only_on_answer_pages_across_a_corpus`)
    is the EC: the same comparison over a seeded corpus of books, with its
    minimum case count asserted inside it.
    """

    @staticmethod
    def _titles_of(recorded: _Recorded) -> List[str]:
        return [
            answer_title(None, payload.name)
            for payload, _, _, _ in recorded.answers
        ] + [
            answer_title(titles.get(str(puzzle_id)), payload.name)
            for _, payloads, _, titles in recorded.packed
            for puzzle_id, payload in payloads
        ]

    def test_every_answer_page_prints_its_pictures_name(
        self, recorded, profile
    ) -> None:
        """The first half, and the control that the second half is not vacuous.

        **Asserted against the raster answer key rather than against a
        literal**, because a caption is *omitted* rather than overlapped where
        the trim leaves no slack for it (CARD-197's AC-6), and the 10 x 10 cm
        minimum trim genuinely has pages where it is. So the claim is the
        cross-medium one — the titles the vector answer pages set are exactly
        the titles the raster answer captions drew — plus two controls: the
        set is not empty on either profile, and on Book 1 it is the whole
        book's four titles, so the comparison is not an agreement between two
        empty sets.
        """
        printed = [
            " ".join(_strings(text))
            for text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
        ]
        assert printed
        vector = {title for title in _TITLES for page in printed if title in page}
        raster = {
            title
            for title in _TITLES
            for _, text, names in recorded.text
            if "_draw_solved_slot" in names and title in text
        }
        assert vector == raster, (sorted(vector), sorted(raster))
        assert vector, "no answer page printed a title, so AC-2's sweep is vacuous"
        if profile == "book1":
            assert vector == set(_TITLES), sorted(vector)

    def test_a_clipped_title_is_counted_as_printed_in_both_media(
        self, recorded
    ) -> None:
        """F-297-03's half of AC-2: a clip is not an omission.

        The cell above reads whole titles, which is the right reading for "is
        the name on the page". It is also blind to a *clipped* name on both
        sides at once — the 10 x 10 cm trim prints ``'Puzzle 2 — Owl in a …'``
        today — so this adds the reading that is not: the set of titles each
        medium printed **something** for, clips included, must agree, and the
        caption cells' element-for-element comparison then pins the string
        itself.
        """
        wanted = set(self._captions_for(recorded))
        vector = {
            _caption_behind(reading, wanted)
            for stream_text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
            for _, text in _shows(stream_text)
            if (reading := _caption_reading(text, wanted)) is not None
        }
        raster = {
            _caption_behind(reading, wanted)
            for _, text, names in recorded.text
            if "_draw_solved_slot" in names
            and (reading := _caption_reading(text, wanted)) is not None
        }
        assert vector == raster, (sorted(vector), sorted(raster))
        assert vector, "no answer page carried a name at all"

    @staticmethod
    def _captions_for(recorded: _Recorded) -> List[str]:
        """The whole caption lines this book's answer key would print."""
        return TestAnswerPages_CaptionHoldsTheFloorInTheStream._captions(recorded)

    def test_the_only_raster_calls_carrying_a_title_are_answer_captions(
        self, recorded
    ) -> None:
        """The second half, over every mark the interior draws."""
        offenders = [
            (page, text, sorted(names))
            for page, text, names in recorded.text
            if any(title in text for title in _TITLES)
            and "_draw_solved_slot" not in names
        ]
        assert offenders == []

    def test_the_interior_really_was_walked_end_to_end(self, recorded) -> None:
        """Guard the instrument: a walk that drew nothing would pass above."""
        assert recorded.page_count >= 10
        assert len({page for page, _, _ in recorded.text}) >= 6
        assert any(
            any(title in text for title in _TITLES) for _, text, _ in recorded.text
        ), "no page of the interior printed a title at all, so the sweep is vacuous"

    def test_no_toc_row_prints_a_title_in_the_stream_either(self, recorded) -> None:
        for text in pdf_vector.content_streams(_written(recorded.toc_streams())):
            shown = " ".join(_strings(text))
            assert not any(title in shown for title in _TITLES), shown

    def test_no_vector_puzzle_page_prints_a_title(self, recorded) -> None:
        payloads = [payload for payload, _, _, _ in recorded.answers] + [
            payload for _, payloads, _, _ in recorded.packed for _, payload in payloads
        ]
        streams = list(recorded.generator.vector_puzzle_pages(payloads))
        assert streams
        for text in pdf_vector.content_streams(_written(streams)):
            shown = " ".join(_strings(text))
            assert not any(title in shown for title in _TITLES), shown

    def test_the_title_prints_only_on_answer_pages_across_a_corpus(self) -> None:
        """EC(ADR-0037/R1): the same comparison over a seeded corpus of books.

        Built by hand with ``random.Random`` (no ``hypothesis`` — it is not in
        the dependency baseline), over the trims CON-018 stocks and over
        puzzle names chosen to be unmistakable in a stream. The minimum case
        count is asserted **inside** the test, so the corpus cannot silently
        shrink (G-7).
        """
        random = _Random(297)
        names = [
            "Zarquon",
            "Vexing Owl",
            "Quokka at Dusk",
            "Jellyfish",
            "Wyvern",
            "Xyloph",
        ]
        cases = 0
        printed = 0
        omitted = 0
        clipped = 0
        # Four of the trims CON-018 stocks, three of them portrait KDP sizes
        # and the fourth the 10 x 10 cm square minimum — which is in the
        # corpus precisely because a square trim leaves a full-page answer no
        # vertical slack at all (measured: 0 px), so the omission branch is
        # exercised rather than assumed.
        for trim in ((10.0, 10.0), (13.97, 21.59), (15.24, 22.86), (21.59, 27.94)):
            for seed in range(3):
                picked = [names[random.randrange(len(names))] for _ in range(2)]
                book = Book(
                    book_id=f"card-297-corpus-{trim[0]}x{trim[1]}-{seed}",
                    metadata=BookMetadata(
                        title="Corpus",
                        description="CARD-297's EC corpus.",
                        theme="generic",
                        target_audience="adults",
                        size="",
                        page_count=0,
                    ),
                    trim_width_cm=_cm(trim[0] * 10),
                    trim_height_cm=_cm(trim[1] * 10),
                    gutter_margin_cm=_cm(KDP_MIN_MARGIN_MM),
                    outside_margin_cm=_cm(KDP_MIN_MARGIN_MM),
                )
                generator = BookPDFGenerator(book)
                puzzles = [
                    _puzzle(12, 12, number=index + 1, depth=3, name=name)
                    for index, name in enumerate(picked)
                ]
                payloads = [generator._payload(row) for row in puzzles]
                answers = [
                    book_answer_vector.answer_page(
                        generator.page_spec(11 + index),
                        generator.dpi,
                        payload,
                        index + 1,
                        11 + index,
                        picked[index],
                    )
                    for index, payload in enumerate(payloads)
                ]
                puzzle_streams = list(generator.vector_puzzle_pages(payloads))
                for index, text in enumerate(
                    pdf_vector.content_streams(_written(answers))
                ):
                    shown = " ".join(_strings(text))
                    # The caption is OMITTED rather than overlapped where the
                    # trim leaves no slack (CARD-197's AC-6), which the 10 cm
                    # trim genuinely does. So the page either prints its own
                    # title or prints no title at all -- never a different
                    # puzzle's, and never one on a page that had no room for
                    # a caption.
                    if picked[index] in shown:
                        printed += 1
                    elif any(
                        len(piece) > 1
                        and piece.endswith("…")
                        and picked[index].startswith(piece.split(" — ")[-1][:-1])
                        for piece in _strings(text)
                    ):
                        # CLIPPED, which is neither printed nor omitted. Counted
                        # as its own outcome since review cycle 2 (F-297-03):
                        # the old reading swept a clipped name into `omitted`
                        # and then asserted the name was absent, so a clip that
                        # kept part of the name would have failed here for the
                        # wrong reason — or, worse, a future clip that dropped
                        # the whole stem would have silently inflated the
                        # omission floor.
                        clipped += 1
                    else:
                        omitted += 1
                        for name in set(picked):
                            assert name not in shown, (trim, seed, name, shown)
                    cases += 1
                for text in pdf_vector.content_streams(_written(puzzle_streams)):
                    shown = " ".join(_strings(text))
                    for name in set(picked):
                        assert name not in shown, (trim, seed, name, shown)
                    cases += 1
        assert cases >= 40, cases
        # Measured on this corpus: 18 of the 24 answer pages have the slack to
        # print a caption (the six that do not are the 10 cm trim's). Asserted
        # as a floor so the sweep cannot go vacuous by every caption being
        # omitted, which is the one way the "prints its own title" half above
        # could pass without being exercised.
        assert printed >= 18, printed
        # And the omission branch is exercised rather than assumed: the 10 cm
        # square trim's six answer pages have 0 px of slack (measured), so the
        # ``else`` arm above is live. A corpus where every caption printed
        # would make it dead.
        assert omitted >= 6, omitted
        # And no case in this corpus clips, so the two floors above are an
        # equality over 24 answer pages rather than three buckets with slack.
        # Pinned because a clip is what F-297-03 showed the old reading could
        # not see: if a corpus name starts clipping, that shows up here as a
        # changed figure instead of as a quietly larger omission count.
        assert clipped == 0, clipped
        assert printed + omitted + clipped == 24, (printed, omitted, clipped)


# --------------------------------------------------------------------------
# AC-3 — the tiles are the grid routine, not a third copy
# --------------------------------------------------------------------------

#: The PDF operators that put a path or a mark on a page, as against the ones
#: that only set state (``g``/``G``/``w``) or set type
#: (``BT``/``Tf``/``Td``/``Tj``/``ET``). A grid is a path, so anything that
#: emits one of these is a door a second grid walk could be driven through.
_PATH_OPERATORS = frozenset({"m", "l", "re", "c", "h", "S", "f", "B"})

#: One call per public ``ContentStream`` member, so :func:`_content_stream_doors`
#: can **drive** each one and read what comes out rather than being told. The
#: arguments only have to be valid — what is measured is which operators are
#: emitted, not where they land.
#:
#: A member with no entry here is **watched anyway** (that is the default-DENY)
#: *and* reported through :data:`_UNCLASSIFIED_DOORS`, so a method added to
#: ``ContentStream`` cannot become an unwatched door by nobody noticing it.
_DOOR_PROBE = {
    "to_points": (10.0,),
    "stroke_grey": (0.0,),
    "fill_grey": (0.0,),
    "stroke_width": (1.0,),
    "line": (1.0, 2.0, 3.0, 4.0),
    "rectangle": (1.0, 2.0, 3.0, 4.0),
    "curve": (1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
    "begin_path": (1.0, 2.0),
    "line_to": (1.0, 2.0),
    "close_path": (),
    "paint": (),
    "round_mark": (50.0, 50.0, 10.0),
    "text": ("x", 1.0, 2.0, 10.0),
    "render": (),
}

#: Why each public ``ContentStream`` member the guard does **not** watch is not
#: watched — one entry per exclusion, machine-checked by
#: ``test_every_unwatched_member_is_excluded_by_its_own_measurement``: the
#: member really emits no path operator, and every operator it *does* emit is
#: named in its own reason. An exclusion is therefore a statement about a
#: measurement rather than an absence from a list (ADR-0039/R2).
#:
#: ``text`` is the entry worth reading twice. It emits no path, so it is not a
#: path door; a *rule* set as a run of underscore glyphs, or a disc set as a
#: round dingbat, is the **named limit**
#: :meth:`~nonogram.admin.book_vector.ContentStream.round_mark`'s own docstring
#: records with **CARD-298** as its owner — ADR-0042/R1's derived
#: per-page-kind check, measured as ink. Nothing here claims it shut.
_NOT_A_DOOR_BECAUSE = {
    "to_points": "converts pixels to points and emits no operator at all",
    "media_box": "a property reading the page box; it emits no operator at all",
    "operators": "a property reading the record back; it emits no operator at all",
    "render": "encodes what was already recorded; it emits no operator at all",
    "stroke_grey": "sets the stroke tone (G) and constructs no path",
    "fill_grey": "sets the fill tone (g) and constructs no path",
    "stroke_width": "sets the stroke width (w) and constructs no path",
    "text": (
        "sets type (g BT Tf Td Tj ET) and constructs no path; a rule set as "
        "glyphs is round_mark's named limit, owned by CARD-298"
    ),
}


def _public_members(cls) -> List[str]:
    """``cls``'s public names, **inherited ones included**, in a stable order.

    **CARD-298, taking CARD-297's review cycle 2 finding F2-01.** This was
    ``vars(cls)`` for one card, which reads the class's own ``__dict__``
    alone — so a drawing door contributed by a *base* class is simply not in
    the set. Cycle 2 drove exactly that: a mixin ahead of ``ContentStream``
    carrying a ``hatch`` method, the class's own surface left at sixteen, and
    a ``stream.hatch`` grid walk **ADMITTED** with both guard cells green and
    :data:`_UNCLASSIFIED_DOORS` empty.

    It was left for a later card on purpose, and the reason constrains how it
    lands: **it changes the guard's own derivation, and a merge gate does not
    mutate** — a version that silently returned *everything* would pass
    exactly as a correct one would. So it ships with its control in the same
    commit, as ``TestContentStreamDoors_AnInheritedDoorIsWatched`` below:
    the shipped class's reading is unmoved at sixteen, an inherited drawing
    door is watched, and the over-returning version is caught by the live
    ``_UNCLASSIFIED_DOORS == ()`` cell rather than by inspection.

    ``dir()`` rather than a walk of ``__mro__``: it is the stdlib's own answer
    to "what can be reached through an instance of this class", which is
    exactly the question a door guard asks, and it is the authority
    ADR-0039/R2 wants rather than a second enumeration of inheritance written
    here. Nothing public comes from ``object`` — its whole surface is
    dunders — so the leading-underscore filter is what keeps the two readings
    identical on a class that inherits only ``object``, and that identity is
    asserted rather than assumed.
    """
    return sorted(name for name in dir(cls) if not name.startswith("_"))


def _content_stream_doors(cls=ContentStream) -> Tuple[Tuple[str, ...], dict, Tuple[str, ...]]:
    """``cls``'s drawing doors, **derived by driving every member**.

    Returns ``(doors, emitted, unclassified)`` — the public members whose own
    output carries a path operator, what each member emitted, and the ones
    :data:`_DOOR_PROBE` does not know how to call.

    This is the half of AC-3's guard review cycle 1 found hand-listed
    (F-297-01). ``_STROKERS`` named ``line`` and ``rectangle``, and a complete
    grid walk written as ``begin_path``/``line_to``/``paint`` reached the page
    through three doors nothing watched. The set is now a **measurement of the
    class**: a door added to ``ContentStream`` is watched because it paints,
    not because somebody remembered to list it, and a member left unwatched is
    left unwatched by :data:`_NOT_A_DOOR_BECAUSE` and the measurement behind
    it.
    """
    doors: List[str] = []
    emitted: dict = {}
    unclassified: List[str] = []
    for name in _public_members(cls):
        member = getattr(cls, name)
        stream = cls(width_px=1000.0, height_px=1000.0, dpi=300)
        if isinstance(member, property):
            getattr(stream, name)
        elif name in _DOOR_PROBE:
            getattr(stream, name)(*_DOOR_PROBE[name])
        else:
            # Unknown: watched, and reported. Default-DENY is what happens to
            # a member nobody has classified yet; it is not a reason to skip.
            unclassified.append(name)
            doors.append(name)
            emitted[name] = ()
            continue
        tokens = tuple(pdf_vector.operator_tokens("\n".join(stream.operators)))
        emitted[name] = tokens
        if set(tokens) & _PATH_OPERATORS:
            doors.append(name)
    return tuple(doors), emitted, tuple(unclassified)


#: Everything in ``ContentStream`` that can put a path on a page, derived
#: above. Eight of sixteen public members, on the measurement this file makes:
#: ``begin_path``, ``close_path``, ``curve``, ``line``, ``line_to``, ``paint``,
#: ``rectangle``, ``round_mark``. The other eight are
#: :data:`_NOT_A_DOOR_BECAUSE`'s.
_STROKERS, _DOOR_EMITS, _UNCLASSIFIED_DOORS = _content_stream_doors()

#: The modules AC-3's guard governs: this card's two page writers. The
#: shared routines they draw through live in ``book_vector_draw``, which is
#: CARD-295's and is deliberately **not** in the domain — a guard over the
#: routine itself would forbid the one implementation it exists to protect.
_GUARDED = (book_answer_vector, book_toc_vector)


def _enclosing(tree: _ast.AST) -> dict:
    """Every node's innermost enclosing ``FunctionDef``, by ``id``.

    Built by descent rather than by :func:`ast.walk`, because ``walk`` loses
    the nesting: a helper defined *inside* an exempt function would otherwise
    be attributed to that function and inherit its exemption, which is one of
    the shapes this guard is controlled against.
    """
    owner: dict = {}

    def descend(node, current):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            current = node
        for child in _ast.iter_child_nodes(node):
            owner[id(child)] = current
            descend(child, current)

    owner[id(tree)] = None
    descend(tree, None)
    return owner


def _parameters(function) -> set:
    args = function.args
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    if args.vararg is not None:
        named.append(args.vararg)
    if args.kwarg is not None:
        named.append(args.kwarg)
    return {argument.arg for argument in named}


def _fills(call: _ast.Call) -> bool:
    """Whether ``call`` paints a **fill** — stated as a literal, or not at all.

    **Read, no longer acted on.** Until review cycle 2 this function was an
    exception inside :func:`stroke_violations`: a ``rectangle`` whose ``paint``
    was the literal ``"fill"`` was admitted without the exemption. That was a
    second discrimination the guard made by *hand* underneath a set that read
    as derived — F-297-01's own defect class — and it left a grid walk written
    as a row of thin filled rectangles admitted on every path. The guard is now
    default-DENY over every door whatever it paints, and a fill reaches a page
    only through the one derived exemption like any other mark.

    It is kept because ``test_a_fill_is_not_a_rule_and_is_admitted`` and this
    docstring are the record of which reading changed, and because a reader
    asking "does this guard still treat a fill specially?" should find the
    answer written down rather than inferred from an absence.
    """
    for keyword in call.keywords:
        if keyword.arg == "paint":
            return (
                isinstance(keyword.value, _ast.Constant)
                and keyword.value.value == "fill"
            )
    return False


def stroke_violations(source: str) -> List[str]:
    """Every place ``source`` rules a line outside the derived exemption.

    **Default-DENY** (ADR-0039/R2). Everything that can put a path on a page is
    collected first — a call to one of :data:`_STROKERS` on any object, and any
    *reference* to one of them that is not a call, which is how such a method
    would be bound to a name and called under another one — and each is then
    admitted only if its innermost enclosing function is in the exemption set.
    An expression at module level has no enclosing function and is therefore
    denied, not skipped.

    **:data:`_STROKERS` is a measurement of ``ContentStream``, not a list.**
    :func:`_content_stream_doors` drives every public member of that class and
    watches the ones whose own output carries a path operator — eight of
    sixteen — so a door added there is watched because it paints. Review cycle
    1 (F-297-01) found this set hand-listed at ``("line", "rectangle")`` and
    drove a complete grid walk past it through ``begin_path``/``line_to``/
    ``paint``; that artefact is now
    ``test_the_guard_catches_a_grid_walk_in_each_of_these_shapes``'s
    ``polyline-through-begin-path-and-paint`` case.

    **What a call paints is no longer consulted.** A fill is watched like a
    stroke, because a grid can be walked with thin filled rectangles as well as
    with lines, and admitting one by its ``paint`` argument was a second
    hand-made discrimination under a derived set (see :func:`_fills`).

    **The exemption set is derived, not listed**: a function is exempt exactly
    when it takes a parameter named ``grid``. That is the structural
    difference between the two kinds of line an answer page draws. The grid's
    own rules are a function of the *layout* alone — which is why CARD-295's
    :func:`~nonogram.admin.book_vector_draw.draw_grid_lines` never sees a
    solution and why it can be reused here at all — while the lighter join
    between two adjacent filled cells is a function of the *solution*, and no
    routine that does not take the grid could decide where one goes. So a
    function that rules a line while holding the grid is drawing a mark the
    shared routine does not have; one that rules a line without it is drawing
    the grid again.
    """
    tree = _ast.parse(source)
    owner = _enclosing(tree)
    exempt = {
        id(node)
        for node in _ast.walk(tree)
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
        and "grid" in _parameters(node)
    }
    called = set()
    found: List[str] = []

    for node in _ast.walk(tree):
        if (
            isinstance(node, _ast.Call)
            and isinstance(node.func, _ast.Attribute)
            and node.func.attr in _STROKERS
        ):
            called.add(id(node.func))
            function = owner[id(node)]
            where = "module level" if function is None else function.name
            if function is None or id(function) not in exempt:
                found.append(f"line {node.lineno}: {where} rules a {node.func.attr}")

    for node in _ast.walk(tree):
        if (
            isinstance(node, _ast.Attribute)
            and node.attr in _STROKERS
            and id(node) not in called
        ):
            function = owner[id(node)]
            where = "module level" if function is None else function.name
            found.append(f"line {node.lineno}: {where} binds .{node.attr} to a name")

    return sorted(found)


def exempt_functions(source: str) -> List[str]:
    """The names the derivation above admits, for a test to read back."""
    tree = _ast.parse(source)
    return sorted(
        node.name
        for node in _ast.walk(tree)
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
        and "grid" in _parameters(node)
    )


def _all_functions(source: str) -> List[str]:
    tree = _ast.parse(source)
    return sorted(
        node.name
        for node in _ast.walk(tree)
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
    )


def _source_of(module) -> str:
    return _Path(module.__file__).read_text(encoding="utf-8")


class TestAnswerTiles_ReuseTheGridRoutine:
    """AC-3: the answer tiles are drawn through CARD-295's grid routine.

    Two halves, because a guard alone would not be a measurement of the reuse
    and a drive alone would not stop the next copy:

    * **the guard** — :func:`stroke_violations`, default-DENY over everything
      in this card's two writer modules that can rule a line, with a
      **derived** exemption (a function that takes the ``grid``). Its controls
      below are deliberately *not* one per branch of the detector: a
      module-level stroke, a helper nested inside an exempt function, a method
      bound to a name, a rectangle whose paint is decided elsewhere. Those
      are the shapes the guard was **not** written from, which is what makes
      them evidence about its completeness rather than about its branches;
    * **the drive** — the routine is run on a real
      :class:`~nonogram.export.layout.AnswerTile`, which is **not** a
      ``Layout`` and carries no clue gutter, and every line it emits is held
      against that tile's own :class:`~nonogram.export.layout.GridLine`\\ s.
      CARD-295's own round reported that this reuse "does not reach"; it
      does, and this is the cell that drives it rather than reading it.
    """

    def test_neither_writer_rules_a_line_outside_the_exemption(self) -> None:
        for module in _GUARDED:
            assert stroke_violations(_source_of(module)) == [], module.__name__

    def test_the_exemption_set_is_derived_and_not_everything(self) -> None:
        """The guard is not default-ALLOW underneath (ADR-0039/R2).

        Three readings, because "derived rather than hand-listed" has been
        satisfied literally before by a predicate that admitted everything:
        the set is non-empty where lines are drawn, it is a **strict** subset
        of the module's functions, and the module that draws no line at all
        exempts nothing.
        """
        answer = _source_of(book_answer_vector)
        exempt = exempt_functions(answer)
        assert exempt, "no function in the answer writer takes the grid"
        assert set(exempt) < set(_all_functions(answer))
        assert exempt_functions(_source_of(book_toc_vector)) == [], (
            "the table of contents rules no line, so it may exempt nothing"
        )

    def test_the_only_exempt_stroker_is_the_solution_dependent_one(self) -> None:
        """Which functions actually use their exemption, read off the module.

        The exemption *set* is derived; this records which of its members are
        load-bearing, so a later card that adds a third exemption has to change
        this cell and say why.

        **Two names, not one, since review cycle 2.** The reading used to be
        the same two-name ``_STROKERS`` tuple the guard used, with a fill
        admitted by its ``paint`` argument, so it saw only the join. It now
        reads all eight derived doors and consults no ``paint``, which brings
        ``draw_answer_cells``' filled cells into view beside
        ``draw_solved_joins``' lines. Both are exempt for the one reason the
        exemption encodes — each is a mark whose *existence* is a function of
        the solution, which no routine that does not take the grid could place
        — so the widening records the same property over a wider vocabulary.
        The cell's name predates it and G-6 forbids renaming a test.
        """
        strokes = {
            owner.name
            for node, owner in _strokers_of(_source_of(book_answer_vector))
            if owner is not None
        }
        assert strokes == {"draw_answer_cells", "draw_solved_joins"}
        # Both hold the grid, which is what makes them exempt rather than
        # tolerated: the set above is a subset of the derivation's own.
        assert strokes <= set(exempt_functions(_source_of(book_answer_vector)))

    def test_the_watched_set_is_derived_from_the_class_and_not_listed(self) -> None:
        """F-297-01: the stroker vocabulary is a measurement of ``ContentStream``.

        Three readings, and the third is the one that matters. The set is
        exactly the public members whose own output carries a path operator,
        it is a **strict** subset of that class's public surface (so the
        derivation is not "everything"), and every door review cycle 1 drove a
        grid walk through is in it.
        """
        members = set(_public_members(ContentStream))
        assert set(_STROKERS) < members, sorted(members - set(_STROKERS))
        assert _UNCLASSIFIED_DOORS == (), _UNCLASSIFIED_DOORS
        # The eight this file measures, named so a change to the class shows
        # up here as a diff rather than as a silently wider or narrower guard.
        assert set(_STROKERS) == {
            "begin_path",
            "close_path",
            "curve",
            "line",
            "line_to",
            "paint",
            "rectangle",
            "round_mark",
        }, sorted(_STROKERS)
        assert len(members) == 16, sorted(members)
        for name in _STROKERS:
            assert set(_DOOR_EMITS[name]) & _PATH_OPERATORS, (name, _DOOR_EMITS[name])

    def test_every_unwatched_member_is_excluded_by_its_own_measurement(self) -> None:
        """An exclusion is a statement with a reason, not an absence.

        For each public member the guard does not watch: it is named in
        :data:`_NOT_A_DOOR_BECAUSE`, it really emitted no path operator when
        driven, and every operator it *did* emit is named in its own reason —
        so a reason cannot drift away from the measurement it stands on.
        """
        unwatched = set(_public_members(ContentStream)) - set(_STROKERS)
        assert set(_NOT_A_DOOR_BECAUSE) == unwatched, (
            sorted(unwatched - set(_NOT_A_DOOR_BECAUSE)),
            sorted(set(_NOT_A_DOOR_BECAUSE) - unwatched),
        )
        assert len(unwatched) == 8, sorted(unwatched)
        for name, reason in _NOT_A_DOOR_BECAUSE.items():
            emitted = _DOOR_EMITS[name]
            assert not (set(emitted) & _PATH_OPERATORS), (name, emitted)
            assert reason.strip(), name
            if emitted:
                words = _re.findall(r"[A-Za-z*]+", reason)
                for operator in set(emitted):
                    assert operator in words, (name, operator, reason)
            else:
                assert "emits no operator at all" in reason, (name, reason)

    def test_a_member_added_to_the_class_is_watched_without_being_listed(
        self,
    ) -> None:
        """The default-DENY, driven: a new door needs no edit to be watched.

        A subclass carrying one more drawing method is handed to the same
        derivation, and the method is in the watched set — the property the
        hand-listed tuple did not have, and the one that would have caught
        F-297-01 the day ``begin_path`` was added.

        **CARD-298 widened the two readings below, and the widening is the
        F2-01 fix showing through.** They used to be ``doors == ("zigzag",)``:
        under ``vars(cls)`` a subclass's reading held its *own* member and
        nothing it inherited, so this cell measured a one-member class and the
        eight doors the subclass really exposes were outside it. Since
        :func:`_public_members` reads ``dir(cls)``, the subclass's doors are
        the base's eight **plus** ``zigzag`` — which is both a stronger claim
        and the claim this test meant to make. The assertion is widened, not
        relaxed: ``zigzag`` is still required to be in the set and still
        required to be reported unclassified without a probe.
        """

        class _WithOneMoreDoor(ContentStream):
            def zigzag(self, x: float, y: float) -> None:
                self.begin_path(x, y)
                self.line_to(x + 1, y + 1)
                self.paint("stroke")

        # Driven through the shipped derivation, not a copy of it: with a probe
        # entry the new door is classified by what it emits, and WITHOUT one it
        # is watched anyway and reported as unclassified. Both halves are the
        # default-DENY.
        saved = dict(_DOOR_PROBE)
        try:
            _DOOR_PROBE["zigzag"] = (1.0, 2.0)
            doors, emits, unclassified = _content_stream_doors(_WithOneMoreDoor)
            assert set(doors) == set(_STROKERS) | {"zigzag"}, doors
            assert unclassified == (), unclassified
            assert set(emits["zigzag"]) & _PATH_OPERATORS, emits["zigzag"]
            del _DOOR_PROBE["zigzag"]
            doors, _, unclassified = _content_stream_doors(_WithOneMoreDoor)
            assert set(doors) == set(_STROKERS) | {"zigzag"}, doors
            assert unclassified == ("zigzag",), unclassified
        finally:
            _DOOR_PROBE.clear()
            _DOOR_PROBE.update(saved)

    # ----------------------------------------------------------------------
    # CARD-298 / F2-01 — the derivation sees a door a BASE class contributes
    # ----------------------------------------------------------------------

    def test_an_inherited_drawing_door_is_watched(self) -> None:
        """F2-01's own case, rebuilt: a mixin **ahead** of ``ContentStream``.

        CARD-297 review cycle 2 built this and the route was **ADMITTED**:
        with ``_public_members`` reading ``vars(cls)``, a ``hatch`` method
        contributed by a base class was not in the class's own ``__dict__``,
        so the derivation never drove it, never classified it and never
        reported it — ``_UNCLASSIFIED_DOORS`` was empty and both guard cells
        were green while a ``stream.hatch`` grid walk went through.

        The mixin is **first** in the bases, which is the half that matters:
        the class's own surface is left at sixteen exactly as the shipped
        class's is, so nothing about the class's own ``__dict__`` tells the
        two apart. The door is found through the MRO or it is not found.
        """

        class _Hatching:
            def hatch(self, x: float, y: float, pitch: float) -> None:
                self.begin_path(x, y)
                self.line_to(x + pitch, y + pitch)
                self.paint("stroke")

        class _Mixed(_Hatching, ContentStream):
            pass

        # The class's own surface is empty, exactly as cycle 2 arranged it:
        # a reading taken from `vars` alone cannot see this door at all.
        assert [n for n in vars(_Mixed) if not n.startswith("_")] == []
        assert "hatch" not in vars(ContentStream)
        assert "hatch" in _public_members(_Mixed)

        doors, _, unclassified = _content_stream_doors(_Mixed)
        assert "hatch" in doors, doors
        # And it is reported, not silently watched: the live guard cell asserts
        # `_UNCLASSIFIED_DOORS == ()`, so a door nobody has classified reds
        # there rather than being absorbed.
        assert unclassified == ("hatch",), unclassified

    def test_the_derivation_is_unmoved_on_the_shipped_class(self) -> None:
        """And the fix changes **nothing** at HEAD, which is why it is safe.

        ``ContentStream`` inherits only ``object``, whose public surface is
        empty, so the ``dir()`` reading and the retired ``vars()`` reading are
        the same sixteen names. Asserted as a set equality rather than as a
        count, so a member that appeared *and* one that vanished could not
        cancel.
        """
        assert ContentStream.__mro__ == (ContentStream, object)
        own = sorted(name for name in vars(ContentStream) if not name.startswith("_"))
        assert _public_members(ContentStream) == own, (
            _public_members(ContentStream),
            own,
        )
        assert len(own) == 16, own
        assert len(_STROKERS) == 8, _STROKERS

    def test_the_derivation_is_not_simply_returning_everything(self) -> None:
        """The control the brief for this fix asked for, in both directions.

        *"A ``dir()``-based version that silently returned everything would
        pass exactly as a correct one would."* It would not, and this is why
        rather than a sentence saying so:

        * **no name it returns is private**, so the ~26 dunders ``dir()``
          itself reports are out — a version that kept them would drive
          ``__init__``, ``__class__`` and the rest through
          :func:`_content_stream_doors`, land every one of them in
          ``unclassified`` (no :data:`_DOOR_PROBE` entry), and red the live
          ``_UNCLASSIFIED_DOORS == ()`` cell on the shipped class;
        * **it still discriminates**: an inherited member that paints nothing
          and has a probe is classified as not-a-door, so the widened
          derivation is not a set that swallowed its own class.

        The second bullet is the one a "return everything" version passes and
        a *correct* one has to earn, so it is driven rather than argued.
        """
        assert all(not name.startswith("_") for name in _public_members(ContentStream))
        assert len(dir(ContentStream)) > len(_public_members(ContentStream)) + 20

        class _Describing:
            def describe(self, width: float) -> float:
                return self.to_points(width)

        class _Mixed(_Describing, ContentStream):
            pass

        saved = dict(_DOOR_PROBE)
        try:
            _DOOR_PROBE["describe"] = (10.0,)
            doors, emits, unclassified = _content_stream_doors(_Mixed)
            assert "describe" in _public_members(_Mixed)
            assert "describe" not in doors, doors
            assert emits["describe"] == (), emits["describe"]
            assert unclassified == (), unclassified
            # The eight real doors are still exactly the eight, so widening
            # the surface did not widen the verdict.
            assert set(doors) == set(_STROKERS), sorted(set(doors) ^ set(_STROKERS))
        finally:
            _DOOR_PROBE.clear()
            _DOOR_PROBE.update(saved)

    @pytest.mark.parametrize(
        "planted,expected",
        [
            pytest.param(
                "stream.line(1, 2, 3, 4)\n",
                "module level rules a line",
                id="module-level-stroke",
            ),
            pytest.param(
                "def draw(stream, tile, grid):\n"
                "    def helper(stream):\n"
                "        stream.line(1, 2, 3, 4)\n"
                "    helper(stream)\n",
                "helper rules a line",
                id="helper-nested-inside-an-exempt-function",
            ),
            pytest.param(
                "def caption(stream, text):\n    rule = stream.line\n    rule(1, 2, 3, 4)\n",
                "caption binds .line to a name",
                id="method-bound-to-a-name",
            ),
            pytest.param(
                "def caption(stream, box):\n    stream.rectangle(1, 2, 3, 4)\n",
                "caption rules a rectangle",
                id="rectangle-stroked-by-default",
            ),
            pytest.param(
                "def caption(stream, how):\n    stream.rectangle(1, 2, 3, 4, paint=how)\n",
                "caption rules a rectangle",
                id="rectangle-whose-paint-is-decided-elsewhere",
            ),
            pytest.param(
                "class Pen:\n    def stroke(self, stream):\n        stream.line(1, 2, 3, 4)\n",
                "stroke rules a line",
                id="stroke-inside-a-class",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    for line in tile.vertical_lines:\n"
                "        stream.begin_path(line.position, line.start)\n",
                "draw rules a begin_path",
                id="a-path-started-without-the-grid",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    for line in tile.vertical_lines:\n"
                "        stream.line_to(line.position, line.end)\n",
                "draw rules a line_to",
                id="a-path-extended-without-the-grid",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    stream.paint('stroke')\n",
                "draw rules a paint",
                id="a-path-painted-without-the-grid",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    for line in tile.vertical_lines:\n"
                "        stream.rectangle(\n"
                "            line.position, line.start, line.position + 1,\n"
                "            line.end, paint='fill',\n"
                "        )\n",
                "draw rules a rectangle",
                id="grid-walked-as-thin-filled-rectangles",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    stream.curve(1, 2, 3, 4, 5, 6)\n",
                "draw rules a curve",
                id="a-curve-is-a-path-too",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    stream.round_mark(1, 2, 3)\n",
                "draw rules a round_mark",
                id="a-round-mark-is-a-path-too",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    stream.close_path()\n",
                "draw rules a close_path",
                id="a-bare-close-path",
            ),
            pytest.param(
                "def draw(stream, tile):\n"
                "    paint = stream.paint\n"
                "    paint('stroke')\n",
                "draw binds .paint to a name",
                id="a-new-door-bound-to-a-name",
            ),
        ],
    )
    def test_the_guard_catches_a_grid_walk_in_each_of_these_shapes(
        self, planted: str, expected: str
    ) -> None:
        found = stroke_violations(planted)
        assert len(found) == 1, found
        assert found[0].endswith(expected), found

    def test_review_cycle_1s_own_artefact_is_now_a_violation(self) -> None:
        """F-297-01's demonstration, re-fired as a cell.

        Cycle 1 built a complete grid walk through ``begin_path``/``line_to``/
        ``paint`` and the guard returned ``[]`` for it, then fed the same code
        a real :class:`ContentStream` and read back three ruled lines
        (``'24 228 m'``, ``'24 12 l'`` …) — a whole grid on a page with zero
        violations reported. Both halves are asserted here: the source is now
        refused, *and* the page it draws really does carry the stroked lines
        that made it a hole rather than a curiosity.
        """
        source = (
            "def draw(stream, tile):\n"
            "    for line in tile.vertical_lines:\n"
            "        stream.begin_path(line.position, line.start)\n"
            "        stream.line_to(line.position, line.end)\n"
            "    stream.paint('stroke')\n"
        )
        found = stroke_violations(source)
        assert found, "cycle 1's grid walk is admitted again"
        assert [place.split(": ")[1] for place in found] == [
            "draw rules a begin_path",
            "draw rules a line_to",
            "draw rules a paint",
        ], found

        # The same code, run. Three ruled lines and one S, through doors the
        # hand-listed tuple did not watch.
        stream = ContentStream(width_px=100.0, height_px=240.0, dpi=72)
        namespace: dict = {}
        exec(compile(source, "<cycle1-artefact>", "exec"), namespace)

        class _Line:
            def __init__(self, position: float) -> None:
                self.position, self.start, self.end = position, 12.0, 228.0

        class _Tile:
            vertical_lines = (_Line(24.0), _Line(48.0), _Line(72.0))

        namespace["draw"](stream, _Tile())
        assert stream.operators == (
            "24 228 m",
            "24 12 l",
            "48 228 m",
            "48 12 l",
            "72 228 m",
            "72 12 l",
            "S",
        ), stream.operators

    def test_a_fill_is_not_a_rule_and_is_admitted(self) -> None:
        """The negative control: the guard is not "no rectangle anywhere".

        **What admits this one changed in review cycle 2.** It used to be the
        ``paint="fill"`` literal — an exception the guard made by hand under a
        set that read as derived, which left a grid walked as thin filled
        rectangles admitted everywhere (now a case of
        ``test_the_guard_catches_a_grid_walk_in_each_of_these_shapes``). What
        admits it now is the one derived exemption: the function holds the
        grid. The companion below is the half that would have been missing.
        """
        assert (
            stroke_violations(
                'def cells(stream, grid):\n'
                '    stream.rectangle(1, 2, 3, 4, paint="fill")\n'
            )
            == []
        )

    def test_the_same_fill_without_the_grid_is_denied(self) -> None:
        """The exemption is what admits a fill, not the word "fill".

        One character of difference from the cell above — the parameter the
        exemption is derived from — and the same filled rectangle is refused.
        That is the pair that makes the admission a reading of the exemption
        rather than a blanket pass for fills.
        """
        found = stroke_violations(
            'def cells(stream, tile):\n'
            '    stream.rectangle(1, 2, 3, 4, paint="fill")\n'
        )
        assert len(found) == 1, found
        assert found[0].endswith("cells rules a rectangle"), found

    def test_the_routine_draws_a_real_answer_tile_that_is_not_a_layout(self) -> None:
        """The drive. An ``AnswerTile`` is not a ``Layout``, and this is it."""
        from nonogram.export.layout import AnswerTile, Layout as _Layout

        spec = BookPDFGenerator(_book()).page_spec(11)
        page = compute_answer_page_layout([(10, 10)] * 4, 4, spec)
        tile = page.tiles[0]
        assert isinstance(tile, AnswerTile) and not isinstance(tile, _Layout)
        assert not hasattr(tile, "clue_entries")
        assert len(tile.vertical_lines) == 11 and len(tile.horizontal_lines) == 11

        grid = [[(row + column) % 3 != 0 for column in range(10)] for row in range(10)]
        stream = ContentStream(width_px=page.width, height_px=page.height, dpi=page.dpi)
        book_answer_vector.draw_solved_grid(stream, tile, grid)
        (written,) = pdf_vector.content_streams(_written([stream]))

        drawn = {
            (float(x1), float(y1), float(x2), float(y2))
            for x1, y1, x2, y2 in _LINE.findall(written)
        }
        expected = set()
        for line in tile.vertical_lines:
            expected.add(
                (
                    _pt(line.position, page.dpi),
                    _flip(line.start, page.height, page.dpi),
                    _pt(line.position, page.dpi),
                    _flip(line.end, page.height, page.dpi),
                )
            )
        for line in tile.horizontal_lines:
            expected.add(
                (
                    _pt(line.start, page.dpi),
                    _flip(line.position, page.height, page.dpi),
                    _pt(line.end, page.dpi),
                    _flip(line.position, page.height, page.dpi),
                )
            )
        assert expected <= drawn, sorted(expected - drawn)
        assert len(expected) == 22

    def test_the_comparison_above_can_fail(self) -> None:
        """One line moved by a pixel, and the comparison notices."""
        import dataclasses

        spec = BookPDFGenerator(_book()).page_spec(11)
        page = compute_answer_page_layout([(10, 10)] * 4, 4, spec)
        tile = page.tiles[0]
        moved = dataclasses.replace(
            tile,
            vertical_lines=(
                dataclasses.replace(
                    tile.vertical_lines[0], position=tile.vertical_lines[0].position + 1
                ),
                *tile.vertical_lines[1:],
            ),
        )
        grid = [[False] * 10 for _ in range(10)]
        streams = []
        for candidate in (tile, moved):
            stream = ContentStream(
                width_px=page.width, height_px=page.height, dpi=page.dpi
            )
            book_answer_vector.draw_solved_grid(stream, candidate, grid)
            streams.append(stream)
        one, two = pdf_vector.content_streams(_written(streams))
        assert set(_LINE.findall(one)) != set(_LINE.findall(two))


def _strokers_of(source: str) -> List[Tuple[object, object]]:
    """Every call through a drawing door in ``source``, with its owner.

    The same vocabulary :func:`stroke_violations` denies from — eight derived
    doors, no exception for what a call paints — so the two halves of AC-3's
    structural claim can no longer disagree about what counts as a mark. They
    shared a two-name tuple until review cycle 2; F-297-01 is that both halves
    were blind to the same shapes, not that one was.
    """
    tree = _ast.parse(source)
    owner = _enclosing(tree)
    out = []
    for node in _ast.walk(tree):
        if (
            isinstance(node, _ast.Call)
            and isinstance(node.func, _ast.Attribute)
            and node.func.attr in _STROKERS
        ):
            out.append((node, owner[id(node)]))
    return out


def _pt(pixels: float, dpi: int) -> float:
    """``pixels`` as the points a content stream writes, rounded as it rounds."""
    return round(pixels * 72.0 / dpi, 3)


def _flip(pixels: float, height: float, dpi: int) -> float:
    """A row counted down from the page top, as the PDF y counted up."""
    return _pt(height - pixels, dpi)


# --------------------------------------------------------------------------
# AC-5 — the difficulty dots on a tile header are the priced primitive
# --------------------------------------------------------------------------


def _solution_tile_bands(spec) -> List[Tuple[int, int, int, int]]:
    """Every band a packed solution tile reserves inside itself, on ``spec``.

    CARD-228's own derivation, re-run here rather than quoted: the band runs
    from the tile's own usable top to one pixel above its drawing, across the
    tile's whole usable width. ``SOLVED_TILE_CAPACITIES`` is ``(2, 4)``, so a
    trim yields ``2 + 4`` such boxes.
    """
    boxes: List[Tuple[int, int, int, int]] = []
    clues = ((2, 2), (2, 2), (2, 2), (2, 2), (2, 2))
    for capacity in (2, 4):
        packed = compute_packed_solved_layout([(clues, clues)] * capacity, capacity, spec)
        assert packed is not None, capacity
        for slot in packed.slots:
            placement = slot.page
            assert placement is not None
            boxes.append(
                (
                    placement.usable_left,
                    placement.usable_top,
                    placement.usable_right,
                    placement.drawing_top - 1,
                )
            )
    return boxes


class TestAnswerTileHeader_DifficultyDotsAreRound:
    """AC-5: a tile header's difficulty dots render as round shapes.

    **What this measures, and the limit it states out loud.** A solution
    tile's header prints its difficulty as a *word* today — ``band_identity``
    composes ``"Puzzle 12 · Hard"`` and nothing else — so there are **no dots
    on an answer page to read back**: ``ContentStream.round_mark`` has zero
    callers in ``src/`` (asserted below), and CARD-228's own AC-5 says why —
    *"what each caller actually puts there is CARD-207/229/231/233's
    business"*. **CARD-233** is the card that gives a tile one header, it is
    queued and gated, and this card's G-1 forbids drawing its design here.

    So AC-5 is taken exactly as CARD-228 left it for its adopting cards —
    *"the adopting cards re-run AC-5 against their own box"* — in the new
    medium: the box is the **real** narrowest band a packed solution tile
    reserves, COMP-007 measures the ladder for it, the ladder is drawn through
    the **one** round-shape primitive CARD-294 priced, and poppler is asked
    whether what came out is round at the stated diameter. Nothing is wired
    into a page, which is what keeps this inside G-1 — and the one claim it
    does **not** make is that an answer page prints dots, which
    :meth:`test_no_answer_page_draws_a_round_mark_today` states as a fact
    rather than leaving to be discovered.
    """

    @pytest.fixture(scope="class")
    @staticmethod
    def box() -> Tuple[int, int, int, int]:
        spec = BookPDFGenerator(_kdp_min_book()).page_spec(11)
        bands = _solution_tile_bands(spec)
        assert len(bands) == 6
        return min(bands, key=lambda band: band[2] - band[0])

    @staticmethod
    def _drawn(box: Tuple[int, int, int, int], dpi: int):
        """The ladder of ``box``, drawn through ``round_mark`` on its own sheet.

        Translated to the box's own corner — a translation, not a
        measurement — so the render is the box and a two-pixel border rather
        than a whole 10 cm page at 1200 DPI.
        """
        left, top, right, bottom = box
        dots = difficulty_dots(
            left, top, right, bottom, filled=len(TIERS), total=len(TIERS)
        )
        assert dots is not None, box
        stream = ContentStream(
            width_px=right - left + 5, height_px=bottom - top + 5, dpi=dpi
        )
        stream.fill_grey(book_vector_draw.INK_GREY)
        for one in dots.dots:
            radius = (one[2] - one[0]) / 2.0
            stream.round_mark(
                one[0] - left + 2 + radius, one[1] - top + 2 + radius, radius
            )
        return dots, stream

    def test_the_box_is_the_narrowest_band_a_solution_tile_reserves(self, box) -> None:
        spec = BookPDFGenerator(_kdp_min_book()).page_spec(11)
        bands = _solution_tile_bands(spec)
        assert box in bands
        assert all(box[2] - box[0] <= other[2] - other[0] for other in bands)

    def test_the_geometry_fits_three_dots_in_that_box(self, box) -> None:
        dots, _ = self._drawn(box, 1200)
        assert dots.total == len(TIERS) == 3
        assert dots.diameter > 0
        assert box[0] < dots.left and dots.right < box[2]
        assert box[1] < dots.top and dots.bottom < box[3]

    @needs_pdftoppm
    def test_poppler_reads_three_round_marks_at_the_stated_diameter(
        self, box, tmp_path
    ) -> None:
        dots, stream = self._drawn(box, 1200)
        data = _written([stream])
        page = pdf_vector.rendered_page(data, 1200, out_dir=tmp_path)
        image = _Image.fromarray(page.astype("uint8"), mode="L")
        marks = round_ink.round_marks(image)
        assert len(marks) == dots.total, [mark.box for mark in marks]
        for mark in marks:
            assert mark.is_round, (mark.aspect, mark.fill)
            assert abs(mark.width - dots.diameter) <= 2, (mark.width, dots.diameter)
            assert abs(mark.height - dots.diameter) <= 2, (mark.height, dots.diameter)

    @needs_pdftoppm
    def test_the_roundness_reading_can_fail(self, box, tmp_path) -> None:
        """The control (ADR-0039/R1): the same ladder as squares is not round.

        Drawn at the same boxes, with the same fill, through the rectangle
        primitive instead — so what changes between this cell and the one
        above is the shape alone.
        """
        dots, _ = self._drawn(box, 1200)
        left, top = box[0], box[1]
        stream = ContentStream(
            width_px=box[2] - left + 5, height_px=box[3] - top + 5, dpi=1200
        )
        stream.fill_grey(book_vector_draw.INK_GREY)
        for one in dots.dots:
            stream.rectangle(
                one[0] - left + 2,
                one[1] - top + 2,
                one[2] - left + 2,
                one[3] - top + 2,
                paint="fill",
            )
        page = pdf_vector.rendered_page(_written([stream]), 1200, out_dir=tmp_path)
        image = _Image.fromarray(page.astype("uint8"), mode="L")
        assert round_ink.round_marks(image) == []

    def test_the_vector_ladder_is_the_geometry_the_raster_ladder_draws(
        self, box
    ) -> None:
        """One implementation, three users: the boxes are the same boxes.

        The raster glyph is ``_draw_difficulty_dots``'s ellipses; both read
        :func:`~nonogram.export.layout.difficulty_dots` for the same box, so
        the comparison is of the two drawings' own inputs rather than of two
        re-derivations.
        """
        left, top, right, bottom = box
        canvas = _Image.new("RGB", (right + 3, bottom + 3), BACKGROUND)
        raster = _draw_difficulty_dots(
            _ImageDraw.Draw(canvas), _Tier.HARD.value, left, top, right, bottom
        )
        vector, _ = self._drawn(box, 1200)
        assert raster is not None
        assert raster.dots == vector.dots
        assert raster.diameter == vector.diameter

    def test_no_answer_page_draws_a_round_mark_today(self, recorded) -> None:
        """The stated limit, as a test rather than as prose (G-1).

        A ``c`` operator is how :meth:`ContentStream.round_mark` draws a
        quadrant, and it is the only thing in this card's writers that could
        emit one. A page kind that starts drawing dots reds here, which is
        CARD-233's own signal to update AC-5 rather than to discover it.
        """
        for text in pdf_vector.content_streams(
            _written(recorded.answer_streams() + recorded.toc_streams())
        ):
            assert " c\n" not in text and not text.rstrip().endswith(" c")
        assert "round_mark" not in _source_of(book_answer_vector)
        assert "round_mark" not in _source_of(book_toc_vector)


# --------------------------------------------------------------------------
# AC-6 — the answer caption still holds CON-020's floor, read off the stream
# --------------------------------------------------------------------------

#: CON-020's floor for reader-facing interior text, in points.
_FLOOR_PT = 10.0

#: Where the two media's answer captions differ, and **why** — one entry per
#: divergence, as ``{whole caption: (what the raster page set, what the vector
#: page sets)}``.
#:
#: Review cycle 1's F-297-03: every title and caption reading in this card
#: filtered by membership in the set of **unclipped** strings, so a clipped
#: caption landed in the "omitted" bucket on both sides and a one-character
#: clip difference passed 596 cells. Measured once the readings admit clipped
#: strings, the two media **already** differ — today, on the 10 x 10 cm minimum
#: trim, in a shipped book:
#:
#: * both clip against the **same** measure, 492 px, which is COMP-007's
#:   ``caption_slot`` figure and not either renderer's;
#: * the raster page measures ``'Puzzle 2 — Owl in a P…'`` with
#:   ``FreeTypeFont.getlength`` at 491.98 px and keeps it;
#: * the vector page measures the same string as a sum of the embedded face's
#:   ``/Widths`` at 492.87 px and runs the loop one more step.
#:
#: 0.89 px across a 492 px string — the "fraction of a dot's advance" this
#: card's own TOC header admits the two engines agree to, landing on an integer
#: boundary. **Neither medium is wrong**: ``/Widths`` is what a PDF viewer sums,
#: so each page clips by the measure its own reader will use, which is the port
#: being faithful rather than broken. It is recorded here because it is a
#: product fact no cell stated, and exact agreement is **not** achievable
#: without one medium measuring with the other's engine.
_DECLARED_CLIP_DIVERGENCE = {
    "Puzzle 2 — Owl in a Pine": (
        "Puzzle 2 — Owl in a P…",
        "Puzzle 2 — Owl in a …",
    ),
}


def _caption_reading(text: str, wanted) -> Optional[str]:
    """``text`` as the caption it is a reading of — whole or clipped — or ``None``.

    The clip loop both media run is ``clipped[:-2] + "…"`` applied until the
    string fits, so every clipped reading is ``caption[:k] + "…"``. Admitting
    those is the whole of F-297-03's fix: a reading that is not in the set of
    unclipped captions is a *clip*, not an omission, and the two are different
    facts about a printed book.
    """
    if text in wanted:
        return text
    if text.endswith("…") and len(text) > 1:
        stem = text[:-1]
        if any(caption.startswith(stem) and caption != stem for caption in wanted):
            return text
    return None


def _caption_behind(reading: str, wanted) -> str:
    """The whole caption ``reading`` is a reading of."""
    if reading in wanted:
        return reading
    stem = reading[:-1]
    matches = sorted(
        caption for caption in wanted if caption.startswith(stem) and caption != stem
    )
    assert len(matches) == 1, (reading, matches)
    return matches[0]


def _unexplained_clip_divergences(vector, raster, wanted) -> List[Tuple[str, ...]]:
    """Captions whose two media disagree **outside** the declared table.

    Both arguments are the readings each medium actually set, clips included.
    Grouped by the caption behind each reading, so "both omitted it" and "both
    printed it clipped to the same string" are both agreement and anything else
    is reported.
    """
    out: List[Tuple[str, ...]] = []
    for caption in sorted(wanted):
        mine = sorted(r for r in vector if _caption_behind(r, wanted) == caption)
        theirs = sorted(r for r in raster if _caption_behind(r, wanted) == caption)
        if mine == theirs:
            continue
        declared = _DECLARED_CLIP_DIVERGENCE.get(caption)
        if declared is not None and theirs == [declared[0]] and mine == [declared[1]]:
            continue
        out.append((caption, tuple(theirs), tuple(mine)))
    return out


class TestAnswerPages_CaptionHoldsTheFloorInTheStream:
    """AC-6 (CON-020): the answer caption's ``Tf`` size is at or above 10 pt.

    Read off the written stream's own ``Tf`` operand — a *point* size against
    the page, which is what makes this a device-independent claim in the new
    medium where the raster page could only be measured in pixels at one DPI.

    **Conditional on the profile, exactly as**
    ``tests/test_book_interior_type_floor.py:369`` **already is**: the
    caption is *omitted* rather than overlapped on the 10 x 10 cm minimum
    trim (CARD-197's AC-6), so requiring one there would fail for the wrong
    reason. The condition is not a licence either — the omission itself is
    asserted, and asserted as **agreement with the raster page's own
    verdict** rather than against a profile name, so a vector writer that
    omitted a caption Book 1 prints would red.
    """

    @staticmethod
    def _captions(recorded: _Recorded) -> List[str]:
        """Every caption string the book's answer key would print."""
        wanted = [
            answer_caption(number, title)
            for _, number, _, title in recorded.answers
        ]
        wanted += [
            answer_caption(
                number, answer_title(titles.get(str(puzzle_id)), payload.name)
            )
            for plan, payloads, _, titles in recorded.packed
            for number, (puzzle_id, payload) in zip(plan.numbers, payloads)
        ]
        return wanted

    def test_every_caption_the_stream_sets_is_at_or_above_the_floor(
        self, recorded, profile
    ) -> None:
        wanted = set(self._captions(recorded))
        assert wanted, "the book has no answer captions to look for"
        found = [
            (size, text)
            for text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
            for size, text in _shows(text)
            if text in wanted
        ]
        for size, text in found:
            assert size >= _FLOOR_PT, (size, text)
        if profile != "min-trim":
            assert found, (
                "Book 1's answer key prints captions, so an empty reading here "
                "is the writer failing to set them, not CARD-197's omission"
            )

    @staticmethod
    def _readings(recorded: _Recorded, wanted) -> Tuple[List[str], List[str]]:
        """What each medium actually set, **clips included** (F-297-03).

        The filter is :func:`_caption_reading`, not membership in ``wanted``:
        until review cycle 2 every caption reading in this card tested
        ``text in wanted``, so a clipped caption was absent from both sides'
        sets and counted as an omission in both media. That is the blindness
        F-297-03 names — the clip point is the one axis the two media are known
        to measure differently.
        """
        vector = [
            reading
            for stream_text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
            for _, text in _shows(stream_text)
            if (reading := _caption_reading(text, wanted)) is not None
        ]
        raster = [
            reading
            for _, text, names in recorded.text
            if "_draw_solved_slot" in names
            and (reading := _caption_reading(text, wanted)) is not None
        ]
        return vector, raster

    def test_the_two_media_omit_the_same_captions(self, recorded) -> None:
        """The omission is the raster page's own verdict, not a profile name.

        **About omission, and no longer blind to clipping.** The two sides are
        compared as the set of *captions* each medium printed something for, a
        clipped reading counting as printed — so a medium that omitted a
        caption the other clipped now reds here, where before cycle 2 both
        would have read as omissions and agreed.
        """
        wanted = set(self._captions(recorded))
        vector, raster = self._readings(recorded, wanted)
        mine = {_caption_behind(reading, wanted) for reading in vector}
        theirs = {_caption_behind(reading, wanted) for reading in raster}
        assert mine == theirs, (sorted(mine), sorted(theirs))

    def test_the_two_media_clip_the_same_captions_to_the_same_string(
        self, recorded, profile
    ) -> None:
        """F-297-03: the caption **string**, not its presence in a set.

        Per caption, the readings the two media set are compared element for
        element, so the three outcomes a slot really has — printed whole,
        clipped to a particular string, omitted — are distinguishable instead
        of collapsing into two. Any disagreement outside
        :data:`_DECLARED_CLIP_DIVERGENCE` fails here, which is what makes a
        clip that moves by one character red.
        """
        wanted = set(self._captions(recorded))
        vector, raster = self._readings(recorded, wanted)
        assert vector or profile == "min-trim", "the vector pages set no caption"
        assert (
            _unexplained_clip_divergences(vector, raster, wanted) == []
        ), _unexplained_clip_divergences(vector, raster, wanted)

    def test_the_min_trim_really_does_clip_one_caption_in_each_medium(self) -> None:
        """Non-vacuity: the comparison above has a clip to compare.

        Without this the element-for-element cell could pass on two media that
        never clip anything, which is how F-297-03's reading survived. Measured
        on the 10 x 10 cm trim, where a packed page prints one caption whole and
        clips the next.
        """
        recorded = _recorded("min-trim")
        wanted = set(self._captions(recorded))
        vector, raster = self._readings(recorded, wanted)
        assert [r for r in vector if r.endswith("…")], vector
        assert [r for r in raster if r.endswith("…")], raster
        # And the declared table is the pair this profile really sets, so an
        # entry that stops being true reds here rather than going stale.
        for caption, (raster_text, vector_text) in _DECLARED_CLIP_DIVERGENCE.items():
            assert [
                r for r in raster if _caption_behind(r, wanted) == caption
            ] == [raster_text], raster
            assert [
                r for r in vector if _caption_behind(r, wanted) == caption
            ] == [vector_text], vector

    def test_the_declared_clip_divergence_is_one_step_of_the_same_loop(self) -> None:
        """The reason behind the declaration, machine-checked rather than told.

        For each declared pair: both readings are clips of the same caption,
        the vector's is exactly **one step** of the shared ``[:-2] + "…"`` loop
        shorter (two source characters off, one ellipsis on), there is an integer measure at which the two shipped clip
        functions really produce exactly those two strings, and at such a
        measure the two engines' widths of the raster string **straddle** it by
        under one pixel. So the divergence is one rounding boundary between two
        font engines and not a second clip rule.
        """
        from nonogram.admin.book_pdf_generator import _clipped_to, _guide_face

        face = interior_face_metrics()
        size = book_answer_vector.answer_type(300).caption_size_px
        font = _guide_face(int(size))
        for caption, (raster_text, vector_text) in _DECLARED_CLIP_DIVERGENCE.items():
            assert raster_text.endswith("…") and vector_text.endswith("…")
            assert caption.startswith(raster_text[:-1]), (caption, raster_text)
            assert caption.startswith(vector_text[:-1]), (caption, vector_text)
            # One step of ``clipped[:-2] + "…"`` drops two characters and adds
            # one, so exactly one step is one character of length.
            assert len(raster_text) - len(vector_text) == 1, (raster_text, vector_text)
            whole = book_vector_draw.advance_px(caption, size, face)
            straddle = [
                measure
                for measure in range(1, int(whole) + 2)
                if _clipped_to(caption, font, measure) == raster_text
                and book_answer_vector._clipped_to_measure(
                    caption, size, face, measure
                )
                == vector_text
            ]
            assert straddle, (caption, raster_text, vector_text)
            measure = straddle[0]
            raster_width = font.getlength(raster_text)
            vector_width = book_vector_draw.advance_px(raster_text, size, face)
            assert raster_width <= measure < vector_width, (
                measure,
                raster_width,
                vector_width,
            )
            assert vector_width - raster_width < 1.0, vector_width - raster_width

    def test_the_clip_comparison_can_fail(self) -> None:
        """The control (ADR-0039/R1): one character, and it reds.

        The same comparison over a vector reading clipped one step further than
        the page really clips it — which is exactly the
        ``clipped[:-2] -> clipped[:-3]`` mutant that survived 596 cells in
        review cycle 1.
        """
        wanted = {"Puzzle 2 — Owl in a Pine"}
        raster = ["Puzzle 2 — Owl in a P…"]
        assert _unexplained_clip_divergences(
            ["Puzzle 2 — Owl in a …"], raster, wanted
        ) == []
        for moved in ("Puzzle 2 — Owl in …", "Puzzle 2 — Owl in a Pine"):
            assert _unexplained_clip_divergences([moved], raster, wanted) != [], moved
        # And a caption one medium omits entirely is not agreement either.
        assert _unexplained_clip_divergences([], raster, wanted) != []

    def test_the_minimum_trim_omits_its_captions_rather_than_shrinking_them(
        self,
    ) -> None:
        """The condition above, named: on the 10 cm trim there is no caption.

        Asserted on the full answer pages, whose drawing reaches the bottom
        margin on a square trim (measured: 0 px of slack). A packed page's
        tiles are shorter than the page and may still have room, which is why
        this reads the full pages rather than the whole section.
        """
        recorded = _recorded("min-trim")
        wanted = {
            answer_caption(number, title)
            for _, number, _, title in recorded.answers
        }
        assert wanted
        streams = [
            book_answer_vector.answer_page(
                recorded.generator.page_spec(page_number),
                recorded.generator.dpi,
                payload,
                number,
                page_number,
                title,
            )
            for payload, number, page_number, title in recorded.answers
        ]
        for text in pdf_vector.content_streams(_written(streams)):
            assert not (set(_strings(text)) & wanted), _strings(text)

    def test_the_two_media_omit_at_the_same_slack_for_every_integer(self) -> None:
        """The threshold agreement review cycle 1 found claimed but unasserted.

        F-297-08 item 4: the round reported that the vector writer's omission
        threshold and the raster page's "agree for every integer slack", and
        no assertion of it was committed anywhere — ``grep`` over the whole
        diff for ``72.9``, "threshold" and "every integer slack" returned
        nothing. Here it is, driven rather than reasoned.

        Each threshold is recomputed from its **own** medium's own face
        measurement — the vector's from the embedded face's ``/Ascent`` and
        ``/Descent``, the raster's from ``FreeTypeFont.getmetrics`` — and the
        two verdicts (print or omit) are compared at every integer slack from
        zero to past both. The agreement is not a coincidence of two numbers:
        a slack is a difference of two integer page coordinates, so what
        matters is that **no integer falls between the two thresholds**, and
        that is asserted as such. A face change that moved them apart across
        an integer reds here instead of silently changing which pages print a
        caption.
        """
        raster_gap = round(ANSWER_TILE_GAP_MM / 25.4 * 300)
        caption_pt = ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4
        ascent, descent = _band_font(type_px(caption_pt, 300)).getmetrics()
        raster_threshold = raster_gap + ascent + descent

        spec = book_answer_vector.answer_type(300)
        face = interior_face_metrics()
        vector_threshold = spec.gap_px + book_vector_draw.line_height_px(
            spec.caption_size_px, face
        )

        # The two really are different numbers, so the agreement below is a
        # measurement and not an identity.
        assert vector_threshold != raster_threshold
        low, high = sorted((float(vector_threshold), float(raster_threshold)))
        assert high - low < 1.0, (low, high)
        assert not [n for n in range(0, int(high) + 2) if low <= n < high], (low, high)

        cases = 0
        for slack in range(0, int(high) * 2 + 2):
            assert (slack >= vector_threshold) == (slack >= raster_threshold), (
                slack,
                vector_threshold,
                raster_threshold,
            )
            cases += 1
        assert cases >= 140, cases

    def test_the_floor_is_the_one_the_constant_states(self) -> None:
        """The figure is re-derived, not quoted: 10 pt is where it comes from."""
        assert ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4 == pytest.approx(_FLOOR_PT)


# --------------------------------------------------------------------------
# EC(ADR-0042/R3) — neither writer derives geometry
# --------------------------------------------------------------------------


def _page_coordinates(stream_text: str) -> Tuple[set, set]:
    """Every x and every y a stream's **paths** name, in points.

    Text is deliberately excluded: where a string sits for a given centre or
    edge is the sum of its glyphs' advances, which
    :mod:`nonogram.admin.book_vector_draw`'s own header names as the one
    arithmetic a writer does ("where a string sits is layout while how wide it
    sets is type"). This is the geometry half.
    """
    xs: set = set()
    ys: set = set()
    for x1, y1, x2, y2 in _LINE.findall(stream_text):
        xs.update((float(x1), float(x2)))
        ys.update((float(y1), float(y2)))
    for x, y, width, height, _ in _RECT.findall(stream_text):
        xs.update((float(x), round(float(x) + float(width), 3)))
        ys.update((float(y), round(float(y) + float(height), 3)))
    return xs, ys


def _stated_coordinates(slots, height: float, dpi: int) -> Tuple[set, set]:
    """Every x and y COMP-007 states for ``slots``, in the stream's own points.

    An **independent recomputation** rather than a second call into the
    writer: the positions, the ends and the frame's four edges are read off
    the layouts and converted here, by this file's own :func:`_pt`/:func:`_flip`.
    """
    xs: set = set()
    ys: set = set()
    for slot in slots:
        for line in slot.vertical_lines:
            xs.add(_pt(line.position, dpi))
            ys.update((_flip(line.start, height, dpi), _flip(line.end, height, dpi)))
        for line in slot.horizontal_lines:
            ys.add(_flip(line.position, height, dpi))
            xs.update((_pt(line.start, dpi), _pt(line.end, dpi)))
        frame = getattr(slot, "frame", None)
        if frame is not None:
            xs.update((_pt(frame.left, dpi), _pt(frame.right, dpi)))
            ys.update(
                (_flip(frame.top, height, dpi), _flip(frame.bottom, height, dpi))
            )
    return xs, ys


class TestPropertyTest_AnswerAndToc_WriterDerivesNoGeometry:
    """EC(ADR-0042/R3): every path coordinate is one COMP-007 already stated.

    **The class name carries the ``Test`` prefix deliberately.** ``pytest``
    matches ``python_classes`` by ``str.startswith``, not by glob, so a class
    named ``PropertyTest_…`` holds tests it silently never runs — no skip, no
    error. The card named this property with the prefix dropped; it is spelled
    **with** the prefix here so that it is actually collected, and the node ids
    are reported with the hand-back.

    The dead spelling is deliberately **not written out** anywhere in this
    file. Review cycle 1's F-297-05: the project's ref resolver is
    ``git grep -lw``, a text search, so a sentence quoting a name that has no
    definition makes that name read as alive — and the one thing keeping the
    card's own spelling resolvable was this very docstring. The card's ref is
    corrected to the collected spelling; stating the rule without restating
    the token is what stops the correction from being undone by prose.

    **No ``hypothesis``** (it is not in the dependency baseline): the corpus is
    built by hand with ``random.Random`` over the book profiles CON-018 stocks
    crossed with **every tile count per page** FR-042 defines — the full page,
    and the packed page at each of ``SOLVED_TILE_CAPACITIES`` — with the case
    count asserted inside the test.
    """

    #: Three of the trims CON-018 stocks, portrait and square, plus the
    #: minimum. Crossed with both parities, because parity moves the usable
    #: area sideways and a writer that derived a position would derive it
    #: differently on each side.
    PROFILES = ((10.0, 10.0), (13.97, 21.59), (21.59, 27.94))

    @staticmethod
    def _books():
        random = _Random(2971)
        for width, height in TestPropertyTest_AnswerAndToc_WriterDerivesNoGeometry.PROFILES:
            for page_number in (11, 12):
                extent = 10 + random.randrange(4)
                yield width, height, page_number, extent

    def test_every_path_coordinate_of_a_full_answer_page_is_stated(self) -> None:
        cases = 0
        for width, height, page_number, extent in self._books():
            generator = BookPDFGenerator(
                Book(
                    book_id=f"ec-{width}-{height}",
                    metadata=BookMetadata(
                        title="EC",
                        description="",
                        theme="generic",
                        target_audience="adults",
                        size="",
                        page_count=0,
                    ),
                    trim_width_cm=_cm(width * 10),
                    trim_height_cm=_cm(height * 10),
                    gutter_margin_cm=_cm(KDP_MIN_MARGIN_MM),
                    outside_margin_cm=_cm(KDP_MIN_MARGIN_MM),
                )
            )
            payload = generator._payload(
                _puzzle(extent, extent, number=1, depth=3, name="Zarquon")
            )
            layout = compute_layout(
                payload.row_clues, payload.column_clues, generator.page_spec(page_number)
            )
            stream = book_answer_vector.answer_page(
                generator.page_spec(page_number), generator.dpi, payload, 1, page_number, "Zarquon"
            )
            (text,) = pdf_vector.content_streams(_written([stream]))
            xs, ys = _page_coordinates(text)
            stated_x, stated_y = _stated_coordinates(
                [layout], layout.height, layout.dpi
            )
            assert xs <= stated_x, sorted(xs - stated_x)
            assert ys <= stated_y, sorted(ys - stated_y)
            assert xs and ys
            cases += 1
        assert cases >= 6, cases

    @pytest.mark.parametrize("capacity", [2, 4])
    def test_every_path_coordinate_of_a_packed_page_is_stated(
        self, capacity: int
    ) -> None:
        cases = 0
        for width, height, page_number, extent in self._books():
            generator = BookPDFGenerator(
                Book(
                    book_id=f"ec-packed-{width}-{height}",
                    metadata=BookMetadata(
                        title="EC",
                        description="",
                        theme="generic",
                        target_audience="adults",
                        size="",
                        page_count=0,
                    ),
                    trim_width_cm=_cm(width * 10),
                    trim_height_cm=_cm(height * 10),
                    gutter_margin_cm=_cm(KDP_MIN_MARGIN_MM),
                    outside_margin_cm=_cm(KDP_MIN_MARGIN_MM),
                )
            )
            rows = [
                _puzzle(extent, extent, number=index + 1, depth=3, name=f"P{index}")
                for index in range(capacity)
            ]
            payloads = [(row["id"], generator._payload(row)) for row in rows]
            packed = compute_packed_solved_layout(
                [(payload.row_clues, payload.column_clues) for _, payload in payloads],
                capacity,
                generator.page_spec(page_number),
            )
            if packed is None:
                continue
            plan = PackedAnswerPage(
                answers=tuple(
                    Answer(number=index + 1, width=extent, height=extent, level=Tier.EASY)
                    for index in range(capacity)
                )
            )
            stream = book_answer_vector.packed_answer_page(
                generator.page_spec(page_number), generator.dpi, plan, payloads, page_number, {}
            )
            (text,) = pdf_vector.content_streams(_written([stream]))
            xs, ys = _page_coordinates(text)
            frame = page_frame(generator.page_spec(page_number))
            stated_x, stated_y = _stated_coordinates(
                packed.slots, frame.height, packed.dpi
            )
            assert xs <= stated_x, sorted(xs - stated_x)
            assert ys <= stated_y, sorted(ys - stated_y)
            cases += 1
        assert cases >= 4, cases

    def test_the_coordinate_comparison_can_fail(self) -> None:
        """One stated coordinate removed, and the containment breaks.

        The control ADR-0039/R1 asks for: the assertion above is a subset
        test, which an empty left side would satisfy, so this shows the left
        side is really being compared.
        """
        generator = BookPDFGenerator(_book())
        payload = generator._payload(_puzzle(12, 12, number=1, name="Zarquon"))
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(11)
        )
        stream = book_answer_vector.answer_page(
            generator.page_spec(11), generator.dpi, payload, 1, 11, "Zarquon"
        )
        (text,) = pdf_vector.content_streams(_written([stream]))
        xs, _ = _page_coordinates(text)
        stated_x, _ = _stated_coordinates([layout], layout.height, layout.dpi)
        assert xs <= stated_x
        assert not xs <= (stated_x - {sorted(xs)[0]})

    def test_the_media_box_is_the_trim_and_nothing_measured(self) -> None:
        """The page's own extent comes from COMP-007, not from its content."""
        generator = BookPDFGenerator(_book())
        payload = generator._payload(_puzzle(12, 12, number=1, name="Zarquon"))
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(11)
        )
        stream = book_answer_vector.answer_page(
            generator.page_spec(11), generator.dpi, payload, 1, 11, "Zarquon"
        )
        assert stream.width_px == layout.width
        assert stream.height_px == layout.height
        frame = page_frame(generator.page_spec(11))
        toc = book_toc_vector.toc_page_stream(
            [TocEntry("Solutions", 11)], frame, generator.dpi, 7
        )
        assert (toc.width_px, toc.height_px) == (frame.width, frame.height)

    def test_the_toc_rows_sit_on_the_ladder_the_type_spec_states(self) -> None:
        """The TOC's own half: the baselines are a recomputed ladder.

        Recomputed here from the frame, the face and the three gap constants —
        not read back out of the writer — so a writer that invented a leading
        would red rather than agree with itself.
        """
        generator = BookPDFGenerator(_book())
        frame = page_frame(generator.page_spec(7))
        spec = book_toc_vector.toc_type(generator.dpi)
        face = interior_face_metrics()
        rows = [
            TocEntry("How to Solve Nonograms", 2),
            TocEntry("Easy", None, starts_group=True),
            TocEntry("Puzzles 1–2", 5),
            TocEntry("Solutions", 11, starts_group=True),
        ]
        stream = book_toc_vector.toc_page_stream(rows, frame, generator.dpi, 7)
        (text,) = pdf_vector.content_streams(_written([stream]))

        ascent = book_vector_draw.ascent_px(spec.entry_size_px, face)
        top = (
            frame.top
            + book_vector_draw.line_height_px(spec.title_size_px, face)
            + spec.title_gap_px
        )
        line = book_vector_draw.line_height_px(spec.entry_size_px, face) + spec.entry_gap_px
        expected = set()
        y = top
        for index, row in enumerate(rows):
            if row.starts_group and index > 0:
                y += spec.group_gap_px
            expected.add(_flip(y + ascent, frame.height, generator.dpi))
            y += line
        expected.add(
            _flip(
                frame.top + book_vector_draw.ascent_px(spec.title_size_px, face),
                frame.height,
                generator.dpi,
            )
        )
        expected.add(_flip(frame.bottom, frame.height, generator.dpi))

        baselines = {
            float(y)
            for y in _re.findall(
                r"Tf \S+ (" + pdf_vector.NUMBER + r") Td", text
            )
        }
        assert baselines == expected, sorted(baselines ^ expected)


# --------------------------------------------------------------------------
# The two constants this card's writers restate rather than import
# --------------------------------------------------------------------------


class TestAnswerPages_TheRestatedConstantsAreTheRasterPagesOwn:
    """The native-reimplementation convention's own control (CLAUDE.md).

    ``book_pdf_generator`` imports :mod:`nonogram.admin.book_answer_vector`,
    so the writer may not import *it* back — and the one tone and one ratio it
    needs from there are therefore restated. "Restated" is only safe while the
    two are held equal somewhere, and the import is legal here, which is the
    same arrangement ``solver/propagate.mask_runs`` and
    ``book_puzzle_vector.BAND_WIDTH_RATIO`` already have.
    """

    def test_the_join_tone_is_derived_from_the_raster_pages_own(self) -> None:
        assert book_answer_vector.SOLVED_JOIN_GREY == _SOLVED_GRID_GRAY[0] / 255

    @staticmethod
    def _layout(generator):
        payload = generator._payload(_puzzle(12, 12, number=1, name="Zarquon"))
        return compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(11)
        )

    def test_the_joins_are_set_in_that_tone_on_a_real_layout(self) -> None:
        """And it reaches the stream: a ``G`` operand no other mark carries.

        Drawn over a **dense** picture, and that is a measurement about this
        file's own corpus rather than a convenience: ``_grid`` above builds a
        gutter-depth pattern whose filled cells are isolated by construction
        (``x % 2 == 0 and y % 2 == 0``), so **no answer page of any book this
        file exports draws a single join**. The branch is live in production —
        a picture is a picture — and it would be dead in every test here that
        went through ``_puzzle``.
        """
        generator = BookPDFGenerator(_book())
        layout = self._layout(generator)
        stream = ContentStream(
            width_px=layout.width, height_px=layout.height, dpi=layout.dpi
        )
        book_answer_vector.draw_solved_grid(
            stream, layout, [[True] * 12 for _ in range(12)]
        )
        (text,) = pdf_vector.content_streams(_written([stream]))
        # The stream writes a number to three places (``book_vector._number``),
        # so the tones come back rounded; the comparison rounds the same way
        # rather than widening to an approximation.
        tones = {level for level, operator in pdf_vector.tones(text) if operator == "G"}
        assert round(book_answer_vector.SOLVED_JOIN_GREY, 3) in tones
        assert round(book_vector_draw.INK_GREY, 3) in tones

    def test_a_picture_with_no_two_adjacent_cells_draws_no_join(self) -> None:
        """The branch from the other side: no adjacency, no lighter tone.

        And no ``g`` either — an empty picture fills nothing, so neither state
        operator is emitted. That is what keeps a reader of the stream from
        mistaking a tone for a mark.
        """
        generator = BookPDFGenerator(_book())
        layout = self._layout(generator)
        stream = ContentStream(
            width_px=layout.width, height_px=layout.height, dpi=layout.dpi
        )
        book_answer_vector.draw_solved_grid(
            stream, layout, [[False] * 12 for _ in range(12)]
        )
        (text,) = pdf_vector.content_streams(_written([stream]))
        tones = pdf_vector.tones(text)
        assert round(book_answer_vector.SOLVED_JOIN_GREY, 3) not in {
            level for level, operator in tones if operator == "G"
        }
        assert [level for level, operator in tones if operator == "g"] == []


class TestAnswerPages_TheCaptionLandsWhereThePlacementPutsIt:
    """Where the caption's glyphs actually land, asked of poppler.

    The stream can say where the *pen* went; where the ink goes is the pen
    plus the face's advances, and only an engine that did not write the file
    can answer that. ``pdftotext -bbox`` reports the box poppler laid the
    glyphs out in, so the caption is checked where a **reader** finds it —
    which is also the one cell that fails if
    :func:`~nonogram.admin.book_vector_draw.set_right_middle`'s two anchor
    conversions are wrong, since every other reading here is of sizes and
    strings.
    """

    @needs_poppler_text
    def test_the_caption_is_right_aligned_on_the_slot_comp_007_reports(
        self, tmp_path
    ) -> None:
        from nonogram.export.layout import caption_slot

        generator = BookPDFGenerator(_book())
        payload = generator._payload(_puzzle(12, 12, number=1, name="Snowflake"))
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(11)
        )
        caption = answer_caption(1, "Snowflake")
        stream = book_answer_vector.answer_page(
            generator.page_spec(11), generator.dpi, payload, 1, 11, "Snowflake"
        )
        data = _written([stream])
        words = pdf_vector.word_boxes(data, out_dir=tmp_path)
        # The **title** word only, and that is a measurement rather than a
        # convenience: the band reads "Puzzle 1 · Easy" and the caption
        # "Puzzle 1 — Snowflake", so matching on the caption's whole word
        # list picks up the band's own "Puzzle" and "1" at the top of the page
        # and the vertical reading comes back 233 pt out (measured). The title
        # appears on the answer page and nowhere else on it (AC-2), which is
        # exactly what makes it the word to read, and it is also the caption's
        # **last** word, so its right edge is the caption's.
        picked = [word for word in words if word.text == "Snowflake"]
        assert len(picked) == 1, [word.text for word in words]

        spec = book_answer_vector.answer_type(generator.dpi)
        face = interior_face_metrics()
        width = book_vector_draw.advance_px(caption, spec.caption_size_px, face)
        box = caption_slot(layout, _math.ceil(width))
        assert box is not None
        scale = 72.0 / generator.dpi
        right = max(word.right for word in picked)
        assert abs(right - box.right * scale) <= 1.0, (right, box.right * scale)

        placement = layout.page
        assert placement is not None
        height = book_vector_draw.line_height_px(spec.caption_size_px, face)
        centre = (placement.drawing_bottom + spec.gap_px + height / 2) * scale
        middle = (
            min(word.top for word in picked) + max(word.bottom for word in picked)
        ) / 2
        assert abs(middle - centre) <= 2.0, (middle, centre)


class TestAnswerPages_TheGreyJoinsAreExactlyTheAdjacentBoundaries:
    """Which boundaries the lighter tone re-rules, against an independent walk.

    Added because a mutant survived: disabling the **vertical** adjacency test
    in :func:`~nonogram.admin.book_answer_vector.draw_solved_joins` left every
    cell of this file green, because the only other reading of the joins is
    "the tone appears on the page" and the horizontal loop still supplied it.
    A tone reading cannot see which boundaries were drawn; this does.

    The expected set is re-derived here from the grid and the tile's own
    rules — a second walk, not a second call into the writer.
    """

    @staticmethod
    def _drawn_and_expected(grid):
        generator = BookPDFGenerator(_book())
        payload = generator._payload(_puzzle(12, 12, number=1, name="Zarquon"))
        layout = compute_layout(
            payload.row_clues, payload.column_clues, generator.page_spec(11)
        )
        stream = ContentStream(
            width_px=layout.width, height_px=layout.height, dpi=layout.dpi
        )
        book_answer_vector.draw_solved_joins(stream, layout, grid)
        (text,) = pdf_vector.content_streams(_written([stream]))
        drawn = {
            (float(x1), float(y1), float(x2), float(y2))
            for x1, y1, x2, y2 in _LINE.findall(text)
        }
        xs = [line.position for line in layout.vertical_lines]
        ys = [line.position for line in layout.horizontal_lines]
        dpi, height = layout.dpi, layout.height
        expected = set()
        for column in range(1, len(xs) - 1):
            for row in range(len(ys) - 1):
                if grid[row][column - 1] and grid[row][column]:
                    expected.add(
                        (
                            _pt(xs[column], dpi),
                            _flip(ys[row], height, dpi),
                            _pt(xs[column], dpi),
                            _flip(ys[row + 1], height, dpi),
                        )
                    )
        for row in range(1, len(ys) - 1):
            for column in range(len(xs) - 1):
                if grid[row - 1][column] and grid[row][column]:
                    expected.add(
                        (
                            _pt(xs[column], dpi),
                            _flip(ys[row], height, dpi),
                            _pt(xs[column + 1], dpi),
                            _flip(ys[row], height, dpi),
                        )
                    )
        return drawn, expected

    def test_a_solid_picture_joins_every_internal_boundary(self) -> None:
        drawn, expected = self._drawn_and_expected([[True] * 12 for _ in range(12)])
        assert drawn == expected
        # 11 internal boundaries per axis x 12 cells along it, both axes.
        assert len(expected) == 2 * 11 * 12

    def test_a_picture_with_only_vertical_pairs_joins_only_those(self) -> None:
        """The arm a surviving mutant hid: the vertical loop on its own.

        Every row is a pair of filled cells side by side and nothing else, so
        there is exactly one vertical join per row and **no** horizontal one.
        """
        grid = [[column in (3, 4) for column in range(12)] for _ in range(1)]
        grid += [[False] * 12 for _ in range(11)]
        drawn, expected = self._drawn_and_expected(grid)
        assert drawn == expected
        assert len(expected) == 1, sorted(expected)

    def test_a_picture_with_only_horizontal_pairs_joins_only_those(self) -> None:
        grid = [[column == 3 for column in range(12)] for _ in range(2)]
        grid += [[False] * 12 for _ in range(10)]
        drawn, expected = self._drawn_and_expected(grid)
        assert drawn == expected
        assert len(expected) == 1, sorted(expected)

    def test_two_filled_cells_that_do_not_touch_join_nothing(self) -> None:
        grid = [[False] * 12 for _ in range(12)]
        grid[0][0] = True
        grid[2][2] = True
        drawn, expected = self._drawn_and_expected(grid)
        assert expected == set()
        assert drawn == set()
