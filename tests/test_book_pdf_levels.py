"""CARD-128 — the printed book's levels (FR-041, INV-009, TERM-031, ADR-0037).

    AC-253  TestBookPdf_DifficultyOrderWithDividerPerLevel
    AC-254  TestBookPdf_DividerPageCarriesLevelNameOnly
    AC-255  TestBookPdf_DividerPagesDoNotConsumePuzzleNumbers
    AC-256  TestBookPdf_EmptyLevelHasNoDivider
    AC-260  TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel

CARD-198 note (SCOPE+, flagged rather than silently absorbed): AC-293
(``TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages``) pinned the
*packed* answer key's own per-level behaviour — ``BookPDFGenerator.answer_key``
giving each of three levels its own run of six-up pages — which CARD-198
deletes along with that method. This file names no CARD-198 Touches path,
but ``BookPDFGenerator.answer_key`` no longer exists, so that one class could
not pass unedited; it has been retired rather than narrowed, since nothing
of its packed-key claim survives for a test to still make. The behaviour
this card replaces it with — one full solved page per puzzle, in book order,
across the same three-level plan — is pinned fresh by
``tests/test_book_solved_answer_key.py``'s AC-1/AC-4, not reproduced here.

AC-287 belongs to the interior's parity and lives with the rest of it, in
``tests/test_book_pdf.py`` (``TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1``).

How a page is identified without an OCR this project does not have
------------------------------------------------------------------
Every claim here is about **which page is where**, so every page is named by
measuring or by re-rendering it, never by trusting the generator's own plan.

*A puzzle page* is identified whole: the page COMP-007 draws for that puzzle's
payload, with the picture's name cleared and a band line this module writes out
from ADR-0037's wording, is compared with the page the interior holds. Two
pages differing by one clue, one band character or one page's parity differ in
their pixels, so the comparison names the puzzle **and** its print number at
once — the technique ``tests/test_book_pdf_band.py`` reads a band with
(CARD-117).

*A divider page* is identified by comparison with the page the generator
draws for that level at that position (``create_level_divider``: the level's
name, its puzzle range and its difficulty dots), so the comparison names the
level and its range at once (:func:`level_divider_at`). The Solutions opener
is named the same way (:func:`is_solutions_opener`).

The book is CON-018's Book 1 profile throughout, written out in millimetres
rather than imported. Its puzzles are 21x20 with 3-deep clue gutters, so no two
of them ever share a puzzle page (FR-040, CARD-127); their answers pack up to
four to a page, one level per page (CARD-202). Each puzzle's
grid carries a different extra cell, so two puzzles of the same extent are
different pictures with different clues and a page holding the wrong one is
visible.

Puzzle pages are content-stream operators (ADR-0042/R1): a puzzle page is
named by its operators against ``vector_puzzle_page`` drawn for the stated
puzzle, position, number and tier (:func:`same_page`), and by the band and
folio its text layer reads (:func:`names_the_page`). The dividers stay raster.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
import pytest
from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin import book_vector
from nonogram.admin.book_vector import ContentStream, write_vector_pdf
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.difficulty import Tier
from nonogram.export import ExportPayload
from tests.helpers import pdf_vector
from tests.helpers.pdf_pages import interior_images

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out rather than imported.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4

#: A pixel darker than this (0..255 grey) is ink.
INK_LEVEL = 128

#: ADR-0037's band, restated: "Puzzle 12 · Easy", the dot U+00B7 with a space
#: either side. Written out rather than imported from ``band_identity``, so the
#: expected line is a second implementation of the rule (CLAUDE.md).
BAND_TEMPLATE = "Puzzle {number} · {tier}"

#: The three levels a divider can open (ADR-0031's three tiers, as AC-020
#: displays them).
LEVEL_NAMES = ("Easy", "Medium", "Hard")


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book() -> Book:
    """A book on CON-018's Book 1 profile, as a ``books`` row carries it."""
    return Book(
        book_id="book-128",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="A test book.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(BOOK1_WIDTH_MM),
        trim_height_cm=_cm(BOOK1_HEIGHT_MM),
        gutter_margin_cm=_cm(GUTTER_MM),
        outside_margin_cm=_cm(OUTSIDE_MM),
    )


def _grid(columns: int, rows: int, depth: int = 3, mark: int = 0) -> List[List[bool]]:
    """A grid with ``depth``-deep clues and one extra cell chosen by ``mark``.

    The extra cell is what makes two puzzles of one extent two different
    pictures, with different clues, so a page holding the wrong one of them
    fails a comparison.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    grid = [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]
    grid[rows - 1][(columns - 1) - (mark % (columns - limit))] = True
    return grid


#: This module's default puzzle width (21x20 puzzles, one per puzzle page).
#: A literal: ``tests/test_book_uploaded_dividers.py`` and
#: ``tests/test_book_divider_pages_option.py`` build their books from it too.
_PUZZLE_COLUMNS = 21


def _puzzle(
    name: str,
    tier: object,
    columns: int = _PUZZLE_COLUMNS,
    rows: int = 20,
    mark: int = 0,
) -> dict:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _grid(columns, rows, mark=mark)
    found = clues.compute_clues(grid)
    return {
        "id": name,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": tier,
    }


def _book_of(*members: Tuple[str, str]) -> List[dict]:
    """A book's rows from ``(name, stored tier)`` pairs, each a different picture."""
    return [
        _puzzle(name, tier, mark=index) for index, (name, tier) in enumerate(members)
    ]


Page = Union[Image.Image, ContentStream]


def _raw_interior(puzzles: Sequence[dict]) -> List[Page]:
    """The book's interior as the generator hands it back: each page in the
    medium its kind is written in (CARD-360).

    A bitmap for a raster page and a ``ContentStream`` for a page written as
    operators (ADR-0042/R1). A claim about *which page this is* is read from
    this, in the page's own medium (:func:`names_the_page`); a claim about
    what a page *looks like* goes through :func:`_interior`.
    """
    return BookPDFGenerator(_book()).interior_pages(list(puzzles))


def _interior(puzzles: Sequence[dict]) -> List[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``.

    **CARD-329: the medium is read here and nowhere else** for every claim
    stated on *device pixels*. ADR-0042/R1 writes the puzzle pages as
    content-stream operators, so the walk hands back a ``ContentStream`` for
    them and an ``Image.Image`` for the kinds that stay raster (the cover and
    the divider, ADR-0042/R2). ``interior_images`` returns a raster page
    unchanged and rasterises an operators page with poppler at that page's own
    DPI. **CARD-360: the claims that name a page do not read it through here**
    -- a poppler render of a stream is never byte-equal to a bitmap COMP-007
    drew, so they are stated in the page's own medium instead.
    """
    return interior_images(_raw_interior(puzzles))


# --------------------------------------------------------------------------
# Naming a page
# --------------------------------------------------------------------------


def _banded_payload(puzzle: dict, tier: str) -> ExportPayload:
    """``puzzle`` as the boundary payload, with no picture name (ADR-0037/R1)."""
    return ExportPayload(
        grid=puzzle["grid"],
        row_clues=tuple(tuple(clue) for clue in puzzle["clues_rows"]),
        column_clues=tuple(tuple(clue) for clue in puzzle["clues_cols"]),
        seed=0,
        mode="random",
        width=puzzle["width"],
        height=puzzle["height"],
        name=None,
        difficulty=tier,
    )


def expected_in_the_medium_of(
    page: Page, puzzle: dict, page_number: int, number: int, tier: str
) -> Page:
    """The operators ``vector_puzzle_page`` draws for ``puzzle`` at the position,
    number and tier this module states (CARD-360)."""
    # The footer's "Solution on p. N" is the answer plan's (owner, 2026-11-10),
    # not this module's subject: it is read off the page and drawn the same.
    found = re.search(r"Solution on p\. (\d+)", " ".join(getattr(page, "operators", ())))
    return BookPDFGenerator(_book()).vector_puzzle_page(
        _banded_payload(puzzle, tier),
        number,
        page_number,
        solution_pages=None if found is None else {number: int(found.group(1))},
    )


def same_page(left: Page, right: Page) -> bool:
    """Two pages are the same page: the same medium and exactly the same marks.

    Bitmaps by their bytes, operators by their operators and extent. **A
    bitmap and a stream are never the same page** -- comparing across media is
    what made the original ``page.tobytes() == expected.tobytes()`` claims red
    once the interior page stopped being a bitmap, and it is refused here
    rather than rasterised into agreement.
    """
    if isinstance(left, Image.Image) and isinstance(right, Image.Image):
        return left.size == right.size and left.tobytes() == right.tobytes()
    if isinstance(left, ContentStream) and isinstance(right, ContentStream):
        return left.operators == right.operators and (
            left.width_px,
            left.height_px,
            left.dpi,
        ) == (right.width_px, right.height_px, right.dpi)
    return False


#: A band is "Puzzle N" or "Puzzle N · Tier"; a QR caption ("Puzzle N · Solve it
#: online") opens with the same word and is not one.
_BAND_SHAPE = re.compile(r"Puzzle \d+(?: · \w+)?")


def _words_of(page: ContentStream) -> list:
    """The words poppler finds on one stream written out as a one-page PDF."""
    data = write_vector_pdf([page], 1).getvalue()
    with tempfile.TemporaryDirectory(prefix="levels-words-") as directory:
        return pdf_vector.word_boxes(data, 1, out_dir=Path(directory))


def band_lines(page: ContentStream) -> List[str]:
    """Every band line of type on ``page`` (:data:`_BAND_SHAPE`).

    Read from the text layer poppler finds in the stream written out as a
    one-page PDF -- an engine that did not write the file, and not
    ``band_identity``. Clue digits, the QR invitation and the grid-size label
    do not have the shape of a band, so on a puzzle page this is the band.

    Since CARD-207 a puzzle page's header is two pieces on one baseline,
    ``Puzzle N`` at the band's size and the tier in capitals, smaller, flush
    right; words are therefore gathered by **baseline** (each box's top plus
    its share of the face's ascent), and a row reading ``Puzzle N TIER`` is
    read back as the band's line ``Puzzle N · Tier``.
    """
    metrics = book_vector.interior_face_metrics()
    ascent_share = metrics.ascent / (metrics.ascent - metrics.descent)
    placed = sorted(
        (word.top + ascent_share * (word.bottom - word.top), word)
        for word in _words_of(page)
    )
    rows: list = []
    for baseline, word in placed:
        if rows and baseline - rows[-1][0] < 0.5:
            rows[-1][1].append(word)
        else:
            rows.append((baseline, [word]))
    lines = [
        " ".join(w.text for w in sorted(row, key=lambda w: w.left))
        for _, row in rows
    ]
    lines = [_HEADER_ROW.sub(lambda m: f"{m[1]} · {m[2].capitalize()}", line) for line in lines]
    return [line for line in lines if _BAND_SHAPE.fullmatch(line)]


#: A puzzle header's row as poppler reads it (CARD-207): the number, then the
#: tier word in capitals.
_HEADER_ROW = re.compile(r"^(Puzzle \d+) (EASY|MEDIUM|HARD)$")


def footer_floor(words: Sequence) -> float:
    """The top, in points, of the footer row -- derived from the page itself.

    The footer row is the row that carries the grid-size label "C x R"
    (CARD-222), found by its ``x`` word; the folio (CARD-200) sits on that same
    row. A clue digit is never on it. Deriving the floor from the label replaces
    a fixed share of the page height (this function used a hard-coded 0.85
    before the review of CARD-360).

    Measured on this tree, by the author, as the share of the page height
    (``top / 792 pt``), at interior pages 6, 7 and 150:

    ========  =======================  ===================
    grid      lowest clue digit's top  footer row's top
    ========  =======================  ===================
    10x10     0.587                    0.8624
    20x20     0.7427                   0.8624
    30x30     0.7918                   0.8624
    ========  =======================  ===================

    (15x20 0.7427 and 30x10 0.5482 are on the same footer row.) So a floor is
    correct exactly when it lies in ``(lowest clue digit, footer row]``, and
    the derived floor is the upper end of that window.
    :meth:`TestBookPdf_AnOperatorsPageIsTheSameStreamEveryExport.test_the_footer_window_is_derived_and_a_floor_past_either_end_is_refused`
    asserts the window and its two controls.

    **A page with no footer at all has no folio, and that is refused loudly.**
    A 20x30 or a 10x30 vector page (measured: pages 6, 7 and 150) carries no
    "x" word and no folio: its only digits near the bottom are clue digits
    (measured: "0", "0", "0", "1" below 85% of the height). Reading a "folio"
    off such a page would mistake a clue digit for one and report a correct page
    as wrong, so this raises with the reason instead of returning something.
    """
    # Since 2026-11-10 the grid size sits in the clue corner and the footer
    # says where the solution is: its "Solution(s)" word marks the row.
    labels = [word for word in words if word.text in ("Solution", "Solutions")]
    labels = labels or [word for word in words if word.text == "x"]
    assert labels, (
        "this page carries no grid-size label, so no footer and no folio to "
        "read (a 20x30 or 10x30 vector page has none); refusing to take a "
        "clue digit for a folio"
    )
    return max(word.top for word in labels)


def footer_digits(
    page: ContentStream, label: Tuple[int, int], floor: Optional[float] = None
) -> List[str]:
    """The digit words in ``page``'s footer row, less the grid-size label's own.

    The footer carries the folio beside the label "C x R"; what is left once the
    label's two numbers are taken away is the folio, as poppler reads it.
    ``floor`` is the footer row's top in points, derived by :func:`footer_floor`
    unless a caller (a control) states one.
    """
    words = _words_of(page)
    if floor is None:
        floor = footer_floor(words)
    row = [w.text for w in words if w.top >= floor - 0.05]
    # A page number the footer points at ("Solution on p. 13") is not the folio.
    digits = [
        text for index, text in enumerate(row)
        if text.isdigit() and not (index and row[index - 1] in ("p.", "and"))
    ]
    for number in label:
        if str(number) in digits:
            digits.remove(str(number))
    return digits


def names_the_page(
    page: Page, puzzle: dict, page_number: int, number: int, tier: str
) -> bool:
    """Whether ``page`` is ``puzzle``'s page at ``page_number`` as Puzzle ``number``.

    The whole-page identification every claim in this module stands on, in the
    page's own medium (CARD-360): the same page as the one drawn for that
    puzzle at that position (:func:`expected_in_the_medium_of` and
    :func:`same_page`) **and**, for a page of operators, a text layer whose one
    band line reads the band this module writes out from ADR-0037's wording
    (:data:`BAND_TEMPLATE`) and whose footer folio reads ``page_number`` -- so
    neither the band's words nor the page's position is asked of the function
    that composed them.
    """
    if not isinstance(page, ContentStream):
        return False
    expected = expected_in_the_medium_of(page, puzzle, page_number, number, tier)
    if not same_page(page, expected):
        return False
    return band_lines(page) == [
        BAND_TEMPLATE.format(number=number, tier=tier)
    ] and footer_digits(page, (puzzle["width"], puzzle["height"])) == [
        str(page_number)
    ]


def level_divider(page_number: int, level: str, first: int, last: int) -> Image.Image:
    """The divider the generator draws for ``level`` (puzzles ``first``-``last``)
    on the sheet of interior ``page_number``."""
    return BookPDFGenerator(_book()).create_level_divider(
        page_number, Tier(level.lower()), (first, last)
    )


def level_divider_at(page: Image.Image, page_number: int, first: int, last: int) -> Optional[str]:
    """Which level's divider for puzzles ``first``-``last`` ``page`` is, if any."""
    if not isinstance(page, Image.Image):
        return None
    for level in LEVEL_NAMES:
        if page.tobytes() == level_divider(page_number, level, first, last).tobytes():
            return level
    return None


def is_solutions_opener(page: Image.Image, page_number: int, puzzle_count: int) -> bool:
    """Whether ``page`` is the Solutions opener for a book of ``puzzle_count`` puzzles.

    Named by comparison with the page the generator draws for it at that
    position, as the level dividers are (:func:`level_divider_at`).
    """
    reference = BookPDFGenerator(_book()).create_solutions_opener(page_number, puzzle_count)
    return page.tobytes() == reference.tobytes()


def _ink(page: Image.Image) -> np.ndarray:
    return np.asarray(page.convert("L")) < INK_LEVEL


def _row_bands(present: Sequence[bool]) -> List[Tuple[int, int]]:
    """The maximal runs of ``True``, as ``(first, last)`` index pairs."""
    bands: List[List[int]] = []
    previous = False
    for index, here in enumerate(present):
        if here and not previous:
            bands.append([index, index])
        elif here:
            bands[-1][1] = index
        previous = here
    return [(first, last) for first, last in bands]


#: How large a block of ink must be, in both axes, to be a puzzle's drawing
#: rather than a line of type — a share of the page. The smallest drawing a
#: book page carries is far above it and a line of type far below.
_DRAWING_SHARE = 0.1


def _carries_a_drawing(page: Image.Image) -> bool:
    """Whether ``page`` holds a block of ink large enough to be a drawing."""
    mask = _ink(page)
    least_wide = page.width * _DRAWING_SHARE
    least_tall = page.height * _DRAWING_SHARE
    for top, bottom in _row_bands(mask.any(axis=1)):
        if bottom - top + 1 < least_tall:
            continue
        strip = mask[top : bottom + 1]
        if any(
            right - left + 1 >= least_wide
            for left, right in _row_bands(strip.any(axis=0))
        ):
            return True
    return False


def interior_shape(pages: Sequence[Image.Image]) -> List[str]:
    """Each puzzle-section page as ``"divider Easy"`` or ``"puzzle"``, in print order.

    Pages 1-4 (title page, the 2-page guide, the one-page TOC) are left out. A
    page carrying a drawing is a puzzle page (one puzzle each, at 21x20);
    any other page is named by :func:`level_divider_at`, with the puzzle range
    the following puzzle pages give it -- ``"divider None"`` if it matches no
    level's divider.
    """
    section = list(enumerate(pages[4:], start=5))
    drawn = [_carries_a_drawing(page) for _, page in section]
    shape: List[str] = []
    seen = 0
    for index, (number, page) in enumerate(section):
        if drawn[index]:
            seen += 1
            shape.append("puzzle")
            continue
        following = 0
        for later in drawn[index + 1 :]:
            if not later:
                break
            following += 1
        level = level_divider_at(page, number, seen + 1, seen + max(following, 1))
        shape.append(f"divider {level}")
    return shape


# --------------------------------------------------------------------------
# AC-253 — the order, and the divider that opens each level
# --------------------------------------------------------------------------

#: AC-253's book: two easy, two medium and one hard 21x20, arranged in that
#: order already, so what is under test is the make-up of the pages and not the
#: grouping (that is AC-260's book).
AC253_MEMBERS = (
    ("E1", "easy"),
    ("E2", "easy"),
    ("M1", "medium"),
    ("M2", "medium"),
    ("H1", "hard"),
)

#: Where each of them prints, and under which band: interior page 1 is the
#: blank title page (CARD-206), pages 2-3 are
#: the guide (CARD-201), page 4 the table of contents (CARD-200 — this
#: book's 5 entries are always exactly one TOC page), page 5 the "Easy"
#: divider, and a divider costs a page and no number. Written out here
#: rather than computed, because it is the claim.
AC253_PAGES = (
    (6, 1, "Easy"),
    (7, 2, "Easy"),
    (9, 3, "Medium"),
    (10, 4, "Medium"),
    (12, 5, "Hard"),
)


class TestBookPdf_DifficultyOrderWithDividerPerLevel:
    """AC-253 (INV-009) — divider "Easy", E1, E2, divider "Medium", M1, M2, divider "Hard", H1."""

    @staticmethod
    def _pages() -> Tuple[List[dict], List[Image.Image]]:
        puzzles = _book_of(*AC253_MEMBERS)
        return puzzles, _interior(puzzles)

    def test_the_puzzle_section_runs_divider_then_that_levels_puzzles(self) -> None:
        _, pages = self._pages()

        assert interior_shape(pages[:12]) == [
            "divider Easy",
            "puzzle",
            "puzzle",
            "divider Medium",
            "puzzle",
            "puzzle",
            "divider Hard",
            "puzzle",
        ]

    def test_each_puzzle_page_is_the_puzzle_and_the_band_it_should_be(self) -> None:
        puzzles = _book_of(*AC253_MEMBERS)
        raw = _raw_interior(puzzles)

        for puzzle, (page_number, number, tier) in zip(puzzles, AC253_PAGES):
            assert names_the_page(
                raw[page_number - 1], puzzle, page_number, number, tier
            ), (
                f"interior page {page_number} is not {puzzle['id']} banded "
                f"'Puzzle {number} · {tier}'"
            )

    def test_the_interior_is_that_section_between_the_guide_and_the_key(self) -> None:
        """The whole file: the title page, the 2-page guide, the TOC, the
        eight pages above, SOLUTIONS, the key.

        The key packs up to four answers a page, one level per page
        (CARD-202), so 2 easy, 2 medium and 1 hard take three answer pages:
        16 pages, which the generator must have reported before it drew
        anything.
        """
        puzzles, pages = self._pages()
        stream = BookPDFGenerator(_book()).interior_stream(puzzles)

        assert len(pages) == 16
        assert stream.page_count == 16
        assert is_solutions_opener(pages[12], 13, len(puzzles)), (
            "interior page 13 is the SOLUTIONS divider"
        )
        assert stream.answer_page_count == 3
        assert all(_carries_a_drawing(page) for page in pages[13:])


# --------------------------------------------------------------------------
# AC-254 — what a divider page carries
# --------------------------------------------------------------------------


class TestBookPdf_DividerPageCarriesLevelNameOnly:
    """AC-254 — each divider page names its own level (and its puzzle range)."""

    #: AC-253's three dividers: interior position, level, its puzzles.
    DIVIDERS = ((5, "Easy", 1, 2), (8, "Medium", 3, 4), (11, "Hard", 5, 5))

    def test_the_three_level_dividers_are_three_different_pages(self) -> None:
        """The premise of the comparison: the levels discriminate."""
        pages = {level: level_divider(5, level, 1, 2).tobytes() for level in LEVEL_NAMES}

        assert len(set(pages.values())) == 3, "two levels draw one page"

    def test_each_divider_carries_its_own_level_name(self) -> None:
        pages = _interior(_book_of(*AC253_MEMBERS))

        for page_number, name, first, last in self.DIVIDERS:
            assert level_divider_at(pages[page_number - 1], page_number, first, last) == name

    def test_a_divider_carries_no_drawing_and_a_puzzle_page_does(self) -> None:
        pages = _interior(_book_of(*AC253_MEMBERS))

        for page_number, name, _, _ in self.DIVIDERS:
            assert not _carries_a_drawing(pages[page_number - 1]), name
        assert _carries_a_drawing(pages[5]), "the control: a puzzle page"


# --------------------------------------------------------------------------
# AC-255 — a divider consumes no puzzle number
# --------------------------------------------------------------------------


class TestBookPdf_DividerPagesDoNotConsumePuzzleNumbers:
    """AC-255 — 2 easy and 1 medium: the medium puzzle is "Puzzle 3 · Medium".

    Its page is interior page 9 (CARD-206: up from 8, now one page further
    behind the blank title page) — the title page, the 2-page guide, the
    TOC, Easy divider, two puzzles, Medium divider — so by the time it
    prints, six title/guide/TOC/divider pages have gone past and the number
    is still 3.
    """

    MEMBERS = (("E1", "easy"), ("E2", "easy"), ("M1", "medium"))

    def test_the_medium_puzzles_band_reads_puzzle_three_medium(self) -> None:
        puzzles = _book_of(*self.MEMBERS)
        raw = _raw_interior(puzzles)

        assert names_the_page(raw[8], puzzles[2], 9, 3, "Medium")

    def test_it_is_not_numbered_by_its_page(self) -> None:
        """The two ways of getting it wrong: numbering by page, or per level.

        Interior page 9 would be "Puzzle 9" if a divider consumed a number,
        and "Puzzle 1 · Medium" if numbering restarted inside a level.
        """
        puzzles = _book_of(*self.MEMBERS)
        page = _raw_interior(puzzles)[8]

        # The control, in the same run: the right number IS this page. Without
        # it a page that no number could name would pass the loop below, which
        # is exactly what the bitmap-against-stream `!=` did.
        assert names_the_page(page, puzzles[2], 9, 3, "Medium")
        for number in (9, 4, 1):
            assert not names_the_page(
                page, puzzles[2], 9, number, "Medium"
            ), f"the medium puzzle prints as Puzzle {number}"

    def test_the_numbers_run_one_to_n_over_the_puzzles(self) -> None:
        puzzles = _book_of(*self.MEMBERS)
        raw = _raw_interior(puzzles)

        for puzzle, page_number, number, tier in (
            (puzzles[0], 6, 1, "Easy"),
            (puzzles[1], 7, 2, "Easy"),
            (puzzles[2], 9, 3, "Medium"),
        ):
            assert names_the_page(
                raw[page_number - 1], puzzle, page_number, number, tier
            ), f"{puzzle['id']} is not Puzzle {number} on interior page {page_number}"


# --------------------------------------------------------------------------
# AC-256 — an empty level has no divider
# --------------------------------------------------------------------------


class TestBookPdf_EmptyLevelHasNoDivider:
    """AC-256 — 3 easy and 2 medium, no hard: the PDF holds no "Hard" divider."""

    MEMBERS = (
        ("E1", "easy"),
        ("E2", "easy"),
        ("E3", "easy"),
        ("M1", "medium"),
        ("M2", "medium"),
    )

    def test_no_page_of_the_interior_is_a_hard_divider(self) -> None:
        pages = _interior(_book_of(*self.MEMBERS))

        assert [s for s in interior_shape(pages[:11]) if s != "puzzle"] == [
            "divider Easy",
            "divider Medium",
        ]
        assert is_solutions_opener(pages[11], 12, len(self.MEMBERS)), (
            "interior page 12 is the SOLUTIONS divider"
        )
        assert all(_carries_a_drawing(page) for page in pages[12:]), "answer pages"

    def test_the_interior_is_one_page_shorter_than_three_levels_would_make_it(
        self,
    ) -> None:
        """Title page, guide (2 pages), TOC (1), Easy, 3 puzzles, Medium,
        2 puzzles, SOLUTIONS, 2 answer pages (easy 3, medium 2: a packed
        page holds one level, CARD-202): fourteen pages.
        """
        pages = _interior(_book_of(*self.MEMBERS))

        assert len(pages) == 14
        assert interior_shape(pages[:11]) == [
            "divider Easy",
            "puzzle",
            "puzzle",
            "puzzle",
            "divider Medium",
            "puzzle",
            "puzzle",
        ]


# --------------------------------------------------------------------------
# AC-260 — a legacy mixed arrangement prints grouped
# --------------------------------------------------------------------------


class TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel:
    """AC-260 (INV-009) — stored M1, E1, H1, E2 prints E1, E2, M1, H1.

    The arrangement was saved before INV-009, so the list handed to the
    generator is mixed. Nothing about it is rewritten (G-1): what is asserted
    is the *pages*, and the stored list is checked afterwards to be the mixed
    one it was.
    """

    MEMBERS = (("M1", "medium"), ("E1", "easy"), ("H1", "hard"), ("E2", "easy"))

    #: The expected print order: which member of ``MEMBERS`` prints where, on
    #: which page and under which band (CARD-206: each one page later than
    #: before, behind the blank title page).
    PRINTED = (
        (1, 6, 1, "Easy"),  # E1
        (3, 7, 2, "Easy"),  # E2
        (0, 9, 3, "Medium"),  # M1
        (2, 11, 4, "Hard"),  # H1
    )

    def test_the_puzzles_print_grouped_by_level(self) -> None:
        puzzles = _book_of(*self.MEMBERS)
        raw = _raw_interior(puzzles)

        for index, page_number, number, tier in self.PRINTED:
            assert names_the_page(
                raw[page_number - 1], puzzles[index], page_number, number, tier
            ), (
                f"{puzzles[index]['id']} does not print on interior page "
                f"{page_number} as Puzzle {number}"
            )

    def test_each_level_still_opens_with_its_own_divider(self) -> None:
        pages = _interior(_book_of(*self.MEMBERS))

        assert interior_shape(pages[:11]) == [
            "divider Easy",
            "puzzle",
            "puzzle",
            "divider Medium",
            "puzzle",
            "divider Hard",
            "puzzle",
        ]

    def test_the_stored_arrangement_is_left_as_it_was(self) -> None:
        """G-1: the grouping is a print-time decision and writes nothing back."""
        puzzles = _book_of(*self.MEMBERS)
        before = [puzzle["id"] for puzzle in puzzles]

        _interior(puzzles)

        assert [puzzle["id"] for puzzle in puzzles] == before
        assert before == ["M1", "E1", "H1", "E2"]


# --------------------------------------------------------------------------
# CARD-360 AC-1 -- what "the same page" means once a page is operators
# --------------------------------------------------------------------------


def _stream(*, extra: bool = False, width_px: float = 300) -> ContentStream:
    """A tiny page of operators, for the controls that need a stream and no book."""
    stream = ContentStream(width_px=width_px, height_px=300, dpi=300)
    stream.line(10, 10, 10, 200)
    if extra:
        stream.line(20, 10, 20, 200)
    return stream


class TestBookPdf_AnOperatorsPageIsTheSameStreamEveryExport:
    """CARD-360 -- what identity means for an operators page in this module.

    **The claims here were about "the same page came back", not about bytes.**
    The original assertions compared ``tobytes()`` of the interior's page with
    ``tobytes()`` of a bitmap COMP-007 drew, because for two bitmaps that is the
    strictest available reading of "the same page". A page of operators has no
    bitmap and poppler's render of it can never equal a PIL bitmap, so that
    comparison could only ever say "no". What a page of operators can be
    identical to is **the page drawn for the same thing, as operators**: the
    same book exported twice writes the same stream, and the page the walk
    chose for a puzzle is the stream the page writer draws for that puzzle at
    that position. This is the answer CARD-355 settled for the memory module
    (``tests/test_book_pdf_memory.py::TestBookPdfMemory_AnOperatorsPageIsTheSameStreamEveryExport``),
    and it carries here for the same reason: nothing in this file is about
    pixels.
    """

    BOOK = AC253_MEMBERS

    def test_the_same_book_exported_twice_is_the_same_pages_page_for_page(self) -> None:
        first = _raw_interior(_book_of(*self.BOOK))
        second = _raw_interior(_book_of(*self.BOOK))

        assert len(first) == len(second) == 16
        assert [type(page) for page in first] == [type(page) for page in second]
        for number, (left, right) in enumerate(zip(first, second), start=1):
            assert same_page(left, right), f"interior page {number} differs on re-export"

    def test_the_comparison_tells_pages_apart_by_position(self) -> None:
        """Control, same run: determinism is not "every page equals every page".

        A comparison that ignored which page it was handed would pass the test
        above on a book of 16 identical pages. Two puzzle pages, a puzzle page
        and a divider and a puzzle page and an answer page are all different
        pages of one export, and a book with its pages swapped is not the same
        book.
        """
        pages = _raw_interior(_book_of(*self.BOOK))

        assert not same_page(pages[5], pages[6]), "E1 and E2 read as one page"
        assert not same_page(pages[5], pages[4]), "a puzzle and a divider"
        assert not same_page(pages[5], pages[13]), "a puzzle and its answer page"
        swapped = list(pages)
        swapped[5], swapped[6] = swapped[6], swapped[5]
        assert [same_page(a, b) for a, b in zip(pages, swapped)].count(False) == 2

    def test_a_page_of_operators_is_its_twin_and_nothing_less(self) -> None:
        """Control for :func:`same_page`: it says yes to a twin and no to each
        kind of difference, including a medium change."""
        assert same_page(_stream(), _stream())
        assert not same_page(_stream(), _stream(extra=True)), "one mark more"
        assert not same_page(_stream(), _stream(width_px=301)), "another extent"
        white, black = Image.new("RGB", (4, 4), "white"), Image.new("RGB", (4, 4), "black")
        assert same_page(white, Image.new("RGB", (4, 4), "white"))
        assert not same_page(white, black), "one bitmap against another"
        assert not same_page(white, _stream()), "a bitmap is never a stream"
        assert not same_page(_stream(), white), "and a stream is never a bitmap"

    @staticmethod
    def _written_page(
        puzzle: dict, page_number: int, number: int, tier: str
    ) -> ContentStream:
        return BookPDFGenerator(_book()).vector_puzzle_page(
            _banded_payload(puzzle, tier), number, page_number
        )

    def test_an_operators_page_is_named_by_its_position_number_tier_and_puzzle(
        self,
    ) -> None:
        puzzles = _book_of(*AC253_MEMBERS)
        page = self._written_page(puzzles[0], 6, 1, "Easy")

        assert names_the_page(page, puzzles[0], 6, 1, "Easy"), "the control"
        assert not names_the_page(page, puzzles[0], 6, 2, "Easy"), "another number"
        assert not names_the_page(page, puzzles[0], 6, 1, "Medium"), "another tier"
        assert not names_the_page(page, puzzles[1], 6, 1, "Easy"), "another puzzle"
        # The edge: the neighbouring page, which is the other parity. A walk
        # that numbered pages from the wrong end of the sheet is one page off.
        assert not names_the_page(page, puzzles[0], 7, 1, "Easy"), "the next page"
        assert not names_the_page(page, puzzles[0], 5, 1, "Easy"), "the previous page"

    def test_the_bands_words_are_read_from_the_text_layer_not_from_band_identity(
        self, monkeypatch
    ) -> None:
        """The twin and the page both use ``band_identity``, so they cannot
        disagree about it; the text layer is what can. Plant a ``band_identity``
        that drops the dot's spaces and BOTH the page and its twin carry it --
        and the page is still refused."""
        puzzles = _book_of(*AC253_MEMBERS)
        control = self._written_page(puzzles[0], 6, 1, "Easy")
        assert band_lines(control) == ["Puzzle 1 · Easy"], "the control reads"

        monkeypatch.setattr(
            "nonogram.admin.book_pdf_generator.band_identity",
            lambda number, tier: f"Puzzle {number}·{tier}",
        )
        planted = self._written_page(puzzles[0], 6, 1, "Easy")

        assert same_page(planted, expected_in_the_medium_of(planted, puzzles[0], 6, 1, "Easy"))
        assert band_lines(planted) != ["Puzzle 1 · Easy"]
        assert not names_the_page(planted, puzzles[0], 6, 1, "Easy")

    def test_the_footer_window_is_derived_and_a_floor_past_either_end_is_refused(
        self,
    ) -> None:
        for columns, rows in ((10, 10), (20, 20), (30, 30), (15, 20), (30, 10)):
            puzzle = _puzzle("W", "easy", columns, rows)
            for page_number in (6, 7, 150):
                page = self._written_page(puzzle, page_number, 1, "Easy")
                words = _words_of(page)
                floor = footer_floor(words)
                clue_top = max(
                    w.top for w in words if w.text.isdigit() and w.top < floor - 0.5
                )
                where = (columns, rows, page_number)
                # the window: the lowest clue digit is above the derived floor
                assert clue_top < floor, where
                assert footer_digits(page, (columns, rows)) == [str(page_number)], where
                # control, just past the LOW end: a floor at the lowest clue
                # digit takes a clue digit for part of the footer
                assert footer_digits(page, (columns, rows), clue_top) != [
                    str(page_number)
                ], where
                # control, just past the HIGH end: a floor below the footer row
                # finds no folio at all
                assert footer_digits(page, (columns, rows), floor + 1.0) == [], where

    def test_a_page_with_no_footer_has_no_folio_and_is_refused_loudly(self) -> None:
        """A 20x30 and a 10x30 vector page carry no footer (measured: no "x"
        label word on pages 6, 7 and 150). The control is the page beside them
        that does."""
        control = self._written_page(_puzzle("C", "easy", 20, 20), 6, 1, "Easy")
        assert footer_digits(control, (20, 20)) == ["6"]
        for columns, rows in ((20, 30), (10, 30)):
            puzzle = _puzzle("N", "easy", columns, rows)
            for page_number in (6, 7, 150):
                page = self._written_page(puzzle, page_number, 1, "Easy")
                assert not any(w.text == "x" for w in _words_of(page))
                with pytest.raises(AssertionError, match="no footer"):
                    footer_digits(page, (columns, rows))

    def test_the_page_position_is_read_from_the_folio_not_from_the_page_it_was_drawn_for(
        self, monkeypatch
    ) -> None:
        """An off-by-one in the writer's page number is carried by the page AND
        its twin (both go through the writer), so equality cannot see it; the
        folio, read by poppler, can. Plant it and the page is refused."""
        puzzles = _book_of(*AC253_MEMBERS)
        control = self._written_page(puzzles[0], 6, 1, "Easy")
        # The grid's own size, as its footer label prints it (this module's
        # default puzzle is ``_PUZZLE_COLUMNS`` x 20 since the packing limit
        # was raised).
        extent = (puzzles[0]["width"], puzzles[0]["height"])
        assert footer_digits(control, extent) == ["6"], "the control reads its folio"

        real = BookPDFGenerator.vector_puzzle_page

        def one_page_late(self, payload, puzzle_number, puzzle_page, *args, **kw):
            return real(self, payload, puzzle_number, puzzle_page + 1, *args, **kw)

        monkeypatch.setattr(BookPDFGenerator, "vector_puzzle_page", one_page_late)
        planted = self._written_page(puzzles[0], 6, 1, "Easy")

        assert same_page(planted, expected_in_the_medium_of(planted, puzzles[0], 6, 1, "Easy"))
        assert footer_digits(planted, extent) == ["7"]
        assert not names_the_page(planted, puzzles[0], 6, 1, "Easy")
