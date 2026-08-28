"""COMP-007 — the shared print geometry behind every rendered puzzle (FR-011).

Three renderers eventually draw the same picture: the PNG raster (this card),
the SVG vector (this card) and CARD-014's PDF, which CON-006 makes a second
sink on the PNG raster path rather than a new dependency. "The same picture"
has to mean the same *numbers*, so the numbers live here, once, and the
renderers only choose how to stroke them.

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
twelve along a fifty-cell row is the thing a solver actually does with a ruler
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

:func:`compute_layout` then picks the largest cell that fits the printable
area of an A4 sheet, clamped into ``[MIN_CELL_MM, MAX_CELL_MM]``:

* the *cap* stops a 10x10 puzzle from being blown up into a poster with
  four-centimetre cells — beyond about 6.5 mm a cell stops getting easier to
  mark and just wastes paper;
* the *floor* is the honest limit of the format. A 50x50 grid whose clues run
  to twenty-five numbers needs seventy-five cells across; at that point the
  cells are 2 mm and the page is full. Rather than shrink past the point where
  a pencil mark is meaningless, the layout keeps 2 mm cells and lets the image
  grow past A4 — a user printing a maximum-size puzzle is scaling it down or
  printing it on A3 either way, and a silently unreadable page would be the
  worse answer.

Layering (ADR-0007): a capability submodule — stdlib only, no siblings, no
orchestrator, and (guardrail G-3) no notion whatsoever of whether the puzzle
it is measuring may be exported.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DPI",
    "MAX_CELL_MM",
    "MIN_CELL_MM",
    "MAJOR_RULE_EVERY",
    "PAGE_HEIGHT_MM",
    "PAGE_MARGIN_MM",
    "PAGE_WIDTH_MM",
    "ClueEntry",
    "GridLine",
    "Layout",
    "compute_layout",
]

#: Output resolution in dots per inch. 300 is the conventional print target:
#: at 150 a thin rule and a small clue digit both start to alias, and at 600
#: the 50x50 page is four times the bytes for detail no home printer resolves.
DPI = 300

#: A4, portrait, in millimetres (ISO 216).
PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0

#: Blank border kept on every side, in millimetres — comfortably inside the
#: unprintable margin of a typical inkjet, and enough to hold the sheet by.
PAGE_MARGIN_MM = 12.0

#: The cell-size clamp, in millimetres. See the module docstring: the cap is
#: "large enough to mark, larger is just paper", the floor is "small enough
#: that a 50x50 still fits, smaller is not a puzzle any more".
MAX_CELL_MM = 6.5
MIN_CELL_MM = 2.0

#: Every Nth grid line is stroked heavy — the standard nonogram counting aid.
MAJOR_RULE_EVERY = 5

#: Clue digits, as a fraction of the cell they sit in. 0.62 leaves a visible
#: gap on both sides of a two-digit clue (the widest that can occur: the
#: longest possible run is 50, AC-038) without the numbers touching the rules.
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


def _fit_cell(total_columns: int, total_rows: int) -> int:
    """The cell size, in device pixels, for a drawing this many cells across.

    The largest cell whose whole drawing — gutters included, which is why the
    arguments are *totals* and not the grid's own dimensions — still fits the
    printable area of an A4 sheet, clamped into the ``MIN_CELL_MM`` ..
    ``MAX_CELL_MM`` band. See the module docstring for why the clamp is
    allowed to win over the fit at the bottom end.
    """
    printable_width = _mm_to_px(PAGE_WIDTH_MM - 2 * PAGE_MARGIN_MM)
    printable_height = _mm_to_px(PAGE_HEIGHT_MM - 2 * PAGE_MARGIN_MM)
    fitted = min(
        printable_width // max(total_columns, 1),
        printable_height // max(total_rows, 1),
    )
    return max(_mm_to_px(MIN_CELL_MM), min(_mm_to_px(MAX_CELL_MM), fitted))


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

    cell = _fit_cell(row_gutter_cells + columns, column_gutter_cells + rows)
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
