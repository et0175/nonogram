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

**How this file reads a TOC page's own rows**, rather than template-matching
rendered pixels: :meth:`BookPDFGenerator.create_toc_page` is handed its own
``entries`` — :class:`TocEntry` rows — by :meth:`interior_stream`'s
``produce()``, already split one page at a time. Spying on
``BookPDFGenerator.create_toc_page`` itself (rather than ``ImageDraw.text``,
which would also have to reconstruct which text belongs to which column) is
exactly what lets this file assert on the *rows a TOC page was asked to
draw* — the content decision — independently of whether the drawing itself
put them in readable pixels. AC-6 is the one exception, and necessarily so:
leader dots are a geometry claim about drawn positions, so that class spies on
``ImageDraw.text`` and measures the three runs against each other with the
page's own font.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pytest
from PIL import ImageDraw

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
    TOC_SOLUTIONS_LABEL,
    BookPDFGenerator,
    DividerPagePlan,
    PuzzlePagePlan,
    TocEntry,
    _guide_face,
    default_toc_frame,
    interior_page_count,
    measured_toc_page_count,
    page_frame,
    structural_toc_entries,
    structural_toc_entry_count,
    toc_range_label,
    type_px,
)
from tests.helpers.book_corpus import corpus_book, puzzle

# CARD-221 removed this file's ``_lettered_as_recorded()`` host gate, which
# compared the baseline fixture's ``font_fingerprint`` against this machine's
# and skipped the two pinned px figures where they differed. Its condition is
# gone, measured rather than assumed: every face the TOC page letters in now
# comes from ``src/nonogram/export/fonts/`` (``_guide_face``), so a row's own
# height is 49 px and the title's line 258 px on every host, and both figures
# are asserted unconditionally below. Nothing else in this file reads the
# host's fonts.

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


def _spy_toc_pages(
    generator: BookPDFGenerator, puzzles: List[dict], monkeypatch: pytest.MonkeyPatch
) -> List[List[TocEntry]]:
    """Every ``create_toc_page`` call's own ``entries``, one list per TOC page."""
    original = BookPDFGenerator.create_toc_page
    recorded: List[List[TocEntry]] = []

    def spy(self, entries, page_number):
        recorded.append(list(entries))
        return original(self, entries, page_number)

    monkeypatch.setattr(BookPDFGenerator, "create_toc_page", spy)
    stream = generator.interior_stream(puzzles)
    for _ in stream.pages:
        pass
    monkeypatch.setattr(BookPDFGenerator, "create_toc_page", original)
    return recorded


def _rows_of(
    generator: BookPDFGenerator, puzzles: List[dict], monkeypatch: pytest.MonkeyPatch
) -> List[TocEntry]:
    """Every TOC row of a book, in order, across however many pages it took."""
    return [row for page in _spy_toc_pages(generator, puzzles, monkeypatch) for row in page]


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

    def test_the_rows_are_exactly_the_books_sections(self, monkeypatch) -> None:
        easy, medium, hard = AC3_SPLIT
        puzzles = _puzzles(easy=easy, medium=medium, hard=hard)
        generator = BookPDFGenerator(_book("card-205-ac1"))

        rows = _rows_of(generator, puzzles, monkeypatch)

        assert [row.label for row in rows] == [
            GUIDE_TITLE,
            "Easy",
            "Puzzles 1–60",
            "Medium",
            "Puzzles 61–120",
            "Hard",
            "Puzzles 121–150",
            TOC_SOLUTIONS_LABEL,
        ]
        assert len(rows) == 2 + 2 * 3, (
            "a three-level book lists eight rows however many puzzles it holds"
        )

    def test_no_row_names_an_individual_puzzle(self, monkeypatch) -> None:
        """The owner's decision, stated as the thing that must not be there.

        Every one of these puzzles carries a distinct picture name, and
        CARD-200's listing printed all 150 of them ("Puzzle 37 — Easy 36").
        Not one may appear now — nor the per-puzzle caption's own shape.
        """
        puzzles = _puzzles(easy=60, medium=60, hard=30)
        generator = BookPDFGenerator(_book("card-205-ac1-names"))

        labels = [row.label for row in _rows_of(generator, puzzles, monkeypatch)]
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
        assert labels == [GUIDE_TITLE, "Easy", "Puzzles 1–2", TOC_SOLUTIONS_LABEL]

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

    def test_each_row_points_at_the_page_the_walk_planned(self, monkeypatch) -> None:
        puzzles = _puzzles(easy=60, medium=60, hard=30)
        generator = BookPDFGenerator(_book("card-205-ac2"))

        rows = _rows_of(generator, puzzles, monkeypatch)
        decided = generator.section_plan(list(puzzles))
        dividers = _divider_pages(generator, puzzles)

        by_label = {row.label: row.page for row in rows}
        assert by_label[GUIDE_TITLE] == 1, (
            "the guide opens the interior as right-hand page 1 (INV-013)"
        )
        # Each range row against its own level's divider, read off the same
        # SectionPlan the pages were drawn from.
        ranges = [row for row in rows if row.label.startswith("Puzzles ")]
        assert [row.page for row in ranges] == [page for _, page in dividers]
        assert [label for label, _ in dividers] == ["Easy", "Medium", "Hard"]

        # The solutions row against the SOLUTIONS divider: the interior's own
        # `first_answer_page - 1`, recomputed here from the walk's own terms
        # rather than read back out of the generator.
        solutions_divider = (
            1 + GUIDE_PAGE_COUNT + decided.toc_page_count + len(decided.pages)
        )
        assert by_label[TOC_SOLUTIONS_LABEL] == solutions_divider

    def test_the_named_pages_really_are_those_pages(self, monkeypatch) -> None:
        """Not just "the numbers agree with an arithmetic", but "the page at
        that position is the page the row names".

        The walk is replayed page by page and each named position is checked
        against what was actually yielded there: page 1 is a guide page, each
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
        for number in range(1, GUIDE_PAGE_COUNT + 1):
            kind_of[number] = "guide"
        solutions = 1 + GUIDE_PAGE_COUNT + decided.toc_page_count + len(decided.pages)
        kind_of[solutions] = "divider:SOLUTIONS"

        assert kind_of[rows[0].page] == "guide"
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
        ``1 + GUIDE_PAGE_COUNT + toc_page_count`` opening position: every
        level row's page must be at least that, and the first level's exactly
        that (its divider is the puzzle section's first page).
        """
        puzzles = _puzzles(easy=5, hard=5)
        generator = BookPDFGenerator(_book("card-205-ac2-offset"))

        rows = _rows_of(generator, puzzles, monkeypatch)
        decided = generator.section_plan(list(puzzles))
        first_section_page = 1 + GUIDE_PAGE_COUNT + decided.toc_page_count

        ranges = [row for row in rows if row.label.startswith("Puzzles ")]
        assert ranges[0].page == first_section_page
        assert all(row.page >= first_section_page for row in ranges)
        assert rows[-1].page > ranges[-1].page


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookToc_RangeRowsFollowTheLevelRuns:
    """60/60/30 reads ``Puzzles 1–60``, ``61–120``, ``121–150``."""

    def test_the_three_ranges_are_the_cards_own_sample(self, monkeypatch) -> None:
        easy, medium, hard = AC3_SPLIT
        puzzles = _puzzles(easy=easy, medium=medium, hard=hard)
        generator = BookPDFGenerator(_book("card-205-ac3"))

        labels = [row.label for row in _rows_of(generator, puzzles, monkeypatch)]

        assert [label for label in labels if label.startswith("Puzzles ")] == [
            "Puzzles 1–60",
            "Puzzles 61–120",
            "Puzzles 121–150",
        ]

    def test_the_ranges_tile_the_book_with_no_gap_or_overlap(self, monkeypatch) -> None:
        """A second, independent reading: the ranges parsed back out of the
        labels must be exactly 1..150, each puzzle in one level's range.

        Written as a parse of the printed text rather than as a repeat of the
        arithmetic that produced it — an off-by-one in
        ``toc_range_label``'s own ``start + 1`` would pass a test that
        rebuilt the expected strings the same way.
        """
        puzzles = _puzzles(easy=60, medium=60, hard=30)
        generator = BookPDFGenerator(_book("card-205-ac3-tiling"))

        covered: List[int] = []
        for row in _rows_of(generator, puzzles, monkeypatch):
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

    def test_a_hundred_and_fifty_puzzles_take_one_toc_page(self, monkeypatch) -> None:
        puzzles = self._corpus()
        generator = BookPDFGenerator(_book("card-205-ac5"))

        pages = _spy_toc_pages(generator, puzzles, monkeypatch)
        decided = generator.section_plan(list(puzzles))

        assert len(pages) == 1, "the structural list fits one page"
        assert decided.toc_page_count == 1
        assert len(pages[0]) == 8

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

    def test_kdp_reports_the_same_toc_length_the_export_wrote(
        self, monkeypatch
    ) -> None:
        """The cross-check, through both functions' real entry points.

        Every other term of the two page counts (puzzle pages, dividers,
        answer pages) is independent of the TOC, and the KDP estimate is
        defined as the generator's own *unpaired* baseline (EC-034), so the
        two totals agreeing is exactly the statement that they agree about
        the TOC. The second assertion keeps that from being vacuous: under
        CARD-200's rule this book's TOC was four pages, so the pre-card entry
        rule would put the two totals four apart.
        """
        puzzles = self._corpus()
        book = _book("card-205-ac5-kdp")
        generator = BookPDFGenerator(book)

        stream = generator.interior_stream(list(puzzles))
        toc_pages_written = len(_spy_toc_pages(generator, puzzles, monkeypatch))

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
        assert structural_toc_entry_count(len(TIERS), len(puzzles)) == 8

    def test_the_gutter_band_itself_follows_the_new_count(self) -> None:
        """One step further out: the figure KDP's band lookup is given.

        A 150-puzzle book is near KDP's 151-300/301-500 boundaries, so this
        asserts the band the real page count lands in rather than only that
        two numbers match.
        """
        from nonogram.admin.book_kdp import kdp_page_band

        puzzles = self._corpus()
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


class TestBookToc_LeaderDotsStayInsideTheGap:
    """The dots lie strictly between the label and the number, touching neither."""

    @staticmethod
    def _drawn(
        generator: BookPDFGenerator,
        entries: List[TocEntry],
        monkeypatch: pytest.MonkeyPatch,
    ) -> List[Tuple[Tuple[float, float], str, Optional[str]]]:
        """One TOC page's **entry-row** ``ImageDraw.text`` calls: ``(xy, text, anchor)``.

        Filtered down to the rows, so a test below can assert on exactly what
        a row drew. Two other marks land on the page and are dropped here:
        the page's ``TOC_TITLE``, set in a much larger face, and the folio,
        which ``_draw_folio`` anchors ``"rb"``/``"lb"`` at the bottom corner.
        The folio happens to be set at the *same* pixel size as an entry
        (``FOLIO_PT == TOC_ENTRY_PT == 10.0``, both CON-020's floor) in a
        different face, so the anchor and not the size is what separates it —
        identity (``font is ...``) cannot: ``_guide_face`` builds a fresh
        ``FreeTypeFont`` on every call rather than caching one.
        """
        original = ImageDraw.ImageDraw.text
        entry_px = type_px(TOC_ENTRY_PT, generator.dpi)
        calls: List[Tuple[Tuple[float, float], str, Optional[str]]] = []

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            anchor = kwargs.get("anchor")
            if getattr(font, "size", None) == entry_px and anchor not in ("rb", "lb"):
                calls.append((xy, text, anchor))
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        generator.create_toc_page(entries, 3)
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
        return calls

    def test_every_dot_run_clears_the_label_and_the_number(self, monkeypatch) -> None:
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
        font = _guide_face(type_px(TOC_ENTRY_PT, DPI))
        gap = type_px(TOC_ENTRY_GAP_PT, DPI)

        calls = self._drawn(generator, entries, monkeypatch)
        rows: Dict[float, Dict[str, Tuple[float, float]]] = {}
        for (x, y), text, anchor in calls:
            width = font.getlength(text)
            kind = "dots" if set(text) == {"."} else ("number" if anchor == "ra" else "label")
            left = x - width if anchor == "ra" else x
            rows.setdefault(y, {})[kind] = (left, left + width)

        numbered = [parts for parts in rows.values() if "number" in parts]
        assert len(numbered) == 5, "five rows carry a page number on this page"
        for parts in numbered:
            assert "dots" in parts, (
                "every one of these rows leaves ample room for leaders"
            )
            label_right = parts["label"][1]
            dot_left, dot_right = parts["dots"]
            number_left = parts["number"][0]
            assert dot_left > label_right, "the dots start clear of the label"
            assert dot_right < number_left, "the dots end clear of the number"
            assert dot_left - label_right >= gap
            assert number_left - dot_right >= 0
            assert parts["label"][0] == frame.left
            assert parts["number"][1] == frame.right

    def test_a_heading_row_draws_no_dots_at_all(self, monkeypatch) -> None:
        generator = BookPDFGenerator(_book("card-205-ac6-heading"))

        calls = self._drawn(generator, [TocEntry("Easy")], monkeypatch)
        entry_texts = [text for _, text, _ in calls]

        assert entry_texts == ["Easy"], (
            "a heading has no number, so there is nothing to lead to"
        )

    @staticmethod
    def _label_filling(font, room: float) -> str:
        """The longest label that fits ``room`` and leaves under a dot's width.

        Filled in two passes — wide glyphs first, then the narrowest one the
        face draws — because "as many ``W`` glyphs as fit" does not state the
        premise these two tests need: it leaves whatever the *last* ``W``
        could not use, which on the packaged face is 16 px against a 13 px
        dot, so a dot still fitted and the "no room at all" edge was never
        reached (CARD-221 — the premise held on Arial by its own metrics, not
        by construction). Topping the row up with the narrow glyph closes the
        remainder to under one dot, and the assertion below says so rather
        than trusting it, on whatever face the page is lettered in.
        """
        label = "W"
        while font.getlength(label + "W") <= room:
            label += "W"
        while font.getlength(label + "i") <= room:
            label += "i"
        assert font.getlength(label) <= room, "the label must fit the row"
        assert room - font.getlength(label) < font.getlength("."), (
            f"{room - font.getlength(label):.0f} px of the row is still "
            f"unfilled and a dot is {font.getlength('.'):.0f} px wide: this "
            "label does not fill the row the way these tests need it to"
        )
        return label

    def test_a_label_that_leaves_no_room_gets_no_dot(self, monkeypatch) -> None:
        """AC-6's own edge: fill the row, and the leaders simply disappear.

        The label is sized against the real frame so it fills everything the
        number and the two clearances leave — the row still prints both its
        parts, with no dot between them and no overlap either.
        """
        generator = BookPDFGenerator(_book("card-205-ac6-tight"))
        frame = page_frame(generator.page_spec(3))
        font = _guide_face(type_px(TOC_ENTRY_PT, DPI))
        gap = type_px(TOC_ENTRY_GAP_PT, DPI)
        room = (frame.right - frame.left) - font.getlength("86") - 2 * gap

        label = self._label_filling(font, room)

        calls = self._drawn(generator, [TocEntry(label, 86)], monkeypatch)
        texts = [text for _, text, _ in calls]

        assert texts == [label, "86"], (
            f"a label {font.getlength(label):.0f} px wide in {room:.0f} px of "
            "room leaves under a dot's width; no dot may be drawn"
        )

    def test_a_nearly_full_row_still_gets_the_dots_that_do_fit(
        self, monkeypatch
    ) -> None:
        """The other side of the same edge, so "no dots" is not the only
        behaviour the implementation can produce — and the run is as long as
        the gap allows, not merely short.

        Swept over a range of label lengths rather than one hand-tuned one:
        the label grows a character at a time from "comfortably short" to
        "no room at all", and at every step the dot run must be **maximal** —
        drawn if and only if one more dot would not fit. That is the
        clipping rule stated as a property, which neither a run that stops
        one dot early nor one that overruns the number can satisfy. A
        minimum number of cases is asserted inside the test so the sweep
        cannot silently shrink (CLAUDE.md).
        """
        generator = BookPDFGenerator(_book("card-205-ac6-nearly-full"))
        frame = page_frame(generator.page_spec(3))
        font = _guide_face(type_px(TOC_ENTRY_PT, DPI))
        gap = type_px(TOC_ENTRY_GAP_PT, DPI)
        number_width = font.getlength("86")
        room = (frame.right - frame.left) - number_width - 2 * gap

        longest = self._label_filling(font, room)

        with_dots = 0
        without_dots = 0
        for length in range(max(0, len(longest) - 40), len(longest) + 1):
            trimmed = longest[:length]
            calls = self._drawn(generator, [TocEntry(trimmed, 86)], monkeypatch)
            dots = [text for _, text, _ in calls if text and set(text) == {"."}]
            run = room - font.getlength(trimmed)

            if dots:
                with_dots += 1
                assert font.getlength(dots[0]) <= run, (
                    f"{len(dots[0])} dots do not fit {run:.0f} px of gap"
                )
                assert font.getlength(dots[0] + ".") > run, (
                    "one more dot would still have fitted: the run is not "
                    "clipped to the gap, it is short of it"
                )
            else:
                without_dots += 1
                assert font.getlength(".") > run, (
                    f"{run:.0f} px of gap holds a dot, but none was drawn"
                )

        assert with_dots >= 20, f"only {with_dots} label lengths drew leaders"
        assert without_dots >= 1, (
            "the sweep must reach the no-room-at-all end of the range too"
        )


# --------------------------------------------------------------------------
# AC-1/AC-6, the owner's 2026-10-14 decision: the groups are set apart
# --------------------------------------------------------------------------


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
        monkeypatch: pytest.MonkeyPatch,
        page_number: int = 3,
    ) -> List[float]:
        """Each drawn row's own ``y``, one per row, in draw order.

        Spies ``ImageDraw.text`` the same way AC-6's own ``_drawn`` does and
        for the same reason (a row's position is only visible in what was
        drawn), separating the page's title and its folio out by the same
        two marks: the title is set in a much larger face, the folio is
        anchored ``"rb"``/``"lb"``. A row draws up to three marks (label,
        leaders, number) at one ``y``, so consecutive repeats collapse —
        rows run strictly down the page, which the tests below also assert.
        """
        original = ImageDraw.ImageDraw.text
        entry_px = type_px(TOC_ENTRY_PT, generator.dpi)
        tops: List[float] = []

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            anchor = kwargs.get("anchor")
            if getattr(font, "size", None) == entry_px and anchor not in ("rb", "lb"):
                if not tops or xy[1] != tops[-1]:
                    tops.append(xy[1])
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        generator.create_toc_page(entries, page_number)
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
        return tops

    @staticmethod
    def _steps() -> Tuple[int, int]:
        """``(one row's step, a group opener's own step)`` in px at ``DPI``."""
        font = _guide_face(type_px(TOC_ENTRY_PT, DPI))
        ascent, descent = font.getmetrics()
        line = ascent + descent + type_px(TOC_ENTRY_GAP_PT, DPI)
        return line, line + type_px(TOC_GROUP_GAP_PT, DPI)

    @classmethod
    def _expected(cls, entries: List[TocEntry]) -> List[int]:
        """The step each row should sit below its predecessor, in draw order.

        Read off the rows' own ``starts_group`` flags — the one place these
        tests state what the drawing is supposed to do, so a case added
        below cannot disagree with the rule by hand-writing its steps.
        """
        line, group_step = cls._steps()
        return [group_step if entry.starts_group else line for entry in entries[1:]]

    def test_each_group_opener_sits_further_below_than_an_ordinary_row(
        self, monkeypatch
    ) -> None:
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

        tops = self._row_tops(generator, entries, monkeypatch)

        assert len(tops) == len(entries), (
            f"eight rows were handed to the page, {len(tops)} were drawn"
        )
        steps = [after - before for before, after in zip(tops, tops[1:])]
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

    def test_the_solutions_row_opens_its_own_group_though_it_is_numbered(
        self, monkeypatch
    ) -> None:
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

        tops = self._row_tops(generator, entries, monkeypatch)

        hard_range_step = tops[-2] - tops[-3]
        solutions_step = tops[-1] - tops[-2]
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
            tops[index] - tops[index - 1]
            for index, e in enumerate(entries)
            if e.is_heading
        }
        assert heading_steps == {solutions_step}, (
            f"the solutions' own separation ({solutions_step} px) must be "
            f"the same one the three headings get ({sorted(heading_steps)}), "
            "one group separation and not two"
        )
        assert len(headings) == 3

    def test_a_one_level_books_group_openers_are_set_off_too(
        self, monkeypatch
    ) -> None:
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

        tops = self._row_tops(generator, entries, monkeypatch)

        assert len(tops) == 4
        steps = [after - before for before, after in zip(tops, tops[1:])]
        assert steps[0] > steps[1], (
            f"the single heading must still be set off from the guide row "
            f"above it ({steps[0]} px of white against {steps[1]} px below it)"
        )
        assert steps[2] > steps[1], (
            f"and so must the solutions row below the only range row "
            f"({steps[2]} px against {steps[1]} px)"
        )
        assert steps == [group_step, line, group_step] == self._expected(entries)

    def test_the_gap_never_pads_the_top_of_a_page(self, monkeypatch) -> None:
        """A page whose first row opens a group starts where any page does.

        The gap separates two groups; above the first row of a page there is
        no group to separate from, and the room it would spend there is
        exactly the room ``_toc_entries_per_page`` reserves for the folio
        (G-1). The structural list never opens a page with such a row — its
        first row is the guide — but ``create_toc_page`` draws what it is
        handed, so the rule is pinned rather than assumed.

        Asserted for **both** kinds of opener since Fix 2: an unnumbered
        heading and the numbered solutions row, so a suppression written
        against ``is_heading`` rather than the flag is caught here too.
        """
        generator = BookPDFGenerator(_book("card-205-fix2-top-of-page"))

        numbered_first = self._row_tops(generator, [TocEntry(GUIDE_TITLE, 1)], monkeypatch)
        heading_first = self._row_tops(
            generator, [TocEntry("Easy", None, starts_group=True)], monkeypatch
        )
        solutions_first = self._row_tops(
            generator,
            [TocEntry(TOC_SOLUTIONS_LABEL, 86, starts_group=True)],
            monkeypatch,
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

        **This test has already caught the thing it exists for.** At Fix 1's
        ``TOC_GROUP_GAP_PT`` of 10 pt the fourth gap put the worst case at
        31 px against the folio's 49 — the page would have gone out
        unnumbered on the two shortest storable trims — which is why the
        constant is 8.5 pt and why the worst case is asserted as a *figure*
        below and not only as an inequality: an inequality is satisfied by
        1 px of margin just as well as by 10, and the next card to add a row
        or a gap should be told how much room it is actually spending.

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

        **At the shipped 8.5 pt the 10.00 cm trim is 2 px short, and this
        test says so by failing.** Measured on the packaged face (CARD-221,
        2026-10-14): that trim's TOC frame is 956 px tall, the title's line
        and gap take 258, eight rows at 66 px apiece and their four 35 px
        gaps take the rest, and **47 px** are left where the folio's own
        line needs **49** — so ``create_toc_page`` on a 10.00 cm book draws
        no folio at all (rendered and spied, not computed: see the test
        below this one). Every other height KDP admits clears it, 10.10 cm
        included at 58 px; 10.00 cm is the one failing height of the 381
        this sweep measures, where on Pillow's built-in face (the off-host
        fallback until CARD-221) both 10.00 and 10.10 failed, at 27 and
        38 px.

        What closes it is the owner's own constant, exactly as CARD-205
        recorded when the same inequality was red off-host: on this face
        **8.2 pt (34 px) is the largest gap that fits**, and 8.0 pt (33 px)
        restores a 6 px margin over the folio — the same "largest that fits,
        less a margin" rule the owner applied to Arial's metrics when they
        chose 8.5 over 8.9. CARD-221 is forbidden that change (its G-6) and
        records the measurement here instead. The alternative the owner may
        prefer — a narrower packaged face — is an ADR-0006/R1 question, not
        a constant.
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
        # Every trim but the shortest storable one clears the folio's line,
        # and the one that does not is 2 px short — the figures, not merely
        # the inequality, because an inequality is satisfied by 1 px of
        # margin as well as by 10 and the next card to add a row or a gap
        # should be told what it is spending. Ungated since CARD-221: these
        # are the packaged face's metrics, which every host now letters in.
        assert [height for height, _ in short] == ["10.00"], (
            "the shortest storable trim is the one height whose folio the "
            f"shipped gap does not leave room for, and the sweep found {short} "
            "— a second height means the gaps have eaten the reservation "
            "`_toc_entries_per_page` makes for the folio (G-1) somewhere new"
        )
        assert worst[0] == 47, (
            f"the worst-case headroom is {worst[0]} px, recorded as 47 "
            "(CARD-221, 10.00 cm trim on the packaged face: 187 px under "
            "eight rows less four 35 px gaps; it was 59 px on Arial, the "
            "host face the interior letterd in until that card). It must "
            f"not drift further below the folio's {folio_line} px without "
            "the move being deliberate"
        )
        assert folio_line - worst[0] == 2, (
            "and the deficit is 2 px: what the owner's 8.5 pt costs the "
            "10.00 cm trim's page number on the deterministic face. 8.2 pt "
            "is the largest gap that fits it, 8.0 pt restores a 6 px margin "
            "— CARD-221's G-6 forbids that change and records this figure "
            "for the owner instead"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "KNOWN, MEASURED AND OWNER-BLOCKED (CARD-221, 2026-10-14). On the "
            "packaged face every interior page is now lettered in — which is "
            "what makes a book's page count, and therefore its printed KDP "
            "gutter, the same on this Mac and on the deployed Linux image — a "
            "TOC row is 49 px tall against Arial's 48 and the title's line 258 "
            "px against 254. At the 10.00 cm minimum storable trim the "
            "structural list's eight rows and four 8.5 pt gaps therefore leave "
            "47 px where `_draw_folio` needs 49, and that page prints "
            "unnumbered: 2 px short, on the one shortest height of the 381 "
            "this sweep measures (10.10 cm clears it at 58 px). Before "
            "CARD-221 the same claim was red on any host without Arial, at 27 "
            "px, and green here only because this Mac has Arial -- so the "
            "defect is not new, it is now the same everywhere, which is the "
            "point of that card. What closes it is TOC_GROUP_GAP_PT: 8.2 pt "
            "(34 px) is the largest gap this face fits, 8.0 pt (33 px) leaves "
            "the 6 px margin the owner's own rule would ask for. That "
            "constant is an owner decision (2026-10-14) and CARD-221's G-6 "
            "puts it out of scope, so this marker records the one claim the "
            "card cannot close rather than letting it disappear. Strict: the "
            "moment the gap moves (or a narrower face ships) this test passes "
            "and pytest fails it, which is the signal to delete this marker."
        ),
    )
    def test_the_shortest_storable_trim_leaves_its_folio_a_line_too(self) -> None:
        """The claim the sweep above excludes 10.00 cm from, on its own.

        Split out of that sweep by CARD-221 rather than gated inside it: the
        sweep keeps every assertion that holds (one page on all 381 heights,
        the worst case is the shortest trim, 380 of 381 clear the folio's
        line, and the two exact figures), and this holds the one that does
        not, so a regression anywhere else in the sweep still reds the suite
        instead of being absorbed by this expected failure.
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

        assert room >= folio_ascent + folio_descent, (
            f"the 10.00 cm trim's eight rows and four gaps leave {room} px "
            f"under the last row, and the folio's own line needs "
            f"{folio_ascent + folio_descent} px"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "KNOWN, MEASURED AND OWNER-BLOCKED (CARD-221, 2026-10-14) — the "
            "rendered half of the arithmetic this class's "
            "`test_the_shortest_storable_trim_leaves_its_folio_a_line_too` "
            "carries, whose own marker states the measurement in full. On the "
            "packaged face the 10.00 cm trim's structural TOC leaves 47 px "
            "under its last row where `_draw_folio` needs 49, so this page "
            "really does go out unnumbered and `folios` below is drawn empty. "
            "The 10.10 cm trim -- the next height a book can store, and the "
            "tightest one the shipped gap still numbers -- is rendered and "
            "asserted by the test that follows this one, so the drawing-level "
            "guard is not lost while this claim is blocked. Strict: it fails "
            "the moment TOC_GROUP_GAP_PT moves below 8.2 pt and the page is "
            "numbered again."
        ),
    )
    def test_the_shortest_trim_still_prints_its_folio_with_the_gaps_in_place(
        self, monkeypatch
    ) -> None:
        """The same claim on the real drawing, on the one trim that can fail it.

        The sweep above is arithmetic; this renders the worst case — the
        shortest trim ``book_page_spec`` lays out at all, where the eight
        rows and three gaps leave the least room — and asserts
        ``_draw_folio`` really drew. It is the direct test of the omission
        the reservation exists to prevent: ``_draw_folio`` returns without
        drawing when the content it is told about leaves no room for its
        own line, so a folio-anchored mark either happened or the page went
        out unnumbered.
        """
        book = _book("card-205-fix2-shortest-trim")
        book.trim_height_cm = "10.00"
        generator = BookPDFGenerator(book)
        entries = _structural_shape(
            ("Easy", "Puzzles 1–60", 5),
            ("Medium", "Puzzles 61–120", 37),
            ("Hard", "Puzzles 121–150", 69),
            solutions_page=86,
        )
        assert sum(entry.starts_group for entry in entries) == 4, (
            "this test's premise: all four gaps are in play, which is the "
            "load the 10.00 cm trim is the only one that can fail under"
        )
        frame = page_frame(generator.page_spec(3))
        book1_frame = page_frame(BookPDFGenerator(_book()).page_spec(3))
        assert (frame.bottom - frame.top) < (book1_frame.bottom - book1_frame.top), (
            "this test's premise: a 10 cm trim's usable height is tighter "
            "than the Book 1 profile every other test in this file uses"
        )

        original = ImageDraw.ImageDraw.text
        folios: List[str] = []
        rows: List[float] = []
        entry_px = type_px(TOC_ENTRY_PT, generator.dpi)

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            anchor = kwargs.get("anchor")
            if anchor in ("rb", "lb"):
                folios.append(text)
            elif getattr(font, "size", None) == entry_px:
                rows.append(xy[1])
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        generator.create_toc_page(entries, 3)
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        assert folios == ["3"], (
            "the shortest trim's TOC page must still carry its folio with "
            f"the group gaps in place, and drew {folios}"
        )
        font = _guide_face(entry_px)
        ascent, descent = font.getmetrics()
        headroom = frame.bottom - (max(rows) + ascent + descent)
        assert headroom >= 0, "the last row's own ink must stay inside the frame"
        # The recorded worst case, read off the real drawing instead of off
        # this file's own arithmetic, is asserted in the test below rather
        # than here (CARD-221): this test is expected to fail, and a pinned
        # figure inside it would keep it failing after the gap that blocks
        # it is fixed — which would make its own `strict` promise false.

    def test_the_shortest_trim_the_shipped_gap_numbers_prints_its_folio(
        self, monkeypatch
    ) -> None:
        """The rendered guard, on the tightest trim that can still pass it.

        10.10 cm: the next height a book can store above
        ``MIN_TRIM_CM``, and — on the packaged face every interior page is
        lettered in since CARD-221 — the tightest one whose structural TOC
        still leaves the folio its own line (58 px against the 49 it needs,
        where 10.00 cm leaves 47). Added by that card so that the omission
        ``_toc_entries_per_page``'s reservation exists to prevent is still
        caught *on a drawn page* while the 10.00 cm claim above is blocked
        on the owner's own ``TOC_GROUP_GAP_PT``: without this, the
        drawing-level half of the guard would have gone from green to
        expected-failure with nothing left asserting it.
        """
        book = _book("card-221-tightest-numbered-trim")
        book.trim_height_cm = "10.10"
        generator = BookPDFGenerator(book)
        entries = _structural_shape(
            ("Easy", "Puzzles 1–60", 5),
            ("Medium", "Puzzles 61–120", 37),
            ("Hard", "Puzzles 121–150", 69),
            solutions_page=86,
        )
        assert sum(entry.starts_group for entry in entries) == 4, (
            "this test's premise: all four gaps are in play"
        )
        frame = page_frame(generator.page_spec(3))
        shortest = _book("card-221-shortest-trim")
        shortest.trim_height_cm = "10.00"
        shortest_frame = page_frame(BookPDFGenerator(shortest).page_spec(3))
        assert (shortest_frame.bottom - shortest_frame.top) < (frame.bottom - frame.top), (
            "this test's premise: 10.10 cm is the tighter-but-one trim, so "
            "only the 10.00 cm page above is expected to lose its folio"
        )

        original = ImageDraw.ImageDraw.text
        folios: List[str] = []
        rows: List[float] = []
        entry_px = type_px(TOC_ENTRY_PT, generator.dpi)

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            anchor = kwargs.get("anchor")
            if anchor in ("rb", "lb"):
                folios.append(text)
            elif getattr(font, "size", None) == entry_px:
                rows.append(xy[1])
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        generator.create_toc_page(entries, 3)
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        assert folios == ["3"], (
            "the tightest trim the shipped gap numbers must carry its folio "
            f"with the group gaps in place, and drew {folios}"
        )
        ascent, descent = _guide_face(entry_px).getmetrics()
        headroom = frame.bottom - (max(rows) + ascent + descent)
        assert headroom == 58, (
            f"the drawn page leaves {headroom} px under its last row, "
            "recorded as 58 — 11 px more than the 10.00 cm trim's 47, which "
            "is the 0.10 cm of extra height"
        )

        # And the worst case's own figure, off the drawing rather than off
        # the sweep's arithmetic — two independent routes to one number
        # (CLAUDE.md's preference for a second implementation over
        # re-deriving a value). It lives here, in a test that is expected to
        # pass, rather than inside the expected-failure above: this is a
        # measurement of where the last row lands and says nothing about
        # whether the folio was drawn, which is that test's own claim.
        shortest_rows: List[float] = []

        def shortest_spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            if getattr(font, "size", None) == entry_px and kwargs.get("anchor") not in ("rb", "lb"):
                shortest_rows.append(xy[1])
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", shortest_spy)
        BookPDFGenerator(shortest).create_toc_page(entries, 3)
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        shortest_headroom = shortest_frame.bottom - (
            max(shortest_rows) + ascent + descent
        )
        assert shortest_headroom == 47, (
            f"the 10.00 cm trim's drawn page leaves {shortest_headroom} px "
            "under its last row, recorded as 47 — the sweep's own worst "
            "case, measured here through `create_toc_page` rather than "
            f"computed, and 2 px short of the {sum(_guide_face(entry_px).getmetrics())} "
            "px the folio's line needs"
        )


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

    def test_the_interior_of_an_empty_book_is_the_guide_alone(self) -> None:
        """No TOC page, and therefore no page numbered for one."""
        generator = BookPDFGenerator(_book("card-205-ac7-interior"))

        stream = generator.interior_stream([])

        assert stream.page_count == GUIDE_PAGE_COUNT
        assert len(list(stream.pages)) == GUIDE_PAGE_COUNT


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
        # `interior_stream`'s own arithmetic for the SOLUTIONS divider:
        # `first_answer_page - 1`, where `first_answer_page` is
        # `1 + GUIDE_PAGE_COUNT + toc_page_count + len(section) + 1`.
        solutions_page = (
            1 + GUIDE_PAGE_COUNT + decided.toc_page_count + len(decided.pages)
        )
        entries = structural_toc_entries(
            decided.pages, decided.payloads, solutions_page
        )
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
        # one solutions row. Written out rather than taken from the function
        # under test, so a builder that lost a row fails here.
        assert len(entries) == 1 + 2 * levels + 1
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
        assert structural_toc_entry_count(3, 150) == 8
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

        def one_row_short(level_count: int, puzzle_count: int) -> int:
            return 0 if puzzle_count == 0 else 1 + 2 * level_count

        monkeypatch.setattr(module, "structural_toc_entry_count", one_row_short)
        generator = BookPDFGenerator(_book("card-205-f003-rows"))

        with pytest.raises(RuntimeError) as raised:
            generator.interior_stream(_puzzles(easy=3))
        message = str(raised.value)

        assert "built 4 row(s)" in message, (
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

        assert calls == [4, 4], (
            "this test's premise: the plan and the draw each measure the "
            f"same four rows, and only the second answer is widened: {calls}"
        )
        assert "4 row(s) need 2 page(s)" in message, message
        assert "laid out on 1" in message, (
            f"the figure the book's own page numbers rest on must be named: {message}"
        )
