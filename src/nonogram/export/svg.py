"""COMP-007 — the SVG renderer (FR-011, the vector half).

The same blank puzzle as ``png.py``, from the same
:func:`~nonogram.export.layout.compute_layout` numbers, drawn as vectors: the
grid as ``<line>`` elements, the clues as ``<text>``. The solution is again
absent by construction rather than by discipline — the layout is computed from
the clues alone, so no filled-cell coordinate exists in this module to draw.

No new dependency, and none needed (guardrail G-4, ADR-0006)
------------------------------------------------------------
SVG is XML, and this document is a few hundred elements of it with no
namespacing beyond the root, no entities and no user-supplied strings: every
value written below is an integer this package computed. ``svgwrite`` or
``cairosvg`` would buy nothing here and would reopen a dependency baseline
ADR-0006 closed. The document is therefore assembled as text, with
:func:`xml.sax.saxutils.escape` applied to the one field that is nominally a
string (the clue digits) so that the "these are only ever integers" assumption
is enforced by the code rather than trusted.

:func:`document` is separated from :func:`render` for the reason
``json_export`` splits them: the markup can be asserted without touching a
filesystem, and there is one obvious function to point a future check at.

Physical size (why the root carries inches and a pixel ``viewBox``)
--------------------------------------------------------------------
``layout`` works in device pixels at 300 DPI for A4. An SVG with a pixel
``width`` would be re-interpreted by every consumer at its own idea of a pixel
(96 per inch, usually) and print at a third of the intended size. So the root
declares ``width``/``height`` in inches — the real, physical measurement — over
a ``viewBox`` in the layout's pixels. The coordinates inside stay integers
identical to the PNG's, and the drawing scales losslessly to whatever the
printer actually is, which is the reason to ship a vector format at all.

Nothing here checks whether the puzzle may be exported: INV-002 is the
orchestrator's single enforcement point (ADR-0007, guardrail G-3), applied
before the payload is even built.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from nonogram.export.layout import Layout, compute_layout

if TYPE_CHECKING:  # pragma: no cover - import cycle is type-time only
    from nonogram.export import ExportPayload

__all__ = ["BACKGROUND", "INK", "document", "render"]

#: Same two colours as the raster renderer, for the same reason: a printed
#: puzzle is written on in pencil and wants maximum contrast.
INK = "#000000"
BACKGROUND = "#ffffff"

#: The clue face, as a CSS font stack. A generic family last, so a viewer with
#: none of the named faces still resolves *something* proportioned like them
#: rather than falling back to a default that overflows the cell.
_FONT_FAMILY = "DejaVu Sans, Helvetica, Arial, sans-serif"

_SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def _root_open(layout: Layout) -> str:
    """The ``<svg>`` element: physical size outside, layout pixels inside."""
    return (
        f'<svg xmlns="{_SVG_NAMESPACE}" version="1.1" '
        f'width="{layout.width_inches:.4f}in" '
        f'height="{layout.height_inches:.4f}in" '
        f'viewBox="0 0 {layout.width} {layout.height}">'
    )


def _background(layout: Layout) -> str:
    """An explicit white sheet.

    SVG's own background is transparent, which a viewer paints over with
    whatever it likes — a dark-mode reader would show black-on-black. A puzzle
    is a sheet of paper, so the sheet is drawn.
    """
    return (
        f'<rect x="0" y="0" width="{layout.width}" height="{layout.height}" '
        f'fill="{BACKGROUND}"/>'
    )


def _line(x1: int, y1: int, x2: int, y2: int, width: int, major: bool) -> str:
    """One ruled line, tagged with why it is as heavy as it is.

    The ``class`` is redundant to the renderer — ``stroke-width`` already says
    everything the drawing needs — and is emitted anyway because an SVG is a
    document someone may open in an editor: ``major`` names the every-5th rule
    so a restyle can find all of them at once instead of matching on a number.
    """
    return (
        f'<line class="{"major" if major else "minor"}" '
        f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke-width="{width}"/>'
    )


def _grid_elements(layout: Layout) -> list[str]:
    """Every ruled line, thin ones first so the heavy rules stay continuous
    where they cross (the same ordering ``png.py`` draws in)."""
    minor: list[str] = []
    major: list[str] = []
    for line in layout.vertical_lines:
        element = _line(
            line.position, line.start, line.position, line.end, line.width, line.major
        )
        (major if line.major else minor).append(element)
    for line in layout.horizontal_lines:
        element = _line(
            line.start, line.position, line.end, line.position, line.width, line.major
        )
        (major if line.major else minor).append(element)
    return minor + major


def _clue_elements(layout: Layout) -> list[str]:
    """Every clue number, centred on the point the layout placed it.

    ``text-anchor="middle"`` with ``dominant-baseline="central"`` is the vector
    equivalent of the raster renderer's ``anchor="mm"``: the glyph is centred on
    the point in both axes, so neither renderer has to know anything about the
    other's font metrics for the two outputs to agree.
    """
    return [
        f'<text x="{entry.center_x}" y="{entry.center_y}">'
        f"{escape(str(entry.value))}</text>"
        for entry in layout.clue_entries
    ]


def document(payload: ExportPayload) -> str:
    """The SVG document for ``payload``, as text.

    Only ``payload``'s clues are read; ``payload.grid`` — the solution — is
    never touched, which is what keeps the printed page a puzzle.

    Newline-separated rather than minified: an export is a durable artifact a
    person may open, diff or restyle, and at the maximum supported 30x30
    (AC-084) the whole document is still a few tens of kilobytes.
    """
    layout = compute_layout(payload.row_clues, payload.column_clues)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        _root_open(layout),
        _background(layout),
        # Presentation shared by every element of a group, stated once: it
        # keeps the per-element markup down to the coordinates that differ,
        # which is the part a reader of this file cares about.
        f'<g stroke="{INK}" stroke-linecap="square">',
        *_grid_elements(layout),
        "</g>",
        f'<g fill="{INK}" font-family="{_FONT_FAMILY}" '
        f'font-size="{layout.clue_font_size}" '
        'text-anchor="middle" dominant-baseline="central">',
        *_clue_elements(layout),
        "</g>",
        "</svg>",
    ]
    return "\n".join(parts)


def render(payload: ExportPayload, path: Path) -> None:
    """Write ``payload`` to ``path`` as SVG (the
    :data:`~nonogram.export.Renderer` signature).

    UTF-8 and newline-terminated, matching the XML declaration above and the
    JSON renderer's convention.
    """
    path.write_text(f"{document(payload)}\n", encoding="utf-8")
