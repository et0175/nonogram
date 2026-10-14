"""CARD-205 — the table of contents lists sections, not puzzles.

    AC-1  TestBookToc_ListsSectionsNotPuzzles
    AC-2  TestBookToc_PageNumbersMatchTheWalk
    AC-3  TestBookToc_RangeRowsFollowTheLevelRuns
    AC-4  TestBookToc_SkipsEmptyLevels
    AC-5  TestBookToc_KdpAgreesWithTheExportedCount
    AC-6  TestBookToc_LeaderDotsStayInsideTheGap
    AC-7  TestBookToc_EmptyBookHasNoTocPage

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
from nonogram.admin.book_pdf_generator import (
    DPI,
    GUIDE_PAGE_COUNT,
    GUIDE_TITLE,
    TOC_ENTRY_GAP_PT,
    TOC_ENTRY_PT,
    TOC_SOLUTIONS_LABEL,
    BookPDFGenerator,
    DividerPagePlan,
    PuzzlePagePlan,
    TocEntry,
    _guide_face,
    measured_toc_page_count,
    page_frame,
    type_px,
)
from tests.helpers.book_corpus import corpus_book, puzzle

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

        label = "W"
        while font.getlength(label + "W") <= room:
            label += "W"
        assert font.getlength(label) <= room < font.getlength(label + "W")

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

        label = "Wi"
        while font.getlength(label) <= room:
            label += "Wi"
        longest = label[:-2]

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
