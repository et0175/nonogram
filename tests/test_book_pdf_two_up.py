"""CARD-127 — two puzzles to a page: the walk, the page, the bands (FR-040).

    AC-242 (INV-010)  TestBookPdf_TwoSmallSameTierNeighboursShareAPage
    AC-243 (INV-010)  TestBookPdf_TwelvePairSharesPageBelowStandardCell
    AC-244 (INV-010)  TestBookPdf_PairJustAboveTwoUpMinimumShares
    AC-245 (INV-010)  TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare
    AC-246 (INV-010)  TestBookPdf_FifteenPlusTwelveDoesNotPair
    AC-247 (INV-010)  TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare
    AC-248 (INV-010)  TestBookPdf_DifferentTiersNeverPair
    AC-249 (INV-010)  TestBookPdf_PairingNeverReordersToFindAPartner
    AC-250 (INV-010)  TestBookPdf_OddPuzzleOutPrintsAlone
    AC-251            TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand
    AC-378            TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow
                      (AC-252, which that class carried, is RETIRED 2026-10-18)

Every verdict is read off the **rendered interior**, never asked of the code
that produced it: how many pages the book has, how many drawings are on a page,
how big their cells are and where their top edges sit all come from the ink,
through ``tests/helpers/two_up_ink.py`` (which splits a two-up page and then
measures each half with CARD-116's ``page_ink``). The expected cells are FR-040
written out again here in floating-point millimetres — ``min(7.5 mm, usable
width / the wider drawing's columns, (trim height − top − bottom − two bands) /
both drawings' rows)`` — over CON-018's profile stated in inches. Nothing in
this module imports ``compute_pair_layout``, ``compute_layout`` or
``book_page_spec``.

A band is ink, and nothing in the dependency baseline turns ink back into
letters, so AC-251 does what CARD-117's band tests do: it renders the line this
card specifies through COMP-007's own header and compares the two bands' ink.
The comparison is on each band's **tight ink box** rather than on the strip it
sits in, because the lower slot's band starts wherever the pair's spare height
leaves it and the reference page's starts at the top margin — a comparison that
required them to agree to the pixel would be measuring the crop, not the words.
It carries the box's **left edge on the page** beside the glyphs (``_Ink``),
because a tight crop alone says what was set and not where: a band centred on
the trim's centre rather than on its slot's would be the same picture moved
sideways by (gutter − outside) / 2, and the glyph comparison would pass it.
The vertical placement is pinned by the millimetres the strips are cropped at.
"""

from __future__ import annotations

from typing import NamedTuple, Optional, Sequence

import numpy as np
import pytest
from PIL import Image

from nonogram import clues
from nonogram.admin.book_answer_key import Answer, plan_small_answer_pages
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import BookPDFGenerator, _folio_reserve_px
from nonogram.difficulty import tier_of_record
from nonogram.export import ExportPayload
from nonogram.export.pdf import render_pages
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.page_ink import drawing_of
from tests.helpers.two_up_ink import drawings_of

# --------------------------------------------------------------------------
# CON-018's Book 1 profile in millimetres, written out rather than imported —
# the same figures tests/test_book_pdf.py and tests/test_book_pdf_band.py use.
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
BOTTOM_MM = 0.47 * 25.4

#: The title band above each puzzle (TERM-028), and NFR-008's standard cell.
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5

#: FR-040's two-up minimum: two puzzles share a page only at this cell or more.
TWO_UP_MINIMUM_MM = 7.0

#: The page's usable width, and the height a page has left once it reserves a
#: band for each of **two** puzzles: 190.5 mm and 229.492 mm on Book 1 since
#: CON-018's 2026-10-17 margin amendment (193.675 mm and 236.35 mm before it).
USABLE_WIDTH_MM = BOOK1_WIDTH_MM - GUTTER_MM - OUTSIDE_MM
PAIR_HEIGHT_MM = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM

#: The footer strip a two-up page reserves since CARD-248, in device pixels,
#: and the height its two drawings are left with: a two-up page now carries
#: **one** footer strip holding both puzzles' QR groups and the page's folio,
#: so ``compute_pair_layout`` keeps ``INTERIOR_FOOTER_MM`` free below the
#: lower slot before it fits anything. 29.878 mm = 353 px, written out here
#: as this file writes every other figure out.
FOOTER_STRIP_PX = 353
RESERVED_PAIR_HEIGHT_MM = PAIR_HEIGHT_MM - FOOTER_STRIP_PX / (300 / 25.4)

#: **Every fixture below was re-chosen for that figure, and the boundary ACs
#: moved with it** — the same thing CARD-222 did to this file when CON-018's
#: margins moved (see ``_FIFTEEN``'s own note). 229.492 mm at FR-040's 7.0 mm
#: floor admitted at most 32 cells of combined drawing height; 199.605 mm
#: admits at most **28**. So AC-242's pair is one cell of gutter shallower,
#: AC-243's twelves are two cells shallower, and AC-244/AC-245's boundary
#: pair is 28/29 cells where it was 32/33. FR-040's own AC-242..AC-246 carry
#: the pre-CARD-248 figures and are owed a re-measurement at the architect
#: station (recorded in CARD-248's notes — this card does not edit the
#: registry), exactly as CARD-222 left AC-244/AC-245.

#: Device pixels per millimetre at the 300 DPI every book page is drawn at.
PX_PER_MM = 300 / 25.4

#: CARD-204 Fix 4's fixed, universal folio reserve, in device pixels —
#: ``_folio_reserve_px`` is a font-measurement helper, imported directly
#: rather than reimplemented a third time (the same precedent
#: ``tests/property/test_book_pairing.py`` set).
RESERVE_PX = _folio_reserve_px(300)

#: How close a measured cell has to be to the millimetres worked out here: one
#: device pixel is 0.085 mm, and each of the grid's edges is rounded to one.
CELL_TOLERANCE_MM = 0.05

#: A pixel darker than this (0..255 grey) is ink, as ``page_ink`` reads one.
INK_LEVEL = 128


# --------------------------------------------------------------------------
# The book and its puzzles
# --------------------------------------------------------------------------


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def _book() -> Book:
    """A book on CON-018's Book 1 profile, as a ``books`` row carries it."""
    return Book(
        book_id="book-127",
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


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> list[list[bool]]:
    """A grid whose row clues are ``row_depth`` deep and columns ``column_depth``.

    The two gutters are set **independently**, which is what several of these
    criteria are stated over (a 15x15 with a 5-deep column gutter beside a
    10x10 with a 3-deep one). Row 0 carries ``row_depth`` single cells with a
    gap between each, so it encodes to that many runs and no row is deeper;
    column 0 does the same down the page. They share the cell at the corner,
    which is one run of each, so neither count is disturbed.
    """
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


def _puzzle(
    columns: int = MIN_SIZE,
    rows: int = MIN_SIZE,
    depth: int = 4,
    column_depth: Optional[int] = None,
    tier: object = "easy",
    name: Optional[str] = "Snowflake",
    puzzle_id: str = "p",
) -> dict:
    """One book puzzle, in the shape the review service hands the generator.

    ``depth`` is the row-clue gutter's depth; ``column_depth`` the column-clue
    gutter's, defaulting to the same.
    """
    down_depth = depth if column_depth is None else column_depth
    grid = _grid(columns, rows, depth, down_depth)
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


def _interior(puzzles: Sequence[dict]) -> list[Image.Image]:
    """The book's interior in print order; ``pages[n - 1]`` is interior page ``n``."""
    return BookPDFGenerator(_book()).interior_pages(list(puzzles))


def _expected_answer_pages(puzzles: Sequence[dict]) -> int:
    """How many answer pages CARD-202's packing takes for ``puzzles``, in order.

    This module's own subject is FR-040 pairing, not CARD-202's packing rule
    (that rule has its own dedicated unit, property and byte-comparison
    coverage in ``tests/test_book_solved_answer_key.py`` and
    ``tests/property/test_book_answer_tiles.py``) — so the answer-page term of
    this module's page-count assertions reuses the production walk directly,
    rather than re-deriving it a second time for a file that is not testing it.
    """
    answers = [
        Answer(
            number=index + 1,
            width=puzzle["width"],
            height=puzzle["height"],
            level=tier_of_record(puzzle["difficulty_tier"]),
        )
        for index, puzzle in enumerate(puzzles)
    ]
    return len(plan_small_answer_pages(answers))


# --------------------------------------------------------------------------
# FR-040's arithmetic, written out here
# --------------------------------------------------------------------------


def _across(puzzle: dict) -> int:
    """The drawing's width in cells: the row-clue gutter plus the grid."""
    return max(len(clue) for clue in puzzle["clues_rows"]) + puzzle["width"]


def _down(puzzle: dict) -> int:
    """The drawing's height in cells: the column-clue gutter plus the grid."""
    return max(len(clue) for clue in puzzle["clues_cols"]) + puzzle["height"]


def _shared_cell_mm(first: dict, second: dict) -> float:
    """FR-040's shared cell for one pair on one Book 1 page, in millimetres."""
    return min(
        STANDARD_CELL_MM,
        USABLE_WIDTH_MM / max(_across(first), _across(second)),
        RESERVED_PAIR_HEIGHT_MM / (_down(first) + _down(second)),
    )


def _mm(pixels: float) -> float:
    return pixels / PX_PER_MM


def _interior_pages(*, puzzle_pages: int, answer_pages: int, levels: int = 1, toc_pages: int = 1) -> int:
    """The interior's page count: guide, levels, puzzle pages, divider, key.

    Written out as FR-043 defines the make-up, with every variable term named
    at the call site rather than left as a bare literal — because all of them
    move. Two-up pairing shortens the puzzle section (FR-040, what this module
    is about), and CARD-128 opens each non-empty level with a divider page.

    ``levels`` is how many of those the book has: **1** for the single-tier
    books most of this module uses, 2 where an AC needs two tiers, and 0 for a
    book whose rows carry no tier of record at all — an ungraded run has no
    name to print, so it opens no divider.

    ``answer_pages`` is the book's own drawable-puzzle count (CARD-198: one
    full solved page per puzzle, no packing) — named at each call site as
    what it is now, a puzzle count, not derived from the pairing this module
    is actually about.

    The guide's own term is **2** (CARD-201's 2-page "how to solve" tutorial,
    up from 1 before this card). ``toc_pages`` (CARD-200) is **1** for every
    book this module builds: all of them are 1-4 puzzles on Book 1's own
    trim, far under the roughly 40-entry-per-page capacity a table of
    contents has there.
    """
    return 2 + toc_pages + levels + puzzle_pages + 1 + answer_pages


# --------------------------------------------------------------------------
# Reading a page's make-up off its ink
# --------------------------------------------------------------------------


def _page_shapes(pages: Sequence[Image.Image], first: int, count: int) -> list[list[tuple[int, int]]]:
    """The ``(columns, rows)`` of every drawing on each of ``count`` puzzle pages.

    ``first`` is the 1-based interior position of the first of them — interior
    page 5 for a single-level book (CARD-200: the 1-page table of contents,
    up from page 4 before it; CARD-201: the 2-page guide is pages 1-2), whose
    page 4 is that level's divider. One inner list per page, in print
    order, each holding its drawings top to bottom — so the concatenation of
    the whole thing is the book's print order as the paper shows it.
    """
    return [
        [(drawing.columns, drawing.rows) for drawing in drawings_of(pages[number - 1])]
        for number in range(first, first + count)
    ]


class _Ink(NamedTuple):
    """A strip's ink: the tight crop, and where on the page it starts.

    The crop says *what* was set, ``left`` says *where* — the x of the leftmost
    ink pixel in the page's own pixels. Both are compared (``_same_ink``),
    because a tight crop is the same picture wherever it sits: a band centred
    on the trim's centre instead of on the slot's would be identical ink shifted
    by (gutter − outside) / 2, and every AC-251 assertion would still pass.
    """

    image: Image.Image
    left: int


def _ink(image: Image.Image, origin: int = 0) -> Optional[_Ink]:
    """``image`` cropped to its ink, or ``None`` when it carries none.

    ``origin`` is the crop's own x on the page, so ``left`` comes back in page
    pixels rather than in the strip's.
    """
    dark = np.asarray(image.convert("L")) < INK_LEVEL
    rows, columns = np.flatnonzero(dark.any(axis=1)), np.flatnonzero(dark.any(axis=0))
    if not rows.size:
        return None
    return _Ink(
        image.crop((columns[0], rows[0], columns[-1] + 1, rows[-1] + 1)),
        origin + int(columns[0]),
    )


#: How far inside the band's own 12 mm the strip compared below is taken. The
#: band's line is set at 5 mm, centred, so a millimetre off each end is white
#: whatever the line says — and it keeps the strip clear of the drawing's top
#: rule, which is centred on the band's lower edge and would otherwise be
#: counted as part of the band's ink.
_BAND_INSET_MM = 1.0

#: The same, at the band's **foot**, which needs more room since CARD-222: the
#: frame's header rule is drawn inside the band, an eighth of its depth above
#: the foot (1.5 mm on a 12 mm band), and that rule runs the full text width —
#: so a strip that reached it would compare the rule instead of the band's own
#: line, on every page and identically, which is exactly the measurement this
#: file exists to avoid. 2 mm clears the rule and its own stroke, and the
#: band's line still ends 1.5 mm above it.
_BAND_FOOT_INSET_MM = 2.0


def _band_ink(page: Image.Image, top_mm: float) -> Optional[_Ink]:
    """The ink of the 12 mm band starting ``top_mm`` down the trim (TERM-028).

    ``top_mm`` is worked out in millimetres by the caller, from CON-018's
    profile and FR-040's own geometry, never read off a layout. The strip runs
    the full width of the trim, so the ``left`` that comes back is the band's
    own placement across the page and not an artefact of the crop.
    """
    top = round((top_mm + _BAND_INSET_MM) * PX_PER_MM)
    bottom = round((top_mm + BAND_MM - _BAND_FOOT_INSET_MM) * PX_PER_MM)
    return _ink(page.crop((0, top, page.width, bottom)))


def _reference_band(
    puzzle: dict, page_number: int, identity: str, *, shift_px: int = 0
) -> Optional[_Ink]:
    """The ink COMP-007 sets for ``identity`` on this puzzle's own single page.

    The same payload the generator builds from the row, except that this test
    supplies the two header fields: no picture name (a puzzle page carries
    none, ADR-0037/R1) and the band line, written out by the caller. Its band
    is the 12 mm below the top margin, where a single page's always is.

    ``shift_px`` is **unused since CARD-224** and kept as the parameter it
    is, with its history: CARD-204 Fix 1 added it, Fix 3 reverted it, Fix 4
    restored it as a fixed amount (owner decision 2026-10-12, "fixed
    universal reserve") because a two-up page's lower slot alone was pulled
    :data:`RESERVE_PX` toward the gutter from its flush edge, and the band is
    centred *on the drawing* (``header_band``'s own ``center_x =
    (drawing_left + drawing_right) // 2``), so the lower band's title moved
    with it. CARD-224 centres every slot across the page's one usable width,
    so both slots' drawings — and therefore both bands — sit on the same
    column as a single page's, and every caller now passes no shift. The
    parameter stays because the next card to move a slot sideways will need
    exactly it, and the tests below assert the zero rather than dropping the
    comparison.
    """
    payload = ExportPayload(
        grid=puzzle["grid"],
        row_clues=tuple(tuple(clue) for clue in puzzle["clues_rows"]),
        column_clues=tuple(tuple(clue) for clue in puzzle["clues_cols"]),
        seed=0,
        mode="random",
        width=puzzle["width"],
        height=puzzle["height"],
        name=None,
        difficulty=identity,
    )
    blank, _ = render_pages(payload, page_spec=book_page_spec(_book(), page_number))
    ink = _band_ink(blank, TOP_MM)
    return ink if ink is None or not shift_px else ink._replace(left=ink.left + shift_px)


def _same_ink(first: Optional[_Ink], second: Optional[_Ink]) -> bool:
    """The same letters **in the same place across the page**.

    Both bands are measured on a page of the same parity, so a band the slot
    centred correctly and the same band on a single page start on the same
    pixel column; the left edges are compared exactly, like the glyphs.
    """
    if first is None or second is None:
        return False
    return (
        first.left == second.left
        and first.image.size == second.image.size
        and first.image.tobytes() == second.image.tobytes()
    )


# --------------------------------------------------------------------------
# AC-242 — two small same-tier neighbours share a page at the standard cell
# --------------------------------------------------------------------------

#: The pair AC-242, AC-251 and AC-252 are all stated over: two easy 10x10
#: puzzles with **3**-deep gutters both ways, so each drawing is 13 cells
#: square.
#:
#: **4-deep until CARD-248**, which reserves a footer strip out of the pair's
#: height: 28 cells no longer clear NFR-008's standard cell (they are exactly
#: the 7.13 mm AC-243 is about now), while 26 do — 199.605/26 = 7.68 mm, so
#: the cap still binds and this AC still states what it is about.
_SMALL_PAIR = dict(columns=10, rows=10, depth=3)


class TestBookPdf_TwoSmallSameTierNeighboursShareAPage:
    """AC-242 — two easy 10x10s with 3-deep gutters print on one page at 7.5 mm.

    Their combined drawing height is 26 cells, which the 199.605 mm a two-up
    page has left under CARD-248's footer strip fits at 7.68 mm — above
    NFR-008's standard cell, so the cap binds and the shared cell is 7.5 mm.
    (The AC's own 4-deep pair is 28 cells: 8.20 mm of the 229.492 mm a pair
    had before the strip, and 7.13 mm of what it has now — see
    ``RESERVED_PAIR_HEIGHT_MM``.)
    """

    def test_the_page_fit_this_pair_asks_for_is_above_the_standard_cell(self):
        """The arithmetic the AC names, before any page is drawn."""
        first = _puzzle(**_SMALL_PAIR)

        assert _down(first) == 13 and _across(first) == 13
        assert abs(RESERVED_PAIR_HEIGHT_MM / 26 - 7.6771) < 1e-3
        assert abs(_shared_cell_mm(first, first) - STANDARD_CELL_MM) < 1e-9

    def test_both_puzzles_print_on_one_page(self):
        puzzles = [_puzzle(**_SMALL_PAIR, puzzle_id="a"), _puzzle(**_SMALL_PAIR, puzzle_id="b")]
        pages = _interior(puzzles)

        # Guide, one shared puzzle page, divider, and the answer section:
        # since CARD-202 these two 10x10s (same tier, both qualifying) pack
        # onto one answer page too — a different saving from the puzzle
        # section's own pairing, computed independently of it.
        assert len(pages) == _interior_pages(
            puzzle_pages=1, answer_pages=_expected_answer_pages(puzzles)
        )
        assert _page_shapes(pages, 5, 1) == [[(10, 10), (10, 10)]]

    def test_both_slots_print_at_the_standard_cell(self):
        pages = _interior(
            [_puzzle(**_SMALL_PAIR, puzzle_id="a"), _puzzle(**_SMALL_PAIR, puzzle_id="b")]
        )

        upper, lower = drawings_of(pages[4])

        for slot in (upper, lower):
            assert abs(_mm(slot.cell) - STANDARD_CELL_MM) < CELL_TOLERANCE_MM, _mm(slot.cell)
        assert abs(upper.cell - lower.cell) <= 1, "one shared cell"

    def test_printed_alone_they_would_have_taken_two_pages(self):
        """The saving this AC is about: the same two puzzles, different tiers."""
        puzzles = [
            _puzzle(**_SMALL_PAIR, puzzle_id="a"),
            _puzzle(**_SMALL_PAIR, tier="medium", puzzle_id="b"),
        ]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles), levels=2
        )
        # Interior page 5 is the easy one, page 7 the medium one: each level
        # opens with a divider of its own (CARD-128).
        assert _page_shapes(pages, 5, 1) == [[(10, 10)]]
        assert _page_shapes(pages, 7, 1) == [[(10, 10)]]


# --------------------------------------------------------------------------
# AC-243 — a pair whose shared cell falls below the standard cell
# --------------------------------------------------------------------------


class TestBookPdf_TwelvePairSharesPageBelowStandardCell:
    """AC-243 — two easy 12x12s with 2-deep gutters share a page at 7.13 mm.

    28 cells of drawing height into the 199.605 mm CARD-248's footer strip
    leaves: the height fit binds, not the cap, so the pair prints at a cell
    the standard one never reaches.

    **4-deep until CARD-248.** That pair is 32 cells, which the strip puts at
    6.24 mm — under FR-040's floor, so it no longer shares a page at all (it
    is AC-246's case now, and ``TestTwoUpFooter_APairThatCannotFit...`` in
    ``tests/test_book_qr_slot.py`` states the whole refused band). Two cells
    shallower keeps this AC on the side of the boundary it is about.
    """

    PAIR = dict(columns=12, rows=12, depth=2)

    def test_both_puzzles_print_on_one_page_at_the_fitted_cell(self):
        puzzles = [_puzzle(**self.PAIR, puzzle_id="a"), _puzzle(**self.PAIR, puzzle_id="b")]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=1, answer_pages=_expected_answer_pages(puzzles)
        )
        assert _page_shapes(pages, 5, 1) == [[(12, 12), (12, 12)]]
        for slot in drawings_of(pages[4]):
            assert abs(_mm(slot.cell) - 7.13) < CELL_TOLERANCE_MM, _mm(slot.cell)

    def test_that_cell_is_the_199_605_mm_over_28_cells(self):
        first = _puzzle(**self.PAIR)

        assert _down(first) == 14
        assert abs(PAIR_HEIGHT_MM - 229.492) < 1e-9
        assert abs(RESERVED_PAIR_HEIGHT_MM - 199.6047) < 1e-3
        expected = _shared_cell_mm(first, first)
        assert abs(expected - RESERVED_PAIR_HEIGHT_MM / 28) < 1e-9
        assert abs(expected - 7.13) < CELL_TOLERANCE_MM

    def test_it_is_below_the_standard_cell_and_above_the_two_up_minimum(self):
        first = _puzzle(**self.PAIR)
        cell = _shared_cell_mm(first, first)

        assert TWO_UP_MINIMUM_MM <= cell < STANDARD_CELL_MM


# --------------------------------------------------------------------------
# AC-244 / AC-245 — the 7.0 mm boundary, one cell of clue gutter apart
# --------------------------------------------------------------------------

#: AC-244's pair: an easy 15x15 with a **1**-deep column-clue gutter followed
#: by an easy 10x10 with a 2-deep one — 16 + 12 = 28 cells down, 7.13 mm.
#:
#: **The boundary has moved twice, for two recorded reasons.** CON-018's
#: margins moved it first (2026-10-17, CARD-222): the AC's own pair is a
#: 3-deep 10x10 beside a 5-deep 15x15, 33 cells down, 7.16 mm on the old
#: margins and 6.95 mm on the amended ones, so that pair stopped sharing a
#: page and the partner was re-chosen one cell shallower. CARD-248's footer
#: strip has now moved it again: 229.492 mm admitted 32 cells at FR-040's
#: 7.0 mm floor and 199.605 mm admits 28, so the 15x15's own column gutter
#: comes down from 5 cells to 1 and the boundary pair is 28 cells against
#: AC-245's 29. The ACs are about the boundary, so each fixture is re-chosen
#: to sit on the side of it the AC names; FR-040's AC-244/AC-245 carry the
#: original figures and are owed a re-measurement at the architect station
#: (recorded in CARD-222's and now CARD-248's Worktree notes — neither card
#: edits the registry).
_FIFTEEN = dict(columns=15, rows=15, depth=5, column_depth=1)
_TEN = dict(columns=10, rows=10, depth=3, column_depth=2)

#: AC-245's: the same 15x15 with one more cell of column-clue gutter — 29 cells
#: down, 6.88 mm, under the minimum.
_FIFTEEN_DEEPER = dict(columns=15, rows=15, depth=5, column_depth=2)


class TestBookPdf_PairJustAboveTwoUpMinimumShares:
    """AC-244 — 28 cells of drawing height share a page at 7.13 mm."""

    def test_the_pair_prints_on_one_page(self):
        puzzles = [_puzzle(**_FIFTEEN, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=1, answer_pages=_expected_answer_pages(puzzles)
        )
        assert _page_shapes(pages, 5, 1) == [[(15, 15), (10, 10)]]

    def test_both_slots_print_at_the_shared_7_13_mm_cell(self):
        pages = _interior([_puzzle(**_FIFTEEN, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")])

        for slot in drawings_of(pages[4]):
            assert abs(_mm(slot.cell) - 7.13) < CELL_TOLERANCE_MM, _mm(slot.cell)

    def test_that_cell_is_28_cells_of_height_and_is_at_or_above_the_minimum(self):
        first, second = _puzzle(**_FIFTEEN), _puzzle(**_TEN)

        assert (_down(first), _down(second)) == (16, 12)
        cell = _shared_cell_mm(first, second)
        assert abs(cell - RESERVED_PAIR_HEIGHT_MM / 28) < 1e-9
        assert abs(cell - 7.13) < CELL_TOLERANCE_MM
        assert cell >= TWO_UP_MINIMUM_MM


class TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare:
    """AC-245 — one more cell of column-clue gutter, 6.88 mm, and they separate.

    One more than AC-244's own pair takes, which under CARD-248's footer strip
    is 29 cells rather than 33 (CON-018's amended margins had already taken it
    from 34 to 33): the partner is still the 2-deep 10x10 AC-244 uses, and the
    15x15's own column gutter is one cell deeper than AC-244's.
    """

    def test_the_two_puzzles_print_on_two_pages(self):
        puzzles = [_puzzle(**_FIFTEEN_DEEPER, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles)
        ), "guide, two puzzle pages, divider, the answer section"
        assert _page_shapes(pages, 5, 2) == [[(15, 15)], [(10, 10)]]

    def test_the_cell_that_pair_would_need_is_under_the_minimum(self):
        first, second = _puzzle(**_FIFTEEN_DEEPER), _puzzle(**_TEN)

        assert (_down(first), _down(second)) == (17, 12)
        cell = _shared_cell_mm(first, second)
        assert abs(cell - RESERVED_PAIR_HEIGHT_MM / 29) < 1e-9
        assert abs(cell - 6.88) < CELL_TOLERANCE_MM
        assert cell < TWO_UP_MINIMUM_MM

    def test_one_cell_of_gutter_is_the_whole_difference(self):
        """AC-244 and AC-245 differ by a single cell of column-clue gutter."""
        shallow, deeper = _puzzle(**_FIFTEEN), _puzzle(**_FIFTEEN_DEEPER)

        assert (shallow["width"], shallow["height"]) == (deeper["width"], deeper["height"])
        assert _down(deeper) - _down(shallow) == 1


# --------------------------------------------------------------------------
# AC-246 — a pair that misses the minimum by more than a rounding
# --------------------------------------------------------------------------


class TestBookPdf_FifteenPlusTwelveDoesNotPair:
    """AC-246 — 32 cells of drawing height (6.24 mm) print on two pages.

    **The same two puzzles as before CARD-248**; it is the figures that move.
    The 15x15's column gutter came down to 1 cell with AC-244's fixture (see
    ``_FIFTEEN``), so the pair is 32 cells rather than 36, and the footer
    strip puts 32 cells at 6.24 mm instead of the 6.37 mm the pre-strip
    229.492 mm gave 36 — still well under FR-040's floor, which is what this
    AC is about.
    """

    TWELVE = dict(columns=12, rows=12, depth=4, column_depth=4)

    def test_the_two_puzzles_print_on_two_pages(self):
        puzzles = [_puzzle(**_FIFTEEN, puzzle_id="a"), _puzzle(**self.TWELVE, puzzle_id="b")]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles)
        )
        assert _page_shapes(pages, 5, 2) == [[(15, 15)], [(12, 12)]]

    def test_the_cell_that_pair_would_need_is_6_24_mm(self):
        first, second = _puzzle(**_FIFTEEN), _puzzle(**self.TWELVE)

        assert _down(first) + _down(second) == 32
        cell = _shared_cell_mm(first, second)
        assert abs(cell - 6.24) < CELL_TOLERANCE_MM, cell
        assert cell < TWO_UP_MINIMUM_MM


# --------------------------------------------------------------------------
# AC-247 — the width term refuses a pair the height would have allowed
# --------------------------------------------------------------------------


class TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare:
    """AC-247 — a 22-wide drawing 28 cells across cannot hold 7.0 mm.

    190.5 mm of usable width over 28 cells is 6.80 mm, so the pair is
    refused on **width** although its combined height fits comfortably — the
    case that a fit measured down the page alone would wave through.
    """

    WIDE = dict(columns=22, rows=10, depth=6, column_depth=2)

    def test_the_two_puzzles_print_on_two_pages(self):
        puzzles = [_puzzle(**self.WIDE, puzzle_id="a"), _puzzle(**_TEN, puzzle_id="b")]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles)
        )
        assert _page_shapes(pages, 5, 2) == [[(22, 10)], [(10, 10)]]

    def test_the_height_would_have_fitted_and_the_width_is_what_refuses(self):
        wide, small = _puzzle(**self.WIDE), _puzzle(**_TEN)

        assert _across(wide) == 28
        assert USABLE_WIDTH_MM / 28 < TWO_UP_MINIMUM_MM
        assert abs(USABLE_WIDTH_MM / 28 - 6.80) < CELL_TOLERANCE_MM
        # The height term on its own would have allowed a 7.0 mm cell — the
        # footer strip included, so the width really is the only refusal.
        assert RESERVED_PAIR_HEIGHT_MM / (_down(wide) + _down(small)) > TWO_UP_MINIMUM_MM
        assert _shared_cell_mm(wide, small) < TWO_UP_MINIMUM_MM


# --------------------------------------------------------------------------
# AC-248 — tiers first: a pair that fits but is not the same level
# --------------------------------------------------------------------------


class TestBookPdf_DifferentTiersNeverPair:
    """AC-248 — the book's last easy and first medium never share a page.

    Both are 10x10 with 4-deep gutters, so they are the pair of AC-242 in every
    respect but their tier. The page they do not share is the proof that the
    tier is consulted before the fit.
    """

    def test_the_easy_and_the_medium_print_on_two_pages(self):
        puzzles = [
            _puzzle(**_SMALL_PAIR, tier="easy", puzzle_id="easy"),
            _puzzle(**_SMALL_PAIR, tier="medium", puzzle_id="medium"),
        ]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles), levels=2
        )
        assert _page_shapes(pages, 5, 1) == [[(10, 10)]]
        assert _page_shapes(pages, 7, 1) == [[(10, 10)]]

    def test_the_same_two_drawings_do_share_a_page_at_one_tier(self):
        """The control: only the tier changed between this and the AC's book."""
        puzzles = [
            _puzzle(**_SMALL_PAIR, tier="easy", puzzle_id="one"),
            _puzzle(**_SMALL_PAIR, tier="easy", puzzle_id="two"),
        ]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=1, answer_pages=_expected_answer_pages(puzzles)
        )

    @pytest.mark.parametrize(
        "first_tier, second_tier",
        [
            ("easy", "Easy"),
            ("EASY", "easy"),
            ("hard", "guess"),
            ("Medium", "medium"),
        ],
    )
    def test_two_spellings_of_one_tier_are_one_tier(self, first_tier, second_tier):
        """ADR-0031's tier of record, not the string: "easy" and "Easy" pair, and
        so do "hard" and ADR-0031/R3's retired "guess"."""
        puzzles = [
            _puzzle(**_SMALL_PAIR, tier=first_tier, puzzle_id="one"),
            _puzzle(**_SMALL_PAIR, tier=second_tier, puzzle_id="two"),
        ]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=1, answer_pages=_expected_answer_pages(puzzles)
        )

    @pytest.mark.parametrize("tier", [None, "", "extreme", 17])
    def test_a_row_with_no_tier_of_record_never_pairs(self, tier):
        """A puzzle whose stored grade is not a tier has no tier, so it has no
        tier equal to its neighbour's — not even another ungraded row's."""
        puzzles = [
            _puzzle(**_SMALL_PAIR, tier=tier, puzzle_id="one"),
            _puzzle(**_SMALL_PAIR, tier=tier, puzzle_id="two"),
        ]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles), levels=0
        )


# --------------------------------------------------------------------------
# AC-249 / AC-250 — the walk goes forward, in order, and leaves no gap
# --------------------------------------------------------------------------


class TestBookPdf_PairingNeverReordersToFindAPartner:
    """AC-249 — A, B, C with A and C a fitting pair still prints three pages.

    A and C are the two halves of AC-242's page. B, an easy 20x20 with 8-deep
    gutters, fits with neither. A book that moved C up beside A would save a
    page and silently overrule the order the owner arranged (INV-009).
    """

    BIG = dict(columns=20, rows=20, depth=8, column_depth=8)

    def _book_order(self):
        return [
            _puzzle(**_SMALL_PAIR, puzzle_id="A"),
            _puzzle(**self.BIG, puzzle_id="B"),
            _puzzle(**_SMALL_PAIR, puzzle_id="C"),
        ]

    def test_the_three_puzzles_print_on_three_pages_in_order(self):
        puzzles = self._book_order()
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=3, answer_pages=_expected_answer_pages(puzzles)
        ), "guide, three puzzle pages, divider, the answer section"
        assert _page_shapes(pages, 5, 3) == [[(10, 10)], [(20, 20)], [(10, 10)]]

    def test_a_and_c_would_have_fitted_together(self):
        """The saving the walk declines to take, stated as the AC states it."""
        a, b, c = self._book_order()

        assert _shared_cell_mm(a, c) >= TWO_UP_MINIMUM_MM
        assert _shared_cell_mm(a, b) < TWO_UP_MINIMUM_MM
        assert _shared_cell_mm(b, c) < TWO_UP_MINIMUM_MM

    def test_moving_c_next_to_a_is_what_would_have_paired_them(self):
        """The control: the same three puzzles in an order that does pair."""
        a, b, c = self._book_order()

        puzzles = [a, c, b]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles)
        ), "one page saved in the puzzle section; the answer section is its own count"
        assert _page_shapes(pages, 5, 2) == [[(10, 10), (10, 10)], [(20, 20)]]


class TestBookPdf_OddPuzzleOutPrintsAlone:
    """AC-250 — three fitting same-tier neighbours make a pair and a single."""

    def _three(self):
        return [_puzzle(**_SMALL_PAIR, puzzle_id=name) for name in ("one", "two", "three")]

    def test_puzzles_one_and_two_share_a_page_and_three_prints_alone(self):
        puzzles = self._three()
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles)
        ), "guide, two puzzle pages, divider, the answer section"
        assert _page_shapes(pages, 5, 2) == [[(10, 10), (10, 10)], [(10, 10)]]

    def test_the_third_page_is_a_single_puzzle_page(self):
        """Interior page 6 carries one drawing, at the cell a single page gives
        a 10x10 with 4-deep gutters: the standard cell."""
        pages = _interior(self._three())

        (alone,) = drawings_of(pages[5])

        assert (alone.columns, alone.rows) == (10, 10)
        assert abs(_mm(alone.cell) - STANDARD_CELL_MM) < CELL_TOLERANCE_MM

    def test_a_fourth_puzzle_joins_the_odd_one_out(self):
        """The walk resumes at the puzzle left alone, so a fourth pairs with it."""
        puzzles = self._three() + [_puzzle(**_SMALL_PAIR, puzzle_id="four")]
        pages = _interior(puzzles)

        assert len(pages) == _interior_pages(
            puzzle_pages=2, answer_pages=_expected_answer_pages(puzzles)
        ), "guide, two shared puzzle pages, divider, the answer section"
        assert _page_shapes(pages, 5, 2) == [
            [(10, 10), (10, 10)],
            [(10, 10), (10, 10)],
        ]


# --------------------------------------------------------------------------
# AC-251 — each slot under its own band, numbered in print order
# --------------------------------------------------------------------------


class TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand:
    """AC-251 — the upper band reads "Puzzle 1 · Easy", the lower "Puzzle 2 · Easy".

    The two lines are written out here, set through COMP-007's own header on a
    single page of the same book, and compared with the ink each band of the
    two-up page carries. A band saying anything else — the wrong number, a
    stored ``"easy"`` unlabelled, the picture's title — is different ink.
    """

    #: Where each band starts, in millimetres down the trim. The upper band is
    #: where every single page's is, the top margin. The lower one is worked
    #: out from the bottom up: the lower drawing's 13 cells at the 7.5 mm
    #: shared cell end on the **footer rule** — one 29.878 mm strip above the
    #: bottom margin since CARD-248, where they used to end on the margin
    #: itself — and its band is the 12 mm above them:
    #: 279.4 − 11.938 − 29.887 − 97.5 − 12 = 128.075 mm.
    UPPER_BAND_TOP_MM = TOP_MM
    LOWER_BAND_TOP_MM = (
        BOOK1_HEIGHT_MM
        - BOTTOM_MM
        - FOOTER_STRIP_PX / PX_PER_MM
        - 13 * STANDARD_CELL_MM
        - BAND_MM
    )

    def _page(self):
        puzzles = [
            _puzzle(**_SMALL_PAIR, puzzle_id="one"),
            _puzzle(**_SMALL_PAIR, puzzle_id="two"),
        ]
        pages = _interior(puzzles)
        assert len(pages) == _interior_pages(
            puzzle_pages=1, answer_pages=_expected_answer_pages(puzzles)
        ), "the pair does share a page"
        return pages[4]  # interior page 5

    def test_the_lower_band_sits_where_the_pair_leaves_it(self):
        """The millimetres the crops below are taken at, stated before use."""
        assert abs(self.LOWER_BAND_TOP_MM - 128.075) < 1e-3

    def test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two(self):
        page = self._page()
        puzzle = _puzzle(**_SMALL_PAIR)

        upper = _band_ink(page, self.UPPER_BAND_TOP_MM)
        lower = _band_ink(page, self.LOWER_BAND_TOP_MM)

        assert upper is not None, "the upper band is blank"
        assert lower is not None, "the lower band is blank"
        assert _same_ink(upper, _reference_band(puzzle, 5, "Puzzle 1 · Easy"))
        # CARD-224: both slots are centred across the page's one usable
        # width, so the lower band sits in the same column as a single page's
        # — no shift. (Until this card the lower slot was pulled RESERVE_PX
        # toward the gutter by CARD-204 Fix 4's folio reserve, and this
        # comparison carried that offset; the reserve now narrows the fit
        # only. RESERVE_PX is asserted non-trivial below so "no shift" is a
        # measurement rather than a tautology.)
        assert RESERVE_PX > 1, RESERVE_PX
        assert _same_ink(lower, _reference_band(puzzle, 5, "Puzzle 2 · Easy"))

    def test_the_two_bands_are_not_the_same_line(self):
        """The measurement has teeth: one band is not the other's ink."""
        page = self._page()

        assert not _same_ink(
            _band_ink(page, self.UPPER_BAND_TOP_MM),
            _band_ink(page, self.LOWER_BAND_TOP_MM),
        )

    def test_neither_band_carries_the_pictures_title(self):
        """ADR-0037/R1 on a two-up page: rename both pictures and the page is
        identical, pixel for pixel."""
        named = _interior(
            [
                _puzzle(**_SMALL_PAIR, name="Snowflake", puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, name="Snowflake", puzzle_id="two"),
            ]
        )
        renamed = _interior(
            [
                _puzzle(**_SMALL_PAIR, name="Iguanodon Skeleton", puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, name="Pterodactyl", puzzle_id="two"),
            ]
        )

        assert named[4].tobytes() == renamed[4].tobytes()
        # The control: the answer pages, which do carry the title, differ.
        assert named[6].tobytes() != renamed[6].tobytes()

    def test_the_numbers_follow_the_pages_before_this_one(self):
        """Puzzle numbers are 1..n in print order, whatever the pages hold: a
        two-up page after a single page carries 2 and 3, not 1 and 2.

        All three are easy, so they are one level and the single page really
        does come before the pair (INV-009): a puzzle of another tier would be
        printed behind its own divider, in its own level, wherever it was
        submitted (CARD-128). The pair is therefore interior page 6 (CARD-200:
        up from 5, the table of contents' own page; CARD-201: up from 4
        before that) — the 2-page guide (1-2), the TOC (3), the "Easy"
        divider 4, the 15x15 alone on 5 — and an even, left-hand page, which
        is what the reference bands (``_reference_band(puzzle, 6, ...)``) are
        laid out on.
        """
        pages = _interior(
            [
                _puzzle(**_FIFTEEN_DEEPER, puzzle_id="alone"),
                _puzzle(**_SMALL_PAIR, puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, puzzle_id="two"),
            ]
        )
        assert _page_shapes(pages, 5, 2) == [[(15, 15)], [(10, 10), (10, 10)]]
        puzzle = _puzzle(**_SMALL_PAIR)

        page = pages[5]  # interior page 6, the two-up page
        assert _same_ink(
            _band_ink(page, self.UPPER_BAND_TOP_MM),
            _reference_band(puzzle, 6, "Puzzle 2 · Easy"),
        )
        # CARD-224: centred, so no shift on this EVEN/left-hand page either
        # — the mirror of page 5's ODD case above (see that comment for what
        # the shift used to carry).
        assert _same_ink(
            _band_ink(page, self.LOWER_BAND_TOP_MM),
            _reference_band(puzzle, 6, "Puzzle 3 · Easy"),
        )


# --------------------------------------------------------------------------
# AC-378 — the upper slot's drawing does NOT start on the single page's row
# (AC-252, which claimed it did, is retired — see the class docstring)
# --------------------------------------------------------------------------


class TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow:
    """AC-378 — the two top pixel rows differ **by design**, and the difference
    is asserted rather than tolerated.

    **What this replaces.** Until CARD-224, EC-022's fixed offset — top margin
    plus band — was where every puzzle page of a book put its drawing's top
    edge, and a two-up page's upper slot was not an exception; AC-252 stated
    that coincidence. FR-032's amendment of 2026-10-17 made a *single* page's
    drawing float at 42% of its puzzle area's spare height (AC-366/AC-367)
    while a two-up slot's stayed at the foot of its own slot's band, so the two
    rows cannot coincide except by accident. **AC-252 is RETIRED (2026-10-18):**
    it is the same retired claim as AC-190, the fixed top edge, seen from the
    two-up page — the 2026-10-17 propagation pass retired AC-190 under FR-032
    but did not reach AC-252, which lives under FR-040. It cannot be rescued by
    floating the upper slot in CARD-226 either: a slot's spare is not a page's
    spare, so 42% of each still lands on different rows. The claim is wrong,
    not merely early.

    **So this is a positive test, not an ``xfail`` of the retired claim.** A
    strict ``xfail`` is *green* in a suite, which would let a merge gate pass
    while the test still asserted the old geometry — the CARD-172 shape, a card
    gated against a false claim. AC-378 names this class as the control that
    the two rows are deliberately different today, and it fails loudly in both
    directions a "fix" could take:

    * pin a single page's drawing back to the band's foot (AC-190's retired
      placement) and the gap measured below collapses to zero;
    * float the upper slot *without* splitting the page and the gap shrinks
      instead.

    Each gets its own message, so a red test says which of the two happened.

    **What will legitimately change this test: AC-379 and CARD-226.** That card
    splits the two-up page into two slots with aligned bottoms, after which
    each slot's drawing floats at 42% of *its own* spare — a different row
    again, and still not the single page's, which is why AC-379 is owed to that
    card rather than claimed here. A reader who finds this test red should first
    check whether they are doing CARD-226's work; if not, one of the two
    "fixes" above is what happened.

    The two surviving siblings state the rest of AC-378: the upper slot's own
    row is the top margin plus the band, and the two pages print different
    cells. The same gap is measured from the *layout* rather than the ink in
    ``tests/test_layout_two_up.py::TestPairLayout_UpperSlotSitsAtItsOwnBandFoot``.
    """

    BIG = dict(columns=20, rows=20, depth=8, column_depth=8)

    #: CARD-222's puzzle area on Book 1 — the header rule's row down to the
    #: footer rule's — in millimetres, written out here as this file writes
    #: every other figure out rather than read back from ``interior_frame``.
    #: The header rule is drawn inside the band, an eighth of its depth above
    #: its foot (the same 1.5 mm ``_BAND_FOOT_INSET_MM`` above is stated
    #: against), and the footer hairline sits one footer strip above the bottom
    #: margin.
    AREA_TOP_MM = TOP_MM + BAND_MM * (1 - 1 / 8)
    AREA_BOTTOM_MM = BOOK1_HEIGHT_MM - BOTTOM_MM - FOOTER_STRIP_PX / PX_PER_MM

    #: FR-032's 42% as amended 2026-10-17 — the owner's optical figure ("which
    #: looks centred once the header sits above it"), written out rather than
    #: imported, so a build that "improved" it to 0.5 fails here too, exactly
    #: as it does in AC-2's own class.
    SPARE_ABOVE = 0.42

    #: The gap between the two top rows on this fixture, in device pixels
    #: (7.96 mm). Pinned as a literal *beside* the derivation in the test
    #: below, so a drift has to move two independent answers to stay green.
    ROW_GAP_PX = 94

    #: How far inside each of the area's two rules the ink is read, in device
    #: pixels. Each rule is stroked from its own boundary row, so a crop on the
    #: boundary itself would report the rule as the drawing's ink; a heavy rule
    #: is at most 6 px at 300 DPI, and AC-3's ink test pins every drawing on
    #: these two pages clear of both rules by far more than that.
    _AREA_INSET_PX = 6

    def _pages(self):
        """The two-up page (interior 5) and the single page after it (6).

        All three puzzles are easy, so the book is one level and the two pages
        this AC compares are consecutive. The 20x20 used to be medium, which
        since CARD-128 would put a divider between them and move it to page 7
        — a difference of no interest to a criterion about a drawing's top
        edge, and the tier was never what kept it from pairing: it is 28 cells
        tall beside a 14-cell drawing, far under the 7.0 mm two-up minimum.
        """
        pages = _interior(
            [
                _puzzle(**_SMALL_PAIR, puzzle_id="one"),
                _puzzle(**_SMALL_PAIR, puzzle_id="two"),
                _puzzle(**self.BIG, puzzle_id="big"),
            ]
        )
        assert _page_shapes(pages, 5, 2) == [[(10, 10), (10, 10)], [(20, 20)]]
        return pages

    @classmethod
    def _ink_bands(cls, page: Image.Image) -> tuple[float, float]:
        """``(above, below)`` in millimetres — the empty bands the puzzle area
        is left with above and below the drawing's outermost ink.

        The book-page twin of ``tests/test_book_puzzle_frame.py``'s
        ``_area_ink_box``, which AC-2 measures the same 42% with. That helper
        reads a ``render_image`` page, which carries the drawing and nothing
        else, so it can crop to the area's own boundaries; a *generated*
        interior page really has the frame's two rules drawn on it, each
        stroked from its boundary row, so the same crop would start on the
        header rule and report the rule as the ink. Cropping
        :data:`_AREA_INSET_PX` inside each rule removes both.

        What comes back is the drawing's **ink**, stroke overhang included, on
        both sides alike. ``drawing_of``'s ``top`` and ``grid_bottom`` are each
        a rule's *first* ink row — deliberate there, because it makes the
        printed cell a rule-to-rule pitch, and asymmetric here: it would
        understate the span by one heavy rule, 2% of a 22 mm spare, against a
        ratio stated to 0.5%.
        """
        top_px = round(cls.AREA_TOP_MM * PX_PER_MM) + cls._AREA_INSET_PX
        bottom_px = round(cls.AREA_BOTTOM_MM * PX_PER_MM) - cls._AREA_INSET_PX
        dark = np.asarray(page.convert("L")) < INK_LEVEL
        rows = np.flatnonzero(dark[top_px : bottom_px + 1].any(axis=1))
        assert rows.size, "the puzzle area carries no ink at all"
        return (
            _mm(top_px + int(rows.min())) - cls.AREA_TOP_MM,
            cls.AREA_BOTTOM_MM - _mm(top_px + int(rows.max())),
        )

    def _predicted_gap_mm(self, single) -> float:
        """The gap the two placements predict, in millimetres: the single
        page's floated top edge less the upper slot's band foot.

        Both terms are this file's own millimetres — CON-018's profile, the
        42% and the cell read back off the drawn grid — with no layout
        function on either side of the comparison.
        """
        depth_mm = _down(_puzzle(**self.BIG)) * _mm(single.cell)
        spare_mm = (self.AREA_BOTTOM_MM - self.AREA_TOP_MM) - depth_mm
        assert spare_mm > 20.0, (spare_mm, "this page must have real spare")
        return self.AREA_TOP_MM + self.SPARE_ABOVE * spare_mm - (TOP_MM + BAND_MM)

    def test_the_two_top_rows_differ_by_the_single_pages_own_float(self):
        """AC-378's own claim: the two rows are 94 px — 7.96 mm — apart, which
        is the figure the two placements predict, and not merely unequal."""
        pages = self._pages()

        upper, lower = drawings_of(pages[4])
        single = drawing_of(pages[5])

        assert lower.top > upper.top, "the lower slot is a second drawing below it"

        gap_px = single.top - upper.top
        assert gap_px > 0, (
            gap_px,
            "the single page's drawing must sit BELOW the upper slot's: an "
            "equal row means a single page was pinned back to the band's foot "
            "- AC-190's retired placement, AC-252's claim - which AC-379's "
            "slot split would not do, since that moves the SLOT, not the page",
        )

        predicted_mm = self._predicted_gap_mm(single)
        assert _mm(gap_px) == pytest.approx(predicted_mm, abs=0.2), (
            gap_px,
            predicted_mm,
            "the gap is not the one the two placements predict: a SMALLER gap "
            "means the upper slot started floating without the page being "
            "split - AC-379 / CARD-226 is the change that may legitimately do "
            "that - and any other value that the single page's own ratio moved",
        )
        assert gap_px == pytest.approx(self.ROW_GAP_PX, abs=2), (gap_px, predicted_mm)

    def test_the_single_page_floats_at_42_percent_of_its_own_spare(self):
        """*Why* the single page's row is where it is — 0.42 of the puzzle
        area's spare above the drawing and 0.58 below, measured off the ink the
        way AC-2's own class measures it."""
        pages = self._pages()

        above, below = self._ink_bands(pages[5])
        spare = above + below

        assert spare > 20.0, (above, below, "this page must have real spare")
        assert above / spare == pytest.approx(self.SPARE_ABOVE, abs=0.005), (above, below)
        assert below / spare == pytest.approx(1 - self.SPARE_ABOVE, abs=0.005), (above, below)

    def test_the_control_the_retired_fixed_top_edge_would_share_the_row(self):
        """The control that can fail (ADR-0039/R1): AC-252's own geometry — a
        single page's drawing at the band's foot, where every drawing sat
        before this card — fails both assertions above.

        Same two pages, same arithmetic, with only the single page's placement
        replaced by the retired one, so what the greens above show is this
        card's placement and not the checks' indifference.
        """
        pages = self._pages()
        upper, _ = drawings_of(pages[4])
        single = drawing_of(pages[5])

        # AC-190's retired top edge: the band's foot, on every page and parity.
        retired_gap_mm = (TOP_MM + BAND_MM) - _mm(upper.top)
        assert abs(retired_gap_mm) < 0.2, (
            retired_gap_mm,
            "AC-252's placement really is the upper slot's own row",
        )
        assert retired_gap_mm != pytest.approx(self._predicted_gap_mm(single), abs=0.2), (
            "the retired fixed top edge would pass the gap assertion"
        )

        # And the band it would leave above the drawing is 0.07 of the spare.
        above, below = self._ink_bands(pages[5])
        retired_above = (TOP_MM + BAND_MM) - self.AREA_TOP_MM
        assert abs(retired_above / (above + below) - self.SPARE_ABOVE) > 0.1, (
            retired_above,
            above + below,
            "the retired fixed top edge would pass the 42% assertion",
        )

    def test_that_row_is_the_top_margin_plus_the_band(self):
        pages = self._pages()

        upper, _ = drawings_of(pages[4])

        assert abs(_mm(upper.top) - (TOP_MM + BAND_MM)) <= _mm(0.5) + 1e-9

    def test_the_two_pages_really_do_print_different_cells(self):
        """The negative control: two rows differing is not two identical pages.

        Written as "a shared top edge is not two identical pages" while
        AC-252 claimed the rows coincided. AC-252 is retired (AC-378); the
        control itself is unchanged and still earns its place -- the gap
        assertion above would pass on two renderings of the SAME puzzle, so
        something has to say the pages differ in their cells too.
        """
        pages = self._pages()

        upper, _ = drawings_of(pages[4])
        single = drawing_of(pages[5])

        assert abs(upper.cell - single.cell) > 1


# --------------------------------------------------------------------------
# The two copies of the export's header-fitting ratios are pinned equal
# --------------------------------------------------------------------------


def test_a_two_up_band_is_fitted_by_the_exports_own_header_ratios() -> None:
    """``_set_band``'s shrink-to-fit is COMP-007's, not a second tuning.

    ``book_pdf_generator`` restates ``pdf``'s two header ratios rather than
    importing them, because they are private to that module and G-3 forbids
    widening its surface. The restatement is only safe while the two agree: if
    COMP-007 retuned its header fitting, a band drawn on a two-up page and the
    same band drawn on a single page would start shrinking at different widths,
    and no AC above would notice — "Puzzle 1 · Easy" never reaches the shrink
    branch, so the ink comparisons never exercise these numbers.

    Importing the private names is legal here and nowhere else: the test tree
    is where the project cross-checks a deliberate reimplementation against its
    original (CLAUDE.md, the ``clues.encode_line`` precedent).
    """
    from nonogram.admin import book_pdf_generator
    from nonogram.export import pdf

    assert (
        book_pdf_generator._BAND_WIDTH_RATIO,
        book_pdf_generator._MIN_BAND_FONT_RATIO,
    ) == (pdf._HEADER_WIDTH_RATIO, pdf._MIN_HEADER_FONT_RATIO)


# --------------------------------------------------------------------------
# The extents these criteria are stated over are the supported ones
# --------------------------------------------------------------------------


def test_the_measured_extents_are_inside_con_011() -> None:
    """Every grid above is one the tool supports (CON-011)."""
    for shape in (_SMALL_PAIR, _FIFTEEN, _FIFTEEN_DEEPER, _TEN,
                  dict(columns=12, rows=12), dict(columns=22, rows=10),
                  dict(columns=20, rows=20)):
        assert MIN_SIZE <= shape["columns"] <= MAX_SIZE
        assert MIN_SIZE <= shape["rows"] <= MAX_SIZE
