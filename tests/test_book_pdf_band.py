"""CARD-117 — the band, the title's one page, and print-weight rules (ADR-0037).

    AC-193  TestBookPdf_PuzzlePageCarriesNoPictureTitle
    AC-194  TestBookPdf_AnswerKeyCarriesPictureTitle
    AC-195  TestBookPdf_EveryFifthGridLineWider
    EC(ADR-0037/R1)
            PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle

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
from typing import Iterable, Sequence

import numpy as np
import pytest
from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import BookPDFGenerator, band_identity
from nonogram.export import ExportPayload
from nonogram.export.pdf import render_pages
from nonogram.export.png import render_answer_page
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of

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

#: The same caption with the title withheld. Not a rule of FR-042 but the
#: **control** the retargeted AC-194 tests need: a page captioned with this
#: is the page the key would carry if the title were not printed, and the
#: title's ink is what stands between the two.
UNTITLED_ANSWER_CAPTION = "Puzzle {number}"

#: FR-042's six-up tiling — every answer here is a MIN_SIZE grid, so no page
#: of these books is ever taken down to four-up (INV-011).
SIX_UP = 6


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

    Only for books whose answers take one page each — the three-tier book of
    AC-194, where every level starts a page of its own (AC-290), and the
    one-puzzle books — so the answer's page is its number's place after the
    SOLUTIONS divider.
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
    entries: Sequence[tuple[dict, str]],
    page_number: int,
    heading: str | None,
    book: Book | None = None,
) -> Image.Image:
    """One page of the packed answer key, drawn from captions written out here.

    FR-042's form of the key (CARD-134): the answers are tiles on a shared
    page, each under its caption, the page headed by its level. The captions
    this module names go in, so comparing the result with the generator's page
    is about which answers, in which order, under which captions, and nothing
    else — the same technique :func:`_pages_with_band` uses for a band, moved
    onto the page shape FR-042 replaced the per-puzzle answer page with
    (guardrail G-2a).
    """
    return render_answer_page(
        [(puzzle["grid"], caption) for puzzle, caption in entries],
        SIX_UP,
        book_page_spec(book if book is not None else _book(), page_number),
        heading,
    )


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

        Retargeted under G-2a: FR-042 deleted the one-answer-page-per-puzzle
        form this used to compare against byte for byte, so the *rule* is
        asserted on the packed key instead. Three measurements, one book:

        * **absent** — the puzzle page is, pixel for pixel, the page of a
          payload carrying no name at all, so "Snowflake" is nowhere on it;
        * **present** — the answer page is the packed page captioned
          "Puzzle 1 — Snowflake", exactly, so it carries the title and the
          same number the band opposite it prints;
        * **contributing** — that page is *not* the one captioned "Puzzle 1",
          so the title is ink and not merely a string that was offered.

        One ``number`` feeds the band and the caption, so the two pages are
        being required to agree on the same N rather than on two numbers that
        happen to be spelled alike; the tier reaches the answer page as the
        level heading FR-042 puts at the top of it.
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
        titled = ANSWER_CAPTION.format(number=number, title=self.NAME)
        assert answer.tobytes() == _answer_page(
            [(puzzle, titled)], answer_page_number([puzzle]), "Easy"
        ).tobytes()
        assert answer.tobytes() != _answer_page(
            [(puzzle, UNTITLED_ANSWER_CAPTION.format(number=number))],
            answer_page_number([puzzle]),
            "Easy",
        ).tobytes(), "the title contributes no ink to the answer page"

    def test_the_title_is_ink_the_answer_band_would_not_have_without_it(self) -> None:
        """Withhold the title and the *same* packed page loses ink, in one place.

        Retargeted under G-2b. What this used to compare the key against was
        ``_pages_with_band(...)[1]`` — the full clued per-puzzle answer page
        FR-042 deleted — so it compared two page *kinds*, which differ (~3% of
        their pixels) whether or not a title is printed, and its companion
        ``_has_ink(_band_strip(page))`` could not fail either: on a packed
        page the top 12 mm is where the first answer *tile* sits, so that
        strip carries ink with no heading and an untitled caption. Both were
        assertions that read as evidence and were not.

        The control is now the same page kind, one caption apart: the packed
        page of this very answer captioned "Puzzle 1" — what the key would
        print if the title were withheld (``answer_caption`` stops at the
        number when there is no title, and the em dash is not printed with
        nothing after it). Three measurements of the one difference:

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

        untitled = _answer_page(
            [(puzzle, UNTITLED_ANSWER_CAPTION.format(number=number))],
            page_number,
            "Easy",
        )
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

        A book of three at three tiers, so FR-042 gives each level a page of
        its own (AC-290) and the answers land on interior pages 6, 7 and 8 —
        which means an answer captioned from its position in the interior
        rather than from the puzzle it answers would read "Puzzle 6" and be
        caught. Each page is compared whole, so a caption carrying the wrong
        number, the wrong title or the wrong level heading fails, and each is
        then re-checked against its untitled control so the title is shown to
        be ink on every one of them.

        Retargeted under G-2a: the assertion moved from the deleted per-puzzle
        answer page onto the packed key, and the rule it asserts — the title
        prints here and its number is the puzzle's — is unchanged.
        """
        puzzles = [
            _puzzle(name=f"Picture {index}", puzzle_id=f"p{index}", tier=tier)
            for index, tier in enumerate(("easy", "medium", "hard"))
        ]
        pages = _interior(puzzles)

        for index, (puzzle, label) in enumerate(zip(puzzles, ("Easy", "Medium", "Hard"))):
            number = index + 1
            page_number = answer_page_number(puzzles, index)
            page = pages[page_number - 1]

            assert page.tobytes() == _answer_page(
                [
                    (
                        puzzle,
                        ANSWER_CAPTION.format(
                            number=number, title=puzzle["puzzle_name"]
                        ),
                    )
                ],
                page_number,
                label,
            ).tobytes(), f"answer {number}"
            assert page.tobytes() != _answer_page(
                [(puzzle, UNTITLED_ANSWER_CAPTION.format(number=number))],
                page_number,
                label,
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
