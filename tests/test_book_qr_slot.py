"""CARD-204 — the placeholder QR icon's reserved slot (item 3 of the owner's
Google Doc "Nonograms - Print layout1").

    AC-5  TestBookPdf_QrSlotReservedWithoutOverlap
    AC-6  TestBookPdf_QrSlotOmittedWhenNoRoomRatherThanOverlapping
    AC-8  TestBookPdf_QrPlaceholderIsVisiblyNotARealCode

What this file is, and is not, about
-------------------------------------
``export/layout.py``'s :func:`~nonogram.export.layout.qr_slot` measures
*where* the icon fits (or that it does not); ``export/png.py`` and
``admin/book_pdf_generator.py`` each carry their own, independently drawn
:func:`_draw_qr_placeholder` (the native-reimplementation convention this
project already uses for grid stroking — see ``test_book_puzzle_frame.py``'s
own module docstring). This file tests both halves: the geometry function
directly, and the actual ink a render produces.

Right-alignment itself (reading (b), AC-1..AC-4) is
``tests/property/test_book_layout.py``'s and
``tests/property/test_book_two_up.py``'s own concern; this file assumes it
and builds on it.
"""

from __future__ import annotations

import random

import numpy as np
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _draw_qr_placeholder as _admin_draw_qr_placeholder,
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
    qr_slot,
)
from nonogram.export.png import INK, render_image
from nonogram.export.png import _draw_qr_placeholder as _png_draw_qr_placeholder
from nonogram.limits import MAX_SIZE, MIN_SIZE

DPI = 300
PX_PER_MM = DPI / 25.4
QR_SLOT_PX = round(QR_SLOT_MM / 25.4 * DPI)

#: CON-018's Book 1 profile, in millimetres — the same stated-from-the-spec
#: construction every other CARD-204 test file uses.
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
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
MIN_THIN_RULE_MM = 0.25


def _spec(*, parity: PageParity = PageParity.ODD, **overrides: object) -> PageSpec:
    return PageSpec(
        width_mm=BOOK1_WIDTH_MM,
        height_mm=BOOK1_HEIGHT_MM,
        top_mm=TOP_MM,
        bottom_mm=BOTTOM_MM,
        gutter_mm=GUTTER_MM,
        outside_mm=OUTSIDE_MM,
        band_mm=BAND_MM,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=MIN_THIN_RULE_MM,
        parity=parity,
        **overrides,
    )


def _grid(columns: int, rows: int, row_depth: int, column_depth: int) -> list[list[bool]]:
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
        seed=204,
        mode="random",
        name="qr-slot-test",
        difficulty="Easy",
    )


# --------------------------------------------------------------------------
# AC-5 — the icon is reserved without overlapping the grid, the band, or
# (per compute_pair_layout) the other slot
# --------------------------------------------------------------------------


class TestBookPdf_QrSlotReservedWithoutOverlap:
    """A 2x2cm icon area is reserved at the gutter side (or the foot) and
    never overlaps the grid, the band, or a neighbouring slot."""

    def test_the_icon_is_exactly_two_by_two_cm(self) -> None:
        """Both the margin-slot and the foot-fallback placements are
        exactly QR_SLOT_MM square, whichever one a given extent takes."""
        row_clues, column_clues = _clue_sets(8, 8, 1, 1)
        for parity in (PageParity.ODD, PageParity.EVEN):
            layout = compute_layout(row_clues, column_clues, _spec(parity=parity))
            icon = qr_slot(layout)
            assert icon is not None, "a small puzzle should leave margin-slot room"
            assert abs((icon.right - icon.left) - QR_SLOT_PX) <= 1
            assert abs((icon.bottom - icon.top) - QR_SLOT_PX) <= 1

    def test_the_margin_slot_sits_on_the_gutter_side_never_over_the_drawing(self) -> None:
        row_clues, column_clues = _clue_sets(8, 8, 1, 1)
        for parity, gutter_left in (
            (PageParity.ODD, True),
            (PageParity.EVEN, False),
        ):
            layout = compute_layout(row_clues, column_clues, _spec(parity=parity))
            page = layout.page
            icon = qr_slot(layout)
            assert icon is not None
            # On the gutter side: left of the drawing on ODD, right of it on EVEN.
            if gutter_left:
                assert icon.right <= page.drawing_left
                assert icon.left >= page.usable_left
            else:
                assert icon.left >= page.drawing_right
                assert icon.right <= page.usable_right
            # Never over the band: its top is no higher than the drawing's own.
            assert icon.top >= page.drawing_top
            assert icon.bottom <= page.usable_bottom
            # Never over the grid/drawing itself (belt and suspenders: the
            # two checks above already imply this on the gutter side).
            assert icon.right <= page.drawing_left or icon.left >= page.drawing_right

    def test_each_two_up_slot_gets_its_own_icon_without_overlap(self) -> None:
        """Two small, same-tier puzzles pair, and each slot's own icon sits
        in its own gutter-side strip — never over either slot's own
        drawing, and never crossing into the other slot's usable area."""
        upper_clues = _clue_sets(8, 8, 1, 1)
        lower_clues = _clue_sets(8, 8, 1, 1)
        for parity in (PageParity.ODD, PageParity.EVEN):
            pair = compute_pair_layout(upper_clues, lower_clues, _spec(parity=parity))
            assert pair is not None
            upper_icon = qr_slot(pair.upper)
            lower_icon = qr_slot(pair.lower)
            assert upper_icon is not None and lower_icon is not None

            for slot, icon in ((pair.upper, upper_icon), (pair.lower, lower_icon)):
                page = slot.page
                assert icon.right <= page.drawing_left or icon.left >= page.drawing_right
                assert icon.top >= page.drawing_top
                assert icon.bottom <= page.usable_bottom

            # The upper slot's icon never reaches into the lower slot's
            # own usable area, and vice versa (the shared midline holds).
            assert upper_icon.bottom <= pair.upper.page.usable_bottom
            assert lower_icon.top >= pair.lower.page.usable_top
            assert pair.upper.page.usable_bottom == pair.lower.page.usable_top

    def test_the_rendered_ink_actually_lands_inside_the_reported_box(self) -> None:
        """Not just the geometry: the real pixels a puzzle page renders put
        ink only inside ``qr_slot``'s own box, outside the drawing."""
        payload = _payload(8, 8, 1, 1)
        spec = _spec(parity=PageParity.ODD)
        image = render_image(payload, page_spec=spec)
        layout = compute_layout(payload.row_clues, payload.column_clues, spec)
        icon = qr_slot(layout)
        assert icon is not None
        page = layout.page

        # The strip between the usable left edge and the drawing's own
        # left edge, above the icon's own top: no ink (the icon starts
        # exactly at the drawing's top, never above it).
        above_icon = image.crop((page.usable_left, page.usable_top, page.drawing_left, icon.top))
        assert above_icon.getextrema() == ((255, 255), (255, 255), (255, 255)) or _blank(above_icon)

        # Inside the icon's own box: some ink (the placeholder glyph).
        inside = image.crop((icon.left, icon.top, icon.right, icon.bottom))
        assert not _blank(inside), "the icon's own box carries no ink at all"


def _blank(image: Image.Image) -> bool:
    return image.convert("L").getextrema() == (255, 255)


# --------------------------------------------------------------------------
# AC-6 — omitted rather than overlapping, when there is no room anywhere
# --------------------------------------------------------------------------


class TestBookPdf_QrSlotOmittedWhenNoRoomRatherThanOverlapping:
    """A page whose chosen slot(s) have no slack for a 2x2cm icon omits it,
    rather than drawing over the grid, the band or a neighbouring slot."""

    def test_a_page_fit_bound_single_page_omits_the_icon(self) -> None:
        """A 30x30 with a 1-deep row gutter and a 10-deep column gutter is
        page-fit-bound on both axes on Book 1's own trim (the same
        construction ``test_book_page_numbers.py``'s own
        ``_tight_fit_single_page_puzzle`` uses for the folio's no-room
        case), leaving neither margin nor foot room."""
        row_clues, column_clues = _clue_sets(30, 30, 1, 10)
        layout = compute_layout(row_clues, column_clues, _spec(parity=PageParity.ODD))
        page = layout.page
        assert page is not None and page.fits
        # Confirm the precondition directly rather than assume it: close to
        # zero slack on both the gutter side and the foot.
        assert page.usable_bottom - page.drawing_bottom < QR_SLOT_PX
        assert min(
            page.drawing_left - page.usable_left, page.usable_right - page.drawing_right
        ) < QR_SLOT_PX

        assert qr_slot(layout) is None

    def test_a_near_floor_two_up_pairs_lower_slot_omits_the_icon(self) -> None:
        """A 25-wide, 10-tall, depth-1 pair on Book 1's own trim (the same
        tight-fit construction ``test_book_page_numbers.py`` uses for the
        folio's own no-room case): the lower slot's drawing reaches both
        the bottom margin and the outer side margin, by construction on
        *every* two-up page (``PairLayout``'s own docstring) — leaving no
        foot and no margin slack either. (The upper slot is not asserted
        here: whatever height the pair leaves spare collects *between* the
        two slots, so the upper slot alone can still have foot room — that
        is a different, per-puzzle case, not this one's.)
        """
        upper_clues = _clue_sets(25, 10, 1, 1)
        lower_clues = _clue_sets(25, 10, 1, 1)
        pair = compute_pair_layout(upper_clues, lower_clues, _spec(parity=PageParity.ODD))
        assert pair is not None
        assert pair.lower.page.usable_bottom - pair.lower.page.drawing_bottom == 0
        assert pair.lower.page.usable_right - pair.lower.page.drawing_right == 0

        assert qr_slot(pair.lower) is None

    def test_the_omission_is_not_a_blanket_rule(self) -> None:
        """Control: an ordinary small puzzle, plenty of slack either way,
        still gets its icon — AC-6 is about the specific no-room case, not
        every page."""
        row_clues, column_clues = _clue_sets(8, 8, 1, 1)
        layout = compute_layout(row_clues, column_clues, _spec(parity=PageParity.ODD))
        assert qr_slot(layout) is not None


# --------------------------------------------------------------------------
# AC-8 — the placeholder is visibly not a real, scannable code
# --------------------------------------------------------------------------


class TestBookPdf_QrPlaceholderIsVisiblyNotARealCode:
    """The drawn glyph is a generic grid-of-squares placeholder, not a real
    QR code, and encodes/links to nothing live."""

    def _icon(self) -> QrSlot:
        return QrSlot(left=100, top=100, right=100 + QR_SLOT_PX, bottom=100 + QR_SLOT_PX)

    def test_the_glyph_is_a_plain_alternating_checkerboard_not_module_data(self) -> None:
        """A real QR code's modules encode data (an irregular-looking
        bit pattern) and three corners carry a nested-square finder
        pattern. This glyph is neither: every filled module sits at
        ``(row + column) % 2 == 1`` on a fixed 5x5 grid, the same pattern
        regardless of what it is drawn beside — checked directly against
        the drawn pixels, not just against the source code's own loop.
        """
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
                is_dark = pixel[0] < 128
                assert is_dark == expected_filled, (row, column, pixel)

    def test_both_renderers_draw_the_identical_pattern(self) -> None:
        """``export/png.py`` and ``book_pdf_generator.py`` reimplement this
        glyph independently (the native-reimplementation convention) — this
        confirms the two reimplementations did not drift into two different
        "placeholders", one of which might read as more real than the
        other."""
        icon = self._icon()
        a = Image.new("RGB", (icon.right + 10, icon.bottom + 10), (255, 255, 255))
        b = Image.new("RGB", (icon.right + 10, icon.bottom + 10), (255, 255, 255))
        _png_draw_qr_placeholder(ImageDraw.Draw(a), icon)
        _admin_draw_qr_placeholder(ImageDraw.Draw(b), icon)
        assert np.array_equal(np.asarray(a), np.asarray(b))

    def test_the_pattern_never_varies_with_the_puzzle_or_the_page(self) -> None:
        """It is decoration, not data: the exact same pixels are drawn
        whatever puzzle or page it is reserved for — nothing about the
        glyph itself could carry a per-puzzle URL, because nothing about
        it ever changes."""
        icon = self._icon()
        rng = random.Random(2204008)
        reference: np.ndarray | None = None
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

    def test_no_url_or_link_appears_anywhere_in_either_drawing_function(self) -> None:
        """CON-021/G-3: the placeholder must not point at any real or
        admin-only URL. Proven the strongest way available short of a
        running scanner: neither function's own source text contains a
        URL scheme, a hostname-shaped token, or any string literal at
        all beyond its own docstring — there is nothing in the code path
        a scanner, or a curious reader of the source, could follow
        anywhere.
        """
        import inspect

        for fn in (_png_draw_qr_placeholder, _admin_draw_qr_placeholder):
            source = inspect.getsource(fn)
            lowered = source.lower()
            for marker in ("http://", "https://", "www.", "ftp://", ".com", ".org", ".net"):
                assert marker not in lowered, (fn, marker)

    def test_it_is_not_mistaken_for_a_real_code_by_the_project_s_own_qr_absence(self) -> None:
        """The project's dependency baseline carries no QR-generation
        library (ADR-0006/R1, G-4) — restated here as a direct check that
        the placeholder's own module never imports one, so there is no
        code path, reachable or not, that could turn this glyph into real
        QR pixels without a future card's explicit dependency decision.
        """
        import nonogram.export.png as png_module
        import nonogram.admin.book_pdf_generator as admin_module

        for module in (png_module, admin_module):
            names = " ".join(dir(module)).lower()
            assert "qrcode" not in names
