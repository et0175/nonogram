"""CARD-391 -- puzzle pages carry no QR: the footer points at the Play online page.

The owner removed the per-puzzle QR code on 2026-11-07 (ADR-0041/R8, "version B,
puzzle pages without a code"): a puzzle page's footer is a hairline rule, the
grid size on the inner side and, on the outer side, one short line --
``Play puzzle 53 online · p. 167``; a two-up page shares ONE such line,
``Play 9 and 10 online · p. 167``, and prints no grid size; a book
with no (valid) player domain prints no pointer. This file holds the claims
that card made and the footer claims of CARD-223/CARD-248 that survived it.

    AC-1  tests/test_book_play_online_page.py::
          test_no_interior_page_but_the_play_page_carries_a_qr
          (ADR-0041/R8's planned ref lives beside the code it counts)
    AC-2  TestFooterPointer_NamesThePuzzleAndThePlayPage
    AC-3  TestFooterPointer_TwoUpSharesOneLine
    AC-4  TestFooterPointer_AbsentWithoutADomain
    AC-5  TestFooterPointer_NamesARealPlayPage
    AC-6  (the held geometry; CARD-392 changed it on purpose, its successor is
          TestPuzzlePages_OnlyAreaDependentMarksMove, CARD-392's AC-7)
    AC-7  TestTwoUp_BookOneVerdictsUnchanged,
          TestTwoUp_NarrowTrimsNowPairOnHeightAndWidthAlone
          TestFooterPointer_YieldsRatherThanCollideWithTheFolio  (the one new
          decision: a line the folio would collide with is not printed)

The footer claims that survived the QR code (the cell cost of the reserved
strip, the pair that cannot fit, the two-up folio) stay in
``tests/test_book_qr_slot.py``, which keeps its name for the reason its own
docstring gives. Every expected string below is a LITERAL built from the book's own numbers (its print numbers and the plan's
Play page), never from ``footer_pointer_text``.

What was retired from the old file, and why, is the CARD-391 closing note's
table: every claim about the QR (the slot's size, corner, caption, typed link,
placeholder glyph, gutter-side ink, the width a pair needed for two groups) is
superseded by the owner's decision, and each retirement names the survivor
here that holds the part of the claim that does not depend on the QR.
"""

from __future__ import annotations

import copy
import random
import re
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from nonogram import clues
from nonogram.admin.book_interior_vector import interior_generator
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    PuzzlePagePlan,
    page_is_right_hand,
)
from nonogram.export import ExportPayload
import nonogram.export.layout as layout_module
from nonogram.export.layout import (
    INTERIOR_FOOTER_MM,
    OrientationPolicy,
    PageParity,
    PageSpec,
    footer_pointer,
    interior_frame,
)
from tests.helpers import pdf_vector
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, corpus_puzzles, puzzle

DPI = 300
PX_PER_MM = DPI / 25.4

#: CON-018's Book 1 profile, in millimetres -- the same stated-from-the-spec
#: construction every other footer/frame test file uses, written out here
#: rather than imported.
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
MIN_THIN_RULE_MM = 0.25

#: The unequal sheet's two side margins, in millimetres: neither is a Book 1
#: figure and the two differ by 12 mm, so "which side" claims made on it cannot
#: pass by reading the wrong margin.
UNEQUAL_GUTTER_MM = 19.0
UNEQUAL_OUTSIDE_MM = 7.0

DOMAIN = "https://nonogram.adverax.io"

#: FR-040's two-up minimum, in millimetres -- written out rather than
#: imported, so a claim about the boundary is not the same constant on both
#: sides.
TWO_UP_MINIMUM_MM = 7.0

#: The footer strip's depth in device pixels, stated from the one-line footer's own
#: two rows rather than read off :data:`INTERIOR_FOOTER_MM`: one 10 pt line and
#: 9 pt of white twice, 28 pt = 9.878 mm (CARD-392; 29.878 mm with the 20 mm
#: QR row before it).
FOOTER_STRIP_PX = 117

def _spec(
    *,
    parity: PageParity = PageParity.ODD,
    width_mm: float = BOOK1_WIDTH_MM,
    height_mm: float = BOOK1_HEIGHT_MM,
    gutter_mm: float = GUTTER_MM,
    outside_mm: float = OUTSIDE_MM,
    **overrides: object,
) -> PageSpec:
    return PageSpec(
        width_mm=width_mm,
        height_mm=height_mm,
        top_mm=TOP_MM,
        bottom_mm=BOTTOM_MM,
        gutter_mm=gutter_mm,
        outside_mm=outside_mm,
        band_mm=BAND_MM,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=MIN_THIN_RULE_MM,
        parity=parity,
        **overrides,
    )


def _unequal_spec(parity: PageParity) -> PageSpec:
    """Book 1's trim with a gutter and an outside margin that **differ**."""
    return _spec(parity=parity, gutter_mm=UNEQUAL_GUTTER_MM, outside_mm=UNEQUAL_OUTSIDE_MM)


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> List[List[bool]]:
    """A grid whose row clues are ``row_depth`` deep and columns ``column_depth``."""
    if 2 * row_depth - 1 > columns or 2 * column_depth - 1 > rows:
        raise ValueError(
            f"a {columns}x{rows} grid cannot carry {row_depth}-deep row clues "
            f"and {column_depth}-deep column clues"
        )
    grid = [[False] * columns for _ in range(rows)]
    for step in range(row_depth):
        grid[0][2 * step] = True
    for step in range(column_depth):
        grid[2 * step][0] = True
    return grid


def _clue_sets(columns: int, rows: int, row_depth: int, column_depth: int):
    found = clues.compute_clues(_grid(columns, rows, row_depth, column_depth))
    return found.rows, found.columns


def _payload(columns: int, rows: int, row_depth: int, column_depth: int) -> ExportPayload:
    grid = _grid(columns, rows, row_depth, column_depth)
    found = clues.compute_clues(grid)
    return ExportPayload(
        grid=grid,
        row_clues=found.rows,
        column_clues=found.columns,
        seed=223,
        mode="random",
        name="footer-pointer-test",
        difficulty="Easy",
    )


# ==========================================================================
# CARD-391 -- fixtures
# ==========================================================================


def _domain_book(trim_mm: Optional[Tuple[float, float]] = None, book_id: str = "card391"):
    """Book 1 with a stored player domain (so it prints a Play page and pointers)."""
    book = copy.copy(corpus_book(book_id))
    book.player_domain = DOMAIN
    if trim_mm is not None:
        book.trim_width_cm = f"{trim_mm[0] / 10:.2f}"
        book.trim_height_cm = f"{trim_mm[1] / 10:.2f}"
    return book


def _no_domain_book(book_id: str = "card391-bare"):
    book = copy.copy(corpus_book(book_id))
    book.player_domain = None
    return book


def _hard_pairs(count: int) -> List[dict]:
    """``count`` small Hard puzzles: neighbours pair two to a page."""
    return [puzzle(f"c391-{i}", 10, 10, 3, "hard", f"Hard {i}") for i in range(count)]


def _poppler() -> None:
    if pdf_vector.PDFTOTEXT is None:
        pytest.skip("poppler (pdftotext) is not installed: the text layer cannot be read")


class _Export:
    """One book exported once: its plan, its file, and a reader of its pages."""

    def __init__(self, book, puzzles: List[dict], tmp_path: Path) -> None:
        _poppler()
        self.generator = interior_generator(book)
        self.plan = self.generator.section_plan(list(puzzles))
        self.data = self.generator.export_interior(puzzles).getvalue()
        self.kinds = [
            kind.value for kind in self.generator.interior_stream(puzzles).page_kinds
        ]
        self.tmp_path = tmp_path

    @property
    def puzzle_pages(self) -> List[PuzzlePagePlan]:
        return [entry for entry in self.plan.pages if isinstance(entry, PuzzlePagePlan)]

    def footer_words(self, page_number: int) -> list:
        """The words on the page's footer line, left to right."""
        words = pdf_vector.word_boxes(self.data, page=page_number, out_dir=self.tmp_path)
        baseline = interior_frame(self.generator.page_spec(page_number)).baseline * 72 / DPI
        # poppler's box runs one descent below the baseline the stream sets
        line = [word for word in words if baseline <= word.bottom <= baseline + 5]
        return sorted(line, key=lambda word: word.left)

    def width_pt(self) -> float:
        match = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", self.data)
        assert match, "no MediaBox"
        return float(match.group(1))


def _sequence_at(words: list, tokens: List[str]) -> Optional[list]:
    """The run of ``words`` whose texts are exactly ``tokens``, or ``None``."""
    texts = [word.text for word in words]
    for start in range(len(texts) - len(tokens) + 1):
        if texts[start : start + len(tokens)] == tokens:
            return words[start : start + len(tokens)]
    return None


def _centre(words: list) -> float:
    return (min(word.left for word in words) + max(word.right for word in words)) / 2


def _on_outer_side(words: list, page_width_pt: float, page_number: int) -> bool:
    """Whether ``words`` lie wholly in the half of the trim away from the spine."""
    middle = page_width_pt / 2
    if page_is_right_hand(page_number):
        return min(word.left for word in words) > middle
    return max(word.right for word in words) < middle


# ==========================================================================
# AC-2 -- the pointer, on a single puzzle page
# ==========================================================================


class TestFooterPointer_NamesThePuzzleAndThePlayPage:
    def test_it_is_on_the_outer_side_at_both_parities_and_the_grid_size_on_the_inner(
        self, tmp_path
    ) -> None:
        rows = corpus_puzzles(5)
        export = _Export(_domain_book(), rows, tmp_path)
        width = export.width_pt()
        play = export.plan.play_page
        assert play is not None
        hands = set()
        checked = 0
        for entry in export.puzzle_pages:
            (number,) = entry.numbers
            hands.add(page_is_right_hand(entry.page_number))
            words = export.footer_words(entry.page_number)
            expected = f"Play puzzle {number} online · p. {play}".split()
            found = _sequence_at(words, expected)
            assert found is not None, (entry.page_number, [w.text for w in words])
            assert _on_outer_side(found, width, entry.page_number), entry.page_number
            columns, height = rows[number - 1]["width"], rows[number - 1]["height"]
            label = _sequence_at(words, [str(columns), "x", str(height)])
            assert label is not None, (entry.page_number, [w.text for w in words])
            # the inner side is the other half of the trim
            assert (_centre(label) > width / 2) is not page_is_right_hand(entry.page_number)
            checked += 1
        assert hands == {True, False}, "both parities are exercised"
        assert checked == 5


# ==========================================================================
# AC-3 -- one shared line on a two-up page
# ==========================================================================


class TestFooterPointer_TwoUpSharesOneLine:
    def test_one_line_naming_both_puzzles_on_the_outer_side_and_no_grid_size(
        self, tmp_path
    ) -> None:
        export = _Export(_domain_book(), _hard_pairs(4), tmp_path)
        width = export.width_pt()
        play = export.plan.play_page
        two_up = [entry for entry in export.puzzle_pages if entry.pair is not None]
        assert [entry.numbers for entry in two_up] == [(1, 2), (3, 4)]
        assert {page_is_right_hand(entry.page_number) for entry in two_up} == {True, False}
        for entry in two_up:
            first, second = entry.numbers
            words = export.footer_words(entry.page_number)
            expected = f"Play {first} and {second} online · p. {play}".split()
            found = _sequence_at(words, expected)
            assert found is not None, (entry.page_number, [w.text for w in words])
            assert _on_outer_side(found, width, entry.page_number)
            assert [w.text for w in words].count("Play") == 1, "exactly one pointer"
            assert "x" not in [w.text for w in words], "no grid-size label on a two-up page"


# ==========================================================================
# AC-4 -- no domain, no pointer
# ==========================================================================


class TestFooterPointer_AbsentWithoutADomain:
    def test_the_footer_carries_the_grid_size_and_the_folio_only(self, tmp_path) -> None:
        for book in (_no_domain_book(), _hard_domain_free_with_invalid_domain()):
            export = _Export(book, baseline_puzzles(), tmp_path)
            assert export.plan.play_page is None
            assert "play" not in export.kinds
            for entry in export.puzzle_pages:
                texts = [word.text for word in export.footer_words(entry.page_number)]
                assert "Play" not in texts and "online" not in texts, texts
                assert str(entry.page_number) in texts
                assert ("x" in texts) is (entry.pair is None), texts


def _hard_domain_free_with_invalid_domain():
    """A hand-edited stored domain the validator refuses behaves as no domain."""
    book = copy.copy(corpus_book("card391-invalid"))
    book.player_domain = "not a domain"
    return book


# ==========================================================================
# AC-5 -- the pointer is true
# ==========================================================================


class TestFooterPointer_NamesARealPlayPage:
    def test_every_page_a_pointer_names_is_a_play_page_of_the_file(self, tmp_path) -> None:
        books = [
            (_domain_book(), baseline_puzzles()),
            (_domain_book(), corpus_puzzles(4)),  # ends on a recto: a blank precedes
            (_domain_book(), corpus_puzzles(5)),  # ends on a verso: no blank
            (_domain_book(), _hard_pairs(3)),  # a pair and a single
        ]
        pointers = 0
        for book, rows in books:
            export = _Export(book, rows, tmp_path)
            for entry in export.puzzle_pages:
                words = export.footer_words(entry.page_number)
                texts = [word.text for word in words]
                start = texts.index("Play")
                named = int(texts[start + texts[start:].index("p.") + 1])
                assert export.kinds[named - 1] == "play", (entry.page_number, named)
                on_it = pdf_vector.word_boxes(export.data, page=named, out_dir=tmp_path)
                assert any(w.text.startswith("nonogram.adverax.io/b/") for w in on_it)
                assert on_it[-1].text == str(named), "its own folio"
                pointers += 1
        assert pointers >= 10, pointers


# ==========================================================================
# CARD-392 AC-7 -- only the marks that depend on the area move
# ==========================================================================

def _stream_marks(book, rows: List[dict], tmp_path) -> dict:
    """``{page: (numbers, stroke widths, type sizes)}`` for each puzzle page.

    The three things AC-7 names as independent of the area: the rule weights
    (ADR-0037/R2's three fixed weights), every point size the page sets (the
    clue digits' and the band's among them), and which puzzles share the page.
    """
    export = _Export(book, rows, tmp_path)
    streams = pdf_vector.content_streams(export.data)
    return {
        entry.page_number: (
            entry.numbers,
            sorted(pdf_vector.stroke_widths(streams[entry.page_number - 1])),
            sorted(pdf_vector.type_sizes(streams[entry.page_number - 1])),
        )
        for entry in export.puzzle_pages
    }


def unequal_book(book_id: str = "card391-unequal"):
    book = copy.copy(corpus_book(book_id))
    book.player_domain = None
    book.gutter_margin_cm = f"{UNEQUAL_GUTTER_MM / 10:.2f}"
    book.outside_margin_cm = f"{UNEQUAL_OUTSIDE_MM / 10:.2f}"
    return book


GEOMETRY_CORPUS = {
    "baseline": (lambda: _no_domain_book("card391-geometry"), baseline_puzzles),
    "singles": (lambda: _no_domain_book("card391-geometry-singles"), lambda: corpus_puzzles(5)),
    "pairs": (lambda: _no_domain_book("card391-geometry-pairs"), lambda: _hard_pairs(4)),
    "unequal": (unequal_book, baseline_puzzles),
}


class TestPuzzlePages_OnlyAreaDependentMarksMove:
    """CARD-392 AC-7: the band shrank by 20 mm and nothing else was told.

    The control is the same code with the footer band put back to its height
    before this card (``INTERIOR_FOOTER_MM`` + 20 mm, patched in process): the
    two exports differ in the area and in nothing else the test lets differ.
    A single puzzle page's cell is fitted against the usable height less the
    band, not against the footer band, so it keeps its cell and with it every
    point size; the rule weights are fixed points. A pair is the exception
    (its cell *is* fitted against the area), so a pair's type sizes are allowed
    to scale and its weights are not.

    **One reading of AC-7 is not kept, and the reason is arithmetic.** The
    card lists the folio's position "relative to the page bottom" among the
    marks that stay put. It cannot: the footer rule sits one band above the
    bottom margin and the folio sits one line below the rule, so shrinking the
    band by 20 mm moves the folio down by 20 mm (274 px -> 38 px above the
    page's bottom edge on Book 1, measured). What stays is the folio's
    position relative to the *rule* (79 px) and its x, held below.
    """

    def test_weights_sizes_and_sharing_hold_and_the_folio_keeps_its_place_in_the_band(
        self, tmp_path, monkeypatch
    ) -> None:
        assert INTERIOR_FOOTER_MM == pytest.approx(9.878, abs=1e-3)
        frames = {}
        for trim in ("book1", "6x9", "5x8"):
            width, height = {"book1": (21.59, 27.94), "6x9": (15.24, 22.86), "5x8": (12.7, 20.32)}[trim]
            book = _no_domain_book(f"card392-frame-{trim}")
            book.trim_width_cm, book.trim_height_cm = f"{width:.2f}", f"{height:.2f}"
            frames[trim] = [interior_frame(BookPDFGenerator(book).page_spec(n)) for n in (1, 2)]
        after = {}
        for label, (make_book, make_rows) in GEOMETRY_CORPUS.items():
            after[label] = _stream_marks(make_book(), make_rows(), tmp_path)

        monkeypatch.setattr(layout_module, "INTERIOR_FOOTER_MM", INTERIOR_FOOTER_MM + 20.0)
        before = {}
        for label, (make_book, make_rows) in GEOMETRY_CORPUS.items():
            before[label] = _stream_marks(make_book(), make_rows(), tmp_path)
        control_frame = interior_frame(_spec())
        monkeypatch.undo()

        compared = singles = 0
        for label in GEOMETRY_CORPUS:
            for page, (numbers, weights, sizes) in after[label].items():
                was = before[label].get(page)
                if was is None or was[0] != numbers:
                    continue  # the band gave this page a different make-up
                assert weights == was[1], (label, page, "a rule weight moved")
                if len(numbers) == 1:
                    assert sizes == was[2], (label, page, "a point size moved")
                    singles += 1
                compared += 1
        assert compared >= 10 and singles >= 8, (compared, singles)

        # The frame, per trim, against the control's own figures read off the
        # same code with the old band: the header rule, the rule weights, the
        # folio's x and its distance from the footer rule are the band's, the
        # rest of the frame is the area.
        now = interior_frame(_spec())
        assert now.header_rule == control_frame.header_rule
        assert now.footer_rule.width == control_frame.footer_rule.width
        assert (now.folio_x, now.label_x) == (control_frame.folio_x, control_frame.label_x)
        # The folio sits 79 px under the rule (the line plus a gap, 10 + 9 pt),
        # on main before this card and now. What moved is its distance from the
        # page's bottom edge, 274 px on main (measured from main's frame) and
        # 38 px now: the band's 20 mm.
        assert now.baseline - now.footer_rule.y == 79
        assert now.page_bottom - now.baseline == 38
        assert control_frame.footer_rule.y - now.footer_rule.y == -236
        assert all(f.baseline - f.footer_rule.y == 79 for pair in frames.values() for f in pair)


# ==========================================================================
# AC-7 -- pairing: Book 1 unchanged, narrow trims now pair
# ==========================================================================


def _pairing_corpus() -> List[dict]:
    """Thirty seeded puzzles in three tiers, of the sizes that pair and that do not."""
    rng = random.Random(391)
    tiers = ["easy", "medium", "hard"]
    rows = []
    for index in range(30):
        rows.append(
            puzzle(
                f"card391-pairing-{index + 1}",
                rng.randint(8, 20),
                rng.randint(6, 14),
                rng.choice((1, 2)),
                tiers[index * 3 // 30],
                f"P{index + 1}",
            )
        )
    return rows


#: The pages of the corpus above on Book 1 under the one-line footer
#: (CARD-392). Recorded from main at a4ebdd53 before it, the walk left 11, 16
#: standing alone and paired the rest ((11,), (12, 13), (14, 15), (16,), (17,
#: 18)); the 20 mm the footer band gave back lifts the pair boundary from 28
#: to 31 combined cells, and 11 + 12 and 16 + 17 now fit (measured with the
#: walk in this worktree; the tiers are 10 puzzles each, so no pair crosses
#: one, and the refusing verdict is held by the AC-4 class in
#: ``tests/test_book_pdf_two_up.py``, stated from the sheet by hand).
BOOK_ONE_PAGES_NOW = [
    (1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16),
    (17, 18), (19, 20), (21, 22), (23, 24), (25, 26), (27, 28), (29, 30),
]  # fmt: skip


class TestTwoUp_BookOneVerdictsFollowTheFreedHeight:
    def test_the_walk_pairs_what_the_one_line_footer_lets_it(self) -> None:
        generator = BookPDFGenerator(_no_domain_book("card391-verdicts"))
        plan = generator.section_plan(_pairing_corpus())
        pages = [e.numbers for e in plan.pages if isinstance(e, PuzzlePagePlan)]
        assert pages == BOOK_ONE_PAGES_NOW
        # The refusing verdict is held where it is stated from first
        # principles: TestTwoUp_ThresholdsRederivedFromTheOneLineFooter.


class TestTwoUp_NarrowTrimsNowPairOnHeightAndWidthAlone:
    def test_a_6_by_9_book_pairs_what_main_printed_on_two_pages(self) -> None:
        """AC-377 said no pair could print on a 6 x 9 in trim, because two QR
        groups did not fit across its 127 mm; with the groups gone the pair is
        judged by FR-040's height and width rules alone. Four 10 x 8 Easies
        print as four single pages on main (the recorded verdict) and as two
        pairs now; four 12 x 12 ones still do not pair, on the height rule
        (CARD-392: four 10 x 10 ones, 22 cells, pair since the band shrank --
        the 6 x 9 boundary is 24 cells, 168.786 mm / 7.0)."""
        book = _no_domain_book("card391-6x9")
        book.trim_width_cm = "15.24"
        book.trim_height_cm = "22.86"
        generator = BookPDFGenerator(book)

        def pages(columns: int, rows: int) -> list:
            found = [puzzle(f"c391-narrow-{i}", columns, rows, 1, "easy", f"N{i}") for i in range(4)]
            return [
                e.numbers
                for e in generator.section_plan(found).pages
                if isinstance(e, PuzzlePagePlan)
            ]

        assert pages(10, 8) == [(1, 2), (3, 4)]  # main: [(1,), (2,), (3,), (4,)]
        assert pages(12, 12) == [(1,), (2,), (3,), (4,)]  # 26 cells of height: refused


# ==========================================================================
# The pointer yields to the folio (the one decision this card makes)
# ==========================================================================


class TestFooterPointer_YieldsRatherThanCollideWithTheFolio:
    def test_the_line_is_placed_to_the_pixel_and_declined_one_pixel_past_it(self) -> None:
        """``footer_pointer`` keeps one footer gap (9 pt = 38 px) between the
        line's inner end and the folio's ink (a reserve of 100 px, half each
        side of the trim's centre); the room is worked by hand from the
        frame's outer edge and the trim's centre."""
        for parity in (PageParity.ODD, PageParity.EVEN):
            frame = interior_frame(_spec(parity=parity))
            if parity is PageParity.ODD:
                room = frame.footer_rule.right - 38 - (frame.folio_x + 50)
            else:
                room = (frame.folio_x - 50) - 38 - frame.footer_rule.left
            fits = footer_pointer(frame, room, 100)
            assert fits is not None
            assert fits.right_aligned is (parity is PageParity.ODD)
            assert fits.x == (
                frame.footer_rule.right if parity is PageParity.ODD else frame.footer_rule.left
            )
            assert footer_pointer(frame, room + 1, 100) is None

    def test_both_lines_print_on_6_by_9_and_neither_on_5_by_8(self, tmp_path) -> None:
        """The boundary, measured. At 10 pt the single line is 52.3 mm and the
        shared two-up line 51.0 mm (two-digit numbers; the owner dropped the
        word "puzzles" from it on 2026-11-08), against 55.8 mm of room between
        a 6 x 9 in page's outer margin and its folio and 43.0 mm on 5 x 8 in:
        both print on the first, neither on the second. For two-digit numbers
        the smallest trim where both fit is about 145.5 mm (5.73 in) wide (the
        single line decides; the shared one alone would fit from 142.9 mm)."""
        rows = [puzzle(f"c391-six-{i}", 10, 7, 1, "easy", f"E{i}") for i in range(3)]
        for trim, prints in (((152.4, 228.6), True), ((127.0, 203.2), False)):
            export = _Export(_domain_book(trim, f"card391-{trim[0]}"), rows, tmp_path)
            by_numbers = {entry.numbers: entry for entry in export.puzzle_pages}
            assert set(by_numbers) == {(1, 2), (3,)}, trim
            for numbers in ((3,), (1, 2)):
                texts = [w.text for w in export.footer_words(by_numbers[numbers].page_number)]
                assert ("Play" in texts) is prints, (trim, numbers, texts)
                assert str(by_numbers[numbers].page_number) in texts
