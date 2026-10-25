"""The book interior's drawing vocabulary: an embedded face and an operator set.

CARD-294, the first implementation of **ADR-0042** (DEC-048 — the book
interior is drawn as PDF content-stream operators and the cover stays
raster).

**This module draws no page.** It is a vocabulary: a content stream that
accumulates operators it is handed, the three PDF objects that embed the
project's own face, and the writer that puts them into a file. Puzzle pages,
answer pages, the guide and the table of contents are CARD-295, CARD-296 and
CARD-297, and each *consumes* what is here. Nothing in this file knows what a
puzzle is.

Why it exists as its own module rather than as more of
:mod:`nonogram.admin.book_pdf_generator`: that file is 7,000 lines and every
card in this phase touches it. A vocabulary with no page knowledge is the one
piece of the phase that can be read, and tested, on its own. It is placed
*beside* ``book_pdf_generator.py`` deliberately, so CARD-273's move of nine
modules to ``src/nonogram/book/`` stays one mechanical ``git mv``.

What is deliberately **not** here
---------------------------------

* **Geometry** (ADR-0042/R3, restating ADR-0036/R2). Every coordinate, every
  stroke width and every tone is an argument. This module computes no
  position, no size and no colour of its own. The one piece of arithmetic
  that looks like an exception is :meth:`ContentStream.round_mark`'s Bézier
  control points, and it is not one: :data:`BEZIER_CIRCLE_KAPPA` is a
  property of the *approximation* — the single number that makes four cubics
  pass through a circle's four quadrant points with matching tangents — not a
  design decision about how big a dot is. The caller still states the centre
  and the radius.

* **Glyph subsetting** (ADR-0042/R5). The whole face is embedded. It
  Flate-compresses to less than one raster page, which is the measurement the
  decision rests on; see
  ``meta/profiling/card-293-vector-interior-comparison.md`` §1.

* **A base-14 substitute** (ADR-0042/R5), because every type measurement in
  this tree — ``type_px``, ``_band_font``, ``_guide_face``, CON-020's 10 pt
  floor — is DejaVu's.

* **A new dependency** (ADR-0042/R4, ADR-0006/R1). The sfnt reader below is
  ``struct`` over five tables, the PDF object structure is the one
  ``book_pdf_generator._write_pdf`` has driven through :mod:`PIL.PdfParser`
  by hand since CARD-145, and the face arrives as *package data* through the
  same ``FONT_PACKAGE``/``FONT_RESOURCE`` pair :mod:`nonogram.export.pdf`
  publishes. There is deliberately no second path to that file.

Units, which are the thing to get right
---------------------------------------

A PDF page is measured in **points** (1/72 in) and COMP-007's ``Layout`` is
measured in **device pixels** at the book's DPI. Both appear here, and which
is which is never implicit:

* **Type size is always points** (:meth:`ContentStream.text` takes
  ``size_pt``), so the operand of ``Tf`` is the physical size and a page
  written at another DPI carries the same type. This is AC-4, and
  ``tests/test_book_pdf_vector_primitives.py``'s
  ``TestVectorPrimitives_PointSizeIsIndependentOfDpi`` is its control.
* **Stroke width is always points** (:meth:`ContentStream.stroke_width`),
  because ADR-0037/R2's weights — the owner's 0.3 / 0.8 / 1.3 pt — are
  stated in points and a content-stream line has no device pixel to clear.
* **Positions are device pixels**, converted on the way out by the stream's
  own DPI, because that is the unit the ``Layout`` a caller is handed speaks.
  :meth:`ContentStream.to_points` is the conversion, exposed so a caller that
  already holds points can say so.

The y axis is flipped on the way out: a ``Layout`` counts rows down from the
page's top edge and a PDF counts up from its foot.

**CON-020's 10 pt floor is deliberately not enforced here**, and the reason is
the same one G-5 gives: this vocabulary emits what it is handed. The floor is a
rule about what a *page* shows a reader — with clue digits excepted, which is a
distinction only a page card can make, since this module cannot tell a clue
digit from a folio. What this module owes the floor is a readable operand, and
that is what :meth:`ContentStream.text` provides: an explicit ``Tf`` in points
on every text object, which is what CARD-299's rewritten
``TestInteriorType_EveryFaceHoldsTheFloor`` reads instead of spying on
``draw.text``.
"""

from __future__ import annotations

import struct
import time
import zlib
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from io import BytesIO
from math import sqrt
from typing import Any, Iterable, Iterator, Mapping

from PIL import PdfParser

from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE

__all__ = [
    "BASE_14_FACES",
    "BEZIER_CIRCLE_KAPPA",
    "ContentStream",
    "FontMetrics",
    "POINTS_PER_INCH",
    "REFUSED_BY_WINANSI",
    "SFNT_TRUETYPE_VERSIONS",
    "TEXT_ENCODING",
    "WINANSI_DIVERGENCES",
    "ContentStreamError",
    "UnrepresentableText",
    "FACE_BASE_FONT",
    "FACE_RESOURCE_NAME",
    "ROUND_MARK_OPERATORS",
    "encode_text",
    "font_metrics",
    "interior_face_bytes",
    "interior_face_metrics",
    "write_vector_pdf",
]

#: One PDF point is 1/72 in. The page's own unit.
POINTS_PER_INCH = 72.0

#: The Python codec the interior's text is encoded with, and the one the
#: embedded face's ``/WinAnsiEncoding`` is read against. The byte a character
#: takes in a content stream is ``chr.encode(TEXT_ENCODING)`` and nothing is
#: hand-tabulated: the codec is the authority (ADR-0039/R2 — a guard's set
#: comes from an enumerable authority, and a character the codec cannot
#: represent is a loud failure rather than a silent ``.notdef`` box).
#:
#: **CP-1252 is ``/WinAnsiEncoding`` at every code except two**, and the
#: earlier spelling of this comment — "``WinAnsiEncoding`` *is* CP-1252" —
#: was measured false in review cycle 1. The exceptions are
#: :data:`WINANSI_DIVERGENCES`, and one of them prints ink, so the
#: divergence is not cosmetic. See :func:`encode_text`, which refuses the
#: inking one.
TEXT_ENCODING = "cp1252"

#: Where CP-1252 and ``/WinAnsiEncoding`` name different glyphs for the same
#: byte: ``{byte code: (the codec's character, WinAnsi's glyph name)}``.
#:
#: **Two explicit members with reasons, not a derived set**, because the
#: authority is PDF 1.7 **Annex D.2**'s encoding table and no codec in the
#: stdlib carries it — there is nothing to enumerate against. The honest
#: shape for that is the one ``tests/test_guard_integrity.py`` uses for its
#: own non-enumerable half: name the members, give each a reason, and give
#: each a control.
#:
#: * ``0xA0`` — the codec says U+00A0 NO-BREAK SPACE, WinAnsi says ``space``.
#:   **Inkless either way**: both glyphs set blank, and the face gives them
#:   the same advance, which
#:   ``test_the_one_divergence_that_inks_nothing_really_inks_nothing``
#:   measures off :func:`interior_face_metrics` rather than asserting from
#:   this comment. Accepted.
#: * ``0xAD`` — the codec says U+00AD SOFT HYPHEN, WinAnsi says ``hyphen``.
#:   **A conforming viewer therefore prints a visible hyphen for a character
#:   that is invisible in the source string**, which is neither a refusal nor
#:   a faithful rendering, and is ink that cannot be fixed after the book is
#:   printed — the whole of :class:`UnrepresentableText`'s rationale.
#:   :func:`encode_text` refuses it.
#: ``{byte code: (the codec's character, WinAnsi's glyph name, WinAnsi inks
#: where the codec does not)}``.
WINANSI_DIVERGENCES = {
    0xA0: ("\u00a0", "space", False),
    0xAD: ("\u00ad", "hyphen", True),
}

#: ``{character: the WinAnsi glyph it would print as}`` for the inking half
#: of :data:`WINANSI_DIVERGENCES`, derived from that mapping rather than
#: restated so the two cannot drift apart.
_REFUSED_GLYPH = {
    character: glyph for character, glyph, inks in WINANSI_DIVERGENCES.values() if inks
}

#: The characters :func:`encode_text` refuses although :data:`TEXT_ENCODING`
#: can carry them.
REFUSED_BY_WINANSI = frozenset(_REFUSED_GLYPH)

#: The resource name the font dictionary is reachable by inside a page's
#: ``/Resources``. One face, one name; the page cards do not get to choose it,
#: because ``Tf`` operands are what CON-020's rewritten floor check reads
#: (CARD-299) and a second spelling would be a second thing to read.
FACE_RESOURCE_NAME = "F1"

#: The PostScript name the embedded face is written under.
FACE_BASE_FONT = "DejaVuSans"

#: The fourteen faces every PDF viewer carries, which ADR-0042/R5 forbids this
#: interior from referencing. Written out because the prohibition needs a set
#: to check against: a page whose ``BaseFont`` is one of these is not setting
#: DejaVu's measurements, whatever the rest of the file says. (PDF 1.7,
#: §9.6.2.2 "Standard Type 1 Fonts"; the four Helvetica and four Times styles,
#: the four Courier styles, Symbol and ZapfDingbats.)
BASE_14_FACES = frozenset(
    {
        "Courier",
        "Courier-Bold",
        "Courier-BoldOblique",
        "Courier-Oblique",
        "Helvetica",
        "Helvetica-Bold",
        "Helvetica-BoldOblique",
        "Helvetica-Oblique",
        "Symbol",
        "Times-Bold",
        "Times-BoldItalic",
        "Times-Italic",
        "Times-Roman",
        "ZapfDingbats",
    }
)

#: The sfnt version tags that mean "this face has TrueType outlines", which
#: is the only kind ``/FontFile2`` may carry (PDF 1.7 §9.9, Table 126).
#: ``\x00\x01\x00\x00`` is the usual tag and ``true`` is the one older Apple
#: tools wrote; ``OTTO`` (CFF outlines) and ``ttcf`` (a collection) are
#: deliberately **not** here — see :func:`_sfnt_tables`, which refuses them.
SFNT_TRUETYPE_VERSIONS = frozenset({b"\x00\x01\x00\x00", b"true"})

#: The control-point offset, as a fraction of the radius, that makes four
#: cubic Béziers approximate a circle.
#:
#: PDF has no circle primitive — PostScript's ``arc`` does not survive into a
#: content stream — so a round mark is four ``c`` operators, one per quadrant,
#: each running between two quadrant points with its control points pushed
#: ``kappa * r`` along the tangent. ``kappa = 4 * (sqrt(2) - 1) / 3`` is the
#: value that makes each cubic pass **exactly** through the circle at its own
#: midpoint, which is what makes the mark's bounding box exactly the declared
#: diameter.
#:
#: **Spelled as the expression rather than as a decimal literal** so the
#: derivation is in the file and a transcription cannot drift. What the
#: approximation costs is measured, not assumed:
#: ``scripts/card294_curve_price.py`` reports the worst radial error over a
#: dense sweep of the curve, and
#: ``tests/test_book_pdf_vector_primitives.py``'s
#: ``TestVectorPrimitives_TheRoundMarkIsAccurateAtThePrintedDotSize``
#: re-derives it with its own sampler and holds it against the dot sizes
#: ``nonogram.export.layout.difficulty_dots`` really produces.
#:
#: **Measured, and it is not the figure usually quoted.** Over a 2,000,001-point
#: sweep of one quadrant the radial error is ``+2.7253e-4`` of the radius at
#: worst and **never negative**: the curve bulges very slightly *outside* the
#: true circle and touches it exactly at eight places (the four quadrant
#: points and the four curve midpoints), so a mark is never drawn smaller
#: than it was asked for. The 1.96e-4 figure that circulates for this
#: approximation belongs to a *different* kappa — 0.5519150244935105, which
#: minimises the maximum error by letting it alternate in sign — and taking
#: it would cost the exact diameter. Exactness of the stated diameter is
#: worth more here, because ``difficulty_dots`` states a diameter and
#: ``DifficultyDots.__post_init__`` reasons about whether two dots touch.
BEZIER_CIRCLE_KAPPA = 4.0 * (sqrt(2.0) - 1.0) / 3.0

#: How many operators one round mark costs, and what they are: a ``m``, four
#: ``c``, a ``h`` and one paint operator. Stated here because AC-3 is a price
#: and a price nobody can check is a rumour —
#: ``test_a_round_mark_is_one_moveto_four_curves_a_close_and_a_paint``
#: tokenises the emitted stream and counts them.
ROUND_MARK_OPERATORS = 7

#: How many decimal places a coordinate or a width is written with. Three is
#: 1/1000 pt — 0.00035 mm, finer than any press — and it keeps the stream
#: short, which is most of why a vector page is 321x smaller than a raster one
#: per page.
#:
#: **It is also the term that limits a small round mark**, not the Bézier
#: approximation: measured on the emitted operands, the worst radial error at
#: the 1.0 mm floor dot is 3.457e-4 of the radius against the approximation's
#: own 2.7253e-4, because at a 0.5 mm radius this rounding stops being
#: negligible beside it. A card that wants a rounder mark spends a place here,
#: not a better :data:`BEZIER_CIRCLE_KAPPA`. See
#: ``meta/profiling/card-294-curve-price.md`` §4.
_PLACES = 3


class ContentStreamError(Exception):
    """A content stream could not be written as asked.

    Its own small hierarchy rather than a reach into
    :mod:`nonogram.errors`: that module is the *domain's* flat exception tree,
    shared by the capability modules under CLAUDE.md's layering rule, and a
    malformed drawing instruction is not a domain error a CLI exit code is
    mapped from. It is a programming mistake in a page card.
    """


class UnrepresentableText(ContentStreamError):
    """Text was asked for that the declared encoding cannot carry.

    Raised rather than substituted, because the substitute is a ``.notdef``
    box on a printed page — the exact defect
    ``nonogram.export.png._lettering_font_bytes`` exists to stop, and one that
    cannot be fixed after the book is printed.
    """


# --------------------------------------------------------------------------
# The embedded face: the sfnt metrics a PDF font dictionary has to state
# --------------------------------------------------------------------------
# No stdlib module parses sfnt, so this is `struct` over five tables. It is
# the whole of ADR-0042/R5's cost, and CARD-293 priced it at 105 lines before
# anyone wrote it for keeps (comparison document, §1).


@dataclass(frozen=True)
class FontMetrics:
    """Everything a PDF ``/Font`` and ``/FontDescriptor`` have to state.

    Widths are in 1000ths of an em, which is PDF's glyph-space unit, and are
    keyed by the **byte** a character takes in :data:`TEXT_ENCODING` rather
    than by its codepoint — because ``/Widths`` is an array indexed from
    ``FirstChar``, and the encoding is what turns a character into an index.
    """

    units_per_em: int
    bbox: tuple[int, int, int, int]
    ascent: int
    descent: int
    cap_height: int
    #: ``{byte code: advance width in 1000ths of an em}``, for 32..255.
    widths_1000: Mapping[int, int]
    #: The first and last byte code :attr:`widths_1000` covers, inclusive.
    first_char: int
    last_char: int

    def advance(self, text: str) -> float:
        """How wide ``text`` sets, in ems.

        The sum of the advances, with no kerning and no shaping: the embedded
        face is declared ``/TrueType`` with ``/WinAnsiEncoding``, for which a
        viewer consults neither ``GPOS`` nor ``kern``. So this is the width
        the viewer will use, not an estimate of it — which is what lets a
        caller centre a string without either side knowing the other's
        rasteriser.

        **That claim has a control that can fail, and did not until review
        cycle 1 said so.** :attr:`widths_1000` and the PDF ``/Widths`` array
        are built from the same dictionary, so a poppler render laid out from
        the emitted ``/Widths`` agrees with :meth:`advance` whatever this
        reader got wrong — measured: every width replaced by a constant 600
        left the whole claim-bearing suite green. The second, independent
        implementation is FreeType, reached through
        :mod:`PIL.ImageFont` — already in the dependency baseline, so no
        revisit of ADR-0006/R1 — and
        ``TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader`` holds all
        219 encoded codes against it.
        """
        return sum(self.widths_1000.get(byte, 0) for byte in encode_text(text)) / 1000.0


def _sfnt_tables(data: bytes) -> dict[str, tuple[int, int]]:
    """``{tag: (offset, length)}`` for every table in ``data``.

    Three things are checked, because review cycle 1 measured what happens
    without them, and two of the three answers were worse than a crash:

    * the **sfnt version tag**. A face tagged ``OTTO`` — CFF outlines — read
      through here produced entirely plausible metrics and was then embedded
      as ``/FontFile2``, which carries TrueType outlines only: a
      spec-invalid file written with no complaint at all.
    * the **table directory's own self-consistency**. ``searchRange``,
      ``entrySelector`` and ``rangeShift`` are each a function of
      ``numTables`` (sfnt spec, the offset table), so they are *derived and
      compared* rather than skipped — which is the only cheap way to notice
      an inflated count. With the bundled face's 20 tables rewritten to
      5000, nothing complained and the metrics came back unchanged.
    * every table's **extent**. A face truncated to 2 KB kept a directory
      that parsed and offsets that pointed past the end, so the failure
      arrived as a raw :exc:`struct.error` from inside this module's private
      parsing rather than as its own declared error type.

    Raises:
        ContentStreamError: any of the three.
    """
    if len(data) < 12:
        raise ContentStreamError(
            f"the face is {len(data)} bytes, too short to hold an sfnt header"
        )
    version = data[:4]
    if version not in SFNT_TRUETYPE_VERSIONS:
        raise ContentStreamError(
            f"the face's sfnt version is {version!r}, not one of "
            f"{sorted(SFNT_TRUETYPE_VERSIONS)} — /FontFile2 carries TrueType "
            f"outlines only, and a CFF face ('OTTO') belongs in /FontFile3"
        )
    count, search_range, entry_selector, range_shift = struct.unpack(">HHHH", data[4:12])
    if count == 0:
        raise ContentStreamError("the face declares no tables")
    selector = count.bit_length() - 1
    expected = (2**selector * 16, selector, count * 16 - 2**selector * 16)
    if (search_range, entry_selector, range_shift) != expected:
        raise ContentStreamError(
            f"the face declares {count} tables but its offset table's "
            f"(searchRange, entrySelector, rangeShift) is "
            f"{(search_range, entry_selector, range_shift)} where {count} "
            f"tables derive {expected} — the directory is not self-consistent"
        )
    if len(data) < 12 + 16 * count:
        raise ContentStreamError(
            f"the face declares {count} tables, which its {len(data)} bytes "
            f"cannot hold"
        )
    tables: dict[str, tuple[int, int]] = {}
    for index in range(count):
        base = 12 + 16 * index
        tag, _checksum, offset, length = struct.unpack(">4sIII", data[base : base + 16])
        if offset + length > len(data):
            raise ContentStreamError(
                f"the face's {tag.decode('latin-1')!r} table runs to "
                f"{offset + length} bytes in a face of {len(data)}"
            )
        tables[tag.decode("latin-1")] = (offset, length)
    return tables


def _table(tables: Mapping[str, tuple[int, int]], tag: str) -> tuple[int, int]:
    """``tables[tag]``, as a :class:`ContentStreamError` rather than a KeyError.

    The tag is named in the message, because "which table is missing" is the
    whole of what a reader of a malformed face needs to be told.
    """
    try:
        return tables[tag]
    except KeyError:
        raise ContentStreamError(f"the face carries no {tag!r} table") from None


def _cmap_format_4(data: bytes, offset: int) -> dict[int, int]:
    """A format-4 ``cmap`` subtable as ``{codepoint: glyph id}``."""
    seg_x2 = struct.unpack(">H", data[offset + 6 : offset + 8])[0]
    segments = seg_x2 // 2
    ends = struct.unpack(f">{segments}H", data[offset + 14 : offset + 14 + seg_x2])
    start_at = offset + 16 + seg_x2
    starts = struct.unpack(f">{segments}H", data[start_at : start_at + seg_x2])
    delta_at = start_at + seg_x2
    deltas = struct.unpack(f">{segments}h", data[delta_at : delta_at + seg_x2])
    range_at = delta_at + seg_x2
    offsets = struct.unpack(f">{segments}H", data[range_at : range_at + seg_x2])
    mapping: dict[int, int] = {}
    for index in range(segments):
        for code in range(starts[index], min(ends[index], 0xFFFF) + 1):
            if offsets[index] == 0:
                glyph = (code + deltas[index]) & 0xFFFF
            else:
                at = range_at + index * 2 + offsets[index] + (code - starts[index]) * 2
                glyph = struct.unpack(">H", data[at : at + 2])[0]
                if glyph:
                    glyph = (glyph + deltas[index]) & 0xFFFF
            if glyph:
                mapping[code] = glyph
    return mapping


def _unicode_cmap(data: bytes) -> dict[int, int]:
    """The Windows/Unicode BMP ``cmap`` — the one a ``/TrueType`` font uses."""
    offset, _ = _table(_sfnt_tables(data), "cmap")
    count = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
    chosen: int | None = None
    for index in range(count):
        base = offset + 4 + 8 * index
        platform, encoding, subtable = struct.unpack(">HHI", data[base : base + 8])
        if (platform, encoding) in {(3, 1), (0, 3), (0, 4)}:
            chosen = offset + subtable
            break
    if chosen is None:
        raise ContentStreamError("the bundled face carries no Windows/Unicode BMP cmap")
    if struct.unpack(">H", data[chosen : chosen + 2])[0] != 4:
        raise ContentStreamError("the bundled face's Unicode cmap is not format 4")
    return _cmap_format_4(data, chosen)


def _advances(data: bytes) -> list[int]:
    """Every glyph's advance width in font units, from ``hhea``/``hmtx``.

    ``hmtx`` holds ``numberOfHMetrics`` full records and then relies on the
    last one for every glyph after it — monospaced tails are stored once — so
    the list is extended rather than indexed short.
    """
    tables = _sfnt_tables(data)
    hhea, _ = _table(tables, "hhea")
    recorded = struct.unpack(">H", data[hhea + 34 : hhea + 36])[0]
    maxp, _ = _table(tables, "maxp")
    glyphs = struct.unpack(">H", data[maxp + 4 : maxp + 6])[0]
    hmtx, _ = _table(tables, "hmtx")
    widths = [
        struct.unpack(">H", data[hmtx + 4 * index : hmtx + 4 * index + 2])[0]
        for index in range(recorded)
    ]
    widths.extend([widths[-1]] * (glyphs - recorded))
    return widths


def _encoded_codepoints() -> dict[int, int]:
    """``{byte code: codepoint}`` for every byte :data:`TEXT_ENCODING` defines.

    Derived from the codec, never tabulated. CP-1252 leaves five bytes in
    ``0x80..0x9F`` undefined; those are simply absent here, and a width array
    entry of 0 is what a viewer gets for them — which is correct, because no
    text can contain them (:func:`encode_text` cannot produce one).
    """
    mapping: dict[int, int] = {}
    for code in range(32, 256):
        try:
            mapping[code] = ord(bytes([code]).decode(TEXT_ENCODING))
        except UnicodeDecodeError:
            continue
    return mapping


def encode_text(value: str) -> bytes:
    """``value`` as the bytes a content stream shows it with.

    Raises:
        UnrepresentableText: ``value`` holds a character
            :data:`TEXT_ENCODING` cannot carry, **or** one of
            :data:`REFUSED_BY_WINANSI` — a character the codec carries
            happily and ``/WinAnsiEncoding`` then sets as different, inking
            glyph. Loudly, and with the character named: the alternative is
            ink on a printed page that nobody asked for.
    """
    for character in value:
        glyph = _REFUSED_GLYPH.get(character)
        if glyph is not None:
            raise UnrepresentableText(
                f"{character!r} (U+{ord(character):04X}) encodes to the byte "
                f"/WinAnsiEncoding sets as {glyph!r}, so it would print "
                f"visible ink the caller did not ask for"
            )
    try:
        return value.encode(TEXT_ENCODING)
    except UnicodeEncodeError as problem:
        bad = value[problem.start : problem.end]
        raise UnrepresentableText(
            f"{bad!r} (U+{ord(bad[0]):04X}) is not in the interior's "
            f"{TEXT_ENCODING} encoding, so it would print as a .notdef box"
        ) from problem


def _cap_height(data: bytes, cmap: Mapping[int, int]) -> int:
    """The top of this face's flat capitals, in font units.

    ``OS/2``'s ``sCapHeight`` when the table carries it (version 2 and up),
    and otherwise the ``yMax`` of the ``H`` glyph's own bounding box — which
    is what "the vertical coordinate of the top of flat capital letters"
    (PDF 1.7, Table 122) means, read rather than guessed.

    **The guess it replaces was measured wrong.** The bundled DejaVuSans
    ships an ``OS/2`` **version 1** table, 86 bytes long, with no
    ``sCapHeight`` at all, so the value this function returns is always the
    fallback for the face this interior actually embeds. The previous
    fallback — seven tenths of the ascender, the usual rule of thumb — gives
    650/1000 em against the 729/1000 em FreeType measures for the same face,
    **10.8 % low**; the 0.15 relative tolerance of
    ``test_the_text_is_inked_on_the_baseline_the_writer_named`` absorbed it,
    which is how it survived round 1. ``H``'s ``yMax`` reproduces FreeType's
    figure exactly, and
    ``TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader`` is where that
    agreement is asserted against an engine that did not write this reader.

    Raises:
        ContentStreamError: the face has neither an ``sCapHeight`` nor an
            ``H`` with an outline. A descriptor cannot state a cap height it
            does not have, and guessing one is what this function exists to
            stop.
    """
    tables = _sfnt_tables(data)
    os2, length = _table(tables, "OS/2")
    if struct.unpack(">H", data[os2 : os2 + 2])[0] >= 2 and length >= 90:
        return struct.unpack(">h", data[os2 + 88 : os2 + 90])[0]
    glyph = cmap.get(ord("H"))
    if glyph is None:
        raise ContentStreamError(
            "the face has no OS/2 sCapHeight and no 'H', so no cap height "
            "can be read from it"
        )
    head, _ = _table(tables, "head")
    long_loca = struct.unpack(">h", data[head + 50 : head + 52])[0] == 1
    loca, _ = _table(tables, "loca")
    if long_loca:
        at = loca + 4 * glyph
        start, end = struct.unpack(">II", data[at : at + 8])
    else:
        at = loca + 2 * glyph
        short_start, short_end = struct.unpack(">HH", data[at : at + 4])
        start, end = short_start * 2, short_end * 2
    if end <= start:
        raise ContentStreamError("the face's 'H' has no outline to measure")
    glyf, _ = _table(tables, "glyf")
    return struct.unpack(">h", data[glyf + start + 8 : glyf + start + 10])[0]


def font_metrics(data: bytes) -> FontMetrics:
    """Read ``data``'s tables into what a PDF font dictionary states."""
    tables = _sfnt_tables(data)
    head, _ = _table(tables, "head")
    upem = struct.unpack(">H", data[head + 18 : head + 20])[0]
    box = struct.unpack(">hhhh", data[head + 36 : head + 44])
    hhea, _ = _table(tables, "hhea")
    ascent, descent = struct.unpack(">hh", data[hhea + 4 : hhea + 8])
    cmap = _unicode_cmap(data)
    cap = _cap_height(data, cmap)
    advances = _advances(data)
    scale = 1000.0 / upem
    encoded = _encoded_codepoints()
    first, last = 32, 255
    widths = {
        code: round(advances[cmap.get(point, 0)] * scale)
        for code, point in encoded.items()
    }
    return FontMetrics(
        units_per_em=upem,
        bbox=(
            round(box[0] * scale),
            round(box[1] * scale),
            round(box[2] * scale),
            round(box[3] * scale),
        ),
        ascent=round(ascent * scale),
        descent=round(descent * scale),
        cap_height=round(cap * scale),
        widths_1000=widths,
        first_char=first,
        last_char=last,
    )


@lru_cache(maxsize=1)
def interior_face_bytes() -> bytes:
    """The bundled DejaVu Sans, read once through :mod:`importlib.resources`.

    The **same** resource mechanism ``export/pdf.py`` and ``export/png.py``
    read it through, named by that module's public
    :data:`~nonogram.export.pdf.FONT_PACKAGE` /
    :data:`~nonogram.export.pdf.FONT_RESOURCE` rather than by a second
    filesystem path to the same file: package data is addressed the way
    package data is addressed, so it keeps working from a wheel that was
    never unpacked, and there is one place to change if the face ever moves.

    Cached because the file is three quarters of a megabyte and every
    interior PDF asks for it.
    """
    return resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()


@lru_cache(maxsize=1)
def interior_face_metrics() -> FontMetrics:
    """:func:`font_metrics` of :func:`interior_face_bytes`, read once."""
    return font_metrics(interior_face_bytes())


# --------------------------------------------------------------------------
# The operator set
# --------------------------------------------------------------------------


def _number(value: float) -> str:
    """A PDF number: no exponent, no trailing zeros, never empty.

    ``repr`` and ``str`` both produce ``1e-05`` for a small enough float, and
    a PDF number has no exponent form — a viewer reads ``1e-05`` as ``1``
    followed by a syntax error. So this is the one place a coordinate becomes
    text.
    """
    text = f"{value:.{_PLACES}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-", "-0") else text


class ContentStream:
    """A page's content stream, accumulated one operator at a time.

    The whole vocabulary the interior's page cards need, and nothing above
    it: a caller states where a line goes, how wide it is and what tone it
    carries, and this records the operators. It holds no notion of a grid, a
    clue, a band or a page kind (G-1), and it derives no position
    (ADR-0042/R3).

    Positions arrive in **device pixels** measured from the page's top-left
    corner, because that is what COMP-007's ``Layout`` speaks; widths and
    type sizes arrive in **points**, because that is what the page is
    measured in and what ADR-0037/R2's weights are stated in. The flip to
    PDF's bottom-left origin happens here, once, in :meth:`_y`.

    Graphics state is the PDF's own: ``stroke_grey``, ``fill_grey`` and
    ``stroke_width`` set it and it persists until set again, exactly as the
    operators do. Nothing is remembered on this side, so what a reader of the
    stream sees is what the viewer sees.

    **There is deliberately no ``q``/``Q``.** Every state operator here is
    absolute, so a page card that wants a different width or tone sets it;
    nesting buys nothing a vocabulary with no transformations and no clipping
    can use, and CARD-293's prototype did without it over a full 30×30 page
    with 540 digits. A page card that turns out to need save/restore should
    add it *with the case that needs it*, rather than this card shipping an
    operator pair nothing exercises.
    """

    def __init__(self, *, width_px: float, height_px: float, dpi: float) -> None:
        if dpi <= 0:
            raise ContentStreamError(f"a page is drawn at a positive DPI, not {dpi!r}")
        self.width_px = width_px
        self.height_px = height_px
        self.dpi = dpi
        self._operators: list[str] = []

    # -- units ------------------------------------------------------------

    def to_points(self, pixels: float) -> float:
        """``pixels`` at this page's DPI, as points."""
        return pixels * POINTS_PER_INCH / self.dpi

    @property
    def media_box(self) -> tuple[float, float, float, float]:
        """The page's ``MediaBox``, in points: the trim, not the drawing."""
        return (0.0, 0.0, self.to_points(self.width_px), self.to_points(self.height_px))

    def _x(self, pixels: float) -> str:
        return _number(self.to_points(pixels))

    def _y(self, pixels: float) -> str:
        """A row, counted down from the page top, as a PDF y counted up."""
        return _number(self.to_points(self.height_px - pixels))

    # -- graphics state ---------------------------------------------------

    def stroke_grey(self, level: float) -> None:
        """Stroke tone, 0 = black, 1 = paper (the ``G`` operator)."""
        self._operators.append(f"{_number(_grey(level))} G")

    def fill_grey(self, level: float) -> None:
        """Fill tone, 0 = black, 1 = paper (the ``g`` operator)."""
        self._operators.append(f"{_number(_grey(level))} g")

    def stroke_width(self, points: float) -> None:
        """Stroke width, in points (the ``w`` operator).

        Points, not pixels, and that is the whole of ADR-0042's removal of
        ADR-0037/R2's device floor: 0.3 pt is expressible here, and a viewer
        resolves it at whatever resolution it is rendering at rather than at
        the one the generator happened to draw in.
        """
        if points < 0:
            raise ContentStreamError(f"a stroke is not {points} pt wide")
        self._operators.append(f"{_number(points)} w")

    # -- paths ------------------------------------------------------------

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """A stroked straight line between two points (``m``/``l``/``S``)."""
        self._operators.append(
            f"{self._x(x1)} {self._y(y1)} m {self._x(x2)} {self._y(y2)} l S"
        )

    def rectangle(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        *,
        paint: str = "stroke",
    ) -> None:
        """An axis-aligned rectangle (the ``re`` operator), painted ``paint``.

        ``left``/``top``/``right``/``bottom`` are the caller's own edges in
        the orientation a ``Layout`` states them in; ``re`` wants a corner and
        two extents, so the conversion happens here. ``paint`` is one of
        ``"stroke"`` (``S``), ``"fill"`` (``f``) or ``"both"`` (``B``) — the
        three PDF already has, named rather than spelled, because a page card
        asking for a filled cell should not have to remember which letter.
        """
        self._operators.append(
            f"{self._x(left)} {self._y(bottom)} "
            f"{_number(self.to_points(right - left))} "
            f"{_number(self.to_points(bottom - top))} re {_paint_operator(paint)}"
        )

    def curve(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
    ) -> None:
        """One cubic Bézier from the current point (the ``c`` operator).

        The two control points and the end point, in device pixels. This is
        the primitive PDF offers for anything that is not a straight line:
        there is no circle, no ellipse and no arc operator in a content
        stream, so every round shape in the interior is built out of calls to
        this.

        Open on purpose — a curve does not start a path, close one or paint
        one. :meth:`begin_path`, :meth:`close_path` and :meth:`paint` are the
        other three, and :meth:`round_mark` is the one composition of them
        this module ships.
        """
        self._operators.append(
            f"{self._x(x1)} {self._y(y1)} {self._x(x2)} {self._y(y2)} "
            f"{self._x(x3)} {self._y(y3)} c"
        )

    def begin_path(self, x: float, y: float) -> None:
        """Start a path at ``(x, y)`` (the ``m`` operator)."""
        self._operators.append(f"{self._x(x)} {self._y(y)} m")

    def line_to(self, x: float, y: float) -> None:
        """Extend the current path to ``(x, y)`` (the ``l`` operator)."""
        self._operators.append(f"{self._x(x)} {self._y(y)} l")

    def close_path(self) -> None:
        """Close the current subpath (the ``h`` operator)."""
        self._operators.append("h")

    def paint(self, paint: str = "stroke") -> None:
        """Paint the current path: ``"stroke"``, ``"fill"`` or ``"both"``."""
        self._operators.append(_paint_operator(paint))

    def round_mark(
        self,
        center_x: float,
        center_y: float,
        radius_px: float,
        *,
        paint: str = "fill",
    ) -> None:
        """A circle of ``radius_px`` about ``(center_x, center_y)``.

        **The interior's only round shape**, and the one primitive CARD-293's
        spike never emitted — it drew straight lines, rectangles, fills and
        text and no curve at all, which is why CARD-294 was ordered first.

        Four cubic Béziers, one per quadrant, each with its control points
        pushed :data:`BEZIER_CIRCLE_KAPPA` times the radius along the
        tangent. That is seven operators
        (:data:`ROUND_MARK_OPERATORS`): ``m``, four ``c``, ``h``, and one
        paint.

        The radius is a device-pixel length because that is the unit
        ``nonogram.export.layout.difficulty_dots`` states a dot's diameter
        in; this function computes neither it nor the centre
        (ADR-0042/R3/G-5). What it does compute is the control-point offset,
        which is a property of the approximation and not of any page — see
        :data:`BEZIER_CIRCLE_KAPPA`.

        The approximation's accuracy is **measured**, not assumed: the worst
        radial error is 2.7253e-4 of the radius (see
        :data:`BEZIER_CIRCLE_KAPPA`), which at the largest dot the book
        prints — 3.556 mm, the cap height of a twelve-millimetre band — is
        0.00048 mm, **one forty-fourth of a device pixel at 1200 DPI**. It is
        the same order as the 0.001 pt (0.00035 mm) the stream rounds its own
        coordinates to, so the approximation is not what limits the mark. The
        figures are derived by ``scripts/card294_curve_price.py`` and
        re-derived, independently, by
        ``TestVectorPrimitives_TheRoundMarkIsAccurateAtThePrintedDotSize``.
        """
        if radius_px <= 0:
            raise ContentStreamError(f"a round mark has a positive radius, not {radius_px!r}")
        pull = radius_px * BEZIER_CIRCLE_KAPPA
        left, right = center_x - radius_px, center_x + radius_px
        top, bottom = center_y - radius_px, center_y + radius_px
        self.begin_path(center_x, top)
        self.curve(center_x + pull, top, right, center_y - pull, right, center_y)
        self.curve(right, center_y + pull, center_x + pull, bottom, center_x, bottom)
        self.curve(center_x - pull, bottom, left, center_y + pull, left, center_y)
        self.curve(left, center_y - pull, center_x - pull, top, center_x, top)
        self.close_path()
        self.paint(paint)

    # -- text -------------------------------------------------------------

    def text(
        self,
        value: str,
        x: float,
        y: float,
        size_pt: float,
        *,
        grey: float = 0.0,
        resource: str = FACE_RESOURCE_NAME,
    ) -> None:
        """``value``, with its baseline starting at ``(x, y)``.

        ``size_pt`` is **points against the page** and is written straight
        into the ``Tf`` operand, which is AC-4: the same call at 300 DPI and
        at 1200 DPI produces the same ``Tf``, and the position scales with the
        device because the physical place on the paper does not move.

        ``x``/``y`` are the baseline's left end in device pixels — a position,
        not a box. Centring a string is the caller's arithmetic over
        :meth:`FontMetrics.advance`, because where a string sits is layout
        (ADR-0042/R3) while how wide it sets is type.
        """
        if size_pt <= 0:
            raise ContentStreamError(f"type is not set at {size_pt} pt")
        self._operators.append(
            f"{_number(_grey(grey))} g BT /{resource} {_number(size_pt)} Tf "
            f"{self._x(x)} {self._y(y)} Td ({_escape(value)}) Tj ET"
        )

    # -- the result -------------------------------------------------------

    @property
    def operators(self) -> tuple[str, ...]:
        """What has been recorded, one entry per emitted line."""
        return tuple(self._operators)

    def render(self) -> bytes:
        """The stream as the bytes a ``/Contents`` object holds.

        Encoded with :data:`TEXT_ENCODING`, not ASCII, because a literal
        string's bytes **are** the font's character codes: ``·`` inside
        ``(…) Tj`` has to reach the file as the single byte ``0xB7`` that
        ``/WinAnsiEncoding`` maps to that glyph. Every operator and every
        number this vocabulary writes is ASCII, which that encoding contains,
        so the only non-ASCII byte a stream can carry is one
        :func:`encode_text` has already admitted.
        """
        if not self._operators:
            return b""
        return encode_text("\n".join(self._operators) + "\n")


def _grey(level: float) -> float:
    if not 0.0 <= level <= 1.0:
        raise ContentStreamError(f"a grey level is 0..1, not {level!r}")
    return level


#: The three PDF paint operators, named. ``B`` fills and then strokes, which
#: is what an outlined dot with white inside it is.
_PAINT_OPERATORS = {"stroke": "S", "fill": "f", "both": "B"}


def _paint_operator(paint: str) -> str:
    try:
        return _PAINT_OPERATORS[paint]
    except KeyError:
        known = ", ".join(sorted(_PAINT_OPERATORS))
        raise ContentStreamError(f"paint is one of {known}, not {paint!r}") from None


def _escape(value: str) -> str:
    """``value`` as a PDF literal string's body.

    Checked against :data:`TEXT_ENCODING` on the way through, so an
    unrepresentable character fails here rather than reaching paper as a box.
    """
    encode_text(value)
    out = value.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")
    return out.replace("\r", r"\r").replace("\n", r"\n")


# --------------------------------------------------------------------------
# The file: the font objects once, then one page per content stream
# --------------------------------------------------------------------------


def write_vector_pdf(
    pages: Iterable[ContentStream],
    page_count: int,
    *,
    face_bytes: bytes | None = None,
    metrics: FontMetrics | None = None,
    comment: str = "nonogram vector interior",
) -> BytesIO:
    """``pages`` as one PDF, rewound to 0 — the font embedded exactly once.

    The same shape ``BookPDFGenerator._write_pdf`` has: ``page_count`` is not
    a hint but the object table's layout, allocated before the catalog is
    written, which is what lets the pages arrive one at a time rather than as
    a list (CARD-145). ``pages`` is consumed exactly once.

    Per page this writes **two** objects — a page and a contents stream of
    operators — where the raster path writes three, the extra one being a
    DCTDecode image. The font's three objects (``/Font``,
    ``/FontDescriptor``, ``/FontFile2``) are written **once per file**
    however many pages show text, which is ADR-0042/R5's "once per file" and
    the property ``PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts``
    sweeps across page counts.

    The content streams are FlateDecoded, and so is the face. Nothing here
    allocates a page bitmap, which is the retention ADR-0042 records as
    falling from 1.00 to 0.000246 ``PAGE_BITMAP_BYTES``.

    Args:
        pages: The content streams, in page order.
        page_count: How many ``pages`` will produce.
        face_bytes: The face to embed; the project's own by default. An
            argument only so a test can embed something else and watch the
            face check fail — AC-1's control needs a way to be wrong.
        metrics: Its metrics, read from ``face_bytes`` when not given.
        comment: The ``%``-comment after the header.

    Raises:
        ContentStreamError: ``pages`` produced a number of pages other than
            ``page_count``. The object table is laid out from that number, so
            a miscount is a corrupt file rather than a short one.
    """
    face = interior_face_bytes() if face_bytes is None else face_bytes
    measured = metrics or (
        interior_face_metrics() if face_bytes is None else font_metrics(face)
    )

    written = BytesIO()
    pdf = PdfParser.PdfParser(f=written, filename="", mode="w+b")
    pdf.info["CreationDate"] = time.gmtime()
    pdf.info["ModDate"] = time.gmtime()

    font_ref = pdf.next_object_id(0)
    descriptor_ref = pdf.next_object_id(0)
    file_ref = pdf.next_object_id(0)
    page_refs: list[Any] = []
    contents_refs: list[Any] = []
    for _ in range(page_count):
        page_refs.append(pdf.next_object_id(0))
        contents_refs.append(pdf.next_object_id(0))
        pdf.pages.append(page_refs[-1])

    pdf.start_writing()
    pdf.write_header()
    pdf.write_comment(comment)
    pdf.write_catalog()

    _write_face(pdf, face, measured, font_ref, descriptor_ref, file_ref)

    index = 0
    for stream in _exactly(pages, page_count):
        _, _, width_pt, height_pt = stream.media_box
        pdf.write_page(
            page_refs[index],
            Resources=PdfParser.PdfDict(
                ProcSet=[PdfParser.PdfName("PDF"), PdfParser.PdfName("Text")],
                Font=PdfParser.PdfDict(**{FACE_RESOURCE_NAME: font_ref}),
            ),
            MediaBox=[0, 0, width_pt, height_pt],
            Contents=contents_refs[index],
        )
        pdf.write_obj(
            contents_refs[index],
            stream=zlib.compress(stream.render(), 9),
            Filter=PdfParser.PdfName("FlateDecode"),
        )
        index += 1

    pdf.write_xref_and_trailer()
    pdf.close()
    written.seek(0)
    return written


def _write_face(
    pdf: PdfParser.PdfParser,
    face: bytes,
    metrics: FontMetrics,
    font_ref: Any,
    descriptor_ref: Any,
    file_ref: Any,
) -> None:
    """The three objects that embed the face, once per document.

    ``Flags=32`` is the non-symbolic bit, which is what PDF 1.7 §9.8.2 says
    a ``/TrueType`` font with ``/WinAnsiEncoding`` sets so that a viewer
    consults the encoding rather than the font's own ``(3, 0)`` cmap.
    ``StemV`` is required by the spec and consulted only when a viewer
    substitutes a face it does not have — which, the face being embedded, it
    never does here.

    **What is controlled and what is only asserted.** Every value written
    below is read back out of the finished file and compared against
    :func:`interior_face_metrics` by
    ``TestVectorFontObjects_TheDescriptorStatesTheFacesOwnMetrics``, so a
    descriptor that drifts from the face reds — ``Flags``, ``CapHeight``,
    ``Ascent``, ``Descent``, ``FontBBox``, ``Length1``, ``StemV``,
    ``Encoding`` and the whole ``/Widths`` array. What is **not** controlled
    is the *behavioural* half of the ``Flags`` sentence above — that a
    viewer which saw ``Flags=4`` would read the font's own cmap instead of
    ``/WinAnsiEncoding``. Measured in review cycle 1: poppler, the only PDF
    engine on this host, extracts and renders the text identically with
    ``Flags=4``, and ``qpdf``, ``mutool`` and ``gs`` are not installed, so no
    instrument here can falsify it. It is therefore stated as what it is: the
    spec's rule, assumed and unverified against Acrobat or a press RIP, with
    the emitted value pinned so it cannot change unnoticed.
    """
    pdf.write_obj(
        file_ref,
        stream=zlib.compress(face, 9),
        Filter=PdfParser.PdfName("FlateDecode"),
        Length1=len(face),
    )
    pdf.write_obj(
        descriptor_ref,
        Type=PdfParser.PdfName("FontDescriptor"),
        FontName=PdfParser.PdfName(FACE_BASE_FONT),
        Flags=32,
        FontBBox=list(metrics.bbox),
        ItalicAngle=0,
        Ascent=metrics.ascent,
        Descent=metrics.descent,
        CapHeight=metrics.cap_height,
        StemV=80,
        FontFile2=file_ref,
    )
    pdf.write_obj(
        font_ref,
        Type=PdfParser.PdfName("Font"),
        Subtype=PdfParser.PdfName("TrueType"),
        BaseFont=PdfParser.PdfName(FACE_BASE_FONT),
        FirstChar=metrics.first_char,
        LastChar=metrics.last_char,
        Widths=[
            metrics.widths_1000.get(code, 0)
            for code in range(metrics.first_char, metrics.last_char + 1)
        ],
        FontDescriptor=descriptor_ref,
        Encoding=PdfParser.PdfName("WinAnsiEncoding"),
    )


def _exactly(pages: Iterable[ContentStream], expected: int) -> Iterator[ContentStream]:
    """``pages``, refusing a count other than ``expected``.

    The vector sibling of ``book_pdf_generator._as_planned``, reimplemented
    rather than imported: this module is a vocabulary with no dependency on
    the 7,000-line generator, and the native-reimplementation convention this
    package already follows for ``_stroke_drawing`` and ``mask_runs`` is what
    keeps the edge from running the wrong way.
    """
    seen = 0
    for page in pages:
        seen += 1
        if seen > expected:
            raise ContentStreamError(
                f"the page plan said {expected} pages and page {seen} arrived"
            )
        yield page
    if seen != expected:
        raise ContentStreamError(f"the page plan said {expected} pages and {seen} arrived")

