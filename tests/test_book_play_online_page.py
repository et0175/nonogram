"""CARD-390 -- the Play online page: one right-hand page after the last puzzle.

The page carries the book's one QR code, which opens its landing page, and the
short address under it (ADR-0041/R8). It exists only for a book with a stored
player domain, sits after the last puzzle page and before the SOLUTIONS
divider, and is always a right-hand page: one blank page goes in front of it
when the last puzzle page is itself right-hand.

Four tests, each over a small corpus rather than one case, and every expected
page number and string is written out below from the plan's own rules worked
by hand (G-5), never read back from the function under test:

* **the plan**: where the page lands and whether a blank precedes it, for books
  whose last puzzle page falls on both parities and whose puzzle section ends
  two-up and single, and that the three counters (the generator's plan, the
  sheet-free KDP baseline and the exported file) are one number;
* **the numbers that follow**: the TOC's Solutions row and the folios of the
  pages after the inserted ones;
* **the code**: it decodes, with a reader written from ISO 18004, to the landing
  URL, and the typed address is in the text layer;
* **every trim**: the code stays readable, the type holds CON-020's floor and
  the ink stays inside the usable area.

The Finalise line and the KDP band moving with the true count are asserted in
``tests/test_book_finalise_gutter.py``, on the panel fixture that file owns.
"""

from __future__ import annotations

import copy
import re

import numpy as np
import pytest

from nonogram.admin.book_interior_vector import interior_generator
from nonogram.admin.book_kdp import unpaired_interior_page_count
from nonogram.admin.book_pdf_generator import PageKind, page_frame
from nonogram.admin.book_puzzle_vector import CLUE_SHADE
from nonogram.admin.book_page_spec import book_page_spec
from tests.helpers import pdf_vector, qr_reader
from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    baseline_puzzles,
    corpus_book,
    corpus_puzzles,
    puzzle,
)


def _poppler() -> None:
    """Poppler is the independent reader: a host without it is a failure, not a skip."""
    assert pdf_vector.PDFTOPPM and pdf_vector.PDFTOTEXT, "poppler is not on this host"

DOMAIN = "https://nonogram.adverax.io"


def _hard_pair(count: int) -> list[dict]:
    """``count`` small Hard puzzles: neighbours pair two to a page."""
    return [puzzle(f"c390-{i}", 10, 10, 3, "hard", f"Hard {i}") for i in range(count)]


def _book(domain: str | None = DOMAIN, *, trim_mm: tuple[float, float] | None = None):
    book = copy.copy(corpus_book())
    book.player_domain = domain
    if trim_mm is not None:
        book.trim_width_cm = f"{trim_mm[0] / 10:.2f}"
        book.trim_height_cm = f"{trim_mm[1] / 10:.2f}"
    return book


#: ``(label, puzzles, play page, blank page or None, SOLUTIONS divider page,
#: total interior pages)``, worked by hand. Front matter is the blank title
#: page, two guide pages and one TOC page (pages 1-4); the rest follows from
#: the section: a divider per level, and a page per puzzle or per pair.
#:
#: * four 18/20 Easies-to-Hards (2 Easy, 1 Medium, 1 Hard): 3 dividers + 4
#:   puzzle pages end on page 11 (a recto), so a blank (12) then the Play page
#:   (13), SOLUTIONS 14, three answer pages 15-17 (the two Easies pack onto
#:   one page, the Medium and the Hard each pack alone);
#: * five (2 Easy, 2 Medium, 1 Hard): the section ends on page 12 (a verso),
#:   so no blank: Play 13, SOLUTIONS 14, three answer pages 15-17 (a packed
#:   Easy pair, a packed Medium pair, the Hard alone);
#:
#: Those two used to end on 18 and 19, one answer page per puzzle: an 18x18
#: or 20x20 was too wide for the answer key's old 15x20 packing limit. The
#: owner raised the limit to 20x25 (2026-11-09), so every corpus answer now
#: packs, same-level neighbours four to a page (a leftover keeps the 2x2 spots, 2026-11-09). Only the
#: answer section shrank; the Play page and SOLUTIONS divider did not move.
#: * the baseline book: its last puzzle page is 10, so Play 11, SOLUTIONS 12,
#:   three answer pages 13-15;
#: * two Hards that pair: one divider and one two-up page end on page 6, so
#:   Play 7, SOLUTIONS 8, answers 9 (two small answers pack onto one page);
#: * three Hards (a pair and a single): the section ends on page 7, so a blank
#:   (8), Play 9, SOLUTIONS 10, answers on 11 (all three on one packed page).
#:
#: Every total counts one more page after the answers: the closing thank-you
#: page (owner, 2026-11-10).
CASES = [
    ("four singles, ends on a recto", corpus_puzzles(4), 13, 12, 14, 18),
    ("five singles, ends on a verso", corpus_puzzles(5), 13, None, 14, 18),
    ("the baseline book", baseline_puzzles(), 11, None, 12, 16),
    ("a pair ends the section", _hard_pair(2), 7, None, 8, 10),
    ("a pair and a single", _hard_pair(3), 9, 8, 10, 12),
]


class TestPlayPage_SitsAfterTheLastPuzzleIsRightHandAndEveryCountAgrees:
    def test_the_plan_the_file_and_the_kdp_baseline_say_one_thing(self) -> None:
        for label, puzzles, play, blank, solutions, total in CASES:
            book = _book()
            generator = interior_generator(book)
            stream = generator.interior_stream(puzzles)
            plan = generator.section_plan(puzzles)
            data = generator.export_interior(puzzles).getvalue()
            kinds = [kind.value for kind in stream.page_kinds]
            streams = pdf_vector.content_streams(data)

            assert plan.play_page == play, label
            assert plan.play_blank_page == blank, label
            assert kinds[play - 1] == "play", (label, kinds)
            assert play % 2 == 1, label
            assert kinds[solutions - 1] == "divider", (label, kinds)
            assert kinds[play - 2] == ("blank" if blank else "puzzle"), (label, kinds)
            assert kinds.count("blank") == (1 if blank else 0), label
            # The one count, four ways: the plan, the kinds it lists, the pages
            # of the written file and the sheet-free baseline the KDP band is
            # read from when no sheet can be laid out.
            assert stream.page_count == len(kinds) == len(streams) == total, label
            assert unpaired_interior_page_count(puzzles, book) == stream.unpaired_page_count, label
            if blank:
                # No ink and no folio: the blank title page's own empty stream.
                assert streams[blank - 1] == "", label
            assert streams[play - 1] != "", label

    def test_a_book_with_no_stored_domain_prints_no_play_page_and_no_blank(self) -> None:
        for puzzles in (baseline_puzzles(), corpus_puzzles(4)):
            stream = interior_generator(_book(None)).interior_stream(puzzles)
            kinds = {kind for kind in stream.page_kinds}

            assert PageKind.PLAY not in kinds and PageKind.BLANK not in kinds
        assert interior_generator(_book(None)).interior_stream(baseline_puzzles()).page_count == (
            BASELINE_PAGE_COUNT
        )


class TestPlayPage_TocAndFoliosFollowTheInsertedPages:
    def test_the_solutions_row_and_every_later_folio_are_the_real_page_numbers(self) -> None:
        _poppler()
        label, puzzles, play, blank, solutions, total = CASES[0]
        data = interior_generator(_book()).export_interior(puzzles).getvalue()
        pages = pdf_vector.extracted_text(data).split("\f")

        assert re.search(rf"Solutions\s*\.+\s*{solutions}\b", pages[3]), pages[3]
        assert pages[play - 1].split()[-1] == str(play)
        # The book's last page is the closing thank-you page (owner,
        # 2026-11-10), which prints no folio; the last folio is the page
        # before it, the last answer page.
        assert pages[total - 2].split()[-1] == str(total - 1)
        assert pages[blank - 1].strip() == ""


def _text_free_codes(page: np.ndarray, words, dpi: int) -> np.ndarray:
    """``page`` with the two rules and every word whitened: what is left is the code."""
    cleaned = page.copy()
    cleaned[(cleaned <= pdf_vector.INK_LEVEL).mean(axis=1) > 0.5] = 255
    scale = dpi / 72.0
    for word in words:
        cleaned[
            int(word.top * scale) - 2 : int(word.bottom * scale) + 3,
            int(word.left * scale) - 2 : int(word.right * scale) + 3,
        ] = 255
    # The approved mockup sets the code in a shaded card, beside the words and
    # among the steps' badges and the callout's bar: what is outside the card
    # is not the code. A page with no card (the plain fallback, or any other
    # page) is read whole, as before.
    card = (page >= 236) & (page <= 246)
    rows = np.nonzero(card.mean(axis=1) > 0.3)[0]
    if rows.size:
        top, bottom = int(rows.min()), int(rows.max())
        cols = np.nonzero(card[top : bottom + 1].mean(axis=0) > 0.3)[0]
        if cols.size:
            left, right = int(cols.min()), int(cols.max())
            outside = np.ones_like(cleaned, dtype=bool)
            outside[top : bottom + 1, left : right + 1] = False
            cleaned[outside] = 255
            # The card's own border (Anna's design, 2026-11-10): its sides are
            # columns that are ink down most of the card.
            sides = (cleaned[top : bottom + 1] <= pdf_vector.INK_LEVEL).mean(axis=0) > 0.5
            cleaned[:, sides] = 255
    return cleaned


def _play_page_of(book, tmp_path, dpi: int = 150):
    _poppler()
    generator = interior_generator(book)
    puzzles = baseline_puzzles()
    kinds = [kind.value for kind in generator.interior_stream(puzzles).page_kinds]
    number = kinds.index("play") + 1
    data = generator.export_interior(puzzles).getvalue()
    page = pdf_vector.rendered_page(data, dpi, page=number, out_dir=tmp_path)
    return data, number, page, pdf_vector.word_boxes(data, number, out_dir=tmp_path)


class TestPlayPage_QrDecodesToTheLandingUrl:
    def test_the_code_decodes_and_the_address_is_printed_under_it(self, tmp_path) -> None:
        data, number, page, words = _play_page_of(_book(), tmp_path)

        assert qr_reader.read_image(_text_free_codes(page, words, 150)) == (
            "https://nonogram.adverax.io/b/5e51610a53"
        )
        address = [word for word in words if word.text.startswith("nonogram.")]
        assert [word.text for word in address] == ["nonogram.adverax.io/b/5e51610a53"]
        ink = np.nonzero(_text_free_codes(page, words, 150) <= 128)
        code_bottom = ink[0].max() * 72 / 150
        code_right = ink[1].max() * 72 / 150
        # Under the code on the plain page; beside it, in the same card, on the
        # approved mockup's.
        assert address[0].top >= code_bottom or address[0].left >= code_right


#: CON-018's Book 1 trim and the two smaller trims the panel offers, in
#: millimetres, and the shortest trim a book can store (10 x 10 cm).
TRIMS = ((215.9, 279.4), (190.5, 234.95), (152.4, 228.6), (100.0, 100.0))


class TestPlayPage_FitsEveryTrimAtAReadableModule:
    def test_the_code_decodes_the_type_holds_the_floor_and_the_ink_stays_inside(
        self, tmp_path
    ) -> None:
        for trim in TRIMS:
            book = _book(trim_mm=trim)
            data, number, page, words = _play_page_of(book, tmp_path)
            label = f"{trim[0]} x {trim[1]} mm"

            assert qr_reader.read_image(_text_free_codes(page, words, 150)) == (
                "https://nonogram.adverax.io/b/5e51610a53"
            ), label
            sizes = pdf_vector.type_sizes(pdf_vector.content_streams(data)[number - 1])
            assert sizes and min(sizes) >= 10.0, (label, sizes)
            frame = page_frame(book_page_spec(book, number))
            scale = 150 / 300
            left, top, right, bottom = pdf_vector.ink_box(page)
            assert frame.left * scale <= left and right <= frame.right * scale + 1, label
            assert frame.top * scale <= top and bottom <= frame.bottom * scale + 1, label


class TestPlayPage_IsTheOnlyPageWithACode:
    """ADR-0041/R8 (CARD-391): one code per book, and it is on this page."""

    def test_no_interior_page_but_the_play_page_carries_a_qr(self, tmp_path) -> None:
        """The planned ref of ADR-0041/R8, now its check:
        ``tests/test_book_play_online_page.py::test_no_interior_page_but_the_play_page_carries_a_qr``.

        A book with a stored domain, exported whole; every page rendered and
        read with the ISO 18004 reader (``tests/helpers/qr_reader.py``, written
        from the standard, independent of the encoder) once its words and
        rules are whitened. Exactly one page decodes -- the Play page, to its
        landing address -- and no puzzle, two-up, guide, contents, divider or
        answer page does. The control for the reading is the one page it does
        read.

        A restored placeholder checkerboard is not a decodable code, so the
        reader alone would not see it; it is caught by what it was drawn with,
        a filled rectangle (``re f``). Since the approved mockup's header
        (CARD-207 scope) a puzzle page paints exactly two of those per puzzle,
        the row- and column-clue gutters' tint, each at ``CLUE_SHADE``; a
        checkerboard's black cells would be more fills, at another tone.
        """
        _poppler()
        generator = interior_generator(_book())
        puzzles = baseline_puzzles()
        kinds = [kind.value for kind in generator.interior_stream(puzzles).page_kinds]
        data = generator.export_interior(puzzles).getvalue()
        play = kinds.index("play") + 1
        decoded: dict[int, str] = {}
        for number in range(1, len(kinds) + 1):
            page = pdf_vector.rendered_page(data, 150, page=number, out_dir=tmp_path)
            words = pdf_vector.word_boxes(data, number, out_dir=tmp_path)
            try:
                decoded[number] = qr_reader.read_image(_text_free_codes(page, words, 150))
            except qr_reader.QrReadError:
                continue
        assert decoded == {play: "https://nonogram.adverax.io/b/5e51610a53"}, decoded

        plan = generator.section_plan(puzzles)
        streams = pdf_vector.content_streams(data)
        puzzle_pages = [entry.page_number for entry in plan.pages if hasattr(entry, "numbers")]
        assert len(puzzle_pages) == 3, "the baseline holds a two-up page and two single pages"
        slots = {entry.page_number: len(entry.numbers) for entry in plan.pages if hasattr(entry, "numbers")}
        for number in puzzle_pages:
            stream = streams[number - 1]
            assert pdf_vector.operator_tally(stream)["f"] == 2 * slots[number], number
            pieces = stream.split(" re f")[:-1]
            prefix = ""
            for piece in pieces:
                prefix += piece
                fills = [level for level, op in pdf_vector.tones(prefix) if op == "g"]
                assert fills and fills[-1] == CLUE_SHADE, (number, fills[-1:])

