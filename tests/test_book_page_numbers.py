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
from typing import Dict, List, Optional, Tuple

import pytest
from PIL import ImageDraw

from nonogram import clues
from nonogram.admin.book_answer_key import Answer, PackedAnswerPage
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    PuzzlePagePlan,
    page_is_right_hand,
)
from nonogram.difficulty import Tier
from nonogram.export.layout import compute_pair_layout
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

        **Review cycle 2, F-1:** this same book's lone *blank* puzzle page
        (page 5 — a single, unpaired puzzle, confirmed by
        ``generator.section_plan``) is page-fit-bound on this 10 cm trim
        exactly the way the reviewer's own reproduction is (direct
        measurement: ``usable_bottom - drawing_bottom == 0``), so it is now
        correctly missing too — before the F-1 fix, this was the one real,
        already-in-the-test-suite case of the defect itself: the folio was
        drawn directly over this page's own grid, and this test's own
        "presence only, within a tolerance of 2" check was loose enough to
        pass anyway.
        """
        generator = BookPDFGenerator(_min_trim_book())
        single = [puzzle("card200-mintrim", 20, 20, 5, "easy", "Solo")]
        calls, drawn = _spy_interior(generator, single, monkeypatch)
        folios = _folios(calls)

        answer_page = drawn  # the one full solved page is always the last
        blank_puzzle_page = drawn - 2  # divider, then this puzzle's own blank page, then SOLUTIONS, then the answer page
        assert answer_page not in folios, (
            "the min-trim book's answer page has no slack for a caption "
            "(CARD-197) and so none for a folio either — one must have been "
            "drawn without checking the room"
        )
        assert blank_puzzle_page not in folios, (
            "the min-trim book's own blank puzzle page is page-fit-bound "
            "(F-1's own defect shape) and must omit its folio rather than "
            "draw it over the grid"
        )
        # Most pages on this tiny, single-puzzle book still print their own
        # folio — the omission is specific to pages with no measurable room
        # (the blank puzzle page's and the answer page's own grids; the
        # guide's own tightest fallback form can be another, since all three
        # genuinely leave no room below their content on this 10 cm trim),
        # not a blanket "min trim never gets folios" bug.
        missing = set(range(1, drawn + 1)) - set(folios)
        assert missing <= {1, blank_puzzle_page, answer_page}, (
            f"unexpected pages missing a folio on the min-trim book: {missing}"
        )
        assert len(folios) >= drawn - 3


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


# --------------------------------------------------------------------------
# Review cycle 2, F-1 (gating) — the folio must never be drawn on top of the
# grid's own ink, even when a page's cell fitting leaves no slack at all.
# --------------------------------------------------------------------------


def _row_depth_1_column_depth_10_grid(size: int = 30) -> List[List[bool]]:
    """A ``size`` x ``size`` grid whose row clues are all exactly one entry
    deep (every row is either fully filled across or fully empty — one run
    either way) while its column clues run ten entries deep (ten isolated
    filled rows, spaced three apart so no two runs touch or merge) — the
    reviewer's own F-1 reproduction geometry (CARD-200 review cycle 2: a
    30-wide/30-tall puzzle, row-clue depth 1, column-clue depth 10, on Book
    1's default trim), built as a real, internally-consistent grid (fed
    through :func:`~nonogram.clues.compute_clues`) rather than synthetic
    clue tuples disconnected from one.
    """
    filled_rows = {0, 3, 6, 9, 12, 15, 18, 21, 24, 27}
    assert len(filled_rows) == 10
    return [[(row in filled_rows) for _ in range(size)] for row in range(size)]


def _tight_fit_single_page_puzzle() -> Dict[str, object]:
    grid = _row_depth_1_column_depth_10_grid(30)
    found = clues.compute_clues(grid)
    return {
        "id": "f1-tight-single",
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": 30,
        "height": 30,
        "puzzle_name": "Tight Fit",
        "difficulty_tier": "hard",
    }


def _folio_calls(monkeypatch: pytest.MonkeyPatch, page_number: int, draw_call) -> List[_TextCall]:
    """Spy on one direct page-drawing call (not a whole interior walk) and
    tag every ``draw.text`` it makes with ``page_number`` — the same
    technique :func:`_spy_interior` uses for a full export, narrowed to one
    method call so each test below can construct its own tight-fit geometry
    directly, without building a whole book around it.
    """
    calls: List[_TextCall] = []
    original = ImageDraw.ImageDraw.text

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        calls.append(_TextCall(page_number, str(text), kwargs.get("anchor")))
        return original(self, xy, text, fill, font, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    try:
        draw_call()
    finally:
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
    return calls


class TestBookPageNumbers_FolioNeverCollidesWithTheGrid:
    """Review cycle 1 shipped ``_blank_page``/``_two_up_page``/
    ``_packed_answer_page`` all calling ``_draw_folio`` without a
    ``content_bottom`` (or, for the latter two, without any horizontal
    figure either), so each one's "is there room, or should I omit it"
    check treated its entire usable area as free space regardless of where
    the puzzle's own grid actually ended. Each test below constructs a real,
    internally-consistent tight-fit grid (verified by direct measurement,
    not assumed) and checks the folio is correctly omitted rather than
    drawn over the ink — and a matching control confirms the fix does not
    turn into a blanket omission.
    """

    def test_the_reviewers_own_geometry_is_still_reproducible(self) -> None:
        """Confirms the defect's precondition still holds on real production
        code. If this assertion ever stops holding, the tests below are
        exercising a scenario that no longer occurs, not a fixed bug.
        """
        from nonogram.export.layout import compute_layout

        generator = BookPDFGenerator(corpus_book("f1-geometry"))
        page_number = 3
        spec = generator.page_spec(page_number)
        row_clues = tuple((1,) for _ in range(30))
        column_clues = tuple((1,) * 10 for _ in range(30))
        layout = compute_layout(row_clues, column_clues, spec)
        placement = layout.page

        assert placement is not None
        assert placement.usable_bottom - placement.drawing_bottom == 0

    def test_blank_page_omits_the_folio_when_the_grid_is_page_fit_bound(
        self, monkeypatch
    ) -> None:
        generator = BookPDFGenerator(corpus_book("f1-blank-tight"))
        payload = generator._payload(_tight_fit_single_page_puzzle())
        page_number = 3

        calls = _folio_calls(
            monkeypatch, page_number, lambda: generator._blank_page(payload, 1, page_number)
        )

        assert not _folios(calls), (
            "a page-fit-bound blank page drew a folio directly over its own "
            "grid instead of omitting it"
        )

    def test_blank_page_still_draws_the_folio_with_real_slack(self, monkeypatch) -> None:
        """Control: an ordinary puzzle (plenty of slack below the grid)
        still gets its folio — the fix must not turn into a blanket
        omission.
        """
        generator = BookPDFGenerator(corpus_book("f1-blank-slack"))
        payload = generator._payload(puzzle("f1-blank-slack-p", 10, 10, 2, "easy", "Slack"))
        page_number = 3

        calls = _folio_calls(
            monkeypatch, page_number, lambda: generator._blank_page(payload, 1, page_number)
        )

        assert _folios(calls) == {page_number: str(page_number)}

    def test_two_up_page_omits_the_folio_when_the_lower_slots_corner_has_no_room_either(
        self, monkeypatch
    ) -> None:
        """A two-up pair whose lower slot's drawing reaches both the page's
        bottom margin (true on *every* two-up page, by construction) and its
        outer side margin (confirmed by direct measurement: a 10-row,
        25-column, depth-1 pair on Book 1's trim does both) is the one case
        a naive "reuse ``solved_puzzle_page``'s vertical-only check" fix
        could not pass: the lower slot's vertical slack reads zero on every
        two-up page regardless, so checking only that would silently omit
        the folio from the whole book (AC-1 would then fail) — this is the
        case where drawing unconditionally (review cycle 1's own code)
        really does print on top of the grid.
        """
        generator = BookPDFGenerator(corpus_book("f1-two-up-tight"))
        upper = generator._payload(puzzle("f1-two-up-tight-u", 25, 10, 1, "easy", "Upper"))
        lower = generator._payload(puzzle("f1-two-up-tight-l", 25, 10, 1, "easy", "Lower"))
        page_number = 5
        spec = generator.page_spec(page_number)
        pair = compute_pair_layout(
            (upper.row_clues, upper.column_clues),
            (lower.row_clues, lower.column_clues),
            spec,
        )
        assert pair is not None
        assert pair.lower.page.usable_bottom - pair.lower.page.drawing_bottom == 0
        assert pair.lower.page.usable_right - pair.lower.page.drawing_right == 0

        plan = PuzzlePagePlan(page_number, (1, 2), pair)
        calls = _folio_calls(
            monkeypatch, page_number, lambda: generator._two_up_page(plan, [upper, lower])
        )

        assert not _folios(calls), (
            "a two-up page whose lower slot has no room on either axis drew "
            "a folio directly over its own grid instead of omitting it"
        )

    def test_two_up_page_still_draws_the_folio_in_the_common_case(self, monkeypatch) -> None:
        """Control, and the regression a naive "always treat the lower
        slot's zero vertical slack as a collision" fix would have caused:
        the baseline book's own Duck/Owl pair has ample *horizontal* room
        even though its lower slot's vertical slack is also zero (true of
        every two-up page) — the folio must still print.
        """
        generator = BookPDFGenerator(corpus_book("f1-two-up-slack"))
        duck = generator._payload(puzzle("f1-two-up-slack-duck", 10, 10, 3, "easy", "Duck"))
        owl = generator._payload(puzzle("f1-two-up-slack-owl", 10, 10, 3, "easy", "Owl"))
        page_number = 5
        spec = generator.page_spec(page_number)
        pair = compute_pair_layout(
            (duck.row_clues, duck.column_clues), (owl.row_clues, owl.column_clues), spec
        )
        assert pair is not None
        assert pair.lower.page.usable_bottom - pair.lower.page.drawing_bottom == 0
        assert pair.lower.page.usable_right - pair.lower.page.drawing_right > 0

        plan = PuzzlePagePlan(page_number, (1, 2), pair)
        calls = _folio_calls(
            monkeypatch, page_number, lambda: generator._two_up_page(plan, [duck, owl])
        )

        assert _folios(calls) == {page_number: str(page_number)}

    def test_packed_answer_page_omits_the_folio_when_the_corner_tile_is_page_fit_bound(
        self, monkeypatch
    ) -> None:
        """The packed-answer corner tile — the one tile that can physically
        reach the folio's own corner — can be just as page-fit-bound as a
        full single answer page's grid (review cycle 1's own claim that a
        packed page's tiles "never reach the page's bottom-outer corner"
        does not hold: confirmed by direct measurement, a 20-row/15-column,
        depth-7 member at capacity 4 lands its corner tile's drawing within
        2px of both the tile's own bottom and right edges, well inside the
        folio digit's own width).
        """
        tight = puzzle("f1-packed-tight", 15, 20, 7, "easy", "Tight")
        generator = BookPDFGenerator(corpus_book("f1-packed-tight-book"))
        payloads = [(f"id{n}", generator._payload(tight)) for n in range(1, 5)]
        answers = tuple(
            Answer(number=n, width=15, height=20, level=Tier.EASY) for n in range(1, 5)
        )
        plan = PackedAnswerPage(answers)
        page_number = 9

        calls = _folio_calls(
            monkeypatch,
            page_number,
            lambda: generator._packed_answer_page(plan, payloads, page_number, {}),
        )

        assert not _folios(calls), (
            "a packed answer page whose corner tile has no room drew a "
            "folio directly over its own grid instead of omitting it"
        )

    def test_packed_answer_page_still_draws_when_the_corner_tile_has_room(
        self, monkeypatch
    ) -> None:
        """Control: an ordinary packed page (plenty of slack in its corner
        tile) still gets its folio.
        """
        easy = puzzle("f1-packed-slack", 10, 10, 3, "easy", "Slack")
        generator = BookPDFGenerator(corpus_book("f1-packed-slack-book"))
        payloads = [(f"id{n}", generator._payload(easy)) for n in range(1, 3)]
        answers = tuple(
            Answer(number=n, width=10, height=10, level=Tier.EASY) for n in range(1, 3)
        )
        plan = PackedAnswerPage(answers)
        page_number = 9

        calls = _folio_calls(
            monkeypatch,
            page_number,
            lambda: generator._packed_answer_page(plan, payloads, page_number, {}),
        )

        assert _folios(calls) == {page_number: str(page_number)}
