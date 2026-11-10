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
# Anna's design (owner, 2026-11-10), replacing version B of 2026-11-07
# --------------------------------------------------------------------------

#: The page's words. Every number on it (puzzle count, the solutions' page)
#: is passed in from the plan, never written here.
PLAY_EYEBROW = "BONUS"
PLAY_BADGE = "FREE ONLINE ACCESS INCLUDED"
PLAY_TITLE = "Play Every Puzzle Online"
PLAY_INTRO = (
    "Prefer solving on a screen, on the go, or without an eraser? Scan the QR "
    "code below to open every puzzle on your phone, tablet or computer. "
    "No app to install."
)
PLAY_ADDRESS_LEAD = "OR TYPE THE ADDRESS:"
PLAY_STEP_HEADS = ("Scan", "Select", "Solve")
PLAY_CALLOUT_LEAD = "Stuck on a tricky deduction?"

#: The code's printed side, and the least it may shrink to.
_PLAY_QR_MM = 32.0
_PLAY_QR_MIN_MM = 25.0
#: The card's and the code box's border, in points, and its grey.
_RULE_PT = 0.8
_RULE_GREY = 0.55
_PANEL = 0.97
#: The card's own shade, the guide's panel grey.
_CARD = 0.945


def play_card_title(puzzle_count: int) -> str:
    """The card's heading: "Online Access to All 160 Puzzles"."""
    if puzzle_count <= 0:
        return "Online Access to Every Puzzle"
    return f"Online Access to All {puzzle_count} Puzzles"


def play_card_count_line(puzzle_count: int) -> str:
    """The line under the card's heading."""
    return "Every puzzle from the book, in the same order and with the same numbers."


def play_steps(puzzle_count: int) -> tuple[tuple[str, str], ...]:
    """The three numbered steps; the second names the book's own puzzle range."""
    numbers = f" (1–{puzzle_count})" if puzzle_count > 0 else ""
    return (
        ("Scan", "Open your phone's camera and point it at the code."),
        ("Select", f"Tap the number{numbers} of the puzzle you are solving."),
        ("Solve", "Tap to fill, check your marks, zoom and undo as you go."),
    )


def play_callout_body(solutions_page: int) -> str:
    """The callout's text after its bold lead, naming the solutions' real page.

    Owner, 2026-11-10: it points a stuck reader at the online Hint, which
    shows the line to work on and why, before the solutions.
    """
    return (
        "Press Hint in the online game: it points to a line you can work on "
        f"and explains why. The solutions are on page {solutions_page}."
    )


def _tracked(pen, text: str, x: float, baseline: float, size_pt: float, tracking_pt: float,
             *, grey: float, bold: bool = True) -> float:
    """Set ``text`` letter-spaced by ``tracking_pt``; returns its right edge."""
    for char in text:
        x = pen.put(char, x, baseline, size_pt, grey=grey, bold=bold) + pen.px(tracking_pt)
    return x - pen.px(tracking_pt)


def _tracked_width(pen, text: str, size_pt: float, tracking_pt: float) -> float:
    return sum(pen.width(char, size_pt) for char in text) + pen.px(tracking_pt) * (len(text) - 1)


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
    """The Play online page as Anna designed it, or ``None`` when the sheet is
    too small for it (the plain centred page is drawn instead).

    Top to bottom: the "BONUS" eyebrow and a bordered badge; the heading; a
    grey paragraph; a bordered card holding the code in its own white box,
    with the puzzle count and the typed address beside it; three numbered
    steps under hairlines; and a shaded callout naming the page the solutions
    start on, which is the page after this one (the plan puts the solutions
    straight after the Play page).
    """
    from nonogram.admin.book_guide_spread import _GREY, _Pen, _badge
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

    # Eyebrow, underlined, and the bordered badge beside it.
    y = frame.header_rule.y + pen.px(34)
    eyebrow_pt, badge_pt = FOLIO_PT, FOLIO_PT
    eyebrow_right = _tracked(pen, PLAY_EYEBROW, left, y, eyebrow_pt, 2.2, grey=_INK_TEXT)
    stream.fill_grey(0.0)
    stream.rectangle(left, y + pen.px(5), eyebrow_right, y + pen.px(6.6), paint="fill")
    badge_left = eyebrow_right + pen.px(14)
    badge_w = _tracked_width(pen, PLAY_BADGE, badge_pt, 1.0) + pen.px(16)
    if badge_left + badge_w <= right:
        stream.fill_grey(_PANEL)
        stream.stroke_grey(0.0)
        stream.stroke_width(_RULE_PT)
        stream.rectangle(badge_left, y - pen.px(12), badge_left + badge_w, y + pen.px(6), paint="both")
        _tracked(pen, PLAY_BADGE, badge_left + pen.px(8), y + pen.px(1), badge_pt, 1.0, grey=_INK_TEXT)

    # Heading and intro.
    y += pen.px(48)
    title_pt = 30.0
    for line in wrap(PLAY_TITLE, pen.type_px(title_pt), width, metrics):
        pen.put(line, left, y, title_pt, bold=True)
        y += pen.px(title_pt * 1.15)
    y = pen.para(PLAY_INTRO, left, y + pen.px(2), width * 0.92, 11.0, grey=_GREY)

    # The card: the code in a white box on the left, words beside it.
    qr_side = _PLAY_QR_MM * mm
    floor = max(_PLAY_QR_MIN_MM * mm, qr_min_side_px(len(modules), dpi))
    if qr_side < floor:
        qr_side = floor
    pad = pen.px(16)
    quiet = pen.px(8)
    card_top = y + pen.px(18)
    box = qr_side + 2 * quiet
    text_left = left + pad + box + pen.px(22)
    text_width = right - pad - text_left
    if text_width < pen.px(150):
        return None
    card_bottom = card_top + box + 2 * pad
    stream.fill_grey(_CARD)
    stream.stroke_grey(0.0)
    stream.stroke_width(_RULE_PT)
    edge = pen.px(_RULE_PT)  # the stroke is centred: keep its outer half inside the margin
    stream.rectangle(left + edge, card_top, right - edge, card_bottom, paint="both")
    stream.fill_grey(1.0)
    stream.stroke_grey(_RULE_GREY)
    stream.stroke_width(_RULE_PT)
    stream.rectangle(left + pad, card_top + pad, left + pad + box, card_top + pad + box, paint="both")
    draw_qr(stream, modules, QrBox(left + pad + quiet, card_top + pad + quiet, qr_side))
    ty = card_top + pad + pen.px(26)
    ty = pen.para(play_card_title(puzzle_count), text_left, ty, text_width, 14.0, bold=True)
    ty = pen.para(play_card_count_line(puzzle_count), text_left, ty - pen.px(4), text_width, FOLIO_PT, grey=_GREY)
    ty += pen.px(8)
    _tracked(pen, PLAY_ADDRESS_LEAD, text_left, ty, FOLIO_PT, 0.6, grey=_GREY, bold=False)
    address, address_px = address_lines(
        short, [type_px(size, dpi) for size in PLAY_ADDRESS_SIZES_PT], text_width, metrics
    )
    ty += pen.px(16)
    for line in address:
        pen.put(line, text_left, ty, address_px / pt, bold=True)
        ty += line_height_px(address_px, metrics)
    if ty > card_bottom:
        return None

    # The three steps, side by side, each under a hairline.
    steps = play_steps(puzzle_count)
    y = card_bottom + pen.px(34)
    gap = pen.px(18)
    column = (width - gap * (len(steps) - 1)) / len(steps)
    steps_bottom = y
    for index, (head, body) in enumerate(steps):
        x = left + index * (column + gap)
        stream.stroke_grey(0.82)
        stream.stroke_width(1.2)
        stream.line(x, y, x + column, y)
        by = y + pen.px(22)
        _badge(pen, x + pen.px(9), by, str(index + 1))
        pen.put(head, x + pen.px(26), by, 12.5, bold=True)
        steps_bottom = max(steps_bottom, pen.para(body, x, by + pen.px(22), column, FOLIO_PT, grey=_GREY))

    # The callout: a dark bar and a shaded panel, naming the solutions' page.
    lead_w = pen.width(PLAY_CALLOUT_LEAD + " ", FOLIO_PT)
    body = play_callout_body(page_number + 1)
    inner = width - pen.px(30)
    lead_px = pen.type_px(FOLIO_PT * 1.4)
    # The lead sits on the first line; the body wraps after it.
    first, rest = _first_line(pen, body, inner - lead_w, inner, metrics)
    callout_h = pen.px(20) + lead_px * (1 + len(rest))
    callout_top = steps_bottom + pen.px(18)
    if callout_top + callout_h > frame.footer_rule.y - pen.px(10):
        return None
    stream.fill_grey(_PANEL)
    stream.rectangle(left, callout_top, right, callout_top + callout_h, paint="fill")
    stream.fill_grey(0.0)
    stream.rectangle(left, callout_top, left + pen.px(3), callout_top + callout_h, paint="fill")
    cy = callout_top + pen.px(10) + pen.type_px(FOLIO_PT) * 0.8
    x = pen.put(PLAY_CALLOUT_LEAD, left + pen.px(16), cy, FOLIO_PT, bold=True)
    pen.put(" " + first, x, cy, FOLIO_PT, grey=_GREY)
    for line in rest:
        cy += lead_px
        pen.put(line, left + pen.px(16), cy, FOLIO_PT, grey=_GREY)

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


#: The eyebrow's and badge's ink.
_INK_TEXT = 0.0


def _first_line(pen, text: str, first_width: float, width: float, metrics: FontMetrics) -> tuple[str, List[str]]:
    """``text`` split into a first line of ``first_width`` and the rest wrapped at ``width``."""
    words = text.split()
    first: List[str] = []
    while words and pen.width(" ".join(first + [words[0]]), FOLIO_PT) <= first_width:
        first.append(words.pop(0))
    rest = wrap(" ".join(words), pen.type_px(FOLIO_PT), width, metrics) if words else []
    return " ".join(first), rest
