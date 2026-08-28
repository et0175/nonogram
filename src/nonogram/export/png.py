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
``layout`` computes everything for A4 at 300 DPI (see its module docstring for
the cell-size clamp that follows from that), and :func:`write_png` stamps that
number into the file's ``pHYs`` chunk, so a print dialog reproduces the intended
physical size instead of assuming 72 DPI and scaling the page to four times its
size.

Nothing here checks whether the puzzle may be exported: INV-002 is the
orchestrator's single enforcement point (ADR-0007, guardrail G-3), applied
before the payload is even built.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from nonogram.export.layout import DPI, GridLine, Layout, compute_layout

if TYPE_CHECKING:  # pragma: no cover - import cycle is type-time only
    from nonogram.export import ExportPayload

__all__ = ["BACKGROUND", "INK", "render", "render_image", "write_png"]

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


def _draw_grid(draw: ImageDraw.ImageDraw, layout: Layout) -> None:
    """Stroke every ruled line, thin ones first.

    Order matters: the every-5th and border rules are drawn last so that where
    a heavy line crosses a thin one, the heavy line is the one that survives
    the overlap and stays visually continuous across the page.
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


def render_image(payload: ExportPayload) -> Image.Image:
    """Draw ``payload`` as a blank puzzle and return the raster (CON-006).

    The in-memory form of the PNG export, and the buffer CARD-014's PDF saves
    a second time rather than redrawing. Only ``payload``'s clues are read;
    ``payload.grid`` — the solution — is never touched, which is what keeps
    the printed page a puzzle.

    Args:
        payload: The finalized puzzle. That it *is* finalized was settled by
            COMP-002's INV-002 gate before this call (guardrail G-3).

    Returns:
        A fresh ``RGB`` image, the size the layout computed for A4 at
        :data:`~nonogram.export.layout.DPI`.
    """
    layout = compute_layout(payload.row_clues, payload.column_clues)
    image = Image.new(_MODE, (layout.width, layout.height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    _draw_grid(draw, layout)
    _draw_clues(draw, layout)
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
