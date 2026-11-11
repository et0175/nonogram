"""The book's answer key: how answers are planned onto pages and wired into
the interior, and what the vector answer pages print.

Every answer up to ``limits.MAX_SIZE`` packs (``PACKED_MAX_WIDTH/HEIGHT``,
owner decision 2026-11-09): a run of answers of one level is cut into pages
of four, then a page of two, then a page of one (CARD-202's walk,
:func:`~nonogram.admin.book_answer_key.plan_small_answer_pages`). The
CARD-297 block further down reads the answer and contents pages' content
streams.

**Puzzles here never pair** on the puzzle pages unless a test says so: the
default puzzle is an :data:`ALONE_SIDE` square with gutter-deep clues, the
shape ``tests/test_book_finalise_gutter.py``'s ``alone`` uses, so the puzzle
section's length is arithmetic and :func:`first_answer_page` can predict
where the answer section starts.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import pytest
from PIL import Image

import nonogram.admin.book_pdf_generator as book_pdf_generator
from nonogram.admin.book_dividers import SOLUTIONS_SLOT
from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _as_planned,
    _degrade_infeasible_packed_pages,
    answer_section_spec,
    page_frame,
    page_is_right_hand,
)
from nonogram.admin.book_answer_key import (
    CAPTION_SEPARATOR,
    Answer,
    PackedAnswerPage,
    answer_caption,
    plan_small_answer_pages,
)
from nonogram.admin.book_pdf_generator import (
    ANSWER_TEXT_FONT_MM,
    BACKGROUND,
    POINTS_PER_INCH,
)
from nonogram.difficulty import Tier
from nonogram.limits import MAX_SIZE
from nonogram.export.layout import compute_packed_solved_layout

from tests.helpers.book_corpus import GUIDE_INTERIOR_PAGES
from tests.helpers.page_ink import drawing_of
from tests.helpers.pdf_pages import interior_images

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out rather than imported.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4


#: The side of this file's default puzzle: large enough that two never share
#: a puzzle page (see the module docstring).
ALONE_SIDE = 22


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
    columns: int = ALONE_SIDE,
    rows: int = ALONE_SIDE,
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


def _interior_images(puzzles: Sequence[dict], book: Optional[Book] = None) -> List[Image.Image]:
    """:func:`_interior`, every page as device pixels (CARD-354, ADR-0042/R6).

    The sites that *measure* a page -- a rule's side, the ink in a gutter --
    read pixels, and a page arrives in whichever medium its kind declares. The
    seam is :func:`tests.helpers.pdf_pages.interior_images`: a bitmap page is
    returned unchanged (so on a tree whose kinds are still raster this is
    exactly :func:`_interior`) and an operator page is rasterised by poppler at
    its own DPI, or refused loudly when poppler is absent.
    """
    return interior_images(_interior(puzzles, book))


def _page_reading(page) -> Tuple[object, ...]:
    """What makes two pages of the SAME medium the same page, byte for byte.

    A bitmap page is its pixels. An operator page is its media box and the
    content stream it records -- the bytes ``/Contents`` holds -- because
    ``ContentStream`` has no ``tobytes`` (CARD-354 M7d: that is the whole of
    the twelve ``AttributeError`` reds). The first element names the medium, so
    two pages of different media can never read as equal *or* be compared as if
    they could: a cross-medium ``==`` would be False and a cross-medium ``!=``
    vacuously True, and neither says anything about the page.
    """
    if isinstance(page, Image.Image):
        return ("raster", page.size, page.tobytes())
    if isinstance(page, ContentStream):
        return ("vector", page.media_box, page.render())
    raise TypeError(f"a book page is a bitmap or a content stream, not {type(page).__name__}")


def _packed_twin(gen: BookPDFGenerator, plan, payloads, page_number: int, titles):
    """The packed answer page, drawn directly by the vector writer.

    Called as the module, not through ``gen.pages``, so the expectation does
    not share the seam the interior's wiring is checked through.
    """
    return book_answer_vector.packed_answer_page(
        gen.page_spec(page_number), gen.dpi, plan, payloads, page_number, titles
    )


class TestBookSolvedAnswerKey_AnEmptyBookHasNoAnswerSection:
    def test_a_book_with_no_puzzles_has_no_answer_section_at_all(self) -> None:
        pages = _interior([])
        assert len(pages) == 1 + 2, (
            "the title page (CARD-206) and the 2-page guide (CARD-201) "
            "alone"
        )


class TestBookSolvedAnswerKey_AnUnnamedPuzzleIsNamedByNumberAlone:
    def test_a_puzzle_with_no_name_at_all_is_still_captioned_by_number_alone(
        self,
    ) -> None:
        """The answer page names it "1" and sets no dangling separator or "None"."""
        puzzle = _puzzle(12, 12, number=1, tier="easy")
        puzzle["puzzle_name"] = None
        book = _book()
        pages = _interior([puzzle], book)
        start = first_answer_page(book, [puzzle])
        page = pages[start - 1]
        assert isinstance(page, ContentStream), type(page)
        (text,) = pdf_vector.content_streams(_written([page]))
        shown = _strings(text)
        assert "1" in shown, shown
        assert not [s for s in shown if "None" in s or CAPTION_SEPARATOR.strip() in s], shown
        assert answer_caption(1, None) == "Puzzle 1"


class TestBookSolvedAnswerKey_ThePlanGuardStillHolds:
    def test_as_planned_itself_still_raises_on_an_undercount(self) -> None:
        """The guard's own unit shape, pinned directly (CARD-145)."""

        def two_pages():
            yield Image.new("RGB", (10, 10), "white")
            yield Image.new("RGB", (10, 10), "white")

        with pytest.raises(RuntimeError, match="interior has 2 pages"):
            list(_as_planned(two_pages(), 3))


# --------------------------------------------------------------------------
# AC-4 — no per-level heading page inside the answer section
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_LevelVisibleViaPerPageBandNoSeparateHeading:
    """2 easy then 1 medium: one answer page per level run, no heading page."""

    @staticmethod
    def _book_and_pages() -> Tuple[Book, List[dict], list]:
        book = _book()
        puzzles = _book_of(*[(ALONE_SIDE, ALONE_SIDE)] * 3, depth=6, tiers=["easy", "easy", "medium"])
        return book, puzzles, _interior(puzzles, book)

    def test_the_answer_section_opens_with_exactly_one_divider_the_solutions_one(
        self,
    ) -> None:
        """No per-level heading page inside the answer section (CARD-198)."""
        book, puzzles, pages = self._book_and_pages()
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)

        # The page immediately before the answer section is the SOLUTIONS
        # opener, reached through the same ``divider_page`` call the walk makes.
        assert _page_reading(pages[start - 2]) == _page_reading(
            gen.divider_page(
                SOLUTIONS_SLOT, start - 1, "SOLUTIONS", puzzle_count=len(puzzles)
            )
        )
        # Every page after it is a vector answer page; a divider is a bitmap
        # (its kind declares raster), so none hides inside the answer run.
        # Up to the closing thank-you page (owner, 2026-11-10), the last page.
        answer_run = pages[start - 1 : -1]
        assert len(answer_run) == 2, "the easy pair, then the medium one"
        assert all(isinstance(page, ContentStream) for page in answer_run)
        assert (
            book_pdf_generator.page_medium(book_pdf_generator.PageKind.DIVIDER)
            is book_pdf_generator.PageMedium.RASTER
        )

    def test_the_total_page_count_has_no_room_for_a_heading_page(self) -> None:
        """1 title (CARD-206) + 2 guide (CARD-201) + 1 TOC (CARD-200) +
        2 dividers + 3 puzzles + SOLUTIONS + 2 answer pages + the closing
        thank-you page (owner, 2026-11-10) = 13.

        A per-level heading page inside the answer section would make it 14
        or 15.
        """
        book, puzzles, pages = self._book_and_pages()
        assert len(pages) == 1 + 2 + 1 + 2 + 3 + 1 + 2 + 1 == 13


# --------------------------------------------------------------------------
# AC-5 — a malformed answer still aborts, before any page is drawn
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_AMemberThatCannotBeMeasuredIsStillNamed:
    """AC-5 — the "could not be laid out" abort contract survives CARD-198."""

    def test_a_ragged_grid_aborts_naming_the_puzzle_with_a_value_error_cause(
        self,
    ) -> None:
        puzzle = _puzzle(ALONE_SIDE, ALONE_SIDE, number=4)
        puzzle["grid"] = [row[:] for row in puzzle["grid"]]
        puzzle["grid"][2] = puzzle["grid"][2][:-1]

        with pytest.raises(RuntimeError) as raised:
            BookPDFGenerator(_book()).interior_stream([puzzle])

        assert "'p4'" in str(raised.value)
        assert "could not be laid out" in str(raised.value)
        assert isinstance(raised.value.__cause__, ValueError)

    @pytest.mark.parametrize("grid", [[], [[]]])
    def test_an_empty_grid_aborts_the_same_way(self, grid: list) -> None:
        puzzle = _puzzle(ALONE_SIDE, ALONE_SIDE, number=9)
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
        good = _puzzle(ALONE_SIDE, ALONE_SIDE, number=1)
        bad = _puzzle(ALONE_SIDE, ALONE_SIDE, number=2)
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

    def test_every_interior_pages_measured_side_matches_its_declared_parity(
        self,
    ) -> None:
        """Puzzle and answer pages via :func:`drawing_of`; page 1 off its own ink.

        The title page (interior page 1, CARD-206; blank until the owner made
        it the title and copyright page on 2026-11-09), the guide's two
        pages and the SOLUTIONS/level divider pages carry no
        ruled grid for :func:`drawing_of` to measure, so each divider is
        skipped (``drawing_of`` itself raises on it — a page with no grid at
        all, never a silently wrong measurement), the title page carries only
        centred text and cannot be measured either, and the guide's own two
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
        pages = _interior_images(puzzles, book)
        middle = pages[0].width / 2
        checked = 0
        decided = BookPDFGenerator(book).section_plan(list(puzzles))

        for number, page in enumerate(pages, start=1):
            right_hand = page_is_right_hand(number)
            if number == 1:
                # CARD-206's title page. Blank until the owner replaced it
                # with the title and copyright page (2026-11-09): it now
                # carries centred text and no grid or folio, so it still has
                # no side to measure. Asserted to carry the page's text, and
                # not counted as a parity measurement.
                ink = np.asarray(page.convert("L")) < 128
                assert ink.any(), "interior page 1 is the title and copyright page"
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
            if 0 < number - max(GUIDE_INTERIOR_PAGES) <= decided.toc_page_count:
                # The table of contents (CARD-200): no grid. Skipped by
                # position since the approved restyle ruled a line under its
                # title, which ``drawing_of`` would otherwise read as a frame.
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
        # table of contents page(s) (CARD-200) and the title page
        # (CARD-206), which has no grid to measure a side from.
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
# CARD-202 — answers pack 4, then 2, then 1 to a page, one level per page
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
    """AC-1 — a single-tier book of qualifying answers packs 4 to a page.

    Since 2026-11-09 (CARD-232 AC-4) a level's leftover page keeps the 2x2
    positions: it is laid out at capacity 4 whatever its count.
    """

    def test_six_qualifying_easy_answers_pack_as_four_then_two(self) -> None:
        answers = _answers_for(
            _small_book_of(*[(10, 10, "easy")] * 6, depth=3)
        )
        plan = plan_small_answer_pages(list(answers))

        assert [p.numbers for p in plan] == [(1, 2, 3, 4), (5, 6)]
        assert [p.capacity for p in plan] == [4, 4]
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
            expected = _packed_twin(gen, packed_page, payloads, start + offset, titles)
            assert _page_reading(pages[start - 1 + offset]) == _page_reading(expected), (
                f"answer page at offset {offset} does not match the direct call"
            )

    def test_a_custom_book_title_reaches_a_packed_page(self) -> None:
        """FR-041 on a packed page: ``books.puzzle_titles`` beats ``puzzle_name``.

        CARD-354 found this unasserted: planting an empty ``titles`` into the
        walk's packed-page call left the whole module green, because every
        packed-page test above builds a book with no custom titles and so
        hands the page ``{}`` either way. The control is the same page drawn
        with ``{}``, in the same medium, and it must differ.
        """
        puzzles = _small_book_of((10, 10, "easy"), (10, 10, "easy"), depth=3)
        book = _book({"p1": "Winter Star"})
        pages = _interior(puzzles, book)
        start = first_answer_page(book, puzzles)
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        (packed,) = plan_small_answer_pages(list(_answers_for(puzzles)))
        assert gen.custom_titles() == {"p1": "Winter Star"}

        expected = _packed_twin(gen, packed, payloads, start, gen.custom_titles())
        assert _page_reading(pages[start - 1]) == _page_reading(expected)

        uncustomised = _packed_twin(gen, packed, payloads, start, {})
        assert _page_reading(pages[start - 1])[0] == _page_reading(uncustomised)[0]
        assert _page_reading(pages[start - 1]) != _page_reading(uncustomised)

    def test_a_run_of_three_leftover_shares_one_page_in_the_2x2_positions(
        self,
    ) -> None:
        """A leftover of three is one page, laid out as a 2x2 with one spot empty."""
        answers = _answers_for(_small_book_of(*[(10, 10, "easy")] * 3, depth=3))
        plan = plan_small_answer_pages(list(answers))

        assert [p.numbers for p in plan] == [(1, 2, 3)]
        assert [p.capacity for p in plan] == [4]


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
        assert levels == [Tier.EASY, Tier.MEDIUM]
        # Never padded to 4 with a Medium answer: the 3 Easy answers close
        # their own page, in the 2x2 positions.
        assert [entry.numbers for entry in plan] == [(1, 2, 3), (4, 5)]
        assert [entry.capacity for entry in plan] == [4, 4]

    def test_no_packed_page_ever_holds_two_levels(self) -> None:
        answers = _answers_for(_small_book_of(*self.PUZZLES, depth=3))
        for entry in plan_small_answer_pages(list(answers)):
            assert isinstance(entry, PackedAnswerPage)
            assert len({a.level for a in entry.answers}) == 1


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
        pages = _interior_images(puzzles, book)
        start = first_answer_page(book, puzzles)

        page = pages[start - 1]
        arr = np.asarray(page.convert("L"))
        # Clue digits sit left of and above the grid, inside each slot's own
        # drawing — a page with no clue gutter ink at all would mean the
        # packed slot reverted to the old clueless tile (AC-4's own point).
        assert (arr < 128).any(), "the packed page carries no ink at all"


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

        # The closing thank-you page (owner, 2026-11-10) follows the key.
        answer_pages = pages[start - 1 : -1]
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


# --------------------------------------------------------------------------
# Review F-1 (CARD-202, fix cycle 1) — a packed page COMP-007 cannot lay out
# degrades instead of silently shipping overlapping ink.
# --------------------------------------------------------------------------


class TestBookSolvedAnswerKey_InfeasiblePackedPagesDegradeGracefully:
    """Review F-1's own reproduction, end to end: a real book, a real export.

    Four answers 15 wide (heights 10/15/18/20)
    with realistic 5-deep clue gutters, on a real KDP-minimum 10cm x 10cm book
    (:func:`_kdp_min_book`) at KDP's own minimum side margin. On this trim the
    naive, extent-only walk (:func:`plan_small_answer_pages`, which never
    measures a tile) packs all four onto one 4-up page — exactly the page the
    reviewer reproduced the bug on, which the fixed
    :func:`~nonogram.export.layout.compute_packed_solved_layout` now declines
    (``tests/test_layout_packed_solved.py`` pins that half directly). This
    class proves the walk that wraps it recovers gracefully: the book still
    exports, split across a working 2-up page and two full pages instead,
    and no two slots' drawing extents overlap anywhere in the result.

    (Two 2-up pages until 2026-11-11, when every answer page began keeping
    the puzzle pages' footer strip free for its centred page number: on this
    10 cm trim the 15 x 18 and 15 x 20 pair no longer fits one page.)
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

    def test_the_walk_degrades_to_a_two_up_page_and_two_full_pages(self) -> None:
        book = _kdp_min_book()
        puzzles = self._puzzles()
        gen = BookPDFGenerator(book)
        payloads = [(p["id"], gen._payload(p)) for p in puzzles]
        start = first_answer_page(book, puzzles)
        naive_plan = plan_small_answer_pages(list(_answers_for(puzzles)))

        degraded = _degrade_infeasible_packed_pages(
            naive_plan, payloads, answer_section_spec(gen.page_spec(start))
        )

        first, *rest = degraded
        assert isinstance(first, PackedAnswerPage)
        assert (first.numbers, first.capacity) == ((1, 2), 2)
        assert [(type(entry), entry.number) for entry in rest] == [
            (Answer, 3),
            (Answer, 4),
        ]

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
            naive_plan, payloads, answer_section_spec(gen.page_spec(start))
        )

        checked_any = False
        for offset, packed in enumerate(degraded):
            if not isinstance(packed, PackedAnswerPage):
                continue  # a full answer page: one slot, nothing to overlap
            members = [payloads[number - 1] for number in packed.numbers]
            layout = compute_packed_solved_layout(
                [(payload.row_clues, payload.column_clues) for _, payload in members],
                packed.capacity,
                answer_section_spec(gen.page_spec(start + offset)),
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
            naive_plan, payloads, answer_section_spec(gen.page_spec(start))
        )

        pages = _interior(puzzles, book)

        # + 1: the closing thank-you page (owner, 2026-11-10).
        assert len(pages) == start - 1 + len(degraded) + 1
        assert len(degraded) == 3, "a 2-up page and two full pages, not one 4-up and not four singles"

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
            naive_plan, payloads, answer_section_spec(gen.page_spec(start))
        )

        for offset, packed_page in enumerate(degraded):
            if not isinstance(packed_page, PackedAnswerPage):
                continue  # full answer pages are pinned by their own tests
            expected = _packed_twin(gen, packed_page, payloads, start + offset, titles)
            assert _page_reading(pages[start - 1 + offset]) == _page_reading(expected), (
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
# written PDF, or against poppler — an engine that did not write it.**
#
# **The pages come from one walk of the real interior** (:func:`recorded`):
# the walk is spied on once — what each TOC page and packed answer page was
# asked to draw — and exactly that is handed to the vector writers again. No
# page plan is re-derived here.
# ==========================================================================

import ast as _ast
import dataclasses as _dataclasses
import math as _math
import re as _re
import sys as _sys
from pathlib import Path as _Path
from random import Random as _Random

from PIL import Image as _Image, ImageDraw as _ImageDraw

from nonogram.admin import book_answer_vector, book_toc_vector, book_vector_draw
from nonogram.admin.book_pdf_generator import (
    DividerPagePlan,
    PuzzlePagePlan,
    TocEntry,
    _draw_difficulty_dots,
    answer_title,
    structural_toc_entries,
)
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_plan import TIERS
from nonogram.admin.book_vector import ContentStream, interior_face_metrics, write_vector_pdf
from nonogram.difficulty import Tier as _Tier
from nonogram.admin.book_pdf_generator import RUNNING_HEAD_MM, answer_section_spec
from nonogram.export.layout import (
    INTERIOR_FOOTER_LINE_PT,
    PageParity,
    compute_answer_page_layout,
    compute_layout,
    difficulty_dots,
    header_band,
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
    """What one walk of a book's real interior asked each page kind to draw.

    The TOC and answer writers in ``generator.pages`` are spied on, and every
    ``ImageDraw.text`` the walk makes (the pages still drawn as bitmaps: the
    dividers and the Solutions opener) is recorded with the ``nonogram``
    functions above it.
    """

    def __init__(self, book: Book, puzzles: Sequence[dict]) -> None:
        self.generator = BookPDFGenerator(book)
        self.toc: List[Tuple[List[TocEntry], int]] = []
        self.answers: List[Tuple[object, int, int, Optional[str]]] = []
        self.packed: List[Tuple[PackedAnswerPage, list, int, dict]] = []
        #: Every ``ImageDraw.text`` the walk made, as ``(page, text, names)``.
        self.text: List[Tuple[int, str, frozenset]] = []
        #: ``(page, string)`` for every string a page the walk yielded as a
        #: content stream sets.
        self.streamed: List[Tuple[int, str]] = []
        #: Interior page numbers the walk yielded as operators.
        self.stream_pages: List[int] = []
        self._walk(list(puzzles))

    def _text_spy(self, current: dict):
        recorded = self
        original_text = _ImageDraw.ImageDraw.text

        def spy_text(self, xy, text, fill=None, font=None, *args, **kwargs):
            names = []
            frame = _sys._getframe(1)
            while frame is not None:
                if frame.f_globals.get("__name__", "").startswith("nonogram."):
                    names.append(frame.f_code.co_name)
                frame = frame.f_back
            recorded.text.append((current["page"], str(text), frozenset(names)))
            return original_text(self, xy, text, fill, font, *args, **kwargs)

        return original_text, spy_text

    def _walk(self, puzzles: List[dict]) -> None:
        self_recorded = self
        generator = self.generator
        current = {"page": 0}
        original_text, spy_text = self._text_spy(current)
        writers = generator.pages

        def spy_vector_toc(writer):
            def spy(rows, frame, dpi, page_number, *args, **kwargs):
                self_recorded.toc.append((list(rows), page_number))
                return writer(rows, frame, dpi, page_number, *args, **kwargs)
            return spy

        def spy_vector_answer(writer):
            def spy(spec, dpi, payload, number, page_number, title=None, *args, **kwargs):
                self_recorded.answers.append((payload, number, page_number, title))
                return writer(spec, dpi, payload, number, page_number, title, *args, **kwargs)
            return spy

        def spy_vector_packed(writer):
            def spy(spec, dpi, plan, payloads, page_number, titles, *args, **kwargs):
                self_recorded.packed.append(
                    (plan, list(payloads), page_number, dict(titles))
                )
                return writer(spec, dpi, plan, payloads, page_number, titles, *args, **kwargs)
            return spy

        _ImageDraw.ImageDraw.text = spy_text
        generator.pages = _dataclasses.replace(
            writers,
            toc=spy_vector_toc(writers.toc),
            answer=spy_vector_answer(writers.answer),
            packed_answer=spy_vector_packed(writers.packed_answer),
        )
        try:
            stream = generator.interior_stream(puzzles)
            pages = iter(stream.pages)
            drawn = 0
            streams: List[ContentStream] = []
            while True:
                current["page"] = drawn + 1
                try:
                    page = next(pages)
                except StopIteration:
                    break
                drawn += 1
                if isinstance(page, ContentStream):
                    streams.append(page)
                    self.stream_pages.append(drawn)
                del page
            self.page_count = drawn
            assert drawn == stream.page_count
        finally:
            _ImageDraw.ImageDraw.text = original_text
            generator.pages = writers
        for number, text in zip(
            self.stream_pages, pdf_vector.content_streams(_written(streams))
        ):
            self.streamed.extend((number, string) for string in _strings(text))

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
    """Four puzzles: two Easy that share a page, then a Medium and a Hard."""
    return [
        _puzzle(12, 12, number=1, depth=3, name=_TITLES[0], tier="easy"),
        _puzzle(12, 12, number=2, depth=3, name=_TITLES[1], tier="easy"),
        _puzzle(MAX_SIZE, MAX_SIZE, number=3, depth=3, name=_TITLES[2], tier="medium"),
        _puzzle(MAX_SIZE, MAX_SIZE, number=4, depth=3, name=_TITLES[3], tier="hard"),
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

    The positive control is :meth:`test_a_bitmap_divider_page_does_carry_one`:
    a page the book still ships as a bitmap really does reference one, so this
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

    def test_a_bitmap_divider_page_does_carry_one(self, recorded) -> None:
        """The control: the same reading sees the image on a raster divider."""
        generator = recorded.generator
        page = generator.create_divider_page(7, "Easy")
        assert isinstance(page, Image.Image), type(page)
        data = generator._write_pdf(
            [page], 1, mode=generator.interior_bitmap_mode, kinds=(book_pdf_generator.PageKind.DIVIDER,)
        ).getvalue()
        assert any("XObject" in keys for keys in pdf_vector.page_resource_keys(data))

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

        **CARD-314 took it to 15, and the two it added paint nothing.**
        ``BMC``/``EMC`` bracket the clue digits an answer tile sets, so the
        stream records the provenance CON-020's exemption is keyed on (PDF 1.7
        §14.6, and
        ``tests/test_book_interior_type_floor.py::TestInteriorType_TheClueDigitMarkIsTheWritersOwn``).
        They come from the **answer** pages only: the TOC draws no clue digits
        and still emits its 6, which is why the asymmetry is restated below
        rather than left inside the union — a bracket appearing on a TOC page
        would be the over-applied mark CARD-314's AC-4 exists to catch, and
        this is the only reading in the tree that would see it on *these* two
        kinds together.

        **The approved solutions mockup took it to 21.** Each solution's
        header now sets its number emboldened (``q``/``Q`` around a ``2 Tr``
        string, :meth:`ContentStream.text`'s ``embolden_pt``) and draws the
        tier's dots flush right through ``draw_tier_dots`` -- the one
        round-mark site -- whose quadrants are ``c``, closed by ``h`` and
        painted by ``B``. So ``B``/``c``/``h`` are no longer surplus: they are
        CARD-233's signal arriving, on the **answer** pages only, and the TOC
        still draws no round shape (asserted per kind below).

        **The approved contents restyle puts them on the TOC too.** Each level
        row now carries its tier's dots after the level's name, drawn by the
        same ``draw_tier_dots``, so ``B``/``c``/``h`` are on both kinds; the
        per-kind reading below now asserts the TOC reaches them only through
        that one site.
        """
        emitted = {
            "g", "G", "w", "m", "l", "S", "re", "f",
            "BT", "ET", "Tf", "Td", "Tj",
            "BMC", "EMC",
            "q", "Q", "Tr",
            "B", "c", "h",
        }
        seen: set = set()
        for stream_text in pdf_vector.content_streams(
            _written(recorded.toc_streams() + recorded.answer_streams())
        ):
            tokens = set(pdf_vector.operator_tokens(stream_text))
            assert tokens <= emitted, sorted(tokens - emitted)
            seen |= tokens
        assert seen == emitted, (sorted(seen - emitted), sorted(emitted - seen))
        # The three members F-297-04 found surplus are a round mark's. Since
        # the approved mockups they are the tier dots of a solution's header
        # and of a contents level row, and both writers reach them only
        # through ``draw_tier_dots``. Stated here as well as in the limit cell
        # so the two cannot drift apart again.
        round_ops = {"B", "c", "h"}
        # The contents' first page carries the level rows; on a small trim a
        # second page may hold only the Solutions rows, which have no dots.
        first_toc = pdf_vector.content_streams(_written(recorded.toc_streams()))[0]
        tokens = set(pdf_vector.operator_tokens(first_toc))
        assert round_ops <= tokens, sorted(round_ops - tokens)
        assert "round_mark" not in _source_of(book_toc_vector)
        assert "draw_tier_dots" in _source_of(book_toc_vector)
        # CARD-314: the mark is on the answer pages and NOT on the TOC, which
        # draws no clue digit. Read per page kind, so an over-applied bracket
        # on a TOC page reds here rather than disappearing into the union.
        for rows, marked in (
            (recorded.toc_streams(), False),
            (recorded.answer_streams(), True),
        ):
            for stream_text in pdf_vector.content_streams(_written(rows)):
                tally = pdf_vector.operator_tally(stream_text)
                assert (tally["BMC"] > 0) is marked, (marked, tally["BMC"])
                assert tally["BMC"] == tally["EMC"], (tally["BMC"], tally["EMC"])


# --------------------------------------------------------------------------
# AC-2 / EC(ADR-0037/R1) — the answer key is the only place the title prints
# --------------------------------------------------------------------------


class TestAnswerKey_IsTheOnlyPlaceTheTitleIsPrinted:
    """AC-2 (FR-033/AC-194, ADR-0037/R1): the picture's name prints on its
    answer page and nowhere else in the interior.

    The second half is asserted over the **whole interior**: every string the
    walk's content-stream pages set, and every ``ImageDraw.text`` call the
    walk's bitmap pages (dividers, the Solutions opener) make. The corpus arm
    (:meth:`test_the_title_prints_only_on_answer_pages_across_a_corpus`) is the
    EC, with its minimum case count asserted inside it.
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
        """The first half, on both profiles: the solution headers name all four."""
        printed = [
            " ".join(_strings(text))
            for text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
        ]
        assert printed
        vector = {title for title in _TITLES for page in printed if title in page}
        assert vector == set(_TITLES), sorted(vector)

    def test_a_clipped_title_is_counted_as_printed_in_both_media(
        self, recorded
    ) -> None:
        """F-297-03: a clip is not an omission.

        The cell above reads whole titles; this one admits a clipped name
        (a stem of it plus "…"), and every title must be named, whole or
        clipped, by some solution header.
        """
        names = set(self._titles_of(recorded))
        vector = {
            _caption_behind(reading, names)
            for stream_text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
            for _, text in _shows(stream_text)
            if (reading := _caption_reading(text, names)) is not None
        }
        assert vector == names, (sorted(vector), sorted(names))

    @staticmethod
    def _captions_for(recorded: _Recorded) -> List[str]:
        """The whole caption lines this book's answer key would print."""
        return TestAnswerPages_CaptionHoldsTheFloorInTheStream._captions(recorded)

    def test_no_bitmap_page_of_the_interior_prints_a_title(self, recorded) -> None:
        """The second half, over the pages the walk still draws as bitmaps."""
        assert recorded.text, "the walk drew no bitmap text, so this reading is vacuous"
        offenders = [
            (page, text, sorted(names))
            for page, text, names in recorded.text
            if any(title in text for title in _TITLES)
        ]
        assert offenders == []

    def test_no_stream_page_outside_the_answer_section_prints_a_title(
        self, recorded, profile
    ) -> None:
        """The second half, over every page the walk yielded as operators.

        A stream has no call chain, so the answer section is told by its page
        numbers, which the walk recorded when it asked the writers for them.
        """
        answer_pages = {n for _, _, n, _ in recorded.answers} | {
            n for _, _, n, _ in recorded.packed
        }
        offenders = [
            (page, text)
            for page, text in recorded.streamed
            if any(title in text for title in _TITLES) and page not in answer_pages
        ]
        assert offenders == []
        # Non-vacuous: operator pages were read, and on Book 1 the answer
        # pages really do print the titles the filter above is looking for.
        assert recorded.streamed, "operator pages were walked and none set a string"
        if profile == "book1":
            titled = {
                page
                for page, text in recorded.streamed
                if any(title in text for title in _TITLES)
            }
            assert titled and titled <= answer_pages, (
                sorted(titled),
                sorted(answer_pages),
            )

    def test_the_interior_really_was_walked_end_to_end(self, recorded) -> None:
        """Guard the instrument: a walk that drew nothing would pass above."""
        assert recorded.page_count >= 10
        lettered = {page for page, _, _ in recorded.text} | {
            page for page, _ in recorded.streamed
        }
        assert len(lettered) >= 6, sorted(lettered)
        assert any(
            any(title in text for title in _TITLES) for _, text in recorded.streamed
        ), "no page of the interior printed a title at all, so the sweep is vacuous"

    def test_no_toc_row_prints_a_title_in_the_stream_either(self, recorded) -> None:
        streams = recorded.toc_streams()
        # Non-vacuity (CARD-354): this loop used to run over whatever the
        # record held, so a record that had stopped capturing the TOC read
        # green over zero pages.
        assert streams, "the book printed no table of contents to read"
        for text in pdf_vector.content_streams(_written(streams)):
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
        # Four of the trims CON-018 stocks: three portrait KDP sizes and the
        # 10 x 10 cm square minimum.
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
                    book_answer_vector.packed_answer_page(
                        generator.page_spec(11 + index),
                        generator.dpi,
                        PackedAnswerPage(
                            (Answer(number=index + 1, width=12, height=12, level=Tier.EASY),),
                            capacity=2,
                        ),
                        [(row["id"], row_payload) for row, row_payload in zip(puzzles, payloads)],
                        11 + index,
                        {},
                    )
                    for index in range(len(payloads))
                ]
                puzzle_streams = list(generator.vector_puzzle_pages(payloads))
                for index, text in enumerate(
                    pdf_vector.content_streams(_written(answers))
                ):
                    shown = " ".join(_strings(text))
                    # The page prints its own title, whole or clipped, and
                    # never a different puzzle's. The name sits in the
                    # solution header, which every trim has room for, so the
                    # omission arm is asserted dead below.
                    if picked[index] in shown:
                        printed += 1
                    elif any(
                        len(piece) > 1
                        and piece.endswith("…")
                        and picked[index].startswith(piece.split(" — ")[-1][:-1])
                        for piece in _strings(text)
                    ):
                        # CLIPPED: neither printed whole nor omitted (F-297-03).
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
        # Measured on this corpus, each answer packed onto its own tile: 23 of
        # the 24 headers name the picture whole and one clips it (a long name
        # on the 10 cm trim's half-width tile); none omits it.
        assert printed >= 23, printed
        assert omitted == 0, omitted
        assert clipped <= 1, clipped
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
    # CARD-314's marked-content brackets. Driven like every other member, so
    # "they paint nothing" is a measurement here rather than a claim: the probe
    # records ``/ClueDigit BMC`` and ``EMC``, neither of which is in
    # :data:`_PATH_OPERATORS`, which is how they land in
    # :data:`_NOT_A_DOOR_BECAUSE` instead of among the doors.
    "begin_marked": ("ClueDigit",),
    "end_marked": (),
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
    "begin_marked": (
        "opens a marked-content sequence (BMC) and constructs no path: PDF 1.7 "
        "§14.6 makes it a statement ABOUT the operators inside it, which is "
        "why CARD-314 carries CON-020's clue-digit provenance in one"
    ),
    "end_marked": (
        "closes a marked-content sequence (EMC) and constructs no path, for "
        "the reason begin_marked gives"
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

#: The answer writer's page furniture: functions that rule exactly ONE
#: horizontal line and hold no grid, each with the reason it is not a grid
#: walk. Added with the approved solutions mockup, which gave every solution a
#: header with a grey hairline under it and every answer page a running head
#: over a rule. Neither is a function of the solution (so the derived ``grid``
#: exemption rightly does not admit them) and neither is a grid rule; a single
#: horizontal line cannot walk a grid, and
#: :func:`_furniture_rule_violations` holds each name to exactly that shape,
#: so this is a declared, checked exemption and not a licence.
_FURNITURE_RULES = {
    "draw_solution_header": "the grey hairline under one solution's header line",
    # "draw_running_head" ruled the line under the answer page's running
    # head until the owner took that line off (2026-11-09): it strokes nothing.
}

#: The contents page's one piece of ruled furniture, held to the same shape.
_TOC_FURNITURE_RULES = {
    "draw_title_rule": "the rule under the contents page's title",
}


def _furniture_rule_violations(source: str, rules: dict = _FURNITURE_RULES) -> List[str]:
    """Every way a :data:`_FURNITURE_RULES` function exceeds one horizontal rule.

    Each must exist, make exactly one call through a drawing door, that call
    must be ``line``, and its two y arguments must be the same expression --
    the shape of one horizontal rule, which no grid walk has.
    """
    tree = _ast.parse(source)
    found: List[str] = []
    functions = {
        node.name: node
        for node in _ast.walk(tree)
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
    }
    for name in rules:
        function = functions.get(name)
        if function is None:
            found.append(f"{name} is declared but not defined")
            continue
        calls = [
            node
            for node in _ast.walk(function)
            if isinstance(node, _ast.Attribute) and node.attr in _STROKERS
        ]
        if len(calls) != 1:
            found.append(f"{name} reaches {len(calls)} drawing doors, not one")
            continue
        door = calls[0]
        parent = next(
            (
                node
                for node in _ast.walk(function)
                if isinstance(node, _ast.Call) and node.func is door
            ),
            None,
        )
        if door.attr != "line" or parent is None or len(parent.args) != 4:
            found.append(f"{name} draws through .{door.attr}, not one line call")
            continue
        if _ast.dump(parent.args[1]) != _ast.dump(parent.args[3]):
            found.append(f"{name}'s line is not horizontal")
    return found


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
        """Since the approved solutions mockup, outside the exemption **or**
        the declared page furniture (:data:`_FURNITURE_RULES`): the solution
        header's hairline and the running head's rule, each held to one
        horizontal line by :func:`_furniture_rule_violations`. The approved
        contents restyle added the TOC's own (:data:`_TOC_FURNITURE_RULES`),
        the rule under its title, held to the same one-line shape."""
        for module in _GUARDED:
            source = _source_of(module)
            outside = [
                violation
                for violation in stroke_violations(source)
                if not any(
                    f": {name} rules a line" in violation
                    for name in (
                        _FURNITURE_RULES if module is book_answer_vector
                        else _TOC_FURNITURE_RULES if module is book_toc_vector
                        else {}
                    )
                )
            ]
            assert outside == [], module.__name__
        assert _furniture_rule_violations(_source_of(book_answer_vector)) == []
        assert _furniture_rule_violations(
            _source_of(book_toc_vector), _TOC_FURNITURE_RULES
        ) == []

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

        **Plus the two furniture rules since the approved solutions mockup**
        (:data:`_FURNITURE_RULES`): they stroke, they are *not* exempt (they
        hold no grid), and they are admitted only as one horizontal rule each.
        """
        strokes = {
            owner.name
            for node, owner in _strokers_of(_source_of(book_answer_vector))
            if owner is not None
        }
        assert strokes == {"draw_answer_cells", "draw_solved_joins"} | set(_FURNITURE_RULES)
        # Both hold the grid, which is what makes them exempt rather than
        # tolerated: the set above is a subset of the derivation's own.
        exempt = set(exempt_functions(_source_of(book_answer_vector)))
        assert strokes - set(_FURNITURE_RULES) <= exempt
        # And the furniture is tolerated, not exempt: neither holds the grid.
        assert not (set(_FURNITURE_RULES) & exempt)

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
        assert len(members) == 18, sorted(members)
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
        assert len(unwatched) == 10, sorted(unwatched)
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
        the same names. Asserted as a set equality rather than as a count, so a
        member that appeared *and* one that vanished could not cancel.

        **The count was sixteen until CARD-314 and is eighteen**, the two added
        being ``begin_marked``/``end_marked`` — the marked-content brackets
        CON-020's clue-digit provenance is carried in. Both are classified in
        :data:`_NOT_A_DOOR_BECAUSE` by their own measurement (they emit ``BMC``
        and ``EMC``, neither a path operator), so :data:`_STROKERS` is unmoved
        at eight: this card added two members to the vocabulary and no door to
        the page.
        """
        assert ContentStream.__mro__ == (ContentStream, object)
        own = sorted(name for name in vars(ContentStream) if not name.startswith("_"))
        assert _public_members(ContentStream) == own, (
            _public_members(ContentStream),
            own,
        )
        assert len(own) == 18, own
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

    **Since the approved solutions mockup** the paragraph above is history:
    each solution's header draws its tier's dots flush right (through
    ``book_puzzle_vector.draw_tier_dots``, the puzzle header's round-mark
    site), so an answer page does print dots, and
    :meth:`test_no_answer_page_draws_a_round_mark_today` now asserts that
    rather than their absence. The box cells below are unchanged.
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
        """The stated limit, as a test rather than as prose (G-1) -- inverted.

        A ``c`` operator is how :meth:`ContentStream.round_mark` draws a
        quadrant. This cell used to assert no answer page emitted one, as
        CARD-233's signal to update AC-5. The approved solutions mockup is
        that signal: every solution's header now draws its tier's dots flush
        right, through ``book_puzzle_vector.draw_tier_dots`` (the puzzle
        header's own round-mark site, not a second one). So the reading is
        now the other way round, per page kind: every answer page draws a
        round mark, and the answer writer reaches ``round_mark`` only through
        ``draw_tier_dots``. The approved contents restyle did the same for the
        TOC: its level rows carry their tier's dots, through the same site.
        (The name is kept: it is cited by node id.)
        """
        def has_curve(text: str) -> bool:
            return " c\n" in text or text.rstrip().endswith(" c")

        answers = pdf_vector.content_streams(_written(recorded.answer_streams()))
        assert answers
        for text in answers:
            assert has_curve(text), "a solution header drew no tier dots"
        tocs = pdf_vector.content_streams(_written(recorded.toc_streams()))
        assert has_curve(tocs[0]), "the contents drew no level's tier dots"
        assert "draw_tier_dots" in _source_of(book_toc_vector)
        assert "round_mark" not in _source_of(book_answer_vector)
        assert "draw_tier_dots" in _source_of(book_answer_vector)
        assert "round_mark" not in _source_of(book_toc_vector)


# --------------------------------------------------------------------------
# AC-6 — the answer caption still holds CON-020's floor, read off the stream
# --------------------------------------------------------------------------

#: CON-020's floor for reader-facing interior text, in points.
_FLOOR_PT = 10.0

def _caption_reading(text: str, wanted) -> Optional[str]:
    """``text`` as the caption it is a reading of — whole or clipped — or ``None``.

    The clip loop is ``clipped[:-2] + "…"`` applied until the string fits, so
    every clipped reading is ``caption[:k] + "…"``. A reading that is not in
    the set of unclipped captions is a *clip*, not an omission (F-297-03).
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


class TestAnswerPages_CaptionHoldsTheFloorInTheStream:
    """AC-6 (CON-020): the solution header's ``Tf`` sizes are at or above 10 pt.

    Read off the written stream's own ``Tf`` operand — a *point* size against
    the page. The header sets the number alone at 12 pt and the picture's name
    in grey at the 10 pt floor; nothing is set under the drawing.
    """

    @staticmethod
    def _names(recorded: _Recorded) -> List[str]:
        """Every picture name the vector answer key's headers set."""
        return TestAnswerKey_IsTheOnlyPlaceTheTitleIsPrinted._titles_of(recorded)

    @staticmethod
    def _header_readings(recorded: _Recorded) -> List[Tuple[float, str]]:
        """``(size, reading)`` for every header name the vector pages set, clips included."""
        names = set(TestAnswerKey_IsTheOnlyPlaceTheTitleIsPrinted._titles_of(recorded))
        return [
            (size, reading)
            for stream_text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
            for size, text in _shows(stream_text)
            if (reading := _caption_reading(text, names)) is not None
        ]

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
        """Read off the solution header since the approved mockup: the name
        (whole or clipped) and the number, each at or above the floor; and
        the old caption line is set nowhere on a vector answer page."""
        wanted = set(self._captions(recorded))
        assert wanted, "the book has no answer captions to look for"
        found = self._header_readings(recorded)
        for size, text in found:
            assert size >= _FLOOR_PT, (size, text)
        numbers = {
            str(number) for _, number, _, _ in recorded.answers
        } | {str(number) for plan, _, _, _ in recorded.packed for number in plan.numbers}
        shown = [
            (size, text)
            for stream_text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
            for size, text in _shows(stream_text)
        ]
        # A bare digit is also a clue digit (CON-020's exemption, below the
        # floor), so each number is asserted to be set at or above the floor
        # at least once -- its header -- rather than every "1" on the page.
        for number in numbers:
            assert any(text == number and size >= _FLOOR_PT for size, text in shown), number
        assert not [
            text
            for stream_text in pdf_vector.content_streams(
                _written(recorded.answer_streams())
            )
            for _, text in _shows(stream_text)
            if _caption_reading(text, wanted) is not None
        ], "the caption line moved into the header and is set nowhere else"
        assert found, (
            "Book 1's answer key prints captions, so an empty reading here "
            "is the writer failing to set them, not CARD-197's omission"
        )

    def test_the_two_media_clip_the_same_captions_to_the_same_string(
        self, recorded, profile
    ) -> None:
        """F-297-03: each solution's name is set by the header exactly once,
        as the name itself or a clip of it (a stem plus "…"), never another
        puzzle's."""
        names = self._names(recorded)
        readings = [reading for _, reading in self._header_readings(recorded)]
        assert readings, "the vector pages set no caption"
        assert sorted(_caption_behind(r, set(names)) for r in readings) == sorted(set(names)), (
            readings,
            names,
        )
        for reading in readings:
            name = _caption_behind(reading, set(names))
            assert reading == name or (
                reading.endswith("…") and name.startswith(reading[:-1])
            ), (name, reading)

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


def _furniture_coordinates(slots, frame, height: float, dpi: int) -> Tuple[set, set]:
    """The page furniture the approved solutions mockup added, in points.

    Not COMP-007 positions themselves but placed against them: each slot's
    header hairline runs across its usable width, 0.3 of its band's height
    below the band's centre (``header_band``, COMP-007's), and the running
    head's rule runs across the page frame 0.55 of the way down the
    ``RUNNING_HEAD_MM`` strip above the tiles. The two ratios are the writer's
    own, restated here because no helper exposes the rule positions; the
    geometry they are ratios of is read off the layout and the frame.
    """
    xs: set = set()
    ys: set = set()
    for slot in slots:
        band = header_band(slot)
        placement = slot.page
        if band.height > 0 and placement is not None:
            xs.update((_pt(placement.usable_left, dpi), _pt(placement.usable_right, dpi)))
            ys.add(_flip(band.center_y + band.height * 0.3, height, dpi))
    xs.update((_pt(frame.left, dpi), _pt(frame.right, dpi)))
    ys.add(_flip(frame.top + RUNNING_HEAD_MM * dpi / 25.4 * 0.55, height, dpi))
    # The clue-gutter shading (CLUE_SHADE, the puzzle pages' own
    # ``shade_clue_cells``): its outer edge is the drawing's own edge,
    # COMP-007's ``drawing_left``/``drawing_top``.
    for slot in slots:
        if slot.page is not None:
            xs.add(_pt(slot.page.drawing_left, dpi))
            ys.add(_flip(slot.page.drawing_top, height, dpi))
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
    crossed with the packed page at two and at four tiles, with the case
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
                answer_section_spec(generator.page_spec(page_number)),
            )
            if packed is None:
                continue
            plan = PackedAnswerPage(
                answers=tuple(
                    Answer(number=index + 1, width=extent, height=extent, level=Tier.EASY)
                    for index in range(capacity)
                ),
                capacity=capacity,
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
            furniture_x, furniture_y = _furniture_coordinates(
                packed.slots, frame, frame.height, packed.dpi
            )
            stated_x, stated_y = stated_x | furniture_x, stated_y | furniture_y
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
            payload.row_clues, payload.column_clues, answer_section_spec(generator.page_spec(11))
        )
        stream = book_answer_vector.answer_page(
            generator.page_spec(11), generator.dpi, payload, 1, 11, "Zarquon"
        )
        (text,) = pdf_vector.content_streams(_written([stream]))
        xs, _ = _page_coordinates(text)
        stated_x, _ = _stated_coordinates([layout], layout.height, layout.dpi)
        furniture_x, _ = _furniture_coordinates(
            [layout], page_frame(generator.page_spec(11)), layout.height, layout.dpi
        )
        stated_x |= furniture_x
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
        # The folio: the puzzle pages' centred footer line, one 9 pt gap
        # above the bottom margin (owner, 2026-11-11).
        expected.add(
            _flip(frame.bottom - round(9.0 * generator.dpi / 72.0), frame.height, generator.dpi)
        )

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


class TestAnswerPages_TheJoinsAreSetInTheirOwnTone:
    """The grey join between two filled cells reaches the stream in its own tone."""

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
        """The picture's name is set in the solution header, after the number,
        in the band COMP-007's ``header_band`` reports for its tile. Its word
        is read back from poppler and held to the header's anchors: its left
        edge one gap after the number's advance from the tile's usable left
        edge, and its middle inside the band. (The node id predates the
        caption's move into the header and is kept.)
        """
        generator = BookPDFGenerator(_book())
        puzzle = _puzzle(12, 12, number=1, name="Snowflake")
        payload = generator._payload(puzzle)
        packed = compute_packed_solved_layout(
            [(payload.row_clues, payload.column_clues)],
            2,
            answer_section_spec(generator.page_spec(11)),
        )
        layout = packed.slots[0]
        stream = book_answer_vector.packed_answer_page(
            generator.page_spec(11),
            generator.dpi,
            PackedAnswerPage(
                (Answer(number=1, width=12, height=12, level=Tier.EASY),), capacity=2
            ),
            [(puzzle["id"], payload)],
            11,
            {},
        )
        data = _written([stream])
        words = pdf_vector.word_boxes(data, out_dir=tmp_path)
        picked = [word for word in words if word.text == "Snowflake"]
        assert len(picked) == 1, [word.text for word in words]

        face = interior_face_metrics()
        scale = 72.0 / generator.dpi
        placement = layout.page
        assert placement is not None
        band = header_band(layout)
        assert band.height > 0
        # The header's own anchors: the number at SOLUTION_NUMBER_PT from the
        # usable left edge, then the name 0.6 of its own size further on.
        number_px = book_answer_vector.SOLUTION_NUMBER_PT * generator.dpi / 72.0
        name_px = INTERIOR_FOOTER_LINE_PT * generator.dpi / 72.0
        name_left = (
            placement.usable_left
            + book_vector_draw.advance_px("1", number_px, face)
            + name_px * 0.6
        )
        left = min(word.left for word in picked)
        assert abs(left - name_left * scale) <= 1.0, (left, name_left * scale)
        assert max(word.right for word in picked) < placement.usable_right * scale

        middle = (
            min(word.top for word in picked) + max(word.bottom for word in picked)
        ) / 2
        band_top = (band.center_y - band.height / 2) * scale
        band_bottom = (band.center_y + band.height / 2) * scale
        assert band_top <= middle <= band_bottom, (middle, band_top, band_bottom)
        # And nothing of the name is under the drawing any more.
        assert middle < placement.drawing_bottom * scale


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

