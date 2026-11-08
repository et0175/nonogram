"""The "How to Solve" spread as PDF content-stream operators (CARD-296, CARD-229, ADR-0042/R1).

CARD-293's spike refused to price this page (its §6 item 4 — *"This is the
largest card and the one the spike deliberately did not price"*), CARD-296
drew it as a second renderer of the raster page, and **CARD-229 redesigned
it** as the facing spread it is today: interior pages 2 (a verso) and 3 (a
recto), in the puzzle pages' own frame —

* the same margins, header rule and footer rule rows
  (:func:`~nonogram.export.layout.guide_spread_layout`, which reads
  :func:`~nonogram.export.layout.interior_frame`), the title set in the band
  where a puzzle page sets its identity, and the folio the puzzle pages' own
  (:func:`~nonogram.admin.book_sheet_vector.draw_sheet_furniture`);
* each technique a row of **two columns**, its numbered heading and short
  explanation on the left and its example on the right;
* the three cell marks as a **key strip** with the difficulty legend beside it,
  the legend's dots CARD-228's (:func:`~nonogram.admin.book_vector_draw.draw_difficulty_dots`);
* **one cell size for every example** on both pages (:func:`example_cell_spec`),
  so the examples look like the puzzles they teach, with a heavier outline
  around the playable squares;
* under the intro, one sentence naming the Play online page when the book
  prints one (CARD-393, folded in).

The module consumes CARD-294's vocabulary (:mod:`nonogram.admin.book_vector`)
and COMP-007's ``Layout`` and draws:

* the page's **title and body text** in the embedded face,
* the **line diagrams** — the basic rule, the three cell-state icons, every
  :class:`~nonogram.admin.book_pdf_generator.GuideTechnique`'s rows and
  CARD-167's four-step **worked example** — all through one routine,
  :func:`draw_line_diagram`,
* the **pipeline diagram** ("assume, and watch it break"),
* the **key strip's legend**,
* the **folio**.

**Every string is a ``GUIDE_*`` constant of the generator** (CARD-229 AC-6):
prose is never written in the drawing code. The worked example's four steps
and the rows/columns callout stay as CARD-201 drew them, because CARD-230
rebuilds them; **when a page cannot hold everything, the ladder in
:data:`_FORMS` gives the worked example up before it gives up the explanations
the spread exists for.**

What this module does **not** do
--------------------------------

* **It derives no geometry** (ADR-0042/R3, restating ADR-0036/R2). The page's
  trim and usable area are :func:`~nonogram.admin.book_pdf_generator.page_frame`'s;
  every diagram's cell pitch, rule width, frame and clue size are
  :func:`~nonogram.export.layout.compute_layout`'s, reached through
  :func:`~nonogram.admin.book_pdf_generator.example_line_layout` and
  :func:`~nonogram.admin.book_pdf_generator.guide_icon_layout`; the thin rule
  the pipeline's boxes are bordered at is
  :func:`~nonogram.admin.book_pdf_generator._guide_rule_width`'s. **Two**
  functions perform arithmetic on a COMP-007 number, and they are the two a
  raster paste already did in pixels: :meth:`_Diagram.translation` — the same
  ``paste`` offset the raster page applies to a cropped diagram, written as an
  offset because a content stream has nothing to paste into — and
  :func:`diagram_box`, whose ``+ pad`` on three edges is the **bleed outset**
  of the box that paste is cropped out of. Neither derives a position; both
  move one COMP-007 gave.

  "The one arithmetic … is translation" is what this said, and review cycle 2
  measured it false by walking every ``ast.BinOp`` whose operand subtree reads
  a guarded ``Layout`` name: ``diagram_box`` was the second, and the paragraph
  below — which lists the module's other arithmetic correctly — omits it, so
  the two disagreed. Counted rather than asserted, because a count in a
  docstring is the kind of sentence a later card quotes.

  Translation is **not** the only arithmetic in the module, and this paragraph
  used to say it was (review cycle 1, F-5) twenty lines above the "Points,
  pixels" section that contradicts it. What the module also computes is the
  **type-derived internal padding** of the two diagrams that are not line
  diagrams, and the page's vertical rhythm: :func:`_pipeline_geometry`'s
  pad/icon/label/box/arrow, the key strip's dot box (a multiple of the leading,
  handed to :func:`~nonogram.export.layout.difficulty_dots`, which places the
  dots), and every leading. Each is a multiple of a
  *point constant of the guide* and of the face's own glyph box, exactly as
  the raster routines this module ports compute them — not a page position,
  and not a number from a ``Layout``, which is what R3 governs. The two
  statements are kept apart here rather than collapsed into one a later card
  would quote.
* **It does not enforce CON-020's floor.** It *records* what it set, so the
  floor can be read: see :class:`DrawnFace` and :attr:`GuidePage.faces`. The
  record is not the control — the control compares it against the ``Tf``
  operands in the written stream, which is the thing a reader's viewer obeys.

Points, pixels, and why this page's type is stated in points
------------------------------------------------------------

The raster page states its type in points and converts **once**, to whole
device pixels, through
:func:`~nonogram.admin.book_pdf_generator.type_px` — "Pillow sizes a face in
pixels, so the conversion is the only thing between 11 pt and the font". That
conversion is a rasterisation step and this medium does not need it: a ``Tf``
operand *is* the physical size. So every size here is the point constant
itself (``GUIDE_BODY_PT`` = 11.0, not ``type_px(11.0, 300) * 72 / 300`` =
11.04), and every vertical rhythm — the leading, the title gap, the gaps
between sections — is that point size scaled to pixels as a **float**, not
rounded to a whole one.

The consequence is deliberate and is the reason it is written down: this page
is **not pixel-identical** to the raster page it replaced, and since CARD-229
it is not the same design either. The raster ``create_guide_page`` still draws
the old single-column page, kept until CARD-387 deletes it; nothing in the
product reads it, and its constants are the strings both pages share.

The one size that is **not** a constant of this module is the clue digit: it
follows its cell (``Layout.clue_font_size``, in device pixels), so it is
converted the other way, by :meth:`~nonogram.admin.book_vector.ContentStream.to_points`.
That is exactly the size CON-020 exempts on a *puzzle* page and does **not**
exempt here — see :data:`CLUE_DIGIT`.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from nonogram.admin.book_pdf_generator import (
    FOLIO_PT,
    GUIDE2_INTRO,
    GUIDE2_TITLE,
    GUIDE_ASSUME_CLOSING,
    GUIDE_ASSUME_HEADING,
    GUIDE_ASSUME_STEPS,
    GUIDE_ASSUME_TEXT,
    GUIDE_BASIC_RULE_CAPTION,
    GUIDE_BASIC_RULE_CLUE,
    GUIDE_BASIC_RULE_CROSSED,
    GUIDE_BASIC_RULE_FILLED,
    GUIDE_BASIC_RULE_HEADING,
    GUIDE_BASIC_RULE_LENGTH,
    GUIDE_BASIC_RULE_TEXT,
    GUIDE_BODY_PT,
    GUIDE_CELL_STATES,
    GUIDE_CELL_STATES_HEADING,
    GUIDE_CERTAINTY_HEADING,
    GUIDE_CLOSING,
    GUIDE_CLOSING_HEADING,
    GUIDE_DIFFICULTY_HEADING,
    GUIDE_DIFFICULTY_LINE,
    GUIDE_DIFFICULTY_LABELS,
    GUIDE_EXAMPLE_HEADING,
    GUIDE_INTRO,
    GUIDE_LEADING_PT,
    GUIDE_SWITCHING_HEADING,
    GUIDE_SWITCHING_TEXT,
    GUIDE_TECHNIQUES_1,
    GUIDE_TECHNIQUES_2,
    GUIDE_TITLE,
    PIPELINE_ICON_BANG,
    PIPELINE_ICON_CROSS,
    PIPELINE_ICON_DOTS,
    PIPELINE_ICON_SQUARE,
    TITLE_PAGE_COUNT,
    WORKED_EXAMPLE_CLUE,
    WORKED_EXAMPLE_LENGTH,
    WORKED_EXAMPLE_STEPS,
    DifficultyLabel,
    ExampleStep,
    GuidePipelineStep,
    GuideTechnique,
    _guide_face,
    _guide_rule_width,
    example_line_layout,
    guide_icon_layout,
    page_frame,
    guide_play_sentence,
    page_is_right_hand,
    type_px,
)
from nonogram.admin.book_plan import TIERS
from nonogram.admin.book_puzzle_vector import band_type_size, draw_band
from nonogram.admin.book_sheet_vector import SheetFurniture, draw_sheet_furniture
from nonogram.admin.book_vector import (
    ContentStream,
    FontMetrics,
    interior_face_metrics,
    write_vector_pdf,
)
from nonogram.admin.book_vector_draw import draw_difficulty_dots, draw_frame, draw_grid_lines
from nonogram.difficulty import tier_of_record
from nonogram.export.layout import (
    MAX_CELL_MM,
    MIN_CELL_MM,
    DifficultyDots,
    Layout,
    PageSpec,
    difficulty_dots,
    guide_example_limit,
    guide_spread_layout,
)

__all__ = [
    "BODY_TEXT",
    "CLUE_DIGIT",
    "FACE_KINDS",
    "FOLIO",
    "GUIDE_PAGE_NUMBERS",
    "PIPELINE_LABEL",
    "DrawnFace",
    "GuideForm",
    "GuidePage",
    "LEGEND_NAME",
    "TITLE",
    "advance_px",
    "diagram_extent",
    "draw_line_diagram",
    "guide_page",
    "guide_pages",
    "wrap",
    "write_guide_pdf",
]

#: Pure black, the only tone this page inks — the vector spelling of
#: ``nonogram.export.png.INK``'s ``(0, 0, 0)``, which is what every mark on
#: today's guide page is drawn in.
_BLACK = 0.0

#: One point is 1/72 in. (The same constant as
#: ``book_vector.POINTS_PER_INCH``; restated rather than imported is *not* the
#: convention here — it is imported below where it is used, through
#: :meth:`ContentStream.to_points`. This module states no conversion of its
#: own.)
#:
#: Named only so the one place that needs the inverse conversion — a pixel
#: size into a point size, for a clue digit that followed its cell — can say
#: which direction it is going. Nothing else reads it.
_POINTS_PER_INCH = 72.0

# --------------------------------------------------------------------------
# The kinds of face this page sets, which is what makes CON-020 readable
# --------------------------------------------------------------------------
#
# CON-020's existing verifier (``tests/test_book_interior_type_floor.py``'s
# ``TestInteriorType_EveryFaceHoldsTheFloor``) works by spying on
# ``ImageDraw.ImageDraw.text`` and tagging each call by the enclosing
# function's name. A vector page makes no such call, so that instrument sees
# nothing here -- and its floor assertion is ``below_floor(...) == []``, which
# is **vacuously true of an empty recording**. What saves it there is the
# sibling that requires a set of covered kinds.
#
# This module carries the same pairing across to the new medium, in the only
# honest form available: it *records* the kind of every string it sets
# (:class:`DrawnFace`), and the control holds that record against the ``Tf``
# operands of the written stream so the record cannot drift from the file,
# then requires :data:`FACE_KINDS` to be covered so the check cannot pass on
# nothing.

#: The page's heading (``GUIDE_TITLE`` / ``GUIDE2_TITLE``).
TITLE = "title"

#: Every paragraph, heading and note of the page's prose.
BODY_TEXT = "body text"

#: A word inside one of the pipeline diagram's boxes, and the ``...``/``!``
#: it letters two of its icons with.
PIPELINE_LABEL = "pipeline label"

#: One tier name in the difficulty legend.
LEGEND_NAME = "legend name"

#: A clue digit of one of this page's line diagrams.
#:
#: **It is NOT exempt from CON-020's floor** (CARD-296 AC-5). The constraint's
#: exemption is two named functions — ``png._draw_clues`` and
#: ``book_pdf_generator._write_clues`` (CARD-184 AC-3) — and it is bounded
#: that way because a *puzzle page's* clue digits are bound to their cell by
#: ``_CLUE_FONT_RATIO`` and INV-006's cell floor puts them at 8.4 pt, so no
#: setting reaches 10 pt there without breaking the cell floor. The floor
#: test's own docstring states the other half: *"The guide page's worked
#: example draws its clue digits through ``_write_clues`` too, from inside
#: ``draw_example_line``; those are the reader's instruction text and are
#: **never** exempt."*
#:
#: This medium has no ``_write_clues`` to tag, so the distinction is made
#: deliberately rather than inherited: a clue digit drawn by this module is
#: tagged with this kind and held to the floor like every other kind, and
#: :data:`EXEMPT_KINDS` is empty.
CLUE_DIGIT = "clue digit"

#: The page number at the bottom-outer corner (CARD-200).
FOLIO = "folio"

#: Every kind of face this page can set. A control over the floor must cover
#: all of them, or it is measuring a subset and reporting a page.
FACE_KINDS = frozenset(
    {TITLE, BODY_TEXT, PIPELINE_LABEL, LEGEND_NAME, CLUE_DIGIT, FOLIO}
)

#: The kinds CON-020 exempts from its 10 pt floor **on this page**: none.
#: Written as an empty set rather than omitted, because "there is no
#: exemption here" is the claim AC-5 makes and an absent name makes no claim.
EXEMPT_KINDS: frozenset = frozenset()

# CON-020's 10 pt floor is deliberately NOT a constant of this module, and
# this module deliberately does not test a size against it. Two reasons, and
# the second was measured rather than reasoned:
#
# * the split this module's own docstring states — it *records* what it set so
#   the floor can be read, and the reading is the control's job, against the
#   ``Tf`` operands of the written file rather than against this record;
# * ``tests/test_book_page_frame.py``'s
#   ``TestBookPageFrame_EachFigureIsDeclaredOnce`` refuses a second name for a
#   figure the package already declares, and 10.0 pt is already
#   ``nonogram.export.layout.INTERIOR_FOOTER_LINE_PT``. A first draft of this
#   module carried a ``FLOOR_PT = 10.0`` and that guard reported it, which is
#   the guard doing exactly its job: a transcribed figure is a figure that can
#   drift.

#: Which interior pages the guide occupies, as offsets from
#: :data:`~nonogram.admin.book_pdf_generator.TITLE_PAGE_COUNT` — the two
#: halves of CARD-201's tutorial, in the order they print.
GUIDE_PAGE_NUMBERS: Tuple[int, int] = (
    1 + TITLE_PAGE_COUNT,
    2 + TITLE_PAGE_COUNT,
)


@dataclass(frozen=True)
class DrawnFace:
    """One string this page set, and the size it set it at.

    Attributes:
        kind: One of :data:`FACE_KINDS`.
        text: The string, as it reaches the stream.
        size_pt: The ``Tf`` operand, in points.
    """

    kind: str
    text: str
    size_pt: float

    def describe(self) -> str:
        return f"{self.kind} {self.text!r}: {self.size_pt:.2f} pt"


@dataclass(frozen=True)
class GuidePage:
    """One drawn guide page: its operators, and what it set.

    Attributes:
        page_number: Its 1-based position in the interior.
        stream: The content stream, ready for
            :func:`~nonogram.admin.book_vector.write_vector_pdf`.
        faces: Every string set on it, in drawing order.
        fallback_level: Which form of the page was drawn: an index into the
            ladder of forms (0 is everything the page can carry; each later one
            drops less valuable marks first).
        form: That form, so a reader can ask what the page kept without
            knowing the ladder.
        content_bottom: The lowest pixel the page's marks reach — the figure
            the folio's omit-rather-than-collide check reads (CARD-200).
    """

    page_number: int
    stream: ContentStream
    faces: Tuple[DrawnFace, ...]
    fallback_level: int
    form: "GuideForm"
    content_bottom: float

    @property
    def kinds(self) -> frozenset:
        """Which of :data:`FACE_KINDS` this page actually set."""
        return frozenset(face.kind for face in self.faces)


# --------------------------------------------------------------------------
# Type measurement: the embedded face's own numbers
# --------------------------------------------------------------------------


def advance_px(text: str, size_px: float, metrics: Optional[FontMetrics] = None) -> float:
    """How wide ``text`` sets at ``size_px``, in device pixels.

    :meth:`~nonogram.admin.book_vector.FontMetrics.advance` is the authority
    and not an estimate: the embedded face is declared ``/TrueType`` with
    ``/WinAnsiEncoding``, for which a viewer consults neither ``GPOS`` nor
    ``kern``, so the sum of the ``/Widths`` this file writes *is* the width
    the reader's viewer will lay out. That is the whole reason a string can be
    centred here without either side knowing the other's rasteriser.
    """
    face = metrics or interior_face_metrics()
    return face.advance(text) * size_px


def ascent_px(size_px: float, metrics: Optional[FontMetrics] = None) -> float:
    """The face's ascender at ``size_px``, in device pixels.

    The number that converts a *top-of-line* position into a baseline, which
    is the one conversion the two media disagree about: Pillow's default
    anchor puts a string's ascender at the ``y`` it is given, and
    :meth:`~nonogram.admin.book_vector.ContentStream.text` puts its baseline
    there.
    """
    face = metrics or interior_face_metrics()
    return face.ascent / 1000.0 * size_px


def descent_px(size_px: float, metrics: Optional[FontMetrics] = None) -> float:
    """The face's descender depth at ``size_px``, in device pixels (positive)."""
    face = metrics or interior_face_metrics()
    return -face.descent / 1000.0 * size_px


def line_height_px(size_px: float, metrics: Optional[FontMetrics] = None) -> float:
    """Ascender plus descender at ``size_px`` — one line's own vertical extent.

    The vector reading of the raster page's ``ascent + descent`` from
    ``font.getmetrics()``, which is what it measures a paragraph line's depth
    with.
    """
    return ascent_px(size_px, metrics) + descent_px(size_px, metrics)


def cap_height_px(size_px: float, metrics: Optional[FontMetrics] = None) -> float:
    """The top of the face's flat capitals at ``size_px``, in device pixels.

    Read off :attr:`~nonogram.admin.book_vector.FontMetrics.cap_height`, which
    CARD-294 fixed: it is ``H``'s own ``glyf`` bounding box, not seven tenths
    of the ascender, and it reproduces FreeType exactly (729/1000 em, against
    the 650 the old guess gave — 10.8 % low).

    **This is the number a clue digit is centred against**, because DejaVu
    sets its decimal digits to cap height: the digits' glyph box runs from the
    baseline to the cap line, so a digit whose box is centred on a clue cell's
    centre has its baseline half a cap height below that centre. It is
    therefore load-bearing here, which is why CARD-294's cycle-2 note N-2 —
    ``_cap_height``'s uncontrolled branches — was routed to this card and
    answered rather than passed on.
    """
    face = metrics or interior_face_metrics()
    return face.cap_height / 1000.0 * size_px


def glyph_box_height_px(text: str, size_px: float) -> float:
    """The vertical extent of ``text``'s own glyph box at ``size_px``.

    The one measurement on this page that the embedded face's PDF metrics
    cannot answer. ``/Widths`` gives advances and the descriptor gives the
    face's ascender, descender, cap height and bounding box; **no per-glyph
    vertical extent crosses a PDF font dictionary**, and the raster page's
    pipeline boxes and difficulty legend are both sized from one —
    ``label_font.getbbox("Mg")``, the height of a capital plus a descender.

    So this reads it through FreeType, from the **same packaged face bytes**,
    by the same door the raster page measures it through
    (:func:`~nonogram.admin.book_pdf_generator._guide_face`). That is not a
    second path to the font file (ADR-0042/R5): it is the project's one
    ``_band_font_bytes`` cache, reached through the one function every
    reader-facing interior page already measures with. Measuring here and
    setting there is the same split CARD-294 already relies on — it
    cross-checks every one of the face's 219 encoded advances against
    FreeType because ``/Widths`` is this writer's own number.

    Pillow sizes a face in whole pixels, so the size is rounded on the way in;
    the value it returns is a diagram's internal padding, not a type size, and
    no ``Tf`` operand is derived from it.
    """
    face = _guide_face(max(1, round(size_px)))
    box = face.getbbox(text)
    return float(box[3] - box[1])


def wrap(
    text: str, size_px: float, measure_px: float, metrics: Optional[FontMetrics] = None
) -> List[str]:
    """``text`` broken greedily at spaces into lines no wider than ``measure_px``.

    A single word wider than ``measure_px`` stays on a line of its own.

    The same greedy rule as
    :func:`~nonogram.admin.book_pdf_generator.wrap_words`, **reimplemented
    rather than imported**: that function measures through a Pillow font
    object's ``getlength`` and this one measures through the embedded face's
    own ``/Widths``, which is the measurement a PDF viewer obeys. The
    convention this package already follows for exactly this case is a native
    reimplementation with a cross-check from the test tree, where importing
    the other one is legal (CLAUDE.md; ``solver/propagate.py``'s ``mask_runs``
    is the precedent, and ``book_vector._exactly`` is the one in this phase).
    """
    face = metrics or interior_face_metrics()
    lines: List[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if current and advance_px(candidate, size_px, face) > measure_px:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


# --------------------------------------------------------------------------
# The one grid routine (CARD-296 AC-4)
# --------------------------------------------------------------------------
#
# There is exactly one drawing path for a ruled grid in this module, and the
# worked example goes through it like every other line diagram. CARD-296's
# AC-4 asks for it to be "CARD-295's grid routine"; CARD-295 draws the puzzle
# page and runs AFTER this card (wave 61 is ordered guide-first -- see the
# routing note on CARD-294's N-2), so there is no such routine to call yet and
# this is it. It is written to be the one CARD-295 consumes: it takes a
# ``Layout`` and a set of filled/crossed cells and knows nothing about a guide
# page, which is the whole of what a puzzle page needs from it.


def diagram_left(layout: Layout) -> int:
    """The leftmost layout coordinate a line diagram's ink reaches.

    The frame's left edge where the layout has a frame — the outer edge of the
    row-clue gutter — and the grid's own first vertical rule where it does
    not (:func:`~nonogram.admin.book_pdf_generator.guide_icon_layout` drops
    the frame for its bare cell icon). Exactly
    :func:`~nonogram.admin.book_pdf_generator.draw_example_line`'s own choice,
    which is what makes the two media put a diagram in the same place.
    """
    if layout.frame is not None:
        return layout.frame.left
    return layout.vertical_lines[0].position


def diagram_box(layout: Layout) -> Tuple[int, int, int, int]:
    """``(left, top, right, bottom)`` of ``layout``'s line diagram.

    Exactly the four expressions
    :func:`~nonogram.admin.book_pdf_generator.draw_example_line` **crops**
    with, bleed margin included: a heavy rule of white on the left and the
    top, and a heavy rule plus one pixel on the right and the bottom.

    **The crop is not cosmetic, and that was measured rather than assumed.**
    The raster routine draws into a full-page canvas and then cuts this box
    out of it, so ink outside the box is discarded — and some is drawn:
    :func:`~nonogram.admin.book_pdf_generator.guide_icon_layout` drops the
    layout's frame but keeps the horizontal rules, which still run the whole
    width of the sheet including the row-clue gutter the icon does not use. A
    content stream has nothing to crop, so every mark is clamped to this box
    on the way out (:func:`_stroke_layout`); without that, each of page 1's
    three cell-state icons drew an extra empty cell to its left, out in the
    page's margin. Caught on a render of the first draft of this module, not
    by any assertion — which is why
    ``TestGuidePage_EveryDiagramStaysInsideItsOwnBox`` exists.
    """
    pad = layout.thick_rule
    return (
        diagram_left(layout) - pad,
        layout.grid_top - pad,
        layout.grid_right + pad + 1,
        layout.grid_bottom + pad + 1,
    )


def diagram_extent(layout: Layout) -> Tuple[int, int]:
    """``(width, height)`` of ``layout``'s line diagram, in device pixels.

    :func:`diagram_box`'s two spans, so the page's fit loop can ask how big a
    diagram is without drawing one — which a content stream cannot do by
    rendering it.
    """
    left, top, right, bottom = diagram_box(layout)
    return right - left, bottom - top


def draw_line_diagram(
    stream: ContentStream,
    layout: Layout,
    step: ExampleStep,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    metrics: Optional[FontMetrics] = None,
) -> Tuple[DrawnFace, ...]:
    """One line diagram — fills, crosses, rules, frame and clue digits.

    The vector counterpart of
    :func:`~nonogram.admin.book_pdf_generator.draw_example_line`, and like it
    the **only** routine in this module that draws a ruled grid: the basic
    rule's "3 2 1", the three bare cell-state icons, every technique's rows
    and CARD-167's four-step worked example all come through here, with
    nothing but their own ``Layout`` and ``step`` to tell them apart. It reads
    nothing module-level, exactly as that function does not.

    Drawing order is that function's, which is the order a puzzle's answer is
    drawn in: filled squares, then crosses, then the ruled lines thin-first
    with the heavy ones and the frame over them, then the clue digits. Where a
    heavy rule crosses a thin one the heavy line is the one that survives the
    overlap and stays continuous.

    ``dx``/``dy`` translate the whole diagram, in device pixels. They are the
    same offset the raster page applies when it pastes the cropped diagram —
    the vector medium has nothing to paste into, so the translation happens at
    the coordinates instead. No size, pitch, width or tone is touched by it
    (ADR-0042/R3): a translation is the one operation that cannot re-derive
    geometry.

    Returns:
        The clue digits it set, as :class:`DrawnFace` records.
    """
    face = metrics or interior_face_metrics()
    xs = [line.position for line in layout.vertical_lines]
    ys = [line.position for line in layout.horizontal_lines]

    # The grid first, in the puzzle pages' own style (their primitives, the
    # layout's declared weights and tones: pale cell lines, heavier every fifth,
    # a border), so the marks a reader fills go on top of it, dark.
    _stroke_layout(stream, layout, dx=dx, dy=dy)

    stream.fill_grey(_BLACK)
    for column in sorted(step.filled):
        stream.rectangle(
            xs[column] + dx,
            ys[0] + dy,
            xs[column + 1] + dx,
            ys[1] + dy,
            paint="fill",
        )

    stream.stroke_grey(_BLACK)
    if step.crossed:
        stream.stroke_width(stream.to_points(layout.thin_rule))
    for column in sorted(step.crossed):
        inset = (xs[column + 1] - xs[column]) // 4
        x0, x1 = xs[column] + inset + dx, xs[column + 1] - inset + dx
        y0, y1 = ys[0] + inset + dy, ys[1] - inset + dy
        stream.line(x0, y0, x1, y1)
        stream.line(x0, y1, x1, y0)

    if layout.frame is not None:
        _outline_playable_squares(stream, layout, xs, ys, dx=dx, dy=dy)
    return _write_clue_digits(stream, layout, dx=dx, dy=dy, metrics=face)


def _outline_playable_squares(
    stream: ContentStream,
    layout: Layout,
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    dx: float,
    dy: float,
) -> None:
    """A heavier outline around the playable squares, apart from their clues.

    CARD-229 AC-5: the examples read as the puzzles they teach, and on a puzzle
    the squares a reader fills are closed off from the clue boxes beside them
    by the grid's own border. The frame :func:`_stroke_layout` strokes closes
    off the clues *and* the squares together, so the squares' own boundary is
    stroked here at the grid's **border** weight and tone, the layout's own
    first vertical line (a border line, the same figure the frame is stroked
    at), and so heavier than every cell line. Every coordinate is one of the
    line positions already read above.
    """
    border = layout.vertical_lines[0]
    stream.stroke_grey(_BLACK if border.grey is None else border.grey)
    stream.stroke_width(
        stream.to_points(border.width) if border.width_pt is None else border.width_pt
    )
    stream.rectangle(
        xs[0] + dx, ys[0] + dy, xs[-1] + dx, ys[1] + dy, paint="stroke"
    )


def _stroke_layout(
    stream: ContentStream, layout: Layout, *, dx: float, dy: float
) -> None:
    """Stroke ``layout``'s ruled lines and frame with the puzzle pages' primitives.

    :func:`~nonogram.admin.book_vector_draw.draw_grid_lines` and
    :func:`~nonogram.admin.book_vector_draw.draw_frame`, the two routines a
    puzzle page draws its grid with: one grid style in the book (CARD-229,
    owner request 2026-11-08), the weights and tones the layout declares
    (ADR-0037/R2) and nothing chosen here. What this adds is the clamp and the
    translation: each line is cut to the box the raster routine cropped its
    diagram out of (see :func:`diagram_box`; a bare cell icon's horizontal rules
    otherwise run the whole sheet) and moved by ``dx``/``dy``, a translation
    being the one operation that cannot re-derive geometry.

    ``layout.frame`` is ``None`` on
    :func:`~nonogram.admin.book_pdf_generator.guide_icon_layout`'s bare cell
    icon: a live branch, taken three times on every page 1 of the guide.
    """
    box_left, box_top, box_right, box_bottom = diagram_box(layout)
    verticals = [
        replace(
            line,
            position=line.position + dx,
            start=max(line.start, box_top) + dy,
            end=min(line.end, box_bottom) + dy,
        )
        for line in layout.vertical_lines
        if box_left <= line.position <= box_right and min(line.end, box_bottom) > max(line.start, box_top)
    ]
    horizontals = [
        replace(
            line,
            position=line.position + dy,
            start=max(line.start, box_left) + dx,
            end=min(line.end, box_right) + dx,
        )
        for line in layout.horizontal_lines
        if box_top <= line.position <= box_bottom and min(line.end, box_right) > max(line.start, box_left)
    ]
    draw_grid_lines(stream, verticals, horizontals)
    frame = layout.frame
    if frame is not None:
        draw_frame(
            stream,
            replace(
                frame,
                left=frame.left + dx,
                top=frame.top + dy,
                right=frame.right + dx,
                bottom=frame.bottom + dy,
            ),
        )


def _write_clue_digits(
    stream: ContentStream,
    layout: Layout,
    *,
    dx: float,
    dy: float,
    metrics: FontMetrics,
) -> Tuple[DrawnFace, ...]:
    """Write ``layout``'s clue numbers, each centred on the point COMP-007 placed.

    The vector reading of
    :func:`~nonogram.admin.book_pdf_generator._write_clues`'s ``anchor="mm"``:
    that anchor centres the glyph box on the point in both axes, so the
    baseline sits half the glyph box's height below the centre and the left
    edge sits half the advance to the left of it. For decimal digits in this
    face the glyph box runs from the baseline to the cap line — DejaVu sets
    its figures to cap height — so the vertical half is
    :func:`cap_height_px`. Both halves are the embedded face's own numbers,
    which is what lets a digit be centred without a rasteriser.

    The size is :attr:`Layout.clue_font_size`, which the layout derived from
    the shared cell, converted to points because that is what a ``Tf`` operand
    is. It is tagged :data:`CLUE_DIGIT` and **not** exempt from CON-020's
    floor (AC-5).
    """
    size_px = layout.clue_font_size
    size_pt = stream.to_points(size_px)
    half_height = cap_height_px(size_px, metrics) / 2.0
    drawn: List[DrawnFace] = []
    for entry in layout.clue_entries:
        text = str(entry.value)
        x = entry.center_x + dx - advance_px(text, size_px, metrics) / 2.0
        y = entry.center_y + dy + half_height
        stream.text(text, x, y, size_pt, grey=_BLACK)
        drawn.append(DrawnFace(CLUE_DIGIT, text, size_pt))
    return tuple(drawn)



# --------------------------------------------------------------------------
# The pipeline diagram, which is not a line diagram
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _PipelineGeometry:
    """The pipeline diagram's internal measurements, in device pixels.

    A **column** of bordered boxes joined by down arrows, each box holding the
    step's word at the left and its icon at the right (CARD-229). It was a row
    of four boxes with the icon under the word, which is 1600 px wide at the
    guide's 11 pt: wider than the example column of a two-column technique on
    every trim but the largest, so the diagram is stacked instead and is as
    wide as one box.
    """

    border: int
    pad: float
    icon: float
    label_h: float
    box_w: float
    box_h: float
    arrow_h: float
    width: float
    height: float


def _pipeline_geometry(
    spec: PageSpec, steps: Sequence[GuidePipelineStep], size_px: float
) -> _PipelineGeometry:
    """The column's own arithmetic, off the same two inputs the row's was.

    The border is :func:`~nonogram.admin.book_pdf_generator._guide_rule_width`'s
    — a puzzle probe layout's thin rule, so the boxes are bordered at the same
    weight as every ruled line on this book's pages (ADR-0037/R2, through
    ``compute_layout`` rather than an invented stroke width). Everything else
    is a multiple of the label's own type size and of the label's glyph box,
    which is the diagram's internal padding and not a page position.
    """
    rule = _guide_rule_width(spec)
    pad = size_px
    label_h = glyph_box_height_px("Mg", size_px)
    icon = size_px * 1.2
    label_w = max(advance_px(step.label, size_px) for step in steps)
    box_w = int(label_w + pad * 3 + icon)
    box_h = int(pad * 2 + max(label_h, icon))
    arrow_h = pad * 1.5
    return _PipelineGeometry(
        border=max(rule, 1),
        pad=pad,
        icon=icon,
        label_h=label_h,
        box_w=box_w,
        box_h=box_h,
        arrow_h=arrow_h,
        width=box_w,
        height=len(steps) * box_h + (len(steps) - 1) * arrow_h,
    )


def pipeline_extent(
    spec: PageSpec, steps: Sequence[GuidePipelineStep], size_px: float
) -> Tuple[float, float]:
    """``(width, height)`` of the pipeline diagram, in device pixels."""
    geometry = _pipeline_geometry(spec, steps, size_px)
    return geometry.width, geometry.height


def draw_pipeline(
    stream: ContentStream,
    spec: PageSpec,
    steps: Sequence[GuidePipelineStep],
    size_px: float,
    size_pt: float,
    *,
    x: float,
    y: float,
    metrics: Optional[FontMetrics] = None,
) -> Tuple[DrawnFace, ...]:
    """"Assume, and watch it break": four bordered boxes joined by arrows.

    Each box is bordered at the page's own thin rule, lettered with the step's
    word at its left and carries its icon at its right: a filled square or a
    crossed square drawn with the same primitives a cell is filled and crossed
    with, and plain ASCII ``"..."``/``"!"`` for the other two
    (:class:`~nonogram.admin.book_pdf_generator.GuidePipelineStep` — a kind,
    deliberately not a Unicode glyph a face might not carry). Pure black ink,
    no fill but the icon's own. An arrow runs down from each box to the next.

    ``x``/``y`` are the diagram's top-left corner on the page.
    """
    face = metrics or interior_face_metrics()
    geometry = _pipeline_geometry(spec, steps, size_px)
    border_pt = stream.to_points(geometry.border)
    half_cap = cap_height_px(size_px, face) / 2.0
    half = geometry.icon / 2.0
    drawn: List[DrawnFace] = []
    top = y
    for index, step in enumerate(steps):
        stream.stroke_grey(_BLACK)
        stream.stroke_width(border_pt)
        stream.rectangle(
            x, top, x + geometry.box_w - 1, top + geometry.box_h - 1, paint="stroke"
        )
        middle = top + geometry.box_h / 2
        # The label, its capitals centred on the box's middle line.
        stream.text(step.label, x + geometry.pad, middle + half_cap, size_pt, grey=_BLACK)
        drawn.append(DrawnFace(PIPELINE_LABEL, step.label, size_pt))

        cx = x + geometry.box_w - geometry.pad - half
        cy = middle
        if step.icon == PIPELINE_ICON_SQUARE:
            stream.fill_grey(_BLACK)
            stream.rectangle(cx - half * 0.5, cy - half * 0.5, cx + half * 0.5, cy + half * 0.5, paint="fill")
        elif step.icon == PIPELINE_ICON_CROSS:
            stream.stroke_grey(_BLACK)
            stream.stroke_width(border_pt)
            stream.line(cx - half * 0.5, cy - half * 0.5, cx + half * 0.5, cy + half * 0.5)
            stream.line(cx - half * 0.5, cy + half * 0.5, cx + half * 0.5, cy - half * 0.5)
        elif step.icon in (PIPELINE_ICON_DOTS, PIPELINE_ICON_BANG):
            glyph = "..." if step.icon == PIPELINE_ICON_DOTS else "!"
            stream.text(
                glyph,
                cx - advance_px(glyph, size_px, face) / 2,
                cy + half_cap,
                size_pt,
                grey=_BLACK,
            )
            drawn.append(DrawnFace(PIPELINE_LABEL, glyph, size_pt))
        else:  # pragma: no cover - defensive; every kind above is handled
            raise ValueError(f"unknown pipeline icon kind: {step.icon!r}")

        top += geometry.box_h
        if index < len(steps) - 1:
            mid_x = x + geometry.box_w / 2
            tip_y = top + geometry.arrow_h - geometry.border
            stream.stroke_grey(_BLACK)
            stream.stroke_width(border_pt)
            stream.line(mid_x, top + geometry.border, mid_x, tip_y)
            head = max(geometry.border * 3, geometry.pad // 2)
            stream.fill_grey(_BLACK)
            stream.begin_path(mid_x, tip_y)
            stream.line_to(mid_x - head, tip_y - head)
            stream.line_to(mid_x + head, tip_y - head)
            stream.close_path()
            stream.paint("fill")
            top += geometry.arrow_h
    return tuple(drawn)


# --------------------------------------------------------------------------
# The shared example cell (CARD-229 AC-5)
# --------------------------------------------------------------------------


def _example_lines() -> List[Tuple[Tuple[int, ...], int]]:
    """Every distinct ``(clue, length)`` line either page of the spread draws."""
    lines: List[Tuple[Tuple[int, ...], int]] = [
        (GUIDE_BASIC_RULE_CLUE, GUIDE_BASIC_RULE_LENGTH),
        (WORKED_EXAMPLE_CLUE, WORKED_EXAMPLE_LENGTH),
    ]
    for entry in (*GUIDE_TECHNIQUES_1, *GUIDE_TECHNIQUES_2):
        lines.append((entry.clue, entry.length))
    return list(dict.fromkeys(lines))


#: How far the shared cell steps down at a time while the examples are too wide
#: for their column, in millimetres.
_CELL_STEP_MM = 0.1


@lru_cache(maxsize=64)
def example_cell_spec(spec: PageSpec, dpi: int) -> PageSpec:
    """``spec`` with the one cell cap every example of the spread is drawn at.

    **One cell for every example on both pages** (CARD-229 AC-5), reached
    through COMP-007 alone: the cap is a ``PageSpec`` field, so each line is
    still laid out by :func:`~nonogram.admin.book_pdf_generator.example_line_layout`
    and this function derives no pitch of its own. It is the largest cap, from
    the book's standard cell down, at which the widest example fits the example
    column's limit
    (:func:`~nonogram.export.layout.guide_example_limit`); and it never goes
    below the cell whose clue digits hold CON-020's 10 pt floor, because the
    guide's digits are instruction text and are not exempt (:data:`CLUE_DIGIT`).
    Where the limit cannot be met at the floor the floor wins and the text
    column is what gives. The search starts at the sheet's own cap (the book's
    standard cell, NFR-008) and a sheet whose cap is the comfort curve starts
    at that curve's largest cell.
    """
    limit = guide_example_limit(spec)
    scale = dpi / _POINTS_PER_INCH
    chosen = spec
    cap = spec.cell_cap if isinstance(spec.cell_cap, float) else MAX_CELL_MM
    while cap >= MIN_CELL_MM:
        candidate = replace(spec, cell_cap=round(cap, 3))
        layouts = [example_line_layout(candidate, c, n) for c, n in _example_lines()]
        if any(layout.clue_font_size / scale < FOLIO_PT for layout in layouts):
            break
        chosen = candidate
        if max(diagram_extent(layout)[0] for layout in layouts) <= limit:
            break
        cap -= _CELL_STEP_MM
    return chosen


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------
#
# Every string is a ``GUIDE_*`` constant of ``book_pdf_generator`` (AC-6). The
# page is the puzzle pages' own frame (``guide_spread_layout``: the same
# margins, header rule and footer rule rows) with the title in the band where a
# puzzle page sets its identity, and a body of rows between the two rules. A
# technique is a row of two columns, its numbered heading and explanation on
# the left and its example on the right.


@dataclass(frozen=True)
class GuideForm:
    """One of the forms a page can take, from everything to the least.

    The ladder is ordered by what a reader loses least: the worked example's
    step sentences go first (CARD-230 rebuilds that block), then the counts and
    the rows' notes, then the framing prose, then the worked example itself, and
    only then the explanations the spread exists for, then the multi-row
    reasoning, the pipeline and the pictures. The worked example outlasts the
    prose because FR-041 promises one and the CON-020 control over its clue
    digits needs one to read. **No form changes a font size** — only which
    marks are drawn and how tight the gaps are.

    Attributes:
        prose: The page's framing sentences: the intro, the switching advice
            and the closing sentences.
        text: Each technique's explanation, the basic rule's and the pipeline's.
        notes: A row's short note ("certain", "Compare") and the basic rule's
            caption.
        steps: The worked example's step sentences, as against their labels.
        counts: "This book contains N puzzles" and the three counts.
        worked: The worked example at all.
        reasoning: Every row of a multi-row technique, as against its last,
            and the pipeline.
        pictures: The key strip's cell-state pictures and the last technique's
            diagram, and the looser gaps.
        captions: The key strip's one-line gloss under each mark's word.
        headings: The key strip's two headings and the section headings
            ("Start with certainty", "Keep switching ...").
        rule: The basic-rule block (its heading, text and diagram).
        last: The last numbered technique of the page's first section.
        legend_line: The one line under the legend's heading.
        tight: The leanest setting: the body keeps
            :data:`~nonogram.export.layout.GUIDE_LEAN_INSET_MM` of white above
            and below instead of the ordinary inset, and the gaps close up.
    """

    prose: bool = True
    text: bool = True
    notes: bool = True
    steps: bool = True
    counts: bool = True
    worked: bool = True
    reasoning: bool = True
    pictures: bool = True
    captions: bool = True
    tight: bool = False
    headings: bool = True
    rule: bool = True
    last: bool = True
    legend_line: bool = True

    @property
    def shows_worked_example(self) -> bool:
        """Whether this form draws the worked example's four steps."""
        return self.worked and self.reasoning


_FORMS: Tuple[GuideForm, ...] = (
    GuideForm(),
    GuideForm(steps=False),
    GuideForm(steps=False, counts=False),
    GuideForm(steps=False, counts=False, notes=False),
    GuideForm(steps=False, counts=False, notes=False, prose=False),
    GuideForm(steps=False, counts=False, notes=False, prose=False, worked=False),
    GuideForm(steps=False, counts=False, notes=False, prose=False, worked=False, text=False),
    GuideForm(
        steps=False,
        counts=False,
        notes=False,
        prose=False,
        worked=False,
        text=False,
        reasoning=False,
    ),
    GuideForm(
        steps=False,
        counts=False,
        notes=False,
        prose=False,
        worked=False,
        text=False,
        reasoning=False,
        pictures=False,
    ),
    GuideForm(
        steps=False,
        counts=False,
        notes=False,
        prose=False,
        worked=False,
        text=False,
        reasoning=False,
        pictures=False,
        captions=False,
        tight=True,
        legend_line=False,
    ),
    GuideForm(
        steps=False,
        counts=False,
        notes=False,
        prose=False,
        worked=False,
        text=False,
        reasoning=False,
        pictures=False,
        captions=False,
        tight=True,
        legend_line=False,
        headings=False,
    ),
    GuideForm(
        steps=False,
        counts=False,
        notes=False,
        prose=False,
        worked=False,
        text=False,
        reasoning=False,
        pictures=False,
        captions=False,
        tight=True,
        legend_line=False,
        headings=False,
        rule=False,
    ),
    GuideForm(
        steps=False,
        counts=False,
        notes=False,
        prose=False,
        worked=False,
        text=False,
        reasoning=False,
        pictures=False,
        captions=False,
        tight=True,
        legend_line=False,
        headings=False,
        rule=False,
        last=False,
    ),
)

#: What :func:`guide_page` offers back, most valuable first, once the ladder has
#: settled on a form: a mark the ladder dropped comes back if the page still
#: fits with it. The ladder only ever removes, so a page that settled low on a
#: sheet with room to spare (a worked-example sentence dropped on one page,
#: leaving a third of the next empty) would otherwise stay bare.
_ADD_BACK: Tuple[str, ...] = (
    "pictures",
    "reasoning",
    "text",
    "worked",
    "prose",
    "notes",
    "counts",
    "steps",
    "legend_line",
    "captions",
)


def _guide_words() -> List[str]:
    """Every word the left (text) column sets, for the column's minimum width."""
    texts = [
        GUIDE_BASIC_RULE_HEADING,
        GUIDE_BASIC_RULE_TEXT,
        GUIDE_ASSUME_HEADING,
        GUIDE_ASSUME_TEXT,
        GUIDE_ASSUME_CLOSING,
    ]
    for entry in (*GUIDE_TECHNIQUES_1, *GUIDE_TECHNIQUES_2):
        texts.extend((entry.heading, entry.caption))
    return [word for text in texts for word in text.split()]


def guide_page(
    spec: PageSpec,
    dpi: int,
    page_number: int,
    *,
    puzzle_count: int = 0,
    easy_count: int = 0,
    medium_count: int = 0,
    hard_count: int = 0,
    play_page: Optional[int] = None,
    metrics: Optional[FontMetrics] = None,
) -> GuidePage:
    """One page of the 2-page "how to solve" spread, as operators.

    ``page_number`` is its 1-based position in the interior **and** which half
    of the tutorial it draws — the half being its position *within* the guide,
    ``page_number - TITLE_PAGE_COUNT``. ``play_page`` is the Play online page's
    interior page number, or ``None`` for a book that prints none: the first
    page then carries the sentence that names it under the intro, and a book
    with none prints exactly the page it would have without the sentence
    (ADR-0041/R8).
    """
    face = metrics or interior_face_metrics()
    page_one = (page_number - TITLE_PAGE_COUNT) % 2 == 1

    scale = dpi / _POINTS_PER_INCH
    body_px = GUIDE_BODY_PT * scale
    leading = GUIDE_LEADING_PT * scale
    body_line = line_height_px(body_px, face)
    body_ascent = ascent_px(body_px, face)

    cell_spec = example_cell_spec(spec, dpi)
    line_layouts: Dict[Tuple[Tuple[int, ...], int], Layout] = {}

    def layout_for(clue: Tuple[int, ...], length: int) -> Layout:
        key = (clue, length)
        layout = line_layouts.get(key)
        if layout is None:
            layout = example_line_layout(cell_spec, clue, length)
            line_layouts[key] = layout
        return layout

    icon_layout = guide_icon_layout(cell_spec)
    example_width = max(
        diagram_extent(layout_for(clue, length))[0] for clue, length in _example_lines()
    )
    text_min = math.ceil(max(advance_px(word, body_px, face) for word in _guide_words()))
    sheet = guide_spread_layout(spec, example_width=example_width, text_min=text_min)
    lean_sheet = guide_spread_layout(
        spec, example_width=example_width, text_min=text_min, lean=True
    )
    left, right = sheet.left, sheet.right
    text_x, text_w = left, sheet.text_width
    example_x = sheet.example_left
    example_w = sheet.example_width

    basic_rule = _Diagram(
        layout_for(GUIDE_BASIC_RULE_CLUE, GUIDE_BASIC_RULE_LENGTH),
        ExampleStep("", "", GUIDE_BASIC_RULE_FILLED, GUIDE_BASIC_RULE_CROSSED),
    )
    cell_states = [
        _Diagram(
            icon_layout,
            ExampleStep(
                "",
                "",
                frozenset({0}) if state.filled else frozenset(),
                frozenset({0}) if state.crossed else frozenset(),
            ),
        )
        for state in GUIDE_CELL_STATES
    ]
    worked_layout = layout_for(WORKED_EXAMPLE_CLUE, WORKED_EXAMPLE_LENGTH)
    worked_example = [_Diagram(worked_layout, step) for step in WORKED_EXAMPLE_STEPS]

    def technique_rows(entry: GuideTechnique) -> List["_Diagram"]:
        layout = layout_for(entry.clue, entry.length)
        return [
            _Diagram(layout, ExampleStep("", "", row.filled, row.crossed))
            for row in entry.rows
        ]

    pipeline_w, pipeline_h = pipeline_extent(spec, GUIDE_ASSUME_STEPS, body_px)

    # The key strip's legend: a row of dots (CARD-228's, through COMP-007) and
    # the tier's name, one entry per tier, in the ladder's own order.
    dot_box_h = round(leading * 1.2)
    dot_box_w = round(dot_box_h * 1.5)
    name_gap = body_px / 2

    def tier_rank(label: DifficultyLabel) -> int:
        tier = tier_of_record(label.name)
        if tier is None or tier not in TIERS:
            raise ValueError(f"the legend names a tier the book does not have: {label.name!r}")
        return TIERS.index(tier) + 1

    def set_page(form: GuideForm) -> Tuple[List["_Mark"], float]:
        """Every mark below the band, and the lowest pixel they reach."""
        marks: List[_Mark] = []
        body_top = (lean_sheet if form.tight else sheet).body_top
        reach = {"bottom": body_top}

        def note(bottom: float) -> None:
            reach["bottom"] = max(reach["bottom"], bottom)

        def paragraph(text: str, x: float, width: float, y: float) -> float:
            """Set ``text`` in the column; return where the next line would go."""
            for line in wrap(text, body_px, width, face):
                marks.append(_Mark(y, x=x, text=line))
                note(y + body_line)
                y += leading
            return y

        def picture(diagram: "_Diagram", x: float, y: float) -> float:
            marks.append(_Mark(y, x=x, diagram=diagram))
            note(y + diagram.height)
            return y + diagram.height

        def gap(amount: Optional[float] = None) -> float:
            if amount is not None:
                return amount
            if form.tight:
                return leading / 8
            return leading / 2 if form.pictures else leading / 6

        def technique(entry: GuideTechnique, rows: List["_Diagram"], y: float) -> float:
            """One technique as a row of two columns; the row's lower edge."""
            ly = paragraph(entry.heading, text_x, text_w, y)
            if form.text:
                ly = paragraph(entry.caption, text_x, text_w, ly)
            ry = y if sheet.two_column else ly
            pairs = list(zip(entry.rows, rows))
            for row, row_diagram in pairs if form.reasoning else pairs[-1:]:
                ry = picture(row_diagram, example_x, ry)
                if row.note and form.notes:
                    ry = paragraph(row.note, example_x, example_w, ry)
            return max(ly, ry) + gap(leading / 4)

        def legend_entry(label: DifficultyLabel, x: float, y: float) -> None:
            dots = difficulty_dots(
                round(x),
                round(y),
                round(x) + dot_box_w - 1,
                round(y) + dot_box_h - 1,
                filled=tier_rank(label),
                total=len(TIERS),
            )
            if dots is not None:
                marks.append(_Mark(y, x=x, dots=dots))
            marks.append(
                _Mark(
                    y,
                    x=x + dot_box_w + name_gap,
                    text=label.name,
                    kind=LEGEND_NAME,
                    dy=(dot_box_h - body_line) / 2,
                )
            )
            note(y + dot_box_h)

        def cell_mark(index: int, x: float, width: float, y: float) -> float:
            """One of the three marks: its picture, then its word and gloss."""
            state = GUIDE_CELL_STATES[index]
            if form.pictures:
                y = picture(cell_states[index], x, y) + leading / 4
            y = paragraph(state.heading, x, width, y)
            return paragraph(state.caption, x, width, y) if form.captions else y

        def key_strip(y: float) -> float:
            """The three marks and the difficulty legend, as one strip."""
            measure = right - left
            mark_words = [
                advance_px(word, body_px, face)
                for state in GUIDE_CELL_STATES
                for word in (state.heading + " " + state.caption).split()
            ]
            name_w = max(
                advance_px(label.name, body_px, face) for label in GUIDE_DIFFICULTY_LABELS
            )
            entry_w = dot_box_w + name_gap + name_w
            zone_pad = body_px / 2
            beside = measure / 4 - zone_pad >= max(max(mark_words), entry_w)
            if beside:
                zone = measure / 4
                top = (
                    paragraph(GUIDE_CELL_STATES_HEADING, left, 3 * zone - zone_pad, y)
                    if form.headings
                    else y
                )
                legend_top = (
                    paragraph(GUIDE_DIFFICULTY_HEADING, left + 3 * zone, zone - zone_pad, y)
                    if form.headings
                    else y
                )
                items = max(top, legend_top) + leading / 4
                lowest = items
                for index in range(len(GUIDE_CELL_STATES)):
                    lowest = max(
                        lowest,
                        cell_mark(index, left + index * zone, zone - zone_pad, items),
                    )
                row = items
                for label in GUIDE_DIFFICULTY_LABELS:
                    legend_entry(label, left + 3 * zone, row)
                    row += dot_box_h
                below = max(lowest, row)
                if form.legend_line:
                    # The line is the legend's, set across the measure under the
                    # strip: a quarter of the measure is too narrow for a sentence.
                    below = paragraph(GUIDE_DIFFICULTY_LINE, left, measure, below + leading / 4)
                return below
            zone = measure / 3
            items = (
                paragraph(GUIDE_CELL_STATES_HEADING, left, measure, y) if form.headings else y
            ) + leading / 4
            lowest = items
            for index in range(len(GUIDE_CELL_STATES)):
                lowest = max(
                    lowest, cell_mark(index, left + index * zone, zone - zone_pad, items)
                )
            items = (
                paragraph(GUIDE_DIFFICULTY_HEADING, left, measure, lowest + gap())
                if form.headings
                else lowest + gap()
            )
            if form.legend_line:
                items = paragraph(GUIDE_DIFFICULTY_LINE, left, measure, items)
            items += leading / 4
            if entry_w <= zone - zone_pad:
                for index, label in enumerate(GUIDE_DIFFICULTY_LABELS):
                    legend_entry(label, left + index * zone, items)
                return items + dot_box_h
            # A name that does not fit its third of the measure would print over
            # the next entry's dots, so the entries stack, one to a row.
            for label in GUIDE_DIFFICULTY_LABELS:
                legend_entry(label, left, items)
                items += dot_box_h
            return items

        y = body_top
        if page_one:
            if form.prose:
                y = paragraph(GUIDE_INTRO, left, right - left, y)
            if play_page is not None:
                y = paragraph(guide_play_sentence(play_page), left, right - left, y)
            if y > body_top:
                y += gap()

            y = key_strip(y) + gap()

            if form.rule:
                ly = paragraph(GUIDE_BASIC_RULE_HEADING, text_x, text_w, y)
                if form.text:
                    ly = paragraph(GUIDE_BASIC_RULE_TEXT, text_x, text_w, ly)
                ry = y if sheet.two_column else ly
                ry = picture(basic_rule, example_x, ry)
                if form.reasoning:
                    # The basic rule's gloss is the explanation of its diagram:
                    # it stays until the page gives up its multi-row reasoning.
                    ry = paragraph(GUIDE_BASIC_RULE_CAPTION, example_x, example_w, ry)
                y = max(ly, ry) + gap()

            if form.headings:
                y = paragraph(GUIDE_CERTAINTY_HEADING, left, right - left, y)
            for index, entry in enumerate(GUIDE_TECHNIQUES_1):
                last = index == len(GUIDE_TECHNIQUES_1) - 1
                if last and not form.last:
                    continue
                if last and not form.pictures:
                    y = paragraph(entry.heading, text_x, text_w, y) + gap(0)
                    continue
                y = technique(entry, technique_rows(entry), y)

            if form.headings:
                y = paragraph(GUIDE_SWITCHING_HEADING, left, right - left, y)
            if form.prose:
                paragraph(GUIDE_SWITCHING_TEXT, left, right - left, y)
        else:
            if form.prose:
                y = paragraph(GUIDE2_INTRO, left, right - left, y) + gap()

            for entry in GUIDE_TECHNIQUES_2:
                y = technique(entry, technique_rows(entry), y)

            ly = paragraph(GUIDE_ASSUME_HEADING, text_x, text_w, y)
            if form.text:
                ly = paragraph(GUIDE_ASSUME_TEXT, text_x, text_w, ly)
                ly = paragraph(GUIDE_ASSUME_CLOSING, text_x, text_w, ly)
            ry = y if sheet.two_column else ly
            if form.reasoning:
                marks.append(
                    _Mark(
                        ry,
                        x=example_x,
                        block=_PIPELINE,
                        width=pipeline_w,
                        height=pipeline_h,
                    )
                )
                note(ry + pipeline_h)
                ry += pipeline_h
            y = max(ly, ry) + gap()

            if form.counts:
                y = paragraph(f"This book contains {puzzle_count} puzzles:", left, right - left, y)
                y = paragraph(f"Easy: {easy_count}", left, right - left, y)
                y = paragraph(f"Medium: {medium_count}", left, right - left, y)
                y = paragraph(f"Hard: {hard_count}", left, right - left, y) + gap()

            if form.shows_worked_example:
                if form.steps:
                    y = paragraph(GUIDE_EXAMPLE_HEADING, left, right - left, y)
                for step, step_diagram in zip(WORKED_EXAMPLE_STEPS, worked_example):
                    y = paragraph(
                        step.caption if form.steps else step.label, left, right - left, y
                    )
                    y = picture(step_diagram, left, y) + leading / 2
                y += gap()

            y = paragraph(GUIDE_CLOSING_HEADING, left, right - left, y)
            if form.prose:
                paragraph(GUIDE_CLOSING, left, right - left, y)

        return marks, reach["bottom"]

    def fits(marks: List["_Mark"], bottom: float, form: GuideForm) -> bool:
        """Whether every drawn mark stays inside the body: below the header
        rule's white, above the footer rule's white, and inside the margins."""
        if bottom > (lean_sheet if form.tight else sheet).body_bottom:
            return False
        for mark in marks:
            if mark.text is not None:
                continue
            width = mark.width if mark.diagram is None else mark.diagram.width
            if mark.dots is not None:
                width = dot_box_w
            if mark.x + width > right:
                return False
        return True

    chosen = len(_FORMS) - 1
    form = _FORMS[chosen]
    marks, bottom = set_page(form)
    for index, candidate in enumerate(_FORMS):
        laid, reached = set_page(candidate)
        if fits(laid, reached, candidate):
            chosen, form, marks, bottom = index, candidate, laid, reached
            break
    else:
        # No form fits: the leanest is drawn, as the page this replaces drew
        # its last form on a sheet too short for any.
        marks, bottom = set_page(form)
    # Offer back, most valuable first, every mark the ladder dropped that the
    # page still has room for (the ladder alone only ever removes).
    for name in _ADD_BACK:
        if getattr(form, name) or form.tight:
            continue
        # Spelled as a constructor, not replace: the placed-page guard
        # (tests/test_book_puzzle_frame.py) reads any replace(**...) as a PageSpec.
        candidate = GuideForm(**{**asdict(form), name: True})
        laid, reached = set_page(candidate)
        if fits(laid, reached, candidate):
            form, marks, bottom = candidate, laid, reached

    trim = page_frame(spec)
    stream = ContentStream(width_px=trim.width, height_px=trim.height, dpi=dpi)

    title_text = GUIDE_TITLE if page_one else GUIDE2_TITLE
    title_px = band_type_size(title_text, sheet.band, right - left, face)
    draw_band(stream, sheet.band, title_text, right - left, face)
    faces: List[DrawnFace] = [DrawnFace(TITLE, title_text, stream.to_points(title_px))]

    for mark in marks:
        if mark.text is not None:
            stream.text(
                mark.text, mark.x, mark.y + mark.dy + body_ascent, GUIDE_BODY_PT, grey=_BLACK
            )
            faces.append(DrawnFace(mark.kind, mark.text, GUIDE_BODY_PT))
        elif mark.diagram is not None:
            dx, dy = mark.diagram.translation(mark.x, mark.y)
            faces.extend(
                draw_line_diagram(
                    stream,
                    mark.diagram.layout,
                    mark.diagram.step,
                    dx=dx,
                    dy=dy,
                    metrics=face,
                )
            )
        elif mark.dots is not None:
            draw_difficulty_dots(stream, mark.dots)
        else:
            faces.extend(
                draw_pipeline(
                    stream,
                    spec,
                    GUIDE_ASSUME_STEPS,
                    body_px,
                    GUIDE_BODY_PT,
                    x=mark.x,
                    y=mark.y,
                    metrics=face,
                )
            )

    # The folio is the puzzle pages': under the footer rule at the trim's
    # centre (``draw_sheet_furniture``), with no grid-size label and no pointer
    # — the page names the Play online page in its own words. A page whose
    # content reaches past the footer rule keeps the corner folio instead
    # (CARD-200) and omits it when it would collide, so what was set is read
    # off the stream rather than assumed: the record is what the page shows.
    folio_px = type_px(FOLIO_PT, dpi)
    written = len(stream.operators)
    draw_sheet_furniture(
        stream,
        SheetFurniture(
            frame=sheet.interior,
            folio=str(page_number),
            folio_size_px=folio_px,
            content_bottom=bottom,
            right_hand=page_is_right_hand(page_number),
        ),
        face,
    )
    if any(f"({page_number}) Tj" in operator for operator in stream.operators[written:]):
        faces.append(DrawnFace(FOLIO, str(page_number), stream.to_points(folio_px)))

    return GuidePage(
        page_number=page_number,
        stream=stream,
        faces=tuple(faces),
        fallback_level=chosen,
        form=form,
        content_bottom=bottom,
    )


#: The one mark kind that is neither text, a line diagram nor dots.
_PIPELINE = "pipeline"


@dataclass(frozen=True)
class _Diagram:
    """One line diagram waiting to be drawn: its layout and its cell states."""

    layout: Layout
    step: ExampleStep

    @property
    def pad(self) -> int:
        return self.layout.thick_rule

    @property
    def left(self) -> int:
        return diagram_left(self.layout)

    @property
    def width(self) -> int:
        return diagram_extent(self.layout)[0]

    @property
    def height(self) -> int:
        return diagram_extent(self.layout)[1]

    def translation(self, x: float, y: float) -> Tuple[float, float]:
        """The ``(dx, dy)`` that lands this diagram's bleed corner at ``(x, y)``.

        The raster page pastes a cropped image, whose pixel ``(0, 0)`` is the
        layout coordinate ``(left - pad, grid_top - pad)``; a content stream
        has nothing to paste into, so the same placement is an offset on the
        coordinates.

        It lives here rather than in :func:`guide_page` so that the page itself
        reads **one** number off a ``Layout`` and not a grid: the paste pad,
        ``icon_layout.thick_rule``-sized, which :class:`_Diagram` holds. This
        docstring used to say the page "never reads a ``Layout``'s grid", which
        is false as written (review cycle 1, F-2), and the correction is
        mechanical rather than verbal: CARD-296's AC-4 guard declares the reads
        as ``guide_page``'s *role* and holds the page to those attribute names,
        so a second number joining them is a test failure.
        """
        return x - (self.left - self.pad), y - (self.layout.grid_top - self.pad)


@dataclass(frozen=True)
class _Mark:
    """One thing the page puts at a ``y``: a line of text, a diagram, a row of
    dots or the pipeline, at the column edge ``x``."""

    y: float
    x: float = 0.0
    text: Optional[str] = None
    kind: str = BODY_TEXT
    dy: float = 0.0
    diagram: Optional[_Diagram] = None
    dots: Optional[DifficultyDots] = None
    block: Optional[str] = None
    width: float = 0.0
    height: float = 0.0


def guide_pages(
    spec_for: Any,
    dpi: int,
    *,
    puzzle_count: int = 0,
    easy_count: int = 0,
    medium_count: int = 0,
    hard_count: int = 0,
    play_page: Optional[int] = None,
) -> List[GuidePage]:
    """Both halves of the tutorial, in the order they print.

    ``spec_for`` is a callable taking an interior page number and returning
    that page's :class:`~nonogram.export.layout.PageSpec` — the shape
    :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.page_spec`
    already has, passed as a callable so this module never holds a generator
    and never reads a book.
    """
    metrics = interior_face_metrics()
    return [
        guide_page(
            spec_for(page_number),
            dpi,
            page_number,
            puzzle_count=puzzle_count,
            easy_count=easy_count,
            medium_count=medium_count,
            hard_count=hard_count,
            play_page=play_page,
            metrics=metrics,
        )
        for page_number in GUIDE_PAGE_NUMBERS
    ]


def write_guide_pdf(pages: Iterable[GuidePage], page_count: int) -> BytesIO:
    """``pages`` as one PDF through CARD-294's writer, rewound to 0.

    Two objects per page — a page and a content stream — and the face's three
    written exactly once for the file (ADR-0042/R5). **No image XObject**, on
    any page, which is AC-1 and is what makes this an ADR-0042/R1 interior
    page rather than a photograph of one.
    """
    return write_vector_pdf(
        (page.stream for page in pages),
        page_count,
        comment="nonogram vector guide",
    )
