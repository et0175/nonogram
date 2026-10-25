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
from typing import Mapping

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


def type_sizes(stream: str) -> list[float]:
    """Every ``Tf`` operand, in order — the point size each text object sets.

    What CON-020's rewritten floor check reads (CARD-299), and AC-4's
    measurement: the operand is a physical point size, so the same drawing at
    another DPI must produce the same list.
    """
    return [float(m) for m in re.findall(rf"/\w+\s+({NUMBER})\s+Tf", stream)]


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
