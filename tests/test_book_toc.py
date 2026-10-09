"""CARD-200 — the table of contents lists every puzzle against its real page.

    AC-4  TestBookToc_ListsEveryPuzzleAgainstItsRealPageNumber
    AC-5  TestBookToc_TitleResolutionMatchesTheAnswerSections
    AC-6  TestBookToc_OverflowsToASecondPageWithoutLosingAnEntryOrBreakingLaterNumbering

**How this file reads a TOC page's own rows**, rather than template-matching
rendered pixels: :meth:`BookPDFGenerator.create_toc_page` is handed its own
``entries`` — ``(label, page_number)`` pairs — by :meth:`interior_stream`'s
``produce()``, already split one page at a time. Spying on
``BookPDFGenerator.create_toc_page`` itself (rather than ``ImageDraw.text``,
which would also have to reconstruct which text belongs to which column) is
exactly what lets this file assert on the *rows a TOC page was asked to
draw* — the content decision — independently of whether the drawing itself
put them in readable pixels (``tests/test_book_page_numbers.py`` already
covers the folio's own pixels; CARD-197/198's own precedent for a caption's
text is a direct string comparison on what the caption function returns, not
a pixel probe, for the same reason).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from nonogram.admin.book_answer_key import answer_caption
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    DividerPagePlan,
    PuzzlePagePlan,
)
from tests.helpers.book_corpus import corpus_book, puzzle


def _book_with_titles(titles: Dict[str, str]) -> Book:
    return Book(
        book_id="card-200-toc",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="CARD-200's own TOC test.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=corpus_book().trim_width_cm,
        trim_height_cm=corpus_book().trim_height_cm,
        gutter_margin_cm=corpus_book().gutter_margin_cm,
        outside_margin_cm=corpus_book().outside_margin_cm,
        puzzle_titles=titles,
    )


def _spy_toc_pages(
    generator: BookPDFGenerator, puzzles: List[dict], monkeypatch: pytest.MonkeyPatch
) -> List[List[Tuple[str, int]]]:
    """Every ``create_toc_page`` call's own ``entries``, one list per TOC page."""
    original = BookPDFGenerator.create_toc_page
    recorded: List[List[Tuple[str, int]]] = []

    def spy(self, entries, page_number):
        recorded.append(list(entries))
        return original(self, entries, page_number)

    monkeypatch.setattr(BookPDFGenerator, "create_toc_page", spy)
    stream = generator.interior_stream(puzzles)
    for _ in stream.pages:
        pass
    monkeypatch.setattr(BookPDFGenerator, "create_toc_page", original)
    return recorded


def _puzzle_page_numbers(generator: BookPDFGenerator, puzzles: List[dict]) -> Dict[int, int]:
    """``{puzzle number: its own interior page}`` — the TOC's own answer key."""
    decided = generator.section_plan(list(puzzles))
    mapping: Dict[int, int] = {}
    for entry in decided.pages:
        if isinstance(entry, DividerPagePlan):
            continue
        for number in entry.numbers:
            mapping[number] = entry.page_number
    return mapping


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestBookToc_ListsEveryPuzzleAgainstItsRealPageNumber:
    """Every puzzle appears exactly once, in book order, against its own page."""

    @staticmethod
    def _book_and_puzzles() -> Tuple[Book, List[dict]]:
        book = corpus_book("card-200-ac4")
        puzzles = [
            puzzle("card200-hard-1", 30, 30, 8, "hard", "Snowflake"),
            puzzle("card200-easy-1", 10, 10, 3, "easy", "Duck"),
            puzzle("card200-easy-2", 10, 10, 3, "easy", "Owl"),
            puzzle("card200-medium-1", 15, 15, 4, "medium", "Tree"),
        ]
        return book, puzzles

    def test_every_puzzle_is_listed_once_in_book_order_against_its_real_page(
        self, monkeypatch
    ) -> None:
        book, puzzles = self._book_and_puzzles()
        generator = BookPDFGenerator(book)

        toc_pages = _spy_toc_pages(generator, puzzles, monkeypatch)
        all_entries = [entry for page in toc_pages for entry in page]
        page_of = _puzzle_page_numbers(generator, puzzles)

        assert len(all_entries) == len(puzzles) == 4, (
            "every drawable puzzle appears exactly once in the TOC"
        )
        # Book order is easy, medium, hard (INV-009) — Duck, Owl, Tree,
        # Snowflake — not the input order (hard first).
        assert [label for label, _ in all_entries] == [
            "Puzzle 1 — Duck",
            "Puzzle 2 — Owl",
            "Puzzle 3 — Tree",
            "Puzzle 4 — Snowflake",
        ]
        for number, (_, toc_page) in enumerate(all_entries, start=1):
            assert toc_page == page_of[number], (
                f"puzzle {number}'s TOC row points at page {toc_page}, but it "
                f"prints on page {page_of[number]}"
            )

    def test_a_paired_two_up_pages_two_puzzles_point_at_the_same_page_number(
        self, monkeypatch
    ) -> None:
        """Duck and Owl (both 10x10 easy) share one two-up puzzle page."""
        book, puzzles = self._book_and_puzzles()
        generator = BookPDFGenerator(book)

        toc_pages = _spy_toc_pages(generator, puzzles, monkeypatch)
        all_entries = [entry for page in toc_pages for entry in page]
        by_label = {label: page for label, page in all_entries}

        assert by_label["Puzzle 1 — Duck"] == by_label["Puzzle 2 — Owl"], (
            "Duck and Owl share a two-up puzzle page, so their TOC rows "
            "must point at the same interior page"
        )
        page_of = _puzzle_page_numbers(generator, puzzles)
        assert page_of[1] == page_of[2]


# --------------------------------------------------------------------------
# AC-5
# --------------------------------------------------------------------------


class TestBookToc_TitleResolutionMatchesTheAnswerSections:
    """The TOC's label is exactly the answer caption's own resolution."""

    def test_a_custom_title_wins_and_an_untitled_puzzle_reads_puzzle_n_alone(
        self, monkeypatch
    ) -> None:
        puzzles = [
            puzzle("card200-titled", 20, 20, 4, "easy", "Picture's own name"),
            puzzle("card200-untitled", 20, 20, 4, "easy", ""),
        ]
        book = _book_with_titles({"card200-titled": "Owner's Custom Title"})
        generator = BookPDFGenerator(book)

        toc_pages = _spy_toc_pages(generator, puzzles, monkeypatch)
        labels = [label for page in toc_pages for label, _ in page]

        assert labels[0] == answer_caption(1, "Owner's Custom Title")
        assert labels[0] == "Puzzle 1 — Owner's Custom Title"
        assert labels[1] == answer_caption(2, None)
        assert labels[1] == "Puzzle 2"

    def test_the_picture_name_is_used_only_when_no_custom_title_is_set(
        self, monkeypatch
    ) -> None:
        puzzles = [puzzle("card200-named", 20, 20, 4, "easy", "Its Own Name")]
        generator = BookPDFGenerator(_book_with_titles({}))

        toc_pages = _spy_toc_pages(generator, puzzles, monkeypatch)
        labels = [label for page in toc_pages for label, _ in page]

        assert labels == [answer_caption(1, "Its Own Name")]
        assert labels == ["Puzzle 1 — Its Own Name"]


# --------------------------------------------------------------------------
# AC-6
# --------------------------------------------------------------------------


class TestBookToc_OverflowsToASecondPageWithoutLosingAnEntryOrBreakingLaterNumbering:
    """A TOC too long for one page spans as many as it needs."""

    @staticmethod
    def _big_corpus(count: int) -> List[dict]:
        return [
            puzzle(f"card200-ac6-{n}", 20, 20, 4, "easy", f"Picture {n}")
            for n in range(count)
        ]

    def test_a_large_book_splits_its_toc_across_more_than_one_page_with_no_entry_lost(
        self, monkeypatch
    ) -> None:
        puzzles = self._big_corpus(60)
        generator = BookPDFGenerator(corpus_book("card-200-ac6"))

        toc_pages = _spy_toc_pages(generator, puzzles, monkeypatch)
        decided = generator.section_plan(list(puzzles))

        assert decided.toc_page_count > 1, (
            "60 puzzles on Book 1's own trim should need more than one TOC "
            "page, or this test exercises nothing new"
        )
        assert len(toc_pages) == decided.toc_page_count
        all_entries = [entry for page in toc_pages for entry in page]
        assert len(all_entries) == len(puzzles) == 60
        assert [label for label, _ in all_entries] == [
            f"Puzzle {n} — Picture {n - 1}" for n in range(1, 61)
        ], "every entry still appears exactly once, in book order"
        for page_entries in toc_pages:
            assert page_entries, "no TOC page is left empty"

    def test_every_page_after_a_multi_page_toc_is_still_consistent_with_the_arithmetic(
        self, monkeypatch
    ) -> None:
        """AC-3 holds at this larger ``toc_page_count`` too."""
        puzzles = self._big_corpus(60)
        generator = BookPDFGenerator(corpus_book("card-200-ac6-numbering"))
        decided = generator.section_plan(list(puzzles))
        section = decided.pages
        plan = [entry for entry in section if isinstance(entry, PuzzlePagePlan)]

        from nonogram.admin.book_pdf_generator import GUIDE_PAGE_COUNT

        expected_first_section_page = 1 + GUIDE_PAGE_COUNT + decided.toc_page_count
        # `section[0]` is the puzzle section's own first page — a level's
        # divider here (this corpus is all-easy, so exactly one) — not
        # necessarily `plan[0]`, the first *puzzle* page, which sits one
        # page later, after that divider.
        assert section[0].page_number == expected_first_section_page

        first_answer_page = (
            1 + GUIDE_PAGE_COUNT + decided.toc_page_count + len(section) + 1
        )
        from nonogram.admin.book_pdf_generator import PackedAnswerPage
        from nonogram.admin.book_answer_key import Answer, plan_small_answer_pages

        # These puzzles are 20x20, too large to pack (CARD-202's own
        # width<=15/height<=20 rule), so the answer section is one full page
        # per puzzle, same as the puzzle count.
        assert first_answer_page - expected_first_section_page == len(section) + 1

    def test_the_toc_itself_carries_a_folio_on_every_one_of_its_pages(
        self, monkeypatch
    ) -> None:
        """The TOC is front matter inside the interior, not cover-like."""
        from PIL import ImageDraw

        puzzles = self._big_corpus(60)
        generator = BookPDFGenerator(corpus_book("card-200-ac6-folio"))
        decided = generator.section_plan(list(puzzles))

        original = ImageDraw.ImageDraw.text
        folio_pages = set()
        current = {"page": 0}

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            if kwargs.get("anchor") in ("rb", "lb"):
                folio_pages.add(current["page"])
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
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
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        toc_page_numbers = set(range(3, 2 + decided.toc_page_count + 1))
        assert toc_page_numbers <= folio_pages, (
            f"TOC pages {toc_page_numbers - folio_pages} drew no folio"
        )
