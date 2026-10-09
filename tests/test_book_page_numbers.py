"""CARD-200 — every interior page carries its own page number; the cover never does.

    AC-1  TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber
    AC-2  TestBookPageNumbers_CoverIsNeverNumbered
    AC-3  TestBookPageNumbers_FoliosMatchInteriorStreamsOwnArithmetic
    AC-9  TestBookPageNumbers_ParityHoldsWithTheTocInserted

**What a "folio" is, and how this file finds one.** ``_draw_folio``
(``book_pdf_generator.py``) is the *only* ``draw.text`` call anywhere in this
module that passes Pillow's ``"rb"``/``"lb"`` anchor — every other mark this
module draws (a title, a band, a caption, a TOC entry's own label or its
right-aligned page number) uses a different anchor or none at all (see that
module's own call sites: the caption is ``"mm"``, the band is ``"lm"``, a TOC
entry's page number is ``"ra"``, a TOC entry's label and every guide/divider
mark use the default). So a ``draw.text`` call recorded with anchor ``"rb"``
or ``"lb"`` is unambiguously the folio, and its own ``text`` is checked
against the exact page number it was drawn for — this file never greps
rendered pixels for a digit the way ``test_book_guide_page.py``'s ``probe``/
``occurrences`` do, which is a second, independent way of finding the same
mark (CLAUDE.md's "prefer an independent second implementation" — the spy
below reads *which call Pillow actually made*, not a template match that
could in principle agree with a wrong implementation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pytest
from PIL import ImageDraw

from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    page_is_right_hand,
)
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, puzzle

#: The two anchors ``_draw_folio`` uses, and only it (see module docstring).
_FOLIO_ANCHORS = {"rb", "lb"}

#: The smallest trim a book may be stored with
#: (``book_page_spec.MIN_TRIM_CM``), written out rather than imported — the
#: same 10x10 cm/tight-margin book ``tests/test_book_interior_type_floor.py``
#: already measured to leave the solved-answer page's caption no slack at
#: all. Used here for AC-1's "except a page whose slack is too small" clause.
_MIN_TRIM_CM = 10.0
_MIN_TRIM_GUTTER_CM = "0.95"
_MIN_TRIM_OUTSIDE_CM = "0.64"


def _min_trim_book() -> Book:
    return Book(
        book_id="card-200-min-trim",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="CARD-200's own min-trim folio test.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{_MIN_TRIM_CM:.2f}",
        trim_height_cm=f"{_MIN_TRIM_CM:.2f}",
        gutter_margin_cm=_MIN_TRIM_GUTTER_CM,
        outside_margin_cm=_MIN_TRIM_OUTSIDE_CM,
    )


@dataclass(frozen=True)
class _TextCall:
    """One ``draw.text`` call, tagged by the interior page it was drawn for."""

    page: int
    text: str
    anchor: Optional[str]


def _spy_interior(
    generator: BookPDFGenerator, puzzles: List[dict], monkeypatch: pytest.MonkeyPatch
) -> Tuple[List[_TextCall], int]:
    """Every ``draw.text`` call one interior export makes, tagged by page.

    The same "spy on ``ImageDraw.text`` while walking ``interior_stream``,
    tag by the page index the walk is up to" technique
    ``tests/test_book_interior_type_floor.py``'s own ``record_interior``
    already uses, narrowed to just what this file needs (text and anchor,
    not font size/chain).
    """
    original = ImageDraw.ImageDraw.text
    calls: List[_TextCall] = []
    current = {"page": 0}

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        calls.append(_TextCall(current["page"], str(text), kwargs.get("anchor")))
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
    assert drawn == stream.page_count
    return calls, drawn


def _folios(calls: List[_TextCall]) -> dict:
    """``{page: folio text}`` — the one ``_draw_folio`` call per page, if any."""
    found: dict = {}
    for call in calls:
        if call.anchor in _FOLIO_ANCHORS:
            assert call.page not in found, f"page {call.page} drew two folios"
            found[call.page] = call.text
    return found


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber:
    """Every interior page kind carries its own plain-decimal folio."""

    def test_every_page_of_a_book_holding_one_of_every_kind_is_numbered(
        self, monkeypatch
    ) -> None:
        """The baseline book: guide x2, TOC, 3 dividers incl. SOLUTIONS, a
        two-up page, a single-puzzle page, a packed-2-up answer page, a
        packed-alone answer page and a full answer page — one of every kind
        this module can draw (``tests/helpers/book_corpus.py``'s own
        docstring).
        """
        generator = BookPDFGenerator(corpus_book())
        calls, drawn = _spy_interior(generator, baseline_puzzles(), monkeypatch)
        folios = _folios(calls)

        assert set(folios) == set(range(1, drawn + 1)), (
            "every interior page should carry exactly one folio; missing or "
            f"extra pages: {set(range(1, drawn + 1)) ^ set(folios)}"
        )
        for page, text in folios.items():
            assert text == str(page), (
                f"page {page}'s folio reads {text!r}, not its own number"
            )
            assert text.isdigit() and not text.startswith("0"), (
                f"page {page}'s folio {text!r} is not a plain decimal"
            )
            assert "Page" not in text, "the folio carries no word, only the number"

    def test_a_page_whose_slack_is_too_small_prints_no_folio_rather_than_collide(
        self, monkeypatch
    ) -> None:
        """The min-trim book's lone answer page has no room for the caption
        (``test_book_interior_type_floor.py``'s own finding) — the folio
        shares that exact slack and is omitted for the same reason, not
        drawn on top of the grid.
        """
        generator = BookPDFGenerator(_min_trim_book())
        single = [puzzle("card200-mintrim", 20, 20, 5, "easy", "Solo")]
        calls, drawn = _spy_interior(generator, single, monkeypatch)
        folios = _folios(calls)

        answer_page = drawn  # the one full solved page is always the last
        assert answer_page not in folios, (
            "the min-trim book's answer page has no slack for a caption "
            "(CARD-197) and so none for a folio either — one must have been "
            "drawn without checking the room"
        )
        # Most pages on this tiny, single-puzzle book still print their own
        # folio — the omission is specific to pages with no measurable room
        # (the answer page's caption slack; the guide's own tightest
        # fallback form can be another, since both this book's 10 cm trim
        # genuinely leaves no room below their content), not a blanket
        # "min trim never gets folios" bug.
        missing = set(range(1, drawn + 1)) - set(folios)
        assert missing <= {1, answer_page}, (
            f"unexpected pages missing a folio on the min-trim book: {missing}"
        )
        assert len(folios) >= drawn - 2


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestBookPageNumbers_CoverIsNeverNumbered:
    """FR-043's rule, made visibly true: the cover carries no folio anywhere."""

    def test_the_cover_draws_no_folio(self, monkeypatch) -> None:
        calls: List[_TextCall] = []
        original = ImageDraw.ImageDraw.text

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            calls.append(_TextCall(0, str(text), kwargs.get("anchor")))
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        BookPDFGenerator(corpus_book()).create_cover_page("Winter Pictures")
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        assert calls, "the generated cover should draw its title"
        assert not _folios(calls), (
            "the cover page drew a folio — FR-043 says it is never numbered"
        )
        assert all(call.text != "1" for call in calls), (
            "nothing on the cover reads as a bare page number"
        )

    def test_export_books_cover_file_carries_no_folio_either(self, monkeypatch) -> None:
        """The real export path, not just the method called directly."""
        calls: List[_TextCall] = []
        original = ImageDraw.ImageDraw.text

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            calls.append(_TextCall(0, str(text), kwargs.get("anchor")))
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        BookPDFGenerator(corpus_book()).export_cover("Winter Pictures")
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        assert not _folios(calls)


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookPageNumbers_FoliosMatchInteriorStreamsOwnArithmetic:
    """A folio that is present but wrong must fail — not just AC-1's presence check."""

    @staticmethod
    def _two_easy_one_medium() -> List[dict]:
        return [
            puzzle("card200-easy-1", 20, 20, 4, "easy", "Easy 1"),
            puzzle("card200-easy-2", 22, 22, 4, "easy", "Easy 2"),
            puzzle("card200-medium-1", 25, 25, 5, "medium", "Medium 1"),
        ]

    def test_the_solutions_divider_and_first_answer_page_carry_the_exact_numbers(
        self, monkeypatch
    ) -> None:
        book = corpus_book("card-200-ac3")
        generator = BookPDFGenerator(book)
        puzzles = self._two_easy_one_medium()

        decided = generator.section_plan(list(puzzles))
        section = decided.pages
        from nonogram.admin.book_pdf_generator import GUIDE_PAGE_COUNT

        solutions_page = 2 + decided.toc_page_count + len(section)
        first_answer_page = solutions_page + 1

        calls, drawn = _spy_interior(generator, puzzles, monkeypatch)
        folios = _folios(calls)

        assert folios[solutions_page] == str(solutions_page), (
            f"the SOLUTIONS divider should read {solutions_page!r}, got "
            f"{folios.get(solutions_page)!r}"
        )
        assert folios[first_answer_page] == str(first_answer_page), (
            f"the first answer page should read {first_answer_page!r}, got "
            f"{folios.get(first_answer_page)!r}"
        )
        # A folio that silently carried the TOC's own length wrong (e.g. off
        # by one) would still be *present* and would still fail these two
        # exact-value assertions — this test is the one AC-1's presence
        # check cannot be, by design.
        assert folios[solutions_page] != str(solutions_page - decided.toc_page_count), (
            "the divider's folio must not silently read a pre-TOC position"
        )


# --------------------------------------------------------------------------
# AC-9
# --------------------------------------------------------------------------


class TestBookPageNumbers_ParityHoldsWithTheTocInserted:
    """Page 1 is still right-hand; every page's parity is still its position."""

    def test_every_folios_own_side_matches_page_is_right_hand(self, monkeypatch) -> None:
        generator = BookPDFGenerator(corpus_book())
        calls, drawn = _spy_interior(generator, baseline_puzzles(), monkeypatch)
        folios = _folios(calls)
        by_page = {call.page: call.anchor for call in calls if call.anchor in _FOLIO_ANCHORS}

        assert page_is_right_hand(1), "interior page 1 (the guide) is right-hand (FR-043)"
        checked = 0
        for page in folios:
            anchor = by_page[page]
            expected = "rb" if page_is_right_hand(page) else "lb"
            assert anchor == expected, (
                f"page {page} is "
                f"{'right' if page_is_right_hand(page) else 'left'}-hand but its "
                f"folio anchored {anchor!r}"
            )
            checked += 1
        assert checked == len(folios) >= drawn - 1, "almost every page carried a checkable folio"

    def test_parity_holds_on_a_larger_book_whose_toc_spans_more_than_one_page(
        self, monkeypatch
    ) -> None:
        """A bigger book (enough puzzles to force a multi-page TOC) still
        keeps every later page's parity equal to its own 1-based position —
        AC-6's own "later numbering still consistent" clause, read for
        parity rather than for the arithmetic AC-6's own test already
        checks.
        """
        generator = BookPDFGenerator(corpus_book("card-200-ac9-big"))
        puzzles = [
            puzzle(f"card200-ac9-{n}", 20, 20, 4, "easy", f"Picture {n}")
            for n in range(60)
        ]
        calls, drawn = _spy_interior(generator, puzzles, monkeypatch)
        folios = _folios(calls)
        by_page = {call.page: call.anchor for call in calls if call.anchor in _FOLIO_ANCHORS}

        decided = generator.section_plan(list(puzzles))
        assert decided.toc_page_count > 1, (
            "this corpus should force a multi-page TOC, or this test checks nothing new"
        )
        for page in folios:
            expected = "rb" if page_is_right_hand(page) else "lb"
            assert by_page[page] == expected
