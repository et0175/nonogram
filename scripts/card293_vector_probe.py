#!/usr/bin/env python
"""CARD-293 (SPIKE) — throwaway probe: is a vector PDF interior affordable?

**This is not production code and nothing imports it.** It lives in
``scripts/`` because CARD-293's ``Touches`` says so, and it exists only to
produce the numbers in
``meta/profiling/card-293-vector-interior-comparison.md``. It touches
``src/**`` not at all: it *reads* COMP-007's :class:`~nonogram.export.layout.Layout`
and ``PIL.PdfParser`` — the same two things the shipped
``book_pdf_generator._write_page`` reads — and writes a second kind of page
object beside the one that ships, in a scratch file, for comparison.

Subcommands (all absolute paths; nothing is written next to the repo):

    font    AC-5 — price font embedding, and prove a clue digit can be placed.
    page    AC-1 — one real book page, raster arm and vector arm, sizes.
    bench   AC-1/G-4/G-6 — interleaved A/B/A/B wall clock, min and median.
    proof   AC-2 — the owner's 0.3/0.8/1.3 pt against every raster reading.

Deliberately NOT here (G-3): any walk of the page plan, any guide/TOC/divider/
answer page, the QR glyph, the difficulty dots. One puzzle page, drawn
convincingly, is the whole deliverable.
"""

from __future__ import annotations

import argparse
import json
import statistics
import struct
import sys
import time
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Sequence

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT / "src"), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PIL import Image, ImageDraw, PdfParser  # noqa: E402

from nonogram.export.layout import Layout, compute_layout  # noqa: E402

FONT_PATH = _ROOT / "src" / "nonogram" / "export" / "fonts" / "DejaVuSans.ttf"

#: The project's own unit for retention (tests/test_book_pdf_memory.py:210).
PAGE_BITMAP_BYTES = 2550 * 3300 * 3

#: 1 PDF point is 1/72 in; the book is drawn at 300 DPI.
PT_PER_PX = 72.0 / 300.0


# --------------------------------------------------------------------------
# TrueType: the metrics a PDF font dictionary has to state
# --------------------------------------------------------------------------
# No stdlib module parses sfnt, so this is `struct` over five tables. It is
# the whole of the "hard part" AC-5 asks to be priced, and it is reported in
# lines of code at the bottom of `cmd_font`.


def sfnt_tables(data: bytes) -> dict[str, tuple[int, int]]:
    """``{tag: (offset, length)}`` for every table in ``data``."""
    count = struct.unpack(">H", data[4:6])[0]
    out: dict[str, tuple[int, int]] = {}
    for index in range(count):
        base = 12 + 16 * index
        tag, _checksum, offset, length = struct.unpack(">4sIII", data[base : base + 16])
        out[tag.decode("latin-1")] = (offset, length)
    return out


@dataclass(frozen=True)
class FontMetrics:
    units_per_em: int
    bbox: tuple[int, int, int, int]
    ascent: int
    descent: int
    cap_height: int
    #: Unicode codepoint -> advance width in 1000ths of an em (PDF's unit).
    widths_1000: dict[int, int]


def _cmap_4(data: bytes, offset: int) -> dict[int, int]:
    """A format-4 ``cmap`` subtable as ``{codepoint: glyph id}``."""
    seg_x2 = struct.unpack(">H", data[offset + 6 : offset + 8])[0]
    segs = seg_x2 // 2
    ends = struct.unpack(f">{segs}H", data[offset + 14 : offset + 14 + seg_x2])
    start_at = offset + 16 + seg_x2
    starts = struct.unpack(f">{segs}H", data[start_at : start_at + seg_x2])
    delta_at = start_at + seg_x2
    deltas = struct.unpack(f">{segs}h", data[delta_at : delta_at + seg_x2])
    range_at = delta_at + seg_x2
    offsets = struct.unpack(f">{segs}H", data[range_at : range_at + seg_x2])
    out: dict[int, int] = {}
    for index in range(segs):
        for code in range(starts[index], min(ends[index], 0xFFFF) + 1):
            if offsets[index] == 0:
                glyph = (code + deltas[index]) & 0xFFFF
            else:
                at = range_at + index * 2 + offsets[index] + (code - starts[index]) * 2
                glyph = struct.unpack(">H", data[at : at + 2])[0]
                if glyph:
                    glyph = (glyph + deltas[index]) & 0xFFFF
            if glyph:
                out[code] = glyph
    return out


def unicode_cmap(data: bytes) -> dict[int, int]:
    """The (3, 1) Windows BMP ``cmap`` — the one a PDF ``/TrueType`` font uses."""
    offset, _ = sfnt_tables(data)["cmap"]
    count = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
    chosen: int | None = None
    for index in range(count):
        base = offset + 4 + 8 * index
        platform, encoding, sub = struct.unpack(">HHI", data[base : base + 8])
        if (platform, encoding) in {(3, 1), (0, 3), (0, 4)}:
            chosen = offset + sub
            break
    if chosen is None:
        raise RuntimeError("no Windows/Unicode BMP cmap in this font")
    if struct.unpack(">H", data[chosen : chosen + 2])[0] != 4:
        raise RuntimeError("cmap subtable is not format 4")
    return _cmap_4(data, chosen)


def _advances(data: bytes) -> list[int]:
    """Every glyph's advance width in font units, from ``hhea``/``hmtx``."""
    tables = sfnt_tables(data)
    hhea, _ = tables["hhea"]
    metrics = struct.unpack(">H", data[hhea + 34 : hhea + 36])[0]
    maxp, _ = tables["maxp"]
    glyphs = struct.unpack(">H", data[maxp + 4 : maxp + 6])[0]
    hmtx, _ = tables["hmtx"]
    out: list[int] = []
    for index in range(metrics):
        out.append(struct.unpack(">H", data[hmtx + 4 * index : hmtx + 4 * index + 2])[0])
    out.extend([out[-1]] * (glyphs - metrics))
    return out


def font_metrics(data: bytes, codepoints: Iterable[int]) -> FontMetrics:
    """Everything a PDF font dictionary and descriptor have to state."""
    tables = sfnt_tables(data)
    head, _ = tables["head"]
    upem = struct.unpack(">H", data[head + 18 : head + 20])[0]
    bbox = struct.unpack(">hhhh", data[head + 36 : head + 44])
    hhea, _ = tables["hhea"]
    ascent, descent = struct.unpack(">hh", data[hhea + 4 : hhea + 8])
    os2, _ = tables["OS/2"]
    version = struct.unpack(">H", data[os2 : os2 + 2])[0]
    cap = (
        struct.unpack(">h", data[os2 + 88 : os2 + 90])[0]
        if version >= 2
        else round(ascent * 0.7)
    )
    cmap = unicode_cmap(data)
    advances = _advances(data)
    scale = 1000.0 / upem
    widths = {}
    for code in codepoints:
        glyph = cmap.get(code, 0)
        widths[code] = round(advances[glyph] * scale)
    return FontMetrics(
        units_per_em=upem,
        bbox=(
            round(bbox[0] * scale),
            round(bbox[1] * scale),
            round(bbox[2] * scale),
            round(bbox[3] * scale),
        ),
        ascent=round(ascent * scale),
        descent=round(descent * scale),
        cap_height=round(cap * scale),
        widths_1000=widths,
    )


#: Tables a rasteriser needs to draw an embedded TrueType glyph. Everything
#: else in DejaVuSans.ttf — GPOS/GSUB/MATH/kern/name/post/GDEF/FFTM/gasp — is
#: layout and metadata a PDF viewer never consults for a simple /TrueType
#: font with /WinAnsiEncoding.
_KEEP_TABLES = ("cvt ", "fpgm", "glyf", "head", "hhea", "hmtx", "loca", "maxp", "prep", "cmap")


def stripped_sfnt(data: bytes, keep: Sequence[str] = _KEEP_TABLES) -> bytes:
    """``data`` with every table outside ``keep`` dropped — a table-level subset.

    This is *not* glyph subsetting: ``glyf``/``loca`` are copied whole, so no
    glyph id moves and no composite-glyph closure has to be computed. That is
    the expensive half of real subsetting and this function is the evidence
    that it is not needed (see the comparison document's AC-5 section).
    """
    tables = sfnt_tables(data)
    present = [tag for tag in keep if tag in tables]
    count = len(present)
    search = 1
    while search * 2 <= count:
        search *= 2
    header = struct.pack(">IHHHH", 0x00010000, count, search * 16, 0, count * 16 - search * 16)
    directory = b""
    body = b""
    cursor = 12 + 16 * count
    for tag in present:
        offset, length = tables[tag]
        chunk = data[offset : offset + length]
        checksum = 0
        padded = chunk + b"\0" * (-len(chunk) % 4)
        for index in range(0, len(padded), 4):
            checksum = (checksum + struct.unpack(">I", padded[index : index + 4])[0]) & 0xFFFFFFFF
        directory += struct.pack(">4sIII", tag.encode("latin-1"), checksum, cursor, length)
        body += padded
        cursor += len(padded)
    return header + directory + body


# --------------------------------------------------------------------------
# A vector page: PDF operators over a COMP-007 Layout
# --------------------------------------------------------------------------


def _num(value: float) -> str:
    """A PDF number, short: no exponent, no trailing zeros."""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


@dataclass(frozen=True)
class Weights:
    """The three rule weights of the owner's design, in PDF points."""

    cell_pt: float
    fifth_pt: float
    border_pt: float
    #: Grey level of a cell line, 0 = black, 1 = paper.
    cell_grey: float = 0.0
    label: str = ""


SHIPPED_TODAY = Weights(0.72, 1.44, 1.44, 0.0, "shipped today (COMP-007: 3 px / 6 px)")
CARD_227 = Weights(0.48, 1.28, 2.08, 0.35, "ADR-0037/R2 amended (CARD-227): 0.48/1.28/2.08 pt")
OWNER = Weights(0.3, 0.8, 1.3, 0.35, "owner's artifact: 0.3/0.8/1.3 pt")


class _Pen:
    """Accumulates PDF path operators, in points, y up from the page foot."""

    def __init__(self, height_px: int) -> None:
        self._height = height_px
        self._parts: list[str] = []

    def _x(self, value: float) -> str:
        return _num(value * PT_PER_PX)

    def _y(self, value: float) -> str:
        return _num((self._height - value) * PT_PER_PX)

    def grey(self, level: float) -> None:
        self._parts.append(f"{_num(level)} G")

    def width(self, points: float) -> None:
        self._parts.append(f"{_num(points)} w")

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self._parts.append(
            f"{self._x(x1)} {self._y(y1)} m {self._x(x2)} {self._y(y2)} l S"
        )

    def rect(self, left: float, top: float, right: float, bottom: float) -> None:
        self._parts.append(
            f"{self._x(left)} {self._y(bottom)} "
            f"{_num((right - left) * PT_PER_PX)} {_num((bottom - top) * PT_PER_PX)} re S"
        )

    def text(
        self,
        value: str,
        center_x: float,
        center_y: float,
        size_px: float,
        metrics: FontMetrics,
        resource: str = "F1",
        grey: float = 0.0,
    ) -> None:
        """``value`` centred on ``(center_x, center_y)``, both axes.

        The vector equivalent of Pillow's ``anchor="mm"``: horizontally by the
        string's own advance, vertically on the ascender/descender midpoint,
        so neither renderer has to know the other's font metrics.
        """
        size_pt = size_px * PT_PER_PX
        advance = sum(metrics.widths_1000.get(ord(ch), 0) for ch in value) / 1000.0
        left = center_x * PT_PER_PX - advance * size_pt / 2.0
        middle = (metrics.ascent + metrics.descent) / 2000.0
        baseline = (self._height - center_y) * PT_PER_PX - middle * size_pt
        escaped = value.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        self._parts.append(
            f"{_num(grey)} g BT /{resource} {_num(size_pt)} Tf "
            f"{_num(left)} {_num(baseline)} Td ({escaped}) Tj ET"
        )

    def stream(self) -> bytes:
        return ("\n".join(self._parts) + "\n").encode("ascii")


def _is_fifth(index: int, last: int) -> bool:
    return index % 5 == 0 or index == last


def page_stream(
    layout: Layout,
    weights: Weights,
    metrics: FontMetrics,
    *,
    band: str | None = None,
    folio: str | None = None,
) -> bytes:
    """One puzzle page as a PDF content stream.

    Every coordinate is COMP-007's (G-1/ADR-0036/R2): this draws what the
    layout already measured and places nothing. The three weights are applied
    where the layout says ``major``/``minor`` and on :attr:`Layout.frame`, which
    is the whole of what CARD-227 would change in the raster renderer too.
    """
    pen = _Pen(layout.height)
    verticals = layout.vertical_lines
    horizontals = layout.horizontal_lines
    last_v, last_h = len(verticals) - 1, len(horizontals) - 1

    # Cell lines first, so the heavier rules stay continuous where they cross
    # (the ordering png.py and svg.py both draw in).
    pen.grey(weights.cell_grey)
    pen.width(weights.cell_pt)
    for index, line in enumerate(verticals):
        if not _is_fifth(index, last_v):
            pen.line(line.position, line.start, line.position, line.end)
    for index, line in enumerate(horizontals):
        if not _is_fifth(index, last_h):
            pen.line(line.start, line.position, line.end, line.position)

    pen.grey(0.0)
    pen.width(weights.fifth_pt)
    for index, line in enumerate(verticals):
        if _is_fifth(index, last_v) and index not in (0, last_v):
            pen.line(line.position, line.start, line.position, line.end)
    for index, line in enumerate(horizontals):
        if _is_fifth(index, last_h) and index not in (0, last_h):
            pen.line(line.start, line.position, line.end, line.position)

    pen.width(weights.border_pt)
    pen.rect(
        verticals[0].position,
        horizontals[0].position,
        verticals[-1].position,
        horizontals[-1].position,
    )
    if layout.frame is not None:
        pen.rect(layout.frame.left, layout.frame.top, layout.frame.right, layout.frame.bottom)

    for entry in layout.clue_entries:
        pen.text(
            str(entry.value),
            entry.center_x,
            entry.center_y,
            layout.clue_font_size,
            metrics,
        )
    if band:
        pen.text(band, layout.width / 2, layout.margin / 2, layout.clue_font_size, metrics)
    if folio:
        pen.text(
            folio,
            layout.width / 2,
            layout.height - layout.margin / 3,
            layout.clue_font_size * 0.7,
            metrics,
        )
    return pen.stream()


class VectorPdfWriter:
    """Writes vector pages with the *same* ``PIL.PdfParser`` the book already uses.

    ``book_pdf_generator._write_page`` writes three objects per page — a
    DCTDecode image, a page, and a contents stream that draws the image over
    the whole page. This writes **two** per page — a page and a contents
    stream of operators — plus three objects *once per file* for the font. The
    object-table pre-allocation, the catalog, the xref and the trailer are
    untouched, which is the finding: the PDF plumbing a vector interior needs
    already ships.
    """

    def __init__(self, *, dpi: int, font_bytes: bytes, metrics: FontMetrics) -> None:
        self.dpi = dpi
        self.font_bytes = font_bytes
        self.metrics = metrics

    def write(self, pages: Sequence[tuple[Layout, bytes]]) -> BytesIO:
        written = BytesIO()
        pdf = PdfParser.PdfParser(f=written, filename="", mode="w+b")
        pdf.info["CreationDate"] = time.gmtime()
        pdf.info["ModDate"] = time.gmtime()

        font_ref = pdf.next_object_id(0)
        descriptor_ref = pdf.next_object_id(0)
        file_ref = pdf.next_object_id(0)
        page_refs = []
        contents_refs = []
        for _ in pages:
            page_refs.append(pdf.next_object_id(0))
            contents_refs.append(pdf.next_object_id(0))
            pdf.pages.append(page_refs[-1])

        pdf.start_writing()
        pdf.write_header()
        pdf.write_comment("CARD-293 spike: vector interior probe")
        pdf.write_catalog()

        first, last = 32, 126
        widths = [self.metrics.widths_1000.get(code, 0) for code in range(first, last + 1)]
        compressed = zlib.compress(self.font_bytes, 9)
        pdf.write_obj(
            file_ref,
            stream=compressed,
            Filter=PdfParser.PdfName("FlateDecode"),
            Length1=len(self.font_bytes),
        )
        pdf.write_obj(
            descriptor_ref,
            Type=PdfParser.PdfName("FontDescriptor"),
            FontName=PdfParser.PdfName("DejaVuSans"),
            Flags=32,
            FontBBox=list(self.metrics.bbox),
            ItalicAngle=0,
            Ascent=self.metrics.ascent,
            Descent=self.metrics.descent,
            CapHeight=self.metrics.cap_height,
            StemV=80,
            FontFile2=file_ref,
        )
        pdf.write_obj(
            font_ref,
            Type=PdfParser.PdfName("Font"),
            Subtype=PdfParser.PdfName("TrueType"),
            BaseFont=PdfParser.PdfName("DejaVuSans"),
            FirstChar=first,
            LastChar=last,
            Widths=widths,
            FontDescriptor=descriptor_ref,
            Encoding=PdfParser.PdfName("WinAnsiEncoding"),
        )

        for index, (layout, stream) in enumerate(pages):
            width_pt = layout.width * 72.0 / self.dpi
            height_pt = layout.height * 72.0 / self.dpi
            pdf.write_page(
                page_refs[index],
                Resources=PdfParser.PdfDict(
                    ProcSet=[PdfParser.PdfName("PDF"), PdfParser.PdfName("Text")],
                    Font=PdfParser.PdfDict(F1=font_ref),
                ),
                MediaBox=[0, 0, width_pt, height_pt],
                Contents=contents_refs[index],
            )
            pdf.write_obj(
                contents_refs[index],
                stream=zlib.compress(stream, 9),
                Filter=PdfParser.PdfName("FlateDecode"),
            )

        pdf.write_xref_and_trailer()
        pdf.close()
        written.seek(0)
        return written


# --------------------------------------------------------------------------
# The raster arm, written by the production writer
# --------------------------------------------------------------------------


def raster_pdf(pages: Sequence[Image.Image], dpi: int, mode: str) -> BytesIO:
    """``pages`` through the shipped writer, so arm A is the real thing.

    Calls ``BookPDFGenerator._write_pdf`` itself rather than a copy of it, so
    the raster arm's bytes are the bytes the book ships (G-4: print what each
    arm IS).
    """
    from nonogram.admin.book_pdf_generator import BookPDFGenerator

    from tests.helpers.book_corpus import corpus_book

    generator = BookPDFGenerator(corpus_book())
    return generator._write_pdf(iter(pages), len(pages), mode=mode)


def raster_pdf_streamed(
    pages: Iterable[Image.Image], count: int, dpi: int, mode: str
) -> BytesIO:
    """``raster_pdf`` over a generator — the one-page-retained shape CARD-145 ships."""
    from nonogram.admin.book_pdf_generator import BookPDFGenerator

    from tests.helpers.book_corpus import corpus_book

    return BookPDFGenerator(corpus_book())._write_pdf(pages, count, mode=mode)


def raster_page(layout: Layout, weights: Weights) -> Image.Image:
    """The same layout drawn as pixels, at ``weights`` rounded to whole pixels.

    A probe, not the renderer: it exists so the proof sheet can show what a
    weight *becomes* on a 300 DPI device — which is the device floor the whole
    card is about. Rounded with ``round`` and floored at 1, exactly as
    COMP-007 rounds ``cell / 30``.
    """
    page = Image.new("RGB", (layout.width, layout.height), "white")
    draw = ImageDraw.Draw(page)
    cell_px = max(1, round(weights.cell_pt / PT_PER_PX))
    fifth_px = max(1, round(weights.fifth_pt / PT_PER_PX))
    border_px = max(1, round(weights.border_pt / PT_PER_PX))
    level = round(255 * weights.cell_grey)
    cell_ink = (level, level, level)

    verticals, horizontals = layout.vertical_lines, layout.horizontal_lines
    last_v, last_h = len(verticals) - 1, len(horizontals) - 1
    for index, line in enumerate(verticals):
        if not _is_fifth(index, last_v):
            draw.line(
                [(line.position, line.start), (line.position, line.end)],
                fill=cell_ink,
                width=cell_px,
            )
    for index, line in enumerate(horizontals):
        if not _is_fifth(index, last_h):
            draw.line(
                [(line.start, line.position), (line.end, line.position)],
                fill=cell_ink,
                width=cell_px,
            )
    for index, line in enumerate(verticals):
        if _is_fifth(index, last_v) and index not in (0, last_v):
            draw.line(
                [(line.position, line.start), (line.position, line.end)],
                fill="black",
                width=fifth_px,
            )
    for index, line in enumerate(horizontals):
        if _is_fifth(index, last_h) and index not in (0, last_h):
            draw.line(
                [(line.start, line.position), (line.end, line.position)],
                fill="black",
                width=fifth_px,
            )
    box = [
        (verticals[0].position, horizontals[0].position),
        (verticals[-1].position, horizontals[-1].position),
    ]
    draw.rectangle(box, outline="black", width=border_px)
    if layout.frame is not None:
        draw.rectangle(
            [
                (layout.frame.left, layout.frame.top),
                (layout.frame.right, layout.frame.bottom),
            ],
            outline="black",
            width=border_px,
        )
    _draw_raster_clues(draw, layout)
    return page


def _draw_raster_clues(draw: ImageDraw.ImageDraw, layout: Layout) -> None:
    from PIL import ImageFont

    face = ImageFont.truetype(str(FONT_PATH), layout.clue_font_size)
    for entry in layout.clue_entries:
        draw.text(
            (entry.center_x, entry.center_y),
            str(entry.value),
            font=face,
            fill="black",
            anchor="mm",
        )


# --------------------------------------------------------------------------
# The book this probe measures
# --------------------------------------------------------------------------


def book_layouts(source: str = "corpus", limit: int | None = 24) -> list[tuple[str, Layout]]:
    """Every puzzle page of the baseline book, as COMP-007 lays it out.

    Reached through the generator's own seams — ``cell_sizes`` and
    ``_puzzle_page_spec`` — so the cell is the book's (NFR-008/CARD-225) and
    not a per-puzzle fit. **No page plan is walked** (G-3): the puzzle page
    positions are read off the shipped ``puzzle_page_plan`` and nothing else
    about the interior is reconstructed.
    """
    from nonogram.admin.book_pdf_generator import (
        BookPDFGenerator,
        print_order,
        puzzle_page_plan,
    )

    from tests.helpers.book_corpus import baseline_puzzles, corpus_book, corpus_puzzles

    book = corpus_book()
    generator = BookPDFGenerator(book)
    puzzles = baseline_puzzles() if source == "baseline" else corpus_puzzles()
    if limit is not None:
        puzzles = puzzles[:limit]
    plan = puzzle_page_plan(book, puzzles)
    ordered = [BookPDFGenerator._payload(p) for p in print_order(puzzles)]
    sizes = generator.cell_sizes(ordered)

    out: list[tuple[str, Layout]] = []
    for entry in plan:
        if entry.is_two_up:
            # G-3: one page kind. A two-up slot is a PairLayout, not a Layout,
            # and pricing it would mean reimplementing the pair walk.
            continue
        payload = ordered[entry.numbers[0] - 1]
        spec = generator._puzzle_page_spec(
            entry.page_number, sizes[BookPDFGenerator._grid_size(payload)]
        )
        out.append(
            (
                f"{payload.width}x{payload.height} @ interior page {entry.page_number}",
                compute_layout(payload.row_clues, payload.column_clues, spec),
            )
        )
    return out


def _hero_layout() -> tuple[str, Layout]:
    """The 30x30 at the book's smallest cell — where a faint rule hurts most."""
    for name, layout in book_layouts("baseline", None):
        if layout.columns == 30:
            return name, layout
    raise RuntimeError("no 30x30 page in the baseline book")


def _arm_identity(layouts: Sequence[tuple[str, Layout]]) -> dict[str, Any]:
    """What this arm IS, printed before any result is read (G-4, CARD-292)."""
    from collections import Counter

    return {
        "pages": len(layouts),
        "grid_sizes": dict(
            sorted(Counter(f"{l.columns}x{l.rows}" for _, l in layouts).items())
        ),
        "first_page": layouts[0][0],
        "last_page": layouts[-1][0],
        "trim_px": [layouts[0][1].width, layouts[0][1].height],
        "dpi": layouts[0][1].dpi,
        "thin_thick_px": [layouts[0][1].thin_rule, layouts[0][1].thick_rule],
    }


def _sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()[:16]


def _loadavg() -> tuple[float, float, float]:
    import os

    return os.getloadavg()


# --------------------------------------------------------------------------
# Subcommands
# --------------------------------------------------------------------------


def cmd_font(args: argparse.Namespace) -> None:
    raw = FONT_PATH.read_bytes()
    digits = [ord(ch) for ch in "0123456789"]
    metrics = font_metrics(raw, range(32, 127))
    stripped = stripped_sfnt(raw)

    report: dict[str, Any] = {
        "font": str(FONT_PATH),
        "tables": sorted(sfnt_tables(raw)),
        "units_per_em": metrics.units_per_em,
        "ascent_descent_cap": [metrics.ascent, metrics.descent, metrics.cap_height],
        "digit_widths_1000": {chr(c): metrics.widths_1000[c] for c in digits},
        "bytes": {
            "whole_raw": len(raw),
            "whole_flate": len(zlib.compress(raw, 9)),
            "table_stripped_raw": len(stripped),
            "table_stripped_flate": len(zlib.compress(stripped, 9)),
            "one_raster_page_jpeg_typical": 460_000,
            "page_bitmap_bytes": PAGE_BITMAP_BYTES,
        },
    }

    # Prove a clue digit lands: one page, every digit, at the book's own size.
    name, layout = _hero_layout()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for label, font_bytes in (("whole", raw), ("stripped", stripped)):
        writer = VectorPdfWriter(dpi=layout.dpi, font_bytes=font_bytes, metrics=metrics)
        stream = page_stream(layout, CARD_227, metrics, band="Puzzle 1 . Hard", folio="7")
        buffer = writer.write([(layout, stream)])
        target = out / f"card293-font-{label}.pdf"
        target.write_bytes(buffer.getvalue())
        report.setdefault("written", {})[label] = {
            "path": str(target),
            "bytes": target.stat().st_size,
        }
    report["hero_page"] = name
    report["content_stream_bytes"] = len(stream)
    report["content_stream_flate"] = len(zlib.compress(stream, 9))
    report["metrics_parser_lines"] = _metrics_parser_lines()
    print(json.dumps(report, indent=2))


def _metrics_parser_lines() -> dict[str, int]:
    """How many lines of this file are the font job — AC-5's estimate basis."""
    text = Path(__file__).read_text().splitlines()

    def span(start: str, end: str) -> int:
        first = next(i for i, line in enumerate(text) if line.startswith(start))
        last = next(i for i, line in enumerate(text) if i > first and line.startswith(end))
        return sum(
            1
            for line in text[first:last]
            if line.strip() and not line.strip().startswith("#")
        )

    return {
        "sfnt_metrics_parser_code_lines": span("def sfnt_tables", "#: Tables a rasteriser"),
        "table_stripper_code_lines": span("def stripped_sfnt", "# ------"),
        "pdf_font_objects_code_lines": span("        first, last = 32", "        for index, ("),
        "text_operator_code_lines": span("    def text(", "    def stream("),
    }


def cmd_page(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw = FONT_PATH.read_bytes()
    metrics = font_metrics(raw, range(32, 127))
    layouts = book_layouts(args.book, args.limit)

    rows = []
    for name, layout in layouts:
        stream = page_stream(layout, CARD_227, metrics, band="Puzzle N . Tier", folio="7")
        vector = VectorPdfWriter(
            dpi=layout.dpi, font_bytes=raw, metrics=metrics
        ).write([(layout, stream)])
        image = raster_page(layout, SHIPPED_TODAY)
        raster = raster_pdf([image], layout.dpi, "L")
        rows.append(
            {
                "page": name,
                "columns": layout.columns,
                "vector_pdf_bytes": len(vector.getvalue()),
                "vector_stream_bytes": len(stream),
                "vector_stream_flate": len(zlib.compress(stream, 9)),
                "raster_pdf_bytes": len(raster.getvalue()),
            }
        )

    # The whole set in one file each, which is what a book's per-page cost is.
    streams = [
        (layout, page_stream(layout, CARD_227, metrics, band="Puzzle N . Tier", folio="7"))
        for _, layout in layouts
    ]
    whole_vector = VectorPdfWriter(dpi=300, font_bytes=raw, metrics=metrics).write(streams)
    images = [raster_page(layout, SHIPPED_TODAY) for _, layout in layouts]
    whole_raster = raster_pdf(images, 300, "L")
    (out / "card293-arm-vector.pdf").write_bytes(whole_vector.getvalue())
    (out / "card293-arm-raster.pdf").write_bytes(whole_raster.getvalue())

    font_cost = len(zlib.compress(raw, 9))
    print(
        json.dumps(
            {
                "arm_identity": _arm_identity(layouts),
                "per_page": rows,
                "all_pages": {
                    "pages": len(streams),
                    "vector_bytes": len(whole_vector.getvalue()),
                    "raster_bytes": len(whole_raster.getvalue()),
                    "vector_per_page": round(len(whole_vector.getvalue()) / len(streams)),
                    "raster_per_page": round(len(whole_raster.getvalue()) / len(streams)),
                    "vector_font_once_bytes": font_cost,
                    "vector_per_page_excluding_font": round(
                        (len(whole_vector.getvalue()) - font_cost) / len(streams)
                    ),
                    "vector_sha": _sha(whole_vector.getvalue()),
                    "raster_sha": _sha(whole_raster.getvalue()),
                },
                "written": [
                    str(out / "card293-arm-vector.pdf"),
                    str(out / "card293-arm-raster.pdf"),
                ],
            },
            indent=2,
        )
    )


def cmd_bench(args: argparse.Namespace) -> None:
    raw = FONT_PATH.read_bytes()
    metrics = font_metrics(raw, range(32, 127))
    layouts = book_layouts(args.book, args.limit)
    digests: dict[str, Any] = {}

    def arm_vector() -> str:
        streams = [
            (layout, page_stream(layout, CARD_227, metrics, band="Puzzle N . Tier", folio="7"))
            for _, layout in layouts
        ]
        buffer = VectorPdfWriter(dpi=300, font_bytes=raw, metrics=metrics).write(streams)
        data = buffer.getvalue()
        return f"{len(data)} B"

    def arm_raster() -> str:
        # Streamed, not listed — the shape CARD-145 ships, so the raster arm
        # retains one page bitmap and the two arms are compared at the same
        # memory shape as well as the same machine state.
        def pages() -> Iterable[Image.Image]:
            for _, layout in layouts:
                yield raster_page(layout, SHIPPED_TODAY)

        buffer = raster_pdf_streamed(pages(), len(layouts), 300, "L")
        data = buffer.getvalue()
        return f"{len(data)} B"

    load_start = _loadavg()
    runs: dict[str, list[float]] = {"vector": [], "raster": []}
    order: list[str] = []
    for _ in range(args.runs):
        for name, arm in (("vector", arm_vector), ("raster", arm_raster)):
            start = time.perf_counter()
            size = arm()
            runs[name].append(round(time.perf_counter() - start, 4))
            digests.setdefault(name, size)
            order.append(name)
    load_end = _loadavg()

    print(
        json.dumps(
            {
                "arm_identity": _arm_identity(layouts),
                "arm_output": digests,
                "order": order,
                "raw_seconds": runs,
                "min": {k: round(min(v), 4) for k, v in runs.items()},
                "median": {k: round(statistics.median(v), 4) for k, v in runs.items()},
                "loadavg_start": load_start,
                "loadavg_end": load_end,
            },
            indent=2,
        )
    )


def cmd_mem(args: argparse.Namespace) -> None:
    """One arm, end to end, so ``/usr/bin/time -l`` can wrap the process.

    Peak RSS is the weak instrument CARD-218 caught lying (it measured a
    192.6 MiB retention *removed* while the peak went up — the figure is
    allocation-order dependent). The exact figure is the **retention**, and
    this command reports it as the project's own ``PAGE_BITMAP_BYTES``: the
    raster arm holds one page bitmap by construction (CARD-145), the vector
    arm holds a content stream and no bitmap at all.
    """
    raw = FONT_PATH.read_bytes()
    metrics = font_metrics(raw, range(32, 127))
    layouts = book_layouts(args.book, args.limit)
    if args.arm == "vector":
        streams = [
            (layout, page_stream(layout, CARD_227, metrics, band="Puzzle N . Tier", folio="7"))
            for _, layout in layouts
        ]
        size = len(VectorPdfWriter(dpi=300, font_bytes=raw, metrics=metrics).write(streams).getvalue())
        held = max(len(stream) for _, stream in streams)
    else:
        def pages() -> Iterable[Image.Image]:
            for _, layout in layouts:
                yield raster_page(layout, SHIPPED_TODAY)

        size = len(raster_pdf_streamed(pages(), len(layouts), 300, "L").getvalue())
        held = PAGE_BITMAP_BYTES
    print(
        json.dumps(
            {
                "arm": args.arm,
                "pages": len(layouts),
                "output_bytes": size,
                "largest_page_artefact_held_bytes": held,
                "in_page_bitmaps": round(held / PAGE_BITMAP_BYTES, 6),
            }
        )
    )


def cmd_proof(args: argparse.Namespace) -> None:
    """AC-2 — the owner's weights beside every raster reading of them."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw = FONT_PATH.read_bytes()
    metrics = font_metrics(raw, range(32, 127))
    name, layout = _hero_layout()

    arms = [
        ("vector", OWNER),
        ("vector", CARD_227),
        ("raster", OWNER),
        ("raster", CARD_227),
        ("raster", SHIPPED_TODAY),
    ]
    written = []
    vector_pages: list[tuple[Layout, bytes]] = []
    raster_images: list[Image.Image] = []
    for kind, weights in arms:
        caption = f"{kind} . {weights.label}"
        if kind == "vector":
            vector_pages.append((layout, page_stream(layout, weights, metrics, band=caption, folio=name)))
        else:
            image = raster_page(layout, weights)
            raster_images.append(image)
            crop = image.crop(
                (
                    layout.grid_left - 20,
                    layout.grid_top - 20,
                    layout.grid_left + 12 * layout.cell,
                    layout.grid_top + 12 * layout.cell,
                )
            )
            target = out / f"card293-detail-raster-{_slug(weights.label)}.png"
            crop.save(target, dpi=(300, 300))
            written.append(str(target))

    vector_pdf = VectorPdfWriter(dpi=300, font_bytes=raw, metrics=metrics).write(vector_pages)
    (out / "card293-proof-vector.pdf").write_bytes(vector_pdf.getvalue())
    raster_pdf_buffer = raster_pdf(raster_images, 300, "L")
    (out / "card293-proof-raster.pdf").write_bytes(raster_pdf_buffer.getvalue())
    written += [str(out / "card293-proof-vector.pdf"), str(out / "card293-proof-raster.pdf")]

    print(
        json.dumps(
            {
                "page": name,
                "cell_px": layout.cell,
                "weights": [
                    {
                        "kind": kind,
                        "label": w.label,
                        "cell_pt": w.cell_pt,
                        "cell_mm": round(w.cell_pt * 25.4 / 72, 4),
                        "cell_px_rounded": max(1, round(w.cell_pt / PT_PER_PX)),
                        "fifth_px_rounded": max(1, round(w.fifth_pt / PT_PER_PX)),
                        "border_px_rounded": max(1, round(w.border_pt / PT_PER_PX)),
                    }
                    for kind, w in arms
                ],
                "written": written,
            },
            indent=2,
        )
    )


def cmd_sheet(args: argparse.Namespace) -> None:
    """AC-2's side-by-side: the same grid corner, four ways, at 1:1 300 DPI.

    The two vector panels are rasterised by **poppler** (``pdftoppm``), not by
    anything in this repo — an independent renderer, so "the PDF says 0.3 pt"
    is checked by something that did not write the PDF. Poppler is an
    inspection tool here and no part of the proposal; if it is missing the
    two vector panels are skipped and the command says so.
    """
    import shutil
    import subprocess

    out = Path(args.out)
    vector_pdf = out / "card293-proof-vector.pdf"
    raster_pdf_path = out / "card293-proof-raster.pdf"
    if not vector_pdf.exists():
        raise SystemExit("run `proof` first")

    _name, layout = _hero_layout()
    cells = 9
    box = (
        layout.grid_left - 6,
        layout.grid_top - 6,
        layout.grid_left + cells * layout.cell,
        layout.grid_top + cells * layout.cell,
    )
    panels: list[tuple[str, Image.Image]] = []

    raster_pages = _pdf_pages(raster_pdf_path.read_bytes())
    panels.append(("raster 300 DPI - SHIPPED TODAY 3/6 px", raster_pages[2].crop(box)))
    panels.append(("raster 300 DPI - owner 0.3/0.8/1.3 pt -> 1/3/5 px", raster_pages[0].crop(box)))

    poppler = shutil.which("pdftoppm")
    if poppler:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            for dpi, label in ((300, "vector @ 300 DPI (device floor)"), (1200, "vector @ 1200 DPI (press RIP)")):
                stem = Path(tmp) / f"v{dpi}"
                subprocess.run(
                    [poppler, "-r", str(dpi), "-png", "-f", "1", "-l", "1", "-singlefile",
                     str(vector_pdf), str(stem)],
                    check=True,
                )
                image = Image.open(stem.with_suffix(".png")).convert("L")
                scale = dpi // 300
                crop = image.crop(tuple(value * scale for value in box))
                if scale != 1:
                    crop = crop.resize((crop.width // scale, crop.height // scale), Image.LANCZOS)
                panels.append((f"{label} - owner 0.3/0.8/1.3 pt", crop))
    else:
        print("pdftoppm not found: the two vector panels are skipped", file=sys.stderr)

    from PIL import ImageFont

    face = ImageFont.truetype(str(FONT_PATH), 26)
    cell_w, cell_h = panels[0][1].size
    gap, caption = 60, 80
    sheet = Image.new(
        "L", (cell_w * 2 + gap * 3, (cell_h + caption) * 2 + gap * 3), 255
    )
    draw = ImageDraw.Draw(sheet)
    for index, (label, panel) in enumerate(panels):
        col, row = index % 2, index // 2
        x = gap + col * (cell_w + gap)
        y = gap + row * (cell_h + caption + gap)
        words, line, lines = label.split(), "", []
        for word in words:
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=face) > cell_w and line:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
        for offset, text in enumerate(lines[:2]):
            draw.text((x, y + offset * 32), text, font=face, fill=0)
        sheet.paste(panel.convert("L"), (x, y + caption))
    target = out / "card293-AC2-side-by-side.png"
    sheet.save(target, dpi=(300, 300))
    pdf_target = out / "card293-AC2-side-by-side.pdf"
    sheet.save(pdf_target, "PDF", resolution=300.0)
    print(json.dumps({"panels": [label for label, _ in panels],
                      "written": [str(target), str(pdf_target)]}, indent=2))


def _pdf_pages(data: bytes) -> list[Image.Image]:
    """Every page of a raster PDF, as images — ``tests/helpers/pdf_pages.py``'s job."""
    from tests.helpers.pdf_pages import pdf_pages

    return list(pdf_pages(data))


def _slug(text: str) -> str:
    keep = [ch if ch.isalnum() else "-" for ch in text.lower()]
    return "".join(keep).strip("-").replace("----", "-").replace("---", "-").replace("--", "-")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(Path.home() / "Documents" / "nonogram-reviews" / "CARD-293"),
        help="where renders go (never beside the repo)",
    )
    parser.add_argument("--book", choices=("baseline", "corpus"), default="corpus")
    parser.add_argument("--limit", type=int, default=24)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("font").set_defaults(func=cmd_font)
    sub.add_parser("page").set_defaults(func=cmd_page)
    bench = sub.add_parser("bench")
    bench.add_argument("--runs", type=int, default=5)
    bench.set_defaults(func=cmd_bench)
    mem = sub.add_parser("mem")
    mem.add_argument("arm", choices=("vector", "raster"))
    mem.set_defaults(func=cmd_mem)
    sub.add_parser("proof").set_defaults(func=cmd_proof)
    sub.add_parser("sheet").set_defaults(func=cmd_sheet)
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
