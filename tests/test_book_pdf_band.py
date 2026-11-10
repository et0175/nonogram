"""CARD-117 — the band, the title's one page, and print-weight rules (ADR-0037).

    AC-193  TestBookPdf_PuzzlePageCarriesNoPictureTitle
    AC-194  TestBookPdf_AnswerKeyCarriesPictureTitle
    AC-195  TestBookPdf_EveryFifthGridLineWider
    EC(ADR-0037/R1)
            PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle

CARD-170 — the band prints once, read from the exported PDF's bytes:

    AC-1, AC-2  TestBookPdf_BandPrintsOnceInTheExportedPdf
    AC-3        TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage

How a band is read back without an OCR this project does not have
-----------------------------------------------------------------
A band is ink, and nothing in the dependency baseline turns ink back into
letters. So a band is asserted by **rendering the text this card specifies and
comparing pages**: the expected line ("Puzzle 1 · Easy") is written out by
hand here, set through COMP-007's own header with the same payload the page
otherwise has, and the result is compared with the page the generator built.
Two pages that differ by one character of band text differ in their pixels, so
the comparison is exact in both directions — it fails a band that says too
much (a picture title on a puzzle page) and one that says something else (the
wrong number, a raw ``"easy"``, an invented label).

What that comparison does *not* prove on its own is that the band says
anything at all: two blank bands are equal too. Every band asserted here is
therefore also checked to carry ink, and the negative controls
(:meth:`TestBookPdf_PuzzlePageCarriesNoPictureTitle.test_renaming_the_picture_leaves_the_puzzle_page_identical`
and its answer-page twin) rename the picture and require the answer page to
*change* — so the same measurement that reports "the name is not on the
puzzle page" is shown to report the name when it is there.

The tier labels, the band's wording and its separator are spelled out in this
module as constants of their own. Nothing here imports
``nonogram.difficulty.tier_of_record`` or ``book_pdf_generator``'s own
``BAND_SEPARATOR``/``band_identity``: the expected string is a second
implementation of ADR-0037's rule, not the same one run twice (CLAUDE.md).

AC-195 measures the rendered page rather than the layout: the rules are found
as runs of ink along a scanline that crosses the grid between two rules, and
their thicknesses are counted in pixels. ``page_ink.drawing_of`` — a helper
that reaches the grid box by a different route, the longest unbroken run on
every line of the page — supplies the box those scanlines are taken inside,
so the two agree on where the grid is before either measures anything in it.
"""

from __future__ import annotations

import math
import random
import re
import tempfile
from collections import Counter
from functools import lru_cache
from importlib import resources
from io import BytesIO
from typing import Iterable, Iterator, NamedTuple, Sequence

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram import clues, errors
from nonogram.admin import book_interior_vector
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    DPI,
    BookPDFGenerator,
    PageKind,
    PageMedium,
    page_medium,
    band_identity,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.admin import book_vector
from nonogram.admin.book_vector import (
    ContentStream,
    UnrepresentableText,
    encode_text,
    write_vector_pdf,
)
from pathlib import Path

from tests.helpers import pdf_vector
from tests.helpers.page_ink import drawing_of
from tests.helpers.pdf_pages import Page, interior_images, pdf_pages
from tests.helpers.pdf_vector import Word
# CARD-219: the readers the shared-render controls at the end of this file are
# built on, which CARD-218 had to write out here and again in
# ``tests/test_book_puzzle_frame.py``. Aliased to the names those controls
# already call, so this file's call sites are unchanged.
from tests.helpers.shared_fixture_controls import (
    bitmap_bytes as _bitmap_bytes,
    lru_cache_names as _lru_cache_names,
    page_digest as _page_digest,
    refuse_unless_every_consumer_is_collected as _refuse_unless_every_consumer_is_collected,
    refuse_unless_nothing_takes_it_later as _refuse_unless_nothing_takes_it_later,
    retained_bitmap_bytes as _retained_bitmap_bytes,
)
# The project's own figure for one book page — 2550 x 3300 RGB, 25,245,000 B.
# Imported rather than restated so the retention bound at the end of this file
# is the unit this repo already reasons in, and cross-checked against the
# pages this module actually draws by
# ``TestBookPdf_TheSharedRenderLeavesNoBitmapBehind.test_the_page_bitmap_unit_is_this_modules_own_page``,
# so it cannot quietly come to mean something else.
from tests.test_book_pdf_memory import PAGE_BITMAP_BYTES

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out here rather than
# imported — the same figures tests/test_book_pdf.py works from.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
# CON-018's margins as amended 2026-10-17 (CARD-222): the outside margin
# moved 0.375 -> 0.5 in, the top to 0.55 in and the bottom to 0.47 in, and the
# gutter deliberately stayed at KDP's 0.5 in. Written out here, as this file
# writes every other figure out, rather than imported.
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4

#: The title band above each puzzle (TERM-028).
BAND_MM = 12.0

#: The strip an answer page keeps above its tiles for the running head
#: ("SOLUTIONS · EASY" / "PUZZLE 1", the approved solutions mockup), so an
#: answer's band starts this much lower than a puzzle's. Written out, as the
#: figures above are, rather than imported.
RUNNING_HEAD_MM = 9.0

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = 300 / 25.4


#: A pixel darker than this (0..255 grey) is ink, as ``page_ink`` reads one.
INK_LEVEL = 128

# --------------------------------------------------------------------------
# ADR-0037's band, restated
# --------------------------------------------------------------------------

#: The band's wording, as ADR-0037 writes it: "Puzzle 12 · Easy". The dot is
#: U+00B7 with a space either side.
BAND_TEMPLATE = "Puzzle {number} · {tier}"

#: The band of a puzzle whose row carries no tier anyone can read: the number
#: alone, with nothing after it. The documented decision of this card — see
#: ``book_pdf_generator.band_identity``.
UNGRADED_TEMPLATE = "Puzzle {number}"

#: Every stored spelling of a tier this project can meet, mapped to the label
#: ADR-0031 displays it under. Written out rather than derived: ``"guess"`` is
#: ADR-0031/R3's retired fourth tier, which reads back as Hard, and any
#: other text — a blank, a word from no vocabulary, a number — is not a tier.
TIER_LABELS = {"easy": "Easy", "medium": "Medium", "hard": "Hard", "guess": "Hard"}


def expected_band(number: int, stored_tier: object) -> str:
    """ADR-0037's band line for a puzzle at print position ``number``.

    A second implementation of the rule, independent of the one under test:
    it maps the stored text to a label through :data:`TIER_LABELS` rather than
    through ``nonogram.difficulty``.
    """
    label = None
    if isinstance(stored_tier, str):
        label = TIER_LABELS.get(stored_tier.strip().casefold())
    if label is None:
        return UNGRADED_TEMPLATE.format(number=number)
    return BAND_TEMPLATE.format(number=number, tier=label)


# --------------------------------------------------------------------------
# FR-042's answer caption, restated (guardrail G-2a)
# --------------------------------------------------------------------------

#: What captioned one answer in the key: the puzzle's number, an em dash
#: (U+2014) with a space either side, and the picture's title. Written out
#: here for the same reason :data:`BAND_TEMPLATE` is — a second implementation
#: of the rule, not ``book_answer_key``'s own ``answer_caption`` run twice.
#: **Retired from the page by the approved solutions mockup**: the title now
#: sits in the solution header beside the number alone, so the tests below
#: hold this string to being printed nowhere.
ANSWER_CAPTION = "Puzzle {number} — {title}"


# --------------------------------------------------------------------------
# The book, its puzzles, and its pages
# --------------------------------------------------------------------------


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book() -> Book:
    """A book on CON-018's Book 1 profile, as a ``books`` row carries it."""
    return Book(
        book_id="book-117",
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


def _gutter_grid(columns: int, rows: int, depth: int) -> list[list[bool]]:
    """A grid whose row **and** column clues are exactly ``depth`` entries deep.

    Every other cell filled along both axes, stopped after ``depth`` runs, so
    the deepest clue in each direction is ``depth`` — which is what decides how
    many cells wide and tall the *drawing* is, and so the printed cell.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    return [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]


#: This module's default puzzle: the largest the book holds. Since answers up
#: to 30x30 pack (owner, 2026-11-09) its answer shares the packed answer page
#: shape every answer has; one puzzle per level still means one answer page
#: per puzzle, which is the page arithmetic below.
_DEFAULT_SIZE = MAX_SIZE


def _puzzle(
    columns: int = _DEFAULT_SIZE,
    rows: int = _DEFAULT_SIZE,
    depth: int = 3,
    name: str | None = "Snowflake",
    tier: object = "easy",
    puzzle_id: str = "p",
) -> dict:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _gutter_grid(columns, rows, depth)
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": tier,
    }


def _raw_interior(puzzles: Sequence[dict], book: Book | None = None) -> list[Page]:
    """The book's interior as the generator hands it back: each page in the
    medium its kind is written in (CARD-356).

    A bitmap for a raster page and a ``ContentStream`` for a page written as
    operators (ADR-0042/R1). A claim about what a page *says* is read from
    this, in the page's own medium; a claim about what it *looks like* goes
    through :func:`_interior`.
    """
    return BookPDFGenerator(book if book is not None else _book()).interior_pages(
        list(puzzles)
    )


def _interior(puzzles: Sequence[dict], book: Book | None = None) -> list[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``.

    **CARD-356: the medium is read here and nowhere else.** Every pixel claim
    below is stated on device pixels, so the conversion is absorbed at this one
    seam -- ``interior_images`` returns a raster page unchanged and rasterises
    an operators page with poppler at the page's own DPI. The seam is applied
    only where the claim is about the *picture*; a claim about a *mark* (the
    band's words, a rule's tone and weight) is read from the stream instead,
    see :func:`_find` and :class:`TestBookPdf_EveryFifthGridLineWider`.
    """
    return interior_images(_raw_interior(puzzles, book))


def _same_page(left: Page, right: Page) -> bool:
    """Two pages are the same page: same medium, and exactly the same marks.

    Bitmaps by their bytes, operators by their operators and extent. A bitmap
    and a stream are never equal -- comparing across media is what made the
    original ``page.tobytes() == expected.tobytes()`` claims red once the page
    stopped being a bitmap, and it is refused here rather than rasterised
    into agreement.
    """
    if isinstance(left, Image.Image) and isinstance(right, Image.Image):
        return left.tobytes() == right.tobytes()
    if isinstance(left, ContentStream) and isinstance(right, ContentStream):
        return (
            left.operators == right.operators
            and (left.width_px, left.height_px, left.dpi)
            == (right.width_px, right.height_px, right.dpi)
        )
    return False


@pytest.fixture(scope="module")
def snowflake_raw() -> list[Page]:
    """The one-puzzle "Snowflake" book as the generator hands it back, drawn
    once for the module: bitmaps and content streams, in print order."""
    return _raw_interior([_puzzle()])


@pytest.fixture(scope="module")
def snowflake_interior(snowflake_raw: list[Page]) -> list[Image.Image]:
    """The one-puzzle "Snowflake" book, as device pixels, drawn once (CARD-218).

    AC-193's and AC-194's classes are two readings of the same printed book —
    the puzzle page carries the identity and not the title, the answer page
    carries both — and four tests across those two classes drew that book
    again each time to read a different page of it: 0.286 s of byte-identical
    repeated rendering, measured.

    Module scope because the duplication spans two classes; not session scope,
    which would keep this book's bitmaps alive for the rest of the run (the
    card's rule 2, and CARD-145's peak-memory concern).

    **CARD-356:** the pages are :func:`snowflake_raw` seen through the
    ``interior_images`` seam, so a page written as operators is here as the
    poppler raster of it. Read-only: every consumer reads the pixels and none
    draws on them.

    The two classes name their picture themselves (``NAME``), and this book is
    :func:`_puzzle`'s default one — so the agreement is asserted here rather
    than assumed. Rename the picture in one class and this goes red at the
    fixture, which is where the divergence is, instead of leaving that class
    silently measuring the other one's book.
    """
    shared = _puzzle()
    for owner in (
        TestBookPdf_PuzzlePageCarriesNoPictureTitle,
        TestBookPdf_AnswerKeyCarriesPictureTitle,
    ):
        assert owner.NAME == shared["puzzle_name"], (
            f"{owner.__name__} reads a book titled {owner.NAME!r}, and this "
            f"fixture draws {shared['puzzle_name']!r}: it needs a render of "
            "its own, or this fixture needs its name"
        )
    drawn = interior_images(snowflake_raw)
    _SHARED_SNOWFLAKE_DIGEST.extend(_page_digest(page) for page in drawn)
    return drawn


#: A sha256 per page of :func:`snowflake_interior` as it was drawn, filled by
#: the fixture and read back by its mutation control at the end of this module.
#: A list rather than a module-level rebinding, so the control cannot pass by
#: reading a name the fixture never set — and a *digest* rather than the bytes,
#: because this list outlives the fixture (see :func:`_page_digest`, and the
#: retention control at the end of this file, which holds every module-level
#: accumulator of this file to exactly 32 B per page of the book it signed).
_SHARED_SNOWFLAKE_DIGEST: list[bytes] = []


#: Where each level sits in the book: easy, then medium, then hard (INV-009).
#: Written out here, keyed on the *label* this module already derives from the
#: stored word, so the print order below is this module's own reading of
#: FR-041 and not ``book_plan``'s run twice.
LEVEL_RANK = {"Easy": 0, "Medium": 1, "Hard": 2}

#: Where a row whose stored tier is no tier at all sits: after every level,
#: and behind no divider — there is no name to put on one.
UNGRADED_RANK = len(LEVEL_RANK)


def level_rank(stored_tier: object) -> int:
    """Which level a stored tier word belongs to, :data:`UNGRADED_RANK` if none."""
    label = None
    if isinstance(stored_tier, str):
        label = TIER_LABELS.get(stored_tier.strip().casefold())
    return UNGRADED_RANK if label is None else LEVEL_RANK[label]


def print_plan(puzzles: Sequence[dict]) -> dict[int, tuple[int, int]]:
    """``{index in the book: (puzzle number, interior page)}`` (CARD-128).

    This module's own reading of the printed book: the rows grouped easy, then
    medium, then hard — a **stable** sort on the level alone, so the order
    inside a level is the one the book was handed in — numbered 1..n over the
    puzzles, and laid out from interior page 5 (CARD-206: the blank title
    page is interior page 1, up from 4 before it; CARD-201: the guide is 2
    pages, not 1; CARD-200: a 1-page table of contents follows it — this
    module's own books never hold more than :data:`MIN_POSITION` + 1 puzzles,
    far under Book 1's own TOC capacity, so the TOC is always exactly one
    page) with one divider page opening each non-empty *named* level. Every
    book here is one of 15..20-cell drawings that never pair (see the class
    docstrings), so a puzzle takes a page.
    """
    order = sorted(range(len(puzzles)), key=lambda index: level_rank(puzzles[index]["difficulty_tier"]))
    plan: dict[int, tuple[int, int]] = {}
    page = 5
    opened: object = None
    for number, index in enumerate(order, start=1):
        rank = level_rank(puzzles[index]["difficulty_tier"])
        if rank != opened:
            opened = rank
            if rank != UNGRADED_RANK:
                page += 1  # this level's divider
        plan[index] = (number, page)
        page += 1
    return plan


def puzzle_page_number(puzzles: Sequence[dict], index: int = 0) -> int:
    """Where puzzle ``index`` (0-based in the book) prints in the interior."""
    return print_plan(puzzles)[index][1]


def solutions_page_number(puzzles: Sequence[dict]) -> int:
    """Where the SOLUTIONS divider sits: after the last puzzle page."""
    return max(page for _, page in print_plan(puzzles).values()) + 1


def answer_page_number(puzzles: Sequence[dict], index: int = 0) -> int:
    """Where puzzle ``index``'s answer prints.

    One full answer page per puzzle, in book order, behind the SOLUTIONS
    divider (CARD-198) — so the answer's page is simply its print number's
    place after that divider, for any book this module builds.
    """
    number, _ = print_plan(puzzles)[index]
    return solutions_page_number(puzzles) + number


# --------------------------------------------------------------------------
# Reading ink off a page
# --------------------------------------------------------------------------


def _band_strip(page: Image.Image) -> Image.Image:
    """The page's title band: the 12 mm below the top margin (TERM-028).

    Worked out in millimetres from CON-018's profile, not read off a layout.
    """
    top = round(TOP_MM * PX_PER_MM)
    return page.crop((0, top, page.width, top + round(BAND_MM * PX_PER_MM)))


def _has_ink(image: Image.Image) -> bool:
    return bool((np.asarray(image.convert("L")) < INK_LEVEL).any())


def _ink_pixels(image: Image.Image) -> int:
    """How many of ``image``'s pixels are ink, as :func:`_has_ink` reads one."""
    return int((np.asarray(image.convert("L")) < INK_LEVEL).sum())


def _rows_that_differ(left: Image.Image, right: Image.Image) -> np.ndarray:
    """The indices of the pixel rows on which two same-sized pages disagree."""
    theirs = np.asarray(left.convert("L"))
    others = np.asarray(right.convert("L"))
    assert theirs.shape == others.shape, "the pages are not the same size"
    return np.flatnonzero((theirs != others).any(axis=1))


def _runs(mask: Iterable[bool]) -> list[list[int]]:
    """The consecutive runs of ``True`` in ``mask``, as lists of indices."""
    runs: list[list[int]] = []
    for index, is_set in enumerate(mask):
        if not is_set:
            continue
        if runs and runs[-1][-1] == index - 1:
            runs[-1].append(index)
        else:
            runs.append([index])
    return runs


def _rule_widths(scan: np.ndarray) -> list[int]:
    """The thickness in pixels of each ruled line a scanline crosses.

    ``scan`` is one pixel row or column of the page, cut to the grid's own
    extent and taken **between** two rules of the other axis, so on a blank
    puzzle page the only ink it can meet is the rules it crosses: one run of
    ink per rule, its length that rule's printed width.
    """
    return [len(run) for run in _runs(scan < INK_LEVEL)]


# --------------------------------------------------------------------------
# AC-193 — the picture's title is not on its puzzle page
# --------------------------------------------------------------------------


class TestBookPdf_PuzzlePageCarriesNoPictureTitle:
    """AC-193 — a book holding "Snowflake" prints no "Snowflake" on its page.

    FR-033: a titled puzzle page gives the picture away before it is drawn.
    """

    NAME = "Snowflake"

    def test_the_puzzle_page_is_the_page_of_a_nameless_payload(
        self, snowflake_raw, snowflake_interior
    ) -> None:
        """The page is, pixel for pixel, the page of a payload with no name.

        The band it *does* carry is "Puzzle 1 · Easy" — written out here — so
        this asserts both halves of ADR-0037/R1 at once: the identity is
        printed and the title is not. A page carrying "Snowflake" anywhere,
        in the band or beside the grid, differs from this one.

        The page must be, operator for operator, the page the generator draws
        for the same puzzle with **no name at all**, and its text layer --
        poppler's, which did not write it -- must read the band
        ``"Puzzle 1 · Easy"`` written out here and no word of the title.
        ``test_the_answer_page_carries_the_title_and_the_same_identity``        primitives. ``test_the_answer_page_carries_the_title_and_the_same_identity``
        is this test's matched control: the same reading finds the title on
        the page that is supposed to carry it.
        """
        puzzle = _puzzle(name=self.NAME)
        number = puzzle_page_number([puzzle])
        page = snowflake_interior[number - 1]
        raw = snowflake_raw[number - 1]

        assert _has_ink(_band_strip(page)), "the band is blank"
        nameless = _raw_interior([_puzzle(name=None)])[number - 1]
        assert _same_page(raw, nameless), "the title changed the puzzle page"
        assert isinstance(raw, ContentStream), "an interior page here is operators"
        lines = _text_of(raw)
        assert [line.text for line in _band_zone(lines)] == ["Puzzle 1 · Easy"]
        assert self.NAME not in {
            word for line in lines for word in line.text.split()
        }

    def test_renaming_the_picture_leaves_the_puzzle_page_identical(
        self, snowflake_interior
    ) -> None:
        """Rename the picture and not one pixel of its puzzle page moves.

        The control the previous test needs: the same book, the same position,
        a different name. The puzzle pages are identical and the *answer*
        pages are not, so a measurement that reports "the name is not here"
        is shown to report a name when there is one.
        """
        snowflake = _puzzle(name=self.NAME)
        renamed = _puzzle(name="Iguanodon Skeleton")

        theirs = snowflake_interior
        others = _interior([renamed])
        puzzle_page = puzzle_page_number([snowflake]) - 1
        answer_page = answer_page_number([snowflake]) - 1

        assert theirs[puzzle_page].tobytes() == others[puzzle_page].tobytes()
        assert theirs[answer_page].tobytes() != others[answer_page].tobytes()


# --------------------------------------------------------------------------
# AC-194 — the title appears on the answer-key page
# --------------------------------------------------------------------------


class TestBookPdf_AnswerKeyCarriesPictureTitle:
    """AC-194 — the same book's answer-key page shows "Snowflake".

    Beside the same number the puzzle page's "Puzzle N · Tier" identity
    carries, so the answer is found by the printed number and recognised by
    the name. Since the approved solutions mockup the answer sets them as a
    solution header (the number alone, then the name; the tier as dots and in
    the running head's "SOLUTIONS · EASY"), not as a band line over a
    "Puzzle N — Name" caption.
    """

    NAME = "Snowflake"

    def test_the_answer_page_carries_the_title_and_the_same_identity(
        self, snowflake_raw, snowflake_interior
    ) -> None:
        """The title is on the answer page and is not on the puzzle page.

        Three measurements, one book, by poppler's text layer: **absent** --
        the puzzle page has the identity and no title word; **present** -- the
        answer page's solution header is the same number alone and then
        "Snowflake", with the tier in the running head above it and no
        "Puzzle 1 — Snowflake" caption; **contributing** -- the same book
        with no title sets the number alone, so the title is a mark and not a
        string that was offered.
        """
        number = 1
        puzzle = _puzzle(name=self.NAME)
        pages = snowflake_interior
        puzzle_raw = snowflake_raw[puzzle_page_number([puzzle]) - 1]
        answer_raw = snowflake_raw[answer_page_number([puzzle]) - 1]
        identity = expected_band(number, puzzle["difficulty_tier"])
        caption = ANSWER_CAPTION.format(number=number, title=self.NAME)

        assert isinstance(puzzle_raw, ContentStream), "an interior page here is operators"
        puzzle_lines = _text_of(puzzle_raw)
        assert [line.text for line in _band_zone(puzzle_lines)] == [identity]
        assert self.NAME not in {
            word for line in puzzle_lines for word in line.text.split()
        }
        answer_lines = _text_of(answer_raw)
        assert _solution_header(answer_lines) == [str(number), self.NAME]
        assert sorted(_running_head(answer_lines)) == sorted(
            [_running_head_section(puzzle["difficulty_tier"]), f"PUZZLE {number}"]
        )
        assert not [line.text for line in answer_lines if "—" in line.text], (
            f"the retired caption {caption!r} is still under the grid"
        )
        untitled = _raw_interior([_puzzle(name=None)])[
            answer_page_number([puzzle]) - 1
        ]
        untitled_lines = _text_of(untitled)
        assert not any(self.NAME in line.text for line in untitled_lines)
        assert _solution_header(untitled_lines) == [str(number)]

    def test_the_title_is_ink_the_answer_band_would_not_have_without_it(
        self, snowflake_interior
    ) -> None:
        """Withhold the title and the *same* answer page loses ink, in one place.

        Retargeted under G-2b (FR-042's packed key), and again under
        CARD-198 (one full solved page per puzzle). The control is the same
        page kind, one caption apart: this very answer page drawn again with
        ``title=None`` — what ``solved_puzzle_page`` prints if the title were
        withheld (``answer_caption`` stops at the number when there is no
        title, and the em dash is not printed with nothing after it). Three
        measurements of the one difference:

        * the two pages are **not** equal, so the title changed the page;
        * the titled page carries **strictly more** ink. The caption's face
          and size are fixed by the tile's geometry, never by the text in it,
          so a longer caption can only add glyphs — a title that merely
          displaced the number, or blanked it, would not raise the count;
        * the rows that differ are **one unbroken run, shorter than the 12 mm
          band** — a single line of type, the caption's. The title's ink is
          where a caption is and nowhere else, so a page that changed because
          its tile moved, its heading changed or a second answer appeared
          fails here rather than passing as "the title did something".

        **Since the approved solutions mockup** that one line is the solution
        header's (the number alone, then the title), not a caption under the
        drawing; the measurement is unchanged, and so is what it pins.

        That last measurement is also the retired ``_has_ink(_band_strip(...))``
        line's epitaph. This whole difference is ~31 pixel rows; the strip it
        read is 142, and measured, that strip still holds some 18,000 ink
        pixels with ``heading=None`` *and* an untitled caption, because the
        answer tile is drawn through it. That assertion tested the tile.

        This is the third witness ADR-0037/R1 keeps here, and it is narrower
        than its siblings by design — they pin the whole page against a
        written-out expectation, this one isolates what the title alone did.
        """
        number = 1
        puzzle = _puzzle(name=self.NAME)
        page_number = answer_page_number([puzzle])
        page = snowflake_interior[page_number - 1]

        # The control: the same book with no title, drawn and read the same way.
        untitled = _interior([_puzzle(name=None)])[page_number - 1]
        assert page.tobytes() != untitled.tobytes(), "the title changed nothing"
        assert _ink_pixels(page) > _ink_pixels(untitled), "the title added no ink"

        differing = _rows_that_differ(page, untitled)
        assert len(differing), "the pages differ in no row"
        assert list(differing) == list(
            range(int(differing.min()), int(differing.max()) + 1)
        ), "the title's ink is not one line of type"
        assert len(differing) < round(BAND_MM * PX_PER_MM), (
            "the title changed more of the page than a caption line is tall"
        )

    def test_the_answer_number_is_the_number_printed_on_the_puzzle(self) -> None:
        """Every answer is captioned with its own puzzle's number, not its page's.

        A book of three at three tiers, so FR-042/CARD-128 gives each level a
        divider of its own and the three puzzles print on pages 3, 5 and 7 —
        their own full answer pages following on 8, 9 and 10 — which means an
        answer captioned from its position in the interior rather than from
        the puzzle it answers would read a number one or two off and be
        caught. (Since the approved solutions mockup the number and the title
        are the answer's solution header, not a caption under the drawing.) Each page is compared whole, so a caption carrying the wrong
        number or the wrong title fails, and each is then re-checked against
        its untitled control so the title is shown to be ink on every one of
        them.

        Retargeted under G-2a, and again under CARD-198: the assertion moved
        from the per-puzzle answer page to the packed key and back again, and
        the rule it asserts — the title prints here and its number is the
        puzzle's — is unchanged throughout.
        """
        puzzles = [
            _puzzle(name=f"Picture {index}", puzzle_id=f"p{index}", tier=tier)
            for index, tier in enumerate(("easy", "medium", "hard"))
        ]
        raw = _raw_interior(puzzles)
        pages = interior_images(raw)
        untitled_book = [
            _puzzle(name=None, puzzle_id=f"p{index}", tier=tier)
            for index, tier in enumerate(("easy", "medium", "hard"))
        ]
        untitled_pages = _interior(untitled_book)

        for index, puzzle in enumerate(puzzles):
            number = index + 1
            page_number = answer_page_number(puzzles, index)
            page = pages[page_number - 1]

            assert isinstance(raw[page_number - 1], ContentStream), "an interior page here is operators"
            # CARD-356: stream arm. The solution header (the approved
            # solutions mockup) is read from the text layer and must be
            # exactly this puzzle's own N and then "Picture k", with the
            # running head above it naming the same N and the puzzle's
            # tier; the title is shown to be ink by the same book drawn
            # with no titles, whose page must differ.
            lines = _text_of(raw[page_number - 1])
            assert _solution_header(lines) == [
                str(number), puzzle["puzzle_name"]
            ], f"answer {number}"
            assert sorted(_running_head(lines)) == sorted(
                [_running_head_section(puzzle["difficulty_tier"]), f"PUZZLE {number}"]
            ), f"answer {number} band"
            assert (
                page.tobytes() != untitled_pages[page_number - 1].tobytes()
            ), f"answer {number} shows no title"


# --------------------------------------------------------------------------
# AC-195 — every 5th rule is wider than every rule between them
# --------------------------------------------------------------------------


#: One entry per execution of :meth:`TestBookPdf_EveryFifthGridLineWider.page`.
#: CARD-218's control on that conversion: the class's five tests pass whatever
#: the fixture's scope is, so without a count there is nothing that fails when
#: the page goes back to being drawn once per test.
_FIFTH_RULE_RENDERS: list[tuple[int, int, int]] = []


#: ADR-0037/R2's three grid weights, written out here (a second statement of
#: them, not ``book_page_spec.GRID_RULES`` read back): the cell lines at
#: 0.3 pt in a 0.35 grey, the every-fifth line at 1.1 pt (the owner raised it
#: from 0.8 pt on 2026-11-08) and the border at 1.3 pt, both in pure black.
CELL_RULE_PT = 0.3
CELL_RULE_GREY = 0.35
FIFTH_RULE_PT = 1.1
BORDER_RULE_PT = 1.3

_STROKE_GREY = re.compile(rf"^({pdf_vector.NUMBER}) G$")
_STROKE_WIDTH = re.compile(rf"^({pdf_vector.NUMBER}) w$")
_STROKE_LINE = re.compile(
    rf"^({pdf_vector.NUMBER}) ({pdf_vector.NUMBER}) m "
    rf"({pdf_vector.NUMBER}) ({pdf_vector.NUMBER}) l S$"
)


class _Rule(NamedTuple):
    axis: str
    #: Points: ``x`` of a vertical rule, ``y`` (up from the foot) of a horizontal.
    position: float
    width: float
    grey: float


def _stroke_rules(stream: ContentStream) -> list[_Rule]:
    """Every ``m``/``l``/``S`` rule a stream strokes before its first marked
    content, with the tone and width in force when it was stroked.

    Read from the content stream **as written to a PDF**, through
    ``pdf_vector.content_streams`` -- not from the object's own operator list --
    so the reading is of the file and the state (``G``, ``w``) is carried the
    way a viewer carries it. The grid is drawn before the clue digits' marked
    content opens, which is where this stops; a rule drawn after that point
    (the sheet's furniture) is not one of the grid's.
    """
    data = write_vector_pdf([stream], 1).getvalue()
    (text,) = pdf_vector.content_streams(data)
    grey, width = 0.0, 1.0
    rules = []
    for row in text.splitlines():
        if row.endswith(" BMC"):
            break
        if match := _STROKE_GREY.match(row):
            grey = float(match.group(1))
        elif match := _STROKE_WIDTH.match(row):
            width = float(match.group(1))
        elif match := _STROKE_LINE.match(row):
            x1, y1, x2, y2 = (float(group) for group in match.groups())
            if x1 == x2:
                rules.append(_Rule("vertical", x1, width, grey))
            elif y1 == y2:
                rules.append(_Rule("horizontal", y1, width, grey))
    return rules


def _grid_rules(stream: ContentStream) -> dict[str, list[_Rule]]:
    """The grid's rules per axis, in reading order: left to right, top to bottom.

    Refuses a page that does not have a ruled line more than the grid has
    cells on each axis, so a stream with the wrong grid is a failure here and
    not a short list that happens to pass.
    """
    rules = _stroke_rules(stream)
    vertical = sorted(
        (rule for rule in rules if rule.axis == "vertical"), key=lambda r: r.position
    )
    horizontal = sorted(
        (rule for rule in rules if rule.axis == "horizontal"),
        key=lambda r: -r.position,
    )
    assert len(vertical) == MAX_SIZE + 1, len(vertical)
    assert len(horizontal) == MAX_SIZE + 1, len(horizontal)
    return {"vertical": vertical, "horizontal": horizontal}


def _unexplained_greys(scan: np.ndarray, declared: set[int]) -> set[int]:
    """The grey levels on ``scan`` that ``declared`` does not account for."""
    return set(np.unique(scan).tolist()) - declared


class TestBookPdf_EveryFifthGridLineWider:
    """AC-195 — measured on a Book 1 page holding a 30x30 at 4.97 mm.

    ADR-0037/R2's strokes come from the book ``PageSpec`` (COMP-007 applies
    them; the admin panel draws no rule of its own, G-1). What is asserted
    here is the printed result: thickness in pixels, rule by rule, on the page
    the generator produced.
    """

    #: The 30x30 with 9-deep clue gutters AC-175 measures at 4.885 mm on Book 1
    #: (4.97 mm before CON-018's 2026-10-17 margin amendment).
    PUZZLE = (MAX_SIZE, MAX_SIZE, 9)
    CELL_MM = 4.885
    CELL_TOLERANCE_MM = 0.05

    #: Heavy rules: the borders and every 5th line of a 30-cell grid.
    HEAVY_INDICES = (0, 5, 10, 15, 20, 25, 30)

    @pytest.fixture(scope="class")
    @classmethod
    def raw_page(cls) -> Page:
        """This class's one 30x30 page as the generator hands it back (CARD-356).

        A bitmap on the unconverted interior and a content stream on the
        converted one; ``page`` below is this seen through the
        ``interior_images`` seam. **The render that
        :data:`_FIFTH_RULE_RENDERS` counts happens here**, once for the class.
        """
        columns, rows, depth = cls.PUZZLE
        puzzle = _puzzle(columns, rows, depth)
        _FIFTH_RULE_RENDERS.append(cls.PUZZLE)
        return _raw_interior([puzzle])[puzzle_page_number([puzzle]) - 1]

    @pytest.fixture(scope="class")
    @classmethod
    def page(cls, raw_page: Page) -> Image.Image:
        """This class's one 30x30 page, drawn once for the class (CARD-218).

        Five tests measured this page and each one drew the whole interior to
        get it: 0.389 s of byte-identical repeated rendering, measured. Class
        scope rather than module scope because this page is read by this class
        alone — the card prefers the narrowest scope that removes the
        duplication, so the bitmap is released when the class is done instead
        of living to the end of the file (CARD-145's peak-memory concern).

        Read-only: ``drawing_of`` and :meth:`_scan` both read the image
        through ``np.asarray`` and return arrays of their own.
        """
        return interior_images([raw_page])[0]

    def test_the_grid_is_the_thirty_by_thirty_at_the_stated_cell(self, page) -> None:
        """The premise of the measurement, taken off the page itself."""
        drawing = drawing_of(page)
        assert (drawing.columns, drawing.rows) == (MAX_SIZE, MAX_SIZE)
        assert drawing.cell / PX_PER_MM == pytest.approx(
            self.CELL_MM, abs=self.CELL_TOLERANCE_MM
        )

    @pytest.mark.parametrize("axis", ["vertical", "horizontal"])
    def test_every_fifth_rule_is_wider_than_every_rule_between_them(
        self, axis: str, raw_page: Page, page: Image.Image
    ) -> None:
        """The heavy rules out-measure every thin one, down the page and across.

        The scanline is taken through the middle of the first cell of the
        other axis — inside the grid, between two rules — so every run of ink
        it meets is a rule of this axis and nothing else.

        **CARD-356: this claim is medium-specific, and the two media answer it
        differently.** The raster path draws a rule as a whole number of
        device pixels, so its heavy rules are all one width, exactly twice the
        thin one, and the thin one is held to :data:`MIN_THIN_RULE_PX`. A page
        of operators *declares* a width in points and the rasteriser resolves
        it: ADR-0037/R2 (amended 2026-10-25) gives it three weights, not two,
        and no millimetre floor, because there is no integer stroke for a
        floor to bind. So on a bitmap page every original assertion stands,
        and on a page of operators the claim is **re-expressed**:

        * *in the stream*, read from the written file: the rules of every
          fifth line are stroked wider than every rule between them, and the
          widths are exactly R2's 0.3 / 1.1 / 1.3 pt (written out here, not
          imported) on the cell lines, the fifths and the border;
        * *in poppler's raster of it*: the three tiers are ordered and
          disjoint in ink width, each within the span ADR-0037's 2026-10-28
          note measured -- the declared width in pixels up to two more.

        **Retired, with named survivors:** "heavy = 2 x thin" (the heavy tier
        is two weights on operators, so the ratio has no subject) and the
        0.25 mm / 3 px thin-rule floor, which is a rasteriser's. The floor's
        survivor is
        ``tests/test_book_grid_rules.py::TestBookGridRules_TheseWidthsNeverReachARasterGrid``
        (a raster grid is refused at the weights an operators grid is
        allowed), and the weights' own is
        ``tests/test_book_grid_rules.py::TestBookGridRules_HasThreeWeights``.
        """
        assert isinstance(raw_page, ContentStream), "an interior page here is operators"
        rules = _grid_rules(raw_page)[axis]
        widths_pt = [rule.width for rule in rules]
        heavy_pt = [widths_pt[index] for index in self.HEAVY_INDICES]
        thin_pt = [
            width
            for index, width in enumerate(widths_pt)
            if index not in self.HEAVY_INDICES
        ]
        assert min(heavy_pt) > max(thin_pt)
        assert set(thin_pt) == {CELL_RULE_PT}
        assert {widths_pt[0], widths_pt[-1]} == {BORDER_RULE_PT}
        assert {widths_pt[index] for index in self.HEAVY_INDICES[1:-1]} == {
            FIFTH_RULE_PT
        }

        ink = _rule_widths(self._scan(page, axis))
        assert len(ink) == MAX_SIZE + 1, "a 30-cell grid is ruled 31 times"
        tiers = {
            "cell": [w for i, w in enumerate(ink) if i not in self.HEAVY_INDICES],
            "fifth": [ink[i] for i in self.HEAVY_INDICES[1:-1]],
            "border": [ink[0], ink[-1]],
        }
        for tier, declared in (
            ("cell", CELL_RULE_PT),
            ("fifth", FIFTH_RULE_PT),
            ("border", BORDER_RULE_PT),
        ):
            declared_px = declared * DPI / 72.0
            # DECLARED BOUND (ADR-0039/R3). The band is [declared px,
            # declared px + 2]: ADR-0037's 2026-10-28 note states it as the
            # span poppler's ink can take for a stroke of that width.
            # Reason: it is a statement about *poppler's* stroke
            # adjustment, not about the file, and it depends on the
            # stroke's sub-pixel phase. MEASURED RESIDUE (poppler 26.08.0,
            # 300 DPI, by this card's reviewer): the real page inks
            # 2 / 4 / 6 px against declared 1.25 / 3.33 / 5.42 (excess
            # 0.75 / 0.67 / 0.58, inside the +2), and one-rule pages at some
            # sub-pixel phases ink 1 / 3 / 5 px (cell 1 px is BELOW the
            # declared 1.25, so the lower edge is not tight either). A
            # different poppler or a different phase can move a tier by a
            # pixel; the +2 is slack for that, not a tolerance on the
            # product, and the EDGE_* / HALF_PIXEL_MM bounds are untouched.
            # Since the fifth went to 1.1 pt (owner, 2026-11-08) it is
            # declared 4.58 px and poppler inks it 4, so the lower edge is
            # one pixel under the declared width; the tier ordering just
            # below is what keeps the three weights apart.
            assert all(
                declared_px - 1 <= width <= declared_px + 2 for width in tiers[tier]
            ), (tier, declared_px, sorted(set(tiers[tier])))
        assert max(tiers["cell"]) < min(tiers["fifth"])
        assert max(tiers["fifth"]) < min(tiers["border"])


    @pytest.mark.parametrize("axis", ["vertical", "horizontal"])
    def test_the_rules_are_pure_black_and_not_anti_aliased(
        self, axis: str, raw_page: Page, page: Image.Image
    ) -> None:
        """Every pixel the scanline crosses is #000 or the paper, never a grey.

        A rule softened to grey prints lighter than it measures, which is the
        complaint ADR-0037 answers (research §5: faint lines). The whole
        scanline is checked, not only the runs, so an anti-aliased *edge*
        beside a rule fails too.

        **CARD-356: on operators this claim is false as stated, and measured
        to be false for a reason other than the one this card was filed
        under.** The card read the ``[0, 89, 255]`` poppler returns as
        "poppler anti-aliases a vector rule". It does not: the 89 is
        ``round(255 * 0.35)``, the **declared tone of the cell lines** (ADR-0037
        R2: the fifths and the border are the interior's one ink, pure black;
        the cell lines are a lighter guide). Poppler, as this tree invokes it,
        returns no grey between a stroke's tone and the paper **across the
        width of an axis-aligned rule** --
        :meth:`test_a_rule_reads_as_the_tone_it_is_declared_at_and_no_other`
        measures that on a page of one rule, at whole- and half-pixel
        positions, along a scanline that crosses it. **That is the whole of
        the claim, and it is narrower than "no anti-aliasing"** (CARD-356
        review F-003, measured by the reviewer): a rule's *ends* carry greys
        (244 / 248 / 251 and the like at 72 / 100 / 150 / 600 DPI), a diagonal
        rule at 300 DPI carries 14 greys, and the tone is not always
        ``round(255 * tone)`` to the grey (tone 0.9 reads 229, not 230).
        This test's scanline is cut inside the grid between two rules, so it
        meets only axis-aligned rule widths; a claim about a rule's end or a
        slanted mark is not made here. So the two halves of the claim have different dispositions:

        * *"pure black"* -- **narrowed to what is declared**: the stream
          strokes every fifth line and the border at tone 0 and every cell
          line at 0.35, and each rule's darkest pixel on the raster is
          ``round(255 * its tone)``;
        * *"not anti-aliased"* -- **kept**, stated against the declaration:
          every grey on the scanline is one the stream declares or the paper,
          so an edge pixel poppler softened would be an unexplained grey and
          fail here (:func:`_unexplained_greys`, with its control below).

        Survivors by name for the declared tones:
        ``tests/test_book_grid_rules.py::TestBookGridRules_CellLinesAreLighterThanTheFifths``.
        """
        assert isinstance(raw_page, ContentStream), "an interior page here is operators"
        rules = _grid_rules(raw_page)[axis]
        tones = [rule.grey for rule in rules]
        assert [tones[i] for i in self.HEAVY_INDICES] == [0.0] * len(
            self.HEAVY_INDICES
        )
        assert {
            tone for i, tone in enumerate(tones) if i not in self.HEAVY_INDICES
        } == {CELL_RULE_GREY}

        scan = self._scan(page, axis)
        declared = {255, *(round(255 * tone) for tone in tones)}
        assert not _unexplained_greys(scan, declared), sorted(
            _unexplained_greys(scan, declared)
        )
        runs = _runs(scan < INK_LEVEL)
        assert len(runs) == MAX_SIZE + 1
        for index, run in enumerate(runs):
            assert {int(scan[pixel]) for pixel in run} == {
                round(255 * tones[index])
            }, f"rule {index}"

        colour = self._scan(page, axis, mode="RGB").reshape(-1, 3)
        ink = colour[(colour < INK_LEVEL).all(axis=1)]
        assert len(ink), "no ink on the scanline"
        assert {tuple(pixel) for pixel in np.unique(ink, axis=0).tolist()} == {
            (0, 0, 0),
            (round(255 * CELL_RULE_GREY),) * 3,
        }

    @pytest.mark.parametrize("tone", [0.0, 0.35, 0.6])
    @pytest.mark.parametrize("x_px", [100.0, 100.5, 100.25])
    def test_a_rule_reads_as_the_tone_it_is_declared_at_and_no_other(
        self, tone: float, x_px: float
    ) -> None:
        """The measurement behind the disposition above, and its control.

        One vertical rule on an otherwise blank page, stroked at ``tone`` and
        placed at a whole pixel and at two fractions of one, rasterised by the
        same poppler call the page reads go through. Every pixel of the
        scanline **across the rule** is the paper or ``round(255 * tone)``:
        no edge grey on the rule's width, at any of these phases. That is what
        makes the 89 on the real page a tone and not an artefact -- and what
        makes "no softened edge across a rule" assertable on operators at all.
        Its scope is exactly that: the rule's ends, a diagonal, and tones
        whose grey is not ``round(255 * tone)`` are outside it (the tones
        parametrised here are 0, 0.35 and 0.6, which are exact).

        The control is :func:`_unexplained_greys` itself: asked about the
        same scanline with the tone **left out** of the declared set, it
        names the tone as unexplained, so the check is shown able to fail.
        """
        stream = ContentStream(width_px=300, height_px=300, dpi=300)
        stream.stroke_grey(tone)
        stream.stroke_width(0.3)
        stream.line(x_px, 20, x_px, 280)
        scan = interior_images([stream])[0].convert("L")
        row = np.asarray(scan)[150]
        paper_and_tone = {255, round(255 * tone)}
        assert not _unexplained_greys(row, paper_and_tone)
        assert (row != 255).any(), "the rule drew nothing"
        if round(255 * tone) != 255:
            assert _unexplained_greys(row, {255}) == {round(255 * tone)}

    def test_the_stream_reader_reads_the_tone_and_weight_it_is_shown(self) -> None:
        """Control for :func:`_grid_rules`: it reports what a stream sets, per line.

        A known stream -- one vertical at 0.35 / 0.3 pt, one horizontal at
        0 / 1.3 pt -- must read back as exactly those two rules with those
        tones and widths, and the stroke state must carry from one line to the
        next as the operators do. A reader that ignored ``G`` or ``w`` would
        return the defaults for both.
        """
        stream = ContentStream(width_px=300, height_px=300, dpi=300)
        stream.stroke_grey(0.35)
        stream.stroke_width(0.3)
        stream.line(100, 20, 100, 280)
        stream.stroke_grey(0.0)
        stream.stroke_width(1.3)
        stream.line(20, 100, 280, 100)
        rules = _stroke_rules(stream)
        assert [(r.axis, r.width, r.grey) for r in rules] == [
            ("vertical", 0.3, 0.35),
            ("horizontal", 1.3, 0.0),
        ]

    @staticmethod
    def _scan(page: Image.Image, axis: str, mode: str = "L") -> np.ndarray:
        """One scanline across ``page``'s grid, cut to the grid's own extent.

        ``page_ink.drawing_of`` gives the grid box — by a different route: the
        longest unbroken run on every line of the whole page. The scanline
        runs from the first rule to a little past the last, so both borders
        are crossed whole and nothing outside the grid (a clue digit, the
        band) can reach it.
        """
        drawing = drawing_of(page)
        pixels = np.asarray(page.convert(mode))
        past_last_rule = round(drawing.cell)
        if axis == "vertical":
            row = drawing.grid_top + round(drawing.cell / 2)
            return pixels[row, drawing.grid_left : drawing.grid_right + past_last_rule]
        column = drawing.grid_left + round(drawing.cell / 2)
        return pixels[drawing.grid_top : drawing.grid_bottom + past_last_rule, column]

    def test_one_render_served_the_whole_class(
        self, request, page: Image.Image
    ) -> None:
        """CARD-218's control on this class's conversion.

        :data:`_FIFTH_RULE_RENDERS` grows by one entry per execution of the
        fixture, so exactly one entry is the statement that this 30x30 page
        was drawn once for the five tests that measure it. Put the scope back
        to ``function``, **and run this whole class**, and there are five, and
        this goes red.

        Both halves of that sentence are now asserted rather than assumed
        (fix round 1, F-002 and F-006). "Last in the class, so every test
        above has taken the fixture by now" was prose; the ordering guard
        reads it off this run's collected order, with ``siblings_excepted``
        off, because here the consumers *are* the classmates. And the
        denominator guard refuses a selection that left one of them out,
        where cycle 1 measured the function-scope mutant surviving a
        single-node-id run of this test.
        """
        _refuse_unless_every_consumer_is_collected(
            request, globals(), SHARED_FIFTH_RULE_PAGE
        )
        _refuse_unless_nothing_takes_it_later(
            request, SHARED_FIFTH_RULE_PAGE, siblings_excepted=False
        )
        assert _FIFTH_RULE_RENDERS == [self.PUZZLE], (
            "the 30x30 page was drawn "
            f"{len(_FIFTH_RULE_RENDERS)} times for this class, not once"
        )
        assert drawing_of(page).columns == MAX_SIZE, (
            "the shared page is not the 30x30 page this class measures"
        )


# --------------------------------------------------------------------------
# The band of a puzzle whose row carries no tier
# --------------------------------------------------------------------------


class TestBookPdf_UngradedPuzzlePrintsItsNumberAlone:
    """This card's documented decision for a tier nobody can read.

    ``band_identity`` prints "Puzzle 12" and stops, rather than printing the
    stored text as it is stored or inventing a fourth label. See its docstring
    for why; this pins it, on the page as well as in the function, so the
    decision cannot drift without a test saying so.
    """

    UNREADABLE = [None, "", "   ", "extreme", "Guess me", 7, ["hard"]]

    @pytest.mark.parametrize("stored", UNREADABLE)
    def test_no_tier_of_record_leaves_the_number_alone(self, stored: object) -> None:
        assert band_identity(12, stored) == "Puzzle 12"

    def test_the_page_of_an_ungraded_puzzle_says_only_its_number(self) -> None:
        puzzle = _puzzle(tier=None)
        raw = _raw_interior([puzzle])[puzzle_page_number([puzzle]) - 1]
        page = interior_images([raw])[0]
        assert _has_ink(_band_strip(page))
        assert isinstance(raw, ContentStream), "an interior page here is operators"
        # CARD-356: the band is read from the stream's text layer. It is
        # exactly "Puzzle 1" -- no separator, no tier, no raw stored text
        # -- which is the whole of the decision this class pins.
        assert [line.text for line in _band_zone(_text_of(raw))] == ["Puzzle 1"]

    @pytest.mark.parametrize("stored,label", sorted(TIER_LABELS.items()))
    def test_every_spelling_a_row_can_hold_reads_as_its_label(
        self, stored: str, label: str
    ) -> None:
        """Including ADR-0031/R3's retired ``"guess"``, which reads as Hard."""
        for spelling in (stored, stored.upper(), stored.capitalize()):
            assert band_identity(4, spelling) == f"Puzzle 4 · {label}"

    @pytest.mark.parametrize("number", [0, -1])
    def test_a_position_that_is_not_a_print_position_is_refused(
        self, number: int
    ) -> None:
        with pytest.raises(ValueError):
            band_identity(number, "easy")


# --------------------------------------------------------------------------
# EC(ADR-0037/R1) — the band, for every puzzle of every book
# --------------------------------------------------------------------------

#: Names a book's puzzles can carry: ASCII, non-ASCII in scripts the packaged
#: face covers (ADR-0006/DEC-027), punctuation that could be mistaken for the
#: band's own marks, a name that *is* a band line, an unnamed row, and one far
#: longer than any page is wide.
CORPUS_NAMES: tuple[str | None, ...] = (
    "Snowflake",
    "cat",
    "Iguanodon Skeleton",
    "Снежинка",
    "Ёлка — зимняя",
    "Puzzle 3 · Easy",
    "L'étoile d'hiver",
    "Χιονονιφάδα",
    "צפור",
    "A" * 200,
    "the quick brown fox jumps over the lazy dog, twice, and then again",
    None,
    "",
)

#: Every spelling of a tier a stored row is known to carry, plus text that is
#: no tier at all — the band has to be right for all of them.
CORPUS_TIERS: tuple[object, ...] = (
    "easy",
    "Easy",
    "EASY",
    "medium",
    "Medium",
    "hard",
    "Hard",
    "guess",
    "Guess",
    None,
    "",
    "extreme",
    17,
)

#: The corpus cannot silently shrink: no ``hypothesis`` in the dependency
#: baseline, so the floor is asserted inside the test (CLAUDE.md).
MIN_BOOKS = 24
MIN_PUZZLES = 60
MIN_POSITION = 4


def _check_band_corpus(names: Sequence[str | None]) -> None:
    """The EC's body, over a corpus whose names are drawn from ``names``.

    CARD-356: **stated in each page's own medium.** A bitmap page is compared
    pixel for pixel with the page COMP-007 draws for a payload with no name
    and the band written out here, exactly as before. A page written as
    operators is required to be, operator for operator, the page the
    generator draws for the **same book with no names at all** -- so the
    title is on no puzzle page, anywhere -- and the band zone's text layer
    (poppler's) must read this module's own :func:`expected_band` and nothing
    else. Both halves of ADR-0037/R1 are carried by those two readings, and
    neither reads the other's answer.

    **What the operators arm does and does not see (CARD-356 review F-001).**
    The equality compares the generator with *itself minus the names*, so it
    sees any mark that **depends on the name** (a title anywhere on the page,
    in any form) and nothing else: a stray mark that does not depend on the
    name -- a stray rule, a second folio -- is on both pages and passes. The
    text layer sees the wrong *words* in the band zone only. So on a converted
    interior this body does **not** carry a whole-page claim, and the answer
    and ungraded pages have no whole-page comparison at all (their bitmap
    comparisons were against a raster primitive that is no longer what the
    generator draws). An independent whole-page expectation for operators
    would mean re-composing the sheet furniture and the grid from
    ``book_sheet_vector`` here, which is a second implementation of the
    writer rather than a cheap reading, so it is **not built**.

    **Who else holds a name-independent stray mark -- MEASURED, not assumed**
    (CARD-356, in-process plants that add one mark to every content stream, run
    against each module alone beside an unplanted control in the same
    invocation; instruments in the card's review folder): on the *puzzle
    page* the writer's own module catches all three plants -- a stray vertical
    rule, a stray text run and a stray filled rectangle -- in, among others,
    ``tests/test_book_puzzle_page_vector.py::TestPropertyTest_PuzzlePage_EveryCoordinateComesFromTheLayout::test_every_mark_on_every_page_is_the_one_the_layout_demands``
    and
    ``tests/test_book_puzzle_page_vector.py::TestSheetFurniture_TheProductionPageCarriesTheFurniture::test_the_page_carries_all_four_pieces_of_furniture``
    (the rule and the text run are also caught by
    ``tests/test_book_puzzle_page_vector.py::TestPuzzlePageStream_TheBareWriterDrawsOnlyTheDrawingAndTheBand::test_the_page_shows_only_the_clue_digits_and_the_band``).
    ``tests/test_book_grid_rules.py`` catches only the stray *rule*, by
    ``tests/test_book_grid_rules.py::TestBookGridRules_FifthLinesOnBothAxes::test_the_stream_strokes_both_axes_at_the_fifth_weight``
    and
    ``tests/test_book_grid_rules.py::TestBookGridRules_RaggedLastBand::test_the_last_band_is_short_and_the_border_keeps_its_weight``,
    and neither the text run nor the rectangle. **Declared residue:** that
    covers the puzzle page only, and only the three marks planted -- an actual
    second folio was not planted. No module was measured for the answer page,
    the ungraded page, the table of contents or the guide, so for those a
    name-independent stray mark is not claimed to be held by anything.
    """
    random_source = random.Random(20260923)
    books = 0
    refused_books = 0
    puzzles_checked = 0
    names_seen: set[str | None] = set()
    labels_seen: set[str] = set()
    positions_seen: set[int] = set()

    for book_index in range(MIN_BOOKS + 4):
        count = random_source.randint(1, MIN_POSITION + 1)
        puzzles = []
        for position in range(1, count + 1):
            side = random_source.randint(MIN_SIZE, MIN_SIZE + 5)
            name = random_source.choice(names)
            tier = random_source.choice(CORPUS_TIERS)
            names_seen.add(name)
            puzzles.append(
                _puzzle(
                    columns=side,
                    # 14..19 rows, so that no two neighbours of a book ever
                    # share a page (FR-040, CARD-127) and every puzzle of this
                    # corpus keeps a page of its own — which is what lets the
                    # whole page be compared against a single puzzle's. A
                    # 3-deep column gutter makes each drawing 17..22 cells
                    # tall, so a pair would need 34 or more of the 33 that
                    # Book 1's 236.35 mm of usable height holds at 7.0 mm.
                    # The band on a two-up page is CARD-127's own corpus
                    # (tests/test_book_pdf_two_up.py).
                    rows=random_source.randint(MIN_SIZE + 4, MIN_SIZE + 9),
                    depth=3,
                    name=name,
                    tier=tier,
                    puzzle_id=f"b{book_index}-p{position}",
                )
            )

        # CARD-383: the expectation is DERIVED FROM THE MEDIUM, never listed.
        # While the answer page is a bitmap the raster page sets every name
        # and no book is refused; once it is operators the interior's
        # encoding sets only what ``encode_text`` accepts, and a book holding
        # a name it cannot set is refused, by name, before any page. The
        # refused book is then banded over what the interior CAN carry (the
        # names it refused are dropped by this test, not by the product), so
        # every floor below counts the same books in both media.
        vector_answers = page_medium(PageKind.ANSWER) is PageMedium.VECTOR
        refused = [
            puzzle
            for puzzle in puzzles
            if vector_answers and not _carried_by_the_interior(puzzle["puzzle_name"])
        ]
        if refused:
            with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
                _raw_interior(puzzles)
            # The first in PRINT order (this module's own reading of FR-041),
            # which is the one the generator reaches first.
            first = min(
                refused, key=lambda puzzle: print_plan(puzzles)[puzzles.index(puzzle)][0]
            )
            assert refusal.value.puzzle_id == first["id"], (
                f"book {book_index}: refused {refusal.value.puzzle_id!r}, "
                f"the first unsettable name is {first['id']!r}"
            )
            assert first["puzzle_name"] in str(refusal.value)
            refused_books += 1
            refused_ids = {puzzle["id"] for puzzle in refused}
            puzzles = [
                {**puzzle, "puzzle_name": None} if puzzle["id"] in refused_ids else puzzle
                for puzzle in puzzles
            ]
        pages = _raw_interior(puzzles)
        plan = print_plan(puzzles)
        nameless = _raw_interior([{**puzzle, "puzzle_name": None} for puzzle in puzzles])
        for index, puzzle in enumerate(puzzles):
            # Where this row lands once the book is grouped by level, and the
            # number it carries there (CARD-128) — this module's own reading
            # of the print order, not the generator's.
            number, page_number = plan[index]
            identity = expected_band(number, puzzle["difficulty_tier"])
            page = pages[page_number - 1]
            where = (
                f"book {book_index}, puzzle {number} "
                f"(name {puzzle['puzzle_name']!r}, stored tier "
                f"{puzzle['difficulty_tier']!r}) does not print {identity!r}"
            )
            assert isinstance(page, ContentStream), "an interior page here is operators"
            assert _same_page(page, nameless[page_number - 1]), where
            band = [line.text for line in _band_zone(_text_of(page))]
            assert band == [identity], f"{where}: the band reads {band!r}"
            puzzles_checked += 1
            positions_seen.add(number)
            if "·" in identity:
                labels_seen.add(identity.rsplit(" · ", 1)[1])
        books += 1

    assert books >= MIN_BOOKS, books
    assert puzzles_checked >= MIN_PUZZLES, puzzles_checked
    assert labels_seen == {"Easy", "Medium", "Hard"}, labels_seen
    assert max(positions_seen) >= MIN_POSITION, positions_seen
    assert len(names_seen) >= 8, names_seen
    assert any(name and not name.isascii() for name in names_seen), names_seen
    assert any(name and len(name) > 100 for name in names_seen), names_seen
    # The refusal arm cannot be empty when the medium and the names say it
    # must fire, and cannot fire when either says it must not (CARD-383,
    # ADR-0039/R1): the matched control, which draws only carried names, must
    # see no refusal in either medium.
    must_refuse = page_medium(PageKind.ANSWER) is PageMedium.VECTOR and any(
        not _carried_by_the_interior(name) for name in names
    )
    if must_refuse:
        assert refused_books >= 1, refused_books
    else:
        assert refused_books == 0, refused_books


def test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle() -> None:
    """EC(ADR-0037/R1) — every puzzle of every book, whatever its name and tier.

    A seeded corpus of books: each one a handful of puzzles with names drawn
    from :data:`CORPUS_NAMES` and stored tiers from :data:`CORPUS_TIERS`, at
    extents across CON-011's range, so a puzzle's print position, its name and
    its tier vary independently. For every puzzle of every book the rendered
    puzzle page is required to be the page the generator draws with no name
    and the band this module composed from ADR-0037's wording and its own tier
    table (see :func:`_check_band_corpus` for how each medium is read).

    Since CARD-128 these are **grouped and divided** books: the tiers are
    drawn independently of the position, so almost every book of the corpus is
    of several levels, prints in an order that is not the one it was handed in
    and carries a divider page opening each of its levels. ``N`` is therefore
    the puzzle's place in the *print* order and the page is the one the
    grouping put it on — both taken from :func:`print_plan`, this module's own
    reading of FR-041 — so a band numbered by submission order, or by page,
    fails here.

    **CARD-383: GREEN BOTH WAYS, with the expectation derived from the
    medium.** :data:`CORPUS_NAMES` carries Cyrillic, Greek and Hebrew titles,
    which the interior's ``cp1252`` encoding cannot show. While the answer page
    is a bitmap (today) every name is set and every book is banded. Once it is
    written as operators (the five-kind probe, and the tree after CARD-322) the
    generator REFUSES a book holding such a name, by name and before any page
    (``errors.UnsettablePuzzleTitle``); this body then asserts that refusal for
    the first name the interior cannot carry and bands the rest of the book.
    Which names are refused is asked of ``encode_text`` through
    :func:`_carried_by_the_interior`, never listed. Its matched control, the
    next test, is untouched.
    """
    _check_band_corpus(CORPUS_NAMES)


def _carried_by_the_interior(name: str | None) -> bool:
    """Whether the interior's own encoder will set ``name`` (default-DENY).

    Asked of ``encode_text``, the authority the writer itself calls, and
    answered only by it: a name is carried when it encodes and refused when
    it raises :class:`UnrepresentableText`; any other outcome is an error, not
    a quiet exclusion (ADR-0039/R2).
    """
    if not name:
        return True
    try:
        encode_text(name)
    except UnrepresentableText:
        return False
    return True


def test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryNameTheInteriorCanCarry() -> None:
    """EC(ADR-0037/R1), over the names the interior's encoding can set.

    The matched control for the red above: the same seeded corpus, the same
    body, restricted to the names ``encode_text`` accepts. Green here and red
    there is exactly the statement that the only thing the full corpus trips
    on is the encoding refusal (CARD-322's), and the corpus floors are
    asserted inside the body so the restriction cannot silently empty it.
    """
    carried = tuple(name for name in CORPUS_NAMES if _carried_by_the_interior(name))
    assert len(carried) >= 8, carried
    assert "Snowflake" in carried and "L'étoile d'hiver" in carried
    _check_band_corpus(carried)


# --------------------------------------------------------------------------
# CARD-383 -- the vector interior refuses, by name and before any page, a
# title its encoding cannot set
# --------------------------------------------------------------------------

GREEK = "Χιονονιφάδα"


def _lift_answer(monkeypatch) -> None:
    """The answer page is operators in the tree (ADR-0042); say so."""
    assert page_medium(PageKind.ANSWER) is PageMedium.VECTOR


def _assembled(book: Book | None = None) -> BookPDFGenerator:
    """A generator that HAS the downstream writers, so a lifted kind is drawn
    and not refused for want of a writer."""
    return BookPDFGenerator(
        book if book is not None else _book(),
        pages=book_interior_vector.DOWNSTREAM_WRITERS,
    )


def _watch_the_write(monkeypatch, generator: BookPDFGenerator) -> list[int]:
    """Count the calls to ``_write_pdf`` -- the first byte of a file."""
    calls: list[int] = []
    original = generator._write_pdf

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(generator, "_write_pdf", counted)
    return calls


#: The doors into the walk that DRAW pages; all of them refuse.
#: ``interior_stream`` is the plan the Finalise counts read and is not one: it
#: decides and draws nothing until its pages are asked for.
_DRAWING_DOORS = (
    "export_interior",
    "interior_pages",
    "interior",
    "export_book",
)


def _through(generator: BookPDFGenerator, door: str, puzzles: list[dict]):
    if door == "export_book":
        return generator.export_book(puzzles, "A title")
    return getattr(generator, door)(puzzles)


class TestBookPdf_TheInteriorRefusesATitleItsEncodingCannotSet:
    """CARD-383 AC-1..AC-4 and AC-8: the refusal, its gate, and its limits."""

    @pytest.mark.parametrize("door", _DRAWING_DOORS)
    def test_a_greek_name_is_refused_by_name_before_any_page(
        self, monkeypatch, door
    ) -> None:
        _lift_answer(monkeypatch)
        generator = _assembled()
        written = _watch_the_write(monkeypatch, generator)
        book = [_puzzle(name=GREEK, puzzle_id="greek-1")]

        with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
            _through(generator, door, book)

        error = refusal.value
        text = str(error)
        assert not isinstance(error, RuntimeError)
        assert error.puzzle_id == "greek-1"
        assert error.puzzle_number == 1
        assert error.title == GREEK
        assert "Χ" in error.characters
        assert GREEK in text and "Puzzle 1" in text
        assert "greek-1" not in text  # a database key is not for the owner
        assert "U+03A7" in text
        assert "Arrangement" in text and "Rename" in text
        assert "Latin letters" in text and "accents" in text
        # Nothing was written: the file never got a first byte.
        assert written == []

    def test_the_refusal_is_a_domain_error_with_the_invalid_input_ancestry(
        self,
    ) -> None:
        assert issubclass(errors.UnsettablePuzzleTitle, errors.InvalidPuzzleName)
        assert issubclass(errors.UnsettablePuzzleTitle, errors.NonogramError)
        assert not issubclass(errors.UnsettablePuzzleTitle, errors.UnletterableTitle)

    def test_the_control_a_latin_name_exports_under_the_same_lift(
        self, monkeypatch
    ) -> None:
        _lift_answer(monkeypatch)
        generator = _assembled()
        written = _watch_the_write(monkeypatch, generator)
        data = generator.export_interior(
            [_puzzle(name="L'étoile d'hiver", puzzle_id="latin-1")]
        )
        assert data.getvalue().startswith(b"%PDF")
        assert written == [1]

    def test_a_deleted_pre_check_is_what_the_refusal_test_is_red_without(
        self, monkeypatch
    ) -> None:
        # AC-4's plant, run in-process: with the check removed, the same
        # book is refused by the WALK instead -- as a RuntimeError that
        # re-types the error and names no character -- so the typed refusal
        # above reds. ``must_red`` is asserted non-empty before it runs.
        from nonogram.admin import book_pdf_generator as module

        must_red = [
            name for name in ("_refuse_unsettable_titles",) if hasattr(module, name)
        ]
        assert must_red, "the module has no pre-check to delete"
        _lift_answer(monkeypatch)
        for name in must_red:
            monkeypatch.setattr(module, name, lambda *a, **k: None)
        with pytest.raises(RuntimeError) as walk:
            _assembled().export_interior([_puzzle(name=GREEK, puzzle_id="g")])
        assert not isinstance(walk.value, errors.NonogramError)

    def test_the_first_unsettable_puzzle_in_print_order_is_the_one_named(
        self, monkeypatch
    ) -> None:
        _lift_answer(monkeypatch)
        book = [
            _puzzle(name="Snowflake", puzzle_id="a"),
            _puzzle(name="Снежинка", puzzle_id="b"),
            _puzzle(name="פתית", puzzle_id="c"),
        ]
        with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
            _assembled().export_interior(book)
        assert refusal.value.puzzle_id == "b"
        assert refusal.value.puzzle_number == 2
        assert "Снежинка" in str(refusal.value)
        assert "פתית" not in str(refusal.value)

    def test_the_first_unsettable_puzzle_is_by_print_order_not_creation_or_id_order(
        self, monkeypatch
    ) -> None:
        # Mixed tiers: print order is easy, medium, hard, so the easy Greek
        # puzzle is Puzzle 1 although it was created third and sorts last by id.
        _lift_answer(monkeypatch)
        book = [
            _puzzle(name="Latin hard", puzzle_id="m1", tier="hard"),
            _puzzle(name="Μεσαίο", puzzle_id="a2", tier="medium"),
            _puzzle(name="Εύκολο", puzzle_id="z3", tier="easy"),
            _puzzle(name="Latin easy", puzzle_id="b4", tier="easy"),
        ]
        with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
            _assembled().export_interior(book)
        assert refusal.value.puzzle_id == "z3"
        assert refusal.value.puzzle_number == 1
        assert "Εύκολο" in str(refusal.value) and "Μεσαίο" not in str(refusal.value)

    def test_a_lifted_book_with_no_puzzles_is_not_refused(self, monkeypatch) -> None:
        _lift_answer(monkeypatch)
        generator = _assembled()
        generator.interior_stream([])
        from nonogram.admin import book_pdf_generator as module

        module._refuse_unsettable_titles(())  # nothing to refuse, nothing raised
        assert generator.export_interior([]).getvalue().startswith(b"%PDF")

    def test_a_greek_custom_title_on_a_latin_named_puzzle_is_refused(
        self, monkeypatch
    ) -> None:
        _lift_answer(monkeypatch)
        book = _book()
        book.puzzle_titles = {"p7": GREEK}
        with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
            _assembled(book).export_interior(
                [_puzzle(name="Snowflake", puzzle_id="p7")]
            )
        # The printed string decides, and the string shown is the printed one.
        assert refusal.value.title == GREEK
        assert GREEK in str(refusal.value)
        assert "Snowflake" not in refusal.value.characters

    def test_a_latin_custom_title_on_a_greek_named_puzzle_is_not_refused(
        self, monkeypatch
    ) -> None:
        _lift_answer(monkeypatch)
        book = _book()
        book.puzzle_titles = {"p7": "Winter Star"}
        data = _assembled(book).export_interior([_puzzle(name=GREEK, puzzle_id="p7")])
        assert data.getvalue().startswith(b"%PDF")

    @pytest.mark.parametrize(
        ("title", "refused"),
        [
            pytest.param("Café – 100 % €", False, id="encodable-punctuation-and-euro"),
            pytest.param("Snow\u2014flake", False, id="em-dash"),
            pytest.param("caf\u00e9", False, id="precomposed-accent"),
            pytest.param("cafe\u0301", True, id="combining-mark"),
            pytest.param("Snow \u2744", True, id="snowflake-symbol"),
            pytest.param("Snow \U0001F9CA", True, id="emoji"),
            pytest.param("soft\u00adhyphen", True, id="soft-hyphen-winansi-divergence"),
            pytest.param("東京", True, id="cjk"),
        ],
    )
    def test_the_title_the_encoder_refuses_is_the_title_the_book_refuses(
        self, monkeypatch, title, refused
    ) -> None:
        # The matched pair of every row is ``encode_text`` itself, the
        # authority: the book is refused exactly when it raises.
        assert _carried_by_the_interior(title) is (not refused)
        _lift_answer(monkeypatch)
        book = [_puzzle(name=title, puzzle_id="edge")]
        if refused:
            with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
                _assembled().export_interior(book)
            for character in refusal.value.characters:
                assert not _carried_by_the_interior(character)
        else:
            assert _assembled().export_interior(book).getvalue().startswith(b"%PDF")

    @pytest.mark.parametrize("name", ["", "   ", None])
    def test_no_title_at_all_is_not_a_refusal(self, monkeypatch, name) -> None:
        _lift_answer(monkeypatch)
        data = _assembled().export_interior([_puzzle(name=name, puzzle_id="blank")])
        assert data.getvalue().startswith(b"%PDF")

    def test_a_very_long_title_is_shortened_in_the_message_and_not_in_the_fact(
        self, monkeypatch
    ) -> None:
        _lift_answer(monkeypatch)
        long_title = "Snowflake " * 30 + GREEK
        with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
            _assembled().export_interior([_puzzle(name=long_title, puzzle_id="long")])
        assert refusal.value.title == long_title.strip()
        assert len(str(refusal.value)) < 700

    def test_the_quoted_title_is_cut_on_a_character_not_a_byte(self, monkeypatch) -> None:
        _lift_answer(monkeypatch)
        # A 2-byte UTF-8 letter exactly at the cut (index 59), then Greek.
        title = "A" * 59 + "é" + "B" * 10 + GREEK
        with pytest.raises(errors.UnsettablePuzzleTitle) as refusal:
            _assembled().export_interior([_puzzle(name=title, puzzle_id="cut")])
        text = str(refusal.value)
        assert "\ufffd" not in text
        assert "A" * 59 + "é..." in text

    def test_a_caller_that_only_plans_the_interior_does_not_start_raising(
        self, monkeypatch
    ) -> None:
        # AC-8. The Finalise counts read the plan and draw nothing; a book the
        # export will refuse is still a book with a page count.
        from nonogram.admin.app import _interior_counts

        _lift_answer(monkeypatch)
        book = _book()
        greek = [_puzzle(name=GREEK, puzzle_id="g")]
        latin = [_puzzle(name="Snowflake", puzzle_id="g")]
        counts = _interior_counts(book, greek)
        control = _interior_counts(book, latin)
        assert counts is not None and control is not None
        assert counts.page_count == control.page_count
        assert counts.answer_page_count == control.answer_page_count
        plan = _assembled(book).interior_stream(greek)
        assert plan.page_count == control.page_count
        # The plan seam itself never drew a title either.
        _assembled(book).section_plan(greek)
        # ... and the doors that draw, on the very same book, refuse.
        with pytest.raises(errors.UnsettablePuzzleTitle):
            _assembled(book).export_interior(greek)


# --------------------------------------------------------------------------
# CARD-170 — the band prints once, read from the exported PDF
# --------------------------------------------------------------------------
#
# The wave-32 goal-check recorded "Puzzle 5 · Hard" drawn twice during an
# export. These tests settle what the *printed* file holds. Every page they
# check is decoded from the bytes ``export_book`` wrote (``pdf_pages``); no
# page is obtained from ``_blank_page``, ``render_pages`` or
# ``interior_pages`` (guardrail G-6).
#
# A band is found on a decoded page without OCR by cutting the page into
# lines of ink and comparing each line with the band text set **once** by
# this module, in the packaged DejaVu Sans, at every type size in
# :data:`LINE_SIZES_PX`. A line is "one copy of the text at size s" when its
# ink box is that setting's box and its ink is that setting's ink, both up to
# the JPEG tolerances below.
#
# What the pixel tests can see follows from how :func:`_lines` cuts a page:
# every run of page rows holding any ink is one group, split sideways only at
# gaps at least as wide as the group is tall. So a second copy is found only
# on rows with no other ink within about a line's height sideways of it — the
# band strip, the gap between the two slots, the top and bottom margins —
# where it makes a line of its own (the text is found twice) or, touching the
# band, widens the band's line (it matches nothing). A copy beside the
# drawing (in a side margin, rows the ~1158 px grid also occupies) or over
# other ink (clues, grid, a caption) merges into that ink's line and is not
# seen; such a copy is caught only by the recorder (AC-3,
# TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage). A second draw at
# exactly the same spot is caught today only incidentally — the second
# antialiased pass darkens the edge pixels past the ink mismatch limit — so
# the pixel tests do not guarantee it; the recorder does.
#
# Measured with a second ``_set_band`` draw on the two-up pages (see the
# card's Worktree notes for the full list): top margin (y-110), slot gap
# (y+1450), bottom margin (lower slot, y+1280), band strip beside the band
# (x-900) and touching it (x+40) each failed found-once and upper-first (the
# last two also the band-strip test); side margins beside the drawing
# (x∓900, y+600), over the column clues (y+300) and inside the grid (y+700)
# left every pixel test green and failed only the recorder's per-page test.

#: The book of this section: two Easy, two Medium and one Hard puzzle, all
#: 10x10 with 3-deep clues, so each same-tier neighbour pair fits one page at
#: a shared cell (FR-040) and the Hard puzzle — the last, and alone in its
#: tier — prints alone through COMP-007's ``render_pages``.
ONCE_TIERS = ("easy", "easy", "medium", "medium", "hard")

#: This module's reading of that book's interior (FR-041, FR-040, FR-042,
#: CARD-198, CARD-201, CARD-200, CARD-206): 1 the blank title / copyright
#: page (CARD-206); 2-3 the guide (CARD-201's 2-page tutorial,
#: up from one page before that card); 4 the table of contents (CARD-200:
#: this 5-puzzle book's TOC always fits one page on Book 1's own trim); 5
#: Easy divider; 6 Puzzles 1-2 two-up; 7 Medium divider; 8 Puzzles 3-4
#: two-up; 9 Hard divider; 10 Puzzle 5 alone; 11 SOLUTIONS divider; 12-14
#: CARD-202's own packed answer section — puzzles 1-2 (both Easy, both
#: qualify) share packed page 12, 3-4 (both Medium, both qualify) share
#: packed page 13, and 5 (Hard, alone in its level, still qualifies) packs
#: alone onto page 14; 15 the closing thank-you page (owner, 2026-11-10).
#: ``print_plan`` above models only books that never pair, so the pages are
#: written out here instead.
ONCE_PAGE_COUNT = 15
ONCE_BAND_PAGES = {1: 6, 2: 6, 3: 8, 4: 8, 5: 10}
HARD_ALONE_PAGE = 10
TWO_UP_PAGE = 6

ANSWER_PAGE_OF = {1: 12, 2: 12, 3: 13, 4: 13, 5: 14}
HARD_ANSWER_PAGE = ANSWER_PAGE_OF[5]

#: The band's type size: 5 mm at 300 DPI (COMP-007's header size), in pixels.
BAND_FONT_PX = round(5.0 * PX_PER_MM)

#: Every type size a line is compared at — far wider than any size the book
#: sets lettering in, so a band set at another size (an answer caption's, say)
#: is still found.
LINE_SIZES_PX = range(10, 121)

#: JPEG tolerances, from what was measured on this section's export: every one
#: of the five decoded bands' ink boxes equalled the box of the text set once
#: at :data:`BAND_FONT_PX` exactly (0 px in both axes), with 0.4-0.7 % of the
#: reference's ink pixels differing; the same band compared with the line of a
#: different puzzle number (same box) differed by 8.8-10.6 %. The two limits
#: sit between those measurements.
#:
#: **CARD-201 note (widened, not loosened blindly — investigated first).**
#: A CARD-202 *packed* answer page splits its usable width into two tiles
#: with a gap between them; when that width does not divide evenly, one
#: tile is a pixel narrower than the other. Each tile's caption is drawn
#: centred on its own ``(drawing_left + drawing_right) / 2`` with
#: ``anchor="mm"`` (``_draw_solved_slot``, unedited by CARD-201 or this
#: merge), so the tile on the "short" side of that 1-pixel split lands its
#: caption at a sub-pixel x-offset the other tile's does not — measured
#: directly (both slots of the same packed page, in-memory, before any
#: JPEG encoding): one slot's caption matches its own synthetic reference
#: at 0 % mismatch, the other at ~2.4-2.5 %, and this is *inherent to the
#: tile split*, not something either card's drawing code got wrong (the
#: same ~2.5 %-vs-0 % split appears identically whether a given puzzle's
#: tile is the left or the right one — it tracks the tile position, not
#: the puzzle). **Which tile ends up on the "short" side flips with page
#: parity** (the gutter/outside margins swap sides, ADR-0036), and CARD-201
#: growing the guide by a page flips every later page's parity — so a
#: packed answer that always happened to land on the "lucky" (0 %) side
#: before CARD-201 can land on the "unlucky" (~2.5 %) side after, with no
#: change to a single pixel of drawing code. Added to this file's own
#: already-measured JPEG noise (0.4-0.7 %), the "unlucky" slot measured
#: 3.19-3.21 % after a real PDF export — just over the original 3 % limit,
#: calibrated before CARD-202's packed pages (two asymmetric tiles) existed
#: at all. Widened to 4 %, which still sits well clear of the 8.8-10.6 %
#: a genuinely different puzzle's caption measures (the comparison this
#: limit must keep failing), and comfortably covers the worst case actually
#: measured (3.21 %) with headroom for the same effect on a 4-up page's
#: four asymmetric tiles.
BOX_TOLERANCE_PX = 2
INK_MISMATCH_LIMIT = 0.04

#: The packaged face the book's lettering is set in, addressed as package data
#: (written out here, not imported from ``export.pdf``).
_FONT_PACKAGE = "nonogram.export"
_FONT_RESOURCE = "fonts/DejaVuSans.ttf"


def _once_book() -> list[dict]:
    # Explicit 10x10 (not this module's own non-qualifying default, see
    # ``_DEFAULT_SIZE``): this section's whole premise is that same-tier
    # neighbours pair on the puzzle page (FR-040), which only a small shape
    # does, and CARD-202's own math makes "small enough to pair" and "small
    # enough to qualify for packing" the same condition at this profile (a
    # pair's combined-height budget is tighter than one packed tile's) — so
    # this book's answer section packs too, and the ONCE_* constants below
    # are this card's own recomputation of that, not CARD-198's any more.
    return [
        _puzzle(columns=10, rows=10, tier=tier, puzzle_id=f"once-{index}")
        for index, tier in enumerate(ONCE_TIERS, start=1)
    ]


def _once_bands() -> dict[int, str]:
    """``{puzzle number: band line}`` for the book, from ADR-0037's wording."""
    return {
        number: expected_band(number, tier)
        for number, tier in enumerate(ONCE_TIERS, start=1)
    }


@lru_cache(maxsize=None)
def _font_bytes() -> bytes:
    return resources.files(_FONT_PACKAGE).joinpath(_FONT_RESOURCE).read_bytes()


@lru_cache(maxsize=None)
def _set_once(text: str, size: int) -> np.ndarray:
    """The ink of ``text`` set once at ``size`` px, cropped to its ink box."""
    font = ImageFont.truetype(BytesIO(_font_bytes()), size=size)
    canvas = Image.new("L", (int(font.getlength(text)) + 2 * size, 3 * size), 255)
    ImageDraw.Draw(canvas).text((size, canvas.height // 2), text, font=font, fill=0, anchor="lm")
    return _cropped(np.asarray(canvas) < INK_LEVEL)


def _cropped(ink: np.ndarray) -> np.ndarray:
    rows = np.flatnonzero(ink.any(axis=1))
    columns = np.flatnonzero(ink.any(axis=0))
    return ink[rows[0] : rows[-1] + 1, columns[0] : columns[-1] + 1]


def _mismatch(found: np.ndarray, reference: np.ndarray) -> float:
    """The share of ``reference``'s ink that ``found`` disagrees with.

    Best over shifts of up to :data:`BOX_TOLERANCE_PX` either way, so a box
    one pixel off does not count every pixel as a disagreement.
    """
    pad = BOX_TOLERANCE_PX
    height = max(found.shape[0], reference.shape[0]) + 2 * pad
    width = max(found.shape[1], reference.shape[1]) + 2 * pad
    here = np.zeros((height, width), dtype=bool)
    here[pad : pad + found.shape[0], pad : pad + found.shape[1]] = found
    best = float("inf")
    for dy in range(-pad, pad + 1):
        for dx in range(-pad, pad + 1):
            there = np.zeros_like(here)
            there[
                pad + dy : pad + dy + reference.shape[0],
                pad + dx : pad + dx + reference.shape[1],
            ] = reference
            best = min(best, float((here ^ there).sum()) / float(reference.sum()))
    return best


def _one_copy_at(ink: np.ndarray, text: str) -> int | None:
    """The type size at which ``ink`` is one copy of ``text``, else ``None``."""
    for size in LINE_SIZES_PX:
        reference = _set_once(text, size)
        if (
            abs(ink.shape[0] - reference.shape[0]) <= BOX_TOLERANCE_PX
            and abs(ink.shape[1] - reference.shape[1]) <= BOX_TOLERANCE_PX
            and _mismatch(ink, reference) <= INK_MISMATCH_LIMIT
        ):
            return size
    return None


#: A row whose longest run of ink is longer than this is a ruled line, not
#: lettering. Measured on this section's export: the drawing's top frame
#: rule's rows run 1153 px; the longest run in any of the five band lines is
#: 30-33 px.
RULE_RUN_PX = 2 * BAND_FONT_PX


def _longest_runs(ink: np.ndarray) -> np.ndarray:
    """Each row's longest run of consecutive ink pixels."""
    padded = np.pad(ink.astype(np.int8), ((0, 0), (1, 1)))
    longest = np.zeros(ink.shape[0], dtype=int)
    for row, edges in enumerate(np.diff(padded, axis=1)):
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
        if starts.size:
            longest[row] = int((ends - starts).max())
    return longest


def _rule_rows(ink: np.ndarray) -> np.ndarray:
    """The rows of ``ink`` that hold a ruled line."""
    return np.flatnonzero(_longest_runs(ink) > RULE_RUN_PX)


def _spans(mask: np.ndarray, gap: int) -> list[tuple[int, int]]:
    """Runs of ``True`` in ``mask``, merging runs separated by ``gap`` or fewer."""
    spans: list[tuple[int, int]] = []
    for index in np.flatnonzero(mask):
        if spans and index - spans[-1][1] <= gap:
            spans[-1] = (spans[-1][0], int(index))
        else:
            spans.append((int(index), int(index)))
    return spans


class _Line(NamedTuple):
    top: int
    left: int
    ink: np.ndarray


def _lines(page: Image.Image) -> Iterator[_Line]:
    """The page's lines of ink: rows of ink, split where a gap is a line tall.

    A word space is far narrower than the line is tall, so a band stays one
    line; the side-by-side answer captions of a level's answer page do not.
    A drawing, its clues inside its frame, is one line the grid's height, so
    nothing on rows beside it is split off from it.
    """
    ink = np.asarray(page.convert("L")) < INK_LEVEL
    for top, bottom in _spans(ink.any(axis=1), 1):
        strip = ink[top : bottom + 1]
        height = bottom - top + 1
        for left, right in _spans(strip.any(axis=0), height):
            piece = strip[:, left : right + 1]
            rows = np.flatnonzero(piece.any(axis=1))
            yield _Line(top + int(rows[0]), left, piece[rows[0] : rows[-1] + 1])


def _lines_ink_of_band(page: Image.Image) -> np.ndarray:
    """The ink of the one line in a bitmap page's band strip, rules aside."""
    strip = np.asarray(_band_strip(page).convert("L")) < INK_LEVEL
    strip[_rule_rows(strip)] = False
    top, bottom = _spans(strip.any(axis=1), 1)[0]
    return _cropped(strip[top : bottom + 1])


class _Found(NamedTuple):
    page: int
    text: str
    size: int
    top: int


# --------------------------------------------------------------------------
# CARD-356 -- reading a line of type in the medium it was written in
#
# The glyph-template search above (``_set_once``/``_mismatch``/``_one_copy_at``)
# sets a string with Pillow and asks whether a line of ink on the page is that
# setting. It is a **raster instrument**: its template is the raster path's own
# rasteriser's rendering of the face, and it is only as good as the page being
# drawn by that same rasteriser. Measured on this module's own book: the same
# band set as operators and rasterised by poppler differs from the template by
# 11-15 % of its ink against a 4 % limit (``INK_MISMATCH_LIMIT``, which this
# card does not move), while the box agrees to within two pixels. Nothing was
# wrong with the page; the template had no subject there.
#
# A page written as operators has an independent reading that is exact
# instead of approximate: poppler's text layer (``pdftotext -bbox``), an
# engine that did not write the file, which reports each word the embedded
# face's ``/Widths`` and ``/Encoding`` actually set and the box it sits in.
# The two readings are kept apart by the page they read, never mixed: a bitmap
# is searched by template, a stream by its words.
# --------------------------------------------------------------------------


class _TextLine(NamedTuple):
    """One line of type from a text layer, in the units the pixel search uses."""

    top: int
    left: int
    text: str
    #: The type size in device pixels, recovered from the word box's height
    #: and the face's own ascent and descent, so it is comparable with
    #: :data:`BAND_FONT_PX` and with the raster search's ``size``.
    size: int


def _lines_of_words(words: Sequence[Word]) -> list[_TextLine]:
    """Poppler's words, joined into lines of type.

    Words on one baseline are one line unless the gap between two of them is
    at least as wide as the words are tall -- the same rule :func:`_lines`
    cuts a bitmap by, so two answer captions side by side on a packed page are
    two lines and a band's word spaces are not breaks.
    """
    # Through the module, not a name imported from it: ``interior_face_metrics``
    # is an ``@lru_cache``, and this module's retention control grants that
    # allowance to exactly the two caches it names.
    metrics = book_vector.interior_face_metrics()
    em_height = (metrics.ascent - metrics.descent) / 1000.0
    px_per_pt = DPI / 72.0
    ordered = sorted(words, key=lambda word: (round(word.top, 1), word.left))
    lines: list[list[Word]] = []
    for word in ordered:
        if lines:
            last = lines[-1][-1]
            same_row = abs(word.top - last.top) < 0.5
            gap = word.left - last.right
            if same_row and gap < (last.bottom - last.top):
                lines[-1].append(word)
                continue
        lines.append([word])
    found = []
    for line in lines:
        height_pt = line[0].bottom - line[0].top
        found.append(
            _TextLine(
                top=round(line[0].top * px_per_pt),
                left=round(line[0].left * px_per_pt),
                text=" ".join(word.text for word in line),
                size=round(height_pt / em_height * px_per_pt),
            )
        )
    return _joined_headers(found, metrics.ascent / 1000.0)


#: The puzzle header's tier word, as CARD-207's header sets it: in capitals.
_HEADER_TIER_WORDS = ("EASY", "MEDIUM", "HARD")


def _joined_headers(lines: list[_TextLine], ascent_em: float) -> list[_TextLine]:
    """``lines`` with each puzzle header read back as one band line.

    Since CARD-207 a puzzle page's header is two pieces on one baseline:
    ``Puzzle N`` flush left at the band's size and the tier in capitals flush
    right, smaller. A ``Puzzle N`` line and a tier word to its right whose
    baselines (top plus the face's ascent at each line's own size) agree to
    :data:`BOX_TOLERANCE_PX` are one header, read as ``"Puzzle N · Tier"`` at
    the number's size and position; every other line is left as it is, so a
    stray tier word or a second number still reads as a line of its own.
    """

    def baseline(line: _TextLine) -> float:
        return line.top + ascent_em * line.size

    paired: dict[int, int] = {}
    for index, line in enumerate(lines):
        if not re.fullmatch(r"Puzzle \d+", line.text):
            continue
        for other, word in enumerate(lines):
            if (
                other not in paired.values()
                and word.text in _HEADER_TIER_WORDS
                and word.left > line.left
                and abs(baseline(word) - baseline(line)) <= BOX_TOLERANCE_PX
            ):
                paired[index] = other
                break
    joined = []
    for index, line in enumerate(lines):
        if index in paired.values():
            continue
        if index in paired:
            tier = lines[paired[index]].text.capitalize()
            line = line._replace(text=f"{line.text} \u00b7 {tier}")
        joined.append(line)
    return joined


def _words_of(page: ContentStream) -> list[Word]:
    """The words poppler finds on one stream written out as a one-page PDF."""
    data = write_vector_pdf([page], 1).getvalue()
    with tempfile.TemporaryDirectory(prefix="band-words-") as directory:
        return pdf_vector.word_boxes(data, 1, out_dir=Path(directory))


def _text_of(page: ContentStream) -> list[_TextLine]:
    """Every line of type on a page written as operators."""
    return _lines_of_words(_words_of(page))


def _band_zone(lines: Sequence[_TextLine]) -> list[_TextLine]:
    """The lines whose top is inside the 12 mm band strip below the top margin."""
    top = round(TOP_MM * PX_PER_MM)
    return [
        line for line in lines if top <= line.top < top + round(BAND_MM * PX_PER_MM)
    ]


def _solution_header(lines: Sequence[_TextLine]) -> list[str]:
    """An answer page's solution header, left to right: ``["7", "Snowflake"]``.

    The approved solutions mockup sets the number alone and the picture's
    name beside it (the tier is the dots, which are not text) in the answer's
    own band, which sits :data:`RUNNING_HEAD_MM` below a puzzle's.
    """
    top = round((TOP_MM + RUNNING_HEAD_MM) * PX_PER_MM)
    zone = [
        line for line in lines if top <= line.top < top + round(BAND_MM * PX_PER_MM)
    ]
    return [line.text for line in sorted(zone, key=lambda line: line.left)]


def _running_head(lines: Sequence[_TextLine]) -> list[str]:
    """The answer page's running head, left to right, from the strip above its band."""
    top = round(TOP_MM * PX_PER_MM)
    zone = [
        line for line in lines if top <= line.top < top + round(RUNNING_HEAD_MM * PX_PER_MM)
    ]
    return [line.text for line in sorted(zone, key=lambda line: line.left)]


def _running_head_section(stored_tier: object) -> str:
    """The running head's section words for a tier: "SOLUTIONS · EASY"."""
    _, _, tier = expected_band(1, stored_tier).partition(" · ")
    return f"SOLUTIONS · {tier.upper()}" if tier else "SOLUTIONS"


class _Reading(NamedTuple):
    """One page, in the form its medium is read in."""

    image: Image.Image
    #: Poppler's words for a page written as operators, ``None`` for a bitmap.
    words: tuple[Word, ...] | None


def _reading_of(page: Page) -> _Reading:
    if isinstance(page, ContentStream):
        return _Reading(interior_images([page])[0], tuple(_words_of(page)))
    return _Reading(page, None)


def _find(readings: Sequence[_Reading], texts: Iterable[str]) -> list[_Found]:
    """Every line of every page that is one copy of one of ``texts``.

    A bitmap page is searched by glyph template (:func:`_one_copy_at`); a page
    written as operators by its text layer, where a line is a copy of ``text``
    when the words poppler joined into it read exactly ``text``.
    """
    texts = tuple(texts)
    found = []
    for page_number, reading in enumerate(readings, start=1):
        if reading.words is not None:
            for line in _lines_of_words(reading.words):
                if line.text in texts:
                    found.append(_Found(page_number, line.text, line.size, line.top))
            continue
        for line in _lines(reading.image):
            for text in texts:
                size = _one_copy_at(line.ink, text)
                if size is not None:
                    found.append(_Found(page_number, text, size, line.top))
    return found


def _exported_pages(data: bytes) -> list[Image.Image]:
    """Every page of an exported interior PDF as device pixels, in print order.

    CARD-356: **``pdf_pages`` cannot be asked for a book with two or more
    operators pages.** It rasterises each one through
    ``pdf_vector.rendered_page`` into ONE shared scratch directory, and that
    function returned ``sorted(directory.glob("page-*.png"))[0]`` (PNG then,
    PGM since CARD-415) -- the
    *earliest file left there*, not the page it was asked for. So every
    operators page of the book comes back as the first one rendered (here the
    blank title page): measured on this module's own book, 9 of its 14 pages
    read as the same blank image. Raster pages are decoded by Pillow and are
    unaffected. Until the helper is fixed (a finding, routed in the card's
    report: ``tests/helpers`` is outside this card's Touches) this module
    reads raster pages through ``pdf_pages`` and each operators page through
    its own fresh scratch directory.
    :meth:`TestBookPdf_BandPrintsOnceInTheExportedPdf.test_the_exported_pages_are_not_one_page_repeated`
    is the control that fails if this goes back to ``pdf_pages`` alone.
    """
    pages = pdf_pages(data)
    media = pdf_vector.page_media(data)
    # Default-DENY (ADR-0039/R2): a page of no medium this tree writes keeps the
    # bugged render if it is skipped, so it is refused here, the way
    # ``band_draws`` refuses it.
    assert pdf_vector.UNCLASSIFIABLE not in media, media
    for index, medium in enumerate(media):
        if medium != pdf_vector.VECTOR:
            continue
        with tempfile.TemporaryDirectory(prefix="band-page-") as directory:
            rendered = pdf_vector.rendered_page(
                data, DPI, index + 1, out_dir=Path(directory)
            )
        pages[index] = Image.fromarray(
            np.asarray(rendered, dtype=np.uint8), mode="L"
        ).convert("RGB")
    return pages


class _Exported(NamedTuple):
    """The book as ``export_book`` wrote it, read page by page in its medium."""

    data: bytes
    media: list[str]
    images: list[Image.Image]
    readings: list[_Reading]


@pytest.fixture(scope="module")
def once_export() -> _Exported:
    """The book's interior, decoded from the PDF ``export_book`` wrote."""
    export = BookPDFGenerator(_book()).export_book(_once_book(), "Band Once")
    data = export.interior.getvalue()
    media = pdf_vector.page_media(data)
    images = _exported_pages(data)
    readings = []
    for number, (medium, image) in enumerate(zip(media, images), start=1):
        if medium == pdf_vector.VECTOR:
            with tempfile.TemporaryDirectory(prefix="band-export-") as directory:
                words = pdf_vector.word_boxes(data, number, out_dir=Path(directory))
            readings.append(_Reading(image, tuple(words)))
        else:
            readings.append(_Reading(image, None))
    return _Exported(data, media, images, readings)


@pytest.fixture(scope="module")
def once_pages(once_export: _Exported) -> list[Image.Image]:
    """The book's interior as device pixels (see :func:`_exported_pages`)."""
    return once_export.images


class TestBookPdf_BandPrintsOnceInTheExportedPdf:
    """AC-1, AC-2 — each band is one line of ink on one page of the PDF.

    Fails if ``_set_band`` (two-up pages) or COMP-007's header (the Hard
    puzzle's page) prints a second copy of a band on rows with no other ink
    within about a line's height sideways (the band strip, the gap between
    slots, the top or bottom margin) or touching the band, or if a band's
    line turns up on such rows on any other page — a divider, the guide or
    the answer key. A copy beside the drawing (a side margin) or over other
    ink (clues, grid, captions) is not seen here; only the recorder class
    (AC-3) catches it. A copy at exactly the band's own spot is caught here
    only incidentally (see the section comment); the recorder guarantees it.
    """

    def test_the_interior_has_the_page_count_this_module_reads(
        self, once_pages: list[Image.Image]
    ) -> None:
        assert len(once_pages) == ONCE_PAGE_COUNT

    def test_every_band_is_found_once_on_its_own_page_and_nowhere_else(
        self, once_export: _Exported
    ) -> None:
        """Each band is found on exactly one page, its puzzle's, and nowhere else.

        A puzzle's band prints once: on its own puzzle page (COMP-007's
        header / ``_set_band``). Its answer — a full page or a slot of a
        packed page — used to print the same "Puzzle N · Tier" line; since the
        approved solutions mockup it carries a solution header of its own
        instead (the number alone, the picture's name, the tier's dots;
        ``draw_solution_header``), so the band line is now found on no answer
        page at all, and never on any *other* puzzle's page. "Nowhere else"
        still means as a line of its own: a copy beside the drawing or over
        other ink is not found (see the section comment; the recorder covers
        it).

        **CARD-356: each page is read in the medium it was written in.** A
        page written as operators is read from its text layer, where "a line
        of its own" is a line poppler joined and a copy over other ink is
        found as well (the template search could not see one); a bitmap page
        keeps the glyph template. Both arms report the size the line was set
        at, and both must say :data:`BAND_FONT_PX`.
        """
        bands = _once_bands()
        found = sorted(
            (hit.page, hit.text, hit.size)
            for hit in _find(once_export.readings, bands.values())
        )
        assert found == sorted(
            (ONCE_BAND_PAGES[number], text, BAND_FONT_PX)
            for number, text in bands.items()
        )

    @pytest.mark.parametrize(
        ("page_number", "number"),
        [(HARD_ALONE_PAGE, 5), (TWO_UP_PAGE, 1), (ONCE_BAND_PAGES[3], 3)],
        ids=["hard-alone", "two-up-easy-upper", "two-up-medium-upper"],
    )
    def test_the_band_strip_holds_one_line_at_the_band_size(
        self, once_export: _Exported, page_number: int, number: int
    ) -> None:
        """The top band strip's ink, rules aside, is one line of the band.

        AC-1 on the Hard puzzle's page (COMP-007's header) and AC-2 on the
        upper slot of each two-up page. The 12 mm strip reaches into the
        drawing's top frame rule (measured: its last 2 px), so rows holding a
        rule are cleared first; what is left must be one run of rows. A copy
        offset down into the frame's rows still leaves its upper part in the
        strip, as a second run of rows or a taller first one (measured: a
        second ``_set_band`` draw at y+60 and at y+80 each failed this test,
        while found-once stayed green).

        **CARD-207: the line is the approved mockup's header.** "Puzzle N" at
        the band's size, emboldened, flush with the usable left edge, and the
        tier in capitals at ``max(10 pt, 0.75 x`` the band's size) flush with
        the usable right edge, the difficulty dots between. So the run's
        leftmost ink is the number's (its box that of "Puzzle N" set once at
        the band's size, plus the emboldening), its rightmost ink is the tier
        word's (the box of the word set once at its size), each within a
        side bearing of its usable edge, and the two sit on one baseline.
        """
        reading = once_export.readings[page_number - 1]
        strip = np.asarray(_band_strip(reading.image).convert("L")) < INK_LEVEL
        text = strip.copy()
        text[_rule_rows(strip)] = False
        rows = _spans(text.any(axis=1), 1)
        assert len(rows) == 1, rows
        band = _once_bands()[number]
        label, _, tier = band.partition(" \u00b7 ")
        word = tier.upper()
        tier_px = round(max(10.0 * DPI / 72.0, 0.75 * BAND_FONT_PX))
        bold_px = math.ceil(BAND_FONT_PX * 0.04)
        # CON-018's margins: a recto's inside (gutter) margin is on its left.
        recto = page_number % 2 == 1
        usable_left = round((GUTTER_MM if recto else OUTSIDE_MM) * PX_PER_MM)
        usable_right = round(
            (BOOK1_WIDTH_MM - (OUTSIDE_MM if recto else GUTTER_MM)) * PX_PER_MM
        )
        bearing = BAND_FONT_PX // 8
        columns = _spans(text.any(axis=0), BAND_FONT_PX // 3)
        middle = text.shape[1] // 2
        number_ink = _cropped(text[:, : middle])
        word_left = columns[-1][0]
        word_ink = _cropped(text[:, word_left:])
        number_ref = _set_once(label, BAND_FONT_PX)
        word_ref = _set_once(word, tier_px)
        assert abs(number_ink.shape[0] - number_ref.shape[0]) <= BOX_TOLERANCE_PX + bold_px, (number_ink.shape, number_ref.shape)
        assert abs(number_ink.shape[1] - number_ref.shape[1]) <= BOX_TOLERANCE_PX + bold_px, (number_ink.shape, number_ref.shape)
        assert abs(word_ink.shape[0] - word_ref.shape[0]) <= BOX_TOLERANCE_PX, (word_ink.shape, word_ref.shape)
        assert abs(word_ink.shape[1] - word_ref.shape[1]) <= BOX_TOLERANCE_PX, (word_ink.shape, word_ref.shape)
        ink_columns = np.flatnonzero(text.any(axis=0))
        assert 0 <= ink_columns[0] - usable_left <= bearing, (ink_columns[0], usable_left)
        assert 0 <= usable_right - ink_columns[-1] <= bearing, (ink_columns[-1], usable_right)
        number_foot = np.flatnonzero(text[:, : middle].any(axis=1))[-1]
        word_foot = np.flatnonzero(text[:, word_left:].any(axis=1))[-1]
        assert abs(number_foot - word_foot) <= BOX_TOLERANCE_PX + 1, (number_foot, word_foot)
        if reading.words is None:
            assert _mismatch(word_ink, word_ref) <= INK_MISMATCH_LIMIT
        else:
            # CARD-356: the glyph template is a raster instrument and has no
            # subject on a page written as operators (see
            # ``test_the_glyph_template_has_no_subject_on_a_page_of_operators``
            # for the measurement). The strip's text layer says the same thing
            # exactly: one line, the band, at the band's size.
            zone = _band_zone(_lines_of_words(reading.words))
            assert [(line.text, line.size) for line in zone] == [
                (band, BAND_FONT_PX)
            ]

    def test_the_two_up_page_carries_each_slots_band_once_upper_first(
        self, once_export: _Exported
    ) -> None:
        bands = _once_bands()
        found = _find([once_export.readings[TWO_UP_PAGE - 1]], bands.values())
        assert [hit.text for hit in sorted(found, key=lambda hit: hit.top)] == [
            bands[1],
            bands[2],
        ]

    def test_the_exported_pages_are_not_one_page_repeated(
        self, once_export: _Exported
    ) -> None:
        """Control on :func:`_exported_pages`: the book's pages are not one image.

        ``pdf_pages`` returned the first operators page it rendered for
        **every** operators page of a book (see :func:`_exported_pages`), and
        every claim above read a blank page without saying so. The six pages
        that carry the book's content -- three puzzle pages, three answer
        pages -- are six different images, each with ink, in either medium.
        Put the fixture back on ``pdf_pages`` alone and this is the test that
        reds.
        """
        content_pages = sorted(
            {*ONCE_BAND_PAGES.values(), *ANSWER_PAGE_OF.values()}
        )
        assert len(content_pages) == 6, content_pages
        digests = {
            number: _page_digest(once_export.images[number - 1])
            for number in content_pages
        }
        assert len(set(digests.values())) == len(content_pages), digests
        for number in content_pages:
            assert _has_ink(once_export.images[number - 1]), f"page {number} is blank"

    def test_the_glyph_template_has_no_subject_on_a_page_of_operators(
        self, once_export: _Exported
    ) -> None:
        """Disposition of the glyph-template search on an operators page (CARD-356).

        The template is the raster path's own rasterisation of the face, so on
        a page written as operators it is the wrong instrument, and this says
        so as a measurement rather than a comment: for the band of a vector
        page the best template mismatch is **over** the limit
        (:data:`INK_MISMATCH_LIMIT`, not moved by this card) while the text
        layer reads the band exactly. Survivors, by name: a bitmap page is
        still searched by template (``_find``'s raster arm, which the
        dividers and the whole unconverted interior go through) and a page of
        operators by its words (``test_every_band_is_found_once_on_its_own_page_and_nowhere_else``).

        On a book whose pages are all bitmaps there is no operators page, and
        the measurement has no page to be taken on: it then asserts the
        converse, that the template **does** match -- so the test is green in
        either tree and means something in each.
        """
        media = once_export.media
        pages = [n for n in ONCE_BAND_PAGES.values() if media[n - 1] == pdf_vector.VECTOR]
        template = _set_once(_once_bands()[5], BAND_FONT_PX)
        if not pages:
            reading = once_export.readings[HARD_ALONE_PAGE - 1]
            assert reading.words is None
            assert _one_copy_at(_lines_ink_of_band(reading.image), _once_bands()[5]) is not None
            return
        reading = once_export.readings[HARD_ALONE_PAGE - 1]
        assert reading.words is not None
        zone = _band_zone(_lines_of_words(reading.words))
        assert [line.text for line in zone] == [_once_bands()[5]]
        strip = np.asarray(_band_strip(reading.image).convert("L")) < INK_LEVEL
        strip[_rule_rows(strip)] = False
        rows = _spans(strip.any(axis=1), 1)
        top, bottom = rows[0]
        mismatch = _mismatch(_cropped(strip[top : bottom + 1]), template)
        assert mismatch > INK_MISMATCH_LIMIT, (
            f"the raster template now matches poppler's rendering of the band "
            f"({mismatch:.3f} <= {INK_MISMATCH_LIMIT}): the glyph-template "
            "arm may be re-applied to operators pages"
        )

    def test_the_search_finds_an_answer_caption_at_its_own_size(
        self, once_export: _Exported
    ) -> None:
        """Control: the search sees the answer key's lettering too.

        The Hard answer's picture name is found once, on its own answer page,
        at a size other than the band's. Since the approved solutions mockup
        that name is the solution header's (``draw_solution_header``: the
        number alone, then the name in grey at the 10 pt floor), where it was
        once the "Puzzle 5 — Snowflake" caption under the drawing; the search
        tells it from a band by size as well as by text, which is what this
        pins. Every puzzle of this book is named "Snowflake", so the name is
        found once per answer and on the answer pages only — never in the
        puzzle section.
        """
        name = "Snowflake"
        found = _find(once_export.readings, [name])
        assert sorted(hit.page for hit in found) == sorted(ANSWER_PAGE_OF.values())
        hard = [hit for hit in found if hit.page == HARD_ANSWER_PAGE]
        assert [(hit.page, hit.text) for hit in hard] == [(HARD_ANSWER_PAGE, name)]
        assert hard[0].size != BAND_FONT_PX
        retired = ANSWER_CAPTION.format(number=5, title=name)
        assert not _find(once_export.readings, [retired]), (
            f"the retired caption {retired!r} is still printed"
        )


class TestBookPdf_AnswerCaptionPrintsTheCustomBookTitle:
    """FR-042/AC-269's ``then``, read off the page instead of inferred.

    AC-268 -- the sibling criterion -- is closed by
    :meth:`TestBookPdf_BandPrintsOnceInTheExportedPdf.test_the_search_finds_an_answer_caption_at_its_own_size`
    above, which composes the caption from :data:`ANSWER_CAPTION` (this
    module's deliberate second implementation of the rule, not
    ``book_answer_key.answer_caption`` run twice) and asserts that string is
    the ink on the answer page, at a size other than the band's. AC-269 is the
    same question for the case that distinguishes it: the per-book title set
    in Arrangement (``books.puzzle_titles``) beating the picture's own name.

    **Why this cell exists.** AC-269's other ref -- the cell at line 308 of
    ``tests/test_book_solved_answer_key.py``, named here by site rather than
    spelled, so this module does not become a text resolver for a ref declared
    elsewhere -- pins the WIRING: it compares the rendered page against
    ``solved_puzzle_page`` called with ``title="Winter Star"``, with the
    picture's name as the negative control.
    That is a real assertion and it is kept; what it cannot see is the caption
    itself, because both sides of its comparison compose the caption through
    the same primitive. Printed "Winter Star -- Puzzle 1", or with the number
    dropped, or with the em dash gone, it would stay green. So AC-269's
    ``then`` -- that the caption *reads* "Puzzle 7 - Winter Star" -- was
    narrated in ``requirements.yml`` and asserted nowhere. CARD-317 review
    cycle 1 (F-003) called that a visibility regression rather than coverage,
    and this is the four-line close it named.

    One-puzzle book, so the number is 1 rather than the criterion's 7; nothing
    else differs, exactly as for AC-268's 5. The negative half is this book's
    own picture name, which must be ink nowhere on that page.

    **Since the approved solutions mockup** the caption under the drawing is
    retired: the title is set in the solution header beside the number alone
    (``draw_solution_header``), so the line read is the title itself, and the
    header is checked to read the number and then the title, in that order.
    """

    TITLE = "Winter Star"
    NAME = "Snowflake"
    PUZZLE_ID = "p7"

    def test_the_answer_caption_reads_the_custom_title_and_not_the_name(self) -> None:
        puzzle = _puzzle(name=self.NAME, puzzle_id=self.PUZZLE_ID)
        book = _book()
        book.puzzle_titles = {self.PUZZLE_ID: self.TITLE}
        pages = _raw_interior([puzzle], book)

        answer = pages[answer_page_number([puzzle]) - 1]
        found = _find([_reading_of(answer)], [self.TITLE, self.NAME])

        assert [hit.text for hit in found] == [self.TITLE], (
            f"the answer page prints {[hit.text for hit in found]} where exactly "
            f"one line of {self.TITLE!r} and no line of {self.NAME!r} was expected"
        )
        assert found[0].size != BAND_FONT_PX, (
            "the caption was found at the band's size, so the line read is the "
            "band and not the caption"
        )
        if isinstance(answer, ContentStream):
            assert _solution_header(_text_of(answer)) == ["1", self.TITLE], (
                "the solution header does not read the puzzle's number and then "
                "the book's own title"
            )


_SHOWN = re.compile(r"\(((?:\\.|[^()\\])*)\) Tj")


def _bands_shown(stream: str, bands: set[str]) -> Counter:
    """How many times each of ``bands`` is shown by a ``(text) Tj`` in ``stream``.

    The operand is read as the string it is: the stream is decoded as
    ``cp1252`` by ``pdf_vector.content_streams`` (the encoding the interior
    declares), so a middle dot in a band is the one character it is.
    A backslash before a backslash or a parenthesis is the only escape this
    writer emits.
    """
    shown: Counter = Counter()
    for operand in _SHOWN.findall(stream):
        text = re.sub(r"\\([()\\])", r"\1", operand)
        if text in bands:
            shown[text] += 1
    return shown


class TestBookPdf_TheStreamReaderCountsABandItIsShown:
    """The control the stream arm of AC-3 needs: it can count, and it can see two.

    A reader that returned an empty counter for every page would pass the
    stream test on any book that was supposed to have no bands and fail on
    every other, so this shows it on a stream whose answer is known: a band
    drawn twice reads as 2, drawn once as 1, a different line as none, and
    the same text drawn inside a longer string is not a band.
    """

    BAND = "Puzzle 1 · Easy"

    def _data(self, *shown: str) -> bytes:
        stream = ContentStream(width_px=300, height_px=300, dpi=300)
        for index, text in enumerate(shown):
            stream.text(text, 10.0, 20.0 + 30 * index, 12.0, grey=0.0)
        return write_vector_pdf([stream], 1).getvalue()

    @pytest.mark.parametrize(
        ("drawn", "count"),
        [
            ((BAND, BAND), 2),
            ((BAND,), 1),
            (("Puzzle 2 · Easy",), 0),
            ((BAND + " and more",), 0),
        ],
        ids=["twice", "once", "another-line", "inside-a-longer-string"],
    )
    def test_a_band_is_counted_as_often_as_it_is_drawn(
        self, drawn: tuple[str, ...], count: int
    ) -> None:
        (stream,) = pdf_vector.content_streams(self._data(*drawn))
        shown = _bands_shown(stream, {self.BAND})
        assert shown[self.BAND] == count
        # The whole counter, not one key: a reader that reported a band that
        # was not drawn, or under a different text, is caught on the cases
        # where nothing should be counted.
        assert sum(shown.values()) == count
        if count == 0:
            assert not shown


_CITATION = re.compile(r"tests/(test_\w+\.py)::(\w+)(?:::(\w+))?")

def _cited_survivors(text: str) -> list[tuple[str, str, str | None]]:
    """``(file, class, method-or-None)`` for every ``tests/<file>::<Class>[::<method>]``
    that ``text`` cites."""
    return sorted(
        {(file, cls, method or None) for file, cls, method in _CITATION.findall(text)},
        key=str,
    )


def _unresolved_survivors(
    text: str, tests_root: Path
) -> list[str]:
    """What ``text`` cites that does not resolve, by ``ast``, default-DENY.

    Only the file a citation names is parsed. A citation resolves when that
    file exists, defines the class at module level, and (when it names one)
    that class defines the method. Anything else is reported by name.
    """
    import ast

    problems = []
    for file, cls, method in _cited_survivors(text):
        target = tests_root / file
        if not target.is_file():
            problems.append(f"{file}: no such file (cited as {cls}::{method})")
            continue
        tree = ast.parse(target.read_text(encoding="utf-8"))
        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == cls
        ]
        if len(classes) != 1:
            problems.append(f"{file}::{cls}: {len(classes)} definitions")
            continue
        if method is not None and not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method
            for node in classes[0].body
        ):
            problems.append(f"{file}::{cls}::{method}: no such method")
    return problems


class TestBookPdf_EveryCitedSurvivorStillExists:
    """This module's retirements name survivors in ``tests/test_book_grid_rules.py``.

    They live in prose, so renaming or removing a cited class would leave a
    retired claim with no survivor and no red. The set is **derived from this
    module's own text** above the guard (ADR-0039/R2): a citation of the form
    ``tests/<file>::<Class>`` added later extends it with no list to keep in
    step, and each is resolved by ``ast`` in the one file it names. Nothing is
    imported from another module.
    """

    SELF = Path(__file__).resolve()

    @classmethod
    def prose(cls) -> str:
        return cls.SELF.read_text(encoding="utf-8").split(
            "class " + "TestBookPdf_EveryCitedSurvivorStillExists"
        )[0]

    def test_every_cited_survivor_resolves(self) -> None:
        assert _unresolved_survivors(self.prose(), self.SELF.parent) == []

    def test_the_derivation_is_not_empty(self) -> None:
        """A floor, not an equality: this refuses the regex matching nothing."""
        cited = _cited_survivors(self.prose())
        assert len(cited) >= 3, cited
        assert {file for file, _, _ in cited} >= {"test_book_grid_rules.py"}

    def test_a_renamed_citation_is_named_and_its_control_is_not(self) -> None:
        text = self.prose()
        victim = "TestBookGridRules_HasThreeWeights"
        assert victim in text
        planted = text.replace(victim, victim + "_Renamed")
        assert _unresolved_survivors(text, self.SELF.parent) == []
        problems = _unresolved_survivors(planted, self.SELF.parent)
        assert len(problems) >= 1 and victim + "_Renamed" in problems[0], problems
        method_planted = text.replace(
            "TestBookGridRules_HasThreeWeights",
            "TestBookGridRules_HasThreeWeights::test_no_such_method_exists",
            1,
        )
        assert any(
            "no such method" in problem
            for problem in _unresolved_survivors(method_planted, self.SELF.parent)
        )


class TestBookPdf_SamePageCanFail:
    """Control for :func:`_same_page`, the medium-neutral equality the puzzle-page
    claims stand on: it is equal for a page and itself, and refuses a page that
    differs by one mark, a page of another extent, and a bitmap against a stream.
    """

    @staticmethod
    def _stream(*, extra: bool = False, width_px: float = 300) -> ContentStream:
        stream = ContentStream(width_px=width_px, height_px=300, dpi=300)
        stream.line(10, 10, 10, 200)
        if extra:
            stream.line(20, 10, 20, 200)
        return stream

    def test_a_page_is_the_same_as_its_twin(self) -> None:
        assert _same_page(self._stream(), self._stream())

    def test_one_mark_more_is_not_the_same_page(self) -> None:
        assert not _same_page(self._stream(), self._stream(extra=True))

    def test_another_extent_is_not_the_same_page(self) -> None:
        assert not _same_page(self._stream(), self._stream(width_px=301))

    def test_a_bitmap_is_never_the_same_as_a_stream(self) -> None:
        assert not _same_page(Image.new("RGB", (300, 300), "white"), self._stream())
        assert _same_page(
            Image.new("RGB", (4, 4), "white"), Image.new("RGB", (4, 4), "white")
        )
        assert not _same_page(
            Image.new("RGB", (4, 4), "white"), Image.new("RGB", (4, 4), "black")
        )


class _BandDraws(NamedTuple):
    #: ``{page written: Counter of band lines drawn on the image written there}``,
    #: pages numbered in write order (the interior's 1..11, then the cover's)
    written: dict[int, Counter]
    #: Band lines drawn on images that were never handed to ``_write_page``.
    unwritten: list[str]
    #: Band lines drawn on an image after that image had been written, counted
    #: only for images that had already received a band line before their
    #: write (only those are held). A late band draw on a written page that had
    #: no band before its write (a divider, say) lands in :attr:`unwritten`,
    #: which no test asserts.
    late: list[str]
    #: CARD-356: the interior pages (1-based) that were written as bitmaps,
    #: read off the written file. Only those go through ``_write_page`` and
    #: ``ImageDraw.text``; ``written``'s keys are write order, and
    #: ``written_pages`` re-keys them to these interior page numbers.
    raster_pages: tuple[int, ...] = ()
    #: The interior PDF as written, for the stream reading.
    data: bytes = b""

    @property
    def written_pages(self) -> dict[int, Counter]:
        """:attr:`written` keyed by interior page number instead of write order."""
        return {
            self.raster_pages[write - 1]: counts
            for write, counts in self.written.items()
        }


@pytest.fixture(scope="class")
def band_draws() -> _BandDraws:
    """Export the book with every ``ImageDraw.text`` and page write recorded.

    A draw is matched to a written page by the identity of the core image the
    draw targets and the page ``_write_page`` receives. Only images that
    received a band line are held, so the recording keeps a few bitmaps alive,
    not the book.
    """
    bands = set(_once_bands().values())
    drawn: list[tuple[object, str]] = []
    written_at: list[tuple[object, int]] = []
    late: list[str] = []
    original_text = ImageDraw.ImageDraw.text
    original_write = BookPDFGenerator._write_page

    def text(self, xy, text, *args, **kwargs):  # type: ignore[no-untyped-def]
        if text in bands:
            if any(image is self.im for image, _ in written_at):
                late.append(text)
            drawn.append((self.im, text))
        return original_text(self, xy, text, *args, **kwargs)

    def write_page(self, pdf, page, *args, **kwargs):  # type: ignore[no-untyped-def]
        page_number = len(writes) + 1
        writes.append(page_number)
        if any(image is page.im for image, _ in drawn):
            written_at.append((page.im, page_number))
        return original_write(self, pdf, page, *args, **kwargs)

    writes: list[int] = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(ImageDraw.ImageDraw, "text", text)
        patch.setattr(BookPDFGenerator, "_write_page", write_page)
        export = BookPDFGenerator(_book()).export_book(_once_book(), "Band Once")
    # CARD-356: ``_write_page`` is the **raster** writer. A page written as
    # operators never reaches it, so the count of writes is no longer the
    # interior's page count: it is the number of bitmap pages the written
    # file holds, read off that file, plus the cover file's one. The medium
    # of each page is classified default-DENY by ``page_media``; a page it
    # cannot classify is a failure here, not a page nobody counted.
    data = export.interior.getvalue()
    media = pdf_vector.page_media(data)
    assert pdf_vector.UNCLASSIFIABLE not in media, media
    assert len(media) == ONCE_PAGE_COUNT, media
    raster_pages = tuple(
        number
        for number, medium in enumerate(media, start=1)
        if medium == pdf_vector.RASTER
    )
    assert len(writes) == len(raster_pages) + 1, (len(writes), raster_pages)

    written: dict[int, Counter] = {}
    unwritten: list[str] = []
    for image, line in drawn:
        pages = [number for target, number in written_at if target is image]
        if pages:
            (page_number,) = pages
            written.setdefault(page_number, Counter())[line] += 1
        else:
            unwritten.append(line)
    return _BandDraws(written, unwritten, late, raster_pages, data)


class TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage:
    """AC-3 — every band draw on a written page is that page's one band.

    Each recorded draw either targets an image later handed to
    ``_write_page`` (counted per page) or one never handed to it
    (:attr:`_BandDraws.unwritten`). The draws that land elsewhere are not
    counted: how many images the export renders and drops is not what this
    card pins.
    """

    def test_each_written_page_received_each_of_its_bands_exactly_once(
        self, band_draws: _BandDraws
    ) -> None:
        """Each puzzle's band is drawn once, on its puzzle page. Its answer —
        a full page or, since CARD-202, its own slot of a packed page — no
        longer draws the band: since the approved solutions mockup it sets a
        solution header of its own (``draw_solution_header``: the number
        alone, the picture's name, the tier's dots), which reads no band line.

        **CARD-356: this is the raster arm of the claim.** The recorder sees
        ``ImageDraw.text`` and ``_write_page``, so it can only see the pages
        that are bitmaps; a page written as operators is not drawn with
        either. It is asserted for exactly the bitmap pages of the written
        file (derived from the file in the fixture), so on a converted
        interior it says that **no divider carries a band** and on the
        unconverted one it says what it always said. The pages written as
        operators are counted in the stream instead:
        :meth:`test_each_operators_page_shows_each_of_its_bands_exactly_once`.
        """
        bands = _once_bands()
        expected: dict[int, Counter] = {}
        for number, page_number in ONCE_BAND_PAGES.items():
            expected.setdefault(page_number, Counter())[bands[number]] += 1
        in_bitmaps = {
            page: counts
            for page, counts in expected.items()
            if page in band_draws.raster_pages
        }
        assert band_draws.written_pages == in_bitmaps

    def test_each_operators_page_shows_each_of_its_bands_exactly_once(
        self, band_draws: _BandDraws
    ) -> None:
        """The stream arm of the same claim, counted in the file that was written.

        For every page of the exported PDF written as operators, the number of
        ``(text) Tj`` shows that read a band line is exactly the number the
        book's own plan puts on that page -- and nothing else shows one, the
        answer pages included (their solution header is not a band line). The
        count is taken from the PDF's content streams
        (``pdf_vector.content_streams``), after the file was written, so a
        second draw of a band cannot reach a written page without raising the
        count: it is also what the ``late`` recorder was asking, for the
        medium that has no write step to be late after.

        Covers the pages the recorder cannot see, and together with it covers
        every page of the book (asserted below), so no page is in neither.
        """
        bands = _once_bands()
        expected: dict[int, Counter] = {}
        for number, page_number in ONCE_BAND_PAGES.items():
            expected.setdefault(page_number, Counter())[bands[number]] += 1

        media = pdf_vector.page_media(band_draws.data)
        streams = pdf_vector.content_streams(band_draws.data)
        counted: dict[int, Counter] = {}
        for number, (medium, stream) in enumerate(zip(media, streams), start=1):
            if medium != pdf_vector.VECTOR:
                continue
            shown = _bands_shown(stream, set(bands.values()))
            # CARD-207: a puzzle page's header shows its band as two pieces
            # (``Puzzle N`` emboldened, the tier in capitals), each its own
            # Tj; ``header_lines`` joins them back into the band's line.
            shown.update(
                line for line in pdf_vector.header_lines(stream) if line in bands.values()
            )
            if shown:
                counted[number] = shown
        operators_pages = {
            n for n, medium in enumerate(media, start=1) if medium == pdf_vector.VECTOR
        }
        assert counted == {
            page: counts for page, counts in expected.items() if page in operators_pages
        }
        # Every page of the book is read by exactly one of the two arms.
        assert operators_pages | set(band_draws.raster_pages) == set(
            range(1, ONCE_PAGE_COUNT + 1)
        )
        assert not operators_pages & set(band_draws.raster_pages)

    def test_no_band_is_drawn_on_a_page_after_it_was_written(
        self, band_draws: _BandDraws
    ) -> None:
        """Only pages that had received a band before their write are watched
        (see :attr:`_BandDraws.late`)."""
        assert band_draws.late == []


# --------------------------------------------------------------------------
# CARD-218 fix round 1 — what the controls below are allowed to conclude
#
# The nine readers these controls are built on used to be written out here and
# again in ``tests/test_book_puzzle_frame.py``, on the house precedent for two
# places needing the same small check (CLAUDE.md, ``solver/propagate.py``'s
# ``mask_runs``). That precedent is for a check a module can cross-check
# natively; these nine read pytest's collection data, which neither file can
# check the other's reading of, and the comment that used to stand here said so
# as "the honest cost of that choice". CARD-219 paid the cost instead: they live
# in ``tests/helpers/shared_fixture_controls.py``, with the agreement guard the
# two copies lacked in ``tests/test_shared_fixture_controls.py``, and with both
# of the holes CARD-218's review left open closed there.
# --------------------------------------------------------------------------


#: The module fixture the module-scoped controls below are controls *on*.
SHARED_SNOWFLAKE = "snowflake_interior"

#: The class fixture :class:`TestBookPdf_EveryFifthGridLineWider`'s control is
#: a control *on*. Only that class declares it, so the two denominators below
#: never overlap.
SHARED_FIFTH_RULE_PAGE = "page"


# --------------------------------------------------------------------------
# RETIRED by CARD-220 — `test_no_test_in_this_module_takes_a_fixture_through_
# getfixturevalue` stood here.
#
# SURVIVOR: tests/test_shared_fixture_controls.py
#   ::TestSharedControls_TheCopiesCannotComeBack
#   ::test_no_importer_reaches_for_a_fixture_at_run_time
#
# It calls the same bound, `shared_fixture_controls.
# refuse_unless_nothing_is_taken_dynamically`, over **every** importer of the
# shared home rather than once per file — "applied here rather than once per
# consumer file so that a module which starts importing the shared home is
# covered the day it does", as its own docstring puts it. This file is one of
# the three importers (measured: test_book_pdf_band.py,
# test_book_puzzle_frame.py, test_book_puzzle_page_vector.py), and the third
# never had a per-file copy — so the shared version already covered strictly
# more than the two copies did.
#
# MUTATION PROOF (CARD-220, out of tree, one file at a time so the survivor
# cannot be credited for the other's mutant):
#   * planted in THIS file only: this module's retired guard FAILED and the
#     survivor FAILED naming `test_book_pdf_band.py` line 1974; the other
#     file's per-file guard PASSED.
#   * planted in test_book_puzzle_frame.py only: the survivor FAILED naming
#     `test_book_puzzle_frame.py` line 3445.
#   * near-miss control: the word in a docstring/string only, planted in both
#     files, left all three GREEN — while a grep instrument would have fired
#     7 times on the MUTATED file. CARD-220 fix round 1 re-derived that figure
#     and states its domain, which the line above did not: the BASELINE is 5
#     occurrences per file at the fork point 4d164f62 (`grep -c` and
#     `grep -o | wc -l` agree, so the domain ambiguity does not explain it),
#     plus the 2 planted mentions. It is 2 per file today. The bound is an
#     `ast` reading of Attribute nodes, not a text match.
#
# Anyone adding a `request.getfixturevalue(...)` consumer to this file still
# reds immediately — in the shared home's test rather than here. Take the
# fixture as a parameter.
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# CARD-218's AC-5 — the control it was missing (cycle 1, F-001)
# --------------------------------------------------------------------------


class TestBookPdf_TheSharedRenderLeavesNoBitmapBehind:
    """AC-5, with a verifier that can fail on this module's **accumulators**.

    AC-5 says the fixture "must not keep more pages alive at once than the
    single-test path did", and named ``test_book_pdf_memory.py``'s peak
    assertions as its verifier. Those assertions instrument that module's own
    ``_live`` dict, so they cannot fail on bytes retained by this one: the
    conversion shipped **8 page bitmaps (201,960,000 B) held to the end of
    every session that collected this file**, and no guard on the board could
    see it: no module under ``tests/`` *asserts a shape* on this process's own
    memory (``tests/helpers/book_corpus.py``'s ``resident_bytes`` reads
    ``ru_maxrss``, but only as the quantity a child's cap is enforced
    against), and the one module that instruments page memory at all measures
    its own live-page dict (deliberately — it says so at its line 84). That
    sentence is held to a grep over every token it claims about —
    ``ru_maxrss|getrusage|RLIMIT_AS|peak_rss|max_rss|tracemalloc|resident_bytes``
    — which returns exactly ``tests/test_book_pdf_memory.py`` and
    ``tests/helpers/book_corpus.py``, **plus the two files this card converts,
    because this very paragraph names the tokens**. Re-run it with
    ``--include='*.py' tests/ | grep -vE 'puzzle_frame|pdf_band'`` to see the
    two that matter, or read the four and note that two of them are this
    sentence talking about itself. (Cycle 2, F-004: the sentence this replaces
    said "at all", and one grep refuted it. The orchestrator's pre-gate then
    found that recording the grep had changed what the grep returns — four
    files, not two — which is why the count is written out here rather than
    left to be rediscovered.)

    pytest keeps a test module in ``sys.modules``, so a module-level
    accumulator outlives the module-scoped fixture that filled it, which is
    exactly what :func:`snowflake_interior` chose module over session scope to
    avoid.

    **Scope, stated as the measurement rather than as a universal.** This
    control's subject is the module-level accumulators
    :func:`_retained_bitmap_bytes` walks — every one this file has, not only
    the digest: :data:`_FIFTH_RULE_RENDERS` is walked by the same instrument
    and holds tuples of three ints, which is why it was never implicated. It
    is *not* a statement about everything this module leaves behind. Measured
    at session end on 2026-10-24, what the walk finds this file retaining is:

        _set_once   lru_cache(maxsize=None), currsize 666 → 24,435,107 B
        _font_bytes lru_cache(maxsize=None), currsize 1   →    757,076 B
        _SHARED_SNOWFLAKE_DIGEST                          →        256 B
        ---------------------------------------------------------------
        total                                                25,192,439 B

    of which **the accumulator is 256 B and the two caches are everything
    else**. That retention is **pre-existing and not this card's**: the same
    walk against this file at the fork point ``c7cca514`` gives
    **25,192,183 B** — identical but for the 256 B of new digest — and both
    ``@lru_cache(maxsize=None)`` decorators are already there, at ``:1111``
    and ``:1116`` of that revision. The caches are out of this control's
    scope, and it claims nothing about them; ``_set_once``'s unbounded cache
    is backlogged in its own right (cycle 2, F-001).

    **Those bytes are not page-bitmap bytes, and CARD-219's fix round stopped
    dividing them into one another.** This docstring used to call the caches
    "0.9979 page bitmaps". A page here is 2550x3300 **RGB**, three bytes a
    pixel; ``_set_once`` caches cropped **boolean ink masks**, one byte a cell
    (measured 2026-10-24: all 666 cached values are ``dtype('bool')``), and
    ``_font_bytes`` holds a TrueType file. One byte of mask is not one byte of
    page, so the ratio compared two units and is gone — the figures above are
    in the one unit the instrument has, *bytes of image or array memory*. Nor
    is 24,435,107 B the ceiling it reads like: each cached mask is a numpy
    **view** of an uncropped mask, and the 666 distinct bases those views keep
    alive hold **110,882,067 B**, 4.5x the figure above, through an edge the
    walk declines (it never descends into something it has already measured).
    Both numbers belong to that backlogged cache and neither is this card's to
    fix; the larger one is recorded here because the smaller one was being
    read as a bound.

    This control is **selection-independent** — unlike the render-count
    controls below it, it needs no denominator: whatever ran, an accumulator
    holding more than its digests is holding more than its digests. One node
    id of it is enough to red the regression.

    It is placed immediately *before* the module's mutation control rather
    than after it, because that control must be the last thing in the file
    that takes :func:`snowflake_interior` (its own ordering guard says so),
    and nothing after this point can add to an accumulator: both fixtures that
    fill one have run.
    """

    def test_the_page_bitmap_unit_is_this_modules_own_page(
        self, snowflake_interior
    ) -> None:
        """The unit the bound below is stated in is this book's real page.

        ``PAGE_BITMAP_BYTES`` is ``test_book_pdf_memory.py``'s definition of a
        page — 2550 x 3300 RGB, 25,245,000 B — and the unit cycle 1 reported
        the retention in. The pages this module draws are measured against it
        here instead of being assumed to match, so a change of trim or
        resolution fails this rather than quietly making the bound mean
        something else. Two instruments, one figure: the project's constant
        and the geometry of a page as drawn.
        """
        measured = {_bitmap_bytes(page) for page in snowflake_interior}
        assert measured == {PAGE_BITMAP_BYTES}, (
            "this module's pages are no longer the page the retention bound "
            f"is stated in: measured {sorted(measured)} B against "
            f"test_book_pdf_memory.PAGE_BITMAP_BYTES = {PAGE_BITMAP_BYTES} B. "
            "Re-derive the bound below from the page this module now draws."
        )

    def test_no_module_level_accumulator_retains_a_page_bitmap(
        self, snowflake_interior
    ) -> None:
        """The accumulators hold one 32-byte digest per page they signed — exactly.

        The node id is unchanged on purpose: the card's mutant tables (M7, M8)
        and three sets of review notes are keyed to it, and the name is still
        true — it is now the weaker half of what is asserted.

        An **equality**, not a bound, and that is the correction cycle 2 asked
        for (F-001). ``total < one page bitmap`` was a threshold this module
        sat 0.21 % under once everything it retains is counted, and it invited
        a comparison against a quantity the instrument above cannot see. The
        equality invites none: the accumulators hold ``32 B x pages`` or they
        are wrong, and they go red the instant any byte comes back — a digest
        store turned into ``page.tobytes()``, a second accumulator holding a
        page, a fixture that never signed, a book of a different length.

        Both sides are derived. ``32`` is sha256's digest size written out by
        hand here rather than read back off :func:`_page_digest`, so this is a
        second statement of the digest's width and not that function run
        twice; the page count is the book the fixture actually handed out. The
        page-bitmap unit still appears, in the message and in the test above,
        because the figure a reader needs when this reds is how many pages the
        accumulator is now worth.

        **CARD-219 widened the walk under it, and with it the exemption.**
        :func:`_retained_bitmap_bytes` asks the garbage collector what every
        value refers to, fenced off from modules, functions and methods, with
        the ``@lru_cache`` exemption and the class rule as its only other
        edits, so the equality above covers the three channels CARD-218 could
        only declare and the three more CARD-219's cycle 1 found still open. **It
        is a bounded reading and not a universal**, and the authority on which
        edges it follows and which it declines is
        ``shared_fixture_controls._step``'s own docstring — this one used to
        say "a page parked anywhere that is not a cache … reds", which was
        false three ways at once (cycle 1, F-001: an instance attribute, a
        deque and a cache inside a list each held a 25,245,000 B page and
        measured 0 B). Read that list before concluding this control covers a
        new hiding place.

        The fourth channel is the one this module has, and it is held apart
        rather than absorbed: the two pre-existing caches hold 25,192,183 B
        between them, so adding them to the total would have forced the bound
        up to where nothing else is checked either. The second assertion is
        the exemption's own control (ADR-0039/R3): the allowance is granted to
        exactly the two names ``functools`` made caches of **and asked for by
        name**, so a third cache reds here. It asks *which* names and never
        how many bytes, because a cache's ``currsize`` depends on content and
        on selection and this control's claim does not. A cache the walk meets
        that this module does not name at all is not in the allowance at all —
        its contents land in the equality above, where an unnamed allowance
        belongs.
        """
        digest_bytes = 32
        unit = _bitmap_bytes(snowflake_interior[0])
        retained = _retained_bitmap_bytes(globals())
        total = sum(retained.by_name.values())
        expected = digest_bytes * len(snowflake_interior)
        detail = (
            ", ".join(
                f"{name} {held:,} B ({held / unit:.4f} pages)"
                for name, held in sorted(
                    retained.by_name.items(), key=lambda row: -row[1]
                )
            )
            or "no module-level name holds any measurable bytes"
        )
        assert total == expected, (
            f"this module's module-level accumulators will leave {total:,} B "
            f"({total / unit:.4f} page bitmaps) alive after its fixtures are "
            f"finalised, rather than the {expected:,} B of one "
            f"{digest_bytes}-byte digest per page of the "
            f"{len(snowflake_interior)}-page book they signed: {detail}. "
            "pytest keeps a test module in sys.modules for the rest of the "
            "session, so a module-level accumulator outlives the "
            "module-scoped fixture that filled it — the retention module "
            "scope was chosen to avoid (CARD-218 AC-5, F-001). Store a "
            "32-byte `_page_digest(page)`, not `page.tobytes()`. This says "
            "nothing about the two `@lru_cache` stores: see the class "
            "docstring, which measures them at 25,192,183 B and leaves them "
            "to their own card."
        )
        # One conjunct, because the other could not fail. CARD-219 shipped
        # `set(retained.by_cache) <= caches` beside this, and both sides of it
        # come from `_caches_of` on this same namespace — `by_cache` is built
        # *from* those names, so the subset holds by construction (cycle 1,
        # F-005; CARD-218's cycle 2 deleted the same shape). The named-set
        # equality below is the failable half and it did bite in cycle 1's spy
        # arm, so it is what stays.
        caches = _lru_cache_names(globals())
        assert caches == {"_font_bytes", "_set_once"}, (
            "the retention allowance is granted to exactly the two "
            "`@lru_cache` stores this module had before CARD-218 "
            "(`_font_bytes`, `_set_once`, together 25,192,183 B of boolean "
            "ink masks and font bytes, backlogged in their own right), and "
            f"this module now declares {sorted(caches)}, with "
            f"{sorted(retained.by_cache)} of them holding measurable bytes. A "
            "new cache is not covered by that allowance: either it holds no "
            "page bitmap, in which case give it its own named exemption here, "
            "or it does, in which case it is the retention this control "
            "exists to refuse."
        )


# --------------------------------------------------------------------------
# CARD-218 — the control on this module's shared render
# --------------------------------------------------------------------------


class TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated:
    """CARD-218's AC-4 for :func:`snowflake_interior`.

    Sharing a render is only sound while every reader is a reader. Pillow
    images are mutable and this module compares pages by ``tobytes()``, so a
    test that drew on a shared page would silently change what the other three
    tests measure, and the failure would land on one of them rather than on
    the test that caused it. This is where it lands instead.

    It is the last class in the module, and since cycle 1's F-006 it *says so
    to pytest* rather than to the reader: both tests below open by asserting,
    off this run's own collected order, that no other test takes
    :func:`snowflake_interior` after them.
    """

    def test_the_shared_pages_are_what_the_fixture_drew(
        self, request, snowflake_interior
    ) -> None:
        """Every page is byte for byte what the fixture drew.

        The digest is taken inside the fixture, before any test sees the
        pages, so this compares the drawn book against the handed-out book
        rather than the handed-out book against itself.

        The two guards first: this control's verdict covers exactly the tests
        that ran, so it refuses a selection that leaves a consumer out, and
        refuses an order that puts one after it (F-002, F-006).
        """
        _refuse_unless_every_consumer_is_collected(request, globals(), SHARED_SNOWFLAKE)
        _refuse_unless_nothing_takes_it_later(
            request, SHARED_SNOWFLAKE, siblings_excepted=True
        )
        assert _SHARED_SNOWFLAKE_DIGEST, "the shared-render digest was not taken"
        moved = [
            number
            for number, (page, drawn) in enumerate(
                zip(snowflake_interior, _SHARED_SNOWFLAKE_DIGEST), start=1
            )
            if _page_digest(page) != drawn
        ]
        assert not moved, (
            "a test in this module drew on the shared interior rather than on "
            f"a copy of it: interior page(s) {moved} no longer match the bytes "
            "the module fixture drew. Take `page.copy()` in the test that "
            "needs to draw, or give that test a render of its own."
        )

    def test_one_render_served_the_whole_module(
        self, request, snowflake_interior
    ) -> None:
        """The saving itself, asserted rather than assumed.

        The digest is appended to once per execution of the module fixture, so
        a digest exactly one book long is the statement that the book was
        drawn once for the module. Widen the fixture's scope back to
        ``function``, or narrow it to ``class``, **and run this whole file**,
        and this holds more than one book's worth of digests and goes red.

        The scope of that claim, corrected in fix round 1 (F-002): it is a
        statement about a run that collected every consumer, and only about
        such a run. Cycle 1 measured the class-scope mutant surviving three
        narrower selections of this very test — the control class alone, this
        node id alone, and ``-k one_render`` — because the counter cannot
        distinguish one render from one render per test when one test took the
        fixture. The first guard refuses those selections now. The second is
        why "one book's worth" can be read as the last word on the module:
        nothing takes the pages after this.
        """
        _refuse_unless_every_consumer_is_collected(request, globals(), SHARED_SNOWFLAKE)
        _refuse_unless_nothing_takes_it_later(
            request, SHARED_SNOWFLAKE, siblings_excepted=True
        )
        assert len(_SHARED_SNOWFLAKE_DIGEST) == len(snowflake_interior), (
            f"{len(_SHARED_SNOWFLAKE_DIGEST)} page digests were recorded for "
            f"a book of {len(snowflake_interior)} pages, across a run that "
            "collected every consumer of the module fixture: the book was "
            "drawn more than once, so the fixture is no longer module-scoped"
        )
