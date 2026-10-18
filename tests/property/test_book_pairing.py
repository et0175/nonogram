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
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _folio_reserve_px,
    _qr_group_line_px,
)
from nonogram.clues import compute_clues
from nonogram.export import ExportPayload
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.two_up_ink import drawings_of

#: FR-040's two-up minimum and NFR-008's standard cell, in millimetres.
TWO_UP_MINIMUM_MM = 7.0
STANDARD_CELL_MM = 7.5

#: ``DPI``, written out here rather than imported, matching this module's own
#: independence from ``nonogram.export.layout`` elsewhere (``_folio_reserve_px``
#: is a font-measurement helper, not FR-040's own geometry, so importing it is
#: not the kind of "same formula, no second check" shortcut this module
#: otherwise avoids).
DPI = 300

#: The title band above each puzzle (TERM-028). A two-up page reserves two.
BAND_MM = 12.0

#: The footer strip a two-up page has reserved out of its height since
#: CARD-248, in device pixels, and the 2 cm QR icon and 9 pt footer gap the
#: two groups in it are built from — all written out here, as this module
#: writes every other figure out, rather than imported from
#: ``nonogram.export.layout``:
#:
#: * ``INTERIOR_FOOTER_MM`` 29.878 mm = **353 px** of height, kept free below
#:   the lower slot's drawing so the page has a footer at all;
#: * one group is the icon, a gap, its widest line and a gap again, and two
#:   groups must fit the usable width or the pair is not paired.
#:
#: The widest line itself comes from :func:`_qr_group_line_px`, imported for
#: the same reason :func:`_folio_reserve_px` is: it measures a face, which
#: this module does not reimplement; FR-040's geometry below is still this
#: module's own arithmetic.
FOOTER_STRIP_PX = 353
QR_SLOT_PX = 236
FOOTER_GAP_PX = 38

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

        The strip carries both puzzles' QR groups and the page's own folio, so
        it is taken out of the height before anything is fitted — 353 px of it,
        converted to millimetres exactly as the production call converts the
        reserve it is handed.
        """
        return (
            self.height_mm
            - TOP_MM
            - BOTTOM_MM
            - 2 * BAND_MM
            - FOOTER_STRIP_PX * 25.4 / DPI
        )

    def footer_carries_two_groups(self) -> bool:
        """Whether this sheet's footer strip is wide enough for two QR groups.

        The walk's second gate since CARD-248: a page that could not carry
        both puzzles' links is not a two-up page at all, so the pair prints on
        two single pages instead (AC-6). ``2 x (icon + gap + line + gap)``
        less the last group's trailing gap, against the usable width — and the
        line is the widest the face can ever set for any puzzle number, never
        this page's own, so the gate is a property of the trim and the face
        (INV-010).

        Measured: Book 1's 190.5 mm usable width carries two; a 6 x 9 in
        book's 127.0 mm carries one, so **no pair on a 6 x 9 trim is a two-up
        page any more**.
        """
        pitch = QR_SLOT_PX + 2 * FOOTER_GAP_PX + _qr_group_line_px(DPI)
        return 2 * pitch - FOOTER_GAP_PX <= self.usable_width_mm * DPI / 25.4

    def shared_cell_mm(
        self, first: "Puzzle", second: "Puzzle", *, reserve: bool = False
    ) -> float:
        """FR-040's shared cell for this pair on this sheet, in millimetres.

        **CARD-204 history: Fix 1/Fix 2's reserve was page/book-specific
        (reverted), Fix 3 removed it entirely (reverted), Fix 4 restores it
        as a fixed, universal constant (owner decision, 2026-10-12, "fixed
        universal reserve").** Fix 1 and Fix 2 had this helper accept a
        book- or page-level ``max_page_number`` and shrink the cell to buy
        CARD-200's folio some guaranteed horizontal room — which let a
        non-geometric, page/book-specific quantity flip whether two puzzles
        paired (INV-010, cycle-1 F-1, cycle-2 F-5). Fix 3 removed the
        mechanism to fix that, but silently reintroduced the folio-loss bug
        on every two-up page (cycle-3 F-7). Fix 4's ``reserve`` flag (a
        plain boolean, not a page number or a count of anything) applies
        the *same* fixed reserve — ``_folio_reserve_px(DPI)``, imported
        directly from ``book_pdf_generator`` rather than reimplemented: it
        is a font-measurement helper, not FR-040's own formula, and this
        module's independent value is the geometric arithmetic below, not a
        second font metrics engine — to every pair alike, regardless of
        this pair's own page number or this book's own scale. ``reserve=
        False`` (the default) is the plain, no-reserve FR-040 number.
        """
        natural = min(
            STANDARD_CELL_MM,
            self.usable_width_mm / max(first.across, second.across),
            self.pair_height_mm / (first.down + second.down),
        )
        if not reserve:
            return natural
        reserve_px = _folio_reserve_px(DPI)
        if not reserve_px:
            return natural
        natural_cell_px = natural * DPI / 25.4
        usable_width_px = self.usable_width_mm * DPI / 25.4
        natural_spare_px = usable_width_px - second.across * natural_cell_px
        if natural_spare_px >= reserve_px:
            return natural
        reserve_mm = reserve_px * 25.4 / DPI
        return min(
            STANDARD_CELL_MM,
            (self.usable_width_mm - reserve_mm) / max(first.across, second.across),
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


def _pages_for_a_qualifying_run(length: int) -> int:
    """CARD-202's own chunking, over a run length alone: 4 at a time while at
    least 4 remain, then 2 at a time while at least 2 remain, then a lone 1
    if one is left over (owner decision, resolved 2026-10-08)."""
    pages = 0
    while length >= 4:
        pages += 1
        length -= 4
    while length >= 2:
        pages += 1
        length -= 2
    if length == 1:
        pages += 1
    return pages


def _expected_answer_pages(order: list[Puzzle]) -> int:
    """How many pages the answer section takes for ``order``.

    CARD-202: a puzzle small enough (width<=15, height<=20) packs with its
    same-level run instead of CARD-198's one page each; a level change or a
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
        qualifies = puzzle.columns <= 15 and puzzle.rows <= 20
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


def _expected_pages(
    sheet: Sheet, order: list[Puzzle]
) -> list[tuple[int, ...]] | None:
    """EC-027's walk, written out: the 1-based puzzle numbers of each page.

    ``reserve=True`` on every ``shared_cell_mm`` call below (CARD-204
    Fix 4): production's own ``puzzle_pages`` always passes
    ``compute_pair_layout`` the fixed folio reserve now, so this oracle
    must too, or it would silently disagree with every pair production
    actually commits to.

    ``None`` is returned when any offer this walk makes lands within a
    millionth of a millimetre of the 7.0 mm threshold — a verdict this
    module's floats cannot be trusted to share with the layout's exact
    fractions, and one disagreement would desynchronise every later page of
    the book.
    """
    pages: list[tuple[int, ...]] = []
    index = 0
    while index < len(order):
        first = order[index]
        second = order[index + 1] if index + 1 < len(order) else None
        if (
            second is not None
            and first.tier_of_record is not None
            and sheet.footer_carries_two_groups()
        ):
            if first.tier_of_record == second.tier_of_record:
                cell = sheet.shared_cell_mm(first, second, reserve=True)
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
    refused_on_footer = 0
    at_cap = below_cap = 0

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
    for case in range(3600):
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
        assert [entry.page_number for entry in plan] == list(range(3, 3 + len(plan))), label
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
                elif not sheet.footer_carries_two_groups():
                    # CARD-248: this trim's footer strip holds one group, not
                    # two, so no pair on it can carry both links.
                    refused_on_footer += 1
                else:
                    assert (
                        sheet.shared_cell_mm(members[0], follower, reserve=True)
                        < TWO_UP_MINIMUM_MM
                    ), label
                    refused_on_fit += 1
                continue

            paired += 1
            upper, lower = members
            assert upper.tier_of_record is not None, label
            assert upper.tier_of_record == lower.tier_of_record, label

            # One shared cell, FR-040's, inside [7.0, 7.5] mm.
            wanted = sheet.shared_cell_mm(upper, lower, reserve=True)
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

    # **Stated against the corpus that is actually built** (CARD-248 review,
    # Fix 3): 3600 books and 15994 pages, measured on this seed. These two
    # floors read ``850``/``3000`` until this fix — the figures from the 900
    # books the loop above built before this card grew it — which was never a
    # weakened guard (``paired >= 100`` and ``refused_on_footer >= 500`` both
    # fail at 900 books) but did read as though the corpus were a quarter of
    # its size. No minimum here is lowered.
    #
    # The book floor is 3600 less the ``near_threshold`` tolerance asserted at
    # the foot of this test, which is the only way a case leaves the loop
    # without counting. The page floor keeps about 6 % for a future geometry
    # change that moves the pairing share (pairing fewer pairs prints *more*
    # pages, so this floor is the safe direction). Both fail outright if the
    # corpus is ever shrunk back towards 900 books, which printed about 4000.
    assert books >= 3595, books
    assert pages >= 15000, pages
    # Both verdicts, and every reason a pair is refused, are in the corpus.
    assert paired >= 100, paired
    assert single >= 2500, single
    assert refused_on_tier >= 1000, refused_on_tier
    assert refused_on_fit >= 350, refused_on_fit
    # CARD-248's own refusal reason: this trim's footer carries one group, not
    # two. Asserted so the 6 x 9 sheet is really exercising it.
    assert refused_on_footer >= 500, refused_on_footer
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

        # The 2-page guide (CARD-201), the table of contents (CARD-200), a
        # divider per non-empty level, the puzzle pages, the SOLUTIONS
        # divider, one answer page per puzzle (CARD-198).
        assert len(interior) == (
            2 + toc_page_count + dividers + len(expected) + 1
            + _expected_answer_pages(printed)
        ), label

        # Which interior page each planned puzzle page landed on: pages 1-2
        # are the guide (CARD-201), pages 3..(2+toc_page_count) are the table
        # of contents (CARD-200), and each named level's run opens with a
        # divider page.
        numbers_of: list[int] = []
        page_number = 3 + toc_page_count
        opened: object = object()
        for group in expected:
            level = printed[group[0] - 1].tier_of_record
            if level != opened:
                opened = level
                if level is not None:
                    page_number += 1
            numbers_of.append(page_number)
            page_number += 1

        drawn = [
            [(drawing.columns, drawing.rows) for drawing in drawings_of(interior[number - 1])]
            for number in numbers_of
        ]
        assert drawn == [
            [(printed[n - 1].columns, printed[n - 1].rows) for n in numbers]
            for numbers in expected
        ], label
        # ... and therefore the print order, front to back, unchanged.
        assert [extent for page in drawn for extent in page] == [
            (puzzle.columns, puzzle.rows) for puzzle in printed
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


# ---------------------------------------------------------------------------
# CARD-204 Fix 2 (cycle-1 review F-1/F-3) — the reserve is the book's own
# scale, never a specific page number
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


#: A pair clear of the 7.0 mm floor even after Fix 4's fixed reserve is
#: subtracted: **23** columns x 6 rows, row- and column-clue depth 2
#: (``across`` = 25). Hand-verified here (``compute_pair_layout`` run
#: directly against this exact geometry, the same independent check
#: cycle-1/2's reviews made) rather than re-derived from this module's own
#: ``Sheet.shared_cell_mm``, which already shares production's formula and so
#: cannot catch a regression in it by agreeing with itself.
#:
#: **Re-chosen for CARD-222, and the window it sits in has closed.** It was
#: 24 columns (``across`` = 26) on CON-018's retired margins, where the
#: geometry-only cell was ``193.675 / 26 == 7.449`` mm and the reserved one
#: ``(193.675 - 9.144) / 26 == 7.097`` mm — both strictly between the 7.0 mm
#: floor and the 7.5 mm cap, so the reserve's whole effect was visible in the
#: pair's own cell. On the amended margins (usable width 190.5 mm) **no
#: ``across`` can do that any more**: the cap needs ``across >= 26``
#: (190.5 / 26 = 7.33) and the floor-with-reserve needs ``across <= 25``
#: ((190.5 - 9.144) / 25 = 7.25). The reserve is 9.144 mm — 4.8% of the
#: usable width — and the cap-to-floor window is 7% wide, so the two no
#: longer leave room for each other. This pair therefore sits at ``across``
#: 25, where the **cap** binds the unreserved cell (7.5 mm) and the reserve
#: still shows in the reserved one (7.254 mm), which is all the property
#: below needs: the same verdict and the same cell wherever the pair lands.
_BORDERLINE_ROW_CLUES = tuple((1, 1) for _ in range(6))
_BORDERLINE_COLUMN_CLUES = tuple((1, 1) for _ in range(23))

#: The pair's shared cell with no reserve: NFR-008's flat 7.5 mm cap, which
#: binds at this ``across`` (190.5 / 25 = 7.62 mm of page fit, above the cap).
_BORDERLINE_CELL_MM = 7.5

#: The same pair's cell **with** Fix 4's fixed reserve subtracted —
#: hand-derived independently (not imported from ``compute_pair_layout`` or
#: ``book_pdf_generator``), then cross-checked directly against
#: ``compute_pair_layout``. ``_folio_reserve_px`` measures 108 px at 300 DPI
#: (27 px per digit, the font's own widest digit, times
#: ``FOLIO_RESERVE_DIGITS`` = 4) == ``108 * 25.4 / 300 == 9.144`` mm;
#: ``(190.5 - 9.144) / 25 == 7.254239999999999...`` mm — below the cap, so the
#: reserve really is what decides this cell, and still above the 7.0 mm floor.
_RESERVE_PX = 108
_BORDERLINE_CELL_WITH_RESERVE_MM = 7.25424

#: The OLD (CARD-204 Fix 1/Fix 2/Fix 3 investigation's own) tightest pair —
#: 25 columns, ``across`` = 27, geometry-only cell ``193.675 / 27 ==
#: 7.173148148148147...`` mm — sits close enough to the 7.0 mm floor that
#: Fix 4's fixed 9.144 mm reserve pushes it *below* the floor in every
#: regime: ``(193.675 - 9.144) / 27 == 6.8345...`` mm. Kept here,
#: deliberately, to prove the invariant also holds in its "always refuses"
#: shape, not only its "always pairs, a bit smaller" one — the fixed
#: reserve must be scale-independent either way it lands.
_TIGHT_ROW_CLUES = tuple((1, 1) for _ in range(6))
_TIGHT_COLUMN_CLUES = tuple((1, 1) for _ in range(25))


def _borderline_pair(tier: str = "easy") -> tuple[Puzzle, Puzzle]:
    first = Puzzle(23, 6, _BORDERLINE_ROW_CLUES, _BORDERLINE_COLUMN_CLUES, tier)
    second = Puzzle(23, 6, _BORDERLINE_ROW_CLUES, _BORDERLINE_COLUMN_CLUES, tier)
    return first, second


def _tight_pair(tier: str = "easy") -> tuple[Puzzle, Puzzle]:
    first = Puzzle(25, 6, _TIGHT_ROW_CLUES, _TIGHT_COLUMN_CLUES, tier)
    second = Puzzle(25, 6, _TIGHT_ROW_CLUES, _TIGHT_COLUMN_CLUES, tier)
    return first, second


def test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber() -> None:
    """INV-010 (CARD-204 Fix 4, owner decision 2026-10-12, "fixed universal
    reserve"): a pair's own geometry and tier, plus one fixed, dpi-only
    constant, alone decide whether it pairs and at what cell — never the
    specific page number it happens to land on, and never the book's own
    total scale either.

    F-1 (cycle 1) reproduced the bug directly: the identical pair of
    puzzles paired at a 2-digit page and refused outright at a 3-digit page
    of the *same* book. Fix 2 narrowed that to a book-level reserve, which
    cycle 2's F-5 then reproduced one level up. Fix 3 removed the reserve
    mechanism entirely, which restored the invariant but silently
    reintroduced the folio-loss bug the reserve existed to fix (cycle-3
    F-7). Fix 4 restores the reserve as a **fixed, dpi-only** constant, so
    this test asserts the invariant in its final shape: the *same* pair, at
    the *same* (now reserve-shrunk) ``cell_mm``, in a 1-digit, a 2-digit,
    and a 3-digit book alike — and, independently of the sweep, confirms
    the *same* pair in the *same*-sized book pairs identically whether it
    is offered first or last (filler puzzles of a *different* tier move it
    between page 3 and a page dozens on, without ever being offered to it,
    since INV-010 forbids a mixed-tier pair outright). A second pair, tight
    enough that the fixed reserve pushes it below the 7.0 mm floor, proves
    the same invariant holds in its "always refuses" shape too.

    No ``hypothesis`` (CLAUDE.md): a small, fully enumerated sweep over
    three known book-scale boundaries rather than a random corpus, with the
    expected ``cell_mm`` an independent hand-derivation
    (``_BORDERLINE_CELL_WITH_RESERVE_MM``), verified directly against
    ``compute_pair_layout`` before this test was written rather than
    re-derived from this module's own ``Sheet.shared_cell_mm`` helper.
    """
    sheet = Sheet(*BOOK1)
    generator = BookPDFGenerator(sheet.book)

    # The two hand-derived cells below are worked out from this exact pixel
    # figure, so check it first: a font whose widest digit measured
    # differently would make both expectations wrong for a reason that has
    # nothing to do with the invariant under test, and this assertion says
    # so in one line instead of as an obscure cell_mm mismatch.
    assert _folio_reserve_px(DPI) == _RESERVE_PX, _folio_reserve_px(DPI)

    # (filler_count, the book's own max_page_number digit count). Every
    # regime pairs at the identical cell_mm (or refuses identically, for the
    # tight pair below) — the whole point of this test is that the
    # digit-count column no longer predicts anything about the verdict or
    # the cell, even though a reserve is now genuinely in effect.
    REGIMES = (
        (1, 1),
        (6, 2),
        (98, 3),
    )

    cases = 0
    for filler_count, digits in REGIMES:
        first, second = _borderline_pair()
        tight_first, tight_second = _tight_pair()
        fillers = [_filler("hard") for _ in range(filler_count)]

        early_order = [first, second] + fillers
        late_order = fillers + [first, second]
        tight_early_order = [tight_first, tight_second] + fillers
        tight_late_order = fillers + [tight_first, tight_second]
        assert len(early_order) == len(late_order)

        early_plan = generator.puzzle_pages([p.payload for p in early_order])
        late_plan = generator.puzzle_pages([p.payload for p in late_order])
        tight_early_plan = generator.puzzle_pages([p.payload for p in tight_early_order])
        tight_late_plan = generator.puzzle_pages([p.payload for p in tight_late_order])

        early_target = next(entry for entry in early_plan if entry.numbers[:1] == (1,))
        late_target = next(
            entry for entry in late_plan if filler_count + 1 in entry.numbers
        )
        tight_early_target = next(
            entry for entry in tight_early_plan if entry.numbers[:1] == (1,)
        )
        tight_late_target = next(
            entry for entry in tight_late_plan if filler_count + 1 in entry.numbers
        )

        # This regime really does carry the digit count it is named for —
        # otherwise the case below proves nothing about the boundary it
        # claims to exercise.
        max_page_number = 3 + len(early_order) - 1
        assert len(str(max_page_number)) == digits, (filler_count, max_page_number)

        # The pair lands on a different *actual* page number in the two
        # placements — otherwise this case would not test position
        # independence at all, only repeat the same call twice.
        assert early_target.page_number != late_target.page_number, (
            filler_count,
            early_target.page_number,
            late_target.page_number,
        )

        # The invariant: the pair always pairs, at the one reserve-shrunk
        # cell, regardless of the page number or the book's own total scale.
        for placement, target in (("early", early_target), ("late", late_target)):
            assert target.pair is not None, (filler_count, placement, target.page_number)
            assert abs(target.pair.cell_mm - _BORDERLINE_CELL_WITH_RESERVE_MM) < 1e-9, (
                filler_count,
                placement,
                target.pair.cell_mm,
            )
            # Strictly smaller than the fully-unreserved cell, by exactly
            # the fixed reserve — never a page/book-scale-dependent amount.
            assert target.pair.cell_mm < _BORDERLINE_CELL_MM, (filler_count, placement)

        # The direct form of the invariant: the two placements agree with
        # each other, not merely with the hand-derived expectation above.
        assert (early_target.pair is None) == (late_target.pair is None)
        assert abs(early_target.pair.cell_mm - late_target.pair.cell_mm) < 1e-9

        # The tight pair: the fixed reserve refuses it in *every* regime —
        # the invariant holds just as well when the verdict is "no" as when
        # it is "yes, a bit smaller".
        assert tight_early_target.pair is None, (filler_count, "early")
        assert tight_late_target.pair is None, (filler_count, "late")

        cases += 1

    assert cases == len(REGIMES)
