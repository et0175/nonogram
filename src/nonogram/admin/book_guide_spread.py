"""The "How to Solve" spread, set as the owner's approved mockup (2026-11-08).

The mockup Olia approved (artifact "Puzzle page layout", version A) sets the
two guide pages as a typeset spread rather than as a column of equal-size
lines: a large title, section headings, numbered badges, a shaded key strip,
two columns per technique (text left, example right), a horizontal
"assume" pipeline, a 2x2 worked example, a tip callout anchored to the foot of
page 2 and the difficulty box anchored to the foot of page 3.

This module draws exactly that, with the pieces the generator already has:

* every string is a ``GUIDE_*`` constant of the generator (CARD-229 AC-6);
* every line diagram is :func:`~nonogram.admin.book_guide_vector.draw_line_diagram`
  over :func:`~nonogram.admin.book_pdf_generator.example_line_layout`, at the
  one example cell (:func:`~nonogram.admin.book_guide_vector.example_cell_spec`),
  so the examples keep the puzzle pages' grid style;
* the difficulty dots are :func:`~nonogram.export.layout.difficulty_dots`';
* the header rule, footer rule and folio are the puzzle pages'
  (:func:`~nonogram.admin.book_sheet_vector.draw_sheet_furniture`), the band
  carries "How to Solve" where a puzzle page carries its identity.

**One face** (ADR-0042/R5): headings are the same DejaVu Sans set with a thin
stroke on top of its fill (text render mode 2), which is how a single embedded
face reads as a semibold without embedding a second font. **No string is set
under 10 pt** (CON-020), clue digits included.

Positions are the mockup's, in points from the top of the body, scaled down
uniformly only when a sheet's text block is narrower than the mockup's; the
diagrams keep their own COMP-007 size and are placed, never resized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from nonogram.admin import book_guide_vector as guide_vector
from nonogram.admin.book_guide_vector import (
    BODY_TEXT,
    FOLIO,
    LEGEND_NAME,
    PIPELINE_LABEL,
    TITLE,
    DrawnFace,
    GuidePage,
    _FORMS,
    diagram_box,
    draw_line_diagram,
    example_cell_spec,
    wrap,
)
from nonogram.admin.book_pdf_generator import (
    FOLIO_PT,
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
    GUIDE_CELL_STATES,
    GUIDE_CELL_STATES_HEADING,
    GUIDE_CERTAINTY_HEADING,
    GUIDE_DIFFICULTY_HEADING,
    GUIDE_DIFFICULTY_LABELS,
    GUIDE_DIFFICULTY_LINE,
    GUIDE_EXAMPLE_HEADING,
    GUIDE_INTRO,
    GUIDE_SWITCHING_HEADING,
    GUIDE_SWITCHING_TEXT,
    GUIDE_TECHNIQUES_1,
    GUIDE_TECHNIQUES_2,
    GUIDE_TITLE,
    GUIDE2_INTRO,
    GUIDE2_TITLE,
    WORKED_EXAMPLE_CLUE,
    WORKED_EXAMPLE_LENGTH,
    WORKED_EXAMPLE_STEPS,
    ExampleStep,
    GuideTechnique,
    example_line_layout,
    guide_icon_layout,
    guide_play_sentence,
    page_frame,
    page_is_right_hand,
    type_px,
)
from nonogram.admin.book_plan import TIERS
from nonogram.admin.book_puzzle_vector import band_type_size, draw_band
from nonogram.admin.book_sheet_vector import SheetFurniture, draw_sheet_furniture
from nonogram.admin.book_vector import ContentStream, FontMetrics, interior_face_metrics
from nonogram.admin.book_vector_draw import draw_difficulty_dots
from nonogram.difficulty import tier_of_record
from nonogram.export.layout import (
    DIFFICULTY_DOT_GAP_RATIO,
    DIFFICULTY_DOT_RATIO,
    Layout,
    PageSpec,
    difficulty_dots,
)

__all__ = ["RUNNING_HEAD", "spread_page"]

#: What the band says on both guide pages, where a puzzle page says "Puzzle 1 · Easy".
RUNNING_HEAD = "How to Solve"

_INK = 0.0
#: The mockup's secondary text (#5b616b) and its shaded panels (#f1f2f4).
_GREY = 0.37
_SHADE = 0.945
_HAIRLINE = 0.77

# Type sizes, points (mockup's, every one at or over CON-020's 10 pt).
_TITLE_PT = 26.0
_TITLE2_PT = 22.0
_INTRO_PT = 12.0
_SECTION_PT = 15.0
_HEAD_PT = 12.5
_BODY_PT = 10.5
_SMALL_PT = FOLIO_PT  # CON-020's floor, the folio's own size
_LEAD = 1.4
#: The stroke that thickens a heading: a fraction of its size, in points.
_BOLD_RATIO = 0.04

#: The mockup's text block width (US Letter less its margins): positions scale
#: with the sheet's block only when it is narrower.
_MOCK_WIDTH_PT = 522.0


@dataclass
class _Pen:
    stream: ContentStream
    face: FontMetrics
    scale: float  # device px per point of spacing, already including any shrink
    dpi: float
    left: float
    right: float
    faces: List[DrawnFace] = field(default_factory=list)

    def px(self, points: float) -> float:
        return points * self.scale

    def type_px(self, size_pt: float) -> float:
        """A type size in device px: type is never shrunk, only spacing."""
        return size_pt * self.dpi / 72.0

    def width(self, text: str, size_pt: float) -> float:
        return self.face.advance(text) * self.type_px(size_pt)

    def put(
        self,
        value: str,
        x: float,
        baseline: float,
        size_pt: float,
        *,
        grey: float = _INK,
        bold: bool = False,
        kind: str = BODY_TEXT,
        align: str = "left",
    ) -> float:
        """Set one line; returns its right edge."""
        w = self.width(value, size_pt)
        if align == "centre":
            x -= w / 2
        elif align == "right":
            x -= w
        self.stream.text(
            value, x, baseline, size_pt, grey=grey,
            embolden_pt=size_pt * _BOLD_RATIO if bold else 0.0,
        )
        self.faces.append(DrawnFace(kind, value, size_pt))
        return x + w

    def para(
        self,
        value: str,
        x: float,
        top_baseline: float,
        width: float,
        size_pt: float,
        *,
        grey: float = _INK,
        bold: bool = False,
    ) -> float:
        """A wrapped paragraph; returns the baseline the next line would take."""
        lead = self.type_px(size_pt * _LEAD)
        y = top_baseline
        for line in wrap(value, self.type_px(size_pt), width, self.face):
            self.put(line, x, y, size_pt, grey=grey, bold=bold)
            y += lead
        return y

    def para_height(self, value: str, width: float, size_pt: float) -> float:
        return len(wrap(value, self.type_px(size_pt), width, self.face)) * self.type_px(size_pt * _LEAD)

    def rule(self, y: float, grey: float = _HAIRLINE, width_pt: float = 0.4) -> None:
        self.stream.stroke_grey(grey)
        self.stream.stroke_width(width_pt)
        self.stream.line(self.left, y, self.right, y)

    def box(self, left: float, top: float, right: float, bottom: float, grey: float) -> None:
        self.stream.fill_grey(grey)
        self.stream.rectangle(left, top, right, bottom, paint="fill")


@dataclass(frozen=True)
class _Lines:
    """The line layouts of one page, all at the spread's one example cell."""

    spec: PageSpec

    def layout(self, clue: Tuple[int, ...], length: int) -> Layout:
        return example_line_layout(self.spec, clue, length)


def _diagram(pen: _Pen, layout: Layout, step: ExampleStep, x: float, top: float) -> Tuple[float, float]:
    """Draw a line diagram with its box's top-left at ``(x, top)``; return its (right, bottom)."""
    left, box_top, right, bottom = diagram_box(layout)
    dx, dy = x - left, top - box_top
    pen.faces.extend(draw_line_diagram(pen.stream, layout, step, dx=dx, dy=dy, metrics=pen.face))
    return right + dx, bottom + dy


def _step(filled=frozenset(), crossed=frozenset()) -> ExampleStep:
    return ExampleStep("", "", frozenset(filled), frozenset(crossed))


def _unnumbered(heading: str) -> Tuple[str, str]:
    """``"2. Squeeze from both ends"`` as ``("2", "Squeeze from both ends")``."""
    number, _, rest = heading.partition(". ")
    return (number, rest) if number.isdigit() else ("", heading)


def _badge(pen: _Pen, cx: float, baseline: float, number: str) -> None:
    """The mockup's numbered black disc, its digit white."""
    r = pen.px(9)
    cy = baseline - pen.px(4)
    # The disc is the book's one round mark, a single solid difficulty dot,
    # so it comes from the one routine that draws round marks.
    # The box difficulty_dots fits a dot of exactly 2r into, centred on (cx, cy).
    half_h = r / DIFFICULTY_DOT_RATIO
    half_w = r * (1 + DIFFICULTY_DOT_GAP_RATIO)
    disc = difficulty_dots(round(cx - half_w), round(cy - half_h), round(cx + half_w),
                           round(cy + half_h), filled=1, total=1)
    if disc is not None:
        draw_difficulty_dots(pen.stream, disc, grey=_INK)
    digit_px = pen.type_px(_SMALL_PT)
    cap = pen.face.cap_height / pen.face.units_per_em * digit_px
    pen.put(number, cx, cy + cap / 2, _SMALL_PT, grey=1.0, bold=True, align="centre")


def _technique(
    pen: _Pen,
    y: float,
    heading: str,
    body: str,
    draw: Callable[[float, float], float],
    diagram_width: float,
    extra: str = "",
    gap_pt: float = 22.0,
) -> float:
    """Numbered heading and text on the left, example on the right; the next y."""
    number, title = _unnumbered(heading)
    text_left = pen.left + pen.px(26)
    text_right = pen.right - diagram_width - pen.px(24)
    _badge(pen, pen.left + pen.px(9), y, number)
    pen.put(title, text_left, y, _HEAD_PT, bold=True)
    yb = pen.para(body, text_left, y + pen.px(17), text_right - text_left, _BODY_PT)
    yd = draw(pen.right - diagram_width, y - pen.px(10))
    if extra:
        # Under the example, in its column: the text column is the long one.
        yd = pen.para(extra, pen.right - diagram_width, yd + pen.px(16), diagram_width,
                      _SMALL_PT, grey=_GREY) - pen.px(10)
    return max(yb, yd + pen.px(10)) + pen.px(gap_pt)


def _rows_draw(pen: _Pen, lines: _Lines, entry: GuideTechnique) -> Tuple[Callable[[float, float], float], float]:
    layout = lines.layout(entry.clue, entry.length)
    left, top, right, bottom = diagram_box(layout)
    note_w = max((pen.width(row.note, _SMALL_PT) for row in entry.rows if row.note and len(row.note) < 16), default=0)
    width = (right - left) + (note_w + pen.px(8) if note_w else 0)

    def draw(x: float, y: float) -> float:
        cur = y
        for row in entry.rows:
            r, b = _diagram(pen, layout, _step(row.filled, row.crossed), x, cur)
            if row.note and len(row.note) < 16:
                pen.put(row.note, r + pen.px(8), (cur + b) / 2 + pen.px(3.5), _SMALL_PT, grey=_GREY)
            elif row.note:
                pen.para(row.note, x, b + pen.px(13), width, _SMALL_PT, grey=_GREY)
                b += pen.para_height(row.note, width, _SMALL_PT)
            cur = b + pen.px(3)
        return cur - pen.px(3)

    return draw, width


def _pipeline(pen: _Pen) -> Tuple[Callable[[float, float], float], float]:
    labels = [step.label.capitalize() for step in GUIDE_ASSUME_STEPS]
    box_w = max(pen.width(label, _SMALL_PT) for label in labels) + pen.px(12)
    gap = pen.px(10)
    width = len(labels) * box_w + (len(labels) - 1) * gap

    def draw(x: float, y: float) -> float:
        h = pen.px(30)
        for k, label in enumerate(labels):
            bx = x + k * (box_w + gap)
            pen.stream.fill_grey(_SHADE if k == 2 else 1.0)
            pen.stream.stroke_grey(_INK)
            pen.stream.stroke_width(0.8)
            pen.stream.rectangle(bx, y, bx + box_w, y + h, paint="both")
            pen.put(label, bx + box_w / 2, y + h / 2 + pen.px(3.6), _SMALL_PT, bold=True,
                     kind=PIPELINE_LABEL, align="centre")
            if k < len(labels) - 1:
                ax0, ax1, ay = bx + box_w + pen.px(1.5), bx + box_w + gap - pen.px(1.5), y + h / 2
                pen.stream.stroke_width(0.8)
                pen.stream.line(ax0, ay, ax1, ay)
                pen.stream.fill_grey(_INK)
                pen.stream.begin_path(ax1, ay)
                pen.stream.line_to(ax1 - pen.px(3.5), ay - pen.px(2.5))
                pen.stream.line_to(ax1 - pen.px(3.5), ay + pen.px(2.5))
                pen.stream.close_path()
                pen.stream.paint("fill")
        return y + h

    return draw, width


def _tier_rank(name: str) -> int:
    tier = tier_of_record(name)
    if tier is None or tier not in TIERS:
        raise ValueError(f"the legend names a tier the book does not have: {name!r}")
    return TIERS.index(tier) + 1


def _dots(pen: _Pen, x: float, cy: float, filled: int) -> float:
    d = pen.px(7)
    h = d / DIFFICULTY_DOT_RATIO
    w = d * (1 + DIFFICULTY_DOT_GAP_RATIO) * len(TIERS)
    dots = difficulty_dots(round(x), round(cy - h / 2), round(x + w), round(cy + h / 2),
                           filled=filled, total=len(TIERS))
    if dots is not None:
        draw_difficulty_dots(pen.stream, dots, grey=_INK)
    return x + w


def _page_two(pen: _Pen, lines: _Lines, top: float, bottom: float, play_page: Optional[int]) -> float:
    """Interior page 2: the basics. Returns the lowest pixel drawn."""
    px = pen.px
    y = top + px(40)
    pen.put(GUIDE_TITLE, pen.left, y, _TITLE_PT, bold=True, kind=TITLE)
    y = pen.para(GUIDE_INTRO, pen.left, y + px(24), pen.right - pen.left, _INTRO_PT, grey=_GREY)
    if play_page:
        y = pen.para(guide_play_sentence(play_page), pen.left, y + px(2), pen.right - pen.left, _BODY_PT)

    # The key strip: the three cell states.
    strip_top = y + px(4)
    strip_h = px(60)
    pen.box(pen.left, strip_top, pen.right, strip_top + strip_h, _SHADE)
    pen.put(GUIDE_CELL_STATES_HEADING.upper(), pen.left + px(14), strip_top + px(19), _SMALL_PT, grey=_GREY, bold=True)
    icon = guide_icon_layout(lines.spec)
    col = (pen.right - pen.left - px(28)) / len(GUIDE_CELL_STATES)
    for k, state in enumerate(GUIDE_CELL_STATES):
        bx = pen.left + px(14) + k * col
        step = _step({0} if state.filled else (), {0} if state.crossed else ())
        r, b = _diagram(pen, icon, step, bx, strip_top + px(27))
        mid = (strip_top + px(27) + b) / 2
        pen.put(state.heading, r + px(8), mid - px(1), 11.0, bold=True)
        pen.put(state.caption, r + px(8), mid + px(11), _SMALL_PT, grey=_GREY)
    y = strip_top + strip_h + px(34)

    # The basic rule: text left, the 3 2 1 line right with its caption under it.
    basic = lines.layout(GUIDE_BASIC_RULE_CLUE, GUIDE_BASIC_RULE_LENGTH)
    bl, bt, br, bb = diagram_box(basic)
    cap_w = max(br - bl, pen.width(GUIDE_BASIC_RULE_CAPTION, _SMALL_PT) / 2 + px(10))
    pen.put(GUIDE_BASIC_RULE_HEADING, pen.left, y, _SECTION_PT, bold=True)
    text_right = pen.right - cap_w - px(24)
    yb = pen.para(GUIDE_BASIC_RULE_TEXT, pen.left, y + px(20), text_right - pen.left, _BODY_PT)
    _, db = _diagram(pen, basic, _step(GUIDE_BASIC_RULE_FILLED, GUIDE_BASIC_RULE_CROSSED),
                     pen.right - cap_w, y + px(6))
    yc = pen.para(GUIDE_BASIC_RULE_CAPTION, pen.right - cap_w, db + px(14), cap_w, _SMALL_PT, grey=_GREY)
    y = max(yb, yc) + px(22)

    pen.put(GUIDE_CERTAINTY_HEADING, pen.left, y, _SECTION_PT, bold=True)
    pen.rule(y + px(8))
    y += px(36)
    for entry in GUIDE_TECHNIQUES_1:
        draw, width = _rows_draw(pen, lines, entry)
        y = _technique(pen, y, entry.heading, entry.caption, draw, width)

    # The tip callout, anchored to the foot of the body.
    callout_h = px(14) + pen.para_height(GUIDE_SWITCHING_TEXT, pen.right - pen.left - px(20), _BODY_PT)
    ct = max(y, bottom - callout_h - px(16))
    pen.box(pen.left, ct - px(12), pen.left + px(3), ct + callout_h, _INK)
    pen.put(GUIDE_SWITCHING_HEADING, pen.left + px(14), ct + px(2), 11.5, bold=True)
    end = pen.para(GUIDE_SWITCHING_TEXT, pen.left + px(14), ct + px(19), pen.right - pen.left - px(20), _BODY_PT)
    return max(ct + callout_h, end)


def _page_three(pen: _Pen, lines: _Lines, top: float, bottom: float) -> float:
    """Interior page 3: the harder techniques, the worked example, difficulty."""
    px = pen.px
    y = top + px(36)
    pen.put(GUIDE2_TITLE, pen.left, y, _TITLE2_PT, bold=True, kind=TITLE)
    y = pen.para(GUIDE2_INTRO, pen.left, y + px(22), pen.right - pen.left, 11.5, grey=_GREY) + px(8)

    for entry in GUIDE_TECHNIQUES_2:
        draw, width = _rows_draw(pen, lines, entry)
        y = _technique(pen, y, entry.heading, entry.caption, draw, width, gap_pt=14.0)
    draw, width = _pipeline(pen)
    y = _technique(pen, y, GUIDE_ASSUME_HEADING, GUIDE_ASSUME_TEXT, draw, width,
                   extra=GUIDE_ASSUME_CLOSING, gap_pt=14.0)

    # The worked example, 2 x 2.
    pen.put(GUIDE_EXAMPLE_HEADING.rstrip("."), pen.left, y, 14.0, bold=True)
    pen.rule(y + px(8))
    y += px(30)
    worked = lines.layout(WORKED_EXAMPLE_CLUE, WORKED_EXAMPLE_LENGTH)
    col = (pen.right - pen.left) / 2
    row_bottom = y_end = y
    for k, step in enumerate(WORKED_EXAMPLE_STEPS):
        bx = pen.left + (k % 2) * col
        by = y if k < 2 else row_bottom + px(16)
        number, _, label = step.label.partition(". ")
        note = step.caption.partition(". ")[2]
        if ": " in note:
            note = note.partition(": ")[2]
        note = note[0].upper() + note[1:]
        pen.put(f"{number}  {label}", bx, by, 11.0, bold=True)
        _, db = _diagram(pen, worked, step, bx, by + px(8))
        end = pen.para(note, bx, db + px(14), col - px(24), _SMALL_PT, grey=_GREY)
        if k < 2:
            row_bottom = max(row_bottom, end)
        else:
            y_end = end
    y = max(row_bottom, y_end)

    # The difficulty box, anchored to the foot of the body.
    names = [label.name for label in GUIDE_DIFFICULTY_LABELS]
    inner = pen.right - pen.left - px(28)
    box_h = px(44) + pen.para_height(GUIDE_DIFFICULTY_LINE, inner, _BODY_PT)
    bt = max(y + px(4), bottom - box_h)
    pen.box(pen.left, bt, pen.right, bt + box_h, _SHADE)
    pen.put(GUIDE_DIFFICULTY_HEADING, pen.left + px(14), bt + px(22), 13.0, bold=True)
    x = pen.left + px(14) + pen.width(GUIDE_DIFFICULTY_HEADING, 13.0) + px(28)
    for name in names:
        end = _dots(pen, x, bt + px(18), _tier_rank(name))
        x = pen.put(name, end + px(6), bt + px(22), _SMALL_PT, bold=True, kind=LEGEND_NAME) + px(26)
    end = pen.para(GUIDE_DIFFICULTY_LINE, pen.left + px(14), bt + px(42), inner, _BODY_PT)
    return max(bt + box_h, end)


#: The mockup's example cell (17 pt), used where its clue digits still hold
#: CON-020's floor; otherwise the generator's own example cell.
_MOCK_CELL_MM = 6.0


def _example_spec(spec: PageSpec, dpi: int) -> PageSpec:
    from dataclasses import replace

    from nonogram.admin.book_guide_vector import _example_lines

    standard = example_cell_spec(spec, dpi)
    if not isinstance(standard.cell_cap, float) or standard.cell_cap <= _MOCK_CELL_MM:
        return standard
    smaller = replace(spec, cell_cap=_MOCK_CELL_MM)
    floor_px = FOLIO_PT * dpi / 72.0
    if all(
        example_line_layout(smaller, c, n).clue_font_size >= floor_px for c, n in _example_lines()
    ):
        return smaller
    return standard


def spread_page(
    spec: PageSpec,
    dpi: int,
    page_number: int,
    *,
    play_page: Optional[int] = None,
    metrics: Optional[FontMetrics] = None,
    puzzle_count: int = 0,
    easy_count: int = 0,
    medium_count: int = 0,
    hard_count: int = 0,
) -> GuidePage:
    """One page of the How to Solve spread as the approved mockup sets it.

    The mockup is a US Letter design. On a sheet it does not fit (its body runs
    into the footer rule, or the text block is too narrow for its two columns)
    the page is CARD-229's own, :func:`~nonogram.admin.book_guide_vector.guide_page`,
    whose ladder of forms is built for small trims.
    """
    page = _mockup_page(spec, dpi, page_number, play_page=play_page, metrics=metrics)
    if page is not None:
        return page
    return guide_vector.guide_page(
        spec,
        dpi,
        page_number,
        puzzle_count=puzzle_count,
        easy_count=easy_count,
        medium_count=medium_count,
        hard_count=hard_count,
        play_page=play_page,
        metrics=metrics,
    )


#: Below this text-block width (points) the two columns cannot be set.
_MIN_WIDTH_PT = 400.0


def _mockup_page(
    spec: PageSpec,
    dpi: int,
    page_number: int,
    *,
    play_page: Optional[int],
    metrics: Optional[FontMetrics],
) -> Optional[GuidePage]:
    from nonogram.export.layout import guide_spread_layout, interior_frame

    face = metrics or interior_face_metrics()
    page_one = (page_number - guide_vector.TITLE_PAGE_COUNT) % 2 == 1
    frame = interior_frame(spec)
    left, right = frame.header_rule.left, frame.header_rule.right
    points_px = dpi / 72.0
    if right - left < _MIN_WIDTH_PT * points_px:
        return None
    shrink = min(1.0, (right - left) / (_MOCK_WIDTH_PT * points_px))
    trim = page_frame(spec)
    stream = ContentStream(width_px=trim.width, height_px=trim.height, dpi=dpi)
    pen = _Pen(stream, face, points_px * shrink, dpi, left, right)
    lines = _Lines(_example_spec(spec, dpi))

    # The band: the puzzle pages' own, carrying the running head.
    band = guide_spread_layout(spec, example_width=1, text_min=1).band
    draw_band(stream, band, RUNNING_HEAD, right - left, face)
    pen.faces.append(DrawnFace(TITLE, RUNNING_HEAD, stream.to_points(band_type_size(RUNNING_HEAD, band, right - left, face))))

    top = frame.header_rule.y
    bottom = frame.footer_rule.y - pen.px(10)
    if page_one:
        reached = _page_two(pen, lines, top, bottom, play_page)
    else:
        reached = _page_three(pen, lines, top, bottom)

    if reached > frame.footer_rule.y:
        return None

    folio_px = type_px(FOLIO_PT, dpi)
    written = len(stream.operators)
    draw_sheet_furniture(
        stream,
        SheetFurniture(
            frame=frame,
            folio=str(page_number),
            folio_size_px=folio_px,
            content_bottom=reached,
            right_hand=page_is_right_hand(page_number),
        ),
        face,
    )
    if any(f"({page_number}) Tj" in op for op in stream.operators[written:]):
        pen.faces.append(DrawnFace(FOLIO, str(page_number), stream.to_points(folio_px)))
    return GuidePage(
        page_number=page_number,
        stream=stream,
        faces=tuple(pen.faces),
        fallback_level=0,
        form=_FORMS[0],
        content_bottom=reached,
    )
