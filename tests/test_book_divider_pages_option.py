"""CARD-305 — the four divider pages become an option on Print setup.

    TestDividerPages_TheDefaultIsEveryBookAsItWasBefore  the control for
            everything below: nothing stored prints all four, which is what
            every book printed when the pages were unconditional
    TestDividerPages_TurningThemOffRemovesExactlyThoseFourPages  the feature:
            three level dividers and SOLUTIONS, four fewer pages, and the
            interior's own walk agrees with its declared count
    TestDividerPages_TheReaderReadsEveryStoredFormAndRefusesTheRest  the
            column's domain, including what it must NOT read as "off"
    TestDividerPages_TheTableOfContentsFollows  the TOC loses a row per level
            and its solutions row points at the first answer page
    TestDividerPages_ThePlanAndTheWalkCannotDisagree  the inverted tripwire:
            a section still holding a divider for a book that prints none
            fails loudly rather than printing a short TOC
    TestDividerPages_TheKdpEstimateAgreesWithTheInterior  the spine/gutter
            estimate is the interior's real length in both states
    TestDividerPages_PrintSetupStoresTheChoice  the screen: ticked, unticked,
            and the submission that does not carry the control at all

**The figures here are worked out, not read back from the code.** AC-253's
five-member book is 2 easy, 2 medium, 1 hard, so it opens three named levels:
three level dividers plus one SOLUTIONS page is **four** pages, and that is
the number the page count must fall by. A book of one level falls by two.

**The one test that would have caught the defect this card most risked** is
``TestDividerPages_PrintSetupStoresTheChoice``'s
``test_a_submission_without_the_control_leaves_the_stored_choice_alone``. A
checkbox posts nothing when it is unticked, so "off" and "this form has no
such field" arrive identically; read naively, the first save from any older
client would strip four pages out of a book that wanted them. The hidden
marker field is what tells them apart, and every other route test in this
suite posts *without* it — so they are themselves that case, and they all
still expect their dividers.
"""

from __future__ import annotations

import re
from dataclasses import replace

import pytest

from nonogram.admin.book_kdp import unpaired_interior_page_count
from nonogram.admin.book_page_spec import (
    DEFAULT_DIVIDER_PAGES,
    DIVIDER_PAGES_COLUMN,
    book_divider_pages,
    divider_pages_from_stored,
)
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    DividerPagePlan,
    GUIDE_TITLE,
    TOC_SOLUTIONS_LABEL,
    interior_page_count,
    structural_toc_entries,
)
from tests.helpers.db import sqlite_session_scope
from tests.test_book_pdf_levels import AC253_MEMBERS, _book, _book_of
from tests.test_book_plan_storage import (
    AC198_MATRIX,
    MODES,
    _build_app,
    _form,
    _new_book,
    _page,
)


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "dividers.db")


@pytest.fixture(params=MODES)
def mode(request):
    return request.param


@pytest.fixture
def app(mode, scope, monkeypatch):
    """The admin app in each storage mode — the reading every route test makes."""
    return _build_app(mode, scope, monkeypatch)

#: AC-253's book opens three named levels, so it carries three level dividers
#: and one SOLUTIONS page. Worked out from the members, not measured.
LEVELS_IN_AC253 = 3
DIVIDERS_IN_AC253 = LEVELS_IN_AC253 + 1


def _generator(divider_pages):
    """A generator for AC-253's book with the column set to ``divider_pages``."""
    return BookPDFGenerator(
        replace(_book(), **{DIVIDER_PAGES_COLUMN: divider_pages})
    )


def _puzzles():
    return _book_of(*AC253_MEMBERS)


class TestDividerPages_TheDefaultIsEveryBookAsItWasBefore:
    """Nothing stored prints all four — the control for every test below.

    Without this, "turning them off removes four pages" would be a claim
    about a book nobody has, and a reader could not tell a working toggle
    from a generator that never drew the pages at all.
    """

    def test_an_empty_column_prints_all_four(self) -> None:
        generator = _generator(None)

        assert generator.divider_pages is True
        assert DEFAULT_DIVIDER_PAGES is True

    def test_the_default_book_really_draws_three_level_dividers(self) -> None:
        pages = _generator(None).section_plan(_puzzles()).pages
        dividers = [p for p in pages if isinstance(p, DividerPagePlan)]

        assert [d.level.value for d in dividers] == ["easy", "medium", "hard"]

    @pytest.mark.parametrize("stored", [None, True, 1, "1", "on", "true", "yes"])
    def test_every_spelling_of_on_prints_them(self, stored) -> None:
        assert _generator(stored).divider_pages is True


class TestDividerPages_TurningThemOffRemovesExactlyThoseFourPages:
    """The feature, measured as a delta rather than as an absolute count."""

    def test_the_page_count_falls_by_exactly_four(self) -> None:
        """Four, because this book opens three levels and has one answer key.

        A delta, not two absolutes: the interior's length also carries the
        title page, the guide, the TOC, the puzzle pages and the answer
        pages, and quoting one of those as this card's figure is how a page
        count claim goes wrong (CARD-227's own F-001 did exactly that).
        """
        puzzles = _puzzles()
        with_dividers = _generator(True).interior_stream(list(puzzles)).page_count
        without = _generator(False).interior_stream(list(puzzles)).page_count

        assert with_dividers - without == DIVIDERS_IN_AC253

    def test_no_divider_page_is_planned_at_all(self) -> None:
        pages = _generator(False).section_plan(_puzzles()).pages

        assert [p for p in pages if isinstance(p, DividerPagePlan)] == []

    def test_the_walk_produces_exactly_the_count_it_declared(self) -> None:
        """The generator's own plan/draw tripwire, driven in both states.

        ``_as_planned`` raises when the walk and the declared count
        disagree, so this both asserts the number and proves the number is
        the one the pages were actually drawn against.
        """
        for flag in (True, False):
            stream = _generator(flag).interior_stream(list(_puzzles()))
            drawn = sum(1 for _ in stream.pages)

            assert drawn == stream.page_count, flag

    def test_the_answer_key_simply_starts_one_page_earlier(self) -> None:
        """The SOLUTIONS page's absence moves the answers up, not sideways.

        The answer pages keep their own count; what changes is where they
        begin. Asserted as the difference between the two interiors'
        answer-page counts being zero while the total fell by four.
        """
        puzzles = _puzzles()
        on = _generator(True).interior_stream(list(puzzles))
        off = _generator(False).interior_stream(list(puzzles))

        assert on.answer_page_count == off.answer_page_count
        assert on.page_count - off.page_count == DIVIDERS_IN_AC253

    def test_a_single_level_book_falls_by_two(self) -> None:
        """The EDGE on the level axis: one divider plus SOLUTIONS, not four.

        A fixed "four" anywhere in the implementation would survive the test
        above — this book has one named level, so the only correct delta is
        two, and the figure has to follow the book.
        """
        one_level = _book_of(("E1", "easy"), ("E2", "easy"))
        on = _generator(True).interior_stream(list(one_level)).page_count
        off = _generator(False).interior_stream(list(one_level)).page_count

        assert on - off == 2

    def test_a_book_with_no_puzzles_is_the_same_length_either_way(self) -> None:
        """No puzzles, no answer key, no levels — so nothing to remove.

        The guard that keeps the SOLUTIONS term out of an empty book is
        ``interior_page_count``'s own ``if puzzle_count``, and this is the
        case where the new term must not reach it.
        """
        assert interior_page_count(0, solutions_divider=True) == interior_page_count(
            0, solutions_divider=False
        )


class TestDividerPages_TheReaderReadsEveryStoredFormAndRefusesTheRest:
    """The column's domain, and the values that must not read as a boolean."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            (None, True),
            ("", True),
            ("   ", True),
            (True, True),
            (False, False),
            (1, True),
            (0, False),
            ("1", True),
            ("0", False),
            ("on", True),
            ("off", False),
            ("true", True),
            ("false", False),
            ("TRUE", True),
            ("False", False),
            ("yes", True),
            ("no", False),
        ],
    )
    def test_the_stored_forms_each_read_as_themselves(self, raw, expected) -> None:
        assert divider_pages_from_stored(raw) is expected

    @pytest.mark.parametrize("raw", ["maybe", "2", 2, -1, 3.5, [], {}, object()])
    def test_a_value_nobody_meant_is_refused_and_names_the_column(self, raw) -> None:
        """Refused, not read as truthy.

        A ``2`` in this column is a bug upstream, and reading it as "on"
        would hide it. The message names the column for the same reason
        ``ink_mode_from_stored``'s does.
        """
        with pytest.raises(ValueError, match=DIVIDER_PAGES_COLUMN):
            divider_pages_from_stored(raw)

    def test_a_book_with_no_such_attribute_reads_as_the_default(self) -> None:
        """A row from before the migration, and ``None`` itself."""
        assert book_divider_pages(object()) is True
        assert book_divider_pages(None) is True


class TestDividerPages_TheTableOfContentsFollows:
    """The TOC names sections, so losing the dividers loses rows."""

    def test_a_book_without_dividers_lists_only_the_guide_and_the_solutions(
        self,
    ) -> None:
        generator = _generator(False)
        decided = generator.section_plan(_puzzles())
        entries = structural_toc_entries(
            decided.pages, decided.payloads, 99, level_rows=False
        )

        assert [entry.label for entry in entries] == [
            GUIDE_TITLE,
            TOC_SOLUTIONS_LABEL,
        ]

    def test_with_dividers_the_level_rows_are_there_to_lose(self) -> None:
        """The control: the same call on the same book keeps 2 rows per level."""
        generator = _generator(True)
        decided = generator.section_plan(_puzzles())
        entries = structural_toc_entries(decided.pages, decided.payloads, 99)

        assert len(entries) == 2 + 2 * LEVELS_IN_AC253

    def test_the_solutions_row_points_at_the_first_answer_page(self) -> None:
        """With no divider to open the section, the row names the answers.

        Read off the rendered TOC row rather than recomputed here: the row's
        page must be a page the book actually has, and with the dividers off
        the page one before the first answer belongs to the last puzzle.
        """
        generator = _generator(False)
        stream = generator.interior_stream(list(_puzzles()))
        # The answer pages are the last `answer_page_count` pages of the
        # interior, so the first of them is derivable from the total.
        first_answer_page = stream.page_count - stream.answer_page_count + 1
        decided = generator.section_plan(_puzzles())
        entries = structural_toc_entries(
            decided.pages, decided.payloads, first_answer_page, level_rows=False
        )

        solutions = [e for e in entries if e.label == TOC_SOLUTIONS_LABEL]
        (row,) = solutions
        assert row.page == first_answer_page


class TestDividerPages_ThePlanAndTheWalkCannotDisagree:
    """The tripwire inverts rather than disappearing.

    The matching check has always refused a section whose dividers disagree
    with the book's level runs. Turning the pages off must not turn that
    check off: a section still holding a divider while the caller says the
    book prints none is the same class of defect, and it has to fail just as
    loudly instead of printing a TOC that omits real pages.
    """

    def test_a_divider_in_the_plan_of_a_book_that_prints_none_is_refused(
        self,
    ) -> None:
        decided = _generator(True).section_plan(_puzzles())

        with pytest.raises(RuntimeError, match="prints none"):
            structural_toc_entries(
                decided.pages, decided.payloads, 99, level_rows=False
            )

    def test_and_the_matching_check_still_works_the_other_way(self) -> None:
        """The control: the original tripwire is untouched."""
        decided = _generator(False).section_plan(_puzzles())

        with pytest.raises(RuntimeError, match="do not match"):
            structural_toc_entries(decided.pages, decided.payloads, 99)


class TestDividerPages_TheKdpEstimateAgreesWithTheInterior:
    """The estimate feeds KDP's gutter band and the spine, so it must agree.

    An estimate that disagreed with the written file would print a gutter
    margin for a book of a different length — a defect that shows up in no
    render of any page, which is why it is asserted against the real
    interior rather than against a second formula.

    The estimate is the **unpaired** count by construction (one page per
    puzzle, one answer page per puzzle), so it is held against the
    interior's own ``unpaired_page_count`` and not against ``page_count``,
    which pairing and packing have already shortened.
    """

    @pytest.mark.parametrize("flag", [True, False])
    def test_the_estimate_is_the_interiors_own_unpaired_count(self, flag) -> None:
        puzzles = _puzzles()
        book = replace(_book(), **{DIVIDER_PAGES_COLUMN: flag})

        estimate = unpaired_interior_page_count(list(puzzles), book=book)
        real = BookPDFGenerator(book).interior_stream(
            list(puzzles)
        ).unpaired_page_count

        assert estimate == real

    def test_and_the_estimate_itself_falls_by_four(self) -> None:
        """The control: the estimate is not simply agreeing by ignoring it."""
        puzzles = _puzzles()
        on = unpaired_interior_page_count(
            list(puzzles), book=replace(_book(), **{DIVIDER_PAGES_COLUMN: True})
        )
        off = unpaired_interior_page_count(
            list(puzzles), book=replace(_book(), **{DIVIDER_PAGES_COLUMN: False})
        )

        assert on - off == DIVIDERS_IN_AC253


class TestDividerPages_PrintSetupStoresTheChoice:
    """The screen, through the real route in both storage modes."""

    def test_the_box_is_ticked_for_a_book_that_prints_them(self, app) -> None:
        book_id = _new_book(app.book_manager)

        html = _page(app.test_client(), book_id)

        tag = re.search(
            r'<input\b[^>]*\bid="interior_divider_pages"[^>]*>', html, re.S
        )
        assert tag, "no divider-pages checkbox on Print setup"
        assert "checked" in tag.group(0)

    def test_unticking_it_stores_false(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX)
        # The real page always posts the marker; an unticked box posts no
        # value of its own, which is this submission.
        form["interior_divider_pages_present"] = "1"

        client.post(f"/book/{book_id}/setup-print", data=form)

        assert book_divider_pages(app.book_manager.get_book(book_id)) is False

    def test_ticking_it_stores_true(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX)
        form["interior_divider_pages_present"] = "1"
        form["interior_divider_pages"] = "1"

        client.post(f"/book/{book_id}/setup-print", data=form)

        assert book_divider_pages(app.book_manager.get_book(book_id)) is True

    def test_a_submission_without_the_control_leaves_the_stored_choice_alone(
        self, app
    ) -> None:
        """The defect this card most risked, as a test.

        An unticked checkbox and an absent field are the same bytes on the
        wire. A client built before this control — or any other form posting
        to this route — must not strip four pages out of a book, so a
        submission carrying no marker leaves the column where it was. Driven
        from "off", because a book already at the default would pass this
        test whatever the code did.
        """
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        turn_off = _form(150, (40, 40, 20), AC198_MATRIX)
        turn_off["interior_divider_pages_present"] = "1"
        client.post(f"/book/{book_id}/setup-print", data=turn_off)
        assert book_divider_pages(app.book_manager.get_book(book_id)) is False

        # ... and now a submission that does not carry the control at all.
        client.post(
            f"/book/{book_id}/setup-print",
            data=_form(150, (40, 40, 20), AC198_MATRIX),
        )

        assert book_divider_pages(app.book_manager.get_book(book_id)) is False

    def test_the_box_comes_back_unticked_once_it_is_stored_off(self, app) -> None:
        """The round trip: the screen shows what the book will print."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX)
        form["interior_divider_pages_present"] = "1"
        client.post(f"/book/{book_id}/setup-print", data=form)

        html = _page(client, book_id)

        tag = re.search(
            r'<input\b[^>]*\bid="interior_divider_pages"[^>]*>', html, re.S
        )
        assert tag
        assert "checked" not in tag.group(0)
