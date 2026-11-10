"""CARD-205 — the table of contents lists sections, not puzzles.

    AC-1  TestBookToc_ListsSectionsNotPuzzles
    AC-2  TestBookToc_PageNumbersMatchTheWalk
    AC-3  TestBookToc_RangeRowsFollowTheLevelRuns
    AC-4  TestBookToc_SkipsEmptyLevels
    AC-5  TestBookToc_KdpAgreesWithTheExportedCount
    AC-6  TestBookToc_LeaderDotsStayInsideTheGap
    AC-7  TestBookToc_EmptyBookHasNoTocPage

Review cycle 1 added two classes that are no AC's own:

    F-001 TestBookToc_TheRowCountIsWhatTheCountFunctionPredicts — the
          builder and the count function called *directly*, over one-, two-
          and three-level books, so their equality is not pinned by a
          coincidence of literals at a single level count.
    F-003 TestBookToc_TheErrorPathsRaiseAndNameTheProblem — the card's five
          raise paths, plus ``interior_stream``'s new row-count tripwire.

This file replaces CARD-200's own, whose three classes
(``…ListsEveryPuzzleAgainstItsRealPageNumber``,
``…TitleResolutionMatchesTheAnswerSections``,
``…OverflowsToASecondPageWithoutLosingAnEntryOrBreakingLaterNumbering``)
asserted exactly the behaviour the owner's 2026-10-13 decision removed: one
row per puzzle, captioned through ``answer_caption``, spilling across several
pages. They are not kept alongside the new ones — a test that pins the old
listing would now have to be marked expected-to-fail, which is a slower way
of deleting it. What they protected that is *still* true is protected here
instead: every row points at a page the walk really planned (AC-2, where
CARD-200's own version pointed each puzzle at its own page), and the measured
split still decides how many TOC pages there are rather than a hardcoded one
(AC-5). ``answer_caption``/``answer_title`` keep their own coverage in
``tests/test_book_solved_answer_key.py`` and ``tests/test_book_solved_page.py``
— this card removes the TOC's *use* of them, not the functions (G-3).

**How this file reads a TOC page's own rows**: the downstream ``toc``
writer is handed each page's :class:`TocEntry` slice by
:meth:`interior_stream`, and :func:`_spy_toc_pages` records what it was
handed. AC-6 and the group gaps are geometry claims, read off the vector
page's own ``Td`` operands (:func:`_vector_toc_page`).
"""

from __future__ import annotations

import dataclasses
import inspect
from typing import Dict, List, NamedTuple, Optional, Tuple

import pytest
from PIL import ImageDraw

from nonogram.admin.book_dividers import SOLUTIONS_SLOT as _SOLUTIONS_SLOT
from nonogram.admin.book_kdp import unpaired_interior_page_count
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_plan import TIERS
from nonogram.admin.book_pdf_generator import (
    DPI,
    GUIDE_PAGE_COUNT,
    GUIDE_TITLE,
    TOC_ENTRY_GAP_PT,
    TOC_ENTRY_PT,
    TOC_GROUP_GAP_PT,
    TITLE_PAGE_COUNT,
    TOC_SOLUTIONS_LABEL,
    TOC_TITLE,
    BookPDFGenerator,
    DividerPagePlan,
    PuzzlePagePlan,
    TocEntry,
    default_toc_frame,
    interior_page_count,
    _toc_entries_per_page,
    measured_toc_page_count,
    page_frame,
    structural_toc_entries,
    structural_toc_entry_count,
    toc_range_label,
    type_px,
)
from tests.helpers.book_corpus import corpus_book, puzzle
from nonogram.admin.book_vector import ContentStream
from tests.helpers.pdf_pages import page_image
from tests.helpers.pdf_pages import same_page as _same_page

#: Enough puzzles per level to make the three ranges unmistakable and to put
#: the book well past the point where a TOC of one row per puzzle would have
#: needed several pages (CARD-200's Book 1 capacity was ~43 rows a page).
#: 60/60/30 is the card's own AC-3 split.
AC3_SPLIT = (60, 60, 30)


def _book(book_id: str = "card-205-toc", titles: Optional[Dict[str, str]] = None) -> Book:
    return Book(
        book_id=book_id,
        metadata=BookMetadata(
            title="Winter Pictures",
            description="CARD-205's own TOC test.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=corpus_book().trim_width_cm,
        trim_height_cm=corpus_book().trim_height_cm,
        gutter_margin_cm=corpus_book().gutter_margin_cm,
        outside_margin_cm=corpus_book().outside_margin_cm,
        puzzle_titles=titles or {},
    )


def _structural_shape(
    *levels: Tuple[str, str, int], solutions_page: int
) -> List[TocEntry]:
    """A structural TOC's rows, built by hand with the flags where they belong.

    The geometry tests below need rows whose ``starts_group`` is set exactly
    where ``structural_toc_entries`` sets it, but they must not *call* that
    function: a drawing test that asked the production builder for its input
    could only ever prove the drawing agrees with the builder, and would go
    green on a day both had dropped the flag together. This states the shape
    independently — a heading and a range row per level, then the solutions —
    and ``TestBookToc_RowsDeclareTheGroupsTheyOpen`` is the separate test
    that the real builder produces this same shape.
    """
    entries = [TocEntry(GUIDE_TITLE, 1)]
    for heading, range_label, page in levels:
        entries.append(TocEntry(heading, None, starts_group=True))
        entries.append(TocEntry(range_label, page))
    entries.append(TocEntry(TOC_SOLUTIONS_LABEL, solutions_page, starts_group=True))
    return entries


def _puzzles(**per_tier: int) -> List[dict]:
    """``_puzzles(easy=60, medium=60, hard=30)`` — 20x20s, none of them pairable.

    20x20 with 4-deep clues is the same shape CARD-200's own corpus used: too
    large for two to share a page, so a level's puzzle pages are its puzzle
    count and the ranges this file asserts are not a verdict of the pairing
    walk. The order is deliberately **not** print order (hard first) wherever
    more than one tier is asked for, so every assertion below is also an
    assertion that :func:`print_order`'s grouping (INV-009) is what makes a
    level's puzzle numbers contiguous at all.
    """
    rows: List[dict] = []
    for tier in ("hard", "medium", "easy"):
        for index in range(per_tier.get(tier, 0)):
            rows.append(
                puzzle(f"card205-{tier}-{index}", 20, 20, 4, tier, f"{tier.title()} {index}")
            )
    return rows


def _same_written_page(written, expected) -> bool:
    """Whether two pages in ONE medium are the same page.

    Two bitmaps are compared by ink as ``same_page`` does; two content streams
    by their bytes (the writer is deterministic, so the stream is the page's
    identity). A bitmap against a stream is REFUSED, not answered: ``!=``
    across media is vacuously true and ``==`` is vacuously false (CARD-322's
    lesson 2), so a caller that holds one of each has built the wrong
    expectation.
    """
    if isinstance(written, ContentStream) and isinstance(expected, ContentStream):
        return written.render() == expected.render()
    assert not isinstance(written, ContentStream) and not isinstance(expected, ContentStream), (
        f"a {type(written).__name__} was held against a {type(expected).__name__}: "
        "build the expected page in the medium the book wrote"
    )
    return _same_page(written, expected)


def _spy_toc_pages(
    generator: BookPDFGenerator, puzzles: List[dict], monkeypatch: pytest.MonkeyPatch
) -> List[List[TocEntry]]:
    """Every TOC page's own ``entries``, one list per TOC page.

    Spies the downstream ``toc`` writer on ``generator.pages``, which is what
    the walk hands each page's slice to.
    """
    recorded: List[List[TocEntry]] = []
    writer = generator.pages.toc

    def spy_writer(rows, frame, dpi, page_number):
        recorded.append(list(rows))
        return writer(rows, frame, dpi, page_number)

    monkeypatch.setattr(generator, "pages", dataclasses.replace(generator.pages, toc=spy_writer))
    for _ in generator.interior_stream(puzzles).pages:
        pass
    return recorded


def _rows_of(
    generator: BookPDFGenerator, puzzles: List[dict], monkeypatch: pytest.MonkeyPatch
) -> List[TocEntry]:
    """Every TOC row of a book, in order, across however many pages it took."""
    return [row for page in _spy_toc_pages(generator, puzzles, monkeypatch) for row in page]


#: **The three node ids in this file that still tie the plan to the pixels.**
#:
#: Seven tests here were converted to read the page plan instead of drawing the
#: book (CARD-219). A plan reading cannot witness what the drawing walk did, so
#: the tie is carried by these three and by nothing else -- measured, not
#: assumed:
#:
#: * ``M29`` (``book_pdf_generator.py:6923``, ``range(toc_page_count)`` ->
#:   ``range(toc_page_count + 1)``, so the walk yields one TOC page more than
#:   the plan says) reds **21 cells before the conversion and 14 after**, plus
#:   **4 errors in both arms**: the four
#:   ``TestBookToc_PageNumbersSurviveTheTitlePage`` node ids, whose shared
#:   rendering fixture raises under this mutant rather than reaching an
#:   assertion. An error is a kill and not a pass, but it is not a *failure
#:   cell*, so two of the three carriers below kill M29 by erroring and the
#:   third (``test_the_named_pages_really_are_those_pages``) by failing. The
#:   7 cells the conversion cost are **exactly** the seven converted tests,
#:   name for name.
#: * ``Q6``/``M15`` (an off-by-one in ``interior_stream``'s
#:   ``first_answer_page``, ``:6718``-``:6720``) reds **4 cells before and 3
#:   after** -- the lost one being
#:   ``TestBookToc_PageNumbersMatchTheWalk::test_each_row_points_at_the_page_the_walk_planned``
#:   -- and the three survivors are exactly the node ids below.
#:
#: Both pairs re-measured 2026-10-24 by CARD-219's fix round, in both arms (the
#: fork point's own copy of this file against this one, the same ``src`` mutant
#: over each), and both reproduce cycle 1's figures to the cell.
#:
#: So: **do not delete, narrow or convert these three without replacing the
#: tie.** CARD-220 is chartered to prune this file for redundancy and this is
#: the list it must read first. :func:`test_the_drawn_tie_is_still_carried_here`
#: holds each one to being present, so pruning one reds rather than passing.
DRAWN_TIE_CARRIERS = (
    "TestBookToc_PageNumbersSurviveTheTitlePage::test_the_solutions_row_points_at_the_solutions_divider",
    "TestBookToc_PageNumbersSurviveTheTitlePage::test_the_comparison_would_have_caught_a_one_page_drift",
    "TestBookToc_PageNumbersMatchTheWalk::test_the_named_pages_really_are_those_pages",
)

#: The three spellings by which a test in this file reaches a **drawn** page:
#: the spy on the drawing call, the rendered-interior fixture, and the page
#: comparison. Read off the three carriers above rather than invented.
DRAWN_PAGE_IDIOMS = ("_rows_of", "_same_page", "rendered")


def test_the_drawn_tie_is_still_carried_here() -> None:
    """The fence on the list above, so that pruning it reds instead of passing.

    Added by CARD-219's fix round (cycle 1, F-004/F-006). Narrowing seven
    docstrings to the terms they really cover is only safe while the tests
    that cover the rest are still here, and the card that is chartered to
    prune this file for redundancy (CARD-220) would otherwise have nothing but
    prose to warn it. A prose fence that nothing runs is the shape this card
    exists to stop shipping, so this is the fence as a test.

    Two readings, in order: the node id resolves on this module, and its body
    still reaches a drawn page by one of :data:`DRAWN_PAGE_IDIOMS`. The second
    is a **name check and not a proof** — it cannot know a page was rasterised
    — but it reds on the one edit that matters, converting a carrier to a plan
    reading, because a plan reading has no reason to name any of the three.
    """
    resolved: dict[str, object] = {}
    missing: list[str] = []
    for node_id in DRAWN_TIE_CARRIERS:
        class_name, _, test_name = node_id.partition("::")
        owner = globals().get(class_name)
        member = getattr(owner, test_name, None) if isinstance(owner, type) else None
        if member is None:
            missing.append(node_id)
        else:
            resolved[node_id] = member

    assert not missing, (
        f"{len(missing)} of this file's drawn-tie carriers no longer exist: "
        f"{missing}. These are the only tests here that witness the page plan "
        "against the pages actually yielded — measured: 14 of M29's 21 cells "
        "and 3 of Q6's 4 — and seven converted tests' docstrings point at "
        "them for the claims they gave up. Replace the tie before removing a "
        "carrier, and update DRAWN_TIE_CARRIERS with the measurement."
    )

    plan_only = sorted(
        node_id
        for node_id, member in resolved.items()
        if not any(
            idiom in inspect.getsource(member) for idiom in DRAWN_PAGE_IDIOMS
        )
    )
    assert not plan_only, (
        f"{plan_only} no longer reach a drawn page by any of "
        f"{list(DRAWN_PAGE_IDIOMS)}, so this file may have converted its last "
        "plan-to-pixel tie away. If the tie moved, move this list with it."
    )


def _planned_rows(generator: BookPDFGenerator, puzzles: List[dict]) -> List[TocEntry]:
    """Every TOC row of a book, in order, **with no page drawn**.

    Read off :attr:`InteriorStream.toc_entries` (CARD-289): the rows
    ``interior_stream`` built and the TOC pages draw, settled before a pixel
    exists. Nothing here computes a page number, so an off-by-one in
    production's own ``first_answer_page`` shows up in the rows these tests
    read. The tie between these rows and the drawn pages is carried by
    :data:`DRAWN_TIE_CARRIERS`.
    """
    return list(generator.interior_stream(list(puzzles)).toc_entries)


def _divider_pages(generator: BookPDFGenerator, puzzles: List[dict]) -> List[Tuple[str, int]]:
    """``(level label, its divider's interior page)`` from the walk itself."""
    decided = generator.section_plan(list(puzzles))
    return [
        (entry.level.label, entry.page_number)
        for entry in decided.pages
        if isinstance(entry, DividerPagePlan)
    ]


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestBookToc_ListsSectionsNotPuzzles:
    """One guide row, a heading + a range row per level, one solutions row —
    and no row naming an individual puzzle."""

    def test_the_rows_are_exactly_the_books_sections(self) -> None:
        """Converted by CARD-219: a positional claim, read off the plan.

        It witnesses the rows ``structural_toc_entries`` produces, and not
        that those are the rows a drawn page carried: that tie is
        :func:`_rows_of`'s, in the eleven tests of this file that still spy on
        the drawing call, and the plan-to-pixel tie is
        :data:`DRAWN_TIE_CARRIERS`'.
        """
        easy, medium, hard = AC3_SPLIT
        puzzles = _puzzles(easy=easy, medium=medium, hard=hard)
        generator = BookPDFGenerator(_book("card-205-ac1"))

        rows = _planned_rows(generator, puzzles)

        assert [row.label for row in rows] == [
            GUIDE_TITLE,
            "Easy",
            "Puzzles 1–60",
            "Medium",
            "Puzzles 61–120",
            "Hard",
            "Puzzles 121–150",
            TOC_SOLUTIONS_LABEL,
            "Easy",
            "Medium",
            "Hard",
        ]
        assert len(rows) == 2 + 3 * 3, (
            "a three-level book lists eight rows however many puzzles it holds"
        )

    def test_no_row_names_an_individual_puzzle(self) -> None:
        """The owner's decision, stated as the thing that must not be there.

        Every one of these puzzles carries a distinct picture name, and
        CARD-200's listing printed all 150 of them ("Puzzle 37 — Easy 36").
        Not one may appear now — nor the per-puzzle caption's own shape.

        Converted by CARD-219: a claim about which labels the rows carry, read
        off the plan. It witnesses the labels ``structural_toc_entries``
        produces and not that a page printed them; see
        :data:`DRAWN_TIE_CARRIERS` for what still ties plan to pixels here.
        """
        puzzles = _puzzles(easy=60, medium=60, hard=30)
        generator = BookPDFGenerator(_book("card-205-ac1-names"))

        labels = [row.label for row in _planned_rows(generator, puzzles)]
        blob = "\n".join(labels)

        for row in puzzles:
            assert row["puzzle_name"] not in blob, (
                f"{row['puzzle_name']!r} is a puzzle's own title and has no "
                "place in a structural table of contents"
            )
        assert "—" not in blob, (
            "the em dash is `answer_caption`'s own 'Puzzle N — Title' "
            "separator; no TOC row is captioned that way any more"
        )
        assert not any(label.startswith("Puzzle ") for label in labels), (
            "'Puzzle N' names one puzzle; a range row reads 'Puzzles N–M'"
        )

    def test_a_custom_puzzle_title_reaches_no_toc_row_either(self, monkeypatch) -> None:
        """The TOC does no title lookup at all now (the card's step 5)."""
        puzzles = _puzzles(easy=2)
        generator = BookPDFGenerator(
            _book("card-205-ac1-titles", {"card205-easy-0": "Owner's Custom Title"})
        )

        labels = [row.label for row in _rows_of(generator, puzzles, monkeypatch)]

        assert "Owner's Custom Title" not in "\n".join(labels)
        assert labels == [GUIDE_TITLE, "Easy", "Puzzles 1–2", TOC_SOLUTIONS_LABEL, "Easy"]

    def test_only_the_level_headings_carry_no_page_number(self, monkeypatch) -> None:
        """A heading groups the row under it; the range row carries the page."""
        puzzles = _puzzles(easy=3, medium=3)
        generator = BookPDFGenerator(_book("card-205-ac1-headings"))

        rows = _rows_of(generator, puzzles, monkeypatch)

        assert [row.label for row in rows if row.is_heading] == ["Easy", "Medium"]
        assert all(row.page is not None for row in rows if not row.is_heading)


class TestBookToc_RowsDeclareTheGroupsTheyOpen:
    """Which rows carry ``starts_group``, read off the real builder (Fix 2).

    The separation itself is a geometry claim, asserted on drawn rows by
    ``TestBookToc_GroupsAreSetOffFromWhatPrecedesThem`` against entries that
    file builds by hand. This is the other half, and the half that would
    otherwise be missing: that ``structural_toc_entries`` really flags the
    rows the drawing is waiting for. Without it both sides could drop the
    flag together and every test here would stay green on a TOC that had
    quietly gone back to eight evenly spaced rows.
    """

    def test_every_heading_and_the_solutions_row_open_a_group(
        self, monkeypatch
    ) -> None:
        puzzles = _puzzles(easy=3, medium=3, hard=3)
        generator = BookPDFGenerator(_book("card-205-fix2-flags"))

        rows = _rows_of(generator, puzzles, monkeypatch)

        assert [row.label for row in rows if row.starts_group] == [
            "Easy",
            "Medium",
            "Hard",
            TOC_SOLUTIONS_LABEL,
        ], "a three-level book's list opens four groups, the solutions last"
        assert [row.label for row in rows if not row.starts_group] == [
            GUIDE_TITLE,
            "Puzzles 1–3",
            "Puzzles 4–6",
            "Puzzles 7–9",
            "Easy",
            "Medium",
            "Hard",
        ], (
            "and nothing else does — the guide opens the list rather than a "
            "group within it, and a range row belongs to the heading above it"
        )

    def test_the_solutions_row_is_flagged_though_it_is_not_a_heading(
        self, monkeypatch
    ) -> None:
        """The distinction the flag exists for, stated on the real rows.

        ``is_heading`` and ``starts_group`` agree on every row of the list
        but this one, which is precisely why the drawing cannot read the
        former: the solutions row carries a page number *and* opens a group.
        """
        puzzles = _puzzles(easy=3, medium=3)
        generator = BookPDFGenerator(_book("card-205-fix2-flags-solutions"))

        rows = _rows_of(generator, puzzles, monkeypatch)
        solutions = [row for row in rows if row.label == TOC_SOLUTIONS_LABEL]

        assert len(solutions) == 1
        assert solutions[0].starts_group is True
        assert solutions[0].is_heading is False
        assert solutions[0].page is not None
        disagree = [row.label for row in rows if row.starts_group != row.is_heading]
        assert disagree == [TOC_SOLUTIONS_LABEL], (
            "the solutions row must be the only row where the two differ — "
            f"{disagree} differ, so `is_heading` is no longer a near-miss for "
            "the flag but a different rule altogether"
        )

    def test_a_one_level_book_still_opens_two_groups(self, monkeypatch) -> None:
        puzzles = _puzzles(easy=4)
        generator = BookPDFGenerator(_book("card-205-fix2-flags-one-level"))

        rows = _rows_of(generator, puzzles, monkeypatch)

        assert [row.label for row in rows if row.starts_group] == [
            "Easy",
            TOC_SOLUTIONS_LABEL,
        ]


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestBookToc_PageNumbersMatchTheWalk:
    """Every row's number is the interior position of the page it names."""

    def test_each_row_points_at_the_page_the_walk_planned(self) -> None:
        """The rows come off the stream's own plan (CARD-219, CARD-289).

        The solutions row is checked two ways: against the stream's own
        ``first_answer_page`` (the divider is the page before it), and against
        ``page_count - answer_page_count``, a derivation that shares no term
        with it, i.e. the last page that is not an answer page.
        """
        puzzles = _puzzles(easy=60, medium=60, hard=30)
        generator = BookPDFGenerator(_book("card-205-ac2"))

        rows = _planned_rows(generator, puzzles)
        decided = generator.section_plan(list(puzzles))
        # The three counts are settled eagerly by this call; nothing is drawn
        # unless `.pages` is walked, and it is not walked here.
        counted = generator.interior_stream(list(puzzles))
        dividers = _divider_pages(generator, puzzles)

        by_label = {row.label: row.page for row in rows}
        assert by_label[GUIDE_TITLE] == 1 + TITLE_PAGE_COUNT, (
            "the blank title page opens the interior and the guide follows it "
            "(INV-013 as amended 2026-10-17, CARD-206)"
        )
        # Each range row against its own level's divider, read off the same
        # SectionPlan the pages were drawn from.
        ranges = [row for row in rows if row.label.startswith("Puzzles ")]
        assert [row.page for row in ranges] == [page for _, page in dividers]
        assert [label for label, _ in dividers] == ["Easy", "Medium", "Hard"]

        assert by_label[TOC_SOLUTIONS_LABEL] == counted.first_answer_page - 1
        # And against the two counts the stream settles for itself: the last
        # page that is not an answer page is the divider that opens the
        # answer section.
        assert by_label[TOC_SOLUTIONS_LABEL] == (
            counted.page_count - counted.answer_page_count
        ), (
            f"the solutions row names interior page "
            f"{by_label[TOC_SOLUTIONS_LABEL]}, but this book's "
            f"{counted.page_count} pages end with {counted.answer_page_count} "
            "answer pages, so the divider that opens them is page "
            f"{counted.page_count - counted.answer_page_count}"
        )

    def test_the_named_pages_really_are_those_pages(self, monkeypatch) -> None:
        """Not just "the numbers agree with an arithmetic", but "the page at
        that position is the page the row names".

        The walk is replayed page by page and each named position is checked
        against what was actually yielded there: page 1 is the blank title
        page and page ``1 + TITLE_PAGE_COUNT`` a guide page (CARD-206), each
        level's named page is that level's own divider, and the solutions
        row's page is the SOLUTIONS divider that opens the answer section.
        """
        puzzles = _puzzles(easy=4, medium=4, hard=4)
        generator = BookPDFGenerator(_book("card-205-ac2-pages"))

        rows = _rows_of(generator, puzzles, monkeypatch)
        decided = generator.section_plan(list(puzzles))
        kind_of: Dict[int, str] = {}
        for entry in decided.pages:
            kind_of[entry.page_number] = (
                f"divider:{entry.level.label}"
                if isinstance(entry, DividerPagePlan)
                else "puzzle"
            )
        for number in range(1, TITLE_PAGE_COUNT + 1):
            kind_of[number] = "title"
        for number in range(
            1 + TITLE_PAGE_COUNT, TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 1
        ):
            kind_of[number] = "guide"
        solutions = (
            1
            + TITLE_PAGE_COUNT
            + GUIDE_PAGE_COUNT
            + decided.toc_page_count
            + len(decided.pages)
        )
        kind_of[solutions] = "divider:SOLUTIONS"

        assert kind_of[rows[0].page] == "guide"
        # The rows after Solutions point into the answer section, in order.
        cut = [row.label for row in rows].index(TOC_SOLUTIONS_LABEL) + 1
        rows, answer_rows = rows[:cut], rows[cut:]
        answer_pages = [row.page for row in answer_rows]
        assert answer_pages == sorted(answer_pages) and answer_pages[0] > rows[-1].page
        for heading, range_row in zip(rows[1:-1:2], rows[2:-1:2]):
            assert kind_of[range_row.page] == f"divider:{heading.label}", (
                f"the {heading.label} range row points at page "
                f"{range_row.page}, which is a {kind_of[range_row.page]} page"
            )
        assert kind_of[rows[-1].page] == "divider:SOLUTIONS"

    def test_the_numbers_move_with_the_tocs_own_length(self, monkeypatch) -> None:
        """The TOC is counted into the pages it names, not numbered as if it
        were not there — the mistake a hardcoded offset makes.

        The same book is measured against the walk's own
        ``1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count`` opening
        position: every
        level row's page must be at least that, and the first level's exactly
        that (its divider is the puzzle section's first page).
        """
        puzzles = _puzzles(easy=5, hard=5)
        generator = BookPDFGenerator(_book("card-205-ac2-offset"))

        rows = _rows_of(generator, puzzles, monkeypatch)
        decided = generator.section_plan(list(puzzles))
        first_section_page = (
            1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + decided.toc_page_count
        )

        ranges = [row for row in rows if row.label.startswith("Puzzles ")]
        assert ranges[0].page == first_section_page
        assert all(row.page >= first_section_page for row in ranges)
        assert rows[-1].page > ranges[-1].page


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookToc_RangeRowsFollowTheLevelRuns:
    """60/60/30 reads ``Puzzles 1–60``, ``61–120``, ``121–150``."""

    def test_the_three_ranges_are_the_cards_own_sample(self) -> None:
        """Converted by CARD-219: the range labels are a plan value.

        A claim about the strings the plan settles, not about ink and not
        about a drawn row count (:data:`DRAWN_TIE_CARRIERS`).
        """
        easy, medium, hard = AC3_SPLIT
        puzzles = _puzzles(easy=easy, medium=medium, hard=hard)
        generator = BookPDFGenerator(_book("card-205-ac3"))

        labels = [row.label for row in _planned_rows(generator, puzzles)]

        assert [label for label in labels if label.startswith("Puzzles ")] == [
            "Puzzles 1–60",
            "Puzzles 61–120",
            "Puzzles 121–150",
        ]

    def test_the_ranges_tile_the_book_with_no_gap_or_overlap(self) -> None:
        """A second, independent reading: the ranges parsed back out of the
        labels must be exactly 1..150, each puzzle in one level's range.

        Written as a parse of the printed text rather than as a repeat of the
        arithmetic that produced it — an off-by-one in
        ``toc_range_label``'s own ``start + 1`` would pass a test that
        rebuilt the expected strings the same way.

        Converted by CARD-219. "Printed text" here always meant the string the
        row carries, not ink: the parse is of ``row.label``, which the plan
        settles. Nothing about this reading needed the page it ends up on —
        and nothing in it witnesses one either (:data:`DRAWN_TIE_CARRIERS`).
        """
        puzzles = _puzzles(easy=60, medium=60, hard=30)
        generator = BookPDFGenerator(_book("card-205-ac3-tiling"))

        covered: List[int] = []
        for row in _planned_rows(generator, puzzles):
            if not row.label.startswith("Puzzles "):
                continue
            first, last = row.label.removeprefix("Puzzles ").split("–")
            covered.extend(range(int(first), int(last) + 1))

        assert covered == list(range(1, 151)), (
            "the level ranges must tile the book's puzzle numbers exactly "
            "once each, in print order"
        )

    def test_a_level_holding_one_puzzle_reads_in_the_singular(self, monkeypatch) -> None:
        """``Puzzle 7``, never ``Puzzles 7–7`` — a printed book is read.

        Not in the card's sample (which only shows multi-puzzle levels); a
        decision taken in ``toc_range_label``, whose own docstring carries
        the reasoning. Pinned here so a later edit cannot quietly reintroduce
        the degenerate range.
        """
        puzzles = _puzzles(easy=2, medium=1, hard=3)
        generator = BookPDFGenerator(_book("card-205-ac3-singular"))

        labels = [row.label for row in _rows_of(generator, puzzles, monkeypatch)]

        assert labels == [
            GUIDE_TITLE,
            "Easy",
            "Puzzles 1–2",
            "Medium",
            "Puzzle 3",
            "Hard",
            "Puzzles 4–6",
            TOC_SOLUTIONS_LABEL,
            "Easy",
            "Medium",
            "Hard",
        ]


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestBookToc_SkipsEmptyLevels:
    """A level with no printable puzzle gets no heading and no range row."""

    def test_an_all_easy_book_lists_one_level(self, monkeypatch) -> None:
        puzzles = _puzzles(easy=12)
        generator = BookPDFGenerator(_book("card-205-ac4"))

        rows = _rows_of(generator, puzzles, monkeypatch)

        assert [row.label for row in rows] == [
            GUIDE_TITLE,
            "Easy",
            "Puzzles 1–12",
            TOC_SOLUTIONS_LABEL,
            "Easy",
        ]
        assert "Medium" not in [row.label for row in rows]
        assert "Hard" not in [row.label for row in rows]

    def test_the_skipped_levels_are_exactly_the_ones_with_no_divider(
        self, monkeypatch
    ) -> None:
        """The TOC's levels and the book's divider pages are the same set —
        the guard is the walk's own, not a second one written for the TOC.
        """
        puzzles = _puzzles(easy=3, hard=3)  # medium empty
        generator = BookPDFGenerator(_book("card-205-ac4-dividers"))

        rows = _rows_of(generator, puzzles, monkeypatch)
        headings = [row.label for row in rows if row.is_heading]

        assert headings == [label for label, _ in _divider_pages(generator, puzzles)]
        assert headings == ["Easy", "Hard"]

    def test_a_run_with_no_readable_tier_gets_no_row_and_no_range(
        self, monkeypatch
    ) -> None:
        """The ungraded tail opens no divider, so it names no section — and,
        crucially, is **not** swept into the last named level's range.

        ``print_order`` ranks untiered rows after all three levels, so in the
        page plan their puzzle pages sit directly behind Hard's with nothing
        structural between them. A TOC that read "every puzzle page until the
        next divider" would print ``Puzzles 4–6`` under Hard here instead of
        ``Puzzles 4–5`` — a wrong range, in ink, that no test of the dividers
        themselves would catch.
        """
        puzzles = _puzzles(easy=3, hard=2)
        untiered = puzzle("card205-untiered", 20, 20, 4, "easy", "No Tier")
        untiered["difficulty_tier"] = "not-a-tier"
        puzzles.append(untiered)
        generator = BookPDFGenerator(_book("card-205-ac4-untiered"))

        rows = _rows_of(generator, puzzles, monkeypatch)

        assert [row.label for row in rows] == [
            GUIDE_TITLE,
            "Easy",
            "Puzzles 1–3",
            "Hard",
            "Puzzles 4–5",
            TOC_SOLUTIONS_LABEL,
            "Easy",
            "Hard",
        ]
        # The untiered puzzle really is in the book and really does print.
        decided = generator.section_plan(list(puzzles))
        printed = [
            number
            for entry in decided.pages
            if isinstance(entry, PuzzlePagePlan)
            for number in entry.numbers
        ]
        assert printed == [1, 2, 3, 4, 5, 6]


# --------------------------------------------------------------------------
# AC-5
# --------------------------------------------------------------------------


class TestBookToc_KdpAgreesWithTheExportedCount:
    """``book_kdp`` and the export must never disagree about the TOC's length.

    The defect this guards is invisible in any render: the KDP page count
    chooses the printed gutter margin, so a TOC entry rule changed in the
    generator and not in ``unpaired_interior_page_count`` binds the book at
    a margin computed for a book of a different length.
    """

    @staticmethod
    def _corpus() -> List[dict]:
        easy, medium, hard = AC3_SPLIT
        return _puzzles(easy=easy, medium=medium, hard=hard)

    def test_a_hundred_and_fifty_puzzles_take_one_toc_page(self) -> None:
        """Converted by CARD-219: one page, eight rows, both plan values.

        The book was rendered to count its TOC pages. The same
        number is on the plan (:attr:`SectionPlan.toc_page_count`), and the
        *reason* it is 1 is on the production function the stream itself asks
        — ``measured_toc_page_count`` over this book's own frame, the same call
        at the same two arguments. Neither figure is this test's own
        arithmetic.

        **What the two agreeing witnesses, narrowed to the truth of it.**
        ``section_plan`` (``src:6450``) makes that same call at those same
        arguments, so the pair is not independent and it does **not** stand in
        for the drawn count — this docstring used to say "the two agreeing is
        what the drawn count used to witness", and that sentence was false
        (CARD-219 cycle 1, F-004). What it does witness is the two terms that
        are not shared: ``structural_toc_entry_count`` (the row count
        ``section_plan`` measures the split from) against
        ``structural_toc_entries`` (the rows actually built, counted here as
        ``len(rows) == 8``), and that the frame and ``dpi`` the plan measured
        at are this book's own.

        **What it no longer witnesses**, measured: ``M29``, which makes the
        walk yield one TOC page more than the plan says, reds 21 cells on the
        pre-card tree and 14 here — and this test is one of the seven cells it
        lost. A test that reads the plan cannot see a drawn count; that is what
        conversion means, and the mutant is still killed 14 times over, plus
        four errors. The node ids that kill it *by drawing* are
        :data:`DRAWN_TIE_CARRIERS`.
        """
        puzzles = self._corpus()
        generator = BookPDFGenerator(_book("card-205-ac5"))

        rows = _planned_rows(generator, puzzles)
        decided = generator.section_plan(list(puzzles))
        frame = page_frame(generator.page_spec(1))

        assert measured_toc_page_count(len(rows), frame, DPI) == 1, (
            "the structural list fits one page"
        )
        assert decided.toc_page_count == 1
        assert len(rows) == 11

    def test_the_split_is_still_measured_and_not_hardcoded(self) -> None:
        """"One page" must be a verdict of the same arithmetic, not a literal.

        ``measured_toc_page_count`` is fed the structural row count on a real
        frame; fed enough rows it still splits. If the generator had been
        changed to return a constant 1, this would fail.
        """
        frame = page_frame(BookPDFGenerator(_book("card-205-ac5-split")).page_spec(1))

        assert measured_toc_page_count(8, frame, DPI) == 1
        assert measured_toc_page_count(0, frame, DPI) == 0
        assert measured_toc_page_count(500, frame, DPI) > 1, (
            "the measured split still splits — this card changed the count "
            "fed to it, not the arithmetic"
        )

    def test_kdp_reports_the_same_toc_length_the_export_wrote(self) -> None:
        """The cross-check, through both functions' real entry points.

        Every other term of the two page counts (puzzle pages, dividers,
        answer pages) is independent of the TOC, and the KDP estimate is
        defined as the generator's own *unpaired* baseline (EC-034), so the
        two totals agreeing is the statement that they agree about the TOC.
        Narrowly, and the narrow version is the true one: the two **call
        sites** agree — ``book_kdp.py:544`` and
        ``book_pdf_generator.py:6450`` each call ``measured_toc_page_count``
        over ``structural_toc_entry_count`` for themselves, and the pre-card
        defect was one of them not passing the term at all. It is *one*
        arithmetic called twice, so this says nothing about whether that
        arithmetic is right; the second assertion is what keeps the pair from
        being vacuous: under CARD-200's rule this book's TOC was four pages, so
        the pre-card entry rule would put the two totals four apart.

        Converted by CARD-219. The TOC length the export "wrote" was read by
        rendering the book and counting the drawing calls; it is read off the
        plan the drawing walk is driven by instead
        (:attr:`SectionPlan.toc_page_count`, the same term
        ``interior_stream`` bakes into every page position). The export's
        *own* figure — ``unpaired_page_count`` — is still read through its real
        entry point, and that call settles its three counts without drawing a
        page unless ``.pages`` is walked, which it is not here.

        **So "wrote" now means "planned to write".** That the walk then yields
        that many TOC pages is not witnessed here — ``M29``, which makes it
        yield one more, no longer reds this test — and is carried by
        :data:`DRAWN_TIE_CARRIERS`.
        """
        puzzles = self._corpus()
        book = _book("card-205-ac5-kdp")
        generator = BookPDFGenerator(book)

        stream = generator.interior_stream(list(puzzles))
        toc_pages_written = generator.section_plan(list(puzzles)).toc_page_count

        assert unpaired_interior_page_count(puzzles, book=book) == (
            stream.unpaired_page_count
        ), (
            "KDP's gutter-band page count and the generator's own unpaired "
            "baseline must agree term for term, the TOC's included"
        )
        frame = page_frame(generator.page_spec(1))
        assert measured_toc_page_count(len(puzzles), frame, DPI) == 4, (
            "the pre-CARD-205 rule (one row per puzzle) would have made this "
            "book's TOC four pages — so the agreement above is a real check "
            "of the new rule, not an identity that holds either way"
        )
        assert toc_pages_written == 1

    def test_the_sheet_free_toc_default_follows_the_new_rule_too(self) -> None:
        """The third caller of ``measured_toc_page_count`` (AC/EC/G gate).

        It has three callers, not two: ``interior_stream``'s own walk and
        ``book_kdp.unpaired_interior_page_count`` — both asserted above — and
        ``interior_page_count``'s sheet-free ``toc_pages`` default
        (:func:`default_toc_frame`), which every caller asking for a page
        count *without* a sheet to measure falls back to. The first two
        agreeing says nothing about the third, and before this test nothing
        in the suite could tell the old rule from the new one there: every
        test that reaches the default passes 0, 1, 3 or 7 puzzles, where the
        per-puzzle rule and the structural one both measure one TOC page. On
        ``default_toc_frame()`` they first disagree at 43 puzzles, and at 150
        it is 1 page against 4 — so leaving this unasserted let
        ``interior_page_count(150)`` report 310 for a book that is 307 pages
        long, and that figure chooses the printed KDP gutter.

        ``unpaired_page_count`` is the right-hand side because
        ``interior_stream`` builds it from exactly the terms this function
        defaults to — puzzle pages unpaired (one per puzzle), one answer page
        per puzzle, ``min(len(TIERS), count)`` dividers — and differs in one
        term only: it passes the TOC length measured off this book's own
        trim, where the left-hand side must derive it. The two sides
        therefore agree if and only if the default agrees about the TOC.
        """
        puzzles = self._corpus()
        book = _book("card-205-ac5-sheet-free")
        generator = BookPDFGenerator(book)

        stream = generator.interior_stream(list(puzzles))

        assert interior_page_count(len(puzzles)) == stream.unpaired_page_count, (
            "`interior_page_count`'s sheet-free TOC default and the TOC this "
            "book actually wrote must agree — every other term of the two "
            "counts is identical by construction"
        )

        assert measured_toc_page_count(len(puzzles), default_toc_frame(), DPI) == 4, (
            "non-vacuity: on the very frame the default measures on, the "
            "pre-CARD-205 rule (one row per puzzle) makes this book's TOC "
            "four pages, so the agreement above is a real check of the new "
            "rule and not an identity that holds either way"
        )
        assert structural_toc_entry_count(len(TIERS), len(puzzles)) == 11

    def test_the_gutter_band_itself_follows_the_new_count(self) -> None:
        """One step further out: the figure KDP's band lookup is given.

        A 150-puzzle book is near KDP's 151-300/301-500 boundaries, so this
        asserts the band the real page count lands in rather than only that
        two numbers match.

        The estimate is one answer page per puzzle, an upper bound that is
        exact only for a book whose answers are too large to pack. The 20x20s
        of :func:`_puzzles` used to be (the packing limit was 15x20); the
        owner raised it to ``PACKED_MAX_WIDTH`` x ``PACKED_MAX_HEIGHT``, so
        this corpus is sized one over that limit, read off the constants, to
        keep the book the estimate is meant to be exact for.
        """
        from nonogram.admin.book_answer_key import PACKED_MAX_HEIGHT, PACKED_MAX_WIDTH
        from nonogram.admin.book_kdp import kdp_page_band

        easy, medium, hard = AC3_SPLIT
        puzzles = [
            puzzle(
                f"card205-band-{tier}-{index}",
                PACKED_MAX_WIDTH + 1,
                PACKED_MAX_HEIGHT + 1,
                4,
                tier,
                f"{tier.title()} {index}",
            )
            for tier, count in (("hard", hard), ("medium", medium), ("easy", easy))
            for index in range(count)
        ]
        book = _book("card-205-ac5-band")
        generator = BookPDFGenerator(book)

        estimate = unpaired_interior_page_count(puzzles, book=book)
        real = generator.interior_stream(list(puzzles)).page_count

        assert kdp_page_band(estimate) == kdp_page_band(real), (
            f"the estimate ({estimate}) and the real book ({real}) must fall "
            "in the same KDP gutter band, or the printed margin is computed "
            "for a book that was never written"
        )


# --------------------------------------------------------------------------
# AC-6
# --------------------------------------------------------------------------


class _VectorMark(NamedTuple):
    """One string a vector TOC page set: its left/right edge and top, in px."""

    left: float
    right: float
    top: float
    text: str


def _vector_toc_page(
    generator: BookPDFGenerator, entries: List[TocEntry], page_number: int = 3
) -> Tuple[List[_VectorMark], Optional[str]]:
    """``(row marks, folio)`` of one TOC page as ``toc_page_stream`` writes it.

    Read off the stream's own ``Td`` operands and converted back to device
    pixels; widths are the embedded face's advances. The title (the first
    string) is dropped, and the folio is the last string when it sits below
    every row (``None`` when the page omitted it).
    """
    from nonogram.admin.book_toc_vector import toc_page_stream
    from nonogram.admin.book_vector import interior_face_metrics
    from nonogram.admin.book_vector_draw import advance_px, ascent_px

    face = interior_face_metrics()
    size_px = type_px(TOC_ENTRY_PT, generator.dpi)
    frame = page_frame(generator.page_spec(page_number))
    stream = toc_page_stream(entries, frame, generator.dpi, page_number)
    scale = stream.to_points(1.0)
    placed = _set_at(stream)
    assert placed[0][2] == TOC_TITLE, placed[:1]
    placed = placed[1:]
    folio = None
    if placed and placed[-1][2] == str(page_number) and all(
        y > placed[-1][1] for _, y, _ in placed[:-1]
    ):
        folio = placed.pop()[2]
    marks = []
    for x, y, text in placed:
        left = x / scale
        top = stream.height_px - y / scale - ascent_px(size_px, face)
        marks.append(_VectorMark(left, left + advance_px(text, size_px, face), top, text))
    return marks, folio


class TestBookToc_LeaderDotsStayInsideTheGap:
    """The dots lie strictly between the label and the number, touching neither."""

    #: ``_set_at`` reads operands rounded to a thousandth of a point (~0.004 px).
    SLACK_PX = 0.05

    @staticmethod
    def _rows(marks: List[_VectorMark]) -> Dict[float, Dict[str, _VectorMark]]:
        rows: Dict[float, Dict[str, _VectorMark]] = {}
        for mark in marks:
            if set(mark.text) == {"."}:
                kind = "dots"
            elif mark.text.isdigit():
                kind = "number"
            else:
                kind = "label"
            rows.setdefault(round(mark.top, 1), {})[kind] = mark
        return rows

    def test_every_dot_run_clears_the_label_and_the_number(self) -> None:
        generator = BookPDFGenerator(_book("card-205-ac6"))
        entries = [
            TocEntry(GUIDE_TITLE, 1),
            TocEntry("Easy"),
            TocEntry("Puzzles 1–60", 5),
            TocEntry("Medium"),
            TocEntry("Puzzles 61–120", 37),
            TocEntry("Hard"),
            TocEntry("Puzzles 121–150", 69),
            TocEntry(TOC_SOLUTIONS_LABEL, 86),
        ]
        frame = page_frame(generator.page_spec(3))
        gap = type_px(TOC_ENTRY_GAP_PT, DPI)
        marks, _ = _vector_toc_page(generator, entries)

        numbered = [parts for parts in self._rows(marks).values() if "number" in parts]
        assert len(numbered) == 5, "five rows carry a page number on this page"
        for parts in numbered:
            assert "dots" in parts, "every one of these rows leaves ample room for leaders"
            label, dots, number = parts["label"], parts["dots"], parts["number"]
            assert dots.left - label.right >= gap - self.SLACK_PX, "the dots start clear of the label"
            assert number.left - dots.right >= -self.SLACK_PX, "the dots end clear of the number"
            assert label.left == pytest.approx(frame.left, abs=self.SLACK_PX)
            assert number.right == pytest.approx(frame.right, abs=self.SLACK_PX)

    @staticmethod
    def _label_filling(room: float) -> str:
        """The longest label that fits ``room`` and leaves under a dot's width.

        Wide glyphs first, then the narrowest, so the remainder is closed to
        under one dot on whatever face the page is lettered in.
        """
        from nonogram.admin.book_vector import interior_face_metrics
        from nonogram.admin.book_vector_draw import advance_px

        face = interior_face_metrics()
        size_px = type_px(TOC_ENTRY_PT, DPI)

        def width(text: str) -> float:
            return advance_px(text, size_px, face)

        label = "W"
        while width(label + "W") <= room:
            label += "W"
        while width(label + "i") <= room:
            label += "i"
        assert width(label) <= room, "the label must fit the row"
        assert room - width(label) < width("."), "this label does not fill the row"
        return label

    @staticmethod
    def _room(generator: BookPDFGenerator) -> float:
        from nonogram.admin.book_vector import interior_face_metrics
        from nonogram.admin.book_vector_draw import advance_px

        frame = page_frame(generator.page_spec(3))
        number = advance_px("86", type_px(TOC_ENTRY_PT, DPI), interior_face_metrics())
        return (frame.right - frame.left) - number - 2 * type_px(TOC_ENTRY_GAP_PT, DPI)

    def test_a_label_that_leaves_no_room_gets_no_dot(self) -> None:
        """AC-6's own edge: fill the row, and the leaders simply disappear."""
        generator = BookPDFGenerator(_book("card-205-ac6-tight"))
        label = self._label_filling(self._room(generator))
        marks, _ = _vector_toc_page(generator, [TocEntry(label, 86)])
        assert sorted(mark.text for mark in marks) == sorted([label, "86"])

    def test_a_nearly_full_row_still_gets_the_dots_that_do_fit(self) -> None:
        """The run is maximal: drawn if and only if one more dot would not fit.

        Swept over label lengths from comfortably short to no room at all, with
        a minimum case count asserted so the sweep cannot silently shrink.
        """
        from nonogram.admin.book_vector import interior_face_metrics
        from nonogram.admin.book_vector_draw import advance_px

        face = interior_face_metrics()
        size_px = type_px(TOC_ENTRY_PT, DPI)
        generator = BookPDFGenerator(_book("card-205-ac6-nearly-full"))
        room = self._room(generator)
        longest = self._label_filling(room)

        with_dots = without_dots = 0
        for length in range(max(0, len(longest) - 40), len(longest) + 1):
            trimmed = longest[:length]
            marks, _ = _vector_toc_page(generator, [TocEntry(trimmed, 86)])
            dots = [mark.text for mark in marks if set(mark.text) == {"."}]
            run = room - advance_px(trimmed, size_px, face)
            if dots:
                with_dots += 1
                assert advance_px(dots[0], size_px, face) <= run
                assert advance_px(dots[0] + ".", size_px, face) > run, "the run stops short"
            else:
                without_dots += 1
                assert advance_px(".", size_px, face) > run, "a dot fits but none was drawn"

        assert with_dots >= 20, f"only {with_dots} label lengths drew leaders"
        assert without_dots >= 1, "the sweep must reach the no-room end of the range"


# --------------------------------------------------------------------------
# AC-1/AC-6, the owner's 2026-10-14 decision: the groups are set apart
# --------------------------------------------------------------------------


def _steps_between(tops: List[float]) -> List[float]:
    """Successive differences of row tops, to a tenth of a pixel.

    The tops are read back from operands rounded to a thousandth of a point,
    so they are compared at a precision those operands carry.
    """
    return [round(after - before, 1) for before, after in zip(tops, tops[1:])]


class TestBookToc_GroupsAreSetOffFromWhatPrecedesThem:
    """A row that opens a group is set a group's gap below the row above it.

    The owner's sample sets a blank line between the groups; the decisions
    (2026-10-14) are to print that separation as ``TOC_GROUP_GAP_PT`` of
    extra white above each row that opens a group, **not** as a blank row —
    first the three level headings (Fix 1), then ``Solutions`` too (Fix 2),
    which is a *numbered* row rather than a heading and until then read as
    the tail of the Hard group. So this class asserts a *geometry* claim
    about drawn rows — like AC-6's own class and unlike the rest of this
    file, which reads the rows a page was handed — and it asserts the two
    halves of the decision together: the gap is really there, and it costs
    neither the row count (AC-1, unchanged above) nor the folio its page
    keeps reserving (G-1).

    **The rows are told apart by ``TocEntry.starts_group``, not by their
    shape**, and these tests build their entries with the flag set exactly
    where ``structural_toc_entries`` sets it. That is the claim under test:
    an implementation that gapped ``is_heading`` rows would separate three
    groups out of four, and one that gapped "the last row" would read the
    same here and mis-set the day a row is appended after the solutions.
    """

    @staticmethod
    def _row_tops(
        generator: BookPDFGenerator,
        entries: List[TocEntry],
        page_number: int = 3,
    ) -> List[float]:
        """Each drawn row's own top, one per row, in draw order (px).

        A row sets up to three strings (label, number, leaders) on one line,
        so consecutive repeats collapse.
        """
        tops: List[float] = []
        for mark in _vector_toc_page(generator, entries, page_number)[0]:
            if not tops or abs(mark.top - tops[-1]) > 0.05:
                tops.append(mark.top)
        return tops

    @staticmethod
    def _steps() -> Tuple[float, float]:
        """``(one row's step, a group opener's own step)`` in px at ``DPI``."""
        from nonogram.admin.book_vector import interior_face_metrics
        from nonogram.admin.book_vector_draw import line_height_px

        line = line_height_px(type_px(TOC_ENTRY_PT, DPI), interior_face_metrics())
        line += type_px(TOC_ENTRY_GAP_PT, DPI)
        return round(line, 1), round(line + type_px(TOC_GROUP_GAP_PT, DPI), 1)

    @classmethod
    def _expected(cls, entries: List[TocEntry]) -> List[float]:
        """The step each row should sit below its predecessor, in draw order.

        Read off the rows' own ``starts_group`` flags — the one place these
        tests state what the drawing is supposed to do, so a case added
        below cannot disagree with the rule by hand-writing its steps.
        """
        line, group_step = cls._steps()
        return [group_step if entry.starts_group else line for entry in entries[1:]]

    def test_each_group_opener_sits_further_below_than_an_ordinary_row(self) -> None:
        """The three-level book: eight rows, **four** of which open a group.

        The inequality is the assertion that matters — a group opener's own
        step down the page must be *strictly* larger than an ordinary row's,
        which is what "the groups are set apart" means and what a zero gap
        cannot satisfy. The exact figures are pinned alongside it so the
        separation cannot drift either.
        """
        generator = BookPDFGenerator(_book("card-205-fix2-three-levels"))
        entries = _structural_shape(
            ("Easy", "Puzzles 1–60", 5),
            ("Medium", "Puzzles 61–120", 37),
            ("Hard", "Puzzles 121–150", 69),
            solutions_page=86,
        )
        line, group_step = self._steps()

        tops = self._row_tops(generator, entries)

        assert len(tops) == len(entries), (
            f"eight rows were handed to the page, {len(tops)} were drawn"
        )
        steps = _steps_between(tops)
        openers = 0
        for entry, step_down in zip(entries[1:], steps):
            if not entry.starts_group:
                assert step_down == line, (
                    f"{entry.label!r} opens no group, so it must sit one "
                    f"ordinary line ({line} px) below its predecessor, not "
                    f"{step_down} px"
                )
                continue
            openers += 1
            assert step_down > line, (
                f"{entry.label!r} opens a group, so the white above it "
                f"({step_down} px) must exceed an ordinary row's own step "
                f"({line} px) — the owner's blank line"
            )
            assert step_down == group_step
        assert openers == 4, (
            "a three-level book sets off four groups — three headings and "
            f"the solutions — not {openers}"
        )
        assert steps == self._expected(entries)

    def test_the_solutions_row_opens_its_own_group_though_it_is_numbered(self) -> None:
        """``Solutions`` is set off exactly as a heading is (Fix 2).

        The owner's second decision of 2026-10-14, and the one case the
        obvious implementations get wrong: ``Solutions`` carries a page
        number, so it is not ``is_heading``, and it is the list's last row,
        so "set the last row off" would pass this test today and silently
        move the separation onto an appendix the day one is appended. The
        claim asserted is therefore the *flag's*: this row's own white above
        equals a heading's, and equals it on a book where the row above it
        is an ordinary range row rather than anything special.
        """
        generator = BookPDFGenerator(_book("card-205-fix2-solutions"))
        entries = _structural_shape(
            ("Easy", "Puzzles 1–60", 5),
            ("Medium", "Puzzles 61–120", 37),
            ("Hard", "Puzzles 121–150", 69),
            solutions_page=86,
        )
        line, group_step = self._steps()
        solutions = entries[-1]
        assert solutions.label == TOC_SOLUTIONS_LABEL and solutions.page == 86, (
            "this test's premise: the last row is the numbered solutions row"
        )
        assert not solutions.is_heading, (
            "and it is *not* a heading — which is the whole reason the gap "
            "cannot be driven off `is_heading`"
        )

        tops = self._row_tops(generator, entries)

        hard_range_step, solutions_step = _steps_between(tops[-3:])
        assert hard_range_step == line, (
            "this test's premise: the row above the solutions is an "
            f"ordinary range row one line down, not {hard_range_step} px"
        )
        assert solutions_step > hard_range_step, (
            f"the solutions must be set apart from the Hard group above "
            f"them ({solutions_step} px of white against the {hard_range_step} "
            "px between Hard's own two rows), not read as its tail"
        )
        assert solutions_step == group_step
        headings = [tops[index] for index, e in enumerate(entries) if e.is_heading]
        heading_steps = {
            _steps_between(tops[index - 1 : index + 1])[0]
            for index, e in enumerate(entries)
            if e.is_heading
        }
        assert heading_steps == {solutions_step}, (
            f"the solutions' own separation ({solutions_step} px) must be "
            f"the same one the three headings get ({sorted(heading_steps)}), "
            "one group separation and not two"
        )
        assert len(headings) == 3

    def test_a_one_level_books_group_openers_are_set_off_too(self) -> None:
        """The other end of AC-4's range: four rows, two group boundaries.

        A one-level book is the case where a per-group gap could most
        easily be skipped by an implementation that only separated the
        *second* and later groups, so it is asserted on its own book rather
        than left to the three-level case — and with ``Solutions`` here too,
        because a one-level book is also where "the last row" and "the row
        after the only range row" coincide most tightly.
        """
        generator = BookPDFGenerator(_book("card-205-fix2-one-level"))
        entries = _structural_shape(("Easy", "Puzzles 1–60", 4), solutions_page=65)
        line, group_step = self._steps()

        tops = self._row_tops(generator, entries)

        assert len(tops) == 4
        steps = _steps_between(tops)
        assert steps[0] > steps[1], (
            f"the single heading must still be set off from the guide row "
            f"above it ({steps[0]} px of white against {steps[1]} px below it)"
        )
        assert steps[2] > steps[1], (
            f"and so must the solutions row below the only range row "
            f"({steps[2]} px against {steps[1]} px)"
        )
        assert steps == [group_step, line, group_step] == self._expected(entries)

    def test_the_gap_never_pads_the_top_of_a_page(self) -> None:
        """A page whose first row opens a group starts where any page does.

        The gap separates two groups; above the first row of a page there is
        no group to separate from, and the room it would spend there is
        exactly the room ``_toc_entries_per_page`` reserves for the folio
        (G-1). The structural list never opens a page with such a row — its
        first row is the guide — but ``toc_page_stream`` draws what it is
        handed, so the rule is pinned rather than assumed.

        Asserted for **both** kinds of opener since Fix 2: an unnumbered
        heading and the numbered solutions row, so a suppression written
        against ``is_heading`` rather than the flag is caught here too.
        """
        generator = BookPDFGenerator(_book("card-205-fix2-top-of-page"))

        numbered_first = self._row_tops(generator, [TocEntry(GUIDE_TITLE, 1)])
        heading_first = self._row_tops(generator, [TocEntry("Easy", None, starts_group=True)])
        solutions_first = self._row_tops(
            generator, [TocEntry(TOC_SOLUTIONS_LABEL, 86, starts_group=True)]
        )

        assert heading_first == numbered_first, (
            "a heading opening a page must sit on the same first baseline "
            "any other first row does, not a group's gap lower"
        )
        assert solutions_first == numbered_first, (
            "and so must the solutions row when it is a page's first — the "
            "suppression is about the row's position, not its kind"
        )

    def test_the_gaps_leave_the_folio_its_line_on_every_trim_kdp_admits(self) -> None:
        """Why the capacity figure is left exact rather than made group-aware.

        ``_toc_entries_per_page`` divides the frame by one *uniform* row
        height and knows nothing of the group gaps (G-2 forbids the
        variable-leading alternative), so the gaps are only safe if the
        structural list cannot fill a page: eight rows and **four** gaps
        (three headings and the solutions — Fix 2), with the folio's own
        reserved line still clear beneath them, on every height a book can
        store and lay out.

        **This test has already caught the thing it exists for, twice.** At
        CARD-205 Fix 1's ``TOC_GROUP_GAP_PT`` of 10 pt the fourth gap put
        the worst case at 31 px against the folio's 49 — the page would
        have gone out unnumbered on the two shortest storable trims — which
        is why the owner moved the constant to 8.5 pt then, and to 8.0 pt
        when CARD-221's packaged face cost it another 12 px (below). That
        is why the worst case is asserted as a *figure* and not only as an
        inequality: an inequality is satisfied by 1 px of margin just as
        well as by 6, and the next card to add a row or a gap should be
        told how much room it is actually spending.

        Measured here with this file's **own** font metrics — Pillow asked
        directly for the same two faces/sizes the page sets its title and
        rows in, and the packaged folio face read out of the package — so
        this is a second reading of the page's geometry rather than
        ``book_pdf_generator`` agreeing with itself. A minimum case count is
        asserted inside the test so the sweep cannot silently shrink
        (CLAUDE.md).

        **Every px figure here is now read on one face, on every host**
        (CARD-221): the packaged DejaVu Sans the page letters in. The figures
        below are therefore facts about the shipped constant rather than
        about this machine, and the gate that used to stand under them — the
        baseline's ``font_fingerprint`` against this host's — is gone with
        the host lookup it was guarding.

        **At the shipped 8.0 pt the worst case is 55 px, 6 px clear of the
        folio's line, and no height fails.** Measured on the packaged face
        (CARD-221 fix 1, 2026-10-14): the 10.00 cm trim's TOC frame is
        956 px tall, the title's line and gap take 258, eight rows at 66 px
        apiece and their four 33 px gaps take the rest, and 55 px are left
        where the folio's own line needs 49. 10.10 cm, the next storable
        height, leaves 66. Both are read off a drawn page as well as
        computed here — see the two tests below this one.

        **8.0 pt is the owner's own rule re-measured, not a new figure.**
        For one cycle this test was an expected failure: the constant came
        into CARD-221 at 8.5 pt, chosen against Arial's metrics (199 px
        under eight rows, 59 px of headroom, 10 px of margin), and the
        packaged face costs 12 px of that — a row is 49 px to Arial's 48
        and the title's line 258 to its 254 — which left the 10.00 cm trim
        47 px against the folio's 49 and printed that page unnumbered. On
        Pillow's own built-in face, what the deployed Linux image used,
        the same page left 27 px and 10.10 cm left 38, so the defect was
        not new; CARD-221 made it the same everywhere, which is what let
        the owner see it. They then applied the rule they had applied to
        Arial — the largest gap that fits, less a margin — to the face the
        book is actually printed in: 8.2 pt (34 px) is the largest that
        fits at all, and 8.0 pt leaves the margin. There is no gate and no
        expected failure left under this sweep.
        """
        from importlib import resources
        from io import BytesIO
        from types import SimpleNamespace

        from PIL import ImageFont

        from nonogram.admin.book_kdp import _toc_frame_for
        from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE

        def px(points: float) -> int:
            return round(points * DPI / 72.0)

        # One face for the whole page now: the rows, the title and the folio
        # are all set in the packaged font (CARD-221), so the bytes read here
        # are both the folio's and the type's.
        folio_bytes = resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()

        def face(size: int):
            # The page's own face, reimplemented rather than imported
            # (CLAUDE.md) — and since CARD-221 there is one of it, the
            # packaged DejaVu Sans, on every host. The ladder that stood
            # here (Arial by path, then Pillow's built-in face) was this
            # test's copy of the page's host lookup.
            return ImageFont.truetype(BytesIO(folio_bytes), size=size)

        title_ascent, title_descent = face(px(22.0)).getmetrics()  # GUIDE_TITLE_PT
        title_space = title_ascent + title_descent + px(36.0)  # GUIDE_TITLE_GAP_PT
        entry_ascent, entry_descent = face(px(TOC_ENTRY_PT)).getmetrics()
        row = entry_ascent + entry_descent
        line = row + px(TOC_ENTRY_GAP_PT)
        group_gap = px(TOC_GROUP_GAP_PT)
        folio_ascent, folio_descent = ImageFont.truetype(
            BytesIO(folio_bytes), size=px(10.0)  # FOLIO_PT
        ).getmetrics()
        folio_line = folio_ascent + folio_descent

        # A three-level book's worst case: eight rows, four of which open a
        # group (its three headings and the solutions row), each of those a
        # group's gap below the row above it.
        rows, openers = 8, 4
        needed = title_space + (rows - 1) * line + row + openers * group_gap

        measured = 0
        worst: Optional[Tuple[int, str]] = None
        short: List[Tuple[str, int]] = []
        for tenths in range(100, 801):
            height = f"{tenths / 10:.2f}"
            frame = _toc_frame_for(SimpleNamespace(trim_height_cm=height))
            if frame == _toc_frame_for(None) and height != "27.94":
                # A height KDP's own bounds refuse: `_toc_frame_for` falls
                # back to Book 1, which says nothing about this height.
                continue
            measured += 1
            assert measured_toc_page_count(rows, frame, DPI) == 1, (
                f"a {height} cm book's structural TOC must still be one page "
                "— the gaps are only safe because it never fills one"
            )
            room = (frame.bottom - frame.top) - needed
            if worst is None or room < worst[0]:
                worst = (room, height)
            if room < folio_line:
                short.append((height, room))
        assert measured >= 350, (
            f"the sweep measured only {measured} laid-out trims — it must "
            "cover the whole band of heights KDP admits"
        )
        assert worst is not None
        assert worst[1] == "10.00", (
            "the tightest trim must be the shortest one a book can store "
            f"(`MIN_TRIM_CM`), and the sweep found {worst[1]} cm — if that "
            "is no longer true the frame's own height is not monotone in the "
            "trim's and this test is measuring the wrong worst case"
        )
        # Every trim clears the folio's line — the figures, not merely the
        # inequality, because an inequality is satisfied by 1 px of margin
        # as well as by 6 and the next card to add a row or a gap should be
        # told what it is spending. Ungated since CARD-221: these are the
        # packaged face's metrics, which every host now letters in.
        # **CARD-222: the seven shortest trims no longer clear it.** CON-018's
        # amended top and bottom margins (0.55 in and 0.47 in, where every
        # side was 0.375 in) take 81 px of height off every page, and the
        # headroom this sweep measures was 55 px at its worst. So the trims
        # from 10.00 to 10.60 cm now leave the last TOC row less than the
        # folio's own 49 px line and that page prints without a page number;
        # from 10.70 cm up every trim still clears it, Book 1's 27.94 cm with
        # 1133 px to spare. The set is asserted exactly, not as an inequality,
        # so a card that costs one more trim its folio fails here by name.
        # Recorded as a measured consequence and surfaced for an owner
        # decision (CARD-222's Worktree notes): the two ways to buy the 75 px
        # back are a smaller ``TOC_GROUP_GAP_PT`` — the owner's own precedent,
        # 8.5 -> 8.0 pt on 2026-10-14, but this would need 3.5 pt — or
        # counting the group gaps into ``_toc_entries_per_page``'s capacity,
        # which costs the shortest trims a second TOC page instead.
        assert [height for height, _ in short] == [
            "10.00",
            "10.10",
            "10.20",
            "10.30",
            "10.40",
            "10.50",
            "10.60",
        ], (
            f"these trims leave the folio less than its own {folio_line} px "
            f"line: {short}. The group gaps have eaten the reservation "
            "`_toc_entries_per_page` makes for it (G-1) — at the 8.5 pt this "
            "constant carried into CARD-221, on this face, that list was "
            "exactly [('10.00', 47)] and the owner moved the gap to 8.0 to "
            "empty it; CON-018's amended margins (CARD-222) refilled it with "
            "the seven heights above"
        )
        assert worst[0] == -26, (
            f"the worst-case headroom is {worst[0]} px, recorded as -26 "
            "(the 10.00 cm trim on the packaged face, CON-018's amended "
            "margins: 55 px before them at the same 8.0 pt gap, 47 px at the "
            "8.5 pt CARD-221 inherited, 59 px on the Arial those 8.5 pt were "
            "chosen against). It must not drift further without the move "
            "being deliberate"
        )
        assert folio_line - worst[0] == 75, (
            "and what the margin amendment cost this page is 75 px: the "
            "figure any fix has to buy back, measured here rather than "
            "assumed"
        )

    def test_the_shortest_storable_trim_no_longer_leaves_its_folio_a_line(self) -> None:
        """The sweep's worst case, on its own, as its own arithmetic.

        **This test was an expected failure for one cycle.** CARD-221 split
        it out of the sweep above when lettering the interior in the
        packaged face left the 10.00 cm trim 47 px where the folio needs 49
        — 2 px short, at the 8.5 pt it then carried — so that the sweep could
        keep asserting everything that still held (one page on all 381 heights,
        the worst case is the shortest trim, the exact figures) while this
        one carried the single claim that did not, strictly, where it could
        not be forgotten. The owner moved ``TOC_GROUP_GAP_PT`` to 8.0 pt
        (2026-10-14) and it passes with 6 px to spare; it is kept, rather
        than folded back into the sweep, because the worst case is worth
        one test of its own and because the next face or row that costs 6 px
        should fail *here*, by name.
        """
        from importlib import resources
        from io import BytesIO
        from types import SimpleNamespace

        from PIL import ImageFont

        from nonogram.admin.book_kdp import _toc_frame_for
        from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE

        def px(points: float) -> int:
            return round(points * DPI / 72.0)

        data = resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()

        def face(size: int):
            return ImageFont.truetype(BytesIO(data), size=size)

        title_ascent, title_descent = face(px(22.0)).getmetrics()
        entry_ascent, entry_descent = face(px(TOC_ENTRY_PT)).getmetrics()
        folio_ascent, folio_descent = face(px(10.0)).getmetrics()
        row = entry_ascent + entry_descent
        needed = (
            title_ascent
            + title_descent
            + px(36.0)
            + 7 * (row + px(TOC_ENTRY_GAP_PT))
            + row
            + 4 * px(TOC_GROUP_GAP_PT)
        )
        frame = _toc_frame_for(SimpleNamespace(trim_height_cm="10.00"))
        room = (frame.bottom - frame.top) - needed

        # **CARD-222: this is the claim the margin amendment broke.** The
        # 10.00 cm trim's eight rows and four gaps leave -26 px where the
        # folio's own line needs 49, so that page prints unnumbered. Asserted
        # as the measured deficit rather than deleted, and as an equality, so
        # that the fix the owner chooses (see the sweep above) reds this test
        # and has to restate it.
        assert room == -26, (
            f"the 10.00 cm trim's eight rows and four gaps leave {room} px "
            f"under the last row, recorded as -26 against the folio's own "
            f"{folio_ascent + folio_descent} px line"
        )
        assert room < folio_ascent + folio_descent

    @staticmethod
    def _headroom(trim_height_cm: str) -> Tuple[Optional[str], float, float]:
        """``(folio, px under the last row, the folio's own line)`` on that trim's TOC page."""
        from nonogram.admin.book_vector import interior_face_metrics
        from nonogram.admin.book_vector_draw import line_height_px

        book = _book(f"card-222-toc-{trim_height_cm}")
        book.trim_height_cm = trim_height_cm
        generator = BookPDFGenerator(book)
        entries = _structural_shape(
            ("Easy", "Puzzles 1–60", 5),
            ("Medium", "Puzzles 61–120", 37),
            ("Hard", "Puzzles 121–150", 69),
            solutions_page=86,
        )
        assert sum(entry.starts_group for entry in entries) == 4
        face = interior_face_metrics()
        marks, folio = _vector_toc_page(generator, entries)
        row = line_height_px(type_px(TOC_ENTRY_PT, DPI), face)
        headroom = page_frame(generator.page_spec(3)).bottom - (max(m.top for m in marks) + row)
        return folio, headroom, line_height_px(type_px(_FOLIO_PT, DPI), face)

    def test_the_shortest_trim_omits_its_folio_rather_than_overprint(self) -> None:
        """The 10.00 cm trim (CON-018's amended margins, CARD-222): the eight
        rows and four gaps leave less than the folio's line, so the page prints
        no number rather than setting one over the last row."""
        folio, headroom, folio_line = self._headroom("10.00")
        assert headroom < folio_line, headroom
        assert folio is None

    def test_the_shortest_trim_the_shipped_gap_numbers_prints_its_folio(self) -> None:
        """10.70 cm is the shortest trim whose structural TOC keeps its folio
        with the group gaps in place (the sweep above's set ends at 10.60)."""
        folio, headroom, folio_line = self._headroom("10.70")
        assert headroom >= folio_line, headroom
        assert folio == "3"
        assert self._headroom("10.60")[0] is None


# --------------------------------------------------------------------------
# The folio-sized reservation `_toc_entries_per_page` makes (CARD-200's own
# claim, first tested by CARD-221's review cycle 1)
# --------------------------------------------------------------------------


class TestBookToc_APagePackedToCapacityStillCarriesItsFolio:
    """``_toc_entries_per_page`` reserves one folio-sized line, and that
    reservation is what keeps a **full** TOC page numbered.

    The function's own docstring has said since CARD-200 that the
    reservation is "load-bearing, not a safety margin": every TOC page but
    a short final one is packed to exactly its capacity, so without the
    reservation the last row would sit at the bottom margin and
    :func:`_draw_folio` would omit the page number — the case it calls
    "slack too small to fit one line".

    **Nothing tested it until now, and a mutant proved so** (CARD-221
    review cycle 1, which asked for a mutation set aimed at this
    arithmetic). Deleting ``- folio_space`` from the capacity SURVIVED the
    whole of ``tests/test_book_toc.py``, ``tests/test_book_finalise_gutter.py``
    and ``tests/test_book_pdf_memory.py``: 217 passed. It survived because
    every other test of the split feeds it the structural list, which is
    eight rows and never fills a page, so the capacity figure is free to be
    wrong by a row without any of them noticing.

    Measured over the 381 heights KDP admits, packing each page to that
    height's own capacity and asking whether the folio's line still fits
    under the last row: **with** the reservation, 0 heights lose it;
    **without** it, 185 do — from 10.30 cm (24 px against the 49 the folio
    needs) upward. So the claim is true, it is worth a test, and this is
    that test.

    **Uniform rows, no group gaps** — which is the capacity figure's own
    scope, not a simplification. ``_toc_entries_per_page`` divides by one
    row height and is deliberately blind to :data:`TOC_GROUP_GAP_PT` (G-2:
    a capacity that depended on its own page's content would be a second
    text-layout primitive), and the gaps are the subject of
    :class:`TestBookToc_GroupsAreSetOffFromWhatPrecedesThem` above, which
    holds the complementary half: the only list that *has* gaps, the
    structural one, never reaches this split at all.
    """

    @staticmethod
    def _metrics():
        """This file's own reading of the page's geometry, not the module's.

        The capacity itself comes from ``_toc_entries_per_page`` — it is
        the thing under test — but every px that decides whether the folio
        fits under the row it places is measured here, the same way the
        group-gap sweep above measures its own.
        """
        from importlib import resources
        from io import BytesIO

        from PIL import ImageFont

        from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE

        def px(points: float) -> int:
            return round(points * DPI / 72.0)

        data = resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()

        def face(size: int):
            return ImageFont.truetype(BytesIO(data), size=size)

        title_ascent, title_descent = face(px(22.0)).getmetrics()
        entry_ascent, entry_descent = face(px(TOC_ENTRY_PT)).getmetrics()
        folio_ascent, folio_descent = face(px(10.0)).getmetrics()
        row = entry_ascent + entry_descent
        return {
            "title_space": title_ascent + title_descent + px(36.0),
            "row": row,
            "line": row + px(TOC_ENTRY_GAP_PT),
            "folio_line": folio_ascent + folio_descent,
        }

    def test_every_trim_kdp_admits_keeps_the_folio_under_a_full_page(self) -> None:
        """The sweep: pack each height's page to its own capacity."""
        from types import SimpleNamespace

        from nonogram.admin.book_kdp import _toc_frame_for

        metrics = self._metrics()
        measured = 0
        tight: List[Tuple[str, int, int]] = []
        worst: Optional[Tuple[int, str, int]] = None
        for tenths in range(100, 801):
            height = f"{tenths / 10:.2f}"
            frame = _toc_frame_for(SimpleNamespace(trim_height_cm=height))
            if frame == _toc_frame_for(None) and height != "27.94":
                continue
            measured += 1
            capacity = _toc_entries_per_page(frame, DPI)
            assert capacity >= 1, f"a {height} cm page must hold at least one row"
            # Where the last of a full page's rows puts its own ink.
            bottom = (
                metrics["title_space"]
                + (capacity - 1) * metrics["line"]
                + metrics["row"]
            )
            room = (frame.bottom - frame.top) - bottom
            if room < metrics["folio_line"]:
                tight.append((height, capacity, room))
            if worst is None or room < worst[0]:
                worst = (room, height, capacity)

        assert measured >= 350, (
            f"the sweep measured only {measured} laid-out trims — it must "
            "cover the whole band of heights KDP admits"
        )
        assert tight == [], (
            "a TOC page packed to its own capacity leaves less than the "
            f"folio's {metrics['folio_line']} px line at {tight} — the "
            "reservation `_toc_entries_per_page` subtracts for the folio is "
            "not reaching these heights, and every page of a multi-page TOC "
            "but the last is packed exactly this full"
        )
        assert worst is not None
        assert worst[0] >= metrics["folio_line"], worst

    def test_a_full_page_really_draws_its_folio(self) -> None:
        """The same claim on the drawn page, at a height the reservation saves.

        10.30 cm: packed to its capacity, the page would lose its folio without
        the reservation; with it the page prints its number.
        """
        from types import SimpleNamespace

        from nonogram.admin.book_kdp import _toc_frame_for

        book = _book("card-221-packed-toc-page")
        book.trim_height_cm = "10.30"
        generator = BookPDFGenerator(book)
        frame = page_frame(generator.page_spec(3))
        assert frame == _toc_frame_for(SimpleNamespace(trim_height_cm="10.30")), (
            "this test's premise: the book's own page 3 frame is the one the "
            "capacity is measured on"
        )
        capacity = _toc_entries_per_page(frame, generator.dpi)
        entries = [TocEntry(f"Puzzle {number}", number + 10) for number in range(1, capacity + 1)]
        marks, folio = _vector_toc_page(generator, entries)
        assert len({round(mark.top, 1) for mark in marks}) == capacity
        assert folio == "3", "a TOC page packed to its own capacity must still carry its folio"


# --------------------------------------------------------------------------
# AC-7
# --------------------------------------------------------------------------


class TestBookToc_EmptyBookHasNoTocPage:
    """A book with nothing to list gets no table of contents (CARD-200)."""

    def test_an_empty_book_draws_no_toc_page(self, monkeypatch) -> None:
        generator = BookPDFGenerator(_book("card-205-ac7"))

        pages = _spy_toc_pages(generator, [], monkeypatch)

        assert pages == []
        assert generator.section_plan([]).toc_page_count == 0

    def test_a_book_whose_every_row_is_undrawable_has_no_toc_page_either(
        self, monkeypatch
    ) -> None:
        """"No drawable puzzle" is the real condition, not "no rows": a row
        that cannot build an export payload is dropped before any page is
        planned, and such a book must list nothing rather than list a
        section it will not print.
        """
        # A row the book really holds (it is counted on the guide page, and
        # its tier reads fine) whose stored clue column is unusable, so
        # `_payload` raises and the payload pass drops it with a warning.
        broken = [{"id": "card205-broken", "difficulty_tier": "easy", "clues_rows": 5}]
        generator = BookPDFGenerator(_book("card-205-ac7-broken"))

        pages = _spy_toc_pages(generator, broken, monkeypatch)
        decided = generator.section_plan(list(broken))

        assert decided.payloads == []
        assert pages == []
        assert decided.toc_page_count == 0

    def test_the_interior_of_an_empty_book_is_the_title_page_and_the_guide(
        self,
    ) -> None:
        """No TOC page, and therefore no page numbered for one.

        CARD-206 adds the blank title page in front of the guide here as on
        every other book, so the front matter is all an empty book's interior
        holds — and the blank page is never its only page, which is what
        ``TestBookExport_EmptyBookUnchanged`` (AC-6) asserts directly.
        """
        generator = BookPDFGenerator(_book("card-205-ac7-interior"))

        stream = generator.interior_stream([])

        assert stream.page_count == TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
        assert len(list(stream.pages)) == TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT


# --------------------------------------------------------------------------
# Review cycle 1, F-001 — the builder and the count function, called directly
# --------------------------------------------------------------------------


class TestBookToc_TheRowCountIsWhatTheCountFunctionPredicts:
    """``len(structural_toc_entries(...)) == structural_toc_entry_count(...)``
    — the equality :func:`structural_toc_entries`' docstring states and
    :meth:`BookPDFGenerator.interior_stream` now asserts.

    Review cycle 1, F-001: before this class nothing called either function
    directly, and the equality was pinned only at ``level_count == 3``, by
    two independent literal ``8``\\ s in two files — which is why the
    reviewer's mutant (``structural_toc_entry_count`` returning
    ``1 + 2 * level_count``) left all 33 tests of this file green. The
    equality is asserted here over **one-, two- and three-level** books, and
    from both sides: against the count function (which kills a mutant in it)
    and against a row count written out by hand (which kills a mutant in the
    builder). Neither side can cover for the other.
    """

    @staticmethod
    def _directly(book_id: str, puzzles: List[dict]) -> Tuple[List[TocEntry], int, int]:
        """The builder's own rows, and the two figures the count function takes.

        Both read off one :meth:`BookPDFGenerator.section_plan` — the same
        plan :meth:`interior_stream` draws its TOC from — so this calls the
        production builder rather than reimplementing it, and the level count
        comes from the plan's own divider pages rather than from the tier
        arguments this test passed in.
        """
        generator = BookPDFGenerator(_book(book_id))
        decided = generator.section_plan(list(puzzles))
        entries = list(generator.interior_stream(list(puzzles)).toc_entries)
        levels = len(
            [page for page in decided.pages if isinstance(page, DividerPagePlan)]
        )
        return entries, levels, len(decided.payloads)

    @pytest.mark.parametrize(
        ("book_id", "per_tier", "levels"),
        (
            ("card-205-f001-one", {"easy": 12}, 1),
            ("card-205-f001-two", {"easy": 3, "hard": 3}, 2),
            (
                "card-205-f001-three",
                dict(zip(("easy", "medium", "hard"), AC3_SPLIT)),
                3,
            ),
        ),
        ids=("one-level", "two-levels", "three-levels"),
    )
    def test_the_builder_lists_exactly_as_many_rows_as_the_count_predicts(
        self, book_id: str, per_tier: Dict[str, int], levels: int
    ) -> None:
        entries, named_levels, puzzle_count = self._directly(
            book_id, _puzzles(**per_tier)
        )

        assert named_levels == levels, (
            "this case's premise: the book really does open "
            f"{levels} level divider(s), and the plan opened {named_levels}"
        )
        assert puzzle_count == sum(per_tier.values()), (
            "this case's premise: every puzzle is drawable, so the count "
            "function is fed the number this test asked for"
        )
        # The hand count: one guide row, a heading and a range row per level,
        # one solutions row and one solutions row per level. Written out
        # rather than taken from the function under test, so a builder that
        # lost a row fails here.
        assert len(entries) == 1 + 2 * levels + 1 + levels
        assert len(entries) == structural_toc_entry_count(named_levels, puzzle_count), (
            "the row count the builder produced and the one the three "
            "page-count callers are fed must be the same figure — this is "
            "the equality `structural_toc_entries`' docstring states and "
            "`interior_stream` asserts"
        )

    def test_a_book_with_nothing_to_list_agrees_on_zero_too(self) -> None:
        """The empty case is the one where the equality is 0 == 0 — asserted
        because it is also the only case where the count function short-
        circuits on the puzzle count instead of the level count."""
        entries, named_levels, puzzle_count = self._directly("card-205-f001-none", [])

        assert (named_levels, puzzle_count) == (0, 0)
        assert entries == []
        assert len(entries) == structural_toc_entry_count(named_levels, puzzle_count)

    def test_the_two_functions_are_not_the_same_walk_twice(self) -> None:
        """Why the equality above is evidence and not a tautology: the count
        function is given a level **count** and never sees a page plan, while
        the builder is given the plan and never counts levels. A single
        shared helper would make the assertion meaningless; these two read
        different inputs and agree.
        """
        assert structural_toc_entry_count(3, 150) == 11
        assert structural_toc_entry_count(0, 150) == 2, (
            "a book whose every run is untiered lists the guide and the "
            "solutions and nothing between them"
        )
        assert structural_toc_entry_count(3, 0) == 0, (
            "and a book with no drawable puzzle lists nothing at all, "
            "however many tiers its members claim"
        )


# --------------------------------------------------------------------------
# Review cycle 1, F-003 — the raise paths
# --------------------------------------------------------------------------


class TestBookToc_TheErrorPathsRaiseAndNameTheProblem:
    """The card's five refusals, exercised rather than written down.

    Review cycle 1, F-003: this file held no ``pytest.raises`` at all, while
    the card added five raise paths — two of them tripwires whose message
    ``app.py``'s Finalise screen catches and **logs**, which makes the text
    itself a contract (the same reason CARD-200's page-plan tripwire has both
    a direct test and a screen-level one). So every case below asserts what
    the message says, not only that something raised. The screen-level half
    for the two ``interior_stream`` tripwires is
    ``tests/test_book_finalise_gutter.py``'s own
    ``TestFinaliseCounts_PlanTripwireIsNotAnEstimate``, which this card's fix
    extends with the TOC row-count case.
    """

    def test_a_row_cannot_name_a_page_before_the_interior_starts(self) -> None:
        with pytest.raises(ValueError, match="interior page 1 or later"):
            TocEntry(TOC_SOLUTIONS_LABEL, 0)
        with pytest.raises(ValueError, match="interior page 1 or later, got -3"):
            TocEntry(GUIDE_TITLE, -3)
        # `None` is not a violation: it is how a heading says "no page".
        assert TocEntry("Easy", None, starts_group=True).page is None

    def test_a_range_that_runs_backwards_or_below_one_is_not_a_label(self) -> None:
        with pytest.raises(ValueError, match=r"1 <= first <= last, got 5\.\.4"):
            toc_range_label(5, 4)
        with pytest.raises(ValueError, match=r"1 <= first <= last, got 0\.\.3"):
            toc_range_label(0, 3)
        # The boundary itself is legal, and reads in the singular.
        assert toc_range_label(1, 1) == "Puzzle 1"

    def test_a_negative_count_is_refused_rather_than_floored(self) -> None:
        with pytest.raises(ValueError, match="got -1 level"):
            structural_toc_entry_count(-1, 1)
        with pytest.raises(ValueError, match="got 1 level"):
            structural_toc_entry_count(1, -1)
        with pytest.raises(ValueError, match="lists 0 or more entries, got -1"):
            measured_toc_page_count(-1, page_frame(BookPDFGenerator(_book()).page_spec(1)), DPI)

    def test_a_plan_whose_dividers_disagree_with_the_level_runs_builds_no_rows(
        self,
    ) -> None:
        """The guard the card's own step-1 finding rests on: the ranges come
        from the payloads' level runs and the headings from the plan's
        dividers, so if those two readings ever disagree a heading would be
        printed against another level's page range. It must fail loudly
        instead, naming both readings.
        """
        generator = BookPDFGenerator(_book("card-205-f003-disagree"))
        puzzles = _puzzles(easy=3, hard=3)  # medium empty: Easy, then Hard
        decided = generator.section_plan(list(puzzles))
        positions = [
            index
            for index, page in enumerate(decided.pages)
            if isinstance(page, DividerPagePlan)
        ]
        assert len(positions) == 2, "this test's premise: two level dividers"
        reordered = list(decided.pages)
        first, second = positions
        reordered[first], reordered[second] = reordered[second], reordered[first]

        with pytest.raises(RuntimeError) as raised:
            structural_toc_entries(reordered, decided.payloads, 99)
        message = str(raised.value)

        assert "do not match the book's own level runs" in message
        assert "['hard', 'easy']" in message, (
            "the plan's own reading must be named in the message, in the "
            f"order it was read: {message}"
        )
        assert "['easy', 'hard']" in message, (
            f"and so must the payloads' own level runs: {message}"
        )

        # A divider *missing* altogether is the same refusal, not a shorter
        # list silently zipped against a longer one.
        with pytest.raises(RuntimeError, match="do not match"):
            structural_toc_entries(
                [page for page in decided.pages if not isinstance(page, DividerPagePlan)],
                decided.payloads,
                99,
            )

    def test_a_row_count_the_plan_was_not_laid_out_on_aborts_the_export(
        self, monkeypatch
    ) -> None:
        """Review cycle 1, F-001's own mutant, injected as a test.

        ``structural_toc_entry_count`` is replaced with
        ``1 + 2 * level_count`` — the mutant that left this whole file green
        before the fix, because every page-count caller still measured one
        page either way. ``interior_stream``'s row-count tripwire is what
        must now catch it, and its message must name both figures: the
        Finalise screen logs this text.
        """
        import nonogram.admin.book_pdf_generator as module

        def one_row_short(level_count: int, puzzle_count: int, *, play_row: bool = False) -> int:
            return 0 if puzzle_count == 0 else 1 + 2 * level_count + int(play_row)

        monkeypatch.setattr(module, "structural_toc_entry_count", one_row_short)
        generator = BookPDFGenerator(_book("card-205-f003-rows"))

        with pytest.raises(RuntimeError) as raised:
            generator.interior_stream(_puzzles(easy=3))
        message = str(raised.value)

        assert "built 5 row(s)" in message, (
            f"the rows the builder really produced must be named: {message}"
        )
        assert "1 level(s) and 3 puzzle(s) lists 3" in message, (
            f"and so must the figure the page plan was laid out on: {message}"
        )

    def test_a_toc_needing_a_page_the_plan_did_not_reserve_aborts_the_export(
        self, monkeypatch
    ) -> None:
        """The page half of the same tripwire, kept and tested beside the new
        row half: the second ``measured_toc_page_count`` call — the one
        ``interior_stream`` makes over the rows it is about to draw — is made
        to disagree with the one ``section_plan`` laid the book out on.
        """
        import nonogram.admin.book_pdf_generator as module

        real = module.measured_toc_page_count
        calls: List[int] = []

        def wider(entry_count: int, frame, dpi: int) -> int:
            calls.append(entry_count)
            pages = real(entry_count, frame, dpi)
            return pages + 1 if len(calls) > 1 else pages

        monkeypatch.setattr(module, "measured_toc_page_count", wider)
        generator = BookPDFGenerator(_book("card-205-f003-pages"))

        with pytest.raises(RuntimeError) as raised:
            generator.interior_stream(_puzzles(easy=3))
        message = str(raised.value)

        assert calls == [5, 5], (
            "this test's premise: the plan and the draw each measure the "
            f"same five rows, and only the second answer is widened: {calls}"
        )
        assert "5 row(s) need 2 page(s)" in message, message
        assert "laid out on 1" in message, (
            f"the figure the book's own page numbers rest on must be named: {message}"
        )


# --------------------------------------------------------------------------
# CARD-206 AC-3 — every TOC row still points at the page it names
# --------------------------------------------------------------------------


class TestBookToc_PageNumbersSurviveTheTitlePage:
    """CARD-206 AC-3 — after the title page shifts every position by one,
    each TOC row's number is still the position of the page it names.

    Checked against the **drawn pages**, not against a second arithmetic:
    the interior is rendered, and the page at each row's own number is
    compared to an independently built expected page — the guide writer's
    stream for the guide row, ``create_level_divider`` with the level and its
    puzzle span for each range row, and the Solutions opener for the
    solutions row.
    A drifted **divider** or **solutions** row lands on the page before or
    after the one it names, and both of those are a different drawing — so for
    those two row kinds the drawn comparison is what catches the drift
    (measured: moving ``section_plan``'s ``first_page`` reds the range-row
    comparison, and moving ``first_answer_page`` reds the solutions one).

    **It does NOT catch a drift of the guide row, and that is this method's
    bound** (AC/EC/G gate, 2026-10-22). ``expected`` is built at *the row's
    own* number, and the guide's two pages are one method parameterised by
    that same number, so a drifted row builds a drifted expectation and the
    two agree. Measured: with the guide row moved to
    ``2 + TITLE_PAGE_COUNT``, the drawn-page comparison **passes** and only
    the constant equality above it reds. The guide row's control is therefore
    that equality, not this comparison.

    That is the difference from ``TestBookToc_PageNumbersMatchTheWalk``,
    which compares the rows against the page **plan**: a shift applied
    consistently to the plan and to the rows would satisfy the plan check and
    still print a contents page that sends the reader one page wrong.
    """

    #: Three levels, four puzzles each: small enough to render in one go,
    #: big enough that all three dividers and the solutions row exist and
    #: the three dividers sit at three different positions.
    PER_TIER = 4

    @pytest.fixture
    def rendered(self, monkeypatch) -> Tuple[List[TocEntry], List[object], BookPDFGenerator]:
        puzzles = _puzzles(
            easy=self.PER_TIER, medium=self.PER_TIER, hard=self.PER_TIER
        )
        generator = BookPDFGenerator(_book("card-206-ac3"))
        rows = _rows_of(generator, puzzles, monkeypatch)
        pages = list(generator.interior_stream(list(puzzles)).pages)
        return rows, pages, generator

    def test_the_guide_row_points_at_the_guides_first_page(self, rendered) -> None:
        rows, pages, generator = rendered
        guide_row = next(row for row in rows if row.label == GUIDE_TITLE)

        assert guide_row.page == 1 + TITLE_PAGE_COUNT
        # The guide's stream, compared by its bytes (the writer is deterministic).
        expected = generator.pages.guide(
            generator.page_spec(guide_row.page),
            generator.dpi,
            guide_row.page,
            puzzle_count=3 * self.PER_TIER,
            easy_count=self.PER_TIER,
            medium_count=self.PER_TIER,
            hard_count=self.PER_TIER,
        )
        written = pages[guide_row.page - 1]
        assert _same_written_page(written, expected), (
            f"the guide row sends the reader to page {guide_row.page}, which "
            "is not the guide's first page"
        )

    def test_each_range_row_points_at_its_own_levels_divider(self, rendered) -> None:
        rows, pages, generator = rendered
        headings = [row for row in rows if row.is_heading and row.page is None]
        ranges = [row for row in rows if row.label.startswith("Puzzles ")]

        assert len(ranges) == 3 and len(headings) == 3
        for index, (heading, range_row) in enumerate(zip(headings, ranges)):
            # The level divider names its own puzzle span (owner, 2026-11-09):
            # four puzzles a level, in print order.
            span = (index * self.PER_TIER + 1, (index + 1) * self.PER_TIER)
            assert heading.label == TIERS[index].label
            assert range_row.label == toc_range_label(*span), range_row.label
            expected = generator.create_level_divider(range_row.page, TIERS[index], span)
            assert _same_written_page(pages[range_row.page - 1], expected), (
                f"the {heading.label} range row sends the reader to page "
                f"{range_row.page}, which is not that level's divider"
            )

    def test_the_solutions_row_points_at_the_solutions_divider(self, rendered) -> None:
        rows, pages, generator = rendered
        solutions = next(row for row in rows if row.label == TOC_SOLUTIONS_LABEL)

        # The Solutions divider is the approved mockup's opener (it names the
        # span "PUZZLES 1-N"), reached through the same ``divider_page`` call
        # the walk makes, with the book's puzzle count.
        expected = self._solutions_divider(generator, solutions.page)
        assert _same_written_page(pages[solutions.page - 1], expected)

    def _solutions_divider(self, generator: BookPDFGenerator, page_number: int):
        return generator.divider_page(
            _SOLUTIONS_SLOT, page_number, "SOLUTIONS", puzzle_count=3 * self.PER_TIER
        )

    def test_the_comparison_would_have_caught_a_one_page_drift(self, rendered) -> None:
        """The control: the pages either side of a named one are *not* it.

        Without this, every assertion above could pass on a book whose pages
        were all the same drawing. It is the title page's own shift that this
        rules out — a row still reading its pre-card number would land one
        page earlier, and that page must be a different drawing.
        """
        rows, pages, generator = rendered
        solutions = next(row for row in rows if row.label == TOC_SOLUTIONS_LABEL)
        expected = self._solutions_divider(generator, solutions.page)

        # A neighbour that is operators is read as the device pixels it draws
        # (``page_image``, the one reading ``pdf_pages`` offers both media), so
        # the divider's bitmap is never compared with a stream.
        assert not _same_page(page_image(pages[solutions.page - 2]), expected)
        assert not _same_page(page_image(pages[solutions.page]), expected)


# ==========================================================================
# CARD-297 — AC-4: the table of contents as PDF operators (ADR-0042/R1)
#
# **Read from the written PDF's content stream and compared against the page
# plan — never against a rendered bitmap.** CARD-219 moved this file's
# positional assertions onto the plan (seven tests converted; page bitmaps
# 2712 -> 556) and left :func:`test_the_drawn_tie_is_still_carried_here` as the
# fence so a later card cannot quietly undo that. This block is written to the
# fence rather than around it: it adds **no** render, it touches none of
# :data:`DRAWN_TIE_CARRIERS`, and the rows it compares against come from
# :func:`_planned_rows` — the same plan reading the converted tests use, with
# no page drawn at all.
#
# What is new is the *other* side of the comparison. CARD-219's converted
# tests could only ask the builder what it decided; a content stream is the
# first artefact in this project that says what the TOC page actually
# **prints**, in a form that is text rather than pixels. So the tie the fence
# protects is not weakened and is not replaced: the plan is still read from the
# plan, and the drawing is now read from the drawing.
# ==========================================================================

import re as _re
from random import Random as _Random

from nonogram.admin.book_pdf_generator import FOLIO_PT as _FOLIO_PT
from nonogram.admin import book_toc_vector as _book_toc_vector
from nonogram.admin.book_vector import write_vector_pdf as _write_vector_pdf
from tests.helpers import pdf_vector as _pdf_vector

_TOC_SHOW = _re.compile(
    r"/\S+ (" + _pdf_vector.NUMBER + r") Tf \S+ \S+ Td \((.*?)\) Tj"
)


def _toc_strings(stream_text: str) -> List[str]:
    """Every string a TOC page's stream sets, in the order it sets them."""
    return [text for _, text in _TOC_SHOW.findall(stream_text)]


def _vector_toc_streams(
    generator: BookPDFGenerator, rows: List[TocEntry]
) -> List[str]:
    """``rows`` as the content streams of the TOC pages that would print them.

    Split by the production split — ``_toc_entries_per_page`` on the same
    frame ``interior_stream`` measures it on — so this helper re-decides
    nothing (the TOC's own page break stays one source of truth, G-1).
    """
    first = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
    streams = list(
        _book_toc_vector.toc_pages(rows, generator.page_spec, generator.dpi, first)
    )
    data = _write_vector_pdf(streams, len(streams)).getvalue()
    return _pdf_vector.content_streams(data)


class TestToc_EveryRowMatchesThePagePlan:
    """AC-4 (CARD-297): the printed rows are the planned rows, read as operators.

    Three things per row — its **name**, its **number**, and the page's own
    **folio** — each compared against :func:`_planned_rows`' own answer. The
    rows arrive in print order in the stream, so the comparison is of two
    ordered lists and not of two sets: a TOC that listed the right rows in the
    wrong order would red.
    """

    PUZZLES = (6, 4, 2)

    @staticmethod
    def _generator() -> BookPDFGenerator:
        return BookPDFGenerator(_book("card-297-toc"))

    def _rows(self) -> List[TocEntry]:
        return _planned_rows(self._generator(), _puzzles(easy=6, medium=4, hard=2))

    def test_every_rows_name_and_number_is_printed_in_plan_order(self) -> None:
        generator = self._generator()
        rows = self._rows()
        assert rows, "the plan listed no rows"
        shown = [
            text
            for stream_text in _vector_toc_streams(generator, rows)
            for text in _toc_strings(stream_text)
        ]
        # The title repeats on every TOC page and the folio closes each one;
        # the leader dots are a run of full stops. What is left, in order, is
        # the rows.
        pages = len(_vector_toc_streams(generator, rows))
        content = [
            text
            for text in shown
            if text != TOC_TITLE and set(text) != {"."}
        ]
        folios = content[-pages:] if pages else []
        content = content[: len(content) - pages]
        printed: List[Tuple[str, Optional[str]]] = []
        index = 0
        while index < len(content):
            label = content[index]
            index += 1
            if index < len(content) and content[index].isdigit():
                printed.append((label, content[index]))
                index += 1
            else:
                printed.append((label, None))
        expected = [
            (row.label, None if row.page is None else str(row.page)) for row in rows
        ]
        assert printed == expected
        assert folios == [
            str(1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + offset)
            for offset in range(pages)
        ]

    def test_only_the_heading_rows_print_without_a_number(self) -> None:
        rows = self._rows()
        headings = [row.label for row in rows if row.page is None]
        assert headings == [tier.label for tier in TIERS]
        shown = [
            text
            for stream_text in _vector_toc_streams(self._generator(), rows)
            for text in _toc_strings(stream_text)
        ]
        for label in headings:
            position = shown.index(label)
            assert set(shown[position + 1]) != {"."}, (
                f"{label!r} is a heading and must lead to no number, so it "
                "gets no leader dots either"
            )

    def test_every_numbered_row_leads_to_its_number_with_dots(self) -> None:
        rows = self._rows()
        shown = [
            text
            for stream_text in _vector_toc_streams(self._generator(), rows)
            for text in _toc_strings(stream_text)
        ]
        cursor = 0
        for row in rows:
            position = shown.index(row.label, cursor)
            cursor = position + 1
            if row.page is None:
                continue
            assert shown[position + 1] == str(row.page)
            assert set(shown[position + 2]) == {"."}, shown[position : position + 3]

    def test_the_comparison_would_have_caught_a_one_page_drift(self) -> None:
        """The control (ADR-0039/R1): a row pointed one page off is seen.

        The same shape ``test_the_comparison_would_have_caught_a_one_page_drift``
        makes for the drawn pages, in the stream instead of in the pixels.
        """
        generator = self._generator()
        rows = self._rows()
        drifted = [
            TocEntry(
                row.label,
                None if row.page is None else row.page + 1,
                starts_group=row.starts_group,
            )
            for row in rows
        ]
        one = _vector_toc_streams(generator, rows)
        two = _vector_toc_streams(generator, drifted)
        assert [_toc_strings(text) for text in one] != [
            _toc_strings(text) for text in two
        ]

    def test_the_page_carries_no_image_xobject(self) -> None:
        """AC-1's TOC half, read where the rows were read (ADR-0042/R1)."""
        generator = self._generator()
        rows = self._rows()
        streams = list(
            _book_toc_vector.toc_pages(rows, generator.page_spec, generator.dpi, 4)
        )
        data = _write_vector_pdf(streams, len(streams)).getvalue()
        for keys in _pdf_vector.page_resource_keys(data):
            assert "XObject" not in keys, keys

    def test_no_page_bitmap_was_built_to_make_any_of_this(self) -> None:
        """The fence's own property, restated for this class (CARD-219).

        Every cell above reads the plan and a content stream. Asserted
        structurally rather than claimed: no method of this class names any of
        the three idioms by which a test in this file reaches a drawn page
        (:data:`DRAWN_PAGE_IDIOMS`).
        """
        source = inspect.getsource(TestToc_EveryRowMatchesThePagePlan)
        assert [idiom for idiom in DRAWN_PAGE_IDIOMS if idiom in source] == []


class TestToc_TheFolioYieldsToARowThatReachesItsLine:
    """The folio's omit-rather-than-collide rule, in the new medium.

    ``_draw_folio``'s room check — "the folio yields, the content wins"
    (CARD-200) — is carried into the vector writer, and this is the cell that
    makes it load-bearing: handed more rows than its own frame has room for,
    the page prints its rows and **no** page number, rather than setting one
    into a row's glyphs.

    The over-long list is reached deliberately rather than built: production
    never hands a page more rows than ``_toc_entries_per_page`` measured for
    it (``interior_stream`` does the split), so the guard's live case has to be
    driven here. The row count is taken **from that same measurement**, so the
    case cannot drift away from the capacity it is twice.
    """

    def test_a_page_given_twice_its_rows_prints_no_folio(self) -> None:
        generator = BookPDFGenerator(_book("card-297-folio"))
        frame = page_frame(generator.page_spec(7))
        capacity = _toc_entries_per_page(frame, generator.dpi)
        rows = [TocEntry(f"Section {index}", index + 1) for index in range(capacity * 2)]
        stream = _book_toc_vector.toc_page_stream(rows, frame, generator.dpi, 7)
        (text,) = _pdf_vector.content_streams(
            _write_vector_pdf([stream], 1).getvalue()
        )
        shown = _toc_strings(text)
        assert shown[0] == TOC_TITLE
        assert shown[-1] != "7", shown[-4:]
        assert "Section 0" in shown

    def test_the_same_page_within_its_capacity_does_print_it(self) -> None:
        """The negative control: the omission is the room check, not the writer."""
        generator = BookPDFGenerator(_book("card-297-folio"))
        frame = page_frame(generator.page_spec(7))
        capacity = _toc_entries_per_page(frame, generator.dpi)
        rows = [TocEntry(f"Section {index}", index + 1) for index in range(capacity)]
        stream = _book_toc_vector.toc_page_stream(rows, frame, generator.dpi, 7)
        (text,) = _pdf_vector.content_streams(
            _write_vector_pdf([stream], 1).getvalue()
        )
        assert _toc_strings(text)[-1] == "7"


class TestToc_TheLeaderRunNeedsNoCorrectionOnThisFace:
    """Why :func:`book_toc_vector.leader_dots`' two corrections are inert here.

    They are the raster page's, kept by G-1, and **two deletion mutants on
    them survive every cell of this card**. That is declared rather than
    discovered, and this class is the proof of why — **corrected in review
    cycle 2, because the proof it first gave was false** (F-297-02).

    What it used to say: ``FontMetrics.advance`` sums the face's own
    ``/Widths`` and divides once, so ``n`` dots measure *exactly* ``n`` times
    one dot, and an exactly linear measure makes ``int(run // dot)`` both the
    largest count that fits and not one short of it. That mechanism is
    self-refuting on its own terms — summing then dividing once computes
    ``(W·n)/1000``, which is precisely **not** ``n·(W/1000)`` in binary
    floating point, so "divides once" is the reason the two differ rather than
    the reason they agree. Measured at this class's own size
    (``type_px(TOC_ENTRY_PT, DPI)`` = 42 px, dot 13.356 px), exact equality
    fails at **56 of the first 200 counts, first at n = 9**, and at **twelve
    counts inside the 120–153 range** the old docstring named as the
    production one. The five counts it sampled all fall in the ~72 % that
    happen to hold, so the control passed by sample selection.

    What holds instead is **reachability, not exactness**: the relative error
    is at most ~2.2e-16, orders of magnitude too small to move
    ``int(run // dot)`` across an integer boundary, so neither loop can fire
    for any run a page can hand it. That is asserted over the reachable domain
    below rather than over hand-picked counts. The inputs that *do* break the
    identity are the exact ``n``-indexed sums themselves, and those are
    synthetic: a real run is ``dot_right - dot_left``, a difference of two page
    coordinates. Fed the sums instead, the grow loop fires on hundreds of
    counts — which is what makes it the exactness argument that fails and not
    the smallness one.

    The raster page corrects because ``FreeTypeFont.getlength`` carries no
    guarantee either; that it happens to be exactly linear at this size is
    :meth:`test_the_raster_measure_is_linear_at_this_size_too`'s own finding,
    a different claim about a different engine.
    """

    @staticmethod
    def _face():
        from nonogram.admin.book_vector import interior_face_metrics

        return interior_face_metrics()

    @staticmethod
    def _reachable_ceiling() -> int:
        """The widest leader run any trim CON-018 stocks can hold, in pixels.

        Derived rather than quoted: a run is a span inside one TOC page's own
        usable area, so the widest trim's usable width bounds every run every
        trim can produce. Book 1 (8.5 x 11 in) is the widest CON-018 stocks.
        """
        generator = BookPDFGenerator(_book("card-297-leader"))
        frame = page_frame(generator.page_spec(7))
        return int(frame.right - frame.left) + 1

    def test_the_measure_is_linear_in_a_repeated_dot(self) -> None:
        """It is **not** exactly linear, and the bound is the error, not equality.

        Three readings, and the first replaces a false claim rather than
        widening a true one.

        * exact equality between ``advance(n dots)`` and ``n * advance(dot)``
          **fails**, and the failures are counted rather than hidden — so no
          later reader can inherit "n dots measure exactly n times one dot" as
          a structural property of summing ``/Widths``;
        * the **relative** error is bounded well below 1e-15 across every count
          past the longest run a page prints, which is the quantity the two
          loops' survival actually rests on;
        * and one dot's advance is a whole thousandth of the em, so what is
          measured above is accumulation in the product rather than kerning.
        """
        from nonogram.admin.book_vector_draw import advance_px

        face = self._face()
        size = type_px(TOC_ENTRY_PT, DPI)
        one = advance_px(".", size, face)
        counts = range(1, 601)
        broken = [n for n in counts if advance_px("." * n, size, face) != n * one]
        assert broken, (
            "exact equality now holds everywhere, so this class's stated "
            "reason is no longer the one its loops survive on"
        )
        assert broken[0] <= 20, broken[:5]
        worst = max(
            abs(advance_px("." * n, size, face) - n * one) / (n * one) for n in counts
        )
        assert 0 < worst < 1e-15, worst
        assert face.advance(".") * 1000 == int(face.advance(".") * 1000)

    def test_neither_correction_fires_for_any_run_a_page_can_hold(self) -> None:
        """The bound the two declared survivors really stand on (F-297-02).

        ``leader_dots`` runs a division and then two corrections. Neither
        correction can change the division's answer for any run a page can
        produce, and that is asserted as exactly that: the returned count
        **equals** ``int(run // dot)`` for every run swept, so a loop that
        fired would have to change it and would red here.

        Two sweeps over the **reachable** domain rather than over dot counts:
        every integer run from zero to the widest trim's own usable width, and
        a seeded fractional corpus over the same span (stdlib
        ``random.Random`` — no ``hypothesis``, it is not in the dependency
        baseline), with the case count asserted inside so the corpus cannot
        silently shrink (G-7).
        """
        from nonogram.admin.book_vector_draw import advance_px

        face = self._face()
        size = type_px(TOC_ENTRY_PT, DPI)
        one = advance_px(".", size, face)
        ceiling = self._reachable_ceiling()
        assert ceiling > 2000, ceiling

        cases = 0
        for run in range(0, ceiling):
            dots = _book_toc_vector.leader_dots(float(run), size, face)
            assert len(dots) == int(run // one), (run, len(dots))
            cases += 1
        choose = _Random(297)
        for _ in range(20_000):
            run = choose.uniform(0.0, float(ceiling))
            dots = _book_toc_vector.leader_dots(run, size, face)
            assert len(dots) == int(run // one), (run, len(dots))
            cases += 1
        assert cases >= 22_000, cases

    def test_the_synthetic_input_that_does_fire_the_grow_loop(self) -> None:
        """The control, and the reason the *exactness* reading was wrong.

        Handed the exact ``n``-indexed sums — the inputs the old docstring's
        mechanism was about — the grow loop *does* fire, on hundreds of counts.
        So the loops are not dead because the measure is exact; they are dead
        because a page cannot hand them an input of that shape. This cell is
        what makes the two arguments distinguishable, which the five sampled
        counts it replaces could not do.
        """
        from nonogram.admin.book_vector_draw import advance_px

        face = self._face()
        size = type_px(TOC_ENTRY_PT, DPI)
        one = advance_px(".", size, face)
        fired = []
        for count in range(0, 2001):
            run = advance_px("." * count, size, face)
            if len(_book_toc_vector.leader_dots(run, size, face)) != int(run // one):
                fired.append(count)
        assert len(fired) > 500, len(fired)
        # Every firing grows rather than trims: the exact sum of n dots is
        # never *over* the run it is, so nothing is ever cut.
        for count in fired:
            run = advance_px("." * count, size, face)
            assert len(_book_toc_vector.leader_dots(run, size, face)) > int(run // one)

    def test_the_division_alone_is_therefore_the_answer(self) -> None:
        from nonogram.admin.book_vector_draw import advance_px

        face = self._face()
        size = type_px(TOC_ENTRY_PT, DPI)
        one = advance_px(".", size, face)
        for run in (0.0, one / 2, one, one * 2.5, one * 40, one * 40 + 0.001):
            dots = _book_toc_vector.leader_dots(run, size, face)
            assert len(dots) == int(run // one), (run, len(dots))
            assert advance_px(dots, size, face) <= run + 1e-9
            assert advance_px(dots + ".", size, face) > run


class TestToc_TheRowClipHasTheBoundItsDocstringPromises:
    """:func:`book_toc_vector.clipped_to`'s stated bound, as a test.

    Review cycle 1's F-297-03, second half: the TOC writer's copy of the clip
    loop is the one undeclared survivor of this card — deleting the whole
    ellipsis loop passed every cell — while its docstring promises a bound
    ("it cannot fire for any row the structural list builds on any trim
    CON-018 stocks"). A stated bound with no cell proving it is the same family
    as F-297-02, so the bound is asserted here and the loop is driven directly
    so it is also covered at the unit level.

    **The asymmetry with the answer writer's copy is deliberate and stays**:
    that one is live (the 10 x 10 cm trim clips a caption today) and covered by
    the cross-medium comparison; this one is dead in production and bounded.
    Which is exactly why the two copies were not shared — a single routine
    would have had to carry both stories.
    """

    #: Trims CON-018 stocks, narrowest first — the 10 x 10 cm square minimum
    #: is the one that bounds this, since a narrower measure is what would make
    #: a label clip.
    TRIMS = ((10.0, 10.0), (13.97, 21.59), (15.24, 22.86), (21.59, 27.94))

    @staticmethod
    def _face():
        from nonogram.admin.book_vector import interior_face_metrics

        return interior_face_metrics()

    def _book_on(self, trim: Tuple[float, float]) -> Book:
        return Book(
            book_id=f"card-297-clip-{trim[0]}x{trim[1]}",
            metadata=BookMetadata(
                title="Winter Pictures",
                description="CARD-297's TOC clip bound.",
                theme="generic",
                target_audience="adults",
                size="",
                page_count=0,
            ),
            trim_width_cm=f"{trim[0]:.2f}",
            trim_height_cm=f"{trim[1]:.2f}",
            gutter_margin_cm=_book().gutter_margin_cm,
            outside_margin_cm=_book().outside_margin_cm,
        )

    def test_no_structural_row_clips_on_any_trim_con_018_stocks(self) -> None:
        """The bound. Every label fits its own measure, so the loop is inert.

        Read off the **production builder's** rows rather than hand-made ones,
        and against the measure the writer really gives each row — the usable
        width less the page number and two gaps, which is the narrower of the
        two measures ``toc_page_stream`` computes.
        """
        from nonogram.admin.book_vector_draw import advance_px

        face = self._face()
        cases = 0
        for trim in self.TRIMS:
            generator = BookPDFGenerator(self._book_on(trim))
            frame = page_frame(generator.page_spec(7))
            spec = _book_toc_vector.toc_type(generator.dpi)
            size_px = spec.entry_size_px
            measure = float(frame.right - frame.left)
            rows = _structural_shape(
                ("Easy", "Puzzles 1–8", 11),
                ("Medium", "Puzzles 9–16", 29),
                ("Hard", "Puzzles 17–24", 47),
                solutions_page=65,
            )
            for row in rows:
                room = measure
                if row.page is not None:
                    room -= advance_px(str(row.page), size_px, face)
                    room -= 2 * spec.entry_gap_px
                assert (
                    _book_toc_vector.clipped_to(row.label, size_px, face, room)
                    == row.label
                ), (trim, row.label, room)
                assert advance_px(row.label, size_px, face) <= room, (trim, row.label)
                cases += 1
        # The corpus cannot silently shrink (G-7): four trims times the rows a
        # three-level structural list builds.
        assert cases >= 32, cases

    def test_the_loop_does_clip_a_label_that_does_not_fit(self) -> None:
        """The drive, so the bound above is a bound and not an absence.

        The loop is dead in production and alive here: a label wider than its
        room comes back ellipsised and short enough to fit, and a label is never
        clipped away entirely however little room there is.

        **The expected string comes from an independent second implementation**
        of the step rather than from the function under test: the candidates
        the ``[:-2] + "…"`` rule can produce are generated here, and the answer
        must be the **first** of them that fits. A step that took one character
        more or fewer off therefore lands on a different candidate and reds —
        which is the edge mutant that survived 596 cells in review cycle 1.
        """
        from nonogram.admin.book_vector_draw import advance_px

        def candidates(text: str) -> List[str]:
            """Every string the rule can produce, longest first."""
            out = [text]
            while len(out[-1]) > 1:
                out.append(out[-1][:-2] + "…")
            return out

        face = self._face()
        size_px = _book_toc_vector.toc_type(DPI).entry_size_px
        label = "A section whose name runs the whole width of the page and more"
        for room in (120.0, 300.0, 600.0, 1200.0):
            clipped = _book_toc_vector.clipped_to(label, size_px, face, room)
            assert clipped != label, room
            assert clipped.endswith("…"), clipped
            assert label.startswith(clipped[:-1]), clipped
            assert advance_px(clipped, size_px, face) <= room, (room, clipped)
            fitting = [
                candidate
                for candidate in candidates(label)
                if advance_px(candidate, size_px, face) <= room
            ]
            assert clipped == fitting[0], (room, clipped, fitting[0])
        # Nothing is clipped away entirely, however little room there is.
        assert len(_book_toc_vector.clipped_to(label, size_px, face, 0.0)) == 1


# --------------------------------------------------------------------------
# F-297-07 — the new anchors' and the folio's *positions*, not just their
# strings. AC-4 reads every TOC row's number, name and folio as VALUES against
# the page plan, which is what it asks for; nothing read any of them as a
# POSITION, so review cycle 1 could delete draw_folio's outer-corner choice
# (`x = right - advance if right_hand else left` -> `x = left`, the folio at
# the gutter on every right-hand page) and set_right_from_top's right
# alignment (a page number running off into the trim margin) with 596 cells
# still green. These cells read the ``Td`` operand.
# --------------------------------------------------------------------------


def _set_at(stream) -> List[Tuple[float, float, str]]:
    """Every ``(x, y, text)`` a stream set, in points, from its own operators."""
    pattern = _re.compile(
        r"/\S+ " + _pdf_vector.NUMBER + r" Tf ("
        + _pdf_vector.NUMBER + r") (" + _pdf_vector.NUMBER + r") Td \((.*?)\) Tj"
    )
    out: List[Tuple[float, float, str]] = []
    for line in stream.operators:
        found = pattern.search(line)
        if found is not None:
            out.append((float(found.group(1)), float(found.group(2)), found.group(3)))
    return out


class TestVectorAnchors_ThePositionsAndNotOnlyTheStrings:
    """Review cycle 1's F-297-07: one control per decision these routines make.

    Of ``draw_folio``'s four decisions — omit or not, which corner, the
    right-hand clearance, the left-hand clearance — exactly one (omit or not)
    had a control before this class. Each cell below deletes one decision by
    construction rather than by mutation: it builds the case where the two
    answers differ and asserts which one comes out, so a routine that stopped
    making the decision reds.
    """

    FRAME = (100.0, 50.0, 700.0, 900.0)  # left, top, right, bottom

    @staticmethod
    def _face():
        from nonogram.admin.book_vector import interior_face_metrics

        return interior_face_metrics()

    def _stream(self):
        from nonogram.admin.book_vector import ContentStream

        return ContentStream(width_px=800.0, height_px=1000.0, dpi=300)

    def test_a_right_hand_folio_ends_at_the_fore_edge_and_a_left_hand_one_starts_at_it(
        self,
    ) -> None:
        """Which corner, read off ``Td`` (FR-043: bottom-**outer**).

        The mutant this closes is ``x = left`` on both parities, which prints
        every right-hand folio at the gutter. The two parities are asserted
        against each other as well as against their own figures, so a routine
        that put both at the same x reds whatever that x is.
        """
        from nonogram.admin.book_vector_draw import advance_px, draw_folio

        left, top, right, bottom = self.FRAME
        face = self._face()
        size_px = type_px(_FOLIO_PT, DPI)
        width = advance_px("7", size_px, face)
        placed = {}
        for right_hand in (True, False):
            stream = self._stream()
            assert draw_folio(
                stream, left, top, right, bottom, "7", size_px, face,
                right_hand=right_hand,
            )
            ((x, _, text),) = _set_at(stream)
            assert text == "7"
            placed[right_hand] = x
        assert placed[True] == pytest.approx(
            stream.to_points(right - width), abs=0.002
        ), placed
        assert placed[False] == pytest.approx(stream.to_points(left), abs=0.002), placed
        assert placed[True] != placed[False]

    def test_the_right_hand_clearance_reads_the_content_s_right_edge(self) -> None:
        """The third decision, and *which* operand it reads.

        Both cases are built so that reading ``content_left`` instead of
        ``content_right`` flips the answer — the mutant that survived 596
        cells in review cycle 1.
        """
        from nonogram.admin.book_vector_draw import draw_folio

        left, top, right, bottom = self.FRAME
        face = self._face()
        size_px = type_px(_FOLIO_PT, DPI)
        # No vertical room, so the horizontal rule decides.
        assert draw_folio(
            self._stream(), left, top, right, bottom, "7", size_px, face,
            right_hand=True, content_bottom=bottom,
            content_right=left, content_left=right,
        ), "content stopping at the gutter leaves the fore-edge corner clear"
        assert not draw_folio(
            self._stream(), left, top, right, bottom, "7", size_px, face,
            right_hand=True, content_bottom=bottom,
            content_right=right, content_left=left,
        ), "content reaching the fore edge must take the folio with it"

    def test_the_left_hand_clearance_is_a_decision_too(self) -> None:
        """The fourth decision — the arm review cycle 1 replaced with ``pass``.

        A left-hand page's folio sits at the gutter-side corner, so what has to
        be clear is the content's **left** edge. Replacing this arm with an
        unconditional "clear" leaves the second case printing a folio into a
        row's glyphs, and nothing in the tree noticed.
        """
        from nonogram.admin.book_vector_draw import draw_folio

        left, top, right, bottom = self.FRAME
        face = self._face()
        size_px = type_px(_FOLIO_PT, DPI)
        assert draw_folio(
            self._stream(), left, top, right, bottom, "7", size_px, face,
            right_hand=False, content_bottom=bottom,
            content_left=right, content_right=right,
        ), "content starting past the folio leaves its corner clear"
        assert not draw_folio(
            self._stream(), left, top, right, bottom, "7", size_px, face,
            right_hand=False, content_bottom=bottom,
            content_left=left, content_right=right,
        ), "content reaching the gutter edge must take the folio with it"

    def test_a_caller_with_no_horizontal_figure_keeps_the_conservative_rule(
        self,
    ) -> None:
        """The default both arms share: no figure, no exemption.

        ``content_right``/``content_left`` default to ``None``, and the
        docstring says a caller with no horizontal figure keeps the more
        conservative rule. Asserted on both parities, so neither arm can be
        the one that quietly admits a missing figure.
        """
        from nonogram.admin.book_vector_draw import draw_folio

        left, top, right, bottom = self.FRAME
        face = self._face()
        size_px = type_px(_FOLIO_PT, DPI)
        for right_hand in (True, False):
            assert not draw_folio(
                self._stream(), left, top, right, bottom, "7", size_px, face,
                right_hand=right_hand, content_bottom=bottom,
            ), right_hand

    def test_the_vertical_room_check_is_what_opens_the_horizontal_one(self) -> None:
        """The first decision, kept honest from the other side.

        With room below the content, no horizontal figure is consulted at all —
        so the clearance arms cannot be what prints a folio, and the omission
        above is the room check rather than a missing default.
        """
        from nonogram.admin.book_vector_draw import draw_folio, line_height_px

        left, top, right, bottom = self.FRAME
        face = self._face()
        size_px = type_px(_FOLIO_PT, DPI)
        room = line_height_px(size_px, face)
        assert room > 0
        assert draw_folio(
            self._stream(), left, top, right, bottom, "7", size_px, face,
            right_hand=True, content_bottom=bottom - room - 1,
            content_right=right, content_left=left,
        )

    def test_a_row_s_page_number_ends_exactly_at_the_measure_s_far_edge(self) -> None:
        """``set_right_from_top``'s right alignment, read off ``Td``.

        The mutant this closes dropped the alignment and set the number
        left-aligned *at* ``right``, i.e. running into the trim margin. The
        assertion is on the string's own far edge — ``x + advance`` — so it
        fails whether the alignment is dropped or merely wrong.
        """
        from nonogram.admin.book_vector_draw import advance_px, set_right_from_top

        face = self._face()
        size_px = type_px(TOC_ENTRY_PT, DPI)
        stream = self._stream()
        set_right_from_top(stream, "123", 700.0, 50.0, size_px, face)
        ((x, _, text),) = _set_at(stream)
        assert text == "123"
        far = x + stream.to_points(advance_px("123", size_px, face))
        assert far == pytest.approx(stream.to_points(700.0), abs=0.002), (x, far)
        assert x < stream.to_points(700.0)

    def test_the_default_anchor_sets_from_the_left_edge_and_the_ascender(self) -> None:
        """``set_from_top``'s two halves, which nothing read as positions.

        Pillow's ``"la"``: the left edge is the ``x`` given, and the baseline is
        the ascender *below* the ``y`` given. Both asserted against the face's
        own figures, which is what makes the conversion checkable rather than
        plausible.
        """
        from nonogram.admin.book_vector_draw import ascent_px, set_from_top

        face = self._face()
        size_px = type_px(TOC_ENTRY_PT, DPI)
        stream = self._stream()
        set_from_top(stream, "Easy", 120.0, 240.0, size_px, face)
        ((x, y, text),) = _set_at(stream)
        assert text == "Easy"
        assert x == pytest.approx(stream.to_points(120.0), abs=0.002)
        baseline = 240.0 + ascent_px(size_px, face)
        assert y == pytest.approx(
            stream.to_points(stream.height_px - baseline), abs=0.002
        ), (y, baseline)
        assert ascent_px(size_px, face) > 0

    def test_the_face_measurements_are_the_faces_own_and_not_estimates(self) -> None:
        """``advance_px``, ``ascent_px``, ``descent_px``, ``line_height_px``.

        Four new face measurements arrived in this card's ``+214`` with no cell
        of their own reading the numbers back. Each is asserted against the
        ``/Widths`` and ``FontDescriptor`` figures it is a scaling of — a
        second expression of the same quantity, so a dropped divisor or a lost
        sign reds — and the descender's flip is asserted as a *sign* change,
        which is the one thing that conversion exists to do.
        """
        from nonogram.admin.book_vector_draw import (
            advance_px,
            ascent_px,
            descent_px,
            line_height_px,
        )

        face = self._face()
        size = 42.0
        assert advance_px("Easy", size, face) == face.advance("Easy") * size
        assert advance_px("", size, face) == 0.0
        assert ascent_px(size, face) == face.ascent / 1000.0 * size
        assert face.descent < 0, face.descent
        assert descent_px(size, face) == -face.descent / 1000.0 * size
        assert descent_px(size, face) > 0
        assert line_height_px(size, face) == pytest.approx(
            ascent_px(size, face) + descent_px(size, face)
        )


# ==========================================================================
# CARD-382 -- the controls for the readings that make this module green in
# BOTH media. Each reading above reads one medium or the other depending on
# the tree; each control below runs in either tree and can fail.
# ==========================================================================


class TestBookToc_TheReadingsReachBothMedia:
    """The TOC spy sees the rows whichever callee the walk used; the page
    comparison refuses to cross media and tells two pages apart in each."""

    def _stream(self, *marks: str) -> ContentStream:
        stream = ContentStream(width_px=600, height_px=800, dpi=300)
        for index, mark in enumerate(marks):
            stream.text(mark, 50, 100 + 40 * index, 10.0)
        return stream

    def test_the_spy_records_the_rows_the_plan_lists(self, monkeypatch) -> None:
        from nonogram.admin.book_interior_vector import interior_generator

        puzzles = _puzzles(easy=2, medium=2, hard=1)
        generator = interior_generator(_book("card-382-vector"))
        rows = _rows_of(generator, puzzles, monkeypatch)
        assert rows, "the spy recorded no row"
        assert rows == _planned_rows(generator, puzzles)

    def test_the_spy_records_nothing_for_a_book_with_no_puzzles(self, monkeypatch) -> None:
        # The spy can come back empty: it is not a list that always fills.
        assert _spy_toc_pages(BookPDFGenerator(_book("card-382-empty")), [], monkeypatch) == []

    def test_two_streams_are_the_same_page_only_if_every_mark_is(self) -> None:
        assert _same_written_page(self._stream("8", "9"), self._stream("8", "9"))
        assert not _same_written_page(self._stream("8", "9"), self._stream("8", "9", "x"))
        assert not _same_written_page(self._stream("8", "9"), self._stream("9", "8"))

    def test_two_bitmaps_are_the_same_page_only_if_their_ink_is(self) -> None:
        from PIL import Image

        def page(box) -> Image.Image:
            image = Image.new("RGB", (300, 300), (255, 255, 255))
            ImageDraw.Draw(image).rectangle(box, fill=(0, 0, 0))
            return image

        assert _same_written_page(page((20, 20, 200, 200)), page((20, 20, 200, 200)))
        assert not _same_written_page(page((20, 20, 200, 200)), page((120, 120, 280, 280)))

    def test_a_bitmap_is_never_held_against_a_stream(self) -> None:
        from PIL import Image

        bitmap = Image.new("RGB", (600, 800), (255, 255, 255))
        with pytest.raises(AssertionError, match="build the expected page in the medium"):
            _same_written_page(bitmap, self._stream("8"))
        with pytest.raises(AssertionError, match="build the expected page in the medium"):
            _same_written_page(self._stream("8"), bitmap)
