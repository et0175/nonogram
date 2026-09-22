"""COMP-007 — the PNG renderer (FR-011, the raster half).

What a person prints and solves: the *blank* grid and its clues. The solution
is deliberately absent — it is the JSON/CSV export's job (FR-012) and CARD-014's
answer-key page — and the omission is structural rather than a rule this module
remembers to follow: everything drawn below comes out of
:func:`~nonogram.export.layout.compute_layout`, which is handed the clues and
never the grid, so there is no filled-cell coordinate in scope to draw even by
mistake.

Why the ``Image`` is the real entry point (CON-006)
---------------------------------------------------
:func:`render_image` returns the Pillow ``Image``; :func:`write_png` saves one,
and :func:`render` is the :data:`~nonogram.export.Renderer` the registry calls.
That order is the point. CON-006 settles FR-016's PDF as *a second sink on this
raster path* — Pillow saves a PDF from the same in-memory image with
``save_all``/``append_images`` — so ADR-0006's dependency baseline is not
reopened for a PDF library. A module that only exposed "write a PNG to this
path" would force CARD-014 either to write a throwaway PNG and read it back, or
to re-implement this drawing against a second geometry that could drift from
this one. Handing back the ``Image`` costs nothing here and is the whole reason
PDF is one card instead of a dependency decision.

It is also what makes this drawing testable without a filesystem or a decoder:
a test can assert on pixels directly, the same way ``json_export.document`` lets
the JSON shape be asserted without writing a file.

Resolution
----------
``layout`` computes everything at 300 DPI for A4, or for the sheet an explicit
``PageSpec`` names (ADR-0036; only the book passes one, through
:func:`render_image`; see the layout module docstring for the cell-size clamp
that follows from that), and :func:`write_png` stamps that
number into the file's ``pHYs`` chunk, so a print dialog reproduces the intended
physical size instead of assuming 72 DPI and scaling the page to four times its
size.

Nothing here checks whether the puzzle may be exported: INV-002 is the
orchestrator's single enforcement point (ADR-0007, guardrail G-3), applied
before the payload is even built.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from nonogram.export.layout import (
    DPI,
    AnswerTile,
    GridLine,
    Layout,
    PageSpec,
    compute_answer_page_layout,
    compute_layout,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle is type-time only
    from nonogram.export import ExportPayload

__all__ = [
    "BACKGROUND",
    "INK",
    "render",
    "render_answer_page",
    "render_image",
    "write_png",
]

#: Pure black on pure white. A puzzle is printed and then written on in pencil,
#: so maximum contrast and no anti-aliased grey in the paper: a laser printer
#: renders a mid-grey rule as a dither pattern, which reads as a texture rather
#: than as a line.
INK = (0, 0, 0)
BACKGROUND = (255, 255, 255)

#: ``"RGB"`` rather than ``"1"`` or ``"L"``. The drawing is two colours, but
#: the glyph rasterizer anti-aliases clue digits, and a bilevel canvas would
#: turn that into speckle at the 2 mm cell the maximum-size puzzle uses. The
#: cost is bytes in a file that is written once and printed.
_MODE = "RGB"


def _clue_font(layout: Layout) -> ImageFont.FreeTypeFont:
    """The font clue numbers are drawn in, sized to the layout's cell.

    Pillow's bundled default at an explicit size, so the output does not depend
    on which fonts the machine running the generator happens to have installed
    — a puzzle generated on one laptop and printed from another must not come
    out with differently-sized clues, and a missing-font fallback that silently
    produced Pillow's unscalable bitmap face would render 2 mm cells with
    11-pixel digits.
    """
    return ImageFont.load_default(size=layout.clue_font_size)


def _draw_grid(draw: ImageDraw.ImageDraw, layout: Layout | AnswerTile) -> None:
    """Stroke every ruled line, thin ones first.

    Order matters: the every-5th and border rules are drawn last so that where
    a heavy line crosses a thin one, the heavy line is the one that survives
    the overlap and stays visually continuous across the page.

    A puzzle page and an answer tile (FR-042) are both ruled by this, because
    both carry the same two tuples of placed :class:`GridLine`s: the answer key
    is ruled by the drawing code the puzzle is ruled by, not by a second one.
    """
    oriented: list[tuple[GridLine, bool]] = [
        *((line, True) for line in layout.vertical_lines),
        *((line, False) for line in layout.horizontal_lines),
    ]
    for line, vertical in sorted(oriented, key=lambda pair: pair[0].major):
        if vertical:
            ends = [(line.position, line.start), (line.position, line.end)]
        else:
            ends = [(line.start, line.position), (line.end, line.position)]
        draw.line(ends, fill=INK, width=line.width)


def _draw_clues(draw: ImageDraw.ImageDraw, layout: Layout) -> None:
    """Write every clue number, centred on the point the layout placed it.

    ``anchor="mm"`` centres the glyph box on that point in both axes, which is
    the one placement rule that does not depend on this font's ascent, descent
    or digit width — so the same coordinates centre a clue for the SVG renderer
    and for whatever face a viewer resolves there.
    """
    font = _clue_font(layout)
    for entry in layout.clue_entries:
        draw.text(
            (entry.center_x, entry.center_y),
            str(entry.value),
            font=font,
            fill=INK,
            anchor="mm",
        )


def render_image(payload: ExportPayload, page_spec: PageSpec | None = None) -> Image.Image:
    """Draw ``payload`` as a blank puzzle and return the raster (CON-006).

    The in-memory form of the PNG export, and the buffer CARD-014's PDF saves
    a second time rather than redrawing. Only ``payload``'s clues are read;
    ``payload.grid`` — the solution — is never touched, which is what keeps
    the printed page a puzzle.

    Args:
        payload: The finalized puzzle. That it *is* finalized was settled by
            COMP-002's INV-002 gate before this call (guardrail G-3).
        page_spec: The sheet (ADR-0036), passed straight to
            :func:`~nonogram.export.layout.compute_layout`. ``None`` — every
            CLI and web export — is today's A4 drawing, byte for byte. A book
            spec with a parity returns the whole trim page with the drawing
            already placed on it, and its band left blank.

    Returns:
        A fresh ``RGB`` image, the size the layout computed at
        :data:`~nonogram.export.layout.DPI`: the drawing plus its margin on
        the default spec, the trim on a placed page.
    """
    layout = compute_layout(payload.row_clues, payload.column_clues, page_spec)
    image = Image.new(_MODE, (layout.width, layout.height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    _draw_grid(draw, layout)
    _draw_clues(draw, layout)
    return image


#: One answer of the key: its solved grid and the caption printed above it.
#: The caption's *text* is composed by the book (COMP-009, CARD-134) — "Puzzle
#: 7", with or without a title — and this module only prints the string it is
#: handed. An empty string prints nothing and still occupies its line.
type Answer = tuple[Sequence[Sequence[bool]], str]


def _answer_extent(grid: Sequence[Sequence[bool]], index: int) -> tuple[int, int]:
    """One answer's ``(width, height)`` in cells, from the grid itself.

    Raises:
        ValueError: the grid is empty or its rows are not all the same length —
            not a rectangle, so not a nonogram's solution.
    """
    rows = len(grid)
    columns = len(grid[0]) if rows else 0
    if not rows or not columns or any(len(row) != columns for row in grid):
        raise ValueError(
            f"answer {index} must be a non-empty rectangular grid, not "
            f"{rows} row(s) of {sorted({len(row) for row in grid})} cell(s)"
        )
    return columns, rows


def _draw_answer(draw: ImageDraw.ImageDraw, tile: AnswerTile, grid: Sequence[Sequence[bool]]) -> None:
    """Fill one answer's cells, then rule it (FR-042, AC-267).

    Filled cells first and the rules over them, so a heavy every-5th rule stays
    continuous across the white of the picture instead of being cut by the next
    filled block. Each cell is the rectangle between its own boundaries, which
    the tile reads off its placed rules — so a filled cell and the rule framing
    it cannot be half a pixel apart.

    No clue number and no clue gutter is drawn, and none *could* be: an
    :class:`AnswerTile` carries neither, the same structural reason
    :func:`render_image` cannot leak a solution onto a puzzle page.
    """
    xs = tile.column_boundaries
    ys = tile.row_boundaries
    for row, cells in enumerate(grid):
        for column, filled in enumerate(cells):
            if filled:
                draw.rectangle(
                    (xs[column], ys[row], xs[column + 1], ys[row + 1]), fill=INK
                )
    _draw_grid(draw, tile)


def render_answer_page(
    answers: Sequence[Answer],
    capacity: int,
    page_spec: PageSpec,
    heading: str | None = None,
) -> Image.Image:
    """Draw one page of the book's packed answer key and return the raster (FR-042).

    The rendering half of CARD-133: the geometry is
    :func:`~nonogram.export.layout.compute_answer_page_layout`'s, and this
    draws what it measured — each answer as its filled grid alone, its caption
    on the tile's reserved line, and the level heading on the page's own line
    when there is one. Which answers share a page, which page carries a
    heading, and what a caption says are the book's decisions (COMP-009,
    CARD-134); this call draws the page it is given.

    Args:
        answers: Up to ``capacity`` ``(grid, caption)`` pairs in fill order,
            left to right then top to bottom. Each ``grid`` is the solution in
            the project's boundary form — rows of booleans, ``True`` for a
            filled cell.
        capacity: 6 (2 x 3) or 4 (2 x 2), INV-011's rule for this page.
        page_spec: The book page — a placed page with a flat cell cap. Its
            title band is ignored: an answer page has none.
        heading: The level heading ("Easy"), or ``None`` for a page without
            one. The same value goes to the layout call, which reserves the
            line, and to this one, which prints it.

    Returns:
        A fresh ``RGB`` image the size of the trim at
        :data:`~nonogram.export.layout.DPI`.

    Raises:
        ValueError: an answer's grid is not a non-empty rectangle, or the
            layout call refuses the page (see
            :func:`~nonogram.export.layout.compute_answer_page_layout`).
        TypeError: ``page_spec`` is not a
            :class:`~nonogram.export.layout.PageSpec`.
    """
    extents = [_answer_extent(grid, index) for index, (grid, _) in enumerate(answers)]
    layout = compute_answer_page_layout(extents, capacity, page_spec, heading)
    image = Image.new(_MODE, (layout.width, layout.height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    if layout.heading is not None and heading:
        draw.text(
            (layout.heading.center_x, layout.heading.center_y),
            heading,
            font=ImageFont.load_default(size=layout.heading.font_size),
            fill=INK,
            anchor="mm",
        )
    for tile, (grid, caption) in zip(layout.tiles, answers, strict=True):
        _draw_answer(draw, tile, grid)
        if caption:
            draw.text(
                (tile.caption_center_x, tile.caption_center_y),
                caption,
                font=ImageFont.load_default(size=tile.caption_font_size),
                fill=INK,
                anchor="mm",
            )
    return image


def write_png(payload: ExportPayload, path: Path) -> Path:
    """Render ``payload`` and save it to ``path`` as a PNG.

    The thin sink around :func:`render_image`: it adds the resolution tag and
    nothing else. Returns the path so a caller that wants both the file and its
    location does not have to hold on to the argument.
    """
    image = render_image(payload)
    image.save(path, format="PNG", dpi=(DPI, DPI))
    return path


def render(payload: ExportPayload, path: Path) -> None:
    """Write ``payload`` to ``path`` (the :data:`~nonogram.export.Renderer`
    signature the registry dispatches through)."""
    write_png(payload, path)
