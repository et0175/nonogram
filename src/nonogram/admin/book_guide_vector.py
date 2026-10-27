"""The guide page as PDF content-stream operators (CARD-296, ADR-0042/R1).

CARD-293's spike refused to price this page (its §6 item 4 — *"This is the
largest card and the one the spike deliberately did not price"*), so this
module is the first drawing of it. It consumes CARD-294's vocabulary
(:mod:`nonogram.admin.book_vector`) and COMP-007's ``Layout``, and it draws:

* the page's **title and body text** in the embedded face,
* the **line diagrams** — the basic rule, the three cell-state icons, every
  :class:`~nonogram.admin.book_pdf_generator.GuideTechnique`'s rows and
  CARD-167's four-step **worked example** — all through one routine,
  :func:`draw_line_diagram`,
* the **pipeline diagram** ("assume, and watch it break"),
* the **difficulty legend**,
* the **folio**.

**It is a second renderer of the same page, not a redesign of it** (CARD-296
G-1). Every string, every diagram, every fallback level and every position
expression is
:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.create_guide_page`'s,
read from that module's own constants. CARD-229 (the facing spread) and
CARD-230 (the four-step worked example) are queued and gated, and the point of
porting the page before them is that they are then written against a vector
page from the start.

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
  pad/icon/label/box/arrow, :func:`legend_extent`'s strip, the title's fitting
  ladder, ``geometry.icon * 0.3``, and every leading. Each is a multiple of a
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
is **not pixel-identical** to the raster page it replaces, and it was never
going to be (ADR-0042's own Consequences: "the 21
``tests/fixtures/book_baseline_card*.json`` recordings change"). What is
identical is the design — the strings, their order, the diagrams, and which
of the five fallback forms fits.

The one size that is **not** a constant of this module is the clue digit: it
follows its cell (``Layout.clue_font_size``, in device pixels), so it is
converted the other way, by :meth:`~nonogram.admin.book_vector.ContentStream.to_points`.
That is exactly the size CON-020 exempts on a *puzzle* page and does **not**
exempt here — see :data:`CLUE_DIGIT`.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    GUIDE_DIFFICULTY_LABELS,
    GUIDE_EXAMPLE_HEADING,
    GUIDE_INTRO,
    GUIDE_LEADING_PT,
    GUIDE_SWITCHING_HEADING,
    GUIDE_SWITCHING_TEXT,
    GUIDE_TECHNIQUES_1,
    GUIDE_TECHNIQUES_2,
    GUIDE_TITLE,
    GUIDE_TITLE_GAP_PT,
    GUIDE_TITLE_PT,
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
    PageFrame,
    _guide_face,
    _guide_rule_width,
    example_line_layout,
    guide_icon_layout,
    page_frame,
    page_is_right_hand,
)
from nonogram.admin.book_vector import (
    ContentStream,
    FontMetrics,
    interior_face_metrics,
    write_vector_pdf,
)
from nonogram.export.layout import Layout, PageSpec

__all__ = [
    "BODY_TEXT",
    "CLUE_DIGIT",
    "FACE_KINDS",
    "FOLIO",
    "GUIDE_PAGE_NUMBERS",
    "PIPELINE_LABEL",
    "DrawnFace",
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

#: How many points the title's fitting loop steps down by when the heading is
#: wider than the usable measure. The raster page steps by one device pixel
#: (``title_size -= 1``) because Pillow sizes a face in whole pixels; a ``Tf``
#: operand is a real number, so the step is stated in the unit the size is
#: stated in. A quarter point is finer than the pixel step it replaces at
#: every resolution this book is composed at (one pixel is 0.24 pt at 300 DPI),
#: so the fitted title is never *larger* than the raster page's.
_TITLE_FIT_STEP_PT = 0.25


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
        fallback_level: Which of the five fallback forms was drawn, as the
            raster page's own ``(full, captions, bare_level)`` triple.
        content_bottom: The lowest pixel the page's marks reach — the figure
            the folio's omit-rather-than-collide check reads (CARD-200).
    """

    page_number: int
    stream: ContentStream
    faces: Tuple[DrawnFace, ...]
    fallback_level: Tuple[bool, bool, int]
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

    _stroke_layout(stream, layout, dx=dx, dy=dy)
    return _write_clue_digits(stream, layout, dx=dx, dy=dy, metrics=face)


def _stroke_layout(
    stream: ContentStream, layout: Layout, *, dx: float, dy: float
) -> None:
    """Stroke every ruled line of ``layout``, thin ones first, then its frame.

    :func:`~nonogram.admin.book_pdf_generator._stroke_drawing`'s loop, operator
    for operator: the two line families merged, sorted on ``major`` so the
    thin rules go down before the every-fifth rules and the border, and then
    the frame's four sides last of all at :attr:`Layout.thick_rule`.

    Every number is COMP-007's — each line's axis position, its two ends and
    its width, and the frame's four boundaries. Nothing is measured, rounded
    or offset, and a PDF stroke is centred on its path exactly as Pillow
    centres a width on a coordinate, so the half a heavy rule that hangs
    outside the frame's box hangs outside it here too.

    ``layout.frame`` is ``None`` on
    :func:`~nonogram.admin.book_pdf_generator.guide_icon_layout`'s bare cell
    icon — a live branch, taken three times on every page 1 of the guide, not
    dead code.
    """
    box_left, box_top, box_right, box_bottom = diagram_box(layout)
    oriented: List[Tuple[Any, bool]] = [
        *((line, True) for line in layout.vertical_lines),
        *((line, False) for line in layout.horizontal_lines),
    ]
    for line, vertical in sorted(oriented, key=lambda pair: pair[0].major):
        # Clamped to the box the raster routine crops out of its canvas: ink
        # outside it is ink that page never showed (see :func:`diagram_box`).
        if vertical:
            if not box_left <= line.position <= box_right:
                continue
            start = max(line.start, box_top)
            end = min(line.end, box_bottom)
            if end <= start:
                continue
            stream.stroke_width(stream.to_points(line.width))
            stream.line(line.position + dx, start + dy, line.position + dx, end + dy)
        else:
            if not box_top <= line.position <= box_bottom:
                continue
            start = max(line.start, box_left)
            end = min(line.end, box_right)
            if end <= start:
                continue
            stream.stroke_width(stream.to_points(line.width))
            stream.line(start + dx, line.position + dy, end + dx, line.position + dy)

    frame = layout.frame
    if frame is None:
        return
    stream.stroke_width(stream.to_points(frame.width))
    left, top = frame.left + dx, frame.top + dy
    right, bottom = frame.right + dx, frame.bottom + dy
    stream.line(left, top, right, top)
    stream.line(left, bottom, right, bottom)
    stream.line(left, top, left, bottom)
    stream.line(right, top, right, bottom)


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
# The two diagrams that are not line diagrams
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _PipelineGeometry:
    """The pipeline diagram's internal measurements, in device pixels."""

    border: int
    pad: float
    icon: float
    label_h: float
    box_w: float
    box_h: float
    arrow_w: float
    width: float


def _pipeline_geometry(
    spec: PageSpec, steps: Sequence[GuidePipelineStep], size_px: float
) -> _PipelineGeometry:
    """:func:`~nonogram.admin.book_pdf_generator._draw_pipeline_diagram`'s own
    arithmetic, read off the same two inputs it reads it off.

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
    box_w = int(max(advance_px(step.label, size_px) for step in steps) + pad * 2)
    box_h = int(pad * 3 + label_h + size_px * 2)
    arrow_w = pad * 3
    return _PipelineGeometry(
        border=max(rule, 1),
        pad=pad,
        icon=size_px * 2,
        label_h=label_h,
        box_w=box_w,
        box_h=box_h,
        arrow_w=arrow_w,
        width=len(steps) * box_w + (len(steps) - 1) * arrow_w,
    )


def pipeline_extent(
    spec: PageSpec, steps: Sequence[GuidePipelineStep], size_px: float
) -> Tuple[float, float]:
    """``(width, height)`` of the pipeline diagram, in device pixels."""
    geometry = _pipeline_geometry(spec, steps, size_px)
    return geometry.width, geometry.box_h


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

    :func:`~nonogram.admin.book_pdf_generator._draw_pipeline_diagram` in
    operators. Each box is bordered at the page's own thin rule, lettered with
    the step's word centred at the top, and carries its icon under the word: a
    filled square or a crossed square drawn with the same primitives a cell is
    filled and crossed with, and plain ASCII ``"..."``/``"!"`` for the other
    two (:class:`~nonogram.admin.book_pdf_generator.GuidePipelineStep` — a
    kind, deliberately not a Unicode glyph a face might not carry). Pure black
    ink, no fill but the icon's own.

    ``x``/``y`` are the diagram's top-left corner on the page. The raster
    version draws into a canvas of its own and the page pastes it; here the
    corner is an offset, which is the same placement written once instead of
    twice.
    """
    face = metrics or interior_face_metrics()
    geometry = _pipeline_geometry(spec, steps, size_px)
    border_pt = stream.to_points(geometry.border)
    icon_top = y + geometry.pad * 2 + geometry.label_h
    ascent = ascent_px(size_px, face)
    half_cap = cap_height_px(size_px, face) / 2.0
    drawn: List[DrawnFace] = []
    at = x
    for index, step in enumerate(steps):
        stream.stroke_grey(_BLACK)
        stream.stroke_width(border_pt)
        stream.rectangle(
            at, y, at + geometry.box_w - 1, y + geometry.box_h - 1, paint="stroke"
        )
        # ``anchor="ma"`` on the raster side: the label's horizontal middle on
        # the box's centre line, its ascender on ``pad``.
        label_x = at + geometry.box_w / 2 - advance_px(step.label, size_px, face) / 2
        stream.text(step.label, label_x, y + geometry.pad + ascent, size_pt, grey=_BLACK)
        drawn.append(DrawnFace(PIPELINE_LABEL, step.label, size_pt))

        cx = at + geometry.box_w / 2
        cy = icon_top + geometry.icon / 2
        half = geometry.icon * 0.3
        if step.icon == PIPELINE_ICON_SQUARE:
            stream.fill_grey(_BLACK)
            stream.rectangle(cx - half, cy - half, cx + half, cy + half, paint="fill")
        elif step.icon == PIPELINE_ICON_CROSS:
            stream.stroke_grey(_BLACK)
            stream.stroke_width(border_pt)
            stream.line(cx - half, cy - half, cx + half, cy + half)
            stream.line(cx - half, cy + half, cx + half, cy - half)
        elif step.icon in (PIPELINE_ICON_DOTS, PIPELINE_ICON_BANG):
            glyph = "..." if step.icon == PIPELINE_ICON_DOTS else "!"
            # ``anchor="mm"``: the glyph box centred on the icon's own centre.
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

        at += geometry.box_w
        if index < len(steps) - 1:
            mid_y = y + geometry.box_h // 2
            tip_x = at + geometry.arrow_w - geometry.border
            stream.stroke_grey(_BLACK)
            stream.stroke_width(border_pt)
            stream.line(at + geometry.border, mid_y, tip_x, mid_y)
            head = max(geometry.border * 3, geometry.pad // 2)
            stream.fill_grey(_BLACK)
            stream.begin_path(tip_x, mid_y)
            stream.line_to(tip_x - head, mid_y - head)
            stream.line_to(tip_x - head, mid_y + head)
            stream.close_path()
            stream.paint("fill")
            at += geometry.arrow_w
    return tuple(drawn)


def legend_extent(
    labels: Sequence[DifficultyLabel], measure_px: float, size_px: float
) -> Tuple[float, float]:
    """``(width, height)`` of the difficulty legend, in device pixels.

    :func:`~nonogram.admin.book_pdf_generator._draw_difficulty_legend`'s own:
    a ``measure``-wide strip with one ``pad`` of white above and below the row
    of names, ``pad`` being the type size.

    **The width is ``measure_px`` echoed back, not a measurement** (review
    cycle 1, F-8), and the strip's only ink is text: the three tier names,
    which is all this diagram has drawn since CARD-221 fix 1. So there is no
    path ink to hold to this extent the way
    ``TestGuidePage_EveryDiagramStaysInsideItsOwnBox`` holds a line diagram's
    and the pipeline's — the names' own ink is held instead by the page's
    :func:`wrap`/``fits_width`` measure and by AC-2's record-against-stream
    comparison, which is where every string the page sets is accounted for.
    The day the legend draws a shape again (**CARD-229**, the key strip with
    CARD-228's dots) it gets the extent control the pipeline has, and the
    vertex bound on this page's paths already applies to it.
    """
    pad = size_px
    return measure_px, pad * 2 + glyph_box_height_px("Mg", size_px)


def draw_legend(
    stream: ContentStream,
    labels: Sequence[DifficultyLabel],
    measure_px: float,
    size_px: float,
    size_pt: float,
    *,
    x: float,
    y: float,
    metrics: Optional[FontMetrics] = None,
) -> Tuple[DrawnFace, ...]:
    """"What the difficulty labels mean": the three tier names, in a row.

    :func:`~nonogram.admin.book_pdf_generator._draw_difficulty_legend` in
    operators — one column per entry, each holding its tier's
    :attr:`~nonogram.admin.book_pdf_generator.DifficultyLabel.name` and
    nothing else, flush at the measure's own left edge, with one ``gutter``
    between columns.

    **It draws no round shape, and that is today's page and not an omission.**
    CARD-296's brief calls the legend's dots "the card's one genuinely new
    primitive"; the legend has had no dots since CARD-221 fix 1 retired
    ``_draw_difficulty_box`` — the owner's decision of 2026-10-14 stopped
    printing the three sentences, and the ruled box went with them, leaving
    three words in a row. The round mark the brief means is
    :func:`~nonogram.admin.book_pdf_generator._draw_difficulty_dots`, which
    **CARD-229** places in the guide's key strip; that card is queued and
    gated, and CARD-296 G-1 forbids drawing its design here. See this card's
    Worktree notes.
    """
    face = metrics or interior_face_metrics()
    pad = size_px
    gutter = pad
    column_w = (measure_px - gutter * (len(labels) - 1)) // len(labels)
    ascent = ascent_px(size_px, face)
    drawn: List[DrawnFace] = []
    at = x
    for label in labels:
        stream.text(label.name, at, y + pad + ascent, size_pt, grey=_BLACK)
        drawn.append(DrawnFace(LEGEND_NAME, label.name, size_pt))
        at += column_w + gutter
    return tuple(drawn)


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------
#
# Every expression below is ``create_guide_page``'s. The five fallback forms,
# the order of the sections, which text each form drops, which diagram each
# ``bare_level`` drops, the width check and the folio's omit-rather-than-
# collide rule are all that method's, read from the same constants.


def guide_page(
    spec: PageSpec,
    dpi: int,
    page_number: int,
    *,
    puzzle_count: int = 0,
    easy_count: int = 0,
    medium_count: int = 0,
    hard_count: int = 0,
    metrics: Optional[FontMetrics] = None,
) -> GuidePage:
    """One page of the 2-page "how to solve" tutorial, as operators.

    ``page_number`` is its 1-based position in the interior **and** which half
    of the tutorial it draws — the half being its position *within* the guide,
    ``page_number - TITLE_PAGE_COUNT`` — exactly as the raster method reads
    it. The page's margins are mirrored by the position itself like any other
    page's (FR-043), through
    :func:`~nonogram.admin.book_pdf_generator.page_frame`.
    """
    face = metrics or interior_face_metrics()
    frame: PageFrame = page_frame(spec)
    stream = ContentStream(width_px=frame.width, height_px=frame.height, dpi=dpi)
    page_one = (page_number - TITLE_PAGE_COUNT) % 2 == 1

    scale = dpi / _POINTS_PER_INCH
    body_px = GUIDE_BODY_PT * scale
    leading = GUIDE_LEADING_PT * scale
    measure = frame.right - frame.left
    title_pt = GUIDE_TITLE_PT
    title_text = GUIDE_TITLE if page_one else GUIDE2_TITLE
    # On a narrow trim the title is wider than the measure: set it a step
    # smaller at a time until it fits, never below the body size.
    while (
        title_pt > GUIDE_BODY_PT
        and advance_px(title_text, title_pt * scale, face) > measure
    ):
        title_pt = max(GUIDE_BODY_PT, title_pt - _TITLE_FIT_STEP_PT)

    # Inside the usable area the layout reported, so the guide page keeps the
    # book's mirrored margins like every other interior page. The raster page
    # draws it at ``(frame.left, frame.top)`` with Pillow's default anchor,
    # which puts the ascender on ``frame.top``; the baseline is that plus the
    # ascender.
    stream.text(
        title_text,
        frame.left,
        frame.top + ascent_px(title_pt * scale, face),
        title_pt,
        grey=_BLACK,
    )
    faces: List[DrawnFace] = [DrawnFace(TITLE, title_text, title_pt)]
    first = frame.top + GUIDE_TITLE_GAP_PT * scale
    body_line = line_height_px(body_px, face)

    # Every line diagram this page draws, laid out once regardless of which
    # fallback form is chosen: one ``example_line_layout`` call per distinct
    # ``(clue, length)`` pair, cached so a technique whose rows share a line
    # lays it out once.
    line_layouts: Dict[Tuple[Tuple[int, ...], int], Layout] = {}

    def layout_for(clue: Tuple[int, ...], length: int) -> Layout:
        key = (clue, length)
        layout = line_layouts.get(key)
        if layout is None:
            layout = example_line_layout(spec, clue, length)
            line_layouts[key] = layout
        return layout

    icon_layout = guide_icon_layout(spec)
    pad = icon_layout.thick_rule

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
    legend_w, legend_h = legend_extent(GUIDE_DIFFICULTY_LABELS, measure, body_px)

    def set_page(
        full: bool, captions: bool, bare_level: int = 0
    ) -> Tuple[List["_Mark"], float]:
        """Every mark below the title, and the lowest pixel they reach.

        ``create_guide_page``'s ``set_page``, with its five fallback forms
        unchanged: ``bare_level`` 0 is labels-only, 1 drops a multi-row
        technique's reasoning rows, the pipeline and the worked-example recap,
        and 2 also drops page 1's cell-state pictures and its "mark spaces"
        diagram and tightens the gaps between sections. **No level changes a
        font size** — only which diagrams and gaps are drawn.
        """
        marks: List[_Mark] = []
        state = {"y": first, "bottom": first}

        def paragraph(text: str) -> None:
            for line in wrap(text, body_px, measure, face):
                marks.append(_Mark(state["y"], text=line))
                state["bottom"] = state["y"] + body_line
                state["y"] += leading

        def picture(diagram: "_Diagram", gap: float, *, needs_pad: bool = True) -> None:
            marks.append(_Mark(state["y"], diagram=diagram, needs_pad=needs_pad))
            state["bottom"] = state["y"] + diagram.height
            state["y"] = state["bottom"] + gap

        def block(kind: str, width: float, height: float, gap: float) -> None:
            marks.append(_Mark(state["y"], block=kind, width=width, height=height))
            state["bottom"] = state["y"] + height
            state["y"] = state["bottom"] + gap

        def space(amount: Optional[float] = None) -> None:
            if amount is None:
                amount = leading / 6 if bare_level >= 2 else leading / 2
            state["y"] += amount

        def technique(
            entry: GuideTechnique,
            rows: List["_Diagram"],
            *,
            draw_diagram: bool = True,
        ) -> None:
            paragraph(entry.heading)
            if full:
                paragraph(entry.caption)
            if draw_diagram:
                last_row_only = bare_level >= 1
                pairs = list(zip(entry.rows, rows))
                drawn = pairs[-1:] if last_row_only else pairs
                for row, row_diagram in drawn:
                    picture(row_diagram, gap=0)
                    if row.note and captions:
                        paragraph(row.note)
            space(0 if bare_level >= 2 else leading / 4)

        if page_one:
            if full:
                paragraph(GUIDE_INTRO)
                space()

            paragraph(GUIDE_BASIC_RULE_HEADING)
            if full:
                paragraph(GUIDE_BASIC_RULE_TEXT)
            picture(basic_rule, gap=0)
            if captions:
                paragraph(GUIDE_BASIC_RULE_CAPTION)
            space()

            paragraph(GUIDE_CELL_STATES_HEADING)
            for cell_state, cell_diagram in zip(GUIDE_CELL_STATES, cell_states):
                paragraph(cell_state.heading)
                if captions:
                    paragraph(cell_state.caption)
                if bare_level < 2:
                    picture(cell_diagram, gap=leading / 4)
            space()

            paragraph(GUIDE_CERTAINTY_HEADING)
            for index, entry in enumerate(GUIDE_TECHNIQUES_1):
                last = index == len(GUIDE_TECHNIQUES_1) - 1
                technique(
                    entry,
                    technique_rows(entry),
                    draw_diagram=not (bare_level >= 2 and last),
                )

            paragraph(GUIDE_SWITCHING_HEADING)
            if full:
                paragraph(GUIDE_SWITCHING_TEXT)
        else:
            if full:
                paragraph(GUIDE2_INTRO)
                space()

            for entry in GUIDE_TECHNIQUES_2:
                technique(entry, technique_rows(entry))

            paragraph(GUIDE_ASSUME_HEADING)
            if full:
                paragraph(GUIDE_ASSUME_TEXT)
            if bare_level < 1:
                block(_PIPELINE, pipeline_w, pipeline_h, gap=leading / 4)
            if full:
                paragraph(GUIDE_ASSUME_CLOSING)
            space()

            paragraph(GUIDE_DIFFICULTY_HEADING)
            block(_LEGEND, legend_w, legend_h, gap=leading / 2)

            if full:
                paragraph(f"This book contains {puzzle_count} puzzles:")
                paragraph(f"Easy: {easy_count}")
                paragraph(f"Medium: {medium_count}")
                paragraph(f"Hard: {hard_count}")
                space()

            if bare_level < 1:
                if captions:
                    paragraph(GUIDE_EXAMPLE_HEADING)
                for step, step_diagram in zip(WORKED_EXAMPLE_STEPS, worked_example):
                    paragraph(step.caption if captions else step.label)
                    picture(step_diagram, gap=leading / 2)
                space()

            paragraph(GUIDE_CLOSING_HEADING)
            if full:
                paragraph(GUIDE_CLOSING)

        return marks, state["bottom"]

    def fits_width(marks: List["_Mark"]) -> bool:
        """Whether every drawn mark stays inside ``frame.right``.

        ``create_guide_page``'s own check (its review cycle 3, F-20), with the
        same tolerance: a line diagram may cross ``frame.right`` by up to half
        a heavy rule, because its frame's border is centred *on* its boundary
        coordinate and half of it hangs outside the box — the by-design
        sideways bleed every puzzle page's grid already has. The pipeline and
        the legend draw flush with no such bleed and get none of it. A text
        mark is skipped: :func:`wrap` already wrapped it to ``measure``.
        """
        for mark in marks:
            if mark.text is not None:
                continue
            width = mark.width if mark.diagram is None else mark.diagram.width
            x = frame.left - pad if mark.needs_pad else frame.left
            bleed = (pad + 1) // 2 if mark.needs_pad else 0
            if x + width > frame.right + bleed:
                return False
        return True

    chosen: Tuple[bool, bool, int] = (False, False, 2)
    marks: List[_Mark] = []
    bottom = first
    for level in ((True, True, 0), (False, True, 0), (False, False, 0), (False, False, 1), (False, False, 2)):
        marks, bottom = set_page(*level)
        chosen = level
        if bottom <= frame.bottom and fits_width(marks):
            break

    body_ascent = ascent_px(body_px, face)
    for mark in marks:
        if mark.text is not None:
            stream.text(
                mark.text, frame.left, mark.y + body_ascent, GUIDE_BODY_PT, grey=_BLACK
            )
            faces.append(DrawnFace(BODY_TEXT, mark.text, GUIDE_BODY_PT))
        elif mark.diagram is not None:
            diagram = mark.diagram
            x = frame.left - pad if mark.needs_pad else frame.left
            dx, dy = diagram.translation(x, mark.y)
            faces.extend(
                draw_line_diagram(
                    stream, diagram.layout, diagram.step, dx=dx, dy=dy, metrics=face
                )
            )
        elif mark.block == _PIPELINE:
            faces.extend(
                draw_pipeline(
                    stream,
                    spec,
                    GUIDE_ASSUME_STEPS,
                    body_px,
                    GUIDE_BODY_PT,
                    x=frame.left,
                    y=mark.y,
                    metrics=face,
                )
            )
        else:
            faces.extend(
                draw_legend(
                    stream,
                    GUIDE_DIFFICULTY_LABELS,
                    measure,
                    body_px,
                    GUIDE_BODY_PT,
                    x=frame.left,
                    y=mark.y,
                    metrics=face,
                )
            )

    # The folio, after every mark above. ``bottom`` is the chosen fallback
    # form's own lowest mark, never re-measured, so a tight fallback on a
    # small trim omits the folio exactly when it would otherwise collide with
    # this page's own last line (CARD-200's omit-rather-than-collide rule).
    faces.extend(
        _draw_folio(
            stream,
            frame,
            page_number,
            scale,
            content_bottom=bottom,
            metrics=face,
        )
    )

    return GuidePage(
        page_number=page_number,
        stream=stream,
        faces=tuple(faces),
        fallback_level=chosen,
        content_bottom=bottom,
    )


#: The two mark kinds that are neither text nor a line diagram.
_PIPELINE = "pipeline"
_LEGEND = "legend"


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
        ``icon_layout.thick_rule``, hoisted once — which is exactly what the
        raster page reads at ``book_pdf_generator.py:4361``. This docstring
        used to say the page "never reads a ``Layout``'s grid", which is false
        as written (review cycle 1, F-2), and the correction is mechanical
        rather than verbal: CARD-296's AC-4 guard now declares that read as
        ``guide_page``'s *role* and holds the page to that one attribute name,
        so a second number joining it is a test failure.
        """
        return x - (self.left - self.pad), y - (self.layout.grid_top - self.pad)


@dataclass(frozen=True)
class _Mark:
    """One thing the page puts at a ``y``: a line of text, a diagram or a block."""

    y: float
    text: Optional[str] = None
    diagram: Optional[_Diagram] = None
    block: Optional[str] = None
    width: float = 0.0
    height: float = 0.0
    needs_pad: bool = False


def _draw_folio(
    stream: ContentStream,
    frame: PageFrame,
    page_number: int,
    scale: float,
    *,
    content_bottom: float,
    metrics: FontMetrics,
) -> Tuple[DrawnFace, ...]:
    """``page_number``'s plain-decimal folio at the bottom-outer corner.

    :func:`~nonogram.admin.book_pdf_generator._draw_folio`'s guide-page path:
    the vertical-only room check (this page passes no horizontal figure, as
    the raster guide does not either), and Pillow's ``"rb"``/``"lb"`` anchor
    at the usable area's bottom-outer corner, picked by
    :func:`~nonogram.admin.book_pdf_generator.page_is_right_hand` (FR-043).

    The anchor's bottom is the *glyph box's* bottom, which for a decimal
    number is its baseline — digits have no descender — so unlike the "mm"
    and "ma" anchors elsewhere on this page the baseline here is simply
    ``frame.bottom``. Written out rather than left implicit, because it is the
    one anchor conversion on the page that is the identity and a reader should
    not have to re-derive that.
    """
    size_px = FOLIO_PT * scale
    text = str(page_number)
    if frame.bottom - content_bottom < line_height_px(size_px, metrics):
        return ()
    if page_is_right_hand(page_number):
        x = frame.right - advance_px(text, size_px, metrics)
    else:
        x = frame.left
    stream.text(text, x, frame.bottom, FOLIO_PT, grey=_BLACK)
    return (DrawnFace(FOLIO, text, FOLIO_PT),)


def guide_pages(
    spec_for: Any,
    dpi: int,
    *,
    puzzle_count: int = 0,
    easy_count: int = 0,
    medium_count: int = 0,
    hard_count: int = 0,
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
