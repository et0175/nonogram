"""The Play online page as PDF operators (CARD-390, ADR-0041/R8, ADR-0042/R1).

One right-hand page after the last puzzle and before the solutions: a heading,
one line of what to do, the book's QR code and, under the code, the address a
reader can type instead. The code opens the book's landing page
(``<player domain>/b/<slug>``, :func:`nonogram.admin.player_bundle.landing_address`),
which lists the puzzles in book order. The page carries a URL and words only: no
grid, no solution and no puzzle title (ADR-0037/R1, ADR-0041/R2).

**Where this module sits.** Downstream of
:mod:`nonogram.admin.book_pdf_generator`, as :mod:`nonogram.admin.book_toc_vector`
is: it takes that module's type sizes and its page-parity rule, and the
generator reaches it through :class:`~nonogram.admin.book_pdf_generator.InteriorPageWriters`
and the one assembly point (:mod:`nonogram.admin.book_interior_vector`). The page
is vector with no raster declaration, so there is no bitmap twin to keep equal.

**Every position arrives.** Where the heading, the instruction, the code and the
address go is :func:`~nonogram.export.layout.play_page_layout`'s (ADR-0036/R2);
the furniture is :func:`~nonogram.admin.book_sheet_vector.draw_sheet_furniture`'s.
This module measures how wide a string *sets* (a type fact) and where a line
breaks, and decides no position. The code is :func:`~nonogram.admin.book_vector_draw.draw_qr`'s,
which refuses a module under its printable floor rather than shrink the code.

**The address is one line where it fits.** It is tried at 12, 11 and 10 pt
(CON-020's floor) and, if even 10 pt overruns the measure, broken once before
``/b/`` so the host and the path each sit whole on a line of their own. A host
too long for a line at the floor is refused (:class:`PlayPageError`), not set
smaller than the floor.
"""

from __future__ import annotations

from typing import List, Sequence

from nonogram.admin.book_guide_vector import wrap
from nonogram.admin.book_pdf_generator import (
    FOLIO_PT,
    GUIDE_BODY_PT,
    GUIDE_LEADING_PT,
    page_frame,
    page_is_right_hand,
    type_px,
)
from nonogram.admin.book_qr import encode_text
from nonogram.admin.book_sheet_vector import SheetFurniture, draw_sheet_furniture
from nonogram.admin.book_vector import ContentStream, FontMetrics, interior_face_metrics
from nonogram.admin.book_vector_draw import (
    INK_GREY,
    QrBox,
    advance_px,
    draw_qr,
    line_height_px,
    qr_min_side_px,
    set_from_top,
)
from nonogram.export.layout import PageSpec, play_page_layout

__all__ = [
    "PLAY_ADDRESS_SIZES_PT",
    "PLAY_HEADING",
    "PLAY_HEADING_PT",
    "PLAY_INSTRUCTION",
    "PlayPageError",
    "address_lines",
    "play_page",
]

#: The page's heading, which is the owner's wording (version B of the One-QR
#: Book Layout, 2026-11-07).
PLAY_HEADING = "Play online"

#: The one line of instruction under it. Drafted from the owner's table ("Turn
#: to page N, scan, then tap the puzzle's number"); the page the reader is on
#: is page N, so it says "scan" and not "turn to".
PLAY_INSTRUCTION = (
    "Scan the code with your phone to play any puzzle in this book, "
    "then tap the puzzle's number."
)

#: The heading's type, in points: large enough to be the page, as the guide's
#: 22 pt title is for its page.
PLAY_HEADING_PT = 28.0

#: The sizes the typed address is tried at, largest first, in points. The last
#: is CON-020's 10 pt floor (``FOLIO_PT``), which nothing here sets below.
PLAY_ADDRESS_SIZES_PT = (12.0, 11.0, FOLIO_PT)

#: Where the address is broken when it does not fit one line.
_PATH_MARK = "/b/"


class PlayPageError(ValueError):
    """The page cannot be drawn without setting type below the floor."""


def address_lines(
    short: str, sizes_px: Sequence[float], measure: float, metrics: FontMetrics
) -> tuple[List[str], float]:
    """``short`` as the lines it is set in, and the size they are set at.

    The largest of ``sizes_px`` at which it sits on one line; failing that, the
    smallest size with the address broken before ``/b/``.

    Raises:
        PlayPageError: a line is still wider than ``measure`` at the smallest
            size.
    """
    for size in sizes_px:
        if advance_px(short, size, metrics) <= measure:
            return [short], size
    size = sizes_px[-1]
    host, mark, path = short.partition(_PATH_MARK)
    lines = [host, mark + path] if mark else [short]
    if any(advance_px(line, size, metrics) > measure for line in lines):
        raise PlayPageError(
            f"the address {short!r} does not fit a {measure:g} px line at the "
            "type floor, even broken before its path"
        )
    return lines, size


def play_page(
    spec: PageSpec,
    dpi: int,
    page_number: int,
    *,
    url: str,
    short: str,
    puzzle_count: int = 0,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> ContentStream:
    """The Play online page for the book whose landing page is ``url``.

    ``url`` is what the code carries and ``short`` what is printed under it;
    :func:`~nonogram.admin.player_bundle.landing_address` makes both from one
    slug, so they cannot name different pages. ``spec`` is this page's own sheet
    (a right-hand page: the caller is the plan, which puts it there).

    Raises:
        QrCapacityError: ``url`` cannot be carried by a printable code.
        QrModuleTooSmall: the code would print under the module floor on this
            sheet.
        PlayPageError: the address cannot be set at the type floor.
        ValueError: the sheet has no room for the page at all.
    """
    face = interior_face_metrics() if metrics is None else metrics
    designed = _mockup_play_page(
        spec, dpi, page_number, url=url, short=short, puzzle_count=puzzle_count, metrics=face
    )
    if designed is not None:
        return designed
    frame = page_frame(spec)
    measure = frame.right - frame.left
    heading_px = type_px(PLAY_HEADING_PT, dpi)
    body_px = type_px(GUIDE_BODY_PT, dpi)
    leading_px = type_px(GUIDE_LEADING_PT, dpi)
    instruction = wrap(PLAY_INSTRUCTION, body_px, measure, face)
    address, address_px = address_lines(
        short, [type_px(pt, dpi) for pt in PLAY_ADDRESS_SIZES_PT], measure, face
    )
    address_leading = line_height_px(address_px, face)
    modules = encode_text(url)
    # The code and its address are the page; the words are what a sheet too
    # short for them gives up, instruction first, then the heading.
    for heading_height, instruction_height in (
        (round(line_height_px(heading_px, face)), len(instruction) * leading_px),
        (round(line_height_px(heading_px, face)), 0),
        (0, 0),
    ):
        try:
            layout = play_page_layout(
                spec,
                heading_height=heading_height,
                instruction_height=instruction_height,
                address_height=round(len(address) * address_leading),
                qr_min_side=qr_min_side_px(len(modules), dpi),
            )
            break
        except ValueError:
            if not heading_height:
                raise

    stream = ContentStream(width_px=frame.width, height_px=frame.height, dpi=dpi)
    draw_sheet_furniture(
        stream,
        SheetFurniture(
            frame=layout.frame,
            folio=str(page_number),
            folio_size_px=type_px(FOLIO_PT, dpi),
            right_hand=page_is_right_hand(page_number),
        ),
        face,
        grey=grey,
    )
    if heading_height:
        set_from_top(
            stream,
            PLAY_HEADING,
            layout.centre_x - advance_px(PLAY_HEADING, heading_px, face) / 2,
            layout.heading_top,
            heading_px,
            face,
            grey=grey,
        )
    for index, line in enumerate(instruction if instruction_height else ()):
        set_from_top(
            stream,
            line,
            layout.centre_x - advance_px(line, body_px, face) / 2,
            layout.instruction_top + index * leading_px,
            body_px,
            face,
            grey=grey,
        )
    draw_qr(
        stream,
        modules,
        QrBox(layout.qr_left, layout.qr_top, layout.qr_side),
    )
    for index, line in enumerate(address):
        set_from_top(
            stream,
            line,
            layout.centre_x - advance_px(line, address_px, face) / 2,
            layout.address_top + index * address_leading,
            address_px,
            face,
            grey=grey,
        )
    return stream


# --------------------------------------------------------------------------
# The approved version B mockup (owner, 2026-11-07)
# --------------------------------------------------------------------------

#: The mockup's words, as requirements/one-qr-book-delta-2026-11-07.md states them.
PLAY_EYEBROW = "BONUS"
PLAY_TITLE = "Play every puzzle online"
PLAY_INTRO = (
    "Scan the code to open this book's puzzle list. Tap a puzzle's number and "
    "solve it in your browser, on a phone, a tablet or a computer. Nothing to install."
)
PLAY_CARD_TITLE = "This book's puzzles"
PLAY_ADDRESS_LEAD = "Or type the address:"
PLAY_STEPS = (
    ("Scan", "Point your phone's camera at the code."),
    ("Pick", "Tap the number of the puzzle you're on."),
    ("Play", "Fill squares with a tap. Undo, zoom and finished-clue marks help along the way."),
)
PLAY_CALLOUT_TITLE = "Stuck? Try it online before you turn the page."
PLAY_CALLOUT_BODY = (
    "The solutions start overleaf. Online, the game tells you when the picture is complete."
)

#: The code's printed side in the mockup, and the least it may shrink to.
_PLAY_QR_MM = 50.0
_PLAY_QR_MIN_MM = 40.0


def play_card_count_line(puzzle_count: int) -> str:
    """The card's second line: "All 158, in the same order and with the same numbers as the book." """
    if puzzle_count <= 0:
        return "In the same order and with the same numbers as the book."
    return f"All {puzzle_count}, in the same order and with the same numbers as the book."


def _mockup_play_page(
    spec: PageSpec,
    dpi: int,
    page_number: int,
    *,
    url: str,
    short: str,
    puzzle_count: int,
    metrics: FontMetrics,
) -> ContentStream | None:
    """The Play online page as the approved mockup sets it, or ``None`` when the
    sheet is too small for it (the plain centred page is drawn instead).

    Top to bottom: a short rule and the "BONUS" eyebrow; the heading; one grey
    paragraph; a shaded card holding the code (50 mm, never under 40 mm) with
    the book's puzzle count and the typed address beside it; three numbered
    steps; and a callout at the foot saying the solutions start overleaf.
    """
    from nonogram.admin.book_guide_spread import _BOLD_RATIO, _GREY, _SHADE, _Pen, _badge
    from nonogram.export.layout import interior_frame

    frame = interior_frame(spec)
    left, right = frame.header_rule.left, frame.header_rule.right
    pt = dpi / 72.0
    width = right - left
    if width < 360 * pt:
        return None
    trim = page_frame(spec)
    stream = ContentStream(width_px=trim.width, height_px=trim.height, dpi=dpi)
    pen = _Pen(stream, metrics, pt, dpi, left, right)
    modules = encode_text(url)
    mm = dpi / 25.4

    y = frame.header_rule.y + pen.px(40)
    stream.fill_grey(0.0)
    stream.rectangle(left, y, left + pen.px(60), y + pen.px(2.4), paint="fill")
    y += pen.px(18)
    pen.put(PLAY_EYEBROW, left, y, FOLIO_PT, grey=_GREY, bold=True)
    y += pen.px(38)
    title_pt = 30.0
    title_lines = wrap(PLAY_TITLE, pen.type_px(title_pt), width * 0.62, metrics)
    for line in title_lines:
        pen.put(line, left, y, title_pt, bold=True)
        y += pen.px(title_pt * 1.15)
    y += pen.px(4)
    y = pen.para(PLAY_INTRO, left, y, width * 0.9, 12.0, grey=_GREY)

    # The card: code on the left, words beside it.
    qr_side = _PLAY_QR_MM * mm
    floor = max(_PLAY_QR_MIN_MM * mm, qr_min_side_px(len(modules), dpi))
    card_top = y + pen.px(8)
    pad = pen.px(22)
    text_left = left + pad + qr_side + pen.px(26)
    text_width = right - pad - text_left
    if text_width < pen.px(150) or qr_side < floor:
        return None
    card_bottom = card_top + qr_side + 2 * pad
    pen.box(left, card_top, right, card_bottom, _SHADE)
    draw_qr(stream, modules, QrBox(left + pad, card_top + pad, qr_side))
    ty = card_top + pad + pen.px(22)
    pen.put(PLAY_CARD_TITLE, text_left, ty, 15.0, bold=True)
    ty = pen.para(play_card_count_line(puzzle_count), text_left, ty + pen.px(20), text_width, 11.0, grey=_GREY)
    ty += pen.px(12)
    pen.put(PLAY_ADDRESS_LEAD, text_left, ty, FOLIO_PT, grey=_GREY)
    address, address_px = address_lines(
        short, [type_px(size, dpi) for size in PLAY_ADDRESS_SIZES_PT], text_width, metrics
    )
    ty += pen.px(17)
    for line in address:
        pen.put(line, text_left, ty, address_px / pt, bold=True)
        ty += line_height_px(address_px, metrics)
    if ty > card_bottom:
        return None

    # The three steps, side by side.
    y = card_bottom + pen.px(42)
    column = width / len(PLAY_STEPS)
    steps_bottom = y
    for index, (head, body) in enumerate(PLAY_STEPS):
        x = left + index * column
        _badge(pen, x + pen.px(9), y, str(index + 1))
        pen.put(head, x + pen.px(26), y, 13.0, bold=True)
        steps_bottom = max(steps_bottom, pen.para(body, x, y + pen.px(22), column - pen.px(20), FOLIO_PT, grey=_GREY))

    # The callout, at the foot of the area.
    callout_h = pen.px(40)
    callout_top = frame.footer_rule.y - pen.px(16) - callout_h
    if callout_top < steps_bottom + pen.px(10):
        return None
    stream.fill_grey(0.0)
    stream.rectangle(left, callout_top, left + pen.px(3), callout_top + callout_h, paint="fill")
    pen.put(PLAY_CALLOUT_TITLE, left + pen.px(14), callout_top + pen.px(15), 11.5, bold=True)
    pen.para(PLAY_CALLOUT_BODY, left + pen.px(14), callout_top + pen.px(32), width - pen.px(14), FOLIO_PT, grey=_GREY)

    draw_sheet_furniture(
        stream,
        SheetFurniture(
            frame=frame,
            folio=str(page_number),
            folio_size_px=type_px(FOLIO_PT, dpi),
            right_hand=page_is_right_hand(page_number),
        ),
        metrics,
    )
    return stream
