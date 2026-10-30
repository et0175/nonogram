"""Read a vector interior PDF back: its streams, its face, and its ink.

CARD-294. Two readers live here and they are not the same kind of thing, so
the difference is worth stating before either is used:

* :func:`content_streams`, :func:`embedded_faces`, :func:`base_font_names`
  and :func:`operator_tokens` read the file with :mod:`PIL.PdfParser` — the
  same parser ``tests/helpers/pdf_pages.py`` already opens a book PDF with.
  They are **convenient, not independent**: the writer under test and this
  reader are both this project's, so an agreement between them proves only
  that two of its functions agree, which is the failure mode CLAUDE.md names.
* :func:`rendered_page` runs **poppler** — ``pdftoppm``, an engine that did
  not write the file — and :func:`extracted_text` runs ``pdftotext``. These
  are the independent half, and they are what AC-2's claim rests on.

``tests/helpers/pdf_pages.py`` is deliberately left alone: it asserts that a
page is *exactly one image XObject*, which is true of the raster pages and
of the cover and is false of a vector page by construction (ADR-0042/R1). A
vector reader beside it rather than a widened one keeps that assertion
meaning what it says.

Nothing here names one of the eight render idioms
``meta/profiling/rank_durations.py`` greps for, so this file does not join the
frozen render-heavy set (CARD-294 G-7).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Mapping, NamedTuple

import numpy as np
from PIL import Image, PdfParser

#: Poppler's rasteriser and text extractor. Absent on a host that never
#: installed poppler, which the tests that need them say out loud rather than
#: passing quietly.
PDFTOPPM = shutil.which("pdftoppm")
PDFTOTEXT = shutil.which("pdftotext")

#: A pixel at or below this grey (0..255) is ink. The same threshold
#: ``tests/helpers/pdf_pages.py`` uses, so "ink" means one thing in this tree.
INK_LEVEL = 128

#: A PDF number as it appears in a content stream: no exponent form.
NUMBER = r"-?\d+(?:\.\d+)?"


def content_streams(data: bytes) -> list[str]:
    """Every page's decoded content stream, in page order.

    Decoded with ``cp1252`` because that is the encoding the interior declares
    (``/WinAnsiEncoding``), so a literal string's bytes come back as the
    characters they set.
    """
    parser = PdfParser.PdfParser(buf=data)
    try:
        streams = []
        for ref in parser.pages:
            page = parser.read_indirect(ref)
            contents = parser.read_indirect(page[b"Contents"])
            streams.append(contents.decode().decode("cp1252"))
        return streams
    finally:
        parser.close()


def page_resource_keys(data: bytes) -> list[set[str]]:
    """Each page's ``/Resources`` keys, as plain strings, in page order.

    Spelled out rather than handed back as Pillow's own dictionary because
    ``PdfDict`` indexes by ``bytes`` but *iterates* ``PdfName``, and a
    membership test that silently reads ``False`` is how "this page carries no
    image XObject" would pass without being true (ADR-0042/R1).
    """
    parser = PdfParser.PdfParser(buf=data)
    try:
        out: list[set[str]] = []
        for ref in parser.pages:
            resources = parser.read_indirect(ref)[b"Resources"]
            out.append({getattr(key, "name", key).decode("latin-1") for key in resources})
        return out
    finally:
        parser.close()


#: The three values :func:`page_media` returns. ``UNCLASSIFIABLE`` is a value
#: and not an exception because the caller is the one that has to fail on it
#: (ADR-0039/R2), and a reader that raised would not let a caller *count* how
#: many pages it could not classify.
RASTER = "raster"
VECTOR = "vector"
UNCLASSIFIABLE = "unclassifiable"


def page_media(data: bytes) -> list[str]:
    """Each page of ``data``, classified by medium — default-DENY.

    A page is :data:`RASTER` iff its resources name an ``/XObject`` and no
    ``/Font``, and :data:`VECTOR` iff they name a ``/Font`` and no
    ``/XObject``. **Both, or neither, is :data:`UNCLASSIFIABLE`** — there is no
    third medium in this project and no fallback: a page shaped like nothing
    this writer emits is a page nobody has classified, which ADR-0039/R2 makes
    a failure rather than a pass.

    **CARD-299 moved this here from ``tests/test_book_pdf.py``, where it was
    ``_page_media``, and that module now calls it** — ADR-0042/R6's readers
    live in several modules and each one of them has to ask the same question
    of the same file, so a second copy of this classification is the one thing
    that would let two readers disagree about what medium a page is. That
    module's ``_declaration_findings`` docstring already insists on "the one
    implementation"; this is where it now is.

    A **vector page with no ink at all still names the face** — every page
    :func:`~nonogram.admin.book_vector.write_vector_page` writes does — so the
    blank title page's vector twin classifies as :data:`VECTOR` and not as
    unclassifiable.
    """
    media = []
    for keys in page_resource_keys(data):
        has_image = "XObject" in keys
        has_face = "Font" in keys
        if has_image and not has_face:
            media.append(RASTER)
        elif has_face and not has_image:
            media.append(VECTOR)
        else:
            media.append(UNCLASSIFIABLE)
    return media


def _objects(data: bytes):
    parser = PdfParser.PdfParser(buf=data)
    try:
        for ref in sorted(parser.xref_table.keys()):
            try:
                obj = parser.read_indirect((ref, 0))
            except Exception:  # pragma: no cover - a free or non-object entry
                continue
            yield parser, obj
    finally:
        parser.close()


def embedded_faces(data: bytes) -> list[bytes]:
    """Every ``/FontFile2``'s decompressed bytes, one per embedded face.

    The count is ADR-0042/R5's "once per file" and the bytes are AC-1's
    comparison against the face on disk.
    """
    faces: list[bytes] = []
    for parser, obj in _objects(data):
        if isinstance(obj, Mapping) and obj.get(b"Type") == b"FontDescriptor":
            faces.append(parser.read_indirect(obj[b"FontFile2"]).decode())
    return faces


def _plain(value):
    """A ``PdfParser`` value as a plain Python one.

    ``PdfName`` holds its bytes in ``.name``; a ``/Name`` that came off the
    writer's side of the parser may arrive as raw bytes instead. Both become
    ``str``, numbers stay numbers, and a list becomes a list of the same —
    because a descriptor entry compared against a metric has to be compared
    as the number or the name it is, not as whichever wrapper it arrived in.
    """
    if isinstance(value, list):
        return [_plain(item) for item in value]
    raw = getattr(value, "name", value)
    if isinstance(raw, bytes):
        return raw.decode("latin-1")
    return raw


def font_objects(data: bytes, kind: str) -> list[dict[str, object]]:
    """Every object whose ``/Type`` is ``kind``, as plain-keyed dictionaries.

    Written for the ``/FontDescriptor`` and ``/Font`` dictionaries, whose
    entries CARD-294 review cycle 1 found stated with a rationale and no
    control (F-4). Indirect references arrive as they are — the caller asks
    about numbers and names, not about the object graph.

    Reads with :mod:`PIL.PdfParser`, so it is the **convenient** half: it
    checks this writer against the metrics this project read, which is the
    right instrument for "the descriptor states the face's own numbers" and
    the wrong one for "the face's numbers are right". The second is
    FreeType's job, in the test module.
    """
    found: list[dict[str, object]] = []
    for _, obj in _objects(data):
        if isinstance(obj, Mapping) and _plain(obj.get(b"Type")) == kind:
            found.append(
                {
                    getattr(key, "name", key).decode("latin-1"): _plain(obj[key])
                    for key in obj
                }
            )
    return found


def font_file_lengths(data: bytes) -> list[int]:
    """Every ``/FontFile2``'s declared ``/Length1``, one per embedded face.

    Separate from :func:`font_objects` because ``/Length1`` lives on the
    *stream* object the descriptor points at, not on the descriptor.
    """
    lengths: list[int] = []
    for parser, obj in _objects(data):
        if isinstance(obj, Mapping) and _plain(obj.get(b"Type")) == "FontDescriptor":
            stream = parser.read_indirect(obj[b"FontFile2"])
            lengths.append(_plain(stream.dictionary[b"Length1"]))
    return lengths


def base_font_names(data: bytes) -> list[str]:
    """Every ``/BaseFont`` the file names — so a base-14 reference is visible."""
    names: list[str] = []
    for _, obj in _objects(data):
        if isinstance(obj, Mapping) and b"BaseFont" in obj:
            # PdfParser hands a /Name back either as a PdfName (which holds
            # its bytes in ``.name``) or as raw bytes, depending on which side
            # of the parser built it. Both spellings are read, because a
            # base-14 reference missed on a type check would read as absent.
            value = obj[b"BaseFont"]
            raw = getattr(value, "name", value)
            names.append(raw.decode("latin-1") if isinstance(raw, bytes) else str(raw))
    return names


def operator_tokens(stream: str) -> list[str]:
    """Every operator token of ``stream``, in order.

    A regular expression over the stream with literal strings and names
    removed first — deliberately a *different* implementation from the
    hand-written scanner in ``scripts/card294_curve_price.py``, so the two
    counts of "how many operators does a round mark cost" are independent.
    """
    without_strings = re.sub(r"\((?:\\.|[^()\\])*\)", " ", stream)
    return [
        token
        for token in without_strings.split()
        if not token.startswith("/") and not re.fullmatch(NUMBER, token)
    ]


def operator_tally(stream: str) -> Counter[str]:
    """``{operator: count}`` over ``stream``."""
    return Counter(operator_tokens(stream))


def tones(stream: str) -> list[tuple[float, str]]:
    """Every ``(level, operator)`` tone ``stream`` sets, in order.

    ``g`` is the fill tone and ``G`` the stroke tone, and the two spellings a
    content stream really uses are **not** the same shape:

    * a path tone stands alone on its line (``0 g``), because
      :meth:`~nonogram.admin.book_vector.ContentStream.fill_grey` and
      ``stroke_grey`` emit one operator each;
    * a **text** tone is written INLINE, at the head of the text object it
      applies to — ``0 g BT /F1 11 Tf 72 720 Td (How to solve) Tj ET`` — because
      :meth:`~nonogram.admin.book_vector.ContentStream.text` emits the whole
      object as one line.

    CARD-296 review cycle 1 (F-3) measured what a line-anchored ``(?m)^…$``
    tone regex does with that: it reads the path tones and **none** of the
    text ones, so the guide's entire body could be set in 50 % grey with the
    tone assertion green. This reader is here, rather than in one page card's
    test module, so CARD-295/297/298 inherit the inline case instead of each
    rediscovering it.

    Literal strings are removed first, so a ``(…) Tj`` operand that happens to
    read ``0 g`` is text and not a tone.
    """
    without_strings = re.sub(r"\((?:\\.|[^()\\])*\)", " ", stream)
    return [
        (float(level), operator)
        for level, operator in re.findall(
            rf"(?:^|\s)({NUMBER}) ([gG])(?=\s|$)", without_strings
        )
    ]


def subpath_vertices(stream: str) -> list[int]:
    """How many points each subpath of ``stream`` is built from, in order.

    A subpath opens at an ``m`` and its points are that ``m`` plus every ``l``
    (straight segment) and ``c`` (cubic Bézier) written after it, up to the
    next ``m``. ``h``, the paint operators and ``re`` end or bypass it and are
    not points.

    **What this counts, and what a bound over it can and cannot claim.**
    PDF has no circle operator, which is true and is not the same statement as
    "a content stream cannot draw a disc": ``begin_path``/``line_to``/
    ``close_path``/``paint`` build an arbitrary polygon out of ``m``, ``l`` and
    ``h``, and a 32-gon is a disc at any size this book prints. CARD-296 review
    cycle 1 (F-1) planted exactly that beside each difficulty tier and every
    curve-operator and ``round_mark`` assertion in the tree stayed green.

    **A vertex bound over this count does NOT close that route**, and this
    docstring used to say it did ("a vertex bound is the mechanism that closes
    it"). CARD-296 review cycle 2 measured two discs that a bound of 4 admits:
    a fan of 32 **three-point** triangles (one subpath per sector, so the count
    this function returns maxes at 3), and a staircase of 24 filled ``re``
    bands (this function counts only ``m``/``l``/``c``, so ``re`` ink is not
    counted at all). The bound cannot be tightened out of it either: a guide
    page's own arrow head is three points, which is also a triangle. The same
    hole is in ``tests/test_book_difficulty_dots.py``'s ``MAX_FLAT_VERTICES``,
    the precedent that reasoning was borrowed from — a ``draw.polygon``
    triangle fan clears a per-call bound the same way.

    So what a bound over this count honestly claims is **"no single long
    subpath"**: a tripwire on a page's own path lengths, worth having and not a
    round-shape rule. Closing the approximation route needs an instrument that
    is not a vertex count — an ink measurement (CARD-241) or a rule on filled
    subpaths — and **CARD-298** owns ADR-0042/R1's derived per-page-kind check,
    which is where it belongs.

    A page card holds its own pages to its own bound (a diagram's longest path
    is its own business); the reader lives here so each page card of the phase
    inherits the count rather than writing a fourth path scanner.
    """
    counts: list[int] = []
    for token in operator_tokens(stream):
        if token == "m":
            counts.append(1)
        elif token in ("l", "c"):
            if not counts:  # a segment with no moveto: malformed, still counted
                counts.append(1)
            counts[-1] += 1
    return counts


def type_sizes(stream: str) -> list[float]:
    """Every ``Tf`` operand, in order — the point size each text object sets.

    What CON-020's rewritten floor check reads (CARD-299), and AC-4's
    measurement: the operand is a physical point size, so the same drawing at
    another DPI must produce the same list.
    """
    return [float(m) for m in re.findall(rf"/\w+\s+({NUMBER})\s+Tf", stream)]


#: The marked-content tag a vector page writes its clue digits inside
#: (``nonogram.admin.book_vector.CLUE_DIGIT_TAG``), **written out rather than
#: imported**. CLAUDE.md's test style: the reader of a claim states the claim
#: independently, so that renaming the writer's constant reds the reading
#: instead of silently following it to a tag nothing emits. The two spellings
#: are held equal by
#: ``tests/test_book_interior_type_floor.py::TestInteriorType_TheClueDigitMarkIsTheWritersOwn``.
CLUE_DIGIT_TAG = "ClueDigit"

#: One marked-content bracket or one ``Tf``, in the order the stream writes
#: them. ``BDC`` is read beside ``BMC`` because a hand-appended row is what an
#: over-application control plants, and a reading blind to one bracket would
#: count its ``EMC`` as closing a sequence nothing opened.
_MARKED_OR_TF = re.compile(
    rf"(?:^|(?<=[\s/\[\]<>(){{}}]))"
    rf"(?:/(?P<tag>[A-Za-z][\w.-]*)\s+(?P<open>BMC|BDC)"
    rf"|(?P<close>EMC)"
    rf"|/(?P<face>\w+)\s+(?P<size>{NUMBER})\s+Tf)"
    rf"(?=[\s/\[\]<>(){{}}]|$)"
)


class MarkedFace(NamedTuple):
    """One ``Tf`` size, and whether the stream says it is a clue digit.

    CARD-314. :func:`type_sizes` above answers "what sizes does this page
    set"; this answers the question CON-020 actually asks, which is "and which
    of them is the **exempt** kind of mark". The exemption is keyed on the
    function that drew (``png._draw_clues`` / ``_write_clues`` /
    ``book_vector_draw.draw_clue_digits``), a content stream records no caller,
    and so the writer records the provenance itself as a
    :data:`CLUE_DIGIT_TAG` marked-content sequence.

    ``exempt`` is therefore read off **the mark and never off the size**: a
    body face that happens to measure a clue digit's 8.64 pt comes back
    ``exempt=False`` and is reported, which is CARD-314's AC-2 and the whole
    reason this is not a size test.
    """

    points: float
    exempt: bool


def marked_type_sizes(stream: str) -> list[MarkedFace]:
    """Every ``Tf`` of ``stream``, each tagged with the mark it was set inside.

    The stream is scanned once, in order, with literal strings blanked first —
    so a ``(see EMC) Tj`` caption is text and not a bracket — and a
    :data:`CLUE_DIGIT_TAG` sequence makes every ``Tf`` inside it exempt. Marked
    content nests (PDF 1.7 §14.6), so the state tracked is a stack rather than
    a flag: a clue-digit sequence containing some other tag's sequence still
    exempts what is inside the inner one, which is the reading the operators
    mean.

    Raises:
        ValueError: the brackets do not pair. An ``EMC`` that closes nothing,
            or a sequence open at the stream's end, leaves the extent of the
            claim undefined — so what is exempt here is not *wrong* but
            **unanalysable**, and ADR-0039/R2 makes that a failure. Raising
            rather than returning a third value is deliberate: unlike
            :func:`page_media`, where a caller may want to count the pages it
            could not classify, there is no partial list of faces to count.
    """
    without_strings = re.sub(r"\((?:\\.|[^()\\])*\)", " ", stream)
    stack: list[str] = []
    faces: list[MarkedFace] = []
    for match in _MARKED_OR_TF.finditer(without_strings):
        if match.group("open"):
            stack.append(match.group("tag"))
        elif match.group("close"):
            if not stack:
                raise ValueError(
                    "this content stream closes a marked-content sequence that "
                    f"was never opened, at offset {match.start()}: its "
                    "clue-digit exemption has no readable extent (ADR-0039/R2)"
                )
            stack.pop()
        else:
            faces.append(
                MarkedFace(float(match.group("size")), CLUE_DIGIT_TAG in stack)
            )
    if stack:
        raise ValueError(
            f"this content stream leaves {stack!r} open at its end, so what "
            "those marked-content sequences are a statement about is the rest "
            "of the page: its clue-digit exemption has no readable extent "
            "(ADR-0039/R2)"
        )
    return faces


def stroke_widths(stream: str) -> list[float]:
    """Every ``w`` operand, in order — stroke widths in points."""
    return [float(m) for m in re.findall(rf"(?m)^({NUMBER}) w$", stream)]


def rendered_page(data: bytes, dpi: int, page: int = 1, out_dir: Path | None = None):
    """``page`` of ``data`` rasterised by **poppler**, as a greyscale array.

    The independent half of AC-2: an engine that did not write the file is
    asked what the file says, and the answer is pixels. Returns a
    ``numpy`` array of 0..255 greys indexed ``[row, column]``.

    Raises:
        RuntimeError: poppler is installed but produced nothing — a failure,
            never a pass. A host with no poppler at all is the caller's
            business (:data:`PDFTOPPM` is ``None``), because a missing engine
            is a missing control and has to be said out loud.
    """
    if PDFTOPPM is None:  # pragma: no cover - guarded at the call site
        raise RuntimeError("poppler's pdftoppm is not on this host")
    directory = out_dir or Path(".")
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "vector.pdf"
    source.write_bytes(data)
    subprocess.run(
        [
            PDFTOPPM,
            "-r",
            str(dpi),
            "-f",
            str(page),
            "-l",
            str(page),
            "-gray",
            "-png",
            str(source),
            str(directory / "page"),
        ],
        check=True,
        capture_output=True,
    )
    rendered = sorted(directory.glob("page-*.png"))
    if not rendered:
        raise RuntimeError(f"pdftoppm wrote no image for page {page}")
    with Image.open(rendered[0]) as image:
        return np.asarray(image.convert("L"), dtype=np.int16)


def extracted_text(data: bytes, out_dir: Path | None = None) -> str:
    """``data``'s text layer, as **poppler** reads it.

    The other independent reading: it exercises the embedded face's
    ``/Widths``, its ``/Encoding`` and the ``Tj`` operand together, and it is
    the only check that the characters a reader can select are the ones the
    writer showed.
    """
    if PDFTOTEXT is None:  # pragma: no cover - guarded at the call site
        raise RuntimeError("poppler's pdftotext is not on this host")
    directory = out_dir or Path(".")
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "text.pdf"
    source.write_bytes(data)
    done = subprocess.run(
        [PDFTOTEXT, str(source), "-"], check=True, capture_output=True
    )
    return done.stdout.decode("utf-8")


#: One word of a page's text layer, as poppler's ``-bbox`` reports it: the
#: text and its box in **points from the page's top-left corner**, y down.
#: A named tuple rather than a 5-tuple because ``word.center_x`` at the call
#: site is the difference between a readable placement assertion and four
#: index expressions (CARD-295).
class Word(NamedTuple):
    text: str
    left: float
    top: float
    right: float
    bottom: float

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2.0

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2.0


_WORD = re.compile(
    r'<word xMin="([\d.eE+-]+)" yMin="([\d.eE+-]+)" '
    r'xMax="([\d.eE+-]+)" yMax="([\d.eE+-]+)">(.*?)</word>'
)


def word_boxes(data: bytes, page: int = 1, out_dir: Path | None = None) -> list[Word]:
    """Every word **poppler** finds on ``page``, with the box it found it in.

    The placement half of the text reading, and the independent one: a box
    here is poppler's own measurement of where the glyphs it laid out from the
    embedded ``/Widths`` actually sit, so comparing it against a
    ``Layout``'s stated centre asks an engine that did not write the file
    where the writer put the mark (CARD-295's AC-3).

    Poppler reports the box in points from the page's **top-left** corner,
    which is the ``Layout``'s own orientation — the flip to PDF's bottom-left
    origin is the writer's business and does not reach here.

    XML by regex rather than by a parser: the five numbers wanted are in one
    attribute list, and ``xml.etree`` would have to be told about the XHTML
    doctype's entities. ``&amp;``/``&lt;``/``&gt;`` are the only escapes
    poppler emits inside a word, and they are undone below.
    """
    if PDFTOTEXT is None:  # pragma: no cover - guarded at the call site
        raise RuntimeError("poppler's pdftotext is not on this host")
    directory = out_dir or Path(".")
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "bbox.pdf"
    source.write_bytes(data)
    done = subprocess.run(
        [PDFTOTEXT, "-bbox", "-f", str(page), "-l", str(page), str(source), "-"],
        check=True,
        capture_output=True,
    )
    found = []
    for left, top, right, bottom, text in _WORD.findall(done.stdout.decode("utf-8")):
        unescaped = (
            text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        )
        found.append(
            Word(unescaped, float(left), float(top), float(right), float(bottom))
        )
    return found


def ink_mask(page: np.ndarray) -> np.ndarray:
    """Which pixels of ``page`` are ink."""
    return page <= INK_LEVEL


def ink_box(page: np.ndarray) -> tuple[int, int, int, int]:
    """``(left, top, right, bottom)`` of every inked pixel, inclusive.

    Raises:
        AssertionError: nothing was inked. A render with no ink is the state
            an "is the shape where the writer said" assertion would otherwise
            pass vacuously on.
    """
    rows, columns = np.nonzero(ink_mask(page))
    assert rows.size, "poppler rendered the page with no ink on it at all"
    return int(columns.min()), int(rows.min()), int(columns.max()), int(rows.max())


def to_buffer(data: BytesIO | bytes) -> bytes:
    """``data`` as bytes, whichever of the two a writer handed back."""
    return data.getvalue() if isinstance(data, BytesIO) else data
