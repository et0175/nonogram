"""CARD-391 -- puzzle pages carry no QR: the footer points at the Play online page.

The owner removed the per-puzzle QR code on 2026-11-07 (ADR-0041/R8, "version B,
puzzle pages without a code"): a puzzle page's footer is a hairline rule, the
grid size on the inner side and, on the outer side, one short line --
``Play puzzle 53 online · p. 167``; a two-up page shares ONE such line,
``Play puzzles 9 and 10 online · p. 167``, and prints no grid size; a book
with no (valid) player domain prints no pointer. This file holds the claims
that card made and the footer claims of CARD-223/CARD-248 that survived it.

    AC-1  tests/test_book_play_online_page.py::
          test_no_interior_page_but_the_play_page_carries_a_qr
          (ADR-0041/R8's planned ref lives beside the code it counts)
    AC-2  TestFooterPointer_NamesThePuzzleAndThePlayPage
    AC-3  TestFooterPointer_TwoUpSharesOneLine
    AC-4  TestFooterPointer_AbsentWithoutADomain
    AC-5  TestFooterPointer_NamesARealPlayPage
    AC-6  TestPuzzlePages_GeometryHeldExceptTheFooter
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
import hashlib
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

#: The footer strip's depth in device pixels, stated from CON-020's own three
#: rows rather than read off :data:`INTERIOR_FOOTER_MM`: the 20 mm row the QR
#: icon used to fill (still reserved, CARD-392 shrinks it), one 10 pt line and
#: 9 pt of white twice. 29.878 mm.
FOOTER_STRIP_PX = 353

#: How many cells of combined drawing height a Book 1 pair may have, with and
#: without the strip reserved, before its shared cell falls under 7.0 mm. Both
#: stated from the usable height by hand (253.492 mm less two 12 mm bands, less
#: the strip for the second), never from ``compute_pair_layout``:
#:
#:     unreserved  229.492 / 7.0 = 32.78  ->  32 cells
#:     reserved    199.605 / 7.0 = 28.51  ->  28 cells
#:
#: so the pairs the strip refuses are **exactly** those whose combined drawing
#: height is 29, 30, 31 or 32 cells.
MAX_PAIR_CELLS_UNRESERVED = 32
MAX_PAIR_CELLS_RESERVED = 28
NEWLY_REFUSED_PAIR_CELLS = frozenset({29, 30, 31, 32})


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
            expected = f"Play puzzles {first} and {second} online · p. {play}".split()
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
# AC-6 -- the geometry is held; only the QR left and the line arrived
# ==========================================================================

#: sha-256 of the decoded content stream of each puzzle page below, recorded
#: from main at a4ebdd53 (the commit this card was cut from) with the QR group
#: switched off in-process, on the corpora named by the keys. They pin
#: that, apart from the removed group, every mark on every puzzle page -- grid,
#: clue boxes, band, rules, folio -- is at the coordinate it was at before this
#: card, and that the footer band's height is unchanged. Never regenerated to
#: make a test pass: a page that stops matching is either a deliberate
#: geometry change (CARD-392's, which earns its own successor) or a regression.
MAIN_PAGE_DIGESTS = {
    "baseline:6": (
        "41bb74ea1ddc7020773cf414a943f9344f207c0feeae3be11f9df71d1b35bbd2"
    ),
    "baseline:8": (
        "ee99aa8749c00243211bd3477229522b528ce10647db0b9bd4447c5a0fa58d47"
    ),
    "baseline:10": (
        "a51c2ad2f4d0b71a4189613046077ad9618dc202d92b56fd38fcb765901816b8"
    ),
    "singles:6": (
        "63c9a92cb97bcd22bab6103e28cd707c4703e3004b5c982b9eca5dfc324379c8"
    ),
    "singles:7": (
        "a8db3bba4261bfcbfea5c8499de6831d55a6d971facba58ea48ff06e4a726aa1"
    ),
    "singles:9": (
        "11e869a44dbcdfe945bcd1dd2317dfcdad6aec555d519e01df2ca872af8eda39"
    ),
    "singles:10": (
        "e91bbef67ecaae636a28b66be99ce596803e3ac27ed00ec03fadf6a681cd7450"
    ),
    "singles:12": (
        "3bf7bb91bd50b57133c5a90542f8d8009416f7a9a32e0159efb8457491257fee"
    ),
    "pairs:6": (
        "32f3511591097f687f026c50447626626bbf711f46a8c6e814be8de3d4b75ed5"
    ),
    "pairs:7": (
        "8d1ff69c06fcae839e9fc982cef640deb10d9dd35d7c8c5727c0a834adc2bae3"
    ),
    "unequal:6": (
        "978c58fee21a8058d21078a5068e73c35768c303cb407eb48df9d08f68aa0597"
    ),
    "unequal:8": (
        "b51d25d9a4bd84d3b9fff8ac037f23d880ad3543a812c53087f9e3d3b8cd10a9"
    ),
    "unequal:10": (
        "a01408f79d95385fc663e80e9ec9f0e94dc4e16a7c2789621029617c45d644e8"
    ),
}


def _stream_digests(book, rows: List[dict], tmp_path) -> dict[int, str]:
    export = _Export(book, rows, tmp_path)
    streams = pdf_vector.content_streams(export.data)
    return {
        entry.page_number: hashlib.sha256(streams[entry.page_number - 1].encode()).hexdigest()
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


class TestPuzzlePages_GeometryHeldExceptTheFooter:
    def test_every_puzzle_page_is_the_page_main_drew_without_its_qr_group(
        self, tmp_path
    ) -> None:
        # The footer band is the unit every usable area is measured against.
        assert INTERIOR_FOOTER_MM == pytest.approx(29.878, abs=1e-3)
        assert interior_frame(_spec()).footer_depth == FOOTER_STRIP_PX
        found = {}
        for label, (make_book, make_rows) in GEOMETRY_CORPUS.items():
            for page, digest in _stream_digests(make_book(), make_rows(), tmp_path).items():
                found[f"{label}:{page}"] = digest
        assert found == MAIN_PAGE_DIGESTS
        assert len(found) >= 13, len(found)


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


#: The pages of the corpus above on Book 1, recorded from main at a4ebdd53
#: before this card removed the pairing walk's width clause (c): which
#: puzzles share a page and which stand alone. Eleven and sixteen are left
#: alone on purpose of the corpus (a tier's odd tail and a pair that does not
#: fit), so both verdicts are in the list.
BOOK_ONE_PAGES_ON_MAIN = [
    (1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11,), (12, 13), (14, 15), (16,),
    (17, 18), (19, 20), (21, 22), (23, 24), (25, 26), (27, 28), (29, 30),
]  # fmt: skip


class TestTwoUp_BookOneVerdictsUnchanged:
    def test_the_walk_pairs_exactly_the_puzzles_it_paired_on_main(self) -> None:
        generator = BookPDFGenerator(_no_domain_book("card391-verdicts"))
        plan = generator.section_plan(_pairing_corpus())
        pages = [e.numbers for e in plan.pages if isinstance(e, PuzzlePagePlan)]
        assert pages == BOOK_ONE_PAGES_ON_MAIN
        assert {len(numbers) for numbers in pages} == {1, 2}, "both verdicts are in the corpus"


class TestTwoUp_NarrowTrimsNowPairOnHeightAndWidthAlone:
    def test_a_6_by_9_book_pairs_what_main_printed_on_two_pages(self) -> None:
        """AC-377 said no pair could print on a 6 x 9 in trim, because two QR
        groups did not fit across its 127 mm; with the groups gone the pair is
        judged by FR-040's height and width rules alone. Four 10 x 8 Easies
        print as four single pages on main (the recorded verdict) and as two
        pairs now; four 10 x 10 ones still do not pair, on the height rule."""
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
        assert pages(10, 10) == [(1,), (2,), (3,), (4,)]  # 22 cells of height: refused


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

    def test_a_6_by_9_book_prints_the_single_pointer_and_omits_the_two_up_one(
        self, tmp_path
    ) -> None:
        """The cost, measured: at 10 pt the single line is 52 mm and the shared
        two-up line 65 mm, against about 58 mm of room between a 6 x 9 in
        page's outer margin and its folio -- so the two-up page of such a book
        carries its Play page's number nowhere (owner question 1 of CARD-391)."""
        rows = [puzzle(f"c391-six-{i}", 10, 8, 1, "easy", f"E{i}") for i in range(3)]
        export = _Export(_domain_book((152.4, 228.6), "card391-6x9"), rows, tmp_path)
        by_numbers = {entry.numbers: entry for entry in export.puzzle_pages}
        assert set(by_numbers) == {(1, 2), (3,)}
        single = [w.text for w in export.footer_words(by_numbers[(3,)].page_number)]
        two_up = [w.text for w in export.footer_words(by_numbers[(1, 2)].page_number)]
        assert "Play" in single
        assert "Play" not in two_up and str(by_numbers[(1, 2)].page_number) in two_up
