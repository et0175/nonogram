"""CARD-223 — the QR code moves into the footer's **outer** corner, with a
caption and a typed link (the owner's artifact "Puzzle page layout",
2026-10-14, issue 1).

    AC-1  TestBookQrSlot_SitsAtTheOuterBottomCorner
    AC-2  TestBookQrSlot_NeverPlacesInkOnTheGutterSide
    AC-3  TestBookQrSlot_CarriesItsCaptionAndLink   (G-2 lives here too)
    AC-4  TestBookQrSlot_IsTwoCentimetresSquare
    AC-5  TestBookQrSlot_YieldsRatherThanCollide
    AC-6  TestBookQrSlot_IsStillThePlaceholderGlyph
          TestBookQrSlot_TheGutterSidePlacementIsGone   (item 4, the removal)

**CARD-248's own classes live at the foot of this file**, because they are
about the same four marks on a page kind that had none of them:

    AC-1  TestTwoUpFooter_CarriesBothPuzzlesLinks
    AC-2  TestTwoUpFooter_EachGroupCarriesItsOwnSlotsLink
    AC-3  TestTwoUpFooter_EachGroupNamesItsPuzzleNumber
    AC-4  TestTwoUpFooter_NeverPlacesInkOnTheGutterSide
    AC-5  TestTwoUpFooter_TheCellCostIsMeasuredAndBounded
    AC-6  TestTwoUpFooter_APairThatCannotFitSplitsIntoSinglePages
    AC-7  TestTwoUpFooter_TwoUpPagesNowCarryTheirFolio
    AC-8  TestTwoUpFooter_UsesTheSameFooterGeometryAsASinglePage

Three of CARD-223's own claims are retired there, each with its survivor
named in place (G-7): the lower slot's missing icon, the upper slot's
midline one, and "three links for four puzzles".

The owner's complaint is **functional**, not cosmetic: the icon "goes to the
gutter side, it sits near the spine, where the page curves and a phone
struggles to scan it". So the claims that matter are the ones about *which*
corner at *which* parity, and the removal — no page may put QR ink on the
gutter side at any parity — is asserted against measured ink, not inferred
from the geometry that replaced it.

**Where the parity claims are evidence, and where they are an identity.**
CON-018 as amended 2026-10-17 makes Book 1's gutter and outside margin both
12.700 mm, so on that profile the usable area does not move with parity: a
claim about how far the icon sits from the *trim* edge is an identity there
and proves nothing about which margin the code read. Every distance claim
below is therefore made on :func:`_unequal_spec`, a sheet whose gutter
(19.0 mm) and outside margin (7.0 mm) differ — the same device CARD-222's
``_unequal_book()`` introduced for the frame's own mirroring — and the Book 1
form of the claim is recorded explicitly as an identity so that nobody later
reads it as evidence. Claims about which *side* the icon is on keep their
teeth on Book 1 and are made there too.

What this file is, and is not, about
-------------------------------------
``export/layout.py``'s :func:`~nonogram.export.layout.qr_slot` and
:func:`~nonogram.export.layout.qr_caption` measure where the icon and its two
lines go (or that they do not go anywhere); ``export/png.py`` and
``admin/book_pdf_generator.py`` each carry their own, independently drawn
``_draw_qr_placeholder`` (the native-reimplementation convention this project
already uses for grid stroking), and ``book_pdf_generator`` alone owns the two
strings. This file tests both halves: the geometry functions directly, and the
actual ink a render produces.

**CARD-204's own AC-5/AC-6/AC-8 classes are gone from this file, and three of
their claims with them**, because this card deletes what they asserted: the
gutter-side margin slot, its parity mirroring, and a two-up page's lower slot
getting an icon at all. The claims that survived the move — the square's size,
the omit-rather-than-overlap discipline, the glyph being visibly fake — are
re-made below under the names this card's ACs give them, against the new
placement.
"""

from __future__ import annotations

import ast
import inspect
import math
import random
import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata
import nonogram.admin.book_pdf_generator as generator_module
from nonogram.admin.book_pdf_generator import (
    BAND_SEPARATOR,
    QR_CAPTION_TEXT,
    QR_LINK_TEMPLATE,
    SIZE_LABEL_PT,
    BookPDFGenerator,
    PuzzlePagePlan,
    _band_font,
    _draw_page_frame,
    _draw_qr_placeholder as _admin_draw_qr_placeholder,
    _folio_reserve_px,
    _qr_group_line_px,
    grid_size_label,
    qr_group_caption,
    qr_link,
    type_px,
)
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    INTERIOR_FOOTER_MM,
    QR_SLOT_MM,
    OrientationPolicy,
    PageParity,
    PageSpec,
    QrSlot,
    compute_layout,
    compute_pair_layout,
    interior_frame,
    qr_caption,
    qr_group_insets,
    qr_slot,
)
import nonogram.export.png as png_module
from nonogram.export.png import render_image
from nonogram.export.png import _draw_qr_placeholder as _png_draw_qr_placeholder
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, puzzle

DPI = 300
PX_PER_MM = DPI / 25.4
QR_SLOT_PX = round(QR_SLOT_MM / 25.4 * DPI)

#: CON-018's Book 1 profile, in millimetres — the same stated-from-the-spec
#: construction every other CARD-204/222 test file uses, written out here
#: rather than imported.
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
# CON-018's margins as amended 2026-10-17 (CARD-222): the outside margin
# moved 0.375 -> 0.5 in, the top to 0.55 in and the bottom to 0.47 in, and the
# gutter deliberately stayed at KDP's 0.5 in.
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
MIN_THIN_RULE_MM = 0.25

#: The unequal sheet's two side margins, in millimetres. Neither is a Book 1
#: figure and the two differ by more than a 2 cm icon, so "the icon's outer
#: edge is the *outside* margin in from the trim" cannot pass by reading the
#: gutter instead.
UNEQUAL_GUTTER_MM = 19.0
UNEQUAL_OUTSIDE_MM = 7.0

#: The shortest trim ``book_page_spec`` admits at all, with the tight margins
#: ``tests/test_book_page_numbers.py`` and ``tests/test_book_page_frame.py``
#: already measure it on. 10 cm square is **below every KDP trim** — the
#: smallest KDP sells is 5 x 8 in — and is here as AC-5's own no-room sheet.
MIN_TRIM_MM = 100.0
MIN_TRIM_GUTTER_MM = 9.5
MIN_TRIM_OUTSIDE_MM = 6.4

#: CON-020's floor in points, and the device pixels a page at :data:`DPI`
#: sets it in — both written out rather than derived from the constant under
#: test, so the assertion is not the same arithmetic on both sides.
FLOOR_PT = 10.0
FLOOR_PX = 42

#: A pixel darker than this (0..255 grey) is ink, the level
#: ``tests/helpers/page_ink.py`` reads a page at.
INK_LEVEL = 128


def _spec(
    *,
    parity: PageParity = PageParity.ODD,
    width_mm: float = BOOK1_WIDTH_MM,
    height_mm: float = BOOK1_HEIGHT_MM,
    gutter_mm: float = GUTTER_MM,
    outside_mm: float = OUTSIDE_MM,
    **overrides: object,
) -> PageSpec:
    return PageSpec(
        width_mm=width_mm,
        height_mm=height_mm,
        top_mm=TOP_MM,
        bottom_mm=BOTTOM_MM,
        gutter_mm=gutter_mm,
        outside_mm=outside_mm,
        band_mm=BAND_MM,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=MIN_THIN_RULE_MM,
        parity=parity,
        **overrides,
    )


def _unequal_spec(parity: PageParity) -> PageSpec:
    """Book 1's trim with a gutter and an outside margin that **differ**.

    The sheet every distance-by-parity claim in this file is made on. On
    Book 1 itself the two margins are the same figure, so the usable area
    does not move with parity and such a claim is an identity (CON-018's own
    amendment note says so); here it moves by 12 mm, which is what makes the
    assertion evidence.
    """
    return _spec(parity=parity, gutter_mm=UNEQUAL_GUTTER_MM, outside_mm=UNEQUAL_OUTSIDE_MM)


def _min_trim_spec(parity: PageParity = PageParity.ODD) -> PageSpec:
    return _spec(
        parity=parity,
        width_mm=MIN_TRIM_MM,
        height_mm=MIN_TRIM_MM,
        gutter_mm=MIN_TRIM_GUTTER_MM,
        outside_mm=MIN_TRIM_OUTSIDE_MM,
    )


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> List[List[bool]]:
    """A grid whose row clues are ``row_depth`` deep and columns ``column_depth``
    (the same construction ``test_book_puzzle_frame.py`` uses, restated here)."""
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


def _clue_sets(columns: int, rows: int, row_depth: int, column_depth: int):
    found = clues.compute_clues(_grid(columns, rows, row_depth, column_depth))
    return found.rows, found.columns


def _payload(columns: int, rows: int, row_depth: int, column_depth: int) -> ExportPayload:
    grid = _grid(columns, rows, row_depth, column_depth)
    found = clues.compute_clues(grid)
    return ExportPayload(
        grid=grid,
        row_clues=found.rows,
        column_clues=found.columns,
        seed=223,
        mode="random",
        name="qr-slot-test",
        difficulty="Easy",
    )


def _px(millimetres: float) -> int:
    return round(millimetres * PX_PER_MM)


def _gutter_half(spec: PageSpec, trim_width_px: int) -> Tuple[int, int]:
    """The half of the trim the spine is on, as ``(left, right)`` in pixels.

    Half the sheet, by parity and nothing else: the binding edge is the left
    on an ODD (right-hand) page and the right on an EVEN (left-hand) one. A
    half rather than "the margin", so the claim stays about which side of the
    sheet the mark is on and cannot be satisfied by a mark that merely clears
    a margin's width.
    """
    middle = trim_width_px // 2
    if spec.parity is PageParity.ODD:
        return 0, middle
    return middle, trim_width_px


def _disjoint(a, b) -> bool:
    """Whether two ``(left, top, right, bottom)`` boxes share no area."""
    return a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


# --------------------------------------------------------------------------
# AC-1 — the outer bottom corner
# --------------------------------------------------------------------------


class TestBookQrSlot_SitsAtTheOuterBottomCorner:
    """The icon's box lies in the footer at the outer edge, mirrored by parity,
    and its outer edge is inside the usable area."""

    def test_the_icon_hugs_the_outer_edge_on_each_parity(self) -> None:
        """Which side, on Book 1 — where the *side* still has teeth even
        though a distance would not."""
        row_clues, column_clues = _clue_sets(20, 20, 1, 1)
        for parity, outer_is_right in ((PageParity.ODD, True), (PageParity.EVEN, False)):
            spec = _spec(parity=parity)
            layout = compute_layout(row_clues, column_clues, spec)
            page = layout.page
            icon = qr_slot(layout)
            assert icon is not None, f"{parity} should carry an icon on Book 1"
            if outer_is_right:
                assert icon.right == page.usable_right
                assert icon.left > page.usable_left
            else:
                assert icon.left == page.usable_left
                assert icon.right < page.usable_right

    def test_the_icon_sits_in_the_footer_strip_on_the_bottom_margin(self) -> None:
        """Vertically, it is the row the frame's own footer band reserves:
        flush with the bottom margin, wholly below the footer's hairline, and
        clear of the footer line the grid size and the folio are set on."""
        row_clues, column_clues = _clue_sets(20, 20, 1, 1)
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            layout = compute_layout(row_clues, column_clues, spec)
            frame = interior_frame(spec)
            icon = qr_slot(layout)
            assert icon is not None
            assert icon.bottom == layout.page.usable_bottom == frame.page_bottom
            assert icon.top > frame.footer_rule.y, "the icon is below the hairline"
            assert icon.top > frame.baseline, "and below the footer line's own baseline"

    def test_unequal_margins_put_the_outer_edge_one_outside_margin_in(self) -> None:
        """**The mirroring evidence** (AC-1), made where it is observable.

        On a sheet whose gutter is 19.0 mm and whose outside margin is
        7.0 mm, the icon's outer edge is the *outside* margin in from the
        trim — at both parities, on opposite sides. Reading the gutter
        instead would put it 19.0 mm in, 142 px away, so this assertion fails
        if the sides are swapped or the wrong margin is read.
        """
        row_clues, column_clues = _clue_sets(20, 20, 1, 1)
        outside_px = _px(UNEQUAL_OUTSIDE_MM)
        gutter_px = _px(UNEQUAL_GUTTER_MM)
        assert outside_px != gutter_px, "the fixture must have unequal margins to prove anything"

        odd_layout = compute_layout(row_clues, column_clues, _unequal_spec(PageParity.ODD))
        even_layout = compute_layout(row_clues, column_clues, _unequal_spec(PageParity.EVEN))
        trim = odd_layout.width
        odd, even = qr_slot(odd_layout), qr_slot(even_layout)
        assert odd is not None and even is not None

        # A right-hand page: the outer edge is the right, one outside margin
        # in from the trim — not one gutter in.
        assert trim - odd.right == outside_px
        assert trim - odd.right != gutter_px
        # A left-hand page: the outer edge is the left, the same figure.
        assert even.left == outside_px
        assert even.left != gutter_px
        # And a true mirror: each box is the other's, reflected in the trim.
        assert odd.left == trim - even.right
        assert odd.right == trim - even.left

    def test_on_the_default_profile_the_same_distance_claim_is_an_identity(self) -> None:
        """Recorded, so nobody reads the Book 1 case as evidence (CON-018).

        With the gutter and the outside margin both 12.700 mm the usable area
        is symmetric about the trim's centre, so "the icon's outer edge is one
        outside margin in" and "…one gutter in" are the **same assertion** on
        Book 1 and neither tells you which margin the code read. What still
        has teeth there is the side, which the first test in this class makes.
        """
        row_clues, column_clues = _clue_sets(20, 20, 1, 1)
        odd = compute_layout(row_clues, column_clues, _spec(parity=PageParity.ODD))
        even = compute_layout(row_clues, column_clues, _spec(parity=PageParity.EVEN))
        assert _px(GUTTER_MM) == _px(OUTSIDE_MM), (
            "CON-018's amendment made these equal; if they ever differ again, "
            "the Book 1 case becomes evidence and this test should say so"
        )
        odd_icon, even_icon = qr_slot(odd), qr_slot(even)
        assert odd_icon is not None and even_icon is not None
        # The two boxes are each other's reflection — which was equally true
        # of the gutter-side placement this card removed: an identity.
        assert odd_icon.left == odd.width - even_icon.right
        # The side, however, still differs.
        assert odd_icon.left != even_icon.left

    def test_the_outer_edge_is_inside_the_usable_area(self) -> None:
        """AC-1's final clause, on both profiles and both parities: the box
        never crosses the usable area into the trim margin."""
        row_clues, column_clues = _clue_sets(20, 20, 1, 1)
        checked = 0
        for parity in (PageParity.ODD, PageParity.EVEN):
            for spec in (_spec(parity=parity), _unequal_spec(parity)):
                layout = compute_layout(row_clues, column_clues, spec)
                page = layout.page
                icon = qr_slot(layout)
                assert icon is not None
                assert page.usable_left <= icon.left < icon.right <= page.usable_right
                assert page.usable_top <= icon.top < icon.bottom <= page.usable_bottom
                checked += 1
        assert checked == 4


# --------------------------------------------------------------------------
# AC-2 — never the spine
# --------------------------------------------------------------------------


def _qr_ink(payload: ExportPayload, spec: PageSpec, monkeypatch) -> np.ndarray:
    """The page's **own QR pixels**: a boolean mask of the pixels that differ
    between the page as it is drawn and the same page drawn with the
    placeholder suppressed.

    Not "the pixels inside the box ``qr_slot`` reported" — that would assume
    the answer. Every pixel this mask holds is one the glyph put there, and
    no pixel it misses is one the glyph put anywhere else.
    """
    drawn = np.asarray(render_image(payload, page_spec=spec).convert("L"))
    monkeypatch.setattr(png_module, "_draw_qr_placeholder", lambda draw, icon: None)
    bare = np.asarray(render_image(payload, page_spec=spec).convert("L"))
    monkeypatch.undo()
    return drawn != bare


class TestBookQrSlot_NeverPlacesInkOnTheGutterSide:
    """No page kind puts a QR pixel in the gutter half of the sheet, at any
    parity — the removal CARD-223 is for, asserted as a removal."""

    @pytest.mark.parametrize("parity", [PageParity.ODD, PageParity.EVEN])
    def test_a_single_puzzle_pages_qr_ink_is_all_in_the_outer_half(
        self, parity: PageParity, monkeypatch
    ) -> None:
        payload = _payload(20, 20, 1, 1)
        spec = _spec(parity=parity)
        mask = _qr_ink(payload, spec, monkeypatch)
        assert mask.any(), "the page drew no QR ink at all, so this proves nothing"
        left, right = _gutter_half(spec, mask.shape[1])
        assert not mask[:, left:right].any(), (
            f"a {parity} page put QR ink in its gutter half, columns {left}..{right}"
        )

    @pytest.mark.parametrize("parity", [PageParity.ODD, PageParity.EVEN])
    def test_the_control_the_old_placement_would_have_failed_this(
        self, parity: PageParity
    ) -> None:
        """The claim above discriminates: a box flush with the usable area's
        **gutter**-side edge — exactly where CARD-204 put it, and where the
        owner found it unscannable — lands inside the half this test forbids.

        Without this, "all the QR ink is in the outer half" could be true of
        a page that simply draws no icon, or of a half-definition that covers
        the whole sheet.
        """
        spec = _spec(parity=parity)
        layout = compute_layout(*_clue_sets(20, 20, 1, 1), spec)
        page = layout.page
        if parity is PageParity.ODD:
            retired = (page.usable_left, page.usable_left + QR_SLOT_PX)
        else:
            retired = (page.usable_right - QR_SLOT_PX, page.usable_right)
        left, right = _gutter_half(spec, layout.width)
        assert left <= retired[0] and retired[1] <= right, (
            "the retired gutter-side box is not inside the gutter half, so this "
            "file's notion of that half is wrong"
        )

    @pytest.mark.parametrize("parity", [PageParity.ODD, PageParity.EVEN])
    def test_a_two_up_pages_outer_group_keeps_its_icon_out_of_the_gutter_half(
        self, parity: PageParity
    ) -> None:
        """A two-up page's **outer** group, both parities — the one that is a
        single page's group to the pixel (AC-8).

        **Retargeted by CARD-248, and narrowed on purpose.** This test used to
        ask each *slot* for an icon of its own: the upper slot answered with a
        box at the midline between the two drawings and the lower slot with
        none, which is the arrangement that printed three links for four
        puzzles. A two-up page now has one footer strip with two groups in it,
        and the **inner** group's own words necessarily cross the trim's
        centre — the row is wider than the outer half of the sheet, which
        ``TestTwoUpFooter_NeverPlacesInkOnTheGutterSide`` asserts as
        arithmetic before narrowing the forbidden region to the strip CARD-204
        actually used. That class is this claim's survivor for the page as a
        whole (G-7); what is still true of the outer group, and is kept here,
        is the gutter **half**.
        """
        spec = _spec(parity=parity)
        pair = compute_pair_layout(
            _clue_sets(10, 10, 3, 3),
            _clue_sets(10, 10, 3, 3),
            spec,
            folio_reserve_px=_folio_reserve_px(DPI),
            footer_reserve_px=interior_frame(spec).footer_depth,
        )
        assert pair is not None
        left, right = _gutter_half(spec, pair.lower.width)

        outer = qr_slot(pair.lower)
        assert outer is not None, "the footer strip's outer group should carry an icon"
        assert not (left <= outer.left < right or left < outer.right <= right)

    def test_no_extent_of_a_seeded_corpus_puts_the_box_in_the_gutter_half(self) -> None:
        """The same claim over a seeded corpus of extents rather than three
        hand-picked ones (no ``hypothesis``: stdlib ``random.Random``, with
        the case count asserted inside the test so the corpus cannot silently
        shrink)."""
        rng = random.Random(2230001)
        checked = 0
        carried = 0
        for _ in range(120):
            columns = rng.randint(MIN_SIZE, MAX_SIZE)
            rows = rng.randint(MIN_SIZE, MAX_SIZE)
            parity = rng.choice((PageParity.ODD, PageParity.EVEN))
            spec = rng.choice((_spec(parity=parity), _unequal_spec(parity)))
            layout = compute_layout(*_clue_sets(columns, rows, 1, 1), spec)
            icon = qr_slot(layout)
            checked += 1
            if icon is None:
                continue
            carried += 1
            left, right = _gutter_half(spec, layout.width)
            assert not (left <= icon.left < right or left < icon.right <= right), (
                columns,
                rows,
                parity,
                icon,
            )
        assert checked == 120
        assert carried >= 100, (
            f"only {carried} of {checked} extents carried an icon at all — the "
            "corpus has stopped exercising the claim"
        )


# --------------------------------------------------------------------------
# AC-3 — the caption and the link (and G-2)
# --------------------------------------------------------------------------


def _text_calls(generator: BookPDFGenerator, puzzles, monkeypatch) -> List[dict]:
    """Every ``draw.text`` call one interior export makes, with its font size.

    The same "spy on ``ImageDraw.text`` while walking ``interior_stream``"
    technique ``tests/test_book_page_numbers.py`` and
    ``tests/test_book_interior_type_floor.py`` already use.
    """
    original = ImageDraw.ImageDraw.text
    calls: List[dict] = []
    current = {"page": 0}

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        calls.append(
            {
                "page": current["page"],
                "text": str(text),
                "anchor": kwargs.get("anchor"),
                "size": getattr(font, "size", None),
                "xy": xy,
            }
        )
        return original(self, xy, text, fill, font, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    stream = generator.interior_stream(puzzles)
    pages = iter(stream.pages)
    drawn = 0
    while True:
        current["page"] = drawn + 1
        try:
            next(pages)
        except StopIteration:
            break
        drawn += 1
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
    return calls


class TestBookQrSlot_CarriesItsCaptionAndLink:
    """Two lines beside the icon — the invitation and the typed link — both at
    or above CON-020's floor, with the link coming from one constant; and
    (G-2) the grid-size label and the QR group do not collide."""

    def test_a_real_book_prints_both_lines_on_every_page_that_has_an_icon(
        self, monkeypatch
    ) -> None:
        """The baseline book, exported: the invitation and a link are set
        together or not at all, on the same pages and in equal numbers, and
        every link printed is this project's own template filled with a puzzle
        number the book really holds.

        **The count moved from three to four under CARD-248, and this test no
        longer owns it.** CARD-223 left a two-up page's lower slot with no
        icon, so this book printed three links for its four puzzles and this
        test asserted exactly that. CARD-248 gives the page one footer strip
        carrying both puzzles' groups;
        ``TestTwoUpFooter_CarriesBothPuzzlesLinks`` is the survivor that
        asserts the four-for-four count (G-7). What is left here is the
        pairing of the two lines — never one without the other — which is
        CARD-223's own AC-3 and is unaffected by how many groups a page has.

        The invitation is matched by **containment** rather than equality
        because a two-up page's groups name their puzzle in the same line
        (:func:`qr_group_caption`).
        """
        generator = BookPDFGenerator(corpus_book())
        puzzles = baseline_puzzles()

        calls = _text_calls(generator, puzzles, monkeypatch)
        captions = [call for call in calls if QR_CAPTION_TEXT in call["text"]]
        links = [call for call in calls if call["text"].startswith("nonogram.example/")]
        assert captions, "no page of the book set the invitation at all"
        assert {call["page"] for call in captions} == {call["page"] for call in links}
        assert len(captions) == len(links)
        assert sorted(call["text"] for call in links) == sorted(
            qr_link(number) for number in range(1, len(puzzles) + 1)
        ), sorted(call["text"] for call in links)

    def test_both_lines_are_set_at_the_floor_and_beside_the_icon(self) -> None:
        """Measured on the geometry and the face, not on the export: the two
        anchors sit inside the icon's own row, on the icon's inner side, and
        the face is CON-020's floor."""
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            layout = compute_layout(*_clue_sets(20, 20, 1, 1), spec)
            icon = qr_slot(layout)
            caption = qr_caption(layout)
            assert icon is not None and caption is not None
            # Inside the icon's own row, so the lines can reach neither the
            # footer line above nor past the bottom margin.
            assert icon.top <= caption.caption_baseline < caption.link_baseline <= icon.bottom
            # On the icon's inner side, running away from the trim edge.
            if parity is PageParity.ODD:
                assert caption.right_aligned and caption.x < icon.left
            else:
                assert not caption.right_aligned and caption.x > icon.right
        assert type_px(FLOOR_PT, DPI) == FLOOR_PX
        assert SIZE_LABEL_PT == FLOOR_PT, "the footer's lines are all set at the floor"

    def test_the_drawn_lines_hold_the_floor_and_stay_inside_the_usable_area(
        self, monkeypatch
    ) -> None:
        """The ink, not the intent: both lines are set in a face at least
        :data:`FLOOR_PX` tall and neither overhangs the usable area."""
        generator = BookPDFGenerator(corpus_book())
        calls = _text_calls(generator, baseline_puzzles(), monkeypatch)
        ours = [
            call
            for call in calls
            if call["text"] == QR_CAPTION_TEXT or call["text"].startswith("nonogram.example/")
        ]
        assert len(ours) >= 6, f"only {len(ours)} QR footer lines were drawn"
        font = _band_font(FLOOR_PX)
        for call in ours:
            assert call["size"] is not None and call["size"] >= FLOOR_PX, call
            spec = generator.page_spec(call["page"])
            placement = compute_layout(*_clue_sets(10, 10, 3, 3), spec).page
            width = font.getlength(call["text"])
            x = call["xy"][0]
            left = x - width if call["anchor"] == "rb" else x
            assert left >= placement.usable_left, call
            assert left + width <= placement.usable_right, call

    def test_the_link_comes_from_exactly_one_constant(self) -> None:
        """AC-3's last clause: CARD-210 changes one line.

        Asserted the strongest way short of running that card — the
        placeholder host appears in exactly one string literal in the whole
        of ``src/nonogram/**``, and :func:`qr_link` is the only reader of the
        name that holds it.
        """
        package = Path(__file__).resolve().parent.parent / "src" / "nonogram"
        holders = []
        for module in sorted(package.rglob("*.py")):
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if "nonogram.example" in node.value:
                        holders.append((module.name, node.value))
        assert holders == [("book_pdf_generator.py", QR_LINK_TEMPLATE)], holders
        assert qr_link(52) == "nonogram.example/p/052", "the artifact's own form"
        assert "QR_LINK_TEMPLATE" in inspect.getsource(qr_link)

    def test_the_printed_link_is_inert(self) -> None:
        """CON-021: a printed address a reader might type must not be a real
        or admin-only one. ``.example`` is reserved by RFC 2606 and cannot
        resolve, and the template carries no scheme and no real TLD."""
        assert QR_LINK_TEMPLATE.split("/")[0].endswith(".example")
        lowered = QR_LINK_TEMPLATE.lower()
        for marker in ("http://", "https://", "www.", ".com", ".org", ".net", ".io"):
            assert marker not in lowered, marker

    def test_the_grid_size_label_and_the_qr_group_do_not_collide(self) -> None:
        """G-2 — they share the footer, so their boxes are disjoint.

        Every box is built from the figures the renderer really draws with:
        the frame's own ``label_x``/``baseline`` and the label measured at its
        own face, against the icon's box and the two lines' own measured
        boxes. The folio is included because it shares the same line.
        """
        font = _band_font(FLOOR_PX)
        ascent, descent = font.getmetrics()
        checked = 0
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            layout = compute_layout(*_clue_sets(20, 20, 1, 1), spec)
            frame = interior_frame(spec)
            icon = qr_slot(layout)
            caption = qr_caption(layout)
            assert icon is not None and caption is not None

            label = grid_size_label(layout.columns, layout.rows)
            label_width = font.getlength(label)
            label_left = (
                frame.label_x - label_width if frame.label_right_aligned else frame.label_x
            )
            label_box = (
                label_left,
                frame.baseline - ascent,
                label_left + label_width,
                frame.baseline + descent,
            )
            folio_width = font.getlength("99")
            folio_box = (
                frame.folio_x - folio_width / 2,
                frame.baseline - ascent,
                frame.folio_x + folio_width / 2,
                frame.baseline + descent,
            )
            icon_box = (icon.left, icon.top, icon.right, icon.bottom)
            line_boxes = []
            for text, baseline in (
                (QR_CAPTION_TEXT, caption.caption_baseline),
                (qr_link(52), caption.link_baseline),
            ):
                width = font.getlength(text)
                left = caption.x - width if caption.right_aligned else caption.x
                line_boxes.append((left, baseline - ascent, left + width, baseline + descent))

            for other in [icon_box, *line_boxes]:
                assert _disjoint(label_box, other), (parity, label_box, other)
                assert _disjoint(folio_box, other), (parity, folio_box, other)
            assert _disjoint(line_boxes[0], line_boxes[1]), (parity, line_boxes)
            for line in line_boxes:
                assert _disjoint(line, icon_box), (parity, line, icon_box)
            checked += 1
        assert checked == 2


# --------------------------------------------------------------------------
# AC-4 — two centimetres square
# --------------------------------------------------------------------------


class TestBookQrSlot_IsTwoCentimetresSquare:
    """The owner's figure from CARD-204, unchanged by the move."""

    def test_every_extent_that_carries_one_reports_a_two_centimetre_square(self) -> None:
        row_clues, column_clues = _clue_sets(20, 20, 1, 1)
        #: ``(extent, inset)`` pairs: single pages at both parities on both
        #: profiles, and — since CARD-248 — **both** groups of a two-up page's
        #: own footer strip, which is where two icons now sit on one page.
        extents = []
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            extents.append((compute_layout(row_clues, column_clues, spec), 0))
            extents.append((compute_layout(row_clues, column_clues, _unequal_spec(parity)), 0))
            pair = compute_pair_layout(
                _clue_sets(10, 10, 3, 3),
                _clue_sets(10, 10, 3, 3),
                spec,
                folio_reserve_px=_folio_reserve_px(DPI),
                footer_reserve_px=interior_frame(spec).footer_depth,
            )
            assert pair is not None
            insets = qr_group_insets(pair.lower, _qr_group_line_px(DPI), 2)
            assert insets is not None
            extents.extend((pair.lower, inset) for inset in insets)
        checked = 0
        for layout, inset in extents:
            icon = qr_slot(layout, inset_px=inset)
            assert icon is not None
            assert abs((icon.right - icon.left) - QR_SLOT_PX) <= 1
            assert abs((icon.bottom - icon.top) - QR_SLOT_PX) <= 1
            checked += 1
        assert checked == 8

    def test_the_drawn_box_measures_two_centimetres_on_the_page(self, monkeypatch) -> None:
        """The ink, at the page's own resolution: the glyph's own pixels span
        2 cm each way, within the pixel its centred border hangs."""
        payload = _payload(20, 20, 1, 1)
        spec = _spec(parity=PageParity.ODD)
        mask = _qr_ink(payload, spec, monkeypatch)
        rows = np.where(mask.any(axis=1))[0]
        columns = np.where(mask.any(axis=0))[0]
        height_mm = (rows[-1] - rows[0] + 1) / PX_PER_MM
        width_mm = (columns[-1] - columns[0] + 1) / PX_PER_MM
        assert width_mm == pytest.approx(QR_SLOT_MM, abs=0.2), width_mm
        assert height_mm == pytest.approx(QR_SLOT_MM, abs=0.2), height_mm


# --------------------------------------------------------------------------
# AC-5 — no room: draw neither, through the folio's own verdict
# --------------------------------------------------------------------------


class TestBookQrSlot_YieldsRatherThanCollide:
    """Where the footer strip is not clear, the page draws neither the icon
    nor its lines — and says so through the same condition the footer group
    (and so the folio's reservation) already uses."""

    def test_a_page_fit_bound_page_gets_neither_the_icon_nor_its_lines(self) -> None:
        """A 30x30 with a 1-deep row gutter and a 10-deep column gutter is
        page-fit-bound on Book 1's own trim — the same construction
        ``tests/test_book_page_numbers.py``'s ``_tight_fit_single_page_puzzle``
        uses for the folio's own no-room case."""
        spec = _spec(parity=PageParity.ODD)
        layout = compute_layout(*_clue_sets(30, 30, 1, 10), spec)
        frame = interior_frame(spec)
        page = layout.page
        assert page is not None and page.fits
        # The precondition, confirmed rather than assumed.
        assert page.drawing_bottom > frame.footer_rule.y
        assert qr_slot(layout) is None
        assert qr_caption(layout) is None

    def test_the_shortest_trim_has_no_room_for_the_group(self) -> None:
        """10 cm square — below every trim KDP sells, and the sheet
        ``test_book_page_frame.py`` already treats as the hardest one. Its
        29.878 mm footer strip is most of what the page has left under the
        drawing, so no puzzle on it carries the group. Recorded as a
        measurement, not as a rule about small books: every KDP trim from
        5 x 8 in up does carry it (the next test)."""
        for columns in (5, 10, 15):
            layout = compute_layout(*_clue_sets(columns, columns, 1, 1), _min_trim_spec())
            assert qr_slot(layout) is None, columns
            assert qr_caption(layout) is None, columns

    @pytest.mark.parametrize(
        "width_mm,height_mm",
        [(127.0, 203.2), (139.7, 215.9), (152.4, 228.6), (215.9, 279.4)],
    )
    @pytest.mark.parametrize("side", [10, 15, 20, 25, 30])
    def test_the_omission_is_not_a_blanket_rule(
        self, width_mm: float, height_mm: float, side: int
    ) -> None:
        """The control AC-5 needs: on every KDP trim this project prints, at
        every puzzle size in this sweep, the group is drawn. If the room check
        ever tightens into a rule that quietly drops the icon from real books,
        this is what reds."""
        spec = _spec(width_mm=width_mm, height_mm=height_mm)
        layout = compute_layout(*_clue_sets(side, side, 1, 1), spec)
        assert qr_slot(layout) is not None
        assert qr_caption(layout) is not None

    def test_the_verdict_is_the_footer_groups_own_verdict(self) -> None:
        """AC-5's "says so through the same 'no room' path the folio
        reservation already uses", as an equivalence rather than a claim.

        ``_draw_page_frame`` returns whether it drew the footer group — the
        hairline, the grid-size label and the centred folio — or fell back to
        CARD-200's bottom-outer-corner folio, which is the corner this icon
        now occupies. Over a seeded corpus of extents the two verdicts agree
        on every case, which is what makes "the icon can never be printed over
        that folio" a property rather than a hope.
        """
        rng = random.Random(2230005)
        agreed = 0
        both_ways = {True: 0, False: 0}
        for _ in range(80):
            columns = rng.randint(MIN_SIZE, MAX_SIZE)
            rows = rng.randint(MIN_SIZE, MAX_SIZE)
            column_depth = rng.choice((1, 5, 10))
            if 2 * column_depth - 1 > rows:
                column_depth = 1
            spec = _spec(parity=rng.choice((PageParity.ODD, PageParity.EVEN)))
            layout = compute_layout(*_clue_sets(columns, rows, 1, column_depth), spec)
            placement = layout.page
            canvas = Image.new("RGB", (layout.width, layout.height), (255, 255, 255))
            footer_drawn = _draw_page_frame(
                ImageDraw.Draw(canvas),
                interior_frame(spec),
                7,
                DPI,
                size_label=grid_size_label(layout.columns, layout.rows),
                content_bottom=placement.drawing_bottom,
            )
            assert (qr_slot(layout) is not None) == footer_drawn, (columns, rows, column_depth)
            assert (qr_caption(layout) is not None) == footer_drawn
            both_ways[footer_drawn] += 1
            agreed += 1
        assert agreed == 80
        assert both_ways[True] and both_ways[False], (
            f"the corpus produced only {both_ways} — an equivalence that never "
            "sees both verdicts is not under test"
        )

    def test_a_pair_laid_out_with_no_footer_reserve_draws_neither(self) -> None:
        """The unreserved pair, kept as the control for the reserve itself.

        **What this used to assert, and what replaced it** (G-7). Until
        CARD-248 every two-up pair was laid out with no vertical reservation,
        so its lower slot's drawing stopped on the bottom margin, its slack
        read zero and it carried no icon and no lines — the defect that
        printed three links for four puzzles. Production now always reserves
        the strip (``compute_pair_layout``'s ``footer_reserve_px``, from
        ``InteriorFrame.footer_depth``), and
        ``TestTwoUpFooter_CarriesBothPuzzlesLinks`` is the survivor asserting
        that the lower slot's extent carries *both* groups.

        What is kept here is the other half of the same statement, which is
        still live and is what makes the reserve's effect visible: with **no**
        reserve the geometry still answers "no room", so the strip is really
        what buys the footer and not something the renderer assumed.
        """
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            bare = compute_pair_layout(
                _clue_sets(10, 10, 3, 3), _clue_sets(10, 10, 3, 3), spec
            )
            assert bare is not None
            assert bare.lower.page.usable_bottom - bare.lower.page.drawing_bottom == 0
            assert qr_slot(bare.lower) is None
            assert qr_caption(bare.lower) is None

            reserved = compute_pair_layout(
                _clue_sets(10, 10, 3, 3),
                _clue_sets(10, 10, 3, 3),
                spec,
                footer_reserve_px=interior_frame(spec).footer_depth,
            )
            assert reserved is not None
            assert qr_slot(reserved.lower) is not None
            assert qr_caption(reserved.lower) is not None

    def test_an_unplaced_sheet_has_neither(self) -> None:
        """CON-019: the default, unparitied spec (every CLI and web export) is
        a drawing-sized image with no margins to reserve from."""
        layout = compute_layout(*_clue_sets(20, 20, 1, 1), None)
        assert layout.page is None
        assert qr_slot(layout) is None
        assert qr_caption(layout) is None

    def test_a_page_with_no_group_draws_no_ink_where_the_group_would_go(
        self, monkeypatch
    ) -> None:
        """The omission as ink: the page-fit-bound page's own render puts no
        QR pixel anywhere at all, rather than putting one somewhere else."""
        payload = _payload(30, 30, 1, 10)
        spec = _spec(parity=PageParity.ODD)
        assert qr_slot(compute_layout(payload.row_clues, payload.column_clues, spec)) is None
        mask = _qr_ink(payload, spec, monkeypatch)
        assert not mask.any(), "a page with no icon still drew QR pixels"


# --------------------------------------------------------------------------
# AC-6 — the placeholder is still obviously fake
# --------------------------------------------------------------------------


class TestBookQrSlot_IsStillThePlaceholderGlyph:
    """The owner's 2026-10-13 decision stands until CARD-210: the drawn glyph
    is a generic grid-of-squares placeholder, not a real QR code, and encodes
    and links to nothing live. (CARD-204's AC-8, re-made here — the move
    changes where the glyph is, not what it is.)"""

    def _icon(self) -> QrSlot:
        return QrSlot(left=100, top=100, right=100 + QR_SLOT_PX, bottom=100 + QR_SLOT_PX)

    def test_the_glyph_is_a_plain_alternating_checkerboard_not_module_data(self) -> None:
        """A real QR code's modules encode data (an irregular-looking bit
        pattern) and three corners carry a nested-square finder pattern. This
        glyph is neither: every filled module sits at
        ``(row + column) % 2 == 1`` on a fixed 5x5 grid — checked against the
        drawn pixels, not against the source's own loop."""
        icon = self._icon()
        image = Image.new("RGB", (icon.right + 10, icon.bottom + 10), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        _png_draw_qr_placeholder(draw, icon)

        side = icon.right - icon.left
        modules = 5
        step = side / modules
        for row in range(modules):
            for column in range(modules):
                x = icon.left + round((column + 0.5) * step)
                y = icon.top + round((row + 0.5) * step)
                pixel = image.getpixel((x, y))
                expected_filled = (row + column) % 2 == 1
                is_dark = pixel[0] < INK_LEVEL
                assert is_dark == expected_filled, (row, column, pixel)

    def test_both_renderers_draw_the_identical_pattern(self) -> None:
        """``export/png.py`` and ``book_pdf_generator.py`` reimplement this
        glyph independently (the native-reimplementation convention) — this
        confirms the two did not drift into two different "placeholders", one
        of which might read as more real than the other."""
        icon = self._icon()
        a = Image.new("RGB", (icon.right + 10, icon.bottom + 10), (255, 255, 255))
        b = Image.new("RGB", (icon.right + 10, icon.bottom + 10), (255, 255, 255))
        _png_draw_qr_placeholder(ImageDraw.Draw(a), icon)
        _admin_draw_qr_placeholder(ImageDraw.Draw(b), icon)
        assert np.array_equal(np.asarray(a), np.asarray(b))

    def test_the_pattern_never_varies_with_the_puzzle_or_the_page(self) -> None:
        """It is decoration, not data: the same pixels whatever puzzle or page
        it is reserved for, so nothing about the glyph itself could carry a
        per-puzzle URL — the link is typed beside it instead, which is this
        card's whole answer to a reader with no camera."""
        icon = self._icon()
        rng = random.Random(2204008)
        reference: Optional[np.ndarray] = None
        for _ in range(5):
            columns = rng.randint(MIN_SIZE, MAX_SIZE)
            rows = rng.randint(MIN_SIZE, MAX_SIZE)
            image = Image.new("RGB", (icon.right + 10, icon.bottom + 10), (255, 255, 255))
            _png_draw_qr_placeholder(ImageDraw.Draw(image), icon)
            pixels = np.asarray(image)
            if reference is None:
                reference = pixels
            else:
                assert np.array_equal(pixels, reference), (columns, rows)

    def test_no_url_appears_anywhere_in_either_drawing_function(self) -> None:
        """CON-021/G-3: the *glyph* must not point at any URL, real or
        placeholder. The typed link is a separate mark with a separate drawer
        (``_draw_qr_caption``), so neither checkerboard function's source may
        contain an address of any kind."""
        for fn in (_png_draw_qr_placeholder, _admin_draw_qr_placeholder):
            source = inspect.getsource(fn).lower()
            for marker in ("http://", "https://", "www.", "ftp://", ".com", ".org", ".net"):
                assert marker not in source, (fn, marker)
            assert "nonogram.example" not in source, fn

    def test_neither_drawing_module_imports_a_qr_encoder(self) -> None:
        """ADR-0006/R1, G-3: the dependency baseline carries no QR-generation
        library, so there is no code path — reachable or not — that could turn
        this glyph into real QR pixels without a future card's explicit
        dependency decision."""
        import nonogram.admin.book_pdf_generator as admin_module
        import nonogram.export.png as png

        for module in (png, admin_module):
            names = " ".join(dir(module)).lower()
            assert "qrcode" not in names


# --------------------------------------------------------------------------
# Item 4 — the removal, stated once
# --------------------------------------------------------------------------


class TestBookQrSlot_TheGutterSidePlacementIsGone:
    """CARD-223's item 4: the gutter-side slot and its parity mirroring are
    deleted, not merely unreachable."""

    def test_the_geometry_function_names_no_gutter_side_placement(self) -> None:
        """Read off the source: ``qr_slot``'s body reads the usable area's
        outer edge by parity and nothing else — there is no second branch left
        that could put the icon back beside the spine.

        A source read rather than a behavioural one because that is what
        "deleted" means here: the behavioural claims are AC-1 and AC-2 above,
        and this is the one that would red if the old branch came back behind
        a condition no corpus happened to reach.
        """
        package = Path(__file__).resolve().parent.parent / "src" / "nonogram"
        source = (package / "export" / "layout.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "qr_slot"
        )
        body = ast.get_source_segment(source, function)
        # The docstring explains the retired placement; the code must not
        # implement it. Strip the docstring and read what is left.
        opening = body.index('"""')
        code = body[body.index('"""', opening + 3) + 3 :]
        assert "drawing_left" not in code, code
        assert "drawing_right" not in code, code
        assert sorted(set(re.findall(r"usable_\w+", code))) == [
            "usable_bottom",
            "usable_left",
            "usable_right",
        ], code


# --------------------------------------------------------------------------
# CARD-248's own fixtures and instruments
# --------------------------------------------------------------------------

#: FR-040's two-up minimum, in millimetres — written out rather than imported,
#: so a claim about the boundary is not the same constant on both sides.
TWO_UP_MINIMUM_MM = 7.0


def _page_text_calls(generator, plan, payloads, monkeypatch) -> List[dict]:
    """Every ``draw.text`` call **one page's** own drawing makes.

    The per-page form of :func:`_text_calls`, for a page composed directly by
    ``_two_up_page`` rather than reached through a whole interior export —
    the same spy ``tests/test_book_page_numbers.py`` uses for the folio.
    """
    original = ImageDraw.ImageDraw.text
    calls: List[dict] = []

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        calls.append(
            {
                "text": str(text),
                "anchor": kwargs.get("anchor"),
                "size": getattr(font, "size", None),
                "xy": xy,
            }
        )
        return original(self, xy, text, fill, font, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    try:
        generator._two_up_page(plan, payloads)
    finally:
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
    return calls


def _refusing_puzzles() -> List[dict]:
    """Two easy 10x14s with 1-deep clues: 30 cells of combined drawing height,
    inside AC-6's refused band, in the shape the generator is handed rows in."""
    return [
        puzzle("card248-split-a", 10, 14, 1, "easy", "Split A"),
        puzzle("card248-split-b", 10, 14, 1, "easy", "Split B"),
    ]


def _narrow_book() -> Book:
    """A storable but absurd 10 x 48 cm book: tall enough to hold a pair,
    too narrow for two footer groups (``MIN_TRIM_CM``, ``MAX_TRIM_HEIGHT_CM``).
    """
    return Book(
        book_id="card248-narrow",
        metadata=BookMetadata(
            title="Narrow",
            description="AC-6's horizontal corner.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=12.0,
        trim_height_cm=48.0,
        gutter_margin_cm=0.95,
        outside_margin_cm=0.64,
    )


# ==========================================================================
# CARD-248 — a two-up page gets ONE footer strip carrying BOTH puzzles' links
# ==========================================================================
#
#     AC-1  TestTwoUpFooter_CarriesBothPuzzlesLinks
#     AC-2  TestTwoUpFooter_EachGroupCarriesItsOwnSlotsLink
#     AC-3  TestTwoUpFooter_EachGroupNamesItsPuzzleNumber
#     AC-4  TestTwoUpFooter_NeverPlacesInkOnTheGutterSide
#     AC-5  TestTwoUpFooter_TheCellCostIsMeasuredAndBounded
#     AC-6  TestTwoUpFooter_APairThatCannotFitSplitsIntoSinglePages
#     AC-7  TestTwoUpFooter_TwoUpPagesNowCarryTheirFolio
#     AC-8  TestTwoUpFooter_UsesTheSameFooterGeometryAsASinglePage
#
# **What CARD-223 left, in one sentence.** It moved the icon to the footer's
# outer corner and measured each extent on its own, so a two-up page's *upper*
# slot got a box at the midline between the two drawings and its *lower* slot
# got none — the baseline book printed three links for four puzzles. This card
# gives the page one footer strip (reserved in the height by
# ``compute_pair_layout``, not improvised by the renderer) and sets both
# puzzles' groups in it.
#
# **Three claims of CARD-223's are retired here, each with its survivor named**
# (G-7):
#
# * ``TestBookQrSlot_YieldsRatherThanCollide``'s
#   ``test_a_two_up_pages_lower_slot_draws_neither`` — the lower slot's zero
#   slack and its missing icon. Survivor: AC-1 below, which asserts the lower
#   slot's extent now carries *both* groups, and AC-7, which asserts the folio
#   that corner used to hold is now on the footer line.
# * ``TestBookQrSlot_NeverPlacesInkOnTheGutterSide``'s
#   ``test_every_two_up_slot_keeps_its_icon_out_of_the_gutter_half`` — the
#   upper slot's own icon. Survivor: AC-4 below, which makes the same claim
#   about the page's real footer ink, on a narrower forbidden region, and says
#   why the half cannot be kept.
# * ``test_a_real_book_prints_both_lines_on_every_page_that_has_an_icon``'s
#   "three links for four puzzles". Survivor: AC-1's own book export, which
#   asserts four.
#
# **Where the gutter-half claim went** (AC-4). Two groups need the room they
# need: two icons, two lines and the white between them. On Book 1 that is
# 2 x 68.5 mm against a 190.5 mm usable width, of which the outer *half* of the
# trim offers only 95.25 mm — so "all the QR ink is in the outer half of the
# sheet", which CARD-223 could assert for one group, is **arithmetically
# impossible** for two, at any arrangement. The claim below is therefore
# narrowed, deliberately and with the arithmetic asserted rather than
# asserted-around: no footer ink lands in the gutter margin, nor anywhere in
# the gutter-side strip CARD-204 actually put the icon in — the placement the
# owner complained about — and the measured clearance beyond that strip is
# recorded as a bound.


#: The footer strip's depth in device pixels, stated from CON-020's own three
#: rows rather than read off :data:`INTERIOR_FOOTER_MM`, so the two are
#: compared and not re-derived (``TestTwoUpFooter_UsesTheSameFooterGeometry``).
FOOTER_STRIP_PX = 353

#: The widest line one group sets on Book 1 for a 1- or 2-digit puzzle (the
#: typed link, which runs wider than even the named invitation at those
#: lengths), and the group pitch that follows: icon + gap + line + gap.
#: Measured; asserted against the renderer's own measurement below.
GROUP_LINE_PX = 549
FOOTER_GAP_PX = 38
GROUP_PITCH_PX = QR_SLOT_PX + 2 * FOOTER_GAP_PX + GROUP_LINE_PX

#: How many cells of combined drawing height a Book 1 pair may have, with and
#: without the strip reserved, before its shared cell falls under FR-040's
#: 7.0 mm. Both stated from the usable height by hand (253.492 mm less two
#: 12 mm bands, less the strip for the second), never from
#: ``compute_pair_layout``:
#:
#:     unreserved  229.492 / 7.0 = 32.78  ->  32 cells
#:     reserved    199.605 / 7.0 = 28.51  ->  28 cells
#:
#: so the pairs this card refuses are **exactly** those whose combined drawing
#: height is 29, 30, 31 or 32 cells (AC-6).
MAX_PAIR_CELLS_UNRESERVED = 32
MAX_PAIR_CELLS_RESERVED = 28
NEWLY_REFUSED_PAIR_CELLS = frozenset({29, 30, 31, 32})


def _footer_reserve_px(spec: PageSpec) -> int:
    """The strip ``compute_pair_layout`` is told to keep, as production tells it."""
    return interior_frame(spec).footer_depth


def _two_up(
    spec: PageSpec,
    upper: Tuple[int, int, int, int] = (10, 10, 3, 3),
    lower: Optional[Tuple[int, int, int, int]] = None,
    *,
    reserve_footer: bool = True,
):
    """A production two-up pair on ``spec``: both reserves, as ``puzzle_pages`` passes them."""
    return compute_pair_layout(
        _clue_sets(*upper),
        _clue_sets(*(lower if lower is not None else upper)),
        spec,
        folio_reserve_px=_folio_reserve_px(DPI),
        footer_reserve_px=_footer_reserve_px(spec) if reserve_footer else 0,
    )


def _drawn_group_lines(numbers: Tuple[int, ...]) -> int:
    """The widest line this page's own groups set, as the renderer measures it."""
    font = _band_font(type_px(FLOOR_PT, DPI))
    return max(
        math.ceil(font.getlength(text))
        for number in numbers
        for text in (qr_group_caption(number), qr_link(number))
    )


def _two_up_render(spec_parity: PageParity, page_number: int, pair, numbers=(1, 2)):
    """A real two-up page image, drawn by the production method."""
    generator = BookPDFGenerator(corpus_book(f"card248-{spec_parity.name}-{page_number}"))
    payloads = [_payload(10, 10, 3, 3), _payload(10, 10, 3, 3)]
    plan = PuzzlePagePlan(page_number, numbers, pair)
    return generator, plan, payloads


def _footer_group_ink(generator, plan, payloads, monkeypatch) -> np.ndarray:
    """The two-up page's **own footer-group pixels** — icon *and* both lines.

    CARD-223's ``_qr_ink`` technique, carried to the admin renderer and to the
    caption as well as the glyph: the page as it is drawn, differenced against
    the same page drawn with both of the group's drawers suppressed. Every
    pixel this mask holds is one the group put there, and no pixel it misses
    is one the group put somewhere else — in particular it is **not** "the
    pixels inside the boxes the layout reported", which would assume the
    answer AC-4 is asking about.
    """
    drawn = np.asarray(generator._two_up_page(plan, payloads).convert("L"))
    monkeypatch.setattr(generator_module, "_draw_qr_placeholder", lambda draw, icon: None)
    monkeypatch.setattr(generator_module, "_draw_qr_caption", lambda *a, **k: None)
    bare = np.asarray(generator._two_up_page(plan, payloads).convert("L"))
    monkeypatch.undo()
    return drawn != bare


def _retired_gutter_strip(spec: PageSpec, layout: "Layout") -> Tuple[int, int]:
    """The strip CARD-204 put the icon in, as ``(left, right)`` pixels.

    The gutter margin **plus** one icon's width of the usable area — i.e.
    everything from the trim edge through the box the owner found unscannable.
    Derived from the spec's own parity and :data:`QR_SLOT_MM`, not written out,
    so it moves with the geometry it is about.
    """
    placement = layout.page
    if spec.parity is PageParity.ODD:
        return 0, placement.usable_left + QR_SLOT_PX
    return placement.usable_right - QR_SLOT_PX, layout.width


# --------------------------------------------------------------------------
# AC-1 — both links
# --------------------------------------------------------------------------


class TestTwoUpFooter_CarriesBothPuzzlesLinks:
    """One footer strip, two groups — icon, caption and typed link each — and
    the baseline book prints four links for four puzzles where it printed
    three."""

    @pytest.mark.parametrize("parity", [PageParity.ODD, PageParity.EVEN])
    def test_the_strip_carries_two_whole_groups_inside_the_footer_row(
        self, parity: PageParity
    ) -> None:
        """Geometry, before any ink: two insets, two icons, two caption
        anchors, all inside the usable area and inside the footer's own row,
        and the two groups disjoint from each other."""
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        frame = interior_frame(spec)
        placement = pair.lower.page

        insets = qr_group_insets(pair.lower, _drawn_group_lines((1, 2)), 2)
        assert insets is not None and len(insets) == 2
        assert insets[0] == 0, "the first group is the outer corner itself"
        assert insets[1] == GROUP_PITCH_PX, insets

        boxes = []
        for inset in insets:
            icon = qr_slot(pair.lower, inset_px=inset)
            caption = qr_caption(pair.lower, inset_px=inset)
            assert icon is not None and caption is not None, inset
            # Inside the usable area, and inside the strip the frame reserves.
            assert placement.usable_left <= icon.left < icon.right <= placement.usable_right
            assert icon.top > frame.footer_rule.y and icon.bottom == frame.page_bottom
            assert icon.top <= caption.caption_baseline < caption.link_baseline <= icon.bottom
            boxes.append((icon.left, icon.top, icon.right, icon.bottom))
        assert _disjoint(boxes[0], boxes[1]), boxes

    def test_the_baseline_book_prints_four_links_for_four_puzzles(
        self, monkeypatch
    ) -> None:
        """The defect, as a count, on the project's own baseline book: its
        puzzles 1 and 2 share a two-up page, and before this card puzzle 2
        printed neither line. Read off the book's own page plan rather than
        written down, so it moves with the pairing instead of pinning a stale
        number — but the *count* is asserted against the number of puzzles,
        which is the claim.
        """
        generator = BookPDFGenerator(corpus_book())
        puzzles = baseline_puzzles()
        plan = generator.section_plan(puzzles)
        two_up_numbers = [
            page.numbers for page in plan.pages
            if getattr(page, "numbers", None) and page.is_two_up
        ]
        assert two_up_numbers, "this book is supposed to hold a two-up page"

        calls = _text_calls(generator, puzzles, monkeypatch)
        links = sorted(
            call["text"] for call in calls if call["text"].startswith("nonogram.example/")
        )
        assert links == sorted(qr_link(number) for number in range(1, len(puzzles) + 1)), links
        assert len(links) == len(puzzles) == 4, (len(links), len(puzzles))

    def test_every_group_sets_both_of_its_lines(self, monkeypatch) -> None:
        """Icon, invitation and link are one group: on a two-up page there are
        two invitations and two links, never an icon with no words under it."""
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec)
        assert pair is not None
        generator, plan, payloads = _two_up_render(PageParity.ODD, 5, pair)
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        invitations = [call for call in calls if QR_CAPTION_TEXT in call["text"]]
        links = [call for call in calls if call["text"].startswith("nonogram.example/")]
        assert len(invitations) == len(links) == 2, (invitations, links)


# --------------------------------------------------------------------------
# AC-2 — each group's link is its own slot's
# --------------------------------------------------------------------------


class TestTwoUpFooter_EachGroupCarriesItsOwnSlotsLink:
    """The defect this catches is two groups both showing one puzzle's link —
    or, just as wrong, the upper puzzle's link set in the lower puzzle's
    group."""

    @pytest.mark.parametrize("parity,page_number", [(PageParity.ODD, 5), (PageParity.EVEN, 6)])
    def test_each_group_is_set_at_its_own_inset_with_its_own_number(
        self, parity: PageParity, page_number: int, monkeypatch
    ) -> None:
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        numbers = (7, 8)
        generator, plan, payloads = _two_up_render(parity, page_number, pair, numbers)
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)

        insets = qr_group_insets(pair.lower, _drawn_group_lines(numbers), 2)
        assert insets is not None
        # Reading order: the upper puzzle is the group a reader meets first,
        # left to right — the inner one on a right-hand page, the outer one on
        # a left-hand one. Expected x per puzzle, from the layout.
        ordered = tuple(reversed(insets)) if parity is PageParity.ODD else insets
        expected = {}
        for number, inset in zip(numbers, ordered, strict=True):
            caption = qr_caption(pair.lower, inset_px=inset)
            expected[qr_link(number)] = caption.x

        drawn = {
            call["text"]: call["xy"][0]
            for call in calls
            if call["text"].startswith("nonogram.example/")
        }
        assert drawn == expected, (drawn, expected)
        assert len(set(drawn.values())) == 2, "the two links are set at two anchors"

    def test_the_two_links_are_two_different_links(self, monkeypatch) -> None:
        """The narrow form of the defect, stated on its own so it cannot be
        satisfied by a page that sets one link twice."""
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec)
        assert pair is not None
        generator, plan, payloads = _two_up_render(PageParity.ODD, 5, pair, (41, 42))
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        links = [
            call["text"] for call in calls if call["text"].startswith("nonogram.example/")
        ]
        assert sorted(links) == [qr_link(41), qr_link(42)], links

    def test_both_links_still_come_from_the_one_constant(self) -> None:
        """G-1: two groups, one template. ``qr_link`` is still the only reader
        of :data:`QR_LINK_TEMPLATE`, and the renderer's two-group drawer calls
        it rather than formatting the host itself."""
        source = inspect.getsource(generator_module.BookPDFGenerator._draw_two_up_qr_groups)
        assert "nonogram.example" not in source
        assert "qr_link" in source


# --------------------------------------------------------------------------
# AC-3 — each group names its puzzle number
# --------------------------------------------------------------------------


class TestTwoUpFooter_EachGroupNamesItsPuzzleNumber:
    """A vertically stacked pair of puzzles maps onto a side-by-side pair of
    links, so each group says which puzzle it belongs to in words.

    **The convention, stated: the upper puzzle's group is the one a reader
    meets first, left to right** — the inner group on an ``ODD`` (right-hand)
    page, where the row packs rightward from the outer margin, and the outer
    group on an ``EVEN`` one. Reading order is the only order a reader
    already has for a row of two; the positions mirror by parity as every
    other mark on a book page does, and which puzzle is named first does not,
    because nobody reads a left-hand page backwards. The number is the primary
    cue and the order the redundant second one.
    """

    def test_each_groups_invitation_names_its_own_puzzle(self, monkeypatch) -> None:
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec)
        assert pair is not None
        numbers = (123, 124)
        generator, plan, payloads = _two_up_render(PageParity.ODD, 5, pair, numbers)
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        invitations = sorted(
            call["text"] for call in calls if QR_CAPTION_TEXT in call["text"]
        )
        assert invitations == sorted(qr_group_caption(number) for number in numbers)
        for number, text in zip(sorted(numbers), invitations, strict=True):
            assert str(number) in text and QR_CAPTION_TEXT in text

    @pytest.mark.parametrize("parity,page_number", [(PageParity.ODD, 5), (PageParity.EVEN, 6)])
    def test_the_upper_puzzles_group_is_the_leftmost_at_both_parities(
        self, parity: PageParity, page_number: int, monkeypatch
    ) -> None:
        """The convention, as drawn ink positions rather than as prose."""
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        upper_number, lower_number = 7, 8
        generator, plan, payloads = _two_up_render(
            parity, page_number, pair, (upper_number, lower_number)
        )
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        font = _band_font(type_px(FLOOR_PT, DPI))

        def left_edge(number: int) -> float:
            (call,) = [c for c in calls if c["text"] == qr_link(number)]
            width = font.getlength(call["text"])
            return call["xy"][0] - width if call["anchor"] == "rb" else call["xy"][0]

        assert left_edge(upper_number) < left_edge(lower_number), (
            "the upper puzzle's group must be the one met first reading left to right"
        )

    def test_naming_the_puzzle_costs_the_row_nothing_it_does_not_have(self) -> None:
        """The measurement that makes AC-3 free rather than a trade: a group's
        width is set by its **widest** line, and the typed link already runs
        wider than the bare invitation, so naming the puzzle moves the row by
        a couple of millimetres at most and the pair still fits with room.

        Measured at the footer's own 10 pt face on Book 1 (190.5 mm usable):
        the bare invitation 25.4 mm, the link 46.5 mm, a named invitation
        48.0 mm at three digits — so two groups measure 140.0 mm there,
        against 137.0 mm unnamed, and 50.5 mm is left over.
        """
        font = _band_font(type_px(FLOOR_PT, DPI))
        assert round(font.getlength(QR_CAPTION_TEXT)) == 300
        assert round(font.getlength(qr_link(123))) == 549
        assert round(font.getlength(qr_group_caption(123))) == 567
        spec = _spec()
        usable = interior_frame(spec).header_rule.right - interior_frame(spec).header_rule.left
        assert usable == 2250
        named = QR_SLOT_PX + 2 * FOOTER_GAP_PX + 567
        assert 2 * named - FOOTER_GAP_PX < usable
        spare_mm = (usable - (2 * named - FOOTER_GAP_PX)) / PX_PER_MM
        assert spare_mm > 20.0, spare_mm

    def test_the_invitations_words_are_still_one_constant(self) -> None:
        """G-1: the named form is built from :data:`QR_CAPTION_TEXT` and
        :data:`BAND_SEPARATOR`, not spelled a second time — so the owner's own
        words exist once in the package."""
        assert qr_group_caption(5).endswith(QR_CAPTION_TEXT)
        assert BAND_SEPARATOR in qr_group_caption(5)
        source = inspect.getsource(qr_group_caption)
        assert "Solve" not in source.split('"""')[-1], "the words are interpolated, not retyped"


# --------------------------------------------------------------------------
# AC-4 — never the spine, on a new page kind
# --------------------------------------------------------------------------


class TestTwoUpFooter_NeverPlacesInkOnTheGutterSide:
    """The owner's original complaint, which this card must not reintroduce on
    a page kind that now carries two groups instead of none.

    Survivor of CARD-223's ``test_every_two_up_slot_keeps_its_icon_out_of_the_gutter_half``
    (G-7), with its forbidden region narrowed from the gutter **half** of the
    sheet to the gutter margin plus the strip CARD-204 actually used — and the
    narrowing is asserted, not asserted-around, in
    :meth:`test_the_gutter_half_cannot_be_kept_for_two_groups_and_here_is_why`.
    """

    @pytest.mark.parametrize("parity,page_number", [(PageParity.ODD, 5), (PageParity.EVEN, 6)])
    def test_no_footer_group_pixel_lands_in_the_retired_gutter_strip(
        self, parity: PageParity, page_number: int, monkeypatch
    ) -> None:
        """Measured ink, both parities: every pixel the two groups draw lies
        outside the gutter margin and outside the icon-wide strip just inside
        it — the placement the owner found unscannable."""
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        generator, plan, payloads = _two_up_render(parity, page_number, pair)
        mask = _footer_group_ink(generator, plan, payloads, monkeypatch)
        assert mask.any(), "the page drew no footer-group ink at all, so this proves nothing"

        left, right = _retired_gutter_strip(spec, pair.lower)
        assert not mask[:, left:right].any(), (
            f"a {parity} two-up page put footer-group ink in columns {left}..{right}"
        )

    @pytest.mark.parametrize("parity", [PageParity.ODD, PageParity.EVEN])
    def test_the_control_the_retired_placement_would_have_failed_this(
        self, parity: PageParity, monkeypatch
    ) -> None:
        """The claim above discriminates (ADR-0039/R1): draw one of the two
        groups' icons where CARD-204 put it — flush with the usable area's
        **gutter**-side edge — and the identical check catches it.

        The icon is drawn into the real page by the real drawer, so what is
        under test is the check and not a hand-made mask.
        """
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        placement = pair.lower.page
        if parity is PageParity.ODD:
            retired = QrSlot(
                left=placement.usable_left,
                top=placement.usable_bottom - QR_SLOT_PX,
                right=placement.usable_left + QR_SLOT_PX,
                bottom=placement.usable_bottom,
            )
        else:
            retired = QrSlot(
                left=placement.usable_right - QR_SLOT_PX,
                top=placement.usable_bottom - QR_SLOT_PX,
                right=placement.usable_right,
                bottom=placement.usable_bottom,
            )
        generator, plan, payloads = _two_up_render(parity, 5, pair)

        real = generator_module._draw_qr_placeholder

        def gutter_side(draw, icon):
            real(draw, retired)

        monkeypatch.setattr(generator_module, "_draw_qr_placeholder", gutter_side)
        mask = _footer_group_ink(generator, plan, payloads, monkeypatch)
        left, right = _retired_gutter_strip(spec, pair.lower)
        assert mask[:, left:right].any(), (
            "the gutter-side placement was not caught, so this file's notion of "
            "the forbidden strip is wrong and the claim above is empty"
        )

    def test_unequal_margins_put_the_outer_group_one_outside_margin_in(self) -> None:
        """**The mirroring evidence** (AC-4), made where it is observable.

        On a sheet whose gutter is 19.0 mm and whose outside margin is 7.0 mm,
        the outer group's icon hugs the **outside** margin at both parities, on
        opposite sides. Reading the gutter instead would put it 19.0 mm in —
        142 px away — so this fails if the sides are swapped or the wrong
        margin is read. ``test_on_the_default_profile_the_same_distance_claim_is_an_identity``
        above records why the Book 1 form of this is *not* evidence.
        """
        outside_px = _px(UNEQUAL_OUTSIDE_MM)
        gutter_px = _px(UNEQUAL_GUTTER_MM)
        assert outside_px != gutter_px, "the fixture must have unequal margins to prove anything"

        odd_pair = _two_up(_unequal_spec(PageParity.ODD))
        even_pair = _two_up(_unequal_spec(PageParity.EVEN))
        assert odd_pair is not None and even_pair is not None
        trim = odd_pair.lower.width
        widest = _drawn_group_lines((1, 2))

        odd_insets = qr_group_insets(odd_pair.lower, widest, 2)
        even_insets = qr_group_insets(even_pair.lower, widest, 2)
        assert odd_insets == even_insets and odd_insets is not None

        odd = [qr_slot(odd_pair.lower, inset_px=inset) for inset in odd_insets]
        even = [qr_slot(even_pair.lower, inset_px=inset) for inset in even_insets]

        # A right-hand page: the outer group's own outer edge is the right, one
        # outside margin in from the trim — not one gutter in.
        assert trim - odd[0].right == outside_px
        assert trim - odd[0].right != gutter_px
        # A left-hand page: the outer edge is the left, the same figure.
        assert even[0].left == outside_px
        assert even[0].left != gutter_px
        # And the whole row is a true mirror, group by group.
        for one, other in zip(odd, even, strict=True):
            assert one.left == trim - other.right
            assert one.right == trim - other.left

    def test_the_gutter_half_cannot_be_kept_for_two_groups_and_here_is_why(self) -> None:
        """The narrowing, asserted (ADR-0039/R3): the row of two groups is
        **wider than the outer half of the trim**, so no arrangement of them
        keeps every pixel out of the gutter half — the forbidden region had to
        shrink, and by how much is recorded rather than glossed.

        Measured on Book 1: the ink two groups need is two icons plus two
        lines plus the white between, 1682 px (142.4 mm); the outer half of
        the trim holds 1125 px (95.25 mm) of usable width. The clearance the
        narrowed claim actually buys is asserted too, so a later card that
        pushes the row toward the spine reds here.
        """
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec)
        assert pair is not None
        placement = pair.lower.page
        widest = _drawn_group_lines((1, 2))
        insets = qr_group_insets(pair.lower, widest, 2)
        assert insets is not None

        row_px = 2 * (QR_SLOT_PX + FOOTER_GAP_PX + widest) + FOOTER_GAP_PX
        outer_half_px = placement.usable_right - pair.lower.width // 2
        assert row_px > outer_half_px, (row_px, outer_half_px)

        # The clearance the narrowed claim buys: the gutter-side-most ink the
        # row can reach, against the strip it must stay out of. Computed for
        # the widest line the renderer can EVER set, not just this page's.
        worst = _qr_group_line_px(DPI)
        worst_pitch = QR_SLOT_PX + 2 * FOOTER_GAP_PX + worst
        innermost = placement.usable_right - worst_pitch - QR_SLOT_PX - FOOTER_GAP_PX - worst
        _, strip_right = _retired_gutter_strip(spec, pair.lower)
        # 240 px (20.3 mm) of clearance beyond the retired strip, for the
        # worst number the face can ever set — a whole icon's width and more,
        # recorded as the measured bound the narrowed claim is worth.
        assert innermost - strip_right == 240, (innermost, strip_right)
        assert innermost - strip_right >= QR_SLOT_PX
        assert innermost == 626, innermost

    @pytest.mark.parametrize("parity,page_number", [(PageParity.ODD, 5), (PageParity.EVEN, 6)])
    def test_the_footer_ink_stays_inside_the_usable_area(
        self, parity: PageParity, page_number: int, monkeypatch
    ) -> None:
        """The other edge of the same claim: nothing runs off into the trim
        margin the printer cuts through, either."""
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        generator, plan, payloads = _two_up_render(parity, page_number, pair)
        mask = _footer_group_ink(generator, plan, payloads, monkeypatch)
        placement = pair.lower.page
        columns = np.where(mask.any(axis=0))[0]
        rows = np.where(mask.any(axis=1))[0]
        assert placement.usable_left <= columns[0] and columns[-1] <= placement.usable_right
        assert rows[0] > interior_frame(spec).footer_rule.y
        assert rows[-1] <= placement.usable_bottom

    def test_no_two_up_page_carries_qr_ink_above_its_footer_strip(
        self, monkeypatch
    ) -> None:
        """The retired midline icon, asserted as a removal. CARD-223 measured
        each slot on its own extent, so the **upper** slot got a box at the
        midline between the two drawings — floating page furniture, and only
        one of the page's two puzzles served. Every footer-group pixel this
        page draws is now inside the footer strip.

        The pair here is deliberately one whose upper slot still *reports* a
        box of its own (its gap between the slots clears the strip's own
        depth), so the claim is about what the renderer asks for and not about
        a geometry that happens to answer ``None``.
        """
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec, (10, 10, 1, 1))
        assert pair is not None
        assert qr_slot(pair.upper) is not None, (
            "this pair's upper slot should still report a midline box, or the "
            "removal below is proved by an accident of the geometry"
        )
        generator, plan, payloads = _two_up_render(PageParity.ODD, 5, pair)
        mask = _footer_group_ink(generator, plan, payloads, monkeypatch)
        rows = np.where(mask.any(axis=1))[0]
        assert rows[0] > interior_frame(spec).footer_rule.y, rows[0]


# --------------------------------------------------------------------------
# AC-5 — the cell cost, measured and bounded
# --------------------------------------------------------------------------


def _expected_pair_cell_mm(
    across: int, lower_across: int, total_down: int, *, strip: bool
) -> float:
    """FR-040's shared cell on Book 1, written out from the sheet's own
    millimetres — **both** reserves included, as production passes them.

    An independent second implementation, not a call into
    ``compute_pair_layout``: ``min(cap, usable width / the wider drawing's
    columns, (usable height - two bands - the strip) / both drawings' rows)``,
    re-fitted against a usable width one folio reserve narrower when the lower
    drawing's own spare at the first answer falls short of that reserve
    (CARD-204 Fix 4's documented rule, restated here rather than imported).
    The strip is stated as :data:`FOOTER_STRIP_PX` pixels converted back to
    millimetres, which is how the production call converts the reserve it is
    handed.
    """
    usable_width = BOOK1_WIDTH_MM - GUTTER_MM - OUTSIDE_MM
    usable_height = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM
    if strip:
        usable_height -= FOOTER_STRIP_PX / PX_PER_MM
    cell = min(STANDARD_CELL_MM, usable_width / across, usable_height / total_down)
    folio_px = _folio_reserve_px(DPI)
    if usable_width * PX_PER_MM - lower_across * cell * PX_PER_MM < folio_px:
        cell = min(
            STANDARD_CELL_MM,
            (usable_width - folio_px / PX_PER_MM) / across,
            usable_height / total_down,
        )
    return cell


class TestTwoUpFooter_TheCellCostIsMeasuredAndBounded:
    """What the strip costs the pairs that keep pairing, per pair, against an
    independently written formula — and the figure CARD-248's own card guessed
    at, measured.

    **The card's "roughly 0.15 mm off the cell, about 2 %" for the tall 15-row
    pairs is wrong, and the direction matters.** That arithmetic counted the
    two 12 mm bands as spare the strip could take; they are not spare. A
    Book 1 pair's whole free vertical slack is the gap *between* its slots,
    and a 15-row depth-1 pair's is **zero** — the pair is already height-bound
    — so the strip cannot be found anywhere and the pair is **refused**
    outright rather than printed 2 % smaller (AC-6). The real worst surviving
    cost is the 13-row band, measured below: 7.5000 -> 7.1287 mm, **4.95 %**.
    """

    def test_the_strip_is_free_wherever_the_gap_between_the_slots_already_holds_it(
        self,
    ) -> None:
        """The card's own "the room already exists" claim, re-derived: a pair
        whose slots sit at least one strip apart commits the identical cell
        with the strip reserved — the strip is taken out of that gap, not out
        of the cell."""
        spec = _spec()
        checked = 0
        for rows in (10, 11, 12):
            bare = _two_up(spec, (10, rows, 1, 1), reserve_footer=False)
            reserved = _two_up(spec, (10, rows, 1, 1))
            assert bare is not None and reserved is not None, rows
            gap = bare.lower.page.usable_top - bare.upper.page.drawing_bottom
            assert gap >= FOOTER_STRIP_PX, (rows, gap)
            assert reserved.cell_mm == bare.cell_mm, (rows, bare.cell_mm, reserved.cell_mm)
            # And the gap really did pay for it.
            assert (
                reserved.lower.page.usable_top - reserved.upper.page.drawing_bottom
                == gap - FOOTER_STRIP_PX
            )
            checked += 1
        assert checked == 3

    def test_the_committed_cell_is_the_independently_written_fit(self) -> None:
        """Every pair that still pairs commits exactly
        ``min(cap, width fit, (height - two bands - strip) / rows)`` — so no
        pair loses more than the strip forces it to."""
        spec = _spec()
        checked = 0
        for columns in range(MIN_SIZE, 25):
            for rows in range(MIN_SIZE, 16):
                pair = _two_up(spec, (columns, rows, 1, 1))
                if pair is None:
                    continue
                across = 1 + columns
                total_down = 2 * (1 + rows)
                expected = _expected_pair_cell_mm(across, across, total_down, strip=True)
                assert abs(pair.cell_mm - expected) < 1e-6, (
                    columns, rows, pair.cell_mm, expected
                )
                checked += 1
        assert checked >= 45, checked

    def test_the_worst_surviving_cost_is_the_thirteen_row_band_at_4_95_percent(
        self,
    ) -> None:
        """The figure the card asked for, measured and pinned.

        13-row depth-1 pairs are the deepest that still pair with the strip
        reserved: 28 cells of drawing height, which 199.605 mm fits at
        7.1287 mm. Unreserved they print at the 7.5 mm cap, so the strip
        costs them 0.3713 mm — **4.95 %**, not the card's guessed 2 %.
        """
        spec = _spec()
        worst = 0.0
        worst_case = None
        for columns in range(MIN_SIZE, 25):
            for rows in range(MIN_SIZE, 16):
                bare = _two_up(spec, (columns, rows, 1, 1), reserve_footer=False)
                reserved = _two_up(spec, (columns, rows, 1, 1))
                if bare is None or reserved is None:
                    continue
                drop = 100 * (bare.cell_mm - reserved.cell_mm) / bare.cell_mm
                if drop > worst:
                    worst, worst_case = drop, (columns, rows, bare.cell_mm, reserved.cell_mm)
        assert worst_case is not None
        assert worst_case[1] == 13, worst_case
        assert abs(worst_case[2] - STANDARD_CELL_MM) < 1e-9
        assert abs(worst_case[3] - 7.1287) < 1e-3, worst_case
        assert abs(worst - 4.95) < 0.01, (worst, worst_case)

    def test_both_slots_keep_one_shared_cell_with_the_strip_reserved(self) -> None:
        """G-4, which CARD-226 builds its aligned bottoms on: the reserve is
        taken from the page, never from one slot, so the two slots print at the
        same cell as each other."""
        spec = _spec()
        checked = 0
        for columns, rows in ((10, 10), (12, 11), (20, 13), (24, 12)):
            pair = _two_up(spec, (columns, rows, 1, 1), (columns, rows, 2, 1))
            if pair is None:
                continue
            assert pair.upper.page.cell_mm == pair.lower.page.cell_mm == pair.cell_mm
            checked += 1
        assert checked >= 3, checked


# --------------------------------------------------------------------------
# AC-6 — a pair that no longer fits prints as two single pages
# --------------------------------------------------------------------------


class TestTwoUpFooter_APairThatCannotFitSplitsIntoSinglePages:
    """The exemption this card grants, as an **exact** set rather than a range
    (ADR-0039/R1, R3), with what happens to its members asserted through the
    production walk.

    **The exact set, on Book 1, and why it is exact rather than a corpus
    sample.** ``compute_pair_layout``'s verdict is a function of two numbers
    only — the wider drawing's columns and the two drawings' combined rows —
    so the set can be stated over the second of them and be complete. The
    usable height is 253.492 mm; two 12 mm bands leave 229.492 mm, and
    FR-040's 7.0 mm floor therefore admits at most 32 cells of drawing height.
    One 353 px strip leaves 199.605 mm, which admits at most 28. So the pairs
    this card stops pairing are **exactly** those whose combined drawing
    height is 29, 30, 31 or 32 cells — and no others, at any width.

    **What they do instead**: two single pages, each with its own footer and
    its own link. That is option 1 of the four the owner was shown, it costs
    one interior page per refused pair, and it is never a two-up page with a
    missing link.

    **It is not a small set.** On the depth-1 equal-size sweep below, 30 of
    the 90 pairs that paired before this card stop pairing; on a seeded
    corpus with real clue depths the share is higher still, because a pair
    deep enough to pair at all is usually already height-bound. The measured
    figures are in the card's report; they are far above the ~2 % the card's
    own prose estimated, and the cost is a longer interior.
    """

    def test_the_refused_set_is_exactly_the_29_to_32_cell_pairs(self) -> None:
        """Over every width and height a book puzzle can have, the verdict
        changes for exactly the combined-height band named above — compared
        against the independently written fit, not against the function."""
        spec = _spec()
        changed_heights = set()
        kept_heights = set()
        checked = 0
        # Unequal heights as well as equal ones, so the band's **odd** members
        # (29 and 31 cells) are reachable at all — an equal pair's combined
        # height is always even, and a sweep of those alone would report a
        # smaller set and look like agreement.
        for columns in (MIN_SIZE, 15, 20, 24):
            for upper_rows in range(MIN_SIZE, MAX_SIZE + 1):
                for lower_rows in range(MIN_SIZE, MAX_SIZE + 1):
                    upper = (columns, upper_rows, 1, 1)
                    lower = (columns, lower_rows, 1, 1)
                    bare = _two_up(spec, upper, lower, reserve_footer=False)
                    reserved = _two_up(spec, upper, lower)
                    checked += 1
                    if bare is None:
                        assert reserved is None, (columns, upper_rows, lower_rows)
                        continue
                    total_down = (1 + upper_rows) + (1 + lower_rows)
                    if reserved is None:
                        changed_heights.add(total_down)
                    else:
                        kept_heights.add(total_down)
        assert checked == 4 * 441
        assert changed_heights == NEWLY_REFUSED_PAIR_CELLS, changed_heights
        assert not (kept_heights & NEWLY_REFUSED_PAIR_CELLS), kept_heights
        assert max(kept_heights) == MAX_PAIR_CELLS_RESERVED, kept_heights

    def test_the_boundary_is_where_the_hand_arithmetic_puts_it(self) -> None:
        """The control for the set above (ADR-0039/R1): 28 cells is accepted
        and 29 refused, and the two figures come from the sheet by hand, not
        from the function under test."""
        pair_height_mm = BOOK1_HEIGHT_MM - TOP_MM - BOTTOM_MM - 2 * BAND_MM
        assert abs(pair_height_mm - 229.492) < 1e-9
        reserved_mm = pair_height_mm - FOOTER_STRIP_PX / PX_PER_MM
        assert abs(reserved_mm - 199.6047) < 1e-3, reserved_mm
        assert int(pair_height_mm / TWO_UP_MINIMUM_MM) == MAX_PAIR_CELLS_UNRESERVED
        assert int(reserved_mm / TWO_UP_MINIMUM_MM) == MAX_PAIR_CELLS_RESERVED
        spec = _spec()
        # 14 drawing rows a slot (a depth-1 13-row puzzle) is 28 cells: paired.
        assert _two_up(spec, (10, 13, 1, 1)) is not None
        # 15 a slot (a depth-1 14-row puzzle) is 30: refused.
        assert _two_up(spec, (10, 14, 1, 1)) is None
        # 29, the odd member of the band, needs an unequal pair.
        assert _two_up(spec, (10, 13, 1, 1), (10, 14, 1, 1)) is None

    def test_such_a_pair_prints_as_two_single_pages_each_with_its_own_link(
        self, monkeypatch
    ) -> None:
        """Through the production walk and a real export: two puzzles in the
        refused band become two plans of one puzzle each, two pages, and two
        links — never one page with one link."""
        generator = BookPDFGenerator(corpus_book("card248-split"))
        payloads = [_payload(10, 14, 1, 1), _payload(10, 14, 1, 1)]
        plans = generator.puzzle_pages(payloads)
        assert [plan.numbers for plan in plans] == [(1,), (2,)], plans
        assert all(plan.pair is None for plan in plans)

        calls = _text_calls(generator, _refusing_puzzles(), monkeypatch)
        links = sorted(
            call["text"] for call in calls if call["text"].startswith("nonogram.example/")
        )
        pages = {
            call["page"]
            for call in calls
            if call["text"].startswith("nonogram.example/")
        }
        assert links == [qr_link(1), qr_link(2)], links
        assert len(pages) == 2, pages

    def test_the_same_pair_one_cell_shallower_does_share_a_page(
        self, monkeypatch
    ) -> None:
        """The control the claim above needs: one cell of clue gutter less and
        the identical two puzzles pair, on one page, with both links on it. If
        the refusal ever became a blanket rule this reds."""
        generator = BookPDFGenerator(corpus_book("card248-nosplit"))
        payloads = [_payload(10, 13, 1, 1), _payload(10, 13, 1, 1)]
        plans = generator.puzzle_pages(payloads)
        assert [plan.numbers for plan in plans] == [(1, 2)], plans
        assert plans[0].pair is not None

    def test_a_trim_too_narrow_for_two_groups_does_not_pair_either(self) -> None:
        """The horizontal half of the same exemption, and a real storable
        trim rather than a hypothetical: a 10 cm wide sheet (``MIN_TRIM_CM``)
        tall enough to hold two puzzles has room for one group and not two, so
        the walk refuses the pair instead of drawing a page with one link.

        The refusal is made on :func:`_qr_group_line_px`'s page-independent
        ceiling, so it is a property of the trim and the face — never of this
        page's own numbers (INV-010).
        """
        tall_narrow = _spec(width_mm=120.0, height_mm=480.0, gutter_mm=9.5, outside_mm=6.4)
        pair = _two_up(tall_narrow, (10, 10, 1, 1))
        assert pair is not None, "this trim must be able to hold the pair at all"
        assert qr_group_insets(pair.lower, _qr_group_line_px(DPI), 1) is not None, (
            "one group fits, so the refusal below is about the second one"
        )
        assert qr_group_insets(pair.lower, _qr_group_line_px(DPI), 2) is None

        generator = BookPDFGenerator(_narrow_book())
        plans = generator.puzzle_pages([_payload(10, 10, 1, 1), _payload(10, 10, 1, 1)])
        assert [plan.numbers for plan in plans] == [(1,), (2,)], plans

    def test_book_ones_own_trim_is_the_control_for_that_refusal(self) -> None:
        """…and the trim this project actually prints has room for two groups
        with millimetres to spare, so the narrow-trim refusal is a measured
        corner and not a rule that quietly unpairs real books."""
        spec = _spec()
        pair = _two_up(spec)
        assert pair is not None
        assert qr_group_insets(pair.lower, _qr_group_line_px(DPI), 2) is not None
        assert qr_group_insets(pair.lower, _qr_group_line_px(DPI), 3) is None, (
            "three groups do not fit — recorded so the spare is known to be finite"
        )


# --------------------------------------------------------------------------
# AC-7 — the folio arrives
# --------------------------------------------------------------------------


class TestTwoUpFooter_TwoUpPagesNowCarryTheirFolio:
    """A gain to claim deliberately: a two-up page had **no** footer, so
    CARD-222's frame refused the strip and the page kept CARD-200's
    bottom-outer-corner folio. With the strip reserved it carries the footer
    rule and the centred folio like every other puzzle page.

    Survivor of ``tests/test_book_page_frame.py``'s
    ``TestBookPageFrame_TwoUpKeepsItsOuterFolio`` (G-7), which asserted the
    opposite and is retargeted there to the exemption that is left.
    """

    @pytest.mark.parametrize("parity,page_number", [(PageParity.ODD, 5), (PageParity.EVEN, 6)])
    def test_the_footer_group_is_drawn_and_the_folio_is_on_its_line(
        self, parity: PageParity, page_number: int, monkeypatch
    ) -> None:
        spec = _spec(parity=parity)
        pair = _two_up(spec)
        assert pair is not None
        frame = interior_frame(spec)
        # The precondition, confirmed rather than assumed: the lower slot's
        # drawing now stops exactly on the footer rule.
        assert pair.lower.page.drawing_bottom == frame.footer_rule.y

        generator, plan, payloads = _two_up_render(parity, page_number, pair)
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        folios = [call for call in calls if call["text"] == str(page_number)]
        assert len(folios) == 1, calls
        assert folios[0]["xy"] == (frame.folio_x, frame.baseline), folios
        assert folios[0]["anchor"] == "mb", folios

    def test_the_frames_own_verdict_says_the_strip_was_drawn(self) -> None:
        """Not read off the ink: ``_draw_page_frame`` returns whether it drew
        the footer group, and on a reserved two-up page it returns ``True``
        where it returned ``False`` before this card."""
        spec = _spec()
        frame = interior_frame(spec)
        for reserve, expected in ((True, True), (False, False)):
            pair = _two_up(spec, reserve_footer=reserve)
            assert pair is not None, reserve
            canvas = Image.new("RGB", (pair.lower.width, pair.lower.height), (255, 255, 255))
            drawn = _draw_page_frame(
                ImageDraw.Draw(canvas),
                frame,
                5,
                DPI,
                size_label=None,
                content_bottom=pair.lower.page.drawing_bottom,
                content_right=pair.lower.page.drawing_right,
                content_left=pair.lower.page.drawing_left,
            )
            assert drawn is expected, (reserve, drawn)

    def test_the_folio_is_not_also_in_the_corner(self, monkeypatch) -> None:
        """One page number, not two: the corner fallback and the footer line
        are alternatives, and gaining the second must not leave the first."""
        spec = _spec(parity=PageParity.ODD)
        pair = _two_up(spec)
        assert pair is not None
        frame = interior_frame(spec)
        generator, plan, payloads = _two_up_render(PageParity.ODD, 5, pair)
        calls = _page_text_calls(generator, plan, payloads, monkeypatch)
        folios = [call for call in calls if call["text"] == "5"]
        assert len(folios) == 1, folios
        assert folios[0]["xy"][1] == frame.baseline
        assert folios[0]["xy"][1] != frame.page_bottom


# --------------------------------------------------------------------------
# AC-8 — one definition of a footer
# --------------------------------------------------------------------------


class TestTwoUpFooter_UsesTheSameFooterGeometryAsASinglePage:
    """G-1/AC-8: a two-up page's footer is **the** footer, not a second
    definition of one for pairs."""

    def test_the_strip_the_pair_reserves_is_the_strip_the_frame_draws(self) -> None:
        """One figure, read by both: the reserve handed to
        ``compute_pair_layout`` is ``InteriorFrame.footer_depth``, and the
        lower slot's resulting slack is exactly that — so the drawing stops
        on the rule the frame strokes, by construction."""
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            frame = interior_frame(spec)
            assert frame.footer_depth == FOOTER_STRIP_PX
            assert frame.footer_depth == round(INTERIOR_FOOTER_MM * PX_PER_MM)
            pair = _two_up(spec)
            assert pair is not None
            placement = pair.lower.page
            assert placement.usable_bottom - placement.drawing_bottom == frame.footer_depth
            assert placement.drawing_bottom == frame.footer_rule.y

    def test_the_outer_group_sits_where_a_single_pages_group_sits(self) -> None:
        """The same box, to the pixel: a two-up page's outer group is a single
        page's group on the same sheet — same icon box, same caption anchor,
        same two baselines."""
        checked = 0
        for parity in (PageParity.ODD, PageParity.EVEN):
            spec = _spec(parity=parity)
            single = compute_layout(*_clue_sets(20, 20, 1, 1), spec)
            pair = _two_up(spec)
            assert pair is not None
            assert qr_slot(pair.lower) == qr_slot(single)
            assert qr_caption(pair.lower) == qr_caption(single)
            checked += 1
        assert checked == 2

    def test_there_is_one_footer_depth_constant_and_one_group_placer(self) -> None:
        """Read off the source: nothing in the package states a second footer
        depth, and the only thing that puts a QR group anywhere is
        ``qr_slot``/``qr_caption`` — the inset parameter is what carries the
        second group, not a second placement rule."""
        package = Path(__file__).resolve().parent.parent / "src" / "nonogram"
        placers = []
        for module in sorted(package.rglob("*.py")):
            tree = ast.parse(module.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in (
                    "qr_slot",
                    "qr_caption",
                    "qr_group_insets",
                ):
                    placers.append((module.name, node.name))
        assert sorted(placers) == [
            ("layout.py", "qr_caption"),
            ("layout.py", "qr_group_insets"),
            ("layout.py", "qr_slot"),
        ], placers
        source = (package / "export" / "layout.py").read_text(encoding="utf-8")
        assert source.count("INTERIOR_FOOTER_MM = ") == 1

    def test_a_single_page_still_asks_for_one_group_and_gets_the_same_answer(
        self,
    ) -> None:
        """G-3's geometry half: the default ``inset_px`` leaves every single
        page's icon and lines exactly where CARD-223 put them, which is what
        makes the baseline comparison for those pages a real control."""
        for parity in (PageParity.ODD, PageParity.EVEN):
            for spec in (_spec(parity=parity), _unequal_spec(parity)):
                layout = compute_layout(*_clue_sets(20, 20, 1, 1), spec)
                assert qr_slot(layout) == qr_slot(layout, inset_px=0)
                assert qr_caption(layout) == qr_caption(layout, inset_px=0)
                insets = qr_group_insets(layout, _drawn_group_lines((1,)), 1)
                assert insets == (0,)
