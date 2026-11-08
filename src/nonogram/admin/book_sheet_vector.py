"""The interior sheet's furniture as PDF operators: folio, rules, label, pointer.

CARD-306, under **ADR-0042** (DEC-048). The marks that belong to the *sheet*
rather than to what is drawn on it — the interior frame's header rule and
footer hairline, the footer's grid-size label, the folio, and the pointer to
the Play online page (CARD-391; until then a placeholder QR icon with its
invitation and typed link stood there) — drawn as a content stream instead of
onto a page bitmap.

Why this is its own module and not a paragraph in
:mod:`nonogram.admin.book_puzzle_vector`
----------------------------------------------------------------------------

Every interior page kind carries the **same** furniture off the **same**
:func:`~nonogram.export.layout.interior_frame`
(``book_pdf_generator._draw_page_frame``, CARD-222), so a page card
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
x and its direction, the folio's centre and the footer line's baseline are
read off :class:`~nonogram.export.layout.InteriorFrame`, and the pointer's
anchor off :func:`~nonogram.export.layout.footer_pointer` — the same COMP-007
objects, so there is one definition of where a mark goes (G-2). **No
coordinate is written in this file.**

**Every word arrives too**, composed by the caller: the folio's digits, the
grid-size label (``book_pdf_generator.grid_size_label``) and the pointer line
(``book_pdf_generator.footer_pointer_text``). Those live in COMP-009's
generator, which this module cannot import, and the same arrangement
``book_puzzle_vector`` already uses for the band's identity: the caller keeps
the strings, this sets the strings it is given.

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
row, the rule, the label, the pointer and the centred folio are **all** omitted
and the page keeps CARD-200's bottom-outer-corner folio instead. *A rule with no
number under it, or a number sitting on a grid, is worse than the corner.*

Here the marks are one branch of one function:
:func:`draw_sheet_furniture` draws the footer rule, the label, the centred
folio and the pointer together or draws none of them.

The pointer has one more way to be absent that the other footer marks do not:
:func:`~nonogram.export.layout.footer_pointer` declines a line the folio would
collide with (a long line on a narrow trim), and the line is then simply not
drawn. That is a verdict about the sheet and the line's width, never about the
page number (the folio's width is a reserve), so the same two puzzles get the
same answer wherever they print.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from nonogram.admin.book_vector import ContentStream, FontMetrics
from nonogram.admin.book_vector_draw import (
    INK_GREY,
    advance_px,
    draw_folio,
)
from nonogram.export.layout import InteriorFrame, PageRule, footer_pointer

__all__ = [
    "SheetFurniture",
    "SheetFurnitureError",
    "draw_page_rule",
    "draw_sheet_furniture",
]


class SheetFurnitureError(ValueError):
    """A furniture request that cannot be drawn without making a worse page.

    A :class:`ValueError`, because that is what every other refusal in this
    family raises (``slot_room``'s unplaced layout, ``two_up_page_stream``'s
    empty slot list), and a named subclass so a caller can tell this refusal
    from a mis-typed argument.
    """


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
        pointer: The line that points at the Play online page, or ``None``
            for a page that prints none (a book with no Play page). One line
            for the whole page, even a two-up one.
        pointer_size_px: The size that line is set at, in device pixels.
        folio_reserve_px: How wide the folio's ink may be taken to be when the
            pointer is checked against it: the generator's fixed reserve, not
            this page's number, so the verdict is the sheet's.
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
    pointer: str | None = None
    pointer_size_px: float = 0.0
    folio_reserve_px: int = 0
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
    to whole pixels — so
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
    floor CARD-222/CARD-225/CARD-248 cite directly — so this strokes what it is
    handed and claims no exemption from a rule that does not reach it.

    **Where that floor actually comes from, since this docstring got it wrong
    once** (CARD-306's review): *not* from ``_pt_to_px_at_least``, which is a
    ceiling on a conversion and not a minimum of two —
    ``_pt_to_px_at_least(0.2)`` is 1, measured. The floor is held by the two
    **point constants**, chosen so that their conversion lands at 3 px and 2 px
    at the book's 300 DPI (``layout.py``'s own comment on
    ``INTERIOR_FOOTER_RULE_PT``: "Two device pixels is the floor, and this rule
    sits on it"). Nothing applies it as a function.

    So a point constant chosen at or below 0.24 pt (measured: 0.24 pt converts
    to 1 px, 0.2401 pt to 2) is caught by a **test** and not by the conversion,
    and the readings that catch it sit on both sides of the medium split:
    ``test_the_hairline_is_at_the_floor_and_the_header_rule_is_heavier`` on the
    raster page's measured ink (pre-existing, CARD-222/CARD-225's) and
    ``TestPropertyTest_SheetFurniture_EveryFrameRuleMeetsTheFurnitureFloor`` on
    this writer's own ``w`` operand (CARD-306's EC). That makes this card's EC
    the **vector** medium's reading of a floor nothing applies, rather than a
    restatement of one held upstream — more load-bearing than a "floor applied
    in ``interior_frame``" reading would suggest, not less.
    """
    stream.stroke_grey(grey)
    stream.stroke_width(stream.to_points(rule.width))
    stream.line(rule.left, rule.y, rule.right, rule.y)


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
    ``mb`` anchors ``_draw_page_frame`` chooses between. The *choice* is the
    caller's, read off
    :attr:`~nonogram.export.layout.InteriorFrame.label_right_aligned` and
    :attr:`~nonogram.export.layout.FooterPointer.right_aligned`; the only thing
    done here is turning a direction into a pen position through the face's
    own advance.

    **The row is taken as the baseline**, which is the convention every vector
    page kind in this package already uses for a bottom-anchored footer mark
    (``book_vector_draw.draw_folio``, ``book_toc_vector``,
    ``book_answer_vector``) and is exact for a string with no descender.
    Measured on the bundled face: Pillow's ``b`` anchor puts the *ink* box's
    bottom on the row, so for the folio's digits and ``"20 x 25"`` the two
    agree to the pixel, while a string whose ``p``/``g``/``y`` descend (the
    pointer, and the typed link the raster page once set) sits its ink one
    descender lower here than a bottom-anchored raster line sets it: **9
    device px, 0.76 mm, at the book's 300 DPI**. That
    is the face's own ink descent at the footer's size — 42 px of type whose
    declared ascent/descent is (39, 10) — so the offset is bounded by the
    declared descent rather than being a free figure. (An earlier draft of this
    paragraph said 35 px and trailed off. 35 px is ``type_px(8.5, DPI)``, the
    interior clue size ``book_pdf_generator`` records, not this offset; as an
    offset it would be 2.96 mm. CARD-306's review measured the real one.) See
    this module's test
    ``test_the_footer_lines_sit_where_the_raster_page_sets_them``, which pins
    the three exact agreements and asserts both this offset and its bound
    rather than leaving either to be discovered. Reproducing Pillow's
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


def draw_sheet_furniture(
    stream: ContentStream,
    furniture: SheetFurniture,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> bool:
    """Draw one interior page's furniture onto ``stream``; say if it got a footer.

    ``_draw_page_frame`` plus the pointer, in operators and in one place. The
    order is the raster page's: the header rule, then the footer group, then
    the pointer — so a reader of the stream meets the marks in the order the
    page puts them down.

    **The footer group is one block** (AC-2). Where
    :attr:`SheetFurniture.footer_is_clear` is false the footer rule, the
    grid-size label, the centred folio **and** the pointer are omitted
    together and the page keeps CARD-200's bottom-outer-corner folio instead,
    which is where ``_folio_reserve_px`` keeps room. There is no state in which
    this page carries a frame rule with no number under it or a number
    standing on a drawing: both are the same ``if``.

    Returns:
        Whether the footer group was drawn. ``False`` means the page fell back
        to the corner folio — the verdict is returned rather than re-derived by
        a caller that wants to assert it, exactly as ``_draw_page_frame``
        returns it.
    """
    draw_page_rule(stream, furniture.frame.header_rule, grey=grey)
    frame = furniture.frame
    if not furniture.footer_is_clear:
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
    if furniture.pointer is not None:
        pointer_size = furniture.pointer_size_px
        slot = footer_pointer(
            frame,
            math.ceil(advance_px(furniture.pointer, pointer_size, metrics)),
            furniture.folio_reserve_px,
        )
        if slot is not None:
            _set_at_baseline(
                stream,
                furniture.pointer,
                slot.x,
                frame.baseline,
                pointer_size,
                metrics,
                align="right" if slot.right_aligned else "left",
                grey=grey,
            )
    return True
