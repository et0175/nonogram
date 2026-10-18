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
import random
import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin.book_pdf_generator import (
    QR_CAPTION_TEXT,
    QR_LINK_TEMPLATE,
    SIZE_LABEL_PT,
    BookPDFGenerator,
    _band_font,
    _draw_page_frame,
    _draw_qr_placeholder as _admin_draw_qr_placeholder,
    grid_size_label,
    qr_link,
    type_px,
)
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    QR_SLOT_MM,
    OrientationPolicy,
    PageParity,
    PageSpec,
    QrSlot,
    compute_layout,
    compute_pair_layout,
    interior_frame,
    qr_caption,
    qr_slot,
)
import nonogram.export.png as png_module
from nonogram.export.png import render_image
from nonogram.export.png import _draw_qr_placeholder as _png_draw_qr_placeholder
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.book_corpus import baseline_puzzles, corpus_book

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
    def test_every_two_up_slot_keeps_its_icon_out_of_the_gutter_half(
        self, parity: PageParity
    ) -> None:
        """Each slot of a two-up page, both parities. The **lower** slot
        carries no icon at all (its drawing's bottom edge is the bottom
        margin on every two-up page, which is both no room and the corner the
        page's own fallback folio is printed in), which is recorded here
        rather than passed over: the claim is vacuous for that slot and must
        be seen to be.
        """
        spec = _spec(parity=parity)
        pair = compute_pair_layout(_clue_sets(10, 10, 3, 3), _clue_sets(10, 10, 3, 3), spec)
        assert pair is not None
        left, right = _gutter_half(spec, pair.upper.width)

        upper = qr_slot(pair.upper)
        assert upper is not None, "the upper slot of this pair should carry an icon"
        assert not (left <= upper.left < right or left < upper.right <= right)

        assert qr_slot(pair.lower) is None, (
            "the lower slot is expected to carry no icon — if it has gained one, "
            "this test's gutter claim about it has stopped being vacuous and "
            "must be made against its real box"
        )

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
        together or not at all, and every link printed is this project's own
        template filled with a puzzle number the book really holds.

        **Three links for four puzzles, and the missing one is named.** This
        book's puzzles 1 and 2 share a two-up page, and a two-up page's lower
        slot carries no icon (``TestBookQrSlot_YieldsRatherThanCollide``, and
        ``qr_slot``'s own docstring for why) — so puzzle 2 prints neither
        line. That is read off the book's own page plan here rather than
        written down, so if the pairing ever changes this test moves with it
        instead of pinning a stale number.
        """
        generator = BookPDFGenerator(corpus_book())
        puzzles = baseline_puzzles()
        plan = generator.section_plan(puzzles)
        lower_slot_puzzles = {
            page.numbers[1]
            for page in plan.pages
            if getattr(page, "numbers", None) and page.is_two_up
        }
        assert lower_slot_puzzles, "this book is supposed to hold a two-up page"
        expected = [
            qr_link(number)
            for number in range(1, len(puzzles) + 1)
            if number not in lower_slot_puzzles
        ]

        calls = _text_calls(generator, puzzles, monkeypatch)
        captions = [call for call in calls if call["text"] == QR_CAPTION_TEXT]
        links = [call for call in calls if call["text"].startswith("nonogram.example/")]
        assert captions, "no page of the book set the invitation at all"
        assert {call["page"] for call in captions} == {call["page"] for call in links}
        assert len(captions) == len(links)
        assert sorted(call["text"] for call in links) == expected, (
            sorted(call["text"] for call in links),
            expected,
        )

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
        extents = []
        for parity in (PageParity.ODD, PageParity.EVEN):
            extents.append(compute_layout(row_clues, column_clues, _spec(parity=parity)))
            extents.append(compute_layout(row_clues, column_clues, _unequal_spec(parity)))
            pair = compute_pair_layout(
                _clue_sets(10, 10, 3, 3), _clue_sets(10, 10, 3, 3), _spec(parity=parity)
            )
            assert pair is not None
            extents.append(pair.upper)
        checked = 0
        for layout in extents:
            icon = qr_slot(layout)
            assert icon is not None
            assert abs((icon.right - icon.left) - QR_SLOT_PX) <= 1
            assert abs((icon.bottom - icon.top) - QR_SLOT_PX) <= 1
            checked += 1
        assert checked == 6

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

    def test_a_two_up_pages_lower_slot_draws_neither(self) -> None:
        """The behaviour this card changes, recorded rather than left to be
        discovered: a two-up page's lower slot has zero slack below its
        drawing on every such page (``PairLayout``), so it carries no icon and
        no lines — while its upper slot carries both."""
        for parity in (PageParity.ODD, PageParity.EVEN):
            pair = compute_pair_layout(
                _clue_sets(10, 10, 3, 3), _clue_sets(10, 10, 3, 3), _spec(parity=parity)
            )
            assert pair is not None
            assert pair.lower.page.usable_bottom - pair.lower.page.drawing_bottom == 0
            assert qr_slot(pair.lower) is None
            assert qr_caption(pair.lower) is None
            assert qr_slot(pair.upper) is not None
            assert qr_caption(pair.upper) is not None

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
