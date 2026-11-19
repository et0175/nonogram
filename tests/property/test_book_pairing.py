"""EC-027 (INV-010) — the pairing walk, over any book order (CARD-127, FR-040).

    EC-027  PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly
        -> test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly
           (the walk itself, over a seeded corpus of book orders)
        -> test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages
           (the same statement about the **pages the interior actually
           contains**, read back off their ink)

The standing property, for every order of any length, tiers and clue depths:

* every page holds one puzzle or two, never more;
* a page holds two only when their tiers are equal, they are consecutive in
  the book order, and they fit at one shared cell of at least 7.0 mm **on a
  sheet capped at the smaller of their two grid sizes' book cells** (CARD-225);
* no puzzle that could have paired with its successor under that rule is left
  alone by the walk;
* concatenating the pages' puzzles front to back yields the book order exactly.

What CARD-225 moved, and what this module had to grow to see it
---------------------------------------------------------------
NFR-008 as amended 2026-10-17 chooses the printed cell **per grid size per
book**, and ``puzzle_pages`` offers each pair a sheet whose flat cap is the
smaller of the two members' grid-size cells. A pairing verdict is therefore no
longer a function of the pair: a third puzzle, anywhere in the book, can take
the cap under 7.0 mm and refuse a pair whose own two-up fit clears it (the
card's F-8), or leave it paired at a smaller cell than its own fit (F-9).

This module was green on both and could not have been otherwise (review cycle
1, F-003): the walk half ran ``puzzle_pages`` with no ``cell_sizes`` map at
all — a legal contract, but the one production no longer takes — and the
rendered half dropped every book holding two members of one grid size, which
is the only shape in which the rule can bite. Both are fixed here:
:func:`_expected_pages` reads the whole book's cells before it walks it,
``puzzle_pages`` is called through the map production settles, the rendered
corpus identifies a page's puzzles by their **drawing** extents rather than
their grid extents so duplicates are still told apart, and eighteen
hand-built books (:func:`_book_cell_books` — nine of each shape since review
cycle 2's F-004) put both F-8 and F-9 in the corpus, asserted by counters at
the foot of each test. Measured: with the
book-wide term deleted from the production side (``_pair_cell_mm`` returning
``None``) both tests fail; before this fix both passed.

How the expectation is independent
----------------------------------
The walk is re-implemented here, in eight lines, over an expected shared cell
written out in floating-point millimetres from FR-040's own definition —
``min(cap, usable width / the wider drawing's columns, (trim height − top −
bottom − two bands) / both drawings' rows)`` — and an expected tier read
through a table of stored spellings written out here rather than through
``nonogram.difficulty``. Nothing in this module imports ``compute_pair_layout``
or ``book_page_spec``; the rendered half measures pages with
``tests/helpers/two_up_ink.py``, which knows nothing about either.

A case whose expected cell lands within a millionth of a millimetre of the
7.0 mm threshold is a float being asked to adjudicate what the layout decides
in exact fractions, so the whole book is skipped — and counted, so the skip
cannot silently swallow the corpus.

No ``hypothesis`` (CLAUDE.md): stdlib ``random.Random`` at fixed seeds, and
each test asserts its own minimum case counts so the corpus cannot shrink.
"""

from __future__ import annotations

import random

from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.clues import compute_clues
from nonogram.export import ExportPayload
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import ink_mask
from tests.helpers.pdf_pages import page_image
from tests.helpers.two_up_ink import drawings_of

#: FR-040's two-up minimum and NFR-008's standard cell, in millimetres.
TWO_UP_MINIMUM_MM = 7.0
STANDARD_CELL_MM = 7.5

#: The cell-size floor COMP-007 keeps even when the sheet cannot hold the
#: drawing at it — written out here as ``tests/property/test_book_pdf_geometry.py``
#: writes it out. It is below FR-040's two-up minimum by a factor of three, so
#: it never decides a pairing verdict; it is part of the single-page fit
#: (:meth:`Sheet.cell_mm`) because that fit's own definition has it.
MIN_CELL_MM = 2.0

#: ``DPI``, written out here rather than imported, matching this module's own
#: independence from ``nonogram.export.layout`` elsewhere.
DPI = 300

#: The title band above each puzzle (TERM-028). A two-up page reserves two.
BAND_MM = 12.0

#: The footer strip a two-up page has reserved out of its height since
#: CARD-248, in device pixels, written out here, as this module writes every
#: other figure out, rather than imported from ``nonogram.export.layout``:
#: ``INTERIOR_FOOTER_MM`` 9.878 mm = **117 px** of height, kept free below
#: the lower slot's drawing so the page has a footer at all. (CARD-248 also
#: made a pair's footer have to hold two QR groups across its width; that
#: clause went with the groups in CARD-391, ADR-0041/R8, so a pair now pairs
#: on the height and width rules of FR-040 alone.)
FOOTER_STRIP_PX = 117

#: CON-018's Book 1 profile in millimetres, stated in inches here rather than
#: imported, and a 6 x 9 in book beside it — a trim on which far fewer pairs
#: fit, so the corpus is not one sheet's arithmetic.
#: The amended profile (2026-10-17, CARD-222): the outside margin moved
#: 0.375 -> 0.5 in, the top to 0.55 in and the bottom to 0.47 in, and the
#: gutter deliberately stayed at KDP's 0.5 in.
BOOK1 = (8.5 * 25.4, 11 * 25.4, 0.5 * 25.4, 0.5 * 25.4)
SIX_BY_NINE = (6 * 25.4, 9 * 25.4, 0.5 * 25.4, 0.5 * 25.4)

#: Top and bottom have no stored column and always come from the profile.
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4

#: Every stored spelling of a tier this project can meet, mapped to the tier of
#: record it means — written out rather than derived, so the expected verdict
#: is a second implementation of ADR-0031's reading. ``"guess"`` is ADR-0031/R3's
#: retired fourth tier, which reads back as Hard.
TIER_OF_RECORD = {
    "easy": "Easy",
    "Easy": "Easy",
    "EASY": "Easy",
    "medium": "Medium",
    "Medium": "Medium",
    "hard": "Hard",
    "Hard": "Hard",
    "guess": "Hard",
    "Guess": "Hard",
}

#: The stored grades a corpus row can carry: the spellings above, and four that
#: are no tier at all — a missing column, a blank, a word from no vocabulary,
#: and a number.
CORPUS_TIERS: tuple[object, ...] = (*TIER_OF_RECORD, None, "", "extreme", 17)


class Sheet:
    """One book's trim and margins, and the millimetres FR-040 works in."""

    def __init__(self, width_mm, height_mm, gutter_mm, outside_mm):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.gutter_mm = gutter_mm
        self.outside_mm = outside_mm

    def __repr__(self):
        return f"Sheet({self.width_mm:.2f}x{self.height_mm:.2f} mm)"

    @property
    def book(self) -> Book:
        """The ``books`` row carrying this print specification."""
        return Book(
            book_id="book-127",
            metadata=BookMetadata(
                title="Property Book",
                description="",
                theme="generic",
                target_audience="adults",
                size="",
                page_count=0,
            ),
            trim_width_cm=f"{self.width_mm / 10:.2f}",
            trim_height_cm=f"{self.height_mm / 10:.2f}",
            gutter_margin_cm=f"{self.gutter_mm / 10:.2f}",
            outside_margin_cm=f"{self.outside_mm / 10:.2f}",
        )

    @property
    def usable_width_mm(self) -> float:
        return self.width_mm - self.gutter_mm - self.outside_mm

    @property
    def pair_height_mm(self) -> float:
        """The height left once a page reserves a band for each of two puzzles
        **and one footer strip** (CARD-248).

        The strip carries the page's folio (and, since CARD-391, its shared
        pointer line), so it is taken out of the height before anything is
        fitted — 353 px of it, converted to millimetres exactly as the
        production call converts the reserve it is handed.
        """
        return (
            self.height_mm
            - TOP_MM
            - BOTTOM_MM
            - 2 * BAND_MM
            - FOOTER_STRIP_PX * 25.4 / DPI
        )

    @property
    def single_height_mm(self) -> float:
        """The height a page holding **one** puzzle fits its drawing in.

        One band and **no** footer strip: a single interior page's drawing is
        fitted to ``trim - top - bottom - band``, which is the figure
        ``tests/property/test_book_pdf_geometry.py`` writes out and measures
        off real ink. It is deliberately a different number from
        :attr:`pair_height_mm`, which reserves a band for each of two puzzles
        and takes CARD-248's footer strip out as well.
        """
        return self.height_mm - TOP_MM - BOTTOM_MM - BAND_MM

    def cell_mm(self, across: int, down: int) -> float:
        """FR-030's single-page fit: what one drawing prints at **alone**.

        ``min(standard cell, usable width / across, single height / down)``,
        never under :data:`MIN_CELL_MM` — this module's own arithmetic, as
        every other figure here is, and the per-member term NFR-008's
        per-grid-size cell is a minimum over (:meth:`book_cell_mm`).
        """
        return max(
            MIN_CELL_MM,
            min(
                STANDARD_CELL_MM,
                self.usable_width_mm / across,
                self.single_height_mm / down,
            ),
        )

    def book_cell_mm(self, order: "list[Puzzle]") -> "dict[tuple[int, int], float]":
        """NFR-008 as amended 2026-10-17: one cell per **grid size** per book.

        CARD-225: the cell a grid size prints at in a book is fitted to the
        deepest-clued member of that grid size, so two members of one extent
        at different clue depths both print at the deeper one's cell. Written
        out here, as :meth:`shared_cell_mm` and :meth:`cell_mm` are, and
        copied in shape from ``tests/property/test_book_pdf_geometry.py``'s
        ``Sheet.book_cell_mm``.

        **Why this oracle needs it at all** (review cycle 1, F-003). The cap a
        pair is offered is the smaller of its two members' grid-size cells, so
        a pair whose own two-up fit clears FR-040's 7.0 mm is nevertheless
        refused when that cap does not — a pairing verdict that depends on a
        *third* puzzle elsewhere in the book. Until this fix the oracle below
        decided every offer from the pair alone and this corpus filtered out
        every book that could have shown the difference.

        Args:
            order: The whole book, in any order. Grid sizes are
                ``(columns, rows)``, read off the puzzles exactly as the
                production map keys them.

        Returns:
            ``{(columns, rows): cell in mm}``, covering exactly the grid sizes
            ``order`` holds.
        """
        sizes: dict[tuple[int, int], float] = {}
        for puzzle in order:
            key = (puzzle.columns, puzzle.rows)
            cell = self.cell_mm(puzzle.across, puzzle.down)
            sizes[key] = cell if key not in sizes else min(sizes[key], cell)
        return sizes

    def shared_cell_mm(
        self,
        first: "Puzzle",
        second: "Puzzle",
        *,
        cap: float = STANDARD_CELL_MM,
    ) -> float:
        """FR-040's shared cell for this pair on this sheet, in millimetres.

        **``cap`` is the sheet's flat cell cap for this offer** (CARD-225).
        NFR-008's 7.5 mm standard cell is the default and was the only
        possibility before that card; since it, a pair is measured on a sheet
        whose cap has been lowered to the smaller of the two members' *grid
        sizes'* book cells (``book_cell_spec`` /
        ``BookPDFGenerator._pair_cell_mm``), and the cap enters the fit at
        exactly the place the standard cell did — it is the first term of the
        minimum below, which is where ``compute_pair_layout`` takes it (its
        ``fit_spec`` carries the lowered cap). A cap below FR-040's 7.0 mm
        therefore refuses the pair outright, however roomy the page is (F-8).

        **No folio reserve since CARD-483.** From CARD-204 Fix 4 this helper
        took a ``reserve`` flag that narrowed the usable width by
        ``_folio_reserve_px`` for a folio at the lower slot's corner, because
        production's walk passed that reserve. CARD-483 stopped production
        passing it (a two-up page's folio is in the footer strip), so the
        oracle stops modelling it: the cell is FR-040's plain number.
        """
        return min(
            cap,
            self.usable_width_mm / max(first.across, second.across),
            self.pair_height_mm / (first.down + second.down),
        )


class Puzzle:
    """One corpus puzzle: its clues, its stored grade and its drawing's extent."""

    def __init__(self, columns, rows, row_clues, column_clues, tier):
        self.columns = columns
        self.rows = rows
        self.row_clues = row_clues
        self.column_clues = column_clues
        self.tier = tier
        self.across = max(len(clue) for clue in row_clues) + columns
        self.down = max(len(clue) for clue in column_clues) + rows

    def __repr__(self):
        return f"Puzzle({self.columns}x{self.rows}, {self.across}x{self.down}, {self.tier!r})"

    @property
    def tier_of_record(self):
        """The tier this row states, or ``None`` when its text is not a tier."""
        return TIER_OF_RECORD.get(self.tier) if isinstance(self.tier, str) else None

    @property
    def payload(self) -> ExportPayload:
        """The row as the generator's walk sees it."""
        return ExportPayload(
            grid=[[False] * self.columns for _ in range(self.rows)],
            row_clues=self.row_clues,
            column_clues=self.column_clues,
            seed=0,
            mode="random",
            width=self.columns,
            height=self.rows,
            name=None,
            difficulty=self.tier,
        )

    def as_row(self, puzzle_id: str) -> dict:
        """The row as the review service hands it to the generator."""
        return {
            "id": puzzle_id,
            "grid": _grid(self.columns, self.rows, *self._depths),
            "clues_rows": [list(clue) for clue in self.row_clues],
            "clues_cols": [list(clue) for clue in self.column_clues],
            "width": self.columns,
            "height": self.rows,
            "puzzle_name": None,
            "difficulty_tier": self.tier,
        }


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> list[list[bool]]:
    """A grid whose row clues are ``row_depth`` deep and columns ``column_depth``.

    Row 0 carries ``row_depth`` single cells a gap apart, so it encodes to that
    many runs and no other row is deeper; column 0 does the same down the page.
    The two share the corner cell, which is one run of each, so neither count
    is disturbed. The depths are independent, which is the whole point: the
    drawing's width and height are what FR-040 fits, and a puzzle's two gutters
    need not agree.
    """
    grid = [[False] * columns for _ in range(rows)]
    for step in range(row_depth):
        grid[0][2 * step] = True
    for step in range(column_depth):
        grid[2 * step][0] = True
    return grid


def _puzzle(rng: random.Random, small: bool = False) -> Puzzle:
    """A puzzle of any supported extent and any clue depth its extent allows.

    Biased toward the small extents that can actually pair — a corpus of 30x30s
    would be a thousand cases all answering ``None`` — but the whole of
    CON-011's range is drawn from, so a pair is never refused here for a reason
    the property does not state.

    ``small`` narrows it further, to 10..14 a side behind gutters at most 3
    deep, for the corpus that renders its pages: there, a few dozen books have
    to hold pages of both make-ups, and a pair needs both drawings inside the
    33 cells of height Book 1 has at 7.0 mm. The sweep over the whole range is
    the walk's own test, which runs a thousand books for the price of none of
    them being drawn.
    """
    def side() -> int:
        if small:
            return rng.randint(MIN_SIZE, 14)
        return rng.randint(MIN_SIZE, 16) if rng.random() < 0.7 else rng.randint(MIN_SIZE, MAX_SIZE)

    deepest = 3 if small else 6
    columns, rows = side(), side()
    row_depth = rng.randint(1, min(deepest, (columns + 1) // 2))
    column_depth = rng.randint(1, min(deepest, (rows + 1) // 2))
    found = compute_clues(_grid(columns, rows, row_depth, column_depth))
    # A tier a reader can grade four times in five: a corpus in which most
    # neighbours disagree about their tier would refuse most pairs before the
    # fit was ever measured, and the fit is half of what is being swept.
    tier = (
        rng.choice(CORPUS_TIERS[len(TIER_OF_RECORD):])
        if rng.random() < 0.2
        else rng.choice(CORPUS_TIERS[: len(TIER_OF_RECORD)])
    )
    puzzle = Puzzle(columns, rows, found.rows, found.columns, tier)
    assert (puzzle.across, puzzle.down) == (row_depth + columns, column_depth + rows)
    puzzle._depths = (row_depth, column_depth)
    return puzzle


def _member(
    columns: int, rows: int, row_depth: int, column_depth: int, tier: str = "easy"
) -> Puzzle:
    """One corpus puzzle at an exact extent and exact clue depths.

    :func:`_puzzle`'s construction with the dice taken out, for the shapes the
    sweep cannot reach (:func:`_book_cell_books`). The same assertion
    :func:`_puzzle` makes is made here: the drawing's extents are the depths
    plus the grid, so a corpus member cannot silently be a different puzzle
    from the one its figures were worked out for.
    """
    found = compute_clues(_grid(columns, rows, row_depth, column_depth))
    puzzle = Puzzle(columns, rows, found.rows, found.columns, tier)
    assert (puzzle.across, puzzle.down) == (row_depth + columns, column_depth + rows)
    puzzle._depths = (row_depth, column_depth)
    return puzzle


#: The Book 1 grid sizes a :func:`_book_cell_books` family is built over, and
#: the clue depths its paired members take (CARD-225, review cycle 2, F-004).
#:
#: A grid size can only show this card's pairing verdict when it holds both a
#: pair that fits two-up and a member deep enough to decide the size's own
#: cell. On Book 1's 190.5 mm of usable width that is a three-column window:
#: a pair fits two-up at 27 drawing cells across or fewer (190.5 / 27 =
#: 7.06 mm; CARD-204's folio reserve held it to about 25 until CARD-483), and
#: a member only takes the size's cell below FR-040's 7.0 mm at
#: 28 or more (190.5 / 28 = 6.80 mm). The paired members are 1 deep across, so
#: each is 23..25 cells wide and fits; the third member's row gutter is set to
#: land the whole size's cell on the figure each family wants.
BOOK_CELL_COLUMNS = (22, 23, 24)
BOOK_CELL_PAIR_DEPTHS = (
    ((1, 1), (1, 2)),
    ((1, 2), (1, 3)),
    ((1, 3), (1, 1)),
)

#: How wide the deciding member's drawing is, in cells, in each family:
#: 28 puts the grid size's cell at 190.5 / 28 = 6.80 mm, **below** 7.0 mm, so
#: the pair is refused for a cell a third puzzle decided (F-8); 27 puts it at
#: 190.5 / 27 = 7.06 mm, **above** 7.0 mm but below the pair's own 7.25/7.5 mm
#: fit, so the pair still pairs and prints smaller than it would alone (F-9).
REFUSING_ACROSS = 28
LOWERING_ACROSS = 27


def _book_cell_family(third_across: int) -> list[tuple[Sheet, list[Puzzle]]]:
    """Nine Book 1 books, each three members of one grid size, built to order.

    One book per :data:`BOOK_CELL_COLUMNS` x :data:`BOOK_CELL_PAIR_DEPTHS`
    combination: two shallow members of the size, which pair, and a third
    whose drawing is ``third_across`` cells wide, which decides the size's
    book cell for all three (:meth:`Sheet.book_cell_mm` takes the minimum
    within a grid size).

    Args:
        third_across: The deciding member's drawing width in cells —
            :data:`REFUSING_ACROSS` or :data:`LOWERING_ACROSS`. Its row gutter
            is whatever gets it there on this width, and its column gutter is
            2, which keeps its drawing distinct from both paired members'.
    """
    sheet = Sheet(*BOOK1)
    return [
        (
            sheet,
            [
                _member(columns, 10, *first),
                _member(columns, 10, *second),
                _member(columns, 10, third_across - columns, 2),
            ],
        )
        for columns in BOOK_CELL_COLUMNS
        for first, second in BOOK_CELL_PAIR_DEPTHS
    ]


def _refusal_books() -> list[tuple[Sheet, list[Puzzle]]]:
    """The F-8 family: the grid size's cell is 6.80 mm, so no pair in the book
    is paired although each pair's own two-up fit clears 7.0 mm."""
    return _book_cell_family(REFUSING_ACROSS)


def _lowered_cell_books() -> list[tuple[Sheet, list[Puzzle]]]:
    """The F-9 family: the grid size's cell is 7.06 mm, so each book's pair is
    paired, at that cell rather than at the 7.25/7.5 mm its own fit allows."""
    return _book_cell_family(LOWERING_ACROSS)


def _book_cell_books() -> list[tuple[Sheet, list[Puzzle]]]:
    """The 18 books that exercise CARD-225's own pairing verdict (F-003).

    Nine of each shape, :func:`_refusal_books` then :func:`_lowered_cell_books`
    — parametrised over three grid widths and three pair depths each in review
    cycle 2 (F-004), where the regression surface inside this property was one
    hand-built book per shape and each of the three counters below was
    satisfied by exactly one occurrence.

    **Why they are built rather than sampled.** F-8 needs one grid size to
    hold both a pair that fits two-up *and* a third, deeper member that takes
    that size's book cell under FR-040's 7.0 mm — so the size must be 22..24
    columns wide, shallow enough down the page for two to stack inside
    :attr:`Sheet.pair_height_mm`, and must appear **twice** in one book of at
    most eight puzzles. :func:`_puzzle` draws a side in that width window
    about once in twenty-three, and two members of the same such size in one
    book essentially never: measured over the 3600-book sweep below, the shape
    occurs zero times, for F-9 as well as F-8.

    **Rare, not unreachable** (review cycle 2, F-004). Measured off-corpus
    over 80,000 books from the same :func:`_puzzle` generator, F-8 occurred
    twice and F-9 not at all — about one book in 40,000, so reaching either by
    sweeping would need O(10^5) books, some thirty times this corpus and far
    outside engineering-standards section 6's case budget. The sweep is what
    makes the oracle's new term *safe* everywhere; these books are what make
    it *bite*, and the counters at the foot of each test are what stop the
    family shrinking back to one case of each.

    Each book's figures are this module's own arithmetic
    (:meth:`Sheet.cell_mm`, :meth:`Sheet.shared_cell_mm`) and are stated in
    :data:`REFUSING_ACROSS` / :data:`LOWERING_ACROSS` only to say what each
    family is *for*; nothing below reads them as an expectation.
    """
    return _refusal_books() + _lowered_cell_books()


def _pages_for_a_qualifying_run(length: int) -> int:
    """A run's pages over its length alone: 4 to a page, the last page
    holding whatever 1-3 are left (owner decision 2026-11-09, CARD-232 AC-4)."""
    return -(-length // 4)


def _expected_answer_pages(order: list[Puzzle]) -> int:
    """How many pages the answer section takes for ``order``.

    CARD-202: a puzzle packs with its same-level run (every supported size
    does since the owner's 2026-11-09 decision); a level change or a
    non-qualifying puzzle closes the run (G-6). Written out here rather than
    imported (``nonogram.admin.book_answer_key.plan_small_answer_pages``):
    this module's subject is the *pairing* walk, and an answer-page count
    re-derived from the generator's own packing function would say nothing
    about the interior it is counting.
    """
    pages = 0
    run_length = 0
    run_level = None
    in_run = False
    for puzzle in order:
        qualifies = puzzle.columns <= MAX_SIZE and puzzle.rows <= MAX_SIZE
        level = puzzle.tier_of_record
        if qualifies and in_run and level == run_level:
            run_length += 1
            continue
        if in_run:
            pages += _pages_for_a_qualifying_run(run_length)
            in_run = False
        if qualifies:
            run_length, run_level, in_run = 1, level, True
        else:
            pages += 1
    if in_run:
        pages += _pages_for_a_qualifying_run(run_length)
    return pages


#: Where each level sits in the printed book (INV-009), and where a row whose
#: tier is no tier at all sits: after every level, behind no divider.
_LEVEL_RANK = {"Easy": 0, "Medium": 1, "Hard": 2}
_UNGRADED_RANK = len(_LEVEL_RANK)


def _extent_of(puzzle: Puzzle) -> tuple[int, int, int, int]:
    """One puzzle's drawing as a page shows it: grid, then drawing, extents.

    ``(columns, rows, across, down)``. The last two are the clue gutters' own
    depths plus the grid (TERM-021), which is what distinguishes two members of
    one grid size on a page since CARD-225 let a book hold them.
    """
    return (puzzle.columns, puzzle.rows, puzzle.across, puzzle.down)


def _drawing_top(ink, drawing) -> int:
    """Where ``drawing``'s column-clue gutter starts, read down its grid's left border.

    The grid's vertical rules run from the drawing's top edge down to the
    grid's bottom border, so the unbroken run of ink in that border's column
    that reaches ``grid_bottom`` starts on the drawing's top edge. Read on the
    whole page rather than taken from ``drawings_of``: with no clue frame
    (2026-11-09) nothing rules a two-up slot's top edge, and the helper's cut
    between the two slots can fall inside the lower slot's first clue row.
    """
    column = ink[: drawing.grid_bottom + 1, drawing.grid_left]
    top = drawing.grid_bottom
    while top > 0 and column[top - 1]:
        top -= 1
    return top


def _measured_extent(drawing, ink) -> tuple[int, int, int, int]:
    """The same four numbers, read off one drawing's own ink.

    ``tests.helpers.page_ink`` reports the grid's extents and the drawing's own
    left edge — the outer edge of the row-clue gutter — and
    :func:`_drawing_top` the top one, so the drawing's extents are those
    edges' distance from the grid's far borders in cells, at the cell the page
    actually printed. Rounded to whole cells: the edges are each rounded to a
    whole device pixel independently, so the quotient lands a few thousandths
    off a whole number (measured: 23.966 for 24).
    """
    cell = drawing.cell
    return (
        drawing.columns,
        drawing.rows,
        round((drawing.grid_right - drawing.left) / cell),
        round((drawing.grid_bottom - _drawing_top(ink, drawing)) / cell),
    )


def _printed(order: list[Puzzle]) -> list[Puzzle]:
    """``order`` as the interior prints it: easy, then medium, then hard.

    A stable sort on the level alone — this module's own reading of FR-041 —
    so two puzzles of one level keep the order they were submitted in
    (CARD-128 decides this at PDF time, so it holds for a list handed straight
    to the generator).
    """
    return sorted(
        order,
        key=lambda puzzle: _LEVEL_RANK.get(puzzle.tier_of_record, _UNGRADED_RANK),
    )


def _divider_count(order: list[Puzzle]) -> int:
    """How many divider pages the puzzle section opens: one per named level."""
    return len({
        puzzle.tier_of_record for puzzle in order if puzzle.tier_of_record is not None
    })


def _book_cap_mm(
    sheet: Sheet,
    book_cells: dict[tuple[int, int], float],
    first: Puzzle,
    second: Puzzle,
) -> float:
    """The flat cap the sheet carries when this pair is offered (CARD-225, F-8).

    The **smaller** of the two members' grid-size book cells — the owner's own
    rule for a shared page ("two puzzles sharing a page use the smaller of
    their two sizes"), which is what makes the two grids line up. Two members
    of one grid size share one entry, so the rule degenerates to that entry.
    """
    return min(
        book_cells[(first.columns, first.rows)],
        book_cells[(second.columns, second.rows)],
    )


def _expected_pages(
    sheet: Sheet, order: list[Puzzle]
) -> list[tuple[int, ...]] | None:
    """EC-027's walk, written out: the 1-based puzzle numbers of each page.

    No folio reserve on any ``shared_cell_mm`` call below: production's
    ``puzzle_pages`` stopped passing ``compute_pair_layout`` one in CARD-483
    (it passed CARD-204 Fix 4's fixed reserve until then, and this oracle
    with it), so modelling one here would disagree with every pair
    production commits to.

    **``cap`` on every call too, since CARD-225** (review cycle 1, F-003).
    NFR-008 as amended 2026-10-17 chooses the printed cell per grid size per
    book, and ``puzzle_pages`` offers each pair a sheet whose flat cap is the
    smaller of the two members' grid-size cells (:func:`_book_cap_mm`). So an
    offer's verdict is no longer a function of the pair alone: a **third**
    puzzle, anywhere in the book and of either member's grid size, can take
    the cap under FR-040's 7.0 mm and refuse a pair whose own two-up fit
    clears it, or leave it paired at a smaller cell than its own fit. This
    oracle therefore reads the whole book before it walks it, exactly as
    production settles the map over the whole book before the walk
    (``BookPDFGenerator.cell_sizes``). Without this term the oracle models the
    rule this card superseded.

    ``None`` is returned when any offer this walk makes lands within a
    millionth of a millimetre of the 7.0 mm threshold — a verdict this
    module's floats cannot be trusted to share with the layout's exact
    fractions, and one disagreement would desynchronise every later page of
    the book.
    """
    book_cells = sheet.book_cell_mm(order)
    pages: list[tuple[int, ...]] = []
    index = 0
    while index < len(order):
        first = order[index]
        second = order[index + 1] if index + 1 < len(order) else None
        if second is not None and first.tier_of_record is not None:
            if first.tier_of_record == second.tier_of_record:
                cell = sheet.shared_cell_mm(
                    first,
                    second,
                    cap=_book_cap_mm(sheet, book_cells, first, second),
                )
                if abs(cell - TWO_UP_MINIMUM_MM) < 1e-6:
                    return None
                if cell >= TWO_UP_MINIMUM_MM:
                    pages.append((index + 1, index + 2))
                    index += 2
                    continue
        pages.append((index + 1,))
        index += 1
    return pages


def test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly() -> None:
    """EC-027: for any book order of any length, tiers and clue depths, the walk
    pairs exactly the in-order, same-tier, fitting neighbours and nothing else,
    and never changes the order."""
    rng = random.Random(20260923127)
    books = pages = paired = single = 0
    refused_on_tier = refused_on_fit = ungraded = odd_tail = near_threshold = 0
    at_cap = below_cap = 0
    # CARD-225 (review cycle 1, F-003): the two ways the grid size's own book
    # cell — a figure a *third* puzzle in the book can decide — changes this
    # walk's answer. Both are asserted non-zero at the foot of this test, so
    # the new term in `_expected_pages` cannot be a no-op dressed up as one.
    refused_on_book_cell = book_cell_lowered = 0

    # **3600 books since CARD-248, up from 900 — and the reason is the point.**
    # That card reserves a footer strip out of every pair's height, and refuses
    # a pair whose page cannot carry both puzzles' links at all; between them
    # they cut this corpus's paired verdicts to **25** at 900 books, against
    # the 100 this test's own minimum below asserted before them — too few to
    # keep these counts meaningful. The corpus grew by the same factor rather
    # than the minima shrinking, so what the property is checked over has not
    # weakened; what shrank is the *share* of pairs that pair, which is this
    # card's measured cost and is asserted as such by
    # ``tests/test_book_qr_slot.py``'s ``TestTwoUpFooter_...`` classes.
    def corpus():
        """The sweep, then the eighteen hand-built books of :func:`_book_cell_books`.

        A generator, so the sweep's draws happen in exactly the order they did
        before this fix (every minimum below is measured on this seed) and no
        book is held in memory once it has been walked.
        """
        for case in range(3600):
            sheet = Sheet(*(SIX_BY_NINE if case % 4 == 0 else BOOK1))
            yield sheet, [_puzzle(rng) for _ in range(rng.randint(1, 8))]
        yield from _book_cell_books()

    for sheet, order in corpus():
        book_cells = sheet.book_cell_mm(order)
        expected = _expected_pages(sheet, order)
        if expected is None:
            near_threshold += 1
            continue

        payloads = [p.payload for p in order]
        generator = BookPDFGenerator(sheet.book)
        # Through the door production goes through (CARD-225): the whole-book
        # cell map, settled once over every member, which is what `section_plan`
        # and `puzzle_page_plan` both hand this walk. Called without it the
        # walk takes its documented no-map fallback (F-14) and certifies the
        # rule this card superseded, which is what left F-8 unseen here.
        plan = generator.puzzle_pages(payloads, cell_sizes=generator.cell_sizes(payloads))
        label = (sheet, [str(p) for p in order])

        # The walk's own shape: one page per plan entry, positions running on
        # from the front matter, and one or two puzzles on each. The walk is
        # called with no ``first_page``, so it starts at its own default: one
        # past the blank title page (CARD-206) and the 2-page guide
        # (CARD-201), i.e. interior page 4 — written out here rather than
        # imported, like every other expectation in this file.
        assert [entry.numbers for entry in plan] == expected, label
        assert [entry.page_number for entry in plan] == list(range(4, 4 + len(plan))), label
        for entry in plan:
            assert 1 <= len(entry.numbers) <= 2, label
            assert entry.is_two_up == (len(entry.numbers) == 2), label

        # Concatenating the pages front to back is the book order exactly.
        printed = [number for entry in plan for number in entry.numbers]
        assert printed == list(range(1, len(order) + 1)), label

        for position, entry in enumerate(plan):
            members = [order[number - 1] for number in entry.numbers]
            if entry.pair is None:
                single += 1
                # Nothing that could have paired was left alone: the next
                # puzzle in the *order* is the only candidate, and it is one
                # only when the tiers agree and the pair fits.
                follower = (
                    order[entry.numbers[0]] if entry.numbers[0] < len(order) else None
                )
                if follower is None:
                    odd_tail += 1
                elif members[0].tier_of_record is None:
                    ungraded += 1
                elif members[0].tier_of_record != follower.tier_of_record:
                    refused_on_tier += 1
                else:
                    # CARD-225: the cell this offer was really measured at is
                    # capped by the two grid sizes' own book cells, so a pair
                    # whose own fit clears 7.0 mm is refused when that cap does
                    # not (F-8). Both readings are taken, so which of the two
                    # refused it is counted rather than conflated.
                    cap = _book_cap_mm(sheet, book_cells, members[0], follower)
                    capped = sheet.shared_cell_mm(
                        members[0], follower, cap=cap
                    )
                    assert capped < TWO_UP_MINIMUM_MM, label
                    if (
                        sheet.shared_cell_mm(members[0], follower)
                        >= TWO_UP_MINIMUM_MM
                    ):
                        refused_on_book_cell += 1
                    else:
                        refused_on_fit += 1
                continue

            paired += 1
            upper, lower = members
            assert upper.tier_of_record is not None, label
            assert upper.tier_of_record == lower.tier_of_record, label

            # One shared cell, FR-040's, inside [7.0, 7.5] mm — and capped at
            # the smaller of the two grid sizes' book cells (CARD-225, F-9:
            # the cap is a ceiling the pair's own fit still beats when it is
            # the smaller of the two).
            cap = _book_cap_mm(sheet, book_cells, upper, lower)
            wanted = sheet.shared_cell_mm(upper, lower, cap=cap)
            assert abs(entry.pair.cell_mm - wanted) < 1e-6, (label, position)
            if wanted < sheet.shared_cell_mm(upper, lower) - 1e-9:
                book_cell_lowered += 1
            assert TWO_UP_MINIMUM_MM <= entry.pair.cell_mm <= STANDARD_CELL_MM, label
            at_cap += entry.pair.cell_mm == STANDARD_CELL_MM
            below_cap += entry.pair.cell_mm < STANDARD_CELL_MM

            # The earlier puzzle takes the upper slot, on this page's own sheet.
            assert (entry.pair.upper.rows, entry.pair.upper.columns) == (upper.rows, upper.columns)
            assert (entry.pair.lower.rows, entry.pair.lower.columns) == (lower.rows, lower.columns)
            for slot in (entry.pair.upper, entry.pair.lower):
                assert slot.page is not None and slot.page.cell_mm == entry.pair.cell_mm

        pages += len(plan)
        books += 1

    # **Stated against the corpus that is actually built** (CARD-248 review,
    # Fix 3): 3600 books and 15994 pages, measured on this seed. These two
    # floors read ``850``/``3000`` until this fix — the figures from the 900
    # books the loop above built before this card grew it — which was never a
    # weakened guard (``paired >= 100`` and ``refused_on_footer >= 500`` both
    # fail at 900 books) but did read as though the corpus were a quarter of
    # its size. No minimum here is lowered.
    #
    # The book floor was derived as 3600 less the ``near_threshold`` tolerance
    # asserted at the foot of this test, which is the only way a case leaves
    # the loop without counting. The page floor keeps about 6 % for a future
    # geometry change that moves the pairing share (pairing fewer pairs prints
    # *more* pages, so this floor is the safe direction). Both fail outright if
    # the corpus is ever shrunk back towards 900 books, which printed about
    # 4000.
    #
    # **Two of these floors were diluted by review cycle 2's F-004 and are
    # restated here rather than re-tightened** (review cycle 3, F-003). The
    # corpus is now 3618 books, not 3600: the 18 hand-built ones
    # (:func:`_book_cell_books`) are appended after the sweep. So ``books >=
    # 3595`` leaves an effective sweep tolerance of 23, not the 5 this comment
    # reasoned about, and ``paired >= 100`` is met by the sweep's own 106 with
    # 9 more coming from the F-9 family — a 7-pair sweep regression would now
    # be absorbed. Measured, not assumed: with the hand-built books removed,
    # every minimum in this block still passes. They are left as they are
    # because tightening a sweep floor against a corpus that two cards have
    # already grown is how these figures went stale twice; what the floors are
    # for is catching a corpus that *shrinks*, and they still do that
    # outright.
    assert books >= 3595, books
    assert pages >= 15000, pages
    # Both verdicts, and every reason a pair is refused, are in the corpus.
    assert paired >= 100, paired
    assert single >= 2500, single
    assert refused_on_tier >= 1000, refused_on_tier
    assert refused_on_fit >= 350, refused_on_fit
    assert ungraded >= 400, ungraded
    assert odd_tail >= 600, odd_tail
    # Both regimes of the shared cell: held at the standard cell, and fitted below it.
    assert at_cap >= 20, at_cap
    assert below_cap >= 20, below_cap
    # The float/fraction skip is a corner, not a sieve.
    assert near_threshold <= 5, near_threshold
    # CARD-225 (review cycle 1, F-003): both ways the book's per-grid-size cell
    # changes this walk's answer are in the corpus. Without them the oracle's
    # new term would be satisfied by every book that has no second member of
    # any grid size — which is what the whole 3600-book sweep is on its own
    # (measured: with `_book_cell_books` removed from the corpus above, both
    # counters are **zero** over 3600 books), and so a production side with
    # the term removed would stay green.
    #
    # **Measured: 9 and 9** — one occurrence per book of each nine-book
    # family, none from the sweep. The floors are set below that, with
    # headroom for a geometry change that moves one width out of the window;
    # they read `>= 1` while each shape was a single hand-built book, which
    # could not say whether the family was nine books or one (review cycle 2,
    # F-004).
    assert refused_on_book_cell >= 6, refused_on_book_cell
    assert book_cell_lowered >= 6, book_cell_lowered


def test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages() -> None:
    """EC-027 about the **pages the interior holds**, measured off their ink.

    The walk above is the generator's plan; this is what came out of it. Each
    book's puzzle pages are read back — how many drawings each carries and what
    extent each one is — and required to be the book order, in order, one or
    two to a page, with the earlier puzzle of a pair on top.

    A small corpus by design: every page here is a real 300 DPI raster. It is
    the plan's *execution* that needs measuring, and one wrong page shows up in
    one book.

    **A book may hold two members of one grid size** (CARD-225, review cycle 1
    F-003), which is the only shape in which NFR-008's per-grid-size cell can
    differ from a member's own fit and so the only shape in which this card's
    pairing verdict is reachable. Until this fix the corpus dropped every such
    book, which kept :func:`_expected_pages`' pair-only reading sound and
    structurally blind. What a page is read back against is therefore the
    **drawing's** extents and not the grid's alone — grid columns and rows plus
    each clue gutter's own depth, all four measured off the ink — so two
    members of one grid size at different clue depths are still told apart by
    the sequence the pages show. Two members of one grid size *and* identical
    gutters are one drawing twice over, with nothing on the page to tell them
    apart, and are still filtered out below.
    """
    rng = random.Random(1271)
    books = pages = paired = single = 0
    # How many of the drawings measured here print at their grid size's book
    # cell rather than at their own fit (CARD-225). Asserted non-zero at the
    # foot, the way `tests/property/test_book_pdf_geometry.py` asserts its own
    # `shared_binds`: without it the widened corpus would be a wider set of
    # books in which the new rule still never bites.
    shared_binds = 0

    def corpus():
        """The small random sweep, then one book of each hand-built shape.

        Both books' three members are one grid size. In the first
        (:func:`_refusal_books`) the pair is refused for a cell a *third*
        puzzle decided, so the interior really does hold three single pages
        where the pair-only reading expects two (F-8). In the second
        (:func:`_lowered_cell_books`) the pair is paired, at the grid size's
        cell rather than at its own larger fit (F-9) — so this half now
        renders that shape too, rather than leaving F-9's ink to
        ``tests/test_book_cell_size.py``'s
        ``TestBookCellSize_SharedPageTakesTheSmaller`` alone (review cycle 2,
        F-004). One book of each: every page here is a real 300 DPI raster,
        and the nine-book families are the walk half's business.
        """
        for case in range(24):
            sheet = Sheet(*(SIX_BY_NINE if case % 4 == 0 else BOOK1))
            yield sheet, [_puzzle(rng, small=True) for _ in range(rng.randint(2, 5))]
        yield _refusal_books()[0]
        yield _lowered_cell_books()[0]

    for sheet, order in corpus():
        # Distinct *drawings*, so the sequence read off the pages identifies
        # the puzzles: two puzzles drawn identically could swap unnoticed.
        drawings = {_extent_of(p) for p in order}
        if len(drawings) != len(order):
            continue
        book_cells = sheet.book_cell_mm(order)
        shared_binds += sum(
            1
            for puzzle in order
            if book_cells[(puzzle.columns, puzzle.rows)]
            < sheet.cell_mm(puzzle.across, puzzle.down) - 1e-9
        )
        # The book prints grouped by level (INV-009, CARD-128), so the walk's
        # order — and every page number below — is the grouped one.
        printed = _printed(order)
        dividers = _divider_count(printed)

        rows = [puzzle.as_row(f"p{index}") for index, puzzle in enumerate(order)]
        generator = BookPDFGenerator(sheet.book)
        # CARD-200 inserts a table of contents between the guide and the
        # puzzle section, whose own length (`toc_page_count`) depends on the
        # book's trim and this book's own puzzle count — read off the real
        # plan for this case rather than assumed.
        toc_page_count = generator.section_plan(rows).toc_page_count
        expected = _expected_pages(sheet, printed)
        assert expected is not None, "no corpus book sits on the threshold"
        interior = generator.interior_pages(rows)
        label = (sheet, [str(p) for p in order])

        # The blank title page (CARD-206), the 2-page guide (CARD-201), the
        # table of contents (CARD-200), a
        # divider per non-empty level, the puzzle pages, the SOLUTIONS
        # divider, the packed answer pages, and the closing thank-you page
        # (owner, 2026-11-10).
        assert len(interior) == (
            1 + 2 + toc_page_count + dividers + len(expected) + 1
            + _expected_answer_pages(printed)
            + 1
        ), label

        # Which interior page each planned puzzle page landed on: page 1 is
        # the blank title page (CARD-206), pages 2-3
        # are the guide (CARD-201), pages 4..(3+toc_page_count) are the table
        # of contents (CARD-200), and each named level's run opens with a
        # divider page.
        numbers_of: list[int] = []
        page_number = 4 + toc_page_count
        opened: object = object()
        for group in expected:
            level = printed[group[0] - 1].tier_of_record
            if level != opened:
                opened = level
                if level is not None:
                    page_number += 1
            numbers_of.append(page_number)
            page_number += 1

        # PLANT RECORD (CARD-359, review F-6): the matched control for the ink
        # assertion below is the plant that keeps the plan and the page count
        # and draws the wrong puzzle (``stalepayload``: red HERE, the other two
        # tests green). The plant that stops two puzzles ever sharing a page
        # (``nopair``) reds this test on the PAGE-COUNT assertion above and
        # never reaches the ink, so it is not evidence for the ink claim.
        # CARD-359 (ADR-0042/R6): the claim is a drawing's extent in whole
        # CELLS, a ratio of two pixel distances read off the page's ink, so
        # it needs pixels and survives the medium (the 1-3 px the media
        # disagree by is under a hundredth of a cell). ``page_image`` hands a
        # raster page back unchanged and rasterises an operators page.
        drawn = []
        for number in numbers_of:
            image = page_image(interior[number - 1])
            ink = ink_mask(image)
            drawn.append([_measured_extent(drawing, ink) for drawing in drawings_of(image)])
        assert drawn == [
            [_extent_of(printed[n - 1]) for n in numbers] for numbers in expected
        ], label
        # ... and therefore the print order, front to back, unchanged.
        assert [extent for page in drawn for extent in page] == [
            _extent_of(puzzle) for puzzle in printed
        ], label

        for page in drawn:
            assert 1 <= len(page) <= 2, label
            paired += len(page) == 2
            single += len(page) == 1
        pages += len(drawn)
        books += 1

    assert books >= 15, books
    assert pages >= 40, pages
    assert paired >= 8, paired
    assert single >= 25, single
    # CARD-225: drawings here really are printed at their grid size's cell
    # rather than at their own fit, so the oracle's book-wide term is doing
    # work on the rendered interior and not only on the plan. **Measured: 4**,
    # two from each of the two hand-built books; the random sweep contributes
    # none (review cycle 2, F-004 — with both books out of the corpus this
    # counter is zero). The floor reds if either book leaves.
    assert shared_binds >= 3, shared_binds


# ---------------------------------------------------------------------------
# CARD-204 Fix 2 (cycle-1 review F-1/F-3) — a pair's verdict is its own
# geometry, never a specific page number (no folio reserve since CARD-483)
# ---------------------------------------------------------------------------


def _filler(tier: str) -> Puzzle:
    """A blank 10x10 puzzle of ``tier``, used only to push a pair's own page
    number around without ever being offered to it itself: deliberately a
    different tier from every pair built below, so INV-010's own
    tier-equality gate keeps it from ever pairing with — or being mistaken
    for a member of — the pair under test, however many fillers surround
    it."""
    blank = tuple((0,) for _ in range(10))
    return Puzzle(10, 10, blank, blank, tier)


#: A pair the 7.5 mm cap binds: **23** columns x 6 rows, row- and column-clue
#: depth 2 (``across`` = 25), so the page fit is 190.5 / 25 = 7.62 mm on
#: Book 1's 190.5 mm of usable width and the cap wins. Until CARD-483 the
#: generator's fixed folio reserve (108 px = 9.144 mm) took it to
#: (190.5 - 9.144) / 25 = 7.25424 mm; with no reserve it is the cap.
_BORDERLINE_ROW_CLUES = tuple((1, 1) for _ in range(6))
_BORDERLINE_COLUMN_CLUES = tuple((1, 1) for _ in range(23))

#: The pair's shared cell: NFR-008's flat 7.5 mm cap.
_BORDERLINE_CELL_MM = 7.5

#: The tight pair — **25** columns, ``across`` = 27 — a pair the folio
#: reserve used to refuse in every regime ((190.5 - 9.144) / 27 = 6.717 mm,
#: under FR-040's 7.0 mm) and that pairs in every regime since CARD-483, at
#: the width-bound cell 190.5 / 27 mm, hand-derived here rather than read off
#: ``compute_pair_layout``. CARD-483's AC-3 pin of a recovered pair, on the
#: production walk.
_TIGHT_ROW_CLUES = tuple((1, 1) for _ in range(6))
_TIGHT_COLUMN_CLUES = tuple((1, 1) for _ in range(25))
_TIGHT_CELL_MM = 190.5 / 27

#: One column wider again — **26** columns, ``across`` = 28 — and the page fit
#: is 190.5 / 28 = 6.80 mm, under the floor with no reserve at all: the
#: "always refuses" shape of the invariant, which the tight pair carried until
#: CARD-483 made it pair.
_WIDE_COLUMN_CLUES = tuple((1, 1) for _ in range(26))


def _borderline_pair(tier: str = "easy") -> tuple[Puzzle, Puzzle]:
    first = Puzzle(23, 6, _BORDERLINE_ROW_CLUES, _BORDERLINE_COLUMN_CLUES, tier)
    second = Puzzle(23, 6, _BORDERLINE_ROW_CLUES, _BORDERLINE_COLUMN_CLUES, tier)
    return first, second


def _tight_pair(tier: str = "easy") -> tuple[Puzzle, Puzzle]:
    first = Puzzle(25, 6, _TIGHT_ROW_CLUES, _TIGHT_COLUMN_CLUES, tier)
    second = Puzzle(25, 6, _TIGHT_ROW_CLUES, _TIGHT_COLUMN_CLUES, tier)
    return first, second


def _wide_pair(tier: str = "easy") -> tuple[Puzzle, Puzzle]:
    first = Puzzle(26, 6, _TIGHT_ROW_CLUES, _WIDE_COLUMN_CLUES, tier)
    second = Puzzle(26, 6, _TIGHT_ROW_CLUES, _WIDE_COLUMN_CLUES, tier)
    return first, second


def test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber() -> None:
    """INV-010: a pair's own geometry and tier alone decide whether it pairs
    and at what cell — never the specific page number it happens to land on,
    and never the book's own total scale either.

    F-1 (CARD-204 cycle 1) reproduced the bug this guards: the identical pair
    paired at a 2-digit page and refused at a 3-digit page of the *same* book,
    because a folio reserve was sized from page numbers. Fix 4 made the
    reserve a fixed, dpi-only constant; **CARD-483 removed it from the walk**,
    because a two-up page's folio is set in the footer strip and the corner it
    reserved is never drawn on (``tests/test_book_page_numbers.py``'s
    ``TestTwoUpNeverTakesTheCornerFolio``). The name is kept; the invariant is
    the same with no reserve at all: the *same* pair, at the *same*
    ``cell_mm``, in a 1-digit, a 2-digit and a 3-digit book alike, whether it
    is offered first or last (filler puzzles of a *different* tier move it
    between page 3 and a page dozens on, without ever being offered to it).

    Three pairs, three shapes: the borderline pair pairs at the cap, the tight
    pair pairs at its width-bound cell (and is one the reserve used to refuse,
    so it also pins CARD-483's recovery through the production walk), and the
    wide pair refuses in every regime.

    No ``hypothesis`` (CLAUDE.md): a small, fully enumerated sweep over three
    known book-scale boundaries, with the expected cells hand-derived.
    """
    sheet = Sheet(*BOOK1)
    generator = BookPDFGenerator(sheet.book)

    # (filler_count, the book's own max_page_number digit count). Every
    # regime gives each pair the identical verdict and cell_mm.
    REGIMES = (
        (1, 1),
        (6, 2),
        (98, 3),
    )

    def target(plan, number):
        return next(entry for entry in plan if number in entry.numbers)

    cases = 0
    for filler_count, digits in REGIMES:
        fillers = [_filler("hard") for _ in range(filler_count)]

        # This regime really does carry the digit count it is named for —
        # otherwise the case below proves nothing about the boundary it
        # claims to exercise.
        max_page_number = 4 + 2 + filler_count - 1
        assert len(str(max_page_number)) == digits, (filler_count, max_page_number)

        found = {}
        for name, make in (
            ("borderline", _borderline_pair),
            ("tight", _tight_pair),
            ("wide", _wide_pair),
        ):
            first, second = make()
            early = target(
                generator.puzzle_pages([p.payload for p in [first, second] + fillers]), 1
            )
            late = target(
                generator.puzzle_pages([p.payload for p in fillers + [first, second]]),
                filler_count + 1,
            )
            # The pair lands on a different *actual* page number in the two
            # placements — otherwise this case would not test position
            # independence at all, only repeat the same call twice.
            assert early.page_number != late.page_number, (name, filler_count)
            # The direct form of the invariant: the two placements agree.
            assert (early.pair is None) == (late.pair is None), (name, filler_count)
            if early.pair is not None:
                assert abs(early.pair.cell_mm - late.pair.cell_mm) < 1e-9, (name, filler_count)
            found[name] = early

        assert found["borderline"].pair is not None, filler_count
        assert abs(found["borderline"].pair.cell_mm - _BORDERLINE_CELL_MM) < 1e-9, filler_count
        assert found["tight"].pair is not None, filler_count
        assert abs(found["tight"].pair.cell_mm - _TIGHT_CELL_MM) < 1e-9, (
            filler_count,
            found["tight"].pair.cell_mm,
        )
        assert found["wide"].pair is None, filler_count

        cases += 1

    assert cases == len(REGIMES)
