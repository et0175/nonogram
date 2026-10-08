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

import random
from collections import Counter
from functools import lru_cache
from importlib import resources
from io import BytesIO
from typing import Iterable, Iterator, NamedTuple, Sequence

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import BookPDFGenerator, band_identity
from nonogram.export import ExportPayload
from nonogram.export.pdf import render_pages
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of
from tests.helpers.pdf_pages import pdf_pages

# --------------------------------------------------------------------------
# CON-018's Book 1 profile, in millimetres, written out here rather than
# imported — the same figures tests/test_book_pdf.py works from.
# --------------------------------------------------------------------------

BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4
TOP_MM = BOTTOM_MM = 0.375 * 25.4

#: The title band above each puzzle (TERM-028).
BAND_MM = 12.0

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = 300 / 25.4

#: ADR-0037/R2's floor on a thin grid rule, and what it is in whole pixels at
#: 300 DPI: 0.25 mm is 2.95 px, which rounds *up* to 3.
MIN_THIN_RULE_MM = 0.25
MIN_THIN_RULE_PX = 3

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

#: What captions one answer in the packed key: the puzzle's number, an em dash
#: (U+2014) with a space either side, and the picture's title. Written out
#: here for the same reason :data:`BAND_TEMPLATE` is — a second implementation
#: of the rule, not ``book_answer_key``'s own ``answer_caption`` run twice.
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


def _puzzle(
    columns: int = MIN_SIZE,
    rows: int = MIN_SIZE,
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


def _interior(puzzles: Sequence[dict], book: Book | None = None) -> list[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``."""
    return BookPDFGenerator(book if book is not None else _book()).interior_pages(
        list(puzzles)
    )


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
    puzzles, and laid out from interior page 2 with one divider page opening
    each non-empty *named* level. Every book here is one of 15..20-cell
    drawings that never pair (see the class docstrings), so a puzzle takes a
    page.
    """
    order = sorted(range(len(puzzles)), key=lambda index: level_rank(puzzles[index]["difficulty_tier"]))
    plan: dict[int, tuple[int, int]] = {}
    page = 2
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


def _pages_with_band(
    puzzle: dict,
    page_number: int,
    *,
    name: str | None,
    identity: str,
    book: Book | None = None,
) -> tuple[Image.Image, Image.Image]:
    """The pages COMP-007 draws for ``puzzle`` with a band written out here.

    The same payload the generator builds from the row, except that its two
    header fields are given by this test: ``name`` (the picture's title, or
    ``None`` for a page that carries none) and ``identity``, the band line.
    Rendered on the sheet of interior page ``page_number``, so the comparison
    is about the band and nothing else.
    """
    payload = ExportPayload(
        grid=puzzle["grid"],
        row_clues=tuple(tuple(clue) for clue in puzzle["clues_rows"]),
        column_clues=tuple(tuple(clue) for clue in puzzle["clues_cols"]),
        seed=0,
        mode="random",
        width=puzzle["width"],
        height=puzzle["height"],
        name=name,
        difficulty=identity,
    )
    spec = book_page_spec(book if book is not None else _book(), page_number)
    return render_pages(payload, page_spec=spec)


def _answer_page(
    puzzle: dict,
    number: int,
    page_number: int,
    *,
    title: str | None,
    book: Book | None = None,
) -> Image.Image:
    """One puzzle's full answer page, drawn through CARD-197's own primitive.

    FR-042's key was a packed page of tiles (CARD-134) from that card until
    CARD-198 replaced it with one full solved page per puzzle
    (``BookPDFGenerator.solved_puzzle_page``) — the very call the generator's
    own answer-section loop makes, so this helper draws through it rather
    than reimplementing its geometry a second time (guardrail G-2a,
    retargeted again under CARD-198, back to a one-answer-page-per-puzzle
    shape — not byte-for-byte the pre-FR-042 original, since CARD-197's
    primitive draws clues, fill and gray gridlines a bare answer tile never
    did, but one page per puzzle all the same).
    """
    payload = ExportPayload(
        grid=puzzle["grid"],
        row_clues=tuple(tuple(clue) for clue in puzzle["clues_rows"]),
        column_clues=tuple(tuple(clue) for clue in puzzle["clues_cols"]),
        seed=0,
        mode="random",
        width=puzzle["width"],
        height=puzzle["height"],
        name=puzzle.get("puzzle_name"),
        difficulty=puzzle["difficulty_tier"],
    )
    generator = BookPDFGenerator(book if book is not None else _book())
    return generator.solved_puzzle_page(payload, number, page_number, title=title)


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

    def test_the_puzzle_page_is_the_page_of_a_nameless_payload(self) -> None:
        """The page is, pixel for pixel, the page of a payload with no name.

        The band it *does* carry is "Puzzle 1 · Easy" — written out here — so
        this asserts both halves of ADR-0037/R1 at once: the identity is
        printed and the title is not. A page carrying "Snowflake" anywhere,
        in the band or beside the grid, differs from this one.
        """
        puzzle = _puzzle(name=self.NAME)
        page = _interior([puzzle])[puzzle_page_number([puzzle]) - 1]

        expected, _ = _pages_with_band(
            puzzle, puzzle_page_number([puzzle]), name=None, identity="Puzzle 1 · Easy"
        )
        assert _has_ink(_band_strip(page)), "the band is blank"
        assert page.tobytes() == expected.tobytes()

    def test_renaming_the_picture_leaves_the_puzzle_page_identical(self) -> None:
        """Rename the picture and not one pixel of its puzzle page moves.

        The control the previous test needs: the same book, the same position,
        a different name. The puzzle pages are identical and the *answer*
        pages are not, so a measurement that reports "the name is not here"
        is shown to report a name when there is one.
        """
        snowflake = _puzzle(name=self.NAME)
        renamed = _puzzle(name="Iguanodon Skeleton")

        theirs = _interior([snowflake])
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

    Beside the same "Puzzle N · Tier" identity the puzzle page carries, so the
    answer is found by the printed number and recognised by the name.
    """

    NAME = "Snowflake"

    def test_the_answer_page_carries_the_title_and_the_same_identity(self) -> None:
        """The title is on the answer page and is not on the puzzle page.

        Retargeted under G-2a (FR-042's packed key), and again under CARD-198
        (one full solved page per puzzle, CARD-197's own primitive): the
        *rule* this AC states has survived two different answer-page shapes
        unchanged. Three measurements, one book:

        * **absent** — the puzzle page is, pixel for pixel, the page of a
          payload carrying no name at all, so "Snowflake" is nowhere on it;
        * **present** — the answer page is exactly
          ``solved_puzzle_page(payload, 1, page_number, title="Snowflake")``,
          so it carries the title and the same number the band opposite it
          prints;
        * **contributing** — that page is *not* the one titled ``None``
          (captioned "Puzzle 1" alone), so the title is ink and not merely a
          string that was offered.

        One ``number`` feeds the band and the caption, so the two pages are
        being required to agree on the same N rather than on two numbers that
        happen to be spelled alike.
        """
        number = 1
        puzzle = _puzzle(name=self.NAME)
        pages = _interior([puzzle])

        expected_puzzle, _ = _pages_with_band(
            puzzle,
            puzzle_page_number([puzzle]),
            name=None,
            identity=expected_band(number, puzzle["difficulty_tier"]),
        )
        assert pages[puzzle_page_number([puzzle]) - 1].tobytes() == expected_puzzle.tobytes()

        answer = pages[answer_page_number([puzzle]) - 1]
        assert answer.tobytes() == _answer_page(
            puzzle, number, answer_page_number([puzzle]), title=self.NAME
        ).tobytes()
        assert answer.tobytes() != _answer_page(
            puzzle, number, answer_page_number([puzzle]), title=None
        ).tobytes(), "the title contributes no ink to the answer page"

    def test_the_title_is_ink_the_answer_band_would_not_have_without_it(self) -> None:
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
        page = _interior([puzzle])[page_number - 1]

        untitled = _answer_page(puzzle, number, page_number, title=None)
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
        caught. Each page is compared whole, so a caption carrying the wrong
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
        pages = _interior(puzzles)

        for index, puzzle in enumerate(puzzles):
            number = index + 1
            page_number = answer_page_number(puzzles, index)
            page = pages[page_number - 1]

            assert page.tobytes() == _answer_page(
                puzzle, number, page_number, title=puzzle["puzzle_name"]
            ).tobytes(), f"answer {number}"
            assert page.tobytes() != _answer_page(
                puzzle, number, page_number, title=None
            ).tobytes(), f"answer {number} shows no title"


# --------------------------------------------------------------------------
# AC-195 — every 5th rule is wider than every rule between them
# --------------------------------------------------------------------------


class TestBookPdf_EveryFifthGridLineWider:
    """AC-195 — measured on a Book 1 page holding a 30x30 at 4.97 mm.

    ADR-0037/R2's strokes come from the book ``PageSpec`` (COMP-007 applies
    them; the admin panel draws no rule of its own, G-1). What is asserted
    here is the printed result: thickness in pixels, rule by rule, on the page
    the generator produced.
    """

    #: The 30x30 with 9-deep clue gutters AC-175 measures at 4.97 mm on Book 1.
    PUZZLE = (MAX_SIZE, MAX_SIZE, 9)
    CELL_MM = 4.97
    CELL_TOLERANCE_MM = 0.05

    #: Heavy rules: the borders and every 5th line of a 30-cell grid.
    HEAVY_INDICES = (0, 5, 10, 15, 20, 25, 30)

    @staticmethod
    def _page() -> Image.Image:
        columns, rows, depth = TestBookPdf_EveryFifthGridLineWider.PUZZLE
        puzzle = _puzzle(columns, rows, depth)
        return _interior([puzzle])[puzzle_page_number([puzzle]) - 1]

    def test_the_grid_is_the_thirty_by_thirty_at_the_stated_cell(self) -> None:
        """The premise of the measurement, taken off the page itself."""
        drawing = drawing_of(self._page())
        assert (drawing.columns, drawing.rows) == (MAX_SIZE, MAX_SIZE)
        assert drawing.cell / PX_PER_MM == pytest.approx(
            self.CELL_MM, abs=self.CELL_TOLERANCE_MM
        )

    @pytest.mark.parametrize("axis", ["vertical", "horizontal"])
    def test_every_fifth_rule_is_wider_than_every_rule_between_them(
        self, axis: str
    ) -> None:
        """The heavy rules out-measure every thin one, down the page and across.

        The scanline is taken through the middle of the first cell of the
        other axis — inside the grid, between two rules — so every run of ink
        it meets is a rule of this axis and nothing else.
        """
        page = self._page()
        widths = _rule_widths(self._scan(page, axis))

        assert len(widths) == MAX_SIZE + 1, "a 30-cell grid is ruled 31 times"
        heavy = [widths[index] for index in self.HEAVY_INDICES]
        thin = [
            width
            for index, width in enumerate(widths)
            if index not in self.HEAVY_INDICES
        ]
        assert min(heavy) > max(thin)
        assert min(thin) >= MIN_THIN_RULE_PX, "ADR-0037/R2's 0.25 mm floor"
        assert min(thin) / PX_PER_MM >= MIN_THIN_RULE_MM
        assert set(heavy) == {2 * width for width in set(thin)}, "heavy = 2 x thin"

    @pytest.mark.parametrize("axis", ["vertical", "horizontal"])
    def test_the_rules_are_pure_black_and_not_anti_aliased(self, axis: str) -> None:
        """Every pixel the scanline crosses is #000 or the paper, never a grey.

        A rule softened to grey prints lighter than it measures, which is the
        complaint ADR-0037 answers (research §5: faint lines). The whole
        scanline is checked, not only the runs, so an anti-aliased *edge*
        beside a rule fails too.
        """
        page = self._page()
        greys = set(np.unique(self._scan(page, axis)).tolist())
        assert greys <= {0, 255}, f"the scanline carries greys: {sorted(greys)}"

        colour = self._scan(page, axis, mode="RGB").reshape(-1, 3)
        ink = colour[(colour < INK_LEVEL).all(axis=1)]
        assert len(ink), "no ink on the scanline"
        assert {tuple(pixel) for pixel in np.unique(ink, axis=0).tolist()} == {(0, 0, 0)}

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
        page = _interior([puzzle])[puzzle_page_number([puzzle]) - 1]
        expected, _ = _pages_with_band(
            puzzle, puzzle_page_number([puzzle]), name=None, identity="Puzzle 1"
        )
        assert _has_ink(_band_strip(page))
        assert page.tobytes() == expected.tobytes()

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


def test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle() -> None:
    """EC(ADR-0037/R1) — every puzzle of every book, whatever its name and tier.

    A seeded corpus of books: each one a handful of puzzles with names drawn
    from :data:`CORPUS_NAMES` and stored tiers from :data:`CORPUS_TIERS`, at
    extents across CON-011's range, so a puzzle's print position, its name and
    its tier vary independently. For every puzzle of every book the rendered
    puzzle page is required to equal, pixel for pixel, the page COMP-007 draws
    for a payload with **no name** and a band line this module composed from
    ADR-0037's wording and its own tier table.

    That single comparison carries both halves of the rule: a page whose band
    said anything else — the wrong number, a stored ``"easy"`` unlabelled, an
    invented tier for an ungraded row — would differ, and so would a page
    carrying the picture's title anywhere on it.

    Since CARD-128 these are **grouped and divided** books: the tiers are
    drawn independently of the position, so almost every book of the corpus is
    of several levels, prints in an order that is not the one it was handed in
    and carries a divider page opening each of its levels. ``N`` is therefore
    the puzzle's place in the *print* order and the page is the one the
    grouping put it on — both taken from :func:`print_plan`, this module's own
    reading of FR-041 — so a band numbered by submission order, or by page,
    fails here.
    """
    random_source = random.Random(20260923)
    books = 0
    puzzles_checked = 0
    names_seen: set[str | None] = set()
    labels_seen: set[str] = set()
    positions_seen: set[int] = set()

    for book_index in range(MIN_BOOKS + 4):
        count = random_source.randint(1, MIN_POSITION + 1)
        puzzles = []
        for position in range(1, count + 1):
            side = random_source.randint(MIN_SIZE, MIN_SIZE + 5)
            name = random_source.choice(CORPUS_NAMES)
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

        pages = _interior(puzzles)
        plan = print_plan(puzzles)
        for index, puzzle in enumerate(puzzles):
            # Where this row lands once the book is grouped by level, and the
            # number it carries there (CARD-128) — this module's own reading
            # of the print order, not the generator's.
            number, page_number = plan[index]
            identity = expected_band(number, puzzle["difficulty_tier"])
            expected, _ = _pages_with_band(
                puzzle, page_number, name=None, identity=identity
            )
            page = pages[page_number - 1]
            assert _has_ink(_band_strip(page)), f"blank band on {identity!r}"
            assert page.tobytes() == expected.tobytes(), (
                f"book {book_index}, puzzle {number} "
                f"(name {puzzle['puzzle_name']!r}, stored tier "
                f"{puzzle['difficulty_tier']!r}) does not print {identity!r}"
            )
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
#: CARD-198): 1 guide; 2 Easy divider; 3 Puzzles 1-2 two-up; 4 Medium
#: divider; 5 Puzzles 3-4 two-up; 6 Hard divider; 7 Puzzle 5 alone; 8
#: SOLUTIONS divider; 9-13 one full answer page per puzzle (CARD-198, up
#: from the packed key's one page per level, 9-11, before this card).
#: ``print_plan`` above models only books that never pair, so the pages are
#: written out here instead.
ONCE_PAGE_COUNT = 13
ONCE_BAND_PAGES = {1: 3, 2: 3, 3: 5, 4: 5, 5: 7}
HARD_ALONE_PAGE = 7
TWO_UP_PAGE = 3

#: Page 8 is the SOLUTIONS divider, so puzzle N's own full answer page is
#: 8 + N (CARD-198: one per puzzle, in book order, right after it).
ONCE_SOLUTIONS_PAGE = 8
HARD_ANSWER_PAGE = ONCE_SOLUTIONS_PAGE + 5

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
BOX_TOLERANCE_PX = 2
INK_MISMATCH_LIMIT = 0.03

#: The packaged face the book's lettering is set in, addressed as package data
#: (written out here, not imported from ``export.pdf``).
_FONT_PACKAGE = "nonogram.export"
_FONT_RESOURCE = "fonts/DejaVuSans.ttf"


def _once_book() -> list[dict]:
    return [
        _puzzle(tier=tier, puzzle_id=f"once-{index}")
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


class _Found(NamedTuple):
    page: int
    text: str
    size: int
    top: int


def _find(pages: Sequence[Image.Image], texts: Iterable[str]) -> list[_Found]:
    """Every line of every page that is one copy of one of ``texts``."""
    texts = tuple(texts)
    found = []
    for page_number, page in enumerate(pages, start=1):
        for line in _lines(page):
            for text in texts:
                size = _one_copy_at(line.ink, text)
                if size is not None:
                    found.append(_Found(page_number, text, size, line.top))
    return found


@pytest.fixture(scope="module")
def once_pages() -> list[Image.Image]:
    """The book's interior, decoded from the PDF ``export_book`` wrote."""
    export = BookPDFGenerator(_book()).export_book(_once_book(), "Band Once")
    return pdf_pages(export.interior.getvalue())


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
        self, once_pages: list[Image.Image]
    ) -> None:
        """Each band is found on exactly two pages, and nowhere else.

        Since CARD-198 a puzzle's band prints twice, by design: once on its
        own puzzle page (COMP-007's header / ``_set_band``) and once on its
        own full answer page (``solved_puzzle_page`` reuses the same
        ``_set_band`` call, CARD-197's step 7) — never on any *other*
        puzzle's page of either kind. "Nowhere else" still means as a line
        of its own: a copy beside the drawing or over other ink is not
        found (see the section comment; the recorder covers it).
        """
        bands = _once_bands()
        found = sorted(
            (hit.page, hit.text, hit.size) for hit in _find(once_pages, bands.values())
        )
        assert found == sorted(
            (page, text, BAND_FONT_PX)
            for number, text in bands.items()
            for page in (ONCE_BAND_PAGES[number], ONCE_SOLUTIONS_PAGE + number)
        )

    @pytest.mark.parametrize(
        ("page_number", "number"),
        [(HARD_ALONE_PAGE, 5), (TWO_UP_PAGE, 1), (ONCE_BAND_PAGES[3], 3)],
        ids=["hard-alone", "two-up-easy-upper", "two-up-medium-upper"],
    )
    def test_the_band_strip_holds_one_line_at_the_band_size(
        self, once_pages: list[Image.Image], page_number: int, number: int
    ) -> None:
        """The top band strip's ink, rules aside, is one line of the band.

        AC-1 on the Hard puzzle's page (COMP-007's header) and AC-2 on the
        upper slot of each two-up page (``_set_band``). The 12 mm strip
        reaches into the drawing's top frame rule (measured: its last 2 px),
        so rows holding a rule are cleared first; what is left must be one run
        of rows whose ink has the extent and the ink of the line set once at
        the band's size. A copy offset down into the frame's rows still leaves
        its upper part in the strip, as a second run of rows or a taller first
        one (measured: a second ``_set_band`` draw at y+60 and at y+80 each
        failed this test, while found-once stayed green).
        """
        strip = np.asarray(_band_strip(once_pages[page_number - 1]).convert("L")) < INK_LEVEL
        text = strip.copy()
        text[_rule_rows(strip)] = False
        rows = _spans(text.any(axis=1), 1)
        assert len(rows) == 1, rows
        top, bottom = rows[0]
        ink = _cropped(text[top : bottom + 1])
        reference = _set_once(_once_bands()[number], BAND_FONT_PX)
        assert abs(ink.shape[0] - reference.shape[0]) <= BOX_TOLERANCE_PX, (ink.shape, reference.shape)
        assert abs(ink.shape[1] - reference.shape[1]) <= BOX_TOLERANCE_PX, (ink.shape, reference.shape)
        assert _mismatch(ink, reference) <= INK_MISMATCH_LIMIT

    def test_the_two_up_page_carries_each_slots_band_once_upper_first(
        self, once_pages: list[Image.Image]
    ) -> None:
        bands = _once_bands()
        found = _find([once_pages[TWO_UP_PAGE - 1]], bands.values())
        assert [hit.text for hit in sorted(found, key=lambda hit: hit.top)] == [
            bands[1],
            bands[2],
        ]

    def test_the_search_finds_an_answer_caption_at_its_own_size(
        self, once_pages: list[Image.Image]
    ) -> None:
        """Control: the search sees the answer key's lettering too.

        The Hard answer's caption is found once, on its own answer page, at
        a size other than the band's — the caption and the band are two
        different lines of type on the same page since CARD-198 (the band
        above the drawing, the caption below it), and the search tells them
        apart by size as well as by text, which is what this pins.
        """
        caption = ANSWER_CAPTION.format(number=5, title="Snowflake")
        found = _find(once_pages, [caption])
        assert [(hit.page, hit.text) for hit in found] == [(HARD_ANSWER_PAGE, caption)]
        assert found[0].size != BAND_FONT_PX


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
        BookPDFGenerator(_book()).export_book(_once_book(), "Band Once")
    # ``export_book`` writes the interior's pages, then the cover file's one.
    assert len(writes) == ONCE_PAGE_COUNT + 1

    written: dict[int, Counter] = {}
    unwritten: list[str] = []
    for image, line in drawn:
        pages = [number for target, number in written_at if target is image]
        if pages:
            (page_number,) = pages
            written.setdefault(page_number, Counter())[line] += 1
        else:
            unwritten.append(line)
    return _BandDraws(written, unwritten, late)


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
        """Each puzzle's band is drawn once on its puzzle page and once on
        its own answer page (CARD-198: ``solved_puzzle_page`` reuses the
        same ``_set_band`` call its puzzle page uses)."""
        bands = _once_bands()
        expected: dict[int, Counter] = {}
        for number, page_number in ONCE_BAND_PAGES.items():
            expected.setdefault(page_number, Counter())[bands[number]] += 1
        for number, text in bands.items():
            expected.setdefault(ONCE_SOLUTIONS_PAGE + number, Counter())[text] += 1
        assert band_draws.written == expected

    def test_no_band_is_drawn_on_a_page_after_it_was_written(
        self, band_draws: _BandDraws
    ) -> None:
        """Only pages that had received a band before their write are watched
        (see :attr:`_BandDraws.late`)."""
        assert band_draws.late == []
