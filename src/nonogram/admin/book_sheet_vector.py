"""The interior sheet's furniture as PDF operators: folio, rules, label, QR.

CARD-306, under **ADR-0042** (DEC-048). The marks that belong to the *sheet*
rather than to what is drawn on it — the interior frame's header rule and
footer hairline, the footer's grid-size label, the folio, and the QR group
(the placeholder icon with its invitation and typed link) — drawn as a
content stream instead of onto a page bitmap.

Why this is its own module and not a paragraph in
:mod:`nonogram.admin.book_puzzle_vector`
----------------------------------------------------------------------------

Every interior page kind carries the **same** furniture off the **same**
:func:`~nonogram.export.layout.interior_frame`
(``book_pdf_generator._draw_page_frame``, CARD-222/CARD-223), so a page card
that drew it would be the first of four copies — the objection
``book_puzzle_vector``'s own docstring raised and the reason it declined to
draw any. This module is the one copy. ``book_puzzle_vector`` draws what makes
a page a *puzzle* page and nothing else, which is still true of it after this
card.

It imports **no page kind and no generator** — only
:mod:`nonogram.export.layout`'s measurements and
:mod:`nonogram.admin.book_vector`'s vocabulary — so
:mod:`nonogram.admin.book_pdf_generator` can import it the way it already
imports ``book_puzzle_vector``, without the module-level cycle that keeps
``book_guide_vector``/``book_toc_vector``/``book_answer_vector`` out of that
generator's page walk (``book_puzzle_vector``'s "Worktree notes").

What is derived here and what arrives already decided (ADR-0042/R3)
----------------------------------------------------------------------------

**Every position arrives.** The two rules' rows, ends and weights, the label's
x and its direction, the folio's centre, the footer line's baseline and the
QR icon's box and caption anchors are all read off
:class:`~nonogram.export.layout.InteriorFrame`,
:class:`~nonogram.export.layout.QrSlot` and
:class:`~nonogram.export.layout.QrCaption` — the same three COMP-007 objects
the raster footer reads, so there is one definition of where a mark goes and
not two that can drift (AC-3, G-2). **No coordinate is written in this file.**

**Every word arrives too**, composed by the caller: the folio's digits, the
grid-size label (``book_pdf_generator.grid_size_label``), the invitation and
the typed link (``QR_CAPTION_TEXT``/``qr_group_caption``/``qr_link``). Those
live in COMP-009's generator, which this module cannot import, and the same
arrangement ``book_puzzle_vector`` already uses for the band's identity: the
caller keeps the strings, this sets the strings it is given.

**The type sizes arrive as device pixels**, from the caller's own
``type_px(FOLIO_PT, dpi)``/``type_px(SIZE_LABEL_PT, dpi)``/
``type_px(INTERIOR_FOOTER_LINE_PT, dpi)``, exactly as
:mod:`nonogram.admin.book_toc_vector` and
:mod:`nonogram.admin.book_answer_vector` take theirs. All three are 10 pt
today (CON-020's interior floor); they are three fields rather than one
because they are three decisions in the generator and agreeing by accident is
not the same as agreeing.

The footer is all-or-nothing, and here it is one block
----------------------------------------------------------------------------

``_draw_page_frame``'s header rule is unconditional and its footer group is
all-or-nothing: where the page's own content reaches below the footer rule's
row, the rule, the label and the centred folio are **all** omitted and the
page keeps CARD-200's bottom-outer-corner folio instead. *A rule with no
number under it, or a number sitting on a grid, is worse than the corner.*

The raster path spreads that one verdict over three call sites — this
function's own ``content_bottom`` test, and
:func:`~nonogram.export.layout.qr_slot`/:func:`~nonogram.export.layout.qr_caption`
answering ``None`` on the identical figure, which ``tests/test_book_qr_slot.py``
pins as an *equivalence over a corpus*. Here the four marks are one branch of
one function, so the equivalence is not something a test has to establish:
:func:`draw_sheet_furniture` draws the footer rule, the label, the centred
folio and the QR groups together or draws none of them, and it **refuses** a
request that hands it QR groups for a page whose footer is not clear
(:class:`SheetFurnitureError`) rather than drawing a half footer.

The QR block's medium, decided
----------------------------------------------------------------------------

**Operators, not an image XObject** (AC-4). The icon is CARD-204's placeholder
— a bordered square around a plain alternating checkerboard, never a real QR
module pattern — so it is a handful of rectangles, not a photograph: there is
nothing in it that a bitmap would carry and a path would not. Declaring it
raster would mean an entry in ``book_pdf_generator._RASTER_DECLARATIONS`` with
a reason, an ``expires_with`` and an image object per page of the book, to ship
a 5x5 chequer. So the decision is drawn rectangles, and
:func:`~nonogram.admin.book_vector.ContentStream` has no XObject vocabulary at
all to express the other choice with — which is what makes "undeclared XObject
on a vector page" a refusal in ``write_vector_page`` rather than a convention
(see that function).

**What the checkerboard reimplements, and what cross-checks it.** The tiling
below is ``book_pdf_generator._draw_qr_placeholder``'s own arithmetic written
natively, per this package's standing convention for logic shared across a
boundary (``_stroke_drawing``, ``mask_runs``, ``book_puzzle_vector``'s
``BAND_WIDTH_RATIO``) — that generator cannot be imported from here. The
**module count** is not reimplemented: it arrives as
:attr:`SheetFurniture.qr_modules` from the generator's own
``_QR_PLACEHOLDER_MODULES``, so the one number that decides what the glyph
looks like has one definition. The tiling itself is held against the raster
page's ink from the test tree, where the import is legal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nonogram.admin.book_vector import ContentStream, FontMetrics
from nonogram.admin.book_vector_draw import (
    INK_GREY,
    advance_px,
    draw_folio,
)
from nonogram.export.layout import InteriorFrame, PageRule, QrCaption, QrSlot

__all__ = [
    "QrGroup",
    "SheetFurniture",
    "SheetFurnitureError",
    "draw_page_rule",
    "draw_sheet_furniture",
    "qr_module_boxes",
]


class SheetFurnitureError(ValueError):
    """A furniture request that cannot be drawn without making a worse page.

    A :class:`ValueError`, because that is what every other refusal in this
    family raises (``slot_room``'s unplaced layout, ``two_up_page_stream``'s
    empty slot list), and a named subclass so a caller can tell this refusal
    from a mis-typed argument.
    """


@dataclass(frozen=True, slots=True)
class QrGroup:
    """One QR group: where it sits, and the two lines it prints.

    A *group* and not an icon, because the glyph and its two lines are one
    mark to a reader and are omitted together — the arrangement
    :func:`~nonogram.export.layout.qr_caption` already enforces by answering
    ``None`` exactly when :func:`~nonogram.export.layout.qr_slot` does.

    Attributes:
        icon: The icon's box, from ``qr_slot(layout, inset_px=...)``.
        caption: Its two lines' anchor, from ``qr_caption`` on the **same**
            layout and the **same** inset. Pairing them in one object is what
            stops a caller measuring the two on different extents, which is
            the defect CARD-248 removed from the raster two-up page.
        invitation: The first line — ``QR_CAPTION_TEXT`` on a single page,
            ``qr_group_caption(number)`` where a page carries two groups.
        link: The second line, ``qr_link(number)``.
    """

    icon: QrSlot
    caption: QrCaption
    invitation: str
    link: str


@dataclass(frozen=True, slots=True)
class SheetFurniture:
    """One interior page's furniture: where it goes, what it says, how big.

    Every field is the caller's: this type holds no default position and no
    default word, so a page that prints no label says so by passing ``None``
    rather than by this module guessing (ADR-0042/R3, G-2).

    Attributes:
        frame: ``interior_frame(page_spec)`` — the sheet's own frame, which
            is the single source every coordinate below comes from.
        folio: The page number as the footer prints it, as a string. **Not an
            int**: a folio is a word on a page here, and the one place that
            decides how a page number is spelled is the generator.
        folio_size_px: The size the folio is set at, in device pixels.
        size_label: The grid size the footer prints
            (``grid_size_label(columns, rows)``), or ``None`` for a page with
            no one grid size to name — a two-up page, whose two slots carry
            two (the raster path passes ``size_label=None`` there).
        label_size_px: The size that label is set at, in device pixels.
        caption_size_px: The size both QR lines are set at, in device pixels.
        qr_modules: How many modules a side the placeholder chequer has, from
            the generator's ``_QR_PLACEHOLDER_MODULES``.
        groups: The QR groups this page's footer carries — none, one (a single
            puzzle page), or one per puzzle (a two-up page's footer strip).
        content_bottom: The lowest row this page's own content already
            reaches, or ``None`` for a page nothing competes with the footer
            for. Read exactly as ``_draw_page_frame`` reads it: it is what
            decides the footer group, and the one row both sides read is
            ``frame.footer_rule.y``.
        content_right: The content's own rightmost column, for the corner
            folio's omit-rather-than-collide check.
        content_left: Its leftmost column, likewise.
        right_hand: Whether this is a right-hand page
            (``page_is_right_hand(page_number)``), which is which corner the
            fallback folio takes. Not derived here: this module reads no page
            number, and the one reader of a page number's parity lives where
            the page numbers do.
    """

    frame: InteriorFrame
    folio: str
    folio_size_px: float
    size_label: str | None = None
    label_size_px: float = 0.0
    caption_size_px: float = 0.0
    qr_modules: int = 0
    groups: tuple[QrGroup, ...] = field(default_factory=tuple)
    content_bottom: float | None = None
    content_right: float | None = None
    content_left: float | None = None
    right_hand: bool = True

    @property
    def footer_is_clear(self) -> bool:
        """Whether this page's footer group can be drawn at all.

        ``_draw_page_frame``'s own expression, on the same two figures: the
        page's own content stops at or above the row the hairline is stroked
        on. Carried as a property so the writer below reads one verdict and
        a caller that must mirror it (a test, a two-up walk) reads the same
        one rather than restating the inequality.
        """
        return self.content_bottom is None or self.content_bottom <= self.frame.footer_rule.y


def draw_page_rule(
    stream: ContentStream, rule: PageRule, *, grey: float = INK_GREY
) -> None:
    """Stroke one of the frame's ruled lines (``_draw_rule``'s operators).

    The one place a frame rule reaches a content stream, so "the header rule
    and the footer rule are the weights COMP-007 measured" is a property of
    this function rather than of each caller (ADR-0036/R2).

    **The width is the rule's own, in the unit the stream wants.**
    :attr:`~nonogram.export.layout.PageRule.width` is whole device pixels —
    ``_pt_to_px_at_least`` of ``INTERIOR_HEADER_RULE_PT``/
    ``INTERIOR_FOOTER_RULE_PT``, i.e. the stated point weight rounded **up**
    to the device floor that keeps furniture from dropping out on press — so
    :meth:`~nonogram.admin.book_vector.ContentStream.to_points` converts that
    figure back rather than this function reaching for the point constant. The
    two differ: at the book's 300 DPI the hairline's 0.4 pt is 1.667 px, which
    is 2 px and so 0.48 pt in the stream. Converting the *device* figure is
    what makes the vector rule the same physical line the raster page prints
    (G-1's sibling: the two media must not disagree about a rule's weight),
    and it is the only figure a ``PageRule`` carries — unlike a
    :class:`~nonogram.export.layout.GridLine`, which since CARD-227 also
    carries its declared ``width_pt``.

    **Not ADR-0037/R2's floor, and that is not an oversight.** R2 binds the
    puzzle **grid**'s rules and has never bound furniture (that ADR's History,
    2026-10-17). The floor these two rules meet is the 2-device-pixel dropout
    floor CARD-222/CARD-225/CARD-248 cite directly, which is already applied
    inside ``interior_frame`` — so this strokes what it is handed and claims
    no exemption from a rule that does not reach it.
    """
    stream.stroke_grey(grey)
    stream.stroke_width(stream.to_points(rule.width))
    stream.line(rule.left, rule.y, rule.right, rule.y)


def qr_module_boxes(icon: QrSlot, modules: int) -> tuple[tuple[int, int, int, int], ...]:
    """The dark squares of the placeholder chequer inside ``icon``, in device pixels.

    ``book_pdf_generator._draw_qr_placeholder``'s own tiling, reimplemented
    natively (see this module's header for why it is not imported): the box is
    cut into ``modules`` columns and ``modules`` rows of equal share, each
    boundary rounded to a whole pixel the same way, and the squares on the
    odd diagonal — ``(row + column) % 2 != 0`` — are the dark ones.

    Returns them in row-major order, so the stream's operators come out in one
    stated order and an oracle can say what the page must emit rather than
    compare sets.

    Raises:
        SheetFurnitureError: ``modules`` is not positive. A chequer of no
            modules is not a lighter glyph, it is a bordered empty square
            claiming to be a code, which is the one thing CARD-204's
            placeholder is careful not to be.
    """
    if modules <= 0:
        raise SheetFurnitureError(
            f"a placeholder chequer has at least one module a side, not {modules!r}"
        )
    side = icon.right - icon.left
    step = side / modules
    return tuple(
        (
            icon.left + round(column * step),
            icon.top + round(row * step),
            icon.left + round((column + 1) * step),
            icon.top + round((row + 1) * step),
        )
        for row in range(modules)
        for column in range(modules)
        if (row + column) % 2 != 0
    )


def _set_at_baseline(
    stream: ContentStream,
    text: str,
    x: float,
    baseline: float,
    size_px: float,
    metrics: FontMetrics,
    *,
    align: str,
    grey: float,
) -> None:
    """Set ``text`` on ``baseline``, anchored at ``x`` by ``align``.

    ``align`` is ``"left"``, ``"right"`` or ``"centre"`` — the three the
    footer's marks need, which is the vector spelling of the ``lb``/``rb``/
    ``mb`` anchors ``_draw_page_frame`` and ``_draw_qr_caption`` choose
    between. The *choice* is the caller's, read off
    :attr:`~nonogram.export.layout.InteriorFrame.label_right_aligned` and
    :attr:`~nonogram.export.layout.QrCaption.right_aligned`; the only thing
    done here is turning a direction into a pen position through the face's
    own advance.

    **The row is taken as the baseline**, which is the convention every vector
    page kind in this package already uses for a bottom-anchored footer mark
    (``book_vector_draw.draw_folio``, ``book_toc_vector``,
    ``book_answer_vector``) and is exact for a string with no descender.
    Measured on the bundled face: Pillow's ``b`` anchor puts the *ink* box's
    bottom on the row, so for the folio's digits, ``"20 x 25"`` and
    ``"Solve it online"`` the two agree to the pixel, while the typed link —
    whose ``p``/``g`` descend — sets its ink one descender lower here than the
    raster page sets it: 35 px at the book's 300 DPI… (see this module's test
    ``test_the_footer_lines_sit_where_the_raster_page_sets_them``, which pins
    the three exact agreements and records the link's offset as the one
    exception rather than leaving it to be discovered). Reproducing Pillow's
    ink-box anchor would need the face's per-glyph ``yMin``, which
    :class:`~nonogram.admin.book_vector.FontMetrics` does not read and which
    would make this the only mark in the interior placed by a second rule.
    """
    if align == "right":
        pen = x - advance_px(text, size_px, metrics)
    elif align == "centre":
        pen = x - advance_px(text, size_px, metrics) / 2.0
    elif align == "left":
        pen = x
    else:  # pragma: no cover - defensive; the three above are the whole set
        raise SheetFurnitureError(
            f"a footer mark is set left, right or centre, not {align!r}"
        )
    # Bound before the call, for the reason ``book_vector_draw.set_from_top``
    # states: a ``Tf`` operand computed inside the argument list takes this
    # module out of the round-mark walk's own excuse.
    size_pt = stream.to_points(size_px)
    stream.text(text, pen, baseline, size_pt, grey=grey)


def _draw_qr_group(
    stream: ContentStream,
    group: QrGroup,
    furniture: SheetFurniture,
    metrics: FontMetrics,
    grey: float,
) -> None:
    """One QR group: the bordered chequer, then its two lines.

    The border is stroked at the **footer hairline's own width**
    (:attr:`~nonogram.export.layout.PageRule.width`), not at a weight picked
    here. The raster placeholder strokes it at a literal ``width=2``, which is
    the 2-device-pixel furniture floor CARD-222/CARD-248 cite — and that floor
    is exactly what ``interior_frame`` already rounded the hairline up to, so
    the two are the same number on a book page (asserted, not assumed, by
    ``test_the_icons_border_is_the_hairlines_own_weight``). Reading it off the
    frame is what makes it derived rather than transcribed (G-2).
    """
    stream.stroke_grey(grey)
    stream.stroke_width(stream.to_points(furniture.frame.footer_rule.width))
    stream.rectangle(
        group.icon.left, group.icon.top, group.icon.right, group.icon.bottom
    )
    stream.fill_grey(grey)
    for left, top, right, bottom in qr_module_boxes(group.icon, furniture.qr_modules):
        stream.rectangle(left, top, right, bottom, paint="fill")
    align = "right" if group.caption.right_aligned else "left"
    for text, baseline in (
        (group.invitation, group.caption.caption_baseline),
        (group.link, group.caption.link_baseline),
    ):
        _set_at_baseline(
            stream,
            text,
            group.caption.x,
            baseline,
            furniture.caption_size_px,
            metrics,
            align=align,
            grey=grey,
        )


def draw_sheet_furniture(
    stream: ContentStream,
    furniture: SheetFurniture,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> bool:
    """Draw one interior page's furniture onto ``stream``; say if it got a footer.

    ``_draw_page_frame`` plus its callers' QR drawing, in operators and in one
    place. The order is the raster page's: the header rule, then the footer
    group, then the QR groups — so a reader of the stream meets the marks in
    the order the page puts them down.

    **The footer group is one block** (AC-2). Where
    :attr:`SheetFurniture.footer_is_clear` is false the footer rule, the
    grid-size label, the centred folio **and** every QR group are omitted
    together and the page keeps CARD-200's bottom-outer-corner folio instead,
    which is where ``_folio_reserve_px`` keeps room. There is no state in which
    this page carries a frame rule with no number under it or a number
    standing on a drawing: both are the same ``if``.

    Returns:
        Whether the footer group was drawn. ``False`` means the page fell back
        to the corner folio — the verdict is returned rather than re-derived by
        a caller that wants to assert it, exactly as ``_draw_page_frame``
        returns it.

    Raises:
        SheetFurnitureError: ``furniture`` carries QR groups for a page whose
            footer is not clear. ``qr_slot`` answers ``None`` on exactly the
            figure :attr:`SheetFurniture.footer_is_clear` reads, so a caller
            that composed both from one layout cannot produce this; one that
            can has measured the icon on a different extent from the frame,
            which is the defect CARD-248 removed from the raster two-up page.
            Refused rather than silently dropped: dropping it would make this
            function's own verdict the second opinion on a question the caller
            already got wrong.
    """
    draw_page_rule(stream, furniture.frame.header_rule, grey=grey)
    frame = furniture.frame
    if not furniture.footer_is_clear:
        if furniture.groups:
            raise SheetFurnitureError(
                "this page's content reaches below the footer rule at "
                f"y={frame.footer_rule.y}, so it has no footer to carry "
                f"{len(furniture.groups)} QR group(s)"
            )
        draw_folio(
            stream,
            frame.header_rule.left,
            frame.header_rule.y,
            frame.header_rule.right,
            frame.page_bottom,
            furniture.folio,
            furniture.folio_size_px,
            metrics,
            right_hand=furniture.right_hand,
            content_bottom=furniture.content_bottom,
            content_right=furniture.content_right,
            content_left=furniture.content_left,
            grey=grey,
        )
        return False
    draw_page_rule(stream, frame.footer_rule, grey=grey)
    if furniture.size_label is not None:
        _set_at_baseline(
            stream,
            furniture.size_label,
            frame.label_x,
            frame.baseline,
            furniture.label_size_px,
            metrics,
            align="right" if frame.label_right_aligned else "left",
            grey=grey,
        )
    _set_at_baseline(
        stream,
        furniture.folio,
        frame.folio_x,
        frame.baseline,
        furniture.folio_size_px,
        metrics,
        align="centre",
        grey=grey,
    )
    for group in furniture.groups:
        _draw_qr_group(stream, group, furniture, metrics, grey)
    return True
