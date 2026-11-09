"""The answer pages as PDF operators — CARD-297, ADR-0042/R1.

:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator._draw_solved_slot`
in the other medium, and the two pages built on it: one answer to a page
(``solved_puzzle_page``) and two or four small answers sharing one
(``_packed_answer_page``). Every mark is that method's, in that method's
order — the filled picture, the ruled grid, the grey joins between adjacent
filled cells, the clue digits, the band and the caption — and then the page's
own folio.

**The answer key is the only place the book prints a picture's title**
(ADR-0037/R1, FR-033/AC-194), and the two strings a slot sets arrive by
different doors, which is what makes the claim checkable rather than asserted:
the band from :func:`~nonogram.admin.book_pdf_generator.band_identity` (a
number and a tier) and the caption from
:func:`~nonogram.admin.book_answer_key.answer_caption` (a number and the
title). :func:`draw_answer_slot` sets the strings it is handed and composes
neither.

What is reused rather than rewritten
------------------------------------

* **the grid** — :func:`~nonogram.admin.book_vector_draw.draw_grid_lines`,
  CARD-295's routine, called with the two line sequences a slot carries. That
  is this card's AC-3, and the reason it depends on CARD-295 rather than on
  CARD-294 alone. The sequence-taking door is what makes the reuse reach past
  a ``Layout``: the same call draws a clueless
  :class:`~nonogram.export.layout.AnswerTile`, which carries
  ``vertical_lines``/``horizontal_lines`` and is not a ``Layout``;
* **the band** — :func:`~nonogram.admin.book_puzzle_vector.draw_band` and
  :func:`~nonogram.admin.book_puzzle_vector.slot_room`, with their two fitting
  steps. An answer slot's band is a puzzle page's band at a smaller size, and
  the raster path already shares one ``_set_band`` between them;
* **the type anchors and the folio** —
  :mod:`nonogram.admin.book_vector_draw`;
* **every constant, every sheet and the page-parity rule** —
  :mod:`nonogram.admin.book_pdf_generator`, imported rather than restated.

Where this module sits, and why the page is not a generator method
-------------------------------------------------------------------

**Downstream of** :mod:`nonogram.admin.book_pdf_generator`, exactly as
:mod:`nonogram.admin.book_guide_vector` is, and the page is a module-level
function taking its sheet. See
:mod:`nonogram.admin.book_toc_vector`'s own header for the measured reason:
``tests/test_book_export_interior_cover.py``'s door-axis walk holds the
number of ``page_spec``/``book_page_spec`` calls in the generator, and the set
of callers outside it, as equalities — the mechanism that keeps a page
position from being computed in a second place. Taking the sheet adds none.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from nonogram.admin.book_answer_key import (
    CAPTION_SEPARATOR,
    PackedAnswerPage,
    answer_caption,
    answer_title,
)
from nonogram.admin.book_pdf_generator import (
    FOLIO_PT,
    POINTS_PER_INCH,
    PageFrame,
    RUNNING_HEAD_MM,
    _SOLVED_GRID_GRAY,
    answer_section_spec,
    band_identity,
    page_frame,
    page_is_right_hand,
    type_px,
)
from nonogram.admin.book_puzzle_vector import (
    draw_tier_dots,
    shade_clue_cells,
    slot_room,
)
from nonogram.admin.book_vector import ContentStream, FontMetrics, interior_face_metrics
from nonogram.admin.book_vector_draw import (
    INK_GREY,
    _middle_em,
    advance_px,
    as_grey,
    draw_clue_digits,
    draw_folio,
    draw_frame,
    draw_grid_lines,
    page_stream,
)
from nonogram.difficulty import tier_of_record
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    ANSWER_TEXT_FONT_MM,
    ANSWER_TILE_GAP_MM,
    INTERIOR_FOOTER_LINE_PT,
    HeaderBand,
    Layout,
    PageSpec,
    compute_layout,
    compute_packed_solved_layout,
    header_band,
    interior_header_rule_px,
)

__all__ = [
    "SOLVED_JOIN_GREY",
    "AnswerTypeSpec",
    "answer_page",
    "answer_page_stream",
    "answer_type",
    "draw_answer_cells",
    "draw_answer_slot",
    "draw_solved_grid",
    "draw_solved_joins",
    "packed_answer_page",
    "packed_answer_page_stream",
]

#: The lighter tone a solved page rules the join between two adjacent filled
#: cells in, so a reader can still see the grid through a filled region
#: (owner's print layout, 2026-10-07), as a content-stream grey.
#:
#: **Derived from the raster page's own constant, not restated beside it**:
#: ``book_pdf_generator._SOLVED_GRID_GRAY`` is the one place the tone is
#: chosen, and :func:`~nonogram.admin.book_vector_draw.as_grey` is the one
#: conversion — the same arrangement
#: :data:`~nonogram.admin.book_vector_draw.INK_GREY` has with
#: :data:`nonogram.export.png.INK`, so the two media cannot disagree about
#: what a join is printed in without a test noticing.
SOLVED_JOIN_GREY = as_grey(_SOLVED_GRID_GRAY)


@dataclass(frozen=True)
class AnswerTypeSpec:
    """Every figure an answer page's lettering and spacing is set from.

    :func:`answer_type` is the only constructor.

    Attributes:
        caption_size_px: The size a caption is set at. It is CON-020's 10 pt
            floor expressed in millimetres, so there is no type size left to
            give back: a caption too wide is clipped, never shrunk.
        gap_px: The white between a slot's drawing and its caption line —
            a physical millimetre figure, not a type size, which is why it
            converts straight to device pixels rather than through
            :func:`~nonogram.admin.book_pdf_generator.type_px` (the same
            distinction ``_draw_solved_slot`` makes at its own call site).
        folio_size_px: The size the page number at the foot is set at.
    """

    caption_size_px: int
    gap_px: int
    folio_size_px: int


def answer_type(dpi: int) -> AnswerTypeSpec:
    """``_draw_solved_slot``'s own figures at ``dpi``, in device pixels."""
    return AnswerTypeSpec(
        caption_size_px=type_px(ANSWER_TEXT_FONT_MM * POINTS_PER_INCH / 25.4, dpi),
        gap_px=round(ANSWER_TILE_GAP_MM / 25.4 * dpi),
        folio_size_px=type_px(FOLIO_PT, dpi),
    )


def draw_answer_cells(
    stream: ContentStream, tile: Any, grid: Sequence[Sequence[bool]], *, grey: float = INK_GREY
) -> None:
    """Fill the solved picture's cells, each between its own ruled boundaries.

    ``tile`` is anything carrying ``vertical_lines``/``horizontal_lines`` — a
    placed :class:`~nonogram.export.layout.Layout` on a book's answer page, or
    a clueless :class:`~nonogram.export.layout.AnswerTile`. The boundaries are
    read off the rules themselves, so a filled cell and the rule framing it
    cannot be half a pixel apart.

    One ``re`` per filled cell and no run merging: a filled row of twenty
    cells is twenty rectangles rather than one, because merging them would
    change which boundaries the grey joins below are drawn over and so change
    the page, which G-1 forbids. (The raster page fills cell by cell too.)

    ``grid`` is truncated to the tile's own line count, exactly as
    ``_draw_solved_slot`` truncates it: a payload longer than its layout is
    the caller's error to make, and drawing the overflow would put ink outside
    the grid rather than report it.
    """
    xs = [line.position for line in tile.vertical_lines]
    ys = [line.position for line in tile.horizontal_lines]
    set_tone = True
    for row_index, row in enumerate(grid[: len(ys) - 1]):
        for column_index, filled in enumerate(row[: len(xs) - 1]):
            if filled:
                if set_tone:
                    # The tone is set once, and **only if something is
                    # filled**: a page with an empty picture emits no ``g`` at
                    # all, so a reader of the stream cannot mistake a state
                    # operator for a mark. The same reason ``draw_grid_lines``
                    # sets its state on change rather than per line.
                    stream.fill_grey(grey)
                    set_tone = False
                stream.rectangle(
                    xs[column_index],
                    ys[row_index],
                    xs[column_index + 1],
                    ys[row_index + 1],
                    paint="fill",
                )


def draw_solved_joins(
    stream: ContentStream,
    tile: Any,
    grid: Sequence[Sequence[bool]],
    *,
    grey: float = SOLVED_JOIN_GREY,
) -> None:
    """Re-rule, in the lighter tone, every boundary between two filled cells.

    The whole of what makes a solved page readable: the filled picture would
    otherwise be a solid black region with no visible grid, so each internal
    boundary whose two neighbours are *both* filled is drawn again at
    :data:`SOLVED_JOIN_GREY` over the fill. Only the internal boundaries — the
    border rules bound the picture rather than cross it — and each at its own
    declared width, read off the same :class:`~nonogram.export.layout.GridLine`
    the black rule under it was drawn at.
    """
    xs = [line.position for line in tile.vertical_lines]
    ys = [line.position for line in tile.horizontal_lines]
    columns, rows = len(xs) - 1, len(ys) - 1

    # The joins to draw, decided before anything is emitted, so that the tone
    # and each width are set **only where a join is actually drawn**: a picture
    # with no two adjacent filled cells emits no operator from this routine at
    # all, which is what makes "this page draws no join" readable off the
    # stream. The same discipline ``draw_grid_lines`` keeps for its own state.
    #
    # Written as one list rather than through a nested helper on purpose: AC-3's
    # guard attributes a stroke to its **innermost** enclosing function, so a
    # helper that emitted the line would not inherit this function's exemption
    # — correctly, since a nested emitter is exactly how a grid walk could be
    # hidden inside a routine that is allowed to stroke.
    joins: List[Tuple[Any, float, float, float, float]] = []
    for column in range(1, columns):
        line = tile.vertical_lines[column]
        for row in range(rows):
            if grid[row][column - 1] and grid[row][column]:
                joins.append((line, xs[column], ys[row], xs[column], ys[row + 1]))
    for row in range(1, rows):
        line = tile.horizontal_lines[row]
        for column in range(columns):
            if grid[row - 1][column] and grid[row][column]:
                joins.append((line, xs[column], ys[row], xs[column + 1], ys[row]))

    width: float | None = None
    for index, (line, x1, y1, x2, y2) in enumerate(joins):
        if index == 0:
            stream.stroke_grey(grey)
        declared = (
            stream.to_points(line.width) if line.width_pt is None else line.width_pt
        )
        if declared != width:
            stream.stroke_width(declared)
            width = declared
        stream.line(x1, y1, x2, y2)


def draw_solved_grid(
    stream: ContentStream,
    tile: Any,
    grid: Sequence[Sequence[bool]],
    *,
    grey: float = INK_GREY,
    join_grey: float = SOLVED_JOIN_GREY,
) -> None:
    """One solved picture: its filled cells, its rules, and its grey joins.

    The three marks in the order ``_draw_solved_slot`` puts them down — the
    fill first so a heavy every-fifth rule stays continuous across it, then
    :func:`~nonogram.admin.book_vector_draw.draw_grid_lines` (**CARD-295's
    routine, not a second grid walk** — this card's AC-3), then the joins over
    the black rules they lighten.

    Takes the two line sequences off ``tile`` rather than a ``Layout``, which
    is what lets the same call draw a clueless
    :class:`~nonogram.export.layout.AnswerTile`.
    """
    draw_answer_cells(stream, tile, grid, grey=grey)
    draw_grid_lines(stream, tile.vertical_lines, tile.horizontal_lines, grey=grey)
    draw_solved_joins(stream, tile, grid, grey=join_grey)


def _clipped_to_measure(
    text: str, size_px: float, metrics: FontMetrics, measure: float
) -> str:
    """``text`` shortened with a trailing ellipsis until it fits ``measure``.

    ``_clipped_to``'s loop over the embedded face's own advances — the same
    three steps :func:`nonogram.admin.book_toc_vector.clipped_to` runs for a
    TOC row. Not shared between the two writers, for the same reason the
    raster page did not share it until CARD-204 had two callers: a caption and
    a listing row clip for different reasons, and a module named for one page
    kind is a module the other has to reach past.
    """
    clipped = text
    while len(clipped) > 1 and advance_px(clipped, size_px, metrics) > measure:
        clipped = clipped[:-2] + "…"
    return clipped


def draw_answer_slot(
    stream: ContentStream,
    slot: Layout,
    grid: Sequence[Sequence[bool]],
    band: HeaderBand,
    band_text: str,
    caption: str,
    type_spec: AnswerTypeSpec,
    *,
    room: float | None = None,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> Tuple[float, float] | None:
    """One answer's whole content on an already-placed slot, in operators.

    ``_draw_solved_slot``'s marks, in its order: the solved picture and its
    rules, the clue digits, the band, and the caption last. Nothing here fits
    a cell or places a line (ADR-0042/R3, ADR-0036/R2) — every coordinate is
    one ``slot`` already states.

    ``band_text`` is ``band_identity``'s line and ``caption`` is
    ``answer_caption``'s. Both are the caller's strings: ADR-0037/R1 is a
    property of *what is passed here*.

    ``room`` defaults to :func:`~nonogram.admin.book_puzzle_vector.slot_room`'s
    answer for ``slot``, which is what every answer page's caller wants.

    Returns ``None``: the picture's name sits in the header, so no caption box is set under the drawing.
    """
    face = interior_face_metrics() if metrics is None else metrics
    shade_clue_cells(stream, slot)
    draw_solved_grid(stream, slot, grid, grey=grey)
    if slot.frame is not None:
        draw_frame(stream, slot.frame, grey=grey)
    draw_clue_digits(stream, slot, face, grey=grey)
    draw_solution_header(stream, slot, band, band_text, caption, face, grey=grey)
    # The picture's name moved into the header (the approved mockup), so
    # nothing is set under the drawing any more.
    return None


#: The approved mockup's solution header: the number at 12 pt semibold, the
#: picture's name in grey at the 10 pt floor (CON-020), a grey hairline under
#: both. Points, converted at the stream's own resolution.
SOLUTION_NUMBER_PT = 12.0
SOLUTION_NAME_GREY = 0.36
SOLUTION_RULE_GREY = 0.78
_SOLUTION_BOLD_RATIO = 0.04


def draw_solution_header(
    stream: ContentStream,
    slot: Layout,
    band: HeaderBand,
    band_text: str,
    caption: str,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """One solution's header line, in its tile's band (the approved mockup).

    Left to right: the puzzle's number, semibold; the picture's name in grey;
    and, flush right, the tier's dots. A grey hairline runs under the whole
    line, the width of the tile. The number and tier are read from
    ``band_text`` (``band_identity``'s "Puzzle 7 · Easy") and the name from
    ``caption`` (``answer_caption``'s "Puzzle 7 — Snowflake"), so the strings
    the key is built from stay the one source of what it says.
    """
    placement = slot.page
    if band.height <= 0 or placement is None or not band_text:
        return
    identity, _, tier = band_text.partition(" · ")
    number = identity.rpartition(" ")[2]
    _, _, name = caption.partition(CAPTION_SEPARATOR)
    left, right = placement.usable_left, placement.usable_right
    number_px = SOLUTION_NUMBER_PT * stream.dpi / 72.0
    name_px = INTERIOR_FOOTER_LINE_PT * stream.dpi / 72.0
    baseline = band.center_y + _middle_em(metrics) * number_px
    stream.text(
        number, left, baseline, SOLUTION_NUMBER_PT, grey=grey,
        embolden_pt=SOLUTION_NUMBER_PT * _SOLUTION_BOLD_RATIO,
    )
    dots_left = right
    if tier:
        middle = baseline - metrics.cap_height / metrics.units_per_em * name_px / 2
        draw_tier_dots(stream, tier, right, middle, name_px, grey=grey)
        dots_left = right - name_px * 0.55 * 3.6
    if name:
        name_left = left + advance_px(number, number_px, metrics) + name_px * 0.6
        measure = dots_left - name_px * 0.8 - name_left
        if measure > 0:
            if advance_px(name, name_px, metrics) > measure:
                name = _clipped_to_measure(name, name_px, metrics, measure)
            stream.text(name, name_left, baseline, INTERIOR_FOOTER_LINE_PT, grey=SOLUTION_NAME_GREY)
    rule_y = band.center_y + band.height * 0.3
    stream.stroke_grey(SOLUTION_RULE_GREY)
    stream.stroke_width(stream.to_points(interior_header_rule_px()))
    stream.line(left, rule_y, right, rule_y)


def answer_page_stream(
    slot: Layout,
    grid: Sequence[Sequence[bool]],
    band: HeaderBand,
    band_text: str,
    caption: str,
    type_spec: AnswerTypeSpec,
    page_number: int,
    *,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> ContentStream:
    """One full answer page — one puzzle solved, with its folio.

    ``solved_puzzle_page``'s page: the slot is the whole page's
    :class:`~nonogram.export.layout.Layout`, so the folio is placed against
    that layout's own usable area rather than against a separate frame.

    The caption's own box is folded into the folio's collision check **only on
    a right-hand page**, where the right-aligned caption can actually reach the
    corner the folio anchors to — the raster page's own parity gate, and the
    defect its review cycle found when the fold-in was applied on both sides.

    Raises:
        ValueError: ``slot`` is not a placed book page.
    """
    face = interior_face_metrics() if metrics is None else metrics
    placement = slot.page
    if placement is None:
        raise ValueError("a full answer page is drawn on a placed book page")
    right_hand = page_is_right_hand(page_number)
    stream = page_stream(slot)
    caption_box = draw_answer_slot(
        stream, slot, grid, band, band_text, caption, type_spec, metrics=face, grey=grey
    )
    content_bottom: float = placement.drawing_bottom
    content_right: float | None = None
    if caption_box is not None and right_hand:
        content_bottom = max(content_bottom, caption_box[0])
        content_right = caption_box[1]
    draw_folio(
        stream,
        placement.usable_left,
        placement.usable_top,
        placement.usable_right,
        placement.usable_bottom,
        str(page_number),
        type_spec.folio_size_px,
        face,
        right_hand=right_hand,
        content_bottom=content_bottom,
        content_right=content_right,
        grey=grey,
    )
    return stream


def packed_answer_page_stream(
    packed: Any,
    answers: Sequence[Tuple[Sequence[Sequence[bool]], HeaderBand, str, str]],
    frame: PageFrame,
    type_spec: AnswerTypeSpec,
    page_number: int,
    *,
    metrics: FontMetrics | None = None,
    grey: float = INK_GREY,
) -> ContentStream:
    """The page two or four small answers share (FR-042), in operators.

    ``_packed_answer_page``'s page. ``packed`` is COMP-007's
    :class:`~nonogram.export.layout.PackedSolvedLayout` — read for its
    ``slots``, ``tile_rows`` and ``tile_columns`` — and ``answers`` carries one
    ``(grid, band, band_text, caption)`` per slot, in the page's own fill
    order. ``frame`` is the page's
    :class:`~nonogram.admin.book_pdf_generator.PageFrame`: a packed page
    carries no page-level usable area of its own, only each tile's, which is
    the gap the frame fills.

    The folio's content figures come from the **corner tile alone** — the last
    tile row crossed with the last tile column on a right-hand page or the
    first on a left-hand one — because no tile elsewhere on the page can reach
    the corner the folio anchors to, and the plan may have left that position
    unfilled, in which case there is nothing there to collide with.

    Raises:
        ValueError: ``answers`` does not match ``packed``'s slots. A plan whose
            answers and slots disagree is a bug in the walk, and a half-drawn
            page is the one way a book could print an answer key missing an
            answer.
    """
    if len(answers) != len(packed.slots):
        raise ValueError(
            f"{len(answers)} answer(s) for {len(packed.slots)} packed slot(s)"
        )
    face = interior_face_metrics() if metrics is None else metrics
    right_hand = page_is_right_hand(page_number)
    stream = ContentStream(width_px=frame.width, height_px=frame.height, dpi=packed.dpi)
    boxes: List[Tuple[float, float] | None] = []
    for slot, (grid, band, band_text, caption) in zip(
        packed.slots, answers, strict=True
    ):
        boxes.append(
            draw_answer_slot(
                stream,
                slot,
                grid,
                band,
                band_text,
                caption,
                type_spec,
                metrics=face,
                grey=grey,
            )
        )
    corner_column = packed.tile_columns - 1 if right_hand else 0
    corner = (packed.tile_rows - 1) * packed.tile_columns + corner_column
    placement = packed.slots[corner].page if corner < len(packed.slots) else None
    content_bottom = None if placement is None else placement.drawing_bottom
    content_right = None if placement is None else placement.drawing_right
    corner_caption = boxes[corner] if corner < len(boxes) else None
    if right_hand and content_bottom is not None and corner_caption is not None:
        content_bottom = max(content_bottom, corner_caption[0])
        content_right = corner_caption[1]
    draw_folio(
        stream,
        frame.left,
        frame.top,
        frame.right,
        frame.bottom,
        str(page_number),
        type_spec.folio_size_px,
        face,
        right_hand=right_hand,
        content_bottom=content_bottom,
        content_right=content_right,
        content_left=None if placement is None else placement.drawing_left,
        grey=grey,
    )
    return stream


# --------------------------------------------------------------------------
# The two pages, from the arguments their raster twins take
# --------------------------------------------------------------------------


def answer_page(
    spec: PageSpec,
    dpi: int,
    payload: ExportPayload,
    puzzle_number: int,
    page_number: int,
    title: str | None = None,
    *,
    metrics: FontMetrics | None = None,
) -> ContentStream:
    """:meth:`solved_puzzle_page`'s vector twin (FR-042, ADR-0042/R1).

    The same :func:`~nonogram.export.layout.compute_layout` call on the same
    sheet, the same :func:`~nonogram.admin.book_pdf_generator.band_identity`
    line and the same :func:`~nonogram.admin.book_answer_key.answer_caption` —
    so this page differs from the raster one in the medium and in nothing else.

    ``spec`` is ``page_number``'s own sheet, which the raster twin asks
    ``page_spec`` for; it arrives as an argument for the reason this module's
    header gives.

    ``title`` is resolved by the caller
    (:func:`~nonogram.admin.book_answer_key.answer_title` over
    ``custom_titles``), exactly as the raster twin documents, so this function
    never reads ``payload.name`` either.
    """
    layout = compute_layout(payload.row_clues, payload.column_clues, answer_section_spec(spec))
    stream = answer_page_stream(
        layout,
        payload.grid,
        header_band(layout),
        band_identity(puzzle_number, payload.difficulty),
        answer_caption(puzzle_number, title),
        answer_type(dpi),
        page_number,
        metrics=metrics,
    )
    draw_running_head(
        stream, page_frame(spec), page_number, (puzzle_number,), payload.difficulty,
        interior_face_metrics() if metrics is None else metrics,
    )
    return stream


def packed_answer_page(
    spec: PageSpec,
    dpi: int,
    plan: PackedAnswerPage,
    payloads: Sequence[Tuple[Any, ExportPayload]],
    page_number: int,
    titles: Dict[str, str],
    *,
    metrics: FontMetrics | None = None,
) -> ContentStream:
    """:meth:`_packed_answer_page`'s vector twin (CARD-202, ADR-0042/R1).

    The same :func:`~nonogram.export.layout.compute_packed_solved_layout` call
    on the same sheet, each slot drawn by the same routine a full answer page's
    is, and the page's own frame from
    :func:`~nonogram.admin.book_pdf_generator.page_frame`.

    ``payloads`` is every drawable puzzle's ``(id, ExportPayload)``, indexed by
    1-based print number minus one — the list the raster twin is handed.

    Raises:
        ValueError: COMP-007 declines the plan at this capacity, which means
            ``_degrade_infeasible_packed_pages``' guarantee broke rather than
            that this page is a case to recover from — the same contract the
            raster twin raises on.
    """
    members = [payloads[number - 1] for number in plan.numbers]
    layout = compute_packed_solved_layout(
        [(payload.row_clues, payload.column_clues) for _, payload in members],
        plan.capacity,
        answer_section_spec(spec),
    )
    if layout is None:
        raise ValueError(
            f"packed answer page {page_number} ({plan.numbers}) cannot be laid "
            f"out at capacity {plan.capacity} after the packing walk already "
            "found it feasible"
        )
    stream = packed_answer_page_stream(
        layout,
        [
            (
                payload.grid,
                header_band(slot),
                band_identity(number, payload.difficulty),
                answer_caption(
                    number, answer_title(titles.get(str(puzzle_id)), payload.name)
                ),
            )
            for slot, number, (puzzle_id, payload) in zip(
                layout.slots, plan.numbers, members, strict=True
            )
        ],
        page_frame(spec),
        answer_type(dpi),
        page_number,
        metrics=metrics,
    )
    draw_running_head(
        stream, page_frame(spec), page_number, plan.numbers, members[0][1].difficulty,
        interior_face_metrics() if metrics is None else metrics,
    )
    return stream


def running_head_text(numbers: Sequence[int], tier: object) -> Tuple[str, str]:
    """The answer page's running head: ``("SOLUTIONS · EASY", "PUZZLES 1–4")``."""
    record = tier_of_record(tier)
    section = "SOLUTIONS" if record is None else f"SOLUTIONS · {record.label.upper()}"
    if len(numbers) == 1:
        span = f"PUZZLE {numbers[0]}"
    else:
        span = f"PUZZLES {numbers[0]}–{numbers[-1]}"
    return section, span


def draw_running_head(
    stream: ContentStream,
    frame: PageFrame,
    page_number: int,
    numbers: Sequence[int],
    tier: object,
    metrics: FontMetrics,
    *,
    grey: float = INK_GREY,
) -> None:
    """The approved mockup's running head across the top of an answer page.

    "SOLUTIONS · <LEVEL>" on the page's outside edge and the span of puzzle
    numbers on its gutter side, in grey at the 10 pt floor. No rule under it
    (owner, 2026-11-09: it sat too close above each solution's own hairline).
    It sits in the strip
    :func:`~nonogram.admin.book_pdf_generator.answer_section_spec` keeps free.
    """
    section, span = running_head_text(numbers, tier)
    size_pt = INTERIOR_FOOTER_LINE_PT
    size_px = size_pt * stream.dpi / 72.0
    strip_px = RUNNING_HEAD_MM * stream.dpi / 25.4
    rule_y = frame.top + strip_px * 0.55
    baseline = rule_y - size_px * 0.45
    if page_is_right_hand(page_number):
        left_text, right_text = span, section
    else:
        left_text, right_text = section, span
    stream.text(left_text, frame.left, baseline, size_pt, grey=SOLUTION_NAME_GREY)
    width = advance_px(right_text, size_px, metrics)
    stream.text(right_text, frame.right - width, baseline, size_pt, grey=SOLUTION_NAME_GREY)
