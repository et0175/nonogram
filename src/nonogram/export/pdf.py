"""COMP-007 — the PDF renderer (FR-016): the puzzle and its answer key.

One file, two pages. Page 1 is what a person prints and solves — the blank grid
and its clues, i.e. CARD-012's PNG raster verbatim. Page 2 is the answer key:
the same drawing with the solution filled in. Both carry the same header,
``"<name> — <tier>"``, so a printed sheet says which puzzle it is and how hard
it was meant to be.

Why there is no PDF library here (CON-006, ADR-0006, guardrail G-1)
-------------------------------------------------------------------
Pillow writes PDFs: ``image.save(path, save_all=True, append_images=[...])``
emits a multi-page document from images already in memory. CON-006 settles
FR-016 on exactly that, which is why this is a fifth renderer rather than a
reopening of ADR-0006's dependency baseline — no ``reportlab``, no ``fpdf``, no
``weasyprint``. The consequence is that a page here *is* a raster, at
:data:`~nonogram.export.layout.DPI`, and the resolution is stamped on the save
so a viewer reproduces A4 rather than assuming 72 DPI.

Why the pages are built out of the PNG renderer
------------------------------------------------
:func:`~nonogram.export.png.render_image` returns the Pillow ``Image`` — CARD-012
exposed it for this card specifically. Page 1 is that image unmodified, so the
PDF and the PNG of one puzzle cannot drift apart: they are the same pixels, and
a change to the grid drawing lands in both without being made twice. Page 2 is
that image *copied* and then filled, and the header band is composited above
both. This module therefore adds exactly the two things a blank raster cannot
already do — reveal the solution and title the page — and re-derives none of the
geometry: every coordinate below comes from
:func:`~nonogram.export.layout.compute_layout` and
:func:`~nonogram.export.layout.header_band`.

Why a font ships inside this package (ADR-0006 revision 2026-09-01, ADR-0006/R1)
--------------------------------------------------------------------------------
Pillow bundles no TTF. ``ImageFont.load_default()`` returns an embedded
ASCII-only face, so every non-ASCII character in a header — ``к``, ``о``, ``т``,
``é`` — was drawn as the ``.notdef`` box an unassigned codepoint gets, and had
been since the first PDF this tool wrote. Filenames were never affected
(ADR-0016's sanitizer is Unicode-aware and passes ``кот`` through verbatim),
which is why the failure was confined to what a reader sees on the sheet.

The header is therefore set in **DejaVu Sans**, shipped as *package data* under
``nonogram/export/fonts/`` and loaded by :func:`_header_font`. Data, not a
dependency: ADR-0006/R1 keeps the installed runtime set at exactly stdlib +
Pillow + NumPy, and a font executes nothing, imports nothing and cannot break on
a version bump, so admitting it costs none of what that baseline exists to keep
out. ``pyproject.toml``'s ``dependencies`` list is unchanged by this; what
changed there is the package-data configuration that makes the file install out
of the src-layout. The font's own licence ships beside it as
``fonts/LICENSE`` — a permissive Bitstream Vera-derived notice that allows
redistribution and requires the notice travel with the file.

**The font's coverage is now the boundary, and it is not all of Unicode.**
DejaVu Sans covers Latin, Cyrillic and Greek (among others), which is what this
buys. A name written in a script it does not cover — Chinese, Japanese, Korean,
Thai, Devanagari — still renders as tofu, by exactly the same mechanism one
layer down. This shrinks the failing set; it does not empty it.

Coverage is not the only boundary, either: this venv's Pillow reports
``features.check("raqm") == False``, so there is no complex-script shaping and
no bidi. DejaVu *does* cover Arabic and Hebrew, but without Raqm a name in
either sets as isolated, unjoined letterforms in left-to-right order rather
than as tofu — wrong in a different way, and not fixed by this card.

Only the header moved. A page's clue digits still come out of
``png._clue_font``'s Pillow default face (:func:`_header_font` is not
consulted there) — they are ASCII decimal digits, so nothing about that
choice can tofu, and ``png.py`` is outside this card's Touches. The
consequence is that a rendered page now carries two typefaces: the title in
the bundled DejaVu Sans, the clue numbers in Pillow's embedded default. That
mix is deliberate and accepted, not an oversight.

What is *not* on the page (guardrail G-6)
------------------------------------------
A static print artifact (CON-002): no interactive layer, no solver state, no
nudge or hint metadata, and no document metadata beyond what Pillow writes for
any image. The only text is the header and the clue numbers.

Nothing here checks whether the puzzle may be exported. INV-002 is enforced once,
by the orchestrator (COMP-002, ADR-0007, guardrail G-4), before the payload this
module receives is even built — and that payload carries no readiness flag to
re-check.
"""

from __future__ import annotations

import io
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from nonogram.export.layout import DPI, HeaderBand, Layout, compute_layout, header_band
from nonogram.export.png import BACKGROUND, INK, render_image

if TYPE_CHECKING:  # pragma: no cover - import cycle is type-time only
    from nonogram.export import ExportPayload

__all__ = [
    "FONT_PACKAGE",
    "FONT_RESOURCE",
    "HEADER_SEPARATOR",
    "header_parts",
    "header_text",
    "render",
    "render_pages",
    "write_pdf",
]

#: Where the bundled face lives, as a package plus a resource path rather than
#: a filesystem path: it is *package data*, so it is addressed the way package
#: data is addressed and keeps working from a zip import or a wheel that was
#: never unpacked. See the module docstring for why it is data and not a
#: dependency (ADR-0006/R1).
FONT_PACKAGE = "nonogram.export"
FONT_RESOURCE = "fonts/DejaVuSans.ttf"

#: The notice that must travel with the file, shipped beside it.
FONT_LICENSE_RESOURCE = "fonts/LICENSE"

#: What sits between the name and the tier in the header. An em dash with
#: spaces around it, which is AC-046's ``"cat — Medium"`` spelled out — a
#: hyphen would read as part of a hyphenated name, and the on-disk file already
#: uses the hyphen for its own ``<name>-<difficulty>`` join (ADR-0016).
#:
#: It is drawn as a stroked rule rather than set as a glyph — see
#: :func:`_draw_header`.
HEADER_SEPARATOR = " — "

#: The em dash's rule, as fractions of the type size: how long the stroke is,
#: how thick, and how much air sits either side of it. An em dash is nominally
#: one em wide, but the spaces around it in :data:`HEADER_SEPARATOR` are part
#: of the mark as a reader sees it, so the stroke itself is shortened and the
#: rest given back as the gaps.
_RULE_LENGTH_RATIO = 0.6
_RULE_WEIGHT_RATIO = 0.07
_RULE_GAP_RATIO = 0.3

#: How far the header may shrink to fit the page, and how much of the page's
#: width it may occupy. ``--name`` is arbitrary user text (AC-045 asks only
#: that it not be blank), so a long name on a small puzzle's page would
#: otherwise be set past both edges and lose its ends — the one way a header
#: can silently stop saying what the puzzle is called. A third of the nominal
#: size is the floor: below that the title is smaller than the clue digits and
#: shrinking further buys nothing worth reading.
_MIN_HEADER_FONT_RATIO = 1 / 3
_HEADER_WIDTH_RATIO = 0.9

#: What marks a name the header had to cut short. Three periods rather than
#: U+2026 — DejaVu Sans does carry the ellipsis character, so this is no longer
#: forced, but it is kept: guardrail G-2 holds the header's composition fixed
#: while the face beneath it changes, and three periods and one ellipsis glyph
#: are not the same mark on the page.
_ELLIPSIS = "..."


@lru_cache(maxsize=1)
def _font_bytes() -> bytes:
    """The bundled TTF, read once.

    Read as bytes through :mod:`importlib.resources` rather than opened by
    path: package data is not guaranteed to be a file on disk, and the bytes
    are the same object every caller wants anyway. Cached because the file is
    roughly three quarters of a megabyte and :func:`_measure_header` is called
    up to three times for a single header.

    A missing or unreadable resource raises out of here rather than being
    papered over with :func:`PIL.ImageFont.load_default`: that fallback is what
    this module was changed to stop doing, and silently reinstating it would
    reproduce the tofu it exists to fix while reporting success.
    """
    return resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()


@lru_cache(maxsize=8)
def _header_font(size: int) -> ImageFont.FreeTypeFont:
    """The bundled DejaVu Sans at ``size`` pixels.

    The bundled face and not a system one, for the same reason
    ``png._clue_font`` documents: the output must not depend on which fonts
    the machine running the generator happens to have installed. What is new
    is that the bundled face is now a real Unicode TTF rather than Pillow's
    ASCII-only default, so a Cyrillic or Greek name sets as itself instead of
    as a row of ``.notdef`` boxes. Scripts DejaVu Sans does not cover still
    do not set — see the module docstring.

    That reason is shared; the *face* is not. ``png._clue_font`` still
    returns ``ImageFont.load_default()`` — this card's Touches is
    :mod:`nonogram.export.pdf` only, and clue digits are ASCII decimal
    digits, so nothing about leaving ``png.py`` alone can tofu. The
    consequence is that every page this module writes now carries two
    typefaces: the header in the bundled DejaVu Sans, the clue numbers still
    in Pillow's embedded default. Deliberate, and accepted — see the module
    docstring.

    Cached by size: :func:`_draw_header` re-measures at a second size when a
    name does not fit, and every page of every export asks for the same handful
    of sizes.
    """
    return ImageFont.truetype(io.BytesIO(_font_bytes()), size=size)


def header_parts(payload: ExportPayload) -> tuple[str, ...]:
    """The header's components, in reading order (AC-046, AC-047).

    ``("cat", "Medium")`` for a named puzzle at a scored tier. The name is
    shown exactly as the aggregate holds it (AC-044): ADR-0016's sanitization
    applies to the *filename* derived from the name, never to the name a reader
    sees.

    A payload missing either half — a hand-assembled one, or a puzzle exported
    before it was scored — contributes only the half it has, and one missing
    both yields ``()``, which :func:`render_pages` reads as "no header band at
    all" rather than printing a bare separator over an untitled page.

    Kept as components rather than as the joined line because that is how the
    header is drawn (:func:`_draw_header`); :func:`header_text` is the same
    thing as one string, for callers that want to read it rather than set it.
    """
    return tuple(part for part in (payload.name, payload.difficulty) if part)


def header_text(payload: ExportPayload) -> str:
    """The header line both pages carry, as one string — ``"cat — Medium"``."""
    return HEADER_SEPARATOR.join(header_parts(payload))


def _reveal(image: Image.Image, layout: Layout, grid: list[list[bool]]) -> Image.Image:
    """Fill ``grid``'s filled cells into ``image``, in place (the answer key).

    The one thing the blank raster deliberately cannot do. Cell rectangles are
    addressed by the same ``origin + index * cell`` arithmetic the layout used
    to place the rules, so a filled cell lands exactly between its two grid
    lines at every cell size.

    The fill is the same :data:`~nonogram.export.png.INK` as the rules, so the
    lines beneath a filled cell neither vanish visibly nor fight it — a solid
    black region is what an answer key's filled run looks like on paper.

    ``grid`` is trusted to match the clues (INV-001 makes them one fact), but
    only the cells the layout actually measured are drawn: a payload whose grid
    disagrees with its clue sets marks the page it can and never paints outside
    the drawing.
    """
    draw = ImageDraw.Draw(image)
    for row_index, row in enumerate(grid[: layout.rows]):
        top = layout.grid_top + row_index * layout.cell
        for column_index, filled in enumerate(row[: layout.columns]):
            if not filled:
                continue
            left = layout.grid_left + column_index * layout.cell
            draw.rectangle(
                (left, top, left + layout.cell, top + layout.cell), fill=INK
            )
    return image


def _measure_header(
    parts: tuple[str, ...], size: int
) -> tuple[ImageFont.FreeTypeFont, list[float], float, float]:
    """The header's type, its pieces' widths, its separator width and its total.

    The package's own DejaVu Sans (:func:`_header_font`) at an explicit size.
    The separator's width is computed from the type size rather than measured,
    because it is stroked rather than set — see :func:`_draw_header`.
    """
    font = _header_font(size)
    widths = [font.getlength(part) for part in parts]
    separator = size * (_RULE_LENGTH_RATIO + 2 * _RULE_GAP_RATIO)
    return font, widths, separator, sum(widths) + separator * (len(parts) - 1)


def _elided(text: str, font: ImageFont.FreeTypeFont, room: float) -> str:
    """``text`` cut down to what fits in ``room``, marked with an ellipsis.

    The last resort of the fitting in :func:`_draw_header`, for a name so long
    that even the smallest type it may be set in does not fit the page. A cut
    that says it happened beats a title running off both edges, where the same
    characters are lost with nothing to show for them.
    """
    kept = text
    while kept and font.getlength(kept + _ELLIPSIS) > room:
        kept = kept[:-1]
    return kept + _ELLIPSIS


def _draw_header(
    draw: ImageDraw.ImageDraw, band: HeaderBand, parts: tuple[str, ...], width: int
) -> None:
    """Set ``parts`` across the band, centred, an em rule between each pair.

    Why the separator is stroked and not set
    ----------------------------------------
    Originally out of necessity: Pillow's bundled default face is an ASCII
    subset with no U+2014, so AC-046's em dash set as a glyph came out as a
    ``.notdef`` box. That constraint is gone — the package now ships its own
    DejaVu Sans (:func:`_header_font`), which does carry the em dash.

    The rule stays anyway — not because the glyph would misbehave (a
    scalable outline glyph's advance is itself a fixed fraction of the type
    size, exactly as linear as the stroke's nominal length) but because
    guardrail G-2 changes the face the header is drawn with and nothing else
    about the header, and a stroked rule and a set em dash are visibly
    different marks on the page. Turning it back into a glyph is a
    deliberate change, not a simplification, and is out of scope here.

    The stroke does have one property the glyph would not: its *weight* is
    ``max(1, round(size * _RULE_WEIGHT_RATIO))`` (see the ``draw.line`` call
    below) — clamped to a minimum of one pixel and rounded to a whole one, so
    at the small end of the fitting range (:data:`_MIN_HEADER_FONT_RATIO`)
    the rule's thickness stops scaling linearly with size even though its
    length still does.

    A non-ASCII *name*, by contrast, is now set rather than boxed — that is the
    whole of what changed here — for names in the scripts DejaVu Sans covers.

    The pieces are measured and laid out from the centre outward rather than
    drawn with a single centred anchor, so the rule lands between the two words
    at exactly the same optical spacing at every type size.

    A header too wide for its page is set smaller rather than off both edges
    (:data:`_MIN_HEADER_FONT_RATIO`) — one measurement, one correction, since
    a face's advance widths scale with its size — and a name that still does
    not fit at that floor is elided rather than clipped. The header therefore
    always fits the page, whatever ``--name`` was.

    Args:
        draw: The page to draw on.
        band: The strip to set the header in.
        parts: The header's pieces, in reading order.
        width: The page's width, which the header has to fit inside.
    """
    size = band.font_size
    font, widths, separator, total = _measure_header(parts, size)

    usable = width * _HEADER_WIDTH_RATIO
    if total > usable:
        size = max(
            round(band.font_size * _MIN_HEADER_FONT_RATIO), int(size * usable / total)
        )
        font, widths, separator, total = _measure_header(parts, size)
    if total > usable:
        # Only the first piece — the name — can be long enough to get here; the
        # tier label is one short word and is never the part that is cut.
        parts = (_elided(parts[0], font, usable - (total - widths[0])), *parts[1:])
        font, widths, separator, total = _measure_header(parts, size)

    rule_length = size * _RULE_LENGTH_RATIO
    gap = size * _RULE_GAP_RATIO
    left = band.center_x - total / 2

    for index, (part, part_width) in enumerate(zip(parts, widths, strict=True)):
        if index:
            rule_left = left + gap
            draw.line(
                ((rule_left, band.center_y), (rule_left + rule_length, band.center_y)),
                fill=INK,
                width=max(1, round(size * _RULE_WEIGHT_RATIO)),
            )
            left += separator
        # ``anchor="lm"``: the piece starts here and is centred on the band's
        # own middle, the same vertical placement rule the clue numbers use.
        draw.text((left, band.center_y), part, font=font, fill=INK, anchor="lm")
        left += part_width


def _titled(
    image: Image.Image, band: HeaderBand, parts: tuple[str, ...]
) -> Image.Image:
    """Return ``image`` with ``parts`` set as a header band above it.

    A fresh, taller canvas with the drawing pasted below the band rather than
    text written into the existing one: the puzzle page must stay the raster
    CARD-012 produces, pixel for pixel, and growing the page is what keeps the
    header out of the drawing's margins at every puzzle size.
    """
    page = Image.new(image.mode, (image.width, image.height + band.height), BACKGROUND)
    page.paste(image, (0, band.height))
    _draw_header(ImageDraw.Draw(page), band, parts, page.width)
    return page


def render_pages(payload: ExportPayload) -> tuple[Image.Image, Image.Image]:
    """Draw ``payload``'s two pages and return them, puzzle first.

    The in-memory form of the PDF export, exposed for the same reason CARD-012
    exposed :func:`~nonogram.export.png.render_image`: the pages can be asserted
    on as pixels, without a PDF decoder the dependency baseline does not have.

    Args:
        payload: The finalized puzzle. That it *is* finalized was settled by
            COMP-002's INV-002 gate before this call (guardrail G-4).

    Returns:
        ``(puzzle_page, answer_page)`` — the blank grid with its clues, and the
        same drawing with the solution revealed. Both are titled with
        :func:`header_text`, and both are the same size, so the two sheets
        print alike.
    """
    layout = compute_layout(payload.row_clues, payload.column_clues)
    blank = render_image(payload)
    answer = _reveal(blank.copy(), layout, payload.grid)

    parts = header_parts(payload)
    if not parts:
        return blank, answer

    band = header_band(layout)
    return _titled(blank, band, parts), _titled(answer, band, parts)


def write_pdf(payload: ExportPayload, path: Path) -> Path:
    """Render ``payload`` and save both pages to ``path`` as one PDF.

    ``save_all``/``append_images`` is CON-006's whole mechanism (see the module
    docstring). ``resolution`` is what makes the pages A4-sized in the document
    instead of 4.17x too large — Pillow's PDF writer assumes 72 DPI otherwise,
    exactly as a PNG viewer does without the ``pHYs`` tag.

    Returns the path so a caller that wants both the file and its location does
    not have to hold on to the argument.
    """
    puzzle_page, answer_page = render_pages(payload)
    puzzle_page.save(
        path,
        format="PDF",
        save_all=True,
        append_images=[answer_page],
        resolution=float(DPI),
    )
    return path


def render(payload: ExportPayload, path: Path) -> None:
    """Write ``payload`` to ``path`` (the :data:`~nonogram.export.Renderer`
    signature the registry dispatches through)."""
    write_pdf(payload, path)
