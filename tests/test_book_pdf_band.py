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


def puzzle_page_number(index: int) -> int:
    """Where puzzle ``index`` (0-based) prints: after the guide page."""
    return 2 + index


def answer_page_number(index: int, count: int) -> int:
    """Where puzzle ``index``'s answer prints: after the SOLUTIONS divider."""
    return 3 + count + index


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
        page = _interior([puzzle])[puzzle_page_number(0) - 1]

        expected, _ = _pages_with_band(
            puzzle, puzzle_page_number(0), name=None, identity="Puzzle 1 · Easy"
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
        puzzle_page = puzzle_page_number(0) - 1
        answer_page = answer_page_number(0, 1) - 1

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
        """The answer page is the page of a payload holding both.

        One ``identity`` string serves both assertions, so the two pages are
        being required to carry the *same* number and tier, not two strings
        that happen to be spelled alike.
        """
        puzzle = _puzzle(name=self.NAME)
        pages = _interior([puzzle])
        identity = "Puzzle 1 · Easy"

        expected_puzzle, _ = _pages_with_band(
            puzzle, puzzle_page_number(0), name=None, identity=identity
        )
        _, expected_answer = _pages_with_band(
            puzzle, answer_page_number(0, 1), name=self.NAME, identity=identity
        )
        assert pages[puzzle_page_number(0) - 1].tobytes() == expected_puzzle.tobytes()
        assert pages[answer_page_number(0, 1) - 1].tobytes() == expected_answer.tobytes()

    def test_the_title_is_ink_the_answer_band_would_not_have_without_it(self) -> None:
        """Drop the name from the expected payload and the band stops matching.

        Without this, the previous test would pass just as well against an
        answer page whose band said only "Puzzle 1 · Easy" — the name has to
        be shown to *contribute* the ink, not merely to have been offered.
        """
        puzzle = _puzzle(name=self.NAME)
        page = _interior([puzzle])[answer_page_number(0, 1) - 1]
        identity = "Puzzle 1 · Easy"

        _, untitled = _pages_with_band(
            puzzle, answer_page_number(0, 1), name=None, identity=identity
        )
        assert _has_ink(_band_strip(page))
        assert page.tobytes() != untitled.tobytes()

    def test_the_answer_number_is_the_number_printed_on_the_puzzle(self) -> None:
        """Every puzzle's answer page repeats its own puzzle's number.

        A book of three, so a page that took its number from its own position
        in the interior — where the answers start at page 6 — rather than from
        the puzzle it answers would be caught.
        """
        puzzles = [
            _puzzle(name=f"Picture {index}", puzzle_id=f"p{index}", tier=tier)
            for index, tier in enumerate(("easy", "medium", "hard"))
        ]
        pages = _interior(puzzles)

        for index, (puzzle, label) in enumerate(zip(puzzles, ("Easy", "Medium", "Hard"))):
            identity = f"Puzzle {index + 1} · {label}"
            _, expected = _pages_with_band(
                puzzle,
                answer_page_number(index, len(puzzles)),
                name=puzzle["puzzle_name"],
                identity=identity,
            )
            page = pages[answer_page_number(index, len(puzzles)) - 1]
            assert page.tobytes() == expected.tobytes(), f"answer {index + 1}"


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
        return _interior([puzzle])[puzzle_page_number(0) - 1]

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
        page = _interior([puzzle])[puzzle_page_number(0) - 1]
        expected, _ = _pages_with_band(
            puzzle, puzzle_page_number(0), name=None, identity="Puzzle 1"
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
                    rows=random_source.randint(MIN_SIZE, MIN_SIZE + 5),
                    depth=3,
                    name=name,
                    tier=tier,
                    puzzle_id=f"b{book_index}-p{position}",
                )
            )

        pages = _interior(puzzles)
        for index, puzzle in enumerate(puzzles):
            number = index + 1
            identity = expected_band(number, puzzle["difficulty_tier"])
            page_number = puzzle_page_number(index)
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
