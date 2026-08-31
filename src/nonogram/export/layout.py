"""COMP-007 — the shared print geometry behind every rendered puzzle (FR-011).

Three renderers draw the same picture: the PNG raster (CARD-012), the SVG vector
(CARD-012) and CARD-014's PDF, which CON-006 makes a second sink on the PNG
raster path rather than a new dependency. "The same picture" has to mean the
same *numbers*, so the numbers live here, once, and the renderers only choose
how to stroke them.

The one thing not all three draw is a header. It is measured here anyway
(:func:`header_band`) — a page's geometry is this module's subject whoever ends
up drawing it — but as a separate measurement laid *above* a computed
:class:`Layout` rather than as a parameter of :func:`compute_layout`, so that
a format without a header carries none of it in its *coordinates*: the PNG and
the PDF's puzzle page are the same pixels, offset by the band's height. The one
thing every format does share is the band's claim on the *sheet*: the cell is
sized so that drawing **plus** band fits A4 (NFR-005 defines page fit that
way), because a cell chosen without the band is a cell the PDF cannot print.
See :func:`header_band` and :func:`_fit_cell`.

A pure function of the clues, and of nothing else
-------------------------------------------------
:func:`compute_layout` takes the two clue sets and returns plain ints, floats
and tuples. No Pillow type, no SVG string and no filesystem appears in its
signature, which is what lets a third renderer consume it without inheriting
the second one's library. The grid's size is not a separate parameter because
it is not separate information: ``len(row_clues)`` is the number of rows and
``len(column_clues)`` the number of columns (INV-001 makes the clue sets the
encoding of the grid, so a size argument could only ever agree with them or be
a bug). Everything else — page size, resolution, the clamp on the cell — is a
module constant, so the same clues always produce the same geometry.

What the geometry is
--------------------
A standard printed nonogram: a square-celled grid, a left gutter holding the
row clues right-aligned against the grid's left edge, a top gutter holding the
column clues bottom-aligned against its top edge, and an empty corner block
where the two gutters meet. The gutters are exactly as deep as the longest
clue in their direction, so a puzzle whose rows never need more than three
numbers does not carry a gutter sized for twenty-five.

Grid lines run the *full* extent of their axis, gutter included — the vertical
line between column 4 and column 5 continues up through the column-clue gutter
— because that is what makes a clue number readable as belonging to its line.
Every fifth line, and both outer borders, is stroked heavier
(:attr:`Layout.thick_rule` against :attr:`Layout.thin_rule`); counting to
twelve along a thirty-cell row is the thing a solver actually does with a ruler
otherwise, and the every-5th rule is the convention that makes it unnecessary.

Why the sizes are what they are (the A4 / 300 DPI target)
---------------------------------------------------------
The card asks for output "legible when printed at A4". That is a physical
statement, so the geometry is computed in physical units and only then turned
into device pixels at :data:`DPI` = 300 — the resolution at which a printed
line looks like a line rather than a staircase, and the number both renderers
stamp onto their output (the PNG as a ``dpi`` tag, the SVG as a physical
``width``/``height`` in inches over a pixel ``viewBox``) so that a printer
reproduces the intended size instead of guessing.

:func:`compute_layout` then sizes the cell as NFR-005 defines it — the
comfortable size for a grid that big, held down to whatever the sheet can
actually take::

    cell = min(comfort_cap(max(columns, rows)), page_fit)

* the *comfort cap* (:func:`comfort_cap_mm`) is how big a cell wants to be at
  that grid size: 9.0 mm at 10 cells a side, declining to 6.5 mm at 30
  (CON-011's largest supported grid), linearly interpolated between NFR-005's
  chosen points and flat outside them. It is a function of the **grid's**
  longer side and of nothing else — a gutter makes a drawing wider, not a cell
  harder to mark. The declining curve replaces a single flat 6.5 mm cap, under
  which a 10x10 and a 25x25 printed *identically* at 6.52 mm and a 10x10 came
  out about 30% smaller than it was meant to be.
* *page fit* is the largest cell whose whole page — grid, plus both clue
  gutters, plus the :data:`HEADER_BAND_MM` strip a titled page lays above the
  drawing — still fits the printable area of A4. The band is counted for all
  three formats, not only the PDF that draws it: it costs a wide drawing
  nothing (the band eats height, and the width term binds unless a drawing is
  about 1.40x taller than it is wide), and for the tall drawings where the
  height term does bind, a cell chosen without it is a cell the PDF cannot put
  on a sheet. That is not hypothetical — a 10x25 whose rows alternate full and
  empty is an ordinary uniquely-solvable puzzle, and sized on the drawing alone
  it overruns A4 by 34 device pixels once the band is added.
* the cap is a **ceiling, never a floor**: where the two disagree, page fit
  wins. From about 20 cells a side up, the gutter makes page fit the smaller
  term every time — at 45% density a 30x30 draws 40 cells across, which is
  260 mm of paper at 6.5 mm cells against the 186 mm A4 actually prints. A cap
  honoured where the page allows it is a real gain at the small sizes a person
  prints most; a cap treated as a target would be a promise the format cannot
  keep.
* the *floor* (:data:`MIN_CELL_MM`) is the honest limit of the format, and is
  deliberately untouched by the above. No supported puzzle reaches it: the
  worst 30x30 draws 45 cells across and still gets a ~4 mm cell, and page fit
  would have to fall below 2 mm — over ninety cells across — before the floor
  bites at all. It is the backstop for that case, and it answers it by keeping
  2 mm cells and letting the image grow past A4 rather than shrinking past the
  point where a pencil mark is meaningless: a user printing a drawing that
  large is scaling it down or printing it on A3 either way, and a silently
  unreadable page would be the worse answer.

Layering (ADR-0007): a capability submodule — stdlib only, no siblings, no
orchestrator, and (guardrail G-3) no notion whatsoever of whether the puzzle
it is measuring may be exported.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CELL_COMFORT_MM",
    "DPI",
    "HEADER_BAND_MM",
    "HEADER_FONT_MM",
    "MAX_CELL_MM",
    "MIN_CELL_MM",
    "MAJOR_RULE_EVERY",
    "PAGE_HEIGHT_MM",
    "PAGE_MARGIN_MM",
    "PAGE_WIDTH_MM",
    "ClueEntry",
    "GridLine",
    "HeaderBand",
    "Layout",
    "comfort_cap_mm",
    "compute_layout",
    "header_band",
]

#: Output resolution in dots per inch. 300 is the conventional print target:
#: at 150 a thin rule and a small clue digit both start to alias, and at 600
#: the 30x30 page is four times the bytes for detail no home printer resolves.
DPI = 300

#: A4, portrait, in millimetres (ISO 216).
PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0

#: Blank border kept on every side, in millimetres — comfortably inside the
#: unprintable margin of a typical inkjet, and enough to hold the sheet by.
PAGE_MARGIN_MM = 12.0

#: NFR-005's chosen comfort values: how big a printed cell should be, in
#: millimetres, for a grid whose *larger* dimension is that many cells. Five
#: decided points, read as a piecewise-linear curve by :func:`comfort_cap_mm`
#: — the points were decided, the line between them is interpolation. Kept as
#: ``(cells, mm)`` pairs in ascending order of ``cells``; the curve must stay
#: non-increasing in ``cells`` (EC-008), which is the whole content of "a
#: bigger grid gets a smaller cell".
CELL_COMFORT_MM: tuple[tuple[int, float], ...] = (
    (10, 9.0),
    (15, 8.0),
    (20, 7.5),
    (25, 7.0),
    (30, 6.5),
)

#: The comfort value for the largest supported grid (CON-011: 30 cells a
#: side), in millimetres. This is no longer *the* cap — the cap is
#: :func:`comfort_cap_mm`, one value per grid size — only the bottom end of
#: its curve, kept under a name because it is the one point of that curve a
#: reader has reason to reach for directly.
MAX_CELL_MM = CELL_COMFORT_MM[-1][1]

#: The cell-size floor, in millimetres: smaller than this is not a puzzle any
#: more, it is a grey square. Unlike the comfort cap above, the floor wins
#: over page fit rather than yielding to it — see the module docstring for why
#: an oversized image beats a silently unreadable page.
#:
#: **A backstop for out-of-range drawings only, and knowingly so.** Measured
#: over all 441 extents CON-011 supports at three gutter depths: the smallest
#: cell any of them gets is 48 px / 4.06 mm (a 30x10 checkerboard, 45 cells
#: across), against this floor's 24 px. Page fit has to fall under 24 px for
#: the floor to engage at all, which needs 92 cells across or 129 down —
#: three times CON-011's widest grid plus its deepest gutter. So the guarantee
#: "the floor still beats page fit" (guardrail G-3) is certified against a
#: synthetic drawing (``test_the_largest_drawing_keeps_a_markable_cell``'s
#: 120x60 clue set) rather than a constructible puzzle, because the domain can
#: no longer construct one. That is recorded rather than hidden: the clamp is
#: live code for a case only a future widening of CON-011, or a future format
#: with a much deeper gutter, would reach — and a later reader tempted to
#: delete it as dead should reach that conclusion on purpose.
MIN_CELL_MM = 2.0

#: Every Nth grid line is stroked heavy — the standard nonogram counting aid.
MAJOR_RULE_EVERY = 5

#: The strip CARD-014's PDF adds *above* a rendered page for its
#: ``<name> — <tier>`` header, and the type size the header is set in, both in
#: millimetres. 5 mm is roughly 14 pt: larger than any clue digit at any cell
#: size, so the title reads as a title, and the 12 mm band leaves a clear
#: half-band of white above and below it. See :func:`header_band` for why the
#: band is measured here but added by the renderer.
HEADER_BAND_MM = 12.0
HEADER_FONT_MM = 5.0

#: Clue digits, as a fraction of the cell they sit in. 0.62 leaves a visible
#: gap on both sides of a two-digit clue (the widest that can occur: the
#: longest possible run is 30, CON-011) without the numbers touching the rules.
_CLUE_FONT_RATIO = 0.62

#: Thin and heavy rule widths, as a fraction of the cell. The thin rule is
#: pinned to the cell rather than fixed in pixels so that the drawing keeps
#: its proportions at every size the clamp above can produce.
_THIN_RULE_RATIO = 1 / 30

#: A run-length clue for one line, and a full set of them — the same boundary
#: types ``nonogram.clues`` produces and ``ExportPayload`` carries (ADR-0012).
type LineClue = tuple[int, ...]
type ClueSet = tuple[LineClue, ...]


@dataclass(frozen=True, slots=True)
class GridLine:
    """One ruled line of the grid, positioned along its own axis.

    Attributes:
        index: Which boundary this is, ``0`` for the top/left edge through
            ``rows``/``columns`` for the bottom/right one.
        position: The line's coordinate on its axis, in device pixels — ``x``
            for a vertical line, ``y`` for a horizontal one.
        start: Where the line begins on the *other* axis, in device pixels.
        end: Where it ends.
        width: How heavy to stroke it — :attr:`Layout.thin_rule` or
            :attr:`Layout.thick_rule`.
        major: Whether this is one of the every-5th (or outer-border) rules.
            Carried separately from :attr:`width` because it is the *reason*
            for the width, and a renderer may want to say so (a different ink,
            a different SVG class) without re-deriving the modulo.
    """

    index: int
    position: int
    start: int
    end: int
    width: int
    major: bool


@dataclass(frozen=True, slots=True)
class ClueEntry:
    """One clue number, and the point it is centred on.

    Attributes:
        value: The run length, exactly as ``nonogram.clues`` encoded it — the
            ``0`` of an empty line included (AC-013), which prints as a real
            ``0`` because that is what the clue set says.
        line: Which row or column the clue belongs to, 0-based.
        depth: How far into the gutter the entry sits, 0-based from the outer
            edge. Right-aligned for rows and bottom-aligned for columns, so
            the last entry of every clue always abuts the grid.
        center_x: The horizontal centre of the entry's box, in device pixels.
        center_y: The vertical centre. Both renderers draw text centred on
            this point, which is the one placement rule that does not depend
            on how a given library measures a glyph.
    """

    value: int
    line: int
    depth: int
    center_x: int
    center_y: int


@dataclass(frozen=True, slots=True)
class Layout:
    """The complete geometry of one rendered puzzle, in device pixels.

    The origin is the image's top-left corner and ``y`` grows downward, which
    is both Pillow's convention and SVG's, so neither renderer has to flip
    anything.

    Attributes:
        rows: Grid height in cells.
        columns: Grid width in cells.
        cell: The side of one square cell.
        margin: The blank border on all four sides.
        row_gutter_cells: How many clue boxes deep the left gutter is — the
            length of the longest row clue.
        column_gutter_cells: The same for the top gutter.
        width: Total image width.
        height: Total image height.
        grid_left: ``x`` of the grid's left edge, i.e. the right edge of the
            row-clue gutter.
        grid_top: ``y`` of the grid's top edge.
        grid_right: ``x`` of the grid's right edge.
        grid_bottom: ``y`` of the grid's bottom edge.
        thin_rule: Stroke width of an ordinary grid line.
        thick_rule: Stroke width of an every-5th or outer-border line.
        clue_font_size: The size to draw a clue number at.
        vertical_lines: Column boundaries, left to right — ``columns + 1`` of
            them, each spanning the full height inside the margins.
        horizontal_lines: Row boundaries, top to bottom — ``rows + 1``, each
            spanning the full width inside the margins.
        row_clues: The left gutter's numbers, already placed.
        column_clues: The top gutter's numbers, already placed.
        dpi: The resolution :attr:`width` and :attr:`height` are expressed at,
            so a renderer can tag its output with the physical size it means.
    """

    rows: int
    columns: int
    cell: int
    margin: int
    row_gutter_cells: int
    column_gutter_cells: int
    width: int
    height: int
    grid_left: int
    grid_top: int
    grid_right: int
    grid_bottom: int
    thin_rule: int
    thick_rule: int
    clue_font_size: int
    vertical_lines: tuple[GridLine, ...]
    horizontal_lines: tuple[GridLine, ...]
    row_clues: tuple[ClueEntry, ...]
    column_clues: tuple[ClueEntry, ...]
    dpi: int = DPI

    @property
    def clue_entries(self) -> tuple[ClueEntry, ...]:
        """Every placed clue number, rows first then columns."""
        return self.row_clues + self.column_clues

    @property
    def grid_lines(self) -> tuple[GridLine, ...]:
        """Every ruled line, verticals first then horizontals."""
        return self.vertical_lines + self.horizontal_lines

    @property
    def width_inches(self) -> float:
        """:attr:`width` as a physical measurement at :attr:`dpi`."""
        return self.width / self.dpi

    @property
    def height_inches(self) -> float:
        """:attr:`height` as a physical measurement at :attr:`dpi`."""
        return self.height / self.dpi


@dataclass(frozen=True, slots=True)
class HeaderBand:
    """The strip a titled page carries above the drawing (FR-016).

    Attributes:
        height: How tall the band is, in device pixels — what the page grows
            by, and how far down the puzzle drawing moves.
        center_x: The horizontal centre of the band.
        center_y: The vertical centre, measured from the *page's* top edge
            (which is the band's own top edge, the band being the first thing
            on the page). A renderer centres the title on ``(center_x,
            center_y)``, the same ``anchor="mm"`` placement rule the clue
            numbers use.
        font_size: The size to set the title in.
    """

    height: int
    center_x: int
    center_y: int
    font_size: int


def header_band(layout: Layout) -> HeaderBand:
    """Measure the title strip for a page drawn to ``layout`` (FR-016).

    Why this is a second function and not a parameter of
    :func:`compute_layout`
    ----------------------------------------------------------------------
    Only the PDF carries a header: FR-011's PNG and SVG are the bare printable
    puzzle, and CON-006 makes the PDF a second *sink* on that same raster
    rather than a second drawing. Folding a header into
    :func:`compute_layout` would move ``grid_top`` — and with it every clue
    centre and every ruled line — for all three renderers, so a format that
    shows no header would still be paying for one in its coordinates. Measured
    separately and added on top, the band is strictly additive: the PNG and the
    PDF's puzzle page are the same pixels, offset by :attr:`HeaderBand.height`.

    What *is* shared is the band's claim on the sheet. :func:`_fit_cell`
    reserves :data:`HEADER_BAND_MM` out of the printable height for every
    format, because all three read one :func:`compute_layout` and a cell chosen
    without the band is a cell the PDF cannot fit on A4 (NFR-005 defines page
    fit over drawing *plus* band for exactly this reason). So the band is free
    in a headerless format's coordinates and not quite free in its cell — and
    only where the height term binds at all, which needs a drawing about 1.40x
    taller than it is wide.

    Measured cost, over CON-011's 441 extents at each of the **four** clue
    patterns :mod:`tests.property.test_layout_cell_size` sweeps — naming them
    rather than counting them, because two different three-pattern subsets of
    this corpus both have 1323 cases and quoting a bare denominator has already
    caused one round of confusion:

    ===================  ================
    pattern              cells moved /441
    ===================  ================
    ``_random_grid``                    3
    ``_checkerboard``                  58
    ``_sparse``                         0
    ``_alternating_rows``             111
    ===================  ================

    **172 of 1764 (9.8%)** over the whole corpus, by at most 0.2540mm — exactly
    three device pixels at :data:`DPI`. Almost all of it is the tall
    alternating-rows regime, where the height term binds most often; ``_sparse``
    never moves at all.

    The type size is physical (:data:`HEADER_FONT_MM` at :data:`DPI`) and not a
    fraction of the cell, unlike :attr:`Layout.clue_font_size`. A clue digit has
    to fit inside its cell, so it must scale with it; a title has a whole page
    width to sit in and only has to be legible, and pinning it to the cell would
    set a 30x30 puzzle's header in the same 3 mm type as its clues.

    Args:
        layout: The geometry of the page the band goes above — read only for
            its width, so the title is centred over the drawing.

    Returns:
        The :class:`HeaderBand` the renderer draws into.
    """
    height = _mm_to_px(HEADER_BAND_MM)
    return HeaderBand(
        height=height,
        center_x=layout.width // 2,
        center_y=height // 2,
        font_size=max(1, _mm_to_px(HEADER_FONT_MM)),
    )


def _mm_to_px(millimetres: float) -> int:
    """Millimetres at :data:`DPI`, rounded to a whole device pixel."""
    return round(millimetres / 25.4 * DPI)


def _gutter_depth(clue_set: ClueSet) -> int:
    """How many clue boxes deep a gutter has to be for ``clue_set``.

    The longest clue in the set, and never less than one: an all-empty line
    still carries the ``(0,)`` marker, so every clue occupies at least one box
    and a gutter of zero would leave a puzzle's clues nowhere to go.
    """
    return max((len(clue) for clue in clue_set), default=1)


def comfort_cap_mm(larger_dimension: int) -> float:
    """How big a printed cell may be for a grid this many cells on its longer
    side, in millimetres (NFR-005).

    :data:`CELL_COMFORT_MM`'s five decided points, linearly interpolated
    between neighbours and held flat outside the range: a grid smaller than
    the first point gets the first point's value and one larger than the last
    gets the last's, because extrapolating a curve that was only ever decided
    over 10..30 would be inventing numbers rather than reading them. CON-011
    keeps every real puzzle inside that range anyway; the flat ends exist so
    that this is a total function on any int a caller can hold.

    Args:
        larger_dimension: ``max(columns, rows)`` of the **grid** — not of the
            drawing. The clue gutter widens the page, not the cell.

    Returns:
        The cell edge the cap allows, in millimetres. Non-increasing in
        ``larger_dimension`` (EC-008).
    """
    if larger_dimension <= CELL_COMFORT_MM[0][0]:
        return CELL_COMFORT_MM[0][1]
    for (left_cells, left_mm), (right_cells, right_mm) in zip(
        CELL_COMFORT_MM, CELL_COMFORT_MM[1:], strict=False
    ):
        if larger_dimension <= right_cells:
            travelled = (larger_dimension - left_cells) / (right_cells - left_cells)
            return left_mm + travelled * (right_mm - left_mm)
    return CELL_COMFORT_MM[-1][1]


def _fit_cell(
    total_columns: int,
    total_rows: int,
    *,
    larger_dimension: int,
    reserved_height_mm: float,
) -> int:
    """The cell size in device pixels: ``min(comfort cap, page fit)`` (NFR-005).

    Two measurements of the same cell, and they are functions of different
    things — which is why this takes both the drawing's totals and the grid's
    own longer side:

    * *page fit* is the largest cell whose whole page still fits the printable
      area of an A4 sheet. Gutters included, which is why
      ``total_columns``/``total_rows`` are totals and not the grid's own
      dimensions; and ``reserved_height_mm`` included too, which is the strip
      a renderer lays above the drawing without :func:`compute_layout` knowing
      any of its geometry.
    * the *comfort cap* is what :func:`comfort_cap_mm` assigns to
      ``larger_dimension``, the longer side of the grid alone.

    Why the reserved strip is a parameter here and a constant at the call site
    ----------------------------------------------------------------------
    The band is the PDF's, and only the PDF draws it — but the *cell* it
    implies is shared, because all three renderers read one
    :func:`compute_layout` and the PDF must be able to print the result. Taking
    the reservation as an argument rather than reading :data:`HEADER_BAND_MM`
    off the module keeps that a decision of the caller, visible at the one line
    that makes it, instead of a global this function silently consults. A
    caller that genuinely draws no band can pass ``0.0``; today none does, and
    the cost of the shared reservation is confined to drawings tall enough for
    the height term to bind at all (roughly 1.40x taller than wide, since
    the band's reservation leaves 261mm of height against 186mm of width).

    The cap is a ceiling and page fit wins whenever it is the smaller of the
    two — for anything from about 20 cells a side up, that is always (see the
    module docstring). It is converted to whole pixels by truncation rather
    than rounding, so "the printed cell never exceeds the cap" (EC-008) holds
    exactly in millimetres instead of to within half a device pixel.

    :data:`MIN_CELL_MM` is the one clamp still allowed to win *over* page fit,
    exactly as before: below it the page is allowed to outgrow A4 rather than
    shrink past the point where a pencil mark is meaningless.
    """
    printable_width = _mm_to_px(PAGE_WIDTH_MM - 2 * PAGE_MARGIN_MM)
    printable_height = _mm_to_px(PAGE_HEIGHT_MM - 2 * PAGE_MARGIN_MM) - _mm_to_px(
        reserved_height_mm
    )
    page_fit = min(
        printable_width // max(total_columns, 1),
        max(printable_height, 0) // max(total_rows, 1),
    )
    cap = int(comfort_cap_mm(larger_dimension) / 25.4 * DPI)
    return max(_mm_to_px(MIN_CELL_MM), min(cap, page_fit))


def _rule_widths(cell: int) -> tuple[int, int]:
    """The thin and heavy stroke widths for a given cell size.

    Kept proportional to the cell so the drawing looks the same at every size
    the clamp can produce, and the heavy rule is exactly twice the thin one —
    enough to read as "heavier" across a page without the every-5th lines
    reading as a second, coarser grid.
    """
    thin = max(1, round(cell * _THIN_RULE_RATIO))
    return thin, thin * 2


def _is_major(index: int, last: int) -> bool:
    """Is boundary ``index`` one of the heavy rules?

    Every :data:`MAJOR_RULE_EVERY`-th boundary counting from the top/left, plus
    the far edge — a 12-wide grid gets heavy rules at 0, 5, 10 and 12, so the
    frame is closed even when the width is not a multiple of five.
    """
    return index % MAJOR_RULE_EVERY == 0 or index == last


def _axis_lines(
    count: int, *, origin: int, cell: int, start: int, end: int, thin: int, thick: int
) -> tuple[GridLine, ...]:
    """The ``count + 1`` boundaries of one axis, from ``origin``."""
    return tuple(
        GridLine(
            index=index,
            position=origin + index * cell,
            start=start,
            end=end,
            width=thick if _is_major(index, count) else thin,
            major=_is_major(index, count),
        )
        for index in range(count + 1)
    )


def _place_row_clues(
    clue_set: ClueSet, *, depth: int, cell: int, margin: int, grid_top: int
) -> tuple[ClueEntry, ...]:
    """Lay the row clues out in the left gutter, right-aligned.

    Right-aligned rather than left-aligned so that the *last* number of every
    clue — the run that ends at the grid's edge — sits in the same column for
    every row, which is how a printed nonogram is read.

    Centres are ``origin + index * cell + cell // 2``: integer arithmetic all
    the way, so a clue box's centre is exactly one half-cell from its own
    boundary at every cell size, and never a rounding step away from where the
    matching grid line was placed.
    """
    half = cell // 2
    return tuple(
        ClueEntry(
            value=value,
            line=row,
            depth=depth - len(clue) + offset,
            center_x=margin + (depth - len(clue) + offset) * cell + half,
            center_y=grid_top + row * cell + half,
        )
        for row, clue in enumerate(clue_set)
        for offset, value in enumerate(clue)
    )


def _place_column_clues(
    clue_set: ClueSet, *, depth: int, cell: int, margin: int, grid_left: int
) -> tuple[ClueEntry, ...]:
    """Lay the column clues out in the top gutter, bottom-aligned.

    The transpose of :func:`_place_row_clues`, and bottom-aligned for the same
    reason: the last number of each clue abuts the grid.
    """
    half = cell // 2
    return tuple(
        ClueEntry(
            value=value,
            line=column,
            depth=depth - len(clue) + offset,
            center_x=grid_left + column * cell + half,
            center_y=margin + (depth - len(clue) + offset) * cell + half,
        )
        for column, clue in enumerate(clue_set)
        for offset, value in enumerate(clue)
    )


def compute_layout(row_clues: ClueSet, column_clues: ClueSet) -> Layout:
    """Measure the printed page for one puzzle's clues.

    Pure and total: same clues in, same numbers out, no I/O, no library types.
    The grid's dimensions come from the clue sets themselves (see the module
    docstring), and the blank grid is the only thing being measured — the
    solution never reaches this function, which is the structural reason the
    renderers cannot leak it onto a page they are only given coordinates for.

    Args:
        row_clues: Row clues, top to bottom, in the ADR-0012 boundary type.
        column_clues: Column clues, left to right.

    Returns:
        The :class:`Layout` both renderers draw from.

    Raises:
        ValueError: one clue set is empty while the other is not — a grid with
            rows but no columns (or the reverse) cannot be drawn, and is a
            pipeline bug rather than a puzzle.
    """
    rows, columns = len(row_clues), len(column_clues)
    if bool(rows) != bool(columns):
        raise ValueError(
            f"clue sets disagree about the grid: {rows} row clue(s) but "
            f"{columns} column clue(s); a grid has either both or neither"
        )

    row_gutter_cells = _gutter_depth(row_clues)
    column_gutter_cells = _gutter_depth(column_clues)

    # The two terms of NFR-005 read different things off the same puzzle: page
    # fit measures the page (grid + gutters + the header band a titled sheet
    # carries above them), the comfort cap measures the grid. Both come from
    # the clue sets, so compute_layout still needs nothing but them (G-4) —
    # HEADER_BAND_MM is a constant of this module, not an argument a caller
    # supplies, so reserving it costs the signature nothing.
    cell = _fit_cell(
        row_gutter_cells + columns,
        column_gutter_cells + rows,
        larger_dimension=max(columns, rows),
        reserved_height_mm=HEADER_BAND_MM,
    )
    margin = _mm_to_px(PAGE_MARGIN_MM)
    thin, thick = _rule_widths(cell)

    grid_left = margin + row_gutter_cells * cell
    grid_top = margin + column_gutter_cells * cell
    grid_right = grid_left + columns * cell
    grid_bottom = grid_top + rows * cell

    return Layout(
        rows=rows,
        columns=columns,
        cell=cell,
        margin=margin,
        row_gutter_cells=row_gutter_cells,
        column_gutter_cells=column_gutter_cells,
        width=grid_right + margin,
        height=grid_bottom + margin,
        grid_left=grid_left,
        grid_top=grid_top,
        grid_right=grid_right,
        grid_bottom=grid_bottom,
        thin_rule=thin,
        thick_rule=thick,
        clue_font_size=max(1, round(cell * _CLUE_FONT_RATIO)),
        # Both axes span the gutters as well as the grid: a vertical line
        # continues up through the column-clue gutter so its clue reads as
        # belonging to that column, and vice versa.
        vertical_lines=_axis_lines(
            columns,
            origin=grid_left,
            cell=cell,
            start=margin,
            end=grid_bottom,
            thin=thin,
            thick=thick,
        ),
        horizontal_lines=_axis_lines(
            rows,
            origin=grid_top,
            cell=cell,
            start=margin,
            end=grid_right,
            thin=thin,
            thick=thick,
        ),
        row_clues=_place_row_clues(
            row_clues,
            depth=row_gutter_cells,
            cell=cell,
            margin=margin,
            grid_top=grid_top,
        ),
        column_clues=_place_column_clues(
            column_clues,
            depth=column_gutter_cells,
            cell=cell,
            margin=margin,
            grid_left=grid_left,
        ),
    )
