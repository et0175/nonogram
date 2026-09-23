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
  the book order, and they fit at one shared cell of at least 7.0 mm;
* no puzzle that could have paired with its successor under that rule is left
  alone by the walk;
* concatenating the pages' puzzles front to back yields the book order exactly.

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
from tests.helpers.two_up_ink import drawings_of

#: FR-040's two-up minimum and NFR-008's standard cell, in millimetres.
TWO_UP_MINIMUM_MM = 7.0
STANDARD_CELL_MM = 7.5

#: The title band above each puzzle (TERM-028). A two-up page reserves two.
BAND_MM = 12.0

#: CON-018's Book 1 profile in millimetres, stated in inches here rather than
#: imported, and a 6 x 9 in book beside it — a trim on which far fewer pairs
#: fit, so the corpus is not one sheet's arithmetic.
BOOK1 = (8.5 * 25.4, 11 * 25.4, 0.5 * 25.4, 0.375 * 25.4)
SIX_BY_NINE = (6 * 25.4, 9 * 25.4, 0.5 * 25.4, 0.375 * 25.4)

#: Top and bottom have no stored column and always come from the profile.
TOP_MM = BOTTOM_MM = 0.375 * 25.4

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
        """The height left once a page reserves a band for each of two puzzles."""
        return self.height_mm - TOP_MM - BOTTOM_MM - 2 * BAND_MM

    def shared_cell_mm(self, first: "Puzzle", second: "Puzzle") -> float:
        """FR-040's shared cell for this pair on this sheet, in millimetres."""
        return min(
            STANDARD_CELL_MM,
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


def _expected_pages(sheet: Sheet, order: list[Puzzle]) -> list[tuple[int, ...]] | None:
    """EC-027's walk, written out: the 1-based puzzle numbers of each page.

    ``None`` when any offer this walk makes lands within a millionth of a
    millimetre of the 7.0 mm threshold — a verdict this module's floats cannot
    be trusted to share with the layout's exact fractions, and one disagreement
    would desynchronise every later page of the book.
    """
    pages: list[tuple[int, ...]] = []
    index = 0
    while index < len(order):
        first = order[index]
        second = order[index + 1] if index + 1 < len(order) else None
        if second is not None and first.tier_of_record is not None:
            if first.tier_of_record == second.tier_of_record:
                cell = sheet.shared_cell_mm(first, second)
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

    for case in range(900):
        sheet = Sheet(*(SIX_BY_NINE if case % 4 == 0 else BOOK1))
        order = [_puzzle(rng) for _ in range(rng.randint(1, 8))]
        expected = _expected_pages(sheet, order)
        if expected is None:
            near_threshold += 1
            continue

        plan = BookPDFGenerator(sheet.book).puzzle_pages([p.payload for p in order])
        label = (sheet, [str(p) for p in order])

        # The walk's own shape: one page per plan entry, positions running on
        # from the guide page, and one or two puzzles on each.
        assert [entry.numbers for entry in plan] == expected, label
        assert [entry.page_number for entry in plan] == list(range(2, 2 + len(plan))), label
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
                    assert sheet.shared_cell_mm(members[0], follower) < TWO_UP_MINIMUM_MM, label
                    refused_on_fit += 1
                continue

            paired += 1
            upper, lower = members
            assert upper.tier_of_record is not None, label
            assert upper.tier_of_record == lower.tier_of_record, label

            # One shared cell, FR-040's, inside [7.0, 7.5] mm.
            wanted = sheet.shared_cell_mm(upper, lower)
            assert abs(entry.pair.cell_mm - wanted) < 1e-6, (label, position)
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

    assert books >= 850, books
    assert pages >= 3000, pages
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


def test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages() -> None:
    """EC-027 about the **pages the interior holds**, measured off their ink.

    The walk above is the generator's plan; this is what came out of it. Each
    book's puzzle pages are read back — how many drawings each carries and what
    extent each one is — and required to be the book order, in order, one or
    two to a page, with the earlier puzzle of a pair on top.

    A small corpus by design: every page here is a real 300 DPI raster. It is
    the plan's *execution* that needs measuring, and one wrong page shows up in
    one book.
    """
    rng = random.Random(1271)
    books = pages = paired = single = 0

    for case in range(24):
        sheet = Sheet(*(SIX_BY_NINE if case % 4 == 0 else BOOK1))
        order = [_puzzle(rng, small=True) for _ in range(rng.randint(2, 5))]
        # Distinct extents, so the sequence read off the pages identifies the
        # puzzles: two puzzles of one extent could swap unnoticed.
        extents = {(p.columns, p.rows) for p in order}
        if len(extents) != len(order):
            continue
        expected = _expected_pages(sheet, order)
        assert expected is not None, "no corpus book sits on the threshold"

        rows = [puzzle.as_row(f"p{index}") for index, puzzle in enumerate(order)]
        interior = BookPDFGenerator(sheet.book).interior_pages(rows)
        label = (sheet, [str(p) for p in order])

        # Guide, the puzzle pages, the divider, one answer page per puzzle.
        assert len(interior) == 1 + len(expected) + 1 + len(order), label

        drawn = [
            [(drawing.columns, drawing.rows) for drawing in drawings_of(interior[number - 1])]
            for number in range(2, 2 + len(expected))
        ]
        assert drawn == [
            [(order[n - 1].columns, order[n - 1].rows) for n in numbers]
            for numbers in expected
        ], label
        # ... and therefore the book order, front to back, unchanged.
        assert [extent for page in drawn for extent in page] == [
            (puzzle.columns, puzzle.rows) for puzzle in order
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
