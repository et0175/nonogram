"""CARD-222 — every interior puzzle page gets one frame: new margins, a header rule, a footer rule.

    AC-2  TestBookPageFrame_HeaderRuleIsOnTheSameBaselineEverywhere
    AC-3  TestBookPageFrame_FooterCarriesSizeAndFolio
    AC-4  TestBookPageFrame_PuzzleAreaHasOneDefinition
    AC-7  TestBookPageFrame_ShortestTrimStillHoldsTheFrame
    F-2   TestBookPageFrame_RefusesASheetThatIsNotABookPage
    F-3   TestBookPageFrame_RefusesAnInvertedPuzzleArea
    F-4   TestBookPageFrame_FooterIsOmittedWholeWhereContentReachesIt
          TestBookPageFrame_TwoUpKeepsItsOuterFolio   (the exemption's control)
    G-1   TestBookPageFrame_EachFigureIsDeclaredOnce
          TestBookPageFrame_TheHairlineIsNotAGridRule (ADR-0037/R2's exemption)
          TestBookPageFrame_MirroringBitesOnUnequalMargins

**Why a book with unequal margins appears below.** CON-018 as amended
2026-10-17 makes the gutter and the outside margin both 0.5 in, so on the
Book 1 profile the usable area no longer moves with page parity: a passing
assertion about a margin's *width* by parity is an identity and proves
nothing (the constraint's own note says so). Every parity claim in this file
is therefore either about which **side** a mark is on — which still has teeth
— or is made on ``_unequal_book()``, a book that stores a gutter and an
outside margin that differ, which is the only configuration in which
mirroring is actually under test.

**How a rule is found.** Never by reading the constant back: a rule is the
one run of rows, in a band of the page, in which *every* pixel between the
frame's two ends is ink. ``_rules_in`` measures that off the rendered page and
returns ``(y, thickness)``, so the assertions below compare measured ink
against the frame — not the frame against itself.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import (
    SIZE_LABEL_PT,
    BookPDFGenerator,
    grid_size_label,
)
from nonogram.export.layout import (
    INTERIOR_FOOTER_MM,
    INTERIOR_FOOTER_RULE_PT,
    INTERIOR_HEADER_RULE_PT,
    MM_PER_POINT,
    QR_SLOT_MM,
    DPI,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_layout,
    interior_frame,
)
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, puzzle

#: Pillow's ink threshold on a greyscale page, as ``page_ink.py`` sets it.
INK_LEVEL = 128

#: CON-020's floor in points, written out rather than imported: the footer's
#: two marks are reader-facing type and are held to it.
FLOOR_PT = 10.0


# --------------------------------------------------------------------------
# Books
# --------------------------------------------------------------------------


def _unequal_book() -> Book:
    """A book storing a gutter and an outside margin that **differ**.

    1.90 cm against 0.70 cm. Neither is the profile's own storage form, so
    both are read as the centimetres they say, and the usable area really does
    move with page parity — which is what makes a mirroring assertion on this
    book evidence rather than an identity.
    """
    return Book(
        book_id="card-222-unequal",
        metadata=BookMetadata(
            title="Unequal Margins",
            description="CARD-222's own mirroring fixture.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm="21.59",
        trim_height_cm="27.94",
        gutter_margin_cm="1.90",
        outside_margin_cm="0.70",
    )


def _min_trim_book() -> Book:
    """The shortest trim ``book_page_spec`` lays out at all: 10.00 x 10.00 cm.

    The same book ``tests/test_book_interior_type_floor.py`` and
    ``tests/test_book_page_numbers.py`` already measure at the minimum trim,
    with their own margins, so AC-7 is asked of the sheet those files already
    treat as the hardest one.
    """
    return Book(
        book_id="card-222-min-trim",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="CARD-222's own shortest-trim fixture.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm="10.00",
        trim_height_cm="10.00",
        gutter_margin_cm="0.95",
        outside_margin_cm="0.64",
    )


# --------------------------------------------------------------------------
# Measuring ink
# --------------------------------------------------------------------------


def _ink(page: Image.Image) -> np.ndarray:
    return np.asarray(page.convert("L")) < INK_LEVEL


def _rules_in(page: Image.Image, left: int, right: int, top: int, bottom: int) -> List[Tuple[int, int]]:
    """Every full-width rule between ``top`` and ``bottom``, as ``(first row, thickness)``.

    A row counts as part of a rule when every pixel from ``left`` to ``right``
    inclusive is ink; neighbouring such rows are one rule. The run's **first**
    row is returned rather than a computed centre: Pillow spreads an
    even-width stroke asymmetrically about its coordinate, so a "centre" would
    be off by one for the 2 px hairline and exact for the 3 px header rule —
    a difference in the measuring tool, not in the page. Callers assert that
    the frame's own ``y`` lies inside the measured run (:func:`_holds`).
    """
    ink = _ink(page)
    full = [y for y in range(top, bottom + 1) if ink[y, left : right + 1].all()]
    rules: List[Tuple[int, int]] = []
    run: List[int] = []
    for y in full:
        if run and y != run[-1] + 1:
            rules.append((run[0], len(run)))
            run = []
        run.append(y)
    if run:
        rules.append((run[0], len(run)))
    return rules


def _holds(rule: Tuple[int, int], y: int) -> bool:
    """Whether a measured run covers the row ``y`` a rule was asked for."""
    first, thickness = rule
    return first <= y <= first + thickness - 1


def _ink_columns(page: Image.Image, top: int, bottom: int) -> List[Tuple[int, int]]:
    """The runs of columns carrying ink between ``top`` and ``bottom``, ``(first, last)``."""
    ink = _ink(page)[top : bottom + 1, :]
    columns = np.where(ink.any(axis=0))[0]
    runs: List[Tuple[int, int]] = []
    if not len(columns):
        return runs
    start = previous = columns[0]
    for column in columns[1:]:
        if column - previous > 20:  # a word's own gap is far smaller
            runs.append((int(start), int(previous)))
            start = column
        previous = column
    runs.append((int(start), int(previous)))
    return runs


# --------------------------------------------------------------------------
# One rendered interior, shared
# --------------------------------------------------------------------------


#: Rendered interiors and recorded text calls, kept so each book's pages are
#: drawn once per session.
_CACHE: Dict[str, object] = {}


class _Interior:
    """The baseline book's interior, rendered once, with its page plan.

    Rendering 13 letter pages is the expensive part of this file, so it is
    done once per book and the pages are kept. ``puzzle_pages`` /
    ``two_up_pages`` come from the generator's own
    :meth:`BookPDFGenerator.section_plan`, never from a hardcoded page number,
    so a change to the interior's shape moves these tests with it instead of
    silently measuring the wrong page.
    """

    def __init__(self, book: Book, puzzles: List[dict]) -> None:
        self.book = book
        generator = BookPDFGenerator(book)
        plan = generator.section_plan(puzzles)
        self.one_up: List[int] = []
        self.two_up: List[int] = []
        self.sizes: Dict[int, Tuple[int, int]] = {}
        self.clues: Dict[int, Tuple[tuple, tuple]] = {}
        for page in plan.pages:
            numbers = getattr(page, "numbers", None)
            if numbers is None:
                continue  # a divider page
            (self.two_up if page.is_two_up else self.one_up).append(page.page_number)
            if not page.is_two_up:
                payload = plan.payloads[numbers[0] - 1]
                self.sizes[page.page_number] = (
                    len(payload.column_clues),
                    len(payload.row_clues),
                )
                self.clues[page.page_number] = (
                    tuple(payload.row_clues),
                    tuple(payload.column_clues),
                )
        stream = BookPDFGenerator(book).interior_stream(puzzles)
        self.pages: Dict[int, Image.Image] = {}
        for number, page in enumerate(stream.pages, start=1):
            self.pages[number] = page.copy()
        self.page_count = stream.page_count

    def frame(self, page_number: int):
        return interior_frame(book_page_spec(self.book, page_number))


def _interior(key: str, book: Book, puzzles: List[dict]) -> _Interior:
    if key not in _CACHE:
        _CACHE[key] = _Interior(book, puzzles)
    return _CACHE[key]  # type: ignore[return-value]


@pytest.fixture(scope="module")
def interior() -> _Interior:
    return _interior("book1", corpus_book(), baseline_puzzles())


def _height_bound_puzzle() -> dict:
    """A 30x30 puzzle whose drawing fills the usable height exactly.

    Every other row filled right across, stopping after ten runs: each row is
    one run of 30 (or the ``(0,)`` of an empty line) and each column is ten
    runs of 1, so the row-clue gutter is 1 cell deep and the column-clue
    gutter 10. 40 cells down against 31 across makes the height the binding
    term, which is what lands ``drawing_bottom`` on the bottom margin.
    """
    from nonogram import clues as clue_module

    grid = [[y % 2 == 0 and y < 19 for _ in range(30)] for y in range(30)]
    found = clue_module.compute_clues(grid)
    assert max(len(line) for line in found.rows) == 1
    assert max(len(line) for line in found.columns) == 10
    return {
        "id": "card222-tall",
        "grid": grid,
        "clues_rows": [list(line) for line in found.rows],
        "clues_cols": [list(line) for line in found.columns],
        "width": 30,
        "height": 30,
        "puzzle_name": "Tall",
        "difficulty_tier": "hard",
    }


def _header_window(frame) -> Tuple[int, int]:
    """The rows a header rule can be in: its own band, and not a row below it.

    Ends at the rule's **last** row rather than some way past it, because the
    drawing's own heavy top border lies an eighth of a band lower and spans
    the whole text width on a page whose drawing fills it — a window reaching
    that row would measure two rules where the page has one of each kind.
    """
    return frame.header_rule.y - 60, frame.header_rule.y + frame.header_rule.width - 1


def _page_whose_drawing_is_narrow(interior: "_Interior") -> int:
    """A one-up puzzle page whose drawing is narrower than the usable width.

    Measured through ``compute_layout`` for each page's own puzzle, so the
    choice follows the corpus instead of naming a page number.
    """
    for number in interior.one_up:
        spec = book_page_spec(interior.book, number)
        columns, rows = interior.sizes[number]
        row_clues, column_clues = interior.clues[number]
        placement = compute_layout(row_clues, column_clues, spec).page
        if placement.drawing_right - placement.drawing_left < placement.usable_right - placement.usable_left:
            return number
    raise AssertionError("every puzzle page's drawing spans the whole text width")


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestBookPageFrame_HeaderRuleIsOnTheSameBaselineEverywhere:
    """AC-2 — a 0.6 pt rule under the header, at one y on every puzzle page."""

    def test_every_puzzle_page_carries_one_full_width_rule_in_its_band(self, interior) -> None:
        measured = {}
        for number in sorted(interior.one_up + interior.two_up):
            frame = interior.frame(number)
            rules = _rules_in(
                interior.pages[number],
                frame.header_rule.left,
                frame.header_rule.right,
                *_header_window(frame),
            )
            assert len(rules) == 1, f"page {number} drew {len(rules)} rules under its header"
            measured[number] = rules[0]
        assert len(measured) >= 3, "the corpus shrank: fewer than three puzzle pages"
        # Identical on every puzzle page, one-up and two-up alike — measured
        # off the ink, then compared with the frame.
        expected = interior.frame(interior.one_up[0]).header_rule.y
        for number, rule in measured.items():
            # Measured off the ink: the run of full-width rows at the band's
            # foot covers the one row every page's rule was asked for, and
            # starts within a pixel of it on every page.
            assert _holds(rule, expected), f"page {number}: {rule} does not cover y={expected}"
            assert abs(rule[0] - expected) <= 2, f"page {number}: {rule}"
        # One line, at one weight, on every puzzle page: the rule is lifted
        # clear of the drawing's own top edge (``INTERIOR_HEADER_RULE_LIFT``),
        # so a drawing spanning the whole text width does not merge its heavy
        # top border into this run. A rule drawn on the band's foot instead
        # would read 6 px here on exactly those pages and 3 px on the others.
        assert {rule[1] for rule in measured.values()} == {3}, measured

    def test_the_rule_is_the_pixels_0_6_pt_rounds_up_to(self, interior) -> None:
        """Measured on a page whose drawing does **not** span the text width.

        Chosen by measurement, not by page number: a page whose drawing is
        narrower than the usable width is the only one on which the full-width
        run at the band's foot is the header rule by itself.
        """
        number = _page_whose_drawing_is_narrow(interior)
        frame = interior.frame(number)
        thickness = _rules_in(
            interior.pages[number],
            frame.header_rule.left,
            frame.header_rule.right,
            *_header_window(frame),
        )[0][1]
        # 0.6 pt is 2.52 px at 300 DPI and a rule is rounded up, so 3 px.
        assert thickness == 3 == frame.header_rule.width
        assert thickness / DPI * 25.4 / MM_PER_POINT == pytest.approx(0.72, abs=0.01)
        assert INTERIOR_HEADER_RULE_PT == 0.6

    def test_the_rule_is_inside_the_band_and_clear_of_the_drawing(self, interior) -> None:
        """The rule is page furniture, not the drawing's own top border.

        FR-032 fixes a puzzle page's top edge at top margin + band. The rule
        sits an eighth of the band above that — far enough that the heaviest
        rule the book strokes cannot reach it from either side, which is what
        keeps it a line of its own on a page whose drawing fills the text
        width. Asserted by calling both, not by comparing two literals.
        """
        number = interior.one_up[0]
        spec = book_page_spec(interior.book, number)
        row_clues, column_clues = interior.clues[number]
        layout = compute_layout(row_clues, column_clues, spec)
        placement = layout.page
        frame = interior_frame(spec)
        assert frame.header_rule.y < placement.drawing_top
        assert frame.header_rule.y > placement.usable_top
        # Clear of the drawing by more than the heaviest rule on the page, so
        # the two cannot touch at any cell the book prints.
        assert placement.drawing_top - frame.header_rule.y > layout.thick_rule


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookPageFrame_FooterCarriesSizeAndFolio:
    """AC-3 — a hairline, the grid size on the inner side, the folio centred."""

    def test_a_hairline_spans_the_text_width_lighter_than_the_header_rule(self, interior) -> None:
        for number in interior.one_up:
            frame = interior.frame(number)
            rules = _rules_in(
                interior.pages[number],
                frame.footer_rule.left,
                frame.footer_rule.right,
                frame.footer_rule.y - 30,
                frame.footer_rule.y + 30,
            )
            assert len(rules) == 1, f"page {number} drew {len(rules)} footer rules"
            assert _holds(rules[0], frame.footer_rule.y)
            thickness = rules[0][1]
            # 0.4 pt is 1.67 px, rounded up to 2 — one pixel lighter than the
            # header's own rule, which is what makes it read as a hairline.
            assert thickness == 2
            assert thickness < frame.header_rule.width
        assert INTERIOR_FOOTER_RULE_PT == 0.4

    def test_the_grid_size_reads_w_x_h_on_the_inner_side(self, interior) -> None:
        """Which side is the inner one comes from the page's **parity**, not
        from the frame.

        Interior page 1 is the guide page and is right-hand (FR-043), so an
        odd page is right-hand, its gutter is on the left and the inner side
        *is* the left. Written out here rather than read off
        ``InteriorFrame.label_right_aligned``: a test that asked the frame
        which side to look at would follow the frame onto the wrong one and
        pass (measured — it did, against the mutant that swaps the two).
        """
        for number in interior.one_up:
            frame = interior.frame(number)
            columns, rows = interior.sizes[number]
            page = interior.pages[number]
            runs = _ink_columns(page, frame.footer_rule.y + 3, frame.baseline)
            assert runs, f"page {number} has no footer line"
            inner_is_left = number % 2 == 1
            centre = page.width // 2
            def on_the_inner_side(run) -> bool:
                return run[1] < centre if inner_is_left else run[0] > centre

            label_runs = [run for run in runs if on_the_inner_side(run)]
            assert label_runs, (
                f"page {number} is {'right' if inner_is_left else 'left'}-hand, "
                f"so its grid size belongs on the {'left' if inner_is_left else 'right'} "
                f"of the footer line, and the line's ink runs are {runs}"
            )
            outer_runs = [
                run
                for run in runs
                if not on_the_inner_side(run) and not (run[0] <= centre <= run[1])
            ]
            assert outer_runs == [], (
                f"page {number} set footer ink on its outer side: {outer_runs}. "
                "The outer corner is the QR's (CARD-223), not the label's"
            )
            # The label's own text, read off the call Pillow was given.
            assert grid_size_label(columns, rows) in _footer_texts(interior, number)

    def test_the_folio_is_centred_below_the_rule(self, interior) -> None:
        """Centred on the **trim's** own middle, read off the page's width.

        ``page.width // 2`` rather than ``InteriorFrame.folio_x``: the claim is
        that the page number lands in the same place on every page of the book,
        and a frame that centred it on the usable area instead would satisfy
        an assertion written against its own field.
        """
        for number in interior.one_up:
            frame = interior.frame(number)
            page = interior.pages[number]
            middle = page.width // 2
            runs = _ink_columns(page, frame.footer_rule.y + 3, frame.baseline)
            centred = [run for run in runs if run[0] <= middle <= run[1]]
            assert len(centred) == 1, f"page {number}: {runs} around x={middle}"
            first, last = centred[0]
            assert (first + last) // 2 == pytest.approx(middle, abs=3)
            assert str(number) in _footer_texts(interior, number)

    def test_both_footer_marks_hold_con020s_floor(self, interior) -> None:
        assert SIZE_LABEL_PT >= FLOOR_PT


def _footer_texts(interior: _Interior, page_number: int) -> List[str]:
    """What the footer's two marks were drawn with, read off ``draw.text``."""
    calls = _text_calls(interior)
    return [call.text for call in calls if call.page == page_number]


class _TextCall(SimpleNamespace):
    pass


def _text_calls(interior: _Interior) -> List[_TextCall]:
    """Every ``draw.text`` call the baseline interior makes, tagged by page.

    The same spy ``tests/test_book_page_numbers.py`` uses — recorded once and
    kept, because it needs its own export of the interior.
    """
    key = f"texts:{interior.book.book_id}"
    if key in _CACHE:
        return _CACHE[key]  # type: ignore[return-value]
    original = ImageDraw.ImageDraw.text
    calls: List[_TextCall] = []
    current = {"page": 0}

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        calls.append(
            _TextCall(page=current["page"], text=str(text), anchor=kwargs.get("anchor"), xy=xy)
        )
        return original(self, xy, text, fill, font, *args, **kwargs)

    ImageDraw.ImageDraw.text = spy  # noqa: B010 - restored below
    try:
        stream = BookPDFGenerator(interior.book).interior_stream(baseline_puzzles())
        pages = iter(stream.pages)
        drawn = 0
        while True:
            current["page"] = drawn + 1
            try:
                next(pages)
            except StopIteration:
                break
            drawn += 1
    finally:
        ImageDraw.ImageDraw.text = original  # noqa: B010
    _CACHE[key] = calls
    return calls


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestBookPageFrame_PuzzleAreaHasOneDefinition:
    """AC-4 — two page kinds read the same area from the same function."""

    def test_a_one_up_page_and_a_two_up_page_read_one_region(self, interior) -> None:
        one_up, two_up = interior.one_up[0], interior.two_up[0]
        # Deliberately *called*, not compared against literals: the two page
        # kinds ask ``interior_frame`` for their own page's region.
        first = interior.frame(one_up)
        second = interior.frame(two_up)
        assert (first.area_top, first.area_bottom) == (second.area_top, second.area_bottom)
        assert first.area_height > 0

    def test_the_area_is_the_two_rules_and_nothing_re_derived(self, interior) -> None:
        frame = interior.frame(interior.one_up[0])
        assert frame.area_top == frame.header_rule.y
        assert frame.area_bottom == frame.footer_rule.y
        assert frame.area_height == frame.footer_rule.y - frame.header_rule.y

    def test_the_region_does_not_move_with_what_is_drawn_on_it(self, interior) -> None:
        """A frame is the sheet's, so two different grids give one region."""
        spec = book_page_spec(interior.book, interior.one_up[0])
        assert interior_frame(spec) == interior_frame(spec)
        other = book_page_spec(interior.book, interior.one_up[0] + 2)  # same parity
        assert interior_frame(other) == interior_frame(spec)


# --------------------------------------------------------------------------
# AC-7
# --------------------------------------------------------------------------


class TestBookPageFrame_ShortestTrimStillHoldsTheFrame:
    """AC-7 — the shortest storable trim still holds both rules and a folio."""

    def test_the_frame_fits_the_ten_centimetre_trim(self) -> None:
        for page_number in (1, 2):
            frame = interior_frame(book_page_spec(_min_trim_book(), page_number))
            assert frame.area_height > 0
            assert frame.header_rule.y < frame.footer_rule.y < frame.baseline < frame.page_bottom

    def test_a_puzzle_page_on_that_trim_carries_the_frame_and_its_folio(self) -> None:
        """What a page on the 10 cm trim actually gets, measured.

        The header rule and the folio: both print on every puzzle page. The
        **footer group does not**, and the reason is not the frame — it is
        that the grid is still pinned to the band's foot and runs past the
        footer rule on a sheet with 62 mm of usable height and a 30 mm footer
        band, so the all-or-nothing footer condition omits the group exactly
        as it does on a page-fit-bound letter page. Measured here (0 of the
        trim's single-puzzle pages draw it) rather than claimed either way:
        CARD-224 places the grid inside the puzzle area, which is what frees
        the strip on this trim.
        """
        interior = _interior("min-trim", _min_trim_book(), baseline_puzzles())
        assert interior.one_up, "the shortest trim printed no single-puzzle page"
        footers = 0
        for number in interior.one_up:
            frame = interior.frame(number)
            header = _rules_in(
                interior.pages[number],
                frame.header_rule.left,
                frame.header_rule.right,
                *_header_window(frame),
            )
            assert len(header) == 1, f"page {number} has no header rule on the shortest trim"
            assert _holds(header[0], frame.header_rule.y)
            footers += len(
                _rules_in(
                    interior.pages[number],
                    frame.footer_rule.left,
                    frame.footer_rule.right,
                    frame.footer_rule.y - 10,
                    frame.footer_rule.y + 10,
                )
            )
            drawing_bottom = compute_layout(
                *interior.clues[number], book_page_spec(interior.book, number)
            ).page.drawing_bottom
            assert drawing_bottom > frame.footer_rule.y
        assert footers == 0, (
            "a page on the shortest trim now frees its footer strip: re-read "
            "this test's own reasoning before changing the number"
        )

    def test_the_frame_never_takes_a_folio_away_from_a_page_that_had_one(self) -> None:
        """AC-7's folio clause, held where CARD-200 itself holds it.

        On the 10 cm trim a page's own content can leave no room for a folio
        at all — ``tests/test_book_page_numbers.py``'s AC-1 excepts exactly
        that page, and this card must not make the exception any wider. So the
        claim is comparative: every page that carries a folio with the frame
        carried one before it, which is asserted by counting the folios the
        interior draws against the pages that have the room for one.
        """
        interior = _interior("min-trim", _min_trim_book(), baseline_puzzles())
        numbered = {
            call.page for call in _text_calls(interior) if call.text == str(call.page)
        }
        assert numbered, "the shortest trim numbered no page at all"
        for number in sorted(interior.one_up + interior.two_up):
            frame = interior.frame(number)
            page = interior.pages[number]
            # A page whose ink stops above the footer line has room, so it
            # must be numbered.
            ink = _ink(page)
            rows = np.where(ink.any(axis=1))[0]
            if rows.max() < frame.footer_rule.y:
                assert number in numbered, f"page {number} lost its folio"


# --------------------------------------------------------------------------
# F-2, F-3 — the frame's own boundaries
# --------------------------------------------------------------------------


class TestBookPageFrame_RefusesASheetThatIsNotABookPage:
    def test_a_spec_without_parity_has_no_frame(self) -> None:
        from nonogram.export.layout import DEFAULT_PAGE_SPEC

        with pytest.raises(ValueError, match="book_page_spec"):
            interior_frame(DEFAULT_PAGE_SPEC)


class TestBookPageFrame_RefusesAnInvertedPuzzleArea:
    def test_a_sheet_whose_band_and_footer_exhaust_it_is_refused(self) -> None:
        """F-3 — an inverted region is raised on, never handed back.

        The sheet below is legal to :class:`PageSpec` (its usable area is
        positive) and too short for a frame: 40 mm of height, 12 mm of band
        and a 29.878 mm footer band leave nothing between the rules.
        """
        spec = PageSpec(
            width_mm=100.0,
            height_mm=40.0,
            top_mm=5.0,
            bottom_mm=5.0,
            gutter_mm=7.0,
            outside_mm=7.0,
            band_mm=12.0,
            orientation=OrientationPolicy.PORTRAIT_ONLY,
            cell_cap=7.5,
            parity=PageParity.ODD,
        )
        with pytest.raises(ValueError, match="no puzzle area"):
            interior_frame(spec)


# --------------------------------------------------------------------------
# F-4 — the footer group is all-or-nothing
# --------------------------------------------------------------------------


class TestBookPageFrame_FooterIsOmittedWholeWhereContentReachesIt:
    """F-4 — a grid standing on the footer strip takes the whole group with it."""

    def test_a_page_fit_bound_puzzle_keeps_the_corner_folio_and_gets_no_footer_rule(self) -> None:
        # The page-fit-bound case CARD-200's own review measured, built here
        # rather than borrowed: a 30-wide, 30-tall grid whose rows carry one
        # run each and whose columns carry ten, so the fit is bound by the
        # *height* and the drawing's bottom edge is the bottom margin itself.
        tall = _height_bound_puzzle()
        book = corpus_book("card-222-tall")
        generator = BookPDFGenerator(book)
        stream = generator.interior_stream([tall])
        pages = list(stream.pages)
        plan = generator.section_plan([tall])
        numbers = [
            page.page_number for page in plan.pages if getattr(page, "numbers", None)
        ]
        assert numbers, "no puzzle page was planned"
        number = numbers[0]
        frame = interior_frame(book_page_spec(book, number))
        page = pages[number - 1]
        drawing_bottom = compute_layout(
            tuple(map(tuple, tall["clues_rows"])),
            tuple(map(tuple, tall["clues_cols"])),
            book_page_spec(book, number),
        ).page.drawing_bottom
        assert drawing_bottom > frame.footer_rule.y, "this fixture is no longer the tight case"
        # No footer rule: the strip is not free.
        assert (
            _rules_in(
                page,
                frame.footer_rule.left,
                frame.footer_rule.right,
                frame.footer_rule.y - 5,
                frame.footer_rule.y + 5,
            )
            == []
        )
        # The header rule is unconditional and still there.
        assert len(
            _rules_in(
                page,
                frame.header_rule.left,
                frame.header_rule.right,
                *_header_window(frame),
            )
        ) == 1

    def test_the_drawer_reports_which_footer_it_drew(self) -> None:
        """The verdict is returned, so a caller need not re-derive it."""
        from nonogram.admin.book_pdf_generator import _draw_page_frame

        frame = interior_frame(book_page_spec(None, 1))
        page = Image.new("RGB", (2550, 3300), (255, 255, 255))
        draw = ImageDraw.Draw(page)
        assert _draw_page_frame(draw, frame, 7, DPI, size_label="20 x 20") is True
        assert (
            _draw_page_frame(
                draw, frame, 7, DPI, size_label="20 x 20", content_bottom=frame.page_bottom
            )
            is False
        )


class TestBookPageFrame_TwoUpKeepsItsOuterFolio:
    """The exemption's control (ADR-0039/R3).

    A two-up page is exempt from the footer group — its lower slot's drawing
    is the bottom margin by construction. The exemption is held to: the page
    must still carry the header rule *and* the corner folio the lower slot
    reserves room for, so "exempt" cannot quietly become "unframed and
    unnumbered".
    """

    def test_a_two_up_page_has_the_header_rule_no_footer_rule_and_a_corner_folio(self, interior) -> None:
        assert interior.two_up, "the baseline book printed no two-up page"
        for number in interior.two_up:
            frame = interior.frame(number)
            page = interior.pages[number]
            assert len(
                _rules_in(
                    page,
                    frame.header_rule.left,
                    frame.header_rule.right,
                    *_header_window(frame),
                )
            ) == 1
            assert (
                _rules_in(
                    page,
                    frame.footer_rule.left,
                    frame.footer_rule.right,
                    frame.footer_rule.y - 5,
                    frame.footer_rule.y + 5,
                )
                == []
            )
            folio = [
                call
                for call in _text_calls(interior)
                if call.page == number and call.text == str(number)
            ]
            assert len(folio) == 1, f"page {number} drew {len(folio)} folios"
            assert folio[0].anchor in {"rb", "lb"}, "a two-up folio left CARD-200's corner"
            assert folio[0].xy[1] == frame.page_bottom


# --------------------------------------------------------------------------
# G-1 and the ADR-0037/R2 exemption
# --------------------------------------------------------------------------


#: The frame's own figures and the module-level name each is declared under.
#: The guard below walks every module in ``src/nonogram/`` with ``ast`` — the
#: structural style ``tests/test_cli.py``'s import guard uses, so it covers
#: code no test renders — and fails on a second **named constant** anywhere in
#: the package holding one of these values under a different name.
FRAME_FIGURES = {
    "INTERIOR_HEADER_RULE_PT": 0.6,
    "INTERIOR_FOOTER_RULE_PT": 0.4,
    "INTERIOR_FOOTER_GAP_PT": 9.0,
    "INTERIOR_FOOTER_LINE_PT": 10.0,
}

#: The constants that already held one of those values before this card, each
#: with the reason it is a different figure that happens to be the same
#: number. **An exemption is a claim** (ADR-0039/R3), so the control is in
#: ``test_no_exempt_constant_is_what_the_frame_actually_reads`` below: none of
#: these names may appear anywhere in the frame's own geometry function or in
#: its drawer, which is what would make one of them a second source for a
#: frame figure rather than an unrelated number.
#:
#: ``10.0`` is CON-020's type floor, which three constants state in points for
#: their own mark; ``MIN_TRIM_CM`` is 10 centimetres, a different unit
#: entirely; ``_RULE_LENGTH_RATIO`` is a fraction of a line's length, not a
#: stroke weight.
PRE_EXISTING_SAME_NUMBER = {
    ("book_page_spec.py", "MIN_TRIM_CM"),
    ("book_pdf_generator.py", "FOLIO_PT"),
    ("book_pdf_generator.py", "TOC_ENTRY_PT"),
    ("pdf.py", "_RULE_LENGTH_RATIO"),
}


def _named_float_constants(path: Path) -> List[Tuple[str, float]]:
    """``(name, value)`` for every module-level ``NAME = <float>`` in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: List[Tuple[str, float]] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, float)
            and isinstance(node.targets[0], ast.Name)
        ):
            found.append((node.targets[0].id, node.value.value))
    return found


def _function_source(path: Path, *names: str) -> str:
    """The source of the named top-level functions in ``path``, concatenated."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            out.append("".join(lines[node.lineno - 1 : node.end_lineno]))
    assert len(out) == len(names), f"{path.name}: found {len(out)} of {names}"
    return "".join(out)


def _package() -> List[Path]:
    package = Path(__file__).resolve().parent.parent / "src" / "nonogram"
    modules = sorted(package.rglob("*.py"))
    assert len(modules) >= 20, "the walk found almost nothing: check the path"
    return modules


class TestBookPageFrame_EachFigureIsDeclaredOnce:
    """G-1 — one source for each of the frame's figures."""

    def test_each_figure_is_declared_under_exactly_one_name(self) -> None:
        offenders: Dict[str, List[str]] = {}
        for name, value in FRAME_FIGURES.items():
            for module in _package():
                for declared, literal in _named_float_constants(module):
                    if literal != value or declared == name:
                        continue
                    if (module.name, declared) in PRE_EXISTING_SAME_NUMBER:
                        continue
                    offenders.setdefault(name, []).append(f"{module.name}:{declared}")
        assert offenders == {}, offenders

    def test_every_exemption_is_a_constant_that_really_exists(self) -> None:
        """The allow-list is held to an equality against today's sites.

        ADR-0039/R3: an exemption is a claim. A name that leaves the package
        must leave this list with it, or the list is a licence for whatever
        takes that name next.
        """
        declared = {
            (module.name, name)
            for module in _package()
            for name, _ in _named_float_constants(module)
        }
        assert PRE_EXISTING_SAME_NUMBER <= declared, PRE_EXISTING_SAME_NUMBER - declared

    def test_no_exempt_constant_is_what_the_frame_actually_reads(self) -> None:
        """The exemption's control (ADR-0039/R3): none of them is read by the
        frame.

        What the exemption must not absorb is a frame figure wearing one of
        these names. With the exemption in place and the frame reading its own
        constants, this passes; replace one of the frame's reads with an
        exempt name — ``FOLIO_PT`` for ``INTERIOR_FOOTER_LINE_PT``, say — and
        it fails, because the name then appears in the source this test
        greps. Measured, not argued: that substitution is one of this card's
        recorded mutants.
        """
        package = Path(__file__).resolve().parent.parent / "src" / "nonogram"
        frame_source = _function_source(
            package / "export" / "layout.py", "interior_frame", "_usable_box_px"
        ) + _function_source(
            package / "admin" / "book_pdf_generator.py", "_draw_page_frame", "_draw_rule"
        )
        for _, name in PRE_EXISTING_SAME_NUMBER:
            assert name not in frame_source, name

    def test_the_frames_geometry_reads_names_and_never_a_number(self) -> None:
        """Every figure in ``interior_frame`` comes from a constant.

        The only numeric literals left are the ``1`` that takes the header
        lift's complement and the ``2``s that halve the trim for the folio and
        count the band's two gaps, so a figure cannot be restated inside the
        function that places it.
        """
        package = Path(__file__).resolve().parent.parent / "src" / "nonogram"
        source = _function_source(package / "export" / "layout.py", "interior_frame")
        numbers = [
            node.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ]
        # ``1`` takes the lift's complement and ``2`` halves the trim and
        # counts the band's two gaps; every figure proper is a name.
        assert set(numbers) <= {1, 2}, numbers

    def test_the_margins_are_declared_only_in_the_profile(self) -> None:
        offenders = []
        for module in _package():
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                for keyword in node.keywords:
                    if keyword.arg in {"top_in", "bottom_in", "outside_in", "gutter_in"}:
                        offenders.append(module.name)
        assert set(offenders) <= {"book_page_spec.py"}, offenders

    def test_the_footer_band_is_derived_from_the_icon_it_has_to_hold(self) -> None:
        assert INTERIOR_FOOTER_MM > QR_SLOT_MM
        assert INTERIOR_FOOTER_MM == pytest.approx(
            QR_SLOT_MM
            + FRAME_FIGURES["INTERIOR_FOOTER_LINE_PT"] * MM_PER_POINT
            + 2 * FRAME_FIGURES["INTERIOR_FOOTER_GAP_PT"] * MM_PER_POINT
        )


class TestBookPageFrame_TheHairlineIsNotAGridRule:
    """The ADR-0037/R2 exemption's control.

    The footer hairline is page furniture, deliberately lighter than R2's
    0.25 mm minimum for a **grid** rule. Both halves are asserted, so the
    exemption cannot grow to cover the grid: the hairline is lighter than the
    thin grid rule, and the thin grid rule on the same page is still at or
    above 0.25 mm.
    """

    def test_the_hairline_is_lighter_than_the_grid_rule_which_still_holds_r2(self) -> None:
        spec = book_page_spec(corpus_book(), 1)
        frame = interior_frame(spec)
        clues = tuple((1,) * 6 for _ in range(30))
        layout = compute_layout(clues, clues, spec)
        assert frame.footer_rule.width < layout.thin_rule
        assert layout.thin_rule / DPI * 25.4 >= 0.25
        assert frame.footer_rule.width / DPI * 25.4 < 0.25


class TestBookPageFrame_MirroringBitesOnUnequalMargins:
    """Mirroring is proved where it is observable, not on the default profile.

    On Book 1 the gutter and the outside margin are both 12.700 mm, so the
    frame's rules land on the same pixels at either parity — an identity. On a
    book storing unequal margins the frame really does mirror, and the two
    assertions below fail if it stops.
    """

    def test_the_rules_and_the_label_swap_sides_with_parity(self) -> None:
        book = _unequal_book()
        odd = interior_frame(book_page_spec(book, 3))
        even = interior_frame(book_page_spec(book, 4))
        trim = compute_layout(((1,),), ((1,),), book_page_spec(book, 3)).width
        assert odd.header_rule.left != even.header_rule.left
        assert odd.header_rule.right != even.header_rule.right
        # A true mirror: each edge is the other page's opposite edge,
        # reflected in the trim.
        assert odd.header_rule.left == trim - even.header_rule.right
        assert odd.header_rule.right == trim - even.header_rule.left
        # The label follows the gutter: the left edge on an odd page, the
        # right on an even one.
        assert (odd.label_x, odd.label_right_aligned) == (odd.header_rule.left, False)
        assert (even.label_x, even.label_right_aligned) == (even.header_rule.right, True)

    def test_the_folio_does_not_move_with_parity(self) -> None:
        book = _unequal_book()
        assert (
            interior_frame(book_page_spec(book, 3)).folio_x
            == interior_frame(book_page_spec(book, 4)).folio_x
        )

    def test_on_the_default_profile_the_same_claim_is_an_identity(self) -> None:
        """Recorded, so nobody reads the Book 1 case as evidence (CON-018)."""
        odd = interior_frame(book_page_spec(corpus_book(), 3))
        even = interior_frame(book_page_spec(corpus_book(), 4))
        assert odd.header_rule == even.header_rule
        assert odd.label_x != even.label_x  # the side still differs
