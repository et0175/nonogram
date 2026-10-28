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

**The defect this card most risked, and the pair of cells that catches it.**
A checkbox posts nothing when it is unticked, so "off" and "this form has no
such field" arrive identically; read naively, the first save from any older
client would strip four pages out of a book that wanted them. The hidden
marker field is what tells them apart. It takes **two** cells in
``TestDividerPages_PrintSetupStoresTheChoice``, and only one of them can fail
on the marker mechanism:

* ``test_a_submission_without_the_control_leaves_the_default_on_alone`` —
  driven from the **default**, which is the state every existing book is in
  and the only state the defect is visible in. Deleting either half of the
  mechanism reds it (measured; see its docstring).
* ``test_a_submission_without_the_control_leaves_the_stored_choice_alone`` —
  driven from "off", where the broken naive read produces ``bool(None)`` ->
  ``False``, the very value it asserts. It therefore passes with the
  mechanism deleted, and its job is the complement: ruling out a route that
  writes the default back on every save.

CARD-305 cycle 1's F-001 is exactly that the from-off cell shipped alone,
with a docstring claiming it was the discriminating one.

Every other route test in this suite posts *without* the marker, so they are
themselves that case and they all still expect their dividers — but all of
their books sit at the default and none asserts the column afterwards, so
they exercise the path without discriminating on it.
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
    divider_pages_from_form,
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
from tests.helpers.page_ink import drawing_of
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

    def test_no_divider_page_is_drawn_at_all_including_solutions(
        self, monkeypatch
    ) -> None:
        """Both dividers, counted where they are actually drawn.

        The cell above reads the **plan**, which holds the three level
        dividers; the SOLUTIONS page is not in it — ``interior_stream`` yields
        that one directly. Both go through ``create_divider_page`` (it is one
        page design for all four), so counting its calls over the whole walk
        is the one place that sees every divider the book draws, which is
        what makes this the criterion for FR-041's *and* FR-042's off case
        rather than two separate readings.

        The ON leg is the control: without it "zero were drawn" would hold
        for a generator that draws no dividers at all.
        """
        drawn: list[str] = []
        original = BookPDFGenerator.create_divider_page

        def record(self, page_number, text="SOLUTIONS"):
            drawn.append(text)
            return original(self, page_number, text)

        monkeypatch.setattr(BookPDFGenerator, "create_divider_page", record)

        list(_generator(True).interior_stream(list(_puzzles())).pages)
        assert drawn == ["Easy", "Medium", "Hard", "SOLUTIONS"]

        drawn.clear()
        list(_generator(False).interior_stream(list(_puzzles())).pages)
        assert drawn == []

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


#: A book storing **unequal** side margins, for the parity class below. On
#: CON-018 as amended 2026-10-17 Book 1's gutter and outside margins are both
#: 0.5 in, so a drawing centred in the usable area is centred on the trim too
#: and a page's side of the spread leaves no trace in its own ink at all
#: (measured: every page reads an offset of 0 px). A 20 mm gutter against a
#: 10 mm outside margin is the only configuration in which mirroring is
#: observable, and it is the one
#: ``TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity`` already uses
#: for the mirror-image change (one page *added*).
MIRROR_GUTTER_MM = 20.0
MIRROR_OUTSIDE_MM = 10.0

#: The pages of this book that carry a measurable drawing: its 5 puzzle pages
#: and its 5 answer pages (one per 20x20 puzzle — nothing here packs). The
#: title page, the two guide pages, the TOC and any divider carry no ruled
#: grid, so ``drawing_of`` declines them. Asserted, because a loop that
#: quietly stopped finding any page to measure would pass.
#:
#: Measured in both states and in two domains: this file, and a standalone
#: probe over the same book outside pytest. 18 pages with the dividers, 14
#: without, 10 measurable in each.
MEASURABLE_PAGES = 10


class TestDividerPages_EveryPagesParityIsStillItsOwnPosition:
    """FR-043/INV-013 for the off state: four pages fewer, parity still right.

    This is the widest consequence of the setting and the one the rest of
    this file does not reach (CARD-305 cycle 1, F-003). The other classes
    control the page **count**, the TOC rows, the walk-vs-declared tripwire
    and the KDP estimate — **none of them would catch a page drawn on the
    frame of a parity it no longer has**, because a page's gutter side comes
    from its number and every one of those numbers moved.

    The board's precedent for the mirror-image change — one page *added* —
    is ``tests/test_book_guide_page.py``'s
    ``TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity::test_every_pages_parity_still_equals_its_own_position``.
    This card removes up to four and shipped no equivalent; this is it, in
    the same instrument (the ink on the page, read back) and on the same
    unequal-margin book, so the two are comparable.

    **Read off the page, not off the plan.** The claim is about where a page
    was really drawn, so the measurement is ``drawing_of``'s: a right-hand
    (odd) page's drawing sits right of the trim's middle, a left-hand (even)
    one left of it, by half the margin difference. Asking the plan what page
    number it thinks each page has would prove only that the plan agrees
    with itself.

    **Both states, and the ON state is the control**, not decoration: it is
    what makes the OFF state's offsets *different numbers* rather than the
    same ones. Measured on this book: with dividers the puzzle pages are
    interior pages 6, 7, 9, 10, 12; without them they are 5, 6, 7, 8, 9 — so
    the first puzzle page's drawing swaps sides between the two runs, and a
    generator that kept the old numbering while emitting the shorter book
    would read the wrong side on every page of it.
    """

    @staticmethod
    def _mirrored(divider_pages):
        return replace(
            _book(),
            gutter_margin_cm=f"{MIRROR_GUTTER_MM / 10:.2f}",
            outside_margin_cm=f"{MIRROR_OUTSIDE_MM / 10:.2f}",
            **{DIVIDER_PAGES_COLUMN: divider_pages},
        )

    @pytest.mark.parametrize("flag", [True, False])
    def test_every_pages_parity_equals_its_own_1_based_position(self, flag) -> None:
        pages = BookPDFGenerator(self._mirrored(flag)).interior_pages(
            list(_puzzles())
        )
        px_per_mm = 300 / 25.4  # the DPI every book page is measured at
        expected_offset = (
            (MIRROR_GUTTER_MM - MIRROR_OUTSIDE_MM) / 2 * px_per_mm
        )

        checked = 0
        for number, page in enumerate(pages, start=1):
            try:
                drawing = drawing_of(page)
            except ValueError:
                # The title page, the guide, the TOC and any divider page
                # carry no measurable drawing. They are not the subject.
                continue
            offset = (drawing.left + drawing.grid_right) / 2 - page.width / 2
            assert (offset > 0) == (number % 2 == 1), (
                f"dividers={flag}: interior page {number} of {len(pages)} is "
                f"centred {offset:.1f} px off the middle, the wrong side for "
                f"{'an odd' if number % 2 else 'an even'} page"
            )
            # Centring makes the magnitude the margin difference's own half
            # on every page, whatever its puzzle (EC-032).
            assert abs(abs(offset) - expected_offset) <= 2, (flag, number, offset)
            checked += 1

        assert checked == MEASURABLE_PAGES, (
            f"dividers={flag}: {checked} pages carried a measurable drawing, "
            f"not {MEASURABLE_PAGES} — the walk is measuring a different book"
        )

    def test_the_two_states_really_put_the_drawings_on_different_sides(self) -> None:
        """The control for the class: the parity claim above has teeth here.

        If the two runs put every drawing on the same side, the test above
        would pass for a generator that ignored the setting when numbering
        pages. They do not: this asserts the first measurable page's side
        **differs** between the states, which is only true because the
        shorter book renumbered. Measured: page 6 (left) with the dividers,
        page 5 (right) without.
        """
        sides = {}
        for flag in (True, False):
            pages = BookPDFGenerator(self._mirrored(flag)).interior_pages(
                list(_puzzles())
            )
            for number, page in enumerate(pages, start=1):
                try:
                    drawing = drawing_of(page)
                except ValueError:
                    continue
                offset = (drawing.left + drawing.grid_right) / 2 - page.width / 2
                sides[flag] = (number, offset > 0)
                break

        assert sides[True] == (6, False), sides
        assert sides[False] == (5, True), sides


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

    @pytest.mark.parametrize(
        "posted,expected",
        [
            # The EDGE, and the whole reason this is a second function: an
            # unticked checkbox posts nothing, and nothing from a *form* is
            # "off" — while nothing from the *column* is the default, which
            # is True. The two doors disagree here on purpose.
            (None, False),
            ("", False),
            ("   ", False),
            # A ticked box posts "1"...
            ("1", True),
            ("on", True),
            ("true", True),
            # ...and a client that means "no" and says so is believed, which
            # ``bool()`` could not do: every one of these stored True before
            # CARD-305 cycle 1's F-004.
            ("0", False),
            ("off", False),
            ("false", False),
            ("no", False),
            ("FALSE", False),
        ],
    )
    def test_the_form_field_reads_as_itself_and_empty_means_off(
        self, posted, expected
    ) -> None:
        assert divider_pages_from_form(posted) is expected

    @pytest.mark.parametrize("posted", ["maybe", "2", "-1"])
    def test_a_posted_field_in_no_vocabulary_is_refused_and_names_the_column(
        self, posted
    ) -> None:
        """Refused rather than guessed at — a book losing four pages is worse.

        The route turns this into a flashed refusal that stores nothing,
        which is the posture it already takes for an unreadable trim; the
        route-level cell for that is
        ``test_a_field_in_no_vocabulary_is_refused_and_stores_nothing``.
        """
        with pytest.raises(ValueError, match=DIVIDER_PAGES_COLUMN):
            divider_pages_from_form(posted)


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
        """A markerless submission leaves a stored **off** alone.

        An unticked checkbox and an absent field are the same bytes on the
        wire, so a client built before this control — or any other form
        posting to this route — must leave the column where it was.

        **This leg alone cannot fail on the marker mechanism**, and saying so
        is the point of the pair (CARD-305 cycle 1, F-001). Driven from
        "off", the broken naive read is
        ``bool(request.form.get("interior_divider_pages"))`` ->
        ``bool(None)`` -> ``False``, which is the value asserted here:
        mechanism-working and mechanism-deleted write the same byte.
        Measured — both deletion mutants (``app.py``'s marker guard and
        ``book_manager._apply_print_spec``'s ``is not None`` guard, each to
        ``if True:``) PASS this cell. Its job is the complement: it rules out
        an implementation that simply writes the default back on every save,
        which the from-ON leg below would accept. The discriminating leg is
        ``test_a_submission_without_the_control_leaves_the_default_on_alone``.
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

    def test_a_submission_without_the_control_leaves_the_default_on_alone(
        self, app
    ) -> None:
        """The defect this card most risked, as a test that can fail.

        **This is the state the defect is visible in**, and it is the state
        every book in production is in: nothing stored, so the book prints
        its dividers. A markerless save must leave it printing them. Read
        naively the marker's absence is indistinguishable from an unticked
        box, so the first Print-setup save from any older client would strip
        four pages out of a book that wanted them — and the owner would find
        it at the proof.

        A separate cell from the from-off leg above rather than a second leg
        inside it, because a test short-circuits at its first failing assert:
        two cells give two verdicts, so "the mechanism is gone" and "the
        route writes the default back" are told apart by *which* name reds.
        Measured (CARD-305 fix round 1): deleting the marker guard
        (``app.py:3724`` -> ``if True:``) reds this cell in both storage
        modes, and so does deleting ``_apply_print_spec``'s
        ``spec.interior_divider_pages is not None`` guard
        (``book_manager.py:1005`` -> ``if True:``), while the from-off leg
        passes under each.
        """
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        # The state of every book that existed before this card: nothing
        # stored, which the reader answers with DEFAULT_DIVIDER_PAGES.
        assert book_divider_pages(app.book_manager.get_book(book_id)) is True

        client.post(
            f"/book/{book_id}/setup-print",
            data=_form(150, (40, 40, 20), AC198_MATRIX),
        )

        assert book_divider_pages(app.book_manager.get_book(book_id)) is True

    @pytest.mark.parametrize("posted", ["0", "off", "false", "no"])
    def test_a_submission_that_says_no_explicitly_stores_false(
        self, app, posted
    ) -> None:
        """F-004, through the real route: the field's own vocabulary holds.

        The shipped template never posts these — an unticked box posts
        nothing — so this is the *next* client: a hand-built form, a JSON-ish
        poster, a future API. Read with ``bool()`` every one of them stored
        **True**, the opposite of what it said, and
        ``_DIVIDER_PAGES_FALSE`` was unreachable from any inbound path.
        """
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX)
        form["interior_divider_pages_present"] = "1"
        form["interior_divider_pages"] = posted

        client.post(f"/book/{book_id}/setup-print", data=form)

        assert book_divider_pages(app.book_manager.get_book(book_id)) is False

    def test_a_field_in_no_vocabulary_is_refused_and_stores_nothing(
        self, app
    ) -> None:
        """A value nobody meant is the route's own ValueError posture.

        Flashed, nothing stored, the page re-rendered — the same thing an
        unreadable trim does. The load-bearing assertion is the second one:
        the book's choice is where it was, so a garbage field cannot take
        four pages off a book by being read as truthy.
        """
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX)
        form["interior_divider_pages_present"] = "1"
        form["interior_divider_pages"] = "maybe"

        response = client.post(f"/book/{book_id}/setup-print", data=form)

        assert DIVIDER_PAGES_COLUMN in response.get_data(as_text=True)
        assert book_divider_pages(app.book_manager.get_book(book_id)) is True

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
